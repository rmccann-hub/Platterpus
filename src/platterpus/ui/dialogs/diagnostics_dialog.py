# SPDX-License-Identifier: GPL-3.0-only
"""**Help → Copy diagnostics** — one selectable, copyable block for a bug report.

**Why this exists.** An audit (2026-08-04) found that the UI had *no* export, no
bundle and no copy-diagnostics action anywhere — the only clipboard call in the whole
UI tree copied a *package search string*. Worse, the one place a cyanrip fatal
sentence is ever displayed (the rip pane's status label) had no
``setTextInteractionFlags``, so the single most useful line in the app could not even
be selected with a mouse.

The per-rip ``.platterpus.json`` is the real bundle and it is excellent, but it is
per-rip and reachable only through **View report** in the rip pane. Two situations it
cannot cover, and both are exactly when a user needs to report something:

* the failure happened **before or outside** a rip — setup, the dependency check, an
  update, a drive probe;
* the user has no rip folder to hand and is being asked, over a chat window, "what
  does it say?"

So this dialog renders what the process knows *right now*: the version pair the
handshake approved, the live environment, and **every diagnostic the collector has
recorded this session** — the same items the report's ``diagnostics`` block carries,
because they come from the same collector rather than a second rendering of it.

**No secrets, and nothing the user has not already seen.** This is built from the
diagnostics collector, the build/environment probe and the log path — the same facts
already written to ``log.txt``. It deliberately does not read the log file itself: a
log can be long, and quietly putting a whole file on the clipboard is not what a
"Copy" button implies.

Pure Qt widget work on the GUI thread: everything shown is already in memory (the
collector is a list; the environment probe is cached by the caller), so there is no
blocking work here and no worker to abandon — the dialog-that-does-blocking-work trap
from CLAUDE.md does not apply, and it must stay that way.
"""

from __future__ import annotations

import logging

from PySide6.QtWidgets import (
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from platterpus import __version__, build_info, diagnostics, handshake_approval
from platterpus.paths import LOG_PATH
from platterpus.ui.dialogs.centering import CenteredDialog

log = logging.getLogger(__name__)

#: How many characters of the rendered report the text box holds. Generous — a
#: diagnostics list is text — but bounded, because a pathological session could
#: otherwise make the dialog slow to open. Truncation is *stated*, never silent.
_MAX_CHARS: int = 200_000


def build_diagnostics_text() -> str:
    """Render the copyable report. **Pure and never raises.**

    Separate from the dialog so it is unit-testable without a QApplication, and so
    the same text can be reused (a future ``--diagnostics`` CLI flag would call this
    rather than reimplementing it — the mistake this project keeps paying for is a
    second rendering of the same facts).
    """
    lines: list[str] = ["=== Platterpus diagnostics ==="]

    # 1. The version PAIR, ours and the ripper's, because a support question is
    #    almost always about the pair rather than either half (CLAUDE.md rule 12).
    try:
        lines += ["", handshake_approval.version_pair_line()]
    except Exception:  # noqa: BLE001 — a diagnostics view must never fail to open
        log.exception("diagnostics view: could not render the version pair")
        lines += ["", f"Platterpus {__version__} (version pair unavailable)"]

    # 2. The environment. First question of every bug report.
    try:
        env = build_info.environment_report()
        # A plain mapping view, because a `TypedDict` cannot be indexed by a loop
        # variable (its keys must be literals). Converting rather than annotating
        # the loop away: the point here is to render *whatever* the environment
        # block carries, including a field added after this file was written, so
        # generic iteration is the correct shape — and a hand-listed set of keys
        # would be one more completeness promise that decays by omission.
        env_items: dict[str, object] = dict(env)
        lines += ["", "--- Environment ---"]
        for key in sorted(env_items):
            if key == "dependencies":
                continue  # rendered below, one row per tool
            lines.append(f"{key}: {env_items[key]}")
        deps = env_items.get("dependencies")
        if isinstance(deps, dict) and deps:
            lines += ["", "--- Dependencies ---"]
            for tool in sorted(deps):
                info = deps[tool]
                if isinstance(info, dict):
                    lines.append(
                        f"{tool}: present={info.get('present')} "
                        f"version={info.get('version') or '(unknown)'} "
                        f"min_version_met={info.get('min_version_met')}"
                    )
        else:
            # SAY SO. A missing dependency section is "the launch check has not run
            # yet", which is a real answer and reads nothing like "no dependencies".
            lines += [
                "",
                "--- Dependencies ---",
                "(not probed yet this session — the launch-time check had not "
                "completed, or it crashed; see the diagnostics below)",
            ]
    except Exception:  # noqa: BLE001
        log.exception("diagnostics view: could not render the environment")
        lines += ["", "--- Environment ---", "(unavailable)"]

    # 3. Every diagnostic recorded this session — the same items the rip report
    #    carries, read from the same collector so the two cannot disagree.
    try:
        block = diagnostics.to_report_block()
        lines += [
            "",
            "--- Diagnostics ---",
            f"errors: {block['error_count']}  warnings: {block['warning_count']}  "
            f"info: {block['info_count']}",
            f"worst: {block['worst_severity'] or 'none recorded'}",
            f"scope: {block['scope']}",
        ]
        if block["truncated"]:
            lines.append(
                f"NOTE: the list is capped — {block['dropped_count']} item(s) were "
                "dropped (head and tail kept)"
            )
        items = block["items"]
        if not items:
            # Not silence, and not a clean bill of health. Those are different
            # claims and this is the one place a reader might conflate them.
            lines.append(
                "(nothing recorded this session — which means nothing REPORTED a "
                "problem, not that everything was verified)"
            )
        for item in items:
            lines.append("")
            lines.append(f"[{item['severity']}] {item['code']} @ {item['at'] or '?'}")
            lines.append(f"  {item['message']}")
            if item.get("tool"):
                lines.append(f"  tool: {item['tool']}")
            # Tri-state, spelled out: "no exit code" and "exit 0" must not look
            # the same here either.
            if item.get("exit_code") is not None:
                lines.append(f"  exit code: {item['exit_code']}")
            elif item.get("argv"):
                lines.append("  exit code: none (no child was reaped)")
            if item.get("argv"):
                lines.append(f"  argv: {' '.join(item['argv'])}")
            if item.get("track") is not None:
                lines.append(f"  track: {item['track']}")
            if item.get("where"):
                lines.append(f"  where: {item['where']}")
            if item.get("detail"):
                lines.append("  detail:")
                lines += [f"    {ln}" for ln in str(item["detail"]).splitlines()]
    except Exception:  # noqa: BLE001
        log.exception("diagnostics view: could not render the diagnostics list")
        lines += ["", "--- Diagnostics ---", "(unavailable)"]

    lines += [
        "",
        "--- Where the rest lives ---",
        f"app log: {LOG_PATH}",
        "per-rip report: a `.platterpus.json` beside each album's audio — it embeds "
        "the ripper's own output and that session's debug log.",
    ]

    text = "\n".join(lines) + "\n"
    if len(text) > _MAX_CHARS:
        dropped = len(text) - _MAX_CHARS
        # Stated, and it keeps the HEAD here on purpose — unlike a tool's output,
        # this document's most important parts (versions, environment, the counts)
        # are at the top, and the diagnostics that follow are already ordered
        # oldest-first with the collector's own head-and-tail cap applied.
        text = text[:_MAX_CHARS] + (
            f"\n… [{dropped} character(s) omitted — the full detail is in {LOG_PATH}]\n"
        )
    return text


class DiagnosticsDialog(CenteredDialog):
    """A read-only, selectable, copyable diagnostics report.

    Inherits :class:`~platterpus.ui.dialogs.centering.CenteredDialog` like every
    other dialog in the app — which is not decoration here of all places: it is
    what gives this dialog the "presented"/"closed" log lines, and a *diagnostics*
    window that leaves no trace of having been opened is the joke telling itself.
    It was the one straight ``QDialog`` subclass left, found by a sweep rather than
    by memory; ``tests/test_dialog_lifecycle_logging.py`` now keeps it that way.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Diagnostics")
        # Sized so a typical report is readable without resizing; the text box
        # scrolls rather than the dialog growing without bound.
        self.resize(760, 560)

        root = QVBoxLayout(self)
        intro = QLabel(
            "Everything Platterpus knows about this session: the version pair, the "
            "environment, and every problem it noticed. Copy this into a bug report.",
            self,
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        self._text: QPlainTextEdit = QPlainTextEdit(self)
        self._text.setReadOnly(True)
        # Monospace: the argv lines and the captured tool output are the point, and
        # proportional text makes a command line hard to read back.
        self._text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._text.setPlainText(build_diagnostics_text())
        self._text.setAccessibleName("Diagnostics report")
        root.addWidget(self._text, 1)

        buttons = QHBoxLayout()
        self._copy_button: QPushButton = QPushButton("Copy to clipboard", self)
        self._copy_button.clicked.connect(self._on_copy)
        buttons.addWidget(self._copy_button)
        self._copied_label: QLabel = QLabel("", self)
        buttons.addWidget(self._copied_label)
        buttons.addStretch(1)
        root.addLayout(buttons)

        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        box.rejected.connect(self.reject)
        # Close must also work from the Accept role on platforms that map it there,
        # and Esc already triggers `rejected`.
        box.accepted.connect(self.accept)
        root.addWidget(box)

    def text(self) -> str:
        """The rendered report. For tests and for a caller that wants to re-use it."""
        return self._text.toPlainText()

    def _on_copy(self) -> None:
        """Put the report on the clipboard and *say so*.

        A copy button that gives no feedback leaves the user unsure whether it
        worked, so they click it again — the same ambiguity this whole subsystem
        exists to remove, in miniature.
        """
        from PySide6.QtWidgets import QApplication

        clipboard = QApplication.clipboard()
        if clipboard is None:
            # Headless / no clipboard service. Say it rather than appearing to work.
            self._copied_label.setText("No clipboard is available on this system.")
            log.warning("diagnostics dialog: no clipboard available")
            return
        clipboard.setText(self.text())
        self._copied_label.setText("Copied.")
