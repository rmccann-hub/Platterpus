#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
#
# Unattended half of a rig session. Everything here runs without a person
# watching, captures its own output, and writes one artifact per step.
#
# THE POINT (cyanrip fork, lap 24 §E2): *"the rig session is the scarce resource;
# anything that runs unattended and writes an artifact is worth more than a
# checklist line."* So the checklist is now only the steps that genuinely need a
# human — insert a disc, click Cancel, watch a window — and this script does the
# rest.
#
# NEVER SILENT: every step announces itself, records its exit code, and writes a
# file even when it finds nothing. A step that produced no artifact is
# distinguishable from one that passed, which the returned session sheet with
# three ticks is the reason for.
#
# Usage:
#   bash scripts/rig_session.sh <output-dir> [path-to-appimage]
#
# Safe to re-run: it only reads, probes and writes into <output-dir>.

# ERREXIT IS ON, and every probe explicitly opts out of it — which is the honest
# way to satisfy both requirements at once.
#
# `tests/test_security_no_shell.py::test_shell_scripts_enable_errexit` requires
# `set -e` in every shipped script, and it is right to: a script that silently
# continues past a failed step is the shell-side version of the swallowed error
# this project keeps finding. But this script's whole purpose is that **a failing
# probe is data** — `-x` wedging IS the measurement — so it must not abort.
#
# The first draft resolved that by dropping `-e` and explaining why in a comment.
# That is exactly the shape CLAUDE.md refuses: weakening a check because your case
# feels special. So errexit stays on, and `run()` neutralises it per-call with an
# `if ! …` guard, which keeps the exemption visible at each site instead of
# implicit for the whole file.
set -euo pipefail

OUT="${1:?usage: rig_session.sh <output-dir> [appimage]}"
APP="${2:-$HOME/Applications/platterpus-x86_64.AppImage}"
RIPPER="$HOME/.local/bin/cyanrip"

mkdir -p "$OUT"
SUMMARY="$OUT/00-summary.txt"
: >"$SUMMARY"

say() { printf '\n=== %s\n' "$*" | tee -a "$SUMMARY"; }
note() { printf '    %s\n' "$*" | tee -a "$SUMMARY"; }

# Run a command, tee it to its own artifact, and record the exit code in the
# summary. The exit code is recorded even on success — a "silent success" is
# still a fact, and this project has been bitten by not logging one.
run() {
  local label="$1" file="$2"; shift 2
  say "$label"
  note "argv: $*"
  # `|| rc=$?` — a command followed by `||` does not trigger errexit, so the
  # failure becomes a value instead of a fatal.
  #
  # **NOT `if ! "$@"; then rc=$?; fi`**, which was the first version and was
  # wrong in the worst possible direction: `!` inverts the status, so `$?` inside
  # the branch is **0** and every failure was recorded as `exit: 0`. A script
  # whose whole purpose is that a failing step is visible, silently reporting
  # success for all of them. Caught by the smoke test's floor — "with every binary
  # absent, at least one non-zero exit must be recorded" — which is the only
  # assertion that could have caught it, since the artifacts were all present and
  # the script exited 0 either way.
  local rc=0
  "$@" >"$OUT/$file" 2>&1 || rc=$?
  note "exit: $rc   artifact: $file ($(wc -c <"$OUT/$file") bytes)"
  return 0   # never propagate: the caller reads the artifact, not our status
}

say "rig session $(date -u +%Y-%m-%dT%H:%M:%SZ)"
note "app:    $APP"
note "ripper: $RIPPER"
note "out:    $OUT"

# ---------------------------------------------------------------- identity ---
# P1/P3 from the sheet, automated. These are the two facts every later claim
# depends on, and both have been left blank on a returned sheet before.
run "P1  app version"      "01-app-version.txt"    "$APP" --version
run "P3  ripper banner"    "02-ripper-version.txt" "$RIPPER" --version

if grep -qE -- '-dirty|-grelease|-gunknown' "$OUT/02-ripper-version.txt" 2>/dev/null; then
  note "!! BANNER IS NOT A VALID TEST BUILD — -dirty/-grelease/-gunknown. STOP AND REPORT."
fi

# ------------------------------------------------------------------ doctor ---
run "P4  doctor"           "03-doctor.txt"         "$APP" --doctor

# ------------------------------------------- the fork's two unsent flags ------
# Our argv surface is 16 flags and contains neither -x nor -j, so these are
# direct invocations of their binary. Scratch dir; nothing touches the library.
mkdir -p "$OUT/scratch"

# 5a. -x / --cache-probe. Never executed on a real drive, anywhere, ever (their
#     AUDIT §3.1). It refuses on a disc image, so a physical disc is the only
#     way. A HANG IS ALSO A RESULT: beta.3 reports a stall rather than wedging
#     silently, which is why this is worth a track. Bounded so an unattended run
#     cannot sit forever.
run "5a  their cache probe (-x)" "04-cache-probe.txt" \
    timeout 300 "$RIPPER" -x -D "$OUT/scratch" -o flac -N
if grep -q "^    exit: 124" "$SUMMARY"; then
  note "!! A STEP TIMED OUT (exit 124) — if it was -x, that is the wedge case. SEND THIS."
fi

# 5b. -j / --diagnostics. Never written by a rip from a physical drive.
run "5b  their diagnostics record (-j)" "05-minus-j.txt" \
    timeout 600 "$RIPPER" -j "$OUT/scratch/diag.json" -D "$OUT/scratch" \
                -o flac -N -l 1 -u "platterpus/rig-session"
if [ -s "$OUT/scratch/diag.json" ]; then
  note "diag.json written: $(wc -c <"$OUT/scratch/diag.json") bytes"
else
  note "!! diag.json NOT written — say so; absence is the finding"
fi

# ------------------------------------------------------------ A25 screening ---
# The discriminating string is the SOURCE line, not the LSN line. Corrected
# 2026-08-04: cyanrip reads pre-gaps from the sub-channel now, so "Pregap LSN"
# != none hits on almost any disc and answers nothing.
say "1   A25 pre-gap screening (reads the app log; no rip)"
LOGS=("$HOME/.local/share/platterpus/log.txt"
      "$HOME/.local/share/platterpus/log.txt".[0-9])
if ! grep -h "Pregap source:" "${LOGS[@]}" 2>/dev/null \
     | sed 's/.*Pregap source:/Pregap source:/' | sort | uniq -c | sort -rn \
     >"$OUT/06-pregap-sources.txt"; then
  note "no Pregap source: lines in the retained log — recorded, not skipped"
fi
TOC_HITS=$(grep -c "Pregap source: TOC" "$OUT/06-pregap-sources.txt" 2>/dev/null || echo 0)
note "artifact: 06-pregap-sources.txt"
if [ "${TOC_HITS:-0}" -gt 0 ]; then
  note "** A TOC-SOURCED PRE-GAP EXISTS — that is the C1 candidate. Name the disc."
else
  note "no TOC-sourced pre-gap in the retained log — a REAL RESULT, not a gap"
fi

# ------------------------------------------------------------ log snapshot ---
# Copy the logs BEFORE anything else rotates them. 1 MiB x 5 is a small window
# and using the app keeps consuming it; a rotated-out file is gone silently.
say "0   snapshot the app logs (do this early — rotation is silent)"
mkdir -p "$OUT/logs"
if ! cp -v "$HOME/.local/share/platterpus/log.txt"* "$OUT/logs/" \
     >"$OUT/07-log-snapshot.txt" 2>&1; then
  note "!! could not copy the app logs — see 07-log-snapshot.txt"
fi
note "artifact: 07-log-snapshot.txt  ($(ls -1 "$OUT/logs" | wc -l) files)"

# ---------------------------------------------------------------- the rips ---
# Anything already ripped under ~/Music gets audited and parity-checked. Run
# this AFTER the Police rip; re-running is harmless.
say "3   audit every rip found (no disc needed)"
run "    --audit-rips" "08-audit-rips.txt" "$APP" --audit-rips "$HOME/Music"

say "3   EAC parity — the anchor. Needs a checkout; skipped if absent."
BASE="output_reference/EAC_flac/eac_baseline_police_classics.log"
if [ -f "$BASE" ]; then
  mapfile -t CANDIDATES < <(find "$HOME/Music" -name '*.log' \
      -not -name '*EAC*compatible*' -newermt '-3 days' 2>/dev/null | head -20)
  if [ "${#CANDIDATES[@]}" -gt 0 ]; then
    run "    eac_parity.py" "09-eac-parity.txt" \
        python3 scripts/eac_parity.py "$BASE" "${CANDIDATES[@]}"
  else
    note "no candidate rip logs found under ~/Music from the last 3 days"
    echo "no candidates" >"$OUT/09-eac-parity.txt"
  fi
else
  note "not in a checkout ($BASE absent) — run this step from the repo later"
  echo "skipped: not in a checkout" >"$OUT/09-eac-parity.txt"
fi

# ------------------------------------------------------------------- done ----
say "COMPLETE"
note "artifacts:"
ls -1 "$OUT" | sed 's/^/      /' | tee -a "$SUMMARY" || true
note ""
note "Send the whole directory. Every file matters, including the empty ones —"
note "an artifact that exists and is empty is a measurement; a missing artifact"
note "is a step that did not run, and only one of those is a result."
