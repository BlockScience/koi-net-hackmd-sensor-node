import json
import os
import threading
import time

from koi_net.core import KobjQueue
from rid_lib.ext import Bundle
from rid_lib.types import HackMDNote
import structlog

from .config import HackMDSensorConfig
from .hackmd_client import HackMDClient
from .models import HackMDNoteObject

log = structlog.stdlib.get_logger()


class HackMDIngestionService:
    def __init__(
        self,
        config: HackMDSensorConfig, 
        kobj_queue: KobjQueue
    ):
        self.log = log
        self.config = config
        self.kobj_queue = kobj_queue
        self.poll_interval = self._resolve_int(
            env_value=getattr(config.env, "HACKMD_POLL_INTERVAL_SECONDS", ""),
            fallback=config.hackmd.poll_interval_seconds,
            label="HACKMD_POLL_INTERVAL_SECONDS",
        )
        self.max_notes_per_poll = self._resolve_int(
            env_value=getattr(config.env, "HACKMD_MAX_NOTES_PER_POLL", ""),
            fallback=config.hackmd.max_notes_per_poll,
            label="HACKMD_MAX_NOTES_PER_POLL",
        )
        workspace_id = self._resolve_optional_str(
            env_value=getattr(config.env, "HACKMD_WORKSPACE_ID", ""),
            fallback=config.hackmd.workspace_id,
        )
        note_ids = self._resolve_note_ids(
            env_value=getattr(config.env, "HACKMD_NOTE_IDS", ""),
            fallback=config.hackmd.note_ids,
        )
        retries = self._resolve_int(
            env_value=getattr(config.env, "HACKMD_RETRIES", ""),
            fallback=getattr(config.hackmd, "retries", 3),
            label="HACKMD_RETRIES",
        )
        backoff_base = self._resolve_float(
            env_value=getattr(config.env, "HACKMD_BACKOFF_BASE_SECONDS", ""),
            fallback=getattr(config.hackmd, "backoff_base_seconds", 1.0),
            label="HACKMD_BACKOFF_BASE_SECONDS",
        )
        backoff_max = self._resolve_float(
            env_value=getattr(config.env, "HACKMD_BACKOFF_MAX_SECONDS", ""),
            fallback=getattr(config.hackmd, "backoff_max_seconds", 10.0),
            label="HACKMD_BACKOFF_MAX_SECONDS",
        )

        self.client = HackMDClient(
            api_token=config.env.HACKMD_API_TOKEN,
            log=self.log,
            workspace_id=workspace_id,
            note_ids=note_ids,
            retries=retries,
            backoff_base=backoff_base,
            backoff_max=backoff_max,
        )

        # Durable state file
        env_state_path = self._resolve_optional_str(
            env_value=getattr(config.env, "HACKMD_STATE_PATH", ""),
            fallback=getattr(config.hackmd, "state_path", "cache/hackmd_state.json"),
        )
        self.state_path = env_state_path or "cache/hackmd_state.json"
        self.state_lock = threading.Lock()
        self.state = self._load_state()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @staticmethod
    def _resolve_optional_str(env_value: str, fallback: str | None) -> str | None:
        env_value = (env_value or "").strip()
        if env_value:
            return env_value
        return fallback

    @staticmethod
    def _resolve_note_ids(env_value: str, fallback: list[str] | None) -> list[str] | None:
        env_value = (env_value or "").strip()
        if not env_value:
            return fallback

        note_ids: list[str] = []
        seen: set[str] = set()
        for item in env_value.split(","):
            value = item.strip()
            if not value or value in seen:
                continue
            seen.add(value)
            note_ids.append(value)
        return note_ids

    @staticmethod
    def _resolve_int(env_value: str, fallback: int, label: str) -> int:
        env_value = (env_value or "").strip()
        if not env_value:
            return fallback
        try:
            return int(env_value)
        except ValueError:
            log.warning("Invalid %s=%r, using fallback=%s", label, env_value, fallback)
            return fallback

    @staticmethod
    def _resolve_float(env_value: str, fallback: float, label: str) -> float:
        env_value = (env_value or "").strip()
        if not env_value:
            return fallback
        try:
            return float(env_value)
        except ValueError:
            log.warning("Invalid %s=%r, using fallback=%s", label, env_value, fallback)
            return fallback

    def _load_state(self) -> dict:
        try:
            with open(self.state_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except Exception as e:
            self.log.warning(f"Failed to load state file {self.state_path}: {e}")
            return {}

    def _save_state(self):
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
            with self.state_lock:
                with open(self.state_path, "w") as f:
                    json.dump(self.state, f, indent=2, default=str)
        except Exception as e:
            self.log.warning(f"Failed to write state file {self.state_path}: {e}")

    def _state_key(self, note: HackMDNoteObject) -> str:
        # Use workspace/note_id if available for uniqueness; else note_id
        return f"{note.workspace_id}/{note.note_id}" if note.workspace_id else note.note_id

    def start(self):
        if self._thread and self._thread.is_alive():
            self.log.debug("HackMD ingestion service already running")
            return

        poll_interval = self.poll_interval
        self.log.info(f"HackMD ingestion service starting; interval={poll_interval}s")

        self._stop_event.clear()

        def _run():
            self.log.info("HackMD ingestion started")
            while not self._stop_event.is_set():
                start = time.time()
                try:
                    self.poll_once()
                except Exception as e:
                    self.log.error(f"Ingestion poll failed: {e}")
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
        notes = self.client.get_notes(limit=self.max_notes_per_poll)

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
            self.log.info(f"Processed {processed} HackMD notes")
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
            self.log.debug(f"Queued bundle for {note_rid}")
        except Exception as e:
            self.log.error(f"Failed to process note {note_rid}: {e}")
