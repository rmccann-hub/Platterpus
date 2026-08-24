"""Goal presets — anchor the rip settings to user *intent*.

Deep-research lesson (docs/ux-design-principles.md #3): novices shouldn't have to
reason about abstract toggles (CTDB, re-compress, format) before they understand
the consequences. EAC's blunt "accurate results vs higher speed" choice worked
because it anchored everything else to a goal. We do the same with three presets.

A preset is just a *bundle of the existing Config fields* — it sets sane values
for a stated goal; the individual Settings controls stay editable underneath
(progressive disclosure, not a wizard that hides things). Picking a preset is a
convenience, never a new code path: the rip still reads the individual fields.

Pure module (no Qt): the Settings dialog applies a preset to its widgets and
reflects the matching preset back. Default goal == the shipping defaults, so
adopting this changed no behaviour.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from platterpus.config import Config

# Stable keys persisted in Config.rip_goal; "custom" means "doesn't match any
# preset" (the user hand-tuned the individual controls).
GOAL_FAST: str = "fast_verified"
GOAL_ARCHIVAL: str = "archival"
GOAL_PORTABLE: str = "portable"
GOAL_CUSTOM: str = "custom"


@dataclass(frozen=True)
class GoalPreset:
    """The Config fields a goal sets. Other fields are left untouched."""

    output_format: str
    ctdb_verify_after_rip: bool
    verify_flac_after_rip: bool
    recompress_flac_after_rip: bool
    secure_rerip_matches: int
    # False = `-Z` on EVERY track from the first read (EAC-style Test and Copy);
    # True = rip fast, then secure-re-read only the tracks AccurateRip did not
    # confirm. This is the field that makes "Archival Exact" a different rip from
    # "Fast Verified" rather than a different label for the same one.
    secure_rerip_dynamic: bool
    # Re-read tracks whose only AccurateRip match was the +450 offset variant. An
    # offset-variant match confirms a pressing; it does not prove the read is
    # reproducible — real hardware produced a track that offset-variant-matched
    # twice with different audio each time (2026-07-23).
    rerip_offset_variant: bool
    # How read speed is chosen. All shipped goals use the adaptive ladder: fast
    # on a clean disc, careful only when a disc needs it (quality only goes up).
    # A user who picks a fixed speed in Settings drops to the "custom" goal.
    read_speed_mode: str


# The three goals. Verification is the constant across ALL of them — every rip
# verifies the bit-perfect FLAC master with the full suite (AccurateRip always +
# CTDB whole-disc + FLAC-integrity decode) BEFORE any transcode, because the
# maintainer's bar is "verification is paramount for every format" (the FLAC
# master is always kept; MP3/WavPack/WAV are derived from it afterward). The
# presets differ only in OUTPUT and effort, not in how hard they check:
#   * Fast Verified — lossless FLAC, full verification, re-read only what needs it.
#   * Archival Exact — the same checks, but EVERY track is read until two reads
#     agree, and an offset-variant match is not accepted on one read either.
#   * Portable — MP3 derived from the (fully verified) FLAC master.
#
# **Archival Exact used to be byte-identical to Fast Verified** (found 2026-08-24
# by an audit for capabilities that claim more than they deliver). Its one
# differing field was `recompress_flac_after_rip=True`, and
# `CyanripImpl.produces_max_compression_flac()` returns True unconditionally — so
# with cyanrip as the sole backend (KDD-18) the re-compress can never run, and the
# Settings checkbox for it is permanently greyed out with a tooltip saying as
# much. Selecting the goal changed nothing at all while its label promised
# "Smallest Lossless Files".
#
# The difference is now the one an archival goal should actually have: **effort**.
# `secure_rerip_dynamic=False` makes it EAC-style Test and Copy — every track read
# until two reads agree, not just the tracks AccurateRip failed to confirm — and
# `rerip_offset_variant=True` refuses to accept an offset-variant match on a
# single read. Both cost rip time, which is the trade an archival goal exists to
# make, and both are long-shipped behaviours rather than anything new.
#
# `recompress_flac_after_rip=True` stays on this preset deliberately. It is inert
# today and correct in intent: a backend that does not max FLAC compression would
# make it live again, and the JSON report already records
# `recompress_gate = "backend already maxes compression"` honestly.
PRESETS: dict[str, GoalPreset] = {
    GOAL_FAST: GoalPreset(
        output_format="flac",
        ctdb_verify_after_rip=True,
        verify_flac_after_rip=True,
        recompress_flac_after_rip=False,
        secure_rerip_matches=2,
        secure_rerip_dynamic=True,
        rerip_offset_variant=False,
        read_speed_mode="auto_ladder",
    ),
    GOAL_ARCHIVAL: GoalPreset(
        output_format="flac",
        ctdb_verify_after_rip=True,
        verify_flac_after_rip=True,
        recompress_flac_after_rip=True,
        secure_rerip_matches=2,
        secure_rerip_dynamic=False,  # -Z on every track: EAC Test and Copy
        rerip_offset_variant=True,
        read_speed_mode="auto_ladder",
    ),
    GOAL_PORTABLE: GoalPreset(
        output_format="mp3",
        ctdb_verify_after_rip=True,
        verify_flac_after_rip=True,
        recompress_flac_after_rip=False,
        secure_rerip_matches=2,
        secure_rerip_dynamic=True,
        rerip_offset_variant=False,
        read_speed_mode="auto_ladder",
    ),
}

# (key, human label) in display order — the Settings combo reads this. "Custom"
# is appended by the dialog (from `option_labels.CUSTOM_LABEL`, shared with the
# naming-scheme combo); it's not a real preset.
#
# Every label follows the one Settings-option convention documented in
# `option_labels.py` — `Name — Descriptor In Title Case [Qualifier]` — and
# `tests/test_option_labels.py` sweeps these through its checker, so a new
# preset added here cannot quietly introduce a sixth phrasing.
GOAL_LABELS: list[tuple[str, str]] = [
    (
        GOAL_FAST,
        "Fast Verified — Lossless, Fully Verified (AccurateRip + CTDB) [Recommended]",
    ),
    (
        GOAL_ARCHIVAL,
        "Archival Exact — Slower, Every Lossless Track Read Twice",
    ),
    (GOAL_PORTABLE, "Portable — MP3 Derived From a Fully Verified Master"),
]


def apply_preset(config: Config, goal: str) -> Config:
    """Return a copy of ``config`` with ``goal``'s preset fields applied.

    Unknown/``custom`` goals return the config unchanged (nothing to apply).
    """
    preset = PRESETS.get(goal)
    if preset is None:
        return config
    return replace(
        config,
        rip_goal=goal,
        output_format=preset.output_format,
        ctdb_verify_after_rip=preset.ctdb_verify_after_rip,
        verify_flac_after_rip=preset.verify_flac_after_rip,
        recompress_flac_after_rip=preset.recompress_flac_after_rip,
        secure_rerip_matches=preset.secure_rerip_matches,
        secure_rerip_dynamic=preset.secure_rerip_dynamic,
        rerip_offset_variant=preset.rerip_offset_variant,
        read_speed_mode=preset.read_speed_mode,
    )


def detect_goal(config: Config) -> str:
    """Return the preset key whose fields match ``config``, else ``"custom"``.

    Lets the Settings dialog show which goal the current settings correspond to
    (and "Custom" once the user hand-tunes a control away from any preset).
    """
    for key, preset in PRESETS.items():
        if (
            config.output_format == preset.output_format
            and config.ctdb_verify_after_rip == preset.ctdb_verify_after_rip
            and config.verify_flac_after_rip == preset.verify_flac_after_rip
            and config.recompress_flac_after_rip == preset.recompress_flac_after_rip
            and config.secure_rerip_matches == preset.secure_rerip_matches
            and config.secure_rerip_dynamic == preset.secure_rerip_dynamic
            and config.rerip_offset_variant == preset.rerip_offset_variant
            and config.read_speed_mode == preset.read_speed_mode
        ):
            return key
    return GOAL_CUSTOM
