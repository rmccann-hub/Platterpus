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

**A behaviour travels only if it is a callable** (added 2026-08-01). `openUrl` returns
False when no application claims a URL; the window's Help → Open logs folder checked
that bool and showed the path instead, correctly, **inline**. The rip pane's two open
buttons and the file viewer's "Open externally…" were written later, without it, and
were silently inert on any desktop with no handler for a bare `.log` — which is the
same desktop the in-app viewer exists to serve. Nobody violated a rule: the rule was a
seven-line block inside one method, and there was nothing to reuse. When the thing you
learned is a *behaviour* rather than a value, extracting it to a shared function
(`ui/external_open.py`) is part of the fix, not a later cleanup — a pattern that lives
only as a shape in one method will not be copied into the next one.


### 5.n — Record the denominator; don't recompute it (added 2026-08-01)

One mistake has now been fixed **four times** in four files: *the log's own track
list used as the population for a completeness claim.* The trust banner, the JSON
verdict, the in-progress report write, and finally the EAC-layout status report —
each compared "how many tracks verified" against `len(rip_log.tracks)`. A cancel
removes tracks from that list, so both sides of the comparison shrink together and
a 2-of-14 rip reports a clean sweep. The last instance printed **`All tracks
accurately ripped`** sixty lines below its own `INCOMPLETE RIP … 2 of 14 disc
tracks` banner, inside one SHA-256-attested document.

Four fixes, four guards, same shape. The pattern is not "add a fifth guard" — it is
that **a derived population is not a fact, and every consumer that re-derives it is
a fresh chance to derive it wrong.** The real fix is to *record* the number once,
where it is known, as data:

- `verdict.expected_track_total()` — the number the rip was **asked** for, which is
  the disc's count or fewer when the user ticked a subset. One function, so a
  deliberate 2-of-14 selection is complete and a cancelled one is not.
- `report["completeness"]` (schema v12) — that number, written into the artifact.
  It had reached the report builder for three releases *as an argument* and was
  never serialized, so the JSON's only track count remained `len(tracks)` and a
  reader had to parse English out of `verdict.message` to learn better.

When reviewing: **any expression of the form `len(<the thing we parsed>)` used as a
denominator for a claim about completeness is a defect until proven otherwise.** Ask
where the authoritative count lives, and whether the artifact states it. If the
artifact cannot answer "how many were there supposed to be?" without arithmetic on
its own contents, the next surface will get it wrong too.

Same family as §5.t's "a floor equal to the population it measures is not a floor":
both are a measurement taken against something that moves with the thing measured.


### 5.m — Two rules already existed. Neither ran. (added 2026-08-02)

A hardware batch of eight discs produced one total rip failure, and both halves
of it were already covered by written rules:

* *"Before invoking an external tool, validate that the arguments we hand it
  satisfy that tool's documented contract."* We passed cyanrip `-t 17=` for a
  16-track disc. It refused the entire rip — exit 1, two seconds, no audio.
* *"When a dependency fails or emits an error, capture its stderr/stdout and
  log it (never swallow it) so the failure is diagnosable."* cyanrip printed
  `Invalid track number 17, list has 16 tracks!`. The report's `failure_hint`
  was `null` and the user was shown **"Rip failed."**

Neither rule had a test, a sweep, or a single call site enforcing it. This is
§5.o for the third time in one week — *a rule enforced nowhere is not a rule* —
so the durable part is not "add these two checks", it is:

**A prose rule in CLAUDE.md is a statement of intent. It becomes real when
something executes it.** When you write or read a rule of the form "always X
before Y", ask immediately: *what would fail if I stopped doing X?* If the
answer is "nothing until a user hits it", the rule is decoration. Give it a
test, a sweep, or a chokepoint function — in the same change that states it.

Two concrete shapes that came out of this one:

- **Validate at the chokepoint, not at every caller.** The `-t` guard lives in
  `_metadata_args`, the single place argv is built, so it holds no matter which
  path assembled the metadata — including the medium-selection bug that
  produced the bad list in the first place, which is still unfixed. A boundary
  guard is worth having *even when you know the upstream cause*, because it
  bounds the blast radius of causes you have not found yet.
- **Range-check anything not derived from the thing you are about to act on.**
  The bad track numbers came from MusicBrainz; the constraint belongs to the
  disc. Values that cross that kind of boundary are where "usually right" hides
  until it isn't. Recorded per-flag in `docs/dependency-contracts.md`.


### 5.ab — A fixture inherits the blind spot of whatever produced it (added 2026-08-03)

The strongest-looking test in the ripper-error suite was
*"every string the ripper can print is surfaced"*, asserted against a committed
fixture of the cyanrip fork's **own machine-generated** fatal inventory. Not a
list we imagined — theirs, 88 strings, derived from their source. It was green.

It was measuring their **filter**.

Their generator passed every candidate through a hand-maintained 21-word
`FATAL_PREFIXES` allowlist (`Invalid`, `Unable`, `Failed`, …). Round 5 replaced
that with a control-flow derivation — a message is listed because its call is
followed by `return 1` / a non-zero `exit()` / `return AVERROR(...)` /
`total_error_count++` / `goto fail` / `goto end` — and the inventory went
**88 → 104**. We re-derived it independently at both pins and got 104 each time,
a strict superset with nothing lost. The allowlist had been hiding **16**.

Our pattern missed **all 13** of the matchable ones. Two are ordinary
real-hardware failures:

```
Offset is unset! To continue with an offset of 0, run with -s 0!
Device does not support changing speeds!
```

Each rendered to the user as a bare *"Rip failed."* — the exact
capture-without-surfacing failure the fixture existed to prevent, live for the
entire time the test was green.

**Why the test could not see it.** The fixture and the thing under test shared an
ancestor. Their allowlist decided which strings entered the fixture; our prefix
list decided which strings our matcher recognised; both lists were guesses at
*"what does a diagnostic look like"*, and they guessed alike. A fixture cannot
detect a blind spot it inherited.

**The rules that follow.**

1. **Ask what produced the fixture, not just who.** "Machine-generated by the
   other side" felt like strong provenance and was not the relevant question. The
   relevant question is *what filter ran between their behaviour and this file*.
   §5.u says answer from the artifact; this is its complement — **know what the
   artifact is a projection of.**
2. **Prefer a mechanism derived from the dependency's emitted text over any
   hand-maintained list of shapes, on either side.** `ripper_messages.py` now
   compiles each published `printf` format into a pattern. Nothing is a
   diagnostic because it starts with a word someone thought sounded bad.
3. **Two guesses at one classification is one too many.** Their allowlist plus our
   prefixes did not add redundancy; they added a shared failure mode that looked
   like agreement.
4. **Keep the fallback and say why.** The prefixes survive as union members, for
   builds newer than the contract — but as the *forward-tolerance* half, never as
   the completeness half. Completeness comes from the inventory.
5. **A format that cannot become a pattern is named and counted, not skipped.**
   A bare `%s` would match every line and turn progress output into fatal-error
   reports, so it is refused — and the refusal is asserted (`== ["%s"]`) so a
   second unpatternable format is a decision rather than a silent gap.

**The generalisation worth carrying:** raising a floor is not the same as fixing a
vacuous test. This test's floor was `>= 80` and 88 cleared it comfortably. The
number was never the problem — the *population* was.

### 5.aa — A gate in the wrong place is not a gate (added 2026-08-03)

The rule *"neither project releases while a handshake round is open"* was written
in `CLAUDE.md` (critical rule #12), in `docs/cyanrip-handshake.md` §7, and in the
deviation policy. What enforced it was a **unit test asserting every round in the
record was CLOSED**, and `release.yml` never called anything.

Both halves of that were wrong, and they were wrong in opposite directions:

- **It blocked the wrong thing.** A round is open *by definition* between sending
  our file and sending our verification. So the moment round 5 was opened, the
  test reddened CI for every ordinary commit on the branch — punishing the work
  the protocol exists to support.
- **It did not block the thing it was for.** Nothing on the release path ran it.
  A release dispatched with a round open would have proceeded, which is the
  single outcome the rule was written to prevent.

The fix separates the two questions:

| Question | Where it belongs | How |
|---|---|---|
| May we release right now? | the **release workflow**, before the build | `scripts/handshake.py --release-gate`, non-zero on any open round |
| Is the record well-formed? | the **test suite**, every commit | an open round may only be the **newest** one |

That second assertion is the one with lasting value, because it is the actual bug
this file was written for: round 3 was never verified back while round 4 closed,
and nothing noticed. "Open" is a legitimate state; "open behind a closed one" is
a hole in the record.

**The recurring shape.** This test's predecessor asserted *"round 4 is OPEN"* and
failed when round 4 closed — a test pinning today's state, i.e. testing the
calendar. Its replacement asserted *"nothing is OPEN"* and failed when a round
was opened. Third variant of one mistake: **assert the invariant, not the
snapshot.** Ask what must be true in *every* valid state, including states that
do not exist yet.

**Corollary, and it is the cheap check:** for any rule you believe is enforced,
**grep for the call site on the path that matters.** Rule 9 already says this
about a `cancel()` — check the call site is reachable, not merely present. It
applies identically to a workflow step, a CI job, and a pre-commit hook. A
`--release-gate` subcommand that no workflow invokes is a documented capability,
not a capability (§5.p).

### 5.u — Answer it from the artifact, not from your memory of the artifact (added 2026-08-02)

The pre-gap convention flipped **twice in one day**, and the deciding evidence
was in the repo the whole time.

1. The cyanrip fork's handshake §H2 argued that EAC's `Pre-gap length` row is
   the TOC component alone, so the fork's track-1 `Pregap length: 300`
   (lead-in 150 + declared TOC gap 150) was not EAC-comparable.
2. I accepted it, citing my own re-measurement: *"EAC reports no pre-gap for
   track 1 of the reference disc — 9 of 14 tracks, track 1 not among them."*
   Committed the change.
3. Then I opened `output_reference/EAC_flac/eac_baseline_police_classics.log`.
   It reads `Track  1 … Pre-gap length  0:00:02.00`. **10 of 14 tracks, track 1
   included.** Reverted.

The "9 of 14" was not invented — it was a correct count of **`INDEX 00` lines in
the cue**, where track 1 *cannot* appear because no addressable sector exists
before LSN 0. A true measurement of one artifact, quoted as evidence about a
different one, and it survived a round-trip through two projects because both
sides were reasoning about what EAC does rather than reading what EAC wrote.

Three things generalise:

- **A remembered measurement is not a measurement.** It has no provenance you
  can re-check and it silently drops the qualifier — here, *which file*. If you
  are about to cite a number you measured earlier, re-run the measurement or
  cite the command. The re-run cost ten seconds.
- **Name the artifact in the claim.** "EAC reports N" is unfalsifiable; "EAC's
  *log* reports N, its *cue* reports M, and they differ on track 1 by
  construction" is checkable and turned out to be the whole answer.
- **A correction from the other side deserves the same scrutiny as a claim.**
  §H2 was well-argued and wrong, and I applied it faster than I had applied any
  finding of my own, precisely because it was a correction. The handshake's
  value is the *check*, not the direction of travel.

The durable artifact is `tests/test_eac_pregap_convention.py`, which does not
state the convention at all — it **derives** it from the committed log and cue
every run: that EAC's fraction is truncated hundredths (decided by the single
row where truncation and rounding disagree), that the row for track *n* > 1 is
`start − INDEX 00`, that track 1's is the lead-in plus any declared gap, and
that our renderer reproduces all ten real rows byte-for-byte. It carries floors
(`len(toc) == 14`, `≥ 10 rows`, `≥ 5 distinct values`, `≥ 1 row that
distinguishes truncation from rounding`) so a swapped or truncated baseline
fails loudly instead of passing vacuously.

**When a committed artifact can settle a question, the test should read the
artifact.** Anything else pins your belief about the artifact.

### §5.ac — Two witnesses that share an ancestor are one witness

*Handshake round 6b, 2026-08-03. The cyanrip fork's finding, generalised, because
we have now hit this shape from three directions and only had a rule for one.*

For a whole session the fork's audio-safety harness compared its build against
upstream `958e1ad`: 55 per-track checksum lines and 11 decoded-PCM hashes,
**identical**, re-run after every commit. Every word of that was true. Both
builds were also returning **99.7% silence** for any disc-image rip above `-P 0`,
because the defect was inherited from upstream — and reporting
`Ripping errors: 0` while doing it. One `cmp` against the fixture `.bin` found in
a second what a session of cross-build diffing could not.

Three checks reported success, each for a different reason, and each is a shape
already written down in this file:

1. **Equality between two implementations that share a parent.** They share its
   bugs, so agreement is expected regardless of correctness. *"Identical to the
   other implementation"* is not *"correct"*.
2. **The suite never ran the broken path.** Their `rip()` helper passed `-P 0` on
   every scenario; the comparison harness omitted it. Suite and harness exercised
   *different* code, and nobody ran the one that was broken. This is §5.o's
   "enforce a rule across the codebase, not at the place it was learned" wearing
   different clothes.
3. **Silence compares equal to silence.** Every check was an equality test
   between two things that were both wrong, and none asserted the content was
   non-trivial.

**The rules, all three of which are cheap:**

- **Assert against the source artifact, not against another run.** The input
  file, the pressed disc, the upstream document — something that did not come out
  of the code under test. A comparison against a second run of anything sharing
  code with the first is a consistency check, not a correctness check.
- **Add a non-triviality floor to every equality assertion.** "Equal *and* not
  mostly zeros", "equal *and* at least N distinct values", "equal *and* the file
  is not empty". Same family as §5's standing "can this check be satisfied by
  finding nothing?" — here the answer was yes, twice, and the emptiness was in
  the *data* rather than in the result set.
- **Make the harness run the product's default.** Where a helper pins a setting
  the product does not pin, that setting is now untested by construction, and the
  helper is *safer than the product* — which §5's stand-in question is about. Pin
  it in the test with a comment, or run both.

Our exposure was luck, and it is worth recording as luck rather than as
diligence: round 5's affected reference never entered our fixtures because
`docs/handshake/verified/round-5.md` §4b had asked them to *keep the previous
reference rather than replace it*, on coverage grounds. The right call for the
wrong reason. What is now deliberate: `tests/test_fork_golden_reference_r6b.py`
asserts `-P 0` appears in the committed reference's own `Invoked as:` line, so a
future fixture generated without it fails at the point of entry instead of
parsing perfectly and meaning nothing.

### §5.ad — A check that passes for the wrong reason

*Handshake round 6, 2026-08-03. Found in `scripts/handshake.py`, the gate that
enforces the handshake protocol — the one detector in the project that had never
been asked §5's own question.*

`--check` validates a received handshake file against ten required sections,
keyed on the section letter. On the fork's round-6 file it reported **one**
problem. There were **three**, and a fourth section passed on a coincidence:

| Section | Reported | Truth |
|---|---|---|
| §J (Questions back) | MISSING | correct |
| §G (Revert-proof) | present | **absent** — "revert" appears zero times; a section was lettered `## G. Asks back` |
| §B (Answers) | present | **absent** — none of `measured` / `read from source` / `unverified` appears |
| §I (Provider contract) | present | present, but credited to the prose *"I wrote, of your continuation-line sweep:"* |

Two distinct defects, and the second is the more interesting:

- **A bare letter at the start of a line is not a heading.** Every required
  section is single-lettered, and English sentences begin with "A ", "I ", "We ".
  The matcher accepted an unmarked letter, so ordinary prose satisfied structure.
- **A letter validates the label, not the subject.** A section the other side
  letters `G` for their own reasons satisfies "§G" while covering something else
  entirely.

**§I is the one to remember, because its verdict was right.** The provider
contract genuinely was in the file. A check that returns the correct answer for
an unrelated reason is worse than one that fails: a failure gets investigated, a
pass gets *cited* — and this one had been cited, in a verification file, as
evidence the round was complete.

**The rule: where a check matches on a label, make it also require the subject.**
The label answers "did they name it", the content answers "did they write it",
and only the pair is a check. Both halves are now in `check_inbound`, and the
regression test reads the committed round-6 file rather than a synthetic one
(§5.u) — the artifact that produced the finding is the artifact that proves the
fix.

A second-order lesson from fixing the tests: `_complete_inbound` built its
"positive control" from `"x" * 300`, which under the new rule is no longer a
complete file — correctly, because 300 characters of filler under a §G heading is
not a revert-proof section. **A fixture that pads with filler teaches the product
that filler counts.** It now pads with each section's own subject.

### §5.ae — A gate that reads presence instead of decision

*Handshake round 7, 2026-08-03. The same file as §5.ad, one round later, and the
reason this gets its own section rather than a line in that one: the fix to §5.ad
was applied to `--check`, and this defect was in `--status`. **The lesson had been
learned in the function next door.***

`round_status` reported a round CLOSED when three files existed —
`outbound/round-N.md`, `inbound/round-N.md`, `verified/round-N.md` — and
`--release-gate` is a thin wrapper over it. Round 7's verification file exists and
declares **`**HOLD on d5d12ec`**: a deliberate mid-round lap, at the fork's own
request. `--status` reported:

```
round-7: sent=yes returned=yes verified=yes  -> CLOSED
handshake: every round is closed — release allowed
```

Every word of that is derived correctly from what it measured. It measured the
wrong thing. **A release would have been permitted with the round open**, which is
the one thing the deviation policy names explicitly.

Three properties the fix needed, each of which is its own way to get this wrong
again:

1. **Read the decision, not the artifact.** `state = CLOSED` now requires
   `verdict == "GO"`.
2. **Fail closed on silence.** A verification with no verdict is not a close. The
   tempting shortcut — *treat a missing verdict as GO so the old rounds still
   pass* — reintroduces the whole defect through the fallback. Rounds 1–3 are
   grandfathered **by number**, in a `RETROSPECTIVE_ROUNDS` frozenset a test pins
   to exactly `{1, 2, 3}`, because otherwise "add the round to the exemption list"
   is a one-line close.
3. **Prose about a verdict is not a verdict.** Round 7's opening paragraph says
   *"not a closing GO"*. A matcher scanning anywhere in the text for `GO` reads
   that file as GO — closing the round off a sentence that says the opposite,
   which is §5.ad's §I failure arriving through a different door. The marker is
   anchored to a line start, and `**GONE**` / `**HOLDINGS**` are asserted not to
   match.

**The rule: when a gate's input is a document that states a decision, the gate
must read the decision.** File presence answers *"did someone do the step"*;
only the content answers *"and what did they conclude"*. The two diverge exactly
when the answer is "not yet" — the case the gate exists for.

And the meta-lesson, which is why §5.ad and §5.ae are adjacent: **fixing a
detector's flaw at the call site where you found it leaves the flaw everywhere
else in the same file.** This is CLAUDE.md rule 9's *"enforce a rule across the
codebase, not at the place it was learned"* at the smallest possible scale — two
functions, one module, one round apart.

### §5.af — A promise of completeness that nothing sweeps

*Documentation-currency audit, 2026-08-03. Three maps, all three declared
canonical in prose, all three expired.*

A map is only ever wrong **by omission**, and an omission is invisible in a diff.
Nobody reviews a file for what is not in it. So a document that promises
completeness — *"the canonical annotated index"*, *"one paragraph per module"* —
is a test waiting to be written, and until it is written the promise decays at
exactly the rate the codebase grows.

| Promise | Where | What had gone missing |
|---|---|---|
| *"the canonical annotated index"* | `CLAUDE.md` → `docs/README.md` | `cyanrip-consumer-contract.md`; and `docs/handshake/` — 24 files of binding correspondence — linked from nowhere |
| *"one paragraph per module, no more"* | `PLANNING.md` §2 | **19 of 122** modules, including two `CLAUDE.md`'s own rules name by name |
| the round-by-round record | `docs/handshake/README.md` | every round after the 4th, plus it taught a closing rule that had been superseded |

**The first one is the instructive one, because the fix had already been
attempted — in prose.** `CLAUDE.md` carries a parenthetical saying the list
*"can't drift from it again; it did once."* That is a comment where a check
belongs, and it failed within the cycle.

Three properties a completeness gate needs, each learned from getting one wrong
while writing these:

1. **Require the unit the promise makes, not a weaker one.** `docs/README.md` is
   an *annotated* index, so the gate requires a **table row with a description**,
   not a mention. A document named once in another entry's prose has a resolving
   link — `test_doc_links.py` is perfectly happy — and is still lost to a reader.
   Matching on mentions would have passed with the gap present.
2. **Derive the expected set from the filesystem**, never from a list in the test.
   A hand-kept list is a second map, and it drifts in the same way for the same
   reason.
3. **Scope the converse check narrowly, or it fails on correct prose.** *"No entry
   for a file that is gone"* is right; *"every filename mentioned resolves"* is
   not — `docs/README.md` rightly says *"(Absorbed the former `best-practices.md`)"*
   and `PLANNING.md` rightly discusses `setup.py` as something we do **not** use.
   My first version failed on both, and a gate that fires on correct writing gets
   switched off.

**And the reverse-direction rule for the tests themselves:** a skip-list built for
one question is the wrong input to a different one. `_source_modules()` excludes
`__init__.py` because a coverage sweep should not demand a paragraph for it —
reusing that filter in the *phantom* check made the test report `PLANNING.md`'s
(correct) `__init__.py` entry as describing a deleted module.

### §5.am — A conformance table is run, not read

*Handshake round 7 lap 5, 2026-08-04.*

The cyanrip fork's shared protocol carries a **14-row table** of cases a conforming
gate must refuse, plus one it must allow. We had already written our gate to the
four *principles* those rows express, revert-proven it, and reported it as done.
Turning the table into fourteen tests found a defect immediately:

> **Row 12 — "no round files at all → refuse; an empty record is not agreement."**
> Ours printed *"every round is closed — release allowed"*.

The mechanism is worth stating because it is so cheap: `round_status()` returned a
bare `"no handshake rounds recorded"` line, the gate decided by looking for lines
ending in `OPEN`, that line does not end in `OPEN`, therefore nothing was open. **A
gate satisfied by finding nothing, in the gate whose entire job is not being
satisfied by nothing.**

**Reading the table would not have found it.** Every row read as something we
already did, because at the level of principle we did. The gap was in a *case*.

Two rules follow:

1. **Where a spec offers concrete cases, write one test per case** — in the spec's
   order, named for its row, so a divergence between two implementations can be
   cited rather than argued. A floor test asserting every row has a test keeps that
   true as the spec grows; a skipped row is a divergence nobody can see.
2. **Assert the ALLOW row first.** A gate that can never say yes is a wall, and it
   passes every refusal row in the table. Putting the positive case at the top of
   the file is how that stays honest instead of remembered. (Their observation, and
   it is the reason the table has that row at all.)

**The companion finding, same lap: a format's own documentation is the likeliest
place to trip its parser.** Round files illustrate the header format in fenced
blocks; both projects' gates read those illustrations as declarations. Theirs
compiled an illustrated field into a binary as a fact; ours resolved correctly only
because the illustrated value happened to match the real one — and our suite
asserted the wrong behaviour outright, with a confident comment. **A declaration is
what a file states, never what it quotes.** Three bait shapes exist (indented,
prose, fenced) and each project had independently found two of the three.

### §5.ah — A detector's input can be pinned by design, and then it detects the design

*Real hardware, 2026-08-05, b8 + cyanrip `f5e11ba`, the Police baseline disc.*

Two user-visible bugs, one cause, and the cause is not in either detector — it is in
the **signal both were reading**.

The stall detector watched the album progress fraction: no meaningful step for 180 s
means the drive is wedged on a scratch. The ETA divided the remaining fraction by
that same fraction's recent rate. Both are sound. But `_overall_from_track` maps a
track's progress into a span of the album, and `_bump_overall` refuses to let the bar
regress — so **a secure re-read, which reads the same track again, pins the album
fraction for its entire duration by construction.** Ten minutes of it, twice, in one
rip. The artifacts say it plainly, in the same seconds:

```
01:38:57 WARNING rip stalled: no forward progress for 3m 2s at 21.7% (track 3)
                 — the drive is stuck on a hard-to-read spot
01:38:50 DEBUG   cyanrip │ Ripping track 3, progress - 52.29%
01:38:55 DEBUG   cyanrip │ Ripping track 3, progress - 54.50%
```

and the ETA, off the same pinned fraction: 54m → 1h5m → 1h50m → 3h15m → **5h40m in
70 seconds**, on a disc with 22 minutes to go. So: a healthy disc reported as
scratched, and a countdown that quintupled while nothing was wrong.

Four lessons, each of which cost something:

1. **Ask what pins your input, not just what your logic does with it.** Both
   detectors were reviewed, tested and correct. Neither review asked *"is there a
   normal, designed condition under which this input stops changing while the world
   does not?"* — and the answer was a headline feature of the product.
2. **A monotonic display value is not a measurement.** `_bump_overall` exists for a
   real UX reason (a bar must not go backwards). The moment a *display* value became
   the input to two *inferences*, the clamp stopped being cosmetic. Derive
   measurements from the raw signal; clamp only on the way to the screen.
3. **The fix for "my signal went quiet" is a second signal, not an exemption.** The
   tempting fix — suppress the stall detector during a re-read — passes the test that
   the false alarm is gone and silently reintroduces the hours-long undetected hang
   the detector was written for. Taking cyanrip's own per-operation percentage as a
   second witness and firing only when *neither* has moved makes the detector
   strictly **more** sensitive. `test_a_genuinely_wedged_drive_is_still_reported_stalled`
   is the converse guard, and it exists because the exemption would have passed
   without it.
4. **A trace that goes quiet during the interesting part is not a trace.** Only the
   branch that made a fresh rate measurement recorded an `eta_trace` sample — the
   hold and stall paths returned early, with a comment reasoning that "holding is the
   absence of a computation." That reasoning cost the analysis of this bug: the
   shipped trace has a **541-second and a 400-second hole**, both landing exactly on
   the minutes the estimator was misbehaving, so its peak reading could not be
   explained from the artifact meant to explain it. Every branch records now, each
   labelled with a `state` — the labelling is what keeps a re-shown estimate from
   reading as a measurement, which is the honest version of what the early return was
   trying to protect.

**And a floor caught a floor.** The regression test for the rate window asserts that
the discarded points would still have been *inside* the 90-second window — otherwise
ordinary pruning, not the fix, explains their absence. Written first as
`clock.now - 600.0`, which is not the elapsed time at all (the fake clock starts at
10 000), it compared ~8800 against a 90-second bound and could never fail. It fired
only because the sibling assertion made the arithmetic visible. Compute a derived
quantity **once, in a named helper**, especially inside a check whose whole purpose is
to not be vacuous.

### §5.ai — A convention is a checker, and the checker sweeps the surface

*The Settings dialog, 2026-08-06. Raised by a person reading a screen, not by any test.*

Five dropdowns in one dialog offered their options five different ways: an em dash in
one, a lowercase parenthetical in another, a bare `Embed in FLAC` with no descriptor at
all, `WavPack (.wv)` and `Fixed speed (advanced)` using the same round bracket for two
unrelated jobs, and two naming presets separated by **two spaces**. No individual label
was wrong. The *set* was, and only a human comparing them noticed — which is exactly the
class of defect no assertion in the suite was positioned to see.

**Two things generalise past dropdown text.**

**1. The unit of enforcement is the constructed surface, not a table of known items.**
The obvious test is a list: *these are the option labels, and each conforms.* That test
is correct on the day it is written and wrong the first time somebody adds a sixth combo
— **wrong by omission, which nobody reviews for** (the same shape as §5.af, arriving
through the UI instead of through a document). So `tests/test_option_labels.py` walks
`vars(dialog)` for every `QComboBox` the real dialog owns and checks every item of each,
with floors (`>= 5` combos, `>= 18` labels) so *finding nothing* cannot read as *all
conformed*.

**2. A checker for human-readable text is unusually easy to satisfy with the wrong
thing**, and three attempts proved it in one sitting:

- **A blanket skip.** "Ignore any word containing a bracket" makes
  `(accuraterip + ctdb)` pass. Fix: strip the brackets and check the words inside — the
  bracket is punctuation, not an exemption.
- **A first-letter check.** `word[0].isupper()` passes `Best-quality`. Fix: split
  hyphenated compounds and check each half.
- **A free-text field.** An unconstrained trailing `[Qualifier]` is just a second
  descriptor, so the inconsistency comes back through the annotation. Fix: close the set.

**Non-vacuity is asserted, not assumed.** A separate test requires all **19** verbatim
pre-rename labels to *fail* the checker. Without it, a future change that loosened the
checker until it accepted anything would leave the sweep green — the sweep proves the
labels match the checker, and only this pins that the checker means something. The
strings are pasted rather than derived from git history for the same reason a fixture
should not be generated by the thing it tests (§5.ab).

**And an exemption written down is not the same as a rule not applied.** The drive
picker's `(no drives found)` is a placeholder, not an option; `is_placeholder()` names
that in code and a test asserts the placeholder is *recognised* while still *failing* the
label check — because implementing the exemption as "the checker accepts parenthesised
strings" would have quietly exempted every badly-named label too.

### §5.aj — The runner is a stand-in too, and the permissive one is the one you type

*The v0.6.12 release CI, 2026-08-17. Found by CI, which is the only thing that was
running the real invocation.*

`tests/test_round_digest.py` opened with `from scripts import round_digest as rd`. It
collected cleanly every time it was run locally and raised `ModuleNotFoundError: No
module named 'scripts'` on all four CI Pythons, at the **collection** stage — so the
release branch's `test` job was red in 16 seconds with the other five jobs green.

The mechanism is one line of CPython behaviour: `python -m pytest` prepends the cwd to
`sys.path`, the `pytest` console script prepends nothing. At the repo root that makes
every non-package directory here — `scripts/`, `build/` — an importable implicit
namespace package under the first runner and invisible under the second. Reproduce CI's
import path locally with **`PYTHONSAFEPATH=1 python -m pytest`**.

**Why this belongs in §5.t's family rather than beside it.** §5.t is about a *fixture*
that does the product's job, so the suite is green while the product is broken. This is
the same shape one level out: the **invocation** is a stand-in for CI's, and it is the
more permissive of the two. That asymmetry is what makes it dangerous — the permissive
runner is the one a human types, so the defect is invisible until CI or a contributor
with a different habit runs it. Ask of a local green run the same question §5.t asks of
a fixture: *what does my stand-in do that the real thing does not?*

**The guard is a sweep, not a fix to one file** (§5.o). `test_harness_fidelity.py`
derives the suspect set from the filesystem — every repo-root directory with no
`__init__.py` — and AST-walks every `tests/*.py` for a top-level import of one, rather
than hard-coding `scripts`. Floors on both sides, because either half can go vacuous
independently: `>= 40` test modules examined so a broken glob cannot read as *nothing
imports badly*, and a converse test requiring `>= 5` modules to still load a script by
file location, so the check cannot pass trivially on the day the established idiom
erodes. Verified by reverting the import and watching the guard name
`test_round_digest.py:23`, with the revert asserted to have landed before the run was
believed (§5.s).

**The near-miss worth recording.** The suite had already been run green under the fixed
import — under `python -m pytest`. Had the guard not been written as a sweep, the same
command would have gone on vouching for the same blind spot.

### §5.al — Two surfaces answering one question by different keys will disagree

*The one-click ripper install, 2026-08-18. Found by adversarial review of a diff that
had already been through a full suite, a typecheck and ten green CI checks.*

Whether a cyanrip build is *"one our record approves"* was computed twice:

| surface | key | when it runs |
|---|---|---|
| `ripper_offer.evaluate_offer` | the manifest's **round label** — `round_closed and handshake_round <= APPROVED_BY_ROUND` | when we offer the install |
| `handshake_approval.approve_ripper` | the **build tag** — `platterpus-fork-g<FORK_PIN>` | on every rip, into the report, the log and the EAC export |

Both readings are defensible in isolation. They are not the same question **in this
project**, and the record says so out loud: `APPROVED_BY_ROUND` names the newest closed
round that approved *the pin we install*, and rounds 9, 10 and 11 each closed against a
commit that is not `FORK_PIN`, because reviewing a pin and installing it are separate
acts. So every head the fork labelled with a round we had closed was presented as
approved, offered on one click with *"nothing to weigh"*, and then reported `unapproved`
by the very next rip. Four real cases reproduced it — including `422d12a`, which the
fork had **withdrawn** for failing its own tests.

**What makes this class dangerous is that neither surface is wrong on its own.** There
is no assertion to add to either one; a test of the offer passes, a test of the approval
passes, and the defect lives strictly in the *relation*. The suite was green.

Three things follow, in order of how much they buy:

1. **One predicate, N callers — and the caller delegates rather than restating.** The
   fix is `handshake_approval.approves_commit`, which `_tag_is_approved` backs and
   `approve_ripper` also calls. Not "both compute the same thing"; literally the same
   function. `ripper_offer._approves_commit` is a one-line pass-through that exists so a
   future edit has to *replace a call* rather than tweak an expression.
2. **Where the two could differ, the one that reaches an archival record wins.** The
   shared predicate uses exact tag equality, not the prefix-tolerant `same_commit`,
   because a prefix match would let the offer promise an approval the rip-time check
   must refuse. Pick the stricter key deliberately and say why.
3. **Test the relation, not the two sides.** The regression test asserts
   `offer.auto_installable is (approve_ripper(banner).verdict == "approved")` for the
   same build — a property no test of either module alone can express.

**The smell to grep for:** a comparison against a *label* the other side supplies (a
round number, a channel name, a version string, a `round_closed` flag) standing in for
a comparison against the *identity* our own record keyed on. Ask: *if the other project
relabelled this without changing the artifact, would my answer change?* If yes, the
label is not the key.

### §5.ak — A bug can be masked by a smaller bug, so a fix makes new states reachable

*The ripper offer, 2026-08-18. Found by answering "what new state does this fix
create?" in a commit message, which is the only reason it was found at all.*

`_up_to_date_offer` rendered the **channel head's** version string against the
**installed** commit and described it as *"the newest published on the stable
channel"*. Every field in that sentence was read from a real object; the sentence was
false. It reports one build's version number as another build's identity.

**It was unreachable, and it was unreachable for the wrong reason.** Getting there
requires a build that is ahead of the channel being asked about — a beta build while
Settings say stable. Placing such a build requires knowing its release sequence, and
the sequence came only from a hand-maintained map in this repo, which by construction
cannot list a release newer than itself. So the code could never *get* to the state
where it would have lied. The larger defect (refusing to place a newer release at all
— the thing a user actually reported) was **hiding** the smaller one.

That is the generalisable part, and it inverts the usual intuition about risk:

> **A correctness fix expands the state space.** States the old bug made unreachable
> become reachable, and nothing has ever executed them. They are not regressions
> introduced by the fix — they are pre-existing defects the fix *exposes*, which is
> worse in one specific way: they arrive already believed-in, in code that has been
> in the tree for weeks and has a passing test suite behind it.

So the question `CLAUDE.md` asks — *what new state does this fix create, and what
tests that?* — is not only about state the fix **adds** (a cache, a guard, a
precondition). It is also about state the fix **unblocks**. Ask, of any fix that makes
a function answer where it used to decline: *what does the code downstream do with the
answers it never used to receive?* Then go and read those branches, because no test
covers them — a branch nothing could reach is a branch nobody wrote a case for.

**The check.** `test_a_build_ahead_of_the_channel_does_not_borrow_the_heads_version`
asserts the negative directly — `f"{stable_row.version} (abc1234)" not in detail` —
rather than asserting the new wording, because the wording is ours to change and the
mis-pairing is the defect. It sits beside a control test
(`test_without_the_manifest_source_that_build_is_a_mismatch`) that passes with the fix
reverted, so the pair distinguishes "the new source works" from "the suite is green".

### 5.ag — An implemented capability is not a capability either (added 2026-08-06)

§5.p is about a capability the docs claimed and the code lacked. This is the step
before it: the code had the capability and **nothing could reach it**.

`src/platterpus/uiscript/` — the unattended-batch scripting subsystem the
maintainer asked for by name — shipped complete: a parser that never raises, a
closed vocabulary table, a `QTimer` runner, a transcript renderer, and 59 passing
tests. It shipped with **no menu item, no dialog and no CLI flag**. The whole
detection is one command:

```sh
grep -rn 'uiscript' src/ --exclude-dir=uiscript      # -> nothing
```

Two things make this worse than an ordinary gap. First, the **tests were green**,
because a subsystem's own tests import it directly — they measure the subsystem,
never its reachability. Second, the **changelog announced it**, so every later
reader (including the next session) had a written statement that the feature
existed, and no reason to check.

The same sweep found the second instance immediately: `rig_session.sh`, the
unattended hardware harness, lived in `scripts/` — present in the git repository
and in nothing that ships. The person who runs it has an AppImage, and the rig
sheet's instruction was, verbatim, `bash ~/path/to/Platterpus/scripts/rig_session.sh`.
It had a smoke test asserting the script's *content* and nothing asserting a
built Platterpus could find it.

**What to do about it, concretely:**

- **For a new package**, assert an import from outside it. If nothing outside
  imports it, it is not wired.
- **For a shipped data file**, assert against the *packaging metadata*, not the
  filesystem — `tests/test_rig_session_reachable.py` reads
  `pyproject.toml`'s `[tool.setuptools.package-data]`, because a file that exists
  in a checkout and is absent from the wheel is exactly the failure, and a
  filesystem check cannot tell those apart.
- **For a user-facing route**, assert it appears where the user would look —
  `--help` text, a menu action, a Settings row.
- **Give the assertion a floor.** `assert "--rig-session" in help_text` passes
  against an empty string under a broken capture, so assert the capture is
  non-trivial first.

**The generalisation, and it is the useful part:** this project's checks are good
at asking *"is this correct?"* and had nothing asking *"can anyone get to it?"*
Both a documented capability and an implemented one can be unreachable, and
unreachable is indistinguishable from absent to the only person who matters.

### 5.an — A gate that picks its subject by chance is not a gate (added 2026-08-06)

§5.aa is *a gate in the wrong place*. This is a gate in the right place, asking
the right question, **of a document chosen by directory iteration order**.

`tests/test_fork_source.py::test_the_pin_is_the_one_the_newest_closed_handshake_round_verified`
stops the setup wizard building a cyanrip commit no closed handshake round
approved — one of the load-bearing checks in the whole seam. It read:

```python
verified = sorted(dir.glob("round-*.md"),
                  key=lambda p: int(re.search(r"round-(\d+)", p.name).group(1)))
newest = verified[-1]
```

Every `round-07-lap-NN.md` file yields the same key, `7`. Python's sort is
stable, so the tie is broken by `Path.glob`'s order, which is `os.scandir`'s,
which is the filesystem's. **"The newest verification" was whichever lap the
directory happened to list last.** It named the right commit for eight
consecutive laps and then a ninth was added and it did not — and the only reason
anyone looked is that CI went red.

Three things to take from it:

- **A non-total sort key makes "the newest" a coin flip.** The shared
  `sort_key` in `scripts/handshake.py` already existed, is `(round, lap, stem)`,
  and says in its own docstring that a non-total key *"makes 'the newest file'
  depend on directory iteration order, which is the class of thing that decides a
  release gate differently on two machines."* The test imported that module for
  something else and then hand-rolled its own ordering anyway. **Sharing a
  definition only helps if the caller uses it.**
- **Read the test's name as a specification.** It said *newest CLOSED round*; the
  code said *newest file*. Those differ exactly when a round is open — which is
  the only time the check matters, because an open round's laps are not
  approvals. The name was right and had been right the whole time.
- **A check that has been green for months is not thereby correct.** This one had
  never once evaluated the document it claimed to. Give a gate a companion test
  that asserts *which subject it examined*, not only what it concluded — the
  conclusion can be right for a reason that will not survive the next file.

### §5.ao — A number read from a run still in flight is the fast tail, not the range

*The CI apt timeout, 2026-08-18. Caught by the run finishing before the commit was
pushed, which is luck, not method.*

Four matrix legs of one commit ran the same `apt-get` step. Two finished quickly and
two were still going, so the timeout for a new bound was calibrated against the two
observations available: **13s and 32s**. 75s per call looked generous — nearly 2.5×
the slower of them.

When the run completed, the four durations were **13s, 32s, 73s and 103s, every one a
success.** A 75s per-call bound sits *inside* the healthy range. The fix written to
stop a 20-minute stall would have begun killing a slow-but-working install, and in the
bad case failed a step that had been passing.

**The sampling error is structural, not careless.** Jobs that finish first finish first
*because* they are fast. Reading an in-flight population therefore reads its fast tail
with certainty — the slow observations are precisely the ones still missing, and their
absence is what makes the sample look tight. The error is systematically in one
direction, and a bound derived that way is always too tight, never too loose.

This is `CLAUDE.md`'s *"did I verify this where it could have failed?"* arriving from a
new direction. There the conditions guaranteed the invariant; here the conditions
guaranteed the *sample*.

What to do instead:

- **Close the population before quoting it.** Wait for the run, the matrix, the batch.
  If you cannot, state the qualifier in the number itself — *"≥73s across the 2 of 4
  legs that had finished"* is honest and unusable as a bound, which is the point.
- **Ask which observations are still missing, and whether they are missing at
  random.** In any race-to-finish population they are not: the missing ones are the
  extreme ones.
- **Separate the two distributions you are choosing between.** Healthy ran 13–103s;
  stalled ran 1200s+. A bound belongs in the gap, and the gap is only visible once both
  ends are measured. Write the arithmetic into the comment so the next reader can
  re-check it against a later sample rather than re-deriving it.
- **Record the count, not just the value.** "240s, from 4 of 4 legs (13/32/73/103s)"
  carries its own provenance; "240s" does not, and silently drops the qualifier the
  first time it is quoted onward — the same decay as §5.u.

### §5.ap — Asking for a thing is not having it: the asynchronous seam a step can outrun

*The rig run of 2026-08-18, app 0.6.16. `pass=50 fail=8`, and all eight are one line.*

`pick-release` chose a MusicBrainz release, called `dialog.accept()`, and recorded
**PASS**. The next step, `expect-tracks 3`, reported *"found 0"* — **124 ms later**.
Then `select-tracks` found nothing to select, `rip` found the Start button disabled,
and `cancel-rip` found no rip running. Four failures, twice, in two sections.

Nothing was broken about the release picking. `MainWindow._fetch_release_detail`
*emits* to the MusicBrainz worker thread rather than calling it, so accepting the
dialog is the moment the work is **requested**, not the moment it is **done**. The
tracks arrived a network round-trip later and were on screen the whole time the
transcript said they were absent — confirmed from the operator's own screenshots,
which show a full track table and an enabled "Start rip".

**Three things to take from it, in order of how much they generalise.**

**1. A verb that ends at a request has invented its own definition of done.** The
predicate `_try_pick_release` was written as *"did the dialog close?"*, which is a fact
about the dialog. The step's actual claim is *"the release is applied"*, which is a
fact about the window. Whenever those two differ by a thread hop, the step passes
early and every step after it inherits a state that has not arrived. Ask of any step
that drives an async subsystem: **what would still be false one millisecond after I
return True?**

**2. The asymmetry is the tell, and it was in the docstring.** That same method's
*other* branch — the one for a disc with only one candidate, where no picker appears —
already refused to pass on an empty track table, and its docstring explained why at
length: *"a picker that never appears is a PASS, and that needs justifying… it is only
accepted alongside positive evidence."* The rule was written down, argued for, and
applied to one of the two branches. This is §5.o (*enforce a rule across the codebase,
not at the place it was learned*) at its smallest possible scale: **the two halves of
one function.** When a method takes a principled stance in one branch, read the other
branch and ask whether the stance holds there too — it usually should, and the branch
that skipped it is where the bug is.

**3. The fixture was already in the post-fetch state, so no test could see it.** Every
existing `pick-release` test used `_TrackTable()`, which constructs itself with **14
rows**. The stand-in was permanently in the condition the product reaches only after a
successful network fetch, so the empty→full transition — the entire subject — did not
exist in the harness. This is §5.aj and `CLAUDE.md`'s *what does my stand-in do that
the real thing does not?*, and the answer here is unusually blunt: **it started at the
end.** The regression test uses a table that starts empty and is filled by the test on
cue, which is the only shape that can express the race.

**Method note.** The wrong diagnosis was reached first and it looked solid: the disc
panel read *"4 matches found — pick one"* in every snapshot through the end of the run,
which reads exactly like a release choice that never applied. It was a second, separate
defect — the panel's label was never updated after a pick — and believing it would have
sent the fix into the MusicBrainz layer. The screenshots settled it. *Two symptoms with
one plausible common cause are still two symptoms* (`CLAUDE.md`: *did I reproduce the
symptom, or only explain it?*).

### §5.aq — One field, two opposite requirements: the value another feature is *supposed* to destroy

*Rig run of 2026-08-19, app 0.6.17. Two failed steps, and the damage was in the
file system rather than the transcript.*

`(ripper)` expands a script's album title to the installed ripper's build tag, so a
two-pass session writes two folders instead of pass 2 landing on pass 1. It read
`ScriptRunner._last_cyanrip_output`. That field has a **second, deliberate
requirement**, added two weeks earlier for a good reason: it is **invalidated on
every new `cyanrip` step** — a refusal, a timeout, a different command — so
`expect-cyanrip` / `expect-exit` can never grade a subject two commands old (§5.an).

Both requirements are correct. They are incompatible on one field, and the
assertion half won by being written second. Section C's cache probe timed out, the
timeout path wrote its own error text into the slot, and both `album … (ripper)`
steps in section D and E failed with *"no build tag has been captured yet"* — twenty
minutes after section A had captured it.

**The consequence was not the two failed steps.** With the placeholder refused, the
rip used the **default album title**, so section D's cancelled rip and section E's
recovery rip both targeted the disc's real album folder. That is what produced the
overwrite prompt the maintainer reported as *"that doesn't seem right"*: the dialog
was correct, the folder collision was real, and the cause was three sections
upstream in a field nobody had connected to it.

**The question this adds** — a sibling to `CLAUDE.md`'s *what pins my input?*, which
is about an input frozen by design:

> **What else WRITES to the field I am reading, and does it write for a reason I
> would not want to override?**

If the answer is "another feature clears it on purpose", you have two facts sharing
one slot and you need two slots. The tell is a lifetime mismatch stated in the
field's own docstring: `_last_cyanrip_output` documents itself as *the last*
invocation's output, and ripper *identity* is a property of the installed binary,
which does not change per command. A value whose natural lifetime is the run cannot
live in a field whose contract is per-step.

**Testing note — the fixture was writing the field the reader read.** The existing
`(ripper)` tests set `runner._last_cyanrip_output = banner` directly. That is
`CLAUDE.md`'s *what does my stand-in do that the real thing does not?* in its most
literal form: the helper bypassed the absorber, so it would have kept passing
against a build where nothing populated the latch at all. The regression test plays
a real `_CyanripJob` through `_service_cyanrip`, and asserts **survival** rather than
expansion — a fresh banner expanding proves nothing about a banner surviving the
traffic that follows it.

**And a recurrence worth naming.** The section-C note this run invalidated was
itself a *correction*, written 2026-08-18, which fixed a genuine hardware hazard
(`-O` overread vs the fork's `-x` cache probe) and closed by asserting the probe
"costs SECONDS". That half was a guess, and it is the half that cost the session:
`-x` measures the cache and then rips the whole disc. `CLAUDE.md` already carries
*did a correction get less scrutiny than a claim?* — this is its second instance in
two weeks, which makes it a pattern. A correction arrives with the authority of
having been researched; the parts of it that were not researched arrive wearing the
same authority.

### §5.as — A report that is accurate word-by-word and wrong in kind

Two findings from one rig run (2026-08-20), same shape, different subsystems, and
both were sentences where **every clause was true and the message was false**.

**One.** A cancelled rip's cyanrip log has no `Log FUN512:` footer, because the
signature is written last and the ripper was killed before it got there. The
verifier saw a non-zero `--verify-log` exit and reported *"it does not match its
own FUN512 checksum, so it is not a faithful record of this rip and must not be
treated as archival evidence"* — at ERROR, and into the report's `issues[]`. The
log genuinely is not a complete record, and `--verify-log` genuinely refused it.
But *"does not match"* asserts a **comparison that never happened**, and the
difference is the whole finding: a mismatch says somebody altered an archival
record, an absence says the ripper died mid-write. One is an incident; the other
is Tuesday.

**Two.** `rig-check` reported *"parsed <log> to ZERO tracks — a parse that finds
nothing is not a parse that found nothing wrong"*. The floor is correct and was
added for a good reason (§5's recurring *can this check be satisfied by finding
nothing?*). It had simply never checked its **subject**: the cancel landed 91 s
into track 1 of a paranoia-max rip, so the log legitimately ended at its `Tracks:`
header and zero was the honest count.

**The generalisation, which is the part worth keeping.** We have a well-worn rule
about a check that can pass for the wrong reason. Its mirror image costs just as
much: **a check that can FAIL for the wrong reason.** A false FAIL does not merely
waste an investigation — it *devalues every other FAIL in the same manifest*,
because the reader learns that a red line here might be nothing. On this run the
two false reports were **both** of the run's two failures, so the entire failure
set was noise and the real result (the drive was released after the cancel — the
question four rig sessions had failed to answer) was the thing nobody was looking
at.

So, of any negative verdict, ask the question we already ask of positive ones:
*what are the distinct conditions that produce this message, and do they mean the
same thing?* If two of them do not, they need two messages. And where the
distinguishing evidence sits **in the artifact itself** — a `Log FUN512:` line
that is present or absent; an `outcome.status` field one directory away — read it
rather than collapsing the cases.

Two corollaries carried over from rules that already existed and applied here:

* **Derive the discriminator from the artifact, not from the dependency's prose.**
  The easy fix for the first finding is to match cyanrip's *"No FUN512 checksum
  found"*. That is precisely what the fork's lap-12 J4 asked us not to do — the
  string is genopt's and one upstream sync from changing. Our own parser already
  knows what the footer looks like; use that.
* **An excuse must require positive evidence.** Skipping the zero-track check
  when a rip *might* have been cancelled would have converted a noisy check into
  one satisfiable by finding nothing. The skip is gated on the report actually
  saying cancelled, with two independent witnesses, and absent that evidence the
  FAIL stands.

### §5.at — The advice a failure prints is code, and it can carry the bug

`wait-for-rip`'s message was excellent: it noticed the app was blocked on a modal,
named the dialog, explained that the rip had been requested but no worker existed
yet, and then said what to do — *"Answer it in the script (`ok` / `cancel`)
between `rip` and this step."*

That last clause was wrong, and wrong in the same way as the defect it was
diagnosing. `rip` only *requests* the start, so the confirmation appears a beat
after it returns; `ok` acts on whatever is on top at the instant it runs and fails
when nothing is. Following the advice literally produces an intermittent *"no
dialog is open"* — which is the §5.ap asynchronous-seam defect, re-emitted by the
very message written to help. (Measured: reverting the new verb to a bare
`_dismiss` reproduces exactly that line.)

The lesson is not "write better prose". It is that **a remediation string is a
recommendation the reader will execute**, so it is subject to the same review as
the code path it describes — including *would this work if the thing it mentions
is asynchronous?* A diagnosis that ships a broken fix is worse than one that
stops at the diagnosis, because the reader trusts it and spends the next run
finding out. Where the app can name the exact line to add, it should quote the
real values it already has (the blocking dialog's actual title) **and** say why
the tempting shorter form is wrong, so the next reader does not simplify it back
into the bug.

### §5.au — A passing check and an absent check have the same signature, so "it is inert" needs a deliberate failure

**2026-08-20.** A local suite run with `--cov=platterpus --cov-report=term
--cov-fail-under=91` printed `4335 passed, 16 skipped … in 320.06s`, exited `0`,
and showed **no coverage table at all** — no `TOTAL` row, no *"Required test
coverage of 91%…"* line, zero matches for `cov|TOTAL|Required` across the log.

There was a mechanism ready to explain it, and it was a good one: `conftest.py`
ends the session with `os._exit(status)` to dodge a PySide teardown abort, so
pytest's epilogue is cut short — therefore the floor is never evaluated and
`--cov-fail-under` is silently inert locally. That accounts for every symptom.
It was written into `TASKS.md`, cited in a commit message, and used to retract
two earlier commit messages as overstatements.

It was wrong. Two commands:

```
$ ls -la .coverage && python3 -m coverage report | tail -1
TOTAL   18808   1416   5060   423   91.51%
$ pytest tests/test_app.py --cov=platterpus --cov-fail-under=100; echo $?
ERROR: Coverage failure: total of 20 is less than fail-under=100
1
```

The data file is written, the number is 91.51% against a floor of 91, the gate
is enforced through the exit code, and it announces its own failure. The
`conftest.py` comment said all of this in those words the whole time: only
pytest-cov's *printed* table is skipped, and only on a passing run, because
`os._exit` fires before the plugin prints.

**The transferable part.** The observation was *exit 0, nothing to look at*. That
is what a **passing** gate produces. It is also what an **absent** gate produces.
The signatures are identical, so the observation carried no information about
which one it was, and every inference drawn from it was unfounded — however good
the mechanism sounded. This is the *"can this check be satisfied by finding
nothing?"* rule turned around and pointed at the reader: **I** was the check, and
I read a pass as an absence.

So: **to claim a check is inert, make it fail on purpose.** An impossible
threshold, a deliberately broken input, a reverted fix — the same move this
project already requires of a new test (*would this fail if I reverted the fix?*),
owed equally to a claim *about* a check. A gate only demonstrates it is alive by
refusing something.

Two corollaries, both paid for here:

- **Read the comment before theorising about the code.** The correct answer was
  in a comment one screen above the `os._exit` call, written by whoever made the
  trade-off deliberately. A mechanism invented from the outside will sometimes
  beat the author's own note, and this was not one of those times.
- **A retraction is a claim and gets the same scrutiny.** Retracting a true
  statement for a false reason is not the safer error: it puts a wrong correction
  into the permanent record, where it reads as the *more* careful of the two
  statements and is that much harder to dislodge. Same shape as §5.ad's *"did a
  correction get less scrutiny than a claim?"*, arriving from the inside.

The one thing genuinely worth fixing is small and is diagnosability, not
correctness: `pytest_sessionfinish` already reaches into the terminal reporter to
print the test summary itself, precisely because losing it made a red run
undiagnosable. The coverage table deserves the same treatment — a run that shows
its own number is a run nobody has to infer one from, and inferring one cost two
successive wrong records. Done: `conftest.print_coverage_report`, pinned by four
tests in `tests/test_harness_fidelity.py` — three on the helper and one AST check
that `pytest_sessionfinish` actually *calls* it, because the first three pass
whether or not anything does.

### §5.ax — The apology nobody audited: a generous cause produces the wrong fix

*2026-08-21, cyanrip round 12. A retraction of a retraction, and the second one
was mine.*

The fork opened round 12 with a `HANDSHAKE-BREAKING` notice stating that our
`SUPPORTED_SCHEMAS` allowlist would reject their new diagnostics-record schema.
It does not — that constant is a `frozenset[int]` over their *release manifest*,
nothing here reads a diagnostics schema string, and a rip never sends `-j` at all.
They promoted a question to `BLOCKING` on it.

In reporting the correction I offered to **share the blame**: our own round-11 lap
had written *"when we next widen `SUPPORTED_SCHEMAS`"* without naming the
document, so — I wrote — a name collision plus one unqualified sentence was
"sufficient explanation", and "half of it is ours."

**They refused the excuse, and they were right.** They opened all three sentences
and reported that every one sits in unambiguous release-manifest context. Checked
here afterwards: mine (`verified/round-11-lap-04.md:95`) sits four lines below a
paragraph about `meson_options`, per-row `build`, and *"a live refusal window on
yours"*; theirs prints `supporting {1, 2}` four lines above the sentence in
question. **Nothing was ambiguous.**

Two lessons, and the second is the general one:

1. **The rule that actually fixes it is theirs, and it is checkable:** *never state
   a mechanism in the other side's code without citing where you read it.* Now a
   `CLAUDE.md` rule. Compare it with the remedy the generous story implies —
   "write less ambiguous sentences" — which is unfalsifiable, has no test, and
   would have changed nothing. **A misattributed cause produces the wrong fix, and
   a flattering misattribution produces a fix nobody can fail.**
2. **An apology is an assertion, and it is the one kind nobody audits.** §5's
   existing rule is *"did a correction get less scrutiny than a claim?"* — a
   finding that arrives as *"you got this wrong"* is not pre-verified. This is its
   mirror. A concession arrives as *"some of this is my fault"*, which reads as
   fair-mindedness rather than as a factual claim about where a defect came from,
   so the peer has no reason to argue and the author has no reason to check. It
   went out at column 0 in a binding protocol file with **no** verification behind
   it, in the same lap that corrected somebody else's unverified column-0 claim.

The test to apply: **if this were a claim instead of an apology, would I have
verified it?** If not, verify it or do not make it. Note what the honest version
costs — nothing. The retraction in lap 4 is shorter than the excuse in lap 2.

### §5.aw — A gate's POPULATION is part of the gate: four green checks that could not reach the bug

*2026-08-21, v0.6.22. Four defects shipped or nearly shipped in one session, each
one living inside a check that was **green, real, and looking somewhere else**.
This is not the "no test existed" failure — every one of these had a test.*

The recurring question in `CLAUDE.md` is *"can this check be satisfied by finding
nothing?"* This is its sibling and it is harder to see, because the check *does*
find something — just never the thing you fear. **Ask not "is this checked" but
"could the thing I fear be inside what this check looked at."**

The four, with what each population excluded:

| defect | the green check | what its population could not contain |
|---|---|---|
| a finished rip announced as *"never finished"* | two re-rip comparison tests | both construct the report **already finalised**, so the empty→full transition the race lived in does not exist in the fixture |
| an unreadable log reported as **tampering** | a test asserting exactly that behaviour | it framed the choice as *gentle* vs *strong* wording and **never considered saying nothing**, so it pinned the defect as correct |
| two ripper failures shown as a bare *"Rip failed"* | the fatal-inventory agreement test | its fixture was **generated from the same round as the inventory**, so the two agreed perfectly and neither could see the contract move 115 → 128 |
| album loudness read from wording the ripper disclaims | a column-0 completeness sweep over `output_reference/` | **no log in that corpus contains the four rows**, so the sweep passed the whole time they were being dropped |

Three distinct mechanisms, and they are worth naming separately because they are
recognisable in advance:

1. **A fixture that starts in the end state cannot see the transition.** Any test
   whose subject is a *change* (empty→full, absent→present, in-progress→final) has
   to construct the earlier state. This is §5.ap's *"what would still be false one
   millisecond after I return True?"* arriving from the fixture side rather than
   the assertion side.
2. **A list checked against itself is consistent, not verified** — §5's oldest
   lesson, and it recurred here in the exact shape round 5 warned about. The tell
   is a fixture and a subject with a **common ancestor**: same round, same
   generator, same commit. Derive the expected value from the *other side's*
   artifact or from the source, never from a snapshot taken beside the thing under
   test. Note the asymmetry that made this one visible: the **input** half of the
   same seam (our argv vs their flag table) has had a real cross-artifact diff every
   commit since the `-V` blocker; the output half had a mirror. One seam, two
   halves, one of them checked properly.
3. **A test can pin the defect.** The unreadable-log test asserted the wrong
   behaviour with a confident docstring, so it would have defended the bug against
   any future fix. When replacing such a test, **quote the old assertion in the new
   one's docstring** — otherwise the next reader sees only the new belief and cannot
   tell it was ever contested.

And the corollary for the corpus itself: `output_reference/` grows by whatever real
discs happen to get ripped, so it is a *sample*, not a specification. A sweep whose
population is "the logs we happen to have" silently narrows every time the
dependency emits something new. Where a handshake round commits an artifact, sweep
**that** — it is the newest statement of what the dependency actually prints.

### §5.av — The same error, made twice in one hour, on the other side of the repo

Immediately after the above, the same move was made again: `--status` reported
`sent=NO` for handshake rounds 9 and 11 while `outbound/round09lap08platterpus.md`
and `outbound/round11lap04platterpus.md` sat in the directory. Obvious
conclusion — the 2026-08-13 separator-free filename convention was applied to the
artifacts and never taught to the tool that reads them, so files are invisible to
`glob("round-*.md")`. It was written up with a severity claim attached (*a
compliance gate silently skipping two of our own artifacts*).

Then the files were opened. Their first header line:

```
HANDSHAKE-ROUND: not-a-lap (transport envelope)
```

They are **transport envelopes** — containers carrying byte-identical lap files
with per-part SHA-256s — and they say so in their own first paragraph. They
declare `not-a-lap` in the header *and* carry a name outside the lap convention,
so the header route and the name route exclude them **consistently**. The tool was
right, the design was coherent, and the "defect" was a container correctly
declining to be counted as its contents. The named compliance test does not even
contain a `glob(`.

**Two things generalise, and neither is "read more carefully".**

- **A file the parser skips is not evidence of a parser bug.** Ask what the file
  *claims to be* before asking why the code disagrees — deliberate exclusion and
  failed inclusion look identical from outside, which is §5.au's signature problem
  wearing different clothes. The rule already existed in `CLAUDE.md` (*"am I
  answering from the artifact, or from my memory of the artifact? If a committed
  file can settle the question, open it"*), and the cost of not following it was
  paid twice in one session, on unrelated subsystems, within the hour.
- **Do not brief a delegate with an unverified premise as settled.** Both
  investigations were handed to subagents whose instructions said the defect was
  *"CONFIRMED BY MEASUREMENT … you are mapping its blast radius, not re-finding
  it."* That sentence does two kinds of damage: it propagates the error, and it
  explicitly forbids the single check that would have caught it. A delegate given
  a premise and told not to test it cannot function as an independent witness —
  it becomes the shared-ancestor problem from the *"two implementations agreeing"*
  rule, manufactured on purpose. Brief the **observation** (*exit 0 and no table*,
  *two files the tool does not list*), never the diagnosis, and say plainly that
  the premise is yours and unconfirmed.

### §5.ay — "Idempotent" is a property of the CALLEE, and we asserted it about the caller

**2026-08-25.** A cancelled rip on the 2026-08-24 rig run left a log with no
completion footer and **no FUN512 checksum at all** — an unverifiable fragment
where an archival record should be. We spent a handshake round attributing it to
the ripper. It was us, and the defect was one sentence of reasoning in a comment.

Three call sites in `RipWorker` each sent their own SIGTERM on a cancel: the user
cancel, the startup-window re-check, and the pre-reap nudge in `_reap_ripper`,
whose comment read *"asking again is free and idempotent, and it guarantees the
process has been told to stop before we start waiting."*

Every clause of that is true **about `Popen.terminate()`**. None of it is true
about the process being terminated. cyanrip's handler is:

```c
if (quit_now) { SIG_WRITE_LIT("Force quitting\n"); _exit(1); }
```

`_exit` runs no `atexit`, and `atexit` is where cyanrip writes the footer and the
checksum. So the second signal does not repeat the first — **it replaces a clean
shutdown with a forced one.** Measured on the real code path (real subprocess,
real `RipHandle`, real `killpg`): **two signals, 0.445 ms apart.** The escape
hatch exists for a user hammering Ctrl-C; half a millisecond is not a user.

**The generalisable rule: idempotence is not a property you can establish by
reading your own call site.** `f(x); f(x)` is safe only if *`f`* is safe to
repeat, and `f` here was a syscall delivered to somebody else's signal handler,
whose source was in a repository we had checked out. Ask of any "calling it twice
is harmless": *harmless to whom — me, or the thing on the other end of it?*

Four things this cost, each worth its own note:

1. **The test asserted the defect was deliberate.** `terminate_calls >= 1`, with
   a comment explaining that a cancelled rip terminates twice and *"that is
   deliberate — SIGTERM is idempotent and free."* A loosened assertion with a
   confident comment is worse than no assertion: it tells the next reader the
   question has been considered. It is `== 1` now, and tightening it is part of
   the fix rather than a tidy-up alongside it.
2. **The fix's own state needed scoping, and a bool was the wrong shape.** "Have
   we signalled?" is a fact about a *subprocess*, and this worker spawns one per
   pass (read-speed ladder, per-track auto-fix). A bool needs a reset, and every
   place to put the reset has a window where a cancel either double-signals the
   old process or fails to signal the new one. Keyed on the **handle's identity**
   there is no window: a new handle is a different object. *When a flag needs a
   reset, ask whether it should have been an identity comparison.*
3. **Extracting the kill into a chokepoint broke the sweep that guards it.**
   `tests/test_qthread_ownership.py` reads `cancel()`'s own body looking for a
   real interrupting call, so moving `terminate()` into `_signal_stop` made
   `RipWorker` report as flag-only — and the *convenient* repair was an allowlist
   entry asserting a flag was sufficient, which is false. The right repair was to
   follow one level of same-class delegation, matching what `_stopped_reachably`
   already did for teardown hooks. **A refactor that trips a correctness sweep is
   a prompt to teach the sweep, not to exempt the subject** — and the exemption
   would have been permanent, silent, and written in the file that exists to stop
   exactly that.
4. **The absence of a fifth possible cause was never checked, because the
   evidence had been censored — see below.**

### §5.az — We deleted the ripper's dying words, then reasoned from the gap

**2026-08-25, found while answering the above.** The cyanrip fork examined the
6.2 MB app log we sent them, found **zero** occurrences of their handler's
`"Trying to quit"` across 51,492 captured ripper lines, and concluded — carefully,
and marked `[MEASURED]` — that *"on the evidence we hold, our handler did not
run."* The premise was true. The conclusion was wrong, and it was wrong because of
our code:

```python
for line in self._handle.log_lines():
    if self._cancelled:
        break          # <- the line just read off the pipe is discarded
```

The check sat **above** the retention code, so the first line the ripper emitted
after our signal — its answer to being cancelled, the single most informative line
in the whole capture — was dropped, silently, on every cancel. Measured by
recording what the iterator *yielded* against what the capture *kept*: yielded
yes, kept no.

Three lessons, in increasing order of how much they generalise:

* **An "absence" in a log is a fact about the logger, not only about the
  subject.** Before inferring from a missing line, establish that the capture
  would have kept it. Both projects skipped that step, and the peer's inference
  was the better-argued of the two.
* **The naive fix is useless and would have passed a weaker test.** cyanrip emits
  `"\r\nTrying to quit\n"` in a *single* `write(2)`; the leading `\r\n` terminates
  the progress redraw that was mid-line, so the first line after the signal is a
  blank and the sentence is the *next* one. Retaining "one more line" keeps a bare
  `\r` and loses the message — so the regression test pins **both** lines, and a
  revert to one-line retention is probed and fails.
* **The worst artifact is not a missing diagnostic; it is a diagnostic that looks
  complete.** `CLAUDE.md` already said *"a silent truncation reads as
  completeness"* and this is the third violation by code written after the rule.
  We handed a peer a capture with a hole we had made, they reasoned correctly from
  it, and it pointed away from the real cause — costing a round. The rule is not
  "log more"; it is that any deliberate drop is **counted and marked**.

### §5.ar — The crash handler was the crash: a modal dialog inside its own event loop

**2026-08-19/20.** CI hung on all four Python legs, twice, and burned the whole
15-minute step each time. The log held progress dots, then nothing, then *"the
action has timed out"*. Nothing about where.

The suite is green locally — under PySide6 6.11.1 **and** 6.11.2, under the same
deterministic ordering CI uses (`pytest-randomly` is not installed, so the order is
the same everywhere; that was checked rather than assumed). So the first move was
not to explain it but to make the machine that *does* fail say where: pytest's own
`faulthandler_timeout` + `faulthandler_exit_on_timeout`, which dump every thread's
stack when one test outruns a bound. One run later:

```
File "src/platterpus/app.py", line 133 in _show_fatal_dialog
File "src/platterpus/app.py", line 252 in hook
File "src/platterpus/app.py", line 133 in _show_fatal_dialog   <- itself, again
File "src/platterpus/app.py", line 252 in hook
File "tests/test_ui_drive_setup_dialog.py", line 391 in ...
```

Line 133 is `box.exec()`. **A modal `exec()` runs a nested event loop**, so Qt
keeps delivering events while the fatal dialog is up — and an exception escaping
any callback in that window re-enters `sys.excepthook`, which calls the dialog
again, *inside* the first one's loop. Nothing raises, so the handler's own
`except Exception` never sees it: the recursion travels through Qt. Headless there
is nobody to click OK, so the process parked there until the job died.

Four things this teaches, each already a rule here and each freshly earned:

* **A hang must name itself.** The diagnosis was alive in the stuck process the
  entire time and we threw it away — the same defect as capturing a dependency's
  stderr and never surfacing it. The bound is 300 s against a 275 s suite, so it
  cannot fire on a slow-but-working test; the measurement is written beside the
  setting.
* **The stack blamed a different test on 3.11 than on 3.12/3.13/3.14.** That is the
  signature of *action at a distance*: the failing test is whichever one first
  pumped the event loop after an earlier test armed the trap. No amount of reading
  the accused test could have found it, which is why localising by re-deriving
  CI's progress ladder (46 dot-lines x 72 = test #3313) mattered — it bounded the
  search to a file, and the file was innocent.
* **"What new state does this fix create?"** The unattended-quit timer added the
  day before is what supplied the *exception*: it is armed inside `main()`'s
  `--run-script` path, four tests drive that path, and its tick reads a window it
  outlives — a PySide6 wrapper whose C++ side is gone raises `RuntimeError` on
  attribute access, from a timer callback, straight into the excepthook.
* **The harness had product crash-handling installed.** Seven tests left
  `sys.excepthook` pointing at the product handler; three of them restored it and
  not `threading.excepthook`, and looked correct doing so. `conftest.py` now
  restores both around every test. This one RESTORES rather than failing the
  offender, which is the opposite of the `os._exit` and window-thread fixtures —
  because leaving that hook installed is *correct* in production, so it is
  ordinary hygiene rather than the harness covering for a product bug.

**Revert-proofing, done by actually reverting.** With the re-entrancy guard removed
and the removal proven to have landed (anchor asserted, file hash compared), the
regression test does not merely fail — it dies with `RecursionError: maximum
recursion depth exceeded`. The nesting is unbounded, which is also what a user
would have met: a pile of dialogs, each needing the one above it dismissed first,
every one able to spawn another. The test asserts on the *count of dialogs opened*,
not on the flag, and then asserts a later unrelated crash still gets its dialog —
a guard that latched ON would silence every future crash report, which is a worse
failure than the one it fixes.

## 5B. What a version number is allowed to claim (the road to 1.0)

**Maintainer ruling, 2026-08-19.** *"I think your current gate to v1.0.0 is
passing the tests. The actual goal should be passing EVERY test all at once,
probably at least twice… we have only tested on my rig, my hardware. We need more
people, more hardware, more Linux distros, to get up to v1.0.0 proper. This should
not be only test or gate, though it should be that too, it should be encoded in
the documentation and testing."*

That correction is worth stating plainly because the implicit gate really was
wrong. "The suite is green" is a statement about **this repository on a CI
runner**. A version number is a statement about **the software in somebody's
hands**, and the two are not the same claim — every defect that mattered this
month was found on hardware by a person, with a green suite the whole time.

### The three thresholds

| Version | What it claims | What that requires |
|---|---|---|
| **0.x** | *"Under development; expect defects."* | The suite is green. Nothing else is asserted, so nothing else is owed. |
| **0.9.1** | *"Feature-complete and internally proven."* | **A complete hardware pass — EVERY test green in ONE run — achieved at least TWICE.** Not "the failures were understood"; not "green except the known ones". One run with a full green sheet is a data point; two is the first evidence it was not luck. |
| **1.0.0** | *"Ready for people who are not us."* | Everything above, **plus independent field evidence: more than one person, more than one machine, more than one Linux distribution.** The maintainer's rig is one configuration out of every configuration a user might have, and a single-rig 1.0 is a claim the evidence cannot carry. |

**The 0.9.1 bar is "all at once", and that word is the whole rule.** A run of
`pass=55 fail=5` where each of the five is separately explained is *not* a pass.
Explaining a failure is how you fix it; it is not how you count it. The reason to
insist is measured in this project's own history: the 2026-08-19 run's five
failures all descended from one defect nobody knew existed, and every one of them
would have been waved through as "understood" by a looser rule.

**The 1.0.0 bar cannot be met by working harder here.** It is not a quality bar
that more diligence clears — it is a *coverage* bar, and the only way to move it
is other people's hardware. That is why it is written down rather than left to
judgement at release time: the temptation at 0.9.9 will be to reason that things
seem fine.

### The evidence ledger

Rows are added when a run happens, by whoever ran it. `test_no_stale_version_claims.py`
parses this table and refuses a version bump that the rows do not support — an
empty ledger fails the 0.9.1 and 1.0.0 gates rather than passing them by finding
nothing.

`result` must be exactly `full-green` or `partial`; anything else is read as
`partial`, because an unrecognised verdict is not a pass. `person` and `machine`
are free text, and only their *distinctness* is counted.

### Acceptance severity — which failures block a version, and which do not

**Maintainer ruling, 2026-08-26.** The `0.7.100` gate is *"error free"*, and that
was sharpened to mean something precise:

> *"If there is something minor like a window size was wrong, then ignore. But
> critical passing tests for cd accuracy and provenance, etc, for archive level
> records, if all those pass fine. Difference between not working as intended and
> not actually doing the job you were built for."*

So the bar is **zero failures in `ARCHIVAL` sections.** `UX` failures are
recorded, triaged and non-blocking.

**The one property that makes this safe: severity is a property of the SECTION,
fixed here in advance — never a judgement made about a failure after seeing it.**
*"The five failures were each understood"* is the exact sentence 2026-08-19
disproved, when all five descended from one unknown defect; a severity assigned at
results time is that sentence wearing a better hat. Classify before the disc goes
in, or the classification is worthless.

**And a `UX` failure is non-blocking only while it is its own defect.** If it
shares a root cause with an `ARCHIVAL` one, it is archival. That keeps the
2026-08-19 lesson instead of trading it away — the 2026-08-26 run is the worked
example, where seven failures across four sections were **one** duplicate-picker
defect, and two of those sections are archival.

<!-- ACCEPTANCE-SEVERITY-TABLE: swept by tests/test_rig_scripts.py -->

| section | severity | why |
|---|---|---|
| A | ARCHIVAL | which binary produced the artifact — provenance, by definition |
| B | ARCHIVAL | settings reach cyanrip's argv; a nudged read offset rips the next disc wrong with a clean-looking log |
| C | ARCHIVAL | a guard that fails to refuse writes bad data |
| D | UX | dialogs open and close; annoying when wrong, not a claim about a disc |
| E | ARCHIVAL | wrong release → wrong tags → a wrong archival record |
| F | ARCHIVAL | the rip itself |
| G | ARCHIVAL | the seam check and the rip's own log — the log *is* the provenance record |
| H | ARCHIVAL | the overwrite prompt; missing the collision destroys a finished master |
| I | ARCHIVAL | cancel; the defect this exists for destroyed the log's completion footer |
| J | ARCHIVAL | identify and rip again after a cancel — a rip, and a drive-state proof |
| K1 | ARCHIVAL | when a user selects MP3 the MP3 *is* their library entry — the thing they play, with its tags and art. "Lossy by design" describes the codec, not the importance of deriving it correctly |
| K2 | ARCHIVAL | WavPack is lossless — a second archival-grade output |
| K3 | ARCHIVAL | **WAV is raw PCM, i.e. lossless** — those bytes *are* the audio. Classified UX in the first draft, which contradicted K2: "lossless → archival" was applied to WavPack and not to WAV. The maintainer caught it |
| K4 | ARCHIVAL | back to FLAC, the archival master |
| L | ARCHIVAL | a preset applies a *bundle* of settings, several reaching cyanrip's argv. B checks each setting round-trips; that a preset applies **all** of it is a different claim, and a preset that silently under-applies hands the user a fast rip they believe is a paranoid one |
| M | UX | naming templates — where a file lands, not whether its bytes are right |
| N | ARCHIVAL | T1, the whole-disc uniform secure re-read: the accuracy claim itself |
| P | ARCHIVAL | the cache probe feeds the accuracy model |
| P2 | ARCHIVAL | C1 — a refusal that hangs the drive costs the disc |
| Q | UX | restoring settings the run changed; hygiene for the *next* run |

<!-- END-ACCEPTANCE-SEVERITY-TABLE -->

**17 ARCHIVAL, 3 UX.** Few UX rows is the honest answer for a CD archival tool: most of what it does *is* the job. The three that remain are genuinely about the program rather than the disc — dialog plumbing (`D`), where a file lands rather than whether its bytes are right (`M`, whose dangerous failure mode is a collision, which `H` catches and grades archival), and hygiene for the *next* run (`Q`). The table is swept: every `log --- ` section in
`fullacceptance.txt` must appear, so a **new** section has to be classified
rather than defaulting to ignorable — the direction that fails safe is the one
that makes you decide.

<!-- FIELD-EVIDENCE-TABLE: parsed by tests/test_no_stale_version_claims.py -->

| date | version | person | machine | distro | result |
|---|---|---|---|---|---|
| 2026-08-18 | 0.6.16 | maintainer | bdr209d | bazzite | partial |
| 2026-08-19 | 0.6.17 | maintainer | bdr209d | bazzite | partial |
| 2026-08-19 | 0.6.18 | maintainer | bdr209d | bazzite | partial |

<!-- END-FIELD-EVIDENCE-TABLE -->

Three runs, three `partial`. That is the honest state: **no full-green pass has
been achieved yet**, so 0.9.1 is not reachable today and the count toward it is
zero. Recording the partials anyway matters — a ledger that held only successes
would make the denominator invisible.

**How a row gets produced** is `docs/test-plan.md` **Part E** — the
failure-derived gate: the twelve defect classes that have actually bitten here,
how to tell a normal failure from a run that is not trustworthy at all, and what a
*pass* has to prove before it may be counted. It exists because of two counted
facts: every failure on both of the last two rig runs descended from a **single**
defect, and every defect that mattered this month was found on hardware with the
suite green throughout.

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
- [ ] **Before a RELEASE tag (not merely a merge): an adversarial review of the
      release diff.** Not a general nicety — the measured reason. On 2026-08-18 a
      25-agent review of a diff with a **green suite, a green typecheck and ten green
      CI checks** raised 20 findings and confirmed 14, three of them blocking, and two
      of the three would have reached an **archival record**: a build stamped
      `unapproved` after the app said it was approved, and a repair path that could
      never succeed for the population it was written for. None was visible to the
      suite, because each lived in a *relation between* two individually-correct places
      (§5.al) — and the suite tests modules. So the gates in `release.yml` are
      necessary and not sufficient: they check that everything ran and passed, which is
      a different claim from *the change is right*.
      Prompt it to **refute**, require every finding to name what it ran, and verify
      each one yourself before acting — *"a correction that arrives as 'you got this
      wrong' is not pre-verified"*. And read an empty result carefully: a pass and *"the
      review could not run"* look identical from the outside, which is exactly what
      happened to the follow-up pass the same day (§5.aj's family, arriving through the
      tooling). Apply **S-14** to what it finds — a real defect is an argument for
      fixing it, not automatically for holding the release.
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

*Last updated for Platterpus v0.6.31.*
