# SPDX-License-Identifier: GPL-3.0-only
"""The files cyanrip says it did not write whole: the fork's ``not written whole:``.

**Why this exists.** A track block's ``File(s):`` list is printed before the
encoders are joined, so it names what was ASKED for, whatever then happened to
the file (the fork's KNOWN-ISSUES item 22). The footer's ``Encoder errors:`` line
says how many tracks' encoders failed, and the track numbers, but not which file
on disk is damaged. From ``.27`` the footer names each one, one line per file,
directly below ``Encoder errors:`` when it names a failed track
(``cyanrip@709337a:src/cyanrip_log.c:327-345``; their P2 row
``cyanrip@302dba8:PROVIDER-CONTRACT.md:286``)::

    Encoder errors: 2 tracks failed (2, 3); 1 track encoded
        not written whole: o/2.flac
        not written whole: o/3.flac

Each path is built as ``File(s):`` builds it (``crip_get_path``), one per output
format whose encoder failed. Their round 36 lap 4 S12 proposed it, our lap 3 S5
accepted it, and their lap 7 S6 says it is built (``d33902d``); their test cuts
the files with a file-size cap and checks the lines name every cut file and
nothing else (``cyanrip@709337a:tests/rip_images.py:2898-2919``).

**What this module does with them.** The parser collects the paths through
:class:`PathSample` (bounded, the elision counted); this module turns them into
the report's ``rip.not_written_whole``, one ``issues`` warning per file, and a
clause for the window's status line, so the user sees WHICH files are damaged
without opening the log. Every path a person sees is screened
(:mod:`platterpus.inbound_text`): it is the ripper's text, and it may carry a
disc's CD-TEXT.

**Absence is not "all written whole".** An older build never prints the lines, so
no line says nothing; the report's list is ``null`` then, never ``[]``.

Pure, Qt-free, never raises. Imports nothing from the parser, so the parser can
take :class:`PathSample` from here without a cycle.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Final

from platterpus import inbound_text

#: How many paths are kept from the start of the list, and how many from its end.
#: A CD holds at most 99 tracks and we send one output format, so a whole disc's
#: list fits in the head; the tail is for a list that does not.
KEEP_HEAD: Final[int] = 100
KEEP_TAIL: Final[int] = 100

#: The longest path kept whole (Linux's PATH_MAX). A longer one keeps its head and
#: its tail, the file's name being at the end, and says how much was cut.
MAX_PATH_CHARS: Final[int] = 4096

#: ``issues`` code: a file the ripper says its encoder did not write whole.
ISSUE_NOT_WRITTEN_WHOLE: Final[str] = "file_not_written_whole"

#: How many paths the status line names before it counts the rest.
_STATUS_PATHS: Final[int] = 3


def bound_path(path: str) -> str:
    """``path`` at most :data:`MAX_PATH_CHARS` long, any cut marked and counted."""
    if len(path) <= MAX_PATH_CHARS:
        return path
    keep = MAX_PATH_CHARS // 2
    cut = len(path) - 2 * keep
    return f"{path[:keep]}… [{cut} characters cut] …{path[-keep:]}"


@dataclass
class PathSample:
    """The paths the footer named, head and tail kept, with the full count.

    Mutable: the parser adds a path per line. ``total`` counts every line read,
    so ``total - len(paths())`` is how many the sample does not hold.
    """

    head: list[str] = field(default_factory=list)
    tail: deque[str] = field(default_factory=lambda: deque(maxlen=KEEP_TAIL))
    total: int = 0

    def add(self, path: str) -> None:
        self.total += 1
        kept = bound_path(path)
        if len(self.head) < KEEP_HEAD:
            self.head.append(kept)
        else:
            self.tail.append(kept)

    def paths(self) -> tuple[str, ...]:
        return (*self.head, *self.tail)


def paths_of(rip_log: object) -> tuple[str, ...]:
    """The paths the log named, as parsed (raw, bounded). Never raises."""
    paths = getattr(rip_log, "not_written_whole", ()) or ()
    if not isinstance(paths, Sequence) or isinstance(paths, str):
        return ()
    return tuple(p for p in paths if isinstance(p, str))


def not_kept(rip_log: object) -> int:
    """How many named paths the parse's sample does not hold (0 when all are)."""
    total = getattr(rip_log, "not_written_whole_total", 0)
    kept = len(paths_of(rip_log))
    if isinstance(total, int) and not isinstance(total, bool) and total > kept:
        return total - kept
    return 0


def _shown(path: str) -> str:
    return inbound_text.screen_line(path).text


def report_list(rip_log: object) -> list[str] | None:
    """The report's ``rip.not_written_whole``: screened paths, or None for no line."""
    paths = paths_of(rip_log)
    if not paths and not not_kept(rip_log):
        return None
    return [_shown(p) for p in paths]


def _track_of(rip_log: object, path: str) -> int | None:
    """The track whose ``File(s):`` path is ``path``, when exactly one names it."""
    numbers = [
        getattr(track, "number", None)
        for track in getattr(rip_log, "tracks", ()) or ()
        if getattr(track, "filename", "") == path
    ]
    found = [n for n in numbers if isinstance(n, int) and not isinstance(n, bool)]
    return found[0] if len(found) == 1 else None


def findings(rip_log: object) -> list[tuple[str, str, str]]:
    """One ``issues`` warning per file not written whole, plus one for any not kept.

    ``(severity, code, message)``, the shape ``rip_report._issues`` adds. A
    warning: the ripper has said in its own words that this file is damaged or
    incomplete, which no checksum of ours has to confirm.
    """
    found: list[tuple[str, str, str]] = []
    for path in paths_of(rip_log):
        number = _track_of(rip_log, path)
        which = f"track {number}: " if number is not None else ""
        found.append(
            (
                "warning",
                ISSUE_NOT_WRITTEN_WHOLE,
                f"{which}cyanrip says its encoder did not write this file whole: "
                f"{_shown(path)}. The file is damaged or incomplete; rip the track "
                "again",
            )
        )
    more = not_kept(rip_log)
    if more:
        found.append(
            (
                "warning",
                ISSUE_NOT_WRITTEN_WHOLE,
                f"cyanrip named {more} more file{'s' if more != 1 else ''} not "
                "written whole than this report lists; see the ripper's log",
            )
        )
    return found


def status_clause(rip_log: object) -> str:
    """A sentence for the status line naming the damaged files, or ``""``."""
    paths = paths_of(rip_log)
    count = len(paths) + not_kept(rip_log)
    if not count:
        return ""
    named = ", ".join(_shown(p) for p in paths[:_STATUS_PATHS])
    rest = count - min(len(paths), _STATUS_PATHS)
    tail = f" and {rest} more" if rest > 0 else ""
    noun = "file was" if count == 1 else "files were"
    return f" cyanrip says {count} {noun} not written whole: {named}{tail}."
