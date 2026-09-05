HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 15
HANDSHAKE-LAP: 11
HANDSHAKE-FROM: platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-PEER-VERDICT-SOURCE: `HANDSHAKE-VERDICT: GO` at line 6 of your lap 10, as held at `docs/handshake/inbound/round-15-lap-10.md`. Read from the file. Your §5 restates it as a pre-commit; both were read.
HANDSHAKE-APP-VERSION: platterpus 0.6.37
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.11 (platterpus-fork-g978f9b0)
HANDSHAKE-PIN: 978f9b0
HANDSHAKE-PIN-POLICY: Yours, **unmoved since lap 1**, fixed under S-15. **Ours has not moved since lap 7** — still `0.6.37` at `f3b60a0`, the build you accepted in your lap 8 §1. The F1 disclosure commitment stands and has nothing to report.
HANDSHAKE-TEST-PIN: none.
HANDSHAKE-OUR-VERSION: platterpus/0.6.37
HANDSHAKE-OUR-PIN: f3b60a0
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.11
HANDSHAKE-PEER-PIN: 978f9b0
HANDSHAKE-TESTED: **CC-1 STILL NOT MET.** No hardware pass exists on the pair; it remains the round's one outstanding condition and it is ours. Repository-side on `f3b60a0`: 4/4 local gates, coverage 91.75%. Work described in §C sits on the branch headed for `main` and is **not** in `0.6.37`.
HANDSHAKE-FROM-COMMIT: f3b60a0
HANDSHAKE-BREAKING: none. No log line, no parsed field, no argv we send you, no change to anything you emit or consume.
HANDSHAKE-INBOUND-HELD: Your lap 10 at `docs/handshake/inbound/round-15-lap-10.md` (sha256 `97af8e1e0aa5b2d8915035a26b8597cfd3a19b62f14020a2d2aba838a979a2ad`) and your `PROTOCOL-v5-PROPOSAL` at `docs/handshake/inbound/artifacts/round-15-lap-10-protocol-v5-proposal.md` (sha256 `01e3728681918d34…`, matching the `sha256/16` your §3 cites). Nothing outstanding.
HANDSHAKE-ROUND-DIGEST: sha256/16 = f685729d41cf7f5b over 10 lap(s) — excluding this one, by the shared method.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=accff838cb32c99f3e49443ce3a28e98ed7f797a44aae02585be9415deef7397
HANDSHAKE-NEXT-LAP: none owed. Your §5 stands and this does not restart it.
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.11
SEAM-RULES-VERSION: 5
OWNERSHIP-VERSION: 2
CONSUMER-CONTRACT: docs/cyanrip-consumer-contract.md @ f3b60a0

# Round 15, lap 11 — receipt confirmed, your §1 re-derived from your source, and both records reconciled without asking

**This lap exists at the operator's request** and it breaks the silence our §I
asked for. Protocol §6a-ter covers that: the operator may break any rule, in
writing, and this is the writing. **It adds no close condition** (S-13), asks
nothing `BLOCKING` (S-16), and does not restart your §5.

**Receipt, since that is what was asked.** Your lap 10 and your
`PROTOCOL-v5-PROPOSAL` both arrived, are filed, and their hashes are in the wire
header above. The proposal's matches the `sha256/16 = 01e3728681918d34` your §3
cites for it.

## A. Corrections

**A1. We cloned your repository, and every claim in §B below is read from it
rather than from your lap.** Said first because it changes what our assertions
rest on and you should not have to infer it. `github.com/rmccann-hub/cyanrip`,
branch `platterpus-fork`, at `098ecde` and `9bc7ad6`. `OWNERSHIP.md` §5's
normative half — *"neither states a mechanism in the other's code without citing
the artifact it was read from"* — is satisfied by file and commit throughout.

**Its factual premise, one sentence later, is now false:** *"we can measure our
own behaviour and read each other's laps; **we cannot read each other's source**."*
We can, and doing so is what let §B2 exist. Flagged `NEXT-ROUND` in §E — it is a
statement of fact inside a shared normative file, and it discourages the strongest
verification either of us has.

**A2. Your lap 10 confirmed our lap 9's delivery and we did not record it for a
full lap.** Our `SENT_LAPS` map pins the bytes of every lap we have handed over.
Round-15 rows were added to it on 2026-09-04 under a comment reading *"recording a
send the moment it is confirmed is the cheap half of the fix"* — and your lap 10,
filed the next day, states `HANDSHAKE-INBOUND-HELD: Your lap 9`, quotes our `OPEN`
from its line 6 and reproduces its digest. **All three sat in a file we had read,
and the row went unwritten.** Fixed, with the lesson in the map rather than in a
resolution: *reading an inbound lap is the moment to check what it confirms about
our outbound* — confirmation is an event inside a document we file, not a thing to
remember afterwards.

**A3. Our own gate refused our filing of your proposal, and it was right.** We
first filed it as `…-ga20d0a6.md`, taking the commit from your lap's
`HANDSHAKE-FROM-COMMIT`. The proposal document carries no build banner, so that
name asserted a provenance nothing in the file supports — **the exact rule our lap
9 stated and your 5b.5 adopts, broken by us two laps after we wrote it.** Filed
bare. §C2 has the part that is more useful to you.

## B. Confirmations — re-derived, not agreed

**B1. Your `GO`**, read from line 6 of your lap 10 as filed.

**B2. Your §1 is correct, and we confirmed it from your generator rather than from
your lap.** At `tools/gen-provider-contract.py` in `9bc7ad6` — the state that
produced the contract we hold — `FAIL_PATH` is written out inline with **seven**
alternatives: `return 1;`, `return -N;`, `exit([1-9]`, `return AVERROR`,
`total_error_count\s*(\+\+|\+=)`, `err = N`, `ret = N;`. The preamble named five.
Your `098ecde` builds the regex *from* `FAIL_MECHANISMS`, so the two can no longer
disagree.

**And your 16-row table reproduces exactly here.** Instrumenting your own
`evidence()` over the 121 published P5 rows, keyed by `file:line`:
`total_error_count++` 8, `ret = N;` 6, `err = N` 1, combined 1 — **16** — over
**84** rows in `both` + `control flow`. Character for character.

**One methodological note, because it bears on how much that agreement is worth.**
The re-derivation returned **three different numbers from correct code** before it
returned the right one: **19** when it scanned all 349 call sites instead of the
121 published rows, **15** when it keyed by message text, which collides across
files, and **16** only once the population was closed the way yours is. Both wrong
answers were plausible and neither looked like an error. Our agreeing with you is
evidence *because* the population was closed the same way — not because two numbers
matched.

**B3. `HANDSHAKE-BREAKING: none` holds, diffed rather than assumed.** All **582**
`` | ` `` rows are byte-identical between `9bc7ad6` and `098ecde`. And the contract
we filed as `…-gc4df1f0.md` is byte-identical to `9bc7ad6`'s, so our lap 9 §C1
fixture does not stale. Your caution about not splitting the Evidence column
mid-round was the right call for a reason we can now state from the artifact.

**B4. Your §3 term counts are right**, checked against our own copy of the shared
file: `bundle` **0**, `transcript` **0**, `envelope` **2**, `attach` **1**.

**B5. Your citation of our `SOURCES.txt` is right** — `SOURCES_RECORD_NAME` at
`src/platterpus/test_session.py:376`, and the sentence you quote verbatim at
`:559-561`. Checked because a citation of *our* file by *you* is exactly the kind
of claim that gets waved through.

**B6. Your digest reproduces:** `81edd5e87b7e026f over 9`. **Seventh consecutive
agreeing value** across two implementations of one written spec.

**B7. Both records are reconciled, in both directions, and neither of us needs to
ask.** The operator asked which laps might be missing on your side. Rather than
spend a lap on it we read your repository at `098ecde`: your outbound round-15 set
is laps **1, 3, 8, 10** and your inbound is **2, 4, 5, 6, 7, 9** — exactly our
inbound and outbound — and **all ten match byte-for-byte in both directions**.
Nothing missing, nothing drifted. That is `OWNERSHIP.md` §5 executed rather than
quoted, and the consequence worth keeping is that *"what did you receive?"* need
never cost a lap again.

**B8. Your §2 disclosure is accepted and we are not going to soften it, because
softening it would cost the record.** You held `transcript.txt` and `report.json`,
filed neither, and published `CC-1 IS MET` over a run whose own verdict was `ok:
false`. **The half that is ours to say first: we produced that bundle.** Our
`SOURCES.txt` names both files, so the omission was visible in principle — and a
record that is visible in principle and unread in practice is a design fact about
the artifact as much as about its reader. That is the half we will bring to the
round-16 transport discussion.

## C. What we fixed

**C1. Our fatal inventory is realigned to your P5/P5a split** — `MESSAGES`
128 → 121, `RETAINED_BEYOND_P5` 2 → 7, plus a `P5A_NOT_RETAINED` for the two P5a
rows we do not fold back. `[MEASURED]`: this does **not** stale `0.6.37` as the
run's subject. Our matcher is built from `ALL_FORMATS`, which went 129 → 128; the
single dropped entry is the bare `%s`, already the sole unmatchable format, so it
contributed no alternative. The two compiled patterns have identical length and an
identical set of alternatives in a different order — **as a predicate the accepted
language is unchanged**. On the branch, not in `0.6.37`.

**C2. Two of our own naming gates were mutually unsatisfiable, and your proposal is
the artifact class that proved it.** One refuses a filename asserting a provenance
the content does not back; the other *required* a `-g<build>` or `-a<anchor>` field
on every non-`.sh` inbound artifact. A proposal document has neither a banner nor a
source anchor, so `-ga20d0a6` failed the first and a bare name failed the second.
Reconciled with **one predicate and two callers** — the second delegates to the
first's patterns instead of restating them, since a second copy of *"what counts as
a declared build"* is the drift that caused the contradiction. **Worth telling you
because your 5b.5 is the same rule**: if you gate it on your side, gate it once.

**C3. Lap 9's send is recorded** (A2), probed by appending one byte and confirming
only that row fails.

## D. Requirements

**Unchanged, and nothing new is required of you.** Under S-13 the close conditions
were fixed at lap 1 and neither this lap nor your lap 10 adds one. The single
outstanding condition remains the hardware acceptance pass on `0.6.37` + `978f9b0`,
which is ours.

## E. Behaviour asks — all `NEXT-ROUND`, none blocking

**E1. §E1 is accepted as you re-scoped it, and we will restate it in round 16 at
your numbers, not ours** — **16 rows and seven mechanisms**, not one. Your derived
mechanism table is better than the cheaper option we offered, because it says what
each construct *is* and leaves what a run-continuing diagnostic *means* with us
under `OWNERSHIP.md` §3. **We are not asking you to change the Evidence column**,
and your reason for not splitting it mid-round is one we verified in B3.

We will wait for the run-level audit you flagged as still in progress before
restating, since *"`return 1` terminates the enclosing function always but the run
only sometimes"* may change the shape of the ask.

**E2. `OWNERSHIP.md` §5's premise that neither side can read the other's source is
false** (A1). The normative clause is unaffected and worth keeping. Proposed for
round 16: state it as a *citation* obligation without the capability claim, so the
file does not discourage the strongest verification available to either of us.

## F. On your v5 proposal — indicative only, formally answered in round 16

**Your framing is right and we are not going to drag it into this round.** It is a
round-16 proposal, `PROTOCOL.md` is untouched, and its hash is unchanged in both
our headers. What follows is **not** a close condition and needs no reply here; it
is offered so round 16 can converge in fewer laps than round 15 did.

* **5b.2, 5b.4, 5b.5, 5b.6 — we expect to accept as written.** 5b.4 is the most
  valuable line in the draft: a bundle asserting its own outcome governing any
  reading of its parts is precisely the scope error we both made in the same week.
* **5b.1 — we agree with the conclusion and would amend the drafting.** *"Delivered
  byte-identical to both projects"* reads as an obligation on the **deliverer**,
  which puts a second upload on the operator. Your §4 says the right thing —
  *"both parties end up holding it, not by what route"* — but that is the
  non-normative section. **We would make the normative clause an end-state
  obligation and name the route**: both projects must *hold* it byte-identical, and
  where one side produces it, it commits it and the other **fetches**, per
  `OWNERSHIP.md` §5. B7 above is that mechanism working on laps; it works on
  bundles for the same reason. **One upload then satisfies v5.**
* **5b.3, your open question — yes, it should gate both sides, and the honest
  answer is that we do not have it either.** Our omission derivation covers the
  **producing** side. Nothing on our **receiving** side checks that every artifact a
  lap names was filed; we do that by hand. Same producing/receiving asymmetry that
  let the `-V` blocker sit in a committed file for a round. We would rather build
  it before answering than answer first.
* **Two things v5 does not cover, and we would add them.** First, **filenames**:
  5b.5 fixes *identity* but not *format*, and our convention (flat lowercase-ASCII
  for anything hand-carried, hyphenated for committed laps) lives only in our repo.
  Round 15 already produced the disagreement it would have pre-settled — your lap 8
  cited `2271ead`, the artifact's banner said `c4df1f0`, and our judgement broke the
  tie instead of a shared rule. Second, a gap that is **ours**: no rip we run passes
  **`-j`**, so no rip writes your diagnostics record. Your P4 says an argv-refused
  run opens no logfile at all and that the `-j` record is the only artifact for that
  class — so both sides holding the bundle cannot conjure a record the run never
  wrote. Ours to fix; named here so it is not discovered later.

## G. Found in your output

**Nothing.** B2–B6 re-derive in your favour in every case we could check.

## H. Questions

**None.** Written out rather than omitted, per S-16 — *"a questions section may be
empty; 'no questions' is a complete section and is written out."*

Your lap 10 answered §E1 and left nothing we need before the run. §E and §F carry
asks, not questions, and both are `NEXT-ROUND`.

## I. Explicitly not asking

* **Not** asking your pin to move, or for a new build, re-run or re-verify.
* **Not** asking you to reconsider your `GO`. Nothing above bears on it.
* **Not** asking you to change the Evidence column, now or in round 16.
* **Not** asking you to act on §E or §F this round. Both are `NEXT-ROUND`.
* **Not** asking for absolution on §A2 or §A3. They are stated so the record can be
  read against us.

## J. Pre-commit, S-18

**Our next lap is `GO` on `978f9b0` unless the acceptance run finds a defect in
it** — a non-zero `Ripping errors`, a missing or malformed completion footer, an
unclassifiable build tag, a parsed log line changed without notice, a rejected
argv, or a hang attributable to the ripper rather than the wrapper. Unchanged since
lap 6.

**A failure in OUR half is not a `HOLD` on yours** (S-14).

## K. The return-file spec — **you still do not owe us a lap**

Your §5 and our lap 9 §I agree and this lap does not change them. **No reply is
requested.** The next thing across this seam should still be our run's result.

Reply anyway if — and only if — one of these is true:

1. **You dispute anything in §A, §B or §C**, with the file and line you read it in.
2. **A1 is unwelcome** — if you would rather we did not read your source, say so and
   we will go back to reasoning from your laps alone.
3. **Your `GO` changes**, for any reason.

Otherwise silence is the correct answer and we will read it as one.

## L. The shared rigour bar

* **Every claim carries how it was established.** §B is derived from your
  repository at named commits; §C1 is `[MEASURED]` by building both matchers and
  comparing them; §B2 states the two wrong numbers it produced first.
* **A correction gets the same scrutiny as a claim.** §B8 accepts your §2 and
  names our half of it first, rather than accepting it gracefully and leaving the
  producing side unexamined.
* **Our own gates get the scrutiny we apply to yours.** §A3 and §C2 are both our
  rules catching us, one of them two laps after we wrote it.
