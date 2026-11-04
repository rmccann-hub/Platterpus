"""Which folders a script run's own ``cyanrip`` steps wrote, so the bundle carries them.

**The gap this closes (found 2026-11-04, preparing round 38's drive-mode test).**
A script's ``cyanrip ... -D <folder>`` step writes the rip's complete log, its cue
sheet and its diagnostics record into ``<rips folder>/<folder>``. Under
``--run-script`` the run's bundle carried only the run folder (transcript,
screenshots, report), so the rip's own log, the one with every read error, every
paranoia counter and every ``Pregap search:`` line, stayed on the owner's disk. The
transcript's one-line summary per rip (``record-accuracy``) was all that reached
us. The owner asked for "a fine detail answer with full error logs", and a summary
of a log is not the log.

**What this module decides, and nothing else.** Two pure functions: which folder a
step's ``-D`` names, resolved the way cyanrip resolves it (against the folder the
step runs in, ``runner._ripper_workdir``), and the ``extra_dirs`` mapping the
bundle builder is handed. The bundle's own type allowlist
(``evidence_bundle.EXTRA_DIR_SUFFIXES``: text, logs, JSON, cue sheets, PNGs) still
decides which files go in, so **no audio is ever carried** (Critical rule #8): a
``.flac`` in the folder is refused by the builder and counted as excluded.

**Bounded.** At most :data:`MAX_RIP_DIRS` folders are carried, in the order the run
made them; a run that makes more names the rest as not carried, rather than
growing the bundle without limit or dropping them silently.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path
from typing import Final

#: How many scripted rip folders one bundle carries. The longest script today
#: (`fullacceptance.txt`) makes about 30; `drivemode.txt` makes 12.
MAX_RIP_DIRS: Final[int] = 64

#: The archive prefix each carried folder sits under, beside the run's own
#: `scriptrun/`.
RIP_DIR_PREFIX: Final[str] = "scriptrips"

#: A folder name the bundle will use as an archive path segment: ASCII letters,
#: digits, dot, dash and underscore, bounded. Anything else (a placeholder left
#: unexpanded, a path with separators) is not carried rather than guessed at.
_SAFE_NAME: Final[re.Pattern[str]] = re.compile(r"[A-Za-z0-9._-]{1,120}")


def rip_output_dir(args: Sequence[str], workdir: Path) -> Path | None:
    """The folder a ``cyanrip`` step's ``-D`` names, or None. Pure; never raises.

    The LAST ``-D`` wins, as in cyanrip's own option parsing. A relative value is
    resolved against ``workdir``, the folder the step runs in, exactly as cyanrip
    resolves it; an absolute one is taken as given. A value that is empty, that
    climbs out with ``..``, or whose last segment is not a safe name, is None: the
    bundle carries what it can name, and says so for the rest.
    """
    value: str | None = None
    for index, arg in enumerate(args):
        if arg == "-D" and index + 1 < len(args):
            value = args[index + 1]
    if not value:
        return None
    candidate = Path(value)
    if ".." in candidate.parts:
        return None
    if not _SAFE_NAME.fullmatch(candidate.name or ""):
        return None
    return candidate if candidate.is_absolute() else workdir / candidate


def bundle_extra_dirs(
    run_folder: Path, rip_dirs: Sequence[Path]
) -> tuple[dict[str, Path], list[Path]]:
    """The bundle's ``extra_dirs``, and the rip folders left out. Pure; never raises.

    ``scriptrun`` is the run folder, as before. Each rip folder goes under
    ``scriptrips/<its name>``, first come first served: a second folder with the
    same name (two steps writing one folder) is carried once, and folders past
    :data:`MAX_RIP_DIRS` are returned as left out so the caller can log them.
    """
    extra: dict[str, Path] = {"scriptrun": run_folder}
    left_out: list[Path] = []
    carried = 0
    for folder in rip_dirs:
        key = f"{RIP_DIR_PREFIX}/{folder.name}"
        if key in extra:
            continue
        if carried >= MAX_RIP_DIRS:
            left_out.append(folder)
            continue
        extra[key] = folder
        carried += 1
    return extra, left_out
