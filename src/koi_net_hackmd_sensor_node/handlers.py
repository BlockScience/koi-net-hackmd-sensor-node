import structlog
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