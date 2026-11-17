"""Run Platterpus's real main() headless, grab every top-level window as it appears.

Every external command is refused (a fresh machine with nothing installed), so
nothing on the host is touched. Env: HOME and XDG dirs point into scratch.
Usage: python drive.py OUTDIR SECONDS [ACTIONS]
ACTIONS is a comma list consumed one per "dialog seen": reject|accept|keep
"""
import os
import subprocess
import sys
import time
from pathlib import Path

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
SECONDS = float(sys.argv[2])
ACTIONS = sys.argv[3].split(",") if len(sys.argv) > 3 and sys.argv[3] else []
LOG = open(OUT / "drive.log", "w")


def note(*a):
    print(*a, file=LOG, flush=True)


_real_popen = subprocess.Popen


class RefusingPopen(_real_popen):
    def __init__(self, args, *a, **k):
        note("REFUSED subprocess:", args if isinstance(args, str) else list(args)[:6])
        raise FileNotFoundError(2, "refused by review harness", str(args))


subprocess.Popen = RefusingPopen
import shutil  # noqa: E402

_real_which = shutil.which
shutil.which = lambda cmd, *a, **k: None

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox  # noqa: E402

seen: dict[str, int] = {}

counter = [0]
start = time.monotonic()


def shoot():
    app = QApplication.instance()
    if app is None:
        return
    for w in app.topLevelWidgets():
        if not w.isVisible() or w.width() < 50:
            continue
        title = w.windowTitle() or w.__class__.__name__
        key = f"{w.__class__.__name__}|{title}"
        pm = w.grab()
        img = pm.toImage()
        h = hash(bytes(img.constBits()))
        if seen.get(key) == h:
            continue
        seen[key] = h
        counter[0] += 1
        safe = "".join(c if c.isalnum() else "_" for c in title)[:50]
        p = OUT / f"{counter[0]:02d}-{w.__class__.__name__}-{safe}.png"
        pm.save(str(p))
        texts = []
        if isinstance(w, QMessageBox):
            texts.append("TEXT: " + w.text())
            texts.append("INFO: " + w.informativeText())
            texts.append("BUTTONS: " + " | ".join(b.text() for b in w.buttons()))
        note(f"SHOT {p.name} t={time.monotonic()-start:.1f}s {key}", *texts)


def act():
    app = QApplication.instance()
    if app is None:
        return
    modal = app.activeModalWidget()
    if not globals().get("_listed"):
        from PySide6.QtGui import QAction
        from PySide6.QtWidgets import QMainWindow
        for w in app.topLevelWidgets():
            if isinstance(w, QMainWindow):
                globals()["_listed"] = True
                for m in w.menuBar().actions():
                    note("MENU", m.text())
                    if m.menu():
                        for a in m.menu().actions():
                            note("   ", repr(a.text()), a.shortcut().toString(), "enabled" if a.isEnabled() else "DISABLED")
                            if a.menu():
                                for b in a.menu().actions():
                                    note("      ", repr(b.text()), b.shortcut().toString())
    if ACTIONS and ACTIONS[0].startswith("menu:") and (modal is None or ACTIONS[0].startswith("menu:!")):
        want = ACTIONS.pop(0).split(":", 1)[1].lstrip("!")
        from PySide6.QtGui import QAction
        for w in app.topLevelWidgets():
            for a in w.findChildren(QAction):
                if a.text().replace("&", "") == want:
                    note("TRIGGER", want)
                    QTimer.singleShot(0, a.trigger)
                    return
        note("NO ACTION", want)
        return
    if ACTIONS and ACTIONS[0] == "closeall":
        ACTIONS.pop(0)
        from PySide6.QtWidgets import QMainWindow
        for w in app.topLevelWidgets():
            if w.isVisible() and not isinstance(w, QMainWindow):
                note("CLOSE", w.windowTitle())
                w.reject() if isinstance(w, QDialog) else w.close()
        return
    if ACTIONS and ACTIONS[0] == "wait":
        ACTIONS.pop(0)
        return
    if modal is not None and ACTIONS:
        a = ACTIONS.pop(0)
        note("ACTION", a, "on", modal.windowTitle())
        if a == "reject":
            modal.reject() if isinstance(modal, QDialog) else modal.close()
        elif a == "accept":
            modal.accept() if isinstance(modal, QDialog) else None
        elif a.startswith("button:"):
            want = a.split(":", 1)[1]
            from PySide6.QtWidgets import QAbstractButton
            for b in modal.findChildren(QAbstractButton):
                if b.text().replace("&", "") == want:
                    b.click()
                    break


def arm():
    t = QTimer()
    t.timeout.connect(shoot)
    t.start(700)
    t2 = QTimer()
    t2.timeout.connect(act)
    t2.start(3000)
    t3 = QTimer()
    t3.setSingleShot(True)
    t3.timeout.connect(lambda: (note("QUIT"), os._exit(0)))
    t3.start(int(SECONDS * 1000))
    globals()["_timers"] = (t, t2, t3)


_orig_init = QApplication.__init__


def _init(self, *a, **k):
    _orig_init(self, *a, **k)
    QTimer.singleShot(0, arm)


QApplication.__init__ = _init

from platterpus import app as appmod  # noqa: E402

sys.exit(appmod.main(sys.argv[4:] if len(sys.argv) > 4 else []))
