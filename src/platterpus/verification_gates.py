# SPDX-License-Identifier: GPL-3.0-only
"""``verification.gates`` read from what HAPPENED, and the record of what did not.

**Why this module exists.** :func:`platterpus.rip_report.build_gates` builds each
gate from the rip's *settings*: FLAC verify switched on, so ``"ran"``. That is a
statement about the request, and a reader takes it as a statement about the work.
The two disagree whenever a requested check could not run, and the measured case
is the worst one for an archival record: ``flac`` was missing, the checker aborted
with ``error: "... not found — cannot verify FLAC integrity"``, and the report
still said ``gates.flac_integrity: "ran"`` (TASKS.md, P2 row #4; `CLAUDE.md`'s *a
completeness field derived from config describes what was requested, and will be
read as what happened*).

So the gate is corrected here, where the settings-derived claim meets the result,
and only ever in one direction: a gate that claims ``"ran"`` and has a result block
beside it is replaced by what that block says. Three states, never two:

* ``"ran — passed"`` — the check ran and every file passed it;
* ``"ran — failed"`` — the check ran and something failed it;
* ``"not run — <the reason>"`` — the check was asked for and could not run, with
  the checker's own sentence (``flac not found``) as the reason.

A gate with **no** result block keeps the bare ``"ran"``. That is the one state
this module cannot settle, because there is nothing to read, and the report's
backstop already files it as ``verification_result_missing``.

**CTDB keeps ``"ran"`` for a lookup that compared something.** Its result is a
verdict with a weight (a match can be outvoted, schema v38), not a pass or a fail,
so it is read from ``verification.ctdb.verdict``. What CTDB *does* share with the
FLAC case is the could-not-run shape: no decoder to compute the CRC, or a lookup
that failed. Those become ``"not run — ..."`` like the FLAC one.

**The fourth state: started, then dropped because the app quit.** The unattended
quit gives up waiting for post-rip work after a budget (``app._arm_unattended_quit``)
and the process ends with checks still running. Before this the report left behind
read complete: ``health_status: "No errors occurred"``, ``completeness.complete:
true``, ``cover_art: null`` (TASKS.md, P2 row #5). :data:`CUT_SHORT_GATE` is the
gate for a check that was running when that happened, and
:func:`verification_completeness` is the block that says which steps did not
finish. *The third state is the one nobody enumerates*: requested, begun, dropped.

Pure, Qt-free, never raises. It imports nothing from :mod:`platterpus.rip_report`
so the builder can import it without a cycle.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from typing import Final

from platterpus.report_types import VerificationCompletenessBlock

#: The request-derived claim. Also the state a gate keeps when no result exists to
#: correct it from (see the module docstring).
GATE_RAN: Final[str] = "ran"
#: The check ran, and its result says every file passed.
GATE_RAN_PASSED: Final[str] = "ran — passed"
#: The check ran, and its result says at least one file failed.
GATE_RAN_FAILED: Final[str] = "ran — failed"
#: Every "asked for, did not run" state starts with this. The two older states of
#: that kind (`rip_report.RIP_DID_NOT_FINISH_GATE`, `rip_report.NOT_WHOLE_DISC_GATE`)
#: already did, so one prefix answers "did this run?" for all of them.
NOT_RUN_PREFIX: Final[str] = "not run — "
#: A check that was running when the unattended quit gave up waiting and ended the
#: process. Begun, never finished: neither "ran" nor "not run".
CUT_SHORT_GATE: Final[str] = "cut short — the app quit before this check finished"

#: Every state that says the check's work was carried out. A caller asking "did
#: anything run?" (the acceptance runner's floor) asks this, not `== "ran"`, which
#: the passed/failed split would otherwise silently turn false.
_RAN_STATES: Final[frozenset[str]] = frozenset(
    {GATE_RAN, GATE_RAN_PASSED, GATE_RAN_FAILED}
)

#: Gate states that are an accurate account of an EMPTY result block, because the
#: check was never asked for. Everything else with an empty block counts against
#: completeness — including a state this module does not recognise, which is the
#: safe direction: an unknown state is never read as "nothing was owed".
_NOT_REQUESTED_STATES: Final[frozenset[str]] = frozenset(
    {"disabled", "flac-only", "backend self-verifies"}
)

#: The `ctdb.verdict` wire values that mean the check could not run at all:
#: ``ctdb.verify.Verdict.DECODER_UNAVAILABLE`` and ``.LOOKUP_ERROR``. Spelled here
#: rather than imported because the enum's module carries the CTDB HTTP adapter and
#: the report builder is kept adapter-free (the reason `ctdb.coverage` spells
#: `NOT_WHOLE_DISC_VERDICT`); `tests/test_verification_gates.py` pins the two copies
#: equal, so a renamed verdict fails a test instead of passing silently.
CTDB_COULD_NOT_RUN_VERDICTS: Final[frozenset[str]] = frozenset(
    {"no_decoder", "lookup_error"}
)

#: A reason is the dependency's own sentence, which is external text. Bounded so a
#: runaway message cannot turn a one-line gate into a page, and the elision is
#: counted and marked, never silent.
_MAX_REASON_CHARS: Final[int] = 200

#: The `issues` code for a record whose post-rip verification was cut short.
ISSUE_VERIFICATION_CUT_SHORT: Final[str] = "verification_cut_short"

#: The gate keys that have a result block, and the order they are listed in.
GATE_KEYS: Final[tuple[str, ...]] = ("ctdb", "flac_integrity", "derived")


def gate_claims_ran(state: object) -> bool:
    """True when ``state`` says the check's work was carried out."""
    return isinstance(state, str) and state in _RAN_STATES


def bounded_reason(text: object) -> str:
    """``text`` as one bounded line, with any cut counted and marked."""
    line = " ".join(str(text or "").split()) or "no reason recorded"
    if len(line) <= _MAX_REASON_CHARS:
        return line
    dropped = len(line) - _MAX_REASON_CHARS
    return f"{line[:_MAX_REASON_CHARS]}… ({dropped} more characters)"


def not_run(reason: object) -> str:
    """The gate state for a requested check that could not run, and why."""
    return f"{NOT_RUN_PREFIX}{bounded_reason(reason)}"


def _from_pass_fail_block(block: Mapping[str, object]) -> str:
    """The tri-state for a block carrying ``ran`` / ``ok`` / ``error``."""
    if not block.get("ran"):
        return not_run(block.get("error"))
    return GATE_RAN_PASSED if block.get("ok") else GATE_RAN_FAILED


def gates_from_results(
    gates: Mapping[str, object] | None,
    *,
    flac_integrity: Mapping[str, object] | None,
    derived: Mapping[str, object] | None,
    ctdb: Mapping[str, object] | None,
) -> dict[str, object] | None:
    """Correct each request-derived ``"ran"`` from the result beside it.

    Only a gate reading exactly ``"ran"`` is touched: every other state is
    already a fact about what happened (superseded, did not finish, not the whole
    disc) or an accurate "never asked for". Only a present block is read: an
    absent one leaves ``"ran"`` for the backstop to file. ``None`` in, ``None``
    out — a caller with no gates has no claim to correct.
    """
    if gates is None:
        return None
    corrected = dict(gates)
    if corrected.get("flac_integrity") == GATE_RAN and flac_integrity is not None:
        corrected["flac_integrity"] = _from_pass_fail_block(flac_integrity)
    if corrected.get("derived") == GATE_RAN and derived is not None:
        corrected["derived"] = _from_pass_fail_block(derived)
    if corrected.get("ctdb") == GATE_RAN and ctdb is not None:
        verdict = ctdb.get("verdict")
        if isinstance(verdict, str) and verdict in CTDB_COULD_NOT_RUN_VERDICTS:
            corrected["ctdb"] = not_run(ctdb.get("message") or verdict)
    return corrected


def verification_completeness(
    gates: Mapping[str, object] | None,
    *,
    blocks: Mapping[str, Mapping[str, object] | None],
    cut_short_steps: Sequence[str] = (),
) -> VerificationCompletenessBlock:
    """Did every post-rip check this rip asked for leave a result? Say which not.

    Computed from the RESULT: the gates as corrected above, and the result blocks
    themselves. ``complete`` is tri-state, like the track ``complete`` beside it:

    * ``None`` when the writer has no gates, so it cannot tell;
    * ``False`` when a requested check did not run, left no result, or was still
      running when the app quit (``cut_short_steps``);
    * ``True`` only when none of those holds.
    """
    steps = [str(step) for step in cut_short_steps]
    if gates is None:
        return {
            "complete": None,
            "not_run": [],
            "without_result": [],
            "cut_short": bool(steps),
            "cut_short_steps": steps,
            "note": _NOTE,
        }
    not_run_keys: list[str] = []
    without_result: list[str] = []
    for key in GATE_KEYS:
        state = gates.get(key)
        if isinstance(state, str) and state.startswith(NOT_RUN_PREFIX):
            not_run_keys.append(key)
        elif blocks.get(key) is None and state not in _NOT_REQUESTED_STATES:
            # "ran" with no block, a superseded or cut-short check, or a state we
            # do not know: in each, something was owed and nothing is here.
            without_result.append(key)
    complete = not (not_run_keys or without_result or steps)
    return {
        "complete": complete,
        "not_run": not_run_keys,
        "without_result": without_result,
        "cut_short": bool(steps),
        "cut_short_steps": steps,
        "note": _NOTE,
    }


_NOTE: Final[str] = (
    "About the post-rip checks, not the tracks (the track count is `complete` one "
    "level up). `not_run` names checks that were asked for and could not run (the "
    "reason is in `verification.gates`); `without_result` names checks that were "
    "asked for or started and left no result; `cut_short_steps` names the post-rip "
    "steps still running when the app gave up waiting and quit. An absent result is "
    "not a passed one."
)


def cut_short_issue_message(
    steps: Sequence[str], gate_keys: Collection[str] = ()
) -> str:
    """The ``issues`` sentence for a record whose verification was cut short."""
    named = ", ".join(steps) or ", ".join(sorted(gate_keys)) or "unknown steps"
    return (
        f"post-rip verification was not completed: the app quit before these "
        f"steps finished ({named}). This record carries no result for them, and "
        f"an absent result is not a passed one."
    )
