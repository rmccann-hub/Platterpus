RESEARCH-FOR: Platterpus session and cyanrip fork session (via the owner)
FROM: the claude-code-skills session, research only (no repository changed, nothing posted)
WRITTEN: 2026-11-03 (UTC)
BUILDS ON: `scratch/EAC-PARITY-PLAN-OF-RECORD-2026-10-26.md` (sections 5, 6, Appendices A to C)
EXPIRES: 2026-12-31

# EAC review: the delta against the plan of record

The owner's ask, 2026-11-03: "review EAC (look for the golden standard version; I've read that the
newer versions prioritize payment and such, not sure if they are worse or better as far as what
they do or performance), review their procedure, online help, their files, their claims, the
facts, what people say."

**Every source below was fetched on 2026-11-03 unless a different date is given.** "Unverified"
marks anything I could not confirm from a source.

How it was done:
- EAC's own site (`exactaudiocopy.de`, every page linked from its menu), saved and read in full.
- **EAC's own files:** the 1.8 installer, downloaded from the site, hashed, and listed and unpacked
  with 7-Zip without running it. Its `News.rtf` (the full changelog, more detailed than the web
  page), `Documentation/EAC.txt`, `Documentation/FAQ.txt` and `Legal.rtf` were read.
- The Hydrogenaudio (HA) wiki and forum, CUETools' wiki, AccurateRip's site, cdHistory, and
  `OPSnet/Logchecker` at its current head.
- The owner's own EAC 1.8 log of the reference disc (`scratchpad/eac.txt`), read as primary
  evidence.

---

## 0. The short answer

1. **1.8 (15 July 2024) is still the newest EAC on 2026-11-03.** Nothing has been released
   since. HA's wiki footnotes it as "the Final Release, except for possible Maintenance and/or
   Critical Fix releases" (that footnote cites no source: unverified).
2. **No "golden" older version exists in any credible source.** No source found says a newer
   version rips worse. EAC's own changelog shows read-path fixes **after** 1.0 beta 3, the
   version the community guide uses:
   - 1.0 beta 6 fixed crashes on read errors;
   - 1.1 fixed "extraction problems with some LG drives";
   - 1.2 fixed a failure to find an AccurateRip checksum and a failure to find a read command.

   Beta 3 also pairs badly with the CTDB plugin (section 1.4). **Run 1.8. The plan's advice
   stands, with stronger reasons.**
3. **Nothing in 1.8 is paid except the optional GD3 metadata plugin** ($7.99 after 10 lookups,
   unchanged since 2011). The "payment" the owner heard of is donation links (Patreon, PayPal)
   and website advertising, not a paywall. What 1.x does add is **outbound submissions**, some on
   by default:
   - AcoustID fingerprints, pre-selected in the installer since 1.2;
   - CTDB, automatic for a new disc;
   - AccurateRip results.
4. **The plan's 34-row table misses about 30 extraction-relevant EAC features** (section 2,
   marked **NEW**). Five matter most:
   - **EAC has a per-track time budget** ("Skip track extraction after duration longer than n
     times realtime"), and options to skip a track on a read error and to cool the drive down.
     Row 5's "no time bound" gap has an EAC precedent to match.
   - **Lock drive tray during extraction** (on by default) bears on row 33.
   - **EAC says its own gap detection can be off by 2 to 3 sectors.** So EAC's pregap of 94 for
     track 9 (row 21) is not ground truth.
   - **EAC's "log checksum" is not a secret signature.** It is a keyed Rijndael-256 checksum
     whose key is public, so anyone can re-sign an edited log. Row 28 should say so.
   - **EAC reads pre-emphasis from the TOC only.** HA's comparison table credits cyanrip with TOC
     and subcode, which would make row 24 "Better" once tested.
5. **The owner's own EAC log shows two EAC behaviours to beat:**
   - "Copy OK" and "No errors occurred" printed over tracks whose Test and Copy CRCs **differ**
     (tracks 3 and 4);
   - "Track quality 100.0 %" with matching CRCs on a track that is wrong (track 5).

---

## 1. Version: is 1.8 still current, and is any version "golden"?

### 1.1 Current release (checked 2026-11-03)

| Fact | Source |
|---|---|
| Download page: "Exact Audio Copy V1.8 (including CDRDAO and Flac packages) last changed on 15.07.24". MD5 `24A110BA57928084283A944C7709FE06`, SHA-1 `CADB6987808DFA4F54CCD41205D7EF5236F29362` | https://www.exactaudiocopy.de/download/ |
| The installer from `https://www.exactaudiocopy.de/eac-1.8.exe` hashes to exactly those values (5,483,360 bytes; SHA-256 `205530cfbfdff82343858f38b0e709e586051fb8900ecd513d7992a3c1ef031b`). File version 1.8.0.0, "© 2024 by Andre Wiethoff", NSIS-3 Unicode installer | Downloaded and hashed 2026-11-03 |
| What's new: newest entry "July 14, 2024", the 1.8 fix for 1.7's empty-email metadata failure. No later entry | https://www.exactaudiocopy.de/whats-new/ |
| "Older Versions" offers 0.1b to 0.81b, 0.95b4, 0.99pb5, **1.0 beta 6**, 1.3, 1.6 and 1.8. **1.0 beta 3 is not offered** | https://www.exactaudiocopy.de/older-versions-for-download/ |
| `exactaudiocopy.org` serves an identical download page that links the same `.de` installer | https://exactaudiocopy.org/download/ |
| HA wiki infobox: "Stable release 1.8 (July 14, 2024)"; footnote: "1.8 is the Final Release, except for possible Maintenance and/or Critical Fix releases." **No source is given for "Final": unverified** | https://wiki.hydrogenaudio.org/index.php?title=Exact_Audio_Copy |
| Web searches for a 1.9 or any 2025 to 2026 release found none. Mirror sites carry 2026 "last modified" dates on 1.8 pages, but the version is still 1.8 | Searches on 2026-11-03 |

### 1.2 Which version the references treat as the reference

| Who | What version | Source |
|---|---|---|
| OPS Logchecker, head still `ca56547` (2026-05-31) on 2026-11-03 | Deducts 30 only for **"EAC version older than 0.99"** (`src/Logchecker.php:476` to `:497`). From 1.0 on, a missing log checksum is flagged. **No version from 0.99 to 1.8 is preferred or penalised** | `git ls-remote https://github.com/OPSnet/Logchecker.git` → `ca565479…` (2026-11-03); code read locally |
| RED's logchecker | **Unverified.** RED's rules and wiki are not public | — |
| HA wiki | Infobox gives 1.8. The "EAC Options" page is "intended for Exact Audio Copy v1.0 and newer". The "EAC Drive Options" page still says "Used EAC version: V0.99 prebeta 5" | https://wiki.hydrogenaudio.org/index.php?title=EAC_Options ; https://wiki.hydrogenaudio.org/index.php?title=EAC_Drive_Options |
| eacguide.github.io (the OPS-lineage guide) | Written for 1.0 beta 3 (2017) | https://eacguide.github.io/ |
| A current guide for 1.8, linked in an HA thread, February 2025 | 1.8 | https://hydrogenaudio.org/index.php/topic,127340.0.html |
| zexwoo's guide (2023) | "This guide was made for EAC version 1.8" | https://zexwoo.blog/en/posts/tutorials/eac-ripping/ |
| HA forum reply #3, 2018-03-22 | "The ripping engine has not changed since long before 2005." | https://hydrogenaudio.org/index.php/topic,115702.0.html |

### 1.3 Does any credible source say newer versions rip worse or differently?

**No credible source says so.** What exists:
- **One user report** on EAC's groups.io list said 1.8 gave errors on the last track of each CD
  where 1.6 did not. The posted log shows `Overread into Lead-In and Lead-Out : Yes` and
  `Make use of C2 pointers : Yes`. Either setting can produce errors at the end of the last
  track, so this is likely configuration, not a regression. Unverified, one report
  (https://groups.io/g/ExactAudioCopy/topics, listing read 2026-11-03).
- **Tweakers comments on 1.8** (Dutch) report freezes and the email-field metadata problem
  (https://tweakers.net/downloads/69284/exact-audio-copy-18.html). Anecdotal; 1.8 itself was the
  fix for the email problem.

**What EAC's own changelog (`News.rtf` inside the 1.8 installer) says changed in or near the read
path:**

| Version | Change, quoted | Matters because |
|---|---|---|
| 0.99 pb5 | "Fixed a small bug in some of the CRC calculations"; "Fixed a small bug when correcting an extracted block" | 0.99pb5 is the other "classic" version |
| 1.0 b2 | "Fixed bug of reading blocks larger than 64kb, which might have affected several devices/interfaces (USB)" | A read-path fix |
| 1.0 b3 | "Some drives were only extracting very slow, this should be fixed now (but in some rare cases, some drives might have started caching now)"; "Removed 'No use of null samples for CRC calculations'" | **Beta 3 itself changed read behaviour**, and warned that it might make some drives cache |
| 1.0 b4 | "Removed the (possible) expiration information dialog"; CTDB plugin enabled by default | Beta builds carried an expiry |
| 1.0 b6 | "Fixed a severe problem with crashing the application when a read error occurs" | Matters on damaged discs (already in the plan) |
| 1.1 | "Fixed extraction problems with some LG drives"; "Fixed a problem on CRC track submission"; "Fixed a problem on writing/appending log files" | **An extraction fix after beta 3.** The plan's "no change to secure mode after 1.0 beta 3" holds for secure mode's design, but not for the read path as a whole |
| 1.2 | "Fixed a very rare occuring problem of not finding an AR checksum for a given track"; "Fixed a rare occuring problem of not finding a read command"; "AcoustID plugin will be pre-selected on installation" | AccurateRip lookup fix; AcoustID on by default |
| 1.4 | Two command-line encoders | — |
| 1.5 | "Fixed a problem with Log file creation" | — |
| 1.6 | gnudb replaces freedb | — |
| 1.7 | freedb removed; **AccurateRip meta** built in as the default metadata source; flac and CTDB plugin updated | — |
| 1.8 | Fixes 1.7's empty-email metadata failure | — |

Source: `News.rtf` extracted from https://www.exactaudiocopy.de/eac-1.8.exe (file dated
2024-07-13), cross-checked against https://www.exactaudiocopy.de/whats-new/.

### 1.4 A concrete reason not to run 1.0 beta 3 (new)

CUETools' plugin page lists two problems with old pairings:
- **Bad recovery records:** "CTDB accepts the recovery record portion of a submission when the
  plugin reports the rip quality as 100%, but since EAC (V1.0 beta 2 through V1.0 beta 4)
  doesn't report suspicious positions to the plugin, the quality may be reported to CTDB as 100%
  when it is actually less than that. This causes CTDB to wrongly accept a recovery record which
  could be used to 'repair' future rips to match the bad rip."
- **Plugin versions:** versions through 2.1.5 work only with 1.0 b2 to b4, and 2.1.6 or higher
  needs 1.0 b5 or later. 1.8 ships plugin 2.2.6, the current release.

Source: http://cue.tools/wiki/CTDB_EAC_Plugin, last edited 28 June 2024.

### 1.5 "Prioritizes payment": what is paid, what is sent out

| Item | Paid? | Source |
|---|---|---|
| EAC itself | Free for non-commercial use; commercial use needs a licence. "No registration is necessary in this case… it is already the full version" | https://www.exactaudiocopy.de/registration/ ; https://www.exactaudiocopy.de/main-legal-limitations/ |
| GD3 metadata plugin | **Paid:** 10 test lookups, then "$7.99" lifetime. Unchanged since 1.0 b2 (2011). `GD3.dll` is in the 1.8 installer | https://www.exactaudiocopy.de/download/ ; installer listing |
| AccurateRip meta (default metadata since 1.7) | Free: "thank Spoon for providing the AccurateRip meta service free for all!" | https://www.exactaudiocopy.de/whats-new/ |
| Commercial SDK | "no longer developed nor licensed" | https://www.exactaudiocopy.de/commercial-sdk/ |
| Patreon and PayPal | Donation links on every page; the site carries "Advertisement / Anzeige" blocks | Every page of https://www.exactaudiocopy.de/ |
| **Anything else paid in 1.8** | **None found** | — |
| AcoustID plugin | Not paid, but **sends audio fingerprints by default**: "AcoustID plugin will be pre-selected on installation" (1.2). The owner's own log shows "Submitting 14 results to AcoustID … successfully submitted" | `News.rtf`; `scratchpad/eac.txt` |
| CTDB plugin | Submits a disc new to CTDB automatically. CTDB keeps a "Submission log, including user's IP addresses and CD drive model" | http://cue.tools/wiki/CTDB_EAC_Plugin ; https://cue.tools/wiki/CTDB (edited 21 March 2026) |
| Drive features | "Submit drive features after detection (but ask for permission)", on by default; it asks first | https://wiki.hydrogenaudio.org/index.php?title=EAC_Options |
| Installer contents | Also includes `INetC.dll` (an NSIS download plugin) and `Empty20.exe` and `empty461.exe`. Likely .NET 2.0 and 4.6.1 presence checks; **unverified** (the NSIS script was not recovered) | 7-Zip listing of `eac-1.8.exe`, 2026-11-03 |

**On the plan's Appendix B ("tie to adware"):** nothing new ties adware to a 1.x installer. The
eBay icons were in 0.99 prebeta 4 and 5, which EAC's own What's new confirms (31 January 2008):
"I have included a desktop and quick launch bar icon in the installer which link to eBay."

---

## 2. Feature checklist (extraction-relevant), from EAC's own pages and the HA wiki

EAC's own help is thin. Its Documentation page says: "No user documentation has been prepared, so
please check out some internet tutorials" (https://www.exactaudiocopy.de/documentation/). EAC's
"EAC related sites" page sends users to the "HydrogenAudio EAC Wiki", which has served since as
the de facto manual (https://www.exactaudiocopy.de/eac-related-sites/). The files bundled in 1.8
are old: `Documentation/FAQ.txt` is dated 2003-04-22 and `Documentation/EAC.txt` 2007-06-18
(installer listing).

**Key:**
- **In table** means the plan's section 5 has a row for it.
- **NEW** means it is not in the 34-row table. Section 6 of the plan names some NEW items as
  logchecker settings; they are marked "NEW (s6)".

Short names for sources:
- `ET` = https://www.exactaudiocopy.de/extraction-technology/
- `FAQ` = https://www.exactaudiocopy.de/faq/
- `FEAT` = https://www.exactaudiocopy.de/features-of-eac/
- `AFD` = https://www.exactaudiocopy.de/automatic-feature-detection-technology/
- `GAP` = https://www.exactaudiocopy.de/gap-technology/
- `OFF` = https://www.exactaudiocopy.de/offset-technology/
- `SYNC` = https://www.exactaudiocopy.de/track-synchronization-technology/
- `AR` = https://www.exactaudiocopy.de/accurate-rip/
- `TIPS` = https://www.exactaudiocopy.de/tips-specs/
- `HAO` = https://wiki.hydrogenaudio.org/index.php?title=EAC_Options
- `HAD` = https://wiki.hydrogenaudio.org/index.php?title=EAC_Drive_Options
- `HAG` = https://wiki.hydrogenaudio.org/index.php?title=EAC_Gap_Settings
- `HAC` = https://wiki.hydrogenaudio.org/index.php?title=EAC_and_Cue_Sheets
- `HAE` = https://wiki.hydrogenaudio.org/index.php?title=Exact_Audio_Copy
- `HACMP` = https://wiki.hydrogenaudio.org/index.php?title=Comparison_of_CD_rippers
- `NEWS` = `News.rtf` inside https://www.exactaudiocopy.de/eac-1.8.exe

### 2.1 Read modes and the read engine

| # | Feature | What it does (one line) | Source | Table? |
|---|---|---|---|---|
| F1 | Secure mode, three variants | One mode per drive type: C2 + accurate stream + no cache ("nearly burst mode speed"); accurate stream, no cache, no C2 ("up to half of maximum speed"); cache-defeating ("a third to a fourth of the drives maximum speed") | ET | In table (15), but the **variants are NEW** |
| F2 | Secure re-read rule | A sector with a read or sync error is re-read "until eight of 16 retries are identical", in 1, 3 or 5 batches of 16, "up to 82 times". If not ~99.5% sure, it reports the position | ET | In table (5) |
| F3 | Error recovery quality: Low / Medium / High | Caps the batches at 1, 3 or 5. HA recommends **Low**: "errors can occur with consistency and as such, more aggressive settings can result in errant data going unreported as being suspicious" | HAO | **NEW** |
| F4 | Fast mode | "Sector synchronized with 2 synchronization blocks of 23 total blocks"; finds no read errors | ET | **NEW** |
| F5 | Burst mode | No synchronization and no error checking. HA: with AccurateRip or a Test CRC "burst mode is completely secure". The log says "No errors occured" on every burst track (HA, Limitations) | ET; HAD; HAE | **NEW** |
| F6 | Paranoid mode | Oldest mode; reads every sector twice in small blocks; "should not be used, if one of the other secure modes works ok" | FAQ | **NEW** |
| F7 | Accurate stream | Unticked: EAC re-synchronizes every 27 sectors. Ticked: every 2 MB (HA forum, 2008). EAC claims identical extraction "is guaranteed" on such drives | ET; https://hydrogenaudio.org/index.php/topic,67834.0.html | In table (16) |
| F8 | Cache defeat ("Drive caches audio data") | Overreads so the cache holds other sectors (`ET`); HA's table says "Over-reading, FUA". If a caching drive runs without it, "the result will be the same as using 'Fast Extraction' (having no error detection)" (`TIPS`). Unticking accurate stream ticks it automatically (`HAD`) | ET; TIPS; HAD; HACMP | In table (17) |
| F9 | C2 pointers | Trust the drive's C2 to skip re-reads. EAC's FAQ answers two C2 cases with "C2 is not correctly implemented in some drives… turn off the C2 error correction". "Examine C2 Feature…" tests only whether the drive *can* flag an error | FAQ; HAD | In table (18) |
| F10 | Automatic feature detection | Tests accurate stream, caching and C2. "testing for caching will give some problems with drives that extract audio very slowly (below 4x speed)… assume that the drive does caching". It has a built-in drive database by model name | AFD | In table (16, 17) as values; **the detection routine is NEW** |
| F11 | Drive read command autodetect | Picks the read command (MMC1 and others). A wrong one can return silence | FAQ; HAD | **NEW** |
| F12 | "Big Endian" byte order; Swap channels | Fixes drives that return byte-swapped or channel-swapped audio | HAD | **NEW** |
| F13 | Spin up drive before extraction | For drives that "cannot rip the beginning of a track correctly" | HAD | **NEW** |
| F14 | Speed selection; "Allow speed reduction during extraction" | Slows the drive on read errors, then speeds it back up. FAQ: if speed stays low, use cool-down or untick it, "but of course then it won't read anymore that accurate on bad sectors" | FEAT; FAQ | In table (20) |
| F15 | **Skip track extraction on read or sync errors** | Skips the track at the first read or sync error; default off | HAO | **NEW** |
| F16 | **Skip track extraction after duration longer than n times realtime** | **A per-track time budget**; default off. HA: "the extraction of a 2-minute track would be aborted after 8 minutes" at n = 4 | HAO | **NEW**: the precedent for row 5's time budget |
| F17 | **Cool down the drive** every n minutes for n minutes | For long, hot rips of damaged discs | HAO | **NEW** |
| F18 | **Lock drive tray during extraction** | Default on, so the tray can't open mid-rip ("Otherwise this will always result in an aborted extraction") | HAO | **NEW**: bears on row 33 |
| F19 | Synchronize between tracks | Re-synchronizes at a track junction with no silence; matters on drives without accurate stream | SYNC; HAO | **NEW** |
| F20 | Interface | "Native Win32 interface"; ASPI no longer used | FAQ | **NEW** (not relevant on Linux) |
| F21 | Two EAC instances for two drives | Supported, "start both instances from different directories". Bug, HA 2025: two instances with different compression settings "randomly share those" | TIPS; https://hydrogenaudio.org/index.php/topic,127927.0.html | **NEW** |

### 2.2 Offsets, overread, silence, CRCs

| # | Feature | What it does | Source | Table? |
|---|---|---|---|---|
| F22 | Read offset by **EAC's own key-disc database** | Compares a reference CD to EAC's list of pressings, identified by matrix code. "YOU SHOULD USE THIS TEST ON TWO DIFFERENT CDS AT LEAST!" EAC's zero is its Plextor 14/32 at +679 | OFF; https://www.exactaudiocopy.de/list-of-included-reference-cds/ | **NEW** as a method (row 19 covers AccurateRip's list) |
| F23 | Read offset by **AccurateRip key disc** | AccurateRip configures the drive from a recognised disc and greys out the field. "This has to be done only once" | AR; HAO | In table (19) |
| F24 | Combined read/write offset | Offset for one reader and writer pair, for exact duplicates | FAQ (offset questions) | **NEW** |
| F25 | Overread into Lead-In and Lead-Out | Reads past the disc's ends so offset correction loses no samples. Set it only if the drive can (blowfish rule quoted at eacguide) | HAD; https://eacguide.github.io/ | **NEW (s6)** |
| F26 | Fill up missing offset samples with silence | Pads the first or last track to full length. "If the use of AccurateRip is desired, it is essential that this option is enabled" | HAO | **NEW (s6)** |
| F27 | Delete leading and trailing silent blocks | Drops whole 588-sample silent blocks; breaks AccurateRip | HAO | **NEW (s6)** |
| F28 | Null samples used in CRC calculations | Always on since 1.0 b3 (the option was removed) | NEWS | **NEW (s6)** |
| F29 | Normalize | Peak normalisation to n%; must be off for an exact copy | HAO | **NEW (s6)** |
| F30 | WAV compare tool | Compares two WAVs and lists missing or extra samples; used to find combined offsets and locate differing positions | TIPS; FAQ | **NEW** |

### 2.3 TOC, sub-channel, gaps, indexes, HTOA, flags

| # | Feature | What it does | Source | Table? |
|---|---|---|---|---|
| F31 | Detect Gaps (F4) | Finds index 00 by searching sub-channel Q. **"the deviance should be lower than 2-3 sectors"** | GAP | In table (21); **the tolerance is NEW** |
| F32 | Gap detection method A / B / C | "None of them is by used method better or worse… A is the fastest one and C the slowest". HA: "the difference between them is unknown" | FAQ; HAD | **NEW** |
| F33 | Gap detection accuracy: Inaccurate / Accurate / Secure | Inaccurate reads once; Accurate and Secure read several times. Try Secure "if you got gap length that are wrong only by some blocks" | FAQ; HAD | **NEW** |
| F34 | Gap handling: append to previous (default) / append to next / leave out | Where index 00 audio goes in per-track files. "Leave out" loses audio and breaks AccurateRip | HAG | In table (21), partly |
| F35 | Test Gaps On Silence (F3) | Reports the percentage of silence in each gap. **HA: "EAC can still report 100.0% silence for gaps that contain samples that are not null… not to be trusted!"** | HAG | **NEW** |
| F36 | Index-based copy (Alt+X) | Rips each index to its own file; used for HTOA | HAG; HAO | **NEW** |
| F37 | HTOA detection and rip | Track 1 shown "in red text if there's a large enough gap to contain HTOA"; rip it by image or index-based rip | HAG | In table (25) |
| F38 | Cue sheet styles | "Single WAV File"; "Multiple WAV Files With Gaps (Noncompliant)"; "…With Left Out Gaps" (PREGAP silence); "…With Corrected Gaps"; "Current Gap Settings" (an alias) | HAC | In table (25) as "image + cue" only; **the multi-file styles are NEW** |
| F39 | UPC/ISRC in the cue | "Retrieve UPC/ISRC codes in CUE sheet generation"; "reported not to work correctly with some drives". cdHistory: "EAC is known not to read the ISRC field correctly" | HAO; https://studio-nibble.com/cd/index.php?title=Exact_Audio_Copy_%28EAC%29 | ISRC in table (22); **the UPC/MCN is NEW** |
| F40 | CD-Text read | Needs "CD-Text Read capable drive". Rewritten in 1.0 b3 and "can now also extract composer". Not Unicode. The cue's TITLE and PERFORMER come from the **main window**, "won't necessarily reflect what is found on the CD" | HAD; NEWS; HAO | **NEW** |
| F41 | Pre-emphasis | Read **from the TOC only**. Post-0.95pb3 versions cannot read sub-channel control flags. Written as `FLAGS PRE` in the cue | https://hydrogenaudio.org/index.php/topic,103716.0.html ; HACMP (EAC "Yes (TOC only)", cyanrip "Yes (TOC+subcode)"); https://www.studio-nibble.com/cd/index.php?title=Pre-emphasis | In table (24); **TOC-only and our possible lead are NEW** |
| F42 | Copy-protection column | "the copy protection is only a flag on the CD, and all CD-ROM drives will ignore it" | FAQ | **NEW** |
| F43 | **"Detect TOC Manually" and "Retrieve Native TOC": removed** | Removed in 0.95pb4 (2003) and 0.95b4 (2006) for German anti-circumvention law. **EAC has no "Detect TOC manipulation" feature today**; none found on its pages | HAE; https://www.exactaudiocopy.de/whats-new/ (21 February 2006) | **NEW** (an absence) |
| F44 | Multisession (CD-Extra) | Reads the audio session. A data track shows with a file icon; burning needs two sessions | FEAT; FAQ | In table (25: data tracks) |

### 2.4 Verification, logs, figures

| # | Feature | What it does | Source | Table? |
|---|---|---|---|---|
| F45 | Test & Copy (F6) / Test only / Copy only (F5) | Two passes, two CRCs. The FAQ: "by comparing the CRC values you could be quite sure that both reads resulted in the same file", which is **consistency, not correctness** | FAQ | In table (4, 9) |
| F46 | Copy and test of ranges and images | "copy & test for CD images" since 0.99 pb1 (2007) | https://www.exactaudiocopy.de/whats-new/ ; NEWS | **NEW** |
| F47 | Copy range | Rips any sample range | FEAT | **NEW**. OPS deducts 30 for a range rip (plan section 6) |
| F48 | **Track quality / Range quality %** | "the ratio between the number of minimum reads needed… and the number of reads that were actually performed. 100% will only occur when the CD was extracted without any rereads… ONLY when there are suspicious positions reported, there are really uncorrectable read errors" | FAQ | **NEW** |
| F49 | **Peak level %** | "this is no quality information" | FAQ | **NEW** |
| F50 | **Extraction speed** | Average speed listed in the log since 1.0 b1 | NEWS | **NEW** |
| F51 | Suspicious positions; "Copy OK" / "Copy finished" / "Copy aborted"; "Timing problem"; "Missing samples" | Per-track result lines. A suspicious position makes the track "Copy finished". Missing samples appear when fill-with-silence is off. Timing problems appear in burst mode and are "a really poor 'error detection'" | FAQ; https://hydrogenaudio.org/index.php/topic,104498.0.html ; Lyrion log example | In table (8, 10) |
| F52 | AccurateRip in the log | v1 and v2 (v2 since 1.0 b1), confidence, the database's CRC on a mismatch. fre:ac's author says EAC also tries other offsets so different pressings can verify (unverified beyond that statement) | AR; NEWS; https://github.com/enzo1982/freac/discussions/319 | In table (9, 11); **the pressing-offset check is NEW** |
| F53 | **Log checksum** | "Option for writing a checksum over the extraction log data" (1.0 b1); `CheckLog.exe` ships in the installer. **The algorithm is public:** Rijndael with a 256-bit block, CBC, zero IV, and a fixed key now in OPS's open-source code. puddly's tool can **re-sign** an edited log | NEWS; `OPSnet/Logchecker@ca56547:src/Check/Checksum/EAC.php`; https://pypi.org/project/eac-logchecker/ | In table (28), but **its forgeability is NEW** |
| F54 | Log options | "Create log files always in english language"; automatic status report after extraction; append to log | HAO | **NEW** |
| F55 | CTDB plugin | Runs after a whole-disc rip: verifies and names differing samples ("Differs in 3 samples @02:24:59"). Submits a disc new to CTDB, else reports e.g. "insufficient quality". Also a metadata source | http://cue.tools/wiki/CTDB_EAC_Plugin ; `scratchpad/eac.txt` | In table (11, 13) |
| F56 | AcoustID plugin | Submits fingerprints; pre-selected since 1.2 | NEWS | **NEW** |
| F57 | Glitch removal / WAV editor interpolation | Hand repair of suspicious positions on uncompressed WAV | https://www.exactaudiocopy.de/glitch-removal/ ; FAQ | **NEW** (not a goal: it alters audio) |

### 2.5 Encoding, metadata, setup

| # | Feature | What it does | Source | Table? |
|---|---|---|---|---|
| F58 | External encoder queue | Encoders run "queued in the background" with n threads; "Test encoder" button. Two command-line encoders since 1.4. The "Additional command-line options" field holds **499 characters**. A failing encoder can leave **WAVs with no clear error** (HA, February 2025) | HAO; NEWS; https://hydrogenaudio.org/index.php/topic,127340.0.html | In table (26), partly; **the failure modes are NEW** |
| F59 | Metadata providers | AccurateRip meta (built in, default since 1.7, no submissions); MusicBrainz plugin; CTDB plugin (MusicBrainz, Discogs, freedb); GD3 (paid). freedb was removed in 1.7. Covers and lyrics | https://www.exactaudiocopy.de/whats-new/ ; https://wiki.hydrogenaudio.org/index.php?title=EAC_Metadata_Options | In table (31), as "paid plugin" only |
| F60 | Configuration wizard; beginner mode | The wizard sets drive, encoder and metadata. Beginner mode **hides** fill-with-silence, sync between tracks, overread, Detect Gaps and the cue styles. Users then can't find settings guides name (HA thread, 2025) | HAO; https://hydrogenaudio.org/index.php/topic,127340.0.html | In table (30), partly |
| F61 | Drive options stored by drive name | Since 0.99 pb1, "if you own two identical drives, changing one drives options will directly change the other drives option" | https://www.exactaudiocopy.de/whats-new/ (29 June 2007) | **NEW** |
| F62 | Profiles | Saved settings sets | eacguide | **NEW** (minor) |

### 2.6 CD-R writing

| # | Feature | What it does | Source | Table? |
|---|---|---|---|---|
| F63 | CD writing (internal engine and CDRDAO) | Writes from a cue sheet with the Layout Editor. "On-the-fly' copies will never be supported" | FAQ; FEAT | **NEW** |
| F64 | Write offset; "Create Offset Test CD"; "Detect Write Features" | Measures and corrects the writer's offset for sample-exact copies | HAD; FAQ | **NEW** |
| F65 | Write UPC/ISRC; write CD-Text (CDRDAO, since 0.99 pb1) | Per-drive capability flags | HAD; NEWS | **NEW** |
| F66 | TAO gap removal | "a function for removing gaps that are e.g. created by TAO recording" (0.95 pb5) | NEWS | **NEW** |

**Count:** 66 items, of which about 33 are NEW, or NEW only in part, against the 34 rows.

---

## 3. EAC's procedure, and claims that are disputed

### 3.1 The documented first-time setup and rip

EAC publishes no manual (F-intro above). From its own technology pages and FAQ:

1. **Drive features:** Drive Options → detect read features. If results disagree between runs,
   "assume that the drive does caching" (AFD).
2. **Mode:** "use the appropriate secure mode for your drive". The 2003 FAQ says "In default
   configuration EAC uses the burst mode" (FAQ). C2 off unless tested (FAQ).
3. **Offset:**
   - preferred: "let AccurateRip detect your offset with one or more audio CDs which it
     recognize as offset reference" (OFF, AR);
   - EAC's own key discs: "same pressing like I used". "If you get at least twice exactly the
     same offset, you could be pretty sure to have found the correct one (and only then!)"
     (FAQ, offset questions).
4. **Overread** only if the drive can (HAD, quoting blowfish via eacguide).
   **"Fill up missing offset samples with silence"** on, or AccurateRip won't verify (AR, HAO).
5. **Gaps:** Detect Gaps. Try method A, then B or C if it hangs or looks wrong. Use Accurate
   accuracy, or Secure "if you got gap length that are wrong only by some blocks" (FAQ). HA's
   test of a reasonable result: gaps of different lengths, about 1 to 5 s each (HAD).
6. **Cue sheet**, then **Test & Copy** (FAQ; HAG).
7. **After the rip:** read the status. Listen to suspicious positions. Repair glitches only in
   uncompressed WAV (FAQ; glitch-removal page).

The community route the plan already records (eacguide, OPS) adds the remaining logchecker
settings. HA's wiki adds two recommendations eacguide does not make:
- **error recovery quality Low** (HAO);
- **cache defeat only if the drive caches.** "Checking the 'Drive caches audio data' box with
  drives that are reported by EAC as not caching will not improve EAC's accuracy" (HAD).
  eacguide says to tick it anyway, to avoid manual rescoring.

### 3.2 EAC's claims, and what credible sources say

| EAC's claim | What sources and evidence say | Verdict |
|---|---|---|
| "If it is not sure that the audio stream is correct (at least that it can not be said at approx. 99.5%) the program will tell the user where" (ET) | HA forum: "Re-reading in order to cherry-pick consistent data and using an arbitrary threshold to qualify it as passing/failing does not constitute correction… In secure mode (w/no C2 pointers, cache audio data is configured correctly for the drive), 'Copy OK' is no guarantee that the rip was without consistent errors… With C2 pointers or in burst mode, 'Copy OK' is no guarantee of anything." (https://hydrogenaudio.org/index.php/topic,104498.0.html). **The owner's log, track 5:** Track quality 100.0 %, Test CRC = Copy CRC, "Copy OK", AccurateRip mismatch. CTDB: "(1341/1443) differs in 3 samples @02:24:59" | **Disputed.** The 99.5% has no published basis, and consistent misreads pass silently |
| "On drives which have the 'accurate stream' feature, this [identical extraction] is guaranteed" (ET) | HA: accurate stream "significantly reduces (if not completely eliminates)" shifts (HAD). With it ticked, EAC checks synchronization only every 2 MB (HA forum, topic 67834) | **Overstated** |
| Test & Copy: "One CRC code is unique for a set of data. So by comparing the CRC values you could be quite sure that both reads resulted in the same file" (FAQ) | CRC32 is not unique (collisions exist at 1 in 2^32 odds per pair, which is negligible here). The real limit is that **matching CRCs prove consistency, not correctness**. HA forum: "T&C is nothing more than a demonstration of precision. It does not provide any guarantee of accuracy." (https://hydrogenaudio.org/index.php/topic,82489.0.html). Owner's log, track 5: T&C matched on wrong audio | **Disputed** as proof of correctness. EAC's own wording only claims "the same file" |
| Track quality: 99.x% means "the secure mode has corrected it" (FAQ) | Same HA thread: re-reading for a majority "does not constitute correction". zexwoo's log guide (Chinese, translated here): it drops 0.1% with each extra read and is unrelated to whether the result is correct (https://zexwoo.blog/posts/knowledge/ripping-logs/, 2021-12-20). Owner's log: wrong tracks at 99.8 %, 99.9 % **and 100.0 %** | **Disputed.** It measures re-read effort, not accuracy |
| Secure mode on a caching drive is safe once cache defeat is set (ET, AFD) | EAC's own tips: without it, "the result will be the same as using 'Fast Extraction' (having no error detection)" (TIPS). EAC's cache test "will give some problems with drives that extract audio very slowly" (AFD). HA: if unsure, test by provoking errors on a scratched disc, or with `cachex`; flushing is unneeded below 64 KB of cache, because "EAC will never request less than this amount" (HAD) | **Holds only when the cache test is right.** A caching drive mis-detected as non-caching gives secure mode no error detection |
| C2 makes secure mode fast and safe (ET: "really fast mode… for drives with C2") | EAC's own FAQ, twice: "C2 is not correctly implemented in some drives… turn off". AccurateRip's home page: no drive self-detects errors 100% of the time, "(and applies to drives with c2 reporting abilities)" (https://www.accuraterip.com/). HA: "Examine C2" can't prove that every error is reported (HAD) | **Disputed by EAC's own FAQ** |
| Offset reference (Plextor 14/32 = +679) (OFF) | HA wiki: "challenged in late 2006… the reference is actually off by 30 samples… Wiethoff feels that it's too late to change… the reliability of AccurateRip data is not compromised" (https://wiki.hydrogenaudio.org/index.php?title=AccurateRip ; https://hydrogenaudio.org/index.php/topic,50301.0.html) | **Disputed but harmless** for verification. Matters only for absolute-zero copies |
| Gap detection is correct in most cases (GAP) | EAC itself: "the deviance should be lower than 2-3 sectors". HA: "There is no way to know if the values are 100% correct" (HAD) | **EAC admits it is approximate**. See row 21 below |
| "Test Gaps On Silence" | HA: reports 100.0% silence for non-null gaps: "not to be trusted" (HAG) | **False positive** |
| Pre-emphasis detected | TOC only. Some discs carry the flag only in sub-channel Q; EAC misses them (cdHistory; HA topic 103716; Steve Hoffman thread, 2022) | **Incomplete** |
| ISRC in the cue | "known not to read the ISRC field correctly" (cdHistory); "not to work correctly with some drives" (HAO) | **Unreliable on some drives.** On the owner's drive, `.26` matches 14 of 14 (plan row 22) |
| Log checksum proves a log unedited | The key is public and the tool re-signs logs (F53) | **Tamper-evidence against casual edits only** |
| "Copy OK" | EAC prints "Copy OK" when no suspicious position was recorded. **The owner's log:** tracks 3 and 4 have **Test CRC ≠ Copy CRC** yet "Copy OK", and the summary says "No errors occurred". HA, 2010: "If you get different CRCs with T&C secure then something is seriously wrong and you shouldn't trust anything" | **Misleading.** EAC's per-track verdict ignores a T&C mismatch; OPS deducts 30 for it |

### 3.3 Known EAC bugs and limits (dated, sourced)

- **Burst-mode logs say "No errors occured" for every track** (HAE, Limitations).
- **CTDB plugin under 1.0 b2 to b4:** suspicious positions are not passed, so bad recovery
  records can be accepted (CTDB EAC Plugin page, 2024-06-28).
- **Crash on read errors:** fixed in 1.0 b6 (April 2015) (NEWS).
- **LG-drive extraction problems:** fixed in 1.1 (2015) (NEWS).
- **File dialogs crash or hang** with WinFSP, Dokan, Cryptomator, TortoiseSVN, Adobe Drive or
  Symantec Endpoint Protection installed. EAC's FAQ names these. An HA poster (2024-12) traces
  it to EAC's 32-bit Stony Brook Modula-2 build; that cause is unverified
  (https://www.exactaudiocopy.de/faq/ ; https://hydrogenaudio.org/index.php/topic,127089.0.html).
- **Fonts on Windows 11:** "MS Sans Serif and MS Serif are missing", so settings render too
  large (FAQ).
- **Two instances share compression settings** at random (HA, 2025-08).
- **The encoder line is capped at 499 characters,** and a failed encode leaves WAVs (HA,
  2025-02).
- **Under Wine:** plugins are not listed on a clean prefix; GD3 and CTDB need .NET 4.8; EAC
  needs .NET 2.0 to install (WineHQ AppDB, 1.8, rated Gold, tested on Wine 11.0:
  https://appdb.winehq.org/objectManager.php?iId=42275&sClass=version).

---

## 4. What people say, 2024 to 2026, and how an EAC rip is still wrong

### 4.1 Praise

- **It is still the default free answer.** HA's February 2025 setup thread treats 1.8 as the
  version to configure (topic 127340). An aggregate of Reddit mentions ranks EAC second to
  dBpoweramp (https://gummysearch.com/tools/best-products/cd-ripping-software/, a marketing
  aggregator, low weight).
- **Its logs are the tracker standard.** An XLD user: "the private torrent sites insist on valid
  log files generated by EAC and X-Lossless for mac" (same aggregator).
- **It is maintained, if slowly.** A Hacker News user, June 2025: "when I contacted the author he
  was very responsive" (https://news.ycombinator.com/item?id=44263371). Another in the same
  thread: "the author seems to have moved on".
- **When AccurateRip can't verify,** fre:ac's author says EAC "has some advantages": it checks
  other offsets, and it reads twice and compares
  (https://github.com/enzo1982/freac/discussions/319).

### 4.2 Complaints

- **Setup is hard and the UI is dated.** Nero's 2026 comparison (a competitor, low weight):
  "interface hasn't been updated in 16 years… First-time setup takes 15–30 minutes"
  (https://pcai.nero.com/blog/best-cd-ripper). HA 2025: beginner mode hides settings, the
  command line is truncated, and files silently stay WAV (topic 127340).
- **It is slow,** by design in secure mode with cache defeat (ET). HA 2025: "EAC wanted to rip
  one of my CDs really slow, like 1.2x" (topic 127340).
- **Metadata churn:** freedb was removed in 1.7. Long-time freedb users lost genre and
  submission (HA, 2024-10: https://hydrogenaudio.org/index.php/topic,126754.0.html). The 1.7
  email bug led to 1.8, and Tweakers commenters report freezes.
- **Windows only;** runs under Wine (WineHQ Gold).
- **For bad discs, HA points to CTDB repair:** "Correction through the CUETools database is a far
  more effective way to handle ripping errors than EAC's archaic method of using re-read sets
  which has never really worked that well on the whole" (HAO, Error recovery quality).

### 4.3 How an EAC rip is still wrong, with "Copy OK"

1. **A consistent misread.** The drive returns the same wrong samples, often interpolated, on
   every read. Secure mode, Test & Copy and Track quality all pass. Only AccurateRip or CTDB
   catch it. **Proven on the owner's drive: track 5**, and HA topic 104498 above.
2. **A caching drive detected as non-caching.** Secure mode's paired reads come from cache: "the
   same as using 'Fast Extraction'" (TIPS). Test & Copy still re-reads the disc, because a whole
   track exceeds the cache. That is why T&C is the backstop there.
3. **C2 trusted on a drive that under-reports it** (FAQ, twice; HAD).
4. **Wrong offset:** a different pressing or a bad key-disc result. AccurateRip then fails on
   every track; CTDB is offset-free (https://cue.tools/wiki/CTDB).
5. **Burst mode with no AccurateRip match:** the log still says "No errors occured" (HAE).
6. **The CD's own layout lost:**
   - HTOA not ripped (HAG);
   - "Leave out gaps" chosen (HAG);
   - silent blocks deleted (HAO);
   - pre-emphasis flagged only in sub-channel and missed (cdHistory);
   - cue gap positions off by 1 to 3 sectors (GAP).
7. **A T&C mismatch that still says "Copy OK" and "No errors occurred":** the owner's log,
   tracks 3 and 4. A user reading only the summary is misled.
8. **AccurateRip confidence counting your own earlier submission.** HA: "So long as you aren't
   comparing against your own submission, a confidence of just one is all that is necessary"
   (https://hydrogenaudio.org/index.php/topic,82751.0.html). The owner's track 5 matched
   "(2/1443)" CTDB entries, possibly earlier submissions from this drive. **Unverified.**

---

## 5. What this changes in the plan of record

| Plan item | Change | Why |
|---|---|---|
| Section 3 table, "What's new" row: "No secure-mode change is listed after 1.0 beta 3" | Keep it, and add: "**read-path fixes after beta 3:** 1.0b6 read-error crash, 1.1 LG-drive extraction, 1.2 AR-checksum lookup and read-command detection" | `News.rtf` in the 1.8 installer |
| Appendix B, "Run 1.8" | **Unchanged; reasons added:** 1.0 b3 is no longer offered on EAC's site; its CTDB pairing can accept bad recovery records; later fixes touch extraction; no tracker penalises 1.x. 1.8's installer hashes match the published MD5 and SHA-1 | Sections 1.1 to 1.4 |
| Appendix B, installer advice | Add: **untick AcoustID** (pre-selected since 1.2). The owner's log shows it submitting. The CTDB plugin submits automatically and CTDB logs IP and drive model | Section 1.5 |
| Row 5, damaged disc | EAC **does** have a time bound (F16, off by default), skip-on-error (F15) and cool-down (F17). Row 5's action, "a per-track time budget", matches EAC's design; consider the same multiple-of-realtime form | HAO |
| Row 21, track 9 pregap | **EAC's 94 isn't ground truth.** EAC states ±2 to 3 sectors. Decide track 9 by sub-channel Q read across several passes, not by agreement with EAC | GAP |
| Row 24, pre-emphasis | EAC reads the TOC only. HA's table says cyanrip reads TOC and subcode. If that holds for the fork, **row 24 is "Better once tested"**. Test needs a disc with PRE only in sub-channel | HACMP; cdHistory |
| Row 28, log anyone can check | Replace "Closed, obfuscated signature" with "**a keyed checksum whose key and algorithm are public; anyone can re-sign an edited log**" | `OPSnet/Logchecker@ca56547:src/Check/Checksum/EAC.php`; eac-logchecker on PyPI |
| Row 8, saying a wrong track is wrong | Add EAC's sharper fault: "Copy OK" and "No errors occurred" printed over a **Test/Copy CRC mismatch** (owner's log, tracks 3 and 4). Our wording should never say "OK" over disagreeing reads | `scratchpad/eac.txt` |
| Row 33, drive blip | EAC locks the tray during extraction by default (F18). Consider locking it as well as confirming a removal (SCSI PREVENT ALLOW MEDIUM REMOVAL; that cyanrip can do this is unverified) | HAO |
| Rows 9 and 10, per-track proof and suspicious positions | Don't copy "Track quality %": it measures re-reads, not accuracy (F48, owner's track 5). If shown at all, label it "re-read effort" | FAQ; owner's log |
| Row 17, cache defeat | HA's 64 KB rule and the scratched-disc test are an independent check of the cache measurement | HAD |
| Row 14, AccurateRip submission | New evidence: AccurateRip's own page lists five "AccurateRip compatible" programs (dBpoweramp, EAC, Rip, XLD, Songbook) and no Linux ripper. It doesn't say whether others may submit: still **unverified** | https://www.accuraterip.com/software.htm |

---

## 6. Not verified

- The source of HA's "1.8 is the Final Release" footnote: the HA wiki history returned HTTP 403
  to every fetch.
- RED's logchecker and its version policy: private.
- Whether GD3 or AcoustID are ticked by default in the 1.8 installer screen today. The
  changelog says AcoustID is "pre-selected" from 1.2; the NSIS script was not recovered.
- What `INetC.dll`, `Empty20.exe` and `empty461.exe` do in the installer.
- That EAC checks AccurateRip at other pressing offsets: one statement, by fre:ac's author.
- That cyanrip reads pre-emphasis from sub-channel: HA's table says so; not checked in the
  fork's code.
- The groups.io report of 1.8 errors on last tracks versus 1.6: one report, likely
  configuration.
- The Stony Brook Modula-2 explanation of the file-dialog crashes: one forum post.

## 7. Sources, each fetched 2026-11-03 unless dated

- EAC: https://www.exactaudiocopy.de/ , `/download/` , `/whats-new/` , `/faq/` ,
  `/extraction-technology/` , `/features-of-eac/` , `/automatic-feature-detection-technology/` ,
  `/gap-technology/` , `/offset-technology/` , `/track-synchronization-technology/` ,
  `/accurate-rip/` , `/tips-specs/` , `/registration/` , `/main-legal-limitations/` ,
  `/older-versions-for-download/` , `/download-from-alternative-servers-2/` ,
  `/commercial-sdk/` , `/documentation/` , `/eac-related-sites/` , `/glitch-removal/` ,
  `/dae-quality/` , `/list-of-included-reference-cds/`
- EAC's files: `eac-1.8.exe` (hashes above) → `News.rtf`, `Documentation/EAC.txt`,
  `Documentation/FAQ.txt`, `Legal.rtf`, kept under
  `/tmp/claude-0/-home-user-claude-code-skills/46cfbc1a-d1c5-5a09-bbbb-4b2444266d0f/scratchpad/eac18-x/`
- HA wiki: Exact_Audio_Copy, EAC_Options, EAC_Drive_Options, EAC_Gap_Settings,
  EAC_and_Cue_Sheets, AccurateRip, Comparison_of_CD_rippers, EAC_Metadata_Options
- HA forum: topics 115702 (2018), 82489 (2010), 67834 (2008), 82751 (2010), 104498, 103716
  (2013), 50301 (2006), 126754 (2024), 127340 (2025), 127089 (2024), 127927 (2025)
- CUETools: http://cue.tools/wiki/CTDB_EAC_Plugin (edited 2024-06-28),
  https://cue.tools/wiki/CTDB (edited 2026-03-21)
- AccurateRip: https://www.accuraterip.com/ , https://www.accuraterip.com/software.htm
- cdHistory: Exact_Audio_Copy_(EAC) and Pre-emphasis pages at studio-nibble.com
- OPS: https://github.com/OPSnet/Logchecker at `ca56547` (head on 2026-11-03);
  https://pypi.org/project/eac-logchecker/
- WineHQ AppDB (EAC 1.8); Tweakers (1.8); groups.io ExactAudioCopy; Hacker News 44263371;
  fre:ac discussion 319; Steve Hoffman forum threads on pre-emphasis (2006, 2022)
- The owner's EAC 1.8 log of the reference disc:
  `/tmp/claude-0/-home-user-claude-code-skills/46cfbc1a-d1c5-5a09-bbbb-4b2444266d0f/scratchpad/eac.txt`
