import types

import pytest
from rid_lib.ext import Bundle

from koi_net.processor.handler import STOP_CHAIN
from koi_net.processor.knowledge_object import KnowledgeObject
from koi_net.protocol.event import EventType
from koi_net_shared.rid_types import HackMDNote
from koi_net_hackmd_sensor_node.handlers import hackmd_bundle_handler


class DummyCache:
    def __init__(self, entries=None):
        self._entries = entries or {}

    def read(self, rid):
        return self._entries.get(rid)

    def write(self, bundle):
        self._entries[bundle.rid] = bundle


@pytest.fixture
def handler_context():
    cache = DummyCache()
    return types.SimpleNamespace(cache=cache)


def make_bundle(note_data):
    rid = HackMDNote(note_data["id"], note_data.get("teamPath"))
    return Bundle.generate(rid=rid, contents=note_data)


def test_handler_accepts_newer_note(handler_context, hackmd_payload):
    bundle = make_bundle(hackmd_payload)
    kobj = KnowledgeObject.from_bundle(bundle, event_type=EventType.NEW)
    result = hackmd_bundle_handler(handler_context, kobj)
    assert result is None


def test_handler_dedupes_same_timestamp(handler_context, hackmd_payload):
    bundle = make_bundle(hackmd_payload)
    handler_context.cache.write(bundle)
    kobj = KnowledgeObject.from_bundle(bundle, event_type=EventType.UPDATE)
    result = hackmd_bundle_handler(handler_context, kobj)
    assert result is STOP_CHAIN


def test_handler_rejects_invalid_payload(handler_context):
    rid = HackMDNote("note-1", None)
    kobj = KnowledgeObject(rid=rid, contents={"invalid": "data"}, event_type=EventType.NEW)
    result = hackmd_bundle_handler(handler_context, kobj)
    assert result is STOP_CHAIN
