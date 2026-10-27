#!/usr/bin/env bash
# Build the Platterpus AppImage via python-appimage.
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
# Reproducibility: we pin every timestamp the build embeds via
# SOURCE_DATE_EPOCH (below), so two builds of the *same commit* on the same
# toolchain produce byte-identical output — verified for the wheel (identical
# sha256 across runs). The exact dependency *bytes* are pinned too, via a
# hash-verified wheelhouse (see the PIP_FIND_LINKS block below): every
# third-party dep in build/python-appimage/requirements.lock is downloaded with
# `pip --require-hashes` and installed offline, so a swapped artifact for a
# pinned version aborts the build. python-appimage's per-line install is
# respected — pip just resolves from the verified wheelhouse instead of PyPI.
# Regenerate the lock with build/lock-requirements.sh; the build refuses to run
# without it (since 2026-10-27; before, it fell back to an online `~=` install).

set -euo pipefail

# --- Resolve paths ---------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RECIPE_DIR="$SCRIPT_DIR/python-appimage"

cd "$REPO_ROOT"

# --- Reproducible-build timestamp (SOURCE_DATE_EPOCH) ----------------------
# Pin every timestamp the build embeds — the wheel's zip entries and the
# AppImage's squashfs — to one deterministic value, so rebuilding the same
# commit yields identical bytes. Standard convention: the HEAD commit's
# author/commit time. A caller can override by exporting SOURCE_DATE_EPOCH
# themselves (e.g. to reproduce an older release); a git-less source tree
# falls back to the zip epoch floor (1980-01-01, the earliest a zip can store).
if [ -z "${SOURCE_DATE_EPOCH:-}" ]; then
    if command -v git >/dev/null 2>&1 &&
        git -C "$REPO_ROOT" rev-parse HEAD >/dev/null 2>&1; then
        SOURCE_DATE_EPOCH="$(git -C "$REPO_ROOT" log -1 --format=%ct HEAD)"
    else
        SOURCE_DATE_EPOCH=315532800  # 1980-01-01 UTC — zip's minimum timestamp
    fi
fi
export SOURCE_DATE_EPOCH
echo "SOURCE_DATE_EPOCH=$SOURCE_DATE_EPOCH (reproducible-build timestamp)"

# --- Prereq check ----------------------------------------------------------
# The build tools, the build backend and sigstore come from ONE hashed lock,
# build/locks/release.lock, which release.yml and appimage.yml install with
# `pip install --require-hashes` (the 2026-10-27 review, item 2.1's follow-up).
# The spec named on each line below is the range pyproject.toml states (the
# `publish` and `appimage` extras); tests/test_dependency_locks.py holds the two
# equal, and the hint points at the lock rather than at the range.
require_python_module() {
    local module="$1"
    local pip_name="$2"
    if ! python3 -c "import ${module}" >/dev/null 2>&1; then
        echo "Missing Python module: ${module} (${pip_name})"
        echo "Install the release tools with:"
        echo "  python3 -m pip install --require-hashes --only-binary=:all: -r build/locks/release.lock"
        exit 1
    fi
}

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 is required but not on PATH."
    exit 1
fi

require_python_module build 'build>=1.6.1,<1.7'
require_python_module python_appimage 'python-appimage>=1.4.6,<1.5'

# --- Stamp the build fingerprint (see src/platterpus/build_info.py) ---------
# Write a generated _build.py INTO the source tree just before the wheel is
# built, so the packaged app can report exactly which build produced a given
# rip report (the report's generator.build_fingerprint). A plain source
# checkout has no such file and reports the "source" sentinel instead. We use
# the git short-SHA when available (with a "-dirty" suffix for uncommitted
# changes), else a date-derived stamp. The file is removed after the wheel is
# built (it's git-ignored regardless) so it never lands in the working tree.
BUILD_STAMP="$REPO_ROOT/src/platterpus/_build.py"

# ONE cleanup hook for the whole script. There is exactly one `trap … EXIT` in
# bash per signal — a second `trap` REPLACES the first silently — so every
# transient file this script creates is restored from here rather than from its
# own trap. (Written after a second trap was nearly added further down for the
# requirements.txt pin below, which would have left the build stamp in the
# working tree with nothing to notice it.) REQ_BAK is empty until that block
# sets it, so the restore is a no-op before then.
REQ_BAK=""
REQ_SRC=""
cleanup() {
    rm -f "$BUILD_STAMP"
    # Restore the committed requirements.txt however this script exits, so a
    # failed build never leaves a version-pinned copy in the working tree.
    if [ -n "$REQ_BAK" ] && [ -f "$REQ_BAK" ]; then
        mv -f "$REQ_BAK" "$REQ_SRC" 2>/dev/null || true
    fi
}
trap cleanup EXIT
if command -v git >/dev/null 2>&1 &&
    git -C "$REPO_ROOT" rev-parse --short HEAD >/dev/null 2>&1; then
    BUILD_FP="$(git -C "$REPO_ROOT" rev-parse --short HEAD)"
    if ! git -C "$REPO_ROOT" diff --quiet HEAD 2>/dev/null; then
        BUILD_FP="${BUILD_FP}-dirty"
    fi
else
    BUILD_FP="build-$(date -u +%Y%m%d%H%M%S)"
fi
cat >"$BUILD_STAMP" <<EOF
# Generated by build/build_appimage.sh at package time — do NOT commit.
# Ties a rip report to the exact build that produced it (see build_info.py).
BUILD_FINGERPRINT = "${BUILD_FP}"
EOF
echo "Stamped build fingerprint: ${BUILD_FP}"

# --- Build the wheel -------------------------------------------------------
echo "[1/3] Building wheel from local source…"
rm -f "$RECIPE_DIR"/platterpus-*.whl
# `--no-isolation`: build with the setuptools and wheel already installed from
# the hashed release lock. An isolated build makes a fresh environment and fetches
# `setuptools>=77` and `wheel` from PyPI by range, unhashed, inside the job that
# attests the result. `build` still checks [build-system].requires and refuses,
# naming what is missing, when this environment does not satisfy it.
python3 -m build --wheel --no-isolation --outdir "$RECIPE_DIR"
ls -1 "$RECIPE_DIR"/platterpus-*.whl
# The stamp has served its purpose (it's baked into the wheel now).
rm -f "$BUILD_STAMP"

# --- Icon ------------------------------------------------------------------
# python-appimage's "build app" recipe requires <name>.png in the recipe
# directory. The real icon (build/python-appimage/io.github.rmccann_hub.Platterpus.png, produced
# by build/make_icon.py) is committed, so this fallback normally does nothing
# — it only fires if that file has been deleted, dropping a 16×16 grey square
# so the build still succeeds.
if [ ! -f "$RECIPE_DIR/io.github.rmccann_hub.Platterpus.png" ]; then
    echo "Note: no io.github.rmccann_hub.Platterpus.png in recipe; generating placeholder."
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
Path("build/python-appimage/io.github.rmccann_hub.Platterpus.png").write_bytes(png)
PY
fi

# --- Build the AppImage ----------------------------------------------------
echo "[2/3] Building AppImage via python-appimage…"

# Pin the bundled CPython version. Without an explicit --python-version,
# python-appimage grabs the NEWEST CPython base image it can find — which in
# July 2026 became a 3.15 *beta* that no PySide6 wheel supports yet, aborting the
# release build with "No matching distribution found for PySide6" (v0.5.7
# release attempt, 2026-07-24). Pinning a stable, PySide6-supported interpreter
# makes the bundled Python deterministic and immune to a new upstream beta
# appearing. 3.12 is mature and fully covered by our PySide6 pin; override via
# PLATTERPUS_PYTHON_VERSION if a future bump is wanted.
PLATTERPUS_PYTHON_VERSION="${PLATTERPUS_PYTHON_VERSION:-3.12}"
echo "Bundling CPython $PLATTERPUS_PYTHON_VERSION (python-appimage base)."

# Tell pip where to find the locally-built platterpus wheel. python-appimage
# installs each requirements.txt line from a temporary directory, so a
# relative `--find-links .` in the recipe can't work; PIP_FIND_LINKS is a pip
# environment variable (not a PYTHON* one), so it survives pip's `-I` isolated
# mode and applies to every per-line install.
#
# THE HASH-VERIFIED WHEELHOUSE (required since 2026-10-27; it was opt-in, and
# the lock was never committed, so every build installed online by range).
# build/python-appimage/requirements.lock pins every third-party dependency the
# AppImage bundles, with the sha256 of every file PyPI publishes for it. We
# download the closure into a local wheelhouse with `--require-hashes`, which
# ABORTS the build if any file's bytes differ from the recorded sha256 (the
# supply-chain gate: a swapped artifact for a pinned version cannot get in).
# Then python-appimage's per-line installs run OFFLINE (PIP_NO_INDEX) from that
# wheelhouse, with the locally-built platterpus wheel served from the recipe dir
# beside it, so the bundle can only contain what the lock names.
#
# The download runs on the HOST's Python, which is not the one being bundled
# (CI runs 3.11; the AppImage bundles 3.12). numpy, cffi and pydantic-core ship
# one wheel per CPython minor, so the download asks for the BUNDLED target: the
# lock's own header names the Python and platform it was resolved for, and a
# build for another Python is refused here rather than failing later, offline,
# on a wheel the bundled pip cannot install. A missing lock is refused too: a
# supply-chain check that quietly falls back to an unhashed install when its
# input is absent can be satisfied by deleting a file.
# Regenerate the lock with build/lock-requirements.sh whenever a range changes.
WHEELHOUSE="$RECIPE_DIR/.wheelhouse"
LOCK="$RECIPE_DIR/requirements.lock"
rm -rf "$WHEELHOUSE"
if [ ! -f "$LOCK" ]; then
    echo "error: $LOCK is missing. Regenerate it with: bash build/lock-requirements.sh" >&2
    exit 1
fi
LOCK_PYTHON="$(sed -n 's/^# target-python: //p' "$LOCK")"
LOCK_PLATFORM="$(sed -n 's/^# target-platform: //p' "$LOCK")"
if [ -z "$LOCK_PYTHON" ] || [ -z "$LOCK_PLATFORM" ]; then
    echo "error: $LOCK does not name its target-python and target-platform; regenerate it" >&2
    exit 1
fi
if [ "$LOCK_PYTHON" != "$PLATTERPUS_PYTHON_VERSION" ]; then
    echo "error: requirements.lock was resolved for CPython $LOCK_PYTHON, but this build" >&2
    echo "bundles CPython $PLATTERPUS_PYTHON_VERSION. Change APPIMAGE_PYTHON in" >&2
    echo "build/lock-requirements.sh, regenerate the lock, and commit both." >&2
    exit 1
fi
# pip expands a legacy `--platform manylinux2014_x86_64` to the older tags it
# implies, but NOT a `manylinux_2_NN` one (pip 24.0, measured 2026-10-27: given
# only `manylinux_2_34_x86_64` it found no cffi 2.1.1, whose wheel is tagged
# `manylinux_2_17`). So every tag a glibc of the lock's floor accepts is passed
# explicitly, newest first: manylinux_2_NN down to _2_5, then the legacy aliases.
if [[ ! "$LOCK_PLATFORM" =~ ^manylinux_2_([0-9]+)_([a-z0-9_]+)$ ]]; then
    echo "error: cannot read a manylinux_2_NN platform from requirements.lock: $LOCK_PLATFORM" >&2
    exit 1
fi
GLIBC_MINOR="${BASH_REMATCH[1]}"
ARCH="${BASH_REMATCH[2]}"
PLATFORM_ARGS=()
for ((minor = GLIBC_MINOR; minor >= 5; minor--)); do
    PLATFORM_ARGS+=(--platform "manylinux_2_${minor}_${ARCH}")
done
PLATFORM_ARGS+=(--platform "manylinux2014_${ARCH}" --platform "manylinux2010_${ARCH}" --platform "manylinux1_${ARCH}")
echo "Verifying the AppImage's dependencies against requirements.lock"
echo "(CPython $LOCK_PYTHON, glibc $LOCK_PLATFORM or older)…"
mkdir -p "$WHEELHOUSE"
python3 -m pip download --require-hashes --only-binary=:all: \
    --implementation cp --python-version "$LOCK_PYTHON" "${PLATFORM_ARGS[@]}" \
    -r "$LOCK" --dest "$WHEELHOUSE"
export PIP_NO_INDEX=1
export PIP_FIND_LINKS="$WHEELHOUSE $RECIPE_DIR"
echo "Installing dependencies offline from the hash-verified wheelhouse."

# PIN THE PLATTERPUS LINE TO THE VERSION WE JUST BUILT.
#
# **The AppImage was being built from PyPI, not from this tree**, and it took a
# beta to expose it. `requirements.txt` carried a bare `platterpus`, and
# `--find-links` only ADDS a source — pip still resolves to the highest
# acceptable version, and **pip excludes pre-releases by default**. So with a
# local `0.6.4b1` wheel and a published `0.6.3` on PyPI, pip chose 0.6.3: the
# release job built a v0.6.4b1 AppImage containing 0.6.3 and the sanity check
# caught it (`built version (platterpus 0.6.3 (source)) does not match tag`).
#
# **This was invisible for every previous release** because the tree version and
# the newest PyPI version were always the same number, so "built from the tree"
# and "built from PyPI" produced identical binaries. Two witnesses agreeing
# because they share an ancestor — `docs/testing.md` §5.ac, arriving in the build.
#
# **The wheel's FILE PATH, not a version pin** (2026-09-25). This was
# `platterpus==<tree version>`, reasoned as "PyPI has no such version, so only the
# local wheel can satisfy it". That holds at RELEASE time, when the version is new,
# and at no other time: between releases the tree carries the version just
# published, PyPI's copy satisfies the same `==`, and pip took it. So every
# `appimage.yml` build of `main` or a branch between releases bundled the LAST
# RELEASE's code, passed `--version` (same number) and looked current. Found by
# the bundled-verifier check on its first CI run, which asked the bundle for a
# module this branch had added and PyPI's 0.6.60 did not have; the smoke test's
# own `platterpus 0.6.60 (source)` (no build stamp, which a local wheel carries)
# had been saying so all along. A path can only be satisfied by the file at it,
# and pip fails loudly if the file is missing.
#
# Found by a glob, not by parsing `ls` (review 2026-10-27, item 3.6): `ls`
# output is text meant for people, and `| head -1` quietly picked one wheel if
# there were ever two. Step [1/3] deletes old wheels before building, so exactly
# one is expected; zero or several is an error, not a choice to make silently.
shopt -s nullglob
PLATTERPUS_WHEELS=("$RECIPE_DIR"/platterpus-*.whl)
shopt -u nullglob
if [ "${#PLATTERPUS_WHEELS[@]}" -ne 1 ]; then
    echo "error: expected one platterpus wheel in $RECIPE_DIR, found ${#PLATTERPUS_WHEELS[@]} — cannot bundle it" >&2
    exit 1
fi
PLATTERPUS_WHEEL="${PLATTERPUS_WHEELS[0]}"
echo "Bundling the platterpus wheel we just built: $PLATTERPUS_WHEEL"
# Assigning these two arms the single EXIT trap installed near the top of the
# script (see `cleanup`) — deliberately NOT a second `trap`, which would silently
# replace the first and orphan the build stamp.
REQ_SRC="$RECIPE_DIR/requirements.txt"
REQ_BAK="$RECIPE_DIR/requirements.txt.orig"
cp "$REQ_SRC" "$REQ_BAK"
python3 - "$REQ_SRC" "$PLATTERPUS_WHEEL" <<'PIN'
import os, re, sys
path, wheel = sys.argv[1], os.path.abspath(sys.argv[2])
if not os.path.isfile(wheel) or any(c.isspace() for c in wheel):
    # python-appimage runs each line through a shell, so a path with whitespace
    # would be split into two arguments.
    sys.exit(f"cannot bundle {wheel!r}: missing, or its path contains whitespace")
text = open(path, encoding="utf-8").read()
new, n = re.subn(r"(?m)^platterpus\s*$", lambda _m: wheel, text)
if n != 1:
    sys.exit(f"expected exactly one bare 'platterpus' line in {path}, found {n}")
open(path, "w", encoding="utf-8").write(new)
print(f"  requirements.txt: platterpus -> {wheel}")
PIN

# Optional offline / rate-limit escape hatch: by default python-appimage hits
# the GitHub API to discover and download a CPython base AppImage. On a host
# where api.github.com is unreachable or rate-limited (HTTP 403), pre-download
# the matching base image (from github.com/niess/python-appimage releases) and
# point PLATTERPUS_BASE_IMAGE at it to skip the API entirely. The filename
# must keep its upstream form, and its CPython minor must match the lock's
# target-python — the override REPLACES --python-version, so the name is checked
# against the lock instead — e.g.
#   python3.12.<patch>-cp312-cp312-manylinux2014_x86_64.AppImage
if [ -n "${PLATTERPUS_BASE_IMAGE:-}" ]; then
    if [ ! -f "$PLATTERPUS_BASE_IMAGE" ]; then
        echo "PLATTERPUS_BASE_IMAGE is set but not a file: $PLATTERPUS_BASE_IMAGE"
        exit 1
    fi
    case "$(basename "$PLATTERPUS_BASE_IMAGE")" in
        "python$LOCK_PYTHON".*) ;;
        *)
            echo "error: PLATTERPUS_BASE_IMAGE is not a CPython $LOCK_PYTHON image, which" >&2
            echo "requirements.lock was resolved for: $PLATTERPUS_BASE_IMAGE" >&2
            exit 1
            ;;
    esac
    echo "Using pre-downloaded base image: $PLATTERPUS_BASE_IMAGE"
    # A pre-downloaded base image already fixes the interpreter version, so
    # --python-version is neither needed nor passed here.
    python3 -m python_appimage build app "$RECIPE_DIR" \
        --base-image "$PLATTERPUS_BASE_IMAGE"
else
    python3 -m python_appimage build app "$RECIPE_DIR" \
        --python-version "$PLATTERPUS_PYTHON_VERSION"
fi

# python-appimage emits the AppImage at the current directory, named after
# the .desktop "Name=" field (e.g. "Platterpus-x86_64.AppImage"). Note:
# python-appimage builds the appimagetool command unquoted, so the Name must
# not contain spaces or the output file is silently never produced. We
# normalise the result to the canonical artifact name the rest of the project
# (README, CLAUDE.md) refers to.
# The verified wheelhouse (if we built one) has served its purpose — the deps
# are now inside the AppImage. Remove it so it never lingers or gets committed.
rm -rf "$WHEELHOUSE"

echo "[3/3] Normalising AppImage name…"
desktop_name="$(sed -n 's/^Name=//p' "$RECIPE_DIR/io.github.rmccann_hub.Platterpus.desktop" | head -1)"
arch="$(uname -m)"
produced="$REPO_ROOT/${desktop_name}-${arch}.AppImage"
canonical="$REPO_ROOT/platterpus-${arch}.AppImage"
if [ -f "$produced" ] && [ "$produced" != "$canonical" ]; then
    mv -f "$produced" "$canonical"
fi
if [ -f "$canonical" ]; then
    ls -lh "$canonical"
else
    echo "No AppImage produced at $canonical. Check python-appimage output above."
    exit 1
fi

# --- Embed AppImage update-information (KDD-17b) -----------------------------
# python-appimage hardcodes its appimagetool invocation (no -u support), so we
# re-pack the finished AppImage ourselves to embed the standard zsync
# update-information. Any AppImageUpdate-compatible tool can then discover the
# newest GitHub release and download only the changed blocks, verified.
# Re-packing also emits platterpus-<arch>.AppImage.zsync (when `zsyncmake` is
# installed — package "zsync") which release.yml uploads beside the AppImage.
# This runs BEFORE the release workflow's checksum step, so the .sha256 always
# covers the final, update-info-embedded file.
UPDATE_INFO="gh-releases-zsync|rmccann-hub|Platterpus|latest|platterpus-${arch}.AppImage.zsync"

find_appimagetool() {
    # A system appimagetool wins; otherwise reuse the copy python-appimage
    # just cached for its own build (~/.cache/python-appimage/bin).
    command -v appimagetool 2>/dev/null && return 0
    local candidate
    # NOTE: python-appimage caches the tool in a DOT-prefixed directory
    # (.appimagetool-<ver>.appdir/AppRun), which a plain * glob skips —
    # that exact miss broke the v0.2.0 release upload. Match both forms.
    for candidate in "$HOME/.cache/python-appimage/bin"/.appimagetool*/AppRun \
                     "$HOME/.cache/python-appimage/bin"/*appimagetool*/AppRun \
                     "$HOME/.cache/python-appimage/bin"/*appimagetool*; do
        if [ -x "$candidate" ]; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

echo "[4/4] Embedding zsync update-information…"
if tool="$(find_appimagetool)"; then
    chmod +x "$canonical"
    workdir="$(mktemp -d)"
    (
        cd "$workdir"
        # Extract-and-repack keeps working on FUSE-less hosts (CI).
        APPIMAGE_EXTRACT_AND_RUN=1 "$canonical" --appimage-extract >/dev/null
        ARCH="$arch" APPIMAGE_EXTRACT_AND_RUN=1 "$tool" --no-appstream \
            -u "$UPDATE_INFO" squashfs-root "$canonical"
    )
    # appimagetool drops the .zsync in its working directory; move it home.
    zsync_name="platterpus-${arch}.AppImage.zsync"
    if [ -f "$workdir/$zsync_name" ]; then
        mv -f "$workdir/$zsync_name" "$REPO_ROOT/$zsync_name"
    fi
    rm -rf "$workdir"
    if [ -f "$REPO_ROOT/$zsync_name" ]; then
        echo "Wrote $zsync_name (delta updates enabled)"
    else
        echo "NOTE: no .zsync produced — install 'zsync' (zsyncmake) for delta"
        echo "      update files; the update-information is embedded regardless."
    fi
else
    echo "NOTE: appimagetool not found — skipped update-information embed."
    echo "      (Run the build once so python-appimage caches it, or install"
    echo "      appimagetool on PATH.)"
fi
