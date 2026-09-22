"""Every Settings option must say what it DOES, not what it is called.

Maintainer directive, 2026-09-21: *"for true false tooltips it should give the
result, for others it should say what different arguments or inputs mean and what
the expected result is."*

**Why this is a test and not a style note.** The audit that produced this rule
found a label and tooltip that were not merely vague but *wrong*: the secure
re-read spin box was called "Max reads to confirm a shaky track" and its tooltip
said "the number you pick is the ceiling", when the flag is cyanrip's `-Z` /
`--repeat-rips` — *"rip tracks until checksums match N times"* — an AGREEMENT
count, whose ceiling is a different setting (`-r`, "Max retries") sitting directly
above it on the same screen. One wrong fact had reached four places: the label,
the tooltip, a code comment, and our own `docs/dependency-contracts.md` gloss,
which was where it started. Nothing could have caught that except reading them —
but a *floor* can stop the next option shipping with no stated outcome at all.

**What this test can and cannot prove.** It cannot check that a tooltip is TRUE;
only a person reading it against the code can. It checks the weaker, mechanical
property that the text describes outcomes: a boolean names both of its states, a
value control names what its values mean. A tooltip can satisfy this and still
be wrong, which is why the accuracy audit is recorded separately rather than
claimed here.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

SETTINGS = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "platterpus"
    / "ui"
    / "settings_dialog.py"
)

#: Controls that legitimately describe no outcome, with the reason. A disabled
#: control has no states to choose between, so demanding "ON:/OFF:" of it would
#: force a sentence that lies. This list may shrink; adding to it needs a reason
#: as concrete as this one.
_NO_OUTCOME_NEEDED: dict[str, str] = {
    "recompress_flac_after_rip": (
        "permanently disabled — cyanrip already encodes FLAC at maximum "
        "compression, so the control cannot change anything and its tooltip "
        "explains that instead of describing two states"
    ),
}


def _tooltips() -> dict[str, str]:
    """Widget attribute -> tooltip text, read with `ast` rather than a regex.

    The first version of this extraction used a regex over double-quoted spans and
    silently mangled every tooltip containing an inner quote — it reported the
    overread tooltip as corrupt when the tooltip was fine and the reader was not.
    A number that does not reproduce is a statement about the method first.
    """
    src = SETTINGS.read_text(encoding="utf-8")
    out: dict[str, str] = {}
    for node in ast.walk(ast.parse(src)):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "setToolTip"
            and isinstance(node.func.value, ast.Attribute)
            and node.args
        ):
            arg = node.args[0]
            try:
                out[node.func.value.attr] = ast.literal_eval(arg)
            except (ValueError, SyntaxError):
                # An f-string: keep the literal parts, which is where the prose is.
                out[node.func.value.attr] = " ".join(
                    v.value
                    for v in ast.walk(arg)
                    if isinstance(v, ast.Constant) and isinstance(v.value, str)
                )
    return out


def _rendered_labels() -> set[str]:
    """Every string the dialog puts on screen: form row labels and box captions.

    Deliberately the same shape as the sweep in
    `tests/test_user_guide_currency.py` — both answer *"is this the name of a
    real control?"*, and that is one question, so neither invents its own idea
    of what a label is.
    """
    shown: set[str] = set()
    for node in ast.walk(ast.parse(SETTINGS.read_text(encoding="utf-8"))):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        first = node.args[0]
        if not (isinstance(first, ast.Constant) and isinstance(first.value, str)):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "addRow":
            shown.add(first.value)
        if isinstance(func, ast.Name) and func.id in ("QCheckBox", "QPushButton"):
            shown.add(first.value)
    return shown


def _saved(kind: str) -> list[tuple[str, str]]:
    """(config key, widget) for every control whose value is persisted."""
    src = SETTINGS.read_text(encoding="utf-8")
    return re.findall(rf"^\s+(\w+)=self\.(_\w+)\.{kind}\(\)", src, re.MULTILINE)


def test_the_sweep_actually_finds_the_settings() -> None:
    """The floor. A regex that stopped matching would pass every case below."""
    assert len(_tooltips()) >= 25, f"only {len(_tooltips())} tooltip(s) found"
    assert len(_saved("isChecked")) >= 12, "the boolean sweep found almost nothing"


def test_every_boolean_setting_names_both_outcomes() -> None:
    """A checkbox has two states and the tooltip must say what each one does."""
    tips = _tooltips()
    offenders: list[str] = []
    for key, widget in _saved("isChecked"):
        if key in _NO_OUTCOME_NEEDED:
            continue
        text = tips.get(widget, "").lower()
        if not ("on" in text and "off" in text):
            offenders.append(key)
    assert not offenders, (
        "these boolean settings do not say what BOTH states do, so a user can only "
        f"learn one half of the choice from the tooltip: {offenders}"
    )


@pytest.mark.parametrize("kind", ["value", "currentData"])
def test_every_value_setting_explains_its_values(kind: str) -> None:
    """A spin box or combo must say what the inputs mean, not just name the field.

    Checked as "the tooltip mentions at least one concrete value or option", which
    is a floor rather than a proof — `0`, `Max`, a named mode. A tooltip reading
    only "The read speed." names the field and teaches nothing.
    """
    tips = _tooltips()
    offenders: list[str] = []
    for key, widget in _saved(kind):
        text = tips.get(widget, "")
        if not text:
            offenders.append(f"{key} (no tooltip)")
            continue
        names_a_value = bool(re.search(r"\b\d+\b|'[^']+'|\"[^\"]+\"|\bMax\b", text))
        if not names_a_value:
            offenders.append(f"{key} (names no concrete value)")
    assert not offenders, (
        "these value settings do not say what their inputs mean or what to expect "
        f"from them: {offenders}"
    )


# --- cross-references between controls --------------------------------------


def test_a_tooltip_may_only_name_a_control_that_exists() -> None:
    """A tooltip pointing at another control must point at a real one.

    Found 2026-09-22: renaming *"Max reads to confirm a shaky track"* to *"Reads
    that must agree to trust a track"* left the Test & Copy tooltip saying
    *Needs “Max reads” at 2 or more* — a control the user cannot find. Same
    defect as the User Guide naming five options that are not on screen, one
    surface further in: the dialog disagreeing with itself.

    **Scope, stated rather than assumed.** This checks phrases in TYPOGRAPHIC
    quotes (“…”) only. Straight-quoted phrases in these tooltips are mostly not
    control names at all — `flac --test`, 'none set', 'unapproved', 'Embed in
    FLAC' — so sweeping them would need a long allowlist, and a list of excuses
    enforces nothing. The typographic pair is used for exactly this purpose and
    a narrow rule that holds beats a wide one that is mostly exceptions. If you
    are cross-referencing another control, use “…” and this test covers you.
    """
    tooltips = _tooltips()
    labels = " \u0001 ".join(_rendered_labels()).lower()
    references = {
        phrase for tip in tooltips.values() for phrase in re.findall("“(.+?)”", tip)
    }
    # Floor: this check can be satisfied by finding nothing, so require it to
    # have found something to check. Drop this and deleting every “…” passes.
    assert references, (
        "no typographic cross-references found at all — either the convention "
        "has been abandoned (update this test) or the extractor is broken"
    )
    dangling = sorted(r for r in references if r.lower() not in labels)
    assert not dangling, (
        "these tooltips name a control that no label on screen matches: "
        f"{dangling}. Rename the reference, or the label it meant."
    )


def test_every_interactive_setting_carries_a_tooltip() -> None:
    """A control a user can change must say what changing it does.

    The tooltip rules above check the WORDING of the tooltips that exist. This
    checks that one exists — a different question, and the one that found the
    *Naming scheme* dropdown with none (2026-09-22). It is the only control in
    the dialog that rewrites two other fields, so it was the worst candidate to
    leave unexplained, and no test asked because every test here started from
    the set of tooltips rather than from the set of controls.

    Starting from the controls is the point: a sweep seeded by what exists can
    never report something missing.

    **There is no allowlist, and there was going to be one.** The first version
    carried `_NO_TOOLTIP_NEEDED` holding the two display-only `QLabel`s — and
    its own converse check immediately reported both as naming controls that do
    not exist, because a `QLabel` is not in the interactive set and never could
    have failed this. The exemption list was empty by construction: two excuses
    for a rule that did not reach them. Deleted rather than kept as
    documentation, since a list of excuses enforces nothing and this one
    enforced less than nothing.
    """
    src = SETTINGS.read_text(encoding="utf-8")
    tree = ast.parse(src)
    interactive = {"QCheckBox", "QComboBox", "QSpinBox", "QLineEdit"}
    declared: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Attribute):
            value = node.value
            if isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
                if value.func.id in interactive:
                    declared[node.target.attr] = value.func.id
    # Floor: the extractor must actually be finding controls.
    assert len(declared) >= 20, (
        f"only {len(declared)} controls found — extractor broken"
    )

    tips = _tooltips()
    missing = sorted(name for name in declared if not tips.get(name, "").strip())
    assert not missing, (
        f"these Settings controls have no tooltip: {missing}. Add one saying "
        "what the values mean and what each produces."
    )
