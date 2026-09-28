"""Every `QMessageBox` in the product must pin its text format to PlainText.

**Why a sweep, and why this one did not exist.** Critical rule #12 says, verbatim:
*"Every widget carrying dependency output is `PlainText`, swept rather than fixed
one at a time."* The sweep was never written. Three of the six message boxes in
`src/` had been fixed individually and the other three had not — which is exactly
the outcome the rule's own wording was trying to prevent, and it stood until an
audit went looking for the sweep the rule claimed (2026-08-20).

The three that were missing it are the argument for the rule:

* `app.py::_show_fatal_dialog` — `setText(f"…{type(exc).__name__}: {exc}")`. The
  exception text is arbitrary external content: a MusicBrainz title, a cyanrip
  line, a path. Under Qt's default `AutoText` a `<` in it is parsed as markup and
  the run after it is dropped **silently**. Worst possible home for that: the
  dialog whose entire job is giving the user something accurate to report.
* `main_window_rip.py::_confirm_known_overwrite` — names a folder built from the
  album's artist, title and year. Rule #12 names this case directly. A truncated
  destructive-overwrite prompt while the Replace button still does the full thing.
* `main_window_drive.py::_present_drive_diagnosis` — device paths, group names and
  a `fix_command` the user is meant to copy verbatim.

**The half this sweep missed for five weeks: Qt's static helpers (2026-09-28).**
The sweep below finds functions that CONSTRUCT a `QMessageBox(...)`. It never saw
`QMessageBox.warning(...)`, `.information(...)`, `.critical(...)` or
`.question(...)`, which build the box inside Qt with the default `AutoText` and
give the caller no way to pin anything. There were **38** such calls in `src/`
while this file's name claimed "every QMessageBox", and several carried
dependency output: the dependency summary (`main_window_deps.py`) shows each
tool's version and build tag, install errors built from a tool's own stderr, and
why a check stopped. Under AutoText a first line holding a tag Qt knows turns the
whole message into HTML, and then every line break collapses, an unknown tag like
`<stdin>` vanishes and `&amp;` becomes `&` — measured, and silent. That is the
"scoping it silently while the rule claims everything" defect named below, in the
file written to fix it.

The fix is one module, `ui/message_boxes.py`, whose four functions take the
static helpers' arguments, return the same answer, and pin PlainText in one
place (`build`). This file now holds three things:

* every function that constructs a `QMessageBox` pins PlainText (the original
  sweep; `build` is one of its ten members and is required to be);
* **no static helper is used anywhere in the package** except named in that
  module's own docstring, calls and bare references alike, under any import
  alias; and the module is imported as a module, never function by function,
  because a by-name import would escape the non-blocking stand-ins in
  `tests/conftest.py` and hang the suite on the first box;
* the box `build` returns reads PlainText back for every kind, and each of the
  four functions shows exactly that box.

**What this sweep does NOT cover, said out loud rather than implied.** It checks
`QMessageBox`, both routes to one, and nothing else. Labels built from a value
are swept by `tests/test_labels_state_their_text_format.py`, which requires each to
state its format; labels given a value later by `setText` are tracked in `TASKS.md`.
Nor does it follow a box after it is built: a later `setTextFormat(RichText)` on
the same object, or a `QMessageBox` class reached through a name this file cannot
resolve statically (a variable holding the class), is outside what an AST sweep
can see. Scoping a sweep is fine; scoping it *silently while the rule claims
everything* is the defect this file was written to fix, so `CLAUDE.md` was
corrected in the same commit to say what is actually swept.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Final

import pytest
from PySide6 import QtGui
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox

from platterpus.ui import message_boxes

SRC: Final[Path] = Path(__file__).resolve().parents[1] / "src" / "platterpus"

#: Floor. Ten functions construct a QMessageBox today (measured 2026-09-28; one
#: of them is `ui/message_boxes.py::build`). A sweep that finds none would report
#: "no offenders" forever — this file's whole subject.
_MIN_MESSAGE_BOX_SITES: Final[int] = 8

#: Functions that construct a QMessageBox whose text is ENTIRELY literal, where
#: pinning the format changes nothing. Empty today, and deliberately so: all ten
#: sites pin it, which costs one line and removes the need to judge per site.
#: A ratchet — it may shrink, never grow. An entry needs the reason written out,
#: because "this one's text is safe" is a claim about every future edit to that
#: function, not just today's.
_LITERAL_TEXT_ONLY: Final[dict[str, str]] = {}


def _message_box_functions() -> dict[str, tuple[Path, ast.FunctionDef]]:
    """Every function in `src/` that constructs a `QMessageBox`, by `module::name`.

    Keyed on the *constructing function* rather than the call, because
    `setTextFormat` is called on the local variable and both live in one scope.
    A class-level walk would also work; this is the smallest thing that is right.
    """
    found: dict[str, tuple[Path, ast.FunctionDef]] = {}
    for path in sorted(SRC.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover — a broken module fails elsewhere
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            constructs = any(
                isinstance(call, ast.Call)
                and (
                    (isinstance(call.func, ast.Name) and call.func.id == "QMessageBox")
                    or (
                        isinstance(call.func, ast.Attribute)
                        and call.func.attr == "QMessageBox"
                    )
                )
                for call in ast.walk(node)
            )
            if constructs:
                found[f"{path.relative_to(SRC)}::{node.name}"] = (path, node)
    return found


def _pins_plaintext(func: ast.FunctionDef) -> bool:
    """True if this function calls `setTextFormat(...PlainText)`.

    Requires the **PlainText** attribute in the argument, not merely a
    `setTextFormat` call: `setTextFormat(Qt.TextFormat.RichText)` is also a
    `setTextFormat` call and is the opposite of this rule. Matching the method
    name alone would be a label where a subject is needed — the failure mode this
    repo keeps recording.
    """
    for node in ast.walk(func):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "setTextFormat"
        ):
            continue
        if any(
            isinstance(inner, ast.Attribute) and inner.attr == "PlainText"
            for inner in ast.walk(node)
        ):
            return True
    return False


def test_the_sweep_finds_the_message_boxes() -> None:
    """Floor first: a sweep over nothing reports no offenders forever."""
    sites = _message_box_functions()
    assert len(sites) >= _MIN_MESSAGE_BOX_SITES, (
        f"only {len(sites)} QMessageBox-constructing function(s) found under "
        f"{SRC} (floor {_MIN_MESSAGE_BOX_SITES}) — the scan is broken, so the "
        "verdict below means nothing"
    )
    # And the subject: the crash dialog is the site with the worst consequence, so
    # its absence from the population means the sweep is looking in the wrong place
    # even if the count happens to clear.
    assert any("_show_fatal_dialog" in key for key in sites), (
        f"the fatal-error dialog is not in the swept population: {sorted(sites)}"
    )
    # And the site every stock box in the product is built by: 38 call sites
    # reach the screen through it, so a sweep that stopped seeing it would stop
    # checking most of the boxes a user ever reads.
    assert "ui/message_boxes.py::build" in sites, (
        f"`ui/message_boxes.py::build` is not in the swept population: {sorted(sites)}"
    )


def test_every_message_box_pins_plaintext() -> None:
    """The rule itself."""
    offenders: list[str] = []
    for key, (_path, func) in sorted(_message_box_functions().items()):
        if key in _LITERAL_TEXT_ONLY:
            continue
        if not _pins_plaintext(func):
            offenders.append(key)
    assert not offenders, (
        "these functions build a QMessageBox without pinning "
        "`setTextFormat(Qt.TextFormat.PlainText)`. Qt's default AutoText "
        "auto-detects HTML, so any `<` in text that came from MusicBrainz, the "
        "ripper, or an exception message is parsed as markup and the rest is "
        "dropped SILENTLY — the user never learns text went missing "
        "(CLAUDE.md Critical rule #12):\n  " + "\n  ".join(offenders)
    )


def test_the_literal_text_allowlist_argues_for_itself() -> None:
    """An exemption must carry a reason, and the list must not swallow the sweep.

    Empty today. Checked anyway, because the failure mode of an allowlist is that
    it fills up quietly: each entry looks locally reasonable and the sweep ends up
    enforcing nothing.
    """
    sites = _message_box_functions()
    stale = sorted(set(_LITERAL_TEXT_ONLY) - set(sites))
    assert not stale, f"allowlist entries no longer exist as sites: {stale}"
    for key, reason in _LITERAL_TEXT_ONLY.items():
        assert len(reason) >= 60, (
            f"{key}: the exemption reason is too short to be a reason: {reason!r}"
        )
    assert len(_LITERAL_TEXT_ONLY) * 2 < max(len(sites), 1), (
        f"{len(_LITERAL_TEXT_ONLY)} of {len(sites)} message boxes are exempt — past "
        "half, this sweep is a list of excuses"
    )


def test_the_detector_rejects_richtext_and_a_bare_call() -> None:
    """Non-triviality, against constructed input: it must be able to say no.

    Three shapes, because the interesting failure is the middle one — a
    `setTextFormat` call that sets the WRONG format would satisfy any check that
    matched the method name alone.
    """
    plain = ast.parse(
        "def f():\n"
        "    box = QMessageBox()\n"
        "    box.setTextFormat(Qt.TextFormat.PlainText)\n"
    ).body[0]
    rich = ast.parse(
        "def f():\n"
        "    box = QMessageBox()\n"
        "    box.setTextFormat(Qt.TextFormat.RichText)\n"
    ).body[0]
    absent = ast.parse("def f():\n    box = QMessageBox()\n").body[0]

    assert isinstance(plain, ast.FunctionDef)
    assert isinstance(rich, ast.FunctionDef)
    assert isinstance(absent, ast.FunctionDef)

    assert _pins_plaintext(plain) is True
    assert _pins_plaintext(rich) is False, (
        "RichText satisfied the check — matching the method name instead of the "
        "format would accept the exact opposite of this rule"
    )
    assert _pins_plaintext(absent) is False


# ==========================================================================
# The static helpers: refused everywhere except the module that replaces them
# ==========================================================================

#: Qt's static helpers that build a box from a caller's text with no way to pin
#: its format. `about` is on the list although nothing calls it today: it takes a
#: text argument and has the same blind spot. `aboutQt` is not: its text is Qt's.
_STATIC_HELPERS: Final[frozenset[str]] = frozenset(
    {"warning", "information", "critical", "question", "about"}
)

#: The replacements, by the name a call site uses (`message_boxes.<name>`).
_ROUTED_FUNCTIONS: Final[frozenset[str]] = frozenset(
    {"warning", "information", "critical", "question"}
)

#: The one module that may name a static helper. It does so only in its own
#: docstring, which the AST sweep does not read, so today the exemption covers
#: nothing — it exists so the module can explain what it replaces.
_THE_MODULE: Final[str] = "ui/message_boxes.py"
_THE_MODULE_DOTTED: Final[str] = "platterpus.ui.message_boxes"

#: Floor on modules examined: 182 on 2026-09-28. Below this the glob is broken and
#: "no static helper found" is a statement about nothing.
_MIN_MODULES_EXAMINED: Final[int] = 150

#: Floor on calls that go through the module: 38 on 2026-09-28, one per former
#: static call. It is the positive half of the check — proof the sweep reads the
#: call sites it is about, not merely that it found no offender among them.
_MIN_ROUTED_CALLS: Final[int] = 30


def _source_modules() -> list[Path]:
    """Every module in the package, `__pycache__` excluded."""
    return sorted(p for p in SRC.rglob("*.py") if "__pycache__" not in p.parts)


def _qmessagebox_names(tree: ast.Module) -> set[str]:
    """Every name that means `QMessageBox` in one module: itself and any alias.

    `app.py` imports it as `_QMessageBox`, so matching the spelling alone would
    miss a static call written through the alias — measured, not hypothetical.
    """
    names = {"QMessageBox"}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "QMessageBox" and alias.asname:
                    names.add(alias.asname)
    return names


def _is_qmessagebox(node: ast.expr, names: set[str]) -> bool:
    """`QMessageBox` (or an alias), bare or dotted (`QtWidgets.QMessageBox`)."""
    if isinstance(node, ast.Name):
        return node.id in names
    return isinstance(node, ast.Attribute) and node.attr == "QMessageBox"


def _static_helper_uses(source: str) -> list[tuple[int, str]]:
    """`(line, helper)` for every use of a static helper in one module's code.

    A USE, not only a call: `show = QMessageBox.warning` and then `show(...)`
    builds the same AutoText box, and so does `getattr(QMessageBox, "warning")`.
    Docstrings and comments are not code and are not read.
    """
    tree = ast.parse(source)
    names = _qmessagebox_names(tree)
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and node.attr in _STATIC_HELPERS
            and _is_qmessagebox(node.value, names)
        ):
            found.append((node.lineno, node.attr))
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "getattr"
            and len(node.args) >= 2
            and _is_qmessagebox(node.args[0], names)
            and isinstance(node.args[1], ast.Constant)
            and node.args[1].value in _STATIC_HELPERS
        ):
            found.append((node.lineno, str(node.args[1].value)))
    return sorted(found)


def _routed_calls(source: str) -> int:
    """How many `message_boxes.<fn>(...)` calls one module makes."""
    return sum(
        1
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in _ROUTED_FUNCTIONS
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "message_boxes"
    )


def _by_name_imports(source: str) -> list[tuple[int, str]]:
    """`(line, name)` for each `from platterpus.ui.message_boxes import <name>`."""
    return sorted(
        (node.lineno, alias.name)
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module == _THE_MODULE_DOTTED
        for alias in node.names
    )


def test_no_static_message_box_helper_is_used_outside_the_module() -> None:
    """The rule for the half the constructor sweep could not see.

    Floors first, both of them: a sweep over no files finds no offenders, and a
    sweep that cannot recognise the routed calls has not shown it reads the sites
    it is judging.
    """
    assert (SRC / _THE_MODULE).is_file(), (
        f"the exemption names {_THE_MODULE}, which does not exist"
    )
    modules = _source_modules()
    offenders: list[str] = []
    routed = 0
    for path in modules:
        source = path.read_text(encoding="utf-8")
        routed += _routed_calls(source)
        rel = path.relative_to(SRC).as_posix()
        if rel == _THE_MODULE:
            continue
        offenders += [
            f"{rel}:{line}: QMessageBox.{helper}"
            for line, helper in _static_helper_uses(source)
        ]
    assert len(modules) >= _MIN_MODULES_EXAMINED, (
        f"only {len(modules)} modules examined under {SRC} (floor "
        f"{_MIN_MODULES_EXAMINED}) — the scan is broken, so the verdict below "
        "means nothing"
    )
    assert routed >= _MIN_ROUTED_CALLS, (
        f"only {routed} `message_boxes.<fn>(...)` calls found (floor "
        f"{_MIN_ROUTED_CALLS}) — either the call sites stopped going through the "
        "module or this sweep stopped recognising them"
    )
    assert not offenders, (
        "these build a message box with Qt's static helper, which fixes the text "
        "format at AutoText: a first line holding an HTML tag turns the whole "
        "message into markup, and line breaks, unknown tags and entities in text "
        "from a dependency are then changed or dropped SILENTLY. Call the "
        "same-named function in `platterpus.ui.message_boxes` instead — same "
        "arguments, same answer, PlainText (CLAUDE.md Critical rule #12):\n  "
        + "\n  ".join(offenders)
    )


def test_the_module_is_imported_as_a_module_never_by_function() -> None:
    """`from platterpus.ui import message_boxes`, then `message_boxes.warning(...)`.

    Not a style preference. `tests/conftest.py` makes every box answer at once by
    replacing the functions ON THE MODULE, and a call site that imported
    `warning` by name holds the real function instead. Its first box would then
    `exec()` for real, which on the headless test platform waits forever for a
    click — one hung test takes the whole run with it.
    """
    offenders = [
        f"{path.relative_to(SRC).as_posix()}:{line}: imports {name!r} by name"
        for path in _source_modules()
        for line, name in _by_name_imports(path.read_text(encoding="utf-8"))
    ]
    assert not offenders, (
        "import the module and call through it (`from platterpus.ui import "
        "message_boxes`, then `message_boxes.warning(...)`):\n  "
        + "\n  ".join(offenders)
    )


def test_the_static_helper_detector_fires_and_does_not_over_fire() -> None:
    """Non-triviality, against constructed input: every shape it must refuse, and
    the look-alikes it must leave alone. A detector only ever shown clean code has
    not been shown to be able to say no."""
    must_flag = {
        "QMessageBox.warning(self, 't', 'x')\n": [(1, "warning")],
        "QtWidgets.QMessageBox.question(None, 't', 'x')\n": [(1, "question")],
        "from PySide6.QtWidgets import QMessageBox as MB\n"
        "MB.critical(None, 't', 'x')\n": [(2, "critical")],
        "show = QMessageBox.information\n": [(1, "information")],
        "getattr(QMessageBox, 'about')(None, 't', 'x')\n": [(1, "about")],
    }
    for source, expected in must_flag.items():
        assert _static_helper_uses(source) == expected, source
    must_pass = [
        "message_boxes.warning(self, 't', 'x')\n",
        "icon = QMessageBox.Icon.Warning\n",
        "yes = QMessageBox.StandardButton.Yes\n",
        "box = QMessageBox(self)\nbox.setText('x')\n",
        "QMessageBox.aboutQt(None)\n",
        "def f():\n    '''Do not call QMessageBox.warning(self, ...) here.'''\n",
        "getattr(QMessageBox, 'StandardButton')\n",
    ]
    for source in must_pass:
        assert _static_helper_uses(source) == [], source
    assert _routed_calls("message_boxes.question(self, 't', 'x')\n") == 1
    assert _routed_calls("message_boxes.build(icon, None, 't', 'x')\n") == 0
    assert _by_name_imports("from platterpus.ui.message_boxes import warning\n") == [
        (1, "warning")
    ]
    assert _by_name_imports("from platterpus.ui import message_boxes\n") == []


# ==========================================================================
# The box itself: PlainText for every kind, read back off the widget
# ==========================================================================

#: Which icon each of the four functions shows: the one difference between them.
_KIND_ICONS: Final[dict[str, QMessageBox.Icon]] = {
    "information": QMessageBox.Icon.Information,
    "warning": QMessageBox.Icon.Warning,
    "critical": QMessageBox.Icon.Critical,
    "question": QMessageBox.Icon.Question,
}

#: A message shaped like the dependency summary, whose first line Qt WOULD read as
#: HTML — asserted below, so these tests cannot silently drift onto text that
#: AutoText would have shown correctly anyway.
_MISREAD_UNDER_AUTOTEXT: Final[str] = (
    "<b>cyanrip</b> 0.9.3 (platterpus-fork)\n"
    "Install failures:\n"
    "  • flac: <stdin>: not found &amp; gone"
)

#: The four REAL functions, taken when this file is imported. `tests/conftest.py`
#: replaces them on the module for every test so no box ever waits for a click;
#: collection imports this file before any test (and so any fixture) runs, so
#: these references are the product's own functions.
_REAL_FUNCTIONS: Final[dict[str, object]] = {
    kind: getattr(message_boxes, kind) for kind in _KIND_ICONS
}


def test_every_kind_the_module_offers_is_in_the_population() -> None:
    """Floor for the two parametrized tests below, which run once per kind.

    Derived from the module's SOURCE, not from `_KIND_ICONS`: its public
    functions other than `build` are the kinds a call site can show, so a fifth
    function added there without a case here fails by name instead of going
    unchecked, and an emptied table cannot pass by generating no cases.
    """
    tree = ast.parse((SRC / _THE_MODULE).read_text(encoding="utf-8"))
    offered = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and not node.name.startswith("_")
        and node.name != "build"
    }
    assert offered == set(_KIND_ICONS) == set(_ROUTED_FUNCTIONS), offered
    assert len(offered) == 4
    # And the references the tests call are the product's own functions, not the
    # stand-ins conftest puts on the module for every test.
    for kind, function in _REAL_FUNCTIONS.items():
        assert getattr(function, "__module__", None) == _THE_MODULE_DOTTED, kind
        assert getattr(function, "__name__", None) == kind


def test_the_misread_text_is_the_case_that_matters(qapp: QApplication) -> None:
    """The premise of the two tests below, checked rather than assumed."""
    assert QtGui.Qt.mightBeRichText(_MISREAD_UNDER_AUTOTEXT) is True
    # And the default really is AutoText, so pinning is what makes the difference.
    default_box = QMessageBox()
    try:
        assert default_box.textFormat() == Qt.TextFormat.AutoText
    finally:
        default_box.deleteLater()


@pytest.mark.parametrize("kind", sorted(_KIND_ICONS))
def test_the_builder_pins_plaintext_for_every_kind(
    qapp: QApplication, kind: str
) -> None:
    """(b) Build the box each kind shows and read the format back off it.

    Off the widget, and off the label that paints the text, rather than off the
    source: the property that protects the user is what the label does.
    """
    box = message_boxes.build(
        _KIND_ICONS[kind], None, f"{kind} title", _MISREAD_UNDER_AUTOTEXT
    )
    try:
        assert box.textFormat() == Qt.TextFormat.PlainText
        label = box.findChild(QLabel, "qt_msgbox_label")
        assert label is not None, "Qt's message label was not found by its name"
        assert label.textFormat() == Qt.TextFormat.PlainText
        assert label.text() == _MISREAD_UNDER_AUTOTEXT, "the text must be verbatim"
        assert box.icon() == _KIND_ICONS[kind]
    finally:
        box.deleteLater()


@pytest.mark.parametrize("kind", sorted(_KIND_ICONS))
def test_each_function_shows_the_built_box(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    """The four public functions show exactly that box, not one of their own.

    `exec` is replaced so the box is inspected at the moment it would appear and
    closed without a click, which Qt answers as NoButton.
    """
    seen: list[tuple[Qt.TextFormat, QMessageBox.Icon, str, str]] = []

    def _inspect_instead_of_blocking(box: QMessageBox) -> int:
        seen.append((box.textFormat(), box.icon(), box.windowTitle(), box.text()))
        return 0

    monkeypatch.setattr(QMessageBox, "exec", _inspect_instead_of_blocking)
    show = _REAL_FUNCTIONS[kind]
    assert callable(show)
    answer = show(None, f"{kind} title", _MISREAD_UNDER_AUTOTEXT)
    assert seen == [
        (
            Qt.TextFormat.PlainText,
            _KIND_ICONS[kind],
            f"{kind} title",
            _MISREAD_UNDER_AUTOTEXT,
        )
    ]
    assert answer == QMessageBox.StandardButton.NoButton
