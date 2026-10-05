#!/usr/bin/env python3
"""Emit the full map of everything Platterpus has or relies on, derived from code.

The maintainer's ask (2026-10-05): *"do a full map out of what projects /
languages / versions / applications / dependencies you have or rely on. keep a
detailed list somewhere standard that you and other applications can see and
use."*

**Two forms, one source, so they cannot drift.** This script builds ONE list of
entries and renders it twice:

* ``bom.cdx.json`` at the repository root — a CycloneDX 1.7 bill of materials
  (``bom.cdx.json`` is the file name CycloneDX documents for a JSON BOM), which
  dependency-track, OSV-Scanner, grype and any other CycloneDX consumer can read;
* the block between the ``BEGIN GENERATED`` / ``END GENERATED`` markers in
  ``DEPENDENCIES.md`` — the same entries as tables for a person.

Both are written from the same objects in the same run, which is the same trick
``scripts/emit_script_language.py`` uses for its prose and its JSON.

**Nothing in it is typed from memory where code can answer.** Each category is
read out of the thing that enforces it:

* Python packages, their pins and the supported interpreter range — ``pyproject.toml``
  and ``build/python-appimage/requirements.txt`` (what the AppImage ships);
* the external programs the app runs — the dependency registry
  (``deps/registry.py``), the real setup-wizard plan (``HostSetup._commands_for``,
  called here, so the container packages and exports are the ones the wizard
  installs), ``install_argv`` for each distro family, the tool-lookup calls in
  ``src/`` (``resolve_tool`` / ``find_tool`` / ``which`` / ``_host_tool``), and
  named constants such as ``sleep_inhibit.INHIBIT_BINARY``;
* the cyanrip fork — ``deps/fork_source.py``'s pin, version and targets, and
  ``handshake_approval``'s round;
* external services — the URL constants in ``src/`` (and, for MusicBrainz, the
  host ``musicbrainzngs`` itself is configured with, because our client never
  overrides it);
* CI — every ``uses:``, ``runs-on:``, ``pip install`` and ``apt-get install`` in
  ``.github/workflows/*.yml``.

**What IS typed here, and how it is held to the code.** A few things have no
constant to read: what a tool is *for*, who runs a service, and the handful of
programs spawned with a literal argv (the menu-cache refreshers, ``bash`` for
``--rig-session``). Those live in the annotation tables below, and each one is
checked BOTH ways when this script runs:

* every tool the code is found to use must have an annotation (so a new
  ``resolve_tool("x")`` cannot slip in unmapped — the run stops and names it);
* every annotation must still be found in the code (a **witness**: the literal
  must appear as a string in the named file, docstrings excluded), so a tool the
  code stopped using cannot linger in the map.

**Determinism.** No timestamp and no serial number: ``metadata.timestamp`` and
``serialNumber`` are both optional in CycloneDX, and either one would change on
every run, which would make ``--check`` fail at random — and the first fix anyone
reaches for is to delete the check. The release date was considered as a fixed
timestamp and rejected: the ``[Unreleased]`` section has no date, so between
releases there is no honest value to put there. The BOM instead names the app
version it describes (``metadata.component.version``), which is the fact a
reader needs, and which is why this generator is re-run after a version bump.

**What this is not.** It is a *pre-build* BOM (CycloneDX lifecycle ``pre-build``):
the constraints the project declares, not the versions a particular install
resolved. The CI ``sbom`` job's artifact is the resolved, built-environment view;
``build_info.component_inventory`` is what a user's machine actually has at run
time. All three answer different questions.

**Schema validation is not done here.** No CycloneDX JSON-schema validator is a
dependency of this project, and adding one needs the maintainer's approval. The
structure is held by ``tests/test_bom_emitted.py``'s own assertions instead.

**Where the code lives.** This file is the command; ``scripts/bommap/`` is
the generator, one module per job (see its ``__init__``), the same
arrangement as ``scripts/lap_language.py`` over ``scripts/laplang/``.

Usage::

    python3 scripts/emit_bom.py            # write bom.cdx.json + the DEPENDENCIES.md block
    python3 scripts/emit_bom.py --stdout   # print the JSON, write nothing
    python3 scripts/emit_bom.py --check    # exit 1 if either is stale
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

# The package puts src/ on sys.path itself; these imports need the line above.
from bommap.model import CATEGORIES, ROOT_REF, GeneratorError  # noqa: E402
from bommap.reading import _join, tool_lookups  # noqa: E402
from bommap.render import (  # noqa: E402
    BEGIN_MARKER,
    END_MARKER,
    SPEC_VERSION,
    bom,
    collect,
    committed_block,
    dependency_graph,
    render_json,
    render_markdown,
    splice,
)
from bommap.workflows import workflows  # noqa: E402

#: What callers (and the test) reach through this module. Listed so the
#: re-exports above are a stated surface rather than an accident of imports.
__all__ = [
    "BEGIN_MARKER",
    "CATEGORIES",
    "END_MARKER",
    "MARKDOWN_PATH",
    "OUTPUT_PATH",
    "ROOT_REF",
    "SPEC_VERSION",
    "GeneratorError",
    "bom",
    "collect",
    "committed_block",
    "dependency_graph",
    "main",
    "render_json",
    "render_markdown",
    "splice",
    "tool_lookups",
    "workflows",
]

_REPO_ROOT: Path = _SCRIPTS.parent

#: The machine-readable output. CycloneDX's documented name for a JSON BOM.
OUTPUT_PATH: Path = _REPO_ROOT / "bom.cdx.json"

#: The human-readable output: a block inside an EXISTING document, not a new
#: file (CLAUDE.md Critical rule #7 — a new file is the last resort).
MARKDOWN_PATH: Path = _REPO_ROOT / "DEPENDENCIES.md"


def main(argv: list[str] | None = None) -> int:
    """Write, print or check. Exit 0 on success, 1 when stale, 2 when the code
    and the generator's annotations disagree (the message names what)."""
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--stdout", action="store_true", help="print the JSON, write nothing"
    )
    group.add_argument(
        "--check", action="store_true", help="exit 1 if either output is stale"
    )
    args = parser.parse_args(argv)

    try:
        text = render_json()
        block = render_markdown()
    except GeneratorError as exc:
        sys.stderr.write(f"emit_bom: {exc}\n")
        return 2
    if args.stdout:
        sys.stdout.write(text)
        return 0
    document = (
        MARKDOWN_PATH.read_text(encoding="utf-8") if MARKDOWN_PATH.exists() else ""
    )
    if args.check:
        current = (
            OUTPUT_PATH.read_text(encoding="utf-8") if OUTPUT_PATH.exists() else ""
        )
        stale: list[str] = []
        if current != text:
            stale.append(OUTPUT_PATH.name)
        if committed_block(document) != block:
            stale.append(f"the generated block in {MARKDOWN_PATH.name}")
        if stale:
            sys.stderr.write(
                f"stale: {_join(stale)}.\nRegenerate with: python3 scripts/emit_bom.py\n"
            )
            return 1
        return 0
    try:
        updated = splice(document, block)
    except GeneratorError as exc:
        sys.stderr.write(f"emit_bom: {MARKDOWN_PATH.name}: {exc}\n")
        return 2
    OUTPUT_PATH.write_text(text, encoding="utf-8")
    MARKDOWN_PATH.write_text(updated, encoding="utf-8")
    sys.stdout.write(
        f"wrote {OUTPUT_PATH.name} and the block in {MARKDOWN_PATH.name}\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
