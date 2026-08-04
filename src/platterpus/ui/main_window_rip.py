"""Rip lifecycle for the main window.

Extracted from ``main_window`` (2026-06-13 modularization) as a mixin —
the single largest concern: starting a rip, the cancel → force-stop
escalation, eject, the finish handler (fidelity verdict, auto-heal,
auto-eject), the unknown-album flow, post-rip tagging, and backend-
independent cover art. ``MainWindow`` inherits this, so its methods stay
reachable as ``window._on_rip_finished`` etc. (which the test suite and Qt
signal connections depend on).

Contract this mixin expects from the host window (all set in
``MainWindow.__init__``): the widgets ``self._track_table``,
``self._rip_progress``, ``self._rip_controls``, ``self._drive_picker``,
``self._disc_info_panel``; the adapters ``self._backend``,
``self._metaflac``; ``self._config``; the rip-state attributes
``self._rip_worker``/``_rip_thread``/``_active_rip_params``/
``_rip_cancelled``/``_auto_retry_done``/``_force_stop_done``/
``_force_stop_timer``/``_force_stop_thread``/``_eject_thread``/
``_post_rip_thread``/``_cover_art_fetcher``/``_pending_picard_launch``/
``_current_release_id``/``_current_release_detail``/``_ctdb_client``/``_ctdb_thread``/
``_flac_verify_thread``/``_derived_verify_thread``;
the ``rip_post_processing_done``, ``cover_art_done``,
``ctdb_verify_done``, ``flac_verify_done``, ``flac_recompress_done``,
``transcode_done`` and ``derived_verify_done`` signals;
and the cross-mixin methods
``self._auto_apply_known_offset`` / ``self._on_drive_setup`` (DriveMixin).

Future contributors: the rip itself runs in ``workers/rip_worker.py`` via a
backend behind the ``RipBackend`` ABC — this file is GUI orchestration
only. To support a new backend's log, extend the sniff/parse block in
``_on_rip_finished`` and ``fidelity_summary`` (see ``docs/architecture.md``).
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

from PySide6.QtCore import QThread, QTimer
from PySide6.QtWidgets import QDialog, QMessageBox

if TYPE_CHECKING:
    from PySide6.QtWidgets import QSystemTrayIcon

    from platterpus.adapters.musicbrainz_client import TrackSummary
    from platterpus.ui.track_table import AlbumMetadata

from platterpus import drive_control, rip_files
from platterpus.adapters import cover_art
from platterpus.adapters.derived_verify import DerivedVerifyResult
from platterpus.adapters.flac_recompress import (
    RecompressResult,
    recompress_flac_files,
)
from platterpus.adapters.flac_verify import FlacVerifyResult
from platterpus.adapters.rip_backend import RipMetadata, TrackTag
from platterpus.adapters.transcode import (
    EMBEDS_COVER_ART,
    TranscodeResult,
    transcode_files,
)
from platterpus.adapters.transcode import (
    SUPPORTED_FORMATS as TRANSCODE_FORMATS,
)
from platterpus.drive_profiles import OffsetSource
from platterpus.offset_config import is_offset_configured
from platterpus.parsers.cyanrip_log import looks_like_cyanrip_log, parse_cyanrip_log
from platterpus.parsers.rip_log import RipLog, TrackResult, parse_rip_log
from platterpus.paths import LOG_PATH
from platterpus.report_types import ArtifactsBlock
from platterpus.rip_addendum import read_log_with_addendum
from platterpus.ui.main_window_helpers import (
    _dir_has_audio,
    fidelity_summary,
    free_album_folder_templates,
    known_album_folder,
    safe_path_segment,
    unique_album_title,
)
from platterpus.ui.main_window_shared import MainWindowShared
from platterpus.ui.unknown_album import (
    UnknownAlbumDialog,
    apply_track_tags,
    launch_picard_for,
)
from platterpus.verdict import expected_track_total
from platterpus.workers import start_worker_thread
from platterpus.workers.ctdb_worker import verify_rip_dir
from platterpus.workers.derived_verify_worker import (
    verify_rip_dir as verify_derived_dir,
)
from platterpus.workers.flac_verify_worker import verify_rip_dir as verify_flac_dir
from platterpus.workers.rip_worker import RipParameters, RipWorker

log = logging.getLogger(__name__)

# How long after Cancel to wait before auto-force-stopping the drive (the
# in-container reader can keep it spinning). The user can hit Force stop to
# escalate sooner.
_FORCE_STOP_COUNTDOWN_MS: int = 5000

# How long window-close may spend stopping the in-container reader, in total.
# Chosen against what the fast path actually costs: on rootless podman the
# in-container processes are host-visible, so the `fuser -k` that does the real
# work is effectively instant (measured at 0.12 s on the rig — 20:50:03,949 →
# 20:50:04,067). 5 s therefore leaves the common case untouched while capping the
# pathological one, where every step misses and the `distrobox enter` fallback
# would otherwise be waited out. Deliberately smaller than the worker shutdown
# budget: this runs BEFORE the workers are stopped and must not eat their share.
_SHUTDOWN_DRIVE_FREE_BUDGET_S: float = 5.0

# How long the rip may go with NO signal from the worker (no progress line, no
# status, no log output) before the liveness watchdog calls it a stall and shows
# the notice. cyanrip streams several lines a second while healthy, so tens of
# seconds of total silence means it's blocked in a read — almost always a wedged
# drive (e.g. an unsupported lead-out overread on the last track). Generous
# enough not to false-alarm on a slow re-read burst; short enough to reassure
# quickly that the freeze is *seen*.
_RIP_STALL_THRESHOLD_S: float = 45.0

# Bound on how long the checksum step waits for in-flight tagging/transcode to
# settle before hashing (mirrors the CTDB/FLAC-verify settle bound), so a wedged
# post-rip step can't hang the digest thread forever.
_CHECKSUM_SETTLE_TIMEOUT_S: float = 120.0

# Guards the lazily-created ``_post_rip_failures`` record. Module-level rather
# than per-window because the record is created by whichever post-rip daemon
# fails FIRST, and two of them can die in the same instant — a read-modify-write
# race there would drop one of the two failures we are adding the record to
# capture. Held only for a dict write, so contention is nil.
_POST_RIP_FAILURE_LOCK: threading.Lock = threading.Lock()


@dataclass(frozen=True)
class TaggingResult:
    """Outcome of the post-rip unknown-album tagging pass.

    Why this type exists (2026-07-31): ``apply_track_tags`` logs each per-file
    ``MetaflacError`` at WARNING and returns the files that *succeeded* — and the
    caller threw that return value away. So a total tagging failure (the disk
    filled during the metaflac pass; ``metaflac`` vanished; every filename lacked
    a leading track number) shipped a whole album of untagged FLACs while the
    window said "Done." and the JSON report said nothing at all. This carries the
    facts back to the GUI thread so the user and the report both learn about it.

    ``attempted`` counts the masters we tried to tag; ``tagged`` how many took
    their tags. ``failures`` are the basenames that did not (kept as names, not
    paths, because that is what a user reads and what the report shows).
    ``error`` is a whole-pass failure — the step raised or never ran — as opposed
    to per-file failures.
    """

    ran: bool = False
    attempted: int = 0
    tagged: int = 0
    failures: tuple[str, ...] = ()
    error: str = ""

    @property
    def ok(self) -> bool:
        """True when the pass ran and every file we attempted took its tags.

        A pass with nothing to tag (``attempted == 0``) is *not* a failure — an
        empty album folder is the caller's problem to report, not this pass's.
        """
        return not self.failures and not self.error


def _rip_master_paths(rip_dir: Path, rip_log: object | None) -> list[Path]:
    """The FLAC masters **this rip** wrote, for a step that is about to change them.

    Every post-rip step below (tagging, colon-restore, re-compress, transcode)
    used to answer this with ``rip_dir.rglob("*.flac")``. Unlike the verification
    steps — which only *read* — these four **mutate or derive from** whatever they
    find, and "the FLACs in the album folder" is not "the FLACs this rip wrote".
    One ordinary sequence puts a stranger's file there: cancel a rip (partial
    files remain, one of them a truncated FLAC), fix a track title, re-rip and
    choose *Replace* — the new titles produce new filenames, so the new files land
    *beside* the old ones. The raw glob then wrote this disc's metadata into the
    leftover, re-compressed it, and transcoded it into the user's library.

    :mod:`platterpus.rip_files` is the single shared answer to "which files are
    mine?" (CLAUDE.md Critical rule #6): it reads the rip's own log — which names
    one file per track — and degrades to a folder scan, logged at WARNING, when
    there is no usable log. ``rip_log`` is the already-parsed log the finish
    handler is holding, passed in so the log is not read a second time.
    """
    file_set = rip_files.rip_master_files(rip_dir, rip_log=rip_log)
    if not file_set.files:
        # Not an error we can act on here (every caller is best-effort), but it
        # must never be silent: a post-rip step that quietly did nothing is
        # indistinguishable from one that succeeded.
        log.warning(
            "no FLAC master from this rip could be identified in %s — the post-rip "
            "step has nothing to work on",
            rip_dir,
        )
    return list(file_set.files)


def _metadata_contains_colon(metadata: RipMetadata | None, release_id: str) -> bool:
    """Whether any tag value handed to cyanrip carries a literal ``:``.

    Drives the post-rip colon-restore (KDD-22): cyanrip can't take a ``:`` in a
    tag arg, so each such value is fed as the U+2236 lookalike and must be
    restored in the written tags afterward. This must cover EVERY field the
    backend's ``_escape_meta_value`` touches — album artist/title, year, genre,
    the ``musicbrainz_albumid`` (``release_id``), and each track's title, artist,
    and ISRC. It previously checked only album/track title+artist, so a colon in
    year/genre/isrc/albumid kept its U+2236 in the tag forever (#29). Pure and
    testable; reads the assembled ``RipMetadata`` so it can't drift from what was
    actually sent.
    """
    if ":" in (release_id or ""):
        return True
    if metadata is None:
        return False
    for value in (
        metadata.album_artist,
        metadata.album_title,
        metadata.year,
        metadata.genre,
    ):
        if ":" in (value or ""):
            return True
    return any(
        ":" in (track.title or "")
        or ":" in (track.artist or "")
        or ":" in (track.isrc or "")
        for track in metadata.tracks
    )


# Field-preserving merge below: one TypeVar so the "keep what we had" rule is
# checked against each field's real type instead of collapsing to Any.
_T = TypeVar("_T")


def _reported(new: _T, current: _T) -> _T:
    """``new`` when the re-rip's log actually reported it, else ``current``.

    The re-rip log is external output, so a field it didn't print parses as None /
    empty. Letting that overwrite a real first-pass value would *delete* known
    facts about the shipped file — worse than the stale value we're fixing. So an
    unreported field keeps what we had.
    """
    return current if new is None or new == "" or new == {} else new


def _verified_by_this_read(new: _T, current: _T, *, track: int, field: str) -> _T:
    """A verification claim the SHIPPED read must earn for itself. No fallback.

    This is the sibling of :func:`_reported` and it deliberately does the opposite
    thing, because a *description* and a *claim of proof* fail in opposite
    directions.

    `_reported` keeps the first pass's value when the re-rip didn't print one, on
    the reasoning that discarding a known fact is worse than keeping a stale one.
    That reasoning holds for a descriptive field. It **inverts** for an
    AccurateRip result, because an AccurateRip verdict is not a description of a
    track — it is the assertion *"a shared database confirmed these exact bytes"*.
    The first pass's verdict confirmed the bytes we THREW AWAY. Carrying it onto
    the replacement means the banner, the JSON report, the per-track table and the
    EAC log all state a verification that never happened for the audio on disk.

    So an unreported verification becomes **unknown**, not inherited. Unknown is
    honest and the UI already renders it ("not in DB" / no checkmark); a stale
    "verified" is the single worst thing this program can say, and it is the exact
    class of failure KDD-30 exists to prevent.

    Dropping a value is a fact worth recording, so it is logged: a track that
    silently lost its verdict would otherwise look like a disc that AccurateRip
    simply doesn't know.
    """
    if new is None or new == "" or new == {}:
        if current is not None and current != "" and current != {}:
            log.info(
                "track %d: dropping the first pass's %s — its file was replaced by "
                "a re-rip whose log reported no %s, so the shipped bytes were never "
                "checked against AccurateRip and must not inherit that verdict",
                track,
                field,
                field,
            )
        return new
    return new


def _merge_shipped_track(
    track: TrackResult, shipped: TrackResult | None, verdicts: dict[int, bool]
) -> TrackResult:
    """One track's first-pass record, corrected to describe the shipped file.

    Pure and module-level so the merge rule is readable and directly testable
    (same reason ``_format_cache_defeat`` lives outside its mixin). ``shipped`` is
    the re-rip's parsed record for this track, or None when nothing was swapped in.

    Every field is named explicitly rather than looped over: this is the rule that
    decides what a CRC and an AccurateRip verdict are *about*, so it should be
    readable line by line — and naming them lets the type checker verify each one,
    which a ``**dict`` splat cannot. ``number`` and ``filename`` are deliberately
    absent: the re-rip ran in a throwaway directory under the same track number,
    so its identity fields are either irrelevant or wrong.
    """
    from dataclasses import replace

    if shipped is not None:
        track = replace(
            track,
            copy_crc=_reported(shipped.copy_crc, track.copy_crc),
            status=_reported(shipped.status, track.status),
            # NOT `_reported`: see `_verified_by_this_read`. These three are
            # claims that a shared database confirmed specific bytes, and the
            # bytes the first pass confirmed were discarded. Inheriting them let a
            # re-ripped track read "AccurateRip verified" when the audio actually
            # shipped had never been checked at all.
            accuraterip_v1=_verified_by_this_read(
                shipped.accuraterip_v1,
                track.accuraterip_v1,
                track=track.number,
                field="AccurateRip v1 result",
            ),
            accuraterip_v2=_verified_by_this_read(
                shipped.accuraterip_v2,
                track.accuraterip_v2,
                track=track.number,
                field="AccurateRip v2 result",
            ),
            accuraterip_offset=_verified_by_this_read(
                shipped.accuraterip_offset,
                track.accuraterip_offset,
                track=track.number,
                field="AccurateRip offset-variant result",
            ),
            # `test_crc` is the other proof-shaped field: it is half of a
            # two-reads-agree pair, and pairing the first pass's Test CRC with the
            # replacement's Copy CRC would render a convergence that never
            # happened. Same rule, same reason.
            test_crc=_verified_by_this_read(
                shipped.test_crc,
                track.test_crc,
                track=track.number,
                field="Test CRC",
            ),
            rip_count=_reported(shipped.rip_count, track.rip_count),
            peak_level=_reported(shipped.peak_level, track.peak_level),
            extraction_quality=_reported(
                shipped.extraction_quality, track.extraction_quality
            ),
            replaygain=_reported(shipped.replaygain, track.replaygain),
        )
    verdict = verdicts.get(track.number)
    if verdict is not None:
        # The convergence verdict is ours, from the auto-fix history — it wins
        # over whatever the re-rip's own log did or didn't say.
        track = replace(track, secure_rerip_converged=verdict)
    return track


def _ripped_audio_seconds(rip_log: object) -> float | None:
    """How much audio the rip ACTUALLY extracted, in seconds. Never raises.

    Summed from each track's sector span, which is the only figure that means
    "we read this much" on a rip that stopped early — the disc's own length says
    what was *available*, not what was taken. Returns None when the log carries
    no usable geometry, which callers read as "cannot say" rather than zero.
    """
    total = 0
    for track in getattr(rip_log, "tracks", ()) or ():
        start = getattr(track, "start_sector", None)
        end = getattr(track, "end_sector", None)
        if isinstance(start, int) and isinstance(end, int) and end >= start:
            total += end - start + 1
    # 75 sectors per second (Red Book), the same constant the TOC table uses.
    return total / 75 if total else None


class RipMixin(MainWindowShared):
    """Start/cancel/finish a rip, plus eject, unknown-album, and cover art."""

    # State only this mixin touches, so it is declared here rather than on the
    # shared seam (``main_window_shared``), which is the map of what the window
    # exposes to *all* its mixins. Bare annotations, like every declaration on
    # that seam: they add no runtime attribute, so both are read with a
    # ``getattr`` default until the first Start assigns them (the same pattern
    # the ``_last_*`` report snapshots use).
    #
    # ``_last_tagging_result`` — the post-rip tagging outcome, folded into the
    # rip report. ``_post_rip_failures`` — ``{thread attribute: error text}`` for
    # every post-rip daemon that died instead of returning a result (see
    # ``_record_post_rip_failure``); written from those daemon threads, read on
    # the GUI thread.
    _last_tagging_result: TaggingResult | None
    _post_rip_failures: dict[str, str]
    #: The ripper's substantive stdout, snapshotted at finish. The report is
    #: written repeatedly and `_rip_worker` is None for every write after the
    #: first, so the writer must read this rather than the worker.
    _last_ripper_stdout: str
    #: The ripper's verdict on its own log, or None if the step never ran. `object`
    #: rather than the adapter's dataclass so this UI mixin does not import an
    #: adapter for a type it only forwards.
    _last_ripper_log_verification: object | None

    # --- Slots: rip flow ----------------------------------------------------

    def _on_rip_requested(self, params: RipParameters) -> None:
        """User clicked Start. Validate, then start the worker thread."""
        # A read offset is mandatory: an accurate offset is what makes the rip
        # bit-perfect. If neither the legacy whipper.conf (still read for the
        # trust display) nor our own --offset override has one, stop here and
        # point the user at the drive-setup wizard rather
        # than letting the rip start and fail. The wizard pre-fills the offset
        # when the drive model is known; otherwise it's found from a CD that's
        # in the AccurateRip database.
        if (
            not is_offset_configured(self._config.override_read_offset)
            and not self._auto_apply_known_offset()
        ):
            # No offset configured AND we don't know this drive's offset →
            # the only case that still needs the wizard. (A known drive is
            # auto-applied above, so the user is never blocked for it.)
            answer = QMessageBox.warning(
                self,
                "Set up your drive first",
                "No read offset is configured for your drive, so ripping can't "
                "start — an accurate read offset is what makes the rip "
                "bit-perfect.\n\n"
                "Open Tools → Set up drive… and either accept the offset it "
                "fills in, or insert a CD that's in the AccurateRip database and "
                "click Detect, then Save.\n\n"
                "Open the drive-setup wizard now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if answer == QMessageBox.StandardButton.Yes:
                self._on_drive_setup()
            return

        # Self-heal a stale/wrong SAVED offset before it silently ruins the rip.
        # `is_offset_configured` is True as soon as an override exists — even if
        # its value is wrong (e.g. a 0 left by the old, since-removed cyanrip
        # "offset detection"). If the saved offset disagrees with the AccurateRip
        # drive-list value for the selected drive, surface it and offer the list
        # value.
        #
        # BUT respect a *deliberate* per-unit offset: if the stored provenance is
        # MANUAL (the user typed it on purpose) or CONFIRMED (two independent
        # sources already agreed), we do NOT offer to overwrite it — that would
        # re-introduce the very silent-wrong-offset the ledger's own rule
        # (`reconcile_offset`) forbids, e.g. clobbering a measured +691 on one of
        # two same-model drives with the model-list +667. Only an untrusted/
        # leftover value (a stale OFFSET_FIND, WHIPPER_CONF, or no provenance)
        # gets the offer.
        drive = self._drive_picker.current_drive()
        if self._config.override_read_offset and drive is not None:
            listed = self._offset_db.lookup(drive.vendor, drive.model)
            if listed is not None and listed != self._config.read_offset:
                fingerprint, _serial, _wwn = self._fingerprint_for(drive)
                stored = self._drive_profiles.get(fingerprint)
                stored_source = (
                    stored.offset.source
                    if stored is not None and stored.offset is not None
                    else None
                )
                deliberate = stored_source in (
                    OffsetSource.MANUAL,
                    OffsetSource.CONFIRMED,
                )
                if not deliberate:
                    label = f"{drive.vendor.strip()} {drive.model.strip()}".strip()
                    answer = QMessageBox.warning(
                        self,
                        "Read offset disagreement",
                        f"The saved read offset is {self._config.read_offset:+d}, "
                        f"but the AccurateRip drive list says {listed:+d} for "
                        f"{label or 'this drive'}.\n\n"
                        "A wrong read offset makes the rip NOT bit-perfect — it "
                        f"won't match AccurateRip. Use the AccurateRip value "
                        f"({listed:+d}) instead?\n\n"
                        "Choose No only if you deliberately measured a different "
                        "offset for this exact drive.",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.Yes,
                    )
                    if answer == QMessageBox.StandardButton.Yes:
                        self._set_read_offset_override(listed)
                        # Record the healed value in the ledger too, so the trust
                        # line reflects it immediately (otherwise the refresh below
                        # re-reads the stale record and shows a now-false "the rip
                        # will use +0" disagreement, telling the user to redo the
                        # fix they just made). Recorded as MANUAL because accepting
                        # this prompt IS a deliberate user choice — and MANUAL is
                        # the one source that always wins `reconcile_offset`, so it
                        # actually replaces the stale record (an ACCURATERIP_LIST
                        # write would tie the incumbent's confidence and be kept
                        # out).
                        self._record_drive_fact(
                            drive,
                            offset_value=listed,
                            source=OffsetSource.MANUAL,
                        )
                        self._refresh_drive_profile_display()

        # The offset is configured now — but `params` was built by the rip
        # controls BEFORE any auto-apply/heal above, so it may still carry
        # read_offset_override=None (or the pre-heal value). Inject the current
        # config value here so cyanrip actually gets its `-s` sample offset
        # (otherwise the rip isn't offset-corrected).
        if self._config.override_read_offset:
            params = replace(params, read_offset_override=self._config.read_offset)

        # The DISC's own track count, from the scanned TOC. The backend needs it
        # to refuse an out-of-range `-t`: cyanrip rejects the whole rip on one
        # ("Invalid track number 17, list has 16 tracks!", exit 1, nothing
        # ripped), which is exactly what happened to disc 1 of a 4-disc set
        # whose MusicBrainz medium listed 18 tracks against a 16-track disc
        # (2026-08-02). Built here rather than in the rip controls because this
        # is where the scanned disc is known; 0/None stays None so the guard
        # never invents a ceiling it cannot justify.
        params = replace(
            params, disc_track_total=getattr(self, "_current_num_tracks", 0) or None
        )

        # Only validate the track table for non-unknown rips — placeholder
        # tags will be applied after the fact in unknown mode.
        if not params.unknown:
            ok, message = self._track_table.validate()
            if not ok:
                QMessageBox.warning(self, "Cannot start rip", message)
                return
            # Known-disc overwrite guard (2026-07-08 trust audit): a re-rip of an
            # ALREADY-identified album to the same folder used to overwrite the
            # existing rip silently. (The unknown-disc collision case auto-suffixes
            # — v0.4.22 — but a known re-rip is often deliberate, so it gets a
            # confirm instead of silent behaviour either way.) If the target folder
            # already holds audio, ask before touching it.
            confirmed = self._confirm_known_overwrite(params)
            if confirmed is None:
                return  # user cancelled
            params = confirmed
        else:
            # Unknown disc: build the output templates from the album fields
            # (literal folder names, not a disc-ID hash).
            params = self._as_unknown_params(params)

        self._rip_progress.clear()
        self._rip_progress.set_status("Starting rip…")
        # Cleared here, set in _on_rip_cancel — so the finish handler can
        # say "cancelled" instead of "failed".
        self._rip_cancelled = False
        # Stamp the rip's start for the elapsed-time record. Set here (the
        # user-perceived Start), NOT in _start_rip_worker, so an auto-heal retry
        # is included in the total — the user waited for the whole thing. cyanrip
        # logs neither its start time nor its run time, so this is the only place
        # the actual wall-clock can be measured (real-disc lesson: 2h45m actual
        # vs cyanrip's "~35m" ETA — see rip_timing.py).
        import time as _time
        from datetime import datetime as _datetime

        self._rip_started_monotonic = _time.monotonic()
        self._rip_started_at = (
            _datetime.now().astimezone().isoformat(timespec="seconds")
        )
        # Epoch start (wall time, comparable to LogRecord.created) bounds this
        # rip's slice of the session log so other albums' reports can exclude it.
        self._rip_epoch_start = _time.time()
        # Drop the previous rip's parsed-log/report state, so a CTDB verify that
        # finishes late can never re-write THIS rip's report against the old one.
        self._last_rip_log = None
        self._last_rip_log_file = None
        self._last_rip_timing = None
        self._current_rip_window = None
        # Async post-rip verification outcomes, accumulated as each finishes.
        # The report is re-written after each, passing all of them, so the final
        # .platterpus.json holds every check regardless of completion order — and
        # a late-finishing verify from THIS rip never carries into the next
        # (they're reset here at the start of each finish).
        self._last_ctdb_result = None
        self._last_flac_verify_result = None
        self._last_transcode_result = None
        self._last_derived_verify_result = None
        self._last_checksums = None
        # v7 report snapshots (0.4.10): the PROCESS outcome, disc provenance, the
        # effective read offset, and the cover-art / re-compress / secure-re-rip
        # results. Reset per rip so a debounced re-write for a NEW rip can never
        # carry the previous rip's values (the report is re-written after each
        # async check finishes; see _schedule_rip_report_write / #20-style guard).
        self._last_outcome = None
        self._last_disc = None
        self._last_read_offset_effective = None
        self._last_secure_rerip = None
        #: The ripper's substantive stdout, snapshotted at finish so the report's
        #: re-writes still carry it after the worker is torn down. See `_finish_rip`.
        self._last_ripper_stdout = ""
        self._last_ripper_log_verification = None
        self._last_cover_art_result = None
        self._last_recompress_result = None
        self._last_tagging_result = None
        self._last_rip_error = None
        # Post-rip daemons that died instead of returning a result. Cleared per
        # Start for the same reason as the results above: a crash recorded against
        # the previous album must not be reported against this one.
        self._post_rip_failures = {}
        # Rip generation, bumped every Start. Each post-rip verify daemon captures
        # the generation it launched under and drops its result if a NEWER rip has
        # started since — so a slow verify from album A (FLAC-verify waits up to
        # 120s) can't write its verdict into album B's report/UI after B begins.
        self._rip_generation += 1
        # Allow exactly one auto-heal retry (rip-as-unknown) per Start, so a
        # persistent failure can't loop.
        self._auto_retry_done = False
        # Disarm any pending auto-force-stop from a previous cancel, so its
        # countdown can't fire into this fresh rip.
        self._force_stop_timer.stop()
        self._force_stop_done = False
        self._force_stop_device = ""

        self._start_rip_worker(params)

    def _confirm_known_overwrite(self, params: RipParameters) -> RipParameters | None:
        """Guard a known-disc rip against silently overwriting an existing rip.

        Returns the params to rip with (possibly rewritten to a fresh numbered
        folder), or ``None`` if the user cancelled. If the target folder holds no
        audio, returns ``params`` unchanged (no dialog). Computing the folder and
        probing it are cheap local operations, and the dialog only waits on the
        user — nothing here blocks the GUI thread on I/O.
        """
        album = self._track_table.album_metadata()
        target = known_album_folder(
            Path(params.output_dir),
            params.disc_template,
            album.artist,
            album.title,
            album.year,
        )
        if not _dir_has_audio(target):
            return params  # nothing there to overwrite → proceed silently

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("Album already ripped")
        box.setText(
            f"“{target.name}” already contains a rip:\n{target}\n\n"
            "Ripping here will overwrite the existing files."
        )
        box.setInformativeText("Replace them, rip to a new numbered folder, or cancel?")
        # DestructiveRole flags the overwrite; AcceptRole is the safe keep-both.
        replace_btn = box.addButton("Replace", QMessageBox.ButtonRole.DestructiveRole)
        new_folder_btn = box.addButton(
            "Rip to a new folder", QMessageBox.ButtonRole.AcceptRole
        )
        cancel_btn = box.addButton(QMessageBox.StandardButton.Cancel)
        box.setDefaultButton(cancel_btn)  # safest default: do nothing
        box.exec()
        clicked = box.clickedButton()
        if clicked is replace_btn:
            return params
        if clicked is new_folder_btn:
            disc_template, track_template = free_album_folder_templates(
                Path(params.output_dir),
                params.disc_template,
                params.track_template,
                album.artist,
                album.title,
                album.year,
            )
            return replace(
                params,
                disc_template=disc_template,
                track_template=track_template,
            )
        return None  # Cancel (or the dialog was dismissed)

    def _as_unknown_params(self, params: RipParameters) -> RipParameters:
        """Return `params` rewritten for an unknown-album rip: `--unknown`,
        no release-id (so the ripper needs no network), and output templates
        built from the album fields the user sees (blanks → Unknown)."""
        album = self._track_table.album_metadata()
        artist = safe_path_segment(album.artist) or "Unknown Artist"
        title = safe_path_segment(album.title) or "Unknown Album"
        # Never silently overwrite a previous unknown disc's master: if this
        # album folder already holds audio (two different unknown discs at the
        # default "Unknown Album" would collide), land in a fresh "(N)" sibling.
        title = unique_album_title(Path(params.output_dir), artist, title)
        return replace(
            params,
            unknown=True,
            release_id="",
            track_template=f"{artist}/{title}/%t - Track %t",
            disc_template=f"{artist}/{title}/{title}",
        )

    def _start_rip_worker(self, params: RipParameters) -> None:
        """Spin up the rip worker thread for `params`. Shared by the initial
        Start and the auto-heal retry, so both wire signals identically."""
        # Snapshot the track table (MB lookup result + user edits) into the
        # params. whipper ignores it (it tags from --release-id itself);
        # cyanrip is fed these tags directly so it never needs its own
        # MusicBrainz lookup (Critical Rule #5, KDD-18 metadata model).
        album = self._track_table.album_metadata()
        # Genre / disc number / per-track ISRC are MusicBrainz-only silent
        # passthroughs (not editable in the table), so they come from the stored
        # release — and only when it matches THIS rip (guards a stale detail from
        # a previous disc, and unknown-album rips where release_id is "").
        detail = self._current_release_detail
        if detail is not None and detail.summary.mbid == params.release_id:
            genre = detail.summary.genre
            disc_number = detail.summary.disc_number
            total_discs = detail.summary.total_discs
            catalog_number = detail.summary.catalog_number
            barcode = detail.summary.barcode
            label = detail.summary.label
            isrc_by_number = {t.number: t.isrc for t in detail.tracks}
            # Per-track MusicBrainz durations (ms), same number-keyed passthrough
            # as ISRC. The worker uses these to weight the overall progress bar by
            # each track's real length so the ETA tracks wall-clock (a long track
            # is a bigger slice) instead of oscillating. Absent → equal-slice.
            length_ms_by_number = {t.number: t.length_ms for t in detail.tracks}
        else:
            genre, disc_number, total_discs, isrc_by_number = "", 1, 1, {}
            catalog_number, barcode, label = "", "", ""
            length_ms_by_number = {}
        # Which tracks to rip, from the "Rip?" checkboxes. All ticked → rip the
        # whole disc (empty tuple, no `-l`); a subset → just those track numbers
        # (cyanrip `-l`). The table's validate() already blocked a zero-selection
        # start, so a non-empty selection here is guaranteed for a real rip.
        only_tracks: tuple[int, ...] = (
            ()
            if self._track_table.all_tracks_selected()
            else tuple(self._track_table.selected_track_numbers())
        )
        params = replace(
            params,
            only_tracks=only_tracks,
            metadata=RipMetadata(
                album_artist=album.artist,
                album_title=album.title,
                year=album.year,
                genre=genre,
                disc_number=disc_number,
                total_discs=total_discs,
                catalog_number=catalog_number,
                barcode=barcode,
                label=label,
                tracks=tuple(
                    TrackTag(
                        number=t.number,
                        title=t.title,
                        artist=t.artist_credit,
                        isrc=isrc_by_number.get(t.number, ""),
                        length_ms=length_ms_by_number.get(t.number),
                    )
                    for t in self._track_table.tracks()
                ),
            ),
        )
        self._rip_controls.set_rip_active(True)
        self._set_rip_lock(True)  # grey out everything that would conflict mid-rip
        # Keep the window repainting during the rip (Plasma 6 Wayland black-window
        # belt — see MainWindow.__init__ / app.py XWayland preference).
        self._repaint_timer.start()
        # Remember the params so the finish handler knows the mode + output dir.
        self._active_rip_params = params

        self._rip_worker = RipWorker(self._backend, params)
        self._rip_thread = QThread(self)

        # Fresh rip → clear any leftover per-track status from a previous run so
        # the live Status column starts all-pending.
        self._track_table.reset_track_status()

        # Make the in-progress rip reachable from the moment it starts: Open rip
        # folder → the output directory (the album subfolder appears inside as
        # cyanrip works), View log → the real-time app log. So a frozen or
        # cancelled rip is never a dead end (the "Open rip folder did nothing
        # after I force-cancelled" report). set_log_path refines these to the
        # backend's own .log / folder at finish.
        self._rip_progress.begin_rip(Path(params.output_dir), LOG_PATH)
        # Arm the liveness watchdog: record "now" as the last-signal time and
        # start the timer. Any worker signal below refreshes it via
        # _note_rip_signal; the timer flags a stall when it goes quiet.
        import time as _time

        self._last_rip_signal_at = _time.monotonic()
        self._rip_liveness_timer.start()

        self._rip_worker.log_line.connect(self._rip_progress.append_log_line)
        self._rip_worker.progress.connect(self._rip_progress.set_progress)
        self._rip_worker.status.connect(self._rip_progress.set_status)
        # Feed the liveness watchdog: every worker signal is proof the rip is
        # alive, so refresh the last-signal timestamp (and clear any stall notice)
        # on each. Connected to the high-frequency signals — progress, status,
        # and raw log lines — so even a phase with no percent movement (encode,
        # verify) still counts as alive as long as output flows.
        self._rip_worker.log_line.connect(self._note_rip_signal)
        self._rip_worker.progress.connect(self._note_rip_signal)
        self._rip_worker.status.connect(self._note_rip_signal)
        # Follow the rip in the track table — highlight the row the ripper is on
        # and advance the live Status column (current row → ripping, each finished
        # track → done).
        self._rip_worker.current_track.connect(self._track_table.highlight_track)
        self._rip_worker.current_track.connect(self._track_table.mark_track_ripping)
        self._rip_worker.track_completed.connect(self._track_table.mark_track_done)
        self._rip_worker.error.connect(self._on_rip_error)
        self._rip_worker.finished.connect(self._on_rip_finished)

        # Standard one-shot teardown + start (finished → quit → deleteLater,
        # rip begins on start_rip when the thread spins up).
        start_worker_thread(
            self._rip_worker, self._rip_thread, self._rip_worker.start_rip
        )

    def _note_rip_signal(self, *_args: object) -> None:
        """Refresh the liveness clock — the rip just proved it's alive.

        Connected to every high-frequency worker signal. Also clears a showing
        stall notice the instant output resumes, so a brief slow patch that
        tripped the watchdog vanishes as soon as the drive gets going again.
        Ignores its signal args (it's wired to several differently-typed signals).
        """
        import time as _time

        self._last_rip_signal_at = _time.monotonic()
        self._rip_progress.set_stall_notice(None)

    def _check_rip_liveness(self) -> None:
        """Timer slot: surface a stall notice when the worker has gone quiet.

        Runs on the GUI thread and only reads a timestamp — never blocks. When
        the drive wedges, the worker parks in a blocking read and stops emitting,
        so `_last_rip_signal_at` stops advancing while this keeps ticking; once
        the gap crosses the threshold we show the notice (and keep the elapsed
        time fresh each tick). Guarded on a rip actually being in flight.
        """
        if self._rip_thread is None or self._last_rip_signal_at == 0.0:
            return
        import time as _time

        from platterpus.rip_timing import format_duration

        idle = _time.monotonic() - self._last_rip_signal_at
        if idle < _RIP_STALL_THRESHOLD_S:
            return
        # Name the most likely culprit when it applies: overread on the last
        # track is the confirmed lead-out-hang cause on some drives (BDR-209D).
        overread_hint = ""
        if (
            self._active_rip_params is not None
            and self._active_rip_params.force_overread
        ):
            overread_hint = (
                " Overread is on, which can hang some drives while reading the "
                "last track's lead-out — turn it off in Settings if this keeps "
                "happening."
            )
        self._rip_progress.set_stall_notice(
            f"⚠ No progress for {format_duration(idle)} — the drive may be stuck. "
            f"Cancel or Force stop to recover.{overread_hint}"
        )

    def _on_rip_cancel(self) -> None:
        if self._rip_worker is None:
            return
        # Cancel is the single most consequential thing a user can press during a
        # rip, and until now it wrote NOTHING to the log — so a report about a
        # cancel that misbehaved (a drive left spinning, a rip recorded as failed)
        # arrived with no record of when, or whether, it was even pressed. The
        # rescue deadline goes in the same line so the log carries the window a
        # reader has to reason about (rig session, 2026-07-30).
        log.info(
            "rip cancel requested by the user; arming the %ds force-stop rescue",
            _FORCE_STOP_COUNTDOWN_MS // 1000,
        )
        self._rip_cancelled = True
        self._force_stop_done = False
        # Capture the device NOW, not when the timer fires. Prefer the drive this
        # rip is actually using (`params.drive`) over whatever the picker happens
        # to show — the picker is a UI control the user can change during the five
        # seconds, and the rescue must target the drive that is still spinning.
        # Same precedence the auto-eject path already uses.
        active = getattr(self, "_active_rip_params", None)
        self._force_stop_device = (
            getattr(active, "drive", "") or self._drive_picker.current_device() or ""
        )
        # The in-container reader can take a moment to stop; set expectations,
        # and arm the auto force-stop in case it doesn't stop on its own.
        secs = _FORCE_STOP_COUNTDOWN_MS // 1000
        self._rip_progress.set_status(
            f"Cancelling rip… if the drive keeps spinning it'll be "
            f"force-stopped in {secs}s (or hit Force stop)."
        )
        self._rip_worker.cancel()
        self._force_stop_timer.start(_FORCE_STOP_COUNTDOWN_MS)

    def _auto_force_stop(self) -> None:
        """Countdown elapsed after Cancel — force-stop if we haven't already."""
        if self._force_stop_done:
            return
        self._do_force_stop("auto")

    def _on_force_stop_button(self) -> None:
        """User pressed Force stop — escalate immediately.

        Force-stop is enabled during a rip AND during a disc scan. With a rip
        in flight it's the rip escalation (kill + eject). With only a scan in
        flight (no rip), it's a stuck TOC read holding the drive — free it
        WITHOUT ejecting, so the disc stays in for a Rescan.
        """
        self._force_stop_timer.stop()
        rip_in_flight = self._rip_thread is not None
        scan_in_flight = (
            self._disc_info_thread is not None and self._disc_info_thread.isRunning()
        )
        if scan_in_flight and not rip_in_flight:
            self._scan_force_stopped = True
            self._free_drive_for_scan("manual")
        else:
            self._do_force_stop("manual")

    def _do_force_stop(self, trigger: str) -> None:
        """Eject + kill the in-container reader so the drive stops spinning.

        Runs on a daemon thread because `eject` and `distrobox enter` can each
        block for their timeout — we must not freeze the GUI. We don't touch
        widgets from the thread; the status is set here on the GUI thread
        first. See drive_control for the (user-approved) Rule #3 exception.
        """
        self._force_stop_done = True
        # Force stop is the user deliberately stopping the rip, so record it as a
        # CANCELLATION. Without this, only `_on_rip_cancel` set the flag, so
        # pressing Force stop on its own (the button is enabled for the whole rip)
        # produced status "Rip failed.", an `outcome.status = "failed"` in the JSON
        # report, an `*** INCOMPLETE RIP (failed) ***` banner in the durable log,
        # AND a failure notification — permanently recording a user's own choice as
        # a malfunction. Found by a rip-path audit, 2026-07-29; the honesty rule
        # this breaks is the same one the rest of the reporting code is built on.
        self._rip_cancelled = True
        # The armed device wins whenever we have one — for the auto trigger it is
        # the whole point (see `_force_stop_device`), and for a manual press during
        # a rip it is still the right target: "Force stop" means stop the thing
        # that is running, not whatever the picker is now pointing at.
        device = self._force_stop_device or self._drive_picker.current_device() or ""
        log.info(
            "force-stopping drive (%s trigger), device=%s armed=%s",
            trigger,
            device or "(default)",
            self._force_stop_device or "(none)",
        )
        self._rip_progress.set_status(
            "Force-stopping the drive (eject + stopping the reader)…"
        )
        thread = threading.Thread(
            target=drive_control.force_stop_drive,
            kwargs={"device": device},
            daemon=True,
        )
        self._force_stop_thread = thread
        thread.start()

    def _free_drive_for_scan(self, trigger: str) -> None:
        """Free a drive wedged by a stuck disc scan: kill the reader, no eject.

        Runs on a daemon thread because the kill + `distrobox enter` fallback
        can each block for their timeout — we never touch widgets from the
        thread. Unlike `_do_force_stop` it does NOT eject: the disc stays in so
        the user can Rescan. Used by the Force-stop button during a scan and
        automatically on a scan timeout (the in-container reader can keep
        holding the drive after the host-side subprocess gives up). See
        drive_control.free_drive for the user-approved Rule #3 exception.
        """
        device = self._drive_picker.current_device() or ""
        log.info(
            "freeing drive after scan (%s trigger), device=%s",
            trigger,
            device or "(default)",
        )
        thread = threading.Thread(
            target=drive_control.free_drive,
            kwargs={"device": device},
            daemon=True,
        )
        self._force_stop_thread = thread
        thread.start()

    def _stop_rip_on_shutdown(self) -> None:
        """Stop an in-flight rip when the window is closing — SYNCHRONOUSLY.

        This is the belt for a real-user bug (2026-07-01): closing the app while
        a rip ran left the drive spinning and the *next* track kept ripping until
        the disc was ejected by hand. ``closeEvent`` did call
        ``self._rip_worker.cancel()``, but that only kills the HOST-side wrapper's
        process group — on rootless podman/Distrobox the in-container reader
        (cyanrip) is a separate process tree that podman does **not** forward the
        signal into, so it keeps holding the drive (same fact the Force-stop path
        was built around — see ``drive_control``).

        The normal in-app Cancel copes by arming ``_force_stop_timer`` and
        escalating to ``force_stop_drive`` after a countdown. On window close that
        safety net is gone: the app tears down before any QTimer fires, and we
        can't offload the kill to a daemon thread either — the interpreter exits
        and kills that thread mid-``pkill``, so the reader is never stopped. So we
        must stop the in-container reader **synchronously, right here**, before
        ``closeEvent`` returns. This is the one deliberate exception to the
        never-block-the-GUI-thread rule: the window is already going away, and a
        bounded blocking kill is the whole point. It's fast in the common case
        (host ``pkill``/``fuser`` are instant because rootless in-container procs
        are host-visible); the slow ``distrobox enter`` fallback only runs if the
        host saw nothing, and is itself bounded by a subprocess timeout.

        Best-effort and gated on a rip actually being in flight (``_rip_thread``
        set) so a normal close never touches the drive. Does NOT eject — closing
        the app shouldn't pop the tray; it just has to stop the reader.
        """
        # A rip in flight is the obvious case, but not the only one. On Cancel the
        # host wrapper dies immediately (podman does not forward the signal into
        # the container), so the pipe EOFs, `_on_rip_finished` clears
        # `_rip_thread`, and the *only* thing left that would kill the in-container
        # reader is the 5-second `_force_stop_timer` rescue. Quit inside that
        # window and the old guard returned here, leaving the reader ripping with
        # no in-app recovery — and the drive's physical eject button is ignored
        # while a read holds the device, so no hardware recovery either. That is
        # the 2026-07-01 real-user bug reachable through a different door (found by
        # a rip-path audit, 2026-07-29). So: also stop when a force-stop is still
        # pending. `closeEvent` disarms that timer, which is why it must disarm it
        # AFTER calling us, not before.
        force_stop_pending = self._force_stop_timer.isActive()
        if self._rip_thread is None and not force_stop_pending:
            return
        log.info(
            "window closing with the drive possibly still reading "
            "(rip in flight: %s, force-stop pending: %s) — stopping the "
            "in-container reader",
            self._rip_thread is not None,
            force_stop_pending,
        )
        if self._rip_worker is not None:
            # Host-side: set the cancel flag + killpg the wrapper group.
            self._rip_worker.cancel()
        # The armed device, for the same reason the rescue timer captures it: the
        # picker is a live UI control and by the time we are closing it may point
        # at a drive that was never involved in this rip.
        device = self._force_stop_device or self._drive_picker.current_device() or ""
        try:
            # free_drive kills the in-container reader (host pkill → fuser →
            # distrobox-enter fallback) WITHOUT ejecting. Synchronous by design
            # (see docstring); best-effort and never raises on its own.
            #
            # BOUNDED. The sequence is up to seven subprocesses, each previously
            # capped at 20 s on its own, so a wedged drive could hold the window
            # in a closing state for over a minute — indistinguishable from a
            # hang, and the maintainer reports freezes as bugs because they are.
            # One shared budget caps the whole thing; a spent budget skips the
            # remaining steps and says so in the log.
            drive_control.free_drive(
                device=device,
                runner=drive_control.budgeted_runner(_SHUTDOWN_DRIVE_FREE_BUDGET_S),
            )
        except Exception:  # noqa: BLE001 — shutdown cleanup must never crash close
            log.exception("shutdown drive-free failed; ignored")

    def _on_eject_requested(self, device: str) -> None:
        """User clicked Eject — eject the selected disc."""
        self._eject_async(device, status="Ejecting the disc…")

    def _eject_async(self, device: str, status: str) -> None:
        """Eject `device` off a daemon thread, and say so when it does not work.

        `eject` can block for its subprocess timeout, so — like the force-stop — we
        never call it on the GUI thread. Still best-effort: a stuck tray does not
        deserve a modal dialog. But it does deserve to be *said*.

        **The bool used to be discarded.** `eject_drive`'s return value went
        nowhere, and its message was already destroyed at the source by a
        `stderr=DEVNULL`, so a tray that never opened left the status line reading
        "Ejecting the disc…" forever — an on-screen statement that was simply
        untrue, with nothing above INFO in the log to contradict it. The worker now
        reports back through a queued signal (never touching a widget off the GUI
        thread) and the status line is corrected. `drive_control.eject_drive` records
        the full diagnostic — argv, exit code, `eject`'s own words — either way.
        """
        log.info("ejecting device=%s", device or "(default)")
        self._rip_progress.set_status(status)

        def _eject_and_report() -> None:
            ok = False
            try:
                ok = drive_control.eject_drive(device=device)
            except Exception:  # noqa: BLE001 — a daemon thread must never crash
                log.exception("eject failed unexpectedly on %s", device or "(default)")
            # A QUEUED emit: this runs on a daemon thread and must not touch a
            # widget. `eject_finished` is connected to a GUI-thread slot.
            self.eject_finished.emit(bool(ok), device)

        thread = threading.Thread(target=_eject_and_report, daemon=True)
        self._eject_thread = thread
        thread.start()

    def _on_eject_finished(self, ok: bool, device: str) -> None:
        """Correct the status line once the eject actually finished (GUI thread).

        Only speaks on failure: a successful eject is self-evident — the tray is
        open — and overwriting a "Rip complete" headline with "ejected" would bury
        the result the user cares about.
        """
        if ok:
            return
        where = device or "the drive"
        message = (
            f"Could not eject {where} — it may still be in use. "
            f"The rip itself is unaffected; see the log for what eject reported "
            f"({LOG_PATH})."
        )
        log.warning("%s", message)
        self._rip_progress.set_status(message)
        self._rip_progress.append_log_line(message)

    def _notify_rip_complete(self, success: bool, detail: str) -> None:
        """Show a desktop notification that the rip finished (best-effort).

        Gated by the ``notify_on_completion`` setting. A user-cancelled rip is
        NOT announced (you just clicked Cancel). Uses a lazily-created
        ``QSystemTrayIcon`` message — pure PySide6, no external tool (so no
        dependency check, Critical rule #6) and no work on any slow path. Guarded
        so a missing tray / notification daemon degrades to a silent no-op and a
        courtesy notification can never crash the finish handler.
        """
        # Every branch below logs its outcome at INFO, and that is deliberate.
        # A toast is gone in eight seconds and nobody can prove afterwards
        # whether it appeared: the maintainer's first test of the v0.5.13 fix was
        # inconclusive purely because they were away from the screen when the rip
        # finished, and the log had nothing to say either way. A courtesy feature
        # still has to be *diagnosable* — "did it fire?" must be answerable from
        # log.txt alone, exactly like every other outcome we record.
        if not self._config.notify_on_completion:
            log.info("completion notification skipped: turned off in Settings")
            return
        if self._rip_cancelled:
            log.info("completion notification skipped: the rip was cancelled")
            return
        try:
            from PySide6.QtWidgets import QSystemTrayIcon

            from platterpus.notify import build_completion_message

            title, body = build_completion_message(success, self._rip_cancelled, detail)
            icon = self._ensure_tray_icon()
            if icon is None:
                log.info(
                    "completion notification skipped: this desktop reports no "
                    "usable system tray, so there is nowhere to post it"
                )
                return
            icon.showMessage(title, body, QSystemTrayIcon.MessageIcon.Information, 8000)
            log.info("completion notification posted: %s — %s", title, body)
        except Exception:  # noqa: BLE001 — a courtesy notification is never load-bearing
            # Kept at exception level (not debug): the v0.5.12 regression that
            # killed notifications outright hid in a swallowed AttributeError,
            # and a swallow nobody can see is how that shipped.
            log.exception("completion notification failed (best-effort)")

    def _ensure_tray_icon(self) -> QSystemTrayIcon | None:
        """Return the shared QSystemTrayIcon used for notifications, or None.

        Created lazily on first use (so users who turn notifications off never
        get a tray presence) and kept for the app's lifetime — ``showMessage``
        needs a visible tray icon. Returns None when the desktop has no usable
        system tray, so the caller simply skips the notification.
        """
        from PySide6.QtWidgets import QSystemTrayIcon

        # Declared on the shared seam (`main_window_shared`), so read it as an
        # attribute — a `getattr` here returned `Any` and silently defeated the
        # return-type check on this very method.
        existing = self._tray_icon
        if existing is not None:
            return existing
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return None
        icon = QSystemTrayIcon(self.windowIcon(), self)
        icon.setToolTip("Platterpus")
        icon.show()
        self._tray_icon = icon
        return icon

    def _on_set_cover_art_from_file(self) -> None:
        """Pick a local image to use as the front cover for the disc on screen.

        Stored on ``self._manual_cover_path`` and used by the next rip's cover-art
        step instead of the archive fetch (cleared when the disc changes). The
        file is validated to be a real JPEG/PNG/GIF at pick time so a wrong file
        is caught here, not silently at rip end.
        """
        from PySide6.QtWidgets import QFileDialog, QMessageBox

        from platterpus.adapters.cover_art import image_extension

        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Choose cover art image",
            "",
            "Images (*.jpg *.jpeg *.png *.gif);;All files (*)",
        )
        if not path_str:
            return  # cancelled
        try:
            head = Path(path_str).read_bytes()[:16]
        except OSError as exc:
            QMessageBox.warning(self, "Cover art", f"Couldn't read that file:\n{exc}")
            return
        if not image_extension(head):
            QMessageBox.warning(
                self, "Cover art", "That file isn't a JPEG, PNG, or GIF image."
            )
            return
        self._manual_cover_path = path_str
        self._rip_progress.set_status(
            f"Cover art set from “{Path(path_str).name}” — it will be used on the "
            "next rip of this disc."
        )

    def _on_rip_error(self, message: str) -> None:
        log.warning("rip error: %s", message)
        # Remember the last hard error so a no-log failure's minimal report can
        # carry it as the outcome's failure hint (see _write_minimal_failure_report).
        self._last_rip_error = message
        self._rip_progress.set_status(f"Error: {message}")

    def _on_rip_finished(self, success: bool, log_path: str) -> None:
        """The rip subprocess exited."""
        log.info("rip finished: success=%s log=%s", success, log_path)

        # Autonomous heal (inert whipper-era seam): a ripper that does its own
        # online lookup can abort when it can't fetch metadata. cyanrip runs -N
        # and never does, so this never fires today, but the GUI already has the
        # metadata (its own host-side MusicBrainz lookup), so re-rip as unknown —
        # which needs no network — and tag locally afterward. Once per Start.
        needs_retry = bool(self._rip_worker and self._rip_worker.needs_unknown_retry)
        params = self._active_rip_params
        if (
            not success
            and not self._rip_cancelled
            and needs_retry
            and params is not None
            and not params.unknown
            and not self._auto_retry_done
        ):
            self._auto_retry_done = True
            log.info("rip lacked online metadata — auto-retrying as unknown-album")
            self._rip_progress.set_status(
                "The ripper couldn't reach MusicBrainz — re-ripping without "
                "online metadata and tagging from what's on screen…"
            )
            unknown_params = self._as_unknown_params(params)
            # Defer so the just-finished thread fully unwinds before we start
            # a new worker/thread.
            QTimer.singleShot(0, lambda: self._start_rip_worker(unknown_params))
            return

        try:
            self._finish_rip(success, log_path)
        except Exception:  # noqa: BLE001 — a finish-handler slot must never crash
            log.exception("finish handler failed; rip state cleared in finally")
        finally:
            # BUG-5: ALWAYS release the rip lock + clear the rip-state references,
            # even if _finish_rip raised partway. These used to be linear at the
            # end of the handler, so an exception anywhere above left _rip_thread
            # set — and shutdown then treats a finished rip as still live (the
            # drive is left spinning, the UI stays disabled until an app restart).
            self._rip_controls.set_rip_active(False)
            self._set_rip_lock(False)  # rip over — re-enable the locked-down UI
            self._repaint_timer.stop()  # rip over — stop the Wayland repaint belt
            self._rip_liveness_timer.stop()  # rip over — disarm the stall watchdog
            self._rip_progress.set_stall_notice(None)  # clear any stall banner
            self._last_rip_signal_at = 0.0
            self._rip_worker = None
            self._rip_thread = None
            self._active_rip_params = None
            # Hook for tests to know that finish-time post-processing is done.
            self.rip_post_processing_done.emit()

    def _finish_rip(self, success: bool, log_path: str) -> None:
        """Body of the finish handler, after the auto-heal decision.

        Snapshots the worker's results, renders + reports the log, and spawns the
        off-thread post-rip work. ``_on_rip_finished`` wraps this in try/finally
        so the rip lock and rip-state references are ALWAYS cleared even if
        something here raises (BUG-5) — otherwise a finished rip looks live to
        shutdown and the drive is left spinning.
        """
        params = self._active_rip_params
        # Measure the actual wall-clock elapsed and record it against cyanrip's
        # own estimate. This is the ONLY place the real run time exists — cyanrip
        # logs the disc's audio length and a finish timestamp but never how long
        # the rip took. Captured here (worker still alive) before it's cleared.
        self._last_rip_timing = self._build_rip_timing()
        # Capture the read-speed ladder's per-pass history now, while the worker
        # is still alive (it's cleared below), so the report can record which
        # speed / -Z the disc needed — or that it never read clean at the floor.
        self._last_speed_attempts = getattr(self._rip_worker, "speed_attempts", [])
        # Tracks still unstable after the per-track auto-fix (couldn't be rescued)
        # — flagged in the report + results pane.
        self._last_unstable_tracks = getattr(self._rip_worker, "unstable_tracks", [])
        # The per-track auto-fix history (which unstable tracks were re-ripped and
        # whether the re-read converged / replaced the original).
        self._last_retried_tracks = getattr(self._rip_worker, "retried_tracks", [])
        # The parsed record of each re-rip that was swapped into the album — the
        # SHIPPED file's own read. Captured here (worker still alive) because the
        # whole-disc log only knows the first pass.
        self._last_swapped_tracks = getattr(
            self._rip_worker, "swapped_track_records", {}
        )
        # The "for posterity" ETA trace (PC clock + cyanrip's ETA + our ETA),
        # captured while the worker is alive; folded into the report below.
        self._last_eta_trace = getattr(self._rip_worker, "eta_trace", [])
        # v7 report (0.4.10): snapshot the PROCESS outcome + disc provenance +
        # the effective read offset NOW, while the worker and `params` are still
        # alive — both are cleared at the end of this handler, and the report is
        # re-written (debounced) afterwards, so these must be captured here and
        # read from self._last_* by _write_rip_report (never off the worker/params).
        from platterpus import rip_report as _rip_report

        if success:
            _status = "success"
        elif self._rip_cancelled:
            _status = "cancelled"
        else:
            _status = "failed"
        self._last_outcome = _rip_report.build_outcome(
            status=_status,
            # ONLY on a non-success outcome. The worker's hint is scraped from the
            # ripper's output, and on a *successful* rip that output can legitimately
            # contain a diagnostic about one track — a dynamic secure-rerip that did
            # not converge prints `Done; (no matches found, but hit repeat limit of
            # N)`. Storing that under `failure_hint` on a rip whose status is
            # "success" and whose exit code is 0 tells every consumer, and
            # `--audit-rips`, that this is why the rip failed. It did not fail. The
            # fact still reaches the user, through the read-stability line in the
            # EAC-style log and the warn banner, which is where it belongs
            # (real-hardware finding, 2026-08-03).
            failure_hint=(
                (
                    (self._rip_worker.failure_hint if self._rip_worker else "")
                    or getattr(self, "_last_rip_error", None)
                    or None
                )
                if _status != "success"
                else None
            ),
            # `_auto_retry_done` is set True when the "re-rip as unknown" self-heal
            # fired earlier this Start; the healed rip's report should say so.
            auto_unknown_retry_fired=self._auto_retry_done,
            auto_unknown_retry_reason=(
                "ripper could not reach MusicBrainz" if self._auto_retry_done else None
            ),
            # How the ripper actually ended, and what we told it to do. Read off
            # the worker here — this runs at finish, while `_rip_worker` is still
            # alive; the outcome dict is then snapshotted and survives the
            # worker being cleared. `getattr` so an older/stand-in worker without
            # these properties degrades to "not recorded" rather than raising in
            # the finish handler.
            ripper_exit_code=getattr(self._rip_worker, "ripper_exit_code", None)
            if self._rip_worker
            else None,
            ripper_argv=getattr(self._rip_worker, "ripper_argv", ())
            if self._rip_worker
            else (),
            ripper_argv_first_pass=getattr(
                self._rip_worker, "ripper_argv_first_pass", ()
            )
            if self._rip_worker
            else (),
        )
        _meta = params.metadata if params is not None else None
        # The release summary this rip's tags came from, for the medium
        # provenance below. None on an unknown-album rip, which has no
        # MusicBrainz release and so no medium to have resolved.
        _summary = getattr(
            getattr(self, "_current_release_detail", None), "summary", None
        )
        self._last_disc = {
            "unknown": bool(params.unknown) if params is not None else None,
            "musicbrainz_release_id": (self._current_release_id or None),
            # Release identifiers written as tags this rip (Picard-style), echoed
            # into the report so the one-file record carries the disc's canonical
            # IDs. None when MB had none / an unknown-album rip.
            "catalog_number": (getattr(_meta, "catalog_number", "") or None),
            "barcode": (getattr(_meta, "barcode", "") or None),
            "label": (getattr(_meta, "label", "") or None),
            # WHICH disc of a multi-disc release these tags came from, and how
            # we decided. A rip we could not resolve is still a rip, but the
            # report must say the titles may belong to another disc rather
            # than presenting them as settled (medium_select.py).
            "medium_basis": (getattr(_summary, "medium_basis", "") or None),
            "medium_detail": (getattr(_summary, "medium_detail", "") or None),
            "medium_undetermined": bool(
                getattr(_summary, "medium_undetermined", False)
            ),
        }
        # The read offset ACTUALLY handed to cyanrip (`-s`) for this rip — so the
        # report's settings.read_offset.effective is the truth, not just config.
        self._last_read_offset_effective = (
            params.read_offset_override if params is not None else None
        )
        # Why the dynamic secure re-rip did/didn't run (mode/engaged/skip reason).
        # getattr so this is None until the worker grows the property (wired next).
        self._last_secure_rerip = getattr(self._rip_worker, "secure_rerip_report", None)
        # SNAPSHOT THE RIPPER'S OUTPUT WHILE THE WORKER STILL EXISTS.
        #
        # The report is written MORE THAN ONCE — the first write happens here, then
        # every post-rip step (FLAC verify, transcode, CTDB, the self-check) triggers
        # a debounced re-write. `_on_rip_finished`'s `finally` sets `_rip_worker =
        # None` in between, and the writer read `getattr(self._rip_worker,
        # "captured_stdout", "")`. So the first write carried the ripper's output and
        # every later one REPLACED it with nothing — and since FLAC verify is on by
        # default and the self-check always runs, the file left on disk always had an
        # empty `ripper_stdout`.
        #
        # Found by reading a real rig artifact (2026-08-04): a clean 14/14 rip whose
        # `artifacts.ripper_stdout` was `{"path": null, "exists": false}` while its
        # `source` string still promised "complete even when the ripper was killed".
        # Accurate about the mechanism, false about the file — and it is the
        # kill-proof recovery source, the one artifact the cyanrip project cannot
        # produce for itself, and the thing round 7 lap 10 tells them we capture.
        #
        # A `_last_*` snapshot, like every other fact the report needs after the
        # worker is gone.
        self._last_ripper_stdout = (
            getattr(self._rip_worker, "captured_stdout", "") or ""
        )
        # The ripper's verdict on its own log (schema v18). Snapshotted for exactly
        # the same reason as the stdout above — the worker is cleared before the
        # debounced report re-writes, and a guard that emitted nothing rather than
        # keeping the value is what left `ripper_stdout` empty on every completed
        # rip. Same trap, so the same answer: keep the value.
        self._last_ripper_log_verification = getattr(
            self._rip_worker, "ripper_log_verification", None
        )

        # (The rip lock + repaint belt are released in _on_rip_finished's finally,
        # so they're reset even if anything below raises — BUG-5.)
        # Default status; replaced with a fidelity summary below if the
        # rip succeeded and we can parse its log. Distinguish a user
        # cancellation from a genuine failure (both report success=False).
        if success:
            status = "Done."
        elif self._rip_cancelled:
            status = "Rip cancelled by user. Partial files may remain."
        else:
            # Prefer an actionable sentence over the bare "Rip failed", so the user
            # knows what to do next — and read BOTH sources, in the same order the
            # report already does (see `failure_hint=` in `_last_outcome` above).
            #
            # THIS READ ONLY `failure_hint`. On every start/stream failure — the
            # backend never launched, the pipe died, the child was unreapable — the
            # ripper produced no stdout, so `failure_hint` is empty, so the last
            # thing the user saw was the generic sentence. Meanwhile the *specific*
            # one had been put on screen by `_on_rip_error` seconds earlier and
            # stashed in `_last_rip_error`, where the report reads it and the status
            # line did not: the one surface a user actually looks at was the only
            # one that threw the diagnosis away.
            #
            # Falls back to a sentence that at least names the log, rather than four
            # words that name nothing.
            hint = (self._rip_worker.failure_hint if self._rip_worker else "") or ""
            status = (
                hint.strip()
                or (getattr(self, "_last_rip_error", "") or "").strip()
                or f"Rip failed — no diagnosis was captured. See {LOG_PATH}"
            )
        self._rip_progress.set_status(status)

        if log_path:
            log_file = Path(log_path)
            self._rip_progress.set_log_path(log_file)
            # Parse and render AR results if the file exists.
            try:
                # errors="replace" (matching the worker's own _parse_log): a rip
                # log with a stray non-UTF-8 byte must NOT raise here — this runs
                # on the GUI thread, and a UnicodeDecodeError (a ValueError, which
                # the old `except OSError` didn't catch) would crash the finish
                # handler and abort the entire post-rip chain (no report, no
                # tagging, no cover art, no eject, and the rip state left uncleared
                # so shutdown thinks a rip is still live).
                # read_log_with_addendum folds in the auto-fix sidecar, which
                # supersedes the first pass's per-track record for any swapped
                # track (see platterpus.rip_addendum).
                text = read_log_with_addendum(log_file)
                # Sniff the format instead of trusting the configured
                # backend: a folder can hold logs from either ripper, and
                # the auto-heal path can change mid-session.
                if looks_like_cyanrip_log(text):
                    rip_log = parse_cyanrip_log(text)
                else:
                    rip_log = parse_rip_log(text)
                # cyanrip's log has no cache line, so its parsed
                # ``defeat_audio_cache`` is None. If we've MEASURED this drive's
                # cache-defeat verdict (cd-paranoia -A, stored in the drive
                # profile — KDD-29), fold it in so the EAC-compatible log and the
                # JSON report show the real Yes/No instead of "(unknown)".
                rip_log = self._inject_measured_cache_defeat(rip_log)
                # The whole-disc log records the FIRST pass only, so a track the
                # per-track auto-fix re-read and swapped in is still described by
                # the read we THREW AWAY. Fold the shipped read's own record (and
                # its convergence) in, so every surface below describes the audio
                # actually on disk (KDD-30).
                rip_log = self._apply_auto_fix_results(rip_log)
                # The disc's own track count and the rip's outcome, both already
                # known here (`_last_outcome` is built above, at build_outcome).
                # Without them the trust headline's denominator is the number of
                # tracks *in the log*, which shrinks with a cancelled rip — so
                # "all N tracks verified" went green over 2 of 14 (found on the
                # rig, 2026-07-30). Same two values the EAC exporter is given.
                finished_outcome = getattr(self, "_last_outcome", None)
                finished_status = (
                    str(finished_outcome.get("status") or "")
                    if isinstance(finished_outcome, dict)
                    else ""
                )
                # ONE number, handed to EVERY surface. `_current_num_tracks` is
                # always the DISC's count, so on its own it made a *deliberate*
                # partial rip (the Rip? column exists for exactly that) report "12
                # tracks were never ripped" — the user's own choice rendered as a
                # fault. `expected_track_total` folds in the selection, and the
                # reason it is computed here rather than inside each renderer is
                # that this bug has shipped four times by being fixed one renderer
                # at a time (audit finding, 2026-07-30).
                expected_total = expected_track_total(
                    getattr(self, "_current_num_tracks", 0) or None,
                    getattr(params, "only_tracks", ()) if params is not None else (),
                )
                # The report is re-written later (after CTDB, after the library
                # move) by which point `_active_rip_params` is cleared, so snapshot
                # the number rather than recomputing it from state that has moved.
                self._last_expected_track_total = expected_total
                self._rip_progress.set_rip_log(
                    rip_log,
                    disc_track_total=expected_total,
                    outcome_status=finished_status,
                )
                # Replace the disc panel's blank AccurateRip field with the
                # real outcome (e.g. "not in database" for a CD-R) instead of
                # the old misleading static "verified during rip".
                self._disc_info_panel.set_accuraterip_result(rip_log)
                if success:
                    status = fidelity_summary(
                        rip_log, expected_track_total=expected_total
                    )
                    self._rip_progress.set_status(status)
                    # A rip that MATCHED AccurateRip confirms the applied read
                    # offset is correct on THIS drive (KDD-31 — our equal-or-
                    # stronger analogue of EAC's Key-Disc offset check). Record
                    # that so the offset's provenance is promoted to CONFIRMED.
                    self._confirm_offset_from_accuraterip(rip_log)
                # Write the machine-readable JSON rip report beside the log
                # (the "two outputs every time" rule, docs/ux-design-principles
                # #2). Kept for the CTDB handler to re-write with the CTDB
                # verdict once that async check finishes.
                self._last_rip_log = rip_log
                self._last_rip_log_file = log_file
                # Now that the log is parsed, enrich the timing with the realtime
                # multiplier (elapsed ÷ the disc's audio length) — a meaningful
                # metric that replaces cyanrip's bogus ETA. Best-effort.
                self._enrich_timing_with_disc_duration(rip_log)
                self._write_rip_report(rip_log, log_file)
                # If a prior rip of THIS disc exists in the library, compare them
                # and surface a banner — the "you've ripped this before" catch for
                # a track that silently changed on a re-rip. Off-thread (it scans
                # the library); only meaningful on a successful, identified rip.
                if success:
                    self._start_rip_comparison(log_file)
                # Optional EAC-layout companion log beside the JSON report.
                self._write_eac_log(rip_log, log_file)
                # Surface the adaptive read-speed ladder's outcome in the results
                # pane when it actually did something — so a user who wasn't
                # watching the live log still sees that a disc needed a slow
                # re-read, or (loudly) that it never read clean at the floor.
                self._append_read_speed_summary()
                # The overall bar is driven from per-track progress, which caps
                # at 95% by design (the last 5% was reserved for a whipper-only
                # "length" phase that cyanrip never emits). On the sole supported
                # backend it therefore froze at 95% under a status line reading
                # "Done" — the textbook "works but feels broken" (audit finding,
                # 2026-07-28). Only on success: a cancelled or failed rip SHOULD
                # leave the bar where it stopped, because that is the truth.
                if success:
                    self._rip_progress.set_progress(100.0, 100.0)
            except OSError as exc:
                log.warning("could not read rip log %s: %s", log_file, exc)
            except Exception:  # noqa: BLE001 — GUI-thread finish handler: a
                # malformed log or a parser/report edge must never crash the
                # finish handler (which would abort the whole post-rip chain and
                # leave the rip state uncleared). Log and continue; the rest of
                # the chain (tagging, cover art, verify, eject, state clear) runs.
                log.exception("rendering rip results failed for %s", log_file)
        elif not success and not self._rip_cancelled:
            # No .log at all + a genuine failure (the backend never started, or
            # the stream died before any file was written) → today this wrote NO
            # report, so a hard failure was completely silent. Leave a minimal
            # one (outcome + settings + environment) beside the intended output
            # dir so the failure is still diagnosable. Best-effort; never raises.
            self._write_minimal_failure_report(params)

        # Desktop notification so an unattended rip announces itself even when
        # Platterpus isn't the focused window. Read the status back off the
        # widget rather than using the local `status`: that local was assigned
        # before `_append_read_speed_summary()` ran, so the notification — whose
        # entire audience is the user who walked away — said "all tracks ripped
        # cleanly" while the window said a track never read reproducibly (audit
        # finding, 2026-07-28). Best-effort; a user cancel is not announced.
        self._notify_rip_complete(
            success, self._rip_progress.current_status() or status
        )

        # Post-rip processing: unknown-mode tagging + backend-independent
        # cover art. Both shell out to metaflac on the SAME FLAC files, so
        # they run SEQUENTIALLY on ONE daemon thread (tag first, then embed
        # art) — never concurrently (two metaflac processes mutating one file
        # race → corrupted/lost tags or artwork). The whole block is off the
        # GUI thread because each step is a subprocess-per-file (~1-2s each):
        # on a 16-track album it would otherwise freeze the window for 15-30s
        # right when the rip finishes (CLAUDE.md "never block the GUI thread";
        # docs/architecture.md §3.2). Only on a successful rip.
        # The album folder the ripper just wrote: the .log lands next to the FLACs,
        # so its parent is that folder. Computed once — every post-rip step below
        # scopes to it (TD-5: this used to be recomputed 5×).
        #
        # **No log means no known album folder, and there is NO safe fallback.** This
        # used to fall back to `params.output_dir`, which is the configured output
        # ROOT — the whole music library. Every step below walks `rip_dir`
        # recursively, so that pointed tagging, colon-restore, recompress, transcode
        # and the checksum manifest at every album the user had ever ripped: MP3s
        # derived from the entire library, and a report that hashed it. The
        # library-move step already refused this case, which is evidence the hazard
        # was understood and simply not applied to its five siblings (audit,
        # 2026-07-29).
        #
        # It is reachable: `_find_log_path` filters by wall-clock mtime, so a backward
        # clock step (NTP) during a long rip drops the log it just wrote.
        rip_dir = Path(log_path).parent if log_path else None
        if success and params is not None and rip_dir is None:
            log.error(
                "rip reported success but no .log was found, so the album folder is "
                "unknown — skipping every post-rip step. Refusing to scope them to "
                "the output root (%s): that would sweep the whole library.",
                params.output_dir,
            )
            self._rip_progress.set_status(
                "Rip finished, but Platterpus could not find the rip log, so the "
                "post-rip checks were skipped. Your audio is in the output folder. "
                # WHICH log? The one it just said it could not find is the ripper's;
                # the one that explains why is the app's, and it was never named.
                f"The app log explains what it looked for: {LOG_PATH}"
            )
        if success and params is not None and rip_dir is not None:
            # Tagging — only when the rip we started was unknown-mode (an
            # identified disc is tagged by cyanrip itself, fed the GUI's -a/-t
            # tags). Scoping to `rip_dir` (not the configured output root) is what
            # keeps this from re-tagging every previously ripped album in the
            # library with THIS disc's metadata.
            tag = params.unknown
            # BUG-1: snapshot the track table HERE (on the GUI thread) — the
            # post-rip daemon must NOT read QWidgets. album_metadata()/tracks()
            # call into Qt models/QLineEdits, which aren't thread-safe; reading
            # them from the daemon was an undefined-behaviour data race on every
            # unknown-album rip. We pass the plain dataclasses into the thread.
            album_snapshot = self._track_table.album_metadata() if tag else None
            tracks_snapshot = list(self._track_table.tracks()) if tag else None
            # Output format: both backends rip to FLAC, so a non-FLAC choice
            # means a post-rip transcode (FLAC kept as the master). "flac" (or
            # any value we don't transcode) leaves transcode_fmt empty = no-op.
            transcode_fmt = (
                self._config.output_format
                if self._config.output_format in TRANSCODE_FORMATS
                else ""
            )
            # Cover art (2026-06-13): the ripper itself never fetches art —
            # cyanrip is fed tags and bypasses its own MusicBrainz lookup — so
            # the GUI fetches the front cover from the Cover Art Archive using
            # the release the user picked, and embeds/saves it per the cover-art
            # setting. A disc that was never identified has no release ID, so
            # plan_actions() makes this a no-op.
            embed, save_file = cover_art.plan_actions(
                mode=self._config.cover_art,
                ripper_fetches_art=False,
                release_id=self._current_release_id,
            )
            # WavPack/WAV can't carry an embedded cover (the transcode drops it —
            # FLAC/MP3 keep theirs), so for those formats make sure the front
            # cover still lands in the album folder as cover.<ext> — the only way
            # they get a visible cover. Force the folder save whenever art is
            # wanted (cover_art mode set) and the disc was identified, so a
            # folder copy always exists alongside any embedded one.
            if (
                transcode_fmt
                and transcode_fmt not in EMBEDS_COVER_ART
                and self._config.cover_art
                and (self._current_release_id or "").strip()
            ):
                save_file = True
            # Opt-in (off by default) FLAC re-compress — only for a backend that
            # doesn't already max compression. whipper encodes at flac's default
            # (`-5`), so re-encoding at `-8` can still shrink it; cyanrip already
            # maxes, so it's skipped there. Folded into the post-rip thread (it
            # mutates the same FLACs as tag/cover, so it MUST run after them, not
            # concurrently) — see _start_post_rip_processing.
            recompress = (
                self._config.recompress_flac_after_rip
                and not self._backend.produces_max_compression_flac()
            )
            # cyanrip can't take a literal ':' in its tag args, so we fed it the
            # ∶ lookalike; restore the real ':' in the written tags afterward
            # (KDD-22 colon handling). Only on the cyanrip path, and only when
            # the metadata actually contains a colon — so a colon-free album
            # (the common case) doesn't spin up the post-rip thread for nothing.
            restore_colons = self._metadata_has_colon()
            # A user-chosen cover image (Set cover art from file…) overrides the
            # archive fetch for THIS disc. Ensure it's at least embedded even if
            # auto cover-art is off, so an explicit choice is always honoured.
            local_cover = getattr(self, "_manual_cover_path", None)
            if local_cover and not (embed or save_file):
                embed = True
            if (
                tag
                or embed
                or save_file
                or recompress
                or transcode_fmt
                or restore_colons
                or local_cover
            ):
                self._start_post_rip_processing(
                    rip_dir,
                    tag=tag,
                    launch_picard=self._pending_picard_launch,
                    release_id=self._current_release_id,
                    embed=embed,
                    save_file=save_file,
                    recompress=recompress,
                    transcode_fmt=transcode_fmt,
                    mp3_vbr_quality=self._config.mp3_vbr_quality,
                    restore_colons=restore_colons,
                    album_metadata=album_snapshot,
                    track_rows=tracks_snapshot,
                    local_cover_path=local_cover,
                    # The rip's own record of which files it wrote. Already parsed
                    # above (`self._last_rip_log`), so hand it over rather than
                    # making each post-rip step re-read the log off disk — and so
                    # every step scopes to the same set of files. None when the log
                    # could not be parsed, in which case rip_files falls back to a
                    # folder scan and says so at WARNING.
                    rip_log=self._last_rip_log,
                )
                post_rip_thread = self._post_rip_thread
            else:
                post_rip_thread = None

            # Opt-in CTDB verify (KDD-14 Phase 1): a second, TOC-keyed
            # verification path alongside AccurateRip. Runs off the GUI thread
            # (network lookup + local FLAC decode), AFTER any post-rip metaflac
            # work settles (passed as wait_for) so it never decodes a file
            # mid-rewrite. Works for known and unknown discs (CTDB is keyed by
            # TOC, not MBID).
            if self._config.ctdb_verify_after_rip:
                self._start_ctdb_verify(rip_dir, wait_for=post_rip_thread)

            # Opt-in (default on) FLAC encode-verify — only for a backend that
            # doesn't already self-verify. whipper passes `flac --verify` during
            # the rip, so it's skipped there; cyanrip (FFmpeg) doesn't, so this
            # gives its rips the same decode==PCM guarantee. Off-thread, after
            # any metaflac rewrites settle (wait_for), like CTDB.
            if (
                self._config.verify_flac_after_rip
                and not self._backend.self_verifies_encode()
            ):
                self._start_flac_verify(rip_dir, wait_for=post_rip_thread)

            # Derived-file verify: when a non-FLAC output was produced, prove the
            # derived MP3/WavPack/WAV are good too — bit-identical to the FLAC
            # master for the lossless formats, decode-clean + complete for lossy
            # MP3 (honest per Critical Rule #4). Runs off-thread AFTER the
            # transcode (post_rip_thread) so it never reads a file mid-write.
            if transcode_fmt:
                self._start_derived_verify(
                    rip_dir, transcode_fmt, wait_for=post_rip_thread
                )

            # Per-file SHA256 digests for the report's integrity section. Always
            # on a successful rip (every format), after the post-rip thread so it
            # hashes the final masters + any derived files. Off-thread; folded
            # into the one debug report via checksums_done.
            self._start_checksums(rip_dir, wait_for=post_rip_thread)

            # Auto-move to the library (Settings "Move finished rips to", "" =
            # off): armed here, executed only once EVERY post-rip worker above
            # has settled — nothing may verify/hash/rewrite a file mid-move.
            self._maybe_schedule_library_move(rip_dir, params)

        # Auto-eject on a clean finish if the user opted in. Only on success —
        # a failed/cancelled rip leaves the disc in so the user can retry, and
        # ejecting mid-failure could fight the force-stop path.
        if success and self._config.auto_eject_after_rip:
            device = (
                params.drive
                if params is not None
                else self._drive_picker.current_device() or ""
            )
            self._eject_async(device, status="Rip complete — ejecting the disc…")

    # --- Convenience for the Unknown Album flow ----------------------------

    def _on_rip_as_unknown(self) -> None:
        """File → Rip as Unknown Album… menu action.

        Validates that a drive is selected, then opens the Unknown Album
        dialog. Sets unknown mode on the rip controls so the user can
        click Start without needing a MusicBrainz release ID.
        """
        if not self._drive_picker.current_device():
            QMessageBox.warning(
                self,
                "Cannot rip",
                "Select a drive first.",
            )
            return
        self.open_unknown_album_dialog()

    def open_unknown_album_dialog(self) -> bool:
        """Show the Unknown Album confirmation. Returns True if accepted.

        Exposed publicly so a future "Rip as unknown" button or menu
        action can drive it. After the dialog accepts, this method sets
        unknown mode on the rip controls and stashes the user's Picard
        preference for use after the rip finishes.
        """
        dialog = UnknownAlbumDialog(
            auto_launch_picard_default=self._config.auto_launch_picard,
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False
        self._rip_controls.set_unknown_mode(True)
        # Stash the user's Picard preference until after the rip finishes.
        self._pending_picard_launch: bool = dialog.auto_launch_picard()
        return True

    # --- Hook used by tests + the unknown flow -----------------------------

    def run_unknown_post_processing(
        self,
        rip_output_dir: Path,
        launch_picard: bool,
        album: AlbumMetadata | None = None,
        tracks: Sequence[TrackSummary] | None = None,
        rip_log: object | None = None,
    ) -> TaggingResult:
        """Tag the FLACs from the track table + optionally launch Picard.

        Called after an unknown-mode rip finishes. The track table holds the
        placeholder rows the user saw before ripping — including any edits they
        made to the titles/artist/album/year — so we write those through to the
        FLAC tags (blank fields fall back to the "Unknown" placeholders).

        ``album`` / ``tracks`` are the track-table snapshot taken on the GUI
        thread by the caller (BUG-1): this method runs on the post-rip DAEMON
        thread, where reading the Qt widgets directly is a data race. When they
        are omitted (a direct test/manual call), we read the table here — which
        is only safe on the GUI thread, so we assert that. Public so it can be
        exercised from tests.

        ``rip_log`` is this rip's already-parsed log, used to scope the tagging to
        the files THIS rip wrote (see :func:`_rip_master_paths`).

        Returns a :class:`TaggingResult` describing what actually happened.
        Returning it (rather than nothing) is the fix for a silent failure mode:
        ``apply_track_tags`` reports per-file failures only to the log file, so an
        album that shipped entirely untagged still ended with the window saying
        "Done." The caller hands this to the GUI thread, which tells the user and
        records it in the rip report.
        """
        if album is None or tracks is None:
            # Only reachable on a direct (test/GUI-thread) call — reading the
            # widgets off the GUI thread is the exact bug this signature exists
            # to prevent, so make the misuse loud rather than silently racy.
            assert threading.current_thread() is threading.main_thread(), (
                "run_unknown_post_processing read the track table off the GUI "
                "thread — snapshot it on the GUI thread and pass album/tracks in"
            )
            album = self._track_table.album_metadata()
            tracks = self._track_table.tracks()
        flac_files = _rip_master_paths(rip_output_dir, rip_log)
        tagged = apply_track_tags(self._metaflac, flac_files, album, tracks)
        # Whatever we tried to tag and did NOT get back is a failure. Deriving the
        # failures by difference (rather than trusting a count) covers BOTH of
        # apply_track_tags' ways of not tagging a file: a metaflac error, and a
        # filename with no leading track number (which it skips deliberately,
        # because guessing a TRACKNUMBER is worse than leaving it alone).
        succeeded = set(tagged)
        failures = tuple(p.name for p in flac_files if p not in succeeded)
        if launch_picard and flac_files:
            launch_picard_for(rip_output_dir)
        return TaggingResult(
            ran=True,
            attempted=len(flac_files),
            tagged=len(tagged),
            failures=failures,
        )

    def _metadata_has_colon(self) -> bool:
        """True if any metadata value fed to cyanrip contains a ``:``.

        Drives the cyanrip colon-restore (KDD-22): only worth a post-rip metaflac
        pass when a colon was actually substituted with the U+2236 lookalike. We
        check the assembled ``RipMetadata`` that was actually sent (album fields,
        year, genre, the release id, and every track's title/artist/isrc) rather
        than re-deriving from the track table — the table exposes only
        title/artist, so a colon in year/genre/isrc/albumid used to be missed and
        left un-restored (#29). Falls back to the current release id if no rip
        params are recorded (e.g. exercised directly in a test).
        """
        params = self._active_rip_params
        metadata = params.metadata if params is not None else None
        release_id = (
            params.release_id if params is not None else self._current_release_id
        )
        return _metadata_contains_colon(metadata, release_id)

    # --- Post-rip processing: tagging + cover art (one off-GUI thread) -------

    def _start_post_rip_processing(
        self,
        rip_dir: Path,
        *,
        tag: bool,
        launch_picard: bool,
        release_id: str,
        embed: bool,
        save_file: bool,
        recompress: bool = False,
        transcode_fmt: str = "",
        mp3_vbr_quality: int = 0,
        restore_colons: bool = False,
        album_metadata: AlbumMetadata | None = None,
        track_rows: Sequence[TrackSummary] | None = None,
        local_cover_path: object | None = None,
        rip_log: object | None = None,
    ) -> None:
        """Run unknown-mode tagging, then cover art, then FLAC re-compress, then
        an optional transcode, on ONE daemon thread.

        ``local_cover_path`` (when set) is a user-chosen image file used as the
        front cover *instead of* fetching from the Cover Art Archive — the "load
        cover art from a file" path.

        ``rip_log`` is the finish handler's already-parsed rip log. Every step
        below mutates or derives from the album's FLACs, so each is scoped to the
        files THIS rip wrote rather than to whatever is in the folder — see
        :func:`_rip_master_paths` for the leftover-file hazard. Passing the parsed
        log (instead of letting each step re-read it) means one parse, and one
        answer every step agrees on.

        ``album_metadata`` / ``track_rows`` are the track-table snapshot taken on
        the GUI thread (BUG-1) and handed to the daemon's tagging step — the
        daemon must never read the Qt widgets itself.

        Why one thread, in this order: the first two steps shell out to
        ``metaflac`` on the SAME FLAC files, and the re-compress step *rewrites*
        those same files — so all three MUST run sequentially: tag first, then
        embed/save the front cover, then re-compress. Two processes mutating one
        FLAC at the same time race each other and corrupt or lose the tags,
        artwork, or audio. Re-compress runs after the metaflac work so it
        operates on the final, fully-tagged-and-arted files (``flac`` preserves
        their tags and embedded art when it re-encodes). The transcode runs
        **last** of all, so it reads the final FLACs (tagged, arted, and
        possibly re-compressed) and derives the chosen output format from them;
        it writes *sibling* files and never touches the FLAC, so it can't race
        the earlier steps. Running them on one worker (rather than several) is
        what guarantees the ordering.

        Why off the GUI thread at all: each step is a subprocess per file
        (~1-2s), so a multi-track album would freeze the event loop for tens of
        seconds right when the rip finishes — exactly the "Not Responding"
        class of bug CLAUDE.md forbids (docs/architecture.md §3.2). The
        cover-art fetch is also a network call, which never belongs on the GUI
        thread either.

        Best-effort end to end: tagging, ``apply_cover_art`` and
        ``recompress_flac_files`` each guard their own failures so a stray bug
        here can't take down the app. The cover-art and re-compress outcomes are
        reported back through ``cover_art_done`` / ``flac_recompress_done``
        (queued cross-thread signals, so the slots run on the GUI thread); each
        emit is guarded because the window may have been closed while the work
        ran.

        Not joined in ``closeEvent``: it's a daemon thread that guards its own
        emit (the same pattern the cover-art fetch always used). Tests join the
        handle on ``self._post_rip_thread`` for determinism.
        """
        gen = self._rip_generation  # drop the transcode result if a newer rip starts

        def work() -> None:
            # 0) Restore the real ':' in cyanrip's tags (it was fed the ∶
            #    lookalike because its parser can't take a literal colon). Runs
            #    FIRST so cover-art and the transcode see the corrected tags.
            #    Never raises; a no-op for colon-free albums.
            if restore_colons:
                from platterpus.adapters.cyanrip_backend import (
                    restore_substituted_colons,
                )

                fixed = restore_substituted_colons(
                    self._metaflac, _rip_master_paths(rip_dir, rip_log)
                )
                if fixed:
                    log.info("colon-restore: fixed tags in %d file(s)", fixed)
            # 1) Tagging next. run_unknown_post_processing is the synchronous
            #    worker body (tests call it directly); we just invoke it here,
            #    off the GUI thread, instead of inline in _on_rip_finished.
            if tag:
                try:
                    # Pass the GUI-thread snapshot in — the daemon must not read
                    # the track-table widgets itself (BUG-1).
                    tag_result = self.run_unknown_post_processing(
                        rip_dir,
                        launch_picard,
                        album=album_metadata,
                        tracks=track_rows,
                        rip_log=rip_log,
                    )
                except Exception as exc:  # noqa: BLE001 — must never crash the GUI
                    log.exception("unknown-album post-processing failed")
                    # A crash mid-pass is still a tagging outcome the user has to
                    # hear about: some files may carry tags, the rest do not, and
                    # before this the whole thing vanished into the log file.
                    tag_result = TaggingResult(
                        ran=True, error=f"{type(exc).__name__}: {exc}"
                    )
                if self._rip_generation != gen:
                    return  # a newer rip started — this result is for the old album
                try:
                    self.tagging_done.emit(tag_result)
                except RuntimeError:  # window destroyed — nothing to update
                    pass
            # 2) Cover art second, only after tagging has fully finished so the
            #    two never touch a FLAC at the same time.
            if embed or save_file:
                try:
                    if local_cover_path:
                        # User-chosen image wins over the archive fetch.
                        art_result = cover_art.apply_local_cover_art(
                            rip_dir,
                            Path(str(local_cover_path)),
                            embed=embed,
                            save_file=save_file,
                            metaflac=self._metaflac,
                            # Scope the embed to the files THIS rip wrote, so a
                            # leftover from an earlier rip isn't given this
                            # album's cover (and isn't counted in "embedded in
                            # N track(s)").
                            rip_log=rip_log,
                        )
                    else:
                        art_result = cover_art.apply_cover_art(
                            rip_dir,
                            release_id,
                            embed=embed,
                            save_file=save_file,
                            metaflac=self._metaflac,
                            fetcher=self._cover_art_fetcher,
                            # The config mode is recorded in the report so it knows
                            # art was *requested* (a plain attribute read — no Qt).
                            mode=self._config.cover_art,
                            rip_log=rip_log,  # this rip's files only
                        )
                except Exception:  # noqa: BLE001 — art must never crash the GUI
                    log.exception("cover art post-processing failed")
                    art_result = cover_art.CoverArtResult(
                        mode=self._config.cover_art,
                        found=False,
                        reason="error",
                        error="failed unexpectedly",
                        message="Cover art: failed unexpectedly (rip unaffected).",
                    )
                # Also grab the back cover + booklet scans, saved as files (they
                # can't be embedded in FLAC). Only when front art was fetched from
                # the archive (a local override has no manifest to consult).
                # Recorded on the result so the report captures the whole package.
                if (
                    self._config.save_additional_art
                    and not local_cover_path
                    and (release_id or "").strip()
                ):
                    try:
                        art_result.additional_saved = cover_art.save_additional_covers(
                            rip_dir, release_id, fetcher=self._cover_art_fetcher
                        )
                    except Exception:  # noqa: BLE001 — extra art must never crash
                        log.exception("additional cover art fetch failed")
                # Same generation guard the transcode step below carries: the
                # cover fetch is the SLOWEST post-rip step (a Cover Art Archive
                # HTTP GET with a 30 s timeout), so it is the one most likely to
                # land after the user has already started the next rip — and
                # `_on_cover_art_done` writes straight into whatever album's
                # report is current, naming a release that album never used
                # (audit finding, 2026-07-28).
                if self._rip_generation != gen:
                    return  # a newer rip started — this result is for the old album
                try:
                    self.cover_art_done.emit(art_result)
                except RuntimeError:  # window destroyed — nothing to update
                    pass
            # 3) Re-compress LAST, so it rewrites the final tagged-and-arted
            #    FLACs (flac preserves their tags + embedded art). Best-effort;
            #    each file is swapped in atomically, so a failure or crash leaves
            #    the original untouched. Outcome reported via flac_recompress_done.
            if recompress:
                try:
                    result = recompress_flac_files(_rip_master_paths(rip_dir, rip_log))
                except Exception:  # noqa: BLE001 — must never crash the GUI
                    log.exception("FLAC re-compress failed unexpectedly")
                    result = RecompressResult(error="failed unexpectedly")
                if self._rip_generation != gen:
                    return  # a newer rip started — this result is for the old album
                try:
                    self.flac_recompress_done.emit(result)
                except RuntimeError:  # window destroyed — nothing to update
                    pass
            # 4) Transcode LAST, reading the final FLACs (tagged, arted, and
            #    possibly re-compressed) to derive the chosen non-FLAC output.
            #    Writes sibling files and keeps the FLAC as the master; never
            #    raises. Outcome reported via transcode_done.
            if transcode_fmt:
                try:
                    tresult = transcode_files(
                        _rip_master_paths(rip_dir, rip_log),
                        fmt=transcode_fmt,
                        mp3_vbr_quality=mp3_vbr_quality,
                    )
                except Exception:  # noqa: BLE001 — must never crash the GUI
                    log.exception("transcode failed unexpectedly")
                    tresult = TranscodeResult(error="failed unexpectedly")
                if self._rip_generation != gen:
                    return  # a newer rip started — this result is for the old album
                try:
                    self.transcode_done.emit(tresult)
                except RuntimeError:  # window destroyed — nothing to update
                    pass

        log.info(
            "post-rip processing in %s "
            "(tag=%s, cover-art embed=%s save=%s, recompress=%s, transcode=%s)",
            rip_dir,
            tag,
            embed,
            save_file,
            recompress,
            transcode_fmt or "no",
        )
        thread = threading.Thread(target=work, daemon=True)
        self._post_rip_thread = thread
        thread.start()

    def _on_cover_art_done(self, result: object) -> None:
        """Cover-art thread finished — record the outcome (runs on the GUI thread).

        Carries a :class:`~platterpus.adapters.cover_art.CoverArtResult` (folded
        into the report's ``cover_art`` block); a bare string is still accepted
        for back-compat (older callers / tests). The human line goes to the log
        view either way.
        """
        if isinstance(result, cover_art.CoverArtResult):
            self._last_cover_art_result = result
            self._schedule_rip_report_write()
            message = result.message or "Cover art applied."
        elif isinstance(result, str):
            message = result
        else:
            return
        log.info("%s", message)
        self._rip_progress.append_log_line(message)

    def _on_tagging_done(self, result: object) -> None:
        """Post-rip tagging finished — surface + record it (runs on the GUI thread).

        Why this slot exists (2026-07-31): ``apply_track_tags`` writes a WARNING
        per failed file and returns the successes, and the caller discarded that
        return value. Nothing else looked at it: no signal, no status line, no
        report field. So the failure mode "the disk filled during the metaflac
        pass, so every FLAC shipped untagged" ended with the window saying "Done."
        and a rip report that mentioned tagging nowhere. This makes it visible in
        all three places the project treats as the record — the status line, the
        rip log view, and the JSON report.

        The trust banner is downgraded too. The audio claim it makes ("these bytes
        matched AccurateRip") is still true — untagged FLACs are still bit-perfect
        — but a green ✓ over an album that carries none of its metadata is exactly
        the silent-success this codebase keeps having to fix, and the north star is
        a complete library entry, not just correct bytes.
        """
        if not isinstance(result, TaggingResult):
            return
        # Recorded even when it went fine, so the report can state positively that
        # tagging ran (an absent field is the ambiguity `verification.gates` was
        # invented to remove).
        self._last_tagging_result = result
        self._schedule_rip_report_write()
        if result.error:
            # A whole-pass failure: we cannot say which files got tags.
            message = (
                f"⚠ Tagging FAILED — the tags from the track table could not be "
                f"written ({result.error}). The audio is unaffected; you can tag "
                "the files with Picard."
            )
        elif result.failures:
            names = ", ".join(result.failures)
            message = (
                f"⚠ Tagging FAILED for {len(result.failures)} of "
                f"{result.attempted} file(s): {names}. The audio is unaffected; "
                "see the app log for each failure."
            )
        else:
            message = f"Tagging: {result.tagged} file(s) tagged from the track table."
        if result.ok:
            log.info("%s", message)
        else:
            log.warning("%s", message)
            # Loud: the status line is the one surface a user who walked away will
            # read, and "Done." over an untagged album is a lie of omission.
            self._rip_progress.set_status(message)
            failed_count = len(result.failures) or result.attempted
            self._rip_progress.downgrade_verdict(
                f"tags could not be written to {failed_count} file(s)"
                if failed_count
                else "the tagging step failed"
            )
        self._rip_progress.append_log_line(message)

    # --- Shared post-rip daemon launcher -----------------------------------

    def _launch_post_rip_daemon(
        self,
        compute: Callable[[], object],
        signal: object,
        thread_attr: str,
    ) -> threading.Thread:
        """Run a post-rip check on a daemon thread, guarded by the rip generation.

        ``compute`` is a no-arg callable that does the off-thread work (a network
        lookup + FLAC decode, a hash sweep, …) and returns its result — or
        ``None`` to signal "skip, don't emit" (e.g. the checksum step when the
        post-rip work didn't settle in time). If a NEWER rip has started since
        this was launched, the result is dropped; otherwise it's delivered via
        ``signal`` (a queued Qt signal), guarded against a destroyed window. The
        thread is stored on ``self.<thread_attr>`` so tests can join it.

        TD-2: this is the ONE place the rip-generation staleness guard lives —
        the correctness property that stops a slow verify from album A writing
        its verdict into album B's report/UI. Extracting it means a new post-rip
        check can't accidentally omit the guard by copy-pasting a launcher.

        Daemon + guarded emit (not a QThread) is deliberate: a full-album decode
        can outlast any reasonable ``closeEvent`` wait, and destroying a running
        QThread aborts the app (docs/architecture.md §3.2). The daemon dies with
        the process and never touches a widget except through the queued signal.

        ``compute`` is guarded: an exception escaping it used to kill the daemon
        thread with no signal emitted and nothing recorded, and a dead thread reads
        as "settled" to :meth:`_post_rip_work_settled` — so the library move went
        ahead exactly as if the check had passed. See
        :meth:`_record_post_rip_failure`.
        """
        gen = self._rip_generation  # drop the result if a newer rip starts

        def runner() -> None:
            try:
                result = compute()
            except Exception as exc:  # noqa: BLE001 — see below
                # A crashed check must not be INDISTINGUISHABLE from a passed one.
                # Two things happen here and both matter: it is logged (so the
                # failure is diagnosable at all), and it is *recorded on the
                # window*, which is what lets the settlement logic — the gate in
                # front of the library move — tell "every check finished" apart
                # from "a check died on its way to finishing". `threading`'s
                # default excepthook logs an escaping exception since v0.5.18, but
                # a log line no code reads cannot change a decision.
                log.exception("post-rip step %s failed", thread_attr)
                self._record_post_rip_failure(
                    thread_attr, f"{type(exc).__name__}: {exc}"
                )
                return
            if result is None:
                return  # the work opted out (e.g. didn't settle) — nothing to emit
            if self._rip_generation != gen:
                return  # a newer rip started — this result is for the old album
            try:
                signal.emit(result)  # type: ignore[attr-defined]
            except RuntimeError:  # window already destroyed — nothing to update
                pass

        thread = threading.Thread(target=runner, daemon=True)
        setattr(self, thread_attr, thread)
        thread.start()
        return thread

    def _record_post_rip_failure(self, step: str, detail: str) -> None:
        """Record that a post-rip daemon died instead of producing a result.

        Called from the failing daemon thread, so it must touch no widget — it only
        writes a plain dict, which the GUI thread reads later (in
        :meth:`_poll_library_move`). ``step`` is the thread attribute the check was
        stored under (``"_ctdb_thread"``, ``"_checksums_thread"``, …), which is the
        one name that identifies the check uniquely.

        The dict is created on first failure rather than in ``__init__`` because
        the failure path is (and should stay) rare; the lock is there because two
        checks can die in the same instant and a lost record defeats the purpose.
        """
        with _POST_RIP_FAILURE_LOCK:
            failures: dict[str, str] | None = getattr(self, "_post_rip_failures", None)
            if failures is None:
                failures = {}
                self._post_rip_failures = failures
            failures[step] = detail

    # --- Post-rip CTDB verify (opt-in, KDD-14 Phase 1) ----------------------

    def _start_ctdb_verify(
        self, rip_dir: Path, wait_for: threading.Thread | None
    ) -> None:
        """Verify the just-finished rip against CTDB on a daemon thread.

        The lookup (network) and the local FLAC decode (a `flac` subprocess per
        track) must not run on the GUI thread. ``wait_for`` is the post-rip
        metaflac thread (or None): we join it first so we never decode a FLAC
        mid-rewrite. The verdict is reported via ``ctdb_verify_done`` (queued to
        the GUI thread). Threading/generation guard: see
        :meth:`_launch_post_rip_daemon`.
        """
        log.info("starting CTDB verify for %s", rip_dir)
        self._rip_progress.set_ctdb_status("Verifying against CTDB…")
        self._launch_post_rip_daemon(
            compute=lambda: verify_rip_dir(
                self._ctdb_client, rip_dir, wait_for=wait_for
            ),
            signal=self.ctdb_verify_done,
            thread_attr="_ctdb_thread",
        )

    def _on_ctdb_verified(self, result: object) -> None:
        """CTDB verify finished — render the verdict under the AR table.

        Runs on the GUI thread (ctdb_verify_done is queued there). `result` is
        a ctdb.verify.CtdbVerifyResult; rip_progress labels an unvalidated
        match "experimental" (KDD-16).
        """
        self._rip_progress.set_ctdb_result(result)  # type: ignore[arg-type]
        verdict = getattr(getattr(result, "verdict", None), "value", "?")
        log.info("CTDB verify verdict: %s", verdict)
        # Record + schedule a (debounced) re-write so the report picks up the
        # CTDB verdict alongside whatever else has finished.
        self._last_ctdb_result = result
        self._schedule_rip_report_write()

    # --- Re-rip comparison ("you've ripped this disc before") ---------------

    def _start_rip_comparison(self, log_file: Path) -> None:
        """Compare this rip against a prior rip of the same disc, off-thread.

        Scans the configured output library for a ``.platterpus.json`` with the
        same disc identity as the rip that just finished; if one is found, builds
        the track-by-track comparison and surfaces it via ``rip_comparison_done``
        (queued to the GUI thread). Returns nothing to emit — so no banner — when
        there's no prior rip (the common case) or the reports can't be read.

        The scan is filesystem I/O over the whole library, so it runs on a daemon
        (never the GUI thread), guarded by the rip generation like every other
        post-rip check (see :meth:`_launch_post_rip_daemon`). Best-effort: the
        pure ``rip_compare`` helpers never raise.
        """
        from platterpus import rip_compare, rip_report

        report_path = rip_report.report_path_for(log_file)
        output_root = Path(self._config.output_dir)
        # With auto-move on, prior rips live in the LIBRARY folder, not the
        # output workspace — scan it too (snapshotted here, on the GUI thread).
        library_text = (self._config.library_dir or "").strip()
        extra_roots = (Path(library_text),) if library_text else ()

        def compute() -> object:
            current = rip_compare.load_report(report_path)
            if current is None or not current.get("tracks"):
                return None  # nothing to compare against
            prior = rip_compare.find_prior_report(
                report_path,
                output_root,
                current_report=current,
                extra_roots=extra_roots,
            )
            if prior is None:
                return None  # no earlier rip of this disc → no banner
            other = rip_compare.load_report(prior)
            if other is None:
                return None
            # `other` is the earlier rip (A); `current` is this one (B).
            return rip_compare.compare_reports(
                other,
                current,
                label_a=rip_compare.report_label(other, fallback=str(prior)),
                label_b=rip_compare.report_label(current, fallback=str(report_path)),
            )

        self._launch_post_rip_daemon(
            compute=compute,
            signal=self.rip_comparison_done,
            thread_attr="_comparison_thread",
        )

    def _on_rip_comparison_done(self, comparison: object) -> None:
        """Render the re-rip comparison banner (queued to the GUI thread)."""
        self._rip_progress.set_comparison(comparison)
        log.info("re-rip comparison: %s", getattr(comparison, "summary", ""))

    # --- Auto-move finished rips to the library ------------------------------

    def _maybe_schedule_library_move(
        self, rip_dir: Path, params: RipParameters
    ) -> None:
        """Arm the library move for a just-finished successful rip.

        The move itself must wait for every post-rip worker (tag/cover/
        transcode, the verification suite, checksums, the comparison scan) and
        the debounced report write — moving the folder under a live verify
        would hand it a vanished path mid-decode. So this only records the
        intent and starts the settlement poll; :meth:`_poll_library_move` fires
        the actual move once everything has wound down. No-op when the feature
        is off (empty ``library_dir``).
        """
        library_text = (self._config.library_dir or "").strip()
        if not library_text:
            return
        # Only ever move a real per-album folder. When no rip log was found,
        # the caller's rip_dir FELL BACK to the output root — "moving" that
        # would relocate the user's whole workspace into the library. Refuse.
        try:
            is_output_root = (
                Path(rip_dir).resolve() == Path(params.output_dir).resolve()
            )
        except OSError:
            is_output_root = rip_dir == params.output_dir
        if is_output_root:
            log.warning(
                "library move skipped: the album folder could not be identified "
                "(no rip log), so there is nothing safe to move"
            )
            return
        self._pending_library_move = (
            Path(rip_dir),
            Path(library_text),
            self._rip_generation,
        )
        self._library_move_timer.start()

    def _post_rip_work_settled(self) -> bool:
        """True when every post-rip worker is done and no report write pends.

        The settlement gate for the library move: all the daemon threads the
        finish handler may have spawned (tag/cover/transcode, CTDB, FLAC
        verify, derived verify, checksums, the comparison scan) plus the
        debounced report timer. ``getattr`` with a default because the thread
        attributes only exist once their first launch happened this session.

        Deliberately answers "is anything still touching the files?", NOT "did
        every check pass" — a check that *crashed* is finished, and blocking the
        move on it would strand the album in the workspace forever. What the crash
        must not do is pass unmentioned, so the caller reads
        :meth:`_post_rip_failure_summary` before it moves anything.
        """
        for attr in (
            "_post_rip_thread",
            "_ctdb_thread",
            "_flac_verify_thread",
            "_derived_verify_thread",
            "_checksums_thread",
            "_comparison_thread",
        ):
            thread = getattr(self, attr, None)
            if thread is not None and thread.is_alive():
                return False
        return not self._rip_report_timer.isActive()

    def _post_rip_failure_summary(self) -> str:
        """One line naming every post-rip check that died, or ``""`` if none did.

        The readable half of :meth:`_record_post_rip_failure`: it turns the
        ``{thread attribute: error}`` record into something a human can act on. The
        leading ``_`` and trailing ``_thread`` are stripped because the attribute
        name is an implementation detail — "ctdb", "checksums" is what the user
        recognises.
        """
        failures: dict[str, str] = getattr(self, "_post_rip_failures", {}) or {}
        if not failures:
            return ""
        named = ", ".join(
            f"{attr.strip('_').removesuffix('_thread')} ({detail})"
            for attr, detail in sorted(failures.items())
        )
        return named

    def _poll_library_move(self) -> None:
        """Settlement-poll slot: fire the armed library move once it's safe.

        Runs on the GUI thread every 500ms while a move is pending. Abandons
        the move if a newer rip has started (its folder stays in the output
        directory — moving it then would race the new rip's post-rip state);
        otherwise waits for :meth:`_post_rip_work_settled`, flushes the report
        (so the finished JSON travels WITH the folder), and hands the actual
        filesystem move to a daemon thread via the shared generation-guarded
        launcher.

        A post-rip check that CRASHED still lets the move proceed — the audio is
        fine and stranding it in the workspace would be the worse outcome — but it
        is announced first. Before this, a crashed daemon was indistinguishable
        from a passed one here, so the album was filed away with the user having
        been told nothing at all (see :meth:`_record_post_rip_failure`).
        """
        pending = self._pending_library_move
        if pending is None:
            self._library_move_timer.stop()
            return
        rip_dir, library, generation = pending
        if generation != self._rip_generation:
            self._pending_library_move = None
            self._library_move_timer.stop()
            log.info("library move of %s abandoned: a newer rip started", rip_dir)
            return
        if not self._post_rip_work_settled():
            return  # keep polling
        self._pending_library_move = None
        self._library_move_timer.stop()
        crashed = self._post_rip_failure_summary()
        if crashed:
            message = (
                "⚠ A post-rip check did not finish, so its result is missing from "
                f"this rip's record: {crashed}. Filing the rip anyway — the audio "
                "itself is unaffected."
            )
            log.warning("%s", message)
            self._rip_progress.append_log_line(message)
        # The debounced report write targets the CURRENT path — flush it now so
        # the complete report moves with the folder instead of being written
        # into a folder that no longer exists.
        self._flush_rip_report()
        self._rip_progress.append_log_line(
            f"Filing the rip in your library: {library} …"
        )
        from platterpus import library_move

        self._launch_post_rip_daemon(
            compute=lambda: library_move.move_album_folder(rip_dir, library),
            signal=self.library_move_done,
            thread_attr="_library_move_thread",
        )

    def _on_library_moved(self, result: object) -> None:
        """The library move finished (queued to the GUI thread).

        On success, repoint everything that references the album's old home —
        the View log / View report / Open rip folder buttons and the cached
        report path (so any defensive late report write lands in the folder's
        NEW location, never resurrects the old one). On failure the rip simply
        stays in the output directory: the rip itself already succeeded, so
        this reports, it never alarms.
        """
        message = str(getattr(result, "message", ""))
        destination = getattr(result, "destination", None)
        if not bool(getattr(result, "ok", False)) or destination is None:
            log.warning("library move failed: %s", message)
            self._rip_progress.append_log_line(
                f"⚠ Library move failed — the rip stayed in the output folder "
                f"({message})."
            )
            return
        new_dir = Path(destination)
        if self._last_rip_log_file is not None:
            new_log = new_dir / self._last_rip_log_file.name
            self._last_rip_log_file = new_log
            self._rip_progress.set_log_path(new_log)
        self._rip_progress.append_log_line(f"✓ Rip filed in your library: {new_dir}")
        log.info("library move complete: %s", new_dir)

    def _build_rip_timing(self) -> dict | None:
        """Build the timing dict for the just-finished rip and log it.

        Returns None when no start was stamped (e.g. a finish with no matching
        request, as some tests drive). The realtime multiplier (elapsed ÷ disc
        length) is added later, once the log is parsed for the disc duration
        (see the enrichment in ``_on_rip_finished``); cyanrip's own ETA is no
        longer recorded — it was wildly wrong (it logged "822h" on a real disc).
        """
        import time as _time
        from datetime import datetime as _datetime

        from platterpus import rip_report
        from platterpus.rip_timing import format_duration

        if self._rip_started_monotonic is None:
            return None
        elapsed = _time.monotonic() - self._rip_started_monotonic
        finished_at = _datetime.now().astimezone().isoformat(timespec="seconds")
        timing = rip_report.build_timing(
            elapsed,
            started_at=self._rip_started_at,
            finished_at=finished_at,
        )
        log.info("rip elapsed (actual): %s", format_duration(elapsed))
        # Record this rip's epoch window for the debug-log filtering. It's kept
        # in `_rip_windows` (so a LATER album's report excludes these lines) AND
        # remembered as the current window (so THIS report never excludes its
        # own lines — see _write_rip_report). The end is "now"; post-rip steps
        # (CTDB/FLAC verify) that log a little later are this rip's own lines and
        # stay included in this report anyway.
        if self._rip_epoch_start is not None:
            window = (self._rip_epoch_start, _time.time())
            self._rip_windows.append(window)
            self._current_rip_window = window
            self._rip_epoch_start = None
        # The start clock is one-shot per rip — clear it so a stray later finish
        # can't reuse it.
        self._rip_started_monotonic = None
        return timing

    def _enrich_timing_with_disc_duration(self, rip_log: object) -> None:
        """Add ``disc_seconds`` + ``realtime_multiplier`` to the stored timing.

        Called once the log is parsed (the disc's audio length lives in cyanrip's
        ``Total time:`` line → ``rip_log.disc_duration``). Best-effort: a missing
        or unparseable duration just leaves the multiplier off. The report is
        (re)written after this, so the enriched timing lands in the JSON.
        """
        from platterpus import rip_report
        from platterpus.rip_timing import parse_hms_to_seconds

        timing = self._last_rip_timing
        if not isinstance(timing, dict):
            return
        elapsed = timing.get("elapsed_seconds")
        if not isinstance(elapsed, int | float):
            return
        disc_seconds = parse_hms_to_seconds(getattr(rip_log, "disc_duration", ""))
        # Delegate rather than recompute. This used to divide elapsed by the
        # DISC's length regardless of whether the rip finished, so a cancelled
        # 2-of-14 rip reported `realtime_multiplier: 0.21` — the fraction of the
        # disc covered, dressed as a speed, when real throughput was ~0.93x.
        # `build_timing` owns that reasoning (and the fallback to audio actually
        # extracted); a second copy of the arithmetic here is exactly how the
        # two got to disagree in the first place.
        enriched = rip_report.build_timing(
            elapsed,
            disc_seconds=disc_seconds or None,
            started_at=timing.get("started_at") or "",
            finished_at=timing.get("finished_at") or "",
            audio_seconds_ripped=_ripped_audio_seconds(rip_log),
            # A rip is "completed" only when it neither was cancelled NOR
            # failed. Gating on the cancel flag alone left the failure case
            # wide open, and the rig found it immediately: the Roots Music
            # rip died after 2 seconds on a bad argument and archived
            # `realtime_multiplier: 0.0` — 2 s over a 3467 s disc, a rate for
            # a rip that read nothing at all (2026-08-02).
            completed=(
                not getattr(self, "_rip_cancelled", False)
                and str(
                    (getattr(self, "_last_outcome", None) or {}).get("status") or ""
                ).casefold()
                not in {"failed", "cancelled"}
            ),
        )
        timing.update(enriched)

    def _build_rip_debug_log(self) -> dict | None:
        """Capture this session's log for the report, minus other albums' rips.

        Returns a ``{"scope", "truncated", "lines"}`` dict (see
        ``rip_report.build_debug_log``) or None if no buffer is installed. The
        excluded windows are every OTHER rip this session — the current rip's own
        window is kept, so its lines (including the post-rip verify steps that
        land after this is first called) are never filtered out of its own
        report. Recomputed on each write so the CTDB re-write picks up the lines
        logged since the first write.
        """
        from platterpus.log_buffer import get_session_buffer
        from platterpus.rip_report import build_debug_log

        buffer = get_session_buffer()
        if buffer is None:
            return None
        others = [w for w in self._rip_windows if w is not self._current_rip_window]
        return build_debug_log(
            buffer.lines_excluding(others), truncated=buffer.truncated
        )

    def _confirm_offset_from_accuraterip(self, rip_log: object) -> None:
        """Promote the applied read offset to CONFIRMED when a rip matched AR.

        The honest, equal-or-stronger analogue of EAC's Key-Disc offset finder
        (KDD-31): if ≥1 track verified against the AccurateRip global consensus,
        the offset that produced it is empirically correct on *this* drive — a
        stronger confirmation than one key disc, and it re-earns itself on every
        matching rip. We record it as an independent ``ACCURATERIP_CONFIRMED``
        fact; when it agrees with the drive-list value already stored,
        ``reconcile_offset`` promotes the offset to CONFIRMED/HIGH. Only records
        a real match and only when an offset override is actually applied (so the
        recorded value is the one the rip used). Best-effort, never raises — a
        provenance touch-up must never break the finish handler.
        """
        try:
            from platterpus.drive_profiles import OffsetSource
            from platterpus.parsers.rip_log import track_accuraterip_verified

            if not self._config.override_read_offset:
                return  # no explicit offset applied → nothing to attribute
            tracks = getattr(rip_log, "tracks", ()) or ()
            if not any(track_accuraterip_verified(t) for t in tracks):
                return  # nothing matched AccurateRip → no confirmation to record
            drive = self._drive_picker.current_drive()
            if drive is None:
                return
            self._record_drive_fact(
                drive,
                offset_value=self._config.read_offset,
                source=OffsetSource.ACCURATERIP_CONFIRMED,
            )
            self._refresh_drive_profile_display()
        except Exception:  # noqa: BLE001 — provenance is a courtesy, never load-bearing
            log.warning("could not confirm offset from AccurateRip", exc_info=True)

    def _inject_measured_cache_defeat(self, rip_log: RipLog) -> RipLog:
        """Fold a MEASURED cache-defeat verdict into a parsed ``RipLog``.

        cyanrip reports no cache line, so ``ripping_info.defeat_audio_cache`` is
        parsed as None. When the selected drive has a *measured* verdict recorded
        (the cd-paranoia ``-A`` probe, stored per drive — KDD-25/KDD-29), inject it
        so the EAC-compatible log and JSON report carry the real Yes/No, honestly
        sourced from our own measurement. Only fills a *missing* value — a log
        that already carried the fact is left exactly as parsed (never overwrite
        real data). Best-effort and never raises: any failure leaves ``rip_log``
        untouched, so the log still renders "(unknown)" rather than crashing the
        finish handler.
        """
        try:
            from dataclasses import replace

            info = getattr(rip_log, "ripping_info", None)
            if info is None or info.defeat_audio_cache is not None:
                return rip_log  # nothing to fill, or the log already had it
            drive = self._drive_picker.current_drive()
            if drive is None:
                return rip_log
            fingerprint, _serial, _wwn = self._fingerprint_for(drive)
            profile = self._drive_profiles.get(fingerprint)
            if profile is None or profile.cache_defeat is None:
                return rip_log
            return replace(
                rip_log,
                ripping_info=replace(info, defeat_audio_cache=profile.cache_defeat),
            )
        except Exception:  # noqa: BLE001 — enrichment must never break finish
            log.warning("could not inject measured cache-defeat verdict", exc_info=True)
            return rip_log

    def _apply_auto_fix_results(self, rip_log: RipLog) -> RipLog:
        """Make the parsed ``RipLog`` describe the files actually on disk.

        The album's whole-disc ``.log`` records the **first** read pass. When the
        auto-fix afterwards re-rips a track and swaps the improved read into the
        album, that first-pass record is describing bytes that no longer exist —
        so anything rendered from it is about the *discarded* read. Real-hardware
        bug, 2026-07-26 (tracks 3 and 5 of the Police disc): the EAC-compatible
        log and the JSON report both printed the first pass's CRC beside the
        shipped file's name. cyanrip's own log carries a written addendum saying
        the shipped CRC supersedes it; our own renderings had no such mechanism.

        Two distinct facts therefore get folded in, both measured:

        1. **The shipped read itself.** For every track the auto-fix swapped in we
           kept the *re-rip's* parsed record, and its measured fields — CRC,
           AccurateRip results, read counts, status — replace the first pass's.
           Identity fields (track number, filename) stay as the album knows them:
           the re-rip ran in a throwaway directory, and it is the same track.
        2. **Whether the re-reads agreed.** ``-Z N`` convergence is the same
           two-reads-agree proof EAC prints as a Test/Copy pair (KDD-30), and the
           first-pass log cannot know it:

           * converged **and** swapped in → ``True`` (the shipped file *is* the
             corroborated read);
           * re-read but never converged → ``False`` (measured non-reproducibility
             — the log must not let it pass as clean, since cyanrip's health line
             stays "No errors occurred" for it);
           * converged but **not** swapped in → left unknown. The shipped bytes
             are still the first pass, so neither claim is earned — under-claim in
             both directions rather than guess.

        Best-effort — never raises, because an enrichment must not abort the
        post-rip chain.
        """
        try:
            from dataclasses import replace

            # `_last_retried_tracks` is the worker's own record of what it
            # re-ripped (mirrored into the report as read_speed.retried_tracks).
            verdicts: dict[int, bool] = {}
            for entry in getattr(self, "_last_retried_tracks", []) or []:
                number = entry.get("track")
                if not isinstance(number, int):
                    continue
                if entry.get("converged"):
                    # Only a re-read that actually replaced the album's file
                    # proves anything about the file that's there now.
                    if entry.get("replaced"):
                        verdicts[number] = True
                else:
                    verdicts[number] = False
            # The worker keeps these parser-agnostically (its own log handling is
            # typed `object`), but both parsers produce TrackResult and the merge
            # only ever reads TrackResult fields — so narrow here, where the values
            # are used, rather than weakening the merge rule's signature to `object`.
            shipped: dict[int, TrackResult] = (
                getattr(self, "_last_swapped_tracks", {}) or {}
            )
            if not verdicts and not shipped:
                return rip_log
            tracks = tuple(
                _merge_shipped_track(track, shipped.get(track.number), verdicts)
                for track in rip_log.tracks
            )
            return replace(rip_log, tracks=tracks)
        except Exception:  # noqa: BLE001 — enrichment must never break finish
            log.warning("could not apply auto-fix results", exc_info=True)
            return rip_log

    def _write_eac_log(self, rip_log: RipLog, log_file: Path) -> None:
        """Write an EAC-layout companion log beside ``log_file`` (best-effort).

        Gated by ``write_eac_log_after_rip`` (off by default). The rendering is
        the honest, clearly-attributed EAC-*layout* text (never a signed/forged
        EAC log — KDD-11/13); it goes next to cyanrip's own ``.log`` as
        ``<name> (EAC-compatible).log`` so the two are never confused. A small
        text write — safe on the GUI thread, same as the JSON report beside it —
        and never raises (a companion log is a courtesy, never load-bearing).
        """
        if not self._config.write_eac_log_after_rip:
            return
        try:
            from platterpus import __version__, build_info
            from platterpus.eac_log_export import render_eac_style_log

            # Software provenance for the archival text artifact, all from
            # already-resolved state (never a fresh probe — that would enter the
            # container and freeze the GUI): our own version+build, and the FLAC
            # encoder versions from the launch-time dependency report. ffmpeg is
            # named only when a derived (non-FLAC) format was produced.
            dep_report = getattr(self, "_last_dependency_report", None)
            wanted = ["flac", "metaflac"]
            if getattr(self._config, "output_format", "flac") != "flac":
                wanted.append("ffmpeg")
            # Tell the renderer the rip's OUTCOME and the disc's true track total,
            # so an interrupted rip can't produce a checksum-attested log that
            # reads as a clean, complete one (real-hardware finding, 2026-07-26: a
            # force-stopped 14-track rip rendered as 13 tidy "Copy OK" blocks).
            # Both come from state we already recorded — `_last_outcome.status`
            # (the same value the JSON report carries) and the scanned TOC's track
            # count — so nothing here is invented.
            # `_last_outcome` is the DICT that `rip_report.build_outcome()`
            # returns — a dict does not expose its keys as attributes, so the
            # `getattr(outcome, "status", "")` this used to do always yielded the
            # default and the INCOMPLETE RIP banner could never render on a real
            # rip (audit finding, 2026-07-28 — the feature shipped broken in
            # v0.5.11). Subscript it, and guard the type so a future shape change
            # degrades to "no banner" instead of raising in the finish path.
            outcome = getattr(self, "_last_outcome", None)
            outcome_status = (
                str(outcome.get("status") or "") if isinstance(outcome, dict) else ""
            )
            text = render_eac_style_log(
                rip_log,
                platterpus_version=__version__,
                build_fingerprint=build_info.build_fingerprint(),
                encoder_versions=build_info.encoder_versions(dep_report, wanted),
                outcome_status=outcome_status,
                disc_track_total=getattr(self, "_current_num_tracks", 0) or None,
                # An interrupted securing pass reached the JSON report and not
                # the durable log, so the archival artifact was the more
                # reassuring of the two (audit finding, 2026-07-28).
                secure_rerip=getattr(self, "_last_secure_rerip", None),
            )
            target = log_file.with_name(f"{log_file.stem} (EAC-compatible).log")
            target.write_text(text, encoding="utf-8")
            log.info("wrote EAC-layout companion log: %s", target)
            # The JSON report embeds this file's text (v12 `artifacts`), and it
            # is written AFTER the report's first write — so without this the
            # one file the user uploads would carry `eac_log.exists: false` for
            # a log sitting right beside it. Re-arm the debounced write; it
            # coalesces with the async verifies' re-writes, so this costs
            # nothing when they are also pending.
            self._schedule_rip_report_write()
        except Exception:  # noqa: BLE001 — a companion log must never crash finish
            log.warning("could not write EAC-layout log", exc_info=True)

    def _write_rip_report(self, rip_log: object, log_file: Path) -> None:
        """Write the JSON rip report beside ``log_file`` (best-effort).

        Pulls every accumulated post-rip result from ``self`` (CTDB, FLAC-verify,
        transcode, checksums) so the file always reflects whatever has finished
        so far. The first write (from ``_on_rip_finished``) calls this directly
        so the report exists the instant the rip ends; the later async verifies
        route through ``_schedule_rip_report_write`` so their re-writes coalesce
        onto the debounce timer instead of serializing the whole JSON per check.
        Since every write passes *all* results, a coalesced write is never lossy
        — the final file holds everything regardless of completion order. A small
        JSON write — safe on the GUI thread (computing the checksums, which is
        NOT, happens off-thread and is passed in via ``self._last_checksums``).
        Never raises (write_report swallows OSError).

        The report is the SINGLE self-contained per-album debug artifact (the
        maintainer's call, 2026-07-01): it EMBEDS this rip's session log under
        ``debug.lines`` (scoped to this album, other rips filtered out), so there
        is no separate ``.platterpus.log`` sidecar. Humans read cyanrip's own
        ``.log``/``.cue``; the global ``~/.local/share/platterpus/log.txt`` stays
        the cross-session catch-all for program-level failures.
        """
        from datetime import datetime

        from platterpus import (
            build_info,
            read_speed_ladder,
            report_artifacts,
            rip_report,
        )

        # environment: the live Python/OS/PySide6/channel probe, plus the
        # per-dependency versions + locations from the LAUNCH-TIME dependency
        # check (never a fresh probe here — that enters the container and would
        # freeze the GUI). None dependencies until the launch check has landed.
        environment = build_info.environment_report()
        dep_report = getattr(self, "_last_dependency_report", None)
        environment["dependencies"] = (
            build_info.dependency_summary(dep_report)
            if dep_report is not None
            else None
        )

        rip_report.write_report(
            rip_log,
            log_file,
            ctdb_result=getattr(self, "_last_ctdb_result", None),
            flac_verify_result=getattr(self, "_last_flac_verify_result", None),
            transcode_result=getattr(self, "_last_transcode_result", None),
            derived_verify_result=getattr(self, "_last_derived_verify_result", None),
            recompress_result=getattr(self, "_last_recompress_result", None),
            cover_art_result=getattr(self, "_last_cover_art_result", None),
            # The post-rip tagging outcome. Recorded as an `issues` entry rather
            # than a block of its own — see rip_report._tagging.
            tagging_result=getattr(self, "_last_tagging_result", None),
            read_speed=read_speed_ladder.attempts_to_report(
                getattr(self, "_last_speed_attempts", []) or [],
                getattr(self, "_last_unstable_tracks", []) or [],
                getattr(self, "_last_retried_tracks", []) or [],
            ),
            secure_rerip=getattr(self, "_last_secure_rerip", None),
            eta_trace=getattr(self, "_last_eta_trace", None) or None,
            checksums=getattr(self, "_last_checksums", None),
            generated_at=datetime.now().astimezone().isoformat(timespec="seconds"),
            timing=self._last_rip_timing,
            debug_log=self._build_rip_debug_log(),
            # The verbatim text of the three files written beside this report
            # (v12). Derived from `log_file`, so a library move — which re-calls
            # this with the new path — re-reads them from their new home rather
            # than embedding a stale copy. Reading three small text files is
            # microseconds; this is already off the rip's critical path (the
            # write is debounced), so it does not warrant a worker thread.
            artifacts=report_artifacts.build_artifacts(
                rip_log=log_file,
                eac_log=log_file.with_name(f"{log_file.stem} (EAC-compatible).log"),
                cue=log_file.with_suffix(".cue"),
                # The ripper's own stdout, which survives a kill when its
                # block-buffered logfile does not — the capture that would have
                # shown the track a truncated log lost. There is no file to read
                # it from; it lives in memory.
                #
                # THE SNAPSHOT, UNCONDITIONALLY. This read the live worker, guarded
                # by `if self._rip_worker is not None else ""` — a conditional whose
                # only effect was to send an EMPTY string on every write after the
                # first, because `_on_rip_finished`'s `finally` clears the worker and
                # every post-rip step (FLAC verify, transcode, CTDB, the self-check)
                # triggers a debounced re-write. The guard was not wrong about the
                # lifetime; it drew the wrong conclusion from it — the answer to "the
                # worker is gone" is to have kept the value, not to emit nothing.
                #
                # Found by reading a real rig artifact (2026-08-04): a clean 14/14
                # rip whose `ripper_stdout` block was `{"path": null, "exists":
                # false}` with a `source` string still promising "complete even when
                # the ripper was killed". Accurate about the mechanism, false about
                # the file — and this is the one artifact the cyanrip project cannot
                # produce for itself, which round 7 lap 10 tells them we capture.
                ripper_stdout=getattr(self, "_last_ripper_stdout", ""),
            ),
            # The one verdict in the report that is not ours (round 7 lap 10, J3).
            ripper_log_verification=getattr(
                self, "_last_ripper_log_verification", None
            ),
            # v7 process/settings/provenance blocks. `outcome`/`disc` are
            # snapshotted at finish (worker/params are cleared before the debounced
            # re-writes); `settings`/`gates` come from the persistent config +
            # backend, so they're rebuilt here each write (pure + cheap).
            outcome=getattr(self, "_last_outcome", None),
            # The disc's own track count, so the JSON's verdict and the window's
            # agree about the denominator on a rip that stopped early.
            #
            # The snapshot is only taken at finish, so it is None for every
            # re-write DURING a rip — and with no denominator the verdict said
            # "✓ Bit-perfect: all 2 tracks verified" over a 2-of-14 rip that was
            # still running (found on the rig, 2026-08-01). The EAC-layout log
            # beside it used the live count and said "2 of 14", so our two
            # archival artifacts disagreed. Falling back to the same computation
            # the finish path uses keeps them in step, and folds in the Rip?
            # selection so a *deliberate* subset is not reported as 12 missing
            # tracks — the false alarm the finish-time fix already had to solve.
            disc_track_total=getattr(self, "_last_expected_track_total", None)
            or expected_track_total(
                getattr(self, "_current_num_tracks", 0) or None,
                getattr(self._active_rip_params, "only_tracks", ())
                if getattr(self, "_active_rip_params", None) is not None
                else (),
            ),
            settings=rip_report.build_settings(
                self._config,
                read_offset_effective=getattr(
                    self, "_last_read_offset_effective", None
                ),
            ),
            disc=getattr(self, "_last_disc", None),
            environment=environment,
            gates=rip_report.build_gates(
                ctdb_enabled=self._config.ctdb_verify_after_rip,
                flac_verify_enabled=self._config.verify_flac_after_rip,
                backend_self_verifies=self._backend.self_verifies_encode(),
                recompress_enabled=self._config.recompress_flac_after_rip,
                backend_maxes_compression=(
                    self._backend.produces_max_compression_flac()
                ),
                transcode_requested=self._config.output_format in TRANSCODE_FORMATS,
            ),
        )

    def _write_minimal_failure_report(self, params: RipParameters | None) -> None:
        """Write a report for a rip that produced NO log at all.

        A hard failure before any output (the backend never started, or the
        stream died before a file was written) used to write nothing — so the
        most-broken rips were the *least* diagnosable. This drops a
        ``platterpus-rip-failure.platterpus.json`` beside the intended output dir.

        **It carries the ripper's captured stdout and the session DEBUG log**, and
        that is the whole point rather than a nicety. It did not, and the
        consequence was the exact inversion this function exists to fix:

        * the worker's ``captured_stdout`` — built with a head, a counted elision
          and a tail *specifically to survive a kill* — was **discarded**;
        * the always-DEBUG session buffer was **not embedded**, because
          ``debug_log=`` was omitted;
        * and ``log.txt`` is **INFO by default** while every ripper line is written
          with ``log.debug("cyanrip │ …")``, so it was not on disk either.

        So on a hard failure with default settings the ripper's entire output
        existed in memory, in a variable the code already knew how to serialise,
        and reached neither the screen, nor the log file, nor the one artifact
        written. Only the one-line ``failure_hint`` survived. The full-report path
        passed both of these all along; only this path — the one for the rips that
        need them most — did not.

        Best-effort and never raises (a failing rip must not be made worse by a
        report write). Each embed is guarded separately, so one that cannot be
        produced cannot cost us the other, or the report.
        """
        if params is None:
            return
        from datetime import datetime

        from platterpus import rip_report
        from platterpus.parsers.rip_log import RipLog

        try:
            out_dir = Path(params.output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            # write_report derives the JSON path from a .log path but never reads
            # it, so a synthetic name is fine — no real log exists for this rip.
            synthetic_log = out_dir / "platterpus-rip-failure.log"
            written = rip_report.write_report(
                RipLog(),
                synthetic_log,
                outcome=getattr(self, "_last_outcome", None),
                settings=rip_report.build_settings(
                    self._config,
                    read_offset_effective=getattr(
                        self, "_last_read_offset_effective", None
                    ),
                ),
                disc=getattr(self, "_last_disc", None),
                # The two embeds. Guarded individually, below.
                artifacts=self._failure_artifacts(),
                debug_log=self._build_rip_debug_log(),
                generated_at=datetime.now().astimezone().isoformat(timespec="seconds"),
            )
            if written is not None:
                # WARNING, not INFO. `log.txt` is INFO-only by default so this did
                # reach it — but a failure report existing at all is a
                # failure-path fact, and it belongs at the level a reader scanning
                # for problems will see. The path is named because a user asked to
                # "send the report" has to be able to find it.
                log.warning("wrote a rip-failure report to %s", written)
                self._rip_progress.append_log_line(
                    f"A failure report was written to {written} — it embeds the "
                    f"ripper's captured output and this session's debug log."
                )
        except Exception:  # noqa: BLE001 — a failure report must never crash close
            log.exception("could not write the minimal failure report")

    def _failure_artifacts(self) -> ArtifactsBlock | None:
        """The ``artifacts`` block for a no-log failure: the ripper's own output.

        Separate and individually guarded so a stdout capture that cannot be built
        cannot cost us the report it was meant to explain. Returns ``None`` when
        there is genuinely nothing captured — which is itself distinguishable in
        the JSON from "we had it and dropped it".
        """
        try:
            from platterpus import report_artifacts

            # Snapshot first, live worker second. A hard failure can land BEFORE
            # `_finish_rip` takes the snapshot, so the worker is the primary source
            # here — but a *re-write* after teardown has no worker, so the snapshot
            # has to be consulted too. Neither alone covers both cases.
            captured = getattr(self, "_last_ripper_stdout", "") or getattr(
                self._rip_worker, "captured_stdout", ""
            )
            if not captured:
                return None
            # No rip_log/eac_log/cue: by definition this path ran because none were
            # written. `build_artifacts` records each absent one explicitly, so the
            # reader is told they are missing rather than left to infer it.
            return report_artifacts.build_artifacts(ripper_stdout=captured)
        except Exception:  # noqa: BLE001 — never cost the report
            log.exception("could not build the failure report's artifacts block")
            return None

    def _append_read_speed_summary(self) -> None:
        """Note the read-speed ladder's outcome in the results log, if it acted.

        A silent single-pass rip (the common, clean case) says nothing — no
        clutter. Otherwise it reports what happened: a slow re-read escalation, an
        auto-fixed unstable track (re-ripped alone and now reading consistently —
        a WIN, said plainly), and — loudly — any track still unstable after the
        auto-fix (a real "may not be bit-perfect" caveat). Best-effort.
        """
        from platterpus.read_speed_ladder import attempts_to_report

        summary = attempts_to_report(
            getattr(self, "_last_speed_attempts", []) or [],
            getattr(self, "_last_unstable_tracks", []) or [],
            getattr(self, "_last_retried_tracks", []) or [],
        )
        if not summary:
            return
        unstable = summary.get("unstable_tracks") or []
        escalated = summary.get("escalated")
        fixed = [
            r.get("track")
            for r in (summary.get("retried_tracks") or [])
            if r.get("replaced")
        ]
        if not escalated and not unstable and not fixed:
            return  # clean single-pass rip — no clutter
        if escalated:
            final = summary.get("final_speed_label", "?")
            if summary.get("unresolved"):
                message = (
                    "⚠ Read-speed ladder: the disc still had read errors after "
                    f"slowing to {final} — some tracks may not be bit-perfect "
                    "(see the report)."
                )
                log.warning("%s", message)
                self._rip_progress.set_status(message)
            else:
                message = (
                    "Read-speed ladder: the disc needed a slower re-read (down to "
                    f"{final}); it then read clean."
                )
                log.info("%s", message)
            self._rip_progress.append_log_line(message)
        if fixed:
            # An unstable track was re-ripped ALONE with a harder -Z and now reads
            # consistently — the audio was auto-improved. Say so plainly (a win).
            plural = "s" if len(fixed) > 1 else ""
            listed = ", ".join(str(n) for n in fixed)
            message = (
                f"✓ Auto-fix: track{plural} {listed} read inconsistently, so it was "
                "re-ripped on its own — it now reads consistently and the better "
                "copy was kept."
            )
            log.info("%s", message)
            self._rip_progress.append_log_line(message)
        if unstable:
            # Still couldn't get a consistent read even after re-ripping the track
            # alone — a genuine "may not be bit-perfect" caveat, said loudly.
            plural = "s" if len(unstable) > 1 else ""
            listed = ", ".join(str(n) for n in unstable)
            message = (
                f"⚠ Read stability: track{plural} {listed} still didn't read "
                "identically even after an automatic re-rip — kept the best read, "
                "which may not be bit-perfect. Clean the disc and try again for a "
                "verified copy. See the report."
            )
            log.warning("%s", message)
            self._rip_progress.set_status(message)
            self._rip_progress.append_log_line(message)
            self._rip_progress.downgrade_verdict(
                f"track{plural} {listed} did not read reproducibly"
            )

    def _schedule_rip_report_write(self) -> None:
        """Coalesce a rip-report re-write onto the debounce timer.

        The post-rip async checks (CTDB / FLAC-verify / checksums / transcode)
        each finish independently and each wants the report refreshed with its
        result. Instead of every handler serializing the whole JSON itself (up
        to ~5×/rip), they call this: a single-shot timer (re)armed here writes
        once when the burst settles. Because every write pulls *all* accumulated
        results from ``self`` (see ``_write_rip_report``), a coalesced write is
        never lossy — the file still ends up holding every finished check. A
        no-op until a rip log exists; flushed on window close so nothing pending
        is dropped.
        """
        if self._last_rip_log is None or self._last_rip_log_file is None:
            return
        self._rip_report_timer.start()  # (re)arm; single-shot, so it coalesces

    def _flush_rip_report(self) -> None:
        """Write any pending debounced rip report immediately (timer slot + close).

        Stops the debounce timer and serializes now, so a queued write is never
        left unwritten when the window closes mid-verify. Safe to call when
        nothing is pending (no rip log yet, or the timer already fired)."""
        self._rip_report_timer.stop()
        if self._last_rip_log is not None and self._last_rip_log_file is not None:
            self._write_rip_report(self._last_rip_log, self._last_rip_log_file)

    # --- Per-file SHA256 digests (embedded in the report) -------------------

    def _start_checksums(
        self, rip_dir: Path, wait_for: threading.Thread | None
    ) -> None:
        """Compute a SHA256 for every audio file, on a daemon thread.

        Runs after ``wait_for`` (the post-rip metaflac/transcode thread) so it
        hashes the FINAL files — the tagged/re-compressed FLAC masters *and* any
        derived MP3/WavPack/WAV. Hashing does real disk I/O across a whole album,
        so it must never touch the GUI thread (§3.2); the result is delivered via
        ``checksums_done`` (queued to the GUI thread), which folds it into the
        one debug report. Daemon + guarded emit, like the CTDB/FLAC-verify steps.
        """
        from platterpus import checksums

        def compute() -> object | None:
            if wait_for is not None:
                wait_for.join(timeout=_CHECKSUM_SETTLE_TIMEOUT_S)
                # `join(timeout)` returns whether or not the thread finished. If
                # the post-rip tagging/transcode is STILL running, the FLAC/derived
                # files are mid-rewrite — hashing them now would record a SHA256
                # that doesn't match the final file, i.e. a false "integrity truth".
                # Better to record no checksums than wrong ones: skip this run
                # (returning None → the shared launcher emits nothing; the report
                # simply omits checksums; the fidelity verdict is unaffected).
                if wait_for.is_alive():
                    log.warning(
                        "post-rip work did not settle within %.0fs — skipping "
                        "checksums so a mid-rewrite file isn't hashed as final",
                        _CHECKSUM_SETTLE_TIMEOUT_S,
                    )
                    return None
            return checksums.compute_digests(rip_dir)

        log.info("computing SHA256 digests for %s", rip_dir)
        self._launch_post_rip_daemon(
            compute=compute,
            signal=self.checksums_done,
            thread_attr="_checksums_thread",
        )

    def _on_checksums_done(self, digests: object) -> None:
        """Digests computed — record + re-write the report (on the GUI thread)."""
        if not isinstance(digests, dict):
            return
        self._last_checksums = digests
        log.info("SHA256 digests: %d file(s) hashed", len(digests))
        self._schedule_rip_report_write()

    # --- Post-rip FLAC encode-verify (opt-in, default on) -------------------

    def _start_flac_verify(
        self, rip_dir: Path, wait_for: threading.Thread | None
    ) -> None:
        """Verify the just-finished rip's FLACs decode cleanly, on a daemon
        thread (same rationale as CTDB: a per-file decode can outlast any
        ``closeEvent`` wait, and destroying a running ``QThread`` aborts the app
        — §3.2). Joins the post-rip metaflac thread first (``wait_for``) so it
        never tests a file mid-rewrite. Result reported via ``flac_verify_done``
        (queued to the GUI thread). Threading/generation guard: see
        :meth:`_launch_post_rip_daemon`."""
        log.info("starting FLAC verify for %s", rip_dir)
        self._rip_progress.append_log_line("Verifying FLAC integrity…")
        self._launch_post_rip_daemon(
            compute=lambda: verify_flac_dir(rip_dir, wait_for=wait_for),
            signal=self.flac_verify_done,
            thread_attr="_flac_verify_thread",
        )

    def _on_flac_verified(self, result: object) -> None:
        """FLAC verify finished — record the outcome (runs on the GUI thread).

        Loud on failure (a corrupt archival file is a real problem): the message
        also replaces the status line. A clean pass or a "couldn't run" skip is
        noted only in the log view.
        """
        if not isinstance(result, FlacVerifyResult):
            return
        # Record + schedule a re-write so the FLAC-integrity outcome lands in the
        # one debug file alongside the other checks (debounced/coalesced).
        self._last_flac_verify_result = result
        self._schedule_rip_report_write()
        if result.error:
            message = f"FLAC verify: skipped — {result.error}"
        elif result.failures:
            # NAME WHAT `flac` SAID, not only which files. "FAILED for 3 file(s):
            # a, b, c" was accurate and useless — a reader could not tell an
            # unreadable file from a corrupt one from a tool that timed out. The
            # reason now travels on the result (see `adapters.tool_run`), so quote
            # it; fall back to bare names if an older result carries no details.
            detail = "; ".join(result.reasons()) or ", ".join(
                p.name for p in result.failures
            )
            message = (
                f"⚠ FLAC verify FAILED for {len(result.failures)} file(s): {detail}"
            )
        else:
            message = f"FLAC verify: all {result.checked} file(s) decode cleanly."
        if result.failures:
            log.warning("%s", message)
            self._rip_progress.set_status(message)
            # The verdict banner was set from the AccurateRip parse minutes ago
            # and knows nothing about this. A green "Bit-perfect" headline over a
            # master that will not decode is the worst thing this screen can say.
            self._rip_progress.downgrade_verdict(
                f"{len(result.failures)} FLAC master(s) failed the decode check"
            )
        else:
            log.info("%s", message)
        self._rip_progress.append_log_line(message)

    # --- Post-rip FLAC re-compress (opt-in, off by default) -----------------

    def _on_flac_recompressed(self, result: object) -> None:
        """FLAC re-compress finished — record the outcome (runs on the GUI
        thread).

        Re-compress is lossless and ``--verify``'d, and any failed file is left
        untouched, so a partial failure is informational rather than alarming: a
        per-file failure is noted in the log (the original FLAC is still a valid
        rip), while a "couldn't run at all" (e.g. ``flac`` missing) is a skip.
        A clean pass just notes how many files shrank.
        """
        if not isinstance(result, RecompressResult):
            return
        # Record + schedule a (debounced) re-write so the re-compress outcome
        # lands in the report's verification block (it mutates the masters, so
        # its result belongs in the one debug file alongside the other checks).
        self._last_recompress_result = result
        self._schedule_rip_report_write()
        if result.error:
            message = f"FLAC re-compress: skipped — {result.error}"
        elif result.failures:
            detail = "; ".join(result.reasons()) or ", ".join(
                p.name for p in result.failures
            )
            message = (
                f"FLAC re-compress: {result.reencoded} file(s) re-compressed; "
                f"{len(result.failures)} left as-is (re-encode failed): {detail}"
            )
        else:
            message = f"FLAC re-compress: {result.reencoded} file(s) re-compressed."
        if result.failures:
            log.warning("%s", message)
        else:
            log.info("%s", message)
        self._rip_progress.append_log_line(message)

    # --- Post-rip transcode (when a non-FLAC output format is selected) -------

    def _on_transcoded(self, result: object) -> None:
        """Transcode finished — record the outcome (runs on the GUI thread).

        The FLAC master is always kept, so a transcode failure never costs the
        user their lossless rip — it's informational, not alarming. A per-file
        failure is noted (the FLAC is still there to retry from); a "couldn't run
        at all" (e.g. ``ffmpeg`` missing) is a skip; a clean pass notes how many
        files were written.
        """
        if not isinstance(result, TranscodeResult):
            return
        # Record + schedule a (debounced) re-write so the transcode outcome is
        # in the report too.
        self._last_transcode_result = result
        self._schedule_rip_report_write()
        if result.error:
            message = f"Transcode: skipped — {result.error} (FLAC master kept)"
        elif result.failures:
            detail = "; ".join(result.reasons()) or ", ".join(
                p.name for p in result.failures
            )
            message = (
                f"Transcode: {result.transcoded} file(s) written; "
                f"{len(result.failures)} failed (FLAC master kept): {detail}"
            )
        else:
            message = f"Transcode: {result.transcoded} file(s) written."
        if result.failures or result.error:
            log.warning("%s", message)
        else:
            log.info("%s", message)
        self._rip_progress.append_log_line(message)

    # --- Post-transcode derived-file verify (MP3/WavPack/WAV) ----------------

    def _start_derived_verify(
        self, rip_dir: Path, fmt: str, wait_for: threading.Thread | None
    ) -> None:
        """Verify the derived ``fmt`` files on a daemon thread (same rationale as
        CTDB/FLAC-verify: a full-album decode can outlast any ``closeEvent`` wait,
        and destroying a running ``QThread`` aborts the app — §3.2). Joins the
        post-rip transcode thread first (``wait_for``) so it never reads a derived
        file mid-write. Result reported via ``derived_verify_done`` (queued to the
        GUI thread). Threading/generation guard: see
        :meth:`_launch_post_rip_daemon`."""
        log.info("starting derived-file verify (%s) for %s", fmt, rip_dir)
        self._rip_progress.append_log_line(f"Verifying derived {fmt.upper()} files…")
        self._launch_post_rip_daemon(
            compute=lambda: verify_derived_dir(rip_dir, fmt, wait_for=wait_for),
            signal=self.derived_verify_done,
            thread_attr="_derived_verify_thread",
        )

    def _on_derived_verified(self, result: object) -> None:
        """Derived-file verify finished — record + surface the outcome.

        Runs on the GUI thread (``derived_verify_done`` is queued there). The
        FLAC master is always the archival copy, so a derived-file problem is
        never catastrophic — but a LOSSLESS mismatch (a WavPack/WAV that isn't
        bit-identical to the master) is a real defect, so it's surfaced loudly;
        a lossy-MP3 pass is stated honestly as "decode-clean", never as
        bit-perfect. A "couldn't run" is a neutral skip.
        """
        if not isinstance(result, DerivedVerifyResult):
            return
        self._last_derived_verify_result = result
        self._schedule_rip_report_write()
        fmt = (result.fmt or "").upper()
        if result.error:
            message = f"{fmt} verify: skipped — {result.error} (FLAC master kept)"
        elif result.mismatches:
            names = ", ".join(p.name for p in result.mismatches)
            message = (
                f"⚠ {fmt} verify FAILED — {len(result.mismatches)} file(s) are NOT "
                f"bit-identical to the FLAC master: {names}"
            )
        elif result.failures:
            names = ", ".join(p.name for p in result.failures)
            message = (
                f"⚠ {fmt} verify: {len(result.failures)} file(s) could not be "
                f"decoded/verified: {names}"
            )
        elif not result.complete:
            message = (
                f"{fmt} verify: only {result.checked}/{result.expected} file(s) "
                "were derived (transcode incomplete; FLAC master kept)"
            )
        elif result.lossless:
            message = (
                f"{fmt} verify: all {result.checked} file(s) are bit-identical to "
                "the FLAC master."
            )
        else:
            message = (
                f"{fmt} verify: all {result.checked} file(s) decode cleanly "
                "(lossy — decodability + completeness, not bit-identity)."
            )
        if result.mismatches or result.failures:
            log.warning("%s", message)
            self._rip_progress.set_status(message)
            # Only a LOSSLESS mismatch contradicts the trust headline; a lossy
            # MP3 that differs from its master is expected by definition.
            if result.mismatches and result.lossless:
                self._rip_progress.downgrade_verdict(
                    f"{len(result.mismatches)} derived {fmt} file(s) are not "
                    "bit-identical to the FLAC master"
                )
        elif not result.complete:
            # An incomplete transcode used to appear ONLY in the scrolling log
            # pane: a user who chose MP3 for their phone and got 9 of 14 found
            # out by scrolling (audit finding, 2026-07-28).
            log.warning("%s", message)
            self._rip_progress.set_status(message)
        else:
            log.info("%s", message)
        self._rip_progress.append_log_line(message)
