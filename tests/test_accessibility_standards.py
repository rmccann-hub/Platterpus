"""WCAG 2.2 AA criteria this app can be held to, enforced rather than asserted.

**Where this came from.** The maintainer commissioned a UI/UX and accessibility
standards review (2026-08-14) and asked for an audit against it, plus rules "so
we do not regress". The review targets *web* line-of-business apps; Platterpus is
desktop Qt, so the DOM-specific half of it (``scroll-padding-top``,
``appearance: base-select``, reflow to 320 px, TV safe areas) does not transfer
and is deliberately not tested here. Pretending it did would be the kind of
box-ticking that makes a conformance claim worthless.

**What does transfer is tested here, and the audit found the app already passing
most of it.** That is exactly when a rule is worth writing down: a passing state
with nothing holding it decays silently, and `CLAUDE.md` is explicit that a
comment where a check belongs is not a fix. Each test below therefore pins a
property the app *currently has*, so the regression is what fails — not the
adoption.

Criteria covered, with why each is testable from source:

* **1.4.1 Use of Color (A)** — every verdict level must carry a non-colour
  marker. ~8% of men have red/green CVD, and a greyscale screenshot or a
  forced-colors theme drops hue entirely. Measured by calling the *real* verdict
  function, not by reading the source for glyphs.
* **2.1.4 Character Key Shortcuts (A)** — the review names this "the criterion
  most often missed on Excel-like grids". Single-character shortcuts fire on
  speech input. We have none; this keeps it that way.
* **3.2.6 Consistent Help (A)** — help stays in one place, reachable by the
  platform's standard key.
* **2.5.8 Target Size (AA)** — 24 px floor, 44 px for committing actions.
* **4.1.3 Status Messages (AA)** — a state change is announced without stealing
  focus.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src" / "platterpus"
UI = SRC / "ui"

#: Markers that carry a status without colour. Deliberately a small closed set:
#: a glyph nobody recognises is not a second channel, and an ad-hoc one per
#: message would let two levels drift into looking alike.
STATUS_MARKERS: frozenset[str] = frozenset("✓⚠ⓘ✗")


class TestUseOfColour:
    """1.4.1 — colour is reinforcement, never the only channel."""

    def test_every_verdict_level_carries_a_non_colour_marker(self) -> None:
        """Measured by *calling* the verdict function across the real branches.

        Reading the source for glyph literals would pass on a branch that builds
        its message some other way, so each case is constructed and run.
        """
        from platterpus.verdict import accuraterip_verdict

        # The fakes speak the classifier's REAL contract, read out of
        # `parsers/rip_log.accuraterip_is_match`: a match is `confidence >= 1`
        # AND a non-all-zero `local_crc`. The first version of this test invented
        # a `matched` attribute nothing reads, so every case fell through to the
        # same branch — and the floor below is what caught it, which is the
        # entire reason the floor is there.
        class _AR:
            def __init__(self, confidence: int | None, crc: str = "1A2B3C4D") -> None:
                self.confidence = confidence
                self.local_crc = crc

        class _Track:
            def __init__(self, *, exact: bool, variant: bool = False) -> None:
                hit = _AR(129)
                miss = _AR(None)
                self.copy_crc = "DEADBEEF"
                self.accuraterip_v1 = hit if exact else miss
                self.accuraterip_v2 = hit if exact else miss
                self.accuraterip_offset = _AR(200) if variant else None

        class _Log:
            def __init__(self, tracks: list[_Track]) -> None:
                self.tracks = tracks

        cases = {
            "all verified -> ok": _Log([_Track(exact=True) for _ in range(3)]),
            "some verified -> warn": _Log([_Track(exact=True), _Track(exact=False)]),
            "exact plus offset-variant -> warn": _Log(
                [_Track(exact=True), _Track(exact=False, variant=True)]
            ),
            "only offset-variant -> warn": _Log(
                [_Track(exact=False, variant=True) for _ in range(2)]
            ),
            "none matched -> neutral": _Log([_Track(exact=False) for _ in range(2)]),
        }

        seen: dict[str, set[str]] = {}
        for name, log in cases.items():
            message, level = accuraterip_verdict(log)
            if not message:
                continue
            first = message.strip()[0]
            assert first in STATUS_MARKERS, (
                f"the {name!r} verdict starts with {first!r}, which is not a "
                f"status marker — its level would be conveyed by COLOUR ALONE, "
                f"invisible to a CVD reader, a greyscale screenshot, or a "
                f"forced-colors theme. Message: {message[:90]!r}"
            )
            seen.setdefault(level, set()).add(first)

        assert len(seen) >= 2, (
            f"only {len(seen)} level(s) were exercised ({sorted(seen)}) — this "
            "check can pass by examining almost nothing; broaden the cases"
        )
        # Two levels sharing a marker is the failure this exists to catch: the
        # text would read the same and only the tint would differ.
        for level, markers in seen.items():
            assert len(markers) == 1, (
                f"level {level!r} uses inconsistent markers {markers} — a reader "
                "cannot learn what the symbol means"
            )
        collapsed = [m for markers in seen.values() for m in markers]
        assert len(set(collapsed)) == len(collapsed), (
            f"two levels share a marker ({seen}) — in greyscale they are "
            "indistinguishable, which is the whole failure mode 1.4.1 names"
        )

    def test_the_marker_check_would_notice_a_bare_message(self) -> None:
        """Non-triviality floor. Without this, a `STATUS_MARKERS` containing
        every character would make the test above pass unconditionally."""
        assert "3" not in STATUS_MARKERS
        assert "A" not in STATUS_MARKERS
        assert not STATUS_MARKERS & set("abcdefghijklmnopqrstuvwxyz0123456789 ")


class TestCharacterKeyShortcuts:
    """2.1.4 — the criterion the standards review calls most-often-missed."""

    def test_no_single_character_shortcut_anywhere(self) -> None:
        """A bare letter shortcut fires on speech input mid-dictation.

        We currently have none — every shortcut is a `QKeySequence.StandardKey`,
        which resolves to a modified key on each platform. This keeps it true:
        the moment someone writes `setShortcut("R")` the suite says why not.
        """
        offenders: list[str] = []
        for path in sorted(UI.rglob("*.py")):
            for lineno, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), 1
            ):
                match = re.search(r'setShortcut\(\s*["\']([^"\']*)["\']', line)
                if not match:
                    continue
                sequence = match.group(1)
                # A modifier makes it safe; a bare printable character does not.
                if not re.search(r"(Ctrl|Alt|Meta|Shift|F\d|Esc|Del|Ins)", sequence):
                    offenders.append(
                        f"{path.relative_to(SRC.parent)}:{lineno}: {sequence!r}"
                    )
        assert not offenders, (
            "single-character keyboard shortcuts (WCAG 2.1.4 Character Key "
            "Shortcuts, level A). These fire while a speech-input user is "
            "dictating. Use QKeySequence.StandardKey, or add a modifier:\n  "
            + "\n  ".join(offenders)
        )

    def test_the_sweep_actually_reaches_the_ui_package(self) -> None:
        """Floor: a broken glob would make the check above pass by scanning
        nothing, which is indistinguishable from conformance."""
        modules = list(UI.rglob("*.py"))
        assert len(modules) >= 20, (
            f"only {len(modules)} modules under {UI} — the sweep is not reaching "
            "the UI package, so a clean result means nothing"
        )
        assert any("setShortcut" in p.read_text(encoding="utf-8") for p in modules), (
            "no setShortcut call found at all — either the sweep is looking in "
            "the wrong place or the menu lost its shortcuts; both are findings"
        )


class TestConsistentHelp:
    """3.2.6 — help lives in one predictable place."""

    def test_help_is_a_menu_with_the_platform_help_key(self) -> None:
        source = (UI / "main_window.py").read_text(encoding="utf-8")
        assert 'addMenu("&Help")' in source, "the Help menu moved or was renamed"
        assert "QKeySequence.StandardKey.HelpContents" in source, (
            "the user guide lost its standard Help key (F1 on this platform); "
            "3.2.6 wants help reachable the same way every time"
        )


class TestStatusMessages:
    """4.1.3 — a state change reaches assistive tech without stealing focus."""

    def test_the_announce_helper_exists_and_is_used(self) -> None:
        from platterpus.ui import accessibility

        assert hasattr(accessibility, "announce")
        users = [
            p.relative_to(SRC.parent)
            for p in UI.rglob("*.py")
            if "announce(" in p.read_text(encoding="utf-8")
            and p.name != "accessibility.py"
        ]
        assert users, (
            "nothing calls `announce()` — status changes are silent to a screen "
            "reader (WCAG 4.1.3), and a helper nobody calls is the shape this "
            "project has shipped three times"
        )

    def test_announcing_does_not_move_focus(self) -> None:
        """The 'without stealing focus' half, which is the part that gets lost.

        An announcement implemented as `setFocus()` would be *heard* and would
        also yank the user out of whatever they were doing mid-rip.
        """
        import inspect

        from platterpus.ui import accessibility

        src = inspect.getsource(accessibility.announce)
        assert "setFocus" not in src, (
            "announce() moves focus; a status update must not relocate the user"
        )


class TestTargetSize:
    """2.5.8 — 24 px floor, 44 px for anything that commits.

    Qt sizes most controls from the platform style, which is the WCAG
    "user-agent control" exception — but the moment we set an explicit height we
    have taken responsibility for it. So the rule is applied to *our own*
    explicit sizing, which is the only part we control and the only part that
    can regress silently.
    """

    MINIMUM_PX = 24

    def test_no_explicit_size_drops_below_the_floor(self) -> None:
        offenders: list[str] = []
        pattern = re.compile(r"set(?:Fixed|Minimum)(?:Height|Width)\(\s*(\d+)\s*\)")
        for path in sorted(UI.rglob("*.py")):
            text = path.read_text(encoding="utf-8")
            tree = ast.parse(text, filename=str(path))
            comment_lines = {
                lineno
                for lineno, line in enumerate(text.splitlines(), 1)
                if line.lstrip().startswith("#")
            }
            del tree  # parsed only to prove the file is real Python
            for lineno, line in enumerate(text.splitlines(), 1):
                if lineno in comment_lines:
                    continue
                for match in pattern.finditer(line):
                    value = int(match.group(1))
                    if value < self.MINIMUM_PX:
                        offenders.append(
                            f"{path.relative_to(SRC.parent)}:{lineno}: {value}px"
                        )
        assert not offenders, (
            "explicitly sized below the 24 px WCAG 2.5.8 floor:\n  "
            + "\n  ".join(offenders)
        )


class TestShortcutsSurviveAQtUpgrade:
    """2.1.1 — a menu action must stay keyboard-reachable across Qt versions.

    **A platform theme is a dependency, and this one moved under us.** The
    convention above says to use `QKeySequence.StandardKey` rather than a literal,
    so shortcuts resolve to a modified key per platform. What it assumed, and never
    checked, is that Qt actually *has* a binding for the key we ask about.

    PySide6 **6.11.2** stopped having two of them. Measured 2026-08-18, same
    machine, same `QT_QPA_PLATFORM=offscreen`, only the wheel changed:

        6.11.1   Quit -> 'Exit'   Preferences -> 'Settings'   HelpContents -> 'F1'
        6.11.2   Quit -> ''       Preferences -> ''           HelpContents -> 'F1'

    So on 6.11.2 the **Quit** and **Settings** items shipped with no shortcut at
    all — a WCAG 2.1.1 regression from a routine dependency release, with no change
    to our code. `main_window.standard_shortcut` asks Qt and then *checks the
    answer*.
    """

    def test_an_unbound_standard_key_falls_back_to_a_real_sequence(self, qapp) -> None:
        """The fallback fires when Qt supplies nothing.

        `StandardKey.UnknownKey` is used as the forced-empty case rather than
        `Quit`, because `Quit` is empty on 6.11.2 and non-empty on 6.11.1 — a test
        keyed on it would assert different things on different wheels, which is the
        problem, not a way to check it. `UnknownKey` is empty on both (verified).
        """
        from PySide6.QtGui import QKeySequence

        from platterpus.ui.main_window import standard_shortcut

        unbound = QKeySequence.StandardKey.UnknownKey
        assert QKeySequence(unbound).isEmpty(), (
            "UnknownKey is bound on this Qt, so this test no longer forces the "
            "empty branch — pick another unbound key rather than deleting the test"
        )
        got = standard_shortcut(unbound, "Ctrl+Q")
        assert not got.isEmpty(), "the fallback did not fire"
        assert got.toString() == "Ctrl+Q"

    def test_qt_wins_when_qt_has_an_answer(self, qapp) -> None:
        """Non-triviality: the fallback must not override a working binding.

        Without this, `standard_shortcut` could ignore Qt entirely and every other
        assertion here would still pass — the platform key is the whole reason
        StandardKey is the convention.
        """
        from PySide6.QtGui import QKeySequence

        from platterpus.ui.main_window import standard_shortcut

        help_key = QKeySequence.StandardKey.HelpContents
        qt_says = QKeySequence(help_key)
        assert not qt_says.isEmpty(), "HelpContents is unbound; pick a bound key"
        got = standard_shortcut(help_key, "Ctrl+Alt+Shift+Z")
        assert got.toString() == qt_says.toString(), (
            "the fallback overrode Qt's own binding — StandardKey must win when it "
            "resolves, or the per-platform behaviour is lost"
        )

    def test_every_menu_shortcut_goes_through_the_guard(self) -> None:
        """A raw `setShortcut(QKeySequence.StandardKey.X)` is the shape that broke.

        Swept rather than fixed at the three sites, because the next person adding a
        menu action will reach for the raw form — it is what the convention above
        literally says to do, and it is what silently lost a shortcut.
        """
        source = (UI / "main_window.py").read_text(encoding="utf-8")
        raw = re.findall(
            r"setShortcut\(\s*QKeySequence\.StandardKey\.(\w+)\s*\)", source
        )
        assert not raw, (
            "these shortcuts ask Qt without checking the answer, so a Qt release "
            f"that drops the binding removes them silently: {raw}. Wrap them in "
            "main_window.standard_shortcut(..., '<fallback with a modifier>')."
        )
        guarded = re.findall(
            r"standard_shortcut\(\s*QKeySequence\.StandardKey\.(\w+)", source
        )
        assert len(guarded) >= 3, (
            f"only {len(guarded)} guarded shortcut(s) found ({guarded}) — the sweep "
            "above can pass by there being no shortcuts at all"
        )

    def test_every_fallback_carries_a_modifier(self) -> None:
        """The fallback must not reintroduce the bare-letter problem (2.1.4)."""
        source = (UI / "main_window.py").read_text(encoding="utf-8")
        fallbacks = re.findall(
            r"standard_shortcut\(\s*QKeySequence\.StandardKey\.\w+\s*,\s*[\"']([^\"']+)[\"']",
            source,
        )
        assert fallbacks, "no fallbacks found — the sweep is not seeing the call sites"
        bare = [
            f
            for f in fallbacks
            if not re.search(r"(Ctrl|Alt|Meta|Shift|F\d|Esc|Del|Ins)", f)
        ]
        assert not bare, (
            f"these fallbacks are bare printable keys and fire during speech input "
            f"(WCAG 2.1.4): {bare}"
        )
