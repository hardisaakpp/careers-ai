#!/usr/bin/env bash
# Runs careers-ai on 127.0.0.1:8930. The key is shared with api-careers (CAREERS_AI_KEY there too).
set -euo pipefail
cd "$(dirname "$0")"
export DOCKER_CONTEXT="${CAREERS_AI_DOCKER_CONTEXT:-default}" # the CV is compiled with Docker Engine
export CAREERS_AI_KEY="${CAREERS_AI_KEY:-local-dev-careers-ai-key-0123456789}"
exec .venv/bin/uvicorn careers_ai.api:crear_app --factory --host 127.0.0.1 --port "${CAREERS_AI_PORT:-8930}"
