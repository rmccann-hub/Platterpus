"""Tests for whipper_gui.composition — the shared adapter composition root.

These pin the seam that app.py and preflight.default_context() now both go
through, so the backend selection + MB-client construction can't drift between
the GUI and the --doctor path. Construction does no I/O, so this runs offline.
"""

from __future__ import annotations

from whipper_gui import composition
from whipper_gui.config import Config


def test_build_backend_defaults_to_whipper() -> None:
    backend, name = composition.build_backend(Config())
    assert name == "whipper"
    assert backend.__class__.__name__ == "WhipperHostExportedImpl"


def test_build_backend_selects_cyanrip() -> None:
    backend, name = composition.build_backend(Config(ripper_backend="cyanrip"))
    assert name == "cyanrip"
    assert backend.__class__.__name__ == "CyanripImpl"


def test_build_backend_passes_working_dir(tmp_path) -> None:
    # working_dir is plumbed through to the backend (None when unset).
    backend, _ = composition.build_backend(Config(working_dir=str(tmp_path)))
    assert backend._working_dir == tmp_path
    backend_none, _ = composition.build_backend(Config(working_dir=""))
    assert backend_none._working_dir is None


def test_build_musicbrainz_client_is_the_v1_impl() -> None:
    client = composition.build_musicbrainz_client()
    assert client.__class__.__name__ == "MusicBrainzNgsImpl"


def test_contact_url_is_a_reachable_project_url() -> None:
    # MusicBrainz policy wants a reachable contact in the user-agent.
    assert composition.CONTACT_URL.startswith("https://")
