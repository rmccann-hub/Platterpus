#!/usr/bin/env bash
# Collect everything needed to diagnose a Platterpus rig run into ONE file.
#
# NEVER copies audio. Only text: transcripts, logs, cue sheets, the rip report,
# the EAC-compatible log, the seam-check manifest. That is deliberate and not
# only about size -- the CRCs in those files prove bit-perfection without the
# audio, and shipping music around is the one thing this project refuses to do.
#
# `set -eu` is the repo's shell rule and is load-bearing here: without it a
# failed copy of the transcript would be invisible and the bundle would arrive
# LOOKING complete while missing the evidence. Everything that may legitimately
# find nothing goes through `optional`, so "absent" and "broken" stay different.
set -eu

OUT=~/platterpusbundle
rm -rf "$OUT"
mkdir -p "$OUT"

# Run a command that is ALLOWED to fail (the file may simply not exist yet).
# Anything not wrapped in this is required, and `set -e` will stop on it.
optional() { "$@" || true; }

echo "== versions =="
{
  optional ~/Applications/platterpus-x86_64.AppImage --version
  optional ~/.local/bin/cyanrip --version
} > "$OUT/versions.txt" 2>&1
optional cat "$OUT/versions.txt"

echo; echo "== preflight =="
optional ~/Applications/platterpus-x86_64.AppImage --doctor > "$OUT/doctor.txt" 2>&1
optional tail -3 "$OUT/doctor.txt"

echo; echo "== script transcripts =="
if [ -d ~/.local/share/platterpus/uiscript ]; then
  cp -r ~/.local/share/platterpus/uiscript "$OUT/uiscript"   # required: it is the point
  find "$OUT/uiscript" -type f | sed "s|$OUT/|  |"
else
  echo "  none found — was a script run on this machine?"
fi

echo; echo "== app log =="
if [ -f ~/.local/share/platterpus/log.txt ]; then
  for f in ~/.local/share/platterpus/log.txt*; do cp "$f" "$OUT"/; done
  echo "  copied"
else
  echo "  none"
fi

echo; echo "== settings =="
for f in ~/.config/platterpus/config.toml ~/.config/platterpus/drive_profiles.json; do
  [ -f "$f" ] && cp "$f" "$OUT"/ && echo "  $(basename "$f")"
done
true   # the loop's last test may be false; that is not a failure

echo; echo "== newest rip's TEXT artifacts (no audio) =="
NEWEST=""
if [ -d ~/Music/rips ]; then
  NEWEST=$(find ~/Music/rips -mindepth 2 -maxdepth 2 -type d -printf '%T@ %p\n' 2>/dev/null \
           | sort -rn | head -1 | cut -d' ' -f2- || true)
fi
if [ -n "$NEWEST" ]; then
  echo "  from: $NEWEST"
  mkdir -p "$OUT/rip"
  optional find "$NEWEST" -maxdepth 2 -type f \
    \( -iname '*.log' -o -iname '*.cue' -o -iname '*.json' -o -iname '*.txt' -o -iname '*.m3u*' \) \
    -exec cp {} "$OUT/rip"/ \;
  optional ls "$OUT/rip"
else
  echo "  no rip folder found"
fi

echo; echo "== proving no audio slipped in =="
AUDIO=$(find "$OUT" -type f \( -iname '*.flac' -o -iname '*.wav' -o -iname '*.mp3' \
        -o -iname '*.wv' -o -iname '*.m4a' -o -iname '*.ape' -o -iname '*.aiff' \) || true)
if [ -n "$AUDIO" ]; then
  echo "  REMOVING audio that must not be here:"; echo "$AUDIO" | sed 's/^/    /'
  echo "$AUDIO" | while read -r f; do rm -f "$f"; done
else
  echo "  clean - no audio files in the bundle"
fi

tar -czf ~/platterpusbundle.tar.gz -C ~ platterpusbundle
echo
echo "=================================================="
echo "UPLOAD THIS ONE FILE:  ~/platterpusbundle.tar.gz"
du -h ~/platterpusbundle.tar.gz
echo "=================================================="
