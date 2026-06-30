"""Wall-clock timing helpers for a rip — *actual* elapsed vs the ripper's ETA.

Why this exists (real-disc lesson, 2026-06-30): a 14-track disc with two
marginal tracks took **2h45m** of wall-clock to rip, while cyanrip's on-screen
ETA sat at "33-45m" the whole time. cyanrip's ETA is computed from the *current*
read pass only — it has no way to know how many secure re-read passes (`-Z N`)
a marginal track will need, so it systematically under-estimates and is, in the
maintainer's words, "useless." The debug record therefore must capture the
**actual** elapsed time (which only the GUI knows — cyanrip's log records the
disc's *audio* duration and a finish timestamp, but never its own run time) and,
for honesty, the ripper's estimate alongside it so the gap is visible.

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
