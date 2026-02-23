# koi-net-hackmd-sensor-node

HackMD sensor node implementation for KOI-net.

## Prerequisites

- Python 3.10+
- `uv` installed

## Environment Setup

1. Create environment file:
   `cp .env.example .env`
2. Set values in `.env`:
   - `PRIV_KEY_PASSWORD`
   - `HACKMD_API_TOKEN`

The node config maps `env.HACKMD_API_TOKEN` to the `HACKMD_API_TOKEN` environment variable.

## Configure Node

Edit `config.yaml` as needed:

- `hackmd.workspace_id`
- `hackmd.note_ids`
- `hackmd.poll_interval_seconds`
- `server.host` / `server.port`

## Install Dependencies

```bash
uv sync --refresh --reinstall
```

## Run

```bash
uv run python -m koi_net_hackmd_sensor_node
```

## Notes

- On first run, if `priv_key.pem` does not exist, it is generated automatically.
- If `priv_key.pem` already exists, `PRIV_KEY_PASSWORD` must match the password used when that key was created.
