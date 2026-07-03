"""Drive picker widget.

A small horizontal panel: label + dropdown of detected drives + Refresh.
Populates from `RipBackend.list_drives()`; emits `drive_changed`
when the selection changes.

The backend's list_drives() call shells out to the ripper (which enters the
Distrobox container — slow on a cold start). The Refresh button routes through
an injected off-GUI-thread refresh when one is set (`set_async_refresh`, wired
by MainWindow to its threaded `refresh_drives`), so a cold container can't
freeze the window; standalone (no callback) it falls back to the synchronous
`refresh()`.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from platterpus.adapters.rip_backend import RipBackend, RipError
from platterpus.parsers.drive_list import DriveDescriptor

log = logging.getLogger(__name__)


class DrivePicker(QWidget):
    """A drop-down listing drives the backend can see.

    Signals:
      drive_changed(str) — emitted when the selected device path changes
                           (including initial population, when one or
                           more drives become available).
    """

    drive_changed = Signal(str)
    # Emitted when a refresh finds zero drives (not on backend errors,
    # which are a different failure already shown inline). MainWindow uses
    # this to offer the drive-access diagnosis.
    drives_unavailable = Signal()
    # Emitted when the user clicks Eject. Carries the selected device path
    # ("" if none is selected → eject the system default). MainWindow does
    # the actual (off-thread) eject so this widget stays UI-only.
    eject_requested = Signal(str)

    def __init__(
        self,
        backend: RipBackend,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._backend: RipBackend = backend
        # Device path -> full descriptor, so callers can recover the
        # selected drive's vendor/model (e.g. for the offset lookup), not
        # just its /dev node.
        self._by_device: dict[str, DriveDescriptor] = {}

        layout = QHBoxLayout(self)
        # Zero margins so the row sits flush inside the parent's
        # layout — the main window controls outer padding.
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("Drive:", self))
        self._combo: QComboBox = QComboBox(self)
        # Accessible name so a screen reader announces the combo as the drive
        # selector, not an anonymous dropdown (ux-design-principles.md #10).
        self._combo.setAccessibleName("Optical drive")
        self._combo.currentIndexChanged.connect(self._on_index_changed)
        layout.addWidget(self._combo, stretch=1)

        # Off-GUI-thread refresh, injected by MainWindow (see set_async_refresh).
        # None → the button falls back to the synchronous refresh().
        self._async_refresh: Callable[[], None] | None = None
        self._refresh_button: QPushButton = QPushButton("Refresh", self)
        self._refresh_button.clicked.connect(self._on_refresh_clicked)
        layout.addWidget(self._refresh_button)

        # Re-run the disc scan for the CURRENT drive. Refresh only reloads
        # the drive LIST (and keeps the selection, so it never re-triggers
        # the scan) — real-user feedback: when the first scan hits a
        # transient error (disc still spinning up → whipper's cdrdao
        # read-toc flake), there was no way to retry short of restarting.
        self._rescan_button: QPushButton = QPushButton("Rescan disc", self)
        self._rescan_button.setToolTip(
            "Read the disc in the selected drive again — use this after "
            "inserting a disc, or when the first scan failed."
        )
        self._rescan_button.clicked.connect(self._on_rescan_clicked)
        layout.addWidget(self._rescan_button)

        # Eject the selected disc. Re-emits as eject_requested so the main
        # window can run the (potentially blocking) eject off the GUI thread.
        self._eject_button: QPushButton = QPushButton("Eject", self)
        self._eject_button.setToolTip("Eject the disc from the selected drive.")
        self._eject_button.clicked.connect(self._on_eject_clicked)
        layout.addWidget(self._eject_button)

    # --- Public surface -----------------------------------------------------

    def set_async_refresh(self, callback: Callable[[], None] | None) -> None:
        """Route the Refresh button through an off-GUI-thread fetch.

        MainWindow injects its threaded `refresh_drives` here so clicking
        Refresh on a cold container doesn't freeze the window. When unset
        (standalone widget / tests), the button uses the synchronous `refresh()`.
        """
        self._async_refresh = callback

    def _on_refresh_clicked(self) -> None:
        """Refresh button slot: prefer the injected off-thread refresh."""
        if self._async_refresh is not None:
            self._async_refresh()
        else:
            self.refresh()

    def refresh(self) -> None:
        """Reload drives from the backend **synchronously**.

        Kept for direct callers/tests. In the app the Refresh button routes
        through `set_async_refresh` (MainWindow's threaded `refresh_drives`),
        which fetches the list off the GUI thread and calls `populate()`. On a
        backend error, shows an "(error: …)" placeholder rather than crashing.
        """
        try:
            drives = self._backend.list_drives()
        except RipError as exc:
            log.warning("list_drives failed: %s", exc)
            self.show_error(str(exc))
            return
        except Exception as exc:  # noqa: BLE001 — never let a drive-list
            # hiccup (e.g. the parser choking on unexpected whipper output)
            # take down the whole window; degrade to a placeholder the user
            # can act on, with the full traceback in the log.
            log.exception("list_drives raised an unexpected error")
            self.show_error(f"{type(exc).__name__}: {exc}")
            return
        self.populate(drives)

    def populate(self, drives: list[DriveDescriptor]) -> None:
        """Fill the dropdown from an already-fetched `drives` list.

        Separated from `refresh()` so the launch path can fetch the list off
        the GUI thread and then call this on the GUI thread. Preserves the
        current selection if its device is still present; emits
        `drive_changed` once for the restored/initial selection, or
        `drives_unavailable` when the list is empty.
        """
        previous_device: str | None = self.current_device()
        self._by_device = {}

        # Block signals during the clear/add cycle so we only emit
        # drive_changed once at the end (or zero times if nothing's available).
        self._combo.blockSignals(True)
        self._combo.clear()

        if not drives:
            self._combo.addItem("(no drives found)", None)
            self._combo.blockSignals(False)
            # Let the main window explain *why* (permissions / no device)
            # instead of leaving a bare empty dropdown.
            self.drives_unavailable.emit()
            return

        restore_index = 0
        for i, drive in enumerate(drives):
            label = f"{drive.vendor.strip()} {drive.model.strip()} ({drive.device})"
            self._combo.addItem(label, drive.device)
            self._by_device[drive.device] = drive
            if drive.device == previous_device:
                restore_index = i

        self._combo.setCurrentIndex(restore_index)
        self._combo.blockSignals(False)

        # Emit once for the restored / initial selection.
        device = self._combo.currentData()
        if device is not None:
            self.drive_changed.emit(device)

    def show_error(self, message: str) -> None:
        """Replace the drive list with a single non-selectable error item.

        Signals are blocked so the placeholder can't fire `drive_changed`
        into the rest of the app.
        """
        self._combo.blockSignals(True)
        self._combo.clear()
        self._combo.addItem(f"(error: {message})", None)
        self._combo.blockSignals(False)

    def current_drive(self) -> DriveDescriptor | None:
        """The full descriptor (vendor/model/offset) of the selected drive.

        None when nothing is selected or the dropdown is showing an error /
        no-drives placeholder. Lets callers look the drive's offset up by
        model without re-running `drive list`.
        """
        device = self.current_device()
        if device is None:
            return None
        return self._by_device.get(device)

    def current_device(self) -> str | None:
        """The device path of the currently selected drive, or None."""
        data = self._combo.currentData()
        if isinstance(data, str):
            return data
        return None

    def all_drives(self) -> list[DriveDescriptor]:
        """Every currently-enumerated drive descriptor (for collision checks)."""
        return list(self._by_device.values())

    # --- Internals ---------------------------------------------------------

    def _on_index_changed(self, index: int) -> None:
        device = self._combo.itemData(index)
        if isinstance(device, str):
            self.drive_changed.emit(device)

    def _on_eject_clicked(self) -> None:
        # current_device() is None when only a placeholder is shown; eject
        # the system default ("") in that case rather than blocking the button.
        self.eject_requested.emit(self.current_device() or "")

    def _on_rescan_clicked(self) -> None:
        """Re-emit drive_changed for the current drive so the main window
        re-runs the whole disc pipeline (disc info → MusicBrainz lookup).
        No-op when nothing is selected — there's nothing to rescan."""
        device = self.current_device()
        if device:
            log.info("rescan requested for %s", device)
            self.drive_changed.emit(device)
