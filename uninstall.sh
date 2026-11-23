#!/usr/bin/env bash
# Uninstall Platterpus from your system.
#
# By default this removes EVERYTHING Platterpus created, so a reinstall starts
# fresh: the 'ripping' container and its image (when no other container uses
# it), the host-exported tools in ~/.local/bin, menu and desktop shortcuts, the
# AppImages, the cyanrip build cache, MusicBrainz Picard with its data, test-run
# folders, settings, logs, and a source checkout's .venv.
#
# Kept unless you ask: your rips (--remove-rips deletes the folder your
# settings name), and Distrobox/podman (--remove-system-packages, offered only
# when Platterpus installed them). The cloned repo itself is never touched.
#
# This file is a thin launcher. The list of what to remove, and the code that
# removes it, is src/platterpus/deps/ (install_footprint.py, host_teardown.py,
# uninstall_cli.py) — the same code the in-app Tools → Uninstall uses, so the
# two cannot drift apart again (TASKS R190).
#
# Usage:
#   bash uninstall.sh                  show the plan, ask, then remove
#   bash uninstall.sh --dry-run        show the plan; change nothing
#   bash uninstall.sh --yes            remove without asking
#   bash uninstall.sh --keep-settings --keep-logs --keep-picard   keep those
#   bash uninstall.sh --remove-rips    ALSO delete your rips
#   bash uninstall.sh --full           accepted for old scripts (now the default)
#   bash uninstall.sh --help

set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"

# A Python new enough for Platterpus (3.12+), first match wins.
find_python() {
    local candidate
    for candidate in python3.14 python3.13 python3.12 python3; do
        if command -v "$candidate" >/dev/null 2>&1 \
            && "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 12))' 2>/dev/null; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

# 1. A source checkout with its own .venv (dev-setup.sh made it).
if [ -x "$here/.venv/bin/python" ] \
    && "$here/.venv/bin/python" -c 'import platterpus' 2>/dev/null; then
    exec "$here/.venv/bin/python" -m platterpus.deps.uninstall_cli \
        --repo-root "$here" "$@"
fi

# 2. A source checkout without a working .venv: run its source directly. The
#    uninstaller needs only the standard library and Platterpus itself.
if [ -d "$here/src/platterpus" ] && py="$(find_python)"; then
    PYTHONPATH="$here/src${PYTHONPATH:+:$PYTHONPATH}" exec "$py" \
        -m platterpus.deps.uninstall_cli --repo-root "$here" "$@"
fi

# 3. The copy staged next to the AppImage (no checkout): open the app's own
#    uninstaller window, which removes the same list.
shopt -s nullglob
for app in "$HOME/Applications"/platterpus*.AppImage; do
    if [ -x "$app" ]; then
        echo "Opening the uninstaller window from $app"
        exec "$app" --uninstall
    fi
done
shopt -u nullglob

echo "Could not find Platterpus here (no source checkout, no AppImage in" >&2
echo "$HOME/Applications). If anything is left, see the README's Uninstall section." >&2
exit 1
