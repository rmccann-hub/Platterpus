"""Pure graders behind the acceptance script's permutation verbs.

**Why these exist.** The acceptance run rips eight times and every rip used the
same handful of settings, so whole paths had never run on hardware (TASKS
*"Permutations the acceptance test still does not run"*, 2026-09-30): a
finished rip filed into a library folder, a rip with no ``-r`` (Max retries 0),
and one with no ``-Z`` (the secure re-read off). Section J2 rips once with all
of them, and these graders answer what that rip did.

**What is decided here, and what is not.** The handlers that find this
section's rip and wait for its record are in
:mod:`platterpus.uiscript.permutation_verbs`. Everything they decide is here,
pure and Qt-free, so it is tested against the committed round-29 reports with no
drive. Nothing here raises on a malformed artifact: a report another thread is
still writing is a check that has not passed, never a crash of an unattended
run.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final

from platterpus.uiscript.artifact_grading import Grade, report_path

#: The scratch library's folder name. It sits INSIDE the run's rips folder (the
#: output directory) rather than beside it, for one reason: the acceptance
#: session collects every rip folder under its rips folder into the bundle
#: (`test_session.session_album_dirs` searches it recursively), so a rip filed
#: here still reaches the one file the operator sends. ASCII letters only, like
#: every name an operator may handle by hand (`CLAUDE.md`, artifact filenames).
SCRATCH_LIBRARY_NAME: Final[str] = "libraryscratch"

#: A flag as cyanrip's argv spells one: ``-r`` or ``--consumer``. Anything else
#: is refused, because ``without r`` (a typo) would pass on every argv there is.
_FLAG: Final[re.Pattern[str]] = re.compile(r"-[A-Za-z]|--[A-Za-z][\w-]*")

#: The flag every rip argv carries (Critical rule #5: cyanrip never looks
#: MusicBrainz up itself). Read here only as a floor: an argv without it is not
#: a rip argv this grader can say anything about.
_EVERY_RIP_CARRIES: Final[str] = "-N"


def scratch_library_dir(output_dir: str) -> tuple[Path | None, str]:
    """``<output_dir>/libraryscratch``, or ``(None, why not)``. Never raises.

    The library folder must be absolute (`settings_validation._validate_dir`),
    and so must the output directory it is derived from. An empty or relative
    output directory is refused here with its own sentence, rather than handed
    to the validator as a path that fails for a reason the operator cannot see.
    """
    text = (output_dir or "").strip()
    if not text:
        return None, (
            "the output directory is empty, so there is no rips folder to put a "
            "scratch library in"
        )
    path = Path(text)
    if not path.is_absolute():
        return None, (
            f"the output directory {text!r} is not an absolute path, so a library "
            "folder derived from it would be refused"
        )
    return path / SCRATCH_LIBRARY_NAME, ""


def grade_library_move(log_file: object, library: Path, before: Path) -> Grade | None:
    """Has this rip's album folder been filed in ``library``? ``None`` = not yet.

    ``log_file`` is the window's ``_last_rip_log_file``, which
    ``MainWindow._on_library_moved`` repoints at the folder's new home once the
    move has finished, so it is the product's own record of where the album is.
    ``before`` is the album folder as the step first saw it.

    **What a pass needs, and why each part.** The folder is inside the library;
    the log the window points at exists there (a pointer to a vanished file is
    the failure a repoint exists to prevent); a report travelled with it (the
    window flushes it before moving, so a folder without one lost its record);
    and nothing is left where it was (a copy is not a move). When the move had
    already finished before the step looked, the old place cannot be re-checked,
    and the pass says so rather than implying it was.
    """
    if not isinstance(log_file, Path):
        return Grade(
            False,
            "the window no longer records where this rip's log is, so where the "
            "album went cannot be read",
        )
    folder = log_file.parent
    try:
        home = library.resolve()
        here = folder.resolve()
        was = before.resolve()
    except (OSError, RuntimeError) as exc:
        return Grade(False, f"the library or album path cannot be resolved: {exc!r}")
    if here == home or not here.is_relative_to(home):
        return None  # still in the output folder: the move has not happened yet
    problems: list[str] = []
    if not log_file.is_file():
        problems.append(f"the window points at {log_file}, which does not exist")
    if report_path(folder) is None:
        problems.append(f"no rip report travelled with the folder to {folder}")
    already = was == here
    if not already and before.exists():
        problems.append(f"{before} still exists, so the album was copied, not moved")
    if problems:
        return Grade(False, "; ".join(problems))
    where = (
        "it had already moved when this step looked, so the old place was not "
        "re-checked"
        if already
        else f"nothing is left at {before}"
    )
    return Grade(
        True,
        f"filed in the library as {folder}, with its log and report; {where}",
    )


def flag_problem(flag: str) -> str:
    """``""`` when ``flag`` is spelled like a cyanrip flag, else why it is not."""
    if _FLAG.fullmatch(flag):
        return ""
    return (
        f"{flag!r} is not a flag: write it as cyanrip's argv does, e.g. `-r` or "
        "`--consumer`. A misspelt flag is absent from every argv, so `without` "
        "would pass whatever was sent"
    )


def grade_rip_argv(report: Mapping[str, Any], flag: str, *, present: bool) -> Grade:
    """Did this rip's argv carry ``flag`` (``present``) or leave it out?

    **Read from the argv as SPAWNED** (the report's ``outcome``, recorded off
    ``Popen.args``), never predicted from the settings: a prediction would
    check the settings against themselves. Whether cyanrip RECEIVED the same
    flags is a second question, answered by ``expect-album-audit
    argv_agreement``, and the section asks both.

    **The whole-disc pass is the one graded**, because it is the one the
    settings alone produce. A later pass is a decision the rip made from what
    it read (re-reading a track AccurateRip did not confirm adds ``-Z`` and
    ``-l``), so when the rip ran more than one pass the detail says what the
    last one carried, ungraded.

    Floors, so this cannot pass by finding nothing: there must be an argv, and
    it must carry ``-N``, which every rip argv does.
    """
    problem = flag_problem(flag)
    if problem:
        return Grade(False, problem)
    outcome = report.get("outcome")
    if not isinstance(outcome, Mapping):
        return Grade(False, "the report records no outcome, so no argv to read")
    first = outcome.get("ripper_argv_first_pass")
    last = outcome.get("ripper_argv")
    argv = first or last
    if not isinstance(argv, list) or len(argv) < 2:
        return Grade(
            False,
            "the report records no argv for this rip, so what it sent cannot be "
            "read (an absent argv is not one without the flag)",
        )
    tokens = [str(token) for token in argv[1:]]  # argv[0] is the binary
    if _EVERY_RIP_CARRIES not in tokens:
        return Grade(
            False,
            f"the recorded argv carries no {_EVERY_RIP_CARRIES}, which every rip "
            "argv does, so it is not one this check can read",
        )
    found = flag in tokens
    value = ""
    if found:
        after = tokens.index(flag) + 1
        if after < len(tokens) and not _FLAG.fullmatch(tokens[after]):
            value = f" {tokens[after]}"
    later = ""
    if isinstance(last, list) and isinstance(first, list) and last != first:
        carried = flag in [str(token) for token in last[1:]]
        later = (
            f"; the rip ran a later pass too, whose argv "
            f"{'carries' if carried else 'leaves out'} {flag} (not graded: a "
            "later pass is chosen by what the rip read, not by the settings)"
        )
    said = f"`{flag}{value}`" if found else f"no `{flag}`"
    if found == present:
        return Grade(True, f"the whole-disc pass sent {said}, as asked{later}")
    wanted = "carry" if present else "leave out"
    return Grade(
        False,
        f"the whole-disc pass sent {said}, and this step expected it to {wanted} "
        f"{flag}{later}",
    )
