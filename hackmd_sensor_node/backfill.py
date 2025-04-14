import logging
import asyncio
from rid_lib.ext import Bundle
from rid_types import HackMDNote
from . import hackmd_api
from .core import node

logger = logging.getLogger(__name__)

async def backfill(team_path="blockscience"):
    notes = await hackmd_api.async_request(f"/teams/{team_path}/notes")
    
    logger.debug(f"Found {len(notes)} in team")

    for note in notes:
        note_rid = HackMDNote(note["id"])
        
        note_bundle = Bundle.generate(
            rid=note_rid,
            contents=note
        )
        
        node.processor.handle(bundle=note_bundle)
        
if __name__ == "__main__":
    node.start()
    asyncio.run(
        backfill()
    )
    node.stop()