# The cyanrip ⇄ Platterpus release handshake

> **The rule, in one line:** neither project ships until **both** have sent a handshake file and
> **both** have verified the other's. Two files, two verifications, every round. No exceptions,
> including "it's only a small change".

This is the canonical, single-homed description of that protocol. `CLAUDE.md` links here rather
than restating it; `tests/test_handshake_protocol.py` enforces that this file and its links stay
in place.

---

## 1. Why it is bidirectional

Platterpus reads cyanrip's log; cyanrip's log is shaped by what Platterpus needs. Neither side
can verify a change to that seam alone, and **each side has now been wrong about the other at
least once**:

| Who was wrong | What about | Caught by |
|---|---|---|
| Platterpus | Told the fork to indent the `-Z` `Done;` line, asserting it was stdout-only. It was not — at 0.9.3 *or* master. The fork implemented the ask faithfully and every verdict shifted by one track. | cyanrip, by reading `cyanrip_log()` |
| Platterpus | Flagged the fork's track-1 `Pregap length: 300` as a factor-of-two contradiction. It is lead-in (150) + declared TOC gap (150). Our *derivation* was the wrong one. | The fork's own package |
| Platterpus | "Corrected" that pre-gap table to **9 of 14, track 1 not among them**. That is a true count of `INDEX 00` lines in EAC's **cue** — where track 1 cannot appear — quoted as evidence about EAC's **log**, which prints a row for **10 of 14, track 1 included**. The original claim had been right. | Platterpus, by finally opening the committed baseline |
| cyanrip | §H2: EAC's `Pre-gap length` is the TOC component alone, so the fork's 300 is not EAC-comparable. Well-argued, and wrong — EAC's real log reads `Track 1 … 0:00:02.00`, the bare lead-in on a disc that declares no track-1 gap, so EAC's row *is* lead-in + declared gap. We had applied it before checking. | Platterpus, `tests/test_eac_pregap_convention.py` |
| cyanrip's FIXPLAN | Concluded a fork could not fix the buffering defect because SIGKILL is uncatchable. True of signal handlers, false of `setvbuf` — which removes the buffering so nothing is pending at kill time. | cyanrip, by measuring |

A one-directional report is a claim. **A handshake is a claim plus an independent check of it.**
Every row above is a case where the check, not the claim, was what found the truth.

## 2. The sequence

Fixed order. Steps 3 and 5 are the ones people skip; they are the entire point.

1. **Platterpus → cyanrip.** Findings, confirmations, corrections, questions, and an explicit
   request for the return file (§4).
2. **cyanrip acts** — fixes, confirms, pushes.
3. **cyanrip → Platterpus.** The return file (§4), answering every question and disclosing
   anything found in *Platterpus's* output.
4. **Platterpus verifies** every claim in it against the real parser and the committed fixtures.
   Not a read-through: run the golden log through `parse_cyanrip_log`, check the version string
   against the pin test, diff the log format.
5. **Platterpus → cyanrip: verification result.** A short confirmation that each claim checked
   out, or a list of what did not. **This is the second handshake and it is mandatory** — a
   silent "no news" leaves the fork unable to distinguish "verified" from "not looked at yet".
6. **Only now** does either side release, and only now does the container switch to the pin.

If step 4 finds a discrepancy, return to step 2. Do not ship "the rest of it" while one item is
outstanding — a partly-verified pin is an unverified pin.

## 3. What Platterpus sends (steps 1 and 5)

**Step 1 — the findings file.** Required sections:

- **Confirmations** — their claims we independently checked, with *how*.
- **Corrections** — anything we previously sent that turned out wrong, stated plainly and
  early. This section is not optional and "nothing to correct" must be written out.
- **What we fixed our side**, so they can drop it from their list.
- **Asks**, separated into *behaviour changes* and *questions*.
- **Explicitly not asking for** — so they do not spend effort on declined items.
- **The return-file spec** (§4), inline. Do not link to it; they may not have this repo.

**Step 5 — the verification file.** Short. For each claim in their return file: verified /
not verified / could not check, and the command or fixture that settled it. Plus a go / no-go
on the release.

## 4. What cyanrip sends (step 3)

One markdown file, these sections, in this order:

| § | Contents |
|---|---|
| **A** | Pin: repo, branch, **commit SHA**, exact `--version` output |
| **B** | Numbered answers to every question asked, each marked **measured** / **read from source** / **unverified**. "Unknown" is acceptable; a guess presented as fact is not. |
| **C** | Changes since the last round — one row per commit, flagging any that alter **log output text** |
| **D** | Log-format delta. **"No changes" must be stated explicitly**; silence is ambiguous. |
| **E** | A regenerated golden reference log, byte-exact, with the command that produced it — if D changed |
| **F** | Verification status, split: **proven** (with *how* — "tests pass" is not how) and **not proven** (with what it would take) |
| **G** | Revert-proof statement per behavioural fix: did you revert it and watch the test fail? A "no" is fine and useful. |
| **H** | **Anything found wrong in Platterpus's output** — logs, JSON, or the argv we pass. **"Nothing found" must be written out.** |
| **I** | Their **provider contract** — the mirror of our consumer contract (§7) |
| **J** | Their open questions back to us |

**§I was added in round 4**, which moved "questions back" from I to J. `scripts/handshake.py
--check` enforces this list, so a round arriving against the older A–I shape is reported rather
than silently accepted — that is the checker working, not the fork failing.

`python scripts/handshake.py --check <file>` runs this table against a received file and exits
non-zero listing what is absent. It also catches the two failures that are *worse* than a
missing section: a section present but empty, and D or H trailing off instead of stating the
null case. `--emit N` produces our outbound skeleton with every §3 section present, and it
builds the table above **from the same data the checker uses**, so we cannot ask for a section
we do not check or check one we never asked for.

## 5. The shared rigour bar

Both sides hold to these. They are not style preferences; each was paid for.

- **Revert-prove every fix.** Actually revert it and watch the test fail. Use a cold bytecode
  cache. This has caught a vacuous test in Platterpus **three times**, once in the same session
  that wrote this file.
- **A rule nothing executes is not a rule** (`docs/testing.md` §5.m). Invariants stated only in
  comments or a README need something that runs.
- **No floor equal to the population it measures** (§5.t). `assert examined >= N` against an
  N-sized population always passes.
- **Bound every quantifier.** `\d{1,9}`, never `\d+`.
- **Distinguish "did not happen" from "happened and found nothing."** Three Platterpus bugs of
  exactly this shape: `Accurip: disabled` as "in DB, no match"; an all-zero CRC as a
  confidence-200 match; `Pregap LSN: unknown` as `none`.
- **Answer it from the artifact, not from your memory of the artifact** (§5.u). A remembered
  measurement has no provenance and silently drops its qualifier. Name *which file* a number
  came from: the pre-gap convention flipped twice in one day because a true count of EAC's
  **cue** was quoted as evidence about EAC's **log**, and both sides reasoned about what EAC
  does instead of reading what EAC wrote.
- **A correction from the other side gets the same scrutiny as a claim.** §H2 was well-argued,
  arrived as a correction, and was applied faster than any finding either side had made
  itself — which is exactly backwards. The handshake's value is the check, not the direction.
- **Say what is unverified, plainly.** A "needs the rig" list is worth more than a green suite
  that quietly excludes the hard cases.
- **Real hardware beats fixtures.** cyanrip's fixtures are libcdio disc images; PR #115's
  Q-subchannel path has never successfully executed on one, because images always fail into
  `unknown`. No synthetic fixture retires that risk.

## 6. Scope — when a handshake is required

| Change | Handshake? |
|---|---|
| Anything altering cyanrip's **log output text** | **Yes** — this is the parsed seam |
| A new cyanrip flag or argument semantics | **Yes** |
| Switching the container to a new fork pin | **Yes** |
| A Platterpus parser change reading fork-only fields | **Yes** |
| A Platterpus release while a fork pin is outstanding | **Yes** |
| Platterpus UI, packaging, docs with no parser impact | No |
| A cyanrip change to code that emits nothing we read | No |

When in doubt: handshake. The cost is a file; the cost of skipping it was a release-shifting
off-by-one verdict.

## 7. Each side states its half of the seam, and each side reads the other's

We are each other's dependency. Platterpus consumes cyanrip's log and argv surface; cyanrip's
log format exists to satisfy Platterpus. **Both halves are written down, both are machine-
derived where possible, and each side is expected to consume the other's.**

| Direction | Artifact | Who produces it | How |
|---|---|---|---|
| Platterpus → fork | **`docs/cyanrip-consumer-contract.md`** — every log line we parse, every line we knowingly ignore with its recorded reason, every flag we pass | us | **generated** by `scripts/emit_dependency_contract.py` from the parser's enumeration tables and a real call to the argv builder; `--check` fails on drift |
| fork → Platterpus | **The provider contract** (§4 I) — stable vs unstable log lines, the argv contract per flag, the exit-code inventory, the fatal-message inventory | the fork | generated if they can; hand-written P3/P4/P5 is still worth more than nothing |

Neither half is a handshake on its own. **A description *derived from* the behaviour cannot
describe behaviour we do not have** — which is exactly how we once told the fork a line was
stdout-only when it was not, and how the fork implemented that faithfully and shifted every
verdict by one track.

### 7.1 Full error capture, both sides, always surfaced

A standing requirement in both directions, not a per-round ask. Each side must:

- **Print a diagnosable line on every fatal path**, at column 0, to a stream the other captures
  (Platterpus merges stderr into stdout). *A non-zero exit with no output is the one failure
  that cannot be explained to a user.*
- **Capture everything the other told it**: exit code (tri-state — `null` for a child never
  reaped, never `0`), the exact argv as spawned, and the complete output. Where output must be
  bounded, keep **head and tail** with a counted elision marker — a tool's fatal message is the
  *last* thing it prints, so a head-only cap drops precisely the line that explains the failure,
  and **a silent truncation reads as completeness**.
- **Surface it to the user.** Capture is not enough: 21 of cyanrip's 45 fatal strings were
  captured by Platterpus and never shown, and from the user's side that is the same bug as
  never capturing them. When a dependency names the problem, the user sees the dependency's own
  sentence, not "Rip failed."
- **Flush before exiting.** An unflushed fatal line is a fatal line the other side never sees.
  This one compounds with block buffering, which is how a real cancelled rip lost verified
  tracks.

### 7.2 Which build produced the artifact

Two binaries can produce the log we archive — the Platterpus fork and upstream cyanrip — and
the version number cannot separate them, because the fork tracks upstream versions. So the fork
**must** carry the token `platterpus-fork` in its version banner's parenthetical, on
`--version` *and* on the first line of every rip's logfile, and Platterpus records the
classification tri-state: `fork` / `stock` / **`unknown`** for an absent or unrecognised tag.
Never the negative — an unrecognised tag is an absence of evidence, not evidence of a stock
binary.

### 7.3 A build tag names a commit, not the content that was built

`meson`'s `vcs_tag` fills the banner from `git rev-parse --short HEAD`, which reports **the
commit**. Build from a tree with uncommitted work — or from a build directory whose configure
is stale — and the banner names a *different tree*, silently and confidently.

Round 6 delivered two consecutive golden references whose banners were three commits behind
the pin they were labelled with, and both were provable from content: one carried a log line
absent from its own named commit's source; the other logged a paranoia read-chunk size
introduced two commits later. So, standing:

- **The producing side adds a `-dirty` marker when the tree is dirty.** `git describe --dirty`,
  or a suffix when `git status --porcelain` is non-empty. (Reinstated as an ask in round 6
  after both sides had filed it as "agreed, not asking".)
- **The consuming side derives provenance from content, not from the banner alone.** A
  *behavioural* fingerprint in the artifact is the counter to have ready — the read-chunk
  count settled which build produced a reference when its banner could not.
- **Classification keys on the fork *id*, never on the pinned sha.** A banner we did not
  produce cannot be required to match a specific commit; requiring it would report a genuine
  fork build as unrecognised. Requiring an exact sha is correct only where *we* control the
  build — our wizard's verify step does, because it detaches onto the pin in a tree it wipes.
- **Where a pin is a docs-only commit above the last source change, it is still the pin.** The
  pin decides the banner, and the banner is what identifies the release. Say so, rather than
  claiming it is "the last commit that changes the binary" when it is not.

### 7.4 Round bookkeeping: amendments, and asks that ride in a verification file

Two mechanical rules, both learned by the record failing to describe the correspondence.

**An amendment belongs to its round.** Round 6 was corrected within hours (`round-6b.md`,
withdrawing the pin `round-6.md` had asked for). Counting that as its own round would report
two open rounds where one was corrected — and would make sending a correction immediately
score *worse* in the record than folding it into the next round, which is the wrong incentive
to encode in tooling. `handshake.py` reads `round-<N><suffix>.md` as round *N*, and `--check`
accepts several files so the round validates as a set: sections may be satisfied by any file
in it, later files supersede earlier ones.

**When our asks ride inside a verification file, write that round's outbound record in the
same commit.** The protocol is two files per round; folding the next round's asks into the
previous round's verification is efficient and correct, but it desynchronises the file count
from the round number, so `--status` can never read the round CLOSED. Twice that looked like a
missing file rather than what it was. `docs/handshake/outbound/round-6.md` is the pattern: a
record file that says plainly it is a record, names where the content was actually delivered,
and points at the answers that prove receipt.

### 7.5 A verification declares a verdict, and the verdict is what closes the round

Every verification file from round 4 on opens with a bolded declaration at the start of a
line — **`**GO on <pin>`** or **`**HOLD on <pin>`** — and `--status` / `--release-gate` read
*that*, not the file's existence. Three rules follow, and all three are enforced by
`tests/test_handshake_tooling.py` rather than stated here only:

- **A HOLD is not a close.** A verification may deliberately be a *mid-round lap*: round 7's
  own §15 asked us to hold and expect more than one exchange, so our reply verified nine
  findings, fixed two of our defects, and explicitly did **not** move the pin. The gate keyed
  on the file existing, reported `round-7 … -> CLOSED`, and allowed a release — while the
  deviation policy forbids releasing or switching the pin with a round open. The same defect
  §7 already records twice: *a check satisfied by the wrong thing*.
- **No verdict fails closed.** A verification that never says which it is has not answered the
  only question the protocol asks of it, and "not yet" is the safe reading. Rounds 1–3 are the
  named exception — reconstructed retrospectively, long before the convention existed — and
  that exemption list may shrink, never grow, or "add the round to the exemption list" becomes
  a one-line way to close an open round.
- **The newest file's verdict wins, and a conflict reads as HOLD.** An amendment supersedes
  what it corrects in this direction too — a GO withdrawn the same evening (round 6b's shape,
  from the other side) must not keep a round closed. A file declaring both changed its mind
  mid-draft: a release wrongly blocked is a delay, a release wrongly allowed ships an
  unverified pin.

**And the prose about a verdict is not the verdict.** Round 7's second paragraph says *"not a
closing GO"*; a matcher scanning the whole text for "GO" reads that file as GO and closes the
round off a sentence saying the opposite. The declaration is anchored to a line start for
exactly that reason.

---

### 7.5a How WE write an S-18 pre-commit: name an artifact and an observable, never a judgement about one

S-18 (`seam-rules.md`) is the shared mechanism — *"our next lap is `GO` unless X"*
binds — and it is the only thing that reliably ends a round. **This section is not
that rule. It is the measured record of how *our* side kept writing X wrongly**,
twice in one round, for two different reasons:

| lap | the X we wrote | why it did not bind |
|---|---|---|
| r16 lap 10 | *"unless **you tell us** §B7's clause-2 evidence is not what clause 2 asks for"* | The trigger is **the other side's opinion**. That is a veto, not a condition — a round cannot converge on something one party can restate at will. They told us, and it voided. |
| r16 lap 12 | *"unless `round16-accept.py`, **at a commit carrying both `a0830e0`'s clause-1 split and §C1's `max`→`min`**, exits non-zero"* | The trigger names a **remedy**. They improved on `a0830e0` rather than carrying it, so the SHA they named (`5bbb5ae`) does not satisfy the literal wording. **A pre-commit that names a remedy expires the moment the remedy is improved** — and the better the peer, the sooner. |

**The fork's has been *"the checker at `<sha>` exits non-zero"* since round 16 lap
11 and has needed no repair.** The difference is not care; it is shape. Theirs
names an **artifact** (a program at a commit) and an **observable** (its exit
code). Ours twice named a *judgement about* one.

So, for every pre-commit we write:

* **X is a command with an exit code, or a file with a hash.** If reading X
  requires anybody's opinion — theirs or ours — it is not X.
* **Name the artifact by identity, not by property.** `at 5bbb5ae`, never *"at a
  commit carrying <fix>"*. If the artifact moves, take the new name as they give
  it and re-offer; that is one line in the next lap, where a property-based
  trigger is a silent non-binding nobody notices until the round will not close.
* **Say which side runs it and publishes it.** Round 16's condition (b) grades
  *our* reader, so we run it and publish the result either way, and its outcome
  needs no agreement from them. Splitting that out in advance is what stops a
  result becoming a negotiation.
* **A pre-commit that cannot bind is worse than none**, because both sides plan
  the close around it. Lap 14 exists solely to re-point ours; without it the
  round had one binding pre-commit where the protocol expects two.

---

### 7.5b Which side's gate can close a round — the property, derived rather than accepted

Round 17 closed on the fork's gate while ours held it `OPEN`, with **both sides
declaring `GO`**. Their §5 asked us to report a disagreement rather than work
around it, and the cause was ours: `close_blockers()` found nothing wrong with
their closing lap and one thing wrong with **our lap 2** — `peer verdict is
'OPEN', not GO`, which was the only honest value it could carry, because they had
not declared when it was written.

**The fork generalised this as *"a round can only close on the gate of whichever
side sent the last lap, and both implementations have that property"*, and filed
it in their `SETTLED.md`. The second clause is wrong about ours, and it is
checkable.** Derived over our whole record:

| round | last lap sent by | our newest own-side lap | their first `GO` | our gate |
|---|---|---|---|---|
| 9 | THEIRS (11) | 10 | lap 7 | CLOSED |
| 10 | THEIRS (5) | 4 | lap 3 | CLOSED |
| 13 | THEIRS (8) | 7 | lap 3 | CLOSED |
| 14 | THEIRS (19) | 18 | lap 16 | CLOSED |
| 16 | THEIRS (17) | 16 | lap 15 | CLOSED |
| 17 | THEIRS (3) | **2** | **lap 3** | **OPEN** |

Five rounds where they sent the last lap closed on our gate without trouble. Their
formulation predicts all five would have hung, so it is not describing the
mechanism.

**The actual property: our gate closes only if we hold an own-side lap numbered
AFTER the peer's first `GO`.** It is a fact about *turn order*, not about who
spoke last — we need a turn in which to transcribe their verdict. Every closed
round has one; round 17 is the first short enough that we did not, because their
first `GO` *was* the closing lap. Round 16 hid it by running to seventeen laps,
so their `GO` at lap 15 was transcribed by our lap 16 before their lap 17.

The remedy was a `verified/` file — our acceptance, numbered after their `GO` —
which is exactly what round 13 did in the same position. **Not a loosening:** the
gate fails closed deliberately, and four releases once went out while a
presence-only check reported every filed round `CLOSED`.

**Their half is genuine and we confirmed it where we could reach it.** Their
`stale_peer_verdict` exists at `tools/release-gate.py:350`, cross-checking a
declared peer verdict against the newest lap in their `inbound/` — a guard they
have because their gate made the mirror mistake in round 9 and closed a round we
were holding open. Ours has no equivalent, and that is a real asymmetry in their
favour rather than a design win for us.

**Why this is written down rather than let go.** A characterisation of *our* code,
in *their* settled-facts file, is a claim we can derive and therefore must — the
same duty that has us re-deriving their numbers. A wrong shared model is worse
than no shared model: under theirs, either side would mispredict every one of the
five rounds above.

### 7.5c A lap is not live because it is committed

**Operator directive, 2026-09-14:** *"a lap should not be seen as ready to read and
use until I am told to do so and let the other repo know. And it should confirm
that in the file as well."* Binds **both** repositories.

**It corrects a rule that was one day old.** When transport moved to git on
2026-09-13 this project wrote *"publishing IS sending."* That collapses two acts
which had been separate since round 1 — and the reason nobody noticed is the
interesting part: **under hand transport the operator *was* the transport.** A lap
they had not weighed simply never moved, so the separation was enforced
structurally and never had to be written down. Replace the structure and the rule
it was silently enforcing goes with it.

> Ask of any mechanism being replaced: **what was the old one doing that nobody
> wrote down?**

**The mechanism.** `HANDSHAKE-READY-TO-READ`, declared in the file:

| state | meaning |
|---|---|
| `no — not announced; do not read or act on this lap yet` | the default at `--emit`. A lap is born held. |
| `yes — released by the operator on <date>` | `handshake.py --announce <lap>` wrote it, **on the operator's word**. |
| *absent* | **not determined** — resolved against the round, never defaulted to yes. |

Four properties, each paid for by a failure already in this file's record:

* **Tri-state and fail-closed.** Absent is not consent (protocol §2 rule 4). The
  mirror of *an unrecognised build tag is never reported as unapproved*.
* **Grandfathered at round 19.** Every lap up to 18 was hand-carried, so delivery
  *was* the announcement. Without the boundary a correctness fix would have marked
  every historical lap held and reopened eighteen closed rounds —
  `tests/test_handshake_tooling.py` asserts against the real record that it did not.
* **Both directions.** We can now read their tree before their operator has
  released anything. A file we *can* fetch is not one we may act on, and closing a
  round on their draft would make their draft our decision. `--announce` refuses an
  inbound lap for the same reason.
* **Held is not silence.** `--status` names the lap it is holding rather than
  printing a bare `we-verified=NO`, because *"said nothing"* and *"said something we
  have not stood behind"* are different states and a gate that renders them
  identically sends the reader looking for a missing file.

**No protocol version bump**, and that is the shared spec's own provision: §3,
*"unknown fields are ignored by both parsers, so either side may add one without
breaking the other."* So it is emitted and enforced here and **proposed** to the
fork as normative — the same route `HANDSHAKE-TO` and `HANDSHAKE-FROM-REPO` took in
round 16. Until they adopt it we treat an absent field on a round ≥ 19 lap of
theirs as *not released*, which fails closed and could hold a round they consider
sent; the standing status names that cost to them explicitly rather than letting
them meet it as a surprise.

## 7.6 Standing status — one home, and it is not this file

**Not a round, and not a call for one.** Rounds are the *formal* channel and they
have a cost (S-13: close conditions are fixed at lap 1, and an open round blocks
both sides' releases). Between rounds the fork still needs to know where we are.

**That answer lives in
[`docs/handshake/outbound/platterpusstatus.md`](handshake/outbound/platterpusstatus.md),
and only there.** It is the file that goes over the wire, it is what
`docs/handshake/README.md` designates, and it is the mirror of the fork's own
`cyanripstatus*.md`. Rewritten in place, never appended to, undated in its
filename — a stale standing status is worse than none.

**And it is the CHANNEL for a fact that changes after a lap is fixed** (adopted
2026-09-18 from the fork's round-22 §1b, which was a finding against us). A lap is
a record of a moment and must never be edited to chase reality; the standing
status is a claim about *now*, rewritten in place, read between rounds and not
gated on either operator's release. That makes it the only document either side
holds that can carry a correction to a lap already fixed — so corrections go
there, under *Live corrections*, and not only into the lap they concern.

**The failure that earned this, and it is ours.** Round 21: we wrote *"the SHA you
recorded for this file is stale"* into lap 4 — **the one document the fork was
blocked from reading**, because it was held. It reached them only because we
happened to notice and route it through the operator by hand. **A warning that
lives only inside the artifact its reader cannot open is not a warning**, and had
we not noticed they would have discovered it as a failed filing. The fork's own
words on raising it: it *"has no home in either project's rules"*. It has one now.

Same shape as *a comment where a check belongs is not a fix*, applied to delivery
rather than to enforcement: the content was correct, complete and addressed to the
right reader, and the channel could not reach them.

**Why this section is a pointer and not the text.** It *was* the text, and so was
the status file: two documents both describing themselves as "the standing answer,
rewritten in place", both going stale independently. This one had drifted four
releases and two rounds behind (it still announced *"As of Platterpus v0.6.23"*,
round 12, and a pin of `ddf7ac3`) while the other announced 0.6.23 and round 13.
`CLAUDE.md` rule #7 names that exactly: **a second doc that duplicates a home is
worse than one long home**, because the reader now holds two maps with no way to
tell which is current. Collapsed 2026-08-27; the content was moved, not summarised
away.

## 7.7 Critical rule #12 in full — the standing seam rules, moved from `CLAUDE.md` (2026-09-26)

`CLAUDE.md` Critical rule #12 is the always-loaded statement of the seam. Until 2026-09-26 it carried every obligation below at full length, with its incident record inline. When `CLAUDE.md` was trimmed to its rules and pointers, each obligation kept its operative sentence there and its full text moved here, verbatim, because this file is the protocol's single home (its header says so, and `tests/test_handshake_protocol.py` holds `CLAUDE.md` to linking rather than restating it). Obligations whose substance already lived in §7.1–§7.3, §9 or `PLANNING.md` KDD-34 were not duplicated here; `CLAUDE.md` points at those directly.

### 7.7a The handshake is AFFIRMATIVE, BILATERAL, and checked at the drive

*Verbatim from `CLAUDE.md` at `f5305a7` (Critical rules, rule #12), moved here when that file was trimmed to its rules and pointers. Inside it, “here” and “this file” mean `CLAUDE.md`, and “above” / “below” mean the neighbouring entries of that section.*

**The handshake is AFFIRMATIVE, BILATERAL, and checked at the drive** (maintainer directive, 2026-08-04: *"Both of you should not make a new release until you are both happy with the handshake files, and proper testing is needed… This needs to be an affirmative handshake and include what versions you both are and what to use, and verify at the time of rip as well so we can confirm."*). Four obligations, each enforced by code rather than remembered: **(1)** a round closes only when **both** sides declare `GO` — one side's GO against the other's HOLD is an open round, and reading only our own verdict made their HOLD unable to block our release (one half of a two-half contract, for the third time in this protocol's life); **(2)** every handshake file from either side opens with the **shared wire header** at column 0, specified in **`docs/handshake-protocol.md` — the SAME FILE in both repos, which neither project owns** (a faithful restatement is still a second spec that can drift; editing it unilaterally is a version bump both sides must ship before the next close). Its §8 is a **conformance table, and it is run, not read** — `tests/test_handshake_conformance.py`, one test per row; running it found an empty record passing our own release gate, which four prose statements of the same principle had not. A declaration is what a file *states*, never what it *quotes*: fenced examples are stripped before matching, because a format's own documentation is the likeliest place to trip its parser; **(3)** **both** versions are named, ours and the ripper's, because a round approves a pin *for a named app version* and two artifacts from the same ripper under different app versions are not interchangeable evidence; **(4)** **every rip verifies its own ripper** against the approved build (`handshake_approval.py` → the report's `ripper_handshake_approval*` fields, added in schema **v15**; the live number is `rip_report.REPORT_SCHEMA_VERSION` — read it, do not quote it here), because a release gate runs once on a machine that never rips a disc and the rig is where an unapproved binary would actually be used. Tri-state as always: `not_determined` is not a pass, and an unrecognised build tag is never reported as unapproved.

### 7.7b Each round is two files and two verifications

*Verbatim from `CLAUDE.md` at `f5305a7` (Critical rules, rule #12), moved here when that file was trimmed to its rules and pointers. Inside it, “here” and “this file” mean `CLAUDE.md`, and “above” / “below” mean the neighbouring entries of that section.*

**Each round is two files and two verifications.** `scripts/handshake.py --emit N` builds our outbound skeleton with every required section; `--check <file>` validates a received one and exits non-zero listing what is absent, including the two failures worse than a missing section (present-but-empty, and a null case left silent); `--status` reports every round as OPEN or CLOSED off `docs/handshake/{outbound,inbound,verified}/`. **A round is OPEN until **both** verifications declare GO — ours *and* theirs. No release, no pin switch while one is open. (Stated as *"our verification file"* until 2026-08-27, which contradicted obligation **(1)** one line above and is exactly the one-half-of-a-two-half-contract failure that obligation exists to name.)** The verdict closes the round, not the file's existence: a verification may deliberately be a mid-round `**HOLD**` (round 7 was, at the fork's own request), and a gate that counts a HOLD as a close is not a gate. Every verification file from round 4 on opens with a bolded `**GO on <pin>`/`**HOLD on <pin>` line at a line start; a missing verdict fails closed. Committing the round files is how the record survives the session.

### 7.7c Both halves of the seam are checked, mechanically, every commit

*Verbatim from `CLAUDE.md` at `f5305a7` (Critical rules, rule #12), moved here when that file was trimmed to its rules and pointers. Inside it, “here” and “this file” mean `CLAUDE.md`, and “above” / “below” mean the neighbouring entries of that section.*

**Both halves of the seam are checked, mechanically, every commit.** The *output* half (their log lines vs our parser) had a standing test; the *input* half (their flag table vs our argv) did not, and that gap shipped a release blocker — every version probe sent `-V`, which cyanrip removed after 0.9.3, and a rejected version flag exits non-zero, which every probe here reads as *"the tool is not installed."* The app would have reported the ripper missing immediately after the wizard built it. Their published flag table had said so for a full round. `tests/test_argv_surface_agreement.py` now diffs every flag we send against the newest inbound round's table, and `tests/test_cyanrip_version_flag.py` pins the probe against each build shape.

### 7.7d State the range a contract claim covers, not the snapshot

*Verbatim from `CLAUDE.md` at `f5305a7` (Critical rules, rule #12), moved here when that file was trimmed to its rules and pointers. Inside it, “here” and “this file” mean `CLAUDE.md`, and “above” / “below” mean the neighbouring entries of that section.*

**State the range a contract claim covers, not the snapshot.** Their note *"`-v` is version; there is no `-V`"* was true when written and one commit from being the misleading kind of true. Same shape as our dependency dialog reading `cyanrip 0.9.3` / `0 missing`: every word accurate, the message wrong. A contract line should say *which builds* it holds for.

### 7.7e An upstream change cannot be escaped by rolling back to upstream

*Verbatim from `CLAUDE.md` at `f5305a7` (Critical rules, rule #12), moved here when that file was trimmed to its rules and pointers. Inside it, “here” and “this file” mean `CLAUDE.md`, and “above” / “below” mean the neighbouring entries of that section.*

**An upstream change cannot be escaped by rolling back to upstream.** The `-V` removal came from upstream, not the fork, so "revert to stock cyanrip" was never a mitigation — only pinning 0.9.3 or fixing the probe was. **Twice now, which makes it a pattern rather than a special case:** the `HH:MM:SS.mmm` → `MM:SS.FF` duration-shape change is also upstream's (PR #130), inherited by the fork, and rolling to stock does not restore the old shape either — we had it filed as a fork change until they corrected us in round 7. When planning a rollback, check whether the failure is *ours*, the fork's, or upstream's; the third kind has the fewest exits, and it is the kind whose origin is easiest to misattribute because the fork is the binary in front of you.

### 7.7f Both directions are sanitised and error-checked, at the boundary, by code

*Verbatim from `CLAUDE.md` at `f5305a7` (Critical rules, rule #12), moved here when that file was trimmed to its rules and pointers. Inside it, “here” and “this file” mean `CLAUDE.md`, and “above” / “below” mean the neighbouring entries of that section.*

**Both directions are sanitised and error-checked, at the boundary, by code.** The rules themselves live in **`docs/seam-rules.md` — one file, byte-identical in both repos, which neither project owns** (same mechanism as `docs/handshake-protocol.md`). Every rule there is tagged `[BOTH]` / `[PLATTERPUS]` / `[CYANRIP]` so each side knows what binds it *and* what the other has promised, and §4 tables **every value that crosses the seam with its type** — because a rule saying "validate the inputs" without naming which inputs and of what type is satisfied by whoever last read it. Summary: The seam has an *outbound* half (the argv we hand them) and an *inbound* half (the log and output we take back and show a user), and **each needs its own validator** — not one, and not a shared intention. Found 2026-08-06 by the maintainer asking the question in both directions on the same day, and both halves were holed:
- **Outbound.** Every rip argv the app builds passes `assert_metadata_lookup_disabled` — one chokepoint, which refuses an argv lacking `-N` and validates the `--consumer` tag. But a **straight-passthrough** path that skips the chokepoint is a hole in a rule the rest of the codebase enforces, and the new script verb was exactly that. Any new route to the ripper — a script verb, a debug console, a CLI flag — **re-establishes the guard by delegating to the chokepoint**, never by restating its rule; a second copy of a safety check is a second thing to drift, and a test asserts the refusal text is byte-identical. The failure this prevents is not a wrong result but a **hang**: without `-N` the ripper runs its own lookup and can block on an interactive prompt with no terminal attached.
- **Inbound.** Their output is **external input** and gets the same treatment: control characters and NULs flagged, absurd line lengths bounded (a multi-megabyte single line freezes the GUI thread rendering it), everything else verbatim, and **any elision counted and marked** — never a silent drop. And the rendering surface is pinned: Qt's default `Qt::AutoText` **auto-detects HTML**, so a captured line that merely looks like markup is *interpreted* rather than shown. The content is not the ripper's own — album and track titles come from MusicBrainz — so a title containing `<` is swallowed as an unknown tag and **the user never learns text went missing**. Every widget carrying dependency output is `PlainText`. **The sweep is `tests/test_message_boxes_are_plaintext.py`, and it covers `QMessageBox` only** — 6 sites, all pinned, with a ratcheted allowlist for literal-text boxes that is empty. Said precisely because this sentence used to read *"swept rather than fixed one at a time"* when **no sweep existed**: three of the six boxes had been fixed individually and three had not, including `_show_fatal_dialog`, whose `{exc}` is arbitrary external text in the one dialog a user screenshots to report a crash (found 2026-08-20 by an audit that went looking for the sweep this rule claimed). The 13 `QLabel(<non-literal>)` sites are **not** swept — most build their text from our own constants, so a blanket rule would need a long allowlist and a list of excuses enforces nothing; they are tracked in `TASKS.md`. Scoping a sweep is fine. Scoping it silently while the rule claims everything is the defect.
- **Nothing crosses the seam unchecked in either direction, and neither half is evidence for the other.** The input half had a contract test and the output half did not; that asymmetry is what let the `-V` blocker sit in a committed file for a full round. Both halves are checked mechanically, every commit.
- **A FIX WE FIND IN OURSELVES THAT COULD HELP THEM IS SENT, AND THE BAR IS
  *could in any possible way*, not *certainly does*** (maintainer directive,
  2026-09-13: *"make sure any fixes you find on yourself that could in any
  possible way help the other repo, you tell them"*). This is the missing
  direction of the seam. The protocol already carries a §H *"Found in our
  output"* for defects we find in **their** artifacts, and the challenge
  mandate has them auditing **us** — nothing obliged either side to report a
  defect found in its **own** code whose *shape* the peer might share.
  **The trigger is the shape, not the subject.** A truncation that drops the
  identifying end of a name, a gate satisfied by the document that documents
  it, a checker scoped to one artifact role and applied to all — none of
  those is about cyanrip, and each is a bug either project can hold. So the
  test is *"is the MECHANISM portable?"*, never *"is their code affected?"* —
  the second question requires reading their tree to answer, and under the
  rule above we will not assert a mechanism in their code anyway. **Report
  the shape with our citation and let them check their own side**; that costs
  us three sentences and costs them one grep.
  **Cheap to over-report and expensive to under-report, so err loudly.** A
  finding they already knew is a paragraph they skim. A finding withheld
  because it looked parochial is the class of defect this seam exists to
  catch, found twice and shared zero times.
  Vehicle: a NEXT-ROUND item in the current lap — not a new round, not a new
  file, and never a reason to hold a round open (S-14: a finding defaults to
  the next round).
  **Bilateral, and it travels.** Unlike the two carve-outs below, this is a
  term of the seam rather than a rule about our own operator: it is worth
  exactly as much in the other direction, and a one-sided version would read
  as us auditing them while keeping our own lessons.

- **The fork does the same, as a double check.** Two independent validators at one boundary are worth more than one careful one, because a value either side waves through still meets a guard. They validate what they receive from us and what they emit to us; we do the same. Neither side treats the other's checking as a reason to skip its own.

### 7.7g The fork has a standing CHALLENGE MANDATE, and it is asymmetric on purpose

*Verbatim from `CLAUDE.md` at `f5305a7` (Critical rules, rule #12), moved here when that file was trimmed to its rules and pointers. Inside it, “here” and “this file” mean `CLAUDE.md`, and “above” / “below” mean the neighbouring entries of that section.*

**The fork has a standing CHALLENGE MANDATE, and it is asymmetric on purpose** (maintainer, 2026-08-26). They were told they are *"the adult in the room"*: as the ripping engine, most of the accuracy and correctness burden is theirs, so they are to **double-check, fact-check, and call out or question** us. Three consequences, and the third is the one that is easy to skip:
- **Expect over-asking, and do not treat it as a process defect.** The maintainer said plainly to expect more questions than normal. A lap that asks four things we think are settled is the mandate working, not a convergence problem — do not answer it with S-16 or a complaint about lap count. Answer the questions.
- **It absolves us of nothing** — the maintainer said so in the same breath, and it is already the rule directly above: *neither side treats the other's checking as a reason to skip its own*. A second validator is worth having precisely because it is second, not because the first one can now relax. Every claim we make still carries its measurement.
- **Find out WHETHER they are more often right, by counting — then find out WHY, and adopt the mechanism rather than the conclusion.** The instruction was *"if they tend to be more correct than wrong, you should find out why and adopt the logic if possible, but let them try it out until you have measurable results either way."* So: **do not pre-judge it in either direction**, and do not decide it from the feel of the last lap. The ledger is `docs/cyanrip-handshake.md` → *Challenge ledger*, one row per substantive challenge with its outcome, cited to the lap that made it and the artifact that settled it. This is the same discipline as the round-7 lap count one bullet down — *counted, not felt*, and there the fork had the numbers first while we had them and had not looked. Adopting **the logic** matters more than the verdict: a peer who is right more often is running a better procedure, and the procedure is the transferable part.

### 7.7h A round must be able to end. Round 7 took 37 laps, 10 test pins and 8 pre-releases to produce 0 releases; rounds 5 and 6 took one lap each

*Verbatim from `CLAUDE.md` at `f5305a7` (Critical rules, rule #12), moved here when that file was trimmed to its rules and pointers. Inside it, “here” and “this file” mean `CLAUDE.md`, and “above” / “below” mean the neighbouring entries of that section.*

**A round must be able to end. Round 7 took 37 laps, 10 test pins and 8 pre-releases to produce 0 releases; rounds 5 and 6 took one lap each.** Counted, not felt — the fork tabled it and we had the same numbers and had not looked. *Nothing in round 7 was bad work*: it found a memory disclosure into an archival record, four segfaults, a gate that graded a crash as a clean refusal, a subsystem with no way to open it. **The round failed anyway, because it had no closing condition that could not be extended** — the properties that make the work good are exactly the ones that keep it open. Four mechanisms, each with a rule, all adopted from the fork's round-7 convergence proposal and binding on both sides:
- **S-13 — a round's close conditions are fixed in its lap 1 and cannot grow.** A criterion discovered later belongs to the *next* round, unless it is a regression in the pin under review. (Round 7 opened with three acceptance criteria; the fourth arrived at lap 31 — correct, and it moved the finish line 30 laps in.)
- **S-14 — a finding defaults to the next round.** Promoting one to blocking requires naming **what it breaks in the artifact under review**. *"It is a real defect"* is an argument for fixing it, never on its own for holding a release. Not one of round 7's findings made the reviewed pin unsafe; every one of them blocked it anyway, because nothing ever asked the question.
- **S-15 — an agreed test pin does not move for the rest of the round**, unless it is found unsafe. Fixes queue for the next one. Ten pins meant the hardware evidence was always about a build nobody was reviewing any more.
- **S-16 — questions carry a target, `BLOCKING` or `NEXT-ROUND`**, and `BLOCKING` must satisfy S-14. **A questions section may be empty**; "no questions" is a complete section and is written out. A spec that *requires* questions makes inventing work mandatory, and a round cannot converge faster than it invents work.
- **Pre-commit, and it is the one that actually ends rounds.** A lap may declare *"our next lap is GO unless X"*, naming X, and it binds. Both sides did this in round 7 laps 36–37.
- **The failure in one sentence: release-grade rigour was being applied to the *round* rather than to the *release*.** The rigour is right. Attaching it to a process that must terminate is what produced 37 laps and no release.

### 7.7i THE FORK IS THE CORE, AND MAKING SURE THEY PERFORM CORRECTLY IS OUR JOB — not a courtesy, and not discharged by their having checked it themselves

*Verbatim from `CLAUDE.md` at `f5305a7` (Critical rules, rule #12), moved here when that file was trimmed to its rules and pointers. Inside it, “here” and “this file” mean `CLAUDE.md`, and “above” / “below” mean the neighbouring entries of that section.*

**THE FORK IS THE CORE, AND MAKING SURE THEY PERFORM CORRECTLY IS OUR JOB —
not a courtesy, and not discharged by their having checked it themselves**
(maintainer directive, 2026-09-04: *"they do it, you double check their work,
even if they did, if you can"*). This is the mirror of the challenge mandate
above and the two are one arrangement, not two favours. Five obligations:
- **Their correctness is load-bearing in a way ours is not, so hold them to
  it.** `docs/OWNERSHIP.md` §1's RECOVERABILITY test already says why: get a
  fact wrong that needs the disc in the drive and the disc has to go back in;
  get one wrong that is derivable afterwards and it is fixed by re-reading
  files already on disk. They own the first kind. That is the reason to hold
  the ripping engine to the higher bar — **and the reason our own bar is
  barely lower, because everything they get right can still reach a user
  wrong through us.**
- **Verifying their emissions is a duty we have already signed, every lap.**
  `docs/OWNERSHIP.md` §3 assigns Platterpus *"The gate over incoming
  artifacts, and the systematic feedback duty"*, and the fork agreed to it.
  So this rule adds no imposition on them and needs no lap: it is us being
  told to actually do a job the shared file already gives us. **Their having
  verified something is not a reason to skip it** — that is the rule one
  bullet up, applied in the direction it is easier to forget.
- **Where their source is reachable, DERIVE the number; do not accept the
  lap's.** Their repository is public and can be cloned into the session
  (`add_repo` / `git clone`, 2026-09-04). On that day their lap 10 published a
  16-row table; instrumenting *their* generator over the 121 published rows
  reproduced it exactly — `total_error_count++` 8, `ret = N;` 6, `err = N` 1,
  combined 1 — and separately confirmed that `FAIL_PATH` really had seven
  alternatives while its preamble named five. **That is the standard now.** A
  claim we could have derived and merely repeated is a claim we asserted. And
  it cuts the other way too: the same session produced **three** different
  answers from correct code (19, 15, 16) before the population was closed
  correctly, so derive, then ask *"is the population I measured closed?"*
  before publishing the number.
- **NEVER put a defect on them that we started, or whose root is not theirs.**
  Establish the origin before attributing it — ours, theirs, or **upstream's**,
  the third being the kind this file already names as easiest to misattribute
  *"because the fork is the binary in front of you"*. A lap's framing is an
  attribution whether or not it uses the word: writing *"your P5 said it was
  fatal"* about a line we chose to grade as fatal is blame, however true the
  clause is. When both sides contributed, say which half is ours **first**.
- **The user sees us and never them, so a failure that reaches a user is ours
  to own in front of that user.** Not *"the ripper failed"* — the sentence a
  user reads names what went wrong and what to do, and the dependency's own
  text is shown as evidence, never as the culprit. This is not politeness: a
  user cannot act on an attribution, and blaming a component they have never
  heard of reads as an excuse. It is also, plainly, what will happen anyway —
  they will hold Platterpus responsible whether or not that is fair, and a
  rule that pretends otherwise costs us the chance to have already fixed it.
- **And our own standard does not drop because we are downstream.** A gate of
  ours that catches us is the system working: on 2026-09-04
  `tests/test_handshake_artifact_naming.py` refused a filing of mine — an
  artifact named `…-ga20d0a6.md` for a document carrying no build banner —
  **one lap after I wrote that very rule into lap 9 and the fork adopted it as
  v5's clause 5b.5.** Apply to our own work the scrutiny this rule demands we
  apply to theirs.
- **NOT bilateral, and it does not travel.** Same carve-out as the bullet
  below: it governs a duty of ours, not a term of the seam contract. Sending
  the fork a rule about how closely we intend to check them would impose
  nothing on them, restate a duty `OWNERSHIP.md` §3 already assigns us, and
  read as a demotion of a peer this project depends on. Do the checking; do
  not publish the intention.

### 7.7j LAPS TRAVEL BY GIT. Write the lap, commit it, push it, then tell the maintainer to point the peer at it

*Verbatim from `CLAUDE.md` at `f5305a7` (Critical rules, rule #12), moved here when that file was trimmed to its rules and pointers. Inside it, “here” and “this file” mean `CLAUDE.md`, and “above” / “below” mean the neighbouring entries of that section.*

**LAPS TRAVEL BY GIT. Write the lap, commit it, push it, then tell the
maintainer to point the peer at it** (maintainer directive, 2026-09-13:
*"no more laps i send manually, you make the doc and put into the repo,
then tell me to have the other repo take a look"*). This **supersedes** the
2026-09-04 rule that said to ask before writing a lap, and it supersedes it
by removing the reason rather than by overruling it: that rule existed
because *only the maintainer can perform the send*, so a written lap could
sit unsent indefinitely — and three did.
**BUT PUBLISHING IS NOT SENDING, AND THIS FILE SAID IT WAS FOR ONE DAY.**
Corrected 2026-09-14 on the maintainer's instruction: *"a lap should not be
seen as ready to read and use until I am told to do so and let the other repo
know. And it should confirm that in the file as well."* **Committing makes a
lap AVAILABLE; the operator's announcement makes it LIVE**, and the two are
separate acts — which is what *"publishing is sending"* collapsed. The error
is instructive rather than careless: under hand transport the operator **was**
the transport, so a lap nobody had weighed simply never moved, and the
separation was invisible because it was structural. Move the transport and the
structure stops enforcing it. Ask of any mechanism being replaced: *what was
the old one doing that nobody wrote down?*
**The file declares its own state**, so a peer never infers it from a commit
date: `HANDSHAKE-READY-TO-READ: no` at emit,
`handshake.py --announce <lap>` flips it to `yes` with the date and who
released it, and **`--announce` is run on the maintainer's word, never on our
own judgement.** Tri-state (`ready_to_read`), fail-closed, with a grandfather
at round 19 because every earlier lap was hand-carried and delivery *was* the
announcement. Our gate will not take a verdict from an unreleased lap **in
either direction** — theirs included, because we can now read their tree
before their operator has released anything, and acting on their draft would
make their draft our decision. It says *which* lap it is holding rather than
reporting a bare "no verdict"; **`--announce` refuses an inbound lap**, since
the peer's operator releases the peer's laps.
Permitted without a protocol bump by the shared spec's own §3 — *"unknown
fields are ignored by both parsers, so either side may add one without
breaking the other"* — so it is **emitted and enforced here, and proposed to
them as normative**, the same shape as `HANDSHAKE-TO`/`-FROM-REPO` in round 16.
**Both repos are public and either side can read the other. That premise was
wrong in both trees for the entire life of this protocol.** The fork found it
in themselves first — their `CLAUDE.md` asserted it twice and a round-18 lap
a third time — ran the check instead of repeating the claim, and told us;
ours said it too, in `docs/cyanrip-known-issues.md` and a session-log entry.
It is the class this file already names: **a note asserting an absence needs
a check that fails when the absence ends.** Same shape as *"there is no
`-V`"* and *"the suite has no network"*. This one is the most expensive of
the three, because it shaped the protocol: round 12 cost a whole round to a
mechanism we asserted in their build and could simply have read.
**`main` is the ref of record, and that is the new failure mode.** Work
happens on a `claude/…` branch and reaches `main` by squash merge, so a lap
can be committed, correct and invisible. Measured the day the rule changed:
`main` was **107 commits behind** and carried **none** of round 18's six
files. So the gate that used to be unable to see a send can now see one —
*is this lap on `main`?* is a question with an answer — and
`tests/test_no_lap_is_left_unsent.py` is where that answer belongs.
**What it does NOT license, and the fork said it first and better:** reading
their tree is not a substitute for a lap and not a licence to author their
half. *"The seam's value is two independent implementations catching each
other, and a convention re-derived from their source is one implementation
copied twice. Read to verify, never to decide for them."* And the citation
rule is unchanged — a mechanism claimed in their code carries
`cyanrip@<sha>:<path>:<line>` — it has merely gone from impossible to cheap.
**The half that stays with the maintainer is the NOTIFICATION**, which is why
the directive ends *"then tell me"*. A published lap nobody has been pointed
at is discoverable rather than lost, which is strictly better than the old
failure, but it is still not delivered. Say which commit it is on.

### 7.7k This rule lives in both repos

*Verbatim from `CLAUDE.md` at `f5305a7` (Critical rules, rule #12), moved here when that file was trimmed to its rules and pointers. Inside it, “here” and “this file” mean `CLAUDE.md`, and “above” / “below” mean the neighbouring entries of that section.*

**This rule lives in both repos.** When it changes here, send the change to the fork in the same round so their `CLAUDE.md` (or equivalent) matches. Two projects with different copies of the protocol is the failure this rule exists to prevent. **The bullet directly above USED to be the exception and no longer is** — when it was *"ask our maintainer before writing a lap"* it governed our operator and shipping it would have handed the fork a rule about a person they do not work with. Now that it is *"laps travel by git"* it is a **term of the seam**: it names where each side publishes and which ref the other reads, and a transport only one side has adopted is not a transport. It travels. (The two carve-outs that remain are the ones that still govern a duty of ours rather than a term between us — *the fork is the core* and the checking we owe them.)

### 7.7l Artifact filenames that cross machines — the full convention

*Verbatim from `CLAUDE.md` at `f5305a7` (Project operations → Artifact filenames that cross machines), moved here when that file was trimmed to its rules and pointers. Inside it, “here” and “this file” mean `CLAUDE.md`, and “above” / “below” mean the neighbouring entries of that section.*

**ASCII letters and digits only. No hyphens, no underscores, no spaces.
Numbers zero-padded.**

**Case is the one deliberate exception, and it is there to serve the rule's own
purpose** (2026-09-07). The hazard was never capitals — it was *two conventions*,
one artifact spelled two ways, which is how a rig run was lost. When the fork
adopted direction-in-the-filename in round 16 they spelled it
`round16lap01FROMcyanripTOplatterpus.md`, so ours is
`round16lap03FROMplatterpusTOcyanrip.md` — matched, not merely correct. The
operator holds both files in one folder and is the only reader either naming
convention exists for. `round08joint.txt`, `round08lap07.md`.

**Scope: artifacts a PERSON handles by hand** — rig scripts, the transport
envelope, anything named in a command an operator will type or paste, anything
that leaves this repo and comes back through a chat client or a file manager.

**NOT the committed handshake laps.** Those are `round-14-lap-18.md`, generated
by `handshake.py::handshake_filename()` and held to that shape by `_LAP_NAME`;
nobody types them and they never leave the repo by hand. The two conventions are
deliberate and this rule said otherwise until 2026-08-27, condemning the repo's
own enforced practice — which is the sort of rule that gets ignored wholesale
rather than obeyed selectively. The envelope that *does* cross by hand
(`round14lap16platterpus.md`) follows the rule, and
`tests/test_handshake_file_naming.py` enforces both shapes separately.

Added 2026-08-13, on the maintainer's instruction, after a rig run was lost to
it. The same artifact was `round08joint.txt` on their disk and
`round-08-joint.txt` in the instructions written for them. A path is an
exact-match string, so the load failed — and (separately fixed) the app then ran
a *different* script without saying so. The maintainer's words: *"every file you
talk about has a `-` or emdash, every file has none… it should be machine
readable, os agnostic, language agnostic."*

Why this spelling and not a prettier one: it is the intersection of what every
filesystem, shell, chat client and file manager in this project's path handles
without quoting or transformation. Hyphens are individually fine; *two
conventions* are not, and this is the one the artifacts already had.

**The rule is a convention; `uiscript/find_script.py` is the guarantee.** A rule
binds whoever last read it, and this artifact crosses two repositories, a chat
client and a file manager — none of which read anything. So `--run-script`
resolves the path by comparing names with separators and case removed, which is
symmetric (it works whichever convention either side picks) and refuses rather
than guesses when two files match. Legislate the name *and* stop depending on it.

## 8. The wire format — the shared protocol file

**The specification is [`handshake-protocol.md`](handshake-protocol.md), and it is
not ours.** It is the same document in both repositories; neither project owns it.
This section used to *restate* the format, which was the two-vocabularies problem in
miniature — a second copy that can drift from the first. The fork wrote it up as a
standalone shared file in round 7 lap 4 and that is strictly better, so we adopted
it verbatim rather than keeping our own wording.

What lives where:

| | where |
|---|---|
| the specification | [`handshake-protocol.md`](handshake-protocol.md) — shared, verbatim, both repos |
| our gate | `scripts/handshake.py` (`--status`, `--check`, `--release-gate`) |
| our conformance tests | `tests/test_handshake_conformance.py` — one test per row of the shared conformance table that is in force for the version we implement (C1–C45 plus C13a at v6), **except the v3/v4 rows among C21–C36 that still have no row-named test** — binding since round 9, counted in `_BINDING_ROWS_WITHOUT_A_NAMED_TEST`, a ratchet that may only shrink (sixteen until 2026-09-25, when C23 and C24 got tests with v6's K2 field; the count moves, so read the table, not this cell) |
| their gate | `tools/release-gate.py`; their tests are `tests/release_gate.py` |

**Current protocol version: 6 implemented, 5 declared** — `handshake.PROTOCOL_VERSION` is the authority for what our gate implements, `handshake.DECLARED_PROTOCOL` for what our laps declare, and the shared file's title for the spec. **Implemented since 2026-09-25**, when both of v6 §14's conditions held: the shared file byte-identical in both trees (`05abdfde…`), and the fork's gate at 6 (`cyanrip@643631b`, said in their round 25 lap 5). **Declared 5 until our next released lap says our gate implements 6** — §14: *"neither side declares 6 until both have said, in a lap, that their gate implements it"*. v6 adds §5e's `HANDSHAKE-AGREED-CHANGES` ledger (C44 requires it on a `GO` file declaring 6; C45: its content never gates a close), K2's `HANDSHAKE-INBOUND-OBSERVED` beside `-HELD` (required on a file declaring 6 — a reading of ours, since no row names it; both sides have written it on every lap since round 22), C43 (the version refusal over every file of a round, which we had since 2026-09-22), and the amended **C13a**: once a round is `CLOSED` a later lap declaring a *different* verdict is refused as a file and the round stays closed (`_terminal_at`), while one declaring the same verdict is not a transition. **What a C13a refusal does to a release is ours, because v6 leaves it to v7**: it holds a release until a later round exists, then that round governs (`illegal_transition_blockers`). The fork's gate still reopens on such a lap (its known divergence), so the two gates would print different round states and both hold the release. No such lap exists in either record; replaying ours finds ten later laps in eight rounds, all `GO`. The same commit enforced **C23** (`INBOUND-HELD` on every round ≥ 9 file), binding since round 9 and never checked: one sent file in the record lacks it, our `verified/round-13-lap-03.md`, pinned by hash. v5 (2026-09-22) added §5b (a close may resolve the peer verdict from the newest peer lap the gate holds, has enumerated and may read, when that lap is newer than the transcription's source), §5c (such a lap must declare `HANDSHAKE-READY-TO-READ: yes`, fail-closed), the `HANDSHAKE-PEER-VERDICT-SOURCE` field (ours, from round 23 lap 2) and rows C37–C42. **Implemented the same day the text became byte-identical, before round 24's lap 1**, because a rehearsal showed what staying at 4 would do: `--check` refused a v5 peer lap while `--status` and `--release-gate` closed a round on it. Both halves are fixed — the version refusal now runs on the path that decides a close (`refused_round_files`), and §5b is `resolve_peer_verdict`. **One reading of the spec is ours and was derived, not chosen**: "enumerated" means enumerated by the gate when it decides, because row C40 (a candidate *newer* than the source) is unreachable if it means "listed in the closing lap's own `INBOUND-HELD`". Raised with the fork for round 24. **Files declaring 4 or less keep v4 close semantics**, for the reason row C29 gives: a declared version is a request to be graded by that version's rules. (This sentence said *v4* until 2026-09-22, and said **2** until 2026-08-27, through the whole of v3 and v4: v3 added §3a addressing, §4a's legal state machine — with `CLOSED → OPEN` removed — §4b `WITHDRAWN`, §5a's digest and §6a-bis; v4 added §5a's one-lap rule. Read the numbers from the code and the shared file, never from this sentence.) A gate reading a *higher* number than it
implements must refuse the round rather than guess — it cannot know which of that
version's rules it is silently not applying. `handshake.PROTOCOL_VERSION` is ours.

**Why the conformance table is run and not merely read.** Running the fork's §8
table against our gate found a real defect on the first pass: row 12 (*"no round
files at all → refuse; an empty record is not agreement"*). Our `--status` returned
a bare "no handshake rounds" line, which does not end in `OPEN`, so
`--release-gate` printed *"every round is closed — release allowed"*. **A gate
satisfied by finding nothing, in the gate whose entire job is not being satisfied by
nothing.** That is the whole argument for a shared table rather than two
descriptions.

**Storage stays local and neither layout is wrong.** Ours is
`docs/handshake/{outbound,inbound,verified}/round-N[suffix].md`; theirs is
`docs/handshake/round-N[-lapM].md`. Both gates key on the *declared*
`HANDSHAKE-ROUND`, so neither depends on the other's filenames — which is something
each side is free to change.

---

## 9. Challenge ledger

**Why this table exists, and why it is a table.** On 2026-08-26 the maintainer
told the fork they are *"the adult in the room"* — as the ripping engine, most of
the accuracy burden is theirs, so they are to double-check, fact-check and
question us. The instruction that came with it was explicitly *measured*, not
felt:

> *"if they tend to be more correct than wrong, you should find out why and adopt
> the logic if possible, but let them try it out until you have measurable
> results either way."*

So: **do not pre-judge it in either direction, and do not decide it from the feel
of the last lap.** That is the same discipline as round 7's lap count, where the
fork tabled the numbers and we had the same numbers and had not looked. One row
per substantive challenge, cited to the lap that made it and the artifact that
settled it — never to a memory of either.

**What counts as a row.** A *substantive* challenge: one side asserting the other
is wrong about a fact, a mechanism or a contract, where the disagreement was
actually resolved. Not a question, not a preference, not an ask. A challenge
neither side settled stays out until it is settled — an unresolved row would be
scored by whoever last edited the table.

**Two things this ledger is NOT.** It is not a scoreboard to win: the whole
point of the mandate is a second validator, and *"neither side treats the other's
checking as a reason to skip its own"* (`CLAUDE.md` rule #12) is unaffected by
whatever this table says. And it is not a licence to weigh a challenge by its
author's record — **adopt the mechanism, not the conclusion.** A peer who is
right more often is running a better procedure, and the procedure is the
transferable part.

| # | round · lap | the challenge | who was right | settled by | mechanism worth taking |
|---|---|---|---|---|---|
| 1 | **r3 §H2** → retracted **r4 §H2** | Fork proposed changing our `Pregap length` derivation (subtract, uniformly) | **US** | `inbound/round-4.md:408` — *"my subtraction proposal was not [correct], and I have made no change"* | Both sides had reasoned from EAC's **cue** and applied it to EAC's **log**, and *"neither of us opened the log"*. Graduated as *answer from the artifact, and name which file* |
| 2 | **r4 §H3** | Fork warned our `Ripper build:` classifier would meet a fourth case: a tarball build emits `platterpus-fork-grelease` | **THEM** (advisory — we were safe, but only by accident of tokenising) | `inbound/round-4.md:419` | A warning about a case you are *currently* safe from is worth more than one about a case you are already failing. Filed as a test case, not as a fix |
| 3 | **r4 flag table** | Their published table said `-v`/`--version` with **no `-V` row**; every version probe we shipped sent `-V` | **THEM**, and the evidence sat in a committed file in this repo for a full round | `tests/test_argv_surface_agreement.py` now diffs it mechanically | *If the contract has two halves, check both.* We had verified their log lines against our parser and never their flag table against our argv |
| 4 | **r5** | Their fatal-message inventory was published as 88 strings; we reported it "VERIFIED INDEPENDENTLY" | **US** — re-deriving from their source found **16 more**, hidden by a hand-maintained prefix allowlist in their generator | `inbound/round-5.md:252` — *"Derive the fatal inventory from control flow, not a prefix allowlist"* | *Verify the behaviour, not the other side's description of it.* A list checked against itself is consistent, not verified |
| 5 | **r5** | Their statement that per-track paranoia counters *"sum exactly to the disc totals"* | **US**, conditionally — true without `-Z`, false under it, where per-track is the last pass and the disc total is every pass | our re-derivation, recorded in `CLAUDE.md` *"did I verify this where it could have failed?"* | Name the condition that would break a claim, then check **there**. We had "verified" it on an artifact where the sum is arithmetically forced |
| 6 | **r7 lap 2** | Fork corrected us that the `HH:MM:SS.mmm` → `MM:SS.FF` duration change is **upstream's** (PR #130), not theirs | **THEM** | `inbound/round-07-lap-02.md:141` | *An upstream change cannot be escaped by rolling back to upstream.* We had it filed as a fork change, which made "revert to stock" look like a mitigation it never was |
| 7 | **r7 convergence** | Fork tabled that round 7 had run 37 laps, 10 test pins and 8 pre-releases to produce **0 releases**, where rounds 5 and 6 took one lap each | **THEM**, and we held the same numbers and had not looked | their round-7 convergence proposal, adopted verbatim as **S-13 … S-16** | *Counted, not felt.* Also the substantive lesson: release-grade rigour applied to the **round** rather than to the **release** |
| 8 | **r12 lap 1 → withdrawn lap 3** | Fork declared, at column 0 as `HANDSHAKE-BREAKING`, that our `SUPPORTED_SCHEMAS` allowlists *schema strings* and would reject their diagnostics record — then promoted a question to `BLOCKING` on it | **US** | `inbound/round-12-lap-03.md:49` — they opened their own record and found **two artifacts in their repository** contradicting the claim before it was made — ours, filed on their side as inbound: `verified/round-10-lap-04.md:58` and `verified/round-11-lap-02.md:84` **in this tree** | *Never state a mechanism in the other side's code without citing where you read it.* Adopted verbatim from their write-up — a `HANDSHAKE-BREAKING` line about someone else's build is a guess unless it names the artifact |
| 9 | **r12 lap 3** | We offered a shared-blame explanation for row 8 — *"a name collision plus one unqualified sentence"*, and offered to take half. **They refused it** | **THEM** | `inbound/round-12-lap-03.md:76` — they opened all three cited sentences and tabled the context of each; every one sat in unambiguous release-manifest context | *An apology can get less scrutiny than a claim, for the same reason nobody argues with it* — and **a misattributed cause produces the wrong fix**: "write less ambiguous sentences" is unfalsifiable, where row 8's rule is checkable |
| 10 | **relayed 2026-08-27** | Their mutation sweep found `for (int j = 0; j < strlen(digest_str); j++)` in `fun512.c` mutated to `<=` and **surviving** | **THEM**, and it landed on us too: our own pattern captured `\S+`, so an 87-character digest would have entered an archival log looking correct | `CHANGELOG.md` (v0.6.30) + `parsers/cyanrip_log.fun512_signature_is_malformed` | **Mutation sweeps in a detached git worktree** — their fix for a recurring dirty tree, and the reason the finding exists at all. A surviving mutant is a test-suite defect reported as a code fact |
| 11 | **r15 lap 10** | Fork asserted our round-15 lap 9 §E1 was **right but too small** — we scoped the undistinguishable class at one mechanism (`total_error_count++`) from their published preamble; they disclosed that `FAIL_PATH` had **seven** alternatives while the preamble named **five** | **THEM** | Re-derived here from their source, not from their lap: `tools/gen-provider-contract.py` at `9bc7ad6` carries the seven-alternative regex written out inline, and instrumenting their own `evidence()` over the 121 published P5 rows reproduces their table exactly — `total_error_count++` 8, `ret = N;` 6, `err = N` 1, combined 1, over 84 `both`+`control flow` rows | **A hand-written description inside a generated artifact is the defect the artifact exists to prevent** — their fix builds `FAIL_PATH` *from* the published table so the two cannot drift, which is the same *one source of truth* move as their round-12 exit-code table and our generated consumer contract. **And the verification lesson is ours:** the re-derivation returned **three** different numbers from correct code (19, then 15, then 16) — 19 scanned all 349 call sites instead of the 121 published rows, 15 keyed by message text, which collides across files. *Is the population I measured closed?* was the entire difficulty, and both wrong answers looked right |
| 12 | **r16 lap 9 §2** | Fork asserted our acceptance run's single failure — `expect-log-well-formed` reporting the cancelled rip's record destroyed — is a **false negative**, and named the limit of what they could show: *"That shape would explain this one and **we have not shown it.**"* | **THEM** on the claim they made, and the restraint is the point | The mechanism, from `session/zz-applog-rotations/03platterpus/log.txt.1` **in the bundle they already held**: verification at `22:02:08.902`, the ripper's `Ripping finished at 2026-09-09T22:02:15-04:00` — 6.1 s later. Our lap 10 §C1 | **A challenge that stops at the evidence is worth more than one that completes the story.** They could have asserted the race and been right; they marked it unproven and were right *and* checkable. And the correction that came back is the transferable half: it is **two** defects, not one — the verb failed at `22:02:38.943`, 23.7 s *after* the log was complete, because it graded our snapshot rather than the file. A fix aimed only at their (correct) hypothesis would have shipped with the second one intact |
| 13 | **r16 lap 9 §1** | Fork concluded *"no `-H`, no `-E`, no `-W`, no `-x` appears in any of the eight rips — grepped from every `Invoked as:` line, not assumed"*, and therefore that close-condition clause 2 had still never run on a drive | **US** | All four ran. The clause-2 rips go through our script's raw `cyanrip` verb, which writes to its own `-D` and produces **no album folder**, so they are in `session/transcript.txt` (L1144 `-H -E`, 221.2 s, exit 0, `Preemphasis: none detected (deemphasis forced)`; L1365 `-H -W`, 220.7 s) and in none of the eight `.log` files | ***Is the population I measured closed?*** — our own rule, and this is the first time it has landed on them. The grep was correct over the set it ran on and the set was not the run. **The remedy is ours though**: a bundle that files its most load-bearing invocations outside the place a reader looks for invocations is our defect, not their oversight |
| 14 | **r16 lap 13 §2** | Fork accepted our §C2 **finding** (`disabled` is the zero-value fallthrough, so `a0830e0`'s clause-1 split IS reachable) and declined the **remedy** we attached to it — *'pin the checker where `a0830e0` is present'* | **THEM** | `a0830e0`'s own `disabled` string, opened in their tree: *'`AccurateRip: disabled` -- the query never ran, because -A was passed to the ONE rip that must not have it'* — **the exact claim our §C2 disproves.** Pinning there would have replaced a vague wrong cause with a specific wrong one. Their replacement reads `Invoked as:` and grades three ways (`round16-accept.py:191-216` at `5bbb5ae`) | **A finding and its remedy are separable, and being right about the first buys nothing for the second.** We proposed the remedy in the same breath as the finding and it inherited the finding's confidence. Their third branch — *no `Invoked as:` line at all* — is the one we would not have thought to ask for, which is the argument for naming the *property* we need and letting the owner of the code choose the fix |
| 15 | **r18 lap 2 §B2** | We asserted their proposed tier vocabulary was not merely incomplete but **actively unsafe to adopt**: two of its tokens, `SKIPPED` and `BLOCKED`, already exist in our tree meaning the opposite things — ours a consequence where theirs is a decision, and vice versa | **US** | `inbound/round-18-lap-03.md:56` — *"Confirmed exactly as you stated it… Two tokens, same spelling, opposite halves of the one distinction the state rule turns on"*; they restructured the spec to **seven concepts with the token as a separate column** (`:71`) | **A shared vocabulary needs a concept column and a token column, because agreeing on a word is not agreeing on a meaning.** Both sides would have passed their own conformance tests and written opposite facts into the same field. The transferable half is the *shape* of the fix: name the concept, then let each side declare its spelling, so a rename is an implementation detail instead of a contract change |
| 16 | **r18 lap 3 §4a** | Fork asserted our §E's *"the shared table now has 36 rows"* was wrong — §8 has **37**, because `C13a` carries a letter suffix our `C\d+` row pattern cannot match | **THEM**, one day after the ratchet was written | Verified against our own byte-identical copy at `docs/handshake-protocol.md:717`; our pattern counted 36 where the widened `C\d+[a-z]?` counts 37. Fixed in `tests/test_handshake_conformance.py`, with `C13a` now pinned by id | **Invisible beats uncovered, and that is the severity — not the arithmetic.** A row the *denominator* cannot include can never be reported missing, so the ratchet would have printed complete coverage while that row had none: `CLAUDE.md`'s *can this check be satisfied by finding nothing?* applied to a **set** rather than a count. **Their own counter has the identical hole** (`\bC[0-9]+\b`, their §5) and they found it in themselves while checking us — the same defect in both projects, independently, on the one row in the table that is not a bare number |
| 17 | **r21 §D → withdrawn r21 lap 4 §A** | We told them, in round-20 lap 2 line 81, that *"rounds 13 and 14 also set `HANDSHAKE-CLOSE-BY` in lap 2 rather than lap 1"*, and carried it into round 21 §D as an open question for them to check against their tree | **THEM** | Their §D answer put both rounds at lap 1; we enumerated every file under `docs/handshake/{inbound,outbound,verified}/` declaring the field and took the earliest declaring lap per round — **both declare it at lap 1**, and our own fixed reporter prints no set-in-lap note for either. Withdrawn in `outbound/round-21-lap-04.md` §A | **A claim can outlive the fix that invalidates it, because nothing re-runs what produced it.** The false line was produced by the directory-major reporter — *their* finding, which the **same lap's §B** describes us fixing. We fixed the code path and never re-derived the sentences it had written. Rule taken: *when a fix lands, grep for what the broken version asserted.* And their restraint is the other half — they offered the round-13 detail *"as evidence rather than as a finding"* and said round 14 might fit our diagnosis where round 13 might not; **both turn out not to fit**, so they under-claimed |
| 18 | **r21 lap 5 §2**, relayed | Fork asserted that round 21's own close condition §0.1 item 2 — *"our parser **reads** `Retry limit:` on real logs"* — was **never satisfiable**, and that the defect is theirs for writing it | **THEM**, and they asked us not to spend a lap on it | Checked in our own tree rather than taken: at `platterpus@4bedb45:src/platterpus/parsers/cyanrip_log.py:1876-1879` the label is an entry in `_IGNORED_DISC_LINES` — recognised and deliberately **not** extracted — and our own comment two lines above says *"We extract nothing from it either way, so the rename is invisible to the PARSE."* Both labels sit in one alternation, so there was never a rename for a parse to survive | **A close condition can ask for a behaviour the other side's code documents as deliberately absent, and nobody notices for four laps** — the comment was in our tree when their lap 1 was written, and neither of us read it. What the condition actually protected (an unrecognised disc line tripping our completeness sweep on *every* rip) **is** retired and was measured. Under R1 the wording is frozen, so it is annotated rather than restated — and our non-vacuity probe is marked down to what it proves: that the **sweep** would have fired, not that anything is *read* |
| 19 | **r21, relayed** | We reported that their recorded SHA for our held lap 4 was stale, and diagnosed it as *"`HANDSHAKE-INBOUND-HELD` pins a document whose own state cell says it may change"* — calling the portable half *"small but real"* | **THEM** — right that we flagged it, and their diagnosis is one step further back than ours | Their own lap 5, opened in their tree: that field carried **two laps, two hashes and two states** — our lap 2 (sent, filed) and our lap 4 (observed, held) — and said of lap 4 *in that same field* that it is not filed, while the note two lines down said they would file it byte-exact against the hash in that field. **The lap contradicted itself inside three lines** | **Staleness did not create the defect; it turned an overloaded field from ambiguous into a wrong instruction.** So the remedy is the **split**, not a re-read: `HANDSHAKE-INBOUND-HELD` for sent laps, `HANDSHAKE-INBOUND-OBSERVED` for held ones carrying `DO NOT FILE AGAINST THESE NUMBERS`. Adopted in both headers the lap it was proposed. Their framing of why it is worth more than agreement — *"we would rather be the worked example than the second opinion"* — is the transferable half: a proposal confirmed from the peer's own code beats one agreed to in principle |
| 20 | **r26 lap 4 §B**, their nit | Fork asserted our cancelled rip's report said *"0 of 0 tracks matched only an offset-variant pressing"* on a 14-track disc | **THEM** | Our copy of the bundle, `docs/handshake/artifactsround26/round26cancelmereport.json`: the parser took the disc's count from their footer, and the report recomputed the sentence from `len(tracks)`, which a cancel empties | **A correction applied to one copy of a rule.** The parser had been fixed and the report's restatement had not; now one function has two callers, tested on the filed log |

**Standing count as of round 26 lap 4: fork right 14, us right 6, of 20
resolved.** Tallied from the table above by `tests/test_challenge_ledger_count.py`,
which is the only reason this line is now right — and it earned its keep again on
2026-09-18: adding rows 17–19 failed the suite twice, once for the headline and
once for the sub-count window still ending at row 16. **Both numbers were re-derived
from the rows rather than added to.** That is the whole design: a corrected number
decays at the next row, a derived one cannot, and the gate refuses the arithmetic
shortcut that produced the original error.

**It was wrong, and it had been wrong before today.** The line read *"fork 8, us 6,
of 14"*, and when two rows were added on 2026-09-13 the new figure was computed by
**adding to the old one** instead of re-deriving it. The table's own rows 1–14
tally fork 9 / us 5; the headline said 8 / 6. So a number the maintainer explicitly
asked to be *"counted, not felt"* was felt — in the table that exists to honour
that instruction, two lines above a sub-count that was correct because it *was*
derived.

`CLAUDE.md` names it exactly: ***am I answering from the artifact, or from my
memory of the artifact?*** The artifact was sixteen rows directly above the
sentence. The fix is not a corrected number — a corrected number decays the next
time a row is added — it is that the count is now derived and a test fails if the
prose disagrees with the rows.

Read the count with three qualifications, all of which cut against treating it as
a verdict:

* **The sample is not closed and it is not the sample the mandate is about.** The
  challenge mandate was issued **2026-08-26**; rows 1–9 predate it. **Rows 10–20
  are the eleven made under it: fork right 9, us right 2** — this sub-count has been
  derived from the rows since it was written, rather than carried forward, which is
  why it was already correct when the headline above was not. *Is the population I
  measured closed?* — nine of these twenty are the *before* picture, and **n=11
  is still not a result**, so the answer to the maintainer's question remains **not
  measurable** and saying so is the honest reading. **Round 21 alone went 3–0 to
  them** (rows 17, 18, 19) and that is recorded rather than balanced: none of the
  three is a case where we asserted they were wrong and were right. Eight-of-ten is
  worth noting and worth not believing — and rows 13 and
  15 are the ones where the
  mechanism the mandate exists to surface ran in **our** favour, which is a reason
  to keep counting rather than a reason to stop. **And do not read the trend as a
  licence to defer to them**: row 14 is a row we could have avoided by asking
  *"is my remedy as well established as my finding?"*, which costs nothing and
  needs no peer.
* **Round 18 added one row in each direction on the same day, which is the
  cleanest illustration of why this is not a scoreboard.** Row 15 is us catching a
  defect in a spec they authored; row 16 is them catching a defect in a ratchet we
  authored. Neither finding is reachable by the side that wrote the thing — and row
  16's mechanism landed on *both* trees, because their counter has the same blind
  spot ours did. **A second validator is worth having precisely because it is
  second** (`CLAUDE.md` rule #12), and rows 15 and 16 are that sentence with
  numbers attached.
* **Neither side's errors are of one kind.** Ours cluster in *verification*
  (rows 4, 5 — checking a description, or checking under conditions that force
  the result); theirs cluster in *attribution* (rows 6, 8 — a mechanism stated
  without opening the artifact it belongs to). Those want different remedies,
  which is why the mechanism column matters more than the tally.
* **Self-correction is in the record on both sides** (rows 1, 8), and it arrived
  faster than either side's peer review. Row 8 is the strongest single entry in
  this table and the fork wrote it *against themselves*.

---

*Last updated for Platterpus v0.6.60.*
