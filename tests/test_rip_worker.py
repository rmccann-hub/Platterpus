"""Tests for platterpus.workers.rip_worker.

We drive the worker synchronously (no QThread, no event loop) — Qt
signals are callable regardless of whether an event loop is running.
Connected slots receive emissions immediately because we use direct
connections by default. This keeps the tests fast and deterministic.

The RipBackend is replaced with a fake so we don't need a real
whipper binary.
"""

from __future__ import annotations

import re
import subprocess
import time
from collections.abc import Iterable
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from platterpus.adapters.rip_backend import (
    RipBackend,
    RipError,
    RipHandle,
    RipMetadata,
    TrackTag,
)
from platterpus.rip_plan import PLAN_PREFIX
from platterpus.workers import rip_worker as rip_worker_module
from platterpus.workers.rip_worker import (
    RipParameters,
    RipWorker,
    _describe_activity,
)

# The `qapp` fixture comes from tests/conftest.py. Worker tests don't
# strictly need a QApplication (QCoreApplication would be enough), but
# the UI tests in the same suite do — so we standardize on the wider
# fixture to avoid "QCoreApplication created, can't upgrade" crashes.


# --- Fakes ----------------------------------------------------------------


class _FakeHandle:
    """Implements the RipHandle interface for the worker to consume.

    **`wait()` honours its timeout.** It used to accept the argument and return the
    exit code anyway, which made this fake incapable of the failure it was standing
    in for: the real `wait()` on an undrained pipe blocks forever, and a fake that
    always returns instantly means no test can ever see that (`docs/testing.md`
    §5.t). `never_exits=True` makes it behave like the real thing does when the
    ripper is blocked writing to a full pipe.
    """

    def __init__(
        self,
        lines: Iterable[str] = (),
        exit_code: int = 0,
        *,
        never_exits: bool = False,
        cancel_returns: int | None = -15,
    ) -> None:
        self._lines: list[str] = list(lines)
        self._exit_code: int = exit_code
        self._never_exits: bool = never_exits
        self._cancel_returns: int | None = cancel_returns
        self.cancel_calls: int = 0
        self.terminate_calls: int = 0
        # Every timeout the worker asked us to wait for, so a test can assert the
        # wait was *bounded* rather than merely that it returned.
        self.wait_timeouts: list[float | None] = []

    def log_lines(self) -> Iterable[str]:
        yield from self._lines

    def wait(self, timeout: float | None = None) -> int:
        self.wait_timeouts.append(timeout)
        if self._never_exits:
            if timeout is None:
                # The bug, made loud instead of infinite: an unbounded wait here is
                # what hung the rip worker's thread forever. Failing fast is the
                # only way a test can tell the difference.
                raise AssertionError(
                    "wait() was called with NO timeout while the ripper is still "
                    "running and its pipe is undrained — this is the deadlock. "
                    "Use RipWorker._reap_ripper, which bounds the wait."
                )
            raise subprocess.TimeoutExpired(cmd="cyanrip", timeout=timeout)
        return self._exit_code

    def terminate(self) -> None:
        # Non-blocking cancel path used from the GUI thread — the worker forwards
        # here so a wedged drive can't freeze the window.
        self.terminate_calls += 1

    def cancel(
        self, term_timeout: float = 5.0, kill_timeout: float = 5.0
    ) -> int | None:
        self.cancel_calls += 1
        return self._cancel_returns


class _FakeBackend(RipBackend):
    """Backend whose `rip()` returns a pre-baked _FakeHandle."""

    def __init__(self, handle: _FakeHandle | None = None) -> None:
        self._handle: _FakeHandle | None = handle
        self._raise_on_rip: Exception | None = None
        self.rip_calls: list[dict[str, object]] = []
        # Optional: called with each recorded rip-call dict, so a test can write
        # the log/FLAC files a real rip would produce (used by the auto-fix
        # tests). Default None → no files written (the other tests don't need it).
        self.rip_side_effect = None

    def set_handle(self, handle: _FakeHandle) -> None:
        self._handle = handle

    def raise_on_rip(self, exc: Exception) -> None:
        self._raise_on_rip = exc

    # ABC plumbing — not used by the worker tests but required to be a
    # non-abstract subclass.
    def list_drives(self) -> list:  # type: ignore[type-arg]
        return []

    def disc_info(self, drive: str):  # type: ignore[no-untyped-def]
        raise NotImplementedError

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
        metadata=None,
        # Mirrors the ABC exactly. A fake that quietly accepts **kwargs would
        # have hidden this widening, which is the harness-fidelity rule: a
        # stand-in must not be more permissive than the real thing.
        disc_track_total: int | None = None,
        read_speed: int = 0,
        only_tracks: tuple[int, ...] = (),
    ) -> RipHandle:
        self.rip_calls.append(
            {
                "drive": drive,
                "release_id": release_id,
                "output_dir": output_dir,
                "unknown": unknown,
                "cover_art": cover_art,
                "max_retries": max_retries,
                "secure_rerip_matches": secure_rerip_matches,
                "force_overread": force_overread,
                "read_offset_override": read_offset_override,
                "metadata": metadata,
                "read_speed": read_speed,
                "only_tracks": tuple(only_tracks),
            }
        )
        if self._raise_on_rip:
            raise self._raise_on_rip
        if self.rip_side_effect is not None:
            self.rip_side_effect(self.rip_calls[-1])
        assert self._handle is not None
        return self._handle  # type: ignore[return-value]

    def version(self) -> str:
        return "fake 0.0.0"


def _params(tmp_path: Path, **overrides: object) -> RipParameters:
    defaults: dict = {
        "drive": "/dev/sr0",
        "release_id": "mbid-abc",
        "output_dir": tmp_path,
        "track_template": "t",
        "disc_template": "d",
    }
    defaults.update(overrides)
    return RipParameters(**defaults)


# --- Signal-collector helper ----------------------------------------------


def _ripper_lines(lines: list[str]) -> list[str]:
    """The log lines that came from the RIPPER, with our own plan removed.

    Every rip now opens by stating what it is about to do — the pre-rip plan, so
    a flag that is off is discovered before a 70-minute read rather than after
    it. Those lines share a prefix precisely so a consumer (a test, or the eye)
    can tell them from the ripper's own output. Filtering here keeps each test
    asserting its own subject rather than re-listing the plan.
    """
    return [line for line in lines if not line.startswith(PLAN_PREFIX)]


class _Signals:
    """Accumulates signal emissions for assertion."""

    def __init__(self) -> None:
        self.log_lines: list[str] = []
        self.progress: list[tuple[float, float]] = []  # (overall, task)
        self.statuses: list[str] = []
        self.current_tracks: list[int] = []
        self.completed_tracks: list[int] = []
        self.errors: list[str] = []
        self.finished: list[tuple[bool, str]] = []

    def attach(self, worker: RipWorker) -> None:
        worker.log_line.connect(self.log_lines.append)
        worker.progress.connect(
            lambda overall, task: self.progress.append((overall, task))
        )
        worker.status.connect(self.statuses.append)
        worker.current_track.connect(self.current_tracks.append)
        worker.track_completed.connect(self.completed_tracks.append)
        worker.error.connect(self.errors.append)
        worker.finished.connect(lambda ok, path: self.finished.append((ok, path)))


# --- Happy-path tests -----------------------------------------------------


def test_emits_log_lines_in_order(qapp: QApplication, tmp_path: Path) -> None:
    handle = _FakeHandle(lines=["one", "two", "three"], exit_code=0)
    backend = _FakeBackend(handle=handle)
    worker = RipWorker(backend, _params(tmp_path))
    sigs = _Signals()
    sigs.attach(worker)

    worker.start_rip()

    # The rip now opens with its own PLAN (rip_plan.describe_rip_plan) — what it
    # is about to do, before anything spawns. Those lines are ours, not the
    # ripper's, and they are all prefixed; strip them here so this test keeps
    # asserting the thing it is about, which is the ORDER of the ripper's output.
    assert _ripper_lines(sigs.log_lines) == ["one", "two", "three"]
    # …and the plan really did precede them, rather than being filtered into
    # nothing by a prefix that no longer matches.
    assert sigs.log_lines[0].startswith(PLAN_PREFIX)
    assert sigs.finished == [(True, "")]
    assert sigs.errors == []


def test_finished_reports_success_on_zero_exit(
    qapp: QApplication, tmp_path: Path
) -> None:
    handle = _FakeHandle(lines=[], exit_code=0)
    worker = RipWorker(_FakeBackend(handle=handle), _params(tmp_path))
    sigs = _Signals()
    sigs.attach(worker)

    worker.start_rip()

    assert sigs.finished[0][0] is True


def test_secure_rerip_param_forwarded_to_backend(
    qapp: QApplication, tmp_path: Path
) -> None:
    """RipParameters.secure_rerip_matches must reach RipBackend.rip()."""
    handle = _FakeHandle(lines=[], exit_code=0)
    backend = _FakeBackend(handle=handle)
    worker = RipWorker(backend, _params(tmp_path, secure_rerip_matches=2))

    worker.start_rip()

    assert backend.rip_calls[0]["secure_rerip_matches"] == 2


def test_force_overread_param_forwarded_to_backend(
    qapp: QApplication, tmp_path: Path
) -> None:
    """RipParameters.force_overread (the Overread toggle → cyanrip -O) must
    reach RipBackend.rip(); off stays off."""
    handle = _FakeHandle(lines=[], exit_code=0)
    backend = _FakeBackend(handle=handle)
    worker = RipWorker(backend, _params(tmp_path, force_overread=True))

    worker.start_rip()

    assert backend.rip_calls[0]["force_overread"] is True


# --- Adaptive read-speed ladder -------------------------------------------


def test_fixed_speed_mode_is_single_pass_and_forwards_read_speed(
    qapp: QApplication, tmp_path: Path
) -> None:
    backend = _FakeBackend(handle=_FakeHandle(lines=[], exit_code=0))
    worker = RipWorker(
        backend, _params(tmp_path, read_speed_mode="fixed", read_speed=4)
    )

    worker.start_rip()

    assert len(backend.rip_calls) == 1  # no ladder in fixed mode
    assert backend.rip_calls[0]["read_speed"] == 4


def test_auto_ladder_clean_disc_is_a_single_pass(
    qapp: QApplication, tmp_path: Path
) -> None:
    # No read errors (the default parse of no-log → no errors) → one pass, at max.
    backend = _FakeBackend(handle=_FakeHandle(lines=[], exit_code=0))
    worker = RipWorker(backend, _params(tmp_path, read_speed_mode="auto_ladder"))

    worker.start_rip()

    assert len(backend.rip_calls) == 1
    assert backend.rip_calls[0]["read_speed"] == 0  # started at the drive's max
    assert worker.speed_attempts[0].clean is True


def test_auto_ladder_re_rips_slower_on_read_errors_then_stops_clean(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A pass with unrecoverable read errors triggers a re-rip a rung slower;
    once a pass reads clean, the ladder stops."""
    import platterpus.workers.rip_worker as mod

    backend = _FakeBackend(handle=_FakeHandle(lines=["ripping"], exit_code=0))
    worker = RipWorker(backend, _params(tmp_path, read_speed_mode="auto_ladder"))
    # Errors on the first pass, clean on the second.
    verdicts = iter([True, False])
    monkeypatch.setattr(mod, "read_errors_present", lambda _log: next(verdicts, False))
    sigs = _Signals()
    sigs.attach(worker)

    worker.start_rip()

    assert len(backend.rip_calls) == 2  # re-ripped once
    assert backend.rip_calls[0]["read_speed"] == 0  # max first
    assert backend.rip_calls[1]["read_speed"] == 8  # stepped down to 8×
    attempts = worker.speed_attempts
    assert [a.clean for a in attempts] == [False, True]
    assert sigs.finished == [(True, "")]


def test_auto_ladder_hard_failure_is_not_marked_clean(
    qapp: QApplication, tmp_path: Path
) -> None:
    """Regression: a pass that HARD-FAILS (non-zero exit) must be recorded as NOT
    clean, so the report's `unresolved` flag is right — even if its log shows no
    read-error line. Earlier code marked a failed rip clean (success short-circuit)."""
    from platterpus.read_speed_ladder import attempts_to_report

    backend = _FakeBackend(handle=_FakeHandle(lines=[], exit_code=1))  # hard fail
    worker = RipWorker(backend, _params(tmp_path, read_speed_mode="auto_ladder"))

    worker.start_rip()

    assert len(backend.rip_calls) == 1  # a hard failure is NOT re-ripped
    assert worker.speed_attempts[-1].clean is False
    assert attempts_to_report(worker.speed_attempts)["unresolved"] is True


def test_auto_ladder_flags_unresolved_after_exhausting_the_ladder(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A disc that never reads clean escalates down the whole ladder + -Z, then
    stops (bounded) and is left FLAGGED as unresolved — quality never went down."""
    import platterpus.workers.rip_worker as mod
    from platterpus.read_speed_ladder import MAX_ATTEMPTS, attempts_to_report

    backend = _FakeBackend(handle=_FakeHandle(lines=["ripping"], exit_code=0))
    worker = RipWorker(backend, _params(tmp_path, read_speed_mode="auto_ladder"))
    monkeypatch.setattr(mod, "read_errors_present", lambda _log: True)

    worker.start_rip()

    assert len(backend.rip_calls) <= MAX_ATTEMPTS  # bounded, never infinite
    assert worker.speed_attempts[-1].clean is False
    report = attempts_to_report(worker.speed_attempts)
    assert report["unresolved"] is True and report["escalated"] is True


def test_auto_fix_keeps_flag_when_rerip_yields_no_usable_log(
    qapp: QApplication, tmp_path: Path
) -> None:
    """Safety path: an unstable track triggers an auto-fix re-rip, but if that
    re-rip produces no usable log (nothing to trust), the original is kept and the
    track stays honestly FLAGGED — no regression, no bogus swap."""
    from platterpus.read_speed_ladder import attempts_to_report

    rip_log = tmp_path / "Album" / "rip.log"
    rip_log.parent.mkdir(parents=True)
    rip_log.write_text(
        "cyanrip 0.9.3 (release)\n"
        "Disc tracks:    1\n"
        "Done; (no matches found, but hit repeat limit of 5)\n"
        "Track 1 ripped and encoded successfully!\n"
        "  EAC CRC32:     329DC760 (after 5 rips)\n"
        "Ripping errors: 0\n",  # cyanrip's whole-disc count stays 0 — the trap
        encoding="utf-8",
    )
    # No rip_side_effect → the re-rip writes no temp log, so auto-fix bails safely.
    backend = _FakeBackend(handle=_FakeHandle(lines=["ripping"], exit_code=0))
    worker = RipWorker(backend, _params(tmp_path, read_speed_mode="auto_ladder"))

    worker.start_rip()

    assert len(backend.rip_calls) == 2  # it TRIED the auto-fix re-rip…
    assert worker.retried_tracks == []  # …but nothing usable came back
    assert worker.unstable_tracks == [1]  # so track 1 stays flagged (no regression)
    # The pass had no HARD errors, so it's "clean" in the attempt sense; the
    # instability is carried by unstable_tracks, which drives `unresolved`.
    assert worker.speed_attempts[-1].clean is True
    report = attempts_to_report(worker.speed_attempts, worker.unstable_tracks)
    assert report["unresolved"] is True  # still flagged via the unstable track
    assert report["unstable_tracks"] == [1]


def test_auto_ladder_speed_locked_drive_escalates_z_never_sends_S(
    qapp: QApplication, tmp_path: Path
) -> None:
    """Real-hardware safety fix: cyanrip ABORTS the rip if handed `-S` on a drive
    that reports its speed as "unchangeable" (the BDR-209D does). When a pass's
    log reveals that, the ladder must escalate via `-Z` ONLY and never send `-S`
    — otherwise a disc with read errors would turn every escalation into a crash.
    """
    rip_log = tmp_path / "Album" / "rip.log"
    rip_log.parent.mkdir(parents=True)
    rip_log.write_text(
        "cyanrip 0.9.3 (release)\n"
        "Speed:          default (unchangeable)\n"  # the drive can't slow down
        "Disc tracks:    1\n"
        "Track 1 ripped and encoded successfully!\n"
        "  EAC CRC32:     329DC760\n"
        "Ripping errors: 3\n",  # real unrecoverable errors → the ladder escalates
        encoding="utf-8",
    )
    backend = _FakeBackend(handle=_FakeHandle(lines=["ripping"], exit_code=0))
    worker = RipWorker(backend, _params(tmp_path, read_speed_mode="auto_ladder"))

    worker.start_rip()

    # It escalated (more than one pass) but NEVER handed cyanrip a slower speed.
    assert len(backend.rip_calls) >= 2
    assert all(call["read_speed"] == 0 for call in backend.rip_calls)
    # …and the escalation happened via -Z climbing instead (2, then 3).
    zs = [call["secure_rerip_matches"] for call in backend.rip_calls]
    assert zs == [0, 2, 3]


# --- Per-track auto-fix (re-rip the unstable track alone, keep it if it converges)

_PASS1_UNSTABLE = (
    "cyanrip 0.9.3 (release)\n"
    "Disc tracks:    3\n"
    "Done; (2 out of 2 matches for current checksum AAAA1111)\n"
    "Track 1 ripped and encoded successfully!\n"
    "  EAC CRC32:     11111111\n"
    "  File(s):\n"
    "    Artist/Album/01 - A.flac\n"
    "Done; (no matches found, but hit repeat limit of 5)\n"  # track 3 unstable
    "Track 3 ripped and encoded successfully!\n"
    "  EAC CRC32:     33333333 (after 5 rips)\n"
    "  File(s):\n"
    "    Artist/Album/03 - C.flac\n"
    "Ripping errors: 0\n"  # whole-disc count stays 0 — instability, not errors
)


def _fake_rip_writer(pass1_log: str, rerip_log: str, rerip_makes_flac: bool):
    """Return a rip_side_effect that writes a whole-disc log on the full rip and a
    (temp) re-rip log — plus, optionally, track 3's re-ripped FLAC — on the -l pass."""

    def _write(call: dict) -> None:
        out = call["output_dir"]
        rel = out / "Artist" / "Album"
        rel.mkdir(parents=True, exist_ok=True)
        if call["only_tracks"]:
            (rel / "rerip.log").write_text(rerip_log, encoding="utf-8")
            if rerip_makes_flac:
                (rel / "03 - C.flac").write_bytes(b"FIXED-FLAC-BYTES")
        else:
            (rel / "rip.log").write_text(pass1_log, encoding="utf-8")

    return _write


def test_auto_fix_swaps_in_reripped_track_when_it_converges(
    qapp: QApplication, tmp_path: Path
) -> None:
    """The auto-fix (user's call): an unstable track is re-ripped ALONE with a
    harder -Z; when the re-read now converges, its FLAC replaces the original and
    the track drops off the unstable list."""
    rerip_ok = (
        "cyanrip 0.9.3 (release)\n"
        "Disc tracks:    3\n"
        "Done; (2 out of 2 matches for current checksum BBBB2222)\n"  # now converges
        "Track 3 ripped and encoded successfully!\n"
        "  EAC CRC32:     99999999\n"
        "  File(s):\n"
        "    Artist/Album/03 - C.flac\n"
        "Ripping errors: 0\n"
    )
    backend = _FakeBackend(handle=_FakeHandle(lines=["ripping"], exit_code=0))
    backend.rip_side_effect = _fake_rip_writer(_PASS1_UNSTABLE, rerip_ok, True)
    worker = RipWorker(
        backend,
        _params(tmp_path, read_speed_mode="auto_ladder", secure_rerip_matches=2),
    )

    worker.start_rip()

    # Two rips: the whole disc, then a -l re-rip of only the unstable track 3.
    assert len(backend.rip_calls) == 2
    assert backend.rip_calls[1]["only_tracks"] == (3,)
    assert backend.rip_calls[1]["read_speed"] == 0  # never -S
    # The re-rip uses the user's configured -Z (their number is the ceiling).
    assert backend.rip_calls[1]["secure_rerip_matches"] == 2
    # Track 3 was fixed → no longer unstable, recorded as replaced.
    assert worker.unstable_tracks == []
    assert worker.retried_tracks == [
        {
            "track": 3,
            "trigger": "instability",
            "reripped_z": 2,
            "converged": True,
            "replaced": True,
        }
    ]
    # The improved FLAC was copied into the album folder.
    swapped = tmp_path / "Artist" / "Album" / "03 - C.flac"
    assert swapped.read_bytes() == b"FIXED-FLAC-BYTES"


def _rerip_ok_log(*, ar_v1: str = "AAAA0001", ar_v2: str = "BBBB0002") -> str:
    """A re-rip log for track 3 that CONVERGED, with its own AccurateRip results.

    The AccurateRip lines matter for the H5 half of this change: the addendum must
    supersede the whole per-track record, not just the CRC, so the fixture has to
    carry values that differ from the first pass or the assertion could not tell.
    """
    return (
        "cyanrip 0.9.3 (release)\n"
        "Disc tracks:    3\n"
        "Done; (2 out of 2 matches for current checksum BBBB2222)\n"
        "Track 3 ripped and encoded successfully!\n"
        "  EAC CRC32:     99999999\n"  # the shipped file's CRC
        # The REAL line shape, copied from the committed rig log
        # (output_reference/cyanrip_fork_flac/…): two-space indent under an
        # "Accurip:" header, bare CRC, verdict and confidence in parentheses. A
        # fixture that invents the shape tests our guess at cyanrip's output.
        "  Accurip:       disc found in database (max confidence: 200)\n"
        f"    Accurip v1:  {ar_v1} (accurately ripped, confidence 42)\n"
        f"    Accurip v2:  {ar_v2} (accurately ripped, confidence 42)\n"
        "  File(s):\n"
        "    Artist/Album/03 - C.flac\n"
        "Ripping errors: 0\n"
    )


def _run_auto_fix_rip(tmp_path: Path) -> Path:
    """Drive a rip whose track 3 is unstable and is rescued by the auto-fix.

    Returns the album folder. Shared by the addendum tests below so they cannot
    disagree about what "the rip that swapped a track in" means.
    """
    backend = _FakeBackend(handle=_FakeHandle(lines=["ripping"], exit_code=0))
    backend.rip_side_effect = _fake_rip_writer(_PASS1_UNSTABLE, _rerip_ok_log(), True)
    worker = RipWorker(
        backend,
        _params(tmp_path, read_speed_mode="auto_ladder", secure_rerip_matches=2),
    )
    worker.start_rip()
    return tmp_path / "Artist" / "Album"


def test_auto_fix_leaves_the_rippers_own_log_byte_exact(
    qapp: QApplication, tmp_path: Path
) -> None:
    """Regression (round 7 lap 10, H1): **do not touch the ripper's log.**

    We used to append the swap addendum to it. cyanrip's log ends with a
    ``Log FUN512:`` self-checksum and ``cyanrip --verify-log`` *rejects trailing
    content by design* — the fork had asked that exact question in round 5, answered
    no, and pinned it with a test — so every auto-fixed disc shipped a log the ripper
    itself would call modified. Found by them reading a real rig artifact, because
    our own integrity check verified the log **we** wrote against the checksum **we**
    computed and had nothing to say about theirs.

    This asserts the bytes, not the absence of a marker: an assertion that only
    looked for the old marker would pass for a differently-worded append.
    """
    album = _run_auto_fix_rip(tmp_path)
    log_path = album / "rip.log"
    album_log = log_path.read_text(encoding="utf-8")

    # The swap really happened — the floor under everything below. Without it this
    # test would pass on a rip that never auto-fixed anything, which is the
    # "satisfied by finding nothing" trap.
    assert (album / "03 - C.flac").read_bytes() == b"FIXED-FLAC-BYTES"

    assert album_log == _PASS1_UNSTABLE, (
        "the ripper's log is no longer byte-exact; something appended to it again"
    )
    assert "[Platterpus auto-fix addendum]" not in album_log
    assert "99999999" not in album_log, (
        "the shipped CRC leaked into the ripper's log — it belongs in the sidecar"
    )


def test_auto_fix_writes_the_supersede_record_to_a_sidecar(
    qapp: QApplication, tmp_path: Path
) -> None:
    """The other half of H1: the supersede must still EXIST, beside the log.

    Leaving the ripper's log alone is only correct if the record moves rather than
    disappears — the first-pass log's CRC for a swapped track describes the bytes we
    deleted (#19), and a fix that made the supersede invisible would trade one wrong
    artifact for another.

    Also pins **H5**: the record supersedes the whole per-track block. The old
    appended version named the CRC alone, leaving the archived AccurateRip v1/v2 and
    the "not attempted" re-read verdict describing the discarded read.
    """
    from platterpus.rip_addendum import ADDENDUM_MARKER, addendum_path_for

    album = _run_auto_fix_rip(tmp_path)
    sidecar = addendum_path_for(album / "rip.log")

    assert sidecar.is_file(), f"no addendum sidecar at {sidecar}"
    text = sidecar.read_text(encoding="utf-8")
    assert ADDENDUM_MARKER in text
    assert "Track 3" in text
    assert "99999999" in text, "the shipped file's CRC is missing"
    # H5: the AccurateRip values and the re-read verdict, from the re-rip's own log.
    assert "AAAA0001" in text, "AccurateRip v1 was not superseded"
    assert "BBBB0002" in text, "AccurateRip v2 was not superseded"
    assert "converged" in text.lower(), "the secure re-read verdict was not recorded"
    # It says why it is a separate file, so a reader who finds it understands.
    assert "verify-log" in text


def test_reading_the_log_back_still_honours_the_supersede(
    qapp: QApplication, tmp_path: Path
) -> None:
    """Moving the addendum must not make the supersede invisible to a re-parse.

    This is the trap the H1 fix could have walked into. The addendum existed in the
    first place because a re-parse from disk got CRCs for bytes that are not on disk
    — the GUI never saw it, since it patches from live worker state. So the sidecar
    is only a fix if the *reader* folds it back in.
    """
    from platterpus.parsers.cyanrip_log import parse_cyanrip_log
    from platterpus.rip_addendum import read_log_with_addendum

    album = _run_auto_fix_rip(tmp_path)
    log_path = album / "rip.log"

    # The ripper's log ALONE still carries the discarded read's CRC — proving the
    # sidecar is doing real work rather than being redundant.
    alone = parse_cyanrip_log(log_path.read_text(encoding="utf-8"))
    track3_alone = next(t for t in alone.tracks if t.number == 3)
    assert track3_alone.copy_crc != "99999999"

    # Read through the sanctioned reader and the shipped CRC wins.
    combined = parse_cyanrip_log(read_log_with_addendum(log_path))
    track3 = next(t for t in combined.tracks if t.number == 3)
    assert track3.copy_crc == "99999999", (
        "a re-parse through read_log_with_addendum did not pick up the supersede"
    )


def test_auto_fix_keeps_original_when_rerip_still_unstable(
    qapp: QApplication, tmp_path: Path
) -> None:
    """If the re-rip STILL doesn't converge, the original is kept untouched (no
    regression) and the track stays flagged unstable."""
    rerip_still_bad = (
        "cyanrip 0.9.3 (release)\n"
        "Disc tracks:    3\n"
        "Done; (no matches found, but hit repeat limit of 5)\n"  # still no converge
        "Track 3 ripped and encoded successfully!\n"
        "  EAC CRC32:     44444444 (after 5 rips)\n"
        "  File(s):\n"
        "    Artist/Album/03 - C.flac\n"
        "Ripping errors: 0\n"
    )
    backend = _FakeBackend(handle=_FakeHandle(lines=["ripping"], exit_code=0))
    # rerip_makes_flac=True to prove we DON'T swap even when a temp file exists.
    backend.rip_side_effect = _fake_rip_writer(_PASS1_UNSTABLE, rerip_still_bad, True)
    worker = RipWorker(
        backend,
        _params(tmp_path, read_speed_mode="auto_ladder", secure_rerip_matches=2),
    )

    worker.start_rip()

    assert len(backend.rip_calls) == 2  # it did try the re-rip
    assert worker.unstable_tracks == [3]  # …but track 3 is still flagged
    assert worker.retried_tracks == [
        {
            "track": 3,
            "trigger": "instability",
            "reripped_z": 2,
            "converged": False,
            "replaced": False,
        }
    ]
    # The original was NOT overwritten by the (non-converged) re-rip.
    assert not (tmp_path / "Artist" / "Album" / "03 - C.flac").exists()


def test_dynamic_mode_ripps_fast_then_secures_only_unverified_track(
    qapp: QApplication, tmp_path: Path
) -> None:
    """Dynamic secure-rerip (the user's ask): pass 1 runs FAST (no -Z); then only
    the track that didn't match AccurateRip is secure-re-ripped, and kept when it
    now converges. The track that matched the DB on the first read is left alone."""
    pass1 = (
        "cyanrip 0.9.3 (release)\n"
        "Disc tracks:    2\n"
        "Track 1 ripped and encoded successfully!\n"
        "  EAC CRC32:     11111111\n"
        "    Accurip v1:  5D3C90CB (accurately ripped, confidence 200)\n"  # proven
        "  File(s):\n"
        "    Artist/Album/01 - A.flac\n"
        "Track 2 ripped and encoded successfully!\n"
        "  EAC CRC32:     22222222\n"
        "    Accurip v1:  DEADBEEF (not found, either a new pressing, or bad rip)\n"
        "  File(s):\n"
        "    Artist/Album/02 - B.flac\n"
        "Ripping errors: 0\n"
    )
    rerip = (
        "cyanrip 0.9.3 (release)\n"
        "Disc tracks:    2\n"
        "Done; (2 out of 2 matches for current checksum ABCD1234)\n"  # now converges
        "Track 2 ripped and encoded successfully!\n"
        "  EAC CRC32:     99999999\n"
        "  File(s):\n"
        "    Artist/Album/02 - B.flac\n"
        "Ripping errors: 0\n"
    )

    def side_effect(call: dict) -> None:
        rel = call["output_dir"] / "Artist" / "Album"
        rel.mkdir(parents=True, exist_ok=True)
        if call["only_tracks"]:
            (rel / "rerip.log").write_text(rerip, encoding="utf-8")
            (rel / "02 - B.flac").write_bytes(b"SECURED-B")
        else:
            (rel / "rip.log").write_text(pass1, encoding="utf-8")

    backend = _FakeBackend(handle=_FakeHandle(lines=["ripping"], exit_code=0))
    backend.rip_side_effect = side_effect
    worker = RipWorker(
        backend,
        _params(
            tmp_path,
            read_speed_mode="auto_ladder",
            secure_rerip_matches=2,
            secure_rerip_dynamic=True,
        ),
    )

    worker.start_rip()

    # Pass 1 was FAST — no -Z, whole disc.
    assert backend.rip_calls[0]["secure_rerip_matches"] == 0
    assert backend.rip_calls[0]["only_tracks"] == ()
    # Then ONLY the unverified track 2 was secured, at the configured -Z 2.
    assert len(backend.rip_calls) == 2
    assert backend.rip_calls[1]["only_tracks"] == (2,)
    assert backend.rip_calls[1]["secure_rerip_matches"] == 2
    assert worker.retried_tracks == [
        {
            "track": 2,
            "trigger": "accuraterip",
            "reripped_z": 2,
            "converged": True,
            "replaced": True,
        }
    ]
    assert worker.unstable_tracks == []
    assert (tmp_path / "Artist" / "Album" / "02 - B.flac").read_bytes() == b"SECURED-B"
    # The report can explain WHY the re-rip ran: dynamic mode, disc in the DB,
    # a track needed securing → engaged.
    assert worker.secure_rerip_report == {
        "mode": "dynamic",
        "engaged": True,
        "disc_in_accuraterip": True,
        "skipped_reason": None,
        # The securing pass ran to completion and recorded every track's outcome.
        # `True` here would mean it was cut short (app shutdown, cancel, a re-rip
        # that produced no log) — the state run 4 hit on real hardware, where an
        # engaged pass left an empty `retried_tracks` and said nothing about it.
        "interrupted": False,
    }


def test_dynamic_mode_skips_rerip_when_disc_not_in_accuraterip(
    qapp: QApplication, tmp_path: Path
) -> None:
    """Regression: a disc that isn't in AccurateRip at all (a CD-R / obscure
    pressing — every track "fails" AR because there's nothing to match) must NOT
    trigger a whole-disc secure re-rip. There's no DB consensus to converge
    toward, so a re-rip can't verify anything and would just re-read + swap every
    track (the "20min → 1h" slowdown dynamic mode exists to avoid). The fast pass
    stands, no track re-ripped."""
    pass1 = (
        "cyanrip 0.9.3 (release)\n"
        "Disc tracks:    2\n"
        "Track 1 ripped and encoded successfully!\n"
        "  EAC CRC32:     11111111\n"
        "    Accurip v1:  AAAAAAAA (not found, either a new pressing, or bad rip)\n"
        "  File(s):\n"
        "    Artist/Album/01 - A.flac\n"
        "Track 2 ripped and encoded successfully!\n"
        "  EAC CRC32:     22222222\n"
        "    Accurip v1:  BBBBBBBB (not found, either a new pressing, or bad rip)\n"
        "  File(s):\n"
        "    Artist/Album/02 - B.flac\n"
        "Ripping errors: 0\n"
    )

    def side_effect(call: dict) -> None:
        rel = call["output_dir"] / "Artist" / "Album"
        rel.mkdir(parents=True, exist_ok=True)
        # A re-rip would be a bug here — write only the whole-disc pass log.
        if not call["only_tracks"]:
            (rel / "rip.log").write_text(pass1, encoding="utf-8")

    backend = _FakeBackend(handle=_FakeHandle(lines=["ripping"], exit_code=0))
    backend.rip_side_effect = side_effect
    worker = RipWorker(
        backend,
        _params(
            tmp_path,
            read_speed_mode="auto_ladder",
            secure_rerip_matches=2,
            secure_rerip_dynamic=True,
        ),
    )

    worker.start_rip()

    assert len(backend.rip_calls) == 1  # ONE fast pass, no targeted re-rip
    assert backend.rip_calls[0]["only_tracks"] == ()
    assert worker.retried_tracks == []
    # The report explains WHY the shaky-looking tracks weren't re-ripped: the
    # disc isn't in AccurateRip, so a targeted re-rip couldn't verify anything.
    assert worker.secure_rerip_report == {
        "mode": "dynamic",
        "engaged": False,
        "disc_in_accuraterip": False,
        "skipped_reason": "disc_not_in_accuraterip",
        # Never started, so it cannot have been interrupted.
        "interrupted": False,
    }


def test_secure_rerip_report_uniform_and_off_modes(
    qapp: QApplication, tmp_path: Path
) -> None:
    """The report's secure_rerip block reflects the non-dynamic modes too:
    uniform (-Z on every track) is 'engaged' from the start; plain off (no -Z)
    has no block to show."""
    # Uniform: a -Z is set but dynamic is off → -Z applies to every track.
    backend = _FakeBackend(handle=_FakeHandle(lines=[], exit_code=0))
    worker = RipWorker(
        backend,
        _params(tmp_path, secure_rerip_matches=2, secure_rerip_dynamic=False),
    )
    worker.start_rip()
    report = worker.secure_rerip_report
    assert report is not None
    assert report["mode"] == "uniform" and report["engaged"] is True

    # Off: no -Z at all → nothing to explain, so no block.
    worker_off = RipWorker(
        _FakeBackend(handle=_FakeHandle(lines=[], exit_code=0)),
        _params(tmp_path, secure_rerip_matches=0),
    )
    worker_off.start_rip()
    assert worker_off.secure_rerip_report is None


def test_swap_in_reripped_track_never_corrupts_the_master(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: the auto-fix FLAC swap is atomic (temp + os.replace), so a
    failure mid-swap leaves the original archival master intact and no temp
    behind — never a truncated/corrupt FLAC where a good one was."""
    from types import SimpleNamespace

    rel = "Artist/Album/02 - B.flac"
    (tmp_path / "Artist" / "Album").mkdir(parents=True)
    dst = tmp_path / rel
    dst.write_bytes(b"ORIGINAL-GOOD-MASTER")
    tmp_root = tmp_path / "refix"
    (tmp_root / "Artist" / "Album").mkdir(parents=True)
    (tmp_root / rel).write_bytes(b"NEW-REREAD")

    worker = RipWorker(_FakeBackend(), _params(tmp_path))

    # Force the atomic replace to fail (disk full / crash surrogate).
    import os

    def boom(_src: object, _dst: object) -> None:
        raise OSError("simulated failure during swap")

    monkeypatch.setattr(os, "replace", boom)

    ok = worker._swap_in_reripped_track(
        SimpleNamespace(filename=rel, number=2), tmp_root
    )

    assert ok is False
    assert dst.read_bytes() == b"ORIGINAL-GOOD-MASTER"  # master untouched
    # No partial temp left in the album dir.
    assert not list((tmp_path / "Artist" / "Album").glob("*.tmp"))


def test_find_log_path_ignores_a_previous_albums_log(
    qapp: QApplication, tmp_path: Path
) -> None:
    """Regression (#20): the output dir is the shared music root. A rip that
    fails before writing its own log must NOT adopt a previous album's log from
    a sibling folder (which rglob-most-recent would otherwise return) and parse
    it as this rip's. Logs older than the rip's start are scoped out."""
    import os

    # A prior album's log, aged an hour into the past.
    stale_dir = tmp_path / "Old Artist" / "Old Album"
    stale_dir.mkdir(parents=True)
    stale = stale_dir / "rip.log"
    stale.write_text("cyanrip 0.9.3\nRipping errors: 0\n", encoding="utf-8")
    old = stale.stat().st_mtime - 3600
    os.utime(stale, (old, old))

    worker = RipWorker(_FakeBackend(), _params(tmp_path))
    worker._rip_started_at = stale.stat().st_mtime + 1800  # this rip started later

    # Only the stale log exists → scoped out → nothing found for this rip.
    assert worker._find_log_path(tmp_path, since=worker._rip_started_at) is None

    # A log this rip actually wrote (newer than the rip start) IS found.
    fresh_dir = tmp_path / "New Artist" / "New Album"
    fresh_dir.mkdir(parents=True)
    fresh = fresh_dir / "rip.log"
    fresh.write_text("cyanrip 0.9.3\nRipping errors: 0\n", encoding="utf-8")
    found = worker._find_log_path(tmp_path, since=worker._rip_started_at)
    assert found == fresh


def test_fixed_mode_never_auto_fixes(qapp: QApplication, tmp_path: Path) -> None:
    """Fixed-speed mode is a single pass with no auto-fix, even if a track was
    unstable — the ladder (and its auto-fix) only run in auto_ladder mode."""
    rel = tmp_path / "Artist" / "Album"
    rel.mkdir(parents=True)
    (rel / "rip.log").write_text(_PASS1_UNSTABLE, encoding="utf-8")
    backend = _FakeBackend(handle=_FakeHandle(lines=["ripping"], exit_code=0))
    worker = RipWorker(backend, _params(tmp_path, read_speed_mode="fixed"))

    worker.start_rip()

    assert len(backend.rip_calls) == 1  # no re-rip
    assert worker.retried_tracks == []


def test_cyanrip_progress_lines_drive_bars_and_track(
    qapp: QApplication, tmp_path: Path
) -> None:
    """cyanrip's \\r-redrawn progress lines (arriving as separate lines via
    universal newlines) must move both bars, set the current track, and
    produce a live status — KDD-18 progress parsing."""
    handle = _FakeHandle(
        lines=[
            "Disc tracks:    16",
            "Ripping track 1, progress - 25.00%, ETA - 3m, errors - 0",
            "Ripping and encoding track 1, progress - 75.00%",
            "Track 1 ripped and encoded successfully!",
            "Ripping track 2, progress - 10.00%",
        ],
        exit_code=0,
    )
    worker = RipWorker(_FakeBackend(handle=handle), _params(tmp_path))
    sigs = _Signals()
    sigs.attach(worker)

    worker.start_rip()

    # Track 1 at 25%: overall = 5 + (0 + .25)/16*90 ≈ 6.4; task = 25.
    overall_1, task_1 = sigs.progress[0]
    assert task_1 == 25.0
    assert 6.0 < overall_1 < 7.0
    # "and encoding" variant parses too.
    assert sigs.progress[1][1] == 75.0
    # Track-done pegs that track's slice (task 100).
    done_overall, done_task = sigs.progress[2]
    assert done_task == 100.0
    assert 10.0 < done_overall < 11.0  # 5 + 1/16*90 ≈ 10.6
    # Track follows along for the row highlight; once per track.
    assert sigs.current_tracks == [1, 2]
    # The completion line ("Track 1 ripped …") fires track_completed(1) so the
    # GUI can mark that row done in the live Status column.
    assert sigs.completed_tracks == [1]
    # Both cyanrip progress forms — the bare "Ripping track N" read and the
    # "Ripping and encoding track N" combined pass — are labelled "Ripping" (one
    # honest verb; "Encoding" hid the disc read, which is the slow part). cyanrip's
    # own per-op ETA is NOT echoed (it resets every phase and is wildly wrong
    # early). No ETA suffix here because the test rip elapses <8s (the minimum
    # before we project one).
    # "of 16" comes from the "Disc tracks: 16" banner (parsed first), so the
    # user sees position at a glance — "track 1 of 16" — from the first line.
    assert any(s.startswith("Ripping track 1 of 16… 25%") for s in sigs.statuses)
    assert any(s.startswith("Ripping track 1 of 16… 75%") for s in sigs.statuses)
    assert not any("Encoding track" in s for s in sigs.statuses)
    assert any(s.startswith("Track 1 done") for s in sigs.statuses)
    # cyanrip's raw "(ETA 3m)" is never surfaced verbatim.
    assert not any("(ETA" in s for s in sigs.statuses)


def test_album_eta_is_self_computed_from_elapsed(
    qapp: QApplication, tmp_path: Path
) -> None:
    """We compute our OWN album ETA from elapsed ÷ fraction — stable and
    self-correcting — instead of capturing cyanrip's per-op ETA (which once
    logged '822h' at 0.01%)."""
    worker = RipWorker(_FakeBackend(handle=_FakeHandle(lines=[])), _params(tmp_path))
    # Not started yet → no estimate.
    assert worker._album_eta_text(50.0) == ""
    # Pretend the rip started 100s ago and is 50% done → ~100s remain.
    worker._started_monotonic = time.monotonic() - 100.0
    text = worker._album_eta_text(50.0)
    assert "left" in text and ("1m" in text or "2m" in text)
    # Too early (disc-scan band ≤5%) → suppressed.
    assert worker._album_eta_text(3.0) == ""
    # cyanrip's obsolete first-ETA capture is gone.
    assert not hasattr(worker, "estimated_seconds")


def test_coarsen_eta_seconds_buckets() -> None:
    from platterpus.workers.rip_worker import _coarsen_eta_seconds

    assert _coarsen_eta_seconds(3998) == 3900  # ≥1h → nearest 5 min
    assert _coarsen_eta_seconds(1234) == 1260  # ≥10 min → nearest 1 min
    assert _coarsen_eta_seconds(137) == 150  # ≥2 min → nearest 30 s
    assert _coarsen_eta_seconds(43) == 40  # <2 min → nearest 10 s


def test_album_eta_is_smoothed(qapp: QApplication, tmp_path: Path) -> None:
    """The displayed ETA is an EMA, so a swing in the raw projection only nudges
    it — it doesn't jump the whole way (real-user 'smooth it out')."""
    worker = RipWorker(_FakeBackend(handle=_FakeHandle(lines=[])), _params(tmp_path))
    worker._started_monotonic = time.monotonic() - 100.0
    worker._album_eta_text(50.0)  # seeds the EMA at ~100s
    seeded = worker._smoothed_remaining_s
    assert seeded is not None
    # A pass that suddenly implies a much larger remaining shouldn't yank the
    # smoothed value all the way there.
    #
    # **THE STIMULUS CHANGED, NOT THE PROPERTY.** This used to jump 50% -> 10%, a
    # 40-POINT DROP. That is now classified as a pass RESTART (the auto-fix re-rip
    # is a second cyanrip invocation reporting progress from zero), which correctly
    # clears the estimate instead of blending two scales — so the old stimulus no
    # longer exercises smoothing at all. The sawtooth the EMA actually exists for is
    # FORWARD: the bar creeps a hair while time passes, so the projected remaining
    # balloons. That is what is fed here. The restart path has its own test
    # (`test_a_rerip_restarting_progress_resets_the_rate_estimate`), so both
    # behaviours are covered rather than one masking the other.
    worker._started_monotonic -= 800.0  # 900s elapsed at ~50% => raw ~900s
    worker._album_eta_text(50.001)
    assert worker._smoothed_remaining_s < 0.5 * (seeded + 900)


def test_eta_rebaselines_per_pass_not_whole_rip(
    qapp: QApplication, tmp_path: Path
) -> None:
    """Regression (#21): the overall-progress fraction resets to 0 at the start
    of every pass, so the album ETA must measure elapsed from THIS pass's start.
    Measuring from the whole-rip start on pass 2+ divided a large elapsed by a
    tiny fresh fraction and projected a wildly inflated 'time left'."""
    worker = RipWorker(_FakeBackend(handle=_FakeHandle(lines=[])), _params(tmp_path))
    now = time.monotonic()
    worker._started_monotonic = now - 1000.0  # pass 1 ran ~1000s

    # A new pass begins: the reset drops the stale smoothing and re-baselines.
    worker._smoothed_remaining_s = 9999.0
    worker._reset_pass_progress()
    assert worker._smoothed_remaining_s is None

    # 20s into pass 2, at 10% of THIS pass's bar.
    worker._eta_pass_started = now - 20.0
    text = worker._album_eta_text(10.0)

    # Per-pass: raw = 20 * 0.9/0.1 = 180s (~3 min). The whole-rip baseline would
    # have given 1000 * 0.9/0.1 = 9000s (2.5h) — the inflation this fixes.
    assert "left" in text
    assert worker._smoothed_remaining_s is not None
    assert worker._smoothed_remaining_s < 600  # minutes, not the ~9000s inflation


def test_album_eta_uses_recent_rate_not_scan_biased_average(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression (real hardware, 2026-07-02): the disc-scan phase (first ~5%) and
    the disc's inner tracks read ~10-15x faster than the bulk, so averaging the
    rate from zero made the EARLY ETA absurdly low — at 5% done / 14s in it said
    "~4m left" with 58m to go. The ETA now projects from a trailing-window rate,
    so it tracks reality once real ripping is under way instead of being dominated
    by the fast start."""
    import platterpus.workers.rip_worker as rw

    clock = {"t": 0.0}
    monkeypatch.setattr(rw.time, "monotonic", lambda: clock["t"])
    worker = RipWorker(_FakeBackend(handle=_FakeHandle(lines=[])), _params(tmp_path))
    worker._started_monotonic = 0.0
    worker._eta_pass_started = 0.0

    # A fast scan (0→5% in 10s) then a steady 1%-per-40s audio read.
    def frac_at(elapsed: float) -> float:
        if elapsed <= 10.0:
            return 0.05 * (elapsed / 10.0)
        return 0.05 + (elapsed - 10.0) * 0.00025

    for elapsed in range(10, 220, 10):
        clock["t"] = float(elapsed)
        worker._album_eta_text(frac_at(float(elapsed)) * 100.0)

    smoothed = worker._smoothed_remaining_s
    assert smoothed is not None
    # At elapsed=210s / 10% done, the read rate is 0.00025 frac/s, so ~3600s truly
    # remain (total ≈ 10s scan + 0.95/0.00025 = 3810s). The OLD from-zero average
    # would have projected 210*(0.9/0.1) = 1890s — roughly half of reality, the
    # scan-biased error this fixes. The windowed estimate must track the truth.
    assert 2800 < smoothed < 4400, smoothed
    assert smoothed > 2500  # decisively above the ~1890s scan-biased cumulative


def test_album_eta_reports_stall_when_progress_flatlines(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression (real hardware: the Roots track-18 read hung for HOURS while the
    on-screen ETA still counted down "~4h left"). When the album fraction stops
    clearing a meaningful forward step for the stall threshold — even if it crawls
    a hair — the ETA must say the drive is STALLED, not show a misleading
    countdown."""
    import platterpus.workers.rip_worker as rw

    clock = {"t": 0.0}
    monkeypatch.setattr(rw.time, "monotonic", lambda: clock["t"])
    worker = RipWorker(_FakeBackend(handle=_FakeHandle(lines=[])), _params(tmp_path))
    worker._started_monotonic = 0.0
    worker._eta_pass_started = 0.0

    # Establish real forward progress at 50%.
    clock["t"] = 10.0
    first = worker._album_eta_text(50.0)
    assert "left" in first and "stalled" not in first

    # Now the read only crawls — +0.001% per tick, never clearing the 0.5% step —
    # for longer than the stall threshold. The timer must NOT reset on the crawl.
    text = ""
    for i in range(1, 30):
        clock["t"] = 10.0 + i * 10.0
        text = worker._album_eta_text(50.0 + i * 0.001)
    assert "stalled" in text
    assert "left" not in text  # no misleading countdown while stuck


def test_album_eta_recovers_after_stall_clears(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Once the drive gets past the hard-to-read spot and the bar jumps forward
    again, the ETA returns to a normal estimate — the stall message is transient,
    not sticky."""
    import platterpus.workers.rip_worker as rw

    clock = {"t": 0.0}
    monkeypatch.setattr(rw.time, "monotonic", lambda: clock["t"])
    worker = RipWorker(_FakeBackend(handle=_FakeHandle(lines=[])), _params(tmp_path))
    worker._started_monotonic = 0.0
    worker._eta_pass_started = 0.0

    clock["t"] = 10.0
    worker._album_eta_text(50.0)
    clock["t"] = 10.0 + rw._ETA_STALL_THRESHOLD_S + 1.0
    assert "stalled" in worker._album_eta_text(50.02)  # stuck

    # Real progress resumes (bar jumps past the 0.5% step): back to a countdown.
    clock["t"] = clock["t"] + 30.0
    recovered = worker._album_eta_text(60.0)
    assert "stalled" not in recovered
    assert "left" in recovered


def test_slow_but_advancing_read_is_not_flagged_stalled(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A merely-slow drive that still makes real forward progress each tick must
    NEVER be mislabelled 'stalled' — only a genuine hang crosses the threshold.
    Guards against a false alarm scaring the user on a healthy (if slow) rip."""
    import platterpus.workers.rip_worker as rw

    clock = {"t": 0.0}
    monkeypatch.setattr(rw.time, "monotonic", lambda: clock["t"])
    worker = RipWorker(_FakeBackend(handle=_FakeHandle(lines=[])), _params(tmp_path))
    worker._started_monotonic = 0.0
    worker._eta_pass_started = 0.0

    # Advance 0.6% every 10s — clears the 0.5% step each tick — for well past the
    # stall threshold. Never a stall.
    text = ""
    for i in range(1, 40):
        clock["t"] = float(i * 10)
        text = worker._album_eta_text(min(99.0, 10.0 + i * 0.6))
    assert "stalled" not in text
    assert "left" in text


def test_stall_is_logged_once_on_entry_and_recovery_is_logged(
    qapp: QApplication,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A stall must be RECORDED (log.txt + the report's embedded debug log), not
    just shown on the transient status line — the maintainer's "show up in either
    the log or json file". It's logged exactly once on entry (a warning), and the
    recovery is logged too; it does not re-log on every stuck tick."""
    import logging

    import platterpus.workers.rip_worker as rw

    clock = {"t": 0.0}
    monkeypatch.setattr(rw.time, "monotonic", lambda: clock["t"])
    worker = RipWorker(_FakeBackend(handle=_FakeHandle(lines=[])), _params(tmp_path))
    worker._started_monotonic = 0.0
    worker._eta_pass_started = 0.0

    clock["t"] = 10.0
    worker._album_eta_text(50.0)

    with caplog.at_level(logging.INFO, logger="platterpus.workers.rip_worker"):
        # Several stuck ticks past the threshold — the warning must appear ONCE.
        for i in range(1, 20):
            clock["t"] = 10.0 + rw._ETA_STALL_THRESHOLD_S + i * 5.0
            worker._album_eta_text(50.0 + i * 0.001)
        stall_warnings = [
            r for r in caplog.records if "stalled" in r.getMessage().lower()
        ]
        assert len(stall_warnings) == 1
        assert stall_warnings[0].levelno == logging.WARNING

        # Real progress resumes → a recovery line is logged.
        clock["t"] = clock["t"] + 30.0
        worker._album_eta_text(60.0)
        assert any("recovered from stall" in r.getMessage() for r in caplog.records)


def _params_with_lengths(tmp_path: Path, lengths_ms: list[int | None]) -> RipParameters:
    """RipParameters carrying MB per-track durations (1-based) for the ETA weighting."""
    tracks = tuple(
        TrackTag(number=i, title=f"T{i}", length_ms=ln)
        for i, ln in enumerate(lengths_ms, start=1)
    )
    return _params(tmp_path, metadata=RipMetadata(tracks=tracks))


def test_overall_bar_is_duration_weighted_when_lengths_known(
    qapp: QApplication, tmp_path: Path
) -> None:
    """With per-track durations, a track's slice of the 5-95% read band is sized by
    its real length — a long track is a bigger slice — so the bar advances with
    audio position (and thus ~wall-clock), which is what stops the ETA oscillating.
    """
    # Tracks 1min / 2min / 1min (total 4min). Track 2 is half the disc.
    worker = RipWorker(
        _FakeBackend(handle=_FakeHandle(lines=[])),
        _params_with_lengths(tmp_path, [60_000, 120_000, 60_000]),
    )
    worker._total_tracks = 3

    # End of track 1 (task=100): duration-weighted = 5 + (60/240)*90 = 27.5,
    # NOT the equal-slice 5 + (1/3)*90 = 35.
    assert worker._overall_from_track(1, 100.0) == pytest.approx(27.5)
    # End of track 2: 5 + (180/240)*90 = 72.5 (equal-slice would be 65).
    assert worker._overall_from_track(2, 100.0) == pytest.approx(72.5)
    # End of the last track always reaches the full read band (95%).
    assert worker._overall_from_track(3, 100.0) == pytest.approx(95.0)
    # Mid track 2 (50%): 5 + (60 + 60)/240*90 = 50.0.
    assert worker._overall_from_track(2, 50.0) == pytest.approx(50.0)


def test_overall_bar_falls_back_to_equal_slices_without_lengths(
    qapp: QApplication, tmp_path: Path
) -> None:
    """No metadata (unknown disc) → equal-per-track slices, exactly today's
    behaviour. The weighting is a best-effort refinement, never a dependency."""
    worker = RipWorker(_FakeBackend(handle=_FakeHandle(lines=[])), _params(tmp_path))
    worker._total_tracks = 3
    assert worker._track_ms == {}  # nothing to weight with
    assert worker._overall_from_track(1, 100.0) == pytest.approx(35.0)  # 5 + 1/3*90
    assert worker._overall_from_track(2, 0.0) == pytest.approx(35.0)


def test_overall_bar_ignores_incomplete_lengths(
    qapp: QApplication, tmp_path: Path
) -> None:
    """If ANY track is missing a (positive) duration, the whole weighting is
    dropped — a partial weight would be worse than honest equal slices."""
    worker = RipWorker(
        _FakeBackend(handle=_FakeHandle(lines=[])),
        _params_with_lengths(tmp_path, [60_000, None, 60_000]),  # track 2 unknown
    )
    worker._total_tracks = 3
    assert worker._track_ms == {}  # refused to build a partial map
    assert worker._overall_from_track(1, 100.0) == pytest.approx(35.0)  # equal-slice


def test_eta_trace_records_both_estimates_speed_and_clock(
    qapp: QApplication, tmp_path: Path
) -> None:
    """The 'for posterity' trace samples pair the PC clock with BOTH estimates
    and the read speed in effect (raw material for a future ETA model)."""
    worker = RipWorker(_FakeBackend(handle=_FakeHandle(lines=[])), _params(tmp_path))
    worker._started_monotonic = time.monotonic() - 100.0
    worker._current_read_speed = 8
    worker._last_cyanrip_eta = "49m"

    worker._album_eta_text(50.0)

    trace = worker.eta_trace
    assert len(trace) == 1
    s = trace[0]
    assert s["read_speed"] == 8
    assert s["cyanrip_eta"] == "49m"
    assert isinstance(s["our_eta_seconds"], int) and s["our_eta_seconds"] > 0
    assert s["at"] and "T" in s["at"]  # an ISO wall-clock timestamp
    assert s["overall_percent"] == 50.0


def test_cyanrip_eta_stripped_from_forwarded_log(
    qapp: QApplication, tmp_path: Path
) -> None:
    """cyanrip's own 'ETA - …' is scrubbed from the forwarded log line so it
    can't contradict our smoothed album ETA in the status."""
    handle = _FakeHandle(
        lines=[
            "Disc tracks:    1",
            "Ripping and encoding track 1, progress - 50.00%, ETA - 49m",
        ],
        exit_code=0,
    )
    worker = RipWorker(_FakeBackend(handle=handle), _params(tmp_path))
    sigs = _Signals()
    sigs.attach(worker)

    worker.start_rip()

    progress_lines = [ln for ln in sigs.log_lines if "progress - 50.00%" in ln]
    assert progress_lines, "the progress line should be forwarded"
    assert all("ETA" not in ln for ln in progress_lines)  # cyanrip ETA stripped
    # …and cyanrip's ETA was still captured for the posterity trace.
    assert worker._last_cyanrip_eta == "49m"


def test_progress_redraws_are_rate_limited_in_the_log(
    qapp: QApplication, tmp_path: Path
) -> None:
    """A flood of cyanrip progress redraws must NOT each hit the log pane — that
    flood (one expensive text-append per redraw) starved repaints and blacked out
    the window when overlapped (real-user report, 2026-06-27). Processed in a
    tight loop (well under the 0.1s window), only the first redraw is logged;
    the bar signal stays unthrottled so progress still moves smoothly."""
    handle = _FakeHandle(
        lines=[
            "Ripping track 1, progress - 10.00%",
            "Ripping track 1, progress - 11.00%",
            "Ripping track 1, progress - 12.00%",
            "Ripping track 1, progress - 13.00%",
        ],
        exit_code=0,
    )
    worker = RipWorker(_FakeBackend(handle=handle), _params(tmp_path))
    sigs = _Signals()
    sigs.attach(worker)

    worker.start_rip()

    # Only the first redraw reaches the log pane (the rest are within 0.1s).
    assert len([line for line in sigs.log_lines if "progress" in line]) == 1
    # …but every redraw still moved the progress bar (cheap, unthrottled) —
    # all four task percentages, plus the final 100% emitted after the loop.
    assert [task for _, task in sigs.progress] == [10.0, 11.0, 12.0, 13.0, 100.0]


def test_non_progress_lines_are_never_throttled(
    qapp: QApplication, tmp_path: Path
) -> None:
    """The rate limit applies ONLY to progress redraws — ordinary log lines
    (errors, phase markers) must always reach the pane, even back-to-back."""
    handle = _FakeHandle(lines=["one", "two", "three", "four"], exit_code=0)
    worker = RipWorker(_FakeBackend(handle=handle), _params(tmp_path))
    sigs = _Signals()
    sigs.attach(worker)

    worker.start_rip()

    assert _ripper_lines(sigs.log_lines) == ["one", "two", "three", "four"]


def test_cyanrip_progress_without_disc_total_keeps_task_bar_moving(
    qapp: QApplication, tmp_path: Path
) -> None:
    """If the 'Disc tracks:' line was missed, the overall bar can't be
    computed — but the task bar must still track the percentage."""
    handle = _FakeHandle(
        lines=["Ripping track 3, progress - 50.00%"],
        exit_code=0,
    )
    worker = RipWorker(_FakeBackend(handle=handle), _params(tmp_path))
    sigs = _Signals()
    sigs.attach(worker)

    worker.start_rip()

    overall, task = sigs.progress[0]
    assert task == 50.0
    assert overall == 5.0  # banded floor, no regression to 0


def test_metadata_param_forwarded_to_backend(
    qapp: QApplication, tmp_path: Path
) -> None:
    """RipParameters.metadata (the GUI's tag snapshot) must reach the
    backend so cyanrip can be fed -a/-t."""
    from platterpus.adapters.rip_backend import RipMetadata, TrackTag

    meta = RipMetadata(album_title="X", tracks=(TrackTag(1, "One", "A"),))
    handle = _FakeHandle(lines=[], exit_code=0)
    backend = _FakeBackend(handle=handle)
    worker = RipWorker(backend, _params(tmp_path, metadata=meta))

    worker.start_rip()

    assert backend.rip_calls[0]["metadata"] == meta


def test_finished_reports_failure_on_nonzero_exit(
    qapp: QApplication, tmp_path: Path
) -> None:
    handle = _FakeHandle(lines=[], exit_code=1)
    worker = RipWorker(_FakeBackend(handle=handle), _params(tmp_path))
    sigs = _Signals()
    sigs.attach(worker)

    worker.start_rip()

    assert sigs.finished[0][0] is False


def test_needs_unknown_retry_set_on_no_metadata_abort(
    qapp: QApplication, tmp_path: Path
) -> None:
    """A known rip that aborts for lack of online metadata flags a heal."""
    handle = _FakeHandle(
        lines=[
            "Reading TOC 100 %",
            "WARNING: network error: (NetworkError(),)",
            "CRITICAL: unable to retrieve disc metadata, --unknown argument not passed",
        ],
        exit_code=1,
    )
    worker = RipWorker(_FakeBackend(handle=handle), _params(tmp_path, unknown=False))
    worker.start_rip()
    assert worker.needs_unknown_retry is True


def test_no_unknown_retry_when_already_unknown(
    qapp: QApplication, tmp_path: Path
) -> None:
    """An already-unknown rip never asks to heal (nothing better to retry)."""
    handle = _FakeHandle(
        lines=["CRITICAL: unable to retrieve disc metadata, --unknown ..."],
        exit_code=1,
    )
    worker = RipWorker(_FakeBackend(handle=handle), _params(tmp_path, unknown=True))
    worker.start_rip()
    assert worker.needs_unknown_retry is False


def test_no_unknown_retry_on_clean_rip(qapp: QApplication, tmp_path: Path) -> None:
    handle = _FakeHandle(lines=["Reading TOC 100 %"], exit_code=0)
    worker = RipWorker(_FakeBackend(handle=handle), _params(tmp_path))
    worker.start_rip()
    assert worker.needs_unknown_retry is False


def test_failure_hint_set_on_track_giveup(qapp: QApplication, tmp_path: Path) -> None:
    """An unreadable track yields an actionable hint, not a bare failure."""
    handle = _FakeHandle(
        lines=["CRITICAL:whipper.command.cd:giving up on track 3 after 5 times"],
        exit_code=1,
    )
    worker = RipWorker(_FakeBackend(handle=handle), _params(tmp_path))
    worker.start_rip()
    assert "Track 3" in worker.failure_hint
    # Actionable, backend-neutral advice (no stale "Keep going" setting, which
    # was removed with whipper, and no false >587 cd-paranoia claim).
    assert "scratched or dirty" in worker.failure_hint


def test_a_giveup_line_does_not_overwrite_the_rippers_own_fatal(
    qapp: QApplication, tmp_path: Path
) -> None:
    """The branch above this one is commented "first error wins" — and this branch
    assigned unconditionally, so a verbatim cyanrip fatal matched ONE LINE EARLIER
    was replaced by canned "clean the disc" advice. The comment described a rule the
    code did not implement here. The tool's own sentence now leads and the advice
    follows, so neither is lost.
    """
    handle = _FakeHandle(
        lines=[
            # A REAL cyanrip format string, taken from the generated inventory —
            # not one I invented, which would test the fixture rather than the matcher.
            "Unable to read track 3 subchannel info!",
            "CRITICAL:whipper.command.cd:giving up on track 3 after 5 times",
        ],
        exit_code=1,
    )
    worker = RipWorker(_FakeBackend(handle=handle), _params(tmp_path))
    worker.start_rip()

    hint = worker.failure_hint
    # The ripper's own words, first.
    assert hint.startswith("Unable to read track 3 subchannel info!")
    # And the actionable advice is still there, appended rather than substituted.
    assert "scratched or dirty" in hint


def test_no_failure_hint_on_clean_rip(qapp: QApplication, tmp_path: Path) -> None:
    handle = _FakeHandle(lines=["Reading TOC 100 %"], exit_code=0)
    worker = RipWorker(_FakeBackend(handle=handle), _params(tmp_path))
    worker.start_rip()
    assert worker.failure_hint == ""


# --- Progress parsing -----------------------------------------------------


def test_progress_two_tier_overall_monotonic_and_task_resets(
    qapp: QApplication, tmp_path: Path
) -> None:
    """Overall bar moves forward across the whole rip; the task bar
    tracks the current operation and resets per phase (T32 feedback:
    "bar goes by track; want an overall bar and a task bar")."""
    handle = _FakeHandle(
        lines=[
            "Reading TOC  50 %",  # scan → 0-5% band
            "Reading table  100 %",
            "Reading track 1 of 2 (1 of 9) ...  50 %",  # track → 5-95% band
            "Verifying track 1 of 2 (3 of 9) ... 100 %",
            "Reading track 2 of 2 (1 of 9) ...  50 %",
            "Getting length of audio track (2 of 2) ... 100 %",  # 95-100%
        ],
        exit_code=0,
    )
    worker = RipWorker(_FakeBackend(handle=handle), _params(tmp_path))
    sigs = _Signals()
    sigs.attach(worker)

    worker.start_rip()

    overalls = [o for o, _ in sigs.progress]
    tasks = [t for _, t in sigs.progress]
    # Overall is monotonic non-decreasing and ends at 100 (success peg).
    assert overalls == sorted(overalls)
    assert overalls[-1] == 100.0
    # Disc scan occupied the low band before any track work.
    assert sigs.progress[0] == (2.5, 50.0)
    assert sigs.progress[1] == (5.0, 100.0)
    # The task bar reset back down when a new operation started.
    assert 50.0 in tasks and 100.0 in tasks


def test_emits_current_track_once_per_new_track(
    qapp: QApplication, tmp_path: Path
) -> None:
    """current_track fires once when whipper moves to a new track — not on
    every per-percent line for the same track — so the GUI can follow the
    rip by highlighting the active row."""
    handle = _FakeHandle(
        lines=[
            "Reading TOC  100 %",  # no track yet
            "Reading track 1 of 3 (1 of 9) ...  10 %",  # → track 1
            "Reading track 1 of 3 (1 of 9) ...  90 %",  # same track, no re-emit
            "Verifying track 1 of 3 (3 of 9) ... 100 %",  # still track 1
            "Reading track 2 of 3 (1 of 9) ...  50 %",  # → track 2
            "Reading track 3 of 3 (1 of 9) ...  50 %",  # → track 3
        ],
        exit_code=0,
    )
    worker = RipWorker(_FakeBackend(handle=handle), _params(tmp_path))
    sigs = _Signals()
    sigs.attach(worker)

    worker.start_rip()

    # One emission per distinct track, in order; no duplicate for track 1.
    assert sigs.current_tracks == [1, 2, 3]


def test_progress_for_ignores_lines_without_usable_percent(
    qapp: QApplication, tmp_path: Path
) -> None:
    worker = RipWorker(_FakeBackend(handle=_FakeHandle([], 0)), _params(tmp_path))
    # Encode/tag sub-phases carry no meaningful percent → no progress emit
    # (the status label covers them; the task bar holds its last value).
    assert worker._progress_for("Encoding track to FLAC (5 of 9) ...   0 %") is None
    assert worker._progress_for("INFO:whipper.command.cd:CRCs match") is None
    assert worker._progress_for("") is None


# --- Status / phase descriptions ------------------------------------------


def test_describe_activity_recognizes_disc_scan() -> None:
    assert _describe_activity("Reading TOC  50 %") == "Reading disc TOC… 50%"
    assert _describe_activity("Reading table  12 %") == "Reading disc table… 12%"


def test_describe_activity_recognizes_track_phases() -> None:
    assert (
        _describe_activity("Reading track 3 of 16 (1 of 9) ...  42 %")
        == "Reading track 3 of 16… 42%"
    )
    assert (
        _describe_activity("Verifying track 3 of 16 (3 of 9) ... 100 %")
        == "Verifying track 3 of 16… 100%"
    )


def test_describe_activity_recognizes_named_subphases() -> None:
    assert (
        _describe_activity("Encoding track to FLAC (5 of 9) ...   0 %")
        == "Encoding to FLAC…"
    )
    assert (
        _describe_activity("Getting length of audio track (1 of 16) ... 100 %")
        == "Checking track 1 of 16…"
    )


def test_describe_activity_cyanrip_shows_track_x_of_y_when_total_known() -> None:
    # When the worker knows the disc's track count it renders "of M" so the user
    # sees position at a glance ("track 12 of 17"). Real cyanrip progress line.
    line = "Ripping and encoding track 12, progress - 42.37%, ETA - 3m, errors - 0"
    assert _describe_activity(line, 17) == "Ripping track 12 of 17… 42%"


def test_describe_activity_cyanrip_omits_total_when_unknown() -> None:
    # With no known total (0 — e.g. before the disc banner on an unknown disc) we
    # omit "of M" rather than show a wrong count. Default keeps old callers happy.
    line = "Ripping track 3, progress - 7.00%"
    assert _describe_activity(line, 0) == "Ripping track 3… 7%"
    assert _describe_activity(line) == "Ripping track 3… 7%"


def test_describe_activity_returns_none_for_unrelated_lines() -> None:
    assert _describe_activity("INFO:whipper.command.cd:CRCs match") is None
    assert _describe_activity("") is None


def test_status_signal_fires_for_disc_scan_phase(
    qapp: QApplication, tmp_path: Path
) -> None:
    """The pre-track disc scan must drive the status so the GUI doesn't
    look frozen on "Starting rip…" (T32 feedback)."""
    statuses: list[str] = []
    handle = _FakeHandle(
        lines=[
            "Reading TOC  50 %",
            "Reading table  10 %",
            "Reading track 1 of 16 (1 of 9) ...  20 %",
        ],
        exit_code=0,
    )
    worker = RipWorker(_FakeBackend(handle=handle), _params(tmp_path))
    worker.status.connect(statuses.append)

    worker.start_rip()

    assert "Reading disc TOC… 50%" in statuses
    assert "Reading disc table… 10%" in statuses
    assert "Reading track 1 of 16… 20%" in statuses


def test_status_signal_deduplicates_repeated_phase(
    qapp: QApplication, tmp_path: Path
) -> None:
    handle = _FakeHandle(
        lines=["Encoding track to FLAC (5 of 9) ...   0 %"] * 3,
        exit_code=0,
    )
    worker = RipWorker(_FakeBackend(handle=handle), _params(tmp_path))
    statuses: list[str] = []
    worker.status.connect(statuses.append)

    worker.start_rip()

    assert statuses == ["Encoding to FLAC…"]


# --- Error paths ----------------------------------------------------------


def test_whipper_error_on_start_emits_error_and_finished_false(
    qapp: QApplication, tmp_path: Path
) -> None:
    backend = _FakeBackend()
    backend.raise_on_rip(RipError("device busy"))
    worker = RipWorker(backend, _params(tmp_path))
    sigs = _Signals()
    sigs.attach(worker)

    worker.start_rip()

    assert sigs.errors == ["device busy"]
    assert sigs.finished == [(False, "")]


def test_unexpected_exception_on_start_emits_error(
    qapp: QApplication, tmp_path: Path
) -> None:
    backend = _FakeBackend()
    backend.raise_on_rip(RuntimeError("kaboom"))
    worker = RipWorker(backend, _params(tmp_path))
    sigs = _Signals()
    sigs.attach(worker)

    worker.start_rip()

    assert len(sigs.errors) == 1
    assert "kaboom" in sigs.errors[0]
    assert sigs.finished == [(False, "")]


# --- Cancellation ---------------------------------------------------------


def test_cancel_before_start_stops_the_subprocess_once_it_exists(
    qapp: QApplication, tmp_path: Path
) -> None:
    """A cancel that lands during rip() startup — before the handle is set —
    must still stop the subprocess. cancel() can only flip the flag then (it
    finds _handle is None); start_rip re-checks the flag after it has the
    handle and cancels it. Regression for the startup-window race where the
    flag was set but the subprocess kept running and wait() blocked on it."""
    handle = _FakeHandle(lines=["one", "two"], exit_code=-15)
    backend = _FakeBackend(handle=handle)
    worker = RipWorker(backend, _params(tmp_path))

    # Cancel before start: the handle isn't set yet, so only the flag is set.
    worker.cancel()
    assert handle.terminate_calls == 0

    worker.start_rip()  # gets the handle, sees the flag, and stops the rip

    # The subprocess was terminated (non-blocking SIGTERM), not the blocking
    # cancel() — a GUI-thread cancel must never wait.
    #
    # `>= 1`, not `== 1`: `_reap_ripper` re-sends SIGTERM before waiting, so a
    # cancelled rip now terminates twice (the startup-window re-check, then the
    # reap). That is deliberate — SIGTERM is idempotent and free, and it makes the
    # reap correct on its own rather than only when the caller remembered to
    # terminate first. The exact count was never what this test was about; the two
    # claims that matter are "it *was* stopped" and "no blocking call on this path".
    assert handle.terminate_calls >= 1
    assert handle.cancel_calls == 0, (
        "the blocking cancel() ran on a path that must stay non-blocking — it is "
        "only reached when a bounded wait has already timed out."
    )


def test_cancel_after_start_forwards_to_handle(
    qapp: QApplication, tmp_path: Path
) -> None:
    """The normal path: with the handle set, cancel() forwards to it."""
    handle = _FakeHandle(lines=["one", "two"], exit_code=0)
    backend = _FakeBackend(handle=handle)
    worker = RipWorker(backend, _params(tmp_path))

    worker.start_rip()  # no cancel → completes; the startup re-check is a no-op
    assert handle.terminate_calls == 0

    worker.cancel()  # handle exists now → forwarded (non-blocking terminate)
    assert handle.terminate_calls == 1
    assert handle.cancel_calls == 0


def test_a_ripper_that_will_not_exit_is_reaped_instead_of_waited_on_forever(
    qapp: QApplication, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Regression: the rip worker used to end with a bare `self._handle.wait()`.

    The read loop does not always run to EOF — on cancel it `break`s — so the
    ripper's stdout pipe stops being drained while the ripper may still be writing.
    A pipe holds ~64 KiB; once full the child blocks in `write()`, never exits, and
    an unbounded `wait()` never returns. It waits on the rip worker's own thread,
    so that thread never finishes and gets abandoned at shutdown.

    `never_exits=True` is the fake being honest about that: it raises if asked to
    wait with no timeout at all, and otherwise times out the way the real call
    would. The worker must bound the wait and then escalate.
    """
    handle = _FakeHandle(lines=["one", "two"], exit_code=0, never_exits=True)
    backend = _FakeBackend(handle=handle)
    worker = RipWorker(backend, _params(tmp_path))

    with caplog.at_level("WARNING"):
        worker.start_rip()  # must return, not hang

    # Bounded: a real timeout was passed, not None.
    assert handle.wait_timeouts, "wait() was never called"
    assert all(t is not None for t in handle.wait_timeouts), (
        f"wait() was called with no timeout: {handle.wait_timeouts}. That is the "
        "deadlock — an undrained pipe means the child never exits."
    )
    # Escalated to the SIGTERM→SIGKILL group kill, which is what actually ends the
    # writer and so what actually breaks the deadlock.
    assert handle.cancel_calls == 1, (
        "the wait timed out but RipHandle.cancel() was not called, so nothing "
        "escalated — the ripper keeps holding the drive."
    )
    # And it said so, loudly enough to appear in a bug report.
    assert any("escalating to SIGTERM/SIGKILL" in r.message for r in caplog.records), (
        f"no diagnostic logged; records were {[r.message for r in caplog.records]}"
    )


def test_a_ripper_that_survives_sigkill_is_reported_not_hung(
    qapp: QApplication, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """The new state the fix creates: `cancel()` can now return None.

    A reader wedged in a drive ioctl sits in uninterruptible sleep where not even
    SIGKILL lands, so the escalation itself can fail to reap. That must be a logged,
    unsuccessful rip — never a hang, and never a silent success.
    """
    handle = _FakeHandle(
        lines=["one"], exit_code=0, never_exits=True, cancel_returns=None
    )
    backend = _FakeBackend(handle=handle)
    worker = RipWorker(backend, _params(tmp_path))
    sigs = _Signals()
    sigs.attach(worker)

    with caplog.at_level("ERROR"):
        worker.start_rip()

    assert handle.cancel_calls == 1
    assert sigs.finished, "the worker never reported a result"
    assert sigs.finished[-1][0] is False, (
        "an unreapable ripper was reported as a SUCCESSFUL rip — exit code None "
        "must never compare equal to 0."
    )
    assert any("even after SIGKILL" in r.message for r in caplog.records)


def test_cancellation_makes_finished_report_false(
    qapp: QApplication, tmp_path: Path
) -> None:
    """When the cancel flag is set during iteration, success must be
    False even if the subprocess exits with 0."""
    handle = _FakeHandle(lines=["x"], exit_code=0)
    backend = _FakeBackend(handle=handle)
    worker = RipWorker(backend, _params(tmp_path))
    sigs = _Signals()
    sigs.attach(worker)

    # Pre-cancel so the loop's first iteration sees the flag.
    worker.cancel()
    worker.start_rip()

    assert sigs.finished[0][0] is False


# --- Log path discovery ---------------------------------------------------


def test_finished_includes_log_path_when_log_present(
    qapp: QApplication, tmp_path: Path
) -> None:
    rip_log = tmp_path / "Artist" / "Album" / "rip.log"
    rip_log.parent.mkdir(parents=True)
    rip_log.write_text("dummy log content")

    handle = _FakeHandle(lines=[], exit_code=0)
    worker = RipWorker(_FakeBackend(handle=handle), _params(tmp_path))
    sigs = _Signals()
    sigs.attach(worker)

    worker.start_rip()

    success, path = sigs.finished[0]
    assert success is True
    assert path == str(rip_log)


def test_finished_log_path_empty_when_no_log_file(
    qapp: QApplication, tmp_path: Path
) -> None:
    handle = _FakeHandle(lines=[], exit_code=0)
    worker = RipWorker(_FakeBackend(handle=handle), _params(tmp_path))
    sigs = _Signals()
    sigs.attach(worker)

    worker.start_rip()

    _, path = sigs.finished[0]
    assert path == ""


def test_find_log_path_skips_a_candidate_that_vanishes_mid_scan(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """BUG-2: a `.log` that disappears between the rglob and its stat is skipped,
    not a fatal FileNotFoundError escaping into start_rip (which would leave
    `finished` un-emitted and the GUI's rip lock stuck)."""
    worker = RipWorker(_FakeBackend(), _params(tmp_path))
    good = tmp_path / "good.log"
    good.write_text("x", encoding="utf-8")
    (tmp_path / "bad.log").write_text("x", encoding="utf-8")
    real_stat = Path.stat

    def flaky_stat(self: Path, *a: object, **k: object):  # noqa: ANN202
        if self.name == "bad.log":
            raise FileNotFoundError("vanished mid-scan")
        return real_stat(self, *a, **k)

    monkeypatch.setattr(Path, "stat", flaky_stat)
    # No raise, and the surviving candidate is returned.
    assert worker._find_log_path(tmp_path) == good


def test_start_rip_belt_emits_finished_on_unexpected_error(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """BUG-2: any unexpected error in the rip body still emits finished(False,
    "") — a rip that never emits finished leaves the GUI rip lock on forever."""
    worker = RipWorker(
        _FakeBackend(handle=_FakeHandle(lines=[], exit_code=0)), _params(tmp_path)
    )
    finished: list[tuple[bool, str]] = []
    worker.finished.connect(lambda ok, path: finished.append((ok, path)))

    def boom() -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(worker, "_run_rip", boom)
    worker.start_rip()
    assert finished == [(False, "")]


# --- Incremental report snapshot (crash/kill durability) ------------------

_INCREMENTAL_LOG = """\
cyanrip 0.9.3 (release)
Device model:   PIONEER  BD-RW   BDR-209D 1.51 SCSI CD-ROM
Offset:         +667 samples
Disc tracks:    2
Album:          Test Album

Track 1 ripped and encoded successfully!
  Duration:    03:51.44
  EAC CRC32:     A1B2C3D4
  Accurip:       found in database (max confidence: 3)
    Accurip v1:  12345678 (accurately ripped, confidence 3)
  File(s):
    Test Album/01 - One.flac
"""


def test_incremental_report_snapshot_written_on_track_completion(
    qapp: QApplication, tmp_path: Path
) -> None:
    """A PARTIAL .platterpus.json is written beside the growing cyanrip .log as
    each track completes, so a hard stop (SIGKILL/power-loss) that never reaches
    the GUI finish handler still leaves the tracks-so-far on disk. Its outcome is
    'in_progress' (the GUI overwrites with the real status at finish)."""
    import json

    album = tmp_path / "Test Album"
    album.mkdir()
    log_file = album / "Test Album.log"

    def side_effect(_call: dict) -> None:
        # cyanrip writes its .log incrementally; emulate the log existing with
        # track 1's summary by the time track 1's "done" line streams.
        log_file.write_text(_INCREMENTAL_LOG, encoding="utf-8")

    handle = _FakeHandle(
        lines=[
            "Ripping and encoding track 1, progress - 99.00%",
            "Track 1 ripped and encoded successfully!",
        ],
        exit_code=0,
    )
    backend = _FakeBackend(handle=handle)
    backend.rip_side_effect = side_effect
    worker = RipWorker(backend, _params(tmp_path))

    worker.start_rip()

    report = album / "Test Album.platterpus.json"
    assert report.is_file(), "a partial report must exist once a track completes"
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["outcome"]["status"] == "in_progress"
    assert len(data["tracks"]) >= 1


def test_incremental_report_snapshot_skipped_before_any_log(
    qapp: QApplication, tmp_path: Path
) -> None:
    """No .log yet (cyanrip hasn't written one) → the snapshot is a silent no-op,
    never a crash. The auto-fix temp rip (output_dir set) also never snapshots."""
    handle = _FakeHandle(
        lines=["Track 1 ripped and encoded successfully!"], exit_code=0
    )
    worker = RipWorker(_FakeBackend(handle=handle), _params(tmp_path))
    # No side_effect → no .log is ever written; must not raise, no report appears.
    worker.start_rip()
    assert not list(tmp_path.rglob("*.platterpus.json"))


# --- the rip-aborting never-raises hole (audit, 2026-07-31) ------------------


def test_a_corrupt_progress_line_never_raises_and_never_ends_the_rip(
    qapp: QApplication, tmp_path: Path
) -> None:
    """The worst instance of the 4300-digit `int()` hole, because of WHERE it was.

    v0.5.19 closed this class in eight parsers, where a raise degrades a field to
    "unknown". It missed `_progress_for`, where the consequence is different in
    kind: it is called from the stdout read loop, inside a `try` whose handler
    terminates the child and emits an error. **One corrupt line ended the rip.**

    It was invisible to the new structural sweep for one reason — that sweep's
    module roster is hand-maintained and nobody had added this file.

    Every shape below made the real `_progress_for` raise before the fix:
    `ValueError` from `int()` on the track/total/percent groups, and — the quieter
    one — `float()` returning `inf` rather than raising, which then blew up as
    `OverflowError` inside `int()` on the GUI thread.

    Built with the real constructor, not `__new__`: `_progress_for` reads
    attributes (`_track_ms_total` among them) that only `__init__` sets, so a
    hand-populated stand-in would have been a *different* object testing a
    *different* method — and it duly failed on an attribute the bug never touched
    (`docs/testing.md` §5.t — "what does my stand-in do that the real thing does
    not?").
    """
    worker = RipWorker(_FakeBackend(handle=_FakeHandle([], 0)), _params(tmp_path))

    huge = "9" * 5000
    lines = [
        f"Ripping and encoding track {huge}, progress - 42.37%",
        f"Ripping and encoding track 3, progress - {huge}%",
        f"Disc tracks:    {huge}",
        f"Track {huge} ripped and encoded successfully!",
        f"Reading track {huge} of 14 ... 50 %",
        f"Reading track 1 of {huge} ... 50 %",
        f"Reading TOC {huge} %",
        f"Getting length of audio track ({huge} of 14)",
    ]
    for line in lines:
        # The contract is "never raises". Any return value is acceptable.
        result = worker._progress_for(line)
        assert result is None or isinstance(result, tuple), line


def test_a_progress_bar_never_receives_a_value_it_cannot_display() -> None:
    """The second half, on the GUI thread.

    `float()` does not raise on a long digit run — it returns `inf`. That reached
    `set_progress`, where `int(inf)` raises `OverflowError` inside a queued slot,
    producing a crash dialog over a progress bar. `nan` did the same with
    `ValueError`.
    """
    from platterpus.ui.rip_progress import _bar_value

    assert _bar_value(float("inf")) == 0
    assert _bar_value(float("-inf")) == 0
    assert _bar_value(float("nan")) == 0
    # And it still does its ordinary job, so the guard is not a mute button.
    assert _bar_value(0.0) == 0
    assert _bar_value(42.7) == 42
    assert _bar_value(100.0) == 100
    assert _bar_value(-5.0) == 0, "clamped, not negative"
    assert _bar_value(150.0) == 100, "clamped, not out of range"


# --- the log is read only AFTER the child has exited ---------------------------
# cyanrip's logfile and cue were block-buffered, so a process killed mid-rip lost
# up to a 4096-byte stdio block — the round-1 finding, reproduced against a real
# cancelled rip whose log ended mid-token at `REPLAYGAIN_TRACK_GA`. The fork's
# `setvbuf` removed the buffering at the source (round 2), and our half of the
# invariant is ordering: never look for the log until the child is reaped.
#
# Structurally that is one code path today (`_reap_ripper()` then
# `_find_log_path()`), and a refactor could invert it with nothing complaining.
# So this is a BEHAVIOURAL test rather than a source-shape one: the fake writes
# the log from inside `wait()`, so a read that happened first would find nothing.


class _WritesLogOnWait:
    """A ripper whose log only exists once it has been waited on.

    Stands in for the real thing more faithfully than a handle that pre-writes
    the file: cyanrip flushes its logfile as it exits, so *before* the wait there
    is either no log or a truncated one. A fake that has the log ready from the
    start cannot exhibit the bug, which is the harness-fidelity rule — a stand-in
    must not be safer than the product.
    """

    def __init__(self, album: Path, text: str) -> None:
        self.argv: tuple[str, ...] = ("cyanrip", "-d", "/dev/sr0")
        self._album: Path = album
        self._text: str = text
        self.waited: bool = False

    def log_lines(self) -> Iterable[str]:
        yield "ripping"

    def wait(self, timeout: float | None = None) -> int:
        self.waited = True
        self._album.mkdir(parents=True, exist_ok=True)
        (self._album / "rip.log").write_text(self._text, encoding="utf-8")
        return 0

    def cancel(self, term_timeout: float = 5.0) -> int:
        return 0


def test_the_rip_log_is_not_read_before_the_child_is_reaped(
    qapp: QApplication, tmp_path: Path
) -> None:
    """Reap, then read. Inverting the two loses whatever was still buffered."""
    album = tmp_path / "Artist" / "Album"
    text = (
        "cyanrip 0.9.4-rc1 (platterpus-fork-g2f950c8)\n"
        "Invoked as: cyanrip -d /dev/sr0\n"
        "Disc tracks:    1\n"
        "Track 1 ripped and encoded successfully!\n"
        "  EAC CRC32:     DEADBEEF\n"
        "  File(s):\n"
        "    Artist/Album/01 - A.flac\n"
        "Ripping errors: 0\n"
    )
    handle = _WritesLogOnWait(album, text)
    backend = _FakeBackend(handle=handle)  # type: ignore[arg-type]
    worker = RipWorker(backend, _params(tmp_path))

    finished: list[tuple[bool, str]] = []
    worker.finished.connect(lambda ok, path: finished.append((ok, path)))
    worker.start_rip()

    assert handle.waited, "the worker never waited on the child at all"
    assert finished, "the worker never emitted finished"
    ok, log_path = finished[-1]
    assert ok, "a clean rip must report success"
    # THE assertion: the log the worker found is the one `wait()` wrote. Had the
    # search run before the reap, there would have been no file to find and this
    # would be empty — which is the data loss, reported as "no log".
    assert log_path, (
        "the worker found no rip log, which is what happens when the search runs "
        "before the child has flushed and exited"
    )
    assert Path(log_path).read_text(encoding="utf-8") == text


# --- the ETA must never print 62 hours -------------------------------------------
#
# MEASURED ON REAL HARDWARE, from the rip's own `eta_trace` (2026-08-05, the Police
# baseline disc on b6 + cyanrip f5e11ba). During track 5's auto-fix re-rip the album
# ETA climbed across eight consecutive samples:
#
#     51m -> 59m -> 70m -> 85m -> 115m -> 175m -> 335m -> 3715m   then snapped to 11m
#
# 3715 minutes is 62 HOURS, on a 60-minute disc, with ~6 minutes of work left. The
# maintainer reported it as "track 5 went from hours to minutes and such".
#
# CAUSE: `raw_remaining = (1 - frac) * window_dt / window_dfrac`, guarded only by
# `window_dfrac > 0`. The re-rip is a SECOND cyanrip invocation, so `overall_percent`
# first went BACKWARDS (94.79 -> 29.35) and then FROZE at 35.45 while work continued.
# A frozen bar still wobbles by a rounding step, and 0.01 percentage points is
# greater than zero, so an hour of remaining work got divided by noise.


class _Clock:
    """A controllable monotonic clock.

    The real trace samples every ~10 seconds. Calling `_album_eta_text` in a tight
    loop instead makes the window's `dt` a few microseconds, so the measured rate
    looks near-infinite and a pre-existing guard returns "" — an artifact of the
    test, not the product. Driving time explicitly is what makes these tests
    reproduce the field behaviour rather than a harness quirk.
    """

    def __init__(self, start: float = 10_000.0) -> None:
        self.now: float = start

    def __call__(self) -> float:
        return self.now

    def tick(self, seconds: float) -> None:
        self.now += seconds


def _eta_worker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[RipWorker, _Clock]:
    """A worker whose ETA clock we drive, with 10 minutes already elapsed."""
    clock = _Clock()
    monkeypatch.setattr(rip_worker_module.time, "monotonic", clock)
    worker = RipWorker(
        _FakeBackend(handle=_FakeHandle(lines=[], exit_code=0)), _params(tmp_path)
    )
    worker._started_monotonic = clock.now - 600.0
    worker._eta_pass_started = worker._started_monotonic
    return worker, clock


def _feed(worker: RipWorker, clock: _Clock, percents: list[float]) -> list[str]:
    """Feed album percentages 10 seconds apart, as the real sampler does."""
    out: list[str] = []
    for pct in percents:
        clock.tick(10.0)
        out.append(worker._album_eta_text(pct))
    return out


def test_a_frozen_progress_bar_never_produces_an_absurd_eta(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The regression. A bar that stops advancing must not divide by its own noise."""
    worker, clock = _eta_worker(tmp_path, monkeypatch)
    # Establish a believable estimate from real forward movement...
    _feed(worker, clock, [20.0, 22.0, 24.0, 26.0, 28.0, 30.0, 33.0, 35.44])
    assert worker._smoothed_remaining_s is not None, (
        "no baseline estimate was established — the test proves nothing"
    )
    # ...then freeze the bar, wobbling by a rounding step exactly as the measured
    # trace did (35.44 -> 35.45 -> 35.44 …). THIS produced 3715 minutes.
    shown = _feed(worker, clock, [35.45, 35.44] * 20)
    worst = worker._smoothed_remaining_s or 0.0
    assert worst < 24 * 60 * 60, (
        f"the estimate reached {worst / 3600:.1f} hours on a frozen bar — the "
        "divide-by-noise bug is back"
    )
    # Precise, not a substring: the first version tested `"d " not in text`, which
    # matches "har**d-**to-read spot" in the stall message. A check that fires on the
    # wrong thing is the failure CLAUDE.md warns about, arriving in the test itself.
    for text in shown:
        for hours in re.findall(r"(\d+)h", text):
            assert int(hours) < 24, f"an ETA of {hours}h was displayed: {text!r}"


def test_the_estimate_is_held_not_reinvented_while_the_bar_is_frozen(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A frozen bar means "rate unmeasurable", so the last estimate stands.

    **THE STALL DETECTOR IS DISABLED HERE ON PURPOSE.** The first version of this
    test passed with the fix reverted, which makes it worthless as written: after
    `_ETA_STALL_THRESHOLD_S` (180 s) without >=0.5% progress, the pre-existing stall
    detector returns "stalled …" *before* any projection runs, so the estimate stops
    moving whatever the arithmetic below it does. The test was measuring a different
    mechanism than its name claims.

    Raising the threshold out of the way is what makes this test about the hold
    path. It also matters for the real bug: the field freeze lasted ~160 s, i.e.
    **under** the stall threshold, so the explosion lived in exactly the window the
    stall detector does not cover.
    """
    monkeypatch.setattr(rip_worker_module, "_ETA_STALL_THRESHOLD_S", 1e9)
    worker, clock = _eta_worker(tmp_path, monkeypatch)
    _feed(worker, clock, [20.0, 24.0, 28.0, 32.0, 35.0])
    before = worker._smoothed_remaining_s
    assert before is not None
    # Freeze for LONGER THAN THE RATE WINDOW (90s) before expecting a hold. For the
    # first 90s of a freeze the window still contains real forward movement, so a
    # growing estimate is correct there — the rate genuinely is falling. Holding is
    # for when the window is entirely frozen and there is no rate left to measure.
    _feed(worker, clock, [35.0] * 12)  # 120s > _ETA_RATE_WINDOW_S
    settled = worker._smoothed_remaining_s
    assert settled is not None
    held = _feed(worker, clock, [35.0, 35.0])
    assert worker._smoothed_remaining_s == settled, (
        "the smoothed estimate moved on a fully-frozen window — recomputed from "
        "noise instead of held"
    )
    # Holding must still SHOW something. Suppressing the ETA entirely while the
    # drive works is its own bug: the user reads a vanished estimate as a hang.
    assert all(text for text in held), (
        f"the ETA vanished while holding instead of showing the last value: {held!r}"
    )
    assert before is not None  # floor: a baseline really was established first


def test_a_rerip_restarting_progress_resets_the_rate_estimate(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """94.79% -> 29.35% is a new pass, not a regression: measure it on its own."""
    worker, clock = _eta_worker(tmp_path, monkeypatch)
    _feed(worker, clock, [80.0, 85.0, 90.0, 94.79])
    assert len(worker._eta_rate_window) > 1, "no window built; the test proves nothing"
    _feed(worker, clock, [29.35])  # the measured re-rip restart
    assert len(worker._eta_rate_window) == 1, (
        "the album's rate window survived a progress restart, so two different "
        "scales are being averaged together"
    )


def test_the_measured_62_hour_sequence_cannot_happen_again(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Replay the field sequence — with the wobble the trace's own rounding hid.

    Samples 338-382 of the 2026-08-05 rip: track 14 finishing, then track 5's
    re-rip restarting progress and freezing it. The old code printed
    51 -> 59 -> 70 -> 85 -> 115 -> 175 -> 335 -> **3715** minutes across it.

    **THE FIRST VERSION OF THIS TEST PASSED WITH THE BUG RESTORED**, and the reason
    is worth keeping: `eta_trace` rounds `overall_percent` to two decimals, so the
    frozen samples all read exactly `35.45`. Feeding those literal values makes
    `window_dfrac` exactly **zero**, which even the buggy code handled — it fell to
    the cumulative branch and produced a sane number. The explosion needed a delta
    that was *tiny but positive*, i.e. movement below the trace's own resolution.

    So the sub-0.01pp wobble here is **inferred, not observed**: cyanrip was
    actively re-reading, so its true percentage cannot have been bit-for-bit
    constant, and only a positive delta explains the measured 3715. Stating that
    plainly because the evidence chain matters — the percentages are measured, the
    wobble is a deduction from them plus the arithmetic.

    **THE STALL DETECTOR IS DISABLED HERE, and the field data is why.** The rip's
    own debug log contains `rip stalled: no forward progress for 3m 0s at 35.5%
    (track 5)` — so in the field the stall detector *did* eventually take over and
    replace the countdown. That means the bug lives in the **first 180 seconds** of a
    freeze, before the rescue, and the 3715-minute reading landed about 80 s in. A
    test that lets the stall detector fire is testing the rescue, not the bug: that
    is precisely why the first version of this test passed with the fix reverted.
    """
    monkeypatch.setattr(rip_worker_module, "_ETA_STALL_THRESHOLD_S", 1e9)
    measured = [
        93.66,
        93.95,
        94.24,
        94.52,
        94.79,  # track 14 finishing
        29.35,
        29.69,
        29.89,
        30.13,
        30.47,
        30.68,  # the re-rip restarts progress
        31.28,
        31.75,
        32.09,
        32.56,
        33.04,
        33.64,
        34.18,
        34.66,
        34.99,
        35.26,
        35.45,
    ]
    # The freeze: 15 samples x 10 s = 150 s, under the 180 s stall threshold, with
    # the inferred sub-resolution wobble.
    frozen = [35.45 + (0.004 if i % 2 else 0.0) for i in range(15)]
    worker, clock = _eta_worker(tmp_path, monkeypatch)
    peak = 0.0
    for text in _feed(worker, clock, [*measured, *frozen]):
        peak = max(peak, worker._smoothed_remaining_s or 0.0)
        for hours in re.findall(r"(\d+)h", text):
            assert int(hours) < 24, f"an absurd ETA was displayed: {text!r}"
    assert peak < 24 * 60 * 60, (
        f"replaying the measured sequence still peaks at {peak / 3600:.1f} hours"
    )
    # FLOOR: the replay must actually have driven the estimator, or it proves nothing.
    assert worker._smoothed_remaining_s is not None, "no estimate was ever produced"


# --- a secure re-read is not a scratched disc, and not an exploding ETA ----------
#
# MEASURED ON REAL HARDWARE (2026-08-05, b8 + cyanrip f5e11ba, the Police baseline
# disc). Two DIFFERENT bugs, one cause, both in the shipped artifacts:
#
#   the rip's own debug log:
#     01:38:57 WARNING rip stalled: no forward progress for 3m 2s at 21.7% (track 3)
#                      — the drive is stuck on a hard-to-read spot
#     01:38:50 DEBUG   cyanrip │ Ripping track 3, progress - 52.29%
#     01:38:55 DEBUG   cyanrip │ Ripping track 3, progress - 54.50%
#
#   the rip's own eta_trace (samples 372-380), the same minutes:
#     21.73% -> 21.73% -> ... (frozen) ... and the ETA 54m -> 65 -> 75 -> 85
#     -> 110 -> 135 -> 195 -> 340 -> 500 minutes, then a snap back to 46m
#
# The drive was reading PERFECTLY, at 1x, printing a steady climb — because this is
# the secure re-read (`-Z`), which reads the SAME track again. `_overall_from_track`
# maps that read into a span of the album the bar has already covered and
# `_bump_overall` refuses to regress, so the album fraction is pinned for the whole
# re-read. Watching only the album fraction, that is indistinguishable from a wedged
# drive — so we told the maintainer twice in one rip that a good disc was scratched,
# and divided (1 - 0.2173) of an album by whatever noise was left in the window.
#
# The floor added for the 62-hour bug could not catch this one: for the first 90 s of
# the freeze the window still holds real pre-freeze movement, so the floor is
# legitimately met and the divisor is legitimately tiny.


# The Police baseline disc's real per-track lengths, from the TOC of the rip's own
# EAC-compatible log (MM:SS.FF at 75 frames/s). Used so the replay weights the album
# bar exactly as the field run did — an equal-slices fallback would put the freeze at
# a different percentage and stop being a replay.
_POLICE_TOC_MMSSFF: list[tuple[int, int, int]] = [
    (3, 13, 12),
    (3, 1, 5),
    (4, 51, 28),
    (5, 2, 0),
    (4, 0, 72),
    (4, 7, 8),
    (4, 21, 7),
    (3, 45, 30),
    (3, 1, 0),
    (4, 14, 45),
    (5, 0, 30),
    (5, 15, 23),
    (4, 53, 42),
    (4, 55, 55),
]


def _police_lengths_ms() -> list[int]:
    return [
        (m * 60 + s) * 1000 + round(f * 1000 / 75) for m, s, f in _POLICE_TOC_MMSSFF
    ]


def _rip_lines_worker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[RipWorker, _Clock]:
    """A worker fed by REAL cyanrip stdout lines, with the Police disc's lengths.

    Deliberately not `_eta_worker`: these tests are about a signal that only exists
    in the per-track progress line, so calling `_album_eta_text` with a bare
    percentage would bypass the very code under test. Driving the actual parser is
    what makes the sequence below a replay rather than an assertion about numbers I
    chose.
    """
    clock = _Clock()
    monkeypatch.setattr(rip_worker_module.time, "monotonic", clock)
    worker = RipWorker(
        _FakeBackend(handle=_FakeHandle(lines=[], exit_code=0)),
        _params_with_lengths(tmp_path, list(_police_lengths_ms())),
    )
    worker._total_tracks = 14
    worker._started_monotonic = clock.now - 600.0
    worker._eta_pass_started = worker._started_monotonic
    return worker, clock


def _eta_elapsed(worker: RipWorker, clock: _Clock) -> float:
    """Seconds of THIS PASS elapsed, as `_album_eta_text` computes it.

    A helper because the two floors below first open-coded it as `clock.now - 600`
    — which is not the elapsed time at all (the fake clock starts at 10_000, and the
    baseline is the pass start), so one floor was ~8800 against a 90-second bound and
    could never fail. A floor that cannot fail is the decoration CLAUDE.md warns
    about, and it arrived in the check written to prevent exactly that.
    """
    return clock.now - (worker._eta_pass_started or 0.0)


def _feed_lines(
    worker: RipWorker, clock: _Clock, track: int, percents: list[float], step: float
) -> list[str]:
    """Feed cyanrip progress lines for `track`, `step` seconds apart.

    Returns the status suffix `_album_eta_text` produced for each, which is exactly
    what the user reads on the progress line.
    """
    out: list[str] = []
    for pct in percents:
        clock.tick(step)
        prog = worker._progress_for(f"Ripping track {track}, progress - {pct:.2f}%")
        assert prog is not None, f"the progress line for {pct}% did not parse"
        out.append(worker._album_eta_text(prog[0]))
    return out


def test_a_secure_reread_is_not_reported_as_a_stalled_or_scratched_disc(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The field bug, verbatim: a healthy re-read must never say "scratch".

    Track 3's re-read ran for ~10 minutes with the album bar pinned, so the
    album-fraction-only stall detector fired twice — while cyanrip's own line climbed
    steadily. A user reading "the drive is stuck on a hard-to-read spot (a scratch or
    smudge)" about a disc that is fine will go clean or replace it for nothing.
    """
    worker, clock = _rip_lines_worker(tmp_path, monkeypatch)
    # Track 3's first read, to 100% — this is what pins the bar at 21.73%.
    _feed_lines(worker, clock, 3, [float(p) for p in range(10, 101, 5)], 10.0)
    pinned = worker._overall
    # Now the re-read: cyanrip restarts the same track at ~0% and climbs. Run it for
    # WELL past the stall threshold — in the field it ran for two full 4:51 passes.
    reread = [float(p) for p in range(2, 100, 2)]
    shown = _feed_lines(worker, clock, 3, reread, 10.0)
    assert _eta_elapsed(worker, clock) > rip_worker_module._ETA_STALL_THRESHOLD_S * 2, (
        "the replay did not run long enough to reach the stall threshold, so it "
        "cannot prove the detector stays quiet"
    )
    assert worker._overall == pinned, (
        "the album bar moved during the re-read, so this replay is not reproducing "
        "the frozen-bar condition the bug needs"
    )
    assert worker._reread_pass == 1, (
        f"the re-read was not recognised (pass={worker._reread_pass}); the rest of "
        "this test would then be checking the wrong code path"
    )
    for text in shown:
        assert "stalled" not in text, f"a healthy re-read was called a stall: {text!r}"
        assert "scratch" not in text, (
            f"a healthy re-read was blamed on a scratch: {text!r}"
        )
    assert not worker._eta_stalled, "the worker still believes the rip is stalled"


def test_a_genuinely_wedged_drive_is_still_reported_stalled(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The converse, and the reason the fix is a SECOND signal rather than an
    exemption: when the drive really does stop, cyanrip stops printing progress
    lines too, so both signals go quiet and the detector must still fire. A fix that
    silenced the detector during re-reads would have passed the test above and
    reintroduced the hours-long silent hang the detector exists for."""
    worker, clock = _rip_lines_worker(tmp_path, monkeypatch)
    _feed_lines(worker, clock, 3, [float(p) for p in range(10, 61, 5)], 10.0)
    # The drive wedges: no more progress lines at all, just the passage of time.
    clock.tick(rip_worker_module._ETA_STALL_THRESHOLD_S + 30.0)
    text = worker._album_eta_text(worker._overall)
    assert "stalled" in text, (
        f"a wedged drive was not reported as stalled: {text!r} — the liveness "
        "signal is being treated as permanent instead of as a timestamp"
    )
    assert worker._eta_stalled


def test_the_eta_holds_and_says_why_during_a_secure_reread(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Replay the measured climb. The album fraction is pinned, so there is nothing
    to project from; the honest output is the last estimate plus the reason.

    The field numbers this replaces: 54m -> 1h5m -> 1h15m -> 1h25m -> 1h50m ->
    2h15m -> 3h15m -> 5h40m, across 70 seconds, on a disc with ~22 minutes to go.
    """
    worker, clock = _rip_lines_worker(tmp_path, monkeypatch)
    _feed_lines(worker, clock, 3, [float(p) for p in range(10, 101, 5)], 10.0)
    baseline = worker._smoothed_remaining_s
    assert baseline is not None, (
        "no estimate was established from the first read, so a 'held' assertion "
        "below would be vacuously true"
    )
    # The measured re-read percentages from the trace's own `activity` strings.
    shown = _feed_lines(
        worker, clock, 3, [5.0, 7.0, 11.0, 14.0, 17.0, 21.0, 24.0], 10.0
    )
    assert worker._smoothed_remaining_s == baseline, (
        "the smoothed estimate moved while the album bar was pinned by a re-read — "
        "it is still being recomputed from a frozen fraction"
    )
    for text in shown:
        assert "verifying track 3" in text, (
            f"the user is not told why the estimate stopped moving: {text!r}"
        )
        assert "left" in text, f"the estimate vanished during the re-read: {text!r}"
        for hours in re.findall(r"(\d+)h", text):
            assert int(hours) < 2, f"the ETA climbed during a re-read: {text!r}"


def test_the_eta_resumes_on_a_fresh_window_after_a_reread(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No rate window may ever SPAN a freeze — the jump on the far side is catch-up,
    not speed.

    Measured: the first sample after track 3's re-read read 21.73% -> 29.55% and
    projected 13 minutes for 12 minutes of work it had not started. That jump is
    everything the pinned bar hid arriving at once, and dividing it by a window whose
    other end predates the freeze reads the rate as far faster than the drive can go.

    The window is emptied when the re-read STARTS, which is what makes this hold. A
    SHORT re-read is what tests it: the discarded points have to still be inside the
    90-second window at the moment the next track appends, or their absence proves
    nothing but the pruning that would have happened anyway.
    """
    worker, clock = _rip_lines_worker(tmp_path, monkeypatch)
    _feed_lines(worker, clock, 3, [float(p) for p in range(10, 101, 5)], 10.0)
    pre_freeze = list(worker._eta_rate_window)
    assert len(pre_freeze) > 1, "no pre-freeze window was built; nothing to poison"
    _feed_lines(worker, clock, 3, [5.0, 40.0, 75.0, 100.0], 10.0)  # 40 s: sub-window
    assert worker._reread_pass == 1, "the re-read was not detected; nothing to leave"
    _feed_lines(worker, clock, 5, [3.0, 8.0, 14.0], 10.0)
    assert worker._reread_pass == 0, "the re-read state survived the track change"
    newest_pre_freeze = max(elapsed for elapsed, _ in pre_freeze)
    assert (
        _eta_elapsed(worker, clock) - newest_pre_freeze
        < rip_worker_module._ETA_RATE_WINDOW_S
    ), (
        "the pre-freeze points would have aged out of the window on their own, so "
        "this test cannot tell the fix from ordinary pruning"
    )
    survivors = [p for p in worker._eta_rate_window if p[0] <= newest_pre_freeze]
    assert not survivors, (
        f"{len(survivors)} pre-freeze point(s) are still in the rate window, so the "
        "measured rate is the catch-up jump divided by the frozen period"
    )


def test_every_eta_branch_records_a_trace_sample(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The diagnostic hole. `eta_trace` used to record only fresh measurements, so
    it went silent on exactly the minutes worth analysing — the b8 trace has a
    541-second gap where the re-read and the stall were. A trace with holes over the
    interesting part cannot answer the question it exists for."""
    worker, clock = _rip_lines_worker(tmp_path, monkeypatch)
    _feed_lines(worker, clock, 3, [float(p) for p in range(10, 101, 5)], 10.0)
    _feed_lines(worker, clock, 3, [2.0, 6.0, 10.0], 10.0)  # re-read
    clock.tick(rip_worker_module._ETA_STALL_THRESHOLD_S + 30.0)
    worker._album_eta_text(worker._overall)  # wedged
    states = [s.get("state") for s in worker.eta_trace]
    assert "computed" in states, "no measurement was recorded at all"
    assert "rereading" in states, (
        f"the re-read minutes are missing from the trace: {states}"
    )
    assert "stalled" in states, (
        f"the stalled minutes are missing from the trace: {states}"
    )
    # A held sample must be LABELLED, or it reads as a fresh measurement — which is
    # the mistake that made the field peak un-analysable.
    for sample in worker.eta_trace:
        assert "state" in sample and "reread_pass" in sample, (
            f"a trace sample carries no provenance: {sample}"
        )
    rereads = [s for s in worker.eta_trace if s.get("state") == "rereading"]
    assert rereads and all(s["reread_pass"] >= 1 for s in rereads), (
        "a 'rereading' sample recorded reread_pass 0, so the two fields disagree"
    )


# --- The post-rip auto-fix ("securing") pass -------------------------------
#
# THE FIELD BUG these cover, read off the 2026-08-05 rig rip's own `eta_trace`
# (Police, "Every Breath You Take: The Classics", 14 tracks, app v0.6.4b11,
# ripper cyanrip 0.9.4-rc1+platterpus.5-beta.5):
#
#   our_eta_seconds  = 2580 (43m), FROZEN across 47 consecutive samples
#   actual_remaining = 4 seconds at the last of them
#   overall_percent  = 35.45, having been 94.77 when the album pass ended
#   activity         = "Ripping track 5 of 14... 99% - about 43m 0s left …"
#   cyanrip_eta      = "3s"   (the ripper's own estimate — and it was right)
#
# The cause was not a bad formula. It was the ALBUM model being applied to a
# pass that is not an album pass: a second cyanrip run, launched after all 14
# tracks were already on disk, re-reading ONE track (`-l 5`) to secure it. The
# fix is to make the worker *know* which kind of pass it is in — declared by the
# call site, never inferred from the numbers — and give the securing pass its
# own progress, wording and estimate.


class _TickingHandle(_FakeHandle):
    """A `_FakeHandle` whose output ADVANCES the fake clock as it is consumed.

    Every rate measurement in the worker divides by wall-clock. A fake that
    yields its whole script inside one microsecond makes every such division
    degenerate, so a test built on it measures the harness, not the product —
    and, worse, it is *safer* than the real thing, which is the gap
    `docs/testing.md` warns stand-ins about. Ticking per line is what makes this
    fake behave like a ripper that prints over minutes.
    """

    def __init__(self, lines: Iterable[str], clock: _Clock, step: float) -> None:
        super().__init__(lines=lines, exit_code=0)
        self._clock: _Clock = clock
        self._step: float = step

    def log_lines(self) -> Iterable[str]:
        for line in self._lines:
            self._clock.tick(self._step)
            yield line


def _cyanrip_read_lines(track: int, reads: int, *, step_pct: int = 4) -> list[str]:
    """cyanrip's real progress-redraw shape for `reads` successive reads of one track.

    Each read sweeps 0→100%, which is exactly what a `-Z` secure re-read looks
    like on the wire (measured 2026-08-05: "progress - 100%" then "progress - 5%",
    twice). The per-op ETA clause is included because it is part of the line the
    ripper actually prints and one of the tests is about that field.
    """
    lines: list[str] = []
    for _ in range(reads):
        for pct in range(step_pct, 101, step_pct):
            # A plausible per-op ETA: 2.5 s of work per remaining percentage point.
            eta = max(1, int((100 - pct) * 2.5))
            lines.append(f"Ripping track {track}, progress - {pct:.2f}%, ETA - {eta}s")
    return lines


def _police_worker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[RipWorker, _Clock, _FakeBackend, _Signals]:
    """A worker on the Police disc with a driveable clock and captured signals."""
    clock = _Clock()
    monkeypatch.setattr(rip_worker_module.time, "monotonic", clock)
    backend = _FakeBackend(handle=_FakeHandle(lines=[], exit_code=0))
    worker = RipWorker(backend, _params_with_lengths(tmp_path, _police_lengths_ms()))
    signals = _Signals()
    signals.attach(worker)
    return worker, clock, backend, signals


def _run_pass(
    worker: RipWorker,
    backend: _FakeBackend,
    clock: _Clock,
    lines: list[str],
    *,
    pass_kind: str,
    only_tracks: tuple[int, ...] = (),
    output_dir: Path | None = None,
    step: float = 5.0,
) -> None:
    """Drive one real `_rip_once` pass over `lines`, declaring what kind it is.

    Deliberately the production entry point rather than poking `_pass_kind`
    directly: the thing under test is that the declaration reaches the progress
    model, the label and the ETA, and a test that sets the flag by hand would
    pass even if `_rip_once` never wired it up.
    """
    backend.set_handle(_TickingHandle(lines, clock, step))
    worker._rip_once(
        read_speed=0,
        secure_rerip_matches=10 if pass_kind == rip_worker_module._PASS_REFIX else 0,
        output_dir=output_dir,
        only_tracks=only_tracks,
        pass_kind=pass_kind,
    )


def _album_tail_lines() -> list[str]:
    """The last two tracks of the whole-disc pass, which take the album bar to 95%.

    Enough to establish a believed album estimate and a high-water bar mark — the
    two things the securing pass then has to not destroy.
    """
    lines: list[str] = ["Disc tracks:    14"]
    for track in (13, 14):
        for pct in range(5, 101, 5):
            lines.append(f"Ripping track {track}, progress - {pct:.2f}%, ETA - 2m")
        lines.append(f"Track {track} ripped and encoded successfully!")
    return lines


def test_the_auto_fix_rerip_is_declared_as_its_own_pass_not_inferred(
    qapp: QApplication, tmp_path: Path
) -> None:
    """The mechanism, checked at the wiring rather than at the model.

    `_auto_fix_tracks` must tell `_rip_once` that its invocation is a securing
    pass. Everything else in this section keys off that declaration, so if the
    call site stopped making it, every other test here would still be exercising
    the flag it set by hand and would stay green while the product regressed.

    The pass kind is sampled at the instant the backend is invoked — i.e. from
    inside the pass — because that is when it has to be right.
    """
    backend = _FakeBackend(handle=_FakeHandle(lines=["ripping"], exit_code=0))
    writer = _fake_rip_writer(_PASS1_UNSTABLE, _rerip_ok_log(), True)
    seen: list[tuple[tuple[int, ...], str]] = []
    worker = RipWorker(
        backend,
        _params(tmp_path, read_speed_mode="auto_ladder", secure_rerip_matches=2),
    )

    def _record(call: dict) -> None:
        seen.append((tuple(call["only_tracks"]), worker._pass_kind))
        writer(call)

    backend.rip_side_effect = _record

    worker.start_rip()

    assert len(seen) == 2, (
        f"expected a whole-disc pass and one securing re-rip, saw {seen} — this "
        "test cannot say anything about how the two are distinguished if only one "
        "of them ran"
    )
    assert seen[0] == ((), rip_worker_module._PASS_ALBUM), (
        f"the whole-disc pass did not declare itself an album pass: {seen[0]}"
    )
    assert seen[1] == ((3,), rip_worker_module._PASS_REFIX), (
        f"the auto-fix re-rip of track 3 did not declare itself a securing pass: "
        f"{seen[1]} — without that declaration it inherits the album progress "
        "model, which is the 94.77% -> 35.45% regression"
    )


def _securing_samples(worker: RipWorker) -> list[dict]:
    return [
        s
        for s in worker.eta_trace
        if s.get("pass_kind") == rip_worker_module._PASS_REFIX
    ]


def test_the_securing_pass_estimate_counts_down_instead_of_freezing(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The headline symptom: 43 minutes shown, frozen, with 4 seconds to go.

    The album pass runs to its end, then a securing pass re-reads track 5 three
    times. The estimate the user sees must track the work that is actually left —
    which, in this phase, is the read that is running — and must therefore MOVE.
    """
    worker, clock, backend, signals = _police_worker(tmp_path, monkeypatch)
    _run_pass(worker, backend, clock, _album_tail_lines(), pass_kind="album")
    _run_pass(
        worker,
        backend,
        clock,
        ["Disc tracks:    14", *_cyanrip_read_lines(5, reads=3)],
        pass_kind=rip_worker_module._PASS_REFIX,
        only_tracks=(5,),
        output_dir=tmp_path / "refix-tmp",
    )

    samples = _securing_samples(worker)
    assert len(samples) >= 10, (
        f"only {len(samples)} securing sample(s) were recorded, which is too few to "
        "tell a moving estimate from a frozen one — the replay is not reaching the "
        "code under test"
    )
    values = [s["our_eta_seconds"] for s in samples if s["our_eta_seconds"] is not None]
    assert len(values) >= 10, "the securing pass produced almost no estimates at all"
    # THE BUG, stated as an assertion: 47 samples all reading 2580 seconds.
    assert len(set(values)) >= 4, (
        f"the securing estimate took only {len(set(values))} distinct value(s) "
        f"across {len(values)} samples ({sorted(set(values))}) — that is the frozen "
        "reading the field trace showed, not an estimate"
    )
    assert max(values) < 2400, (
        f"the securing pass still projects album-scale time ({max(values)}s): the "
        "field freeze was 2580s for a four-second job"
    )
    # Within the FINAL read (nothing restarts after it) the estimate must fall.
    last_read = max(s["reread_pass"] for s in samples)
    tail = [
        s["our_eta_seconds"]
        for s in samples
        if s["reread_pass"] == last_read and s["our_eta_seconds"] is not None
    ]
    assert len(tail) >= 4, (
        f"only {len(tail)} sample(s) in the final read; a countdown cannot be "
        "demonstrated from that few"
    )
    assert tail == sorted(tail, reverse=True), (
        f"the estimate did not decrease as the read progressed: {tail}"
    )
    assert tail[-1] < tail[0] / 2, (
        f"the estimate barely moved across the whole read ({tail[0]}s -> "
        f"{tail[-1]}s) — it is being held, not measured"
    )
    # And the user-visible wording must scope the number to the read, never imply
    # it knows how many more re-reads there will be (it cannot).
    securing_status = [s for s in signals.statuses if "secure it" in s]
    assert len(securing_status) >= 10, (
        f"only {len(securing_status)} securing status line(s) were emitted"
    )
    with_eta = [s for s in securing_status if "left in" in s]
    assert len(with_eta) >= 5, (
        f"the securing phase almost never showed an estimate: {securing_status[:5]}"
    )
    for text in with_eta:
        assert "left in this read" in text or "left in re-read" in text, (
            f"the estimate is not scoped to the read it actually measures: {text!r}"
        )


def test_the_securing_pass_never_rewinds_the_album_bar_or_says_track_n_of_m(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Defects (2) and (3): the bar regressed 94.77% -> 35.45% and relabelled
    itself "Ripping track 5 of 14…" after all 14 tracks were on disk — while the
    same sentence carried a 99% track-local figure beside that 35.45% bar.

    **REVERT-PROOFED, and the result is worth knowing before you touch either
    fix.** Two independent changes prevent the rewind, and *each one alone is
    enough to keep this test green*:

    1. ``_reset_pass_progress`` no longer zeroes ``self._overall`` for a refix pass
       (b11 zeroed it unconditionally, which restarted the no-regress clamp and let
       35% be accepted after 94.77%);
    2. ``_progress_for`` returns the reserved post-rip band for a refix pass
       instead of mapping the track into the album's read band.

    So reverting **one** of them does NOT fail this test — measured, both ways.
    Reverting **both** fails it at **35.36%**, which is the field value (35.45%) to
    within the fixture's rounding. That is defence in depth, not redundancy, but it
    has a consequence: a green run here is *not* evidence that either fix is
    individually unnecessary. Do not delete one because the suite still passes —
    that is precisely the reasoning this note exists to block.
    """
    worker, clock, backend, signals = _police_worker(tmp_path, monkeypatch)
    _run_pass(worker, backend, clock, _album_tail_lines(), pass_kind="album")
    album_peak = max(overall for overall, _ in signals.progress)
    album_emissions = len(signals.progress)
    assert album_peak > 90.0, (
        f"the album pass only reached {album_peak:.2f}%, so a later 'did the bar "
        "regress' assertion would have nothing meaningful to regress from"
    )

    _run_pass(
        worker,
        backend,
        clock,
        ["Disc tracks:    14", *_cyanrip_read_lines(5, reads=3)],
        pass_kind=rip_worker_module._PASS_REFIX,
        only_tracks=(5,),
        output_dir=tmp_path / "refix-tmp",
    )

    securing_progress = signals.progress[album_emissions:]
    assert len(securing_progress) >= 20, (
        f"only {len(securing_progress)} progress emission(s) came from the securing "
        "pass; there is not enough here to prove the bar behaved"
    )
    worst = min(overall for overall, _ in securing_progress)
    assert worst >= album_peak, (
        f"the album bar REGRESSED to {worst:.2f}% during the securing pass (it was "
        f"{album_peak:.2f}% when the album finished) — the field symptom exactly"
    )
    overalls = [overall for overall, _ in signals.progress]
    assert overalls == sorted(overalls), (
        "the overall bar went backwards somewhere across the two passes"
    )
    assert max(overalls) < 100.0, (
        "the securing pass drove the album bar to 100%, which claims the rip is "
        "finished while a file may still be swapped in"
    )
    # The task bar is where the phase's motion lives, so it must still be moving.
    tasks = [task for _, task in securing_progress]
    assert len(set(tasks)) >= 10, (
        "the task bar barely moved during the securing pass, so the user has no "
        "live signal at all while the album bar deliberately holds"
    )

    # The album leg only ever touched tracks 13 and 14, so every status naming
    # track 5 came from the securing pass — no index arithmetic needed, and the
    # selector cannot silently pick up an album line if the fixture changes.
    about_track_5 = [s for s in signals.statuses if "track 5" in s]
    assert len(about_track_5) >= 10, (
        f"only {len(about_track_5)} status line(s) mentioned track 5; the securing "
        "pass is not reaching the status label"
    )
    for text in about_track_5:
        assert "of 14" not in text, (
            f"the securing pass still describes itself in album terms: {text!r} — "
            "there is no 'track 5 of 14' left to do, all 14 are already on disk"
        )
    # The label answers "did it stop saying the wrong thing"; this answers "did it
    # say the right thing". A check that only requires an absence passes when the
    # label disappears entirely.
    assert any("Re-ripping track 5 to secure it" in s for s in about_track_5), (
        f"the securing phase never names what it is doing: {about_track_5[:3]}"
    )


def test_the_same_lines_are_modelled_differently_by_pass_kind(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The declaration is what does the work — proved by holding the input fixed.

    Byte-identical cyanrip output is fed to two workers; the only difference is
    what the call site said the pass was. The album-declared run reproduces the
    field behaviour (a ~35% bar for track 5 of 14); the securing-declared run does
    not. If the distinguishing mechanism were a heuristic over the numbers, both
    runs would have to behave the same, because the numbers are the same.
    """
    lines = ["Disc tracks:    14", *_cyanrip_read_lines(5, reads=2)]

    as_album, clock_a, backend_a, sig_a = _police_worker(tmp_path, monkeypatch)
    _run_pass(as_album, backend_a, clock_a, lines, pass_kind="album")

    as_refix, clock_b, backend_b, sig_b = _police_worker(tmp_path, monkeypatch)
    _run_pass(
        as_refix,
        backend_b,
        clock_b,
        lines,
        pass_kind=rip_worker_module._PASS_REFIX,
        only_tracks=(5,),
        output_dir=tmp_path / "refix-tmp",
    )

    album_peak = max(overall for overall, _ in sig_a.progress)
    refix_peak = max(overall for overall, _ in sig_b.progress)
    assert album_peak < 45.0, (
        f"the album-declared run reached {album_peak:.2f}%, so it is NOT reproducing "
        "the album mapping (track 5 of 14 lands near 35%) and this comparison "
        "proves nothing"
    )
    assert refix_peak > 90.0, (
        f"the securing-declared run put the bar at {refix_peak:.2f}%; the securing "
        "pass must hold in the reserved post-rip band, not rewind into the read band"
    )
    assert any("of 14" in s for s in sig_a.statuses), (
        "the album-declared run did not produce the 'of 14' wording, so the "
        "contrast below is not measuring the label"
    )
    assert not any("of 14" in s for s in sig_b.statuses), (
        "the securing-declared run still labels itself in album terms"
    )


def test_the_secure_reread_hold_inside_the_album_pass_is_unchanged(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Case (i) must be untouched. A `-Z` re-read INSIDE the whole-disc pass is a
    different situation from the post-rip securing pass: there the album's
    remaining work genuinely has not changed, so holding the album estimate is the
    honest answer, and recomputing it from the pinned fraction is the b8 explosion
    (54m -> 5h40m in 70 seconds).

    Written as the converse of the change above, because "give the securing pass
    its own model" is one careless generalisation away from "stop holding during
    every re-read", which would silently restore that explosion.
    """
    worker, clock = _rip_lines_worker(tmp_path, monkeypatch)
    _feed_lines(worker, clock, 3, [float(p) for p in range(10, 101, 5)], 10.0)
    baseline = worker._smoothed_remaining_s
    assert baseline is not None, (
        "no album estimate was established, so 'it was held' would be vacuous"
    )
    assert worker._pass_kind == rip_worker_module._PASS_ALBUM, (
        "the fixture is not in an album pass; this test would then be checking the "
        "securing path and calling it the album path"
    )
    shown = _feed_lines(worker, clock, 3, [5.0, 9.0, 13.0, 17.0, 21.0, 25.0], 10.0)
    assert worker._reread_pass == 1, "no re-read was detected; nothing was held"
    assert worker._smoothed_remaining_s == baseline, (
        "the album estimate moved while the album bar was pinned by an in-pass "
        "re-read — the b8 hold has been lost"
    )
    assert len(shown) >= 5
    for text in shown:
        assert "verifying track 3" in text, (
            f"the in-pass re-read stopped explaining itself: {text!r}"
        )
        assert "left" in text, f"the held estimate vanished: {text!r}"
        # The securing wording must not leak into the album pass: it would tell a
        # user mid-album that the disc was finished and being checked.
        assert "left in this read" not in text and "left in re-read" not in text, (
            f"the securing pass's per-read wording leaked into an album pass: {text!r}"
        )
    states = [s.get("state") for s in worker.eta_trace]
    assert "rereading" in states, f"the in-pass hold stopped being traced: {states}"
    assert not [s for s in states if str(s).startswith("securing")], (
        f"an album pass recorded a securing state: {states}"
    )


def test_the_securing_pass_borrows_the_rippers_eta_only_where_we_have_none(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """cyanrip's own per-op ETA is a SECOND signal here, not a replacement.

    CLAUDE.md: "the fix for a signal going quiet is a second signal, not an
    exemption". Our own measurement does not exist for the first tick of a read
    (there is no window yet) — and that is the only place the ripper's number is
    used. Once we can measure, ours wins, and every borrowed sample is labelled so
    the trace never passes the dependency's claim off as our measurement.

    On the field rip the ripper said "3s" and was right while our album model said
    43 minutes; that is why it is worth having, and its history of printing "822h"
    at 0.01% is why it is not promoted.
    """
    worker, clock, backend, _signals = _police_worker(tmp_path, monkeypatch)
    _run_pass(
        worker,
        backend,
        clock,
        [
            # One read: the first line has no window behind it, the rest do.
            "Ripping track 5, progress - 4.00%, ETA - 40s",
            *[
                f"Ripping track 5, progress - {pct:.2f}%, ETA - 40s"
                for pct in range(8, 101, 4)
            ],
        ],
        pass_kind=rip_worker_module._PASS_REFIX,
        only_tracks=(5,),
        output_dir=tmp_path / "refix-tmp",
    )
    samples = _securing_samples(worker)
    assert len(samples) >= 5, f"too few securing samples to judge: {len(samples)}"
    borrowed = [s for s in samples if s["state"] == "securing_from_ripper"]
    measured = [s for s in samples if s["state"] == "securing"]
    assert len(borrowed) == 1, (
        f"expected exactly one borrowed sample (the first tick of the read, before "
        f"a rate window exists); got {len(borrowed)}: "
        f"{[s['state'] for s in samples]}"
    )
    assert borrowed[0]["our_eta_seconds"] == 40, (
        f"the borrowed value is not the ripper's own number: {borrowed[0]}"
    )
    assert len(measured) >= 4, (
        f"only {len(measured)} sample(s) came from our own measurement — the "
        "ripper's estimate has become the primary source, which it must not be"
    )
    # Ours diverges from the ripper's constant 40s, which is the proof that the
    # later samples are measurements and not the borrowed number carried forward.
    assert any(s["our_eta_seconds"] != 40 for s in measured), (
        "every 'measured' sample equals the ripper's own figure, so nothing here "
        "distinguishes a measurement from a passthrough"
    )


_PROVIDER_CONTRACT = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "handshake"
    / "inbound"
    / "artifacts"
    / "round-07-lap-25-provider-contract-g9048082.md"
)


def test_cyanrip_eta_parser_covers_every_shape_the_provider_contract_publishes(
    qapp: QApplication,
) -> None:
    """Read the shapes out of the FORK'S OWN published contract, not out of memory.

    CLAUDE.md: when a committed artifact can settle the question, the test should
    read the artifact — anything else pins a belief about it. §P2a of the round-7
    provider contract lists cyanrip's ETA segment formats; each is turned into a
    concrete string here and put through the real parser.
    """
    assert _PROVIDER_CONTRACT.is_file(), (
        f"the provider contract is missing at {_PROVIDER_CONTRACT}; this test "
        "cannot verify against an artifact that is not there"
    )
    text = _PROVIDER_CONTRACT.read_text(encoding="utf-8")
    formats = re.findall(
        r"^\|\s*\d+\s*\|\s*`,\s*ETA\s*-\s*([^`]+)`\s*\|\s*$", text, re.M
    )
    assert len(formats) >= 3, (
        f"found {len(formats)} ETA format row(s) in the provider contract "
        f"({formats}); the parser's coverage claim cannot be checked against fewer "
        "than the three shapes it is written for"
    )
    checked = 0
    for fmt in formats:
        # printf → a concrete sample. `%ih %im` → "7h 7m", `%llds` → "42s".
        sample = fmt.replace("%lld", "42").replace("%i", "7").strip()
        parsed = rip_worker_module._cyanrip_eta_seconds(sample)
        assert parsed is not None and parsed > 0, (
            f"the parser could not read {sample!r}, built from the contract's own "
            f"format {fmt!r} — a shape cyanrip is documented to print"
        )
        checked += 1
    assert checked >= 3, "fewer shapes were actually exercised than were found"
    # The exact values, so "it returned a number" is not mistaken for "it returned
    # the right number".
    assert rip_worker_module._cyanrip_eta_seconds("1h 5m") == 3900
    assert rip_worker_module._cyanrip_eta_seconds("3m") == 180
    assert rip_worker_module._cyanrip_eta_seconds("3s") == 3


@pytest.mark.parametrize(
    "raw",
    [
        None,
        "",
        "   ",
        "soon",
        "-3s",
        "3 seconds",
        "99999999999999999999h",
        "ETA - 3s",
        "3s3s3s",
        "\x00s",
        "m",
    ],
)
def test_cyanrip_eta_parser_refuses_junk_without_raising(
    qapp: QApplication, raw: str | None
) -> None:
    """It parses EXTERNAL text on the rip's read loop, where an exception ends the
    rip — so it must never raise, and it must not answer confidently about input it
    does not understand. The empty/whitespace cases are the specific trap: every
    group in the pattern is optional, so a naive version matches "" and reports a
    confident zero seconds remaining."""
    assert rip_worker_module._cyanrip_eta_seconds(raw) is None


def test_the_trace_says_which_kind_of_pass_each_sample_came_from(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Why the field trace was hard to read: 47 samples said "Ripping track 5 of
    14" at 35.45% and nothing in the record said they came from a separate
    one-track re-rip that ran after the album finished. Two samples with the same
    `overall_percent` mean different things depending on the pass, so the pass has
    to be in the sample."""
    worker, clock, backend, _signals = _police_worker(tmp_path, monkeypatch)
    _run_pass(worker, backend, clock, _album_tail_lines(), pass_kind="album")
    _run_pass(
        worker,
        backend,
        clock,
        ["Disc tracks:    14", *_cyanrip_read_lines(5, reads=2)],
        pass_kind=rip_worker_module._PASS_REFIX,
        only_tracks=(5,),
        output_dir=tmp_path / "refix-tmp",
    )
    trace = worker.eta_trace
    assert len(trace) >= 15, f"only {len(trace)} trace sample(s) recorded"
    assert all("pass_kind" in s for s in trace), (
        "a sample carries no pass kind, so it cannot be attributed to a pass"
    )
    kinds = {s["pass_kind"] for s in trace}
    assert kinds == {rip_worker_module._PASS_ALBUM, rip_worker_module._PASS_REFIX}, (
        f"the trace does not distinguish the two passes it recorded: {kinds}"
    )
    album = [s for s in trace if s["pass_kind"] == rip_worker_module._PASS_ALBUM]
    refix = [s for s in trace if s["pass_kind"] == rip_worker_module._PASS_REFIX]
    assert len(album) >= 5 and len(refix) >= 5, (
        f"one side is nearly empty (album={len(album)}, refix={len(refix)}), so the "
        "state assertions below would be near-vacuous"
    )
    assert all(str(s["state"]).startswith("securing") for s in refix), (
        f"a securing sample was labelled with an album branch: "
        f"{sorted({str(s['state']) for s in refix})}"
    )
    assert not any(str(s["state"]).startswith("securing") for s in album), (
        f"an album sample was labelled with a securing branch: "
        f"{sorted({str(s['state']) for s in album})}"
    )
