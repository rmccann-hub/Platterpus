"""Keep the in-app User Guide current with the app's actual settings.

The User Guide (`help_content.USER_GUIDE`, shown at Help → User Guide) is the
one end-user-facing explanation of what every setting does. It drifts silently:
someone adds a Settings control, ships it, and the guide never learns about it —
which is exactly what happened to the doc version-stamp footer (a convention
that was only *trusted* rotted a whole release). So this test makes currency
enforced, not trusted, mirroring `test_doc_version_stamps.py`:

**Every field on `Config` must be classified.** Either it's a user-facing
setting that the guide documents (listed in `_GUIDE_KEYWORDS` with a phrase that
must appear in the guide text), or it's internal/advanced and explicitly exempt
(listed in `_NOT_IN_GUIDE` with the reason). A field in neither set fails the
test — so adding a new setting *forces* a decision: document it in the guide, or
justify leaving it out. There is no way to add a setting and quietly skip the
guide.

When you add a `Config` field:
  - user-facing (appears in the Settings dialog) → add a bullet to
    `help_content.USER_GUIDE` and map the field to a distinctive phrase here;
  - internal state / advanced tool-path → add it to `_NOT_IN_GUIDE` with why.
"""

from __future__ import annotations

from dataclasses import fields

from platterpus.config import Config
from platterpus.help_content import USER_GUIDE

# User-facing settings → a distinctive phrase that must appear in the guide.
# Matching is case-insensitive; the phrase is what a reader would search for.
# Several template fields share the "file-name templates" bullet, and the two
# read-speed fields share the "Read speed" bullet — that's fine, the point is
# that the *concept* is documented.
_GUIDE_KEYWORDS: dict[str, str] = {
    "output_dir": "Output folder",
    "working_dir": "Working directory",
    "track_template": "file-name templates",
    "disc_template": "file-name templates",
    "track_template_unknown": "file-name templates",
    "disc_template_unknown": "file-name templates",
    "read_offset": "Read offset override",
    "override_read_offset": "Read offset override",
    "auto_launch_picard": "Picard",
    "auto_eject_after_rip": "Eject after a successful rip",
    "notify_on_completion": "desktop notification",
    "library_dir": "Move finished rips to",
    "debug_logging": "Debug logging",
    "cover_art": "Cover art",
    "save_additional_art": "back cover and booklet",
    "max_retries": "Max retries",
    "force_overread": "Overread",
    "secure_rerip_matches": "Max reads to confirm a shaky track",
    "secure_rerip_dynamic": "Max reads to confirm a shaky track",
    "read_speed_mode": "Read speed",
    "read_speed": "Read speed",
    "ctdb_verify_after_rip": "Verify with CTDB",
    "verify_flac_after_rip": "Verify FLACs",
    "recompress_flac_after_rip": "Re-compress FLACs",
    "write_eac_log_after_rip": "EAC-compatible log",
    "output_format": "Output format",
    "mp3_vbr_quality": "MP3 VBR quality",
    "rip_goal": "Goal",
}

# Fields deliberately NOT in the end-user guide, each with the reason. These are
# internal one-shot state flags or an advanced tool-path override — not things a
# user sets to shape a rip, so documenting them would only add noise.
_NOT_IN_GUIDE: dict[str, str] = {
    "metaflac_path": "advanced tool-path override, not a rip setting",
    "drive_setup_prompted": "internal one-shot 'have we offered drive setup' flag",
    "host_setup_prompted": "internal one-shot 'have we offered host setup' flag",
    "appimage_integration_prompted": "internal one-shot 'menu integration offered' flag",
    "integration_declined_path": "internal: remembers a declined integration path",
    "schema_version": "internal config-schema version, migration bookkeeping",
}


def _config_field_names() -> set[str]:
    return {f.name for f in fields(Config)}


def test_every_config_field_is_classified() -> None:
    """No setting may exist without being either documented or explicitly exempt.

    This is the forcing function: a new `Config` field that's neither mapped to
    a guide phrase nor exempted trips this test, so the guide can't silently fall
    behind the settings.
    """
    documented = set(_GUIDE_KEYWORDS)
    exempt = set(_NOT_IN_GUIDE)
    all_fields = _config_field_names()

    overlap = documented & exempt
    assert not overlap, f"fields both documented and exempt: {sorted(overlap)}"

    unclassified = all_fields - documented - exempt
    assert not unclassified, (
        "new Config field(s) not classified for the User Guide: "
        f"{sorted(unclassified)} — document each in help_content.USER_GUIDE and "
        "map it in _GUIDE_KEYWORDS, or add it to _NOT_IN_GUIDE with the reason."
    )

    stale = (documented | exempt) - all_fields
    assert not stale, (
        f"classification lists reference removed Config fields: {sorted(stale)} — "
        "drop them from _GUIDE_KEYWORDS / _NOT_IN_GUIDE."
    )


def test_documented_settings_appear_in_the_guide() -> None:
    """Each user-facing setting's phrase must actually be present in the guide."""
    guide = USER_GUIDE.casefold()
    missing = {
        field: phrase
        for field, phrase in _GUIDE_KEYWORDS.items()
        if phrase.casefold() not in guide
    }
    assert not missing, (
        "User Guide is missing a bullet for these settings (phrase not found): "
        f"{missing} — add or fix the phrasing in help_content.USER_GUIDE."
    )
