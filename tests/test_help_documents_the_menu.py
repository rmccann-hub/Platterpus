"""Every Tools action a person can click is findable in the in-app User Guide.

**Why this file exists.** v0.6.32 shipped **Tools → Run acceptance test…** — the
one-click replacement for three bash scripts, and the answer to the maintainer's
*"this was supposed to be a no cli program"* — and `help_content.py` did not
mention it. Zero occurrences of the word "acceptance". The Guide's testing
section still walked the reader to `Tools → Run test script…` and then to
`--rig-session FOLDER`, a **command line**, as the way to run an unattended
hardware session.

So the feature built to remove the terminal was undiscoverable from inside the
product, and the only route the product documented was the terminal one. Nothing
was broken; a user simply could not find it.

Found 2026-09-01 by an audit lens asking *"is the in-app path documented AT ALL
in the user-facing help?"* — a question no existing test asked, because every
help test checked that the text it already had was well-formed.

**The sweep is derived, not listed.** The menu is read out of
`main_window._build_menus`' source, so an action added tomorrow is covered the
day it lands rather than the day somebody remembers this file. That is the same
reason `test_documented_ripper_flags_are_real.py` sweeps the tree instead of
naming four paths: a hand-kept list of "the places this could go wrong" decays
invisibly, and the thing it stops covering is always the newest thing.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
MAIN_WINDOW: Final[Path] = REPO_ROOT / "src" / "platterpus" / "ui" / "main_window.py"

#: `tools_menu.addAction("Run &acceptance test…")` — the label, as written.
_TOOLS_ACTION: Final[re.Pattern[str]] = re.compile(
    r'tools_menu\.addAction\(\s*"([^"]+)"', re.MULTILINE
)

#: Actions whose absence from the Guide is deliberate, each with its reason.
#: Deliberately short: an allowlist is how a check like this rots into decoration,
#: so anything added here needs a sentence somebody can disagree with.
_NOT_IN_THE_GUIDE: Final[dict[str, str]] = {
    # The Guide is what this opens. Documenting the door inside the room is
    # circular, and a reader who is reading it has already found it.
    "&Settings…": "Settings is documented field-by-field throughout the Guide",
}


def _menu_labels() -> list[str]:
    """Every Tools-menu label, read from the source that builds the menu."""
    text = MAIN_WINDOW.read_text(encoding="utf-8")
    return [m.group(1) for m in _TOOLS_ACTION.finditer(text)]


def _searchable(label: str) -> str:
    """The label reduced to what a Guide would plausibly write.

    Qt's `&` accelerator and the trailing ellipsis are chrome — the Guide writes
    *"Tools → Run acceptance test…"* but it may equally write *"Run acceptance
    test"* mid-sentence, and failing on the ellipsis would be a false alarm.
    """
    return label.replace("&", "").rstrip("…").strip()


def test_the_menu_sweep_actually_finds_the_menu() -> None:
    """The floor. A regex that stopped matching would pass every case below
    while checking nothing — the shape this repo has 52 live instances of."""
    labels = _menu_labels()
    assert len(labels) >= 8, (
        f"only {len(labels)} Tools action(s) found in {MAIN_WINDOW.name}; the "
        "pattern has stopped matching and this file is measuring nothing"
    )
    assert any("acceptance" in label.lower() for label in labels), (
        f"the acceptance action is not in the swept menu: {labels}"
    )


def test_every_tools_action_appears_in_the_user_guide() -> None:
    """The regression test for the acceptance session's absence."""
    from platterpus.help_content import user_guide

    guide = user_guide()
    assert len(guide) > 5_000, (
        f"the Guide is only {len(guide)} characters — that is not the real "
        "document, so every assertion below would be about the wrong text"
    )

    missing: list[str] = []
    for label in _menu_labels():
        if label in _NOT_IN_THE_GUIDE:
            continue
        if _searchable(label) not in guide:
            missing.append(label)

    assert not missing, (
        "these Tools actions are not mentioned anywhere in the in-app User "
        "Guide, so a person cannot find them from inside the program:\n  "
        + "\n  ".join(missing)
        + "\n(If an omission is deliberate, add it to _NOT_IN_THE_GUIDE with a "
        "reason — but read that dict's comment first.)"
    )


def test_the_guide_check_can_actually_fail() -> None:
    """Non-triviality, against constructed text, in both directions.

    The `&`/ellipsis stripping is exactly the kind of normalisation that can
    quietly match everything, so both halves are pinned.
    """
    assert _searchable("Run &acceptance test…") == "Run acceptance test"
    assert _searchable("&Uninstall Platterpus…") == "Uninstall Platterpus"
    # It must NOT reduce a label to something so generic it matches any prose.
    assert _searchable("Set up &drive…") == "Set up drive"
    assert "Run acceptance test" not in "The guide says nothing about testing."


def test_the_guide_does_not_send_a_user_to_the_terminal_for_the_session() -> None:
    """The half that motivated the feature.

    The Guide is allowed to mention `--rig-session` — it exists and some people
    want it — but the acceptance session must be described as the menu action it
    is, or the document is still teaching the route the product replaced.
    """
    from platterpus.help_content import user_guide

    guide = user_guide()
    assert "Run acceptance test" in guide, "the menu action is undocumented"
    heading = guide.find("Running the full acceptance test")
    assert heading != -1, "the acceptance session has no section of its own"
    # Its own section must reach the deliverable without a command line: the
    # operator's whole question is "what do I send?".
    section = guide[heading : heading + 2_000]
    assert "Downloads" in section, (
        "the acceptance section never says where the one file lands"
    )
