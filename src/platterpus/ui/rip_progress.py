"""Rip progress widget — live status pane + AccurateRip results.

Three bands, top to bottom:

  **header** (fixed, never scrolls, never hidden)
      Overall progress bar · status line + task progress bar · stall notice ·
      the verdict banner (the bold, colour-coded at-a-glance trust headline) ·
      the read-effort and re-rip-comparison warnings
  **body** (a QTabWidget — exactly one scroll surface visible at a time)
      "Tracks"   the per-track AccurateRip results table
      "Details"  the CTDB verdict, the AccurateRip reconciliation, and album
                 loudness — marked with a ⚠ in the tab label when it holds a
                 caveat, so nothing hides behind an unopened tab
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
"""

from __future__ import annotations

import logging
import math
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from platterpus.ctdb.verify import CtdbVerifyResult, Verdict
from platterpus.parsers.rip_log import (
    RipLog,
    accuraterip_is_match,
    track_accuraterip_verified,
    tracks_needing_heavy_reread,
)
from platterpus.ui.accessibility import announce
from platterpus.ui.external_open import open_path_externally

# Re-exported so existing imports (and tests) can keep doing
# `from platterpus.ui.rip_progress import accuraterip_verdict`; the canonical
# home is the pure platterpus.verdict module.
from platterpus.verdict import (
    AR_STATE_ABSENT,
    AR_STATE_NO_DATA,
    AR_STATE_NO_MATCH,
    AR_STATE_NOT_CHECKED,
    AR_STATE_OFFSET_VARIANT,
    AR_STATE_VERIFIED,
    accuraterip_compared,
    accuraterip_state,
    accuraterip_verdict,
    reconcile_ar_ctdb,
)

__all__ = [
    "RipProgress",
    "accuraterip_verdict",
    "comparison_banner_text",
    "loudness_summary_line",
    "read_effort_summary_line",
    "status_phase_key",
]

# Shared explanation of the offset-variant ("partially accurate") status, used
# both as an AR-cell tooltip and echoed in the User Guide glossary — one wording
# so the table and the help can't drift (docs/ux-design-principles.md #1).
OFFSET_VARIANT_TOOLTIP: str = (
    "Offset-variant (partially accurate): the audio matches a known pressing in "
    "AccurateRip, but one shifted by a fixed offset from the common pressing — "
    "so it's not the exact canonical checksum. Usually just a different pressing "
    "and perfectly fine. BUT if a re-rip of the same disc gives a different "
    "result here, that points to a read-stability problem on this track, not a "
    "pressing difference — re-rip to confirm."
)

# The "we compared it and nothing matched" state. This is NOT "not in the
# database" — the disc IS there, our read just doesn't match any stored copy of
# it — and saying "not in DB" about such a track is a factually false claim. The
# durable EAC-compatible log already learned this (it writes "Cannot be verified
# as accurate", review finding 2026-07-28); the on-screen table did not, and
# collapsed the case into "not in DB" until 2026-07-31. The narrow column can
# only carry "in DB, no match", so the nuance lives here in the tooltip.
NO_MATCH_TOOLTIP: str = (
    "In the database, but no match: AccurateRip has this disc, and this track's "
    "checksum was compared against the copies other people submitted — none of "
    'them matched. That is NOT the same as "not in the database": the track '
    "simply cannot be verified as accurate. Innocent causes are common (an "
    "unlisted pressing, or a drive read offset that differs from ours), but a "
    "genuine read error looks exactly the same from here — re-rip the disc to "
    "tell them apart, and compare the two rips."
)

# The lookup never ran, so the database has said nothing either way. Kept
# separate from NO_MATCH_TOOLTIP because collapsing them is the exact conflation
# that made a never-queried disc read as a failed comparison (audit, 2026-07-31).
NOT_CHECKED_TOOLTIP: str = (
    "Not checked: no AccurateRip lookup was made for this rip, so the database "
    "has said nothing about this track either way. This is not a result — it is "
    "the absence of one. Re-rip with AccurateRip enabled (and a working network "
    "connection from the ripping container) to get a verdict."
)

log = logging.getLogger(__name__)

# AR table column layout. The brief calls out per-track AR confidence;
# we expose v1 and v2 separately since they can disagree. The trailing "EAC"
# column shows each track's EAC-format CRC32 (cyanrip's "EAC CRC32", = the Copy
# CRC in the companion log) so it can be eyeballed against a real EAC rip,
# plus a ✓ when the track meets the archival bar we can actually verify.
_AR_COLUMNS: list[str] = ["#", "Title", "Status", "AR v1", "AR v2", "EAC"]
_AR_COL_NUMBER: int = 0
_AR_COL_TITLE: int = 1
_AR_COL_STATUS: int = 2
_AR_COL_V1: int = 3
_AR_COL_V2: int = 4
_AR_COL_EAC: int = 5

# Glyphs for the EAC column's at-a-glance archival mark (symbol + text, never
# colour alone — the trust-first UX rule).
_EAC_VERIFIED: str = "✓"
_EAC_PARTIAL: str = "~"

# Tab order in the pane's body. Named rather than inlined because three separate
# methods switch between them and an off-by-one here would silently show the
# wrong tab at the end of a rip.
_TAB_TRACKS: int = 0
_TAB_DETAILS: int = 1
_TAB_LOG: int = 2

# Base labels for the tabs. `_refresh_details_tab_marker` prepends a warning
# glyph to the Details label when that tab is holding a caveat, so a user who
# never opens it can still SEE that there is something in there — the tab must
# not become a place where warnings go to hide (docs/ux-design-principles.md:
# status is conveyed by symbol + text, never by absence).
_TAB_LABEL_TRACKS: str = "&Tracks"
_TAB_LABEL_DETAILS: str = "&Details"
_TAB_LABEL_LOG: str = "Live &log"


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
    """Live progress + log + AccurateRip results."""

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
        # The last parsed rip log, kept so the CTDB handler (which finishes later,
        # asynchronously) can reconcile its verdict against AccurateRip.
        self._last_rip_log: RipLog | None = None
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

        # --- Overall progress (whole rip) ---
        # A coarse start-to-finish bar so the user can gauge how much of
        # the entire disc is left, independent of the per-track churn.
        overall_row = QHBoxLayout()
        overall_row.addWidget(QLabel("Overall", self))
        self._overall_bar: QProgressBar = QProgressBar(self)
        self._overall_bar.setRange(0, 100)
        self._overall_bar.setValue(0)
        self._overall_bar.setTextVisible(True)
        overall_row.addWidget(self._overall_bar, stretch=1)
        root.addLayout(overall_row)

        # --- Status line + current-task progress bar ---
        # The status label names the current operation; the task bar
        # tracks that one operation's 0-100% (it resets read→verify→encode).
        self._status_label: QLabel = QLabel("Idle.", self)
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
        self._stall_label.setWordWrap(True)
        self._stall_label.setVisible(False)
        self._stall_label.setStyleSheet(_banner_style("warn"))
        root.addWidget(self._stall_label)

        self._progress_bar: QProgressBar = QProgressBar(self)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        root.addWidget(self._progress_bar)

        # --- Verification verdict banner (at-a-glance trust) ---
        # A single bold, colour-coded headline above the per-track table so the
        # user sees "is this rip trustworthy?" without reading every row. Green
        # = every audio track matched AccurateRip (bit-perfect, community-
        # verifiable); amber = a partial match worth a look; grey = nothing to
        # assert yet (e.g. a disc not in the database). Populated from the
        # parsed log by set_rip_log; hidden until then. The wording NEVER over-
        # claims — it mirrors what AccurateRip actually returned.
        self._verdict_banner: QLabel = QLabel("", self)
        self._verdict_banner.setWordWrap(True)
        self._verdict_banner.setVisible(False)
        root.addWidget(self._verdict_banner)

        # --- Read-effort early warning (per-track "hard to read") ---
        # Amber footnote naming tracks that needed unusually heavy re-reading (or
        # a -Z that never converged) even if they matched AccurateRip — the
        # earliest hint a track may not be reproducible. Hidden on a clean rip.
        self._read_effort_label: QLabel = QLabel("", self)
        self._read_effort_label.setWordWrap(True)
        self._read_effort_label.setVisible(False)
        self._read_effort_label.setStyleSheet(_banner_style("warn"))
        root.addWidget(self._read_effort_label)

        # --- Re-rip comparison banner ("you've ripped this disc before") ---
        # When a prior rip of the SAME disc is found in the library, a one-liner
        # here says how this rip compares — how many tracks are byte-identical,
        # which differ, and which rip is the better master. Populated off-thread
        # after the rip (set_comparison); hidden when there's no prior rip.
        self._comparison_label: QLabel = QLabel("", self)
        self._comparison_label.setWordWrap(True)
        self._comparison_label.setVisible(False)
        root.addWidget(self._comparison_label)

        # --- The tabbed body: one scroll surface per tab, never nested --------
        # Everything below the headline goes into tabs. The point is not
        # tidiness, it is that **only one tab is visible at a time**, so the pane
        # can never show two scrollbars and can never nest one inside another
        # (see the band comment at the top of __init__ for the measurements).
        #
        # The order is the order you need them in: the per-track table is what
        # you read when a rip finishes and is therefore first and default; the
        # supporting explanations sit behind it; the live console is last because
        # it matters *during* a rip, and `begin_rip`/`set_rip_log` switch to the
        # right one at the right moment so you never have to click to see what is
        # happening now.
        self._tabs: QTabWidget = QTabWidget(self)
        # Document mode: this is an interior grouping, not a top-level notebook,
        # so the heavier framed-tab look would read as a separate window.
        self._tabs.setDocumentMode(True)
        root.addWidget(self._tabs, stretch=1)

        # --- AccurateRip results table ---
        self._ar_table: QTableWidget = QTableWidget(0, len(_AR_COLUMNS), self)
        self._ar_table.setHorizontalHeaderLabels(_AR_COLUMNS)
        self._ar_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._ar_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._ar_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._ar_table.verticalHeader().setVisible(False)
        header = self._ar_table.horizontalHeader()
        header.setSectionResizeMode(_AR_COL_TITLE, QHeaderView.ResizeMode.Stretch)
        for col in (
            _AR_COL_NUMBER,
            _AR_COL_STATUS,
            _AR_COL_V1,
            _AR_COL_V2,
            _AR_COL_EAC,
        ):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        # A small minimum so the splitter can shrink this tab and free up drag
        # slack at the default window size. Without it the pane's minimum height
        # ≈ the whole window, leaving nothing to redistribute — the splitter
        # handles showed the resize cursor but wouldn't move until the window was
        # maximized (real-user report, 0.4.4). The table scrolls, so 64 px is fine.
        self._ar_table.setMinimumHeight(64)
        self._tabs.addTab(self._ar_table, _TAB_LABEL_TRACKS)

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

        # --- CTDB verdict line (second, TOC-keyed verification path) ---
        # A one-liner that only appears when a CTDB verify ran (it's an opt-in,
        # post-rip network check). The audio-CRC algorithm is now
        # hardware-validated (KDD-16, crc.CRC_VALIDATED True), so a match renders
        # green "verified"; the "experimental" wording remains only as a defensive
        # fallback should the gate ever be re-opened (set_ctdb_result reads the
        # flag live).
        self._ctdb_label: QLabel = QLabel("", self)
        self._ctdb_label.setWordWrap(True)
        self._ctdb_label.setVisible(False)
        details.addWidget(self._ctdb_label)

        # --- CTDB ↔ AccurateRip reconciliation ---
        # A neutral one-liner explaining why a CTDB "no match" and an AccurateRip
        # "mostly accurate" are the SAME finding, not two contradictory ones (a
        # whole-disc CRC can't match when a couple of tracks differ). Only shown
        # when the two would otherwise look like they disagree (see
        # verdict.reconcile_ar_ctdb); hidden the rest of the time.
        self._ctdb_reconcile_label: QLabel = QLabel("", self)
        self._ctdb_reconcile_label.setWordWrap(True)
        self._ctdb_reconcile_label.setVisible(False)
        self._ctdb_reconcile_label.setStyleSheet("QLabel { color: palette(mid); }")
        details.addWidget(self._ctdb_reconcile_label)

        # --- Album loudness + partial-accurate footnote ---
        # A neutral one-liner surfacing two facts cyanrip already computed and
        # that we were only writing to the JSON: the album loudness (integrated
        # LUFS / range / true peak) and how many tracks were offset-variant
        # ("partially accurate") matches. Populated from the parsed log by
        # set_rip_log; hidden when there's nothing to show (e.g. a whipper log
        # carries no loudness and the disc had no partial matches).
        self._loudness_label: QLabel = QLabel("", self)
        self._loudness_label.setWordWrap(True)
        self._loudness_label.setVisible(False)
        self._loudness_label.setStyleSheet("QLabel { color: palette(mid); }")
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
        # Same splitter-slack reasoning as the table above.
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
        root.addLayout(button_row)

        # --- Accessibility (docs/ux-design-principles.md #10) ---
        # Screen readers announce a widget by its accessible name; without one a
        # bare QProgressBar/QLabel/QTableWidget reads as just its value or
        # "label". Name every status surface so the rip is followable without
        # sight, and so the colour-coded verdict is never the *only* signal.
        self._overall_bar.setAccessibleName("Overall rip progress")
        self._progress_bar.setAccessibleName("Current task progress")
        self._status_label.setAccessibleName("Rip status")
        self._log_view.setAccessibleName("Rip log output")
        self._verdict_banner.setAccessibleName("AccurateRip verification verdict")
        self._read_effort_label.setAccessibleName("Read-effort warning")
        self._stall_label.setAccessibleName("Rip stall warning")
        self._comparison_label.setAccessibleName("Re-rip comparison")
        self._ar_table.setAccessibleName("Per-track AccurateRip results")
        self._ctdb_label.setAccessibleName("CTDB verification result")
        self._ctdb_reconcile_label.setAccessibleName(
            "CTDB and AccurateRip reconciliation"
        )
        self._loudness_label.setAccessibleName(
            "Album loudness and partial-match summary"
        )
        self._view_log_button.setAccessibleName("Open the rip log file")
        self._view_report_button.setAccessibleName(
            "Open the machine-readable rip report (JSON)"
        )
        self._view_cue_button.setAccessibleName("Open the disc's cue sheet")
        self._open_folder_button.setAccessibleName("Open the folder containing the rip")
        # The tab strip is now the way to reach two thirds of this pane, so it has
        # to be as reachable as the buttons: each tab carries an Alt+<letter>
        # mnemonic (in its label), the strip is in the tab order, and the widget
        # itself is named so a screen reader says what the grouping *is* rather
        # than just "tab bar". Ctrl+Tab / arrow keys move between tabs for free.
        self._tabs.setAccessibleName("Rip results, details, and live log")
        self._tabs.setTabToolTip(_TAB_TRACKS, "Per-track AccurateRip results")
        self._tabs.setTabToolTip(
            _TAB_DETAILS,
            "CTDB verification, read-effort caveats, and album loudness",
        )
        self._tabs.setTabToolTip(_TAB_LOG, "Live output from the ripper")

    # --- Public surface -----------------------------------------------------

    def clear(self) -> None:
        """Reset to the idle state. Called when starting a new rip."""
        self._status_label.setText("Idle.")
        self._overall_bar.setValue(0)
        self._progress_bar.setValue(0)
        self._log_view.clear()
        self._verdict_banner.clear()
        self._verdict_banner.setVisible(False)
        self._read_effort_label.clear()
        self._read_effort_label.setVisible(False)
        self._comparison_label.clear()
        self._comparison_label.setVisible(False)
        self._ar_table.setRowCount(0)
        self._ctdb_label.clear()
        self._ctdb_label.setVisible(False)
        self._ctdb_reconcile_label.clear()
        self._ctdb_reconcile_label.setVisible(False)
        self._loudness_label.clear()
        self._loudness_label.setVisible(False)
        self._stall_label.clear()
        self._stall_label.setVisible(False)
        self._view_log_button.setEnabled(False)
        self._view_report_button.setEnabled(False)
        self._view_cue_button.setEnabled(False)
        self._open_folder_button.setEnabled(False)
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
        # The Details tab is empty again, so drop any warning marker from its
        # label — a stale ⚠ on an empty tab would send the user looking for a
        # caveat that no longer exists.
        self._refresh_details_tab_marker()

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
            for label in (self._ctdb_label, self._ctdb_reconcile_label)
        )
        label = f"⚠ {_TAB_LABEL_DETAILS}" if has_warning else _TAB_LABEL_DETAILS
        if self._tabs.tabText(_TAB_DETAILS) != label:
            self._tabs.setTabText(_TAB_DETAILS, label)

    def begin_rip(self, rip_dir: Path | None, live_log: Path | None) -> None:
        """At rip START, make the in-progress rip reachable immediately.

        Enables **Open rip folder** (→ ``rip_dir``, which cyanrip populates as it
        works) and **View log** (→ ``live_log``, the real-time app log) the moment
        the rip begins — so a frozen or cancelled rip is never a dead end (the
        reported "Open rip folder did nothing after I force-cancelled"). At finish
        :meth:`set_log_path` supersedes these with the backend's own richer
        ``.log`` / ``.cue`` / JSON report. Report + cue stay disabled until then
        (they don't exist yet). Call after :meth:`clear`.
        """
        self._rip_dir = rip_dir
        self._inprogress_rip_dir = rip_dir
        self._live_log_path = live_log
        self._open_folder_button.setEnabled(rip_dir is not None)
        self._view_log_button.setEnabled(live_log is not None)
        # Show the live console for the duration of the rip. During a rip the
        # console is the interesting tab and the results table is empty, so
        # landing on anything else would mean the user has to click to watch
        # their own rip. `set_rip_log` switches back to Tracks at the end.
        self._tabs.setCurrentIndex(_TAB_LOG)

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
        """Update both progress bars.

        `overall` is the whole-rip percentage (monotonic); `task` is the
        current operation's own 0-100%. The status label is driven
        separately via `set_status` (fed from the rip worker's phase
        signal), so the label stays meaningful during phases that have no
        numeric percent.

        **Both values are clamped, and non-finite ones are dropped.** This is the
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
        self._progress_bar.setValue(_bar_value(task))

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
        if not self._verdict_base_message:
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
        if not base and not self._verdict_downgrades:
            self._verdict_banner.setVisible(False)
            return
        if self._verdict_downgrades:
            # Drop a leading "✓" — the tick is a claim this text no longer
            # supports. With no base verdict at all the reasons stand alone.
            headline = base.lstrip("✓ ").strip() if base.startswith("✓") else base
            joined = "; ".join(self._verdict_downgrades)
            text = f"⚠ {headline} — {joined}" if headline else f"⚠ {joined}"
            level = "warn"
        else:
            text = base
        self._verdict_banner.setText(text)
        self._verdict_banner.setStyleSheet(_banner_style(level))
        self._verdict_banner.setVisible(True)
        announce(self._verdict_banner, text)

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
        self._render_verdict_banner(level)

        # Read-effort early warning (per-track "hard to read"). Hidden when clean.
        effort = read_effort_summary_line(rip_log)
        self._read_effort_label.setText(effort)
        self._read_effort_label.setVisible(bool(effort))
        if effort:
            announce(self._read_effort_label, effort)

        tracks = rip_log.tracks
        self._ar_table.setRowCount(len(tracks))
        for row, track in enumerate(tracks):
            number_item = QTableWidgetItem(str(track.number))
            title_item = QTableWidgetItem(_basename(track.filename))
            status_item = QTableWidgetItem(track.status or "")
            # Pass the +450 offset-variant result so a track that matched only
            # that (v1/v2 "not found") reads as a partially-accurate match, not
            # an alarming "…or bad rip" (trust-first, mirrors the CTDB fix).
            offset = track.accuraterip_offset
            # cyanrip's per-track "Accurip:" status — the only thing that says
            # whether a lookup happened at all. Without it, a disc nobody looked
            # up read as "in DB, no match" (audit, 2026-07-31).
            lookup = getattr(track, "accuraterip_lookup", None)
            v1_item = QTableWidgetItem(
                _ar_cell(track.accuraterip_v1, offset_result=offset, lookup=lookup)
            )
            v2_item = QTableWidgetItem(
                _ar_cell(track.accuraterip_v2, offset_result=offset, lookup=lookup)
            )
            # Footnote the cells that need one — the offset-variant explanation
            # (#4 of the 2026-07-09 trust improvements) and the "in the database
            # but nothing matched" explanation. `_ar_tooltip` reads the SAME
            # `_ar_state` as the cell text above, so the words and their
            # explanation can't disagree; deciding it here by hand is what let
            # the two drift before. Qt shows no tooltip for an empty string, so
            # an unremarkable cell needs no branch.
            v1_item.setToolTip(
                _ar_tooltip(track.accuraterip_v1, offset_result=offset, lookup=lookup)
            )
            v2_item.setToolTip(
                _ar_tooltip(track.accuraterip_v2, offset_result=offset, lookup=lookup)
            )
            eac_text, eac_tip = _eac_cell(track)
            eac_item = QTableWidgetItem(eac_text)
            eac_item.setToolTip(eac_tip)
            self._ar_table.setItem(row, _AR_COL_NUMBER, number_item)
            self._ar_table.setItem(row, _AR_COL_TITLE, title_item)
            self._ar_table.setItem(row, _AR_COL_STATUS, status_item)
            self._ar_table.setItem(row, _AR_COL_V1, v1_item)
            self._ar_table.setItem(row, _AR_COL_V2, v2_item)
            self._ar_table.setItem(row, _AR_COL_EAC, eac_item)

        # Album loudness + partial-accurate footnote (data cyanrip already
        # logged; previously only in the JSON). Hidden when there's nothing.
        summary = loudness_summary_line(rip_log)
        self._loudness_label.setText(summary)
        self._loudness_label.setVisible(bool(summary))

        # The rip is over, so the per-track results are what matters now — switch
        # away from the live console the user was watching. Only when there is
        # actually a table to show: an empty result set would swap a console with
        # useful output for a blank grid.
        if self._ar_table.rowCount():
            self._tabs.setCurrentIndex(_TAB_TRACKS)

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
        self._comparison_label.setStyleSheet(_banner_style(level))
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

    def set_ctdb_result(self, result: CtdbVerifyResult) -> None:
        """Render the final CTDB verdict under the AccurateRip table.

        The audio-CRC algorithm is hardware-validated (KDD-16), so a trustworthy
        match renders as verified. If that gate is ever re-opened
        (``result.trustworthy`` False), a match falls back to an "experimental"
        label — we never claim a verification the algorithm can't stand behind.
        """
        verdict_text = ctdb_verdict_line(result)
        self._ctdb_label.setText(verdict_text)
        self._ctdb_label.setStyleSheet(_banner_style(ctdb_verdict_level(result)))
        self._ctdb_label.setVisible(True)
        self._announce_ctdb(verdict_text)

        # Reconcile against AccurateRip so a CTDB "no match" beside an
        # AccurateRip "mostly accurate" doesn't read as a contradiction. Shown
        # only when the two would otherwise look like they disagree.
        reconciliation = (
            reconcile_ar_ctdb(self._last_rip_log, result)
            if self._last_rip_log is not None
            else None
        )
        if reconciliation:
            self._ctdb_reconcile_label.setText(reconciliation)
            self._ctdb_reconcile_label.setVisible(True)
        else:
            self._ctdb_reconcile_label.clear()
            self._ctdb_reconcile_label.setVisible(False)
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
    if verdict is Verdict.MATCH:
        if result.trustworthy:
            return f"CTDB: verified ✓ (confidence {result.confidence})"
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
        if result.crc_validated:
            # We compute ONE checksum, at the standard alignment. CTDB itself
            # sweeps ±5879 samples because offset-shifted pressings are routine
            # (see ctdb/crc.py CTDB_OFFSET_RANGE), and our sweep lives only in
            # `--ctdb-calibrate`. So "differs from the database" was a positive
            # inaccuracy claim derived from testing 1 of ~11,759 valid
            # alignments (audit finding, 2026-07-28). Say what we measured.
            return (
                "CTDB: no match at the standard alignment — CTDB also holds "
                "offset-shifted pressings and this check only tests the "
                "standard one, so it isn’t evidence your rip is wrong. "
                "AccurateRip is the per-track authority."
            )
        return (
            "CTDB: not confirmed — the CRC check is still experimental (pending "
            "hardware validation, KDD-16); a non-match here doesn’t mean your "
            "rip is wrong — AccurateRip is the authority"
        )
    if verdict is Verdict.NOT_IN_DATABASE:
        return "CTDB: this disc isn’t in the database"
    if verdict is Verdict.DECODER_UNAVAILABLE:
        return "CTDB: not verified — install the `flac` decoder to enable this"
    return "CTDB: verification unavailable (lookup or decode error)"


def ctdb_verdict_level(result: CtdbVerifyResult) -> str:
    """Banner level ("ok" | "warn" | "neutral") for a CTDB verdict.

    Pairs with :func:`ctdb_verdict_line` to colour the label. A *trustworthy*
    match is green; an experimental (not-yet-hardware-validated) match is amber
    — never green, mirroring the wording's refusal to over-claim. Everything
    else (no match, not in DB, decoder missing, error) is neutral grey: those
    are "couldn't confirm", not "failed".
    """
    verdict = result.verdict
    if verdict is Verdict.MATCH:
        return "ok" if result.trustworthy else "warn"
    return "neutral"


def loudness_summary_line(rip_log: object) -> str:
    """One-line album-loudness + partial-accurate footnote, or "" when there's
    nothing to show.

    Pure and **never raises** (it backs a results-pane label populated from a
    best-effort parse): it defends against a missing/oddly-typed
    ``album_loudness`` dict or ``partially_accurate_summary`` and just omits any
    part it can't render. cyanrip logs carry integrated loudness (LUFS), loudness
    range (LU) and true peak (dBFS); whipper logs don't, so this returns "" for
    them (the label then stays hidden). The two facts are joined with " · " so a
    disc that has one but not the other still reads cleanly.
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
                parts.append("Album loudness: " + ", ".join(bits))
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
            text += (
                "  Run  platterpus --compare  for the full table, or  "
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


# Banner colours by level. Muted, theme-neutral hues that read on both light
# and dark Qt palettes; the bold weight does the "look here" work.
_BANNER_COLORS: dict[str, str] = {
    "ok": "#1a7f37",  # green — trustworthy
    "warn": "#9a6700",  # amber — needs a look
    "neutral": "#57606a",  # grey — nothing to assert
}


def _banner_style(level: str) -> str:
    """Qt stylesheet for a verdict label at the given level."""
    color = _BANNER_COLORS.get(level, _BANNER_COLORS["neutral"])
    return f"QLabel {{ color: {color}; font-weight: bold; padding: 2px; }}"


def _basename(path: str) -> str:
    """Render a track filename as just its basename without extension."""
    if not path:
        return ""
    stem = Path(path).stem
    return stem or path


def _copy_is_ok(status: str) -> bool:
    """True when a track's status is a clean copy (EAC's 'Copy OK')."""
    return status.strip().lower() in ("copy ok", "ripped successfully")


def _eac_cell(track: object) -> tuple[str, str]:
    """Render the EAC column for a track: the EAC CRC32 value + an archival mark.

    Returns ``(text, tooltip)``. The value is cyanrip's per-track EAC CRC32 (the
    same "Copy CRC" the companion log carries), so it can be diffed against a
    real EAC rip. The trailing glyph is an at-a-glance, HONEST archival mark —
    never a claim that our log equals an EAC-signed one (Platterpus never signs
    an EAC log):

    * ``✓`` — the track is AccurateRip-verified *and* its copy is OK. The rip as
      a whole is read-offset-corrected with no read errors, so a verified track
      meets the archival bar we can actually check.
    * ``~`` — partially accurate: matched only an offset-variant pressing, not
      the exact AccurateRip checksum (never a false ✓).
    * (no glyph) — a real CRC we recorded but can't externally verify (not in
      the AccurateRip database).

    Never raises (duck-typed via ``getattr`` / the shared match helpers).
    """
    crc = (getattr(track, "copy_crc", "") or "").upper()
    if not crc:
        return "—", "No per-track EAC CRC32 was recorded for this track."
    status = getattr(track, "status", "") or ""
    if track_accuraterip_verified(track) and _copy_is_ok(status):
        return (
            f"{crc}  {_EAC_VERIFIED}",
            "EAC-format CRC32. ✓ = AccurateRip-verified and copy OK; the rip is "
            "read-offset-corrected with no read errors, so this track meets the "
            "archival bar we can verify. NOT a claim of EAC-checksum equivalence "
            "— Platterpus never signs an EAC log.",
        )
    if accuraterip_is_match(getattr(track, "accuraterip_offset", None)):
        return (
            f"{crc}  {_EAC_PARTIAL}",
            "EAC-format CRC32. ~ = partially accurate: matched an offset-variant "
            "pressing, not the exact AccurateRip checksum.",
        )
    return (
        crc,
        "EAC-format CRC32 (compare against a real EAC log). No ✓: this track "
        "didn't match the AccurateRip database — either it isn't present, or the "
        "read didn't match a stored copy — so it can't be independently verified.",
    )


# --- The AccurateRip states, decided in ONE place ---------------------------
#
# AccurateRip can put a track in exactly four states, and the project's dominant
# bug shape is each render surface re-deriving them with its own if-chain (four
# such disagreements shipped in one week — see tests/test_surface_consistency.py).
# Naming the states, and deciding them once in `_ar_state`, means the cell text
# and the cell tooltip cannot drift apart *within* this module; the fitness test
# then guards the harder seam — that this module and the durable EAC-compatible
# log (`eac_log_export._accuraterip_line`) put the same track in the same state.
#
# Values are plain strings, not an Enum, because they are only ever compared
# against these constants and a string keeps the debugger/log output readable.
# The state names and the classifier now live in `platterpus.verdict`, the module
# whose whole purpose is "one definition of verified" — because the EAC log
# renderer needs the identical classification and two copies is how the two
# surfaces came to disagree. Aliased to the old private names so this file's
# rendering code reads unchanged.
_AR_STATE_VERIFIED = AR_STATE_VERIFIED
_AR_STATE_OFFSET_VARIANT = AR_STATE_OFFSET_VARIANT
_AR_STATE_NO_MATCH = AR_STATE_NO_MATCH
_AR_STATE_ABSENT = AR_STATE_ABSENT
_AR_STATE_NO_DATA = AR_STATE_NO_DATA
_AR_STATE_NOT_CHECKED = AR_STATE_NOT_CHECKED
_ar_compared = accuraterip_compared
_ar_state = accuraterip_state


def _ar_cell(
    result: object, *, offset_result: object = None, lookup: str | None = None
) -> str:
    """Render one AccurateRip cell (v1 or v2) for a track.

    ``offset_result`` is the track's +450 offset-variant result (cyanrip's
    "Accurip 450:"). When the standard checksum (``result``) did NOT match but
    the offset-variant DID, the track is a **partially-accurate** match — a
    pressing shifted by the common offset — so we say "offset-variant match (N)"
    rather than leave cyanrip's alarming "not found, either a new pressing, or
    bad rip" on screen for a track that's actually fine. This mirrors the CTDB
    honesty fix: a benign result must never read as a failure.

    The cell text is short because the column is narrow; where short text cannot
    carry the nuance (``in DB, no match``), :func:`_ar_tooltip` supplies it.
    Never raises (duck-typed via ``accuraterip_is_match`` / ``getattr``).
    """
    state = _ar_state(result, offset_result, lookup)
    if state == _AR_STATE_VERIFIED:
        # A genuine database match, format-agnostic across whipper's "Found,
        # exact match" and cyanrip's "accurately ripped, confidence N".
        return f"OK ({getattr(result, 'confidence', None)})"
    if state == _AR_STATE_OFFSET_VARIANT:
        conf = getattr(offset_result, "confidence", None)
        return (
            f"offset-variant match ({conf})"
            if conf is not None
            else "offset-variant match"
        )
    if state == _AR_STATE_NOT_CHECKED:
        # NOT "not in DB" — nobody looked, so the database has no opinion. Saying
        # "no match" here asserted both that the disc is present and that our read
        # disagreed with it, neither of which was established.
        return "not checked"
    if state == _AR_STATE_NO_MATCH:
        # THE FIX (2026-07-31): this used to say "not in DB" — a false claim
        # about a disc the database demonstrably has. Keep it short enough for
        # the column; NO_MATCH_TOOLTIP carries the rest.
        return "in DB, no match"
    if state == _AR_STATE_NO_DATA:
        return "—"
    # Absent: nothing was submitted for this disc, so there was nothing to
    # compare against. Say that plainly instead of cyanrip's alarmist "either a
    # new pressing, or bad rip" (a not-in-DB track is not necessarily a bad rip).
    result_text = getattr(result, "result", "") or ""
    lowered = result_text.lower()
    if not result_text or "not present" in lowered or "not found" in lowered:
        return "not in DB"
    # Unrecognized wording from a future backend: show it verbatim rather than
    # guessing, so an unexpected state is diagnosable instead of mislabelled.
    confidence = getattr(result, "confidence", None)
    return f"{result_text} ({confidence})" if confidence is not None else result_text


def _ar_tooltip(
    result: object, *, offset_result: object = None, lookup: str | None = None
) -> str:
    """The tooltip for one AR cell — empty when the cell text needs no footnote.

    Derived from the same :func:`_ar_state` as the cell text, so a cell can never
    show one state's words with another state's explanation. (It previously was
    re-derived at the call site, which is the same one-fact-many-derivations
    shape this whole module keeps getting bitten by.) Never raises.
    """
    state = _ar_state(result, offset_result, lookup)
    if state == _AR_STATE_OFFSET_VARIANT:
        return OFFSET_VARIANT_TOOLTIP
    if state == _AR_STATE_NOT_CHECKED:
        return NOT_CHECKED_TOOLTIP
    if state == _AR_STATE_NO_MATCH:
        return NO_MATCH_TOOLTIP
    return ""
