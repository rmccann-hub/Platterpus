#!/usr/bin/env bash
# install-appimage.sh — desktop-integrate the Whipper GUI AppImage.
#
# An AppImage is a single portable binary: by design it does NOT add itself
# to your application menu or drop a desktop icon (unlike the source install
# via dev-setup.sh). This script does that integration for a downloaded
# AppImage, so it behaves like an installed app — and `--uninstall` undoes it.
#
# It's standalone: it needs only the AppImage (not a repo checkout), and it
# pulls the icon out of the AppImage itself.
#
# Usage:
#   bash install-appimage.sh [path/to/whipper-gui-x86_64.AppImage]
#   bash install-appimage.sh --uninstall
#   bash install-appimage.sh --help
#
# With no path, it looks for whipper-gui*.AppImage in the current directory,
# then ~/Downloads, then ~/Applications.

set -euo pipefail

APP_NAME="Whipper GUI"
DESKTOP_ID="whipper-gui"
APPS_DIR="$HOME/Applications"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}"
DESKTOP_DIR="$DATA_DIR/applications"
ICON_DIR="$DATA_DIR/icons"
DESKTOP_FILE="$DESKTOP_DIR/$DESKTOP_ID.desktop"
ICON_FILE="$ICON_DIR/$DESKTOP_ID.png"
USER_DESKTOP="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"

usage() {
    sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
}

# Refresh the freedesktop + KDE menu caches so the entry appears/disappears
# without a re-login. All best-effort.
refresh_menu() {
    command -v update-desktop-database >/dev/null 2>&1 \
        && update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
    for kbs in kbuildsycoca6 kbuildsycoca5; do
        if command -v "$kbs" >/dev/null 2>&1; then
            "$kbs" >/dev/null 2>&1 || true
            break
        fi
    done
}

do_uninstall() {
    rm -f "$DESKTOP_FILE" "$ICON_FILE" "$USER_DESKTOP/$DESKTOP_ID.desktop"
    refresh_menu
    echo "Removed Whipper GUI menu entry, desktop icon, and icon file."
    echo "The AppImage binary itself was left untouched."
}

# Find the AppImage to integrate: explicit arg, else search common spots.
find_appimage() {
    local arg="${1:-}"
    if [ -n "$arg" ]; then
        [ -f "$arg" ] || { echo "Not a file: $arg" >&2; return 1; }
        ( cd "$(dirname "$arg")" && printf '%s/%s\n' "$PWD" "$(basename "$arg")" )
        return 0
    fi
    local dir
    for dir in "$PWD" "$HOME/Downloads" "$APPS_DIR"; do
        local hit
        hit="$(ls -1 "$dir"/whipper-gui*.AppImage 2>/dev/null | head -1 || true)"
        if [ -n "$hit" ]; then
            echo "$hit"
            return 0
        fi
    done
    return 1
}

# Pull the bundled icon out of the AppImage. Falls back to the stock
# "media-optical" icon name (present in every icon theme) if extraction
# fails, so the launcher always ends up with *an* icon.
extract_icon() {
    local appimage="$1"
    local workdir
    workdir="$(mktemp -d)"
    local got=""
    # .DirIcon is the AppImage-standard icon; the named PNG is our 512px one.
    if ( cd "$workdir" && "$appimage" --appimage-extract whipper-gui.png ) \
            >/dev/null 2>&1 && [ -f "$workdir/squashfs-root/whipper-gui.png" ]; then
        got="$workdir/squashfs-root/whipper-gui.png"
    elif ( cd "$workdir" && "$appimage" --appimage-extract .DirIcon ) \
            >/dev/null 2>&1 && [ -f "$workdir/squashfs-root/.DirIcon" ]; then
        got="$workdir/squashfs-root/.DirIcon"
    fi
    if [ -n "$got" ]; then
        mkdir -p "$ICON_DIR"
        cp -f "$got" "$ICON_FILE"
        echo "$ICON_FILE"
    else
        echo "media-optical"  # stock fallback icon name
    fi
    rm -rf "$workdir"
}

do_install() {
    local src icon_value appimage
    src="$(find_appimage "${1:-}")" || {
        echo "Couldn't find a whipper-gui*.AppImage." >&2
        echo "Pass its path: bash install-appimage.sh /path/to/whipper-gui-x86_64.AppImage" >&2
        exit 1
    }

    # Park the AppImage in ~/Applications so the launcher's path is stable.
    mkdir -p "$APPS_DIR"
    appimage="$APPS_DIR/$(basename "$src")"
    if [ "$src" != "$appimage" ]; then
        cp -f "$src" "$appimage"
        echo "Copied AppImage to $appimage"
    fi
    chmod +x "$appimage"

    icon_value="$(extract_icon "$appimage")"

    mkdir -p "$DESKTOP_DIR"
    cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=$APP_NAME
GenericName=CD Audio Ripper
Comment=Rip audio CDs to FLAC with whipper
Exec=$appimage
Icon=$icon_value
Terminal=false
Categories=AudioVideo;Audio;DiscBurning;
Keywords=cd;rip;flac;audio;whipper;musicbrainz;
EOF
    echo "Installed menu entry: $DESKTOP_FILE"

    # Also drop a clickable icon on the Desktop (executable + GNOME-trusted).
    if [ -d "$USER_DESKTOP" ]; then
        cp -f "$DESKTOP_FILE" "$USER_DESKTOP/$DESKTOP_ID.desktop"
        chmod +x "$USER_DESKTOP/$DESKTOP_ID.desktop"
        command -v gio >/dev/null 2>&1 \
            && gio set "$USER_DESKTOP/$DESKTOP_ID.desktop" metadata::trusted true \
               >/dev/null 2>&1 || true
        echo "Installed desktop icon: $USER_DESKTOP/$DESKTOP_ID.desktop"
    fi

    refresh_menu
    echo
    echo "Done. \"$APP_NAME\" should now appear in your application menu."
    echo "(If not immediately, log out and back in.)"
}

case "${1:-}" in
    -h|--help) usage; exit 0 ;;
    --uninstall) do_uninstall ;;
    *) do_install "${1:-}" ;;
esac
