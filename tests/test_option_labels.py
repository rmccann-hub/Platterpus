"""The Settings-option naming convention, and the sweep that enforces it.

Two halves, and the second is the one that matters over time:

1. Unit tests for :func:`platterpus.option_labels.check_option_label` — including
   the near-misses, because a checker that only ever sees good input is a
   checker nobody has tested.
2. A **sweep over every item of every combo in the real dialog**, with floors.
   ``CLAUDE.md``'s recurring lesson is *enforce a rule across the codebase, not
   at the place it was learned*: a table of "the labels we know about" would go
   stale the first time somebody adds a sixth dropdown, and would go stale
   invisibly, because a list is only ever wrong by omission.

The sweep is also **revert-proof by construction** rather than by assertion: it
reads the labels out of the constructed widgets, so reverting any label to its
old wording fails it. `test_the_old_labels_would_all_fail_this_check` pins that
explicitly with the real pre-rename strings, so the check cannot be satisfied by
a checker that accepts everything.
"""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QComboBox

from platterpus import goal_presets, naming, option_labels
from platterpus.config import Config
from platterpus.ui.settings_dialog import SettingsDialog

# --- The checker itself ---------------------------------------------------


def test_conforming_labels_pass() -> None:
    for label in (
        "FLAC — lossless archival master (recommended)",
        "WavPack (.wv) — lossless, keeps tags and cover art",
        "MP3 — lossy, best-quality VBR, keeps tags and cover art",
        "WAV — raw PCM, basic tags only, no cover art",
        "Fast verified — lossless, checked against AccurateRip and CTDB (recommended)",
        "Artist / Year - Album / 01 - Title — chronological, foobar2000 style",
        "Artist / Album (Year) / 01 - Title — Plex and Jellyfin style",
        "Custom — hand-tuned below",
        "Don't fetch — no cover art at all",
        "Fixed speed — always the speed set below (advanced)",
    ):
        assert option_labels.check_option_label(label) is None, label


def test_a_hyphen_separator_is_named_as_the_problem() -> None:
    # The maintainer's own example used a hyphen ("Flack - Lossless Archival
    # Master"), so this is the likeliest way a new label goes wrong. The message
    # has to say *use an em dash*, not merely "no separator found".
    problem = option_labels.check_option_label("FLAC - lossless archival master")
    assert problem is not None
    assert "em dash" in problem


def test_no_separator_at_all_fails() -> None:
    assert option_labels.check_option_label("Embed in FLAC") is not None


def test_two_separators_fail() -> None:
    problem = option_labels.check_option_label("A — B — C")
    assert problem is not None
    assert "exactly one" in problem


def test_a_title_case_descriptor_fails_and_names_the_words() -> None:
    """W1 of the 2026-11-17 UX review: Title Case inside a list item."""
    problem = option_labels.check_option_label("FLAC — Lossless Archival Master")
    assert problem is not None
    assert "sentence case" in problem
    # Naming the offending words is the point: a bare "not sentence case" over a
    # 60-character label leaves the reader hunting.
    assert "Lossless" in problem and "Archival" in problem and "Master" in problem


def test_a_title_case_name_fails() -> None:
    problem = option_labels.check_option_label("Fast Verified — lossless")
    assert problem is not None and "Verified" in problem
    assert option_labels.check_option_label("fast verified — lossless") is not None


def test_a_path_shape_name_keeps_its_tag_fields() -> None:
    """``Artist / Album / 01 - Title`` names tag fields, not prose."""
    assert option_labels.check_option_label("Artist / Album — simple") is None
    assert option_labels.check_option_label("Artist / Album — Simple") is not None


def test_acronyms_product_names_and_listed_proper_names_keep_their_capitals() -> None:
    for label in (
        "MP3 — best-quality VBR",
        "A — checked against AccurateRip and CTDB",
        "A — Plex and Jellyfin style",
        "A — 24× speed",
    ):
        assert option_labels.check_option_label(label) is None, label
    # A capitalised word that is none of those is Title Case.
    assert option_labels.check_option_label("A — Kodi style") is not None


def test_a_hyphenated_compound_is_checked_on_both_halves() -> None:
    # Checking only the first letter would pass "best-Quality" — the exact hole
    # a naive implementation leaves.
    assert option_labels.check_option_label("MP3 — best-quality VBR") is None
    problem = option_labels.check_option_label("MP3 — best-Quality VBR")
    assert problem is not None
    assert "best-Quality" in problem


def test_words_inside_parentheses_are_still_checked() -> None:
    # A blanket "skip anything with a bracket" would let this through, which is
    # a check satisfied by the wrong thing.
    assert (
        option_labels.check_option_label("A — fully verified (Fully Checked)")
        is not None
    )
    assert option_labels.check_option_label("A — fully verified (AccurateRip)") is None


def test_an_unknown_qualifier_fails_with_the_allowed_set() -> None:
    problem = option_labels.check_option_label("FLAC — lossless master (best)")
    assert problem is not None
    assert "recommended" in problem  # lists what IS allowed


def test_the_old_bracketed_qualifier_is_named_as_the_problem() -> None:
    problem = option_labels.check_option_label("FLAC — lossless master [Recommended]")
    assert problem is not None
    assert "(recommended)" in problem


def test_a_qualifier_alone_is_not_a_descriptor() -> None:
    assert option_labels.check_option_label("FLAC — (recommended)") is not None


def test_double_space_fails() -> None:
    # The pre-rename naming labels used two spaces before "(recommended)".
    problem = option_labels.check_option_label("Artist / Album  — simple")
    assert problem is not None
    assert "double space" in problem


def test_whitespace_and_empty_fail() -> None:
    assert option_labels.check_option_label(" FLAC — master ") is not None
    assert option_labels.check_option_label("") is not None


def test_placeholders_are_recognised_and_are_not_conforming_labels() -> None:
    # The drive picker's stand-ins. Exempt by name, not by omission — and the
    # exemption must NOT be implemented as "the checker accepts them", or every
    # parenthesised bad label would pass too.
    for placeholder in ("(no drives found)", "(error: permission denied)"):
        assert option_labels.is_placeholder(placeholder)
        assert option_labels.check_option_label(placeholder) is not None
    assert not option_labels.is_placeholder("FLAC — lossless archival master")


def test_the_checker_never_raises_on_odd_input() -> None:
    for odd in ("—", " — ", "[]", "A — [", "A — )", "—", "A — 24× Speed"):
        option_labels.check_option_label(odd)  # must not raise


# --- The pure label tables ------------------------------------------------


def test_every_goal_label_conforms() -> None:
    assert len(goal_presets.GOAL_LABELS) >= 3  # floor: cannot pass by finding none
    for key, label in goal_presets.GOAL_LABELS:
        assert option_labels.check_option_label(label) is None, f"{key}: {label}"


def test_every_naming_preset_label_conforms() -> None:
    assert len(naming.PRESETS) >= 5  # floor
    for preset in naming.PRESETS:
        problem = option_labels.check_option_label(preset.label)
        assert problem is None, f"{preset.key}: {problem}"


def test_the_custom_row_is_one_shared_constant() -> None:
    # It was a hardcoded literal in the dialog AND a constant in naming.py.
    assert naming.CUSTOM_LABEL == option_labels.CUSTOM_LABEL
    assert option_labels.check_option_label(option_labels.CUSTOM_LABEL) is None


# --- The sweep over the real dialog --------------------------------------


def _combos(dialog: SettingsDialog) -> list[tuple[str, QComboBox]]:
    """Every QComboBox the dialog owns, named by its attribute for the message.

    Derived from the constructed widget tree rather than from a list of the ones
    we know about, so a dropdown added later is covered without anyone editing
    this file.
    """
    found: list[tuple[str, QComboBox]] = []
    for name, value in vars(dialog).items():
        if isinstance(value, QComboBox):
            found.append((name, value))
    return sorted(found)


def test_every_option_in_every_settings_combo_conforms(qapp: QApplication) -> None:
    dialog = SettingsDialog(Config())
    combos = _combos(dialog)
    # Floors, so "found nothing" cannot read as "all conformed". Five combos
    # today (goal, naming, format, cover art, read-speed mode); the counts may
    # grow, never shrink below these.
    assert len(combos) >= 5, (
        f"only found {len(combos)} combos: {[n for n, _ in combos]}"
    )
    checked = 0
    for name, combo in combos:
        assert combo.count() >= 2, f"{name} offers fewer than two options"
        for i in range(combo.count()):
            label = combo.itemText(i)
            problem = option_labels.check_option_label(label)
            assert problem is None, f"{name}[{i}] {label!r} {problem}"
            checked += 1
    assert checked >= 18, f"only checked {checked} option labels"


def test_the_old_labels_would_all_fail_this_check(qapp: QApplication) -> None:
    """Revert-proof, stated rather than assumed.

    These are the verbatim Title Case strings that shipped until 2026-11-17
    (UX review W1). If a future change loosened the checker until it accepted
    anything, the sweep above would still pass — this is what stops that, and it
    is why the strings are pasted rather than derived. (The labels from before
    the Title Case rename were sentence case already, and several of them
    conform again; they are not listed.)
    """
    old = [
        "FLAC — Lossless Archival Master [Recommended]",
        "WavPack (.wv) — Lossless, Keeps Tags and Cover Art",
        "MP3 — Lossy, Best-Quality VBR, Keeps Tags and Cover Art",
        "WAV — Raw PCM, Basic Tags Only, No Cover Art",
        "Don't Fetch — No Cover Art at All",
        "Embed in FLAC — Art Inside Each Track",
        "Save as File — Art Beside the Tracks",
        "Embed and Save File — Both [Recommended]",
        "Adaptive Ladder — Fast, Slower Only if a Disc Needs It [Recommended]",
        "Fixed Speed — Always the Speed Set Below [Advanced]",
        "Fast Verified — Lossless, Fully Verified (AccurateRip + CTDB) [Recommended]",
        "Archival Exact — Slower, Every Lossless Track Read Twice",
        "Portable — MP3 Derived From a Fully Verified Master",
        "Custom — Hand-Tuned Below",
        "Artist / Album / 01 - Title — Simple, No Year Clutter [Recommended]",
        "Artist / Album / 01 Title — Same Layout, No Dash",
        "Artist / Album (Year) / 01 - Title — Plex and Jellyfin Style",
        "Artist / Year - Album / 01 - Title — Chronological, foobar2000 Style",
        "Artist / Album / 01 - Track Artist - Title — Compilations, Various Artists",
    ]
    assert len(old) >= 19  # floor: the whole Title Case set, not a sample
    for label in old:
        assert option_labels.check_option_label(label) is not None, (
            f"{label!r} is a Title Case label and must not pass the checker"
        )


def test_relabelling_did_not_change_what_any_option_means(qapp: QApplication) -> None:
    """The rename is cosmetic: every combo must still carry the same item DATA.

    A relabel that quietly dropped or reordered a value would change behaviour
    while looking like a copy edit — and the data, not the text, is what reaches
    the config file.
    """
    dialog = SettingsDialog(Config())
    assert [
        dialog._format_combo.itemData(i) for i in range(dialog._format_combo.count())
    ] == ["flac", "wavpack", "mp3", "wav"]
    assert [
        dialog._cover_art_combo.itemData(i)
        for i in range(dialog._cover_art_combo.count())
    ] == ["", "embed", "file", "complete"]
    assert [
        dialog._read_speed_mode_combo.itemData(i)
        for i in range(dialog._read_speed_mode_combo.count())
    ] == ["auto_ladder", "fixed"]
    assert [
        dialog._goal_combo.itemData(i) for i in range(dialog._goal_combo.count())
    ] == [
        goal_presets.GOAL_FAST,
        goal_presets.GOAL_ARCHIVAL,
        goal_presets.GOAL_PORTABLE,
        goal_presets.GOAL_CUSTOM,
    ]
    assert [
        dialog._naming_combo.itemData(i) for i in range(dialog._naming_combo.count())
    ] == [p.key for p in naming.PRESETS] + [None]
