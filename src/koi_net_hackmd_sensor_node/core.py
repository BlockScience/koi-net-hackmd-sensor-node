<<<<<<< HEAD
from koi_net.core import FullNode
from .handlers import custom_manifest_handler, custom_hackmd_bundle_handler

from .config import HackMDSensorNodeConfig
from .lifecycle import CustomNodeLifecycle


class HackMDSensorNode(FullNode):
    config_cls = HackMDSensorNodeConfig
    knowledge_handlers = FullNode.knowledge_handlers + [
        custom_hackmd_bundle_handler
    ]
    lifecycle = CustomNodeLifecycle

=======
import structlog

from koi_net.core import FullNode

from . import handlers
from .config import HackMDSensorConfig
from .ingestion import HackMDIngestionService

log = structlog.stdlib.get_logger()


class HackMDSensorNode(FullNode):
    config_schema = HackMDSensorConfig
    knowledge_handlers = FullNode.knowledge_handlers + handlers.knowledge_handlers
    ingestion_service: HackMDIngestionService = HackMDIngestionService


if __name__ == "__main__":
    HackMDSensorNode().run()
>>>>>>> dev
