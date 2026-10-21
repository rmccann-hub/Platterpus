# SPDX-License-Identifier: GPL-3.0-only
"""Verify a finished rip against the CUETools Database (CTDB).

Ties together the lookup adapter, the FLAC decode, and the (offset-0, best-
effort) CTDB CRC into a single verdict. Clean-room per KDD-16.

The flow:
  0. Refuse to look up a rip that does not cover the whole disc (a partial
     ``-l`` rip): its files make a TOC of a disc that does not exist, so any
     answer CTDB gives is about something else (``Verdict.NOT_WHOLE_DISC``;
     the disc's track count comes from :mod:`platterpus.ctdb.coverage`).
  1. Build the disc TOC from the ripped FLACs (track lengths via metaflac).
  2. Look the TOC up in CTDB.
  3. If found, decode the tracks to PCM and compute our CRC, then compare to
     the database entries.

Every step degrades to a clear verdict rather than raising, so a missing
decoder or a network blip never crashes the caller.

The CRC/offset/wire-format pieces are hardware-validated (KDD-16): a
`--ctdb-calibrate` run reproduced a stored CTDB CRC at aligned offset 0, so
`crc.CRC_VALIDATED` is True and a `MATCH` is trustworthy (shown "verified",
not "experimental"). Each result still carries `crc_validated` and reads the
gate live at verdict time, so the honesty wording tracks the flag if it's
ever toggled back (e.g. a future algorithm change re-opening the gate).
"""

from __future__ import annotations

import enum
import logging
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from platterpus.adapters.ctdb_client import (
    CTDBClient,
    CtdbLookupError,
    CtdbLookupResult,
)
from platterpus.build_info import self_invocation
from platterpus.ctdb import crc as crc_mod
from platterpus.ctdb import decode
from platterpus.ctdb.coverage import NOT_WHOLE_DISC_VERDICT
from platterpus.ctdb.matching import (
    CtdbTrackResult,
    match_disc,
    match_tracks,
)
from platterpus.ctdb.sweep import DISC_OFFSET_RANGE, SweepResult, sweep_disc
from platterpus.ctdb.toc import SamplesProbe, disc_toc_from_files
from platterpus.ctdb.track_wording import per_track_sentence

log = logging.getLogger(__name__)


class Verdict(enum.Enum):
    """The possible outcomes of a CTDB verify."""

    MATCH = "match"  # our CRC matched a DB entry
    NO_MATCH = "no_match"  # disc in DB, but our CRC didn't match
    NOT_IN_DATABASE = "not_in_db"  # TOC not found in CTDB
    DECODER_UNAVAILABLE = "no_decoder"  # can't compute local CRC (no flac)
    LOOKUP_ERROR = "lookup_error"  # network/parse failure
    # NOT LOOKED UP, on purpose: the files cover fewer tracks than the disc has.
    # CTDB keys a whole disc by its whole TOC, and the only TOC we can build is
    # from the files we ripped — so a 2-of-14 rip would send CTDB a two-track
    # disc that does not exist, get a 404, and report "this disc is not in
    # CTDB" about a disc CTDB holds 102 entries for (the 2026-09-28 Full run:
    # five partial-rip reports said exactly that). Neither a pass nor a failure:
    # the check did not run, and says why. Its value is spelled once, in
    # `coverage`, because the adapter-free report builder compares against it.
    NOT_WHOLE_DISC = NOT_WHOLE_DISC_VERDICT


@dataclass(frozen=True)
class CtdbVerifyResult:
    """A verify outcome plus the supporting detail for display/logging."""

    verdict: Verdict
    confidence: int = 0
    our_crc: int | None = None
    matched_crc: int | None = None
    message: str = ""
    crc_validated: bool = crc_mod.CRC_VALIDATED
    # The database's CRC(s) for this disc's TOC — what we tried (and, while the
    # CRC algorithm is unvalidated, failed) to match. Kept so the rip report and
    # `--ctdb-calibrate` carry everything needed to pin the algorithm offline
    # (our_crc vs these) without a second live lookup. Empty when not in the DB.
    db_crcs: tuple[int, ...] = ()
    # **The weight of the entries, beside the one we matched** (2026-10-19,
    # the claude-code-skills audit check, P1). CTDB's confidence is the number of
    # submissions behind an entry. A match only says our CRC equals SOME entry;
    # on the reference disc it equalled a confidence-1 entry, very likely the
    # owner's own EAC rip of 2026-06-11 with the same track-5 misread, while an
    # entry of 1,405 disagreed, and the app showed a green "verified". These two
    # numbers are what a reader needs to see that: the strongest entry's
    # confidence, and every entry's confidence summed.
    best_confidence: int = 0
    total_confidence: int = 0
    # **Per track** (TASKS R43, 2026-10-21): what CTDB's per-track CRCs say about
    # each track, in disc order (`ctdb/matching.py`). Empty when the check never
    # got as far as computing our CRCs (not in the database, no decoder, ...).
    tracks: tuple[CtdbTrackResult, ...] = ()
    # **The offset sweep** (TASKS R43): how far, in samples either side, our
    # whole-disc CRC was compared (0: the aligned CRC only), and where the
    # strongest matched entry's pressing sits from ours (0 aligned, None without
    # a match). A MATCH sums every entry matched at any offset, as CUETools'
    # `Confidence` does.
    offset_range: int = 0
    matched_offset: int | None = None

    @property
    def outvoted(self) -> bool:
        """A MATCH whose entry is not the strongest one CTDB holds for this TOC.

        Our rip equals a minority of submissions and differs from the plurality,
        which corroborates nothing: it is as consistent with a shared misread as
        with a correct read. False for anything that is not a MATCH.
        """
        return self.verdict is Verdict.MATCH and self.confidence < self.best_confidence

    @property
    def disagreeing_confidence(self) -> int:
        """Submissions behind every entry other than the one we matched."""
        if self.verdict is not Verdict.MATCH:
            return 0
        return max(0, self.total_confidence - self.confidence)

    @property
    def trustworthy(self) -> bool | None:
        """Can this verdict's claim about the disc be believed? Tri-state.

        A MATCH is only trustworthy once the CRC algorithm is confirmed, and only
        when its entry is the plurality (:attr:`outvoted` is False). ``None``
        is for a check that made NO claim — :attr:`Verdict.NOT_WHOLE_DISC` never
        asked CTDB anything, so there is nothing to trust or distrust, and a
        ``true`` beside it would read as "a CTDB check ran and can be relied on".
        """
        if self.verdict is Verdict.NOT_WHOLE_DISC:
            return None
        if self.verdict is not Verdict.MATCH:
            return True
        return self.crc_validated and not self.outvoted


# A decoder turns a FLAC path into PCM bytes (injected for tests).
PcmDecoder = Callable[[Path], bytes]


def not_whole_disc_result(
    covered: int, disc_tracks: int, data_tracks: Sequence[int] = ()
) -> CtdbVerifyResult:
    """The verdict for a file list that does not cover the disc. No lookup made.

    The message is the one sentence every surface shows (the Details tab reads
    it rather than composing its own, so the two cannot drift), in the report's
    ``not run — <why>`` shape. It names both numbers, because "not run" alone
    would leave a reader guessing whether the check was skipped, dropped, or
    broken.

    ``data_tracks`` are the numbers of the disc's DATA tracks the rip's log holds
    (TASKS R13). When they make up the whole shortfall, the rip left nothing out:
    the disc is an Enhanced CD, and the TOC built from the audio files cannot hold
    its data track. "this rip has 2 of the disc's 3 tracks" said the rip was
    partial when it was not, so that case gets its own sentence. The verdict stays
    NOT_WHOLE_DISC, because the TOC we can build still is not the disc's.
    """
    if data_tracks and covered + len(data_tracks) >= disc_tracks:
        if len(data_tracks) == 1:
            which = f"its data track (track {data_tracks[0]})"
        else:
            named = ", ".join(str(n) for n in data_tracks[:-1])
            which = f"its data tracks (tracks {named} and {data_tracks[-1]})"
        return CtdbVerifyResult(
            Verdict.NOT_WHOLE_DISC,
            message=(
                "not run — CTDB verifies whole discs, and the table of contents "
                f"built from this rip's audio files cannot include {which}"
            ),
        )
    return CtdbVerifyResult(
        Verdict.NOT_WHOLE_DISC,
        message=(
            f"not run — CTDB verifies whole discs, and this rip has {covered} of "
            f"the disc's {disc_tracks} tracks"
        ),
    )


def verify_rip(
    flac_paths: Sequence[Path],
    client: CTDBClient,
    *,
    disc_tracks: int | None = None,
    data_tracks: Sequence[int] = (),
    decoder: PcmDecoder | None = None,
    samples_probe: SamplesProbe | None = None,
) -> CtdbVerifyResult:
    """Verify the rip in `flac_paths` against CTDB. Never raises for expected
    failure modes — returns a verdict instead.

    ``disc_tracks`` is the disc's own track count (see
    :func:`platterpus.ctdb.coverage.disc_track_count`), or ``None`` when no
    witness said. When it is known and the files cover fewer
    tracks, nothing is probed, decoded or looked up: the result is
    :attr:`Verdict.NOT_WHOLE_DISC`. ``None`` keeps the old behaviour, because a
    count we do not have is not evidence that the rip is partial.
    ``data_tracks`` (the log's data-track numbers) only words that refusal: see
    :func:`not_whole_disc_result`.

    `decoder`/`samples_probe` are injected in tests; production defaults use
    the host `flac`/`metaflac`.
    """
    decoder = decoder or decode.decode_flac_to_pcm
    samples_probe = samples_probe or decode.total_samples

    # 0) Is the TOC we are about to build the DISC's TOC? It is built from the
    #    files (toc.disc_toc_from_files), so it is only when the files are every
    #    track. Checked BEFORE the TOC is built, not after the lookup comes back:
    #    a 404 on a synthetic TOC looks exactly like a 404 on a real one, and
    #    "not in CTDB" is the claim this guard exists to stop us making. More
    #    files than tracks is left to the old path: when the files and the count
    #    both come from the rip's own log they cannot outnumber its tracks, and
    #    the folder-scan fallback that can is already logged at WARNING by
    #    `rip_files` as the reduced-confidence case it is.
    if disc_tracks is not None and len(flac_paths) < disc_tracks:
        return not_whole_disc_result(len(flac_paths), disc_tracks, data_tracks)

    # 1) TOC → 2) lookup.
    try:
        toc = disc_toc_from_files(flac_paths, samples_probe)
    except decode.DecoderUnavailable as exc:
        return CtdbVerifyResult(Verdict.DECODER_UNAVAILABLE, message=str(exc))
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
        # BUG-4: a wedged flac/metaflac raises TimeoutExpired (the decoders use
        # real timeouts); it's NOT an OSError/RuntimeError, so without it a hang
        # bypassed classification and only the worker's broad except caught it.
        return CtdbVerifyResult(Verdict.LOOKUP_ERROR, message=f"TOC error: {exc}")

    try:
        result = client.lookup(toc)
    except CtdbLookupError as exc:
        return CtdbVerifyResult(Verdict.LOOKUP_ERROR, message=str(exc))

    if not result.in_database:
        return CtdbVerifyResult(
            Verdict.NOT_IN_DATABASE, message="this disc is not in CTDB"
        )

    # 3) decode + CRC compare. Stream each track's PCM through ONE pass that
    #    measures every CRC we compare (`ctdb/sweep.py`), one track resident at a
    #    time rather than the whole disc plus a b"".join copy — that spiked
    #    ~1.5 GB on the verify daemon thread (#39). The windows need the disc's
    #    frame count and track starts up front (the back trim is length-dependent),
    #    which the TOC gives us before decoding.
    try:
        measured = sweep_disc(
            (decoder(Path(p)) for p in flac_paths), toc, disc_range=DISC_OFFSET_RANGE
        )
    except decode.DecoderUnavailable as exc:
        return _db_only_result(result, Verdict.DECODER_UNAVAILABLE, str(exc))
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        # BUG-4: include TimeoutExpired here too — a wedged decoder during the
        # CRC pass must classify as a decode error, not escape uncaught.
        return _db_only_result(result, Verdict.LOOKUP_ERROR, f"decode error: {exc}")
    our_crc = measured.disc.get(0)
    if our_crc is None:
        # A disc too short to hold the guard band — no meaningful CTDB CRC.
        return _db_only_result(
            result, Verdict.LOOKUP_ERROR, "disc too short for the CTDB CRC guard band"
        )
    return _match_verdict(result, our_crc, measured)


def _match_verdict(
    result: CtdbLookupResult, our_crc: int, measured: SweepResult | None = None
) -> CtdbVerifyResult:
    db_crcs = tuple(e.crc for e in result.entries if e.crc is not None)
    best = max((e.confidence for e in result.entries), default=0)
    total = sum(max(0, e.confidence) for e in result.entries)
    # Without a measurement (a caller holding only the aligned CRC) there is no
    # sweep and no per-track result, and the messages claim neither.
    disc_crcs = dict(measured.disc) if measured is not None else {0: our_crc}
    swept = max((abs(o) for o in disc_crcs), default=0)
    disc_matched = match_disc(result.entries, disc_crcs)
    tracks = (
        match_tracks(result.entries, measured.tracks, disc_matched)
        if measured is not None
        else ()
    )
    per_track = f" {per_track_sentence(tracks, total)}" if tracks else ""
    if disc_matched:
        matched = [(result.entries[i], o) for i, o in disc_matched.items()]
        confidence = sum(max(0, e.confidence) for e, _ in matched)
        lead, offset = min(matched, key=lambda m: (-m[0].confidence, abs(m[1]), m[1]))
        if not crc_mod.CRC_VALIDATED:
            message = (
                "CRC matched, but the CRC algorithm is UNVERIFIED "
                "(KDD-16) — treat as experimental"
            )
        elif confidence < best:
            message = minority_match_sentence(confidence, total)
            message += f".{per_track}" if per_track else ""
        else:
            message = f"verified against CTDB (confidence {confidence})"
            if offset:
                message += f", {shifted_pressing_phrase(offset)}"
        return CtdbVerifyResult(
            Verdict.MATCH,
            confidence=confidence,
            our_crc=our_crc,
            matched_crc=lead.crc,
            db_crcs=db_crcs,
            crc_validated=crc_mod.CRC_VALIDATED,
            message=message,
            best_confidence=best,
            total_confidence=total,
            tracks=tracks,
            offset_range=swept,
            matched_offset=offset,
        )
    n = len(result.entries)
    # The message MUST depend on whether our CRC algorithm is trustworthy. While
    # CRC_VALIDATED is False (KDD-16), our_crc is a known-placeholder value that
    # is EXPECTED to disagree with the database, so a no-match says nothing about
    # the rip — claiming "the rip differs" here is the false alarm the real-disc
    # Police report exposed. Only once the algorithm is hardware-validated does a
    # no-match actually mean the audio differs from the database.
    if crc_mod.CRC_VALIDATED and swept:
        # Every alignment CTDB itself would accept was tried, so this is now a
        # finding about the audio, scoped to what CTDB holds: no entry equals it.
        message = (
            f"disc is in CTDB, but our CRC matched none of its {n} entries at any "
            f"alignment within ±{swept:,} samples, so our audio differs from every "
            "entry CTDB holds for this disc. AccurateRip remains the primary "
            f"proof.{per_track}"
        )
    elif crc_mod.CRC_VALIDATED:
        message = (
            f"disc is in CTDB but our CRC didn't match any of the {n} "
            "entries at the standard alignment. CTDB also holds offset-shifted "
            "pressings, which this check does not sweep, so a non-match here is "
            "not evidence the rip is wrong — AccurateRip is the per-track "
            f"authority.{per_track}"
        )
    else:
        message = (
            f"disc is in CTDB (confidence {best}), but the CTDB CRC algorithm is "
            "not yet hardware-validated (KDD-16), so this non-match is not "
            "meaningful — AccurateRip is the authority here. Run "
            f"`{self_invocation()} --ctdb-calibrate <folder>` to pin the algorithm."
        )
    # The weight of the entries is a fact about the database whatever our CRC
    # did, so a no-match carries it too. Until 2026-10-20 only a MATCH did, and
    # the 2026-10-20 Full run's report read `confidence: 1416` beside
    # `best_confidence: 0` and `total_confidence: 0`, as if the strongest entry
    # had no submissions behind it.
    return CtdbVerifyResult(
        Verdict.NO_MATCH,
        confidence=best,
        our_crc=our_crc,
        db_crcs=db_crcs,
        crc_validated=crc_mod.CRC_VALIDATED,
        message=message,
        best_confidence=best,
        total_confidence=total,
        tracks=tracks,
        offset_range=swept,
    )


def shifted_pressing_phrase(offset: int) -> str:
    """The one wording for a match found away from alignment (verdict and screen)."""
    return f"a pressing {offset:+,d} samples from ours"


def minority_match_sentence(matched: int, total: int) -> str:
    """The one wording for a match outvoted by a stronger CTDB entry.

    Shared by the verify message and the results pane, so the report and the
    screen cannot describe the same match two ways.
    """
    disagree = max(0, total - matched)
    return (
        f"matched {matched:,} of {total:,} CTDB submissions; {disagree:,} disagree. "
        "Our rip equals a minority entry, which a shared misread could explain, "
        "so this does not corroborate the rip; AccurateRip is the authority"
    )


def _db_only_result(
    result: CtdbLookupResult, verdict: Verdict, message: str
) -> CtdbVerifyResult:
    """Verdict for 'found in DB but couldn't compute our CRC'."""
    best = max((e.confidence for e in result.entries), default=0)
    return CtdbVerifyResult(
        verdict,
        confidence=best,
        db_crcs=tuple(e.crc for e in result.entries if e.crc is not None),
        crc_validated=crc_mod.CRC_VALIDATED,
        message=message,
        best_confidence=best,
        total_confidence=sum(max(0, e.confidence) for e in result.entries),
    )
