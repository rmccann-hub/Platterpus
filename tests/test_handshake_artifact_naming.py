"""A handshake artifact's filename must name the build its OWN BANNER asserts.

**Why this file exists, and it is the rule's own failure mode.**
``docs/handshake/README.md`` states the rule as a table row:

    Artifacts: ``round-NN-lap-LL-<kind>-g<build>.<ext>`` — ``<build>`` is the
    commit the artifact's **own banner** asserts, not the commit a lap file names
    it by. Those differ, and only the banner is derivable from the artifact's
    content.

Nothing checked it. On 2026-08-21 five of round 12 lap 3's artifacts were filed
under ``g237a4ff`` — the commit the fork's covering message named as its release —
when their banners say ``g6a23662`` (the four rip artifacts) and ``g8a1a3ee`` (the
provider contract, which names the commit that generated it). All five were wrong,
filed by the same person who had read the rule an hour earlier.

That is `CLAUDE.md`'s *a comment where a check belongs is not a fix*, and it is the
provenance failure round 6 of this handshake cost two golden references to: **a
claim about an artifact must be derivable from the artifact's content, not from the
banner of a covering message.** A filename is a claim.

**Why it is worth a test rather than care.** The filename is a *second description*
of a fact the artifact already declares — the same shape as the lap-file convention,
which is safe only because `tests/test_handshake_file_naming.py` asserts the name
and the wire header agree. This is that assertion for artifacts.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

import pytest

_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
_ARTIFACTS: Final[Path] = _REPO_ROOT / "docs" / "handshake" / "inbound" / "artifacts"

#: The build tag a fork artifact stamps on itself. Matched anywhere in the file:
#: a log carries it on line 1, a diagnostics record inside JSON, and a generated
#: contract on its own ``Build:`` line.
_BANNER: Final[re.Pattern[str]] = re.compile(
    r"platterpus-fork-g(?P<sha>[0-9a-f]{7,40})"
)

#: The ``-g<build>`` field of the filename.
_NAMED: Final[re.Pattern[str]] = re.compile(r"-g(?P<sha>[0-9a-f]{7,40})\.[a-z]+$")

#: **The rule binds artifacts filed from round 12 lap 3 onward.** Earlier ones are
#: inventoried below rather than exempted one at a time, because they fall into two
#: categories with two causes, and nine separate excuses would enforce nothing.
_ENFORCED_FROM: Final[tuple[int, int]] = (12, 3)

#: **Category 1 — the fork's generator normalised its own build away.** Every
#: provider contract before round 12 lap 3 carries the literal
#: ``platterpus-fork-g<commit>``, so its name cannot come from its content and comes
#: from the lap that enclosed it. That is the defect we reported as round 12 §E3, and
#: their lap 3 fixed it by writing the real value and normalising in ``--check`` —
#: which is why `round-12-lap-03-provider-contract-g8a1a3ee.md` states a real commit
#: and every earlier one does not. Counted, frozen, and it may only shrink.
_PLACEHOLDER_BUILD: Final[frozenset[str]] = frozenset(
    {
        "round-07-lap-24-audit-ge61e75a.md",
        "round-07-lap-25-provider-contract-g9048082.md",
        "round-07-lap-30-provider-contract-gdc21958.md",
        "round-07-lap-32-provider-contract-g4a35604.md",
        "round-07-lap-39-provider-contract-g422d12a.md",
        "round-08-lap-01-provider-contract-gea2793a.md",
        "round-09-lap-03-provider-contract-g42fe4f2.md",
        "round-11-lap-03-provider-contract-gc455683.md",
        "round-12-lap-01-provider-contract-gdef36a6.md",
    }
)

#: **Category 2 — a name and a banner that genuinely disagree, and it is the finding
#: this whole rule comes from.** `round-07-lap-33-golden-reference-g104f6d4.log` is
#: filed under the commit its lap named and its own first line says ``g92ceeed``.
#: That is round 6/7's provenance failure verbatim — *"two consecutive golden
#: references whose banners named commits three behind the pin"* — and the file is
#: kept under the misleading name **on purpose**: renaming it would erase the
#: evidence, and every document that cites it cites this path. One entry, frozen.
_NAME_DISAGREES_WITH_BANNER: Final[frozenset[str]] = frozenset(
    {"round-07-lap-33-golden-reference-g104f6d4.log"}
)

_GRANDFATHERED: Final[frozenset[str]] = _PLACEHOLDER_BUILD | _NAME_DISAGREES_WITH_BANNER

#: ``round-NN-lap-LL`` from an artifact name, for the enforcement boundary.
_ROUND_LAP: Final[re.Pattern[str]] = re.compile(r"^round-0*(\d+)-lap-0*(\d+)")


def naming_disagreement(name: str, text: str) -> str | None:
    """``None`` if `name` is consistent with the build `text` declares, else why not.

    **Pure, and that is the point.** The sweep below reads the real directory, where
    — as of this being written — every artifact either agrees or is inventoried. So
    reverting the sweep's assertion changes nothing, and a probe reports it
    "unaffected": the check is *satisfied by finding nothing*. Its logic therefore
    needs proving separately, on inputs that do violate it. That is
    `test_the_comparison_actually_catches_a_misnaming`.

    Returns the reason rather than a bool so the sweep can print it, and so the two
    distinguishable failures stay distinguishable: a file that declares **no** build
    and a file that declares a **different** one are different findings with
    different remedies (report it to the sender, versus rename it here).
    """
    named = _NAMED.search(name)
    if named is None:
        return "the filename carries no -g<build> field"
    banner = _BANNER.search(text)
    if banner is None:
        return "the file declares no platterpus-fork-g<commit> build at all"
    a, b = named.group("sha"), banner.group("sha")
    if a.startswith(b) or b.startswith(a):
        return None
    return f"filed under g{a} but the file itself says g{b}"


def _filed_at(name: str) -> tuple[int, int] | None:
    """The ``(round, lap)`` an artifact was filed under, from its own name."""
    match = _ROUND_LAP.match(name)
    return (int(match.group(1)), int(match.group(2))) if match else None


def _artifacts() -> list[Path]:
    """Every committed inbound artifact whose name carries a ``-g<build>`` field."""
    if not _ARTIFACTS.is_dir():
        return []
    return sorted(
        p for p in _ARTIFACTS.iterdir() if p.is_file() and _NAMED.search(p.name)
    )


def test_there_are_artifacts_to_check() -> None:
    """The floor. A glob that matched nothing would pass every assertion below,
    which is the exact failure mode this file was written for."""
    found = _artifacts()
    assert len(found) >= 8, f"only found {[p.name for p in found]}"


@pytest.mark.parametrize("artifact", _artifacts(), ids=lambda p: p.name)
def test_the_filename_names_the_build_the_artifact_itself_asserts(
    artifact: Path,
) -> None:
    """**The check the README's table row could not perform.**

    Derived from the artifact's content, never from a lap file or a covering
    message — those are the two things that were wrong when this was written.
    """
    named = _NAMED.search(artifact.name)
    assert named is not None  # guaranteed by the collector
    filed = _filed_at(artifact.name)
    text = artifact.read_text(encoding="utf-8", errors="replace")
    banner = _BANNER.search(text)
    grandfathered = artifact.name in _GRANDFATHERED

    if banner is None:
        assert grandfathered, (
            f"{artifact.name} states no `platterpus-fork-g<commit>` banner, so its "
            f"filename asserts a provenance nothing in the file supports. If the "
            f"SENDER's generator left a placeholder, that is a finding to report to "
            f"them — as round 12 §E3 was — not a row to add here."
        )
        return

    # Delegates rather than restating: a second spelling of the comparison is a
    # second thing to drift, and the helper is the one with a proof behind it.
    if naming_disagreement(artifact.name, text) is None:
        assert not grandfathered, (
            f"{artifact.name} is grandfathered but its name and banner now agree "
            f"(`{banner.group(0)}`). Remove it from the inventory — the exemption "
            f"is describing a problem that no longer exists."
        )
        return

    assert grandfathered, (
        f"{artifact.name} is filed under g{named.group('sha')} but its own banner "
        f"says g{banner.group('sha')}.\n\n"
        f"The filename must name the build the ARTIFACT asserts, not the commit a "
        f"lap file or a covering message names it by — those differ, and only the "
        f"banner is derivable from the content. Rename it with `git mv`.\n\n"
        f"This is round 6/7's provenance failure in miniature, and it is what "
        f"happened on 2026-08-21: five of round 12 lap 3's artifacts were filed "
        f"under the release commit the fork's message named, when their banners "
        f"said otherwise."
    )
    assert filed is not None and filed < _ENFORCED_FROM, (
        f"{artifact.name} was filed at round {filed} — at or after "
        f"{_ENFORCED_FROM}, where this rule binds — so it may not be grandfathered."
    )


def test_the_grandfathered_inventory_only_shrinks() -> None:
    """A frozen historical count, not a growing list of excuses.

    Measured 2026-08-21 across 33 committed artifacts: 23 agree, 9 carry the
    sender's ``<commit>`` placeholder, 1 genuinely disagrees. Every entry must
    still exist — a rule about a file nobody has is noise — and the totals may
    only fall.
    """
    present = {p.name for p in _artifacts()}
    for name in sorted(_GRANDFATHERED):
        assert name in present, (
            f"{name} is inventoried but not committed — delete the entry rather "
            f"than leaving a rule about a file nobody has"
        )
    assert len(_PLACEHOLDER_BUILD) <= 9, (
        f"{len(_PLACEHOLDER_BUILD)} placeholder artifacts; 9 were measured on "
        f"2026-08-21. A NEW artifact whose generator cannot name its own build is a "
        f"finding for the sender, not a row here — that is what round 12 §E3 was."
    )
    assert len(_NAME_DISAGREES_WITH_BANNER) <= 1, (
        f"{len(_NAME_DISAGREES_WITH_BANNER)} artifacts whose name contradicts their "
        f"own content; ONE was measured, and it is kept because it is the evidence "
        f"of round 6/7's provenance failure. A second means a misfiling — rename it."
    )
    # Non-triviality: the enforced population must be the majority, or the
    # grandfathering has quietly become the rule.
    enforced = [
        p
        for p in _artifacts()
        if (f := _filed_at(p.name)) is not None and f >= _ENFORCED_FROM
    ] + [p for p in _artifacts() if p.name not in _GRANDFATHERED]
    assert len({p.name for p in enforced}) >= 20, (
        f"only {len({p.name for p in enforced})} artifacts are actually checked; "
        f"the exemptions have outgrown the rule"
    )


def test_the_comparison_actually_catches_a_misnaming() -> None:
    """**The proof the sweep above cannot give.**

    Every committed artifact today either agrees with its banner or is inventoried,
    so the sweep's assertion is never the thing that fails — a revert probe reports
    it `unaffected`, which is indistinguishable from a dead check. `CLAUDE.md`: *can
    this check be satisfied by finding nothing? Then give it a floor.* This is that
    floor, and it is the one that matters: it feeds the comparison the exact
    mistake made on 2026-08-21 and requires it to be caught.
    """
    real = "cyanrip 0.9.4-rc2+platterpus.7 (platterpus-fork-g6a23662)\n"

    # The actual misfiling: named for the commit the covering message called the
    # release, while the artifact says otherwise.
    why = naming_disagreement("round-12-lap-03-golden-reference-g237a4ff.log", real)
    assert why is not None, "the 2026-08-21 misnaming is not caught"
    assert "g237a4ff" in why and "g6a23662" in why, (
        f"the reason must name BOTH commits, or the reader cannot act on it: {why}"
    )

    # The corrected name passes.
    assert (
        naming_disagreement("round-12-lap-03-golden-reference-g6a23662.log", real)
        is None
    )

    # An abbreviated name against a full banner is agreement, not a mismatch: a
    # 7-char name and a 40-char banner name the same commit.
    assert (
        naming_disagreement(
            "round-12-lap-03-golden-reference-g6a23662.log",
            "cyanrip (platterpus-fork-g6a236629f1c4d5e8a7b0c3d2e1f0a9b8c7d6e5f4)\n",
        )
        is None
    )

    # The two distinguishable failures stay distinguishable.
    placeholder = naming_disagreement(
        "round-11-lap-03-provider-contract-gc455683.md",
        "Build: `cyanrip 0.9.4-rc1+platterpus.6 (platterpus-fork-g<commit>)`\n",
    )
    assert placeholder is not None and "no platterpus-fork" in placeholder, (
        f"a placeholder build must read as 'declares none', not as a mismatch — "
        f"they need different remedies: {placeholder}"
    )
