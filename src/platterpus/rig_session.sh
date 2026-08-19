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

# 5a. -x / --cache-probe. NO LONGER RUN — and this is the second site of one fix.
#
#     It was executed on a real drive for the first time on 2026-08-19 (BDR-209D,
#     `platterpus-fork-gddf7ac3`), which is what this step existed for, and it
#     answered: `Cache probe: 32 sectors, 73.5 KiB, uncached read 362.6 ms`.
#
#     **And then it went on to rip the entire disc** — ETA 1h 3m. Which means this
#     step, in the command a person is told to run *after every rig pass*, spent
#     five minutes ripping the disc into `$OUT/scratch`, held the drive, and left
#     an unreapable child behind (`exit: 124`, then nothing to reap). A "probe"
#     that costs five minutes of drive time and leaves the device busy is not a
#     diagnostic; it is the thing that breaks the diagnosis after it.
#
#     The rig script `docs/rig-scripts/rigcancelandoverread.txt` dropped its own
#     `-x` step the same day. This is the SAME defect at a second call site, and
#     finding it required looking for the call rather than fixing the place the
#     lesson was learned (`docs/testing.md` §5.o). Grep before believing a fix is
#     complete.
#
#     It comes back when the fork ships a build whose `-x` exits after measuring;
#     that is an ask on them (`docs/cyanrip-handshake.md`). The measurement above
#     is recorded so the number is not lost with the step, and the single home for
#     the flag's behaviour is `docs/dependency-contracts.md`.
say "5a  their cache probe (-x) — NOT RUN, deliberately"
note "measured once on 2026-08-19: Cache probe: 32 sectors, 73.5 KiB, uncached read 362.6 ms"
note "it then rips the whole disc (ETA 1h 3m) and leaves the drive held, so this"
note "harness no longer runs it. Returns when the fork's -x exits after measuring."
note "This is a recorded omission, not a skipped check: see docs/dependency-contracts.md."

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


# =============================================================================
# PART 2 — added for v0.6.4b7. Everything below needs no disc and no human.
#
# The maintainer's ask: *"emphasize automation, and give me files (macros, for
# example) and such to do this for you and complete as many tests as possible.
# Do this for both Platterpus and Cyanrip as much as possible so we can do a
# bunch at once."* So this half runs BOTH sides' checkable surfaces in one go.
# =============================================================================

say "10  ETA sanity — the 62-hour bug, checked against THIS rip's own trace"
# The b6 rip's report contained 383 ETA samples and one of them read 3715
# minutes. Every report on this machine is now swept for a repeat, so the fix is
# verified against real artifacts rather than only against the unit test.
python3 - "$HOME/Music" >"$OUT/10-eta-sweep.txt" 2>&1 <<'PY' || true
import json, pathlib, sys
roots = [pathlib.Path(sys.argv[1])] if len(sys.argv) > 1 else []
worst = []
checked = 0
for root in roots:
    for path in root.rglob("*.platterpus.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, ValueError) as exc:
            print(f"UNREADABLE {path}: {exc}")
            continue
        samples = (data.get("eta_trace") or {}).get("samples") or []
        if not samples:
            continue
        checked += 1
        peak = max((s.get("our_eta_seconds") or 0) for s in samples)
        worst.append((peak, len(samples), path.name))
        flag = "  <-- ABSURD" if peak > 24 * 3600 else ""
        print(f"{peak/3600:8.2f}h peak   {len(samples):5d} samples   {path.name}{flag}")
print()
print(f"reports with an ETA trace: {checked}")
if not checked:
    print("NO REPORTS WITH A TRACE FOUND — that is a real result, not a pass:")
    print("  either no rip has run under a version that records one, or ~/Music is elsewhere.")
else:
    absurd = [w for w in worst if w[0] > 24 * 3600]
    print(f"absurd (>24h) peaks: {len(absurd)}  <-- must be 0 from v0.6.4b7 on")
PY
note "artifact: 10-eta-sweep.txt"

say "11  report sizes — the 1.5 MB JSON, and whether retention is holding"
# EVERY command here is `|| true`-guarded. `ls` on a glob that matches nothing
# exits 2, and with errexit on that killed the entire script mid-step — found by
# actually running it, not by reading it. A step that finds nothing must record
# "nothing" and continue.
{
  echo "== per-album report sizes (81% of the b6 one was the embedded debug log) =="
  find "$HOME/Music" -name '*.platterpus.json' -printf '%10s  %p\n' 2>/dev/null \
      | sort -rn | head -12 || true
  echo
  echo "== app log retention (8 MiB x 10 from v0.6.4b7; was 1 MiB x 5) =="
  ls -la "$HOME/.local/share/platterpus/"log.txt* 2>/dev/null \
      || echo "(no app logs found at that path — recorded, not skipped)"
  echo
  echo "A file at EXACTLY the max size is FULL, which is how the old 1 MiB window"
  echo "silently evicted the rip you were trying to diagnose."
} >"$OUT/11-sizes.txt" 2>&1
note "artifact: 11-sizes.txt"

say "12  the fork's own test suite, IN A CLEAN CLONE (their lap 25 §C1 lesson)"
# Their beta.3 note claimed "28/28 from a clean checkout" and it was false for
# anyone who cloned: `git clone` makes a local branch only for the remote HEAD,
# so `master` was unreachable and version_matrix failed. Verifying in the tree
# that produced the artifact is not verifying what a consumer gets — so this
# clones fresh rather than using any existing checkout.
if command -v git >/dev/null 2>&1; then
  CLONE="$OUT/scratch/cyanrip-clean"
  rm -rf "$CLONE"
  run "    clone the fork" "12-fork-clone.txt" \
      git clone --quiet https://github.com/rmccann-hub/cyanrip "$CLONE"
  if [ -d "$CLONE" ]; then
    ( cd "$CLONE" && git log --oneline -1 && git branch -a ) \
        >>"$OUT/12-fork-clone.txt" 2>&1 || true
    note "clone present — run their suite there per their beta note"
  else
    note "!! clone failed (no network, or the repo is private) — recorded, not skipped"
  fi
else
  note "git absent — cannot do the clean-clone check"
  echo "skipped: no git" >"$OUT/12-fork-clone.txt"
fi

say "13  our own gates, so a rig session also proves the app's build is sane"
if [ -f pyproject.toml ]; then
  run "    handshake status"  "13-handshake-status.txt" python3 scripts/handshake.py --status
  run "    doctor (no network)" "14-preflight.txt" python3 scripts/preflight.py --no-network
else
  note "not in a checkout — skipping the repo-side gates"
  # BOTH artifacts, not just the first. The script's own contract is that every step
  # writes a file even when it finds nothing, so a step that did not run is
  # distinguishable from one that passed — and this branch was writing 13 and
  # silently omitting 14. Found by the smoke test, which counts artifacts.
  echo "skipped: not in a checkout" >"$OUT/13-handshake-status.txt"
  echo "skipped: not in a checkout" >"$OUT/14-preflight.txt"
fi

# ------------------------------------------------- the rip that just happened --
#
# WHY THIS IS HERE RATHER THAN IN A CHECKLIST (maintainer, 2026-08-07: *"these
# types of things are for the testing script to automate and manage"*). The rip
# itself is done by a person in the GUI — that part is genuinely manual. But
# everything *after* it is mechanical: find the rip, audit it, collect the text
# artifacts, bundle them. Handing that back as a list of commands to type is
# exactly the work this script exists to absorb.
#
# NOTHING HERE NEEDS AN ARGUMENT. The newest rip is discovered, not named: a
# folder the operator has to type is a folder they can mistype, and the mistake
# is silent because auditing the *wrong* album still produces a clean-looking
# report.

say "15  the most recent rip, found rather than named"

# Where rips land. Read from the user's own config when it is there, so this
# follows a changed output folder instead of assuming the default. `grep` on one
# TOML line rather than a parser: the value is a quoted string on its own line,
# and a missing/odd config falls through to the defaults below.
CONFIG="$HOME/.config/platterpus/config.toml"
SEARCH_DIRS=()
if [ -f "$CONFIG" ]; then
  CONFIGURED="$(sed -n 's/^[[:space:]]*output_dir[[:space:]]*=[[:space:]]*"\(.*\)"[[:space:]]*$/\1/p' "$CONFIG" | head -n 1)"
  [ -n "${CONFIGURED:-}" ] && [ -d "$CONFIGURED" ] && SEARCH_DIRS+=("$CONFIGURED")
  LIBRARY="$(sed -n 's/^[[:space:]]*library_dir[[:space:]]*=[[:space:]]*"\(.*\)"[[:space:]]*$/\1/p' "$CONFIG" | head -n 1)"
  [ -n "${LIBRARY:-}" ] && [ -d "$LIBRARY" ] && SEARCH_DIRS+=("$LIBRARY")
fi
[ -d "$HOME/Music" ] && SEARCH_DIRS+=("$HOME/Music")
note "searching: ${SEARCH_DIRS[*]:-<none>}"

NEWEST_REPORT=""
if [ ${#SEARCH_DIRS[@]} -gt 0 ]; then
  # Newest by mtime. `-print0` + `sort -z` so a path with spaces or a newline in
  # an album title cannot split a filename in half — album titles are user data
  # and this project has already been bitten by a colon in one.
  NEWEST_REPORT="$(find "${SEARCH_DIRS[@]}" -name '*.platterpus.json' -type f -printf '%T@\t%p\0' 2>/dev/null \
    | sort -z -rn | head -z -n 1 | tr -d '\0' | cut -f2-)"
fi

if [ -z "${NEWEST_REPORT:-}" ]; then
  # A REAL RESULT, not a skip. If this script runs before any rip exists, saying
  # so is the honest answer; going quiet would look identical to a clean audit.
  note "!! no .platterpus.json found — either no rip has happened yet, or rips"
  note "   land somewhere none of the searched directories cover. NOT a pass."
  echo "no rip report found under: ${SEARCH_DIRS[*]:-<none>}" >"$OUT/15-newest-rip.txt"
  echo "skipped: no rip to audit" >"$OUT/16-audit.txt"
else
  ALBUM_DIR="$(dirname "$NEWEST_REPORT")"
  note "newest rip: $ALBUM_DIR"
  {
    echo "report:      $NEWEST_REPORT"
    echo "album dir:   $ALBUM_DIR"
    echo "modified:    $(date -u -r "$NEWEST_REPORT" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo unknown)"
    echo
    echo "--- directory listing (audio sizes only; no audio is copied) ---"
    ls -la "$ALBUM_DIR"
  } >"$OUT/15-newest-rip.txt" 2>&1

  # The graded artifact checks — including the two the cyanrip fork asked for
  # (`handshake_note`, `checksum_inventory`). Runs through the app so an AppImage
  # user needs no checkout.
  if [ -x "$APP" ]; then
    run "    audit the rip" "16-audit.txt" "$APP" --audit-rips "$ALBUM_DIR"
  elif [ -f pyproject.toml ]; then
    run "    audit the rip" "16-audit.txt" python3 -m platterpus --audit-rips "$ALBUM_DIR"
  else
    note "!! no way to run the audit — neither the AppImage nor a checkout"
    echo "skipped: no runnable Platterpus" >"$OUT/16-audit.txt"
  fi

  # ---- a DOUBLE rip, if one happened ----------------------------------------
  #
  # Ripped the disc twice? Then the interesting artifact is not either rip, it is
  # the DIFF: which tracks came back byte-identical and which changed. That is
  # the finding the whole double-pass exercise exists to produce.
  #
  # No arguments. `--compare` with none discovers the newest rip and the best
  # earlier rip OF THE SAME DISC, which is the part worth getting right: pairing
  # by recency alone would diff two different albums and print a confident table
  # doing it. Exit 1 means "nothing to compare" -- a single rip, not a failure --
  # so it does not fail the session; the reason is recorded either way.
  say "17b the double-rip diff, if a second pass exists"
  if [ -x "$APP" ]; then
    run "    compare passes" "17b-compare.txt" "$APP" --compare
  elif [ -f pyproject.toml ]; then
    run "    compare passes" "17b-compare.txt" python3 -m platterpus --compare
  else
    note "!! no way to run the comparison — neither the AppImage nor a checkout"
    echo "skipped: no runnable Platterpus" >"$OUT/17b-compare.txt"
  fi

  # ---- the seam check, our half ---------------------------------------------
  #
  # The cyanrip fork's script writes into the SAME directory and appends to the
  # same MANIFEST.txt, so the two projects' evidence is one upload rather than
  # two piles a person has to reconcile. It is read-only; the heavy check inside
  # it composes a real rip's argv, runs it against a device that cannot open, and
  # reads the invocation back out of cyanrip's own -j record — which is the one
  # argv question that can be settled without spending a disc.
  say "17  the cyanrip seam check (our half; theirs appends to the same manifest)"
  if [ -x "$APP" ]; then
    run "    rig check" "17-rig-check.txt" \
        "$APP" --rig-check "$OUT/seam" --rig-check-album "$ALBUM_DIR"
  elif [ -f pyproject.toml ]; then
    run "    rig check" "17-rig-check.txt" \
        python3 -m platterpus --rig-check "$OUT/seam" --rig-check-album "$ALBUM_DIR"
  else
    note "!! no way to run the seam check — neither the AppImage nor a checkout"
    echo "skipped: no runnable Platterpus" >"$OUT/17-rig-check.txt"
  fi

  # ---- collect the TEXT artifacts, and only the text artifacts --------------
  #
  # CRITICAL RULE #8: no copyrighted media, ever, not even temporarily. The
  # evidence we need is entirely textual — the logs, the cue, the JSON reports —
  # and the CRCs inside them prove bit-perfection without the audio. The
  # extension list below is an ALLOW-list for exactly that reason: a deny-list of
  # audio extensions would silently start copying the first format we forgot.
  say "18  collect the rip's text artifacts (never the audio)"
  COLLECT="$OUT/rip-artifacts"
  mkdir -p "$COLLECT"
  COPIED=0
  while IFS= read -r -d '' f; do
    cp -- "$f" "$COLLECT/" 2>/dev/null && COPIED=$((COPIED + 1))
  done < <(find "$ALBUM_DIR" -maxdepth 1 -type f \
             \( -name '*.log' -o -name '*.cue' -o -name '*.txt' -o -name '*.json' \
                -o -name '*.md5' -o -name '*.sha256' \) -print0 2>/dev/null)
  note "copied $COPIED text artifact(s) — audio deliberately excluded"
  ls -1 "$COLLECT" 2>/dev/null | sed 's/^/      /' | tee -a "$SUMMARY" || true
  if [ "$COPIED" -eq 0 ]; then
    note "!! zero artifacts copied from a rip folder that exists — that is a finding"
  fi
fi

# ------------------------------------------------------------------- done ----
say "COMPLETE"
note "artifacts:"
ls -1 "$OUT" | sed 's/^/      /' | tee -a "$SUMMARY" || true
note ""
note "Every file matters, including the empty ones — an artifact that exists and"
note "is empty is a measurement; a missing artifact is a step that did not run,"
note "and only one of those is a result."

# ---- one file to send ------------------------------------------------------
#
# The last manual step this script can remove. "Send the whole directory" means
# the operator selects, compresses and uploads N files, and a directory upload
# that silently drops one is indistinguishable from a step that never ran. One
# archive, named for itself, is one thing to attach.
#
# `tar` failing is not fatal: the directory is still there and still complete, so
# the fallback is to say so rather than to lose the session.
ARCHIVE="$OUT.tar.gz"
if command -v tar >/dev/null 2>&1; then
  if tar -czf "$ARCHIVE" -C "$(dirname "$OUT")" "$(basename "$OUT")" 2>/dev/null; then
    note ""
    note "SEND THIS ONE FILE:"
    note "    $ARCHIVE   ($(wc -c <"$ARCHIVE") bytes)"
    note ""
    note "It contains no audio — only logs, cue sheets and JSON reports."
  else
    note "!! could not build the archive; send the directory instead: $OUT"
  fi
else
  note "tar is absent; send the directory instead: $OUT"
fi
