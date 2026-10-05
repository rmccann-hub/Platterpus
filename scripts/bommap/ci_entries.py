"""GitHub Actions, CI programs and packages, and runner images."""

from __future__ import annotations

import re
from typing import Final

from bommap.model import _P, Entry
from bommap.reading import _join, _require
from bommap.workflows import _where, workflows


def _ci_entries() -> list[Entry]:
    entries: list[Entry] = []
    actions: dict[tuple[str, str], dict[str, set[str]]] = {}
    for flow in workflows():
        for job, action, ref, comment in flow.uses:
            actions.setdefault((action, ref), {}).setdefault(comment, set()).add(
                _where(flow.rel, job)
            )
    for (action, ref), by_comment in sorted(actions.items()):
        owner, _, rest = action.partition("/")
        comments = sorted(c for c in by_comment if c)
        places = sorted({p for ps in by_comment.values() for p in ps})
        pinned = re.fullmatch(r"[0-9a-f]{40}", ref) is not None
        entries.append(
            Entry(
                ref=f"gha:{action}@{ref}",
                category="ci-action",
                name=rest,
                group=owner,
                version=_join(comments) or ref,
                scope="excluded",
                purl=f"pkg:github/{owner}/{rest.split('/')[0]}@{ref}",
                description=_ACTION_PURPOSE.get(action, ""),
                used_in=tuple(places),
                enforced_in=tuple(sorted({p.split(" ")[0] for p in places})),
                external_refs=(
                    ("vcs", f"https://github.com/{owner}/{rest.split('/')[0]}", ""),
                ),
                properties=(
                    (_P + "pinned-ref", ref),
                    (_P + "pinned-to-commit-sha", "yes" if pinned else "no"),
                    (_P + "version-comment", _join(comments) or "none"),
                ),
            )
        )

    # The gitleaks binary, which the action downloads and runs.
    gitleaks_actions = [e for e in entries if e.name == "gitleaks-action"]
    if gitleaks_actions:
        entries.append(
            Entry(
                ref="ci:gitleaks",
                category="ci-tool",
                name="gitleaks",
                scope="excluded",
                description="The secret scanner the gitleaks job runs.",
                used_in=gitleaks_actions[0].used_in,
                external_refs=(("vcs", "https://github.com/gitleaks/gitleaks", ""),),
                properties=(
                    (
                        _P + "version-basis",
                        "chosen by gitleaks/gitleaks-action at its pinned commit; not pinned in this repository",
                    ),
                ),
                required_by=tuple(e.ref for e in gitleaks_actions),
            )
        )

    apt: dict[str, set[str]] = {}
    for flow in workflows():
        for job, package in flow.apt:
            apt.setdefault(package, set()).add(_where(flow.rel, job))
    for package, apt_places in sorted(apt.items()):
        entries.append(
            Entry(
                ref=f"apt:{package}",
                category="ci-tool",
                name=package,
                cdx_type="library" if package.startswith("lib") else "application",
                scope="excluded",
                purl=f"pkg:deb/ubuntu/{package}",
                description=_APT_PURPOSE.get(package)
                or (
                    "A system library PySide6 needs to run headless in CI."
                    if package.startswith("lib")
                    else "Installed with apt-get on the runner."
                ),
                used_in=tuple(sorted(apt_places)),
                properties=(
                    (_P + "version-basis", "the runner image's Ubuntu archive"),
                ),
            )
        )

    for program, rel, literal, purpose in _CI_PROGRAMS:
        entries.append(
            Entry(
                ref=f"ci:{program}",
                category="ci-tool",
                name=program,
                scope="excluded",
                description=purpose,
                used_in=(_require(rel, literal, why=f"CI program {program}"),),
                properties=(
                    (
                        _P + "version-basis",
                        "not pinned; whatever the runner or tool cache provides",
                    ),
                ),
            )
        )

    runners: dict[str, set[str]] = {}
    for flow in workflows():
        for job, label in flow.runners:
            runners.setdefault(label, set()).add(_where(flow.rel, job))
    for label, runner_places in sorted(runners.items()):
        entries.append(
            Entry(
                ref=f"runner:{label}",
                category="ci-runner",
                name=label,
                cdx_type="operating-system",
                scope="excluded",
                description="GitHub-hosted runner image.",
                used_in=tuple(sorted(runner_places)),
                properties=(
                    (
                        _P + "pinned",
                        "no (a moving label)"
                        if label.endswith("-latest")
                        else "to the image's major release",
                    ),
                ),
            )
        )
    return entries


#: What each action is for. The set of actions comes from the workflows; an
#: action missing here gets an empty description, never a guess.
_ACTION_PURPOSE: Final[dict[str, str]] = {
    "actions/attest-build-provenance": "Signs the release AppImage's build-provenance attestation.",
    "actions/checkout": "Checks out the repository.",
    "actions/setup-python": "Installs the job's Python.",
    "actions/upload-artifact": "Keeps a job's output (the SBOM, the AppImage, mutation reports).",
    "gitleaks/gitleaks-action": "Runs the gitleaks secret scan.",
    "pypa/gh-action-pypi-publish": "Publishes the wheel and sdist to PyPI.",
}


_APT_PURPOSE: Final[dict[str, str]] = {
    "zsync": "zsyncmake, which writes the AppImage's .zsync delta-update file.",
}


#: Programs a build or workflow runs that no package list names. Each carries
#: its witness, so an entry the scripts stopped using stops the run.
_CI_PROGRAMS: Final[tuple[tuple[str, str, str, str], ...]] = (
    (
        "appimagetool",
        "build/build_appimage.sh",
        "appimagetool",
        "Re-packs the AppImage to embed the zsync update information (the copy python-appimage caches, or the system's).",
    ),
    (
        "gh",
        ".github/workflows/release.yml",
        "gh",
        "GitHub CLI on the runner: creates the release and uploads its assets.",
    ),
)
