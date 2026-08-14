#!/usr/bin/env bash
set -euo pipefail

if [ $# -ne 2 ]; then
  echo "Usage: $0 <spec-git-tag> <path-to-combined-spec-file>"
  exit 1
fi

SPEC_TAG="$1"
SPEC_FILE="$2"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

[ -d "$ROOT_DIR/.generated" ] && rm -rf "$ROOT_DIR/.generated"
mkdir -p "$ROOT_DIR/.generated"

rm -rf "$ROOT_DIR/apple_ads_platform/api"
rm -rf "$ROOT_DIR/apple_ads_platform/models"

openapi-generator-cli generate \
  -i "$SPEC_FILE" \
  -g python \
  -o "$ROOT_DIR/.generated" \
  -t "$ROOT_DIR/generator/templates" \
  -p packageName=apple_ads_platform \
  -p projectName=apple-ads-platform \
  -p hideGenerationTimestamp=true \
  -p disallowAdditionalPropertiesIfNotPresent=false \
  -p enumUnknownDefaultCase=true

mkdir -p "$ROOT_DIR/apple_ads_platform"
cp -a "$ROOT_DIR/.generated/apple_ads_platform/api" "$ROOT_DIR/apple_ads_platform/"
cp -a "$ROOT_DIR/.generated/apple_ads_platform/models" "$ROOT_DIR/apple_ads_platform/"
cp "$ROOT_DIR/.generated/apple_ads_platform/api_client.py" "$ROOT_DIR/apple_ads_platform/"
cp "$ROOT_DIR/.generated/apple_ads_platform/api_response.py" "$ROOT_DIR/apple_ads_platform/"
cp "$ROOT_DIR/.generated/apple_ads_platform/configuration.py" "$ROOT_DIR/apple_ads_platform/"
cp "$ROOT_DIR/.generated/apple_ads_platform/exceptions.py" "$ROOT_DIR/apple_ads_platform/"
cp "$ROOT_DIR/.generated/apple_ads_platform/rest.py" "$ROOT_DIR/apple_ads_platform/"
cp "$ROOT_DIR/.generated/apple_ads_platform/py.typed" "$ROOT_DIR/apple_ads_platform/"
cp "$ROOT_DIR/.generated/apple_ads_platform/__init__.py" "$ROOT_DIR/apple_ads_platform/"

LICENSE_HEADER=$(head -1 "$ROOT_DIR/LICENSE_HEADER.txt")
while IFS= read -r -d '' file; do
  if ! head -5 "$file" | grep -qF "$LICENSE_HEADER"; then
    { echo "$LICENSE_HEADER"; echo ""; cat "$file"; } > "$file.tmp" && mv "$file.tmp" "$file"
  fi
done < <(find "$ROOT_DIR/apple_ads_platform" -name "*.py" -print0)

PREV_SPEC_TAG=$(cat "$ROOT_DIR/spec.version" 2>/dev/null || true)
echo "${SPEC_TAG##*-}" > "$ROOT_DIR/spec.version"
if [ "${SPEC_TAG##*-}" != "${PREV_SPEC_TAG##*-}" ]; then
  echo "0" > "$ROOT_DIR/patch.version"
fi

rm -rf "$ROOT_DIR/.generated"