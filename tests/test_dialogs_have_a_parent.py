"""Every prompt the app opens is attached to a window of ours (operator, 2026-10-19).

**Why this exists.** The operator asked that prompts, the album picker first among
them, never open as a window of their own or inside another dialog. A dialog with a
parent is a transient of that window: the desktop keeps it over the window, centres
it there (`ui/dialogs/centering.py`), and gives it no taskbar entry of its own. A
dialog built with no parent is a free-standing top-level that the desktop may place
anywhere. The sweep found two; one, the crash dialog, now takes the active window.

The scan reads every module's calls to a dialog class (Qt's own and every subclass
in this package) and refuses one built with no parent or with ``None`` as its
parent. The allowlist names each exception and why no window exists to attach to.
"""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "platterpus"

_QT_DIALOGS: frozenset[str] = frozenset(
    {"QDialog", "QMessageBox", "QFileDialog", "QInputDialog", "QProgressDialog"}
)

#: ``(module, class)`` pairs built with no parent on purpose, each with its reason.
_NO_WINDOW_TO_ATTACH_TO: dict[tuple[str, str], str] = {
    ("app.py", "UninstallDialog"): (
        "`--uninstall` runs without the main window by design, so the uninstall "
        "dialog is the app's only window"
    ),
}


def _dialog_classes(root: Path = SRC) -> set[str]:
    """Qt's dialog classes and every class of ours derived from one, by name."""
    names = set(_QT_DIALOGS)
    changed = True
    trees = [ast.parse(p.read_text(encoding="utf-8")) for p in root.rglob("*.py")]
    while changed:  # a subclass of a subclass counts too
        changed = False
        for tree in trees:
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name not in names:
                    bases = {
                        getattr(b, "id", None) or getattr(b, "attr", None)
                        for b in node.bases
                    }
                    if bases & names:
                        names.add(node.name)
                        changed = True
    return names


def _parentless_constructions(
    root: Path = SRC,
) -> tuple[list[tuple[str, int, str]], int]:
    """Each dialog built with no parent, and how many constructions were read."""
    dialogs = _dialog_classes(root)
    found: list[tuple[str, int, str]] = []
    examined = 0
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
                continue
            if node.func.id not in dialogs:
                continue
            examined += 1
            keywords = {k.arg: k.value for k in node.keywords}
            first = node.args[0] if node.args else keywords.get("parent")
            if first is None or (
                isinstance(first, ast.Constant) and first.value is None
            ):
                if (rel, node.func.id) not in _NO_WINDOW_TO_ATTACH_TO:
                    found.append((rel, node.lineno, node.func.id))
    return found, examined


def test_every_dialog_the_app_builds_has_a_parent_window() -> None:
    found, examined = _parentless_constructions()
    assert examined >= 25, f"only {examined} dialog construction(s) read"  # floor
    assert not found, (
        "these dialogs are built with no parent, so they open as windows of their "
        "own (operator, 2026-10-19): "
        + ", ".join(f"{rel}:{line} {name}()" for rel, line, name in found)
    )


def test_the_sweep_sees_a_parentless_dialog(tmp_path: Path) -> None:
    """Non-triviality: the real scan, on a module that builds one dialog of each
    kind, refuses exactly the parentless ones, a subclass's included."""
    (tmp_path / "mod.py").write_text(
        "class Picker(QDialog):\n    pass\n"
        "a = QMessageBox()\n"
        "b = QMessageBox(self)\n"
        "c = Picker(None)\n"
        "d = Picker(parent=self)\n",
        encoding="utf-8",
    )
    found, examined = _parentless_constructions(tmp_path)
    assert examined == 4
    assert [(line, name) for _, line, name in found] == [
        (3, "QMessageBox"),
        (5, "Picker"),
    ]
