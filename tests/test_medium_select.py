"""Picking the right disc out of a multi-disc MusicBrainz release.

The rig failure this exists for (2026-08-02): disc 1 of a four-disc set has 16
tracks. Every code path took ``medium-list[0]``, which listed 18. Platterpus
handed cyanrip ``-t 17=`` and ``-t 18=``; cyanrip answered ``Invalid track
number 17, list has 16 tracks!`` and exited in two seconds with nothing ripped.

The argv chokepoint now refuses an out-of-range ``-t``, so that *symptom* cannot
recur — and it is worth being clear that fixing the symptom made the underlying
bug **more** dangerous, not less. Suppress the two bad arguments and the other
sixteen still go through: a disc-2 rip tagged with disc-1's titles, completing
successfully, looking right, and wrong. A rip that fails loudly is recoverable;
a library entry that is quietly mislabelled is not.

So the assertion this file cares most about is the one where the selector
**refuses to choose**. Two media with the same track count is an ambiguity, and
returning either one as a determination would be a coin flip presented as a
fact.
"""

from __future__ import annotations

import pytest

from platterpus.medium_select import CONFIDENT_BASES, select_medium

_DISC_ID_1 = "pNtImOkdBm9RMBIalzx0w9cfsYY-"
_DISC_ID_2 = "xYz123AbCdEfGhIjKlMnOpQrStU-"


def _medium(position: int, tracks: int, *, disc_ids: tuple[str, ...] = ()) -> dict:
    return {
        "position": str(position),
        "format": "CD",
        "track-count": str(tracks),
        "track-list": [{"position": str(n)} for n in range(1, tracks + 1)],
        "disc-list": [{"id": d} for d in disc_ids],
    }


# --- the rig failure ----------------------------------------------------------


def test_the_four_disc_set_that_killed_a_rip() -> None:
    """The concrete regression. The disc in the drive has 16 tracks and is
    medium 2; medium 1 has 18. Taking `medium-list[0]` is what broke it."""
    media = [
        _medium(1, 18),
        _medium(2, 16, disc_ids=(_DISC_ID_1,)),
        _medium(3, 14),
        _medium(4, 17),
    ]
    choice = select_medium(media, disc_id=_DISC_ID_1, disc_track_count=16)
    assert choice.index == 1
    assert choice.basis == "disc-id"
    assert choice.confident
    assert choice.position == 2
    assert choice.total_media == 4
    # And the track list handed onward is the RIGHT disc's.
    assert len(choice.medium["track-list"]) == 16


def test_the_disc_id_wins_even_when_the_track_count_points_elsewhere() -> None:
    """The disc ID came from the physical TOC. If MB's track count disagrees,
    MB's track count is what is wrong."""
    media = [_medium(1, 16), _medium(2, 18, disc_ids=(_DISC_ID_1,))]
    choice = select_medium(media, disc_id=_DISC_ID_1, disc_track_count=16)
    assert choice.index == 1
    assert choice.basis == "disc-id"


# --- the refusal, which is the point ------------------------------------------


def test_two_media_with_the_same_count_is_an_ambiguity_not_a_match() -> None:
    """A coin flip presented as a fact is the failure mode. Both media have 16
    tracks and no disc IDs: there is genuinely nothing to choose on."""
    media = [_medium(1, 16), _medium(2, 16)]
    choice = select_medium(media, disc_track_count=16)
    assert choice.basis == "undetermined-first"
    assert not choice.confident
    assert "Could not determine" in choice.detail
    # A rip is still possible — the caller gets a medium — but nothing claims
    # it is the right one.
    assert choice.index == 0


def test_no_signals_at_all_is_undetermined() -> None:
    media = [_medium(1, 18), _medium(2, 16)]
    choice = select_medium(media)
    assert choice.basis == "undetermined-first"
    assert not choice.confident


def test_an_unmatched_disc_id_does_not_silently_become_a_match() -> None:
    """MB knows disc IDs for these media and ours is not among them, so this
    release's media are all *not* our disc. Falls through, does not guess."""
    media = [_medium(1, 18, disc_ids=(_DISC_ID_2,)), _medium(2, 20, disc_ids=("z-",))]
    choice = select_medium(media, disc_id=_DISC_ID_1)
    assert not choice.confident


def test_the_undetermined_detail_names_the_counts_it_saw() -> None:
    """A "could not tell" that does not say what it looked at is unactionable —
    the user cannot tell whether MB is wrong or the drive is."""
    media = [_medium(1, 18), _medium(2, 16)]
    detail = select_medium(media, disc_track_count=99).detail
    assert "18" in detail and "16" in detail
    assert "99" in detail


# --- the cases where choosing IS justified ------------------------------------


def test_a_unique_track_count_match_is_enough() -> None:
    media = [_medium(1, 18), _medium(2, 16), _medium(3, 14)]
    choice = select_medium(media, disc_track_count=16)
    assert choice.index == 1
    assert choice.basis == "track-count"
    assert choice.confident


def test_a_sole_medium_needs_no_evidence() -> None:
    choice = select_medium([_medium(1, 12)])
    assert choice.basis == "sole-medium"
    assert choice.confident


def test_a_sole_medium_wins_even_when_mb_has_the_count_wrong() -> None:
    """Checked before the track-count rule on purpose: a single-disc release
    with a wrong count in MB must still resolve, since there is no other disc
    it could possibly be."""
    choice = select_medium([_medium(1, 12)], disc_track_count=13)
    assert choice.basis == "sole-medium"
    assert choice.confident


def test_the_track_list_is_used_when_track_count_is_absent() -> None:
    """MB does not always send `track-count`. Counting the list is what keeps
    the fallback rule usable instead of silently unavailable."""
    media = [_medium(1, 18), _medium(2, 16)]
    for medium in media:
        del medium["track-count"]
    choice = select_medium(media, disc_track_count=16)
    assert choice.index == 1
    assert choice.basis == "track-count"


# --- it never raises ----------------------------------------------------------


@pytest.mark.parametrize(
    "media",
    [
        None,
        [],
        "not a list",
        [None, None],
        [{"track-count": "not a number"}],
        [{"disc-list": "not a list"}],
        [{"track-count": "9" * 5000}],
        [{"position": -1, "track-count": 3}],
        [{}],
        [[], {}],
        {"not": "a list"},
    ],
)
def test_it_never_raises_on_hostile_input(media: object) -> None:
    """MusicBrainz is the untrusted boundary of an unmaintained dependency, so
    an odd payload must produce a verdict, not an exception."""
    choice = select_medium(media, disc_id="x", disc_track_count=3)  # type: ignore[arg-type]
    assert choice.basis in {
        "disc-id",
        "track-count",
        "sole-medium",
        "undetermined-first",
        "none",
    }
    assert isinstance(choice.detail, str) and choice.detail
    assert isinstance(choice.position, int) and choice.position >= 1


def test_a_bad_element_does_not_abort_a_good_selection() -> None:
    """One malformed entry beside three good ones must not lose the answer."""
    media = [None, _medium(2, 16, disc_ids=(_DISC_ID_1,)), "junk"]
    choice = select_medium(media, disc_id=_DISC_ID_1)  # type: ignore[arg-type]
    assert choice.basis == "disc-id"
    assert choice.total_media == 3, "the reported total is what MB actually sent"


def test_an_empty_media_list_reports_none_and_no_medium() -> None:
    choice = select_medium([])
    assert choice.basis == "none"
    assert choice.index == -1
    assert choice.medium == {}
    assert not choice.confident


# --- the confidence flag itself -----------------------------------------------


def test_confidence_is_exactly_the_documented_set() -> None:
    """A floor and a guard: if a basis is added and forgotten, `confident`
    silently answers False for it, or — worse — someone adds it to the set
    without a rule that earns it."""
    assert CONFIDENT_BASES == {"disc-id", "track-count", "sole-medium"}
    assert "undetermined-first" not in CONFIDENT_BASES
    assert "none" not in CONFIDENT_BASES


def test_position_falls_back_to_index_when_mb_omits_it() -> None:
    media = [{"track-count": "10"}, {"track-count": "16"}]
    choice = select_medium(media, disc_track_count=16)
    assert choice.index == 1
    assert choice.position == 2
