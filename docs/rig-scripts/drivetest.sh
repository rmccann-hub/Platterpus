#!/usr/bin/env bash
# drivetest.sh -- round 38's drive test, every terminal step, in one command.
#
# WHY THIS EXISTS. The drive test in docs/rig-session.md used to be fifteen
# pastes. Every paste is a step the software was supposed to do (CLAUDE.md,
# "never hand back an instruction file"), and the first real attempt lost a run
# to exactly that shape: a stop the operator could not tell from a finish. This
# does every terminal step itself, records its own times in UTC, retries a run
# that stopped before its first rip, and ends by naming ONE file to upload.
#
# WHAT IT NEVER DOES. It never writes to the drive (every SCSI command here is a
# READ: READ BUFFER 3Ch, READ CD BEh, INQUIRY, GET CONFIGURATION, MODE SENSE),
# never changes firmware, never burns, never runs Overread, and never packs
# audio: the upload holds text and logs only, and it is checked before it is
# named.
#
# HOW TO RUN IT (bash, on the Bazzite host, not inside the container):
#
#   bash drivetest.sh            phases 1 and 2. Stops ONCE, to have you wipe
#                                the disc; everything else is unattended.
#   bash drivetest.sh perfect    phase 3, after Windows has set PureRead to
#                                Perfect: reads the drive again, then Run D.
#   bash drivetest.sh restored   after Windows has put PureRead back: reads the
#                                drive once more and says whether it matches.
#   bash drivetest.sh status     what is done and what is next.
#
# WHEN SOMETHING FAILS, IT DECIDES WHETHER GOING ON STILL MEANS SOMETHING:
#   * nothing can run (no AppImage, the wrong cyanrip build, no disc, no disk
#     space, a run that cannot even start three times): it STOPS;
#   * a reading or a run fails after it produced something (a drive query, a run
#     whose rips began, the track 9 reads, cdrdao): it KEEPS what it made, writes
#     the full error to ~/platterpus-rig/drivetest38/errors.txt, and GOES ON, because every later
#     step is still a separate answer.
# Either way it builds the upload, so nothing that was measured is lost, and the
# full error (the failing step's whole text, the command, its exit code and its
# output) is in errors.txt inside it and printed on the screen.
#
# IT RESUMES. Each finished step leaves a marker in ~/platterpus-rig/drivetest38/state/, so
# running the same command again after a stop carries on from where it stopped
# instead of starting over. Delete a marker to redo that step.
#
# `set -euo pipefail` is the repo's shell rule: an unexpected failure stops the
# script rather than producing an upload that looks complete, including a failure
# in the middle of a pipeline. Commands that may legitimately fail or find nothing
# are written with `|| ...` beside them, saying what then.
set -euo pipefail

# --- where things are ---------------------------------------------------------

# EVERYTHING THIS TEST WRITES LIVES IN ONE FOLDER, under the one folder the app
# keeps all rig evidence in (`~/platterpus-rig`, test_session.RIG_PARENT_NAME,
# named to mirror the fork's `~/cyanrip-rig`; the owner's "stop polluting my home
# directory", 2026-09-11). One folder per round's drive test, so a later round's
# test cannot mix with this one. Deleting the folder removes all of it.
ROUND="${DRIVETEST_ROUND:-38}"
DM="$HOME/platterpus-rig/drivetest$ROUND"
STATE="$DM/state"
LOG="$DM/drivetest.log"
DEVICE="${DRIVETEST_DEVICE:-/dev/sr0}"
# The build under test. Overridable so a later round can reuse the script.
EXPECT_BUILD="${DRIVETEST_EXPECT_BUILD:-platterpus.30}"
# Where the rip scripts are fetched from. This script runs the CURRENT
# drivemode.txt and drivespeed.txt from the repository, not the copies packaged
# in the installed release, so a fix to a rip script (the release it picks, on
# 2026-11-05) reaches a test without waiting for a release.
REF="${DRIVETEST_REF:-main}"
RAW="https://raw.githubusercontent.com/rmccann-hub/Platterpus/$REF/src/platterpus/rig_scripts"
BUNDLES="$HOME/.local/share/platterpus/bundles"
UISCRIPT="$HOME/.local/share/platterpus/uiscript"
# The same audio list as platterpuscollect.sh and .githooks/audio-extensions.txt:
# nothing with one of these endings may enter an upload.
AUDIO_EXTS="flac wav pcm raw mp3 m4a aac ogg oga opus wv ape wma aiff aif alac dsf dff"

mkdir -p "$STATE" "$DM/dumps"

# Keep the machine awake for the whole test. A run is two hours; a suspended
# laptop in the middle of Run B is a lost run. Re-runs this script under
# systemd-inhibit once; the variable stops it doing so twice.
if [ -z "${DRIVETEST_AWAKE:-}" ] && command -v systemd-inhibit >/dev/null 2>&1; then
  export DRIVETEST_AWAKE=1
  exec systemd-inhibit --what=sleep:idle --who="Platterpus drive test" \
    --why="a rip run is in progress" bash "$0" "$@"
fi

# Everything printed also goes to the log, which is part of the upload: it is
# the log sheet, with times nobody had to write down.
exec > >(tee -a "$LOG") 2>&1

say()  { printf '\n[%s UTC] %s\n' "$(date -u '+%Y-%m-%d %H:%M:%S')" "$*"; }
done_mark() { date -u > "$STATE/$1.done"; }
is_done()   { [ -f "$STATE/$1.done" ]; }
# Set by each entry point: what to upload if the script has to stop early.
UPLOAD_NAME=""
UPLOAD_SINCE=""
UPLOAD_PIECES=()
IN_UPLOAD=""

# Write a full error into errors.txt (part of the upload) and on the screen.
# $1 a one-line title; the rest of the text comes on stdin.
note_error() {
  {
    printf '\n===== %s UTC: %s =====\n' "$(date -u '+%Y-%m-%d %H:%M:%S')" "$1"
    cat
  } | tee -a "$DM/errors.txt"
}

# Stop, but first build the upload of everything measured so far, so a stop never
# loses a reading. (Not from inside make_upload: its own failure must not loop.)
stop() {
  say "STOPPED: $*"
  echo "$*" | note_error "stopped"
  if [ -n "$UPLOAD_NAME" ] && [ -z "$IN_UPLOAD" ]; then
    make_upload "${UPLOAD_NAME}stopped" "$UPLOAD_SINCE" "${UPLOAD_PIECES[@]}" || true
  fi
  exit 1
}

# Every step of a ui-script run that did not pass, with its whole text: what the
# script asked, and what the app said. Read from the run's own report.json.
report_failures() {
  python3 -I - "$1" <<'PY' || echo "(could not read $1 as JSON; it is in the upload)"
import json, sys
report = json.load(open(sys.argv[1], encoding="utf-8"))
print("report:", sys.argv[1])
print("ok:", report.get("ok"), "| ended:", report.get("ended_reason") or "normally")
bad = [s for s in report.get("steps", []) if s.get("outcome") in ("fail", "error", "blocked")]
print(f"{len(bad)} step(s) did not pass")
for step in bad:
    print(f"--- line {step.get('line_no')} [{step.get('outcome')}]: {step.get('source')}")
    print(step.get("detail") or "(no detail recorded)")
PY
}

# A command inside the ripping container, the same route cyanrip takes.
inbox() { distrobox enter ripping -- "$@"; }

# Save one read-only query's answer, stamped with the drive's clock-free UTC time.
dump() { inbox sh -c "date -u; $2" > "$DM/dumps/$1.txt" 2>&1; }

# The 256 bytes of a saved READ BUFFER answer, as one hex string (the 16 hex
# columns of each sg_raw row; the ASCII column after them is ignored).
f4_bytes() {
  awk '/^ *[0-9a-f]+  +[0-9a-f][0-9a-f] /{for(i=2;i<=17;i++) printf "%s", $i}' "$1"
}

# --- the app, the ripper, the rips folder -------------------------------------

find_app() {
  for p in "$HOME/Applications/platterpus-x86_64.AppImage" \
           "$HOME/Downloads/platterpus-x86_64.AppImage"; do
    [ -x "$p" ] && { echo "$p"; return 0; }
  done
  return 1
}
APP="$(find_app)" || stop "no Platterpus AppImage in ~/Applications or ~/Downloads"

# Where the app puts rips: its own setting, else its default.
RIPS="$(grep -E '^output_dir' "$HOME/.config/platterpus/config.toml" 2>/dev/null \
        | sed -E 's/.*= *"(.*)"/\1/')" || true
RIPS="${RIPS:-$HOME/Music/rips}"

check_versions() {
  say "Checking versions"
  "$APP" --version || stop "the AppImage did not start"
  local banner
  banner="$("$HOME/.local/bin/cyanrip" --version 2>&1 | head -3)" || true
  echo "$banner"
  case "$banner" in
    *"$EXPECT_BUILD"*) echo "cyanrip is the build under test ($EXPECT_BUILD)." ;;
    *) stop "cyanrip is not $EXPECT_BUILD. Open Platterpus, Tools > Setup & Updates > Choose a build..., pick it, close Platterpus, and run this again." ;;
  esac
}

# Fetch the two rip scripts into the test folder's scripts/. A short or empty file is a
# failed download, not a script, and the run would fail in a less obvious way.
fetch_scripts() {
  local name
  mkdir -p "$DM/scripts"
  for name in drivemode drivespeed; do
    curl -fsSL -o "$DM/scripts/$name.txt" "$RAW/$name.txt" \
      || stop "could not download $name.txt from $RAW. Check the internet connection and run this again."
    [ "$(wc -c < "$DM/scripts/$name.txt")" -gt 1000 ] \
      || stop "$name.txt downloaded empty or short. Run this again."
  done
  echo "Rip scripts fetched from $REF: $(wc -c < "$DM/scripts/drivemode.txt") and $(wc -c < "$DM/scripts/drivespeed.txt") bytes."
}

install_tools() {
  if inbox sh -c 'command -v sg_raw && command -v sg_turs && command -v cdrdao' >/dev/null 2>&1; then
    echo "sg3_utils and cdrdao are already in the container."
    return 0
  fi
  say "Installing the read-only tools in the container (it may ask for your password)"
  inbox sudo dnf install -y sg3_utils cdrdao
}

# Wait until no cyanrip is running and the drive says the disc is ready (TEST
# UNIT READY). A cyanrip left running by an earlier, stopped run still holds the
# drive (2026-11-05: two survived the app closing), and a run started beside it
# reads the disc twice at once. Waiting is safe; killing it is the app's job.
wait_disc() {
  local i
  for i in $(seq 1 60); do
    pgrep -x cyanrip >/dev/null 2>&1 || break
    [ "$i" = 1 ] && echo "A cyanrip from an earlier run is still running; waiting for it to finish (up to 10 minutes)..."
    [ "$i" = 60 ] && stop "a cyanrip from an earlier run is still running after 10 minutes. Eject the disc, put it back, and run this again."
    sleep 10
  done
  for i in $(seq 1 24); do
    if inbox sg_turs "$DEVICE" >/dev/null 2>&1; then
      echo "Disc ready."
      sleep 10   # the sheet's settle time after inserting
      return 0
    fi
    [ "$i" = 1 ] && echo "Waiting for the disc to be ready..."
    sleep 5
  done
  stop "the drive did not report a disc ready within 2 minutes. Check the disc is in and the tray closed, then run this again."
}

# --- a run, with the retry the first attempt needed ---------------------------

# The newest ui-script run folder's report says how the run ended.
last_report() {
  # No report (no folder yet, or none newer) is an answer, not a failure: the
  # caller says so. `|| true` also covers sort's SIGPIPE when head stops early.
  find "$UISCRIPT" -mindepth 2 -maxdepth 2 -name report.json -newer "$1" \
    -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2- || true
}

# How many folders with this prefix the rips folder holds (0 if it does not exist).
count_rips() {
  local n
  n="$(find "$RIPS" -mindepth 1 -maxdepth 1 -type d -name "$1*" 2>/dev/null | wc -l)" || n=0
  echo "$n"
}

# run_script NAME PREFIX LABEL
#   NAME   the packaged script (drivemode or drivespeed)
#   PREFIX the folder prefix its rips use (dm or ds)
#   LABEL  runA, runB, runC or runD
#
# RETRIES ONLY A RUN THAT STOPPED BEFORE ITS FIRST RIP. 0.7.121 can stop in its
# first minutes when two disc reads overlap at start-up (found 2026-11-05, the
# first attempt at Run A); nothing has been read from the disc for the test at
# that point, so a retry loses nothing. A run that stopped after rips began is
# NOT retried: what it made is evidence, and a second run would be a different
# session. It is packed and the script stops so you can tell us.
run_script() {
  local name="$1" prefix="$2" label="$3" attempt marker report rips
  if is_done "$label"; then echo "$label already done."; return 0; fi
  for attempt in 1 2 3; do
    marker="$STATE/$label.attempt$attempt.started"
    date -u > "$marker"
    say "$label, attempt $attempt: running the $name script (no input needed)"
    "$APP" --run-script "$DM/scripts/$name.txt" || echo "(the app exited non-zero; reading its report)"
    report="$(last_report "$marker")"
    if [ -n "$report" ]; then
      echo "Report: $report"
      grep -E '"ok"|"ended_reason"' "$report" | head -2 || true
    else
      echo "No report was written for this attempt."
    fi
    rips="$(count_rips "$prefix")"
    if [ "$rips" -gt 0 ]; then
      echo "$label made $rips rip folder(s)."
      pack "$prefix" "$label"
      if [ -n "$report" ] && grep -q '"ok": true' "$report"; then
        done_mark "$label"
        return 0
      fi
      # Ended with something not ok after rips began. Keep it, mark it, and
      # carry on: every step after it is still worth having, and the report
      # inside the upload says what went wrong.
      say "$label ENDED WITH A FAILED STEP after its rips began. Kept and packed; going on, because every later run is a separate answer."
      if [ -n "$report" ]; then report_failures "$report"; else echo "no report was written"; fi \
        | note_error "$label ended with a failed step after its rips began (kept)"
      done_mark "$label"
      return 0
    fi
    say "$label stopped before its first rip. Retrying (that loses nothing)."
    { if [ -n "$report" ]; then report_failures "$report"; else echo "no report was written"; fi
      echo "--- cyanrip processes running now:"; pgrep -a cyanrip || echo "none"
    } | note_error "$label attempt $attempt stopped before its first rip"
    wait_disc
  done
  stop "$label stopped before its first rip three times; every attempt's full error is in errors.txt."
}

# Move a run's folders out of the rips folder (so the next run cannot overwrite
# them) and pack their logs, never their audio.
pack() {
  local prefix="$1" label="$2"
  mkdir -p "$DM/$label"
  find "$RIPS" -mindepth 1 -maxdepth 1 -type d -name "$prefix*" -exec mv -t "$DM/$label/" {} +
  pack_logs "$label" "$label-logs.tar.gz"
}

# Pack a folder under the test folder into a .tar.gz of its logs, leaving out every
# audio ending in both cases.
pack_logs() {
  local folder="$1" out="$2" excludes=() ext
  for ext in $AUDIO_EXTS; do
    excludes+=("--exclude=*.$ext" "--exclude=*.$(echo "$ext" | tr '[:lower:]' '[:upper:]')")
  done
  tar czf "$DM/$out" "${excludes[@]}" -C "$DM" "$folder"
  echo "Packed $DM/$out"
}

# Folders left in the rips folder by a run started by hand would be overwritten
# or mistaken for this run's. Offer them as the run they are, or move them aside.
adopt_or_move_aside() {
  local prefix="$1" label="$2" n answer
  is_done "$label" && return 0
  n="$(count_rips "$prefix")"
  [ "$n" -eq 0 ] && return 0
  echo "Found $n '$prefix' folder(s) in $RIPS from a run started by hand."
  echo "If that run FINISHED, answer y. If it was stopped early, answer n: they are kept aside, uploaded, and $label runs again."
  read -r -p "Use them as $label? [y/N] " answer || answer=n
  case "$answer" in
    y|Y|yes|YES)
      pack "$prefix" "$label"
      done_mark "$label"
      echo "$label taken from the run you started by hand." ;;
    *)
      local aside
      aside="$DM/leftover-$(date -u +%Y%m%dT%H%M%S)"
      mkdir -p "$aside"
      find "$RIPS" -mindepth 1 -maxdepth 1 -type d -name "$prefix*" -exec mv -t "$aside/" {} +
      pack_logs "$(basename "$aside")" "$(basename "$aside").tar.gz"
      echo "Moved aside to $aside (kept; its logs are in the upload)." ;;
  esac
}

# --- the steps ----------------------------------------------------------------

drive_readings() {
  if is_done readings || [ -s "$DM/dumps/cyanrip-vendor.json" ]; then
    echo "The drive readings are already saved."
    done_mark readings
    return 0
  fi
  say "Reading the drive's own settings (read-only)"
  dump pioneer-f4 "sg_raw -R -r 256 $DEVICE 3c 02 f4 00 00 00 00 01 00 00"
  if grep -qi 'illegal request' "$DM/dumps/pioneer-f4.txt"; then
    dump pioneer-f4-alt "sg_raw -R -r 256 $DEVICE 3c 01 f4 00 00 00 00 01 00 00"
  fi
  dump before "sg_inq $DEVICE; sg_get_config -q $DEVICE; sg_get_config -q -H $DEVICE; for c in 0 1 2 3; do echo \"=== page control \$c ===\"; sg_modes -a -c \$c $DEVICE; done"
  "$HOME/.local/bin/cyanrip" -d "$DEVICE" -I -N -U \
    --diagnostics "$DM/dumps/cyanrip-vendor.json" --read-vendor-settings \
    > "$DM/dumps/cyanrip-vendor.txt" 2>&1 || echo "(cyanrip's vendor read exited non-zero; its output is saved)"
  done_mark readings
}

wipe_pause() {
  is_done wipe && return 0
  say "YOUR TURN (about 2 minutes): the disc comes out now"
  eject "$DEVICE" 2>/dev/null || inbox eject "$DEVICE" 2>/dev/null || echo "Eject it by hand."
  echo "Wipe it gently from the centre outward with a soft, dry, lint-free cloth."
  echo "Put it back in and close the tray."
  local notes=""
  read -r -p "What did you wipe with, and any liquid? Type it, then Enter: " notes || true
  echo "Wipe: ${notes:-(nothing typed)}" | tee -a "$DM/notes.txt"
  wait_disc
  done_mark wipe
}

track9_reads() {
  is_done track9 && return 0
  say "Phase 2: track 9 read two ways, then cdrdao (about 10 minutes)"
  mkdir -p "$DM/track9"
  (
    cd "$DM/track9"
    date -u > times.txt
    # Flush the drive's cache by reading 312 sectors at the start of the disc,
    # so each timed read comes from the disc and not from the cache.
    flush() {
      inbox sh -c "for l in 0 26 52 78 104 130 156 182 208 234 260 286; do sg_raw -R -r 61152 $DEVICE be 00 \$(printf '%02x %02x %02x %02x' 0 0 \$((l>>8)) \$((l&255))) 00 00 1a 10 00 00 >/dev/null 2>&1; done"
    }
    for n in 1 2 3; do
      flush
      { echo "raw$n"; inbox bash -c "time sg_raw -R -o raw$n.bin -r 39168 $DEVICE be 00 00 02 38 98 00 00 10 10 01 00"; } >> times.txt 2>&1
      flush
      { echo "q$n"; inbox bash -c "time sg_raw -R -o q$n.bin -r 37888 $DEVICE be 00 00 02 38 98 00 00 10 10 02 00"; } >> times.txt 2>&1
    done
    ls -l ./*.bin >> times.txt
    local rc=0
    inbox cdrdao read-toc --device "$DEVICE" "$DM/track9/cdrdao.toc" > cdrdao-output.txt 2>&1 || rc=$?
    if [ "$rc" != 0 ]; then
      { echo "command: cdrdao read-toc --device $DEVICE (inside the container)"; echo "exit code: $rc"; cat cdrdao-output.txt; } \
        | note_error "cdrdao read-toc failed (kept; going on)"
    fi
    if grep -q -i -E "error|illegal|denied" times.txt; then
      grep -i -E -B2 -A2 "error|illegal|denied" times.txt | note_error "a track 9 read reported an error (kept; going on)"
    fi
  )
  tar czf "$DM/track9.tar.gz" -C "$DM" track9
  done_mark track9
}

# One upload: the named pieces, the log, and every bundle made since the test began.
make_upload() {
  IN_UPLOAD=1
  local name="$1" since="$2"; shift 2
  # Cross-machine artifact spelling: letters and digits only (CLAUDE.md), since
  # this name is typed into a chat client's upload dialog.
  local base="platterpusdrivetest$ROUND$name"
  local stage="$DM/$base"
  rm -rf "$stage"   # our own staging folder, rebuilt each time
  mkdir -p "$stage/bundles"
  local piece
  for piece in "$@"; do
    [ -e "$DM/$piece" ] && cp -r "$DM/$piece" "$stage/"
  done
  cp "$LOG" "$stage/"
  [ -f "$DM/errors.txt" ] && cp "$DM/errors.txt" "$stage/"
  [ -f "$DM/preflight.txt" ] && cp "$DM/preflight.txt" "$stage/"
  # The app's own log, and every script run's transcript and report since the
  # test began: the full text behind any failure, whether or not a bundle was made.
  mkdir -p "$stage/applog" "$stage/scriptruns"
  find "$HOME/.local/share/platterpus" -maxdepth 1 -name 'log.txt*' -exec cp -t "$stage/applog/" {} + 2>/dev/null || true
  find "$UISCRIPT" -mindepth 1 -maxdepth 1 -type d -newer "$since" -exec cp -r -t "$stage/scriptruns/" {} + 2>/dev/null || true
  find "$DM" -maxdepth 1 -name 'leftover-*.tar.gz' -exec cp -t "$stage/" {} +
  [ -f "$DM/notes.txt" ] && cp "$DM/notes.txt" "$stage/"
  find "$BUNDLES" -maxdepth 1 -name '*.tar.gz' -newer "$since" -exec cp -t "$stage/bundles/" {} + 2>/dev/null || true
  local out="$DM/$base.tar.gz"
  tar czf "$out" -C "$DM" "$base"
  # Prove no audio got in, by listing what is actually in the archive. Listed
  # first, searched second: inside one pipeline a failed listing would read as
  # "no audio found", which is a different fact.
  local pattern listing
  pattern="\\.($(echo "$AUDIO_EXTS" | tr ' ' '|'))\$"
  listing="$(tar tzf "$out")"
  if printf '%s\n' "$listing" | grep -iE "$pattern"; then
    rm -f "$out"
    stop "an audio file got into the upload, so it was deleted. Tell the Platterpus session."
  fi
  IN_UPLOAD=""
  if [ -s "$DM/errors.txt" ]; then
    say "Errors were recorded; the full text is in errors.txt inside the upload, and here:"
    cat "$DM/errors.txt"
  fi
  case "$name" in
    *stopped) say "THE TEST STOPPED. Upload this ONE file to both sessions anyway; it holds everything measured so far and the full error: $out ($(du -h "$out" | cut -f1))" ;;
    *) say "DONE. Upload this ONE file to both sessions: $out ($(du -h "$out" | cut -f1))" ;;
  esac
}

# Checks before anything runs. A missing build, disc space or disc stops it; a
# drive that is not the reference rig's, or an unreachable MusicBrainz, is
# recorded and the test goes on (any drive may run it, TASKS R137).
preflight() {
  say "Preflight"
  {
    echo "app: $("$APP" --version 2>&1 | head -1)"
    echo "cyanrip: $("$HOME/.local/bin/cyanrip" --version 2>&1 | head -1)"
    echo "kernel: $(uname -r)"
    echo "drive: $(inbox sg_inq "$DEVICE" 2>&1 | grep -E 'Vendor|Product|revision' | tr -s ' ' | tr '\n' ' ')"
    echo "rips folder: $RIPS"
    df -h "$HOME" | tail -1
  } > "$DM/preflight.txt" 2>&1 || true
  "$APP" --doctor >> "$DM/preflight.txt" 2>&1 || echo "(--doctor reported a problem; see preflight.txt)" >> "$DM/preflight.txt"
  cat "$DM/preflight.txt"
  local free_kb
  free_kb="$(df -Pk "$HOME" | awk 'NR==2 {print $4}')" || free_kb=0
  [ "${free_kb:-0}" -gt 2000000 ] || stop "less than 2 GB free in your home folder; the runs need room for their FLACs."
  grep -q "BDR-209D" "$DM/preflight.txt" \
    || echo "This is not the reference rig's drive. The test still runs; the readings are this drive's." | note_error "different drive (going on)"
}

# The test began when its first reading was saved. A bundle older than that is
# from another test; one newer is this test's, including any failed attempt's.
start_marker() {
  if [ ! -f "$STATE/test.started" ]; then
    if [ -f "$DM/dumps/pioneer-f4.txt" ]; then
      touch -r "$DM/dumps/pioneer-f4.txt" "$STATE/test.started"
    else
      date -u > "$STATE/test.started"
    fi
  fi
  echo "$STATE/test.started"
}

# THE FIRST VERSION OF THIS TEST LEFT FILES LOOSE IN THE HOME FOLDER: the rig
# sheet's pastes downloaded ~/drivemode.txt and ~/drivespeed.txt (which, being
# found first, also shadow the copies packaged in the app by name) and wrote
# ~/drivemode/. Move them into this test's folder, never delete them: the drive
# readings in ~/drivemode/dumps are this test's own and are reused, not redone.
tidy_old_locations() {
  local moved=0 f
  mkdir -p "$DM/old"
  if [ -d "$HOME/drivemode/dumps" ]; then
    for f in "$HOME"/drivemode/dumps/*; do
      [ -e "$f" ] || continue
      if [ -e "$DM/dumps/$(basename "$f")" ]; then mv "$f" "$DM/old/"; else mv "$f" "$DM/dumps/"; fi
      moved=$((moved + 1))
    done
    rmdir "$HOME/drivemode/dumps" 2>/dev/null || true
  fi
  if [ -d "$HOME/drivemode" ]; then
    find "$HOME/drivemode" -mindepth 1 -maxdepth 1 -exec mv -t "$DM/old/" {} + 2>/dev/null || true
    rmdir "$HOME/drivemode" 2>/dev/null && moved=$((moved + 1))
  fi
  for f in "$HOME/drivemode.txt" "$HOME/drivespeed.txt" "$HOME/drivetest.sh"; do
    [ -f "$f" ] && { mv "$f" "$DM/old/"; moved=$((moved + 1)); }
  done
  rmdir "$DM/old" 2>/dev/null || true
  if [ "$moved" -gt 0 ]; then
    echo "Tidied $moved old item(s) from your home folder into $DM (kept, not deleted)."
  fi
}

# --- the three entry points ---------------------------------------------------

phase12() {
  say "Round 38 drive test, phases 1 and 2. Rips go to $RIPS"
  local since
  since="$(start_marker)"
  UPLOAD_NAME=phase12; UPLOAD_SINCE="$since"
  UPLOAD_PIECES=(dumps runA-logs.tar.gz runB-logs.tar.gz runC-logs.tar.gz track9.tar.gz)
  check_versions
  fetch_scripts
  install_tools
  preflight
  if ! is_done notes; then
    local room=""
    read -r -p "Room: normal, warm or cold? Anything else unusual? (Enter to skip): " room || true
    echo "Room: ${room:-(nothing typed)}" >> "$DM/notes.txt"
    done_mark notes
  fi
  drive_readings
  wait_disc
  adopt_or_move_aside dm runA
  run_script drivemode dm runA
  wipe_pause
  run_script drivemode dm runB
  run_script drivespeed ds runC
  track9_reads
  make_upload phase12 "$since" "${UPLOAD_PIECES[@]}"
  echo
  echo "Next: phase 3 in Windows (the sheet's step 3.1). Then come back and run:"
  echo "  bash $SELF perfect"
}

phase3() {
  is_done track9 || stop "phases 1 and 2 are not finished. Run: bash $SELF"
  say "Phase 3: PureRead should now be Perfect. Reading the drive again (read-only)"
  date -u > "$STATE/phase3.started"
  UPLOAD_NAME=phase3; UPLOAD_SINCE="$STATE/phase3.started"; UPLOAD_PIECES=(dumps runD-logs.tar.gz)
  fetch_scripts
  wait_disc
  if ! is_done perfectreadings; then
    dump pioneer-f4-perfect "sg_raw -R -r 256 $DEVICE 3c 02 f4 00 00 00 00 01 00 00"
    dump after-perfect "sg_inq $DEVICE; sg_get_config -q $DEVICE; sg_get_config -q -H $DEVICE; for c in 0 1 2 3; do echo \"=== page control \$c ===\"; sg_modes -a -c \$c $DEVICE; done"
    done_mark perfectreadings
  fi
  if [ "$(f4_bytes "$DM/dumps/pioneer-f4.txt")" = "$(f4_bytes "$DM/dumps/pioneer-f4-perfect.txt")" ]; then
    say "The drive's settings bytes are THE SAME as before Windows. Running Run D anyway: that is an answer too."
  else
    say "The drive's settings bytes CHANGED since before Windows."
  fi
  run_script drivemode dm runD
  make_upload phase3 "$STATE/phase3.started" "${UPLOAD_PIECES[@]}"
  echo
  echo "Next: put PureRead back in Windows (the sheet's step 3.4), then come back and run:"
  echo "  bash $SELF restored"
  echo "Upload your Windows screenshots with that file."
}

restored() {
  say "Checking PureRead went back (read-only)"
  UPLOAD_NAME=restored; UPLOAD_SINCE="$STATE/test.started"; UPLOAD_PIECES=(dumps)
  wait_disc
  dump pioneer-f4-restored "sg_raw -R -r 256 $DEVICE 3c 02 f4 00 00 00 00 01 00 00"
  if [ "$(f4_bytes "$DM/dumps/pioneer-f4.txt")" = "$(f4_bytes "$DM/dumps/pioneer-f4-restored.txt")" ]; then
    say "BACK TO ORIGINAL: the settings bytes match the first reading."
  else
    say "NOT THE SAME as the first reading. Tell both sessions before the Full run."
  fi
  make_upload restored "$STATE/test.started" dumps
  echo
  echo "Last: the Full run, in the app: Tools > Advanced > Run acceptance test..., Full."
}

status() {
  local s
  for s in readings runA wipe runB runC track9 perfectreadings runD; do
    if is_done "$s"; then echo "done   $s ($(cat "$STATE/$s.done"))"; else echo "to do  $s"; fi
  done
}

# The one place this script lives, so every "run this next" names a path that
# exists, whatever folder it was first run from.
SELF="$HOME/platterpus-rig/drivetest.sh"
if [ "$(readlink -f "$0")" != "$(readlink -f "$SELF" 2>/dev/null || echo none)" ]; then
  cp "$0" "$SELF"
fi
[ "${1:-}" = status ] || tidy_old_locations

case "${1:-}" in
  "")       phase12 ;;
  perfect)  phase3 ;;
  restored) restored ;;
  status)   status ;;
  *) echo "usage: bash $SELF [perfect|restored|status]"; exit 2 ;;
esac
