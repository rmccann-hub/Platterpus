"""Dependabot cannot turn a whole weekly update red over one minor pin.

Critical rule #11 pins every CI-gating tool, and a few runtime packages, to a
minor (`>=X.Y.Z,<X.(Y+1)`), and tests/test_gating_tools_are_pinned.py refuses a
widened range. Dependabot widens ranges as a matter of course, so a widening it
proposes is red by design (PLANNING.md KDD-43). Two defences live in
`.github/dependabot.yml`, and this test holds both (the follow-up review of
2026-10-27, item 3):

1. Every minor-pinned package in pyproject.toml is in the `pinned-minor` group,
   and that group comes before the catch-all `pip-weekly`, because Dependabot
   puts a package in the first group that matches. A widening then reddens only
   its own pull request.
2. Every pinned CI tool is in the `ignore` list, as ruff and mypy have been
   since 2026-09.

The file is read as text, since the suite has no YAML parser and the shapes
checked are fixed lines; the floors keep a broken read from passing.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Final

REPO: Final[Path] = Path(__file__).resolve().parent.parent
DEPENDABOT: Final[Path] = REPO / ".github" / "dependabot.yml"

#: A minor ceiling: `<6.12`, `<0.16`. A major-only ceiling (`<2`) is not a pin.
_MINOR_CEILING: Final[re.Pattern[str]] = re.compile(r"<\s*\d+\.\d+")

#: The CI tools, as opposed to runtime packages: these are ignored too.
_CI_TOOLS: Final[frozenset[str]] = frozenset(
    {"ruff", "mypy", "pip-audit", "build", "twine", "python-appimage"}
)


def _minor_pinned() -> dict[str, str]:
    """Every pyproject requirement with a minor ceiling, name → which list."""
    project = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]
    found: dict[str, str] = {}
    sources = [("dependencies", project["dependencies"])] + [
        (f"extra {name}", specs)
        for name, specs in project["optional-dependencies"].items()
    ]
    for where, specs in sources:
        for spec in specs:
            if _MINOR_CEILING.search(spec):
                name = re.split(r"[<>=!~ ;\[]", spec, maxsplit=1)[0]
                found[name] = where
    return found


def _pip_block() -> str:
    """The pip ecosystem's block of dependabot.yml, up to the next ecosystem."""
    text = DEPENDABOT.read_text(encoding="utf-8")
    start = text.index('- package-ecosystem: "pip"')
    end = text.find("- package-ecosystem:", start + 1)
    return text[start : end if end != -1 else len(text)]


def _group_patterns(block: str, group: str) -> list[str]:
    match = re.search(
        rf"^      {re.escape(group)}:\n(?P<body>(?:        .*\n)+)", block, re.MULTILINE
    )
    assert match, f"dependabot.yml has no `{group}` group in its pip block"
    return re.findall(r'^          - "([^"]+)"$', match.group("body"), re.MULTILINE)


def test_every_minor_pin_has_its_own_group_ahead_of_the_weekly_one() -> None:
    pinned = _minor_pinned()
    # 11 on 2026-10-27; fewer means the read broke, not that pins went away.
    assert len(pinned) >= 10, pinned
    block = _pip_block()
    patterns = _group_patterns(block, "pinned-minor")
    missing = sorted(set(pinned) - set(patterns))
    assert not missing, (
        f"minor-pinned in pyproject.toml but not in dependabot's `pinned-minor` "
        f"group, so one widening would redden the whole weekly group: {missing}"
    )
    assert block.index("      pinned-minor:") < block.index("      pip-weekly:"), (
        "`pinned-minor` must come before `pip-weekly`: Dependabot uses the first "
        "group that matches"
    )


def test_every_pinned_ci_tool_is_ignored() -> None:
    pinned = _minor_pinned()
    tools = {name for name in pinned if name in _CI_TOOLS} | {
        name for name, where in pinned.items() if where == "extra ci-lint"
    }
    assert len(tools) >= 8, tools
    ignored = set(
        re.findall(r'^      - dependency-name: "([^"]+)"$', _pip_block(), re.M)
    )
    missing = sorted(tools - ignored)
    assert not missing, f"pinned CI tools Dependabot is not told to leave: {missing}"
