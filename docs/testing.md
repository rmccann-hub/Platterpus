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
| **Supply-chain / audit** | `ci.yml` + `mutation.yml` | gating `pip-audit` (dependency CVEs), the server-side media-guard (rule 9's CI backstop), the advisory `tests-touched` nudge (rule 1's reminder), and the weekly non-gating mutation run — from the 2026-07-08 trust audit ([trust-audit-2026-07-08.md](archive/trust-audit-2026-07-08.md)). |
| **Manual / hardware** | [test-plan.md](test-plan.md) | a real rip, CTDB verify CRC, the drive-setup wizard screens (Test 3), the read-effort/CD-Extra/companion-log cases (Tests 12–14), the GUI screenshot. Gated work that the cloud env can't validate. |

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

### 5.x — Test the wiring, at the call site (added 2026-07-28)

The 2026-07-28 whole-application audit found the **same test-shaped hole** behind
four of the five recent escapes, and behind one feature that shipped broken for
four consecutive releases:

> A test that hands a fact to a renderer proves the renderer honours it. It proves
> **nothing** about whether anything ever *tells* it.

The pure case: `render_eac_style_log(rip_log, outcome_status="cancelled")` was
called directly by two tests, both green, both correct. The production call site
read `_last_outcome` — a **dict** — with `getattr(outcome, "status", "")`, which
always returned `""`, so the `*** INCOMPLETE RIP ***` banner could not render on
any real rip. `mypy` could not catch it either: `getattr(x, "literal", default)`
is typed `Any`. Four releases claimed a fix that had never once executed.

So, as a rule:

- **A regression test for a wiring bug goes through the production entry point**
  (`window._write_eac_log`, not `render_eac_style_log`). If the entry point is
  awkward to drive, that awkwardness is the finding — fix the seam.
- **Where a value's type is known, read the attribute.** A `getattr` with a
  default is an assertion-free cast: it silently absorbs a shape change and
  defeats every type check downstream. Where the shape genuinely is external
  (a `Signal(object)` payload), `isinstance`-narrow at entry — that narrows for
  mypy *and* is a real runtime guard (`_on_derived_verified` is the pattern).
- **A guard added in one place is a bug report about every other place.** The
  clean-sweep denominator and the offset-variant predicate were each fixed once,
  in the EAC exporter, and left wrong in the verdict banner, the status line, the
  disc panel and the JSON report. When you add a guard, grep for the predicate and
  fix every site — or better, move it into one shared function and delete the
  copies. `tests/test_surface_consistency.py` exists to make that failure loud.
- **Prefer a positive anchor to a bare negative.** `assert "Test CRC" not in text`
  passes just as happily against a renderer that produced nothing at all — and
  `render_eac_style_log`'s blanket `except` means a broken render degrades to a
  (validly-checksummed) stub. Pair each `not in` with something that must be there.

### 5.y — Fail open is worse than fail loud (added 2026-07-28)

A broad `try` around a whole function turns "this crashed" into "this found
nothing", and the two are indistinguishable to the caller. `validate_config()` was
one `try` around every rule: a single non-string field made the first rule raise,
the catch-all returned the issues collected so far — an empty list — and the
config layer read that as "valid" and persisted a `..`-traversal template.

- **Isolate each unit of work** so a crash costs only that unit's findings, and
  **log which one failed** by name.
- **Type-check before you parse.** A validator that skips the one field that is
  actually broken has failed at its only job.
- Never-raises and fail-open are *not* the same contract. Never-raises means the
  caller keeps running; it does not license reporting success.

### 5.z — Diagnosability is part of the suite (added 2026-07-28)

`conftest.py` hard-exits at session finish to dodge a PySide teardown race. That
workaround was discarding pytest's **entire terminal summary**: a red CI run
produced progress dots and nothing else — no failing test names, no tracebacks, no
`--durations`. It was invisible because the suite was green. The hook now prints
the summary itself before exiting; if you touch that hook, keep it that way.


### 5.w — Cyclic GC is paused during a test, and why that is load-bearing

**Fixed 2026-07-28, after being latent for most of the project's life. Read this
before touching `tests/conftest.py`'s fixture order, and before adding a
`gc.collect()` anywhere.**

**The symptom.** The suite died with SIGSEGV, intermittently on CI and *5 runs
out of 5* locally on a 4-core Python 3.11 box. The traceback always pointed at
an innocent bystander — a dialog test that happened to call `gc.collect()`, a
`pathlib.rglob` inside a checksums worker — never at anything related to the
actual defect.

**The mechanism.** Three things compounded:

1. **`deleteLater()` does nothing here.** It posts a `DeferredDelete` event and
   hands ownership to Qt, and Qt delivers that event only when the event loop
   that posted it exits, or when it is requested *by type*. This suite runs no
   event loop; `processEvents()` does not qualify and neither does a bare
   `sendPostedEvents()`. So windows accumulated, pinned, for the whole process.
2. **Post-rip work runs on daemon `threading.Thread`s** — hashing, verification,
   transcoding, the library move. Daemon means "don't hold up interpreter exit",
   not "safe to abandon".
3. **A cyclic collection can begin on any thread** that trips the allocation
   threshold. Whichever thread is inside the collector when the GUI thread
   destroys a widget is the one that dies. On CPython ≤ 3.11 a collection can
   even start part-way through a C-extension allocation, which is why the 3.11
   CI leg failed while 3.12+ passed.

**The fix, in `tests/conftest.py`** — and note it generalises a guard the
codebase had already reached for twice locally (`process_until` pauses the
collector around its pump; the e2e rip fixture pauses it for a whole test):

* `_cyclic_gc_paused_during_each_test` disables the **cyclic** collector for the
  duration of every test and does a cheap generation-0 collect at teardown.
  Reference counting is untouched, so nearly everything is still freed the
  instant it goes out of scope; only cycle *detection* is deferred to a
  deterministic point on the main thread.
* `stop_window_threads` joins **all seven** QThread slots and **all nine** daemon
  thread slots a window owns. It previously joined four and no daemons.
* `_join_leaked_worker_threads` is the backstop for plain `threading.Thread`,
  mirroring the existing one for `QThread`.

**Fixture order is part of the fix.** Autouse fixtures tear down in reverse
setup order, so the GC fixture is declared **first** in order to tear down
**last** — after the join fixtures have stopped every worker. That is the one
moment when no other thread can be inside the collector. Move it and the bug
comes back.

**The detector: `tests/test_qt_teardown_fitness.py`.** It forces a full
all-generations collection every run and asserts no worker thread survived. It
exists so this can never silently regress, and **it must not be deleted or
skipped to make CI green** — a suite that stays up only because nothing looks at
its garbage is not passing, it is not looking.

| Measurement | Result |
|---|---|
| Before the fix, detector present | **3 crashes / 3 runs** |
| Before the fix, `origin/main` unmodified | **5 crashes / 5 runs** |
| After, randomized order, no coverage | **0 / 10** |
| After, randomized order, under `--cov` | **0 / 8** |

**Two "obvious" fixes that made it worse, recorded so nobody re-tries them in
isolation.** Draining `DeferredDelete` after each test, and switching
`MainWindow`'s first-run `QTimer.singleShot` to the context-object form, are both
*correct in themselves* — and each, applied alone, moved the crash rather than
removing it. Both unpin objects that were merely leaking, making them genuinely
collectable before the teardown story was ready for them to die. Unpinning is
safe only once the workers are reliably joined and the collector is controlled,
which is now true; they remain unapplied because they are no longer needed to fix
anything, not because they are wrong.

**What this means for you:**

* Don't add a `gc.collect()` to a test. The one full collection lives in the
  detector, at a point where workers are provably stopped. If you need to prove
  an object was released, prove it by refcount-deterministic destruction (see
  `tests/test_ui_auto_center.py`).
* If you add a worker thread to `MainWindow`, add its attribute name to
  `stop_window_threads` in the same change.
* If a test monkeypatches something a worker reads, **join the worker before
  undoing the patch.** A test doing this backwards is what leaked a 120-second
  `compute_digests` into dozens of later tests and produced the crash that
  finally made this visible.

### 5.v — A layout is only tested if something is *constrained* (added 2026-07-28)

The results pane drew its text on top of itself in any non-maximised window, and
it shipped through five hardware runs, an eight-reviewer whole-application audit,
and every UI test we had. Two mechanisms, one lesson — both explained in full in
[architecture.md §3.9](architecture.md):

1. **Vertical (the one the user actually saw).** A `QVBoxLayout` with less height
   than its children's minimums does not clip and does not scroll — it
   **overflows, and sibling rectangles collide**. Compounded by a pane that
   under-reports: a wrapped `QLabel`'s `minimumSizeHint` height is one line while
   its `heightForWidth` is two or three, so the pane claimed 326 px and allocated
   ~405 px. Fixed with a `QScrollArea` (v0.5.15).
2. **Horizontal.** An un-wrapped `QLabel` makes its whole single line the pane's
   minimum width, so the window refuses to narrow. Fixed with `setWordWrap`
   (v0.5.14) — and note this was *reported as the fix for the overlap and was
   not*. A stuck minimum width cannot by itself paint text over text.

**Why the suite could not see either.** Every existing test asserted on
*content* — this label says that string, this row appears — and content is
correct at every size. Nothing asserted on a *constraint*. A widget under no size
pressure cannot exhibit a size-pressure bug, and the offscreen platform hands
every widget all the room it asks for.

So, for any pane whose text is generated at runtime:

* **Constrain it, then assert.** `resize()` to a deliberately absurd size and
  assert on geometry — no shown window and no screenshot needed, just
  `layout().activate()`.
* **The vertical invariant is "no two siblings intersect".** That *is* the
  definition of text-over-text and it is exactly checkable: walk every visible
  leaf widget, group by parent, compare geometries pairwise.
* **The horizontal invariant must be font-metric independent.** Assert *the same
  vocabulary repeated N times does not change `minimumSizeHint().width()`*. Never
  an absolute pixel value, and never equality against the short-text minimum: a
  wrapped label's minimum is its longest single **word**, which is irreducible
  and font-dependent. (The first draft failed at 219 vs 188 px for this reason.)
* **Make the detector prove it can still see the bug — this one nearly shipped
  blind.** The first overlap detector walked `pane.layout()`. After the fix that
  layout holds a *single* item (the scroll area), so it compared one widget
  against nothing and reported "no overlaps" for a pane that was still broken.
  The kept version returns how many widgets it examined and **asserts that count
  is >= 8**, so a structural refactor fails the test loudly instead of quietly
  emptying it. *Any* detector that a "found nothing" result would satisfy needs a
  floor like this.
* **Verify non-vacuity by reverting the fix.** Every test here was confirmed to
  fail against the broken code first — the overlap tests naming the same two
  widget pairs the user's screenshot showed.

Generalised: *"it looks right on my screen"* is not coverage, and neither is
*"the strings are correct"*. Anywhere the program's output size is data-dependent
— a label, a column, a dialog, a tooltip — the test worth writing squeezes it and
asserts it copes.

3. **Nested scroll surfaces (v0.5.16).** The v0.5.15 scroll area made the table
   and the console *nested* scroll areas — two scrollbars 15 px apart, the wheel
   landing on whichever was under the pointer. And the obvious repair is a trap:
   **a nested scroll area with nothing left to scroll does not pass the wheel to
   its parent**, so turning the inner bar off buys a dead wheel zone. Fixed
   structurally, with tabs, so only one scroll surface is ever visible.

   The tests for it are *structural*, not cosmetic, and that is the transferable
   part: `len(live_scrollbars) <= 1` on every tab at every size, and
   `nested_scroll_areas() == []`. Both carry a **vacuity floor** — the first
   asserts it saw at least one scrollbar somewhere (otherwise "at most one" is
   trivially true), the second asserts it found at least two scroll areas to
   compare (otherwise there is nothing it could detect). Confirmed non-vacuous by
   re-introducing the nesting: the detector named all three offenders.

**A related trap from the same session: a feature with no trace cannot be
tested, or even confirmed.** Whether the desktop completion notification fired
was unanswerable from `log.txt` — the success path logged nothing and the failure
path logged at `debug`. So a shipped fix had no way to be verified on hardware:
the maintainer stepped away, and the eight-second toast was simply gone. Anything
whose only evidence is transient (a toast, a flash, a colour) must **record its
outcome, including why it was skipped**, or neither a test nor a bug report can
reach it.


### 5.t — Harness fidelity: a stand-in must not be better than the real thing (added 2026-07-29)

**The single most expensive failure class in this project's history**, and the one
ordinary tests cannot see by construction: *something that stood in for the real
thing behaved better than the real thing, so the suite was green while the product
was broken.* A test cannot notice that its own scaffolding is holding the product
up.

The case that named the rule: `MainWindow.closeEvent` never stopped the rip
`QThread`, so closing the window mid-rip destroyed a running thread and aborted
the process. It shipped for **five releases**. No test could have caught it,
because `tests/conftest.py`'s `stop_window_threads` — which every window fixture
calls — stopped `_rip_thread` itself. The harness quietly did the product's job.

Four shapes of the same mistake, all of which have actually bitten here:

| The stand-in | What it hid | Found by |
|---|---|---|
| A fixture that **cleans up** more than production does | the mid-rip abort (5 releases) | an audit, not a test |
| A test that **stubs the method under test** (`_ensure_tray_icon`) | the notification never fired (1 release) | a real-hardware log |
| A detector that can be **satisfied by finding nothing** | a broken pane reported as fixed | reverting the fix |
| An assertion on **content, never on constraint** | text painted over text | a user's screenshot |

So, the obligations:

* **Anything the harness tidies up, production must tidy up too.** Enforced
  executably by `tests/test_harness_fidelity.py`, which compares
  `stop_window_threads`'s thread list against what `closeEvent` actually passes to
  `stop_thread` and fails when the harness covers more. The harness may cover
  *fewer* things (it often builds a partial object); the asymmetry that kills is
  the harness covering for the product. **A deliberate asymmetry must be
  commented with its reason** — the daemon post-rip threads are joined by the
  harness and deliberately not by production, and that exemption is written down
  in both places.
* **Never stub the thing you are testing.** If a test replaces
  `_ensure_tray_icon`, it proves the caller calls *something*, not that the
  feature works. Drive the real path and assert no exception was logged (§5.x).
* **Every detector needs a vacuity floor.** Assert on the size of the search
  space, not only on the result: "examined ≥ N widgets", "found ≥ 2 scroll areas
  to compare", "saw ≥ 1 scrollbar somewhere". A check that a "found nothing"
  result would satisfy is not a check.
* **Prove non-vacuity by reverting the fix.** Not optional, and not a formality —
  it has caught a vacuous detector on this file *twice*, including the harness
  guard above, whose first version collected every mention of `self._rip_thread`
  and so passed against the exact bug it was written for (`_stop_rip_on_shutdown`
  *mentions* the thread in a guard clause without stopping it). Mentioning is not
  stopping. If reverting the fix leaves the suite green, the test is decoration.
* **Ask what the stand-in does that the real thing does not** — for every fixture,
  fake, stub and helper you add. Then either delete the difference or pin it.

### 5.s — A fix is a change, and changes have their own failure modes (added 2026-07-29)

Three consecutive releases each fixed a real bug and each introduced the next one:

* **v0.5.14** fixed a genuine minimum-*width* problem and was shipped as the fix
  for overlapping text, which was a *height* problem — and wrapping a label adds
  height, so it marginally worsened the symptom it was credited with fixing.
* **v0.5.15** fixed the overlap with a scroll area, which made the table and the
  console *nested* scroll surfaces — two scrollbars 15 px apart.
* **v0.5.16**'s hard-exit guard was correct, and its precondition drifted within
  the same session: one call site abandons a thread unconditionally and the
  retention list was append-only, so the guard began firing on *every* quit and
  `atexit` stopped running.

So, before calling a fix done, answer three questions in the commit message:

1. **Did I reproduce the symptom, or only explain it?** A mechanism that
   plausibly accounts for a report is not the mechanism. v0.5.14 cost a release
   to this. Ten minutes with a probe beats a confident diagnosis.
2. **What new state does this fix create, and what tests that?** A scroll area
   creates nesting. A guard creates a precondition. An `os._exit` creates a
   skipped-teardown path. Each is new behaviour and needs its own test — the
   *fix's* failure modes, not just the bug's.
3. **Is the reported symptom actually gone, or just the mechanism I named?**
   "The tests are green" and "the user's problem is solved" are different claims.
   Where only hardware can settle it, say so explicitly rather than implying the
   suite proved it.

### 5.r — A gating tool must not float (added 2026-07-29)

`ruff format` and `mypy --strict` change what they accept between minor releases.
A wide version range on a **gating** job means a routine upstream release turns CI
red with *zero* change to our code — and the failure reads as a code problem, so
the first hour goes into the wrong place. It also lets local and CI resolve
different versions and disagree about a green build, which is how a whole session
can be spent trusting the wrong numbers.

So: the two tools that gate (`ruff`, `mypy`) are pinned to the minor they were
measured against, and bumping one is a deliberate commit that re-runs the gate.
Non-gating tools (`pytest`, `hypothesis`, `pytest-cov`) stay loose — they cannot
silently redefine "correct".

Corollary for anyone reading numbers out of a tool: **record the version beside
the number.** A typing census that says "132 errors" without saying "mypy 2.3.0"
is not reproducible, because `--strict`'s flag set is version-dependent.

A related trap that cost a real false-green build: **check *which* binary the gate
ran.** `mypy` on `PATH` here was a stale global 1.19.1 while the pin is `>=2.3,<2.4`,
so a bare `mypy` invocation silently measured against the wrong tool and produced
118 phantom import errors. Invoke gating tools as `python -m <tool>` from the
activated venv, and if a number surprises you, print `--version` before believing it.

### 5.q — An exit code is only a verdict if the run reached the end (added 2026-07-29)

**The worst build outcome is not red. It is green-and-wrong**, and this project
shipped one: CI's `test` job on PR #105 exited **0** having run **76%** of the
suite. No summary line, no coverage report, `--cov-fail-under` never evaluated,
~500 tests never executed, and a genuinely failing test swallowed — all behind a
green tick that a merge was performed on.

The mechanism is worth understanding because it generalises past this repo.
`tests/conftest.py` deliberately ends the session with `os._exit(status)` (to dodge
a PySide global-teardown abort). Its comment claimed it could not mask a mid-run
abort, and that was true for a *signal* — but not for a mid-run **`os._exit(0)`**,
which is byte-identical to success from the outside. Product code supplies exactly
such a call: `platterpus.hard_exit` exists to leave the process without teardown,
and a test drove the update-relaunch path straight into it.

Three durable rules come out of it:

1. **A run must prove it finished, and the proof cannot come from inside the run.**
   A truncated process cannot report on itself — it is gone. So
   `pytest_sessionfinish` writes `.pytest-session-complete` as its very last act,
   `pytest_sessionstart` deletes any stale copy (a leftover from yesterday would
   vouch for today), and **CI fails the job when the file is missing**. Any harness
   that hard-exits, forks, or `execv`s needs an equivalent liveness artefact.
2. **A seam nobody uses is not a safety feature.** `hard_exit._exit_fn` was built
   as the injection point for exactly this and documented as "reached only when a
   test injects a recording stub" — and no test ever injected one, so the real
   `os._exit` was live in every test for five releases. Injection seams belong in
   an **autouse** fixture: the failure mode is silent, so an opt-in seam protects
   only the tests whose authors already knew about the hazard, and the test that
   needed it did not.
3. **Match the stand-in's control flow, not just its signature.** `os._exit` never
   returns, so the stand-in raises (from `BaseException`, so no stray
   `except Exception:` can swallow what the real thing cannot be caught at all).
   A recorder that *returns* lets tests execute code production can never reach —
   §5.t's rule applied to control flow rather than to cleanup.

And a diagnosability note that is really part of the same bug: CI passed `-q` on
top of the `-q` already in `addopts`, taking verbosity to `-2`, which **suppresses
pytest's `N passed` summary**. That summary is the only human-visible proof in a log
that the run reached the end, so its absence looked normal and nobody read the
truncation. Never double `-q`; if a log has no summary line, treat that as a
finding, not as formatting.

Proven by reverting, per §5.s: with the fixture removed, the guard test fails **and**
the process dies at status 0 with the sentinel absent — so both halves fire.


### 5.p — A documented capability is not a capability (added 2026-07-29)

One audit turned up four instances of the same shape in one pass, which is what makes
it a rule rather than four bugs:

| what the docs said | what the code did |
|---|---|
| `RipWorker.cancel` — "the force-stop timer escalates to a SIGKILL" | `RipHandle.cancel()` was called from **nowhere**; the escalation did not exist |
| `drive_setup_dialog` — "cancel_setup SIGTERM/SIGKILLs the subprocess" | resolved to the ABC's concrete **no-op**; the backend never overrode it |
| `cache_probe` — "the probe is off the GUI thread, **cancellable**" | `subprocess.run` hides the child; there was nothing to signal |
| `hard_exit._exit_fn` — "reached only when a test injects a recording stub" | no test ever injected one, so the real `os._exit` was live in the suite |

Every one of them read as *covered* in review, because a reviewer checking "is
cancellation handled?" finds a `cancel()` method, a docstring describing signals, and
a plausible mechanism. The prose was doing the reassuring; nothing was doing the work.

Three checks, cheap enough to be habitual:

1. **Grep for a call site before believing a method works.** A fully-implemented,
   well-documented, never-called method is dead code that reads as a feature. Where a
   method is load-bearing for safety, pin the wiring with a test (§5.x) —
   `test_rip_handle_cancel_is_actually_called_from_the_product` is the model.
2. **Check reachability, not presence.** That wiring test's first version only asserted
   a call site *existed somewhere in `src/`*, and it passed against a reverted tree —
   the call still sat inside a helper nothing called any more. A call site in dead code
   is dead code. This is the same "mentioning is not stopping" trap as §5.t, hit a
   second time in the same session, which is why it now gets its own line.
3. **Treat a concrete no-op default on an ABC as a hazard.** It is right for a
   subclass with nothing to do and a trap for one that does: the subclass inherits
   "handled" for free and no abstract-method error ever fires. If a hook can be
   load-bearing for *some* backends, test that the shipped one overrides it — asserting
   `hasattr` is worthless, since the method is present either way. Compare the
   functions: `Sub.hook is not Base.hook`.

Corollary on wording: when a docstring describes a mechanism, it is a claim about code
that exists **now**. If you are writing the intention ahead of the implementation, say
so in the docstring, or don't write it yet.


### 5.o — Enforce a rule across the codebase, not at the place it was learned (added 2026-07-29)

Every rule this project broke in one cycle was **already written down, and already
enforced — in exactly one place.** `CLAUDE.md` rule 9 is most of a page on not
destroying a live `QThread`, and `test_harness_fidelity.py` checks it thoroughly for
`MainWindow`. Nine classes create threads. One was checked. The dialog with no teardown
at all was found by a person reading code, months later.

That is the predictable shape: a bug is fixed where it was found, a test is added for
*that* instance, and the rule is written in prose for everywhere else. Prose does not
run in CI. The next instance is then a fresh discovery rather than a caught regression.

So when a bug turns out to be an instance of a rule, ask: **what is the whole set this
rule applies to, and can the test enumerate it from the source rather than from my
memory?** A sweep that derives its own targets covers code that does not exist yet,
which is the only kind of coverage that survives contact with a future contributor.

Three shapes that work here, all in `tests/test_qthread_ownership.py`:

- **Derive the population, don't list it.** Walk the AST for `self.x = QThread(...)`
  rather than hand-maintaining a list of classes. Then give it a floor
  (`>= _MIN_EXPECTED_OWNERS`) so a broken walk fails loudly instead of finding nothing
  (§5.t). Resolve through the real MRO when responsibility is split across mixins —
  a file-scoped check produces false failures, and "fixing" those by giving a mixin its
  own `closeEvent` would break the concrete class's teardown.
- **Make the exception explicit and reasoned.** A flag-only `cancel()` is sometimes
  genuinely right (a chunked download that polls per chunk; a step loop where killing
  a half-done `dnf install` is worse than waiting). Encode that as an allowlist keyed
  by class with the reason as its value, plus a staleness check that fails when an
  entry stops being needed. The forced justification is the feature — it is exactly
  what did not happen for the cancel that wore a killer's docstring for five releases.
- **Ratchet a gap you are not closing today.** Five workers expose no `cancel()` at
  all. Pinning that as a frozen set with an upper bound means the known gap is written
  down, counted, and can only shrink — the same discipline as the mypy per-module
  opt-outs (`CLAUDE.md` rule 10). A tracked gap is honest; an untracked one spreads.

The test that only covers the instance you just fixed is the cheapest test to write and
the one most likely to let the same bug back in somewhere else.


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
      `[skip changelog]` line of its own in the commit message — and *only* a
      historical-record commit: contributor/CI-facing changes are **not** exempt,
      maintainer ruling 2026-07-21). — *CLAUDE.md Critical Rule #7*
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

*Last updated for Platterpus v0.5.17.*
