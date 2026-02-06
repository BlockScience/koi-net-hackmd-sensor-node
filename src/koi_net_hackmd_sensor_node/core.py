from koi_net.core import FullNode

from . import handlers
from .config import HackMDSensorConfig
from .ingestion import HackMDIngestionService


class HackMDSensorNode(FullNode):
    config_schema = HackMDSensorConfig
    knowledge_handlers = FullNode.knowledge_handlers + handlers.knowledge_handlers
    ingestion_service: HackMDIngestionService = HackMDIngestionService
