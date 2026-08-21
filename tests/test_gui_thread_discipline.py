"""Architectural fitness test: the GUI thread is never blocked.

Codifies CLAUDE.md's **"never block the GUI thread"** rule as an executable
guard so the freeze bug class can't creep back (the 2026-06-13 in-app-update
freeze, plus the latent `gio`/`kbuildsycoca`/launch-probe freezes). No module
under ``src/platterpus/ui/`` may make a *synchronous blocking* call —
``subprocess.run``/``check_output``/``check_call``/``call``, any ``urlopen``,
or ``time.sleep``. Blocking work belongs on a ``QObject`` worker on a
``QThread`` (need the result) or a fire-and-forget ``subprocess.Popen(...,
start_new_session=True)`` (don't).

Why AST, not grep: parsing means a docstring, comment, or string that merely
*mentions* ``subprocess.run`` doesn't trip the guard — only a real call does.

Deliberately NOT forbidden: ``QThread.wait()`` / ``thread.join()``. The UI
uses those only at *teardown* (``closeEvent`` / dialog ``reject``) to join a
worker before destroying it — required (destroying a running ``QThread``
aborts the app) and bounded. Blocking during normal operation is the bug;
joining on the way out is correct.

This is a "fitness function" test — a small, fast check that protects an
architectural property instead of a single behaviour. Portable pattern: any
GUI project can drop this in to keep its event loop responsive.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_UI_DIR = Path(__file__).resolve().parents[1] / "src" / "platterpus" / "ui"

# Module-qualified calls that block the calling thread until they return.
_FORBIDDEN_QUALIFIED: set[tuple[str, str]] = {
    ("subprocess", "run"),
    ("subprocess", "check_output"),
    ("subprocess", "check_call"),
    ("subprocess", "call"),
    ("os", "system"),
    ("os", "waitpid"),
    ("time", "sleep"),
}
# Whole modules that have no business being called on the GUI thread under any
# spelling — every call on them is synchronous network/blocking I/O.
_FORBIDDEN_RECEIVERS: set[str] = {"requests"}
# Calls by attribute name regardless of receiver — network I/O has no business
# on the GUI thread under any spelling (urllib.request.urlopen, request.urlopen).
_FORBIDDEN_ATTRS: set[str] = {"urlopen"}


def _ui_modules() -> list[Path]:
    return sorted(p for p in _UI_DIR.rglob("*.py") if "__pycache__" not in p.parts)


#: Floor for the parametrized sweep below. 33 modules today (measured
#: 2026-08-20); the bar sits below that so ordinary consolidation does not trip
#: it, and above the 20/15 floors the two sibling sweeps over this same directory
#: already use. Lowering it is a deliberate act with a re-measured number, never a
#: way to make a red run green.
_MIN_UI_MODULES: int = 25


def test_the_blocking_call_sweep_examines_the_real_ui_package() -> None:
    """Floor for the parametrized sweep — which structurally CANNOT floor itself.

    `@pytest.mark.parametrize("path", _ui_modules())` generates one case per
    module, so an **empty population generates no cases at all**. Measured under
    this repo's config (`addopts = "-q --strict-markers"`, no
    `empty_parameter_set_mark`): an empty parametrize reports `1 skipped` and
    exits **0**. A floor asserted *inside* the parametrized function would be
    skipped along with it, which is exactly why this test is separate and
    unparametrized.

    That matters more here than almost anywhere: the sweep guards *"never block
    the GUI thread"*, a rule `CLAUDE.md` says was **written in blood** and which
    has bitten three times. The two meta-tests below prove the *detector* works on
    a planted file in `tmp_path` — a different claim. A perfect detector applied
    to zero modules passes, and nothing said so.

    The realistic drift is not this directory vanishing; it is modules *leaving*
    it (a dialog moved to `src/platterpus/dialogs/`), shrinking the population
    with no count to notice. So the count is asserted — and so is the **subject**,
    because 25 unrelated files in the right directory would satisfy a count alone.
    """
    assert _UI_DIR.is_dir(), (
        f"the UI package is not at {_UI_DIR}, so the sweep matches nothing and "
        "every blocking-call case is silently skipped. Fix the path, do not "
        "delete the test."
    )
    modules = _ui_modules()
    assert len(modules) >= _MIN_UI_MODULES, (
        f"the sweep reached only {len(modules)} UI modules (floor "
        f"{_MIN_UI_MODULES}). Either the glob is broken or the package moved. If "
        "modules legitimately left `ui/`, re-measure and lower _MIN_UI_MODULES "
        "deliberately — do not treat this as spurious, because the same shrink is "
        "what a broken sweep looks like."
    )
    # The subject, not just the size: this rule exists because of the main window.
    assert any("main_window" in path.name for path in modules), (
        "no main_window* module is in the swept population, so whatever this "
        "sweep is now examining, it is not the surface the GUI-thread rule is "
        f"about. Population: {[p.name for p in modules[:12]]}"
    )


def _import_aliases(tree: ast.AST) -> tuple[dict[str, str], dict[str, tuple[str, str]]]:
    """Resolve a module's imports so aliased blockers can't slip the guard.

    Returns ``(module_alias, name_import)``:
      * ``module_alias`` maps a local name → canonical top-level module, covering
        ``import subprocess`` and ``import subprocess as sp`` (and ``import
        time as _time``). The canonical name is the FIRST dotted component, so
        ``import urllib.request`` maps ``urllib`` → ``urllib``.
      * ``name_import`` maps a bare local name → ``(module, attr)`` for
        ``from subprocess import run`` / ``from time import sleep as nap``, so a
        direct ``run(...)`` / ``nap(...)`` call resolves back to its origin.

    Without this the guard only caught the literal ``subprocess.run`` spelling —
    ``import subprocess as sp; sp.run(...)`` and ``from subprocess import run``
    both slipped through (the gap behind why blocking calls reached the GUI).
    """
    module_alias: dict[str, str] = {}
    name_import: dict[str, tuple[str, str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split(".")[0]
                module_alias[local] = alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom) and node.module:
            top = node.module.split(".")[0]
            for alias in node.names:
                name_import[alias.asname or alias.name] = (top, alias.name)
    return module_alias, name_import


def _blocking_calls(path: Path) -> list[str]:
    """Return 'line:call' for each blocking call found in `path` (AST-based).

    Resolves import aliases first, so a blocker is caught however it's spelled —
    ``subprocess.run``, ``sp.run`` (aliased import), or a bare ``run`` brought in
    via ``from subprocess import run``.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    module_alias, name_import = _import_aliases(tree)
    hits: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute):
            attr = func.attr
            raw = func.value.id if isinstance(func.value, ast.Name) else "?"
            module = module_alias.get(raw, raw)  # resolve `sp` → `subprocess`
            if (
                (module, attr) in _FORBIDDEN_QUALIFIED
                or module in _FORBIDDEN_RECEIVERS
                or attr in _FORBIDDEN_ATTRS
            ):
                hits.append(f"line {node.lineno}: {module}.{attr}(...)")
        elif isinstance(func, ast.Name):
            # A bare call like `run(...)` / `sleep(...)` — blocking only if it was
            # `from <module> import <that-name>` for a forbidden (module, attr).
            origin = name_import.get(func.id)
            if origin is not None and (
                origin in _FORBIDDEN_QUALIFIED or origin[1] in _FORBIDDEN_ATTRS
            ):
                hits.append(f"line {node.lineno}: {origin[0]}.{origin[1]}(...)")
    return hits


@pytest.mark.parametrize("path", _ui_modules(), ids=lambda p: p.name)
def test_ui_module_makes_no_blocking_calls(path: Path) -> None:
    hits = _blocking_calls(path)
    assert not hits, (
        f"{path.name} makes a blocking call on the GUI thread "
        f"({'; '.join(hits)}). Move it to a QObject worker on a QThread, or "
        "fire-and-forget subprocess.Popen(..., start_new_session=True). "
        "See CLAUDE.md 'never block the GUI thread' + docs/architecture.md §3.2."
    )


# --------------------------------------------------------------------------
# THE RECURRING TRAP, swept directory-independently.
#
# `CLAUDE.md` names it explicitly: *"The recurring trap is a modal dialog that
# does the blocking work itself in a button slot"* — `exec()` runs a nested event
# loop, but the slot still blocks the GUI thread. It has bitten **three** times
# (the in-app-update freeze and several latent freezes, 2026-06-13; the dependency
# install freeze shipped in 0.4.2, where a Picard Flatpak install ran on the GUI
# thread inside a modal dialog's `exec()`).
#
# There was no sweep for it. The sweep above is scoped to `src/platterpus/ui/`,
# which is 33 of 154 modules — and widening THAT is the wrong fix, measured: 12
# non-`ui/` modules make blocking calls and essentially all of them are correct,
# because `adapters/`, `deps/`, `ctdb/` and `drive_control.py` are worker-side code
# that is *supposed* to block. The rule is "never block the GUI THREAD", and a
# directory is only a proxy for that.
#
# So this keys on evidence inside the function instead: a function that BUILDS A
# MODAL DIALOG is GUI-thread code wherever it lives, and must not also make a
# blocking call. That covers `app.py` and everything else without inheriting the
# false positives.
#
# Zero violations today across 7 dialog-building functions. This keeps it there.
# --------------------------------------------------------------------------

#: Widget constructors that mean "this function drives a modal dialog".
_DIALOG_WIDGETS: set[str] = {
    "QMessageBox",
    "QDialog",
    "QProgressDialog",
    "QFileDialog",
    "QInputDialog",
}

#: Blocking primitives, by attribute name. Deliberately EXCLUDES `join`: the
#: overwhelmingly common `join` in this codebase is `str.join`, and a detector that
#: cannot tell `"".join(parts)` from `thread.join()` produces a false positive on
#: the most important site in the sweep — measured, it flagged
#: `_show_fatal_dialog` for `"".join(traceback.format_exception(...))`. A checker
#: that cries wolf on correct code gets switched off, so the ambiguous name is left
#: out rather than allowlisted.
_BLOCKING_IN_A_DIALOG: set[str] = {
    "run",
    "check_output",
    "check_call",
    "call",
    "sleep",
    "urlopen",
    "system",
}

#: Floor: 7 dialog-building functions today.
_MIN_DIALOG_FUNCTIONS: int = 5


def _dialog_building_functions() -> dict[str, ast.FunctionDef]:
    """Every function in the package that constructs a modal dialog widget."""
    src = Path(__file__).resolve().parents[1] / "src" / "platterpus"
    found: dict[str, ast.FunctionDef] = {}
    for path in sorted(src.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            builds = any(
                isinstance(call, ast.Call)
                and (
                    (
                        isinstance(call.func, ast.Name)
                        and call.func.id in _DIALOG_WIDGETS
                    )
                    or (
                        isinstance(call.func, ast.Attribute)
                        and call.func.attr in _DIALOG_WIDGETS
                    )
                )
                for call in ast.walk(node)
            )
            if builds:
                found[f"{path.relative_to(src)}::{node.name}"] = node
    return found


def test_the_dialog_sweep_has_dialogs_to_sweep() -> None:
    """Floor, and the subject: the crash dialog must be in the population."""
    functions = _dialog_building_functions()
    assert len(functions) >= _MIN_DIALOG_FUNCTIONS, (
        f"only {len(functions)} dialog-building function(s) found (floor "
        f"{_MIN_DIALOG_FUNCTIONS}) — the scan is broken, so 'no offenders' below "
        "means nothing"
    )
    assert any("_show_fatal_dialog" in key for key in functions), (
        f"the fatal-error dialog is not in the population: {sorted(functions)}"
    )


def test_no_modal_dialog_does_its_own_blocking_work() -> None:
    """The trap CLAUDE.md names, and the reason it is directory-independent."""
    offenders: list[str] = []
    for key, func in sorted(_dialog_building_functions().items()):
        hits = sorted(
            {
                f"{node.func.attr}()"
                for node in ast.walk(func)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in _BLOCKING_IN_A_DIALOG
            }
        )
        if hits:
            offenders.append(f"{key} -> {', '.join(hits)}")
    assert not offenders, (
        "these functions drive a modal dialog AND make a blocking call in the same "
        "scope. `exec()` runs a nested event loop, but the slot still blocks the "
        "GUI thread — the window shows 'Not Responding' and ignores every click. "
        "Move the work to a QObject worker on a QThread and report back via queued "
        "signals (docs/architecture.md, 'Dialogs that do blocking work'). This has "
        "shipped three times:\n  " + "\n  ".join(offenders)
    )


def test_the_dialog_blocking_detector_can_actually_fire() -> None:
    """Non-triviality, and the false positive it must NOT have.

    Two halves. A planted offender must be caught — otherwise the sweep above is
    decoration. And `"".join(...)` must NOT be caught: an earlier version of this
    detector included `join`, and flagged `_show_fatal_dialog` for
    `"".join(traceback.format_exception(...))`. A checker that fires on correct
    code is worse than none, because the fix is to delete the checker.
    """
    offender = ast.parse(
        "def slot():\n"
        "    box = QMessageBox()\n"
        "    subprocess.run(['flatpak', 'install'])\n"
        "    box.exec()\n"
    ).body[0]
    innocent = ast.parse(
        "def slot():\n"
        "    box = QMessageBox()\n"
        "    box.setDetailedText(''.join(traceback.format_exception(e)))\n"
        "    box.exec()\n"
    ).body[0]
    assert isinstance(offender, ast.FunctionDef)
    assert isinstance(innocent, ast.FunctionDef)

    def hits(fn: ast.FunctionDef) -> set[str]:
        return {
            node.func.attr
            for node in ast.walk(fn)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in _BLOCKING_IN_A_DIALOG
        }

    assert hits(offender) == {"run"}, "the planted blocking call was not detected"
    assert hits(innocent) == set(), (
        "a string join was read as a blocking call — the false positive that would "
        "flag the crash dialog and get this whole sweep switched off"
    )


def test_guard_actually_detects_a_blocking_call(tmp_path: Path) -> None:
    """Meta-test: prove the guard isn't a no-op — it must flag a planted call
    and must ignore a mere mention in a string/comment."""
    offender = tmp_path / "offender.py"
    offender.write_text(
        "import subprocess, time, urllib.request, os\n"
        "def bad():\n"
        "    subprocess.run(['x'])\n"
        "    time.sleep(1)\n"
        "    urllib.request.urlopen('http://x')\n"
        "    os.system('x')\n"
    )
    assert len(_blocking_calls(offender)) == 4

    innocent = tmp_path / "innocent.py"
    innocent.write_text(
        '"""We must not call subprocess.run here."""\n'
        "import subprocess\n"
        "def ok():\n"
        "    subprocess.Popen(['x'], start_new_session=True)  # fire-and-forget\n"
        "    ', '.join(['a', 'b'])  # str.join is not thread.join\n"
        "    thread.wait(2000)  # QThread teardown join is allowed\n"
    )
    assert _blocking_calls(innocent) == []


def test_guard_resolves_import_aliases(tmp_path: Path) -> None:
    """The blind spot that let blocking calls through before: a blocker reached
    through an aliased import (`import subprocess as sp`) or a bare name brought
    in via `from ... import` must be caught, not just the literal `module.attr`
    spelling."""
    aliased = tmp_path / "aliased.py"
    aliased.write_text(
        "import subprocess as sp\n"
        "import time as _t\n"
        "from subprocess import run\n"
        "from time import sleep as nap\n"
        "import requests\n"
        "def bad():\n"
        "    sp.run(['x'])\n"  # aliased module
        "    run(['x'])\n"  # from-import bare name
        "    nap(1)\n"  # from-import aliased name
        "    requests.get('http://x')\n"  # whole-module-forbidden receiver
        "    _t.monotonic()\n"  # NOT blocking — only time.sleep is
    )
    hits = _blocking_calls(aliased)
    # 4 blockers; _t.monotonic() must NOT be flagged.
    assert len(hits) == 4, hits
    assert not any("monotonic" in h for h in hits)
