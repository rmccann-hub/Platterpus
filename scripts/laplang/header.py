"""The header of a language-1 lap: every field it may carry, and each field's type."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Final

from .model import Problem
from .values import (
    HEX64,
    LAPFILE,
    PARTIES,
    SHA,
    Check,
    check_app,
    check_banner,
    check_build,
    check_build_or_none,
    check_builds,
    check_date,
    check_datetime,
    check_int,
    check_operator_date,
    check_parties,
    check_party,
    check_refs,
    check_refs_or_none,
    check_sha,
    check_sha_or_none,
    check_url,
    check_urls,
    check_verdict,
    check_version,
)

#: The field a lap declares to opt in, and the only version this checker speaks.
LANGUAGE_FIELD: Final[str] = "HANDSHAKE-LANGUAGE"
LANGUAGE_VERSION: Final[str] = "1"
#: v6 fields whose value is free text by design (an override's reason, in the
#: operator's words) are still not paragraphs.
MAX_FREE_HEADER_CHARS: Final[int] = 300
#: Experimental `HANDSHAKE-X-*` fields are untyped, and short.
MAX_EXPERIMENTAL_CHARS: Final[int] = 120


def check_next_lap(value: str) -> str | None:
    if value == "none":
        return None
    m = re.fullmatch(r"(?P<lap>[1-9][0-9]*) (?P<party>\S+)", value)
    if m is None or m.group("party") not in PARTIES:
        return "`<lap number> <party>`, or `none` when this side expects no further lap"
    return None


def check_ready(value: str) -> str | None:
    if value == "no":
        return None
    m = re.fullmatch(r"yes — operator \([^()]+\), (?P<date>\S+)", value)
    if m is None or check_date(m.group("date")) is not None:
        return "`no`, or `yes — operator (<name>), <YYYY-MM-DD>`"
    return None


def check_confirmed(value: str) -> str | None:
    if value == "yes":
        return None
    m = re.fullmatch(r"no (?P<build>.+)", value)
    if m is None or check_build(m.group("build")) is not None:
        return "`yes`, or `no <the build we actually are>`"
    return None


def check_opener(value: str) -> str | None:
    # v6 §1a spells the provider `cyanrip`, where HANDSHAKE-FROM spells it
    # `cyanrip-fork`. Two spellings of one party is a v6 wart; the proposal asks
    # v7 to settle on one. Until then the v6 spelling stays legal here.
    return (
        None
        if value in {"cyanrip", "platterpus"}
        else "`cyanrip` or `platterpus` (v6 §1a)"
    )


def check_held(value: str) -> str | None:
    if value == "none":
        return None
    item = rf"{LAPFILE} \((?:OPEN|HOLD|GO|WITHDRAWN)\) sha256:{HEX64} [1-9][0-9]* bytes"
    items = value.split(", ")
    if all(re.fullmatch(item, i) for i in items):
        return None
    return "`none`, or `round-RR-lap-NN.md (<VERDICT>) sha256:<64 hex> <n> bytes`, separated by `, `"


def check_observed(value: str) -> str | None:
    if value == "none":
        return None
    item = rf"{LAPFILE} \(READY-TO-READ: no\) at [a-z-]+@{SHA}"
    if all(re.fullmatch(item, i) for i in value.split(", ")):
        return None
    return "`none`, or `round-RR-lap-NN.md (READY-TO-READ: no) at <repo>@<sha>`, separated by `, `"


def check_digest(value: str) -> str | None:
    ok = re.fullmatch(r"sha256/16 = [0-9a-f]{16} over [0-9]+ lap\(s\)", value)
    return None if ok else "`sha256/16 = <16 hex> over <n> lap(s)`"


def check_source_anchor(value: str) -> str | None:
    return (
        None
        if re.fullmatch(r"sha256/16 = [0-9a-f]{16}", value)
        else "`sha256/16 = <16 hex>`"
    )


def check_peer_source(value: str) -> str | None:
    """`lap <n> round-RR-lap-NN.md sha256:<hex> <bytes> bytes`, or `none`.

    Both gates as they stand read this value identically: ours takes the filename
    first, the fork's takes the first `lap N`, and this form puts both in agreement
    at the front. The checker holds `n` and `NN` equal, so neither reading can see
    a different lap from the other.
    """
    if value == "none":
        return None
    m = re.fullmatch(
        rf"lap (?P<n>[1-9][0-9]*) {LAPFILE} sha256:{HEX64} [1-9][0-9]* bytes", value
    )
    if m is None:
        return "`none`, or `lap <n> round-RR-lap-NN.md sha256:<64 hex> <n> bytes`"
    if int(m.group("n")) != int(m.group("l")):
        return "the lap number and the filename's lap number to be the same lap"
    return None


def check_shared_hashes(value: str) -> str | None:
    item = rf"[a-z][a-z-]*(?:\(v[1-9][0-9]*\))?={HEX64}"
    if all(re.fullmatch(item, i) for i in value.split(" ")):
        return None
    return "`<name>[(v<n>)]=<64 hex>` entries separated by single spaces"


def check_free(value: str) -> str | None:
    if not value.strip():
        return "a value"
    if len(value) > MAX_FREE_HEADER_CHARS:
        return f"at most {MAX_FREE_HEADER_CHARS} characters; the rest is a statement"
    return None


def check_language(value: str) -> str | None:
    return None if value == LANGUAGE_VERSION else f"`{LANGUAGE_VERSION}`"


def check_contract(value: str) -> str | None:
    ok = re.fullmatch(rf"[A-Za-z0-9_./-]+\.md @ {SHA}", value)
    return None if ok else "`<path>.md @ <sha>`"


#: Declared fields that do not carry the `HANDSHAKE-` prefix. v6 §6 defines
#: `PROVIDER-CONTRACT`; the other three are in use on both sides (33 laps since
#: round 20 carry the two version fields). They are part of the header block
#: like any other field, so they are listed here rather than matched by shape.
UNPREFIXED_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "PROVIDER-CONTRACT",
        "CONSUMER-CONTRACT",
        "SEAM-RULES-VERSION",
        "OWNERSHIP-VERSION",
    }
)


# ---------------------------------------------------------------------------
# The header table: every field a language-1 lap may carry, and its type.
# A field not here is either retired (with its replacement named) or refused.
# `HANDSHAKE-X-*` is the escape hatch for trying a field out.
# ---------------------------------------------------------------------------

HEADER_TYPES: Final[dict[str, Check]] = {
    "HANDSHAKE-PROTOCOL": check_int,
    "HANDSHAKE-LANGUAGE": check_language,
    "HANDSHAKE-ROUND": check_int,
    "HANDSHAKE-LAP": check_int,
    "HANDSHAKE-FROM": check_party,
    "HANDSHAKE-TO": check_parties,
    "HANDSHAKE-OPENER": check_opener,
    "HANDSHAKE-FROM-REPO": check_url,
    "HANDSHAKE-FROM-COMMIT": check_sha,
    "HANDSHAKE-FROM-COMMIT-SOURCE": check_refs,
    "HANDSHAKE-FROM-VERSION": check_version,
    "HANDSHAKE-TO-REPO": check_urls,
    "HANDSHAKE-TO-VERSION": check_builds,
    "HANDSHAKE-TO-VERSION-CONFIRMED": check_confirmed,
    "HANDSHAKE-VERDICT": check_verdict,
    "HANDSHAKE-VERDICT-SOURCE": check_refs,
    "HANDSHAKE-PEER-VERDICT": check_verdict,
    "HANDSHAKE-PEER-VERDICT-SOURCE": check_peer_source,
    "HANDSHAKE-APP-VERSION": check_app,
    "HANDSHAKE-RIPPER-VERSION": check_banner,
    "HANDSHAKE-PIN": check_sha,
    "HANDSHAKE-PIN-POLICY": check_refs,
    "HANDSHAKE-CANDIDATE": check_build_or_none,
    "HANDSHAKE-CANDIDATE-SOURCE": check_refs,
    "HANDSHAKE-TEST-PIN": check_sha_or_none,
    "HANDSHAKE-TEST-PIN-SOURCE": check_refs,
    "HANDSHAKE-OUR-VERSION": check_build,
    "HANDSHAKE-OUR-PIN": check_sha,
    "HANDSHAKE-OUR-PIN-SOURCE": check_refs,
    "HANDSHAKE-PEER-VERSION": check_build,
    "HANDSHAKE-PEER-PIN": check_sha,
    "HANDSHAKE-PEER-PIN-SOURCE": check_refs,
    "HANDSHAKE-PEER-VERSION-SOURCE": check_refs,
    "HANDSHAKE-TESTED": check_refs_or_none,
    "HANDSHAKE-BREAKING": check_refs_or_none,
    "HANDSHAKE-OVERRIDE": check_free,
    "HANDSHAKE-OVERRIDE-BY": check_operator_date,
    "HANDSHAKE-OVERRIDE-WHY": check_free,
    "HANDSHAKE-WITHDRAWN-REASON": check_free,
    "HANDSHAKE-INBOUND-HELD": check_held,
    "HANDSHAKE-INBOUND-OBSERVED": check_observed,
    "HANDSHAKE-ROUND-DIGEST": check_digest,
    "HANDSHAKE-SOURCE-ANCHOR": check_source_anchor,
    "HANDSHAKE-SHARED-HASHES": check_shared_hashes,
    "HANDSHAKE-SHARED-HASHES-SOURCE": check_refs,
    "HANDSHAKE-AGREED-CHANGES": check_refs_or_none,
    "HANDSHAKE-CLOSE-BY": check_datetime,
    "HANDSHAKE-READY-TO-READ": check_ready,
    "HANDSHAKE-NEXT-LAP": check_next_lap,
    "PROVIDER-CONTRACT": check_contract,
    "CONSUMER-CONTRACT": check_contract,
    "SEAM-RULES-VERSION": check_int,
    "OWNERSHIP-VERSION": check_int,
}

#: Field names the record has used that language 1 retires, each with what
#: replaces it. A retired field is refused rather than ignored: ignoring is how
#: 21 undefined names accumulated, each read by one side only.
RETIRED_FIELDS: Final[dict[str, str]] = {
    "HANDSHAKE-ARTIFACT-BUILD": "a CLAIM cited, anchoring the artifact",
    "HANDSHAKE-ARTIFACTS": "a CLAIM cited, anchoring each artifact",
    "HANDSHAKE-ENCLOSED": "a CLAIM cited, anchoring each artifact",
    "HANDSHAKE-CORRECTS": "an ERRATUM",
    "HANDSHAKE-LAP-CORRECTION": "an ERRATUM",
    "HANDSHAKE-PEER-DIGEST-CHECK": "a CLAIM measured",
    "HANDSHAKE-PEER-DIGEST-VERIFIED": "a CLAIM measured",
    "HANDSHAKE-INBOUND-OBSERVED-HISTORY": "a CLAIM measured",
    "HANDSHAKE-RELEASE": "a NOTICE, or a CLAIM about the release",
    "HANDSHAKE-CLOSE-BY-NOTE": "a statement, referenced from a -SOURCE field",
    "HANDSHAKE-FROM-COMMIT-NOTE": "a statement, referenced from HANDSHAKE-FROM-COMMIT-SOURCE",
    "HANDSHAKE-LAP-NUMBERING-NOTE": "a statement",
    "HANDSHAKE-PROTOCOL-NOTE": "a statement",
    "HANDSHAKE-READY-TO-READ-NOTE": "a statement",
    "HANDSHAKE-TEST-PIN-NOTE": "a statement, referenced from HANDSHAKE-TEST-PIN-SOURCE",
    "HANDSHAKE-VERDICT-NOTE": "a statement, referenced from HANDSHAKE-VERDICT-SOURCE",
}

#: Header fields whose value is a list of local statement references, and the
#: kinds (with qualifiers) those references may point at. `None` means any kind.
HEADER_REF_KINDS: Final[dict[str, frozenset[tuple[str, str | None]] | None]] = {
    "HANDSHAKE-TESTED": frozenset({("CLAIM", "measured")}),
    "HANDSHAKE-BREAKING": frozenset({("NOTICE", "breaking"), ("NOTICE", "semantic")}),
    # A landed change is a CLAIM carrying its evidence; one not landed is a
    # PROMISE naming who does it and when. v6 §5e's ledger, typed.
    "HANDSHAKE-AGREED-CHANGES": frozenset(
        {
            ("CLAIM", "measured"),
            ("CLAIM", "derived"),
            ("CLAIM", "cited"),
            ("CLAIM", "operator"),
            ("PROMISE", None),
        }
    ),
}


def check_header(header: Sequence[tuple[str, str, int]]) -> list[Problem]:
    problems: list[Problem] = []
    seen: dict[str, int] = {}
    for key, value, line in header:
        if key in seen:
            problems.append(
                Problem("L8", line, f"{key} appears twice (first at line {seen[key]})")
            )
            continue
        seen[key] = line
        if key.startswith("HANDSHAKE-X-"):
            if len(value) > MAX_EXPERIMENTAL_CHARS or not value:
                problems.append(
                    Problem(
                        "L9", line, f"{key}: an experimental field is one short value"
                    )
                )
            continue
        if key in RETIRED_FIELDS:
            problems.append(
                Problem("L10", line, f"{key} is retired; write {RETIRED_FIELDS[key]}")
            )
            continue
        check = HEADER_TYPES.get(key)
        if check is None:
            problems.append(
                Problem(
                    "L11",
                    line,
                    f"{key} is not a language-1 field (use HANDSHAKE-X-* to try one out)",
                )
            )
            continue
        why = check(value)
        if why is not None:
            problems.append(Problem("L12", line, f"{key} must be {why}"))
    return problems
