"""A killed child's output is kept, not thrown away.

**Asked by the cyanrip fork (seam packet 2026-08-10, T-C), and the answer was
"we discard it".** On 2026-08-10 a `cyanrip -I -N -d /dev/sr0` probe was killed
at 120 s and the diagnostic record showed ``exit code: none`` with **nothing
captured** — while the same command had taken 16 s three days earlier. Their
point: *"if output was captured and discarded, that is the evidence that would
settle whether the hang was ours, and keeping it costs nothing."*

It was captured and discarded. `KillableCommand.run` caught `TimeoutExpired`,
killed the group, called `communicate()` a second time to reap — which **returns
everything buffered before the timeout** — ignored the return value, and
re-raised.

That is `CLAUDE.md`'s diagnostic-completeness rule for the fourth time: a fact we
held and dropped, which is worse than one never obtained because the report looks
complete either way. `subprocess.run` has always done this correctly (catch,
drain, re-raise with output attached); this class was the one path that did not,
which is why swapping `run` for it silently lost the capture.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from platterpus.killable import KillableCommand


def _python(code: str) -> list[str]:
    return [sys.executable, "-u", "-c", code]


def test_output_written_before_a_timeout_survives_the_kill() -> None:
    """The regression. A child that talks, then hangs, keeps what it said."""
    cmd = KillableCommand("probe")
    with pytest.raises(subprocess.TimeoutExpired) as caught:
        cmd.run(
            _python(
                "import sys, time\n"
                "print('reading sector 12345')\n"
                "sys.stdout.flush()\n"
                "time.sleep(30)\n"
            ),
            timeout=1.0,
        )
    assert "reading sector 12345" in (caught.value.stdout or ""), (
        "the child's output was discarded when it was killed — that line is often "
        "the whole diagnosis of a hang"
    )


def test_stderr_survives_too_because_a_hang_often_reports_there() -> None:
    """`TimeoutExpired.output` aliases `.stdout` only; stderr needs its own path."""
    cmd = KillableCommand("probe")
    with pytest.raises(subprocess.TimeoutExpired) as caught:
        cmd.run(
            _python(
                "import sys, time\n"
                "sys.stderr.write('drive not ready\\n')\n"
                "sys.stderr.flush()\n"
                "time.sleep(30)\n"
            ),
            timeout=1.0,
        )
    assert "drive not ready" in (caught.value.stderr or "")


def test_a_silent_child_reports_empty_rather_than_inventing_output() -> None:
    """Non-triviality floor, and a tri-state one.

    Without this the fix could "pass" by attaching a placeholder. Nothing written
    must read as nothing captured — absence is a real answer here and must not be
    dressed up.
    """
    cmd = KillableCommand("probe")
    with pytest.raises(subprocess.TimeoutExpired) as caught:
        cmd.run(_python("import time; time.sleep(30)"), timeout=1.0)
    assert not (caught.value.stdout or "")
    assert not (caught.value.stderr or "")


def test_the_normal_path_is_unaffected() -> None:
    """A command that finishes in time still returns its output the same way."""
    cmd = KillableCommand("probe")
    done = cmd.run(_python("print('fine')"), timeout=30.0)
    assert done.returncode == 0
    assert "fine" in (done.stdout or "")


def test_run_capture_surfaces_the_partial_output_in_the_diagnostic(monkeypatch):
    """The other half: capturing it is useless if the record does not carry it.

    `run_capture` read `exc.output` — the stdout alias — so a tool that wrote its
    last words to stderr still produced an empty `detail`. Both streams now reach
    the diagnostic, merged exactly as the success path merges them.
    """
    from platterpus import diagnostics
    from platterpus.adapters import rip_backend

    recorded: list[dict[str, object]] = []
    monkeypatch.setattr(
        diagnostics,
        "error",
        lambda code, message, **fields: recorded.append(
            {"code": code, "message": message, **fields}
        ),
    )

    def _timeout(*_args: object, **_kwargs: object) -> None:
        exc = subprocess.TimeoutExpired(cmd=["cyanrip"], timeout=120.0)
        exc.stdout = "opening drive\n"
        exc.stderr = "no disc detected\n"
        raise exc

    monkeypatch.setattr(rip_backend.INFO_PROBE, "run", _timeout)

    with pytest.raises(rip_backend.RipError):
        rip_backend.run_capture("cyanrip", "/usr/bin/cyanrip", ["-I"], timeout=120.0)

    assert recorded, "a timeout must be recorded, not swallowed"
    detail = str(recorded[-1].get("detail") or "")
    assert "opening drive" in detail, "stdout missing from the diagnostic"
    assert "no disc detected" in detail, (
        "stderr missing from the diagnostic — `exc.output` aliases stdout only"
    )
    # Tri-state discipline: nothing was reaped, so the exit code is None and never 0.
    assert recorded[-1].get("exit_code") is None


def test_a_timeout_with_nothing_captured_says_so_rather_than_going_quiet(monkeypatch):
    """An empty capture must be explained, not rendered as a blank field.

    "Nothing captured" and "we did not look" are different, and the message has to
    distinguish them or the next reader repeats this whole investigation.
    """
    from platterpus import diagnostics
    from platterpus.adapters import rip_backend

    recorded: list[dict[str, object]] = []
    monkeypatch.setattr(
        diagnostics,
        "error",
        lambda code, message, **fields: recorded.append(
            {"code": code, "message": message, **fields}
        ),
    )

    def _timeout(*_args: object, **_kwargs: object) -> None:
        raise subprocess.TimeoutExpired(cmd=["cyanrip"], timeout=120.0)

    monkeypatch.setattr(rip_backend.INFO_PROBE, "run", _timeout)

    with pytest.raises(rip_backend.RipError):
        rip_backend.run_capture("cyanrip", "/usr/bin/cyanrip", ["-I"], timeout=120.0)

    message = str(recorded[-1].get("message") or "")
    assert "written nothing" in message or "unreapable" in message, (
        f"an empty capture must explain itself; got {message!r}"
    )


def test_bytes_on_the_exception_do_not_crash_the_diagnostic(monkeypatch) -> None:
    """The unreapable path can leave **bytes** on the exception. Handle them.

    `Popen.communicate` populates `TimeoutExpired` from the raw pipe before text
    decoding, so when the second drain cannot complete — an unreapable child, the
    exact case of the 2026-08-10 hang — the attributes are bytes. Concatenating
    them with a `str` raises `TypeError` and takes down the diagnostic path at the
    one moment it is the only thing still reporting.

    Found by revert-proving the capture fix: the reverted run failed with
    `a bytes-like object is required, not 'str'` instead of the clean assertion
    the test expected, and the surprise was the finding.
    """
    from platterpus import diagnostics
    from platterpus.adapters import rip_backend

    recorded: list[dict[str, object]] = []
    monkeypatch.setattr(
        diagnostics,
        "error",
        lambda code, message, **fields: recorded.append(
            {"code": code, "message": message, **fields}
        ),
    )

    def _timeout(*_args: object, **_kwargs: object) -> None:
        exc = subprocess.TimeoutExpired(cmd=["cyanrip"], timeout=120.0)
        exc.stdout = b"opening drive\n"
        exc.stderr = b"\xff\xfe not valid utf-8 \n"  # and undecodable, for good measure
        raise exc

    monkeypatch.setattr(rip_backend.INFO_PROBE, "run", _timeout)

    with pytest.raises(rip_backend.RipError):
        rip_backend.run_capture("cyanrip", "/usr/bin/cyanrip", ["-I"], timeout=120.0)

    detail = str(recorded[-1].get("detail") or "")
    assert "opening drive" in detail, (
        "bytes output was dropped instead of decoded — that is the whole capture"
    )
