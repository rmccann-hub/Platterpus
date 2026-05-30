#!/usr/bin/env bash
# Post-clone setup for Whipper GUI development.
#
# Run this once after cloning the repo. It creates a Python virtual
# environment in .venv/, upgrades pip, and installs the package in
# editable mode so changes to src/whipper_gui/ are picked up live.
#
# Usage:
#   bash dev-setup.sh             # set up venv + install runtime deps
#   bash dev-setup.sh --dev       # also install pytest (for running tests)
#
# Re-running is safe — uses an existing .venv if present.

set -euo pipefail

cd "$(dirname "$0")"

# --- Parse args ---
INSTALL_DEV=0
for arg in "$@"; do
    case "$arg" in
        --dev)  INSTALL_DEV=1 ;;
        -h|--help)
            sed -n 's/^# \?//p' "$0" | head -15
            exit 0
            ;;
        *)
            echo "Unknown argument: $arg" >&2
            echo "Use --help for usage." >&2
            exit 1
            ;;
    esac
done

# --- Create venv if missing ---
if [ ! -d .venv ]; then
    echo "Creating virtual environment in .venv/..."
    python3 -m venv .venv
else
    echo "Reusing existing .venv/"
fi

# --- Source and upgrade pip ---
# shellcheck disable=SC1091
source .venv/bin/activate
echo "Upgrading pip in the venv..."
pip install --upgrade pip --quiet

# --- Install the package ---
if [ "$INSTALL_DEV" -eq 1 ]; then
    echo "Installing whipper-gui in editable mode (with dev extras: pytest)..."
    pip install -e ".[dev]"
else
    echo "Installing whipper-gui in editable mode..."
    pip install -e .
fi

# --- Done ---
cat <<EOF

----------------------------------------
Setup complete.

To launch the GUI:
    source .venv/bin/activate
    whipper-gui

Or in one shot, no activation needed:
    .venv/bin/whipper-gui

EOF

if [ "$INSTALL_DEV" -eq 1 ]; then
    cat <<EOF
To run tests:
    source .venv/bin/activate
    pytest

EOF
fi

cat <<EOF
The venv is in .venv/ — to leave it after activation, run \`deactivate\`.
----------------------------------------
EOF
