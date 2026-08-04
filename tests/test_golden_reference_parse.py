"""The fork's golden reference, run through the real parser, asserted per line.

## Why this file exists (round 7 lap 12, J1)

Lap 9's J2 asked whether the fork's new pre-log block disturbs our parser. I
answered from the *design* — label-driven rule table, never positional, property
test for never-raises — and stated the caveat honestly: *"that is a claim about our
parser's design, verified by reading it, not a measurement against the block."*

Their reply was the right one:

> *"Send one (or name the round whose golden reference has it) and we will run the
> real parser over it and report per-line."* — our own offer, quoted back.
> *"Run it and tell us."*

This is that measurement, committed rather than reported once. The artifact is
`docs/handshake/inbound/artifacts/round-7-golden-reference-70dcf19.log` — their
file, byte-for-byte, at the commit they named.

**It found two things a design argument could not**, which is the whole argument
for running it: `Read stalls:` was not parsed at all (a line they added *for us*,
about which I had just answered a design question), and track 1's pre-gap length
disagrees with itself in their log — see
`test_track_one_pregap_disagrees_with_itself_in_their_log`, which is a finding
*about their artifact* and is asserted here so it cannot quietly change.

## What is asserted, and why each thing

Not "the parse succeeded" — that is satisfied by finding nothing. Every field the
log states is checked against the value read *out of the log text* in the same
test, so the expectation cannot drift from the artifact.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from platterpus.parsers import cyanrip_log as parser_module
from platterpus.parsers.cyanrip_log import looks_like_cyanrip_log, parse_cyanrip_log

_REPO = Path(__file__).resolve().parent.parent
GOLDEN = (
    _REPO
    / "docs"
    / "handshake"
    / "inbound"
    / "artifacts"
    / "round-7-golden-reference-70dcf19.log"
)

#: Their new block, verbatim from the artifact. Lines 29-34 at `70dcf19`.
PRE_LOG_OPEN = "--- output before this log was opened ---"
PRE_LOG_CLOSE = "--- end of pre-log output ---"


def _text() -> str:
    return GOLDEN.read_text(encoding="utf-8")


def _disc_rules() -> tuple[object, ...]:
    """Every disc-level rule, from the parser's own tables.

    Read off the module rather than re-listed, so a new rule is covered the moment
    it exists — the alternative is a second inventory that can disagree with the
    first, which is the defect this project keeps finding.
    """
    return tuple(
        rule
        for name in (
            "_RULES_BEFORE_GAPS",
            "_RULES_AFTER_GAPS",
            "_RULES_BEFORE_TRACKS",
            "_RULES_AFTER_TRACKS",
        )
        for rule in getattr(parser_module, name)
    )


def _matching_rule(line: str) -> str | None:
    for rule in _disc_rules():
        if rule.pattern.match(line):  # type: ignore[attr-defined]  # _LineRule
            return str(rule.name)  # type: ignore[attr-defined]  # _LineRule
    return None


def test_the_golden_reference_is_committed_and_is_theirs() -> None:
    """Floor. Every assertion below reads this file; without it they all vanish."""
    assert GOLDEN.is_file(), f"missing golden reference {GOLDEN}"
    text = _text()
    assert looks_like_cyanrip_log(text), "we do not even recognise it as a cyanrip log"
    # Their build, not ours, and the commit they named the file at.
    assert text.startswith("cyanrip 0.9.4-rc1+platterpus.5-beta.1 (platterpus-fork-g")
    assert len(_disc_rules()) >= 20, "the rule table came back nearly empty"


# --- lap 9 J2: does the new pre-log block disturb the parser? -----------------


def test_the_pre_log_block_is_present_in_the_artifact() -> None:
    """The floor under the next test.

    Asserting "the block does not break us" against a file that has no block is
    the purest form of passing by finding nothing.
    """
    lines = _text().splitlines()
    assert PRE_LOG_OPEN in lines, "the artifact has no pre-log block to test against"
    assert PRE_LOG_CLOSE in lines
    start = lines.index(PRE_LOG_OPEN)
    end = lines.index(PRE_LOG_CLOSE)
    assert end > start
    # It really does sit between the header and `Gaps:`, which is the position the
    # J2 question was about.
    assert any(line.startswith("Total time:") for line in lines[:start])
    assert any(line.rstrip() == "Gaps:" for line in lines[end:])


def test_no_pre_log_line_is_claimed_by_a_disc_rule() -> None:
    """The measurement J2 asked for: every line of the block, individually.

    A *false match* is the failure mode that matters. Our parser ignores what it
    does not recognise, so an unrecognised block is inert — the risk is a line
    inside it accidentally satisfying a rule and overwriting a real disc field.
    """
    lines = _text().splitlines()
    start = lines.index(PRE_LOG_OPEN)
    end = lines.index(PRE_LOG_CLOSE)
    block = lines[start : end + 1]
    assert len(block) >= 4, f"the block is only {len(block)} lines: {block}"

    claimed = {line: _matching_rule(line) for line in block if line.strip()}
    offenders = {line: rule for line, rule in claimed.items() if rule}
    assert not offenders, (
        f"a pre-log line was claimed by a disc rule: {offenders}. That line's value "
        "would overwrite a real field parsed from the header above it."
    )
    assert len(claimed) >= 4, "fewer than four non-blank lines examined"


def test_the_block_does_not_shift_the_disc_fields_around_it() -> None:
    """The positional-parsing worry, tested rather than argued.

    Removing the block must change nothing about the parse. If any field moved, the
    parser was position-sensitive somewhere and the design claim was wrong.
    """
    import dataclasses

    text = _text()
    lines = text.splitlines(keepends=True)
    start = next(i for i, x in enumerate(lines) if x.rstrip("\n") == PRE_LOG_OPEN)
    end = next(i for i, x in enumerate(lines) if x.rstrip("\n") == PRE_LOG_CLOSE)
    without = "".join(lines[:start] + lines[end + 1 :])
    assert without != text, "the removal did not change the text; test is vacuous"

    a, b = parse_cyanrip_log(text), parse_cyanrip_log(without)
    for f in dataclasses.fields(a):
        if f.name == "log_checksum":
            continue  # the checksum covers the text, which we just changed
        assert getattr(a, f.name) == getattr(b, f.name), (
            f"{f.name} changed when the pre-log block was removed — the parser is "
            "position-sensitive, which is exactly what lap 9 J2 asked about"
        )


# --- the two self-describing lines, and the one we were ignoring --------------


def test_the_handshake_and_consumer_lines_are_read() -> None:
    """Both claimed at schema v17, and this is their first real fork artifact."""
    r = parse_cyanrip_log(_text())
    assert (
        r.handshake_note == "round 7 lap 10 OPEN, verdict HOLD -- NOT a released build"
    )
    assert r.consumer == "platterpus/0.6.4b3"
    # The note names lap 10 while the file arrived with lap 12. That is CORRECT and
    # is the property worth having: the state is compiled in when the binary is
    # built, so it cannot name a lap that post-dates it. It is also the fork's own
    # argument for `Handshake-Lap` in their J2.
    assert "lap 10" in r.handshake_note


def test_read_stalls_is_parsed() -> None:
    """REGRESSION: it was not, and I had just answered a design question about it.

    Lap 9's J3 asked whether we wanted the stall figure per-track or disc-level. I
    answered *"disc-level is enough"* — about a line the parser was silently
    dropping. Answering a contract question from the design instead of from the code
    is the exact failure this whole round keeps circling.
    """
    r = parse_cyanrip_log(_text())
    assert r.read_stalls == "none (no read exceeded 10s)", (
        f"read_stalls is {r.read_stalls!r}; the artifact's line is "
        "'Read stalls:    none (no read exceeded 10s)'"
    )
    # And the value is taken verbatim rather than normalised into a boolean: "none"
    # names the threshold it was measured against, which a bool would discard.
    assert "10s" in r.read_stalls


def test_read_stalls_is_absent_not_none_on_stock() -> None:
    """The third state. Stock never prints the line.

    "no stalls measured" and "stalls not measured" are different claims. Collapsing
    them would make every AppImage user's report assert a measurement nothing took.
    """
    stock = sorted((_REPO / "output_reference" / "cyanrip_flac").glob("*.log"))
    assert stock, "no stock log to compare against"
    for path in stock:
        if "EACcompatible" in path.name:
            continue
        r = parse_cyanrip_log(path.read_text(encoding="utf-8", errors="replace"))
        assert r.read_stalls == "", f"{path.name}: {r.read_stalls!r}"


# --- the whole-disc parse, checked against the log's own numbers --------------


def test_the_disc_fields_match_what_the_log_states() -> None:
    """Read the expectation out of the artifact, never out of my memory of it."""
    text = _text()
    r = parse_cyanrip_log(text)

    def stated(pattern: str) -> str:
        m = re.search(pattern, text, re.M)
        assert m, f"the artifact has no line matching {pattern!r}"
        return m.group(1).strip()

    assert r.disc_id == stated(r"^DiscID:\s+(\S+)")
    assert r.cddb_id == stated(r"^CDDB ID:\s+(\S+)")
    assert r.disc_duration == stated(r"^Total time:\s+(\S+)")
    assert r.log_checksum == stated(r"^Log FUN512:\s+(\S+)")
    assert r.ripping_info.drive == stated(r"^Drive used:\s+(.+?)\s*$")
    assert r.rip_completed is True
    assert (r.rip_completed_tracks, r.rip_completed_total) == (3, 3)
    assert len(r.tracks) == 3, "three tracks in, three tracks out"
    assert r.health_status == "No errors occurred"
    # `Paranoia level: none` → nothing measured about cache defeat. Tri-state.
    assert r.ripping_info.defeat_audio_cache is None


def test_an_accuraterip_disabled_disc_verifies_nothing() -> None:
    """`Accurip: disabled` with CRCs printed is the F2/F3 trap in one artifact.

    The per-track blocks carry `Accurip v1/v2/450` values because cyanrip computes
    them regardless; `Accurip: disabled` says they were never compared to anything.
    Reading a computed CRC as a database match would claim independent verification
    for a rip that had none — and the `+450: 00000000` row is the F3 case, a
    zero CRC that must not read as agreement.
    """
    from platterpus.verdict import accuraterip_counts, accuraterip_verdict

    r = parse_cyanrip_log(_text())
    total, verified, partial = accuraterip_counts(r)
    assert (verified, partial) == (0, 0), (
        f"{verified} verified / {partial} partial on a disc where AccurateRip was "
        "disabled — a computed CRC was read as a database match"
    )
    assert total == 3, "the tracks were not counted at all; the check is vacuous"
    _message, level = accuraterip_verdict(r, disc_track_total=3)
    assert level == "neutral", f"level {level!r} for an unverifiable disc"
    for track in r.tracks:
        assert track.accuraterip_lookup == "disabled"
        assert track.accuraterip_offset is not None
        assert track.accuraterip_offset.local_crc == "00000000"


def test_pregap_lsn_zero_is_known_not_absent() -> None:
    """Track 1 reports `Pregap LSN: 0`, and `0` is falsy.

    A truthiness check anywhere on this path turns a *reported* position into "not
    reported". The parser gets it right; this pins it, because the artifact is the
    only place the zero case has ever actually appeared.
    """
    r = parse_cyanrip_log(_text())
    first = r.tracks[0]
    assert first.pregap_start_lsn == 0
    assert not first.pregap_start_lsn, "0 must still be falsy — that IS the trap"
    assert first.pregap_state == "known", (
        "a reported LSN of 0 was classified as unknown, so a falsy check swallowed it"
    )


def test_an_unreadable_subchannel_is_unknown_with_its_reason() -> None:
    """Track 3: `Pregap LSN: unknown (sub-channel unreadable)`.

    The reason is the point. "unknown" alone leaves the user unable to tell a drive
    limitation from a disc without pre-gaps.
    """
    r = parse_cyanrip_log(_text())
    third = r.tracks[2]
    assert third.pregap_state == "unknown"
    assert third.pregap_start_lsn is None
    assert third.pregap_length_frames is None
    assert "sub-channel unreadable" in third.pregap_unknown_reason


# --- a finding about THEIR artifact -------------------------------------------


def test_track_one_pregap_disagrees_with_itself_in_their_log() -> None:
    """**A finding, asserted so it cannot change quietly.**

    Their log states track 1's pre-gap twice and the two disagree by exactly 2x:

    * `Pregap length: 300 frames` and `Pregap LSN: 0 (duration: 00:04.00)`
      — internally consistent with each other (4s x 75 = 300).
    * `Start LSN: 150` minus `Pregap LSN: 0` = **150**, and the `Gaps:` block says
      `150 frame pregap in track 1` — also internally consistent with each other.

    **Track 2 is the control**: LSN 300 -> start 375 = 75, stated 75 frames, stated
    duration `00:01.00` = 75, `Gaps:` says 75. All four agree. So this is not our
    arithmetic and not a general problem with their pre-gap path — it is one track.

    We take the per-track `Pregap length` (300), which means our EAC-style log
    renders `0:00:04.00` for a gap their own `Gaps:` block calls 150 frames. Lap 13
    asks which value is authoritative rather than guessing: a cue declaring
    `PREGAP 00:02:00` on top of a 150-frame lead-in would make 300 correct and the
    `Gaps:` line the incomplete one, and we cannot tell from outside.

    If they change either line this test fails, which is the point — it is the
    record of a disagreement, and a silent change would erase the question.
    """
    text = _text()
    r = parse_cyanrip_log(text)

    def frames_of(mmssff: str) -> int:
        minutes, rest = mmssff.split(":", 1)
        seconds, frames = rest.split(".", 1)
        return (int(minutes) * 60 + int(seconds)) * 75 + int(frames)

    gaps = {
        int(m.group("track")): int(m.group("frames"))
        for m in re.finditer(
            r"^\s+(?P<frames>\d+) frame pregap in track (?P<track>\d+)", text, re.M
        )
    }
    assert gaps, "no Gaps rows parsed out of the artifact; the comparison is vacuous"

    durations = [
        frames_of(m.group(1))
        for m in re.finditer(r"^\s+Pregap LSN:\s+\d+ \(duration: (\S+)\)", text, re.M)
    ]
    assert len(durations) == 2, (
        f"expected two reported pregap durations, got {durations}"
    )

    first, second = r.tracks[0], r.tracks[1]

    # Track 2 — the control. Every source agrees, which is what makes track 1 a
    # finding rather than a suspicion about our own reading.
    assert second.pregap_length_frames == 75
    assert second.start_sector is not None and second.pregap_start_lsn is not None
    assert second.start_sector - second.pregap_start_lsn == 75
    assert durations[1] == 75
    assert gaps[2] == 75

    # Track 1 — two internally-consistent pairs that disagree with each other.
    assert first.pregap_length_frames == 300
    assert durations[0] == 300, "the stated duration no longer agrees with 300 frames"
    assert first.start_sector is not None and first.pregap_start_lsn is not None
    derived = first.start_sector - first.pregap_start_lsn
    assert derived == 150, f"LSN arithmetic gives {derived}, not 150"
    assert gaps[1] == 150, "the Gaps block no longer says 150"
    assert first.pregap_length_frames == 2 * derived, (
        "the 2x relationship changed. Re-read the artifact and lap 13's question "
        "before updating this test — the disagreement is the thing being recorded."
    )

    # And the audio geometry is NOT in doubt, which narrows the question to the gap.
    assert first.start_sector == 150
    assert first.end_sector == 374
    assert first.end_sector - first.start_sector + 1 == 225  # matches "Frames: 225"


@pytest.mark.parametrize("truncate_at", [0, 1, 5, 30, 100, 200, 278])
def test_a_truncated_golden_reference_never_raises(truncate_at: int) -> None:
    """The never-raises rule, exercised on their real text rather than fuzz.

    A killed rip leaves a log cut mid-write, and this is the closest thing we have
    to what that looks like for the *new* format.
    """
    lines = _text().splitlines(keepends=True)
    parsed = parse_cyanrip_log("".join(lines[:truncate_at]))
    assert parsed is not None
