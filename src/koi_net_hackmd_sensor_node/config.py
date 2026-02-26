import os

from koi_net.config.full_node import (
    FullNodeConfig,
    KoiNetConfig,
    NodeProfile,
    NodeProvides,
    ServerConfig
)
from koi_net.config.core import EnvConfig, NodeContact
from pydantic import BaseModel, Field, model_validator
from rid_lib.types import KoiNetNode, HackMDNote


class HackMDEnvConfig(EnvConfig):
    HACKMD_API_TOKEN: str = "HACKMD_API_TOKEN"
    HACKMD_WORKSPACE_ID: str = "HACKMD_WORKSPACE_ID"
    HACKMD_NOTE_IDS: str = "HACKMD_NOTE_IDS"
    HACKMD_POLL_INTERVAL_SECONDS: str = "HACKMD_POLL_INTERVAL_SECONDS"
    HACKMD_MAX_NOTES_PER_POLL: str = "HACKMD_MAX_NOTES_PER_POLL"
    HACKMD_STATE_PATH: str = "HACKMD_STATE_PATH"
    HACKMD_RETRIES: str = "HACKMD_RETRIES"
    HACKMD_BACKOFF_BASE_SECONDS: str = "HACKMD_BACKOFF_BASE_SECONDS"
    HACKMD_BACKOFF_MAX_SECONDS: str = "HACKMD_BACKOFF_MAX_SECONDS"
    COORDINATOR_RID: str = "COORDINATOR_RID"
    COORDINATOR_URL: str = "COORDINATOR_URL"

class HackMDConfig(BaseModel):
    workspace_id: str | None = None
    note_ids: list[str] | None = None
    poll_interval_seconds: int = 300
    max_notes_per_poll: int = 100
    state_path: str = "./state/hackmd_state.json"
    retries: int = 3
    backoff_base_seconds: float = 1.0
    backoff_max_seconds: float = 10.0

class HackMDSensorConfig(FullNodeConfig):
    hackmd: HackMDConfig = Field(default_factory=HackMDConfig)
    server: ServerConfig = ServerConfig(port=8081)
    koi_net: KoiNetConfig = KoiNetConfig(
        node_name="hackmd_sensor",
        node_profile=NodeProfile(
            provides=NodeProvides(
                event=[HackMDNote],
                state=[HackMDNote, KoiNetNode]
            ),
        ),
        rid_types_of_interest=[KoiNetNode],
        first_contact=NodeContact(url="http://127.0.0.1:8080/koi-net"),
    )
    env: HackMDEnvConfig = Field(default_factory=HackMDEnvConfig)

    @model_validator(mode="after")
    def apply_coordinator_contact_from_env(self):
        coordinator_rid = (os.getenv("COORDINATOR_RID") or "").strip()
        coordinator_url = (os.getenv("COORDINATOR_URL") or "").strip()

        if coordinator_rid:
            self.koi_net.first_contact.rid = KoiNetNode.from_string(coordinator_rid)
        if coordinator_url:
            self.koi_net.first_contact.url = coordinator_url

        return self
