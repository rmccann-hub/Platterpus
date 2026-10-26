"""`cyanrip-diagnostics/11`'s two per-track keys, read into the report (schema 40).

The fork holds `kept_read_began` and `isrc_disc_read` back until a release of
ours reads `/11` (their round 36 lap 7 S15). Neither is built, so no record in
either tree carries them: the `/11` rows here are the fork's own `/10` sample
(`cyanrip@5f1d036:docs/sample-interrupted.diagnostics.json`, copied byte for byte
into `tests/fixtures/cyanrip_fork_diagnostics10_interrupted.json`) with the two
keys added in the shapes they proposed: `isrc_disc_read` one of `read
sub-channel`, `q frames`, `read sub-channel, again` (their lap 4 S12), and
`kept_read_began` the instant their `Kept read began:` line prints (lap 7 S5).

**The `/10` half is the stronger claim.** A `/10` record must read exactly as it
did: every field the report carried before is unchanged, and the two new ones say
`not_present`, never a negative.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from platterpus import error_positions as ep
from platterpus import isrc_provenance as ip
from platterpus import record_track_v11 as v11
from platterpus.ripper_ending import STATE_READ

_FIXTURE = (
    Path(__file__).parent / "fixtures" / "cyanrip_fork_diagnostics10_interrupted.json"
)

#: The keys v40 adds to each block's rows; everything else predates it.
_NEW_ISRC_KEYS = {"disc_read", "disc_read_state"}
_NEW_READS_KEYS = {"kept_read_began", "kept_read_began_state"}


def _sample() -> dict[str, object]:
    data = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    assert data["schema"] == "cyanrip-diagnostics/10"
    rows = data["rip"]["track_state"]
    assert len(rows) == 3  # floor: the sample's three tracks
    return data


def _as_v11(data: dict[str, object], **keys: object) -> str:
    """The sample as a `/11` record, each row given ``keys``."""
    copy = json.loads(json.dumps(data))
    copy["schema"] = "cyanrip-diagnostics/11"
    for row in copy["rip"]["track_state"]:
        row.update(keys)
    return json.dumps(copy)


def _blocks(text: str) -> tuple[dict[str, object], ep.ErrorPositionsBlock]:
    reading = ip.parse_isrcs(text)
    return ip.report_block(reading), ep.report_block(reading)


def _without(rows: object, keys: set[str]) -> list[dict[str, object]]:
    assert isinstance(rows, list)
    return [{k: v for k, v in row.items() if k not in keys} for row in rows]


# --- /10 reads as it did ------------------------------------------------------------


def test_a_10_record_reads_as_before_and_the_new_keys_are_not_present() -> None:
    isrc, reads = _blocks(json.dumps(_sample()))

    assert isrc["state"] == reads["state"] == STATE_READ
    assert len(reads["tracks"]) == 3
    for row in isrc["tracks"]:  # type: ignore[attr-defined]  # a list of row dicts
        assert (row["disc_read"], row["disc_read_state"]) == (None, v11.NOT_PRESENT)
    for track in reads["tracks"]:
        assert (track["kept_read_began"], track["kept_read_began_state"]) == (
            None,
            v11.NOT_PRESENT,
        )


def test_adding_the_11_keys_changes_nothing_the_report_already_said() -> None:
    """The relation, not a snapshot: the same rows with and without the keys agree
    on every field that existed before v40, in both blocks."""
    data = _sample()
    before_isrc, before_reads = _blocks(json.dumps(data))
    after_isrc, after_reads = _blocks(
        _as_v11(data, kept_read_began="2026-10-21T09:41:04Z", isrc_disc_read="q frames")
    )
    assert _without(before_isrc["tracks"], _NEW_ISRC_KEYS) == _without(
        after_isrc["tracks"], _NEW_ISRC_KEYS
    )
    assert _without(before_reads["tracks"], _NEW_READS_KEYS) == _without(
        after_reads["tracks"], _NEW_READS_KEYS
    )
    # Non-trivial: the keys did arrive, so equality above is not silence.
    assert {row["disc_read"] for row in after_isrc["tracks"]} == {"q frames"}  # type: ignore[attr-defined]  # rows are dicts


# --- /11 -------------------------------------------------------------------------


@pytest.mark.parametrize("word", v11.ISRC_DISC_READS)
def test_each_proposed_read_word_is_read(word: str) -> None:
    isrc, _reads = _blocks(_as_v11(_sample(), isrc_disc_read=word))
    states = {(r["disc_read"], r["disc_read_state"]) for r in isrc["tracks"]}  # type: ignore[attr-defined]  # rows are dicts
    assert states == {(word, v11.READ)}


def test_the_kept_read_time_is_read_in_utc_from_either_form() -> None:
    for value in ("2026-10-21T09:41:04Z", "2026-10-21T05:41:04-04:00"):
        _isrc, reads = _blocks(_as_v11(_sample(), kept_read_began=value))
        assert {
            (t["kept_read_began"], t["kept_read_began_state"]) for t in reads["tracks"]
        } == {("2026-10-21T09:41:04Z", v11.READ)}


def test_null_is_not_stated_and_an_unknown_value_is_unrecognised_but_kept() -> None:
    _isrc, reads = _blocks(_as_v11(_sample(), kept_read_began=None))
    assert {t["kept_read_began_state"] for t in reads["tracks"]} == {v11.NOT_STATED}

    isrc, reads = _blocks(
        _as_v11(_sample(), isrc_disc_read="raw p-w\x1b", kept_read_began=1729500000)
    )
    row = isrc["tracks"][0]  # type: ignore[index]  # a list of row dicts
    # The ripper's word is shown, screened, never guessed into one of the three.
    assert (row["disc_read"], row["disc_read_state"]) == (  # type: ignore[index]  # row is a dict
        "raw p-w\\x1b",
        v11.UNRECOGNISED,
    )
    track = reads["tracks"][0]
    assert (track["kept_read_began"], track["kept_read_began_state"]) == (
        None,
        v11.UNRECOGNISED,
    )


def test_an_unrecognised_word_is_bounded_and_the_cut_counted() -> None:
    record = v11.parse_row({"isrc_disc_read": "x" * 500})
    assert record.isrc_disc_read_state == v11.UNRECOGNISED
    assert record.isrc_disc_read is not None
    assert record.isrc_disc_read.endswith("… [436 more characters]")


@given(
    st.dictionaries(
        st.sampled_from([v11.KEPT_READ_BEGAN_KEY, v11.ISRC_DISC_READ_KEY, "number"]),
        st.one_of(
            st.none(),
            st.booleans(),
            st.integers(),
            st.floats(),
            st.text(max_size=120),
            st.lists(st.integers(), max_size=3),
        ),
    )
)
def test_parse_row_never_raises_and_states_are_known(row: dict[str, object]) -> None:
    record = v11.parse_row(row)
    assert record.kept_read_began_state in v11.STATES
    assert record.isrc_disc_read_state in v11.STATES
    if record.kept_read_began_state != v11.READ:
        assert record.kept_read_began is None
