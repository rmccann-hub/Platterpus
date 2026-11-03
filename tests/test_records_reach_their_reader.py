"""Records the ripper or the app made that reached no reader (TASKS R117).

Findings 6, 7 and 9 of the 2026-11-03 Full run, beside the `[plan]` half, which
`tests/test_rip_plan.py` holds against the argv builder:

* **`.28`'s disc-level blocks** `Pregap searches:` and `Names shortened:` were
  parsed into `RippingInfo` and read by nothing. The report now carries both under
  `rip`. The EAC-layout log does not: they are cyanrip extras with no EAC line,
  like the paranoia counts (`docs/eac-parity.md`).
* **A dependency diagnostic said "cyanrip exited 64"** while the ripper's own
  sentence, `Offset is unset! To continue with an offset of 0, run with -s 0!`,
  sat only in its detail. The message now leads with it.
* **Process-session diagnostics repeated in every later report**: the secure
  re-read's report opened with track 5's verdict from the rip before it. The
  block is now this rip's, with the session's earlier ones counted once.

The secure re-read's log is that run's own, copied from evidence `1bb98a2c`; the
probe output is the `deps.command_failed` detail that run's report recorded.
"""

from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import pytest
from evidence_paths import evidence

from platterpus import diagnostics
from platterpus.adapters import rip_backend
from platterpus.diagnostics_scope import scoped_to_rip
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.rip_report import build_report, build_timing

_LOG = "docs/handshake/artifactsround37/round37full1103asecurereread.log"

#: The `deps.command_failed` detail of that run's report, verbatim: the output of
#: `~/.local/bin/cyanrip -N -l 1`, exit 64, on a drive with no offset set.
_PROBE_OUTPUT = (
    "Checking /dev/cdrom for cdrom...\n"
    "\t\tCDROM sensed: PIONEER  BD-RW   BDR-209D 1.51 SCSI CD-ROM\n\n\n"
    "Opening drive...\n"
    "Offset is unset! To continue with an offset of 0, run with -s 0!\n"
    "Paranoia status counts:\n  none\n\n"
    "Ripping errors: 0\n"
    "Encoder errors: not applicable; no track was encoded\n"
    "Read stalls:    none (no read exceeded 10s)\n"
    "Rip completed:  no (aborted, 0 of 14 tracks)\n"
    "Ripping finished at 2026-11-02T23:24:05-05:00"
)


@pytest.fixture(autouse=True)
def _clean_collector() -> Iterator[None]:
    diagnostics.clear()
    yield
    diagnostics.clear()


# --- the disc-level blocks -----------------------------------------------------


def test_the_pregap_searches_block_reaches_the_report() -> None:
    parsed = parse_cyanrip_log(evidence(_LOG).read_text(encoding="utf-8"))
    assert len(parsed.ripping_info.pregap_searches) == 13  # tracks 2 to 14
    rows = build_report(parsed)["rip"]["pregap_searches"]
    assert [row["track"] for row in rows] == list(range(2, 15))
    nine = next(row for row in rows if row["track"] == 9)
    assert nine["search"]["state"] == "read"
    assert nine["search"]["asked"] == 267
    assert nine["search"]["elsewhere"] == 210
    assert nine["search"]["harder_pass_ran"] is True
    assert nine["search"]["undecided_from"] == 145567


def test_the_names_shortened_block_reaches_the_report() -> None:
    long_name = "A" * 251 + ".flac"
    parsed = parse_cyanrip_log(
        "cyanrip 0.9.4-rc3+platterpus.28 (platterpus-fork-g3f288fb)\n"
        "Names shortened:\n"
        f"    folder: {'B' * 255} (301 bytes as rendered)\n"
        f"    track 3, flac: {long_name} (412 bytes as rendered)\n"
        "\n"
    )
    assert len(parsed.ripping_info.names_shortened) == 2
    assert build_report(parsed)["rip"]["names_shortened"] == [
        {"what": "folder", "name": "B" * 255, "rendered_bytes": 301},
        {"what": "track 3, flac", "name": long_name, "rendered_bytes": 412},
    ]


def test_no_block_is_null_never_an_empty_claim() -> None:
    parsed = parse_cyanrip_log("cyanrip 0.9.4\n")
    rip = build_report(parsed)["rip"]
    assert rip["pregap_searches"] is None
    assert rip["names_shortened"] is None


# --- the ripper's own sentence ----------------------------------------------------


def test_a_failed_probe_leads_with_the_rippers_own_sentence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(argv: list[str], **kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(returncode=64, stdout=_PROBE_OUTPUT, stderr="")

    monkeypatch.setattr(rip_backend.INFO_PROBE, "run", fake_run)
    code, _ = rip_backend.run_capture(
        "cyanrip", "cyanrip", ["-N", "-l", "1"], timeout=5, stdin_devnull=True
    )
    assert code == 64
    (item,) = diagnostics.default_log().items()
    assert item.code == "deps.command_failed"
    assert item.message == (
        "cyanrip exited 64: Offset is unset! To continue with an offset of 0, "
        "run with -s 0!"
    )
    assert item.exit_code == 64 and "Opening drive..." in item.detail


def test_output_with_no_diagnostic_line_keeps_the_number_alone() -> None:
    assert rip_backend.ripper_sentence("Opening drive...\nRipping errors: 0\n") == ""


# --- diagnostics scoped to the rip ------------------------------------------------


def _item(at: str, code: str, severity: str = "info") -> dict[str, object]:
    return {"at": at, "code": code, "severity": severity}


def test_earlier_diagnostics_are_counted_once_not_repeated() -> None:
    block: dict[str, object] = {
        "scope": "process session (not only this rip)",
        "items": [
            _item("2026-11-03T02:59:36+00:00", "ripper.secure_rerip_verdict"),
            _item("2026-11-03T03:00:00+00:00", "deps.command_failed", "warning"),
            _item("2026-11-03T03:35:38+00:00", "ripper.secure_rerip_verdict"),
        ],
    }
    # 22:20:06 in New York is 03:20:06 UTC: the rip's own `timing.started_at`.
    scoped = scoped_to_rip(block, "2026-11-02T22:20:06-05:00")
    assert [i["at"] for i in scoped["items"]] == ["2026-11-03T03:35:38+00:00"]  # type: ignore[index, union-attr]  # a list of dicts here
    assert scoped["info_count"] == 1 and scoped["warning_count"] == 0
    assert scoped["codes"] == ["ripper.secure_rerip_verdict"]
    assert scoped["earlier_in_session"] == {
        "count": 2,
        "codes": ["ripper.secure_rerip_verdict", "deps.command_failed"],
        "worst_severity": "warning",
    }
    assert "this rip" in str(scoped["scope"]) and "2 earlier" in str(scoped["scope"])


def test_an_unreadable_start_leaves_the_session_block_as_it_was() -> None:
    block: dict[str, object] = {"items": [_item("2026-11-03T02:59:36+00:00", "x")]}
    assert scoped_to_rip(block, "") is block
    assert scoped_to_rip(block, "not a time") is block
    assert scoped_to_rip(block, "2026-11-02T22:20:06") is block  # no offset


def test_the_report_scopes_its_diagnostics_to_the_rip() -> None:
    diagnostics.info("ripper.secure_rerip_verdict", "a verdict from the rip before")
    (before,) = diagnostics.default_log().items()
    timing = build_timing(10.0, started_at="2999-01-01T00:00:00+00:00")
    block = build_report(parse_cyanrip_log("cyanrip 0.9.4\n"), timing=timing)[
        "diagnostics"
    ]
    assert block["items"] == []
    assert block["earlier_in_session"]["count"] == 1
    assert before.at < "2999"  # the item really is earlier than the start
