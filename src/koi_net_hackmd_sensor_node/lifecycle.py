import asyncio
from dataclasses import dataclass

from koi_net.core import KobjQueue
from koi_net.build.threaded_component import ThreadedComponent
from rid_lib.ext import Bundle
from rid_lib.types import HackMDNote

from .config import HackMDSensorConfig
from .hackmd_api import HackMDClient

# NOTE: seemingly unused

@dataclass
class CustomNodeLifecycle(ThreadedComponent):
    kobj_queue: KobjQueue
    config: HackMDSensorConfig
    
    async def backfill(self):
        hackmd = HackMDClient(self.config.env.hackmd_api_token)
        notes = await hackmd.async_request(
            f"/teams/{self.config.hackmd.team_path}/notes")

        self.log.debug(f"Found {len(notes)} in team")

        for note in notes:
            note_rid = HackMDNote(note["id"])

            note_bundle = Bundle.generate(
                rid=note_rid,
                contents=note
            )

            self.kobj_queue.push(bundle=note_bundle)
    
    async def backfill_loop(self):
        while True:
            await self.backfill()
            await asyncio.sleep(600)

    def run(self):
        asyncio.run(self.backfill_loop())
