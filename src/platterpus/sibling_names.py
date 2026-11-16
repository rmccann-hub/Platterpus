"""Every file name Platterpus builds from a name cyanrip chose: one place.

**Why this module exists (TASKS R88, 2026-11-16).** Linux allows at most 255
BYTES in one file or folder name. cyanrip names each track's file and the rip's
log from the tags and naming scheme we send, and then Platterpus writes files of
its own BESIDE them, named by adding an ending to cyanrip's name: a temporary
copy while a re-read track is swapped in, a temporary file while a FLAC is
transcoded, the EAC-compatible log, the JSON report, and so on. Each of those
endings makes the name longer. So a track name of 250 bytes is a legal name for
cyanrip and still breaks the rip afterwards, because ``<name>.platterpus-refix.tmp``
is 271 bytes and cannot be created (measured: ``ENAMETOOLONG``).

The before-Start name-length check (``adapters/cyanrip_name_lengths.py``)
therefore has to leave room for the longest ending we add. It can only do that
reliably if the endings live in ONE place that both the check and the code that
writes the files read. That is this module:

* each ending is a constant here, and each writer builds its name through the
  helper beside it (``refix_temp_name`` and so on), never by spelling the ending
  itself (``tests/test_sibling_names.py`` sweeps the package for a stray copy);
* ``master_siblings`` / ``derived_siblings`` / ``log_siblings`` list every name
  built from one cyanrip name, through those same helpers;
* the three ``*_EXTRA_BYTES`` numbers are DERIVED from those lists, so adding a
  new ending to a list moves the check's limit with no number typed anywhere.

Pure: no I/O, no Qt, never raises.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import PurePosixPath
from typing import Final

# --- Endings added to a track's FLAC master (cyanrip's own file name) ---------

#: The temporary copy a re-read track is written to before it replaces the
#: original (``workers/rip_worker.py``, the securing pass's swap).
REFIX_TEMP_SUFFIX: Final[str] = ".platterpus-refix.tmp"
#: The hidden temporary a CTDB repair writes the repaired FLAC to
#: (``ctdb/repair_commit.candidate_path``): a dot before the name, an ending after.
CTDB_CANDIDATE_PREFIX: Final[str] = "."
CTDB_CANDIDATE_SUFFIX: Final[str] = ".ctdb-repair.flac"
#: Where the original FLAC is kept once a CTDB repair replaces it.
CTDB_BACKUP_SUFFIX: Final[str] = ".before-ctdb-repair"

# --- Endings added to a derived file (the FLAC's stem with its own extension) -

#: The temporary file ffmpeg writes a transcode to (``adapters/transcode.py``).
TRANSCODE_TEMP_SUFFIX: Final[str] = ".transcode.tmp"
#: The temporary file an MP3 is re-tagged into (``adapters/mp3_replaygain.py``).
REPLAYGAIN_TEMP_SUFFIX: Final[str] = ".replaygain.tmp"

# --- Endings that replace ``.log`` on the rip log cyanrip wrote ---------------

#: The extension cyanrip gives the rip log; every ending below replaces it.
RIP_LOG_EXTENSION: Final[str] = ".log"
#: The EAC-layout log (``ui/main_window_rip``, KDD-24).
EAC_LOG_SUFFIX: Final[str] = " (EAC-compatible).log"
#: The JSON rip report (``rip_report``).
REPORT_SUFFIX: Final[str] = ".platterpus.json"
#: The auto-fix addendum. Deliberately long and namespaced: it sits in the user's
#: album folder, and a reader who has never heard of this program should be able
#: to tell whose it is and that it is not part of the rip itself.
ADDENDUM_SUFFIX: Final[str] = ".platterpus-addendum.txt"
#: The securing pass's own ripper log, kept beside the album's. ``.txt``, never
#: ``.log``: the album's log is found by its suffix, and a second cyanrip ``.log``
#: in the folder would be a second candidate for THE log.
SECURING_PASS_LOG_SUFFIX: Final[str] = ".platterpus-securing-pass.txt"
#: Each verified-read chase's ripper log, ``.txt`` for the same reason.
CHASE_LOG_SUFFIX: Final[str] = ".platterpus-verified-read.txt"

#: What ``atomic_write`` adds to a name while it writes it, used here for the
#: JSON report (written atomically, so its temporary exists beside the log).
ATOMIC_TEMP_SUFFIX: Final[str] = ".tmp"


def refix_temp_name(name: str) -> str:
    """The temporary a re-read track ``name`` is copied to before the swap."""
    return name + REFIX_TEMP_SUFFIX


def ctdb_candidate_name(name: str) -> str:
    """The hidden temporary a CTDB repair of ``name`` is written to."""
    return CTDB_CANDIDATE_PREFIX + name + CTDB_CANDIDATE_SUFFIX


def ctdb_backup_name(name: str) -> str:
    """Where the original ``name`` is kept once a CTDB repair replaces it."""
    return name + CTDB_BACKUP_SUFFIX


def transcode_temp_name(name: str) -> str:
    """The temporary the derived file ``name`` is transcoded into."""
    return name + TRANSCODE_TEMP_SUFFIX


def replaygain_temp_name(name: str) -> str:
    """The temporary the MP3 ``name`` is re-tagged into."""
    return name + REPLAYGAIN_TEMP_SUFFIX


def atomic_temp_name(name: str) -> str:
    """The temporary ``atomic_write`` writes ``name`` through."""
    return name + ATOMIC_TEMP_SUFFIX


def log_stem(log_name: str) -> str:
    """``Album.log`` → ``Album``: the stem every log sidecar is named from.

    Exactly ``Path(...).stem``, which is what the writers always used; a pure
    path, so the name-length check can ask it of a plain string with no I/O."""
    return PurePosixPath(log_name).stem


def eac_log_name(log_name: str) -> str:
    """The EAC-layout log beside the rip log ``log_name``."""
    return log_stem(log_name) + EAC_LOG_SUFFIX


def report_name(log_name: str) -> str:
    """The JSON rip report beside the rip log ``log_name``."""
    return log_stem(log_name) + REPORT_SUFFIX


def addendum_name(log_name: str) -> str:
    """The auto-fix addendum beside the rip log ``log_name``."""
    return log_stem(log_name) + ADDENDUM_SUFFIX


def securing_pass_log_name(log_name: str) -> str:
    """The securing pass's log beside the rip log ``log_name``."""
    return log_stem(log_name) + SECURING_PASS_LOG_SUFFIX


def chase_log_name(log_name: str) -> str:
    """A verified-read chase's log beside the rip log ``log_name``."""
    return log_stem(log_name) + CHASE_LOG_SUFFIX


def master_siblings(name: str) -> tuple[str, ...]:
    """Every name we create beside a track's FLAC master named ``name``."""
    return (refix_temp_name(name), ctdb_candidate_name(name), ctdb_backup_name(name))


def derived_siblings(name: str) -> tuple[str, ...]:
    """Every name we create beside a derived file (``.mp3``, ``.wv``, ``.wav``)."""
    return (transcode_temp_name(name), replaygain_temp_name(name))


def log_siblings(log_name: str) -> tuple[str, ...]:
    """Every name we create beside the rip log cyanrip named ``log_name``."""
    return (
        eac_log_name(log_name),
        report_name(log_name),
        atomic_temp_name(report_name(log_name)),
        addendum_name(log_name),
        securing_pass_log_name(log_name),
        chase_log_name(log_name),
    )


def _extra_bytes(siblings: Callable[[str], tuple[str, ...]], probe: str) -> int:
    """How many bytes the longest sibling adds to a cyanrip name like ``probe``.

    Every ending is ASCII and is added the same way whatever the name, so one
    short probe measures it for every name."""
    own = len(probe.encode("utf-8"))
    return max(len(s.encode("utf-8")) for s in siblings(probe)) - own


#: The most bytes we add to a track's FLAC name (the refix temporary's 21 today).
MASTER_EXTRA_BYTES: Final[int] = _extra_bytes(master_siblings, "a.flac")
#: The most bytes we add to a derived file's name.
DERIVED_EXTRA_BYTES: Final[int] = _extra_bytes(derived_siblings, "a.mp3")
#: The most bytes we add to the rip log's name, ``.log`` counted off (the
#: securing-pass and chase logs' 29-byte endings less ``.log``'s 4, today).
LOG_EXTRA_BYTES: Final[int] = _extra_bytes(log_siblings, "a.log")
