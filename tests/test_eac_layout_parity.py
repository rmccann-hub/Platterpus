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

from dataclasses import replace
from pathlib import Path

import pytest

from platterpus.eac_log_export import render_eac_style_log
from platterpus.parity import compare_logs
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.parsers.rip_log import RipLog

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
    assert "Utilize accurate stream : (not reported by cyanrip)" in text
    assert text.count("(not reported by cyanrip)") >= 1


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
