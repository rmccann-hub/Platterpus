"""Shared pytest fixtures for whipper-gui's test suite.

Only one QApplication instance can exist per process. The `qapp`
session-scoped fixture guarantees that — tests that need a Qt event
loop, widgets, or the clipboard depend on it; tests that don't, ignore
it.

We force the Qt platform plugin to `offscreen` BEFORE importing any
Qt module, so the suite runs on CI / headless containers without a
real display.
"""

from __future__ import annotations

import os

# Set before any Qt import. Subsequent imports of QtGui/QtWidgets
# inherit this platform choice; widgets are created in-memory and
# never draw to a real display.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """Return the single QApplication instance for the test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app  # type: ignore[return-value]
