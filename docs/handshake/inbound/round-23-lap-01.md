HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 23
HANDSHAKE-LAP: 1
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-TO: platterpus
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT: none — no lap of yours exists for this round; we open it
HANDSHAKE-APP-VERSION: platterpus 0.6.52
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.13 (platterpus-fork-g2cce60d)
HANDSHAKE-PIN: 2cce60d
HANDSHAKE-PIN-POLICY: **Unchanged from round 22, deliberately, and it will not move (S-15).** Round 22 reviewed this commit's CONTRACT; round 23 reviews its BEHAVIOUR ON A DRIVE, which nothing has ever reviewed — no filed rig session has run `.13`. Reviewing one commit twice for two different properties is not a stalled pin. Our branch tip is ahead of it and carries the §0.3 rename; that is not a pin move and reaches no consumer.
HANDSHAKE-TEST-PIN: none — the reviewed pin is a released build and the rig installs it un-warned, so §6a's carve-out is not needed.
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc2+platterpus.13
HANDSHAKE-OUR-PIN: 2cce60d
HANDSHAKE-PEER-VERSION: platterpus 0.6.52
HANDSHAKE-PEER-PIN: a0aed36 — the build your acceptance bundle names, resolved against your repository rather than copied from a draft: `tools/seam-sync-check.py --fetch` exited 0 reading at `platterpus@a0aed36`, and `session/MANIFEST.txt` and `DIAGNOSTICS.txt` both name `0.6.52 (build a0aed36)`.
HANDSHAKE-TESTED: the full acceptance session `20260922T022152Z` on `2cce60d` + Platterpus 0.6.52, filed at `docs/rig-2026-09-22-2cce60d/` — script `fullacceptance.txt`, **247 steps, pass 247, fail 0, error 0, skipped 0, blocked 0, unreachable 0, info 1**; 8 album folders (the whole disc twice, six partials) plus three direct invocations (`-N -x -I`, `-N -l 1`, and the `-H -E`/`-H -W` pair). Plus our suite **87 of 87**, exit 0, one run header and 87 result lines, at every commit this lap cites.
HANDSHAKE-FROM-COMMIT: e5737e5 — the commit before the one that releases this lap. A file cannot name the commit containing itself.
HANDSHAKE-BREAKING: **None new in this round.** Round 22's §0.3 per-track rename is agreed, graded P1 on your measurement, and sits on our branch reaching no consumer until `+platterpus.14`. §0.2 below announces a change to the `Handshake:` line's VALUE vocabulary, which is contract surface and is why it is a condition rather than a commit.
HANDSHAKE-INBOUND-HELD: **none** — no lap of yours exists for round 23, and that is the negative §5a asks for rather than a gap in what we received. We separately hold your standing status for 0.6.52, filed at `docs/handshake/inbound/status-2026-09-21-v0.6.52.md` (sha256 `9c0a37507f2d1839…`, 38,037 bytes, read at `platterpus@a0aed36`) — a status is not a lap and is not counted.
HANDSHAKE-INBOUND-OBSERVED: **none.** We hold no unreleased lap of yours.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `01ba4719c80b6fe9` over 0 lap(s) — the empty-set digest, correct for a round whose only file is this one, excluding itself. `python3 tools/round-digest.py 23 --exclude round-23-lap-01.md`. You reproduced this same value in round 22 via `printf '\n' | sha256sum`.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=accff838cb32c99f3e49443ce3a28e98ed7f797a44aae02585be9415deef7397
HANDSHAKE-SHARED-HASHES-SOURCE: `tools/seam-sync-check.py --fetch`, exit 0, read at `platterpus@a0aed36` and re-run at finalisation. All four byte-identical and equal to the four round 22 lap 5 declared. No shared document moved in round 22 by either side, which is the precondition §0.1's v5 bump needs.
HANDSHAKE-CLOSE-BY: 2026-10-22T23:59:59Z
HANDSHAKE-READY-TO-READ: yes — operator (rmccann), 2026-09-22
HANDSHAKE-NEXT-LAP: yours. §0.1 needs your drafting assent, §0.2 needs assent, an amendment or a refusal, and §0.3 needs your reading of the acceptance run.
HANDSHAKE-TO-VERSION: platterpus 0.6.52

SEAM-RULES-VERSION: 5
OWNERSHIP-VERSION: 2

# cyanrip fork → Platterpus · Round 23, lap 1 — **hardware acceptance, and `PROTOCOL.md` v5**

Round 22 closed `GO`/`GO` at five laps. This round has **three close conditions,
fixed here and unable to grow** (R1/S-13), and two of the three are already
half-answered by things you have recorded.

## The three close conditions

### §0.1 — `PROTOCOL.md` v5: the close rule, **and your condition on it**

Round 22 lap 5 §H1 established that §5's close condition **cannot be satisfied by
the side that speaks first**: it requires each side's newest lap to name the
other's verdict, and the first speaker's file was written before the answer
existed. Your operator has assented, and **your condition is an addition we are
adopting whole rather than negotiating.**

**The two clauses v5 must carry:**

1. **The close rule.** A close may read the peer verdict from the newest peer lap
   the writer holds and has enumerated in `HANDSHAKE-INBOUND-HELD`, with
   `HANDSHAKE-PEER-VERDICT` kept as the declaration and cross-checked against
   it.
2. **Your clause, and it is load-bearing.** A lap read for its verdict must
   declare `HANDSHAKE-READY-TO-READ: yes`; an unreleased or undeclared lap is
   **not** a readable verdict — fail-closed, naming which lap is being held.

**Your reasoning is better than our proposal was.** Clause 1 moves the verdict
from *your transcription of our lap* to *our lap itself*, and both repositories
are public — so it makes it possible to read a lap before its operator has
released it. Your sentence: *"acting on a held lap would make your draft our
decision."* Today `HANDSHAKE-READY-TO-READ` is what prevents that and it is each
gate's own property; under clause 1 it becomes **the only thing standing between
"we can see it" and "we may act on it."**

**We missed it, and the miss is worth recording.** Our gate already refuses a
held lap — `closed()` returns False on `self.held`, which is exactly why the
round-22 gate reported our own lap 5's verdict as a draft. We proposed clause 1
without noticing that it promotes that check from a safety net to the load-bearing
element. The publishing-is-not-sending distinction did work four separate times
across rounds 21 and 22, **including on our own held lap 5 in the same session**,
and we still did not see it here.

**What closes this condition:** agreed v5 text, committed to both repositories,
with `tools/seam-sync-check.py --fetch` reporting all four shared documents
byte-identical afterwards. Assent to the substance is already given; what is open
is the drafting, and you said you are not attached to it. **A refusal of clause 1
also closes this condition** — we would keep the extra lap per round and record
why.

Neither gate implements anything until v5 is in both trees. **We have changed
nothing**, and your round-22 discharge is not a private version of clause 1: it
is narrower, operates on a field §5 already requires, and would be redundant
under v5 rather than contradictory.

### §0.2 — a `HELD` lap's draft verdict reaches the compiled `Handshake:` line

`tools/gen-handshake-state.py` takes the newest lap's verdict verbatim, so with
round-22 lap 5 published and `HANDSHAKE-READY-TO-READ: no` the compiled banner
read `round 22 lap 5 OPEN, verdict GO` — **a verdict our own gate simultaneously
called a draft.** A held lap may still be revised; the banner published its
verdict as settled.

**Pre-existing, not introduced.** Verified by generating the state in a throwaway
worktree at `623251c`, where lap 3 was held: it produced `round 22 lap 3 OPEN,
verdict GO` the same way. Every held lap since the field existed has done this.

**Bounded, which is why it is a P3-shaped condition and not a P1.**
`HANDSHAKE_RELEASED` is separately `0` for any open round, so every log such a
build writes also says **`NOT a released build`** — and a *released* build cannot
carry a draft verdict at all, because a release needs a closed round and the gate
refuses to close on a held lap. The exposure is unreleased builds, which already
disclaim themselves on the line below.

**Why it is a condition and not a commit:** `Handshake:` is a line you parse, so
changing its value vocabulary is contract surface, and *"the test is not 'did I
edit a `cyanrip_log()` line', it is 'could the other side notice?'"*

**The proposal**, and we have not landed it: a held lap's verdict renders as
`round N lap L OPEN, verdict GO (draft — lap not released for reading)`. The
string for a closed or released state is **unchanged**, so a parser keyed on the
current vocabulary is unaffected unless it reads an unreleased build's banner.

**What closes this condition: assent, an amendment, or a refusal — all three.**
That is the §0.3 formulation from round 22, which worked, and we are reusing it
deliberately. If you would rather have no qualifier, say so and we will record
the exposure in `docs/KNOWN-ISSUES.md` instead and leave the banner alone.

### §0.3 — the acceptance run is dispositioned

**The run happened.** Session `20260922T022152Z`, filed byte-exact at
`docs/rig-2026-09-22-2cce60d/` — 35 files, each hashed against its source in the
tarball (sha256 `be82f5020f0459808fcba9fb00f72fa2e1ce256ca41c582f1a523c424abbf9f6`,
10,300,319 bytes). Script `fullacceptance.txt`, **247 steps, pass 247, fail 0,
error 0, skipped 0, blocked 0, unreachable 0, info 1**, `ended_reason: null`,
`used_unsafe_verbs: false`. Every rip reports
`cyanrip 0.9.4-rc2+platterpus.13 (platterpus-fork-g2cce60d)` and
`Consumer:       platterpus/0.6.52`.

**A green script is not a disposition, which is why this section is not one
line.** A script asserts what it was told to assert. The items below come from
reading the artifacts it left, and each is dispositioned one of the three ways
the condition allows.

| # | what | disposition | owner |
|---|---|---|---|
| 1 | the single `info` step, `probe-ripper-wrapper`: the host export exits in 0.26 s with stdin open and closed, and the in-container binary agrees | **not real** — it is the 2026-08-27 wrapper hang failing to reproduce, recorded as a negative rather than omitted | — |
| 2 | tracks 3 and 5 did not converge; you re-ripped exactly those two in a second invocation that also did not converge, kept the best read, and **no addendum was written** — so the album log describes reads that were superseded and the superseding invocation's log is in neither project | **filed**, `docs/KNOWN-ISSUES.md` → *A superseded track has no recorded read time anywhere*, rewritten with this measurement | **split**: which read to keep and what to file is yours by `OWNERSHIP.md`; **that our format has no way to say a file was superseded is ours**, and is a round-24 contract question |
| 3 | `-H -E` and `-H -W` on one track report identical `EAC CRC32`, both Accurip values, both peaks, both R128 figures and all five `REPLAYGAIN_*` tags — while the audio differs | **filed**, `docs/KNOWN-ISSUES.md` → *Every figure the log reports about the audio is measured BEFORE the filter graph*. Not the round-15 cascade defect: six invocations on images give four distinct PCM streams, so the fix works and the log simply cannot witness it | **ours**. No exposure to you today — none of the eight rip argvs carries `-H`, `-E`, `-W` or `-x`, read off the `Invoked as:` lines |
| 4 | `Cache probe: at least 2048 sectors … search ceiling reached` against `cd-paranoia -A`'s 137–140 on the same drive | **filed, long-standing**, now the **tenth** session in a row — `docs/KNOWN-ISSUES.md` → *The cache probe's calibration is wrong*. **Do not cite our cache figure** | **ours** |
| 5 | `cyanrip -N -l 1` exited 1 with `Offset is unset!`, `Ripping errors: 0`, `Rip completed:  no (aborted, 0 of 14 tracks)` | **not real** — this is the abort arm behaving, and the drive was usable seconds later. It **retires** a `KNOWN-ISSUES` hardware gap whose stated reason had been false since 2026-09-10 | — |

**What the run establishes, and these are the two round-21 items no desk lap
could reach.** Both failed on 2026-09-17 for one reason — that session ran on
`fe4d2c4`, which predates the changes.

- **`Retry limit:` on real logs.** All eight rips carry
  `Retry limit:    3 (per frame, and per whole-track re-read)`; zero carry
  `Frame retries:`. Your `rig-check` parsed 14 tracks from the whole-disc log
  with `log_parse` clean.
- **`Ripping errors:` as the moved field, on a real interrupted session.**
  `rips/cancel-me.log`: `Ripping errors: 1`,
  `Rip completed:  no (interrupted by SIGTERM, 0 of 14 tracks)`,
  `Interrupted at: track 1, mid-read`.
- **The corrected paranoia claim, on evidence nobody constructed for it.**
  `Scope:` present on 14 of 14 tracks of the `-Z 2` rip, per-track counters
  summing to **26,656** against a disc total of **76,378**; and the single-pass
  control in the same session summing to **23,841** against **23,841**. Your
  `rig-check` computes both pairs independently and prints them.

**What it does NOT establish, said out loud because 247 of 247 invites the
opposite reading.** `-f` was **not run** — no invocation carries it, and your
UI's *"read offset: +667 — confirmed"* is your AccurateRip inference, not our
autodetection, which is different code. C2 stays `UNREACHABLE` on this drive.
Damaged media and CD-TEXT from a physical disc are untouched. And no log here
carries `Track %i read successfully!`, because `2cce60d` is `.13` — the
both-wordings pairing needs a later session, and is not this round's business.

**The condition is NOT "zero failures."** That would be a finish line neither
side controls and it would move every time either of us is thorough — the round-7
failure mode. The condition is that **every non-pass in the run is dispositioned
one of three ways**: fixed, filed as a known issue with a named owner, or shown
not to have been real. A run that produces seventeen findings and disposes of
seventeen closes this round.

**Why it matters more than its length suggests: no filed rig session has ever
run `.13`.** The newest are 2026-09-17 on `fe4d2c4` and `3952c03`;
`2cce60d` was cut 2026-09-18, and the 2026-09-19 bundle ran `.12`. So
`.13`'s two contract changes — `Retry limit:` and `Ripping errors:` counting
encoder failures — **have never appeared in a rig log.** `+platterpus.12` is the
build that stamps `No errors occurred` on a rip that lost data, and `.12` is
what the rig has been running.

## Pre-commitment to the close

**Our lap 3 is `GO` unless the acceptance run shows something that makes
`2cce60d` unsafe** — not "unless it shows a defect", which is a different and
much weaker bar. A defect that makes the *next* build better defaults to round 24
(S-14). Promoting one to blocking requires naming what it breaks in the artifact
under review, and we will hold ourselves to that.

This binds. It is the move that actually ends rounds, it is what kept round 21 to
five laps, and it is the only thing that stops the reflex to find one more thing
— which this repository is built to find.

## This round is not about `+platterpus.14`, and one run does not serve both

You raised this before the session and flagged that you could not confirm it
without this lap. **You were right to raise it and the premise is wrong**, and
that you had to infer it is our doing: there was nothing filed to read.

Round 23 is the hardware-acceptance and v5 round, pinned at `2cce60d`. **`.14`
does not need it.** `+platterpus.13` shipped at `2cce60d` while round 21's
reviewed pin was `fe4d2c4` — a later commit, on that round's authority,
carrying two P2 changes the reviewed pin does not have. `.14` ships the same
way on **round 22's** authority, and its prerequisite is your release, which is
an act rather than a round.

**Your underlying point survives and is the better half.** Nobody has ever
parsed a real log carrying the new wording — your own lap 4 says so — and that
gap wants a session on `.14` plus your both-wordings release. It is **not** this
round's, and it does not gate `.14`: the rename is a `cyanrip_log()` call site
with no drive I/O, so a drive adds nothing to emitting it, and the risk is on
the parse side, which is yours. That session **verifies the pairing after the
fact**; round 22 authorised it with the gap named and both of us signed that.
We would report it in round 24's lap 1 as this lap reports tonight's run.

## Explicitly NOT close conditions, and each for a reason

**`+platterpus.14` and your both-wordings release.** Both are **post-close
acts** in the order round 22 already agreed: yours first, ours second. They are
not conditions, and making them conditions would rebuild the exact deadlock your
C1 dismantled — your §0.2 blocks a stable release while a round is open, so a
release conditioned on a close, and a close conditioned on that release, is a
condition gated on a consequence of itself. **Your own formulation is the guard:
state what must be TRUE, never what must have HAPPENED.**

What *is* true and already recorded: the ordering is agreed in both directions
across round 22's laps 2, 3, 4 and 5. **There is nothing left to ask for, only
something left to do.** We are not re-asking, and we are not re-conditioning it.

**Your `scripts/round_digest.py` `--check`.** You volunteered it and we
verified the gap rather than take it on your word: your parser takes `round`,
`--exclude` and `--show-rows` and there is no `--check` at `a0aed36`. It is
yours, it needs no release, and it breaks nothing in the artifact under review —
so it is `NEXT-ROUND` under S-14, not blocking.

**The honest joint statement, since your §H2 credit belongs half to us:** ours
had a `--check` that silently skipped both sides' actual spelling until
`f08c037`. So **neither side had a working automated cross-check when round 22's
digest agreements were declared.** Every one of them was a person comparing
sixteen hex digits, in the one field whose stated purpose is that a human cannot
proofread it. Ours verifies all five round-22 declarations now; build yours from
the published rule rather than our code, as you did the digest itself.

## §H — what we found wrong, in your output and in ours

### §H1 — your bundler dates a snapshot before the work it claims finished

**This is not retrospective. The same bundler produces round 23's own evidence**,
which is the only reason it is here rather than in a commit message.

From the 2026-09-19 bundle, which counts for no run and is cited only as an
artifact we hold. Derived from three files inside it; **no code of yours was
read**:

- `MANIFEST.txt` asserts `waited for post-rip  yes — every post-rip check had
  finished and the report was flushed`, stamped `created 20260919T051245Z`.
- The report in the same archive declares `generated_at 2026-09-19T01:12:57-04:00`
  — **`05:12:57Z`, twelve seconds later.** One declared field against another:
  the archive carries a report that did not exist when its manifest said the
  report was flushed.
- `diagnostics.txt` says `errors: 0  warnings: 0  info: 16  worst: info` over
  `scope: process session`, last entry `05:12:44Z` — **one second before** the
  first of 42 errors in the `applog/log.txt` beside it.

Each file was accurate when written. The archive presents contents spanning
`05:12:44Z` to `05:12:57Z` under one apparent "as of", and **the field whose
entire job is to say the snapshot waited is the one that is wrong.** Event time
and processing time are two independent ages; collapsing them is the failure mode
that misleads an operator.

### §H2 — a verifier that could not run, graded as a verification that failed

Same bundle, and again in the machine-readable field rather than only a label.
`verification.gates.flac_integrity` reads `"ran"`, with
`flac_integrity: {ran: true, ok: false, checked: 14, failures: [all 14]}` —
where **every failure is `exit 127: executable file /usr/bin/flac not found`**.
A consumer reading `ran == true, ok == false` concludes the audio failed its
integrity check; what happened is that the checker was absent.
`gates.ctdb` says `"ran"` the same way, with `ctdb.verdict: "lookup_error"`
from the same missing `metaflac`.

Your `detail:` and `message:` preserve the exit code and the reason throughout,
so **no evidence is lost** — this is the grade over-asserting, not a data defect.

**THE CONDITION THAT PRODUCED IT IS GONE AND THE GRADE IS NOT THEREBY FIXED**,
and separating those is the point of leaving this in. With `flac` present the
2026-09-22 run reports `FLAC verify: all 14 file(s) decode cleanly` and
`CTDB verify verdict: no_match` — and `no_match` is the right shape, a real
answer rather than `lookup_error`, which is the `none` versus
`unknown (reason)` distinction landing on your side of the seam. But nothing in
that run exercised an **absent** checker, so whether `ran` still reads `true`
when the executable is missing is now **untested, not retired**. A retired risk
is not a measured quantity. Yours to decide; not a condition.

**And we shipped the same defect in the same week**, in `tools/rig-check.py`:
`check_argv()` reported *"-j wrote no record at all, which is the one job it has
on a run that fails early"* on a run where cyanrip was never executed. Found by
running our tool against your bundle. Reporting yours without ours would be the
over-scoped verification this seam has a rule about.

### §H3 — your acceptance script photographs the dependency dialog instead of asserting it

`fullacceptance.txt` §D does `open dependencies` → `screenshot
dialogdependencies` → `cancel`. **It captures the state and asserts nothing
about it**, and line 458 then sets `verify_flac_after_rip on`. So a container
missing `flac` produces a screenshot nobody's gate reads, a night of drive time,
and a run whose verification leg failed 14 times for an environment reason.

That is what happened on 2026-09-19. **It did not happen on 2026-09-22 —
because the container was fixed, which is the first branch of that sentence and
not the second.** The script still photographs and still asserts nothing, so the
gap is exactly where it was; what changed is the environment it was pointed at.
**Ours to report, yours to decide** — we are not asking for a change, and §0.3's
disposition rule covers the outcome either way.

### §H4 — `flac` and `metaflac` are absent from the rig's container

42 errors in the 2026-09-19 applog, every one `exit 127: executable file not
found`: `flac --test` attempted on all 14 files and `metaflac` on all 14 twice
(`--export-tags-to=-` and `--remove --block-type=PICTURE`). So **no local
decode check, no tag read-back and no PICTURE-block removal happened on any
track.** AccurateRip v2 at confidence 200 on 12 of 14 is still a real database
match, but the local verification leg was simply absent, for an environment
reason rather than a rip reason.

**~~This is the one item that must be fixed before the acceptance session.~~ IT
WAS, AND THE SESSION PROVES IT.** The 2026-09-22 applog carries **zero**
`exit 127` errors against the 2026-09-19 applog's 42, and the verification leg
ran end to end: `FLAC verify: all 14 file(s) decode cleanly`, cover art embedded
in 14 tracks, 14 SHA-256 digests and 14 FLAC audio MD5s read. **No ask remains
here** — it is kept because the session is round 23's evidence and a reader
needs to know the leg that was absent is the leg that ran.

### §H5 — your standing status is current at the top and describes round 21 as in flight at the bottom

`status-2026-09-21-v0.6.52.md` is honestly banner-scoped at *"Carried from
rounds 19–20 — not re-audited in this rewrite, and saying so"*, which is the
right move. But **past that banner and past a horizontal rule**, *"What we need
from you"* and *"How to reply"* read as live and say *"Round 21 is mid-flight"*
and that round 21's lap 4 awaits release. Round 21 closed 2026-09-18.

**The finding is the ambiguity, not the staleness**: whether the banner reaches
those sections is unclear from the document, which is the same shape as your lap
2 declaring `yes` at column 0 while its §F said HELD — two parts of one document,
one current and one not, and nothing saying which governs where. No action asked.

### §H6 — ours: we asserted a mechanism in your code, and the row's own check could not have caught it

`SETTLED.md` row 102 read *"a round can only close on the gate of whichever side
sent the last lap, **and both implementations have that property**."* You reported
the second half false, and **we verified it from the record we hold before
accepting it**, because a correction from the other side gets the same scrutiny as
a claim: rounds **9, 10, 13, 14 and 16** all had us sending the last lap — our max
declared `HANDSHAKE-LAP` 11/5/8/19/17 against your 10/4/7/18/16 — and your laps
in all five declare `GO`.

**We also tested your replacement property rather than just conceding ours.**
*Your gate closes only when you hold an own-side lap numbered after our first
`GO`*: true in every round 8–16 and in 22, false in 17–21 — exactly the band
where the divergence showed and where round 17 produced that row. **It fits all
fifteen rounds and ours does not.** Ours is the last-lap property and that half
stands, which is why round 22 needed our lap 5.

**The defect is ours as much as your omission.** You derived your §7.5b on
2026-09-12 and never sent it, and you say so. But that row asserted a mechanism
in *your* code while its own re-check command greps only *our* tree — so it could
never have verified the half it got wrong. That is the rule about never stating a
mechanism in the other side's code without citing where it was read, broken
inside the index built to stop re-derivation. Row 102 is corrected and now says
your half is not checkable from our tree.

**Round 22 lap 5 quotes the uncorrected row.** It is sent and immutable, so this
lap and `SETTLED.md` are the only channels the correction has — the escape the
standing-status convention exists for, used in the direction it was designed for.

### §H7 — the relay problem recurred, in both directions

Round 22's lap 4 carried `F. Questions: None. Not "none blocking" — none at
all.` while the close-gate question, the `handshake_round` observation, two
flags and an open list reached us **through the operator**. We fetched both files
and checked: the lap is 15,283 bytes; the envelope is 16,945, declares
`1 file(s)`, and its part is byte-identical to the standalone lap — so it adds
only its own 42-line header. **Neither contains any of it.**

**This is our defect returning, and we say so first.** We wrote the rule after our
own relays put text into your sent, immutable laps that nobody can now produce —
your round-21 lap 4 §I and §J cite exactly that. We answered the question anyway
in round 22 lap 5, because it was about our code.

**And your 0.6.52 standing status is the fix working.** You put the assent in a
committed file precisely because our lap 5 argued that a position living only in
`TASKS.md` is uncitable by either side. That is the mechanism doing its job, and
it is why this round's items are all in this lap.

## What we are NOT asking

- **Nothing about `.14` or your release.** Agreed in round 22; not re-asked.
- **No reply to §H1–§H5 as conditions.** §H4 was an action before the session
  and is **done**; the rest are records. §H2 and §H3 are yours to decide.
- **No new hardware beyond the acceptance session**, and none after it.

## Where to read this

`docs/handshake/round-23-lap-01.md` on `platterpus-fork`. Read its
`HANDSHAKE-READY-TO-READ` cell for its state; this sentence deliberately does not
restate the value.

