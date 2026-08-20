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


# --- The runner is a stand-in too ----------------------------------------
#
# Everything above polices fixtures that do the product's job. This one
# polices the *invocation*: a local `python -m pytest` is a stand-in for
# CI's bare `pytest`, and it is the more permissive of the two. `python -m`
# prepends the cwd to `sys.path`, so at the repo root every non-package
# directory here — `scripts/`, `build/`, `uiscript/`'s parent — becomes an
# importable implicit namespace package. The `pytest` console script that
# CI runs prepends nothing.
#
# So `from scripts import round_digest` collects locally and raises
# `ModuleNotFoundError` on all four CI Pythons. That shipped: it was the
# only import of its kind in the suite, every other test reaching into
# `scripts/` loads by file location, and it turned the v0.6.12 release CI
# red at the collection stage (2026-08-17). Reproduce CI's import path
# locally with `PYTHONSAFEPATH=1 python -m pytest`.


def _repo_root_dirs_that_are_not_packages() -> set[str]:
    """Top-level directories importable ONLY because the cwd is on `sys.path`.

    A directory with no `__init__.py` is not a package; it resolves as an
    implicit namespace package, and only while its *parent* is on the path.
    Under CI's runner the repo root is not, so importing one of these by
    name is a collection error.
    """
    return {
        entry.name
        for entry in REPO_ROOT.iterdir()
        if entry.is_dir()
        and not entry.name.startswith(".")
        and not (entry / "__init__.py").exists()
    }


def test_no_test_imports_a_repo_root_directory_by_name() -> None:
    """No test may depend on the repo root being `sys.path[0]`.

    The failure mode is asymmetric and that is what makes it dangerous:
    the permissive runner is the one a human types, so the bug is
    invisible until CI — or a contributor with a different habit — runs it.
    """
    suspect = _repo_root_dirs_that_are_not_packages()
    assert "scripts" in suspect, (
        "`scripts/` is expected to be a non-package directory; if it gained "
        "an `__init__.py` this guard needs rethinking (it would still not be "
        "on `sys.path` under the bare `pytest` runner, so the rule stands)."
    )

    modules = sorted(REPO_ROOT.glob("tests/*.py"))
    assert len(modules) >= 40, (
        f"only {len(modules)} test modules found — the glob is wrong and this "
        "check has gone vacuous."
    )

    offenders: list[str] = []
    for path in modules:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                roots = [(node.module or "").split(".")[0]]
            else:
                continue
            for root in roots:
                if root in suspect:
                    offenders.append(f"{path.name}:{node.lineno} imports `{root}`")

    assert not offenders, (
        "these tests import a repo-root directory by name, which only resolves "
        "under `python -m pytest` and fails under the bare `pytest` CI runs:\n  "
        + "\n  ".join(offenders)
        + "\nLoad the module by file location instead (see `_load()` in "
        "tests/test_handshake_conformance.py for the idiom)."
    )


def test_the_by_file_location_idiom_is_actually_used() -> None:
    """The converse floor: prove tests DO reach into `scripts/` some other way.

    Without this, the check above passes trivially the day nobody needs
    `scripts/` at all — and would keep passing while the idiom it points
    people at quietly disappeared.
    """
    users = [
        path.name
        for path in sorted(REPO_ROOT.glob("tests/*.py"))
        if "spec_from_file_location" in path.read_text(encoding="utf-8")
    ]
    assert len(users) >= 5, (
        f"only {len(users)} test modules load a script by file location "
        f"({users}) — the established idiom has eroded; the guard above now "
        "polices a population that barely exists."
    )


def test_a_hang_dumps_its_stack_instead_of_eating_the_ci_step(pytestconfig) -> None:
    """A test that never returns must say WHERE it stopped.

    On 2026-08-19 all four CI legs stopped after 3312 tests and burned the whole
    15-minute step, and the log said one thing: *"the action has timed out"*. The
    diagnosis — which thread, which frame — was alive in the stuck process the
    entire time and was discarded, which is the same failure as capturing a
    dependency's stderr and never surfacing it: the facts were in hand and the
    report looked complete without them.

    Read off the EFFECTIVE pytest config rather than by grepping `pyproject.toml`,
    because what protects a run is the value pytest resolved, not the text of a
    file that a `-o` override or a stray `pytest.ini` could shadow.
    """
    timeout = float(pytestconfig.getini("faulthandler_timeout") or 0.0)
    assert timeout > 0.0, (
        "faulthandler_timeout is unset, so a hung test prints nothing and costs "
        "the entire CI step. Set it in [tool.pytest.ini_options]."
    )
    # A bound tight enough to fire on a healthy run is worse than none, because
    # `exit_on_timeout` makes a false positive kill the run. The suite measured
    # 275 s end to end, so the floor is stated against that, not against a guess.
    assert timeout >= 290.0, (
        f"faulthandler_timeout is {timeout:g}s, which is inside the range a "
        "healthy full run occupies (275 s measured 2026-08-20) — it would kill "
        "working runs. Re-measure before lowering it."
    )
    assert pytestconfig.getini("faulthandler_exit_on_timeout") is True, (
        "faulthandler_exit_on_timeout is off, so the stack dump is followed by "
        "the rest of the step timing out anyway and the trace is buried."
    )
