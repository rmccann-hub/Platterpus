SUPERSEDED-BY: EAC-PARITY-PLAN-OF-RECORD-2026-10-26.md (https://claude.ai/artifact/ACChXwKyAGM9wvCTVjqDDo). Do not send this file.
REPORT-FOR: Platterpus session and cyanrip fork session
FROM: the claude-code-skills session, for the owner to pass on once, to both sessions
WRITTEN: 2026-10-26 01:45 UTC (the evening of 2026-10-25 in New York)
EXPIRES: 2026-12-31. Re-check EAC's version and the sources before relying on it after that.
SUBJECT: are we ripping as well as EAC? Checked against sources independent of both repositories

# EAC parity, checked independently

## The owner's words, verbatim

> "look, for this, both reops, they need to rip and be correrct, reporting on files is good, but
> ripping ir the goal. we need to report on that accuractly to confirm, that is what we do."

> "so since you are in the middle, are we ripping as good or better than EAC? based on
> evidence? id like to do better, but doing at least the same same is fine."

> "im not asking about what i gave you, what do you know independent of me about eac? thats a
> real scientific test is it not? go out and see."

This file goes with `report-for-both-sessions-2026-10-26-four-full-runs.md`, sent the same day,
which scores every track of the four Full runs of 2026-10-21 and 22.

## 1. What independent sources say about EAC

Each was fetched on 2026-10-26 from outside both repositories. A vendor's claim about its own
product is marked as such.

| Fact | Source | How strong |
|---|---|---|
| The newest version is **EAC 1.8, dated 14 July 2024** on EAC's news page (the program's own log header says 15 July 2024). 1.7 came the day before; 1.6 on 11 November 2020. Nothing newer is listed | [EAC: What's new](https://www.exactaudiocopy.de/whats-new/) | EAC's own site |
| **Secure mode** "reads every audio sector at least twice", or relies on the drive's C2 error data. On a read or sync error it reads the sector "until eight of 16 retries are identical", at most one, three or five rounds by the quality setting, so "bad sectors are read up to 82 times" | [EAC: Extraction Technology](https://exactaudiocopy.de/extraction-technology/) | EAC's own site |
| Below about 99.5% confidence, EAC "will tell the user where the (possible) read error occurred". These are its suspicious positions | the same | EAC's own site |
| A drive that caches audio returns the same bytes on every re-read; EAC overreads elsewhere to flush it. Secure mode with cache defeat runs at about "a third to a fourth of the drive's maximum speed" | the same | EAC's own site |
| **Test & Copy is a separate, optional mode** that reads each track twice. Secure mode alone doesn't do it | the same, and the forum thread below | EAC's own site, and users |
| EAC has an **"allow speed reduction during extraction"** setting | the dBpoweramp test's EAC settings; Platterpus's archived settings guide | Two sources, one a vendor's |
| **"Copy OK" and "No errors occurred" are EAC's own read check.** Users see them on tracks AccurateRip rejects. Re-reading can return the same wrong data every time | [Hydrogenaudio forum](https://hydrogenaudio.org/index.php?msg=484968), [another thread](https://hydrogenaudio.org/index.php?msg=681881) | Users, not EAC |
| **AccurateRip** says it is "the only Audio CD ripping technology which can verify extracted audio files are 100% free from errors"; its database was updated September 2026. Confidence is the count of matching submissions | [AccurateRip](http://www.accuraterip.com/); the forum thread above | Its own site; users |
| **CTDB** stores a whole-disc CRC32 and a recovery record of about 180 KB. It treats every pressing as one disc and skips HTOA and 5,880 samples at each end. It repairs one damaged stretch of about 30 to 40 sectors (about 75 on popular discs), only with every track present | [CUETools Database wiki](https://cue.tools/wiki/CTDB), edited 21 March 2026 | CTDB's own maker |
| **The only published damaged-disc comparison** is dBpoweramp's maker testing its own product: EAC 0.95 beta 4 against dBpoweramp R12, one scratched disc, four drives, AccurateRip as the judge, "errors not reported" as the worst outcome. dBpoweramp got 64 tracks right to EAC's 53, and EAC more often reported no error over a wrong track | [dBpoweramp: Secure Ripper Test](https://dbpoweramp.com/secure-ripper.htm) | A vendor's test of its own product, old, one disc |

**What couldn't be found from here:**
- the Hydrogenaudio wiki, which refused the request (HTTP 403);
- any recent, independent test of EAC, dBpoweramp, XLD, CUERipper and whipper;
- any study of how often secure rippers silently get damaged discs wrong.

### A setup guide isn't an authority: eacguide.github.io

The owner asked whether [eacguide.github.io](https://eacguide.github.io/) is the source of truth
for EAC, and for ripping. It isn't, for either:
- **What it is:** a community guide by one author, first posted on a file-sharing forum. Its
  repository has 4 commits, all on 2017-12-26, and none since. It's written for EAC 1.0 beta 3,
  and EAC is now at 1.8.
- **What it aims at:** a log that passes a tracker's logchecker. That checks how EAC was set up,
  not whether the audio is right.
- **Where it agrees with the EAC baseline:** secure mode, accurate stream on, C2 off, the offset
  taken from AccurateRip's list, gaps appended to the previous track, AccurateRip and the CTDB
  plugin on.
- **Test & Copy:** it uses it, and so did all three EAC baseline sessions. Every track in
  their logs (`platterpus@bba81563:output_reference/EAC_*/`) has a Test CRC. So the baseline
  already measured EAC at its strongest.
- **Where it's silent:** speed reduction, and what "Copy OK" means.
- **Where the evidence contradicts it:** it says that with these settings "the only possible
  errors would be with the CD itself". On 2026-10-21, the same disc in the same drive gave
  track 3 right with `.25` and wrong with `.26`. How the drive is read matters too.

No guide is the truth of ripping. The truth is the audio checked against other people's rips of
the same pressing: AccurateRip at high confidence, and CTDB. Ideally on more than one drive.
EAC's own pages say how EAC works; a guide says how one community sets it up.

## 2. Where we stand, on evidence

**The one disc with EAC runs to compare: the reference disc, The Police, on the same drive.**
EAC 1.8 was set up properly in all three sessions: Test & Copy, secure mode, accurate stream on, cache
defeat on, C2 off, offset +667, no overread.

| | EAC 1.8 | Platterpus |
|---|---|---|
| Tracks right per rip | 13, 12 and 11 of 14 | 12 or 13 of 14 in every one of 26 earlier rips; 13 of 14 in 2026-10-21's main rip |
| Track 3 | right in 1 of 3 | right in 9 of 26 earlier. On 2026-10-21: `.25` right 2 of 2, `.26` right 0 of 3 single reads, right after the securing pass |
| Track 5 | never right | right once (2026-10-07); not in 2026-10-21's run |
| "Copy OK" over a consistent wrong read | yes, every session | yes: 5 tracks on 2026-10-21 |
| A false "everything verified" | no | no |
| Re-reads until AccurateRip verifies | not documented | yes, in the securing pass's chase |
| Locates bad samples | yes, through its CTDB plugin | no |

**The verdict:**
- **On this one disc and drive, we are equal to EAC,** and a little ahead on the hard track and
  on album-level honesty.
- **We are behind on locating bad samples.**
- **On the other three discs, the damaged one included, there's nothing to compare against:**
  no EAC runs of them exist.
- **One risk could put us behind:** `.26` read track 3 wrong every time it read it once.

**The yardstick from now on** is the one the field uses, and the only published comparison
used. AccurateRip, at high confidence, decides right and wrong. Each track scores as right,
wrong but reported, or **wrong and reported as fine, the worst outcome**. On 2026-10-21 and 22,
no track was reported as verified when it wasn't. But 5 wrong tracks carried "Copy OK", 3 of
them with "confirmed across 3 secure re-reads", which a user reads as fine. That is the gap to
close.

Two findings change what "better than EAC" means:
- **Stepping the speed down is parity, not a lead.** EAC has the setting. A step-down that runs
  only when a track fails AccurateRip, and is recorded, is still worth building: it is how `.26`
  can keep its speed without losing track 3.
- **EAC may not be the strongest yardstick.** dBpoweramp's multi-pass mode with AccurateRip is
  what its own maker measured ahead of EAC. "Better than EAC" is the owner's floor; matching
  what dBpoweramp claims is the stronger aim.

## 3. Platterpus's documents that disagree with the sources

All at `platterpus@bba81563`. The fork's documents make no claim about EAC that the sources
contradict.

| Where | It says | The sources say | Change it to |
|---|---|---|---|
| `PLANNING.md:1359`, KDD-30 | "EAC's secure mode does a **Test** pass and a **Copy** pass and prints both CRCs", and `-Z N` "delivers the *same guarantee*" | Secure mode re-reads sectors, up to 82 times for a bad one. Test & Copy is a separate, optional mode reading each track twice | `-Z` gives Test & Copy's guarantee, that two whole reads agree, not secure mode's sector checks. Agreeing reads can still be wrong, as track 5 showed |
| `docs/archive/upstream-modification-investigation.md:213` | "EAC uses drive C2 pointers for fast error location" | EAC can use C2, or read twice instead. The EAC baseline ran with C2 off, as your settings guide advises | "EAC can use the drive's C2 pointers, when switched on" |
| `CHANGELOG.md:39` (0.7.112) | "…where EAC keeps the majority" | EAC documents a majority rule per *sector*, 8 of 16 reads identical. What it keeps for a *track* when that fails isn't documented; it flags the position | "…where EAC repeats a sector until 8 of 16 reads agree, and otherwise flags it" |
| `docs/eac-parity.md:1116` and `:1284` | "AccurateRip submission is impossible from Linux" | AccurateRip's own site doesn't say either way | Cite where this was established, or mark it unverified |
| `README.md:181` | speed reduction: "…not EAC's per-sector slow-down" | Nothing found says how EAC's setting works in detail | Cite it, or drop "per-sector" |

## 4. What to do, in order

**To stay at least equal:**
1. **Settle `.26` against track 3 before `.26` reaches the stable channel** (both; the fork
   first). When a track fails AccurateRip, re-read it at a lower speed, and record that the
   speed was lowered. Proof needs a few rips of tracks 3 and 5 on the drive.
2. **Ship the right read whenever one exists** (Platterpus). On 2026-10-21 a right read of
   track 3 was in hand and `-Z` converged on a wrong one, which shipped.
3. **Keep every right read when a pass stops, and bound a damaged disc's time** (Platterpus).

**To be better than EAC:**

4. **Never print "Copy OK" or "confirmed" over a track AccurateRip contradicts. Say "wrong", not
   "unverified".** A first-frame match proves the pressing, so a whole-track mismatch means the
   audio differs. EAC prints "Copy OK" there too, so this alone puts us ahead on the measure
   that matters most. Provable from the four bundles.
5. **Read track 5 right:** neither tool has done it reliably.
6. **Locate bad samples as EAC's CTDB plugin does.** It's large, and it's the one place EAC is
   ahead today.

**To be able to say it, beyond one disc:**

7. **Score every Full run the same way:** each track right, wrong but reported, or wrong and
   reported as fine. Put the counts at the top of the run's reading. Today the scoring is done
   by hand.

## 5. What waits for the owner

- **EAC 1.8 rips of the damaged disc (*Roots Music* disc 1) and disc 3,** on the same drive with
  the baseline's settings (secure mode, accurate stream, cache defeat, C2 off, offset +667,
  overread off), and with CTDB submission off. Ideally two of each, alternating with Platterpus
  rips of the same discs on the same day. This turns "equal on one disc" into a verdict on the
  discs where rippers differ.
  - **Keep Test & Copy on,** as the baseline had it.
  - **Stay on EAC 1.8, from exactaudiocopy.de only.** EAC's own changelog lists no change to
    secure mode after 1.0 beta 3, which added the CTDB plugin. The changes since then are to
    metadata, plugins and the burning component, plus one fix that matters here: on
    2015-04-09, EAC stopped "crashing EAC whenever a read error occurs". The bundled extra
    found was an eBay shortcut in the 0.99 prebeta 4 and 5 installers, in 2008 and 2009, and
    unchecking it skipped it. Nothing found ties adware to a 1.x installer. The paid part is
    the GD3 metadata plugin, added in May 2011, before 1.0 beta 3, so beta 3 carries it too.
    It costs money only after 10 test lookups. In the installer, keep AccurateRip and the CTDB
    plugin, and leave the metadata plugins and AcoustID off.
  - **EAC is closed source,** so no one outside its author can check what it does. That
    doesn't weaken the comparison: AccurateRip and CTDB judge both rippers' audio, not EAC.
    Run it on a machine or virtual machine kept for ripping.
- **A second drive,** when one is available.
- **A deeper search on the gaps in section 1,** as a research prompt the claude-code-skills
  session writes on request.
