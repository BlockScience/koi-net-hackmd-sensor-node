from pydantic import BaseModel, Field
from koi_net.protocol.node import NodeProfile, NodeType, NodeProvides
from koi_net.config import NodeConfig, EnvConfig, KoiNetConfig
from rid_types import HackMDNote

class HackMDConfig(BaseModel):
    team_path: str | None = "blockscience"

class HackMDEnvConfig(EnvConfig):
    hackmd_api_token: str | None = "HACKMD_API_TOKEN"

class HackMDSensorNodeConfig(NodeConfig):
    koi_net: KoiNetConfig | None = Field(default_factory = lambda: 
        KoiNetConfig(
            node_name="hackmd-sensor",
            node_profile=NodeProfile(
                node_type=NodeType.FULL,
                provides=NodeProvides(
                    event=[HackMDNote],
                    state=[HackMDNote]
                )
            )
        )
    )
    env: HackMDEnvConfig | None = Field(default_factory=HackMDEnvConfig)
    hackmd: HackMDConfig | None = Field(default_factory=HackMDConfig)