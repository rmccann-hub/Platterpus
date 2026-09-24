"""Which settings are the USER'S, and writing back only what they changed.

**Why a module of its own.** Three places need the same two answers, and each got
one of them wrong or nearly did on 2026-09-23:

* the Settings dialog, whose OK wrote back every value it had merely DISPLAYED,
  and so reverted a read offset the drive wizard saved while it was open;
* the acceptance run, whose first settings-restore put `host_setup_prompted`
  back to False, so the first-run setup offer would have reappeared after every
  run;
* the rip report and the acceptance bundle, which must record every setting a
  rip ran under — derived from the dataclass, so a setting added tomorrow is
  recorded tomorrow rather than whenever somebody remembers the list.

"The user's settings" is every :class:`~platterpus.config.Config` field except
:data:`~platterpus.config.APP_STATE_FIELDS`, the app's own bookkeeping. Pure and
Qt-free, so all of it is tested without a display.
"""

from __future__ import annotations

import dataclasses
import json
import logging
from collections.abc import Mapping

from platterpus.config import APP_STATE_FIELDS, Config

log: logging.Logger = logging.getLogger(__name__)


def user_setting_names() -> tuple[str, ...]:
    """Every field of :class:`Config` a user sets, in declaration order."""
    return tuple(
        f.name for f in dataclasses.fields(Config) if f.name not in APP_STATE_FIELDS
    )


def user_settings(config: object) -> dict[str, object]:
    """``{field: value}`` for every user setting in ``config``. Never raises.

    Duck-typed (``getattr``) so a partial or stand-in config yields what it has:
    a field it lacks is simply absent, never invented.
    """
    return {
        name: getattr(config, name)
        for name in user_setting_names()
        if hasattr(config, name)
    }


def with_values(config: Config, values: Mapping[str, object]) -> Config:
    """A copy of ``config`` with ``values`` written in. ``config`` is untouched.

    For a mapping built at run time — a dialog's widgets, one control's field —
    which ``dataclasses.replace(config, **values)`` cannot type-check, because
    the checker cannot tell which field each value is for. A name that is not a
    field is refused rather than silently added as a stray attribute, which a
    typo in a control's wiring would otherwise do.
    """
    known = {f.name for f in dataclasses.fields(Config)}
    unknown = sorted(set(values) - known)
    if unknown:
        raise ValueError(f"not Config fields: {unknown}")
    copy = dataclasses.replace(config)
    for name, value in values.items():
        setattr(copy, name, value)
    return copy


def apply_user_edits(current: Config, opened: Config, edited: Config) -> Config:
    """``current`` with only the fields the user changed in the dialog applied.

    **Why not just ``edited``.** Settings is modal, but the application keeps
    running underneath it, and the window's config is a live object that other
    code writes to. The dialog's widgets are loaded once, when it opens. So
    ``edited`` — the whole config read back off the widgets — carries every value
    the dialog merely DISPLAYED, stale or not, and writing it back reverts
    whatever changed in the meantime.

    Reproduced 2026-09-23, not reasoned about: with Settings open on a read offset
    of 667, the drive wizard (then reachable from a Re-detect… button in this very
    dialog) saved the detected value 6, and pressing OK saved 667 over it — the
    save sequence was ``[6, 667]``. The next disc would have ripped at the wrong
    offset with a clean-looking log, which `CLAUDE.md` names as the reason a
    gesture must never change a calibration value.

    So a field is written only when the widget's value differs from what the
    widget was loaded with. What the user touched wins; everything else stays as
    the application currently has it. Pure, so it is tested without a display.
    """
    changes = {
        field.name: getattr(edited, field.name)
        for field in dataclasses.fields(Config)
        if getattr(edited, field.name) != getattr(opened, field.name)
    }
    if changes:
        log.info("settings: applying user edits to %s", sorted(changes))
    return dataclasses.replace(current, **changes)


@dataclasses.dataclass(frozen=True)
class SettingWrite:
    """What happened when one control saved one setting.

    ``applied`` says whether the value is now in effect; ``message`` is the
    sentence to show beside the control, empty when there is nothing to say. The
    two are separate because they can disagree: a value the validator refused is
    neither applied nor saved, while a value applied for this session and then
    not written to disk is in effect and still needs a sentence.
    """

    applied: bool
    message: str = ""


def changed_settings(before: object, after: object) -> list[str]:
    """The user settings whose value differs between two configs, in field order."""
    old, new = user_settings(before), user_settings(after)
    return [name for name in old if name in new and old[name] != new[name]]


def settings_record_text(before: object | None, run_ended_with: object) -> str:
    """The acceptance bundle's ``SETTINGS.json``: what the run ran under. Pure.

    Two snapshots, because the bundle's copy of ``config.toml`` cannot answer the
    question: it is read after the user's own settings are restored, so it
    describes the user, not the run. ``before_run`` is ``null`` when no snapshot
    was taken — stated, never filled in with the run's values.
    """
    record: dict[str, object] = {
        "record": "platterpus acceptance settings",
        "before_run": user_settings(before) if before is not None else None,
        "run_ended_with": user_settings(run_ended_with),
        "changed_by_run": (
            changed_settings(before, run_ended_with) if before is not None else None
        ),
    }
    return json.dumps(record, indent=2, sort_keys=False, default=str) + "\n"
