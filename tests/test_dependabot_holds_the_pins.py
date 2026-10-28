"""Dependabot cannot float a pin, nor hold the weekly update hostage to one.

Critical rule #11 pins every CI-gating tool, and a few runtime packages, to a
minor (`>=X.Y.Z,<X.(Y+1)`), and tests/test_gating_tools_are_pinned.py refuses a
widened range. `.github/dependabot.yml` keeps Dependabot from fighting that, in
three ways, and this test holds each (the follow-up reviews of 2026-10-27):

1. **Every minor-pinned CI tool is ignored BY NAME**, with no `update-types`.
   An `update-types` ignore skips versions relative to the dependency's current
   version, and a pyproject range has none, so it matched nothing
   (dependabot-core@8ef6f0723368:common/lib/dependabot/config/ignore_condition.rb:56-58);
   that is how #303 and #399 got through. A name-only ignore skips every version
   update and still lets a security update through (:42-43).
2. **Every minor-pinned package is kept out of the weekly group**, so each one
   that is not ignored (the runtime pins) arrives in a pull request of its own,
   and a red widening holds back only itself.
3. **Both ecosystems wait seven days** before proposing a release.

The file is read as text, since the suite has no YAML parser and the shapes
checked are fixed lines at fixed indentation; floors keep a broken read from
passing.
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

#: The shortest cooldown the config may carry (zizmor's dependabot-cooldown
#: audit flags fewer than seven days).
_MIN_COOLDOWN_DAYS: Final[int] = 7


def _name(spec: str) -> str:
    return re.split(r"[<>=!~ ;\[]", spec, maxsplit=1)[0]


def _minor_pinned() -> tuple[set[str], set[str]]:
    """``(runtime, tools)``: minor-pinned names in `dependencies` and in the extras.

    The split is read from where pyproject puts each one, not from a list kept
    here: what the app needs at run time is a runtime pin, and what only a
    developer or a CI job installs (the extras) is a tool.
    """
    project = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]
    runtime = {_name(s) for s in project["dependencies"] if _MINOR_CEILING.search(s)}
    tools = {
        _name(s)
        for specs in project["optional-dependencies"].values()
        for s in specs
        if _MINOR_CEILING.search(s)
    }
    return runtime, tools


def _ecosystem_block(ecosystem: str) -> str:
    """One ecosystem's block of dependabot.yml, up to the next ecosystem."""
    text = DEPENDABOT.read_text(encoding="utf-8")
    start = text.index(f'- package-ecosystem: "{ecosystem}"')
    end = text.find("- package-ecosystem:", start + 1)
    return text[start : end if end != -1 else len(text)]


def _ignore_entries(block: str) -> dict[str, list[str]]:
    """Each ignored name and the keys under it (`update-types`, `versions`)."""
    entries: dict[str, list[str]] = {}
    current: str | None = None
    for line in block.splitlines():
        named = re.match(r'^      - dependency-name: "([^"]+)"$', line)
        if named:
            current = named.group(1)
            entries[current] = []
        elif current is not None and re.match(r"^        [a-z-]+:", line):
            entries[current].append(line.strip().split(":")[0])
        elif not line.startswith("        "):
            current = None
    return entries


def _weekly_excludes(block: str) -> list[str]:
    match = re.search(
        r"^      pip-weekly:\n(?P<body>(?:        .*\n)+)", block, re.MULTILINE
    )
    assert match, "dependabot.yml has no `pip-weekly` group in its pip block"
    body = match.group("body")
    assert "exclude-patterns:" in body, "`pip-weekly` excludes nothing"
    excludes = body.split("exclude-patterns:", 1)[1]
    return re.findall(r'^          - "([^"]+)"$', excludes, re.MULTILINE)


def test_the_split_is_read_from_pyproject_and_is_not_empty() -> None:
    runtime, tools = _minor_pinned()
    # 3 runtime pins and 9 tools on 2026-10-27; fewer means the read broke.
    assert {"PySide6", "sigstore"} <= runtime, runtime
    assert len(tools) >= 8 and {"ruff", "mypy"} <= tools, tools


def test_every_pinned_ci_tool_is_ignored_by_name_alone() -> None:
    _, tools = _minor_pinned()
    entries = _ignore_entries(_ecosystem_block("pip"))
    missing = sorted(tools - set(entries))
    assert not missing, f"pinned CI tools Dependabot is not told to leave: {missing}"
    typed = sorted(name for name, keys in entries.items() if "update-types" in keys)
    assert not typed, (
        "an `update-types` ignore matches nothing for a pyproject range, so these "
        f"would be proposed anyway (#303, #399); ignore them by name: {typed}"
    )


def test_no_runtime_pin_is_ignored() -> None:
    """We want to hear of PySide6's, sigstore's and numpy's releases."""
    runtime, _ = _minor_pinned()
    ignored = set(_ignore_entries(_ecosystem_block("pip")))
    assert not runtime & ignored, sorted(runtime & ignored)


def test_every_minor_pin_is_kept_out_of_the_weekly_group() -> None:
    runtime, tools = _minor_pinned()
    excludes = set(_weekly_excludes(_ecosystem_block("pip")))
    missing = sorted((runtime | tools) - excludes)
    assert not missing, (
        "minor-pinned in pyproject.toml but inside dependabot's weekly group, so "
        f"one red widening would hold every other update back: {missing}"
    )


def test_there_is_no_shared_pinned_group_any_more() -> None:
    """#399 came from one: a single group put PySide6 and mypy in one pull request."""
    block = _ecosystem_block("pip")
    groups = re.findall(r"^      ([a-z0-9-]+):\n        applies-to:", block, re.M)
    assert groups == ["pip-weekly"], groups


def test_both_ecosystems_wait_a_week_before_proposing_a_release() -> None:
    """Item 3 of the second follow-up: a cooldown set to 0 went unnoticed."""
    for ecosystem in ("pip", "github-actions"):
        block = _ecosystem_block(ecosystem)
        match = re.search(r"^    cooldown:\n      default-days: (\d+)$", block, re.M)
        assert match, f"{ecosystem} has no cooldown"
        assert int(match.group(1)) >= _MIN_COOLDOWN_DAYS, (
            f"{ecosystem} waits {match.group(1)} days; the floor is {_MIN_COOLDOWN_DAYS}"
        )


def test_no_ecosystem_names_labels() -> None:
    """Named labels that do not exist make Dependabot post an error on every pull
    request (#397, #399); with none named it creates its default `dependencies`."""
    for ecosystem in ("pip", "github-actions"):
        assert not re.search(r"^    labels:", _ecosystem_block(ecosystem), re.M), (
            f"{ecosystem} names labels; create them in the repository first, or "
            "leave Dependabot its default"
        )
