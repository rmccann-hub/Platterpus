"""The window's close finishes, and imports nothing on the way out (TASKS R118).

**The incident.** 0.7.115, 2026-10-28 23:20:26 (the row says 0.7.114; the log's
banner says 0.7.115, build de2420d): a SIGTERM reached the app, `_drain` called
`window.close()`, and `closeEvent` raised
``ImportError: cannot import name 'report_writer' from 'platterpus'`` from
`_flush_rip_report`. Above that frame the traceback held 65+ frames of
`ui/dialogs/auto_center.py` `eventFilter`, which read as a recursion.

**What it was, measured, not explained.**

* *Not a recursion.* Line 201 of the filter is ``event.type() == …``; it calls
  nothing that can re-enter. When a Python override of a Qt virtual raises,
  PySide keeps the exception pending while Qt finishes the close, and every
  Python event filter Qt calls meanwhile fails on its first call into Qt with
  that exception, adding one frame each. Reproduced with PySide6 6.11.2: a
  raising ``closeEvent`` under the filter gave 17 such frames and a maximum
  nesting depth of ONE. The second test below pins both halves.
* *Not a circular import, and not interpreter shutdown.* `report_writer` imports
  nothing from `platterpus`, and the close ran inside ``app.exec()``. It was the
  module's FIRST import of the session (no rip had run, so nothing had loaded
  it), attempted after the signal, and the file was not found. A session logout
  sends SIGTERM to every process of the session, the AppImage runtime that serves
  the package's mount among them; with the mount gone, any module not already in
  ``sys.modules`` cannot be found, and ``from platterpus import report_writer``
  turns that into exactly this message. The first test reproduces the message
  word for word by refusing every new import during a close. (That the runtime
  died first is the one link no log shows; only a hardware logout can confirm it.)
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from conftest import stop_window_threads
from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QApplication

from platterpus import report_writer
from platterpus.adapters.metaflac import MetaflacAdapter
from platterpus.adapters.rip_backend import RipBackend
from platterpus.config import Config
from platterpus.deps.manager import DependencyManager
from platterpus.ui.dialogs.auto_center import DialogCenterFilter

_SRC: Path = Path(__file__).resolve().parent.parent / "src"

# A fresh interpreter, because the question is about what the close path imports
# that START-UP did not, and a test process has whatever every earlier test loaded.
# The child builds the window the way `app.main` does (the fakes are the ones
# `test_audit_regressions.py` uses), then installs a finder that refuses every
# module not already loaded, standard library included: the AppImage carries its
# own Python, so with the mount gone a lazy `import datetime` fails as surely as a
# lazy `from platterpus import report_writer`.
_CHILD: str = r"""
import importlib.abc, json, os, sys
from types import SimpleNamespace
sys.path.insert(0, sys.argv[1])
from PySide6.QtWidgets import QApplication
app = QApplication([])
from platterpus.adapters.metaflac import MetaflacAdapter
from platterpus.adapters.rip_backend import RipBackend
from platterpus.config import Config
from platterpus.deps.manager import DependencyManager
from platterpus.ui.main_window import MainWindow

class _Backend(RipBackend):
    name = "fake"
    def list_drives(self, timeout_s=None): return []
    def disc_info(self, drive, timeout_s=None): raise NotImplementedError
    def rip(self, *a, **k): raise NotImplementedError
    def version(self): return "fake 0"

window = MainWindow(
    config=Config(), backend=_Backend(), mb_client=SimpleNamespace(),
    metaflac=MetaflacAdapter(), dependency_manager=DependencyManager(specs=[]),
    save_config=lambda _cfg: None,
)
# No first-run offers: they are modals, and nobody answers them here.
window._unattended = True
window.show()
for _ in range(5):
    app.processEvents()

import logging
errors = []
class _Keep(logging.Handler):
    def emit(self, record):
        errors.append(record.getMessage())
_keep = _Keep(level=logging.ERROR)
logging.getLogger().addHandler(_keep)

refused = []
class _MountGone(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path, target=None):
        if name not in sys.modules:
            refused.append(name)
            raise ModuleNotFoundError(f"No module named {name!r}", name=name)
        return None

sys.meta_path.insert(0, _MountGone())
try:
    window.close()
    outcome = "closed"
except Exception as exc:
    outcome = f"raised {type(exc).__name__}: {exc}"
closing_refused = list(refused)
logging.getLogger().removeHandler(_keep)
# The floor: the finder really refuses. A module certainly not loaded by now.
probe = "tabnanny"
probe_was_loaded = probe in sys.modules
try:
    __import__(probe)
    probe_refused = False
except ModuleNotFoundError:
    probe_refused = True
sys.meta_path.pop(0)
print(json.dumps({
    "refused": closing_refused, "outcome": outcome, "errors": errors,
    "visible": window.isVisible(), "probe_was_loaded": probe_was_loaded,
    "probe_refused": probe_refused,
}))
sys.stdout.flush()
os._exit(0)
"""


def test_a_close_after_the_mount_is_gone_imports_nothing(tmp_path: Path) -> None:
    """Close a freshly started window while no new module can be found.

    Before the fix this printed the field's own sentence, ``ImportError: cannot
    import name 'report_writer' from 'platterpus'``, and ``refused`` was
    ``['platterpus.report_writer']``. Now the module is bound when
    `main_window_rip` loads, so the close needs no file.
    """
    env = dict(os.environ)
    # The child's config and log land in the test's own folder, never the user's.
    env["HOME"] = str(tmp_path)
    env["XDG_CONFIG_HOME"] = str(tmp_path / "config")
    env["XDG_DATA_HOME"] = str(tmp_path / "data")
    env["QT_QPA_PLATFORM"] = "offscreen"
    completed = subprocess.run(
        [sys.executable, "-c", _CHILD, str(_SRC)],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
        cwd=tmp_path,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr[-4000:]
    last = completed.stdout.strip().splitlines()[-1]
    result = json.loads(last)
    # The floor first: a finder that refuses nothing would pass the rest.
    assert result["probe_was_loaded"] is False, "fixture: the probe module was loaded"
    assert result["probe_refused"] is True, "fixture: the finder refused nothing"
    assert result["outcome"] == "closed", result["outcome"]
    assert result["visible"] is False, "the window did not close"
    # And nothing on the way out failed quietly: since the close now logs a
    # flush failure instead of raising it, "it closed" alone could hide one.
    assert result["errors"] == [], result["errors"]
    assert result["refused"] == [], (
        "the close path imported a module start-up had not loaded; after a "
        f"logout takes the AppImage's mount, that import fails: {result['refused']}"
    )


class _Backend(RipBackend):
    name = "fake"

    def list_drives(self, timeout_s: float | None = None) -> list[object]:  # type: ignore[override]  # a fake: the window reads none of it
        return []

    def disc_info(self, drive: str, timeout_s: float | None = None) -> object:  # type: ignore[override]  # never called
        raise NotImplementedError

    def rip(self, *args: object, **kwargs: object) -> object:  # type: ignore[override]  # never called
        raise NotImplementedError

    def version(self) -> str:
        return "fake 0"


def test_a_flush_that_raises_is_logged_and_the_close_finishes(
    qapp: QApplication,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The flush is the close's last step, and its failure must not leave it.

    Raised out of `closeEvent`, the exception went back through `window.close()`
    into the signal handler's `_drain`, and on the way every Python event filter
    Qt called failed with it (the 65+ `auto_center.py` frames). Now it is logged
    with its traceback, Qt's own close runs, and no filter sees it.
    """
    from platterpus.ui.main_window import MainWindow

    def _gone() -> report_writer.ReportWriter:
        raise ImportError("cannot import name 'report_writer' from 'platterpus'")

    monkeypatch.setattr(report_writer, "writer", _gone)

    # Count the app-wide filter's calls and their nesting, and keep any exception
    # one of them raised. The class attribute is what PySide dispatches to.
    seen: dict[str, int] = {"calls": 0, "depth": 0, "max_depth": 0}
    raised: list[str] = []
    original = DialogCenterFilter.eventFilter

    def _counting(self: DialogCenterFilter, obj: QObject, event: QEvent) -> bool:
        seen["calls"] += 1
        seen["depth"] += 1
        seen["max_depth"] = max(seen["max_depth"], seen["depth"])
        try:
            return original(self, obj, event)
        except BaseException as exc:
            raised.append(f"{type(exc).__name__}: {exc}")
            raise
        finally:
            seen["depth"] -= 1

    monkeypatch.setattr(DialogCenterFilter, "eventFilter", _counting)
    centre_filter = DialogCenterFilter()
    qapp.installEventFilter(centre_filter)
    window = MainWindow(
        config=Config(),
        backend=_Backend(),
        mb_client=SimpleNamespace(),  # type: ignore[arg-type]  # never reached
        metaflac=MetaflacAdapter(),
        dependency_manager=DependencyManager(specs=[]),
        save_config=lambda _cfg: None,
    )
    try:
        window.show()
        seen.update(calls=0, max_depth=0)
        with caplog.at_level(logging.ERROR, logger="platterpus.ui.main_window"):
            window.close()  # raised ImportError here before the fix

        assert not window.isVisible(), "Qt's own close did not run"
        assert any(
            "the rip report could not be flushed" in r.getMessage()
            and r.exc_info is not None
            for r in caplog.records
        ), "the failure was not logged with its traceback"
        # The filter was exercised during the close (the floor), never raised,
        # and was never entered twice at once: the incident's frames were one
        # pending exception charged to each later call, not a recursion.
        assert seen["calls"] > 0, "fixture: no event reached the filter"
        assert raised == [], raised
        assert seen["max_depth"] == 1, seen
    finally:
        qapp.removeEventFilter(centre_filter)
        stop_window_threads(window)
        window.deleteLater()
