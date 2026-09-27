"""Tests for platterpus.logging_setup.

configure_logging() mutates the global root logger and writes under a real
path, so each test snapshots and restores the root logger and points the log
path at a tmp dir.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest

from platterpus import logging_setup


@pytest.fixture
def clean_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Iterator[logging.Logger]:
    """Give each test a fresh, isolated root logger + a tmp log path."""
    log_dir = tmp_path / "logs"
    monkeypatch.setattr(logging_setup, "LOG_DIR", log_dir)
    monkeypatch.setattr(logging_setup, "LOG_PATH", log_dir / "log.txt")

    root = logging.getLogger()
    saved_handlers = root.handlers[:]
    saved_level = root.level
    saved_attr = getattr(root, logging_setup._CONFIGURED_ATTR, None)
    saved_fh = getattr(root, logging_setup._FILE_HANDLER_ATTR, None)
    saved_bh = getattr(root, logging_setup._BUFFER_HANDLER_ATTR, None)

    root.handlers = []
    root.setLevel(logging.WARNING)
    for attr in (
        logging_setup._CONFIGURED_ATTR,
        logging_setup._FILE_HANDLER_ATTR,
        logging_setup._BUFFER_HANDLER_ATTR,
    ):
        if hasattr(root, attr):
            delattr(root, attr)
    try:
        yield root
    finally:
        # Close the handlers this test opened, then restore the original state.
        for handler in root.handlers:
            handler.close()
        root.handlers = saved_handlers
        root.setLevel(saved_level)
        for attr, value in (
            (logging_setup._CONFIGURED_ATTR, saved_attr),
            (logging_setup._FILE_HANDLER_ATTR, saved_fh),
            (logging_setup._BUFFER_HANDLER_ATTR, saved_bh),
        ):
            if value is not None:
                setattr(root, attr, value)
            elif hasattr(root, attr):
                delattr(root, attr)


def _handler_names(root: logging.Logger) -> set[str]:
    return {type(h).__name__ for h in root.handlers}


def test_configure_logging_adds_file_and_console_handlers(
    clean_root: logging.Logger,
) -> None:
    logging_setup.configure_logging(console_level=logging.WARNING)

    # The log directory is created up front.
    assert logging_setup.LOG_DIR.exists()
    names = _handler_names(clean_root)
    # The file handler is our banner-stamping RotatingFileHandler subclass.
    assert any(isinstance(h, RotatingFileHandler) for h in clean_root.handlers)
    assert "StreamHandler" in names  # exact-name match: the console handler
    # Root captures everything; per-handler levels filter.
    assert clean_root.level == logging.DEBUG


def test_console_level_is_honoured(clean_root: logging.Logger) -> None:
    logging_setup.configure_logging(console_level=logging.ERROR)
    console = next(
        h for h in clean_root.handlers if type(h).__name__ == "StreamHandler"
    )
    file_handler = next(
        h for h in clean_root.handlers if isinstance(h, RotatingFileHandler)
    )
    assert console.level == logging.ERROR
    # File defaults to INFO now; debug mode (below) raises it to DEBUG.
    assert file_handler.level == logging.INFO


def test_configure_logging_is_idempotent(clean_root: logging.Logger) -> None:
    # (pytest's own logging plugin may also attach handlers to root, so we
    # assert the count doesn't *increase* on a second call rather than a
    # fixed absolute count.)
    logging_setup.configure_logging()
    count = len(clean_root.handlers)
    # Our two handlers are present after the first call.
    assert any(isinstance(h, RotatingFileHandler) for h in clean_root.handlers)
    assert "StreamHandler" in _handler_names(clean_root)
    # A second call must not pile on duplicate handlers.
    logging_setup.configure_logging()
    assert len(clean_root.handlers) == count


def _file_handler(root: logging.Logger) -> logging.Handler:
    return next(h for h in root.handlers if isinstance(h, RotatingFileHandler))


def test_debug_true_sets_file_handler_to_debug(clean_root: logging.Logger) -> None:
    logging_setup.configure_logging(debug=True)
    assert _file_handler(clean_root).level == logging.DEBUG


def test_set_debug_logging_toggles_file_level(clean_root: logging.Logger) -> None:
    logging_setup.configure_logging()  # file starts at INFO
    fh = _file_handler(clean_root)
    assert fh.level == logging.INFO

    logging_setup.set_debug_logging(True)
    assert fh.level == logging.DEBUG  # verbose for a bug report

    logging_setup.set_debug_logging(False)
    assert fh.level == logging.INFO  # back to lighter logging


def test_set_debug_logging_noop_before_configure(clean_root: logging.Logger) -> None:
    """Calling the toggle before logging is configured must not raise."""
    logging_setup.set_debug_logging(True)  # no file handler yet → no-op
    assert "RotatingFileHandler" not in _handler_names(clean_root)


def test_reconfigure_honours_debug_when_already_configured(
    clean_root: logging.Logger,
) -> None:
    """A second configure_logging(debug=True) (idempotent path) still applies
    the requested verbosity rather than silently keeping INFO."""
    logging_setup.configure_logging()  # INFO
    logging_setup.configure_logging(debug=True)  # idempotent, but re-levels
    assert _file_handler(clean_root).level == logging.DEBUG


def test_installs_session_log_buffer_that_captures_records(
    clean_root: logging.Logger,
) -> None:
    """configure_logging installs the in-memory SessionLogBuffer and exposes it
    via get_session_buffer; it must actually capture emitted records (this is
    what the self-contained rip report embeds)."""
    from platterpus.log_buffer import SessionLogBuffer, get_session_buffer

    logging_setup.configure_logging()

    assert "SessionLogBuffer" in _handler_names(clean_root)
    buffer = get_session_buffer()
    assert isinstance(buffer, SessionLogBuffer)

    logging.getLogger("platterpus.test").info("hello-from-a-test")
    assert any("hello-from-a-test" in line for line in buffer.lines_excluding([]))


def test_session_buffer_is_always_debug_regardless_of_toggle(
    clean_root: logging.Logger,
) -> None:
    """The in-memory buffer is held at DEBUG **always**, independent of the
    Debug-logging setting, so the `.platterpus.json` report is the fully-verbose
    per-album record even with default settings. The toggle governs only the
    on-disk log.txt verbosity — never the buffer."""
    from platterpus.log_buffer import get_session_buffer

    logging_setup.configure_logging()  # log.txt starts at INFO…
    buffer = get_session_buffer()
    fh = _file_handler(clean_root)
    assert buffer.level == logging.DEBUG  # …but the buffer is DEBUG from the start
    assert fh.level == logging.INFO

    logging_setup.set_debug_logging(True)
    assert buffer.level == logging.DEBUG  # unchanged
    assert fh.level == logging.DEBUG  # only the file follows the toggle

    logging_setup.set_debug_logging(False)
    assert buffer.level == logging.DEBUG  # still DEBUG — never lowered
    assert fh.level == logging.INFO


def test_configure_with_debug_still_leaves_buffer_at_debug(
    clean_root: logging.Logger,
) -> None:
    """Even the default (debug=False) start puts the buffer at DEBUG — the report
    must never depend on the user having enabled Debug logging first."""
    from platterpus.log_buffer import get_session_buffer

    logging_setup.configure_logging(debug=False)
    assert get_session_buffer().level == logging.DEBUG


def test_log_file_is_stamped_with_app_and_version_banner(
    clean_root: logging.Logger,
) -> None:
    """Every log.txt is stamped with an app+version banner at the top, so a log
    excerpt in a bug report always says which build wrote it (maintainer's ask)."""
    from platterpus import __version__

    logging_setup.configure_logging()
    text = logging_setup.LOG_PATH.read_text(encoding="utf-8")
    assert "Platterpus" in text
    assert __version__ in text  # the running version is named in the file


def test_rotated_backup_also_gets_the_version_banner(
    clean_root: logging.Logger,
) -> None:
    """A ROTATED backup must carry the banner too — a bug report often attaches a
    backup, not the live file. Forcing a rollover re-stamps the new active file."""
    from platterpus import __version__

    logging_setup.configure_logging()
    fh = _file_handler(clean_root)
    # Force a rollover: the previous file becomes log.txt.1 and a fresh log.txt is
    # opened — which must be re-stamped with the banner.
    fh.doRollover()  # type: ignore[attr-defined]
    logging.getLogger("platterpus.test").info("after-rollover-line")

    backup = logging_setup.LOG_PATH.with_name(logging_setup.LOG_PATH.name + ".1")
    assert backup.exists()
    assert __version__ in backup.read_text(encoding="utf-8")  # the old file
    assert __version__ in logging_setup.LOG_PATH.read_text(encoding="utf-8")  # the new


# ---------------------------------------------------------------------------
# One record, two renderings: the terminal gets a summary, the file the whole
# ---------------------------------------------------------------------------
#
# TASKS (2026-08-15, audited partly done 2026-09-25): `--install-ripper` printed
# its own multi-line `sh -c` build scripts to the terminal, because the step engine
# logs each container command at INFO and the console handler prints INFO. The
# 2180e85 fix put each script on one escaped line, which fixed the FILE and left
# the terminal a line several thousand characters wide.


def test_a_step_engine_script_is_one_short_line_on_the_terminal_and_whole_in_the_file(
    clean_root: logging.Logger, capsys: pytest.CaptureFixture[str]
) -> None:
    """Through the real handlers and the real `SubprocessRunner`, not a stand-in.

    Both halves asserted, because either alone is satisfied by the wrong fix: a
    terminal-only assertion passes against code that dropped the script from the
    log too, which is the diagnostic loss `CLAUDE.md` forbids; a file-only one
    passes against the code this replaced.
    """
    from platterpus.deps.step_engine import SubprocessRunner, one_line_argv
    from platterpus.log_buffer import get_session_buffer

    logging_setup.configure_logging()  # console at INFO, bound to captured stderr
    script = "set -eu\n" + "".join(f"echo step{i}\n" for i in range(40))
    argv = ["sh", "-c", script, "build-cyanrip-fork", "pin-label"]

    rc, out = SubprocessRunner().run(argv)
    assert rc == 0, out
    for handler in clean_root.handlers:
        handler.flush()

    terminal = [
        line for line in capsys.readouterr().err.splitlines() if "host-setup:" in line
    ]
    assert len(terminal) == 1, f"expected one terminal line, got:\n{terminal}"
    line = terminal[0]
    assert "echo step" not in line, f"the script body reached the terminal:\n{line}"
    assert "41-line script" in line, f"the elision is not counted:\n{line}"
    assert "log file" in line, "the terminal is not told where the full text is"
    # The label and the other arguments stay verbatim: they say WHICH script ran.
    assert "build-cyanrip-fork pin-label" in line
    assert len(line) < 300, f"not a summary ({len(line)} chars):\n{line}"

    # The file and the session buffer (the rip report's embedded log) keep the
    # exact argv — every line of the script, escaped onto one log line.
    recorded = one_line_argv(argv)
    assert recorded in logging_setup.LOG_PATH.read_text(encoding="utf-8")
    buffer = get_session_buffer()
    assert buffer is not None
    assert any(recorded in entry for entry in buffer.lines_excluding([]))


def test_the_console_summary_never_leaks_into_the_file(
    clean_root: logging.Logger, capsys: pytest.CaptureFixture[str]
) -> None:
    """The formatter works on a copy. Handlers share one record object, so a
    formatter that edited `record.msg` would hand the summary to every handler
    after it. Today that is the session buffer (the rip report's embedded log),
    because the file handler happens to be added first — so both are checked,
    and the check does not depend on which order the handlers were added in."""
    from platterpus.log_buffer import get_session_buffer

    logging_setup.configure_logging()
    logging.getLogger("platterpus.test").info(
        "FULL-%s", "TEXT", extra=logging_setup.console_summary("SHORT")
    )
    logging.getLogger("platterpus.test").info("plain line with no summary")
    for handler in clean_root.handlers:
        handler.flush()

    err = capsys.readouterr().err
    text = logging_setup.LOG_PATH.read_text(encoding="utf-8")
    assert "SHORT" in err and "FULL-TEXT" not in err
    assert "FULL-TEXT" in text and "SHORT" not in text
    buffer = get_session_buffer()
    assert buffer is not None
    kept = "\n".join(buffer.lines_excluding([]))
    assert "FULL-TEXT" in kept and "SHORT" not in kept, kept[-500:]
    # A record with no summary is printed as it always was.
    assert "plain line with no summary" in err


def test_a_failing_step_shows_its_output_on_the_terminal_but_not_its_script(
    clean_root: logging.Logger, capsys: pytest.CaptureFixture[str]
) -> None:
    """The failure path is when the terminal is actually read.

    What the dependency SAID is the one thing a person watching needs on screen
    (`CLAUDE.md`: show the user the dependency's own sentence), so the bounded
    output stays; only the argv is summarised. The file keeps both whole.
    """
    from platterpus.deps.step_engine import SubprocessRunner, one_line_argv

    logging_setup.configure_logging()
    script = "set -eu\necho the-dependency-says-why >&2\nexit 3\n"
    argv = ["sh", "-c", script, "verify-cyanrip-fork"]

    rc, _ = SubprocessRunner().run(argv)
    assert rc == 3
    for handler in clean_root.handlers:
        handler.flush()

    err = capsys.readouterr().err
    assert "exit 3 from sh -c <3-line script" in err, err
    assert "the-dependency-says-why" in err, "the failure's own sentence is missing"
    assert "set -eu" not in err, f"the script body reached the terminal:\n{err}"
    text = logging_setup.LOG_PATH.read_text(encoding="utf-8")
    assert f"exit 3 from {one_line_argv(argv)}" in text
    assert "the-dependency-says-why" in text
