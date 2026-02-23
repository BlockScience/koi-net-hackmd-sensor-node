# koi-net-hackmd-sensor-node

## Overview
HackMD sensor node that polls notes and emits KOI bundles.

## Prerequisites
- Python 3.10+
- `uv`

## Environment
Create `.env` from `.env.example`:

```bash
cp .env.example .env
```

Required:
- `PRIV_KEY_PASSWORD`
- `HACKMD_API_TOKEN`

Optional runtime targeting/overrides:
- `HACKMD_WORKSPACE_ID`
- `HACKMD_NOTE_IDS` (comma-separated note IDs)
- `HACKMD_POLL_INTERVAL_SECONDS`
- `HACKMD_MAX_NOTES_PER_POLL`
- `HACKMD_STATE_PATH`
- `HACKMD_RETRIES`
- `HACKMD_BACKOFF_BASE_SECONDS`
- `HACKMD_BACKOFF_MAX_SECONDS`

Precedence:
- `.env` overrides are applied first when non-empty.
- If env override is empty, node falls back to `config.yaml` values.

## Quick Start
```bash
uv sync --refresh --reinstall
set -a; source .env; set +a
uv run python -m koi_net_hackmd_sensor_node
```

Expected startup signal: node runs on `127.0.0.1:8001` and logs HackMD polling activity.

## First Contact / Networking
- Default first contact is coordinator: `http://127.0.0.1:8080/koi-net`.
- Default node port: `8001`.

## Config Generation
- `config.yaml` is auto-generated on first run.
- `config.yaml.example` contains all defaults, including env mappings.

## Troubleshooting
- Missing token errors: set `HACKMD_API_TOKEN`.
- No notes processed: verify `HACKMD_WORKSPACE_ID` / `HACKMD_NOTE_IDS`.
- Missing `PRIV_KEY_PASSWORD`: export env before startup.
