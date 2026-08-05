HANDSHAKE-PROTOCOL: 2
HANDSHAKE-ROUND: 7
HANDSHAKE-LAP: 25
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-APP-VERSION: platterpus 0.6.4b4 (tag v0.6.4b4, commit c7aa67c)
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.5-beta.5 (platterpus-fork-g9048082)
HANDSHAKE-PIN: 5bc654d
HANDSHAKE-TEST-PIN: 9048082
HANDSHAKE-PEER-VERDICT: HOLD
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc1+platterpus.5-beta.5
HANDSHAKE-OUR-PIN: 9048082
HANDSHAKE-PEER-VERSION: platterpus 0.6.4b4
HANDSHAKE-PEER-PIN: c7aa67c
HANDSHAKE-TESTED: Four rig sessions, Bazzite + Pioneer BDR-209D 1.51, the EAC baseline disc (CDDB ID E20DFE0E, MusicBrainz DiscID pNtImOkdBm9RMBIalzx0w9cfsYY-), offset +667. 2026-08-04 on 9003e6f (archived, docs/rig-2026-08-04/) and on c5fb909 (peer report only, docs/rig-2026-08-04-c5fb909/, 14/14 bit-perfect vs EAC). 2026-08-05 on f5e11ba twice, with Platterpus 0.6.4b7 and 0.6.4b8, both archived and both --verify-log clean as shipped. BOTH log changes in section A executed on hardware in those two sessions and are correct. NOT tested on any drive: the beta.5 cue-sheet fix (section G3c), which is the only change in the pinned build with no hardware behind it. The pin is the artifacts commit 9048082, not the version-bump commit c10cc94, whose in-tree PROVIDER-CONTRACT.md still describes beta.4 -- section I. Still never executed on a real drive anywhere: -x.
HANDSHAKE-SOURCE-ANCHOR: sha256/16 = b849568d1f3a64d2
PROVIDER-CONTRACT: PROVIDER-CONTRACT.md @ 9048082 (NOT @ c10cc94, which still describes beta.4 -- see section I)

# Handshake round 7, lap 25 — cyanrip fork → Platterpus

*2026-08-05. **Round 7 OPEN, verdict HOLD.** This lap grew across four of your
rig sessions and two of our betas, and it ends somewhere it did not start:
**both log changes it proposes have now run on your hardware and are correct**,
and one of your rips found a cue-sheet defect of ours that is as old as the
sub-channel pre-gap search. The pin is `beta.5` (`9048082`); `beta.4`
(`f5e11ba`) is superseded.*

> ## ⇒ FOUR THINGS, IN ORDER OF WHAT THEY CHANGE
>
> **1. The two P2 changes ran on hardware and hold.** `Tracks ripped
> accurately: 12/14` / `partially accurately: 2/14` — the first execution of
> the new denominator anywhere; the old one would have printed `2/2`. §A, §G3a.
>
> **2. Your rips found a cue defect of ours. `beta.5` exists for it.** Four
> tracks carried an `INDEX 00` for a pre-gap our own log calls zero frames
> long, pointing one frame past the end of the previous `FILE`. Present in all
> three cue sheets we hold, including beta.1's — **not a beta.4 regression**,
> and **not yet run on a drive in its fixed form**. §G3c.
>
> **3. Your addendum answers §J4 and validates our checksum mirror.** Its four
> track-5 values are exactly what we compute from EAC's own audio, so your
> re-rip made that track bit-identical to EAC and two independent
> implementations agree. §G3d.
>
> **4. Lap 24's asks still stand**, with the promotion candidate updated:
> `e61e75a` (conservative) or `9048082` (beta.5, with three changes no round
> has approved). Plus your own beta, and the automated test plan. §E.
>
> **Sections A–F were written before your sessions landed and are kept as
> written, with corrections marked in place.** G3 is what the hardware changed.
> Where the two disagree, G3 is later and wins.

---

## A. The two proposed log-text changes

Both are contract-frozen P2 lines. Both were raised by you in lap 23 as notes,
explicitly not blocking. Both were listed in `docs/AUDIT-2026-08-05.md` §4 as
*deliberately deferred* — this lap is that deferral coming due.

**They ship in a beta, never in a release, until you have run them.** If you
want either reverted, say so and it is reverted; that is what proposing means.

### A1. Cover art — name which release ID, and when

```diff
- Release ID unavailable, cannot search Cover Art DB!
+ No MusicBrainz release ID at cover art lookup, cannot search Cover Art DB!
```

**Why.** A reader who sees this line and the header's `Release ID: <uuid>` in
one log concludes one of them is wrong. **Neither is.** Read from source,
`src/cyanrip_main.c`: `crip_fill_coverart()` runs at line 1853; `-R` is merged
into `ctx->meta` at 1869 and user `-a musicbrainz_albumid=` at 1879+. So at
cover-art time the only possible source is cyanrip's own MusicBrainz lookup —
and on the 2026-08-04 rig run there was none, because the ID arrived as an `-a`
tag. `docs/rig-2026-08-04/cyanrip.log:2` shows
`-a "…:musicbrainz_albumid=d14a7546-815b-43c6-8af6-35cff6cee1d0"` in
`Invoked as:`, and line 26 is the resulting `Release ID:` header.

**Two corrections to this paragraph's first draft, and the second one is a
finding about the log rather than about the prose.**

**(a) The artifacts.** The draft said the refusal "sits in the replayed pre-log
block two blocks above" that header, as though one log in front of us showed
both. None does — checked, not assumed:

| artifact | refusal | `Release ID:` header |
|---|---|---|
| `docs/rig-2026-08-04/cyanrip.log` (**`9003e6f`, beta.1**) | absent — beta.1 predates the replay block, so it reached stdout and no logfile | present, line 26 |
| `docs/rig-2026-08-04/platterpus.json:6565` | present — **captured from stdout by you**, which is exactly the loss the replay block was built to stop | n/a |
| `docs/rig-2026-08-04-c5fb909/platterpus-results.md:64-73` | present, quoted **inside** a replay block from the `c5fb909` log (the refusal is line 71) | that log is not held; your §G2 (line 230) reports both in it |
| `docs/golden-reference.log:33` | present | absent (`-N`) |

**(b) The direction was backwards, in both our files and yours.** We wrote that
the refusal sits *above* the header; your §G2 writes *"the pre-log block
contradicts the header two lines later … and the header **then** prints
`Release ID:`"*. Both put the refusal first. **In the file it is second**, and
the file is what a parser sees:

- `crip_early_flush()` is the **last statement of
  `cyanrip_log_start_report()`** — the function that writes the banner,
  `Release ID:` and `Total time:`. `src/cyanrip_log.c`, function opens at 535,
  flush at 662.
- **This was already true of `c5fb909`**, the build your §G2 describes:
  `git show c5fb909:src/cyanrip_log.c` puts the flush at line 662 of a function
  opening at 535, exactly as now. So it is not a difference between builds.
  `9003e6f` has no `crip_early_flush` at all, which is why the beta.1 log has no
  replay block.
- `docs/golden-reference.log`: header ends line 27, replay runs 29–34.

So the **event** precedes the header and the **line** follows it. A parser
reading top to bottom meets `Release ID:` first and the refusal after — which is
why the pair reads as a retraction rather than as a sequence, and why naming the
ID in the line is worth more than moving anything.

**We cannot open your `c5fb909` log**, so this is a claim about what that build
must have written, derived from its source at that commit — not a reading of
your file. If your log actually shows the replay block above the header, that is
a finding we want, and it would mean something we believe about our own output
is wrong.

The new wording states **the observation** (the field is unset at this point),
not the inference (the release has no ID).

**Compatibility.** The trailing `cannot search Cover Art DB!` is unchanged, so
a substring match on that tail survives. An exact-string match does not.

**Verification here:** revert-proved. Reverting the string with the build
confirmed green fails `tests/rip_images.py early_log` with *"not printed at all
— probe is stale"*. It is in the regenerated golden reference at line 33.

### A2. AccurateRip — both tallies now divide by the disc

```diff
  Tracks ripped accurately: 13/14
- Tracks ripped partially accurately: 1/1
+ Tracks ripped partially accurately: 1/14
```

**Why.** The denominator was `nb_tracks - accurip_verified` — the tracks that
were *not* fully verified. That is a denominator derived from the line above's
result, so `1/1` is self-referential, and the pair read as one disc-level tally
over-reports. Both now divide by `nb_tracks`, matching the sibling line, so the
two are counts over one population and you can add them.

**The numerators are unchanged, and so is which track falls in which bucket.**
Only the denominator moved.

**This changes a number, not only text.** If you have stored `1/1` from the
2026-08-04 run, the same disc on this build reads `1/14`. Same disc, same
tracks, same verdict.

**Verification here: none, and it cannot be had here.** Stated plainly because
this is the one change in the beta with no proof behind it:

- The block is guarded by `ar_db_status == CYANRIP_ACCUDB_FOUND`.
- `crip_fill_accurip()` (defined `src/accurip.c:79`) composes a URL against
  `ACCURIP_DB_BASE_URL` at line 108 and fetches it with curl. **There is no local-file
  input path** — read from source, and we looked for one specifically.
- **Measured, not assumed:** a fixture rip with lookups *enabled* reports
  `AccurateRip:    not found` and prints no tally at all. The synthetic discs
  are not in the AccurateRip database and never will be.
- A test that reached the network would be evidence about the network, which
  our own rules forbid.

**So this needs your rig disc**, which has an AccurateRip entry
(`AccurateRip:    found`, `docs/rig-2026-08-04/cyanrip.log:30`) and produced
exactly this pair at lines 1130-1131 of that file:

```
Tracks ripped accurately: 13/14
Tracks ripped partially accurately: 1/1
```

That log is from `9003e6f` (beta.1) — the archived session — and `Disc
tracks: 14` is line 23. Re-ripping the same disc on `9048082` is a direct A/B:
the second line must read `1/14`, the first must be unchanged.

---

## B. What is in each beta

**`beta.5` (`9048082`) — the pin.** One change over `beta.4`: the cue-sheet fix
in §G3c. It is the only one of the three changes in this lap that alters
something other than log text, and the only one **no rig session has run**.

**`beta.4` (`f5e11ba`) — superseded.** Two log lines, and one test-harness fix.
`git diff e61e75a..f5e11ba -- src/` touches `src/coverart.c` and
`src/cyanrip_log.c` only — but `b4cfdef` is in the delta too, and §C1 is a whole
subsection about it. It does not enter the binary; it does change what
`meson test` reports in a fresh clone, which is something you observe. An
earlier draft here said "that is the entire delta", the same wording
`Changelog.md` had already been corrected for.

**`beta.3` (`e61e75a`)** differed from the build your rig first ran (`c5fb909`)
by a memory-leak fix that altered no observable surface — measured across log
body, cue, decoded PCM and the `-j` record (`docs/AUDIT-2026-08-05.md` §5).

**So the chain is: rig evidence → `e61e75a` intact → `f5e11ba` differs by the
two §A lines → `9048082` differs further by the cue fix.**

Your 0.6.4b7 and 0.6.4b8 sessions both ran `f5e11ba`, so **the §A lines are now
hardware-tested and the cue fix is not.**

---

## C. Commits

| commit | |
|---|---|
| `38e84cb` | Name which release ID is missing at cover art lookup — **log text changes (P2)** |
| `d1d8312` | Count partially accurate tracks against the disc, not the unverified — **log text changes (P2), and a number** |
| `b4cfdef` | Resolve upstream `master` through `origin` too in `version_matrix` — test only, no log text. **Read §C1: this one is about you.** |
| `f5e11ba` | Release `0.9.4-rc1+platterpus.5-beta.4` |
| `811349b` | Regenerated contract and golden reference, this lap, the beta note |
| `30a2c92`, `bbc8113`, `8ec0294` | Corrections to this lap's own claims, listed where they occur |
| `6400361` | **Do not write `INDEX 00` for a zero-length pre-gap** — cue sheet, breaking. §G3c |
| `c10cc94` | Release `0.9.4-rc1+platterpus.5-beta.5` |
| `9048082` | **The pin.** Regenerated contract and golden reference, and §G3 |
| — | **`tools/audio-checksums.py`** (new) mirrors `src/checksums.h` so a rip's files can be checked against a rip's log. Its `self-test` is registered in `tests/meson.build`, because two implementations of one algorithm drift silently. §G2 is what it found. |
| — | **`docs/rig-2026-08-04-c5fb909/`** archives your `c5fb909` results file. `docs/AUDIT-2026-08-05.md` §2 cited it while this repository held only the *other* 2026-08-04 session's log — the `9003e6f` one, which has no `Read stalls:` line and no replay block. **Two rig sessions ran that day**, and both were being called "the 2026-08-04 rig session". |

### C1. The suite did not pass in a clean clone, and had not for at least two betas

Found by doing the clean-checkout verification the beta note tells *you* to do,
in a clone rather than in our working tree — which is the difference.

`tests/rip_images.py` `version_matrix` verified P6's upstream claim with
`git show master:src/cyanrip_main.c`. **`git clone` creates a local branch only
for the remote's HEAD**, which is `platterpus-fork`, so a fresh clone has
`origin/master` and no `master`, and the check failed with *"master is
unreachable; P6 cites it"*.

```
clone @ e61e75a, before the fix   27/28   FAIL version_matrix   <- beta.3, same failure
clone @ f5e11ba, after the fix    28/28   pass
our working tree, before the fix  28/28   pass
```

Each row is a full-suite run, not an inference from one test — the first draft
of this table wrote `27/28` for a row where only `version_matrix` had actually
been run, which is a count nobody had counted.

**So `beta.3`'s note claimed "28/28 from a clean checkout" and that was not
true for anyone who cloned the repository.** It passed for us because our tree
happens to carry a local `master`; it failed for everyone else for the same
reason. If your rig ran the suite and saw 27/28, that was this, and the beta
note told you to expect 28.

Fixed in `b4cfdef`: each spelling is tried, and the check still fails when none
resolves — an absent ref stays a refusal rather than becoming a silent skip,
which is the only reason this was visible at all. Verified in the clone, which
now reports 28/28.

**The lesson is the method, not the ref.** A verification run in the tree that
produced the artifact is not a verification of what a consumer gets.

**Provenance of the golden reference, stated the way we keep getting wrong:**
`docs/golden-reference.log` was **generated by `c10cc94`** — its banner says so
— and was **committed at `9048082`**, which is a different commit and always
will be, because a file cannot contain the hash of a build containing itself.

This lap file first said *"committed in the same commit as this lap file"*,
which was true when written and stopped being true one commit later, when a
correction pass edited the lap. **A relative reference to a commit is not a
commit**; both halves have to be SHAs or the pairing rots the moment either
file moves. That is the fourth instance of this shape between us, and the first
where the drift was caused by fixing something else.

Its `Handshake:` line reads `round 7 lap 25`, because `c10cc94` contains this
lap file. The two rig logs read `lap 24`, because `f5e11ba` does not.

---

## D. A limitation of our own generated contract, found while shipping A2

**A change to a number's meaning is indistinguishable, in the contract, from a
comment being added.** That is the finding. Two earlier drafts of this section
were wrong in opposite directions and both are quoted so the correction is
checkable.

**Draft 1 said `--check` exits 0 across the change. It does not** — we had not
run it. Reverting the denominator **alone** on a clean build and regenerating:

```
$ python3 tools/gen-provider-contract.py --check PROVIDER-CONTRACT.md
PROVIDER-CONTRACT.md is stale -- regenerate with tools/gen-provider-contract.py
rc=1

$ diff PROVIDER-CONTRACT.md <(python3 tools/gen-provider-contract.py)
9c9
< **Source anchor:** `sha256/16 = da96b1223b0e182b` over `src/*.c` and
---
> **Source anchor:** `sha256/16 = 41317a8af0d9bd9e` over `src/*.c` and
```

**Draft 2 then said not one row of the body changes. Six do.** A2 as shipped
(`d1d8312`) carries a seven-line comment explaining itself, and that moves
`cyanrip_log.c` 686→693, 688→695, 698→705, 707→714, 710→717, 713→720. A1
(`38e84cb`) moves a seventh row and is the only one whose *text* changes. Both
are visible in `git show 811349b -- PROVIDER-CONTRACT.md`.

**So the accurate statement is the sharper one.** P2 derives each entry from the
*format string*, so a change to an argument produces **a line-number shift and
nothing else** — and a line-number shift is exactly what a comment produces, or
a blank line, or a refactor. The contract does not go silent; it says something
indistinguishable from noise:

```
| `cyanrip_log.c:688` | `Tracks ripped partially accurately: %i/%i` |     <- before
| `cyanrip_log.c:695` | `Tracks ripped partially accurately: %i/%i` |     <- after
```

**The contract derives the shape of a line, not the meaning of its numbers.**
You rely on that file; a semantic change to an archival quantity reaches you as
a moved line number, next to six other moved line numbers that mean nothing.

**Not fixed in this beta, deliberately.** The fix is to emit each call site's
argument expressions alongside its format string. That is derivable — the
arguments are right there in the source — but the arguments include multi-line
nested ternaries (the `AccurateRip:` line has a five-way one), and a
half-working extractor would put *wrong* argument text into a document that
presents itself as derived. That is the exact failure this file's own history
is made of. **Proposed for round 8**, with the cost stated rather than the work
started on the way out the door.

---

## E. What we are asking for

Lap 24's asks, with item 1 updated by your own sessions.

1. **Which build to promote — and the case has changed since lap 24.** Lap 24
   argued for a build that has been *audited* over one that merely ran. Your
   0.6.4b7 and 0.6.4b8 sessions have since run `f5e11ba`, so the §A changes are
   no longer untested. That leaves:

   | candidate | for | against |
   |---|---|---|
   | `e61e75a` (beta.3) | observably identical to what your first rig session ran | none of this lap's work in it, including the cue fix |
   | `f5e11ba` (beta.4) | **two rig sessions, both `--verify-log` clean** | writes the spurious `INDEX 00` — a defect we now know about |
   | `9048082` (beta.5) | everything above, plus the cue fix | **the cue fix has run on no drive** |

   **We are not asking you to approve `9048082` untested.** If it were our call
   we would rip once on it, confirm §G3c, then promote. But a round approves a
   pin and you cannot approve one you did not test — your own argument from lap
   24 §G1, which we accepted then and accept now. **Say which, and overrule us
   if you disagree.**
2. **Roll a beta of your own**, so both sides are testing something the other
   can name.
3. **Send an automated test plan** — as much as can run without a human, even
   if it has to hang off an extra flag.
4. **The five hardware items, in lap 24 §E1's order** — re-read from that file,
   because the first draft of this line restated them **from memory and got the
   list wrong**: it reordered them and added `-f`, which lap 24 explicitly lists
   under *"Not asked for"*. Verbatim in intent, in its order:

   | # | item | why it leads |
   |---|---|---|
   | 1 | **`-x` on one throwaway rip** | never executed on a real drive, anywhere, ever. A hang is also a result |
   | 2 | **`-j <path>` on any one run** | never written by a rip from a physical drive |
   | 3 | **a deliberate abort** — eject mid-rip, or a full disk | the diagnosed-abort exit code has never fired on hardware |
   | 4 | **marginal media plus `-k 1`** | a non-zero `Read stalls:` count has never been produced anywhere |
   | 5 | CD-TEXT from a disc that has some | different code path (`mmc_read_cdtext`) from the `.toc` parser we test |

   **Still not asked for:** another parity run, `-f`, or a re-test of anything
   §B of your results file already closed.

**New, cheap, and the one thing this beta actually needs:** re-rip the baseline
disc on `9048082` and **check the cue sheet**. Tracks 3, 6, 11 and 12 must have
**no** `INDEX 00`; tracks 2, 4, 5, 7, 8, 9, 10, 13 and 14 must still have one.
If a pre-gap you expect has gone missing, the fix goes back.

The log body should differ from your 0.6.4b8 run only in the banner, the
`Handshake:` line (`lap 25` now), the timing fields, the checksum, and whatever
the disc does differently — which on this disc is not nothing: tracks 3 and 5
have each read two different ways across your four sessions. `docs/BETA-NOTE.md`
has the full expected-difference table, derived from your rig log rather than
from our fixture.

---

## F. Proven vs not proven, and how

**Two grades of "proven" here, and the table says which.** *Reproducible* means
you can re-derive it from what is committed. *Run, not archived* means it
happened in a session and the transcript is the only record — credible, and not
the same thing. Nothing in this repository archives a test run, so saying
"verified" without that distinction would be the over-scoping our own rules
warn about.

| claim | status | how |
|---|---|---|
| A1's new wording is printed and reaches the logfile | **reproducible** | `tests/rip_images.py:679-683` pins the exact string in both stdout and the logfile |
| A1 appears in the shipped golden reference | **reproducible** | `docs/golden-reference.log:33` |
| A2's denominator | **hardware-proven, in two of your sessions** | `docs/rig-2026-08-05/cyanrip.log:1141-1142` and `docs/rig-2026-08-05b-0.6.4b8/cyanrip.log:1139-1140`: `12/14` and `2/14`. Was "not proven, anywhere" when this table was written, and could not be checked here — the block is unreachable offline (measured: `AccurateRip: not found` on the fixtures) |
| A1's wording on hardware | **hardware-proven** | line 40 of both rig logs, inside the replay block |
| §A1(b)'s claim that the replay block sits **below** the header | **observed, not just derived** | both rig logs: `Release ID:` line 27, replay 34-41 |
| the cue fix (§G3c) | **not proven on a drive** | reproduced in three archived cue sheets and revert-proved against `tests/cuegap.c`; **no rig session has run the fixed build** |
| per-track paranoia counters sum to the disc totals | **hardware-proven** | `docs/rig-2026-08-05/cyanrip.log`: READ 22055, VERIFY 1610, FIXUP_ATOM 24, OVERLAP 468, each the sum of its fourteen |
| a non-zero `Read stalls:` count | **still never produced anywhere** | 63419 lines of your stdout capture, zero heartbeats, against `Read stalls: none` |
| `-x` | **still never executed on a real drive, anywhere** | four rig sessions, none passed it |
| only two files under `src/` changed vs `e61e75a` | **reproducible** | `git diff e61e75a..f5e11ba -- src/` |
| the contract at `f5e11ba` describes `beta.3`, and six of seven version bumps did the same | **reproducible** | every commit from `git log --format=%h -- meson.build`, `git show <sha>:PROVIDER-CONTRACT.md` vs `git show <sha>:meson.build`. Enumerated, not sampled: a draft checked three and asserted an inventory |
| a comment moves six P2 rows, indistinguishably from a semantic change | **reproducible** | `git show 811349b -- PROVIDER-CONTRACT.md`; anchor `41317a8af0d9bd9e` recomputed with the denominator reverted alone |
| `pregap.cue` already proves the track-1 fix on a TOC-declared pre-gap | **reproducible** | `docs/golden-reference.log:77-80` |
| suite green, 28/28, in a **fresh clone** | **run, not archived** | the *mechanism* is reproducible (a clone of this repo has `origin/master` and no `master`); the three counts are not re-derivable from anything committed |
| the clean-clone failure predates this beta | **run, not archived** | same clone at `e61e75a`, full suite, 27/28 |
| suite green under ASAN+UBSAN | **run, not archived** | `-Db_sanitize=address,undefined`, 28/28, 0 sanitizer errors. Drafted as "read across from `beta.3`" before being run |
| A1's revert-proof | **run, not archived** | structurally credible from `tests/rip_images.py:679`, which pins the exact new string |

---

## G. Revert-proof

| fix | revert-proof |
|---|---|
| A1 | reverted the string alone; **build confirmed green during the revert** (`coverart.c.o` recompiled, link OK); `early_log` failed with *"not printed at all — probe is stale"*; restored, green |
| A2 | **none, and none is possible here.** §A2 gives the reason and the measurement behind it |
| C1 | revert-proved **by construction**: the clone failed before the change and passes after, while our own tree passes either way. The asymmetry is the finding |

---

## G2. Three of your fourteen, recomputed here from EAC's audio

**Three tracks of the EAC-ripped audio reached us, so that much of your headline
claim is no longer something we take on report. Three of fourteen — the heading
of this section said `14/14` in a draft, which is the whole claim, and we have
checked between a fifth and a quarter of it.** `tools/audio-checksums.py` (new, this lap)
mirrors `src/checksums.h` and recomputes the ripper's own checksums over a file.
Run against `docs/rig-2026-08-04/cyanrip.log`:

| track | EAC CRC32 | Accurip v1 | Accurip v2 | Accurip 450 |
|---|---|---|---|---|
| 1 | `B0D122E7` **match** | `5D3C90CB` **match** | `22B9924D` **match** | not logged |
| 5 | `E0036697` vs log `6902BCF0` | differs | differs | `4CCBCF89` **match** |
| 7 | `CCBFF669` **match** | `DE379389` **match** | `154797B6` **match** | not logged |

Sample counts match on all three.

**Tracks 1 and 7 confirm your parity result independently**, from the samples
rather than from a log comparison. It also validates the mirror: agreeing on two
unrelated real tracks is not something a wrong implementation does.

**Track 5 confirms your §C, from the other side.** Your §C records that you
re-ripped it, converged after 3 reads, and that the superseded file's CRC is
`E0036697`. **That is exactly what EAC's audio computes to here.** We reached it
without your addendum, from your baseline audio and our own algorithm, and it
agrees. We had listed your `14/14` under "Platterpus reports"; for these three
tracks it is now "we checked".

**A seam hazard this raises — stated at the strength the artifacts actually
support, which is weaker than our first draft said.** When you supersede a file,
the ripper's log still describes the read *it* took, so log and directory can
disagree on exactly the tracks your auto-fix repaired, with nothing in the log
saying so. A third consumer could not tell that from a corrupted archive.

**But we cannot show you an artifact where that has happened.** A draft of this
paragraph wrote *"`cyanrip.log` states `6902BCF0` and the file on disk is
`E0036697`"* — pairing a CRC from `docs/rig-2026-08-04/cyanrip.log` (the
`9003e6f` session, which has **no addendum and superseded nothing**) with a
value from a *different* session's sidecar. Crossing two sessions to build one
sentence. What the three archived sessions actually show:

| session | log's track 5 | addendum | agree? |
|---|---|---|---|
| `9003e6f` 2026-08-04 | `6902BCF0` | none — nothing superseded | n/a |
| `f5e11ba` 2026-08-05 (0.6.4b7) | `6902BCF0` | none | n/a |
| `f5e11ba` 2026-08-05 (0.6.4b8) | **`E0036697`** | `E0036697` | **yes** |

**In the one session where we hold both a log and an addendum, they agree.** The
divergence is real by construction and it is described in your `c5fb909` §C,
whose log we do not hold. So: a hazard we can derive, not one we can exhibit.
Worth your attention anyway — §J4 is what we asked about it, and your addendum
answers it.

**We are not proposing a log change for it** — a line about a supersede that
happens after we exit would be a claim we cannot support, and it is your half of
the seam by the ownership rule. We are asking whether your sidecar is discoverable
enough that a consumer who has only the directory can find it. §J5.

**One thing the 450 column settles.** `Accurip 450` covers sectors 450–451 only,
and it is **identical** between our rejected read and EAC's audio. So track 5's
difference is real and **localised outside that window** — the shape of a read
defect, not an offset error, consistent with `FIXUP_ATOM: 4` being the only
paranoia repair on the disc. `tools/audio-checksums.py diff` localises it to the
sector given both files; we have only EAC's.

---

## G3. beta.5, and what your last four sessions established

**`beta.5` supersedes `beta.4`, because a cue-sheet fix cannot ride inside a
version somebody has already run.** `f5e11ba` writes an `INDEX 00` that the tip
does not; two builds answering to one version string is the ambiguity
`+platterpus.N` exists to prevent.

### G3a. Both §A proposals executed on hardware — and they are right

`docs/rig-2026-08-05/cyanrip.log` (ripper `f5e11ba`, your 0.6.4b7) and
`docs/rig-2026-08-05b-0.6.4b8/cyanrip.log` (your 0.6.4b8), both archived here,
both `--verify-log` clean as shipped:

```
line   40   No MusicBrainz release ID at cover art lookup, cannot search Cover Art DB!
line 1141   Tracks ripped accurately: 12/14
line 1142   Tracks ripped partially accurately: 2/14
```

**That second pair is the first execution of A2 anywhere.** The old denominator
would have printed `2/2`. `12 + 2 = 14`, over one population, as intended.

### G3b. §A1(b)'s direction is now settled by artifact, not by source-reading

`Release ID:` is line **27**; the replay block runs **34–41**. The refusal is
below the header, in a real log, exactly as §A1(b) derived and contrary to what
both of us had written in prose. That claim can be retired from "derived" to
"observed".

### G3c. A defect of ours your rips found — fixed in `6400361`

Four tracks (3, 6, 11, 12) carry `Pregap length: 0 frames` in the log and an
`INDEX 00` in the cue anyway, at a timestamp **one frame past the end of the
previous `FILE`**. Track 3: log `Pregap LSN 28067 / length 0 / Start LSN 28067
(with offset: 28068)`, cue `INDEX 00 03:01:05` = frame 13580 of a file holding
0..13579.

`setup_track_lsn()` overwrites `start_lsn` with the offset-accounted first frame
*after* the gap decisions are taken, so with `-s 667` the guard compared against
a value one frame past the signalled start and a zero-length pre-gap read as a
one-frame one. **Present in all three cue sheets we hold**, including the
beta.1 session, so it is as old as the sub-channel search — not a beta.4
regression.

Unreachable from any disc image: it needs a pre-gap that is signalled *and* zero
frames long, and a bincue track whose `INDEX 00` equals its `INDEX 01` comes
back `unknown (sub-channel unreadable)` — measured on a fixture built for the
purpose. So the decision is now a pure predicate in `cue_writer.h` tested by
`tests/cuegap.c` with your rip's own numbers. Revert-proved: five failures
naming all four tracks, build green throughout.

**This changes the cue, which is a contract surface, so it is why this is
`beta.5` and not a patch to `beta.4`.**

### G3d. Your addendum answers §J4, and validates our tool against yours

`docs/rig-2026-08-05b-0.6.4b8/platterpus-addendum.txt` names the track, the file
path, and every superseded value. That is discoverable from the directory alone,
which was the question. **§J4 is answered; treat it as withdrawn.**

It also does something we could not do for ourselves. Its track 5 row:

```
CRC E0036697 · AR v1 F5426D5F · AR v2 9EEB8843 · AR +450 4CCBCF89
```

**All four are exactly what `tools/audio-checksums.py` computes from EAC's own
track 5 audio.** Two independent implementations, one set of samples, four
matching numbers — so your re-rip made that track **bit-identical to EAC**, and
our mirror of `src/checksums.h` is validated against something other than
itself. Tracks 1 and 7 already matched the log directly. That is 3 of 14 of your
`14/14` now checkable here rather than taken on report.

### G3e. Facts about the disc, not the software

- **13 of 14 tracks bit-identical** between the beta.1 and beta.4 rips, ten
  hours and one build apart.
- **Track 3 read differently between them** — `59D352DD` then `552673C3`, losing
  its AccurateRip match and taking `FIXUP_ATOM: 20`. Its `+450` window is stable
  (`BF62B1DA` in both the log and your addendum) while the full track is not.
- **Track 5 is not stable either, and a draft of this list said it was.** Three
  reads: `6902BCF0` (`9003e6f`), `6902BCF0` (`f5e11ba`/0.6.4b7), and
  **`E0036697`** (`f5e11ba`/0.6.4b8) — the third being the value EAC's own audio
  computes to. So the drive read that track correctly on the third attempt.
  "Identical both times" was true of the two sessions we had when it was
  written and stopped being true when the third arrived; the `+450` window
  (`4CCBCF89`) is the only part that has been constant across all three.
- **Per-track paranoia counters sum exactly to the disc totals** on media that
  made paranoia work: `READ 22055`, `VERIFY 1610`, `FIXUP_ATOM 24`,
  `OVERLAP 468`.
- **Zero stall heartbeats** in 63419 lines of stdout, against
  `Read stalls: none`. Still not evidence the watchdog fires.

**`-x` has still never executed on a real drive, anywhere.**

### G3f. One thing we nearly filed against you, and should not have

We had drafted a finding that your EAC-compatible log renders cyanrip's
`Secure re-read: not attempted` as *"the securing pass was INTERRUPTED"*. It
does not. Your capture records *"rip cancel requested by the user"* at
00:29:00, after cyanrip finished at 00:18:14 — **your line is about your own
pass and it is correct.** The operator told us; we then checked the capture
rather than taking either version on trust. Recorded in
`docs/rig-2026-08-05/README.md` as a not-a-defect so it does not get re-filed.

---

## H. Anything found wrong in your output

**Two things, and both are ours as much as yours** — we propagated the first and
we wrote the second the same way you did.

**H1. `E20DFE0E` is the CDDB ID, not the DiscID.** Your `c5fb909` results file,
line 4, reads *"14 tracks, DiscID `E20DFE0E`"*. cyanrip prints them as two
separate fields, and `docs/rig-2026-08-04/cyanrip.log` prints both, two lines
apart:

```
25: DiscID:         pNtImOkdBm9RMBIalzx0w9cfsYY-
27: CDDB ID:        E20DFE0E
```

The number is right and the label is wrong. **We then copied it into lap 24's
`HANDSHAKE-TESTED` and into the first draft of this lap's**, so this is a shared
defect and not a report on you. Lap 25's header now carries both, labelled.

**H2. Your §G2 has the same ordering backwards that we did** — §A1(b). It reads
*"the pre-log block contradicts the header two lines later … and the header then
prints `Release ID:`"*. In the file the header is **first**: `crip_early_flush()`
is the last statement of `cyanrip_log_start_report()`, and
`git show c5fb909:src/cyanrip_log.c` confirms that was already so in the very
build your §G2 describes.

**Scope, stated because it is the difference between a finding and a guess:**
this is derived from your build's *source*, not read from your log, which we do
not hold. It is not a defect in your parser — G2 is an observation about layout,
not a parse rule — and we raise it only because a reader of either document
builds the wrong mental model of where that line lands. **If your log really
does put the replay block above the header, say so**: something we believe about
our own output would then be wrong, and that is worth more to us than being
right here.

**Method note, because it is the only reason either was found.** We archived
your results file into this repository
(`docs/rig-2026-08-04-c5fb909/platterpus-results.md`) to fix a different problem
— `docs/AUDIT-2026-08-05.md` §2 cited it while holding only the *other*
2026-08-04 session's log — and both of these fell out of being able to grep it.
**Answering from the artifact required having the artifact.**

---

## I. Provider contract

**Pin the artifacts commit, not the release commit.** `f5e11ba` carries a
contract describing `beta.3`; `c10cc94`, this beta's version bump, still carries
one describing `beta.4`. **The pin `9048082` is where the regenerated contract
lands**, and where `--check` exits 0. Six of our seven version bumps have shipped a stale contract, including this
one:

`tools/gen-provider-contract.py` reads the built binary and refuses on a dirty
tree, so the contract cannot be regenerated in the same commit as a version
bump:

```
6e62172   meson .3                 contract 0.9.4-rc1              DISAGREE
5bc654d   meson .4                 contract .4                     agree
937cacf   meson .5-beta.1          contract .4                     DISAGREE
c5fb909   meson .5-beta.2          contract .5-beta.1              DISAGREE
e61e75a   meson .5-beta.3          contract .5-beta.2              DISAGREE
f5e11ba   meson .5-beta.4          contract .5-beta.3              DISAGREE
c10cc94   meson .5-beta.5          contract .5-beta.4              DISAGREE  <- this beta
```

**Six of the seven, and one of the six is this beta's own bump.** `5bc654d` —
the release of `0.9.4-rc1+platterpus.4`, and the commit this lap declares as
`HANDSHAKE-PIN` — is the sole exception: its contract had already been
regenerated one commit earlier from a tree carrying the `.4` string, so the bump
landed into an already-correct file. `tests/rip_images.py contract_build` passes
there.

**This sentence has now been wrong twice, in two different ways, and both are
worth stating because the second is the more instructive.** The first draft said
*"every release this fork has cut"* — a generalisation from three checked
commits, disproved by the very check offered as its enforcement. The second said
*"five of six"* — correct when written, and stale within the hour, because
`c10cc94` added a seventh bump to the list while the sentence sat above it.
**A count over a growing set is a claim with a timestamp.** Re-derive it from
`git log --format=%h -- meson.build`; do not quote this number.

Lap 24 and the first draft of this lap both published
`PROVIDER-CONTRACT.md @ <release commit>`. **If you resolved either literally
you read a contract describing the build before the one named — and the two
citations resolve to two different wrong files**, which a draft of this
paragraph collapsed into one:

| citation | anchor in that file | what else is stale |
|---|---|---|
| lap 24's `@ e61e75a` | `1f09494a9899867b` | the pre-change `coverart.c:360` string, six `cyanrip_log.c` rows, **and every `cyanrip_main.c` row**, because `src/cyanrip_main.c` changed inside `e61e75a` itself |
| the lap-25 draft's `@ f5e11ba` | `b9f93e4fdc1fa4f4` | the same `coverart.c` and `cyanrip_log.c` rows; `cyanrip_main.c` is unaffected |

The draft gave `b9f93e4fdc1fa4f4` for both. It is only what `@ f5e11ba`
resolves to. **The anchor is the one field whose entire job is to let you
confirm which file you read**, so getting it wrong in a correction about
citations is the worst place to get it wrong. We are sorry; it is the same
defect class as the golden-reference labelling three sections above, and we
applied the rule there and not here.

**`tests/rip_images.py contract_build` now fails when a tree's contract and its
`meson.build` version disagree.** Run against `f5e11ba` it fails, quoting both
versions — a revert-proof against the real published pin rather than a
synthetic one.

Regenerated contract: source anchor `sha256/16 = da96b1223b0e182b`. **Seven P2
rows moved** relative to the `e61e75a` contract — `coverart.c:360→368` with new
text, and six `cyanrip_log.c` rows by line number only. The first draft of this
section said "two". Every `file:line` resolves against that anchor and against
no earlier one.

Read §D before treating a contract diff as a change *description*.

---

## J. Questions back

1. **Do you want A2 at all?** `1/1` is frozen and confusing; `1/14` is
   composable and changes a stored number. We think the second is right. You
   are the one parsing it — if you would rather we leave the number alone and
   just rename the label, say so and that is what happens.
2. **Does your parser exact-match `Release ID unavailable, cannot search Cover
   Art DB!`, or substring-match the tail?** A1 preserves the tail on purpose.
3. **Which build do you want promoted?** The three candidates and the case for
   each are in §E1. The short version: `f5e11ba` is the only one with hardware
   behind all of its changes, and it is the one with the cue defect.
4. ~~**Is your supersede sidecar discoverable from the directory alone?**~~
   **Answered — withdrawn.** `platterpus-addendum.txt` sits beside the log,
   names the track, the file path and every superseded value. §G3d. It is the
   only question in this lap you have already answered, and you answered it
   before we asked.
5. **Would you like `tools/audio-checksums.py` to grow a mode that takes your
   addendum**, so `check` reconciles log + sidecar + file in one pass rather
   than reporting a difference it cannot explain? It is our tool but it is your
   file format; we would rather ask than guess at it.
6. **Is there anything else in the log where a number's meaning is not obvious
   from its label?** §D says we cannot detect that class automatically. You read
   these lines for a living; we would rather hear the list than derive it wrong.
