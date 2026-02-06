import httpx
import logging
import time
import random
from datetime import datetime
from typing import List, Dict, Any, Optional

from .models import HackMDNoteObject


def _parse_date_string(date_str: Any) -> Optional[datetime]:
    """
    NOTE: this seems to be currently unused
    
    Parses a date string, handling potential None, int, or empty string values.
    Returns a datetime object or None if parsing fails.
    """
    logger = logging.getLogger(__name__)
    
    if date_str is None:
        return None

    date_str = str(date_str).strip()
    if not date_str:
        return None

    try:
        # Try parsing as a Unix timestamp (milliseconds)
        # Check if it's a string of digits and long enough to be a millisecond timestamp
        if isinstance(date_str, str) and date_str.isdigit() and len(date_str) > 10:
            timestamp_ms = int(date_str)
            return datetime.fromtimestamp(timestamp_ms / 1000)

        # HackMD often returns 'Z' for UTC, which fromisoformat doesn't directly support
        # Replace 'Z' with '+00:00' for proper ISO 8601 parsing
        if date_str.endswith('Z'):
            date_str = date_str.replace('Z', '+00:00')
        return datetime.fromisoformat(date_str)
    except ValueError as e:
        logger.warning(f"Could not parse date string '{date_str}': {e}")
        return None


class HackMDClient:
    def __init__(
        self,
        api_token: str,
        log: logging.Logger = logging.getLogger(__name__),
        workspace_id: str | None = None,
        note_ids: List[str] | None = None,
        retries: int = 3,
        backoff_base: float = 1.0,
        backoff_max: float = 10.0,
    ):
        self.log = log
        self.api_token = api_token
        self.workspace_id = workspace_id
        self.note_ids = note_ids or []
        self.base_url = "https://api.hackmd.io/v1"

        self.retries = max(0, retries)
        self.backoff_base = max(0.1, backoff_base)
        self.backoff_max = max(self.backoff_base, backoff_max)

        # Increase timeouts to reduce read timeouts on large notes
        self.client = httpx.Client(
            headers={"Authorization": f"Bearer {api_token}"},
            timeout=httpx.Timeout(connect=30.0, read=60.0, write=30.0, pool=30.0)
        )

        # Expose headers for testing
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }

    def _get(self, url: str, *, params: Dict[str, Any] | None = None, headers: Dict[str, str] | None = None) -> httpx.Response:
        attempt = 0
        while True:
            try:
                resp = self.client.get(url, params=params, headers=headers)
                if resp.status_code in (429, 500, 502, 503, 504):
                    raise httpx.HTTPStatusError("retryable status", request=resp.request, response=resp)
                return resp
            except (httpx.ConnectError, httpx.ReadError, httpx.TimeoutException, httpx.HTTPStatusError) as e:
                if attempt >= self.retries:
                    self.log.error("GET %s failed after %d retries: %s", url, attempt, e)
                    raise
                delay = min(self.backoff_max, self.backoff_base * (2 ** attempt))
                delay = delay * (0.5 + random.random())  # jitter
                self.log.warning("GET %s failed (%s). retrying in %.2fs", url, type(e).__name__, delay)
                time.sleep(delay)
                attempt += 1

    def get_notes(self, limit: int = 100) -> List[HackMDNoteObject]:
        """Fetch notes from HackMD by note IDs, team workspace, or user account.

        Priority:
        1) If specific note IDs are configured, fetch those notes.
        2) Else if a workspace/team is configured, fetch team notes.
        3) Else fetch notes for the authenticated user.
        """
        # 1) Specific note IDs
        if self.note_ids:
            notes: List[HackMDNoteObject] = []
            for nid in self.note_ids[:limit]:
                note_data = self._fetch_single_note(nid)
                if note_data:
                    notes.append(self._parse_note(note_data))
            return notes

        # 2) Team/workspace notes
        if self.workspace_id:
            endpoint = f"{self.base_url}/teams/{self.workspace_id}/notes"
            params = {"limit": limit}
        else:
            # 3) User notes
            endpoint = f"{self.base_url}/notes"
            params = {"limit": limit}

        response = self._get(endpoint, params=params)
        response.raise_for_status()

        notes: List[HackMDNoteObject] = []
        for note_data in response.json():
            notes.append(self._parse_note(note_data))

        return notes

    def get_note_content(self, note_id: str) -> str:
        """Fetch full content of a specific note"""
        endpoint = f"{self.base_url}/notes/{note_id}"
        response = self._get(endpoint)
        response.raise_for_status()

        # Handle both JSON and text responses for testing compatibility
        try:
            return response.json().get("content", "")
        except Exception:
            return response.text

    def _fetch_single_note(self, note_id: str) -> Dict[str, Any] | None:
        """Fetch a single note's full record by ID (metadata + content)."""
        endpoint = f"{self.base_url}/notes/{note_id}"
        response = self._get(endpoint)
        response.raise_for_status()
        return response.json()

    def _parse_note(self, note_data: Dict[str, Any]) -> HackMDNoteObject:
        """Parse HackMD API response into HackMDNoteObject"""
        # If list endpoint was used, it lacks content; enrich via single note fetch
        content = note_data.get("content")
        if content is None and note_data.get("id"):
            try:
                content = self.get_note_content(note_data["id"]) or ""
            except Exception as e:
                self.log.warning(f"Failed to fetch content for note {note_data.get('id')}: {e}")
                content = ""

        # Determine workspace/team path if present in payload
        workspace = self.workspace_id
        if not workspace:
            workspace = note_data.get("teamPath")

        return HackMDNoteObject.model_validate({
            **note_data,
            "id": note_data["id"],
            "title": note_data.get("title", "Untitled"),
            "content": content,
            "userPath": note_data.get("ownerPath"),  # Map ownerPath to userPath
            "teamPath": workspace
        })
