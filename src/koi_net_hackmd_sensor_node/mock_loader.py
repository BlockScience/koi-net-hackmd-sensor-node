#!/usr/bin/env python3
"""
Mock data loader for HackMD Sensor Node.

Loads JSON files and processes them through the existing _process_note method.
"""

import json
import os
import re
from pathlib import Path

import structlog
from rid_lib.ext import Bundle
from rid_lib.types import HackMDNote


log = structlog.stdlib.get_logger()


class HackMDMockLoader:
    """Loads mock HackMD note data by processing JSON files."""
    
    def __init__(
        self,
        mock_data_path: str,
        kobj_queue,
        log=None,
    ):
        self.mock_data_path = Path(mock_data_path)
        self.kobj_queue = kobj_queue
        self.log = log or structlog.stdlib.get_logger()
    
    def _extract_note_id_from_orn(self, orn: str) -> str:
        match = re.match(r"orn:hackmd\.note:([a-f0-9]+)", orn)
        if match:
            return match.group(1)
        raise ValueError(f"Invalid HackMD ORN: {orn}")
    
    def load_all(self):
        """Load all mock JSON files and process them."""
        if not self.mock_data_path.exists():
            self.log.warning(f"Mock data path does not exist: {self.mock_data_path}")
            return 0
        
        loaded = 0
        for filepath in self.mock_data_path.glob("*.json"):
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)
                
                contents = data.get("contents", {})
                manifest_rid = data.get("manifest", {}).get("rid", "")
                
                note_id = self._extract_note_id_from_orn(manifest_rid)
                workspace_id = contents.get("team_path") or contents.get("workspace_id")
                
                note_rid = HackMDNote(note_id, workspace_id)
                bundle = Bundle.generate(rid=note_rid, contents=contents)
                
                self.kobj_queue.push(bundle=bundle)
                self.log.debug(f"Queued mock HackMD note: {note_rid}")
                loaded += 1
                
            except Exception as e:
                self.log.error(f"Failed to load {filepath.name}: {e}")
        
        self.log.info(f"Loaded {loaded} mock HackMD notes")
        return loaded
