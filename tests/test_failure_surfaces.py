# SPDX-License-Identifier: GPL-3.0-only
"""Sweeps over how failures reach the user.

**Why these are sweeps and not spot checks.** An audit (2026-08-04) found ~20 modal
failure reports saying *"see the log"* while naming no path, and two that named the
hardcoded literal ``~/.local/share/platterpus/log.txt`` — wrong under any relocated
``XDG_DATA_HOME``, and a path the user does not have is worse than no path, because
they conclude the log is missing. The instructive part is that **the two which
tried hardest were the two that got it wrong.** Fixing twenty strings by hand and
adding a comment saying "always name the path" would decay at exactly the rate the
UI grows, and it would decay *invisibly*, because a map is only ever wrong by
omission (CLAUDE.md: *"a comment where a check belongs is not a fix"*).

So: the sentence lives in ``ui/failure_text.py``, and these tests are what keep the
rest of the tree from writing its own. Each carries a **floor** — an examined-count
assertion — because a sweep that finds nothing because it looked nowhere is
decoration (*"can this check be satisfied by finding nothing?"*).
"""

from __future__ import annotations

import re
from pathlib import Path

from platterpus.paths import LOG_PATH
from platterpus.ui import failure_text

_SRC = Path(__file__).resolve().parents[1] / "src" / "platterpus"

#: The literal that is wrong whenever ``XDG_DATA_HOME`` is set. Written in pieces so
#: this file's own text cannot match the pattern it searches for — a detector that
#: flags itself is a detector nobody keeps.
_HARDCODED_LOG = "~/.local/" + "share/platterpus/log.txt"

#: Files where the literal is legitimate: prose *about* the default location rather
#: than an instruction to open a specific file. Deliberately tiny and justified —
#: an allowlist is where a sweep goes to die, so each entry states why.
_LITERAL_ALLOWED: dict[str, str] = {
    # A module docstring explaining what the greppable prefix is for; the runtime
    # value is built from `paths.LOG_PATH` two screens below it.
    "diagnostics.py": "docstring example of the grep command, not a user-facing string",
    # A comment naming where the app's log lives, not a message shown to anyone.
    "app.py": "code comment",
    "ui/main_window_rip.py": "code comment contrasting the album log with the app log",
}


def _python_files() -> list[Path]:
    return sorted(p for p in _SRC.rglob("*.py") if "__pycache__" not in p.parts)


def _rel(path: Path) -> str:
    return path.relative_to(_SRC).as_posix()


def _without_comments(text: str) -> str:
    """``text`` with ``#`` comment tails blanked, line count preserved.

    **A comment explaining a fixed message is not the message.** The first version of
    this sweep flagged `rip_audit.py` because the *comment* recording what the old
    wording had been quoted it — the check firing on the note that documented its own
    fix. CLAUDE.md's converse question, arriving immediately: *can it be satisfied by
    the wrong thing?*

    Naive on purpose: a ``#`` inside a string literal truncates that line early. That
    can only cause a false *negative*, never a false positive, and the
    ``examined_matches`` floor is what stops the whole sweep quietly going blind.
    Line numbers are preserved so offender positions stay accurate.
    """
    out: list[str] = []
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#"):
            out.append("")
            continue
        head, sep, _tail = line.partition("  #")
        out.append(head if sep else line)
    return "\n".join(out)


def test_no_module_hardcodes_the_log_path_literal() -> None:
    """The path must come from ``paths.LOG_PATH``, never from a typed-out literal.

    Two dialogs did type it out, and both were wrong under a custom
    ``XDG_DATA_HOME``. This is the check that would have caught them.
    """
    files = _python_files()
    # FLOOR: if the tree walk breaks, this test must fail rather than pass vacuously.
    assert len(files) >= 100, (
        f"only {len(files)} module(s) examined — the sweep is not reaching the "
        "source tree, so a pass here means nothing"
    )

    offenders: list[str] = []
    for path in files:
        rel = _rel(path)
        if rel in _LITERAL_ALLOWED:
            continue
        if _HARDCODED_LOG in path.read_text(encoding="utf-8"):
            offenders.append(rel)

    assert not offenders, (
        f"{len(offenders)} module(s) hardcode the log path instead of using "
        f"platterpus.paths.LOG_PATH (wrong under a custom XDG_DATA_HOME): "
        + ", ".join(offenders)
        + ". Use platterpus.ui.failure_text.LOG_POINTER in a user-facing message."
    )


def test_the_allowlist_entries_still_contain_what_they_excuse() -> None:
    """An allowlist that outlives its reason is a hole with documentation.

    *"Can it be satisfied by the wrong thing?"* — an entry for a file that no longer
    contains the literal silently permits a future one. Requires each entry to still
    be *needed*.
    """
    stale = [
        rel
        for rel in _LITERAL_ALLOWED
        if _HARDCODED_LOG not in (_SRC / rel).read_text(encoding="utf-8")
    ]
    assert not stale, (
        "these _LITERAL_ALLOWED entries no longer contain the literal they excuse — "
        "remove them so they cannot silently permit a new one: " + ", ".join(stale)
    )


#: "See the log" in its many phrasings, as a user-facing *string* (inside quotes).
#: Case-insensitive; deliberately narrow so it does not fire on comments or prose
#: about logging in general.
_VAGUE_LOG_REFERENCE = re.compile(
    r"""["'][^"'\n]{0,200}?\b(?:see|check|send|attach|consult)\b"""
    r"""[^"'\n]{0,40}?\bthe\s+log\b""",
    re.IGNORECASE,
)


def test_a_message_that_says_see_the_log_also_names_it() -> None:
    """A failure message that points at "the log" must say *which file*.

    Asking a user to send a file they have never been told the location of is the
    accurate-and-useless shape this project keeps paying for. The fix at each site is
    to append ``failure_text.LOG_POINTER`` (or name ``LOG_PATH`` inline).
    """
    files = [p for p in _python_files() if p.name != "failure_text.py"]
    assert len(files) >= 100, f"only {len(files)} module(s) examined — sweep broken"

    offenders: list[str] = []
    examined_matches = 0
    for path in files:
        text = _without_comments(path.read_text(encoding="utf-8"))
        for match in _VAGUE_LOG_REFERENCE.finditer(text):
            examined_matches += 1
            line_no = text.count("\n", 0, match.start()) + 1
            # The pointer may be appended on a nearby line rather than inside the
            # same string literal, so look at a small window around the match: the
            # question is whether *this message* names the path, not whether this
            # one string does.
            lines = text.splitlines()
            window = "\n".join(lines[max(0, line_no - 6) : line_no + 6])
            if "LOG_POINTER" in window or "LOG_PATH" in window:
                continue
            offenders.append(f"{_rel(path)}:{line_no}")

    # FLOOR: the pattern must still be finding the phrasing at all. If a refactor
    # rewords every site, this test would otherwise pass by matching nothing and
    # stop protecting anything.
    assert examined_matches >= 3, (
        f"the 'see the log' pattern matched only {examined_matches} time(s) — it has "
        "stopped recognising how these messages are written, so a pass proves nothing"
    )
    assert not offenders, (
        f"{len(offenders)} failure message(s) point at 'the log' without naming it: "
        + ", ".join(offenders)
        + ". Append platterpus.ui.failure_text.LOG_POINTER."
    )


def test_the_shared_pointers_name_the_resolved_path() -> None:
    """The helper itself must resolve through ``paths``, not restate a literal."""
    for name, value in (
        ("LOG_POINTER", failure_text.LOG_POINTER),
        ("BUG_REPORT_POINTER", failure_text.BUG_REPORT_POINTER),
        ("RIP_REPORT_POINTER", failure_text.RIP_REPORT_POINTER),
    ):
        assert str(LOG_PATH) in value, f"{name} does not name the real log path"
        assert value.strip(), f"{name} is empty"


def test_with_log_pointer_keeps_the_original_message() -> None:
    combined = failure_text.with_log_pointer("The rip could not start.")
    assert combined.startswith("The rip could not start.")
    assert str(LOG_PATH) in combined
    # An empty message must still produce a usable sentence rather than a stray
    # blank line followed by a path.
    assert failure_text.with_log_pointer("") == failure_text.LOG_POINTER
