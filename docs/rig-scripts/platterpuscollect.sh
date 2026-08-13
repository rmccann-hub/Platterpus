#!/usr/bin/env bash
# Collect everything needed to diagnose a Platterpus run into ONE file.
#
# NEVER copies audio. Only text: transcripts, logs, cue sheets, the rip report,
# the EAC-compatible log, the seam-check manifest. That is deliberate and not
# only about size -- the CRCs in those files prove bit-perfection without the
# audio, and shipping music around is the one thing this project refuses to do.
set -u
OUT=~/platterpusbundle
rm -rf "$OUT" 2>/dev/null
mkdir -p "$OUT"

echo "== versions =="
{
  ~/Applications/platterpus-x86_64.AppImage --version 2>&1
  ~/.local/bin/cyanrip --version 2>&1 | head -3
} > "$OUT/versions.txt" 2>&1
cat "$OUT/versions.txt"

echo; echo "== preflight =="
~/Applications/platterpus-x86_64.AppImage --doctor > "$OUT/doctor.txt" 2>&1
tail -3 "$OUT/doctor.txt"

echo; echo "== script transcripts =="
if [ -d ~/.local/share/platterpus/uiscript ]; then
  cp -r ~/.local/share/platterpus/uiscript "$OUT/uiscript"
  find "$OUT/uiscript" -type f | sed "s|$OUT/|  |"
else
  echo "  none"
fi

echo; echo "== app logs =="
cp ~/.local/share/platterpus/log.txt* "$OUT"/ 2>/dev/null && echo "  copied" || echo "  none"

echo; echo "== settings =="
cp ~/.config/platterpus/config.toml "$OUT"/ 2>/dev/null
cp ~/.config/platterpus/drive_profiles.json "$OUT"/ 2>/dev/null
ls "$OUT" | grep -E 'config.toml|drive_profiles' | sed 's/^/  /'

echo; echo "== newest rip's TEXT artifacts (no audio) =="
NEWEST=$(find ~/Music/rips -mindepth 2 -maxdepth 2 -type d -printf '%T@ %p\n' 2>/dev/null \
         | sort -rn | head -1 | cut -d' ' -f2-)
if [ -n "${NEWEST:-}" ]; then
  echo "  from: $NEWEST"
  mkdir -p "$OUT/rip"
  find "$NEWEST" -maxdepth 2 -type f \
    \( -iname '*.log' -o -iname '*.cue' -o -iname '*.json' -o -iname '*.txt' -o -iname '*.m3u*' \) \
    -exec cp {} "$OUT/rip"/ \; 2>/dev/null
  ls "$OUT/rip" 2>/dev/null | sed 's/^/    /' || echo "    (no text artifacts yet)"
else
  echo "  no rip folder found"
fi

echo; echo "== proving no audio slipped in =="
AUDIO=$(find "$OUT" -type f \( -iname '*.flac' -o -iname '*.wav' -o -iname '*.mp3' \
        -o -iname '*.wv' -o -iname '*.m4a' -o -iname '*.ape' \) | head)
if [ -n "$AUDIO" ]; then
  echo "  REMOVING audio that should not be here:"; echo "$AUDIO" | sed 's/^/    /'
  find "$OUT" -type f \( -iname '*.flac' -o -iname '*.wav' -o -iname '*.mp3' \
       -o -iname '*.wv' -o -iname '*.m4a' -o -iname '*.ape' \) -delete
else
  echo "  clean - no audio files in the bundle"
fi

tar -czf ~/platterpusbundle.tar.gz -C ~ platterpusbundle
echo
echo "=================================================="
echo "UPLOAD THIS ONE FILE:  ~/platterpusbundle.tar.gz"
du -h ~/platterpusbundle.tar.gz
echo "=================================================="
