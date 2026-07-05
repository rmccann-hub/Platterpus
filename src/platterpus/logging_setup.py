"""Logging configuration for the GUI.

Call `configure_logging()` once at startup (from `app.main`). After that,
every module that does `logging.getLogger(__name__).info(...)` writes to
three destinations:

  1. A rotating file at `LOG_PATH` — INFO by default, DEBUG when the
     "Debug logging" setting is on (`set_debug_logging`). The always-on,
     cross-session catch-all for problems with no rip folder to attach to.
  2. The console (INFO and up, configurable).
  3. An in-memory `SessionLogBuffer` — **always DEBUG**, independent of the
     toggle. It's the sole source for the `.platterpus.json` rip report's
     embedded log, so that per-album debug record is always fully verbose
     (it lives only in memory and is bounded, so DEBUG here is free).

Modules MUST NOT add their own handlers or call `logging.basicConfig` —
configuration is centralized here per CLAUDE.md's "Log with the `logging`
module, not `print`" rule. New code that wants extra detail just logs at
DEBUG: it always reaches the rip report, and reaches log.txt when the
Debug-logging setting is on.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from platterpus.log_buffer import SessionLogBuffer, set_session_buffer
from platterpus.paths import LOG_DIR, LOG_PATH

# Rotation policy. Five backups of 1 MiB each keeps a useful history
# (~5 MiB total) without growing unbounded on long-running sessions.
_LOG_MAX_BYTES: int = 1_048_576
_LOG_BACKUP_COUNT: int = 5

# Format chosen to be greppable by tail/less without being noisy in the
# console pane. Module name (%(name)s) makes it easy to track which
# subsystem emitted a line.
_LOG_FORMAT: str = "%(asctime)s %(levelname)s %(name)s: %(message)s"

# Sentinel attribute set on the root logger after configure_logging()
# runs once, so repeated imports during tests or re-entries don't pile
# up duplicate handlers.
_CONFIGURED_ATTR: str = "_platterpus_configured"
# Tag the file handler so `set_debug_logging()` can find it again after
# configure_logging() returns (handlers are otherwise anonymous).
_FILE_HANDLER_ATTR: str = "_platterpus_file_handler"
# Same idea for the in-memory session buffer (embedded in the rip report).
_BUFFER_HANDLER_ATTR: str = "_platterpus_buffer_handler"


def configure_logging(console_level: int = logging.INFO, debug: bool = False) -> None:
    """Initialize the root logger with a rotating file and a console handler.

    Idempotent: a second call only re-applies the requested verbosity. Safe to
    call before any other module logs (it's the very first thing `app.main`
    does).

    `console_level` controls how chatty the terminal is. The file handler is at
    INFO by default; `debug=True` (the Settings "Debug logging" toggle,
    `Config.debug_logging`) bumps it to DEBUG so a bug report captures every
    probe/subprocess/parse step. Toggle later at runtime with
    `set_debug_logging()`.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    if getattr(root, _CONFIGURED_ATTR, False):
        # Already configured (e.g. a second QApplication in tests) — still
        # honour the requested verbosity.
        set_debug_logging(debug)
        return

    # Root captures everything; per-handler levels do the filtering.
    root.setLevel(logging.DEBUG)

    formatter = logging.Formatter(_LOG_FORMAT)

    file_handler = RotatingFileHandler(
        LOG_PATH,
        maxBytes=_LOG_MAX_BYTES,
        backupCount=_LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)

    # In-memory session buffer: ALWAYS DEBUG, independent of the file handler and
    # the Debug-logging toggle. Rationale: this buffer is the SOLE source for the
    # `.platterpus.json` report's embedded log, whose whole job is to be "verbose
    # enough to debug a rip from alone." It lives only in memory (no second file
    # on disk) and is bounded (see SessionLogBuffer's record cap), so capturing
    # DEBUG here is free. Pinning it to the file handler's level meant a
    # default-settings bug report shipped a JSON missing every subprocess/probe/
    # parse DEBUG line — the "not verbose enough" gap. The report is now always
    # fully verbose; the toggle below governs only how chatty log.txt is on disk.
    buffer_handler = SessionLogBuffer()
    buffer_handler.setLevel(logging.DEBUG)
    buffer_handler.setFormatter(formatter)

    root.addHandler(file_handler)
    root.addHandler(console_handler)
    root.addHandler(buffer_handler)

    # Quiet third-party libraries that log chatter at INFO/DEBUG. musicbrainzngs
    # emits ~40 "in <ws2:artist>, uncaught attribute type-id" lines per release
    # lookup (harmless XML-schema notes) — they flooded both log.txt and the
    # rip report's embedded debug log (real rip: 40+ noise lines). Pin it to
    # WARNING so our own DEBUG stays readable; a real MB error still shows.
    logging.getLogger("musicbrainzngs").setLevel(logging.WARNING)

    # Remember the file + buffer handlers so the runtime toggle can re-level
    # both, and expose the buffer to the report builder.
    setattr(root, _FILE_HANDLER_ATTR, file_handler)
    setattr(root, _BUFFER_HANDLER_ATTR, buffer_handler)
    set_session_buffer(buffer_handler)
    # Mark configured so subsequent calls bail out early.
    setattr(root, _CONFIGURED_ATTR, True)


def set_debug_logging(enabled: bool) -> None:
    """Raise/lower the FILE log's verbosity at runtime (the Settings toggle).

    DEBUG when enabled, INFO otherwise; the console level is left alone. A
    no-op if logging hasn't been configured yet (configure_logging applies the
    initial level itself).
    """
    root = logging.getLogger()
    file_handler = getattr(root, _FILE_HANDLER_ATTR, None)
    if file_handler is None:
        return
    file_handler.setLevel(logging.DEBUG if enabled else logging.INFO)
    # The in-memory buffer is deliberately NOT re-leveled here: it stays at DEBUG
    # always (set in configure_logging) so the `.platterpus.json` report is the
    # fully-verbose per-album record regardless of this toggle — which now governs
    # only log.txt's on-disk verbosity.
    logging.getLogger(__name__).info(
        "debug logging %s", "ENABLED" if enabled else "disabled"
    )
