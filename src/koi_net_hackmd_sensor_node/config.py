from pydantic import BaseModel
from koi_net.config.full_node import FullNodeConfig, KoiNetConfig, NodeProfile, NodeProvides
from koi_net.config.core import EnvConfig
from rid_lib.types import HackMDNote


class HackMDConfig(BaseModel):
    team_path: str = "blockscience"

class HackMDEnvConfig(EnvConfig):
    hackmd_api_token: str = "HACKMD_API_TOKEN"

class HackMDSensorNodeConfig(FullNodeConfig):
    koi_net: KoiNetConfig = KoiNetConfig(
        node_name="hackmd-sensor",
        node_profile=NodeProfile(
            provides=NodeProvides(
                event=[HackMDNote],
                state=[HackMDNote]
            )
        )
    )
    env: HackMDEnvConfig = HackMDEnvConfig()
    hackmd: HackMDConfig = HackMDConfig()