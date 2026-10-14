# Handshake protocol v9

**This file is the shared language. Both projects implement it; neither owns
it.** cyanrip and Platterpus each have a gate that reads round files and decides
whether a round is closed, and so which pair is approved. Those gates must agree
on every field name, every
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

   **A fence is what CommonMark calls one** (v8, E10). A line indented by at
   most three spaces and opening with three or more backticks, or three or more
   tildes, opens a block. The block closes only on a line indented by at most
   three spaces made of the same character, at least as many of it, and
   nothing after them but spaces or tabs. A block left open runs to the end of
   the file. **Every reader of a lap follows it**: the gate, the round digest
   (§5a) and the lap-language checker, since two readers that toggle on
   different lines disagree about what a file declares and which laps it
   counts.
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
| `HANDSHAKE-PROTOCOL` | integer | this spec's version. A gate that reads a **higher** number than it implements must refuse the round rather than guess — **in any file of the round, its own or the peer's, not only the newest** (v6, C43). |
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

### `HANDSHAKE-NEXT-LAP` — where the round is going (v7, D7)

Required on every lap of a file declaring 7:

```
HANDSHAKE-NEXT-LAP: <n> (ours|yours): <what it carries>; <what closes on it, or none>
HANDSHAKE-NEXT-LAP: none — <why no lap follows>
```

`(ours)` and `(yours)` are from the writer's side. The reader learns from the
header what the round expects next and why, without reading the body. `none` is
for a lap after which none is expected, such as the closing lap of a round.

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
| `HANDSHAKE-FROM-COMMIT` | short SHA | **required from round 9. Amended in v6 (§3b).** A commit **reachable from the branch on which the sender publishes its laps**, at which every `file:line` and every measurement in the lap resolves — *not* `HANDSHAKE-PIN`, which is the commit under review. They are equal only by coincidence. |
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

## 3b. What a citation names (v6)

**A citation is an anchor and a hint, and they do different jobs.** v3 made every
lap name `HANDSHAKE-FROM-COMMIT` and defined it as *"the commit of the sending
tree at the moment the lap was written"*. The two projects then read that two
ways: cyanrip as the parent of the commit that releases the lap, Platterpus as
the newest commit on the branch it publishes. Both are defensible, and every test
on both sides passed. Meanwhile one lap's evidence sat on a session branch at a
third commit.

- **The anchor is content.** A file the other side is asked to rely on — a lap, a
  standing status, a rig artifact, a shared document — is cited by the **sha256
  of its exact bytes**, with its byte count. A content hash cannot be pruned.
- **The hint is a commit.** Name a commit at which the file can be fetched,
  beside the hash. A commit is a location. On a repository that squash-merges
  and deletes merged branches, a commit that is not an ancestor of the published
  branch is destroyed by routine `git gc`, and every citation of it stops
  resolving. cyanrip's round 23 lap 3 cites Platterpus's `b5af9bec`, which is the
  worked example: that branch is kept only because the citation needs it.
- **Only a sent lap has a hash worth quoting** (§5a).
- **`HANDSHAKE-FROM-COMMIT` is defined by what it must do**: a commit reachable
  from the branch on which the sender publishes its laps, at which the lap's
  `file:line` citations and measurements resolve. Either project's current choice
  satisfies it whenever the cited evidence is on that branch. Evidence that is
  only on an unpublished branch satisfies neither, and is cited by content hash
  instead. `HANDSHAKE-FROM-COMMIT-SOURCE`, optional, says how the sender chose it.
- **An evidence citation is exempt from `HANDSHAKE-FROM-COMMIT`** (v9, HR-2 6a).
  From a side's move of its run evidence to its `evidence` branch, a lap cites
  a file there as `<repo>@<evidence commit>:<path>` with its SHA-256, and the
  citation resolves at the commit it names, which must be reachable from that
  repository's `refs/heads/evidence` (§17).

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

**A lap is sent when it is released, and its number is claimed then (v6, K1).**
A lap is `SENT` when its operator releases it for reading —
`HANDSHAKE-READY-TO-READ: yes` (§5c) — not when it is committed. Committed and
pushed but not released is still `DRAFT`: it may be revised, so a mistake found
after `git push` has somewhere to go. **The lap number is claimed at the same
moment.** Each side allocates the next number from its own tree and neither gate
can see the other's held laps, so two laps drafted at once can carry the same
number; round 21 produced two lap 4s, one per project. The number belongs to
whichever is released first, and a held lap whose number has been taken is
renumbered before it is released. Two *released* laps declaring the same number
are still ambiguous (§2 rule 3), and ambiguity is not a close.

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
round.** A withdrawn round approved nothing, so a release that cites one as its
approval claims an approval that never happened. Until v8 the assertion also
kept `WITHDRAWN` from smuggling a release past the rule that refused one while a
round was open; v8 retires that rule (§6b), and the assertion stays for the
first reason. It is not optional and is the reason `WITHDRAWN` did not exist
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
| `HANDSHAKE-TESTED` | **no approval without testing.** A round that closed with nothing tested approves a pair nobody checked. Name what ran and on which pair of builds. |

Any one missing → **the round stays open**, and the gate must say *which* field is
absent rather than refusing without a reason.

### The peer verdict is transcribed, not judged

Write down what they declared. If they said `HOLD`, record `HOLD` — do not
translate an encouraging paragraph into a `GO`. If their file is ambiguous, that
is a lap, not a close.

## 5b. Where the peer verdict may be resolved from (v5; step 1 amended in v6)

**§5's required list is unchanged. What v5 changes is where
`HANDSHAKE-PEER-VERDICT` may be RESOLVED from when a gate decides a close.**

Under v4 that field is a transcription and nothing else, so a round can only
close in a lap written *after* the peer's verdict existed. **The side that speaks
first therefore cannot close a round both sides agree is finished**: its newest
lap was written before the answer it is required to name. This is not a rare
case — it is guaranteed whenever the two sides alternate, and it costs exactly
one lap per round. Both projects have paid it, in both directions: Platterpus in
round 17, cyanrip in round 22, whose lap 3 declared `OPEN` because that was the
only honest value when it was written and whose lap 5 existed solely to carry a
transcription.

**`HANDSHAKE-PEER-VERDICT` remains required and remains a declaration.** v5 adds
one field beside it:

```
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-PEER-VERDICT-SOURCE: <the peer lap this was transcribed from, and the commit it was read at>
```

**The field name is Platterpus's.** They introduced `-SOURCE` suffixes
unilaterally in round 23 lap 2 — on the peer verdict, the peer pin, their own
verdict and `FROM-COMMIT` — before this clause existed, because a declaration
whose origin is unstated cannot be checked against anything. It is adopted here
verbatim rather than renamed.

**The rule.** A gate resolving a close MUST:

1. **Identify the candidate lap**: the newest peer lap **filed in the gate's own
   record when it decides** — held, not merely fetchable. **It must declare
   `HANDSHAKE-READY-TO-READ: yes` (§5c); if it does not, the round does not close
   (C38).** An older released lap is never used in place of a newer one that is
   not released. **Amended in v6.** v5 also required the
   lap to be enumerated in the closing file's own `HANDSHAKE-INBOUND-HELD`. The
   lap that makes step 3 useful is always written *after* the closing file, so
   under that reading step 3 could not fire on any real record, and cyanrip's one
   test showing it close used a fixture in which a lap declared that it held a lap
   not yet written. The closing file's `HANDSHAKE-INBOUND-HELD` still says what its
   writer held; the source the gate prints (C42) says what the close rested on.
2. **If that lap is the one `HANDSHAKE-PEER-VERDICT-SOURCE` names**, cross-check
   the declared value against the lap's own `HANDSHAKE-VERDICT` and **refuse on
   any mismatch**, naming both values and both files. A transcription that
   disagrees with its source is worse than either alone, because each side can
   cite one of them and both are in the record.
3. **If that lap is NEWER than the one the source field names**, the peer lap's
   own declaration is authoritative and the close MAY proceed on it. The gate
   MUST print both — the superseded transcription and the lap that superseded it
   — because a close that silently rests on a value no file in the closing side's
   own tree states is precisely the failure §5 exists to prevent. **This step is
   the whole of v5's saving**; steps 1, 2 and 4 are what make it safe.
4. **If it holds no such lap**, the round does not close, and the gate MUST say
   which condition in step 1 failed.

**What this does not do.** It does not let a gate infer a verdict from prose,
from silence, or from tone. *Transcribed, not judged* is unchanged and now
governs the peer file exactly as it governed the transcription: one declared
field, read out of one named file, matched at column 0 under §2.

## 5c. A lap read for its verdict must be released for reading (v5)

**This clause is Platterpus's, adopted whole, and it is what makes §5b safe
rather than dangerous.**

A lap may be **published** — committed, fetchable, countable by every conforming
enumerator — long before its operator has released it. Both repositories are
public. So §5b makes it mechanically possible to read a verdict out of a lap the
other side has not yet sent, and **acting on one would make the writer's draft
into the reader's decision.**

**The rule, and it fails closed.** A lap resolved under §5b MUST declare
`HANDSHAKE-READY-TO-READ: yes`. A lap declaring `no`, or not declaring the field
at all, is **not a readable verdict**. A gate that cannot establish the value
treats it as `no`.

**And it must name what it is holding.** A gate refusing under this clause MUST
print the lap file and the value it read. Refusing silently is indistinguishable
from finding nothing, and *"their lap 4 is held"* and *"we hold no lap 4"* are
different facts with different remedies — the `none` versus `unknown (reason)`
distinction, inside the rule that decides whether a round closes.

**Why it is load-bearing rather than a courtesy.** Before v5,
`HANDSHAKE-READY-TO-READ` was each gate's own property: the verdict came from a
transcription, and a transcription can only be written by someone who was told.
Under §5b it becomes **the only thing standing between "we can see it" and "we
may act on it."** Platterpus made this point against cyanrip's own proposal,
which had not noticed that it promotes an existing safety net into the
load-bearing element.

## 5d. A warning about a held lap goes where its reader can open it (v6, K3)

**Before writing down any correction or warning, ask: can the person it is for
open the thing it is in?**

A published lap that is not yet released (§5c) cannot be read by the other side,
so anything written into it for them does not reach them. Round 21 lap 4 carried
*"the SHA you recorded is stale"* inside the one document its reader was blocked
from opening, and it arrived only because its writer noticed and told the
operator. **A warning that lives only inside an artifact its reader cannot open
is not a warning.**

When the answer is no, the warning goes in the writer's **standing status**: a
document each side keeps between laps, rewritten in place, which declares no
`HANDSHAKE-*` field and so is counted by no enumerator (§5a). It is the one
message about a lap that legitimately travels outside one, and it is narrow by
construction: it concerns a lap its reader cannot yet open.

*The rule is the question, not the destination, on purpose.* A rule phrased as a
destination gets followed when someone remembers the destination; a rule phrased
as a question gets asked at the moment the correction is written. (Platterpus's
drafting, round 22 lap 2 §0.1, adopted in cyanrip's lap 3.)

## 5e. The agreed-change ledger (v6)

**A round closes on agreement, and agreement is not delivery.** K1 and K3 were
agreed in round 22 and K2 in round 21, and round 23 agreed a qualifier on
cyanrip's `Handshake:` log line. Each round closed correctly, and none of the four
was built by the time the next round opened, because the building was left to
memory and memory does not survive a round boundary. So a closing lap carries a
ledger:

```
HANDSHAKE-AGREED-CHANGES: K1 landed at 1a2b3c4 (PROTOCOL.md v6); the Handshake: qualifier not landed, cyanrip's
HANDSHAKE-AGREED-CHANGES: none
```

- **Required on a file declaring protocol 6 or later and verdict `GO`** (C44).
  `none` is legal and is written out.
- It lists every change **this round agreed, and every change an earlier round's
  ledger carried as `not landed`**, each with **the commit that landed it, or
  `not landed` and whose it is**. An entry leaves the ledger when it lands or when
  both sides withdraw it in a lap.
- **It does not gate the close** (C45). A round may close with changes not landed;
  the ledger makes that visible and carries them forward.
- Each side writes its own. A difference between the two sides' ledgers is worth
  one line in the next lap, not a lap of its own.

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

**Sent laps here, held ones beside it (v6, K2).** `HANDSHAKE-INBOUND-HELD` lists
peer laps that are **released** (§5c), each with its declared verdict and the
sha256 and byte count of the copy held: a hash of a sent lap is a fact about that
lap. A peer lap the writer can see but that is **not yet released** goes in
`HANDSHAKE-INBOUND-OBSERVED` instead, naming the commit it was read at and **no
hash**:

```
HANDSHAKE-INBOUND-OBSERVED: round-21-lap-04.md (READY-TO-READ: no), read at platterpus@27a174dc
HANDSHAKE-INBOUND-OBSERVED: none
```

A held lap declares itself mutable, so its size and digest at one commit identify
that commit, not the lap: round 21's held lap 4 was quoted at 31,732 bytes and
was half again as large at the next tip. `none` is legal and is written out, as
for `-HELD`. **Required on every lap of a file declaring 8 or later, and both
gates check it** (v8, E11, C47): until v8 one gate required it from 6 and the
other never read it, a divergence no lap had separated.

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

**R3 — A finding is fixed within the round (v7, D4).** Every defect a round
finds that can be fixed without a drive, the other side's code, or the
operator's decision is fixed and landed before that side's closing lap, and it
ships in that side's next release (v8, E6). A lap lists only what could not be
fixed that way, each item with why and whose it is. **This replaces v3's
deferral half**, *"a finding defaults to `NEXT-ROUND`"*. **The other half
stays**: a fix never holds the verdict on the build that was tested, and
promoting a finding to blocking still requires naming **what it breaks in the
artifact under review**; *"it is a real defect"* is an argument for fixing it,
never on its own for holding a release. R9 is the operator's rule this extends:
*"let's fix as much as we can"*.

**R4 — Once agreed, the pin does not move for the rest of the round**, unless it
is found unsafe. Fixes land past the pin within the round (R3, S-14) and ship
in that side's next release (v8, E6); the next round reviews them. A pin that
moves whenever something is fixed guarantees the evidence is always about a
build nobody is reviewing.

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

**R8 — A round reviews a released pair (v8, the operator's rule; v6 made a
round end on releases).** *"Either app releases when its own suite is green, and
a round reviews a pair after both are out. Name the rules in the shared files
that change, so both sides edit the same text in the same round. Each side's pin
approval still decides which ripper build Platterpus installs by default, and
that is what keeps users safe in between."* The operator of both projects,
2026-10-07, after *"We should be able to release a new version and use it, for
either app, and test them, without so much paperwork that does so little."*
Until v8 a round's close authorised a release of both applications, provider
first; that is retired. So:

1. **A round's close approves the pair it reviewed, and authorises nothing
   else** (v8, E2). The consumer's approved pin moves only on a close, and only
   to the provider build of that pair. Each side releases whenever its own
   suite passes (§6b), whether a round is open or not, and announces the
   release in its status block the same day (§6c).

   **The build under review moves when the provider releases, not when a round
   opens** (v7, D2). The provider gives its release's version and commit in its
   release manifest, and in a lap or its status block (§6c). The consumer's
   release names that build as its build under review and the last build a
   closed round approved as its approved pin. **Round 20's order is the one
   exception, unchanged**: when the provider's release removes or rewords a
   string the consumer matches, the consumer's release that reads both wordings
   comes first.

   **A release's contract change is derived, never described** (v7, D9). The
   lap or status line that announces a release quotes the releasing side's
   derivation of it: for cyanrip, `tools/contract-delta.py --rows <previous
   release> <candidate>`; for Platterpus, the diff of its generated consumer
   contract between the two releases; and for the bundle's shape, which neither
   side generates yet, each member added or removed as read from the bundle's
   own manifest.
2. **Each side chooses its own channel** (v8, E3). A channel is the releasing
   side's statement of its own risk, and the consumer follows the provider's
   manifest on the channel its user chose. **Marking is allowed, and
   withholding is not.** If a release has to carry a mark, such as a
   pre-release flag, a note that the hardware run has not happened yet, or a
   consumer reporting the provider's new release as not yet approved, it
   carries the mark and says what the mark means.
3. **A round reviews a released pair, and the real test is its run** (v8,
   E4; v7, the operator's O1 and O4). Its lap 1, the provider's (§1a), names
   the newest release of each side. The operator runs the Full acceptance on
   that pair, before lap 1 or after, and the bundle it produces is committed,
   byte-identical, to both repositories. Each side's next lap reads it, lands
   every fix it can (R3), and accepts or does not; if both accept, the round
   closes, and a further lap happens only when one side must answer the other.
   **A release made during the round is the next round's to review**, and the
   round's pin does not move (R4).

   **A run tests only the newest pair** (v7, D3). The consumer's acceptance run
   refuses, in its first section, unless the installed provider build is its
   build under review, that build is the provider's newest release by the
   provider's manifest read at run time, and the app is the consumer's newest
   release; a pair it cannot establish as newest is refused. The provider's
   bundle reader reports, when it reads a bundle, whether the pair was the
   newest when the run began and whether a newer release was published before
   it ended. **A run on anything else is not evidence.**
4. **Hardware evidence is a round's test, not a close condition of its own.**
   The run is what `HANDSHAKE-TESTED` cites (§5); it is a close condition only
   when the round cannot be answered without a drive, and then its lap 1 says
   why.
5. **Opening a round before its run is routine** (v8, E4). v7's point 5 made
   it an override of point 3 with its expected cost in laps; v8 retires that,
   since a round may open whenever its pair exists.
6. **A reading that finds nothing to act on is a short lap** (v7, D5, §6d).
   Short only when nothing needs explaining: any finding, disagreement or
   answer that needs its reasoning carries it in full.

**R9 — Fix it, do not argue it (v6, the operator's rule).** *"Let's make these as
few rounds as needed, and let's fix as much as we can. I want to spend time on
physical CD rips. Not arguing over bugs and language."* The same instruction.
A finding goes to a commit, and the lap that reports it says what was fixed. A
disagreement about wording is settled in the next version of the text, by the
side whose text it is, and it is not argued across laps. A lap carries only
what the other side must act on or answer before the round can close. **The
rules about evidence are unchanged**: answer from the artifact, revert-prove
the fix, and keep `none` distinct from `unknown`. What R9 cuts is the
back-and-forth over those.

**An answer is not a settlement (v7, the operator's rule of 2026-09-30).**
*"just because you get a lap answer doesn't mean you can't push back and get
more reasoning or an explanation or another answer. This is the point of laps.
Not to use the least amount but the have full explainations before finishing a
round."* So what R9 cuts is choreography, meaning acknowledgements,
transcriptions, crossings and runs on a stale pair, and never explanation. When
an answer arrives without its reasoning, or with reasoning that does not hold
against the artifact, the next lap asks for it and says why the round needs
it. A lap that buys an explanation is the protocol working. **A round closes
when both sides can state why**, not when one side has stopped talking.

**R10 — Retired in v8 (E5).** v7's R10 let either side release outside the
cycle when a released build corrupted audio or could not rip. From v8 every
release is outside a round's cycle (R8 point 1), so a hotfix needs no rule of
its own. What R10 carried that still binds is in R8 point 1: the release is
announced in the releasing side's status block the same day, it never moves the
other side's approved pin, and **a provider release that removes or rewords a
line the consumer matches keeps round 20's order**, the consumer's release
that reads both wordings first. A hotfix is the release most likely to be
written quickly, which is when a reworded line is least likely to be checked
against what the consumer matches.

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
does not close a round and does not move `HANDSHAKE-PIN`. A gate must assert
that a file declaring only a test pin still refuses. From v8 a released build
can be a round's pin directly (§6b, R8 point 3), so a test pin is needed only
for a build nobody has released.

Both sides declare the same test pin, in writing, before the session. Logs it
produces say `NOT a released build`, which is correct and is the point — the
artifact records that it came from a build under review rather than an agreed
one. Those logs are what `HANDSHAKE-TESTED` then cites.

**Sequence:** agree the test pin → both install it → run the session → both file
the results → *then* the round can close on that evidence, moving
`HANDSHAKE-PIN` to what was tested.

### 6b. Releases, and what a channel claims (v8, E1)

**Either side may release, on any channel, whenever its whole suite passes on
the release commit from a clean checkout**, whether a round is open or not. Its
gate prints every open round first, so a release while one is open is never
quiet.

| | permitted with a round open? |
|---|---|
| **any release, any channel** | **yes**, when the releasing side's whole suite passes on the release commit from a clean checkout, after printing every open round |

**A release claims its own side's testing and nothing more.** Joint verification
is claimed by the consumer's approved pin, which moves only on a close (R8
point 1); that pin is what decides which provider build the consumer installs
by default, and what keeps its users safe while a round is open.

Until v8 the table had two rows: a stable release was refused while a round was
open, because a stable release claimed the pair was jointly verified, and a
pre-release or beta was permitted after printing the open rounds, since refusing
it would have guaranteed a round could never close. Proposed by Platterpus in
round 7 lap 7, adopted by cyanrip in lap 8, and retired in round 31 (E1), when a
channel stopped claiming joint verification. Both gates' `--prerelease` flag
stays, printing the open rounds first; from v8 the gate does the same without
it.

Proposed by cyanrip in round 7 lap 6. Carried as an **optional** field on
purpose: v2 gates ignore unknown fields, so it costs the other side nothing
before they implement it. **`HANDSHAKE-PROTOCOL` is deliberately not bumped for
this** — a bump would make every v2 gate refuse the file that proposes it, which
is the opposite of what a proposal needs. It becomes v3 only once both sides
implement it.

## 6c. The status block (v7, D6)

Each side's standing status opens with these declarations at column 0, and is
updated in the same commit as any change to what they state:

```
STATUS-ROUND: <round>, OPEN|CLOSED[, what it waits on]
STATUS-LAPS: newest sent <file> (ours), <file> (theirs); next <n> (<side>) carrying <what>; held <n> carrying <what>|none
STATUS-RELEASED: <version> at <commit>, <UTC date>[, hotfix: <why>]
STATUS-RELEASE-NEXT: <version>[ at <commit>], carrying <what>; pins <approved>, reviews <under review>
STATUS-RUN-NEXT: <provider build> with <consumer build>; waiting on <what>|ready
STATUS-OPEN: <id> <owner> <fixing at <commit or lap> | cannot, because …>
```

`STATUS-RELEASED` appears once, in this position, and names that side's newest
published release, marked `hotfix:` while the newest is one. In
`STATUS-RELEASE-NEXT`, **`pins <approved>` is the consumer's approved pin as the
consumer's tree declares it when the line is written** (v8, E8), not the
provider's stable commit: from v8 the two differ whenever the provider has
released past the last pair a round approved.
`STATUS-OPEN` repeats, once per open item, and each item is fixed under R3 or
says why it cannot be. **It is not a lap**: it declares no `HANDSHAKE-*`
header, and changing it needs no reply. Chiming in costs a commit to your own
status, or a line in your next lap. **Each side's own suite checks its own block
against its record, positionally**, so the convention has two implementations
and neither checks the other's.

## 6d. The short reading lap (v7, D5)

The lap a side writes when its reading of a run finds nothing to act on is the
wire headers and then:

```
LSL: <n>

## The run

S1 FACT read: The bundle is sha256 `<64 hex>`, <n> bytes, filed at `<dir>`.
  evidence: <side>@<sha>:<dir>/README.md:1
  holds: <the pair, provider then consumer>
S2 FACT read: The pair was the newest when the run began, and still was when it ended.
  evidence: <the bundle reader's report, or the acceptance run's own check>
  holds: <the pair>
S3 FACT read: <one surface read, and what it shows>        (one per surface)
  evidence: <the filed artifact, with its line>
  holds: <the pair>
S<n> NONE: No defect in <build> in the run.
  scope: <what was read>
  evidence: <where>
  examined: <n> <unit>, closed

## Fixed

S<n> DID: <each fix landed because of the run>              (none: omit the section)
  commit: <sha>

## Close conditions

S<n> TERM set: <condition>                                  (the opener's lap 1 only, one per condition)
  requires: <what meets it>
S<n> TERM met: <condition>                                  (every GO lap, one per condition met)
  term: <side>:R<round>.L1.S<n>
  evidence: <where>
S<n> TERM pending: <condition>                              (a condition only the other side can still meet)
  term: <side>:R<round>.L1.S<n>
  on: them
  remains: <what it still needs>

## Verdict

S<n> VERDICT: GO
  basis: S1 S2 …
```

**What makes a reading clean**: no `FINDING`, `ASK`, `CORRECT`, `AMEND` or
`REFUSE` is needed. The moment one is, the lap is an ordinary lap. **What it
keeps**: the bundle's hash, so both sides are reading the same bytes; the pair,
because a run on anything but the newest pair is not evidence (R8 point 3); one
`FACT` per surface with its evidence, so the reading can be checked rather than
trusted; a `NONE` naming its scope and its population, because a clean result
must say what it was clean over; the fixes as `DID`s, so R3 is visible; and the
close conditions, set in the opener's lap 1 (R1) and given a status in every
`GO`, met, or pending on the other side where only it can still meet one,
because a `GO` over no condition passes by finding nothing.
**What it drops**: `NOTE`s and prose sections. The template is a floor for a
clean reading, never a ceiling.

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

  **Whether the build is released is decided by the build alone** (v8, E7):
  `released build` when it declared itself released at build time (cyanrip's
  `-Ddeclare_released=true`) from a tree with no visible changes, and
  `NOT a released build` otherwise. The round state stays in the line as
  information, so a release cut while a round is open reads
  `round N lap M OPEN, verdict V -- released build`. Until v8 an open round
  made every build read `NOT a released build`, so every rip of a release cut
  inside a round carried it.
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
| C13a | a later lap after the round reached a **terminal** state (§4a), declaring a verdict **other than the one that made it terminal** | refuse the *file* as an illegal transition; the round stays in its terminal state. **A later lap declaring the same verdict is not a transition**: under §5b the second side's closing lap follows the close on the first side's gate. **v3 changed this**: under v2 it reopened the round. **Amended in v6**: v3–v5 said *of any verdict*, which refuses that closing lap |
| C14 | no round files at all | refuse; an empty record is not agreement |
| C15 | `HANDSHAKE-PROTOCOL` higher than implemented | refuse rather than guess |
| C16 | complete two-sided tested round | **allow** — a gate that can never say yes is a wall, not a gate |
| C17 | a file declaring `HANDSHAKE-TEST-PIN` and otherwise complete, but verdict `HOLD` | refuse; a test pin is not a release |
| C18 | `HANDSHAKE-TEST-PIN` present alongside a valid close | **allow**, and the test pin must not be mistaken for `HANDSHAKE-PIN` |
| C19 | a **stable** release requested with any round open | **v8**: **allow**, and print every open round first (§6b, E1); **v3 to v7**: refuse |
| C20 | a **pre-release** requested with a round open | **allow**, and print every open round first — a beta claims no joint verification, and refusing it guarantees the round can never close |

### Rows added in v3/v4 — required once both gates implement 4

A gate implementing protocol 2 must not be
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
| C27 | a release naming a round whose latest verdict is `WITHDRAWN` | refuse — a withdrawn round approved nothing, so a release cannot cite it (§4b); until v8 it also kept `WITHDRAWN` from smuggling a release past C19 |
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

### Rows added in v5 — required once both gates implement 5

A gate implementing 4 must not be failed for missing them;
a gate implementing 5 must have every one. Split by heading for the same reason
as the v3/v4 block: a deferral that needs a human to remember it is one that
rots.

| ID | case | expected |
|---|---|---|
| C37 | a close resolving the peer verdict under §5b from a lap the gate does **not hold in its own record** when it decides | refuse; §5b reads a lap the deciding side has filed, never one it can merely fetch. **Amended in v6**: v5 required the lap to be named in the closing file's `HANDSHAKE-INBOUND-HELD` (§5b step 1) |
| C38 | the §5b candidate lap's `HANDSHAKE-READY-TO-READ` is not `yes`, is absent, or cannot be established | refuse, **naming that lap and the value read** (§5c) |
| C39 | the §5b lap is the one `HANDSHAKE-PEER-VERDICT-SOURCE` names, and the two verdicts **disagree** | refuse, naming both values and both files |
| C40 | the §5b lap is **newer** than the one `HANDSHAKE-PEER-VERDICT-SOURCE` names | **allow**, resolved on the peer lap's own declaration, **and print both** |
| C41 | a file declaring `HANDSHAKE-PROTOCOL: 5` with `HANDSHAKE-PEER-VERDICT` or `HANDSHAKE-PEER-VERDICT-SOURCE` absent | refuse; §5b changes where the field is resolved from, not whether it is required |
| C42 | a gate declaring 5 that closes a round **without** printing which lap the peer verdict came from | refuse; under §5b the close rests on a file in the peer's tree, and a close whose source is invisible cannot be audited later |

### Rows added in v6 — required once both gates implement 6

A gate implementing 5 must not be failed for missing them; a gate implementing 6
must have every one.

| ID | case | expected |
|---|---|---|
| C43 | **any** file of the round — the gate's own or the peer's, not only the one its verdict is read from — declares a `HANDSHAKE-PROTOCOL` higher than the gate implements | refuse the round, naming the file; a newer lap may lean on a clause of the older one's version. **This row must hold on both gates before either side declares 6**: it is what makes a lap declaring 6 refused, rather than read, by a gate implementing 5 |
| C44 | a file declaring protocol 6 or later and verdict `GO`, with no `HANDSHAKE-AGREED-CHANGES` | refuse, naming the field (§5e) |
| C45 | `HANDSHAKE-AGREED-CHANGES: none`, or a ledger with `not landed` entries, on an otherwise complete close | **allow**; the ledger records delivery and does not gate the close |

### Rows added in v7 — required once both gates implement 7

A gate implementing 6 must not be failed for missing them; a gate implementing 7
must have every one.

| ID | case | expected |
|---|---|---|
| C46 | a file declaring protocol 7 or later with no `HANDSHAKE-NEXT-LAP`, or one that is neither `<n> (ours)` or `<n> (yours)` followed by `:`, nor `none` | refuse, naming the field (§3) |

### Rows added in v8 — required once both gates implement 8

A gate implementing 7 must not be failed for missing them; a gate implementing 8
must have every one.

| ID | case | expected |
|---|---|---|
| C47 | a file declaring protocol 8 or later with no `HANDSHAKE-INBOUND-OBSERVED` | refuse, naming the field (§5a, E11) |
| C48 | a field line inside a fence that CommonMark recognises and a backtick-only, column-0 reading does not: a tilde fence, a fence indented by one to three spaces, or a backtick block that a shorter backtick line does not close | not a declaration; the gate does not read it and the digest does not count it (§2 rule 2, E10) |
| C49 | a field line after a fence that is never closed | not a declaration: an unclosed block runs to the end of the file (§2 rule 2, E10) |

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

## 13. Changes in v5

**v5 is v4 plus the two clauses round 23 §0.1 named, and nothing else.** Nothing
in v4 is withdrawn.

- **§5b — where the peer verdict may be resolved from.** A gate may resolve it
  from the newest peer lap it holds and has enumerated, when that lap is newer
  than the one its own `HANDSHAKE-PEER-VERDICT-SOURCE` names. **cyanrip's
  clause**, from round 22 lap 5 §H1, which established that §5 as written cannot
  be satisfied by the side that speaks first.
- **§5c — such a lap must declare `HANDSHAKE-READY-TO-READ: yes`**, fail-closed,
  naming what is held. **Platterpus's clause**, adopted whole. It is the
  condition their operator attached to assenting to §5b, and it is correct: §5b
  promotes an existing safety net into the only thing separating *visible* from
  *actionable*.
- **`HANDSHAKE-PEER-VERDICT-SOURCE`**, required on a file declaring 5. **Their
  field**, invented in round 23 lap 2 before this clause was drafted.
- **§8 rows C37–C42.**

**Why v5 rather than an edit to v4.** Same reason v4 was not an edit to v3: v4
was adopted byte-identical by both projects and its hash is quoted in sent laps.
The number is what makes *"we hold the same spec"* checkable, and editing a
version in place is the drift this file exists to prevent — even when both sides
agree on the edit.

**What v5 does not do.** It does not widen the verdict vocabulary (§4 is
unchanged; `ACK` stays deferred). It does not let a gate read a lap it has not
enumerated, nor one whose operator has not released it, nor a verdict out of
prose. And it does not touch `HANDSHAKE-FROM-COMMIT`, whose two projects
currently read it two different ways — that is a real divergence, it is recorded
in round 23 lap 3 §D, and it is **not** in v5 because both sides assented to two
clauses and a spec that grows past its assent is the round-7 failure mode wearing
a protocol's clothes.

**Neither gate implements 5 until this file is byte-identical in both trees.**
That is the condition round 23 §0.1 closes on, and it is deliberately the
harder-to-fake half: a version number can be declared by one side alone; four
matching hashes cannot.

### Deferred to v6, not rejected

- **An `ACK` verdict** — receipt only, empty body legal, refused if it carries
  questions or findings. Platterpus's round 9 lap 2 §A1-c. It serves §6a-bis
  directly: §4's set has no way to say *"received, nothing to add"* except a
  `HOLD`, and a `HOLD` with content generates content in reply. **Accepted in
  principle, deferred because it widens the verdict vocabulary** — the one set
  both gates must agree on exactly — and that is worth its own round rather than
  riding along with two amendments already in flight. **Still deferred at v5,
  and for the same reason**: v5 carries exactly the two clauses round 23 §0.1
  named and both sides assented to, and nothing else.

## 14. Changes in v6

**v6 is v5 plus what round 24 agreed for it, four corrections the record showed
the spec needed, the operator's two rules of 2026-09-23, and nothing else.**
Nothing in v5 is withdrawn. cyanrip's round 24 lap 1 §D1 proposed the list and
Platterpus's round 24 lap 2 §E agreed it. The corrections and the operator's
rules were not on it, and are marked.

- **K1, K2 and K3**, agreed and never written into v5: K1 and K3 in round 22
  (cyanrip's lap 1 §0.1, Platterpus's lap 2 §0.1), K2 in round 21 (Platterpus's
  lap 4 §K). **K1**: a lap is sent when it is released, and its number is claimed
  then (§4a). **K2**: `HANDSHAKE-INBOUND-HELD` for sent laps and
  `HANDSHAKE-INBOUND-OBSERVED` for held ones (§5a). **K3**: a warning about a held
  lap goes where its reader can open it, phrased as the question (§5d); the
  question is Platterpus's drafting.
- **§5b step 1 and C37**: *held, and enumerated by the gate when it decides*.
  Platterpus's gate already read it that way; cyanrip's read the text cyanrip had
  drafted, under which step 3 cannot fire. Round 24 lap 1 §B3.
- **A correction, not on round 24's list: §5b step 1's release condition is a
  requirement on the candidate, not a filter.** v5 and the first v6 draft read
  *"the newest peer lap … that declares `HANDSHAKE-READY-TO-READ: yes`"*. Read as
  a filter, the candidate always declares `yes`, so C38 can never fire, and an
  older released lap stands in for a newer held one. Both gates already read it
  as the requirement: each takes its newest held peer lap and refuses if it is not
  released (`cyanrip@39dee09:tools/release-gate.py:678-686`,
  `platterpus@86f0547:scripts/handshake.py:2188-2197`). No row's expected outcome
  changes. Platterpus's round 25 lap 2.
- **§5e, the agreed-change ledger**, `HANDSHAKE-AGREED-CHANGES`, with C44 and
  C45. It exists because K1–K3 and round 23's `Handshake:` qualifier were agreed,
  closed on, and not built.
- **§3b, what a citation names**: the sha256 as the anchor and a commit as the
  hint, and `HANDSHAKE-FROM-COMMIT` defined by what it must do rather than by how
  each side chose it. cyanrip drafted it, as its round 23 lap 5 §E undertook.
- **§8's two *"not yet in force"* sentences deleted.** Both became false when both
  gates implemented 5, and a version-frozen file cannot correct a present-tense
  sentence later. The conditional headings already said it.
- **A correction, not on round 24's list: C43.** C15 applied to every file of
  the round. Platterpus's gate has done this since 2026-09-22
  (`refused_round_files`); cyanrip's inbound loader read no peer lap's version
  until `cc235a1`. It is the precondition for anyone declaring 6.
- **A correction, not on round 24's list: C13a amended.** Neither gate
  implemented it, and as written it refuses the second side's closing lap.
  Replaying cyanrip's record lap by lap finds six `GO` laps, in rounds 7, 8, 11,
  12 and 15, that follow the lap at which its gate first reads the round closed;
  C13a as written refuses all six. It now refuses a later lap only if that lap
  declares a different verdict.
- **A correction, not on round 24's list: `ACK` retired.** §13 deferred it to v6.
  Since round 14, when the operator told both projects to stop the back-and-forth,
  an acknowledgement has not been a lap: silence is acceptance, and only
  disagreement or a correction needs one. A verdict meaning *received, nothing to
  add* has nothing left to carry. §4's vocabulary is unchanged.
- **The operator's rules, not on round 24's list: R8 and R9** (§6a-bis). A
  round ends on a release of both applications, both usable, and the real test
  on the released pair opens the next round, with its bundle in both
  repositories. And findings are fixed, not argued. Given in cyanrip's round 25
  lap 2, in the operator's words. R8 point 1 as first drafted had the consumer's
  release pin the provider's new one, which a pin approved by a closed round
  cannot do; cyanrip's round 25 lap 3 corrected it.
- **§8 rows C43–C45.**

**Why v6 rather than an edit to v5.** v5 was adopted byte-identical by both
projects and its hash is quoted in sent laps. The number is what makes *"we hold
the same spec"* checkable.

**Declaring 6.** Neither side declares 6 until both have said, in a lap, that
their gate implements it. C43 is what makes a premature declaration fail closed on
the other gate rather than be read. **Neither gate implements 6 until this file is
byte-identical in both trees.**

### What v6 does not do

- It does not widen or narrow §4's vocabulary.
- It does not settle what refusing a C13a file does to a release. The row says the
  file is refused and the round stays closed, and says nothing about the release;
  neither gate has implemented it, so nothing has had to decide.
- It does not make the ledger a close condition. A round may close with changes
  not landed; the ledger makes that visible and carries each one forward.
- It does not make R8 a gate row. A release happens outside the lap record, so
  neither gate can see it. The closing laps name the releases, and the next
  round's lap 1 cites them.

### Deferred to v7, not rejected

*§15 says which of these v7 took.*

- **Definitions of the optional fields** both sides already carry and no shared
  document defines: `HANDSHAKE-NEXT-LAP`, `HANDSHAKE-VERDICT-SOURCE`,
  `HANDSHAKE-PEER-PIN-SOURCE`, `HANDSHAKE-PIN-POLICY`, `HANDSHAKE-BREAKING`, and
  `HANDSHAKE-SHARED-HASHES` with its `-SOURCE`. Unknown fields are ignored (§3),
  so their absence here breaks nothing.
- **Two rules agreed in round 15 and never written**: the `HOTFIX` carve-out by
  artifact class, and `HANDSHAKE-NEXT-LAP`'s crossing tiebreak (cyanrip's round 15
  lap 3 §5, Platterpus's lap 4 §D). K1 may make the tiebreak unnecessary. The
  carve-out reads Platterpus's class from the GitHub pre-release flag, and round
  24 found that flag marks nothing a user receives across Platterpus's 0.x line,
  whose updater offers every `v0.*` on the stable channel. It needs redrafting,
  not transcribing.
- **Release ordering**: whether a stable release may precede the round that
  reviews it. It is the operator's question before it is the spec's.
- **The evidence-transport proposal**,
  `PROTOCOL-v5-PROPOSAL-evidence-transport.md` §5b.1–§5b.8: adopt or retire.
- **`HANDSHAKE-CONCURRENT-WITH`** (round 7 laps 32–33), never built. K1 may
  subsume it.
- **A `SEAM-COMMANDS: audited @ N` close field**, and **a semantic-change marker**
  to pair with a definition of `HANDSHAKE-BREAKING`.
- **C13a's effect on a release**, above.

## 15. Changes in v7

**v7 is v6 plus what round 30 agreed, and nothing else.** Nothing in v6 is
withdrawn except v3's deferral half of R3. cyanrip's round 30 lap 1 proposed the
decisions (`PROPOSAL-release-cycle.md`, D1–D10), Platterpus's lap 4 answered
each by number, and the operator ruled on O1–O4 (relayed in Platterpus's lap 4
S46, in the operator's words *"o1, A. o2, i agree, yes. o3, beta. o4, every
night a new paid [pair] exists"*).

- **R3, fix within the round** (D4, accepted in Platterpus's lap 4 S21). The
  deferral half of v3's R3 is replaced; its other half stays.
- **R8 points 1–6**: the build under review moves when the provider releases
  (D2, S19); a release's contract change is derived (D9, S26); the provider's
  new release goes to beta until its run passes (O3); the run happens every
  night a new pair exists, and the round opens from its bundle (D1 option A,
  S18, and O1, O4); a run tests only the newest pair (D3, S20); opening before
  the run is not routine (D8, O2); a clean reading is a short lap (D5, S22).
- **R9, an answer is not a settlement**: the operator's rule of 2026-09-30,
  not on the proposal's list, and added to R9 because R9's own words, *"not
  argued across laps"*, read as the opposite. It is in cyanrip's `CLAUDE.md`
  and the proposal's §1 in the same words.
- **R10, a hotfix outside the cycle** (D10, as Platterpus's lap 4 S27 amended
  it, with cyanrip's half of *"the releasing side's own gate"* named).
- **§3, `HANDSHAKE-NEXT-LAP`** (D7, S24), taken from v6's deferred list, with
  C46.
- **§6c, the status block** (D6, S23), and **§6d, the short reading lap** (D5,
  converged from both sides' drafts: Platterpus's
  `docs/cyanrip-handshake.md` §7.5d with the pair `FACT` and the `NONE` cyanrip
  added).
- **Amended before landing** by Platterpus's lap 6 S19 to S22: §6d's close
  conditions, R4's fixes with S-15's, and §6c's `STATUS-RELEASED` with R8
  point 1's manifest; S19 and S22 as cyanrip's lap 7 amended them.

**Declaring 7.** Neither side declares 7 until both have said, in a lap, that
their gate implements it. C43 makes a premature declaration fail closed on the
other gate. **Neither gate implements 7 until this file is byte-identical in
both trees.** Round 30's laps declare 6, and it closes under v6; v7 governs from
round 31.

### What v7 does not do

- It does not make R8, R10, §6c or §6d gate rows. A release, a run and a status
  block all happen outside the lap record; each side's own suite checks its own
  status block.
- It does not settle a hotfix while the other side's round is open beyond what
  R10 says: each side's own gate is the whole of the rule.
- It does not change §4's vocabulary, §5's close, or any v6 row.

### Deferred to v8, not rejected

Everything on v6's deferred-to-v7 list that v7 did not take: the definitions of
`HANDSHAKE-VERDICT-SOURCE`, `HANDSHAKE-PEER-PIN-SOURCE`, `HANDSHAKE-PIN-POLICY`,
`HANDSHAKE-BREAKING` and `HANDSHAKE-SHARED-HASHES`; `HANDSHAKE-NEXT-LAP`'s
crossing tiebreak; the evidence-transport proposal; `HANDSHAKE-CONCURRENT-WITH`;
the `SEAM-COMMANDS` close field and the semantic-change marker; and C13a's
effect on a release. The `HOTFIX` carve-out by artifact class is superseded by
R10, which names each side's gate rather than an artifact class.

## 16. Changes in v8

**v8 is v7 plus what round 31 agreed, and nothing else.** cyanrip's round 31
lap 1 proposed E1 to E9 on the operator's word of 2026-10-07 and took
Platterpus's round 30 lap 14 S6 and S22 as E11 and E10; Platterpus's round 31
lap 2 accepted each by number (S5 to S13, S22, S23).

- **E1, §6b**: either side releases on any channel whenever its whole suite
  passes on the release commit from a clean checkout, and its gate prints the
  open rounds first. C19 is amended to allow it.
- **E2, R8 point 1**: a close approves the pair it reviewed and authorises
  nothing else; the consumer's approved pin moves only on a close. §4b's
  withdrawal guard, §5's `HANDSHAKE-TESTED` row and C27's reason are reworded
  to match.
- **E3, R8 point 2**: each side chooses its own channel.
- **E4, R8 points 3 to 5**: a round reviews a released pair, its lap 1 names
  the newest release of each side, and the run is its test before lap 1 or
  after; opening before the run is routine.
- **E5, R10**: retired; what it carried is in R8 point 1.
- **E6, R3 and R4**, with `seam-rules.md` v8's S-14 and S-15: a fix ships in
  that side's next release.
- **E7, §7**: `released build` is decided by the build alone.
- **E8, §6c**: `pins <approved>` is the consumer's approved pin as the
  consumer's tree declares it.
- **E9**: each side's own gate and release workflow stop refusing a release
  while a round is open. Not text here; named so both land in the same round.
- **E10, §2 rule 2**: a fence is what CommonMark calls one, for every reader of
  a lap, with C48 and C49.
- **E11, §5a**: `HANDSHAKE-INBOUND-OBSERVED` is required from 8, with C47.

**Declaring 8.** Neither side declares 8 until both have said, in a lap, that
their gate implements it. C43 makes a premature declaration fail closed on the
other gate. **Neither gate implements 8 until this file is byte-identical in
both trees.** Round 31's laps declare 7, and it closes under v7; v8 governs from
round 32.

### What v8 does not do

- It does not change §4's vocabulary, §5's close, or any row but C19 and C27's
  reason.
- It does not make a release depend on a round, in either direction: a round
  can no more hold a release than authorise one.
- It does not take anything from v7's deferred list, which stands as written
  there.

## 17. Changes in v9

**v9 is v8 plus HR-2 and its clarifications HR-2.1, and nothing else.** The
operator gave both sides HR-2's agreed text on 2026-10-14, built from both
sides' reviews, as round 33's first task, and HR-2.1 later the same day. HR-2
moves run evidence off each default branch onto an `evidence` branch, and says
how laps cite it, how checkers resolve it and how CI fetches it. Both texts
follow, word for word, and are normative; the rest of this file is unchanged
except §3b's last bullet, which points here.

```text
HR-2 (protocol v9, with the lap-statement language amended to match)

1. Evidence is what a run, a rig session or the other side produced that nothing on the default
   branch reads: no build, test, tool, checker, CI step or SETTLED check. It includes application
   logs, report JSON, rip logs, cues, captures, screenshots, transcripts, diagnostics records,
   and the copies a lap cites of them. These stay on the default branch: laps; the other side's
   standing statuses; the shared seam files and any specification a lap checker implements
   (such as lsl-amendments-1.md); the release ledger, the manifest and the release-suite records
   (docs/release-evidence/); provider contracts, golden references and sample diagnostics; each
   run folder's README, as its index; and every fixture.
2. Readers. Before the move, each side runs its whole suite and every check in a scratch clone
   with the moving files absent. Every moving file that anything opens is copied byte for byte
   to a fixture path, or replaced by a slim extract that names its source's path and SHA-256,
   and its reader is pointed there. From the move on, a check refuses any new test, tool or
   check that opens an evidence path. A test that passes on nothing when its input is missing
   is a defect, fixed on sight.
3. Each repository keeps an orphan branch named `evidence`. Each commit after the first has the
   previous tip as its only parent and adds files without changing or removing any. It is never
   merged, rebased, force-pushed, deleted or tagged, and a ruleset blocks deletion and
   non-fast-forward updates.
4. The default branch keeps docs/evidence-manifest.tsv, append-only: UTF-8, tab-separated, one
   header line `path	bytes	sha256	evidence_commit	last_default_commit`, sorted by path, one row
   per file. evidence_commit is the full 40-character commit that added the file;
   last_default_commit is the last default-branch commit that held it, empty if it was filed
   straight to evidence. A path containing a tab or a newline isn't filed.
5. The move.
   a. It moves whole run folders, byte for byte, at their current paths. A folder's README is on
      both branches: evidence holds the whole folder, and the default branch keeps the README.
      No file is changed in the move. Files already committed keep their bytes, because laps
      cite them by hash.
   b. The commit is built from an enumerated list of folders, never a pattern (git ls-tree
      treats `docs/rig-*` literally, prints nothing and exits 0). It is built in a temporary
      clone made with `git clone --depth 1 --single-branch`, so the push sends only trees and
      one commit, never the files themselves.
   c. Its author and committer are `evidence <evidence@invalid>`, with both dates set to the
      instant round 33's lap 1 fixes, given in all six GIT_AUTHOR_* and GIT_COMMITTER_*
      variables. Either side can then rebuild the other's commit from its list and compare IDs.
   d. Before the push, its file count and bytes match the manifest rows. After it: for every
      moved folder, `git rev-parse <last default commit>:<folder>` equals
      `git rev-parse <evidence commit>:<folder>`; and every path the removal commit deletes has
      exactly one manifest row.
6. Citations.
   a. From the move on, a lap cites evidence as `<repo>@<evidence commit>:<path>` with its
      SHA-256. Such a citation is exempt from FROM-COMMIT (PROTOCOL §3b) and the lap-statement
      language's one-branch-per-side rule. It resolves at the commit it names, which must be
      reachable from that repository's refs/heads/evidence.
   b. Each lap checker treats evidence as a second ref of record, for evidence citations only.
      It refuses one with no manifest row at the lap's FROM-COMMIT. It fetches a missing commit
      by its hash into a temporary repository. It reports one it can't fetch as unchecked,
      except in CI's evidence job, which fails instead.
   c. Holding. "A cited document must be one our repository holds: committed on our default
      branch, or on our evidence branch with a manifest row giving its SHA-256." A copy of the
      other side's evidence goes on your own evidence branch, byte for byte.
   d. Old laps. A citation by commit made before the move still resolves, because history is
      kept. A bare path in an earlier lap resolves through the manifest and is checked by
      SHA-256. A link at a branch name stops resolving and isn't edited. LSL B1 re-runs a run:
      command with the cited evidence placed at its own paths in the FROM-COMMIT tree.
7. Fetching. A committed SessionStart hook adds `^refs/heads/evidence` to each remote's fetch
   refspec (git 2.29 or later), and the context file tells sessions to run the same lines where
   hooks don't run. It limits later fetches. It cannot change the clone a session makes before
   hooks run, so it shrinks the checkout, not the first download. A tool reads evidence by
   fetching into a temporary bare repository (`git init --bare <tmp>`, then
   `git -C <tmp> fetch --depth 1 <url> <commit>`), never into the working clone, because a
   --depth fetch makes a full clone shallow.
8. CI.
   a. Exactly one job fetches evidence. It checks every added manifest row against its file at
      its commit, fails if any tag points at or reaches an evidence commit, runs every check
      that reads evidence, and runs the secret scan over evidence.
   b. Other jobs fetch only what they read, by explicit refspec. A job that needs no history
      uses depth 1. A range-only job may use a blobless clone (`filter: blob:none`).
   c. Each fetch change is proved by one real run on a pull request and one on a push to the
      default branch.
9. New evidence. Before evidence is first committed, the side that produced it replaces home
   folders with ~ and the hostname with `host`, and leaves out the owner's real name, through
   its filing tool, counting each replacement in the bundle's manifest. A log that verifies its
   own bytes (a cyanrip log checked with -Y, an EAC log's checksum) is verified first, and the
   result and both hashes are recorded.
10. Filing, in this order:
    a. Build the evidence commit in a temporary depth-1 clone of evidence, with the previous
       tip as its parent, and push it.
    b. Open a pull request on the default branch adding the manifest rows. CI checks each row
       against the fetched commit, then it merges.
    c. Write the lap from a FROM-COMMIT that already has the rows, and publish it.
    6b's refusal of a citation with no manifest row is what enforces this order.
11. Laps never move.
12. Order and proof. Both sides first land this text and v9 checker support with nothing moved.
    Each side moves when its suite passes in a scratch clone with its move simulated. Either
    side may go first. After a move, the other side's checker verifies it with 5d's checks,
    fetching by hash. Then each side sends one lap citing one file on its own evidence branch,
    and the other side's checker must pass it with only the default branch and the cited commit
    fetched. Only after that do laps use the new form.
```

```text
HR-2.1 (clarifications, part of v9; added to PROTOCOL §17 after HR-2's text, word for word)
a. (5a) A file that must stay on the default branch but sits in a folder that moves, such as a
   README or a specification like outbound/artifacts/lsl-amendments-1.md, is on both branches:
   evidence holds the whole folder, and the default branch keeps that file. Run files outside
   any folder stay on the default branch.
b. (4, 5d) last_default_commit is the default-branch commit the evidence commit was built from.
   The removal pull request's first commit has it as its parent. Before that pull request
   merges, CI checks that each moved folder's tree on the current default branch still equals
   its tree at the evidence commit. If it doesn't, a file changed after the build, and the
   removal waits until that's resolved.
c. (7) The temporary repository's fetch may add `--filter=blob:none`, so it downloads only the
   files it reads.
d. (8a) Where GitHub's secret scanning and push protection are both enabled for the repository,
   they are the secret scan over evidence. A side may also run its own scanner.
```

**Declaring 9.** As for 8: neither side declares 9 until both have said, in a
lap, that their gate implements it, and **neither gate implements 9 until this
file is byte-identical in both trees.** HR-2's own order is its point 12, and
its citation rules bind from each side's move.

### What v9 does not do

- It does not change §4's vocabulary, §5's close, or any conformance row.
- It does not move a lap (HR-2 point 11), and it edits no file already sent.
