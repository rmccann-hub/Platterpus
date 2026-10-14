"""cyanrip's ``--diagnostics`` record: where it is, so the report bundle can send it.

**Why this module exists.** Every rip asks cyanrip for a machine-readable record
of the run (``--diagnostics <name>``, built in ``adapters/cyanrip_backend.py``). For one
whole failure class it is the only evidence there is: a run cyanrip refuses
during argument validation opens no logfile at all (the fork's provider
contract, P4). It never reached the evidence bundle, because cyanrip runs with
``cwd=output_dir``, the rips ROOT, and is handed a bare file name, while the
bundle reads only the album folder cyanrip creates below it from ``-D``
(0 records in the 2026-09-07 bundle, "all 8 paths relative").

**The record stays where cyanrip writes it.** Moving it into the album folder
was built and then withdrawn on 2026-09-27, on the maintainer's ruling that a rip
leaves only the ``.log``, the ``.cue`` and the ``.platterpus.json`` in the album.
Embedding the record in ``.platterpus.json`` instead is the next round's work,
because it moves the report schema. Until then each rip's report bundle collects
the record by name from the rips root.

**Nothing here predicts a path.** The record's location is read off the argv the
ripper was actually spawned with and the directory it ran in: the same two facts
cyanrip itself resolves the name against. Predicting the album folder is what
once cost a finished 14-track rip over one character (``CLAUDE.md``).

**The securing pass's record is kept beside them (2026-10-14, TASKS R9).** The
securing pass runs in a temporary folder that is deleted when it ends, so its
record went with it, and nothing said so: two of the 2026-10-13 Full run's
eleven invocations left no record and the bundle's MANIFEST was silent about
both. The worker now copies that record into the rips root, beside the album
passes' records, under a name that says which pass wrote it,
and when it cannot, it says why. That lives in :mod:`platterpus.record_fate`,
because it touches the disk and this module does not.

Pure and Qt-free: no filesystem access, so nothing here can fail a rip.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Final

#: The flag that names the record, read back off the argv AS SPAWNED so this
#: module cannot disagree with what the ripper was told. This is the ONE home of
#: the spelling: the argv builder (`adapters/cyanrip_backend.py`) and the rig
#: check's probe (`rig_check.py`) both import it from here.
#:
#: **Long form since 2026-10-13.** It was ``-j`` until the fork retired its four
#: short options for its next release (`.23`): a retired letter exits 1 with
#: ``Unable to parse command line argument`` (their round 32 lap 5, S10 and S11).
#: Every build of theirs that takes ``-j`` also takes ``--diagnostics``: `.22`'s
#: provider contract lists both forms (`cyanrip@200530e`, PROVIDER-CONTRACT
#: lines 56-59), so the long form is safe on the pinned build too.
DIAGNOSTICS_FLAG: Final[str] = "--diagnostics"

#: Archive folder the report bundle puts the records in. Not ``album/``: the
#: records are not in the album folder, and the member name says where from.
BUNDLE_FOLDER: Final[str] = "ripperdiagnostics"


def record_path_from_argv(argv: Sequence[str], cwd: Path) -> Path | None:
    """Where the ripper was told to write its record, or ``None``. Pure.

    The LAST ``--diagnostics`` wins, because that is what cyanrip does: genopt makes a
    repeated single-value option replace the previous one (see
    ``rig_check.compose_probe_argv``, which cites the lines). A relative name is
    resolved against ``cwd``, the directory the ripper was run in.
    """
    value = ""
    for index, item in enumerate(argv):
        if item == DIAGNOSTICS_FLAG and index + 1 < len(argv):
            value = argv[index + 1]
    if not value:
        return None
    candidate = Path(value)
    return candidate if candidate.is_absolute() else cwd / candidate


def bundle_members(records: Iterable[Path]) -> dict[str, Path]:
    """Archive name to path, one entry per distinct record. Pure.

    The file name is kept as it is, because the bundle judges a file by its
    suffix. Two different paths with the same name get numbered folders rather
    than one dict key, because a repeated key would silently drop the first.
    Whether each file is actually there is the bundle's question, answered with
    a manifest row, not this function's.
    """
    members: dict[str, Path] = {}
    for record in dict.fromkeys(records):
        name = f"{BUNDLE_FOLDER}/{record.name}"
        count = 1
        while name in members:
            count += 1
            name = f"{BUNDLE_FOLDER}{count}/{record.name}"
        members[name] = record
    return members
