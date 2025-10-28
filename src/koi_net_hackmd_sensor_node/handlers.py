import logging
from koi_net.processor.handler import HandlerType, STOP_CHAIN
from koi_net.processor.knowledge_object import KnowledgeObject
from koi_net.protocol.event import EventType
from koi_net.context import HandlerContext
from rid_lib.ext import Bundle

from rid_types import HackMDNote
from .core import node
from .hackmd_api import HackMDClient

logger = logging.getLogger(__name__)


@node.pipeline.register_handler(HandlerType.Manifest)
def custom_manifest_handler(ctx: HandlerContext, kobj: KnowledgeObject):
    if type(kobj.rid) == HackMDNote:
        logger.debug("Skipping HackMD note manifest handling")
        return
    
    prev_bundle = ctx.cache.read(kobj.rid)

    if prev_bundle:
        if kobj.manifest.sha256_hash == prev_bundle.manifest.sha256_hash:
            logger.debug("Hash of incoming manifest is same as existing knowledge, ignoring")
            return STOP_CHAIN
        if kobj.manifest.timestamp <= prev_bundle.manifest.timestamp:
            logger.debug("Timestamp of incoming manifest is the same or older than existing knowledge, ignoring")
            return STOP_CHAIN
        
        logger.debug("RID previously known to me, labeling as 'UPDATE'")
        kobj.normalized_event_type = EventType.UPDATE

    else:
        logger.debug("RID previously unknown to me, labeling as 'NEW'")
        kobj.normalized_event_type = EventType.NEW
        
    return kobj
    
    
@node.pipeline.register_handler(HandlerType.Bundle, rid_types=[HackMDNote])
def custom_hackmd_bundle_handler(ctx: HandlerContext, kobj: KnowledgeObject):
    hackmd = HackMDClient(ctx.config.env.hackmd_api_token)
    
    prev_bundle = ctx.cache.read(kobj.rid)
    
    if prev_bundle:
        prevChangedAt = prev_bundle.contents["lastChangedAt"]
        currChangedAt = kobj.contents["lastChangedAt"]
        logger.debug(f"Changed at {prevChangedAt} -> {currChangedAt}")
        if currChangedAt > prevChangedAt:
            logger.debug("Incoming note has been changed more recently!")
            kobj.normalized_event_type = EventType.UPDATE
            
        else:
            logger.debug("Incoming note is not newer")
            return STOP_CHAIN
        
    else:
        logger.debug("Incoming note is previously unknown to me")
        kobj.normalized_event_type = EventType.NEW
        
    logger.debug("Retrieving full note...")
    
    data = hackmd.request(f"/notes/{kobj.rid.note_id}")
    
    if not data:
        logger.debug("Failed.")
        return STOP_CHAIN
    
    logger.debug("Done.")
    
    full_note_bundle = Bundle.generate(
        rid=kobj.rid,
        contents=data
    )
    
    kobj.manifest = full_note_bundle.manifest
    kobj.contents = full_note_bundle.contents
    
    return kobj