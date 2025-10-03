import pytest
from pydantic import ValidationError

from koi_net_hackmd_sensor_node.models import HackMDNoteObject
from koi_net_shared.rid_types import HackMDNote


def test_hackmd_note_object_parses_payload(hackmd_payload):
    note = HackMDNoteObject(**hackmd_payload)
    assert note.note_id == hackmd_payload["id"]
    assert note.title == hackmd_payload["title"]
    assert note.tags == []
    assert note.publish_type == "view"
    assert "Soma Oil" in note.content
    assert note.created_at == hackmd_payload["createdAt"]
    assert note.last_changed_at == hackmd_payload["lastChangedAt"]


def test_required_fields_validation(hackmd_payload):
    invalid = hackmd_payload.copy()
    invalid.pop("id")
    with pytest.raises(ValidationError):
        HackMDNoteObject(**invalid)


def test_optional_fields_defaults(hackmd_payload):
    minimal = {
        "id": hackmd_payload["id"],
        "title": hackmd_payload["title"],
        "createdAt": hackmd_payload["createdAt"],
        "lastChangedAt": hackmd_payload["lastChangedAt"],
        "titleUpdatedAt": hackmd_payload["titleUpdatedAt"],
        "publishType": hackmd_payload["publishType"],
        "publishLink": hackmd_payload["publishLink"],
        "shortId": hackmd_payload["shortId"],
        "content": hackmd_payload["content"],
        "lastChangeUser": hackmd_payload["lastChangeUser"],
        "userPath": hackmd_payload["userPath"],
    }
    note = HackMDNoteObject(**minimal)
    assert note.tags == []
    assert note.tags_updated_at is None
    assert note.permalink is None


def test_hackmd_note_rid_round_trip(hackmd_payload):
    note = HackMDNoteObject(**hackmd_payload)
    rid = HackMDNote(note_id=note.note_id, workspace_id=note.team_path)
    assert HackMDNote.from_reference(rid.reference).note_id == note.note_id
