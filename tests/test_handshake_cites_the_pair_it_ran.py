"""A handshake file that cites hardware must name the pair the hardware ran.

## The finding this exists for (round 7 lap 10, §A)

Lap 8 put the tested pair in writing as `cyanrip 0.9.4-rc1+platterpus.5-beta.1`
(commit `9003e6f`) **with Platterpus v0.6.4b1**. The rig session actually ran
**0.6.4b3**. The fork caught it by reading a version string out of an artifact and
comparing it to a header we had written two laps earlier — by hand, across files,
with nothing checking it. Their words:

> *"A close that cites testing which happened on an undeclared pair records
> agreement about a combination nobody ran."*

And:

> *"nothing in either artifact would have flagged the mismatch."*

That last sentence is the bug. The evidence was in the repository — the report's
`generator.version`, the EAC log's header — and the declaration was in a file three
directories away, and no code related them. This is the same shape as every other
finding in this round: a fact we *had*, in a form nobody compared.

## What is checked, and what deliberately is not

Only files that **cite a committed artifact directory** are held to it. A file that
makes no hardware claim has no pair to get wrong, and demanding a version match from
one would be a check satisfied by the wrong thing.

The comparison is against the artifact's own **content** (`generator.version` in the
report it points at), never against `__version__` — the app version moves on after a
round closes, and a gate keyed on "current" would refuse a correct historical record.
CLAUDE.md rule 12: *any claim about an artifact's provenance must be derivable from
the artifact's content.*

Both halves are checked, because a seam has two: the **app** version and the
**ripper** build. Naming one correctly and the other from memory is how round 4
verified a flag table it had never diffed.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_HANDSHAKE = _REPO / "docs" / "handshake"
_REFERENCE = _REPO / "output_reference"

#: A wire-header field at column 0. Same rule the protocol spec states: a
#: declaration is what a file *states*, so fenced examples are stripped first.
_FIELD = re.compile(r"^(?P<key>HANDSHAKE-[A-Z-]+):[ \t]*(?P<value>.*?)[ \t]*$", re.M)

#: A citation of a committed artifact directory, e.g.
#: ``output_reference/cyanrip_fork_flac/``.
_CITATION = re.compile(r"output_reference/(?P<dir>[A-Za-z0-9_.-]+)/?")

_FENCE = re.compile(r"^```.*?^```", re.M | re.S)


def _declared(text: str) -> dict[str, str]:
    return {
        m.group("key"): m.group("value") for m in _FIELD.finditer(_FENCE.sub("", text))
    }


def _cited_dirs(text: str) -> set[str]:
    """Artifact directories a file points at, excluding fenced examples."""
    return {
        m.group("dir")
        for m in _CITATION.finditer(_FENCE.sub("", text))
        if (_REFERENCE / m.group("dir")).is_dir()
    }


def _artifact_versions(directory: Path) -> tuple[set[str], set[str]]:
    """``(app_versions, ripper_banner_lines)`` read out of a directory's artifacts.

    Sets rather than single values because a directory may legitimately hold more
    than one rip; a citation is satisfied if it names one of them.
    """
    apps: set[str] = set()
    rippers: set[str] = set()
    for report in sorted(directory.glob("*.json")):
        try:
            data = json.loads(report.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        version = ((data.get("generator") or {}).get("version")) or ""
        if version:
            apps.add(str(version))
    for log in sorted(directory.glob("*.log")):
        if "EACcompatible" in log.name:
            continue
        first = log.read_text(encoding="utf-8", errors="replace").split("\n", 1)[0]
        if first.strip():
            rippers.add(first.strip())
    return apps, rippers


def _handshake_files() -> list[Path]:
    return sorted(
        p
        for sub in ("outbound", "inbound", "verified")
        for p in (_HANDSHAKE / sub).glob("*.md")
    )


def test_there_are_handshake_files_and_committed_artifacts() -> None:
    """Floor. With either side empty every assertion below passes by finding nothing.

    This is the trap the check is *about*: the fork's §A mismatch survived because
    nothing related two things that both existed.
    """
    files = _handshake_files()
    assert len(files) >= 5, f"only {len(files)} handshake files — the sweep is blind"
    dirs = (
        [p for p in _REFERENCE.iterdir() if p.is_dir()] if _REFERENCE.is_dir() else []
    )
    assert dirs, (
        "no committed artifact directories — nothing to check citations against"
    )


def test_at_least_one_file_cites_an_artifact() -> None:
    """The second floor, and the one that matters more.

    Every per-file assertion below is conditional on a citation. If no file cited
    anything the whole module would be green while checking nothing — which is
    indistinguishable from the mismatch it exists to catch.
    """
    citing = [
        p for p in _handshake_files() if _cited_dirs(p.read_text(encoding="utf-8"))
    ]
    assert citing, (
        "no handshake file cites a committed artifact directory, so the pair-mismatch "
        "check examined nothing"
    )


def test_a_file_citing_hardware_names_the_app_version_that_produced_it() -> None:
    """`HANDSHAKE-APP-VERSION` must match the artifact's own `generator.version`.

    Read off the artifact's CONTENT, not off `__version__`: the app version moves on
    after a round closes, and a check keyed on "current" would refuse a correct
    historical record. Rule 12 — provenance must be derivable from the artifact.
    """
    checked = 0
    for path in _handshake_files():
        text = path.read_text(encoding="utf-8")
        cited = _cited_dirs(text)
        if not cited:
            continue
        declared = _declared(text).get("HANDSHAKE-APP-VERSION", "")
        if not declared:
            continue  # pre-header rounds; the wire-field gate covers absence
        for name in sorted(cited):
            apps, _ = _artifact_versions(_REFERENCE / name)
            if not apps:
                continue  # a directory of logs with no report says nothing about us
            checked += 1
            assert any(app in declared for app in apps), (
                f"{path.name} declares HANDSHAKE-APP-VERSION {declared!r} and cites "
                f"output_reference/{name}/, whose report was written by "
                f"{sorted(apps)}. A file that cites testing done on an undeclared "
                "pair records agreement about a combination nobody ran (round 7 "
                "lap 10 §A)."
            )
    assert checked, "no (file, artifact) pair was comparable — the check is decoration"


def test_a_file_citing_hardware_names_the_ripper_build_that_produced_it() -> None:
    """The other half of the pair. A seam has two ends and both get named.

    Round 4 was "verified" by diffing their log lines against our parser while their
    flag table went undiffed; naming one half of a pair correctly and the other from
    memory is the same mistake with different nouns.
    """
    checked = 0
    for path in _handshake_files():
        text = path.read_text(encoding="utf-8")
        cited = _cited_dirs(text)
        if not cited:
            continue
        declared = _declared(text).get("HANDSHAKE-RIPPER-VERSION", "")
        if not declared:
            continue
        for name in sorted(cited):
            _, rippers = _artifact_versions(_REFERENCE / name)
            if not rippers:
                continue
            checked += 1
            # The build TAG is the identifying part — a version number cannot
            # separate the fork from upstream, since the fork tracks upstream
            # versions (rule 12). So match on the parenthetical when there is one.
            tags = {
                banner[banner.index("(") + 1 : banner.rindex(")")]
                for banner in rippers
                if "(" in banner and ")" in banner
            }
            if not tags:
                continue
            assert any(tag in declared for tag in tags), (
                f"{path.name} declares HANDSHAKE-RIPPER-VERSION {declared!r} and "
                f"cites output_reference/{name}/, whose log was written by a binary "
                f"tagged {sorted(tags)}"
            )
    assert checked, "no (file, ripper) pair was comparable — the check is decoration"


def test_the_check_would_catch_the_actual_lap_8_mismatch() -> None:
    """Prove the failure path, against the real numbers rather than by reasoning.

    Lap 8 declared `0.6.4b1`; the rig ran `0.6.4b3`. A detector that cannot be shown
    to reject that has not been shown to do anything — and this project has twice
    shipped a check that passed against the very bug it was written for.
    """
    apps, _ = _artifact_versions(_REFERENCE / "cyanrip_fork_flac")
    assert apps == {"0.6.4b3"}, f"the committed artifact reports {apps}, not 0.6.4b3"

    lap8_declaration = "platterpus 0.6.4b1"
    assert not any(app in lap8_declaration for app in apps), (
        "the predicate accepts lap 8's declaration against the b3 artifact, so it "
        "would not have caught the mismatch the fork found by hand"
    )
    # …and accepts the correct one, or it would reject everything.
    assert any(app in "platterpus 0.6.4b3" for app in apps)
