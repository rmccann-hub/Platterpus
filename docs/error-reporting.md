# Error reporting — the design of record

> *"Do a full check for error reporting to both Cyanrip and Platterpus, as many and
> as full surface coverage as possible, even if you think it's not needed. I want
> full error and reporting to the output log file (JSON) as possible for future
> debugging. Be thorough and verbose; make finding errors easy."*
> — maintainer, 2026-08-04

This is the single home for **how a failure becomes something a person can act
on**. `CLAUDE.md`'s *diagnostic completeness* rule is the law; this file is how the
codebase satisfies it, and what each surface is *for*.

Companions: [`testing.md`](testing.md) for the rules a change is held to,
[`architecture.md`](architecture.md) for the patterns,
[`dependency-contracts.md`](dependency-contracts.md) for what each external tool is
allowed to be asked and expected to say.

---

## 1. The finding that produced all of this

Four parallel read-only audits ran on 2026-08-04: subprocess capture, swallowed
exceptions, the JSON report surface, and user-facing surfacing. They produced a
ranked list of about forty findings, and the striking thing is the shape they
share.

**Almost none of them were "we never obtained the fact."** They were *"we had the
fact and discarded it"* — which `CLAUDE.md` already calls the worse of the two,
because the artifact still **looks** complete. Three examples, in order of how
badly they read:

* `flac_verify`, `transcode` and `flac_recompress` each declared their injected
  command seam as `Callable[[list[str]], int]`. Each one's default runner captured
  the tool's stderr, logged a line or two, and dropped the rest. So a report could
  say *"FLAC verify FAILED for 3 file(s): a, b, c"* and could not say **what `flac`
  said about them**. Not an oversight at a call site — a **missing channel**, which
  no amount of care at the call sites could have closed.
* `metaflac` runs on **every** rip — it is how the user's edited tags reach the FLAC
  and how the cover art is embedded — and logged nothing at all on failure. The
  argv, the exit code and the output were discarded at the point of failure; three
  of six call sites then reduced the exception to a one-line warning, and one
  dropped its text entirely.
* The rip-failure report exists for rips that produced **no log at all** — the
  most-broken ones — and passed neither `artifacts=` nor `debug_log=`. The worker's
  `captured_stdout`, built with a head, a counted elision and a tail *specifically
  to survive a kill*, was discarded; the always-DEBUG session buffer was not
  embedded; and `log.txt` is INFO by default while every ripper line is written
  with `log.debug`, so it was not on disk either. The ripper's entire output existed
  in memory, in a variable the code already knew how to serialise, and reached
  nothing.

**A fourth shape, and the one worth naming loudest:** the two dialogs that tried
hardest to be helpful — by actually naming the log file — were the two that named
it *wrong*, hardcoding `~/.local/share/platterpus/log.txt` against an XDG-aware
`paths.py`. Twenty others said *"see the log"* and named nothing. The failure was
not twenty forgetful authors; **it was that there was nothing to call.**

---

## 2. The four obligations, and where each is met

`CLAUDE.md` requires four things of every external tool we run. Here is the code
that provides each, so a reader can check rather than trust.

| Obligation | Where |
|---|---|
| **Exit code, tri-state** — `null` for a child never reaped is a real answer and is never written as `0` | `adapters/tool_run.ToolRun.exit_code`; `diagnostics.Diagnostic.exit_code`; `outcome.ripper_exit_code` |
| **Exact argv as spawned** | `ToolRun.argv` (read off `proc.args`); `RipWorker._ripper_argv`, snapshotted *before* the read loop so a rip that dies in its first second still carries it |
| **Complete output, stderr merged** | `run_tool` uses `stderr=STDOUT`; bounded by `diagnostics.bounded_output` — head **and** tail, elision counted |
| **A sentence a person can read** | `ToolRun.summary`, `Diagnostic.message`, and the `*Failure.reason` on each adapter result |

### The bounding rule has one home

`diagnostics.bounded_output()`. It had been written **three** times with three
different limits, one of them head-only — and a head-only cap drops exactly the
last line, which is where a tool puts its fatal message. Head *and* tail, tail
larger, elision counted and marked. **A silent truncation reads as completeness.**

### Three states, not two

`ToolRun.started` is the state the old `int` seam could not express:

* **not started** — a missing binary. A problem with the *pass*: nothing was
  checked, so nothing should be blamed. Abort.
* **started, no verdict** — a timeout we killed. A problem with *this input*: the
  tool demonstrably works. Blame the file, continue, and **name the duration that
  was exceeded**.
* **started, exited non-zero** — the tool refused, and said why.

Collapsing the first two is how a missing `flac` came to be reported as a corrupt
FLAC.

---

## 3. The three surfaces, and what each is for

One collector feeds all three. That is the whole design: **two artifacts that
describe the same event differently is the drift this project keeps paying for.**

### `diagnostics.py` — the collector

Every subsystem records a `Diagnostic` (severity, namespaced `subsystem.what` code,
message, detail, tool, argv, tri-state exit code, where, track). **One `record()`
call writes to two sinks** — the text log and the report — so they cannot disagree.
Four rules are encoded rather than remembered:

1. **Recording also logs.** Not "and remember to log too."
2. **Never raises.** A recorder that throws while recording an error destroys the
   evidence for the failure it was called about.
3. **Bounded, with the truncation stated.**
4. **Tri-state everywhere it matters.**

The log prefix is a fixed, greppable token, and *"make finding errors easy"* is a
literal instruction: `grep 'platterpus-diagnostic' <log>` shows every problem the
program noticed, in order, without knowing a single subsystem name. The report's
`log_grep_hint` field prints that exact command with the **real** path.

### `log.txt` — the always-on, cross-session record

INFO by default. **This is why the level of a failure record matters:** a
diagnostic emitted at DEBUG is captured, enumerated in the JSON, and *invisible* in
the one file most bug reports contain. Failure records land at ERROR or WARNING;
`tests/test_diagnostics.py` asserts the level, not merely that something was
logged.

### `.platterpus.json` — the per-rip bundle

Schema v16. `diagnostics` sits **third**, ahead of `outcome` and the verdict,
because it is the first thing anyone debugging a rip should read. `issues[]` is the
severity-tagged derived list — the thing a triager opens first — and it is derived
from the *serialised* blocks, never the raw results, so it can never disagree with
what the report shows.

`issues[]` being empty means **"nothing reported a problem"**, which is *not*
"everything was verified". Every surface that renders it says so.

### `Help → Copy diagnostics…` — the surface for failures outside a rip

The per-rip JSON is the richer bundle, but it exists only for a rip and is reachable
only from the rip pane. A setup failure, a dependency-check crash, a failed update
or a drive probe had no copyable surface at all. This one renders the version
**pair**, the environment and every diagnostic recorded this session, from the same
collector.

---

## 4. The severity contract

Three levels, and the distinction is load-bearing: if everything were escalated,
the level would carry no information and a reader scanning for problems would be
back to reading everything.

| | Means | Example |
|---|---|---|
| `error` | The user experienced a failure, or a claim we make is invalidated | the ripper exited non-zero; a FLAC master failed its decode test; the re-compress step could not rewrite a master |
| `warning` | Something degraded, was skipped, or could not be measured. The rip may be fine | CTDB unreachable; a dependency below its minimum; a non-zero *probe* exit; the library move failed (the audio is still where the rip put it) |
| `info` | Notable, not a problem — because *"why did it choose that?"* is a real debugging question | the release genuinely has no cover art; the ripper build could not be identified (`not_determined`) |

**An unrecognised severity becomes `error`, never `info`.** Guessing downward would
hide a problem, and that is the wrong place to be optimistic.

---

## 5. Codes

`Diagnostic.code` is a stable, machine-greppable key: namespaced `subsystem.what`,
listed in `diagnostics.KNOWN_CODES`. The **message** is for a person and may be
reworded freely; the **code** is a contract, so a bug report can say *"seven
`ripper.stall_detected` in one rip"* without anyone parsing prose.

An unlisted code is **recorded anyway** — losing a real diagnostic to a taxonomy
quibble would be absurd — and logs a warning so the list stays honest. Because the
runtime behaviour is deliberately forgiving, the gate lives in the tests:
`test_every_wired_code_is_a_known_code`.

---

## 6. What is enforced, and by what

Every rule above has a test, because **a comment where a check belongs is not a
fix** — and this project has now watched that lesson arrive from five directions.

| Rule | Enforced by |
|---|---|
| Every failure-prone subsystem records | `tests/test_diagnostics.py::test_every_failure_prone_subsystem_records_a_diagnostic` — requires the module to **both** import the collector *and* name its code, because a label match alone answers "did they name it" and not "did they write it" |
| Failure records land at a level `log.txt` keeps | `…::test_a_failure_record_lands_at_a_level_the_default_log_file_keeps` |
| Wired codes are known codes | `…::test_every_wired_code_is_a_known_code` |
| No message says "see the log" without naming it | `tests/test_failure_surfaces.py` |
| No module hardcodes the log path | same file — with an allowlist that must still *contain* what it excuses |
| `report_types.py` describes the whole report | `tests/test_report_types_completeness.py` — a runtime sweep over a real report |
| `issues[]` flags each thing it now flags | `tests/test_rip_report.py`, one test per code |
| The rip-failure report embeds the ripper's output and the debug log | `tests/test_ui_main_window.py` — revert-proven |

**Every sweep carries a floor.** *"Can this check be satisfied by finding
nothing?"* — an examined-count assertion is the answer, and two of these sweeps
have floors on *both* the population and the per-item count.

Two of the checks written this session were themselves wrong on the first attempt,
in the two ways `CLAUDE.md` predicts:

* the "see the log" sweep fired on a **comment documenting a fix** — a check
  satisfied by the wrong thing;
* the wiring sweep reported `ctdb_client.py` as unwired because its import shares a
  line with another name. It reads the AST now: **a matcher narrower than the
  language it inspects produces confident wrong answers**, and a false failure
  trains people to ignore a check as surely as a false pass lets a bug through.

---

## 7. What we ask of the ripper, and what it asks of us

The seam is bidirectional (`CLAUDE.md` rule 12), so error reporting is a
**bilateral** obligation, carried in the handshake rounds rather than assumed.

**What we already rely on, and now consume in full:** cyanrip's exit code, its
fatal-message inventory (the matcher is built from their published format strings
rather than any list either side maintains by hand — `ripper_messages.py`), the
`Invoked as:` line so a mangled argument is visible from both ends, and the build
tag in its version banner.

**What we commit to, in both directions:**

* print a diagnosable line on **every** fatal path;
* capture the other side's exit code, exact argv and complete output;
* flush before exiting;
* and **show the user the dependency's own sentence** rather than a generic
  failure. *Capture without surfacing is the same bug from their side* — 21 of
  cyanrip's fatal strings were captured and never surfaced once, which is what
  `tests/test_ripper_error_surfacing.py` exists to prevent recurring.

**The open ask, carried into the round-7 lap:** seven of the ripper's refusal paths
fire *before* its logfile exists, so nothing in the archived log can show them, and
its heartbeat lines are stdout-only. We capture stdout for exactly this reason. The
question we owe them an answer to is whether those paths should be fixed by opening
the logfile earlier or documented in the provider contract as stdout-only — they
asked for our view rather than assuming, and either answer is fine as long as it is
*written down* on both sides.

---

## 8. Adding a new failure path

1. Pick or add a code in `diagnostics.KNOWN_CODES` (`subsystem.what`).
2. Record it — `diagnostics.error/warning/info`, or
   `record_command_failure` for an external tool, which takes all four obligations
   in one call. **Do not** hand-roll the four; a per-call-site version is how four
   facts drift to three.
3. If it should appear in `issues[]`, add a check to `rip_report._issues` reading
   the **serialised** block, and a regression test for that code.
4. If a user sees it, append `ui/failure_text.LOG_POINTER` — do not write your own
   sentence, and do not type out the path.
5. Ask the pre-flight question that applies here: *"is the user's symptom gone, or
   just the mechanism I named?"* A capture with no surfacing is not a fix.

---

*Last updated for Platterpus v0.6.4b8.*
