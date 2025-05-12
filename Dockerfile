FROM python:3.12-slim

# Accept module name and port as build arguments
ARG MODULE_NAME
ARG PORT=8002

# Set environment variables from build args
ENV PORT=$PORT
ENV MODULE_NAME=hackmd_sensor_node

WORKDIR /app

# Copy project files and source code
COPY . /app/

# Install curl for healthcheck and build dependencies
RUN apt-get update && \
    apt-get install -y curl build-essential && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install dependencies from requirements.txt instead of editable mode
RUN if [ -f "requirements.txt" ]; then \
        pip install --no-cache-dir -r requirements.txt; \
    else \
        echo "No requirements.txt found, installing package directly"; \
        pip install --no-cache-dir .; \
    fi

# Expose port for container
EXPOSE $PORT

# Configure healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl --fail http://localhost:$PORT/koi-net/health || exit 1

# Start server using environment variables
# The module name is used to determine which server module to load
CMD uvicorn hackmd_sensor_node.server:app --host 0.0.0.0 --port $PORT
