#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -eq 0 ]]; then
    echo "Usage: ./run.sh <script.py> [args...]" >&2
    exit 1
fi

source venv/bin/activate

exec python "$@"
