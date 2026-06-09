"""Parse cyanrip's rip log into the shared RipLog record.

cyanrip writes a per-album ``Album name.log`` next to the FLACs (one per
output format). Its content mirrors what cyanrip prints to stdout — the
start report, one block per track, and a finish report. Exact format
strings verified against cyanreg/cyanrip master ``src/cyanrip_log.c``:

    cyanrip 0.9.3.1 (...)
    Drive used:     PIONEER BD-RW   BDR-209D (revision 1.10)
    Offset:         +667 samples
    ...
    Track 5 ripped and encoded successfully!
      Preemphasis:   none detected
        Duration:    03:51.44
      EAC CRC32:     A1B2C3D4 (after 2 rips)
      Accurip:       found in database (max confidence: 3)
        Accurip v1:  12345678 (accurately ripped, confidence 3)
        Accurip v2:  9ABCDEF0 (not found, either a new pressing, or bad rip)
    ...
    Tracks ripped accurately: 15/16
    Ripping errors: 0
    Ripping finished at 2026-06-09 12:34:56

We reuse the whipper parser's dataclasses (`RipLog`, `TrackResult`,
`AccurateRipResult`) so the GUI's results table, disc panel, and fidelity
summary work identically on both backends. Mapping notes:

* cyanrip computes ONE EAC CRC32 per track (no whipper-style test+copy
  dual read) — it lands in ``copy_crc`` and ``test_crc`` stays empty, so
  the fidelity summary can tell the two verification models apart.
* `health_status` is normalized to whipper's "No errors occurred"
  phrasing when cyanrip reports 0 ripping errors, so downstream string
  checks behave the same.

Like every parser of external output, this must never raise on arbitrary
text — it degrades to empty fields (institutional rule, docs/testing.md).
"""

from __future__ import annotations

import re

from whipper_gui.parsers.rip_log import (
    AccurateRipResult,
    RipLog,
    RippingInfo,
    TrackResult,
)

# First meaningful line of any cyanrip log/output: "cyanrip 0.9.3.1 (tag)".
_HEADER = re.compile(r"^cyanrip\s+(?P<version>\S+)")
_DRIVE = re.compile(r"^Drive used:\s+(?P<drive>.+?)\s*$")
# "Offset:         +667 samples" (sign printed explicitly by cyanrip).
_OFFSET = re.compile(r"^Offset:\s+(?P<sign>[+-])(?P<value>\d+)\s+samples")
# A track block opens with its outcome line.
_TRACK_START = re.compile(
    r"^Track (?P<number>\d+) "
    r"(?P<what>ripped and encoded successfully!|ripped and encoded with errors\.|is data:)"
)
_PREEMPHASIS = re.compile(r"^\s+Preemphasis:\s+(?P<text>.+?)\s*$")
# "  EAC CRC32:     A1B2C3D4" with an optional "(after N rips)" suffix.
_EAC_CRC = re.compile(r"^\s+EAC CRC32:\s+(?P<crc>[0-9A-Fa-f]{8})")
# "    Accurip v1:  12345678 (accurately ripped, confidence 3)" — the
# parenthetical varies ("not found, either a new pressing, or bad rip").
_ACCURIP_TRACK = re.compile(
    r"^\s+Accurip v(?P<version>[12]):\s+(?P<crc>[0-9A-Fa-f]{8})"
    r"(?:\s+\((?P<result>[^)]*)\))?"
)
_ACCURIP_CONFIDENCE = re.compile(r"confidence\s+(?P<value>\d+)")
# Finish report.
_ACCURATE_TOTAL = re.compile(
    r"^Tracks ripped accurately:\s+(?P<hit>\d+)/(?P<total>\d+)"
)
_RIP_ERRORS = re.compile(r"^Ripping errors:\s+(?P<count>\d+)")
_FINISHED_AT = re.compile(r"^Ripping finished at\s+(?P<when>.+?)\s*$")


def looks_like_cyanrip_log(text: str) -> bool:
    """True if `text` is cyanrip output (vs whipper's YAML-ish log).

    The first non-blank line of a cyanrip log is its version banner;
    whipper logs start with "Log created by: whipper ...".
    """
    for line in text.splitlines():
        if line.strip():
            return bool(_HEADER.match(line))
    return False


def parse_cyanrip_log(text: str) -> RipLog:
    """Parse a cyanrip log into the backend-neutral RipLog.

    Missing pieces degrade to empty/None — including a log truncated by a
    crash mid-rip. Never raises on arbitrary input.
    """
    log_creator = ""
    creation_date = ""
    drive = ""
    read_offset: int | None = None
    accuraterip_summary = ""
    health_status = ""
    tracks: list[TrackResult] = []

    # Mutable fields of the track block currently being read; flushed into
    # `tracks` when the next block (or the end of input) is reached.
    current: dict | None = None

    def flush() -> None:
        nonlocal current
        if current is None:
            return
        tracks.append(
            TrackResult(
                number=current["number"],
                pre_emphasis=current["pre_emphasis"],
                copy_crc=current["copy_crc"],
                status=current["status"],
                accuraterip_v1=current["v1"],
                accuraterip_v2=current["v2"],
            )
        )
        current = None

    for line in text.splitlines():
        match = _HEADER.match(line)
        if match and not log_creator:
            log_creator = f"cyanrip {match.group('version')}"
            continue

        match = _DRIVE.match(line)
        if match:
            drive = match.group("drive")
            continue

        match = _OFFSET.match(line)
        if match:
            value = int(match.group("value"))
            read_offset = -value if match.group("sign") == "-" else value
            continue

        match = _TRACK_START.match(line)
        if match:
            flush()
            what = match.group("what")
            if what == "is data:":
                status = "data track (skipped)"
            elif what.endswith("successfully!"):
                status = "ripped successfully"
            else:
                status = "ripped with errors"
            current = {
                "number": int(match.group("number")),
                "pre_emphasis": None,
                "copy_crc": "",
                "status": status,
                "v1": None,
                "v2": None,
            }
            continue

        if current is not None:
            match = _PREEMPHASIS.match(line)
            if match:
                current["pre_emphasis"] = not match.group("text").startswith("none")
                continue

            match = _EAC_CRC.match(line)
            if match:
                current["copy_crc"] = match.group("crc").upper()
                continue

            match = _ACCURIP_TRACK.match(line)
            if match:
                result_text = match.group("result") or ""
                conf_match = _ACCURIP_CONFIDENCE.search(result_text)
                ar = AccurateRipResult(
                    version=int(match.group("version")),
                    result=result_text,
                    confidence=int(conf_match.group("value")) if conf_match else None,
                    local_crc=match.group("crc").upper(),
                )
                current[f"v{ar.version}"] = ar
                continue

        match = _ACCURATE_TOTAL.match(line)
        if match:
            accuraterip_summary = (
                f"{match.group('hit')}/{match.group('total')} tracks "
                "ripped accurately (AccurateRip)"
            )
            continue

        match = _RIP_ERRORS.match(line)
        if match:
            count = int(match.group("count"))
            # Same phrasing as whipper's healthy verdict so downstream
            # string checks treat both backends alike.
            health_status = (
                "No errors occurred" if count == 0 else f"{count} ripping errors"
            )
            continue

        match = _FINISHED_AT.match(line)
        if match:
            creation_date = match.group("when")
            continue

    flush()
    return RipLog(
        log_creator=log_creator,
        creation_date=creation_date,
        ripping_info=RippingInfo(
            drive=drive,
            extraction_engine=log_creator,
            read_offset_correction=read_offset,
        ),
        tracks=tuple(tracks),
        accuraterip_summary=accuraterip_summary,
        health_status=health_status,
    )
