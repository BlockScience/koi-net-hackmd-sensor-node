import logging
from rid_lib.ext import Bundle
from rid_types import HackMDNote
from . import hackmd_api
from .core import node
from .config import StateType

logger = logging.getLogger(__name__)

async def _process_team_notes(team_path, state):
    processed_count = 0
    bundled_count = 0
    logger.info(f"Processing all notes in team path: '{team_path}'")
    if not team_path:
        logger.error("HackMD team path is not configured. Cannot backfill all team notes.")
        return processed_count, bundled_count
    team_notes = await hackmd_api.async_request(f"/teams/{team_path}/notes")
    if not team_notes:
        logger.warning(f"No notes found or error fetching notes for team '{team_path}'. Backfill ending.")
        return processed_count, bundled_count
    logger.debug(f"Found {len(team_notes)} notes in team summary.")
    for note_summary in team_notes:
        processed_count += 1
        note_id = note_summary.get("id")
        last_modified_str = note_summary.get("lastChangedAt")
        title = note_summary.get("title", f"Note {note_id}")
        if not note_id or not last_modified_str:
            logger.warning(f"Skipping note from team list due to missing ID or lastChangedAt: {note_summary}")
            continue
        if note_id not in state or last_modified_str > state[note_id]:
            logger.info(f"Processing note '{title}' (ID: {note_id}) from team list - New or updated.")
            note_details = hackmd_api.request(f"/notes/{note_id}")
            if not note_details:
                logger.error(f"Failed to fetch details for note ID {note_id} from team list. Skipping.")
                continue
            try:
                rid = HackMDNote(note_id=note_id)
                contents = {
                    "id": note_id,
                    "title": title,
                    "content": note_details.get("content"),
                    "createdAt": note_details.get("createdAt"),
                    "lastChangedAt": note_details.get("lastChangedAt", last_modified_str),
                    "publishLink": note_details.get("publishLink"),
                    "tags": note_details.get("tags", []),
                }
                if contents["content"] is None:
                    logger.error(f"Content missing for note ID {note_id} from team list. Skipping bundle.")
                    continue
                bundle = Bundle.generate(rid=rid, contents=contents)
                logger.debug(f"Making backfill note bundle {rid} from team list available locally.")
                node.processor.handle(bundle=bundle)
                bundled_count += 1
                state[note_id] = contents["lastChangedAt"]
            except Exception as e:
                logger.error(f"Error creating/handling bundle for note {note_id} from team list: {e}", exc_info=True)
        else:
            logger.debug(f"Skipping note '{title}' (ID: {note_id}) from team list - Already up-to-date.")
    return processed_count, bundled_count

def _process_target_notes(target_note_ids, state):
    processed_count = 0
    bundled_count = 0
    logger.info(f"Targeting specific HackMD notes for backfill: {target_note_ids}")
    for note_id in target_note_ids:
        processed_count += 1
        logger.debug(f"Fetching targeted note ID: {note_id}")
        note_details = hackmd_api.request(f"/notes/{note_id}")
        if not note_details:
            logger.warning(f"Could not fetch details for targeted note ID {note_id}. Skipping.")
            continue
        last_modified_str = note_details.get("lastChangedAt")
        title = note_details.get("title", f"Note {note_id}")
        if not last_modified_str:
            logger.warning(f"Skipping targeted note {note_id} ('{title}') due to missing lastChangedAt.")
            continue
        if note_id not in state or last_modified_str > state[note_id]:
            logger.info(f"Processing targeted note '{title}' (ID: {note_id}) - New or updated.")
            try:
                rid = HackMDNote(note_id=note_id)
                contents = {
                    "id": note_id,
                    "title": title,
                    "content": note_details.get("content"),
                    "createdAt": note_details.get("createdAt"),
                    "lastChangedAt": last_modified_str,
                    "publishLink": note_details.get("publishLink"),
                    "tags": note_details.get("tags", []),
                }
                if contents["content"] is None:
                    logger.error(f"Content missing for targeted note ID {note_id}. Skipping bundle.")
                    continue
                bundle = Bundle.generate(rid=rid, contents=contents)
                logger.debug(f"Making backfill targeted note bundle {rid} available locally.")
                node.processor.handle(bundle=bundle)
                bundled_count += 1
                state[note_id] = last_modified_str
            except Exception as e:
                logger.error(f"Error bundling targeted note {note_id}: {e}", exc_info=True)
        else:
            logger.debug(f"Skipping targeted note '{title}' (ID: {note_id}) - Already up-to-date.")
    return processed_count, bundled_count


async def backfill(state: StateType):
    """Fetches notes, compares with state, and bundles new/updated notes."""

    team_path = getattr(node.config.hackmd, 'team_path', "blockscience") # Safer access with default
    target_note_ids = getattr(node.config.hackmd, 'target_note_ids', None)

    logger.info("Starting HackMD backfill.")

    try:
        processed_count = 0
        bundled_count = 0

        # Decide whether to process specific notes or all team notes
        if target_note_ids:
            pc, bc = _process_target_notes(target_note_ids, state)
            processed_count += pc
            bundled_count += bc
        else:
            # Original logic: process all notes in the team
            logger.info(f"Processing all notes in team path: \'{team_path}\'")
            if not team_path:
                logger.error("HackMD team path is not configured. Cannot backfill all team notes.")
                return

            team_notes = await hackmd_api.async_request(f"/teams/{team_path}/notes")
            if not team_notes:
                logger.warning(f"No notes found or error fetching notes for team \'{team_path}\'. Backfill ending.")
                return

            logger.debug(f"Found {len(team_notes)} notes in team summary.")
            for note_summary in team_notes:
                processed_count += 1
                note_id = note_summary.get("id")
                last_modified_str = note_summary.get("lastChangedAt")
                title = note_summary.get("title", f"Note {note_id}")

                if not note_id or not last_modified_str:
                    logger.warning(f"Skipping note from team list due to missing ID or lastChangedAt: {note_summary}")
                    continue

                # Check if note needs processing based on state
                if note_id not in state or last_modified_str > state[note_id]:
                    logger.info(f"Processing note \'{title}\' (ID: {note_id}) from team list - New or updated.")
                    # Fetch full content only when needed
                    note_details = hackmd_api.request(f"/notes/{note_id}")
                    if not note_details:
                        logger.error(f"Failed to fetch details for note ID {note_id} from team list. Skipping.")
                        continue

                    try:
                        rid = HackMDNote(note_id=note_id)
                        contents = {
                            "id": note_id,
                            "title": title,
                            "content": note_details.get("content"),
                            "createdAt": note_details.get("createdAt"),
                            "lastChangedAt": note_details.get("lastChangedAt", last_modified_str),
                            "publishLink": note_details.get("publishLink"),
                            "tags": note_details.get("tags", []),
                        }
                        if contents["content"] is None:
                            logger.error(f"Content missing for note ID {note_id} from team list. Skipping bundle.")
                            continue

                        bundle = Bundle.generate(rid=rid, contents=contents)
                        logger.debug(f"Making backfill note bundle {rid} from team list available locally.")
                        node.processor.handle(bundle=bundle)
                        bundled_count += 1
                        state[note_id] = contents["lastChangedAt"] # Update state with timestamp used

                    except Exception as e:
                        logger.error(f"Error creating/handling bundle for note {note_id} from team list: {e}", exc_info=True)
                else:
                    logger.debug(f"Skipping note \'{title}\' (ID: {note_id}) from team list - Already up-to-date.")

        logger.info(f"HackMD backfill complete. Processed {processed_count} notes, bundled {bundled_count} new/updated notes.")

    except Exception as e:
        logger.error(f"Unexpected error during HackMD backfill: {e}", exc_info=True)
