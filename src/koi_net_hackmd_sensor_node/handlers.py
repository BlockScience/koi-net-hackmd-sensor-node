import structlog
<<<<<<< HEAD
from koi_net.processor.handler import HandlerType, STOP_CHAIN, KnowledgeObject, HandlerContext, KnowledgeHandler
from koi_net.protocol.event import EventType
from rid_lib.ext import Bundle

from rid_lib.types import HackMDNote
from .hackmd_api import HackMDClient

log = structlog.stdlib.get_logger()


@KnowledgeHandler.create(HandlerType.Manifest)
def custom_manifest_handler(ctx: HandlerContext, kobj: KnowledgeObject):
    if type(kobj.rid) == HackMDNote:
        log.debug("Skipping HackMD note manifest handling")
        return
    
    prev_bundle = ctx.cache.read(kobj.rid)

    if prev_bundle:
        if kobj.manifest.sha256_hash == prev_bundle.manifest.sha256_hash:
            log.debug("Hash of incoming manifest is same as existing knowledge, ignoring")
            return STOP_CHAIN
        if kobj.manifest.timestamp <= prev_bundle.manifest.timestamp:
            log.debug("Timestamp of incoming manifest is the same or older than existing knowledge, ignoring")
            return STOP_CHAIN
        
        log.debug("RID previously known to me, labeling as 'UPDATE'")
        kobj.normalized_event_type = EventType.UPDATE

    else:
        log.debug("RID previously unknown to me, labeling as 'NEW'")
        kobj.normalized_event_type = EventType.NEW
        
    return kobj
    
    
@KnowledgeHandler.create(HandlerType.Bundle, rid_types=[HackMDNote])
def custom_hackmd_bundle_handler(ctx: HandlerContext, kobj: KnowledgeObject):
    hackmd = HackMDClient(ctx.config.env.hackmd_api_token)
    
    prev_bundle = ctx.cache.read(kobj.rid)
    
    if prev_bundle:
        prevChangedAt = prev_bundle.contents["lastChangedAt"]
        currChangedAt = kobj.contents["lastChangedAt"]
        log.debug(f"Changed at {prevChangedAt} -> {currChangedAt}")
        if currChangedAt > prevChangedAt:
            log.debug("Incoming note has been changed more recently!")
            kobj.normalized_event_type = EventType.UPDATE
            
        else:
            log.debug("Incoming note is not newer")
            return STOP_CHAIN
        
    else:
        log.debug("Incoming note is previously unknown to me")
        kobj.normalized_event_type = EventType.NEW
        
    log.debug("Retrieving full note...")
    
    data = hackmd.request(f"/notes/{kobj.rid.note_id}")
    
    if not data:
        log.debug("Failed.")
        return STOP_CHAIN
    
    log.debug("Done.")
    
    full_note_bundle = Bundle.generate(
        rid=kobj.rid,
        contents=data
    )
    
    kobj.manifest = full_note_bundle.manifest
    kobj.contents = full_note_bundle.contents
    
    return kobj
=======
from rid_lib.ext import Bundle
from koi_net_shared import HackMDNote
from koi_net.processor.context import HandlerContext
from koi_net.processor.handler import HandlerType, KnowledgeHandler, STOP_CHAIN
from koi_net.processor.knowledge_object import KnowledgeObject
from .models import HackMDNoteObject

log = structlog.stdlib.get_logger()

@KnowledgeHandler.create(
    HandlerType.Bundle,
    rid_types=[HackMDNote]
)
def hackmd_bundle_handler(ctx: HandlerContext, kobj: KnowledgeObject):
    log.debug("hackmd_bundle_handler: entry rid=%r event=%s source=%r", kobj.rid, kobj.event_type, kobj.source)
    """Validate and dedupe HackMD note bundles using `last_changed_at`.

    If a previous bundle exists and the incoming `last_changed_at` is not strictly newer,
    stop the handler chain to avoid redundant writes and broadcasts.
    """

    try:
        hackmd_data = HackMDNoteObject.model_validate(kobj.contents or {})
    except Exception as e:
        import traceback
        log.warning("Invalid HackMDNoteObject payload for %s: %s\nTRACE=\n%s", kobj.rid, e, traceback.format_exc())
        return STOP_CHAIN

    prev_bundle = ctx.cache.read(kobj.rid)
    if prev_bundle:
        try:
            prev_data = HackMDNoteObject.model_validate(prev_bundle.contents)
            current_timestamp = hackmd_data.last_changed_at
            prev_timestamp = prev_data.last_changed_at
            
            if current_timestamp and prev_timestamp:
                if current_timestamp <= prev_timestamp:
                    log.debug("Skipping stale/no-op HackMDNote for %s (incoming <= cached)", kobj.rid)
                    return STOP_CHAIN
        except Exception:
            # If previous payload cannot be parsed, fall through and allow write
            pass

    log.debug("Accepting HackMD note: %s (chars=%d)", getattr(hackmd_data, "title", None), len(hackmd_data.content or ""))

# Intentionally omit auto-negotiation beyond KOI default handlers to keep
# the sensor focused on emitting HackMDNote. Downstream consumers should
# subscribe explicitly to this sensor's events.

@KnowledgeHandler.create(
    HandlerType.Final,
    rid_types=[HackMDNote]
)
def logging_handler(ctx: HandlerContext, kobj: KnowledgeObject):
    """Log processed knowledge objects"""
    log.info(f"Processed {type(kobj.rid).__name__}: {kobj.rid}")


# Export handlers for HackMDSensorNode class
knowledge_handlers = [
    hackmd_bundle_handler,
    logging_handler,
]
>>>>>>> dev
