"""Wall-clock timing helpers for a rip — *actual* elapsed vs the ripper's ETA.

Why this exists (real-disc lesson, 2026-06-30 → refined 0.4.5): a 14-track disc
with two marginal tracks took **2h38m** of wall-clock while cyanrip's on-screen
ETA yo-yoed and, at the very first 0.01% tick, extrapolated to an absurd
**822h** — which we (wrongly) captured as "the estimate." cyanrip's ETA is
computed from the *current* read pass only, with no idea how many secure
re-read passes (`-Z N`) a marginal track needs, so it is, in the maintainer's
words, "useless." So we no longer record cyanrip's ETA at all. Instead the live
ETA is computed from *actual* elapsed ÷ album-fraction (stable, self-correcting;
see `workers/rip_worker._album_eta_text`), and the report records the actual
elapsed plus a **realtime multiplier** (elapsed ÷ the disc's audio length) — a
meaningful, honest archival metric. The disc's audio length comes from cyanrip's
`Total time:` line, parsed by :func:`parse_hms_to_seconds`.

Everything here is pure and **never raises** (mirrors the parser discipline):
these feed the post-rip log line and the JSON report, neither of which may ever
crash a finished rip over a formatting hiccup.
"""

from __future__ import annotations

import re

# cyanrip renders its ETA as a compact duration: "3m", "1h2m", "45s", "1h",
# "2h3m4s". We parse the hour/minute/second pieces independently so any subset
# (and any order cyanrip might print) still resolves. A bare integer is read as
# seconds. Anything unrecognised → None (the estimate is best-effort).
_ETA_PIECE = re.compile(r"(?P<value>\d+)\s*(?P<unit>[hms])", re.IGNORECASE)
_BARE_INT = re.compile(r"^\s*(?P<value>\d+)\s*$")
_UNIT_SECONDS: dict[str, int] = {"h": 3600, "m": 60, "s": 1}


def parse_eta_to_seconds(text: str | None) -> int | None:
    """Parse a cyanrip ETA string ("3m", "1h2m", "45s") into whole seconds.

    Returns None for empty/unparseable input. Never raises.
    """
    if not text:
        return None
    try:
        bare = _BARE_INT.match(text)
        if bare:
            return int(bare.group("value"))
        total = 0
        matched = False
        for piece in _ETA_PIECE.finditer(text):
            matched = True
            total += (
                int(piece.group("value")) * _UNIT_SECONDS[piece.group("unit").lower()]
            )
        return total if matched else None
    except (ValueError, KeyError):  # defensive — the regex already constrains input
        return None


_HMS = re.compile(r"^\s*(?P<h>\d{1,2}):(?P<m>\d{2}):(?P<s>\d{2}(?:\.\d+)?)\s*$")


def parse_hms_to_seconds(text: str | None) -> float | None:
    """Parse a ``HH:MM:SS(.mmm)`` duration (cyanrip's ``Total time:``) to seconds.

    Returns None for empty/unparseable input. Never raises.
    """
    if not text:
        return None
    try:
        match = _HMS.match(text)
        if not match:
            return None
        return (
            int(match.group("h")) * 3600
            + int(match.group("m")) * 60
            + float(match.group("s"))
        )
    except (ValueError, KeyError):  # defensive — the regex already constrains input
        return None


def format_duration(seconds: float | None) -> str:
    """Render a number of seconds as a compact human string ("2h 45m 13s").

    Drops leading zero units ("45m 13s", "13s") but always shows at least
    seconds. Negative or None → "unknown". Never raises.
    """
    try:
        # `not (seconds >= 0)` rejects None, NaN (all comparisons False) and
        # negatives in one go; inf is caught by the OverflowError guard below.
        if seconds is None or not seconds >= 0:
            return "unknown"
        total = int(round(seconds))
        hours, rem = divmod(total, 3600)
        minutes, secs = divmod(rem, 60)
        parts: list[str] = []
        if hours:
            parts.append(f"{hours}h")
        if minutes or hours:  # show minutes once we're past an hour, for "1h 0m 5s"
            parts.append(f"{minutes}m")
        parts.append(f"{secs}s")
        return " ".join(parts)
    except (TypeError, ValueError, OverflowError):
        return "unknown"
