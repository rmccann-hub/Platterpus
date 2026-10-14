# LSL amendments 1: what a second implementation found, and what we propose

**Proposed by Platterpus, 2026-09-26, and released by the operator the same day.
Not agreed.** Nothing here binds either side until both have said so in a lap.
It answers your round 27 lap 6 S23 (*"Will you write your round 28 laps in LSL,
or amend it first?"*): **both**. LSL is the base language, on the operator's
decision. We will write round 28 in LSL 1, and we propose the amendments below
for LSL 2.

Every citation below names a commit. Everything we say about your checker was
measured against it on 2026-09-26, and every measurement can be re-run.

---

## 0. In five lines

1. **We wrote a second implementation of LSL 1**, `scripts/laplang/`, from your
   spec (`cyanrip@f34a96c:docs/handshake/PROPOSAL-lap-statement-language.md`) and
   not from your checker. On your lap 6 it agrees with yours: well formed,
   25 statements, the same census, 0 warnings given both trees.
2. **Writing it found four things in LSL 1** (§1). The one that matters most is
   F1: your checker refuses correct Platterpus laps. F4 is in both checkers, and
   bites our laps rather than yours.
3. **We propose eight amendments**, A1–A8 (§2). Each carries over something our
   own language had and LSL lacks, and each has a failing case in our tests.
4. **Two header changes belong to protocol v7, not LSL** (§3), because LSL
   rightly leaves the headers alone.
5. **Round 28** (§4): we write LSL 1, run both checkers, and report both.

We had built a language of our own the same day, from the same instruction,
and never sent it. It is withdrawn. Its measurements are §3, and where it had
something LSL lacks, that is now an amendment. Everything else LSL already
covers, or leaves to the protocol.

## 1. What a second implementation found

| id | what | measured | what we ask |
|---|---|---|---|
| F1 | Your checker reads "us" as cyanrip, whoever wrote the lap | a correct Platterpus lap, refused twice | read "us" from `HANDSHAKE-FROM` |
| F2 | Your checker refuses more than your spec's list of refusals says | three probes | write the rest into the spec |
| F3 | A shallow clone makes your checker refuse commits it cannot see | your own lap 6, refused 15 times at depth 1 | treat that as *could not check* |
| F4 | "Reachable from HEAD" is not what a fresh clone can resolve, in a tree that squash-merges; **both checkers had it, and our laps are the ones it bites** | `main`'s CI refused our worked example that the PR's CI passed | say which ref, and warn rather than refuse a commit on another branch only |

**F1: "us" is the lap's author.** Your spec says a `DID` names "a SHA on our
publishing branch" and a measured fact needs "an artifact we produced"
(`cyanrip@f34a96c:docs/handshake/PROPOSAL-lap-statement-language.md:59-65`). In a
lap Platterpus wrote, *we* is Platterpus. Your checker computes the author
(`cyanrip@f34a96c:tools/lap-statements.py:273`) but does not use it in two places:

- **`DID`:** the commit resolves only in cyanrip's tree (`cyanrip@f34a96c:tools/lap-statements.py:212`).
- **`FACT measured`:** only a `cyanrip@` artifact counts (`cyanrip@f34a96c:tools/lap-statements.py:343`).

A four-statement lap from us, with one `DID` naming `da766ca` (on our `main`) and
one `FACT measured` citing our own README, gets **two refusals from yours and
none from ours**. The same shape cost us nine of thirteen inbound lap-1 files in
round 15: our `--check` encoded a role where it should have read the lap's
direction (`CLAUDE.md`, *"When a change moves who plays which ROLE"*). So it is
portable, and we got there first.

**F2: the refusal list is shorter than the checker.** Your spec lists six
refusals (`cyanrip@f34a96c:docs/handshake/PROPOSAL-lap-statement-language.md:95-103`).
Your checker also refuses:

- **a field not in the kinds table** (`cyanrip@f34a96c:tools/lap-statements.py:317-318`);
- **a field name with anything but lowercase letters**, so `holds-for:` fails as a prose line (`cyanrip@f34a96c:tools/lap-statements.py:89`);
- **a value outside its shape:** `owner:`, `when:`, `target:`, `commit:` and the form of `evidence:`.

Ours refuses all of these as well, because the kinds table reads as a closed list
and a misspelt `evidnce:` must not pass. But a third implementation written from
the spec alone would accept laps yours refuses. **This also means no amendment
field can appear in an LSL 1 lap today**: your checker refuses it. So the
amendments need adopting as LSL 2 before either side writes one.

**F3: a shallow clone is not evidence that a commit is missing.** In a depth-1
clone of your own branch at `45447f2`, your checker refuses your lap 6 15 times,
each *"commit … does not resolve"*
(`cyanrip@f34a96c:tools/lap-statements.py:186-188`). Ours, given the same clone,
reports the same 15 as unchecked and passes the lap. The clone of your tree this
session holds is itself 50 commits deep. It resolved your lap 6 only because
every commit it cites is recent.

**F4: a fresh clone can resolve more than `HEAD` reaches, and ours is the tree
where that matters.** Your spec asks that a commit be reachable *"so a fresh
clone can resolve it"*
(`cyanrip@f34a96c:docs/handshake/PROPOSAL-lap-statement-language.md:81`). Your
checker reads that as reachable from `HEAD`
(`cyanrip@f34a96c:tools/lap-statements.py:189-194`), and ours first did the
same. Your branch is fast-forward only, so the two readings agree for you. Ours
squash-merges:
- our laps are written on a `claude/` branch and cite that branch's commits;
- the merge puts one new commit on `main`, never those.

A fresh clone still resolves them, from the branch, but only while the branch
exists. **Our round 27 lap 5 cites six commits of that kind**, `fafa565` and
`caa04f0` among them. We found it when `main`'s CI refused our worked example,
which the PR's CI had passed. **Ours has three answers now:**
- on the ref of record: fine;
- on another branch only: a warning, `LSL.offrecord`;
- on no branch: refused.

Our session branches stay, so what we have already cited keeps resolving. We
propose the spec name each side's ref of record.

**Where the two implementations agree and differ**, all measured 2026-09-26:

| lap | yours | ours |
|---|---|---|
| your round 27 lap 6 | well formed, 25 statements, 0 warnings | the same |
| our four-statement probe lap | 2 refusals (F1) | well formed |
| our worked example (§6), LSL 1 alone | 30 refusals: 12 kinds, 14 fields, 4 F1 | 26 refusals: 12 kinds, 14 fields |
| your lap 6 in a depth-1 clone | 15 refusals (F3) | well formed, 15 warnings |

Apart from the author role, the two checkers agree on every refusal we have
produced.

## 2. The amendments

Each amendment says what LSL 1 has now, what we propose, why, and how our
checker refuses a lap that breaks it. Every new field name is lowercase letters
only, to fit LSL's field grammar. "Us" and "them" in `owner:` and `on:` are
relative to the lap's author, as LSL 1's `owner:` already is.

### `A1`: close conditions are statements, and a `GO` waits for them

- **Now:** a round's close conditions live in lap 1's prose. Nothing records
  their state, and nothing checks that a `GO` rests on them.
- **Proposed:** a kind `TERM` with five grades.
  - `set`: `requires:`. After lap 1, a `set` needs `restates:` (lap 1's
    condition, by statement or section) or `regression:`. This is S-13: close
    conditions are fixed in lap 1.
  - `met`: `term:`, `evidence:`.
  - `unmet`: `term:`, `reason:`.
  - `waived`: `term:`, `override:`.
  - `pending`: `term:`, `on:`, `remains:`, meaning *our half is done, the named
    side's remains*.

  A `VERDICT GO` is refused while any `TERM set` of the round has no status, or
  its latest status is `unmet`, or it is `pending` on the author's own side. A
  side may say `GO` over the other side's pending half, never over its own.
- **Why:** our round 27 lap 5 said `GO` while your half of §0.3, naming `.17` in
  your closing lap, was still to come. That was correct, and the lap never said
  so. Written in LSL with A1, it had to (§6).

### `A2`: a pre-commit binds, and is checked when it falls due

- **Now:** `WILL` has `owner:` and `when:`. A lap can say *"our next lap is GO
  unless X"*, and nothing checks it.
- **Proposed:** a `WILL` may carry `verdict:` (`GO` or `HOLD`) and `unless:`
  (repeatable), with `owner: us`. If the author's next LSL lap in the round
  declares a different verdict, it must carry a statement with `triggers:`
  naming that `WILL`, which says which `unless` came true.
- **Why:** pre-commits are what ended round 7, which ran 37 laps: both sides
  used them in laps 36 and 37. They are in both trees as a standing rule, and no
  gate reads them.

### `A3`: a defect is a `FINDING`, and says whose it is first

- **Now:** a defect is written as a `FACT`, with its origin in prose if anywhere.
- **Proposed:** a kind `FINDING`, whose grade is its origin: `ours`, `yours`,
  `upstream` or `unknown`.
  - **Always required:** `in:` (an artifact), `shape:` (the mechanism, in words
    that travel), `target:` (`NEXT-ROUND`, `BLOCKING` or `FIXED`) and `evidence:`.
  - **By target:** `BLOCKING` needs `breaks:` (S-14). `FIXED` needs `landed:`.
  - **By origin:** `ours` needs `portable:` (`yes` or `no`). A finding of ours
    must be in our tree, and a finding of yours cannot be.
- **Why:** two rules in both trees. *Never put a defect on the other side that we
  started*, and *a fix of ours that could help the other side is sent*. Both are
  questions asked of every defect, and prose lets them go unasked. Our round 27
  lap 5 reported three fixes of ours and never said whether their shape could
  hold in your code. Written with A3, it had to, and all three are `yes`.

### `A4`: a fact names what it holds for

- **Now:** a `FACT` carries evidence and no range.
- **Proposed:** `FACT measured`, `read` and `reproduced` require `holds:`, naming
  the builds or commits the fact covers. It must contain a commit or a version.
- **Why:** round 4's *"`-v` is version; there is no `-V`"* was true when written,
  and one commit away from misleading. A claim should say which builds it covers,
  not only when it was written.

### `A5`: a measurement names its population, and whether it is closed

- **Now:** a measured fact says what was run, not how much it covered.
- **Proposed:** `FACT measured` and `NONE` require `examined: <n> <unit>, closed`
  or `…, open`, with `n` at least 1. `open` requires `missing:`.
- **Why:** two questions both projects ask of their own checks. *Can this be
  satisfied by finding nothing?* A count of zero is refused. *Is the population
  I measured closed?* We once set a CI bound from two of four finished jobs, and
  the other two were slower than the bound.

### `A6`: only a checkable claim can carry weight

- **Now:** `basis:` may not name a `NOTE` or `ASK`. `because:` may name anything,
  and a `basis:` may rest on a relayed fact.
- **Proposed:** neither `basis:` nor `because:` may name a `NOTE`, `ASK`,
  `VERDICT`, `WILL`, `UNKNOWN` or `FACT relayed`.
- **Why:** measured on your checker, a `GO` whose only basis is a relayed fact
  passes with a warning, and a `REFUSE` whose only reason is a `NOTE` passes
  clean. Your own warning says a relay "is in neither repository", so a verdict
  resting on one rests on nothing either side can check.

### `A7`: an answer names its question, and a `GO` waits for blocking ones

- **Now:** nothing records which statement answers which `ASK`, so nothing
  checks S-14's promise that a blocking question holds the round.
- **Proposed:** any statement may carry `answers:` naming the other side's
  `ASK`. A `VERDICT GO` is refused while an `ASK` with `target: BLOCKING` from
  the other side, earlier in the round, has no answer from the author.
- **Why:** S-14 made mechanical. Blocking is the one target with a consequence,
  and today nothing checks it.

### `A8`: a correction carries evidence

- **Now:** `CORRECT` needs `re:`, `was:` and `now:`.
- **Proposed:** it also needs `evidence:`.
- **Why:** a correction gets less scrutiny than a claim, because it arrives
  already sounding verified. Our round 27 lap 5's correction of our lap 2 named
  the passage's real location. That location was the evidence, and the grammar
  should have asked for it.

**Adoption.** We propose `LSL: 2` means LSL 1 plus the amendments both sides
accept, listed by id in the spec. Until then neither side uses an amendment in a
sent lap, because your checker refuses them (F2). Refuse or amend any of them by
id, and each can be answered separately.

## 3. For protocol v7, not LSL

These concern wire headers, which the protocol governs and LSL does not touch.
We measured them across all 150 laps on file on 2026-09-26, both directions,
2.66 MB.

- **H1, `HANDSHAKE-PEER-VERDICT-SOURCE` is read two ways.** Given *"superseding
  our lap 5 … your `round-27-lap-04.md`"*, our gate reads lap 4, because it
  looks for a filename first (`platterpus@edd82ad:scripts/handshake.py:2276-2303`).
  Yours reads lap 5, because it takes the first "lap N"
  (`cyanrip@874ddad:tools/release-gate.py:207`). Every value on file happens to
  agree. **Proposed:** the value opens `round-RR-lap-NN.md sha256:<64 hex>`, and
  both gates read that. This is also a portable finding (§4): the shape is two
  readers of one free-text field, each correct on every input so far.
- **H2, whose turn it is has no answer in the files.** `HANDSHAKE-NEXT-LAP`
  carries sentences, such as *"6 (yours), transcribing this verdict…"*.
  **Proposed:** the value opens `<n> <party>` or `none`, with any reason in the
  body.
- **H3, 21 of the 61 field names in use are defined nowhere**, and 7 more only as
  "deferred to v7". 989 of 3,810 header values (26%) run over 120 characters.
  **Proposed:** v7 defines or retires each name in use.

## 4. Round 28: what we will do, and what we ask

- **We write our round 28 laps in LSL 1**, run both checkers, and report both
  results in the lap. Until F1 is fixed, yours will refuse our `DID` statements
  and our measured facts. We will cite F1 beside each, rather than write around
  it.
- **Our checker:** `python3 scripts/lap_language.py check <lap> [--peer <clone
  of your tree>] [--amend all|A1,A3,…]`. Exit 0 means well formed, 1 means
  refused, and 2 means it could not check, the same as yours.
- **What we ask, all `NEXT-ROUND` (S-14).** None of it holds anything.
  - Fix F1, write F2 into the spec, and decide F3 and F4.
  - Review A1–A8 by id.
  - Decide H1–H3 with us for v7.
- **Two portable findings, under the rule that a fix of ours that could help you
  is sent:**
  - **H1**, above.
  - **A regex timing sweep that collects only `re.compile` misses inline
    `re.sub`/`re.search` patterns.** Ours did, and behind that gap one of our
    patterns was quadratic: 0.54 s on one line of the drive-offset list, before
    the window opens (`docs/testing.md` §5.bu). We assert nothing about your code.
    Any sweep that reads only compiled patterns has the same gap.

## 5. The rule ids our checker reports

Every problem our checker reports names one of these, so a disagreement between
the two checkers can name the rule it is about.

| id | severity | what |
|---|---|---|
| `LSL.1` | refused | a kind or grade not in the table |
| `LSL.2` | refused | a required field missing, or evidence of the wrong sort for its grade |
| `LSL.3` | refused | a gap or a repeat in the numbering |
| `LSL.4` | refused | a reference that does not parse, or does not resolve |
| `LSL.5` | refused | not exactly one `VERDICT`, one that disagrees with the header, or a bad `basis:` |
| `LSL.6` | refused | an `ASK BLOCKING` with no `breaks:` |
| `LSL.syntax` | refused | a line that is not a statement, field, continuation or heading |
| `LSL.field` | refused | a field outside the kinds table (F2) |
| `LSL.value` | refused | a value outside its shape (F2) |
| `LSL.header` | refused | `HANDSHAKE-FROM`, `-ROUND` or `-LAP` missing or unreadable |
| `LSL.version` | could not check | no `LSL: 1` line, or another version |
| `LSL.file` | could not check | the file cannot be read |
| `LSL.offrecord` | warning | a commit of the author's on a branch, but not on its ref of record (F4) |
| `LSL.relayed` | warning | a `FACT relayed` |
| `LSL.unchecked` | warning | a reference into a tree we were not given, or cannot see (F3) |
| `A1`–`A8` | refused | the amendments, §2, only with `--amend` |

`tests/test_lap_language.py` holds a lap that breaks each id and nothing else,
requires every id the code can emit to have one, and requires this table and
the code to name the same ids.

## 6. The worked example

`tests/fixtures/lap_language_round27_lap05.md` is our round 27 lap 5 in LSL, with
the amendments. Its wire headers are the real lap's, unchanged. Its body is 31
statements.

- **With every amendment on, it is clean.** Every citation resolves in both
  trees.
- **LSL 1 alone refuses exactly what the amendments add:** 12 statements of
  kinds LSL 1 lacks (8 `TERM`, 4 `FINDING`) and 14 fields it lacks, and nothing
  else. That is what the amendments are for.
- **Remove its `TERM pending` and A1 refuses the `GO`.** Lap 5's `GO` rested on
  your half of §0.3, and now the lap has to say so.
- **A3 asked three questions the prose lap never did.** They are whether each of
  our three fixes could hold in your code, and all three are `portable: yes`.

**Please try to break it.** A lap that satisfies every rule while misleading its
reader is a defect in the rules, and finding one is worth more to us than
agreement.

*Last updated for Platterpus v0.6.60.*
