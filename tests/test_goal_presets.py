"""Tests for platterpus.goal_presets (the rip-goal preset bundles)."""

from __future__ import annotations

from dataclasses import fields, replace

from hypothesis import given
from hypothesis import strategies as st

import platterpus.ui.settings_dialog
from platterpus.config import Config
from platterpus.goal_presets import (
    GOAL_ARCHIVAL,
    GOAL_CUSTOM,
    GOAL_FAST,
    GOAL_PORTABLE,
    PRESETS,
    GoalPreset,
    apply_preset,
    detect_goal,
    fields_differing,
    nearest_preset,
    turns_on_eac_log,
)
from platterpus.ui.settings_groups import (
    GOAL_FIELD_NAMES,
    GOAL_KEY_TEXT,
    goal_status_text,
)


def test_default_config_is_fast_verified() -> None:
    # The shipping defaults must equal the Fast-verified preset, so adopting
    # presets changed no behaviour and the default goal is a real preset.
    assert detect_goal(Config()) == GOAL_FAST


def test_apply_archival_sets_the_bundle() -> None:
    out = apply_preset(Config(), GOAL_ARCHIVAL)
    assert out.output_format == "flac"
    assert out.ctdb_verify_after_rip is True
    # The field that makes Archival a different rip (every track read twice).
    assert out.secure_rerip_dynamic is False
    assert out.rip_goal == GOAL_ARCHIVAL
    assert detect_goal(out) == GOAL_ARCHIVAL


def test_every_pair_of_goals_differs_in_a_field_the_rip_reads() -> None:
    """Two presets with identical fields would be one goal under two names, and
    `detect_goal` would always report whichever is listed first.

    Asserted after `recompress_flac_after_rip` left the presets (2026-10-07):
    it had been Archival's only difference once before, so its removal is the
    kind of change that can quietly make two goals equal again. They are not:
    Archival differs from Fast Verified in `secure_rerip_dynamic`, and Portable
    from both in `output_format`.
    """
    from itertools import combinations

    from platterpus.goal_presets import PRESETS

    # Floor: three goals means three pairs; fewer and this checks less than it says.
    assert len(PRESETS) >= 3
    pairs = list(combinations(PRESETS.items(), 2))
    assert len(pairs) >= 3
    for (key_a, preset_a), (key_b, preset_b) in pairs:
        differing = [
            f.name
            for f in fields(GoalPreset)
            if getattr(preset_a, f.name) != getattr(preset_b, f.name)
        ]
        assert differing, f"{key_a} and {key_b} set identical fields"
        # And each preset round-trips to itself, not to an earlier twin.
        assert detect_goal(apply_preset(Config(), key_a)) == key_a
        assert detect_goal(apply_preset(Config(), key_b)) == key_b


def test_archival_turns_the_eac_log_on_and_no_goal_turns_it_off() -> None:
    """Archival switches the EAC-layout log on (2026-11-12); the others leave it.

    Starts from `False`, the value every config saved before the default moved
    carries, so the assertion is about the goal and not about the default.
    """
    off = Config(write_eac_log_after_rip=False)
    assert turns_on_eac_log(GOAL_ARCHIVAL) is True
    assert apply_preset(off, GOAL_ARCHIVAL).write_eac_log_after_rip is True
    for goal in (GOAL_FAST, GOAL_PORTABLE):
        assert turns_on_eac_log(goal) is False
        assert apply_preset(off, goal).write_eac_log_after_rip is False
        assert apply_preset(Config(), goal).write_eac_log_after_rip is True


def test_the_eac_log_does_not_decide_which_goal_a_config_is() -> None:
    """The log is an output written about the rip, not a way of reading the disc.

    Were it matched by `detect_goal`, every Archival user whose saved config
    carries the old default (`false`) would be reported as `custom`, with a
    `rip_goal_stored` warning on every rip (`rip_report._stale_rip_goal`).
    """
    for goal in (GOAL_FAST, GOAL_ARCHIVAL, GOAL_PORTABLE):
        applied = apply_preset(Config(), goal)
        assert detect_goal(replace(applied, write_eac_log_after_rip=False)) == goal
        assert detect_goal(replace(applied, write_eac_log_after_rip=True)) == goal
    assert "write_eac_log_after_rip" not in {f.name for f in fields(GoalPreset)}


def test_the_retired_recompress_field_is_not_a_preset_field() -> None:
    """The setting was removed (2026-10-07); a preset must not bring it back."""
    assert "recompress_flac_after_rip" not in {f.name for f in fields(GoalPreset)}


def test_apply_portable_selects_mp3() -> None:
    out = apply_preset(Config(), GOAL_PORTABLE)
    assert out.output_format == "mp3"
    # Every preset now fully verifies the master (incl. CTDB) before deriving.
    assert out.ctdb_verify_after_rip is True
    assert out.verify_flac_after_rip is True
    assert detect_goal(out) == GOAL_PORTABLE


def test_every_preset_fully_verifies_the_master() -> None:
    # Verification is the constant across all presets: AccurateRip is always on
    # (cyanrip), and every preset enables CTDB + FLAC-integrity verify.
    for goal in (GOAL_FAST, GOAL_ARCHIVAL, GOAL_PORTABLE):
        out = apply_preset(Config(), goal)
        assert out.ctdb_verify_after_rip is True
        assert out.verify_flac_after_rip is True


def test_every_preset_uses_the_adaptive_ladder() -> None:
    # All shipped goals default to the adaptive read-speed ladder (fast, careful
    # only when needed) — a fixed speed is a Custom choice.
    for goal in (GOAL_FAST, GOAL_ARCHIVAL, GOAL_PORTABLE):
        assert apply_preset(Config(), goal).read_speed_mode == "auto_ladder"


def test_fixed_read_speed_detects_as_custom() -> None:
    # Choosing a fixed speed (disabling the ladder) matches no preset → Custom.
    cfg = apply_preset(Config(), GOAL_FAST)
    cfg = replace(cfg, read_speed_mode="fixed")
    assert detect_goal(cfg) == GOAL_CUSTOM


def test_hand_tuned_config_detects_as_custom() -> None:
    # Turning verification OFF matches no preset (they all verify) → Custom.
    cfg = Config(
        output_format="flac",
        ctdb_verify_after_rip=False,
    )
    assert detect_goal(cfg) == GOAL_CUSTOM


def test_apply_unknown_goal_is_noop() -> None:
    cfg = Config(ctdb_verify_after_rip=True)
    assert apply_preset(cfg, GOAL_CUSTOM) is cfg  # unchanged
    assert apply_preset(cfg, "nonsense") is cfg


# --- Completeness: the dialog must wire a control for every preset field -----
#
# `GoalPreset` and the Settings dialog hold the same list twice, in different
# languages: the dataclass names the Config fields a preset sets, and
# `SettingsDialog._wire_goal_presets` connects one widget per field so that
# hand-editing any of them flips the goal combo to "Custom". Nothing structural
# keeps them in step, and they have already fallen out of step twice:
#
#   * `verify_flac_after_rip` gained a preset field but no wiring, so editing that
#     checkbox left the combo claiming a preset the config no longer matched (the
#     bug the comment inside `_wire_goal_presets` records);
#   * a dead `_goal_driven_widgets()` accessor listed five of the six and was
#     called from nowhere — a stale roster reading as the authoritative one
#     (removed 2026-07-31).
#
# So this asserts the count rather than trusting the next author to remember. It
# is deliberately structural (AST over the source, no Qt, no QApplication): the
# behavioural per-widget tests live in `test_ui_settings_dialog.py`, and they can
# only ever cover the widgets someone thought to write a case for. This one fails
# for the field nobody thought about.


def _dependent_connect_count() -> int:
    """How many widgets `_wire_goal_presets` connects to `_on_dependent_changed`."""
    import ast
    from pathlib import Path

    source = Path(platterpus.ui.settings_dialog.__file__).read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.FunctionDef) and node.name == "_wire_goal_presets":
            return sum(
                1
                for inner in ast.walk(node)
                if isinstance(inner, ast.Call)
                and isinstance(inner.func, ast.Attribute)
                and inner.func.attr == "connect"
                and any(
                    isinstance(arg, ast.Attribute)
                    and arg.attr == "_on_dependent_changed"
                    for arg in inner.args
                )
            )
    raise AssertionError(
        "SettingsDialog._wire_goal_presets not found — it was renamed or removed, "
        "so this check would have passed by finding nothing. Update the walk."
    )


def test_every_goal_preset_field_has_a_wired_control() -> None:
    """A preset field with no wired widget silently strands the goal combo.

    The combo would keep displaying a preset while the config had drifted off it,
    which is the "surface disagrees with state" class of defect this project keeps
    paying for.
    """
    preset_fields = [f.name for f in fields(GoalPreset)]
    wired = _dependent_connect_count()

    # Floor: if the AST walk found nothing to count, the assertion below would be
    # trivially satisfiable in the wrong direction on the next refactor.
    assert wired >= 2, (
        f"only found {wired} `.connect(self._on_dependent_changed)` calls in "
        "_wire_goal_presets — the walk has gone stale and this check is vacuous."
    )
    assert wired == len(preset_fields), (
        f"GoalPreset sets {len(preset_fields)} fields {preset_fields} but "
        f"_wire_goal_presets wires {wired} controls. Every preset field needs a "
        "control whose changed-signal reaches _on_dependent_changed, or editing "
        "that control leaves the goal combo showing a preset the settings no "
        "longer match. Wire the missing one — do not adjust this count."
    )


# --- Which options differ, and from which preset (TASKS R180, UX review S1) --
#
# Settings' line under the Goal names the options that made it Custom and the
# preset they differ from. These two functions are that sentence's facts.


def test_a_preset_applied_differs_from_itself_in_nothing() -> None:
    # Floor: three goals today; a loop over none would pass having checked none.
    assert len(PRESETS) >= 3
    for goal in PRESETS:
        config = apply_preset(Config(), goal)
        assert fields_differing(config, goal) == [], goal
        assert nearest_preset(config) == goal


def test_fields_differing_names_each_changed_field_in_the_presets_order() -> None:
    config = replace(
        apply_preset(Config(), GOAL_FAST),
        read_speed_mode="fixed",
        output_format="wavpack",
    )
    # The preset's field order (output_format first), not the order of change.
    assert fields_differing(config, GOAL_FAST) == ["output_format", "read_speed_mode"]


def test_custom_and_unknown_goals_differ_in_nothing() -> None:
    """Custom sets nothing, so there is nothing for a config to differ from."""
    assert fields_differing(Config(output_format="wav"), GOAL_CUSTOM) == []
    assert fields_differing(Config(), "no-such-goal") == []


def test_nearest_preset_is_the_one_fewest_fields_away() -> None:
    # MP3 at a fixed speed: one field off Portable, two off Fast verified.
    portable_ish = replace(
        apply_preset(Config(), GOAL_PORTABLE), read_speed_mode="fixed"
    )
    assert nearest_preset(portable_ish) == GOAL_PORTABLE
    # Test and Copy with CTDB off: one field off Archival, two off Fast.
    archival_ish = replace(
        apply_preset(Config(), GOAL_ARCHIVAL), ctdb_verify_after_rip=False
    )
    assert nearest_preset(archival_ish) == GOAL_ARCHIVAL


def test_a_tie_goes_to_the_recommended_preset_listed_first() -> None:
    """WavPack is one field off Fast verified and one off Portable (the format
    each time). A tie must depend on nothing but the config, so it goes to the
    first preset in `PRESETS`, the recommended one."""
    tie = replace(apply_preset(Config(), GOAL_FAST), output_format="wavpack")
    assert len(fields_differing(tie, GOAL_FAST)) == 1
    assert len(fields_differing(tie, GOAL_PORTABLE)) == 1
    assert next(iter(PRESETS)) == GOAL_FAST
    assert nearest_preset(tie) == GOAL_FAST


@given(
    output_format=st.sampled_from(["flac", "wavpack", "mp3", "wav"]),
    ctdb=st.booleans(),
    verify_flac=st.booleans(),
    matches=st.integers(min_value=0, max_value=5),
    dynamic=st.booleans(),
    variant=st.booleans(),
    speed=st.sampled_from(["auto_ladder", "fixed"]),
)
def test_detect_goal_names_a_preset_exactly_when_nothing_differs_from_it(
    output_format: str,
    ctdb: bool,
    verify_flac: bool,
    matches: int,
    dynamic: bool,
    variant: bool,
    speed: str,
) -> None:
    """Two surfaces answer "is this a preset?": `detect_goal` (the combo on
    open, the rip report's goal) and `fields_differing` (the Custom line). They
    must use the same key, or the line could say Custom about a config the
    combo names (`docs/testing.md` §5.al)."""
    config = Config(
        output_format=output_format,
        ctdb_verify_after_rip=ctdb,
        verify_flac_after_rip=verify_flac,
        secure_rerip_matches=matches,
        secure_rerip_dynamic=dynamic,
        rerip_offset_variant=variant,
        read_speed_mode=speed,
    )
    nearest = nearest_preset(config)
    if detect_goal(config) == GOAL_CUSTOM:
        assert fields_differing(config, nearest) != []
    else:
        assert fields_differing(config, nearest) == []
        assert detect_goal(config) == nearest


# --- The line under the Goal, and the names it uses -------------------------


def test_every_preset_field_has_a_name_in_the_custom_line() -> None:
    assert set(GOAL_FIELD_NAMES) == {f.name for f in fields(GoalPreset)}


def test_the_goal_line_explains_the_mark_while_a_preset_is_named() -> None:
    for goal in PRESETS:
        assert goal_status_text(goal, Config()) == GOAL_KEY_TEXT
    assert GOAL_KEY_TEXT == (
        "◆ marks the options a goal sets. Change one and the goal becomes Custom."
    )


def test_the_custom_line_names_what_differs_and_from_which_preset() -> None:
    one = replace(apply_preset(Config(), GOAL_FAST), output_format="wavpack")
    assert goal_status_text(GOAL_CUSTOM, one) == (
        "ⓘ Custom: Output format differs from Fast verified. ◆ marks the options "
        "a goal sets. Change one and the goal becomes Custom."
    )
    three = replace(one, read_speed_mode="fixed", ctdb_verify_after_rip=False)
    assert goal_status_text(GOAL_CUSTOM, three).startswith(
        "ⓘ Custom: Output format, CTDB and Read speed differ from Fast verified."
    )
    # Custom picked by hand over values that still match a preset says so.
    same = apply_preset(Config(), GOAL_PORTABLE)
    assert goal_status_text(GOAL_CUSTOM, same).startswith(
        "ⓘ Custom: every option a goal sets still matches Portable."
    )
