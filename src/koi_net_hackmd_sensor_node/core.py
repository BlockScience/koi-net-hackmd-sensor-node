from koi_net.core import FullNode

from . import handlers
from .config import HackMDSensorConfig
from .ingestion import HackMDIngestionService


class HackMDSensorNode(FullNode):
    config_schema = HackMDSensorConfig
    suppress_peer_node_rebroadcast_handler = (
        handlers.SuppressPeerNodeRebroadcastHandler
    )
    hackmd_bundle_handler = handlers.HackMDBundleHandler
    hackmd_logging_handler = handlers.HackMDLoggingHandler
    ingestion_service: HackMDIngestionService = HackMDIngestionService
