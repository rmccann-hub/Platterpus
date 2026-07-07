"""Tests for the pure Settings/Config input validator (settings_validation).

The validator is the single source of truth for "is this config value usable",
so these tests assert the rules directly — no GUI needed. Covers the happy path,
each error/warning rule, hand-edited out-of-range/bad-enum values, and the
never-raises guarantee (a validator that crashed would take Settings down)."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from platterpus import settings_validation as sv
from platterpus.config import Config


def _fields(issues) -> set[str]:
    return {i.field for i in issues}


def _errors(issues) -> list:
    return sv.errors_only(issues)


# --- Happy path -------------------------------------------------------------


def test_default_config_has_no_errors() -> None:
    """A fresh default Config must validate clean (no errors) — otherwise a
    first-run user couldn't save Settings. (metaflac may warn if not on PATH.)"""
    issues = sv.validate_config(Config())
    assert _errors(issues) == []


def test_valid_config_with_real_dirs_and_metaflac(tmp_path: Path) -> None:
    metaflac = tmp_path / "metaflac"
    metaflac.write_text("#!/bin/sh\n")
    metaflac.chmod(0o755)
    cfg = Config(
        output_dir=str(tmp_path / "out"),
        working_dir=str(tmp_path / "work"),
        metaflac_path=str(metaflac),
    )
    assert sv.validate_config(cfg) == []


# --- Directory rules --------------------------------------------------------


def test_empty_output_dir_is_error() -> None:
    issues = sv.validate_config(Config(output_dir="  "))
    assert any(i.field == "output_dir" and i.is_error() for i in issues)


def test_relative_output_dir_is_error() -> None:
    issues = sv.validate_config(Config(output_dir="rips/here"))
    assert any(
        i.field == "output_dir" and "absolute" in i.message and i.is_error()
        for i in issues
    )


def test_output_dir_with_nul_is_error() -> None:
    issues = sv.validate_config(Config(output_dir="/tmp/a\x00b"))
    assert any(i.field == "output_dir" and i.is_error() for i in issues)


def test_output_dir_that_is_a_file_is_error(tmp_path: Path) -> None:
    a_file = tmp_path / "afile"
    a_file.write_text("x")
    issues = sv.validate_config(Config(output_dir=str(a_file)))
    assert any(i.field == "output_dir" and "not a folder" in i.message for i in issues)


def test_output_dir_under_unwritable_ancestor_is_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If the nearest existing ancestor isn't writable, the folder can't be
    created — that's an error (caught before the rip fails on it)."""
    import os

    real_access = os.access

    def fake_access(path, mode):  # noqa: ANN001
        if str(path) == str(tmp_path) and mode == os.W_OK:
            return False
        return real_access(path, mode)

    monkeypatch.setattr(os, "access", fake_access)
    issues = sv.validate_config(Config(output_dir=str(tmp_path / "cannot" / "make")))
    assert any(
        i.field == "output_dir" and "isn’t writable" in i.message for i in issues
    )


# --- Template rules ---------------------------------------------------------


def test_empty_template_is_error() -> None:
    issues = sv.validate_config(Config(track_template=""))
    assert any(i.field == "track_template" and i.is_error() for i in issues)


def test_absolute_template_is_error() -> None:
    issues = sv.validate_config(Config(track_template="/%A/%d/%t - %n"))
    assert any(
        i.field == "track_template" and "relative" in i.message and i.is_error()
        for i in issues
    )


def test_unknown_token_is_warning_not_error() -> None:
    issues = sv.validate_config(Config(track_template="%A/%d/%q - %n"))
    token_issues = [i for i in issues if i.field == "track_template"]
    assert token_issues, "expected a warning about %q"
    assert all(not i.is_error() for i in token_issues)
    assert any("%q" in i.message for i in token_issues)


def test_template_rendering_to_empty_is_error() -> None:
    # A template of only separators renders to an empty name.
    issues = sv.validate_config(Config(track_template="/"))
    assert any(i.field == "track_template" and i.is_error() for i in issues)


def test_template_double_slash_is_warning() -> None:
    issues = sv.validate_config(Config(track_template="%A//%d/%t - %n"))
    assert any(
        i.field == "track_template"
        and "empty path segment" in i.message
        and not i.is_error()
        for i in issues
    )


# --- Tool-path rules --------------------------------------------------------


def test_metaflac_absolute_missing_is_error() -> None:
    issues = sv.validate_config(Config(metaflac_path="/nowhere/metaflac"))
    assert any(i.field == "metaflac_path" and i.is_error() for i in issues)


def test_metaflac_absolute_nonexecutable_is_error(tmp_path: Path) -> None:
    plain = tmp_path / "metaflac"
    plain.write_text("not exec")
    plain.chmod(0o644)
    issues = sv.validate_config(Config(metaflac_path=str(plain)))
    assert any(
        i.field == "metaflac_path" and "not an executable" in i.message for i in issues
    )


def test_metaflac_empty_is_error() -> None:
    issues = sv.validate_config(Config(metaflac_path=""))
    assert any(i.field == "metaflac_path" and i.is_error() for i in issues)


def test_metaflac_bare_name_defers_to_dependency_subsystem() -> None:
    """A bare command name is accepted as-is — availability is the dependency
    subsystem's job (Critical rule #6), not a scattered PATH check here."""
    issues = sv.validate_config(Config(metaflac_path="metaflac"))
    assert not any(i.field == "metaflac_path" for i in issues)


def test_metaflac_path_with_control_char_is_error() -> None:
    """BUG-6: a tool path is a charset-validated boundary too, but this validator
    used to skip the control-char check the directory validators apply. A NUL —
    and a whitespace-classed C0 separator that str.strip() would eat — must be
    rejected wherever it appears (checked on the RAW value)."""
    issues = sv.validate_config(Config(metaflac_path="meta\x00flac"))
    assert any(
        i.field == "metaflac_path" and "control character" in i.message for i in issues
    )


def test_metaflac_path_with_trailing_c0_separator_is_error() -> None:
    # \x1f is whitespace to str.strip(), so a check on the stripped text would
    # miss a trailing one — the raw-value check catches it.
    issues = sv.validate_config(Config(metaflac_path="metaflac\x1f"))
    assert any(i.field == "metaflac_path" and i.is_error() for i in issues)


# --- Numeric range rules (a hand-edited config can exceed the spinner) ------


@pytest.mark.parametrize(
    "field,value",
    [
        ("read_offset", 99999),
        ("read_offset", -99999),
        ("max_retries", 500),
        ("secure_rerip_matches", 50),
        ("read_speed", 999),
        ("mp3_vbr_quality", 42),
    ],
)
def test_out_of_range_int_is_error(field: str, value: int) -> None:
    issues = sv.validate_config(Config(**{field: value}))
    assert any(i.field == field and i.is_error() for i in issues)


def test_non_int_value_is_error() -> None:
    """A hand-edited TOML could put a string where an int belongs."""
    cfg = Config()
    cfg.max_retries = "five"  # type: ignore[assignment]
    issues = sv.validate_config(cfg)
    assert any(i.field == "max_retries" and i.is_error() for i in issues)


def test_bool_is_not_a_valid_int_field() -> None:
    cfg = Config()
    cfg.read_speed = True  # type: ignore[assignment]
    issues = sv.validate_config(cfg)
    assert any(i.field == "read_speed" and i.is_error() for i in issues)


# --- Enum rules -------------------------------------------------------------


@pytest.mark.parametrize(
    "field,value",
    [
        ("output_format", "ogg"),
        ("cover_art", "sometimes"),
        ("read_speed_mode", "turbo"),
        ("rip_goal", "nonsense"),
    ],
)
def test_bad_enum_is_error(field: str, value: str) -> None:
    issues = sv.validate_config(Config(**{field: value}))
    assert any(i.field == field and i.is_error() for i in issues)


def test_custom_goal_is_valid() -> None:
    from platterpus import goal_presets

    issues = sv.validate_config(Config(rip_goal=goal_presets.GOAL_CUSTOM))
    assert not any(i.field == "rip_goal" for i in issues)


# --- Robustness + logging ---------------------------------------------------


def test_validate_never_raises_on_garbage() -> None:
    """The validator must not crash even on a wildly malformed config."""
    cfg = Config()
    cfg.output_dir = None  # type: ignore[assignment]
    cfg.track_template = 12345  # type: ignore[assignment]
    cfg.metaflac_path = None  # type: ignore[assignment]
    # Should return issues, not raise.
    result = sv.validate_config(cfg)
    assert isinstance(result, list)


# --- Enforcement: every field is covered, and reacts to a bad value ---------

# A deliberately-bad value for EVERY Config field, so the meta-tests can prove
# each one is actually validated (not just listed). Keep in step with Config —
# the completeness test below fails loudly if a field is missing here.
_BAD_VALUES: dict[str, object] = {
    "output_dir": "",  # empty
    "working_dir": "relative/not/absolute",
    "track_template": "",  # empty
    "disc_template": "/leading/slash",  # absolute
    "track_template_unknown": "a/../b",  # path traversal
    "disc_template_unknown": "",  # empty
    "metaflac_path": "/nowhere/metaflac",  # missing executable
    "read_offset": 99999,  # out of range
    "max_retries": 9999,  # out of range
    "secure_rerip_matches": 9999,  # out of range
    "read_speed": 9999,  # out of range
    "mp3_vbr_quality": 42,  # out of range
    "output_format": "ogg",  # bad enum
    "cover_art": "sometimes",  # bad enum
    "read_speed_mode": "turbo",  # bad enum
    "rip_goal": "nonsense",  # bad enum
    "integration_declined_path": "bad\x00path",  # control char
    "schema_version": "six",  # not an int
    "override_read_offset": "yes",  # not a bool
    "auto_launch_picard": "yes",
    "auto_eject_after_rip": "yes",
    "notify_on_completion": "yes",
    "drive_setup_prompted": "yes",
    "host_setup_prompted": "yes",
    "appimage_integration_prompted": "yes",
    "debug_logging": "yes",
    "secure_rerip_dynamic": "yes",
    "ctdb_verify_after_rip": "yes",
    "verify_flac_after_rip": "yes",
    "recompress_flac_after_rip": "yes",
    "write_eac_log_after_rip": "yes",
    "save_additional_art": "yes",
}


def test_validated_field_names_matches_config_exactly() -> None:
    """Every Config field must be declared validated — so a new setting can't be
    added without a validation rule (CLAUDE.md: validate EVERY input)."""
    from dataclasses import fields

    config_fields = {f.name for f in fields(Config)}
    assert sv.validated_field_names() == config_fields


def test_bad_value_map_covers_every_config_field() -> None:
    """The enforcement map below must name every field — otherwise the
    'reacts to a bad value' test silently skips one."""
    from dataclasses import fields

    config_fields = {f.name for f in fields(Config)}
    assert set(_BAD_VALUES) == config_fields


@pytest.mark.parametrize("field", sorted(_BAD_VALUES))
def test_every_field_reacts_to_a_bad_value(field: str) -> None:
    """Corrupting each field in turn must produce an issue for THAT field — proof
    that the validator genuinely checks it, not just lists it."""
    cfg = Config()
    setattr(cfg, field, _BAD_VALUES[field])
    issues = sv.validate_config(cfg)
    assert any(i.field == field for i in issues), f"{field} was not validated"


# --- Security: exploit-shaped inputs are rejected ---------------------------


@pytest.mark.parametrize(
    "template",
    ["../%A/%d/%t - %n", "%A/../../etc/%n", "%A/%d/../../../%n"],
)
def test_path_traversal_in_template_is_error(template: str) -> None:
    """A '..' segment would write outside the output dir — always an error."""
    issues = sv.validate_config(Config(track_template=template))
    assert any(
        i.field == "track_template" and ".." in i.message and i.is_error()
        for i in issues
    )


@pytest.mark.parametrize("bad", ["/tmp/a\x00b", "/tmp/a\tb", "/tmp/a\x1bb"])
def test_control_chars_in_path_are_error(bad: str) -> None:
    issues = sv.validate_config(Config(output_dir=bad))
    assert any(i.field == "output_dir" and i.is_error() for i in issues)


# --- Property-based: the security invariants hold at EVERY position ---------
#
# The examples above pin a few `..`/control-char placements; these prove the
# invariant across the whole input space. A path-traversal or control-char check
# that a refactor accidentally scoped to "only the first segment" or "not at the
# end" would pass the examples yet reopen the hole — hypothesis finds exactly
# that by fuzzing the position. deadline=None: `_validate_dir`/`_validate_template`
# short-circuit before any filesystem probe on these inputs, but CI runners are
# noisy and this is a correctness assertion, not a timing one.

# Path segments that carry no "/" and no control char, so the ONLY thing that
# can trip validation is the ".." we inject — isolating the traversal rule.
_SAFE_SEG = st.text(
    alphabet=st.characters(
        min_codepoint=0x20, max_codepoint=0x7E, blacklist_characters="/"
    ),
    max_size=6,
)


@st.composite
def _template_with_a_dotdot_segment(draw: st.DrawFn) -> str:
    """A relative template whose "/"-split contains a literal ".." segment,
    placed at a hypothesis-chosen position among otherwise-innocuous segments."""
    parts = draw(st.lists(_SAFE_SEG, max_size=5))
    idx = draw(st.integers(min_value=0, max_value=len(parts)))
    parts.insert(idx, "..")
    return "/".join(parts)


@given(template=_template_with_a_dotdot_segment())
@settings(max_examples=200, deadline=None)
def test_dotdot_template_is_always_an_error_property(template: str) -> None:
    # Wherever the ".." sits, the traversal guard must flag track_template as an
    # error — else a crafted/typo'd template writes outside the output directory.
    assert ".." in template.split("/")  # sanity: the injection survived
    issues = sv.validate_config(Config(track_template=template))
    assert any(
        i.field == "track_template" and ".." in i.message and i.is_error()
        for i in issues
    ), f"'..' traversal not rejected for template {template!r}"


# Non-whitespace C0/DEL controls only, so `.strip()` can never quietly remove the
# character before the check runs (\t \n \v \f \r ARE whitespace and would be
# stripped from the ends — those are covered by the middle-of-string examples).
_NON_WS_CONTROLS = [chr(c) for c in [*range(0x00, 0x09), *range(0x0E, 0x20), 0x7F]]
_PRINTABLE = st.text(
    alphabet=st.characters(min_codepoint=0x21, max_codepoint=0x7E), max_size=6
)


@given(ctrl=st.sampled_from(_NON_WS_CONTROLS), prefix=_PRINTABLE, suffix=_PRINTABLE)
@settings(max_examples=200, deadline=None)
def test_control_char_in_output_dir_is_always_an_error_property(
    ctrl: str, prefix: str, suffix: str
) -> None:
    # A control character anywhere in a path (NUL truncates a C string; ESC & co.
    # have no business in a path) must be rejected wherever it lands.
    value = "/tmp/" + prefix + ctrl + suffix
    issues = sv.validate_config(Config(output_dir=value))
    assert any(i.field == "output_dir" and i.is_error() for i in issues), (
        f"control char {ctrl!r} not rejected in {value!r}"
    )


def test_log_issues_writes_errors_and_warnings(caplog) -> None:
    issues = [
        sv.ValidationIssue("output_dir", "bad dir", sv.SEVERITY_ERROR),
        sv.ValidationIssue("metaflac_path", "not on path", sv.SEVERITY_WARNING),
    ]
    with caplog.at_level(logging.INFO):
        sv.log_issues(issues)
    text = caplog.text
    assert "output_dir" in text and "bad dir" in text
    assert "metaflac_path" in text and "not on path" in text
