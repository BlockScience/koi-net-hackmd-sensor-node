from koi_net.config.full_node import (
    FullNodeConfig,
    KoiNetConfig,
    NodeProfile,
    NodeProvides,
    ServerConfig
)
from koi_net.config.base import EnvConfig
from pydantic import BaseModel, Field
from rid_lib.types import KoiNetNode, HackMDNote


class HackMDEnvConfig(EnvConfig):
    hackmd_api_token: str

class HackMDConfig(BaseModel):
    workspace_id: str | None = None
    note_ids: list[str] | None = ["-3EahWEbQQe3TB6THIywLA"]
    poll_interval_seconds: int = 300
    max_notes_per_poll: int = 100
    state_path: str = "./state/hackmd_state.json"
    retries: int = 3
    backoff_base_seconds: float = 1.0
    backoff_max_seconds: float = 10.0

class HackMDSensorConfig(FullNodeConfig):
    hackmd: HackMDConfig = Field(default_factory=HackMDConfig)
    server: ServerConfig = ServerConfig(port=8001)
    koi_net: KoiNetConfig = KoiNetConfig(
        node_name="hackmd_sensor",
        node_profile=NodeProfile(
            provides=NodeProvides(
                event=[HackMDNote, KoiNetNode],
                state=[HackMDNote, KoiNetNode]
            ),
        ),
        rid_types_of_interest=[KoiNetNode]
    )
    env: HackMDEnvConfig = Field(default_factory=HackMDEnvConfig)
