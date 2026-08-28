#!/usr/bin/env bash
# =============================================================================
# THE MORNING AFTER — collect everything the overnight acceptance run produced
# =============================================================================
#
#   Run it:   bash platterpusmorning.sh
#   Then:     upload the ONE file it names at the end.
#
# It takes about a minute, needs no disc, and never touches the drive.
#
# -----------------------------------------------------------------------------
# WHY THIS EXISTS — the app's own bundle does NOT contain your rips
# -----------------------------------------------------------------------------
# Three collection mechanisms already exist and **none of them gathers the
# artifacts an overnight acceptance run actually produces.** Measured by reading
# them, not assumed:
#
#   * The bundle the script run builds itself — the "SEND THIS ONE FILE" line in
#     the app log — calls `evidence_bundle.build_bundle()` WITHOUT `album_dir`
#     (src/platterpus/uiscript/runner.py, the `work()` closure). That parameter
#     is what admits a rip folder's files. So the auto-bundle carries the app log
#     and the script run folder — transcript, report JSON, screenshots — and
#     **not one rip log, cue sheet, EAC log or cyanrip -j record.**
#   * `--rig-session` audits the NEWEST `.platterpus.json` in depth
#     (rig_session.sh, the `NEWEST_REPORT` find) and summarises the rest. Its
#     candidate rip logs feed `eac_parity.py` and are only used if you are inside
#     a repo checkout. It copies no album files either.
#   * `platterpuscollect.sh` takes the newest rip folder only.
#
# The overnight script performs **seven** rips. Collecting "the newest" gets you
# the last one, which is the `-x -I` cache probe's neighbour — not the section-N
# whole-disc uniform secure re-read, which is the single artifact the cyanrip
# handshake round is waiting on. Losing it wastes the entire night, and the loss
# would be silent: the bundle would arrive looking complete.
#
# So this script's ONE job that the others do not do is: **every text artifact
# from every rip folder, not the newest one.** It folds the other mechanisms in
# rather than reimplementing them.
#
# -----------------------------------------------------------------------------
# WHAT IT WILL NEVER DO
# -----------------------------------------------------------------------------
# Copy audio. Critical rule #8 — this repository is public and the bundle gets
# attached to a handshake round. Only the eight text suffixes the app's own
# bundler allows are copied, and the staged tree is then SWEPT for audio with
# the count of files examined printed, because a check that can be satisfied by
# finding nothing needs a floor.
#
# Every external command is bounded with `timeout -k`. A bare `timeout` sends
# SIGTERM and then waits, unbounded, for a child that may be inside a drive
# ioctl in uninterruptible sleep — the timeout that exists to stop a hang
# becomes the hang. That cost this project a whole rig step once.
# =============================================================================

set -euo pipefail
# ERREXIT IS ON, and every tolerated failure below is made explicit rather than
# blanket-permitted. The first version of this script omitted `-e` on the
# reasoning that a collector must not abort on one missing artifact — true, and
# the wrong conclusion. A blanket omission also swallows the failures nobody
# anticipated (a typo, a bad path, an unwritable directory), and those are
# exactly the ones `bad()` cannot report because no one thought to check for
# them. `tests/test_security_no_shell.py::test_shell_scripts_enable_errexit`
# refuses a shipped script without it and has no allowlist, correctly.
#
# So: a command that may legitimately fail carries its own `|| true` or sits in
# an `if`, and says which. Everything else aborts, loudly, as it should. Note
# the `[ x ] && action` idiom is avoided throughout — it evaluates to 1 when the
# test is false, which under `-e` aborts the script on a *non*-event.

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
# The staging tree stays in $HOME; only the ONE archive lands where the operator
# looks for it. Maintainer's instruction, 2026-08-26: the single file goes to
# ~/Downloads, because that is the folder a browser upload dialog opens in and
# hunting for it in $HOME is work handed back.
#
# Falls back to $HOME rather than creating the directory: on a machine without a
# Downloads folder, silently inventing one puts the file somewhere the operator
# has no habit of looking, which is the same problem with an extra step. The
# "SEND THIS ONE FILE" line prints the real path either way, so the fallback is
# visible rather than assumed.
OUT="${HOME}/platterpusmorning${STAMP}"
if [ -d "${HOME}/Downloads" ]; then
  ARCHIVE="${HOME}/Downloads/platterpusmorning${STAMP}.tar.gz"
else
  ARCHIVE="${OUT}.tar.gz"
fi

# The eight suffixes the app's own bundler admits, plus .png for screenshots.
# Copied from `evidence_bundle.ALLOWED_SUFFIXES` so the two cannot disagree
# about what counts as text.
TEXT_SUFFIXES=(txt cue md5 json toml md log sha256)
AUDIO_SUFFIXES=(flac wav mp3 m4a aac ogg opus wv ape aiff aif dsf dff wma alac)

PROBLEMS=0
say()  { printf '\n== %s\n' "$*"; }
note() { printf '   %s\n' "$*"; }
bad()  { printf '   !! %s\n' "$*"; PROBLEMS=$((PROBLEMS + 1)); }

mkdir -p "$OUT"/{logs,rips,bundles,session,probes} || {
  printf 'fatal: cannot create %s\n' "$OUT" >&2
  exit 1
}

printf '=============================================================\n'
printf 'PLATTERPUS MORNING COLLECTION\n'
printf 'staging into: %s\n' "$OUT"
printf '=============================================================\n'

# --- 0. Which binary ---------------------------------------------------------
# Prefer where the app relocates itself when integrated; fall back to a search
# rather than failing, because an operator who never integrated it still has one.
say "0  locating the AppImage"
APP="${HOME}/Applications/platterpus-x86_64.AppImage"
if [ ! -x "$APP" ]; then
  note "not at $APP — searching"
  # `|| true`: find exits non-zero when it cannot read a directory, and `head`
  # closing the pipe early makes that routine. An empty result is handled below.
  APP="$(timeout -k 10 60 find "$HOME" -maxdepth 4 -name 'platterpus*.AppImage' \
         -type f -perm -u+x 2>/dev/null | head -1 || true)"
fi
if [ -n "${APP:-}" ] && [ -x "$APP" ]; then
  note "using $APP"
else
  bad "no Platterpus AppImage found — version probes and --rig-session skipped"
  APP=""
fi

# --- 1. Versions, first, so every artifact below is attributable -------------
# A result that looks wrong must be attributable rather than guessed at, and the
# two version strings are the only things that say WHICH pair produced the night.
say "1  version probes"

# WHY THIS IS A FUNCTION AND NOT TWO INLINE `timeout` CALLS. The 2026-08-27
# collection killed `cyanrip --version` at 60s having ALREADY captured its
# banner, and recorded that as `(probe failed: exit 124)`. Three things were
# wrong, and the third is the one that matters:
#
#   1. THE BOUND DID NOT MATCH THE APP'S. `cyanrip_backend._INFO_TIMEOUT_S` is
#      120.0 — the number measured against a cold Distrobox container. This
#      script used 60, so the app's own `--doctor` printed `[✓] cyanrip
#      reachable` in the same collection where this probe reported a failure.
#      Two surfaces answering one question with different bounds; the bound is
#      now taken from the app's, cited, so they cannot drift apart silently.
#   2. NO STDIN REDIRECT. The adapter passes `stdin_devnull=True` deliberately:
#      a ripper that reaches for a terminal it should not have blocks forever
#      when one is attached, and the morning collection runs on a real tty.
#   3. A KILL AFTER THE OUTPUT ARRIVED WAS REPORTED IDENTICALLY TO SILENCE.
#      "exit 124" covered both, and they are opposite diagnoses — one says the
#      binary works and did not exit, the other says nothing came back at all.
#      An absence in a capture is a fact about the capture first, so the probe
#      now states which of the two it saw, and keeps whatever did arrive.
PROBE_TIMEOUT_S=120        # = cyanrip_backend._INFO_TIMEOUT_S
probe() {
  # $1 = label for the transcript, rest = argv. Never aborts the script: a
  # failed probe is DATA and the next section still has work to do.
  local label="$1"; shift
  local scratch rc
  scratch="$(mktemp)"
  printf '$ %s\n' "$label"
  rc=0
  timeout -k 10 "$PROBE_TIMEOUT_S" "$@" </dev/null >"$scratch" 2>&1 || rc=$?
  cat "$scratch"
  if [ "$rc" -eq 0 ]; then
    :
  elif [ "$rc" -ge 124 ] && [ -s "$scratch" ]; then
    printf '(probe TIMED OUT after %ss — but output above WAS captured, so the\n' \
           "$PROBE_TIMEOUT_S"
    printf ' binary ran and did not exit; this is not a silent hang)\n'
  elif [ "$rc" -ge 124 ]; then
    printf '(probe TIMED OUT after %ss with NO output at all)\n' "$PROBE_TIMEOUT_S"
  else
    printf '(probe exited %s — output above is everything it printed)\n' "$rc"
  fi
  rm -f "$scratch"
  return 0
}

{
  printf '# collected %s\n\n' "$STAMP"
  if [ -n "$APP" ]; then
    probe 'platterpus --version' "$APP" --version
  else
    printf '(no AppImage located)\n'
  fi
  printf '\n'
  probe 'cyanrip --version' "$HOME/.local/bin/cyanrip" --version
} >"$OUT/probes/versions.txt" 2>&1
sed 's/^/   /' "$OUT/probes/versions.txt"
# An EMPTY transcript is the one outcome the sections below cannot work around:
# every artifact they collect is attributable only via these two strings.
[ -s "$OUT/probes/versions.txt" ] || bad "version probes produced an EMPTY transcript"

# --- 2. --doctor: the environment as it stood in the morning -----------------
say "2  --doctor (no disc needed)"
if [ -n "$APP" ]; then
  if timeout -k 30 300 "$APP" --doctor >"$OUT/probes/doctor.txt" 2>&1; then
    note "doctor: clean"
  else
    # A non-zero doctor is DATA, not a failure of this script — it is exactly the
    # thing worth capturing. Only an absent report is a problem.
    note "doctor: reported issues (exit $?) — captured, read the file"
  fi
  [ -s "$OUT/probes/doctor.txt" ] || bad "doctor produced an EMPTY report"
else
  note "skipped: no AppImage"
fi

# --- 3. THE RIPS — all of them. This is the part nothing else does -----------
# Where rips land: read the operator's own config rather than assuming, then fall
# back. Assuming ~/Music/rips when the config says otherwise would collect an
# empty tree and report success, which is the failure this whole script exists
# to prevent.
say "3  every rip folder's TEXT artifacts (never audio)"
CONF="${HOME}/.config/platterpus/config.toml"
OUTPUT_DIR=""
if [ -f "$CONF" ]; then
  # `|| true`: grep exits 1 when the key is absent, which is not an error — the
  # fallback below covers it.
  OUTPUT_DIR="$(grep -E '^[[:space:]]*output_dir[[:space:]]*=' "$CONF" 2>/dev/null \
                | head -1 | sed -E 's/.*=[[:space:]]*"([^"]*)".*/\1/' || true)"
  OUTPUT_DIR="${OUTPUT_DIR/#\~/$HOME}"
fi
CANDIDATES=()
if [ -n "$OUTPUT_DIR" ] && [ -d "$OUTPUT_DIR" ]; then CANDIDATES+=("$OUTPUT_DIR"); fi
if [ -d "$HOME/Music" ]; then CANDIDATES+=("$HOME/Music"); fi

# DROP ANY ROOT NESTED INSIDE ANOTHER, and this is a real defect the first live
# run caught rather than a tidiness pass. The config's `output_dir` is normally
# `~/Music/rips`, which is INSIDE the `~/Music` fallback — so `find` walked every
# file twice and the count read 48 for 24 artifacts.
#
# A doubled count is worse than a wrong path, because it inflates: the "did we
# get enough?" floor below would pass on half the evidence. The tree itself was
# correct (the second copy overwrote the first at the same destination), so
# nothing was lost — only the number that the operator is asked to sanity-check
# was silently twice the truth, which is the one number in this script whose
# whole job is to be checkable.
SEARCH=()
for c in ${CANDIDATES+"${CANDIDATES[@]}"}; do
  nested=0
  for other in ${CANDIDATES+"${CANDIDATES[@]}"}; do
    if [ "$c" = "$other" ]; then continue; fi
    case "$c" in "$other"/*) nested=1 ;; esac
  done
  if [ "$nested" -eq 0 ]; then SEARCH+=("$c"); fi
done
# Belt: if two roots are literally equal, `case` above cannot tell them apart.
if [ "${#SEARCH[@]}" -gt 1 ]; then
  mapfile -t SEARCH < <(printf '%s\n' "${SEARCH[@]}" | sort -u)
fi

if [ "${#SEARCH[@]}" -eq 0 ]; then
  bad "no rip directory found (config said '${OUTPUT_DIR:-nothing}', ~/Music absent)"
else
  note "searching: ${SEARCH[*]}"
  # Build the -name predicate from TEXT_SUFFIXES so the list has one home.
  FIND_ARGS=()
  for s in "${TEXT_SUFFIXES[@]}"; do
    if [ "${#FIND_ARGS[@]}" -gt 0 ]; then FIND_ARGS+=(-o); fi
    FIND_ARGS+=(-name "*.${s}")
  done
  COPIED=0
  FAILED=0
  # -print0 / read -d '' throughout: album titles are user data and this run
  # deliberately uses one containing a space, a colon and an angle bracket.
  while IFS= read -r -d '' f; do
    rel="${f#"${HOME}/"}"
    dest="$OUT/rips/$rel"
    if mkdir -p "$(dirname "$dest")" 2>/dev/null && cp -p "$f" "$dest" 2>/dev/null; then
      COPIED=$((COPIED + 1))
    else
      FAILED=$((FAILED + 1))
      printf '%s\n' "$f" >>"$OUT/rips/COPY-FAILURES.txt"
    fi
  done < <(timeout -k 30 600 find "${SEARCH[@]}" -type f \( "${FIND_ARGS[@]}" \) -print0 2>/dev/null)

  note "copied $COPIED text artifact(s) from the rip tree"
  if [ "$FAILED" -gt 0 ]; then
    bad "$FAILED file(s) FAILED to copy — see rips/COPY-FAILURES.txt"
  fi

  # THE FLOOR. An overnight run performs seven rips, each writing at least a log
  # and a report, so a single-digit count means something went wrong — either the
  # night failed early or this search looked in the wrong place. Reported rather
  # than assumed, because "copied 0" and "copied 40" print the same shade of
  # green without it.
  if [ "$COPIED" -eq 0 ]; then
    bad "ZERO rip artifacts found. Either no rip completed, or rips do not live"
    bad "under ${SEARCH[*]}. Do NOT upload this bundle as if it were complete."
  elif [ "$COPIED" -lt 14 ]; then
    bad "only $COPIED artifact(s) — an overnight run makes seven rips and should"
    bad "produce far more. Check the transcript before treating this as a pass."
  fi

  # How many distinct album folders were reached, which is the number that maps
  # onto "seven rips" and is the one worth eyeballing.
  # `|| echo 0`: a staging tree with no logs is a real state, reported by the
  # floors above rather than by aborting here.
  ALBUMS="$(timeout -k 10 60 find "$OUT/rips" -name '*.log' -printf '%h\n' 2>/dev/null \
            | sort -u | wc -l || echo 0)"
  note "spanning $ALBUMS album folder(s) — the overnight script makes 7 or 8"
fi

# --- 4. The app's own auto-bundles ------------------------------------------
# Folded in rather than reimplemented: they carry the script transcript, the
# report JSON and every screenshot, which is exactly the half this script does
# not gather itself. Taking the newest THREE, not one — the run may have
# produced more than one and the newest is not reliably the acceptance run's.
say "4  the app's own evidence bundles"
BUNDLE_DIR="${HOME}/.local/share/platterpus/bundles"
if [ -d "$BUNDLE_DIR" ]; then
  N=0
  while IFS= read -r -d '' b; do
    cp -p "$b" "$OUT/bundles/" 2>/dev/null && N=$((N + 1)) \
      || bad "could not copy bundle $b"
  done < <(timeout -k 10 120 find "$BUNDLE_DIR" -name '*.tar.gz' -type f \
           -printf '%T@\t%p\0' 2>/dev/null | sort -zrn | head -z -n 3 | cut -zf2-)
  note "copied $N bundle(s) from $BUNDLE_DIR"
  if [ "$N" -eq 0 ]; then bad "NO auto-bundle found — the script run may not have finished"; fi
else
  bad "no bundle directory at $BUNDLE_DIR"
fi

# --- 5. App logs, including rotations ---------------------------------------
say "5  app log and its rotations"
LOGN=0
for l in "$HOME/.local/share/platterpus/log.txt"*; do
  [ -f "$l" ] || continue
  cp -p "$l" "$OUT/logs/" 2>/dev/null && LOGN=$((LOGN + 1)) || bad "could not copy $l"
done
note "copied $LOGN log file(s)"
if [ "$LOGN" -eq 0 ]; then bad "NO app log found — the diagnosis of anything odd lives there"; fi

# --- 6. --rig-session, folded in --------------------------------------------
# Last, because it is the slowest and the most likely to be skipped. It runs the
# probes and audits neither of the sections above cover. Generously bounded: it
# does real work, and a bound inside the healthy range would kill a working step
# and report it as a finding.
say "6  --rig-session (probes and audits; several minutes)"
if [ -n "$APP" ]; then
  if timeout -k 60 1800 "$APP" --rig-session "$OUT/session" \
       >"$OUT/session/rigsession-stdout.txt" 2>&1; then
    note "rig-session: completed"
  else
    rc=$?
    if [ "$rc" -eq 124 ]; then
      bad "rig-session TIMED OUT after 30 min — captured what it wrote"
    elif [ "$rc" -eq 137 ]; then
      bad "rig-session needed SIGKILL — something was wedged, not merely slow"
    else
      note "rig-session exited $rc — that is data; the output is captured"
    fi
  fi
else
  note "skipped: no AppImage"
fi

# --- 7. THE AUDIO SWEEP — prove the rule, do not assert it -------------------
# Critical rule #8. The copy above filtered by suffix, so this should find
# nothing — which is exactly why it prints how many files it EXAMINED. A sweep
# that reports "clean" without a denominator is satisfied by an empty tree.
say "7  audio sweep (Critical rule #8)"
# `|| echo 0`: an unreadable staging dir must reach the zero-check below, which
# says the sweep proved nothing, rather than aborting before it runs.
EXAMINED="$(timeout -k 10 120 find "$OUT" -type f 2>/dev/null | wc -l || echo 0)"
AUDIO_FOUND=0
for s in "${AUDIO_SUFFIXES[@]}"; do
  while IFS= read -r -d '' a; do
    AUDIO_FOUND=$((AUDIO_FOUND + 1))
    bad "AUDIO IN THE BUNDLE: $a"
    rm -f -- "$a" 2>/dev/null && note "   removed it"
  done < <(timeout -k 10 60 find "$OUT" -type f -iname "*.${s}" -print0 2>/dev/null)
done
note "examined $EXAMINED staged file(s); audio found: $AUDIO_FOUND"
if [ "$EXAMINED" -eq 0 ]; then
  bad "the sweep examined ZERO files — it proved nothing, and neither did this run"
fi

# --- 8. Manifest, then one archive ------------------------------------------
say "8  manifest and archive"
{
  printf 'PLATTERPUS MORNING COLLECTION\n'
  printf 'collected:       %s\n' "$STAMP"
  printf 'host:            %s\n' "$(uname -a 2>/dev/null || echo unknown)"
  printf 'appimage:        %s\n' "${APP:-(none found)}"
  printf 'rip search:      %s\n' "${SEARCH[*]:-(none)}"
  printf 'rip artifacts:   %s\n' "${COPIED:-0}"
  printf 'album folders:   %s\n' "${ALBUMS:-0}"
  printf 'app bundles:     %s\n' "${N:-0}"
  printf 'app logs:        %s\n' "${LOGN:-0}"
  printf 'files staged:    %s\n' "$EXAMINED"
  printf 'audio found:     %s  (must be 0)\n' "$AUDIO_FOUND"
  printf 'problems:        %s\n' "$PROBLEMS"
  printf '\nNO AUDIO IS PRESENT. Only these suffixes were copied: %s\n' "${TEXT_SUFFIXES[*]}"
  printf '\n--- full file list ---\n'
  timeout -k 10 120 find "$OUT" -type f -printf '%10s  %P\n' 2>/dev/null | sort -k2
} >"$OUT/MANIFEST.txt" 2>&1

# `-C "$(dirname)"` so the archive holds one top-level directory rather than an
# absolute path, and so tar is never asked to read the directory it writes into.
if timeout -k 30 900 tar -czf "$ARCHIVE" -C "$(dirname "$OUT")" "$(basename "$OUT")" 2>/dev/null; then
  SIZE="$(wc -c <"$ARCHIVE" 2>/dev/null || echo 0)"
  note "archive written ($SIZE bytes)"
else
  bad "tar FAILED — the staged directory is still complete at $OUT"
  ARCHIVE=""
fi

printf '\n=============================================================\n'
if [ "$PROBLEMS" -gt 0 ]; then
  printf 'FINISHED WITH %d PROBLEM(S) — read the !! lines above.\n' "$PROBLEMS"
  printf 'The bundle is still worth sending; it is just not complete.\n'
else
  printf 'FINISHED CLEAN.\n'
fi
printf '=============================================================\n'
if [ -n "$ARCHIVE" ]; then
  printf '\nSEND THIS ONE FILE:\n\n    %s\n\n' "$ARCHIVE"
else
  printf '\nSEND THIS ONE DIRECTORY (tar failed):\n\n    %s\n\n' "$OUT"
fi
exit 0
