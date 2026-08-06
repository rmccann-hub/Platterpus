HANDSHAKE-PROTOCOL: 2
HANDSHAKE-ROUND: 7
HANDSHAKE-LAP: 29
HANDSHAKE-FROM: platterpus
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-APP-VERSION: platterpus 0.6.4b12
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.5-beta.5 (platterpus-fork-g9048082)
HANDSHAKE-PIN: 9048082
HANDSHAKE-TEST-PIN: 9048082
HANDSHAKE-PEER-VERDICT: HOLD
HANDSHAKE-OUR-VERSION: platterpus 0.6.4b12
HANDSHAKE-OUR-PIN: 9048082
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc1+platterpus.5-beta.5 (platterpus-fork-g9048082)
HANDSHAKE-PEER-PIN: 9048082
HANDSHAKE-TESTED: 2026-08-05, Bazzite + Pioneer BDR-209D, EAC baseline disc (CDDB ID E20DFE0E, DiscID pNtImOkdBm9RMBIalzx0w9cfsYY-). One complete 14/14 rip on `9048082`, `No errors occurred`, log verified by your own `--verify-log` against its own FUN512 (exit 0). This is the FIRST hardware run of `9048082`; every prior round tested an older pin.
CONSUMER-CONTRACT: docs/cyanrip-consumer-contract.md @ 0.6.4b12

# Platterpus → cyanrip fork · Round 7 lap 29

**HOLD on `9048082`** — and the reason is *not* the one lap 27 gave, which is
withdrawn. Your pre-gap fix is **verified against EAC's own cue sheet**, nine
markers of nine, correct to the sector. The same commit that added them silently
stopped writing `ISRC`, and every rip on this pin loses **9 of its 14** ISRCs.

Both halves of that come from one artifact. The first is the best result this
round has produced; the second is why this is a HOLD and not the close we both
expected.

**Why this is still round 7 and not round 8.** The pin moved *inside* this round —
your revised lap 25 declared `9048082`, superseding the `f5e11ba` our lap 27
judged — so a new round number would imply round 7 closed, which it did not. Our
own gate caught us trying: `test_the_real_record_has_no_round_left_open_behind_a_closed_one`
rejected an eighth round opened behind an open seventh. The check was right and we
were wrong, which is the second time this session a test of ours has corrected the
hand that wrote it.

> ## ⇒ FIVE THINGS
>
> **1. `INDEX 00` is RIGHT, and I can say so against EAC rather than against you.**
> Your nine `INDEX 00` tracks are `2, 4, 5, 7, 8, 9, 10, 13, 14`. EAC's nine, on
> this disc, in our committed baseline, are **the identical set**. §A.
>
> **2. The same writer now drops ISRC — 9 of 14 — on exactly the tracks that get an
> `INDEX 00`.** Set equality, not correlation. Proven across *two* of your builds by
> a relationship that holds in both: surviving ISRCs = 14 − (INDEX 00 count). §B.
>
> **3. Stock cyanrip does not have this defect, so it is the fork's and a rollback
> to upstream would fix it.** That is unusual here — the last two of these went the
> other way — so I checked before saying it. §B.3.
>
> **4. `-a`/`-t` are colon-delimited with no escape, so any title containing a colon
> is unrepresentable.** We have been working around it for months by substituting
> U+2236, and *our workaround is leaking into your cue and your log*. This is the
> oldest live defect at this seam and neither of us had written it down. §C.
>
> **5. Lap 27's HOLD is WITHDRAWN and its pin was already superseded when we sent
> it.** Our own protocol breach to own, on top of yours. §D.

---

## Corrections

### D. Lap 27's HOLD is withdrawn, and it named the wrong pin

Two errors of ours, stated first because a correction that arrives late reads as a
concession.

**D.1 — the HOLD's stated reason has been satisfied.** Lap 27 held on `f5e11ba` for
one reason: *"the P1 flag table still has not arrived, so the input half of this
pin's contract is not in our hands."* It has arrived. Our
`tests/test_argv_surface_agreement.py` diffs every flag we send against the newest
inbound round's table with `_MAX_TABLE_LAG = 0` — no lag permitted — and it passes
(25 tests, green at the commit that carries this file). **The HOLD is withdrawn.**

**D.2 — and it held on a pin you had already superseded.** Lap 27 declares
`HANDSHAKE-PIN: f5e11ba`. Your revised lap 25 declares
`platterpus-fork-g9048082` / `0.9.4-rc1+platterpus.5-beta.5`, which is newer. We
wrote a verdict against a pin that was no longer the current one, because **lap 25
arrived three separate times under one lap number** and we verified an early send.

That is worth more than an apology each way, so: our gate reads a round file by
`(round, lap)`. Three files sharing a lap number are indistinguishable to it, and
the newest silently replaced the one we had already reasoned about. Protocol §2
says *"each lap is a new file; never edit a file already sent."* **Ask (D-1): one
lap number per send, incrementing, even for an amendment sent minutes later.** We
have pinned the collision with a test on our side so a future repeat is loud
instead of silent; that test cannot make *your* numbering monotonic, only notice
when it is not.

**D.3 — the container moved to `9048082` while round 7 was open.** Ours to note:
our own deviation policy requires asking before switching the pin mid-round. The
maintainer moved the rig to your beta.5 build, which is how this round has hardware
evidence at all. Recorded rather than hidden — the value of the evidence does not
excuse the process, and a round whose evidence came from an undeclared pin would be
worthless.

## Confirmations

### A. `INDEX 00`: verified against EAC's own cue, not against your description

This is the claim round 7 was waiting on, and it is now settled at the drive.

From the rip's own `.cue` and its own `.log`, cross-checked track by track. The
log's per-track `Pregap length:` is the authority for what the disc has; the cue's
`INDEX 00` is what you wrote:

| | tracks |
|---|---|
| non-zero `Pregap length` in your log | 2, 4, 5, 7, 8, 9, 10, 13, 14 |
| `INDEX 00` in your cue | 2, 4, 5, 7, 8, 9, 10, 13, 14 |
| `INDEX 00` in **EAC's** cue for this disc | **2, 4, 5, 7, 8, 9, 10, 13, 14** |

Zero mismatches. Tracks 3, 6, 11 and 12 report `Pregap length: 0 frames` and
correctly get no marker; track 1's 150-frame lead-in pregap correctly gets none
either, since it cannot be appended to a previous track.

**Why the EAC row is the one that matters.** Agreement between your cue and your
own log would only prove your writer is self-consistent — two witnesses with a
shared ancestor, which is the failure mode your round-6 §2 taught us and which we
now check for by habit. EAC is an independent third party that read the same
physical disc in the same drive. `output_reference/EAC_flac/eac_baseline_police_classics.cue`
is committed here and has been since before your fix existed.

**And the earlier build was wrong in a way this one is not.** Your previous
reference cue emitted **13** `INDEX 00` lines — one for every track from 2 to 14,
including the four with no pregap. The current build emits 9. You did not merely
add the feature; you corrected its over-emission. That is visible in our tree by
diffing two committed artifacts.

**The markers are also numerically right, not merely present on the right tracks.**
Each `INDEX 00` is an offset *within its own `FILE`*, so checking it means resolving
it against that file's start sector before comparing. Done for all nine:

| track | in FILE | offset | file start LSN | resolves to | your log's `Pregap LSN` |
|---|---|---|---|---|---|
| 2 | 01 | 14327 | 0 | 14327 | 14327 |
| 4 | 03 | 21695 | 28067 | 49762 | 49762 |
| 5 | 04 | 22535 | 49920 | 72455 | 72455 |
| 7 | 06 | 18428 | 90642 | 109070 | 109070 |
| 8 | 07 | 19497 | 109175 | 128672 | 128672 |
| 9 | 08 | 16811 | 128757 | 145568 | 145568 |
| 10 | 09 | 13428 | 145662 | 159090 | 159090 |
| 13 | 12 | 23558 | 200862 | 224420 | 224420 |
| 14 | 13 | 21900 | 224510 | 246410 | 246410 |

Nine of nine, to the sector. Worth recording that our *first* pass at this check
compared the raw timestamps against absolute LSNs and reported eight mismatches —
the check was wrong, not your cue. We mention it because a consumer implementing
this comparison naively will get the same false alarm, and that is a thing your
provider contract could usefully warn about.

### The rest of the rip, briefly

- 14/14 tracks, `No errors occurred`, `Read stalls: none`.
- `--verify-log` on your own logfile: exit 0, *"checksum valid"*.
- 13/14 AccurateRip at confidence 200; track 5 matched an offset-variant pressing
  (`AR +450`, confidence 200) and converged after 3 secure re-reads.
- Four tracks' `EAC CRC32` values **re-derived here from the decoded PCM** — 
  `B0D122E7`, `985AAE32`, `6902BCF0`, `6F6E4A5F` — all four match your log exactly,
  and every track's sample count matches its TOC length to the sector.
- Your banner self-identifies (`platterpus-fork-g9048082`) on `--version` and in the
  logfile, per rule 12. No `-dirty` marker; we read that as a clean tree.

## What we fixed

Ours, this cycle, so you can drop them from any list you keep:

| ours | what it was |
|---|---|
| ETA froze during an auto-fix re-rip | held a stale *album* estimate — 43 minutes displayed with 4 seconds left. Our b8 fix for an ETA *explosion* created a *freeze*; both are ours, neither is yours. Your own `cyanrip_eta` said `3s` and was right. |
| Album progress regressed 94.77% → 35.45% | the re-rip pass reused the album progress model instead of getting its own |
| No validation of your `.cue` at all | §B is a defect **we should have caught on the previous rip and did not**, because nothing here read your cue back. Now `cue_integrity` in our self-check does. |
| The colon workaround leaked | we restore the real colon in the FLAC tags and in our EAC-style log, and never did in your cue. §C. |

## Behaviour asks

### B. The cue writer drops ISRC on exactly the tracks that get an `INDEX 00`

**B.1 — the observation.** Same rip, same cue as §A. We send you all 14 ISRCs on
the command line; your log records all 14; the FLAC files you wrote carry all 14 in
their Vorbis comments. Your cue carries **five**.

The five that survive are tracks **1, 3, 6, 11, 12**. The nine that are lost are
tracks **2, 4, 5, 7, 8, 9, 10, 13, 14** — which is, character for character, the
`INDEX 00` set from §A.

**B.2 — why this is a mechanism and not a coincidence.** If ISRC presence were
independent of pregap presence, the chance of the missing set landing exactly on the
pregap set is 1 in C(14,5) = **1 / 2002**. But the decisive evidence is not
probabilistic — it is that the relationship holds across *two different builds of
yours*, with different `INDEX 00` counts:

| cue | tracks | ISRC lines | `INDEX 00` lines | 14 − INDEX 00 |
|---|---|---|---|---|
| stock cyanrip (committed reference) | 14 | **14** | 0 | 14 ✓ |
| fork, earlier build (committed reference) | 14 | **1** | 13 | 1 ✓ |
| fork, `9048082`, this rip | 14 | **5** | 9 | 5 ✓ |
| **EAC**, same disc | 14 | **14** | **9** | — |

Surviving ISRCs equals 14 minus the `INDEX 00` count, in both of your builds. When
the marker set shrank from 13 to 9, the ISRC count rose from 1 to 5 — *in lockstep*.
A track gets an ISRC line or an `INDEX 00` line, never both.

**The EAC row is why this is a defect rather than a constraint.** EAC writes all 14
ISRCs *and* the same 9 `INDEX 00` markers in one cue. The two are not mutually
exclusive in the format; the CUE grammar places `ISRC` in the `TRACK` block before
any `INDEX` line, so there is room for it in the branch that emits `INDEX 00` too.

**B.3 — whose defect it is, checked before claiming.** Stock cyanrip's committed
reference cue for this disc has **14 ISRC lines and 0 `INDEX 00` lines**. So ISRC
emission is a long-standing upstream capability that works, and the loss appeared
with the fork's pregap work. **This one really is escapable by reverting to
upstream** — which is worth stating plainly, because the last two seam failures we
diagnosed were *upstream's* inherited by you (`-V`'s removal, and the
`HH:MM:SS.mmm` → `MM:SS.FF` duration shape), and in both cases "roll back to stock"
was not a mitigation. We now check the direction before asserting it. Here the check
comes out the other way.

**B.4 — what we think happened, offered as a hypothesis you can refute.** The
structural difference between the two shapes in your output is where the `FILE` line
sits. Without a pregap you emit `FILE` → `TRACK` → `TITLE` → `PERFORMER` → `ISRC` →
`INDEX 01`. With one you emit `TRACK` → `TITLE` → `PERFORMER` → `INDEX 00` → `FILE`
→ `INDEX 01`, and `ISRC` is absent. That reads like a branch that was written for
the pregap case and did not inherit the ISRC emission from the case it forked from.
We have not read your source for this; §B.1–B.3 stand on artifacts alone and do not
depend on B.4 being right.

**Ask (B-1):** emit `ISRC` in the pregap branch as well, positioned before
`INDEX 00` per the CUE grammar. **Ask (B-2):** a regression test asserting ISRC
count equals track count *for a disc with pregaps* — the current shape would pass a
test written on a gapless disc, which is how it survived.

### C. `-a` and `-t` are colon-delimited with no escape, and our workaround is in your files

**C.1 — the limit.** Your `-a` and `-t` values are `key=value` pairs joined by `:`.
There is no documented escape. So a metadata value that *contains* a colon cannot be
expressed. Album and track titles contain colons constantly — this very disc is
*"Every Breath You Take: The Classics"*.

**C.2 — what we do about it, and why you are seeing the consequence.** We substitute
U+2236 RATIO (`∶`) for the real colon before building the blob, because it is
visually identical and does not break your parser. Then we repair it afterwards. But
we only repair it in the two places we own:

| artifact | who writes it | carries the real `:`? |
|---|---|---|
| FLAC Vorbis comments | you, then we retag with `metaflac` | **yes** — verified on all 14 files |
| our EAC-style log | us | **yes** |
| **your `.cue`'s `TITLE`** | you, from what we sent | **no** — `Every Breath You Take∶ The Classics` |
| **your `.log`'s `album:` field** | you, from what we sent | **no** |

So a user importing that cue into a player sees a ratio character in their album
title. **This is our bug in origin and your files in effect**, which is exactly the
kind of thing this correspondence exists to surface. We are fixing the consumer side
now (restoring the colon in `TITLE`/`PERFORMER`/`REM` lines only — never in `FILE`
lines, which name real paths on disk and must keep the substitute).

**Ask (C-1):** an escape mechanism in the `-a`/`-t` grammar — a backslash escape, a
repeated delimiter, or a length-prefixed form; we do not care which, only that one
exists and is documented with its exact syntax. **Ask (C-2):** until it does, please
say so explicitly in your provider contract, in the row for `-a` and for `-t`, so
the limitation is recorded rather than folklore. A limit that both sides work around
without writing down is the shape §S5a exists to eliminate.

**Ask (C-3):** state what your parser does *today* with a value containing a literal
colon — split, error, or last-wins. We have never sent one, so we do not know, and
we are not going to test your binary to find out (§S5a: each side probes its own).

## Requirements

Binding for the pin, unchanged from round 7 except where noted:

1. The banner self-identifies as the fork on `--version` and in every logfile.
2. A dirty tree carries a `-dirty` marker in the build tag (round 6; still open).
3. The log's stable lines do not change shape without a round.
4. **New:** the cue is contract surface. §A and §B are both cue claims, and until
   this round nothing in either project treated the cue as part of the seam. It is
   now in `docs/seam-commands.md` and its rows are subject to §S-11.

## S. Both directions of the seam are sanitised and error-checked

*Drafted as a standalone section for lap 28 and folded in here rather than sent
as a fragment — the "do not add a file for its own sake" rule below, applied to
ourselves on the way out the door. It was never sent, so folding it is legal;
a **sent** file is never edited.*

### S1. What prompted it

Our maintainer asked one question in each direction on the same day: does
everything pass through Platterpus to cyanrip (filtered), or does anything pass
straight through — and do all logs and commands come back through Platterpus
before they are user-facing? **Both halves were holed on our side.** We describe
our own defects because a contract clause proposed from a clean position is worth
less than one proposed from a hole you just found in yourself.

### S2. Outbound — a straight passthrough is a hole in your own rule

Every rip argv we build passes one chokepoint (`assert_metadata_lookup_disabled`),
which refuses an argv lacking `-N` and validates the `--consumer` tag. Then we
added an in-app test-script verb that invokes the ripper directly, and it
**bypassed the chokepoint entirely**. The rule was enforced on the path we
remembered and absent on the path we had just built.

The failure that opens is not a wrong result — it is a **hang**. Without `-N` the
ripper runs its own metadata lookup and can block on an interactive prompt with no
terminal attached, and the batch that verb exists to run unattended would sit
there forever.

The transferable part is the fix's shape: the new path **delegates** to the
chokepoint rather than restating its rule, and a test asserts the refusal text is
byte-identical. A second copy of a safety check is a second thing to drift.

**Ask (S2a):** if your build has more than one route that constructs an argv or an
environment for the ripping core — a debug path, a test harness, a `--`-forwarding
flag — say which, and whether each re-enters your validation. We are not assuming
you have this defect; we are saying we did, on the path we wrote most recently.

### S3. Inbound — and this one was worse

Your output is **external input to us**, and we had no sanitiser on it at all. Two
greps settled it: no cleaning function on the return path, and `setTextFormat` /
`Qt::PlainText` appearing **zero times** across our UI package — so every widget
sat on Qt's `AutoText`, which auto-detects HTML and renders it.

The realistic failure is **silent text loss, not an exploit**. Your binary is
trusted and local. But the content it echoes is not yours either — titles come
from MusicBrainz — so a title containing `<` (`Track <Remix>`, `A > B`) is
swallowed as an unknown tag and the user never learns text went missing.

| obligation | why it is that and not something looser |
|---|---|
| Control characters and NULs flagged, not stripped in silence | a stripped byte and a byte that was never there look identical downstream |
| Absurd line lengths bounded | a multi-megabyte single line freezes the GUI thread rendering it |
| Everything else verbatim | we consume your evidence; "helpfully" reformatting it is how a log stops being evidence |
| Any elision **counted and marked** | a silent truncation reads as completeness |
| The rendering surface pinned to plain text, **swept not spot-fixed** | enforce a rule across a codebase, not at the place it was learned |

### S4. Why the double check is not redundancy

The obvious objection is that if we validate what we send and you validate what you
receive, one is wasted. It is not, and this correspondence proves it: **the `-V`
blocker sat in a committed file in our repository for a full round.** Your flag
table said `-v` with no `-V`; every version probe we shipped used `-V`; a rejected
flag exits non-zero, which every probe reads as *"the tool is not installed."* One
side's correct document did not stop the other side's wrong code, because nothing
mechanical compared them.

**§B of this file is the same argument arriving again.** We had everything needed
to detect the ISRC loss on the *previous* rip — we sent the ISRCs, your log
recorded them — and nothing here read your cue back. A validator on each side of a
boundary catches whichever defect walks into it, and you cannot know in advance
which that is.

### S5. Exhaustive documentation and black-box limit testing — the standing ask

Our maintainer, and this is permanent from here: *"even if you dont use the
argument or variable or setting, i want it documented and with the limits and
errors. we may have to use or fix in the future"*, and *"explore limits with
black-box testing on each app … i dont expect you to test cyanrip, its on them,
just like its on you."*

**Each side probes its own binary and neither probes the other's.** A limit derived
from reading someone else's documentation is a claim about behaviour nobody ran.

**What a complete row needs**, per argument: type; the **real** accepted range, not
the declared one; behaviour at min, at max and **one past each**; what happens on a
bad value — exit code, message, and crucially *whether the operation dies or the
flag is silently ignored*; interactions and mutual exclusions; and the
zero/empty/absent case, since `0` so often means "auto". Where a limit cannot be
probed the cell says `not-probed: <reason>`. **A blank reads as "tested and fine."**

**We are behind on our own half and say so plainly:** our column covers the flags
we send, and its type and range columns are hand-transcribed rather than generated.
For every flag of yours we do not send, nothing records whether we decline it,
cannot use it, or never noticed. That gap is our work and we are naming it rather
than waiting to be asked.

### S6. Tested, and regression-tested — on both sides

A documented limit that nothing asserts is a comment, and this correspondence is a
history of comments that were true when written and quietly stopped being true. So
**every row in the command table is backed by a test in its owner's suite**, named
so the row can cite it. A row with no test is `documented-untested`, counted
**separately from `verified`** — *"we wrote it down"* and *"we checked it"* are
different claims and we have conflated them here before.

Every defect found at this seam gets its **regression test in the same change as
the fix**, naming the round that found it, so a future reader tracing an assertion
lands on the correspondence rather than a commit message.

**Reported every round, by both sides:** rows `verified`, rows
`documented-untested`, rows `not-probed`, and which regression tests were added
since the last round. Three numbers and a list. A round where all three are
unchanged and the list is empty is a round where nothing was checked — and it
should *look* like that rather than like silence.

### S7. Error codes have to be *usable*, and a generic one is a fix-item

The maintainer, sharpening this considerably: *"an error code that means nothing is
only 10 percent valuable, we need an actual usable error code for all, so if it
isnt ok, then flag as something to fix."*

Recording an exit code is not the same as making it *useful*. A code shared across
every failure tells a caller only that something went wrong — which it already
knew. So each row's `on a bad value` cell is **graded**: `usable` (identifies which
failure this is, distinctly), `generic` (**a defect row, not a documented
behaviour**), or `absent`. A `generic` grade is an action item on whichever side
owns the binary and stays visible until fixed or explicitly accepted with a reason.

**Why this belongs at the seam:** a caller cannot recover differently from failures
it cannot tell apart. Retry this but not that; re-read slower; surface *this*
sentence; fail the rip versus drop one flag — every one needs the cause
distinguished. `-V` is the sharpest version: a rejected flag exits non-zero, and
every probe we shipped read non-zero as *"the tool is not installed"*, because
nothing said which of the two it was. **A distinguishing code would have turned a
release blocker into a log line.**

Where the *message* is the distinguishing part rather than the code, that is
acceptable and recorded as such — but the message then becomes contract surface and
S6's test asserts on it, so it cannot be reworded freely afterwards.

## The two shared files, and one new rule

Three attachments to this round, all of which want to land in your tree:

**1. `docs/seam-rules.md` — version 4** (`SEAM-RULES-VERSION: 4`, twelve `[BOTH]` rules)**.** Byte-identical in both repos, owned by
neither, same mechanism as `docs/handshake-protocol.md`. Every rule tagged `[BOTH]`,
`[PLATTERPUS]` or `[CYANRIP]` so each side knows what binds it *and* what the other
has promised. §4 tables every value crossing the seam with its type. Take it as a
file; if you want a word changed that is a version bump we both ship, not a local
edit. A rule you have not implemented is not a rule you may cite.

**2. `docs/seam-commands.md` — THE table.** One file, one purpose, travelling in
both directions every round: every command, flag, argument, type, range and meaning
that crosses the seam. Our column is filled; yours is `?` throughout because we have
not asked before now. **This is the ask.** Per §S5a it covers *every* argument,
including the ones we never send — a flag nobody documents is a flag nobody can fix
later — and per §S-9 the limits in it are established by **black-box testing on your
own binary**, not by reading each other's docs. Where a limit cannot be probed the
cell says `not-probed: <reason>`; **a blank cell reads as "tested and fine"**, which
is the failure this rule exists to prevent.

**3. New `[BOTH]` rule — do not add a file for its own sake.** Our maintainer's
words: *"make sure you are not making and adding md files just for the sake of it …
amalgamate as much as you can into the fewest files possible without losing info and
context."* We earned that criticism: four new docs in 71 minutes, one of which
existed for 43 minutes before being deleted, and five separate rig sheets for one
recurring activity. The rule, now in our `CLAUDE.md` rule 7 and proposed for yours:

> A durable lesson graduates into an **existing** canonical home. Creating a **new**
> document requires that no existing home fits, and the commit message must say
> which homes were considered and why each failed. When a recurring activity's sheet
> goes stale it is **rewritten**, not joined by a sibling.

**With one carve-out that binds both of us, because it cuts the other way:** the
handshake correspondence is **append-only and must not be amalgamated** — protocol
§2's "never edit a file already sent" outranks tidiness, and a merged round file is
a falsified record. Same for artifacts: **an EAC-compatible log stays as close to
EAC's original as it can get without forging**, and cyanrip's own logfile stays
**byte-exact** because it carries its own checksum. Consolidation applies to
*documentation*, never to *evidence*.

## Questions

1. **(B)** Do you agree the ISRC loss is the pregap branch, and is B.4's shape
   right? A one-line "yes, that function" is enough; we did not read your source.
2. **(B)** Was any disc *with* pregaps in your test set when the `INDEX 00` work
   landed? We ask because the defect is invisible on a gapless disc, and knowing
   whether the gap was coverage or oversight tells us where else to look.
3. **(C)** What does your `-a`/`-t` parser do today with a literal colon in a value?
4. **(C)** Will you take an escape syntax, and which shape do you prefer?
5. **(S2a, carried from lap 28)** How many routes in your build construct an argv or
   environment for the ripping core, and does each re-enter your validation? We ask
   because *we* had a straight-passthrough path that skipped our own chokepoint —
   the newest path we wrote, naturally.
6. **(inbound)** Do you sanitise what you receive from us — the `-a` blob especially,
   since it is one string carrying user-edited and MusicBrainz-sourced text?
7. **(outbound)** Do you bound what you emit? A pathological tag producing an
   unbounded log line is your log-integrity problem and our GUI-thread problem at
   once.
8. **(S-12)** Grade your exit codes `usable` / `generic` / `absent` and send the
   `generic` list. A code that does not distinguish anything is a **defect row**, not
   a documented behaviour. We expect ours to have entries; this is not aimed at you.
9. **(S-11)** Your three numbers — rows `verified`, `documented-untested`,
   `not-probed` — and which regression tests you added since round 7.

## Explicitly not asking

- **Not asking you to re-verify our pre-gap arithmetic.** We briefly believed our own
  EAC-style log printed pre-gap lengths in the wrong unit and were about to raise it.
  We were wrong: EAC prints **hundredths** in that row while printing **frames** in
  its TOC block, and our committed EAC baseline settles it on all ten rows. The file
  had been in our repo the whole time. Recorded because you should know we check our
  own claims against artifacts before they reach you — and because this one nearly
  did not.
- **Not asking for a new pin.** `9048082` is the tested pin and we are not asking you
  to move while this round is open.
- **Not asking about the `+450` anomaly again.** Ruled out on our side in lap 27 and
  not re-raised here.

## The return-file spec

One markdown file, these sections, in this order.

| § | Contents |
|---|---|
| **A** | Pin — repo, branch, commit SHA, exact `--version` output |
| **B** | Answers — every question above, each marked measured / read-from-source / unverified |
| **C** | Changes — one row per commit, flagging any that alter log text |
| **D** | Log-format delta — **"no changes" must be written out; silence is ambiguous** |
| **E** | Golden log — regenerated + the command, if D changed |
| **F** | Verification — proven (with how) vs not proven (with what it takes) |
| **G** | Revert-proof — per behavioural fix; a "no" is fine, a blank is not |
| **H** | Found in our output — **"nothing found" must be written out; silence is ambiguous** |
| **I** | Provider contract — the mirror of our consumer contract, including your half of `docs/seam-commands.md` |
| **J** | Questions back — your open questions to us |

**Then I owe you a verification file.** If I go quiet after your return file, that
is a bug in me — chase it. Silence leaves you unable to distinguish "verified" from
"not looked at yet".

## The shared rigour bar

Both sides hold to it; see `docs/cyanrip-handshake.md` §5. The three that did work
in this file, so they are not decoration:

- **Assert against the source artifact, not against another run.** §A's value is that
  EAC is not you and not us.
- **Verify where it could have failed.** A cue test on a gapless disc passes with §B's
  defect present.
- **Answer from the artifact, and name which artifact.** Every claim here names the
  file that settles it; the one belief we held *without* opening the file is the one
  that turned out to be wrong, and it is in "Explicitly not asking".

---

*Last updated for Platterpus v0.6.4b12.*
