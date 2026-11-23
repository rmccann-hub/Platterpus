"""How a finished or failed rip is worded on the status line and the banner.

**Why this module exists** (UX review of 0.7.127, findings V1 and E1, fixed on
the owner's word of 2026-11-17). After a rip that AccurateRip called WRONG on
two of fourteen tracks, the status line read *"Done — 12/14 tracks ripped
cleanly. ⚠ …"* under an amber banner: the first word a user reads said the job
was fine. The banner said what was wrong and never said what to do about it.
And a rip that failed outright was one grey line, *"Error: …"*, with no marker
and nowhere to click.

**What this module decides, and what it does not.** It decides only the
*wording around* a verdict: the status line's first words, the banner's next
step, and the failure banner's sentence. The verdict itself (which tracks
AccurateRip contradicts, what level the banner is at) is decided where it
always was, in :mod:`platterpus.verdict`, and is passed in here. Nothing here
counts tracks or reads a log, so no surface can disagree with the verdict
because of this module.

**The honesty rules it keeps** (``docs/ux-design-principles.md``):

* ``✓`` leads the status line only when the verdict is ``ok`` (every audio
  track verified, nothing missing, nothing downgraded) *and* the line's own
  summary is the clean one. A one-frame match is a contradicted track, so it
  always leads with ``⚠``; a partial rip's verdict is ``warn``, so it never
  leads with ``✓``.
* No verdict (``None``: the log could not be read, or held no audio track) is
  *not determined*, and gets no mark at all rather than a pass.
* Status is never colour alone: every lead carries its marker
  (``✓`` / ``⚠`` / ``ⓘ`` / ``✖``).

Pure: no Qt, no I/O, never raises on the values its callers pass.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Final

#: The track list's right-click action that ticks only the highlighted rows.
#: ``ui/track_table.py`` builds its menu item from this constant and the banner's
#: next step names it, so the sentence cannot name a label the window lacks.
RIP_ONLY_THESE: Final[str] = "Rip only these"

#: The Start button's visible text, without its ``&`` mnemonic marker. The test
#: of the next step reads the real button's text and compares it with this.
START_RIP: Final[str] = "Start rip"

#: The rip pane's tab that holds the ripper's own output, as its label reads
#: without the ``&`` mnemonic marker. The status line sends the reader there for
#: what the ripper printed; it said "the Rip log tab" for months, a tab that never
#: existed. ``tests/test_one_track_table.py`` holds this equal to the
#: label ``ui/rip_progress.py`` builds the tab with.
LIVE_LOG_TAB: Final[str] = "Live log"

#: The failure banner's sentence when nothing at all was captured. The path is
#: appended by the caller, which knows which log it is.
NO_DIAGNOSIS: Final[str] = "Rip failed — no diagnosis was captured. See"


def tracks_phrase(numbers: Sequence[object]) -> str:
    """``track 3``, ``tracks 3 and 5`` or ``tracks 3, 5 and 7``; "" for none."""
    names = [str(n) for n in numbers]
    if not names:
        return ""
    if len(names) == 1:
        return f"track {names[0]}"
    return f"tracks {', '.join(names[:-1])} and {names[-1]}"


def next_step_sentence(numbers: Sequence[object]) -> str:
    """The banner's one plain next action for tracks AccurateRip contradicts.

    "" for no tracks. Names the controls by the labels the window shows
    (:data:`RIP_ONLY_THESE`, :data:`START_RIP`): a next step that names a
    button nobody can find is worse than none.
    """
    which = tracks_phrase(numbers)
    if not which:
        return ""
    them = "it" if len(numbers) == 1 else "them"
    return (
        f"Next: clean the disc, then re-rip {which}: select {them} in the track "
        f"list, right-click, choose “{RIP_ONLY_THESE}” and press {START_RIP}."
    )


def finished_line(
    body: str,
    *,
    verdict_level: str | None,
    body_clean: bool,
    attention: Sequence[object] = (),
) -> str:
    """The status line for a rip that finished: a lead with a marker, then ``body``.

    ``body`` is the rip-quality summary (``main_window_helpers.fidelity_summary``
    builds it), starting lowercase: ``"all 14 tracks ripped cleanly, …"``.
    ``verdict_level`` is the verdict banner's level as it is shown (``"ok"``,
    ``"warn"``, ``"neutral"``, ``"error"``, or None when there is no verdict).
    ``body_clean`` says whether ``body`` is the clean summary. ``attention`` is
    the tracks AccurateRip contradicts, as ``verdict.accuraterip_contradictions``
    numbers them.

    * tracks contradicted: ``⚠ Finished — 2 tracks need attention (3 and 5).``
      then the body as a sentence;
    * ``error``: ``✖ Finished with errors — …``;
    * ``warn``, or a body that is not clean: ``⚠ Finished with warnings — …``;
    * ``ok`` with a clean body: ``✓ Finished — …``;
    * ``neutral`` with a clean body: ``ⓘ Finished, not verified by AccurateRip — …``;
    * no verdict: ``Finished — …``, with no mark (not determined is never a pass).
    """
    text = body.strip()
    if attention:
        count = len(attention)
        need = "track needs" if count == 1 else "tracks need"
        listed = tracks_phrase(attention).split(" ", 1)[1]
        lead = f"⚠ Finished — {count} {need} attention ({listed})."
        return f"{lead} {text[:1].upper()}{text[1:]}" if text else lead
    if verdict_level == "error":
        lead = "✖ Finished with errors"
    elif verdict_level == "warn" or not body_clean:
        lead = "⚠ Finished with warnings"
    elif verdict_level == "ok":
        lead = "✓ Finished"
    elif verdict_level == "neutral":
        lead = "ⓘ Finished, not verified by AccurateRip"
    else:
        lead = "Finished"
    return f"{lead} — {text}" if text else f"{lead}."


def failure_banner_text(error: str, hint: str, log_path: object) -> str:
    """The failure banner: the dependency's own sentence first, then ours.

    ``error`` is what the rip worker reported (``_on_rip_error``: the ripper's
    or the system's own words, prefixed with who said it); ``hint`` is
    Platterpus's reading of the ripper's output (``failure_hint``), which may
    say what to do. Both are shown when both exist and differ, the error first
    (``CLAUDE.md`` rule #12: *show the user the dependency's own sentence*).
    With neither, the sentence admits that nothing was captured and names
    ``log_path``. Always starts with ``✖``.
    """
    parts: list[str] = []
    for part in (error.strip(), hint.strip()):
        if part and part not in parts:
            parts.append(part)
    if not parts:
        return f"✖ {NO_DIAGNOSIS} {log_path}"
    return "✖ " + " — ".join(parts)


def cancelled_folder(log_path: str, output_dir: object | None) -> Path | None:
    """The folder a cancelled rip's files are in, or None when nothing names one.

    The ripper writes its log in the album's folder, so a log names the folder
    exactly. Without one (a cancel before the log was written) the album's
    folder is somewhere under ``output_dir``, which is the nearest folder that
    can be named for certain. The window hands the same value to the status
    line and to the Open folder button, so the two cannot name two places
    (UX review E2).
    """
    if log_path.strip():
        return Path(log_path).parent
    text = "" if output_dir is None else str(output_dir).strip()
    return Path(text) if text else None


def cancelled_status(log_path: str, output_dir: object | None) -> str:
    """The status line after a cancel: what is left behind, and where.

    It used to read *"Rip cancelled by user. Partial files may remain."*:
    honest, but it named no folder, and "by user" was said of every cancel,
    the ones the app made too (a disc taken out). Keeps the word "cancelled",
    which the rig scripts' ``expect-status cancelled`` reads.
    """
    folder = cancelled_folder(log_path, output_dir)
    if folder is None:
        return "Rip cancelled. Tracks that finished, and partial files, may remain."
    where = f"in {folder}" if log_path.strip() else f"in the album's folder in {folder}"
    return f"Rip cancelled. Tracks that finished, and any partial files, are {where}."


def stall_next_step(cancelled: bool) -> str:
    """What the stall notice tells the user to do, before and after a cancel.

    Force stop is shown only once a cancel has been asked for (UX review M4,
    `RipControls._refresh_button_state`), so before one the notice sends the
    user to Cancel and says Force stop will follow, and after one it names
    Force stop, the button now beside Cancel, with its cost.
    """
    if cancelled:
        return "Force stop ends it now, but the rip's log will then be incomplete."
    return (
        "Press Cancel to recover; if the drive keeps spinning, Force stop "
        "appears beside it."
    )
