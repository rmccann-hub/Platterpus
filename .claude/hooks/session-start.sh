#!/bin/bash
# Switch on the audio guard in a cloud session (CLAUDE.md Critical rule #8).
#
# `.githooks/pre-commit` refuses a commit that stages a music file. Git runs it
# only once `core.hooksPath` points at `.githooks`, and `dev-setup.sh` is what
# sets that. A Claude Code session on the web starts from a fresh clone that
# never ran `dev-setup.sh`, so the guard was off there. This turns it on.
#
# Only in a cloud session (`CLAUDE_CODE_REMOTE=true`): locally `dev-setup.sh` does
# the job, and a developer's own git config is theirs to set. Idempotent, and it
# never fails the session. A guard that cannot be set is reported, not fatal,
# because the agent-side PreToolUse hook (`.claude/hooks/audio_guard.py`) still
# blocks a commit or push while audio is staged, and a command that stages it.
#
# It also keeps the `evidence` branch out of every fetch (HR-2 §7, agreed
# 2026-10-14): run evidence lives on that orphan branch, hundreds of MB that no
# build reads, and a tool that needs one file fetches that commit by hash into a
# temporary repository. A negative refspec (`^refs/heads/evidence`, git 2.29 or
# later) is added to each remote's fetch lines, in every session, local or cloud.
# It cannot change the clone made before hooks run, so it shrinks later fetches,
# not the first download. Where hooks do not run, CLAUDE.md gives the same lines.
set -euo pipefail

repo="${CLAUDE_PROJECT_DIR:-$(pwd)}"

exclude_evidence() {
  local version major minor remote
  version="$(git --version 2>/dev/null | sed -n 's/^git version \([0-9]*\)\.\([0-9]*\).*/\1 \2/p')"
  read -r major minor <<<"${version:-0 0}"
  if [ "${major:-0}" -lt 2 ] || { [ "$major" -eq 2 ] && [ "${minor:-0}" -lt 29 ]; }; then
    echo "session-start: git older than 2.29 has no negative refspecs; evidence is not excluded from fetches" >&2
    return 0
  fi
  for remote in $(git -C "$repo" remote 2>/dev/null); do
    if ! git -C "$repo" config --get-all "remote.$remote.fetch" >/dev/null 2>&1; then
      continue
    fi
    if git -C "$repo" config --get-all "remote.$remote.fetch" | grep -qxF '^refs/heads/evidence'; then
      continue
    fi
    if git -C "$repo" config --add "remote.$remote.fetch" '^refs/heads/evidence'; then
      echo "session-start: $remote no longer fetches the evidence branch" >&2
    else
      echo "session-start: could not exclude evidence from $remote's fetches" >&2
    fi
  done
}
exclude_evidence || true

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

if [ ! -x "$repo/.githooks/pre-commit" ]; then
  echo "session-start: no executable .githooks/pre-commit in $repo; audio guard not set" >&2
  exit 0
fi
if [ "$(git -C "$repo" config --get core.hooksPath 2>/dev/null || true)" = ".githooks" ]; then
  exit 0
fi
if git -C "$repo" config core.hooksPath .githooks; then
  echo "session-start: audio guard on (core.hooksPath=.githooks)" >&2
else
  echo "session-start: could not set core.hooksPath; audio guard is OFF for git commits" >&2
fi
exit 0
