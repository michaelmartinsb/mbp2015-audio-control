#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"
HOME_VENV_PYTHON="$HOME/venvs/audio-profile-switcher/bin/python"

if [[ -x "$PROJECT_VENV_PYTHON" ]]; then
  exec "$PROJECT_VENV_PYTHON" "$SCRIPT_DIR/audio-profile-switcher.py" "$@"
fi

if [[ -x "$HOME_VENV_PYTHON" ]]; then
  exec "$HOME_VENV_PYTHON" "$SCRIPT_DIR/audio-profile-switcher.py" "$@"
fi

exec python3 "$SCRIPT_DIR/audio-profile-switcher.py" "$@"
