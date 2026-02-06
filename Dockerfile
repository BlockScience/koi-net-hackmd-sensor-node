FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy all project files first
COPY . .

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl

# Install dependencies using UV
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system -e .

EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl --fail http://localhost:8002/koi-net/health || exit 1

CMD ["python", "-m", "koi_net_hackmd_sensor_node"]