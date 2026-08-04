# SPDX-License-Identifier: GPL-3.0-only
"""Tests for the one-place-for-every-error collector (`diagnostics`).

The module exists to answer *"did anything go wrong, and what?"* from a single
report block, so these tests are mostly about the properties that make it
trustworthy rather than about it merely storing things:

1. **Recording also logs.** One call, two sinks — so the text log and the JSON
   cannot describe the same event differently. Asserted, because "and remember to
   log too" at every call site is the drift this design removes.
2. **It never raises.** A recorder that throws while recording an error destroys
   the evidence for the failure it was called about.
3. **Truncation is stated.** A capped list that does not say it was capped reads as
   the complete set.
4. **Tri-state exit codes.** `None` (no child reaped) is a real answer and never
   renders as `0`.
"""

from __future__ import annotations

import ast
import dataclasses
import logging
import threading
from pathlib import Path

import pytest

from platterpus import diagnostics as d


@pytest.fixture(autouse=True)
def _clean_collector() -> None:
    """The collector is a process-wide global; a leaked item would cross tests."""
    d.clear()


# --- Recording also logs ----------------------------------------------------


def test_recording_also_writes_to_the_log(caplog: pytest.LogCaptureFixture) -> None:
    """One call site feeds BOTH the log file and the report.

    The alternative — every caller logging separately — is two independent
    descriptions of one event, which is exactly the drift this project keeps
    paying for. So the recorder owns it.
    """
    with caplog.at_level(logging.ERROR, logger="platterpus.diagnostics"):
        d.error(
            "ripper.nonzero_exit",
            "cyanrip failed",
            tool="cyanrip",
            argv=["cyanrip", "-N", "-d", "/dev/sr0"],
            exit_code=1,
            detail="fatal: Unable to open device!",
        )

    text = caplog.text
    assert "platterpus-diagnostic" in text, "the greppable token is missing"
    assert "ripper.nonzero_exit" in text
    assert "cyanrip -N -d /dev/sr0" in text, "the argv did not reach the log"
    assert "exit code: 1" in text
    assert "Unable to open device" in text, "the tool's own words were dropped"

    # And the same facts are in the report block — not a paraphrase.
    item = d.to_report_block()["items"][0]
    assert item["argv"] == ["cyanrip", "-N", "-d", "/dev/sr0"]
    assert item["exit_code"] == 1
    assert "Unable to open device" in item["detail"]


def test_the_grep_hint_is_the_token_actually_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The hint in the report must be a command that really works.

    A documented grep that finds nothing is worse than no hint: it converts "I
    can't find the errors" into "there were no errors".
    """
    with caplog.at_level(logging.WARNING, logger="platterpus.diagnostics"):
        d.warning("ctdb.query_failed", "CTDB unreachable")
    hint = d.to_report_block()["log_grep_hint"]
    # Pull the quoted pattern out of the hint and check it against real log text.
    assert "'" in hint
    pattern = hint.split("'")[1]
    assert pattern in caplog.text, (
        f"the report advertises `grep {pattern!r}` but that string is not in the log"
    )


# --- Never raises -----------------------------------------------------------


class _Exploding:
    """A value whose ``__str__`` raises — rare, real, and exactly the trap."""

    def __str__(self) -> str:
        raise RuntimeError("__str__ exploded")


def test_an_unstringifiable_detail_does_not_take_the_recorder_down() -> None:
    item = d.error("internal.unexpected_exception", "something", detail=_Exploding())
    assert item is not None
    assert "unstringifiable" in item.detail
    assert d.to_report_block()["error_count"] == 1


@pytest.mark.parametrize(
    "kwargs",
    [
        {"detail": _Exploding()},
        {"argv": _Exploding()},
        {"tool": _Exploding()},
        {"argv": 42},  # not iterable
        {"argv": "a bare string command line"},
        {"argv": [_Exploding(), "ok"]},
        {"where": _Exploding()},
        {"exit_code": None},
        {"track": None},
    ],
)
def test_no_argument_shape_can_make_recording_raise(kwargs: object) -> None:
    assert d.error("internal.unexpected_exception", "msg", **kwargs) is not None  # type: ignore[arg-type]


def test_a_bare_string_argv_is_kept_whole_not_exploded_into_characters() -> None:
    """`Popen.args` can be a string. Iterating it would give one arg per letter —
    a silently useless command line, which is worse than none at all."""
    item = d.error("ripper.nonzero_exit", "x", argv="cyanrip -d /dev/sr0")
    assert item is not None
    assert item.argv == ("cyanrip -d /dev/sr0",)


def test_an_unknown_severity_becomes_error_not_info(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Guessing DOWNWARD would hide a problem. Fail toward loud."""
    with caplog.at_level(logging.WARNING, logger="platterpus.diagnostics"):
        item = d.record("catastrophe", "internal.unexpected_exception", "msg")
    assert item is not None and item.severity == d.ERROR
    assert "unknown severity" in caplog.text


def test_an_unlisted_code_is_still_recorded_but_noted(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Losing a real diagnostic to a taxonomy quibble would be absurd.

    But the mismatch is logged, so `KNOWN_CODES` stays honest rather than quietly
    becoming fiction.
    """
    with caplog.at_level(logging.WARNING, logger="platterpus.diagnostics"):
        item = d.warning("brand.new.code", "still recorded")
    assert item is not None
    assert d.to_report_block()["error_count"] == 0
    assert item.code in d.to_report_block()["codes"]
    assert "KNOWN_CODES" in caplog.text


def test_exception_records_the_traceback_not_just_the_message() -> None:
    """The traceback is the point — it locates the bug; the message does not."""
    try:
        raise ValueError("boom")
    except ValueError as exc:
        item = d.exception("internal.unexpected_exception", "build hiccup", exc)
    assert item is not None
    assert "ValueError: boom" in item.detail
    assert "Traceback" in item.detail
    assert "line" in item.detail, "no source location survived"


# --- Tri-state --------------------------------------------------------------


def test_a_missing_exit_code_is_null_and_never_zero() -> None:
    """`None` means no child was reaped. Writing it as 0 would claim success."""
    d.error("ripper.unreapable_child", "wedged", tool="cyanrip", argv=["cyanrip"])
    item = d.to_report_block()["items"][0]
    assert item["exit_code"] is None
    assert item["exit_code"] != 0


def test_an_http_tool_is_not_described_as_an_unreaped_child(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """REGRESSION, found by reading this module's own first output.

    The log line said "exit code: none (child never reaped)" for a CTDB *HTTP*
    lookup, which spawns no child at all — a confident, wrong explanation, i.e. the
    accurate-sounding-but-misleading shape this whole subsystem exists to remove.
    The note is now gated on `argv` (a real spawned process) rather than on `tool`.
    """
    with caplog.at_level(logging.WARNING, logger="platterpus.diagnostics"):
        d.warning(
            "ctdb.query_failed", "CTDB unreachable", tool="ctdb", detail="HTTP 503"
        )
    assert "reaped" not in caplog.text, (
        "an HTTP lookup was described as a child process that was never reaped"
    )

    caplog.clear()
    with caplog.at_level(logging.ERROR, logger="platterpus.diagnostics"):
        d.error("ripper.unreapable_child", "wedged", tool="cyanrip", argv=["cyanrip"])
    assert "reaped" in caplog.text, (
        "a genuinely unreaped child must still say so — the converse, so the gate "
        "cannot pass by never mentioning it"
    )


# --- Bounds and truncation --------------------------------------------------


def test_the_cap_is_stated_and_counted() -> None:
    """A capped list that does not say it was capped reads as the complete set."""
    for i in range(d._MAX_ITEMS + 25):
        d.info("ripper.parse_degraded", f"item {i}")
    block = d.to_report_block()
    assert block["truncated"] is True
    assert block["dropped_count"] == 25
    assert len(block["items"]) == d._MAX_ITEMS


def test_the_cap_keeps_the_head_AND_the_tail() -> None:
    """The tail is nearest the failure; the head is often the root cause.

    A head-only cap drops exactly the diagnostics next to the thing that broke.
    """
    total = d._MAX_ITEMS + 50
    for i in range(total):
        d.info("ripper.parse_degraded", f"item {i}")
    messages = [i["message"] for i in d.to_report_block()["items"]]
    assert "item 0" in messages, "the head was dropped"
    assert f"item {total - 1}" in messages, "the tail was dropped"


def test_an_untruncated_report_does_not_claim_truncation() -> None:
    """The converse — so `truncated` cannot pass by always being True."""
    d.warning("deps.missing", "one thing")
    block = d.to_report_block()
    assert block["truncated"] is False
    assert block["dropped_count"] == 0


def test_a_huge_detail_is_capped_and_says_so() -> None:
    d.error("setup.step_failed", "big", detail="x" * (d._MAX_DETAIL_CHARS + 5000))
    detail = d.to_report_block()["items"][0]["detail"]
    assert detail is not None
    assert "omitted" in detail, "a silently trimmed detail reads as the whole output"
    assert "5000" in detail, "the elision does not count what it dropped"


# --- Summary fields ---------------------------------------------------------


def test_worst_severity_and_counts() -> None:
    assert d.default_log().worst_severity() is None, "nothing recorded is not an error"
    d.info("ripper.parse_degraded", "i")
    assert d.default_log().worst_severity() == d.INFO
    d.warning("ctdb.query_failed", "w")
    assert d.default_log().worst_severity() == d.WARNING
    d.error("ripper.nonzero_exit", "e")
    assert d.default_log().worst_severity() == d.ERROR

    block = d.to_report_block()
    assert (block["error_count"], block["warning_count"], block["info_count"]) == (
        1,
        1,
        1,
    )


def test_codes_are_distinct_and_in_first_seen_order() -> None:
    d.error("ripper.nonzero_exit", "a")
    d.warning("ctdb.query_failed", "b")
    d.error("ripper.nonzero_exit", "c")  # repeat
    assert d.to_report_block()["codes"] == ["ripper.nonzero_exit", "ctdb.query_failed"]


def test_a_clean_rip_produces_an_explicitly_empty_block() -> None:
    """The block is always present. Absent-vs-empty must not be a distinction a
    reader has to make: `error_count: 0` says "checked, none" out loud."""
    block = d.to_report_block()
    assert block["error_count"] == 0
    assert block["worst_severity"] is None
    assert block["items"] == []
    assert block["log_grep_hint"]


# --- Thread safety ----------------------------------------------------------


def test_concurrent_recording_loses_nothing() -> None:
    """Rips are not single-threaded: the rip, transcode and CTDB workers plus the
    GUI thread can all record. A plain list would drop items INVISIBLY."""
    per_thread, threads = 40, 8

    def worker(n: int) -> None:
        for i in range(per_thread):
            d.info("ripper.parse_degraded", f"t{n}-{i}")

    pool = [threading.Thread(target=worker, args=(n,)) for n in range(threads)]
    for t in pool:
        t.start()
    for t in pool:
        t.join()

    assert d.default_log().count() == per_thread * threads


# --- The contract with the report schema ------------------------------------


def test_the_dataclass_and_the_typeddict_cannot_drift() -> None:
    """`DiagnosticItemBlock` claims to mirror `Diagnostic` exactly. Check it.

    Two hand-maintained descriptions of one shape is precisely the drift this
    project keeps finding; the claim is only worth making if something enforces it.
    """
    from platterpus.report_types import DiagnosticItemBlock

    produced = {f.name for f in dataclasses.fields(d.Diagnostic)}
    declared = set(DiagnosticItemBlock.__annotations__)
    assert produced == declared, (
        f"Diagnostic and DiagnosticItemBlock disagree — "
        f"only in the dataclass: {sorted(produced - declared)}; "
        f"only in the TypedDict: {sorted(declared - produced)}"
    )


def test_every_json_key_is_declared_and_serialisable() -> None:
    import json

    from platterpus.report_types import DiagnosticItemBlock

    d.error("ripper.nonzero_exit", "x", tool="cyanrip", argv=["a"], exit_code=2)
    block = d.to_report_block()
    # Round-trips: a report that cannot be written is not a report.
    json.dumps(block)
    assert set(block["items"][0]) == set(DiagnosticItemBlock.__annotations__)


def test_an_isolated_collector_does_not_touch_the_global() -> None:
    """`DiagnosticLog` is instantiable, so a test (or a future per-rip scope) can
    collect without the process-wide one being involved."""
    private = d.DiagnosticLog()
    private.error("deps.missing", "mine only")
    assert private.count() == 1
    assert d.default_log().count() == 0


# --- The wiring is a sweep, not a promise (2026-08-04) ---------------------
#
# A collector nothing calls is an empty section that reads as "nothing went wrong".
# CLAUDE.md's standing lesson from the `cancel()` audit applies verbatim: *grep for a
# call site before believing it works, and check the call site is reachable, not
# merely present.* So this asserts every subsystem that CAN fail actually records —
# by importing the real module and looking for the call, with a floor so the sweep
# cannot pass by finding nothing.

_SRC = Path(__file__).resolve().parents[1] / "src" / "platterpus"

#: Module → the diagnostic code it must be able to record. Every entry is a
#: subsystem an audit found failing silently; the point of the list is that adding a
#: new failure path is a *decision*, and removing one from here is visible in a diff.
_WIRED: dict[str, str] = {
    "workers/rip_worker.py": "ripper.nonzero_exit",
    "workers/dependency_worker.py": "deps.command_failed",
    "deps/host_setup.py": "setup.step_failed",
    "adapters/metaflac.py": "metaflac.failed",
    "adapters/cache_probe.py": "deps.command_failed",
    "adapters/ctdb_client.py": "ctdb.query_failed",
    "adapters/musicbrainz_client.py": "musicbrainz.lookup_failed",
    "adapters/cover_art.py": "coverart.fetch_failed",
    "adapters/tool_run.py": "record_command_failure",
    "library_move.py": "library.move_failed",
    "drive_control.py": "drive.control_failed",
    "ui/main_window_helpers.py": "library.move_failed",
}


def _imports_diagnostics(source: str) -> bool:
    """Whether ``source`` imports the collector, in any legal form.

    **AST, not a substring.** The first version of this check looked for the exact
    line ``from platterpus import diagnostics`` and reported `ctdb_client.py` as
    unwired — it imports the collector on a shared line
    (``from platterpus import __version__, diagnostics``), which is the same import.
    A matcher narrower than the language it inspects produces confident wrong
    answers, and a *false* failure trains people to ignore the check as surely as a
    false pass lets a bug through.
    """
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "platterpus":
            if any(alias.name == "diagnostics" for alias in node.names):
                return True
        if isinstance(node, ast.ImportFrom) and node.module == "platterpus.diagnostics":
            return True
        if isinstance(node, ast.Import):
            if any(a.name == "platterpus.diagnostics" for a in node.names):
                return True
    return False


def test_every_failure_prone_subsystem_records_a_diagnostic() -> None:
    """Each module must both import the collector AND name its code.

    Two conditions, not one — the pair is the check. Importing it proves nothing
    (an unused import passes lint in no project, but a leftover one would); naming
    the code proves nothing on its own either, since a string can sit in a comment.
    Requiring both, in the same file, is what makes this a check rather than a label
    match (CLAUDE.md: *"the label answers 'did they name it', the content answers
    'did they write it', and only the pair is a check"*).
    """
    problems: list[str] = []
    for rel, code in _WIRED.items():
        path = _SRC / rel
        assert path.exists(), f"{rel} has moved — this sweep is measuring nothing"
        source = path.read_text(encoding="utf-8")
        if not _imports_diagnostics(source):
            problems.append(f"{rel} does not import the diagnostics collector")
            continue
        if code not in source:
            problems.append(f"{rel} never names {code!r}")
    assert not problems, (
        "the diagnostics collector is not wired where an audit found silent "
        "failures — " + "; ".join(problems)
    )
    # FLOOR: the list itself must not have been emptied.
    assert len(_WIRED) >= 10, f"only {len(_WIRED)} subsystems swept"


def test_every_wired_code_is_a_known_code() -> None:
    """A typo in a code silently mints a category no aggregation will ever find.

    `record()` logs a warning for an unlisted code rather than refusing it — losing a
    real diagnostic to a taxonomy quibble would be absurd — which is exactly why this
    needs a test: the runtime behaviour is deliberately forgiving, so the gate has to
    live here.
    """
    codes = {c for c in _WIRED.values() if "." in c and not c.startswith("record")}
    unknown = sorted(c for c in codes if c not in d.KNOWN_CODES)
    assert not unknown, f"not in KNOWN_CODES: {unknown}"
    assert len(codes) >= 8, f"only {len(codes)} distinct codes swept"


# --- The level a bug report actually keeps (2026-08-04) --------------------
#
# G0 from the subprocess-capture audit, and the finding that makes half the others
# moot if unfixed: `log.txt` is **INFO-only by default** (`logging_setup` sets the
# file handler to INFO unless the user has turned Debug logging on, and the toggle is
# described as "Off by default"). Every subprocess record — including cyanrip's whole
# transcript, written with `log.debug("cyanrip │ …")` — is therefore *absent* from
# the file a user attaches to a bug report.
#
# So the rule is: a failure record must land at a level the default file handler
# keeps. This test is the enforcement, because the rule was previously nowhere.


def test_a_failure_record_lands_at_a_level_the_default_log_file_keeps(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """ERROR and WARNING, never DEBUG — with the argv and the output attached.

    The floor that matters: assert the *level*, not merely that something was
    logged. A diagnostic emitted at DEBUG is captured, enumerated in the JSON, and
    invisible in the one file most bug reports contain.
    """
    d.clear()
    with caplog.at_level(logging.DEBUG):
        d.record_command_failure(
            "flac.verify_failed",
            "flac --test",
            ["flac", "--test", "/x/01.flac"],
            1,
            "01.flac: ERROR while decoding data\n",
            where="test",
        )
        d.warning("ctdb.query_failed", "CTDB was unreachable", tool="CTDB (HTTP)")

    records = [r for r in caplog.records if "platterpus-diagnostic" in r.getMessage()]
    assert len(records) == 2, f"expected 2 diagnostic log records, got {len(records)}"
    levels = {r.levelno for r in records}
    assert logging.DEBUG not in levels, (
        "a failure diagnostic was emitted at DEBUG, which log.txt does not keep by "
        "default — so it would be absent from exactly the file a bug report carries"
    )
    assert levels <= {logging.ERROR, logging.WARNING}, f"unexpected levels: {levels}"

    # And the four facts travel with it, in the TEXT log — not only in the JSON.
    error_text = next(r.getMessage() for r in records if r.levelno == logging.ERROR)
    assert "exit code: 1" in error_text
    assert "flac --test /x/01.flac" in error_text  # the exact argv
    assert "ERROR while decoding data" in error_text  # the tool's own words
    assert "flac.verify_failed" in error_text  # the greppable code
    d.clear()


def test_an_info_diagnostic_is_info_not_a_warning() -> None:
    """The converse. If everything were escalated to WARNING, the level would carry
    no information and a reader scanning for problems would be back to reading
    everything — which is the state this whole subsystem exists to end."""
    d.clear()
    item = d.info("ripper.parse_degraded", "a note, not a problem")
    assert item is not None
    assert item.severity == d.INFO
    d.clear()
