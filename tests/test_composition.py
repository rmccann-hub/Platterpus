"""Tests for platterpus.composition — the shared adapter composition root.

These pin the seam that app.py and preflight.default_context() now both go
through, so the backend selection + MB-client construction can't drift between
the GUI and the --doctor path. Construction does no I/O, so this runs offline.
"""

from __future__ import annotations

from platterpus import composition
from platterpus.config import Config


def test_build_backend_is_cyanrip() -> None:
    # cyanrip is the sole backend (KDD-18 — better in essentially every
    # situation: active, no >587 offset bug, max compression, -Z convergence).
    backend, name = composition.build_backend(Config())
    assert name == "cyanrip"
    assert backend.__class__.__name__ == "CyanripImpl"


# `test_build_backend_passes_working_dir` lived here until 2026-08-24. It asserted
# `backend._working_dir == tmp_path` — that the value had been HANDED OVER, which
# was true and irrelevant: nothing ever read that attribute. `CLAUDE.md` names the
# shape ("am I asserting that a thing HAPPENED, or that it was REQUESTED?"), and a
# green test over a dead field is what let the Settings row and the User Guide go
# on telling users to change it if their disk was short on space. Field, row, guide
# entry, validator and constructor parameter are all gone; this note is the record.


def test_build_musicbrainz_client_is_the_v1_impl() -> None:
    client = composition.build_musicbrainz_client()
    assert client.__class__.__name__ == "MusicBrainzNgsImpl"


def test_contact_url_is_a_reachable_project_url() -> None:
    # MusicBrainz policy wants a reachable contact in the user-agent.
    assert composition.CONTACT_URL.startswith("https://")
