from koi_net.core import FullNode

from . import handlers
from .config import HackMDSensorConfig
from .ingestion import HackMDIngestionService


class HackMDSensorNode(FullNode):
    config_schema = HackMDSensorConfig
    knowledge_handlers = (
        handlers.PREPEND_HANDLERS
        + FullNode.knowledge_handlers
        + handlers.APPEND_HANDLERS
    )
    ingestion_service: HackMDIngestionService = HackMDIngestionService
