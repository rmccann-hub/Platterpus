# Architecture & Contributor Guide

> **Who this is for.** Anyone — not just the original author — who wants to
> understand, extend, or safely change Platterpus. It explains *how the
> pieces fit*, *the patterns to follow* (with the **why** and the hard-won
> lessons behind them), and *where to plug new things in*.
>
> Read it alongside its companions, each of which owns a different slice so
> nothing is stated twice:
> - **[`../CLAUDE.md`](../CLAUDE.md)** — the *locked* contract: code
>   conventions, critical rules, deviation policy. If anything here ever
>   conflicts with CLAUDE.md, **CLAUDE.md wins**; this guide explains and
>   expands those rules, it does not override them.
> - **[`../PLANNING.md`](../PLANNING.md)** — the module map and the keyed
>   design-decision log (KDD-01 onward — see `docs/README.md` for the current range): the "why is it like this?" record.
> - **[`testing.md`](testing.md)** — the testing strategy, taxonomy, and
>   Definition of Done.
> - **[`session-log.md`](session-log.md)** — the dated chronology of how each
>   lesson here arose.

## 1. What this program is

A Linux desktop GUI (PySide6 / Qt6) that drives the `cyanrip` audio-CD ripping
CLI to produce EAC-equivalent, archival-quality FLAC rips. The GUI itself never
rips: it shells out to a host-exported `~/.local/bin/cyanrip`, which
transparently enters a Distrobox container named `ripping` to do the work.
**This routing is non-negotiable** (see
`CLAUDE.md` Critical Rule #3) — the GUI is an orchestrator and a user
interface, not a ripper.

```
┌────────────────────────────────────────────────────────────┐
│  Platterpus (this app, runs on the host as PySide6)         │
│   • picks the MusicBrainz release  • builds the rip command  │
│   • shows progress + the fidelity verdict  • tags / art      │
└───────────────┬──────────────────────────────────────────────┘
                │ subprocess → ~/.local/bin/cyanrip (host export)
                ▼
        ┌───────────────────────┐     MusicBrainz / Cover Art Archive /
        │ Distrobox "ripping"   │     CTDB  ◄─ queried by the GUI on the
        │ container: cyanrip +  │        host (never the ripper; AccurateRip
        │                       │        verification happens in-rip, inside
        │                       │        cyanrip — the GUI only carries the
        │                       │        bundled offline AR drive-offset list)
        │ flac                  │
        └───────────────────────┘
```

## 2. The layers (and the dependency direction)

Dependencies point **downward** only — UI depends on workers/adapters,
adapters depend on nothing in the UI. Keep it that way; it's what makes the
pieces independently testable and replaceable.

| Layer | Package | Responsibility | May import |
|-------|---------|----------------|------------|
| **UI** | `ui/` | Qt widgets, dialogs, the main window. *No business logic, no blocking I/O.* | workers, adapters, parsers, deps, config |
| **Workers** | `workers/` | `QObject`s that run slow work (network, subprocess) off the GUI thread and emit results as signals. | adapters, parsers |
| **Adapters** | `adapters/` | The *only* code that talks to an external tool/service (cyanrip, metaflac, MusicBrainz, Cover Art Archive, CTDB, AccurateRip). Thin, swappable. | parsers, stdlib |
| **Parsers** | `parsers/` | Turn external tool output (rip logs, disc info) into typed dataclasses. Pure, never raise. | stdlib only |
| **Deps** | `deps/` | The single dependency self-management subsystem (detect → install → guide) and the host bootstrap/teardown engines. | adapters, stdlib |
| **Domain** | `ctdb/` | Backend-independent CTDB verify (TOC math, PCM decode, CRC). | adapters, stdlib |
| **Qt-free domain modules** | ~25 top-level modules (`verdict.py`, `rip_report.py`, `parity.py`, `rip_compare.py`, `naming.py`, `settings_validation.py`, …) | One pure, Qt-free concern each (verdicts, reports, parity, naming, validation, timing, …). **The canonical per-module map is PLANNING.md §2** — look there, not here, for what each does. | parsers, adapters, stdlib |
| **Core** | `config.py`, `paths.py`, `logging_setup.py`, `app.py`, `composition.py` | Config schema, well-known paths, app entry, and the composition root. | everything (composition) |

`app.py` is the **composition root**, with the reusable construction logic in
`composition.py`: `build_backend(cfg)` (constructs the sole cyanrip backend — KDD-18 — + the
host-exported-path fallback) and `build_musicbrainz_client()`. `app.py` injects
everything into `MainWindow`; `preflight.default_context()` (the `--doctor`
diagnostic) builds the *same* adapters through the *same* helpers, so the GUI and
the doctor can never diverge. Nothing else should construct adapters — inject
them, so tests can pass fakes.

> **Code style** (type hints, naming, ~300-line module heuristic, heavy
> intent-comments, no clever metaprogramming) is owned by `CLAUDE.md`
> *Code conventions* — follow it there; it isn't restated here.

## 3. Patterns you must follow

Each pattern below is the **single canonical home** for that topic. Other
docs (and KDDs) link here rather than restating.

### 3.1 Adapter layer for every external tool (Critical Rule #1)
Every call into an unmaintained or external dependency goes through a thin
adapter behind an interface, so a future replacement is a one-file swap, not
a codebase-wide rewrite. Currently flagged unmaintained:
`python-musicbrainzngs`, and `appimage-builder` (if ever reached for) — see
Critical rule #1 and the `DEPENDENCIES.md` table.

The pattern (designs in [`../PLANNING.md`](../PLANNING.md) §5–§6):

- Define an **abstract base class** describing *what the GUI needs*, in our
  own vocabulary (`RipBackend`, `MusicBrainzClient`, `CTDBClient`). The
  GUI depends only on the ABC.
- Provide a **concrete implementation** that wraps the real tool/library
  (`adapters/cyanrip_backend.py` — the sole backend today, KDD-18; a second
  could slot in behind the same ABC, which is exactly how whipper was replaced).
- **Inject the adapter** at construction so tests pass a fake — no real
  binary, network, or drive in the suite.
- Keep the ABC surface *minimal and capability-shaped*. Optional capabilities
  (e.g. `analyze_drive()` / `find_offset()`) default to `NotImplementedError`
  so fakes and alternative backends still construct.

Design the interface around the *consumer's* needs, not the wrapped library's
shape — that's what makes the dependency swappable. **Never** call an external
tool from a widget; **never fork whipper** (KDD-18) — write an adapter.

### 3.2 Never block the GUI thread (this caused real bugs — internalize it)
Anything that can take more than a few milliseconds — `subprocess.run`,
network I/O, large-file hashing/copying, `thread.join()`, `QThread.wait()`,
`kbuildsycoca6`, even a "best-effort" shell-out — freezes the event loop. A
frozen loop means the window shows "Not Responding" and ignores *every* click
(including Cancel and the X) until it returns.

Two sanctioned tools:
- **Need the result?** A `QObject` worker moved to a `QThread` (or a daemon
  `threading.Thread` that reports back via a queued signal). The result
  arrives as a signal — cross-thread connections are delivered on the GUI
  thread. See `workers/` and the `_start_*` methods.
- **Don't need the result?** Fire-and-forget:
  `subprocess.Popen(argv, stdout=DEVNULL, stderr=DEVNULL, start_new_session=True)`
  and return immediately. This is how the menu-cache refresh
  (`appimage_integration._default_refresh`) and the GNOME `gio` trust-marking
  (`_mark_trusted`) run.

When reviewing a diff, ask: *if this line ran on a stalled network or a cold
container, would the window freeze?* If yes, it belongs in a worker or a
fire-and-forget `Popen`.

> **Post-mortem (2026-06-13), worth re-reading before any UI change.** The
> in-app updater went "Not Responding" frozen at 100% for minutes; Cancel did
> nothing and the X took ages. Root cause: the post-download menu
> re-integration called `kbuildsycoca6` via `subprocess.run(timeout=30)` **on
> the GUI thread**. The same anti-pattern lurked in `_mark_trusted` (a 15 s
> `gio` call) and the launch dependency probe (`whipper --version`, which
> enters the container). All three were the *same class* of bug.

Worker mechanics, all demonstrated in `workers/`:

- **Worker-object + `moveToThread`, not `QThread` subclassing.** A `QThread`
  instance lives in the thread that *created* it, so slots on a `QThread`
  subclass run in the wrong thread. Put the work in a `QObject` worker and
  `moveToThread()` it. See `RipWorker`, `MusicBrainzWorker`, `DriveSetupWorker`.
- **Never touch widgets from a worker thread.** Communicate results back via
  **signals** (delivered as queued connections on the GUI thread). The worker
  emits `progress`/`status`/`finished`; the GUI updates widgets in the slots.
- **Connect a cross-thread signal to a *bound QObject method*, never a lambda
  or free function.** Qt picks the connection type from the *receiver*: a slot
  with no QObject context (a `lambda`, a module function) defaults to
  **DirectConnection**, so it runs on the **emitting** (worker) thread — even
  though you wired it from the GUI thread. A bound method of a GUI-thread
  `QObject` gets AutoConnection → QueuedConnection → runs on the GUI thread.
  This bit us: the launch dependency check connected `worker.finished` to a
  lambda, so `_apply_dependency_report` (which builds resolver dialogs) ran on
  the worker thread, creating widgets off the GUI thread ("QObject::setParent:
  ... in a different thread"). Fix was `worker.finished.connect(self._on_…)`
  with a bound method; stash any per-call state on `self`. The app-startup
  smoke test (`tests/test_app_smoke.py`) now fails on any cross-thread Qt
  warning so this class of bug can't come back silently. **It bit us a SECOND
  time (2026-06-27): the in-app *update installer* wired `progress`/`status`/
  `finished` to closures + a lambda, so the progress-dialog updates and the
  restart `QMessageBox` ran on the worker thread and *deadlocked* the window
  ("Not Responding").** Same fix (bound methods; dialog stashed on
  `self._install_dialog`). When adding ANY worker, grep
  `worker.*\.connect\((lambda|<a local def>)` before you ship — the rule is easy
  to forget at a new call site.
- **Long, non-cancellable post-rip work → daemon thread + queued signal, NOT a
  `closeEvent`-joined `QThread`.** The deterministic-cleanup rule below assumes
  you can bound-wait the thread at close. When you *can't* — CTDB verify and
  PCM decode can run far longer than any sane `wait()` timeout — don't put it on
  a `QThread` you join in `closeEvent`: if the window closes mid-run, you either
  block the close or **destroy a running `QThread`, which aborts the app**. Use
  a daemon `threading.Thread` that reports back via a queued signal (e.g.
  `ctdb_verify_done`); daemon threads die with the process and are never joined
  on close. The post-rip tagging/cover-art/CTDB chain runs this way. (When
  several steps touch the *same* files — tagging, cover-art, and the optional
  FLAC re-compress all rewrite the rip's FLACs — run them **sequentially on one
  thread**, in a fixed order, not in parallel, to avoid a same-file race. The
  re-compress runs **last** so it operates on the final tagged-and-arted files.)
- **Clean up deterministically:** connect `worker.finished → thread.quit`,
  `worker.finished → worker.deleteLater`, `thread.finished →
  thread.deleteLater`. **Join/stop threads before the window closes**
  (`closeEvent`) — destroying a running `QThread` aborts the whole app.
  (This bit us: closing the drive-setup dialog mid-detection killed the
  process — fixed by cancelling + joining on `reject()`/`closeEvent`.)
- **Don't call `QApplication.processEvents()` from inside a slot that runs
  during a modal `exec()`.** It re-enters the event loop and pumps unrelated
  timers/threads — an order-dependent crash. To force an immediate repaint of a
  status label, use `widget.repaint()`.
- **Dialogs that do blocking work** *(the name CLAUDE.md's never-block rule
  cites — this bullet is that section)*: **a modal dialog must NOT do blocking
  work in a button slot — this is the freeze trap that has bitten three times.** A
  `QDialog.exec()` runs a *nested* event loop, which tempts you to "just install
  here and `repaint()` between steps." But the slot itself still runs on the GUI
  thread, so a `subprocess`/network call in it freezes the whole window until it
  returns. The 0.4.2 bug: `PendingInstallsDialog` ran a Picard Flatpak install in
  its Install-Selected slot → the window went black, unclickable, "installing…"
  stuck, until the download finished. **The pattern:** the dialog runs the
  blocking loop on a worker `QThread` (`_InstallWorker`) and updates each row via
  **queued signals**, which the modal `exec()` loop delivers on the GUI thread —
  so the dialog stays live. The injected work callable (`install_one`) must be
  **thread-safe**: no Qt, and no opening sub-dialogs (that crashes off the GUI
  thread). GUI-only sub-steps (e.g. opening the host-setup wizard, which is
  itself internally async) are done on the GUI thread *outside* the worker loop —
  see `main_window_deps._resolve_missing_unified`, which splits wizard installs
  (GUI thread) from subprocess installs (off-thread). Also gate the dialog's
  close (`reject()`, which the title-bar ✕ also calls) while the worker runs, so
  it can't be dismissed out from under a running thread (a destroyed dialog +
  live `QThread` = hard abort). **Test it:** assert the work ran on a different
  `threading.get_ident()` than the GUI thread (`tests/test_ui_pending_installs_
  dialog.py::test_install_runs_off_the_gui_thread`), and drive the loop with a
  bounded `processEvents()` pump (see `docs/testing.md`), never `QThread.wait()`
  on the GUI thread (it deadlocks the queued `finished` signal).
- Use thread-safe primitives for cancellation flags — a plain `bool` set from
  the GUI thread and read by the worker is fine under the GIL; anything richer
  needs care.
- **Cancellation: re-check the flag right after you acquire the resource it
  acts on.** A `cancel()` that "stop the subprocess if `self._handle` is set"
  silently does nothing if Cancel lands *during* the spawn (flag set, handle
  not yet assigned) — the child then runs to completion and `wait()` blocks.
  The spawn window is a real race. After assigning `self._handle` in
  `RipWorker.start_rip`, re-read `self._cancelled` and `cancel()` the handle if
  it's set. Same shape for any "set flag now, act on it later" cancellation.

### 3.3 Invoking external programs (subprocess)
The GUI shells out constantly (cyanrip, flatpak, eject, pkill):

- **Never `shell=True`.** Pass an **argument list**, not a string — the module
  handles quoting/escaping and there is no shell to inject into. The GUI puts
  user-entered metadata (album/track names) into argv and path templates, so
  this is the single most important subprocess-security practice.
- **Resolve executables to absolute paths when the environment is hostile.** A
  GUI launched from a desktop icon (not a shell) inherits a *minimal* `PATH`
  that can miss `~/.local/bin` and even `/usr/bin`. `drive_control._resolve()`
  falls back through common absolute locations; do the same for any tool a
  desktop-launched process must reach.
- **Always set a `timeout`** (install commands cap at 300 s; force-stop probes
  at 20 s) — a wedged child must not hang forever. **But budget container-
  entering commands for the cold-start.** The *first* `cyanrip` call of
  a session starts the Distrobox `ripping` container (podman cold-start), which
  routinely takes tens of seconds on first use after a boot. A timeout calibrated
  for a *warm* system turns that legitimately-slow first call into a false
  failure — it shipped as "whipper timed out after 30s" on the first disc scan
  and as a *missing*-whipper verdict at launch (real-user report, 2026-06-27).
  The info/probe timeouts (`_INFO_TIMEOUT_S`, `_PROBE_TIMEOUT_S`) are deliberately
  ≥60–120 s for this reason; they're a wedged-process backstop, **not** a latency
  target (the warm case returns in a second or two regardless), and they run off
  the GUI thread so the window stays responsive while they wait. A useful side
  effect: a launch probe that waits for the container *warms* it, so the disc
  scan that follows is fast. Pin the values with a regression test so a future
  contributor doesn't "optimize" them back down.
- **Capture output, then `log` it** — don't stream to a console the user can't
  see. Surface the *last* error line; keep the full output in the log file.
- **Catch specific exceptions:** `FileNotFoundError`,
  `subprocess.TimeoutExpired`, `subprocess.SubprocessError`, `OSError` — never
  a bare `except`.
- **Cancel the whole process group, not just the parent.** A ripped-from-under
  reader (`cdparanoia`) outlives a killed parent. Launch cancellable
  subprocesses with `start_new_session=True` and signal the group
  (`os.killpg`). See `drive_control.force_stop_drive()` and the drive/reader-control
  section of `docs/dependency-contracts.md` for the scoped, user-approved
  force-stop exception (to Critical Rule #3) and its `pkill` anchoring rules.

### 3.4 Parsers never raise (institutional rule)
Anything that parses external output uses **named-group regexes** (not column
indices — tool output shifts between minor versions), tolerates garbage, and
returns a best-effort dataclass instead of raising:

- Match on *labels*, not positions. See `deps/version.py`
  (`DEFAULT_VERSION_PATTERN`) and the live cyanrip rip-progress patterns in
  `workers/rip_worker.py` (`_CYANRIP_TRACK_PROGRESS`,
  `Ripping(?: and encoding)? track (?P<track>\d+), progress - …`).
- Treat "couldn't parse" as a first-class outcome (return `None`/empty), not a
  crash — upstream output drifts.
- Add a fixture + test for every real-world output sample you encounter, and a
  `hypothesis` "never raises on arbitrary input" property test for every new
  parser (`tests/test_parsers_property.py`).

### 3.5 One dependency subsystem (Critical Rule #6)
All "is this tool present and the right version?" logic lives in `deps/`
(`DependencyManager.check_all` probes; `deps/resolvers.py` holds the three tier
building blocks: auto-install → queued install → copyable search string). Do
**not** add ad-hoc `shutil.which` checks elsewhere. New deps are registered in
`deps/registry.py` (mark `optional=True` if absence shouldn't nag).

**Resolution routing (installing what's missing) lives in the GUI**, not the
manager: `main_window_deps._resolve_missing_unified` splits missing deps by
*where the install runs* (setup wizard for container tools, an off-thread
live-progress `PendingInstallsDialog` for packaged installs, a manual-search
dialog otherwise). It's UI-coupled by nature — each tier opens a different
dialog and the install must stay off the GUI thread — so it can't live in the
Qt-free `deps/`. The manager once carried a parallel `resolve_missing` tier
cascade; it was unused (the GUI always routed itself) and was removed so there
is a **single** resolution path (audit #33). The presence/version half — the
part Critical Rule #6 requires be centralized — stays in `deps/`.

### 3.6 MainWindow is composed from mixins
`MainWindow` was a 1707-line god-object; it's decomposed (2026-06-13) into
cohesive `*Mixin` classes it inherits, so each concern lives in its own
focused file while methods stay reachable as `window._x` (which the test
suite and Qt signal wiring depend on). Each mixin documents the `self.`
attributes it assumes `MainWindow.__init__` has set. **This table is the
canonical ownership map** — KDD-19 records the *decision* and links here.

| Concern | Home |
|---------|------|
| Pure helpers (string-safety, fidelity verdict) | `main_window_helpers.py` |
| Self-update (check / download / install / restart) | `main_window_update.py` (`UpdateMixin`) |
| Rip lifecycle, force-stop, eject, cover art | `main_window_rip.py` (`RipMixin`) |
| Host setup / AppImage integration / uninstall | `main_window_provision.py` (`ProvisioningMixin`) |
| Drive setup / offset / access diagnosis | `main_window_drive.py` (`DriveMixin`) |
| Dependency check / resolve routing / summary | `main_window_deps.py` (`DependencyMixin`) |
| Construction, menus, signal wiring, MusicBrainz slots, settings | `main_window.py` (the assembler) |

`MainWindow(QMainWindow, RipMixin, UpdateMixin, ProvisioningMixin, DriveMixin, DependencyMixin)`
— a 1707-line god-object reduced to an assembler plus six focused
modules. (The split first landed it at ~460 lines; it has since grown as
new-feature wiring accreted — split again if a *concern*, not just a line
count, starts sharing the file.)

**Typing seam (`main_window_shared.py`).** A mixin's `self` is the concrete
`MainWindow` at runtime, but mypy types it as the bare mixin — so cross-mixin
`self._x` access it can't see would raise `attr-defined`. The **shared typing
seam** `MainWindowShared` (in `main_window_shared.py`) is the fix: a single,
type-only declaration of the surface the window exposes to its mixins (injected
deps, child widgets, per-session state, Qt signals, and the cross-mixin methods
each mixin calls on `self`). Every mixin *and* the concrete window inherit it,
so mypy resolves cross-mixin access from any mixin, and all six modules are now
in the strict gate (2026-07-20) with no `ignore_errors` left anywhere.

It is **runtime-neutral**: the attribute lines are bare annotations (no runtime
state), the cross-mixin method stubs live under `if TYPE_CHECKING:` (they don't
exist at runtime — the real impls are the only ones called), and the base it
inherits is chosen by `TYPE_CHECKING` — `QWidget` for the type checker (so mypy
knows `self` is a Qt widget), plain `object` at runtime (so the mixins gain no
Qt base and the MRO/metaclass are exactly as before). It is deliberately
`QWidget`, not `QMainWindow`: `MainWindow` lists `QMainWindow` first in its own
bases, so a seam deriving `QMainWindow` would demand it come both before *and*
after the mixins in the MRO — unsatisfiable; `QWidget` (never a *direct* base of
`MainWindow`) has no such conflict. When you add a shared attribute or a
cross-mixin call, declare it on the seam (keep the per-mixin `self.` dependency
comments accurate too — they document *which* mixin owns each concern).

### 3.7 Error handling & logging
- **Catch specific exceptions**, never bare `except:`. A last-resort
  `except Exception` is acceptable *only* at a thread/GUI boundary where a
  crash would take down the app, and it must `log.exception(...)` and degrade
  gracefully (tagging must never crash the GUI).
- **Use the `logging` module, never `print`.** The user's log lives at
  `~/.local/share/platterpus/log.txt` — the first thing to ask for in a bug
  report (the Settings *debug logging* toggle raises it to verbose DEBUG). Log
  at the right level: `debug` for probe detail, `info` for lifecycle,
  `warning` for recoverable failures, `exception` for unexpected ones.
- **Surface the actionable line to the user; keep the full detail in the log**
  (e.g. the dependency-summary "Install failures" block shows the last error
  line and points at the log).
- **Two audiences, two artifacts (maintainer's call, 2026-07-01).** Platterpus's
  app log lands in exactly two places — *not* redundant — and there is **no**
  standalone `.platterpus.log` sidecar:
  1. **Global** `~/.local/share/platterpus/log.txt` — a `RotatingFileHandler`
     installed once at startup by `logging_setup.configure_logging`, capturing
     every line since launch across *all* rips and *before any rip starts*. It's
     the cross-session catch-all for **program-level failures** — the only record
     when a rip never begins (a drive/permission/dependency problem, a crash
     during disc scan).
  2. **Per-album, embedded in the JSON** — this rip's session log lives *inside*
     `<Album>.platterpus.json` under `debug.lines` (scoped to this one album —
     other rips filtered out via the rip-epoch windows in `main_window_rip`, fed
     by the in-memory `SessionLogBuffer`). The JSON is the single, complete,
     self-contained **debug/LLM artifact** for that album's rip: verdict + every
     verification result + checksums + timing + loudness + read-speed history +
     the embedded log. **Humans read cyanrip's own `.log`/`.cue`** that sit beside
     it; the JSON is for machine/LLM consumption and deep debugging.
     The `SessionLogBuffer` is held at **DEBUG always**, independent of the
     Settings *debug logging* toggle (v0.4.13) — it's in-memory and bounded, so
     capturing DEBUG is free, and it means every report is verbose enough to
     debug from *out of the box* rather than only after a user enables the toggle.
     The toggle governs only the on-disk `log.txt`'s verbosity (item 1).
  We deliberately do NOT also write a plain-text `.platterpus.log` sidecar — it
  duplicated cyanrip's human `.log` (for people) and the JSON's `debug` block (for
  machines), so it earned its place in neither. The global log is the program-
  failure catch-all; the JSON is the per-album debug record. Removing either loses
  a case the other can't cover.

### 3.7a Error reporting — the design of record

> *"Do a full check for error reporting to both Cyanrip and Platterpus, as many and
> as full surface coverage as possible, even if you think it's not needed. I want
> full error and reporting to the output log file (JSON) as possible for future
> debugging. Be thorough and verbose; make finding errors easy."*
> — maintainer, 2026-08-04

§3.7 above is the *rule* in three bullets; this is the **design that satisfies
it**, and what each surface is for. `CLAUDE.md`'s *diagnostic completeness*
convention is the law; everything here is how the codebase meets it, written so a
reader can check rather than trust. **Read this before adding a failure path**;
the step-by-step recipe is in §4 (*Add a failure path*).

*(Absorbed the former `error-reporting.md` on 2026-08-06. It restated §3.7's
rules at length one screen away from them, which is the two-maps-one-territory
problem: a reader who found one had no way to know the other existed. Companions
are unchanged — [`testing.md`](testing.md) for the rules a change is held to,
[`dependency-contracts.md`](dependency-contracts.md) for what each external tool
may be asked and is expected to say.)*

#### The finding that produced all of this

Four parallel read-only audits ran on 2026-08-04: subprocess capture, swallowed
exceptions, the JSON report surface, and user-facing surfacing. They produced a
ranked list of about forty findings, and the striking thing is the shape they
share.

**Almost none of them were "we never obtained the fact."** They were *"we had the
fact and discarded it"* — which `CLAUDE.md` already calls the worse of the two,
because the artifact still **looks** complete. Three examples, in order of how
badly they read:

- `flac_verify`, `transcode` and `flac_recompress` each declared their injected
  command seam as `Callable[[list[str]], int]`. Each one's default runner captured
  the tool's stderr, logged a line or two, and dropped the rest. So a report could
  say *"FLAC verify FAILED for 3 file(s): a, b, c"* and could not say **what `flac`
  said about them**. Not an oversight at a call site — a **missing channel**, which
  no amount of care at the call sites could have closed.
- `metaflac` runs on **every** rip — it is how the user's edited tags reach the FLAC
  and how the cover art is embedded — and logged nothing at all on failure. The
  argv, the exit code and the output were discarded at the point of failure; three
  of six call sites then reduced the exception to a one-line warning, and one
  dropped its text entirely.
- The rip-failure report exists for rips that produced **no log at all** — the
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

#### The four obligations, and where each is met

`CLAUDE.md` requires four things of every external tool we run. Here is the code
that provides each.

| Obligation | Where |
|---|---|
| **Exit code, tri-state** — `null` for a child never reaped is a real answer and is never written as `0` | `adapters/tool_run.ToolRun.exit_code`; `diagnostics.Diagnostic.exit_code`; `outcome.ripper_exit_code` |
| **Exact argv as spawned** | `ToolRun.argv` (read off `proc.args`); `RipWorker._ripper_argv`, snapshotted *before* the read loop so a rip that dies in its first second still carries it |
| **Complete output, stderr merged** | `run_tool` uses `stderr=STDOUT`; bounded by `diagnostics.bounded_output` — head **and** tail, elision counted |
| **A sentence a person can read** | `ToolRun.summary`, `Diagnostic.message`, and the `*Failure.reason` on each adapter result |

**The bounding rule has one home:** `diagnostics.bounded_output()`. It had been
written **three** times with three different limits, one of them head-only — and a
head-only cap drops exactly the last line, which is where a tool puts its fatal
message. Head *and* tail, tail larger, elision counted and marked. **A silent
truncation reads as completeness.**

**Three states, not two.** `ToolRun.started` is the state the old `int` seam could
not express:

- **not started** — a missing binary. A problem with the *pass*: nothing was
  checked, so nothing should be blamed. Abort.
- **started, no verdict** — a timeout we killed. A problem with *this input*: the
  tool demonstrably works. Blame the file, continue, and **name the duration that
  was exceeded**.
- **started, exited non-zero** — the tool refused, and said why.

Collapsing the first two is how a missing `flac` came to be reported as a corrupt
FLAC.

#### The three surfaces, and what each is for

One collector feeds all three. That is the whole design: **two artifacts that
describe the same event differently is the drift this project keeps paying for.**

**`diagnostics.py` — the collector.** Every subsystem records a `Diagnostic`
(severity, namespaced `subsystem.what` code, message, detail, tool, argv,
tri-state exit code, where, track). **One `record()` call writes to two sinks** —
the text log and the report — so they cannot disagree. Four rules are encoded
rather than remembered: (1) recording also logs, not "and remember to log too";
(2) it **never raises**, because a recorder that throws while recording an error
destroys the evidence for the failure it was called about; (3) bounded, with the
truncation stated; (4) tri-state everywhere it matters. The log prefix is a fixed,
greppable token, and *"make finding errors easy"* is a literal instruction:
`grep 'platterpus-diagnostic' <log>` shows every problem the program noticed, in
order, without knowing a single subsystem name. The report's `log_grep_hint` field
prints that exact command with the **real** path.

**`log.txt` — the always-on, cross-session record.** INFO by default. **This is
why the level of a failure record matters:** a diagnostic emitted at DEBUG is
captured, enumerated in the JSON, and *invisible* in the one file most bug reports
contain. Failure records land at ERROR or WARNING; `tests/test_diagnostics.py`
asserts the level, not merely that something was logged.

**`.platterpus.json` — the per-rip bundle.** Schema v16. `diagnostics` sits
**third**, ahead of `outcome` and the verdict, because it is the first thing anyone
debugging a rip should read. `issues[]` is the severity-tagged derived list — the
thing a triager opens first — and it is derived from the *serialised* blocks, never
the raw results, so it can never disagree with what the report shows. `issues[]`
being empty means **"nothing reported a problem"**, which is *not* "everything was
verified". Every surface that renders it says so.

**`Help → Copy diagnostics…` — the surface for failures outside a rip.** The
per-rip JSON is the richer bundle, but it exists only for a rip and is reachable
only from the rip pane. A setup failure, a dependency-check crash, a failed update
or a drive probe had no copyable surface at all. This one renders the version
**pair**, the environment and every diagnostic recorded this session, from the same
collector.

#### The severity contract

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

#### Codes

`Diagnostic.code` is a stable, machine-greppable key: namespaced `subsystem.what`,
listed in `diagnostics.KNOWN_CODES`. The **message** is for a person and may be
reworded freely; the **code** is a contract, so a bug report can say *"seven
`ripper.stall_detected` in one rip"* without anyone parsing prose. An unlisted code
is **recorded anyway** — losing a real diagnostic to a taxonomy quibble would be
absurd — and logs a warning so the list stays honest. Because the runtime behaviour
is deliberately forgiving, the gate lives in the tests:
`test_every_wired_code_is_a_known_code`.

#### What is enforced, and by what

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

Two of the checks written that session were themselves wrong on the first attempt,
in the two ways `CLAUDE.md` predicts: the "see the log" sweep fired on a **comment
documenting a fix** — a check satisfied by the wrong thing; and the wiring sweep
reported `ctdb_client.py` as unwired because its import shares a line with another
name. It reads the AST now: **a matcher narrower than the language it inspects
produces confident wrong answers**, and a false failure trains people to ignore a
check as surely as a false pass lets a bug through.

#### What we ask of the ripper, and what it asks of us

The seam is bidirectional (`CLAUDE.md` rule 12), so error reporting is a
**bilateral** obligation, carried in the handshake rounds rather than assumed.

**What we already rely on, and now consume in full:** cyanrip's exit code, its
fatal-message inventory (the matcher is built from their published format strings
rather than any list either side maintains by hand — `ripper_messages.py`), the
`Invoked as:` line so a mangled argument is visible from both ends, and the build
tag in its version banner.

**What we commit to, in both directions:** print a diagnosable line on **every**
fatal path; capture the other side's exit code, exact argv and complete output;
flush before exiting; and **show the user the dependency's own sentence** rather
than a generic failure. *Capture without surfacing is the same bug from their
side* — 21 of cyanrip's fatal strings were captured and never surfaced once, which
is what `tests/test_ripper_error_surfacing.py` exists to prevent recurring.

**The open ask, carried into the round-7 lap:** seven of the ripper's refusal paths
fire *before* its logfile exists, so nothing in the archived log can show them, and
its heartbeat lines are stdout-only. We capture stdout for exactly this reason. The
question we owe them an answer to is whether those paths should be fixed by opening
the logfile earlier or documented in the provider contract as stdout-only — they
asked for our view rather than assuming, and either answer is fine as long as it is
*written down* on both sides.

### 3.8 Live status surfaces announce, focus-safely (accessibility)

A passive `QLabel`/banner that changes text is **invisible to a screen reader**
unless the widget takes keyboard focus — and stealing focus mid-rip is exactly
what an accessible app must never do. So every *live* status/verdict surface
(rip status line, verdict banners, CTDB line, wizard steps, install rows,
Settings validation, MB identification outcomes) also calls
`ui.accessibility.announce(widget, message)` — Qt's announcement event, the
desktop `aria-live`: spoken by assistive technology while focus stays put.
Rules when adding one:

- **Announce state changes, never repaints.** A percent/ETA tick is not news;
  throttle like `RipProgress.set_status` (dedup on `status_phase_key`, the
  clause before the "…") or on the full text for low-frequency lines.
- **Outcomes, not transients** ("querying…" is silent; "1 match: …" speaks).
- The helper **never raises**, feature-detects the Qt API, and is a cheap no-op
  offscreen — safe to call unconditionally; tests monkeypatch the *importing
  module's* `announce` name (§5.1) and assert on the messages.
- Also keep every affordance **keyboard-reachable**: Qt gives
  keyboard-selectable labels only `ClickFocus` (set `StrongFocus` explicitly —
  the disc-ID labels bug), QLabel links need `LinksAccessibleByKeyboard`, and
  prominent buttons carry unique `&`-mnemonics per window
  (`tests/test_ui_accessibility.py` pins the uniqueness).

### 3.8a Progress: the bar is a display, the estimator needs the raw signal

`RipWorker._progress_for` turns each ripper progress line into **two** numbers: the
album bar (0-100 across the whole rip) and the current operation's own percentage.
The album bar is deliberately **monotonic** — `_bump_overall` clamps it so it can
never go backwards, because a bar that retreats reads as a fault.

That clamp is fine for a bar and a trap for anything that *infers* from it. A secure
re-read (`-Z`) reads a track the bar has already counted, so `_overall_from_track`
returns a lower value and the clamp pins the album fraction for the entire re-read —
minutes at a time, by design, on a perfectly healthy drive. Two inferences read that
fraction and both described the clamp instead of the disc: the stall detector
announced *"stuck on a hard-to-read spot (a scratch or smudge)"* and the ETA divided
the remaining fraction by the leftover noise and reached 5h40m (measured twice in one
rip, 2026-08-05; `docs/testing.md` §5.ah).

So, when you add anything that reasons about rip progress:

- **Derive it from the raw per-operation percentage, or from a second signal** —
  never from the clamped album bar alone. `_note_task_progress` maintains both:
  `_task_forward_at` (the last time the operation's own percentage really advanced,
  which is *liveness*) and `_reread_pass` (how many times the current track's read
  has restarted, which is *why the album bar is pinned*).
- **A liveness check needs every signal to be quiet, not one.** Firing on a single
  quiet signal cries wolf; exempting a phase restores the hang the check exists for.
  `tests/test_rip_worker.py::test_a_genuinely_wedged_drive_is_still_reported_stalled`
  is the converse guard — keep one whenever you add a suppression.
- **When you cannot measure, hold the last value and say why.** `· verifying track 3
  (re-read 2) · about 54m left` is the shape: a number that stops moving with a
  reason beside it. Blanking the estimate reads as a hang; recomputing it from a
  pinned input is how both of the above happened.
- **Every branch of the estimator records an `eta_trace` sample, tagged with the
  branch that produced it** (`computed` / `held_*` / `rereading` / `stalled`). The
  first version recorded only fresh measurements, and the resulting holes in the
  shipped trace landed exactly on the minutes worth analysing.

### 3.8b Tables: size a column to what it *can* hold, not to what it holds now

`ResizeToContents` looks like the right answer for any column whose width should
follow its text, and it is — right up to the point where that text changes while the
user is watching. The Status column in the track grid changes on every track
transition, so the grid re-laid-out roughly **twice per track**, sliding the Title
text sideways 28 times over a disc (measured 2026-08-05; `Status` swung 48 → 67 → 53
px and the stretch columns absorbed it).

The pattern that replaced it, and the one to follow for any new grid:

- **One column stretches. Every other column is `Interactive` at a computed width.**
  `Interactive`, not `Fixed`, so the user can still drag; what they cannot get is the
  table rearranging itself under them.
- **Compute the width from the widest string the column can EVER hold**, and derive
  that from the same table the cells render from — `track_table.status_column_width`
  reads `_STATUS_DISPLAY.values()`, so adding a status widens the column with no
  second list to update. A hand-written list of specimen strings is a copy, and it
  goes stale silently because a narrow column elides rather than errors.
- **Size for the domain, not for this disc.** The `#` column is sized for `"99"`, not
  for the disc's own highest track, so a 9-track and a 14-track disc render
  identically — otherwise the column changes width *between* rips instead of during
  one.
- **Recompute on a DATA change, never on a status change.** `_apply_column_widths` is
  called from `set_release` / `set_placeholder_tracks` / the album-artist
  propagation, and from nowhere else.
- **Two `Stretch` columns split the remainder evenly**, which is almost never what you
  want: it gave a column repeating `"The Police"` the same width as the column of long
  varied titles. Stretch the one that needs the room; size the other to its content
  with a **cap** (a share of the table) so an outlier row cannot crowd the first out.
- **The pure width functions take a `measure` callable** so they are testable without
  a laid-out widget, and the widget wrapper is a thin `resizeSection` loop that never
  raises — geometry polish must not be able to take a rip down.

And one Qt fact worth knowing before you tune anything: **`QSplitter.setStretchFactor`
distributes only the space left after each pane's `sizeHint`.** When the hints already
fill the window the factors are inert — measured across four factor sets and four
window sizes with byte-identical results. If a pane opens too small, `setSizes()` on
first show is the lever, not the factors (`main_window._apply_pane_shares`); apply it
**once**, or it silently undoes the user's dragging.

### 3.9 Variable-length panes: wrap the labels, give it one scroll surface, and never nest two

Two distinct failure modes, one root cause: **a widget whose content length is
data-dependent will demand more room than the window has, and Qt's response to
"not enough room" is not what you would hope.** Both shipped (fixed in v0.5.14
and v0.5.15) and both were invisible on a maximised window.

#### The vertical half: a layout that runs out of room *overlaps*

**A `QVBoxLayout` given less height than its children's minimums does not clip
and does not scroll — it overflows, and overflowing means sibling rectangles
collide and paint over each other.** That is what "the text is on top of other
text" actually is.

Worse, the pane can under-report what it needs, so this can happen even at the
pane's own stated minimum: **a word-wrapped `QLabel`'s `minimumSizeHint()` height
is one line, while its `heightForWidth()` is two or three.** The layout computes
the pane minimum from the one-line figures, then allocates using
height-for-width, and the difference is the overlap. Measured on `RipProgress`
with a real rip log at 940 px wide: minimum height reported **326 px**, height
actually allocated **~405 px** — and below 326 px the verdict banner was drawn
across the live-log box and the CTDB line across the AccurateRip table.

**So: any pane whose text length depends on the data needs a scroll surface**
(`QScrollArea`, `setWidgetResizable(True)`, `QFrame.Shape.NoFrame`). That converts
"not enough room" from a paint collision into a scrollbar, and keeps the pane's
own minimum small so a long report never dictates a tall window.

> **Rejected alternative, so nobody re-derives it:** teaching every wrapped label
> to report its true height-for-width *does* remove the overlap — and drives
> `RipProgress`'s minimum height to **1418 px**, demanding a window taller than
> most screens. Measured before choosing.

A pane whose minimum is already honest needs no scroll area — `DiscInfoPanel` is
a grid of short values and was measured clean at every size down to 300×80. Don't
add one reflexively; measure.

#### The corollary: **never nest one scroll surface inside another**

Wrapping the whole of `RipProgress` in one scroll area fixed the overlap and
immediately caused the next complaint, because a `QTableWidget` and a
`QPlainTextEdit` *are* scroll areas: inside the outer one they became nested, and
the pane showed **two vertical scrollbars 15 px apart** (measured at x=911 and
x=926 on a 940×400 pane) with the wheel acting on whichever the pointer was over.

The repair that looks obvious does not work. Sizing the table to its content and
setting `ScrollBarAlwaysOff` removes the second bar — and **a nested scroll area
with nothing left to scroll does not pass the wheel on to its parent** (measured:
an exhausted inner area left the outer one at 0; overriding `wheelEvent` to
`ignore()` did not help, because `QAbstractScrollArea` handles the wheel in
`viewportEvent` on the *viewport*). So you trade a visible scrollbar for a **dead
wheel zone** over the biggest widget in the pane, which reads as more broken, not
less.

The structural answer, and the shape `RipProgress` now has:

| band | contains | scrolls? |
| --- | --- | --- |
| **header** | progress bars, status line, the trust verdict, warnings | no — fixed, always on screen |
| **body** | a `QTabWidget`: *Tracks* (table), *Details* (a scroll area of prose), *Live log* (console) | one tab visible ⇒ at most one scroll surface, never nested |
| **footer** | the output buttons | no |

Rules when you extend it:

- **Put a new scrollable widget in its own tab, or in the fixed header if it
  cannot scroll.** Never inside another scroll area.
- **A tab must not become where warnings hide.** Anything behind an unopened tab
  is invisible, so mark the *tab label* — `_refresh_details_tab_marker` puts a ⚠
  on "Details" whenever a caveat lands there. Mark warnings only; marking neutral
  information trains the user to ignore the marker.
- **The tabs follow the task.** `begin_rip` shows the console, `set_rip_log`
  brings the results forward. A tab the user has to go and find is worse than a
  cramped column.
- **`isHidden()`, not `isVisible()`, when you ask "is this widget switched off?"**
  A widget in a background tab is not *visible* even while it holds text, so
  `isVisible()` answers a different question than you meant. (The same
  distinction silently cost 18 px in the table's content-height formula, where
  `horizontalHeader().isVisible()` is False before the widget is shown.)

#### The horizontal half: an un-wrapped label dictates the minimum width

**Every `QLabel` that displays a value or a message the program generates at
runtime gets `setWordWrap(True)`.** This is not cosmetic. An un-wrapped label
reports its *entire single line* as its `minimumSizeHint`, a minimum that
propagates up through every containing layout to the window — so the longest
string that label is ever handed becomes **a width the user cannot resize below**.

This shipped (fixed in v0.5.14). Measured on the real widgets: the results pane's
status label took `RipProgress`'s minimum width from **366 px to 906 px** the
moment it held a genuine end-of-rip status, and `DiscInfoPanel`'s value labels
took its minimum from **208 px to 575 px** with real post-rip values.

> **A correction worth keeping, because the mistake is instructive.** v0.5.14
> fixed this and was reported as the fix for the overlapping text — it was not.
> A stuck minimum *width* makes the window refuse to narrow; it does not by
> itself put text on top of text. That was the vertical mechanism above, and
> wrapping a label slightly *increases* vertical demand (a second line), so the
> width fix marginally worsened the symptom it was credited with fixing. The two
> are complementary — wrapping is what lets the scrolled content re-flow narrow
> instead of growing a horizontal scrollbar — but they are different bugs on
> different axes. **Reproduce the symptom before believing a diagnosis**; the
> tell here was that the report said *smaller*, not *narrower*.

- **Wrap dynamic text; leave fixed captions alone.** A field *name*
  ("MusicBrainz ID") is short, never changes, and its width *is* the column, so
  it stays un-wrapped on purpose. The rule is about text whose length the code
  does not control.
- **Wrapping does not break identifiers.** A disc ID or a CRC is a single token
  with no spaces; Qt still reserves its full width and never splits it. Only
  genuine sentences re-flow.
- **Test the invariant, not the pixels.** Assert that *the same vocabulary
  repeated N times does not change* `minimumSizeHint().width()` — a wrapped
  label's minimum is its longest single **word**, which is irreducible and
  font-dependent, so an exact-pixel expectation is not portable across CI fonts.
  Each pane also carries a fitness test walking `findChildren(QLabel)` and
  failing on any un-wrapped label holding a long dynamic string, so a new label
  cannot reintroduce this silently. No window needs to be shown for either.

### 3.10 Unattended testing: the script console, and why a subsystem needs a surface

**The rule this section exists to state:** *a subsystem is not shipped until
something in the application can reach it.* `docs/testing.md` §5.p says a
documented capability is not a capability; this is the same rule one step
earlier — an **implemented** capability is not a capability either.

`src/platterpus/uiscript/` was built to a maintainer request, with a parser that
never raises, a closed verb vocabulary, a `QTimer`-driven runner, a transcript
renderer and its own test file. It shipped with **no menu item, no dialog and no
CLI flag**: `grep -rn 'uiscript' src/ --exclude-dir=uiscript` returned nothing.
The changelog announced it, so from the outside it looked delivered. The check
that would have caught it is one line — *does anything import this?* — and it is
worth running on any package added as "the subsystem for X".

**The shape now, and the seam to extend.**

```
uiscript/script.py    parse(text) -> [Step]        pure, never raises
uiscript/verbs.py     VERBS, OPENABLE, reference   the single vocabulary table
uiscript/runner.py    ScriptRunner(window)          one step per event-loop tick
uiscript/report.py    RunReport -> text / dict      the transcript
ui/dialogs/script_console.py                        the SURFACE (menu, buttons)
```

Three entry points, **one method**: the Tools menu item, `--run-script FILE`, and
the config's `test_script_autorun` all call
`MainWindow.open_script_console(autorun=...)`. Adding a fourth (a D-Bus hook, a
hotkey) means calling that method, never re-describing how a batch starts.

**Adding a verb** is a table row in `verbs.py` plus a `_do_<name>` handler on
`ScriptRunner` — and the two are swept against each other, in *both* directions,
by `tests/test_uiscript.py`: a verb flagged `implemented` must have a handler, and
a handler must not exist for a verb flagged otherwise. That sweep exists because
13 of 25 verbs once parsed, arity-checked, passed the unsafe gate and then failed
at **run** time, which for an unattended batch means dying mid-run against a
reference that promised the command would work.

**Two hard constraints on any new verb:**

1. **Nothing blocks the tick.** The runner lives on the GUI thread and its whole
   design (§3.2) is that a modal dialog's nested event loop still delivers timer
   events. A verb that needs a subprocess starts it on a daemon thread and lets
   the tick poll — see `_CyanripJob`, and note that the first version of the
   `cyanrip` verb did *not* do this and argued for the exemption in a docstring.
2. **Any route to the ripper re-establishes the argv chokepoint by delegating to
   it.** `sanitise_cyanrip_args` calls into the same refusal
   `assert_metadata_lookup_disabled` raises, byte-for-byte, and a test asserts the
   text is identical. A second copy of a safety check is a second thing to drift
   (Critical rule #12, the outbound half).

### 3.11 Say what you are about to do, not only what you did

`rip_plan.describe_rip_plan` emits a `[plan]` block before a rip spawns anything.
It is worth understanding as a *pattern*, because the failure it addresses recurs
wherever this app decides something on the user's behalf:

- The app builds the ripper's argv, so the flags are **our** decision.
- The only record of that decision was the finished artifact — post-mortem.
- One setting had two modes hiding inside one on/off (`-Z` on at 2, but *dynamic*:
  pass 1 carries no `-Z`), so "on" was true and uninformative.

The plan is a **pure function of the parameters** and deliberately *not* a second
argv builder. It describes the builder's inputs and the one decision the worker
makes above it, naming the flag each becomes. That gives two independent records
of the same choice — the plan and the log's `Invoked as:` — and a disagreement
between them is a finding you can only notice because both exist. It also states
the flags we never send (`-j`, `-x`) **positively**, because "absent from the
plan" and "we never send it" look identical to a reader.

Reach for this whenever a surface would otherwise only be able to report a choice
after the cost of acting on it has been paid.

### 3.12 Constructing a window is not the same event as starting the application

Anything that can **interrupt a person** — a modal, a notification, a check that
ends in a prompt — is armed from `app.py`'s launch path, never from
`MainWindow.__init__`. `refresh_drives()` and
`schedule_ripper_update_check()` are both called from there, and both say so in
their own docstrings.

**Why it is a rule and not a preference.** The suite builds `MainWindow` directly
in dozens of tests, and several then spin a nested event loop. The automatic
cyanrip check was first armed by a `QTimer.singleShot` in `__init__`; the timer
fired inside one of those loops, the check found no fork ripper, produced a
one-click install offer, and `exec()`d a `QMessageBox` **with nobody to click it**.
The suite stopped dead and stayed there (measured 2026-08-18).

The tempting fix is a test-mode flag the harness sets. **Do not** — it would hide a
real hazard behind a green suite: a dialog that can appear at a moment nobody
chose is a product defect wherever it happens. "A window object exists" is a fact
about memory; "the application started" is a fact about a user sitting down. Only
the second one licenses interrupting them.

**And moving it was only half the fix — the more important half is below.** With
the timer armed from `app.py` the suite hung *in exactly the same place*: some test
drives the real launch path, so the timer was still pending when an unrelated test
called `processEvents()`. Chasing the *scheduler* was chasing the trigger; the
defect was in what the callback did.

### 3.12a A dialog raised from a queued signal uses `open()`, never `exec()`

`exec()` runs a **nested event loop**. That is fine for a dialog a user opened from
a menu — the click is the outermost thing happening, and blocking until they answer
is what a modal means. It is wrong for a dialog raised from a *timer* or a
*worker's `finished`*, because the nested loop is then spun inside whatever the GUI
thread was already doing — a repaint, another dialog's loop, a test's
`processEvents()` — and it does not return until somebody answers. Nothing
guarantees anybody will.

This is the GUI-thread rule arriving from a direction §3.2 does not cover: not *a
slot doing blocking work*, but **a slot becoming blocking work for its caller**.
The `_install_dialog` pattern in `main_window_update.py` already avoids it for the
app's own updater; `_offer_ripper_install` now does too:

```python
self._ripper_offer_box = box          # held on self — the handler outlives this call
box.buttonClicked.connect(self._on_ripper_offer_answered)   # bound method, GUI thread
box.open()                            # shows and RETURNS
```

The state the handler needs (which build, which offer) lives on `self` for the same
reason: a callback that must survive the call that created it cannot close over
locals. `tests/test_ripper_update_worker.py` asserts this on the source, because a
behavioural test for "did it not hang" is a test that hangs when it fails.

**The general question to ask of any new dialog:** *who is on the stack when this
opens?* If the honest answer is "whatever happened to be running", it is `open()`.

**And the companion question: is anybody there to answer it?** An unattended
`--run-script` session drives this same GUI for 30–50 minutes with nobody watching,
so anything that can raise a dialog must stand down for it — `app.py` does not arm
the automatic ripper check when a script is in play. A modal in an unattended run
does not merely annoy: it blocks the batch, and if answered it can change the
system under test *while the test is running*. Whenever you add something that can
interrupt, check it against all three: **a person is here** (`self.isVisible()` — a
timer armed at launch fires seconds later, and the window may have been closed by
then), **they are not busy** (no rip running, no script driving), and **they asked
for this or it is important enough to ask anyway**.

All three were learned the same afternoon, each from a different surface, each
after the previous one looked like the whole fix. `_maybe_check_ripper_updates`
carries them in that order with the incident behind each.

Two corollaries, both cheap:

- **Deferred work must re-check its preconditions when it fires, not when it is
  scheduled.** A delay long enough to be useful is long enough for the world to
  change — the automatic check stands down if a rip started in the meantime,
  because the user came to rip a disc and the install it offers would replace the
  binary doing the ripping.

  **This paragraph was written before the code did it, which is the whole lesson.**
  The three conditions were checked in `_maybe_check_ripper_updates` — the *arming*
  slot — and never in `_on_ripper_update_result`, the slot that actually raises the
  dialog. So the rule was stated one screen from the code that violated it, and the
  method's own docstring asserted *"It does not run during a rip"* as a property of
  the flow when it was a property of one instant. A comment where a check belongs is
  not a fix; found by review the same day it was written.

  **Count the deferrals, and guard the longest one.** There are two here and only
  the short one was obvious: the 8-second timer, and then the *worker's own latency*
  — a manifest fetch plus a `distrobox enter` version probe at 60 s per flag. The
  second is the one where a user inserts a disc and starts ripping. Whenever work is
  handed to a thread, its completion is a second deferral, and the precondition has
  to be re-read there.

  The conditions are a **named method returning a reason** (`_interruption_blocker`),
  not three copies of an `if`, so both call sites ask the same question and every
  refusal can say which condition refused. And there are **three**, not two: *a
  person is here*, *they are not busy*, *nothing else has the floor* — the third
  because a launch-armed timer fires inside the first-run setup question's nested
  `exec()` loop, and a window-modal box stacked on an application-modal one is
  input-blocked with both answers still pending.
- **A worker that was cancelled must produce nothing actionable.** `cancel()` comes
  from `closeEvent`, so its late `finished` lands in a window that is going away.
  It still has to *emit* — a worker that never finishes is a thread `stop_thread`
  cannot join (rule 9) — but it emits a verdict with no action attached.

### 3.13 Reporting is a feature: the one file a user sends

**The rule.** *Every manual step in a reporting procedure is a thing the software was
supposed to do.* `CLAUDE.md` states it for instruction files — *"never hand back an
instruction file… hand back three steps and a file to run"* — and the same reasoning
applies to what comes back the other way. "Send me the log, the report, the cue and a
screenshot" is four manual steps and a compression, and a folder upload that silently
drops one file is indistinguishable from a step that never ran.

So: **every rip writes one `.tar.gz`, on every outcome**, and the UI hands the user its
location. `evidence_bundle.py` builds it; `main_window_rip._write_evidence_bundle_async`
is the only caller for a rip and `uiscript.runner._write_run_bundle` the only one for a
test-script run.

**If you add an artifact, four things are already decided for you.**

1. **Hook at the single point every outcome passes through, not at the happy one.**
   The rip's call sits inside `_on_rip_finished`'s `finally`, so it also runs for a
   cancel, a failure, and the path where the finish handler itself raised. The rips
   worth sending are exactly the ones a *"write it when we finish nicely"* hook skips.
   Two call sites — one for success, one for failure — would be two things that can
   disagree about what a bundle contains.

2. **Filter by allowlist, never denylist.** Critical rule #8 forbids copyrighted media
   leaving in anything we generate, and the bundle walks a folder that is by definition
   full of FLACs. A denylist of audio extensions is wrong the first time a format nobody
   listed appears, it fails **open**, and it fails **silently**. `ALLOWED_SUFFIXES` is
   text-only; anything else is excluded *and counted*.
   The widened set that admits our own screenshots (`EXTRA_DIR_SUFFIXES`) applies only
   to directories a caller names explicitly, and the album folder is never one — an
   album folder's `cover.jpg` is record-label artwork, so widening globally would sweep
   it in as an invisible side effect of a screenshot feature.

3. **Name every omission.** A file that was missing, unreadable, over the cap or the
   wrong type gets a `MANIFEST.txt` row with its reason. A bundle quietly holding eight
   of eleven artifacts looks exactly like a complete one, and the reader draws
   conclusions from the gap. Same rule as `diagnostics.py`: *a silent truncation reads
   as completeness*, and where a file must be bounded it keeps **head and tail** with a
   counted elision, because a tool's fatal message is the last thing it prints.

4. **Off the GUI thread, and it never raises.** Gzipping a 4 MB log plus its rotations
   is not a few-milliseconds operation (§3.2), so it runs on a plain daemon thread —
   not a `QThread`, which would add a `closeEvent` teardown obligation (rule #9) for
   work that owns no Qt object. And a convenience wrapped around a rip that has already
   finished must never surface as a crash after a successful one: `build_bundle` returns
   a `BundleResult` carrying `error`, and the caller reports it.

**Why `evidence_bundle.py` is Qt-free.** The caller passes in whatever in-memory text it
wants embedded (`extra_text` — the diagnostics blob) rather than the module reaching into
the UI for it, and owns the thread. That is what makes the whole thing unit-testable
without a `QApplication`, which is where its audio-exclusion guarantee is actually
asserted (`tests/test_evidence_bundle.py`).

**The archive's name follows the cross-machine artifact rule** — lowercase ASCII letters
and digits only (`CLAUDE.md` → *Artifact filenames that cross machines*). It is going to
be named in a chat message and typed into a file dialog, which is exactly the crossing
that cost a rig run once.

## 4. Extension points — how to add things

> The goal: a contributor who has never spoken to the author can add a
> capability by following one of these recipes, without touching unrelated
> code.

### Add a ripping backend (e.g. a future `XyzripImpl`)
cyanrip is currently the **sole** backend (KDD-18 — whipper was removed
2026-06-30), but the `RipBackend` ABC seam is kept exactly so another engine
can be slotted in without rewriting the GUI:
1. Implement the `RipBackend` ABC in `adapters/xyzrip_backend.py`
   (`rip`, `disc_info`, `version`, optional `find_offset`/`analyze_drive`).
2. Add a parser in `parsers/` for its log + disc-info output (named-group
   regex, never-raise, + a property test). Map it onto the shared `RipLog` /
   `DiscInfo` dataclasses so the GUI verdict code is unchanged.
3. Reintroduce a selection mechanism in the **composition root**
   (`composition.build_backend`, the one place that constructs the backend —
   it currently hard-returns cyanrip). A `Config` field + a Settings control
   would feed it; both `app.py` and `preflight.py` get the new backend for free
   because they share that root.
4. If it needs a package, add a wizard step in `deps/host_setup.py` and CLI
   parity in `setup-host.sh` (keep the two install stanzas in sync).
5. Gate any backend-specific Settings widgets in `settings_dialog.py` — grey
   out, explain, never lose values. (The whipper-era `_apply_backend_capabilities`
   gating was removed when cyanrip became sole; reintroduce that shape if a
   second backend returns.)

A **backend-specific rip parameter** (one backend has a flag another lacks)
threads through one fixed path: `Config` field → `RipParameters` (frozen) →
the `RipBackend.rip()` ABC signature → each adapter's argv builder. A
backend with no equivalent **accepts and ignores** it (`del param`), and its
Settings widget is greyed out for that backend. `secure_rerip_matches` (cyanrip
`-Z N` "re-rip until N reads match", for marginal discs) is the worked
example — copy its shape for the next one.

> **Comment hygiene after a backend swap (hard-won, 2026-06-30).** When whipper
> was removed, dozens of docstrings/comments still said "whipper does X" as if
> describing *current* behavior — false for the next reader. The convention:
> comments describe what the **current** backend does; the old tool appears only
> as accurate *history* explaining why code is shaped a certain way (e.g. "this
> parser reads whipper-FORMAT logs, kept for old logs/fixtures"). When you swap
> or remove a backend, grep the whole tree for its name and re-audit every hit —
> a stale "current-behavior" claim is a bug in the docs.

### Add an output format
WavPack, MP3, and WAV already ship (KDD-22); FLAC is the always-produced lossless
**master** and other formats are *derived* from it by a post-rip transcode
(`adapters/transcode.py`). To add another (e.g. ALAC, Opus): add it to
`transcode.py`'s `_FORMAT_EXT`/`_build_argv` (one ffmpeg branch), add the value to
the `Config.output_format` choices + the Settings combo, and round-trip it in
`SettingsDialog.to_config()` (exposing a config field is incomplete until
`to_config` carries it — KDD-22). The transcode runs **last** in the post-rip
daemon thread (after tag → cover → re-compress), writing sibling files so it can't
race the metaflac steps. Route any new encoder binary through the dependency
subsystem (no bespoke install code, Critical Rule #6 + #4).

### Add a dependency
Register it in `deps/registry.py` with its probe and install tiers. Mark it
`optional=True` if its absence shouldn't nag. Nothing else changes.

### Add a parser of external output
New module in `parsers/`, named-group regex, return a dataclass, never raise,
add a property test. If it feeds a verdict, extend `fidelity_summary` in
`main_window_helpers.py`.

### Add a failure path
The design and the *why* are §3.7a; this is the five-step recipe. It lives here
rather than trailing the design prose because a contributor adding a failure path
is doing an *extension*, and extensions are looked up in this section.

1. Pick or add a code in `diagnostics.KNOWN_CODES` (`subsystem.what`).
2. Record it — `diagnostics.error/warning/info`, or `record_command_failure` for
   an external tool, which takes all four obligations in one call. **Do not**
   hand-roll the four; a per-call-site version is how four facts drift to three.
3. If it should appear in `issues[]`, add a check to `rip_report._issues` reading
   the **serialised** block, and a regression test for that code.
4. If a user sees it, append `ui/failure_text.LOG_POINTER` — do not write your own
   sentence, and do not type out the path.
5. Ask the pre-flight question that applies here: *"is the user's symptom gone, or
   just the mechanism I named?"* A capture with no surfacing is not a fix.

### Verification & parity (the "prove it" surfaces)
"Is this track AccurateRip-verified?" has **one** definition for the whole app:
`parsers/rip_log.accuraterip_is_match` / `track_accuraterip_verified`
(**confidence ≥ 1** — a real match always has it; "not present" has `None`/`0`).
It can only ever under-claim, never fabricate a match. The whole-disc verdict
(`platterpus.verdict.accuraterip_verdict` → `(message, level)`) builds on it and
lives in its own Qt-free module so every surface shares it: the colour-coded
**verdict banner** above the results table (`ui/rip_progress` re-exports it), the
disc-info panel, the status-line `fidelity_summary`, the EAC-style log renderer,
and the **JSON rip report** — so they can never disagree (a past bug had the disc
panel string-match "exact match", which silently under-counted cyanrip rips).
Don't re-derive "verified" anywhere else; call the shared helpers.

**Two outputs every time:** beside the backend's human `.log`, Platterpus writes
a machine-readable **`<name>.platterpus.json`** rip report
(`platterpus.rip_report`, pure + never-raises; `scripts/rip_report.py` is the
CLI) carrying the drive/rip settings, per-track CRCs + AccurateRip results, the
shared verdict, and the CTDB result. `_on_rip_finished` writes it first
(AccurateRip); then each async post-rip check (CTDB, FLAC-verify, transcode,
derived-verify, re-compress, checksums) re-writes it with its result as it
finishes — the re-writes coalesce onto a debounce timer
(`_schedule_rip_report_write`), and each write passes *all* accumulated results
so a coalesced write is never lossy. QA / re-verification / repair tooling
consume the JSON; humans read the log.

**The JSON has to be diagnosable ALONE (schema v12).** It is the file a user is
asked to attach to a bug report, and until v0.6.0 every real diagnosis still
began with "can you also send me the `.log`?" — the report was 164 KB of good
structured data and still lost to a 4 KB text file it did not contain. So it now
embeds the verbatim text of the three companions written beside it, via
`platterpus.report_artifacts`: cyanrip's own `.log`, our EAC-layout render, and
the `.cue`, each with a byte count and a SHA-256 **of the bytes on disk** (not of
the possibly-truncated text — a digest of something no file ever contained looks
checkable and isn't).

Two invariants that module exists to hold, both worth preserving if you extend it:

- **Text only, by allowlist.** `EMBEDDABLE_SUFFIXES` is a closed set, not a
  "anything but audio" denylist, because a denylist fails *open* on the format
  nobody thought of. Critical rule #8 says no copyrighted media ever leaves in an
  artifact we hand around, and "the caller passes the right path" is not a
  guarantee — a rejected path is recorded with its reason rather than raising
  inside a rip's finish path, so the refusal is visible in the output it protects.
- **Absence is data.** A file that isn't there gets `exists: false` and keeps its
  `path`, because "cyanrip wrote no cue" and "we didn't look for one" are
  different findings and an omitted key cannot tell them apart. A zero-byte file
  is present-and-empty, never folded in with missing — the 0-byte `.cue` a
  cancelled rip leaves behind is invisible in a summary and obvious in a byte
  count.

Ordering matters when you add an artifact: the EAC-layout log is written *after*
the report's first write, so `_write_eac_log` re-arms the debounced report write.
Without that the single uploaded file would say `eac_log.exists: false` about a
log sitting directly beside it — the report would be wrong about its own folder.

The same release added `report["completeness"]`, which records `tracks_expected`
(what the rip was *asked* for) rather than leaving `len(tracks)` as the report's
only track count. See `docs/testing.md` §5.n for why that is a category of bug
and not a one-off.

**Facts the app learns *after* the ripper's log is written must be folded in
before rendering.** The backend's `.log` is a snapshot of one rip pass, but
Platterpus keeps learning after it: a measured cache-defeat verdict lives in the
drive profile, a cancelled rip's real status lives in the worker outcome, and the
per-track auto-fix re-reads tracks *after* the whole-disc log exists. Each of
those was, at some point, a shipped honesty bug — a log that said "(unknown)"
about something we knew, one that read as complete when it wasn't, one that
dropped a Test & Copy proof we had earned. So `_on_rip_finished` runs the parsed
`RipLog` through small **enrichers** (`_inject_measured_cache_defeat`,
`_apply_auto_fix_results`) *before* the report and the EAC-layout log are
written, and passes late-known context (`outcome_status`, `disc_track_total`,
`secure_rerip`) into the renderer. The contract for any new one: `dataclasses.replace` onto a frozen
copy, never raise (a provenance touch-up must not abort the post-rip chain), and
only assert what the *shipped bytes* earned — e.g. a converged re-read that never
replaced the album's file proves nothing about the file that's still there. When
you add a post-rip fact, ask *which renderings need telling?* — the answer is
usually all of them, and the bug is always the one you forgot.

> **This is not hypothetical, and the trap has a specific shape.** The 2026-07-28
> audit found the `outcome_status` wiring had *never* worked: `_last_outcome` is a
> dict, the call site read it with `getattr`, and the INCOMPLETE RIP banner
> therefore could not render on any real rip — through four releases, with a green
> test suite, because the regression test called `render_eac_style_log` directly
> with `outcome_status="cancelled"` instead of going through `_write_eac_log`. A
> test that passes the fact in by hand proves the renderer honours it; it proves
> nothing about whether anything ever *tells* it. **Test the wiring, at the call
> site.** The same audit found `interrupted` reaching the JSON report and not the
> log — the "which renderings need telling?" question, answered incompletely.

Of the two, one *fills* a missing value and must never overwrite what the log
itself said (`_inject_measured_cache_defeat`). The other deliberately
**replaces**:
when the per-track auto-fix swaps a re-read into the album, the first-pass record
describes bytes that no longer exist, so `_apply_auto_fix_results` folds the
*re-rip's own* parsed record over it (`_merge_shipped_track` — a pure module
function naming every field explicitly, so the rule reads line by line and the
type checker verifies each one). The distinction is the question *whose read is
this record about?* — fill when the log simply didn't know a fact, replace when
the log is describing the wrong bytes. Even then: identity fields never move, and
a field the re-rip's log didn't report can't erase a real one, because deleting a
known fact is worse than the stale value you're fixing.

**Parity vs EAC** is measured, not claimed: `platterpus.parity` /
`scripts/eac_parity.py` compare a rip log's per-track Copy CRC against the
committed EAC baseline in `output_reference/` (format auto-detected, EAC's UTF-16
handled). `tests/test_parity.py` pins the committed cyanrip-vs-EAC result (12/14;
T3+T5 differ) as a no-hardware regression guard. `scripts/render_eac_log.py`
renders our rip into an EAC *layout* (clearly attributed, **never signed** — an
EAC-signed log would be provenance forgery) so the two can be eyeballed
side-by-side.

**Re-rip comparison ("you've ripped this disc before").** Platterpus is
stateless per rip, so it can't natively tell you a re-rip came out *different*
from last time — but the `.platterpus.json` reports remember, and
`platterpus.rip_compare` (pure, never-raises) diffs two of them: per-track
byte-identity, and a **better-master** call (exact AccurateRip match >
offset-variant > not-in-DB, confidence tiebreak, genuine ties left `unknown`).
It reads trust straight from each report's `accuraterip_verified` flag — the
*same* shared definition above — so it can never contradict the rip it compares.
Discovery (`find_prior_report`) keys on the **TOC-derived disc IDs** now in the
report's `rip` block (`musicbrainz_disc_id`, then `cddb_id`, then the MB
release id) — a physical-disc key that's stable across re-rips, unlike the
release id. Same disc is necessary but *not sufficient*: a candidate is also
classified by its own `outcome.status` (`report_completeness` → complete /
partial / abandoned), and discovery ranks **completeness before recency**. An
`in_progress` report is the rip worker's durability snapshot of a rip that never
ended (window closed mid-rip, power loss), so it is never auto-selected — it
carries the newest timestamp in the library and would otherwise hide the user's
real prior rip and warn about the tracks it never reached. A `cancelled`/`failed`
prior *is* used — those CRCs are real reads — but only when no complete prior
exists, and `compare_reports` then labels the result and stops counting the
tracks the short side never got as changes. A report with **no `outcome` block**
(pre-v7) counts as complete: in those versions only the rip-finished handler ever
wrote one. Three surfaces consume it: the `--compare` CLI, the results-pane
banner after a rip (discovery scans the library, so it runs **off the GUI
thread** via `_launch_post_rip_daemon` and reports back through the queued
`rip_comparison_done` signal — same pattern as CTDB verify), and the
`--assemble-best-of` CLI (a **non-destructive** per-track copy of the better
rip into a new folder; it never touches the sources). To extend it, add fields
to the report and read them in `compare_reports`; keep the module Qt-free and
never-raising.

### Add a metadata or art source
New adapter behind a small interface (mirror `MusicBrainzClient` /
`cover_art`). Query it on the host (Critical Rule #5: the GUI resolves the
release, never the ripper's interactive prompt).

## 5. Testing contract (the safety net that lets us refactor fearlessly)

> **The full strategy, taxonomy, and Definition of Done live in
> [`testing.md`](testing.md)** — authoritative. This is the quick reference.

- `pytest` from the repo root (no env vars — `pyproject.toml` sets
  `pythonpath = ["src"]`); the suite touches no real hardware, network, or
  container. CI enforces **branch coverage with a hard floor**
  (`--cov-fail-under`, 91, ratchets up) on Python 3.11–3.14, plus `ruff`
  lint + format, the gating `mypy` typecheck (strict def-typing,
  `pyproject.toml [tool.mypy]`), and the changelog / media-guard /
  `pip-audit` backstop jobs.
- **Institutional rules:** every shipped bug gets a regression test in the
  same change; every new external-output parser gets a never-raises property
  test.
- **Inject fakes through the adapters** (backend/MB/metaflac) so worker and
  window tests run deterministically and offline. GUI tests use the shared
  `qapp` fixture (`tests/conftest.py`) under `QT_QPA_PLATFORM=offscreen`.
- **Drive signals synchronously in tests.** Qt signals are callable without an
  event loop; with direct connections, slots fire immediately — assert on
  collected emissions. For threaded code, stash the thread on the object and
  `join()` it rather than sleeping. **Stub anything that would touch the
  network or a real subprocess** (the update downloader, the cover-art
  fetcher, `gio`/`kbuildsycoca`) — an unstubbed one can hang the suite.
- Keep tests fast and order-independent — a test that only fails after another
  ran is a real defect (it caught a Qt re-entrancy crash here).

### 5.1 When you move code between modules, move its monkeypatch targets too
`monkeypatch.setattr(some_module, "free_function", fake)` only affects callers
that resolve the name *through that module*. If a method moves to a new
module, patch it there — or patch the function's *source* module and call it
module-qualified (e.g. `offset_config.is_offset_configured(...)`) so one patch
point covers every caller. A patch that silently stops intercepting is how the
2026-06-13 `RipMixin` extraction briefly let a test start a real rip thread.
Patching an attribute *on a shared module object* (`drive_control.eject_drive`)
is unaffected by where the caller lives.

This isn't only about *methods* moving — a **shared helper** relocates name
resolution too. When `cyanrip._run` was routed through `whipper_backend.run_capture`
(2026-06-22), `subprocess.run` began resolving in `whipper_backend`, so the
cyanrip tests' `subprocess.run` patch had to move there with it (the helper
now lives in `adapters/rip_backend.py` — today's patch point). The mirror-image
trick is to design the helper so it *doesn't* relocate the patchable seam: the
`workers.start_worker_thread` helper takes the `QThread` the caller already
created (rather than constructing one), so every test that patches a module's
`QThread` keeps intercepting. **When extracting a helper, ask which names it now
resolves and whether any test patches them** — then either move the patch or keep
the construction at the call site.

## 6. Packaging, building & releasing

We build a single-file AppImage with
[`python-appimage`](https://github.com/niess/python-appimage) (Critical Rule
#2 — do **not** reach for `appimage-builder` without asking). Build/CI test
procedure: **§6.1 below**; recipe details:
[`../build/python-appimage/README.md`](../build/python-appimage/README.md).

The recipe (`build/build_appimage.sh`, `build/python-appimage/`) encodes
several gotchas found the hard way:

- `python-appimage` installs `requirements.txt` **one line at a time from a
  temp dir**, so a `--find-links .` line fails → use the `PIP_FIND_LINKS` env
  var.
- Each `pip install` runs through a shell, so `<`/`>` version pins read as
  redirections → use `~=` pins.
- The entrypoint is globbed as `entrypoint.*`, so it **must** have an
  extension (`entrypoint.sh`).
- A space in the `.desktop` `Name=` breaks the unquoted `appimagetool` call →
  `Name=Platterpus`.
- The bundled manylinux CPython has **no CA certificates**, so HTTPS
  (MusicBrainz) fails until `entrypoint.sh` points `SSL_CERT_FILE` /
  `SSL_CERT_DIR` at the host bundle.
- FUSE-less hosts (CI) need `APPIMAGE_EXTRACT_AND_RUN=1`; rate-limited
  base-image downloads need an authenticated `GITHUB_TOKEN` or a pre-staged
  base image.

**Releasing is tag-driven and automated** — don't hand-build or hand-upload.
The operational steps (bump `__version__`, roll the CHANGELOG, dispatch the
workflow) are owned by `CLAUDE.md` *CI / release*; the contract that shapes
the design:

- **Single-source the version** from `src/platterpus/__init__.py:__version__`
  (`pyproject.toml` reads it dynamically) — never hard-code it twice.
- `release.yml` builds the AppImage + `.sha256` (+ `.zsync`) and attaches them
  to a GitHub Release; `v0.*` tags publish as pre-releases.
- The wheel/sdist publish to PyPI via `publish-pypi.yml` using **Trusted
  Publishing (OIDC)** — no API token in the repo. Keep publish in a *separate*
  workflow so a PyPI misconfiguration can't block the AppImage release.
- Follow [SemVer](https://semver.org/) and
  [Keep a Changelog](https://keepachangelog.com/) (newest first, an
  `Unreleased` section on top).
- **Keeping the record current is enforced, not optional.** The CHANGELOG
  bullet (same commit), the `session-log.md` entry (session end), and
  lesson-graduation are mandated by `CLAUDE.md` Critical Rule #7, with the
  checklist in [testing.md §6](testing.md) and a CI `changelog` job as the
  mechanical backstop. The design + rationale is **KDD-20** in
  [PLANNING.md](../PLANNING.md).

### 6.1 AppImage build & testing procedure

*(Absorbed the former `appimage-testing.md` on 2026-08-06 — it was the
procedure half of this section, one link away from the design half.)*

The AppImage is built by exactly one recipe — `build/build_appimage.sh` — used
locally, in CI, and at release time. This is the procedure for testing it in each
situation, including branches that don't have a published release yet.

**When the AppImage is built:**

| Trigger | Workflow | Result |
|---|---|---|
| Every push to `main` | `.github/workflows/appimage.yml` | Builds + smoke-tests (`--version`); uploads the AppImage as a **run artifact**. Catches a broken build recipe immediately. |
| Manual run on **any branch** | `appimage.yml` (`workflow_dispatch`) | Same — a downloadable AppImage artifact for a branch with no release. (Run artifacts expire — 90 days by default; re-run the workflow to regenerate one.) |
| Push a `vX.Y.Z` tag **or dispatch the Release workflow with the tag as input** (Actions → Release → *Run workflow* — it creates the tag itself; the only route that works from cloud sessions) | `.github/workflows/release.yml` | Builds, checksums, and **publishes** the AppImage + its `.sha256` + `.zsync` (self-update) + `install.sh`/`install-appimage.sh` to a GitHub Release (`v0.*` → pre-release), then dispatches the PyPI publish. |

**Testing `main`.** Every push to `main` runs the **AppImage** workflow. Confirm
it's green in the **Actions** tab. To test the actual binary, open the latest
`AppImage` run and download the `platterpus-x86_64.AppImage` artifact, then:

```bash
chmod +x platterpus-x86_64.AppImage
./platterpus-x86_64.AppImage --version       # quick smoke test
bash install-appimage.sh ./platterpus-x86_64.AppImage   # desktop-integrate it
```

**Testing a feature branch (no release yet).** A branch won't have a published
AppImage. Two ways to get one:

1. **CI artifact (recommended).** Actions tab → **AppImage** workflow → **Run
   workflow** → pick your branch. When it finishes, download the
   `platterpus-x86_64.AppImage` artifact from the run and test as above.
2. **Build locally** from the checkout:
   ```bash
   git checkout my-branch
   bash build/build_appimage.sh          # → platterpus-x86_64.AppImage
   bash install.sh --build               # build + host stack + integrate
   # or, if the host stack is already set up:
   bash install.sh --no-host --appimage ./platterpus-x86_64.AppImage
   ```

**Testing the release flow.**

1. Bump `__version__` in `src/platterpus/__init__.py` and add a `CHANGELOG.md`
   entry.
2. `git tag vX.Y.Z && git push origin vX.Y.Z` — or, from a cloud session
   (tag pushes are proxy-blocked), dispatch the **Release** workflow with the
   tag as input (it creates the tag itself).
3. Watch the **Release** workflow; confirm the GitHub Release has the AppImage,
   its `.sha256`, its **`.zsync`** (the self-update file — the build fails
   without it), and the installer scripts attached; then confirm the
   dispatched `publish-pypi.yml` run published the wheel/sdist.
4. Test the published artifact as an end user would:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/rmccann-hub/Platterpus/main/install.sh | bash
   ```

**Testing the installer / uninstaller without a real machine.** `install.sh`,
`install-appimage.sh`, and `uninstall.sh` are guarded by smoke tests
(`tests/test_install_script.py`, `tests/test_install_appimage_script.py`,
`tests/test_uninstall_script.py`; `setup-host.sh` has its own,
`tests/test_setup_host_script.py`) that check syntax, `--help`, and `--dry-run`
behaviour, and exercise an install→uninstall round-trip against a sandboxed
`HOME`. Run them with `pytest`. The full host-stack bootstrap (Distrobox +
cyanrip) still needs a real-hardware confirmation — CI only dry-run-tests it.

### 6.2 Release signing (offline-key minisign) — maintainer ritual

*(Absorbed the former `release-signing.md` on 2026-08-06. It is executed
under release-time pressure, so `CLAUDE.md` → *CI / release* points here directly
rather than relying on a reader finding this section — and **the arming
transition below is the part that is dangerous to half-read**: once a public key
is baked in, a release without a `.minisig` cannot be updated to.)*

Platterpus's in-app updater verifies every download's **SHA-256** (integrity).
This is the second gate — an **Ed25519 signature** that proves *who* published a
release (authenticity), made with a key the maintainer holds **offline**. It's the
maintainer-facing companion to
[`../src/platterpus/update_signing.py`](../src/platterpus/update_signing.py) (the
verify side) and [PLANNING.md KDD-26](../PLANNING.md).

**Threat it closes:** SHA-256 alone can't stop a compromised release channel that
swaps *both* the AppImage and its `.sha256`. A signature made with a secret key
that never touches CI (or any online system) can't be forged that way — not even
by a CI compromise. That's why the key is **offline** and signing happens
**outside** the CI release workflow; a key kept in a CI secret would only prove
"built by our CI," which the SLSA build-provenance attestation already does.

> **The app only ever *verifies*.** No secret key is in the repo, the build, or
> the app. The **public** key is safe to commit — that's the whole point.

**Status.** The verify side (parse `.minisig` → Ed25519-verify fail-closed) ships
**dormant**: `update_signing.PUBLIC_KEY_B64` is empty, so the updater is
SHA-256-only and nothing about updates changes. Arming it is the one-time setup
below.

**One-time setup (do this once, on a trusted machine — never in CI).**

1. **Install minisign** (`sudo dnf install minisign` / `sudo apt install
   minisign`, or from <https://jedisct1.github.io/minisign/>).
2. **Generate the keypair** and store the **secret** key somewhere offline and
   backed up (a password manager, an encrypted USB key — *not* the repo, *not* a
   CI secret):
   ```bash
   minisign -G -p minisign.pub -s minisign.key
   ```
   You'll set a password on the secret key; you'll enter it each time you sign.
3. **Bake in the public key.** Open `minisign.pub` — it has two lines:
   ```
   untrusted comment: minisign public key ABC123…
   RWQ…the base64…=
   ```
   Copy the **second line** (the base64) into
   `src/platterpus/update_signing.py`:
   ```python
   PUBLIC_KEY_B64: str = "RWQ…the base64…="
   ```
   Commit that change. It **arms** the fail-closed gate — read the transition
   immediately below *before* you cut the release.

**The transition (read before arming).** Once a public key is baked in, the
updater **refuses** any release without a valid `.minisig`. So:

- The **first** release built after you bake in the key **must** carry a
  `.minisig`, and **every** release after it must be signed. A release that
  forgets the signature can't be auto-updated *to* (users would see "this release
  has no verifiable signature — refusing to install").
- Users on an **older, pre-signing** release update to the first signed release
  normally (their running app has no key baked in yet, so it's still
  SHA-256-only). It's the *new* app they land on that enforces signatures going
  forward.

**Per-release signing (every release, after CI finishes).** The `release.yml`
workflow builds and uploads the AppImage, its `.sha256`, and the `.zsync`. It
**cannot** sign (the key is offline). After it finishes:

1. **Download** the released AppImage (the exact bytes CI published):
   ```bash
   curl -fLO https://github.com/rmccann-hub/Platterpus/releases/download/vX.Y.Z/platterpus-x86_64.AppImage
   ```
2. **Sign it** (prehashed — `-H` — is what the verifier expects for a file this
   large, and is faster):
   ```bash
   minisign -S -H -s minisign.key -m platterpus-x86_64.AppImage
   ```
   This writes `platterpus-x86_64.AppImage.minisig`.
3. **Verify your own signature** before uploading (catches a wrong key/typo):
   ```bash
   minisign -V -p minisign.pub -m platterpus-x86_64.AppImage
   ```
   It should print `Signature and comment signature verified`.
4. **Upload `platterpus-x86_64.AppImage.minisig`** to the GitHub Release as an
   asset, next to the AppImage. That's the file the updater fetches
   (`<AppImage>.minisig`) and checks.

> **Sanity check the whole chain** on a spare machine: run the *previous*
> released Platterpus, "Check for updates," and confirm it installs the new
> signed release. If you ever need to unpublish, delete the release assets; the
> updater fails closed rather than installing something unverifiable.

**If a release shipped unsigned by mistake.** The updater will refuse it
(fail-closed) once signing is armed — that's working as intended, not a bug. Fix
it by signing that release's AppImage and uploading the `.minisig` (steps 2–4
above); no rebuild needed, since you sign the exact published bytes.

## 7. Security & licensing hygiene

- **No `shell=True`; argument lists only** (§3.3) — the GUI passes
  user-entered metadata into subprocess argv and path templates.
- **Never write secrets to the log** or to committed files. The release
  pipeline uses OIDC Trusted Publishing so there's no token to leak.
- **Respect the Distrobox routing boundary** (Critical Rule #3): the GUI calls
  the host-exported `~/.local/bin/cyanrip`; it does not enter the container,
  except the one scoped, user-approved force-stop exception.
- **Licensing:** we are GPL-3.0-only. Before reusing third-party code, check
  compatibility — e.g. CTDB verify is built **clean-room** from the LGPL
  reference, *not* ported from the GPL-2.0-only `python-cuetoolsdb` (KDD-16).
  Protocols/algorithms are facts (not copyrightable expression); specific code
  is. When in doubt, reimplement from a spec and add an SPDX header.

## 8. Future improvements & directions

Concrete backlog lives in `TASKS.md`; this section is the *architectural*
horizon — the seams that exist so future contributors can take the program
places we haven't planned.

- **Backends as plugins.** The `RipBackend` ABC already makes backends
  swappable — it's how whipper was replaced by cyanrip (KDD-18). A small
  entry-point/registry could let third parties drop in a backend without
  editing `app.py` (a `Config`-level backend selector was removed when cyanrip
  became the sole backend; reintroduce one here if a second returns).
- **A real preferences framework.** `config.py` is a flat dataclass with
  manual schema migration; as options grow, a typed settings registry with
  per-key metadata (label, help, backend-applicability) would let the Settings
  dialog build itself instead of hand-wiring each widget.
- **CTDB repair** (KDD-14/16): the verify half is built and
  backend-independent; repair (wrapping the .NET `ctdb-cli`) is the headline
  EAC++ differentiator, parked on the bundle-vs-install question.
- **Library management:** ReplayGain, auto-move to a library tree, multi-disc
  queue, udev-driven auto-detect on disc insert — all sit above the rip
  pipeline and need no changes to the adapter layer.
- **Internationalization:** user-facing strings are currently inline; a future
  `tr()` pass would route them through Qt's translation system.
- **Packaging reach:** AppImage + pipx today; the adapter/host-wizard split
  keeps a Flatpak-with-host-access or other channel conceivable without
  touching the GUI (subject to Critical Rule #3).

When you add a capability the author never imagined: keep the layer direction
(§2), put external calls behind an adapter (§3.1), never block the GUI thread
(§3.2), and leave a test. That's the whole contract.

## References

External sources for the practices above:

- **Python & typing:** [PEP 8](https://peps.python.org/pep-0008/) ·
  [PEP 484 type hints](https://peps.python.org/pep-0484/) ·
  [PEP 257 docstrings](https://peps.python.org/pep-0257/)
- **Adapters:** [`abc`](https://docs.python.org/3/library/abc.html) ·
  dependency-inversion principle
- **Subprocess:** [`subprocess`](https://docs.python.org/3/library/subprocess.html) ·
  [Bandit B602 `shell=True`](https://bandit.readthedocs.io/en/latest/plugins/b602_subprocess_popen_with_shell_equals_true.html) ·
  [`shlex.quote`](https://docs.python.org/3/library/shlex.html#shlex.quote)
- **Parsing:** [`re`](https://docs.python.org/3/library/re.html)
- **Qt threading:**
  [QThread](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QThread.html) ·
  [Threads & QObjects](https://doc.qt.io/qt-6/threads-qobject.html) ·
  [Signals & Slots](https://doc.qt.io/qtforpython-6/tutorials/basictutorial/signals_and_slots.html) ·
  [Real Python — QThread](https://realpython.com/python-pyqt-qthread/)
- **Logging:** [Logging HOWTO](https://docs.python.org/3/howto/logging.html) ·
  [`logging`](https://docs.python.org/3/library/logging.html)
- **Testing:** [pytest](https://docs.pytest.org/)
- **Packaging & release:**
  [Python Packaging User Guide](https://packaging.python.org/) ·
  [`python-appimage`](https://github.com/niess/python-appimage) ·
  [PEP 621](https://peps.python.org/pep-0621/) ·
  [PyPI Trusted Publishers](https://docs.pypi.org/trusted-publishers/) ·
  [`pypa/gh-action-pypi-publish`](https://github.com/pypa/gh-action-pypi-publish) ·
  [SemVer](https://semver.org/) · [Keep a Changelog](https://keepachangelog.com/)
- **Security & licensing:**
  [OWASP — OS command injection](https://owasp.org/www-community/attacks/Command_Injection) ·
  [SPDX licenses](https://spdx.org/licenses/) ·
  [GNU license compatibility](https://www.gnu.org/licenses/gpl-faq.html)

---

*Last updated for Platterpus v0.6.19.*
