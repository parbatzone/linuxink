#!/bin/bash
# LinuxInk - one-shot runner: auto-installs deps, then launches
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$HOME/.local/share/linuxink/venv"

echo "LinuxInk — checking dependencies..."

# ── Create or reuse virtualenv ────────────────────────────────────────────────
if [[ ! -f "$VENV_DIR/bin/python3" ]]; then
    echo "  Setting up virtual environment (first run, ~30 seconds)..."
    mkdir -p "$(dirname "$VENV_DIR")"
    python3 -m venv "$VENV_DIR"
fi

PYTHON="$VENV_DIR/bin/python3"
PIP="$VENV_DIR/bin/pip"

# ── Install PyQt6 if missing ──────────────────────────────────────────────────
if ! "$PYTHON" -c "import PyQt6" 2>/dev/null; then
    echo "  Installing PyQt6 (first run, ~60 seconds)..."
    "$PIP" install --quiet --upgrade pip
    "$PIP" install --quiet PyQt6
    echo "  PyQt6 installed."
fi

echo "  All good — launching..."

# ── Launch with X11 fallback ──────────────────────────────────────────────────
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
export QT_LOGGING_RULES="*.debug=false;qt.qpa.*=false"

cd "$SCRIPT_DIR"
exec "$PYTHON" "$SCRIPT_DIR/main.py" "$@"
