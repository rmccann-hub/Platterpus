# SPDX-License-Identifier: GPL-3.0-only
"""The thin caller: repair a rip from the CTDB verify's own result (TASKS R43).

``ctdb/repair.py`` is the core and takes every input explicitly; this is the one
place that reads them off a :class:`~platterpus.ctdb.verify.CtdbVerifyResult`
and the files, so a future GUI action or script verb calls one function and
cannot assemble the inputs a second way. It adds what the verify does not keep:
each file's frame count, read by ``metaflac`` (``decode.total_samples``), so the
plan can refuse a file that is not whole CD sectors.

Returns the verify result with ``repair`` set, which is how the rip report gets
``ctdb.repair`` (schema 44). Every other field stays what the verify MEASURED,
before the repair: a repaired rip reads "repaired" beside the verdict that led
to it, and only a fresh verify measures the repaired files. Blocking, like the
core: off the GUI thread.
"""

from __future__ import annotations

import dataclasses
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

from platterpus.adapters.flac_rewrite import FlacRewriter
from platterpus.ctdb import decode
from platterpus.ctdb.repair import PcmDecoder, repair_rip
from platterpus.ctdb.repair_types import refused
from platterpus.ctdb.toc import SamplesProbe
from platterpus.ctdb.verify import CtdbVerifyResult


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
    record = repair_rip(
        [Path(p) for p in flac_paths],
        result.localisation,
        result.entries,
        result.disc_crcs,
        track_frames=frames,
        accuraterip_verified=accuraterip_verified,
        decoder=decoder,
        rewriter=rewriter,
    )
    return dataclasses.replace(result, repair=record)
