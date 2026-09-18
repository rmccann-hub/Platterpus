"""The standing status is a claim about NOW, so something has to check it is.

**Why this file exists.** ``docs/handshake/outbound/platterpusstatus.md`` is the
first thing the peer project reads, and ``docs/cyanrip-handshake.md`` §7.6 says in
its own words that *"a stale standing status is worse than none"*. On 2026-09-13 it
was **seventeen days, seventeen patch versions and four rounds** out of date — still
announcing 0.6.30, pin ``d9c058c``, and *"round 15 not open"* — while the app was
0.6.47 on pin ``fe4d2c4`` with rounds 15 through 18 all closed.

**The instructive part is how it got there.** That file is the SURVIVOR of a
consolidation: two documents both described themselves as *"the standing answer,
rewritten in place"*, they drifted independently, and in August one was collapsed
into the other under ``CLAUDE.md`` rule #7. The consolidation fixed the
**duplication** and did nothing about the **decay**, because nothing checked the
survivor either. That is this repo's own *"does this document promise
completeness? then it needs a sweep, not a comment"* — applied to **currency**
rather than coverage, and it is the harder case: a stale map is wrong by omission
and nobody reviews a file for what is no longer true in it.

**So the fix is a gate, not a rewrite.** A rewrite is correct for seventeen days.

**Deliberately narrow.** This checks the handful of facts that are load-bearing
for the reader — version, pin, approving round, rounds-closed — by deriving each
from the code or the record and requiring the document to *state* it. It does not
grade prose, because a check nobody can satisfy gets deleted rather than obeyed.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_STATUS = _REPO_ROOT / "docs" / "handshake" / "outbound" / "platterpusstatus.md"
_VERIFIED = _REPO_ROOT / "docs" / "handshake" / "verified"
_INBOUND = _REPO_ROOT / "docs" / "handshake" / "inbound"

sys.path.insert(0, str(_REPO_ROOT / "src"))


def _status_text() -> str:
    """The document, with a FLOOR so an empty or moved file fails loudly.

    Every assertion below is of the form *"this string appears"*, and every one of
    them passes vacuously against a file that does not exist or has been emptied —
    which is the failure mode ``CLAUDE.md`` names as *can this check be satisfied
    by finding nothing?* The floor is what makes the answer no.
    """
    assert _STATUS.is_file(), (
        f"{_STATUS.relative_to(_REPO_ROOT)} is missing. It is the file the peer "
        "reads first and the one docs/cyanrip-handshake.md §7.6 designates as the "
        "only home for our standing answer. If it moved, move this gate with it."
    )
    text = _STATUS.read_text(encoding="utf-8")
    assert len(text) > 2000, (
        f"the standing status is only {len(text)} bytes. A status that short is "
        "not a status; this floor exists so the string checks below cannot pass by "
        "matching against nothing."
    )
    return text


def test_the_standing_status_names_the_version_we_actually_ship() -> None:
    """The single most-read fact in it, and the one that decayed first."""
    from platterpus import __version__

    text = _status_text()
    assert __version__ in text, (
        f"the standing status does not mention {__version__}, the version in "
        "src/platterpus/__init__.py. The peer reads this file to learn where we "
        "are; a version it does not name is a version it is not describing. "
        "Rewrite the file in place — never add a dated sibling (§7.6)."
    )


def test_the_standing_status_names_the_pin_we_actually_run() -> None:
    """A wrong pin here points the peer's whole review at the wrong build."""
    from platterpus.deps import fork_source

    text = _status_text()
    assert fork_source.FORK_PIN in text, (
        f"the standing status does not mention pin {fork_source.FORK_PIN!r}, which "
        "is what deps/fork_source.py holds. This is the value the peer uses to "
        "decide which of their builds we are talking about."
    )


def test_the_standing_status_names_the_round_that_approved_the_pin() -> None:
    """Derived from the constant, which is itself derived from the record.

    Chained deliberately: ``handshake_approval`` is already held to the handshake
    files by ``tests/test_fork_source.py``, so requiring the document to agree with
    the constant transitively requires it to agree with the record — without this
    gate needing its own opinion about which round closed when.
    """
    from platterpus import handshake_approval as ha

    text = _status_text()
    assert re.search(rf"\bround\s+{ha.APPROVED_BY_ROUND}\b", text, re.IGNORECASE), (
        f"the standing status never says 'round {ha.APPROVED_BY_ROUND}', which is "
        "handshake_approval.APPROVED_BY_ROUND — the round whose bilateral GO "
        "approves the pin we ship. The file was found announcing round 14 while "
        "the constant said 18."
    )


def _newest_round_on_disk() -> int:
    """Highest round number with a file in verified/ or inbound/.

    Read off the filesystem rather than a constant, because the point of this gate
    is to catch the document lagging the record, and a constant is one more thing
    that can lag it.
    """
    rounds: set[int] = set()
    for directory in (_VERIFIED, _INBOUND):
        for path in directory.glob("round-*-lap-*.md"):
            match = re.match(r"round-(\d+)-lap-\d+\.md$", path.name)
            if match:
                rounds.add(int(match.group(1)))
    assert rounds, (
        "no round-NN-lap-MM.md files found in verified/ or inbound/. Either the "
        "handshake record moved or this glob stopped matching — and a 'newest "
        "round' computed over an empty set would let every claim below pass."
    )
    return max(rounds)


def test_the_standing_status_does_not_lag_the_handshake_record() -> None:
    """The failure that actually happened: four rounds closed, the file said none had.

    It announced *"round 15 — not open, and it is yours to open"* while rounds 15,
    16, 17 and 18 had all closed GO/GO. Nothing in the repository disagreed with
    it, because nothing was looking.
    """
    newest = _newest_round_on_disk()
    text = _status_text()
    assert re.search(rf"\b{newest}\b", text), (
        f"round {newest} has files in the handshake record and the standing status "
        f"never mentions the number {newest}. The document is behind the record it "
        "exists to summarise. Rewrite it in place (§7.6); do not add a sibling."
    )


def _derived_round_state(number: int) -> str:
    """``"OPEN"`` or ``"CLOSED"`` for one round, from the gate's own computation.

    Read from :func:`handshake.round_status` rather than re-derived here, so this
    test and ``--status`` cannot disagree about a round. Two surfaces answering one
    question off different keys is the defect this repo has paid for more than once.
    """
    import importlib.util  # noqa: PLC0415

    spec = importlib.util.spec_from_file_location(
        "handshake", _REPO_ROOT / "scripts" / "handshake.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # REGISTERED BEFORE EXECUTION, and it is not optional: `handshake.py` defines
    # dataclasses, and `dataclasses` resolves a class's annotations through
    # `sys.modules[cls.__module__].__dict__`. Load it unregistered and that lookup
    # returns None, which surfaces as a bare `AttributeError` inside the stdlib and
    # reads like a broken dataclass rather than a broken import.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    prefix = f"round-{number}:"
    for line in module.round_status():
        if line.startswith(prefix):
            return "CLOSED" if line.rstrip().endswith("-> CLOSED") else "OPEN"
    raise AssertionError(
        f"handshake.round_status() reported no line for round {number}, which has "
        "files on disk. Either the gate stopped seeing the round or this prefix "
        "match broke -- and a state derived from no line would let the assertions "
        "below pass over anything."
    )


def test_the_standing_status_does_not_CONTRADICT_the_newest_round_s_state() -> None:
    """The mention test above can be satisfied by the WRONG sentence, and was.

    **This is a real miss in this file, found 2026-09-18.** The test directly above
    was written because the document had announced *"round 15 -- not open, and it is
    yours to open"* while rounds 15 to 18 had all closed. It checks that the newest
    round's **number** appears somewhere in the text. On 2026-09-18 the document
    read:

        | round 21 | **not open.** Yours to open, ... |

    with four round-21 laps on disk and our own lap 4 written -- and the test passed,
    because the number 21 is right there **inside the false sentence**. The gate
    written for that exact wording sailed over the same wording one round later.

    That is ``CLAUDE.md``'s *"can it be satisfied by the WRONG thing?"*, and its
    remedy verbatim: *where a check matches on a label, make it also require the
    subject -- the label answers "did they name it", the content answers "did they
    write it", and only the pair is a check.* Both tests are kept. The one above
    catches a round the document never mentions; this one catches a round it
    mentions and describes backwards.

    **Deliberately one-directional in what it forbids.** It asserts the document
    does not *deny* an open round, and does not try to grade how well it describes
    one -- a check nobody can satisfy gets deleted rather than obeyed, which is the
    standing rule for this file.
    """
    newest = _newest_round_on_disk()
    state = _derived_round_state(newest)
    pattern = re.compile(rf"round[\s-]+{newest}\b", re.IGNORECASE)
    lines = [line for line in _status_text().splitlines() if pattern.search(line)]
    assert lines, (
        f"round {newest} has files in the handshake record and no line of the "
        "standing status mentions it. The test above should have caught this "
        "first; if it did not, its pattern and this one have diverged."
    )

    if state != "OPEN":
        return

    denials = ("not open", "not yet open", "yours to open", "is not yet a round")
    for line in lines:
        lowered = line.casefold()
        for denial in denials:
            assert denial not in lowered, (
                f"handshake.round_status() computes round {newest} as OPEN -- it has "
                f"laps on disk -- and the standing status says {denial!r} about it:\n"
                f"  {line.strip()[:200]}\n"
                "This is the first document the peer reads. Rewrite the row in "
                "place (cyanrip-handshake.md 7.6); do not add a sibling."
            )
    assert any("open" in line.casefold() for line in lines), (
        f"round {newest} is OPEN and the standing status mentions it without ever "
        "saying so. Stating the state is the whole job of that row -- a reader who "
        "has to infer it from what is absent is reading a map that is wrong by "
        "omission, which is exactly how this file decayed before."
    )


def test_the_standing_status_says_where_the_peer_should_read_us() -> None:
    """Transport moved to git on 2026-09-13, so the file must carry the addresses.

    The maintainer's instruction was that laps stop travelling by hand: each side
    commits to its own public repo and the other reads it. That only works if both
    sides know the ref and the path — and the one document guaranteed to be read
    first is the right place to say so.

    Checked as a set of concrete strings rather than by grading prose: the repo,
    the ref of record, and the directory our laps live in. If any of these change,
    this fails and the peer's instructions get updated in the same commit.
    """
    text = _status_text()
    for needle, why in (
        ("rmccann-hub/Platterpus", "the repository they read"),
        ("docs/handshake/outbound/", "where our laps are"),
        ("rmccann-hub/cyanrip", "the repository we read"),
        ("platterpus-fork", "the ref of theirs we read"),
    ):
        assert needle in text, (
            f"the standing status never names {needle!r} — {why}. Since 2026-09-13 "
            "laps travel by git rather than by hand, so an address left unstated is "
            "a lap neither side can find."
        )


def test_the_gate_is_not_vacuous() -> None:
    """Prove the checks above can FAIL — by mutating the text, not by forbidding words.

    **The first version of this test forbade the stale values** (``0.6.30``,
    ``d9c058c``) anywhere in the file, and it failed on the document's own note
    explaining that it HAD been stale. That is the same defect the approved-pair
    guard hit on its own changelog entry: *a declaration is what a document states,
    never what it quotes*, and a blanket string ban cannot tell the two apart. The
    convenient repair — an allowlist, or blanking quoted spans — would have made the
    gate answer a subtly different question than the one it is named for.

    So this proves the property directly instead. Each check is re-run against a
    copy of the real text with its subject removed, and must fail there. That
    constrains the document not at all, and is strictly stronger than a word ban:
    a word ban shows the value is absent, this shows the CHECK is load-bearing.

    Same discipline as ``scripts/revert_probe.py`` — a string check never observed
    to fail is indistinguishable from one that cannot.
    """
    from platterpus import __version__
    from platterpus.deps import fork_source

    text = _status_text()

    # Assert the real thing passes first. Without this the mutation below could be
    # "failing" because the subject was never there — a mutation test whose subject
    # is already absent proves nothing, and reads exactly like one that works.
    assert __version__ in text and fork_source.FORK_PIN in text, (
        "preconditions for the mutation check are not met — see the two tests "
        "above, which name the missing value"
    )

    for subject, label in ((__version__, "version"), (fork_source.FORK_PIN, "pin")):
        mutated = text.replace(subject, "\u2014redacted\u2014")
        # The mutation LANDED — asserted rather than assumed, because a revert or
        # redaction that silently did nothing is this repo's recorded way to get a
        # passing run that proves the opposite of what it claims (four measured
        # times, `CLAUDE.md` *prove the revert landed before believing the run*).
        assert mutated != text, (
            f"redacting the {label} changed nothing, so the assertion below would "
            "hold for a reason that has nothing to do with the check"
        )
        # And the check the test above performs now FAILS on the mutated text.
        assert subject not in mutated, (
            f"the {label} survived its own redaction — it appears in a form "
            "`str.replace` did not reach, so this proof does not cover it"
        )

    # The round check too, exercised through the same regex the real test uses so a
    # change to that pattern cannot pass here while failing there.
    from platterpus import handshake_approval as ha

    pattern = rf"\bround\s+{ha.APPROVED_BY_ROUND}\b"
    assert re.search(pattern, text, re.IGNORECASE), "precondition: the round is named"
    blanked = re.sub(pattern, "round ZZ", text, flags=re.IGNORECASE)
    assert blanked != text, "blanking the round number changed nothing"
    assert not re.search(pattern, blanked, re.IGNORECASE), (
        "the round number survived being blanked, so the round check is not "
        "shown to be capable of failing"
    )
