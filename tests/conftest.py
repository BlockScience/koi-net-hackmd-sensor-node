import json
import pathlib
from unittest.mock import Mock

import pytest

from koi_net_hackmd_sensor_node.models import HackMDNoteObject

FIXTURE_DIR = pathlib.Path(__file__).parent


@pytest.fixture
def hackmd_payload():
    data = json.loads((FIXTURE_DIR / "hackmd.json").read_text())
    return data


@pytest.fixture
def hackmd_note(hackmd_payload):
    return HackMDNoteObject(**hackmd_payload)


@pytest.fixture
def fake_node_interface():
    node = Mock()
    node.processor.handle = Mock()
    node.request_handler = Mock()
    return node
