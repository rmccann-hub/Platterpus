#!/usr/bin/env bash
# Uninstall Platterpus from your system.
#
# Default removals (safe — easily redoable with dev-setup.sh):
#   - The .venv/ directory
#   - GUI config at ~/.config/platterpus/
#   - GUI logs at ~/.local/share/platterpus/
#
# Optional removals (prompted interactively, or --full to enable all):
#   - MusicBrainz Picard Flatpak
#   - The Distrobox 'ripping' container
#   - whipper.conf at ~/.config/whipper/
#   - Host-exported whipper, metaflac, flac and cyanrip at ~/.local/bin/
#
# NEVER removed unless explicitly asked via --remove-rips:
#   - Music files at ~/Music/rips/ (or wherever your Config points)
#   - The cloned repo directory itself — `cd ..; rm -rf <repo>` is yours
#
# Usage:
#   bash uninstall.sh                  # interactive: prompts for each broader removal
#   bash uninstall.sh --yes            # remove the defaults silently; skip broader
#   bash uninstall.sh --full --yes     # remove everything including broader stack
#   bash uninstall.sh --dry-run        # show what would be removed without doing it
#   bash uninstall.sh --help

set -euo pipefail

# --- Defaults --------------------------------------------------------------

INTERACTIVE=1
DRY_RUN=0
REMOVE_PICARD=0
REMOVE_CONTAINER=0
REMOVE_WHIPPER_CONFIG=0
REMOVE_EXPORTS=0
REMOVE_RIPS=0

usage() {
    cat <<'HELP'
Uninstall Platterpus from your system.

Default removals (safe — easily redoable with dev-setup.sh):
  - The .venv/ directory
  - GUI config at ~/.config/platterpus/
  - GUI logs at ~/.local/share/platterpus/

Optional removals (prompted interactively, or --full to enable all):
  - MusicBrainz Picard Flatpak
  - The Distrobox 'ripping' container
  - whipper.conf at ~/.config/whipper/
  - Host-exported whipper, metaflac, flac and cyanrip at ~/.local/bin/

NEVER removed unless explicitly asked via --remove-rips:
  - Music files at ~/Music/rips/ (or wherever your Config points)
  - The cloned repo directory itself — `cd ..; rm -rf <repo>` is yours

Usage:
  bash uninstall.sh                  interactive prompts
  bash uninstall.sh --yes            remove defaults silently; skip broader
  bash uninstall.sh --full --yes     remove everything including broader stack
  bash uninstall.sh --dry-run        show what would be removed
  bash uninstall.sh --help           this message
HELP
}

# --- Parse args ------------------------------------------------------------

while [ $# -gt 0 ]; do
    case "$1" in
        --yes) INTERACTIVE=0 ;;
        --dry-run) DRY_RUN=1 ;;
        --full)
            REMOVE_PICARD=1
            REMOVE_CONTAINER=1
            REMOVE_WHIPPER_CONFIG=1
            REMOVE_EXPORTS=1
            ;;
        --remove-rips) REMOVE_RIPS=1 ;;
        -h|--help) usage; exit 0 ;;
        *)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
    shift
done

# --- Helpers --------------------------------------------------------------

# run "<command>" — executes if not dry-run, otherwise prints what would run.
run() {
    if [ "$DRY_RUN" -eq 1 ]; then
        echo "  DRY-RUN: $*"
    else
        "$@"
    fi
}

# prompt "<question>" — returns 0 (yes) / 1 (no). In non-interactive mode,
# returns 1 (no) unless the variable for this category was already set to 1
# (via --full or a specific flag).
prompt() {
    local question="$1"
    if [ "$INTERACTIVE" -eq 0 ]; then
        return 1
    fi
    read -rp "$question [y/N] " ans
    [[ "$ans" =~ ^[Yy]$ ]]
}

removed() { echo "  ✓ removed: $1"; }
skipped() { echo "  - skipped:  $1"; }
missing() { echo "  - not present: $1"; }

# --- Header ---------------------------------------------------------------

cd "$(dirname "$0")"
REPO_ROOT="$(pwd)"

echo "Platterpus uninstall"
echo "  Repo root: $REPO_ROOT"
if [ "$DRY_RUN" -eq 1 ]; then
    echo "  Mode: DRY RUN (no files will be touched)"
fi
echo

# --- 1. Always-removed (safe defaults) ------------------------------------

echo "Default removals:"

if [ -d "$REPO_ROOT/.venv" ]; then
    run rm -rf "$REPO_ROOT/.venv"
    removed "$REPO_ROOT/.venv"
else
    missing "$REPO_ROOT/.venv"
fi

# `platterpus` CLI symlink dev-setup.sh puts on PATH. Only remove it if
# it actually points into this repo's venv (don't clobber a pipx install
# of the same name).
CLI_LINK="$HOME/.local/bin/platterpus"
if [ -L "$CLI_LINK" ] && [ "$(readlink "$CLI_LINK")" = "$REPO_ROOT/.venv/bin/platterpus" ]; then
    run rm -f "$CLI_LINK"
    removed "$CLI_LINK"
else
    missing "$CLI_LINK"
fi

GUI_CONFIG="$HOME/.config/platterpus"
if [ -d "$GUI_CONFIG" ]; then
    run rm -rf "$GUI_CONFIG"
    removed "$GUI_CONFIG"
else
    missing "$GUI_CONFIG"
fi

GUI_LOGS="$HOME/.local/share/platterpus"
if [ -d "$GUI_LOGS" ]; then
    run rm -rf "$GUI_LOGS"
    removed "$GUI_LOGS"
else
    missing "$GUI_LOGS"
fi

# Pre-rename leftovers (the app was "Whipper GUI" before Platterpus). The
# rename copied ~/.config/whipper-gui → ~/.config/platterpus rather than moving
# it, so the old dirs can linger — clear them for a clean slate.
for _legacy in "$HOME/.config/whipper-gui" "$HOME/.local/share/whipper-gui"; do
    if [ -d "$_legacy" ]; then
        run rm -rf "$_legacy"
        removed "$_legacy (legacy whipper-gui)"
    fi
done

# The freedesktop app-id: the AppImage integration writes its menu entry and
# icon under this name (paths.APP_ID), while dev-setup.sh uses the short
# `platterpus` name. Remove BOTH so every install method is covered — and the
# legacy pre-rename `whipper-gui` name too, for a truly clean slate.
APP_ID="io.github.rmccann_hub.Platterpus"

# Main menu launcher. Created as "$APP_ID.desktop" by the AppImage (the bug this
# fixes: the old uninstaller only deleted "platterpus.desktop" and orphaned the
# AppImage's real entry), or "platterpus.desktop" by dev-setup.sh.
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
_desktop_removed=0
for _name in "$APP_ID.desktop" "platterpus.desktop" "whipper-gui.desktop"; do
    DESKTOP_FILE="$DESKTOP_DIR/$_name"
    if [ -f "$DESKTOP_FILE" ]; then
        run rm -f "$DESKTOP_FILE"
        removed "$DESKTOP_FILE"
        _desktop_removed=1
    fi
done
if [ "$_desktop_removed" -eq 1 ]; then
    # Refresh the app-menu caches so the entry disappears immediately
    # (mirrors dev-setup.sh). update-desktop-database covers the MIME
    # cache; KDE Plasma's launcher needs kbuildsycoca. Best-effort.
    if command -v update-desktop-database >/dev/null 2>&1; then
        run update-desktop-database "$DESKTOP_DIR"
    fi
    for _kbs in kbuildsycoca6 kbuildsycoca5; do
        if command -v "$_kbs" >/dev/null 2>&1; then
            run "$_kbs"
            break
        fi
    done
else
    missing "$DESKTOP_DIR/$APP_ID.desktop"
fi

# The clickable copy placed on the user's Desktop (AppImage uses "$APP_ID",
# dev-setup uses "platterpus").
DESKTOP_USER_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"
for _name in "$APP_ID.desktop" "platterpus.desktop"; do
    DESKTOP_ICON="$DESKTOP_USER_DIR/$_name"
    if [ -f "$DESKTOP_ICON" ]; then
        run rm -f "$DESKTOP_ICON"
        removed "$DESKTOP_ICON"
    fi
done

# AppImage install (install.sh / install-appimage.sh): the parked AppImage,
# its extracted icon, the uninstall shortcut, and the staged copy of this
# very script. Globs the versioned AppImage filename.
APPS_DIR="$HOME/Applications"
shopt -s nullglob
for _app in "$APPS_DIR"/platterpus*.AppImage "$APPS_DIR"/[Ww]hipper-[Gg][Uu][Ii]*.AppImage; do
    run rm -f "$_app"
    removed "$_app"
done
shopt -u nullglob

# Extracted app icon. The AppImage integration copies it as "$APP_ID.png"; the
# old uninstaller only knew "platterpus.png". Remove both.
ICONS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons"
for _name in "$APP_ID.png" "platterpus.png"; do
    APP_ICON="$ICONS_DIR/$_name"
    if [ -f "$APP_ICON" ]; then
        run rm -f "$APP_ICON"
        removed "$APP_ICON"
    fi
done

UNINSTALL_DESKTOP="$DESKTOP_DIR/platterpus-uninstall.desktop"
if [ -f "$UNINSTALL_DESKTOP" ]; then
    run rm -f "$UNINSTALL_DESKTOP"
    removed "$UNINSTALL_DESKTOP"
fi

# The staged copy of this uninstaller (deleting a running script is safe on
# Linux — the kernel keeps the open inode until the process exits).
STAGED_UNINSTALLER="$APPS_DIR/platterpus-uninstall.sh"
if [ -f "$STAGED_UNINSTALLER" ]; then
    run rm -f "$STAGED_UNINSTALLER"
    removed "$STAGED_UNINSTALLER"
fi

# Build artifact left over from dev-setup or AppImage builds.
if [ -d "$REPO_ROOT/build/python-appimage/__pycache__" ]; then
    run rm -rf "$REPO_ROOT/build/python-appimage/__pycache__"
fi

echo

# --- 2. Optional removals (Picard, container, whipper.conf, exports) -----

echo "Optional removals (Picard, container, whipper.conf, host exports):"

# Picard
if [ "$REMOVE_PICARD" -eq 1 ] || prompt "Remove MusicBrainz Picard (Flatpak)?"; then
    if command -v flatpak >/dev/null 2>&1 && \
       flatpak list --user 2>/dev/null | grep -q "org.musicbrainz.Picard"; then
        run flatpak uninstall --user -y org.musicbrainz.Picard
        removed "Picard (Flatpak)"
    else
        missing "Picard (Flatpak — not installed at user level)"
    fi
else
    skipped "MusicBrainz Picard"
fi

# Distrobox 'ripping' container
if [ "$REMOVE_CONTAINER" -eq 1 ] || prompt "Remove the 'ripping' Distrobox container?"; then
    if command -v distrobox >/dev/null 2>&1 && \
       distrobox list 2>/dev/null | grep -q "ripping"; then
        run distrobox stop ripping --yes 2>/dev/null || true
        run distrobox rm ripping --force 2>/dev/null || true
        removed "Distrobox 'ripping' container"
    else
        missing "Distrobox 'ripping' container"
    fi
else
    skipped "Distrobox 'ripping' container"
fi

# whipper config — remove the whole ~/.config/whipper/ directory, not just
# whipper.conf, so the drive-setup wizard's whipper.conf.bak backup doesn't
# survive a "full" uninstall. Matches what the in-app uninstaller
# (deps/host_teardown.py) already does (it removes the config dir).
WHIPPER_CONF_DIR="$HOME/.config/whipper"
if [ "$REMOVE_WHIPPER_CONFIG" -eq 1 ] || prompt "Remove whipper config (drive calibration, incl. .bak) at $WHIPPER_CONF_DIR?"; then
    if [ -d "$WHIPPER_CONF_DIR" ]; then
        run rm -rf "$WHIPPER_CONF_DIR"
        removed "$WHIPPER_CONF_DIR"
    else
        missing "$WHIPPER_CONF_DIR"
    fi
else
    skipped "$WHIPPER_CONF_DIR"
fi

# Host-exported binaries from Distrobox. Must match what setup-host.sh exported
# (cyanrip, metaflac AND flac); `flac` was missing, so its wrapper was orphaned.
# `whipper` stays for a pre-KDD-18 install that may still have it exported.
if [ "$REMOVE_EXPORTS" -eq 1 ] || prompt "Remove host-exported whipper, metaflac, flac and cyanrip wrappers at ~/.local/bin/?"; then
    for bin in whipper metaflac flac cyanrip; do
        target="$HOME/.local/bin/$bin"
        if [ -f "$target" ]; then
            run rm -f "$target"
            removed "$target"
        else
            missing "$target"
        fi
    done
else
    skipped "host-exported whipper, metaflac, flac and cyanrip"
fi

# Music files — opt-in only, never via --full.
if [ "$REMOVE_RIPS" -eq 1 ]; then
    RIPS_DIR="$HOME/Music/rips"
    if [ -d "$RIPS_DIR" ]; then
        echo
        echo "⚠️  --remove-rips was passed. About to delete $RIPS_DIR"
        echo "    (this is your music! make sure you have a backup.)"
        if [ "$INTERACTIVE" -eq 1 ]; then
            read -rp "Type 'DELETE' to confirm: " confirm
            if [ "$confirm" != "DELETE" ]; then
                echo "  Aborted; rips kept."
                exit 0
            fi
        fi
        run rm -rf "$RIPS_DIR"
        removed "$RIPS_DIR"
    fi
fi

echo
echo "Done."
echo
echo "Not touched (remove yourself if you want):"
# Only mention the repo when we're actually running from a checkout (the
# staged-copy/AppImage case runs from ~/Applications, where there's no repo).
if [ -f "$REPO_ROOT/pyproject.toml" ]; then
    echo "  - The cloned repo at $REPO_ROOT"
    echo "    To remove: cd .. && rm -rf \"$(basename "$REPO_ROOT")\""
fi
if [ "$REMOVE_RIPS" -eq 0 ]; then
    echo "  - Music files at ~/Music/rips/ (use --remove-rips if you really want to)"
fi
