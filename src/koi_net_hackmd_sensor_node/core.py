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

