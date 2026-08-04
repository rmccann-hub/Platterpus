"""Tests for platterpus.adapters.metaflac.

`metaflac` is shelled out at runtime; tests monkeypatch subprocess so
they're hermetic and don't require a real metaflac install.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from platterpus import diagnostics
from platterpus.adapters import metaflac as metaflac_module
from platterpus.adapters.metaflac import MetaflacAdapter, MetaflacError


def _ok(stdout: str = "") -> Any:
    return SimpleNamespace(stdout=stdout, stderr="", returncode=0)


def _fail(stderr: str = "boom\n") -> Any:
    return SimpleNamespace(stdout="", stderr=stderr, returncode=1)


# --- read_tags ------------------------------------------------------------


def test_read_tags_parses_key_value_lines(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sample = (
        "ARTIST=Pink Floyd\n"
        "TITLE=Speak to Me\n"
        "ALBUM=The Dark Side of the Moon\n"
        "TRACKNUMBER=01\n"
    )
    captured: list[list[str]] = []

    def fake_run(argv: list[str], **kw: Any) -> Any:
        captured.append(argv)
        return _ok(stdout=sample)

    monkeypatch.setattr(metaflac_module.subprocess, "run", fake_run)

    adapter = MetaflacAdapter()
    tags = adapter.read_tags(Path("/x/track.flac"))

    assert tags == {
        "ARTIST": "Pink Floyd",
        "TITLE": "Speak to Me",
        "ALBUM": "The Dark Side of the Moon",
        "TRACKNUMBER": "01",
    }
    assert captured[0] == ["metaflac", "--export-tags-to=-", "/x/track.flac"]


def test_read_tags_ignores_lines_without_equals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sample = "ARTIST=Pink Floyd\ngarbage-line-without-equals\nTITLE=Track\n"
    monkeypatch.setattr(
        metaflac_module.subprocess, "run", lambda *a, **kw: _ok(stdout=sample)
    )

    tags = MetaflacAdapter().read_tags(Path("/x/track.flac"))

    assert tags == {"ARTIST": "Pink Floyd", "TITLE": "Track"}


def test_read_tags_duplicate_keys_keep_last_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sample = "ARTIST=First\nARTIST=Second\n"
    monkeypatch.setattr(
        metaflac_module.subprocess, "run", lambda *a, **kw: _ok(stdout=sample)
    )

    tags = MetaflacAdapter().read_tags(Path("/x/track.flac"))

    assert tags == {"ARTIST": "Second"}


# --- write_tags -----------------------------------------------------------


def test_write_tags_emits_remove_then_set_for_each_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[list[str]] = []

    def fake_run(argv: list[str], **kw: Any) -> Any:
        captured.append(argv)
        return _ok()

    monkeypatch.setattr(metaflac_module.subprocess, "run", fake_run)

    MetaflacAdapter().write_tags(
        Path("/x/track.flac"),
        {"ARTIST": "Pink Floyd", "TITLE": "Breathe"},
    )

    argv = captured[0]
    assert argv[0] == "metaflac"
    # All --remove-tag come before all --set-tag.
    remove_indices = [i for i, a in enumerate(argv) if a.startswith("--remove-tag")]
    set_indices = [i for i, a in enumerate(argv) if a.startswith("--set-tag")]
    assert all(r < s for r in remove_indices for s in set_indices)
    # Path is last.
    assert argv[-1] == "/x/track.flac"
    # Both keys appear in remove and set forms.
    assert "--remove-tag=ARTIST" in argv
    assert "--remove-tag=TITLE" in argv
    assert "--set-tag=ARTIST=Pink Floyd" in argv
    assert "--set-tag=TITLE=Breathe" in argv


def test_write_tags_is_noop_for_empty_dict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called: list[bool] = []

    def fake_run(*a: Any, **kw: Any) -> Any:
        called.append(True)
        return _ok()

    monkeypatch.setattr(metaflac_module.subprocess, "run", fake_run)

    MetaflacAdapter().write_tags(Path("/x/track.flac"), {})

    assert called == []


# --- Error handling -------------------------------------------------------


def test_read_tags_raises_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        metaflac_module.subprocess,
        "run",
        lambda *a, **kw: _fail(stderr="ERROR: bad FLAC\n"),
    )

    with pytest.raises(MetaflacError) as info:
        MetaflacAdapter().read_tags(Path("/x/bad.flac"))
    assert "bad FLAC" in str(info.value)


def test_raises_when_metaflac_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    def not_found(*a: Any, **kw: Any) -> Any:
        raise FileNotFoundError("metaflac")

    monkeypatch.setattr(metaflac_module.subprocess, "run", not_found)

    with pytest.raises(MetaflacError) as info:
        MetaflacAdapter().read_tags(Path("/x/track.flac"))
    assert "not found" in str(info.value)


def test_raises_on_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*a: Any, **kw: Any) -> Any:
        raise subprocess.TimeoutExpired(cmd="metaflac", timeout=30)

    monkeypatch.setattr(metaflac_module.subprocess, "run", boom)

    with pytest.raises(MetaflacError) as info:
        MetaflacAdapter().read_tags(Path("/x/track.flac"))
    assert "timed out" in str(info.value)


# --- Constructor with custom binary --------------------------------------


def test_custom_binary_path_is_honored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[list[str]] = []

    def fake_run(argv: list[str], **kw: Any) -> Any:
        captured.append(argv)
        return _ok()

    monkeypatch.setattr(metaflac_module.subprocess, "run", fake_run)

    MetaflacAdapter(binary_name="/opt/flac/bin/metaflac").read_tags(
        Path("/x/track.flac")
    )
    assert captured[0][0] == "/opt/flac/bin/metaflac"


# --- embed_picture ----------------------------------------------------------


def test_embed_picture_removes_old_pictures_then_imports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Re-running must replace the cover, not stack a duplicate PICTURE
    block (players show whichever block they find first)."""
    captured: list[list[str]] = []

    def fake_run(argv: list[str], **kw: Any) -> Any:
        captured.append(argv)
        return _ok()

    monkeypatch.setattr(metaflac_module.subprocess, "run", fake_run)

    MetaflacAdapter().embed_picture(Path("/x/track.flac"), Path("/x/cover.jpg"))

    assert captured == [
        ["metaflac", "--remove", "--block-type=PICTURE", "/x/track.flac"],
        ["metaflac", "--import-picture-from=/x/cover.jpg", "/x/track.flac"],
    ]


def test_embed_picture_raises_metaflac_error_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        metaflac_module.subprocess, "run", lambda *a, **kw: _fail("bad image\n")
    )
    with pytest.raises(MetaflacError):
        MetaflacAdapter().embed_picture(Path("/x/t.flac"), Path("/x/c.jpg"))


# --- Diagnostic completeness (2026-08-04) ---------------------------------
#
# `metaflac` runs on EVERY rip — it is how the user's edited tags reach the FLAC
# and how the cover art is embedded — and every failure path used to log NOTHING.
# `MetaflacError` carried a message built from the last stderr line; the argv, the
# exit code and the rest of the output were discarded at the point of failure, and
# three of the six call sites then reduced the exception to a one-line warning.
# These tests pin all four facts CLAUDE.md's diagnostic-completeness rule requires.


def test_a_failure_records_argv_exit_code_and_complete_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    diagnostics.clear()
    monkeypatch.setattr(
        metaflac_module.subprocess,
        "run",
        lambda *a, **kw: SimpleNamespace(
            stdout="scanning\n",
            stderr="metaflac: ERROR: unsupported block type\n",
            returncode=1,
            args=["metaflac", "--set-tag=X=1", "/x/t.flac"],
        ),
    )

    with pytest.raises(MetaflacError) as caught:
        MetaflacAdapter().write_tags(Path("/x/t.flac"), {"X": "1"})

    exc = caught.value
    # (1) on the exception, so a caller can render any of it
    assert exc.exit_code == 1
    assert exc.argv[0] == "metaflac"
    assert "/x/t.flac" in exc.argv
    assert "unsupported block type" in exc.output
    assert "scanning" in exc.output  # COMPLETE output, stderr merged — not a tail
    assert "exited 1" in str(exc)

    # (2) and in the diagnostics collector, BEFORE the raise — so the evidence
    # exists whether or not the caller chooses to log the exception.
    items = diagnostics.default_log().items()
    assert [i.code for i in items] == ["metaflac.failed"]
    recorded = items[0]
    assert recorded.severity == "error"
    assert recorded.tool == "metaflac"
    assert recorded.exit_code == 1
    assert "/x/t.flac" in recorded.argv
    assert "unsupported block type" in recorded.detail
    diagnostics.clear()


def test_a_timeout_names_the_duration_and_reaps_no_exit_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tri-state: a killed child has NO exit code, and must never read as 0."""
    diagnostics.clear()

    def boom(*a: Any, **kw: Any) -> Any:
        raise subprocess.TimeoutExpired(cmd="metaflac", timeout=30, output="partial\n")

    monkeypatch.setattr(metaflac_module.subprocess, "run", boom)

    with pytest.raises(MetaflacError) as caught:
        MetaflacAdapter().read_tags(Path("/x/t.flac"))

    assert caught.value.exit_code is None
    assert "30s" in str(caught.value)  # the duration exceeded is NAMED
    assert "partial" in caught.value.output  # what it managed to say survives
    assert diagnostics.default_log().items()[0].exit_code is None
    diagnostics.clear()


def test_an_oserror_becomes_a_metaflac_error_not_a_raw_oserror(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Was uncaught: an EACCES escaped as `OSError` from an adapter documented to
    raise `MetaflacError`, so every caller's `except MetaflacError` missed it."""
    diagnostics.clear()

    def boom(*a: Any, **kw: Any) -> Any:
        raise OSError("permission denied")

    monkeypatch.setattr(metaflac_module.subprocess, "run", boom)

    with pytest.raises(MetaflacError, match="could not run metaflac"):
        MetaflacAdapter().read_tags(Path("/x/t.flac"))
    assert diagnostics.default_log().count() == 1
    diagnostics.clear()


def test_stdin_is_never_inherited(monkeypatch: pytest.MonkeyPatch) -> None:
    """A metaflac that decided to prompt would block forever in a GUI process with
    no terminal, and "hung with no explanation" is the least diagnosable failure."""
    seen: list[dict[str, Any]] = []

    def fake_run(argv: list[str], **kw: Any) -> Any:
        seen.append(kw)
        return _ok()

    monkeypatch.setattr(metaflac_module.subprocess, "run", fake_run)
    MetaflacAdapter().read_tags(Path("/x/t.flac"))
    assert seen[0]["stdin"] is subprocess.DEVNULL
