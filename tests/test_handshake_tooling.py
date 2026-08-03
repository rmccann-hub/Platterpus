"""The handshake protocol must execute, not just be written down.

``docs/cyanrip-handshake.md`` describes a bidirectional protocol: two files per
round, two verifications, no release until both are in. That was prose, and this
project's own rule is that **a rule nothing executes is not a rule**
(``docs/testing.md`` §5.m). A round came back missing a required section twice,
and both times it was caught by someone happening to notice.

``scripts/handshake.py`` makes it executable in both directions — emit our
outbound file with every required section, validate their inbound one — and this
file holds it to the same bar the protocol holds us to.

The assertions that matter most are the ones proving the checker can **fail**.
A validator that always returns "fine" is decoration, and it is the specific
shape of decoration that gets trusted for a year before anyone tests it.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _REPO_ROOT / "scripts" / "handshake.py"
_PROTOCOL = _REPO_ROOT / "docs" / "cyanrip-handshake.md"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("handshake", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def hs() -> ModuleType:
    return _load()


def _complete_inbound(hs: ModuleType) -> str:
    """A file that satisfies every rule, built from the spec itself.

    Built from ``INBOUND_SECTIONS`` rather than hand-written so that adding a
    required section cannot leave this fixture quietly incomplete — the
    "positive control" stays positive by construction.
    """
    body = "x" * (hs.MIN_SECTION_CHARS + 250)
    return "# cyanrip → Platterpus\n\n" + "\n\n".join(
        f"## {s.key}\n\n{body}" for s in hs.INBOUND_SECTIONS
    )


# --- the checker can pass, and more importantly can fail ---------------------


def test_a_complete_file_passes(hs: ModuleType, tmp_path: Path) -> None:
    """The positive control. Without it, every failure below could be the
    checker rejecting everything."""
    path = tmp_path / "round.md"
    path.write_text(_complete_inbound(hs), encoding="utf-8")
    assert hs.check_inbound(path) == []


@pytest.mark.parametrize("dropped", [s.key for s in _load().INBOUND_SECTIONS])
def test_dropping_any_single_section_is_caught(
    hs: ModuleType, tmp_path: Path, dropped: str
) -> None:
    """Swept over every section, not spot-checked on one. A checker that
    enforced eight of ten would look identical from the outside."""
    body = "x" * (hs.MIN_SECTION_CHARS + 250)
    text = "# cyanrip → Platterpus\n\n" + "\n\n".join(
        f"## {s.key}\n\n{body}" for s in hs.INBOUND_SECTIONS if s.key != dropped
    )
    path = tmp_path / "round.md"
    path.write_text(text, encoding="utf-8")
    problems = hs.check_inbound(path)
    assert any(f"§{dropped}" in p for p in problems), (
        f"dropping §{dropped} was not reported: {problems}"
    )


def test_a_section_present_but_empty_is_caught(hs: ModuleType, tmp_path: Path) -> None:
    """The failure worse than a missing section: a heading with nothing under
    it passes a naive "is the heading there" check while telling us nothing."""
    text = _complete_inbound(hs).replace(
        f"## F\n\n{'x' * (hs.MIN_SECTION_CHARS + 250)}", "## F\n\nTODO"
    )
    path = tmp_path / "round.md"
    path.write_text(text, encoding="utf-8")
    problems = hs.check_inbound(path)
    assert any("§F" in p and "present but" in p for p in problems), problems


def test_a_silent_null_case_is_caught_for_the_explicit_sections(
    hs: ModuleType, tmp_path: Path
) -> None:
    """§D (log-format delta) and §H (found in our output) are the two where
    silence and "nothing to report" are indistinguishable, and only one of those
    is safe. A short, non-committal section must be rejected."""
    explicit = [s.key for s in hs.INBOUND_SECTIONS if s.must_be_explicit]
    assert len(explicit) >= 2, "the must-be-explicit set collapsed"
    for key in explicit:
        text = _complete_inbound(hs).replace(
            f"## {key}\n\n{'x' * (hs.MIN_SECTION_CHARS + 250)}",
            f"## {key}\n\nWe looked at this area during the round and moved on.",
        )
        path = tmp_path / f"round-{key}.md"
        path.write_text(text, encoding="utf-8")
        assert any(f"§{key}" in p for p in hs.check_inbound(path)), (
            f"§{key} trailed off without stating the null case and was accepted"
        )


def test_an_explicit_nothing_is_accepted(hs: ModuleType, tmp_path: Path) -> None:
    """The other half: "no changes" *is* a complete answer and must not be
    nagged, or the check trains people to pad sections with filler."""
    text = _complete_inbound(hs).replace(
        f"## D\n\n{'x' * (hs.MIN_SECTION_CHARS + 250)}",
        "## D\n\nNo changes to the log format this round. Byte-identical to round 3.",
    )
    path = tmp_path / "round.md"
    path.write_text(text, encoding="utf-8")
    assert not any("§D" in p for p in hs.check_inbound(path)), hs.check_inbound(path)


# --- robustness: a validator that crashes is a validator people stop running --


@pytest.mark.parametrize(
    "content", ["", "   \n\n  ", "#" * 5000, "\x00\x01", "no headings at all"]
)
def test_it_reports_rather_than_raising(
    hs: ModuleType, tmp_path: Path, content: str
) -> None:
    path = tmp_path / "round.md"
    path.write_text(content, encoding="utf-8")
    problems = hs.check_inbound(path)
    assert isinstance(problems, list)
    assert problems, "a file with no sections must produce problems, not silence"


def test_a_missing_file_is_reported_not_raised(hs: ModuleType, tmp_path: Path) -> None:
    assert hs.check_inbound(tmp_path / "nope.md")


def test_heading_decoration_does_not_matter(hs: ModuleType, tmp_path: Path) -> None:
    """The fork is a different project with its own habits. Rejecting a complete
    file over `### §A —` vs `## A` would be theatre, and would get the checker
    switched off."""
    body = "x" * (hs.MIN_SECTION_CHARS + 250)
    styles = ["## {k}", "### §{k} — Title", "## {k}. Title", "**{k}**"]
    text = "# r\n\n" + "\n\n".join(
        styles[i % len(styles)].format(k=s.key) + f"\n\n{body}"
        for i, s in enumerate(hs.INBOUND_SECTIONS)
    )
    path = tmp_path / "round.md"
    path.write_text(text, encoding="utf-8")
    assert hs.check_inbound(path) == []


# --- the outbound half --------------------------------------------------------


def test_our_own_skeleton_satisfies_our_own_outbound_spec(hs: ModuleType) -> None:
    """The emitter and the outbound checker must agree, or we ship a skeleton
    that our own rules reject."""
    assert hs.check_outbound(hs.emit_outbound(99)) == []


def test_the_skeleton_carries_the_inbound_spec_inline(hs: ModuleType) -> None:
    """The fork does not have this repo, so linking to the spec is useless. Every
    required inbound section must appear in the file we actually send."""
    skeleton = hs.emit_outbound(99)
    for section in hs.INBOUND_SECTIONS:
        assert f"**{section.key}**" in skeleton, (
            f"§{section.key} not in the outbound spec"
        )


def test_the_spec_we_send_is_the_spec_we_enforce(hs: ModuleType) -> None:
    """The asymmetry that rots a protocol: asking for a section nobody checks, or
    checking one nobody was asked for. Both tables come from one list, and this
    pins that they still do."""
    rendered = hs._inbound_spec_markdown()
    for section in hs.INBOUND_SECTIONS:
        assert section.title in rendered
    assert rendered.count("|") >= len(hs.INBOUND_SECTIONS) * 2


def test_the_round_4_outbound_we_actually_sent_is_complete(hs: ModuleType) -> None:
    """Not the skeleton — the real file. A generator that passes its own check
    proves nothing about what a human then wrote."""
    real = _REPO_ROOT / "docs" / "handshake" / "outbound" / "round-4.md"
    if not real.exists():
        pytest.skip("round-4 outbound not recorded")
    assert hs.check_outbound(real.read_text(encoding="utf-8")) == []


# --- the protocol doc and the tool must not drift -----------------------------


def test_every_enforced_section_appears_in_the_protocol_doc(hs: ModuleType) -> None:
    """The doc is what a human reads and the script is what runs. If they
    disagree, the one that runs wins silently — so they are pinned together."""
    doc = _PROTOCOL.read_text(encoding="utf-8")
    for section in hs.INBOUND_SECTIONS:
        assert f"**{section.key}**" in doc, (
            f"§{section.key} is enforced by scripts/handshake.py but is not in "
            f"{_PROTOCOL.name} — a reader following the doc would send an "
            f"incomplete file and only find out from the checker"
        )


def test_the_protocol_doc_names_the_checker(hs: ModuleType) -> None:
    """So the next person reading the doc knows the tool exists at all."""
    doc = _PROTOCOL.read_text(encoding="utf-8")
    assert "scripts/handshake.py" in doc


def test_the_section_list_is_not_trivially_small(hs: ModuleType) -> None:
    """Floor. Every sweep above is "for each section", which an empty list
    satisfies perfectly."""
    assert len(hs.INBOUND_SECTIONS) >= 8
    assert len(hs.OUTBOUND_SECTIONS) >= 6
    assert len({s.key for s in hs.INBOUND_SECTIONS}) == len(hs.INBOUND_SECTIONS)


# --- round status -------------------------------------------------------------


def test_status_reports_an_incomplete_round_as_open(
    hs: ModuleType, tmp_path: Path
) -> None:
    """The release gate, exercised against a CONSTRUCTED state.

    The first version of this asserted "round 4 is OPEN" against the real
    `docs/handshake/` — and then round 4 closed, and the test failed on
    progress. A test that pins today's state is not testing the logic; it is
    testing the calendar. `round_status` takes a root so both branches can be
    driven deterministically.
    """
    for name in ("outbound", "inbound", "verified"):
        (tmp_path / name).mkdir()
    (tmp_path / "outbound" / "round-9.md").write_text("sent", encoding="utf-8")
    (tmp_path / "inbound" / "round-9.md").write_text("back", encoding="utf-8")

    lines = hs.round_status(tmp_path)
    assert any(ln.startswith("round-9") and ln.endswith("OPEN") for ln in lines), lines
    assert any("do not release" in ln for ln in lines), (
        "an open round must say the release is blocked; that sentence IS the gate"
    )


def test_status_reports_a_complete_round_as_closed(
    hs: ModuleType, tmp_path: Path
) -> None:
    """The other branch. Without it, "reports OPEN" could be satisfied by a
    function that reports OPEN unconditionally."""
    for name in ("outbound", "inbound", "verified"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "round-9.md").write_text("x", encoding="utf-8")

    lines = hs.round_status(tmp_path)
    assert any(ln.startswith("round-9") and ln.endswith("CLOSED") for ln in lines)
    assert not any("do not release" in ln for ln in lines)


def test_the_verification_is_what_closes_a_round(
    hs: ModuleType, tmp_path: Path
) -> None:
    """Step 5 is the one that gets skipped, so it is the one pinned: sent and
    returned is NOT enough, and the missing piece must be ours."""
    for name in ("outbound", "inbound", "verified"):
        (tmp_path / name).mkdir()
    (tmp_path / "outbound" / "round-9.md").write_text("x", encoding="utf-8")
    (tmp_path / "inbound" / "round-9.md").write_text("x", encoding="utf-8")
    assert hs.round_status(tmp_path)[0].endswith("OPEN")

    (tmp_path / "verified" / "round-9.md").write_text("x", encoding="utf-8")
    assert hs.round_status(tmp_path)[0].endswith("CLOSED")


def test_no_rounds_at_all_is_reported_not_silently_fine(
    hs: ModuleType, tmp_path: Path
) -> None:
    """An empty record must not read as "everything is closed"."""
    lines = hs.round_status(tmp_path)
    assert lines and "no handshake rounds" in lines[0]


def test_the_real_record_has_no_round_left_open_behind_a_closed_one(
    hs: ModuleType,
) -> None:
    """The actual repo state — asserted as well-formedness, not as "all closed".

    **This test used to assert every round was closed, and that was wrong in the
    same way its own predecessor was wrong.** The predecessor pinned "round 4 is
    OPEN" and failed when round 4 closed; this one failed the moment round 5 was
    *opened*. A round is open by definition between sending our file and sending
    our verification, so a test forbidding that reddens CI for ordinary work —
    and, worse, it was the *only* thing enforcing "no release while a round is
    open", which meant the rule was enforced where releases do not happen and
    not where they do. The release gate now lives in `release.yml` (via
    `handshake.py --release-gate`), where it belongs.

    What is still worth asserting is the shape the record must always have: an
    open round may only be the **newest** one. A round left open *behind* a
    closed one is the real bug this file was written for — round 3 was never
    verified back while round 4 closed, and nothing noticed.
    """
    lines = hs.round_status()
    rounds = [ln for ln in lines if ln.startswith("round-")]
    assert len(rounds) >= 4, "the correspondence record has shrunk"

    def number(line: str) -> int:
        return int(line.split(":")[0].removeprefix("round-"))

    ordered = sorted(rounds, key=number)
    open_numbers = [number(ln) for ln in ordered if ln.endswith("OPEN")]
    newest = number(ordered[-1])
    stale = [n for n in open_numbers if n != newest]
    assert not stale, (
        "a handshake round is open behind a newer one, which is how round 3 went "
        f"unverified while round 4 closed: round(s) {stale} open, newest is {newest}"
    )
    # Floor: an all-CLOSED record must not make this vacuous. Every round needs
    # an outbound file, or the record has a hole rather than a state.
    assert all("sent=yes" in ln for ln in rounds), (
        "a round exists with no outbound file: " + "; ".join(rounds)
    )


def test_the_release_gate_blocks_a_release_while_a_round_is_open(
    hs: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The gate itself, both ways — a checker that cannot fail is decoration.

    Exercised through `main(["--release-gate"])` so it is the same code path the
    release workflow runs, not a re-implementation of it.
    """
    (tmp_path / "outbound").mkdir()
    (tmp_path / "inbound").mkdir()
    (tmp_path / "verified").mkdir()
    (tmp_path / "outbound" / "round-1.md").write_text("x", encoding="utf-8")
    monkeypatch.setattr(hs, "HANDSHAKE_DIR", tmp_path)

    # Sent, nothing back: OPEN → blocked.
    assert hs.main(["--release-gate"]) == 1

    # Their return arrives but we have not verified it. A partly-verified pin is
    # an unverified pin, so this must STILL block.
    (tmp_path / "inbound" / "round-1.md").write_text("x", encoding="utf-8")
    assert hs.main(["--release-gate"]) == 1

    # Both directions done → allowed.
    (tmp_path / "verified" / "round-1.md").write_text("x", encoding="utf-8")
    assert hs.main(["--release-gate"]) == 0


def test_the_release_workflow_actually_calls_the_gate() -> None:
    """The wiring, not the gate. The rule was stated in three documents and
    enforced on the release path in none of them; grep for the call site rather
    than believing the subcommand exists (CLAUDE.md rule 9's lesson, applied to
    a workflow instead of a `cancel()`)."""
    workflow = (
        Path(__file__).resolve().parents[1] / ".github" / "workflows" / "release.yml"
    ).read_text(encoding="utf-8")
    assert "handshake.py --release-gate" in workflow
    # And before the build, so a blocked release costs seconds not an AppImage.
    assert workflow.index("handshake.py --release-gate") < workflow.index(
        "Build the AppImage"
    )
