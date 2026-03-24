#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTEST="$SCRIPT_DIR/venv/bin/pytest"

exec "$PYTEST" "$SCRIPT_DIR/tests/" "$@"
