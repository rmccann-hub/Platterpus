---
name: test-verification-checklist
description: "Self-audit checklist for Claude Code sessions. Run before claiming any code task is complete. Enforces evidence over assertion, blocks the common agent failure modes (weakening tests to make them pass, claiming untested code works), and scales rigor by tier."
metadata:
  version: "1.0.0"
  updated: "2026-09-05"
---

# Claude Code Test Verification Checklist

Run this against your own work before reporting completion. Every box requires
**pasted command output**, not a claim.

## How To Use This File

Three ways, pick one:

- **Paste it.** Drop the whole file into the session and say: *"Before you tell me
  you're done, work this checklist and show output for every box."*
- **Commit it.** Put it at `docs/TEST-VERIFICATION-CHECKLIST.md` and add to
  `CLAUDE.md`: *"Before declaring any task complete, work through
  `docs/TEST-VERIFICATION-CHECKLIST.md` at Tier 2 and output the Final Report."*
- **Invoke it.** Say: *"Run the verification checklist, Tier 2, Gates B through G."*

Set the tier at the start of the session:

| Tier | Use for | Gates required |
|------|---------|----------------|
| **1** | Scripts, internal tools, prototypes | A, B, C, G |
| **2** | Production, commercial, anything others depend on | A–G |
| **3** | Safety-critical, financial, data-destructive | A–G plus all Tier 3 items |

---

## Rule Zero: Evidence, Not Claims

<constraints>
An unchecked box is honest. A checked box without pasted output is a lie.

FORBIDDEN phrases unless immediately followed by the actual terminal output:
  "tests pass" / "this should work" / "I've verified" / "the build succeeds"
  "coverage is good" / "no errors" / "it's working now"

If a command was not run, the box stays unchecked and the Final Report says so.
If a command cannot be run in this environment, say WHY and mark it BLOCKED.
Never infer a result from reading code. Execute or abstain.
</constraints>

---

## Gate A: Before Writing Any Code

- [ ] Restated the task in my own words and confirmed scope with the user
- [ ] Read the existing code I am about to change — not just the file, the callers
- [ ] Identified the existing test setup (runner, config, conventions) and will match it
- [ ] Checked whether tests for this behavior already exist before writing new ones
- [ ] Listed my assumptions explicitly; flagged any that the user must confirm
- [ ] Confirmed what "done" means: what must be true for this to be correct?

**Stop condition:** If I cannot state how I will verify success, I do not start.

---

## Gate B: Before Claiming Code Works

Run each. Paste each output.

- [ ] **Build/compile** succeeds — output pasted
- [ ] **Formatter** run — output pasted
- [ ] **Linter** clean or violations explicitly listed — output pasted
- [ ] **Type checker** clean (typed languages) — output pasted
- [ ] **Full test suite** run, not just the new tests — output pasted
- [ ] **Exit codes** confirmed `0`, not just "looked fine"
- [ ] Ran the actual code path a real user hits, not only the test harness

<constraints>
Partial test runs prove nothing about regressions. Run the full suite.
If the suite is too slow to run fully, say so and state what was skipped.
</constraints>

---

## Gate C: Test Quality Audit

Tests that pass but verify nothing are worse than no tests. Audit for it.

### Every new test

- [ ] Asserts a specific value, not merely "no exception thrown"
- [ ] Fails if I break the code — **proved by actually breaking it and re-running**
- [ ] Has a name that says what broke without reading the body
- [ ] Is deterministic: no wall-clock, no real network, no ambient state, no ordering dependency
- [ ] Does not mock the thing under test
- [ ] Follows Arrange-Act-Assert with one Act

### Suite-level

- [ ] No test was skipped, `xfail`ed, or commented out to get green
- [ ] No assertion was loosened to accommodate a failure
- [ ] Ran the suite twice; results identical (no flakes)
- [ ] Ran the suite in random order if the runner supports it

<constraints>
FORBIDDEN RESOLUTIONS for a failing test. If a test fails, the only legitimate
moves are: fix the code, or report the failure to the user with analysis.

NEVER: delete the test, skip it, mark it expected-fail, widen the expected value
to match actual, wrap the call in a catch-all, add `# type: ignore`, or lower a
coverage threshold. If I am tempted to do any of these, that IS the finding —
surface it instead of hiding it.
</constraints>

---

## Gate D: Coverage of the Test Taxonomy

- [ ] **Unit** — pure logic covered, isolated, fast
- [ ] **Boundary** — zero, negative, max, empty, one-past-the-end tested
- [ ] **Negative/error path** — every `catch`/`except`/`if err != nil` branch has a test
- [ ] **Integration** — every external dependency boundary exercised for real
- [ ] **Regression** — a test now exists that would have caught the bug I just fixed
- [ ] **Coverage measured** — number reported, not estimated (Tier 1 ≥60% branch,
      Tier 2 ≥80% branch, Tier 3 100% branch + MC/DC on core)

Tier 2+:

- [ ] **Property-based** tests for algorithmic/pure code (invariants, round-trips)
- [ ] **Mutation score** reported — the only honest measure of suite quality
      (Tier 2 ≥60% core, Tier 3 ≥80%)
- [ ] **Fuzz target** for any parser, decoder, deserializer, or untrusted input handler
- [ ] **Contract test** at any consumer/provider or service boundary

---

## Gate E: Non-Functional and Supply Chain

Tier 2+. Skip only with a stated reason.

### Security

- [ ] Dependency/vulnerability scan run — output pasted
- [ ] Secret scan run; no credentials in code, config, or git history
- [ ] Static security analysis run (Bandit, gosec, cargo-audit, CodeQL, Semgrep)
- [ ] All user input validated at the boundary; injection vectors parameterized
- [ ] Errors do not leak stack traces, paths, or secrets to users or logs

### Reliability and performance

- [ ] Every external call has a timeout and a defined failure behavior
- [ ] Retries use backoff and are bounded — no retry storms
- [ ] Operations that can be invoked twice are idempotent
- [ ] Fault injection: verified behavior when the dependency returns 500, hangs, drops
- [ ] Benchmark baseline captured if performance matters; no unexplained regression
- [ ] Long-running paths checked for leaks (handles, memory, connections)

### Interface and lifecycle

- [ ] Accessibility scan run (UI work): keyboard-only path and contrast verified
- [ ] Upgrade from previous version tested — **and rollback tested**
- [ ] Schema migration tested forward **and backward**
- [ ] Backup verified by actually restoring, not by confirming the file exists
- [ ] Uninstall / cleanup path tested
- [ ] Cross-platform matrix run if the project claims multi-platform support

---

## Gate F: Edge Case Gap Sweep

The categories teams skip. Walk the list; mark N/A with a reason, never silently.

### Time and calendar

- [ ] Timezone differences — [ ] DST transition — [ ] Leap year (Feb 29)
- [ ] Month/year boundary — [ ] Clock skew — [ ] Dates far past/future

### Input and encoding

- [ ] Empty / null / missing — [ ] Zero, negative, MAX_INT — [ ] Very large input
- [ ] Unicode, emoji, accents, apostrophes (`O'Brien`, `müller`) — [ ] RTL text
- [ ] Injection payloads — [ ] Zero-byte and at-limit files — [ ] Wrong file type

### State and concurrency

- [ ] Double-submit / double-click — [ ] Race conditions — [ ] Deadlock
- [ ] Concurrent edit conflict — [ ] Out-of-order events — [ ] Crash mid-transaction

### Failure and resource

- [ ] Dependency returns 500 — [ ] Dependency hangs — [ ] Network partition/offline
- [ ] Disk full — [ ] Memory/handle exhaustion — [ ] Permission denied
- [ ] Partial failure leaves consistent state

### Lifecycle

- [ ] First run / cold start — [ ] Config missing or malformed
- [ ] Environment parity (dev vs prod) — [ ] Log rotation / unbounded log growth

---

## Gate G: Before Declaring Done

- [ ] Re-read the original request; every part of it is addressed
- [ ] Nothing was silently dropped, stubbed, or `TODO`-ed without telling the user
- [ ] No debug code, commented-out blocks, or scratch files left behind
- [ ] Docs/README/comments updated if behavior changed
- [ ] Diff reviewed line by line — every change is intentional and explained
- [ ] Full suite green on a clean run, from a clean state
- [ ] **Final Report produced** in the format below

---

## Required Final Report Format

```text
VERIFICATION REPORT — Tier <1|2|3>

RAN (with output shown above):
  build ............ PASS/FAIL
  lint ............. PASS/FAIL
  typecheck ........ PASS/FAIL/N-A
  full suite ....... PASS/FAIL  (<n> passed, <n> failed, <n> skipped)
  coverage ......... <n>% branch
  mutation ......... <n>%  or NOT RUN
  security scan .... PASS/FAIL/NOT RUN

DID NOT RUN (and why):
  <command> — <reason: blocked / not applicable / no tooling / out of scope>

KNOWN GAPS:
  <what is untested, unverified, or assumed — be specific>

RISKS I AM NOT COMFORTABLE WITH:
  <anything I worked around, guessed at, or could not confirm>

CONFIDENCE: <high | medium | low> — <one sentence why>
```

<constraints>
The "DID NOT RUN", "KNOWN GAPS", and "RISKS" sections must never be empty on a
non-trivial task. If they are, I did not audit honestly — go back to Gate B.
</constraints>

---

## Anti-Pattern Watchlist

Self-check. These are the ways an agent produces work that looks finished but isn't.

| Anti-pattern | What it looks like | Correct move |
|---|---|---|
| Claiming without running | "Tests should pass now" | Run it. Paste output. |
| Green-by-weakening | Loosened assert, added skip, widened expected | Fix code or report failure |
| Mocking the subject | Test mocks the function it tests | Test real behavior |
| Assertion-free test | Only checks "didn't throw" | Assert a specific value |
| Coverage theater | Tests written to touch lines, not verify behavior | Run mutation testing |
| Silent scope drop | Part of the request quietly unaddressed | Say what was skipped |
| Error swallowing | `except: pass` added to quiet a failure | Handle or propagate |
| Happy-path-only | Every test uses valid input | Walk Gates D and F |
| Untested "fix" | Bug fixed, no regression test added | Add the test that would have caught it |
| Partial-run inference | Ran one test file, declared suite green | Run the full suite |

---

## Command Reference by Ecosystem

Substitute the project's actual tooling; this is the default set.

```bash
# Python
ruff format . && ruff check . && mypy . && pytest --cov --cov-branch -q
pip-audit && bandit -r .
mutmut run                      # Tier 2+

# JavaScript / TypeScript
npm run lint && npx tsc --noEmit && npx vitest run --coverage
npm audit --audit-level=high
npx stryker run                 # Tier 2+

# C# / .NET
dotnet format --verify-no-changes && dotnet build -warnaserror
dotnet test --collect:"XPlat Code Coverage"
dotnet list package --vulnerable --include-transitive

# Go
gofmt -l . && golangci-lint run && go test ./... -race -cover
govulncheck ./...
go test -fuzz=Fuzz -fuzztime=60s ./...    # Tier 2+

# Rust
cargo fmt --check && cargo clippy -- -D warnings
cargo test && cargo llvm-cov --branch
cargo audit && cargo deny check
cargo mutants && cargo miri test          # Tier 2+

# PHP
vendor/bin/php-cs-fixer fix --dry-run && vendor/bin/phpstan analyse
vendor/bin/phpunit --coverage-text && composer audit

# PowerShell
Invoke-ScriptAnalyzer -Path . -Recurse -Severity Error,Warning
Invoke-Pester -CodeCoverage *.psm1 -Output Detailed

# Bash
shellcheck *.sh && bats test/

# SQL (SQL Server)
sqlfluff lint . ; EXEC tSQLt.RunAll
```

---

## Limitations

- Checklist verifies process, not correctness — a fully checked list on wrong
  requirements still ships the wrong thing. Gate A is the guard against that.
- Mutation and fuzz tooling does not exist for PowerShell, Bash, or user-authored
  SQL; cover those concerns with boundary, negative, and golden-file tests instead.
- Coverage thresholds are defaults, not law. Adjust per project and state the target.
- Tier 3 items (formal methods, MC/DC, traceability matrices) are referenced here
  but not specified in full; see the full testing taxonomy for those.

*Last updated for Platterpus v0.6.38.*
