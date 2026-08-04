# SPDX-License-Identifier: GPL-3.0-only
"""Full EAC parity, proven against two committed artifacts of the same physical disc.

**This is the file that closes the parity question, and it does it by reading
artifacts rather than by asserting.** Both sides are committed text:

* `output_reference/EAC_flac/eac_baseline_police_classics.log` — a genuine Exact
  Audio Copy 1.8 log (UTF-16, verbatim).
* `output_reference/cyanrip_fork_flac/` — a real rip of **the same disc, in the same
  drive** (Pioneer BDR-209D, offset +667) by Platterpus 0.6.4b3 +
  `cyanrip 0.9.4-rc1+platterpus.5-beta.1 (platterpus-fork-g9003e6f)`, 2026-08-04.

Two results, both measured here rather than remembered:

1. **14 of 14 tracks are bit-identical to EAC** (`Copy CRC` equal, track for track).
   That closes the `output_reference/README.md` parity goal.
2. **All ten of EAC's `Pre-gap length` rows match ours to the hundredth of a
   second, in order.** The KDD-32 / `INDEX 00` capability gap — cyanrip 0.9.3 could
   not see the pregaps EAC detects, which `eac_log_export._gap_handling` documented as
   our one measurable archival shortfall — is **closed for the fork**.

Track 5 is the interesting one and is asserted separately: its first read pass
produced a CRC that does **not** match EAC, and the auto-fix re-rip is what brought
it to bit-identical. So this file is also the proof that the secure-re-rip feature
does the thing it exists for.

**Why a test and not a note in the session log.** A remembered measurement has no
provenance you can re-check, and it silently drops its qualifier (CLAUDE.md: *"am I
answering from the artifact, or from my memory of the artifact?"*). These artifacts
can settle the question, so the test reads them.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_EAC = _REPO_ROOT / "output_reference" / "EAC_flac" / "eac_baseline_police_classics.log"
_FORK_DIR = _REPO_ROOT / "output_reference" / "cyanrip_fork_flac"
_FORK_EAC_STYLE = _FORK_DIR / "cyanrip_fork_police_classics_EACcompatible.log"
_FORK_LOG = _FORK_DIR / "cyanrip_fork_police_classics.log"

#: The disc has 14 tracks. Stated so a truncated artifact cannot pass by comparing
#: three tracks and finding them equal.
_TRACK_COUNT = 14
#: EAC reports a pre-gap for ten of them.
_PREGAP_COUNT = 10

_COPY_CRC = re.compile(r"Copy CRC\s+([0-9A-F]{8})")
_TRACK_HEADER = re.compile(r"^\s*Track\s+(\d+)\s*$")
_PREGAP = re.compile(r"Pre-gap length\s+(\S+)")


def _eac_text() -> str:
    """The genuine EAC log, decoded from its native UTF-16.

    Not converted to UTF-8 in the repo on purpose — the encoding is part of the
    authentic artifact, and a conversion silently broke the parity checker once.
    """
    return _EAC.read_bytes().decode("utf-16", "replace")


def _copy_crcs(text: str) -> dict[int, str]:
    """``{track number: Copy CRC}`` from an EAC-layout log. First value per track."""
    out: dict[int, str] = {}
    track: int | None = None
    for line in text.splitlines():
        header = _TRACK_HEADER.match(line)
        if header:
            track = int(header.group(1))
            continue
        crc = _COPY_CRC.search(line)
        if crc and track is not None:
            out.setdefault(track, crc.group(1))
    return out


def test_every_track_is_bit_identical_to_the_eac_baseline() -> None:
    """14 of 14 `Copy CRC`s equal. The parity goal, measured.

    A matching `Copy CRC` on the same physical disc means the two rips decoded to
    the same PCM — that is what "bit-perfect" means here, and it is why this project
    can commit the *text* and never the audio (CLAUDE.md rule #8).
    """
    ours = _copy_crcs(_FORK_EAC_STYLE.read_text(encoding="utf-8"))
    theirs = _copy_crcs(_eac_text())

    # FLOORS FIRST. Equality between two empty dicts is not parity, and this disc's
    # track count is known — so require it on both sides before comparing.
    assert len(ours) == _TRACK_COUNT, f"our log has {len(ours)} tracks, not 14"
    assert len(theirs) >= _TRACK_COUNT, f"the EAC baseline has {len(theirs)} tracks"

    differing = {t: (theirs.get(t), ours[t]) for t in ours if theirs.get(t) != ours[t]}
    assert not differing, (
        f"these tracks are NOT bit-identical to EAC (track: EAC, ours): {differing}"
    )


def test_track_5_reached_parity_only_via_the_auto_fix_rerip() -> None:
    """The secure re-rip is what closed the last track. Proof, not a claim.

    Track 5 matched no AccurateRip v1/v2 entry on the first pass — only the `+450`
    offset-variant — so the auto-fix re-ripped it and swapped the better read in. The
    whole-disc log records the FIRST pass's CRC; the addendum records the SHIPPED
    file's. EAC's value agrees with the addendum and *disagrees* with the first pass,
    which is exactly the feature working.
    """
    whole_disc = _FORK_LOG.read_text(encoding="utf-8")
    eac_crc = _copy_crcs(_eac_text())[5]
    shipped_crc = _copy_crcs(_FORK_EAC_STYLE.read_text(encoding="utf-8"))[5]

    # The addendum is the record of the swap; without it this test is comparing
    # nothing meaningful.
    assert "[Platterpus auto-fix addendum]" in whole_disc, (
        "the committed fork log carries no auto-fix addendum — this artifact is not "
        "the multi-pass rip this test is about"
    )
    addendum = whole_disc.split("[Platterpus auto-fix addendum]", 1)[1]
    assert f"CRC {shipped_crc}" in addendum, (
        "the shipped CRC is not the one the addendum records, so the EAC-style log "
        "and the addendum disagree about which read was kept"
    )
    assert shipped_crc == eac_crc, "the shipped track 5 does not match EAC"

    # And the FIRST pass differed — otherwise the re-rip changed nothing and this
    # test would be asserting a coincidence.
    first_pass = whole_disc.split("[Platterpus auto-fix addendum]", 1)[0]
    first_crcs = set(re.findall(r"EAC CRC32:\s+([0-9A-F]{8})", first_pass))
    assert eac_crc not in first_crcs, (
        "EAC's track-5 CRC already appears in the first pass, so the auto-fix was "
        "not what achieved parity and this test proves nothing about it"
    )


def test_the_pregap_rows_match_eac_to_the_hundredth() -> None:
    """All ten, in order. The KDD-32 archival shortfall, closed for the fork.

    `eac_log_export._gap_handling` documented cyanrip 0.9.3's inability to see these
    as *"our one measurable archival shortfall against EAC"*. The fork reads them from
    the sub-channel and finds precisely EAC's ten. Asserted against EAC's own file so
    this cannot pass by matching a number we chose.
    """
    theirs = _PREGAP.findall(_eac_text())[:_PREGAP_COUNT]
    ours = _PREGAP.findall(_FORK_EAC_STYLE.read_text(encoding="utf-8"))

    assert len(theirs) == _PREGAP_COUNT, (
        f"the EAC baseline yielded {len(theirs)} pre-gap rows, expected "
        f"{_PREGAP_COUNT} — the parse is wrong, so a match would be meaningless"
    )
    assert ours == theirs, f"pre-gap rows differ:\n  EAC : {theirs}\n  ours: {ours}"


def test_the_gap_handling_row_agrees_with_eac_on_this_disc() -> None:
    """The row this artifact caught being broken.

    The fork prints ``merging into track N``; our matcher looked for ``merged``, so
    the row read "(not reported by the ripper)" while EAC's said "Appended to previous
    track". Same disc, same drive, and now the same row — earned from the evidence
    rather than by matching a string.
    """
    from platterpus.eac_log_export import _gap_handling
    from platterpus.parsers.cyanrip_log import parse_cyanrip_log

    parsed = parse_cyanrip_log(_FORK_LOG.read_text(encoding="utf-8"))
    ours = _gap_handling(parsed.ripping_info, True)

    eac_rows = [ln for ln in _eac_text().splitlines() if ln.startswith("Gap handling")]
    assert eac_rows, "the EAC baseline carries no Gap handling row"
    expected = eac_rows[0].split(":", 1)[1].strip()

    assert ours == expected, (
        f"our Gap handling row is {ours!r}; EAC's, on the same disc, is {expected!r}"
    )


def test_the_committed_fork_artifacts_are_the_build_they_claim() -> None:
    """Provenance: a build tag names a commit, so check the artifact says which.

    CLAUDE.md rule 12 — *any claim about an artifact's provenance must be derivable
    from the artifact's content*. Two logs of one disc from two binaries are not
    interchangeable evidence, and this whole file is about comparing one specific
    binary's output with EAC's.
    """
    whole_disc = _FORK_LOG.read_text(encoding="utf-8")
    assert "platterpus-fork-g9003e6f" in whole_disc, (
        "the committed fork log does not name the build it came from"
    )
    assert "cyanrip 0.9.4-rc1+platterpus.5-beta.1" in whole_disc

    eac_style = _FORK_EAC_STYLE.read_text(encoding="utf-8")
    assert "Platterpus 0.6.4b3" in eac_style, (
        "the EAC-style log does not name the Platterpus build that rendered it"
    )
    # Same drive as the baseline, or the CRC comparison is between two different
    # read offsets and proves nothing about either.
    assert "BDR-209D" in whole_disc and "BDR-209D" in _eac_text()
