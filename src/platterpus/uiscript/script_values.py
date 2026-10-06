"""Two pure readers of a script's argument values, shared by the runner and the
run estimate.

``coerce_setting`` turns a ``set`` line's text into the type the config field
holds; ``parse_track_spec`` turns ``select-tracks 1,3,5-7`` into track numbers.
They lived in ``runner.py`` until 2026-10-06, when the acceptance run's overall
estimate (``uiscript/run_estimate.py``) had to read a script's settings and
selections BEFORE it runs: a second reading of the same text would be a second
answer to one question, so both callers import these. Pure; no Qt.
"""

from __future__ import annotations

from typing import Final

#: Widest range a single `select-tracks` chunk may expand to. A CD holds 99 tracks;
#: this is generous and still refuses a pasted typo.
MAX_TRACK_RANGE: Final[int] = 200


def coerce_setting(current: object, raw: str) -> tuple[object, str]:
    """Turn a script's string into the type the config field already holds.

    Returns ``(value, "")`` or ``(None, reason)``. The *existing* value decides the
    type rather than a table of field names, so a new setting needs no entry here —
    the same reason the verb takes a config field name at all.

    ``bool`` is checked before ``int`` because ``bool`` is an ``int`` subclass, and a
    field holding ``False`` would otherwise be parsed as a number and set to ``0`` —
    equal to ``False`` today and a different thing the moment anything compares
    identity or writes it back to TOML.
    """
    text = raw.strip()
    if isinstance(current, bool):
        lowered = text.casefold()
        if lowered in {"on", "true", "yes", "1"}:
            return True, ""
        if lowered in {"off", "false", "no", "0"}:
            return False, ""
        return None, f"{text!r} is not on/off (accepted: on, off, true, false, yes, no)"
    if isinstance(current, int):
        try:
            return int(text), ""
        except ValueError:
            return None, f"{text!r} is not a whole number"
    if isinstance(current, float):
        try:
            return float(text), ""
        except ValueError:
            return None, f"{text!r} is not a number"
    if isinstance(current, str):
        return text, ""
    return None, f"settings of type {type(current).__name__} cannot be set by script"


def parse_track_spec(spec: str) -> tuple[list[int], str]:
    """``"1,3,5-7"`` → ``[1, 3, 5, 6, 7]``. Returns ``(numbers, "")`` or ``([], why)``.

    Bounded deliberately: a range is capped so a typo like ``1-999999`` is refused
    rather than materialised into a list that stalls the GUI thread building it.
    """
    numbers: set[int] = set()
    for chunk in spec.replace(" ", "").split(","):
        if not chunk:
            continue
        if "-" in chunk.lstrip("-"):
            low_text, _, high_text = chunk.partition("-")
            try:
                low, high = int(low_text), int(high_text)
            except ValueError:
                return [], f"{chunk!r} is not a track range like 5-7"
            if low > high:
                return [], f"{chunk!r} counts backwards"
            if high - low > MAX_TRACK_RANGE:
                return [], f"{chunk!r} spans more than {MAX_TRACK_RANGE} tracks"
            numbers.update(range(low, high + 1))
            continue
        try:
            numbers.add(int(chunk))
        except ValueError:
            return [], f"{chunk!r} is not a track number"
    if not numbers:
        return [], f"{spec!r} named no tracks"
    return sorted(numbers), ""
