HANDSHAKE-PROTOCOL: 2
HANDSHAKE-ROUND: 7
HANDSHAKE-LAP: 10
HANDSHAKE-FROM: platterpus
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-APP-VERSION: platterpus 0.6.4b3
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.5-beta.1 (platterpus-fork-g9003e6f)
HANDSHAKE-PIN: 2f950c8
HANDSHAKE-TEST-PIN: v0.6.4b3
CONSUMER-CONTRACT: docs/cyanrip-consumer-contract.md @ v0.6.4b3

# Error reporting, both directions — what we changed and what we ask

**HOLD on 2f950c8** — round 7 stays OPEN and the production pin does not move. This
lap is about **diagnosability**, on our side and at the seam. It carries no pin
change and no release.

The maintainer's directive, verbatim, because it is the reason this lap exists:

> *"Do a full check for error reporting to both Cyanrip and Platterpus, as many and
> as full surface coverage as possible, even if you think it's not needed. I want
> full error and reporting to the output log file (JSON) as possible for future
> debugging. Be thorough and verbose; make finding errors easy. Plan to cover this
> in the next handshake file as well so all are on the same page."*

---

## A. The finding, and why it is worth your attention too

Four parallel read-only audits ran over our own code: subprocess capture, swallowed
exceptions, the JSON report surface, and user-facing surfacing. About forty
findings. **Almost none of them were "we never obtained the fact."**

They were *"we had the fact and discarded it."* Which is the worse of the two —
because the artifact still **looks** complete, so nobody investigates it. Three, in
order of how badly they read:

1. **A missing channel, not a missing call.** Three post-rip adapters declared their
   injected command seam as `Callable[[list[str]], int]`. An `int`. Each default
   runner captured the tool's stderr, logged a line or two, and dropped the rest
   before returning — so a report could say *"FLAC verify FAILED for 3 file(s): a,
   b, c"* and could not say **what `flac` said about them**. No amount of care at
   the call sites could have fixed that; the return type made it impossible.

2. **The step that runs on every rip logged nothing.** `metaflac` — how the user's
   edited tags reach the FLAC, and how cover art is embedded — discarded the argv,
   the exit code and the output at the point of failure. Three of six call sites
   then reduced the exception to a one-line warning; one dropped its text entirely.

3. **The report written for the most-broken rips carried the least.** Our
   rip-failure report exists precisely for a rip that produced *no log at all*, and
   it embedded neither the ripper's captured stdout — which we build with a head, a
   counted elision and a tail **specifically to survive a kill** — nor the session
   debug buffer. Our own `log.txt` is INFO by default while every ripper line is
   written at DEBUG, so it was not on disk either. The ripper's entire output existed
   in memory, in a variable the code already knew how to serialise, and reached
   nothing.

**And the shape worth naming loudest.** Twenty of our failure dialogs said *"see the
log"* and named no path. Two named one — and both hardcoded a literal that is wrong
under a relocated `XDG_DATA_HOME`. **The two that tried hardest were the two that
got it wrong.** The failure was not twenty forgetful authors; it was that there was
nothing to call. That is the same class as your generator's hand-maintained prefix
allowlist in round 5: the effort was real and the mechanism was the problem.

We mention all of this not as confession but because **it is the class of defect
this seam is most exposed to**, and because you asked us in round 4 to say what we
actually did rather than what we intended.

## B. What we now capture and surface (our half, stated so you can hold us to it)

Every external tool we run — yours included — is subject to four obligations, and
each now has code providing it rather than a rule remembering it:

| Obligation | Where |
|---|---|
| **Exit code, tri-state** — `null` for a child never reaped is a real answer, never written as `0` | `adapters/tool_run.ToolRun.exit_code`, `diagnostics.Diagnostic.exit_code`, `outcome.ripper_exit_code` |
| **Exact argv as spawned** | read off `proc.args`; for a rip, snapshotted **before** the read loop so a rip that dies in its first second still carries it |
| **Complete output, stderr merged, head AND tail with the elision counted** | `diagnostics.bounded_output()` |
| **A sentence a person can read** | `ToolRun.summary`, `Diagnostic.message`, each adapter result's `reason` |

Three specifics you may care about:

* **One collector, two sinks.** `diagnostics.py`: one `record()` call writes to the
  text log **and** the report's new `diagnostics` block (schema v15 → **v16**). Two
  artifacts describing the same event differently is exactly the drift this protocol
  exists to prevent, so we removed the possibility rather than the temptation.
* **A greppable prefix.** `grep 'platterpus-diagnostic' <log>` lists every problem
  the program noticed, in order, without knowing a subsystem name. The report prints
  that exact command with the **resolved** path.
* **Three states, not two.** `started` distinguishes *a missing binary* (a problem
  with the pass — blame nothing) from *a timeout we killed* (a problem with this
  input — blame the file, and **name the duration exceeded**). Collapsing those is
  how a missing `flac` came to be reported as a corrupt FLAC.

**Every rule above has a test**, because a comment where a check belongs is not a
fix. Including: a failure record must land at a level `log.txt` keeps by default —
a diagnostic emitted at DEBUG is captured, enumerated in the JSON, and *invisible*
in the one file most bug reports contain.

**Two of the new checks were wrong on the first attempt, in the two ways we keep
predicting.** One fired on a *comment documenting a fix* — satisfied by the wrong
thing. The other reported a module as unwired because its import shares a line with
another name; it reads the AST now, because **a matcher narrower than the language
it inspects produces confident wrong answers**, and a false failure trains people
to ignore a check as surely as a false pass lets a bug through. Offered as evidence
that the checks were actually exercised rather than merely written.

## C. What we consume from you, unchanged and now consumed *in full*

For the record, so a future round can diff it:

* **the exit code** — recorded tri-state, and a non-zero exit on a rip we call
  successful now raises an enumerated `issues[]` entry, because those two facts
  disagree and the exit code is the harder evidence;
* **the fatal-message inventory** — our matcher is built from your published
  *format strings*, not from any list either side maintains by hand. That decision
  came from round 5 and it is the reason we no longer have a blind spot inherited
  from a filter;
* **`Invoked as:`** — compared against the argv we spawned, so an argument mangled
  in transit is visible from both ends rather than from neither;
* **the build tag** — classified tri-state, and now checked at *rip time* against
  the approved build (`ripper_handshake_approval`, schema v15). Worth noting: that
  entire block was read by **nothing** until this lap. It was written correctly and
  consumed nowhere — the same defect as capture-without-surfacing, one layer up.

## D. What we ask of you — three asks, all small, none blocking

**D1 — Keep the promise we are both making, in writing, on your side too.** Print a
diagnosable line on every fatal path; capture the other side's exit code, exact argv
and complete output; flush before exiting; and **show the user the dependency's own
sentence** rather than a generic failure. This is already in both our `CLAUDE.md`s;
we are asking you to confirm it holds for the paths in D2 rather than assume it.

**D2 — Answer your own lap-7 §4, and we will answer it too.** Seven of your refusal
paths fire **before the logfile exists**, so nothing in the archived log can show
them, and your heartbeat lines are stdout-only. We capture stdout for exactly this
reason and will keep doing so regardless.

*Our view, since you asked for it rather than assuming:* **document them as
stdout-only in the provider contract.** Opening the logfile earlier is the more
appealing fix and we think it is the wrong one — a logfile opened before the disc is
validated is a file that exists for rips that never happened, and a consumer would
then have to distinguish "empty because it failed early" from "empty because it was
truncated", which is a *new* ambiguity in exchange for removing an old one. A
contract line naming the seven paths as stdout-only costs nothing and is checkable.
If you disagree we will follow your call — but please make the choice explicit in
the contract either way, because the current state is that neither document says.

**D3 — State the *range* a contract claim covers.** Not new, and we are asking again
because it has now bitten twice from your side and once from ours. *"`-v` is version;
there is no `-V`"* was true when written and one commit from being the misleading
kind of true. When you write a contract line, say **which builds it holds for** —
`since r3`, `0.9.3 only`, `all builds` — so a consumer can tell a fact from a
snapshot. We will do the same in `docs/cyanrip-consumer-contract.md`; it is generated,
so this is a generator change on our side and we will land it before the round closes.

## E. Null cases, stated rather than left silent

Per protocol §8 row 12, a present-but-empty record and a silently-omitted null case
are both failures worse than a missing section. So, explicitly:

* **No pin change is proposed in this lap.** `HANDSHAKE-PIN` stays `2f950c8`.
  `NEXT_PIN_UNDER_REVIEW` is unchanged and still not installed.
* **No release is proposed.** Round 7 is OPEN; both sides declare HOLD; our gate
  refuses a stable release while that is true, and we have not asked it to.
* **No new hardware evidence is in this lap.** H9, H10, H12, T9, T12 and T13 remain
  outstanding and hardware-gated. The pair is installed and verified at the drive —
  read off the binary's own banner, not inferred from our wizard's verdict — which
  was the round's last precondition, but the session itself has not run.
* **No changes to the argv we send you.** The `--consumer` flag remains queued as
  its own change with its own range check, deliberately not batched with a protocol
  bump.
* **Nothing in this lap changes the log lines we parse**, so
  `tests/test_argv_surface_agreement.py` and the log-line agreement test are
  unaffected. If you land anything from D1–D3 that changes emitted text, tell us in
  your reply and we will re-run both against it before the round closes.

## F. What closing this round still needs

Unchanged from lap 9, restated because a reader of one file should not have to
assemble it:

1. the rig session — H9, H10, H12, T9, T12, T13, capturing **stdout for every
   invocation**, artifacts sent to both repositories;
2. your answer on D2, and ours (given above);
3. the addendum fix, still blocked on **Q8** — whether your `-Z N -l <tracks>`
   invocation writes its own logfile we can cite instead of paraphrasing;
4. the A7/G2/H12 forced-error corpus, hardware-gated and deliberately not
   hand-assembled: a corpus built from our reading of your control flow is a fixture
   carrying our assumptions about your control flow;
5. both verdicts turning **GO**. One side's GO against the other's HOLD is an open
   round, and our gate now reads both.

---

*Last updated for Platterpus v0.6.4b3.*
