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
#
# **PRESENT IS NOT THE SAME AS WORKING, and the difference cost a whole run in
# this test suite before it could cost one on the rig.** The first version
# checked `command -v systemd-inhibit` only. But `systemd-inhibit` fails with
# *"Failed to connect to bus: No such file or directory"* and **exit 1** whenever
# there is no session bus to talk to — an ssh login, a cron job, a container, a
# user systemd unit without `DBUS_SESSION_BUS_ADDRESS`. It is installed on all of
# those. So the prefix would be adopted, the very first command under it would
# fail instantly, and `RUN_STATUS` would be **1 from the inhibitor** — with the
# AppImage never executed at all. A night spent doing nothing, and (worse, after
# the banner below was added) reported as a probable wrong-ripper abort. A
# misdiagnosis is worse than no diagnosis.
#
# So the capability is PROBED, not inferred from the binary existing: run the
# real thing over `true` and adopt the prefix only if that actually worked. Two
# lines, and it converts an unrecoverable silent failure into the loud downgrade
# that was always intended.
INHIBIT=()
if command -v systemd-inhibit >/dev/null 2>&1 &&
   systemd-inhibit --what=idle --who=Platterpus --why="capability probe" \
                   --mode=block true >/dev/null 2>&1; then
  INHIBIT=(systemd-inhibit
    --what=idle:sleep:handle-lid-switch
    --who=Platterpus
    --why="overnight acceptance run"
    --mode=block)
  printf 'Sleep/idle/lid suspend is HELD OFF for the duration of this run.\n'
  printf 'The lock is released automatically when it finishes — nothing to undo.\n\n'
elif command -v systemd-inhibit >/dev/null 2>&1; then
  printf '!! systemd-inhibit is installed but could not take a lock (usually no\n'
  printf '!! session bus — an ssh or cron invocation). The run will proceed\n'
  printf '!! WITHOUT the lock, so this machine MAY SUSPEND mid-rip. Run it from a\n'
  printf '!! desktop terminal, or disable sleep by hand, if you can.\n\n'
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
STARTED_AT="$(date -u +%s)"
"${INHIBIT[@]}" "$APPIMAGE" --run-script "$SCRIPT" || RUN_STATUS=$?
ELAPSED=$(( $(date -u +%s) - STARTED_AT ))

printf '\n'
printf '=============================================================\n'
printf '  RUN FINISHED — exit %s after %ss. Collecting artifacts...\n' \
       "$RUN_STATUS" "$ELAPSED"
printf '=============================================================\n\n'

# **A TWO-SECOND ABORT AND A SIX-HOUR RUN LOOK THE SAME AT 2AM.** On 2026-08-27
# the acceptance script aborted correctly at its section-A precondition — wrong
# ripper installed — in about two seconds, printed the reason, and the operator
# went to bed on a run that had already stopped. Nothing was broken; the whole
# night was spent because a real abort scrolled past like progress.
#
# This is presentation, NOT a second check: the wrapper does not re-decide
# anything about the ripper. It reads the exit status the run already produced
# and the wall-clock it already knows, and refuses to let the pair go unnoticed.
# Adding a ripper check here would be the "two surfaces, one question" defect
# this very run was aborted by.
#
# The threshold is deliberately generous. Section A alone takes seconds; the
# first rip takes many minutes. Anything under two minutes did not reach a rip,
# whatever the reason, and the operator needs to know that BEFORE going to bed.
if [ "$RUN_STATUS" -ne 0 ] && [ "$ELAPSED" -lt 120 ]; then
  printf '#############################################################\n'
  printf '##  STOP — READ THIS BEFORE GOING TO BED                   ##\n'
  printf '#############################################################\n'
  printf '##  The run exited %-3s after only %ss. It did NOT reach a\n' \
         "$RUN_STATUS" "$ELAPSED"
  printf '##  rip — it stopped on a PRECONDITION, and the reason is\n'
  printf '##  printed above this banner (scroll up).\n'
  printf '##\n'
  printf '##  The commonest cause is the wrong cyanrip build installed.\n'
  printf '##  The failing step prints the ONE command that fixes it.\n'
  printf '##  Fix that, then run this script again.\n'
  printf '##\n'
  printf '##  Artifacts are still being collected, so the bundle below\n'
  printf '##  is worth uploading either way — it carries the reason.\n'
  printf '#############################################################\n\n'
fi

# The collector, run under the same lock: it tars up to a few hundred megabytes
# and a suspend part-way through a `tar` produces a truncated archive that still
# looks like an archive.
"${INHIBIT[@]}" bash "$COLLECT"

printf '\n'
printf '=============================================================\n'
printf '  DONE. Acceptance run exit code was %s.\n' "$RUN_STATUS"
printf '  The ONE file to upload is named above, in ~/Downloads.\n'
printf '=============================================================\n\n'
