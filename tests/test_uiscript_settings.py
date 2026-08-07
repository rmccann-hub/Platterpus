"""The script surface's Settings and track-selection verbs.

These are the verbs that make the vocabulary *more* precise than a person driving
the GUI: exact per-field values, exact per-track selections, repeatable. So the
things worth pinning are the ones a careless implementation gets wrong in a way
that still looks green — a set that silently does nothing, a validator result read
as the wrong sense, a track selection that quietly drops a number.

Pure-function level: `_coerce_setting`, `_validation_error_for` and
`_parse_track_spec` carry the whole decision, so they are tested without Qt.
"""

from __future__ import annotations

import dataclasses

import pytest

from platterpus.config import Config
from platterpus.settings_validation import SEVERITY_WARNING, validate_config
from platterpus.uiscript.runner import (
    _coerce_setting,
    _parse_track_spec,
    _validation_error_for,
)

# --- Coercion ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("on", True),
        ("ON", True),
        ("true", True),
        ("yes", True),
        ("1", True),
        ("off", False),
        ("false", False),
        ("no", False),
        ("0", False),
    ],
)
def test_booleans_accept_the_words_a_person_would_write(text: str, expected: bool):
    value, problem = _coerce_setting(False, text)
    assert problem == ""
    assert value is expected


def test_a_boolean_field_is_never_parsed_as_a_number() -> None:
    """`bool` is an `int` subclass, so order of checks decides correctness here.

    An `isinstance(current, int)` test placed first would match a boolean field and
    turn `set debug_logging 0` into the integer `0` — equal to `False` today, and a
    different thing the moment anything compares identity or writes it back to TOML
    (`false` versus `0`). The bug would be invisible in every assertion that used
    `==`.
    """
    value, problem = _coerce_setting(False, "0")
    assert problem == ""
    assert value is False
    assert isinstance(value, bool)


def test_a_nonsense_boolean_is_refused_with_the_accepted_words() -> None:
    value, problem = _coerce_setting(True, "maybe")
    assert value is None
    assert "on" in problem and "off" in problem


def test_integers_and_strings_round_trip() -> None:
    assert _coerce_setting(0, "3") == (3, "")
    assert _coerce_setting("flac", "wavpack") == ("wavpack", "")
    value, problem = _coerce_setting(0, "three")
    assert value is None and "whole number" in problem


# --- Validation gating ------------------------------------------------------


def test_an_invalid_value_is_refused_by_the_real_validator() -> None:
    """The scripted path must not be able to persist what the dialog would refuse."""
    bad = dataclasses.replace(Config(), output_format="mp4")
    assert _validation_error_for(bad, "output_format")


def test_a_valid_value_passes() -> None:
    good = dataclasses.replace(Config(), output_format="wavpack")
    assert _validation_error_for(good, "output_format") == ""


def test_a_warning_does_not_block_a_set() -> None:
    """**Regression test: `is_error` is a method, and it has to be called.**

    Reading it as an attribute (`getattr(issue, "is_error", True)`) yields a *bound
    method*, which is always truthy — so every warning-severity issue would have been
    reported as a rejection and the verb would refuse values the Settings dialog
    happily accepts. The first version of `_validation_error_for` did exactly that.

    This test finds a real warning-severity issue from the live validator rather than
    constructing one, so it cannot pass against a validator whose severities have
    moved. If no field ever produces a warning again, it skips loudly instead of
    passing quietly — a test that silently stops testing is the thing it is here to
    prevent.
    """
    # A template with an unknown %code is a WARNING: legal, probably not intended.
    config = dataclasses.replace(Config(), track_template="%A/%q-unknown/%t")
    issues = validate_config(config)
    warnings = [i for i in issues if i.severity == SEVERITY_WARNING]
    if not warnings:
        pytest.skip("no warning-severity issue available to test the distinction")
    field = warnings[0].field
    assert not any(i.is_error() for i in issues if i.field == field), (
        "fixture picked a field that also has an error — pick a warning-only one"
    )
    assert _validation_error_for(config, field) == "", (
        f"a {SEVERITY_WARNING}-severity issue on {field!r} blocked the set; only a "
        f"hard error may. A script must not be stricter than the dialog."
    )


def test_a_validator_that_explodes_blocks_rather_than_silently_setting(monkeypatch):
    """A validator fault must fail closed. Silently applying is the wrong direction."""
    import platterpus.settings_validation as sv

    def boom(_config: object) -> list[object]:
        raise RuntimeError("validator exploded")

    monkeypatch.setattr(sv, "validate_config", boom)
    assert _validation_error_for(Config(), "output_format")


# --- Track selection --------------------------------------------------------


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        ("1", [1]),
        ("1,3", [1, 3]),
        ("5-7", [5, 6, 7]),
        ("1,3,5-7", [1, 3, 5, 6, 7]),
        ("7-5,1", None),  # backwards range → refused
        ("3-3", [3]),
        (" 1 , 2 ", [1, 2]),
        ("2,2,2", [2]),  # de-duplicated
    ],
)
def test_track_specs_parse_the_way_a_person_writes_them(spec, expected) -> None:
    numbers, problem = _parse_track_spec(spec)
    if expected is None:
        assert problem, f"{spec!r} should have been refused"
    else:
        assert problem == "", problem
        assert numbers == expected


def test_an_absurd_range_is_refused_rather_than_materialised() -> None:
    """`1-999999` is a typo, not a selection. Refusing beats building the list.

    A CD holds 99 tracks, so any range past the cap is a pasted mistake — and
    expanding it would hand the GUI thread a list to build and the track table a
    selection to apply, for a disc that cannot have them.
    """
    numbers, problem = _parse_track_spec("1-999999")
    assert numbers == []
    assert "spans more than" in problem


@pytest.mark.parametrize("spec", ["", ",", "abc", "1-x", "x-1", ",,,"])
def test_a_malformed_spec_is_refused_not_silently_empty(spec: str) -> None:
    """An empty selection and a refused one must not render the same.

    A spec that parsed to nothing would select no tracks, and "rip zero tracks"
    reports success just as loudly as a real rip.
    """
    numbers, problem = _parse_track_spec(spec)
    assert numbers == []
    assert problem, f"{spec!r} produced no numbers AND no complaint"
