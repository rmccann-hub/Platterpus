# SPDX-License-Identifier: GPL-3.0-only
"""Repair a rip toward the strongest CTDB entry, proving it before replacing anything.

On the owner's word of 2026-11-04 (*"Start building CTDB repair now? yes"*),
which revisits KDD-14's "wrap ctdb-cli" (``PLANNING.md``): the localisation
(``ctdb/localise.py``) already does CUETools' ``VerifyParity`` clean-room, so
the repair is the step after it, CUETools' ``CDRepairFix.Write``
(``CUETools.AccurateRip/CDRepair.cs:331-363``, GPL-2.0-or-later): XOR each
located word. The safety design mirrors ``neheb/cdverify``'s ``src/repair.rs``
(GPL-3.0-or-later), a port of the same CUETools code, so a reference rather
than an independent witness.

**The contract, in order.** Each step either passes or ends the repair with a
:class:`RepairRecord` saying why, and nothing on disk changes until step 6:

1. **Plan** (``repair_plan.py``): the strongest entry only, never a minority
   one; nothing when AccurateRip verified an affected track; refused in a guard
   band, outside the audio, with a pregap, with more corrections in a column
   than the entry's parity carries.
2. **Unchanged**: each affected file decodes to the audio the localisation
   measured (length and CRC-32), or the repair is refused.
3. **Apply**: XOR the words (``repair_apply.py``).
4. **Encode** a NEW file beside the original (a hidden temporary name), and
   give it every metadata block of the original (``adapters/flac_rewrite.py``).
5. **Prove, from the new file**: decode it again and require its PCM to equal
   the original's XOR the plan, byte for byte; then measure the whole disc as
   it will be (every other track decoded from its own file, and required
   unchanged too) and require the entry's whole-disc CRC and each repaired
   track's CRC at the entry's offset. AccurateRip v1 and v2 of the track are
   computed before and after (``accuraterip_crc.py``), the one witness that
   is not CTDB.
6. **Commit**: the original is kept as ``<name>.flac.before-ctdb-repair`` (a
   hard link, or a verified copy where links are not supported), then the new
   file is renamed over the original's name, atomically. A second repair over a
   kept original is refused rather than overwrite it.

**Not edited, ever:** the ripper's log (KDD-24: a log is the record of the read,
and a repair is not a read). Nor are the EAC-layout log's rows of the read: the
window renders that log once more when a repair lands (G3, 2026-11-11), and its
Copy CRC and AccurateRip rows still describe the read, while each repaired
track's ``Record:`` row says what replaced it (``track_record.py``). The record
names what it left untouched, and the rip report carries it (``ctdb.repair``).

Blocking (it decodes the whole disc once more and runs ``flac``): never on the
GUI thread (Critical rule 9). There is no worker and no ``cancel()`` yet,
because nothing calls this from the GUI; that wiring is TASKS R43's.
"""

from __future__ import annotations

import logging
import subprocess
import zlib
from collections.abc import Callable, Iterator, Mapping, Sequence
from pathlib import Path

from platterpus.adapters.ctdb_client import CtdbEntry
from platterpus.adapters.flac_rewrite import CD_SHAPE, FlacRewriter
from platterpus.ctdb import decode
from platterpus.ctdb.differences import CtdbLocalisation
from platterpus.ctdb.repair_apply import apply_fixes, prove, unchanged_reason
from platterpus.ctdb.repair_commit import CommitRefused, candidate_path, commit
from platterpus.ctdb.repair_plan import plan_repair
from platterpus.ctdb.repair_types import (
    RepairedTrack,
    RepairPlan,
    RepairRecord,
    RepairStatus,
    failed,
    refused,
)
from platterpus.deps.registry import probe_dependency

log = logging.getLogger(__name__)

#: What a repair never changes, said in every record.
UNTOUCHED: tuple[str, ...] = (
    "the ripper's log (KDD-24: the record of the read), and the EAC-layout log's "
    "rows of the read: each repaired track's Record row names this repair beside "
    "them",
    "derived copies (MP3, WavPack, WAV) made from the original FLAC",
    "samples in CTDB's guard bands (about the disc's first and last 5,880 "
    "frames at the entry's offset), which no parity covers: damage there is "
    "neither found nor repaired",
)

PcmDecoder = Callable[[Path], bytes]

_DECODE_ERRORS = (
    decode.DecoderUnavailable,
    OSError,
    RuntimeError,
    subprocess.TimeoutExpired,
)


class _Refused(Exception):
    """Internal: a guard said no; carries the sentence and whether it was a failure."""

    def __init__(self, reason: str, *, failure: bool = False) -> None:
        super().__init__(reason)
        self.reason: str = reason
        self.failure: bool = failure


def _decode(decoder: PcmDecoder, path: Path) -> bytes:
    try:
        return decoder(path)
    except _DECODE_ERRORS as exc:
        raise _Refused(f"could not decode {path.name}: {exc}", failure=True) from exc


def _rebuilt(
    plan: RepairPlan,
    paths: Sequence[Path],
    decoder: PcmDecoder,
    repaired: Mapping[int, bytes],
) -> Iterator[bytes]:
    """The disc as it will be: repaired tracks from memory, the rest re-read and checked."""
    for number, path in enumerate(paths, start=1):
        if number in repaired:
            yield repaired[number]
            continue
        pcm = _decode(decoder, path)
        problem = unchanged_reason(pcm, number, plan)
        if problem:
            raise _Refused(problem)
        yield pcm


def _witness(pcm: bytes, track: int, total: int) -> tuple[int | None, int | None]:
    from platterpus.accuraterip_crc import accuraterip_crcs  # numpy, probed first

    crcs = accuraterip_crcs(pcm, track, total)
    return (None, None) if crcs is None else (crcs.v1, crcs.v2)


def repair_rip(
    flac_paths: Sequence[Path],
    localisation: CtdbLocalisation | None,
    entries: Sequence[CtdbEntry],
    disc_crcs: Mapping[int, int],
    *,
    track_frames: Sequence[int],
    pregap_frames: int = 0,
    accuraterip_verified: Mapping[int, bool | None] | None = None,
    track_crcs_before: Sequence[Mapping[int, int]] = (),
    decoder: PcmDecoder | None = None,
    rewriter: FlacRewriter | None = None,
) -> RepairRecord:
    """Repair the rip in ``flac_paths`` toward the strongest entry. Never raises.

    The first four arguments are what the CTDB verify had: its files (disc
    order), its localisation, the lookup's entries and the measured
    ``{offset: whole-disc CRC}``. ``track_frames`` are the files' frame counts.
    """
    planned = plan_repair(
        localisation,
        entries,
        disc_crcs,
        track_frames,
        pregap_frames=pregap_frames,
        accuraterip_verified=accuraterip_verified,
    )
    if not isinstance(planned, RepairPlan):
        log.warning("CTDB repair refused: %s", planned.reason)
        return refused(planned.reason)
    plan = planned
    if len(flac_paths) != len(plan.track_frames):
        return refused("the files are not the ones the plan was made for", plan)
    probe = probe_dependency("numpy")
    if probe is None or not probe.present:
        return refused(
            "numpy is not installed (the AccurateRip witness needs it)", plan
        )
    writer = rewriter or FlacRewriter()
    missing = writer.missing()
    if missing:
        return failed(missing, plan)
    candidates: list[Path] = []
    try:
        record = _repair(
            plan,
            list(flac_paths),
            decoder or decode.decode_flac_to_pcm,
            writer,
            disc_crcs,
            track_crcs_before,
            candidates,
        )
    except (_Refused, OSError) as exc:
        # An OSError here is the disk itself (a leftover temporary that cannot be
        # removed, a folder gone read-only): a failure, never an exception out.
        refusal = exc if isinstance(exc, _Refused) else _Refused(str(exc), failure=True)
        for path in candidates:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                log.warning("CTDB repair: could not remove %s", path)
        log.warning(
            "CTDB repair %s: %s",
            "failed" if refusal.failure else "refused",
            refusal.reason,
        )
        return (failed if refusal.failure else refused)(refusal.reason, plan)
    log.info("CTDB repair committed: entry %s, tracks %s", plan.entry_id, plan.tracks)
    return record


def _repair(
    plan: RepairPlan,
    paths: list[Path],
    decoder: PcmDecoder,
    writer: FlacRewriter,
    disc_crcs: Mapping[int, int],
    track_crcs_before: Sequence[Mapping[int, int]],
    candidates: list[Path],
) -> RepairRecord:
    total = len(paths)
    repaired: dict[int, bytes] = {}
    witness_before: dict[int, tuple[int | None, int | None]] = {}
    for track in plan.tracks:
        path = paths[track - 1]
        shape = writer.stream_shape(path)
        if shape != CD_SHAPE:
            raise _Refused(f"{path.name} is not 44.1 kHz 16-bit stereo ({shape})")
        original = _decode(decoder, path)
        problem = unchanged_reason(original, track, plan)
        if problem:
            raise _Refused(problem)
        fixed = apply_fixes(original, plan.fixes_for(track))
        if isinstance(fixed, str):
            raise _Refused(fixed)
        new = candidate_path(path)
        new.unlink(missing_ok=True)  # our own leftover from an interrupted repair
        candidates.append(new)
        for problem in (writer.encode(fixed, new), writer.copy_metadata(path, new)):
            if problem:
                raise _Refused(problem, failure=True)
        # The proof below measures the NEW FILE's decoded bytes, not the bytes we
        # meant to write: the artifact is what gets replaced, so it is what is
        # proved. They must also equal the original XOR the plan exactly.
        written = _decode(decoder, new)
        if written != fixed:
            raise _Refused(
                f"the new {path.name} does not decode to the corrected audio; "
                "nothing is replaced",
                failure=True,
            )
        repaired[track] = written
        witness_before[track] = _witness(original, track, total)
    proof = prove(plan, _rebuilt(plan, paths, decoder, repaired))
    if isinstance(proof, str):
        raise _Refused(proof)
    try:
        kept = commit(
            [(paths[t - 1], candidate_path(paths[t - 1])) for t in plan.tracks]
        )
    except CommitRefused as exc:
        raise _Refused(exc.reason, failure=exc.failure) from exc
    rows: list[RepairedTrack] = []
    for track in plan.tracks:
        v1_before, v2_before = witness_before[track]
        v1_after, v2_after = _witness(repaired[track], track, total)
        path = paths[track - 1]
        before_track = (
            track_crcs_before[track - 1].get(plan.offset)
            if len(track_crcs_before) == total
            else None
        )
        rows.append(
            RepairedTrack(
                track=track,
                path=str(path),
                original_kept_as=str(kept[path]),
                samples_corrected=len(plan.fixes_for(track)),
                pcm_crc32_before=plan.track_crc32s[track - 1],
                pcm_crc32_after=zlib.crc32(repaired[track]) & 0xFFFFFFFF,
                ctdb_crc_expected=plan.expected_track_crcs[track - 1],
                ctdb_crc_after=proof.track_crcs[track],
                ctdb_crc_before=before_track,
                accuraterip_v1_before=v1_before,
                accuraterip_v2_before=v2_before,
                accuraterip_v1_after=v1_after,
                accuraterip_v2_after=v2_after,
            )
        )
    return RepairRecord(
        RepairStatus.REPAIRED,
        entry_id=plan.entry_id,
        confidence=plan.confidence,
        offset=plan.offset,
        disc_crc_expected=plan.expected_disc_crc,
        disc_crc_before=disc_crcs.get(plan.offset),
        disc_crc_after=proof.disc_crc,
        words=plan.fixes,
        tracks=tuple(rows),
        encoder_argv=writer.encoder_argv,
        untouched=UNTOUCHED,
    )
