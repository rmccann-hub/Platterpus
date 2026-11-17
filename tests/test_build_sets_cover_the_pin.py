"""The fork builds whose ``-Z`` log the record reads include the builds we ship with.

**The defect (the fork's round 41 lap 5 S18).** ``AR_GUIDED_CONVERGENCE_BUILDS`` and
``OTHER_READS_COMPLETE_BUILDS`` lived in ``track_record_sources.py`` and stayed at
``.31`` while ``fork_source`` named ``.32``, ``.33`` and ``.34`` under review. A
build at or after ``.31`` that is not in the first set makes
``ar_guided_convergence`` answer None, so in round 41's run (0.7.127 with ``.34``)
the secure re-read's EAC-layout log said, for 13 of its 14 tracks::

    Record: re-read, at least 2 agreeing of 3; verified by AccurateRip v1 at
    confidence 129 and v2 at confidence 200; whether the fork's .31
    AccurateRip-guided -Z rule chose this read is not determined (this release
    does not read that build's log)

(``docs/handshake/artifactsround41/round41fullsecurerereadeac.log``, track 1, filed
on the evidence branch at ``193801b1``), though ``.34``'s log ends each converged
track in the agreement form and prints the overrule when the rule fires. ``.34``'s
source is ``.31``'s for every line the record reads; the sets cite it
(:mod:`platterpus.deps.fork_source`).

**What is held here.** (1) Every fork-build-number set either module defines is
named below with its rule, so a new one cannot escape the check; each set whose rule
is "this build and later, once its source is read" contains the build under review
and the production build, both derived from ``fork_source``'s targets, never typed.
(2) A ``.34`` re-read's record, from the run's own securing-pass lines: no "not
determined", an exact count, and the overrule named where the log names it.

Round 41's evidence is not among the test fixtures (``tests/evidence_paths.py``
resolves only ``tests/fixtures/evidence/``, which holds no ``artifactsround41``), so
the log text below is the run's securing pass
(``round41fullsecurerereadsecuringpass.txt``, the same commit), trimmed to the rows
the record reads. Text only; no audio (Critical rule 8).
"""

from __future__ import annotations

from typing import Final

import pytest

from platterpus import track_record_sources
from platterpus.deps import fork_source
from platterpus.eac_log_export import render_eac_style_log
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.parsers.rip_log import TrackResult
from platterpus.track_record import RECORD_AR_GUIDED, RECORD_REREAD, track_record
from platterpus.track_record_sources import (
    AR_GUIDED_CONVERGENCE_BUILDS,
    AR_GUIDED_FIRST_BUILD,
    OTHER_READS_COMPLETE_BUILDS,
    ar_guided_convergence,
    fork_build_number,
    prints_every_other_read,
)
from platterpus.uiscript.track_record_grading import eac_log_blocks

#: Every module-level set of fork BUILD NUMBERS, by module and name, with whether
#: its rule is "this build and later, once its source is read" (so the builds we
#: ship with must be in it). A set not listed here fails
#: :func:`test_every_build_number_set_is_registered`.
_BUILD_NUMBER_SETS: Final[dict[tuple[str, str], bool]] = {
    ("fork_source", "AR_GUIDED_CONVERGENCE_BUILDS"): True,
    ("fork_source", "OTHER_READS_COMPLETE_BUILDS"): True,
}

_MODULES: Final[dict[str, object]] = {
    "fork_source": fork_source,
    "track_record_sources": track_record_sources,
}

_BANNER_34: Final[str] = "cyanrip 0.9.4-rc3+platterpus.34 (platterpus-fork-gfb28088)"


def _shipped_builds() -> dict[str, int]:
    """The build numbers of the pin under review and the production pin, read off
    the version each target pairs with its commit (``tests/test_fork_source.py``
    holds the pairing), so a pin move moves these with it."""
    found: dict[str, int] = {}
    for label, target in (
        ("PIN_UNDER_REVIEW", fork_source.UNDER_REVIEW_TARGET),
        ("FORK_PIN", fork_source.PRODUCTION_TARGET),
    ):
        number = fork_build_number(f"cyanrip {target.version}")
        assert number is not None, (
            f"{label}'s version {target.version!r} names no build"
        )
        found[label] = number
    assert fork_source.UNDER_REVIEW_TARGET.pin == fork_source.PIN_UNDER_REVIEW
    assert fork_source.PRODUCTION_TARGET.pin == fork_source.FORK_PIN
    return found


def _int_sets(module: object) -> dict[str, frozenset[int]]:
    return {
        name: value
        for name, value in vars(module).items()
        if name.isupper()
        and isinstance(value, frozenset)
        and value
        and all(isinstance(v, int) and not isinstance(v, bool) for v in value)
    }


def test_every_build_number_set_is_registered() -> None:
    """A set of build numbers added to either module must be classified here."""
    seen: dict[tuple[str, str], frozenset[int]] = {}
    for module_name, module in _MODULES.items():
        for name, value in _int_sets(module).items():
            # A re-export is the same object; file it under the module that owns it.
            owner = (
                "fork_source"
                if value is getattr(fork_source, name, None)
                else module_name
            )
            seen[(owner, name)] = value
    # Floor: the check found the two sets the defect was in.
    assert len(seen) >= 2, seen
    assert set(seen) == set(_BUILD_NUMBER_SETS), (
        f"build-number sets {sorted(set(seen) ^ set(_BUILD_NUMBER_SETS))} are not "
        "registered in _BUILD_NUMBER_SETS (or no longer exist): say whether each "
        "holds 'this build and later, once read', so a pin move is checked against it"
    )


#: The open-ended sets, written out (not computed from the registry, so an empty
#: registry cannot make this sweep pass on nothing); the registry is held to it.
_OPEN_ENDED: Final[tuple[tuple[str, str], ...]] = (
    ("fork_source", "AR_GUIDED_CONVERGENCE_BUILDS"),
    ("fork_source", "OTHER_READS_COMPLETE_BUILDS"),
)


def test_the_open_ended_list_is_the_registrys() -> None:
    assert set(_OPEN_ENDED) == {
        k for k, open_ended in _BUILD_NUMBER_SETS.items() if open_ended
    }


@pytest.mark.parametrize(("module_name", "name"), _OPEN_ENDED)
def test_each_open_ended_set_holds_the_builds_we_ship_with(
    module_name: str, name: str
) -> None:
    """Naming a build as the pin under review, or rolling ``FORK_PIN`` to it, must
    name it in each set too, once its source is read; until then this fails. If the
    build changed a line the set's reader reads, it needs a new reader, not a
    silent miss."""
    members = getattr(_MODULES[module_name], name)
    for label, number in _shipped_builds().items():
        assert number in members, (
            f"{label} is +platterpus.{number}, which {module_name}.{name} does not "
            f"list ({sorted(members)}): read that build's source for the lines this "
            "set stands for, and add it with its citation (the fork's round 41 lap 5 "
            "S18 found .32 to .34 missing)"
        )


def test_the_old_names_still_import_from_track_record_sources() -> None:
    assert track_record_sources.AR_GUIDED_CONVERGENCE_BUILDS is (
        fork_source.AR_GUIDED_CONVERGENCE_BUILDS
    )
    assert track_record_sources.OTHER_READS_COMPLETE_BUILDS is (
        fork_source.OTHER_READS_COMPLETE_BUILDS
    )


def test_the_builds_read_are_exactly_those_cited() -> None:
    """Enumerated, never a range: the sets are exactly the builds whose source
    their comments cite (``.31`` to ``.34`` for the rule; ``.30`` to ``.34`` for
    the lines), and every one is a build that can apply the rule."""
    assert AR_GUIDED_CONVERGENCE_BUILDS == frozenset({31, 32, 33, 34})
    assert OTHER_READS_COMPLETE_BUILDS == frozenset({30, 31, 32, 33, 34})
    assert min(AR_GUIDED_CONVERGENCE_BUILDS) >= AR_GUIDED_FIRST_BUILD


# --- round 41's secure re-read, on .34 ---------------------------------------------

#: The run's securing pass (``-l 3,5 -Z 2 -r 5 --reread-until-accuraterip 2``),
#: verbatim but trimmed to the rows the record reads. Track 3 converged after 4
#: reads, one of which (``061D2412``) was not kept; track 5 reached the repeat limit
#: after AccurateRip overruled its agreement (``cyanrip@fb28088:src/cyanrip_main.c:
#: 2314``'s form).
_SECURING_PASS_34: Final[str] = f"""{_BANNER_34}
Disc tracks:    14
Tracks to rip:  3, 5
AccurateRip:    found

Tracks:

Repeating ripping (0 out of 2 matches for current checksum 061D2412)

Repeating ripping (0 out of 2 matches for current checksum 59D352DD)

Repeating ripping (1 out of 2 matches for current checksum 59D352DD)

Done; (2 out of 2 matches for current checksum 59D352DD)
Track 3 read with no error reported.
Summary:

  EAC CRC32:     59D352DD (after 4 rips)
  Secure re-read:  converged after 4 reads
  Other read:      061D2412, read 1 time, differs from the kept read in second 240 (04:00)
  Accurip:       disc found in database (max confidence: 200)
    Accurip v1:  3C8BDDD2 (accurately ripped, confidence 128)
    Accurip v2:  96DF8C22 (accurately ripped, confidence 200)

  File(s):
    The Police/secure reread/03 - Message in a Bottle.flac


Repeating ripping (0 out of 2 matches for current checksum E0036697)

Repeating ripping (1 out of 2 matches for current checksum E0036697)

Repeating ripping (2 out of 2 matches for current checksum E0036697)

Repeating ripping (3 out of 2 matches for current checksum E0036697)

Done; (repeat limit of 5 reads reached; at most 5 reads agreed; agreement on E0036697 overruled by AccurateRip)
Track 5 read with errors.
Summary:

  EAC CRC32:     E0036697 (after 5 rips)
  Secure re-read:  did NOT converge after 5 reads (repeat limit hit)
  Accurip:       disc found in database (max confidence: 200)
    Accurip v1:  F5426D5F (not found, either a new pressing, or bad rip)
    Accurip v2:  9EEB8843 (not found, either a new pressing, or bad rip)

  File(s):
    The Police/secure reread/05 - Don't Stand So Close to Me.flac

Secure re-reads: 1 track did not converge (track 5)
Ripping errors: 0
Rip completed:  yes (2 of 14 tracks)
"""


def _track(number: int, text: str = _SECURING_PASS_34) -> TrackResult:
    (track,) = [t for t in parse_cyanrip_log(text).tracks if t.number == number]
    return track


def test_a_converged_34_track_is_read_not_left_undetermined() -> None:
    """The defect itself: track 3 of round 41's securing pass. Its record said
    ``at least 2 agreeing of 4`` and "not determined"; ``.34``'s log states both."""
    track = _track(3)
    # The parse is what the record stands on; assert it rather than assume it.
    assert track.rip_count == 4 and track.secure_rerip_converged is True
    assert len(track.other_reads) == 1 and track.other_reads_not_kept == 0
    assert ar_guided_convergence(track, _BANNER_34) is False  # read: not by the rule
    assert prints_every_other_read(_BANNER_34) is True
    record = track_record(
        track, ripper_version=parse_cyanrip_log(_SECURING_PASS_34).log_creator
    )
    assert record.kind == RECORD_REREAD
    assert record.line.startswith(
        "re-read, 3 agreeing of 4; verified by AccurateRip"
    ), record.line
    assert "not determined" not in record.line
    assert "at least" not in record.line


def test_the_eac_layout_logs_record_row_says_it_too() -> None:
    """Through the renderer, which hands the record the log's own banner: the row
    a reader of the EAC-layout log sees."""
    log = parse_cyanrip_log(_SECURING_PASS_34)
    block = eac_log_blocks(render_eac_style_log(log))[3]
    (row,) = [line.strip() for line in block if "Record:" in line]
    assert row.startswith(
        "Record: re-read, 3 agreeing of 4; verified by AccurateRip"
    ), row
    assert "not determined" not in row


def test_a_34_limit_after_an_overrule_names_the_overrule() -> None:
    """Track 5: the limit line names the overrule, and the record says so, with no
    "not determined" beside it."""
    track = _track(5)
    overrule = track.secure_rerip_ar_overrule
    assert overrule is not None and not overrule.ended_on_match
    assert overrule.overruled_crc == "E0036697"
    record = track_record(track, ripper_version=_BANNER_34)
    assert "an agreement on E0036697 was overruled by AccurateRip" in record.line, (
        record.line
    )
    assert "not determined" not in record.line


def test_a_34_early_end_is_the_rule_choosing_the_read() -> None:
    """The early end, in ``.34``'s format (``cyanrip@fb28088:src/cyanrip_main.c:
    2212`` and its row at ``src/cyanrip_log.c:866``, the same strings as ``.31``'s),
    files the track as the rule's choice, not as a caveat."""
    text = _SECURING_PASS_34.replace(
        "Done; (2 out of 2 matches for current checksum 59D352DD)",
        "Done; (read 4 matches AccurateRip at confidence 200; agreement on 061D2412 "
        "overruled by AccurateRip; kept 59D352DD, read 1 time)",
    ).replace(
        "  Secure re-read:  converged after 4 reads",
        "  Secure re-read:  matched AccurateRip after 4 reads (agreement on 061D2412 "
        "overruled)",
    )
    track = _track(3, text)
    assert ar_guided_convergence(track, _BANNER_34) is True
    record = track_record(track, ripper_version=_BANNER_34)
    assert record.kind == RECORD_AR_GUIDED, record
    assert record.line.startswith(
        "re-read: matched AccurateRip at confidence 200 after 4 reads, overruling an "
        "agreement on 061D2412 (kept 59D352DD, from read 4)"
    ), record.line
    assert "not determined" not in record.line


def test_a_build_after_the_ones_read_still_says_not_determined() -> None:
    """The caveat is kept for a build whose log is not read, derived as one past
    the newest read, so the test does not go stale when a build joins."""
    unread = max(AR_GUIDED_CONVERGENCE_BUILDS) + 1
    assert unread not in OTHER_READS_COMPLETE_BUILDS
    version = f"cyanrip 0.9.4-rc3+platterpus.{unread} (platterpus-fork-g0000000)"
    # Without its `Other read:` line, so the count rests on the build alone: a
    # build not read keeps the floor, one read states every read agreed.
    silent = _track(
        3,
        _SECURING_PASS_34.replace(
            "  Other read:      061D2412, read 1 time, differs from the kept read in "
            "second 240 (04:00)\n",
            "",
        ),
    )
    assert silent.other_reads == ()
    line = track_record(silent, ripper_version=version).line
    assert "is not determined (this release does not read that build's log)" in line
    assert line.startswith("re-read, at least 2 agreeing of 4;"), line
    read = track_record(silent, ripper_version=_BANNER_34).line
    assert read.startswith("re-read, 4 agreeing of 4;"), read


# --- the merge: the count must come from the reads it counts ------------------------

#: The album pass's track 3 in the same run: five reads, every one ``3D8FCF0C``,
#: which AccurateRip does not match, so the rule overruled the agreement and the
#: repeat limit ended the track (the run's addendum: the first pass's CRC32 was
#: ``3D8FCF0C``; its EAC-layout log: "the first pass did not converge after 5 reads
#: (repeat limit hit; at most 5 of 5 reads agreed)"). All five agreed, so the log
#: prints no ``Other read:`` line for it.
_ALBUM_PASS_34: Final[str] = f"""{_BANNER_34}
Disc tracks:    14
AccurateRip:    found

Tracks:

Repeating ripping (0 out of 2 matches for current checksum 3D8FCF0C)

Repeating ripping (1 out of 2 matches for current checksum 3D8FCF0C)

Repeating ripping (2 out of 2 matches for current checksum 3D8FCF0C)

Repeating ripping (3 out of 2 matches for current checksum 3D8FCF0C)

Done; (repeat limit of 5 reads reached; at most 5 reads agreed; agreement on 3D8FCF0C overruled by AccurateRip)
Track 3 read with errors.
Summary:

  EAC CRC32:     3D8FCF0C (after 5 rips)
  Secure re-read:  did NOT converge after 5 reads (repeat limit hit)
  Accurip:       disc found in database (max confidence: 200)
    Accurip v1:  0D2C8A11 (not found, either a new pressing, or bad rip)
    Accurip v2:  1B7E40C3 (not found, either a new pressing, or bad rip)

  File(s):
    The Police/secure reread/03 - Message in a Bottle.flac

Ripping errors: 0
"""


def test_the_shipped_tracks_count_is_its_own_reads() -> None:
    """The run's track 3 as the album's record holds it: the securing pass's read
    merged over the album pass's. The run printed ``at least 2 agreeing of 4`` and
    "not determined"; reading ``.34`` must give the true count, 3 of 4 (one read was
    ``061D2412``), not 4 of 4 from the album pass's empty ``Other read:`` lines."""
    from platterpus.ui.main_window_rip import _merge_shipped_track

    album = _track(3, _ALBUM_PASS_34)
    assert album.other_reads == () and album.rip_count == 5  # what the merge inherits
    merged = _merge_shipped_track(album, _track(3), {3: True})
    assert merged.rip_count == 4 and len(merged.other_reads) == 1
    line = track_record(merged, ripper_version=_BANNER_34).line
    assert line.startswith("re-read, 3 agreeing of 4; verified by AccurateRip"), line
    assert "not determined" not in line
