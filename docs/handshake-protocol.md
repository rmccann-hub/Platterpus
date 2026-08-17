# Handshake protocol v4

**This file is the shared language. Both projects implement it; neither owns
it.** cyanrip and Platterpus each have a gate that reads round files and decides
whether a release is permitted. Those gates must agree on every field name, every
allowed value, and what a close requires — otherwise one side can believe a round
is closed while the other believes it is open, which is precisely the failure both
gates exist to prevent.

Copy this file into both repositories. When it changes, `HANDSHAKE-PROTOCOL`
increments and **both sides must ship the new version before the next close**.

---

## 1. Where it applies, and where it does not

The protocol governs **the declared header of a round file**. It does not govern
directory layout, filenames, or storage — those are local and the two projects
already differ:

| | cyanrip | Platterpus |
|---|---|---|
| stores rounds in | `docs/handshake/round-N[-lapM].md` | `outbound/`, `inbound/`, `verified/` |
| gate | `tools/release-gate.py` | `scripts/handshake.py` |

**Neither layout is wrong and neither needs to change.** A gate reads whichever
files its own project stores and parses the header below. Do not encode the other
side's layout into your gate; that is a dependency on something it is free to
change.

## 1a. Who opens a round, and who sends lap 1 (v3 — normative)

**Settled 2026-08-13, when the operator put "who starts?" to both projects at
once without either seeing the other's answer.** That is the best available test
of a shared convention, and both sides reached the same rule by different
routes. It is recorded here, in the shared file, so neither copy can drift.

> ### The provider opens. By default, every time.
>
> **The provider is the repository that produces the artifact under review.**
> Between cyanrip and Platterpus that is **cyanrip**, and lap 1 of every round is
> cyanrip's.

### Why — and the reason that actually decides it

**Only the provider can mint the unit of work.** A round is a decision about a
**pin**; §6a-bis R4 freezes that pin once the round starts; and **you cannot open
a round against a commit that does not exist**. This is not a tiebreak between
two reasonable positions — it is constitutive of what a round *is*.

*(This was Platterpus's argument. cyanrip's own first answer reasoned from
ownership — the side that can **measure** a surface should speak before the side
that can only infer it — and ranked dependency direction third. Ours was a good
rule about who is **credible**; theirs is a fact about **what a round is**, so
theirs is the one written down. The disagreement is recorded rather than
smoothed over, because a convention both sides merely tolerate drifts.)*

Two supporting facts, both checkable rather than argued:

- Platterpus's setup wizard installs cyanrip's pinned commit, so **a consumer
  release cut first would ship an installer for a build nobody had agreed on.**
- When upstream cyanrip moved `-V` to `-v`, Platterpus shipped four call sites
  against the old flag while cyanrip's table already recorded the change. **A
  consumer that moves first is guessing at what it will receive.**

### The general form, which both sides stated independently and in nearly the same words

> **Whoever is asking for a change goes first. Whoever is being asked to trust it
> goes last.** The one making the claim writes it down; the other verifies.
> Never the reverse — a claim checked by its own author is two related witnesses.

### Three exceptions, and each is bounded

**E1 — A new requirement starts with the consumer.** A provider cannot implement
an unstated need, so the consumer names it. **But that is an *ask*, and it
belongs to the next round, not the one in flight**; it does not make the consumer
the opener of the round that eventually delivers it.

**E2 — Within a round, a blocker goes first regardless of who opened.** If one
side's defect prevents the other from producing evidence the round's own close
conditions require, the side holding the defect speaks first. *Ordering a round
and ordering the work inside one are two different questions*, and conflating
them is what made the two projects' first answers look opposed when only one was
about round initiation. (Round 8's `J11` is the worked example: a consumer defect
blocked the rip that condition 1 required, so it went first though the provider
had opened.)

**E3 — The operator may hand the opening to either side**, under §6a-ter, in
writing:

```
HANDSHAKE-OVERRIDE: 1a — Platterpus opens round N
HANDSHAKE-OVERRIDE-BY: operator (name), <date>
HANDSHAKE-OVERRIDE-WHY: <a reason a later reader can weigh>
```

### More than two repositories

The rule generalises without amendment: **the round is about one artifact, and
the repository that produces that artifact opens it.** In a chain A → B → C, a
round about B's output is opened by B, whether C or A raised the need. A
repository that is neither the producer nor named in `HANDSHAKE-TO-REPO` (§3a) is
not a party and does not open anything.

**A round has exactly one opener and one lap sequence.** Additional recipients
join that sequence; they do not start parallel rounds about the same artifact.

### Declared, not assumed

Every lap 1 carries:

```
HANDSHAKE-OPENER: cyanrip
```

so *"who opened this?"* is answered by the file rather than by convention. A
round whose lap 1 does not declare an opener is not malformed — but the field is
the only place the answer survives a year.

## 2. Declaration syntax — identical on both sides

Every field is a line of the form:

```
FIELD-NAME: value
```

**Matched line-anchored at column 0.** These properties are normative, not
implementation detail, because a gate that relaxes any of them silently accepts
files the other gate rejects:

1. **Column 0 only.** An indented copy is prose, not a declaration.
   `  HANDSHAKE-VERDICT: GO` **must not** match.
2. **Strip fenced code blocks before matching.** A declaration is a statement the
   file *makes*, not one it *quotes*. Examples, templates and conformance tables
   legitimately contain field lines at column 0 and none of them is a
   declaration. **This was found the hard way**: the lap that introduced this
   very spec documented the close requirements in a ``` block, and the gate read
   the illustrated `HANDSHAKE-PEER-VERSION` as a fact and compiled it into the
   binary. If your gate does not strip fences, it will do the same to this file.
3. **A field appearing twice is ambiguous, and ambiguity is not a close.** Do not
   take the first, do not take the last — refuse.
4. **An absent required field fails closed.** Never treat "missing" as a
   permissive default. That fallback reintroduces the entire defect: under it, a
   round closes by omitting a field.
5. **Prose containing a value is not a declaration of it.** A file whose text
   reads *"this is not a closing GO"* must not close a round.
6. **An unrecognised value is not agreement.** Treat any verdict outside the
   vocabulary below as "not closed", not as an error to skip past.

## 3. Required fields

```
HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 7
HANDSHAKE-LAP: 4
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-APP-VERSION: platterpus 0.6.3
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.4 (platterpus-fork-g<sha>)
HANDSHAKE-PIN: <sha>
```

| field | value | notes |
|---|---|---|
| `HANDSHAKE-PROTOCOL` | integer | this spec's version. A gate that reads a **higher** number than it implements must refuse the round rather than guess. |
| `HANDSHAKE-ROUND` | integer | must match the round the file belongs to. A file declaring a different round than it is filed under is a bookkeeping error and refused. |
| `HANDSHAKE-LAP` | integer ≥ 1 | absent means lap 1. **A round's state is its latest lap's verdict** — by declared number, never by filename or mtime. |
| `HANDSHAKE-FROM` | `cyanrip-fork` \| `platterpus` | who wrote it. Makes a crossed pair unambiguous without relying on filename conventions. |
| `HANDSHAKE-VERDICT` | see §4 | this side's position. |
| `HANDSHAKE-APP-VERSION` | `platterpus <semver>` | the consumer build this file's results were produced with. |
| `HANDSHAKE-RIPPER-VERSION` | `cyanrip <version> (<build tag>)` | the ripper banner, **verbatim**, that produced them. |
| `HANDSHAKE-PIN` | short SHA | the commit this file concerns. |

**Required from round 8 on.** Rounds up to and including 7 are exempt, because
neither project could comply with a spec written during round 7. A gate must pin
that boundary as a constant and assert it in a test, so widening the exemption is
a visible edit rather than a side effect. **These four are required on *every*
file, including a mid-round `HOLD`** — a lap reporting a measurement must say
which pair produced it; the §5 fields say only who agreed.

**The two version fields are load-bearing, not bookkeeping.** A round that
approves a pin approves it *for a named consumer version*. Two artifacts from the
same ripper under different app versions are not interchangeable evidence, and a
file reporting a result without saying which **pair** produced it is a
measurement with no provenance.

**Unknown fields are ignored by both parsers**, so either side may add one
without breaking the other. A format that breaks on an extra line is a format
people stop emitting.

**Each lap is a new file. Never edit a file already sent.** A round's state is
its **latest lap**, not a conjunction over all of them -- which is why a later
lap can move a round from `OPEN` to a terminal state.

**It cannot move it back.** v2 said a later lap could *reopen* a round; **v3
removes that** (§4a). A closed round is finished, and new evidence opens a new
round -- otherwise "closed" means "closed for now" and a consumer cannot pin
against it.

## 3a. Addressing — where it came from, and what it wants changed (v3)

**A handshake file may travel between more than two repositories, and a reader
must be able to confirm it is the intended recipient without being told out of
band.** Until v3 a file said only `HANDSHAKE-FROM: platterpus` — a project
nickname, not an address — and named the pin under review but never the tree the
lap itself was written from. Those are different commits and conflating them
means a lap's claims cannot be located in any repository.

```
HANDSHAKE-FROM-REPO:    https://github.com/rmccann-hub/cyanrip
HANDSHAKE-FROM-COMMIT:  a083279
HANDSHAKE-FROM-VERSION: 0.9.4-rc1+platterpus.6-beta.4
HANDSHAKE-TO-REPO:      https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-VERSION:   platterpus 0.6.12b6
```

| field | value | notes |
|---|---|---|
| `HANDSHAKE-FROM-REPO` | canonical URL | **required from round 9.** The repository the file was authored in. A URL, not a nickname: `HANDSHAKE-FROM` stays as the human-readable party name and is not an address. |
| `HANDSHAKE-FROM-COMMIT` | short SHA | **required from round 9.** The commit of the sending tree **at the moment the lap was written** — *not* `HANDSHAKE-PIN`, which is the commit under review. They are equal only by coincidence. Every `file:line` and every measurement in the lap resolves against this commit. |
| `HANDSHAKE-FROM-VERSION` | version string | the sending project's own version at that commit. |
| `HANDSHAKE-TO-REPO` | one or more canonical URLs, comma-separated | **required from round 9.** Who the file is addressed to. A repository that does not find itself here **must not act on the file** — it may read it, but it is not a party. |
| `HANDSHAKE-TO-VERSION` | version string, one per `TO-REPO` in the same order | **what the sender believes the recipient currently is.** This is the field that makes confirmation real rather than assumed. |

**The recipient has a confirmation duty and it is one line.** Its next lap must
state, explicitly, whether `HANDSHAKE-TO-VERSION` matched what it actually was:

```
HANDSHAKE-TO-VERSION-CONFIRMED: yes
HANDSHAKE-TO-VERSION-CONFIRMED: no — addressed to platterpus 0.6.12b6, we are 0.6.13
```

**`no` is not a failure and must not block anything by itself.** It is a
measurement: it says the sender reasoned about a version that was not the one
that read the file, so any claim in that lap about the recipient's behaviour is
suspect and should be re-checked before it is acted on. Silence here is the
defect, not disagreement.

**Why `TO-VERSION` and not just `TO-REPO`.** A repository is stable; the thing a
lap asks to change is a *version* of it. "Fix this in Platterpus" is
unfalsifiable a month later; "fix this in `platterpus 0.6.12b6`" can be checked
against what that build actually did.

**Fan-out.** A lap addressed to several repositories is one file with several
`TO-REPO` entries, never several edited copies. Each recipient answers with its
own lap and its own confirmation line. **A round has exactly one opener and one
lap sequence**; additional recipients participate in that sequence and do not
start parallel ones.

## 4. Verdict vocabulary — closed set

| verdict | meaning | closes? |
|---|---|---|
| `OPEN` | round opened, awaiting the other side | no |
| `HOLD` | mid-round lap; work continues, do not release | no |
| `GO` | this side affirmatively agrees to release | **only with §5** |
| `WITHDRAWN` | this side ends the round **without** agreement (v3) | **yes — see §4b** |
| anything else | unrecognised | no |

`GO` is the only *agreeing* closing value, and on its own it is still not a
close. **An unrecognised verdict never closes anything**: a gate that has not
heard of a value fails closed rather than guessing, because guessing is how two
gates come to disagree about the one thing they exist to agree on.

## 4a. Legal states, and the only transitions between them (v3)

**A round and a lap each have a state, the set is closed, and every transition
is listed. Anything not listed is illegal and a gate must refuse it.** Before
v3 the states existed only as prose and each gate inferred them, which is how
one project's gate closed a round whose latest lap said `HOLD`.

### Round states

| state | meaning | terminal? |
|---|---|---|
| `OPEN` | opened by the opener; laps in flight | no |
| `RECONCILE` | the two sides hold different records — §5a digest mismatch | no |
| `CLOSED` | `GO` on both sides with every §5 field present | **yes** |
| `WITHDRAWN` | ended without agreement | **yes** |
| `EXPIRED` | `HANDSHAKE-CLOSE-BY` passed with no terminal state reached | **yes** |

### Legal transitions

| from | to | trigger |
|---|---|---|
| *(none)* | `OPEN` | the opener sends lap 1 |
| `OPEN` | `RECONCILE` | either side's `HANDSHAKE-ROUND-DIGEST` disagrees (§5a) |
| `RECONCILE` | `OPEN` | both digests agree again after exchanging the missing laps |
| `OPEN` | `CLOSED` | §5 satisfied on both sides |
| `OPEN` | `WITHDRAWN` | either side declares `WITHDRAWN` |
| `OPEN` | `EXPIRED` | `CLOSE-BY` passes while still `OPEN` |
| `RECONCILE` | `WITHDRAWN` | either side declares `WITHDRAWN` |
| any terminal | *(nothing)* | **a terminal state is final** |

**Illegal, and named because each has been attempted:**

- `RECONCILE → CLOSED`. **A round may not close while the two sides hold
  different records.** Closing on a record one side has not seen is the
  thirteen-laps-of-one-sided-conversation failure with a ribbon on it.
- `CLOSED → OPEN`. A closed round is finished. New evidence opens a **new
  round**; it does not reopen a decision already acted on. (v2 permitted a later
  lap to reopen a round. **v3 removes that**: reopening makes "closed" mean
  "closed for now", and a consumer cannot pin against that.)
- `EXPIRED → OPEN` by extending the date. See §6b R2.
- Any transition out of `WITHDRAWN`.

### Lap states

A lap is `DRAFT` → `SENT` → `RECEIVED` → `ANSWERED`.

**`SENT` is irreversible and is the whole reason the record is append-only.** A
sent lap is never edited; a correction is a **new lap** that says what it
corrects. A lap that was drafted and never sent may be edited or deleted freely
and leaves no trace — but the moment it is handed over it is evidence.

**`RECEIVED` is only claimable by the recipient**, in its own next lap, via
`HANDSHAKE-INBOUND-HELD` (§5a). The sender may never mark its own lap received;
that is the assumption that hid thirteen undelivered laps.

## 4b. `WITHDRAWN` — ending without agreement (v3)

`WITHDRAWN` closes a round and requires **none** of the §5 agreement fields,
because there is no agreement to record. It requires instead:

```
HANDSHAKE-VERDICT: WITHDRAWN
HANDSHAKE-WITHDRAWN-REASON: <one line, why this round is ending unfinished>
```

**And a gate must additionally assert that no release names a withdrawn
round.** Without that, `WITHDRAWN` becomes a way to smuggle a release past the
"no release while a round is open" rule by ending the round instead of closing
it. That assertion is not optional and is the reason `WITHDRAWN` did not exist
before v3: a terminal state with no such guard is worse than none.

**Either side may withdraw unilaterally.** Withdrawal is not a veto over the
other project — it ends *this round*, and the work returns as a new round when
someone is ready.

## 5. Closing a round is affirmative and two-sided

**A round closes only when all of the following are true.** One side saying `GO`
is a statement about its own tree, not agreement — "they did not object" is never
"they agreed".

```
HANDSHAKE-VERDICT: GO
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-OUR-VERSION: 0.9.4-rc1+platterpus.4
HANDSHAKE-OUR-PIN: <commit sha>
HANDSHAKE-PEER-VERSION: platterpus/0.6.4
HANDSHAKE-PEER-PIN: <commit sha>
HANDSHAKE-TESTED: <what was run, on which pair>
```

| field | why it is required for a close |
|---|---|
| `HANDSHAKE-PEER-VERDICT` | the other half of the agreement, transcribed from the file they actually sent. Not inferred from their silence, their tone, or the absence of objections. |
| `HANDSHAKE-OUR-VERSION` / `HANDSHAKE-PEER-VERSION` | **which two programs agreed.** An agreement that does not name its parties cannot be quoted later. |
| `HANDSHAKE-OUR-PIN` / `HANDSHAKE-PEER-PIN` | commit SHAs. A version string can be reused across builds; a SHA cannot. Pin SHAs, never tags or branch tips. |
| `HANDSHAKE-TESTED` | **no release without testing.** A round that closed with nothing tested is a release nobody checked. Name what ran and on which pair of builds. |

Any one missing → **the round stays open**, and the gate must say *which* field is
absent rather than refusing without a reason.

### The peer verdict is transcribed, not judged

Write down what they declared. If they said `HOLD`, record `HOLD` — do not
translate an encouraging paragraph into a `GO`. If their file is ambiguous, that
is a lap, not a close.

## 5a. Both sides must be able to prove they hold the same record (v3)

**This is the checksum, and it exists because both gates reported healthy
through thirteen laps that one side never received.** Each gate read only its
own directory. A gate that reads only its own outbox cannot tell *"they agreed"*
from *"they never got it"*, and reports green for both — a check that can only
pass by finding nothing.

Two fields, and they do different jobs. Ship both.

### `HANDSHAKE-INBOUND-HELD` — the enumeration

```
HANDSHAKE-INBOUND-HELD: round-08-lap-02.md (OPEN), round-08-lap-08.md (HOLD), round-08-lap-10.md (GO)
HANDSHAKE-INBOUND-HELD: none
```

Every lap **of this round, from the other parties**, that the writer actually
holds, with each one's declared verdict. `none` is a legal and meaningful value
and must be written out — *"we hold none of yours"* and *"we forgot to say"* are
different claims.

**It also carries the negative.** If the writer believes a lap number does not
exist, say so: *"there is no lap 4"* and *"we never received your lap 4"* are the
two answers a broken channel makes indistinguishable, and only the sender can
tell them apart.

### `HANDSHAKE-ROUND-DIGEST` — the checksum

```
HANDSHAKE-ROUND-DIGEST: sha256/16 = 9f3c1a77b2e40d81 over 5 lap(s)
```

Computed over **every lap of this round the writer holds, its own and inbound
alike — excluding the lap being written** (see "Self-reference" below). The
construction is fixed so two independent implementations produce the same
value:

1. For each lap file: `sha256` of its **exact bytes**.
2. Form one line per lap: `<lap number>\t<HANDSHAKE-FROM>\t<sha256 hex>`.
3. Sort those lines **byte-wise ascending**.
4. Join with `\n`, append a trailing `\n`, encode UTF-8.
5. `HANDSHAKE-ROUND-DIGEST` is the **first 16 hex characters** of the `sha256`
   of that, and the count of laps included.

**Deliberately over the lap number and `FROM`, not the filename.** Filenames are
local layout and the two projects already differ; a digest that depended on them
would disagree by construction. And deliberately over exact bytes, so a lap that
was reflowed or re-encoded in transit does not silently pass as the original.

### What counts as one lap (v4)

**A file is one lap, for digest purposes, only if — after fenced code blocks are
stripped — it declares `HANDSHAKE-ROUND`, `HANDSHAKE-LAP` and `HANDSHAKE-FROM`
exactly once each.** Anything else is excluded, and its exclusion is not an
error.

This follows from §2 rule 3, which already says a field declared twice is
ambiguous and that ambiguity is never resolved by taking the first or the last.
**A file with two `HANDSHAKE-LAP` lines is not a lap; it is a file *containing*
laps.**

**Why it is a rule and not an implementation detail.** Platterpus built a
transport envelope — one file carrying three laps verbatim so an operator could
send one attachment instead of three — and their first enumerator read the first
`HANDSHAKE-LAP` in its body and counted the envelope as a fourth lap. The digest
that came out was stable, reproducible, and described a record neither side
held. Under §4a that is not a harmless difference: it puts the round into
`RECONCILE`, a state exchanging files cannot exit, because there is nothing
missing to exchange.

**Derived, not listed.** A filename exclusion, or a list of known container
formats, only ever excludes the container someone has already met. This test
excludes the next one too. **Neither project maintains a list.**

*(Proposed by Platterpus, round 9 lap 2 §A1-a, from their own defect. Adopted
verbatim in substance.)*

### Self-reference — the digest excludes the lap that carries it (v4)

**A digest over exact bytes cannot include the file carrying it**, and a spec
that ignores that guarantees a permanent disagreement rather than a detectable
one.

> **The digest declared in lap N covers every lap of the round the writer holds
> at the time of writing, excluding lap N itself.**
>
> **A verifier checks it by computing over its own holdings, excluding that same
> lap N** — not excluding the verifier's own newest lap.

The second sentence is the one that makes the check well-defined, and it is not
symmetric with the first: the writer excludes *itself*, the reader excludes *the
file it just received*. Equality then means precisely **"we hold the same record
apart from the lap in flight"**, which is the claim wanted. Without it, each side
excludes a different file and the numbers differ forever by construction — the
failure this section exists to prevent, reintroduced by the fix for a different
one.

**Consequence, and it is a feature:** two sides mid-exchange will report
different lap counts, and **the difference is exactly the laps in flight**. That
is information, not noise. A gate should print both counts rather than only the
verdict.

*(Proposed by Platterpus, round 9 lap 2 §A1-b. The verifier-side half is
cyanrip's amendment to the amendment: their wording defines what the writer
computes and leaves what the reader compares it against undetermined.)*

### What a mismatch means, and what it forbids

**Equal digests:** both sides hold the same record. Proceed.

**Unequal digests:** the round moves to `RECONCILE` (§4a). Each side sends the
laps the other's `INBOUND-HELD` shows it is missing, both recompute, and the
round returns to `OPEN` when they agree.

> **A round MUST NOT close while the digests disagree.** This is the rule the
> whole section exists for. A `GO` exchanged over divergent records is two
> parties agreeing about different things.

**A gate must print both values whenever it prints a round's state**, so a
mismatch is visible without being asked for. Silence about a digest is
indistinguishable from a matching one, which is the failure again.

## 6a-bis. Convergence — a round must be able to end (v3)

**Round 7 ran 37 laps, 10 test pins and 8 pre-releases without producing a
release. Nothing in it was bad work.** The round failed because it had no
closing condition that could not be extended, and the properties that made the
work good — thoroughness, adversarial reading, finding one more thing — are
exactly the ones that keep it open. These rules are load-bearing and a gate
should refuse or warn on each.

**R1 — Close conditions are fixed in lap 1 and cannot grow.** A criterion
discovered later belongs to the *next* round, unless it is a regression in the
pin under review. Otherwise the finish line moves every time either side is
thorough.

**R2 — `HANDSHAKE-CLOSE-BY` is set in lap 1 and is not extended.** It is an
**ISO 8601 instant** (`2026-08-22T23:59:59Z`) — never a bare date, which names
no timezone and gave two defensible answers to *"has it passed?"* on the same
afternoon. It is **advisory to the gates and mandatory in the file**: a gate
*prints* whether it has passed and never enforces it, because enforcement lets a
clock skew block a release. When it passes with no terminal state reached, the
round is `EXPIRED` (§4a) and its work returns as a new round.

**R3 — A finding defaults to `NEXT-ROUND`.** Promoting one to blocking requires
naming **what it breaks in the artifact under review**. *"It is a real defect"*
is an argument for fixing it, never on its own for holding a release.

**R4 — Once agreed, the pin does not move for the rest of the round**, unless it
is found unsafe. Fixes queue. A pin that moves whenever something is fixed
guarantees the evidence is always about a build nobody is reviewing.

**R5 — Questions carry a target: `BLOCKING` or `NEXT-ROUND`.** `BLOCKING`
must satisfy R3. **A questions section may be empty**, and *"no questions"* is a
complete section. A spec that requires questions manufactures work faster than
the round can close it.

**R6 — Pre-commit is mandatory from lap 5 onward.** Every lap from the fifth
must contain a line of the form:

> *our next lap is `GO` unless X*, naming X.

It binds. **Name an event, never a lap number** — *"the first lap we send after
receiving your lap 10"*, not *"our lap 15"* — because a lap number can be
overtaken by the sender's own choices and then has to be restated, and restating
a pre-commit twice is the failure this rule exists to prevent.

**R7 — Lap ceiling.** At **lap 21** a round must reach a terminal state. A lap
22 is illegal without a recorded override (§6a-ter). Twenty-one laps is more
than twice what any successful round has needed and is set where it cannot bind
good work — only runaway.

## 6a-ter. Overrides — the operator may break any rule, in writing (v3)

**Every rule above may be overridden by the human operating both projects.**
None of this is a safety system against a person; it is a coordination system
between two programs, and a person who understands the trade is entitled to make
it.

**An override is only real if it is recorded in the file:**

```
HANDSHAKE-OVERRIDE: R4 — pin moved to 2ce8993 mid-round
HANDSHAKE-OVERRIDE-BY: operator (rmccann), 2026-08-15
HANDSHAKE-OVERRIDE-WHY: the round's only hardware evidence needs the cache-probe fix; the cost of a second rig session exceeds the cost of re-gathering §A
```

- **Rule id, who, and why. All three.** A "why" that says *"approved"* is not a
  reason and a later reader cannot weigh it.
- **A gate honours a recorded override and prints it loudly** — every time it
  prints the round's state, not once. An override that becomes invisible after
  the session that made it is indistinguishable from the rule never existing.
- **An unrecorded override did not happen.** If a gate would refuse without the
  line, it refuses. This is the whole mechanism: overrides are cheap and
  legitimate, but they leave a mark.
- **Overrides do not stack silently.** Each is one rule, one line. A single
  override cannot suspend "the rules".
- **No override of §5a's digest rule.** A round must never close while the two
  sides demonstrably hold different records — that is not a policy trade, it is
  agreeing about different things, and no reason makes it mean something.

## 6. Optional fields

```
PROVIDER-CONTRACT: PROVIDER-CONTRACT.md @ <sha>
HANDSHAKE-SOURCE-ANCHOR: sha256/16 = <hex>
HANDSHAKE-TEST-PIN: <sha>
```

`PROVIDER-CONTRACT` is a resolvable pointer to the generated interface contract
at a specific commit, so a consumer's machine-readable check has something to
resolve rather than parsing prose. **Do not write "unchanged" unless you have
compared** — that sentence has already been proposed once when the contract had
in fact moved.

`HANDSHAKE-SOURCE-ANCHOR` pins that contract by **content** rather than by
pointer, so it stays checkable if the file is ever moved or renamed.

### 6a. `HANDSHAKE-TEST-PIN` — and the deadlock it exists to break

**A round cannot close without evidence that can only be gathered by installing
the build the round is reviewing.** Written out, our own rules deadlock:

1. A close requires `HANDSHAKE-TESTED`, naming what ran on which pair.
2. Hardware evidence can only be gathered on the rig.
3. The rig installs the pinned build.
4. Neither project may switch the pin while a round is open.
5. So the rig runs the *previous* release — the one without any of the changes
   under review.
6. So `HANDSHAKE-TESTED` can never describe the build being reviewed.
7. So the round never closes.

Every step is a rule both projects hold, and together they are unsatisfiable.
The fault is conflating two different pins:

| | what it is | who installs it | closes a round? |
|---|---|---|---|
| **production pin** (`HANDSHAKE-PIN`) | the agreed build | everything | it *is* the agreement |
| **test pin** (`HANDSHAKE-TEST-PIN`) | a build designated to gather the evidence a close needs | the rig, deliberately, for a session | **never** |

**A test pin is not a release and must never be treated as one.** Declaring it
does not close a round, does not move `HANDSHAKE-PIN`, and does not permit a
release. A gate must assert that a file declaring only a test pin still refuses.

Both sides declare the same test pin, in writing, before the session. Logs it
produces say `NOT a released build`, which is correct and is the point — the
artifact records that it came from a build under review rather than an agreed
one. Those logs are what `HANDSHAKE-TESTED` then cites.

**Sequence:** agree the test pin → both install it → run the session → both file
the results → *then* the round can close on that evidence, moving
`HANDSHAKE-PIN` to what was tested.

### 6b. Pre-releases, for projects whose artifact is a release

A test pin works when the other side builds from a tree. When a project's
artifact is something a user *installs* — an AppImage, a package — the test pin
has to be a published pre-release, and a gate that refuses all releases refuses
that too.

So the gate distinguishes what a release *claims* rather than whether one
happens:

| | permitted with a round open? |
|---|---|
| **stable release** | **no** — it claims the pair was jointly verified |
| **pre-release / beta** | **yes**, after printing every open round |

A beta claims no joint verification: it ships saying so, and every rip it makes
records that in its own artifact. **Refusing it would not protect a user; it
would guarantee the round can never close**, because the evidence a close
requires can only come from running the thing.

Proposed by Platterpus in round 7 lap 7, adopted by cyanrip in lap 8. Both gates
take a `--prerelease` flag which prints the open rounds first, so permitting a
beta is never quiet.

Proposed by cyanrip in round 7 lap 6. Carried as an **optional** field on
purpose: v2 gates ignore unknown fields, so it costs the other side nothing
before they implement it. **`HANDSHAKE-PROTOCOL` is deliberately not bumped for
this** — a bump would make every v2 gate refuse the file that proposes it, which
is the opposite of what a proposal needs. It becomes v3 only once both sides
implement it.

## 7. Rip-time verification

The header above governs *documents*. It cannot tell anyone, months later,
whether a **particular rip on disk** came from an agreed pair. That needs the
artifact itself to carry it.

cyanrip therefore compiles its round state into the binary and prints two lines
into every logfile:

```
Handshake:      round 7 lap 3 OPEN, verdict HOLD -- NOT a released build
Consumer:       platterpus/0.6.3
                (reported by the caller, not verified by cyanrip)
```

- **`Handshake:`** is *derived*, by `tools/gen-handshake-state.py`, from the same
  round files the gate reads, regenerated by the build whenever one changes. It
  is not a hand-maintained string. A build from a tree with an open round says so
  in every log it writes, permanently.
- **`Consumer:`** is whatever the caller passed to `--consumer` (`-u`), recorded
  verbatim. **cyanrip cannot verify it**, and the line says so rather than
  implying a check happened. Absent the flag it reads
  `not identified (no --consumer given)` — a field that answers the question
  beats a field that is missing and prompts it.

**Platterpus should pass `--consumer <name>/<version>` on every rip.** Together
the two lines let anyone holding only the log answer "which pair produced this,
and had they agreed?" without access to either repository.

Neither line is a quality verdict. They report what was configured and what the
caller claimed, with provenance — the judgement stays downstream.

## 8. Conformance

A gate implementing this spec must refuse a release in every one of these cases.
Both projects should have a test per row; cyanrip's are in
`tests/release_gate.py`.

**Each row has a stable ID.** Cite them when reporting a disagreement, so the two
projects are provably talking about the same row rather than the same paraphrase.
cyanrip's `tests/release_gate.py` declares which rows each test covers and asserts
every ID here is covered by at least one — a coverage claim that is derived from
this table rather than asserted alongside it.

| ID | case | expected |
|---|---|---|
| C1 | our `GO`, no peer verdict | refuse, naming the missing peer verdict |
| C2 | our `GO`, peer `HOLD` | refuse, naming the peer verdict |
| C3 | both `GO`, any identity field missing | refuse, naming the field |
| C4 | both `GO`, no `HANDSHAKE-TESTED` | refuse |
| C5 | verdict field absent entirely | refuse |
| C6 | verdict declared twice | refuse as ambiguous |
| C7 | verdict indented / inside prose | refuse; the declaration did not match |
| C8 | a complete close **illustrated inside a ``` block** | refuse, and do not adopt any of the illustrated values |
| C9 | a round ≥ 8 file missing any of `FROM` / `APP-VERSION` / `RIPPER-VERSION` / `PIN` | refuse, naming the field — including on a mid-round `HOLD` |
| C10 | a round ≤ 7 file missing them | **allow**; the exemption is by pinned number |
| C11 | unrecognised verdict | refuse |
| C12 | declared round ≠ the round it is filed under | refuse |
| C13 | a later lap declaring `HOLD` after an earlier lap's `GO`, where that `GO` did **not** close the round (no peer verdict, missing fields) | refuse — the round was never closed, and the latest lap governs |
| C13a | a later lap of any verdict after the round reached a **terminal** state (§4a) | refuse the *file* as an illegal transition; the round stays closed. **v3 changed this**: under v2 it reopened the round |
| C14 | no round files at all | refuse; an empty record is not agreement |
| C15 | `HANDSHAKE-PROTOCOL` higher than implemented | refuse rather than guess |
| C16 | complete two-sided tested round | **allow** — a gate that can never say yes is a wall, not a gate |
| C17 | a file declaring `HANDSHAKE-TEST-PIN` and otherwise complete, but verdict `HOLD` | refuse; a test pin is not a release |
| C18 | `HANDSHAKE-TEST-PIN` present alongside a valid close | **allow**, and the test pin must not be mistaken for `HANDSHAKE-PIN` |
| C19 | a **stable** release requested with any round open | refuse |
| C20 | a **pre-release** requested with a round open | **allow**, and print every open round first — a beta claims no joint verification, and refusing it guarantees the round can never close |

### Rows added in v3/v4 — required once both gates implement 4

**These are not yet in force.** A gate implementing protocol 2 must not be
failed for missing them, and a gate implementing 4 must have every one. The
split is by heading rather than by a list a test hardcodes, so bumping
`PROTOCOL_VERSION` turns them on with no second edit — a deferral that needs a
human to remember it is a deferral that rots.

| ID | case | expected |
|---|---|---|
| C21 | `HANDSHAKE-ROUND-DIGEST` present on both sides and **unequal** | refuse; the round is `RECONCILE` and **may not close**. Not overridable (§6a-ter) |
| C22 | a close attempted while the round is `RECONCILE` | refuse, naming both digests |
| C23 | `HANDSHAKE-INBOUND-HELD` absent on a round ≥ 9 file | refuse; silence about what you hold is the failure this field exists for |
| C24 | `HANDSHAKE-INBOUND-HELD: none` | **allow** — `none` is a claim, and a legal one |
| C25 | a round ≥ 9 file missing any of `FROM-REPO` / `FROM-COMMIT` / `TO-REPO` / `TO-VERSION` | refuse, naming the field |
| C26 | a file whose `TO-REPO` does not name this repository | **do not act on it**; it may be read and stored, but this repository is not a party |
| C27 | a release naming a round whose latest verdict is `WITHDRAWN` | refuse — otherwise `WITHDRAWN` smuggles a release past C19 |
| C28 | `HANDSHAKE-VERDICT: WITHDRAWN` with no `HANDSHAKE-WITHDRAWN-REASON` | refuse |
| C29 | a lap declaring a **lower** `HANDSHAKE-PROTOCOL` than an earlier lap of the same record | refuse; under-declaring is silently valid to a version check and asks the peer to grade the file by rules the sender is not following |
| C30 | lap number > 21 with no recorded override | refuse (§6a-bis R7) |
| C31 | `HANDSHAKE-OVERRIDE` present with `-BY` or `-WHY` missing | refuse; an override without a weighable reason is not recorded, and an unrecorded override did not happen |
| C32 | a valid, complete `HANDSHAKE-OVERRIDE` | **honour it, and print it every time the round's state is printed** — an override that becomes invisible is indistinguishable from the rule never existing |
| C33 | an override naming §5a's digest rule | refuse; that rule alone is not overridable |
| C34 | a file declaring `HANDSHAKE-LAP` (or `ROUND`, or `FROM`) more than once, after fences are stripped | **exclude it from the digest**; it is not a lap. Not an error |
| C35 | a lap whose declared digest includes itself | refuse; a digest over exact bytes cannot cover the file carrying it |
| C36 | verifying a peer's digest by excluding **your own** newest lap rather than **theirs** | refuse; the exclusion is of the lap in flight, and getting this backwards makes the two sides disagree forever |

That last row matters as much as the others. Assert it, or a gate that refuses
everything passes every other test in the table.

## 9. Grandfathering

Rounds recorded before this spec existed have no verdict field. They are
exempted **by number**, in a set the gate pins and a test asserts — never by a
rule like "a missing verdict is fine for old rounds", which is the fallback that
lets any new round close by omission.

- cyanrip grandfathers rounds `{5, 6}`.
- Platterpus grandfathers rounds `{1, 2, 3}` for the prose form and `{1..7}` for
  the header form.

**Both sets may shrink, never grow.** Round 7 is grandfathered on both sides for
the wire header, because neither side could comply with a spec being written
during it.

## 10. Changes in v2

Adopted from Platterpus's round-7 lap-3 proposal, which arrived independently and
is better than what v1 had:

- `HANDSHAKE-FROM`, `HANDSHAKE-APP-VERSION`, `HANDSHAKE-RIPPER-VERSION` and
  `HANDSHAKE-PIN` become required. v1 named the *agreeing* versions only in the
  closing fields; v2 names the *producing* pair on every file, so a mid-round lap
  reporting a measurement says which two builds produced it.
- Unknown fields are explicitly ignored rather than merely tolerated.

A v1 gate reading a v2 file refuses, which is correct and is why the number
moved. **Both sides ship v2 before the next close.**

Widening either set is a visible edit to a pinned constant, and it should be
argued for in a round rather than done quietly.

## 11. Changes in v3

**v3 exists because round 8 produced three failures that v2 could not have
caught, and one of them ran for thirteen laps.**

- **§3a Addressing.** `HANDSHAKE-FROM-REPO`, `HANDSHAKE-FROM-COMMIT`,
  `HANDSHAKE-FROM-VERSION`, `HANDSHAKE-TO-REPO`, `HANDSHAKE-TO-VERSION`, and the
  recipient's `HANDSHAKE-TO-VERSION-CONFIRMED` reply. A file can now say **where
  it came from, at which commit, and which version of which repository it is
  asking to change** — and the recipient confirms rather than assumes. Required
  from round 9. `HANDSHAKE-FROM-COMMIT` is deliberately **not**
  `HANDSHAKE-PIN`: one is where the lap was written, the other is what it is
  about, and they are equal only by coincidence.
- **§4a Legal states, as a closed set with every transition listed.** Round:
  `OPEN`, `RECONCILE`, `CLOSED`, `WITHDRAWN`, `EXPIRED`. Lap: `DRAFT`, `SENT`,
  `RECEIVED`, `ANSWERED`. **`CLOSED → OPEN` is removed** — v2 let a later lap
  reopen a closed round, which makes "closed" mean "closed for now" and cannot
  be pinned against. **`RECEIVED` is claimable only by the recipient.**
- **§4b `WITHDRAWN`.** A terminal state for ending without agreement, with a
  mandatory reason and a mandatory gate assertion that **no release names a
  withdrawn round** — without which it is a way to smuggle a release past the
  open-round rule.
- **§5a The round digest.** `HANDSHAKE-INBOUND-HELD` enumerates what the writer
  holds; `HANDSHAKE-ROUND-DIGEST` is a fixed-construction checksum over it.
  **A round may not close while the digests disagree**, and that rule alone is
  not overridable. This is the direct answer to thirteen laps of a one-sided
  conversation with both gates green throughout.
- **§6a-bis Convergence, R1–R7.** Close conditions fixed at lap 1; `CLOSE-BY` as
  an advisory ISO instant that is never extended; findings default to
  `NEXT-ROUND`; the pin does not move; questions carry targets and may be empty;
  **pre-commit mandatory from lap 5, naming an event rather than a lap number**;
  and a **lap ceiling of 21**.
- **§1a Who opens a round.** Normative for the first time: **the provider
  opens, every time** -- the repository that produces the artifact under review.
  Only the provider can mint the unit of work, because a round is a decision
  about a pin and you cannot open one against a commit that does not exist.
  With the general form (*whoever asks for a change goes first; whoever is asked
  to trust it goes last*), three bounded exceptions, and the multi-repo
  generalisation. Settled 2026-08-13 by asking both projects simultaneously; it
  had lived only in one project's private notes until now.
- **§8 Conformance rows C21-C33**, one per new rule, so "we implement v3" is a
  claim either side can check row by row rather than a paraphrase. **C13 was
  also corrected**: its old rationale said *"a round can reopen"*, which v3
  removes -- a conformance table contradicting the spec it belongs to is how two
  gates come to disagree while both believe they conform.
- **§6a-ter Overrides.** Any rule may be overridden by the operator, in writing,
  with rule id, who and why — honoured, printed loudly and permanently, and
  **an unrecorded override did not happen.**

A v2 gate reading a v3 file refuses, which is correct and is why the number
moved. **Both sides ship v3 before the next close.**

### What v3 does not do

- It does not change filenames, directory layout, or either project's storage.
  §1 still holds: layout is local.
- It does not add a required *questions* section, a required lap cadence, or any
  rule whose effect is to generate work. Every v3 addition either makes a
  claim checkable or makes a round end.
- It does not make either gate depend on the other side's implementation. Both
  compute the digest from files they hold; neither reaches into the other's
  repository.


## 12. Changes in v4

**v4 is v3 plus two amendments Platterpus raised in round 9 lap 2, both of which
came from their implementation failing on its first run.** Nothing in v3 is
withdrawn.

- **§5a "What counts as one lap".** A file is one lap only if, after fences are
  stripped, it declares `HANDSHAKE-ROUND`, `HANDSHAKE-LAP` and `HANDSHAKE-FROM`
  **exactly once each**. Derived from §2 rule 3 rather than from a list of
  container formats, so it excludes the next container as well as the one that
  prompted it. **Their finding, their rule, adopted in substance.**
- **§5a "Self-reference".** The digest in lap N covers what the writer holds
  **excluding lap N**, and a verifier checks it **excluding that same lap N**.
  The first half is theirs; **the second half is cyanrip's amendment to it** —
  their wording defined what the writer computes and left undetermined what the
  reader compares it against, and without that the two sides exclude different
  files and disagree permanently by construction.
- **§8 rows C34–C36**, one per new rule.

**Why v4 rather than an edit to v3.** v3 was adopted byte-identical by both
projects and its hash is quoted in a sent lap. Editing a version in place is the
drift this file exists to prevent, even when both sides agree on the edit —
the number is what makes "we hold the same spec" checkable.

**Neither gate implemented 3.** Both were still declaring 2 under the bootstrap
in round 9 lap 1 §0, so nothing is skipped by going straight to 4: implement 4,
declare 4, and the round's close condition 1 is met.

### Deferred to v5, not rejected

- **An `ACK` verdict** — receipt only, empty body legal, refused if it carries
  questions or findings. Platterpus's round 9 lap 2 §A1-c. It serves §6a-bis
  directly: §4's set has no way to say *"received, nothing to add"* except a
  `HOLD`, and a `HOLD` with content generates content in reply. **Accepted in
  principle, deferred because it widens the verdict vocabulary** — the one set
  both gates must agree on exactly — and that is worth its own round rather than
  riding along with two amendments already in flight.
