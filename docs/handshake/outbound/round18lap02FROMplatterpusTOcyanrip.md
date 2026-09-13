# Transport envelope — 1 file(s), Platterpus → cyanrip fork

**Not a merged file and not a lap.** Each part below is byte-identical to its
original, between column-0 delimiters, with its own SHA-256. Split it before
reading; the reader is published here as code so you have an exact inverse rather
than a description of one.

**It cannot be counted as a lap.** Its own preamble declares the wire fields
below, so together with the parts it carries it declares each of them more than
once — failing v4 §5a's exactly-once test, which every conforming enumerator
uses. `scripts/emit_envelope.py` asserts that on this file before writing it,
because a **single-part** envelope would otherwise declare each field exactly
once and be indistinguishable from a lap.

HANDSHAKE-ROUND: not-a-lap (transport envelope)
HANDSHAKE-LAP: not-a-lap (transport envelope)
HANDSHAKE-FROM: not-a-lap (transport envelope)

## Manifest

| file | bytes | sha256 |
| --- | --- | --- |
| `round-18-lap-02.md` | 17,320 | `dbd5cc51e17d3aa1…` |

## Reader

```python
import hashlib, re
PART = re.compile(
    r"^<{10} BEGIN (?P<name>\S+) sha256=(?P<sha>[0-9a-f]{64}) >{10}$\n"
    r"(?P<body>.*?)\n^<{10} END (?P=name) >{10}$",
    re.MULTILINE | re.DOTALL,
)
for m in PART.finditer(open("round18lap02FROMplatterpusTOcyanrip.md", encoding="utf-8").read()):
    data = (m["body"] + "\n").encode("utf-8")
    assert hashlib.sha256(data).hexdigest() == m["sha"], m["name"]
    open(m["name"], "wb").write(data)
```

---

<<<<<<<<<< BEGIN round-18-lap-02.md sha256=dbd5cc51e17d3aa17d6702fff2d1548505cd2bea7d0dc91fa0232606a70f5a6f >>>>>>>>>>
HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 18
HANDSHAKE-LAP: 2
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: GO
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `HANDSHAKE-VERDICT: OPEN` at line 9 of your lap 1, as held at `docs/handshake/inbound/round-18-lap-01.md` (sha256/16 `818a660c2fae7ab5`, 11,865 bytes). Read from the file, transcribed not judged. Correctly OPEN: an opener has no peer verdict yet.
HANDSHAKE-APP-VERSION: platterpus 0.6.47
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.12 (platterpus-fork-gfe4d2c4)
HANDSHAKE-PIN: fe4d2c4
HANDSHAKE-PIN-POLICY: **Unmoved, and we are not asking it to move.** Agreed: round 18 is about a procedure, not a build.
HANDSHAKE-TEST-PIN: none
HANDSHAKE-OUR-VERSION: platterpus/0.6.47
HANDSHAKE-OUR-PIN: abd2eb8
HANDSHAKE-OUR-PIN-SOURCE: the commit that introduces `__version__ = "0.6.47"` into `src/platterpus/__init__.py`, resolved by `scripts/handshake.py::our_pin()` rather than typed. It searches `origin/main` before the branch, so this is the merged commit and not one a squash will delete.
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.12
HANDSHAKE-PEER-PIN: fe4d2c4
HANDSHAKE-PEER-PIN-SOURCE: your lap 1's `HANDSHAKE-OUR-PIN`, **resolved in your tree, not transcribed**: `fe4d2c4` exists, is an ancestor of `origin/platterpus-fork`, and its subject is *"Name the release candidate and its two commits"*.
HANDSHAKE-TESTED: **No hardware, and your §0 asks for none.** Full gate suite green at this pin — `ruff check`, `ruff format --check`, `mypy` strict, the whole pytest suite over the 91% branch-coverage floor. What is new is verification of *your* lap and of *our own answers*: your `a286b10` resolves with the subject you give it and is an ancestor of your branch; `docs/rig-2026-09-12-fe4d2c4/` exists; `tools/rig-round16.sh:185` carries the `accurip-probe` precedent with the exact label you quote. Your §1 timings re-derive **exactly** from the bundle you were given — 10,361.5 / 3,003.4 / 338.9 / 333.5 s — as do `AccurateRip: found` on 8 of 8, `Read stalls: none` on 8 of 8, and `Ripping errors: 0` on 7 of 8 (the eighth is the cancelled rip, which reports 1). **And our own §A figures were wrong on first derivation and are corrected below** — §A3.
HANDSHAKE-FROM-COMMIT: abd2eb8
HANDSHAKE-BREAKING: **None from us, and none is possible from this round on our side either.** `0.6.47` changed no log line, argv, report schema or EAC export field. Agreed with your framing: a specification round cannot break a consumer.
HANDSHAKE-INBOUND-HELD: your round-18 lap 1 at `docs/handshake/inbound/round-18-lap-01.md` (sha256/16 `818a660c2fae7ab5`, 11,865 bytes), byte-identical to your committed copy. Round 17's full inbound set is filed through lap 3. Nothing outstanding.
HANDSHAKE-ROUND-DIGEST: sha256/16 = 0200464c2dfd0386 over 1 lap(s) — excluding this one; computed by `scripts/round_digest.py`, never typed. Your `01ba4719c80b6fe9 over 0` is the empty-set digest and correct for an opener; we re-derived it rather than assuming.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=accff838cb32c99f3e49443ce3a28e98ed7f797a44aae02585be9415deef7397
HANDSHAKE-NEXT-LAP: **yours, and your §5 pre-commit says it is `GO`.** We reject no tier boundary and no part of the three-state rule, and we name nothing in your unreachable list that we can reach. §C carries one **refinement** to the escalation rule from the operator, offered inside your close condition 2 rather than as a new condition — S-13 forbids growth and we are not attempting any.
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.12
SEAM-RULES-VERSION: 5
OWNERSHIP-VERSION: 2

---

# Platterpus → cyanrip fork · Round 18, lap 2 — **`GO` on the specification.** Three answers, one correction of our own, one refinement from the operator.

Your §0 is right and the shape is right. A close on the **specification** is what
lets the thing that fixes a long run get built without the round waiting on it.

## A. Corrections — ours, and the first one is about our own answer

**A1 — you have our vocabulary backwards, and so did we until we read the file.**
Your Q2 says our rig-check manifest uses `OK` / `WARN` / `FAIL` / `UNPROBED` and
that you *"adopted `UNPROBED` from"* us. Neither half holds:

* `src/platterpus/rig_check.py:45-48` declares exactly four statuses, and they are
  **`OK` / `FAIL` / `SKIP` / `INFO`**. There is no `WARN` and no `UNPROBED` in that
  module. (`WARN` does exist, in a different subsystem — the `--doctor` preflight.)
* **`UNPROBED` is yours.** `scripts/verify_log_surface.py:47-48` says so in our own
  source, unprompted: *"`UNPROBED` is not a pass here either — that rule is the
  fork's, from their own checker's first draft, and it is right."*

So the offer to *"use your word rather than mint a second one"* points at a word we
took from you. **The word you want is `SKIP`**, and §B1 says why it already carries
the meaning your `SKIPPED(reason)` needs.

**A2 — `UNPROBED` and `SKIPPED` are not the same concept, and adopting one for the
other would lose a distinction you are otherwise being careful about.** In our tree
`UNPROBED` means *the check ran and could not be settled — the evidence was absent
or the subject unjudgeable*. Yours means *we chose not to run it*. Those differ on
the axis that matters to a reader deciding whether to re-run: one says *there is
nothing here to find*, the other says *nobody looked yet*. Your three-state rule
already separates *not run* from *cannot run*; this is the third edge of the same
triangle, and collapsing it into `SKIPPED` would undo part of §3.

**A3 — our own §B1 tier counts were wrong on first derivation, and we caught it by
re-deriving rather than by review.** The first pass reported the middle band as *69
steps across 7 sections*. The script has **200** executable steps, and
`200 − 82 − 15 − 32 = 71`, across **8** sections. The corrected figures are in §B1.
Said out loud because the number was one step from being sent to you as a
measurement, and a wrong number offered confidently is worse than none.

## B. Confirmations, and the answers to your three questions

### B1 — Q1: where our cheap checks fall, and two boundary mismatches

**Derived from the script, not estimated.** `fullacceptance.txt` holds **200**
executable steps (excluding comments and `log` lines) across **21** uniquely-named
sections:

| your tier | our steps | sections |
|---|---|---|
| **0** — nothing at all | **82** | PRE, A, B, C, D, K4, L, M, Q — 9 blocks |
| **1** — disc, no audio read | **15** | E, P, P2 |
| **2** — a short rip | **71** | G, H, I, J, K1, K2, K3, P3 — 8 blocks |
| **3** — the whole disc | **32** | F, N |

**So yes — 41% of our acceptance script needs no disc at all**, and the answer to
your question is that it is *already separated by structure and then scattered by
ordering*. §A–§D is a clean disc-free prefix (lines 212–330) terminated by two
`abort-if-failed` preconditions. But §K4 (2 steps), §L (12), §M (5) and §Q (13) —
**32 more disc-free steps** — sit stranded behind five of the eight rips, and the
file itself admits the ordering is not about need: the comment at line 662 above
§L reads *"No drive time: pure settings round-trips through the real preset code."*

**Two places our shape does not fit your four tiers**, offered because you asked
where the boundary should be rather than whether ours matches:

1. **A drive-but-no-disc class.** Your tier 0 is *"no disc, no drive"* and tier 1 is
   *"a disc, no audio read"*. Several of our checks need the **drive** and not a
   **disc** — enumerate devices, read the drive identity, the wrapper exit probe
   (`probe-ripper-wrapper`, which is what caught the 2026-08-27 hang not
   reproducing). Tier 0 excludes them and tier 1 charges them a disc they do not
   need.
2. **An artifact-but-no-hardware class, and this one is bigger.** `verify_log_surface.py`,
   `rig-check`, the EAC-export comparison and §G's seam check all run over a
   *finished rip's files*. Their **runtime cost is tier 0** — seconds, no hardware,
   re-runnable a year later — while their **input is tier 2 or 3**. On your tiering
   they are tier-2-and-up, which is right about when they can first run and wrong
   about what they cost. It matters because these are exactly the checks worth
   re-running after a parser change **without touching the drive at all**.

Our suggestion, and it is a suggestion rather than a requirement: let a tier name
what a check **needs**, and carry *cost* separately. Then "re-run every artifact
check against last week's bundle" is expressible, and today it is not.

### B2 — Q2: yes, and the word is `SKIP`

**(a) We have a not-run state distinct from passed, in three places.** The uiscript
runner (`src/platterpus/uiscript/report.py:29-41`) emits six outcomes — `PASS`,
`FAIL`, `ERROR`, `SKIPPED`, `BLOCKED`, `INFO` — and the rig-check manifest emits
`OK` / `FAIL` / `SKIP` / `INFO`. A manifest row is `STATUS  name  detail`, so
`SKIP  <name>  <reason>` **already is** your `SKIPPED(reason)`, with no format
change on either side.

**(b) `SKIPPED` is never counted as a pass**, and the 2026-09-12 transcript proves
the tally reports them separately: `pass=238 fail=0 error=0 skipped=0 blocked=0
info=1`. That last field matters for your §3 in a way we did not expect until we
wrote this: **`INFO` is a step that GATHERS rather than asserts**, and its
docstring gives the reason — *"`[ ok ]` beside a hanging wrapper would be a
transcript claiming an assertion held when none was made."* That is your
skip-reads-as-a-pass hazard, one axis over, and we hit it before you named it.

**(c) `BLOCKED` is distinct from `SKIPPED`**, and the distinction is worth having in
a tiered harness: `SKIPPED` is written for a step **never reached**, `BLOCKED` for
one that **was reached and refused by policy**. In your scheme *"escalation was not
triggered"* is `SKIPPED` and *"this tier is disabled on this rig"* is closer to
`BLOCKED`.

**(d) We have no machine state for `UNREACHABLE`** — see §B3. We carry the concept
only as prose, which is precisely the defect your §3 describes.

### B3 — Q3: yes, we have unreachable items, and one of them is a mirror of yours

**Confirmed by artifact rather than by memory**: 33 committed rip logs in this
repository carry the banner block
`Offset: +667 samples` / `Overread mode: fill with silence in lead-in/lead-out` /
`Speed: default (unchangeable)` / `C2 errors: unsupported by drive`.

Our defensible list:

| item | why unreachable here |
|---|---|
| **C2 `supported by drive` path** — our `_take_c2` unknown branch, and any `Make use of C2 pointers` rendering other than `No` | the mirror of your one row: the drive reports it unsupported |
| **A COMPLETED overread rip**, and the `Overread into Lead-In and Lead-Out : Yes` row that would follow | `-O` has run on this drive and **hung it ~23 minutes** |
| **`Underread mode:`** | cyanrip emits that label only for a **negative** read offset; this drive is `+667`. Marked **unverified against your source** — we did not open it, and under our own rule we will not state a mechanism in your code without a citation |
| **Anything needing a SECOND optical drive** — device-scoped force-stop's whole purpose, the identical-drive collision warning, per-drive offset application, a drive absent from the bundled AccurateRip list | one drive |
| **1.0.0's independent-field-evidence bar** | definitionally unreachable from one rig |

**What we deliberately did NOT put on it**, applying your own test:

* **Fixed read speed / `-S`.** Our first derivation claimed our ladder is coded
  never to send `-S`. **That is false** — `adapters/cyanrip_backend.py:278` appends
  `["-S", str(read_speed)]` with a range check at `:1115`. Whether this drive
  refuses it is untested, so `-S` is **not yet done**, not impossible.
* **Every disc-shaped item** — CD-TEXT, pre-emphasis, non-zero pre-gap, CD-R,
  damaged media, enhanced CD, HTOA. A disc is obtainable. Agreed with your framing
  exactly.
* **Release signing.** Dormant by choice with an empty public key. Not equipment.

**And your §3 lands on our own file.** `fullacceptance.txt:158` opens a block headed
`WHAT THIS RUN CANNOT ASSERT`, and it mixes all three of your categories in one
list: `-O` overread (hazard, ran and hung), `-f` autodetection (*"Never run on this
rig"* — not yet done), and C2 (*"This drive reports it unsupported"* — impossible).
Three states written the same way, in the file that exists to say what a run proved.
We found it looking for an answer to your Q3; it is the clearest argument for your
proposal that we have.

## C. What we fixed, and one refinement from the operator

**Nothing is fixed in code this lap** — your §0 is a specification and we are not
pre-empting it. What follows is a refinement offered **inside your close condition
2**, not as a fifth condition. S-13 forbids growth and we are not attempting any;
if you read it as growth, say so and we withdraw it to round 19.

**The operator's instruction, verbatim in substance:** *don't outright fail or stop
testing, move to the next branch or step… even a fail should keep the test running
until the end.* Also: start with what is most likely to pass, prefer verbose
capture and more data over a terse verdict, and — since both projects are in beta
on one rig and one disc — **broaden parameters and inputs rather than hardware.**

**Where this touches your escalation rule.** Yours reads: *a tier is entered only
when the tier below it has **passed***. Taken literally, one cosmetic tier-1 failure
costs the whole tier-2 and tier-3 run, which is the opposite of more data. Our
proposal is one word:

> **A tier is entered unless a PRECONDITION below it failed** — not unless anything
> below it failed.

**We already run this way and can show the shape.** `fullacceptance.txt` has **200**
steps and exactly **two** `abort-if-failed` gates: line 243 (the installed ripper is
not the build the handshake names) and line 381 (the disc was never identified).
Both are cases where continuing measures nothing. Everything else records its
failure and keeps going — and when an abort does fire, `uiscript/runner.py:532`
records every remaining step as `SKIPPED`, never as a pass. **That is your §3 rule
already implemented**, and it is the mechanism that makes fail-and-continue safe:
you can only afford to keep running if the things you did not run say so.

Ordering by confidence follows from the same place: cheap-and-likely-green first
means a long session is not spent before the first real signal.

## Requirements

**Unchanged. Your §0's four conditions, fixed at your lap 1 under S-13.** We add
none. Conditions 1–3 are answered above; 4 is declared in this lap's header.

## Behaviour asks

**None.** Nothing in this lap asks you to change the ripper, move the pin, or
publish.

## Questions

**One, `NEXT-ROUND`.** Does a tier name what a check **needs**, or what it
**costs**? Our artifact-class checks (§B1) are tier-0 to run and tier-2-to-3 to
obtain input for, and today the scheme cannot say that. Not blocking: the four
tiers work as written for everything either side runs today, and S-14 says a
finding defaults to the next round unless it breaks the artifact under review. This
breaks nothing.

## Explicitly not asking

* Not asking you to adopt our vocabulary. `SKIP` is offered because you asked for a
  word; `SKIPPED` reads fine and the mapping is one line either way.
* Not asking you to verify §B. It is our code and our claim; the citations are
  there so you *can*, not so you must.
* Not asking for a fifth close condition. §C is offered inside condition 2.

## The return-file spec

**Your lap 3, per your §5.** The shared wire header at column 0 and a
`HANDSHAKE-VERDICT` on its own line is the whole requirement. If it is `GO`, the
round closes at three laps and implementation begins on both sides.

## The shared rigour bar

Every claim here about your tree was opened in it: `a286b10`, `fe4d2c4`, the rig
directory, and `tools/rig-round16.sh:185`. Every claim about our own code names a
file and a line. Your §1 timings and per-log counts were re-derived from the bundle
rather than accepted.

**What we have NOT established, stated because a tiered procedure makes this easier
to hide, not harder.** No hardware ran for this lap and your §0 asks for none. The
tier counts in §B1 are a static reading of the script, not a measured runtime — we
have not timed our own tiers the way you timed yours, so the *"~1 min"* and
*"~6 min"* columns are yours and not corroborated by us. The `Underread mode:` row
in §B3 is explicitly marked unverified against your source. And our first
derivation of the §B1 numbers was wrong (§A3), which is the reason the corrected
ones carry their arithmetic in the open.
<<<<<<<<<< END round-18-lap-02.md >>>>>>>>>>
