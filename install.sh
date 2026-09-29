#!/usr/bin/env bash
# install.sh — one-command, single-file installer for Platterpus (end users).
#
# Takes a machine from nothing to a launchable app:
#   1. Host stack: Distrobox + the `ripping` container + cyanrip + flac,
#      exported to ~/.local/bin (delegated to setup-host.sh --no-gui).
#   2. The GUI: downloads the published AppImage release (or uses a local /
#      freshly-built one) and parks it in ~/Applications. A download is checked
#      first, the way the in-app updater checks an update: against the
#      release's published .sha256, and against its build attestation when an
#      installed GitHub CLI (`gh`, 2.51.0 or later) can check it. A file that
#      fails either check is refused.
#   3. Desktop integration: an app-menu entry, a Desktop icon, AND an
#      "Uninstall Platterpus" shortcut (delegated to install-appimage.sh).
#
# It reuses setup-host.sh and install-appimage.sh, downloading them if this
# script is run on its own (not from a checkout), so it stays a single file
# you can download and run — or pipe:
#   curl -fsSL https://raw.githubusercontent.com/rmccann-hub/Platterpus/main/install.sh | bash
#
# Usage:
#   bash install.sh                 # full install (host stack + GUI)
#   bash install.sh --yes           # assume "yes" to confirmations
#   bash install.sh --dry-run       # print actions, change nothing
#   bash install.sh --no-host       # skip the host stack; install the GUI only
#   bash install.sh --appimage PATH # use a local AppImage (skip the download)
#   bash install.sh --build         # build the AppImage from a source checkout
#   bash install.sh --container NAME --image IMAGE   # passed to setup-host.sh
#   bash install.sh --help

set -euo pipefail

# --- Config / defaults -----------------------------------------------------
OWNER_REPO="rmccann-hub/Platterpus"
REPO_RAW="https://raw.githubusercontent.com/$OWNER_REPO/main"
APPIMAGE_NAME="platterpus-x86_64.AppImage"
APPS_DIR="$HOME/Applications"

DRY_RUN=0
ASSUME_YES=0
DO_HOST=1
DO_BUILD=0
APPIMAGE_PATH=""
CONTAINER=""
IMAGE=""

usage() {
    cat <<'HELP'
install.sh — one-command installer for Platterpus.

Installs everything an end user needs:
  1. Host stack  : Distrobox + the `ripping` container + cyanrip + flac,
                   exported to ~/.local/bin (via setup-host.sh --no-gui).
  2. GUI         : downloads the published AppImage, checks it against the
                   release's .sha256 (and its build attestation, if an installed
                   GitHub CLI `gh`, 2.51.0 or later, can check it), and puts it
                   in ~/Applications.
  3. Shortcuts   : app-menu entry, Desktop icon, and an "Uninstall Platterpus"
                   shortcut (via install-appimage.sh).

Usage:
  bash install.sh                 full install (host stack + GUI)
  bash install.sh --yes           assume "yes" to confirmations
  bash install.sh --dry-run       print actions, change nothing
  bash install.sh --no-host       skip the host stack; install the GUI only
  bash install.sh --appimage PATH use a local AppImage (skip the download)
  bash install.sh --build         build the AppImage from a source checkout
  bash install.sh --container NAME --image IMAGE   passed to setup-host.sh
  bash install.sh --help          this message

To remove everything later: use the "Uninstall Platterpus" shortcut, or run
uninstall.sh (interactive, with options).
HELP
}

# --- Parse args ------------------------------------------------------------
while [ $# -gt 0 ]; do
    case "$1" in
        --yes|-y) ASSUME_YES=1 ;;
        --dry-run) DRY_RUN=1 ;;
        --no-host) DO_HOST=0 ;;
        --build) DO_BUILD=1 ;;
        --appimage) shift; APPIMAGE_PATH="${1:?--appimage needs a path}" ;;
        --container) shift; CONTAINER="${1:?--container needs a value}" ;;
        --image) shift; IMAGE="${1:?--image needs a value}" ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
    shift
done

# --- Helpers ---------------------------------------------------------------
# run(): echo a command; execute it unless --dry-run.
run() {
    if [ "$DRY_RUN" -eq 1 ]; then
        echo "  DRY-RUN: $*"
    else
        "$@"
    fi
}

# Where this script lives, if it's a real file (not a `curl … | bash` pipe).
SCRIPT_DIR=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi

TMP_DIR=""
# A download that has not passed its checks yet (see download_appimage). Set
# while one exists, so an interrupted or refused install leaves nothing behind.
PART_FILE=""
# Must return 0: as an EXIT-trap, a non-zero status here would become the
# script's exit code (it does, when TMP_DIR is empty and the && short-circuits).
cleanup() {
    [ -n "$TMP_DIR" ] && rm -rf "$TMP_DIR"
    [ -n "$PART_FILE" ] && rm -f "$PART_FILE"
    return 0
}
trap cleanup EXIT

# fetch_script <name> — print a path to a sibling script, preferring a local
# copy (running from a checkout), else downloading it from the repo.
fetch_script() {
    local name="$1"
    if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/$name" ]; then
        echo "$SCRIPT_DIR/$name"
        return 0
    fi
    [ -n "$TMP_DIR" ] || TMP_DIR="$(mktemp -d)"
    curl -fsSL "$REPO_RAW/$name" -o "$TMP_DIR/$name" || return 1
    echo "$TMP_DIR/$name"
}

# gh_can_verify_attestations — true when the gh on PATH lists
# --signer-workflow among `gh attestation verify`'s flags. The pattern matches
# a flag line (leading spaces, then the flag), not the help's prose, which
# mentions the flag in backticks. The help is captured before it is matched:
# under `set -o pipefail`, `gh … | grep -q` can report a match as a failure
# when grep exits early and gh is killed writing to the closed pipe.
gh_can_verify_attestations() {
    local help
    help="$(gh attestation verify --help 2>&1)" || true
    grep -qE '^[[:space:]]+--signer-workflow[[:space:]]' <<<"$help"
}

# download_appimage <dest> — fetch the AppImage from the newest release, and
# install it only after it passes the two checks the in-app updater makes
# before it installs an update (update_install.py, update_attestation.py):
#   1. integrity: its SHA-256 matches the release's published .sha256;
#   2. provenance, when an installed GitHub CLI (`gh`) can check it: its build
#      attestation verifies, i.e. it was built by this repository's release
#      workflow. `--bundle` uses the attestation the release publishes, so gh
#      needs no login. Without gh, or with a gh too old to check it, this
#      check is skipped and the script says which.
# The download goes to a .part file beside <dest> and is renamed into place
# only once both checks pass, so a refused file never replaces a working
# install. Uses the API (not /releases/latest/download) because v0.x ships as
# a *pre-release*, which the "latest" endpoint skips.
#
# Returns 1 when there is nothing to install (no release, or the download
# failed) and 2 when a check refused the file. Each refusal prints its own
# reason; the caller adds its "no published release yet?" hint only for 1.
download_appimage() {
    local dest="$1" url expected actual bundle
    url="$(curl -fsSL "https://api.github.com/repos/$OWNER_REPO/releases" \
        | grep '"browser_download_url"' \
        | grep "$APPIMAGE_NAME\"" \
        | head -1 | cut -d'"' -f4)"
    [ -n "$url" ] || return 1
    echo "  from: $url"
    [ -n "$TMP_DIR" ] || TMP_DIR="$(mktemp -d)" || return 1
    PART_FILE="$(dirname "$dest")/.platterpus-install.part"
    curl -fL "$url" -o "$PART_FILE" || return 1

    # 1. Integrity: the release's published SHA-256 (sha256sum's own format,
    #    "<64 hex>  <name>", as release.yml writes it).
    if ! command -v sha256sum >/dev/null 2>&1; then
        echo "Refusing to install: sha256sum is not available, so the download" >&2
        echo "can't be checked against the release's checksum." >&2
        return 2
    fi
    if ! curl -fsSL "$url.sha256" -o "$TMP_DIR/$APPIMAGE_NAME.sha256"; then
        echo "Refusing to install: couldn't fetch the release's checksum" >&2
        echo "($APPIMAGE_NAME.sha256), so the download can't be checked." >&2
        return 2
    fi
    expected="$(tr -d '\r' <"$TMP_DIR/$APPIMAGE_NAME.sha256" \
        | awk 'NR == 1 { print tolower($1) }')"
    if ! [[ "$expected" =~ ^[0-9a-f]{64}$ ]]; then
        echo "Refusing to install: the release's checksum file is malformed." >&2
        return 2
    fi
    # Read from stdin: sha256sum escapes some file names in its output.
    actual="$(sha256sum <"$PART_FILE" | awk '{ print $1 }')"
    if [ "$actual" != "$expected" ]; then
        echo "Refusing to install: the download does not match the release's" >&2
        echo "checksum." >&2
        echo "  expected: $expected" >&2
        echo "  got:      $actual" >&2
        return 2
    fi
    echo "  checksum matches the release's $APPIMAGE_NAME.sha256."

    # 2. Provenance: the build attestation, when gh is here and can check it.
    #    "Can check" is read off gh's own help, not guessed from its version:
    #    the flags list must name --signer-workflow, which gh lists from 2.51.0
    #    on. An older gh fails `attestation verify` the same way a real
    #    mismatch does (a gh without the command exits 1, "unknown command"),
    #    and treating that as a refusal would turn away a download that is fine.
    if command -v gh >/dev/null 2>&1 && gh_can_verify_attestations; then
        bundle="$TMP_DIR/$APPIMAGE_NAME.sigstore.json"
        if ! curl -fsSL "$url.sigstore.json" -o "$bundle"; then
            echo "Refusing to install: couldn't fetch the release's build" >&2
            echo "attestation ($APPIMAGE_NAME.sigstore.json)." >&2
            return 2
        fi
        if ! gh attestation verify "$PART_FILE" --repo "$OWNER_REPO" \
            --bundle "$bundle" \
            --signer-workflow "$OWNER_REPO/.github/workflows/release.yml" \
            >"$TMP_DIR/gh-attestation.log" 2>&1; then
            echo "Refusing to install: gh could not verify the build attestation." >&2
            echo "gh said:" >&2
            sed 's/^/    /' "$TMP_DIR/gh-attestation.log" >&2
            return 2
        fi
        echo "  build attestation verified: built by $OWNER_REPO's release workflow."
    elif command -v gh >/dev/null 2>&1; then
        echo "  This gh is too old to check the attestation (it needs gh 2.51.0 or"
        echo "  later), so only the checksum was checked. The app checks the"
        echo "  attestation before every update it installs."
    else
        echo "  gh (the GitHub CLI) is not installed, so the build attestation"
        echo "  was not checked. The app checks it before every update it installs."
    fi

    chmod +x "$PART_FILE" || return 2
    mv -f "$PART_FILE" "$dest" || return 2
    PART_FILE=""
}

# --- 1. Host stack ---------------------------------------------------------
HOST_FLAGS=()
[ "$ASSUME_YES" -eq 1 ] && HOST_FLAGS+=(--yes)
[ "$DRY_RUN" -eq 1 ] && HOST_FLAGS+=(--dry-run)
[ -n "$CONTAINER" ] && HOST_FLAGS+=(--container "$CONTAINER")
[ -n "$IMAGE" ] && HOST_FLAGS+=(--image "$IMAGE")

if [ "$DO_HOST" -eq 1 ]; then
    echo "==> 1/3 Host stack (Distrobox + ripping container + cyanrip)…"
    host_sh="$(fetch_script setup-host.sh)" \
        || { echo "Couldn't obtain setup-host.sh." >&2; exit 1; }
    run bash "$host_sh" --no-gui "${HOST_FLAGS[@]}"
else
    echo "==> 1/3 Skipping host stack (--no-host)."
fi

# --- 2. Obtain the AppImage ------------------------------------------------
appimage=""
if [ -n "$APPIMAGE_PATH" ]; then
    echo "==> 2/3 Using local AppImage: $APPIMAGE_PATH"
    appimage="$APPIMAGE_PATH"
elif [ "$DO_BUILD" -eq 1 ]; then
    echo "==> 2/3 Building the AppImage from source…"
    if [ -z "$SCRIPT_DIR" ] || [ ! -f "$SCRIPT_DIR/build/build_appimage.sh" ]; then
        echo "--build needs a source checkout (run this script from a clone)." >&2
        exit 1
    fi
    run bash "$SCRIPT_DIR/build/build_appimage.sh"
    appimage="$SCRIPT_DIR/$APPIMAGE_NAME"
else
    echo "==> 2/3 Downloading the latest published AppImage…"
    run mkdir -p "$APPS_DIR"
    if [ "$DRY_RUN" -eq 1 ]; then
        echo "  DRY-RUN: download $APPIMAGE_NAME from the newest release, check it"
        echo "  DRY-RUN: against the release's .sha256 (and its build attestation, if"
        echo "  DRY-RUN: an installed gh can check it), then move it into $APPS_DIR/"
    else
        download_appimage "$APPS_DIR/$APPIMAGE_NAME" || {
            status=$?
            if [ "$status" -eq 1 ]; then
                echo "Couldn't download the AppImage — no published release yet?" >&2
                echo "Run from a checkout with --build, or pass --appimage PATH." >&2
            else
                echo "Nothing was installed; an AppImage already in $APPS_DIR" >&2
                echo "is unchanged." >&2
            fi
            exit 1
        }
    fi
    appimage="$APPS_DIR/$APPIMAGE_NAME"
fi

# --- 3. Desktop integration (+ uninstall shortcut) -------------------------
echo "==> 3/3 Integrating into your desktop…"
ia_sh="$(fetch_script install-appimage.sh)" \
    || { echo "Couldn't obtain install-appimage.sh." >&2; exit 1; }
run bash "$ia_sh" "$appimage"

echo
echo "Done. Look for \"Platterpus\" in your application menu."
echo "To remove it later, use the \"Uninstall Platterpus\" shortcut."
