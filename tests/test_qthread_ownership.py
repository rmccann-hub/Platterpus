"""Every class that creates a `QThread` must stop it on teardown. All of them.

**Why this exists as a sweep rather than a per-class test.** Destroying a
`QWidget` while a `QThread` it owns is still running is fatal — Qt calls
`qFatal()` → `SIGABRT`. The codebase knows this; `CLAUDE.md` rule 9 is most of a
page about it, and `test_harness_fidelity.py` enforces it thoroughly **for
`MainWindow`**. Nine classes create threads. One was checked.

The one that wasn't: `PendingInstallsDialog` had **no teardown path at all** — the
thread was parented to the dialog, the dialog to the main window, so a close
arriving from above ran `~QThread()` on a live thread. It survived review because
the dialog *does* refuse to close mid-install, which reads as "handled" until you
notice that guards user intent and not object lifetime. It was found by an audit
(2026-07-29), and an audit is a person remembering to look.

So this generalises the `MainWindow` rule to **every** `QThread` owner, present and
future. A new dialog that spawns a worker is covered the day it is written, without
anyone remembering to add a test for it.

Two details that matter, both learned the hard way in this repo:

* **It resolves through the MRO**, not per-file. `MainWindow` creates its threads in
  one module and stops some of them in a mixin in another, so a file-scoped check
  would report false failures. Importing the class and walking `type.__mro__` gets
  this right for free, and keeps working when the mixins are reorganised.
* **It checks the stop is *reachable* from a teardown hook**, not merely present
  somewhere in the class. A `stop_thread` call inside a helper nothing calls is
  dead code that looks like a fix — the same "mentioning is not stopping" trap that
  produced a vacuous detector twice in one session (`docs/testing.md` §5.t, §5.p).
"""

from __future__ import annotations

import ast
import importlib
import inspect
import textwrap
from pathlib import Path

REPO_ROOT: Path = Path(__file__).resolve().parents[1]
SRC_ROOT: Path = REPO_ROOT / "src" / "platterpus"

# Qt's own teardown entry points for a widget/dialog. A thread must be stopped from
# one of these, or from something one of them calls.
_TEARDOWN_HOOKS: frozenset[str] = frozenset(
    {"closeEvent", "reject", "accept", "done", "hideEvent"}
)

# `QThread()` assigned to a plain local inside a docstring example or a factory is
# not an ownership claim — only `self.<attr> = QThread(...)` is, because that is what
# ties the thread's lifetime to a Python object that can be destroyed.
_MIN_EXPECTED_OWNERS: int = 5


def _thread_attributes_created_in(source: str) -> set[str]:
    """Attribute names assigned a freshly-constructed `QThread` in `source`."""
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Assign):
            continue
        value = node.value
        if not isinstance(value, ast.Call):
            continue
        callee = value.func
        name = (
            callee.id if isinstance(callee, ast.Name) else getattr(callee, "attr", "")
        )
        if name != "QThread":
            continue
        for target in node.targets:
            if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
                if target.value.id == "self":
                    found.add(target.attr)
    return found


def _qthread_owners() -> dict[str, set[str]]:
    """Map ``module:ClassName`` → the thread attributes that class constructs.

    Walks the real source tree rather than a hand-maintained list, which is the
    whole point: a class added next month is covered without anyone updating a
    fixture.
    """
    owners: dict[str, set[str]] = {}
    for path in sorted(SRC_ROOT.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if "QThread(" not in text:
            continue
        tree = ast.parse(text)
        module = (
            path.relative_to(SRC_ROOT.parent)
            .with_suffix("")
            .as_posix()
            .replace("/", ".")
        )
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            attrs = _thread_attributes_created_in(ast.unparse(node))
            if attrs:
                owners[f"{module}:{node.name}"] = attrs
    return owners


def _class_bases() -> dict[str, list[str]]:
    """``ClassName`` → the base-class names it declares, read from source.

    Read via AST rather than by importing everything, so discovering the class graph
    has no import side effects and no ordering surprises.
    """
    bases: dict[str, list[str]] = {}
    for path in sorted(SRC_ROOT.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ClassDef):
                bases[node.name] = [
                    base.id if isinstance(base, ast.Name) else getattr(base, "attr", "")
                    for base in node.bases
                ]
    return bases


def _subclasses_of(name: str, bases: dict[str, list[str]]) -> set[str]:
    """Every class in `src/` that inherits `name`, transitively."""
    found: set[str] = set()
    frontier = {name}
    while frontier:
        current = frontier.pop()
        for child, parents in bases.items():
            if current in parents and child not in found:
                found.add(child)
                frontier.add(child)
    return found


def _method_sources(cls: type) -> dict[str, str]:
    """Every method the class resolves, across its MRO, dedented and parseable.

    MRO-wide because a mixin may declare the teardown that stops a thread the
    concrete class created — exactly how `MainWindow` and `RipMixin` are split.
    Nearest definition wins, matching Python's own attribute lookup.
    """
    sources: dict[str, str] = {}
    for klass in cls.__mro__:
        if klass.__module__.startswith(("PySide6", "builtins", "shiboken")):
            continue  # Qt's C++ classes have no Python source
        for name, member in vars(klass).items():
            if name in sources or not callable(member):
                continue
            try:
                sources[name] = textwrap.dedent(inspect.getsource(member))
            except (OSError, TypeError):
                continue  # C-level or dynamically created — nothing to read
    return sources


def _attrs_passed_to_stop_thread(source: str) -> set[str]:
    """`self.<attr>` names handed to `stop_thread(...)` — the call, not a mention."""
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        callee = node.func
        name = (
            callee.id if isinstance(callee, ast.Name) else getattr(callee, "attr", "")
        )
        if name != "stop_thread":
            continue
        for arg in node.args:
            if isinstance(arg, ast.Attribute):
                found.add(arg.attr)
    return found


def _functions_called_in(source: str) -> set[str]:
    """Names of everything invoked in `source`, for one-level reachability."""
    called: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call):
            callee = node.func
            name = (
                callee.id
                if isinstance(callee, ast.Name)
                else getattr(callee, "attr", "")
            )
            if name:
                called.add(name)
    return called


def _stopped_reachably(cls: type) -> set[str]:
    """Thread attributes stopped from a teardown hook, or from something one calls.

    One level of indirection is deliberate and sufficient for the real shapes here
    (`closeEvent` → `_stop_detection` → `stop_thread`). It is *not* "anywhere in the
    class": a `stop_thread` call in an orphaned helper must not count, or the check
    passes on dead code.
    """
    sources = _method_sources(cls)
    reachable_methods: set[str] = set()
    for hook in _TEARDOWN_HOOKS & sources.keys():
        reachable_methods.add(hook)
        reachable_methods |= _functions_called_in(sources[hook]) & sources.keys()

    stopped: set[str] = set()
    for method in reachable_methods:
        stopped |= _attrs_passed_to_stop_thread(sources[method])
    return stopped


def _import_class(qualified: str) -> type | None:
    module_name, class_name = qualified.split(":")
    return getattr(importlib.import_module(module_name), class_name, None)


def _responsible_classes(qualified: str, bases: dict[str, list[str]]) -> list[type]:
    """The class(es) that must stop the threads `qualified` creates.

    **A mixin is not a standalone owner.** `MainWindow` is deliberately split into
    mixins (`CLAUDE.md` → *Modules*), so `RipMixin` constructs `_rip_thread` while
    `MainWindow.closeEvent` stops it. Blaming the mixin would be a false positive,
    and — worse — "fixing" it by giving the mixin its own `closeEvent` would break
    the concrete class's teardown. So responsibility resolves *downward*: a class
    that declares a teardown hook answers for itself; one that doesn't is a mixin,
    and its concrete subclasses answer for it.
    """
    cls = _import_class(qualified)
    if cls is None:
        return []
    if _TEARDOWN_HOOKS & _method_sources(cls).keys():
        return [cls]
    _, class_name = qualified.split(":")
    concrete: list[type] = []
    for child_name in sorted(_subclasses_of(class_name, bases)):
        child = getattr(importlib.import_module(cls.__module__), child_name, None)
        if child is None:
            # Declared in a sibling module; find it via the real subclass graph.
            child = next(
                (c for c in _all_subclasses(cls) if c.__name__ == child_name), None
            )
        if child is not None and _TEARDOWN_HOOKS & _method_sources(child).keys():
            concrete.append(child)
    return concrete


def _all_subclasses(cls: type) -> set[type]:
    out: set[type] = set()
    for sub in cls.__subclasses__():
        out.add(sub)
        out |= _all_subclasses(sub)
    return out


def test_every_qthread_owner_stops_its_threads_on_teardown() -> None:
    """The sweep. A new thread-spawning dialog is covered the day it is written."""
    # Import the UI package so the real subclass graph is populated before we ask
    # which concrete class answers for a mixin.
    importlib.import_module("platterpus.ui.main_window")

    owners = _qthread_owners()
    bases = _class_bases()
    assert len(owners) >= _MIN_EXPECTED_OWNERS, (
        f"only found {len(owners)} QThread-owning classes ({sorted(owners)}), which "
        "is fewer than this codebase has. The detection walk has gone stale — a "
        "sweep that finds nothing passes for the wrong reason."
    )

    failures: list[str] = []
    for qualified, created in sorted(owners.items()):
        responsible = _responsible_classes(qualified, bases)
        if not responsible:
            failures.append(
                f"{qualified} creates {sorted(created)} and neither it nor any "
                "concrete subclass defines a teardown hook"
            )
            continue
        for cls in responsible:
            forgotten = sorted(created - _stopped_reachably(cls))
            if forgotten:
                hooks = sorted(_TEARDOWN_HOOKS & _method_sources(cls).keys())
                failures.append(
                    f"{qualified} creates {forgotten}, and {cls.__name__} (which "
                    f"answers for it) does not reachably stop_thread() them "
                    f"from {hooks}"
                )

    assert not failures, (
        "QThread(s) can be destroyed while still running — Qt treats that as fatal "
        "(qFatal → SIGABRT), so this aborts the whole app for a user who closes a "
        "window at the wrong moment:\n  " + "\n  ".join(failures) + "\n\n"
        "Fix: stop each one from closeEvent/reject (or a helper they call) via "
        "platterpus.workers.stop_thread, which waits briefly and otherwise ABANDONS "
        "the thread — retaining the reference and registering it so process exit "
        "takes the hard_exit path instead of aborting. See CLAUDE.md rule 9."
    )


def test_every_qthread_owner_is_answered_for_by_something_with_a_teardown_hook() -> (
    None
):
    """Stated separately because "no hook anywhere" and "hook that forgets one" differ.

    "No hook anywhere" is the `PendingInstallsDialog` shape: nothing to review,
    nothing to get visibly wrong, and the crash only arrives when something *else*
    destroys the object. The sweep above catches it too, but its message would talk
    about a forgotten attribute rather than the actual problem.
    """
    importlib.import_module("platterpus.ui.main_window")
    bases = _class_bases()

    unanswered = [
        qualified
        for qualified in sorted(_qthread_owners())
        if not _responsible_classes(qualified, bases)
    ]
    assert not unanswered, (
        f"these classes create a QThread and nothing answers for stopping it: "
        f"{unanswered}. Refusing to close while busy is not a substitute — that "
        "guards user intent, not object lifetime, and a parent being destroyed does "
        "not ask."
    )


# --- Cancellation: a flag-only cancel must be justified, not just shipped -------

# Names that actually interrupt a blocked call. A `cancel()` whose body reaches none
# of these cannot stop a thread sitting in `communicate()` or a socket read — it can
# only set a variable and hope somebody polls it.
_INTERRUPTING_CALLS: frozenset[str] = frozenset(
    {
        "terminate",
        "kill",
        "killpg",
        "send_signal",
        "cancel",  # e.g. RipHandle.cancel — SIGTERM then SIGKILL
        "cancel_setup",
        # Module-level entry points onto a `killable.KillableCommand`, which SIGKILLs
        # the running child's process group. Named individually rather than matched
        # by prefix so adding a new one is a deliberate act — a `cancel_*` wildcard
        # would silently bless a function that does nothing.
        "cancel_active_probe",
        "cancel_info_probe",
        "cancel_version_probes",
    }
)

# Workers whose `cancel()` deliberately only sets a flag, each with the reason it is
# acceptable. **This allowlist is the point of the test**: CLAUDE.md rule 9 forbids
# shipping a flag-only cancel, and the honest exception is a step loop that genuinely
# polls the flag often enough to matter. Adding an entry here is a deliberate act that
# forces the author to write down why — which is exactly what did NOT happen for
# `DriveSetupWorker`, whose flag-only cancel wore a killer's docstring for as long as
# it existed (audit, 2026-07-29).
_FLAG_ONLY_CANCELS: dict[str, str] = {
    "HostSetupWorker": (
        "Honoured BETWEEN steps, and that is the right call rather than a gap: a "
        "step is a package install, and killing a half-done `dnf install` leaves the "
        "host worse off than waiting does. Documented as boundary-only in the class "
        "docstring, so it makes no promise it doesn't keep. A step can run for "
        "1800 s, so shutdown may abandon this thread — safe, because exit bypasses "
        "interpreter teardown (platterpus.hard_exit)."
    ),
    "UpdateInstallWorker": (
        "The blocking work is a chunked HTTP download whose loop tests the flag at "
        "the top of every iteration (update_install.download_and_install, verified "
        "2026-07-29), so the flag IS the interrupt — there is no long uninterruptible "
        "call to signal, and the worker raises out within one chunk read."
    ),
}


def _worker_cancel_methods() -> dict[str, str]:
    """``ClassName`` → source of its `cancel` method, for every worker in `src/`."""
    found: dict[str, str] = {}
    for path in sorted((SRC_ROOT / "workers").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "cancel":
                    found[node.name] = ast.unparse(item)
    return found


def test_a_flag_only_cancel_is_either_justified_or_not_shipped() -> None:
    """CLAUDE.md rule 9, made executable rather than merely written down.

    "A `cancel()` that only sets a flag the blocked call never checks is a false
    promise" is a rule the codebase broke three separate ways in one audit, because a
    rule in a document is only as good as the next person's memory of it. This turns
    it into a build failure with a forced justification: interrupt the block, or add
    an allowlist entry saying why a flag suffices.
    """
    cancels = _worker_cancel_methods()
    assert len(cancels) >= 3, (
        f"found only {len(cancels)} worker cancel() methods ({sorted(cancels)}) — "
        "the walk has gone stale and this check is passing by finding nothing."
    )

    interrupting: list[str] = []
    unjustified: list[str] = []
    for class_name, source in sorted(cancels.items()):
        if _functions_called_in(source) & _INTERRUPTING_CALLS:
            interrupting.append(class_name)
        elif class_name not in _FLAG_ONLY_CANCELS:
            unjustified.append(class_name)

    # Floor: if NOTHING classified as interrupting, the classifier is broken and the
    # "unjustified" list would be meaningless (everything would look flag-only).
    assert interrupting, (
        "no worker cancel() was recognised as interrupting a blocked call, so the "
        f"call-name table is out of date. Known names: {sorted(_INTERRUPTING_CALLS)}"
    )

    assert not unjustified, (
        f"these workers' cancel() only set a flag: {unjustified}. A thread blocked in "
        "subprocess.communicate(), a socket read, or a long C call never sees it, so "
        "cancelling does nothing and shutdown abandons the thread. Either interrupt "
        "the block (kill the child process — see RipWorker.cancel / "
        "DriveSetupWorker.cancel), or add an entry to _FLAG_ONLY_CANCELS in this file "
        "stating why a flag is genuinely enough. Do not document one as working."
    )


def test_the_flag_only_allowlist_has_no_stale_entries() -> None:
    """An allowlist that outlives its reason quietly permits the next mistake.

    If a worker on the list is deleted or gains a real interrupt, its entry must go —
    otherwise the list slowly becomes a blanket exemption nobody re-reads.
    """
    cancels = _worker_cancel_methods()
    stale: list[str] = []
    for class_name in sorted(_FLAG_ONLY_CANCELS):
        if class_name not in cancels:
            stale.append(f"{class_name} (no longer defines cancel())")
        elif _functions_called_in(cancels[class_name]) & _INTERRUPTING_CALLS:
            stale.append(
                f"{class_name} (now interrupts the block — exemption unneeded)"
            )
    assert not stale, (
        f"stale _FLAG_ONLY_CANCELS entries: {stale}. Remove them so the list keeps "
        "meaning something."
    )


# Workers that expose no `cancel()` at all. CLAUDE.md rule 9 says every worker that
# blocks must have one. **Three** entries remain, and only two of them block: a
# `/dev` + `/sys` sweep that does not (see `DriveListWorker` below), and two network
# calls that a stalled connection can hold open for a long time. For the blocking two
# `stop_thread` has nothing to call: it quits the event loop they are not sitting in,
# waits out its share of the shutdown budget, and ABANDONS the thread.
#
# (This comment said "these five do block" until 2026-07-31, describing the list as
# it stood when written — before `DiscInfoWorker` and `DependencyCheckWorker` gained
# real cancels the same day and came off it. The count in
# `test_the_no_cancel_ratchet_only_shrinks` was updated then and this prose was not,
# so the file's own header contradicted both its assertion and `DriveListWorker`'s
# entry, which says plainly that it does not block. Re-derive a count; don't carry
# one forward.)
#
# That is *bounded and non-fatal* — abandonment retains the reference and registers
# the thread, so exit takes the `platterpus.hard_exit` path instead of aborting — but
# it is not the same as cancelling. Closing this properly means giving `run_capture`
# a killable child the way `cache_probe` now has (Popen + start_new_session, so a
# killpg reaches the podman/in-container tree) and threading a cancel through.
#
# **This list is a RATCHET: it may shrink, never grow.** Same discipline as the mypy
# per-module opt-outs in `pyproject.toml` (CLAUDE.md rule 10) — a known gap that is
# written down, counted, and closed one entry at a time, rather than a blanket
# exemption nobody re-reads.
_WORKERS_WITHOUT_CANCEL: frozenset[str] = frozenset(
    {
        # Pure filesystem: globs /dev/sr* and reads sysfs. No subprocess, no
        # socket, nothing that blocks measurably — so there is nothing a cancel
        # could interrupt, and adding one would be ceremony. This entry is
        # permanent-by-nature rather than debt.
        "DriveListWorker",
        # Network via urllib/musicbrainzngs. NOT fixable by the killable-subprocess
        # route the other two took — there is no child process, so interrupting it
        # means closing the socket out from under the request. Real debt, and a
        # different mechanism; see TASKS.md.
        "MusicBrainzWorker",
        "UpdateCheckWorker",
    }
)


def _qobject_worker_classes() -> dict[str, set[str]]:
    """``ClassName`` → its method names, for every QObject worker in `src/workers`."""
    workers: dict[str, set[str]] = {}
    for path in sorted((SRC_ROOT / "workers").rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ClassDef) and any(
                getattr(base, "id", getattr(base, "attr", "")) == "QObject"
                for base in node.bases
            ):
                workers[node.name] = {
                    item.name for item in node.body if isinstance(item, ast.FunctionDef)
                }
    return workers


def test_a_new_blocking_worker_cannot_ship_without_a_cancel() -> None:
    """The ratchet. New workers must be cancellable; the known five may only shrink.

    The point is asymmetry: this test is *satisfied* by today's code, so it does not
    block work, but it fails the moment someone adds a sixth un-cancellable worker.
    That is the difference between a documented gap and a spreading one.
    """
    workers = _qobject_worker_classes()
    assert len(workers) >= 6, (
        f"found only {len(workers)} QObject workers ({sorted(workers)}) — the walk "
        "has gone stale and this is passing by finding nothing."
    )

    without = {name for name, methods in workers.items() if "cancel" not in methods}
    new = sorted(without - _WORKERS_WITHOUT_CANCEL)
    assert not new, (
        f"these workers block but expose no cancel(): {new}. `stop_thread` then has "
        "nothing to call — `quit()` never reaches a thread blocked in a subprocess or "
        "socket read — so closing the window waits out the shutdown budget and "
        "abandons the thread. Give it a cancel() that kills the child process (see "
        "RipWorker.cancel, DriveSetupWorker.cancel, or cache_probe.cancel_active_probe "
        "for the killable-subprocess pattern). Do NOT add it to "
        "_WORKERS_WITHOUT_CANCEL — that list only shrinks."
    )


def test_the_no_cancel_ratchet_only_shrinks() -> None:
    """A ratchet that can be widened is a comment. This is the part with teeth."""
    workers = _qobject_worker_classes()
    assert len(_WORKERS_WITHOUT_CANCEL) <= 3, (
        f"_WORKERS_WITHOUT_CANCEL has grown to {len(_WORKERS_WITHOUT_CANCEL)}. It was "
        "5 when written (2026-07-29), came down to 3 the same day when "
        "DiscInfoWorker and DependencyCheckWorker gained real cancels, and may only "
        "get smaller — fix the worker instead of widening the exemption."
    )
    retired = sorted(
        name
        for name in _WORKERS_WITHOUT_CANCEL
        if name in workers and "cancel" in workers[name]
    )
    assert not retired, (
        f"{retired} now define cancel() — remove them from _WORKERS_WITHOUT_CANCEL and "
        "lower the bound above, so the ratchet keeps ratcheting."
    )
    gone = sorted(name for name in _WORKERS_WITHOUT_CANCEL if name not in workers)
    assert not gone, f"{gone} no longer exist — drop them from the list."


def test_every_worker_cancel_is_actually_invoked_at_a_stop_site() -> None:
    """A `cancel()` nothing calls is dead code that reads as a safety feature.

    **This test exists because the sweep above had the same blind spot as the bug it
    was written for.** It checks that a worker's `cancel()` exists and that it
    interrupts a blocked call — and says nothing about whether anything *calls* it.
    So `DiscInfoWorker.cancel` and `DependencyCheckWorker.cancel` were written,
    documented, covered by the flag-only guard... and invoked from nowhere, because
    the two `stop_thread(...)` call sites omitted the worker argument. Found by audit
    within the hour, which is luck, not process (2026-07-29).

    `stop_thread(thread, worker)` is the only route by which a worker's `cancel()`
    runs during teardown — `stop_thread` calls it via `getattr`, so passing only the
    thread silently skips it. This asserts that every worker class with a `cancel()`
    is passed to `stop_thread` somewhere in `src/`, by matching the *attribute name*
    of the second positional argument against the worker's own slot name.

    `docs/testing.md` §5.p, rule 1: grep for a call site before believing a method
    works — including one you wrote ten minutes ago.
    """
    importlib.import_module("platterpus.ui.main_window")

    cancels = _worker_cancel_methods()
    assert cancels, "no worker cancel() methods found — the walk has gone stale"

    # Worker attribute names handed to stop_thread as the SECOND positional arg.
    passed: set[str] = set()
    for path in sorted(SRC_ROOT.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Call):
                continue
            callee = node.func
            name = (
                callee.id
                if isinstance(callee, ast.Name)
                else getattr(callee, "attr", "")
            )
            if name != "stop_thread" or len(node.args) < 2:
                continue
            second = node.args[1]
            if isinstance(second, ast.Attribute):
                passed.add(second.attr)

    assert passed, (
        "no stop_thread(...) call in src/ passes a worker at all, so no worker's "
        "cancel() can ever run during teardown."
    )

    # Map each cancel-bearing worker class to the attribute name(s) it is stored in,
    # read from the declared slots rather than guessed from the class name.
    slot_types: dict[str, str] = {}
    for path in sorted(SRC_ROOT.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                annotation = ast.unparse(node.annotation)
                for worker_name in cancels:
                    if worker_name in annotation:
                        slot_types[node.target.id] = worker_name

    uninvoked = sorted(
        {
            worker
            for slot, worker in slot_types.items()
            # `RipWorker.cancel` is invoked directly from the Cancel button, not via
            # stop_thread, and has its own reachability test in test_rip_backend.py.
            if worker != "RipWorker" and slot not in passed
        }
    )
    assert not uninvoked, (
        f"these workers implement cancel() but are never passed to stop_thread: "
        f"{uninvoked}. `stop_thread(thread)` without the worker silently skips the "
        "cancel, so closing the window waits out the shutdown budget and abandons a "
        "thread still blocked in a container exec — and the cancel() is dead code "
        "that reads, in review, as though the hazard were handled."
    )


# --- "some blocking call is interruptible" is not "all of them are" ------------
#
# `test_a_flag_only_cancel_is_either_justified_or_not_shipped` asks whether a
# `cancel()` contains ANY name from `_INTERRUPTING_CALLS`. That is an existence check,
# and rule 9 needs a universal one: a worker must be able to interrupt *every* call it
# can be blocked in. `RipperUpdateWorker` shipped the gap (found by review, 2026-08-18):
# its `cancel()` closed the HTTPS socket — a real interrupter, so the sweep was
# satisfied — while `run()` had gained a `check_cyanrip` probe that runs `distrobox
# enter` at 60 s per version flag. Two minutes of block that closing a socket does
# nothing about, and `QThread.quit()` cannot reach either.

#: Blocking helpers a worker can call, mapped to the interrupter that ends them.
#:
#: Hand-maintained, like `_INTERRUPTING_CALLS` — but a *pair* rather than a bare name,
#: which is what makes it a universal check. Every entry is a measured ceiling, not a
#: guess, and the map may grow when a new blocking helper appears; what it must never
#: do is lose a row while its helper is still called.
#: Every one of these reaches ``VERSION_PROBE.run(timeout=_PROBE_TIMEOUT_S)``, which
#: `cancel_version_probes()` is the only thing that ends. Derived by reading
#: ``deps/checks.py`` rather than remembered — and the map's own guard below resolves
#: each name against the module, which is how the first draft's invented ``check_tool``
#: was caught on its first run.
_BLOCKER_INTERRUPTERS: dict[str, str] = {
    "check_cyanrip": "cancel_version_probes",
    "check_cdparanoia": "cancel_version_probes",
    "check_metaflac": "cancel_version_probes",
    "check_flac": "cancel_version_probes",
    "check_ffmpeg": "cancel_version_probes",
    # Added when the derivation below was written and immediately found it missing —
    # which is the point of deriving rather than listing. A worker calling this one
    # would have gone unchecked while the sweep reported clean.
    "check_picard_flatpak": "cancel_version_probes",
}


def test_every_blocking_helper_a_worker_calls_has_its_interrupter_in_cancel() -> None:
    """The universal form of rule 9: cancel must reach EVERY block, not one of them.

    Derived from the source rather than listed: for each worker class that owns a
    `cancel()`, every blocking helper it calls anywhere in the class must have its
    matching interrupter named in that `cancel()`.

    Pre-existing gaps in workers this batch did not touch are reported as a message
    rather than silently tolerated — but the assertion is scoped to what the source
    actually shows, so it cannot be satisfied by finding nothing (see the floor).
    """
    import ast
    from pathlib import Path

    src_root = Path(__file__).resolve().parents[1] / "src" / "platterpus"
    gaps: list[str] = []
    examined = 0
    pairs_seen = 0

    for path in sorted(src_root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            cancel = next(
                (
                    item
                    for item in node.body
                    if isinstance(item, ast.FunctionDef) and item.name == "cancel"
                ),
                None,
            )
            if cancel is None:
                continue
            examined += 1
            class_calls = _functions_called_in(ast.unparse(node))
            cancel_calls = _functions_called_in(ast.unparse(cancel))
            for blocker, interrupter in _BLOCKER_INTERRUPTERS.items():
                if blocker not in class_calls:
                    continue
                pairs_seen += 1
                if interrupter not in cancel_calls:
                    gaps.append(
                        f"{path.relative_to(src_root)}::{node.name} calls "
                        f"{blocker}() but its cancel() never calls {interrupter}() — "
                        f"that block cannot be interrupted (CLAUDE.md rule 9)"
                    )

    # Two floors, because either half can go vacuous on its own.
    assert examined >= 3, (
        f"only {examined} classes with a cancel() were found; the walk has gone stale "
        "and this check is passing by finding nothing"
    )
    assert pairs_seen >= 1, (
        "no worker was found calling any helper in _BLOCKER_INTERRUPTERS, so this "
        "check examined nothing. Either the map is stale or the helpers were renamed; "
        "a map that matches no code is decoration."
    )
    assert not gaps, "\n".join(gaps)


def test_the_blocker_map_names_helpers_that_actually_exist() -> None:
    """A stale row in the map is worse than a missing one: it looks like coverage.

    Both halves of every pair are resolved against the real module, so a rename that
    silently emptied the check fails here instead.
    """
    from platterpus.deps import checks

    for blocker, interrupter in _BLOCKER_INTERRUPTERS.items():
        assert hasattr(checks, blocker), (
            f"_BLOCKER_INTERRUPTERS names {blocker!r}, which no longer exists in "
            "platterpus.deps.checks — the row matches nothing and reads as coverage"
        )
        assert hasattr(checks, interrupter), (
            f"_BLOCKER_INTERRUPTERS names interrupter {interrupter!r}, which no longer "
            "exists in platterpus.deps.checks"
        )


def test_the_blocker_map_lists_every_probe_reaching_helper_in_checks() -> None:
    """The map is DERIVED-AGAINST, not merely spelled correctly.

    ``test_the_blocker_map_names_helpers_that_actually_exist`` catches a row that names
    something gone; it cannot catch a row that was never added. That is the more likely
    failure and the one that reads as coverage: a new ``check_*`` helper appears, reaches
    ``VERSION_PROBE.run``, and the sweep simply never asks about it.

    So the expected set comes out of ``deps/checks.py`` itself — every module-level
    function whose body reaches ``VERSION_PROBE`` — the same "derive it from the source,
    do not maintain a mirror by hand" rule the map's own subject matter is about.

    Functions that reach it only *indirectly* (through another listed helper) are not
    required: the sweep matches on what a worker actually calls, and the intermediate is
    already covered by its own row.
    """
    checks_src = (SRC_ROOT / "deps" / "checks.py").read_text(encoding="utf-8")
    tree = ast.parse(checks_src)

    def _touches_probe(node: ast.FunctionDef) -> bool:
        return any(
            isinstance(n, ast.Name) and n.id == "VERSION_PROBE" for n in ast.walk(node)
        )

    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    # The module's own private runner is what actually holds VERSION_PROBE; the public
    # `check_*` helpers go through it. So follow ONE level of indirection — a derivation
    # that only looked for direct references found NOTHING, and its floor said so rather
    # than passing quietly, which is why the floor is there.
    direct = {n.name for n in functions if _touches_probe(n)}
    reaching: set[str] = set()
    for node in functions:
        if node.name.startswith("_") or node.name == "cancel_version_probes":
            continue
        if node.name in direct or (_functions_called_in(ast.unparse(node)) & direct):
            reaching.add(node.name)

    # Floor: if the derivation finds nothing, the assertion below is vacuous.
    assert reaching, (
        "no function in deps/checks.py was found reaching VERSION_PROBE — the "
        "derivation has gone stale and this check would pass by finding nothing"
    )

    missing = sorted(reaching - set(_BLOCKER_INTERRUPTERS))
    assert not missing, (
        f"deps/checks.py has probe-reaching helpers absent from "
        f"_BLOCKER_INTERRUPTERS: {missing}. A worker calling one of those would not be "
        f"checked for having an interrupter, and the sweep would report clean. Add each "
        f"with its interrupter (cancel_version_probes for anything on VERSION_PROBE)."
    )
