#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="$(basename -- "$SCRIPT_DIR")"
PARENT_DIR="$(dirname -- "$SCRIPT_DIR")"
OUTPUT_DIR="$SCRIPT_DIR/dist"
OUTPUT_FILE="$OUTPUT_DIR/${PROJECT_NAME}_entrega.zip"

if ! command -v zip >/dev/null 2>&1; then
    echo "Error: the 'zip' command is not installed." >&2
    echo "On Debian/Ubuntu, install it with: sudo apt install zip" >&2
    exit 1
fi

mkdir -p "$OUTPUT_DIR"
rm -f "$OUTPUT_FILE"

echo "Creating Windows-compatible ZIP: $OUTPUT_FILE"

(
    cd "$PARENT_DIR"
    zip -9 -r "$OUTPUT_FILE" "$PROJECT_NAME" \
        -x "$PROJECT_NAME/.git/*" \
        -x "$PROJECT_NAME/.internal/*" \
        -x "$PROJECT_NAME/.venv/*" \
        -x "$PROJECT_NAME/venv/*" \
        -x "$PROJECT_NAME/*/.venv/*" \
        -x "$PROJECT_NAME/*/venv/*" \
        -x "$PROJECT_NAME/*/__pycache__/*" \
        -x "$PROJECT_NAME/*.pyc" \
        -x "$PROJECT_NAME/*.pyo" \
        -x "$PROJECT_NAME/.pytest_cache/*" \
        -x "$PROJECT_NAME/*/.pytest_cache/*" \
        -x "$PROJECT_NAME/dist/*" \
        -x "$PROJECT_NAME/*.zip"
)

echo "ZIP created successfully: $OUTPUT_FILE"
