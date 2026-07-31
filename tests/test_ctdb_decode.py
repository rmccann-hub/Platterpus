# SPDX-License-Identifier: GPL-3.0-only
"""Tests for platterpus.ctdb.decode — host flac/metaflac wrappers (no real IO)."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import pytest

from platterpus.ctdb import decode


def _completed(returncode: int, stdout: bytes = b"", stderr: bytes = b""):
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=stderr
    )


def test_decode_raises_when_flac_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(decode, "_which", lambda name: None)
    with pytest.raises(decode.DecoderUnavailable):
        decode.decode_flac_to_pcm(Path("x.flac"))


def test_decode_returns_stdout_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(decode, "_which", lambda name: "/usr/bin/flac")
    pcm = b"\x01\x02\x03\x04"
    result = decode.decode_flac_to_pcm(
        Path("x.flac"), runner=lambda argv: _completed(0, stdout=pcm)
    )
    assert result == pcm


def test_decode_raises_on_nonzero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(decode, "_which", lambda name: "/usr/bin/flac")
    with pytest.raises(RuntimeError):
        decode.decode_flac_to_pcm(
            Path("x.flac"),
            runner=lambda argv: _completed(1, stderr=b"boom\n"),
        )


def test_flac_available_reflects_which(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(decode, "_which", lambda name: "/usr/bin/flac")
    assert decode.flac_available() is True
    monkeypatch.setattr(decode, "_which", lambda name: None)
    assert decode.flac_available() is False


def test_total_samples_parses_metaflac(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(decode, "_which", lambda name: "/usr/bin/metaflac")
    out = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="17640\n", stderr=""
    )
    assert decode.total_samples(Path("a.flac"), runner=lambda argv: out) == 17640


def test_total_samples_unparseable_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(decode, "_which", lambda name: "/usr/bin/metaflac")
    out = subprocess.CompletedProcess(args=[], returncode=0, stdout="??\n", stderr="")
    with pytest.raises(RuntimeError):
        decode.total_samples(Path("a.flac"), runner=lambda argv: out)


def test_total_samples_missing_metaflac(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(decode, "_which", lambda name: None)
    with pytest.raises(decode.DecoderUnavailable):
        decode.total_samples(Path("a.flac"))


def test_total_samples_nonzero_rc_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(decode, "_which", lambda name: "/usr/bin/metaflac")
    out = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="err")
    with pytest.raises(RuntimeError):
        decode.total_samples(Path("a.flac"), runner=lambda argv: out)


def test_total_samples_failure_carries_metaflac_stderr(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Regression (2026-07-31): the failure used to raise a bare "metaflac failed
    on a.flac" and throw metaflac's stderr away, so the reason was unrecoverable.

    The tool's own words must reach BOTH the exception message (which
    ctdb/verify.py turns into the user-visible verdict) and the log file.
    """
    monkeypatch.setattr(decode, "_which", lambda name: "/usr/bin/metaflac")
    out = subprocess.CompletedProcess(
        args=[],
        returncode=1,
        stdout="",
        stderr="a.flac: ERROR: the file does not appear to be a FLAC stream\n",
    )

    with caplog.at_level(logging.WARNING, logger="platterpus.ctdb.decode"):
        with pytest.raises(RuntimeError) as excinfo:
            decode.total_samples(Path("a.flac"), runner=lambda argv: out)

    # The specific reason, not just "something failed".
    assert "does not appear to be a FLAC stream" in str(excinfo.value)
    assert "rc=1" in str(excinfo.value)
    assert "does not appear to be a FLAC stream" in caplog.text
    assert "a.flac" in caplog.text


def test_total_samples_unparseable_output_is_logged(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """A zero exit with junk on stdout is just as undiagnosable — log what we
    actually got (stdout, plus any stderr) before it becomes a verdict."""
    monkeypatch.setattr(decode, "_which", lambda name: "/usr/bin/metaflac")
    out = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="??\n", stderr="odd warning"
    )

    with caplog.at_level(logging.WARNING, logger="platterpus.ctdb.decode"):
        with pytest.raises(RuntimeError):
            decode.total_samples(Path("a.flac"), runner=lambda argv: out)

    assert "'??'" in caplog.text  # the actual unparseable output, quoted
    assert "odd warning" in caplog.text


def test_decode_failure_carries_flac_stderr(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Same obligation for the decoder itself: the stderr tail reaches the
    exception message *and* the log (it previously reached neither the log nor
    named the file)."""
    monkeypatch.setattr(decode, "_which", lambda name: "/usr/bin/flac")

    with caplog.at_level(logging.WARNING, logger="platterpus.ctdb.decode"):
        with pytest.raises(RuntimeError) as excinfo:
            decode.decode_flac_to_pcm(
                Path("x.flac"),
                runner=lambda argv: _completed(
                    1, stderr=b"x.flac: ERROR: got error while decoding data\n"
                ),
            )

    assert "got error while decoding data" in str(excinfo.value)
    assert "x.flac" in str(excinfo.value)
    assert "got error while decoding data" in caplog.text


def test_which_falls_back_to_absolute_path(monkeypatch: pytest.MonkeyPatch) -> None:
    # PATH lookup fails, but the binary exists at a known absolute location.
    monkeypatch.setattr(decode.shutil, "which", lambda name: None)
    monkeypatch.setattr(
        decode.Path, "exists", lambda self: str(self) == "/usr/bin/flac"
    )
    assert decode._which("flac") == "/usr/bin/flac"


def test_which_returns_none_when_nothing_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(decode.shutil, "which", lambda name: None)
    monkeypatch.setattr(decode.Path, "exists", lambda self: False)
    assert decode._which("flac") is None
