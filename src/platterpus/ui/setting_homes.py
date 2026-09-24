"""Where each user setting is edited: exactly one window, one control.

**Why this exists.** The maintainer, 2026-09-23: *"Flag other duplicate
menu/option/setting items. I think mostly they should be in one place."* An
audit of every window found five settings with two editors:

* the **read offset** and its **Apply** tick-box, in Settings *and* in the
  drive wizard. That pair had already cost a real defect: Settings, opened on
  one offset, wrote it back over the one the wizard saved while it was open;
* the **update channels** for the app and for cyanrip, in Settings, while the
  checks they steer live in Setup & Updates;
* the three **test-script options**, in Settings, while the console that loads
  and runs the script has its own copy of the unsafe-verbs box.

Each now has one home, and this table is the record of it. It is data, not
behaviour: every window builds its own controls, and
``tests/test_setting_homes.py`` builds every window and holds them to the
table. So a setting added tomorrow must say where it lives, a control added to
a second window for a setting homed elsewhere fails, and a value control that
edits no setting must say so in that test's allowlist, with a reason.

**The rule for choosing a home:** a setting lives beside the action it steers.
The read offset is a property of the drive, so it lives with drive
calibration; a channel decides what an update check offers, so it lives with
the check; the startup script is chosen where scripts are loaded and run.
Everything else describes the rip itself and lives in Settings.

Pure data: no Qt, so the Settings dialog, the tests and the guide can all read
it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

#: Tools → Settings…
SETTINGS: Final[str] = "settings"
#: Tools → Setup & Updates… → Set up drive…
DRIVE_SETUP: Final[str] = "drive_setup"
#: Tools → Setup & Updates…
SETUP_CENTER: Final[str] = "setup_center"
#: Tools → Run test script…
SCRIPT_CONSOLE: Final[str] = "script_console"

#: The menu path a person follows to reach each window. Every one is held to a
#: real menu item and button by ``tests/test_help_documents_the_menu.py``'s
#: vocabulary, through the guide text that quotes it.
WINDOW_PATHS: Final[dict[str, str]] = {
    SETTINGS: "Tools → Settings…",
    DRIVE_SETUP: "Tools → Setup & Updates… → Set up drive…",
    SETUP_CENTER: "Tools → Setup & Updates…",
    SCRIPT_CONSOLE: "Tools → Run test script…",
}


@dataclass(frozen=True)
class SettingHome:
    """One setting's home: the window, and the attribute holding its control."""

    window: str
    control: str


SETTING_HOMES: Final[dict[str, SettingHome]] = {
    # --- The rip: Settings --------------------------------------------------
    "rip_goal": SettingHome(SETTINGS, "_goal_combo"),
    "output_dir": SettingHome(SETTINGS, "_output_dir_edit"),
    "library_dir": SettingHome(SETTINGS, "_library_dir_edit"),
    "track_template": SettingHome(SETTINGS, "_track_template_edit"),
    "disc_template": SettingHome(SETTINGS, "_disc_template_edit"),
    "track_template_unknown": SettingHome(SETTINGS, "_track_template_unknown_edit"),
    "disc_template_unknown": SettingHome(SETTINGS, "_disc_template_unknown_edit"),
    "metaflac_path": SettingHome(SETTINGS, "_metaflac_path_edit"),
    "output_format": SettingHome(SETTINGS, "_format_combo"),
    "mp3_vbr_quality": SettingHome(SETTINGS, "_mp3_quality_spin"),
    "auto_launch_picard": SettingHome(SETTINGS, "_auto_picard_check"),
    "auto_eject_after_rip": SettingHome(SETTINGS, "_auto_eject_check"),
    "notify_on_completion": SettingHome(SETTINGS, "_notify_check"),
    "debug_logging": SettingHome(SETTINGS, "_debug_logging_check"),
    "cover_art": SettingHome(SETTINGS, "_cover_art_combo"),
    "save_additional_art": SettingHome(SETTINGS, "_additional_art_check"),
    "max_retries": SettingHome(SETTINGS, "_max_retries_spin"),
    "force_overread": SettingHome(SETTINGS, "_force_overread_check"),
    "secure_rerip_matches": SettingHome(SETTINGS, "_secure_rerip_spin"),
    "rerip_offset_variant": SettingHome(SETTINGS, "_rerip_offset_variant_check"),
    # Shown inverted, as "Verify every track with a second read".
    "secure_rerip_dynamic": SettingHome(SETTINGS, "_verify_every_track_check"),
    "read_speed_mode": SettingHome(SETTINGS, "_read_speed_mode_combo"),
    "read_speed": SettingHome(SETTINGS, "_read_speed_spin"),
    "ctdb_verify_after_rip": SettingHome(SETTINGS, "_ctdb_verify_check"),
    "verify_flac_after_rip": SettingHome(SETTINGS, "_verify_flac_check"),
    "recompress_flac_after_rip": SettingHome(SETTINGS, "_recompress_flac_check"),
    "write_eac_log_after_rip": SettingHome(SETTINGS, "_eac_log_check"),
    # --- The drive: the calibration wizard ----------------------------------
    "read_offset": SettingHome(DRIVE_SETUP, "_offset_spin"),
    "override_read_offset": SettingHome(DRIVE_SETUP, "_apply_offset_check"),
    # --- What the update checks offer: beside the checks --------------------
    "update_channel": SettingHome(SETUP_CENTER, "_app_beta_check"),
    "ripper_channel": SettingHome(SETUP_CENTER, "_ripper_beta_check"),
    # --- Test scripts: where scripts are loaded and run ---------------------
    "test_script_path": SettingHome(SCRIPT_CONSOLE, "_startup_script_edit"),
    "test_script_autorun": SettingHome(SCRIPT_CONSOLE, "_autorun_check"),
    "test_script_allow_unsafe": SettingHome(SCRIPT_CONSOLE, "_unsafe_check"),
}


def fields_homed_in(window: str) -> frozenset[str]:
    """The settings whose one home is ``window``."""
    return frozenset(
        name for name, home in SETTING_HOMES.items() if home.window == window
    )


def home_path(field: str) -> str:
    """The menu path to the window that edits ``field``, or ``""`` if none."""
    home = SETTING_HOMES.get(field)
    return WINDOW_PATHS.get(home.window, "") if home is not None else ""
