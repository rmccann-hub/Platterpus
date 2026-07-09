#!/usr/bin/env bash
# Set up a local cyanrip soft-fork checkout for the colon-fix contribution.
#
# Run this LOCALLY (or in a Claude session seeded with the fork) — this
# Platterpus cloud session is scoped to this repo and can't reach cyanrip.
# It only does the mechanical git scaffolding from docs/cyanrip-soft-fork.md §1;
# the code edit (apply-colon-fix.py) and the GitHub actions (issue/PR) are
# separate, deliberate steps.
#
# Prereq: fork cyanreg/cyanrip on GitHub first (click "Fork" → it lands as
# <owner>/cyanrip). This script clones YOUR fork, wires the upstream remote,
# fast-forwards master, and cuts the fix/meta-colon topic branch.
#
# Usage:
#   scripts/cyanrip/setup-fork.sh [FORK_OWNER] [DEST_DIR]
#     FORK_OWNER  GitHub owner of your fork   (default: rmccann-hub)
#     DEST_DIR    where to clone              (default: ./cyanrip)
set -euo pipefail

FORK_OWNER="${1:-rmccann-hub}"
DEST_DIR="${2:-cyanrip}"
FORK_URL="https://github.com/${FORK_OWNER}/cyanrip"
UPSTREAM_URL="https://github.com/cyanreg/cyanrip"
TOPIC_BRANCH="fix/meta-colon"

echo "→ cloning your fork: ${FORK_URL}"
if ! git clone "${FORK_URL}" "${DEST_DIR}"; then
  echo
  echo "Clone failed. Fork cyanreg/cyanrip first:"
  echo "  open ${UPSTREAM_URL} and click 'Fork' (lands as ${FORK_OWNER}/cyanrip),"
  echo "  or with the GitHub CLI:  gh repo fork cyanreg/cyanrip --clone=false"
  exit 1
fi

cd "${DEST_DIR}"
echo "→ wiring the upstream remote + fast-forwarding master"
git remote add upstream "${UPSTREAM_URL}" 2>/dev/null || true
git fetch upstream
git switch master 2>/dev/null || git switch -c master upstream/master
git merge --ff-only upstream/master || true

echo "→ cutting the topic branch ${TOPIC_BRANCH} off upstream/master"
git switch -c "${TOPIC_BRANCH}" upstream/master

cat <<EOF

Done. You are on ${TOPIC_BRANCH} in $(pwd).

Next:
  1. Apply the colon fix (dry run first):
       python3 ../scripts/cyanrip/apply-colon-fix.py .
       python3 ../scripts/cyanrip/apply-colon-fix.py . --apply
       git diff        # review — it must be a minimal, clean diff
  2. Build + smoke-test (needs the toolchain + a disc):
       ../scripts/cyanrip/build.sh .
  3. Commit one focused change, push to your fork, open the PR:
       git commit -am "cyanrip_main: don't inject positional keys into an explicit key=value tag string"
       git push -u origin ${TOPIC_BRANCH}
       # open the issue with scripts/cyanrip/issue-colon.md, then the PR with pr-colon.md
EOF
