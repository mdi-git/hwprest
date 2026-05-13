#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
IMAGE_NAME="${RHWP_PNG_DOCKER_IMAGE:-rhwp-native-skia:latest}"

docker run --rm \
  -v "${PROJECT_ROOT}/rhwp:/workspace/rhwp" \
  -v /tmp:/tmp \
  -w /workspace/rhwp \
  "${IMAGE_NAME}" \
  /bin/bash -c '
    export PATH="/usr/local/cargo/bin:${PATH}"
    cargo build --release --features native-skia
    exec target/release/rhwp "$@"
  ' -- "$@"
