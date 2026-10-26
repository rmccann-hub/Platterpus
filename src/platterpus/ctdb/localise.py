# SPDX-License-Identifier: GPL-3.0-only
"""Locate the samples a rip differs from a CTDB entry in (TASKS R43).

What EAC's CTDB plugin prints as ``(1416/1441) Differs in 16 samples
@04:04:68,04:05:17,04:11:32``: CUETools' ``CDRepairEncode.VerifyParity`` (LGPL,
``CUETools.AccurateRip/CDRepair.cs``), rebuilt clean-room (KDD-16) from its
published behaviour and the mathematics, with no code copied:

1. compute OUR syndromes over the disc's audio, one streamed pass
   (:mod:`platterpus.ctdb.syndromes`, numpy);
2. fetch the entry's syndromes, its parity record (``adapters/ctdb_parity.py``),
   and check its column 0 against the lookup's ``syndrome`` attribute, as
   CUETools' ``FetchDB`` does;
3. find the entry's alignment: the offset where our column-0 syndromes equal its
   ``syndrome`` attribute (CUETools' ``FindOffset``), else where its per-track
   CRCs placed it (``matching.entry_offsets``), else 0;
4. XOR the two at that alignment and decode each differing column
   (:mod:`platterpus.ctdb.rs_decode`);
5. **close the loop**: apply the corrections to our whole-disc CRC and require
   the entry's CRC. A decode that does not reproduce it locates nothing.

Step 5 is what makes a located sample a measurement rather than an inference: a
wrong alignment, a corrupt record or more errors than the parity can carry all
fail it, and fail to "not determined", never to a list of positions.

**Which entries.** Those with a parity record that our whole disc does not
match and that weigh at least as much as the one it does (all of them for a
no-match), strongest first, at most :data:`MAX_ENTRIES`. Locating our difference
from an entry weaker than the one we match answers nothing anyone asked.

**Bounded.** One decode pass over the disc, :data:`BUDGET_S` seconds in all;
running out records "not determined" with the reason. Memory is the syndromes
module's (a few MB) plus one track's PCM, which the caller's decoder holds.
Runs on the CTDB worker thread, never the GUI thread (``workers/ctdb_worker.py``).
Never raises for an expected failure: each becomes a reason.
"""

from __future__ import annotations

import logging
import subprocess
import time
from collections.abc import Iterable, Mapping, Sequence

from platterpus.adapters.ctdb_client import CTDBClient, CtdbEntry
from platterpus.ctdb import decode
from platterpus.ctdb.differences import (
    CtdbLocalisation,
    EntryLocalisation,
    LocalisationStatus,
)
from platterpus.ctdb.matching import entry_offsets, match_disc
from platterpus.deps.registry import probe_dependency

log = logging.getLogger(__name__)

#: At most this many entries are located against (each is a 376 KB fetch).
MAX_ENTRIES: int = 3

#: The whole localisation's time bound, decode pass included.
BUDGET_S: float = 300.0

_NOT_NEEDED_REASON: str = (
    "no CTDB entry with a parity record outweighs the one this rip matches"
)


def candidates(entries: Sequence[CtdbEntry], disc_crcs: Mapping[int, int]) -> list[int]:
    """Indices of the entries worth locating against, strongest first (module docstring)."""
    matched = match_disc(entries, disc_crcs)
    floor = max((entries[i].confidence for i in matched), default=0)
    chosen = [
        index
        for index, entry in enumerate(entries)
        if index not in matched and entry.parity_url and entry.confidence >= floor
    ]
    chosen.sort(key=lambda i: (-entries[i].confidence, i))
    return chosen[:MAX_ENTRIES]


def _not_determined(reason: str, entries: Iterable[CtdbEntry] = ()) -> CtdbLocalisation:
    rows = tuple(
        EntryLocalisation(
            e.entry_id, e.confidence, LocalisationStatus.NOT_DETERMINED, reason=reason
        )
        for e in entries
    )
    return CtdbLocalisation(LocalisationStatus.NOT_DETERMINED, reason, rows)


def localise_disc(
    entries: Sequence[CtdbEntry],
    disc_crcs: Mapping[int, int],
    track_crcs: Sequence[Mapping[int, int]],
    chunks: Iterable[bytes],
    total_frames: int,
    client: CTDBClient,
    *,
    budget_s: float = BUDGET_S,
) -> CtdbLocalisation:
    """Locate our differences from the strongest differing entries. Never raises.

    ``disc_crcs`` and ``track_crcs`` are what the sweep measured; ``chunks`` is a
    FRESH pass over the disc's PCM (a generator that decodes on demand, so a disc
    that needs no localisation is never decoded twice). Steps 2 to 5 of the module
    docstring are :mod:`platterpus.ctdb.verify_parity`, once per entry.
    """
    chosen = candidates(entries, disc_crcs)
    if not chosen:
        return CtdbLocalisation(LocalisationStatus.NOT_NEEDED, _NOT_NEEDED_REASON)
    picked = [entries[i] for i in chosen]
    probe = probe_dependency("numpy")
    if probe is None or not probe.present:
        return _not_determined("numpy is not installed", picked)
    try:
        # Imported here, not at the top, because these two import numpy and the
        # registry has only just said it is installed (Critical rule #6).
        from platterpus.ctdb import syndromes, verify_parity
    except ImportError as exc:  # installed per its metadata, yet unimportable
        return _not_determined(f"numpy could not be imported ({exc})", picked)

    columns = syndromes.layout(total_frames)
    if columns is None:
        return _not_determined("the disc is too short to hold one parity row", picked)
    deadline = time.monotonic() + budget_s
    accumulator = syndromes.SyndromeAccumulator(columns, deadline)
    try:
        for chunk in chunks:
            if not accumulator.feed(chunk):
                break
    except (
        decode.DecoderUnavailable,
        OSError,
        RuntimeError,
        subprocess.TimeoutExpired,
    ) as exc:
        return _not_determined(f"decode error ({exc})", picked)
    ours = accumulator.finish()
    if ours is None:
        why = (
            f"stopped at the {budget_s:.0f} s time bound"
            if accumulator.stopped
            else "the decoded audio did not reach the end of the parity window"
        )
        return _not_determined(why, picked)

    placed = entry_offsets(entries, track_crcs)
    rows = [
        verify_parity.locate_entry(
            entries[index], placed.get(index), ours, disc_crcs, client, deadline
        )
        for index in chosen
    ]
    located = any(r.status is LocalisationStatus.LOCATED for r in rows)
    status = (
        LocalisationStatus.LOCATED if located else LocalisationStatus.NOT_DETERMINED
    )
    reason = "" if located else (rows[0].reason if rows else "")
    return CtdbLocalisation(status, reason, tuple(rows))
