"""Fault injection at the boundaries where a failure must not become a second one.

**The category this suite did not have.** The taxonomy calls it reliability
testing: every external dependency returning an error, timing out, or running out
of a resource. Platterpus has one place where that matters more than anywhere
else — **the evidence bundle**, which is the artifact a user sends when something
has ALREADY gone wrong. Its module docstring promises *"it never raises"*, and
until now nothing injected a fault to find out.

A reporting path that fails while reporting a failure is the worst version of the
bug, because it destroys the only evidence of the first one. `docs/testing.md`'s
framing applies directly: a diagnosis captured and never delivered is the same
defect from the user's side.

Scope, stated so it is not mistaken for more: these inject **filesystem** faults,
which are the ones reachable without hardware. Drive and network faults are named
in `TASKS.md` and are hardware- or worker-gated.
"""

from __future__ import annotations

import errno
import tarfile
from pathlib import Path
from typing import Any

import pytest

from platterpus import evidence_bundle


def _log_dir(tmp_path: Path) -> Path:
    d = tmp_path / "logs"
    d.mkdir()
    (d / "log.txt").write_text("a log line\n", encoding="utf-8")
    return d


def _build(tmp_path: Path, **kw: Any) -> Any:
    # `log_dir` is resolved lazily. Passing `_log_dir(tmp_path)` as a `dict.pop`
    # default evaluates it EVERY call — creating the directory even when the
    # caller supplied its own, which made four of these tests fail on
    # FileExistsError rather than on the fault they inject.
    log_dir = kw.pop("log_dir", None)
    if log_dir is None:
        log_dir = _log_dir(tmp_path)
    return evidence_bundle.build_bundle(
        dest_dir=kw.pop("dest_dir", tmp_path / "bundles"),
        stamp="20260905T000000Z",
        app_version="0.6.38",
        outcome="test",
        log_dir=log_dir,
        **kw,
    )


def test_the_happy_path_still_produces_a_readable_archive(tmp_path: Path) -> None:
    """The control. Without it, every fault case below could be passing because
    the bundle never works at all — a suite that cannot tell 'handled the fault'
    from 'never functioned' is measuring nothing."""
    result = _build(tmp_path)
    assert result.ok and result.path is not None
    with tarfile.open(result.path) as tar:
        assert tar.getnames(), "the archive is empty"


def test_a_FULL_DISK_is_reported_not_raised(tmp_path: Path, monkeypatch) -> None:
    """**ENOSPC while writing the bundle.**

    An archival ripper filling a disk mid-session is not exotic — a whole-disc
    FLAC rip plus derived formats is gigabytes, and the bundle is written after
    it. The failure must arrive as `BundleResult.error` for the caller to show,
    never as an exception out of a daemon thread where nothing is catching.
    """
    real_open = tarfile.open

    def _full(*args: Any, **kwargs: Any) -> Any:
        raise OSError(errno.ENOSPC, "No space left on device")

    monkeypatch.setattr(tarfile, "open", _full)
    result = _build(tmp_path)
    monkeypatch.setattr(tarfile, "open", real_open)

    assert not result.ok
    assert result.error, "a full disk produced no error text to show the user"
    assert "space" in result.error.lower() or "enospc" in result.error.lower(), (
        result.error
    )


def test_an_UNREADABLE_source_file_is_skipped_and_NAMED(tmp_path: Path) -> None:
    """A permission error on one artifact must not lose the other twenty — and
    the omission must be visible. *An absence nobody can see reads as a complete
    bundle* is this project's own sentence, and it is the whole point."""
    log_dir = _log_dir(tmp_path)
    denied = log_dir / "log.txt.1"
    denied.write_text("rotated\n", encoding="utf-8")

    # NOT `chmod(0o000)`: this suite runs as root in CI, and root ignores the
    # permission bits — the test would have passed by never injecting the fault,
    # which is the failure mode this whole file is about. The error is raised
    # directly instead, so the fault is real wherever the suite runs.
    real_read = Path.read_bytes

    def _denied(self: Path) -> bytes:
        if self.name == "log.txt.1":
            raise PermissionError(errno.EACCES, "Permission denied", str(self))
        return real_read(self)

    Path.read_bytes = _denied  # type: ignore[method-assign]
    try:
        result = _build(tmp_path, log_dir=log_dir)
    finally:
        Path.read_bytes = real_read  # type: ignore[method-assign]

    assert result.ok, "one unreadable file took the whole bundle down"
    names = [entry.name for entry in result.skipped]
    assert any("log.txt.1" in n for n in names), (
        f"the unreadable file was dropped SILENTLY; skipped={names}"
    )


def test_a_DESTINATION_THAT_CANNOT_BE_CREATED_is_reported(tmp_path: Path) -> None:
    """The bundle directory itself may be unwritable — a read-only home, a full
    quota. Reported, not raised."""
    blocker = tmp_path / "blocked"
    blocker.write_text("I am a file, not a directory\n", encoding="utf-8")
    result = _build(tmp_path, dest_dir=blocker / "bundles")
    assert not result.ok
    assert result.error


def test_a_VANISHING_file_between_listing_and_reading_is_survived(
    tmp_path: Path,
) -> None:
    """A TOCTOU the real world produces: log rotation deletes a file between the
    directory scan and the read. Common enough that a bundle built during heavy
    logging would hit it, and it must not be fatal."""
    log_dir = _log_dir(tmp_path)
    doomed = log_dir / "log.txt.2"
    doomed.write_text("about to vanish\n", encoding="utf-8")

    real_read = Path.read_bytes

    def _vanish(self: Path) -> bytes:
        if self.name == "log.txt.2":
            self.unlink(missing_ok=True)
            raise FileNotFoundError(
                errno.ENOENT, "No such file or directory", str(self)
            )
        return real_read(self)

    original = Path.read_bytes
    Path.read_bytes = _vanish  # type: ignore[method-assign]
    try:
        result = _build(tmp_path, log_dir=log_dir)
    finally:
        Path.read_bytes = original  # type: ignore[method-assign]

    assert result.ok, "a file disappearing mid-scan took the bundle down"


@pytest.mark.parametrize("size", [0, 1])
def test_a_ZERO_BYTE_or_ONE_BYTE_artifact_is_handled(tmp_path: Path, size: int) -> None:
    """Boundary values on the file itself. A zero-byte log is what a rip killed
    before its first write leaves behind — the case most worth bundling."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / "log.txt").write_bytes(b"x" * size)
    result = _build(tmp_path, log_dir=log_dir)
    assert result.ok, result.error
