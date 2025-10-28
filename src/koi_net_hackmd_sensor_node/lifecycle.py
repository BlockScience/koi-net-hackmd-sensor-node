import logging
import asyncio
from koi_net.lifecycle import NodeLifecycle
from rid_lib.ext import Bundle
from rid_types import HackMDNote
from .hackmd_api import HackMDClient

logger = logging.getLogger(__name__)


class CustomNodeLifecycle(NodeLifecycle):
    async def backfill(self):
        hackmd = HackMDClient(self.config.env.hackmd_api_token)
        notes = await hackmd.async_request(
            f"/teams/{self.config.hackmd.team_path}/notes")
    
        logger.debug(f"Found {len(notes)} in team")

        for note in notes:
            note_rid = HackMDNote(note["id"])
            
            note_bundle = Bundle.generate(
                rid=note_rid,
                contents=note
            )
            
            self.processor.handle(bundle=note_bundle)
    
    async def backfill_loop(self):
        while True:
            await self.backfill()
            await asyncio.sleep(600)
    
    def start(self):
        super().start()
        asyncio.create_task(
            self.backfill_loop()
        )