"""The auto-fix supersede record: a sidecar, and a reader that must not lose it.

Two obligations, and they pull in opposite directions — which is why both are
tested here rather than trusted to a comment:

1. **The ripper's log stays byte-exact.** cyanrip's log ends with a ``Log FUN512:``
   self-checksum and ``cyanrip --verify-log`` rejects trailing content, so appending
   the addendum shipped a log the ripper called modified on every auto-fixed disc
   (round 7 lap 10, H1).
2. **The supersede stays visible on a re-parse.** That is the *original* bug the
   addendum was written for: the GUI patches from live worker state, so only a
   re-parse from disk ever saw the discarded read's CRCs. A fix that moved the
   record out of the log without teaching the reader about it would have swapped
   one wrong artifact for another.

The sweep at the bottom enforces (2) mechanically, because "remember to use
`read_log_with_addendum`" is a rule, and this project's own history says a rule in
a docstring decays while a rule in a test does not.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from platterpus import rip_addendum as ra

_REPO = Path(__file__).resolve().parent.parent
_SRC = _REPO / "src" / "platterpus"
#: Also swept: `scripts/`. **The second half of the same 2026-08-04 miss.** The rule was
#: enforced across `src/` and nowhere else, so the one log reader that lives in `scripts/`
#: — the EAC parity checker, i.e. the tool that answers "are we bit-perfect?" — was outside
#: every guard the rule has. CLAUDE.md §5.o, arriving again: enforce a rule across the
#: codebase, not at the place it was learned.
_SCRIPTS = _REPO / "scripts"


def _swept_roots() -> list[Path]:
    """Every Python file the addendum rule binds. Both roots, so neither can drift."""
    return [*_SRC.rglob("*.py"), *_SCRIPTS.rglob("*.py")]


# --- render_addendum: pure, so it is testable as text -------------------------


def _record(**over: object) -> ra.SupersededTrack:
    base: dict[str, object] = {
        "number": 5,
        "filename": "05 - Roxanne.flac",
        "crc": "E0036697",
        "accuraterip_v1": "F5426D5F — accurately ripped, confidence 12",
        "accuraterip_v2": "9EEB8843 — accurately ripped, confidence 30",
        "accuraterip_offset": "4CCBCF89 — accurately ripped (+450)",
        "secure_reread": "converged after 5 reads",
    }
    base.update(over)
    return ra.SupersededTrack(**base)  # type: ignore[arg-type]  # kwargs are typed above


def test_the_render_carries_every_field_not_just_the_crc() -> None:
    """H5: the appended version named the CRC alone.

    Everything else in the archived per-track block — AccurateRip v1/v2, the
    offset-variant result, the secure-re-read verdict — then went on describing the
    read we deleted. The fork's own table of that rip is the evidence:
    `Accurip v1 7CE3F6E7 → F5426D5F, not superseded`.
    """
    text = ra.render_addendum("accuraterip", [_record()])
    for expected in (
        "E0036697",  # the shipped CRC
        "F5426D5F",  # AR v1, recomputed
        "9EEB8843",  # AR v2, recomputed
        "4CCBCF89",  # AR +450
        "converged after 5 reads",
        "05 - Roxanne.flac",
        "Track 5",
    ):
        assert expected in text, f"{expected!r} missing from the rendered addendum"


def test_the_render_says_why_it_is_a_separate_file() -> None:
    """A reader who finds this file must not have to guess why it exists.

    Specifically: that the ripper's log is deliberately unmodified, and that
    `cyanrip --verify-log` is the reason. Without that sentence the sidecar looks
    like a stray file, and the next person to "tidy up" appends it back.
    """
    text = ra.render_addendum("instability", [_record()])
    assert "verify-log" in text
    assert "BYTE-EXACT" in text or "byte-exact" in text.lower()


def test_a_missing_field_renders_as_na_rather_than_being_dropped() -> None:
    """An omitted row silently reads as "unchanged", which is the H5 failure again."""
    text = ra.render_addendum("instability", [_record(accuraterip_v1="", crc="")])
    assert text.count("n/a") >= 2, text


def test_an_empty_track_list_renders_nothing() -> None:
    """An empty file reads as "no supersede happened", not "we had nothing to say"."""
    assert ra.render_addendum("accuraterip", []) == ""


def test_the_trigger_wording_distinguishes_the_two_reasons() -> None:
    ar = ra.render_addendum("accuraterip", [_record()])
    instab = ra.render_addendum("instability", [_record()])
    assert "AccurateRip" in ar
    assert "read consistently" in instab
    assert ar != instab


# --- paths -------------------------------------------------------------------


def test_the_sidecar_sits_beside_the_log_and_keeps_its_stem() -> None:
    path = ra.addendum_path_for("/music/The Police/Classics/Classics.log")
    assert path.parent == Path("/music/The Police/Classics")
    assert path.name == "Classics" + ra.ADDENDUM_SUFFIX


def test_a_folder_containing_a_dot_does_not_lose_part_of_its_path() -> None:
    """`with_suffix` on a full path would; this operates on the name."""
    path = ra.addendum_path_for("/music/v1.2 rips/Album.log")
    assert path.parent == Path("/music/v1.2 rips")
    assert path.name == "Album" + ra.ADDENDUM_SUFFIX


def test_the_sidecar_is_not_a_log_so_log_globs_cannot_pick_it_up() -> None:
    """`rip_files._log_candidates` globs `*.log`.

    A sidecar with a `.log` suffix would be swept as a rip log and parsed as one,
    which is a subtle way to make the album's "which files are mine?" answer wrong.
    """
    assert not ra.ADDENDUM_SUFFIX.endswith(".log")
    assert ra.ADDENDUM_SUFFIX.endswith(".txt")


# --- write + read round trip -------------------------------------------------


def test_write_then_read_folds_the_record_back_in(tmp_path: Path) -> None:
    log = tmp_path / "Album.log"
    log.write_text("cyanrip 0.9.3 (release)\nLog FUN512: abc\n", encoding="utf-8")
    original = log.read_bytes()

    written = ra.write_addendum(log, "accuraterip", [_record()])

    assert written is not None
    assert log.read_bytes() == original, "writing the sidecar modified the log"
    combined = ra.read_log_with_addendum(log)
    assert combined.startswith("cyanrip 0.9.3 (release)")
    assert "E0036697" in combined


def test_write_returns_none_and_creates_nothing_for_an_empty_list(
    tmp_path: Path,
) -> None:
    log = tmp_path / "Album.log"
    log.write_text("x\n", encoding="utf-8")
    assert ra.write_addendum(log, "accuraterip", []) is None
    assert not ra.addendum_path_for(log).exists()


def test_reading_a_log_with_no_sidecar_returns_it_unchanged(tmp_path: Path) -> None:
    """The ordinary case — most rips need no auto-fix — and it must be silent."""
    log = tmp_path / "Album.log"
    log.write_text("cyanrip 0.9.3\n", encoding="utf-8")
    assert ra.read_log_with_addendum(log) == "cyanrip 0.9.3\n"
    assert ra.addendum_text(log) == ""


def test_reading_a_missing_log_yields_empty_rather_than_raising(
    tmp_path: Path,
) -> None:
    assert ra.read_log_with_addendum(tmp_path / "nope.log") == ""


def test_an_empty_sidecar_does_not_append_a_stray_separator(tmp_path: Path) -> None:
    """A zero-byte sidecar is not a supersede, so it must not alter the text.

    Otherwise an interrupted write turns into trailing whitespace in every
    downstream consumer of the log text.
    """
    log = tmp_path / "Album.log"
    log.write_text("cyanrip 0.9.3\n", encoding="utf-8")
    ra.addendum_path_for(log).write_text("   \n", encoding="utf-8")
    assert ra.read_log_with_addendum(log) == "cyanrip 0.9.3\n"


def test_an_unreadable_sidecar_is_recorded_not_swallowed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A sidecar that EXISTS and cannot be read is a fact we must not discard.

    Distinct from the missing case, which is normal and silent. If this went quiet
    the shipped CRCs would be missing from every surface with nothing saying why —
    the "we had the fact and discarded it" shape.
    """
    from platterpus import diagnostics

    log = tmp_path / "Album.log"
    log.write_text("cyanrip 0.9.3\n", encoding="utf-8")
    sidecar = ra.addendum_path_for(log)
    sidecar.write_text("something", encoding="utf-8")

    real_read = Path.read_text

    def _boom(self: Path, *args: object, **kw: object) -> str:
        if self == sidecar:
            raise PermissionError("nope")
        return real_read(self, *args, **kw)  # type: ignore[arg-type]  # passthrough

    monkeypatch.setattr(Path, "read_text", _boom)
    before = len(diagnostics.default_log().items())
    assert ra.read_log_with_addendum(log) == "cyanrip 0.9.3\n"
    after = diagnostics.default_log().items()
    assert len(after) > before, "an unreadable sidecar was swallowed silently"
    assert after[-1].code == "addendum.log_unreadable"


def test_a_failed_write_is_recorded_and_never_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Losing the addendum must not cost a rip whose audio is already correct."""
    from platterpus import diagnostics

    log = tmp_path / "Album.log"
    log.write_text("cyanrip 0.9.3\n", encoding="utf-8")

    def _boom(self: Path, *args: object, **kw: object) -> int:
        raise OSError("disk full")

    monkeypatch.setattr(Path, "write_text", _boom)
    before = len(diagnostics.default_log().items())
    assert ra.write_addendum(log, "accuraterip", [_record()]) is None
    after = diagnostics.default_log().items()
    assert len(after) > before
    assert after[-1].code == "addendum.write_failed"


# --- the sweep: no log parse may bypass the addendum-aware reader -------------

#: Every function that turns rip-log TEXT into a parsed object. A read that feeds
#: one of these without folding the sidecar in gets checksums for bytes that are
#: not on disk.
_PARSE_FUNCS: frozenset[str] = frozenset(
    {
        "parse_cyanrip_log",
        "parse_rip_log",
        # **ADDED 2026-08-04, and this omission is what let the bug through.** The sweep
        # keyed only on the two full parsers, so a module that opened a rip log and pulled
        # per-track CRCs out of it by ANY other route was not considered a log-parsing
        # module at all — it was invisible, not exempt. `scripts/eac_parity.py` read the
        # log with `decode_log_bytes` and extracted CRCs with `compare_logs`, and reported
        # **13/14 NOT parity** for a rip that was 14/14, because the ripper's log records
        # the read that Platterpus discarded. A wrong answer to the project's headline
        # question, from the project's own tool.
        #
        # The lesson is the trigger, not the file: a sweep that names *some* ways of
        # reading a log will keep missing the next one. These are every entry point that
        # turns log TEXT into per-track CRCs.
        "compare_logs",
        "track_copy_crcs",
    }
)

#: The sanctioned readers.
_SANCTIONED: frozenset[str] = frozenset({"read_log_with_addendum", "with_addendum"})

#: Modules exempt from the sweep, each with a reason. Deliberately tiny: an
#: exemption list that grows is the rule being retired one file at a time.
_EXEMPT: dict[str, str] = {
    # The addendum module itself — it IS the reader.
    "rip_addendum.py": "defines the sanctioned readers",
    # rip_compare re-reads a REPORT (JSON), never a log, and parses log text only
    # from text already handed to it by a caller that used a sanctioned reader.
    "rip_compare.py": "parses text passed in, never a path it opened itself",
}


def _log_parsing_modules() -> list[Path]:
    """Source modules that call a rip-log parser at all."""
    found: list[Path] = []
    for path in sorted(_swept_roots()):
        if path.name in _EXEMPT:
            continue
        source = path.read_text(encoding="utf-8", errors="replace")
        if any(f"{name}(" in source for name in _PARSE_FUNCS):
            found.append(path)
    return found


def test_no_module_parses_a_rip_log_it_read_without_the_addendum() -> None:
    """A module that opens a log AND parses it must use a sanctioned reader.

    Deliberately coarse — module-level, not flow-sensitive — because the precise
    version (does *this* text come from *that* read?) needs dataflow analysis, and a
    matcher narrower than the language it inspects produces confident wrong answers.
    Coarse here means: if you parse a log and you also call `read_text`/`read_bytes`,
    you must name a sanctioned reader somewhere in the file. False *positives* are
    possible and are cheap to resolve (use the reader, or take an exemption with a
    reason); a false negative is the bug shipping again.
    """
    modules = _log_parsing_modules()
    # Floors. A sweep that examined nothing, or found no parse sites, passes by
    # finding nothing.
    assert len(modules) >= 3, (
        f"only {len(modules)} module(s) parse a rip log — the sweep has lost its "
        "subject matter, or a parser was renamed without updating _PARSE_FUNCS"
    )

    offenders: list[str] = []
    checked = 0
    for path in modules:
        source = path.read_text(encoding="utf-8", errors="replace")
        opens_a_file = "read_text(" in source or "read_bytes(" in source
        if not opens_a_file:
            continue  # it parses text handed to it; not this rule's business
        checked += 1
        if not any(name in source for name in _SANCTIONED):
            offenders.append(str(path.relative_to(_REPO)))

    assert checked >= 2, (
        f"only {checked} module(s) both open and parse a log — the second floor: "
        "with fewer than two there is nothing to compare and the sweep is decoration"
    )
    assert not offenders, (
        "these modules read a rip log from disk and parse it without going through "
        f"platterpus.rip_addendum: {offenders}. A re-parse that skips the sidecar "
        "reports the CRCs of bytes the auto-fix deleted — the bug the addendum "
        "exists to prevent, and the trap moving it to a sidecar created."
    )


def test_the_sweep_would_fail_if_a_reader_were_reverted() -> None:
    """Prove the sweep is not vacuous, without editing the source tree.

    Runs the same predicate over a *synthetic* module that reads a log and parses it
    with no sanctioned reader. This project has shipped a detector that passed
    against the very bug it was written for, twice; a sweep whose failure path is
    never exercised is indistinguishable from one that cannot fail.
    """
    fake = (
        "text = Path(p).read_text(encoding='utf-8')\nreturn parse_cyanrip_log(text)\n"
    )
    assert any(f"{name}(" in fake for name in _PARSE_FUNCS)
    assert "read_text(" in fake
    assert not any(name in fake for name in _SANCTIONED), (
        "the synthetic offender accidentally satisfies the sweep, so the sweep's "
        "failure path is untested"
    )


def test_every_exemption_names_a_module_that_exists() -> None:
    """An exemption for a deleted or renamed module silently widens the rule."""
    for name in _EXEMPT:
        assert list(_SRC.rglob(name)), f"exempt module {name} no longer exists"
    for name, reason in _EXEMPT.items():
        assert reason.strip(), f"{name} is exempt with no stated reason"


def test_the_module_never_imports_qt() -> None:
    """It is called from a worker thread and from the pure-ish file layer."""
    tree = ast.parse((_SRC / "rip_addendum.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert "PySide6" not in (node.module or "")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                assert "PySide6" not in alias.name
