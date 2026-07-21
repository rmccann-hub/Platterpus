#!/usr/bin/env bash
# Generate build/python-appimage/requirements.lock — an exact, hash-pinned
# lock of the AppImage's THIRD-PARTY runtime dependencies (the reproducible-
# build "Option A" plumbing; TASKS.md → "Reproducible AppImage build").
#
# Why a separate generator (not part of build_appimage.sh)
# --------------------------------------------------------
# The lock records exact versions + sha256 hashes for PySide6, musicbrainzngs,
# tomli-w AND their full transitive closure (e.g. PySide6 → shiboken6). Those
# hashes are specific to the Python version and platform they were resolved on,
# so the lock MUST be regenerated in the same environment the release build
# runs in (CI: Linux x86_64, the pinned CPython). Running this on a different
# OS/Python would pin the wrong wheels. Keeping generation in its own script
# makes that an explicit, occasional maintainer action — run it only when a
# dependency version in requirements.txt changes — never a silent per-build step.
#
# What consumes the lock
# ----------------------
# build_appimage.sh, when the lock exists, does
#     pip download --require-hashes -r requirements.lock --dest <wheelhouse>
# which re-fetches every wheel and ABORTS if any byte differs from the recorded
# hash (the supply-chain trust gate — defends against PyPI/a mirror serving a
# swapped artifact for a pinned version). It then installs python-appimage's
# deps offline from that verified wheelhouse. Until the lock exists the build
# falls back to today's version-pinned (`~=`) online install, unchanged.
#
# The local `platterpus` wheel is deliberately NOT in the lock: it's our own
# build, its bytes are already pinned by SOURCE_DATE_EPOCH (verified identical
# across rebuilds), and it changes every commit — so it's installed from the
# recipe dir, not hash-gated.
#
# Usage (run from anywhere; resolves its own paths):
#     bash build/lock-requirements.sh
# then review + commit the regenerated build/python-appimage/requirements.lock.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RECIPE_DIR="$SCRIPT_DIR/python-appimage"
REQUIREMENTS="$RECIPE_DIR/requirements.txt"
LOCK_FILE="$RECIPE_DIR/requirements.lock"

if [ ! -f "$REQUIREMENTS" ]; then
    echo "error: $REQUIREMENTS not found" >&2
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "error: python3 is required but not on PATH" >&2
    exit 1
fi

# The third-party deps to lock = every non-comment, non-blank requirements.txt
# line EXCEPT the local `platterpus` wheel (see header). Reading them from the
# single source keeps the lock's inputs from drifting from what the build bundles.
mapfile -t DEPS < <(
    grep -v '^[[:space:]]*#' "$REQUIREMENTS" |
        grep -v '^[[:space:]]*$' |
        grep -vi '^[[:space:]]*platterpus[[:space:]]*$'
)
if [ "${#DEPS[@]}" -eq 0 ]; then
    echo "error: no third-party requirements found to lock" >&2
    exit 1
fi
echo "Locking these third-party requirements (+ their transitive deps):"
printf '  %s\n' "${DEPS[@]}"

# pip's install --report writes a JSON resolution with each resolved dist's
# name, version, and (for PyPI wheels) sha256 — the robust way to build a
# hashed lock without parsing wheel filenames. Needs a reasonably modern pip.
python3 -m pip --version
REPORT="$(mktemp)"
trap 'rm -f "$REPORT"' EXIT

# `download` (not install) so nothing touches the current environment; the
# resolver still walks the full transitive closure. No --only-binary: a dep
# that ships sdist-only (rare for these) is still hash-pinned, which is the
# security goal — wheels-vs-sdist is a reproducibility nuance we accept.
echo "Resolving with pip (this fetches metadata + wheels; PySide6 is large)…"
DL_DIR="$(mktemp -d)"
trap 'rm -f "$REPORT"; rm -rf "$DL_DIR"' EXIT
python3 -m pip download \
    --dest "$DL_DIR" \
    --report "$REPORT" \
    "${DEPS[@]}"

# Turn the report into a hash-pinned requirements file. One entry per resolved
# dist: `name==version --hash=sha256:…` (pip's --require-hashes format).
python3 - "$REPORT" "$LOCK_FILE" <<'PY'
import json
import sys

report_path, lock_path = sys.argv[1], sys.argv[2]
with open(report_path, encoding="utf-8") as fh:
    report = json.load(fh)

entries: list[tuple[str, str, str]] = []
for item in report.get("install", []):
    meta = item.get("metadata", {})
    name = meta.get("name", "")
    version = meta.get("version", "")
    archive = item.get("download_info", {}).get("archive_info", {})
    # Newer pip nests hashes under `hashes`; older exposes a single `hash`.
    sha256 = (archive.get("hashes", {}) or {}).get("sha256", "")
    if not sha256:
        legacy = archive.get("hash", "")  # e.g. "sha256=abc…"
        if legacy.startswith("sha256="):
            sha256 = legacy.split("=", 1)[1]
    if not (name and version and sha256):
        raise SystemExit(
            f"error: pip report is missing name/version/sha256 for {name or item!r} "
            "— cannot write a complete hashed lock (is pip too old, or a dist "
            "served without a sha256?)"
        )
    entries.append((name.lower(), version, sha256))

entries.sort()
lines = [
    "# GENERATED by build/lock-requirements.sh — do not edit by hand.",
    "# Exact, hash-pinned third-party runtime deps for the AppImage build.",
    "# Regenerate (in the release env: Linux x86_64 + the pinned CPython)",
    "# whenever a version in requirements.txt changes. The local `platterpus`",
    "# wheel is intentionally absent (built locally, pinned by SOURCE_DATE_EPOCH).",
    "",
]
for name, version, sha256 in entries:
    lines.append(f"{name}=={version} \\")
    lines.append(f"    --hash=sha256:{sha256}")
with open(lock_path, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")

print(f"Wrote {lock_path} with {len(entries)} hash-pinned dists.")
PY

echo "Done. Review the diff and commit build/python-appimage/requirements.lock."
