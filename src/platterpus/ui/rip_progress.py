"""Rip progress widget — live status pane + the rip's verdict.

Three bands, top to bottom:

  **header** (fixed, never scrolls, never hidden)
      the ONE progress bar ("Track 5 of 14 — 31% of the rip") · status line ·
      stall notice · the verdict banner (the bold, colour-coded at-a-glance
      trust headline) · the reconciled verdict line (which of AccurateRip and
      CTDB decides, and why) · the read-effort and re-rip-comparison warnings
  **body** (a QTabWidget — exactly one scroll surface visible at a time)
      "Details"  the CTDB verdict, the CTDB repair, and album loudness — marked
                 with a ⚠ in the tab label when it holds a caveat, so nothing
                 hides behind an unopened tab
      "Live log" the ripper's own output, a read-only console
  **footer** (fixed)
      View log · View report · View cue · Open rip folder

*Why tabs rather than one column:* stacking all of it vertically caused two
shipped bugs in successive releases — text painted over text when the window was
short (a QVBoxLayout overflows rather than clipping), and then, once that was
fixed with a scroll area, two nested scrollbars 15 px apart. A nested scroll
surface that has nothing left to scroll does not even pass the wheel on to its
parent, so the pane must never contain one. The band structure is what
guarantees that. The full reasoning and the measurements are in ``__init__``.

The "View log" / "View report" buttons open the file in an in-app read-only
viewer (avoiding the "Open With" chooser a .log/.platterpus.json triggers on a
fresh KDE); "Open rip folder" defers to the file manager via
QDesktopServices.openUrl().

**The per-track results are not here any more** (UX review of 0.7.127, M2; TASKS
R179). This pane had its own results table in a "Tracks" tab, listing the same
tracks as the editable track table above it with different status words, and a
second, unlabelled progress bar. The window now has one track table, which gains
a Verified column after a rip: this pane computes its cells
(``ui/track_results.py``) and hands them over with :attr:`RipProgress.track_results_changed`,
so the verdict banner, the reconciled line and the table are rendered from the
same inputs at the same moments.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QEvent, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from platterpus import album_loudness
from platterpus.build_info import self_invocation
from platterpus.ctdb.track_wording import per_track_sentence
from platterpus.ctdb.verify import (
    CtdbVerifyResult,
    Verdict,
    minority_match_sentence,
    shifted_pressing_phrase,
)
from platterpus.data_tracks import is_data_track
from platterpus.finish_wording import next_step_sentence
from platterpus.parsers.rip_log import RipLog, tracks_needing_heavy_reread
from platterpus.reconciled_verdict import reconcile_verdict, repaired_tracks
from platterpus.track_proof import contradicted_tracks_sentence
from platterpus.ui.accessibility import announce
from platterpus.ui.external_open import open_path_externally
from platterpus.ui.plain_text import plain_tooltip
from platterpus.ui.status_colours import (
    PALETTE_EVENTS,
    SECONDARY_STYLE,
    apply_status_style,
    reapply_status_styles,
)

# Re-exported so existing imports (and tests) can keep doing
# `from platterpus.ui.rip_progress import accuraterip_verdict`; the canonical
# home is the pure platterpus.verdict module.
from platterpus.ui.track_results import TrackResultCells, result_cells
from platterpus.verdict import (
    accuraterip_contradictions,
    accuraterip_rejected_count,
    accuraterip_verdict,
    apply_downgrades,
)

#: The verdict banner's accessible name, and the one it carries while it shows a
#: failed rip instead (`show_failure`), so a screen reader names what it is.
_VERDICT_ACCESSIBLE_NAME: str = "AccurateRip verification verdict"
_FAILURE_ACCESSIBLE_NAME: str = "Rip failure"

__all__ = [
    "RipProgress",
    "accuraterip_verdict",
    "comparison_banner_text",
    "loudness_summary_line",
    "read_effort_summary_line",
    "status_phase_key",
]

log = logging.getLogger(__name__)

# Tab order in the pane's body. Named rather than inlined because three separate
# methods switch between them and an off-by-one here would silently show the
# wrong tab at the end of a rip.
_TAB_DETAILS: int = 0
_TAB_LOG: int = 1

# Base labels for the tabs. `_refresh_details_tab_marker` prepends a warning
# glyph to the Details label when that tab is holding a caveat, so a user who
# never opens it can still SEE that there is something in there — the tab must
# not become a place where warnings go to hide (docs/ux-design-principles.md:
# status is conveyed by symbol + text, never by absence).
_TAB_LABEL_DETAILS: str = "&Details"
_TAB_LABEL_LOG: str = "Live &log"


#: What the Details tab says before a rip has given it anything: during a rip
#: it is the tab on show (UX review M3: the raw console is not the default), so
#: it says where the live work is instead of being a blank page.
DETAILS_PLACEHOLDER: str = (
    "ⓘ While a rip runs, the track list above follows it row by row. When it "
    "finishes, this tab holds the CTDB check, any CTDB repair and the album "
    "loudness. The ripper's own output is in the Live log tab."
)

#: The one progress bar's text before any track has started (the disc scan) and
#: when no rip is running: the percentage of the whole rip, said as such.
_BAR_FORMAT_IDLE: str = "%p% of the rip"

# Hook so tests can intercept the "open file" action without launching
# a real text editor.
_OpenUrlFn = Callable[[QUrl], bool]
# Hook so tests can intercept the in-app file view without spinning a dialog.
_ViewFileFn = Callable[[Path, str], None]


def _is_readable(path: Path) -> bool:
    """Is there a file at ``path`` we could actually show? Never raises.

    Used to choose between the backend's own ``.log`` and the real-time app log
    at *click* time. An OSError here (a dead network mount, a permissions quirk)
    means "can't show it", same as a missing file — a predicate that guards a
    fallback must not itself be the thing that fails.
    """
    try:
        return path.is_file()
    except OSError:  # a stat can fail on a stale mount, not just on absence
        return False


def _bar_value(percent: float) -> int:
    """A percentage as a safe 0-100 int for a QProgressBar. Never raises.

    Pure and module-level so it is directly testable. A non-finite value becomes
    0 rather than an exception, because the alternative is a crash dialog over a
    progress bar; a value outside 0-100 is clamped rather than dropped, since a
    ripper reporting 101% still means "essentially done".
    """
    if not math.isfinite(percent):
        log.warning(
            "progress value %r is not a finite number — showing 0 rather than "
            "raising on the GUI thread",
            percent,
        )
        return 0
    return max(0, min(100, int(percent)))


class RipProgress(QWidget):
    """Live progress + log + the rip's verdict."""

    #: The per-track cells the track table shows after a rip, recomputed and
    #: emitted whenever one of their inputs lands (the rip log, CTDB's answer,
    #: the repair) and emitted EMPTY when the pane is cleared for a new rip. The
    #: window connects it to ``TrackTable.set_results`` on the GUI thread, so the
    #: table always shows what this pane's verdict was rendered from.
    track_results_changed = Signal(object)  # dict[int, TrackResultCells]

    def __init__(
        self,
        parent: QWidget | None = None,
        open_url: _OpenUrlFn | None = None,
        view_file: _ViewFileFn | None = None,
    ) -> None:
        super().__init__(parent)
        # Inject the openUrl function so tests can verify the action
        # without launching a real viewer.
        self._open_url: _OpenUrlFn = open_url or QDesktopServices.openUrl
        # The log / JSON report open in an in-app read-only viewer (IMP-1) — a
        # .log/.platterpus.json has no default handler on a fresh KDE, so
        # openUrl would pop the "Open With" chooser. Injected for tests.
        self._view_file: _ViewFileFn = view_file or self._default_view_file
        # Wall-clock source for the status-line timestamp (maintainer's ask:
        # "if you have a status, put a timestamp in too"). Injectable so tests
        # get a fixed clock instead of the moving wall clock.
        self._now: Callable[[], datetime] = datetime.now
        self._log_path: Path | None = None
        # The real-time app log (``log.txt``), set at rip START by begin_rip so
        # "View log" works *during* the rip — even if the drive freezes before
        # the backend writes its own ``.log``. set_log_path supersedes it at
        # finish with the backend's richer per-track log.
        self._live_log_path: Path | None = None
        # The in-progress album folder set by begin_rip (the output directory) —
        # the fallback the Open-folder button reverts to if the rip finishes
        # WITHOUT a backend .log (cancel / freeze), so it stays reachable. Kept
        # separate from `_rip_dir` (which set_log_path repoints to the exact
        # album folder on a successful finish) so a None finish reverts to the
        # in-progress folder, not to a previous rip's.
        self._inprogress_rip_dir: Path | None = None
        # The JSON report and the album folder, derived from the log path when a
        # rip finishes (set in set_log_path) — back the "View report" / "Open
        # rip folder" buttons.
        self._report_path: Path | None = None
        self._rip_dir: Path | None = None
        # cyanrip's own ``.cue`` sheet, written beside the ``.log`` (same stem).
        # Backs the "View cue" button — enabled only when the file is actually
        # present, since (unlike the JSON report we write ourselves right after)
        # the cue is produced by cyanrip during the rip and a given rip may not
        # have one.
        self._cue_path: Path | None = None
        # This rip's single-file report bundle (`evidence_bundle.py`). Written
        # off-thread after the rip ends — for EVERY outcome, including cancel and
        # failure — and reported back here by a queued signal, so it is None
        # until then and None again if the bundle could not be built.
        self._bundle_path: Path | None = None
        # The last parsed rip log, kept so the CTDB handler (which finishes later,
        # asynchronously) can reconcile its verdict against AccurateRip.
        self._last_rip_log: RipLog | None = None
        # The last CTDB result's per-track rows, kept so the results table and
        # the note under the status line can say where CTDB disagrees about a
        # track AccurateRip does not contradict (`ctdb_disagreement`), whichever
        # of the rip log and the CTDB answer arrives last.
        self._ctdb_tracks: tuple[object, ...] = ()
        # The last CTDB result and the automatic repair's result, kept for the
        # reconciled verdict line, which needs all three inputs (the rip log,
        # CTDB's answer and the repair) whichever arrives last.
        self._ctdb_result: object | None = None
        self._repair_result: object | None = None
        # The per-track cells last handed to the track table, kept so a reader
        # (a test, a script verb) can see what the table was given.
        self._track_results: dict[int, TrackResultCells] = {}
        # The tracks this rip covers, in order, and the one being read now, for
        # the one bar's "Track 5 of 14" (`set_current_track`).
        self._rip_tracks: tuple[int, ...] = ()
        self._current_track: int | None = None
        # Screen-reader announcement throttles (gap #4, focus-safe live updates).
        # The status line redraws many times a second (percent + ETA), so we
        # announce only when its *phase* changes (see status_phase_key); the CTDB
        # line is deduped on its full text (an in-progress ping then a verdict).
        self._announced_status_key: str = ""
        self._announced_ctdb_text: str = ""
        self._announced_stall_text: str = ""
        # The last status text WITHOUT the timestamp prefix, so the desktop
        # notification can send whatever the window is actually showing.
        self._last_status_text: str = ""
        # Post-rip checks that contradict the verdict banner (see
        # `downgrade_verdict`). Kept alongside the banner's original wording so
        # each downgrade appends rather than overwrites.
        self._verdict_base_message: str = ""
        self._verdict_downgrades: list[str] = []
        # The tracks the verdict says AccurateRip contradicts, by number, when
        # some (not all) of the rip's audio tracks are contradicted: the banner
        # then ends with one plain next step naming them (UX review V1). Empty
        # when there is no such step to give.
        self._verdict_attention: tuple[object, ...] = ()
        # The level the banner was last drawn with (before any failure turns it
        # to "error"), so the banner can be drawn again when a repair lands.
        self._verdict_render_level: str = ""
        # The level the banner shows now ("ok", "warn", "neutral", "error"), or
        # None while it is hidden. Read by the window for the status line's
        # lead (`verdict_level`), so the two cannot carry different marks.
        self._verdict_level: str | None = None
        # A failed rip's sentence (`show_failure`), shown at the error level in
        # place of a verdict, and the log the Open log button opens. Empty and
        # None while the rip has not failed.
        self._verdict_failure: str = ""
        self._failure_log_path: Path | None = None
        # A cancelled rip's folder (`offer_cancelled_folder`), which the Open
        # folder button beside the banner opens. None until a rip is cancelled.
        self._cancelled_folder: Path | None = None

        # --- Why this pane is built in three bands ---------------------------
        # This pane has to show five different things: live progress, a live
        # console, a trust verdict, per-track results, and three explanatory
        # paragraphs. That is more than fits in a small window, and the two
        # releases before this one were both consequences of trying to stack it
        # all in one column:
        #
        #   v0.5.15 — a QVBoxLayout given less height than its children's
        #   minimums does NOT clip and does NOT scroll: it **overflows, and the
        #   children's rectangles collide**, painting text over text. Measured at
        #   940 px wide: the pane claimed a 326 px minimum height while
        #   allocating ~405 px, because a word-wrapped QLabel's minimumSizeHint
        #   is one line while its heightForWidth is two or three. Fixed by
        #   wrapping everything in one QScrollArea.
        #
        #   …which introduced the problem this layout solves. The table and the
        #   console are themselves scrollable, so inside that outer scroll area
        #   they became **nested** scroll surfaces: two vertical scrollbars 15 px
        #   apart (measured at x=911 and x=926 on a 940x400 pane), and the wheel
        #   acting on whichever happened to be under the pointer. The maintainer's
        #   report was exact: "difficult to use together".
        #
        # The trap that rules out the obvious repair: **a nested scroll area that
        # has nothing left to scroll does not pass the wheel on to its parent**
        # (measured — an exhausted inner QScrollArea left the outer one at 0). So
        # merely turning the table's own scrollbar off trades a visible scrollbar
        # for a *dead wheel zone* over the biggest widget in the pane, which feels
        # more broken, not less.
        #
        # Hence: never nest a scroll surface inside another one. The pane is three
        # bands —
        #
        #   header  (fixed)  progress bars, the status line, the verdict headline
        #                    — what you glance at; never scrolled, never hidden
        #   tabs             one scroll surface per tab, and only one tab visible,
        #                    so there is never more than one scrollbar and never a
        #                    nested one
        #   footer  (fixed)  the four output buttons
        #
        # Measured against the same probes: at most ONE live scrollbar at every
        # size from 1900x980 down to 940x240, zero nested scroll areas, and zero
        # overlapping siblings — so the v0.5.15 fix is preserved rather than
        # traded away. See docs/architecture.md §3.9 and docs/testing.md §5.v.
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # --- The ONE progress bar (whole rip) ---
        # A start-to-finish bar so the user can gauge how much of the disc is
        # left, labelled IN the bar with the track it is on: "Track 5 of 14 —
        # 31% of the rip" (`_refresh_bar_format`). There used to be a second,
        # unlabelled bar under the status line for the current operation's own
        # 0-100%, and an "Overall" caption beside this one: two bars, one of them
        # unexplained (UX review of 0.7.127, M2). The status line already says
        # the current operation and its percentage ("Ripping track 5 of 14…
        # 62%"), so the second bar repeated it without saying what it was.
        self._overall_bar: QProgressBar = QProgressBar(self)
        self._overall_bar.setRange(0, 100)
        self._overall_bar.setValue(0)
        self._overall_bar.setTextVisible(True)
        self._overall_bar.setFormat(_BAR_FORMAT_IDLE)
        root.addWidget(self._overall_bar)

        # --- Status line ---
        # Names the current operation and its own percentage, and at the end of
        # a rip carries the finished line.
        self._status_label: QLabel = QLabel("Idle.", self)
        # PlainText, like every label in this pane that is given a value later:
        # this one shows cyanrip's own fatal sentence, and Qt's default AutoText
        # would read a `<` in it as markup and could drop the rest of the line
        # (CLAUDE.md Critical rule #12).
        self._status_label.setTextFormat(Qt.TextFormat.PlainText)
        # Word-wrapped, like every other label in this pane — and this one is the
        # reason the rule matters. An un-wrapped QLabel's minimum width is the
        # width of its whole single line, and that minimum propagates up: a real
        # end-of-rip status ("… Done — all 14 tracks ripped cleanly, no read
        # errors. AccurateRip: 13/14 verified. 1 track partially accurate
        # (offset-variant match).") demanded **906 px**, against 366 px for the
        # idle text. So the entire results pane refused to be narrower than the
        # longest status it had ever shown. Maximised it looked right; make the
        # window smaller and the layout could not comply, so the contents
        # overflowed their viewport and the CTDB and loudness lines were drawn
        # over the AccurateRip table (real-hardware report, 2026-07-28).
        #
        # Wrapping trades width for height, which is the correct trade for a
        # sentence: it costs a second line on a narrow window instead of making
        # the whole pane unusable there. `tests/test_ui_rip_progress.py` pins the
        # pane's minimum width against the longest status we can produce.
        self._status_label.setWordWrap(True)
        # SELECTABLE. This is the only place in the app where cyanrip's own fatal
        # sentence is ever displayed, and it could not be selected with a mouse or
        # read by a keyboard user — so the single most useful line for a bug report
        # was the one line that could not be copied out of the window.
        # `main_window_drive.py` already does this for its diagnosis box; this label
        # was written without it.
        self._status_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        root.addWidget(self._status_label)

        # --- Stall notice (GUI-side liveness watchdog) ---
        # The rip worker streams cyanrip's output; when the drive wedges (e.g.
        # an unsupported lead-out overread on the last track), cyanrip blocks in
        # a read syscall and emits NOTHING, so the worker's own progress-based
        # stall detector can't fire and the bars just sit there. The main window
        # runs a timer that watches wall-clock time since the last worker signal
        # and calls set_stall_notice() when it crosses the threshold — this
        # banner is how "it might be frozen" becomes visible instead of a silent
        # hang. Hidden whenever the rip is making progress.
        self._stall_label: QLabel = QLabel("", self)
        self._stall_label.setTextFormat(Qt.TextFormat.PlainText)
        self._stall_label.setWordWrap(True)
        self._stall_label.setVisible(False)
        apply_status_style(self._stall_label, "warn")
        root.addWidget(self._stall_label)

        # --- Verification verdict banner (at-a-glance trust) ---
        # A single bold, colour-coded headline above the per-track table so the
        # user sees "is this rip trustworthy?" without reading every row. Green
        # = every audio track matched AccurateRip (bit-perfect, community-
        # verifiable); amber = a partial match worth a look; grey = nothing to
        # assert yet (e.g. a disc not in the database). Populated from the
        # parsed log by set_rip_log; hidden until then. The wording NEVER over-
        # claims — it mirrors what AccurateRip actually returned.
        self._verdict_banner: QLabel = QLabel("", self)
        # PlainText: the bold comes from the style sheet, not from markup, and the
        # downgrade reasons appended to it can quote a tool's message.
        self._verdict_banner.setTextFormat(Qt.TextFormat.PlainText)
        self._verdict_banner.setWordWrap(True)
        self._verdict_banner.setVisible(False)
        # The banner shares its row with **Open log**, shown only while the
        # banner reports a failed rip (UX review E1): the fallback sentence names
        # the log's path, and a path the user must copy by hand is a dead end.
        # Opening it goes through `open_path_externally` (QDesktopServices,
        # which hands the file to the desktop and returns at once, so the GUI
        # thread never waits; when nothing on the system opens a .log, the user
        # is shown the path instead of a button that does nothing).
        self._open_failure_log_button: QPushButton = QPushButton("Open &log", self)
        self._open_failure_log_button.setVisible(False)
        self._open_failure_log_button.setAccessibleName(
            "Open the app log, which records why the rip failed"
        )
        self._open_failure_log_button.clicked.connect(self._on_open_failure_log)
        # **Open folder**, shown only after a CANCELLED rip (UX review E2): the
        # status line says where the finished tracks and any partial files are,
        # and this opens that folder, through the same fire-and-forget
        # `open_path_externally`. Alt+N: the footer's "Open rip fol&der" holds D.
        # Deliberately no "Delete partial files" beside it: deleting a user's
        # files needs its own design and the owner's eyes (R182, wave 1).
        self._open_cancelled_folder_button: QPushButton = QPushButton(
            "Ope&n folder", self
        )
        self._open_cancelled_folder_button.setVisible(False)
        self._open_cancelled_folder_button.setAccessibleName(
            "Open the folder that holds the cancelled rip's files"
        )
        self._open_cancelled_folder_button.clicked.connect(
            self._on_open_cancelled_folder
        )
        verdict_row = QHBoxLayout()
        verdict_row.addWidget(self._verdict_banner, stretch=1)
        verdict_row.addWidget(
            self._open_failure_log_button, alignment=Qt.AlignmentFlag.AlignTop
        )
        verdict_row.addWidget(
            self._open_cancelled_folder_button, alignment=Qt.AlignmentFlag.AlignTop
        )
        root.addLayout(verdict_row)

        # --- The reconciled verdict: which source decides, and why ------------
        # ONE line under the banner that reconciles AccurateRip and CTDB (UX
        # review of 0.7.127, V2 and A3; TASKS R181). Before it, CTDB's "verified
        # ✓" sat in the Details tab and AccurateRip's "WRONG" in the banner, both
        # amber, and nothing said which to believe. The sentence comes from
        # `reconciled_verdict.reconcile_verdict` and always names the source that
        # decides; it carries the CTDB per-track note of 0.7.119 ("CTDB disagrees
        # on track 2 (differs); AccurateRip is the verdict") word for word, which
        # used to be its own line under the status line. It leads with ✓, ⚠ or ⓘ,
        # so its colour is never the only signal. Hidden until CTDB answers: with
        # no CTDB answer, the banner is the whole verdict.
        self._reconciled_label: QLabel = QLabel("", self)
        self._reconciled_label.setTextFormat(Qt.TextFormat.PlainText)
        self._reconciled_label.setWordWrap(True)
        self._reconciled_label.setVisible(False)
        root.addWidget(self._reconciled_label)

        # --- Read-effort early warning (per-track "hard to read") ---
        # Amber footnote naming tracks that needed unusually heavy re-reading (or
        # a -Z that never converged) even if they matched AccurateRip — the
        # earliest hint a track may not be reproducible. Hidden on a clean rip.
        self._read_effort_label: QLabel = QLabel("", self)
        self._read_effort_label.setTextFormat(Qt.TextFormat.PlainText)
        self._read_effort_label.setWordWrap(True)
        self._read_effort_label.setVisible(False)
        apply_status_style(self._read_effort_label, "warn")
        root.addWidget(self._read_effort_label)

        # --- Re-rip comparison banner ("you've ripped this disc before") ---
        # When a prior rip of the SAME disc is found in the library, a one-liner
        # here says how this rip compares — how many tracks are byte-identical,
        # which differ, and which rip is the better master. Populated off-thread
        # after the rip (set_comparison); hidden when there's no prior rip.
        self._comparison_label: QLabel = QLabel("", self)
        self._comparison_label.setTextFormat(Qt.TextFormat.PlainText)
        self._comparison_label.setWordWrap(True)
        self._comparison_label.setVisible(False)
        root.addWidget(self._comparison_label)

        # --- The tabbed body: one scroll surface per tab, never nested --------
        # Everything below the headline goes into tabs. The point is not
        # tidiness, it is that **only one tab is visible at a time**, so the pane
        # can never show two scrollbars and can never nest one inside another
        # (see the band comment at the top of __init__ for the measurements).
        #
        # Two tabs since the per-track results moved into the one track table
        # (UX review M2): the supporting explanations, then the live console.
        # Details is the default, during a rip too: the review's M3 found the raw
        # console ("Ripping and encoding track 4, progress - 100.00%") was what a
        # rip opened on, while the track list above already follows the rip row
        # by row. The console stays one click away.
        self._tabs: QTabWidget = QTabWidget(self)
        # Document mode: this is an interior grouping, not a top-level notebook,
        # so the heavier framed-tab look would read as a separate window.
        self._tabs.setDocumentMode(True)
        root.addWidget(self._tabs, stretch=1)

        # --- The "Details" tab: the supporting explanations -------------------
        # The three explanatory paragraphs are the *evidence* behind the headline
        # rather than the headline itself, so they live one tab away — but they are
        # long, wrap to several lines each, and are exactly what overflowed the
        # pane in the first place. So this tab is a scroll area: it is the one
        # place a variable-length block of prose can grow without pushing anything
        # else off the layout, and because only one tab is visible its scrollbar
        # is never a second one.
        self._details_area: QScrollArea = QScrollArea(self._tabs)
        # Resizable so the content's *width* tracks the viewport — that is what
        # makes the wrapped labels re-flow instead of demanding a horizontal
        # scrollbar. Height is free to exceed the viewport; that is the point.
        self._details_area.setWidgetResizable(True)
        self._details_area.setFrameShape(QFrame.Shape.NoFrame)
        details_content = QWidget(self._details_area)
        self._details_area.setWidget(details_content)
        details = QVBoxLayout(details_content)
        details.setContentsMargins(4, 4, 4, 4)
        self._tabs.addTab(self._details_area, _TAB_LABEL_DETAILS)

        # --- The Details tab's empty state ---
        # Shown while none of the lines below has anything, so the default tab
        # is never a blank page (see DETAILS_PLACEHOLDER).
        self._details_placeholder: QLabel = QLabel(DETAILS_PLACEHOLDER, self)
        self._details_placeholder.setTextFormat(Qt.TextFormat.PlainText)
        self._details_placeholder.setWordWrap(True)
        self._details_placeholder.setStyleSheet(SECONDARY_STYLE)
        details.addWidget(self._details_placeholder)

        # --- CTDB verdict line (second, TOC-keyed verification path) ---
        # A one-liner that only appears when a CTDB verify ran (it's an opt-in,
        # post-rip network check). The audio-CRC algorithm is now
        # hardware-validated (KDD-16, crc.CRC_VALIDATED True), so a match renders
        # green "verified"; the "experimental" wording remains only as a defensive
        # fallback should the gate ever be re-opened (set_ctdb_result reads the
        # flag live).
        self._ctdb_label: QLabel = QLabel("", self)
        self._ctdb_label.setTextFormat(Qt.TextFormat.PlainText)
        self._ctdb_label.setWordWrap(True)
        self._ctdb_label.setVisible(False)
        details.addWidget(self._ctdb_label)

        # (The CTDB ↔ AccurateRip reconciliation that sat here, explaining why a
        # CTDB "no match" and an AccurateRip "mostly accurate" are one finding,
        # is now part of the reconciled verdict line in the header, which every
        # user sees without opening this tab: UX review V2.)

        # --- The automatic CTDB repair (KDD-47, amended 2026-11-05: no button) ---
        # What the repair did, or why it did not, in plain words and with its
        # marker (`ctdb/repair_wording.py`). Its own line, under the CTDB verdict:
        # the verdict above stays the READ's, and this says what happened after it.
        # PlainText, because the reason can quote a tool (`flac`, `metaflac`).
        self._ctdb_repair_label: QLabel = QLabel("", self)
        self._ctdb_repair_label.setTextFormat(Qt.TextFormat.PlainText)
        self._ctdb_repair_label.setWordWrap(True)
        self._ctdb_repair_label.setVisible(False)
        details.addWidget(self._ctdb_repair_label)

        # --- Album loudness + partial-accurate footnote ---
        # A neutral one-liner surfacing two facts cyanrip already computed and
        # that we were only writing to the JSON: the album loudness (integrated
        # LUFS / range / true peak) and on how many tracks only one frame
        # matched AccurateRip ("partially accurate"). Populated from the parsed log by
        # set_rip_log; hidden when there's nothing to show (e.g. a legacy-format log
        # carries no loudness and the disc had no partial matches).
        self._loudness_label: QLabel = QLabel("", self)
        self._loudness_label.setTextFormat(Qt.TextFormat.PlainText)
        self._loudness_label.setWordWrap(True)
        self._loudness_label.setVisible(False)
        self._loudness_label.setStyleSheet(SECONDARY_STYLE)
        details.addWidget(self._loudness_label)
        # Soak up the leftover height so the paragraphs sit at the top of the tab
        # instead of being spread down it.
        details.addStretch(1)

        # --- The "Live log" tab: the rip tool's own output ---------------------
        # A console, and treated as one: it keeps its own scrollbar because that
        # is what a console is, and as the whole content of its tab that
        # scrollbar is unambiguous — the wheel over it can only mean "scroll the
        # log".
        self._log_view: QPlainTextEdit = QPlainTextEdit(self)
        self._log_view.setReadOnly(True)
        # Cap the scrollback so a long rip doesn't blow up memory; the ripper
        # emits thousands of lines per rip.
        self._log_view.setMaximumBlockCount(10_000)
        # A small minimum so the splitter can shrink this pane and free up drag
        # slack at the default window size (the 0.4.4 resize report); the log
        # scrolls, so 64 px is fine.
        self._log_view.setMinimumHeight(64)
        self._tabs.addTab(self._log_view, _TAB_LABEL_LOG)

        # FOLLOW THE TAIL, and do it explicitly rather than relying on Qt.
        #
        # Real-user report (2026-08-06): the status line read *"Re-ripping track 5
        # to secure it… 97%"* while this pane's visible lines said *"Ripping and
        # encoding track 12, progress - 7.22%"* — and the maintainer reasonably
        # asked which one to believe. The artifact settles it: the album pass left
        # track 12 at 19:04:09 and the securing re-rip of track 5 ran 19:13→19:33,
        # so the status was current and **the pane was showing the past**.
        #
        # Measured cause, not inferred: `appendPlainText` only auto-scrolls a
        # widget Qt is actually laying out. With this view sitting in a
        # NON-CURRENT tab — which is where it sits for most of a rip, because the
        # user is watching the track grid — 3000 appends leave the scrollbar at
        # `value=0` against `maximum=2999`. The content is all there; the viewport
        # never moved. Switching to the tab then lands wherever Qt's deferred
        # layout puts it, which is why the symptom looks arbitrary.
        #
        # So: track whether the user is "following", and pin the view ourselves —
        # on every append, and again whenever the tab becomes visible. Scrolling
        # up deliberately still pauses the follow (it is a console; reading back
        # is the point) and scrolling to the bottom resumes it.
        self._log_follow: bool = True
        self._log_view.verticalScrollBar().valueChanged.connect(self._on_log_scrolled)
        self._tabs.currentChanged.connect(self._on_tab_changed)

        # --- Post-rip output buttons ---
        # Three complementary outputs land beside the FLACs every rip (the
        # "two outputs every time" principle, docs/ux-design-principles #2):
        # cyanrip's human-readable .log, our machine-readable .platterpus.json
        # report, and the album folder that holds both (+ the FLACs/.cue). All
        # three buttons stay disabled until a rip finishes and a log path is
        # known (set_log_path), then enable together.
        button_row = QHBoxLayout()
        button_row.addStretch(1)
        # "&" marks each button's Alt+<letter> mnemonic (keyboard reachability,
        # gap #4) — letters chosen to stay unique within the main window
        # (menus hold F/T/H; the drive row and rip controls hold theirs).
        self._view_log_button: QPushButton = QPushButton("&View log", self)
        self._view_log_button.setEnabled(False)
        self._view_log_button.clicked.connect(self._on_view_log_clicked)
        button_row.addWidget(self._view_log_button)
        self._view_report_button: QPushButton = QPushButton("View re&port", self)
        self._view_report_button.setEnabled(False)
        self._view_report_button.clicked.connect(self._on_view_report_clicked)
        button_row.addWidget(self._view_report_button)
        # cyanrip's .cue sheet — the disc's track/index map, the same artifact we
        # surface the .log for. Enabled only when a cue is actually present.
        self._view_cue_button: QPushButton = QPushButton("View c&ue", self)
        self._view_cue_button.setEnabled(False)
        self._view_cue_button.clicked.connect(self._on_view_cue_clicked)
        button_row.addWidget(self._view_cue_button)
        self._open_folder_button: QPushButton = QPushButton("Open rip fol&der", self)
        self._open_folder_button.setEnabled(False)
        self._open_folder_button.clicked.connect(self._on_open_folder_clicked)
        button_row.addWidget(self._open_folder_button)
        # The one file to send. Every rip — success, partial, cancelled, failed —
        # writes a single .tar.gz of the text artifacts (`evidence_bundle.py`),
        # and this reveals it. Without a button the feature is a log line, and
        # the manual step it exists to remove is "find the files" (maintainer,
        # 2026-08-19: *"so i only need to upload 1 file here"*).
        # `&b`, not `&t` — `t` is the Tools menu's mnemonic, and an ambiguous
        # mnemonic only cycles focus instead of activating, which defeats the
        # point (gap #4). The first version of this button took `t` and the
        # accessibility sweep caught it; `b` was free.
        self._bundle_button: QPushButton = QPushButton("Report &bundle", self)
        self._bundle_button.setEnabled(False)
        self._bundle_button.clicked.connect(self._on_bundle_clicked)
        button_row.addWidget(self._bundle_button)
        root.addLayout(button_row)

        # --- Accessibility (docs/ux-design-principles.md #10) ---
        # Screen readers announce a widget by its accessible name; without one a
        # bare QProgressBar/QLabel/QTableWidget reads as just its value or
        # "label". Name every status surface so the rip is followable without
        # sight, and so the colour-coded verdict is never the *only* signal.
        self._overall_bar.setAccessibleName("Overall rip progress")
        self._status_label.setAccessibleName("Rip status")
        self._log_view.setAccessibleName("Rip log output")
        self._verdict_banner.setAccessibleName(_VERDICT_ACCESSIBLE_NAME)
        self._read_effort_label.setAccessibleName("Read-effort warning")
        self._stall_label.setAccessibleName("Rip stall warning")
        self._reconciled_label.setAccessibleName(
            "Which check decides the verdict, AccurateRip or CTDB, and why"
        )
        self._comparison_label.setAccessibleName("Re-rip comparison")
        self._ctdb_label.setAccessibleName("CTDB verification result")
        self._ctdb_repair_label.setAccessibleName("CTDB repair result")
        self._loudness_label.setAccessibleName(
            "Album loudness and partial-match summary"
        )
        self._view_log_button.setAccessibleName("Open the rip log file")
        self._view_report_button.setAccessibleName(
            "Open the machine-readable rip report (JSON)"
        )
        self._view_cue_button.setAccessibleName("Open the disc's cue sheet")
        self._open_folder_button.setAccessibleName("Open the folder containing the rip")
        self._bundle_button.setAccessibleName(
            "Open the folder holding this rip's single-file report bundle"
        )
        # The tab strip is now the way to reach two thirds of this pane, so it has
        # to be as reachable as the buttons: each tab carries an Alt+<letter>
        # mnemonic (in its label), the strip is in the tab order, and the widget
        # itself is named so a screen reader says what the grouping *is* rather
        # than just "tab bar". Ctrl+Tab / arrow keys move between tabs for free.
        self._tabs.setAccessibleName("Rip details and live log")
        self._tabs.setTabToolTip(
            _TAB_DETAILS,
            "CTDB verification, the CTDB repair, and album loudness",
        )
        self._tabs.setTabToolTip(_TAB_LOG, "Live output from the ripper")

    def event(self, event: QEvent) -> bool:
        """Keep the pane's minimum height honest whenever its contents change.

        A label's new text, a line shown or hidden, or a new width all reach this
        widget as a ``LayoutRequest`` or a ``Resize``, and each can change how
        tall the header must be. See :meth:`_fit_minimum_height` for why.
        """
        handled = super().event(event)
        if event.type() in (QEvent.Type.LayoutRequest, QEvent.Type.Resize):
            self._fit_minimum_height()
        return handled

    def _fit_minimum_height(self) -> None:
        """Set the minimum height to what the header needs at the current width.

        THE v0.5.15 TRAP, met again by this pane's own redesign (R179): a
        QVBoxLayout given less height than its word-wrapped labels need does not
        clip and does not scroll; it overflows, and the labels are drawn over the
        tabs. A wrapped label's minimum size is ONE line, so the pane's minimum
        said it fit in a height it did not. With the results table gone the
        splitter gives this pane less room than before, and the verdict banner,
        the reconciled line and the finished status line together run to six or
        seven lines on a 1000 px window: measured, the reconciled line's last
        line was drawn under the tab strip.

        So the minimum is computed from the height each visible header item needs
        AT THIS WIDTH (``heightForWidth``), plus the tabs' and the footer's own
        minimums. The splitter honours a child's minimum, so a long verdict now
        takes its room from the track list above instead of drawing over the
        tabs; the track list has its own floor. Cheap (a dozen items) and set
        only when it changes.
        """
        layout = self.layout()
        if layout is None:
            return
        width = self.width()
        if width <= 0:
            return
        margins = layout.contentsMargins()
        inner = max(1, width - margins.left() - margins.right())
        needed = margins.top() + margins.bottom()
        shown = 0
        for index in range(layout.count()):
            item = layout.itemAt(index)
            if item is None or item.isEmpty():
                continue
            shown += 1
            if item.widget() is self._tabs:
                needed += self._tabs.minimumSizeHint().height()
            elif item.hasHeightForWidth():
                needed += item.heightForWidth(inner)
            else:
                needed += item.minimumSize().height()
        needed += layout.spacing() * max(0, shown - 1)
        if needed != self.minimumHeight():
            self.setMinimumHeight(needed)

    def changeEvent(self, event: QEvent) -> None:  # noqa: N802 — Qt override
        """Recolour the status lines when the desktop's colours change.

        Qt calls this when the palette or theme changes under the open window
        (Breeze to Breeze Dark in System Settings, say). Each status line's
        colour was chosen for the palette in force when it was set, so the
        light-theme amber stayed on a charcoal background until the app was
        restarted (UX review L1, 2026-11-17). ``reapply_status_styles`` chooses
        each one again for the palette in force now; it touches only labels,
        on the GUI thread this event arrives on.
        """
        if event.type() in PALETTE_EVENTS:
            reapply_status_styles(self)
        super().changeEvent(event)

    # --- Public surface -----------------------------------------------------

    def clear(self) -> None:
        """Reset to the idle state. Called when starting a new rip."""
        self._status_label.setText("Idle.")
        self._overall_bar.setValue(0)
        self._rip_tracks = ()
        self._current_track = None
        self._refresh_bar_format()
        self._log_view.clear()
        self._verdict_banner.clear()
        self._verdict_banner.setVisible(False)
        self._read_effort_label.clear()
        self._read_effort_label.setVisible(False)
        self._comparison_label.clear()
        self._comparison_label.setVisible(False)
        self._ctdb_label.clear()
        self._ctdb_label.setVisible(False)
        self._ctdb_repair_label.clear()
        self._ctdb_repair_label.setVisible(False)
        self._reconciled_label.clear()
        self._reconciled_label.setVisible(False)
        self._ctdb_tracks = ()
        self._ctdb_result = None
        self._repair_result = None
        self._loudness_label.clear()
        self._loudness_label.setVisible(False)
        self._stall_label.clear()
        self._stall_label.setVisible(False)
        self._view_log_button.setEnabled(False)
        self._view_report_button.setEnabled(False)
        self._view_cue_button.setEnabled(False)
        self._open_folder_button.setEnabled(False)
        # The previous rip's bundle must not be reachable from this rip's pane —
        # a stale artifact offered as this one's evidence is worse than none.
        self._bundle_button.setEnabled(False)
        self._bundle_path = None
        self._log_path = None
        self._live_log_path = None
        self._report_path = None
        self._cue_path = None
        self._rip_dir = None
        self._inprogress_rip_dir = None
        self._last_rip_log = None
        # Reset the announcement throttles so the NEXT rip's first phase is
        # announced even if it matches the previous rip's last one. "Idle." is
        # deliberately not announced — clearing the pane isn't news.
        self._announced_status_key = ""
        self._announced_ctdb_text = ""
        self._announced_stall_text = ""
        self._last_status_text = ""
        self._verdict_base_message = ""
        self._verdict_downgrades = []
        self._verdict_attention = ()
        self._verdict_render_level = ""
        self._verdict_level = None
        self._verdict_banner.setToolTip("")
        self._verdict_failure = ""
        self._failure_log_path = None
        self._open_failure_log_button.setVisible(False)
        self._cancelled_folder = None
        self._open_cancelled_folder_button.setVisible(False)
        self._verdict_banner.setAccessibleName(_VERDICT_ACCESSIBLE_NAME)
        # The Details tab is empty again, so drop any warning marker from its
        # label — a stale ⚠ on an empty tab would send the user looking for a
        # caveat that no longer exists.
        self._refresh_details_tab_marker()
        # The track table drops the last rip's Verified column and results.
        self._emit_track_results()

    def _refresh_details_tab_marker(self) -> None:
        """Mark the Details tab when it is holding something the user should see.

        A tab is a good way to keep the pane to one scroll surface and a bad way
        to store warnings: anything behind it is invisible until clicked. So the
        tab label itself carries the signal — a ⚠ appears the moment any caveat
        lands in there, which keeps the "you can see there is a problem without
        opening anything" property the single-column layout had for free.

        Only the *warning* surfaces count. The loudness footnote is neutral
        information and marking the tab for it would train the user to ignore
        the marker, which is the failure mode this is meant to avoid.
        """
        # `isHidden()`, NOT `isVisible()`. A widget in a background tab is not
        # visible even when it is holding text, so `isVisible()` would only ever
        # mark the tab while you were already looking at it — useless. `isHidden()`
        # asks the question we actually mean: "has this label been switched off?".
        # (Same distinction cost 18 px in the table-height formula; it is worth
        # knowing once.)
        has_warning = any(
            not label.isHidden() and bool(label.text())
            for label in (self._ctdb_label, self._ctdb_repair_label)
        )
        # The empty state shows only while nothing else in the tab does.
        self._details_placeholder.setVisible(
            all(
                label.isHidden() or not label.text()
                for label in (
                    self._ctdb_label,
                    self._ctdb_repair_label,
                    self._loudness_label,
                )
            )
        )
        label = f"⚠ {_TAB_LABEL_DETAILS}" if has_warning else _TAB_LABEL_DETAILS
        if self._tabs.tabText(_TAB_DETAILS) != label:
            self._tabs.setTabText(_TAB_DETAILS, label)

    def begin_rip(
        self,
        rip_dir: Path | None,
        live_log: Path | None,
        *,
        tracks: Sequence[int] = (),
    ) -> None:
        """At rip START, make the in-progress rip reachable immediately.

        Enables **Open rip folder** (→ ``rip_dir``, which cyanrip populates as it
        works) and **View log** (→ ``live_log``, the real-time app log) the moment
        the rip begins — so a frozen or cancelled rip is never a dead end (the
        reported "Open rip folder did nothing after I force-cancelled"). At finish
        :meth:`set_log_path` supersedes these with the backend's own richer
        ``.log`` / ``.cue`` / JSON report. Report + cue stay disabled until then
        (they don't exist yet). Call after :meth:`clear`.

        ``tracks`` are the track numbers this rip reads, in order, for the bar's
        "Track 5 of 14" (:meth:`set_current_track`); empty when unknown, and the
        bar then says only the percentage.
        """
        self._rip_tracks = tuple(tracks)
        self._current_track = None
        self._refresh_bar_format()
        self._rip_dir = rip_dir
        self._inprogress_rip_dir = rip_dir
        self._live_log_path = live_log
        self._open_folder_button.setEnabled(rip_dir is not None)
        self._view_log_button.setEnabled(live_log is not None)
        # NOT the live console (UX review M3). The track list above follows the
        # rip row by row, which is what a person watches; the raw console is one
        # click away for whoever wants it. (It used to be switched to here, and
        # the rip opened on "Ripping and encoding track 4, progress - 100.00%".)
        self._tabs.setCurrentIndex(_TAB_DETAILS)

    def set_current_track(self, number: int) -> None:
        """The rip has moved on to track ``number``: say so in the bar.

        Connected to the rip worker's ``current_track`` signal (queued to the GUI
        thread). Only the bar's text changes; its value stays the whole rip's
        percentage (:meth:`set_progress`).
        """
        self._current_track = number
        self._refresh_bar_format()

    def bar_text(self) -> str:
        """The one progress bar's text as shown ("Track 5 of 14 — 31% of the rip")."""
        return self._overall_bar.text()

    def _refresh_bar_format(self) -> None:
        """Label the one bar with the track it is on, and what its percentage is.

        "Track 5 of 14 — %p% of the rip" for a whole-disc rip; for a rip of some
        tracks, "Track 5 (2 of 3) — %p% of the rip", because "Track 5 of 3"
        would be nonsense and the disc's own number is the one in the table. A
        track the rip was not told about (a securing re-read is still one of the
        rip's tracks, so this is only a defensive case) is named alone.
        """
        number = self._current_track
        tracks = self._rip_tracks
        if number is None:
            text = _BAR_FORMAT_IDLE
        elif number in tracks and tracks == tuple(range(1, len(tracks) + 1)):
            text = f"Track {number} of {len(tracks)} — {_BAR_FORMAT_IDLE}"
        elif number in tracks:
            position = tracks.index(number) + 1
            text = f"Track {number} ({position} of {len(tracks)}) — {_BAR_FORMAT_IDLE}"
        else:
            text = f"Track {number} — {_BAR_FORMAT_IDLE}"
        if self._overall_bar.format() != text:
            self._overall_bar.setFormat(text)

    def set_stall_notice(self, text: str | None) -> None:
        """Show (``text``) or hide (``None``) the stall banner.

        Driven by the main window's liveness timer: shown when no worker signal
        has arrived for a while (a likely drive freeze), hidden the instant
        progress resumes. Announced once per distinct message for screen readers
        (gap #4) — not on every timer tick while it's stuck.
        """
        if text:
            self._stall_label.setText(text)
            self._stall_label.setVisible(True)
            if text != self._announced_stall_text:
                self._announced_stall_text = text
                announce(self._stall_label, text)
        else:
            self._stall_label.clear()
            self._stall_label.setVisible(False)
            self._announced_stall_text = ""

    def append_log_line(self, line: str) -> None:
        """Append one line of ripper output to the streaming log view.

        Pins the view to the newest line unless the user has scrolled up. See the
        long note where `_log_follow` is created: Qt does not auto-scroll a widget
        in a non-current tab, which is where this one spends most of a rip, and
        the result was a pane showing output from twenty minutes earlier while the
        status line was current.
        """
        self._log_view.appendPlainText(line)
        if self._log_follow:
            self._scroll_log_to_end()

    def _scroll_log_to_end(self) -> None:
        """Move the log view to its newest line.

        `setValue(maximum())` rather than `ensureCursorVisible()`: the cursor is
        already at the end after `appendPlainText`, and `ensureCursorVisible` is a
        no-op on a widget Qt has not laid out — which is exactly the case this
        exists for. Setting the scrollbar works whether or not the viewport has
        been realised, and re-running it on tab-show corrects the value once Qt
        finally computes a real maximum.
        """
        bar = self._log_view.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _on_log_scrolled(self, value: int) -> None:
        """Follow the tail only while the user is *at* the tail.

        Called for our own `setValue` too, which is harmless: that call sets the
        value to the maximum, so it re-affirms following rather than cancelling
        it. A user dragging up sets a lower value and pauses the follow, which is
        the behaviour a console should have — a log that yanks itself back to the
        bottom while you are reading is worse than one that does not follow.
        """
        bar = self._log_view.verticalScrollBar()
        self._log_follow = value >= bar.maximum()

    def _on_tab_changed(self, index: int) -> None:
        """Re-pin the log when its tab becomes visible.

        The whole point of the fix. While the tab was hidden Qt reported a
        scrollbar maximum that did not reflect the appended content, so the
        `setValue` in `_scroll_log_to_end` had nothing to move to. Once the tab is
        current Qt lays the document out for real, and *this* is the first moment
        a correct maximum exists.
        """
        if index == _TAB_LOG and self._log_follow:
            self._scroll_log_to_end()

    def set_progress(self, overall: float, task: float) -> None:
        """Update the one progress bar.

        `overall` is the whole-rip percentage (monotonic) and drives the bar.
        `task` is the current operation's own 0-100%; it is accepted because the
        worker's signal carries it, and not drawn, because the status line
        already says it ("Ripping track 5 of 14… 62%") and a second bar for it
        was the unlabelled one the UX review's M2 found. The status label is
        driven separately via `set_status` (fed from the rip worker's phase
        signal), so the label stays meaningful during phases that have no
        numeric percent.

        **The value is clamped, and a non-finite one is dropped.** This is the
        last line of defence before an `int()` that runs on the GUI thread, and
        `int()` on a non-finite float *raises* — `OverflowError` for `inf`,
        `ValueError` for `nan`. Either would escape a queued slot into the
        crash-dialog handler, over a progress bar.

        It is reachable from external text, which is why it is guarded rather than
        trusted: the worker derives these from `float()` on a percentage matched
        out of the ripper's stdout, and `float()` does *not* raise on a long digit
        run — it quietly returns `inf`. The producing patterns are now bounded so
        they cannot match one, but a percentage is a number arriving from another
        process and a guard here costs two comparisons (audit, 2026-07-31).
        """
        self._overall_bar.setValue(_bar_value(overall))
        del task  # said by the status line; see the docstring

    def set_status(self, text: str) -> None:
        """Set the status label, prefixed with the wall-clock time it was set.

        The timestamp (maintainer's ask: "if you're going to have a status,
        put a timestamp in as well") gives every phase a visible "when" — so a
        screenshot or a glance at a long rip shows the moment the current state
        was reached, and a status that stops advancing shows a time that stops
        advancing. Format ``HH:MM:SS · <text>``.
        """
        stamp = self._now().strftime("%H:%M:%S")
        self._status_label.setText(f"{stamp} · {text}")
        # Focus-safe live announcement (gap #4): speak the phase to a screen
        # reader WITHOUT touching focus — but only when the phase actually
        # changes. The raw text redraws constantly ("… 27%", "… 28%", ETA
        # ticks); announcing every redraw would drown the reader, so the
        # percent/ETA tail after the "…" is not part of the dedup key.
        self._last_status_text = text
        key = status_phase_key(text)
        if key and key != self._announced_status_key:
            self._announced_status_key = key
            announce(self._status_label, key)

    def current_status(self) -> str:
        """The most recent status text (no timestamp prefix), or "".

        The desktop notification needs this. It used to be sent the local
        ``status`` variable captured in ``_on_rip_finished``, which is assigned
        *before* the read-speed/stability summary overwrites the on-screen line
        — so the unattended user, the notification's entire audience, was told
        "all tracks ripped cleanly" while the window said a track never read
        reproducibly (audit finding, 2026-07-28).
        """
        return self._last_status_text

    def downgrade_verdict(self, reason: str) -> None:
        """Recolour the trust banner to amber and append ``reason``.

        The banner is set once, from the AccurateRip parse, and then never hears
        about anything that fails afterwards — a FLAC master that won't decode,
        a lossless derived file that doesn't match, read instability that
        survived the auto-fix. A green "Bit-perfect" headline above a status line
        reporting a failed integrity check is the single worst thing this screen
        can show, because the banner is the at-a-glance trust object the whole
        design rests on. Anything that discovers a problem after the fact calls
        this (audit finding, 2026-07-28).

        Idempotent per reason: the same reason is never appended twice, so a
        re-run of a post-rip check can't stack duplicates.
        """
        if not reason or reason in self._verdict_downgrades:
            return
        self._verdict_downgrades.append(reason)
        # (Never while a failure is shown: the banner's text is then the failure,
        # which `_render_verdict_banner` adds by itself, and taking it as the
        # base would print it twice.)
        if not self._verdict_base_message and not self._verdict_failure:
            self._verdict_base_message = self._verdict_banner.text()
        self._render_verdict_banner("warn")

    def _render_verdict_banner(self, level: str) -> None:
        """Draw the banner from its two inputs: the base verdict + the downgrades.

        The banner is **one sentence assembled from two pieces of state**, and it
        used to be assembled in two places — :meth:`set_rip_log` wrote the clean
        verdict, :meth:`downgrade_verdict` wrote verdict-plus-reasons — so which
        one ran last decided what the user saw. ``set_rip_log`` even carried a
        comment promising it re-applied any already-recorded downgrades; nothing
        did. It was true only by accident, because ``set_rip_log`` happens to be
        called exactly once per :meth:`clear` and the post-rip checks that
        downgrade all report *after* it. One reordering — the unknown-album
        self-heal is a single ``return`` away from ripping twice in one cycle —
        and a recorded "FLAC master failed the decode check" would have vanished
        under a fresh green "✓ Bit-perfect", which this screen exists to prevent.

        So there is one renderer and it reads both inputs every time. That is the
        same fix as ``expected_track_total`` and ``_ar_tooltip``: when a fact has
        more than one surface, compute it once (audit finding, 2026-07-31).
        """
        base = self._verdict_base_message
        failure = self._verdict_failure
        if not base and not self._verdict_downgrades and not failure:
            self._verdict_banner.setVisible(False)
            self._verdict_level = None
            return
        # One assembly, shared with the report's verdict (`apply_downgrades`), so
        # the window and the record cannot word the same downgrade two ways.
        text, level = (
            apply_downgrades(base, level, self._verdict_downgrades)
            if base or self._verdict_downgrades
            else ("", level)
        )
        # ONE PLAIN NEXT STEP, on the screen only (UX review V1). The sentence
        # above says what AccurateRip found; this says what to do about it, with
        # the controls named by the labels the window shows. Added here, not to
        # the verdict, because the verdict is also the report's `verdict` field,
        # which records what was found rather than advice.
        #
        # NOT when a downgrade is on the verdict. A downgrade is a second cause the
        # window learned after the log (the disc is another album's, the ripper is
        # not the one approved, …), and "clean the disc and re-rip" is the wrong
        # advice for any of them: re-ripping another album's disc under these tags
        # repeats the mistake. The banner then says exactly what the report says
        # (`tests/test_disc_identity.py`, the banner and report word a mismatch
        # identically), which is the right state for a verdict with two causes.
        #
        # Nor for a track a CTDB repair replaced and a fresh CTDB check confirmed:
        # the reconciled line says CTDB decides it, and "re-rip track 9" under
        # "CTDB decides track 9" would be two instructions about one file.
        self._verdict_render_level = level
        attention = tuple(
            n for n in self._verdict_attention if n not in self._repaired_confirmed()
        )
        if level == "warn" and attention and not self._verdict_downgrades:
            text = f"{text} {next_step_sentence(attention)}"
        # A FAILED RIP OUTRANKS ITS VERDICT (UX review E1). The failure's
        # sentence comes first, at the error level with its ✖; whatever the
        # partial log's verdict says follows on the next line, because the
        # tracks that did finish are still worth knowing about.
        if failure:
            text = f"{failure}\n{text}" if text else failure
            level = "error"
        self._verdict_level = level
        self._verdict_banner.setText(text)
        apply_status_style(self._verdict_banner, level)
        self._verdict_banner.setVisible(True)
        announce(self._verdict_banner, text)

    def show_failure(self, text: str, log_path: Path | None) -> None:
        """Show a failed rip on the verdict banner, at the error level.

        ``text`` is the whole sentence (``finish_wording.failure_banner_text``:
        ``✖``, the dependency's own words first). ``log_path`` is the log the
        **Open log** button beside it opens; None hides the button. Replaces an
        earlier failure's text (the finish handler words it again with
        everything it knows), and is cleared by :meth:`clear` at the next rip.

        UX review E1, 2026-11-17: a failure used to be one grey status line,
        ``Error: …``, with no marker and nothing to click.
        """
        self._verdict_failure = text.strip()
        self._failure_log_path = log_path
        self._open_failure_log_button.setVisible(log_path is not None)
        self._verdict_banner.setAccessibleName(_FAILURE_ACCESSIBLE_NAME)
        self._render_verdict_banner("error")

    def offer_cancelled_folder(self, folder: Path | None) -> None:
        """After a cancelled rip, offer to open ``folder``; None hides the offer.

        The window words the status line ("… are in <folder>") and hands the
        same folder here, so the sentence and the button cannot name two
        places. Cleared by :meth:`clear` at the next rip.
        """
        self._cancelled_folder = folder
        self._open_cancelled_folder_button.setVisible(folder is not None)

    def _on_open_cancelled_folder(self) -> None:
        """Open the cancelled rip's folder on the desktop."""
        if self._cancelled_folder is None:
            return
        open_path_externally(
            self._cancelled_folder,
            parent=self,
            open_url=self._open_url,
            what="rip folder",
        )

    def _on_open_failure_log(self) -> None:
        """Open the log the failure banner names, on the desktop."""
        if self._failure_log_path is None:
            return
        open_path_externally(
            self._failure_log_path,
            parent=self,
            open_url=self._open_url,
            what="log file",
        )

    def verdict_level(self) -> str | None:
        """The level the verdict banner shows now, or None while it is hidden.

        ``"ok"``, ``"warn"``, ``"neutral"`` or ``"error"``, after every
        downgrade. The window reads it for the status line's lead
        (``finish_wording.finished_line``), so the line under the progress bar
        and the banner under it carry the same mark (UX review V1).
        """
        return self._verdict_level

    def set_rip_log(
        self,
        rip_log: RipLog,
        *,
        disc_track_total: int | None = None,
        outcome_status: str = "",
    ) -> None:
        """Populate the AccurateRip table + verdict banner from a parsed log.

        ``disc_track_total`` and ``outcome_status`` are what stop the trust
        headline claiming "all N tracks" over a rip that never reached the end of
        the disc — a cancelled rip's log contains only the tracks it got to, so
        the log alone cannot tell the verdict how much is missing. Keyword-only
        and defaulted so a caller without them degrades to the old wording rather
        than failing.
        """
        # Kept so the async CTDB verdict can reconcile itself against AccurateRip.
        self._last_rip_log = rip_log
        # The rip is over, so the one bar no longer names a track it is on.
        self._current_track = None
        self._refresh_bar_format()
        message, level = accuraterip_verdict(
            rip_log,
            disc_track_total=disc_track_total,
            outcome_status=outcome_status,
        )
        # The log gives the BASE verdict only. Anything already recorded by
        # `downgrade_verdict` is still true and is re-applied by the one renderer
        # — which is what the old comment here claimed and the old code did not
        # do. It also announces the headline focus-safely, the one post-rip
        # update a screen-reader user must not miss (gap #4).
        self._verdict_base_message = message
        # Which tracks need the next step, and the technical sentence for the
        # tooltip ("only frame 450 matched …"), from the verdict's own predicate
        # (`accuraterip_contradictions`). A next step only when SOME of the audio
        # tracks are contradicted: when every one is, re-ripping them all is not
        # the advice, and the verdict already names a wrong read offset.
        contradictions = accuraterip_contradictions(rip_log)
        audio_tracks = [t for t in rip_log.tracks if not is_data_track(t)]
        self._verdict_attention = (
            tuple(number for number, _kind in contradictions)
            if 0 < len(contradictions) < len(audio_tracks)
            else ()
        )
        detail = contradicted_tracks_sentence(contradictions)
        self._verdict_banner.setToolTip(
            plain_tooltip(
                f"{detail}. The track list's Verified column shows each track's result."
                if detail
                else ""
            )
        )
        self._render_verdict_banner(level)

        # Read-effort early warning (per-track "hard to read"). Hidden when clean.
        effort = read_effort_summary_line(rip_log)
        self._read_effort_label.setText(effort)
        self._read_effort_label.setVisible(bool(effort))
        if effort:
            announce(self._read_effort_label, effort)

        # The per-track cells for the track table, and the reconciled line: a
        # CTDB answer that arrived first is applied to them here.
        self._render_reconciled()

        # Album loudness + partial-accurate footnote (data cyanrip already
        # logged; previously only in the JSON). Hidden when there's nothing.
        summary = loudness_summary_line(rip_log)
        self._loudness_label.setText(summary)
        self._loudness_label.setVisible(bool(summary))
        self._refresh_details_tab_marker()

        # The rip is over: show the Details tab, whatever the user was reading
        # during it (the console, say). The per-track results are in the track
        # list above, which needs no tab.
        self._tabs.setCurrentIndex(_TAB_DETAILS)

    def set_comparison(self, comparison: object) -> None:
        """Show the re-rip comparison banner from a RipComparison.

        ``comparison`` is a :class:`platterpus.rip_compare.RipComparison`. Passing
        None (or something with no summary) hides the banner. Duck-typed via the
        pure :func:`comparison_banner_text` so it never raises."""
        text, level = comparison_banner_text(comparison)
        if not text:
            self._comparison_label.clear()
            self._comparison_label.setVisible(False)
            return
        self._comparison_label.setText(text)
        apply_status_style(self._comparison_label, level)
        self._comparison_label.setVisible(True)
        # A silently-changed track is exactly what a screen-reader user would
        # otherwise never learn about — announce the comparison (gap #4).
        announce(self._comparison_label, text)

    def set_ctdb_status(self, text: str) -> None:
        """Show an in-progress CTDB line (e.g. 'Verifying against CTDB…')."""
        self._ctdb_label.setText(text)
        self._ctdb_label.setVisible(True)
        self._refresh_details_tab_marker()
        self._announce_ctdb(text)

    def set_ctdb_repair(
        self, text: str, level: str, *, result: object | None = None
    ) -> None:
        """Show what the automatic CTDB repair did, or why it did not.

        ``text`` carries its own marker (``✓``/``⚠``/``ⓘ``), so the colour from
        ``level`` is never the only signal. Empty ``text`` hides the line.

        ``result`` is the repair's finished result (the CTDB result carrying its
        ``repair`` record and ``after_repair`` check), when there is one: the
        reconciled line and the track table then say which tracks were repaired
        and whether a fresh CTDB check confirmed them. None (the in-progress
        line) leaves what they say unchanged.
        """
        self._ctdb_repair_label.setText(text)
        apply_status_style(self._ctdb_repair_label, level)
        self._ctdb_repair_label.setVisible(bool(text))
        if text:
            self._refresh_details_tab_marker()
            self._announce_ctdb(text)
        if result is not None:
            self._repair_result = result
            self._render_reconciled()

    def set_ctdb_result(self, result: CtdbVerifyResult) -> None:
        """Render the final CTDB verdict under the AccurateRip table.

        The audio-CRC algorithm is hardware-validated (KDD-16), so a trustworthy
        match renders as verified. If that gate is ever re-opened
        (``result.trustworthy`` False), a match falls back to an "experimental"
        label — we never claim a verification the algorithm can't stand behind.
        """
        level = ctdb_verdict_level(result, self._last_rip_log)
        verdict_text = ctdb_display_line(result, level)
        self._ctdb_label.setText(verdict_text)
        apply_status_style(self._ctdb_label, level)
        self._ctdb_label.setVisible(True)
        self._announce_ctdb(verdict_text)

        # The reconciled line under the banner says which of the two decides,
        # and the track table's cells take CTDB's per-track answer (its ⓘ note
        # on a track CTDB questions that AccurateRip does not contradict).
        self._ctdb_result = result
        self._ctdb_tracks = tuple(getattr(result, "tracks", ()) or ())
        self._render_reconciled()
        # The Details tab now holds a verdict the user has not seen — put the
        # marker on its label so they know to look, rather than discovering it
        # only if they happen to click.
        self._refresh_details_tab_marker()

    def set_log_path(self, path: Path | None) -> None:
        """Enable the post-rip output buttons from the rip log's path.

        The log path locates all three outputs: the ``.log`` itself, the
        ``.platterpus.json`` report beside it, and their parent album folder.
        Passing None (or "") disables all three (used when no log was written).
        """
        from platterpus.rip_report import report_path_for

        if path is None or str(path) == "":
            # Cancelled, or no .log was written (a frozen last-track rip). Do NOT
            # blank the buttons begin_rip enabled at start: the partial album
            # folder and the real-time app log are still the user's way in. Only
            # the report + cue (which need the finished .log) are unavailable.
            self._log_path = None
            self._report_path = None
            self._cue_path = None
            self._view_report_button.setEnabled(False)
            self._view_cue_button.setEnabled(False)
            # Revert Open folder to the in-progress folder begin_rip set (None if
            # no rip was begun), NOT a previous finish's album folder. View log
            # falls back to the live app log. Both stay reachable after a cancel /
            # freeze; both are off if there was no in-progress rip.
            self._rip_dir = self._inprogress_rip_dir
            self._view_log_button.setEnabled(self._live_log_path is not None)
            self._open_folder_button.setEnabled(self._rip_dir is not None)
            return
        self._log_path = path
        self._report_path = report_path_for(path)
        self._rip_dir = path.parent
        # Don't gate on .exists() — the files may be reachable by xdg-open even
        # if a Path test fails, and the JSON report is written immediately after
        # this call (by the finish handler), so it'll be there on click.
        self._view_log_button.setEnabled(True)
        self._view_report_button.setEnabled(True)
        self._open_folder_button.setEnabled(True)
        # cyanrip writes ``<stem>.cue`` beside ``<stem>.log``. Unlike the report,
        # it's already on disk by now (cyanrip made it during the rip), so gate
        # the button on the file actually being there — no dead button when a
        # rip produced no cue. Deriving from the log path means a library move
        # (which re-calls set_log_path with the new location) repoints it too.
        cue_path = path.with_suffix(".cue")
        self._cue_path = cue_path if cue_path.exists() else None
        self._view_cue_button.setEnabled(self._cue_path is not None)

    # --- Internals ----------------------------------------------------------

    def track_results(self) -> dict[int, TrackResultCells]:
        """The per-track cells last handed to the track table, by track number."""
        return dict(self._track_results)

    def reconciled_text(self) -> str:
        """The reconciled verdict line as shown, or "" while it is hidden."""
        return (
            "" if self._reconciled_label.isHidden() else self._reconciled_label.text()
        )

    def _repaired_confirmed(self) -> frozenset[object]:
        """Tracks a CTDB repair replaced and a fresh CTDB check confirmed."""
        return frozenset(
            n for n, agrees in repaired_tracks(self._repair_result).items() if agrees
        )

    def _emit_track_results(self) -> None:
        """Recompute the track table's cells from what this pane holds; emit them.

        Empty with no rip log (a cleared pane), so the table drops the last
        rip's Verified column. Read from the same three inputs as the reconciled
        line, at the same moments, so the two cannot describe one rip two ways.
        """
        rip_log = self._last_rip_log
        self._track_results = (
            result_cells(rip_log, self._ctdb_tracks, self._repair_result)
            if rip_log is not None
            else {}
        )
        self.track_results_changed.emit(dict(self._track_results))

    def _render_reconciled(self) -> None:
        """Re-render the reconciled verdict line and the track table's cells.

        Called by :meth:`set_rip_log`, :meth:`set_ctdb_result` and
        :meth:`set_ctdb_repair`, so the order the three inputs arrive in does not
        matter: each one re-renders from all three. The line is hidden until
        CTDB has answered (``reconcile_verdict`` returns None), and announced to
        a screen reader once per distinct sentence.
        """
        self._emit_track_results()
        if self._repair_result is not None and self._verdict_render_level:
            # A confirmed repair takes its tracks out of the banner's next step.
            self._render_verdict_banner(self._verdict_render_level)
        verdict = reconcile_verdict(
            self._last_rip_log, self._ctdb_result, self._repair_result
        )
        if verdict is None:
            self._reconciled_label.clear()
            self._reconciled_label.setVisible(False)
            return
        changed = verdict.text != self._reconciled_label.text()
        self._reconciled_label.setText(verdict.text)
        # Not bold: the banner above is the headline, and two bold amber
        # paragraphs one under the other was the weight the UX review's A3 found
        # separated nothing. The marker and the colour still carry the level.
        apply_status_style(self._reconciled_label, verdict.level, bold=False)
        self._reconciled_label.setVisible(True)
        if changed:
            announce(self._reconciled_label, verdict.text)

    def _announce_ctdb(self, text: str) -> None:
        """Announce a CTDB line once — the in-progress ping, then the verdict.

        Deduped on the full text so a repeated render of the same state (the
        async handler can re-fire) never repeats itself to a screen reader.
        """
        if text and text != self._announced_ctdb_text:
            self._announced_ctdb_text = text
            announce(self._ctdb_label, text)

    def _default_view_file(self, path: Path, title: str) -> None:
        """Open ``path`` in the in-app read-only viewer (IMP-1), passing along the
        same injected ``open_url`` so the viewer's "Open externally…" button still
        defers to the OS. Import is local so the dialog module isn't pulled in
        until the first view."""
        from platterpus.ui.dialogs.file_viewer import FileViewerDialog

        dialog = FileViewerDialog(
            path, title=title, parent=self, open_url=self._open_url
        )
        dialog.exec()

    def _on_view_log_clicked(self) -> None:
        # Prefer the backend's own .log once the rip has finished; during the
        # rip (before it exists) fall back to the real-time app log so the button
        # is useful the whole time — including while the drive is stuck.
        #
        # Resolve WHICH of the two at click time, not at set time. `set_log_path`
        # deliberately doesn't gate on .exists() (the report is written moments
        # after it's called, so a set-time check would disable a button that is
        # about to be valid) — but that means `_log_path` can name a file that
        # never appeared, and preferring it unconditionally showed the user an
        # errno inside the viewer while the app log sat right there, readable.
        # Click time is the one moment the answer is actually knowable.
        candidates = [p for p in (self._log_path, self._live_log_path) if p is not None]
        if not candidates:
            return
        target = next((p for p in candidates if _is_readable(p)), candidates[0])
        if target is not candidates[0]:
            log.warning(
                "rip log %s is not readable; showing %s instead", candidates[0], target
            )
        # In-app viewer, not openUrl: a .log has no default app on a fresh KDE.
        self._view_file(target, f"Rip log — {target.name}")

    def _on_view_report_clicked(self) -> None:
        if self._report_path is None:
            return
        self._view_file(self._report_path, f"Rip report — {self._report_path.name}")

    def _on_view_cue_clicked(self) -> None:
        if self._cue_path is None:
            return
        # In-app viewer, not openUrl: a .cue has no default app on a fresh KDE.
        self._view_file(self._cue_path, f"Cue sheet — {self._cue_path.name}")

    def set_bundle_path(self, path: Path | None) -> None:
        """Point the "Report bundle" button at this rip's archive.

        Called from the GUI thread by a queued signal once the bundle has been
        written off-thread. `None` disables the button, which is the honest state
        when the bundle could not be built — a button that opens nothing is the
        silent-no-op shape this widget's other handlers already guard against.
        """
        self._bundle_path = path
        self._bundle_button.setEnabled(path is not None)

    def _on_bundle_clicked(self) -> None:
        if self._bundle_path is None:
            return
        # Reveal the FOLDER, not the archive: a .tar.gz has no useful default
        # handler on most desktops (it opens an archive manager at best), and
        # the user's next action is to attach the file, which needs a file
        # manager sitting on it.
        open_path_externally(
            self._bundle_path.parent,
            parent=self,
            open_url=self._open_url,
            what="report bundle folder",
        )

    def _on_open_folder_clicked(self) -> None:
        if self._rip_dir is None:
            return
        # A folder usually DOES have a default handler (the file manager), so
        # openUrl is the right call here — and revealing the folder is the whole
        # point. "Usually" is why this goes through the shared helper: when no
        # file manager is wired up openUrl returns False, and throwing that away
        # is what makes a button that silently does nothing.
        open_path_externally(
            self._rip_dir,
            parent=self,
            open_url=self._open_url,
            what="rip folder",
        )


def status_phase_key(text: str) -> str:
    """The screen-reader dedup key for a status line: its *phase* clause.

    Status texts carry a fast-changing numeric tail after an ellipsis —
    "Ripping track 3 of 14… 27%", "Reading disc TOC… 42% — about 3m left" —
    that redraws many times a second. The phase clause before the "…" is what
    a listener actually needs ("Ripping track 3 of 14"), and it only changes
    on real transitions (new track, new phase). A status with no ellipsis
    (e.g. the finish verdict "Done — all 14 tracks verified, …") is its own
    key, so it is announced in full, once. Pure; unit-tested directly.
    """
    return text.split("…", 1)[0].strip()


def ctdb_verdict_line(result: CtdbVerifyResult) -> str:
    """One-line, user-facing summary of a CTDB verify outcome.

    Pure function (no widget) so it's unit-testable. The wording is the
    important safety case, in BOTH directions, and hinges on
    ``result.crc_validated`` (the CRC algorithm is hardware-validated, KDD-16):
    until then a MATCH is spelled out as *experimental* (never a plain
    "verified") and a NO_MATCH is spelled out as *not confirmed* (never "your
    rip differs") — because an un-validated CRC is a placeholder that is
    EXPECTED to disagree with the database, so neither a hit nor a miss is
    meaningful yet. This mirrors the rip's own "never claim a check that didn't
    run" rule.
    """
    verdict = result.verdict
    # Per track (TASKS R43): the same sentence the verdict's message carries,
    # added where the whole-disc line alone leaves the reader asking "which
    # track?" — a minority match and a no-match. Empty with no per-track result.
    # It carries where a track differs when the parity located it (R43).
    per_track = per_track_sentence(
        result.tracks, result.total_confidence, result.localisation
    )
    per_track = f" {per_track}" if per_track else ""
    if verdict is Verdict.MATCH:
        if result.trustworthy:
            shifted = (
                f", {shifted_pressing_phrase(result.matched_offset)}"
                if result.matched_offset
                else ""
            )
            return f"CTDB: verified ✓ (confidence {result.confidence}{shifted})"
        if result.crc_validated and result.outvoted:
            sentence = minority_match_sentence(
                result.confidence, result.total_confidence
            )
            return f"CTDB: {sentence}.{per_track}" if per_track else f"CTDB: {sentence}"
        return (
            f"CTDB: CRC matched (confidence {result.confidence}) — "
            "EXPERIMENTAL, pending hardware validation of the CRC algorithm "
            "(not yet a confirmed verification)"
        )
    if verdict is Verdict.NO_MATCH:
        # A no-match only means "the rip differs" if our CRC is trustworthy.
        # While the CRC algorithm is un-hardware-validated (KDD-16) our CRC is a
        # known placeholder that is EXPECTED to disagree, so asserting the rip
        # differs is a false alarm (the real-disc Police report showed exactly
        # this against an AccurateRip-verified rip). Mirror the MATCH path, which
        # already spells itself out as experimental until validated.
        if result.crc_validated and result.offset_range:
            # Every alignment CTDB accepts was tried (TASKS R43), so this line
            # may say what the earlier one below could not: no entry equals ours.
            return (
                "CTDB: no match — our audio differs from every entry CTDB holds "
                f"for this disc, at every alignment within ±{result.offset_range:,} "
                f"samples. AccurateRip remains the primary proof.{per_track}"
            )
        if result.crc_validated:
            # Without a sweep (a result built from the aligned CRC alone) the
            # line claims only that alignment, as it did before R43. CTDB itself
            # sweeps ±5879 samples because offset-shifted pressings are routine
            # (see ctdb/crc.py CTDB_OFFSET_RANGE), and our sweep lives only in
            # `--ctdb-calibrate`. So "differs from the database" was a positive
            # inaccuracy claim derived from testing 1 of ~11,759 valid
            # alignments (audit finding, 2026-07-28). Say what we measured.
            return (
                "CTDB: no match at the standard alignment — CTDB also holds "
                "offset-shifted pressings and this check only tests the "
                "standard one, so it isn’t evidence your rip is wrong. "
                f"AccurateRip is the per-track authority.{per_track}"
            )
        return (
            # No decision-log number in a user's sentence (UX review of
            # 0.7.127, W2): this said "(pending hardware validation, KDD-16)".
            "CTDB: not confirmed — the CRC check is still experimental (not yet "
            "validated on real drives); a non-match here doesn’t mean your "
            "rip is wrong — AccurateRip is the authority"
        )
    if verdict is Verdict.NOT_WHOLE_DISC:
        # The verdict's own sentence ("not run — CTDB verifies whole discs, and
        # this rip has 2 of the disc's 14 tracks"), not a paraphrase: one wording,
        # so this line and the report cannot describe the same skip two ways. It
        # must never fall through to the NOT_IN_DATABASE line below, which is a
        # claim about the disc that a check that never ran cannot make.
        return f"CTDB: {result.message}"
    if verdict is Verdict.NOT_IN_DATABASE:
        return "CTDB: this disc isn’t in the database"
    if verdict is Verdict.DECODER_UNAVAILABLE:
        return "CTDB: not verified — install the `flac` decoder to enable this"
    return "CTDB: verification unavailable (lookup or decode error)"


def ctdb_verdict_level(result: CtdbVerifyResult, rip_log: object = None) -> str:
    """Banner level ("ok" | "warn" | "neutral") for a CTDB verdict.

    Pairs with :func:`ctdb_verdict_line` to colour the label. A *trustworthy*
    match is green; an experimental (not-yet-hardware-validated) match is amber
    — never green, mirroring the wording's refusal to over-claim. Everything
    else (no match, not in DB, decoder missing, error) is neutral grey: those
    are "couldn't confirm", not "failed". A partial rip's ``NOT_WHOLE_DISC``
    is grey too: the check did not run, which is neither a pass nor a failure.

    **Green also needs AccurateRip to reject no track** (2026-10-19, P1): a
    whole-disc match beside a track AccurateRip compared and did not verify is
    two checks disagreeing, and green would side with the weaker one. Without a
    rip log the AccurateRip half is unknown and does not block green.
    """
    verdict = result.verdict
    if verdict is Verdict.MATCH:
        if not result.trustworthy:
            return "warn"
        if rip_log is not None and accuraterip_rejected_count(rip_log) > 0:
            return "warn"
        return "ok"
    return "neutral"


def ctdb_display_line(result: CtdbVerifyResult, level: str) -> str:
    """The Details tab's CTDB line, which never says "verified ✓" in amber.

    :func:`ctdb_verdict_line` words a trustworthy match "CTDB: verified ✓", and
    :func:`ctdb_verdict_level` makes it amber when AccurateRip rejects a track:
    the UX review's A3 found exactly that, a "verified ✓" whose colour said the
    opposite. So at the warn level the match is worded as what it is, a match of
    the whole disc that the reconciled line above weighs against AccurateRip,
    with a ``⚠`` that agrees with the colour. Every other line is unchanged.
    """
    text = ctdb_verdict_line(result)
    if level == "warn" and result.verdict is Verdict.MATCH and result.trustworthy:
        return (
            f"CTDB: ⚠ the whole disc matches (confidence {result.confidence}), but "
            "AccurateRip rejects a track; the verdict line above says which decides."
        )
    return text


def loudness_summary_line(rip_log: object) -> str:
    """One-line album-loudness + partial-accurate footnote, or "" when there's
    nothing to show.

    Pure and **never raises** (it backs a results-pane label populated from a
    best-effort parse): it defends against a missing/oddly-typed
    ``album_loudness`` dict or ``partially_accurate_summary`` and just omits any
    part it can't render. cyanrip logs carry integrated loudness (LUFS), loudness
    range (LU) and true peak (dBFS); legacy-format logs don't, so this returns
    "" for them (the label then stays hidden). The two facts are joined with
    " · " so a disc that has one but not the other still reads cleanly.
    """
    parts: list[str] = []
    try:
        loudness = getattr(rip_log, "album_loudness", None) or {}
        if isinstance(loudness, dict):
            bits: list[str] = []
            integrated = loudness.get("integrated_lufs")
            lra = loudness.get("lra_lu")
            peak = loudness.get("true_peak_dbfs")
            if integrated:
                bits.append(f"{integrated} LUFS integrated")
            if lra:
                bits.append(f"range {lra} LU")
            if peak:
                bits.append(f"true peak {peak} dBFS")
            if bits:
                # "Album loudness" only when the rip read the album. cyanrip's
                # rows cover whatever was read, so an interrupted or `-l` rip gets
                # a label saying what it measured (see `album_loudness`).
                name = album_loudness.label(album_loudness.coverage(rip_log))
                parts.append(f"{name}: " + ", ".join(bits))
        # Recomputed from the final per-track results, NOT read off the parse.
        #
        # This footnote sits directly under the verdict banner, and the banner
        # counts via `accuraterip_counts` while the parse-time string describes the
        # whole-disc pass. After an auto-fix re-rip those two disagree: on the
        # Police disc (2026-08-07) the banner said "the other 1" and this line said
        # "2 of 14", on the same screen. Same fact, two numbers, and the stale one
        # reads as the more specific.
        from platterpus.rip_report import _final_partial_summary

        partial = _final_partial_summary(rip_log) or ""
        if isinstance(partial, str) and partial.strip():
            parts.append(partial.strip())
    except Exception:  # noqa: BLE001 — a results-pane footnote must never crash
        log.exception("loudness summary line failed; omitting")
        return ""
    return " · ".join(parts)


def comparison_banner_text(comparison: object) -> tuple[str, str]:
    """Render a re-rip comparison banner: ``(text, level)``.

    ``comparison`` is a :class:`platterpus.rip_compare.RipComparison`. Returns
    ``("", "neutral")`` when there's nothing to show (no comparison, or no
    summary). The level ("ok"/"warn"/"neutral") drives the banner colour and the
    leading symbol (symbol + text, never colour alone — a11y). When some tracks
    differ, it appends the CLI hint for the full table / best-of assembly. Pure
    and **never raises** (duck-typed via ``getattr``); it backs a results-pane
    label populated off-thread.
    """
    try:
        summary = getattr(comparison, "summary", "") or ""
        if not summary:
            return "", "neutral"
        level = getattr(comparison, "headline_level", "neutral") or "neutral"
        prefix = {"ok": "✓", "warn": "⚠", "neutral": "ⓘ"}.get(level, "ⓘ")
        text = f"{prefix} Compared to your previous rip of this disc: {summary}"
        if getattr(comparison, "differing_count", 0):
            # The invocation the user can ACTUALLY type. There is no
            # `platterpus` on PATH for an AppImage install, which is the primary
            # distribution channel, so the literal string was an instruction that
            # produces `command not found`. Same defect the cyanrip fork reported
            # against the update dialog (round 8 lap 7 §H) — they found one
            # instance; this was the second of five.
            text += (
                f"  Run  {self_invocation()} --compare  for the full table, or  "
                "--assemble-best-of  to keep the best copy of each track."
            )
        return text, level
    except Exception:  # noqa: BLE001 — a results-pane banner must never crash
        log.exception("comparison banner text failed; omitting")
        return "", "neutral"


def read_effort_summary_line(rip_log: object) -> str:
    """One-line "these tracks were hard to read" footnote, or "" when clean.

    Names the tracks that needed unusually heavy re-reading (or a ``-Z`` secure
    re-read that never converged) — the earliest in-rip hint that a track's audio
    may not be reproducible, even when it ultimately matched AccurateRip. Pure
    and **never raises** (it backs a results-pane label). Returns "" on a clean
    single-pass rip so the label stays hidden and uncluttered.
    """
    try:
        flagged = tracks_needing_heavy_reread(rip_log)
    except Exception:  # noqa: BLE001 — a footnote must never crash the pane
        log.exception("read-effort summary line failed; omitting")
        return ""
    if not flagged:
        return ""
    listed = ", ".join(str(n) for n in flagged)
    return (
        f"⚠ Track(s) {listed} needed heavy re-reading — the read may not be "
        "reproducible; re-rip to confirm."
    )
