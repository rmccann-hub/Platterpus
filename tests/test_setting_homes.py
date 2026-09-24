"""Every user setting has exactly one home, and no window edits one it does not own.

**Why this exists.** The maintainer, 2026-09-23: *"Flag other duplicate
menu/option/setting items. I think mostly they should be in one place."* The
audit found seven settings with two editors — the read offset and its Apply
tick-box (Settings and the drive wizard), both update channels (Settings, while
the checks they steer live in Setup & Updates), and the three test-script
options (Settings and the console). Two editors of one value is not a cosmetic
problem here: Settings, opened on one offset, once wrote it back over the one
the wizard had just saved.

`ui/setting_homes.py` records the one home of each setting. This file builds
every window that edits settings and holds them to it, in both directions:

* **every** user setting has a home, and its control exists in that window and
  is a value control (the forward direction);
* **every** value control in every such window either IS the home control of a
  setting homed in that window, or is named in :data:`_NOT_A_SETTING` with a
  reason (the converse). A second editor for a setting homed elsewhere is
  therefore an unaccounted control, and fails.

The allowlist is a ratchet: an entry needs a sentence somebody can disagree
with, because a list of excuses enforces nothing.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Final

import pytest
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QCheckBox,
    QComboBox,
    QLineEdit,
    QRadioButton,
    QWidget,
)

from platterpus.config import Config
from platterpus.ui import setting_homes
from platterpus.ui.setting_homes import (
    DRIVE_SETUP,
    SCRIPT_CONSOLE,
    SETTING_HOMES,
    SETTINGS,
    SETUP_CENTER,
    WINDOW_PATHS,
    fields_homed_in,
    home_path,
)
from platterpus.user_settings import SettingWrite, user_setting_names

#: The widget kinds that hold a value a user sets.
_VALUE_CONTROLS: Final[tuple[type, ...]] = (
    QCheckBox,
    QRadioButton,
    QAbstractSpinBox,
    QComboBox,
    QLineEdit,
)

#: Value controls that edit no setting, per window, each with its reason.
_NOT_A_SETTING: Final[dict[str, dict[str, str]]] = {
    SETTINGS: {
        "_naming_combo": (
            "a shortcut that fills the two template boxes; it stores nothing of "
            "its own, so whatever it writes there is the setting"
        ),
    },
    DRIVE_SETUP: {},
    SETUP_CENTER: {},
    SCRIPT_CONSOLE: {},
}


def _windows(
    qapp: QApplication,
) -> dict[str, Callable[[], QWidget]]:
    """One way to build each window that edits settings."""
    from test_ui_drive_setup_dialog import _StubBackend

    from platterpus.ui.dialogs.script_console import ScriptConsoleDialog
    from platterpus.ui.dialogs.setup_center import SetupCenterDialog
    from platterpus.ui.drive_setup_dialog import DriveSetupDialog
    from platterpus.ui.settings_dialog import SettingsDialog

    holder = QWidget()
    return {
        SETTINGS: lambda: SettingsDialog(Config()),
        DRIVE_SETUP: lambda: DriveSetupDialog(_StubBackend(), "/dev/sr0"),
        SETUP_CENTER: lambda: SetupCenterDialog(
            None,
            app_version="0.0.0",
            ripper_pin="0000000",
            ripper_version="0.0.0",
            approved_by_round=0,
            dependency_report=None,
            actions={},
            config=Config(),
            save_setting=lambda _f, _v: SettingWrite(True),
        ),
        SCRIPT_CONSOLE: lambda: ScriptConsoleDialog(holder),
    }


def _named_controls(window: QWidget) -> dict[int, str]:
    """``{id(control): attribute name}`` for the window's own value controls."""
    return {
        id(value): name
        for name, value in vars(window).items()
        if isinstance(value, _VALUE_CONTROLS)
    }


def _inner(widget: QWidget, window: QWidget) -> bool:
    """A control that is part of another control (a spin box's own line edit)."""
    parent = widget.parentWidget()
    while parent is not None and parent is not window:
        if isinstance(parent, QAbstractSpinBox | QComboBox):
            return True
        parent = parent.parentWidget()
    return False


# --- The table --------------------------------------------------------------


def test_every_user_setting_has_exactly_one_home() -> None:
    assert set(SETTING_HOMES) == set(user_setting_names()), (
        "settings with no home, or homes for things that are not settings: "
        f"{sorted(set(SETTING_HOMES) ^ set(user_setting_names()))}"
    )
    assert {home.window for home in SETTING_HOMES.values()} <= set(WINDOW_PATHS)


def test_the_window_sweep_has_the_four_homes_to_sweep() -> None:
    """The floor under the two parametrized sweeps below (they build each window).

    An emptied `WINDOW_PATHS` would generate no cases, and "no window has a second
    editor" would pass having opened none.
    """
    assert set(WINDOW_PATHS) == {SETTINGS, DRIVE_SETUP, SETUP_CENTER, SCRIPT_CONSOLE}


def test_each_window_is_home_to_something_and_the_sets_partition() -> None:
    """Non-triviality: four homes, each non-empty, together covering it all."""
    parts = [fields_homed_in(window) for window in WINDOW_PATHS]
    assert all(parts), "a window in WINDOW_PATHS is home to nothing"
    assert sum(len(p) for p in parts) == len(SETTING_HOMES)


def test_the_moved_settings_live_beside_what_they_steer() -> None:
    """The placements this change made, pinned so a revert fails by name."""
    assert fields_homed_in(DRIVE_SETUP) == {"read_offset", "override_read_offset"}
    assert fields_homed_in(SETUP_CENTER) == {"update_channel", "ripper_channel"}
    assert fields_homed_in(SCRIPT_CONSOLE) == {
        "test_script_path",
        "test_script_autorun",
        "test_script_allow_unsafe",
    }
    assert home_path("read_offset") == "Tools → Setup & Updates… → Set up drive…"
    assert home_path("no_such_setting") == ""


# --- The windows ------------------------------------------------------------


@pytest.mark.parametrize("window_key", sorted(WINDOW_PATHS))
def test_each_home_control_exists_in_its_window(
    qapp: QApplication, window_key: str
) -> None:
    window = _windows(qapp)[window_key]()
    for field in sorted(fields_homed_in(window_key)):
        control = getattr(window, SETTING_HOMES[field].control, None)
        assert isinstance(control, _VALUE_CONTROLS), (
            f"{field}: {window_key} has no value control called "
            f"{SETTING_HOMES[field].control!r}"
        )


@pytest.mark.parametrize("window_key", sorted(WINDOW_PATHS))
def test_no_window_carries_a_value_control_the_table_cannot_account_for(
    qapp: QApplication, window_key: str
) -> None:
    """The converse: a second editor for a setting homed elsewhere fails here.

    Every value control a user can reach in the window is found through Qt's own
    child list, not through the attributes, so a control built and never stored
    is found too.
    """
    window = _windows(qapp)[window_key]()
    named = _named_controls(window)
    owned = {SETTING_HOMES[f].control for f in fields_homed_in(window_key)}
    excused = set(_NOT_A_SETTING[window_key])
    found = [
        child
        for kind in _VALUE_CONTROLS
        for child in window.findChildren(kind)
        if not _inner(child, window)
    ]
    assert found, f"{window_key}: the sweep found no value controls at all"
    unaccounted: list[str] = []
    for child in found:
        name = named.get(id(child))
        if name is None:
            label = getattr(child, "text", lambda: "")() or child.accessibleName()
            unaccounted.append(f"an unnamed {type(child).__name__} {label!r}")
        elif name not in owned and name not in excused:
            unaccounted.append(name)
    assert not unaccounted, (
        f"{window_key} has value controls no setting is homed on: "
        f"{sorted(set(unaccounted))}. If one edits a setting, home it in "
        "`ui/setting_homes.py`; if it edits none, add it to _NOT_A_SETTING with "
        "the reason."
    )


def test_the_allowlist_names_only_controls_that_exist(qapp: QApplication) -> None:
    """A stale excuse is how an allowlist rots into decoration."""
    windows = _windows(qapp)
    for window_key, excused in _NOT_A_SETTING.items():
        window = windows[window_key]()
        for name in excused:
            assert isinstance(getattr(window, name, None), _VALUE_CONTROLS), (
                window_key,
                name,
            )


def test_the_converse_can_fail(qapp: QApplication) -> None:
    """Prove the sweep is not vacuous: a second offset editor in Settings fails.

    Built the way the old code built it — a spin box attribute on the dialog —
    and checked with the same rule the sweep applies.
    """
    from PySide6.QtWidgets import QSpinBox

    window = _windows(qapp)[SETTINGS]()
    window._second_offset_editor = QSpinBox(window)  # type: ignore[attr-defined]  # the defect under test
    named = _named_controls(window)
    owned = {SETTING_HOMES[f].control for f in fields_homed_in(SETTINGS)}
    strays = [
        name
        for name in named.values()
        if name not in owned and name not in _NOT_A_SETTING[SETTINGS]
    ]
    assert strays == ["_second_offset_editor"]


def test_every_documented_setting_has_a_tooltip_in_its_home(
    qapp: QApplication,
) -> None:
    """Every guide-documented setting carries its guide text on hover too.

    Moved here from the Settings tests on 2026-09-24: a setting's tooltip lives
    on its ONE control, wherever that is, so the sweep has to follow the table.
    """
    from test_user_guide_currency import _GUIDE_KEYWORDS

    documented = set(_GUIDE_KEYWORDS)
    assert documented <= set(SETTING_HOMES), sorted(documented - set(SETTING_HOMES))
    windows = _windows(qapp)
    built = {key: build() for key, build in windows.items()}
    for field in sorted(documented):
        home = SETTING_HOMES[field]
        tip = getattr(built[home.window], home.control).toolTip()
        assert tip and tip.strip(), f"{field} has no tooltip on its home control"


def test_every_window_path_is_one_the_menu_resolves() -> None:
    """The paths the table hands to Settings' read-only line are real ones."""
    from test_help_documents_the_menu import _dead_paths, _menu_model

    model = _menu_model()
    for path in WINDOW_PATHS.values():
        assert _dead_paths(path, model) == [], path


def test_the_table_imports_no_qt() -> None:
    """Pure data, so the guide, the validator and the tests can all read it."""
    import ast
    from pathlib import Path

    tree = ast.parse(Path(setting_homes.__file__).read_text(encoding="utf-8"))
    imported = {
        node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not any(name.startswith("PySide6") for name in imported)


def test_every_home_tick_box_says_what_both_states_do(qapp: QApplication) -> None:
    """The Settings wording rule, applied wherever a setting now lives.

    Maintainer, 2026-09-21: *"for true false tooltips it should give the
    result"*. `tests/test_settings_tooltips_say_what_happens.py` holds Settings
    to it by reading that dialog's source; moving a setting out of Settings must
    not move it out of the rule, so this follows the home table instead. Words,
    not substrings: "only" and "one" contain "on" and would pass anything.
    """
    built = {key: build() for key, build in _windows(qapp).items()}
    offenders: list[str] = []
    checked = 0
    for field, home in sorted(SETTING_HOMES.items()):
        if home.window == SETTINGS:
            continue  # the source-reading sweep's population
        control = getattr(built[home.window], home.control)
        if not isinstance(control, QCheckBox):
            continue
        checked += 1
        tip = control.toolTip().lower()
        if not (re.search(r"\bon\b", tip) and re.search(r"\boff\b", tip)):
            offenders.append(field)
    assert checked >= 4, f"only {checked} moved tick-box(es) examined"
    assert not offenders, (
        f"these tick-boxes do not say what BOTH states do: {offenders}"
    )
