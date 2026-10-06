# SPDX-License-Identifier: GPL-3.0-only
"""Which pass of a rip an exit status describes, said the same way everywhere.

**Why this exists (ruling C1, ``PLANNING.md`` KDD-41).** A rip can run the ripper
more than once: the album pass (the whole disc, or the user's ``-l`` selection,
with any read-speed-ladder retries), then a securing pass that re-reads the tracks
AccurateRip did not confirm. Until 2026-10-05 the report's ``ripper_exit_code``
held whichever ran LAST, while ``status`` described the album pass, so a securing
pass that exited 1 over an album pass that exited 0 read as *"recorded as
successful but the ripper exited 1"*. Since C1 the securing pass also follows an
album pass that exited 1, so the two codes now meet in one report often, and every
reader has to say which one it is quoting.

**The report shape (schema v31).** ``outcome.ripper_exit_code`` is the ALBUM pass's.
``outcome.securing_pass_started`` says whether a securing pass's ripper was spawned,
and ``outcome.securing_pass_exit_code`` is its exit status. Both codes are
tri-state: ``null`` is "never reaped", never ``0``, and the securing pass's
``null`` reads as "did not run" only when ``securing_pass_started`` is false.

**An older report** has no ``securing_pass_started`` key, and its
``ripper_exit_code`` was the last pass's, whichever that was. Which pass it
describes is then not recorded, so it is quoted as a plain "ripper exit", exactly
as before, rather than labelled with a pass we cannot know.

Pure; never raises; reads a report's ``outcome`` block defensively.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

#: The report keys this module owns, named once so the writer and the readers
#: cannot spell them two ways.
SECURING_STARTED_KEY: str = "securing_pass_started"
SECURING_EXIT_KEY: str = "securing_pass_exit_code"


def exit_text(code: int | None) -> str:
    """An exit status as a reader should see it: ``null`` is never shown as 0."""
    return "not reaped (null)" if code is None else str(code)


def securing_fact(started: bool, code: int | None) -> str:
    """The securing pass's exit for a one-line fact: its code, or that it never ran."""
    return exit_text(code) if started else "did not run"


def _code(value: object) -> int | None:
    """An exit status from a report, or ``None``. A bool is not an exit status."""
    return value if isinstance(value, int) and not isinstance(value, bool) else None


@dataclass(frozen=True)
class PassExits:
    """The rip's exit statuses, by pass.

    ``securing_started`` is ``None`` when the report does not record it (an older
    report), which is "not determined", not "no securing pass".
    """

    album: int | None
    securing_started: bool | None
    securing: int | None

    @classmethod
    def from_outcome(cls, outcome: object) -> PassExits:
        """Read a report's ``outcome`` block. Never raises."""
        if not isinstance(outcome, Mapping):
            return cls(album=None, securing_started=None, securing=None)
        started = outcome.get(SECURING_STARTED_KEY)
        return cls(
            album=_code(outcome.get("ripper_exit_code")),
            securing_started=started if isinstance(started, bool) else None,
            securing=_code(outcome.get(SECURING_EXIT_KEY)),
        )

    @property
    def pass_recorded(self) -> bool:
        """Whether the report says which pass ``album`` describes."""
        return self.securing_started is not None

    def phrase(self) -> str:
        """``album pass exit 1; securing pass exit 0``, or an older report's form.

        The album pass leads because the rip's status describes it. The securing
        pass is named only when it ran. An older report keeps its old wording,
        ``ripper exit N``, because which pass that was is not recorded.
        """
        if not self.pass_recorded:
            return f"ripper exit {exit_text(self.album)}"
        text = f"album pass exit {exit_text(self.album)}"
        if self.securing_started:
            text += f"; securing pass exit {exit_text(self.securing)}"
        return text
