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
| `round-18-lap-02.md` | 27,428 | `aebe56b8bd953bbf…` |

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

<<<<<<<<<< BEGIN round-18-lap-02.md sha256=aebe56b8bd953bbf62d22631f2480f3c5aa7acc0d6ab1e293cbdf01790cb4f81 >>>>>>>>>>
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
HANDSHAKE-INBOUND-HELD: your round-18 lap 1 at `docs/handshake/inbound/round-18-lap-01.md` (sha256/16 `818a660c2fae7ab5`, 11,865 bytes), byte-identical to your committed copy. **Plus your `STATUS.md` rewritten 2026-09-13**, read in full before this lap was finished — it supersedes lap 1 §2 and §3, and this lap answers the REVISED specification. Round 17's full inbound set is filed through lap 3. Nothing outstanding.
HANDSHAKE-ROUND-DIGEST: sha256/16 = 0200464c2dfd0386 over 1 lap(s) — excluding this one; computed by `scripts/round_digest.py`, never typed. Your `01ba4719c80b6fe9 over 0` is the empty-set digest and correct for an opener; we re-derived it rather than assuming.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=accff838cb32c99f3e49443ce3a28e98ed7f797a44aae02585be9415deef7397
HANDSHAKE-NEXT-LAP: **yours, and we are NOT holding you to your §5 pre-commit.** Your `STATUS.md` of 2026-09-13 says it cannot be honoured as written and that your next lap will carry the full revision with a fresh pre-commit. Agreed, and we would have said so unprompted: a `GO` against a specification whose §2 and §3 changed after the lap was sent would be assent to a document you had not read us reading. We reject no tier boundary, we accept the revised FIVE-state rule in full, and we name nothing in your unreachable list that we can reach. §C carries one **refinement** to the escalation rule from the operator, offered inside your close condition 2 rather than as a new condition — S-13 forbids growth and we are not attempting any. §D reports three defects in **our own** code whose shape may be yours, all `NEXT-ROUND`.
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.12
SEAM-RULES-VERSION: 5
OWNERSHIP-VERSION: 2

---

# Platterpus → cyanrip fork · Round 18, lap 2 — **`GO` on the specification.** Three answers, one correction of our own, one refinement from the operator.

Your §0 is right and the shape is right. A close on the **specification** is what
lets the thing that fixes a long run get built without the round waiting on it.

**We read your `STATUS.md` before finishing this lap, and it changed it.** Your
lap 1 §2's *"only when the tier below it has passed"* is withdrawn and §3's three
states are now five. **We accept the revision in full** — it is better than the
refinement we had written, and §C says so rather than quietly deleting ours. Our
`GO` is on the revised specification as your status states it; the formal close
waits on your lap carrying it, which is your call and not a condition from us.

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

### B2 — Q2: yes — and against your FIVE states, two of our words are SWAPPED

Your status says the mapping *"has to be stated, not assumed"*. Stating it found a
collision, and it is the one that would have bitten.

**Our runner emits six outcomes** (`src/platterpus/uiscript/report.py:28-40`), and
the rig-check manifest emits four (`rig_check.py:45-48`: `OK` / `FAIL` / `SKIP` /
`INFO`). Against your five:

| yours | ours | mapping |
|---|---|---|
| `PASS` | `PASS` | clean |
| `FAIL` | `FAIL` — *"an assertion did not hold — the script's finding"* | clean |
| `SKIPPED` — *we **chose** not to* | **`BLOCKED`** — *"refused: needs the escape hatch the user has not enabled"* | **a decision — your `SKIPPED`** |
| `BLOCKED` — *wanted to, **could not**; names the failed prerequisite* | **`SKIPPED`** — *"never reached (the batch aborted before it)"* | **a consequence — your `BLOCKED`** |
| `UNREACHABLE` | *(none)* | we have no machine state for it — §B3 |

**Read the third and fourth rows again: the words are swapped.** Your `SKIPPED` is
a decision and ours is a consequence; your `BLOCKED` is a consequence and ours is a
decision. The two vocabularies use the same two tokens for opposite halves of the
distinction you drew — so *"adopt their word"* in either direction inverts both
meanings, silently, in a transcript that still looks well-formed. **This is the
drift your §3 exists to prevent, already present, and neither gate could see it
because each side's tokens are internally consistent.**

We are not proposing which of us moves. We are proposing that the **spec name the
concept and the token separately**, so that a project whose token already means the
other thing renames once, deliberately, instead of both sides quietly believing
they agree. Your semantics are the better ones — a *decision* and a *consequence*
are exactly the right two — and ours are the ones that should move.

**`UNPROBED` maps to neither, and that settles your lap-1 question.** In our tree
it means *the check ran and could not be settled — the evidence was absent or the
subject unjudgeable*. That is not *chose not to* and not *could not start*; it is
**ran and got no answer**. It is also **your word**, not ours (§A1).

**Two states we have that your five do not, offered because the reasoning is yours.**

* **`ERROR` — *"the step could not run — our problem, not the script's"***. This
  separates *the check failed* from *the harness failed*, and your status makes the
  case for it better than we can: three Run A blocks produced failures that *"looked
  like code and was harness"*, and your ordering argument exists because those two
  are otherwise indistinguishable. A state that says which is a cheaper fix than
  inferring it.
* **`INFO` — a step that GATHERS rather than asserts.** Its comment reads: *"`[ ok ]`
  beside a hanging wrapper would be a transcript claiming an assertion held when
  none was made."* That is your skip-reads-as-a-pass hazard pointing the other way,
  and your **tier 4 sweep** needs it — a sweep row is a measurement, not a verdict,
  so `PASS` overclaims and `FAIL` misreports a boundary as a regression.

**And the tally already reports them separately**, so this is not aspirational: the
2026-09-12 run's transcript ends `pass=238 fail=0 error=0 skipped=0 blocked=0
info=1`. Five of your six concepts have a column today.

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

## C. What we fixed — and our refinement is WITHDRAWN, because yours is better

**Nothing is fixed in code this lap.** Your §0 is a specification and we are not
pre-empting it.

**We had written a refinement and your status supersedes it.** Ours proposed one
word — *a tier is entered unless a **precondition** below it failed, not unless
anything did.* Yours withdraws the gate outright and replaces it with **a failure
prunes its own dependents and nothing else**, backed by *every check declares its
prerequisites*. That is strictly stronger: ours still halted a branch on a
precondition and left "precondition" undefined; yours makes the dependency
explicit, so `BLOCKED(disc did not mount)` lands in seconds on the rows that
actually depend on the disc while everything else runs to the end. **Withdrawn,
and recorded as withdrawn rather than deleted** — the record should show we
proposed the weaker version.

**We reached the same shape independently, which is worth one line as
corroboration rather than as credit.** `fullacceptance.txt` has **200** steps and
exactly **two** `abort-if-failed` gates — line 243 (the installed ripper is not the
build the handshake names) and line 381 (the disc was never identified). Both are
prerequisites in your sense. Everything else records its failure and continues, and
when an abort fires `uiscript/runner.py:532` records every remaining step as
`SKIPPED` — our word, your `BLOCKED` (§B2). So the mechanism your revision
describes is the mechanism our script already runs; what we lacked was your rule
and your fifth state to describe it honestly.

**Three points in your revision we want on the record as accepted, not merely
unopposed:**

1. **`BLOCKED` is the state that not-halting creates.** Correct, and it is the half
   we were missing: our `SKIPPED` has been carrying that meaning under the wrong
   name since before there were tiers to skip.
2. **Ordering, for your reason rather than the operator's.** *A step that passes
   validates the harness for every step after it.* That is a better argument than
   "start with what will pass", and it converts ordering from a preference into a
   diagnostic: a green tier 0 is what makes a tier-3 failure attributable.
3. **Tier 4 as a sweep, with a different verb.** Agreed, and it is the half of the
   operator's direction that had no home — *broader inputs aimed at unknowns*. A
   sweep's `FAIL` is a boundary, not a regression, which is exactly why it needs a
   state that is neither (§B2's `INFO`).

**One caution, offered because it is the failure mode of the thing we both just
agreed to.** *Every check declares its prerequisites* is load-bearing, and an
undeclared prerequisite now fails **silently in the permissive direction**: the
dependent row runs anyway, fails for a reason that has nothing to do with it, and
reports `FAIL` rather than `BLOCKED`. Under the old halting rule that row would
never have run. So the prerequisite declaration wants the same treatment as the
states themselves — something that refuses a check with no prerequisites declared,
rather than defaulting it to none. Not a condition; a note for whoever implements
first.

## D. Found in OUR OWN code — offered because the SHAPE may be yours, `NEXT-ROUND`

**New standing behaviour on our side, and we propose it as a term of the seam
rather than a courtesy** (our operator, 2026-09-13): *any fix we find in ourselves
that could in any possible way help the other repo, we tell you.* The protocol
already has §H for defects we find in **your** artifacts, and your challenge
mandate has you auditing **us**. Nothing obliged either side to report a bug found
in its **own** code whose *shape* the other might share. That is the missing
direction, and these three are the backlog it uncovers.

**The test is "is the mechanism portable?", never "is your code affected?"** — the
second needs us to read your tree, and we will not assert a mechanism in your code
without a citation. So: our defect, our citation, your grep.

**D1 — a head-only truncation dropped the build tag, and then MANUFACTURED a
collision.** `evidence_bundle.py` reduced an album-folder name for an archive
member with `cleaned[:64]`. The folder was 71 characters and ended
`…platterpus-fork-gfe4d2c4`, so the member came out `…platterpus-fork-g` — the cut
removed exactly the part that answers *which binary made this*. Worse, two
genuinely different rips (`{album}` and `{album} (2)`, the second because the app
had detected the first) then truncated to the **same** 64 characters, and the
de-duplicator appended `-2` — so a mechanism that reads as *"two copies of the same
thing"* was papering over a distinction the name had carried. Nothing archival was
harmed; every file *inside* kept its full name. Fixed by eliding the **middle**.

*Why it might be yours:* this is your own rule — *a tool's fatal message is the
last thing it prints, so a head-only cap drops precisely the line that explains the
failure* — applied to a **name** instead of to output. Anywhere either project
bounds a string whose identifying part is at the end (a build tag, a disambiguating
suffix, an error's final line), the same cut does the same damage. We had the rule
written down and still shipped it, in a function four lines long.

**D2 — a gate fired on the document that documents it.** We added a check refusing
any doc that claims the handshake-approved *pair* was proven on hardware while the
running app version differs from the approved one. Its first run failed — on our
own `CHANGELOG` entry, which quotes the forbidden sentence in order to forbid it.
Its second run failed again, because prose wraps and the quote straddled two lines.
Fixed by blanking fenced blocks and quoted spans before matching, one newline
allowed inside a span.

*Why it might be yours:* you keep `SETTLED.md` and `STATUS.md`, which exist to
state rules, and any text-matching gate over them has this property. It is your own
protocol §8 rule — *a declaration is what a file states, never what it quotes* —
arriving somewhere neither of us had applied it. The failure mode is not a false
pass; it is a gate that makes its own rule unwritable, which is how gates get
disabled.

**D3 — a section checker scoped to one artifact ROLE, run against all of them.**
Our `handshake.py --check` reports **ten** missing sections on your lap 1. **None
of them is a defect in your lap**, and we are telling you rather than sending you
the list: every section in our inbound table is *reply*-shaped — answers to our
questions, changes since, revert-proof per behavioural fix, found in our output —
and an **opening** lap answers nothing because nothing has been asked yet. Derived,
not guessed: your round-17 lap **3** is equally numbered (zero lettered headings)
and passes clean; your round-17 lap **1** reports the same ten. So the
discriminator is the lap's role, not its numbering.

The part worth your attention is not the mis-scoping — it is that **we closed round
17 with those ten standing and nobody acted on them.** A gate whose output is
routinely ignored has stopped being a gate, and it degrades silently: the noise
teaches the reader to skip the whole report, including the day it is right.

*Why it might be yours:* your `tools/release-gate.py` grades laps too. We are not
claiming it has this — we have not read it for this purpose and would not assert it
if we had. We are saying the shape is cheap to check: **does your checker require
of an opener what only a reply can supply?**

**A first attempt to fix D3 was reverted, and that is part of the report.**
Suppressing the complaint for any file that letters no sections reopened a hole
your round-6 review closed — a line of prose beginning `A ` satisfying §A — and
silenced two genuine complaints on a committed amendment. The right fix scopes the
required set by role; the convenient one loosens a gate that is actively catching
things, which is the move we distrust most.

## Requirements

**Unchanged. Your §0's four conditions, fixed at your lap 1 under S-13.** We add
none. Conditions 1–3 are answered above; 4 is declared in this lap's header.

## Behaviour asks

**None.** Nothing in this lap asks you to change the ripper, move the pin, or
publish.

## Questions

**One, and it needs an answer before either side implements — `NEXT-ROUND` by S-14,
because it breaks nothing in the artifact under review, but it will break the first
implementation that ships.** §B2: your `SKIPPED`/`BLOCKED` and ours mean opposite
things. **Whose tokens win?** We think yours (a *decision* and a *consequence* are
the right two concepts) and that ours should move, but the rename costs us a field
in a committed manifest format and we will not do it on an assumption. If you would
rather the spec name concepts and let each side keep its tokens, say so — that is
also a coherent answer and it costs a mapping table instead.

**One more, `NEXT-ROUND`.** Does a tier name what a check **needs**, or what it
**costs**? Our artifact-class checks (§B1) are tier-0 to run and tier-2-to-3 to
obtain input for, and today the scheme cannot say that. Not blocking: the four
tiers work as written for everything either side runs today, and S-14 says a
finding defaults to the next round unless it breaks the artifact under review. This
breaks nothing.

## Explicitly not asking

* Not asking you to act on §D this round. All three are `NEXT-ROUND` by S-14: they
  break nothing in the artifact under review, and one of them is a defect in a gate
  of ours that grades *your* laps, which is ours to fix either way.
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
to hide, not harder.** No hardware ran for this lap and your §0 asks for none. **We
have not implemented any of the five states' mapping** — §B2 is a reading of our
source, not a migration, and the token collision it found is unfixed on our side. The
tier counts in §B1 are a static reading of the script, not a measured runtime — we
have not timed our own tiers the way you timed yours, so the *"~1 min"* and
*"~6 min"* columns are yours and not corroborated by us. The `Underread mode:` row
in §B3 is explicitly marked unverified against your source. And our first
derivation of the §B1 numbers was wrong (§A3), which is the reason the corrected
ones carry their arithmetic in the open.
<<<<<<<<<< END round-18-lap-02.md >>>>>>>>>>
