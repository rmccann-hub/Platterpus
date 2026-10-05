"""Languages, runtimes and platforms: the two Pythons, Qt, Linux."""

from __future__ import annotations

import re

from bommap.model import _P, ROOT_REF, Entry, GeneratorError
from bommap.reading import (
    _join,
    _normalise,
    _project,
    _requirement,
    _strings,
    _text,
    _vers,
)
from bommap.workflows import workflows


def _runtime_entries() -> list[Entry]:
    """Python (two of them: the user's for pipx, ours in the AppImage), Qt, Linux."""
    project = _project()
    requires = str(project["requires-python"])
    classifiers = _strings(project.get("classifiers", []))
    ci = _text(".github/workflows/ci.yml")
    matrix_match = re.search(r"python-version:\s*\[(?P<v>[^\]]+)\]", ci)
    if matrix_match is None:
        raise GeneratorError("ci.yml no longer declares a python-version matrix")
    matrix = re.findall(r'"([^"]+)"', matrix_match.group("v"))
    coverage = re.findall(
        r'-\s*python-version:\s*"([^"]+)"\s*\n\s*coverage:\s*true', ci
    )
    single = sorted(
        {
            version
            for flow in workflows()
            for version in re.findall(
                r'^\s*python-version:\s*"([^"]+)"\s*$', _text(flow.rel), re.MULTILINE
            )
        }
    )
    listed = sorted(
        c.rsplit("::", 1)[1].strip()
        for c in classifiers
        if c.startswith("Programming Language :: Python :: 3.")
    )

    build = _text("build/build_appimage.sh")
    bundled = re.search(
        r'PLATTERPUS_PYTHON_VERSION="\$\{PLATTERPUS_PYTHON_VERSION:-(?P<v>[0-9.]+)\}"',
        build,
    )
    if bundled is None:
        raise GeneratorError("build_appimage.sh no longer pins the bundled CPython")

    pyside = next(
        _requirement(d)
        for d in _strings(project["dependencies"])
        if _normalise(_requirement(d)[0]) == "pyside6"
    )
    os_classifiers = sorted(
        c for c in classifiers if c.startswith("Operating System ::")
    )
    env_classifiers = sorted(c for c in classifiers if c.startswith("Environment ::"))
    release = _text(".github/workflows/release.yml")
    artifact = re.search(r"platterpus-(?P<arch>[A-Za-z0-9_]+)\.AppImage", release)
    if artifact is None:
        raise GeneratorError("release.yml no longer names the AppImage artifact")
    arch = artifact.group("arch")

    return [
        Entry(
            ref="runtime:python",
            category="runtime",
            name="python",
            group="CPython",
            cdx_type="platform",
            constraint=requires,
            version_range=_vers("generic", requires),
            is_external=True,
            description=(
                "The interpreter a pipx or development install runs on. The "
                "AppImage brings its own (next row)."
            ),
            used_in=("pip / pipx installs", "development checkouts", "CI"),
            enforced_in=(
                "pyproject.toml [project].requires-python",
                ".github/workflows/ci.yml (test matrix)",
            ),
            external_refs=(("website", "https://www.python.org/", ""),),
            properties=(
                (_P + "ci-matrix", _join(matrix)),
                (_P + "ci-coverage-leg", _join(coverage) or "none"),
                (_P + "ci-single-version-jobs", _join(single)),
                (_P + "classifiers", _join(listed)),
            ),
            required_by=(ROOT_REF,),
        ),
        Entry(
            ref="runtime:python-appimage-bundled",
            category="runtime",
            name="python (bundled in the AppImage)",
            group="CPython",
            cdx_type="platform",
            version=bundled.group("v"),
            description=(
                "The interpreter python-appimage bundles into the AppImage; pinned "
                "so a new upstream beta cannot become the release's runtime."
            ),
            used_in=("platterpus-x86_64.AppImage",),
            enforced_in=(
                "build/build_appimage.sh (PLATTERPUS_PYTHON_VERSION, overridable)",
            ),
            external_refs=(
                (
                    "distribution",
                    "https://github.com/niess/python-appimage/releases",
                    "python-appimage's CPython base images",
                ),
            ),
            required_by=(ROOT_REF,),
        ),
        Entry(
            ref="runtime:qt",
            category="runtime",
            name="Qt",
            cdx_type="framework",
            constraint=pyside[1],
            description=(
                "The GUI toolkit. It ships inside the PySide6 wheels, and PySide6 "
                "releases carry Qt's version number, so the PySide6 constraint is "
                "the Qt constraint."
            ),
            used_in=("every window and dialog (through PySide6)",),
            enforced_in=(
                "pyproject.toml [project].dependencies (PySide6)",
                "build/python-appimage/requirements.txt (PySide6)",
            ),
            external_refs=(("website", "https://www.qt.io/", ""),),
            properties=((_P + "version-basis", "the PySide6 constraint"),),
            required_by=("pypi:pyside6",),
        ),
        Entry(
            ref="runtime:linux",
            category="runtime",
            name="Linux",
            cdx_type="operating-system",
            is_external=True,
            description="The only operating system Platterpus targets.",
            used_in=(f"platterpus-{arch}.AppImage", "pip / pipx installs"),
            enforced_in=("pyproject.toml [project].classifiers",),
            properties=(
                (_P + "classifiers", _join(os_classifiers + env_classifiers)),
                (_P + "appimage-architecture", arch),
            ),
            required_by=(ROOT_REF,),
        ),
    ]
