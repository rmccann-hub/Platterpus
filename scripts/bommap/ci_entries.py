"""GitHub Actions, CI programs and packages, and runner images."""

from __future__ import annotations

import re
from typing import Final

from bommap.model import _P, Entry, GeneratorError
from bommap.reading import _join, _require, _text
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

    entries.extend(_gitleaks_entries(entries))
    entries.extend(_actionlint_entries())

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
        pin = _program_pin(program, rel)
        entries.append(
            Entry(
                ref=f"ci:{program}",
                category="ci-tool",
                name=program,
                version=pin,
                scope="excluded",
                description=purpose,
                used_in=(_require(rel, literal, why=f"CI program {program}"),),
                enforced_in=(rel,) if pin else (),
                properties=(
                    (
                        _P + "version-basis",
                        f"pinned by sha256 in {rel}"
                        if pin
                        else "not pinned; whatever the runner or tool cache provides",
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


#: A pinned release's version and tarball sha256, by shape.
_VERSION_SHAPE: Final[re.Pattern[str]] = re.compile(r"\d{1,6}\.\d{1,6}\.\d{1,6}")
_SHA256_SHAPE: Final[re.Pattern[str]] = re.compile(r"[0-9a-f]{64}")

#: The CI workflow whose jobs fetch release binaries pinned by version and sha256.
_SECRET_SCAN_WORKFLOW: Final[str] = ".github/workflows/ci.yml"


def _pinned_release_binary(
    name: str, env: str, repo: str, job: str, description: str
) -> Entry | None:
    """A release binary a CI job fetches, pinned as `<env>_VERSION` and
    `<env>_SHA256` in the job, or None when the workflow pins no such binary."""
    # String operations, not a pattern built from `env`, as `_program_pin`.
    found: dict[str, str] = {}
    for line in _text(_SECRET_SCAN_WORKFLOW).splitlines():
        for key in ("VERSION", "SHA256"):
            prefix = f'{env}_{key}: "'
            at = line.find(prefix)
            if at >= 0 and line.rstrip().endswith('"'):
                found.setdefault(key, line[at + len(prefix) :].rstrip()[:-1])
    version, sha = found.get("VERSION", ""), found.get("SHA256", "")
    if not (_VERSION_SHAPE.fullmatch(version) and _SHA256_SHAPE.fullmatch(sha)):
        return None
    return Entry(
        ref=f"ci:{name}",
        category="ci-tool",
        name=name,
        scope="excluded",
        description=description,
        external_refs=(("vcs", f"https://github.com/{repo}", ""),),
        version=version,
        purl=f"pkg:github/{repo}@v{version}",
        used_in=(_where(_SECRET_SCAN_WORKFLOW, job),),
        enforced_in=(_SECRET_SCAN_WORKFLOW,),
        properties=(
            (
                _P + "version-basis",
                "pinned in the workflow, with the release tarball's sha256",
            ),
            (_P + "tarball-sha256", sha),
        ),
    )


def _gitleaks_entries(entries: list[Entry]) -> list[Entry]:
    """The gitleaks binary CI runs: pinned in the workflow, or chosen by the action.

    Since 2026-10-05 (`PLANNING.md` KDD-41) the `gitleaks` job installs the CLI
    itself, its version and the release tarball's sha256 pinned in the job, so the
    map names that version. The action branch stays for a workflow that still uses
    it. A `gitleaks` job with neither stops the run: a tool CI runs must not drop
    out of the map because the way it is installed changed (it did, once, the day
    this was written).
    """
    pinned = _pinned_release_binary(
        "gitleaks",
        "GITLEAKS",
        "gitleaks/gitleaks",
        "gitleaks",
        "The secret scanner the gitleaks job runs.",
    )
    if pinned is not None:
        return [pinned]
    actions = [e for e in entries if e.name == "gitleaks-action"]
    text = _text(_SECRET_SCAN_WORKFLOW)
    if actions:
        return [
            Entry(
                ref="ci:gitleaks",
                category="ci-tool",
                name="gitleaks",
                scope="excluded",
                description="The secret scanner the gitleaks job runs.",
                external_refs=(("vcs", "https://github.com/gitleaks/gitleaks", ""),),
                used_in=actions[0].used_in,
                properties=(
                    (
                        _P + "version-basis",
                        "chosen by gitleaks/gitleaks-action at its pinned commit; not pinned in this repository",
                    ),
                ),
                required_by=tuple(e.ref for e in actions),
            )
        ]
    if "\n  gitleaks:\n" in text:
        raise GeneratorError(
            f"{_SECRET_SCAN_WORKFLOW} has a gitleaks job but neither the action nor a "
            "pinned GITLEAKS_VERSION and GITLEAKS_SHA256; say how it gets gitleaks"
        )
    return []


def _actionlint_entries() -> list[Entry]:
    """The actionlint binary the `workflow-lint` job fetches and runs.

    Since 2026-11-03 (TASKS R91) the job installs actionlint's release binary,
    pinned like gitleaks, instead of building actionlint-py from its sdist by
    pyproject's range; pyproject's `actionlint-py` line stays for local installs
    and is mapped separately. Running the fetched binary unpinned stops the run.
    """
    pinned = _pinned_release_binary(
        "actionlint",
        "ACTIONLINT",
        "rhysd/actionlint",
        "workflow-lint",
        "The workflow linter the workflow-lint job runs.",
    )
    if pinned is not None:
        return [pinned]
    if '"$RUNNER_TEMP/actionlint"' in _text(_SECRET_SCAN_WORKFLOW):
        raise GeneratorError(
            f"{_SECRET_SCAN_WORKFLOW} runs a fetched actionlint but does not pin "
            "ACTIONLINT_VERSION and ACTIONLINT_SHA256; say which one it runs"
        )
    return []


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


def _program_pin(program: str, rel: str) -> str:
    """The release a script pins ``program`` to, read from the script, or "".

    Read, not restated: ``build/build_appimage.sh`` names appimagetool's release
    as ``APPIMAGETOOL_TAG="<tag>"`` beside its sha256 (2026-11-02, after the
    floating "continuous" build of 2026-11-01 refused our AppDir).
    """
    # String operations, not a pattern built from the name: a computed pattern
    # is one `tests/test_regex_bounded_time.py` cannot time.
    variable = "".join(c if c.isalnum() else "_" for c in program.upper()) + "_TAG"
    prefix = f'{variable}="'
    for line in _text(rel).splitlines():
        if (
            line.startswith(prefix)
            and line.endswith('"')
            and len(line) > len(prefix) + 1
        ):
            return line[len(prefix) : -1]
    return ""


#: Programs a build or workflow runs that no package list names. Each carries
#: its witness, so an entry the scripts stopped using stops the run.
_CI_PROGRAMS: Final[tuple[tuple[str, str, str, str], ...]] = (
    (
        "appimagetool",
        "build/build_appimage.sh",
        "appimagetool",
        "Packs the AppImage for python-appimage, and re-packs it to embed the zsync update information; a fixed release the build fetches and checks by sha256.",
    ),
    (
        "gh",
        ".github/workflows/release.yml",
        "gh",
        "GitHub CLI on the runner: creates the release and uploads its assets.",
    ),
)
