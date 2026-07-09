#!/usr/bin/env bash
# Build cyanrip from a checkout (meson/ninja) and print the binary + export step.
#
# Run inside the `ripping` Distrobox container (it has FFmpeg/libcdio-paranoia/
# libmusicbrainz5/libcurl + the C toolchain). This is the "build from our pinned
# commit instead of a distro package" step from docs/cyanrip-soft-fork.md §4 —
# the routing to ~/.local/bin/cyanrip is unchanged (Critical Rule #3); only the
# binary's *source* moves.
#
# Usage:  scripts/cyanrip/build.sh [CHECKOUT_DIR]   (default: ./cyanrip)
set -euo pipefail

CHECKOUT="${1:-cyanrip}"
cd "${CHECKOUT}"

for tool in meson ninja; do
  command -v "${tool}" >/dev/null 2>&1 || {
    echo "error: ${tool} not found — run this in the ripping container"; exit 1; }
done

echo "→ meson setup build"
meson setup build --reconfigure 2>/dev/null || meson setup build
echo "→ ninja -C build"
ninja -C build

BIN="$(pwd)/build/src/cyanrip"
COMMIT="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
echo
echo "Built cyanrip @ ${COMMIT}:  ${BIN}"
"${BIN}" -V 2>&1 | head -1 || true
cat <<EOF

To consume it, export this binary to the host as ~/.local/bin/cyanrip exactly
like the host_setup step does (the GUI keeps calling ~/.local/bin/cyanrip — the
Distrobox routing is unchanged). Record the commit (${COMMIT}) so a rip report
can say which cyanrip built it. Rebuild after each rebase onto upstream master.
EOF
