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
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

repo="${CLAUDE_PROJECT_DIR:-$(pwd)}"
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
