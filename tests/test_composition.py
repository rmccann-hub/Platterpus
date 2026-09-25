"""Tests for platterpus.composition — the shared adapter composition root.

These pin the seam that app.py and preflight.default_context() now both go
through, so the backend selection + MB-client construction can't drift between
the GUI and the --doctor path. Construction does no I/O, so this runs offline.
"""

from __future__ import annotations

import ast
from pathlib import Path

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


# --- nothing constructs the owned adapters except this module ----------------
#
# Critical rule #1 and docs/architecture.md §2: adapters are constructed only at
# the composition root. The 2026-09-25 TASKS audit found `rig_check.py` building
# `CyanripImpl` itself, and nothing here could have caught it: the tests above
# check what `build_backend` returns, not who else builds the same thing.
#
# Scoped to the adapters this module OWNS. Its own docstring leaves the trivial
# zero-argument ones (`CtdbHttpImpl`, `DependencyManager`) inline at their call
# sites on purpose, so sweeping those would refuse a documented decision.

_SRC = Path(composition.__file__).resolve().parent
_OWNED: frozenset[str] = frozenset({"CyanripImpl", "MusicBrainzNgsImpl"})


def _constructions(source: str) -> list[tuple[str, int]]:
    """``(class name, line)`` for every call of an owned adapter class in ``source``."""
    found: list[tuple[str, int]] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
        if name in _OWNED:
            found.append((name, node.lineno))
    return found


def test_only_the_composition_root_constructs_the_owned_adapters() -> None:
    outside: list[str] = []
    at_root = 0
    for path in sorted(_SRC.rglob("*.py")):
        sites = _constructions(path.read_text(encoding="utf-8"))
        if path.name == "composition.py" and path.parent == _SRC:
            at_root += len(sites)
            continue
        outside += [
            f"{path.relative_to(_SRC)}:{line} builds {name}" for name, line in sites
        ]
    # Floor: the sweep must see the root's own constructions, or it is not looking.
    assert at_root >= len(_OWNED), f"only {at_root} construction(s) found at the root"
    assert not outside, (
        "construct these through platterpus.composition, not directly:\n  "
        + "\n  ".join(outside)
    )


def test_the_sweep_fires_on_a_direct_construction() -> None:
    """The twin: the detector must report the shape it exists to refuse."""
    source = (
        "from platterpus.adapters.cyanrip_backend import CyanripImpl\n"
        "backend = CyanripImpl(binary_path='cyanrip')\n"
    )
    assert _constructions(source) == [("CyanripImpl", 2)]


def test_build_cyanrip_backend_uses_the_binary_it_is_given() -> None:
    backend = composition.build_cyanrip_backend("/opt/test/cyanrip")
    assert backend.__class__.__name__ == "CyanripImpl"
    assert backend._binary == "/opt/test/cyanrip"  # noqa: SLF001


def test_the_backend_runs_the_HOST_EXPORTED_ripper_when_it_exists(
    tmp_path: Path, monkeypatch
) -> None:
    """Critical rule #3: the GUI calls the host-exported `~/.local/bin/cyanrip`.

    Nothing pinned this (TASKS `rule-3.routing`). The builder prefers that
    absolute path because a desktop-launched GUI's PATH may omit `~/.local/bin`;
    a change to prefer a PATH lookup, or a container entry, would pass every
    other test here. The rip argv's first element is checked too, since that is
    what the OS actually receives.
    """
    from platterpus import paths

    assert Path.home() / ".local" / "bin" / "cyanrip" == paths.CYANRIP_BINARY_DEFAULT
    exported = tmp_path / ".local" / "bin" / "cyanrip"
    exported.parent.mkdir(parents=True)
    exported.write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setattr(composition, "CYANRIP_BINARY_DEFAULT", exported)
    backend, _ = composition.build_backend(Config())
    assert backend._binary == str(exported)  # noqa: SLF001

    # And the fallback when there is no export: a PATH lookup of the ripper by
    # name, never a container command.
    monkeypatch.setattr(composition, "CYANRIP_BINARY_DEFAULT", tmp_path / "absent")
    backend, _ = composition.build_backend(Config())
    assert backend._binary == "cyanrip"  # noqa: SLF001
