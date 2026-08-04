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
`docs/handshake/inbound/artifacts/round-07-lap-12-golden-reference-gceca8bc.log` — their
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
_ARTIFACTS = _REPO / "docs" / "handshake" / "inbound" / "artifacts"

#: The reference the fork asked us to parse in lap 12, at `70dcf19`.
#:
#: **Superseded and deliberately KEPT.** It carries the track-1 pre-gap defect our
#: lap-13 §C reported, and it is the only artifact that proves the defect shipped —
#: the same reasoning that keeps the H2 `.platterpus.json` unregenerated. Deleting it
#: would erase the evidence and leave only our account of it.
GOLDEN_WITH_DEFECT = _ARTIFACTS / "round-07-lap-12-golden-reference-gceca8bc.log"

#: The reference regenerated after the fix, which the fork names at `f00cb2b`.
GOLDEN_FIXED = _ARTIFACTS / "round-07-lap-14-golden-reference-g486dce3.log"

#: Every committed reference. The whole-file checks run over ALL of them, because a
#: property that holds for one artifact and not the next is exactly what a corpus is
#: for — and because a new reference must not silently escape the sweep.
GOLDEN_ALL = (GOLDEN_WITH_DEFECT, GOLDEN_FIXED)

#: The newest one, for checks about current behaviour.
GOLDEN = GOLDEN_FIXED

#: Their new block, verbatim from the artifact. Lines 29-34 at `70dcf19`.
PRE_LOG_OPEN = "--- output before this log was opened ---"
PRE_LOG_CLOSE = "--- end of pre-log output ---"


def _text(path: Path = GOLDEN) -> str:
    return path.read_text(encoding="utf-8")


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


#: The lap of the handshake file that DELIVERED each reference. Not read from the
#: artifact — that is the whole point of the test below.
DELIVERED_BY_LAP: dict[str, int] = {
    GOLDEN_WITH_DEFECT.name: 12,
    GOLDEN_FIXED.name: 14,
}


def test_the_handshake_and_consumer_lines_are_read() -> None:
    """Both claimed at schema v17, over every committed reference."""
    for path in GOLDEN_ALL:
        parsed = parse_cyanrip_log(_text(path))
        assert parsed.handshake_note, f"{path.name}: no Handshake: line parsed"
        assert "OPEN" in parsed.handshake_note, path.name
        assert "NOT a released build" in parsed.handshake_note, path.name
        assert parsed.consumer == "platterpus/0.6.4b3", path.name


def test_the_compiled_in_lap_is_always_behind_the_file_that_ships_it() -> None:
    """The property, asserted instead of the literal — and it IS the J2 argument.

    The state is compiled in from the fork's own round files, so **a binary can never
    name a lap that post-dates it**: adding a lap file changes the binary. Both
    references demonstrate it — lap 12 delivered a binary saying lap 10, lap 14
    delivered one saying lap 12 — and that is precisely why a round number alone cannot
    identify a build and why we accepted `Handshake-Lap` for round 8.

    Pinning the literal `"lap 10"` was the wrong assertion: it broke on their next
    reference for a reason that is *correct behaviour*. A test that fails when the
    dependency does the right thing teaches people to edit the test.
    """
    assert len(DELIVERED_BY_LAP) >= 2, "one reference cannot show a pattern"
    for path in GOLDEN_ALL:
        delivering_lap = DELIVERED_BY_LAP[path.name]
        note = parse_cyanrip_log(_text(path)).handshake_note
        match = re.search(r"lap (\d+)", note)
        assert match, f"{path.name}: no lap number in {note!r}"
        compiled_lap = int(match.group(1))
        assert compiled_lap < delivering_lap, (
            f"{path.name} was delivered by lap {delivering_lap} but its binary claims "
            f"lap {compiled_lap}. A binary naming a lap at or after the file that "
            "ships it would mean the compiled-in state is not compiled in."
        )


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


def _pregap_sources(path: Path) -> dict[int, dict[str, int | None]]:
    """The four independent statements each artifact makes about a pre-gap length.

    All four read out of the file, never remembered: the per-track `Pregap length`,
    the duration beside `Pregap LSN`, the `Start LSN − Pregap LSN` arithmetic, and the
    disc-level `Gaps:` block. Four witnesses to one number is what turned a suspicion
    into a finding, and it only worked because they are genuinely independent.
    """
    text = path.read_text(encoding="utf-8")
    parsed = parse_cyanrip_log(text)

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
    durations = [
        frames_of(m.group(1))
        for m in re.finditer(r"^\s+Pregap LSN:\s+\d+ \(duration: (\S+)\)", text, re.M)
    ]
    out: dict[int, dict[str, int | None]] = {}
    for index, track in enumerate(parsed.tracks):
        if track.pregap_start_lsn is None or track.start_sector is None:
            continue  # track 3: sub-channel unreadable, nothing to cross-check
        out[track.number] = {
            "stated": track.pregap_length_frames,
            "duration": durations[index] if index < len(durations) else None,
            "derived": track.start_sector - track.pregap_start_lsn,
            "gaps": gaps.get(track.number),
        }
    return out


def test_the_superseded_reference_still_carries_the_defect() -> None:
    """The evidence that it shipped, asserted so the artifact cannot drift.

    Round 7 lap 13 §C reported that track 1's pre-gap length disagreed with itself:
    `Pregap length: 300 frames` and `duration: 00:04.00` agreeing with each other,
    `Start LSN 150 − Pregap LSN 0 = 150` and the `Gaps:` block agreeing with each
    other, exactly 2x apart. The fork confirmed it from their source — the per-track
    block added the 2-second lead-in **unconditionally**, so a TOC that already
    signalled the gap got the same 150 sectors counted twice — and told us `150` is
    authoritative.

    This artifact is kept because it is the only thing that proves the defect was
    real rather than our reading of it.
    """
    sources = _pregap_sources(GOLDEN_WITH_DEFECT)
    assert set(sources) == {1, 2}, f"expected two cross-checkable tracks, got {sources}"

    one = sources[1]
    assert one["stated"] == 300
    assert one["duration"] == 300, "the stated duration no longer agrees with 300"
    assert one["derived"] == 150
    assert one["gaps"] == 150
    assert one["stated"] == 2 * (one["derived"] or 0), "the 2x relationship changed"

    # Track 2 is the control, and it is the reason this was a finding rather than a
    # doubt about our arithmetic. The fork said so too.
    assert len(set(sources[2].values())) == 1, sources[2]


def test_the_fixed_reference_has_all_four_sources_agreeing() -> None:
    """J1's confirmation: the disagreement is gone, and gone the right way.

    The fork predicted our lap-13 assertion would now fail and called that failure the
    confirmation. It does, and this is the positive form of it — checked as *agreement
    across all four independent sources*, for **both** tracks, so a fix that made
    every source equally wrong would still be caught. That is their own test's
    property, asserted independently on our side of the seam.
    """
    sources = _pregap_sources(GOLDEN_FIXED)
    assert set(sources) == {1, 2}, f"expected two cross-checkable tracks, got {sources}"
    for number, values in sources.items():
        assert None not in values.values(), f"track {number}: missing source {values}"
        assert len(set(values.values())) == 1, (
            f"track {number}'s four pre-gap sources still disagree: {values}"
        )
    # And the authoritative value is the one they named, not merely *a* consistent one.
    assert sources[1]["stated"] == 150
    assert sources[2]["stated"] == 75


def test_the_two_references_differ_only_where_the_fix_landed() -> None:
    """The blast radius of their fix, measured rather than accepted.

    Their §E says track 1's `Pregap length` and its `Pregap LSN` duration changed and
    nothing else. A log-format delta is a claim about *our* parse surface, so we check
    it against our own fields: every parsed value must be identical between the two
    references except the ones they declared, plus the artifact-identity fields (the
    checksum covers changed text, and the banner/timestamp move on every rebuild).
    """
    import dataclasses

    old = parse_cyanrip_log(_text(GOLDEN_WITH_DEFECT))
    new = parse_cyanrip_log(_text(GOLDEN_FIXED))

    # Identity fields legitimately differ between two builds of the same fixture.
    expected_disc_differences = {
        "log_checksum",
        "ripper_build",
        "creation_date",
        "handshake_note",
        "invoked_as",
        "tracks",
    }
    for field in dataclasses.fields(old):
        if field.name in expected_disc_differences:
            continue
        assert getattr(old, field.name) == getattr(new, field.name), (
            f"disc field {field.name} changed between the two references, which their "
            "§E log-format delta does not declare"
        )

    assert len(old.tracks) == len(new.tracks) == 3
    declared = {"pregap_length_frames", "pregap_sectors"}
    # Per-track timing legitimately varies run to run; it is not a format change.
    noise = {"extraction_speed", "extraction_elapsed_seconds"}
    changed: set[str] = set()
    for before_track, after_track in zip(old.tracks, new.tracks, strict=True):
        for field in dataclasses.fields(before_track):
            if field.name in noise:
                continue
            if getattr(before_track, field.name) != getattr(after_track, field.name):
                changed.add(field.name)
    assert changed <= declared, (
        f"their fix changed {sorted(changed - declared)} as well as {sorted(declared)}. "
        "Their §E declares only the pre-gap length; anything else is an undeclared "
        "log-format change and needs raising before we rely on it."
    )
    assert changed, "nothing changed between the references; one of them is misfiled"


def test_every_committed_reference_reports_read_stalls() -> None:
    """The line we were dropping, checked across the corpus rather than once.

    A property asserted against a single artifact is a property of that artifact.
    """
    assert len(GOLDEN_ALL) >= 2, "fewer than two references; there is no corpus"
    for path in GOLDEN_ALL:
        parsed = parse_cyanrip_log(_text(path))
        assert parsed.read_stalls == "none (no read exceeded 10s)", (
            f"{path.name}: read_stalls is {parsed.read_stalls!r}"
        )


#: For each committed reference: the lap that delivered it, and the commit **that
#: lap's prose named it by**. The banner's build is read from the artifact, never
#: listed here — that is the whole point.
#:
#: Both are needed because they differ, which was our lap-15 §C finding.
DELIVERY: dict[str, tuple[int, str]] = {
    GOLDEN_WITH_DEFECT.name: (12, "70dcf19"),
    GOLDEN_FIXED.name: (14, "f00cb2b"),
}


def _banner_build(path: Path) -> str:
    return parse_cyanrip_log(_text(path)).ripper_build


def test_the_filename_names_the_build_that_produced_the_artifact() -> None:
    """The naming convention, and it encodes the lesson rather than restating it.

    A reference has **two** commits — generated by X, committed at Y — and their lap 16
    settled that both get named. The *filename* carries X, because X is the one
    **derivable from the artifact's own content** (its banner) and the one a provenance
    dispute turns on; Y lives in the lap file's prose, which is where their §C puts it.

    Their §C also killed the tempting alternative: regenerating the reference inside the
    change's own commit would not collapse the two numbers, because the artifact would
    then be built from a tree whose HEAD is the *previous* commit and the banner would
    name the parent again. *"It moves the mismatch rather than removing it"* — a file
    cannot contain the hash of a build containing itself. The remedy has to be labelling.
    """
    assert DELIVERY, "no references registered; the convention is unchecked"
    for path in GOLDEN_ALL:
        build = _banner_build(path)
        assert build, f"{path.name}: no build tag in the banner"
        short = build.rsplit("-g", 1)[-1]
        assert short and short in path.name, (
            f"{path.name} does not name the build that produced it ({build}). The "
            "filename convention is that an artifact is identified by the commit its "
            "own banner asserts, so a provenance question is answerable from the name."
        )
        # …and the lap and round, like every other handshake file.
        lap, _named = DELIVERY[path.name]
        assert f"lap-{lap:02d}" in path.name, path.name
        assert path.name.startswith("round-07-"), path.name


def test_the_lap_prose_named_a_different_commit_than_the_banner() -> None:
    """**The lap-15 §C finding, now historical — and kept as the record of it.**

    Laps 12 and 14 named the reference by the commit they *committed* it at; the
    artifact's banner names the commit that *built* it. They differed both times:

    * lap 12 said `70dcf19`; the banner says `platterpus-fork-gceca8bc`
    * lap 14 said `f00cb2b`; the banner says `platterpus-fork-g486dce3`

    `486dce3` is the parent of `f00cb2b`, which confirms the mechanism we guessed from
    outside: the fix commit builds the binary, the next commit checks in the regenerated
    artifact. Benign — but lap 14 §A asserted the opposite outright (*"this lap's header
    names `f00cb2b`, the build of the artifact this lap is about"*), in the section whose
    job is naming which build is which. Rule 12's third instance.

    **Their lap 16 adopted "generated by X, committed at Y" and added a check on their
    side that fails unless a lap names the banner's build.** So this test is now a record
    rather than an open finding, and it stays for the reason we keep the superseded
    reference: it is the evidence, not our account of it.
    """
    for name, (lap, named_by_lap) in DELIVERY.items():
        path = _ARTIFACTS / name
        assert path.is_file(), name
        build = _banner_build(path)
        assert named_by_lap not in build, (
            f"lap {lap} named {named_by_lap!r} and the banner says {build!r} — these "
            "now agree, so the practice changed. Update this test and lap 17's §C, "
            "which report them as having never agreed."
        )


def test_the_behavioural_fingerprint_settles_which_build_it_was() -> None:
    """The counter they proposed in round 6, and the reason a label dispute is cheap.

    A banner is a claim; the log's *content* is evidence. The fixed reference reports
    `Pregap length: 150 frames`, which no build without their §C fix could print — so
    whatever produced it contained the fix, whatever its label says. That is what turned
    our §C from *"which artifact is this?"* into *"which name is wrong?"*, and only the
    second question was ever open.
    """
    fixed = _pregap_sources(GOLDEN_FIXED)
    assert fixed[1]["stated"] == 150, "the fingerprint that identifies the fixed build"
    defective = _pregap_sources(GOLDEN_WITH_DEFECT)
    assert defective[1]["stated"] == 300, (
        "the superseded reference no longer carries the defect, so the two artifacts "
        "are no longer behaviourally distinguishable and the fingerprint is gone"
    )


@pytest.mark.parametrize("truncate_at", [0, 1, 5, 30, 100, 200, 278])
def test_a_truncated_golden_reference_never_raises(truncate_at: int) -> None:
    """The never-raises rule, exercised on their real text rather than fuzz.

    A killed rip leaves a log cut mid-write, and this is the closest thing we have
    to what that looks like for the *new* format.
    """
    lines = _text().splitlines(keepends=True)
    parsed = parse_cyanrip_log("".join(lines[:truncate_at]))
    assert parsed is not None
