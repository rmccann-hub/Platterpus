SUPERSEDED-BY: EAC-PARITY-PLAN-OF-RECORD-2026-10-26.md (https://claude.ai/artifact/ACChXwKyAGM9wvCTVjqDDo). Do not send this file.
REPORT-FOR: Platterpus session and cyanrip fork session
FROM: the claude-code-skills session, for the owner to pass on once, to both sessions
WRITTEN: 2026-10-26 02:30 UTC (the evening of 2026-10-25 in New York)
EXPIRES: 2026-12-31. Re-read the logchecker before relying on it after that.
SUBJECT: the default rip: what a clean tracker rip in EAC takes, and Platterpus's default
measured against it

# The default rip

## The owner's words, verbatim

Said to the claude-code-skills session on 2026-10-26, about 02:05 UTC:

> "lets start with making the default for us, what we need to do for eac for a proper clean rip
> for a good tracker. you can do something else if you want. and i want our rips to be as good
> or better (better)"

So this file does two things:
- **Section 1** sets out what a clean EAC rip for a good tracker takes. It's also how the owner's
  own EAC rips are set up.
- **Section 2** measures Platterpus's default against each item, and says what's left to be
  better.

## Where the rules come from

- **What trackers score:** OPS's logchecker, the open-source code trackers run, read at
  `OPSnet/Logchecker@ca56547` (2026-05-31, still the newest commit on 2026-10-26). Line numbers
  below are in its `src/Logchecker.php`. It's the same commit Platterpus's
  `docs/eac-parity.md` Part D read. Where Part D's figures differ, they came from
  `hey-bro-check-log`, unmaintained since 2020. The figures below are OPS's own.
- **How EAC is set up to meet it:** [eacguide.github.io](https://eacguide.github.io/), dated by
  its repository to 2017-12-26, and checked against the logchecker.
- **Redacted's ripping page** ([interviewfor.red](https://interviewfor.red/en/ripping.html))
  says only to use EAC or XLD set up by its wiki, and never to edit a log. Its wiki needs a
  login, so it isn't read here.

A logchecker scores the setup and what the log says, not whether the audio is right. OPS's
README says so itself (Part D §5). Correctness is AccurateRip and CTDB.

## 1. A clean EAC rip for a good tracker

### The settings, with what the logchecker takes off for each

| EAC setting | Set it to | Points off otherwise | Where |
|---|---|---|---|
| EAC version | 1.8, from exactaudiocopy.de | 30 below 0.99 | `:485` |
| Read mode | Secure | 20 | `:1512` |
| Utilize accurate stream | Yes | 20, and 20 if the line is missing | `:1734`, `:640` |
| Defeat audio cache | Yes | 10 | `:1757` |
| Make use of C2 pointers | No | 10 | `:1790` |
| Read offset correction | The drive's value from AccurateRip's list (+667 for the BDR-209D) | 5 | `:1818` |
| Fill up missing offset samples with silence | Yes | 5 | `:1841` |
| Delete leading and trailing silent blocks | No | 5 | `:1851` |
| Null samples used in CRC calculations | Yes | 5 | `:1865` |
| Normalize | Off | 100: the log fails | `:1873` |
| Gap handling | Appended to previous track, **after running Detect Gaps** | 10, and 10 for "Not detected" | `:1882` to `:1888` |
| Add ID3 tag | No, for FLAC | 1 | `:1920` |
| Test & Copy | On, every track | 10 if not used | `:1351` |
| A range rip | Never; rip tracks | 30 | `:990` |
| A virtual or null drive | Never | 20 | `:1554`, `:1558` |
| Overread into lead-in and lead-out | Off on this drive | Not scored | Part D §2 |

### What the rip itself must show, per track

| In the log | Points off |
|---|---|
| Test CRC differs from Copy CRC | 30 per track (`:1939`) |
| A suspicious position | 20 per track (`:1243`) |
| A timing problem | 20 per track (`:1263`) |
| Missing samples | 20 per track (`:1273`) |
| Copy aborted | 100 (`:1284`) |

AccurateRip's results are shown in colour but take no points at OPS (`:886` to `:908`). The
log's checksum is reported beside the score, not deducted from it (`:413` to `:433`, `:562`).
A tracker reads both.

### The steps in EAC, in order

1. **Drive options:** Secure mode, accurate stream, defeat audio cache, C2 off.
2. **Offset:** from AccurateRip's list, confirmed with a key disc; overread off.
3. **Plugins:** AccurateRip on and the CTDB plugin installed. Leave the GD3, metadata and
   AcoustID plugins off.
4. **Compression:** FLAC `-8 -V`, no ID3 tag, no normalising.
5. **Per disc:**
   1. Run **Detect Gaps**.
   2. Create a **cue sheet** with gaps ("Multiple WAV Files With Gaps (Noncompliant)").
   3. Run **Test & Copy** on all tracks, to compressed files.
6. **Save the log unedited,** in English, beside the files. Never edit it.

The EAC baseline sessions on the Police disc already had Test & Copy, secure mode, accurate
stream, cache defeat, C2 off and +667 (`platterpus@bba81563:output_reference/EAC_*/`).

## 2. Platterpus's default, measured against it

The default is the **Fast Verified** goal (`config.py:417`):
- read every track once at speed;
- re-read with `-Z 2` only the tracks AccurateRip doesn't verify, until three reads agree;
- read every track twice when AccurateRip can't vouch for the disc.

### Where the default already meets the bar or beats it

| The tracker's bar | Platterpus's default | Grade |
|---|---|---|
| Secure mode | libcdio-paranoia in full mode, every read | Equal |
| Defeat audio cache | Measured per drive, not asserted (KDD-29) | Equal where measured |
| C2 off | Not used; the log says so where the drive reports C2 unsupported | Equal |
| The offset from AccurateRip's list | Applied, checked against the list, and re-confirmed by every rip that matches | Better: EAC only prints the number |
| No silent blocks deleted; null samples in the CRC; no normalising; no ID3 in FLAC; no range rips | All hold (Part D §3) | Equal |
| Gaps appended to the previous track, detected | The fork reads pregaps from the sub-channel and matches EAC's ten pregap rows in 23 of 26 rips | Equal, except track 9's pregap on `.26` |
| FLAC `-8 -V` | Maximum compression, then `flac --test` and SHA-256 on every finished file | Better |
| AccurateRip and CTDB | Both on by default; CTDB per track and across offsets, matches weighed | Equal, behind on locating bad samples |
| Test & Copy on every track | **Different:** a track AccurateRip verifies is read once; any other is read until reads agree | See the question below |
| A failed track | Re-read automatically until AccurateRip verifies one read (the chase) | Better: EAC leaves it to the user |
| The disc's ISRCs | Read from the disc and preferred (`prefer_disc_isrc`, on by default) | Equal, proven on `.26` |
| A log anyone can check | Our own log plus an EAC-layout log (off by default), with an open SHA-256 | Better on openness; no tracker accepts it, by design (KDD-24) |

### What's left, before the default can be called better

In order. The first five come from the four Full runs and the EAC parity check sent the same
day.

1. **Truthful wording, Platterpus (R1 to R3).** A logchecker treats "Copy OK" as the good state
   (`:1450`). Our log printed it, and "confirmed across 3 secure re-reads", over 5 wrong tracks.
   EAC does the same. Saying "wrong" instead is the clearest place we beat EAC.
2. **`.26`'s speed against track 3, the fork first (C1).** A default must not read a hard track
   worse than the build before it.
3. **Ship a right read when one exists, and keep it through a cancel, Platterpus (C2, C3).**
4. **Error positions, the fork then Platterpus (TASKS R44).** A logchecker takes 20 points per
   track with a suspicious position, so EAC users see them. Ours records counts only in released
   builds.
5. **A time bound on a damaged disc, Platterpus (C4).**
6. **Accurate stream, the fork.** It's 20 points in a logchecker, and nothing in our log answers
   it (Part D §3). Say whether the drive reports it, or whether `cd-paranoia -A` can measure it.
7. **Cache defeat measured without asking the user, Platterpus.** Today it's measured when the
   user runs Analyse cache. Run it once per drive in setup, so the default rip always has an
   answer.
8. **What `-r 5` means beside EAC's retries, the fork.** EAC reads a bad sector up to 82 times.
   cyanrip's `-r` is per frame and also caps whole-track reads. Say whether 5 is comparable, and
   whether a damaged disc wants more.

### The one question for the owner

**Should the default read every track at least twice, as EAC's Test & Copy does?**

- **Today, Fast Verified:** a track AccurateRip verifies is read once. That's a stronger proof
  than two agreeing reads: AccurateRip compares our bytes with other people's rips, and two
  reads only show the drive gave the same bytes twice. Track 5 of the Police disc agreed
  wrongly in every EAC session.
- **Archival Exact,** already in Settings, reads every track until three reads agree. It roughly
  doubles the rip time on a clean disc. What it adds is a second read on tracks AccurateRip
  already verified.

**The recommendation is to keep Fast Verified as the default.** It meets Test & Copy's bar
wherever AccurateRip can't vouch, and beats it where AccurateRip can. The log should say, per
track, which proof it has: verified by AccurateRip at confidence N, or reads agree. That's the
change to make, in R1's wording work.

## 3. What each session is asked for

Each names one writer for each item it takes, in its next lap:
- **The fork:** items 2, 4, 6 and 8 of section 2.
- **Platterpus:** items 1, 3, 5 and 7, and the per-track proof line.

**Waits on the owner:**
- the answer to the question above;
- EAC rips of the damaged disc and disc 3, set up by section 1.
