import logging
from koi_net import NodeInterface
from koi_net.processor.default_handlers import (
    basic_rid_handler,
    secure_profile_handler,
    edge_negotiation_handler,
    coordinator_contact,
    basic_network_output_filter,
    forget_edge_on_node_deletion
)

from .config import HackMDSensorNodeConfig
from .lifecycle import CustomNodeLifecycle

logger = logging.getLogger(__name__)


node = NodeInterface(
    config=HackMDSensorNodeConfig.load_from_yaml("config.yaml"),
    use_kobj_processor_thread=True,
    handlers=[
        basic_rid_handler,
        secure_profile_handler,
        edge_negotiation_handler,
        coordinator_contact,
        basic_network_output_filter,
        forget_edge_on_node_deletion
    ],
    NodeLifecycleOverride=CustomNodeLifecycle
)

from . import handlers