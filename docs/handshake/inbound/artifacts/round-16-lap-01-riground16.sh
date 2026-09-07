#!/bin/sh
# Round 16 acceptance rips -- the three clauses of the close condition.
#
# WHAT THIS IS FOR. Round 16 lap 1 fixes one close condition: a hardware run on
# pin a9aedf0 establishing that the AccurateRip path still succeeds with the
# rewritten response parser, that -H together with de-emphasis produces correct
# de-emphasised audio, and that no line Platterpus parses has moved except the
# ones the lap's section D names.
#
# WHY IT RIPS ONLY A FEW TRACKS. -l takes a track list, so each rip is under a
# minute rather than ten. Tracks 1-3 of the reference disc are not an arbitrary
# choice: on 2026-08-05 they returned three DIFFERENT AccurateRip response
# shapes -- found, not-found, and a 450-frame partial -- so a three-track rip
# exercises three arms of the parser that was rewritten.
#
# WHAT IT DOES NOT DO. It does not judge. It prints what was measured beside
# what the record says to expect and leaves the verdict to a human, per the
# ownership rule. It never writes outside --out.
#
# THE -j HAZARD IS REAL AND UNEXPLAINED. docs/SETTLED.md records C1: on the same
# drive and disc, `-N -l 1` took 4.9 s and exited 1, while a run carrying
# `-j -D -o -u` took 1800 s and was SIGKILLed. That is Platterpus's
# observation (their lap 16 section D) and the cause was never found. Note the
# controlled pair differs in FOUR flags, so "-j-associated" is as far as the
# evidence goes -- it is not established that -j is the cause. Every invocation
# here is therefore wrapped in timeout(1), and a timeout is recorded as a
# reproduction rather than as a script failure.

set -u

DEV=${DEV:-/dev/sr0}
OFFSET=${OFFSET:-667}          # the BDR-209D's read offset, as used on 2026-08-05.
                               # AccurateRip checksums DEPEND on this being right;
                               # a wrong offset makes every comparison below fail
                               # for a reason that has nothing to do with the parser.
OUT=${OUT:-./round16-$(date -u +%Y%m%dT%H%M%SZ)}
CRIP=${CRIP:-cyanrip}
LIMIT=${LIMIT:-600}            # per-invocation ceiling, seconds
EXPECT_BUILD=platterpus-fork-ga9aedf0

mkdir -p "$OUT" || exit 1
echo "output: $OUT"
echo

run() {                        # run <name> <clause> -- <argv...>
  name=$1; clause=$2; shift 3
  printf '=== %-22s %s\n' "$name" "$clause"
  printf '    %s' "$CRIP"; for a in "$@"; do printf ' %s' "$a"; done; printf '\n'
  start=$(date +%s)
  timeout "$LIMIT" "$CRIP" "$@" > "$OUT/$name.stdout" 2>&1
  rc=$?
  end=$(date +%s)
  echo "    exit $rc in $((end-start))s   -> $OUT/$name.stdout"
  if [ "$rc" = 124 ]; then
    echo "    *** TIMED OUT at ${LIMIT}s. This is a C1 reproduction, not a script"
    echo "    *** failure. Keep this directory; it is the evidence."
  fi
  echo "$rc" > "$OUT/$name.exit"
  echo
}

# ---------------------------------------------------------------- preflight
echo "=== preflight: is the PIN installed? ==="
banner=$("$CRIP" --version 2>&1 | head -1)
echo "    $banner"
case "$banner" in
  *"$EXPECT_BUILD"*) echo "    OK: this is the round-16 pin." ;;
  *) echo "    *** NOT THE PIN. Expected $EXPECT_BUILD."
     echo "    *** Evidence from another build cannot close this round. Stop." ;;
esac
echo "$banner" > "$OUT/banner.txt"
echo

echo "=== the disc in the drive ==="
timeout 120 "$CRIP" -d "$DEV" -N -A -U -I > "$OUT/disc-info.txt" 2>&1
grep -E "^(DiscID|CDDB ID|Disc tracks|Total time):" "$OUT/disc-info.txt" | sed 's/^/    /'
echo "    (reference disc for clause 1 is DiscID pNtImOkdBm9RMBIalzx0w9cfsYY-,"
echo "     CDDB E20DFE0E, 14 tracks, 59:42.57 -- The Police, 'Every Breath You"
echo "     Take: The Classics'. A DIFFERENT disc still tests the parser, but"
echo "     the line-by-line comparison below only means something on that one.)"
echo

# ------------------------------------------------- clause 1: AccurateRip
# -A DISABLES AccurateRip, so it is deliberately ABSENT here. -N and -U stay,
# so the ONLY network call this run makes is the AccurateRip query -- which is
# the thing under test, with the fewest other variables in play.
run accurip "clause 1 -- AccurateRip path, rewritten parser" -- \
    -d "$DEV" -s "$OFFSET" -l 1,2,3 -N -U -o flac \
    -D "$OUT/accurip" -F "{track}" -L accurip -M accurip

# ------------------------------------------- clause 2: -H with de-emphasis
# The pair is the point. -H -E forces de-emphasis with HDCD decoding on; -H -W
# disables it with everything else identical. Before the fix these produced
# BYTE-IDENTICAL audio, because the filter string was a ternary cascade and
# aemphasis was never reached. They must now differ.
run hdcd-deemph "clause 2 -- -H with de-emphasis forced" -- \
    -d "$DEV" -s "$OFFSET" -l 1 -N -A -U -o flac -H -E \
    -D "$OUT/hdcd-deemph" -F "{track}" -L hdcd-deemph -M hdcd-deemph

run hdcd-nodeemph "clause 2 -- the control: same rip, de-emphasis OFF" -- \
    -d "$DEV" -s "$OFFSET" -l 1 -N -A -U -o flac -H -W \
    -D "$OUT/hdcd-nodeemph" -F "{track}" -L hdcd-nodeemph -M hdcd-nodeemph

# --------------------------------- clause 3 + the -j record's new schema
# Separated from the rips above precisely BECAUSE of C1: if -j is what hangs,
# it hangs here and the other evidence is already on disk.
run plain-j "clause 3 -- a plain rip, and the -j record at schema /4" -- \
    -d "$DEV" -s "$OFFSET" -l 1 -N -A -U -o flac \
    -D "$OUT/plain" -F "{track}" -L plain -M plain -j "$OUT/plain.json"

# ================================================================ summary
echo "================================ measurements ================================"
echo
echo "--- clause 1: AccurateRip lines this run produced ---"
if [ -f "$OUT/accurip/accurip.log" ]; then
  grep -aE "^AccurateRip:|Accurip (v1|v2|450):" "$OUT/accurip/accurip.log" | sed 's/^/    /'
else
  echo "    no logfile written -- read $OUT/accurip.stdout"
fi
cat <<'EXPECTED'

    ON RECORD from docs/rig-2026-08-05/cyanrip.log, same disc, same offset,
    tracks 1-3, produced by an OLDER build with the OLD parser:

    AccurateRip:    found
        Accurip v1:  5D3C90CB (accurately ripped, confidence 129)
        Accurip v2:  22B9924D (accurately ripped, confidence 200)
        Accurip v1:  A3019EB3 (accurately ripped, confidence 131)
        Accurip v2:  31C28378 (accurately ripped, confidence 200)
        Accurip v1:  DCA378E8 (not found, either a new pressing, or bad rip)
        Accurip v2:  36F6EA91 (not found, either a new pressing, or bad rip)
        Accurip 450: BF62B1DA (matches Accurip DB, confidence 200, track is partially accurately ripped)

    The CHECKSUMS must match exactly -- they are arithmetic over the same audio.
    The CONFIDENCES may legitimately have risen: they are a count of other
    people's submissions and the database moves. A confidence that FELL, or a
    checksum that differs, is a finding.
EXPECTED
echo
echo "--- clause 2: the two rips must DIFFER ---"
a=$(find "$OUT/hdcd-deemph" -name '*.flac' 2>/dev/null | head -1)
b=$(find "$OUT/hdcd-nodeemph" -name '*.flac' 2>/dev/null | head -1)
if [ -n "$a" ] && [ -n "$b" ]; then
  ha=$(md5sum "$a" | cut -d' ' -f1); hb=$(md5sum "$b" | cut -d' ' -f1)
  echo "    -H -E : $ha"
  echo "    -H -W : $hb"
  if [ "$ha" = "$hb" ]; then
    echo "    *** IDENTICAL -- de-emphasis did not reach the audio. Clause 2 FAILS."
  else
    echo "    differ, which is what the fix was for."
    echo "    (container bytes include a creation_time that differs between ANY two"
    echo "     rips, so a difference here is necessary and not sufficient. The"
    echo "     decoded-sample comparison below is the one that means something.)"
  fi
  # THE DECODED SAMPLES ARE THE CLAIM, not the container. Two rips by the same
  # binary differ in creation_time regardless, so a container difference is
  # necessary and not sufficient -- this project has stated a wrong version of
  # that claim before and the long true sentence is the one to keep.
  if command -v ffmpeg >/dev/null 2>&1; then
    for f in "$a" "$b"; do
      printf '    decoded %-16s %s\n' "$(basename "$(dirname "$f")")" \
        "$(ffmpeg -v error -i "$f" -f md5 - 2>/dev/null | sed 's/^MD5=//')"
    done
    echo "    THESE are the two that must differ. If the containers differ and the"
    echo "    decoded samples do not, de-emphasis did not reach the audio."
  else
    echo "    ffmpeg absent -- decoded-sample comparison UNPROBED. The container"
    echo "    comparison above cannot settle clause 2 on its own; install ffmpeg"
    echo "    or bring the flacs back for the comparison to be done off the rig."
  fi
else
  echo "    one or both rips produced no flac -- read the .stdout files"
fi
echo
echo "--- clause 2, the other half: what the LOG and CUE claim ---"
grep -ah "Preemphasis:" "$OUT"/hdcd-deemph/*.log "$OUT"/hdcd-nodeemph/*.log 2>/dev/null | sed 's/^/    /'
# -h and a pipe, not -c: `grep -c` over several files prints ONE COUNT PER
# FILE, so the line came out as "0\n0" the first time this was run. Counting
# what the pattern returned, and asking whether it is the number expected, is
# the same rule this project already applies to greps over the record.
pre_e=$(cat "$OUT"/hdcd-deemph/*.cue 2>/dev/null | grep -ac 'FLAGS PRE'); pre_e=${pre_e:-0}
pre_w=$(cat "$OUT"/hdcd-nodeemph/*.cue 2>/dev/null | grep -ac 'FLAGS PRE'); pre_w=${pre_w:-0}
echo "    FLAGS PRE in the -H -E cue: $pre_e  (expect 0 -- the audio was de-emphasised)"
echo "    FLAGS PRE in the -H -W cue: $pre_w  (expect >0 ONLY if the disc's TOC flags pre-emphasis;"
echo "                                         on a disc that does not, 0 is correct in both)"
echo
echo "--- the -j record ---"
if [ -f "$OUT/plain.json" ]; then
  python3 - "$OUT/plain.json" <<'PY' 2>/dev/null || echo "    (python3 absent; read $OUT/plain.json)"
import json,sys
d=json.load(open(sys.argv[1]))
for k in ("schema","started_at","finished_at","exit_code"):
    print(f"    {k:12} {d.get(k)!r}")
print("    expect schema 'cyanrip-diagnostics/4' and two offset-bearing instants")
PY
else
  echo "    NO RECORD WRITTEN. If plain-j timed out, that is the C1 reproduction."
fi
echo
echo "--- every log's first line must be the fork banner, and -Y must verify ---"
for f in $(find "$OUT" -name '*.log' 2>/dev/null); do
  printf '    %-40s %s\n' "$(basename "$f")" "$(head -1 "$f")"
  timeout 60 "$CRIP" -Y "$f" >/dev/null 2>&1
  echo "        -Y exit $?  (0 = the log verifies against its own FUN512)"
done
echo
echo "=============================================================================="
echo "WHAT THIS RUN CANNOT ESTABLISH, whatever it printed:"
echo "  * C2 error reporting -- the rig's drive reports C2 unsupported."
echo "  * -f, offset autodetection. Not exercised here."
echo "  * damaged media. This disc is intact."
echo "  * CD-TEXT from a disc that has some, which is a different code path"
echo "    (mmc_read_cdtext) from the image parser every fixture uses."
echo "  * whether -H behaves correctly on a disc that genuinely carries"
echo "    pre-emphasis. -E FORCES the same filter graph, which is why the lap"
echo "    says -H -E is not a weaker substitute -- but a TOC-flagged disc would"
echo "    additionally show the flag being read."
echo
echo "Bring back the whole of $OUT."
