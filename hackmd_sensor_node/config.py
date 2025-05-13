import json
import logging
from pydantic import BaseModel, Field
from koi_net.protocol.node import NodeProfile, NodeType, NodeProvides
from koi_net.config import NodeConfig, EnvConfig, KoiNetConfig
from rid_types import HackMDNote
from pathlib import Path
from typing import Dict

# Define StateType here to avoid circular import
StateType = Dict[str, str]

logger = logging.getLogger(__name__)

HACKMD_STATE_FILE_PATH = Path(".koi/hackmd/hackmd_state.json")

class HackMDConfig(BaseModel):
    team_path: str | None = "blockscience"
    target_note_ids: list[str] | None = None

class HackMDEnvConfig(EnvConfig):
    hackmd_api_token: str | None = "HACKMD_API_TOKEN"

class HackMDSensorNodeConfig(NodeConfig):
    koi_net: KoiNetConfig = Field(default_factory=lambda:
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

# --- State Management Functions ---
def load_hackmd_state() -> StateType:
    """Loads the last modified timestamp state from the JSON file."""
    try:
        HACKMD_STATE_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        if HACKMD_STATE_FILE_PATH.exists():
            with open(HACKMD_STATE_FILE_PATH, "r") as f:
                state_data = json.load(f)
            logger.info(f"Loaded HackMD state from '{HACKMD_STATE_FILE_PATH}': {len(state_data)} notes tracked.")
            return state_data
        else:
            logger.info(f"HackMD state file '{HACKMD_STATE_FILE_PATH}' not found. Starting empty.")
            return {}
    except Exception as e:
        logger.error(f"Error loading HackMD state file '{HACKMD_STATE_FILE_PATH}': {e}", exc_info=True)
        return {}

def save_hackmd_state(state: StateType):
    """Saves the state dictionary to the JSON file."""
    try:
        HACKMD_STATE_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(HACKMD_STATE_FILE_PATH, "w") as f:
            json.dump(state, f, indent=4)
        logger.debug(f"Saved HackMD state to '{HACKMD_STATE_FILE_PATH}'.")
    except Exception as e:
        logger.error(f"Error writing HackMD state file '{HACKMD_STATE_FILE_PATH}': {e}", exc_info=True)
