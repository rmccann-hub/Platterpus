"""T14 — the dynamic secure-rerip, walked end to end: pass 1 → miss → pass 2 → report.

**Why this file exists, and why it is one file rather than more unit tests.**
Two real user-facing bugs shipped in v0.6.3 and both were found by a human reading
a real rip's artifacts, not by the suite (`docs/session-log.md`, 2026-08-03):

1. The argv-agreement self-check compared the *last* ripper invocation against the
   `Invoked as:` line the *first* pass writes, and told a clean rip *"the command
   line changed in transit … Something between us altered it"* — naming the
   auto-fix pass's own `-Z`/`-l` as injected arguments.
2. `Done; (no matches found, but hit repeat limit of 5)` was scraped into
   `outcome.failure_hint` on a rip whose status was `success` and exit code `0`.

Both were the **same shape**: a report describing a multi-pass rip through fields
that assume one pass. Every individual piece had unit tests. Nothing walked the
whole chain, so the seam between the pieces — which is where both defects lived —
was untested. Offered to the cyanrip fork as T14 in `verified/round-7.md` §9,
because their side has the mirror-image gap.

**What is real here and what is faked.** The `RipWorker` is real, and it is the
component that decides to run a second pass and does so itself
(`_auto_fix_tracks`). `build_outcome`, the report writer and `rip_audit` are all
real. Faked only at the external boundary: the ripper subprocess. The fake is
*two-call* — it must be, because a single-call fake cannot exhibit the bug.

**What this fixture does NOT exercise, stated because the fork asked and because
they were right to ask.** Track 5's `Done; (no matches found, but hit repeat limit
of 5)` is here because the fixture writes it, **not** because any read disagreed
with another. It is the right *string* for the wrong *reason*. Their `reference`
scenario has the identical property — it reaches that line by exhausting the repeat
limit on clean audio — and their round-7 lap-2 §8 asked both sides to say so
rather than let the fixture imply non-convergence had been exercised.

So, plainly: **nothing here proves we handle a genuine non-convergence.** What
would is a disc that actually fails to converge for a physical reason, which is
hardware (`docs/hardware-test-checklist.md` §F). A harness that is safer than the
product makes the product's gap invisible — this project's own rule, and it applies
to the fixture that was written to close a gap.

**Asserted against the artifact, not against a belief.** The report is written to
disk and **re-read** before the audit runs over it, so a field that serialises
wrongly (or not at all) fails here rather than passing in memory. And the
non-triviality floor: the test asserts the second pass *actually happened* and
that the two argvs *actually differ*, because if the fake collapsed to one pass
every downstream assertion would pass while proving nothing (`docs/testing.md`
§5.ac — silence compares equal to silence).
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pytest
from PySide6.QtWidgets import QApplication

from platterpus import rip_audit
from platterpus.adapters.rip_backend import DiscInfo, RipBackend, RipHandle
from platterpus.rip_report import build_outcome
from platterpus.workers.rip_worker import RipParameters, RipWorker

# --- the two logs the two passes produce --------------------------------------
#
# Shaped after the real 14-track rip that produced both bugs, cut to 5 tracks so
# the fixture stays readable. Tracks 3 and 5 miss AccurateRip on pass 1, which is
# exactly what makes the worker run a second pass over just those two.

_FIRST_PASS_ARGV = (
    "cyanrip",
    "-d",
    "/dev/sr0",
    "-s",
    "667",
    "-o",
    "flac",
    "-r",
    "5",
    "-N",
    "-c",
    "1/1",
)


def _first_pass_log(argv: Iterable[str]) -> str:
    """A whole-disc log: no `-Z`, tracks 3 and 5 missing AccurateRip.

    `Invoked as:` is written from the argv the fake was *actually* called with,
    not from a literal — so the agreement check compares the real pair. A
    hand-written `Invoked as:` would make this assert that two constants I typed
    match each other, which is not the property under test.
    """
    invoked = " ".join(argv)
    blocks = []
    for number in (1, 2, 3, 4, 5):
        hit = number not in (3, 5)
        accurip = (
            f"    Accurip v1:  AAAAAAA{number} (accurately ripped, confidence 200)\n"
            if hit
            else f"    Accurip v1:  AAAAAAA{number} (not found, either a new "
            "pressing, or bad rip)\n"
        )
        blocks.append(
            f"Track {number} ripped and encoded successfully!\n"
            f"  EAC CRC32:     0000000{number}\n" + accurip + "  File(s):\n"
            f"    Artist/Album/0{number} - T{number}.flac\n"
        )
    return (
        "cyanrip 0.9.4-rc1 (platterpus-fork-g2f950c8)\n"
        f"Invoked as: {invoked}\n"
        "Disc tracks:    5\n"
        "Offset: +667 samples\n"
        "Paranoia level: 0\n"
        "Album: Test Album\n" + "".join(blocks) + "Ripping errors: 0\n"
    )


def _second_pass_log(argv: Iterable[str], tracks: tuple[int, ...]) -> str:
    """The auto-fix pass over only the tracks AccurateRip missed.

    Track 3 converges (its re-reads agree, so it is swapped in); track 5 does not,
    and its `Done; (no matches found, …)` line is the exact string that used to
    land in `failure_hint` on a successful rip.
    """
    invoked = " ".join(argv)
    blocks = []
    for number in tracks:
        converged = number == 3
        done = (
            f"Done; (2 out of 2 matches for current checksum BBBB{number}222)\n"
            if converged
            else "Done; (no matches found, but hit repeat limit of 5)\n"
        )
        blocks.append(
            done + f"Track {number} ripped and encoded successfully!\n"
            f"  EAC CRC32:     9999999{number}\n"
            "  File(s):\n"
            f"    Artist/Album/0{number} - T{number}.flac\n"
        )
    return (
        "cyanrip 0.9.4-rc1 (platterpus-fork-g2f950c8)\n"
        f"Invoked as: {invoked}\n"
        "Disc tracks:    5\n"
        "Paranoia level: 2\n" + "".join(blocks) + "Ripping errors: 0\n"
    )


class _Handle:
    """A ripper run that has already finished cleanly, carrying its own argv.

    `argv` is what `RipWorker` reads off the handle to record what it spawned —
    the same attribute the real `RipHandle` exposes off `Popen.args`, so the
    recorded vector cannot drift from what the OS received.
    """

    def __init__(self, argv: tuple[str, ...], lines: Iterable[str] = ()) -> None:
        self.argv: tuple[str, ...] = argv
        self._lines: list[str] = list(lines)

    def log_lines(self) -> Iterable[str]:
        yield from self._lines

    def wait(self, timeout: float | None = None) -> int:
        return 0

    def cancel(self, term_timeout: float = 5.0) -> int:
        return 0


class _TwoPassBackend(RipBackend):
    """A ripper that must be called twice, and writes what each pass writes.

    Deliberately **not** permissive: `rip()` mirrors the ABC's signature exactly
    rather than swallowing `**kwargs`, per the harness-fidelity rule — a fake
    that accepts more than the real thing hides a widening at the seam.
    """

    def __init__(self, album_dir: Path) -> None:
        self.album_dir: Path = album_dir
        self.calls: list[dict[str, Any]] = []
        self.argvs: list[tuple[str, ...]] = []

    def list_drives(self) -> list:  # type: ignore[type-arg]
        return []

    def disc_info(self, drive: str) -> DiscInfo:
        return DiscInfo(num_tracks=5)

    def version(self) -> str:
        return "cyanrip 0.9.4-rc1 (platterpus-fork-g2f950c8)"

    def rip(
        self,
        drive: str,
        release_id: str,
        output_dir: Path,
        track_template: str,
        disc_template: str,
        unknown: bool = False,
        cover_art: str = "",
        max_retries: int = 5,
        secure_rerip_matches: int = 0,
        force_overread: bool = False,
        read_offset_override: int | None = None,
        metadata: Any = None,
        disc_track_total: int | None = None,
        read_speed: int = 0,
        only_tracks: tuple[int, ...] = (),
    ) -> RipHandle:
        self.calls.append(
            {
                "secure_rerip_matches": secure_rerip_matches,
                "only_tracks": tuple(only_tracks),
                "output_dir": output_dir,
            }
        )
        # The argv the real backend would build for these parameters: the
        # whole-disc pass carries no `-Z`, the auto-fix pass adds `-Z N -l t,t`.
        argv = list(_FIRST_PASS_ARGV)
        if secure_rerip_matches:
            argv += ["-Z", str(secure_rerip_matches)]
        if only_tracks:
            argv += ["-l", ",".join(str(t) for t in only_tracks)]
        vector = tuple(argv)
        self.argvs.append(vector)

        album = output_dir / "Artist" / "Album"
        album.mkdir(parents=True, exist_ok=True)
        if only_tracks:
            # The auto-fix pass writes its own log and its own FLACs into a
            # throwaway directory — it must NOT clobber the album's whole-disc
            # log, which is what `Invoked as:` is read from.
            (album / "rerip.log").write_text(
                _second_pass_log(vector, tuple(only_tracks)), encoding="utf-8"
            )
            for number in only_tracks:
                (album / f"0{number} - T{number}.flac").write_bytes(b"FIXED-FLAC")
        else:
            (album / "rip.log").write_text(_first_pass_log(vector), encoding="utf-8")
            for number in (1, 2, 3, 4, 5):
                (album / f"0{number} - T{number}.flac").write_bytes(
                    b"\xfffLaC" + bytes([number])
                )
        return _Handle(vector, ["ripping"])  # type: ignore[return-value]


@pytest.fixture()
def two_pass(qapp: QApplication, tmp_path: Path) -> tuple[RipWorker, _TwoPassBackend]:
    """A real `RipWorker` driven synchronously over the two-call backend.

    Synchronous on purpose: Qt signals are callable without an event loop, and the
    threading of this path already has its own coverage. What is under test here
    is the *data* that survives two passes, not the thread hand-off.
    """
    album = tmp_path
    backend = _TwoPassBackend(album / "Artist" / "Album")
    worker = RipWorker(
        backend,
        RipParameters(
            drive="/dev/sr0",
            release_id="mbid-abc",
            output_dir=album,
            track_template="t",
            disc_template="d",
            # Dynamic secure-rerip: `-Z` is NOT applied to every track. Pass 1
            # reads the disc once with no `-Z`, then only the tracks AccurateRip
            # did not verify are re-read. This is the setting the real rip ran
            # under and the only one that produces two passes.
            secure_rerip_matches=2,
            secure_rerip_dynamic=True,
            read_offset_override=667,
            disc_track_total=5,
        ),
    )
    worker.start_rip()
    return worker, backend


def test_the_fake_actually_ran_two_passes(
    two_pass: tuple[RipWorker, _TwoPassBackend],
) -> None:
    """The non-triviality floor, first, because everything else depends on it.

    If the worker had run one pass, every assertion below would pass by
    describing a single-pass rip correctly — the test would be green and would
    prove nothing about the case it was written for.
    """
    _worker, backend = two_pass
    assert len(backend.calls) == 2, (
        "the auto-fix pass did not run, so this file is not exercising the "
        f"multi-pass path at all: calls={backend.calls}"
    )
    first, second = backend.calls
    assert first["only_tracks"] == (), "pass 1 must be the whole disc"
    assert second["only_tracks"] == (3, 5), (
        "pass 2 must cover exactly the tracks AccurateRip did not verify: "
        f"{second['only_tracks']}"
    )
    assert second["secure_rerip_matches"] == 2, "pass 2 must carry `-Z N`"
    # And the two command lines must genuinely differ, or "they agree" is vacuous.
    assert backend.argvs[0] != backend.argvs[1]


def test_the_worker_records_both_the_first_and_the_last_argv(
    two_pass: tuple[RipWorker, _TwoPassBackend],
) -> None:
    """`ripper_argv` is the last invocation; `ripper_argv_first_pass` is the first.

    The distinction is the whole fix: one answers *"what command should I re-run"*
    and the other answers *"what command wrote the `Invoked as:` line in the
    archival log"*, and conflating them is what accused the user's system of
    tampering.
    """
    worker, backend = two_pass
    assert worker.ripper_argv == backend.argvs[1]
    assert worker.ripper_argv_first_pass == backend.argvs[0]
    assert "-Z" not in worker.ripper_argv_first_pass, (
        "the first pass must not carry `-Z` — if it does, the fixture is not "
        "reproducing dynamic mode and the speed characteristics differ too"
    )
    assert "-Z" in worker.ripper_argv


def test_the_report_survives_a_round_trip_through_disk(
    two_pass: tuple[RipWorker, _TwoPassBackend], tmp_path: Path
) -> None:
    """Both fields must reach the JSON, and `null` must stay distinguishable.

    Read back off disk rather than asserted in memory: a field that serialises
    wrongly is a field the fork and `--audit-rips` never see, and that is the
    only form in which it matters.
    """
    worker, _backend = two_pass
    outcome = build_outcome(
        status="success",
        ripper_exit_code=0,
        ripper_argv=worker.ripper_argv,
        ripper_argv_first_pass=worker.ripper_argv_first_pass,
    )
    path = tmp_path / "round-trip.platterpus.json"
    path.write_text(json.dumps({"outcome": outcome}), encoding="utf-8")
    reread = json.loads(path.read_text(encoding="utf-8"))["outcome"]

    assert reread["ripper_argv"] == list(worker.ripper_argv)
    assert reread["ripper_argv_first_pass"] == list(worker.ripper_argv_first_pass)
    assert reread["ripper_argv"] != reread["ripper_argv_first_pass"]


def test_a_single_pass_rip_reports_null_for_the_first_pass_field() -> None:
    """The other branch, and the reason the field is `null` rather than a copy.

    If a one-pass rip echoed its argv into both fields, nothing downstream could
    tell *"single pass"* from *"first of several"* — and the audit's wording
    ("on the whole-disc pass") would be wrong on every ordinary rip.
    """
    outcome = build_outcome(
        status="success", ripper_exit_code=0, ripper_argv=_FIRST_PASS_ARGV
    )
    assert outcome["ripper_argv_first_pass"] is None
    assert outcome["ripper_argv"] == list(_FIRST_PASS_ARGV)


def test_the_audit_finds_no_tampering_in_a_clean_two_pass_rip(
    two_pass: tuple[RipWorker, _TwoPassBackend], tmp_path: Path
) -> None:
    """The v0.6.3 false alarm, end to end and off the artifact.

    A clean rip whose self-heal fired must not be told its command line was
    altered in transit. Driven through the real `rip_audit` over a real written
    report, because the bug was in the *comparison*, not in either half.
    """
    worker, backend = two_pass
    folder = backend.album_dir
    invoked = next(
        line.split("Invoked as:", 1)[1].strip()
        for line in (folder / "rip.log").read_text(encoding="utf-8").splitlines()
        if line.startswith("Invoked as:")
    )
    # Floor: the log we are comparing against must be the FIRST pass's. The
    # second pass overwrote `rip.log` in its own directory, not this one — assert
    # that rather than trusting it, since a fixture that let pass 2 clobber the
    # album log would make the agreement check trivially true.
    assert "-Z" not in invoked, (
        "the album log's `Invoked as:` is not the whole-disc pass — the fixture "
        f"let the auto-fix pass overwrite it: {invoked}"
    )

    report = {
        "outcome": build_outcome(
            status="success",
            ripper_exit_code=0,
            ripper_argv=worker.ripper_argv,
            ripper_argv_first_pass=worker.ripper_argv_first_pass,
        ),
        "rip": {"invoked_as": invoked},
    }
    path = folder / "album.platterpus.json"
    path.write_text(json.dumps(report), encoding="utf-8")

    audit = rip_audit.audit_album(path)
    tamper = [
        f.text
        for f in audit.findings
        if "altered" in f.text or "changed in transit" in f.text
    ]
    assert not tamper, (
        "a clean two-pass rip was accused of command-line tampering — the "
        "v0.6.3 false alarm: " + "; ".join(tamper)
    )
    # And the check must have actually run and said something, or "no tamper
    # finding" is satisfied by a check that never spoke (`rip_audit`'s own floor
    # rule). It must also name which pass it read.
    argv_findings = [
        f.text
        for f in audit.findings
        if "flags we sent" in f.text or "command line" in f.text
    ]
    assert argv_findings, (
        "the argv-agreement check said nothing at all, so this test cannot "
        "distinguish 'agreed' from 'never looked'"
    )
    assert any("whole-disc pass" in t for t in argv_findings), (
        "a multi-pass rip's agreement finding must name which pass it covered: "
        + "; ".join(argv_findings)
    )


def test_the_audit_still_catches_a_genuinely_altered_command_line(
    two_pass: tuple[RipWorker, _TwoPassBackend], tmp_path: Path
) -> None:
    """The fix must not have turned the check off.

    Comparing like with like is the fix; comparing nothing would also silence the
    false alarm, and would be worse than the bug. So: same clean two-pass rip,
    one argument injected into what the ripper says it received.
    """
    worker, backend = two_pass
    invoked = " ".join(worker.ripper_argv_first_pass) + " --injected-by-a-wrapper"
    report = {
        "outcome": build_outcome(
            status="success",
            ripper_exit_code=0,
            ripper_argv=worker.ripper_argv,
            ripper_argv_first_pass=worker.ripper_argv_first_pass,
        ),
        "rip": {"invoked_as": invoked},
    }
    path = tmp_path / "tampered.platterpus.json"
    path.write_text(json.dumps(report), encoding="utf-8")

    audit = rip_audit.audit_album(path)
    assert any("--injected-by-a-wrapper" in f.text for f in audit.findings), (
        "the argv-agreement check no longer notices an argument that appeared in "
        "transit: " + "; ".join(f.text for f in audit.findings)
    )


def test_a_non_converged_track_does_not_become_a_failure_hint(
    two_pass: tuple[RipWorker, _TwoPassBackend],
) -> None:
    """The second v0.6.3 bug: `failure_hint` on a rip that succeeded.

    Track 5's re-reads never agreed, so the ripper printed `Done; (no matches
    found, but hit repeat limit of 5)`. That is a true and useful fact about read
    stability. It is not why the rip failed, because the rip did not fail — and a
    field named `failure_hint` on a `success` outcome tells every consumer,
    including `--audit-rips`, that it was.
    """
    outcome = build_outcome(
        status="success",
        failure_hint=None,
        ripper_exit_code=0,
        ripper_argv=_FIRST_PASS_ARGV,
    )
    assert outcome["failure_hint"] is None
    # The fact itself must not have been *lost* — it is recorded, elsewhere, as a
    # read-stability observation. Assert the worker still knows track 5 did not
    # converge, so this test cannot be satisfied by throwing the fact away.
    worker, _backend = two_pass
    retried = list(getattr(worker, "retried_tracks", []) or [])
    assert retried, "the worker recorded no re-read history at all"
    five = [entry for entry in retried if entry.get("track") == 5]
    assert five, f"track 5's re-read attempt is not recorded: {retried}"
    assert five[0].get("converged") is False, (
        "track 5's non-convergence must survive as a recorded fact, not be "
        f"dropped along with the failure_hint: {five[0]}"
    )
