REPORT-FOR: Platterpus session and cyanrip fork session
FROM: the claude-code-skills session, sent once to both by the owner, as a link
WRITTEN: 2026-10-26 02:30 UTC (the evening of 2026-10-25 in New York)
EXPIRES: 2026-12-31. Re-check EAC's version, the logchecker and the sources after that.
SUPERSEDES: four files sent on 2026-10-26: `report-for-both-sessions-2026-10-26-four-full-runs.md`,
`for-both-sessions-2026-10-26-eac-parity-independent-check.md`,
`for-both-sessions-2026-10-26-what-made-eac-good.md` and
`for-both-sessions-2026-10-26-default-rip.md`, and holds all of them, with the three per-run
findings files word for word in Appendices G to I. Where they differ, this file holds.
UPDATED: 2026-10-26 02:36 UTC, adding section 9 on the owner's word of that hour; 2026-10-26 02:50 UTC, correcting section 4's count
HOME: Platterpus's `docs/eac-parity.md` Part F holds this plan from `platterpus@f54348e1`, with its items as TASKS R49 to R66. Once that reaches Platterpus's `main`, this file is retired: corrections go there. Section 9 came after Part F was written, so it's still to be taken in.
READS: `platterpus@59f4e331` (`claude/session-omka9f`) and `cyanrip@5af8493` (round 36 lap 8),
both fetched 2026-10-26 02:05 UTC

# EAC parity: the plan of record

**Contents:**
- **The plan:**
  1. The owner's words
  2. The yardstick
  3. The research and data to use
  4. Where we stand, on evidence
  5. Every regard, EAC against us
  6. A clean EAC rip, as a tracker scores it, and our default against it
  7. Documentation to update
  8. What each session is asked for, and what waits on the owner
  9. Clean inputs, clean outputs, clean updates
- **Appendices:**
  - A. What made EAC trusted
  - B. Which EAC to run
  - C. eacguide.github.io
  - D. Corrections made along the way
  - E. The old report's IDs mapped to rows, the test harness and the timed rip
  - F. Terms
  - G. Run 1 findings: the reference disc, 2026-10-21
  - H. Run 2 findings: the damaged disc, 2026-10-21
  - I. Runs 3 and 4 findings: discs 3 and 4, 2026-10-22

## 1. The owner's words, verbatim

Said to the claude-code-skills session on 2026-10-25 and 26 (UTC), newest first:

> "this must be everting, all ecompasing."

> "update all, i want you to give me a file for both repos, i want all to look at the right
> research and data and move forward here. my goal is to be better or at best equal, to eac, in
> all regards.so do this, or tell me why its not possible, and update all documentation."

> "lets start with making the default for us, what we need to do for eac for a proper clean rip
> for a good tracker. you can do something else if you want. and i want our rips to be as good
> or better (better)"

> "yes and we want to focus on what made it good and universally liked. and make ours the same
> for linux, and porting to windows might be a way longer goal"

> "look, for this, both reops, they need to rip and be correrct, reporting on files is good, but
> ripping ir the goal. we need to report on that accuractly to confirm, that is what we do."

**What this asks of both sessions:**
1. Read the research and data in section 3, and work from them.
2. For every row of section 5, reach equal or better than EAC, or record why it can't be done.
3. Make the documentation changes in section 7.
4. Answer in your next lap, with one writer named for each item you take.

## 2. The yardstick

- **A rip is right** when AccurateRip verifies the track's whole checksum at high confidence, or
  CTDB's strongest entry agrees with it.
- **A rip is wrong** when the frame-450 checksum matches AccurateRip and the whole track doesn't.
  The frame match proves the pressing, so a whole-track mismatch means the audio differs.
- **Every track scores one of three ways:**
  - right;
  - wrong but reported;
  - **wrong and reported as fine.** This is the worst, and the one to drive to zero.
- **A tracker's logchecker is a different test.** It scores how the ripper was set up and what
  the log says, not whether the audio is right. OPS's own README says a log below 100 can be a
  perfect rip.
- **EAC's own words don't decide correctness either.** "Copy OK" means EAC saw no read error, and
  users see it over tracks AccurateRip rejects.

## 3. The research and data to use

### Sources outside both repositories, each fetched or read on 2026-10-26

| Source | What it settles |
|---|---|
| [EAC: Extraction Technology](https://exactaudiocopy.de/extraction-technology/) | Secure mode reads each sector at least twice, or uses C2; a bad sector is read until 8 of 16 agree, up to 82 reads. It names suspicious positions. Test & Copy is a separate mode |
| [EAC: What's new](https://www.exactaudiocopy.de/whats-new/) | 1.8, 14 July 2024, is current. No secure-mode change is listed after 1.0 beta 3. A crash on read errors was fixed on 2015-04-09. GD3, a paid metadata plugin, has shipped since May 2011 |
| [EAC's home page](https://www.exactaudiocopy.de/) | What EAC claims: "multi-reading with verify and AccurateRip", and it "will tell you on which time position the (possible) distortion occurred" |
| [AccurateRip](http://www.accuraterip.com/) | How it verifies; confidence is the count of matching submissions |
| [CUETools Database wiki](https://cue.tools/wiki/CTDB), edited 21 March 2026 | Whole-disc CRC and recovery record. It repairs one damaged stretch of about 30 to 40 sectors |
| [dBpoweramp: Secure Ripper Test](https://dbpoweramp.com/secure-ripper.htm) | The only published damaged-disc comparison: a vendor testing its own product, EAC 0.95b4, one disc. dBpoweramp got 64 tracks right to EAC's 53 |
| [Hydrogenaudio forum](https://hydrogenaudio.org/index.php?msg=484968) | "Copy OK" over tracks AccurateRip rejects |
| [OPSnet/Logchecker](https://github.com/OPSnet/Logchecker) at `ca56547` (2026-05-31, newest on 2026-10-26) | What a tracker scores, line by line, in section 6 |
| [eacguide.github.io](https://eacguide.github.io/), repository dated 2017-12-26 | How the community sets EAC up for 1.0 beta 3. **A setup guide, not an authority:** its claim that "the only possible errors would be with the CD itself" is contradicted by section 4 |

**Not to rely on:**
- the figures in `hey-bro-check-log`, unmaintained since 2020-03-31. Platterpus's Part D table
  took several from it; section 6 has OPS's;
- my earlier advice to step the speed down for track 3. The fork's lap 8 S8 refutes it, as
  section 4 says;
- any claim, mine included, that the EAC baseline ran without Test & Copy. Every track in its
  three logs has a Test CRC.

### Data, each with where it lives

| Data | Where |
|---|---|
| Three EAC 1.8 sessions on the reference disc: Test & Copy, secure mode, accurate stream, cache defeat, C2 off, +667 | `platterpus@bba81563:output_reference/EAC_flac/`, `EAC_mp3/`, `EAC_wav/` |
| 26 Platterpus rips of the reference disc, 2026-08-04 to 10-16 | Platterpus's `evidence` branch; scored in `docs/eac-parity.md` Part E2 |
| The four Full runs of `.26` with 0.7.112, 2026-10-21 and 22 | `cyanrip@c65b7b9`, `0c8e6bd`, `f3be312`, `c917bf6` (evidence); Platterpus's `evidence` at `6b31795c`; read by the fork in `cyanrip@5af8493:docs/handshake/round-36-lap-08.md` |
| The track-by-track scoring of those runs | Section 4, from the bundles' `.platterpus.json` records and EAC-layout logs |
| The pinned drive | Pioneer BDR-209D, firmware 1.51, +667, `Speed: default (unchangeable)` |

## 4. Where we stand, on evidence

### Is the audio right? The four Full runs, every track written

| Disc | Right | Wrong | What happened |
|---|---|---|---|
| *Roots Music* disc 4 | all | 0 | Every rip, both builds |
| *Roots Music* disc 3 | all but 1 | 1 | Track 16 is damaged. The main rip's read was wrong; the chase's fifth read verified and shipped. **Final: 16 of 16** |
| The Police (reference) | 39 | 5 | Track 3 wrong in `.26`'s timed rips and secure re-rip; track 5 wrong, its right value never read. **Final main rip: 13 of 14** |
| *Roots Music* disc 1 (damaged) | 10 | 8 | Tracks 11 to 18. The run hit its 6-hour limit in the securing pass; a re-read of track 11 that verified was thrown away by the cancel |

**164 of 178 tracks written were right; 14 were wrong.** Counted: every track of every rip that wrote a `.platterpus.json` report, plus the six one-track de-emphasis rips (`album/r16deemphon` and `r16deemphoff` in the reference run and in discs 3 and 4), which wrote only a cyanrip log and all verified. The first version of this file left those six out and said 158 of 172.

### Did we say so truthfully?

- **Every "Bit-perfect" verdict was true.** No wrong track was ever called verified.
- **But wrong tracks were reported as fine, in the log a user reads:**
  - 5 carried "Copy OK";
  - 3 of those 5 also carried "confirmed across 3 secure re-reads";
  - on the damaged disc, tracks 11, 12, 14 and 16 printed `read successfully!` and failed
    AccurateRip (the fork's lap 8 S9).

  This is the worst outcome, and EAC does the same.

### Against EAC, on the one disc both have ripped in the same drive

| | EAC 1.8, 3 sessions | Platterpus |
|---|---|---|
| Tracks right per rip | 13, 11 and 12 of 14 | 12 or 13 in 26 rips; 13 on 2026-10-21 |
| Track 3 | right in 1 of 3 | right in 9 of 26 earlier rips. `.25` right 2 of 2 on 2026-10-21, but wrong at 0.96× on 2026-10-20. `.26` right at 0.99× in the securing pass, wrong at 0.74× in the secure re-rip |
| Track 5 | never right; Test & Copy agreed on the wrong value every time | right once (2026-10-07) |
| Track 4 | wrong once | right 26 of 26 |

**What this shows:**
- **On this disc and drive, we are equal to EAC.**
- **Track 3 is marginal on this drive whatever the build or speed.** The fork's lap 8 S8: "Two
  rips a side cannot separate the build from the disc." Speed is not shown to be the cause, so
  stepping the speed down is not the fix. This drive doesn't take a speed setting anyway.
- **Track 5 is a systematic misread.** The drive returns the same wrong bytes to both programs.
  No software beats it on this drive except by luck; another drive can.

### What the fork's lap 8 found in `.26`

| What | Their reading |
|---|---|
| The disc's ISRCs | **Working:** 14 of 14 on the reference disc match EAC's cue |
| Accurate stream | The drive's declaration is read: "declared supported by drive (capabilities page, not measured)", 38 of 38 logs |
| `Recordable:` | **Broken:** libcdio's placeholder `0xffff` is printed as the drive's answer. Blocking (S4) |
| Track 9's pregap | **Never 94,** where `.25` and EAC read 94: 95 in 3 logs, unknown in 5. Blocking (S5) |
| Damaged disc | First skips on a build from `.20`, all placed in the record |

Round 36 is on hold for the owner's word (S15). The fork recommends both fixes in `.27`, then a
Full run of the reference disc.

## 5. Every regard, EAC against us

**Grades:**
- **Better** and **Equal** are the goal reached.
- **Behind** means it can be reached, and the action says how.
- **Not possible** means it can't, and the reason is given.

| # | Regard | EAC | Us today | Grade | To reach equal or better | Whose |
|---|---|---|---|---|---|---|
| 1 | Reading the audio right | 12.0 of 14 a rip, one disc | 12.4 of 14, one disc | Equal | Rows 2 to 6, then more discs and drives (row 29) | Both |
| 2 | Keeping a right read once found | Keeps its Test/Copy pair whatever AccurateRip says | The chase keeps the read that verifies, but `-Z` shipped a wrong read over a right one, and a cancel threw a right one away | Behind | Ship any read that verifies, whichever path read it; keep finished tracks through a cancel | Platterpus |
| 3 | Re-reading a failed track | Leaves it to the user | Automatic, until a read verifies | Better | Keep | — |
| 4 | A disc AccurateRip doesn't know | Test & Copy on every track | Every track read until reads agree, from 0.7.111 | Equal | Rip one such disc end to end on the drive | Owner's disc |
| 5 | A damaged disc | Reads a bad sector up to 82 times, then flags it | Track 18 took 5 h 18 min; no time bound | Behind | A per-track time budget; record a track whose every read skips as unreadable on this drive, with positions. Say what `-r 5` means beside EAC's 82 | Platterpus; the fork for `-r` |
| 6 | Track 3 on this drive | Right 1 in 3 | Right in some rips, both builds | Equal | Pair `.25` and `.26` over more rips before naming a cause; the chase is the fix that works | The fork |
| 7 | Track 5 on this drive | Never | Once | **Not possible** on this drive | The drive returns the same wrong bytes to every program. Another drive can | — |
| 8 | Saying a wrong track is wrong | "Copy OK" over it | "Copy OK", "confirmed across 3 secure re-reads", "read successfully!" | Equal, both bad | Say "wrong" where the frame-450 match proves the pressing; never print either phrase over a track AccurateRip contradicts; the per-track status gives the outcome | Platterpus; the fork for `read successfully!` |
| 9 | The proof each track has | Test & Copy CRCs | AccurateRip at confidence N, or reads agree | Better once shown | One line per track naming which proof it has | Platterpus |
| 10 | Where a read was unsure | Suspicious positions | Counts in released builds; positions in `.25`'s record, not yet in the log | Behind | Agree the log wording (R44) and print them | Both |
| 11 | CTDB check | Per track; names the bad samples | Per track and across offsets, matches weighed (R43, R34) | Behind on naming samples | The syndrome pass (R43), on the owner's word on `numpy` or a native extension | Platterpus |
| 12 | CTDB repair | Not in EAC; CUETools does it | Deferred (KDD-14) | Equal | Building it would be better than EAC | Platterpus, later |
| 13 | CTDB submission | Yes | Not built | Behind | Build it. Never submit a track AccurateRip rejects, which EAC did with track 5 | Platterpus |
| 14 | AccurateRip submission | Yes | None | Behind, may be **not possible** | Part E calls it impossible from Linux, with no source. Find out whether AccurateRip accepts submissions from programs it hasn't approved. If it doesn't, it's not ours to change | Platterpus to cite or check |
| 15 | Secure reading | Secure mode | libcdio-paranoia, full mode | Equal | — | — |
| 16 | Accurate stream | Setting, logged | The drive's declaration read and shown, "not measured" (`platterpus@59f4e331`) | Equal on what can be known | Say whether paranoia's read path depends on it; if so, refuse a drive that declares it unsupported | The fork |
| 17 | Cache defeat | Setting, logged | Measured when the user runs Analyse cache | Behind on the default | Measure once per drive in setup | Platterpus |
| 18 | C2 | Off by the guides | Not used; logged where the drive reports | Equal | — | — |
| 19 | Read offset | Set by the user | From AccurateRip's list, checked every rip | Better | — | — |
| 20 | Read speed | "Allow speed reduction" | This drive takes no speed setting; the ladder re-reads | Equal on this drive | Test on a drive that takes `-S` | Owner's hardware |
| 21 | Pregaps and gaps | Detect Gaps; appended to the previous track | Matches EAC in 23 of 26 rips; `.26` never reads track 9 as 94 | Behind on `.26` | Lap 8 S5's record, then the fix in `.27` | The fork |
| 22 | The disc's ISRCs | Read for the cue | `.26` reads them, 14 of 14 matching EAC | Equal | Platterpus's cue check compares with the code it sent; compare with the disc's (lap 8 S10) | Platterpus |
| 23 | CD-R detection | — | `.26`'s `Recordable:` prints a placeholder | Behind | Lap 8 S4's fix in `.27` | The fork |
| 24 | Pre-emphasis | Kept, flagged | Kept, `FLAGS PRE` | Equal, untested | Rip a pre-emphasised disc | Owner's disc |
| 25 | HTOA, image + cue, data tracks | Supported | Not, or copied by default (R12) | Behind | Build them; HTOA and image + cue low, as Part E7 has them | Both |
| 26 | Checking the finished files | `flac -V` at encode | `flac --test` after tagging, SHA-256, derived formats checked | Better | — | — |
| 27 | A tracker accepting the log | Accepted by name | Refused by name, before any setting is read | **Not possible** by our own work | The checkers allow-list rippers. Copying EAC's identity is forgery, refused under KDD-24. The honest route is to ask OPS to add Platterpus, as it added whipper. That's OPS's decision, not ours | — |
| 28 | A log anyone can check | Closed, obfuscated signature | Open SHA-256 over our own log | Better on openness | Keep our own log the goal (KDD-36) | — |
| 29 | Breadth of proof | Twenty years, thousands of drives | One drive, one machine | **Not possible** to equal soon | Time cannot be skipped. Narrow it with a second drive, machine and distro (the 0.8.1 gate) | Owner's hardware |
| 30 | Setup | Needs a guide | Settings chosen for the user | Better | — | — |
| 31 | Openness, cost, extras | Closed source, freeware, paid plugin | Open source, free, nothing bundled | Better | — | — |
| 32 | Platform | Windows | Linux | Equal for Linux users | A Windows build is the owner's long-term goal; no work now. Note what blocks it when working near it | Both, later |
| 33 | A drive blip mid-rip | — | One "tray open" blip cleared the app's disc view and cost 57 steps | Behind | Confirm a removal before acting on it | Platterpus |
| 34 | Speed of a clean rip | 1.6× to 9.1× with Test & Copy | `.26` is 2.8× to 5.1× faster than `.25` | No data against EAC | Time one EAC rip and one Platterpus rip of the same disc | Owner, at the drive |

## 6. A clean EAC rip, as a tracker scores it, and our default against it

### What OPS's logchecker takes off, at `ca56547` (`src/Logchecker.php`)

| EAC setting | Set to | Points off otherwise |
|---|---|---|
| Version | 1.8, from exactaudiocopy.de | 30 below 0.99 (`:485`) |
| Read mode | Secure | 20 (`:1512`) |
| Utilize accurate stream | Yes | 20, and 20 if the line is missing (`:1734`, `:640`) |
| Defeat audio cache | Yes | 10 (`:1757`) |
| Make use of C2 pointers | No | 10 (`:1790`) |
| Read offset correction | The drive's AccurateRip value | 5 (`:1818`) |
| Fill up missing offset samples with silence | Yes | 5 (`:1841`) |
| Delete leading and trailing silent blocks | No | 5 (`:1851`) |
| Null samples used in CRC calculations | Yes | 5 (`:1865`) |
| Normalize | Off | 100 (`:1873`) |
| Gap handling | Appended to previous track, after Detect Gaps | 10, and 10 for "Not detected" (`:1882` to `:1888`) |
| Add ID3 tag | No | 1 (`:1920`) |
| Test & Copy | On | 10 (`:1351`) |
| Range rip | Never | 30 (`:990`) |
| Virtual or null drive | Never | 20 (`:1554`, `:1558`) |

**What it takes off per track:**

| In the log | Points off |
|---|---|
| Test CRC differs from Copy CRC | 30 (`:1939`) |
| A suspicious position | 20 (`:1243`) |
| A timing problem | 20 (`:1263`) |
| Missing samples | 20 (`:1273`) |
| Copy aborted | 100 (`:1284`) |

AccurateRip's results take no points (`:886` to `:908`). The checksum is reported beside the
score, not deducted (`:413` to `:433`, `:562`).

### The steps in EAC, for the owner's EAC rips

1. **Drive options:** Secure mode, accurate stream, defeat audio cache, C2 off.
2. **Offset:** from AccurateRip's list (+667); overread off.
3. **Plugins:** AccurateRip on and the CTDB plugin installed. Leave GD3, the other metadata
   plugins and AcoustID off.
4. **Compression:** FLAC `-8 -V`, no ID3 tag, no normalising.
5. **Per disc:**
   1. Run Detect Gaps.
   2. Create a cue sheet with gaps.
   3. Run Test & Copy on all tracks, to compressed files.
6. **The log:** save it unedited, in English.

### Our default, Fast Verified, against that bar

- **Already meets the bar or beats it:** secure reads, C2, offset, gaps (except `.26`'s track 9),
  ISRCs, no silent-block deletion, null samples, no normalising, no ID3 tag, per-track rips,
  AccurateRip and CTDB.
- **Meets it differently:** Test & Copy.
  - A track AccurateRip verifies is read once. That's stronger proof than two reads agreeing.
  - Any other track is read until reads agree.
  - **The recommendation is to keep this as the default and print each track's proof**
    (row 9). Archival Exact, already in Settings, reads every track twice for anyone who wants
    EAC's Test & Copy exactly.
  - **Waits on the owner's word.**
- **Behind:** rows 10 (positions), 16 (accurate stream) and 17 (cache defeat).

## 7. Documentation to update

Each session changes its own files. These sessions' records are append-only where their own
rules say so; correct those with a dated note, not by rewriting the entry.

### Platterpus, at `bba81563` unless named

| Where | Change |
|---|---|
| `PLANNING.md:1359`, KDD-30 | Secure mode doesn't do a Test pass and a Copy pass. Test & Copy is a separate mode. `-Z` gives Test & Copy's guarantee, not secure mode's sector checks |
| `docs/archive/upstream-modification-investigation.md:213` | "EAC can use the drive's C2 pointers, when switched on" |
| `CHANGELOG.md:39` (0.7.112) | A dated correction: EAC repeats a sector until 8 of 16 reads agree, and otherwise flags it; it doesn't keep a majority per track |
| `docs/eac-parity.md:1116` and `:1284` | Cite where "AccurateRip submission is impossible from Linux" was established, or mark it unverified (row 14) |
| `README.md:181` | Cite how EAC's speed reduction works, or drop "per-sector" |
| `docs/eac-parity.md` Part D §2 | Replace the deductions with OPS's (section 6): C2 is 10, null samples 5, Test & Copy 10, "Not detected" gaps 10, AccurateRip 0, the checksum reported not deducted. Name `hey-bro-check-log` as unmaintained |
| `docs/eac-parity.md` Part E1 to E7 | Add this file's rows that Part E lacks (2, 5, 8, 9, 13, 14, 23, 33, 34). Re-grade row 16 from `59f4e331`. Add the fork's lap 8 S8 to E2's track-3 reading |
| `docs/eac-parity.md`, a new short section | The yardstick in section 2, and the per-run scoring, kept with each Full run's reading |
| `TASKS.md` | One row per Platterpus item in section 5, each pointing here |

### The cyanrip fork

| Where | Change |
|---|---|
| `.26`'s Changelog | Already corrected in lap 8 S14 |
| The filed READMEs of the four runs | Already corrected in lap 8 S13 |
| Any document that ties `7dbe56a` to track 3's misreads | Your lap 8 S8 names no cause. Keep it that way until paired rips separate the build from the disc |
| Your own record of the EAC comparison, if you keep one | Rows 5, 6, 10, 16, 21 and 23 of section 5 are yours |

### claude-code-skills

Nothing in that repository covers ripping. The four files this one supersedes were never
committed there.

## 8. What each session is asked for, and what waits on the owner

**The fork**, by row:
- 21 and 23: `.27` with lap 8's fixes;
- 6: paired rips before naming a cause;
- 10: positions in the log, with the wording agreed;
- 16: whether paranoia's path depends on accurate stream;
- 5: what `-r` means beside EAC's 82 reads;
- 8: `read successfully!` over a track the rip can't vouch for;
- section 9: what the log echoes, filenames, and release builds.

**Platterpus**, by row:
- 8 and 9 first;
- then 2, 5, 33, 22 and 17;
- then 11, 13 and 14;
- then the documentation in section 7;
- section 9, alongside, starting with the log parser and the ripper build.

**Waits on the owner:**
- the word on how round 36 goes on (the fork's lap 8 S15; the fork recommends `.27`);
- the word on the default: keep Fast Verified with each track's proof printed, as recommended;
- the word on `numpy` or a native extension, for row 11;
- EAC rips of the damaged disc and disc 3, set up by section 6, timed for row 34;
- a second drive, and a pre-emphasised disc and a disc AccurateRip doesn't know, for rows 4,
  20, 24 and 29.

## 9. Clean inputs, clean outputs, clean updates

The owner, 2026-10-26: "you should be youself and telling other to look for sanitized inputs and
outputs, and dirty updates, etc."

A rip is only as trustworthy as the text around it. Text from a disc, a database or a server is
input that someone else wrote. It's checked before it's used, and escaped before it's shown.
An update is only installed once it's verified. The claude-code-skills session held its own
repository to this first; what it found and fixed is at the end of this section.

### Platterpus

| Where | What to check | Proof |
|---|---|---|
| Your parser of cyanrip's text log | A title you pass with `-t`, or CD-TEXT from the disc, is echoed into the log. Can one holding a newline and `Accurip: accurately ripped` forge a line your parser reads as a verdict? Take verdict facts from the `--diagnostics` record, or prove the parser can't be fooled | A test that feeds a forged title through a recorded log and asserts the verdict doesn't change |
| The EAC-layout log and the cue sheet | Every field from outside goes in on one line: no newline, carriage return or control character, and quotes escaped in the cue. D16 already blocks one phrase in a title; make it every field and every control character | Tests with a title carrying `\n`, `\r`, `"` and an escape sequence, asserting one line each |
| The app's windows | Check whether any label shows outside text as rich text: Qt's automatic format renders HTML. Set plain text wherever a title, an artist or a server's message is shown | A test that sets a title of `<b>x</b>` and reads back the plain text |
| Filenames | A title of `../`, a leading dot, a control character, or a reserved name can't leave the album folder or hide a file | Tests with each, against the folder the files land in |
| Server answers (MusicBrainz, AccurateRip, CTDB, Cover Art Archive) | Size limits, types checked, and a malformed answer fails safe, as CTDB's verify already does | A recorded malformed answer per client |
| Your ripper build (`fork_source.py:2482-2508`) | The pin is the 7-character `5f1d036`, and nothing compares the full `HEAD` with an expected full SHA. A dirty tree only warns, then builds. Pin the full 40-character SHA, assert `HEAD` equals it, and refuse to build from a dirty tree | A test of the generated script: a wrong `HEAD` or a dirty tree exits non-zero |
| Dirty ripper builds (`fork_source.py:504-510`, `:1585`) | A `-dirty` build tag counts as its release for ordering. Keep that for ordering, but report a dirty build as unapproved, and never offer or install one | A test that a `-dirty` tag reads as unapproved |
| App updates (`update_attestation.py`) | **Already ahead:** the updater refuses anything without a Sigstore build-provenance attestation. Its own notes say `main` isn't protected and an older build can be served as newer. Refuse a version lower than the one installed | A test that an older version is refused |

### The cyanrip fork

| Where | What to check | Proof |
|---|---|---|
| What the log echoes | Titles from `-t`, CD-TEXT and ISRCs read from the disc go into the log and the cue. Escape control characters and newlines as they're written, so no field can forge a line for Platterpus's parser or a tracker's logchecker | A test with a CD-TEXT title carrying `\nAccurip: accurately ripped` |
| Filenames (`-T`) | The sanitize mode handles `../`, control characters, a leading dot and reserved names | Tests per case |
| Sub-channel and drive answers | A frame or a mode page from the drive is input too: the `Recordable:` placeholder (lap 8 S4) is one where an unchecked answer was printed as fact | Bounds and sentinel checks, as S4's fix does |
| Release builds | `tools/gen-golden-reference.py` already refuses a dirty build. Make every released binary refuse one too, so a release can never name a tree it wasn't built from | A test, or a release-workflow step that fails on `-dirty` |

### What the claude-code-skills session found in its own repository, and fixed

All in `claude/brave-pasteur-40a2fq` at `435824b`:
- the hidden-character rule now scans `src/`, `tests/`, `docs/` and `.github/` too, where a
  Trojan Source edit shows a reviewer one thing and runs another. Three tests on `main` held
  the characters they plant literally; they now spell them as escapes;
- the cloud install hook refuses a release whose files carry a hidden character;
- a server's error, and what Claude Code sends back, are printed with control characters
  spelled out, so they can't drive a terminal or forge a line in an issue agents read.

**Still open, and behind Platterpus:** this repository's releases carry no checksum and no
provenance attestation, and its hook installs the newest release with nothing behind it but
HTTPS. Attesting releases, as Platterpus does, changes the release workflow, which waits on the
owner's word.

## Appendix A. What made EAC trusted, and what isn't worth copying

From EAC's own pages, and from what the community built around it:

1. **It checks its own reads, and says where it's unsure.** It reads "almost perfectly" by
   "multi-reading with verify", and "will tell you on which time position the (possible)
   distortion occurred" ([EAC's home page](https://www.exactaudiocopy.de/)). Other rippers of its
   day only corrected jitter, so users had to listen to every track.
2. **It checks the result against everyone else's,** through AccurateRip
   ([Wikipedia](https://en.wikipedia.org/wiki/Exact_Audio_Copy), citing PC World), and later
   CTDB, whose plugin also names the samples that differ.
3. **Its log lets anyone check a rip without the disc.** The settings and every track's result
   are on the page, and trackers built logcheckers on it.
4. **The right settings are known and shared.** Guides set it up the same way, and AccurateRip's
   drive-offset list was largely built from EAC users (Platterpus's Part E6).
5. **It copies the disc exactly:** offset, gaps and pregaps, a cue sheet, ISRCs and pre-emphasis.
6. **It's free,** and it has run on thousands of drives for over twenty years.

**What isn't worth copying:**
- it's closed source;
- it runs on Windows only;
- it needs a guide to set up;
- it ships a paid metadata plugin;
- it prints "Copy OK" over a track AccurateRip rejects.

Platterpus already avoids the first four. The fifth is row 8.

**Where each stands in section 5:**

| Trait | Rows |
|---|---|
| 1 | 2, 3, 5, 8, 9, 10 |
| 2 | 11 to 14 |
| 3 | 9, 27, 28 |
| 4 | 17, 19, 30 |
| 5 | 21 to 25 |
| 6 | 29, 31 |

## Appendix B. Which EAC to run, and why not an older one

Asked by the owner on 2026-10-26: "ive been told it is now since that version had all sorts of
things we dont want or need … and paid for. not what they stand for, so who knows what else they
put in there".

**Run 1.8, from exactaudiocopy.de only.**
- **What EAC's changelog shows:**
  - no change to secure mode after 1.0 beta 3 (September 2011), which added the CTDB plugin;
  - since then, changes to metadata, plugins and the burning component;
  - one fix that matters here: on 2015-04-09 EAC stopped "crashing EAC whenever a read error
    occurs". Beta 3 lacks it, which matters on a damaged disc.
- **The paid part** is the GD3 metadata plugin, added in May 2011, before beta 3. So beta 3
  carries it too. It costs money after 10 test lookups, and it's optional in the installer.
- **The bundled extra** was an eBay shortcut in the 0.99 prebeta 4 and 5 installers, 2008 and
  2009. It was pre-ticked, and unticking it skipped it
  ([Wilders Security](https://www.wilderssecurity.com/threads/exact-audio-copy-detected-as-variant-of-win32-adware-adon.254059/)).
  Nothing found ties adware to a 1.x installer. Warnings about 1.8 come from mirror sites
  ([FileHorse](https://www.filehorse.com/download-exact-audio-copy/),
  [Filepuma](https://www.filepuma.com/download/exact_audio_copy_1.8-40081/)), so download from
  EAC's own site.
- **In the installer:**
  - keep AccurateRip and the CTDB plugin;
  - leave off GD3, the other metadata plugins and AcoustID.
- **Closed source:** no one outside its author can check what EAC does. That doesn't weaken the
  comparison, because AccurateRip and CTDB judge both rippers' audio, not EAC. Run it on a
  machine or virtual machine kept for ripping.

## Appendix C. eacguide.github.io: a setup guide, not an authority

Asked by the owner on 2026-10-26: "is this file the final source of truth for EAC, but most
importantly, the single truth of ripping?"

**It's neither.**
- **What it is:** a community guide by one author, first posted on a file-sharing forum. Its
  repository has 4 commits, all on 2017-12-26. It's written for EAC 1.0 beta 3.
- **What it aims at:** a log that passes a tracker's logchecker.
- **Where it agrees with the EAC baseline:** secure mode, accurate stream, C2 off, the offset from
  AccurateRip's list, gaps appended to the previous track, Test & Copy, AccurateRip and CTDB.
- **Where it's silent:** speed reduction, and what "Copy OK" means.
- **Where the evidence contradicts it:** it says that with these settings "the only possible
  errors would be with the CD itself". On this drive, track 3 of one disc reads right in some
  rips and wrong in others, on both builds, with no read error reported.

No guide is the truth of ripping. The truth is the audio checked against other people's rips of
the same pressing, ideally on more than one drive.

## Appendix D. Corrections made along the way

Each was made on 2026-10-26 and is already reflected above.

| What was said | What's true | Found by |
|---|---|---|
| EAC doesn't step speed down | EAC has "allow speed reduction during extraction" | The dBpoweramp test's EAC settings, and Platterpus's archived settings guide |
| The EAC baseline ran without Test & Copy | All three sessions used it: every track has a Test CRC | Reading `platterpus@bba81563:output_reference/EAC_*/` |
| Track 3's misreads are likely `.26`'s speed; re-read slower | No cause is shown. `.26` read it right at 0.99× and wrong at 0.74×; `.25` read it wrong at 0.96× on 2026-10-20. This drive takes no speed setting | The fork's lap 8 S8 |
| Platterpus's Part D deductions | Several came from `hey-bro-check-log`, unmaintained since 2020; OPS's differ (section 6) | Reading `OPSnet/Logchecker@ca56547` |
| Run 1's findings, "Speed observation" (Appendix G) | Superseded by the row above. Kept word for word as filed | The fork's lap 8 S8 |

## Appendix E. The old report's IDs, mapped to section 5's rows

For a session that already has the first four-runs report.

| Old ID | What it was | Row |
|---|---|---|
| R1 | Say "wrong" when the evidence says wrong | 8 |
| R2 | Never print "Copy OK" or "confirmed" over a track AccurateRip contradicts | 8 |
| R3 | The per-track status says the outcome | 8 |
| C1 | Track 3 at `.26`'s speed | 6 (the speed theory withdrawn) |
| C2 | A right read in hand, a wrong one shipped | 2 |
| C3 | A cancel must keep what's right | 2 |
| C4 | A time bound on a damaged disc | 5 |
| C5 | Track 5's right value never read | 7 |
| Harness: cue ISRC check | Compares with the code sent | 22 |
| Harness: tray-open blip | One flap cost 57 steps | 33 |
| Harness: cover-art race, derived-file check, audit on a damaged disc, the chase's missing records | Platterpus's test harness | Appendix G, and section 8 |
| Harness: `Recordable:` and track 9's pregap | The fork's | 23 and 21 |
| EAC parity items 1 to 7 | Track 3, the right read, a time bound, truthful wording, track 5, sample location, per-run scoring | 6, 2, 5, 8, 7, 11, and section 2 |

**The test harness, which doesn't decide correctness.** These failed steps, not rips, and none
touched the audio. Fix them so the next run's failures are about rips:
- the cue's ISRC check compares with the codes sent;
- a "tray open" blip cleared the disc view;
- the cover-art grade races the booklet download;
- the derived-file check runs before the files are written;
- the audit expects clean on a damaged disc, and counts a replaced read's errors;
- the chase's diagnostics records are missing from the bundle;
- `Recordable:` reads unknown;
- track 9's pregap.

**The timed rip:** tracks 1 to 3, two rips each.
- `.26` is 2.9× faster on The Police, 2.8× on disc 3 and 5.1× on disc 4.
- Each pair agrees within 1%.

## Appendix F. Terms used here

| Term | Meaning |
|---|---|
| AccurateRip | A database of track checksums from other people's rips. A match at confidence N means N rips agree with ours |
| Frame 450 | AccurateRip's one-frame checksum. A match proves the pressing; it doesn't prove the track |
| CTDB | The CUETools Database: whole-disc checksums, per-track checksums and recovery data |
| Secure mode | EAC reads each sector at least twice, and re-reads a bad one until 8 of 16 agree |
| Test & Copy | EAC reads every track twice and compares the CRCs |
| `-Z N` | cyanrip re-reads a track until N+1 reads agree, up to `-r` reads |
| `-r N` | cyanrip's per-frame retries, and its cap on whole-track reads |
| Securing pass | Platterpus re-reads the tracks AccurateRip didn't verify, with `-Z` |
| The chase | Platterpus re-reads singly until one read verifies, then keeps that read |
| Paranoia skip | libcdio-paranoia gave up on a stretch and kept an unverified read |
| Pregap, `INDEX 00` | The gap before a track. Its position goes in the cue sheet |
| ISRC | A recording's code. The disc can carry its own in the sub-channel |
| HTOA | Hidden audio before track 1 |
| Logchecker | A tracker's program that scores a rip log |
| Fast Verified, Archival Exact | Platterpus's default goal, and the one that reads every track until reads agree |

## Appendix G. Run 1 findings: the reference disc, 2026-10-21 11:35 UTC

Word for word as written on 2026-10-26, from the bundle `20261021t113505z`. Its "Speed observation" in §3 is superseded: see Appendix D.

### Full acceptance run 20261021T113505Z: findings

Run: Platterpus 0.7.112 (9bf0cd3) with ripper `.26` (ca0f097), reference disc (The Police,
14 tracks), started 2026-10-21 11:35:05 UTC. Verdict: pass 424, fail 60, unreachable 1, info 12.
Read-only analysis. Sources: Platterpus `origin/main` bba81563 (its acceptance script is
byte-identical to the `script_source` in `session/run/report.json`), and the fork's
`origin/platterpus-fork` fc73b4d.

#### Path abbreviations (all bundle-relative)

- `T` = `session/run/transcript.txt`; `RJ` = `session/run/report.json`
- `AL` = `session/artifacts/02platterpus/log.txt` (app log; its times are UTC-04:00, converted to
  UTC below). `AL1` = `session/zz-applog-rotations/03platterpus/log.txt.1`
- `F/` = `album/full acceptance_ angle_bracket 20261021t11__terpus-fork-gca0f097/`. Section F,
  the whole-disc rip in dynamic mode. Files: `F.log` (the ripper log, `…gca0f097.log`), `F.sec`
  (`…platterpus-securing-pass.txt`), `F.add` (`…platterpus-addendum.txt`), `F.json`, `F.cue`,
  and `F.eac` (`… (EAC-compatible).log`)
- `N/` = `album/secure reread 20261021t113505 platterpus-fork-gca0f097/`. Section N, archival,
  with uniform `-Z 2`. Files `N.log`, `N.json`, `N.cue`, `N.eac`, on the same pattern.
- `K3/` = `album/derived wav …gca0f097/`
- `A1/`, `A2/` = `album/timing A1|A2 … platterpus-fork-g5f1d036/` (`.25`); `B1/`, `B2/` =
  `album/timing B1|B2 … platterpus-fork-gca0f097/` (`.26`)
- `R16on/`, `R16off/` = `album/r16deemphon/`, `album/r16deemphoff/` (`Unknown disc (PNTI).log`)
- `P@` = `platterpus@bba81563:`; `C@` = `cyanrip@fc73b4d:`

#### 1. The 60 failures: four causes

| Group | Count | Script lines | Root cause | Owner | New? |
|---|---|---|---|---|---|
| A | 3 | L726, L1109, L1274 | Platterpus defect: the cue audit ignores `--prefer-disc-isrc` | Platterpus | New |
| B | 2 | L729, L730 | Rig trigger (a drive-status flap), plus a Platterpus grader defect | Platterpus | New |
| C | 16 | L782–L864 (sections H, I) | Cascade of B: the auto-rescan opened a 4-candidate release picker that no step answered | Platterpus (app plus harness) | New |
| D | 39 | L897–L1086 (sections J, J2, K1, K2) | Platterpus harness race: `pick-release` answered C's stale picker, and `rip` fired while J's own rescan was still running | Platterpus (harness) | New |

3 + 2 + 16 + 39 = 60. One step was unreachable: E2 L571. It was known beforehand (TASKS
"Permutations the acceptance test still does not run", (a); T:389). That makes 48 of the 60
failures B's knock-on effects, and the other 12 (A, B and the 10 in C before the cancel) come
from two defects. **No failure is a fork defect, and none is a defect in the audio.**

##### A. The cue ISRC round-trip check counts the disc's own ISRCs as a mismatch (3)

- **Expected:** `expect-album-audit` passes. **Happened:** `cue_integrity warned: cue sheet — 14
  ISRC(s) differ from what we sent: track 1: cue GBAAM7800003 vs sent GBAAM0201086…`
  (T:460-461 for L726, T:971 for L1109, which is K3 and 2 tracks, and T:1130 for L1274, which is
  N; AL:660).
- **What the files hold:** F's argv sends `--prefer-disc-isrc`, along with MusicBrainz ISRCs in
  `-t … isrc=GBAAM0201086` (F.log:2). `.26` reads the disc's codes (`Disc ISRC: GBAAM7800003`,
  F.log:78) and, as `--prefer-disc-isrc` asks, writes them to the tags and the cue
  (F.log:117; F.cue:16-100). The report itself records this correctly as info only:
  `isrc_disc_differs … the files carry GBAAM7800003` (F.json:322-387).
- **Root cause:** a Platterpus defect. `_check_isrcs` compares the cue with the ISRCs Platterpus
  *sent*, with no case for `--prefer-disc-isrc` (P@src/platterpus/cue_validate.py:575-663,
  mismatch at :619-620). It never fired before because `.25` read no disc ISRC on this drive
  (A1.log:76 `Disc ISRC: none (libcdio returned none)`). `.26` fixing item 8 is what exposed it.
- **Fix:** when the argv carries `--prefer-disc-isrc` and the report holds a valid disc ISRC for a
  track, expect the disc's code in the cue. This is Platterpus's fix. TASKS R20 (P@TASKS.md:88)
  covers the report and argv but does not name the cue check.

##### B. The tag and cover graders read the live window, which a drive-status flap had cleared (2)

- **Timeline (UTC):** F's rip finished at 12:01:58 (AL:610). Post-rip checks ran, FLAC verify
  passed (AL:647), and CTDB matched (AL:651). At **12:02:39** the drive's status poll read
  `disc -> open` (AL:649), then `disc removed … — clearing the disc view` (AL:650),
  `open -> unavailable` (AL:653) and, 2.5 s later, `unavailable -> disc … auto-rescanning`
  (AL:665-666). Nothing asked for an eject: `auto_eject_after_rip off` (T:31).
- **L729 expect-tags (T:466):** `track 1: ALBUM is ['full acceptance: angle<bracket …'], chosen
  ''; … the window has no row for it`. The FLAC is in fact right
  (`session/run/tags0729.txt:10-17`). The grader takes "chosen" from the window's track table
  (P@src/platterpus/uiscript/artifact_verbs.py:173-182), which the flap had just emptied.
- **L730 expect-cover-art (T:468):** `mode 'embed' embeds nothing, yet track(s) 1…14 carry a
  picture`. The grader takes `release_id` from the window (artifact_verbs.py:216). The flap
  cleared it, and `plan_actions` returns (False, False) for an empty id
  (P@src/platterpus/adapters/cover_art.py:434-454). The files do hold the cover
  (tags0729.txt:30; AL:636 `Cover art: embedded in 14 track(s)`).
- **Root cause:** the trigger is the rig's drive. It reported tray-open for one poll. The same
  2.4 s open→unavailable→disc pattern recurs while the app is idle in earlier logs (AL1:53913,
  63418, 72444, 72454, 72463). Its cause cannot be found from the bundle. The defects it exposed
  are Platterpus's:
  1. `MediaWatcher` treats a single OPEN reading as a removal, with no confirming second read
     (P@src/platterpus/drive_media.py:76, 123, 209-231).
  2. The graders compare the rip's files with mutable window state instead of with the rip's own
     record (its report or argv).
- **Owner:** Platterpus. Neither TASKS nor STATUS names this; TASKS:7792 describes the watcher
  without noting the flap.

##### C. Sections H and I: blocked behind the release picker the auto-rescan opened (16)

- At 12:02:57 the auto-rescan's MusicBrainz lookup returned 4 candidates and opened the modal
  picker (AL:681-682). The disc view was still empty, so:
  - L782 and L825: `no tracks are loaded` (T:503, 554)
  - L791: no track 1 (T:507)
  - L792: Start not enabled (T:509)
  - L793: waited 120 s for "Album already ripped" while the picker was open (T:511)
  - L794: nothing to wait for (T:513)
  - L827: refused to press Start behind the picker (T:558)
  - L831: `no rip is running` (T:572)
  - L841: the status line still read F's `Done — all 14 tracks…` (T:577)
  - L798, L802-L805, L860, L864: `no rip has finished since this section asked for one`
    (T:540-548, 581-583)
- **Root cause:** a cascade of B. The script calls `pick-release` only after its own `rescan`
  steps (E, J L893, N L1242), and an unplanned rescan has no step to answer it. **Owner:**
  Platterpus. The direct fix is B's debounce. The harness could also fail fast on a picker it
  didn't expect, instead of letting 16 steps time out behind it. Losses from C: H's overwrite
  prompt (the per-track `-t` escaping, `E=MC2…`) and section I's whole cancel path, including
  `sigterm-world` (T:587: NOT DETERMINED) and S25. None of them was tested.

##### D. Sections J, J2, K1 and K2: rips started while J's own rescan was still running (39)

- L892 `rescan` started a new DiscInfoWorker at 12:08:35 (AL:702). L893 `pick-release 1 120`
  passed in 0.6 s (T:643), but it answered **C's stale picker**: `user chose 65282302… after
  338.4s` (AL:704-705). The new scan was still running cyanrip `-I` and its MusicBrainz lookup
  until **12:08:49** (AL:770: `4 candidates … again, but a release was already chosen … not
  re-opening`).
- Within those 14 s the script ran four rips. Each one failed on `Start button is not enabled`:
  L897, L965, L1045, L1073 (T:651, 743, 803, 877; AL:708, 725, 743, 757). All their graders
  failed too (T:653-691, 745-761, 805-843, 879-904). K3's rip was the next one, at 12:08:51
  (AL:795), and it succeeded (T:938-940).
- **Root cause:** a Platterpus harness defect. `rip` fails at once while a scan is active instead
  of waiting a bounded time, and `pick-release` takes any open picker, including one an earlier
  scan opened. On a clean run the fresh picker gates the scan, so this only shows up after C.
  **Owner:** Platterpus (uiscript). New. TASKS:6857 records an older, different "Start not
  enabled" cause, which has been fixed.
- **Untested as a result:** the drive-open proof (J), the J2 permutations (no `-r`/`-Z`, fixed
  speed, library move, **`--prefer-disc-isrc` off**), MP3 (K1) and WavPack (K2).

#### 2. The known fixes on this disc

| # | Item | Verdict | Evidence |
|---|---|---|---|
| 2 | Keep the AccurateRip-verified read, not the majority (the 0.7.112 chase) | **NOT EXERCISED as shipped; the goal is CONTRADICTED in N** | F: the chase on track 5 reads `skipped_reads_agreed`, `distinct_reads_seen 1` (F.json:1251-1252), with E0036697 every time (F.log:402, F.sec:143-147). Track 3 was saved by the securing pass, not the chase (F.json:1232-1241; F.add:20-25). No log hits the repeat limit. **N:** track 3's reads were `59D352DD` (the AR-verified value), then `3D8FCF0C` three times (N.log:225-231). The rip shipped `3D8FCF0C`, which matched on frame 450 only (N.log:270-275). N's `retried_tracks` is `[]`, mode `uniform` (N.json:1443-1445), because the chase runs only over the securing pass's retried tracks (P@src/platterpus/workers/rip_worker.py:3226-3238; P@src/platterpus/verified_read_chase.py:14-45). So the archival path has no chase. The fork's `--prefer-accuraterip-match` (`.27`, unreleased; C@docs/handshake/STATUS.md:30) acts only at the repeat limit, and N converged after 4 reads, before it. |
| 3 | No "No errors occurred" over an unclean read | **NOT EXERCISED** | The fix fires on paranoia skips or an error line under `Ripping errors: 0` (P@src/platterpus/rip_health.py:1-20; P@TASKS.md:1290-1320). No log has either: every count is 0, and every `error_positions` entry is empty (F.json:691 onward). Outside its scope: N.json:612 and N.eac:266 still read "No errors occurred", and N.eac:96-99 reads `Test and Copy CRC identical — confirmed across 4 secure re-reads … Copy OK` for track 3, whose first read disagreed. That wording overstates the case (Platterpus). |
| 5 | The record says which checks ran | **PROVEN (pass, fail and not-run arms); cut-short NOT EXERCISED** | K3: `ctdb: not run — CTDB verifies whole discs…`, `flac_integrity: ran — passed`, `derived: ran — passed` (K3 json:1135-1139). F: `flac_integrity: ran — passed`, `ctdb: ran` beside a verdict, by design (P@src/platterpus/verification_gates.py:131-157). No give-up happened. |
| 6 | Error positions in the report | **PROVEN in structure; positions NOT EXERCISED** | `disc.error_positions` is read from `.26`'s `-j`, with `state: read`, positions `[]`, 0 read errors and 0 skips, and `count_agrees_with_counters: true` on every track (F.json:691 onward, N.json:902 onward). The disc gave no error, and the EAC-layout log is unchanged by design. |
| 7 | CTDB per track, over ±5879 | **PROVEN on hardware; a nonzero-offset match NOT EXERCISED** | F: `offset_range 5879`, `matched_offset 0`, `Per track: 13 of 14 agree with CTDB; track 5 agrees only with a minority (2 of 1,518)` (F.json:2151-2157, 2267). N: `no_match … Per track: 12 of 14 agree; tracks 3 and 5 differ from every entry` (N.json:2340-2346, 2456). |
| 8 | The disc's ISRCs | **PROVEN** | `.26` read 14 of 14 codes on every `.26` rip (F.log:78…1068; N.log:84…; B1.log:78; K3; R16on.log:76). The cue matches EAC's cue track for track (F.cue:16-100 against P@output_reference/EAC_flac/eac_baseline_police_classics.cue:13-111; track 1 GBAAM7800003, track 14 GBAAM9500177). `.25` in this same run read none (A1.log:76). The fork's close condition is met (C@docs/handshake/STATUS.md:15). It also exposed group A. |
| 10 | Pregap stability | **Track 4: consistent (158 in 8 of 8 `.26` logs). Track 9: CONTRADICTED** | EAC's value for track 9 is 94: INDEX 00 03:44:11 on a 16,905-frame track 8 (EAC cue:74). `.25` read 94 twice (A1.log:50, A2.log:50). `.26` read **95** in 3 logs (F.sec:52, N.log:52, K3 log:52) and `pregap of track 9 unknown (sub-channel CRC mismatches)` in 5 (F.log:52, B1.log:52, B2.log:52, R16on.log:49, R16off.log:49). It read 94 in **none**. No `two searches read` clause printed anywhere. The fork's stated close condition, "reads 94 and 158 in every log" (C@docs/handshake/STATUS.md:20; C@docs/handshake/round-36-lap-04.md:81), fails. The cue for F has no INDEX 00 for track 9 (F.cue:69-70), and N's says 03:44:10, which is 95 (N.cue:69). Owner: the fork. Side effect: the new "unknown" line printed on a drive for the first time (STATUS.md:12 `gaps-undetermined-pregap`), and Platterpus's `expect-pregaps-agree` set those 3 logs aside as unreadable (T:1997). |
| 11 | Whether the read offset is AccurateRip's | **PROVEN in the report and results pane; the log half not shipped** | `read_offset_check: matches, applied 667, listed 667, AR re-confirms 13 of 14` (F.json:1160 onward; AL:616). The cyanrip log says only `Offset: +667 samples` (F.log:10), and the EAC-layout log says `Read offset correction : 667` (F.eac:22). Both are as planned (P@TASKS.md:125, P2 #6). |
| 12 | No "not in the database" for a disc AccurateRip holds | **PROVEN** | N had the old trigger, 12 of 14 verified. Its verdict reads `…on the other 2, only one frame matched` (N.json:259 onward); F's reads the same way (T:577). The phrase appears nowhere in the bundle outside the script's comments. The "differs from AccurateRip's entry" arm was NOT EXERCISED: every failing track matched frame 450. |
| — | `Accurate stream:` | **PROVEN as printed and parsed; one Platterpus gap** | `Accurate stream: declared supported by drive (capabilities page, not measured)` (F.log:15) maps to `rip.accurate_stream: declared_supported` (F.json:1178). The EAC-layout log still says `Utilize accurate stream : (not reported by the ripper)` (F.eac:18, N.eac:18). That is now false. It may be held back on purpose until the wording is agreed with the fork (unsure). |
| — | `Recordable:` | **Printed, but undetermined on this drive** | `Recordable: unknown (profile 0xffff is not a CD profile)` on every `.26` log (F.log:16), maps to `recordable: unknown` (F.json:1180). The fork's lap 1 S5 expects `no, CD-ROM (drive's current profile)` for a pressed CD (C@docs/handshake/round-36-lap-01.md:59). Owner: the fork, to find out whether the BDR-209D really reports 0xFFFF or the profile is parsed wrongly. |

#### 3. Accuracy

Track 3's AccurateRip-verified value is **59D352DD** (v1 3C8BDDD2, confidence 128; v2 96DF8C22,
confidence 200; F.sec:102-106), which matches the repo's records
(P@docs/handshake/inbound/round-35-lap-15.md:78). Track 5's is **C96464AB**, and no read in this
run produced it.

| Rip (build) | Verified | Not verified (frame 450 only) | Shipped CRCs of tracks 3 and 5 |
|---|---|---|---|
| F album pass (`.26`, about 3.5x) | 1, 2, 4, 6-14 | 3 (2363932F), 5 (E0036697) | first pass (F.log:248-253, 402-407) |
| F as shipped, after the securing pass | 1-4, 6-14 (13 of 14) | 5 | 3 = **59D352DD ✓** (re-read, verified); 5 = **E0036697 ✗**: 3 matching reads, the same as the first pass (F.add:20-32) |
| N archival (`.26`) | 1, 2, 4, 6-14 (12 of 14) | 3, 5 | 3 = **3D8FCF0C ✗**, 5 = **6902BCF0 ✗** (N.log:270-275, 438-443) |
| K3 (`.26`, tracks 1-2) | 1, 2 | — | — |
| A1, A2 (`.25`, about 0.9x) | 1, 2, 3 | — | 3 = 59D352DD ✓ in both (A1.log:246, A2.log:246) |
| B1, B2 (`.26`, about 2.7x) | 1, 2 | 3 | 3 = D7314554 ✗, 2363932F ✗ (B1.log:248, B2.log:248) |
| R16on, R16off (`.26`, track 1) | 1 | — | — |

- **Shipped unverified when a verified read was available: yes, track 3 in N.** Its first `-Z`
  read was 59D352DD, the verified value, and cyanrip converged on 3D8FCF0C instead
  (N.log:225-231). The report raises only `heavy_reread` (N.json:603), and the EAC-layout log
  calls the result "confirmed across 4 secure re-reads… Copy OK".
- Track 5 never verified. The values read were E0036697 (4 times in F) and 6902BCF0 (3 times in
  N). Per track, CTDB puts F's E0036697 with a minority of 2 in 1,518 (F.json:2267) and N's
  6902BCF0 with none.
- **Speed observation (correlation only, small sample).** With the same argv, `.26` reads about
  2.9 times faster than `.25` (ratio 0.348 and 0.346, T:2206). The fork attributes that to
  upstream `7dbe56a` (C@docs/handshake/round-36-lap-01.md:48). Track 3 verified in 2 of 2 `.25`
  rips at 0.9-0.96x, and in 0 of 2 `.26` rips at 2.8x, and F's fast first pass misread it too.
  The fork pre-committed to GO "unless … the timed rip show[s]" a defect
  (C@docs/handshake/round-36-lap-07.md:142), so this deserves a look before the round closes.

#### Unsure, or not checked

- What makes the drive report tray-open briefly. Whether it's a kernel or drive power-state
  artefact can't be determined from the bundle.
- Per-track CTDB rows show `offset: -7` while the whole-disc `matched_offset` is 0
  (F.json:2271 onward). Not explained.
- Whether the "unknown (sub-channel CRC mismatches)" track 9 result comes from the two searches
  disagreeing or from one search failing. The log doesn't say.
- `SOURCES.txt` says app-log rotations .7 to .10 were archived, but `MANIFEST.txt:196-199`
  excluded them for the size budget. This is a minor wording inconsistency in the bundle.
- The DIAGNOSTICS warning `cyanrip exited 64` (DIAGNOSTICS.txt:123-143) is the expected negative
  test at L1414/L1416 (T:1514-1535), not a defect.

## Appendix H. Run 2 findings: the damaged disc, 2026-10-21 21:45 UTC

Word for word as written on 2026-10-26, from the bundle `20261021t214509z`. `B/` is the bundle's root.

### Run 2 findings: Full acceptance run of 2026-10-21 21:45 UTC (bundle 20261021t214509z)

Read-only analysis. Platterpus 0.7.112 (build 9bf0cd3) with cyanrip `0.9.4-rc3+platterpus.26` (ca0f097).
Source read against: `platterpus@bba81563` and `cyanrip@ca0f097` (the build that ran; the fork tip
`fc73b4d` is cited where it differs). All times are UTC. The app log and the cyanrip logs are written in
local time (UTC-04:00), and every time below has been converted.

Path prefixes used below:

- `B/` = the bundle's root, `20261021t214509z/`
- `ALB/` = `B/album/full acceptance∶ angle‹bracket 20261021t214510 platterpus-fork-gca0f097 CD1`, followed by
  `.log` (the album pass's cyanrip log), `.platterpus-securing-pass.txt`, `.platterpus.json` (the rip
  report) or ` (EAC-compatible).log`
- `APP` = `B/session/artifacts/02platterpus/log.txt` (the live app log; this run is lines 5825 to 14558)
- `DIAG1` = `B/ripperdiagnostics/cyanrip-diagnostics-20261021T214611Z.json` (the album pass's `-j` record)
- `DIAG2` = `B/ripperdiagnostics/cyanrip-diagnostics-20261022T001928Z-securingpass.json`

The seven bundled rotations, `B/session/zz-applog-rotations/*/log.txt.1` to `.7`, cover 2026-10-12 to
2026-10-21 11:50 UTC, which is all before this run. They hold nothing about it. Rotations `.8` to `.10`
were left out for the size budget (`B/MANIFEST.txt:93-95`), and they are older still.

#### 0. Which disc it was: confirmed

The disc is *Roots Music: An American Journey*, disc 1 of 4 (Rounder 11661-0501-2, release
`53d0f596-95a3-4e60-b4aa-09f5f7532b1e`). It has 18 tracks, MusicBrainz disc ID
`zxtbw2JgJ.kZBiyIcKOQvn2ZTUM-` and AccurateRip ID `00244e5e-01e6a7bd-000dac12`.

- Evidence in this run: `ALB/.log:2,27-35`, and `B/session/run/transcript.txt:356-369`, where the step
  identified the disc unambiguously with 18 tracks.
- Evidence that it is the same damaged disc as the 2026-10-04 run: the same disc ID appears in
  `platterpus@bba81563:tests/fixtures/evidence/docs/handshake/artifactsround30/round30oct04fullreport.json`.
  `platterpus@bba81563:docs/testing.md:4253-4262` describes that run: track 18 had 2,586 skips and
  section F's six-hour wait ran out with the securing pass still on track 18. **This run repeats that
  failure.**

#### 1. Why the rip ran past 6 hours

##### Summary

**Track 18's damaged area, read through a drive that cannot be slowed, accounts for 5 h 17 m 50 s of the
rip's 6 h 00 m 10 s (88 %).** The securing pass's `-Z 2 -r 5` is what multiplies it: it re-reads track 18
up to five times, and each read takes about 1.75 to 2.4 hours.

- Pass 1, the album pass, read track 18 once in 2 h 22 m 28 s.
- Pass 2, the securing pass, re-read tracks 11 to 18 and reached track 18's second of up to five reads.
  The harness then stopped it.

**0.7.112's new rule, "re-read singly until one read AccurateRip verifies" (the verified-read chase),
never ran.** It runs only after a securing pass that finished (`rip_worker.py:3137-3149` returns first;
the chase is called at `:3231`). No `[verified read]` line appears anywhere in `APP`, and every
`retried_tracks[].verified_read_chase` is `null` (`ALB/.platterpus.json:5615-5675`).

##### The album pass

The album pass ran from 21:46:11 to 00:19:28. It was invoked with `-r 5` and no `-Z` (dynamic mode), as
`ALB/.log:2` and `APP:6000` show.

| Trk | Start (UTC) | Read time | AccurateRip | Paranoia | Source |
|---|---|---|---|---|---|
| 1-10 | 21:46:28-21:50:30 | 17-34 s each, 6.0-8.3x | verified (v2 conf 28-29) | clean | `ALB/.log:64-841` |
| 11 | 21:50:50 | 24.8 s | frame 450 only | FIXUP_ATOM 1012 | `ALB/.log:846-921` |
| 12 | 21:51:16 | 23.6 s | frame 450 only | FIXUP_ATOM 26166 | `:926-1001` |
| 13 | 21:51:41 | 33.9 s | frame 450 only | **1 skip**, LSN 158236 | `:1006-1082` |
| 14 | 21:52:16 | 55.7 s | frame 450 only | — | `:1087-1162` |
| 15 | 21:53:14 | 61.2 s | frame 450 only | **1 skip**, LSN 208410 | `:1167-1244` |
| 16 | 21:54:16 | 22.2 s | frame 450 only | — | `:1249-1324` |
| 17 | 21:54:39 | 139.4 s, 1.4x | frame 450 only | **28 skips** | `:1329-1405` |
| 18 | 21:56:59 | **8548.5 s (2 h 22 m 28 s), 0.031x** | frame 450 only | **2076 skips**, 703 FIXUP_EDGE | `:1410-1488` |

On track 18, 259 reads took 10 s or more. They add up to 7,087 s of the 8,548 s, and the longest was
77 s at LSN 253113 (`DIAG1` messages; `ALB/.log:1528`). The app logged 17 "rip stalled" warnings on the
album pass's track 18 between 22:26 and 00:11 (`APP:8064` onward). The footer reads
`Ripping errors: 2106 (including 2106 paranoia skips)`, `Rip completed: yes`
(`ALB/.log:1515-1530`).

##### The read-speed ladder did not step

The ladder logged "no step after pass 1: the drive reported no read errors" (`APP:10226`). Two things
stopped it, and both are by design:

- The drive cannot change speed: `Speed: default (unchangeable)` (`ALB/.log:13`), and
  `rip.speed_changeable: false` in the report.
- The ladder does not count paranoia skips as read errors
  (`platterpus@bba81563:src/platterpus/ladder_trigger.py:26-31,98-99`).

So read speed was not a lever on this drive, though the wording "no read errors" sits badly beside 2,106
skips.

##### The securing pass

**The plan.** `plan_securing_pass` re-reads the tracks that fail AccurateRip on a disc AccurateRip holds,
and that includes the tracks that matched on one frame only (`rerip_offset_variant`)
(`platterpus@bba81563:src/platterpus/securing_pass.py:222-235`). That gives `-Z 2 -r 5 -l 11..18`, run
as **one** cyanrip invocation (`ALB/.platterpus-securing-pass.txt:2`, `APP:10228`).

**The bound.** cyanrip's loop for each track stops when 2 reads match the current one
(`cyanrip@ca0f097:src/cyanrip_main.c:1778`), or when it reaches `-r` = 5 reads (`:1790`). At the limit it
keeps the read that most reads agreed on, and the newest on a tie (`:1244-1253`, `:1809`). Within each
read, paranoia's per-frame retries are capped at 5 (`cyanrip@ca0f097:src/cyanrip_main.h:732-739`, used at
`src/cyanrip_main.c:762-763`).

**The timeline.** Each read's start comes from the "being re-read (pass k)" lines in `APP:10303-13280`.

| Trk | Reads (UTC) | Read durations | Outcome | Source |
|---|---|---|---|---|
| 11 | 00:19:46-00:21:58 | 23, 28, 29, 26, 25 s | 5 distinct CRCs. **The kept 5th read `10248071` is AccurateRip-verified: v1 conf 12, v2 `F90C8B07` conf 29.** | `ALB/.platterpus-securing-pass.txt:65-116` |
| 12 | 00:21:59-00:24:14 | 34, 29, 22, 21, 28 s | 5 distinct; frame 450 only; 1 skip, LSN 151669 | `:155-207`; `DIAG2` track_state |
| 13 | 00:24:16-00:27:40 | 46, 39, 32, 50, 37 s | 5 distinct; frame 450 only | `:246-298` |
| 14 | 00:27:42-00:32:24 | 59, 58, 58, 53, 54 s | 5 distinct; frame 450 only | `:337-389` |
| 15 | 00:32:27-00:36:57 | 53, 54, 53, 57, 53 s | 5 distinct; frame 450 only | `:428-480` |
| 16 | 00:36:59-00:38:56 | 25, 23, 23, 24, 22 s | 5 distinct; frame 450 only | `:520-572` |
| 17 | 00:38:57-00:50:46 | **600 s** (17 stalls, 352 s), then 27, 28, 27, 27 s | 5 distinct; 142 skips over all reads | `:611-663`; `APP:11330-11453` |
| 18 | read 1: 00:50:49-02:34:38 | **1 h 43 m 49 s** (193 stalls of 10 s or more, 4,110 s, longest 59 s) | CRC `AB84C427`, "0 out of 2 matches" | `:702`; `APP:13280` |
| 18 | read 2: 02:34:38-03:46:11 | **1 h 11 m 33 s and unfinished** (137 stalls, 2,632 s) | Reached about LSN 253132 of 242462-262524, about 53 %. SIGTERM. | `:704,739-745`; `DIAG2` |

The securing pass ran 3 h 26 m 51 s. Tracks 11 to 17 took 31 m; track 18 took 2 h 55 m 22 s
(`DIAG2` `rip_time_us` 10,533 s). Every finished track hit the repeat limit with "at most 1 read agreed"
(`B/DIAGNOSTICS.txt:27-67`). On tracks 11 to 17, no two of the five reads ever returned the same
audio.

**Run-out projection.** At this pace, read 2 needed about another hour, and reads 3 to 5 about 1.75 to
2.25 h each. The securing pass would have ended about 10 to 11 hours after the rip began. After that, the
0.7.112 chase would have run, because tracks 12 to 18 each showed more than one value
(`verified_read_chase.py:36-43,186-198`). It allows up to `min(-r, 5)` = 5 single reads per track
(`:85,183`). For track 18 alone that is about 9 to 12 more hours. **The end-to-end worst case is
roughly 20 to 24 hours.** The script's own estimate said "up to 16h 20m" (`transcript.txt:4`), while
section F waits 6 hours.

##### The questions asked

**Does the new rule loop on a damaged disc where no read can ever verify?**

It cannot loop without end: each track gets at most 5 attempts
(`platterpus@bba81563:src/platterpus/verified_read_chase.py:85,183`;
`src/platterpus/workers/verified_read_run.py:138`). But it has **no time bound**, and its gate admits
exactly the tracks where no read can verify. The gate asks that "the drive returned more than one
value" (`verified_read_chase.py:36-43,194-198`), and a damaged track returns a new value on every read.
On this disc the chase would spend up to 5 more whole reads on each of tracks 12 to 18, with no prospect
of verifying track 18. **It did not run in this run.**

**Is it the securing pass, the `-Z` repeat count, read speed, or the drive?**

- **Drive and disc:** they are the root cause. 2,076 skips and 259 stalls on track 18, at 0.031x.
- **Securing pass:** it is why the rip went past 6 hours. It started at 2 h 33 m and spent 2 h 55 m on
  track 18.
- **`-Z`/`-r`:** the multiplier, at up to 5 reads × about 2 h.
- **Read speed:** not a factor. The drive's speed is fixed, and the ladder by policy ignores skips.

**Was any bound supposed to stop it?**

The bounds are counts only:

- `-r 5` on frame retries and on whole-track reads (`cyanrip@ca0f097:src/cyanrip_main.c:1790`;
  `src/cyanrip_main.h:732-739`);
- the chase ceiling of 5.

Nothing bounds time:

- The fork's stall watchdog only reports liveness: "Seconds a frame read must stall before reporting
  liveness" (`cyanrip@ca0f097:src/cyanrip_main.c:2537-2538`).
- Platterpus's stall detection only decorates the status line
  (`platterpus@bba81563:src/platterpus/workers/rip_worker.py:1246-1258`).
- `_REFIX_ETA_MAX_S` = 6 h (`rip_worker.py:549,1478-1492`) only suppresses the ETA (`APP:10291-10297`).
- The only time limit was the test script's own: `wait-for-rip 21600`
  (`platterpus@bba81563:src/platterpus/rig_scripts/fullacceptance.txt:601-618,664`). Its comment sizes F
  by "section N's workload" on a clean disc and does not consider a damaged one.

Neither repository has a time limit, the fork's tip `fc73b4d` included.

#### 2. The one failed step

**`L664 wait-for-rip 21600` expected** the rip that `L663 rip` started at 21:46:11 to finish within
21,600 s, so that F's later steps could grade a finished rip: `expect-rip-complete`,
`expect-verification`, the AccurateRip and CTDB checks, and the rest.

**What happened:** at 03:46:11 it recorded `fail: still not finished after 21600s`
(`B/session/run/report.json` step `line_no 664`, `elapsed_s 21600.025`; `transcript.txt:421-424`;
`APP:14524`).

- The rip was in the securing pass, on track 18's second read.
- The runner cancelled it with SIGTERM (`APP:14527`). The ripper's log gained its footer 9.5 s later
  (`APP:14535`).
- The run ended, with 348 steps BLOCKED and the verdict pass 144, fail 1, blocked 348, unreachable 1,
  info 4 (`transcript.txt:773-776`).

`B/MANIFEST.txt:28` words the same counts as "349 failed", which conflates BLOCK with FAIL.

**This is a budget overrun on the known damaged disc, not a new defect in F's checks.** The same thing
happened on 2026-10-04.

#### 3. Was the app's behaviour right for a user?

##### What the user was told

The user was told that something was slow. They were not told what it would cost, and they were not
given a choice.

- **Right:** the status line carries "· stalled Xm — the drive is stuck on a hard-to-read spot (a
  scratch or smudge)" (`rip_worker.py:1255-1258`), and 34 stall episodes were logged (`APP:8064-14466`).
  The securing pass announces "Re-ripping track(s) 11, …, 18 (didn't match AccurateRip) to secure them…"
  (`rip_worker.py:3111`).
- **Wrong:**
  - The pre-rip estimate was "about 1h" (`APP:5998`), and the actual time was 6 h 0 m 10 s and still
    running (`APP:14539`).
  - During the securing pass the ETA is withheld ("showing no estimate", `APP:10291-10297`), so a user
    sees no number at all.
  - Nothing says "track 18 alone may take another 10+ hours, and further reads are unlikely to verify
    it".
  - There is no way to stop re-reading one track and keep the rest.

##### Cancel

Cancel works: SIGTERM, the footer written, the drive released in about 10 s (`APP:14527-14547`). But it
is all or nothing:

- **Cancelling the securing pass discards every re-read it finished.** That includes track 11's
  AccurateRip-verified read (v2 conf 29). Nothing is swapped from a pass that did not finish
  (`rip_worker.py:3137-3149`). `_record_unfinished_refix` keeps only each track's converged flag and
  never asks `reread_supersedes` (`rip_worker.py:3462-3480`), although that rule would have kept the read
  (`platterpus@bba81563:src/platterpus/verdict.py:916-921`). The report says track 11 is
  `replaced: false, kept_read: first_read` (`ALB/.platterpus.json:5608-5615`). The EAC-layout log says
  "Copy NOT confirmed — re-reads did not converge" (`ALB/ (EAC-compatible).log:212-214`). **A verified
  copy was produced and thrown away, and no structured field or sentence mentions it.** The evidence
  survives only in the embedded securing-pass log text.
- The cancel is attributed to the user. The runner did it ("ui script run ended … cancelling it",
  `APP:14524-14527`), yet the log line reads "rip cancel requested by the user". The EAC-layout log says
  "INTERRUPTED (you cancelled the rip)" (`ALB/ (EAC-compatible).log:11,325`).

##### What it did with the bad tracks

The labelling is honest and conservative.

- All 18 FLACs are the album pass's reads (`B/MANIFEST.txt:75-92` lists them).
- Tracks 11 to 17 are flagged as never converging, and 13, 15, 17 and 18 as unverified skips. Track 18
  carries 2 frames of appended silence (`ALB/ (EAC-compatible).log:313-326`).
- The verdict is `warn`, naming the 8 frame-450-only tracks and the 7 that did not converge
  (`ALB/.platterpus.json:291`). `outcome.status` is `cancelled` (`:128`).
- `read_speed.unstable_tracks` is `[]` and `unresolved` is `false` (`:5604-5605`), even though tracks 11
  to 17 never converged. The verdict covers this, but the field is inconsistent.

##### Side effects worth noting

- **The drive's estimate is now wrong.** The app learned the drive's speed from this rip, "3500 s of
  audio in 9162 s; folded over 1 rip(s), 0.38x" (`APP:14545`;
  `platterpus@bba81563:src/platterpus/ui/main_window_drive.py:347-363` does not exclude a rip with stalls
  or skips). The next estimate for this drive will be about 2.6 times too long.
- **The bundled report predates the post-rip checks.** CTDB and FLAC verification were launched at
  03:46:21 (`APP`, just after 14547). The report was generated at 03:46:22 with `gates.ctdb: "ran"`,
  `gates.flac_integrity: "ran"` and both in `without_result` (`ALB/.platterpus.json:304,6860-6862`,
  with two `verification_result_missing` warnings at `:467-476`), and the bundle was packed straight
  after.
- **The exit codes disagree.** The report's `securing_pass_exit_code` is 1 (`:138`), while `DIAG2` says
  `exit_code: 143` (SIGTERM). One is the wrapper's and the other the reader's.
- **The fork reports a misleading speed.** In the securing pass, "Extraction speed" and "Elapsed" span
  all 5 reads but divide by one track's length. Track 11 reads "1.4x" when each read ran at about 7x
  (`ALB/.platterpus-securing-pass.txt:104-105`).

#### 4. The known fixes this disc exercises

##### (6) Error positions in the report: **PROVEN** in the report, **NOT EXERCISED** in the EAC-layout log (by design)

**In the report.** `disc.error_positions` (`ALB/.platterpus.json:811` onward) carries, per track:

- the positions;
- `error_positions_dropped`;
- `count_agrees_with_counters: true` for all 18 tracks.

Its values match the cyanrip log and `DIAG1`:

| Track | Skips | Positions |
|---|---|---|
| 13 | 1 | LSN 158236 |
| 15 | 1 | LSN 208410 |
| 17 | 28 | (listed) |
| 18 | 1000 listed + 1076 dropped = 2076 | (first 1000 listed) |

The `error_positions_reported` warnings name the tracks, the counts and the first sectors
(`:432-450`).

**Defects:**

- **(a) The count states the list, not the counter.** Track 18's `skips` is 1000 (`:5491`) and its
  message says "cdparanoia reported … 1000 skip(s)". paranoia reported 2,076; the remaining 1,076 are only
  mentioned afterwards as "did not list".
- **(b) Positions repeat.** Track 17's 28 entries cover 16 sectors, and track 18's 1000 cover 287. The
  message prints "238003, 238003".
- **(c) The securing pass's positions never reach the structured report.** For example, track 12's skip
  at LSN 151669, which the album pass did not have. The block "describes album pass" (`:812`).
- **(d) The EAC-layout log shows no positions.** This is deliberate until the handshake agrees a wording
  (`CHANGELOG.md:94-95`).

##### (3) "No errors occurred" over an unclean read: **NOT EXERCISED** for its trigger, **PROVEN** for the skip half

**The trigger did not occur.** The fix fires when an error line sits above `Ripping errors: 0`
(`ripper_error_lines_under_zero_summary`), and no pass here summarised 0 errors: the album pass's footer
reads 2106 (`ALB/.log:1526`) and the securing pass's reads 3390 (`.platterpus-securing-pass.txt:739`).

**The skip half is proven.** The fix's companion, `unverified_paranoia_skips`, fired for tracks 13, 15,
17 and 18 (`ALB/.platterpus.json:462-465`). The EAC-layout "Read stability" line names them
(`(EAC-compatible).log:323`). Nowhere reads clean: `health_status` is "2106 ripping errors"
(`.platterpus.json:481`), and the EAC disc line says "2106 ripping errors" and "Some tracks could not be
verified" (`(EAC-compatible).log:316-318`).

**The 2026-10-04 regression is also fixed.** "Copy OK" no longer appears over a stopped securing pass's
tracks; they now read "Copy NOT confirmed" (`(EAC-compatible).log:214-296`).

##### Paranoia counters: **PROVEN**

- **The album pass.** Its per-track `paranoia_all_reads` sum to the disc totals exactly: READ 554629,
  VERIFY 1025708, FIXUP_ATOM 56958786, SKIP 2106 (`DIAG1`; `ALB/.log:1518-1524`;
  `.platterpus.json` `paranoia_counts`).
- **The securing pass under `-Z`.** Its per-track blocks say "Scope: the last of 5 reads; the disc totals
  below sum all of them" (`.platterpus-securing-pass.txt:145`). Summing `DIAG2`'s per-track
  `paranoia_all_reads`, partial track 18 included, gives the footer exactly: READ 933705, SKIP 3389,
  FIXUP_DROPPED 4 (`:730-737`).

**Not exercised:** Platterpus does not read the `-Z` all-reads counters into the report. No securing read
was kept, so the report describes only the album pass.

##### The damaged disc's error and skip reporting: **PROVEN**, with wording defects

**Consistent across the ripper's surfaces:**

- the cyanrip log, "Track N read with errors" for 13, 15, 17 and 18, the footer, and "Read stalls: 261 …
  longest 77s";
- the `-j` record;
- the report's issues `ripper_read_stalls`, `error_positions_reported`, `unverified_paranoia_skips` and
  `heavy_reread`;
- the EAC-layout status block.

`READERR` is 0 everywhere: the drive never returned a hard error, and every error was a paranoia skip.

**The defects:**

- (6)(a) and (6)(b) above;
- the ladder's "the drive reported no read errors" (`APP:10226`);
- "you cancelled";
- track 11's verified re-read, which goes unreported.

#### 5. Proposed fix

##### The bound (Platterpus owns it: the policy, the UI, the swap)

**1. Run the securing pass one track at a time.** Use `-l N` per invocation, or else swap each track a
stopped pass finished. The fork's footer already names the only partial file: "Partial files: 1 track
(18)" (`.platterpus-securing-pass.txt:741`). Then:

- run `reread_supersedes` on every finished track;
- extend `_record_unfinished_refix` (`rip_worker.py:3428-3496`) to swap through the same path as
  `rip_worker.py:3193-3212`.

A stop on track 18 then keeps track 11's verified read.

**2. Give each track a time budget for re-reading.** Derive it from that track's album-pass read: for
example, stop re-reading track N once its re-reads have used `max(5 × track length, 2 × its album-pass
read time)`, and spend at most a rip-level total above the pre-rip ceiling. On reaching the budget, keep
the best read so far, record `stopped_reason: "time_budget"`, and move to the next track. Apply the same
budget to the chase loop (`verified_read_run.py:138-177` has the `cancelled` hook; add a clock check
beside it).

**3. Skip the chase when no read can be verified.** Add a gate before `plan_chase` returns `run=True`.
When the album read and every securing read of the track carry paranoia skips, it is an unreadable area,
not a near miss. Record `CHASE_SKIPPED_UNREADABLE` instead of spending 5 reads. Tracks 13, 15, 17 and 18
would be skipped. Tracks 12, 14 and 16 stay eligible: they had no skips, and track 11 shows that kind of
track can verify.

**4. Ask the user.** Once a track exceeds its budget, the status line offers "Track 18 has taken 2 h 22 m
and has 2,076 unreadable spots; more reads are unlikely to help: [Stop re-reading this track] [Keep
trying]". Attribute cancels properly: the user, the test run, or the time limit.

##### The fork's side (optional)

- **`--prefer-accuraterip-match`** is already on the fork's tip (`cyanrip@6e2ca21`, not in `.26`). It
  keeps an AccurateRip-matching read at the repeat limit. Send it once a released build carries it.
- **A track-level deadline flag**, which the fork could add. It would end the `-Z` loop at a read
  boundary with a distinct line, such as "Done; (time limit of N s reached; …)", and a distinct
  `secure_rip_state`. That would let Platterpus stop without SIGTERM, and the log would never blame the
  disc for the operator's limit (the same concern as `src/cyanrip_main.c:1722-1738`).

Neither is required for the bound above: SIGTERM between per-track invocations is already clean.

##### What the report should say when no read can be verified

Per track: **"Not verified: unreadable on this drive."**

- Reads made, each with its duration and CRC. For track 18: one album read of 2 h 22 m, then the
  securing reads.
- "No two reads agreed".
- AccurateRip: matched on frame 450 only, confidence 28.
- paranoia skips: 2,076, at sectors 242,828 to 259,798, given as times within the track, and the count
  from the counter, not the list.
- Why re-reading stopped: the time budget, the repeat limit, "you stopped it", or "the test run stopped
  it".
- Which read the file holds.
- Whether any read was verified, so that track 11 would read "a re-read matched AccurateRip (confidence
  29) and was kept".

Disc level: "Track 18 cannot be read reliably by this drive; another drive or cleaning the disc may
help", and no "about 1h" estimate left standing.

##### Tests that need no drive

**Platterpus** (the suites exist: `tests/test_verified_read_chase.py`,
`tests/test_rip_worker_verified_read.py`, `tests/test_securing_pass.py`,
`tests/test_auto_fix_convergence.py`):

1. Commit this bundle's `ALB/.log` and `.platterpus-securing-pass.txt` as fixtures.
2. With a fake `_rip_once` returning `success=False` and a temporary folder holding track 11's FLAC,
   assert that track 11 is `replaced`, `replaced_because=accuraterip`, and that tracks 12 to 17 are
   recorded unswapped.
3. With `plan_chase` over the fixtures, assert that tracks 13, 15, 17 and 18 are skipped as unreadable
   and that 12, 14 and 16 are eligible.
4. With `run_chase`, a `read_once` that never verifies, and an injected clock advancing 2 h per read,
   assert it stops at the budget with `stopped_reason: "time_budget"`.
5. Write golden tests of the report sentences and the EAC-layout lines, built from these fixtures.

**Fork:** extend `tests/stall.c` or `tests/badsector.c` with a fake slow reader, and assert that the
deadline ends the `-Z` loop at a read boundary with the new line and state.

**Acceptance script:** section F's wait should take the run estimate's ceiling, or the rig should run F
on the reference disc and test the damaged disc in its own section, with the bound above as the thing
graded.

## Appendix I. Runs 3 and 4 findings: discs 3 and 4, 2026-10-22

Word for word as written on 2026-10-26, from the bundles `20261022t114515z` and `20261022t215702z`.

### Full runs of 2026-10-22: Platterpus 0.7.112 with ripper `.26` (ca0f097)

Read-only analysis. Nothing in either bundle was executed. All times are UTC. The app log and the rip logs stamp local time (UTC-04:00), which is converted here.

Sources read against: Platterpus `origin/main` bba81563 (the run's embedded `script_source` is byte-identical to `src/platterpus/rig_scripts/fullacceptance.txt` there), and the fork `origin/platterpus-fork` fc73b4d (`docs/handshake/STATUS.md`) with `.26`'s source at ca0f097.

#### Path legend

Every citation is bundle-relative. `R1:` means `20261022t114515z/` and `R2:` means `20261022t215702z/`. The aliases below each stand for a bundle-relative path.

| Alias | Bundle-relative path |
|---|---|
| `FA1` | `album/full acceptance_ angle_bracket 20261022t11__terpus-fork-gca0f097/full acceptance∶ angle‹bracket 20261022t114515 platterpus-fork-gca0f097 CD3` (+ `.log`, ` (EAC-compatible).log`, `.platterpus.json`, `.platterpus-securing-pass.txt`, `.platterpus-verified-read.txt`, `.cue`) |
| `SR1` | `album/secure reread 20261022t114515 platterpus-fork-gca0f097/secure reread 20261022t114515 platterpus-fork-gca0f097 CD3` (+ the same suffixes, and `.platterpus-addendum.txt`) |
| `FA2` | `album/full acceptance_ angle_bracket 20261022t21__terpus-fork-gca0f097/full acceptance∶ angle‹bracket 20261022t215702 platterpus-fork-gca0f097 CD4` |
| `SR2` | `album/secure reread 20261022t215702 platterpus-fork-gca0f097/secure reread 20261022t215702 platterpus-fork-gca0f097 CD4` |
| `TA1_2` | `album/timing A1 20261022t215702 platterpus-fork-g5f1d036/timing A1 20261022t215702 platterpus-fork-g5f1d036 CD4.log` (`TA2_2` is the same for A2) |
| `DM1` | `album/derived mp3 20261022t114515 platterpus-fork-gca0f097/derived mp3 20261022t114515 platterpus-fork-gca0f097 CD3.platterpus.json` |
| `APP` | `session/artifacts/02platterpus/log.txt` |
| `TR` | `session/run/transcript.txt` |
| `REP` | `session/run/report.json` |

#### 0. The two runs are not of the same disc

The brief says the two runs read the same disc. They did not. They read **two different discs of one 4-CD release**:

| | R1 (11:45:15Z to 14:42:05Z) | R2 (21:57:02Z to 23:34:41Z) |
|---|---|---|
| `-c` sent | `3/4` (R1:FA1.log:2) | `4/4` (R2:FA2.log:2) |
| Disc number | 3 (R1:FA1.log:25-26) | 4 (R2:FA2.log:25-26) |
| DiscID | `bkyFFk2LvIJXMj3E1Is2rA8Rj9U-` (R1:FA1.log:29) | `rBin7wC6wjdr7ZsrLr.6j6rYAkA-` (R2:FA2.log:29) |
| AccurateRip ID | `002086bf-0189efd1-f80d8b10` (R1:FA1.log:34) | `0024d7eb-01b5ecd5-d30e6e10` (R2:FA2.log:34) |
| Total time | 57:47.65 (R1:FA1.log:37) | 61:34.30 (R2:FA2.log:37) |
| Platterpus medium match | "medium 3 of 4" (R1:FA1.platterpus.json, `disc.medium_detail`) | "medium 4 of 4" (R2:FA2.platterpus.json) |
| File names | `… CD3.*` | `… CD4.*` |

The r16 folders are named after each DiscID's first four letters: `Unknown disc (BKYF)` in R1 and `Unknown disc (RBIN)` in R2.

**Consequence:** comparing the runs' per-track checksums, AccurateRip results, pregaps, ISRCs or CTDB results tests nothing about consistency, because every one of them is a property of the medium. Section 3 therefore checks consistency **within** each run, where every disc was read 2 to 15 times. It then lists every difference between the runs and says which ones come from the medium.

#### 1. Which disc

**Release.** MusicBrainz `53d0f596-95a3-4e60-b4aa-09f5f7532b1e` (R1:FA1.log:30, R2:FA2.log:30). That is *Roots Music: An American Journey* (Various Artists, Rounder 11661-0501-2, barcode 011661050129, US, 2001-10-09), four CDs of 18, 18, 16 and 16 tracks.

The title comes from a read-only MusicBrainz web-service lookup made on 2026-10-26. The label, catalog number, barcode and date also appear in the `-a` argument at R1:FA1.log:2.

MusicBrainz lists `bkyFF…` under medium 3 and `rBin7…` under medium 4. Each of those media also carries a second disc ID.

| Property | Disc 3 (R1) | Disc 4 (R2) | Evidence |
|---|---|---|---|
| Track count | 16, all audio | 16, all audio | R1:FA1.log:27 and R2:FA2.log:27; CDDB IDs end in `0x10`; every `-j` record has `cd_tracks: 16` with `data_ripped: false` |
| TOC | Track 1 at sector 0; track 16 runs 245135-260089 | Track 1 at sector 0; track 16 runs 258525-277079 | R1:FA1 (EAC-compatible).log:38-57; R2:FA2 (EAC-compatible).log:38-57 |
| CD-R? | **Not determined by the drive** | **Not determined by the drive** | See below |
| Enhanced CD | No | No | No data track in the TOC, `cd_tracks` or the `-j` records |
| CD-TEXT | None reported by libcdio | None reported by libcdio | R1:FA1.log:17; R2:FA2.log:17; every `-j` record has `cdtext.status` "none reported by libcdio" |
| Pre-emphasis | None, all 16 tracks | None, all 16 tracks | R1:FA1.log:78 and the other track blocks; `-j` `preemphasis: "none"` on all 118 track entries read |
| Hidden track before track 1 | No | No | Track 1: `Pregap source: lead-in`, 150 frames, `Start LSN: 0` (R1:FA1.log:93-94; R2:FA2.log:97-98) |
| AccurateRip | Found; per-track maximum confidence 23-24 | Found; per-track maximum confidence 25-28 | R1:FA1.log:35; R2:FA2.log:35 |
| CTDB | In CTDB with 5 entries: best confidence 52, total 56 | In CTDB with 4 entries: best confidence 65, total 68 | R1:SR1.platterpus.json:2657-2664; R2:FA2.platterpus.json:2248-2255 |
| Disc ISRCs | None on any track, even after 200 Q frames | Read on 13 of 16 tracks (all but 4, 8 and 15) | Section 3c |

**CD-R.** The `Recordable:` line reads `unknown (profile 0xffff is not a CD profile)` on both discs (R1:FA1.log:16; R2:FA2.log:16).

- The same value appears on The Police disc in the 2026-10-21 bundles, so this drive, or libcdio's `mmc_get_disctype`, never reports a CD profile. On this rig the line cannot answer the question.
- The other evidence points to a pressed CD: AccurateRip confidence 24-28, CTDB entries that match, and MusicBrainz's format "CD".

#### 2. Every failed step

No failed step comes from a fork defect: `.26` did what its contract says on every path the runs reached. The counts in `REP` are R1 pass 480, fail 4, unreachable 1, info 12; and R2 pass 481, fail 2, blocked 1, unreachable 1, info 12.

R2's MANIFEST says "3 FAILURE(S)" (R2:MANIFEST.txt:37), which counts the blocked step as a failure. Its own verdict line keeps them apart (R2:MANIFEST.txt:39).

| Run | Step | What failed | Cause | Owner | Both runs? | Tracked? |
|---|---|---|---|---|---|---|
| R1 | L726 `expect-album-audit` (section F) | "completion warned: … 1 ripping errors" (R1:TR:457-458; R1:REP:2042) | **Disc and script.** Track 16 has a real paranoia skip at LSN 248743 (R1:FA1.platterpus.json:1242). Its kept read is unverified, and the chase found no verified read (R1:FA1.platterpus.json:1371-1373). The product's warning is correct. The script asserts a clean self-audit on a disc that will not read clean, although its own comment says read instability is "deliberately not graded" (`fullacceptance.txt:686-689`). `grade_album_audit` excuses only the open-round warning. | Platterpus (script or grader) | No. R2's L726 fails for another reason. | No |
| R1 | L730 `expect-cover-art` (F) | "the report says 0 file(s) took the cover; the files hold 16" (R1:TR:465-466) | **Platterpus defect: a race.** See the note below the table. | Platterpus | No. R2's L730 is blocked and its L910 passes (R2:TR:673). | No |
| R1 | L910 `expect-cover-art` (J) | "…0 file(s)…; the files hold 2" (R1:TR:683-684) | Same race: graded at 12:30:55Z (R1:APP:18410), result recorded at 12:31:55Z (R1:APP:18501-18502). | Platterpus | Failed in R1 only. In R2 the cover result landed about 50 s after post-rip began, before grading. | No |
| R1 | L1274 `expect-album-audit` (N) | "completion warned: … 2 ripping errors" (R1:TR:1116; R1:REP:4889) | **Platterpus defect.** The chase replaced track 16 with a read AccurateRip verifies (R1:SR1.platterpus-addendum.txt:20-25), and the verdict is "Bit-perfect: all 16 tracks" (R1:SR1.platterpus.json:269). Yet `health_status` stays "2 ripping errors" (R1:SR1.platterpus.json:657), counted from the superseded `-Z` read. `rip_audit.py:425-429` warns on any `health_status` other than "No errors occurred". The EAC-layout log likewise prints "All tracks accurately ripped" over "2 ripping errors" (R1:SR1 (EAC-compatible).log:292,294). | Platterpus | No. R2's L1274 fails for another reason. | No |
| R2 | L726 and L1274 `expect-album-audit` | "cue_integrity warned: … track 10: cue USZO10001709 vs sent USZ010001709" (R2:TR:450-451, 1103-1104) | **Platterpus defect.** See the note below the table. | Platterpus | Yes, both steps in R2. R1's disc carries no ISRCs, so it cannot show this. | No |
| R2 | L730 `expect-cover-art`, **blocked** | "none was fetched: network HTTP 500" (R2:TR:458-459) | **Rig/network.** The Cover Art Archive returned HTTP 500 for the front cover (R2:APP:27591; R2:FA2.platterpus.json:2466-2472). Booklet images from the same archive did save 54 s later (R2:APP:27603), so the message "could not reach the Cover Art Archive" (R2:APP:27604) overstates it. | External | No | The class is recorded in TASKS R17 (CAA HTTP 500 on 2026-10-14) |
| Both | L571 `expect-offset-refusal`, unreachable, not a failure | The drive is in AccurateRip's list (R1:TR:387, R2:TR:381) | Rig | n/a | Yes | Yes: TASKS, "Permutations the acceptance test still does not run, (a)" |

**The cover-art race (R1 L730 and L910).** The FLACs already carry the front cover when the grader reads them.

- The report's `cover_art` block, with `embedded_count`, is written only after Platterpus downloads this release's 23-25 booklet scans. That takes 60-120 s here.
- The step graded at 12:18:09Z (R1:APP:17625). The result was recorded as "late" at 12:19:40Z (R1:APP:17718-17719), and the report now says 16 (R1:FA1.platterpus.json:2660).
- `settle_state()` (`uiscript/artifact_grading.py`) waits for `outcome` and `verification.gates`, not for `cover_art`.
- The defect is latent. It shows on a release with many CAA images, and The Police release does not have them.

**The cue ISRC check under `--prefer-disc-isrc` (R2 L726 and L1274).**

- `--prefer-disc-isrc` was sent (R2:FA2.platterpus.json:472), so the files and the cue carry the disc's code `USZO10001709` (R2:FA2.log:792; R2:FA2.cue:77).
- MusicBrainz has `USZ010001709`, with a digit zero where the disc has a letter O.
- `cue_validate._check_isrcs` compares the cue with the ISRCs **sent**, not with those **written**. The report already knows the difference: `agreement: "differ"`, `written: USZO10001709` (R2:FA2.platterpus.json:568-572), and the `isrc_disc_differs` info issue (:313).
- The fork's behaviour is correct.

TASKS R20 covers ISRC provenance, not this check.

##### Defects that failed no step

1. **The derived-file verify runs before the transcode writes its files.** It gives up after about 60 s while the transcode waits behind the cover-art and booklet fetch.
   - R1: MP3, WavPack and WAV all report "not run — no … files found to verify". For example, the verify was skipped at 12:38:35Z (R1:APP:18991) and the transcode wrote its files at 12:39:26Z (R1:APP:18999). WavPack and WAV: R1:APP:19336/19342 and 19679/19686.
   - R2: MP3 is the same (R2:APP:29047). WavPack and WAV ran and passed, because their transcode finished first (R2:APP:29373-29384).
   - So no derived file was verified in R1, and no MP3 in either run. `expect-verification` passed every time, because the gate honestly says "not run". This is Platterpus's, and it is untracked.
2. **The verified-read chase's `-j` records are missing from the bundle.** The chase's 10 cyanrip invocations in R1 each passed `--diagnostics` (for example `cyanrip-diagnostics-20261022T121023Z.json`; R1:FA1.platterpus-verified-read.txt:2). None is in `ripperdiagnostics/`, and the MANIFEST says "missing none" (R1:MANIFEST.txt:33-34).
   - The positions of the skips in chase reads 1, 3 and 4 of SR1 and in read 1 of FA1 are therefore lost.
   - TASKS R9 fixed this for the securing pass only. The chase path is untracked.
3. **SR1's track 16 mixes two reads.** Its CRC, 3EACDE74, and its AccurateRip result come from chase read 5, but its speed (0.55x), elapsed time (362.25 s) and paranoia counters (`SKIP: 1`) come from the superseded `-Z` read (R1:SR1.platterpus.json:2596-2636; R1:SR1.log:1424-1430). The kept read ran at 4.8x in 41.53 s with no skip (R1:SR1.platterpus-verified-read.txt:822-823, 840-901). The EAC-layout log repeats the mix: "Extraction speed 0.6 X … 0:06:02 … Copy CRC 3EACDE74" (R1:SR1 (EAC-compatible).log:282-286).
4. **`expect-pregaps-agree` (P4) misses two kinds of log.** It runs before the P5 timing rips, so in R2 it reported "11 logs … identical" (R2:TR:1971-1974) without seeing the `.25` logs that omit track 5's pregap (section 3b). It also sets aside any log whose `Gaps:` block holds an `unknown` line (R1:TR:1970-1974, three logs).
5. **Minor.** `distinct_reads_seen: 4` counts only the `Repeating ripping` values, but each securing pass read five distinct values (R1:SR1.platterpus.json:1594; R1:FA1.platterpus-securing-pass.txt:60-68,108). `expect-accuraterip` labels track 16's one-frame (frame 450) match `offset-variant` (R1:TR:459-460).

#### 3. Consistency

##### 3a. Per-track checksums and AccurateRip, within each run

**R1, disc 3.** Every read was parsed: album logs, both securing passes, all 10 chase reads, and both `.25` and `.26`.

- **Tracks 1-15:** one CRC per track across every read (track 1 has 15 reads, track 2 has 11, track 3 has 6, tracks 4-15 have 2 each). Every read is AccurateRip v1 and v2 accurate, at the same values. Examples: track 1 `C2691C02`, v2 `E03D140D` at confidence 24 (R1:FA1.log:95-101); track 15 `3ECA7369`, v2 `0AA80B51`.
- **Track 16:** 14 reads produced **14 different CRCs**. Thirteen are unverified and match only on frame 450 (`F81ED370`, confidence 24). One, chase read 5 of SR1 (`3EACDE74`, v2 `B337E973` at confidence 24), is verified (R1:SR1.platterpus-verified-read.txt:831-835). The other 13 reads and where they appear:
  - FA1: `8B597546` (R1:FA1.log:1275), `60CB92F8` (R1:FA1.platterpus-securing-pass.txt:108), and five chase reads, none verified (R1:FA1.platterpus-verified-read.txt:101,284,465,646,827).
  - SR1: `0FC7769D` (R1:SR1.log:1390), `808A9514` (R1:SR1.platterpus-securing-pass.txt:108), and chase reads 1-4.
- Each of the three `-Z` passes on track 16 hit the repeat limit with every read different: "at most 1 read agreed" (R1:SR1.log:1350; both securing passes at :68). Track 16 is physically marginal on this disc.

**R2, disc 4.** All 16 tracks have one CRC each across every read (track 1 has 15 reads, track 2 has 11, track 3 has 6, the rest 2), all AccurateRip accurate, with no securing pass and no chase. "Tracks ripped accurately: 16/16" (R2:FA2.log:1348); "Ripping errors: 0" (R2:FA2.log:1355).

##### 3b. Pregaps

`.26`'s two-search clause ("two searches read %i and %i frames", `cyanrip_log.c:439-440`) printed **nowhere**: every `Pregap source:` line is `lead-in` (30) or `sub-channel (not signalled by TOC)` (98). Wherever both searches ran, they agreed.

**R1** has 27 cyanrip invocations: 25 by `.26` and 2 by `.25`.

- All 27 `Gaps:` lists agree on 75, 110, 157, 132, 140, 110, 140, 178, 183 and 108 frames for tracks 3, 4, 5, 6, 8, 9, 10, 13, 14 and 15 (R1:FA1.log:46-56).
- In 3 of the 25 `.26` invocations, track 16's search **failed**, and the list says so: "pregap of track 16 unknown (sub-channel CRC mismatches)". This is in `cancel me … CD3.log:57`, `derived wavpack … CD3.log:57` and `r16deemphon/Unknown disc (BKYF).log:54`.
- The other 22 list no pregap for track 16. All 14 of track 16's own blocks print 0 frames.
- No track's measured value varied.

**R2** has 15 invocations: 13 by `.26` and 2 by `.25`.

- All 13 `.26` lists are identical and include `175 frame pregap in track 5` (R2:FA2.log:49; track block R2:FA2.log:411).
- **Both `.25` lists omit track 5** (R2:TA1_2:44-47, R2:TA2_2:44-47). Same disc, same run.

##### 3c. The disc's ISRCs (`Disc ISRC:` lines)

**R1, disc 3.** Every `.26` read of every track says "none (libcdio returned none, also after reading 200 Q frames of the track, none an ISRC frame)" (R1:FA1.log:79 and the other blocks). The two `.25` timing logs say "none (libcdio returned none)". So the drive's Q frames carry no ISRC on this disc. The files carry MusicBrainz's codes for 9 tracks.

**R2, disc 4.**

- `.26` read codes for tracks 1-3, 5-7, 9-14 and 16 (R2:FA2.log:83, 162, 241, 398, 477, 556, 713, 792, 871, 950, 1029, 1108, 1266) and "none … 200 Q frames" for tracks 4, 8 and 15 (R2:FA2.log:320, 635, 1187).
- The codes are consistent across every read of each track. For example, track 1 has `USRO28102801` in all 13 `.26` reads.
- **`.25`, in the same run, read none for tracks 1-3** (R2:TA1_2:80,159; the same in A2).
- Disc against MusicBrainz:
  - Track 10: disc `USZO10001709` (letter O), MusicBrainz `USZ010001709` (digit zero).
  - Track 15: the disc has none and MusicBrainz has `CAW119901677`, which the files carry.
  - All other tracks agree.

##### 3d. Error positions (`-j` `error_positions`)

**R1.** Every position is a skip, and every one is on track 16, whose range is 245135-260089:

| Read | Positions (LSN) | Evidence |
|---|---|---|
| FA1 album pass | 248743 | R1:ripperdiagnostics/cyanrip-diagnostics-20261022T114605Z.json:55 |
| FA1 securing pass | 250438, 250364 | …120418Z-securingpass.json:55 |
| SR1 album pass | 250715, 251158 | …124948Z.json:55 |
| SR1 securing pass | 250401 | …134436Z-securingpass.json:55 |

- The positions vary from read to read but stay within LSN 248743-251158, about 48-80 s into the track.
- The report repeats the album-pass positions (R1:FA1.platterpus.json:406, 1242).
- Every other track and record is empty. The cancelled rip has `ripping_errors: 1` with no skip.

**R2.** Every record is empty, which is consistent with no errors.

##### 3e. CTDB per track

| Rip | Whole disc | Per track |
|---|---|---|
| R1 FA1 | `no_match` "at any alignment within ±5,879 samples" | Tracks 1-15 match (confidence 54-56); track 16 `differs` (CRC 26521651). R1:FA1.platterpus.json:2440-2459, 2627-2628 |
| R1 SR1, after the chase | `match`, confidence 52, offset 0 | All 16 match; track 16 at confidence 53 (CRC 0DF70A39). R1:SR1.platterpus.json:2657-2664 |
| R2 FA2 and SR2 | `match`, confidence 65, offset 0 | All 16 match at 67-68, with identical per-track CRCs in both rips. R2:FA2.platterpus.json:2248-2435 |

##### Every difference between the two runs

- **Caused by the medium:**
  - The disc itself: DiscID, TOC, length, AccurateRip ID, titles and ISRCs.
  - Every CRC and AccurateRip value.
  - AccurateRip confidence: 23-24 against 25-28.
  - CTDB: 5 entries at 52 against 4 entries at 65.
  - Pregap sets.
  - ISRCs: none against 13 of 16.
  - Track 16's damage, which only disc 3 has. It caused R1's securing passes, chases, skips and error positions, while R2 had none of these.
- **Caused by the run:**
  - Cover-art fetch: R1 succeeded but late; R2 hit HTTP 500 on F and was on time on J. This gives L730 fail against blocked, and L910 fail against pass.
  - Derived verify: 0 of 3 ran in R1, 2 of 3 in R2.
  - Cache probe: 140 sectors against 137 (R1:TR:1477; R2:TR:1475).
  - P5 timing ratios: 0.354 and 0.354 in R1 (R1:TR:2180-2182), against 0.197 and 0.193 in R2 (R2:TR:2180-2182). `.25` took about 698 s for tracks 1-3 on both discs, at roughly 1x; `.26` read at 2.5-6x.
  - Bundle size: 17 `-j` records and 136 files in R1, against 15 and 129 in R2 (MANIFEST:33, :48).

#### 4. The known fixes

| # | Fix | Verdict | Evidence |
|---|---|---|---|
| 1 | Second read on a disc AccurateRip doesn't know | **NOT EXERCISED** | Both discs are in AccurateRip (R1:FA1.log:35; R2:FA2.log:35) and `accuraterip_standing` is `in_database` (R1:FA1.platterpus.json:1433). The retries that did happen were triggered by `accuraterip` and `instability`, never by `second_read`. |
| 2 | Keep the read AccurateRip verifies at the repeat limit | **PROVEN** on Platterpus's chase (R7). The fork's `--prefer-accuraterip-match` is `.27` and **NOT EXERCISED**. | SR1 track 16: two `-Z` passes at the limit, then chase read 5 verified at v2 confidence 24 and was kept (R1:SR1.platterpus.json:1590-1642; addendum :20-25; EAC log :285-287; CTDB track 16 match). FA1: five chase reads, none verified, the first read kept and nothing falsely replaced (R1:FA1.platterpus.json:1371-1373). Faults beside it: L1274 (section 2) and defects 2 and 3. |
| 3 | No "No errors occurred" over an unclean read | **PROVEN** for a counted skip. The uncounted case is **NOT EXERCISED**. | FA1: `health_status` "1 ripping errors" (R1:FA1.platterpus.json:440); EAC log "Copy NOT confirmed … 1 ripping errors" (R1:FA1 (EAC-compatible).log:270-280); `unverified_paranoia_skips` issue (:431). The phrase is printed only on clean rips. The trigger the fix adds, a skip under `Ripping errors: 0`, did not occur: every skip was counted. EAC's "There were errors" wording is not built (lap 3 S11). |
| 4 | An Enhanced CD's data track | **NOT EXERCISED** | No data track on either disc. |
| 5 | The record says which checks ran | **PROVEN** | The gates read from results: `ctdb: "ran"` or "not run — CTDB verifies whole discs…", and `derived: "not run — no mp3 files found to verify"` (R1:DM1:1271). The gates are honest, and that honesty is what exposed defect 1. A check cut short was not exercised. |
| 6 | Error positions | **PROVEN** in R1; empty in R2, which is correct | Section 3d. The `-j` positions, the report's `disc.error_positions` and the issue text agree (R1:FA1.platterpus.json:406, 1242). Gaps: the chase reads' positions are lost (defect 2), and the EAC-layout wording is not built (S10). |
| 7 | CTDB per track and over offsets | **PROVEN** per track. The offset sweep is PROVEN for a no-match at every alignment. A **non-zero pressing offset is NOT EXERCISED**. | Section 3e. FA1 names track 16 alone as differing, and every match was at offset 0. |
| 8 | The disc's ISRCs | **PROVEN** | Disc 4: `.26` read 13 of 16 codes where `.25`, in the same run on the same drive, read none for tracks 1-3 (section 3c). Disc 3: "none … 200 Q frames" on all 16 tracks, which is the STATUS close's other branch. The Police disc, where EAC shows codes, was not re-read. |
| 10 | Pregap stability | **PROVEN on disc 4**, but its **close condition is unmet** | Track 5's 175 frames appear in 13 of 13 `.26` logs and 0 of 2 `.25` logs (section 3b). Disc 3 agrees everywhere. STATUS closes the item only on The Police disc reading 94 and 158 frames, and that disc was not run. Also first seen on a drive: `gaps-undetermined-pregap`'s `unknown` line, in 3 R1 logs (STATUS:12). |
| 11 | The log says whether the offset is AccurateRip's for the drive | **The report proves it; the log does not say it** | `read_offset_check: matches`, "+667, matches the AccurateRip drive database for PIONEER BD-RW BDR-209D", reconfirmed by AccurateRip on 15 of 16 and 16 of 16 tracks (R1:FA1.platterpus.json:1289-1294; R1:SR1.platterpus.json:1510-1515). The EAC-layout line is still bare "Read offset correction : 667" (R1:FA1 (EAC-compatible).log:22), awaiting lap 3 S12. |
| 12 | No "not in the database" for a disc AccurateRip holds | **PROVEN** | FA1's headline names the one-frame match (R1:FA1.platterpus.json:267). No report or EAC log in either run contains "not in the database". |
| — | `Accurate stream:` and `Recordable:` lines | **PROVEN** printed and parsed; `Recordable:` is uninformative | Both lines are in all 38 `.26` logs and absent from the 4 `.25` logs, which report `not_present`. The values are parsed (R1:FA1.platterpus.json:1306-1309). `Recordable:` is `0xffff` on every disc this rig has run, so it never answers CD-R. The EAC-layout line still says "Utilize accurate stream : (not reported by the ripper)" (R1:FA1 (EAC-compatible).log:18). |
| — | The derived MP3's ReplayGain, measured on the MP3 | **PROVEN, on the record only** | `measured_on: "the MP3 itself (ffmpeg ebur128, true peak)"`, 2 of 2 tracks and the album tagged, in both runs (R1:DM1:1289). The MP3s are not in the bundle and the app log prints no gain values, so the values cannot be checked independently. The MP3 decode check did not run in either run (defect 1). |

##### Fork STATUS items these runs bear on (for the fork's reading)

- `disc-isrc-read` (STATUS:15) meets its close condition: codes on disc 4, and "the drive's Q frames carry none" on disc 3.
- `gaps-undetermined-pregap` (STATUS:12) printed on a drive for the first time.
- `error-positions` (STATUS:21) is non-empty on a drive for the first time.
- `hardware-unverified` (STATUS:27): "a paranoia skip on a drive" now has evidence. There are 8 skips across 4 `-j` records.
- `repeat-limit-last-read` (STATUS:11): the limit was hit 3 times, each time with 5 distinct reads. The newest read was kept, so the clause correctly stayed silent.
- `subchannel-pregap-varies` (STATUS:20): supported on disc 4, but its stated close condition, The Police disc, is unmet.
- `recordable-medium-line` (STATUS:24): reads `0xffff` on three discs. Whether that comes from the drive or from libcdio's `mmc_get_disctype` parsing is not determinable from this evidence.
