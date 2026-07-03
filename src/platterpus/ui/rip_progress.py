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
from platterpus.parsers.rip_log import RipLog

# Re-exported so existing imports (and tests) can keep doing
# `from platterpus.ui.rip_progress import accuraterip_verdict`; the canonical
# home is the pure platterpus.verdict module.
from platterpus.verdict import accuraterip_verdict

__all__ = ["RipProgress", "accuraterip_verdict", "loudness_summary_line"]

log = logging.getLogger(__name__)

# AR table column layout. The brief calls out per-track AR confidence;
# we expose v1 and v2 separately since they can disagree.
_AR_COLUMNS: list[str] = ["#", "Title", "Status", "AR v1", "AR v2"]
_AR_COL_NUMBER: int = 0
_AR_COL_TITLE: int = 1
_AR_COL_STATUS: int = 2
_AR_COL_V1: int = 3
_AR_COL_V2: int = 4


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
        self._log_path: Path | None = None
        # The JSON report and the album folder, derived from the log path when a
        # rip finishes (set in set_log_path) — back the "View report" / "Open
        # rip folder" buttons.
        self._report_path: Path | None = None
        self._rip_dir: Path | None = None

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
        for col in (_AR_COL_NUMBER, _AR_COL_STATUS, _AR_COL_V1, _AR_COL_V2):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        # Same reasoning as the log view: a small minimum so the splitter can
        # shrink this table and free up drag slack at the default window size.
        self._ar_table.setMinimumHeight(64)
        root.addWidget(self._ar_table, stretch=1)

        # --- CTDB verdict line (second, TOC-keyed verification path) ---
        # Sits directly under the AccurateRip table — a one-liner that only
        # appears when a CTDB verify ran (it's an opt-in, post-rip network
        # check). Until the audio-CRC algorithm is hardware-validated a match
        # is shown as "experimental" (KDD-16); see set_ctdb_result.
        self._ctdb_label: QLabel = QLabel("", self)
        self._ctdb_label.setWordWrap(True)
        self._ctdb_label.setVisible(False)
        root.addWidget(self._ctdb_label)

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
        self._ar_table.setAccessibleName("Per-track AccurateRip results")
        self._ctdb_label.setAccessibleName("CTDB verification result")
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
        self._ar_table.setRowCount(0)
        self._ctdb_label.clear()
        self._ctdb_label.setVisible(False)
        self._loudness_label.clear()
        self._loudness_label.setVisible(False)
        self._view_log_button.setEnabled(False)
        self._view_report_button.setEnabled(False)
        self._open_folder_button.setEnabled(False)
        self._log_path = None
        self._report_path = None
        self._rip_dir = None

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
        """Set the status label (start/finish + per-phase updates)."""
        self._status_label.setText(text)

    def set_rip_log(self, rip_log: RipLog) -> None:
        """Populate the AccurateRip table + verdict banner from a parsed log."""
        message, level = accuraterip_verdict(rip_log)
        if message:
            self._verdict_banner.setText(message)
            self._verdict_banner.setStyleSheet(_banner_style(level))
            self._verdict_banner.setVisible(True)
        else:
            self._verdict_banner.setVisible(False)

        tracks = rip_log.tracks
        self._ar_table.setRowCount(len(tracks))
        for row, track in enumerate(tracks):
            number_item = QTableWidgetItem(str(track.number))
            title_item = QTableWidgetItem(_basename(track.filename))
            status_item = QTableWidgetItem(track.status or "")
            v1_item = QTableWidgetItem(_ar_cell(track.accuraterip_v1))
            v2_item = QTableWidgetItem(_ar_cell(track.accuraterip_v2))
            self._ar_table.setItem(row, _AR_COL_NUMBER, number_item)
            self._ar_table.setItem(row, _AR_COL_TITLE, title_item)
            self._ar_table.setItem(row, _AR_COL_STATUS, status_item)
            self._ar_table.setItem(row, _AR_COL_V1, v1_item)
            self._ar_table.setItem(row, _AR_COL_V2, v2_item)

        # Album loudness + partial-accurate footnote (data cyanrip already
        # logged; previously only in the JSON). Hidden when there's nothing.
        summary = loudness_summary_line(rip_log)
        self._loudness_label.setText(summary)
        self._loudness_label.setVisible(bool(summary))

    def set_ctdb_status(self, text: str) -> None:
        """Show an in-progress CTDB line (e.g. 'Verifying against CTDB…')."""
        self._ctdb_label.setText(text)
        self._ctdb_label.setVisible(True)

    def set_ctdb_result(self, result: CtdbVerifyResult) -> None:
        """Render the final CTDB verdict under the AccurateRip table.

        A match that isn't yet trustworthy (the audio-CRC algorithm is not
        hardware-validated, KDD-16) is labelled experimental — we never claim
        a verification the algorithm can't yet stand behind.
        """
        self._ctdb_label.setText(ctdb_verdict_line(result))
        self._ctdb_label.setStyleSheet(_banner_style(ctdb_verdict_level(result)))
        self._ctdb_label.setVisible(True)

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

    Pure function (no widget) so it's unit-testable. The MATCH wording is the
    important safety case: until ``result.trustworthy`` (the CRC algorithm is
    hardware-validated, KDD-16) a match is spelled out as *experimental*, never
    as a plain "verified" — mirroring the rip's own "never claim a check that
    didn't run" rule.
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
        return "CTDB: no match — this rip differs from the database entries"
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


def _ar_cell(result: object) -> str:
    """Render an AccurateRipResult (or None) for one cell."""
    if result is None:
        return "—"
    # Don't import the dataclass to avoid circular fuss; rely on duck
    # typing — RipLog hands us AccurateRipResult instances directly.
    confidence = getattr(result, "confidence", None)
    result_text = getattr(result, "result", "") or ""
    if confidence is None:
        return result_text or "—"
    if "exact match" in result_text:
        return f"OK ({confidence})"
    if "not present" in result_text.lower():
        return "not in DB"
    return f"{result_text} ({confidence})"
