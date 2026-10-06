"""The pure half of the offset-override verb: what it looks up and what it says.

Split from :mod:`platterpus.uiscript.offset_verbs` the way the other verb
modules are split from their graders (``permutation_grading``,
``artifact_grading``): the handler presses Start and waits; everything it
decides from a value is here, Qt-free, so it is tested with no window.
"""

from __future__ import annotations

from typing import Final

#: The refusal's window title, as ``RipMixin._on_rip_requested`` sets it.
#:
#: **A second description of one fact, safe only because a test ties them**:
#: ``tests/test_uiscript_offset_refusal.py`` reads the title out of the real
#: method, the way ``runner._RELEASE_PICKER_TITLE`` is tied to the picker. It is
#: not imported because the verb must not pull the main window's module in to
#: compare a string.
OFFSET_REFUSAL_TITLE: Final[str] = "Set up your drive first"

#: The refusal's button that declines the wizard. The wizard is a dialog of its
#: own, and an unattended run must not open it: nobody is there to set a drive up.
DECLINE_LABEL: Final[str] = "No"

#: How long the refusal gets to appear. It is raised synchronously by Start, so
#: it is up within a tick or two on any machine; the margin covers a busy GUI
#: thread, and a wait that runs out is a FAIL that names what was on screen.
OFFSET_REFUSAL_WAIT_S: Final[float] = 30.0


def drive_in_offset_list(window: object) -> tuple[str, int | None]:
    """``(label, offset)`` of the selected drive in the AccurateRip drive list.

    The same lookup the app's first-rip auto-apply uses
    (``_auto_apply_known_offset``), and the one ``set-drive-offset`` and
    ``expect-offset-refusal`` share, so the two verbs cannot disagree about
    whether this drive is listed. ``("", None)`` with no drive selected;
    ``(label, None)`` for a drive the list does not carry.
    """
    picker = getattr(window, "_drive_picker", None)
    database = getattr(window, "_offset_db", None)
    drive = picker.current_drive() if picker is not None else None
    if drive is None or database is None:
        return "", None
    label = f"{drive.vendor.strip()} {drive.model.strip()}".strip()
    return label, database.lookup(drive.vendor, drive.model)


def unreachable_detail(label: str, listed: int) -> str:
    """Why the refusal cannot be reached on this drive. Pure; the step's record.

    Says what would happen instead and that nothing was changed, so a reader of
    the transcript knows both why the step did not run and that the run's offset
    is untouched.
    """
    return (
        f"not run on this equipment: {label} is in the AccurateRip drive list "
        f"({listed:+d}). With the override off the app applies that offset and "
        "rips instead of refusing, which would also rewrite the offset "
        "set-drive-offset set for every later section. The refusal can only be "
        "reached on a drive the list does not carry. Nothing was changed. This is "
        "not a pass (TASKS: Permutations the acceptance test still does not run, (a))."
    )


def start_blocker(window: object, dialog_title: str) -> str:
    """Why Start cannot be pressed now, or ``""``: the refusals ``rip`` makes.

    A dialog already up, a rip already running, or Start disabled (no disc
    identified). The refusal under test is reached only from Start, as a
    person's click reaches it, so a Start that cannot be pressed asks nothing.
    """
    if dialog_title:
        return (
            f"a dialog is waiting for an answer: {dialog_title!r}. Refusing to "
            "press Start behind it."
        )
    if getattr(window, "_rip_worker", None) is not None:
        return "a rip is already running"
    can_start = getattr(getattr(window, "_rip_controls", None), "can_start", None)
    if callable(can_start) and not can_start():
        return (
            "the Start button is not enabled, and the refusal is reached only from "
            "Start: identify the disc first (section E)"
        )
    return ""
