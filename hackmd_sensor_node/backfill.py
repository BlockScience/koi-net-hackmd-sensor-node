import logging
from rid_lib.ext import Bundle
from rid_types import HackMDNote
from . import hackmd_api
from .core import node

logger = logging.getLogger(__name__)


def run(team_path="blockscience"):
    notes = hackmd_api.request(f"/teams/{team_path}/notes")
    
    logger.info(f"Found {len(notes)} in team")

    for note in notes:
        note_rid = HackMDNote(note["id"])
        
        note_bundle = Bundle.generate(
            rid=note_rid,
            contents=note
        )
        
        node.processor.handle(bundle=note_bundle)
        
if __name__ == "__main__":
    node.start()
    run()
    node.stop()