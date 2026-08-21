"""`--rig-session`'s help text must describe what `rig_session.sh` actually does.

**The defect this pins.** The flag's help said the harness runs *"the ripper's own
`-x` and `-j`"*. Step 5a of `rig_session.sh` says, in capitals, that `-x` is **NOT
RUN** — deliberately, because it measures the drive cache and then rips the whole
disc (ETA 1h 3m, measured 2026-08-19) and leaves the drive held. The harness was
right and the help text was nine months of stale.

That is not a typo class. It is the *"two surfaces answering one question"* shape
(`docs/testing.md` §5.al): `--help` is what an operator reads before a hardware
session, and the harness is what runs. An operator trusting the help would either
eject the disc unnecessarily, or — worse — read a later `-x` regression as expected
behaviour because the help said it was supposed to happen.

So this test compares the two artifacts instead of trusting either. It is
deliberately narrow: it does not try to verify the whole help string against the
whole harness, only that a flag the harness marks NOT RUN is not advertised as run.
A checker that tried to diff prose against shell would be the kind nobody can
reason about.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
APP: Final[Path] = REPO_ROOT / "src" / "platterpus" / "app.py"
HARNESS: Final[Path] = REPO_ROOT / "src" / "platterpus" / "rig_session.sh"


def _rig_session_help() -> str:
    """The `--rig-session` help string, joined from its implicit concatenation."""
    text = APP.read_text(encoding="utf-8")
    start = text.index('"--rig-session"')
    # The argparse call ends at the closing paren of add_argument.
    block = text[start : text.index("parser.add_argument", start + 1)]
    marker = "help="
    assert marker in block, "the --rig-session argument has no help= to check"
    help_block = block[block.index(marker) :]
    # Join the adjacent string literals the way Python does.
    return " ".join(re.findall(r'"([^"]*)"', help_block))


def _flags_the_harness_refuses() -> set[str]:
    """Ripper flags `rig_session.sh` marks as deliberately not run.

    Keyed on the harness's own emphatic phrasing rather than on a list kept here,
    so adding a second refused flag needs no edit to this test — the point being
    that the harness is the authority and this file only compares.
    """
    refused: set[str] = set()
    for line in HARNESS.read_text(encoding="utf-8").splitlines():
        if "NOT RUN" not in line.upper():
            continue
        refused.update(re.findall(r"(?<![\w-])(-[a-zA-Z])(?![\w-])", line))
    return refused


def test_the_harness_declares_at_least_one_refused_flag() -> None:
    """Floor. With no refused flag the comparison below cannot fail.

    If `-x` is ever un-refused because the fork fixed it, this test is the one that
    should fail first — and its message should say what to do, rather than leaving
    somebody deleting an assertion they do not understand.
    """
    refused = _flags_the_harness_refuses()
    assert refused, (
        "rig_session.sh no longer marks any ripper flag as NOT RUN. If the fork "
        "shipped an `-x` that exits after measuring and step 5a now runs it, then "
        "this file's premise is gone: delete it and update the --rig-session help "
        "to say the probe runs again. Do not simply drop this assertion."
    )
    assert "-x" in refused, (
        f"expected -x among the refused flags, found {sorted(refused)} — the cache "
        "probe is the one this test was written for"
    )


def test_the_help_does_not_advertise_a_flag_the_harness_refuses() -> None:
    """The rule: help and harness must agree about what runs."""
    help_text = _rig_session_help()
    offenders: list[str] = []
    for flag in sorted(_flags_the_harness_refuses()):
        # "the ripper's own -x and -j" advertises it; "Does NOT run their -x" does
        # not. So look for the flag in a sentence that is not a negation.
        for sentence in re.split(r"(?<=[.:])\s+", help_text):
            if flag not in sentence:
                continue
            if re.search(r"\bnot run\b|\bdoes not\b|\bskip", sentence, re.I):
                continue
            offenders.append(f"{flag}: {sentence.strip()[:120]}")
    assert not offenders, (
        "the --rig-session help advertises a ripper flag that rig_session.sh "
        "deliberately does NOT run. An operator reads --help before a hardware "
        "session; the harness is what actually runs. Two descriptions of one "
        "behaviour, and this is the one that is wrong:\n  " + "\n  ".join(offenders)
    )


def test_the_help_says_why_the_probe_is_skipped() -> None:
    """A bare "does not run -x" invites somebody to switch it back on.

    The reason is the load-bearing part: it rips the whole disc and holds the
    drive. Naming it is what stops the next person treating the omission as an
    oversight — the same reason every allowlist entry here carries a written
    reason.
    """
    help_text = _rig_session_help().lower()
    assert "-x" in help_text, "the help no longer mentions -x at all"
    assert "rips the whole" in help_text or "holds the drive" in help_text, (
        "the help says the probe is skipped but not why, so the omission reads as "
        f"an oversight: {help_text!r}"
    )
