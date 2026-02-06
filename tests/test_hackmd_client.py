import types

import httpx
import pytest

from koi_net_hackmd_sensor_node.hackmd_client import HackMDClient


class DummyResponse:
    def __init__(self, status=200, json_data=None, text=""):
        self.status_code = status
        self._json = json_data
        self.text = text
        self.request = httpx.Request("GET", "https://api.hackmd.io/v1/notes")

    def json(self):
        if self._json is None:
            raise ValueError("no json")
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=self.request, response=self)


@pytest.fixture
def client():
    return HackMDClient(api_token="token-123", note_ids=["note-1"], retries=1, backoff_base=0.01, backoff_max=0.02)


def test_client_sets_headers(client):
    assert client.headers["Authorization"] == "Bearer token-123"
    assert client.headers["Content-Type"] == "application/json"


def test_get_notes_fetches_specific_ids(monkeypatch, client, hackmd_payload):
    monkeypatch.setattr(client, "_fetch_single_note", lambda note_id: hackmd_payload)
    notes = client.get_notes(limit=5)
    assert len(notes) == 1
    assert notes[0].note_id == hackmd_payload["id"]


def test_get_notes_workspace(monkeypatch, hackmd_payload):
    client = HackMDClient(api_token="token-123", workspace_id="team-1")

    def fake_get(url, params=None, headers=None):
        assert "teams/team-1/notes" in url
        return DummyResponse(json_data=[hackmd_payload])

    monkeypatch.setattr(client, "_get", fake_get)
    monkeypatch.setattr(client, "get_note_content", lambda note_id: hackmd_payload["content"])

    notes = client.get_notes(limit=5)
    assert notes[0].note_id == hackmd_payload["id"]
    assert notes[0].team_path == "team-1"


def test_get_retries_on_timeout(monkeypatch, client, hackmd_payload):
    calls = {"count": 0}

    def fake_sleep(_):
        pass

    def fake_get(url, params=None, headers=None):
        calls["count"] += 1
        if calls["count"] == 1:
            raise httpx.TimeoutException("timeout")
        return DummyResponse(json_data=[hackmd_payload])

    monkeypatch.setattr("time.sleep", fake_sleep)
    monkeypatch.setattr(client, "client", types.SimpleNamespace(get=fake_get))
    resp = client._get("https://api.hackmd.io/v1/notes")
    assert resp.json() == [hackmd_payload]
    assert calls["count"] == 2
