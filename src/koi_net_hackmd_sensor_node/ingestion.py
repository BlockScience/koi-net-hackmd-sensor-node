import json
import logging
import os
import threading
import time
from datetime import datetime
from rid_lib.ext import Bundle
from .hackmd_client import HackMDClient
from koi_net_shared import HackMDNote
from .models import HackMDNoteObject

logger = logging.getLogger(__name__)

class HackMDIngestionService:
    def __init__(self, node, config):
        self.node = node
        self.config = config

        self.client = HackMDClient(
            api_token=config.hackmd.api_token,
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

    def _load_state(self) -> dict:
        try:
            with open(self.state_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except Exception as e:
            logger.warning("Failed to load state file %s: %s", self.state_path, e)
            return {}

    def _save_state(self):
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
            with self.state_lock:
                with open(self.state_path, "w") as f:
                    json.dump(self.state, f, indent=2, default=str)
        except Exception as e:
            logger.warning("Failed to write state file %s: %s", self.state_path, e)

    def _state_key(self, note: HackMDNoteObject) -> str:
        # Use workspace/note_id if available for uniqueness; else note_id
        return f"{note.workspace_id}/{note.note_id}" if note.workspace_id else note.note_id

    def run_forever(self, stop_event: threading.Event):
        poll_interval = self.config.hackmd.poll_interval_seconds
        logger.info("HackMD ingestion started; interval=%ss", poll_interval)
        while not stop_event.is_set():
            start = time.time()
            try:
                self.poll_once()
            except Exception as e:
                logger.error("Ingestion poll failed: %s", e)
                # brief backoff on hard failure
                time.sleep(5)
            elapsed = time.time() - start
            sleep_for = max(0.0, poll_interval - elapsed)
            if sleep_for > 0:
                stop_event.wait(sleep_for)
        logger.info("HackMD ingestion stopped")

    def poll_once(self):
        logger.info("Polling HackMD for notes...")
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
            logger.info("Processed %d HackMD notes", processed)
            self._save_state()
        else:
            logger.info("No HackMD note changes detected")

    def _process_note(self, note_rid: HackMDNote, note_data):
        try:
            # Handle both dict and HackMDNoteObject
            if hasattr(note_data, 'model_dump'):
                contents = note_data.model_dump(mode="json")
            else:
                contents = note_data
            
            bundle = Bundle.generate(rid=note_rid, contents=contents)
            self.node.processor.handle(bundle=bundle)
            logger.debug("Queued bundle for %s", note_rid)
        except Exception as e:
            logger.error("Failed to process note %s: %s", note_rid, e)
