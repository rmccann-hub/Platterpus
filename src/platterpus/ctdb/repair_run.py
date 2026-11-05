# SPDX-License-Identifier: GPL-3.0-only
"""The thin caller: repair a rip from the CTDB verify's own result (TASKS R43, R133).

``ctdb/repair.py`` is the core and takes every input explicitly; this is the one
place that reads them off a :class:`~platterpus.ctdb.verify.CtdbVerifyResult`
and the files, so the app's automatic repair after a rip
(``workers/ctdb_repair_worker.py``) calls one function and cannot assemble the
inputs a second way. It adds what the verify does not keep: each file's frame
count, read by ``metaflac`` (``decode.total_samples``), so the plan can refuse a
file that is not whole CD sectors; and each track's own CTDB CRC at offset 0,
which the record names as ``ctdb_crc_before`` when the entry sits at offset 0.

Returns the verify result with ``repair`` set, which is how the rip report gets
``ctdb.repair`` (schema 44). Every other field stays what the verify MEASURED,
before the repair: a repaired rip reads "repaired" beside the verdict that led
to it, and only a fresh verify measures the repaired files (``after_repair``).
Blocking, like the core: off the GUI thread.

Two pure predicates live here too, because they are questions about the same
verify result and the same rip log, and the worker and the window must ask them
the same way (``CLAUDE.md``: one predicate, N callers):

* :func:`differs_from_strongest`, whether a repair should be attempted at all
  (the owner's word of 2026-11-05, KDD-47 amended: no button);
* :func:`accuraterip_answers`, AccurateRip's per-track answer from the rip's own
  log, which the plan uses to refuse rewriting a track AccurateRip verified.
"""

from __future__ import annotations

import dataclasses
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

from platterpus.adapters.flac_rewrite import FlacRewriter
from platterpus.ctdb import decode
from platterpus.ctdb.matching import match_disc
from platterpus.ctdb.repair import PcmDecoder, repair_rip
from platterpus.ctdb.repair_types import refused
from platterpus.ctdb.toc import SamplesProbe
from platterpus.ctdb.verify import CtdbVerifyResult, Verdict
from platterpus.data_tracks import is_data_track
from platterpus.parsers.rip_log import track_accuraterip_verified
from platterpus.verdict import track_accuraterip_contradiction

#: The verdicts in which the lookup happened AND our audio was compared with it.
#: Only these can say the rip differs from an entry.
_COMPARED: frozenset[Verdict] = frozenset({Verdict.MATCH, Verdict.NO_MATCH})


def differs_from_strongest(result: object) -> bool:
    """Whether this CTDB result says the rip differs from CTDB's strongest entry.

    The trigger for the automatic repair. True when CTDB was looked up and our
    audio compared (a MATCH or a NO_MATCH), our whole-disc CRCs were measured,
    and no entry carrying the most submissions equals our audio at any offset
    the sweep measured: a NO_MATCH, or a MATCH with a weaker entry only (an
    outvoted match, the reference disc's track 5 on 2026-11-04). False for
    everything else: a match with the strongest entry is the version of the disc
    most people hold, and a check that compared nothing has no difference to
    repair. Duck-typed and pure; never raises.

    True does not mean the repair will happen. The plan still refuses every case
    it cannot place or prove (``repair_plan.py``), and the refusal is then what
    the user is told.
    """
    try:
        if getattr(result, "verdict", None) not in _COMPARED:
            return False
        entries = tuple(getattr(result, "entries", ()) or ())
        disc_crcs = getattr(result, "disc_crcs", None) or {}
        if not entries or not disc_crcs:
            return False
        best = max(int(getattr(entry, "confidence", 0) or 0) for entry in entries)
        if best <= 0:
            return False
        matched = match_disc(entries, disc_crcs)
        return not any(
            int(getattr(entries[index], "confidence", 0) or 0) == best
            for index in matched
        )
    except (AttributeError, TypeError, ValueError):
        return False


def accuraterip_answers(
    rip_log: object, file_count: int
) -> dict[int, bool | None] | None:
    """AccurateRip's answer per track, keyed by the track's place among the files.

    ``True`` where AccurateRip verified the track (either version matched),
    ``False`` where it compared the track and did not verify it
    (``verdict.track_accuraterip_contradiction``), ``None`` where it said
    nothing. Keyed 1..``file_count`` in disc order, the numbering the repair
    plan uses (the i-th file is the i-th audio track).

    **``None`` for the whole answer when the log's audio tracks cannot be lined
    up with the files** (no log, or a different count). The caller must then
    refuse: the AccurateRip guard is what stops the repair rewriting a track
    AccurateRip verified, and a guard fed nothing is a guard that cannot fail.
    Pure; never raises.
    """
    try:
        tracks = [
            t for t in (getattr(rip_log, "tracks", ()) or ()) if not is_data_track(t)
        ]
    except (AttributeError, TypeError):
        return None
    if file_count <= 0 or len(tracks) != file_count:
        return None
    answers: dict[int, bool | None] = {}
    for place, track in enumerate(tracks, start=1):
        try:
            if track_accuraterip_verified(track):
                answers[place] = True
            elif track_accuraterip_contradiction(track) is not None:
                answers[place] = False
            else:
                answers[place] = None
        except (AttributeError, TypeError, ValueError):
            answers[place] = None
    return answers


def _track_crcs_before(result: CtdbVerifyResult) -> list[dict[int, int]]:
    """Each track's CTDB CRC by offset, as the verify measured it (offset 0 only).

    ``CtdbTrackResult.our_crc`` is the track's CRC at offset 0, so the record's
    ``ctdb_crc_before`` is filled when the entry repaired toward sits at offset
    0 and stays null otherwise, rather than being called measured when it was
    not.
    """
    rows: list[dict[int, int]] = []
    for track in result.tracks:
        crc = getattr(track, "our_crc", None)
        rows.append({0: crc} if isinstance(crc, int) else {})
    return rows


def repair_verified_rip(
    flac_paths: Sequence[Path],
    result: CtdbVerifyResult,
    *,
    accuraterip_verified: Mapping[int, bool | None] | None = None,
    samples_probe: SamplesProbe | None = None,
    decoder: PcmDecoder | None = None,
    rewriter: FlacRewriter | None = None,
) -> CtdbVerifyResult:
    """``result`` with ``repair`` filled in: repaired, refused or failed. Never raises.

    ``flac_paths`` must be the files the verify read, in disc order.
    ``accuraterip_verified`` is, per track number, whether AccurateRip verified
    the track (True), compared and did not (False), or did not say (None).
    ``samples_probe``, ``decoder`` and ``rewriter`` default to plain
    ``subprocess`` runs; a caller that offers a ``cancel()`` passes killable ones.
    """
    probe = samples_probe or decode.total_samples
    try:
        frames = [probe(Path(p)) for p in flac_paths]
    except (
        decode.DecoderUnavailable,
        OSError,
        RuntimeError,
        subprocess.TimeoutExpired,
    ) as exc:
        record = refused(f"could not read the files' lengths ({exc})")
        return dataclasses.replace(result, repair=record)
    befores = _track_crcs_before(result)
    record = repair_rip(
        [Path(p) for p in flac_paths],
        result.localisation,
        result.entries,
        result.disc_crcs,
        track_frames=frames,
        accuraterip_verified=accuraterip_verified,
        track_crcs_before=befores if len(befores) == len(flac_paths) else (),
        decoder=decoder,
        rewriter=rewriter,
    )
    return dataclasses.replace(result, repair=record)
