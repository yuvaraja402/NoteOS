#!/usr/bin/env bash
set -euo pipefail

IMAGE="${1:-noteos-api:preview}"
OUTPUT="${2:-/tmp/noteos-api.oci.tar}"

# Local archive only. Registry publication is deliberately disabled.
# Future release builds may replace the output option with --push after review.

docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -f backend/Dockerfile \
  -t "$IMAGE" \
  --output "type=oci,dest=$OUTPUT" \
  backend
