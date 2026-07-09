"""Rip progress widget — live status pane + AccurateRip results.

Three panes stacked vertically:

  Status line + QProgressBar
  Live rip-tool stdout (read-only QPlainTextEdit)
  Verification verdict banner (bold, colour-coded at-a-glance trust headline)
  AccurateRip results table (populated when the rip log lands)
  CTDB verdict line (second, TOC-keyed verification path)

The "View log" / "View report" buttons open the file in an in-app read-only
viewer (avoiding the "Open With" chooser a .log/.platterpus.json triggers on a
fresh KDE); "Open rip folder" defers to the file manager via
QDesktopServices.openUrl().
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
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

# Re-exported so existing imports (and tests) can keep doing
# `from platterpus.ui.rip_progress import accuraterip_verdict`; the canonical
# home is the pure platterpus.verdict module.
from platterpus.verdict import accuraterip_verdict, reconcile_ar_ctdb

__all__ = [
    "RipProgress",
    "accuraterip_verdict",
    "comparison_banner_text",
    "loudness_summary_line",
    "read_effort_summary_line",
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


# Hook so tests can intercept the "open file" action without launching
# a real text editor.
_OpenUrlFn = Callable[[QUrl], bool]
# Hook so tests can intercept the in-app file view without spinning a dialog.
_ViewFileFn = Callable[[Path, str], None]


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
        # The JSON report and the album folder, derived from the log path when a
        # rip finishes (set in set_log_path) — back the "View report" / "Open
        # rip folder" buttons.
        self._report_path: Path | None = None
        self._rip_dir: Path | None = None
        # The last parsed rip log, kept so the CTDB handler (which finishes later,
        # asynchronously) can reconcile its verdict against AccurateRip.
        self._last_rip_log: RipLog | None = None

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
        root.addWidget(self._status_label)

        self._progress_bar: QProgressBar = QProgressBar(self)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        root.addWidget(self._progress_bar)

        # --- Live rip-tool stdout ---
        self._log_view: QPlainTextEdit = QPlainTextEdit(self)
        self._log_view.setReadOnly(True)
        # Cap at a reasonable scrollback so a long rip doesn't blow up
        # memory; the ripper emits thousands of lines per rip.
        self._log_view.setMaximumBlockCount(10_000)
        # A small minimum so this scroll area can be dragged down by the
        # splitter. Without it the panel's minimum height ≈ the whole window
        # at the default size, leaving no slack to redistribute — the splitter
        # handles showed the resize cursor but wouldn't move until the window
        # was maximized (real-user report, 0.4.4). It scrolls, so 64px is fine.
        self._log_view.setMinimumHeight(64)
        root.addWidget(self._log_view, stretch=1)

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
        # Same reasoning as the log view: a small minimum so the splitter can
        # shrink this table and free up drag slack at the default window size.
        self._ar_table.setMinimumHeight(64)
        root.addWidget(self._ar_table, stretch=1)

        # --- CTDB verdict line (second, TOC-keyed verification path) ---
        # Sits directly under the AccurateRip table — a one-liner that only
        # appears when a CTDB verify ran (it's an opt-in, post-rip network
        # check). The audio-CRC algorithm is now hardware-validated (KDD-16,
        # crc.CRC_VALIDATED True), so a match renders green "verified"; the
        # "experimental" wording remains only as a defensive fallback should the
        # gate ever be re-opened (set_ctdb_result reads the flag live).
        self._ctdb_label: QLabel = QLabel("", self)
        self._ctdb_label.setWordWrap(True)
        self._ctdb_label.setVisible(False)
        root.addWidget(self._ctdb_label)

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
        root.addWidget(self._ctdb_reconcile_label)

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
        root.addWidget(self._loudness_label)

        # --- Post-rip output buttons ---
        # Three complementary outputs land beside the FLACs every rip (the
        # "two outputs every time" principle, docs/ux-design-principles #2):
        # cyanrip's human-readable .log, our machine-readable .platterpus.json
        # report, and the album folder that holds both (+ the FLACs/.cue). All
        # three buttons stay disabled until a rip finishes and a log path is
        # known (set_log_path), then enable together.
        button_row = QHBoxLayout()
        button_row.addStretch(1)
        self._view_log_button: QPushButton = QPushButton("View log", self)
        self._view_log_button.setEnabled(False)
        self._view_log_button.clicked.connect(self._on_view_log_clicked)
        button_row.addWidget(self._view_log_button)
        self._view_report_button: QPushButton = QPushButton("View report", self)
        self._view_report_button.setEnabled(False)
        self._view_report_button.clicked.connect(self._on_view_report_clicked)
        button_row.addWidget(self._view_report_button)
        self._open_folder_button: QPushButton = QPushButton("Open rip folder", self)
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
        self._open_folder_button.setAccessibleName("Open the folder containing the rip")

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
        self._view_log_button.setEnabled(False)
        self._view_report_button.setEnabled(False)
        self._open_folder_button.setEnabled(False)
        self._log_path = None
        self._report_path = None
        self._rip_dir = None
        self._last_rip_log = None

    def append_log_line(self, line: str) -> None:
        """Append one line of whipper output to the streaming log view."""
        self._log_view.appendPlainText(line)

    def set_progress(self, overall: float, task: float) -> None:
        """Update both progress bars.

        `overall` is the whole-rip percentage (monotonic); `task` is the
        current operation's own 0-100%. The status label is driven
        separately via `set_status` (fed from the rip worker's phase
        signal), so the label stays meaningful during phases that have no
        numeric percent.
        """
        self._overall_bar.setValue(int(overall))
        self._progress_bar.setValue(int(task))

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

    def set_rip_log(self, rip_log: RipLog) -> None:
        """Populate the AccurateRip table + verdict banner from a parsed log."""
        # Kept so the async CTDB verdict can reconcile itself against AccurateRip.
        self._last_rip_log = rip_log
        message, level = accuraterip_verdict(rip_log)
        if message:
            self._verdict_banner.setText(message)
            self._verdict_banner.setStyleSheet(_banner_style(level))
            self._verdict_banner.setVisible(True)
        else:
            self._verdict_banner.setVisible(False)

        # Read-effort early warning (per-track "hard to read"). Hidden when clean.
        effort = read_effort_summary_line(rip_log)
        self._read_effort_label.setText(effort)
        self._read_effort_label.setVisible(bool(effort))

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
            v1_item = QTableWidgetItem(
                _ar_cell(track.accuraterip_v1, offset_result=offset)
            )
            v2_item = QTableWidgetItem(
                _ar_cell(track.accuraterip_v2, offset_result=offset)
            )
            # When a track matched only the offset-variant pressing, explain what
            # that means (and the re-rip caveat) right on the cell — #4 of the
            # 2026-07-09 trust improvements.
            if not track_accuraterip_verified(track) and accuraterip_is_match(offset):
                v1_item.setToolTip(OFFSET_VARIANT_TOOLTIP)
                v2_item.setToolTip(OFFSET_VARIANT_TOOLTIP)
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

    def set_ctdb_status(self, text: str) -> None:
        """Show an in-progress CTDB line (e.g. 'Verifying against CTDB…')."""
        self._ctdb_label.setText(text)
        self._ctdb_label.setVisible(True)

    def set_ctdb_result(self, result: CtdbVerifyResult) -> None:
        """Render the final CTDB verdict under the AccurateRip table.

        The audio-CRC algorithm is hardware-validated (KDD-16), so a trustworthy
        match renders as verified. If that gate is ever re-opened
        (``result.trustworthy`` False), a match falls back to an "experimental"
        label — we never claim a verification the algorithm can't stand behind.
        """
        self._ctdb_label.setText(ctdb_verdict_line(result))
        self._ctdb_label.setStyleSheet(_banner_style(ctdb_verdict_level(result)))
        self._ctdb_label.setVisible(True)

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

    def set_log_path(self, path: Path | None) -> None:
        """Enable the post-rip output buttons from the rip log's path.

        The log path locates all three outputs: the ``.log`` itself, the
        ``.platterpus.json`` report beside it, and their parent album folder.
        Passing None (or "") disables all three (used when no log was written).
        """
        from platterpus.rip_report import report_path_for

        if path is None or str(path) == "":
            self._log_path = None
            self._report_path = None
            self._rip_dir = None
            self._view_log_button.setEnabled(False)
            self._view_report_button.setEnabled(False)
            self._open_folder_button.setEnabled(False)
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

    # --- Internals ----------------------------------------------------------

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
        if self._log_path is None:
            return
        # In-app viewer, not openUrl: a .log has no default app on a fresh KDE.
        self._view_file(self._log_path, f"Rip log — {self._log_path.name}")

    def _on_view_report_clicked(self) -> None:
        if self._report_path is None:
            return
        self._view_file(self._report_path, f"Rip report — {self._report_path.name}")

    def _on_open_folder_clicked(self) -> None:
        if self._rip_dir is None:
            return
        # A folder DOES have a default handler (the file manager), so openUrl is
        # the right call here — and revealing the folder is the whole point.
        self._open_url(QUrl.fromLocalFile(str(self._rip_dir)))


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
            return "CTDB: no match — this rip differs from the database entries"
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
        partial = getattr(rip_log, "partially_accurate_summary", "") or ""
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


def _ar_cell(result: object, *, offset_result: object = None) -> str:
    """Render one AccurateRip cell (v1 or v2) for a track.

    ``offset_result`` is the track's +450 offset-variant result (cyanrip's
    "Accurip 450:"). When the standard checksum (``result``) did NOT match but
    the offset-variant DID, the track is a **partially-accurate** match — a
    pressing shifted by the common offset — so we say "offset-variant match (N)"
    rather than leave cyanrip's alarming "not found, either a new pressing, or
    bad rip" on screen for a track that's actually fine. This mirrors the CTDB
    honesty fix: a benign result must never read as a failure. Never raises
    (duck-typed via ``accuraterip_is_match`` / ``getattr``).
    """
    # Partially-accurate: standard v1/v2 didn't match, but the offset variant did.
    if not accuraterip_is_match(result) and accuraterip_is_match(offset_result):
        conf = getattr(offset_result, "confidence", None)
        return (
            f"offset-variant match ({conf})"
            if conf is not None
            else "offset-variant match"
        )
    if result is None:
        return "—"
    confidence = getattr(result, "confidence", None)
    result_text = getattr(result, "result", "") or ""
    # A genuine database match (confidence >= 1), format-agnostic across whipper's
    # "Found, exact match" and cyanrip's "accurately ripped, confidence N".
    if accuraterip_is_match(result):
        return f"OK ({confidence})"
    # Not matched and no offset match — it's simply absent from the database. Say
    # that plainly instead of cyanrip's alarmist "either a new pressing, or bad
    # rip" (a not-in-DB track is not necessarily a bad rip).
    lowered = result_text.lower()
    if not result_text or "not present" in lowered or "not found" in lowered:
        return "not in DB"
    return f"{result_text} ({confidence})" if confidence is not None else result_text
