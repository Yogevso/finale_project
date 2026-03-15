#!/usr/bin/env bash
# Pull the configured Ollama model into the running Ollama container.
# Usage: ./scripts/pull-ollama-model.sh [model_name]
set -euo pipefail

MODEL="${1:-llama3.1:8b}"
OLLAMA_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
MAX_RETRIES=3
RETRY_DELAY=10

echo "Pulling model '${MODEL}' from Ollama at ${OLLAMA_URL}..."

for i in $(seq 1 "$MAX_RETRIES"); do
    if curl -fsS "${OLLAMA_URL}/api/pull" -d "{\"name\": \"${MODEL}\"}" --max-time 600; then
        echo ""
        echo "Model '${MODEL}' pulled successfully."
        exit 0
    fi
    echo "Attempt ${i}/${MAX_RETRIES} failed. Retrying in ${RETRY_DELAY}s..."
    sleep "$RETRY_DELAY"
done

echo "ERROR: Failed to pull model '${MODEL}' after ${MAX_RETRIES} attempts." >&2
exit 1
