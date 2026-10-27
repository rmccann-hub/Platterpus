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
RIPS_LISTED=yes
if [ -d ~/Music/rips ]; then
  # Listed first, sorted second: inside one pipeline a failing `find` was
  # invisible and printed "no rip folder found", which is a different fact.
  if RIPS=$(find ~/Music/rips -mindepth 2 -maxdepth 2 -type d -printf '%T@ %p\n'); then
    NEWEST=$(printf '%s\n' "$RIPS" | sort -rn | head -1 | cut -d' ' -f2-)
  else
    echo "  COULD NOT LIST ~/Music/rips (find failed) -- the newest rip is NOT in this bundle"
    RIPS_LISTED=no
  fi
fi
if [ -n "$NEWEST" ]; then
  echo "  from: $NEWEST"
  mkdir -p "$OUT/rip"
  optional find "$NEWEST" -maxdepth 2 -type f \
    \( -iname '*.log' -o -iname '*.cue' -o -iname '*.json' -o -iname '*.txt' -o -iname '*.m3u*' \) \
    -exec cp {} "$OUT/rip"/ \;
  optional ls "$OUT/rip"
elif [ "$RIPS_LISTED" = yes ]; then
  echo "  no rip folder found"
fi

echo; echo "== proving no audio slipped in =="
# Every extension the repository's audio guards refuse. This script is
# downloaded and run on its own, so it cannot read the repository's shared list
# (.githooks/audio-extensions.txt) and carries a copy; tests/test_media_guard_hook.py
# holds this line equal to that file. It checked 7 of the 18 until 2026-10-27
# (external review item 1.6), so a bundle holding a .ogg, .opus or .pcm was
# reported "clean".
AUDIO_EXTS="flac wav pcm raw mp3 m4a aac ogg oga opus wv ape wma aiff aif alac dsf dff"

# List the bundle's audio files, one per line. Exits non-zero if `find` fails,
# which the callers below treat as "could not look", never as "none found".
audio_in_bundle() {
  local args=() ext
  for ext in $AUDIO_EXTS; do
    if [ "${#args[@]}" -gt 0 ]; then args+=(-o); fi
    args+=(-iname "*.$ext")
  done
  find "$OUT" -type f \( "${args[@]}" \)
}

# The check that lets this script print "clean". It must SUCCEED before its
# silence means anything: with `|| true`, a `find` that failed printed "clean -
# no audio files in the bundle" about a bundle nobody had looked at (Critical
# rule #8; fixed 2026-10-12). If it cannot look, nothing is packed.
if ! AUDIO=$(audio_in_bundle); then
  echo "  COULD NOT CHECK the bundle for audio (find failed) -- NOT packing it." >&2
  echo "  Nothing was uploaded. Fix the error above and run this again." >&2
  exit 1
fi
if [ -n "$AUDIO" ]; then
  echo "  REMOVING audio that must not be here:"; printf '%s\n' "$AUDIO" | sed 's/^/    /'
  # `IFS= read -r` hands `rm` each line exactly as `find` printed it (review
  # item 3.7). A bare `read` strips leading and trailing blanks; that could not
  # bite here, since every line starts with "$OUT/" and ends in an extension,
  # but the exact form costs nothing and does not rely on that. A here-string
  # rather than a pipe keeps the loop in this shell, so a failed `rm` is
  # reported here.
  while IFS= read -r f; do
    rm -f -- "$f" || echo "  could not remove: $f" >&2
  done <<<"$AUDIO"
  # Removal is a claim until it is checked. Look again, and refuse to pack a
  # bundle that still holds audio (a name with a newline in it, for one, cannot
  # survive the one-name-per-line list above).
  if ! LEFT=$(audio_in_bundle); then
    echo "  COULD NOT RE-CHECK the bundle after removing audio -- NOT packing it." >&2
    exit 1
  fi
  if [ -n "$LEFT" ]; then
    echo "  AUDIO IS STILL IN THE BUNDLE -- NOT packing it. Remove these by hand:" >&2
    printf '%s\n' "$LEFT" | sed 's/^/    /' >&2
    exit 1
  fi
  echo "  removed; the bundle is now clean"
else
  echo "  clean - no audio files in the bundle"
fi

tar -czf ~/platterpusbundle.tar.gz -C ~ platterpusbundle
echo
echo "=================================================="
echo "UPLOAD THIS ONE FILE:  ~/platterpusbundle.tar.gz"
du -h ~/platterpusbundle.tar.gz
echo "=================================================="
