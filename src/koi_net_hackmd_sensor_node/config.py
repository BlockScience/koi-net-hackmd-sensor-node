<<<<<<< HEAD
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
=======
from pydantic import Field, BaseModel, PrivateAttr
from koi_net_shared import HackMDNote
from koi_net.config.full_node import (
    FullNodeConfig,
    ServerConfig,
    KoiNetConfig,
    NodeProfile,
    NodeProvides
)
from rid_lib.types import KoiNetNode

import os
from dotenv import load_dotenv


class HackMDConfig(BaseModel):
    workspace_id: str | None = None
    note_ids: list[str] | None = ["-3EahWEbQQe3TB6THIywLA"]
    poll_interval_seconds: int = 300
    max_notes_per_poll: int = 100
    state_path: str = "./state/hackmd_state.json"
    retries: int = 3
    backoff_base_seconds: float = 1.0
    backoff_max_seconds: float = 10.0

    _api_token: str = PrivateAttr()

    def __init__(self, **data):
        super().__init__(**data)
        load_dotenv()
        self._api_token = os.getenv("HACKMD_API_TOKEN")
        if not self._api_token:
            raise ValueError("HACKMD_API_TOKEN environment variable not set.")

    @property
    def api_token(self) -> str:
        return self._api_token


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
>>>>>>> dev
