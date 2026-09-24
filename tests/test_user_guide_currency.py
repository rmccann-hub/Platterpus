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

import ast
import inspect
import re
from dataclasses import fields
from pathlib import Path

from platterpus.config import Config
from platterpus.help_content import USER_GUIDE
from platterpus.ui import settings_dialog

# User-facing settings → a distinctive phrase that must appear in the guide.
# Matching is case-insensitive; the phrase is what a reader would search for.
# Several template fields share the "file-name templates" bullet, and the two
# read-speed fields share the "Read speed" bullet — that's fine, the point is
# that the *concept* is documented.
_GUIDE_KEYWORDS: dict[str, str] = {
    "output_dir": "Output directory",
    "track_template": "file-name templates",
    "disc_template": "file-name templates",
    "track_template_unknown": "file-name templates",
    "disc_template_unknown": "file-name templates",
    "read_offset": "Read offset (samples)",
    "override_read_offset": "Apply this read offset to rips",
    "auto_launch_picard": "Picard",
    "auto_eject_after_rip": "Eject the disc after a successful rip",
    "notify_on_completion": "desktop notification",
    "library_dir": "Move finished rips to",
    "debug_logging": "Debug logging",
    "update_channel": "Offer beta (pre-release) updates",
    "ripper_channel": "cyanrip update channel",
    "cover_art": "Cover art",
    "save_additional_art": "back cover and booklet",
    "max_retries": "Max retries",
    "force_overread": "Overread",
    "secure_rerip_matches": "Reads that must agree to trust a track",
    "secure_rerip_dynamic": "Verify every track with a second read",
    "rerip_offset_variant": "re-read tracks where only one frame matched",
    "read_speed_mode": "Read speed",
    "read_speed": "Read speed",
    "ctdb_verify_after_rip": "Verify with CTDB",
    "verify_flac_after_rip": "Verify FLAC files",
    "recompress_flac_after_rip": "Re-compress FLACs",
    "write_eac_log_after_rip": "EAC-compatible log",
    "output_format": "Output format",
    "mp3_vbr_quality": "MP3 VBR quality",
    "rip_goal": "Goal",
    # Unattended testing. Documented, not exempted: it is a visible Settings row
    # with a Browse button, and a setting a user can see and cannot look up is
    # exactly the noise this classification exists to prevent.
    "test_script_path": "Test script",
    "test_script_autorun": "Run it automatically when Platterpus starts",
    "test_script_allow_unsafe": "unsafe script verbs",
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
    "integration_declined_version": (
        "internal: the other half of the declined-integration key — the version it "
        "was declined at, so a decline lasts one release rather than forever"
    ),
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


# --- the guide vs the SCREEN, which is the leg that was missing --------------


def _labels_the_dialog_renders() -> set[str]:
    """Every string the Settings dialog puts in front of a user, from source.

    Read with `ast` rather than by constructing the dialog: the strings must be
    right in the file, and building a real `SettingsDialog` would need a
    QApplication and a Config for a question that is purely textual.
    """
    tree = ast.parse(Path(inspect.getfile(settings_dialog)).read_text(encoding="utf-8"))
    shown: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            # form.addRow("Label:", widget)
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "addRow"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                shown.add(node.args[0].value)
            # QCheckBox("text", self) / QPushButton("text", self)
            if (
                isinstance(func, ast.Name)
                and func.id in ("QCheckBox", "QPushButton")
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                shown.add(node.args[0].value)
    return shown


def _normalise(text: str) -> str:
    """Compare meaning, not punctuation: strip Qt mnemonics, case and symbols.

    `&&` is Qt's escape for a literal ampersand and a single `&` marks the
    accelerator, so "Test && Copy" and "Test & Copy" are the same words on
    screen — a comparison that failed on that would be about Qt, not about
    whether the guide is current.
    """
    return re.sub(
        r"[^a-z0-9]+", " ", text.replace("&&", "&").replace("&", "").lower()
    ).strip()


def test_every_option_the_guide_names_exists_on_screen() -> None:
    """The guide's bolded option names must match labels the dialog renders.

    **The leg that was missing, and why the existing tests could not stand in
    for it.** `test_documented_settings_appear_in_the_guide` asserts the guide
    contains a phrase — but the phrase comes from `_GUIDE_KEYWORDS` in this file,
    so the guide is being checked against a fixture *we* maintain rather than
    against the product. A list checked against itself is consistent, not
    verified: both halves move together when someone updates them together, and
    neither notices when the **dialog** moves.

    Measured on 2026-09-22, after a tooltip pass renamed one label: four of the
    eighteen options the guide names by bold no longer existed on screen —
    "Output folder" (the row says *Output directory*), "Max reads to confirm a
    shaky track" (renamed that day), "Read offset override" (two controls, named
    as one), and "Eject after a successful rip" (the box says *Eject the disc
    after…*). Three of the four predated the rename. Every existing test was
    green throughout, because none of them had ever read the dialog.

    A label is an exact string to the person following it — the same reasoning
    the v0.6.52 menu-path change was made under.
    """
    shown = {_normalise(s) for s in _labels_the_dialog_renders() if s.strip()}
    # Non-triviality floor: an empty or tiny set would make every `any()` below
    # fail open the moment the extractor stopped finding anything.
    assert len(shown) >= 20, (
        f"only {len(shown)} labels extracted from the Settings dialog — the "
        "extractor has stopped working, not the dialog"
    )

    section = USER_GUIDE.split("## Settings (Tools → Settings)", 1)[1]
    section = section.split("\n## ", 1)[0]
    named = [
        part
        for bullet in re.findall(r"^- \*\*(.+?)\*\*", section, re.M)
        for part in re.split(r"\*\* and \*\*", bullet)
    ]
    # Same floor on the other side: a split that silently found nothing would
    # make this test pass by examining an empty list.
    assert len(named) >= 15, f"only {len(named)} options parsed out of the guide"

    absent = [
        option
        for option in named
        if not any(
            _normalise(option) == label or _normalise(option) in label
            for label in shown
        )
    ]
    assert not absent, (
        "the User Guide names these options in bold and the Settings dialog "
        f"renders no such label: {absent}. Rename the guide to match the screen "
        "(the screen is what the reader is looking at), or rename the label."
    )
