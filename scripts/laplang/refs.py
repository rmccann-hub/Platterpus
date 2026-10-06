"""References in an LSL lap, and resolving them against the two trees.

The spec's forms (§"References"):

* an artifact, `<side>@<sha>:<path>[:<line>[-<line>]]`. It always names a
  commit, so a branch name never parses as one;
* a command and its output, `run: <command> => <result>`;
* a statement, `S<n>` in this lap or `<side>:R<round>.L<lap>.S<n>` in another;
* a section of a prose lap, `<side>:R<round>.L<lap>.§<section>`.

**"Our tree" means the tree of the lap's author.** The spec says a `DID` names
"a SHA on our publishing branch" and a measured fact needs "an artifact we
produced", and in a lap Platterpus wrote, *we* is Platterpus. The fork's checker
reads *we* as cyanrip whoever wrote the lap. Measured 2026-09-26: a correct
Platterpus lap was refused twice, once for its own commit and once for its own
measurement.

**A shallow clone cannot show that a commit does not exist.** Its missing
history is a fact about the clone, not about the commit, so that case is
reported as *could not check* rather than refused. (Measured the same day: the
fork's own lap 6, checked by their checker in a depth-1 clone of their own
tree, drew 15 refusals.)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

from .gitio import decode_cited, run_git, run_git_bytes
from .model import Side

ARTIFACT_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?P<side>cyanrip|platterpus)@(?P<sha>[0-9a-f]{7,40}):(?P<path>[^\s:]+)"
    r"(?::(?P<first>\d+)(?:-(?P<last>\d+))?)?$"
)
STATEMENT_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?:(?P<side>cyanrip|platterpus):R(?P<round>\d+)\.L(?P<lap>\d+)\.)?"
    r"(?P<target>S\d+|§[A-Za-z0-9.]+)$"
)
SHA_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{7,40}$")


@dataclass(frozen=True)
class ArtifactRef:
    side: Side
    sha: str
    path: str
    first: int | None
    last: int | None


@dataclass(frozen=True)
class StatementRef:
    """`side`, `round` and `lap` are None for a statement of this lap."""

    side: Side | None
    round: int | None
    lap: int | None
    target: str

    @property
    def is_section(self) -> bool:
        return self.target.startswith("§")

    @property
    def number(self) -> int | None:
        return int(self.target[1:]) if not self.is_section else None


def parse_artifact(token: str) -> ArtifactRef | None:
    match = ARTIFACT_RE.match(token)
    if match is None:
        return None
    side: Side = "cyanrip" if match["side"] == "cyanrip" else "platterpus"
    return ArtifactRef(
        side=side,
        sha=match["sha"],
        path=match["path"],
        first=int(match["first"]) if match["first"] else None,
        last=int(match["last"]) if match["last"] else None,
    )


def parse_statement(token: str) -> StatementRef | None:
    match = STATEMENT_RE.match(token)
    if match is None:
        return None
    side: Side | None = None
    if match["side"] is not None:
        side = "cyanrip" if match["side"] == "cyanrip" else "platterpus"
    return StatementRef(
        side=side,
        round=int(match["round"]) if match["round"] else None,
        lap=int(match["lap"]) if match["lap"] else None,
        target=match["target"],
    )


def tokens(value: str) -> list[str]:
    """A list-valued field's items: `S1, S2 S3` is three."""
    return [t for t in re.split(r"[,\s]+", value.strip()) if t]


def first_token(value: str) -> str:
    parts = value.split()
    return parts[0] if parts else ""


def is_run(value: str) -> bool:
    return value.startswith("run: ")


#: What resolving a reference found. `unchecked` is not a pass. `offrecord` means
#: the commit resolves, but only from a branch other than the side's ref of record,
#: so a lap citing it holds only while that branch exists.
Outcome = Literal["ok", "refused", "unchecked", "offrecord"]


@dataclass(frozen=True)
class Resolution:
    outcome: Outcome
    message: str = ""


class Trees:
    """The two repositories, and the ref each side publishes from.

    `roots` maps a side to a clone of its tree, or None when none was given. An
    artifact in a tree we were not given is reported unchecked, never passed.
    """

    def __init__(self, roots: dict[Side, Path | None], at: dict[Side, str]) -> None:
        self.roots = roots
        self.at = at
        self._cache: dict[
            tuple[Side, str, str, bool], Resolution | tuple[int, Resolution]
        ] = {}
        self._shallow: dict[Side, bool] = {}

    def artifact(self, ref: ArtifactRef, author: Side | None) -> Resolution:
        """Resolve `ref`. It must be reachable from the author's publishing ref
        when it is in the author's own tree."""
        root = self.roots.get(ref.side)
        if root is None:
            return Resolution(
                "unchecked",
                f"UNCHECKED {ref.side}@{ref.sha}:{ref.path}: no clone of that tree "
                "was given (--peer)",
            )
        must_reach = ref.side == author
        key = (ref.side, ref.sha, ref.path, must_reach)
        if key not in self._cache:
            self._cache[key] = self._resolve_path(root, ref, must_reach)
        got = self._cache[key]
        if isinstance(got, Resolution):
            return got
        line_count, reach = got
        lines = _check_lines(ref, line_count)
        return lines if lines.outcome != "ok" else reach

    def commit(self, side: Side, sha: str) -> Resolution:
        """Resolve a `DID` commit: it must be on `side`'s publishing ref."""
        root = self.roots.get(side)
        if root is None:
            return Resolution(
                "unchecked",
                f"UNCHECKED commit {sha}: no clone of {side}'s tree was given",
            )
        found = self._commit_exists(root, side, sha)
        if found.outcome != "ok":
            return found
        return self._reachable(root, side, sha)

    def _resolve_path(
        self, root: Path, ref: ArtifactRef, must_reach: bool
    ) -> Resolution | tuple[int, Resolution]:
        found = self._commit_exists(root, ref.side, ref.sha)
        if found.outcome != "ok":
            return found
        reach = Resolution("ok")
        if must_reach:
            reach = self._reachable(root, ref.side, ref.sha)
            if reach.outcome in ("refused", "unchecked"):
                return reach
        # Read as BYTES and decoded here, not by `text=True`: a cited file is
        # not always UTF-8. EAC writes its logs in UTF-16, and the first lap to
        # cite one (our round 30 lap 16, EAC's own log of the reference disc)
        # made this line raise UnicodeDecodeError and took the whole check down
        # with it. See `gitio.decode_cited`.
        shown = run_git_bytes(root, "show", f"{ref.sha}:{ref.path}")
        if shown is None:
            return Resolution(
                "unchecked", f"UNCHECKED {ref.side}@{ref.sha}: git did not answer"
            )
        if shown.returncode != 0:
            return Resolution(
                "refused", f"{ref.path} does not exist at {ref.side}@{ref.sha}"
            )
        return (line_count(decode_cited(shown.stdout)), reach)

    def _commit_exists(self, root: Path, side: Side, sha: str) -> Resolution:
        result = run_git(root, "rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}")
        if result is None:
            return Resolution(
                "unchecked", f"UNCHECKED {side}@{sha}: git did not answer"
            )
        if result.returncode == 0:
            return Resolution("ok")
        if self._is_shallow(root, side):
            return Resolution(
                "unchecked",
                f"UNCHECKED {side}@{sha}: not in this clone, and the clone is "
                "shallow, so its absence proves nothing",
            )
        return Resolution("refused", f"commit {sha} does not resolve in {side}'s tree")

    def _reachable(self, root: Path, side: Side, sha: str) -> Resolution:
        """Is `sha` on `side`'s ref of record, on some other branch, or nowhere?

        The spec asks that a commit be reachable *"so a fresh clone can resolve
        it"*, and both checkers first read that as "reachable from HEAD". For a
        repository that squash-merges, those differ. A Platterpus lap is written
        on a `claude/` branch and cites that branch's commits, and a squash merge
        puts a new commit on `main`, never those. A fresh clone still resolves
        them, from the branch, but only while the branch exists. So there are
        three answers, not two: on the ref of record (fine), on another branch
        only (a warning, `offrecord`), or on nothing (refused). Found 2026-09-26,
        when `main`'s CI refused the worked example that the PR's CI had passed.
        The same day, session branches began merging into `main` with a merge
        commit, so an off-record commit now reaches the record at the merge. The
        warning still applies to any lap read before that merge.
        """
        at = self.at.get(side, "HEAD")
        on_record = run_git(root, "merge-base", "--is-ancestor", sha, at)
        if on_record is None:
            return Resolution(
                "unchecked", f"UNCHECKED {side}@{sha}: git did not answer"
            )
        if on_record.returncode == 0:
            return Resolution("ok")
        if on_record.returncode != 1:
            return Resolution(
                "unchecked", f"UNCHECKED {side}@{sha}: {at} does not resolve"
            )
        holders = run_git(root, "branch", "-r", "--contains", sha)
        names = [
            line.strip().split(" ")[0]
            for line in (holders.stdout.splitlines() if holders is not None else [])
            if line.strip() and "->" not in line
        ]
        if names:
            return Resolution(
                "offrecord",
                f"commit {sha} is on {', '.join(names[:3])} but not on {side}'s "
                f"{at}; a lap citing it holds only while that branch exists",
            )
        return Resolution(
            "refused",
            f"commit {sha} is on no branch of {side}'s tree, so a fresh clone "
            "cannot resolve it",
        )

    def _is_shallow(self, root: Path, side: Side) -> bool:
        if side not in self._shallow:
            result = run_git(root, "rev-parse", "--is-shallow-repository")
            self._shallow[side] = result is None or result.stdout.strip() != "false"
        return self._shallow[side]


def line_count(text: str) -> int:
    """How many lines a citation can name in `text`: its newlines, plus one for a
    final line that has none.

    Counting newlines alone said a one-line file without a final newline "has 0
    lines", so its only line could not be cited. Four files of the round 29
    bundle end that way as delivered, the host export's one-line banner among
    them. Our round 29 lap 4 S33 proposed counting the unterminated last line;
    the fork accepted it (their round 30 lap 1 S20), and both checkers change in
    round 30.
    """
    return text.count("\n") + (1 if text and not text.endswith("\n") else 0)


def _check_lines(ref: ArtifactRef, line_count: int) -> Resolution:
    if ref.first is None:
        return Resolution("ok")
    last = ref.last if ref.last is not None else ref.first
    if ref.first < 1 or last < ref.first:
        return Resolution(
            "refused", f"line range {ref.first}-{ref.last} is not a range"
        )
    if last > line_count:
        return Resolution(
            "refused",
            f"{ref.side}@{ref.sha}:{ref.path} has {line_count} lines; line {last} "
            "does not exist",
        )
    return Resolution("ok")


def default_at(root: Path | None, candidates: tuple[str, ...]) -> str:
    """The first of `candidates` that resolves in `root`, else `HEAD`."""
    if root is None:
        return "HEAD"
    for name in candidates:
        result = run_git(root, "rev-parse", "--verify", "--quiet", f"{name}^{{commit}}")
        if result is not None and result.returncode == 0:
            return name
    return "HEAD"
