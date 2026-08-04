"""The auto-fix swap addendum, and why it lives in a **sidecar** file.

## What this records

When the per-track auto-fix re-rips a track and swaps the improved read in, the
whole-disc log written by the first pass becomes *partly* untrue: its recorded
checksums for that track describe the bytes we discarded, not the file now on
disk. The archival claim has to stay honest, so something must say "that row is
superseded, here is the shipped file's read."

## Why a sidecar and not an append (round 7 lap 10, H1)

We used to append this block to the ripper's own ``.log``. That file ends with
cyanrip's ``Log FUN512:`` self-checksum line, and ``cyanrip --verify-log``
**rejects trailing content by design** — so every disc that needed an auto-fix
shipped with a log the ripper itself would call modified. The fork found it by
reading a real rig artifact.

Three things about that are worth keeping in the code rather than only in a
handshake file:

* **The question had already been asked and answered.** Round 5 asked whether an
  addendum could go after the checksum line; the answer was no, and the fork
  pinned it with a test. We appended anyway. A contract answer that lives only in
  a document is one nobody re-reads.
* **Our own integrity check could not see it.** ``self_check``'s ``log_integrity``
  verified *the EAC-style log we wrote* against *the checksum we computed* — a
  closed loop that agrees with itself no matter what we did to somebody else's
  file. Fixed alongside this (``rip_audit`` now runs ``cyanrip --verify-log`` on
  the ripper's log, which is an *independent* witness).
* **Modifying a dependency's artifact is never free.** A file another tool wrote,
  with its own verification, is that tool's evidence. Ours goes beside it.

So: the ripper's log is left **byte-exact**, and the addendum is written to
``<log stem>.platterpus-addendum.txt``. Reading a rip's log back means reading
both — :func:`read_log_with_addendum` is the single place that does it, so a
re-parse still honours the supersede (which is the bug that put the addendum in
the log's text in the first place: the GUI patched from live worker state and
only a re-parse from disk saw the stale CRCs).

## It now supersedes the whole per-track record, not just the CRC (H5)

The appended version named the CRC alone, leaving the archived AccurateRip v1/v2
values and the secure-re-read verdict describing the discarded read. Widening the
append field-by-field would have been the wrong fix — hence the record below,
which carries everything the re-rip measured about the shipped file.

Backwards compatibility: logs from before this change carry the block inline, and
:mod:`platterpus.parsers.cyanrip_log` still parses it there. The parser reads a
*shape*, not a position, so both layouts resolve to the same superseded CRCs.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Final

log: Final[logging.Logger] = logging.getLogger(__name__)

#: Suffix appended to the ripper log's stem. Deliberately long and namespaced:
#: this file sits in the user's album folder next to their music, and a reader
#: who has never heard of this program should be able to tell whose it is and
#: that it is not part of the rip itself.
ADDENDUM_SUFFIX: Final[str] = ".platterpus-addendum.txt"

#: The block's opening marker. Kept identical to the text the appended version
#: used, so a parser (ours or a third party's) recognises both layouts.
ADDENDUM_MARKER: Final[str] = "[Platterpus auto-fix addendum]"

_RULE: Final[str] = "=" * 72


@dataclass(frozen=True)
class SupersededTrack:
    """Everything the re-rip measured about the file that actually shipped.

    One record per swapped track. Every field is a *string as rendered*, not a
    parsed value: this is archival text destined for a file a person reads, and
    the structured record is the ``.platterpus.json`` report's ``retried_tracks``.
    Empty strings render as ``n/a`` rather than being omitted — a row with a
    missing field silently reads as "unchanged", which is the H5 failure again.
    """

    number: int
    filename: str = ""
    #: The shipped file's EAC-style CRC32. The one field the old append carried.
    crc: str = ""
    #: AccurateRip v1/v2/offset-variant, recomputed for the shipped read.
    accuraterip_v1: str = ""
    accuraterip_v2: str = ""
    accuraterip_offset: str = ""
    #: The secure re-read verdict for the shipped read, e.g. "converged after 5
    #: reads". The archived first-pass block says "not attempted", which is true
    #: of the read it describes and false of the file on disk.
    secure_reread: str = ""


def addendum_path_for(log_path: str | Path) -> Path:
    """Where the sidecar for ``log_path`` goes.

    ``…/Album.log`` → ``…/Album.platterpus-addendum.txt``. Uses ``with_suffix("")``
    on the *name* only, so a folder containing a dot cannot lose part of its path.
    """
    path = Path(log_path)
    return path.with_name(path.stem + ADDENDUM_SUFFIX)


def _row(label: str, value: str) -> str:
    return f"      {label:<22}{value or 'n/a'}"


def render_addendum(trigger: str, swapped: list[SupersededTrack]) -> str:
    """The sidecar's full text. Pure — no I/O — so it is testable as text.

    ``trigger`` is why the re-rip happened (``"accuraterip"`` or anything else,
    which means read instability). Returns ``""`` for an empty track list so a
    caller cannot write an empty file that reads as "no supersede happened" when
    it means "we had nothing to say".
    """
    if not swapped:
        return ""
    why = (
        "did not match AccurateRip on the first pass"
        if trigger == "accuraterip"
        else "did not read consistently on the first pass"
    )
    lines: list[str] = [
        _RULE,
        ADDENDUM_MARKER,
        _RULE,
        "This file accompanies the ripper's whole-disc log in this folder and",
        "supersedes part of it. The ripper's log is left BYTE-EXACT so that",
        "`cyanrip --verify-log` still verifies it; that is why this is a separate",
        "file rather than text appended to it.",
        "",
        f"The track(s) below {why} and were re-ripped to secure them; the improved",
        "read was swapped in. Every value below describes the file ACTUALLY ON DISK",
        "and supersedes the value recorded for that track in the log beside it —",
        "including the AccurateRip results and the secure-re-read verdict, which",
        "the log records for the read that was discarded.",
        "",
    ]
    for entry in swapped:
        shown = entry.filename or f"track {entry.number}"
        # The "  Track N (name): CRC XXXXXXXX" line keeps the exact shape the
        # appended version used, because our parser matches on it and a real
        # rig log in output_reference/ still carries it inline.
        lines.append(f"  Track {entry.number} ({shown}): CRC {entry.crc or 'n/a'}")
        lines.append(_row("AccurateRip v1:", entry.accuraterip_v1))
        lines.append(_row("AccurateRip v2:", entry.accuraterip_v2))
        lines.append(_row("AccurateRip +450:", entry.accuraterip_offset))
        lines.append(_row("Secure re-read:", entry.secure_reread))
        lines.append("")
    lines.append(_RULE)
    return "\n".join(lines) + "\n"


def write_addendum(
    log_path: str | Path, trigger: str, swapped: list[SupersededTrack]
) -> Path | None:
    """Write the sidecar beside ``log_path``. Returns the path, or ``None``.

    Best-effort by design: a write failure is logged (at WARNING, and to the
    diagnostics collector, so it reaches a bug report) and swallowed, because
    losing the addendum must never abort a rip whose audio is already correct.
    The report's ``retried_tracks`` is the structured record either way.
    """
    text = render_addendum(trigger, swapped)
    if not text:
        return None
    target = addendum_path_for(log_path)
    try:
        target.write_text(text, encoding="utf-8")
    except OSError as exc:
        from platterpus import diagnostics

        diagnostics.warning(
            "addendum.write_failed",
            (
                f"could not write the auto-fix addendum to {target} — the rip's "
                "audio is unaffected, but the folder's text record does not say "
                "which track(s) were re-ripped; the .platterpus.json report's "
                "retried_tracks does"
            ),
            detail=str(exc),
        )
        return None
    return target


def addendum_text(log_path: str | Path) -> str:
    """The sidecar's text for ``log_path``, or ``""`` if there is none.

    Never raises. A missing sidecar is the *ordinary* case — most rips need no
    auto-fix — so absence is silent; an unreadable one that exists is not, and is
    recorded, because that is a fact we had and would otherwise discard.
    """
    sidecar = addendum_path_for(log_path)
    try:
        return sidecar.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""
    except OSError as exc:
        from platterpus import diagnostics

        diagnostics.warning(
            "addendum.log_unreadable",
            (
                f"an auto-fix addendum exists at {sidecar} but could not be read, so "
                "this rip's superseded checksums are not being applied — the values "
                "shown for any re-ripped track describe the read that was discarded"
            ),
            detail=str(exc),
        )
        return ""


def with_addendum(text: str, log_path: str | Path) -> str:
    """``text`` (already-decoded log content) plus its sidecar, if any.

    Split out from :func:`read_log_with_addendum` because one caller decodes the
    log itself (``rip_files`` handles a BOM / UTF-16 log via ``decode_log_bytes``)
    and must not lose that handling to reach the addendum.
    """
    extra = addendum_text(log_path)
    if not extra.strip():
        return text
    if text and not text.endswith("\n"):
        text += "\n"
    return text + "\n" + extra


def read_log_with_addendum(log_path: str | Path) -> str:
    """A rip log's text with its sidecar addendum appended, if one exists.

    **Every read-back of a rip log must go through here** (or
    :func:`with_addendum`). A re-parse that reads the log alone gets checksums for
    bytes that are not on disk — the original reason the addendum existed at all,
    and the trap moving it to a sidecar could have walked straight into:
    *fixing H1 by making the supersede invisible instead*.
    ``tests/test_rip_addendum.py`` sweeps the source for log-parsing reads that
    bypass these two functions, because a rule remembered is a rule that decays.

    Never raises: a missing or unreadable log yields ``""``.
    """
    path = Path(log_path)
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return with_addendum(text, path)


def read_any_log(log_path: str | Path) -> str:
    """Any rip log's text — **encoding sniffed, addendum applied**. One reader.

    :func:`read_log_with_addendum` assumes UTF-8, which is right for cyanrip and whipper
    and wrong for EAC (UTF-16). The three CLI tools in ``scripts/`` all have to accept
    either, so each of them grew the same two-line ``decode_log_bytes(p.read_bytes())`` —
    and **all three of them thereby skipped the addendum.**

    Found 2026-08-04 when `scripts/eac_parity.py` reported the rig's Police rip as
    **13/14 NOT parity**: it read track 5's CRC as ``6902BCF0``, the pass Platterpus
    *discarded* after re-ripping, where the file on disk is ``E0036697`` — EAC's own value.
    The rip was 14/14. Widening the sweep that should have caught it then found
    ``render_eac_log.py`` and ``rip_report.py`` doing the same, so the archival
    EAC-compatible log and the regenerated report were both exposed to it too.

    **Three copies of a read is three chances to forget the sidecar**, which is the same
    argument that made `handshake.sort_key` public. So: one function, and the scripts call
    it rather than spelling the read themselves.

    Never raises: a missing or unreadable log yields ``""``.
    """
    from platterpus.parity import decode_log_bytes  # noqa: PLC0415 — avoids a cycle

    path = Path(log_path)
    try:
        text = decode_log_bytes(path.read_bytes())
    except OSError:
        return ""
    return with_addendum(text, path)


__all__ = [
    "ADDENDUM_MARKER",
    "ADDENDUM_SUFFIX",
    "SupersededTrack",
    "addendum_path_for",
    "addendum_text",
    "read_any_log",
    "read_log_with_addendum",
    "render_addendum",
    "with_addendum",
    "write_addendum",
]
