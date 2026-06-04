#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-g42-agentthon}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

docker build -t "$IMAGE_NAME" .
docker run --rm -p 8000:8000 -p 7687:7687 --env-file .env "$IMAGE_NAME"
