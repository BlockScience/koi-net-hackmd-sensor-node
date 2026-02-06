import json
import os
import threading
import time
from logging import Logger

from koi_net.core import KobjQueue
from rid_lib.ext import Bundle
from rid_lib.types import HackMDNote

from .config import HackMDSensorConfig
from .hackmd_client import HackMDClient
from .models import HackMDNoteObject


class HackMDIngestionService:
    def __init__(
        self,
        log: Logger,
        config: HackMDSensorConfig, 
        kobj_queue: KobjQueue
    ):
        self.log = log
        self.config = config
        self.kobj_queue = kobj_queue

        self.client = HackMDClient(
            api_token=config.env.hackmd_api_token,
            log=self.log,
            workspace_id=config.hackmd.workspace_id,
            note_ids=config.hackmd.note_ids,
            retries=getattr(config.hackmd, "retries", 3),
            backoff_base=getattr(config.hackmd, "backoff_base_seconds", 1.0),
            backoff_max=getattr(config.hackmd, "backoff_max_seconds", 10.0),
        )

        # Durable state file
        self.state_path = getattr(config.hackmd, "state_path", "cache/hackmd_state.json")
        self.state_lock = threading.Lock()
        self.state = self._load_state()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def _load_state(self) -> dict:
        try:
            with open(self.state_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except Exception as e:
            self.log.warning("Failed to load state file %s: %s", self.state_path, e)
            return {}

    def _save_state(self):
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
            with self.state_lock:
                with open(self.state_path, "w") as f:
                    json.dump(self.state, f, indent=2, default=str)
        except Exception as e:
            self.log.warning("Failed to write state file %s: %s", self.state_path, e)

    def _state_key(self, note: HackMDNoteObject) -> str:
        # Use workspace/note_id if available for uniqueness; else note_id
        return f"{note.workspace_id}/{note.note_id}" if note.workspace_id else note.note_id

    def start(self):
        if self._thread and self._thread.is_alive():
            self.log.debug("HackMD ingestion service already running")
            return

        poll_interval = self.config.hackmd.poll_interval_seconds
        self.log.info("HackMD ingestion service starting; interval=%ss", poll_interval)

        self._stop_event.clear()

        def _run():
            self.log.info("HackMD ingestion started")
            while not self._stop_event.is_set():
                start = time.time()
                try:
                    self.poll_once()
                except Exception as e:
                    self.log.error("Ingestion poll failed: %s", e)
                    time.sleep(5)
                elapsed = time.time() - start
                remaining = max(0.0, poll_interval - elapsed)
                if remaining:
                    self._stop_event.wait(remaining)
            self.log.info("HackMD ingestion stopped")

        self._thread = threading.Thread(target=_run, name="hackmd-ingestion", daemon=True)
        self._thread.start()

    def stop(self):
        if not self._thread:
            return

        self._stop_event.set()
        self._thread.join(timeout=5)
        self._thread = None

    def poll_once(self):
        self.log.info("Polling HackMD for notes...")
        notes = self.client.get_notes(limit=self.config.hackmd.max_notes_per_poll)

        processed = 0
        for note in notes:
            # Handle both dict and HackMDNoteObject
            if isinstance(note, dict):
                note_data = note
                note_obj = HackMDNoteObject.model_validate(note_data)
            else:
                note_obj = note
                note_data = note.model_dump(mode="json")
            
            key = self._state_key(note_obj)
            prev_timestamp = self.state.get(key)
            
            # Convert timestamps to comparable format
            current_timestamp = note_obj.last_changed_at
            if current_timestamp is None:
                current_timestamp = note_obj.created_at
            
            # Decide whether to process
            should = False
            if prev_timestamp is None:
                should = True
            elif current_timestamp and current_timestamp > prev_timestamp:
                should = True

            if not should:
                continue

            note_rid = HackMDNote(note_obj.note_id, note_obj.workspace_id)
            self._process_note(note_rid, note_data)
            processed += 1
            # Update state with timestamp
            if current_timestamp:
                self.state[key] = current_timestamp

        if processed:
            self.log.info("Processed %d HackMD notes", processed)
            self._save_state()
        else:
            self.log.info("No HackMD note changes detected")

    def _process_note(self, note_rid: HackMDNote, note_data):
        try:
            # Handle both dict and HackMDNoteObject
            if hasattr(note_data, 'model_dump'):
                contents = note_data.model_dump(mode="json")
            else:
                contents = note_data
            
            bundle = Bundle.generate(rid=note_rid, contents=contents)
            self.kobj_queue.push(bundle=bundle)
            self.log.debug("Queued bundle for %s", note_rid)
        except Exception as e:
            self.log.error("Failed to process note %s: %s", note_rid, e)
