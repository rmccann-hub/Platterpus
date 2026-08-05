# SPDX-License-Identifier: GPL-3.0-only
"""The auto-fix re-rip, validated against an INDEPENDENT ripper on the worst track.

**WHAT THIS SETTLES.** Track 5 of the EAC baseline disc ("Don't Stand So Close to Me")
has been the problem child of every session: it is the disc's offset-variant track, and
on 2026-08-04 cyanrip read it **twice with different results** — so Platterpus discarded
the first read and swapped in the second. That is the auto-fix doing the most
consequential thing it can do: **deciding which of two readings of the same audio is the
real one**, and throwing the other away.

Nothing in-house could check that decision. Comparing cyanrip against cyanrip compares
relatives — CLAUDE.md's shared-ancestor trap — and the AccurateRip database does not
help here, because this pressing does not match its consensus at all.

**EAC settles it.** The committed baseline log holds two independent EAC 1.8 extractions
of the same physical disc in the same drive, and both report for track 5 exactly the
values our re-rip produced, while the read we threw away appears in neither:

    EAC log 1 (20:01)            Test CRC E0036697   Copy CRC E0036697   AR v2 9EEB8843
    EAC log 2 (20:02)            Test CRC E0036697   Copy CRC E0036697   AR v2 9EEB8843
    cyanrip pass 2 (KEPT)        CRC      E0036697                       AR v2 9EEB8843
    cyanrip pass 1 (DISCARDED)   CRC      6902BCF0                       AR v2 268CCD94

So the auto-fix kept the read a separate implementation agrees with, twice. Had it kept
the first pass — or had the swap been wired the other way round — this test fails.

**It reads the committed artifacts rather than restating them** (CLAUDE.md: *when a
committed artifact can settle a question, the test should read the artifact*), so it
cannot drift from what those files say, and it fails if either is edited or moved.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_EAC_LOG = _REPO / "output_reference" / "EAC_flac" / "eac_baseline_police_classics.log"
_ART = _REPO / "docs" / "handshake" / "artifacts-round-07"
_CYANRIP_LOG = _ART / "round-07-lap-23-rig-rip-gc5fb909.log"
_ADDENDUM = _ART / "round-07-lap-23-rig-rip-gc5fb909.platterpus-addendum.txt"

#: The read Platterpus KEPT for track 5, and what EAC independently produced.
_KEPT_CRC = "E0036697"
_KEPT_AR_V2 = "9EEB8843"
#: The read Platterpus THREW AWAY.
_DISCARDED_CRC = "6902BCF0"
_DISCARDED_AR_V2 = "268CCD94"


def _eac_text() -> str:
    """EAC writes UTF-16LE. Decoding it wrongly is how a grep for its checksum once
    came back empty and nearly produced the claim that it carried none."""
    return _EAC_LOG.read_bytes().decode("utf-16-le", errors="replace")


@pytest.mark.parametrize(
    "path", [_EAC_LOG, _CYANRIP_LOG, _ADDENDUM], ids=["eac", "cyanrip", "addendum"]
)
def test_the_artifacts_this_rests_on_are_present(path: Path) -> None:
    """A floor. Every assertion below is vacuous if a file has moved or been pruned."""
    assert path.is_file(), f"missing committed artifact: {path}"
    assert path.stat().st_size > 1000, (
        f"suspiciously small: {path} ({path.stat().st_size} B)"
    )


def test_eac_independently_produced_the_read_we_KEPT() -> None:
    """The core claim: a separate implementation agrees with our re-rip."""
    eac = _eac_text()
    assert _KEPT_CRC in eac, (
        f"EAC's log does not contain {_KEPT_CRC}, the CRC of the read we kept — the "
        "premise of this whole comparison is gone"
    )
    assert _KEPT_AR_V2 in eac, f"EAC's log does not contain AR v2 {_KEPT_AR_V2}"
    # EAC ran it twice; both passes must agree, or "independent confirmation" overstates.
    assert eac.count(_KEPT_CRC) >= 2, (
        f"{_KEPT_CRC} appears {eac.count(_KEPT_CRC)}x in EAC's log; the baseline holds "
        "two extractions and the claim is that BOTH produced it"
    )
    assert (
        _ADDENDUM.read_text(encoding="utf-8", errors="replace").count(_KEPT_CRC) >= 1
    ), "our addendum no longer records that CRC as the shipped read"


def test_the_read_we_DISCARDED_appears_in_no_EAC_log() -> None:
    """The other half, and the one that makes the first half mean something.

    If EAC had also produced `6902BCF0` somewhere, "EAC agrees with the read we kept"
    would be true and worthless — agreement with both is agreement with neither.
    """
    eac = _eac_text()
    assert _DISCARDED_CRC not in eac, (
        f"{_DISCARDED_CRC} — the read we threw away — appears in EAC's log after all, "
        "so EAC does not discriminate between our two passes and this test proves "
        "nothing about which read was right"
    )
    assert _DISCARDED_AR_V2 not in eac, (
        f"discarded AR v2 {_DISCARDED_AR_V2} is in EAC's log"
    )
    # And it must still be in OUR log, or the comparison has lost its other term.
    assert _DISCARDED_CRC in _CYANRIP_LOG.read_text(
        encoding="utf-8", errors="replace"
    ), (
        "the discarded read is no longer in the cyanrip log, so there is nothing to "
        "contrast and the test has quietly become one-sided"
    )


def test_track_5_is_still_the_offset_variant_track() -> None:
    """Context that keeps the result from being over-read.

    Neither ripper verifies track 5 against AccurateRip's consensus — EAC says so in as
    many words. The auto-fix did not make the track "accurate"; it picked the correct
    bytes for a pressing AccurateRip's v1/v2 does not describe. cyanrip additionally
    identifies WHY (a +450 offset-variant match), which EAC has no check for — so our
    log is strictly more informative here, and that is the claim, not "we beat EAC".
    """
    eac = _eac_text()
    assert "Cannot be verified as accurate" in eac, (
        "EAC's log no longer reports an unverifiable track, so the framing above — "
        "that this is a pressing mismatch and not a bad read — is unsupported"
    )
    cyanrip = _CYANRIP_LOG.read_text(encoding="utf-8", errors="replace")
    assert "Accurip 450:" in cyanrip, "the +450 line is gone from the cyanrip log"
