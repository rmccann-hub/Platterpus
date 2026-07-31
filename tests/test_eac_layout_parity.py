"""The EAC-layout export is checked against a *real EAC log of the same disc*.

`output_reference/EAC_flac/eac_baseline_police_classics.log` is a genuine Exact
Audio Copy V1.8 log of the reference disc, produced on the same drive. That makes
it the only honest yardstick for "does our log look like EAC's": not a
hand-written idea of the format, but the actual bytes EAC writes.

Two properties are pinned here, and they are different claims:

1. **Layout** — the sections we can fill are byte-identical to EAC's, including
   column alignment. The TOC table is the strongest case: it is *derived* from
   the per-track sectors cyanrip reports, and reproduces EAC's table exactly.
2. **Machine-comparability** — the maintainer's requirement that accuracy versus
   EAC be determinable *from the logs alone*. `platterpus.parity.compare_logs`
   reads both documents and pairs their per-track CRCs with no other input, so
   anyone holding the two files can settle the question themselves.

Rows cyanrip genuinely cannot report are asserted to be *labelled*, never
guessed and never quietly dropped — the honesty rule that makes the rest of the
document worth reading.
"""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path

import pytest

from platterpus.eac_log_export import render_eac_style_log
from platterpus.parity import compare_logs
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.parsers.rip_log import RipLog, TrackResult

_REPO = Path(__file__).resolve().parent.parent
_EAC_BASELINE = (
    _REPO / "output_reference" / "EAC_flac" / "eac_baseline_police_classics.log"
)
_CYANRIP_RIP = (
    _REPO / "output_reference" / "cyanrip_flac" / "cyanrip_flac_police_classics.log"
)


def _eac_text() -> str:
    # Real EAC writes UTF-16 (with a BOM); reading it as UTF-8 raises.
    return _EAC_BASELINE.read_text(encoding="utf-16")


def _our_log() -> RipLog:
    """The committed cyanrip rip of the same disc, with the facts a rip supplies.

    ``defeat_audio_cache`` is injected the way the app injects it at runtime (it
    is measured by the cd-paranoia probe, not printed by cyanrip — KDD-29), so
    the rendering under test is the one users actually get.
    """
    log = parse_cyanrip_log(_CYANRIP_RIP.read_text(encoding="utf-8", errors="replace"))
    return replace(log, ripping_info=replace(log.ripping_info, defeat_audio_cache=True))


def _rendered() -> str:
    return render_eac_style_log(
        _our_log(),
        platterpus_version="0.0.0-test",
        encoder_versions={"flac": "1.5.0"},
    )


def _section(text: str, header: str, length: int) -> list[str]:
    lines = text.splitlines()
    start = lines.index(header)
    return lines[start : start + length]


pytestmark = pytest.mark.skipif(
    not _EAC_BASELINE.exists() or not _CYANRIP_RIP.exists(),
    reason="reference logs not present in this checkout",
)


# --- layout ------------------------------------------------------------------


def test_toc_table_is_byte_identical_to_the_real_eac_log() -> None:
    """EAC's TOC, reproduced exactly — values *and* column alignment.

    This is the one block where "looks the same" can be proven rather than
    asserted, because both documents describe the same physical disc.
    """
    theirs = _section(_eac_text(), "TOC of the extracted CD", 20)
    ours = _section(_rendered(), "TOC of the extracted CD", 20)
    assert ours == theirs


def test_the_archival_header_rows_appear_with_eac_s_exact_labels() -> None:
    """Same rows, same spelling, same column at which the value starts.

    A reader diffing the two files should find these lines aligned, not merely
    present — that is what makes a side-by-side comparison readable.
    """
    text = _rendered()
    for row in (
        "Read mode               : ",
        "Utilize accurate stream : ",
        "Defeat audio cache      : ",
        "Make use of C2 pointers : ",
        "Read offset correction                      : ",
        "Overread into Lead-In and Lead-Out          : ",
        "Fill up missing offset samples with silence : ",
        "Delete leading and trailing silent blocks   : ",
        "Null samples used in CRC calculations       : ",
        "Used interface                              : ",
        "Gap handling                                : ",
    ):
        assert any(line.startswith(row) for line in text.splitlines()), (
            f"EAC prints a {row.split(':')[0].strip()!r} row; ours is missing or "
            "differently aligned"
        )


def test_measured_rows_carry_the_measured_value() -> None:
    """The rows we *can* fill must be filled, not labelled away."""
    text = _rendered()
    assert "Read offset correction                      : 667" in text
    assert "Defeat audio cache      : Yes" in text
    # The BDR-209D reports C2 as unsupported, so EAC's row is a truthful "No".
    assert "Make use of C2 pointers : No" in text
    # cyanrip drives libcdio-paranoia — EAC's "Secure", by EAC's own definition.
    assert "Read mode               : Secure" in text


def test_unreportable_rows_are_labelled_never_guessed() -> None:
    """The honesty rule: an EAC value we can't stand behind is named as absent.

    A fabricated "Yes" here would poison every other row — a reader has no way to
    tell which values were real. One constant wording makes the gaps greppable.
    """
    text = _rendered()
    assert "Utilize accurate stream : (not reported by the ripper)" in text
    assert text.count("(not reported by the ripper)") >= 1


def test_the_status_report_uses_eac_s_own_wording() -> None:
    theirs = _eac_text()
    ours = _rendered()
    for phrase in (
        "track(s) accurately ripped",
        "No errors occurred",
        "End of status report",
    ):
        assert phrase in theirs, "sanity: phrase should exist in the real EAC log"
        assert phrase in ours


def test_the_document_never_impersonates_eac() -> None:
    """Layout parity stops exactly at provenance — that line is not moved."""
    text = _rendered()
    assert not text.startswith("Exact Audio Copy V")
    assert "NOT a genuine EAC log" in text
    # EAC's own checksum marker must never appear; ours is separately labelled.
    assert "==== Log checksum " not in text
    assert "NOT an EAC checksum" in text


# --- machine-comparability (the maintainer's "from the logs alone") ----------


def test_accuracy_versus_eac_is_computable_from_the_two_logs_alone() -> None:
    """Hand someone both files and they can settle the accuracy question.

    No JSON report, no database lookup, no access to the audio — just the two
    text documents. That is the property that makes the log worth keeping.
    """
    report = compare_logs(_eac_text(), _rendered())
    assert len(report.tracks) == 14, "every track must pair up across the two logs"
    assert not report.extra, "no track should appear in one log and not the other"
    assert all(t.baseline_crc and t.candidate_crc for t in report.tracks)


def test_the_shipped_rip_matches_eac_on_every_track_but_the_unstable_one() -> None:
    """The measured parity result, pinned — and it is better than it used to be.

    The committed cyanrip log records the *first* read pass, where tracks 3 and 5
    both differed from EAC (12/14). The per-track auto-fix re-reads such tracks
    and swaps the converged copy in, and v0.5.11 made the log report that shipped
    read — at which point track 5 turns out to match EAC **exactly**. So the fix
    that started as an honesty correction also raised measured parity to 13/14;
    only track 3, which has never read the same way twice on this drive, differs.
    """
    log = _our_log()
    shipped = {3: "3D8FCF0C", 5: "E0036697"}  # cyanrip's swap addendum, real run
    log = replace(
        log,
        tracks=tuple(
            replace(t, copy_crc=shipped.get(t.number, t.copy_crc)) for t in log.tracks
        ),
    )
    rendered = render_eac_style_log(log, encoder_versions={"flac": "1.5.0"})
    report = compare_logs(_eac_text(), rendered)
    differing = [t.number for t in report.tracks if t.baseline_crc != t.candidate_crc]
    assert differing == [3], (
        "expected only the known-unstable track 3 to differ from the EAC rip; "
        f"got {differing}"
    )


# --- regressions from the 2026-07-28 adversarial review ----------------------


def test_track_header_is_right_aligned_like_eac() -> None:
    """EAC writes "Track  1" but "Track 14" — one space plus width-2."""
    text = _rendered()
    assert "\nTrack  1\n" in text
    assert "\nTrack 14\n" in text
    assert "Track  14" not in text


def test_the_compressor_row_does_not_credit_a_binary_that_did_not_run() -> None:
    """The audio is encoded in-process by libavcodec, not by the flac binary.

    Naming `flac <version>` there described a tool merely installed on the host,
    and contradicted the very next row.
    """
    text = _rendered()
    assert "Command line compressor         : (none" in text
    assert "Command line compressor         : flac" not in text


def test_c2_capability_is_not_reported_as_c2_use() -> None:
    """cyanrip's "C2 errors: %s by drive" states what the DRIVE can do.

    "unsupported" proves C2 was not used, so "No" is earned. An affirmative
    capability says nothing about whether the rip used it, so it must stay
    unknown rather than become EAC's "Yes".
    """
    from platterpus.parsers.cyanrip_log import parse_cyanrip_log as _parse

    def c2_of(line: str) -> bool | None:
        return _parse(f"cyanrip 0.9.3\n{line}\n").ripping_info.c2_pointers

    assert c2_of("C2 errors:      unsupported by drive") is False
    assert c2_of("C2 errors:      supported by drive") is None
    assert c2_of("C2 errors:      disabled") is False


def test_rows_asserted_from_cyanrip_behaviour_are_not_asserted_for_others() -> None:
    """A log some other ripper wrote must not inherit cyanrip's properties."""
    from platterpus.parsers.rip_log import RipLog as _RipLog

    text = render_eac_style_log(_RipLog(log_creator="whipper 0.7.4"))
    for row in (
        "Delete leading and trailing silent blocks   : ",
        "Null samples used in CRC calculations       : ",
        "Used interface                              : ",
    ):
        line = next(x for x in text.splitlines() if x.startswith(row))
        assert line.endswith("(not reported by the ripper)"), line


def test_one_unmeasured_track_does_not_delete_the_whole_toc() -> None:
    """A data track has no sectors; that must not remove the other 13 rows."""
    from platterpus.parsers.rip_log import RipLog as _RipLog
    from platterpus.parsers.rip_log import TrackResult as _Track

    rip_log = _RipLog(
        tracks=(
            _Track(number=1, copy_crc="AAAA0001", start_sector=0, end_sector=14486),
            _Track(number=2, copy_crc="BBBB0002"),  # data track: no geometry
        )
    )
    text = render_eac_style_log(rip_log)
    assert "TOC of the extracted CD" in text
    assert "0:00.00" in text  # track 1 still measured
    assert "?" in text  # track 2 named, not silently dropped


def test_renderer_survives_a_track_with_no_number() -> None:
    """A format spec on None used to collapse the whole log to the stub."""
    from platterpus.parsers.rip_log import RipLog as _RipLog
    from platterpus.parsers.rip_log import TrackResult as _Track

    rip_log = _RipLog(
        tracks=(_Track(number=None, copy_crc="AAAA0001", start_sector=0, end_sector=9),)  # type: ignore[arg-type]
    )
    text = render_eac_style_log(rip_log)
    assert "log could not be rendered" not in text


def test_the_output_format_block_is_gated_on_the_backend_too() -> None:
    """Every row in it asserts something about cyanrip's encoder.

    The three archival-header rows were gated first; this block sat one lower
    and still told a whipper rip that "cyanrip encodes in-process via
    libavcodec" (review finding, 2026-07-28).
    """
    from platterpus.parsers.rip_log import RipLog as _RipLog

    text = render_eac_style_log(_RipLog(log_creator="whipper 0.7.4"))
    for row in (
        "Used output format              : ",
        "Add ID3 tag                     : ",
        "Command line compressor         : ",
    ):
        line = next(x for x in text.splitlines() if x.startswith(row))
        assert line.endswith("(not reported by the ripper)"), line
    assert "libavcodec" not in text


def test_the_backend_gate_is_not_a_substring_match() -> None:
    """ "not-cyanrip 1.0" must not inherit cyanrip's asserted behaviour."""
    from platterpus.parsers.rip_log import RipLog as _RipLog

    for impostor in ("not-cyanrip 1.0", "whipper (cyanrip-compatible)"):
        text = render_eac_style_log(_RipLog(log_creator=impostor))
        line = next(
            x for x in text.splitlines() if x.startswith("Used interface        ")
        )
        assert line.endswith("(not reported by the ripper)"), f"{impostor}: {line}"
    # …while the real thing still asserts.
    real = render_eac_style_log(_RipLog(log_creator="cyanrip 0.9.3"))
    assert "Native Linux SCSI/MMC (libcdio-paranoia)" in real


# --- the pre-gap unit, checked against EAC's real values (2026-07-30) --------


def _eac_pregap_values() -> list[str]:
    """The ten real `Pre-gap length` values from ONE run of the committed EAC log.

    The baseline file is two concatenated EAC runs, each with its own checksum
    footer, so it is split first — a whole-file scan doubles every count and that
    error has already been made once in this project's notes.
    """
    text = _EAC_BASELINE.read_bytes().decode("utf-16")
    first_run = text.split("Exact Audio Copy V1.8")[1]
    return re.findall(r"Pre-gap length\s+(\d+:\d\d:\d\d\.\d\d)", first_run)


def test_eac_pregap_fraction_is_hundredths_not_frames() -> None:
    """Prove the unit from EAC's own output rather than from the column header.

    Every other `FF` field in an EAC log is CD frames (0–74), and this one looks
    identical — which is why our renderer used frames. It is wrong: one of EAC's
    ten real values is `0:00:01.96`, and 96 cannot be a frame index. So the field
    is hundredths of a second.

    This is the floor for the test below: if the baseline ever loses its pre-gap
    rows, this fails loudly instead of the next test passing vacuously.
    """
    values = _eac_pregap_values()
    assert len(values) == 10, f"expected 10 pre-gap rows in one EAC run, got {values}"
    fractions = [int(v.split(".")[1]) for v in values]
    assert max(fractions) > 74, (
        "no EAC value exceeds 74, so this evidence no longer distinguishes "
        "hundredths from frames — re-derive the unit before trusting the renderer"
    )
    assert 96 in fractions, "the decisive value 0:00:01.96 is missing from the baseline"


def test_our_pregap_row_renders_hundredths_so_it_can_match_eac() -> None:
    """Our renderer must be able to produce EAC's values, including `.96`.

    cyanrip 0.9.3 reports no pre-gaps on the reference disc, so this row never
    renders today — it goes live the moment cyanrip learns to detect them (upstream
    PR #115). That is precisely when a silent unit mismatch is hardest to catch: the
    row would simply appear, look plausible, and be wrong on 9 of 10 values.
    """
    # 72 frames is 96 hundredths — the value frames-based rendering could never
    # produce, since it would print `.72`.
    log = RipLog(
        log_creator="cyanrip 0.9.3",
        tracks=(
            TrackResult(
                number=8,
                filename="08.flac",
                copy_crc="D723C1B0",
                pregap_sectors=75 + 72,  # 1 second + 72 frames
            ),
        ),
    )
    text = render_eac_style_log(log)
    assert "     Pre-gap length  0:00:01.96" in text, (
        "the row must render hundredths; frames would print 0:00:01.72"
    )
    assert "0:00:01.72" not in text


def test_no_pregap_rendering_can_produce_an_impossible_fraction() -> None:
    """Sweep every sub-minute sector count: the fraction must stay two digits.

    A rounded conversion could emit `.100` for the last frame of a second, which is
    not a value EAC can print and would misalign the column. Truncation cannot,
    and this proves it across the whole range rather than at one point.
    """
    checked = 0
    for sectors in range(1, 75 * 60):
        log = RipLog(
            log_creator="cyanrip 0.9.3",
            tracks=(
                TrackResult(number=1, copy_crc="AAAA1111", pregap_sectors=sectors),
            ),
        )
        rows = [
            ln
            for ln in render_eac_style_log(log).splitlines()
            if "Pre-gap length" in ln
        ]
        assert len(rows) == 1, f"{sectors} sectors produced {rows}"
        fraction = rows[0].rsplit(".", 1)[1]
        assert len(fraction) == 2 and fraction.isdigit(), rows[0]
        assert int(fraction) <= 99, rows[0]
        checked += 1
    assert checked >= 4000, f"only swept {checked} sector counts"
