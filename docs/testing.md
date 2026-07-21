# Testing strategy & standards

The single, authoritative description of **how we test Platterpus** and the
rules every change is held to. It exists because this project's hardest bugs
have all been the same shape: code that passes unit tests with fakes, then
fails on real hardware / in the packaged build / on an unexpected input
(silent startup crash, AppImage CA-cert bug, `offset find`, whipper output
drift). The strategy below is built to catch *that* class.

> **Portability note.** This file is written to be lifted into a sibling
> project (e.g. `scheduling-engineV2`) with only the project-specific
> examples swapped. The layers, the five-tier case taxonomy, and the
> institutional rules are general; the parser/adapter/Qt specifics are the
> illustrations.

---

## 1. Philosophy — the trophy, plus a hardware gate on top

We follow the **testing trophy** (Kent C. Dodds) rather than a unit-heavy
pyramid, because the value in this codebase lives at the *seams* — adapters
wrapping an external CLI, Qt widgets reacting to signals, parsers digesting
third-party output. Pure unit tests of trivial functions buy little; tests of
how the pieces integrate buy a lot.

```
        ▲  manual / real-hardware  ← the test-plan; CI literally cannot do this
       ╱ ╲ packaging smoke (AppImage actually launches)
      ╱   ╲ property-based (parsers never crash on any input)
     ╱     ╲ integration / contract (adapter ⇄ faked subprocess; widget ⇄ signal)
    ╱       ╲ unit (parsers, value logic, config)
   ╱_________╲ static (ruff, type hints) — free, always-on
```

The trophy's base is **static analysis** — `ruff` + mandatory type hints catch
a whole tier of bugs before a test runs. The layer CI *cannot* reach — a real
CD in a real drive — sits at the very top and is covered by a written
[test-plan.md](test-plan.md), not by automation. Naming that gap explicitly is
the point: **we do not pretend CI proves the app rips a disc.**

## 2. The layers, and what lives in each

| Layer | Tooling | What we put here |
|---|---|---|
| **Static** | `ruff check` + `ruff format --check`, `mypy` (strict def-typing, `pyproject.toml [tool.mypy]`) | style, import order, likely-bug patterns (bugbear), modern-syntax, wrong attributes / bad return types / None-misuse. CI `lint` + `typecheck` jobs (both gating). |
| **Unit** | `pytest` | parsers (`test_parsers_*`), config schema/migration, value helpers, dependency-version logic. |
| **Integration / contract** | `pytest` + fakes | adapters against a faked `subprocess` (argv built right, non-zero/timeout handled); Qt widgets driven through their signals with a fake backend (`test_ui_*`). |
| **End-to-end** | `pytest` + fakes at the boundary only | the *whole* pipeline through the real assembled `MainWindow` (all mixins, real signals, a real `RipWorker` on a real `QThread`), faking only the external edge (ripper subprocess, MusicBrainz, cover-art HTTP, `metaflac`). `test_e2e_rip_pipeline.py` drives one full rip and asserts the cross-cutting outcome: tagged FLACs + embedded/saved cover art + a fidelity verdict. This is the only tier that proves the *threaded* finish path is wired across module boundaries. |
| **Startup smoke** | `pytest` + offscreen Qt | the real `app.main()` entry point comes up headless (composition root, real adapters, a turn of the real event loop), with probes stubbed for hermeticity. `test_app_smoke.py` asserts the window composes (menus + widgets) and the launch dependency check applies **on the GUI thread** with no cross-thread Qt warnings — it caught a real off-thread-apply bug unit tests couldn't. |
| **Property-based** | `hypothesis` | invariants over huge input spaces — see §4. |
| **Packaging smoke** | `appimage.yml` | the built AppImage launches headless and reaches the Qt loop (`test_build_harness.py` guards the recipe). |
| **Supply-chain / audit** | `ci.yml` + `mutation.yml` | gating `pip-audit` (dependency CVEs), the server-side media-guard (rule 9's CI backstop), the advisory `tests-touched` nudge (rule 1's reminder), and the weekly non-gating mutation run — from the 2026-07-08 trust audit ([trust-audit-2026-07-08.md](trust-audit-2026-07-08.md)). |
| **Manual / hardware** | [test-plan.md](test-plan.md) | a real rip, CTDB verify CRC, the drive-setup wizard screens (the whipper-era `drive analyze`/`offset find` cases need re-scoping), the GUI screenshot. Gated work that the cloud env can't validate. |

## 3. The five-tier case taxonomy (apply to every feature)

For any non-trivial unit of behaviour, deliberately write cases across these
tiers. "I added a happy-path test" is not done.

1. **Easy** — the documented happy path (the shape from the real fixture).
2. **Medium** — realistic variations: optional fields absent, reordered output,
   extra whitespace, a second drive, a year-less album.
3. **Hard** — combinations and stateful sequences: a track with v1 *and* v2
   AccurateRip blocks; cancel *during* the pre-track scan; a config migration
   from an older schema.
4. **Edge** — boundaries: empty input, zero tracks, a negative read offset,
   the max retries, a 99-track disc, a path with spaces/unicode.
5. **Unexpected** — adversarial / malformed: garbage bytes where a number is
   expected, a truncated log, an output format cyanrip has never actually
   emitted. **This tier is where the silent-crash bugs hide** — and where
   property-based testing (§4) earns its keep.

## 4. Techniques — when to reach for each

- **Example tests** (default). One behaviour per test, Arrange-Act-Assert,
  named for the behaviour (`test_refresh_handles_unexpected_exception...`).
- **Golden / characterization tests.** For parsing real tool output, commit a
  captured sample under `tests/fixtures/` and assert against it. This is how we
  pin cyanrip's actual log/`-I` shapes (the live backend whose output can
  drift — when it does, update the fixture in the same PR as the parser
  change) and how the frozen legacy whipper formats stay pinned for old logs
  (`rip_log_real_whipper_0_7.log`, `drive_list_pioneer.txt`, …).
- **Property-based tests** (`hypothesis`). Use for **invariants that must hold
  over all inputs**. Our keystone invariant: *a parser must never raise on
  arbitrary text* (`test_parsers_property.py`). Hypothesis generates hundreds of
  adversarial inputs and **shrinks** any failure to a minimal reproducer.
  Also good for round-trips (build valid input → parse → recover it) and
  metamorphic relations (N concatenated blocks → N records).
  - **Where they earn their keep over examples: *position-dependent* invariants.**
    A security/format check written against a few hand-picked example positions
    ("`..` in the middle", "control char in the middle") can silently *not* hold
    at the edges. Fuzz the position (`test_settings_validation.py`'s traversal /
    control-char property tests) — that's exactly how the 2026-07-03 bug was
    found: `_validate_dir` checked the **stripped** value, and `str.strip()`
    removes more than the obvious whitespace — the C0 "information separators"
    `\x1c`–`\x1f` (plus `\t\n\r\v\f`) are stripped too, so a leading/trailing one
    slipped past a check that caught it mid-string. **Lesson:** validate the
    **raw** input for a forbidden character class; strip only for the empty /
    format checks, never before a character-set check.
- **Fakes over mocks.** Construct a real fake implementing the adapter ABC
  (`_FakeBackend`) rather than patching internals — it survives refactors and
  documents the contract.
- **Fault injection.** Make the fake *raise* (timeout, non-zero exit, malformed
  output) and assert the app degrades loudly, not silently. Every external call
  has a failure path; test it.
- **Qt signals & threads.** Drive widgets through their public signals; test
  worker *logic* directly (call `run()`/`start_rip()` and assert emitted
  signals) and keep Qt glue thin. For a genuine **end-to-end** test that runs a
  worker on a *real* `QThread` and waits for completion, `pytest-qt`'s
  `qtbot.waitSignal` is the standard tool — we deliberately **don't** depend on
  it (minimal-deps ethos) and instead wait the dependency-free way. Two
  hard-won rules for that (see `test_e2e_rip_pipeline.py`):
  - **Don't block the GUI thread waiting for the worker.** `QThread.wait()` on
    the GUI thread *deadlocks*: the worker's `finished → thread.quit()` is a
    queued connection *to the GUI thread* (the `QThread` object lives there), so
    a blocked GUI thread never delivers `quit()` and the thread never ends.
    Instead, **poll** with a wall-clock deadline until the terminal signal fires
    — use the shared **`process_until(predicate, timeout=…)`** fixture
    (`conftest.py`), the one canonical bounded pump (it also flushes posted
    events so queued cross-thread signals deliver). Never a bare
    `while True`; never `QThread.wait()` on the GUI thread.
    (`QEventLoop.exec()`/`QSignalSpy.wait()` are also unreliable to *terminate*
    under the headless `offscreen` platform.) This deadlock is real and was hit
    in-suite: `test_rip_not_blocked_when_drive_offset_is_known` used `wait()` and
    left a thread running into teardown.
  - **A leaked worker thread aborts the whole suite.** Destroying a running
    `QThread` is a hard `SIGABRT`, so a test that starts a worker but returns
    before it finishes can take down *every* test, not just itself. An autouse
    `conftest` fixture (`_join_leaked_qthreads`) tracks `QThread.start()` and
    joins any still-running at teardown as a backstop (warning, not failing) —
    but the *fix* is to drive the worker to completion with `process_until`. Run
    `pytest -W error::UserWarning` locally to surface any leaker as a failure.
  - **The PySide interpreter-shutdown abort (and our mitigation).** Separately
    from a *mid-run* leak, PySide6 + `offscreen` + many QThread tests can SIGABRT
    during the QApplication's Qt-internal global teardown — *after* every test
    passed and coverage was written. It only flips the exit code (a CI flake).
    `conftest` mitigates it: the session QApplication is pinned in a module
    global (never GC'd), and a `pytest_sessionfinish` hookwrapper `os._exit`s the
    process with the real status once results + the `.coverage` data file are
    finalized — skipping the crash-prone teardown. It does **not** mask failures
    (an impossible gate / a failing test still exit non-zero — there are checks
    for both) and does **not** mask a mid-run abort. Trade-off: pytest-cov's
    *printed* report is skipped (it prints later); the gate is still enforced by
    exit code and `coverage report` reads the saved `.coverage` anytime. This is
    best-effort — it greatly reduces but doesn't 100% eliminate the local race
    (it's environment-specific; real CI has been green).
  - **A *mid-run* GC pass can finalize a QObject off the Qt thread → SIGSEGV.**
    Distinct from the shutdown abort above (which the `os._exit` hook covers):
    the `test_e2e_rip_pipeline` test runs real worker/daemon threads doing file
    I/O + Qt work *concurrently* with the GUI thread, and Python's cyclic GC can
    fire on **any** thread when its allocation threshold trips. Under `offscreen`,
    a collection that finalizes a QObject on a non-Qt thread segfaults the
    interpreter *during the run* (exit 139) — a real, intermittent CI abort
    (traced from a faulthandler dump to a GC pass on the cover-art worker thread
    inside `apply_cover_art`, 2026-07-03; it hit py3.12 three runs straight while
    3.11/3.13/3.14 stayed green — then hopped to the pending-installs-dialog test
    on 3.13 the next run). The `os._exit` hook can't help (the crash is mid-run,
    not at shutdown). **Mitigation (central):** the shared `process_until` **pump**
    pauses the cyclic collector (`gc.disable()`) for the duration of each pump and
    restores it after — the pump *is* the window where a worker thread churns Qt
    objects concurrently with the GUI thread, so every worker-thread test that
    waits via `process_until` is covered at once. The `e2e_window` fixture does the
    same for the one test with its own inline poll loop. Refcount freeing still
    runs throughout and cyclic collection resumes the instant the pump returns, so
    memory stays bounded and nothing any test asserts changes. Reach for a manual
    `gc.disable()` only for a test that runs Qt work on non-Qt threads *without*
    going through the pump; the real answer everywhere else is to drive workers to
    completion and not create QObjects off the Qt thread.
  - **The mid-run abort was a wrong-thread QObject destruction — ROOT-CAUSED and
    FIXED (2026-07).** Hammering the two worst files (`test_e2e_rip_pipeline` +
    `test_ui_pending_installs_dialog`) reproduced a ~40–55% process abort
    (SIGABRT/SIGSEGV/SIGBUS, exit 134/135/139) on py3.11 — and it **persisted with
    cyclic GC fully disabled**, which ruled out the GC-finalize theory. The
    faulthandler dump showed a *worker* thread aborting in pure C++. The real
    cause: `PendingInstallsDialog._on_install_finished` (a queued slot on the GUI
    thread) cleared the last Python reference to the install **worker** while the
    worker's own `QThread` was still alive — destroying the worker's C++ QObject
    on the wrong thread (undefined behaviour). `gc.disable()` couldn't help because
    the destruction was refcount-driven (`= None`), not a cyclic collection. **Fix:**
    let the queued `deleteLater` destroy the worker on its own thread, and clear
    the Python refs only after the *thread's* `finished` signal (event loop fully
    stopped). Local abort rate dropped from ~40–55% to **0/25**. The CI test step
    is back to a single clean pass (no retry wrapper) with a `timeout-minutes`
    backstop. Lesson graduated: a worker moved to a `QThread` must be destroyed on
    that thread (queued `deleteLater`), never by dropping its last Python ref from
    the GUI thread — clear the owning references on `QThread.finished`, not on the
    worker's `finished`.
  - **Suppress first-run offers before pumping events.** `processEvents()` will
    fire any pending `QTimer.singleShot` — including `_maybe_offer_first_run_setup`,
    whose `QMessageBox.exec()` **blocks forever headless**. Construct the window
    with the "already prompted" config flags (`host_setup_prompted=True`, …) so
    those offers are no-ops. (This is the same `processEvents` hazard called out
    for widget tests in `conftest`.)
- **Architectural fitness tests.** A small, fast test that protects a *design
  property* rather than a single behaviour. We enforce the "never block the GUI
  thread" rule this way: `test_gui_thread_discipline.py` AST-parses every
  `ui/` module and fails if any makes a synchronous blocking call
  (`subprocess.run`/`check_output`/…, `os.system`, `urlopen`, a call on
  `requests`, `time.sleep`) — so the freeze bug class can't silently return. It
  **resolves import aliases first** (`import subprocess as sp; sp.run(...)` and
  `from subprocess import run` both count) and ships with meta-tests proving the
  guard detects a planted offender *and* its aliased spellings (a fitness test
  that can't fail is worthless). **Known limit — and why it's not enough alone:**
  the AST guard only sees `ui/`; it cannot follow a `ui/` slot that synchronously
  calls a blocking function defined in `deps/`/`adapters/` (a callable passed in).
  That exact gap shipped the 0.4.2 install freeze. The complement is a **runtime
  guard** (next bullet). Reach for fitness tests whenever a rule is easy to
  violate and expensive to catch by eye; portable to any sibling project.
- **Runtime "didn't block the GUI thread" guards.** Because the AST guard can't
  follow cross-module calls, any path that does blocking work behind a callable
  also gets a *runtime* check. Two complementary forms (both in
  `test_ui_pending_installs_dialog.py`): (1) **thread-identity** — record
  `threading.get_ident()` on the GUI thread, have the injected work record it
  too, and assert they differ (`test_install_runs_off_the_gui_thread`); (2)
  **heartbeat** — a main-thread `QTimer` must keep ticking while the work runs
  (`test_event_loop_stays_alive_during_a_slow_install`); if the work ran on the
  GUI thread, `processEvents()` would block inside it and the timer would stall.
  Identity is the zero-flake primary; heartbeat catches blockers identity can't
  see (a slow pure-Python loop, a C-extension call).
- **Mutation testing** (weekly in CI, never a gate). `mutmut` measures whether
  tests actually *catch* bugs rather than just execute lines — coverage says a
  line ran, mutation says a test fails when that line is wrong. It runs
  automatically as a weekly, non-blocking workflow
  (`.github/workflows/mutation.yml`) over the parsers, the AccurateRip verdict
  (`verdict.py`), and the CTDB CRC (`ctdb/crc.py`) — read the run summary for
  survivors; it never gates a PR. The §7 `pipx` command runs it locally on any
  module.

## 5. Institutional rules (the non-negotiables)

1. **Every shipped bug gets a regression test in the same PR as the fix.** The
   test must fail before the fix and pass after. (E.g. the startup-resilience
   fix shipped with `test_refresh_handles_unexpected_exception_without_crashing`
   and the excepthook tests.) This is how a real-hardware finding becomes
   permanent CI coverage.
2. **Parsers never raise.** Any new parser of external output gets a
   property-based "never raises on arbitrary input" test alongside its example
   tests. Degrade to empty/default; never throw into the GUI.
3. **Fail loud, never silent.** Error paths surface to the log *and* the user
   (dialog / placeholder). Tests assert the surfacing, not just the absence of a
   crash.
4. **Coverage gate.** CI runs branch coverage with `--cov-fail-under` (currently
   **91%**, TOTAL ~93%). The gate **ratchets up, never down** — raise it when
   TOTAL comfortably clears it; never lower it to make a build green.
5. **Version matrix.** CI runs the suite on every supported Python (3.11–3.14).
   Add a version when users move to it; we've been bitten by version-specific
   breakage before.
6. **The hardware gate is explicit.** Anything that can only be proven on real
   hardware goes in [test-plan.md](test-plan.md) with a checkbox, and the code is
   structured to **fail safe** until that box is ticked (e.g. CTDB CRC returns
   NO_MATCH, never a false "verified").
7. **Stub anything that touches the network, a real subprocess, or a real
   thread.** An unstubbed update download, cover-art fetch, `gio`/`kbuildsycoca`
   launch, or rip worker can hang the suite or spawn detached background
   processes. Inject a fake (the adapters take injectable fetchers/runners) or
   monkeypatch the call.
8. **When you move code between modules, move its monkeypatch targets too.**
   `monkeypatch.setattr(some_module, "free_function", fake)` only affects callers
   that resolve the name *through that module*. After a method moves to a new
   module (e.g. a `MainWindow` mixin extraction), patch it where it now lives —
   or patch the function's **source module** and have callers use it
   module-qualified (`offset_config.is_offset_configured(...)`), so one patch
   point covers every caller. A patch that silently stops intercepting is how
   the 2026-06-13 `RipMixin` extraction briefly let a test start a *real* rip
   thread in headless mode (hard abort). Patching an attribute on a **shared
   module object** (`drive_control.eject_drive`) is unaffected by caller
   location.
9. **No copyrighted media in the repo — not even a temporary test fixture**
   (`CLAUDE.md` Critical rule #8). The repo is public, so a committed music file
   redistributes copyrighted material. Test real audio **outside** the repo (the
   scratchpad or `/tmp`), delete it after, and commit only the **text** proof —
   rip logs + per-track CRCs (the CRCs prove bit-perfection without the audio).
   If a test truly needs real PCM, generate a synthetic tone or use a CC0/
   public-domain clip — never a commercial track. `.gitignore` denies audio
   extensions as a backstop, and CI's server-side `media-guard` job rejects any
   pushed audio file even if the local hook was bypassed.
10. **Off-thread work gets a runtime guard that it ran off the GUI thread.** The
    freeze bug class (now seen three times — see CLAUDE.md) is only caught if a
    test *proves* the blocking work (install, rip, probe, decode) ran on a
    worker, not the GUI thread — the AST guard structurally can't follow a
    callable into `deps/`/`adapters/`. For any path that does blocking work
    behind a callable, add a thread-identity assertion (and, for slow work, a
    heartbeat) — see §4 "Runtime guards" and
    `test_install_runs_off_the_gui_thread`. This is the regression guard that
    keeps the 0.4.2 install freeze from silently returning.
11. **Validate every input and every dependency output — and enforce it in CI.**
    (CLAUDE.md Code conventions; added 2026-07-01 after a session found it was
    *nowhere* a written requirement.) The rules aren't left to discipline — they
    are self-enforcing:
    - **Inputs:** all validation lives in the pure `settings_validation` module
      (never inline in widget slots). A **completeness meta-test**
      (`test_validated_field_names_matches_config_exactly`) asserts *every*
      `Config` field has a rule, and a **reacts-to-a-bad-value** meta-test
      corrupts each field in turn and asserts an issue is raised — so a new
      setting **cannot ship unvalidated** (the test goes red). The dialog shows a
      visible error and blocks OK on any error, and `log_issues` records it.
    - **Security:** exploit-shaped inputs are rejected — path traversal (`..`),
      control chars/NUL, absolute templates. And there is **no shell**:
      `test_security_no_shell` statically forbids `shell=True` / `os.system` /
      `os.popen` across the whole tree, so a crafted album title or path can never
      reach a shell (every subprocess is an argv list).
    - **Outputs:** a failing dependency's stderr is captured to the log (never
      swallowed); parsers of that output still never raise (rule 2). The exact
      args/syntax we pass each tool are recorded in
      [dependency-contracts.md](dependency-contracts.md) — keep it in step with
      the adapter in the same change.
    - **Reports:** the `.platterpus.json` rip report is the machine-readable
      record of *everything that happened* — every gate, error, and check (the
      maintainer's standing ask). Its completeness is enforced the same way
      inputs are: a **completeness meta-test** (`test_rip_report_completeness.py`)
      asserts every top-level section the schema promises is actually populated by
      `build_report`, so a new report field **cannot ship un-serialized** (the
      test goes red). Same shape as the settings completeness meta-test above —
      the discipline is *don't trust a human to remember; make the omission fail a
      test*.

## 6. Definition of Done (testing) — paste into every PR

- [ ] New/changed behaviour has tests across the relevant **tiers** (§3) — at
      least happy-path + one edge + one unexpected.
- [ ] Any **bug fixed** has a regression test that fails without the fix.
- [ ] New **parser of external output** has a property-based never-raises test.
- [ ] New **external call** has a fault-injection test (timeout / non-zero /
      malformed) asserting a loud, graceful failure.
- [ ] New **user/config input** is validated in `settings_validation` (type +
      range + chars + format), the **completeness meta-test** still passes, and a
      new `Config` field has both a `validated_field_names()` entry and a
      `_BAD_VALUES` entry. New **dependency call** or flag is recorded in
      [dependency-contracts.md](dependency-contracts.md) and captures the tool's
      stderr to the log on failure. — *CLAUDE.md: validate every input & output*
- [ ] New **rip-report section/field** is populated by `build_report` and the
      report **completeness meta-test** (`test_rip_report_completeness.py`) still
      passes — a new field cannot ship un-serialized. — *CLAUDE.md: validate every
      input & output*
- [ ] `ruff check` + `ruff format --check` clean.
- [ ] `mypy` clean (the gating CI `typecheck` job; strict def-typing package-wide).
- [ ] Coverage gate passes; gate not lowered.
- [ ] If the change touches hardware-only behaviour, [test-plan.md](test-plan.md)
      has a new/updated checklist item.
- [ ] **No copyrighted media staged** — no audio file (`.flac`/`.wav`/`.mp3`/…)
      in the commit, even a temporary test fixture. — *CLAUDE.md Critical Rule #8*
- [ ] `CHANGELOG.md` `[Unreleased]` has a bullet for the change, **in the same
      commit** (CI enforces this; a pure historical-record commit opts out with a
      `[skip changelog]` line of its own in the commit message). — *CLAUDE.md
      Critical Rule #7*
- [ ] **At session end:** `docs/session-log.md` has a newest-first entry, and any
      durable lesson has been **graduated** to its home (CLAUDE.md / `PLANNING.md`
      KDD / [architecture.md](architecture.md) / this file) — not left only in the
      log. — *CLAUDE.md Critical Rule #7*

## 7. Commands

```bash
# Fast local loop (no coverage overhead):
pytest

# Exactly what CI enforces (branch coverage + gate):
pytest --cov=platterpus --cov-report=term-missing --cov-fail-under=91

# Property tests only (more examples for a deeper sweep):
pytest tests/test_parsers_property.py --hypothesis-seed=random

# Test-quality audit (slow; runs weekly in CI via mutation.yml, never a gate).
# Run locally on the same scope, or any module:
pipx run mutmut run --paths-to-mutate "src/platterpus/parsers/,src/platterpus/verdict.py,src/platterpus/ctdb/crc.py"
pipx run mutmut results
```

Install the test tooling with the dev extra: `pip install -e ".[dev]"`
(brings in `pytest`, `ruff`, `pytest-cov`, `hypothesis`, `mypy`).

## 8. Sources

- [Testing Trophy & integration-first strategy](https://dev.to/craftedwithintent/understanding-the-testing-pyramid-and-testing-trophy-tools-strategies-and-challenges-k1j)
- [Hypothesis — property-based testing](https://hypothesis.readthedocs.io/)
- [pytest-qt — Qt GUI testing](https://pytest-qt.readthedocs.io/)
- [Golden/snapshot testing options](https://pypi.org/project/pytest-golden/)
- [Mutation testing with mutmut](https://johal.in/mutation-testing-with-mutmut-python-for-code-reliability-2026/)

---

*Last updated for Platterpus v0.4.24.*
