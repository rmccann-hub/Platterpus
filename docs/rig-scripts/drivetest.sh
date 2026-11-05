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
# IT RESUMES. Each finished step leaves a marker in ~/drivemode/state/, so
# running the same command again after a stop carries on from where it stopped
# instead of starting over. Delete a marker to redo that step.
#
# `set -euo pipefail` is the repo's shell rule: an unexpected failure stops the
# script rather than producing an upload that looks complete, including a failure
# in the middle of a pipeline. Commands that may legitimately fail or find nothing
# are written with `|| ...` beside them, saying what then.
set -euo pipefail

# --- where things are ---------------------------------------------------------

DM="$HOME/drivemode"                 # everything this test writes lives here
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
stop() { say "STOPPED: $*"; exit 1; }

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

# Fetch the two rip scripts into ~/drivemode/scripts. A short or empty file is a
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
      say "$label ENDED WITH A FAILED STEP after its rips began. Kept and packed; its report is in the upload."
      done_mark "$label"
      return 0
    fi
    say "$label stopped before its first rip. Retrying (that loses nothing)."
    wait_disc
  done
  stop "$label stopped before its first rip three times. Upload $DM/drivetest.log and the newest bundle in $BUNDLES."
}

# Move a run's folders out of the rips folder (so the next run cannot overwrite
# them) and pack their logs, never their audio.
pack() {
  local prefix="$1" label="$2"
  mkdir -p "$DM/$label"
  find "$RIPS" -mindepth 1 -maxdepth 1 -type d -name "$prefix*" -exec mv -t "$DM/$label/" {} +
  pack_logs "$label" "$label-logs.tar.gz"
}

# Pack a folder under ~/drivemode into a .tar.gz of its logs, leaving out every
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
    inbox cdrdao read-toc --device "$DEVICE" "$DM/track9/cdrdao.toc" > cdrdao-output.txt 2>&1 \
      || echo "(cdrdao exited non-zero; its output is saved)"
  )
  tar czf "$DM/track9.tar.gz" -C "$DM" track9
  done_mark track9
}

# One upload: the named pieces, the log, and every bundle made since the test began.
make_upload() {
  local name="$1" since="$2"; shift 2
  local stage="$DM/upload-$name"
  rm -rf "$stage"   # our own staging folder, rebuilt each time
  mkdir -p "$stage/bundles"
  local piece
  for piece in "$@"; do
    [ -e "$DM/$piece" ] && cp -r "$DM/$piece" "$stage/"
  done
  cp "$LOG" "$stage/"
  find "$DM" -maxdepth 1 -name 'leftover-*.tar.gz' -exec cp -t "$stage/" {} +
  [ -f "$DM/notes.txt" ] && cp "$DM/notes.txt" "$stage/"
  find "$BUNDLES" -maxdepth 1 -name '*.tar.gz' -newer "$since" -exec cp -t "$stage/bundles/" {} + 2>/dev/null || true
  local out="$DM/upload-$name.tar.gz"
  tar czf "$out" -C "$DM" "upload-$name"
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
  say "DONE. Upload this ONE file to both sessions: $out ($(du -h "$out" | cut -f1))"
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

# --- the three entry points ---------------------------------------------------

phase12() {
  say "Round 38 drive test, phases 1 and 2. Rips go to $RIPS"
  local since
  since="$(start_marker)"
  check_versions
  fetch_scripts
  install_tools
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
  make_upload phase12 "$since" dumps runA-logs.tar.gz runB-logs.tar.gz runC-logs.tar.gz track9.tar.gz
  echo
  echo "Next: phase 3 in Windows (the sheet's step 3.1). Then come back and run:"
  echo "  bash $0 perfect"
}

phase3() {
  is_done track9 || stop "phases 1 and 2 are not finished. Run: bash $0"
  say "Phase 3: PureRead should now be Perfect. Reading the drive again (read-only)"
  date -u > "$STATE/phase3.started"
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
  make_upload phase3 "$STATE/phase3.started" dumps runD-logs.tar.gz
  echo
  echo "Next: put PureRead back in Windows (the sheet's step 3.4), then come back and run:"
  echo "  bash $0 restored"
  echo "Upload your Windows screenshots with that file."
}

restored() {
  say "Checking PureRead went back (read-only)"
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

case "${1:-}" in
  "")       phase12 ;;
  perfect)  phase3 ;;
  restored) restored ;;
  status)   status ;;
  *) echo "usage: bash $0 [perfect|restored|status]"; exit 2 ;;
esac
