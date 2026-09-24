"""`user_settings`: which settings are the user's, and nothing is left out.

The list is DERIVED from the dataclass, so a setting added tomorrow is recorded
tomorrow. These tests hold that derivation to the two things that make it safe:
it covers every field that is not the app's own bookkeeping, and it never
invents a field a stand-in config does not have.
"""

from __future__ import annotations

import dataclasses
from types import SimpleNamespace

from platterpus.config import APP_STATE_FIELDS, Config
from platterpus.user_settings import user_setting_names, user_settings


def test_every_field_is_either_the_users_or_the_apps() -> None:
    every = {f.name for f in dataclasses.fields(Config)}
    names = set(user_setting_names())
    assert names | APP_STATE_FIELDS == every
    assert not names & APP_STATE_FIELDS
    # Non-triviality: a derivation that returned nothing would pass the union
    # above only if every field were app state, which is not the config we ship.
    assert len(names) >= 30, names


def test_the_snapshot_carries_every_user_setting_and_no_app_state() -> None:
    config = dataclasses.replace(Config(), read_offset=667, host_setup_prompted=True)
    snap = user_settings(config)
    assert snap["read_offset"] == 667
    assert set(snap) == set(user_setting_names())
    assert "host_setup_prompted" not in snap


def test_a_stand_in_yields_what_it_has_and_invents_nothing() -> None:
    assert user_settings(SimpleNamespace(read_offset=6)) == {"read_offset": 6}


def test_the_settings_record_names_what_the_run_changed() -> None:
    import json

    from platterpus.user_settings import settings_record_text

    before = Config()
    during = dataclasses.replace(before, output_format="mp3", host_setup_prompted=True)
    record = json.loads(settings_record_text(before, during))
    assert record["changed_by_run"] == ["output_format"]
    assert record["run_ended_with"]["output_format"] == "mp3"


def test_no_snapshot_is_stated_not_filled_in() -> None:
    import json

    from platterpus.user_settings import settings_record_text

    record = json.loads(settings_record_text(None, Config()))
    assert record["before_run"] is None and record["changed_by_run"] is None
