"""Tests for platterpus.goal_presets (the rip-goal preset bundles)."""

from __future__ import annotations

from dataclasses import fields, replace

import platterpus.ui.settings_dialog
from platterpus.config import Config
from platterpus.goal_presets import (
    GOAL_ARCHIVAL,
    GOAL_CUSTOM,
    GOAL_FAST,
    GOAL_PORTABLE,
    GoalPreset,
    apply_preset,
    detect_goal,
)


def test_default_config_is_fast_verified() -> None:
    # The shipping defaults must equal the Fast-verified preset, so adopting
    # presets changed no behaviour and the default goal is a real preset.
    assert detect_goal(Config()) == GOAL_FAST


def test_apply_archival_sets_the_bundle() -> None:
    out = apply_preset(Config(), GOAL_ARCHIVAL)
    assert out.output_format == "flac"
    assert out.ctdb_verify_after_rip is True
    assert out.recompress_flac_after_rip is True
    assert out.rip_goal == GOAL_ARCHIVAL
    assert detect_goal(out) == GOAL_ARCHIVAL


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
