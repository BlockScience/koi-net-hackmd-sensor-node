import logging
from rid_types import HackMDNote
from koi_net import NodeInterface
from koi_net.protocol.node import NodeProfile, NodeType, NodeProvides
from koi_net.processor.default_handlers import (
    basic_rid_handler,
    edge_negotiation_handler,
    basic_network_output_filter
)
from .config import URL, FIRST_CONTACT

logger = logging.getLogger(__name__)


node = NodeInterface(
    name="hackmd-sensor",
    profile=NodeProfile(
        base_url=URL,
        node_type=NodeType.FULL,
        provides=NodeProvides(
            event=[HackMDNote],
            state=[HackMDNote]
        )
    ),
    use_kobj_processor_thread=True,
    first_contact=FIRST_CONTACT,
    handlers=[
        basic_rid_handler,
        edge_negotiation_handler,
        basic_network_output_filter
    ]
)

from . import handlers