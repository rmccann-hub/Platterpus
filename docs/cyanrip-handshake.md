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

## 7.6 Standing status — what the fork can assume between rounds

**Not a round, and not a call for one.** Rounds are the *formal* channel and they
have a cost (S-13: a round's close conditions are fixed at lap 1, and an open round
blocks both sides' releases). Between rounds the fork still needs to know where we
are, so this section is the standing answer, rewritten in place rather than
accumulating a file per update. Maintainer's framing, 2026-08-21: *"context for the
next test and what to do (if anything is needed even)."*

**As of Platterpus v0.6.21 (2026-08-21):**

- **No round is open.** All eleven are CLOSED with bilateral `GO`;
  `scripts/handshake.py --release-gate` prints *"every round is closed — release
  allowed"*. Nothing on our side is waiting on the fork, and nothing the fork does
  is currently blocked by us.
- **The pin is unchanged:** `cyanrip 0.9.4-rc1+platterpus.5 (platterpus-fork-gddf7ac3)`,
  approved by **round 8**. We install it and every rip re-verifies it at the drive.
- **The seam has not moved, and this is checkable rather than asserted.** The
  generated `docs/cyanrip-consumer-contract.md` — every log line we parse, every
  flag we send — is **byte-identical since v0.6.12b6**, the app version round 8
  approved the pin for, apart from the line naming the round itself. Nine app
  minors, +183 lines across the three seam modules, and **zero** change to the
  contract they implement: the additions were internal (an absent-vs-mismatched
  verdict distinction, a shared `has_log_checksum` helper, escaping property
  tests). So round 8's evidence still holds for 0.6.21 on the seam axis, and the
  fork does not need to re-derive anything for this release.
- **One honest caveat, because rule #12 obligation 3 says artifacts under different
  app versions are not interchangeable evidence:** `APPROVED_FOR_PLATTERPUS_VERSION`
  still reads `0.6.12b6`, so every rip report and EAC log states the pairing was
  verified at that version while the app is 0.6.21. That is a *true historical
  record*, not a stale pointer — the round and the pin agree — and it is
  informational: the verdict keys on the build tag, so no rip is mis-graded. It is
  named here so nobody reads the version gap as a silent re-approval.

**Two asks, both `NEXT-ROUND`, neither blocking anything** (S-14: a finding is not
grounds to hold a release unless it breaks the artifact under review — neither does):

1. **`-x` measures the cache and then rips the whole disc.** Measured on the rig
   2026-08-19: `cyanrip -x -N -s 0` printed `Cache probe: 32 sectors, 73.5 KiB,
   uncached read 362.6 ms` and then continued into a full rip, ETA 1h 3m. Our
   verb killed it at 300 s and **the child could not be reaped** (`exit: null`), so
   the drive stayed held for everything after it. We have removed the probe from
   the rig script until `-x` exits after measuring. Worth saying plainly: this was
   the *useful* outcome of running the flag for the first time — "it does something
   nobody expected" is exactly what a first execution is for.
2. **`--verify-log` should separate *absent* from *mismatched* by exit code.** A
   killed or cancelled rip leaves a log with **no** `Log FUN512:` footer; an altered
   archival record leaves one that does not match. *"The ripper was killed
   mid-write"* and *"this file was modified"* are different findings and only the
   second is a tamper claim. We fixed our side in 0.6.20 by reading the log
   ourselves rather than keying on the message text — per the fork's own lap-12 J4,
   which asked us not to build on genopt's `"No FUN512 checksum found"` string. That
   works, and it also means two projects now answer *is this log a complete archival
   record* by separate routes. A machine-readable discriminator plus the null case
   stated in the provider contract would collapse them back into one.

**What the next hardware run is for, so the fork knows what to expect from it.**
`docs/rig-scripts/rigcancelandoverread.txt`, revised for 0.6.21, on the pinned
build. It proves one thing nothing else can: a **completed second rip after a
mid-rip cancel** — the open half of Task #53. The drive-*open* half is already
proven (2026-08-20: after a cancel the drive re-scanned and re-identified the disc,
which a held reader cannot do). Nothing in the run asks anything of the fork, and
nothing in it is expected to exercise a fork change; if it fails, the finding is
most likely ours.

**So: nothing is needed from the fork right now.** Round 12 opens when that run
produces a clean bundle, carrying the two asks above. Opening it earlier would
create a round whose close condition cannot be met without hardware evidence we do
not yet have — the S-13 failure that ran round 7 to 37 laps.

---

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
| our conformance tests | `tests/test_handshake_conformance.py`, **one test per §8 row** |
| their gate | `tools/release-gate.py`; their tests are `tests/release_gate.py` |

**Current protocol version: 2.** A gate reading a *higher* number than it
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

*Last updated for Platterpus v0.6.21.*
