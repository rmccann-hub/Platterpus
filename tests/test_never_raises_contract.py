# SPDX-License-Identifier: GPL-3.0-only
"""Fitness test: "never raises" must be a property of the code, not of the docstring.

CLAUDE.md's parser rule — *"parsers of external output never raise — they return
a best-effort dataclass"* — is asserted in ~180 docstrings across ``src/``. This
file checks the one way it is actually broken in practice, and checks it
everywhere at once rather than at the place it was last noticed.

**The mechanism.** CPython 3.11+ refuses to convert a decimal string of more than
4300 digits: ``int("9" * 4301)`` raises ``ValueError``
(``sys.set_int_max_str_digits``, a CVE-2020-10735 mitigation). A ``\\d+`` regex
group is unbounded, so a named-group regex proves the *characters* are digits and
says nothing about the *length* — every bare ``int(match.group(…))`` in a parser
is a live ``ValueError`` that no amount of regex care removes.

**Why the sweep, and not another pinned case.** This was already found once, in
``parsers/cyanrip_log.py``: seven numeric fields, all demonstrated raising
(review finding, 2026-07-28). The fix and its pinned regression test
(``test_parsers_property.test_an_absurdly_long_number_never_raises``) were
scoped to that one parser — so **six identical holes in five other modules
survived it**, in the EAC-log, cd-info and whipper-log parsers, the
``whipper.conf`` offset scanner and the CTDB ``.cue`` reader. Every one of them
carried a docstring saying "never raises". Found by audit, 2026-07-31.

That is the failure ``docs/testing.md`` §5.o names: *enforce a rule across the
codebase, not at the place it was learned.* So there are two tests here and they
do different jobs:

* :func:`test_a_long_digit_run_never_raises` is the **behavioural** proof — it
  feeds the boundary payload through real entry points and fails with the field
  name when one regresses.
* :func:`test_no_parser_converts_an_integer_without_a_guard` is the **structural**
  proof — it fails when a *new* unguarded ``int()`` appears in a parser, including
  in a field this file never thought to enumerate. Behavioural tests cover the
  cases someone remembered; the sweep covers the next one.

Hypothesis cannot find this unaided — a 4301-digit run never appears by chance in
``st.text()`` — which is why the boundary is pinned explicitly rather than
fuzzed. See ``tests/test_parsers_property.py`` for that reasoning in full.
"""

from __future__ import annotations

import ast
import logging
from collections.abc import Callable
from pathlib import Path

import pytest

from platterpus.adapters.cache_probe import parse_cache_analysis
from platterpus.ctdb.toc import parse_cue_index01_sectors
from platterpus.offset_config import read_drive_offsets
from platterpus.parsers.cd_info import parse_cd_info
from platterpus.parsers.cyanrip_info import parse_cyanrip_info
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.parsers.drive_list import parse_drive_list
from platterpus.parsers.eac_log import parse_eac_copy_crcs
from platterpus.parsers.rip_log import parse_rip_log
from platterpus.rip_timing import parse_eta_to_seconds, parse_hms_to_seconds
from platterpus.safe_int import int_or_none

SRC_ROOT = Path(__file__).resolve().parents[1] / "src" / "platterpus"

# One past CPython's conversion ceiling — the exact boundary, not a round number,
# so the test fails for the real reason rather than for being absurdly large.
OVER_THE_LIMIT: str = "9" * 4301


# --- Part 1: the behavioural proof ------------------------------------------
#
# (label, callable, text) per numeric field. The label is what a failure prints,
# so it names the field rather than the module — "which number regressed" is the
# question a failure has to answer.
_CASES: list[tuple[str, Callable[[str], object], str]] = [
    # parsers/eac_log.py — the track number keying every Copy CRC.
    (
        "eac_log: EAC track number",
        parse_eac_copy_crcs,
        f"Track {OVER_THE_LIMIT}\n     Copy CRC B0D122E7\n",
    ),
    # parsers/cd_info.py — the audio-track count (mid-line, `search` not `match`).
    #
    # Honest note: this case is currently **belt, not braces**. `_NUM_TRACKS` uses a
    # bounded `\d{1,4}` quantifier (a separate ReDoS fix), so no over-limit digit run
    # can reach the conversion and reverting the guard alone will NOT fail this case
    # — the structural sweep below is what holds cd_info. It stays in the table
    # because the bound belongs to the regex, and a future author widening `\d{1,4}`
    # back to `\d+` would then be caught here rather than shipping the hole again.
    (
        "cd_info: audio track count",
        parse_cd_info,
        f"Disc duration: 00:59:59, {OVER_THE_LIMIT} audio tracks\n",
    ),
    # parsers/cyanrip_info.py — the same count from `cyanrip -I`.
    (
        "cyanrip_info: disc track count",
        parse_cyanrip_info,
        f"Disc tracks:  {OVER_THE_LIMIT}\n",
    ),
    # parsers/rip_log.py — the track header, which opens a per-track block.
    (
        "rip_log: track header number",
        parse_rip_log,
        f"Tracks:\n  {OVER_THE_LIMIT}:\n",
    ),
    # parsers/rip_log.py — the AccurateRip sub-section version key.
    (
        "rip_log: AccurateRip version",
        parse_rip_log,
        f"Tracks:\n  1:\n    AccurateRip v{OVER_THE_LIMIT}:\n",
    ),
    # ctdb/toc.py — each MSF field of a `.cue` INDEX 01 line. All three are
    # separate conversions, so all three are separate holes.
    (
        "ctdb/toc: cue INDEX 01 minutes",
        parse_cue_index01_sectors,
        f"    INDEX 01 {OVER_THE_LIMIT}:00:00\n",
    ),
    (
        "ctdb/toc: cue INDEX 01 seconds",
        parse_cue_index01_sectors,
        f"    INDEX 01 00:{OVER_THE_LIMIT}:00\n",
    ),
    (
        "ctdb/toc: cue INDEX 01 frames",
        parse_cue_index01_sectors,
        f"    INDEX 01 00:00:{OVER_THE_LIMIT}\n",
    ),
    # parsers/drive_list.py — the configured read offset.
    #
    # ⚠️ The header line below must match `_DRIVE_LINE` **exactly** (lowercase
    # `drive:`, colons after every key, a `release:` field). The offset line is
    # only read once a header has opened a block, so a near-miss header makes this
    # case pass by never reaching the conversion — which is what the first draft of
    # this test did, and why the structural sweep below found this site and the
    # behavioural case did not. Keep them in sync; see the parser's own regex.
    (
        "drive_list: configured read offset",
        parse_drive_list,
        "drive: /dev/sr0, vendor: PIONEER, model: BD-RW BDR-209D, release: 1.10\n"
        f"  Configured read offset: {OVER_THE_LIMIT}\n",
    ),
    # adapters/cache_probe.py — the measured cache size in sectors.
    (
        "cache_probe: cache size in sectors",
        parse_cache_analysis,
        f"Drive cache: {OVER_THE_LIMIT} sectors\n",
    ),
    # rip_timing.py — cyanrip's ETA, both the bare-integer and unit-suffix forms.
    ("rip_timing: bare ETA seconds", parse_eta_to_seconds, OVER_THE_LIMIT),
    ("rip_timing: ETA unit piece", parse_eta_to_seconds, f"{OVER_THE_LIMIT}m"),
    (
        "rip_timing: HH:MM:SS hours",
        parse_hms_to_seconds,
        f"{OVER_THE_LIMIT}:00:00",
    ),
    # parsers/cyanrip_log.py — the parser this was originally found in. Kept here
    # so the roster is the whole rule, not the part that was still outstanding;
    # its own seven fields stay pinned in test_parsers_property.py.
    (
        "cyanrip_log: read offset",
        parse_cyanrip_log,
        f"cyanrip 0.9.3\nOffset:         +{OVER_THE_LIMIT} samples\n",
    ),
]


@pytest.mark.parametrize(
    ("label", "parse", "text"),
    _CASES,
    ids=[case[0] for case in _CASES],
)
def test_a_long_digit_run_never_raises(
    label: str, parse: Callable[[str], object], text: str
) -> None:
    """Every numeric field degrades to a default instead of raising ValueError.

    A parser that throws here takes down whatever called it — the drive list at
    startup, the disc scan, or the post-rip finish handler that writes the report.
    """
    try:
        parse(text)
    except Exception as exc:  # noqa: BLE001 — the assertion IS "nothing escapes"
        pytest.fail(
            f"{label} raised {type(exc).__name__}: {exc}. A parser of external "
            "output must never raise (CLAUDE.md) — route the conversion through "
            "platterpus.safe_int.int_or_none."
        )


def test_the_whipper_conf_offset_scanner_never_raises(tmp_path: Path) -> None:
    """The `whipper.conf` read-offset scan, which reads a file rather than a string.

    Separate from the table above because its entry point takes a path. It backs a
    *trust* check — "what offset will actually reach the ripper?" — so a crash here
    would take out the Settings dialog and ``--doctor`` alike.
    """
    conf = tmp_path / "whipper.conf"
    conf.write_text(
        f"[drive:PIONEER%20BD-RW]\nread_offset = {OVER_THE_LIMIT}\n",
        encoding="utf-8",
    )
    assert read_drive_offsets(conf) == [], (
        "an unusable read_offset must be dropped, not reported as a real offset"
    )


def test_the_payload_is_actually_over_cpython_s_limit() -> None:
    """The floor for the table above: prove the payload still triggers the bug.

    Without this, a CPython release that raised the digit ceiling (or a typo that
    shortened the string) would leave every case above passing for the wrong
    reason — a detector satisfied by finding nothing. This asserts the *mechanism*
    is live, so the parametrized cases are meaningful.
    """
    with pytest.raises(ValueError, match="4300 digits"):
        int(OVER_THE_LIMIT)


def test_int_or_none_is_total(caplog: pytest.LogCaptureFixture) -> None:
    """The shared guard degrades on every failure shape, and says so in the log."""
    with caplog.at_level(logging.WARNING):
        assert int_or_none(OVER_THE_LIMIT, field="probe") is None
        assert int_or_none("not a number") is None
        assert int_or_none(None) is None
        assert int_or_none(object()) is None
    assert int_or_none("42") == 42
    assert int_or_none("-7") == -7
    # CLAUDE.md: a dependency's unusable output is captured and logged, never
    # swallowed — a bug report has to carry *which* field was wrong.
    assert "probe" in caplog.text, (
        "the field name must reach the log, or a failure is undiagnosable"
    )
    # The 4301-char value must not be pasted into log.txt whole.
    assert OVER_THE_LIMIT not in caplog.text, (
        "the unusable value is truncated in the log record, not dumped in full"
    )


# --- Part 2: the structural proof -------------------------------------------
#
# The modules that turn external text into values and are documented never-raises.
# **This roster is the scope of the rule.** A module absent from it is not guarded
# here, so add new parsers as they appear (same discipline as the import roster in
# test_surface_consistency.py).
_PARSER_MODULES: tuple[str, ...] = (
    "parsers/cd_info.py",
    "parsers/cyanrip_info.py",
    "parsers/cyanrip_log.py",
    "parsers/drive_list.py",
    "parsers/eac_log.py",
    "parsers/rip_log.py",
    "adapters/cache_probe.py",
    "ctdb/decode.py",
    "ctdb/toc.py",
    "drive_profiles.py",
    "offset_config.py",
    "parity.py",
    "rip_timing.py",
    "safe_int.py",
)

# Exceptions that make an `int()` call safe to leave bare inside a `try`.
_ABSORBING = frozenset({"ValueError", "TypeError", "Exception", "BaseException"})


def _catches_conversion_error(handler: ast.ExceptHandler) -> bool:
    """True when this handler would absorb a failed ``int()``."""
    if handler.type is None:  # bare `except:` — absorbs everything
        return True
    if isinstance(handler.type, ast.Name):
        return handler.type.id in _ABSORBING
    if isinstance(handler.type, ast.Tuple):
        return any(
            isinstance(elt, ast.Name) and elt.id in _ABSORBING
            for elt in handler.type.elts
        )
    return False


def _unguarded_int_calls(tree: ast.AST) -> list[int]:
    """Line numbers of every bare ``int(…)`` not lexically inside an absorbing try.

    Walks the tree carrying "am I inside a protecting `try` body?" downward. A
    call to :func:`platterpus.safe_int.int_or_none` is not an ``int()`` call at
    all, so routing a conversion through the shared guard satisfies this without
    needing to be special-cased.
    """
    found: list[int] = []

    def walk(node: ast.AST, protected: bool) -> None:
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "int"
            and not protected
        ):
            found.append(node.lineno)
        if isinstance(node, ast.Try):
            absorbs = any(_catches_conversion_error(h) for h in node.handlers)
            for child in node.body:
                walk(child, protected or absorbs)
            # `else`/`finally` run outside the protected region, and the handlers
            # themselves are not protected by their own try.
            for child in node.handlers + node.orelse + node.finalbody:
                walk(child, protected)
            return
        for child in ast.iter_child_nodes(node):
            walk(child, protected)

    walk(tree, False)
    return found


def test_no_parser_converts_an_integer_without_a_guard() -> None:
    """A bare ``int()`` in a parser is a ValueError with a docstring denying it.

    This is the part with teeth: it fails for a field nobody enumerated in the
    table above, which is exactly how the six surviving holes got there — the
    behavioural test only covered the parser someone was looking at.
    """
    offenders: list[str] = []
    examined = 0
    guarded_seen = 0
    for relative in _PARSER_MODULES:
        path = SRC_ROOT / relative
        assert path.is_file(), (
            f"{relative} is in the roster but not on disk — a renamed or deleted "
            "module silently narrows this sweep. Update _PARSER_MODULES."
        )
        source = path.read_text(encoding="utf-8")
        examined += 1
        tree = ast.parse(source, str(path))
        guarded_seen += source.count("int_or_none") + source.count("int(")
        for lineno in _unguarded_int_calls(tree):
            offenders.append(f"{relative}:{lineno}")

    # Floors: a walk that examined nothing, or found no conversions at all, would
    # pass by finding nothing — the failure mode this whole file exists to stop.
    assert examined >= 14, (
        f"only examined {examined} parser modules — the roster has shrunk and this "
        "check is passing vacuously."
    )
    assert guarded_seen >= 20, (
        f"only saw {guarded_seen} integer-conversion sites across {examined} "
        "modules. The parsers are full of them, so the detector is broken."
    )

    assert not offenders, (
        f"bare int() in a documented never-raises parser: {offenders}. "
        "CPython refuses a digit run longer than 4300 characters, and a `\\d+` "
        "group is unbounded — so this raises ValueError on corrupt external text "
        "and takes its caller down with it. Route it through "
        "platterpus.safe_int.int_or_none (or wrap it in a try that catches "
        "ValueError). Do NOT add the module to an exemption list."
    )
