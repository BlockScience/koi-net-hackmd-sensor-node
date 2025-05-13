import logging
from koi_net.processor.handler import HandlerType, STOP_CHAIN
from koi_net.processor.knowledge_object import KnowledgeSource, KnowledgeObject
from koi_net.processor.interface import ProcessorInterface
from koi_net.protocol.event import EventType
from koi_net.protocol.edge import EdgeType, EdgeProfile, EdgeStatus
from koi_net.protocol.node import NodeProfile
from koi_net.protocol.helpers import generate_edge_bundle
from rid_lib.ext import Bundle
from rid_lib.types import KoiNetNode, KoiNetEdge

from rid_types import HackMDNote
from .core import node
from . import hackmd_api

logger = logging.getLogger(__name__)


@node.processor.register_handler(HandlerType.Network, rid_types=[KoiNetNode])
def coordinator_contact(processor: ProcessorInterface, kobj: KnowledgeObject):
    # when I found out about a new node
    if kobj.normalized_event_type != EventType.NEW: 
        return
    
    node_profile = kobj.bundle.validate_contents(NodeProfile)
    
    # looking for event provider of nodes
    if KoiNetNode not in node_profile.provides.event:
        return
    
    logger.info("Identified a coordinator for network discovery!")
    logger.info("Proposing bidirectional edges for network discovery...")
    
    # First edge proposal - FROM Coordinator TO Sensor (existing)
    processor.handle(bundle=generate_edge_bundle(
        source=kobj.rid,
        target=node.identity.rid,
        edge_type=EdgeType.WEBHOOK,
        rid_types=[KoiNetNode]
    ))
    
    # Second edge proposal - FROM Sensor TO Coordinator (critical for discovery)
    processor.handle(bundle=generate_edge_bundle(
        source=node.identity.rid,
        target=kobj.rid,
        edge_type=EdgeType.WEBHOOK,
        rid_types=[KoiNetNode, HackMDNote]  # Include both KoiNetNode and HackMDNote
    ))
    
    logger.info(f"Proposed two edges for bidirectional communication with Coordinator {kobj.rid}")
    
    logger.info("NETWORK SETUP: Catching up on network state...")
    
    rid_payload = processor.network.request_handler.fetch_rids(kobj.rid, rid_types=[KoiNetNode])
        
    rids = [
        rid for rid in rid_payload.rids 
        if rid != processor.identity.rid and 
        not processor.cache.exists(rid)
    ]
    
    logger.info(f"NETWORK SETUP: Found {len(rids)} network nodes to fetch from coordinator")
    
    bundle_payload = processor.network.request_handler.fetch_bundles(kobj.rid, rids=rids)
    
    for bundle in bundle_payload.bundles:
        # marked as external since we are handling RIDs from another node
        # will fetch remotely instead of checking local cache
        logger.info(f"NETWORK SETUP: Processing network node bundle for {bundle.rid}")
        processor.handle(bundle=bundle, source=KnowledgeSource.External)
    logger.info("NETWORK SETUP: Network initialization completed")


@node.processor.register_handler(HandlerType.Manifest)
def custom_manifest_handler(processor: ProcessorInterface, kobj: KnowledgeObject):
    if type(kobj.rid) == HackMDNote:
        logger.debug("Skipping HackMD note manifest handling")
        return kobj
    
    prev_bundle = processor.cache.read(kobj.rid)

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
    
    
@node.processor.register_handler(HandlerType.Bundle, rid_types=[HackMDNote])
def custom_hackmd_bundle_handler(processor: ProcessorInterface, kobj: KnowledgeObject):
    assert type(kobj.rid) == HackMDNote

    # Guard against missing summary keys
    if 'lastChangedAt' not in kobj.contents:
        logger.error(f"Bundle missing 'lastChangedAt' for RID {kobj.rid}. Aborting.")
        return STOP_CHAIN
    if 'content' not in kobj.contents or kobj.contents.get('content') is None:
        logger.error(f"Bundle missing or empty 'content' for RID {kobj.rid}. Aborting.")
        return STOP_CHAIN

    prev_bundle = processor.cache.read(kobj.rid)
    
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
    data = hackmd_api.request(f"/notes/{kobj.rid.note_id}")
    
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


@node.processor.register_handler(
    handler_type=HandlerType.Bundle,
    rid_types=[KoiNetEdge],
    source=KnowledgeSource.External, 
    event_types=[EventType.NEW]
)
def handle_incoming_edge_proposal(processor: ProcessorInterface, kobj: KnowledgeObject):
    logger.info(f"Sensor: BH - Received NEW KoiNetEdge proposal {kobj.rid}")

    if not kobj.contents:
        logger.error(f"Sensor: BH - KoiNetEdge KObj {kobj.rid} has no contents even at Bundle stage. This is unexpected. KObj: {kobj!r}")
        return STOP_CHAIN

    try:
        edge_profile = EdgeProfile.model_validate(kobj.contents)
    except Exception as e:
        logger.error(f"Sensor: BH - Error validating EdgeProfile for {kobj.rid}: {e}. KObj: {kobj!r}", exc_info=True)
        return STOP_CHAIN

    # Automatically accepting all edge proposals for HackMDNote subscriptions
    if HackMDNote in edge_profile.rid_types:
        logger.info(f"Sensor: BH - Automatically approving edge {edge_profile.source} -> {edge_profile.target} for HackMDNote")
        
        # Log network graph state for debugging
        logger.info(f"NETWORK GRAPH STATE: Known nodes: {[n for n in processor.network_graph.nodes]}")
        
        # Add small delay to give network discovery time to complete
        import time
        logger.info(f"DELAY: Waiting 2 seconds before approval to allow network graph to update...")
        time.sleep(2)
        
        edge_profile.status = EdgeStatus.APPROVED
        
        # Re-queue this approved edge as an INTERNAL UPDATE event
        update_bundle = Bundle(
            rid=kobj.rid,
            contents=edge_profile.model_dump(),
            timestamp=kobj.bundle.timestamp,
        )
        
        processor.handle(bundle=update_bundle, source=KnowledgeSource.Internal, event_type=EventType.UPDATE)
        
        logger.info(f"Sensor: BH - Requeued APPROVED edge {kobj.rid} with source={KnowledgeSource.Internal}")
        
        # Check if we have the required nodes in the network graph
        target_node = edge_profile.source
        if target_node not in processor.network_graph.nodes:
            logger.warning(f"Sensor: BH - IMPORTANT: Target node {target_node} is not in our network graph!")
        
        return STOP_CHAIN

    return
