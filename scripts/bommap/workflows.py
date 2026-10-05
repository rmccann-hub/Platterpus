"""What each `.github/workflows/*.yml` declares: actions, runners, and the
packages its jobs `pip install` and `apt-get install`.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from functools import cache
from typing import Final

from bommap.model import _REPO_ROOT
from bommap.reading import _logical_lines, _rel


@dataclass
class _Workflow:
    """What one ``.github/workflows/*.yml`` file declares, by job.

    Read with line-level regexes rather than a YAML parser on purpose: PyYAML is
    not a dependency of this project, and adding one needs the maintainer's
    approval. The shapes read here (``uses:``, ``runs-on:``, ``pip install``,
    ``apt-get install``) are single-line by construction.
    """

    rel: str
    #: (job, action, ref, version comment)
    uses: list[tuple[str, str, str, str]] = field(default_factory=list)
    #: (job, runner label)
    runners: list[tuple[str, str]] = field(default_factory=list)
    #: (job, requirement text)
    pip: list[tuple[str, str]] = field(default_factory=list)
    #: (job, Debian package)
    apt: list[tuple[str, str]] = field(default_factory=list)


_JOB_LINE: Final[re.Pattern[str]] = re.compile(r"^  (?P<job>[A-Za-z0-9_-]+):\s*$")


_USES: Final[re.Pattern[str]] = re.compile(
    r"uses:\s*(?P<action>[^@\s]+)@(?P<ref>\S+)(?:\s+#\s*(?P<comment>.*\S))?"
)


_RUNS_ON: Final[re.Pattern[str]] = re.compile(r"^\s*runs-on:\s*(?P<label>\S+)\s*$")


_PIP_INSTALL: Final[re.Pattern[str]] = re.compile(r"\bpip\s+install\s+(?P<rest>.*)$")


_APT_INSTALL: Final[re.Pattern[str]] = re.compile(
    r"\bapt-get\b(?:\s+\"\$\{opts\[@\]\}\")?\s+install\s+(?P<rest>.*)$"
)


#: Tokens that end a shell command inside a ``run:`` line.
_COMMAND_END: Final[frozenset[str]] = frozenset({"&&", "||", ";", "then", "|"})


def _command_tokens(rest: str) -> list[str]:
    """The words of one command, stopping at the first ``&&`` / ``;`` / ``then``."""
    try:
        words = shlex.split(rest, comments=False, posix=True)
    except ValueError:
        words = rest.split()
    tokens: list[str] = []
    for word in words:
        if word in _COMMAND_END:
            break
        if word.endswith(";"):
            tokens.append(word[:-1])
            break
        tokens.append(word)
    return tokens


@cache
def workflows() -> tuple[_Workflow, ...]:
    out: list[_Workflow] = []
    for path in sorted((_REPO_ROOT / ".github" / "workflows").glob("*.yml")):
        flow = _Workflow(rel=_rel(path))
        in_jobs = False
        job = ""
        for line in _logical_lines(path.read_text(encoding="utf-8")):
            if line.startswith("jobs:"):
                in_jobs = True
                continue
            if in_jobs and (match := _JOB_LINE.match(line)):
                job = match.group("job")
                continue
            if match := _USES.search(line):
                flow.uses.append(
                    (
                        job,
                        match.group("action"),
                        match.group("ref"),
                        match.group("comment") or "",
                    )
                )
            if match := _RUNS_ON.match(line):
                flow.runners.append((job, match.group("label")))
            if match := _PIP_INSTALL.search(line):
                tokens = _command_tokens(match.group("rest"))
                skip_next = False
                for token in tokens:
                    if skip_next:
                        skip_next = False
                        continue
                    if token in {"-e", "-r", "-c", "--requirement", "--constraint"}:
                        skip_next = True
                        continue
                    # Flags, `.`/`.[dev]` (the project itself, listed elsewhere) and
                    # `"$spec"` (a pin read OUT of pyproject.toml at run time, so it
                    # is the pyproject entry this map already carries).
                    if token.startswith(("-", ".", "$")) or "/" in token:
                        continue
                    flow.pip.append((job, token))
            if match := _APT_INSTALL.search(line):
                for token in _command_tokens(match.group("rest")):
                    if token.startswith("-") or token.startswith("$"):
                        continue
                    flow.apt.append((job, token))
        out.append(flow)
    return tuple(out)


def _where(rel: str, job: str) -> str:
    return f"{rel} ({job})" if job else rel
