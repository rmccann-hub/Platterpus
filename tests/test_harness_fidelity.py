"""Fitness tests for the TEST HARNESS itself, not for the product.

Every bug in this file's history escaped for the same reason: **something that
stood in for the real thing behaved better than the real thing, so the suite was
green while the product was broken.** These tests police that gap.

The one that motivated the file: `closeEvent` never stopped the rip QThread, so
closing the window mid-rip aborted the process. No test could have caught it,
because `conftest.stop_window_threads` — which every window fixture calls —
stopped `_rip_thread` itself. The harness quietly did the product's job, so the
missing production code looked present. Found by an audit, 2026-07-29, five
releases after the gap opened.

That is a *class*, not an incident, and the whole class is invisible to ordinary
tests by construction: a test cannot notice that its own scaffolding is holding
the product up. So it needs checks written from the outside, which is what this
file is.

The rules these encode live in `docs/testing.md` §5.t. If you add a stand-in —
a fixture that tidies up, a stub that answers, a helper that drives — ask what it
does that production does not, and either delete the difference or pin it here.
"""

from __future__ import annotations

import ast
import inspect
import textwrap
from pathlib import Path

REPO_ROOT: Path = Path(__file__).resolve().parents[1]


def _names_passed_to(source: str, callee: str, suffix: str) -> set[str]:
    """Attribute names ending with `suffix` that are passed to `callee(...)`.

    **Deliberately not "names mentioned in the source".** The first version of
    this helper collected every `self.<x>_thread` it could see, and it passed
    against the very bug it was written to catch — because
    `_stop_rip_on_shutdown` *mentions* `self._rip_thread` in a guard clause
    (`if self._rip_thread is None`) without stopping it. Mentioning a thread is
    not stopping it, and a detector that conflates the two cannot fail. Caught
    only by reverting the fix and watching the test still pass.

    So this looks for the actual call: `stop_thread(self._rip_thread, ...)`.
    """
    found: set[str] = set()
    for node in ast.walk(ast.parse(textwrap.dedent(source))):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
        if name != callee:
            continue
        for arg in node.args:
            if isinstance(arg, ast.Attribute) and arg.attr.endswith(suffix):
                found.add(arg.attr)
    return found


def _string_literals_ending_with(source: str, suffix: str) -> set[str]:
    """String constants ending with `suffix` — conftest's loops iterate names."""
    found: set[str] = set()
    for node in ast.walk(ast.parse(textwrap.dedent(source))):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value.endswith(suffix) and node.value.startswith("_"):
                found.add(node.value)
    return found


def test_the_harness_does_not_stop_a_qthread_that_production_leaves_running() -> None:
    """The check that would have caught the mid-rip abort five releases earlier.

    `stop_window_threads` exists so no window fixture forgets a thread, and that
    is right. But it made the suite *safer than the product*: it stopped
    `_rip_thread`, which `closeEvent` did not, so the abort was unreachable from
    any test while being reliably reachable by a user.

    So the rule is: **the harness may not clean up a QThread that production
    leaves running.** Anything the harness stops, `closeEvent` must stop too. The
    harness is allowed to stop *fewer* things (it often constructs a partial
    window) — the asymmetry that matters is the harness covering for the product.
    """
    from platterpus.ui.main_window import MainWindow

    conftest_source = (REPO_ROOT / "tests" / "conftest.py").read_text(encoding="utf-8")
    tree = ast.parse(conftest_source)
    helper = next(
        (
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "stop_window_threads"
        ),
        None,
    )
    assert helper is not None, (
        "tests/conftest.py no longer defines stop_window_threads — this guard "
        "was written around it. Point it at whatever replaced it rather than "
        "deleting the check."
    )
    harness_stops = _string_literals_ending_with(ast.unparse(helper), "_thread")

    # closeEvent delegates part of the work, so include what it calls into.
    from platterpus.ui.main_window_rip import RipMixin

    # Dedent each separately: a method's source is indented, and concatenating
    # two indented blocks is not parseable.
    close_source = textwrap.dedent(
        inspect.getsource(MainWindow.closeEvent)
    ) + textwrap.dedent(inspect.getsource(RipMixin._stop_rip_on_shutdown))
    production_stops = _names_passed_to(close_source, "stop_thread", "_thread")

    # Daemon `threading.Thread`s are a deliberate, documented exception: they die
    # with the process and production must NOT join them (that would freeze close
    # on a long post-rip step). The harness joins them because a daemon still
    # running during a later test's garbage collection is what segfaulted CI.
    # That asymmetry is intended and reasoned; only QThreads are policed here.
    qthread_slots = {
        "_mb_thread",
        "_dep_check_thread",
        "_disc_info_thread",
        "_drive_list_thread",
        "_update_thread",
        "_install_thread",
        "_rip_thread",
    }

    covered_only_by_harness = sorted((harness_stops & qthread_slots) - production_stops)
    assert not covered_only_by_harness, (
        "the test harness stops QThread(s) that closeEvent does not: "
        f"{covered_only_by_harness}. That makes the suite safer than the product "
        "— destroying a window while one of these runs aborts the process for a "
        "real user, and no test can see it because the fixture cleans up first. "
        "Either stop them in closeEvent, or (if a slot is genuinely dialog-local) "
        "remove it from stop_window_threads."
    )


def test_every_qthread_slot_is_stopped_on_close() -> None:
    """The product-side half: no declared QThread slot may be forgotten.

    Stated against the declared surface rather than against the harness, so this
    still holds if `conftest` is rewritten. `main_window_shared` declares the
    slots; `closeEvent` (plus what it delegates to) must account for every one.
    """
    from platterpus.ui.main_window import MainWindow
    from platterpus.ui.main_window_rip import RipMixin

    shared = (
        REPO_ROOT / "src" / "platterpus" / "ui" / "main_window_shared.py"
    ).read_text(encoding="utf-8")
    # Annotated declarations of the form `_x_thread: QThread | None`.
    declared: set[str] = set()
    for node in ast.walk(ast.parse(shared)):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name = node.target.id
            if name.endswith("_thread") and "QThread" in ast.unparse(node.annotation):
                declared.add(name)
    assert declared, (
        "no QThread slots found in main_window_shared — the declaration style "
        "changed and this guard has gone vacuous. Fix the walk."
    )

    close_source = textwrap.dedent(
        inspect.getsource(MainWindow.closeEvent)
    ) + textwrap.dedent(inspect.getsource(RipMixin._stop_rip_on_shutdown))
    stopped = _names_passed_to(close_source, "stop_thread", "_thread")
    forgotten = sorted(declared - stopped)
    assert not forgotten, (
        f"closeEvent does not account for these QThread slots: {forgotten}. "
        "Destroying the window while one of them runs aborts the process."
    )
