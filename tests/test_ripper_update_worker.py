"""The ripper update check off the GUI thread, and the window methods around it.

`test_ripper_manifest.py` covers the parsing and the decision. This covers the
parts that touch Qt: the worker, its cancel, and the four window methods that
read the setting, read the installed build, and render the verdict.

Those were the untested half, and the worker in particular is where "cancel is a
real interrupt" has to hold — a flag the blocked read never checks is a false
promise (`CLAUDE.md` rule 9), and the no-cancel ratchet in
`tests/test_qthread_ownership.py` only shrinks.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from platterpus.deps.ripper_manifest import CancellableFetcher
from platterpus.deps.ripper_offer import (
    OFFER_AVAILABLE,
    OFFER_NOT_DETERMINED,
    OFFER_UP_TO_DATE,
)

pytest.importorskip("PySide6.QtWidgets")

MANIFEST: dict[str, Any] = {
    "schema": 1,
    "project": "cyanrip-fork",
    "default_channel": "stable",
    "channels": {
        "stable": {
            "version": "0.9.4-rc1+platterpus.5",
            "commit": "ddf7ac3",
            "release_seq": 11,
            "handshake_round": 7,
            "round_closed": True,
            "install": "https://github.com/rmccann-hub/cyanrip/archive/ddf7ac3.tar.gz",
        }
    },
}


def _serve(
    monkeypatch, body: str | None = None, error: Exception | None = None
) -> None:
    """Make the REAL fetcher return `body` (or raise `error`).

    Patched at `urlopen` rather than at `_default_fetch`, because the worker does
    not use `_default_fetch`: it passes its own `CancellableFetcher.fetch` so the
    read stays interruptible. Patching the convenience function would have left
    the worker talking to the real network — a test that appears to control its
    input and does not.
    """
    import platterpus.deps.ripper_manifest as rm

    class _Response:
        def read(self, _size: int) -> bytes:
            if error is not None:
                raise error
            return (body or "").encode()

        def close(self) -> None:
            pass

    def _open(*_a: object, **_k: object) -> _Response:
        if error is not None:
            raise error
        return _Response()

    monkeypatch.setattr(rm.urllib.request, "urlopen", _open)


# --- The worker --------------------------------------------------------------


def test_the_worker_emits_an_offer_never_none(qapp, process_until, monkeypatch) -> None:
    """ "Couldn't determine" is a verdict this subsystem carries explicitly.

    Emitting `None` for it would push the distinction onto every caller, and the
    caller that forgets is the one that renders "unknown" as reassurance.
    """
    from platterpus.workers.ripper_update_worker import RipperUpdateWorker

    _serve(monkeypatch, json.dumps(MANIFEST))

    seen: list[object] = []
    worker = RipperUpdateWorker(channel="stable", installed_commit="ddf7ac3")
    worker.finished.connect(seen.append)
    worker.run()

    assert len(seen) == 1
    assert seen[0] is not None
    assert getattr(seen[0], "verdict", "") == OFFER_UP_TO_DATE


def test_the_worker_reports_not_determined_when_the_fetch_fails(qapp, monkeypatch):
    from platterpus.workers.ripper_update_worker import RipperUpdateWorker

    _serve(monkeypatch, error=OSError("network unreachable"))

    seen: list[object] = []
    worker = RipperUpdateWorker()
    worker.finished.connect(seen.append)
    worker.run()

    assert len(seen) == 1
    assert getattr(seen[0], "verdict", "") == OFFER_NOT_DETERMINED


def test_the_worker_still_finishes_when_evaluation_itself_explodes(qapp, monkeypatch):
    """A worker must ALWAYS finish. A thread that never emits is a thread that
    never gets joined, and `stop_thread` then waits out the shutdown budget."""
    import platterpus.deps.ripper_offer as offer_mod
    from platterpus.workers import ripper_update_worker as mod

    def boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("evaluation exploded")

    # The handler re-imports evaluate_offer inside run(), so patch the module.
    monkeypatch.setattr(offer_mod, "evaluate_offer", boom)

    seen: list[object] = []
    worker = mod.RipperUpdateWorker()
    worker.finished.connect(seen.append)
    # The except branch calls evaluate_offer again to build the "not determined"
    # answer; if that also raises, run() must still not propagate.
    try:
        worker.run()
    except RuntimeError:
        pytest.fail("run() propagated an exception — a worker must always finish")
    assert len(seen) <= 1, "at most one finished emission"


def test_the_worker_offers_the_newer_build_with_its_consequence(qapp, monkeypatch):
    from platterpus.workers.ripper_update_worker import RipperUpdateWorker

    ahead = json.loads(json.dumps(MANIFEST))
    ahead["channels"]["stable"].update(
        {"release_seq": 20, "commit": "beefcaf", "handshake_round": 9}
    )
    _serve(monkeypatch, json.dumps(ahead))

    seen: list[Any] = []
    worker = RipperUpdateWorker(channel="stable", installed_commit="ddf7ac3")
    worker.finished.connect(seen.append)
    worker.run()

    assert seen[0].verdict == OFFER_AVAILABLE
    assert seen[0].would_be_unapproved is True
    assert "unapproved" in seen[0].detail


def test_the_worker_cancel_is_wired_to_the_fetcher(qapp) -> None:
    """`cancel()` must reach the thing that can actually break a blocked read.

    Structural, deliberately: the runtime behaviour (a closed socket makes the
    read raise) needs a real network to demonstrate, but *that the worker's cancel
    reaches the fetcher at all* is what makes it more than a flag — and it is what
    would silently regress if someone replaced the fetcher with a plain function.
    """
    from platterpus.workers.ripper_update_worker import RipperUpdateWorker

    worker = RipperUpdateWorker()
    assert isinstance(worker._fetcher, CancellableFetcher)
    worker.cancel()
    assert worker._fetcher._cancelled is True
    # Idempotent, because teardown can call it twice.
    worker.cancel()


def test_a_cancelled_worker_refuses_to_fetch(qapp, monkeypatch) -> None:
    """The cancel must take effect even if it lands before run() starts.

    The gap between constructing a worker and its thread actually running is real;
    a cancel landing there must not be ignored, or the window tears down while a
    network read it already abandoned is still starting.
    """
    from platterpus.workers.ripper_update_worker import RipperUpdateWorker

    worker = RipperUpdateWorker()
    worker.cancel()

    seen: list[Any] = []
    worker.finished.connect(seen.append)
    worker.run()
    assert seen[0].verdict == OFFER_NOT_DETERMINED


# --- The fetcher's own bounds ------------------------------------------------


def test_the_fetcher_refuses_an_over_cap_body(monkeypatch) -> None:
    """An unbounded read has no upside; the cap is the half that matters."""
    import platterpus.deps.ripper_manifest as rm

    class _Response:
        def read(self, size: int) -> bytes:
            return b"x" * size  # always one byte past the cap

        def close(self) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_exc: object) -> None:
            pass

    monkeypatch.setattr(rm.urllib.request, "urlopen", lambda *_a, **_k: _Response())
    with pytest.raises(ValueError, match="exceeded"):
        CancellableFetcher().fetch("https://example.invalid/m.json")


def test_the_fetcher_returns_the_body_it_read(monkeypatch) -> None:
    """Non-triviality floor: the refusal tests above must be refusing something
    that otherwise works."""
    import platterpus.deps.ripper_manifest as rm

    payload = json.dumps(MANIFEST).encode()

    class _Response:
        def read(self, _size: int) -> bytes:
            return payload

        def close(self) -> None:
            pass

    monkeypatch.setattr(rm.urllib.request, "urlopen", lambda *_a, **_k: _Response())
    assert CancellableFetcher().fetch("https://example.invalid/m.json") == (
        payload.decode()
    )


def test_a_cancel_during_the_read_discards_the_result(monkeypatch) -> None:
    """A body that arrived after the user closed the window is not an answer."""
    import platterpus.deps.ripper_manifest as rm

    fetcher = CancellableFetcher()

    class _Response:
        def read(self, _size: int) -> bytes:
            fetcher.cancel()  # the GUI thread closes us mid-read
            return b"{}"

        def close(self) -> None:
            pass

    monkeypatch.setattr(rm.urllib.request, "urlopen", lambda *_a, **_k: _Response())
    with pytest.raises(ValueError, match="cancelled"):
        fetcher.fetch("https://example.invalid/m.json")


# --- The window methods ------------------------------------------------------


def _stub_window(config: object, banner: str = "") -> Any:
    """Just enough window for the mixin methods, which take only `self`.

    A real `QWidget`, not a bare object: `_on_ripper_update_result` builds a
    `QMessageBox(self)`, and Qt refuses a non-widget parent. A plain stub passed
    that check only because the first version of these tests never reached the
    dialog — the stub was quietly narrower than the thing it stood in for.
    """
    from PySide6.QtWidgets import QWidget

    win = QWidget()
    win._config = config
    win._observed_ripper_banner = banner
    win._ripper_update_worker = None
    win._ripper_update_thread = None
    return win


def test_the_channel_is_read_live_and_falls_back_to_stable(qapp) -> None:
    """A value the validator would reject must not widen what a user is offered."""
    import dataclasses

    from platterpus.config import Config
    from platterpus.ui.main_window_update import UpdateMixin

    good = _stub_window(dataclasses.replace(Config(), ripper_channel="beta"))
    assert UpdateMixin._ripper_channel(good) == "beta"

    bad = _stub_window(dataclasses.replace(Config(), ripper_channel="nightly"))
    assert UpdateMixin._ripper_channel(bad) == "stable"

    missing = _stub_window(object())
    assert UpdateMixin._ripper_channel(missing) == "stable"


@pytest.mark.parametrize(
    ("banner", "expected"),
    [
        ("cyanrip 0.9.4-rc1+platterpus.5 (platterpus-fork-gddf7ac3)", "ddf7ac3"),
        ("cyanrip 0.9.4 (platterpus-fork-gddf7ac3-dirty)", "ddf7ac3-dirty"),
        ("cyanrip 0.9.3", None),  # no parenthetical at all
        ("cyanrip 0.9.3 (some-other-tag)", None),  # not a fork tag
        ("cyanrip 0.9.3 (platterpus-fork-g)", None),  # tag present, sha empty
        ("", None),
    ],
)
def test_the_installed_commit_is_read_off_the_banner(banner, expected) -> None:
    """Best-effort and never raising: every failure mode is already "not determined".

    **Repointed 2026-08-17, and the move is the fix.** This used to call
    ``UpdateMixin._installed_ripper_commit(window)``, whose only input was a cached
    ``window._observed_ripper_banner`` — an attribute assigned **nowhere in src/**,
    and assigned *here*, by ``_stub_window``. That is precisely what made the dead
    code look wired: the test supplied the producer the product lacked, so the
    parsing was exercised while the path that fed it in production returned ``None``
    on every call. The window then reported the build-time constant ``FORK_PIN`` as
    "what you have", forever, including right after a successful install.

    The parsing now lives in :func:`platterpus.ripper_identity.fork_commit_from_banner`
    and the worker probes the binary for the banner itself, so there is no cache to
    populate and nothing for a stub to stand in for. The cases below are unchanged —
    they were always the right cases, asked of the wrong object.
    """
    from platterpus.ripper_identity import fork_commit_from_banner

    assert fork_commit_from_banner(banner) == expected


def test_the_verdict_dialog_renders_plain_text_never_html(qapp, monkeypatch) -> None:
    """**The inbound-seam rule, at the widget that shows dependency output.**

    Qt's default `AutoText` auto-detects HTML. This paragraph carries a version
    string and a commit read out of a *network document*, and album titles reaching
    other panes come from MusicBrainz — so a value containing `<` would be swallowed
    as an unknown tag and the user would never learn text went missing. Asserted on
    the constructed box rather than trusted to review.
    """
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QMessageBox

    from platterpus.deps.ripper_offer import RipperOffer
    from platterpus.ui.main_window_update import UpdateMixin

    built: list[QMessageBox] = []
    real_exec = QMessageBox.exec

    def _capture(self: QMessageBox) -> int:
        built.append(self)
        return 0

    monkeypatch.setattr(QMessageBox, "exec", _capture)
    try:
        window = _stub_window(object())
        offer = RipperOffer(
            verdict=OFFER_AVAILABLE,
            channel="stable",
            release=None,
            detail="a <newer> build exists",
        )
        UpdateMixin._on_ripper_update_result(window, offer)
    finally:
        monkeypatch.setattr(QMessageBox, "exec", real_exec)

    assert len(built) == 1, "the verdict must be shown, not swallowed"
    box = built[0]
    assert box.textFormat() == Qt.TextFormat.PlainText, (
        "dependency output must render as PlainText; AutoText would interpret "
        "'<newer>' as markup and silently drop it"
    )
    assert "<newer>" in box.text(), "the literal text must survive to the widget"
    # And the in-flight slots are cleared, so a second check is possible.
    assert window._ripper_update_worker is None
    assert window._ripper_update_thread is None


def test_a_verdict_with_no_detail_still_says_something(qapp, monkeypatch) -> None:
    """A dialog with an empty body is the 'accurate and useless' failure."""
    from PySide6.QtWidgets import QMessageBox

    from platterpus.ui.main_window_update import UpdateMixin

    # Capture the TEXT at exec time, not the widget. The box is parented to the
    # window, so holding the widget past the test means reading a C++ object Qt
    # has already deleted — `libshiboken: Internal C++ object already deleted`.
    shown: list[str] = []
    monkeypatch.setattr(
        QMessageBox, "exec", lambda self: shown.append(self.text()) or 0
    )

    window = _stub_window(object())
    UpdateMixin._on_ripper_update_result(window, object())
    assert shown and shown[0].strip(), "an empty verdict dialog tells nobody anything"


def test_a_second_check_is_refused_while_one_is_in_flight(qapp) -> None:
    """One at a time, so a slow check cannot spawn a thread per click."""
    from platterpus.ui.main_window_update import UpdateMixin

    window = _stub_window(object())
    window._ripper_update_thread = object()  # pretend one is running
    UpdateMixin._on_check_ripper_updates(window)
    # No worker was constructed, so nothing to join — the guard returned early.
    assert window._ripper_update_worker is None
