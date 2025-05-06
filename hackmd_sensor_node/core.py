import logging
from koi_net import NodeInterface
from koi_net.processor.default_handlers import (
    basic_rid_handler,
    edge_negotiation_handler,
    basic_network_output_filter
)
from .config import HackMDSensorNodeConfig

logger = logging.getLogger(__name__)


node = NodeInterface(
    config=HackMDSensorNodeConfig.load_from_yaml("config.yaml"),
    use_kobj_processor_thread=True,
    handlers=[
        basic_rid_handler,
        edge_negotiation_handler,
        basic_network_output_filter
    ]
)

from . import handlers