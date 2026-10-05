"""Python packages: what the app imports, the dev extra, and build/CI tools."""

from __future__ import annotations

import re
from functools import cache
from typing import Final

from bommap.model import _P, ROOT_REF, Entry, GeneratorError
from bommap.reading import (
    _exact,
    _imported_by,
    _join,
    _normalise,
    _project,
    _pyproject,
    _requirement,
    _strings,
    _text,
    _witnessed,
)
from bommap.workflows import _where, workflows


@cache
def _appimage_requirements() -> dict[str, str]:
    """Normalised name → the spec ``build/python-appimage/requirements.txt`` gives."""
    out: dict[str, str] = {}
    for raw in _text("build/python-appimage/requirements.txt").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        name, spec = _requirement(line)
        out[_normalise(name)] = spec
    return out


def _python_runtime_entries() -> list[Entry]:
    from platterpus.deps.registry import SPECS

    registry = {spec.dep_id: spec for spec in SPECS}
    appimage = _appimage_requirements()
    entries: list[Entry] = []
    for text in _strings(_project()["dependencies"]):
        name, constraint = _requirement(text)
        norm = _normalise(name)
        exact = _exact(constraint)
        enforced = ["pyproject.toml [project].dependencies"]
        props: list[tuple[str, str]] = [
            (_P + "constraint", constraint),
            (_P + "imported-by", _imported_by(name, ("src",))),
        ]
        if norm in appimage:
            enforced.append("build/python-appimage/requirements.txt")
            props.append((_P + "appimage-constraint", appimage[norm]))
        spec = registry.get(norm)
        if spec is not None:
            enforced.append("src/platterpus/deps/registry.py (checked at launch)")
            props.append(
                (_P + "checked-minimum", ".".join(str(n) for n in spec.min_version))
            )
        entries.append(
            Entry(
                ref=f"pypi:{norm}",
                category="python-runtime",
                name=name,
                cdx_type="framework" if norm == "pyside6" else "library",
                version=exact,
                constraint=constraint,
                purl=f"pkg:pypi/{norm}" + (f"@{exact}" if exact else ""),
                description=_PYTHON_PURPOSE.get(norm, ""),
                used_in=(props[1][1],),
                enforced_in=tuple(enforced),
                properties=tuple(props),
                required_by=(ROOT_REF,),
            )
        )
    return entries


#: What each runtime package is FOR. The package list itself comes from
#: pyproject; an entry missing here gets an empty description, never a guess.
_PYTHON_PURPOSE: Final[dict[str, str]] = {
    "pyside6": "Qt for Python: the whole GUI.",
    "musicbrainzngs": (
        "MusicBrainz client, behind the MusicBrainzClient adapter (Critical "
        "rule #1; unmaintained upstream)."
    ),
    "tomli-w": "Writes config.toml (the standard library reads TOML but cannot write it).",
    "cryptography": "Ed25519 verification for the minisign path of the updater.",
    "sigstore": "Verifies each release's build-provenance attestation before an update installs.",
}


@cache
def _dev_block_raw() -> str:
    """The raw text of pyproject's ``dev = [...]`` block, comments included.

    tomllib drops comments, and the comment is where pyproject marks which dev
    tools GATE CI (Critical rule #11), so that one fact is read from the text.
    """
    match = re.search(
        r"^dev = \[(?P<body>.*?)^\]", _text("pyproject.toml"), re.MULTILINE | re.DOTALL
    )
    if match is None:
        raise GeneratorError("pyproject.toml has no dev extra block")
    return match.group("body")


def _python_dev_entries() -> list[Entry]:
    extras = _project()["optional-dependencies"]
    assert isinstance(extras, dict)
    raw = _dev_block_raw()
    gating_start = raw.find("--- gating")
    entries: list[Entry] = []
    for text in _strings(extras["dev"]):
        name, constraint = _requirement(text)
        norm = _normalise(name)
        position = raw.find(f'"{text}"')
        gating = gating_start != -1 and position > gating_start
        imported = _imported_by(name, ("tests", "scripts"))
        # Where it is run: any workflow or the local gate runner that names it
        # on a non-comment line. A pytest plugin is named by neither (pytest
        # loads it), so its row says so instead of inventing a place.
        runners = [
            rel
            for rel in (*(f.rel for f in workflows()), "scripts/check.py")
            if _witnessed(rel, name, as_word=True)
        ]
        used = ([imported] if imported != "not imported directly" else []) + runners
        props: list[tuple[str, str]] = [
            (_P + "constraint", constraint),
            (_P + "imported-by", imported),
            (
                _P + "gates-ci",
                "yes (pinned to the measured minor, Critical rule #11)"
                if gating
                else "no",
            ),
        ]
        entries.append(
            Entry(
                ref=f"pypi:{norm}",
                category="python-dev",
                name=name,
                cdx_type="library",
                version=_exact(constraint),
                constraint=constraint,
                scope="excluded",
                purl=f"pkg:pypi/{norm}",
                description=_DEV_PURPOSE.get(norm, ""),
                used_in=tuple(used) or ("loaded by pytest as a plugin",),
                enforced_in=("pyproject.toml [project.optional-dependencies].dev",),
                properties=tuple(props),
            )
        )
    return entries


#: What each dev tool is for. The list itself comes from pyproject's dev extra.
_DEV_PURPOSE: Final[dict[str, str]] = {
    "pytest": "The test runner.",
    "pytest-cov": "Branch coverage and the CI coverage floor.",
    "pytest-xdist": "Parallel test runs (CI and scripts/check.py pass -n auto).",
    "hypothesis": "Property-based tests, including the parsers' never-raises properties.",
    "ruff": "Lint and format; gates CI.",
    "mypy": "Strict type checking; gates CI.",
}


def _python_build_entries(taken: set[str]) -> list[Entry]:
    """Build-system requirements and every package a workflow or build script installs.

    A package installed in several places is ONE entry whose constraint lists
    each place — two places pinning it differently is a fact worth seeing, and
    merging them into one number would hide it.
    """
    seen: dict[str, dict[str, set[str]]] = {}
    names: dict[str, str] = {}

    def add(text: str, where: str) -> None:
        name, constraint = _requirement(text)
        norm = _normalise(name)
        if norm in taken:  # already listed as a runtime or dev package
            return
        names.setdefault(norm, name)
        seen.setdefault(norm, {}).setdefault(constraint or "unpinned", set()).add(where)

    build_system = _pyproject()["build-system"]
    assert isinstance(build_system, dict)
    for text in _strings(build_system["requires"]):
        add(text, "pyproject.toml [build-system].requires")
    for flow in workflows():
        for job, text in flow.pip:
            add(text, _where(flow.rel, job))
    for match in re.finditer(
        r"^require_python_module\s+\S+\s+'(?P<spec>[^']+)'",
        _text("build/build_appimage.sh"),
        re.MULTILINE,
    ):
        add(match.group("spec"), "build/build_appimage.sh")

    entries: list[Entry] = []
    for norm in sorted(seen):
        by_constraint = seen[norm]
        # One constraint everywhere reads as that constraint; different ones in
        # different places are spelled out place by place.
        constraint = (
            next(iter(by_constraint))
            if len(by_constraint) == 1
            else "; ".join(
                f"{c} in {_join(sorted(places))}"
                for c, places in sorted(by_constraint.items())
            )
        )
        places = sorted({p for ps in by_constraint.values() for p in ps})
        exacts = {_exact(c) for c in by_constraint}
        entries.append(
            Entry(
                ref=f"pypi:{norm}",
                category="python-build",
                name=names[norm],
                cdx_type="application",
                version=exacts.pop() if len(exacts) == 1 else "",
                constraint=constraint,
                scope="excluded",
                purl=f"pkg:pypi/{norm}",
                description=_BUILD_PURPOSE.get(norm, ""),
                used_in=tuple(places),
                enforced_in=tuple(places),
                properties=((_P + "constraint", constraint),),
            )
        )
    return entries


_BUILD_PURPOSE: Final[dict[str, str]] = {
    "build": "PEP 517 frontend: builds the wheel and sdist.",
    "cyclonedx-bom": "Writes the CI sbom job's resolved-environment SBOM.",
    "pip": "Installs everything else.",
    "pip-audit": "The gating vulnerability audit of the resolved runtime graph.",
    "python-appimage": "Builds the AppImage (Critical rule #2).",
    "setuptools": "The build backend.",
    "twine": "Checks the wheel and sdist before the PyPI upload.",
    "wheel": "Wheel support for the build backend.",
}
