import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
from koi_net.processor.knowledge_object import KnowledgeSource
from rid_lib.types import KoiNetNode
from koi_net.protocol.api_models import (
    PollEvents,
    FetchRids,
    FetchManifests,
    FetchBundles,
    EventsPayload,
    RidsPayload,
    ManifestsPayload,
    BundlesPayload
)
from koi_net.protocol.consts import (
    BROADCAST_EVENTS_PATH,
    POLL_EVENTS_PATH,
    FETCH_RIDS_PATH,
    FETCH_MANIFESTS_PATH,
    FETCH_BUNDLES_PATH
)

from .core import node
from .backfill import backfill
from .config import load_hackmd_state, save_hackmd_state
from . import hackmd_api


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# --- Updated Backfill Loop ---
async def backfill_loop():
    # Determine sleep duration (e.g., from config or default)
    sleep_duration = 600 # Example: 10 minutes
    # sleep_duration = getattr(node.config.hackmd, 'backfill_interval_seconds', 600) # If added to config

    logger.info(f"HackMD backfill loop starting. Interval: {sleep_duration} seconds.")
    # Load state ONCE before the loop starts continuous updates
    current_state = load_hackmd_state()
    while True:
        try:
            logger.info("Starting periodic HackMD backfill...")
            # Pass the current state map to the backfill function
            await backfill(current_state)
            # Save the potentially modified state after backfill completes
            save_hackmd_state(current_state)
            logger.info("Periodic HackMD backfill completed.")
        except Exception as e:
            logger.error(f"Error during periodic HackMD backfill: {e}", exc_info=True)
        await asyncio.sleep(sleep_duration)

# --- Updated Lifespan Context Manager ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("HackMD Sensor Node: FastAPI application startup...")
    try:
        node.start()
        logger.info(f"KOI-net node {node.identity.rid} started.")
        
        # Network initialization sequence
        logger.info("NETWORK SETUP: Beginning network initialization sequence...")
        
        # Wait a moment before initializing connections
        await asyncio.sleep(1)
        
        # Explicitly initiate coordinator contact if configured
        if hasattr(node.config.koi_net, 'first_contact') and node.config.koi_net.first_contact:
            logger.info(f"NETWORK SETUP: Initiating first contact with coordinator: {node.config.koi_net.first_contact}")
            try:
                # Fetch the coordinator's bundle with retries
                coordinator_bundles = None
                retry_delay = 1
                for attempt in range(1, 4):
                    try:
                        coordinator_bundles = node.network.request_handler.fetch_bundles(
                            url=node.config.koi_net.first_contact,
                            rids=[KoiNetNode.generate("coordinator")]
                        )
                        break
                    except Exception as e:
                        if attempt < 4:
                            logger.warning(f"NETWORK SETUP: Attempt {attempt} to fetch coordinator failed: {e}. Retrying in {retry_delay}s.")
                            await asyncio.sleep(retry_delay)
                            retry_delay *= 2
                        else:
                            logger.error(f"NETWORK SETUP: Failed to fetch coordinator after {attempt} attempts: {e}")
                
                if coordinator_bundles.bundles:
                    coordinator_bundle = coordinator_bundles.bundles[0]
                    logger.info(f"NETWORK SETUP: Received coordinator bundle: {coordinator_bundle.rid}. Queueing for processing.")
                    node.processor.handle(
                        bundle=coordinator_bundle, 
                        source=KnowledgeSource.External
                    )
                    
                    # Give some time for the network to establish
                    await asyncio.sleep(2)
                    
                    # Log network state
                    known_nodes = node.network.graph.list_nodes()
                    logger.info(f"NETWORK SETUP: Known nodes after initialization: {known_nodes}")
                    
                    current_edges = node.network.graph.list_edges()
                    logger.info(f"NETWORK SETUP: Current edges after initialization: {current_edges}")
                else:
                    logger.warning("NETWORK SETUP: Could not fetch coordinator bundle")
            except Exception as e:
                logger.error(f"NETWORK SETUP: Error during network initialization: {e}")
                import traceback
                logger.debug(traceback.format_exc())
            
            logger.info("NETWORK SETUP: Network initialization complete")

        # Initial backfill on startup (optional)
        logger.info("Performing initial HackMD backfill on startup...")
        initial_state = load_hackmd_state()
        # Run initial backfill - pass the state, save after it finishes
        await backfill(initial_state)
        save_hackmd_state(initial_state)
        logger.info("Initial HackMD backfill completed.")

        # Start the periodic backfill loop
        asyncio.create_task(backfill_loop()) # Loop manages its own state loading/saving now

    except Exception as e:
        logger.critical(f"Critical error during HackMD node startup: {e}", exc_info=True)
        raise RuntimeError("Failed to initialize KOI-net node components") from e

    yield # Application runs here

    logger.info("HackMD Sensor Node: FastAPI application shutdown...")
    try:
        node.stop()
        logger.info(f"KOI-net node {node.identity.rid} stopped.")
    except Exception as e:
        logger.error(f"Error stopping KOI-net node: {e}", exc_info=True)
    logger.info("HackMD Sensor Node: Shutdown complete.")


app = FastAPI(
    lifespan=lifespan, 
    title="KOI-net Protocol API",
    version="1.0.0"
)


koi_net_router = APIRouter(
    prefix="/koi-net"
)

@koi_net_router.post(BROADCAST_EVENTS_PATH)
def broadcast_events(req: EventsPayload):
    logger.info(f"Request to {BROADCAST_EVENTS_PATH}, received {len(req.events)} event(s)")
    for event in req.events:
        logger.info(f"{event!r}")
        node.processor.handle(event=event, source=KnowledgeSource.External)
    

@koi_net_router.post(POLL_EVENTS_PATH)
def poll_events(req: PollEvents) -> EventsPayload:
    logger.info(f"Request to {POLL_EVENTS_PATH}")
    events = node.network.flush_poll_queue(req.rid)
    return EventsPayload(events=events)

@koi_net_router.post(FETCH_RIDS_PATH)
def fetch_rids(req: FetchRids) -> RidsPayload:
    return node.network.response_handler.fetch_rids(req)

@koi_net_router.post(FETCH_MANIFESTS_PATH)
def fetch_manifests(req: FetchManifests) -> ManifestsPayload:
    return node.network.response_handler.fetch_manifests(req)

@koi_net_router.post(FETCH_BUNDLES_PATH)
def fetch_bundles(req: FetchBundles) -> BundlesPayload:
    return node.network.response_handler.fetch_bundles(req)


app.include_router(koi_net_router)

@app.get("/health", tags=["System"])
async def health_check():
    """Basic health check for the service."""
    return {"status": "healthy", "node_id": str(node.identity.rid) if node.identity else "uninitialized"}