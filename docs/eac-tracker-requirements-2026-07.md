# EAC vs. Platterpus, measured against tracker logcheckers (2026-07-29)

**The question asked:** how does Platterpus compare to EAC, to EAC rips, and to what
music trackers require of a rip log?

**The short answer, and it is not the flattering one:** a Platterpus/cyanrip log will
**never** pass a tracker logchecker, and no amount of work on this codebase changes
that. The gate is *which program ripped the disc*, checked before a single quality
line is read. That is a hard architectural fact, not a gap to close — and the one way
to "close" it is forgery, which KDD-24 already rules out.

What *is* worth doing is the rest of this document: the requirements EAC's settings
encode are mostly about read correctness, and several are things Platterpus already
does but does not *say*, or could measure and currently leaves as "unknown". Those are
real archival-quality wins, and they are ranked at the end.

---

## 1. Who checks, and what they actually run

Trackers score logs with two open-source implementations. Both do a **ripper
allow-list first**, quality second:

| Checker | Accepts | Everything else |
|---|---|---|
| [OPSnet/Logchecker](https://github.com/OPSnet/Logchecker) (PHP; what OPS runs) | EAC, XLD, whipper ≥0.7.3 | `UnknownRipperException` → score **0**, "Unrecognized log file" |
| [ligh7s/hey-bro-check-log](https://github.com/ligh7s/hey-bro-check-log) (Python; "aligned with Redacted standards") | EAC ≥0.99, EAC95, XLD | `UnrecognizedException` — and the version string must be in a hardcoded table |

Redacted's own rules name only EAC and XLD, and treat a log from any other tool as
trumpable ([rules](https://interviewfor.red/en/rules.html),
[ripping](https://interviewfor.red/en/ripping.html)).

**So: cyanrip, morituri, dBpoweramp, Rubyripper, CUERipper — not accepted.** whipper is
the sole non-EAC/XLD exception, and only at OPS.

### Checksums are not the barrier — identity is

Worth being precise, because it is easy to assume the opposite. EAC's footer is an
obfuscated Rijndael-256 fold under a reverse-engineered key
([eac_logchecker.py](https://github.com/OPSnet/eac_logchecker.py),
[eac_logsigner](https://github.com/puddly/eac_logsigner)). But **whipper's checksum is a
plain SHA-256 of every line but the last, and OPS validates it**
(`src/Check/Checksum/Whipper.php`).

Platterpus's own footer is *structurally the same scheme* a real tracker already
accepts. The only thing between them is the ripper's name — which is exactly the right
place for the wall to be.

---

## 2. What the checkers deduct for

Recorded because these are the *quality* criteria worth caring about even when the
score is unreachable. From `heybrochecklog/resources/eac/english.json` +
`resources/__init__.py`, cross-checked against the PHP:

| Log line | Required | Deduction |
|---|---|---|
| `Read mode` | Secure | −20 |
| `Utilize accurate stream` | Yes | −20 |
| `Defeat audio cache` | Yes | −10 |
| `Make use of C2 pointers` | No | −20 |
| `Read offset correction` | matches the drive's AccurateRip value | −5 |
| `Fill up missing offset samples with silence` | Yes | −5 |
| `Delete leading and trailing silent blocks` | No | −5 |
| `Null samples used in CRC calculations` | Yes | −1 |
| `Gap handling` | Appended to previous track | −10 |
| `Add ID3 tag` | No | −1 |
| per-track `Test CRC` on every track | present | −20 |
| `Test CRC` ≠ `Copy CRC` | — | −30 per track |
| AccurateRip results | present | −5 |
| `==== Log checksum … ====` | present | −15 |

**Automatic zero:** unrecognised ripper; `Copy aborted`; `Normalize to`; `Use
compression offset`; a virtual/fake drive.

**Unscoreable rather than deducted** (thrown out): any of the settings lines *missing*;
a track missing filename/peak/copy-CRC; track count ≠ TOC count; an unknown version
string; a non-English log.

**Not scored at all:** overread into lead-in/lead-out. It is a recommendation.

---

## 3. Where Platterpus stands, row by row

cyanrip flags from `_build_rip_argv`: `-d`, `-s <offset>`, `-o flac`, `-r <retries>`,
`-Z <matches>`, `-O` (only when force-overread is on), `-S <speed>`, `-l <tracks>`,
`-N`, `-a`/`-t`, `-D`/`-F`, `-G`. Notably **no `-p`** — cyanrip's default already merges
pregaps into the previous track.

| Requirement | Platterpus equivalent | Status |
|---|---|---|
| Secure read | libcdio-paranoia always; `paranoia_level` allow-listed | **met** |
| Defeat audio cache | *measured* via `cd-paranoia -A` (KDD-29), not asserted | **met when probed** |
| Delete silent blocks: No | asserted for cyanrip (it writes what it reads) | **met** |
| Null samples in CRC: Yes | asserted for cyanrip (CRCs matched a real EAC log, 12/14 tracks) | **met** |
| Gap handling | wording **actually** fixed 2026-07-30 (see below) — says "Not detected, thus appended to previous track" | **wording met, detection is not** |
| Test & Copy | `-Z` convergence rendered as a Test/Copy pair | **partial** |
| AccurateRip | parsed and rendered; `verdict.py` is the single predicate | **met** |
| No ID3 on FLAC | Vorbis comments only | **met** |
| Individual tracks (not a range rip) | cyanrip is always per-track | **met** |
| No normalization / compression offset | never emitted | **met** |
| Read offset correction | `-s` applied; value printed but never asserted *correct* | **partial** |
| Fill missing offset samples with silence | derived from overread text, else unknown | **partial** |
| `Make use of C2 pointers` | **`No`, measured** on a drive that reports C2 unsupported; "(not reported)" otherwise (see below) | **met on the rig; open in general** |
| `Utilize accurate stream` | no equivalent | **open** |
| Signed EAC log footer | plain SHA-256, self-labelled *not* EAC's | **by design** |
| Recognised ripper name | never emitted (KDD-11/24/28) | **by design → score 0** |

### The C2 row — earned by the ripper, not by the survey (settled 2026-07-30)

The survey says libcdio-paranoia never uses C2 error pointers, which would let this
row be asserted `No` and remove EAC's most heavily-weighted unknown. **I changed it on
that basis, a test stopped me, and the test was right.**
`test_does_not_fabricate_read_mode_or_c2_pointers` exists precisely to stop a value
being printed into an archival log without evidence, and a secondary source summarising
libcdio is not the standard the silent-blocks and null-samples rows are held to.

**Then the rig answered it directly.** cyanrip's own header on the BDR-209D prints
`C2 errors: unsupported by drive`, the parser maps that to `False`, and the exported log
reads `Make use of C2 pointers : No`. That is first-party evidence from the tool doing
the read — the standard the test was defending — so the row is now filled on this drive.

The distinction the parser keeps, and that matters: cyanrip's line reports what the
**drive can do**, not what the rip did. "unsupported" *proves* C2 was not used; a
"supported" line would prove only that it was available, and EAC's row asks whether C2
was *used*. So a C2-capable drive still yields "(not reported)" rather than a guess in
either direction. The row is met where the hardware settles it, open where it doesn't.

---

### Pregap detection — a real archival gap, now visible in the log (found 2026-07-30)

Comparing the committed real EAC 1.8 log against the cyanrip log **of the same disc in
the same drive** shows something neither log's wording had made obvious:

| | EAC 1.8 | cyanrip 0.9.3 |
|---|---|---|
| `Gap handling` | `Appended to previous track` | `Gaps: None signalled` |
| Per-track `Pre-gap length` | present for **10 of 14** tracks (1, 2, 4, 5, 7, 8, 9, 10, 13, 14) | none |

**EAC detects pregaps that cyanrip does not.** (Ten of the fourteen; tracks 3, 6, 11 and 12 have none in EAC's log either. The committed baseline is **two concatenated EAC runs**, so a whole-file `grep -c` doubles every count — 20 pregap lines, not 20 pregaps.) EAC runs its own gap-detection pass;
cyanrip reports what the disc's TOC signalled, and on this disc the TOC signalled
nothing. Both tools then *append* the gap to the previous track, so **the audio is
unaffected** — this is a completeness gap in the archival record, not a correctness one.

It is the same capability gap as KDD-32 / the `INDEX 00` work, and it is the reason the
run sheet's cyanrip-`master` build step exists.

Until 2026-07-30 our exported row echoed cyanrip's "None signalled", which hid the
comparison entirely. It now reads EAC's own phrase for the not-detected case, so a
side-by-side diff against a real EAC log shows the difference instead of burying it —
and `test_gap_row_vocabulary_comes_from_a_real_eac_log_not_from_us` pins the
disagreement so nobody later "fixes" it by making the string match.

---

## 4. Ranked next steps, cheapest first

1. **Earn the C2 row** — read libcdio-paranoia's source for C2 handling, or measure it,
   then assert `No` with the evidence recorded next to the assertion. ~10 lines once the
   evidence exists; the point is the evidence, not the lines.
2. **`Fill up missing offset samples with silence`** — plumb `force_overread` into the
   renderer, which currently only sees parsed log text. ~30 lines.
3. **Assert the offset is *correct*, not merely applied** — the AccurateRip drive table
   is already in `adapters/accuraterip_offsets_data.py`, so the log can say
   `+667 (matches the AccurateRip database for PIONEER BD-RW BDR-209D)`. Genuine
   archival value: it turns a number into a checkable claim. ~40 lines.
4. **Investigate accurate-stream** — check whether `cd-paranoia -A` output carries a
   usable signal. May be a dead end; investigation before code.
5. **Do NOT build a whipper-format emitter.** It is the only technically-passing route,
   and it is the same forgery as EAC-signing: whipper did not do the rip.

---

## 5. The honest framing

A 100% logchecker score certifies **process and provenance** — that a known program,
configured a known way, produced this log. It explicitly does not certify bit-perfect
audio; OPS's own README concedes that a sub-100% log can still be a perfect rip.

Platterpus makes a *different and narrower* claim, and it is a stronger one about the
audio itself: **provably bit-perfect, verified openly** via AccurateRip v1/v2 + CTDB
CRCs and per-track Copy-CRC parity against the committed EAC baseline in
`output_reference/EAC_flac/` (currently 12/14 for cyanrip FLAC, with the two
mismatches attributable to the disc, tracked in the hardware runs).

That is the goal to keep. "Tracker-acceptable" is not reachable and should not be
chased.

### One correction to our own docs

`docs/eac-log-and-repair-feasibility.md` says whipper "still cannot clear RED's
checksum requirement." OPS's checker **does** validate whipper's plain SHA-256, so the
checksum wall is cleared there. The accurate statement is that *Redacted's rules* list
only EAC and XLD — a policy limit, not a technical one.

---

*Sources:* [OPSnet/Logchecker](https://github.com/OPSnet/Logchecker) ·
[ligh7s/hey-bro-check-log](https://github.com/ligh7s/hey-bro-check-log) ·
[OPSnet/eac_logchecker.py](https://github.com/OPSnet/eac_logchecker.py) ·
[puddly/eac_logsigner](https://github.com/puddly/eac_logsigner) ·
[interviewfor.red rules](https://interviewfor.red/en/rules.html) ·
[interviewfor.red ripping](https://interviewfor.red/en/ripping.html) ·
[eacguide.github.io](https://eacguide.github.io/) ·
[arg274/cambia](https://github.com/arg274/cambia)

*Last updated for Platterpus v0.6.1.*
