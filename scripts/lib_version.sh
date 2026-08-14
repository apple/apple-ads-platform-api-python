#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

SPEC_VERSION="$(cat "$ROOT_DIR/spec.version")"
PATCH_VERSION="$(cat "$ROOT_DIR/patch.version")"

MINOR="${SPEC_VERSION##*-}"

echo "1.${MINOR}.${PATCH_VERSION}"
