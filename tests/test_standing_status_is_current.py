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

import datetime
import functools
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType

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


def test_the_APPROVED_BY_row_itself_names_the_approval_record() -> None:
    """The test above asks whether *"round N"* appears ANYWHERE, and on
    2026-09-22 it passed over a table whose `approved by` row still said
    **round 21, for Platterpus 0.6.50** — two rounds and two app versions stale —
    because the section heading directly above it said *"round 23 CLOSED"*. A
    heading that is current lent its round number to a row that was not.

    So this reads the ROW, and requires both halves of the approval there: the
    round and the app version it approved the pin for.
    """
    from platterpus import handshake_approval as ha

    text = _status_text()
    rows = [line for line in text.splitlines() if line.startswith("| approved by |")]
    assert len(rows) == 1, (
        f"expected exactly one '| approved by |' row in the standing status, found "
        f"{len(rows)} — if the table was restructured, move this gate with it"
    )
    row = rows[0]
    # Read the cell's DECLARED HEAD, not the whole cell. The first version of
    # this gate searched the row and was proved vacuous by the revert probe the
    # same day: the row's own prose says "round 23 reviewed `2cce60d`" and
    # "not a repeat of 0.6.52's", so a head reverted to round 21 / 0.6.50 still
    # passed — the flaw one level down from the heading that hid it before.
    head = re.match(
        r"^\| approved by \| \*\*round (?P<round>\d+)\*\*, for Platterpus "
        r"\*\*(?P<version>[0-9][0-9a-z.]*)\*\*",
        row,
    )
    assert head, (
        "the 'approved by' row no longer opens with '**round N**, for Platterpus "
        f"**X.Y.Z**', so this gate cannot read its claim: {row[:160]}"
    )
    assert int(head.group("round")) == ha.APPROVED_BY_ROUND, (
        f"the standing status says the pin was approved by round "
        f"{head.group('round')}; handshake_approval.APPROVED_BY_ROUND is "
        f"{ha.APPROVED_BY_ROUND}"
    )
    assert head.group("version") == ha.APPROVED_FOR_PLATTERPUS_VERSION, (
        f"the standing status says the approval was for Platterpus "
        f"{head.group('version')}; handshake_approval.APPROVED_FOR_PLATTERPUS_VERSION "
        f"is {ha.APPROVED_FOR_PLATTERPUS_VERSION}"
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


# --- The D6 status block (the fork's release-cycle proposal, round 30) ---------
#
# The proposal's D6 asks each side to keep a block of `STATUS-` declarations at
# column 0, current in the same commit as any change to what they state, and
# checked by its own suite. The fork's own C2 had not landed when we wrote ours
# (round 30 lap 3 carries no DID for it), so this is the worked example, and the
# check is what makes it one: a block nothing checks decays like the prose did.


def _handshake_module() -> ModuleType:
    """`scripts/handshake.py`, loaded the way `_derived_round_state` loads it."""
    import importlib.util  # noqa: PLC0415

    if "handshake" in sys.modules:
        return sys.modules["handshake"]
    spec = importlib.util.spec_from_file_location(
        "handshake", _REPO_ROOT / "scripts" / "handshake.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # before exec: its dataclasses need it
    spec.loader.exec_module(module)
    return module


def _laps(direction: str) -> list[tuple[int, int, str, bool]]:
    """(round, lap, file name, released) for every lap file in one direction."""
    hs = _handshake_module()
    found = []
    for path in (_REPO_ROOT / "docs" / "handshake" / direction).glob("round-*.md"):
        named = hs.name_round_and_lap(path)
        if named is None:
            continue
        text = path.read_text(encoding="utf-8")
        released = hs.is_released_for_reading(text, round_hint=named[0])
        found.append((named[0], named[1], path.name, bool(released)))
    return sorted(found)


def _version_tuple(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in text.split("."))


#: The order §6c (v7) gives the block's single-occurrence lines. `STATUS-RELEASED`
#: *"appears once, in this position"*; the fork checks its block's order too
#: (their `64922e8`), so ours is checked positionally, not merely for presence.
_BLOCK_ORDER: tuple[str, ...] = (
    "ROUND",
    "LAPS",
    "RELEASED",
    "RELEASE-NEXT",
    "RUN-NEXT",
)

#: Floor on the release tags found, so the `STATUS-RELEASED` check cannot pass by
#: finding none. We had 100+ `v*` tags on 2026-10-05; a clone without tags (a
#: depth-1 checkout, or `git clone --no-tags`) is the case this refuses.
_MIN_RELEASE_TAGS: int = 50


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(_REPO_ROOT), *args],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    ).stdout.strip()


@functools.cache
def _newest_release() -> tuple[str, str, datetime.date]:
    """(version, full commit, commit's UTC date) of our newest release tag.

    **Read from the tags reachable from HEAD, not from ``__version__``.** A release
    PR bumps ``__version__`` before the tag exists, so ``__version__`` names the
    release being cut, while §6c's `STATUS-RELEASED` names the newest one
    *published*. ``--merged HEAD`` keeps a branch cut before a release reading the
    release it was cut after. Ordered by
    :func:`platterpus.update_check.release_sort_key`, the updater's own ordering,
    so a beta (``v0.6.66b1``) ranks above the release before it and below its own
    final release, as it does for a user.
    """
    from platterpus.update_check import release_sort_key

    tags = _git("tag", "-l", "v*", "--merged", "HEAD").split()
    keyed = [(release_sort_key(t[1:]), t) for t in tags]
    found = [(key, tag) for key, tag in keyed if key is not None]
    assert len(found) >= _MIN_RELEASE_TAGS, (
        f"only {len(found)} release tag(s) reachable from HEAD; the STATUS-RELEASED "
        "check needs the tags (CI's test job fetches them with fetch-depth: 0)"
    )
    tag = max(found)[1]
    commit = _git("rev-parse", f"{tag}^{{commit}}")
    stamp = datetime.datetime.fromisoformat(_git("log", "-1", "--format=%cI", commit))
    return tag[1:], commit, stamp.astimezone(datetime.UTC).date()


def _status_block_problems(text: str) -> list[str]:
    """Every way the block disagrees with the record, the code, or D6's shape.

    A pure function of the document's text, so the mutation test below can prove
    each check is load-bearing by feeding it a copy with one fact changed.
    """
    from platterpus import __version__
    from platterpus.deps import fork_source

    lines: dict[str, list[str]] = {}
    for match in re.finditer(r"(?m)^STATUS-([A-Z-]+): (.+)$", text):
        lines.setdefault(match.group(1), []).append(match.group(2).strip())
    problems: list[str] = []
    for key in _BLOCK_ORDER:
        if len(lines.get(key, [])) != 1:
            problems.append(f"STATUS-{key} appears {len(lines.get(key, []))} times")
    if not lines.get("OPEN"):
        problems.append("no STATUS-OPEN line: D6 repeats it once per open item")
    if problems:
        return problems
    order = [
        key
        for key in re.findall(r"(?m)^STATUS-([A-Z-]+): ", text)
        if key in _BLOCK_ORDER
    ]
    if order != list(_BLOCK_ORDER):
        problems.append(
            f"the block's lines are in the order {order}; §6c gives {list(_BLOCK_ORDER)}"
        )

    newest = _newest_round_on_disk()
    got = re.match(r"(\d+), (OPEN|CLOSED)\b", lines["ROUND"][0])
    if got is None:
        problems.append(
            f"STATUS-ROUND is not '<round>, OPEN|CLOSED': {lines['ROUND'][0]!r}"
        )
    else:
        if int(got.group(1)) != newest:
            problems.append(
                f"STATUS-ROUND names {got.group(1)}; the record's newest is {newest}"
            )
        state = _derived_round_state(newest)
        if got.group(2) != state:
            problems.append(
                f"STATUS-ROUND says {got.group(2)}; the gate computes {state}"
            )

    ours, theirs = _laps("outbound"), _laps("inbound")
    sent_ours = [name for _, _, name, released in ours if released]
    sent_theirs = [name for _, _, name, released in theirs if released]
    held = [lap for rnd, lap, _, released in ours if rnd == newest and not released]
    laps = re.match(
        r"newest sent (\S+) \(ours\), (\S+) \(theirs\); next .+; held (none|(\d+) carrying .+)$",
        lines["LAPS"][0],
    )
    if laps is None:
        problems.append(f"STATUS-LAPS is not in D6's shape: {lines['LAPS'][0]!r}")
    else:
        if not sent_ours or laps.group(1) != sent_ours[-1]:
            problems.append(
                f"STATUS-LAPS names {laps.group(1)} as ours; newest released is {sent_ours[-1:]}"
            )
        if not sent_theirs or laps.group(2) != sent_theirs[-1]:
            problems.append(
                f"STATUS-LAPS names {laps.group(2)} as theirs; newest released is {sent_theirs[-1:]}"
            )
        stated_held = [] if laps.group(3) == "none" else [int(laps.group(4))]
        if stated_held != held:
            problems.append(
                f"STATUS-LAPS says held {stated_held or 'none'}; round {newest} holds {held or 'none'}"
            )

    # A PLANNED release may move the constants: round N's closing release pins
    # the build round N reviewed and reviews the fork's next build, which does
    # not exist yet (option A, their D2). So `pins` is today's approved pin or
    # the build under review, and a build is named either by its commit or, not
    # yet released, as the fork's next `+platterpus.N`, N one past ours.
    reviewed = re.search(
        r"\+platterpus\.(\d+)$", fork_source.UNDER_REVIEW_TARGET.version
    )
    if reviewed is None:
        return [
            f"the build under review's version has no +platterpus.N: "
            f"{fork_source.UNDER_REVIEW_TARGET.version!r}"
        ]
    reviewed_n = int(reviewed.group(1))
    next_build = f"+platterpus.{reviewed_n + 1}"
    build = r"([0-9a-f]{7,40}|\+platterpus\.\d+)"

    def known_build(name: str) -> bool:
        return name in (fork_source.PIN_UNDER_REVIEW, next_build)

    # v7 §6c: `<version> at <commit>, <UTC date>[, hotfix: <why>]`, naming our
    # newest published release. The version and commit are read from git; the date
    # is the release's publication, which git does not record, so it is bounded
    # instead: not before the tagged commit, and not in the future.
    newest_version, newest_commit, committed_on = _newest_release()
    released = re.match(
        r"(\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?) at ([0-9a-f]{7,40}), "
        r"(\d{4}-\d{2}-\d{2})(?:, hotfix: \S.*)?$",
        lines["RELEASED"][0],
    )
    if released is None:
        problems.append(
            f"STATUS-RELEASED is not in §6c's shape: {lines['RELEASED'][0]!r}"
        )
    else:
        if released.group(1) != newest_version:
            problems.append(
                f"STATUS-RELEASED names {released.group(1)}; the newest release tag "
                f"reachable from HEAD is v{newest_version}"
            )
        if not newest_commit.startswith(released.group(2)):
            problems.append(
                f"STATUS-RELEASED names commit {released.group(2)}; "
                f"v{newest_version} is at {newest_commit[:12]}"
            )
        try:
            on = datetime.date.fromisoformat(released.group(3))
        except ValueError:
            problems.append(
                f"STATUS-RELEASED's date {released.group(3)!r} is not a date"
            )
        else:
            today = datetime.datetime.now(datetime.UTC).date()
            if not committed_on <= on <= today:
                problems.append(
                    f"STATUS-RELEASED says {on}; v{newest_version}'s commit is from "
                    f"{committed_on} (UTC), and today is {today}"
                )

    release = re.match(
        rf"(\d+\.\d+\.\d+), .+; pins ([0-9a-f]{{7,40}}), reviews {build}$",
        lines["RELEASE-NEXT"][0],
    )
    if release is None:
        problems.append(
            f"STATUS-RELEASE-NEXT is not in D6's shape: {lines['RELEASE-NEXT'][0]!r}"
        )
    else:
        if _version_tuple(release.group(1)) <= _version_tuple(__version__):
            problems.append(
                f"STATUS-RELEASE-NEXT names {release.group(1)}, not after {__version__}"
            )
        if release.group(2) not in (fork_source.FORK_PIN, fork_source.PIN_UNDER_REVIEW):
            problems.append(
                f"STATUS-RELEASE-NEXT pins {release.group(2)}; neither FORK_PIN "
                f"{fork_source.FORK_PIN} nor the build under review "
                f"{fork_source.PIN_UNDER_REVIEW}"
            )
        if not known_build(release.group(3)):
            problems.append(
                f"STATUS-RELEASE-NEXT reviews {release.group(3)}; neither "
                f"PIN_UNDER_REVIEW {fork_source.PIN_UNDER_REVIEW} nor {next_build}"
            )
        if release.group(2) == release.group(3):
            problems.append("STATUS-RELEASE-NEXT pins and reviews the same build")

    run = re.match(
        rf"{build} with (\d+\.\d+\.\d+); (waiting on .+|ready)$",
        lines["RUN-NEXT"][0],
    )
    if run is None:
        problems.append(
            f"STATUS-RUN-NEXT is not in D6's shape: {lines['RUN-NEXT'][0]!r}"
        )
    else:
        if not known_build(run.group(1)):
            problems.append(
                f"STATUS-RUN-NEXT tests {run.group(1)}; neither PIN_UNDER_REVIEW "
                f"{fork_source.PIN_UNDER_REVIEW} nor {next_build}"
            )
        if release is not None and run.group(1) != release.group(3):
            problems.append(
                f"STATUS-RUN-NEXT tests {run.group(1)}, but the next release "
                f"reviews {release.group(3)}"
            )
        consumers = {__version__} | ({release.group(1)} if release else set())
        if run.group(2) not in consumers:
            problems.append(
                f"STATUS-RUN-NEXT runs {run.group(2)}, neither ours nor the next release"
            )

    ids: list[str] = []
    for item in lines["OPEN"]:
        shaped = re.match(
            r"(\S+) (us|them) (fixing at \S.*|cannot, because \S.*)$", item
        )
        if shaped is None:
            problems.append(
                f"STATUS-OPEN is not '<id> <owner> <fixing at …|cannot, because …>': {item!r}"
            )
        else:
            ids.append(shaped.group(1))
    if len(ids) != len(set(ids)):
        problems.append(f"STATUS-OPEN repeats an id: {sorted(ids)}")
    return problems


def test_the_status_block_is_current() -> None:
    """Every D6 line agrees with the record and the code, and is in D6's shape."""
    problems = _status_block_problems(_status_text())
    assert not problems, "the status block is stale:\n  " + "\n  ".join(problems)


def test_the_status_block_check_can_fail() -> None:
    """Each check fails on a copy of the real text with its one fact changed.

    Floor: every mutation must land (the needle is in the text) and must produce
    a problem, so the check cannot pass by parsing nothing.
    """
    from platterpus.deps import fork_source

    text = _status_text()
    newest = _newest_round_on_disk()
    released_ours = [name for _, _, name, released in _laps("outbound") if released]
    reviewed = re.search(
        r"\+platterpus\.(\d+)$", fork_source.UNDER_REVIEW_TARGET.version
    )
    assert reviewed is not None, fork_source.UNDER_REVIEW_TARGET.version
    next_build = f"+platterpus.{int(reviewed.group(1)) + 1}"
    far_build = f"+platterpus.{int(reviewed.group(1)) + 5}"
    newest_version, newest_commit, _ = _newest_release()
    older_version = "0.0.1"  # in the shape, and never our newest release
    released_line = next(
        ln for ln in text.splitlines() if ln.startswith("STATUS-RELEASED: ")
    )
    dated = re.search(r"\d{4}-\d{2}-\d{2}", released_line)
    assert dated is not None, released_line
    released_date = dated.group()
    release_next_line = next(
        ln for ln in text.splitlines() if ln.startswith("STATUS-RELEASE-NEXT: ")
    )
    mutations = {
        "the round": (f"STATUS-ROUND: {newest},", f"STATUS-ROUND: {newest - 1},"),
        "our newest lap": (
            f"newest sent {released_ours[-1]}",
            "newest sent round-01-lap-01.md",
        ),
        "the pin": (f"pins {fork_source.PIN_UNDER_REVIEW}", "pins 0000000"),
        "the build to review": (f"reviews {next_build}", f"reviews {far_build}"),
        "a build both pinned and reviewed": (
            f"reviews {next_build}",
            f"reviews {fork_source.PIN_UNDER_REVIEW}",
        ),
        "the run's provider": (
            f"STATUS-RUN-NEXT: {next_build}",
            f"STATUS-RUN-NEXT: {far_build}",
        ),
        "an open item's shape": (
            "STATUS-OPEN: screenshot-unexposed us cannot, because",
            "STATUS-OPEN: screenshot-unexposed maybe later",
        ),
        "the newest release": (
            f"STATUS-RELEASED: {newest_version} at",
            f"STATUS-RELEASED: {older_version} at",
        ),
        "the newest release's commit": (
            f" at {newest_commit[:7]}, ",
            " at 0000000, ",
        ),
        "the release date": (
            f" at {newest_commit[:7]}, {released_date}",
            f" at {newest_commit[:7]}, 2099-01-01",
        ),
        "the block's order": (
            f"{released_line}\n{release_next_line}\n",
            f"{release_next_line}\n{released_line}\n",
        ),
    }
    assert len(mutations) >= 10
    for what, (needle, replacement) in mutations.items():
        assert needle in text, f"{what}: the needle {needle!r} is not in the block"
        assert _status_block_problems(text.replace(needle, replacement, 1)), (
            f"changing {what} in the status block was not caught"
        )
