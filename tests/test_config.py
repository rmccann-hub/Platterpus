"""Tests for platterpus.config.

Monkeypatches the CONFIG_PATH and CONFIG_DIR module attributes so each
test gets an isolated tmp directory and the user's real ~/.config is
never touched.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from platterpus import config as config_module
from platterpus.config import SCHEMA_VERSION


def _redirect_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the config module at tmp_path. Returns the redirected file path."""
    config_file = tmp_path / "config.toml"
    monkeypatch.setattr(config_module, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(config_module, "CONFIG_PATH", config_file)
    return config_file


def test_config_has_no_whipper_era_fields() -> None:
    """Regression guard for the whipper removal (KDD-18): the config dataclass
    must not carry the retired whipper-only fields. If one creeps back, some
    dead code is reading it — fail here, loudly."""
    import dataclasses

    field_names = {f.name for f in dataclasses.fields(config_module.Config)}
    retired = {
        "ripper_backend",
        "whipper_path",
        "continue_on_cdr",
        "force_overread",
        "keep_going",
    }
    leaked = field_names & retired
    assert not leaked, f"retired whipper-era config field(s) reappeared: {leaked}"


def test_load_ignores_unknown_legacy_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An upgrading user's config.toml still has the old whipper keys; load()
    must drop them silently rather than choke (mirrors the real 0.4.0→0.4.1
    upgrade, where the log showed 'unknown config keys ignored: …')."""
    config_file = _redirect_config(tmp_path, monkeypatch)
    config_file.write_text(
        'schema_version = 1\nread_offset = 667\nripper_backend = "whipper"\n'
        'whipper_path = "/x"\nkeep_going = true\n',
        encoding="utf-8",
    )

    cfg = config_module.load()  # must not raise

    assert cfg.read_offset == 667  # the still-valid key survived
    assert not hasattr(cfg, "ripper_backend")


def test_first_load_creates_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When the file is missing, load() writes defaults and returns them."""
    config_file = _redirect_config(tmp_path, monkeypatch)
    assert not config_file.exists()

    cfg = config_module.load()

    assert config_file.exists()
    assert cfg.schema_version == SCHEMA_VERSION
    assert cfg.auto_launch_picard is False
    assert cfg.read_offset == 0


def test_save_then_load_roundtrip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Modifying and saving persists; the next load sees the change."""
    _redirect_config(tmp_path, monkeypatch)

    cfg = config_module.load()
    cfg.read_offset = 667
    cfg.auto_launch_picard = True
    config_module.save(cfg)

    reloaded = config_module.load()
    assert reloaded.read_offset == 667
    assert reloaded.auto_launch_picard is True


def test_auto_eject_defaults_off_and_round_trips(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _redirect_config(tmp_path, monkeypatch)

    cfg = config_module.load()
    assert cfg.auto_eject_after_rip is False  # default

    cfg.auto_eject_after_rip = True
    config_module.save(cfg)
    assert config_module.load().auto_eject_after_rip is True


def test_debug_logging_defaults_off_and_round_trips(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _redirect_config(tmp_path, monkeypatch)

    cfg = config_module.load()
    assert cfg.debug_logging is False  # default off

    cfg.debug_logging = True
    config_module.save(cfg)
    assert config_module.load().debug_logging is True


def test_ctdb_verify_defaults_on_and_round_trips(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _redirect_config(tmp_path, monkeypatch)

    cfg = config_module.load()
    # On by default (0.4.5): full verification of the master for every format.
    assert cfg.ctdb_verify_after_rip is True

    cfg.ctdb_verify_after_rip = False
    config_module.save(cfg)
    assert config_module.load().ctdb_verify_after_rip is False


def test_verify_flac_defaults_on_and_round_trips(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _redirect_config(tmp_path, monkeypatch)

    cfg = config_module.load()
    assert cfg.verify_flac_after_rip is True  # default ON (archival integrity)

    cfg.verify_flac_after_rip = False
    config_module.save(cfg)
    assert config_module.load().verify_flac_after_rip is False


def test_recompress_flac_defaults_off_and_round_trips(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _redirect_config(tmp_path, monkeypatch)

    cfg = config_module.load()
    assert cfg.recompress_flac_after_rip is False  # opt-in (costs CPU/time)

    cfg.recompress_flac_after_rip = True
    config_module.save(cfg)
    assert config_module.load().recompress_flac_after_rip is True


def test_output_format_defaults_flac_and_round_trips(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _redirect_config(tmp_path, monkeypatch)

    cfg = config_module.load()
    # Default stays FLAC — the lossless archival master (Critical Rule #4);
    # WavPack/MP3/WAV are derived from it when selected (KDD-22).
    assert cfg.output_format == "flac"
    assert cfg.mp3_vbr_quality == 0

    cfg.output_format = "mp3"
    cfg.mp3_vbr_quality = 2
    config_module.save(cfg)
    reloaded = config_module.load()
    assert reloaded.output_format == "mp3"
    assert reloaded.mp3_vbr_quality == 2


def test_save_is_atomic_no_tmp_left_behind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The temp file used during atomic write must not survive a successful save."""
    config_file = _redirect_config(tmp_path, monkeypatch)

    cfg = config_module.load()
    config_module.save(cfg)

    tmp_file = config_file.with_suffix(".tmp")
    assert not tmp_file.exists(), "temp file leaked after successful save"


def test_unknown_keys_are_dropped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A newer file with extra keys loads without crashing in an older binary."""
    config_file = _redirect_config(tmp_path, monkeypatch)
    # Hand-write a config with one known key and one future key.
    config_file.write_text(
        'schema_version = 1\nread_offset = 100\nfuture_key_not_in_v1 = "value"\n'
    )

    cfg = config_module.load()

    assert cfg.read_offset == 100
    # The unknown key didn't sneak onto the dataclass.
    assert not hasattr(cfg, "future_key_not_in_v1")


def test_v1_untouched_templates_ride_chain_to_current_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A v1 config still holding the v1 default templates rides the whole
    migration chain (v1→v2→v3) to the current clean Artist/Album/## - Title
    default on load."""
    config_file = _redirect_config(tmp_path, monkeypatch)
    config_file.write_text(
        "schema_version = 1\n"
        'track_template = "%A - %d/%t. %a - %n"\n'
        'disc_template = "%A - %d/%A - %d"\n'
    )

    cfg = config_module.load()

    assert cfg.schema_version == SCHEMA_VERSION
    assert cfg.track_template == "%A/%d/%t - %n"
    assert cfg.disc_template == "%A/%d/%d"
    # The unknown-disc templates fill in from defaults (absent in v1).
    assert cfg.track_template_unknown.startswith("Unknown Artist/Unknown Album/")


def test_v2_cluttered_default_upgrades_to_clean_v3(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A v2 config still on the cluttered default template (repeated
    album/artist + trailing date) auto-upgrades to the clean v3 default."""
    config_file = _redirect_config(tmp_path, monkeypatch)
    config_file.write_text(
        "schema_version = 2\n"
        'track_template = "%A/%d/%t - %n - %d - %A - %y"\n'
        'disc_template = "%A/%d/%d"\n'
    )

    cfg = config_module.load()

    assert cfg.schema_version == SCHEMA_VERSION
    assert cfg.track_template == "%A/%d/%t - %n"
    assert cfg.disc_template == "%A/%d/%d"


def test_migration_preserves_custom_templates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A user who hand-edited their template keeps it through every upgrade."""
    config_file = _redirect_config(tmp_path, monkeypatch)
    config_file.write_text('schema_version = 1\ntrack_template = "my/custom/%t %n"\n')

    cfg = config_module.load()

    assert cfg.schema_version == SCHEMA_VERSION
    assert cfg.track_template == "my/custom/%t %n"


def test_v3_year_preset_upgrades_to_year_only_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A v3 config on a year-in-folder preset (which used %y = the full date)
    auto-upgrades to the year-only %Y form introduced in v4."""
    config_file = _redirect_config(tmp_path, monkeypatch)
    config_file.write_text(
        "schema_version = 3\n"
        'track_template = "%A/%d (%y)/%t - %n"\n'
        'disc_template = "%A/%d (%y)/%d"\n'
    )

    cfg = config_module.load()

    assert cfg.schema_version == SCHEMA_VERSION
    assert cfg.track_template == "%A/%d (%Y)/%t - %n"
    assert cfg.disc_template == "%A/%d (%Y)/%d"


def test_v3_year_preset_migration_leaves_custom_templates_alone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The v3→v4 year-token upgrade only touches an exact old preset template —
    a hand-edited one that happens to contain %y is left untouched."""
    config_file = _redirect_config(tmp_path, monkeypatch)
    config_file.write_text('schema_version = 3\ntrack_template = "%A - %d - %y/%t"\n')

    cfg = config_module.load()

    assert cfg.schema_version == SCHEMA_VERSION
    assert cfg.track_template == "%A - %d - %y/%t"


def test_read_speed_defaults_and_round_trip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _redirect_config(tmp_path, monkeypatch)

    cfg = config_module.load()
    # Default = the adaptive ladder, starting at the drive's max (0).
    assert cfg.read_speed_mode == "auto_ladder"
    assert cfg.read_speed == 0

    cfg.read_speed_mode = "fixed"
    cfg.read_speed = 8
    config_module.save(cfg)
    reloaded = config_module.load()
    assert reloaded.read_speed_mode == "fixed"
    assert reloaded.read_speed == 8


def test_v4_config_upgrades_to_v5_with_read_speed_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A v4 config (no read-speed fields) loads at the current schema with the
    adaptive-ladder defaults filled in — no value transform needed."""
    config_file = _redirect_config(tmp_path, monkeypatch)
    config_file.write_text("schema_version = 4\n")

    cfg = config_module.load()

    assert cfg.schema_version == SCHEMA_VERSION
    assert cfg.read_speed_mode == "auto_ladder"
    assert cfg.read_speed == 0


def test_secure_rerip_dynamic_defaults_on_and_round_trips(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _redirect_config(tmp_path, monkeypatch)

    cfg = config_module.load()
    # Dynamic is the behaviour now, not an opt-in → default True.
    assert cfg.secure_rerip_dynamic is True

    # A power user can force always-secure by flipping it in TOML; it round-trips.
    cfg.secure_rerip_dynamic = False
    config_module.save(cfg)
    assert config_module.load().secure_rerip_dynamic is False


def test_v5_config_upgrades_with_dynamic_default_and_bumps_inherited_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A v5 config (no secure_rerip_dynamic) loads at the current schema with the
    dynamic default (True) filled in. An inherited secure_rerip_matches of 0 — the
    0.4.8 default that left the 0.4.9 dynamic re-rip silently OFF for upgraders —
    is bumped ONCE to 2 by the v6→v7 step so the feature actually engages."""
    config_file = _redirect_config(tmp_path, monkeypatch)
    config_file.write_text("schema_version = 5\nsecure_rerip_matches = 0\n")

    cfg = config_module.load()

    assert cfg.schema_version == SCHEMA_VERSION
    assert cfg.secure_rerip_dynamic is True
    assert cfg.secure_rerip_matches == 2  # inherited 0 → bumped to the new default


def test_v6_zero_bumps_to_two_but_nonzero_is_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The v6→v7 bump only rescues an inherited 0. A user who deliberately set a
    non-zero ceiling keeps exactly that — the migration never lowers or clobbers a
    real choice."""
    config_file = _redirect_config(tmp_path, monkeypatch)
    config_file.write_text("schema_version = 6\nsecure_rerip_matches = 5\n")

    cfg = config_module.load()

    assert cfg.schema_version == SCHEMA_VERSION
    assert cfg.secure_rerip_matches == 5  # deliberate value untouched


def test_v7_zero_is_left_alone_the_bump_is_one_time(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The bump is a one-time correction, not a permanent floor: once a config is
    at v7, a saved 0 means the user chose it after the migration ran, so it stays
    0 (dynamic re-rip off). Otherwise the setting could never be turned off."""
    config_file = _redirect_config(tmp_path, monkeypatch)
    config_file.write_text("schema_version = 7\nsecure_rerip_matches = 0\n")

    cfg = config_module.load()

    assert cfg.schema_version == SCHEMA_VERSION
    assert cfg.secure_rerip_matches == 0  # already-v7 → deliberate 0 respected


def test_load_never_raises_on_corrupt_toml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A corrupt config.toml must not crash startup — load() runs before the
    QApplication/excepthook exist. It backs the bad file up and returns defaults."""
    config_file = _redirect_config(tmp_path, monkeypatch)
    config_file.write_text("this is not = valid toml [[[\n")

    cfg = config_module.load()  # must not raise

    assert cfg == config_module.Config()  # defaults
    assert config_file.with_suffix(".bad").exists()  # bad file preserved for the user


def test_load_never_raises_on_non_numeric_schema_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A hand-broken schema_version (non-numeric) is tolerated, not a crash."""
    config_file = _redirect_config(tmp_path, monkeypatch)
    config_file.write_text('schema_version = "garbage"\n')

    cfg = config_module.load()  # must not raise (int("garbage") would)

    assert cfg == config_module.Config()
    assert config_file.with_suffix(".bad").exists()


def test_load_resets_a_traversal_template_from_a_hand_edited_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: a hand-edited config bypasses the Settings dialog's validators,
    so load() must itself reject an exploit-shaped value. A `..` traversal track
    template must be reset to the default before it can reach the ripper."""
    config_file = _redirect_config(tmp_path, monkeypatch)
    config_file.write_text(
        f'schema_version = {SCHEMA_VERSION}\ntrack_template = "../../../etc/%t"\n'
    )

    cfg = config_module.load()

    # The traversal template was reset to the safe default; other fields intact.
    assert cfg.track_template == config_module.Config().track_template
    assert ".." not in cfg.track_template


def test_fresh_config_defaults_enable_dynamic_secure_rerip() -> None:
    """The shipped default must make the dynamic secure re-rip actually run —
    the worker gates it on secure_rerip_matches > 0 AND secure_rerip_dynamic, so
    a fresh install with -Z at 0 would leave the headline feature inert."""
    cfg = config_module.Config()
    assert cfg.secure_rerip_dynamic is True
    assert cfg.secure_rerip_matches == 2  # > 0 → dynamic path is active
