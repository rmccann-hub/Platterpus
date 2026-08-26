#!/usr/bin/env bash
# =============================================================================
# THE OVERNIGHT RUN — one command, sleep held off, one file in ~/Downloads
# =============================================================================
#
#   Run it:   bash platterpusovernight.sh
#   Then:     go to bed. In the morning, upload the ONE file it names.
#
# Put a disc in the drive first. Nothing else.
#
# -----------------------------------------------------------------------------
# WHY THIS EXISTS
# -----------------------------------------------------------------------------
# The pieces all existed and the operator was being asked to chain them:
# inhibit sleep, run the acceptance script, wait, then remember to run the
# collector in the morning. That is three commands and one thing to remember,
# and `CLAUDE.md` is explicit that a procedure handed back in prose is a symptom
# rather than a deliverable — *"never hand back an instruction file; hand back
# three steps and a file to run."* Every hand-run step here is a step the
# software was supposed to do.
#
# So this script is one caller of the two that already exist. It does NOT
# reimplement either: the acceptance run is `--run-script fullacceptance.txt`
# and the collection is `platterpusmorning.sh`, both unchanged. A second
# implementation of either would be a second thing to drift.
#
# -----------------------------------------------------------------------------
# SLEEP — WHY `systemd-inhibit` AND NOT A SETTINGS CHANGE
# -----------------------------------------------------------------------------
# Changing the KDE power settings would (a) persist after the run, silently
# leaving the machine awake forever, and (b) require the operator to remember to
# change it back — the handed-back step again. `systemd-inhibit` takes the lock
# for the LIFETIME OF THE CHILD PROCESS and drops it the instant the child
# exits, including on a crash or a Ctrl-C. Nothing to undo, nothing to remember,
# and no state left behind if the run dies at 3 a.m.
#
# `--what=idle:sleep:handle-lid-switch` covers the three ways this machine can
# stop mid-rip: the idle timer, an explicit suspend, and the lid. `handle-lid-
# switch` is included even on a desktop because it costs nothing and the rig has
# been a laptop before.
#
# **It does NOT stop the screen blanking, deliberately.** A blanked screen is
# harmless — the session keeps running — and inhibiting the screensaver as well
# means leaving the display on all night for nobody. If a *screenshot* step
# needs the display awake, that is a different lock and this is the wrong place
# for it; nothing in `fullacceptance.txt` requires it today.
#
# If `systemd-inhibit` is absent (it should not be on Bazzite), the run proceeds
# WITHOUT the lock and says so loudly rather than refusing. A run that happens
# and might get suspended beats a run that did not happen — but the operator is
# told, because a silent downgrade is how you spend a night and learn nothing.
# =============================================================================

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="${1:-${HERE}/fullacceptance.txt}"
COLLECT="${HERE}/platterpusmorning.sh"

# The AppImage. Searched rather than hardcoded, because it has lived in three
# places across this project's rig sessions and a wrong path here fails at
# midnight with the disc already in the drive.
APPIMAGE=""
for candidate in \
  "${HOME}/Applications/platterpus-x86_64.AppImage" \
  "${HOME}/Downloads/platterpus-x86_64.AppImage" \
  "${HOME}/platterpus-x86_64.AppImage"; do
  if [ -x "$candidate" ]; then APPIMAGE="$candidate"; break; fi
done

if [ -z "$APPIMAGE" ]; then
  printf 'ERROR: no executable platterpus-x86_64.AppImage found in:\n'
  printf '  ~/Applications/  ~/Downloads/  ~/\n\n'
  printf 'Download it, then:  chmod +x <path to it>\n'
  exit 1
fi

if [ ! -f "$SCRIPT" ]; then
  printf 'ERROR: acceptance script not found: %s\n' "$SCRIPT"
  exit 1
fi

if [ ! -f "$COLLECT" ]; then
  printf 'ERROR: collector not found: %s\n' "$COLLECT"
  printf 'It must sit beside this script.\n'
  exit 1
fi

printf '\n'
printf '=============================================================\n'
printf '  PLATTERPUS OVERNIGHT RUN\n'
printf '=============================================================\n'
printf '  app      : %s\n' "$APPIMAGE"
printf '  version  : %s\n' "$("$APPIMAGE" --version 2>&1 | head -1)"
printf '  script   : %s\n' "$SCRIPT"
printf '  started  : %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf '=============================================================\n\n'

# THE SLEEP LOCK. Resolved into an argv prefix rather than branching around the
# whole run twice — two copies of the same long command line is two things to
# keep in step, and only one of them would get the next fix.
INHIBIT=()
if command -v systemd-inhibit >/dev/null 2>&1; then
  INHIBIT=(systemd-inhibit
    --what=idle:sleep:handle-lid-switch
    --who=Platterpus
    --why="overnight acceptance run"
    --mode=block)
  printf 'Sleep/idle/lid suspend is HELD OFF for the duration of this run.\n'
  printf 'The lock is released automatically when it finishes — nothing to undo.\n\n'
else
  printf '!! systemd-inhibit not found. The run will proceed, but this machine\n'
  printf '!! MAY SUSPEND mid-rip. Disable sleep by hand if you can.\n\n'
fi

# The acceptance run. Not `set -e`-fatal: a script run that ends in failures
# still produced artifacts, and those artifacts are the entire point of the
# night. Collecting them is what must not be skipped — an aborted collection
# after a failed run loses the evidence that would explain the failure, which is
# the worst of the three possible outcomes.
RUN_STATUS=0
"${INHIBIT[@]}" "$APPIMAGE" --run-script "$SCRIPT" || RUN_STATUS=$?

printf '\n'
printf '=============================================================\n'
printf '  RUN FINISHED — exit %s. Collecting artifacts...\n' "$RUN_STATUS"
printf '=============================================================\n\n'

# The collector, run under the same lock: it tars up to a few hundred megabytes
# and a suspend part-way through a `tar` produces a truncated archive that still
# looks like an archive.
"${INHIBIT[@]}" bash "$COLLECT"

printf '\n'
printf '=============================================================\n'
printf '  DONE. Acceptance run exit code was %s.\n' "$RUN_STATUS"
printf '  The ONE file to upload is named above, in ~/Downloads.\n'
printf '=============================================================\n\n'
