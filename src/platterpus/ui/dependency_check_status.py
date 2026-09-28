"""What the dependency check says to a person: while it runs, and when it lands.

**Why this exists.** The maintainer, 2026-09-28: Setup & Updates → *Check
dependencies* "seems to freeze, not respond, or give no error". The check runs
off the GUI thread, so the window never froze — but it LOOKED dead four ways:
nothing on screen said a check was running; a second click was silently ignored;
a wedged container meant minutes with no result; and a result that arrived
while another dialog was open could be dropped with only a log line. Every one
of those is a sentence that was never shown, so the sentences live here.

**Pure text, no widgets.** Each function returns a string, so every message is
testable without a display, and the status bar and the Setup & Updates window
read the SAME words: `dependency_summary_line` is the one verdict both show, and
`deps.manager.describe_unchecked` is the one wording of an incomplete check that
every surface uses. Two surfaces answering one question with two functions is the
shape this project keeps paying for.

**Tri-state, and never "all present" about a check that did not finish.** A check
that stopped early is marked ⚠ and names what it did not reach; it is not
allowed to borrow the ✓ of the tools it did.
"""

from __future__ import annotations

from typing import Final

from platterpus.deps.manager import describe_unchecked
from platterpus.paths import LOG_PATH

#: The status marker vocabulary. **Never colour alone** — around 8% of men have
#: red/green colour-vision deficiency, and a greyscale screenshot or a
#: forced-colors theme drops hue entirely, so every level carries a glyph.
OK_MARK: Final[str] = "✓"
WARN_MARK: Final[str] = "⚠"
INFO_MARK: Final[str] = "ⓘ"

#: Where a user re-runs the check, as the menu path they would follow.
RERUN_PATH: Final[str] = "Tools → Setup & Updates… → Check dependencies"


def _item_name(item: object) -> str:
    """The name to show for a missing item.

    A real ``MissingItem`` carries only ``spec`` and ``probe``, so the spec's
    ``display_name`` is the name. The Setup & Updates line used to read a
    ``name`` attribute that no real item has, so every missing tool it listed
    rendered as ``?``; ``name`` stays as the fallback for callers that pass one.
    """
    spec = getattr(item, "spec", None)
    return str(
        getattr(spec, "display_name", None)
        or getattr(item, "name", None)
        or getattr(spec, "dep_id", None)
        or "?"
    )


def dependency_summary_line(report: object | None) -> str:
    """One line describing the last dependency probe, for a person.

    **Tri-state, like every other verdict here.** "We have not looked yet" is a
    real answer and must not render as "nothing is wrong": a window that says
    `✓ All present` before any probe has run would be asserting something it
    cannot know, which is the failure mode this project keeps a marker
    vocabulary for. The same holds for a check that stopped part-way: it reads
    ⚠ and says what it did not check, whatever the checked tools said.
    """
    if report is None:
        return f"{INFO_MARK} Not checked yet in this session."
    missing = list(getattr(report, "missing", []) or [])
    required = [
        m for m in missing if not getattr(getattr(m, "spec", None), "optional", False)
    ]
    optional = [
        m for m in missing if getattr(getattr(m, "spec", None), "optional", False)
    ]
    incomplete = describe_unchecked(report)
    parts: list[str] = []
    if required:
        names = ", ".join(_item_name(m) for m in required)
        parts.append(f"{WARN_MARK} {len(required)} required missing: {names}.")
    if incomplete:
        # Leads with its own marker when nothing required is missing, so an
        # incomplete check is never a ✓ line.
        parts.append(incomplete if required else f"{WARN_MARK} {incomplete}")
    elif not required:
        parts.append(f"{OK_MARK} All required tools present.")
    if optional:
        names = ", ".join(_item_name(m) for m in optional)
        parts.append(f"Optional not installed: {names}.")
    return " ".join(parts)


def running_message(deadline_s: float) -> str:
    """Shown the moment a check the user asked for starts."""
    return (
        "Checking dependencies… The first check of a session starts the ripping "
        "container and can take up to a minute; the check gives up after "
        f"{deadline_s:g} s at most."
    )


def already_running_message() -> str:
    """Shown when the user asks for a check while one is already running."""
    return (
        f"{INFO_MARK} A dependency check is already running, so a second one was "
        "not started. Its result will be shown when it finishes."
    )


def outcome_message(report: object | None) -> str:
    """Replaces the running message when the check lands.

    ``report`` is None only when the check itself crashed — never "no tools".
    The caller stamps the time, so the sentence carries no clock of its own.
    """
    if report is None:
        return (
            f"{WARN_MARK} The dependency check stopped with an unexpected error, so "
            f"nothing is known about the tools. The error is in {LOG_PATH}."
        )
    return f"Dependency check finished: {dependency_summary_line(report)}"


def incomplete_background_message(report: object) -> str:
    """For a check nobody clicked (the launch check) that did not finish.

    Such a check stays silent when it completes — optional tools must not nag —
    but one that stopped part-way leaves the ripper's state unknown, and a
    one-line status message is the least that can say so without a dialog.
    """
    return (
        f"{WARN_MARK} The background dependency check did not finish. "
        f"{describe_unchecked(report)} Run it again from {RERUN_PATH}."
    )


def waiting_for_dialog_message() -> str:
    """The check has landed, but another dialog must be answered first."""
    return (
        f"{INFO_MARK} The dependency check has finished. Its result will be shown "
        "when the dialog that is open now is closed."
    )


def gave_up_message() -> str:
    """The result waited for another dialog and was not shown; say where it is."""
    return (
        f"{WARN_MARK} The dependency check finished while another dialog stayed "
        "open, so its result was not shown. Tools → Setup & Updates… shows the "
        f"result; {RERUN_PATH} runs it again."
    )


def overdue_message(waited_s: float) -> str:
    """The backstop: the check is still running well past its own deadline.

    Only reachable if a probe ignores the deadline — every probe the registry
    has today is capped by it — so this sentence exists for the day one does
    not, and says plainly that the window is still working.
    """
    return (
        f"{WARN_MARK} The dependency check has been running for {waited_s:g} s and "
        "did not stop when it should have. The window still works; the check will "
        f"report if it ever finishes. Details are in {LOG_PATH}."
    )
