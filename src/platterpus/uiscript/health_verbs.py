"""``expect-installed``: the acceptance run reports on the installation too.

The owner, 2026-11-25: the Full run *"should include everything, not just how the
rip runs. now the priority might not be same, but it should be reported."* That
day's reinstall left the menu entry and the Desktop icon pointing at a file that
had moved and logged a traceback on close, and no step of the run could have seen
either. This verb asks, one aspect per step:

* ``shortcuts`` — the menu entry, the uninstaller's entry and the Desktop icon
  each launch the installed AppImage, which is there and executable;
* ``tools`` — the tools setup exports to ``~/.local/bin`` are there;
* ``drive`` — the selected drive has a saved read offset and a cache verdict for
  its current firmware (the owner's rule of 2026-11-12: drive facts are measured
  once, up front, and saved);
* ``log`` — this launch's log holds no Python traceback;
* ``diagnostics`` — what the app recorded as errors and warnings this launch,
  reported as info (a run provokes some on purpose, so a count is not a verdict).

The checks are pure (`platterpus.install_health`); this mixin only reads the
window and records. Nothing here starts a process, so it runs on the GUI thread
in microseconds. Its section's severity is declared before any run
(`docs/testing.md` → *Acceptance severity*, section S).
"""

from __future__ import annotations

import logging
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

from platterpus import install_health
from platterpus.paths import APP_NAME
from platterpus.uiscript.report import Outcome

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

    from platterpus.uiscript.script import Step

log = logging.getLogger(__name__)

#: The aspects ``expect-installed`` knows, in the order the run asks them.
ASPECTS: tuple[str, ...] = ("shortcuts", "tools", "drive", "log", "diagnostics")


def installed_appimage() -> Path | None:
    """Where the running AppImage lives now, or ``None`` if not an AppImage.

    ``$APPIMAGE`` names the path the app was launched from; after the first-run
    offer moves the file into ``~/Applications`` that path is gone, and the file
    is there instead (the owner's log of 2026-11-25).
    """
    from platterpus import appimage_integration as ai

    launched = ai.appimage_path()
    if launched is None:
        return None
    if not launched.exists():
        moved = ai.APPLICATIONS_DIR / launched.name
        if moved.exists():
            return moved
    return launched


class HealthVerbsMixin:
    """``expect-installed <aspect>``."""

    if TYPE_CHECKING:
        _window: QWidget

        def _record(
            self,
            step: Step,
            outcome: Outcome,
            detail: str = "",
            *,
            elapsed: float = 0.0,
            artifact: str = "",
            declined_by_size: bool = False,
        ) -> None: ...

        def _session_log(self) -> tuple[list[str] | None, str]: ...

    def _do_expect_installed(self, step: Step) -> None:
        """``expect-installed <aspect>``: one fact about the installation."""
        aspect = step.args[0] if step.args else ""
        if aspect not in ASPECTS:
            self._record(
                step,
                Outcome.ERROR,
                f"{aspect!r} is not an aspect; use one of {', '.join(ASPECTS)}",
            )
            return
        if aspect == "diagnostics":
            self._record(step, Outcome.INFO, self._diagnostics_summary())
            return
        if aspect == "log":
            self._grade_log(step)
            return
        findings = self._findings(aspect)
        self._record_findings(step, aspect, findings)

    def _findings(self, aspect: str) -> list[install_health.Finding]:
        """The findings for a file-reading aspect. Never raises."""
        from platterpus import appimage_integration as ai
        from platterpus import tool_paths

        try:
            if aspect == "shortcuts":
                return install_health.check_shortcuts(
                    installed_appimage(),
                    desktop_dir=ai.DESKTOP_DIR,
                    desktop_folder=ai.DESKTOP_FOLDER,
                    desktop_id=ai.DESKTOP_ID,
                    uninstall_name=f"{APP_NAME}-uninstall",
                )
            if aspect == "tools":
                return install_health.check_tools(Path(tool_paths.exported_tools_dir()))
            return self._drive_findings()
        except Exception as exc:  # noqa: BLE001 — a check that cannot run is reported
            log.exception("expect-installed %s could not run", aspect)
            return [install_health.Finding(False, f"the check could not run: {exc!r}")]

    def _drive_findings(self) -> list[install_health.Finding]:
        """The selected drive's saved offset and cache verdict, read off the window."""
        from platterpus import cache_check_plan

        window = self._window
        picker = getattr(window, "_drive_picker", None)
        drive = picker.current_drive() if picker is not None else None
        if drive is None:
            return install_health.check_drive_facts(
                "", None, cache_check_plan.MEASURED, False
            )
        # The drive mixin's own readers, the ones drive setup uses.
        profiles = getattr(window, "_drive_profiles", None)
        fingerprint_for = getattr(window, "_fingerprint_for", None)
        selected_offset = getattr(window, "_selected_drive_offset", None)
        if profiles is None or fingerprint_for is None or selected_offset is None:
            return [install_health.Finding(False, "the window has no drive profiles")]
        profile = profiles.get(fingerprint_for(drive)[0])
        state = cache_check_plan.verdict_state(profile, getattr(drive, "release", ""))
        saved = selected_offset().record is not None
        label = (
            " ".join(
                part
                for part in (getattr(drive, "vendor", ""), getattr(drive, "model", ""))
                if part
            )
            or "the selected drive"
        )
        return install_health.check_drive_facts(
            label, state, cache_check_plan.MEASURED, saved
        )

    def _record_findings(
        self, step: Step, aspect: str, findings: list[install_health.Finding]
    ) -> None:
        """PASS when every judged finding held; FAIL naming each that did not."""
        failed = [f.text for f in findings if f.ok is False]
        lines = "\n".join(
            ("✓ " if f.ok else "✗ " if f.ok is False else "ⓘ ") + f.text
            for f in findings
        )
        if failed:
            self._record(
                step, Outcome.FAIL, f"{aspect}: {len(failed)} problem(s)\n{lines}"
            )
        elif any(f.ok for f in findings):
            self._record(step, Outcome.PASS, f"{aspect}:\n{lines}")
        else:
            # Nothing to judge (not an AppImage): reported, never a pass.
            self._record(step, Outcome.INFO, f"{aspect}: nothing to check\n{lines}")

    def _grade_log(self, step: Step) -> None:
        """FAIL on any traceback this launch logged; INFO if the log is unread."""
        lines, kept = self._session_log()
        if lines is None:
            self._record(step, Outcome.INFO, f"not determined: {kept}")
            return
        total = install_health.count_tracebacks(lines)
        if total:
            shown = install_health.find_tracebacks(lines)
            self._record(
                step,
                Outcome.FAIL,
                f"this launch logged {total} traceback(s) ({kept}); the first:\n"
                + "\n".join(shown),
            )
            return
        self._record(step, Outcome.PASS, f"no traceback in this launch's log ({kept})")

    @staticmethod
    def _diagnostics_summary() -> str:
        """Errors and warnings recorded this launch, by code. Never raises."""
        from platterpus import diagnostics

        try:
            items = diagnostics.default_log().items()
        except Exception as exc:  # noqa: BLE001 — a report must not crash the run
            return f"the diagnostics could not be read: {exc!r}"
        if not items:
            return "no error or warning was recorded this launch"
        by_severity = Counter(str(item.severity) for item in items)
        by_code = Counter(f"{item.severity} {item.code}" for item in items)
        head = ", ".join(f"{n} {s}" for s, n in sorted(by_severity.items()))
        body = "\n".join(f"  {n} × {key}" for key, n in sorted(by_code.items()))
        return (
            f"recorded this launch: {head} (some are provoked on purpose by the "
            f"run's own steps, so this is a report, not a verdict):\n{body}"
        )
