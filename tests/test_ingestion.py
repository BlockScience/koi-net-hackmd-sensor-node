import json
import types

from koi_net_shared.rid_types import HackMDNote

from koi_net_hackmd_sensor_node.ingestion import HackMDIngestionService


def make_config(tmp_path):
    return types.SimpleNamespace(
        hackmd=types.SimpleNamespace(
            api_token="token",
            workspace_id=None,
            note_ids=None,
            max_notes_per_poll=10,
            poll_interval_seconds=60,
            state_path=str(tmp_path / "state" / "hackmd_state.json"),
        )
    )


def test_poll_once_processes_new_note(tmp_path, fake_node_interface, hackmd_note):
    config = make_config(tmp_path)
    service = HackMDIngestionService(fake_node_interface, config)
    service.client = types.SimpleNamespace(get_notes=lambda limit: [hackmd_note])

    service.poll_once()

    fake_node_interface.processor.handle.assert_called_once()
    args, kwargs = fake_node_interface.processor.handle.call_args
    bundle = kwargs["bundle"]
    assert isinstance(bundle.rid, HackMDNote)
    key = f"{hackmd_note.workspace_id}/{hackmd_note.note_id}" if hackmd_note.workspace_id else hackmd_note.note_id
    assert service.state[key] == hackmd_note.last_changed_at
    state_file = tmp_path / "state" / "hackmd_state.json"
    stored = json.loads(state_file.read_text())
    assert stored


def test_poll_once_skips_when_no_change(tmp_path, fake_node_interface, hackmd_note):
    config = make_config(tmp_path)
    service = HackMDIngestionService(fake_node_interface, config)
    key = service._state_key(hackmd_note)
    service.state[key] = hackmd_note.last_changed_at
    service.client = types.SimpleNamespace(get_notes=lambda limit: [hackmd_note])

    service.poll_once()
    fake_node_interface.processor.handle.assert_not_called()
