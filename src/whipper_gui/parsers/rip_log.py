"""Parse whipper's rip `.log` file into a RipLog dataclass.

Format (verified against whipper-team/whipper master, result/logger.py)
is YAML-structured with these top-level sections:

    Log created by: whipper X.Y.Z (...)
    Log creation date: YYYY-MM-DDThh:mm:ssZ

    Ripping phase information: ...
    CD metadata: ...
    TOC: ...
    Tracks:
      1. (filename: ...)
        Peak level: 0.xxxxxx
        Pre-emphasis: Yes|No
        Extraction speed: N.N X
        Extraction quality: NN.NN %
        Test CRC: XXXXXXXX
        Copy CRC: XXXXXXXX
        Status: ...
        AccurateRip v1:
          Result: ...
          Confidence: N
          Local CRC: XXXXXXXX
          Remote CRC: XXXXXXXX
        AccurateRip v2:
          (same fields)
    Conclusive status report:
      AccurateRip summary: ...
      Health status: No errors occurred|There were errors|...

    SHA-256 hash: <hex>

We don't pull in a YAML parser — the format is regular enough that a
state-machine with named-group regexes handles it cleanly. Per
CLAUDE.md, the parser degrades gracefully (returns RipLog with empty
fields for anything it can't parse) rather than crashing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class AccurateRipResult:
    """One of the two AccurateRip checks per track (v1 or v2)."""

    version: int
    result: str = ""              # "Found, exact match" / etc.
    confidence: int | None = None
    local_crc: str | None = None  # uppercase hex
    remote_crc: str | None = None # uppercase hex


@dataclass(frozen=True)
class TrackResult:
    """One track's results from the rip log."""

    number: int
    filename: str = ""
    peak_level: float | None = None
    pre_emphasis: bool | None = None
    extraction_speed: float | None = None     # in X (drive multiplier)
    extraction_quality: float | None = None   # percentage 0..100
    test_crc: str = ""
    copy_crc: str = ""
    status: str = ""
    accuraterip_v1: AccurateRipResult | None = None
    accuraterip_v2: AccurateRipResult | None = None


@dataclass(frozen=True)
class RipLog:
    """The full parsed log."""

    log_creator: str = ""
    creation_date: str = ""
    tracks: tuple[TrackResult, ...] = ()
    accuraterip_summary: str = ""
    health_status: str = ""
    sha256_hash: str = ""


# --- Line-level regexes -----------------------------------------------------

_TRACK_HEADER = re.compile(
    r"^\s+(?P<number>\d+)\.\s*\(filename:\s*(?P<filename>.+?)\)\s*$"
)
_AR_HEADER = re.compile(r"^\s+AccurateRip v(?P<version>\d+):\s*$")
_FIELD = re.compile(r"^(?P<indent>\s+)(?P<key>[\w][\w\s\-]*?):\s*(?P<value>.*)$")
_TOP_LEVEL_SECTION = re.compile(r"^(?P<name>\w[\w\s]*?):\s*$")
_SPEED = re.compile(r"^(?P<value>-?\d+(?:\.\d+)?)\s*X\s*$")
_QUALITY = re.compile(r"^(?P<value>-?\d+(?:\.\d+)?)\s*%\s*$")


def parse_rip_log(text: str) -> RipLog:
    """Parse the full text of a whipper `.log` file.

    Tolerates absent fields and unexpected lines. Returns a RipLog with
    whatever could be extracted; never raises on malformed input.
    """
    log_creator = ""
    creation_date = ""
    sha256 = ""
    summary = ""
    health = ""

    tracks: list[TrackResult] = []
    current_track: _MutableTrack | None = None
    current_ar: int | None = None  # 1 or 2; None when outside an AR block.

    in_tracks = False
    in_status = False

    for line in text.splitlines():
        # Top-of-file metadata: simple "Key: value" lines at column 0.
        if line.startswith("Log created by:"):
            log_creator = line.split(":", 1)[1].strip()
            continue
        if line.startswith("Log creation date:"):
            creation_date = line.split(":", 1)[1].strip()
            continue
        if line.startswith("SHA-256 hash:"):
            sha256 = line.split(":", 1)[1].strip()
            continue

        # Top-level section header switches our parser state.
        top = _TOP_LEVEL_SECTION.match(line)
        if top:
            name = top.group("name").strip()
            if name == "Tracks":
                in_tracks = True
                in_status = False
            elif name == "Conclusive status report":
                if current_track is not None:
                    tracks.append(current_track.build())
                    current_track = None
                in_tracks = False
                in_status = True
            else:
                # Other sections (Ripping phase information, CD
                # metadata, TOC, etc.). Leaving tracks/status mode.
                if current_track is not None:
                    tracks.append(current_track.build())
                    current_track = None
                in_tracks = False
                in_status = False
            current_ar = None
            continue

        if in_tracks:
            # A new track header flushes the previous one.
            header = _TRACK_HEADER.match(line)
            if header:
                if current_track is not None:
                    tracks.append(current_track.build())
                current_track = _MutableTrack(
                    number=int(header.group("number")),
                    filename=header.group("filename").strip(),
                )
                current_ar = None
                continue

            ar = _AR_HEADER.match(line)
            if ar and current_track is not None:
                current_ar = int(ar.group("version"))
                current_track.ar[current_ar] = {}
                continue

            field = _FIELD.match(line)
            if field and current_track is not None:
                key = field.group("key").strip()
                value = field.group("value").strip()
                indent = len(field.group("indent"))
                # AR sub-fields are indented further than track-level
                # ones. Whipper indents them by 2 more spaces (6 vs 4).
                if current_ar is not None and indent >= 6:
                    current_track.ar[current_ar][key] = value
                else:
                    current_track.fields[key] = value
                    current_ar = None
                continue

        if in_status:
            field = _FIELD.match(line)
            if not field:
                continue
            key = field.group("key").strip()
            value = field.group("value").strip()
            if key == "AccurateRip summary":
                summary = value
            elif key == "Health status":
                health = value

    # Flush a track that wasn't followed by a status section.
    if current_track is not None:
        tracks.append(current_track.build())

    return RipLog(
        log_creator=log_creator,
        creation_date=creation_date,
        tracks=tuple(tracks),
        accuraterip_summary=summary,
        health_status=health,
        sha256_hash=sha256,
    )


# --- In-flight track accumulator -------------------------------------------


class _MutableTrack:
    """Mutable scratch struct used while a track section is being parsed.

    Lives only inside parse_rip_log(); the final immutable record is
    produced by .build() at flush time.
    """

    def __init__(self, number: int, filename: str) -> None:
        self.number: int = number
        self.filename: str = filename
        self.fields: dict[str, str] = {}
        # ar[version] -> {Result, Confidence, Local CRC, Remote CRC}
        self.ar: dict[int, dict[str, str]] = {}

    def build(self) -> TrackResult:
        return TrackResult(
            number=self.number,
            filename=self.filename,
            peak_level=_parse_float(self.fields.get("Peak level")),
            pre_emphasis=_parse_yes_no(self.fields.get("Pre-emphasis")),
            extraction_speed=_parse_with_pattern(
                self.fields.get("Extraction speed"), _SPEED
            ),
            extraction_quality=_parse_with_pattern(
                self.fields.get("Extraction quality"), _QUALITY
            ),
            test_crc=self.fields.get("Test CRC", ""),
            copy_crc=self.fields.get("Copy CRC", ""),
            status=self.fields.get("Status", ""),
            accuraterip_v1=_build_ar(1, self.ar.get(1)),
            accuraterip_v2=_build_ar(2, self.ar.get(2)),
        )


def _build_ar(
    version: int, raw: dict[str, str] | None
) -> AccurateRipResult | None:
    if raw is None:
        return None
    return AccurateRipResult(
        version=version,
        result=raw.get("Result", ""),
        confidence=_parse_int(raw.get("Confidence")),
        local_crc=raw.get("Local CRC") or None,
        remote_crc=raw.get("Remote CRC") or None,
    )


# --- Tiny value parsers -----------------------------------------------------


def _parse_int(s: str | None) -> int | None:
    if s is None or not s.strip():
        return None
    try:
        return int(s)
    except ValueError:
        return None


def _parse_float(s: str | None) -> float | None:
    if s is None or not s.strip():
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _parse_yes_no(s: str | None) -> bool | None:
    if s is None:
        return None
    normalized = s.strip().lower()
    if normalized in ("yes", "true"):
        return True
    if normalized in ("no", "false"):
        return False
    return None


def _parse_with_pattern(
    s: str | None, pattern: re.Pattern[str]
) -> float | None:
    """Extract the float `value` named-group from `pattern` applied to `s`."""
    if s is None:
        return None
    match = pattern.match(s.strip())
    if not match:
        return None
    return float(match.group("value"))
