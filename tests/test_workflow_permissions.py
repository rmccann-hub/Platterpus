"""Every workflow's top-level token only READS; a write is granted on the job that needs it.

Why this exists (2026-09-28, the maintainer's call). The operator's repository
standard asks every workflow to set ``permissions:`` with ``contents: read`` or
narrower at the top, with any wider grant given only to the job that needs it,
and says one workflow missing the block is the finding however many others have
it. Measured that day: ``appimage.yml`` had no block at all, so it ran with the
repository's default token, and ``release.yml`` granted four writes to the whole
workflow rather than to its one job.

**Why a sweep and not two fixes.** A per-file check protects only the files that
were wrong on the day. This reads every workflow the directory holds, so the next
one added is held to the same shape without anyone remembering to add it here.

Parsed as text rather than YAML: PyYAML is not a declared dependency of the test
suite, and the shape checked (a column-0 ``permissions:`` key and its two-space
children) is simple enough to read without one.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

_WORKFLOWS: Final[Path] = Path(__file__).resolve().parents[1] / ".github" / "workflows"

#: Values a workflow-level grant may carry.
_READ_ONLY: Final[frozenset[str]] = frozenset({"read", "none"})


def _top_level_permissions(text: str) -> dict[str, str] | None:
    """The workflow-level ``permissions:`` mapping, or ``None`` when there is none.

    The inline forms ``permissions: read-all`` / ``{}`` are returned as a one-key
    mapping so the caller judges them like any other grant.
    """
    lines = text.splitlines()
    for index, line in enumerate(lines):
        match = re.match(r"^permissions:\s*(?P<inline>\S.*)?$", line)
        if match is None:
            continue
        inline = (match.group("inline") or "").split("#", 1)[0].strip()
        if inline:
            return {"(inline)": inline}
        grants: dict[str, str] = {}
        for child in lines[index + 1 :]:
            if not child.strip() or child.lstrip().startswith("#"):
                continue
            if not child.startswith("  ") or child.startswith("   "):
                break
            key, _, value = child.strip().partition(":")
            grants[key.strip()] = value.split("#", 1)[0].strip()
        return grants
    return None


def _workflow_files() -> list[Path]:
    return sorted([*_WORKFLOWS.glob("*.yml"), *_WORKFLOWS.glob("*.yaml")])


def test_every_workflow_reads_only_at_the_top() -> None:
    files = _workflow_files()
    # NON-TRIVIALITY: the directory holds five workflows today; a glob that found
    # none would pass everything below.
    assert len(files) >= 5, [f.name for f in files]
    problems: list[str] = []
    for path in files:
        grants = _top_level_permissions(path.read_text(encoding="utf-8"))
        if grants is None:
            problems.append(f"{path.name}: no workflow-level `permissions:` block")
            continue
        if not grants:
            problems.append(f"{path.name}: an empty `permissions:` block")
            continue
        for key, value in grants.items():
            if key == "(inline)":
                if value not in ("{}", "read-all"):
                    problems.append(f"{path.name}: `permissions: {value}` at the top")
            elif value not in _READ_ONLY:
                problems.append(
                    f"{path.name}: `{key}: {value}` at the top; grant it on the job"
                )
    assert not problems, "\n".join(problems)


def test_the_release_job_still_holds_the_writes_it_needs() -> None:
    """The other half: moving the grants must not lose them. The release job
    creates the Release, dispatches the PyPI publish, mints an OIDC identity and
    writes the attestation, and each of those fails without its grant."""
    text = (_WORKFLOWS / "release.yml").read_text(encoding="utf-8")
    job = text.split("\n  build-and-release:\n", 1)[1]
    block = job.split("\n    permissions:\n", 1)[1].split("\n    runs-on:", 1)[0]
    for grant in ("contents", "actions", "id-token", "attestations"):
        assert re.search(rf"^      {grant}: write\b", block, re.MULTILINE), grant


def test_the_parser_reads_the_shapes_it_judges() -> None:
    """The parser can fail: a block, an inline form, and no block at all."""
    assert _top_level_permissions(
        "on: push\npermissions:\n  contents: read\njobs:\n"
    ) == {"contents": "read"}
    assert _top_level_permissions("permissions: write-all\n") == {
        "(inline)": "write-all"
    }
    assert _top_level_permissions("on: push\njobs:\n  x:\n    permissions:\n") is None
