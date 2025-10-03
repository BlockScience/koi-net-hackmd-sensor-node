from pydantic import Field, BaseModel, PrivateAttr
from koi_net_shared import HackMDNote
from koi_net.config import NodeConfig, KoiNetConfig, ServerConfig, NodeContact
from koi_net.protocol.node import NodeProfile, NodeProvides, NodeType
from rid_lib.types import KoiNetNode

import os
from dotenv import load_dotenv


class HackMDConfig(BaseModel):
    workspace_id: str | None = None
    note_ids: list[str] | None = ["-3EahWEbQQe3TB6THIywLA"]
    poll_interval_seconds: int = 300
    max_notes_per_poll: int = 100
    # IMPORTANT: must not live under koi_net.cache_directory_path; rid_lib Cache expects
    # only base64-encoded RID filenames in that directory. Use a separate 'state' dir.
    state_path: str = "./state/hackmd_state.json"
    retries: int = 3
    backoff_base_seconds: float = 1.0
    backoff_max_seconds: float = 10.0

    _api_token: str = PrivateAttr()

    def __init__(self, **data):
        super().__init__(**data)
        load_dotenv()  # Ensure .env is loaded
        self._api_token = os.getenv("HACKMD_API_TOKEN")
        if not self._api_token:
            raise ValueError("HACKMD_API_TOKEN environment variable not set.")

    @property
    def api_token(self) -> str:
        return self._api_token


class HackMDSensorConfig(NodeConfig):
    hackmd: HackMDConfig = Field(default_factory=HackMDConfig)
    server: ServerConfig = Field(default_factory=lambda: ServerConfig(port=8001))
    koi_net: KoiNetConfig = Field(
        default_factory=lambda: KoiNetConfig(
            node_name="hackmd_sensor",
            cache_directory_path=os.getenv("CACHE_DIR", "./cache"),
            event_queues_path=os.getenv("EVENT_QUEUES_FILE", "event_queues.json"),
            private_key_pem_path=os.getenv("PRIVATE_KEY_FILE", "private_key.pem"),
            first_contact=NodeContact(
                url=f"http://{os.getenv('COORDINATOR_HOST', '127.0.0.1')}:8080/koi-net"
            ),
            node_profile=NodeProfile(
                node_type=NodeType.FULL,
                provides=NodeProvides(
                    event=[HackMDNote, KoiNetNode], state=[HackMDNote, KoiNetNode]
                ),
            ),
        )
    )
