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
import re
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


def _body(hs: ModuleType, section: object) -> str:
    """Filler long enough to clear the length floor, containing the section's
    own subject keywords.

    The keywords are what makes this a *complete* file under the round-6 rule:
    a heading lettered §G over 300 characters of `xxxx` is not a revert-proof
    section, and the checker now says so. Padding with the subject rather than
    with `x` keeps this fixture honest instead of teaching the product that
    filler counts as content.
    """
    subject = " ".join(getattr(section, "keywords", ()) or ("content",))
    return (subject + " ") * 4 + "x" * (hs.MIN_SECTION_CHARS + 250)


def _complete_inbound(hs: ModuleType) -> str:
    """A file that satisfies every rule, built from the spec itself.

    Built from ``INBOUND_SECTIONS`` rather than hand-written so that adding a
    required section cannot leave this fixture quietly incomplete — the
    "positive control" stays positive by construction.
    """
    return "# cyanrip → Platterpus\n\n" + "\n\n".join(
        f"## {s.key}\n\n{_body(hs, s)}" for s in hs.INBOUND_SECTIONS
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
    text = "# cyanrip → Platterpus\n\n" + "\n\n".join(
        f"## {s.key}\n\n{_body(hs, s)}" for s in hs.INBOUND_SECTIONS if s.key != dropped
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
    section_f = next(s for s in hs.INBOUND_SECTIONS if s.key == "F")
    text = _complete_inbound(hs).replace(
        f"## F\n\n{_body(hs, section_f)}",
        # Long enough to carry the subject (so the ABSENT floor does not fire
        # instead) yet under the length floor — the "heading with nothing real
        # under it" case this test is named for.
        "## F\n\nverified: TODO",
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
        section = next(s for s in hs.INBOUND_SECTIONS if s.key == key)
        # ONE keyword, not all of them. §H's keyword list literally contains
        # "nothing found", which is also an `_EXPLICIT_NOTHING` phrase — joining
        # the whole list made this fixture assert the null case it was supposed
        # to be withholding, and the test passed for the wrong reason.
        text = _complete_inbound(hs).replace(
            f"## {key}\n\n{_body(hs, section)}",
            f"## {key}\n\n{section.keywords[0]}: we looked at this "
            f"area during the round and moved on.",
        )
        path = tmp_path / f"round-{key}.md"
        path.write_text(text, encoding="utf-8")
        assert any(f"§{key}" in p for p in hs.check_inbound(path)), (
            f"§{key} trailed off without stating the null case and was accepted"
        )


def test_an_explicit_nothing_is_accepted(hs: ModuleType, tmp_path: Path) -> None:
    """The other half: "no changes" *is* a complete answer and must not be
    nagged, or the check trains people to pad sections with filler."""
    section_d = next(s for s in hs.INBOUND_SECTIONS if s.key == "D")
    text = _complete_inbound(hs).replace(
        f"## D\n\n{_body(hs, section_d)}",
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
    styles = ["## {k}", "### §{k} — Title", "## {k}. Title", "**{k}**"]
    text = "# r\n\n" + "\n\n".join(
        styles[i % len(styles)].format(k=s.key) + f"\n\n{_body(hs, s)}"
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
    # The verification must DECLARE a verdict; presence alone no longer closes a
    # round (see `test_a_verification_that_holds_does_not_close_the_round`).
    (tmp_path / "verified" / "round-9.md").write_text(
        "**GO on pin `abc1234`.**", encoding="utf-8"
    )

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

    (tmp_path / "verified" / "round-9.md").write_text(
        "**GO on pin `abc1234`.**", encoding="utf-8"
    )
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
    # Round 9, deliberately: rounds 1-3 are grandfathered past the verdict
    # requirement (`RETROSPECTIVE_ROUNDS`), so building this scenario on round 1
    # would exercise the exemption instead of the gate.
    (tmp_path / "outbound" / "round-9.md").write_text("x", encoding="utf-8")
    monkeypatch.setattr(hs, "HANDSHAKE_DIR", tmp_path)

    # Sent, nothing back: OPEN → blocked.
    assert hs.main(["--release-gate"]) == 1

    # Their return arrives but we have not verified it. A partly-verified pin is
    # an unverified pin, so this must STILL block.
    (tmp_path / "inbound" / "round-9.md").write_text("x", encoding="utf-8")
    assert hs.main(["--release-gate"]) == 1

    # Our verification exists but declares no verdict. Still blocked: a file that
    # does not say whether the pin may move has not answered the question.
    verified = tmp_path / "verified" / "round-9.md"
    verified.write_text("x", encoding="utf-8")
    assert hs.main(["--release-gate"]) == 1

    # A verification that HOLDS is not a close. This is the round-7 case, and the
    # reason presence-only was wrong: the file was there, the round was not done.
    verified.write_text("**HOLD on `d5d12ec`.** Mid-round lap.", encoding="utf-8")
    assert hs.main(["--release-gate"]) == 1

    # Both directions done AND the verdict is GO → allowed.
    verified.write_text("**GO on pin `abc1234`.**", encoding="utf-8")
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


# --- the round-6 lesson: the gate that guards the handshake had never been -----
# --- asked "can this be satisfied by finding nothing?" ------------------------


def test_prose_beginning_a_line_does_not_satisfy_a_section(
    hs: ModuleType, tmp_path: Path
) -> None:
    """Round 6's §I passed on the sentence "I wrote, of your continuation-line
    sweep:".

    Every required section is single-lettered, and English sentences begin with
    "A ", "I " and "We ". The first checker accepted a bare letter at line start
    as a heading, so ordinary writing satisfied structure — and the section it
    credited (the provider contract) really was in the file, which is what made
    the bug invisible: a right answer for a wrong reason.

    Swept over every section, because getting this right for §I and wrong for §A
    would look identical from outside.
    """
    for section in hs.INBOUND_SECTIONS:
        subject = " ".join(section.keywords or ("content",))
        # A whole file of prose: each required subject IS discussed (so the
        # keyword floor is satisfied) and every line begins with the section's
        # letter — but not one heading marker anywhere.
        prose = "\n\n".join(
            f"{s.key} sentence about {' '.join(s.keywords or ('content',))} "
            + "written as flowing prose with no heading marker at all. " * 4
            for s in hs.INBOUND_SECTIONS
        )
        path = tmp_path / f"prose-{section.key}.md"
        path.write_text(prose, encoding="utf-8")
        problems = hs.check_inbound(path)
        assert any(f"§{section.key}" in p for p in problems), (
            f"§{section.key} ({subject}) was satisfied by a line of prose "
            f"beginning with '{section.key} ': {problems}"
        )


def test_a_relettered_section_covering_a_different_subject_is_caught(
    hs: ModuleType, tmp_path: Path
) -> None:
    """Round 6's §G ("Revert-proof") passed because they lettered an unrelated
    section `## G. Asks back`. The word "revert" appears **zero** times in that
    file. The checker reported one problem; there were two.

    The letter answers "did you label it", the keywords answer "did you write
    it", and only the pair is a check. Relettering alone must still be tolerated
    — see the next test — so this asserts specifically on the *subject* being
    absent while the letter is present.
    """
    section_g = next(s for s in hs.INBOUND_SECTIONS if s.key == "G")
    assert section_g.keywords, "§G lost its subject keywords; this test is vacuous"
    text = _complete_inbound(hs).replace(
        f"## G\n\n{_body(hs, section_g)}",
        "## G. Asks back\n\n" + "Things I would like from you next round. " * 12,
    )
    path = tmp_path / "relettered.md"
    path.write_text(text, encoding="utf-8")
    problems = hs.check_inbound(path)
    assert any("§G" in p and "ABSENT" in p for p in problems), problems
    # And it says WHY, naming both halves — a bare "missing" would send them
    # hunting for a heading that is right there.
    assert any("lettered G" in p for p in problems), problems


def test_the_real_round_6_file_reproduces_what_the_old_checker_missed(
    hs: ModuleType,
) -> None:
    """The revert-proof for the checker fix, against the committed artifact.

    `docs/testing.md` §5.u: when a committed artifact can settle a question, the
    test reads the artifact. The question is whether the fix catches what it was
    written for, and the round-6 correspondence is in this repo.

    Checked against round 6 **alone**, which is what the old checker was run on
    when the file arrived. It reported one problem (§J). There were three more:
    §G's subject ("revert") appears zero times while a section is lettered G,
    §B's provenance markers are absent, and §I was credited to a line of prose
    beginning "I wrote,". Their amendment later supplied the revert-proof
    unprompted — see the next test — which is why this reads the file the finding
    was actually made against rather than the pair.
    """
    six = _REPO_ROOT / "docs" / "handshake" / "inbound" / "round-6.md"
    assert six.exists(), "round-6.md is not committed"
    problems = hs.check_inbound(six)
    keys = {p.split(" ")[0] for p in problems}
    assert {"§B", "§G", "§I", "§J"} <= keys, (
        f"the round-6 misses are no longer reproduced: {problems}"
    )
    # The two that the LETTER matched, so a bare "missing" would have sent them
    # hunting for a heading that is right there.
    assert any("§G" in p and "lettered G" in p for p in problems), problems


def test_the_amendment_supplies_what_the_return_file_lacked(hs: ModuleType) -> None:
    """Validating the pair is strictly better than validating either half.

    Round 6b's §2 carries the revert-proof round 6 did not — *"reverting the
    cachemodel to upstream's 1 fails four of its checks"* — so §G is satisfied by
    the pair. That is the behaviour the multi-file check exists for: requiring an
    amendment to restate all ten sections would make sending a correction within
    hours score worse in the record than folding it into the next round.
    """
    inbound = _REPO_ROOT / "docs" / "handshake" / "inbound"
    six, six_b = inbound / "round-6.md", inbound / "round-6b.md"
    assert six_b.exists(), "the round-6 amendment is not committed"
    pair = hs.check_inbound(six, six_b)
    assert not any("§G" in p for p in pair), (
        "§G is reported for the pair, but round 6b states the revert-proof: "
        + str(pair)
    )
    # Floor, both directions: the pair must beat each half, or the union is doing
    # nothing and this test would pass on a checker that ignored the second file.
    assert len(pair) < len(hs.check_inbound(six))
    assert len(pair) < len(hs.check_inbound(six_b))
    assert len(pair) >= 1, "the pair is now clean — update the finding, not the test"


def test_an_amendment_belongs_to_its_round_rather_than_being_one(
    hs: ModuleType, tmp_path: Path
) -> None:
    """`round-6b.md` is round 6, not round 6b.

    Counting an amendment as its own round would report two open rounds where one
    was corrected — and would make sending a correction within hours score worse
    in the record than folding it silently into the next round. The wrong
    incentive, encoded in the tooling.
    """
    for name in ("outbound", "inbound", "verified"):
        (tmp_path / name).mkdir()
    for name in ("outbound", "inbound", "verified"):
        (tmp_path / name / "round-6.md").write_text("x", encoding="utf-8")
    (tmp_path / "inbound" / "round-6b.md").write_text("x", encoding="utf-8")
    (tmp_path / "verified" / "round-6.md").write_text(
        "**GO on pin `abc1234`.**", encoding="utf-8"
    )

    lines = [ln for ln in hs.round_status(tmp_path) if ln.startswith("round-")]
    assert lines == ["round-6: sent=yes returned=yes verified=yes (GO)  -> CLOSED"], (
        lines
    )
    assert hs.round_number(Path("round-6b.md")) == 6
    assert hs.round_number(Path("round-6.md")) == 6
    # A name that is not a round must be ignored, not crash the report.
    assert hs.round_number(Path("notes.md")) is None


# --- the round-7 lesson: a HOLD is not a close --------------------------------
# The gate keyed on the verification file EXISTING. Round 7's verification is a
# deliberate mid-round HOLD — the fork's §15 asked us to hold — so `--status`
# reported it CLOSED and `--release-gate` allowed a release, while the deviation
# policy forbids releasing or moving the pin with a round open. Same shape as the
# round-6 finding one file up: the check was satisfied by the *wrong thing*, and
# it reported the right-looking answer for a reason that had nothing to do with
# the question.


def test_a_verification_that_holds_does_not_close_the_round(
    hs: ModuleType, tmp_path: Path
) -> None:
    """A HOLD and a GO must land on opposite sides of the gate.

    Both branches, in one test, off the same files — so "reports OPEN" cannot be
    satisfied by a function that ignores the verdict and reports OPEN always.
    """
    for name in ("outbound", "inbound", "verified"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "round-9.md").write_text("x", encoding="utf-8")
    verified = tmp_path / "verified" / "round-9.md"

    verified.write_text(
        "# Round 9 — Platterpus verification\n\n"
        "**HOLD on `d5d12ec`. The pin has NOT moved.** Mid-round lap.\n",
        encoding="utf-8",
    )
    held = hs.round_status(tmp_path)
    assert held[0].endswith("OPEN"), held
    assert "HOLD" in held[0], "the status must say WHY it is open, not just that"
    assert any("do not release" in ln for ln in held)

    verified.write_text("**GO on pin `d5d12ec`.**\n", encoding="utf-8")
    went = hs.round_status(tmp_path)
    assert went[0].endswith("CLOSED"), went
    assert not any("do not release" in ln for ln in went)


def test_a_verification_with_no_verdict_does_not_close_a_round(
    hs: ModuleType, tmp_path: Path
) -> None:
    """Fail closed. A verification that never says GO or HOLD has not answered
    the only question the protocol asks of it, and the safe reading of an
    unanswered question is "not yet"."""
    for name in ("outbound", "inbound", "verified"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "round-9.md").write_text(
            "Plenty of prose, no verdict anywhere in it.", encoding="utf-8"
        )
    lines = hs.round_status(tmp_path)
    assert lines[0].endswith("OPEN"), lines
    assert "verified=NO" in lines[0], lines


def test_prose_about_the_verdict_is_not_the_verdict(hs: ModuleType) -> None:
    """The specific way this could have gone wrong.

    Round 7's file says, in its opening paragraph, *"this is a mid-round reply,
    not a closing GO"* — and declares **HOLD** further down. A pattern searching
    anywhere in the text for "GO" reads that file as a GO and closes the round
    off a sentence saying the opposite. Anchored to the line start, so the
    marker is a *declaration* and prose is prose.
    """
    prose = (
        "This is a mid-round reply, not a closing GO. Your §15 asked us to hold.\n"
        "We will send a GO when the corpus lands.\n"
        "\n"
        "**HOLD on `d5d12ec`.**\n"
    )
    assert hs.verification_verdict(prose) == "HOLD"
    # And the converse: a bolded GO at a line start IS the declaration.
    assert hs.verification_verdict("**GO on pin `abc1234`.** Everything checked.") == (
        "GO"
    )
    assert hs.verification_verdict("no verdict here at all") is None
    # A word merely starting with the letters must not match.
    assert hs.verification_verdict("**GONE, and HOLDINGS aside, we agree.**") is None


def test_conflicting_verdicts_read_as_hold(hs: ModuleType) -> None:
    """A file that declares both changed its mind mid-draft. A release wrongly
    blocked is a delay; a release wrongly allowed ships an unverified pin."""
    assert hs.verification_verdict("**GO on `a`.**\n\n**HOLD on `a`.**\n") == "HOLD"


def test_the_newest_verification_file_supplies_the_verdict(
    hs: ModuleType, tmp_path: Path
) -> None:
    """An amendment supersedes what it corrects — in *this* direction too.

    Reading the oldest file would let a since-withdrawn GO keep a round closed,
    which is exactly the situation round 6b created on the fork's side: a pin
    asked for in the morning and withdrawn by evening.
    """
    for name in ("outbound", "inbound", "verified"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "round-9.md").write_text("x", encoding="utf-8")
    (tmp_path / "verified" / "round-9.md").write_text(
        "**GO on pin `abc1234`.**", encoding="utf-8"
    )
    assert hs.round_status(tmp_path)[0].endswith("CLOSED")

    (tmp_path / "verified" / "round-9b.md").write_text(
        "**HOLD on `abc1234`.** Withdrawing yesterday's GO.", encoding="utf-8"
    )
    lines = hs.round_status(tmp_path)
    assert lines[0].endswith("OPEN"), lines
    assert "HOLD" in lines[0]


def test_the_real_verification_files_all_declare_a_verdict(hs: ModuleType) -> None:
    """Read the committed artifacts, not my memory of them.

    CLAUDE.md: *when a committed artifact can settle a question, the test should
    read the artifact.* Every verification file from round 4 on must declare a
    verdict; rounds 1–3 are the named retrospective exceptions and are the only
    ones allowed to be silent.
    """
    files = sorted(hs.VERIFIED_DIR.glob("round-*.md"))
    assert len(files) >= 6, "the verification record has shrunk"
    silent: list[str] = []
    verdicts: dict[str, str] = {}
    for path in files:
        num = hs.round_number(path)
        assert num is not None, path
        verdict = hs.verification_verdict(path.read_text(encoding="utf-8"))
        if verdict is None:
            if num not in hs.RETROSPECTIVE_ROUNDS:
                silent.append(path.name)
        else:
            verdicts[path.name] = verdict
    assert not silent, (
        "verification file(s) declare no GO/HOLD verdict, so the round cannot be "
        f"read as closed or open: {silent}"
    )
    # Floor + non-triviality: this must not pass by finding nothing, and it must
    # have seen BOTH verdicts, or it is only testing one branch of the parser
    # against the real corpus.
    assert len(verdicts) >= 4, verdicts
    assert set(verdicts.values()) == {"GO", "HOLD"}, (
        "the real record no longer contains one of each verdict, so this test has "
        f"stopped comparing them: {verdicts}"
    )


def test_the_retrospective_grandfather_list_may_not_grow(hs: ModuleType) -> None:
    """A ratchet, not a preference.

    Rounds 1–3 were reconstructed in one sitting long after they closed, before
    the verdict convention existed. That is a closed historical set. Left
    unpinned, "add the round to RETROSPECTIVE_ROUNDS" is a one-line way to make
    an open round read as closed — which is the defect this whole section exists
    to prevent, re-introduced through the exemption instead of the check.
    """
    assert hs.RETROSPECTIVE_ROUNDS == frozenset({1, 2, 3}), (
        "the retrospective grandfather list may shrink, never grow: a round that "
        "needs an exemption to close needs a verdict instead"
    )


# --- the correspondence index must not fall behind the correspondence ---------
# `docs/handshake/README.md` described the closing rule as "all three files
# exist" — the rule that was wrong — and its round-by-round map named exactly one
# round, four rounds in. `docs/README.md` links it as "the round-by-round map",
# so a stale map is a broken promise in the canonical index.


def test_the_handshake_readme_covers_every_round_on_disc(hs: ModuleType) -> None:
    """Every round with a file must have a row in the correspondence index.

    Derived from the directories rather than from a list kept here, so the check
    cannot drift the same way the map did.
    """
    readme = (hs.HANDSHAKE_DIR / "README.md").read_text(encoding="utf-8")
    rounds: set[int] = set()
    for sub in ("outbound", "inbound", "verified"):
        for path in (hs.HANDSHAKE_DIR / sub).glob("round-*.md"):
            num = hs.round_number(path)
            if num is not None:
                rounds.add(num)
    assert len(rounds) >= 4, f"only {len(rounds)} rounds found — glob broken?"

    # A row, not a mention: the round number must open a table row, which is what
    # makes it an entry in the map rather than a passing reference in prose.
    rows = {
        int(m.group("n"))
        for m in re.finditer(
            r"^\|\s*\**\s*(?P<n>\d{1,4})\s*\**\s*\|", readme, re.MULTILINE
        )
    }
    missing = sorted(rounds - rows)
    assert not missing, (
        "docs/handshake/README.md has no round-by-round row for round(s) "
        f"{missing} — docs/README.md links it as the map, so a stale map is a "
        "broken promise in the canonical index"
    )


def test_the_handshake_readme_states_the_verdict_rule(hs: ModuleType) -> None:
    """The index must not teach the rule the gate no longer uses.

    It said a round is closed "when all three exist". That sentence was the
    defect, written down — and a reader who believes it will read `--status`'s
    output as agreement.
    """
    readme = (hs.HANDSHAKE_DIR / "README.md").read_text(encoding="utf-8")
    assert "GO" in readme and "HOLD" in readme, (
        "the correspondence index never mentions the GO/HOLD verdict that decides "
        "whether a round is closed"
    )
    # And it must not still assert the presence-only rule as sufficient.
    assert not re.search(r"CLOSED\*{0,2}\s+only when all three exist", readme), (
        "docs/handshake/README.md still states the presence-only closing rule"
    )


# --- readiness: the shapes the fork's NEXT file could arrive in ----------------
# Round 7 is open and their reply is expected. Two shapes are legitimate — an
# amendment to round 7, or a fresh round 8 — and the machinery must handle both
# without a human deciding which. Written as readiness rather than after the fact,
# because the last two rounds each surprised the tooling once.


def test_their_amendment_to_an_open_round_keeps_it_open_on_our_hold(
    hs: ModuleType, tmp_path: Path
) -> None:
    """`inbound/round-7b.md` is round 7, and our HOLD still governs.

    Their reply to a mid-round verification is an amendment (protocol §7.4), so it
    must not read as a new round — and it must not close the old one either. Only
    *our* verdict closes a round; a new file from them is more input, not a
    decision.
    """
    for name in ("outbound", "inbound", "verified"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "round-7.md").write_text("x", encoding="utf-8")
    (tmp_path / "verified" / "round-7.md").write_text(
        "**HOLD on `d5d12ec`.** Mid-round lap.", encoding="utf-8"
    )
    (tmp_path / "inbound" / "round-7b.md").write_text(
        "our reply to your lap 1", encoding="utf-8"
    )

    lines = [ln for ln in hs.round_status(tmp_path) if ln.startswith("round-")]
    assert lines == [
        "round-7: sent=yes returned=yes verified=yes (HOLD — not closed)  -> OPEN"
    ], lines
    # And once we send a GO — as `round-7c.md`, the newest verified file — it closes.
    (tmp_path / "verified" / "round-7c.md").write_text(
        "**GO on `d5d12ec`.** Lap 2 closes it.", encoding="utf-8"
    )
    closed = [ln for ln in hs.round_status(tmp_path) if ln.startswith("round-")]
    assert closed[0].endswith("CLOSED"), closed


def test_a_fresh_round_from_them_before_we_send_ours_reads_as_unsent(
    hs: ModuleType, tmp_path: Path
) -> None:
    """`inbound/round-8.md` with no `outbound/round-8.md` is OPEN, and says why.

    The protocol is that we send first, so their opening a round out of order is a
    real state the record must represent rather than paper over — `sent=NO` is the
    line that tells a reader which half is missing and whose it is.
    """
    for name in ("outbound", "inbound", "verified"):
        (tmp_path / name).mkdir()
    for name in ("outbound", "inbound"):
        (tmp_path / name / "round-7.md").write_text("x", encoding="utf-8")
    (tmp_path / "verified" / "round-7.md").write_text(
        "**GO on `d5d12ec`.**", encoding="utf-8"
    )
    (tmp_path / "inbound" / "round-8.md").write_text("we opened one", encoding="utf-8")

    lines = [ln for ln in hs.round_status(tmp_path) if ln.startswith("round-")]
    assert len(lines) == 2, lines
    assert lines[0].endswith("CLOSED"), lines[0]
    assert "sent=NO" in lines[1] and lines[1].endswith("OPEN"), lines[1]
    # The release gate must block on it: an unanswered round of theirs is still an
    # open round, and "we did not start it" is not an exemption.
    assert any("do not release" in ln for ln in hs.round_status(tmp_path))


def test_check_inbound_reports_the_missing_provider_contract(hs: ModuleType) -> None:
    """Their round-7 file has no §I, and `--check` must say so, by name.

    Read off the committed artifact rather than a synthetic file (§5.u). This is
    the finding our reply's §7 asked them to fix, and the assertion is here so
    that when they send it, this test is what confirms it landed — rather than my
    reading the file and forming an opinion.
    """
    path = hs.INBOUND_DIR / "round-7.md"
    assert path.is_file(), "the committed round-7 inbound file is missing"
    problems = hs.check_inbound(path)
    assert any("§I" in p for p in problems), (
        "the checker no longer reports round 7's absent provider contract — if "
        "they have since supplied it, update this test to assert the round is "
        f"clean instead of deleting it: {problems}"
    )
