"""Tests for platterpus.logging_setup.

configure_logging() mutates the global root logger and writes under a real
path, so each test snapshots and restores the root logger and points the log
path at a tmp dir.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
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

    root.handlers = []
    root.setLevel(logging.WARNING)
    for attr in (logging_setup._CONFIGURED_ATTR, logging_setup._FILE_HANDLER_ATTR):
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
    assert "RotatingFileHandler" in names
    assert "StreamHandler" in names  # exact-name match: the console handler
    # Root captures everything; per-handler levels filter.
    assert clean_root.level == logging.DEBUG


def test_console_level_is_honoured(clean_root: logging.Logger) -> None:
    logging_setup.configure_logging(console_level=logging.ERROR)
    console = next(
        h for h in clean_root.handlers if type(h).__name__ == "StreamHandler"
    )
    file_handler = next(
        h for h in clean_root.handlers if type(h).__name__ == "RotatingFileHandler"
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
    assert "RotatingFileHandler" in _handler_names(clean_root)
    assert "StreamHandler" in _handler_names(clean_root)
    # A second call must not pile on duplicate handlers.
    logging_setup.configure_logging()
    assert len(clean_root.handlers) == count


def _file_handler(root: logging.Logger) -> logging.Handler:
    return next(h for h in root.handlers if type(h).__name__ == "RotatingFileHandler")


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
