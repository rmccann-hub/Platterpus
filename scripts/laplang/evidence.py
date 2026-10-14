"""Evidence citations (HR-2 §6): files that live on a repository's `evidence` branch.

**Why this exists (HR-2, round 33's first task, agreed 2026-10-14).** Run evidence
moves off each default branch onto an orphan branch named `evidence`, append-only.
A lap then cites it as `<repo>@<evidence commit>:<path>` with its SHA-256, and the
default branch keeps `docs/evidence-manifest.tsv`, one row per file. Such a
citation is exempt from FROM-COMMIT and from the one-branch-per-side rule (§6a):
it resolves at the commit it names, which must be reachable from that repository's
`refs/heads/evidence`. A checker (§6b):

* treats `evidence` as a second ref of record, **for evidence citations only**;
* refuses one with no manifest row at the lap's FROM-COMMIT;
* fetches a missing commit by its hash into a temporary repository, never into
  the working clone (§7: a `--depth` fetch makes a full clone shallow);
* reports one it cannot fetch as unchecked, except in CI's evidence job
  (``HR2_EVIDENCE_STRICT=1``), which fails instead.

**What makes a citation an evidence citation here: its path has a manifest row**
in the cited repository's manifest at the commit the caller names (the lap's
FROM-COMMIT for the author's own tree, the peer's ref of record otherwise). A
citation of a commit that only the `evidence` branch reaches, with no row, is the
§6b refusal. Everything else falls through to the ordinary rules unchanged, so
nothing read before the move is read differently.

**The fetch is blobless.** `git fetch --depth 1 --filter=blob:none` brings the
commit and its trees; reading the one cited file then fetches that blob alone,
from the remote the fetch marked as a promisor (measured 2026-10-14 on a local
repository: 2 KiB fetched, not the whole commit). A depth-1 fetch of an evidence
commit WITHOUT the filter would download every file it holds, hundreds of MB.
"""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

from .gitio import run_git, run_git_bytes

MANIFEST_PATH: Final[str] = "docs/evidence-manifest.tsv"
HEADER: Final[str] = "path\tbytes\tsha256\tevidence_commit\tlast_default_commit"
EVIDENCE_BRANCH: Final[str] = "evidence"
STRICT_ENV: Final[str] = "HR2_EVIDENCE_STRICT"

_SHA40: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{40}$")
_SHA256: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{64}$")

Outcome = Literal["ok", "refused", "unchecked"]


@dataclass(frozen=True)
class Row:
    """One manifest row (HR-2 §4)."""

    path: str
    size: int
    sha256: str
    evidence_commit: str
    last_default_commit: str


@dataclass(frozen=True)
class Answer:
    """What resolving an evidence citation found. `data` is the cited file's
    bytes when it was read, so the caller can check a line range."""

    outcome: Outcome
    message: str = ""
    data: bytes | None = None


def strict() -> bool:
    """CI's evidence job: what cannot be fetched fails instead of going unchecked."""
    return os.environ.get(STRICT_ENV) == "1"


def parse_manifest(text: str) -> tuple[dict[str, Row], list[str]]:
    """The manifest's rows by path, and every way it breaks HR-2 §4.

    Never raises: a malformed manifest is a list of problems, and a row that
    cannot be read is left out of the map rather than guessed at.
    """
    problems: list[str] = []
    rows: dict[str, Row] = {}
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    else:
        problems.append("the manifest does not end with a newline")
    if not lines or lines[0] != HEADER:
        problems.append(f"the first line is not the header {HEADER!r}")
        return rows, problems
    previous = ""
    for number, line in enumerate(lines[1:], start=2):
        cells = line.split("\t")
        if len(cells) != 5:
            problems.append(f"line {number}: {len(cells)} cells, not 5")
            continue
        path, size, sha, commit, last = cells
        bad = []
        if not path or path.startswith("/") or ".." in path.split("/"):
            bad.append("path is not a plain repository path")
        if not size.isdigit():
            bad.append("bytes is not a whole number")
        if not _SHA256.match(sha):
            bad.append("sha256 is not 64 lowercase hex digits")
        if not _SHA40.match(commit):
            bad.append("evidence_commit is not a full 40-character commit")
        if last and not _SHA40.match(last):
            bad.append("last_default_commit is neither empty nor a full commit")
        if bad:
            problems.append(f"line {number} ({path}): " + "; ".join(bad))
            continue
        if path in rows:
            problems.append(f"line {number}: {path} has a second row")
            continue
        if path < previous:
            problems.append(f"line {number}: {path} is out of order (sorted by path)")
        previous = path
        rows[path] = Row(path, int(size), sha, commit, last)
    return rows, problems


def manifest_at(root: Path, commit: str) -> dict[str, Row] | None:
    """The manifest as it stands at `commit` in `root`, or None if it has none."""
    shown = run_git_bytes(root, "show", f"{commit}:{MANIFEST_PATH}")
    if shown is None or shown.returncode != 0:
        return None
    return parse_manifest(shown.stdout.decode("utf-8", errors="replace"))[0]


def _local_evidence_refs(root: Path) -> list[str]:
    """The refs in `root` that name an `evidence` branch, local or fetched."""
    listed = run_git(
        root,
        "for-each-ref",
        "--format=%(refname)",
        f"refs/heads/{EVIDENCE_BRANCH}",
        f"refs/remotes/*/{EVIDENCE_BRANCH}",
    )
    if listed is None or listed.returncode != 0:
        return []
    return [line.strip() for line in listed.stdout.splitlines() if line.strip()]


def on_local_evidence(root: Path, sha: str) -> bool:
    """Is `sha` reachable from an `evidence` branch this clone already holds?"""
    for ref in _local_evidence_refs(root):
        result = run_git(root, "merge-base", "--is-ancestor", sha, ref)
        if result is not None and result.returncode == 0:
            return True
    return False


class Fetcher:
    """Reads an evidence file by commit hash, fetching into a temporary bare
    repository when this clone does not hold the commit (HR-2 §6b, §7)."""

    def __init__(self) -> None:
        self._temps: dict[str, Path] = {}
        self._evidence_fetched: dict[str, bool] = {}

    def _remote_url(self, root: Path) -> str | None:
        got = run_git(root, "remote", "get-url", "origin")
        if got is None or got.returncode != 0 or not got.stdout.strip():
            return None
        return got.stdout.strip()

    def _temp_for(self, url: str) -> Path | str:
        if url in self._temps:
            return self._temps[url]
        try:
            path = Path(tempfile.mkdtemp(prefix="hr2-evidence-"))
        except OSError as exc:
            return f"no temporary repository could be made ({exc})"
        made = run_git(path, "init", "--bare", "-q", ".")
        added = run_git(path, "remote", "add", "origin", url)
        if (
            made is None
            or made.returncode != 0
            or added is None
            or added.returncode != 0
        ):
            return "git could not set up a temporary repository"
        self._temps[url] = path
        return path

    def read(self, root: Path, sha: str, path: str) -> bytes | str:
        """The bytes of `path` at `sha`, or why they could not be read."""
        local = run_git_bytes(root, "show", f"{sha}:{path}")
        if local is not None and local.returncode == 0:
            return local.stdout
        url = self._remote_url(root)
        if url is None:
            return f"{sha} is not in this clone and it has no origin to fetch from"
        temp = self._temp_for(url)
        if isinstance(temp, str):
            return temp
        fetched = run_git(
            temp, "fetch", "-q", "--depth", "1", "--filter=blob:none", "origin", sha
        )
        if fetched is None or fetched.returncode != 0:
            said = (fetched.stderr.strip().splitlines() or [""])[-1] if fetched else ""
            return f"could not fetch {sha} from {url} ({said or 'no answer'})"
        shown = run_git_bytes(temp, "show", f"{sha}:{path}")
        if shown is None or shown.returncode != 0:
            return f"{path} does not exist at {sha}"
        return shown.stdout

    def reachable_from_evidence(self, root: Path, sha: str) -> bool | str:
        """Is `sha` on the cited repository's `evidence` branch? True, False, or
        why it could not be told."""
        if on_local_evidence(root, sha):
            return True
        url = self._remote_url(root)
        if url is None:
            return "this clone has no origin to read the evidence branch from"
        temp = self._temp_for(url)
        if isinstance(temp, str):
            return temp
        if not self._evidence_fetched.get(url):
            fetched = run_git(
                temp,
                "fetch",
                "-q",
                "--filter=blob:none",
                "origin",
                f"+refs/heads/{EVIDENCE_BRANCH}:refs/heads/{EVIDENCE_BRANCH}",
            )
            if fetched is None or fetched.returncode != 0:
                return f"could not fetch the {EVIDENCE_BRANCH} branch from {url}"
            self._evidence_fetched[url] = True
        result = run_git(temp, "merge-base", "--is-ancestor", sha, EVIDENCE_BRANCH)
        if result is None:
            return "git did not answer"
        return result.returncode == 0


def check_citation(
    fetcher: Fetcher, root: Path, row: Row, sha: str, label: str
) -> Answer:
    """Resolve an evidence citation whose path has manifest row `row` (§6a, §6b)."""
    data = fetcher.read(root, sha, row.path)
    if isinstance(data, str):
        return _unfetchable(f"{label}: {data}")
    got = hashlib.sha256(data).hexdigest()
    if got != row.sha256:
        return Answer(
            "refused",
            f"{label}: the file at {sha[:12]} hashes {got[:16]}…, its manifest row "
            f"says {row.sha256[:16]}…",
        )
    on_branch = fetcher.reachable_from_evidence(root, sha)
    if isinstance(on_branch, str):
        return _unfetchable(f"{label}: {on_branch}", data)
    if not on_branch:
        return Answer(
            "refused",
            f"{label}: {sha[:12]} is not reachable from refs/heads/{EVIDENCE_BRANCH} "
            "(HR-2 §6a)",
        )
    return Answer("ok", data=data)


def _unfetchable(message: str, data: bytes | None = None) -> Answer:
    if strict():
        return Answer("refused", f"{message} (CI's evidence job fails on this)")
    return Answer("unchecked", f"UNCHECKED {message}", data)
