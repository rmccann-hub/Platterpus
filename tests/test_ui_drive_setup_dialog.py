"""Tests for platterpus.ui.drive_setup_dialog.

We don't drive a real worker thread — we construct the dialog and call
its `_on_finished` slot directly to verify result rendering.
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from platterpus.adapters.rip_backend import RipBackend
from platterpus.ui.drive_setup_dialog import DriveSetupDialog, _format_result
from platterpus.workers.drive_setup_worker import DriveSetupResult


class _StubBackend(RipBackend):
    def list_drives(self):  # type: ignore[override]
        return []

    def disc_info(self, drive):  # type: ignore[override]
        raise NotImplementedError

    def rip(self, *a, **kw):  # type: ignore[override]
        raise NotImplementedError

    def version(self) -> str:  # type: ignore[override]
        return "fake"

    def supports_offset_detection(self) -> bool:  # type: ignore[override]
        # A detection-capable backend, so the detect-flow tests exercise the
        # Detect button + progress bar. cyanrip is the real no-detect case,
        # covered by _NonDetectingBackend below.
        return True


class _NonDetectingBackend(_StubBackend):
    """A backend that can do NEITHER offset detection nor cache analysis."""

    def supports_offset_detection(self) -> bool:  # type: ignore[override]
        return False

    def supports_cache_analysis(self) -> bool:  # type: ignore[override]
        return False


class _CacheOnlyBackend(_StubBackend):
    """Mirrors cyanrip: can MEASURE the cache but has no offset finder (KDD-29)."""

    def supports_offset_detection(self) -> bool:  # type: ignore[override]
        return False

    def supports_cache_analysis(self) -> bool:  # type: ignore[override]
        return True


def _dialog(qapp: QApplication) -> DriveSetupDialog:
    return DriveSetupDialog(_StubBackend(), "/dev/sr0")


def test_initial_state(qapp: QApplication) -> None:
    dialog = _dialog(qapp)
    assert dialog._detect_button.isEnabled() is True
    assert dialog._progress.isVisible() is False
    assert "/dev/sr0" in dialog._device_label.text()
    assert dialog._results_label.toPlainText() == ""


def test_manual_offset_save_emits_signal(qapp: QApplication) -> None:
    """The manual fallback emits the entered offset for the main window."""
    dialog = _dialog(qapp)
    captured: list[int] = []
    dialog.manual_offset_saved.connect(captured.append)

    dialog._offset_spin.setValue(667)
    dialog._on_save_offset_clicked()

    assert captured == [667]
    assert "+667" in dialog._status_label.text()


def test_manual_offset_prefilled_from_current(qapp: QApplication) -> None:
    dialog = DriveSetupDialog(_StubBackend(), "/dev/sr0", current_offset=-12)
    assert dialog._offset_spin.value() == -12


def test_known_offset_prefills_spinbox(qapp: QApplication) -> None:
    # The model-looked-up offset is the primary path: it must pre-fill the
    # spinbox (and take precedence over current_offset) so the user can save
    # it in one click without a disc.
    dialog = DriveSetupDialog(
        _StubBackend(),
        "/dev/sr0",
        current_offset=0,
        known_offset=667,
        drive_label="PIONEER BD-RW BDR-209D",
    )
    assert dialog._offset_spin.value() == 667


def test_known_offset_save_emits_that_value(qapp: QApplication) -> None:
    dialog = DriveSetupDialog(
        _StubBackend(), "/dev/sr0", known_offset=667, drive_label="PIONEER BDR-209D"
    )
    captured: list[int] = []
    dialog.manual_offset_saved.connect(captured.append)
    dialog._save_offset_button.click()
    assert captured == [667]


def test_on_finished_renders_success(qapp: QApplication) -> None:
    dialog = _dialog(qapp)
    dialog._on_finished(
        DriveSetupResult(
            offset=667,
            can_defeat_cache=True,
        )
    )
    text = dialog._results_label.toPlainText()
    assert "+667 samples" in text
    assert "Audio cache" in text
    assert dialog._progress.isVisible() is False
    assert dialog._detect_button.text() == "Re-detect"


def test_manual_controls_locked_during_detection(qapp: QApplication) -> None:
    """The offset spinbox + Save button lock while detection runs, and the
    finish slot re-enables them."""
    dialog = _dialog(qapp)
    # Both live before detection.
    assert dialog._offset_spin.isEnabled() is True
    assert dialog._save_offset_button.isEnabled() is True

    dialog._on_detect_clicked()
    assert dialog._offset_spin.isEnabled() is False
    assert dialog._save_offset_button.isEnabled() is False

    # Stop the worker thread we just started, then deliver the result.
    dialog._stop_detection()
    dialog._on_finished(DriveSetupResult(offset=667, can_defeat_cache=True))
    assert dialog._offset_spin.isEnabled() is True
    assert dialog._save_offset_button.isEnabled() is True


def test_on_finished_ignored_while_closing(qapp: QApplication) -> None:
    """A late worker result must not poke widgets once the dialog is closing.

    This is what prevented the crash: on close we cancel + join the thread,
    and any queued finished signal that arrives afterward is a no-op."""
    dialog = _dialog(qapp)
    dialog._closing = True
    dialog._on_finished(DriveSetupResult(offset=667, can_defeat_cache=True))
    assert dialog._results_label.toPlainText() == ""  # untouched


def test_no_detect_button_when_backend_cannot_detect(qapp: QApplication) -> None:
    """cyanrip has no offset finder, so the dialog must NOT offer a Detect button
    that can only fail — the offset comes from the AccurateRip list / manual
    entry. (Honesty: never present a non-working path as working.)
    """
    dialog = DriveSetupDialog(
        _NonDetectingBackend(),
        "/dev/sr0",
        known_offset=667,
        drive_label="PIONEER BD-RW BDR-209D",
    )
    assert dialog._can_detect is False
    assert dialog._detect_button is None
    assert dialog._progress is None
    # Manual save still works — it's the primary path now.
    captured: list[int] = []
    dialog.manual_offset_saved.connect(captured.append)
    dialog._save_offset_button.click()
    assert captured == [667]


def test_no_detect_mode_omits_verification_wording(qapp: QApplication) -> None:
    """The known-offset callout must not advertise 'Detect' verification when the
    backend can't detect."""
    dialog = DriveSetupDialog(
        _NonDetectingBackend(),
        "/dev/sr0",
        known_offset=667,
        drive_label="PIONEER BD-RW BDR-209D",
    )
    texts = [
        w.text()
        for w in dialog.findChildren(type(dialog._device_label))
        if hasattr(w, "text")
    ]
    joined = "\n".join(texts)
    assert "optional verification" not in joined
    assert "auto-detection isn't available" in joined.lower()


def test_format_result_offset_failure() -> None:
    text = _format_result(
        DriveSetupResult(offset=None, offset_error="not in AccurateRip")
    )
    assert "✗ Read offset: not in AccurateRip" in text


def test_format_result_negative_offset_signed() -> None:
    text = _format_result(DriveSetupResult(offset=-582, can_defeat_cache=False))
    assert "-582 samples" in text


def test_undefeatable_cache_is_reported_as_a_warning_not_reassurance() -> None:
    """REGRESSION (2026-07-26): can_defeat_cache is "do re-reads reach the disc?",
    so False is the DANGEROUS outcome — but the wording read "this drive doesn't
    cache audio, so Platterpus doesn't need to read around a cache", presenting the
    one genuinely worrying result as fine. It must warn instead."""
    text = _format_result(DriveSetupResult(can_defeat_cache=False))
    assert "⚠" in text
    assert "CACHED audio" in text
    assert "doesn't cache audio" not in text  # the old, inverted reassurance
    # …and it must not leave the user thinking the rip is worthless either.
    assert "AccurateRip" in text


def test_defeated_cache_does_not_claim_the_drive_caches() -> None:
    """True means re-reads reach the disc (cache flushed OR absent) — it must not
    assert "this drive caches audio", which we didn't establish."""
    text = _format_result(DriveSetupResult(can_defeat_cache=True))
    assert "re-reads reach the disc" in text
    assert "this drive caches audio" not in text


def test_cache_only_success_is_not_finished_with_issues(qapp: QApplication) -> None:
    """REGRESSION (real hardware, 2026-07-26): a perfect cache measurement on
    cyanrip announced "Finished with issues." because `ok` meant "got an offset"
    and cyanrip never has one. Guard it at the exact widget the user read."""
    dialog = DriveSetupDialog(_CacheOnlyBackend(), "/dev/sr0")
    dialog._on_finished(DriveSetupResult(can_defeat_cache=True))
    assert dialog._status_label.text() == "Done."
    assert "Finished with issues" not in dialog._status_label.text()


# --- Cache-only (cyanrip) analyze path (KDD-29) ------------------------------


def test_cache_only_backend_shows_analyse_button(qapp: QApplication) -> None:
    """cyanrip can't detect the offset but CAN measure the cache — so the dialog
    offers an "Analyse cache" action even though offset detection is off."""
    dialog = DriveSetupDialog(_CacheOnlyBackend(), "/dev/sr0")
    assert dialog._can_detect is False
    assert dialog._can_analyze is True
    assert dialog._detect_button is not None
    # Labelled as a cache analysis, not "Detect" (which implies offset finding).
    assert "cache" in dialog._detect_button.text().lower()


def test_on_finished_emits_for_cache_only_result(qapp: QApplication) -> None:
    """A cache-only run (no offset) must still record its verdict, and the button
    re-labels to "Re-analyse cache"."""
    dialog = DriveSetupDialog(_CacheOnlyBackend(), "/dev/sr0")
    captured: list[DriveSetupResult] = []
    dialog.detection_recorded.connect(captured.append)

    dialog._on_finished(
        DriveSetupResult(offset=None, offset_error=None, can_defeat_cache=True)
    )

    assert len(captured) == 1  # recorded even with no offset
    assert captured[0].can_defeat_cache is True
    assert dialog._detect_button.text() == "Re-analyse cache"


def test_no_emit_when_nothing_measured(qapp: QApplication) -> None:
    """A run that produced neither an offset nor a cache verdict has nothing to
    persist — the recorder signal must not fire."""
    dialog = DriveSetupDialog(_CacheOnlyBackend(), "/dev/sr0")
    captured: list[DriveSetupResult] = []
    dialog.detection_recorded.connect(captured.append)

    dialog._on_finished(
        DriveSetupResult(offset=None, can_defeat_cache=None, analyze_error="no disc")
    )
    assert captured == []


def test_format_result_omits_offset_line_for_cache_only() -> None:
    """A cache-only result (offset None, offset_error None = not attempted) must
    NOT print a misleading ✗ offset line — only the cache verdict shows."""
    text = _format_result(
        DriveSetupResult(offset=None, offset_error=None, can_defeat_cache=True)
    )
    assert "Read offset" not in text
    assert "cache" in text.lower()


# --- Keyboard reachability + announcements (a11y gap #4) ---------------------


def test_offset_lookup_link_is_keyboard_followable(qapp: QApplication) -> None:
    """The accuraterip.com lookup link was mouse-only (QLabel default) — the
    one affordance in this dialog a keyboard user couldn't reach. The
    keyboard-links flag also puts the label in the tab chain (StrongFocus)."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QLabel

    dialog = DriveSetupDialog(_StubBackend(), "/dev/sr0")
    link_labels = [
        label
        for label in dialog.findChildren(QLabel)
        if "accuraterip.com" in label.text()
    ]
    assert len(link_labels) == 1
    flags = link_labels[0].textInteractionFlags()
    assert flags & Qt.TextInteractionFlag.LinksAccessibleByKeyboard
    assert link_labels[0].focusPolicy() & Qt.FocusPolicy.TabFocus


def test_manual_offset_spin_has_accessible_name(qapp: QApplication) -> None:
    dialog = DriveSetupDialog(_StubBackend(), "/dev/sr0")
    assert dialog._offset_spin.accessibleName()


def test_save_offset_confirmation_is_announced(qapp: QApplication, monkeypatch) -> None:
    heard: list[str] = []
    monkeypatch.setattr(
        "platterpus.ui.drive_setup_dialog.announce",
        lambda _source, message: heard.append(message) or True,
    )
    dialog = DriveSetupDialog(_StubBackend(), "/dev/sr0")
    dialog._offset_spin.setValue(667)

    dialog._on_save_offset_clicked()

    assert len(heard) == 1
    assert "+667" in heard[0]


# --- Layout: text must never be clipped ------------------------------------
#
# Regression for the measured clipping (2026-07-29). `setMinimumSize(460, 320)` was a
# hand-picked guess 185 px shorter than the content needs, so shrinking the dialog cut
# off its own explanation of what a read offset IS — the intro label was 73 px short at
# 440x300. Nothing overlapped, because `_results_label` has stretch=1 and absorbed the
# squeeze until it had nothing left; then the fixed prose took it.


def _clipped_labels(dialog: DriveSetupDialog) -> list[str]:
    """Every visible label whose text needs more room than it was given.

    A word-wrapped label's `heightForWidth` is the truth; its `minimumSizeHint`
    height is one line, which is exactly why the layout under-reported and the
    hand-picked minimum looked adequate.
    """
    from PySide6.QtWidgets import QLabel

    bad: list[str] = []
    for label in dialog.findChildren(QLabel):
        if label.isHidden() or not label.text():
            continue
        if label.wordWrap():
            needed = label.heightForWidth(label.width())
        else:
            needed = label.sizeHint().height()
            if label.sizeHint().width() > label.width() + 1:
                bad.append(f"{label.text()[:40]!r} clipped horizontally")
        if needed > label.height() + 1:
            bad.append(
                f"{label.text()[:40]!r} short by {needed - label.height()}px "
                f"(has {label.height()}, needs {needed} at width {label.width()})"
            )
    return bad


@pytest.mark.parametrize("known_offset", [None, 667])
def test_the_dialog_cannot_be_shrunk_until_its_text_is_clipped(
    qapp: QApplication, known_offset: int | None
) -> None:
    """Both configurations, several sizes, no clipped prose.

    Parametrised over `known_offset` because the known-offset banner is an extra
    wrapped label — it made the deficit worse (3 clipped labels at 440x300 vs 2), and
    a test that only covered one shape would have missed the bigger case.
    """
    dialog = DriveSetupDialog(
        _CacheOnlyBackend(),
        "/dev/sr0",
        known_offset=known_offset,
        drive_label="PIONEER BD-RW BDR-209D",
    )
    dialog.show()

    examined = 0
    for width, height in ((760, 620), (560, 520), (460, 420), (440, 360), (440, 300)):
        dialog.resize(width, height)
        qapp.processEvents()
        clipped = _clipped_labels(dialog)
        examined += 1
        assert not clipped, (
            f"asked for {width}x{height} (became "
            f"{dialog.width()}x{dialog.height()}) and text is clipped: {clipped}"
        )
    # Floor: "no clipping" is trivially true if we never actually laid anything out.
    assert examined == 5
    from PySide6.QtWidgets import QLabel

    assert len([lbl for lbl in dialog.findChildren(QLabel) if lbl.text()]) >= 3, (
        "found fewer than three labels with text — the dialog was not built, so "
        "this check passed by finding nothing."
    )


@pytest.mark.parametrize("known_offset", [None, 667])
def test_the_minimum_size_is_derived_from_the_content_not_hardcoded(
    qapp: QApplication, known_offset: int | None
) -> None:
    """The mechanism, pinned separately from the symptom.

    The symptom test above would also pass if someone hardcoded a large enough
    minimum — which would then rot the moment the intro text changes. This asserts
    the minimum actually tracks the laid-out content, and that it is big enough to
    show it.
    """
    dialog = DriveSetupDialog(
        _CacheOnlyBackend(),
        "/dev/sr0",
        known_offset=known_offset,
        drive_label="PIONEER BD-RW BDR-209D",
    )
    dialog.show()

    minimum = dialog.minimumSize()
    hint = dialog.sizeHint()
    assert minimum.height() >= min(hint.height(), 620), (
        f"minimum height {minimum.height()} is below what the content needs "
        f"({hint.height()}), so the dialog can still be shrunk into clipping."
    )
    # It really is enforced, not merely stored: a smaller resize must be refused.
    dialog.resize(300, 200)
    qapp.processEvents()
    assert dialog.height() >= minimum.height()
    assert dialog.width() >= minimum.width()
    # And the results box — the one scroll surface — is what yields instead.
    assert dialog._results_label.minimumHeight() < minimum.height()


def test_the_dialog_has_exactly_one_scroll_surface(qapp: QApplication) -> None:
    """Never nest a scroll surface (`architecture.md` §3.9).

    `_results_label` is a `QPlainTextEdit`, i.e. already a scroll area. Fixing the
    clipping by wrapping the dialog in a `QScrollArea` — the rip pane's fix — would
    nest them, and a nested scroll area with nothing left to scroll swallows the
    wheel rather than passing it up. That is the v0.5.15 bug; this guard stops it
    being reintroduced here by someone reaching for the familiar fix.
    """
    from PySide6.QtWidgets import QAbstractScrollArea

    # Bind the dialog to a local: an inline temporary is collected mid-test and the
    # findChildren below then raises on a deleted C++ object.
    dialog = DriveSetupDialog(_CacheOnlyBackend(), "/dev/sr0")
    dialog.show()

    surfaces: list[QAbstractScrollArea] = list(dialog.findChildren(QAbstractScrollArea))
    if isinstance(dialog, QAbstractScrollArea):
        surfaces.append(dialog)
    assert surfaces, "found no scroll areas at all — this check would pass vacuously"
    nested = [
        f"{type(inner).__name__} inside {type(outer).__name__}"
        for outer in surfaces
        for inner in outer.findChildren(QAbstractScrollArea)
        if inner is not outer and inner in surfaces
    ]
    assert not nested, f"nested scroll surfaces: {nested}"
    # And exactly one, so a future "just add a QScrollArea" cannot slip in unnoticed.
    assert len(surfaces) == 1, (
        f"expected one scroll surface (the results box); found {len(surfaces)}: "
        f"{[type(s).__name__ for s in surfaces]}"
    )
