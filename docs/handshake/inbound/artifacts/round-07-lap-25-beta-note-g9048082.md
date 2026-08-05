# cyanrip beta — `0.9.4-rc1+platterpus.5-beta.5`

*Information only. This file describes the beta and what to test in it, and
nothing else.*

---

## Identifiers

```
version   0.9.4-rc1+platterpus.5-beta.5
repo      rmccann-hub/cyanrip
branch    platterpus-fork
build     9048082      <- check this out
tests     31/31
anchor    sha256/16 = b849568d1f3a64d2   (over src/*.c and src/*.h)
contract  PROVIDER-CONTRACT.md in that tree, and it describes that tree
```

**`beta.4` (`f5e11ba`) is superseded and should not be installed.** It writes an
`INDEX 00` for zero-length pre-gaps that this build does not — a cue-sheet
change, so it earns a version rather than riding inside `beta.4`.

**The commit is the identifier.** There is no git tag and no GitHub release: the
git proxy refuses tag pushes (`HTTP 403`, `git ls-remote --tags origin` returns
nothing) and no release-creation API is reachable from it.

> **Pin the artifacts commit, not the commit that bumped the version.**
> `tools/gen-provider-contract.py` reads the *built binary* and refuses on a
> dirty tree, so the contract cannot be regenerated in the same commit as a
> version bump — the bump has to be committed before a clean build exists to
> derive from. **Six of the seven version bumps that carry a contract shipped one
> describing the previous version — including this beta's own:**
>
> ```
> 6e62172   meson .3          contract 0.9.4-rc1     DISAGREE
> 5bc654d   meson .4          contract .4            agree
> 937cacf   meson .5-beta.1   contract .4            DISAGREE
> c5fb909   meson .5-beta.2   contract .5-beta.1     DISAGREE
> e61e75a   meson .5-beta.3   contract .5-beta.2     DISAGREE
> f5e11ba   meson .5-beta.4   contract .5-beta.3     DISAGREE
> c10cc94   meson .5-beta.5   contract .5-beta.4     DISAGREE  <- this beta
> ```
>
> Six, not seven: `5bc654d`'s contract had been regenerated one commit earlier
> from a tree already carrying the new string. An earlier draft of this file said
> *"every release"*, generalising from three checked commits;
> `tests/rip_images.py contract_build` passes at `5bc654d`, so the check offered
> as that claim's enforcement was also its disproof. Enumerated from
> `git log --format=%h -- meson.build`, not sampled.
>
> **`c10cc94` is the version bump for this beta and its contract still says
> `beta.4`.** `9048082`, above, is where the regenerated contract lands.
> `contract_build` now fails on any tree where the two disagree.

**This is a pre-release.** It claims no joint verification, and says so in every
logfile it writes. Round 7 is open and both projects declare HOLD.

**It supersedes `…-beta.3` (`e61e75a`) and `…-beta.2` (`c5fb909`) as the build
to install — but read the next section before assuming the rig evidence carries
over. Unlike `beta.3`, this build is *not* observably identical to the one the
rig tested.**

## Build and verify

```sh
git clone <repo> && cd cyanrip
git checkout 9048082
meson setup build && ninja -C build
meson test -C build --print-errorlogs
./build/src/cyanrip --version
python3 tools/gen-provider-contract.py --check PROVIDER-CONTRACT.md
```

Expected:

```
31/31 tests passing
cyanrip 0.9.4-rc1+platterpus.5-beta.5 (platterpus-fork-g9048082)
PROVIDER-CONTRACT.md is up to date
```

31, not 28. Three checks are new since `beta.3`: `contract_build`, the audio
checksum mirror's `self-test`, and the cue pre-gap decision.

A banner ending `-dirty` means the tree had uncommitted changes and the commit
does not describe the binary.

**If you ran the previous beta's suite and saw 27/28, that was a defect in our
test harness and not in your setup.** `version_matrix` resolved upstream
`master` as a local branch, and `git clone` creates a local branch only for the
remote's HEAD — which is `platterpus-fork` — so a fresh clone had
`origin/master` and no `master`, and the check failed with *"master is
unreachable"*. It passed in our working tree, which happens to carry the
branch, so `beta.3`'s note claimed 28/28 from a clean checkout and that was not
true for anyone who cloned. Fixed in `beta.4`; this beta's 31/31 was verified in
a fresh clone rather than in the tree that built it.

## Which artifact in that tree describes which commit

| artifact | describes | why |
|---|---|---|
| `PROVIDER-CONTRACT.md` | **the pin, `9048082`** | correct, and the reason the pin is this commit and not `c10cc94` |
| `docs/golden-reference.log` + `.diagnostics.json` | build **`c10cc94`** (banner says so) | a log carries the build tag of the binary that wrote it, so it can never sit inside that build's own commit |
| this note | build **`9048082`** | same reason: it names a commit, so it lands as that commit's child |

`c10cc94` and `9048082` are the same ripping code — `git diff c10cc94..9048082
-- src/ meson.build` is empty. They differ in the build SHA in the banner and in
the documents above. **`f5e11ba` is a different program**: it lacks the cue fix.

## What changed in `beta.4`, and still applies here — two log lines

Both were raised as non-blocking notes and both were carried as known
imprecision. They are **proposals shipped in a beta so they can be run**, and
either can be withdrawn.

`git diff e61e75a..f5e11ba -- src/` touches two files and nothing else.
**`beta.5` adds one more change on top of these: the cue fix below.**

### 1. Cover art — the line now names which release ID, and when

```diff
- Release ID unavailable, cannot search Cover Art DB!
+ No MusicBrainz release ID at cover art lookup, cannot search Cover Art DB!
```

The old line and the header's `Release ID: <uuid>` appear in the same log and
read as a contradiction. Both are true, and the ordering is worth stating
exactly because both projects have described it loosely:

- **Chronologically the refusal comes first.** `-R` and a user
  `-a musicbrainz_albumid=` are merged into the metadata **after**
  `crip_fill_coverart()` runs, so cyanrip genuinely had no ID of its own at
  that moment.
- **Positionally it comes second.** `crip_early_flush()` is the last statement
  of `cyanrip_log_start_report()` (`src/cyanrip_log.c:662`), so the replayed
  pre-log block is written *after* the header — in `docs/golden-reference.log`
  the header ends at line 27 and the replay runs 29–34.

So a parser reading top to bottom meets the `Release ID:` header first and the
refusal after it, which is the opposite of the order in which they happened.
The new line states what was observed rather than the stronger claim that the
release has no ID.

**The trailing `cannot search Cover Art DB!` is unchanged**, so a substring
match on the tail still works. An exact-string match does not.

### 2. AccurateRip — both tally lines now divide by the disc

```diff
  Tracks ripped accurately: 13/14
- Tracks ripped partially accurately: 1/1
+ Tracks ripped partially accurately: 1/14
```

The partial line divided by *tracks not fully verified* while the line above it
divides by the disc's track count, so `1/1` was a denominator derived from the
first line's result and the pair read as one tally over-reports. Both now
divide by the track count.

**The numerators are unchanged, and so is which track falls in which bucket.**
Same disc, same verdict, different denominator.

**This one changes a number, not only text.** The archived rig log
(`docs/rig-2026-08-04/cyanrip.log`, build `9003e6f`) has exactly this pair at
lines 1130-1131 against `Disc tracks: 14` on line 23. A stored `1/1` from that
disc becomes `1/14`.

## The cue-sheet fix, which is new in `beta.5`

**A zero-length pre-gap no longer gets an `INDEX 00`.** Your own rips found it:
on tracks 3, 6, 11 and 12 the log said `Pregap length: 0 frames` and the cue
declared an `INDEX 00` anyway, at a timestamp **one frame past the end of the
previous `FILE`**.

```
track 3   log:  Pregap LSN 28067,  length 0,  Start LSN 28067 (with offset: 28068)
          cue:  INDEX 00 03:01:05   = frame 13580 of a file holding frames 0..13579
```

The guard compared against `start_lsn`, which `setup_track_lsn()` overwrites
with the offset-accounted first frame *after* the gap decisions are taken — so
with `-s 667` it sat one frame past the signalled start and a zero-length
pre-gap read as a one-frame one. The length two lines below already used
`start_lsn_sig`. **Present in all three cue sheets on record**, including the
2026-08-04 beta.1 session, so this is not a `beta.4` regression.

**What to check:** re-rip and confirm your cue has **no** `INDEX 00` for tracks
3, 6, 11 and 12, and still has one for 2, 4, 5, 7, 8, 9, 10, 13 and 14. If a
pre-gap you expect has gone missing, that is a finding and the fix goes back.

No test here can reach the trigger — it needs a pre-gap that is signalled *and*
zero frames long, and a bincue track whose `INDEX 00` equals its `INDEX 01`
comes back `unknown (sub-channel unreadable)`, measured on a fixture built for
it. `tests/cuegap.c` exercises the decision directly, with your rip's numbers.

## What to test

### Highest value, cheapest, and specific to this beta

**Re-rip the baseline disc (The Police, *Every Breath You Take: The Classics*,
14 tracks, MusicBrainz DiscID `pNtImOkdBm9RMBIalzx0w9cfsYY-`, CDDB ID
`E20DFE0E`) on `9048082` and diff the log against the one you already have.**

> **Which log?** Two rig sessions ran on 2026-08-04 — `9003e6f` (beta.1) and
> `c5fb909` (beta.2) — and our documents had been calling both "the 2026-08-04
> session". Diff against the **`c5fb909`** one: beta.1 predates the pre-log
> replay block and has no `Read stalls:` line, so half the table below has
> nothing to compare against in it.

**Diff it, but do not expect it to be nearly identical.** An earlier draft of
this file gave a short "everything must match except" table and told you that
anything else moving was a finding. That table was derived from
`docs/golden-reference.log` — a 3-track *image* rip with `-N -A -P 0`, which has
no AccurateRip block, no paranoia activity and one version string. **A reference
that does not contain the varying lines cannot tell you which lines vary.** The
list below is derived from `docs/rig-2026-08-04/cyanrip.log`, a real 14-track
disc rip, and it is longer.

**Expected to differ, by cause:**

| cause | lines |
|---|---|
| **build identity** | the banner **and every per-track `comment:` tag** — the version string appears **15 times** in a real log, not once (`grep -c` on the rig log), plus `Handshake:` (this build says `round 7 lap 25`) |
| **invocation** | `Invoked as:`, `Consumer:` |
| **read timing** | `Extraction speed:`, `Elapsed:`, `Ripping finished at`, and `Read stalls:` if a read ever stalls |
| **read behaviour** | **every `Paranoia status counts:` block** — the rig log has 15 of them and they carry real activity (`FIXUP_ATOM: 4` on track 5). These are a measurement of that read, not of the disc, and two rips of one disc need not agree |
| **the AccurateRip database, not us** | `confidence N` on every `Accurip v1`/`v2` line, `max confidence:`, and therefore possibly `Tracks ripped accurately: N/M` if a track crosses the threshold between rips. The rig log shows `confidence 129`/`200`; those accumulate over time |
| **this beta's two changes** | §1 and §2 |
| **follows from all of the above** | `Log FUN512:` |

**What should be identical:** the TOC and disc identity (`DiscID`, `CDDB ID`,
`Disc tracks:`, `Total time:`), the drive and offset block, and **every checksum
over the audio** — `CRC32`, `EAC CRC32`, `Accurip v1`/`v2` (the checksums, not
their confidences).

**`Pregap source:` is not in that list, and an earlier draft put it there.**
13 of the 14 lines on this disc read `sub-channel (not signalled by TOC)`, which
is the *outcome of an MMC read*, not a TOC field — the same read can come back
`unknown (sub-channel unreadable)` or `unknown (sub-channel CRC mismatches)` on
another attempt. Empirically it has been stable: identical across the two rips
we hold, 13 `sub-channel` + 1 `lead-in` both times. Stable so far is not
guaranteed, and this file should not have promised the stronger thing.

**A checksum that moves is worth reporting. Anything in the table above is
expected. A `Pregap source:` that moves is interesting but not a defect.**

The second line is the one that matters most: **it has never executed
anywhere.** The block needs an AccurateRip database hit, the lookup fetches over
the network with no local-file input, and the synthetic test discs are not in
the database — measured, a fixture rip with lookups enabled reports
`AccurateRip:    not found` and prints no tally at all. Your baseline disc is
the only place this can be verified.

### Check the files against the log, not just log against log

`tools/audio-checksums.py` is new in this beta. It reimplements
`src/checksums.h` in Python, so any audio file can be checked against any
cyanrip log without the disc:

```sh
tools/audio-checksums.py check track05.flac --log cyanrip.log --track 5
tools/audio-checksums.py diff  ours.flac theirs.flac      # localise to the sector
tools/audio-checksums.py self-test                        # it has not drifted
```

Run over three tracks of the EAC baseline it reproduced the rig log exactly for
tracks 1 and 7, and for track 5 produced `E0036697` — the value the auto-fix
supersede recorded, not the `6902BCF0` in the log. **Both are right**: the log
describes the read that was thrown away. Worth knowing before you diff a
directory against a log and conclude something is corrupt.

### Everything else, unchanged from the previous beta

Nothing else in this build is new, so the standing list still stands. **In the
order it was asked for**, which is by cost-to-close and not by size of gap — the
gap inventory in `docs/AUDIT-2026-08-05.md` §3 is ordered differently on
purpose, and this file previously mixed the two:

1. **`-x` on one throwaway rip.** Never executed on a real drive, anywhere,
   ever — the largest single gap in the project, and the cheapest to close. It
   now reports a stall if it wedges rather than hanging silently, which is why
   asking is reasonable. **A hang is also a result** — send it either way.
2. **`-j <path>` on any one run.** The diagnostics record has only ever been
   written by image rips. Off by default and changes nothing else. Worth
   cross-checking `read_stalls` and `rip.track_state` against the same facts in
   the log.
3. **A deliberate abort** — eject mid-rip, or fill the write target. The
   diagnosed-abort exit code has never fired on hardware; the rig rip had
   `Ripping errors: 0`.
4. **Marginal media plus `-k 1`.** A non-zero `Read stalls:` count has never
   been produced anywhere. The `none` form is hardware-confirmed **by your
   report, not by anything in this repository** — the rig log archived here is
   the `9003e6f` session and has no `Read stalls:` line at all; the only record
   is `docs/rig-2026-08-04-c5fb909/platterpus-results.md:78`, and that session's
   cyanrip log is not held. The populated forms are unit-tested against the
   formatter and no drive has ever emitted one.
5. **CD-TEXT from a disc that has some**, opportunistically. A physical disc's
   CD-TEXT goes through `mmc_read_cdtext`, a different code path from the
   `.toc` image parser the suite uses.

**Not asked for:** `-f` offset autodetection, another EAC parity run, or
re-testing anything the 2026-08-04 session already closed. `-f` remains unrun
and is listed as a gap in the audit, but it is not worth a rig slot.

### One thing to know before relying on `PROVIDER-CONTRACT.md`

**A change to a number's meaning is indistinguishable, in the contract, from a
comment being added.** That is the finding, and it took two wrong drafts to
state correctly.

Measured, by reverting the denominator **alone** on a clean build and
regenerating: the entire diff is the source anchor —
`da96b1223b0e182b` → `41317a8af0d9bd9e` — and every P2 row is byte-identical,
because P2 derives each entry from the *format string* and §2 changed an
argument.

But change §2 **as shipped** (`d1d8312`) also carries a seven-line comment
explaining it, and that moves six `cyanrip_log.c` rows: 686→693, 688→695,
698→705, 707→714, 710→717, 713→720. §1 moves a seventh, `coverart.c:360→368`,
and is the only row whose **text** changes.

So the contract does not go quiet — it emits a line-number shift. **It emits
exactly the same line-number shift for a comment, a blank line, or a
refactor.** A consumer diffing two contracts sees six rows move and cannot tell
whether a denominator changed or someone documented it.

Two earlier drafts of this paragraph were wrong in opposite directions: the
first said `--check` exits 0 across the change (it does not — the anchor moves),
the second said not one row of the body changes (six do, once the comment is
counted).

Deliberately not patched: a half-working argument extractor would put wrong text
into a document that presents itself as derived. Proposed as round 8 work with
the cost stated.

## What every logfile from this build contains

```
cyanrip 0.9.4-rc1+platterpus.5-beta.5 (platterpus-fork-g9048082)
Invoked as:     …
Handshake:      round 7 lap 25 OPEN, verdict HOLD -- NOT a released build
Consumer:       <whatever --consumer was given>
                (reported by the caller, not verified by cyanrip)
```

`Handshake:` is derived from `docs/handshake/` at build time, so it reports the
newest lap the *tree* contains — `lap 25` at `9048082`. Building `f5e11ba`
instead reports `lap 24`, which is not a discrepancy: lap 25 did not exist yet.
`Consumer:` is whatever you pass to `-u`, recorded verbatim and explicitly not
verified.

## Flags relevant to this build

| flag | |
|---|---|
| `-u` / `--consumer <string>` | recorded verbatim in the log, explicitly not verified |
| `-j` / `--diagnostics <path>` | machine-readable JSON record; off unless given |
| `-k` / `--stall-secs <seconds>` | seconds a frame read must stall before liveness is reported (default 10, `0` disables) |
| `-x` / `--cache-probe` | measure the drive's readback cache before ripping; refuses on a disc image. **Never executed on real hardware** |

Flag count: 41. Full generated interface in `PROVIDER-CONTRACT.md` **in the
`9048082` tree** — not in `c10cc94`'s, which still carries `beta.4`'s.

## What this build still cannot claim

Full list with the cost to close each: `docs/AUDIT-2026-08-05.md` §3.

- **The two changed lines have not run on a drive**, and §2 has not run
  anywhere at all.
- **`-x` has never produced a measurement on a real drive.**
- **A non-zero `Read stalls:` count has never been produced anywhere**, and the
  `none` form is confirmed only by Platterpus's report of the `c5fb909` session,
  whose cyanrip log this repository does not hold. A silent watchdog is not a
  working watchdog — zero heartbeats on healthy media is the expected result and
  is not evidence either way.
- **The diagnosed-abort exit code has never fired on hardware.**
- **`-j` has never been written by a rip from a physical drive.**
- **`-f` and CD-TEXT from a disc that has some** remain unrun.
- **The track-1 pre-gap fix has never fired on a real TOC** — and that is the
  whole of what is missing, because **the image case is already closed**.
  `tests/fixtures/pregap.cue` declares a track-1 HTOA and
  `docs/golden-reference.log:77-80` shows the fix working on it:
  `Pregap LSN: 0`, `Pregap length: 150 frames`, `Pregap source: TOC`,
  `Start LSN: 150`. An earlier draft of this file called a disc image "the
  cheapest route left", presenting a closed route as the open one; the audit
  (§3.7) had it right and this file contradicted it.

  What remains is a *physical* disc whose TOC declares the pre-gap, and there may
  not be one to hand. Platterpus's results file scopes its measurement precisely:
  *"across every `Pregap source:` line in the whole retained log history — 40+
  occurrences spanning three days of rips"*, none of them `TOC`. **That is
  "looked in one collection's retained logs and found none", not "no candidate
  exists"** — an earlier draft of this file wrote the stronger form, which is the
  `none` versus `unknown (reason)` distinction this project has a rule about,
  applied to somebody else's evidence. The rig logs archived here agree as far as
  they go: 13 `sub-channel` and 1 `lead-in` per disc, no `TOC`.
