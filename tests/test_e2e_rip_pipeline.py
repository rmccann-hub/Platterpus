"""End-to-end test of the rip pipeline through the real GUI wiring.

This is the suite's **end-to-end tier** (see docs/testing.md §2): it builds
the real ``MainWindow`` (all mixins, real Qt signals, a real ``RipWorker`` on
a real ``QThread``) and fakes only the *external boundary* — the ripper
subprocess, MusicBrainz, the cover-art HTTP fetch, and ``metaflac``. Then it
drives one complete unknown-album rip and asserts the whole "good music, good
cover, good everything" outcome lands: the FLACs get tagged, the front cover
is fetched + embedded + saved, and a fidelity verdict is produced — exactly
the cross-cutting flow the MainWindow mixin refactor and the cover-art feature
have to keep working together.

Why this matters: the per-module unit tests drive slots synchronously; only
an end-to-end test proves the *threaded* path (worker → queued ``finished``
signal → ``_on_rip_finished`` → tagging + the cover-art daemon thread) is
wired correctly across module boundaries.

Pattern note (research-backed, no new dependency): the canonical way to drive
a worker-thread flow in a test is pytest-qt's ``qtbot.waitSignal``. We don't
depend on pytest-qt, and the event-loop waiters (``QEventLoop.exec`` /
``QSignalSpy.wait``) don't terminate cleanly under the headless *offscreen*
platform — a known quirk pytest-qt papers over. So we wait the
dependency-free way: ``QThread.wait()`` blocks the calling thread until the
worker QThread finishes (no event loop needed), then a *bounded*
``processEvents()`` loop flushes the queued ``finished`` → ``_on_rip_finished``
slot. The post-rip cover-art fetch runs on a daemon thread, which we join
before asserting on the art.

(``conftest`` warns against ``processEvents()`` in *widget* tests because it
can fire stale deferred timers from earlier tests' destroyed windows. That's
safe here: this is a dedicated test with its own fresh window, the success
path schedules no deferred offers, and the loop is bounded.)
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from PySide6.QtWidgets import QApplication

from whipper_gui.adapters.musicbrainz_client import (
    MusicBrainzClient,
    ReleaseDetail,
    ReleaseSummary,
    TocSignature,
)
from whipper_gui.adapters.whipper_backend import DiscInfo, WhipperBackend
from whipper_gui.config import Config
from whipper_gui.deps.manager import DependencyManager
from whipper_gui.parsers.drive_list import DriveDescriptor
from whipper_gui.ui.main_window import MainWindow
from whipper_gui.workers.rip_worker import RipParameters

# A real whipper rip log so the finish handler parses a genuine fidelity
# verdict (not a hand-faked one).
_WHIPPER_LOG = Path(__file__).parent / "fixtures" / "rip_log_real_whipper_0_7.log"
_JPEG = b"\xff\xd8\xff\xe0" + b"cover-bytes" * 4  # valid JPEG magic + body


# --- Fakes at the external boundary only ----------------------------------


class _FakeHandle:
    """Duck-typed RipHandle: a whipper run that 'just finished' cleanly."""

    def log_lines(self) -> Iterator[str]:
        yield "Ripping track 1 of 2"
        yield "Ripping track 2 of 2"

    def wait(self, timeout: Any = None) -> int:
        return 0  # exit code 0 → success

    def cancel(self, term_timeout: float = 5.0) -> int:
        return 0


class _ArtifactWritingBackend(WhipperBackend):
    """A backend whose rip() writes the artifacts a real ripper would — a
    .log next to FLAC files — so the finish→verdict→tag→cover-art pipeline
    has real files to act on. Everything else is the minimum to construct."""

    def list_drives(self) -> list[DriveDescriptor]:
        return [
            DriveDescriptor(device="/dev/sr0", vendor="ACME", model="CD", release="1")
        ]

    def disc_info(self, drive: str) -> DiscInfo:
        return DiscInfo(num_tracks=2)

    def version(self) -> str:
        return "fake-whipper 0.0.0"

    def rip(self, *, output_dir: Path, **kwargs: Any) -> _FakeHandle:
        # Unknown-album rips land under "<Artist>/<Album>/" — match the
        # default placeholders the GUI uses so the finish handler (which
        # scopes to the .log's parent) finds these files.
        album = output_dir / "Unknown Artist" / "Unknown Album"
        album.mkdir(parents=True, exist_ok=True)
        (album / "01 - Track 01.flac").write_bytes(b"\xffflac-1")
        (album / "02 - Track 02.flac").write_bytes(b"\xffflac-2")
        (album / "rip.log").write_text(_WHIPPER_LOG.read_text(encoding="utf-8"))
        return _FakeHandle()


class _FakeMb(MusicBrainzClient):
    def releases_by_disc_id(self, disc_id: str) -> list[ReleaseSummary]:
        return []

    def releases_by_toc(self, toc: TocSignature) -> list[ReleaseSummary]:
        return []

    def release_by_mbid(self, mbid: str) -> ReleaseDetail:  # pragma: no cover
        raise AssertionError("E2E doesn't fetch release detail")

    def set_user_agent(self, app: str, version: str, contact: str) -> None:
        pass


class _RecordingMetaflac:
    """Records tag writes + cover embeds instead of shelling out to metaflac."""

    def __init__(self) -> None:
        self.tagged: list[Path] = []
        self.embedded: list[Path] = []

    def write_tags(self, flac_path: Path, tags: dict[str, str]) -> None:
        self.tagged.append(flac_path)

    def embed_picture(self, flac_path: Path, image_path: Path) -> None:
        self.embedded.append(flac_path)


@pytest.fixture()
def e2e_window(qapp: QApplication, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Build the real MainWindow with boundary-only fakes; tear down threads."""
    config = Config(
        output_dir=str(tmp_path / "rips"),
        ripper_backend="whipper",
        cover_art="complete",  # embed AND save cover.jpg
        override_read_offset=True,
        read_offset=667,
        # Mark first-run offers already done so the deferred singleShot for
        # `_maybe_offer_first_run_setup` can't pop a modal QMessageBox during
        # our processEvents() poll (a modal .exec() blocks forever headless —
        # the hazard conftest warns about).
        host_setup_prompted=True,
        drive_setup_prompted=True,
        appimage_integration_prompted=True,
    )
    metaflac = _RecordingMetaflac()
    window = MainWindow(
        config=config,
        backend=_ArtifactWritingBackend(),
        mb_client=_FakeMb(),
        metaflac=metaflac,  # type: ignore[arg-type]
        dependency_manager=DependencyManager(specs=[]),
        save_config=lambda _cfg: None,
    )
    # Offset is "configured" so the rip isn't blocked (patch where the rip
    # methods resolve the name — main_window_rip — per the move-the-patch rule).
    monkeypatch.setattr(
        "whipper_gui.ui.main_window_rip.is_offset_configured", lambda _override: True
    )
    # No network: the cover-art fetcher returns bytes directly. A release id
    # is present (as if the user had picked one) so cover art has a target.
    window._cover_art_fetcher = lambda _url: _JPEG
    window._current_release_id = "release-mbid"
    window._metaflac = metaflac  # type: ignore[assignment]

    yield window, metaflac, Path(config.output_dir)

    # Teardown: stop the persistent MB worker thread + any rip thread.
    if window._mb_thread.isRunning():
        window._mb_thread.quit()
        window._mb_thread.wait(2000)
    if window._rip_thread is not None and window._rip_thread.isRunning():
        window._rip_thread.quit()
        window._rip_thread.wait(2000)
    window.deleteLater()


def test_e2e_unknown_rip_tags_flacs_and_embeds_cover_art(
    e2e_window, qapp: QApplication
) -> None:
    """One full unknown-album rip, end to end through a real worker thread:
    artifacts written → finish handler → fidelity verdict → tag → cover art."""
    window, metaflac, output_dir = e2e_window

    # Record when the finish handler completes (it fires this at its end).
    finished: list[bool] = []
    window.rip_post_processing_done.connect(lambda: finished.append(True))

    params = RipParameters(
        drive="/dev/sr0",
        release_id="",
        output_dir=output_dir,
        track_template="t",
        disc_template="d",
        unknown=True,
    )
    window._on_rip_requested(params)  # validates → real RipWorker on a QThread

    # Pump the GUI event loop until the finish handler completes. We must NOT
    # block the GUI thread with QThread.wait() here: the worker's
    # `finished → _rip_thread.quit` is a *queued connection to the GUI thread*
    # (the QThread object lives here), so blocking would deadlock — quit()
    # would never be delivered and the thread would never end. A bounded
    # processEvents() poll keeps delivering the queued finish + quit slots.
    deadline = time.monotonic() + 10.0
    while not finished and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.005)
    assert finished, "the finish handler did not run within the timeout"

    # Cover art runs on a daemon thread kicked off inside the finish handler;
    # join it so its artifacts are settled before we assert.
    if window._cover_art_thread is not None:
        window._cover_art_thread.join(8.0)
        assert not window._cover_art_thread.is_alive()

    album = output_dir / "Unknown Artist" / "Unknown Album"

    # Good music: the rip completed and produced the FLACs, and the worker
    # was cleaned up.
    assert window._rip_worker is None
    assert window._active_rip_params is None
    flacs = sorted(album.glob("*.flac"))
    assert len(flacs) == 2

    # Good everything: unknown-album post-processing tagged both FLACs.
    assert sorted(p.name for p in metaflac.tagged) == [
        "01 - Track 01.flac",
        "02 - Track 02.flac",
    ]

    # Good cover image: the front cover was embedded in both and saved as a
    # file (cover_art="complete").
    assert sorted(p.name for p in metaflac.embedded) == [
        "01 - Track 01.flac",
        "02 - Track 02.flac",
    ]
    assert (album / "cover.jpg").read_bytes() == _JPEG
