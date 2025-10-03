import logging
from rid_lib.ext import Bundle
from koi_net_shared import HackMDNote
from koi_net.context import HandlerContext
from koi_net.processor.handler import HandlerType, STOP_CHAIN
from koi_net.processor.knowledge_object import KnowledgeObject
from .models import HackMDNoteObject
from .core import node

logger = logging.getLogger(__name__)

@node.pipeline.register_handler(
    HandlerType.Bundle,
    rid_types=[HackMDNote]
)
def hackmd_bundle_handler(ctx: HandlerContext, kobj: KnowledgeObject):
    logger.debug("hackmd_bundle_handler: entry rid=%r event=%s source=%r", kobj.rid, kobj.event_type, kobj.source)
    """Validate and dedupe HackMD note bundles using `last_changed_at`.

    If a previous bundle exists and the incoming `last_changed_at` is not strictly newer,
    stop the handler chain to avoid redundant writes and broadcasts.
    """

    try:
        hackmd_data = HackMDNoteObject.model_validate(kobj.contents or {})
    except Exception as e:
        import traceback
        logger.warning("Invalid HackMDNoteObject payload for %s: %s\nTRACE=\n%s", kobj.rid, e, traceback.format_exc())
        return STOP_CHAIN

    prev_bundle = ctx.cache.read(kobj.rid)
    if prev_bundle:
        try:
            prev_data = HackMDNoteObject.model_validate(prev_bundle.contents)
            current_timestamp = hackmd_data.last_changed_at
            prev_timestamp = prev_data.last_changed_at
            
            if current_timestamp and prev_timestamp:
                if current_timestamp <= prev_timestamp:
                    logger.debug("Skipping stale/no-op HackMDNote for %s (incoming <= cached)", kobj.rid)
                    return STOP_CHAIN
        except Exception:
            # If previous payload cannot be parsed, fall through and allow write
            pass

    logger.debug("Accepting HackMD note: %s (chars=%d)", getattr(hackmd_data, "title", None), len(hackmd_data.content or ""))

# Intentionally omit auto-negotiation beyond KOI default handlers to keep
# the sensor focused on emitting HackMDNote. Downstream consumers should
# subscribe explicitly to this sensor's events.

@node.pipeline.register_handler(
    HandlerType.Final,
    rid_types=[HackMDNote]
)
def logging_handler(ctx: HandlerContext, kobj: KnowledgeObject):
    """Log processed knowledge objects"""
    logger.info(f"Processed {type(kobj.rid).__name__}: {kobj.rid}")
