"""Which *build* of a dependency is installed — and saying so where users look.

The bug these tests pin was found by the maintainer reading a dialog. Platterpus
had been taught to name the ripper build in the EAC-style log, in the JSON report
and in ``--doctor``; the launch-time dependency dialog still printed a bare
``cyanrip 0.9.3`` and a headline of ``0 missing/needs-attention``. Both were
true statements and together they were misleading: the fork install had never
happened, and the one surface the user actually reads said nothing about it.

The fork keeps upstream's version string **deliberately** (its ``meson.build``
sets a separate ``PROJECT_FORK_ID``), so a version number can never answer
"is this my fork?". That is the whole reason a build note exists as its own
concept rather than as a version comparison.
"""

from __future__ import annotations

from typing import Any

import pytest

from platterpus.deps.build_notes import BuildNote, cyanrip_build_note
from platterpus.deps.checks import ProbeResult
from platterpus.deps.manager import DependencyManager
from platterpus.deps.registry import SPECS, DependencySpec, Tier
from platterpus.ui.main_window_deps import _installed_line

FORK_BANNER = "cyanrip 0.9.4-rc1 (platterpus-fork-ga04a94b)"
STOCK_BANNER = "cyanrip 0.9.3 (release)"


def _probe(raw: str, version: tuple[int, ...] = (0, 9, 4)) -> ProbeResult:
    return ProbeResult(
        present=True,
        version=version,
        location="/home/u/.local/bin/cyanrip",
        raw_output=raw,
    )


# --- the classifier delegation ----------------------------------------------


def test_the_fork_banner_reads_as_the_wanted_build() -> None:
    note = cyanrip_build_note(_probe(FORK_BANNER))
    assert note.ok is True
    assert note.needs_attention is False
    assert "fork" in note.summary.lower()
    assert note.fix_hint == ""  # nothing to fix


def test_a_stock_banner_reads_as_the_wrong_build_and_says_what_it_costs() -> None:
    note = cyanrip_build_note(_probe(STOCK_BANNER))
    assert note.ok is False
    assert note.needs_attention is True
    assert "NOT the Platterpus fork" in note.summary
    # The detail has to say what the difference *costs*, not just that it exists —
    # otherwise a user reasonably concludes it does not matter.
    assert "pre-gap" in note.detail
    assert "Set up Platterpus" in note.fix_hint


@pytest.mark.parametrize(
    "raw",
    [
        "",  # nothing captured
        "cyanrip 0.9.4",  # no parenthetical at all
        "cyanrip 0.9.4 (g1a2b3c4)",  # a bare git describe
        "cyanrip 0.9.4 (some-distro-tag)",
        "total nonsense",
    ],
)
def test_an_unrecognised_banner_is_not_determined_never_stock(raw: str) -> None:
    """The recurring bug in this codebase is collapsing "cannot tell" into a
    definite answer. `ok=None` must stay None — reporting an unfamiliar tag as
    "unmodified upstream" would be a claim we do not have."""
    note = cyanrip_build_note(_probe(raw))
    assert note.ok is None
    assert note.needs_attention is True  # unknown IS worth telling the user
    assert "not identified" in note.summary


def test_the_classifier_is_shared_not_reimplemented() -> None:
    """One classifier, so the log, the report, --doctor and this dialog cannot
    describe the same binary four different ways (CLAUDE.md: "say which build
    produced an artifact ... classification lives in one shared pure module").

    Checked by behaviour rather than by grepping an import: a tag the shared
    module accepts as the fork must be accepted here too. `platterpus-fork-grelease`
    is the tarball-build case the fork warned about — substring-matching
    "release" would flip their own binary to "unmodified upstream".
    """
    from platterpus.ripper_identity import identify_from_banner

    tarball = "cyanrip 0.9.4-rc1 (platterpus-fork-grelease)"
    assert identify_from_banner(tarball).kind == "fork"
    assert cyanrip_build_note(_probe(tarball)).ok is True


def test_a_build_note_never_raises_on_hostile_output() -> None:
    """It is fed an external tool's stdout. A dependency dialog that crashes
    because a banner was odd is worse than one that says "could not tell"."""
    for raw in ("\x00\x01\x02", "(" * 500, ")" * 500, "cyanrip " + "9" * 5000):
        assert cyanrip_build_note(_probe(raw)).ok is None


# --- the registry wiring ----------------------------------------------------


def test_the_cyanrip_spec_carries_a_build_note() -> None:
    """The wiring, not just the function. Twenty-five tests once passed against
    a reverted client because they exercised a pure helper and never the wiring;
    this asserts the registry entry exists."""
    cyanrip = next(s for s in SPECS if s.dep_id == "cyanrip")
    assert cyanrip.build_note is not None
    assert cyanrip.build_note(_probe(STOCK_BANNER)).ok is False


def test_specs_without_a_build_note_default_to_none() -> None:
    """ "No note" must mean "the version is the whole story", never "the build is
    fine" — so the default is None and consumers treat absence as absence."""
    others = [s for s in SPECS if s.dep_id != "cyanrip"]
    assert others  # floor: this assertion is meaningless with an empty list
    assert all(s.build_note is None for s in others)


# --- the manager ------------------------------------------------------------


def _spec(dep_id: str, note: Any = None, raw: str = "") -> DependencySpec:
    return DependencySpec(
        dep_id=dep_id,
        display_name=dep_id,
        probe=lambda: _probe(raw),
        min_version=(0, 0, 0),
        tier=Tier.MANUAL,
        install_command=None,
        search_string="x",
        build_note=note,
    )


def test_check_all_records_the_build_note_and_flags_attention() -> None:
    report = DependencyManager(
        [_spec("cyanrip", cyanrip_build_note, STOCK_BANNER), _spec("flac")]
    ).check_all()

    assert report.build_notes["cyanrip"].ok is False
    assert "flac" not in report.build_notes
    assert [spec.dep_id for spec, _ in report.build_attention] == ["cyanrip"]


def test_the_right_build_produces_no_attention() -> None:
    report = DependencyManager(
        [_spec("cyanrip", cyanrip_build_note, FORK_BANNER)]
    ).check_all()
    assert report.build_notes["cyanrip"].ok is True
    assert report.build_attention == []


def test_a_raising_build_note_does_not_break_the_dependency_check() -> None:
    """A display-only enrichment must never abort a check the user needs."""

    def boom(_probe_result: ProbeResult) -> BuildNote:
        raise RuntimeError("nope")

    report = DependencyManager([_spec("cyanrip", boom, STOCK_BANNER)]).check_all()
    assert [s.dep_id for s in report.ok] == ["cyanrip"]  # still probed OK
    assert "cyanrip" not in report.build_notes  # and simply has no note
    assert report.build_attention == []


# --- the summary the user actually reads ------------------------------------


def test_the_installed_line_names_the_build_beside_the_version() -> None:
    spec = _spec("cyanrip")
    spec_named = DependencySpec(**{**spec.__dict__, "display_name": "cyanrip"})
    line = _installed_line(
        spec_named,
        {"cyanrip": (0, 9, 3)},
        {"cyanrip": cyanrip_build_note(_probe(STOCK_BANNER))},
    )
    assert line.startswith("cyanrip 0.9.3")
    assert "NOT the Platterpus fork" in line


def test_the_installed_line_is_unchanged_for_deps_with_no_note() -> None:
    line = _installed_line(_spec("flac"), {"flac": (1, 5, 0)}, {})
    assert line == "flac 1.5.0"
