"""The typed atoms a lap is written in.

Each check returns None when a value is well formed, or a short phrase naming
what was expected, so an error message can say what to write instead.
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Callable
from typing import Final

#: The two parties, spelled as `HANDSHAKE-FROM` spells them. One spelling each.
PARTIES: Final[frozenset[str]] = frozenset({"cyanrip-fork", "platterpus"})
#: Repository names as a citation spells them (`cyanrip@<sha>:<path>:<line>`).
REPOS: Final[frozenset[str]] = frozenset({"cyanrip", "platterpus"})
VERDICTS: Final[frozenset[str]] = frozenset({"OPEN", "HOLD", "GO", "WITHDRAWN"})
#: The longest free-text attribute value, in words.
MAX_ATTRIBUTE_WORDS: Final[int] = 60

# ---------------------------------------------------------------------------
# Value types. Each returns None when the value is well formed, or a short
# phrase naming what was expected. Plain functions, so a test can call one.
# ---------------------------------------------------------------------------

Check = Callable[[str], str | None]

SHA: Final[str] = r"[0-9a-f]{7,40}"
HEX64: Final[str] = r"[0-9a-f]{64}"
VERSION: Final[str] = r"[0-9][0-9A-Za-z.+~-]*"
LAPFILE: Final[str] = r"round-(?P<r>[0-9]{2})-lap-(?P<l>[0-9]{2})\.md"

REF: Final[re.Pattern[str]] = re.compile(
    r"(?:r(?P<round>[1-9][0-9]*)l(?P<lap>[1-9][0-9]*))?#(?P<sid>[A-Z][1-9][0-9]{0,2})"
)
CITE: Final[re.Pattern[str]] = re.compile(
    rf"(?P<repo>[a-z-]+)@(?P<sha>{SHA}):(?P<path>[^\s:]+)"
    r"(?::(?P<l1>[1-9][0-9]*)(?:-(?P<l2>[1-9][0-9]*))?)?"
)
ANCHOR: Final[re.Pattern[str]] = re.compile(
    rf"sha256:(?P<hex>{HEX64}) (?P<bytes>[1-9][0-9]*) bytes"
    rf"(?: at (?P<at>[a-z-]+@{SHA}:[^\s:]+))?"
)


def words(text: str) -> int:
    return len(re.findall(r"\S+", text))


def check_text(value: str) -> str | None:
    if not value.strip():
        return "non-empty text"
    if words(value) > MAX_ATTRIBUTE_WORDS:
        return f"at most {MAX_ATTRIBUTE_WORDS} words (a longer point is a statement)"
    return None


def check_int(value: str) -> str | None:
    return None if re.fullmatch(r"[1-9][0-9]*", value) else "a positive integer"


def check_party(value: str) -> str | None:
    return None if value in PARTIES else "`cyanrip-fork` or `platterpus`"


def check_parties(value: str) -> str | None:
    items = value.split(", ")
    if any(i not in PARTIES for i in items) or len(set(items)) != len(items):
        return "parties separated by `, `, each once"
    return None


def check_verdict(value: str) -> str | None:
    return None if value in VERDICTS else "one of OPEN, HOLD, GO, WITHDRAWN"


def check_sha(value: str) -> str | None:
    return (
        None if re.fullmatch(SHA, value) else "a lowercase hex commit, 7 to 40 digits"
    )


def check_sha_or_none(value: str) -> str | None:
    return None if value == "none" else check_sha(value)


def check_url(value: str) -> str | None:
    ok = re.fullmatch(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value)
    return None if ok else "a repository URL, https://github.com/<owner>/<repo>"


def check_urls(value: str) -> str | None:
    return (
        None
        if all(check_url(v) is None for v in value.split(", "))
        else ("repository URLs separated by `, `")
    )


def check_app(value: str) -> str | None:
    return (
        None
        if re.fullmatch(rf"platterpus {VERSION}", value)
        else ("`platterpus <version>`")
    )


def check_banner(value: str) -> str | None:
    ok = re.fullmatch(rf"cyanrip {VERSION} \([^()\s]+\)", value)
    return None if ok else "the banner verbatim: `cyanrip <version> (<build tag>)`"


def check_build(value: str) -> str | None:
    ok = re.fullmatch(rf"(?:cyanrip|platterpus) {VERSION}", value)
    return None if ok else "`cyanrip <version>` or `platterpus <version>`"


def check_builds(value: str) -> str | None:
    return (
        None
        if all(check_build(v) is None for v in value.split(", "))
        else ("builds separated by `, `")
    )


def check_build_or_none(value: str) -> str | None:
    return None if value == "none" else check_build(value)


def check_version(value: str) -> str | None:
    ok = re.fullmatch(rf"(?:(?:cyanrip|platterpus) )?{VERSION}", value)
    return None if ok else "a version, optionally after the program's name"


def check_ref(value: str) -> str | None:
    return (
        None if REF.fullmatch(value) else "a statement reference, `#C1` or `r27l4#Q2`"
    )


def check_refs(value: str) -> str | None:
    items = value.split(", ")
    if not items or any(REF.fullmatch(i) is None for i in items):
        return "statement references separated by `, `"
    if len(set(items)) != len(items):
        return "each reference once"
    return None


def check_refs_or_none(value: str) -> str | None:
    return None if value == "none" else check_refs(value)


def check_cite(value: str, *, need_line: bool = False) -> str | None:
    m = CITE.fullmatch(value)
    if m is None or m.group("repo") not in REPOS:
        return "a citation, `<cyanrip|platterpus>@<sha>:<path>[:<line>[-<line>]]`"
    if need_line and m.group("l1") is None:
        return "a citation with a line, `<repo>@<sha>:<path>:<line>`"
    if m.group("l2") is not None and int(m.group("l2")) < int(m.group("l1")):
        return "a line range that does not run backwards"
    return None


def check_cite_line(value: str) -> str | None:
    return check_cite(value, need_line=True)


def check_anchor(value: str) -> str | None:
    m = ANCHOR.fullmatch(value)
    if m is None:
        return "an anchor, `sha256:<64 hex> <n> bytes [at <repo>@<sha>:<path>]`"
    at = m.group("at")
    if at is not None and check_cite(at) is not None:
        return "an anchor whose `at` hint is a citation of a real repository"
    return None


def check_location(value: str) -> str | None:
    if check_cite(value) is None or check_anchor(value) is None:
        return None
    return "a citation or an anchor"


def check_date(value: str) -> str | None:
    try:
        dt.date.fromisoformat(value)
    except ValueError:
        return "a date, YYYY-MM-DD"
    return (
        None
        if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value)
        else "a date, YYYY-MM-DD"
    )


def check_datetime(value: str) -> str | None:
    if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", value):
        try:
            dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return "a UTC time, YYYY-MM-DDTHH:MM:SSZ"
        return None
    return "a UTC time, YYYY-MM-DDTHH:MM:SSZ"


def check_yes_no(value: str) -> str | None:
    return None if value in {"yes", "no"} else "`yes` or `no`"


def check_examined(value: str) -> str | None:
    ok = re.fullmatch(r"[1-9][0-9]* [^,]+, (?:closed|open)", value)
    return (
        None
        if ok
        else (
            "what was examined: `<count ≥ 1> <unit>, closed` or `…, open` "
            "(a measurement of nothing is not one)"
        )
    )


def check_operator(value: str) -> str | None:
    return (
        None if re.fullmatch(r"operator \([^()]+\)", value) else "`operator (<name>)`"
    )


def check_operator_date(value: str) -> str | None:
    m = re.fullmatch(r"operator \([^()]+\), (?P<date>\S+)", value)
    if m is None or check_date(m.group("date")) is not None:
        return "`operator (<name>), <YYYY-MM-DD>`"
    return None


def check_restates(value: str) -> str | None:
    """`§<section> of <anchor>`: which condition of which (legacy) lap 1."""
    m = re.fullmatch(r"§[0-9A-Za-z.]+ of (?P<anchor>.+)", value)
    if m is None or check_anchor(m.group("anchor")) is not None:
        return "`§<section> of sha256:<64 hex> <n> bytes at <repo>@<sha>:<path>`"
    return None


def check_answer_target(value: str) -> str | None:
    """A statement reference, or `§<section> of <anchor>` for a lap written
    before the language, which has no statements to point at."""
    if check_ref(value) is None or check_restates(value) is None:
        return None
    return "a reference to a QUESTION, or `§<section> of <anchor>` for an older lap"


def check_due(value: str) -> str | None:
    if re.fullmatch(r"(?:round [1-9][0-9]* )?lap [1-9][0-9]*", value):
        return None
    if check_date(value) is None:
        return None
    return "`lap <n>`, `round <r> lap <n>`, or a date"
