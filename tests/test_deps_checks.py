"""Tests for platterpus.deps.checks.

The probes shell out to real tools, so we test by patching `shutil.which` and
`checks.VERSION_PROBE.run` to deterministic stubs. (The probe goes through the
killable `VERSION_PROBE`, **not** `subprocess.run` — patching the latter would
stub something the code no longer calls, and the test would pass while proving
nothing.) The shape of each ProbeResult is what we care about — not whether
cyanrip itself runs.
"""

from __future__ import annotations

import subprocess
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from platterpus.deps import checks
from platterpus.deps.checks import (
    ProbeResult,
    check_cdparanoia,
    check_cyanrip,
    check_ffmpeg,
    check_flac,
    check_metaflac,
    check_picard_flatpak,
    check_python_pkg,
)


def _fake_run(stdout: str = "", stderr: str = "", returncode: int = 0) -> Any:
    """Build a fake `subprocess.run` return value."""
    return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)


# --- check_cyanrip ---


def test_check_cyanrip_missing_when_binary_absent(tmp_path: Path) -> None:
    probe = check_cyanrip(tmp_path / "does-not-exist")
    assert probe.present is False
    assert probe.version is None


def test_check_cyanrip_parses_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    binary = tmp_path / "cyanrip"
    binary.write_text("#!/bin/sh\necho 'cyanrip 0.9.3'\n")
    binary.chmod(0o755)

    monkeypatch.setattr(
        checks.VERSION_PROBE,
        "run",
        lambda *a, **kw: _fake_run(stdout="cyanrip 0.9.3\n"),
    )

    probe = check_cyanrip(binary)
    assert probe.present is True
    assert probe.version == (0, 9, 3)
    assert probe.location == str(binary)


def test_check_cyanrip_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    binary = tmp_path / "cyanrip"
    binary.write_text("#!/bin/sh\nsleep 60\n")
    binary.chmod(0o755)

    def boom(*a: Any, **kw: Any) -> Any:
        raise subprocess.TimeoutExpired(cmd="cyanrip", timeout=10)

    monkeypatch.setattr(checks.VERSION_PROBE, "run", boom)

    probe = check_cyanrip(binary)
    assert probe.present is False
    assert probe.version is None


def test_probe_timeout_budgets_for_cold_container() -> None:
    """The launch probe timeout must tolerate a Distrobox container cold-start.

    Regression guard (real-user report, Bazzite + BDR-209D, 2026-06-27): the
    first `whipper --version` of a session starts the `ripping` container, which
    can take tens of seconds. The old 10s cap made a cold container look like a
    MISSING whipper at launch and left it cold for the disc scan. Keep this
    high enough that the launch probe waits for the container to come up (which
    also warms it for the scan that follows). Native-binary probes return in ms
    regardless, so the larger ceiling only bites a cold-start or a wedged tool.
    """
    assert checks._PROBE_TIMEOUT_S >= 45.0


# --- exit-code handling (regression: a failed probe is not a version) -------
#
# The bug: `_run_version_command` reported success for any run that *finished*,
# so the error text of a broken tool was parsed for a version. `parse_version`
# takes the first `N.N` it finds, and error text is full of them — a podman
# version in a Distrobox failure, a SONAME in a linker error. The dependency
# report then claimed a broken tool was installed AND that it met its minimum
# version, so nothing offered to fix it. These tests pin the exit code as the
# thing that decides whether the tool answered us.


def test_check_cdparanoia_nonzero_exit_is_absent_despite_version_like_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A linker error mentioning `libcdio.so.19.0` must not become "version 19.0".

    This is the exact reported shape: the binary exists (so the `exists()` gate
    passes), the run completes (so the old code said "ran OK"), and the only
    numbers in the output belong to a shared library, not to cd-paranoia.
    """
    binary = tmp_path / "cd-paranoia"
    binary.write_text("#!/bin/sh\nexit 127\n")
    binary.chmod(0o755)
    monkeypatch.setattr(
        checks.VERSION_PROBE,
        "run",
        lambda *a, **kw: _fake_run(
            stderr=(
                "cd-paranoia: error while loading shared libraries: "
                "libcdio.so.19.0: cannot open shared object file\n"
            ),
            returncode=127,
        ),
    )

    probe = check_cdparanoia(binary)
    assert probe.present is False
    # The specific trap: not merely "not present" but not carrying the
    # library's version number either — a consumer reading `version` must not
    # find (19, 0) sitting there.
    assert probe.version is None


def test_check_cyanrip_nonzero_exit_is_absent_despite_podman_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A Distrobox/podman failure prints podman's version — not cyanrip's.

    The host export is a shell script that enters the container, so it runs and
    prints even when the container is broken. Reporting cyanrip as present at
    podman's version (and above cyanrip's 0.9.0 floor) is the worst outcome:
    the setup wizard that would fix the container never gets offered.
    """
    binary = tmp_path / "cyanrip"
    binary.write_text("#!/bin/sh\nexit 125\n")
    binary.chmod(0o755)
    monkeypatch.setattr(
        checks.VERSION_PROBE,
        "run",
        lambda *a, **kw: _fake_run(
            stderr=(
                "Error: unable to start container ripping: "
                "podman 4.9.4 reported: OCI runtime error\n"
            ),
            returncode=125,
        ),
    )

    probe = check_cyanrip(binary)
    assert probe.present is False
    assert probe.version is None


def test_check_metaflac_nonzero_exit_is_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same rule for the PATH-resolved probes, not just the path-gated ones."""
    monkeypatch.setattr(checks.shutil, "which", lambda _: "/usr/bin/metaflac")
    monkeypatch.setattr(
        checks.VERSION_PROBE,
        "run",
        lambda *a, **kw: _fake_run(
            stderr="metaflac: symbol lookup error: libFLAC.so.12.1\n", returncode=1
        ),
    )

    probe = check_metaflac()
    assert probe.present is False
    assert probe.version is None


def test_killed_probe_is_absent_not_a_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A probe WE killed must never read as an answer.

    `cancel_version_probes()` SIGKILLs the child, which surfaces as a negative
    return code with whatever the tool had already written. Partial output can
    absolutely contain a version-like number, so the cancel path relies on the
    same exit-code rule.
    """
    monkeypatch.setattr(checks.shutil, "which", lambda _: "/usr/bin/ffmpeg")
    monkeypatch.setattr(
        checks.VERSION_PROBE,
        "run",
        lambda *a, **kw: _fake_run(stdout="ffmpeg version 6.1.1", returncode=-9),
    )

    probe = check_ffmpeg()
    assert probe.present is False
    assert probe.version is None


def test_failed_probe_logs_exit_code_and_captured_output(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """A failed probe must be diagnosable from the log file alone.

    CLAUDE.md: when a dependency fails, capture its stderr/stdout and log it.
    Without this, "cd-paranoia is missing" in the UI has no explanation anywhere
    and a bug report cannot say *why* the tool was rejected.
    """
    monkeypatch.setattr(checks.shutil, "which", lambda _: "/usr/bin/flac")
    monkeypatch.setattr(
        checks.VERSION_PROBE,
        "run",
        lambda *a, **kw: _fake_run(
            stderr="flac: error while loading shared libraries: libogg.so.0\n",
            returncode=127,
        ),
    )

    with caplog.at_level("WARNING", logger="platterpus.deps.checks"):
        assert check_flac().present is False

    logged = caplog.text
    assert "127" in logged  # the exit code
    assert "libogg.so.0" in logged  # the tool's own words, not swallowed


def test_version_probe_accepts_an_explicitly_allow_listed_exit_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The allow-list seam works, for the day a tool needs it.

    Non-zero-on-`--version` is a real upstream convention: libcdio's shared
    `print_version()` exits `EXIT_INFO` (100). No dependency Platterpus probes
    does that today (all were checked against upstream source), so nothing
    passes this parameter — but the seam is tested so that a future fix is an
    explicit per-tool allow-list rather than a relapse into accepting every
    exit code.
    """
    monkeypatch.setattr(checks.shutil, "which", lambda _: "/usr/bin/cd-info")
    monkeypatch.setattr(
        checks.VERSION_PROBE,
        "run",
        # libcdio's own shape: a good banner, then exit(EXIT_INFO) == 100.
        lambda *a, **kw: _fake_run(stdout="cd-info version 10.2\n", returncode=100),
    )

    # Not allow-listed → rejected, which is the default every real caller uses.
    ran_default, _output, _loc = checks._run_version_command(["cd-info", "--version"])
    assert ran_default is False

    ran, output, location = checks._run_version_command(
        ["cd-info", "--version"],
        accept_exit_codes=frozenset({0, 100}),
    )
    assert ran is True
    assert "10.2" in output
    assert location == "/usr/bin/cd-info"


def test_summarize_output_flattens_and_bounds_what_reaches_the_log() -> None:
    """The log line stays one readable, bounded line.

    Empty output is spelled out (a blank tail looks like a truncated log line),
    newlines are flattened so one failure is one grep-able record, and a tool
    that spews megabytes cannot bloat the user's log file.
    """
    assert checks._summarize_output("   \n\n ") == "(none)"
    assert checks._summarize_output("first\nsecond\n") == "first | second"

    summary = checks._summarize_output("x" * (checks._MAX_LOGGED_OUTPUT_CHARS + 50))
    assert summary.endswith("(truncated)")
    # Bounded: the payload is capped, plus the short truncation marker.
    assert len(summary) < checks._MAX_LOGGED_OUTPUT_CHARS + 30


# --- check_cdparanoia (KDD-29) ---


def test_check_cdparanoia_missing_when_binary_absent(tmp_path: Path) -> None:
    probe = check_cdparanoia(tmp_path / "does-not-exist")
    assert probe.present is False
    assert probe.version is None


def test_check_cdparanoia_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    binary = tmp_path / "cd-paranoia"
    binary.write_text("#!/bin/sh\necho 'cdda paranoia III release 10.2'\n")
    binary.chmod(0o755)
    monkeypatch.setattr(
        checks.VERSION_PROBE,
        "run",
        lambda *a, **kw: _fake_run(stdout="cdda paranoia III release 10.2\n"),
    )
    probe = check_cdparanoia(binary)
    assert probe.present is True
    assert probe.location == str(binary)


def test_check_cdparanoia_timeout_is_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    binary = tmp_path / "cd-paranoia"
    binary.write_text("#!/bin/sh\nsleep 99\n")
    binary.chmod(0o755)

    def boom(*a: Any, **kw: Any) -> Any:
        raise subprocess.TimeoutExpired(cmd="cd-paranoia", timeout=60)

    monkeypatch.setattr(checks.VERSION_PROBE, "run", boom)
    assert check_cdparanoia(binary).present is False


# --- check_metaflac ---


def test_check_metaflac_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(checks.shutil, "which", lambda _: None)

    def not_found(*a: Any, **kw: Any) -> Any:
        raise FileNotFoundError

    monkeypatch.setattr(checks.VERSION_PROBE, "run", not_found)

    probe = check_metaflac()
    assert probe.present is False


def test_check_metaflac_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(checks.shutil, "which", lambda _: "/usr/bin/metaflac")
    monkeypatch.setattr(
        checks.VERSION_PROBE,
        "run",
        lambda *a, **kw: _fake_run(stdout="metaflac 1.4.3\n"),
    )

    probe = check_metaflac()
    assert probe.present is True
    assert probe.version == (1, 4, 3)
    assert probe.location == "/usr/bin/metaflac"


# --- check_flac ---


def test_check_flac_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(checks.shutil, "which", lambda _: None)

    def not_found(*a: Any, **kw: Any) -> Any:
        raise FileNotFoundError

    monkeypatch.setattr(checks.VERSION_PROBE, "run", not_found)

    probe = check_flac()
    assert probe.present is False


def test_check_flac_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(checks.shutil, "which", lambda _: "/usr/bin/flac")
    monkeypatch.setattr(
        checks.VERSION_PROBE,
        "run",
        lambda *a, **kw: _fake_run(stdout="flac 1.4.3\n"),
    )

    probe = check_flac()
    assert probe.present is True
    assert probe.version == (1, 4, 3)
    assert probe.location == "/usr/bin/flac"


# --- check_ffmpeg ---


def test_check_ffmpeg_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(checks.shutil, "which", lambda _: None)

    def not_found(*a: Any, **kw: Any) -> Any:
        raise FileNotFoundError

    monkeypatch.setattr(checks.VERSION_PROBE, "run", not_found)

    probe = check_ffmpeg()
    assert probe.present is False
    assert probe.version is None


def test_check_ffmpeg_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(checks.shutil, "which", lambda _: "/usr/bin/ffmpeg")
    captured: dict[str, Any] = {}

    def fake_run(argv: Any, *a: Any, **kw: Any) -> Any:
        captured["argv"] = argv
        # ffmpeg prints its banner to the version flag.
        return _fake_run(stdout="ffmpeg version 6.1.1-3ubuntu5 Copyright (c)\n")

    monkeypatch.setattr(checks.VERSION_PROBE, "run", fake_run)

    probe = check_ffmpeg()
    assert probe.present is True
    assert probe.version == (6, 1, 1)
    assert probe.location == "/usr/bin/ffmpeg"
    # ffmpeg uses single-dash `-version`, not GNU `--version`.
    assert captured["argv"] == ["ffmpeg", "-version"]


# --- check_picard_flatpak ---


def test_check_picard_flatpak_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(checks.shutil, "which", lambda _: "/usr/bin/flatpak")
    output = (
        "MusicBrainz Picard - Picard\n"
        "ID:      org.musicbrainz.Picard\n"
        "Version: 2.11.0\n"
    )
    monkeypatch.setattr(
        checks.VERSION_PROBE, "run", lambda *a, **kw: _fake_run(stdout=output)
    )

    probe = check_picard_flatpak()
    assert probe.present is True
    assert probe.version == (2, 11, 0)


def test_check_picard_flatpak_not_installed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(checks.shutil, "which", lambda _: "/usr/bin/flatpak")
    # `flatpak info` for a missing app prints to stderr without "Version:".
    monkeypatch.setattr(
        checks.VERSION_PROBE,
        "run",
        lambda *a, **kw: _fake_run(
            stdout="",
            stderr="error: org.musicbrainz.Picard not installed\n",
            returncode=1,
        ),
    )

    probe = check_picard_flatpak()
    assert probe.present is False


# --- check_python_pkg ---


def test_check_python_pkg_present() -> None:
    # `pytest` is definitely installed when this test runs.
    probe = check_python_pkg("pytest")
    assert probe.present is True
    assert probe.version is not None
    assert probe.location == "python: pytest"


def test_check_python_pkg_missing() -> None:
    probe = check_python_pkg("this-package-does-not-exist-9c8a")
    assert probe.present is False
    assert probe.version is None


# --- ProbeResult dataclass shape ---


def test_probe_result_is_frozen() -> None:
    probe = ProbeResult(present=True, version=(0, 1, 0), location="/x")
    with pytest.raises(FrozenInstanceError):
        probe.present = False  # type: ignore[misc]


# --- check_libdiscid (ctypes-driven; monkeypatch the loader) --------------


def test_check_libdiscid_absent_when_no_variant_loads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No SONAME resolves / loads → present=False (the documented default;
    whipper computes the disc ID in-container, so this is the common case)."""
    import ctypes
    import ctypes.util

    monkeypatch.setattr(ctypes.util, "find_library", lambda _name: None)

    def no_load(_name: str):
        raise OSError("not found")

    monkeypatch.setattr(ctypes, "CDLL", no_load)

    result = checks.check_libdiscid()
    assert result.present is False
    assert result.version is None
    assert result.location is None


def test_check_libdiscid_present_with_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A SONAME that loads and answers discid_get_version_string() → present,
    with the parsed version and the SONAME as the location."""
    import ctypes
    import ctypes.util

    monkeypatch.setattr(ctypes.util, "find_library", lambda _name: "libdiscid.so.0")

    class _FakeLib:
        class discid_get_version_string:  # noqa: N801 — mimics a ctypes func
            restype = None

            def __call__(self) -> bytes:
                return b"libdiscid 0.6.2"

        def __init__(self) -> None:
            # ctypes accesses lib.discid_get_version_string as an attribute
            # and sets .restype on it, then calls it — model that.
            self.discid_get_version_string = _FakeLib.discid_get_version_string()

    monkeypatch.setattr(ctypes, "CDLL", lambda _name: _FakeLib())

    result = checks.check_libdiscid()
    assert result.present is True
    assert result.location == "libdiscid.so.0"
    assert result.version is not None  # parse_version extracted something


def test_check_libdiscid_present_but_version_call_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Library loads but the version symbol is missing → still present, with
    an empty version string (the AttributeError branch)."""
    import ctypes
    import ctypes.util

    monkeypatch.setattr(ctypes.util, "find_library", lambda _name: None)

    class _NoVersionLib:
        def __getattr__(self, _name: str):  # any symbol access raises
            raise AttributeError("no such symbol")

    monkeypatch.setattr(ctypes, "CDLL", lambda _name: _NoVersionLib())

    result = checks.check_libdiscid()
    assert result.present is True
    assert result.raw_output == ""
