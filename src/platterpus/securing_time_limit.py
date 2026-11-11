# SPDX-License-Identifier: GPL-3.0-only
"""The securing pass's time limit: rule 2 of the chase budget, where cyanrip carries it.

:mod:`platterpus.chase_budget` states rule 2 (TASKS R49, round 39): a track's
re-reads may take the larger of 5 x its length and 2 x its album-pass read time.
The verified-read chase checks it itself, between single reads. The securing
pass reads with ``-Z``, so there the fork's own ``--reread-time-limit`` (``.28``
on) can carry it, checked between whole-track reads inside one cyanrip run; this
module turns the pass's tracks into that one number. The flag's words, range and
gate are ``adapters/reread_time_limit_args.py``.

Pure, no Qt, no I/O; never raises.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Mapping, Sequence

from platterpus.adapters.reread_time_limit_args import REREAD_TIME_LIMIT_MAX_SECONDS
from platterpus.chase_budget import (
    read_elapsed_seconds,
    time_budget_seconds,
    track_seconds,
)

log = logging.getLogger(__name__)


def securing_pass_time_limit(
    tracks: Sequence[int], album_tracks: Mapping[int, object]
) -> int | None:
    """Rule 2 for the securing pass's ``-Z`` reads, in cyanrip's whole seconds.

    Where it fits: the securing pass reads with ``-Z``, so the fork's
    ``--reread-time-limit`` carries rule 2 there (``.28`` on; the backend sends
    it only to a build whose contract lists it). The option is one value for the
    whole run, so it is the LARGEST of the pass's tracks' budgets: no track is cut
    below its own. ``None`` when any track's budget cannot be computed (no stated
    length): the count alone then bounds the pass, as before round 39, rather
    than a limit taken from another track. ``album_tracks`` is the album pass's
    record per track. Rounded up to a whole second and kept within the option's
    range (1 to INT32_MAX). Never raises.
    """
    try:
        budgets: list[float] = []
        for number in tracks:
            album = album_tracks.get(number)
            budget = time_budget_seconds(
                track_seconds(album), read_elapsed_seconds(album)
            )
            if budget is None:
                return None
            budgets.append(budget)
        if not budgets:
            return None
        return max(1, min(math.ceil(max(budgets)), REREAD_TIME_LIMIT_MAX_SECONDS))
    except Exception:  # noqa: BLE001 — no limit is the behaviour before round 39
        log.exception("securing pass time limit failed; sending none")
        return None
