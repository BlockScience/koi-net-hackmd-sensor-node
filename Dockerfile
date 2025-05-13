FROM python:3.12-slim AS build

# Install build dependencies and UV
RUN apt-get update && \
    apt-get install -y build-essential curl && \
    pip install --no-cache-dir uv && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only requirements file first to leverage Docker cache
COPY requirements.txt* ./

# Install dependencies using UV for faster installation
RUN if [ -f "requirements.txt" ]; then \
        uv pip install --system -r requirements.txt; \
    fi

# Final stage
FROM python:3.12-slim

# Accept module name and port as build arguments
ARG MODULE_NAME
ARG PORT=8002

# Set environment variables from build args
ENV PORT=$PORT
ENV MODULE_NAME=hackmd_sensor_node

WORKDIR /app

# Install only runtime dependencies (curl for healthcheck)
RUN apt-get update && \
    apt-get install -y curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy installed dependencies from build stage
COPY --from=build /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY --from=build /usr/local/bin/ /usr/local/bin/

# Copy project files and source code
COPY . /app/

# Expose port for container
EXPOSE $PORT

# Configure healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl --fail http://localhost:$PORT/koi-net/health || exit 1

# Start server using environment variables
# The module name is used to determine which server module to load
CMD uvicorn hackmd_sensor_node.server:app --host 0.0.0.0 --port $PORT
