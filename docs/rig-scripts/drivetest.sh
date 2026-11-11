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
#   bash drivetest.sh quiet      after Windows has put PureRead back and turned
#                                Advanced Quiet Drive OFF: reads the drive, then
#                                the speed test again (Run E).
#   bash drivetest.sh restored   after Windows has put everything back: reads the
#                                drive once more and says whether it matches.
#   bash drivetest.sh probe      round 39's G4, with Platterpus closed: one disc
#                                read timed, two reads 2.4 s apart, and the C2
#                                probe at the five places the wrong samples sit.
#   bash drivetest.sh records    every ripper record (`--diagnostics`, the JSON
#                                cyanrip writes beside each rip, never audio)
#                                in the rips folder since 2026-11-09, in one
#                                upload: the fork's round 39 lap 1 S10.
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
  # The WHOLE output, not its first lines: the first container command after a
  # boot prints distrobox's own "Starting container..." lines before cyanrip
  # speaks, and a check that read three lines missed the banner (2026-11-09).
  banner="$("$HOME/.local/bin/cyanrip" --version 2>&1)" || true
  printf '%s\n' "$banner" | grep -i cyanrip || printf '%s\n' "$banner"
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
  if inbox sh -c 'command -v sg_raw && command -v sg_turs && command -v cdrdao && command -v strace' >/dev/null 2>&1; then
    echo "sg3_utils, cdrdao and strace are already in the container."
    return 0
  fi
  say "Installing the read-only tools in the container (it may ask for your password)"
  inbox sudo dnf install -y sg3_utils cdrdao strace
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
    # Keep the sub-channel only: 96 raw bytes a frame (raw reads), 16 formatted
    # (Q reads); the 2352 bytes of audio before them are dropped (rule #8).
    local f
    for f in raw*.bin; do [ -f "$f" ] && strip_audio "$f" 2448 96 >> times.txt; done
    for f in q*.bin; do [ -f "$f" ] && strip_audio "$f" 2368 16 >> times.txt; done
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

# EVERY RIP'S RIPPER RECORD (the fork's round 39 lap 1 S10, BLOCKING: "put each
# rip's --diagnostics record in the bundle, in the test burn and from now on").
# The app asks every fork rip for one (`cyanrip_backend.diagnostics_args_for_build`)
# and cyanrip writes it where the rip ran, the rips folder's ROOT, as
# cyanrip-diagnostics-<UTC>.json; the securing pass's is kept beside its album as
# ...-securingpass.json. pack() moves album folders only, so until now no
# record of a drive-test rip reached an upload, and the fork could not compare
# track 3's per-second CRCs (their S9). JSON text, 20 to 160 kB each, never audio;
# the newest 400 are kept and any more counted. $1 the start marker, $2 the folder.
copy_records() {
  local since="$1" dest="$2" found kept
  mkdir -p "$dest"
  found="$(find "$RIPS" "$DM" -maxdepth 4 -type f -name 'cyanrip-diagnostics-*.json' \
    -newer "$since" -not -path "$dest/*" -printf '%T@ %p\n' 2>/dev/null | sort -rn)" || found=""
  kept=0
  if [ -n "$found" ]; then
    while read -r _ f; do
      [ "$kept" -lt 400 ] || break
      # A name met twice (a record moved with its album) keeps both, numbered.
      local name; name="$(basename "$f")"
      [ -e "$dest/$name" ] && name="$kept-$name"
      cp "$f" "$dest/$name" && kept=$((kept + 1))
    done <<< "$found"
  fi
  local total; total="$(printf '%s' "$found" | grep -c . || true)"
  echo "ripper records: $kept of ${total:-0} found in $RIPS and $DM since $(date -u -r "$since" '+%Y-%m-%d %H:%M UTC')" \
    | tee "$dest/RECORDS.txt"
}

# One upload: the named pieces, the log, every bundle made since the test began,
# and every ripper record written since then (copy_records).
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
  # The kernel's own messages about the drive since the test began (resets,
  # aborted commands, medium errors), which no program's log carries; and a
  # manifest of the upload, so the reader can check nothing was lost in transit.
  # Both from the fork's runner (their tools/rig-drivetest.sh), folded into this
  # one on our round 38 lap 15 S5.
  journalctl -k --no-pager -o short-iso --since "@$(stat -c %Y "$since")" 2>/dev/null \
    | grep -i -E "sr[0-9]|cdrom|scsi|ata[0-9]" > "$stage/kernel.txt" \
    || echo "(no kernel messages about the drive since the test began, or journalctl unreadable)" > "$stage/kernel.txt"
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
  copy_records "$since" "$stage/records"
  # Listed into a file outside the folder, then moved in, so the manifest never
  # lists itself half-written.
  ( cd "$stage" && find . -type f -exec sha256sum {} + | sort -k2 > "$DM/.manifest.tmp" ) && mv "$DM/.manifest.tmp" "$stage/MANIFEST.txt"
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
  echo "Next, in Windows: put PureRead back as your first screenshot shows, AND turn"
  echo "Advanced Quiet Drive OFF. Then come back and run:"
  echo "  bash $SELF quiet"
  echo "(To skip the Quiet Drive test, put only PureRead back and run: bash $SELF restored)"
  echo "Upload your Windows screenshots with that file."
}

# Phase 3b, agreed with the fork on 2026-11-10 (their reading of Run C: every rip
# read at 2.9x to 3.5x whether 4x or 24x was asked, and the drive's settings
# block reports Quiet mode on, which may cap the speed). Run after Windows has
# put PureRead back and turned Advanced Quiet Drive OFF: reads the settings, then
# runs the speed test again (Run E). `restored` afterwards checks both went back.
quiet() {
  is_done track9 || stop "phases 1 and 2 are not finished. Run: bash $SELF"
  say "Phase 3b: Quiet Drive should now be OFF. Reading the drive again (read-only)"
  date -u > "$STATE/quiet.started"
  UPLOAD_NAME=quiet; UPLOAD_SINCE="$STATE/quiet.started"; UPLOAD_PIECES=(dumps runE-logs.tar.gz)
  fetch_scripts
  wait_disc
  if ! is_done quietreadings; then
    dump pioneer-f4-quiet "sg_raw -R -r 256 $DEVICE 3c 02 f4 00 00 00 00 01 00 00"
    dump after-quiet "sg_inq $DEVICE; sg_get_config -q $DEVICE; sg_get_config -q -H $DEVICE; for c in 0 1 2 3; do echo \"=== page control \$c ===\"; sg_modes -a -c \$c $DEVICE; done"
    done_mark quietreadings
  fi
  if [ "$(f4_bytes "$DM/dumps/pioneer-f4.txt")" = "$(f4_bytes "$DM/dumps/pioneer-f4-quiet.txt")" ]; then
    say "The drive's settings bytes are THE SAME as the first reading, so Quiet Drive may not have changed. Running Run E anyway."
  else
    say "The drive's settings bytes CHANGED since the first reading."
  fi
  run_script drivespeed ds runE
  make_upload quiet "$STATE/quiet.started" "${UPLOAD_PIECES[@]}"
  echo
  echo "Next: in Windows, put Advanced Quiet Drive back as your first screenshot shows, then come back and run:"
  echo "  bash $SELF restored"
}

# Round 39's gate G4, the physics, once per session (the owner's plan of
# 2026-11-11; ported from the fork's tools/rig-drivetest.sh, its do_check and
# do_c2, so one runner carries both, our round 38 lap 15 S5). Run with
# Platterpus CLOSED and the reference disc in. Read-only throughout.
#   1. One disc read alone, timed.
#   2. Two disc reads 2.4 s apart, timed: whether two reads at once stall
#      without the app (round 38's Run A stopped on two overlapping reads).
#   3. The C2 probe: READ CD asking for C2 error pointers (byte 9 = 12h, 2646
#      bytes a frame) at a control (LBA 5000) and where the wrong samples sit:
#      track 3 at LBA 46422, 46446 and 46911 (04:04-04:11 into it) and track 5 at
#      83416 (02:24.59), three reads each after a cache flush, then once more at
#      track 5 with the block error bits (14h). It says whether the drive flags
#      the samples it gets wrong, which decides how round 39 re-reads.
PROBE_SECS="${DRIVETEST_PROBE_SECS:-300}"
probe() {
  UPLOAD_NAME=probe; UPLOAD_SINCE="$STATE/probe.started"; UPLOAD_PIECES=(probe)
  date -u > "$STATE/probe.started"
  install_tools
  pgrep -f "platterpus-x86_64.AppImage" >/dev/null 2>&1 && stop "Platterpus is open. Close it, then run this again: the probe needs the drive to itself."
  wait_disc
  local c="$DM/probe" t0 rc secs
  mkdir -p "$c"
  say "Probe 1 of 3: one disc read alone"
  t0=$(date +%s); rc=0
  timeout -k 5 "$PROBE_SECS" "$HOME/.local/bin/cyanrip" -I -N -d "$DEVICE" > "$c/solo.txt" 2>&1 || rc=$?
  secs=$(( $(date +%s) - t0 ))
  echo "one read alone: exit $rc after ${secs}s" | tee "$c/summary.txt"
  [ "$rc" = 0 ] || { echo "command: cyanrip -I -N -d $DEVICE; exit $rc; output in probe/solo.txt"; tail -20 "$c/solo.txt"; } | note_error "probe: the single disc read failed (going on)"
  wait_disc
  say "Probe 2 of 3: two disc reads, 2.4 s apart"
  ( t=$(date +%s); r=0; timeout -k 5 "$PROBE_SECS" "$HOME/.local/bin/cyanrip" -I -N -d "$DEVICE" > "$c/pairA.txt" 2>&1 || r=$?
    echo "$r $(( $(date +%s) - t ))" > "$c/pairA.rc" ) &
  local pa=$! rb=0 tb sb ra sa
  sleep 2.4
  tb=$(date +%s)
  timeout -k 5 "$PROBE_SECS" "$HOME/.local/bin/cyanrip" -I -N -d "$DEVICE" > "$c/pairB.txt" 2>&1 || rb=$?
  sb=$(( $(date +%s) - tb ))
  wait "$pa" || true
  read -r ra sa < "$c/pairA.rc"
  echo "two reads 2.4 s apart: A exit $ra after ${sa}s; B exit $rb after ${sb}s (124 or 137 = killed at ${PROBE_SECS}s)" | tee -a "$c/summary.txt"
  if [ "$ra" != 0 ] || [ "$rb" != 0 ]; then
    { echo "A exit $ra after ${sa}s, B exit $rb after ${sb}s"; echo "--- A's last lines"; tail -15 "$c/pairA.txt"; echo "--- B's last lines"; tail -15 "$c/pairB.txt"; } \
      | note_error "probe: two reads at once did not both finish (kept; going on)"
  fi
  # A pair that stalled (killed at the limit: 124 or 137) runs again under
  # strace, so the record shows the system call each read was in when it
  # stopped (the fork's lap 16 S9, as their runner does it).
  case "$ra $rb" in
    *124*|*137*)
      say "Probe 2b: a read stalled; the pair again under strace"
      pgrep -f "cyanrip -I -N -d $DEVICE" >/dev/null 2>&1 && pkill -KILL -f "cyanrip -I -N -d $DEVICE"
      wait_disc
      ( timeout -k 5 "$PROBE_SECS" distrobox enter ripping -- strace -f -tt -v -s 32 -e trace=openat,ioctl,read,close \
          -o "$c/pairA.strace" /usr/local/bin/cyanrip -I -N -d "$DEVICE" > "$c/pairA-strace.txt" 2>&1 || true ) &
      local ps=$!
      sleep 2.4
      timeout -k 5 "$PROBE_SECS" distrobox enter ripping -- strace -f -tt -v -s 32 -e trace=openat,ioctl,read,close \
          -o "$c/pairB.strace" /usr/local/bin/cyanrip -I -N -d "$DEVICE" > "$c/pairB-strace.txt" 2>&1 || true
      wait "$ps" || true
      for f in "$c"/pair?.strace; do
        [ -f "$f" ] && echo "$(basename "$f"): last call: $(grep -v 'resumed\|exited\|killed' "$f" | tail -1 | cut -c1-200)" | tee -a "$c/summary.txt"
      done ;;
  esac
  # A read this probe started and that is still running would hold the drive
  # for the C2 reads; it is ours, so it is stopped (only `-I -N` reads on this
  # device, the ones the probe itself ran).
  sleep 2
  if pgrep -f "cyanrip -I -N -d $DEVICE" >/dev/null 2>&1; then
    pkill -KILL -f "cyanrip -I -N -d $DEVICE" || true
    echo "a probe read was still running after both ended; stopped it" | tee -a "$c/summary.txt"
  fi
  wait_disc
  say "Probe 3 of 3: the C2 probe"
  local t lba n out
  for t in control:5000 t3a:46422 t3b:46446 t3c:46911 t5:83416; do
    lba="${t#*:}"; t="${t%%:*}"
    for n in 1 2 3; do
      c2_flush
      out="$c/$t-c2-$n.bin"
      if ! c2_read "$out" "$lba" 12 2646 > "$out.txt" 2>&1; then
        { echo "READ CD with byte 9 = 12h at LBA $lba, read $n"; cat "$out.txt"; } | note_error "probe: the drive refused C2 pointers at $t (kept; going on)"
        if [ "$t" = control ]; then echo "the drive refused C2 pointers at the control; the rest is skipped" | tee -a "$c/summary.txt"; break 2; fi
      fi
    done
  done
  c2_flush
  c2_read "$c/t5-c2b-1.bin" 83416 14 2648 > "$c/t5-c2b-1.bin.txt" 2>&1 \
    || { echo "READ CD with byte 9 = 14h at LBA 83416"; cat "$c/t5-c2b-1.bin.txt"; } | note_error "probe: the drive refused the block error bits (kept; going on)"
  python3 -I - "$c" >> "$c/summary.txt" 2>&1 <<'PY' || echo "(could not summarise the C2 reads; they are kept)" >> "$c/summary.txt"
import pathlib, sys
d = pathlib.Path(sys.argv[1])
for f in sorted(d.glob("*-c2-*.bin")):
    data = f.read_bytes()
    if len(data) != 26 * 2646:
        print(f"{f.name}: {len(data)} bytes, not 26 frames of 2646")
        continue
    flagged = []
    for i in range(26):
        bits = sum(bin(b).count("1") for b in data[i * 2646 + 2352:(i + 1) * 2646])
        if bits:
            flagged.append(f"frame {i} ({bits} bit{'s' if bits != 1 else ''})")
    print(f"{f.name}: " + (", ".join(flagged) if flagged else "no C2 bit set in 26 frames"))
PY
  local f
  for f in "$c"/*-c2-*.bin; do [ -f "$f" ] && strip_audio "$f" 2646 294 >> "$c/summary.txt"; done
  [ -f "$c/t5-c2b-1.bin" ] && strip_audio "$c/t5-c2b-1.bin" 2648 296 >> "$c/summary.txt"
  cat "$c/summary.txt"
  done_mark probe
  make_upload probe "$STATE/probe.started" "${UPLOAD_PIECES[@]}"
}

# READ CD (BEh), 26 frames from LBA $2, byte 9 = $3, $4 bytes a frame.
c2_read() {
  # shellcheck disable=SC2046  # the LBA's four bytes are four arguments
  inbox sg_raw -R -o "$1" -r $((26 * $4)) "$DEVICE" be 00 \
    $(printf '%02x %02x %02x %02x' $(( ($2 >> 24) & 255 )) $(( ($2 >> 16) & 255 )) $(( ($2 >> 8) & 255 )) $(( $2 & 255 ))) \
    00 00 1a "$3" 00 00
}

# Read 312 sectors at the start of the disc, more than the drive's 128 to 255
# sector cache, so the next read comes from the disc.
c2_flush() {
  inbox sh -c "for l in 0 26 52 78 104 130 156 182 208 234 260 286; do sg_raw -R -r 61152 $DEVICE be 00 \$(printf '%02x %02x %02x %02x' 0 0 \$((l>>8)) \$((l&255))) 00 00 1a 10 00 00 >/dev/null 2>&1; done"
}

# KEEP NO AUDIO FROM A RAW READ (Critical rule #8). READ CD returns each
# frame's 2352 bytes of audio beside what we asked for (the C2 pointers, or
# the sub-channel); a fraction of a second of a commercial album is still the
# album, and these files go to both sessions and their evidence branches. This
# rewrites FILE keeping only each frame's last TAIL bytes (FRAME bytes a frame),
# as FILE.noaudio, and deletes FILE. $1 FILE, $2 FRAME, $3 TAIL.
strip_audio() {
  python3 -I - "$1" "$2" "$3" <<'PY'
import pathlib, sys
src = pathlib.Path(sys.argv[1]); frame = int(sys.argv[2]); tail = int(sys.argv[3])
data = src.read_bytes()
kept = b"".join(data[i + frame - tail:i + frame] for i in range(0, len(data) - frame + 1, frame))
pathlib.Path(str(src) + ".noaudio").write_bytes(kept)
print(f"{src.name}: {len(data)} bytes read, {len(data) // frame} frame(s); kept {len(kept)} bytes, audio dropped")
PY
  rm -f "$1"
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

# The fork's round 39 lap 1 S10: the records of 2026-11-09 and 2026-11-10, if
# they are still in the rips folder, give track 3's comparison with no rig time.
# Reads nothing from the drive; needs neither the app closed nor a disc.
records() {
  local since="$STATE/records.since"
  touch -d "${DRIVETEST_RECORDS_SINCE:-2026-11-09T00:00:00Z}" "$since"
  UPLOAD_NAME=records; UPLOAD_SINCE="$since"; UPLOAD_PIECES=()
  say "Collecting every ripper record in $RIPS since $(date -u -r "$since" '+%Y-%m-%d %H:%M UTC')"
  make_upload records "$since"
}

status() {
  local s
  for s in readings runA wipe runB runC track9 perfectreadings runD quietreadings runE probe; do
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
  quiet)    quiet ;;
  probe)    probe ;;
  restored) restored ;;
  records)  records ;;
  status)   status ;;
  *) echo "usage: bash $SELF [perfect|quiet|restored|probe|records|status]"; exit 2 ;;
esac
