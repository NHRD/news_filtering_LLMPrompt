#!/bin/bash
# RSS News Pipeline launcher
# Loads .env and sets PATH for Gemini CLI before running the pipeline.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load environment variables from .env
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$SCRIPT_DIR/.env"
    set +a
fi

# Add Gemini CLI (installed via nvm) to PATH
export PATH="$HOME/.nvm/versions/node/v22.22.1/bin:$PATH"

# Run the pipeline
exec "$SCRIPT_DIR/venv/bin/python" -m src.main "$@"
