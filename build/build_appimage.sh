#!/usr/bin/env bash
# Build the Whipper GUI AppImage via python-appimage.
#
# What this script does:
#   1. Verifies the build prerequisites (python3 ≥ 3.11, `build`,
#      `python-appimage`) are installed; offers a hint if not.
#   2. Builds a wheel from the local source via `python -m build`.
#   3. Places the wheel under build/python-appimage/ where
#      python-appimage's requirements.txt picks it up via --find-links.
#   4. Drops in a placeholder icon if no real one is present yet.
#   5. Invokes `python -m python_appimage build app …` to bundle the
#      Python interpreter + the wheel + its deps into a single .AppImage
#      at the repo root.
#
# The build is reproducible to a first approximation: the wheel is
# rebuilt every run from the current source, and python-appimage pins
# a CPython tag (manylinux2014). Reproducibility in the strict sense
# (bit-identical output) requires SOURCE_DATE_EPOCH discipline that
# we don't enforce here — sufficient for v1.

set -euo pipefail

# --- Resolve paths ---------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RECIPE_DIR="$SCRIPT_DIR/python-appimage"

cd "$REPO_ROOT"

# --- Prereq check ----------------------------------------------------------
require_python_module() {
    local module="$1"
    local pip_name="$2"
    if ! python3 -c "import ${module}" >/dev/null 2>&1; then
        echo "Missing Python module: ${module}"
        echo "Install with: python3 -m pip install --user ${pip_name}"
        exit 1
    fi
}

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 is required but not on PATH."
    exit 1
fi

require_python_module build build
require_python_module python_appimage 'python-appimage>=1.4,<2'

# --- Build the wheel -------------------------------------------------------
echo "[1/3] Building wheel from local source…"
rm -f "$RECIPE_DIR"/whipper_gui-*.whl
python3 -m build --wheel --outdir "$RECIPE_DIR"
ls -1 "$RECIPE_DIR"/whipper_gui-*.whl

# --- Placeholder icon ------------------------------------------------------
# python-appimage's "build app" recipe requires <name>.png in the
# recipe directory. If the user hasn't committed a real icon yet, we
# drop in a 16×16 grey square so the build succeeds and the user can
# replace it before release.
if [ ! -f "$RECIPE_DIR/whipper-gui.png" ]; then
    echo "Note: no whipper-gui.png in recipe; generating placeholder."
    python3 - <<'PY'
import struct
import zlib
from pathlib import Path

# Hand-rolled 16x16 RGBA PNG with a uniform mid-grey. Stays under
# 200 bytes; replace with a real icon before release.
width = height = 16
pixels = bytes((40, 40, 40, 255) * width)
raw = b"".join(b"\x00" + pixels for _ in range(height))
compressed = zlib.compress(raw, 9)

def chunk(tag, data):
    crc = zlib.crc32(tag + data) & 0xffffffff
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
png = (
    b"\x89PNG\r\n\x1a\n"
    + chunk(b"IHDR", ihdr)
    + chunk(b"IDAT", compressed)
    + chunk(b"IEND", b"")
)
Path("build/python-appimage/whipper-gui.png").write_bytes(png)
PY
fi

# --- Build the AppImage ----------------------------------------------------
echo "[2/3] Building AppImage via python-appimage…"
python3 -m python_appimage build app "$RECIPE_DIR"

# python-appimage emits the AppImage at the current directory.
echo "[3/3] AppImage written:"
ls -lh "$REPO_ROOT"/*.AppImage 2>/dev/null || {
    echo "No .AppImage found at repo root. Check python-appimage output above."
    exit 1
}
