#!/usr/bin/env bash
set -euo pipefail

IMAGE="${1:-noteos-api:latest}"

docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -f backend/Dockerfile \
  -t "$IMAGE" \
  --push \
  backend
