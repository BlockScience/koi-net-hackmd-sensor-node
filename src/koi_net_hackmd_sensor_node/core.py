from koi_net import NodeInterface
from .config import HackMDSensorConfig
from .ingestion import HackMDIngestionService

# Initialize node
node = NodeInterface(
    config=HackMDSensorConfig.load_from_yaml("config.yaml"),
    use_kobj_processor_thread=True,
)

# Initialize ingestion service
ingestion_service = HackMDIngestionService(node, node.config)

# Import handlers after node creation
from . import handlers  # noqa: E402, F401
