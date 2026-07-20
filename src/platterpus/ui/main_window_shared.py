"""The typing seam shared by ``MainWindow`` and its mixins.

Why this file exists
--------------------
``MainWindow`` is a Qt "god-object" split into cohesive ``*Mixin`` classes it
inherits (see ``docs/architecture.md`` §3.6). At **runtime** a mixin method's
``self`` *is* the concrete ``MainWindow``, so ``self._config``,
``self._rip_progress``, ``self.refresh_drives()`` and friends all work — the
attribute or sibling-mixin method is really there on the assembled object.

A **type checker**, though, sees a mixin in isolation: inside ``RipMixin`` the
type of ``self`` is ``RipMixin``, which declares none of the attributes that
``MainWindow.__init__`` sets nor the methods that *other* mixins define. Without
help, mypy reports hundreds of "has no attribute" errors and the whole UI
god-object has to be excluded from the type gate.

This class is that help. It is a **type-only declaration** of everything the
window provides to its mixins — the injected dependencies, the child widgets,
the per-session state, the Qt signals, and the cross-mixin methods. Every mixin
(and the concrete ``MainWindow``) inherits it, so mypy can resolve
``self._x`` / ``self.some_sibling_method()`` from *any* mixin.

It changes **no runtime behaviour**:

* The attribute lines are *bare annotations* (``name: Type`` with no ``=``).
  Annotations do not create attributes — they only populate ``__annotations__``
  — so at runtime this class has no instance state. Every attribute is really
  assigned in ``MainWindow.__init__`` (or a mixin's reset helper), exactly as
  before.
* The method declarations live under ``if TYPE_CHECKING:`` and so **do not
  exist at runtime at all** — the real implementations (in the concrete window
  or a sibling mixin) are the only ones ever called. They are here purely so
  mypy can see the cross-mixin call sites; keep each stub's signature in step
  with its real implementation.
* The base it inherits is chosen by ``TYPE_CHECKING`` (see ``_SeamBase`` below):
  ``QWidget`` for the type checker, plain ``object`` at runtime. This is the one
  and only bit of indirection here, and it is a well-known, non-magic typing
  idiom (no metaclass tricks, no dynamic class creation, no monkey-patching) —
  it exists so mypy knows ``self`` inside a mixin really is a Qt widget (the
  concrete window is one), which lets it both resolve the Qt methods a mixin
  calls on ``self`` (``self.close()``, ``self.update()`` …) *and* accept ``self``
  where a ``QWidget`` parent is expected (``QMessageBox.information(self, …)``).

  Why ``QWidget`` and not ``QMainWindow``: ``MainWindow`` lists ``QMainWindow``
  first in its own bases, so if the seam also derived ``QMainWindow`` the C3
  linearisation would need ``QMainWindow`` both *before* the mixins (base order)
  and *after* them (it would be a mixin ancestor) — an unsatisfiable order.
  ``QWidget`` is never a *direct* base of ``MainWindow``, so it slots in after
  everything with no contradiction. And at runtime the base is ``object``, so
  the mixins gain no Qt base at all: the MRO and the (Shiboken) metaclass are
  exactly what they were before this file existed. Verified: the full test
  suite is unchanged.

So: the single source of truth for the *shared surface* — "what does the window
expose to its mixins" — written once, read by the next contributor, and enforced
by the type gate.

A note on the annotation convention, so the split doesn't puzzle you: the few
attributes whose type was *changed* for the seam (the workers/dialogs/manager
that used to be ``object | None``) drop their inline annotation in
``MainWindow.__init__`` — a bare ``self._x = None  # type on MainWindowShared``
— so the concrete type lives in exactly one place (here). The rest keep their
inline ``__init__`` annotation *and* are declared here; that duplication is
deliberate (the assignment stays self-documenting at its site) and harmless —
mypy holds the two in sync, and would flag any drift. Either way, this class is
the declaration the mixins actually type-check against.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from PySide6.QtCore import QThread, QTimer, Signal
    from PySide6.QtWidgets import QProgressDialog, QSplitter, QWidget

    from platterpus.adapters import cover_art
    from platterpus.adapters.accuraterip_offsets import OffsetDatabase
    from platterpus.adapters.ctdb_client import CTDBClient
    from platterpus.adapters.derived_verify import DerivedVerifyResult
    from platterpus.adapters.metaflac import MetaflacAdapter
    from platterpus.adapters.musicbrainz_client import (
        MusicBrainzClient,
        ReleaseDetail,
        ReleaseSummary,
    )
    from platterpus.adapters.rip_backend import RipBackend
    from platterpus.config import Config
    from platterpus.deps.manager import DependencyManager, DependencyReport
    from platterpus.drive_media import MediaWatcher
    from platterpus.drive_profile_store import DriveProfileStore
    from platterpus.drive_profiles import OffsetSource
    from platterpus.parsers.rip_log import RipLog
    from platterpus.ui.disc_info_panel import DiscInfoPanel
    from platterpus.ui.drive_picker import DrivePicker
    from platterpus.ui.rip_controls import RipControls
    from platterpus.ui.rip_progress import RipProgress
    from platterpus.ui.track_table import TrackTable
    from platterpus.workers.dependency_worker import DependencyCheckWorker
    from platterpus.workers.disc_info_worker import DiscInfoWorker
    from platterpus.workers.drive_list_worker import DriveListWorker
    from platterpus.workers.mb_worker import MusicBrainzWorker
    from platterpus.workers.rip_worker import RipParameters, RipWorker
    from platterpus.workers.update_worker import (
        UpdateCheckWorker,
        UpdateInstallWorker,
    )

    # At type-check time the seam IS a QWidget (the concrete window is one), so
    # mypy resolves the Qt methods a mixin calls on ``self`` and accepts ``self``
    # where a QWidget parent is expected. See the module docstring for why this
    # is QWidget (not QMainWindow) and why it is runtime-neutral.
    _SeamBase = QWidget
else:
    # At runtime the seam is a plain object subclass — it adds no Qt base to the
    # mixins, so the MRO and metaclass are exactly as they were before.
    _SeamBase = object


class MainWindowShared(_SeamBase):
    """Type-only declaration of the surface every ``MainWindow`` mixin shares.

    See the module docstring for the full rationale. In short: inheriting this
    lets mypy resolve cross-mixin ``self._x`` / ``self.sibling_method()`` access;
    it adds no runtime state or behaviour.
    """

    # --- Injected dependencies (set in MainWindow.__init__) ----------------
    _config: Config
    _backend: RipBackend
    _mb_client: MusicBrainzClient
    _metaflac: MetaflacAdapter
    _dependency_manager: DependencyManager
    _ctdb_client: CTDBClient
    _offset_db: OffsetDatabase
    _drive_profiles: DriveProfileStore
    _save_config: Callable[[Config], None]

    # --- Per-session state -------------------------------------------------
    _current_release_id: str
    _current_release_detail: ReleaseDetail | None
    _last_mb_releases: list[ReleaseSummary]
    _manual_cover_path: str | None
    _current_disc_id: str
    _current_num_tracks: int

    # Active rip's worker/thread (concrete types so member access resolves).
    _rip_worker: RipWorker | None
    _rip_thread: QThread | None
    # Update check + install workers/threads and the install progress dialog.
    _update_worker: UpdateCheckWorker | None
    _update_thread: QThread | None
    _install_worker: UpdateInstallWorker | None
    _install_thread: QThread | None
    _install_dialog: QProgressDialog | None
    _install_post_download: bool
    # Launch-time dependency probe + its GUI-backed manager.
    _dep_check_worker: DependencyCheckWorker | None
    _dep_check_thread: QThread | None
    _dep_check_manager: DependencyManager | None
    _dep_check_show_summary: bool
    # Disc probe (per drive change) + scan force-stop flag.
    _disc_info_worker: DiscInfoWorker | None
    _disc_info_thread: QThread | None
    _scan_force_stopped: bool
    # Launch-time drive listing.
    _drive_list_worker: DriveListWorker | None
    _drive_list_thread: QThread | None

    # In-flight rip bookkeeping.
    _active_rip_params: RipParameters | None
    _rip_cancelled: bool
    _auto_retry_done: bool
    _force_stop_done: bool
    _force_stop_timer: QTimer
    _force_stop_thread: threading.Thread | None
    _repaint_timer: QTimer
    _rip_report_timer: QTimer

    # Freshly-inserted-disc auto-detect (drive_media).
    _disc_status_probe: Callable[[str], str]
    _media_watcher: MediaWatcher
    _media_poll_timer: QTimer
    _eject_thread: threading.Thread | None

    # Post-rip work (cover art, tagging) daemon + injected fetcher.
    _cover_art_fetcher: cover_art.Fetcher | None
    _post_rip_thread: threading.Thread | None

    # The last parsed rip log + file path (kept for the coalesced report re-write).
    _last_rip_log: RipLog | None
    _last_rip_log_file: Path | None
    # Wall-clock timing of the in-flight / just-finished rip.
    _rip_started_monotonic: float | None
    _rip_started_at: str
    _last_rip_timing: dict | None
    # Per-rip histories folded into the report at finish.
    _last_speed_attempts: list
    _last_unstable_tracks: list
    _last_retried_tracks: list
    _last_eta_trace: list
    # Rip time-windows for per-report debug-log filtering.
    _rip_epoch_start: float | None
    _rip_windows: list[tuple[float, float]]
    _current_rip_window: tuple[float, float] | None
    _pending_picard_launch: bool

    # Post-rip async-check daemon threads.
    _ctdb_thread: threading.Thread | None
    _flac_verify_thread: threading.Thread | None
    _derived_verify_thread: threading.Thread | None

    # Per-rip result snapshots, reset to None at the start of each finish and
    # filled as each (possibly async) check lands, so the coalesced report
    # re-write can pass every outcome regardless of completion order. The ones
    # delivered via a ``Signal(object)`` are typed ``object | None`` because that
    # is exactly what their queued-signal handlers receive and store (they do
    # not narrow); ``_last_derived_verify_result`` is the exception — its handler
    # ``isinstance``-narrows, so it carries the concrete type.
    _last_rip_error: str | None
    _last_outcome: dict | None
    _last_disc: dict | None
    _last_read_offset_effective: int | None
    _last_secure_rerip: object | None
    _last_ctdb_result: object | None
    _last_flac_verify_result: object | None
    _last_transcode_result: object | None
    _last_derived_verify_result: DerivedVerifyResult | None
    _last_cover_art_result: object | None
    _last_recompress_result: object | None
    _last_checksums: dict | None
    _last_dependency_report: DependencyReport | None

    # Rip generation guard (drops a stale previous rip's late verify).
    _rip_generation: int
    _drive_access_nudged: bool

    # --- Child widgets -----------------------------------------------------
    _drive_picker: DrivePicker
    _disc_info_panel: DiscInfoPanel
    _track_table: TrackTable
    _rip_controls: RipControls
    _rip_progress: RipProgress
    _content_splitter: QSplitter

    # --- MusicBrainz worker (its own thread) -------------------------------
    _mb_worker: MusicBrainzWorker
    _mb_thread: QThread

    # --- Qt signals (declared as class attrs on the concrete MainWindow) ---
    # Accessed on the instance as SignalInstances; the PySide6 stubs let a
    # ``Signal``-typed attribute resolve ``.emit`` / ``.connect``.
    rip_post_processing_done: Signal
    cover_art_done: Signal
    ctdb_verify_done: Signal
    flac_verify_done: Signal
    flac_recompress_done: Signal
    transcode_done: Signal
    derived_verify_done: Signal
    checksums_done: Signal
    rip_comparison_done: Signal
    _mb_lookup_disc_id_requested: Signal
    _mb_fetch_release_requested: Signal

    if TYPE_CHECKING:
        # --- Cross-mixin / Qt methods a mixin calls on ``self`` -----------
        # Real implementations live in the concrete MainWindow or a sibling
        # mixin (see docs/architecture.md §3.6 for the ownership map). These
        # type-only stubs exist so mypy can resolve the call sites; keep their
        # signatures in step with the real methods.

        # Defined on the concrete MainWindow (main_window.py):
        def refresh_drives(self) -> None: ...
        def _set_rip_lock(self, active: bool) -> None: ...
        def _start_disc_info(self, device: str) -> None: ...

        # Defined in ProvisioningMixin (main_window_provision.py):
        def open_host_setup_dialog(self) -> None: ...

        # Defined in DependencyMixin (main_window_deps.py):
        def run_dependency_check_async(self, show_summary: bool = ...) -> None: ...

        # Defined in DriveMixin (main_window_drive.py):
        def _set_read_offset_override(self, value: int) -> None: ...
        def _refresh_drive_profile_display(self) -> None: ...
        def _record_drive_fact(
            self,
            drive: object,
            *,
            offset_value: int | None = ...,
            source: OffsetSource | None = ...,
            cache_defeat: bool | None = ...,
        ) -> None: ...
        def _on_drive_setup(self) -> None: ...
        def _maybe_offer_drive_setup(self) -> None: ...
        def _fingerprint_for(self, drive: object) -> tuple[str, str, str]: ...
        def _auto_apply_known_offset(self) -> bool: ...
