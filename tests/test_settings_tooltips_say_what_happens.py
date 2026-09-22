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
