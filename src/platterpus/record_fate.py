"""What became of each ripper invocation's ``--diagnostics`` record (TASKS R9).

**Why this exists.** Every rip asks cyanrip for a machine-readable record of how
it ended (:mod:`platterpus.diagnostics_record`). The album passes write theirs in
the rips root, where the bundles find them. The securing pass, a re-read of the
tracks that need it (``-l 3,5``), runs in a temporary folder that is deleted
when it ends, so its record was deleted with it, and nothing said so: two of the
2026-10-13 Full run's eleven invocations left no record, and the session
bundle's MANIFEST was as silent about them as about a record that never existed.
``CLAUDE.md``: an absence in a log is a fact about the logger before it is a fact
about the subject, and a silent one reads as completeness.

**Two halves, one fact.**

* :func:`keep_securing_record` runs on the rip worker's thread before the
  temporary folder goes: it copies the record into the rips root, beside the
  album passes', under a name that says which pass wrote it, and when it cannot
  it returns why (:class:`RecordFate`). The report carries that as
  ``outcome.securing_pass_record`` (schema v34).
* :func:`record_absences` runs when a session is packed: it reads each rip's
  report and names, in the MANIFEST, every invocation whose record is missing
  and the reason the report gives, cross-checked against the records the scan
  found. The session does not talk to the worker, so the report is the route.

Qt-free and never raises: a record is evidence about a rip, and losing it must
never cost the rip or the session's bundle.
"""

from __future__ import annotations

import json
import logging
import shutil
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, TypedDict

from platterpus.diagnostics_record import DIAGNOSTICS_FLAG

log = logging.getLogger(__name__)

#: What the kept copy's name gains, before its suffix, so a reader of the rips
#: root can tell the securing pass's record from the album pass's:
#: ``cyanrip-diagnostics-20261013T162022Z-securingpass.json``. It still matches
#: the session's ``cyanrip-diagnostics-*.json`` scan, which is how the session
#: bundle collects it with no second glob. ASCII letters only, like every name a
#: person may handle (``CLAUDE.md``, artifact filenames).
SECURING_RECORD_MARK: Final[str] = "-securingpass"

#: How the securing pass's record ended up. ``not_run``: no securing pass ripper
#: was spawned, so there was no record to keep (nothing is missing). ``kept``:
#: copied into the rips root. ``missing``: a pass ran and its record is not in
#: the rips root, and ``detail`` says why.
STATE_NOT_RUN: Final[str] = "not_run"
STATE_KEPT: Final[str] = "kept"
STATE_MISSING: Final[str] = "missing"


class SecuringRecordBlock(TypedDict):
    """The report's ``outcome.securing_pass_record`` block (schema v34)."""

    state: str
    path: str | None
    detail: str | None


@dataclass(frozen=True)
class RecordFate:
    """What became of one pass's record: :data:`STATE_KEPT` and where, or
    :data:`STATE_MISSING` and why, or :data:`STATE_NOT_RUN`.

    ``path`` is the kept copy when kept, and where cyanrip was TOLD to write it
    when missing (a folder that no longer exists, but the name is the evidence a
    reader can search the app log for). ``detail`` is the reason, a sentence.
    """

    state: str = STATE_NOT_RUN
    path: Path | None = None
    detail: str = ""

    def as_block(self) -> SecuringRecordBlock:
        """The JSON form, ``null`` for an absent path or reason."""
        return {
            "state": self.state,
            "path": str(self.path) if self.path is not None else None,
            "detail": self.detail or None,
        }


def securing_record_destination(
    source: Path, rips_root: Path, attempt: int = 1
) -> Path:
    """Where the securing pass's record ``source`` is kept in ``rips_root``. Pure.

    ``cyanrip-diagnostics-<stamp>.json`` becomes
    ``<rips_root>/cyanrip-diagnostics-<stamp>-securingpass.json``; ``attempt``
    numbers a second name when the first is taken (``-securingpass2``), because
    a copy never overwrites a record that is already there.
    """
    count = "" if attempt <= 1 else str(attempt)
    return rips_root / f"{source.stem}{SECURING_RECORD_MARK}{count}{source.suffix}"


def securing_record_missing_reason(
    told: Path | None, *, cancelled: bool, copy_error: str = ""
) -> str:
    """Why a securing pass that ran left no record in the rips root. Pure.

    ``told`` is where its argv told cyanrip to write it (``None`` when the argv
    named no record); ``cancelled`` whether the rip was cancelled, which is the
    one ordinary way a record never arrives; ``copy_error`` a failed copy of a
    record that WAS there.
    """
    if told is None:
        return (
            f"the securing pass's argv named no {DIAGNOSTICS_FLAG} record, so "
            "cyanrip was never asked for one"
        )
    if copy_error:
        return (
            f"cyanrip wrote {told.name}, and it could not be copied out of the "
            f"securing pass's temporary folder before that was deleted: {copy_error}"
        )
    if cancelled:
        return (
            f"cyanrip was told to write {told.name} and it was not there when the "
            "temporary folder was cleared: the rip was cancelled, and cyanrip writes "
            "the record as it exits, so a reader still stopping writes it later, "
            "into a folder that is gone, and one that is killed writes none"
        )
    return (
        f"cyanrip was told to write {told.name} and it was not there when the "
        "securing pass ended: cyanrip writes it as it exits, so it was killed, "
        "crashed, or is a build that does not write one"
    )


def describe_fate(fate: object) -> str:
    """One line for a bundle's facts: where the securing pass's record went. Pure.

    Anything that is not a :class:`RecordFate` (a caller with no worker to ask)
    is "not determined", never "not run", which would claim a fact.
    """
    if not isinstance(fate, RecordFate):
        return "not determined (no rip worker to ask)"
    if fate.state == STATE_KEPT:
        return f"kept as {fate.path}"
    if fate.state == STATE_MISSING:
        return f"MISSING: {fate.detail or 'no reason was recorded'}"
    return "none due (no securing pass ripper was started)"


def outcome_block(fate: RecordFate | None, *, started: bool) -> SecuringRecordBlock:
    """The report's ``outcome.securing_pass_record`` block. Pure.

    ``None`` is a caller that did not say. It is written ``not_run`` only when no
    securing pass started; when one did, it is ``missing``, because a record
    nobody accounted for is not one that was kept.
    """
    if fate is None:
        fate = (
            RecordFate(
                STATE_MISSING,
                None,
                "the securing pass ran and nothing reported what became of its record",
            )
            if started
            else RecordFate()
        )
    return fate.as_block()


def missing_issue(block: object) -> str:
    """The report issue's sentence for a missing record, or ``""``. Pure."""
    if not isinstance(block, Mapping) or block.get("state") != STATE_MISSING:
        return ""
    reason = block.get("detail") or "no reason was recorded"
    return f"the securing pass's own diagnostics record was not kept: {reason}"


def keep_securing_record(
    told: Path | None, rips_root: Path, *, started: bool, cancelled: bool
) -> RecordFate:
    """Copy the securing pass's record into ``rips_root``, or say why not.

    ``told`` is where the pass's argv told cyanrip to write it, inside the
    pass's temporary folder (``None``: the argv named none); ``started`` whether
    that pass's ripper was spawned at all (if not, no record was due and the
    answer is ``not_run``); ``cancelled`` whether the rip was cancelled, which
    changes the reason. Thread-safe and Qt-free, and never raises. Never
    overwrites: a taken name gets a number (:func:`securing_record_destination`).
    """
    if not started:
        return RecordFate()
    try:
        if told is None or not told.is_file():
            fate = RecordFate(
                STATE_MISSING,
                told,
                securing_record_missing_reason(told, cancelled=cancelled),
            )
        else:
            attempt = 1
            target = securing_record_destination(told, rips_root)
            while target.exists():
                attempt += 1
                target = securing_record_destination(told, rips_root, attempt)
            shutil.copyfile(told, target)
            return RecordFate(STATE_KEPT, target)
    except OSError as exc:
        fate = RecordFate(
            STATE_MISSING,
            told,
            securing_record_missing_reason(
                told, cancelled=cancelled, copy_error=str(exc)
            ),
        )
    log.warning("the securing pass's -j record is missing: %s", fate.detail)
    return fate


# --- Reading the absences back, for the session bundle -----------------------

#: A rip report is a few megabytes at most (the 2026-10-13 secure re-read's is 6).
#: One far past that is not loaded whole on a guess; it is counted as unread.
_MAX_REPORT_BYTES: Final[int] = 64 * 1024 * 1024

#: cyanrip's record states (`ripper_ending`) that mean the album pass's record
#: did not reach us. `not_requested` is an argv that named none.
_ALBUM_RECORD_LOST: Final[frozenset[str]] = frozenset(
    {"absent", "unreadable", "not_requested"}
)


def record_absences(
    album_dirs: Sequence[Path], records: Sequence[Path], *, report_glob: str
) -> str:
    """Every ripper invocation whose record is missing, named with the reason its
    rip's report gives, as one MANIFEST line. Never raises.

    **Why the reports, and not the records.** A scan finds the records that ARE
    there; it cannot name one that is not, because nothing on disk says a record
    was due. Each app rip's report says which passes ran and what became of each
    record: ``outcome.ripper_record`` for the last album pass (W6) and
    ``outcome.securing_pass_record`` for the securing pass (v34).

    **Cross-checked against the scan (``records``) both ways.** An album pass's
    record the report read as absent, but which the scan found (a cancelled
    ripper writes it after the report was written), is not missing; a securing
    pass's record the report says was kept, but which the scan did not find, is.

    **What it cannot see, said in the line.** A folder with no report (a script's
    ``cyanrip`` verb) names no invocation, and a report older than schema v34
    does not say what became of a securing pass's record; both are counted, never
    read as "nothing missing". Only the LAST album pass of a rip is in its report,
    so an earlier pass of a speed-ladder retry is not covered. ``report_glob`` is
    the session's own marker of a rip report, passed in so the two cannot differ.
    """
    found = {path.name for path in records}
    missing: list[str] = []
    reports = unread = pre_v34 = no_report = 0
    try:
        for folder in album_dirs:
            paths = sorted(folder.glob(report_glob))
            if not paths:
                no_report += 1
                continue
            for path in paths:
                outcome = _report_outcome(path)
                if outcome is None:
                    unread += 1
                    continue
                reports += 1
                missing += _album_pass_absence(folder.name, outcome, found)
                securing = outcome.get("securing_pass_record")
                if isinstance(securing, dict):
                    missing += _securing_pass_absence(folder.name, securing, found)
                elif outcome.get("securing_pass_started") is True:
                    pre_v34 += 1
    except Exception as exc:  # noqa: BLE001 — a fact must never stop the packing
        log.exception("could not read the rips' reports for missing records")
        return f"not determined: the reports could not be read ({exc!r})"
    said = (
        f"{len(missing)} named by {reports} rip report(s): " + "; ".join(missing)
        if missing
        else f"none named by {reports} rip report(s)"
    )
    caveats: list[str] = []
    if unread:
        caveats.append(
            f"{unread} report(s) had no readable outcome block, so not determined there"
        )
    if pre_v34:
        caveats.append(
            f"{pre_v34} securing pass(es) ran under a report older than schema v34, "
            "which does not say what became of its record: not determined"
        )
    if no_report:
        caveats.append(
            f"{no_report} folder(s) have no rip report (a script's cyanrip verb), so "
            "their invocations are not covered here"
        )
    return "; ".join([said, *caveats])


def _report_outcome(path: Path) -> dict[str, object] | None:
    """A rip report's ``outcome`` block, or ``None`` when it cannot be read."""
    try:
        if path.stat().st_size > _MAX_REPORT_BYTES:
            return None
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, ValueError) as exc:
        log.warning("could not read the rip report %s: %r", path, exc)
        return None
    outcome = data.get("outcome") if isinstance(data, dict) else None
    return outcome if isinstance(outcome, dict) else None


def _album_pass_absence(
    folder: str, outcome: Mapping[str, object], found: set[str]
) -> list[str]:
    """The album pass's record, named when the report says it did not arrive."""
    record = outcome.get("ripper_record")
    if not isinstance(record, dict):
        return []
    state = record.get("state")
    if state not in _ALBUM_RECORD_LOST:
        return []
    detail = str(record.get("detail") or "")
    if state == "absent" and detail and Path(detail).name in found:
        return []  # written after the report was: the scan has it
    if state == "not_requested":
        return [f"{folder}: album pass: its argv named no record"]
    return [f"{folder}: album pass: cyanrip's record was {state} ({detail})"]


def _securing_pass_absence(
    folder: str, block: Mapping[str, object], found: set[str]
) -> list[str]:
    """The securing pass's record, named when missing or not where it was kept."""
    state = block.get("state")
    if state == STATE_MISSING:
        return [f"{folder}: securing pass: {block.get('detail') or 'no reason given'}"]
    if state == STATE_KEPT:
        kept = str(block.get("path") or "")
        if Path(kept).name not in found:
            return [
                f"{folder}: securing pass: its report says it was kept as {kept}, "
                "and the scan of the rips folders did not find it"
            ]
    return []
