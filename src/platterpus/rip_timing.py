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
# Bounded quantifiers: unbounded, `_ETA_PIECE` is quadratic in the input length
# (measured at 67 ms on a 2000-character digit run), and its input is a
# subprocess's ETA string — external text, arbitrary length. Eight digits is over
# three years in seconds, so nothing real is lost.
_ETA_PIECE = re.compile(r"(?P<value>\d{1,8})\s*(?P<unit>[hms])", re.IGNORECASE)
_BARE_INT = re.compile(r"^\s*(?P<value>\d{1,8})\s*$")
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

#: ``MM:SS.FF`` — cyanrip's *other* duration shape, where ``FF`` is **CD frames**
#: (1/75 s, 0–74), not hundredths. Minutes are not modulo 60, so a 90-minute disc
#: prints ``90:12.34``; the pattern allows three digits for that reason.
_MSF = re.compile(r"^\s*(?P<m>\d{1,3}):(?P<s>\d{2})\.(?P<f>\d{2})\s*$")

#: CD frames per second. A sector *is* a frame: 75 per second, by the Red Book.
CD_FRAMES_PER_SECOND: int = 75


def parse_cd_duration_to_seconds(text: str | None) -> float | None:
    """Parse either duration shape cyanrip prints, in real seconds.

    **Two shapes, and the difference is not cosmetic.** Verified from the fork's
    source at the pinned commit (``src/utils.h``, ``snprintf("%02i:%02i.%02i",
    min, sec, remain)`` with ``remain = frames % 75``) and stated in their
    published contract's units block:

    * ``HH:MM:SS.mmm`` — three colon-separated fields; the fraction is
      **milliseconds**. What a full-length disc's ``Total time:`` looks like.
    * ``MM:SS.FF`` — two fields; the fraction is **CD frames**, 1/75 s, range
      0–74. What a short disc and every per-track ``Duration:`` looks like.

    Reading ``.57`` as hundredths where it means 57 frames is wrong by up to
    **0.98 s** — 57/75 = 0.76 s, not 0.57 s — and reading ``.74`` as hundredths
    is wrong in the same direction on every track of every disc. The real rip
    that motivated this printed ``Total time:     59:42.57``.

    Discriminate on **colon count**, which is what their contract tells a
    consumer to do: two colons means milliseconds, one means frames. Guessing
    from the fraction's magnitude cannot work — ``.34`` is a legal value in both.

    Returns None for empty/unparseable input. Never raises: this is a parser of
    external output.
    """
    if not text:
        return None
    try:
        hms = _HMS.match(text)
        if hms is not None:
            return (
                int(hms.group("h")) * 3600
                + int(hms.group("m")) * 60
                + float(hms.group("s"))
            )
        msf = _MSF.match(text)
        if msf is None:
            return None
        frames = int(msf.group("f"))
        # A frame field above 74 is not a frame field. Rather than silently
        # producing a value >1 s from a fraction, refuse: the input does not
        # match either documented shape, and inventing a reading of it is how a
        # duration quietly gains a second.
        if frames >= CD_FRAMES_PER_SECOND:
            return None
        return (
            int(msf.group("m")) * 60
            + int(msf.group("s"))
            + frames / CD_FRAMES_PER_SECOND
        )
    except (ValueError, KeyError):  # defensive — the regexes already constrain input
        return None


def parse_hms_to_seconds(text: str | None) -> float | None:
    """Backwards-compatible alias for :func:`parse_cd_duration_to_seconds`.

    Kept because the name is used at several call sites and in tests; the old
    behaviour (``HH:MM:SS`` only, silently returning None for ``MM:SS.FF``) was
    the defect, so the alias deliberately points at the *fixed* function rather
    than preserving it.
    """
    return parse_cd_duration_to_seconds(text)


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
