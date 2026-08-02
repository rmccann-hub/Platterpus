"""A killed ripper loses the tail of its log, and the silence was the bug.

Real artifact, the rig, 2026-08-01. cyanrip opens its logfile block-buffered, so
a completed track's record only reaches disk when a 4 KiB stdio block fills or
the process exits cleanly. The rip was cancelled during track 4; the host
wrapper died at once but **podman does not forward the signal into the
container**, so the real ripper kept running with its buffer unflushed. Four
point three seconds later ``fuser -k`` (SIGKILL) reached it. What was left on
disk was exactly **4096 bytes**, ending mid-token at ``REPLAYGAIN_TRACK_GA``.

**Track 3 — "Message in a Bottle", EAC CRC32 59D352DD, AccurateRip v2 at
confidence 200 — had completed 36 seconds before the cancel and was absent from
every artifact Platterpus wrote.** The data was never lost: it is in the
captured stdout, and it is in the report's own ``debug.lines``. The report was
simply built from the file.

What made it a *trust* bug rather than a missing-feature bug is that nothing
said so. A truncated log and a rip that genuinely stopped earlier are
indistinguishable from the parse alone — both give fewer tracks and no finish
report — so the verdict confidently blamed the user's cancel for 12 tracks
"never ripped" when the true figure was 11, and the claim was unfalsifiable from
the artifact.

These tests pin the detector. They do NOT pin recovery — parsing the captured
stdout instead is the separate, larger fix (the parser cannot read stdout at
all today: it opens a track on ``Track N ripped and encoded successfully!``,
which stdout never prints).

The fixture is the real 4096-byte file, byte for byte. Do not regenerate or
normalise it: the exact length and the missing trailing newline are the
evidence.
"""

from __future__ import annotations

from pathlib import Path

from platterpus.eac_log_export import render_eac_style_log
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.rip_report import build_report

_FIXTURES = Path(__file__).parent / "fixtures"
_TRUNCATED = _FIXTURES / "cyanrip_truncated_4096.log"
_COMPLETE = (
    Path(__file__).parent.parent
    / "output_reference"
    / "cyanrip_flac"
    / "cyanrip_flac_police_classics.log"
)


def _truncated_text() -> str:
    return _TRUNCATED.read_bytes().decode("utf-8", errors="replace")


# --- the artifact itself ----------------------------------------------------


def test_the_fixture_is_still_the_evidence_it_was_captured_as() -> None:
    """Guard the guard. The detector keys on the missing trailing newline, so an
    editor that "helpfully" added one would make every test below pass
    vacuously against a file that no longer reproduces the defect."""
    raw = _TRUNCATED.read_bytes()
    assert len(raw) == 4096, "one stdio block — that is the whole finding"
    assert not raw.endswith(b"\n"), "cut mid-write"
    assert raw.endswith(b"REPLAYGAIN_TRACK_GA"), "cut mid-token, in track 2's tags"


# --- detection --------------------------------------------------------------


def test_the_rig_artifact_is_recognised_as_cut_off() -> None:
    rip_log = parse_cyanrip_log(_truncated_text())
    assert rip_log.log_truncated is True
    assert rip_log.last_track_incomplete is True


def test_the_surviving_partial_track_is_flagged_not_silently_trusted() -> None:
    """Track 2's record was itself cut: it kept its CRC and its AccurateRip
    match but never reached its ``File(s):`` line, so the report showed a
    verified track with a null filename and null ReplayGain. Keeping it is
    right — the CRC is real — but a consumer counting verified tracks needs to
    know one of them is a fragment."""
    rip_log = parse_cyanrip_log(_truncated_text())
    assert len(rip_log.tracks) == 2
    last = rip_log.tracks[-1]
    assert last.copy_crc == "985AAE32", "the CRC really was written"
    assert not last.filename, "…but the block stopped before the filename"
    assert rip_log.last_track_incomplete is True


def test_a_complete_log_is_not_flagged() -> None:
    """The false-positive direction. Every real rip would carry the warning if
    this were wrong, which would train the maintainer to ignore it — the exact
    failure mode the Details-tab marker comment warns about."""
    rip_log = parse_cyanrip_log(_COMPLETE.read_text(encoding="utf-8"))
    assert len(rip_log.tracks) == 14
    assert rip_log.log_truncated is False
    assert rip_log.last_track_incomplete is False


def test_a_cleanly_stopped_rip_is_not_flagged() -> None:
    """The discriminating case, and the reason "no finish report" is NOT used as
    a signal: a rip that stopped between tracks has complete records, a final
    newline, and no finish report — exactly like a truncated one on that last
    point. Only the mid-write evidence separates them."""
    text = _COMPLETE.read_text(encoding="utf-8").split("Track 3 ripped")[0]
    assert text.endswith("\n")
    rip_log = parse_cyanrip_log(text)
    assert len(rip_log.tracks) == 2, "same track count as the truncated case"
    assert rip_log.log_truncated is False, "but nothing was cut mid-record"


def test_an_empty_log_is_not_flagged() -> None:
    assert parse_cyanrip_log("").log_truncated is False


# --- the surfaces that made the false claim ---------------------------------


def test_the_json_report_says_its_track_list_is_a_floor() -> None:
    """`log_parse.ok` stays True — the parse really did succeed on what was
    there, and that is precisely why it could not be the warning."""
    report = build_report(
        parse_cyanrip_log(_truncated_text()),
        disc_track_total=14,
        outcome={"status": "cancelled"},
    )
    assert report["log_parse"]["ok"] is True
    assert "cut off mid-write" in (report["log_parse"]["note"] or "")

    codes = {i["code"]: i for i in report["issues"]}
    assert "ripper_log_truncated" in codes, "a silent data loss is the bug itself"
    assert codes["ripper_log_truncated"]["severity"] == "error", (
        "it invalidates the other entries rather than adding to them"
    )


def test_the_attested_log_stops_claiming_tracks_were_never_extracted() -> None:
    """The sentence that was wrong on the rig. "The remaining 12 track(s) were
    never extracted" is a claim about the DISC for which the truncated log is
    the only evidence — and it was both miscounted (11, not 12) and
    unfalsifiable. A truncated log gets the honest sentence instead."""
    text = render_eac_style_log(
        parse_cyanrip_log(_truncated_text()),
        outcome_status="cancelled",
        disc_track_total=14,
    )
    assert "never extracted" not in text
    assert "cut off mid-write" in text
    assert "FLOOR, not a count" in text
    # The measured part is still stated — the fix removes an unsupported claim,
    # it does not make the log vaguer about what it does know.
    assert "2 of 14 disc tracks" in text


def test_an_untruncated_partial_rip_still_names_the_missing_tracks() -> None:
    """The other direction, so the fix is not "never say anything". When the log
    is intact, "12 track(s) were never extracted" is supported by the evidence
    and must still be said."""
    text = render_eac_style_log(
        parse_cyanrip_log(
            _COMPLETE.read_text(encoding="utf-8").split("Track 3 ripped")[0]
        ),
        outcome_status="cancelled",
        disc_track_total=14,
    )
    assert "12 track(s) were never extracted" in text
    assert "FLOOR" not in text
