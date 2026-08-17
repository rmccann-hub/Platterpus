"""The ``.cue`` we ship is external input, and until now nothing read it.

Every assertion about *what a real cue looks like* in this file reads a
**committed artifact** rather than a hand-typed string — CLAUDE.md, *"when a
committed artifact can settle a question, the test should read the artifact"*.
The two files are:

* ``output_reference/cyanrip_fork_flac/cyanrip_fork_police_classics.cue`` — a
  real fork rip's cue sheet, and
* ``…/cyanrip_fork_police_classics.platterpus.json`` — the report from the same
  rip, which carries the argv we sent (so, the ISRCs) and the ripper's own
  measured pre-gap lengths.

Those are *independent* sources: the cue is judged against the command line and
the ripper's log rows, never against itself. Two witnesses that share an ancestor
agree on their ancestor's bugs.

**What the committed cue proves on its own.** It is a ``beta.1`` rip, one pin
older than the 2026-08-05 rig rip that prompted this module, and it carries a
*larger* instance of the same two defects:

* 13 of its 14 ``ISRC`` lines are missing, and the 13 missing tracks are exactly
  the 13 tracks carrying an ``INDEX 00`` marker — the same set-equality
  signature the newer rip showed at 9 of 14.
* 4 of its ``INDEX 00`` markers are spurious: tracks 3, 6, 11 and 12 have a
  measured pre-gap of **0 frames** in the ripper's own log. (Round 7 fixed that;
  the newer rip marks exactly the 9 non-zero tracks. So this artifact is also
  the negative control proving the pre-gap check can fail.)
* its album ``TITLE`` still reads ``Every Breath You Take∶ The Classics``.

The one thing the committed file cannot settle is the newer rip's exact shape,
so ``_b5_shaped_cue`` *derives* that from the same two artifacts rather than
inventing it, and asserts the derivation landed before using it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from platterpus import cue_validate, rip_audit
from platterpus.cue_validate import (
    COLON_SUBSTITUTE,
    LEVEL_NOTE,
    LEVEL_OK,
    LEVEL_WARN,
    CueFinding,
    ExpectedCue,
    parse_cue,
    restore_metadata_colons,
    sent_album_metadata,
    sent_track_metadata,
    validate_cue,
)

_REFERENCE = (
    Path(__file__).resolve().parent.parent / "output_reference" / "cyanrip_fork_flac"
)
_CUE_PATH = _REFERENCE / "cyanrip_fork_police_classics.cue"
_REPORT_PATH = _REFERENCE / "cyanrip_fork_police_classics.platterpus.json"


# --- reading the committed artifacts ----------------------------------------


def _real_cue() -> str:
    return _CUE_PATH.read_text(encoding="utf-8")


def _real_report() -> dict:
    data = json.loads(_REPORT_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _expected_from_report(report: dict) -> ExpectedCue:
    """Build `ExpectedCue` the way `rip_audit` does — from argv + log rows.

    Deliberately goes through the *production* helpers rather than
    re-implementing the extraction here: a fixture that parses the argv its own
    way is a second implementation, and two implementations agreeing is not
    either one being correct.
    """
    argv = [str(x) for x in (report.get("outcome") or {}).get("ripper_argv") or []]
    sent = sent_track_metadata(argv)
    album = sent_album_metadata(argv)
    tracks = [t for t in report.get("tracks") or [] if isinstance(t, dict)]
    return ExpectedCue(
        isrcs={n: p["isrc"] for n, p in sent.items() if p.get("isrc")},
        pregap_frames={
            t["number"]: t["pregap_length_frames"]
            for t in tracks
            if isinstance(t.get("number"), int)
            and isinstance(t.get("pregap_length_frames"), int)
            and t.get("pregap_state") == "known"
        },
        track_titles={
            n: p["title"].replace(COLON_SUBSTITUTE, ":")
            for n, p in sent.items()
            if p.get("title")
        },
        album_title=(album.get("album") or "").replace(COLON_SUBSTITUTE, ":") or None,
        track_count=len(tracks),
    )


def _codes(findings: list[CueFinding]) -> set[str]:
    return {f.code for f in findings}


def _by_code(findings: list[CueFinding], code: str) -> CueFinding:
    matches = [f for f in findings if f.code == code]
    assert len(matches) == 1, f"expected exactly one {code}, got {len(matches)}"
    return matches[0]


# --- the artifacts are what this file claims they are ------------------------
#
# A non-triviality floor for everything below. If the reference rip is ever
# replaced with a *fixed* one, these fail loudly instead of the defect tests
# quietly starting to pass for the wrong reason.


def test_the_reference_cue_really_does_carry_both_defects() -> None:
    text = _real_cue()
    tracks = parse_cue(text).tracks

    assert len(tracks) == 14, "the reference rip is a 14-track disc"
    with_isrc = [t.number for t in tracks if t.isrc]
    with_index00 = [t.number for t in tracks if t.index00]
    assert with_isrc == [1], f"expected only track 1 to carry an ISRC, got {with_isrc}"
    assert len(with_index00) == 13
    # Set equality — the signature. Every track the cue gave an INDEX 00 is a
    # track it dropped the ISRC from.
    assert set(with_index00) == {t.number for t in tracks if not t.isrc}
    assert text.count(COLON_SUBSTITUTE) >= 1


def test_the_reference_report_disagrees_with_the_cues_pregap_markers() -> None:
    """The independent witness: four of those 13 markers are for 0-frame gaps."""
    expected = _expected_from_report(_real_report())
    zero = {n for n, frames in expected.pregap_frames.items() if frames == 0}
    assert zero == {3, 6, 11, 12}, zero
    assert len(expected.isrcs) == 14, "we sent an ISRC for every track"
    assert expected.pregap_frames[1] == 150, "track 1's lead-in pre-gap"


# --- the ISRC round-trip ------------------------------------------------------


def test_the_reference_cue_is_reported_as_dropping_thirteen_isrcs() -> None:
    findings = validate_cue(_real_cue(), expected=_expected_from_report(_real_report()))
    finding = _by_code(findings, "cue_isrc_missing")

    assert finding.level == LEVEL_WARN
    assert "13 of 14" in finding.text
    # Match the LIST, not loose numbers anywhere in the sentence. A per-number
    # `\b14\b` search passes on the "13 of 14" in the same sentence, so it stayed
    # green with the track list elided at eight — a check satisfied by the wrong
    # thing (CLAUDE.md). Found by the revert harness, 2026-08-06.
    assert "track(s) " + ", ".join(str(n) for n in range(2, 15)) in finding.text
    # And it points at the cause rather than leaving the reader to spot it.
    assert "INDEX 00" in finding.text


def test_this_rips_exact_defect_names_all_nine_missing_isrcs() -> None:
    """The 2026-08-05 rig rip: 9 of 14 ISRCs missing, on exactly the 9 pre-gap
    tracks. Derived from the committed artifacts, not invented — see
    :func:`_b5_shaped_cue`."""
    report = _real_report()
    expected = _expected_from_report(report)
    cue, dropped = _b5_shaped_cue(_real_cue(), expected)

    findings = validate_cue(cue, expected=expected)
    finding = _by_code(findings, "cue_isrc_missing")

    assert finding.level == LEVEL_WARN
    assert "9 of 14" in finding.text
    # The whole list, verbatim — see the note in the 13-of-14 test above. All
    # nine, in order, with nothing elided.
    assert sorted(dropped) == [2, 4, 5, 7, 8, 9, 10, 13, 14]
    assert "track(s) " + ", ".join(str(n) for n in sorted(dropped)) in finding.text
    assert "signature" in finding.text

    # The other half of the same rip: its INDEX 00 markers are CORRECT, so the
    # pre-gap check must pass here while it fails on the older artifact. A
    # validator that warned about everything would satisfy the assertion above
    # without being a check at all.
    assert _by_code(findings, "cue_pregap_ok").level == LEVEL_OK


def test_an_isrc_whose_value_changed_is_a_different_finding_from_a_missing_one() -> (
    None
):
    expected = _expected_from_report(_real_report())
    cue = _real_cue().replace("ISRC GBAAM0201086", "ISRC XXAAM0201086")
    findings = validate_cue(cue, expected=expected)

    mismatch = _by_code(findings, "cue_isrc_mismatch")
    assert mismatch.level == LEVEL_WARN
    assert "XXAAM0201086" in mismatch.text and "GBAAM0201086" in mismatch.text


def test_sending_no_isrcs_is_not_determined_never_ok() -> None:
    """The floor. This check must not be satisfiable by having nothing to compare
    — otherwise an unknown-disc rip would report a clean ISRC round-trip while
    the cue could be carrying anything at all."""
    findings = validate_cue(_real_cue(), expected=ExpectedCue())
    finding = _by_code(findings, "cue_isrc_not_determined")

    assert finding.level == LEVEL_NOTE
    assert "cue_isrc_ok" not in _codes(findings)
    assert LEVEL_OK != finding.level


def test_a_cue_carrying_every_isrc_we_sent_passes() -> None:
    """Positive control — without it every assertion above could be an ISRC check
    that always warns."""
    expected = _expected_from_report(_real_report())
    cue, _ = _b5_shaped_cue(_real_cue(), expected, drop_isrcs=False)
    findings = validate_cue(cue, expected=expected)

    finding = _by_code(findings, "cue_isrc_ok")
    assert finding.level == LEVEL_OK
    assert "14" in finding.text


# --- pre-gap markers ----------------------------------------------------------


def test_the_reference_cue_is_reported_as_marking_four_zero_frame_pregaps() -> None:
    findings = validate_cue(_real_cue(), expected=_expected_from_report(_real_report()))
    finding = _by_code(findings, "cue_pregap_marker_spurious")

    assert finding.level == LEVEL_WARN
    assert "4 track(s)" in finding.text
    for number in (3, 6, 11, 12):
        assert re.search(rf"\b{number}\b", finding.text)


def test_track_one_is_never_expected_to_carry_an_index_00() -> None:
    """Track 1's pre-gap is the disc's lead-in: 150 frames that sit before the
    first sector of audio, with no previous track to append them to. The
    committed cue therefore has no ``INDEX 00`` for track 1 while the report
    records a 150-frame pre-gap for it — and that combination must never be a
    finding. This reads both artifacts rather than asserting the rule abstractly.
    """
    expected = _expected_from_report(_real_report())
    sheet = parse_cue(_real_cue())
    track_one = next(t for t in sheet.tracks if t.number == 1)

    assert expected.pregap_frames[1] > 0 and not track_one.index00, (
        "the artifacts no longer set up the case this test exists for"
    )
    findings = validate_cue(_real_cue(), expected=expected)
    missing = [f for f in findings if f.code == "cue_pregap_marker_missing"]
    assert not missing, [f.text for f in missing]


def test_a_missing_marker_on_a_real_pregap_is_reported() -> None:
    """The other direction, which the committed artifact does not exercise."""
    expected = _expected_from_report(_real_report())
    cue = _real_cue().replace("    INDEX 00 03:11:02\n", "")  # track 2's marker
    findings = validate_cue(cue, expected=expected)

    finding = _by_code(findings, "cue_pregap_marker_missing")
    assert finding.level == LEVEL_WARN
    assert re.search(r"\b2\b", finding.text)


def test_no_measured_pregaps_is_not_determined() -> None:
    expected = _expected_from_report(_real_report())
    findings = validate_cue(
        _real_cue(),
        expected=ExpectedCue(isrcs=expected.isrcs, track_count=expected.track_count),
    )
    finding = _by_code(findings, "cue_pregap_not_determined")
    assert finding.level == LEVEL_NOTE
    assert "cue_pregap_ok" not in _codes(findings)


def test_a_pregap_map_naming_only_track_one_is_not_determined() -> None:
    """The subtler floor: input present, nothing comparable in it. Track 1 is
    exempt, so a map containing only track 1 leaves zero comparisons — which
    must read as "not determined", not as a clean pass."""
    findings = validate_cue(_real_cue(), expected=ExpectedCue(pregap_frames={1: 150}))
    assert "cue_pregap_not_determined" in _codes(findings)
    assert "cue_pregap_ok" not in _codes(findings)


# --- colon fidelity, and the false positive that would sink it ---------------


def test_the_reference_cues_album_title_is_flagged_as_our_escaping_artefact() -> None:
    expected = _expected_from_report(_real_report())
    findings = validate_cue(_real_cue(), expected=expected)
    finding = _by_code(findings, "cue_colon_artefact")

    assert finding.level == LEVEL_WARN
    assert "U+2236" in finding.text
    assert "line 13" in finding.text  # where the album TITLE actually is
    # It says what the title really is, from the argv we sent.
    assert "Every Breath You Take: The Classics" in finding.text


def _cue_with_colons_in_filenames() -> str:
    """A cue whose FILE lines legitimately contain U+2236.

    Not hypothetical: cyanrip sanitises ``:`` out of a *filename* with the same
    RATIO lookalike, so any disc with a colon in a track title produces exactly
    this. The album on the rig is one — its folder is named with the substitute.
    """
    return (
        f'TITLE "Part 1{COLON_SUBSTITUTE} The Beginning"\n'
        'PERFORMER "Someone"\n'
        f'FILE "01 - Overture{COLON_SUBSTITUTE} Dawn.flac" WAVE\n'
        "  TRACK 01 AUDIO\n"
        f'    TITLE "Overture{COLON_SUBSTITUTE} Dawn"\n'
        "    ISRC AAAAA0000001\n"
        "    INDEX 01 00:00:00\n"
    )


def test_a_colon_substitute_inside_a_FILE_line_is_never_flagged() -> None:
    """**The false positive that would make this validator worse than nothing.**

    A ``FILE`` line names a real path. cyanrip writes the U+2236 form there
    because that is what the file on disk is called, so flagging it would invite
    a "fix" that points the cue at a file that does not exist.
    """
    cue = _cue_with_colons_in_filenames()
    file_line = f'FILE "01 - Overture{COLON_SUBSTITUTE} Dawn.flac" WAVE'
    assert file_line in cue, "the fixture no longer sets up the case"

    sheet = parse_cue(cue)
    # Structural, not incidental: paths are kept out of the metadata list, so the
    # colon check cannot reach one even if it wanted to.
    assert any(COLON_SUBSTITUTE in name for name in sheet.files)
    assert not any(
        COLON_SUBSTITUTE in m.value and m.value in sheet.files for m in sheet.metadata
    )

    findings = validate_cue(cue, expected=ExpectedCue())
    finding = _by_code(findings, "cue_colon_artefact")
    # Two metadata offenders (album TITLE, track TITLE) — and NOT the FILE line.
    assert "2 metadata value(s)" in finding.text
    assert "line 1 (TITLE)" in finding.text and "line 5 (TITLE)" in finding.text
    assert "line 3" not in finding.text, "the FILE line was flagged"
    assert "Overture" not in finding.text


def test_restore_metadata_colons_leaves_FILE_lines_byte_identical() -> None:
    cue = _cue_with_colons_in_filenames()
    file_line = f'FILE "01 - Overture{COLON_SUBSTITUTE} Dawn.flac" WAVE'
    restored, changes = restore_metadata_colons(cue)

    assert changes == 2, "only the two metadata values should change"
    assert file_line in restored, "the FILE path was rewritten"
    assert 'TITLE "Part 1: The Beginning"' in restored
    assert 'TITLE "Overture: Dawn"' in restored
    assert restored.count(COLON_SUBSTITUTE) == 1  # the surviving FILE path


def test_restoring_the_reference_cue_changes_exactly_its_album_title() -> None:
    cue = _real_cue()
    restored, changes = restore_metadata_colons(cue)

    assert changes == cue.count(COLON_SUBSTITUTE) == 1
    assert 'TITLE "Every Breath You Take: The Classics"' in restored
    # Everything else is untouched — a repair that reflows the file would break
    # its own checksum-free archival value.
    assert len(restored.splitlines()) == len(cue.splitlines())
    assert restored.replace(":", COLON_SUBSTITUTE, 0) != cue

    # And the repaired file now passes the check that failed on the original.
    expected = _expected_from_report(_real_report())
    assert "cue_colon_artefact" in _codes(validate_cue(cue, expected=expected))
    assert "cue_colon_ok" in _codes(validate_cue(restored, expected=expected))


def test_a_cue_with_no_metadata_lines_is_not_determined() -> None:
    findings = validate_cue(
        'FILE "01.flac" WAVE\n  TRACK 01 AUDIO\n    INDEX 01 00:00:00\n',
        expected=ExpectedCue(),
    )
    assert "cue_colon_not_determined" in _codes(findings)
    assert "cue_colon_ok" not in _codes(findings)


# --- structural sanity --------------------------------------------------------


def test_the_reference_cue_is_structurally_well_formed() -> None:
    findings = validate_cue(_real_cue(), expected=_expected_from_report(_real_report()))
    finding = _by_code(findings, "cue_structure_ok")
    assert finding.level == LEVEL_OK
    assert "14 track(s)" in finding.text


def test_a_gap_in_the_track_numbering_is_reported() -> None:
    cue = _real_cue().replace("  TRACK 07 AUDIO", "  TRACK 08 AUDIO", 1)
    findings = validate_cue(cue, expected=ExpectedCue(track_count=14))
    assert _by_code(findings, "cue_track_numbering").level == LEVEL_WARN


def test_a_track_with_no_INDEX_01_is_reported() -> None:
    cue = _real_cue().replace("    INDEX 01 00:00:00\n", "", 1)
    finding = _by_code(
        validate_cue(cue, expected=ExpectedCue(track_count=14)), "cue_missing_index01"
    )
    assert finding.level == LEVEL_WARN
    assert re.search(r"\b1\b", finding.text)


def test_a_short_cue_is_reported_against_the_expected_track_count() -> None:
    finding = _by_code(
        validate_cue(_real_cue(), expected=ExpectedCue(track_count=15)),
        "cue_track_count",
    )
    assert finding.level == LEVEL_WARN
    assert "14" in finding.text and "15" in finding.text


def test_an_unknown_track_count_is_not_determined_rather_than_passed() -> None:
    findings = validate_cue(_real_cue(), expected=ExpectedCue())
    assert "cue_track_count_not_determined" in _codes(findings)


def test_text_that_is_not_a_cue_at_all_is_not_determined() -> None:
    """Distinct from "this cue is broken". We were handed something we cannot
    read, and saying so is a different claim from an accusation."""
    findings = validate_cue('hello\nworld\n{ "json": true }\n', expected=ExpectedCue())
    finding = _by_code(findings, "cue_unrecognised")
    assert finding.level == LEVEL_NOTE


def test_a_parseable_cue_with_no_tracks_is_a_warning() -> None:
    findings = validate_cue(
        'REM DISCID "E20DFE0E"\nTITLE "Album"\nPERFORMER "Someone"\n',
        expected=ExpectedCue(),
    )
    assert _by_code(findings, "cue_no_tracks").level == LEVEL_WARN


def test_an_empty_cue_is_not_determined() -> None:
    assert _by_code(validate_cue("   \n", expected=ExpectedCue()), "cue_empty")
    assert _by_code(validate_cue("", expected=ExpectedCue()), "cue_empty")


# --- the parser itself --------------------------------------------------------


def test_the_gap_appended_layout_attributes_each_track_to_its_own_FILE() -> None:
    """cyanrip writes ``INDEX 00`` *before* the FILE line, so a FILE can appear
    inside an open TRACK block. Read naively, every track after the first would
    be attributed to the previous track's file. Asserted against the real cue."""
    sheet = parse_cue(_real_cue())
    for track in sheet.tracks:
        assert track.file.startswith(f"{track.number:02d} - "), (
            f"track {track.number} attributed to {track.file!r}"
        )
    assert len(sheet.files) == 14


def test_the_parser_reads_titles_performers_and_rems_off_the_real_cue() -> None:
    sheet = parse_cue(_real_cue())
    assert sheet.album_performer == "The Police"
    assert sheet.album_title.startswith("Every Breath You Take")
    assert any(m.field_name == "REM DISCID" for m in sheet.metadata)
    # A floor: the colon check's denominator has to be a real number.
    assert len(sheet.metadata) >= 30
    assert sheet.lines_understood >= sheet.lines_seen - 1


@pytest.mark.parametrize(
    "text",
    [
        "",
        "\x00\x00\x00",
        "TRACK 99999999999999999999999 AUDIO",
        "INDEX 01 " + "9" * 5000 + ":00:00",
        "FILE " + "x" * 100_000,
        "TITLE " + COLON_SUBSTITUTE * 10_000,
        "REM\nTRACK\nINDEX\nISRC\nFILE\nTITLE\nPERFORMER",
    ],
)
def test_the_parser_never_raises_on_hostile_input(text: str) -> None:
    parse_cue(text)
    validate_cue(text, expected=ExpectedCue(isrcs={1: "X"}, pregap_frames={2: 5}))
    restore_metadata_colons(text)


def test_a_check_that_explodes_is_reported_not_raised(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`validate_cue` is called from inside the rip report writer. If it can
    raise, a malformed cue takes the whole report with it."""

    def boom(sheet: object, expected: object) -> list[CueFinding]:
        raise RuntimeError("kaboom")

    monkeypatch.setattr(cue_validate, "_check_isrcs", boom)
    findings = validate_cue(_real_cue(), expected=ExpectedCue())
    assert _by_code(findings, "cue_check_failed").level == LEVEL_NOTE
    assert "kaboom" in findings[0].text


# --- the constants this module deliberately duplicates -----------------------


def test_the_finding_levels_are_identical_to_the_auditors() -> None:
    """`cue_validate` declares its own level constants so a pure text validator
    does not import the library auditor. That is a second copy, so the drift is
    checked rather than trusted."""
    pairs = [
        (cue_validate.LEVEL_OK, rip_audit.LEVEL_OK),
        (cue_validate.LEVEL_NOTE, rip_audit.LEVEL_NOTE),
        (cue_validate.LEVEL_WARN, rip_audit.LEVEL_WARN),
    ]
    assert len(pairs) == 3
    for mine, theirs in pairs:
        assert mine == theirs
    assert len({m for m, _ in pairs}) == 3, "the three levels must be distinct"


def test_the_colon_substitute_is_the_one_the_backend_actually_sends() -> None:
    """If these ever diverge, the check silently stops finding the artefact it
    exists for — the failure mode that looks exactly like success."""
    from platterpus.adapters.cyanrip_backend import _COLON_SUBSTITUTE

    assert COLON_SUBSTITUTE == _COLON_SUBSTITUTE == "∶"


def test_every_track_of_a_real_disc_is_named_never_elided() -> None:
    """The elision bound must not be able to hide the diagnosis.

    A Red Book CD holds at most 99 tracks, and "which tracks" *is* the finding —
    the set being exactly the pre-gap tracks is what points at the cue writer's
    pre-gap branch. So a 99-track disc names all 99.
    """
    many = {n: f"XX{n:010d}" for n in range(1, 100)}
    cue = "\n".join(
        f"  TRACK {n:02d} AUDIO\n    INDEX 01 00:00:00" for n in range(1, 100)
    )
    finding = _by_code(
        validate_cue(cue, expected=ExpectedCue(isrcs=many)), "cue_isrc_missing"
    )
    assert "more)" not in finding.text
    assert "track(s) " + ", ".join(str(n) for n in range(1, 100)) in finding.text


def test_a_corrupt_cue_claiming_thousands_of_tracks_elides_with_a_count() -> None:
    """And the bound still exists, because external input is not trustworthy —
    but a silent truncation reads as completeness, so the elision is counted."""
    many = {n: f"XX{n:010d}" for n in range(1, 501)}
    cue = "\n".join(f"  TRACK {n} AUDIO\n    INDEX 01 00:00:00" for n in range(1, 501))
    finding = _by_code(
        validate_cue(cue, expected=ExpectedCue(isrcs=many)), "cue_isrc_missing"
    )
    assert f"and {500 - cue_validate.MAX_NAMED_TRACKS} more" in finding.text


# --- deriving this rip's exact shape from the committed artifacts ------------


def _b5_shaped_cue(
    cue_text: str, expected: ExpectedCue, *, drop_isrcs: bool = True
) -> tuple[str, set[int]]:
    """Rewrite the committed cue into the shape the 2026-08-05 rig rip produced.

    Two edits, both driven by the *report's* pre-gap numbers rather than by a
    hand-typed list:

    * ``INDEX 00`` survives only on tracks whose measured pre-gap is non-zero
      (round 7's fix — the committed cue predates it and marks four 0-frame
      gaps), and
    * an ``ISRC`` line is added for every track that ends up **without** an
      ``INDEX 00`` — reproducing the fork's cue writer dropping ISRC precisely
      in its pre-gap branch.

    **And the layout moves with the marker**, which is the part that is easy to
    forget and was: cyanrip nests a track's own ``FILE`` line *after* its
    ``INDEX 00`` only in the gap-appended shape. A track with no pre-gap gets
    the ordinary ``FILE``-then-``TRACK`` order — verified against the 2026-08-15
    rig cue, where tracks 3 and 6 have 0-frame pre-gaps and their ``FILE`` lines
    precede their ``TRACK`` lines. Dropping the marker while leaving the ``FILE``
    inside the block produced a shape the ripper never writes, and the
    ``INDEX 00`` placement check correctly called three of its markers misplaced.
    *What does my stand-in do that the real thing does not* — this is the answer,
    pinned rather than papered over.

    Returns ``(cue_text, tracks_without_an_isrc)`` and asserts the result really
    is the 9-of-14 shape before handing it back: a fixture that quietly drifted
    would make every assertion against it meaningless.
    """
    marked = {
        n
        for n, frames in expected.pregap_frames.items()
        if frames > 0 and n != 1  # track 1's lead-in is never marked
    }
    out: list[str] = []
    current: int | None = None
    #: Where in `out` the open TRACK line sits, and whether this track lost its
    #: marker and so needs its FILE line hoisted above that TRACK line.
    track_line_at: int | None = None
    hoist_next_file = False
    for line in cue_text.splitlines():
        match = re.match(r"^\s*TRACK\s+(?P<n>\d+)\s", line)
        if match:
            current = int(match["n"])
            track_line_at = len(out)
            hoist_next_file = current not in marked
        if re.match(r"^\s*INDEX 00\b", line) and current not in marked:
            continue  # round 7: no marker for a 0-frame pre-gap
        if re.match(r"^\s*ISRC\b", line) and drop_isrcs and current in marked:
            continue
        if re.match(r"^\s*FILE\b", line) and hoist_next_file:
            assert track_line_at is not None
            out.insert(track_line_at, line)
            hoist_next_file = False
            continue
        out.append(line)
        if (
            re.match(r"^\s*PERFORMER\b", line)
            and current is not None
            and current in expected.isrcs
            and (current not in marked or not drop_isrcs)
        ):
            # Re-add the ISRC the committed (older) cue is missing, so the only
            # tracks left without one are the pre-gap tracks.
            if not any(
                re.match(rf"^\s*ISRC\s+{re.escape(expected.isrcs[current])}", prior)
                for prior in out
            ):
                out.append(f"    ISRC {expected.isrcs[current]}")
    text = "\n".join(out) + "\n"

    sheet = parse_cue(text)
    without = {t.number for t in sheet.tracks if not t.isrc and t.number is not None}
    with_marker = {t.number for t in sheet.tracks if t.index00 and t.number is not None}
    assert with_marker == marked == {2, 4, 5, 7, 8, 9, 10, 13, 14}, with_marker
    if drop_isrcs:
        assert without == marked, f"derivation drifted: {without} vs {marked}"
        assert len(without) == 9
    else:
        assert not without, f"every track should carry an ISRC, missing {without}"
    # The layout must still be one cyanrip would write: every track's audio in
    # its own file, every marker nested under its predecessor's. Asserted here,
    # in the fixture, so a future edit to the rewrite cannot quietly hand a
    # malformed sheet to fourteen assertions that were never about layout.
    assert {t.number: t.file for t in sheet.tracks} == {
        n: f"{n:02d} - " + title
        for n, title in (
            (t.number, t.file.split(" - ", 1)[1]) for t in sheet.tracks if t.file
        )
    }, "a track's FILE is no longer its own audio"
    assert "cue_index00_misplaced" not in {
        f.code for f in validate_cue(text, expected=expected)
    }, "the rewrite produced a layout the ripper never writes"
    return text, without


# --- the wiring into rip_audit's self_check ----------------------------------


def test_cue_integrity_is_a_registered_check() -> None:
    names = [c.name for c in rip_audit.CHECKS]
    assert "cue_integrity" in names
    check = next(c for c in rip_audit.CHECKS if c.name == "cue_integrity")
    # It reads the cue text embedded in the report, so it works on a report read
    # on another machine — no filesystem needed.
    assert check.needs_files is False
    assert check.question.endswith("?")


def _audit(report: dict) -> rip_audit.AlbumAudit:
    album = rip_audit.AlbumAudit(folder=Path("."))
    rip_audit._audit_cue_integrity(report, album)
    return album


def test_the_check_reports_the_real_rips_missing_isrcs_end_to_end() -> None:
    """The whole path: a real report in, findings out — with no hand-assembled
    `ExpectedCue` in the middle. This is what would have caught the rig rip."""
    report = _real_report()
    report.setdefault("artifacts", {})["cue"] = {
        "path": "x.cue",
        "exists": True,
        "truncated": False,
        "text": _real_cue(),
    }
    album = _audit(report)

    texts = [f.text for f in album.findings]
    assert any("ISRC(s) we sent are missing" in t for t in texts), texts
    assert any("U+2236" in t for t in texts), texts
    assert album.worst == LEVEL_WARN


def test_an_absent_cue_is_not_determined_never_a_pass() -> None:
    album = _audit({})
    assert album.findings, "the check went silent"
    assert all(f.level != LEVEL_OK for f in album.findings)
    assert "not determined" in album.findings[0].text


def test_a_truncated_cue_is_not_judged() -> None:
    """Every check here reports an *absence*, and a cut-off copy is full of
    absences that the file on disk does not have."""
    album = _audit(
        {"artifacts": {"cue": {"text": _real_cue()[:400], "truncated": True}}}
    )
    assert len(album.findings) == 1
    assert album.findings[0].level == LEVEL_NOTE
    assert "truncated" in album.findings[0].text
    assert "cue sheet — " in album.findings[0].text


def test_the_check_compares_against_the_FIRST_pass_argv() -> None:
    """On a rip where the auto-fix re-ripped two tracks, the last argv describes
    a two-track command. Reading it would report twelve tracks' ISRCs missing —
    the same false alarm `_audit_argv_agreement` was fixed for on real hardware.
    """
    report = _real_report()
    # The artifact's OWN first pass, not a synthetic one built from its last.
    # (Review, 2026-08-06: this used to copy `ripper_argv` — the auto-fix re-rip
    # — into the first-pass slot, which produced a "first pass" carrying `-l 5`.
    # No real first pass looks like that, and reading the artifact's own is both
    # more faithful and what CLAUDE.md asks for: answer from the artifact.)
    full = [str(x) for x in report["outcome"]["ripper_argv_first_pass"]]
    assert any(str(x).startswith("14=") for x in full), "artifact shape changed"
    assert "-l" not in full, "a whole-disc first pass must not carry -l"
    # The *last* pass only re-ripped track 5.
    report["outcome"]["ripper_argv"] = [
        x for x in full if not re.match(r"^\d+=", str(x)) or str(x).startswith("5=")
    ]
    report.setdefault("artifacts", {})["cue"] = {"text": _real_cue(), "exists": True}

    album = _audit(report)
    assert any("13 of 14" in f.text for f in album.findings), [
        f.text for f in album.findings
    ]


def test_an_unknown_pregap_is_never_turned_into_an_accusation() -> None:
    """Tri-state, at the input to the check rather than only at its output.

    ``pregap_state == "unknown"`` means the ripper could not read the pre-gap —
    the length beside it is not a measurement. Feeding it to the marker check
    would accuse the cue of omitting a marker for a gap nobody measured, which is
    the "not determined reported as negative" failure this codebase keeps
    finding. Added 2026-08-06 after the revert harness showed the filter was
    unguarded: the reference rip measures every track, so no existing test could
    tell whether the filter was there.
    """
    report = _real_report()
    expected = _expected_from_report(report)
    cue, _ = _b5_shaped_cue(_real_cue(), expected, drop_isrcs=False)
    report.setdefault("artifacts", {})["cue"] = {"text": cue, "exists": True}

    # Track 3 has a 0-frame gap and correctly carries no INDEX 00. Mark it
    # unmeasured, with a stale non-zero length beside it — exactly the shape a
    # failed sub-channel read leaves behind.
    track_three = next(t for t in report["tracks"] if t["number"] == 3)
    assert track_three["pregap_state"] == "known", "artifact shape changed"
    track_three["pregap_state"] = "unknown"
    track_three["pregap_length_frames"] = 999

    album = _audit(report)
    assert not [f for f in album.findings if "no INDEX 00 marker" in f.text], [
        f.text for f in album.findings
    ]
    # And the check still ran on the tracks that WERE measured — the exclusion
    # must not silently disable the whole check.
    assert any("INDEX 00 markers agree" in f.text for f in album.findings)


def test_a_clean_rip_reaches_an_all_ok_cue_verdict() -> None:
    """Positive control for the wiring, and the proof that `_healthy()` in
    `tests/test_rip_audit.py` only needs a valid cue added to stay green: a
    report carrying a correct cue produces nothing but OK from this check."""
    report = _real_report()
    expected = _expected_from_report(report)
    fixed, _ = _b5_shaped_cue(_real_cue(), expected, drop_isrcs=False)
    fixed, _ = restore_metadata_colons(fixed)
    report.setdefault("artifacts", {})["cue"] = {"text": fixed, "exists": True}

    album = _audit(report)
    assert album.findings
    assert all(f.level == LEVEL_OK for f in album.findings), [
        (f.level, f.text) for f in album.findings
    ]


# --- the partial rip: a shipped feature this check used to accuse -------------
#
# Found by the adversarial review, 2026-08-06, by probing the check with the
# committed report rather than by reading the code. Platterpus lets the user tick
# individual tracks (TASKS #32/#33) and that becomes cyanrip `-l 3,5` — but `-t`
# tag arguments are built from the METADATA and ignore the selection, so a
# two-track rip still sends fourteen ISRCs. The check compared all fourteen
# against a two-track cue and produced four warnings about a rip that did exactly
# what the user asked. CLAUDE.md: a checker that cries wolf on a shipped feature
# is one the reader learns to skip, which costs more than not having it.


def _partial_rip_report(selection: tuple[int, ...]) -> dict:
    """The committed report, rewritten as a rip of `selection` only.

    Built from the real artifact — the argv, the ISRCs and the pre-gap rows are
    the committed ones — so the only invented part is the shape of the partial
    cue, which is invented from the report's own track rows.
    """
    report = _real_report()
    # Build on the artifact's FIRST-pass argv, not its last. The committed rip
    # is a multi-pass one: its `ripper_argv` is the auto-fix re-rip of track 5
    # and already carries `-l 5`. Appending a user selection to *that* would
    # produce an argv with two `-l` flags — a shape cyanrip never receives — and
    # would silently test the wrong selection.
    argv = [str(x) for x in report["outcome"]["ripper_argv_first_pass"]]
    assert "-l" not in argv, "the artifact's first pass is no longer a whole-disc rip"
    # Exactly what `cyanrip_backend` does: `-l` is appended, and the `-t` blobs
    # are left alone (they come from the metadata, not from the selection).
    # A user-selected rip that needed no auto-fix is single-pass, so the whole
    # command line lives in `ripper_argv` and there is no first pass recorded.
    report["outcome"]["ripper_argv"] = [
        *argv,
        "-l",
        ",".join(str(n) for n in selection),
    ]
    report["outcome"]["ripper_argv_first_pass"] = None
    report["tracks"] = [t for t in report["tracks"] if t["number"] in selection]
    assert len(report["tracks"]) == len(selection), "the artifact's track rows moved"

    sheet = parse_cue(_real_cue())
    kept = [t for t in sheet.tracks if t.number in selection]
    assert len(kept) == len(selection)
    # The ISRCs come from the argv we are about to send, not from the committed
    # cue — that cue is the one with the ISRC defect, and reusing its (absent)
    # ISRC lines would make every partial-rip test below fail for the ORIGINAL
    # reason rather than for the selection handling under test.
    sent = sent_track_metadata([str(x) for x in report["outcome"]["ripper_argv"]])
    # The album TITLE line comes from the SAME argv as everything else here, and
    # not from a placeholder. It said `TITLE "Album"` until round 7 lap 31, when
    # the title-fidelity check started comparing the cue's titles against the text
    # we sent and — correctly — reported the placeholder as a mismatch. That is the
    # "what does my stand-in do that the real thing does not" question answering
    # itself: a fixture that invents a title cannot exercise a check about titles.
    #
    # It is written VERBATIM, including the U+2236 the committed argv carries: that
    # rip was made before the backslash escape shipped, and a fixture that quietly
    # modernised its own input would be testing a rip that never happened. The
    # audit consequently reports one colon-artefact warning about this cue, which
    # is *true of that rip* — the assertions below name it instead of using
    # `worst` as a proxy for "no ISRC false positives".
    sent_album = sent_album_metadata([str(x) for x in report["outcome"]["ripper_argv"]])
    album_title = sent_album.get("album", "Album")
    assert COLON_SUBSTITUTE in album_title or ":" in album_title, (
        "the artifact's album title carries neither a colon nor its substitute, so "
        "this fixture no longer exercises the separator case it was built for"
    )
    lines = [f'TITLE "{album_title}"']
    for track in kept:
        assert track.number is not None
        lines += [
            f'FILE "{track.file}" WAVE',
            f"  TRACK {track.number:02d} AUDIO",
            f'    TITLE "{track.title}"',
            f"    ISRC {sent[track.number]['isrc']}",
            "    INDEX 01 00:00:00",
        ]
    report.setdefault("artifacts", {})["cue"] = {
        "text": "\n".join(lines) + "\n",
        "exists": True,
    }
    return report


def test_a_user_selected_partial_rip_is_not_accused_of_missing_twelve_isrcs() -> None:
    """The headline false positive: 12 warnings for a two-track rip.

    Floors, so this cannot pass by the check having gone silent: the ISRC
    finding must still be PRESENT and must still name a real number.
    """
    report = _partial_rip_report((3, 5))
    album = _audit(report)

    # The floor first — the check must still have run and still have compared
    # something. A fix that simply switched the check off would pass a
    # "no warnings" assertion.
    assert any("ISRC" in f.text for f in album.findings), [
        f.text for f in album.findings
    ]
    # The denominator is the SELECTION, not the metadata — "all 2" not "all 14".
    # Asserting the whole sentence rather than a loose "2", because "2 of 14"
    # also contains a 2: a check keyed on the label passes with the subject
    # deleted (CLAUDE.md).
    assert any(
        "all 2 ISRC(s) we sent round-tripped into the cue" in f.text
        for f in album.findings
    ), [f.text for f in album.findings]
    # And now the defect: no accusation about the twelve tracks we never ripped.
    assert not [f for f in album.findings if "do not appear in the cue" in f.text], [
        f.text for f in album.findings
    ]
    assert not [f for f in album.findings if "are missing from the cue" in f.text], [
        f.text for f in album.findings
    ]
    # `album.worst != LEVEL_WARN` stood here as a proxy for "no ISRC false
    # positives" until round 7 lap 31. The fixture's cue is now written from the
    # committed argv verbatim, and that argv predates the backslash escape — so the
    # audit correctly reports exactly one warning, about the U+2236 in the album
    # title. Naming it is *stricter* than the old proxy was: a new warning of any
    # other kind still fails here, where a blanket "worst != warn" would have had to
    # be deleted outright.
    unexpected = [
        f for f in album.findings if f.level == LEVEL_WARN and "U+2236" not in f.text
    ]
    assert not unexpected, [(f.level, f.text) for f in album.findings]


def test_a_partial_rips_non_contiguous_numbering_is_not_determined_not_a_warning() -> (
    None
):
    """Tracks 3 and 5 are legitimately not "1..N in order".

    Reported as NOT DETERMINED rather than silently accepted: which convention
    cyanrip uses under `-l` (original numbers, or renumbered from 1) has never
    been measured here, and a pass we cannot support is as dishonest as an
    accusation we cannot support.
    """
    album = _audit(_partial_rip_report((3, 5)))
    numbering = [f for f in album.findings if "track number" in f.text]

    assert len(numbering) == 1, [f.text for f in album.findings]
    assert numbering[0].level == LEVEL_NOTE
    assert "not checked" in numbering[0].text
    assert "3, 5" in numbering[0].text  # it still names what it saw


def test_a_partial_rip_does_not_demand_a_marker_for_an_unrippable_pregap() -> None:
    """Track 5's pre-gap belongs to track 4's file, and track 4 was not ripped.

    So no `INDEX 00` can be written for it, and its absence is correct. The
    floor: the report must genuinely record a non-zero pre-gap for track 5, or
    this test proves nothing.
    """
    report = _partial_rip_report((3, 5))
    frames = {t["number"]: t["pregap_length_frames"] for t in report["tracks"]}
    assert frames[5] > 0, f"the artifact no longer sets up this case: {frames}"

    album = _audit(report)
    assert not [f for f in album.findings if "no INDEX 00 marker" in f.text], [
        f.text for f in album.findings
    ]


def test_a_contiguous_selection_is_still_pregap_checked() -> None:
    """The other floor, and the one that stops the fix from being an off-switch.

    On a selection of tracks 4 AND 5, track 5's previous track WAS ripped — so
    its file exists, the marker is expressible, and its absence is a real
    finding. If the partial-rip guard were a blanket "skip pre-gaps whenever
    `-l` is present" this would go quiet.
    """
    report = _partial_rip_report((4, 5))
    frames = {t["number"]: t["pregap_length_frames"] for t in report["tracks"]}
    assert frames[5] > 0, f"the artifact no longer sets up this case: {frames}"

    album = _audit(report)
    marker = [f for f in album.findings if "no INDEX 00 marker" in f.text]
    assert len(marker) == 1, [f.text for f in album.findings]
    assert marker[0].level == LEVEL_WARN
    assert "5" in marker[0].text


def test_an_unreadable_track_selection_refuses_to_narrow() -> None:
    """A selection we cannot parse must NOT quietly shrink what gets checked.

    `-l 3-7` is a shape our argv builder never emits; if cyanrip ever grows it,
    reading the `3` and dropping the rest would silently stop checking tracks
    that really were ripped. `None` (whole-disc behaviour) is the conservative
    answer, and it is the one this asserts.
    """
    assert cue_validate.sent_track_selection(["-l", "3-7"]) is None
    assert cue_validate.sent_track_selection(["-l", ""]) is None
    assert cue_validate.sent_track_selection(["cyanrip", "-N"]) is None
    assert cue_validate.sent_track_selection(["-l"]) is None
    # ...and the shape we DO emit is read exactly. Without this the three
    # assertions above are satisfied by a function that always returns None.
    assert cue_validate.sent_track_selection(["-l", "3,5"]) == frozenset({3, 5})


def test_a_whole_disc_rip_still_gets_the_full_isrc_accusation() -> None:
    """The regression floor for the fix itself: narrowing must apply ONLY when a
    selection was actually sent. The committed 14-track rip has no `-l`, so its
    13-of-14 finding must be untouched."""
    report = _real_report()
    # The check reads the FIRST pass, and that is the one that must be free of
    # `-l`. The artifact's *last* pass legitimately has `-l 5` — it is the
    # auto-fix re-rip — and that must not be mistaken for a user selection.
    assert "-l" not in [str(x) for x in report["outcome"]["ripper_argv_first_pass"]]
    assert "-l" in [str(x) for x in report["outcome"]["ripper_argv"]], (
        "this test's whole point is that the LAST pass has an -l; artifact changed"
    )
    report.setdefault("artifacts", {})["cue"] = {"text": _real_cue(), "exists": True}

    album = _audit(report)
    assert any("13 of 14" in f.text for f in album.findings), [
        f.text for f in album.findings
    ]


# --- the never-raises property (CLAUDE.md: every parser of external output) ---

hypothesis = pytest.importorskip("hypothesis")
st = hypothesis.strategies


_LINES = st.sampled_from(
    [
        'REM DISCID "E20DFE0E"',
        'TITLE "Album"',
        "PERFORMER",
        'FILE "01.flac" WAVE',
        "  TRACK 01 AUDIO",
        "  TRACK",
        "    INDEX 00 00:00:00",
        "    INDEX 01",
        "    ISRC GBAAM0201086",
        COLON_SUBSTITUTE * 20,
        "\x00\x1b[31m",
    ]
)


@hypothesis.settings(max_examples=300, deadline=None)
@hypothesis.given(st.one_of(st.text(), st.lists(_LINES, max_size=40).map("\n".join)))
def test_no_input_makes_the_cue_seam_raise(text: str) -> None:
    """The invariant every parser of external output here upholds. A cue is
    written by an external tool and read inside the rip-report writer; a throw
    here would take down the report of a rip that otherwise succeeded."""
    sheet = parse_cue(text)
    assert isinstance(sheet.tracks, list)
    findings = validate_cue(
        text, expected=ExpectedCue(isrcs={1: "A"}, pregap_frames={2: 1}, track_count=3)
    )
    assert findings, "validate_cue must always say something"
    restored, changes = restore_metadata_colons(text)
    assert changes >= 0
    assert COLON_SUBSTITUTE not in restored or changes >= 0


# --- Title fidelity: the check that cannot pass by finding nothing -----------


def _titled_cue(album: str, track_title: str) -> str:
    return "\n".join(
        [
            f'TITLE "{album}"',
            'FILE "01.flac" WAVE',
            "  TRACK 01 AUDIO",
            f'    TITLE "{track_title}"',
            "    INDEX 01 00:00:00",
            "",
        ]
    )


def test_titles_matching_what_we_sent_is_reported_with_a_count() -> None:
    """The pass arm must say how many titles it compared.

    "No substitute found" was the whole of this check until round 7 lap 31, and a
    check that can only succeed by finding nothing is decoration (CLAUDE.md). The
    count is the floor: a future edit that stops comparing turns this OK into a
    NOTE, and the assertion on the number catches an edit that keeps comparing
    but silently compares less.
    """
    findings = validate_cue(
        _titled_cue("Every Breath You Take: The Classics", "Roxanne"),
        expected=ExpectedCue(
            album_title="Every Breath You Take: The Classics",
            track_titles={1: "Roxanne"},
        ),
    )
    ok = _by_code(findings, "cue_colon_ok")
    assert ok.level == LEVEL_OK
    assert "2 title(s) match" in ok.text, ok.text


def test_a_truncated_title_is_caught_even_though_no_substitute_is_present() -> None:
    """The failure the old check was blind to, and the reason for this one.

    Measured, not imagined: cyanrip's real parser turns an unescaped ':' in a
    value into a silent truncation — `album=Every Breath You Take: The
    Classics:album_artist=...` parses to `Every Breath You Take` and the rest is
    dropped, exit 0, nothing logged. The resulting cue contains no U+2236 at all,
    so the U+2236 check would have called it clean.
    """
    findings = validate_cue(
        _titled_cue("Every Breath You Take", "Roxanne"),
        expected=ExpectedCue(
            album_title="Every Breath You Take: The Classics",
            track_titles={1: "Roxanne"},
        ),
    )
    mismatch = _by_code(findings, "cue_title_mismatch")
    assert mismatch.level == LEVEL_WARN
    # It must quote BOTH strings — a mismatch report that says only "differs"
    # cannot be acted on from a bug report.
    assert "Every Breath You Take: The Classics" in mismatch.text
    assert 'cue says "Every Breath You Take"' in mismatch.text
    # And it must name the mechanism, so the reader knows where to look.
    assert "unescaped" in mismatch.text


def test_nothing_to_compare_against_is_not_determined_not_a_pass() -> None:
    """An unknown disc has no expected titles, so there is no verdict to give.

    Tri-state everywhere: the absence of evidence is reported as such. This is the
    arm that stops the check from becoming a rubber stamp on rips it never saw the
    metadata for.
    """
    findings = validate_cue(
        _titled_cue("Some Album", "Some Track"), expected=ExpectedCue()
    )
    assert "cue_colon_ok" not in _codes(findings)
    note = _by_code(findings, "cue_colon_not_determined")
    assert note.level == LEVEL_NOTE


def test_a_title_a_cue_cannot_quote_is_not_determined_rather_than_accused() -> None:
    """A `"` in a title is a formatting difference, not lost text.

    Deliberately a NOTE and not a WARN: a false accusation on a good rip costs
    more trust than a missed one on a rare title, and we have no measured case of
    how cyanrip writes a quote into a cue. When we have one, this can tighten.
    """
    findings = validate_cue(
        _titled_cue("Say It Loud", "Track"),
        expected=ExpectedCue(album_title='Say "It" Loud'),
    )
    assert "cue_title_mismatch" not in _codes(findings)
    note = _by_code(findings, "cue_colon_not_determined")
    assert "cannot quote" in note.text


def test_the_substitute_still_wins_over_the_title_comparison() -> None:
    """Ordering matters: U+2236 gets its own message, not a generic mismatch.

    Both findings would be true of a cue carrying the substitute, and the
    substitute one is more actionable — it names the repair. Asserting the
    ordering pins it, because which of two true diagnoses a user sees is a
    product decision, not an accident of control flow.
    """
    findings = validate_cue(
        _titled_cue(f"Every Breath You Take{COLON_SUBSTITUTE} The Classics", "Roxanne"),
        expected=ExpectedCue(album_title="Every Breath You Take: The Classics"),
    )
    assert "cue_colon_artefact" in _codes(findings)
    assert "cue_title_mismatch" not in _codes(findings)


# --- INDEX 00 placement: the misplaced pre-gap marker on a partial rip -------
#
# Everything here is measured off two committed artifacts from one hardware run
# (Bazzite + Pioneer BDR-209D, 2026-08-15, cyanrip `platterpus-fork-gddf7ac3`,
# app 0.6.12b6, `-l 1,3,5,6,7` on a 14-track disc). The run is round 8's rip on
# the pin under review; the fork reported the same defect independently from
# their side, so the two findings are a two-sided confirmation rather than one
# project's anecdote.
#
# The artifact is the point. Nothing below hard-codes "682" from a chat log —
# the numbers are re-derived from the cue and the report every run, and the
# derivation is asserted before it is used.

_RIG = (
    Path(__file__).resolve().parent.parent / "docs" / "handshake" / "artifactsround08"
)
_RIG_CUE_PATH = _RIG / "round08pinripcue.cue"
_RIG_REPORT_PATH = _RIG / "round08pinripreport.json"


def _rig_cue() -> str:
    return _RIG_CUE_PATH.read_text(encoding="utf-8")


def _rig_expected() -> ExpectedCue:
    """`ExpectedCue` for the rig rip, built the way `rip_audit` builds it."""
    report = json.loads(_RIG_REPORT_PATH.read_text(encoding="utf-8"))
    argv = [str(x) for x in (report.get("outcome") or {}).get("ripper_argv") or []]
    tracks = [t for t in report.get("tracks") or [] if isinstance(t, dict)]
    return ExpectedCue(
        pregap_frames={
            t["number"]: t["pregap_length_frames"]
            for t in tracks
            if isinstance(t.get("number"), int)
            and isinstance(t.get("pregap_length_frames"), int)
            and t.get("pregap_state") == "known"
        },
        track_frames={
            t["number"]: t["end_sector"] - t["start_sector"] + 1
            for t in tracks
            if isinstance(t.get("number"), int)
            and isinstance(t.get("start_sector"), int)
            and isinstance(t.get("end_sector"), int)
        },
        ripped_tracks=cue_validate.sent_track_selection(argv),
    )


def test_index_time_to_frames_reads_cue_times_and_refuses_malformed_ones() -> None:
    """`MM:SS:FF` in CD frames, and a range check that is not cosmetic.

    An `FF` of 80 is a malformed marker, not a large one. Normalising it would
    turn a corrupt time into a plausible number and let the placement check
    reason about a position nobody wrote.
    """
    assert cue_validate.index_time_to_frames("00:00:00") == 0
    assert cue_validate.index_time_to_frames("05:00:35") == 22535
    assert cue_validate.index_time_to_frames("04:05:53") == 18428
    # Minutes are unbounded: one file may legally exceed 99 minutes.
    assert cue_validate.index_time_to_frames("120:00:00") == 120 * 60 * 75
    for bad in ("", "1:2", "aa:bb:cc", "00:61:00", "00:00:80", "00:00:-1", "1:2:3:4"):
        assert cue_validate.index_time_to_frames(bad) is None, bad


def test_the_rig_cue_carries_one_orphaned_index00_and_one_correct_one() -> None:
    """The measured defect, re-derived from the two committed artifacts.

    Track 5's pre-gap marker is nested under **track 3's** file because track 4
    was not part of the rip; track 7's is nested under track 6's file, which
    *was* ripped, and is correct. One cue, both outcomes — which is what makes
    the check falsifiable rather than a detector that flags every partial rip.
    """
    sheet = parse_cue(_rig_cue())
    by_number = {t.number: t for t in sheet.tracks}

    # Derive, then assert the derivation landed, then use it.
    assert set(by_number) == {1, 3, 5, 6, 7}, "the rig cue is the 5-track selection"
    marker_5 = cue_validate.index_time_to_frames(by_number[5].index00)
    marker_7 = cue_validate.index_time_to_frames(by_number[7].index00)
    assert marker_5 == 22535 and marker_7 == 18428

    expected = _rig_expected()
    assert expected.ripped_tracks == frozenset({1, 3, 5, 6, 7})
    # Track 5's marker sits under track 3's FILE; track 7's under track 6's.
    assert by_number[5].index00_file == by_number[3].file
    assert by_number[7].index00_file == by_number[6].file
    # The overshoot is arithmetic on the artifacts, not a remembered number.
    assert marker_5 - expected.track_frames[3] == 682
    assert marker_7 < expected.track_frames[6]

    findings = validate_cue(_rig_cue(), expected=expected)
    codes = _codes(findings)
    assert "cue_index00_orphaned" in codes
    assert "cue_index00_ok" not in codes
    orphan = _by_code(findings, "cue_index00_orphaned")
    assert orphan.level == LEVEL_WARN
    # It names the one track and only the one track.
    assert "track 5" in orphan.text
    assert "track 7" not in orphan.text
    # And it carries the measurement, so a reader does not have to compute it.
    assert "682 frame(s)" in orphan.text
    assert "9.09 s" in orphan.text


def test_the_existing_pregap_check_still_passes_on_that_cue() -> None:
    """The new check found what the old one was structurally unable to see.

    `_check_pregaps` skips a track whose predecessor was not ripped, because an
    *absent* marker there is correct. That exemption is still right — this
    asserts it, so the two checks stay complementary instead of one quietly
    subsuming the other and hiding which question is being answered.
    """
    findings = validate_cue(_rig_cue(), expected=_rig_expected())
    assert "cue_pregap_marker_missing" not in _codes(findings)
    assert "cue_pregap_marker_spurious" not in _codes(findings)


def test_a_whole_disc_cue_gets_a_clean_placement_verdict() -> None:
    """The negative control: every marker's previous track is present.

    Read off the committed whole-disc reference rip, so a change that made the
    check fire on ordinary cues fails here rather than in the field. Uses a
    non-trivial floor: at least two markers must actually have been examined,
    or "clean" would only mean "nothing to look at".
    """
    sheet = parse_cue(_real_cue())
    markers = [t for t in sheet.tracks if t.index00 and t.number not in (None, 1)]
    assert len(markers) >= 2, "the reference cue must carry markers to check"

    findings = validate_cue(_real_cue(), expected=_expected_from_report(_real_report()))
    codes = _codes(findings)
    assert "cue_index00_ok" in codes
    assert "cue_index00_orphaned" not in codes
    assert "cue_index00_misplaced" not in codes
    assert "cue_index00_past_eof" not in codes


def test_a_cue_with_no_pregap_markers_is_not_determined_not_ok() -> None:
    """The floor. A check that passes by having nothing to examine is decoration."""
    cue = (
        'FILE "01.flac" WAVE\n'
        "  TRACK 01 AUDIO\n"
        "    INDEX 01 00:00:00\n"
        'FILE "02.flac" WAVE\n'
        "  TRACK 02 AUDIO\n"
        "    INDEX 01 00:00:00\n"
    )
    findings = validate_cue(cue, expected=ExpectedCue())
    assert "cue_index00_ok" not in _codes(findings)
    note = _by_code(findings, "cue_index00_not_determined")
    assert note.level == LEVEL_NOTE


def test_track_1_is_never_place_checked() -> None:
    """Track 1's pre-gap is the disc lead-in and belongs to no file.

    Synthetic, because no real cue writes it — which is exactly why it needs a
    test: the branch is unreachable from any artifact we hold.
    """
    cue = (
        'FILE "01.flac" WAVE\n'
        "  TRACK 01 AUDIO\n"
        "    INDEX 00 00:00:00\n"
        "    INDEX 01 00:02:00\n"
    )
    findings = validate_cue(cue, expected=ExpectedCue())
    assert _by_code(findings, "cue_index00_not_determined")


def test_a_marker_under_the_wrong_present_file_is_misplaced() -> None:
    """Synthetic: the predecessor *was* ripped and the marker still went astray.

    Not observed on any artifact — cyanrip nests correctly whenever the previous
    track is present. Kept because "the previous track is missing" and "the
    previous track is present but the marker is elsewhere" are different faults
    with different fixes, and a checker that collapsed them would misdirect a
    bug report. Written in the *non*-gap-appended layout (each track's own FILE
    line precedes its indices), which is the shape that makes the two differ.
    """
    astray = (
        'FILE "01.flac" WAVE\n'
        "  TRACK 01 AUDIO\n"
        "    INDEX 01 00:00:00\n"
        'FILE "02.flac" WAVE\n'
        "  TRACK 02 AUDIO\n"
        "    INDEX 01 00:00:00\n"
        'FILE "03.flac" WAVE\n'
        "  TRACK 03 AUDIO\n"
        "    INDEX 00 00:01:00\n"
        "    INDEX 01 00:02:00\n"
    )
    findings = validate_cue(astray, expected=ExpectedCue())
    misplaced = _by_code(findings, "cue_index00_misplaced")
    assert misplaced.level == LEVEL_WARN
    assert "track 3" in misplaced.text
    assert '"03.flac"' in misplaced.text and '"02.flac"' in misplaced.text
    assert "cue_index00_ok" not in _codes(findings)

    # And the correct gap-appended shape of the same three tracks is clean, so
    # this is not just "any three-track cue trips the check".
    proper = (
        'FILE "01.flac" WAVE\n'
        "  TRACK 01 AUDIO\n"
        "    INDEX 01 00:00:00\n"
        "  TRACK 02 AUDIO\n"
        "    INDEX 00 00:01:00\n"
        'FILE "02.flac" WAVE\n'
        "    INDEX 01 00:00:00\n"
        "  TRACK 03 AUDIO\n"
        "    INDEX 00 00:01:00\n"
        'FILE "03.flac" WAVE\n'
        "    INDEX 01 00:00:00\n"
    )
    assert "cue_index00_ok" in _codes(validate_cue(proper, expected=ExpectedCue()))


def test_a_marker_past_the_end_of_the_right_file_is_reported() -> None:
    """The predecessor is present and correct, and the marker still overshoots.

    Distinct from the orphan case: here the nesting is right and the *time* is
    wrong, which a cue reader hits the same way but a bug report must describe
    differently.
    """
    cue = (
        'FILE "01.flac" WAVE\n'
        "  TRACK 01 AUDIO\n"
        "    INDEX 01 00:00:00\n"
        "  TRACK 02 AUDIO\n"
        "    INDEX 00 00:20:00\n"
        'FILE "02.flac" WAVE\n'
        "    INDEX 01 00:00:00\n"
    )
    # Track 1 is 1000 frames long; the marker sits at 20 s = 1500 frames.
    findings = validate_cue(cue, expected=ExpectedCue(track_frames={1: 1000}))
    past = _by_code(findings, "cue_index00_past_eof")
    assert past.level == LEVEL_WARN
    assert "500 frame(s)" in past.text
    # Without the lengths it is not an accusation — the nesting alone is fine.
    assert "cue_index00_ok" in _codes(validate_cue(cue, expected=ExpectedCue()))


def test_the_audit_reaches_the_finding_end_to_end_on_the_rig_report() -> None:
    """The plumbing, not just the checker.

    A check whose input is never populated in production passes every test and
    finds nothing in the field. This runs the *production* entry point over the
    committed rig report — which embeds its own cue — and asserts the sentence a
    user would actually see, including the measured overshoot that only exists
    because `rip_audit` now derives `track_frames` from the sector numbers.
    """
    report = json.loads(_RIG_REPORT_PATH.read_text(encoding="utf-8"))
    album = rip_audit.AlbumAudit(folder=Path("/nonexistent/rig-album"))
    rip_audit._audit_cue_integrity(report, album)

    texts = [f.text for f in album.findings]
    assert texts, "the audit produced no cue findings at all"
    hits = [t for t in texts if "has no file to belong to" in t]
    assert len(hits) == 1, texts
    assert "track 5" in hits[0]
    assert "682 frame(s)" in hits[0]
    assert any(f.level == LEVEL_WARN for f in album.findings)


def test_no_markers_is_a_pass_only_when_something_says_none_were_due() -> None:
    """The floor, and its escape hatch — both halves, because either alone is wrong.

    A disc with no signalled pre-gap correctly produces a cue with no `INDEX 00`
    at all, and that is the common case. Calling it "not determined" would put a
    permanent NOTE on most clean rips, and a verdict that can never reach OK is
    not a verdict. But the pass is only earned by an *independent* source saying
    no marker was due — the ripper's measured pre-gap lengths — never by the
    cue's own silence.
    """
    cue = (
        'FILE "01.flac" WAVE\n'
        "  TRACK 01 AUDIO\n"
        "    INDEX 01 00:00:00\n"
        'FILE "02.flac" WAVE\n'
        "  TRACK 02 AUDIO\n"
        "    INDEX 01 00:00:00\n"
    )
    # Measured: track 1 is the lead-in, track 2 has no pre-gap. Nothing was due.
    ok = _by_code(
        validate_cue(cue, expected=ExpectedCue(pregap_frames={1: 150, 2: 0})),
        "cue_index00_ok",
    )
    assert ok.level == LEVEL_OK
    assert "no signalled pre-gap" in ok.text

    # Same cue, nothing measured — the silence is now unexplained.
    assert (
        _by_code(
            validate_cue(cue, expected=ExpectedCue()), "cue_index00_not_determined"
        ).level
        == LEVEL_NOTE
    )

    # Same cue, and a pre-gap *was* measured on track 2. The marker's absence is
    # a real gap in the sheet, so this must not be graded a pass here — the
    # pre-gap check owns that finding and says so.
    findings = validate_cue(cue, expected=ExpectedCue(pregap_frames={1: 150, 2: 90}))
    assert "cue_index00_ok" not in _codes(findings)
    assert _by_code(findings, "cue_pregap_marker_missing").level == LEVEL_WARN
