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

**What this sweep does NOT cover, said out loud rather than implied.** It checks
`QMessageBox` only. There are 13 `QLabel(<non-literal>)` sites in `src/`, and they
are *not* swept here: most build their text from our own constants, so a blanket
rule would need a long allowlist and a list of excuses enforces nothing. They are
tracked in `TASKS.md` instead. Scoping a sweep is fine; scoping it *silently while
the rule claims everything* is the defect this file was written to fix, so
`CLAUDE.md` was corrected in the same commit to say what is actually swept.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Final

SRC: Final[Path] = Path(__file__).resolve().parents[1] / "src" / "platterpus"

#: Floor. Six functions construct a QMessageBox today. A sweep that finds none
#: would report "no offenders" forever — this file's whole subject.
_MIN_MESSAGE_BOX_SITES: Final[int] = 5

#: Functions that construct a QMessageBox whose text is ENTIRELY literal, where
#: pinning the format changes nothing. Empty today, and deliberately so: all six
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
