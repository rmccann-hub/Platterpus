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


def _gitleaks_job() -> str:
    """The text of ci.yml's `gitleaks` job, from its key to the next job's key."""
    text = (_WORKFLOWS / "ci.yml").read_text(encoding="utf-8")
    start = text.index("\n  gitleaks:\n")
    nxt = re.search(r"\n  [a-z][a-z0-9-]*:\n", text[start + 1 :])
    assert nxt is not None, "the gitleaks job is the last job; read the file again"
    return text[start : start + 1 + nxt.start()]


def test_the_secret_scan_reads_the_whole_history_and_refuses_to_read_less() -> None:
    """A12 (`PLANNING.md` KDD-39; released from C3 by KDD-41).

    `gitleaks/gitleaks-action` scanned `--no-merges --first-parent <range>`, so a
    merge push to `main` logged "0 commits scanned" and passed. The job now runs
    the pinned CLI over every commit with merge diffs, and refuses a scan that read
    too little three ways, each held here because each was found to be needed:
    a shallow clone passed a relative floor alone when it was first tried.
    """
    job = _gitleaks_job()
    run_lines = [ln for ln in job.splitlines() if not ln.lstrip().startswith("#")]
    code = "\n".join(run_lines)
    assert "gitleaks/gitleaks-action" not in code, "the range-limited action is back"
    assert "fetch-depth: 0" in code
    assert '--log-opts="-m HEAD"' in code, "merge commits must be diffed per parent"
    assert "--is-shallow-repository" in code
    assert re.search(r'GITLEAKS_VERSION: "\d+\.\d+\.\d+"', code)
    assert re.search(r'GITLEAKS_SHA256: "[0-9a-f]{64}"', code)
    assert "sha256sum --check" in code
    minimum = re.search(r'MIN_COMMITS_SCANNED: "(\d+)"', code)
    assert minimum is not None and int(minimum.group(1)) >= 1500, (
        "the absolute floor fell; history on main only grows, so it should not"
    )
    assert "commits scanned" in code and "* 90 / 100" in code


#: `uses: <ref>` in a workflow, with an optional leading `- ` and quotes.
_USES: Final[re.Pattern[str]] = re.compile(
    r"^\s*(?:-\s+)?uses:\s*[\"']?(?P<ref>[^\s\"'#]+)", re.MULTILINE
)
#: A remote action pinned to a full commit SHA: `owner/repo[/path]@<40 hex>`.
_PINNED: Final[re.Pattern[str]] = re.compile(
    r"^[\w.-]+/[\w.-]+(?:/[\w./-]+)?@[0-9a-f]{40}$"
)


def test_every_action_is_pinned_to_a_full_commit_sha() -> None:
    """Every `uses:` is a local `./` action or a remote one pinned to a 40-hex SHA.

    The owner turned on GitHub's "require actions pinned to a full commit SHA"
    policy on 2026-10-12, so a tag or branch ref (`@v4`, `@main`) would now fail
    the workflow outright, and a required check that cannot start never reports.
    `test_bom_emitted.py` already maps every SHA-pinned action into the BOM, but
    its regex matches only SHAs, so a tag-pinned action passed it silently. This
    is the converse, and it has a floor so finding nothing cannot pass.

    The actions' own nested `uses:` were checked by hand on 2026-10-12 at the
    pinned SHAs: `attest-build-provenance` pins `actions/attest`, and
    `gh-action-pypi-publish` pins `actions/setup-python` plus a local `./`
    action of its own; the other three are Node actions with none.
    """
    refs: list[tuple[str, str]] = []
    for workflow in _workflow_files():
        for match in _USES.finditer(workflow.read_text(encoding="utf-8")):
            refs.append((workflow.name, match.group("ref")))
    assert len(refs) >= 20, f"only {len(refs)} `uses:` found; the reader is broken"
    unpinned = [
        f"{name}: {ref}"
        for name, ref in refs
        if not ref.startswith("./") and not _PINNED.match(ref)
    ]
    assert not unpinned, (
        "these actions are not pinned to a full commit SHA, which the repository's "
        "Actions policy now refuses:\n  " + "\n  ".join(unpinned)
    )


#: The comment a SHA pin carries: the exact release tag that SHA is, `# v1.14.1`.
_EXACT_TAG_COMMENT: Final[re.Pattern[str]] = re.compile(
    r"@[0-9a-f]{40}\s+#\s*v\d+\.\d+\.\d+\s*$"
)


def test_every_sha_pin_names_the_exact_tag_it_is() -> None:
    """A pin's comment names an exact tag, never a moving one (2026-10-27 review, 2.6).

    `# v4` sat on a `v4.1.1` pin and `# release/v1`, a branch, on `v1.14.1`. A
    moving name reads as a version and says nothing about which one, so the next
    reader cannot check the SHA against it. Each comment was resolved with
    `git ls-remote https://github.com/<owner>/<repo> refs/tags/*` (annotated tags
    peeled with `^{}`) on 2026-10-27. This checks the shape; whether the SHA *is*
    that tag needs the network, and Dependabot rewrites both together.
    """
    lines = [
        (workflow.name, line.strip())
        for workflow in _workflow_files()
        for line in workflow.read_text(encoding="utf-8").splitlines()
        if re.search(r"uses:\s*\S+@[0-9a-f]{40}", line)
    ]
    assert len(lines) >= 20, f"only {len(lines)} SHA pins found; the reader is broken"
    vague = [
        f"{name}: {line}" for name, line in lines if not _EXACT_TAG_COMMENT.search(line)
    ]
    assert not vague, (
        "these SHA pins do not name the exact tag they are (`# vX.Y.Z`):\n  "
        + "\n  ".join(vague)
    )


def test_the_tag_comment_check_refuses_a_moving_name() -> None:
    """Non-triviality: the two shapes the review found are refused."""
    sha = "0f67c3f4856b2e3261c31976d6725780e5e4c373"
    assert _EXACT_TAG_COMMENT.search(f"uses: a/b@{sha} # v4.1.1")
    assert not _EXACT_TAG_COMMENT.search(f"uses: a/b@{sha} # v4")
    assert not _EXACT_TAG_COMMENT.search(f"uses: a/b@{sha} # release/v1")
    assert not _EXACT_TAG_COMMENT.search(f"uses: a/b@{sha}")


def test_no_workflow_cancels_a_release_a_publish_or_a_push() -> None:
    """Concurrency may cancel superseded pull-request runs only (2026-10-27, 2.7).

    A literal ``cancel-in-progress: true`` cancels every kind of run in its group,
    a push to ``main`` and a release among them, so it is refused outright; a
    workflow that cancels must say so in an expression that names
    ``pull_request``. The release and the publish queue runs for one tag rather
    than letting two upload into the same release at once, and never cancel.
    """
    texts = {w.name: w.read_text(encoding="utf-8") for w in _workflow_files()}
    blanket = [
        name
        for name, text in texts.items()
        if re.search(r"^\s*cancel-in-progress:\s*true\s*(#.*)?$", text, re.MULTILINE)
    ]
    assert not blanket, f"cancel every run in the group, pushes included: {blanket}"
    for name, text in texts.items():
        for match in re.finditer(r"cancel-in-progress:\s*\$\{\{(?P<e>[^}]*)\}\}", text):
            assert "pull_request" in match.group("e"), (name, match.group("e"))
    for name in ("release.yml", "publish-pypi.yml"):
        block = re.search(
            r"^concurrency:\n  group: (?P<g>[^\n]+)\n  cancel-in-progress: (?P<c>\S+)$",
            texts[name],
            re.MULTILINE,
        )
        assert block is not None, f"{name} has no workflow-level concurrency group"
        assert block.group("c") == "false", name
        assert "${{" in block.group("g"), f"{name}: the group must name the tag"


def test_the_pin_check_refuses_a_tag_ref() -> None:
    """Non-triviality: the patterns above reject the shapes they exist to reject."""
    assert not _PINNED.match("actions/checkout@v4")
    assert not _PINNED.match("actions/checkout@main")
    assert not _PINNED.match("actions/checkout@3d3c42e")
    assert _PINNED.match("actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1")
    found = _USES.search("      - uses: actions/checkout@v4 # comment\n")
    assert found is not None and found.group("ref") == "actions/checkout@v4"


def test_every_job_names_its_runner_image() -> None:
    """No job runs on a moving ``-latest`` label (2026-10-19 review, item 7).

    GitHub moves ``ubuntu-latest`` to a new Ubuntu on its own schedule. A job on it
    changes environment without a commit of ours, and the PyPI publish, which runs
    once per release, would meet the change at a release, the worst time.
    """
    labels: list[tuple[str, str]] = []
    for workflow in _workflow_files():
        for line in workflow.read_text(encoding="utf-8").splitlines():
            match = re.match(r"\s+runs-on:\s*(\S+)", line)
            if match:
                labels.append((workflow.name, match.group(1)))
    # Floor: the sweep read every job we have, not none of them.
    assert len(labels) >= 10, labels
    moving = [(name, label) for name, label in labels if label.endswith("-latest")]
    assert not moving, f"jobs on a moving runner label: {moving}"


# --- Every workflow, not only ci.yml (the follow-up review of 2026-10-27, item 7)


def _jobs(text: str) -> dict[str, str]:
    """Each job's text, keyed by its name: the lines under `jobs:` at two spaces."""
    lines = text.splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.rstrip() == "jobs:")
    jobs: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines[start + 1 :]:
        match = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", line)
        if match:
            current = match.group(1)
            jobs[current] = []
        elif current is not None:
            jobs[current].append(line)
    return {name: "\n".join(body) for name, body in jobs.items()}


def test_every_checkout_in_every_workflow_drops_its_token() -> None:
    """Item 1.4, across all workflows. ci.yml's own test held only ci.yml, so a
    release.yml or publish-pypi.yml checkout that kept its token would have been
    caught by the non-required zizmor job alone. The release job's one tag push
    passes its token for that push only, so no checkout needs to keep it."""
    checkouts = 0
    missing: list[str] = []
    for path in _workflow_files():
        lines = path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if not re.match(r"^\s*- uses: actions/checkout@", line):
                continue
            checkouts += 1
            indent = len(line) - len(line.lstrip(" "))
            block: list[str] = []
            for after in lines[i + 1 :]:
                here = len(after) - len(after.lstrip(" "))
                if after.strip() and here <= indent:
                    break
                block.append(after.strip())
            if "persist-credentials: false" not in block:
                missing.append(f"{path.name}:{i + 1}")
    # 15 checkouts across the six workflows on 2026-10-27.
    assert checkouts >= 14, checkouts
    assert not missing, f"checkouts that keep the token in .git/config: {missing}"


def test_no_job_that_can_publish_or_write_restores_a_cache() -> None:
    """Item 1.3, across all workflows: a job holding `id-token: write` or a
    `contents: write` restores no cache, since a cache is input another run
    wrote (zizmor: cache poisoning)."""
    privileged = 0
    offenders: list[str] = []
    for path in _workflow_files():
        for name, body in _jobs(path.read_text(encoding="utf-8")).items():
            if not re.search(r"^\s+(id-token|contents):\s*write\b", body, re.M):
                continue
            privileged += 1
            if re.search(r"^\s+cache:\s*\S", body, re.M) or "actions/cache@" in body:
                offenders.append(f"{path.name} job {name}")
    # release.yml's build-and-release and publish-pypi.yml's publish, at least.
    assert privileged >= 2, privileged
    assert not offenders, f"privileged jobs that restore a cache: {offenders}"


def test_the_cache_check_sees_a_cache_in_a_privileged_job() -> None:
    """The check above, fed the shape it refuses."""
    text = (
        "jobs:\n  publish:\n    permissions:\n      id-token: write\n    steps:\n"
        "      - uses: actions/setup-python@x\n        with:\n          cache: pip\n"
    )
    body = _jobs(text)["publish"]
    assert re.search(r"^\s+(id-token|contents):\s*write\b", body, re.M)
    assert re.search(r"^\s+cache:\s*\S", body, re.M)
