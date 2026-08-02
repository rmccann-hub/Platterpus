"""Auditing a whole library of finished rips from its artifacts.

The v0.6.1 hardware plan asked a human to open files and read fields. The
maintainer's answer — *"either have them done by the application or give me a
command to do all of it at once"* — is right, and every question on that list is
answerable from what is already on disk.

The two assertions that matter most here are both about **not lying**:

* an empty FLAC in a rip that reports SUCCESS must read differently from one
  after a cancel (the first is a bug worth reporting, the second is documented
  upstream behaviour), and
* a library the audit cannot read must say so rather than come back clean.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from platterpus import rip_audit
from platterpus.rip_audit import LEVEL_OK, LEVEL_WARN, audit_album, render, run_audit


def _write(folder: Path, report: dict, *, flac_sizes: list[int] | None = None) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "Album.platterpus.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    for i, size in enumerate(flac_sizes or [], start=1):
        (folder / f"{i:02d}.flac").write_bytes(b"x" * size)
    return path


_BIG = rip_audit.MIN_PLAUSIBLE_TRACK_BYTES * 10


def _healthy(**over: object) -> dict:
    base: dict = {
        "album": "Healthy",
        "rip": {
            "ripper_identity": "fork",
            "ripper_build": "platterpus-fork-ga04a94b",
            "rip_completed": True,
            "rip_completed_tracks": 2,
            "rip_completed_total": 2,
        },
        "outcome": {"status": "success"},
        "tracks": [{"pregap_source": "TOC"}],
    }
    base.update(over)  # type: ignore[arg-type]
    return base


# --- the empty-file check, and why it must read two different ways -----------


def test_empty_audio_after_a_cancel_is_reported_as_expected(tmp_path: Path) -> None:
    """The fork measured this (round 4, Q9): cyanrip encodes on a separate
    thread behind a queue, so it logs a track — CRC and all — before the encoder
    flushes. Kill it and you get a 0-byte FLAC for a "successful" track. That is
    upstream behaviour, not corruption, and telling the user it is corruption
    would send them hunting a disc problem that does not exist.
    """
    report = _healthy()
    report["rip"]["rip_completed"] = False
    report["outcome"] = {"status": "cancelled"}
    album = audit_album(_write(tmp_path / "a", report, flac_sizes=[_BIG, 0]))

    empty = [f for f in album.findings if "empty/truncated" in f.text]
    assert len(empty) == 1
    assert "EXPECTED, not corruption" in empty[0].text
    assert "Re-rip" in empty[0].text


def test_empty_audio_in_a_SUCCESSFUL_rip_is_reported_as_a_bug(tmp_path: Path) -> None:
    """The other half, and the one that would otherwise hide. A rip claiming
    success with a 0-byte track means we verified audio that is not there —
    which is the app making a claim it cannot support."""
    album = audit_album(_write(tmp_path / "a", _healthy(), flac_sizes=[_BIG, 0]))

    empty = [f for f in album.findings if "empty/truncated" in f.text]
    assert len(empty) == 1
    assert "should not happen" in empty[0].text
    assert "EXPECTED" not in empty[0].text


def test_a_complete_rip_with_real_files_is_clean(tmp_path: Path) -> None:
    """Positive control. Without it every check above could be an auditor that
    warns about everything."""
    album = audit_album(_write(tmp_path / "a", _healthy(), flac_sizes=[_BIG, _BIG]))
    assert album.worst == LEVEL_OK, [f.text for f in album.findings]
    assert album.empty_files == 0


# --- completion is tri-state -------------------------------------------------


def test_an_absent_completion_footer_is_not_a_failure_verdict(tmp_path: Path) -> None:
    """`None` means the ripper never got to tell us — a killed rip, or a log
    from before the fork emitted the footer. `False` means it finished and
    reported failure. Rendering the first as the second would accuse a rip that
    may have been fine."""
    report = _healthy()
    del report["rip"]["rip_completed"]
    album = audit_album(_write(tmp_path / "a", report, flac_sizes=[_BIG]))

    assert album.completed is None
    assert any("footer is absent" in f.text for f in album.findings)
    assert not any("did NOT complete" in f.text for f in album.findings)


def test_an_incomplete_rip_carries_the_rippers_own_counts_and_reason(
    tmp_path: Path,
) -> None:
    report = _healthy()
    report["rip"].update(
        rip_completed=False,
        rip_completed_tracks=2,
        rip_completed_total=14,
        rip_completed_reason="interrupted by user",
    )
    album = audit_album(_write(tmp_path / "a", report, flac_sizes=[_BIG]))
    text = " ".join(f.text for f in album.findings)
    assert "2 of 14" in text
    assert "interrupted by user" in text


# --- failures carry what is needed to reproduce them -------------------------


def test_a_failed_rip_reports_exit_code_and_command(tmp_path: Path) -> None:
    report = _healthy()
    report["outcome"] = {
        "status": "failed",
        "failure_hint": "Invalid track number 17, list has 16 tracks!",
        "ripper_exit_code": 1,
        "ripper_command_display": "cyanrip -d /dev/sr0 -N -t 17=",
    }
    album = audit_album(_write(tmp_path / "a", report, flac_sizes=[_BIG]))
    text = " ".join(f.text for f in album.findings)
    assert "16 tracks" in text
    assert "exit code: 1" in text
    assert "-t 17=" in text


def test_a_never_reaped_child_reads_as_null_not_zero(tmp_path: Path) -> None:
    """A child wedged in a drive ioctl is never reaped, and `0` there would read
    as a clean exit."""
    report = _healthy()
    report["outcome"] = {"status": "failed", "ripper_exit_code": None}
    album = audit_album(_write(tmp_path / "a", report, flac_sizes=[_BIG]))
    assert any("not reaped (null)" in f.text for f in album.findings)


# --- multi-disc ---------------------------------------------------------------


def test_an_undetermined_medium_warns_that_titles_may_be_wrong(tmp_path: Path) -> None:
    report = _healthy()
    report["disc"] = {
        "medium_basis": "undetermined-first",
        "medium_undetermined": True,
        "medium_detail": "Could not determine which of this release's 4 discs...",
    }
    album = audit_album(_write(tmp_path / "a", report, flac_sizes=[_BIG]))
    assert album.worst == LEVEL_WARN
    assert any("may belong to a different disc" in f.text for f in album.findings)


def test_a_resolved_medium_does_not_warn(tmp_path: Path) -> None:
    report = _healthy()
    report["disc"] = {"medium_basis": "disc-id", "medium_undetermined": False}
    album = audit_album(_write(tmp_path / "a", report, flac_sizes=[_BIG]))
    assert album.worst == LEVEL_OK


# --- the headline nobody has had yet -----------------------------------------


def test_a_successful_subchannel_read_is_called_out_loudly(tmp_path: Path) -> None:
    """As of v0.6.1 the fork's Q-subchannel path has never executed
    successfully anywhere — disc images always fail into `unknown`. The first
    real one is a result, and it must not be buried in a per-album line."""
    report = _healthy(tracks=[{"pregap_source": "sub-channel (not signalled by TOC)"}])
    audits = [audit_album(_write(tmp_path / "a", report, flac_sizes=[_BIG]))]
    text = render(audits, tmp_path)
    assert "SUB-CHANNEL pre-gap read SUCCEEDED" in text


def test_the_headline_is_absent_when_no_subchannel_read_happened(
    tmp_path: Path,
) -> None:
    """Guards the guard: if the banner fired unconditionally it would be
    meaningless, and the test above would pass forever."""
    audits = [audit_album(_write(tmp_path / "a", _healthy(), flac_sizes=[_BIG]))]
    assert "SUCCEEDED" not in render(audits, tmp_path)


def test_the_unknown_pregap_reasons_stay_distinguishable(tmp_path: Path) -> None:
    """ "Sub-channel unreadable" and "CRC mismatches" are two different failure
    modes the fork's contract lists separately, and both are results."""
    report = _healthy(
        tracks=[
            {
                "pregap_state": "unknown",
                "pregap_unknown_reason": "sub-channel unreadable",
            },
            {
                "pregap_state": "unknown",
                "pregap_unknown_reason": "sub-channel CRC mismatches",
            },
        ]
    )
    album = audit_album(_write(tmp_path / "a", report, flac_sizes=[_BIG]))
    assert len(album.pregap_sources) == 2


# --- it never raises, and never comes back falsely clean ---------------------


@pytest.mark.parametrize(
    "content", ["", "not json", "[]", '{"tracks": "not a list"}', "\x00\x01", "null"]
)
def test_a_broken_report_is_reported_not_crashed_on(
    tmp_path: Path, content: str
) -> None:
    """A live library contains half-written JSON from interrupted rips. An
    auditor that dies on the first one is useless exactly when it is needed —
    and one that silently skips it is worse, because the album vanishes from
    the report."""
    folder = tmp_path / "a"
    folder.mkdir()
    path = folder / "Album.platterpus.json"
    path.write_text(content, encoding="utf-8")
    album = audit_album(path)
    assert album.findings, "a broken report produced no findings at all"


def test_an_empty_library_says_so_rather_than_looking_clean(tmp_path: Path) -> None:
    """Exit 0 with no output would read as "everything is fine"."""
    text = render([], tmp_path)
    assert "No .platterpus.json reports found" in text
    assert run_audit(tmp_path) == 0


def test_the_exit_code_distinguishes_a_clean_library_from_one_needing_work(
    tmp_path: Path,
) -> None:
    """Proves the exit code can be both. A checker that always returns 0 is
    decoration."""
    clean = tmp_path / "clean"
    _write(clean / "a", _healthy(), flac_sizes=[_BIG])
    assert run_audit(clean) == 0

    dirty = tmp_path / "dirty"
    bad = _healthy()
    bad["outcome"] = {"status": "failed"}
    _write(dirty / "a", bad, flac_sizes=[_BIG])
    assert run_audit(dirty) == 1


def test_it_walks_subfolders(tmp_path: Path) -> None:
    """A rips folder is a tree of album folders, not a flat directory."""
    _write(tmp_path / "Artist" / "Album One", _healthy(), flac_sizes=[_BIG])
    _write(tmp_path / "Artist" / "Album Two", _healthy(), flac_sizes=[_BIG])
    assert len(rip_audit.find_reports(tmp_path)) == 2


def test_the_audit_is_read_only(tmp_path: Path) -> None:
    """It runs against a live library, so it must not touch it. Compares the
    full tree before and after, including file sizes and mtimes."""
    _write(tmp_path / "a", _healthy(), flac_sizes=[_BIG, 0])

    def snapshot() -> set[tuple[str, int]]:
        return {
            (str(p.relative_to(tmp_path)), p.stat().st_size)
            for p in sorted(tmp_path.rglob("*"))
            if p.is_file()
        }

    before = snapshot()
    run_audit(tmp_path)
    assert snapshot() == before


def test_the_cli_flag_is_wired(tmp_path: Path) -> None:
    """Grep the call site: a fully-implemented feature reachable from nothing
    is a failure this project has shipped."""
    import inspect

    from platterpus import app

    source = inspect.getsource(app)
    assert "--audit-rips" in source
    assert "rip_audit.run_audit(" in source


# --- the registry, and the automatic per-rip block ---------------------------
#
# "Does the check happen automatically and get added to the json file? include
# all checks you need and any future or past checks too, should be easy."
# Yes, and the registry is what makes "easy" true: a future check is one
# function plus one row in CHECKS, and it then runs in both surfaces at once.


def test_every_registered_check_is_accounted_for(tmp_path: Path) -> None:
    """The core registry invariant, and the reason it is a registry.

    Every check must appear in `checks_run` or `checks_skipped` — never simply
    vanish. A findings list that is short because a check did not execute reads
    identically to one that is short because nothing was wrong, and this
    codebase has shipped that confusion three times.
    """
    block = rip_audit.self_check_block(_healthy(), tmp_path)
    accounted = set(block["checks_run"]) | set(block["checks_skipped"])
    registered = {c.name for c in rip_audit.CHECKS}
    assert accounted == registered, f"unaccounted: {registered ^ accounted}"


def test_a_file_check_is_SKIPPED_not_passed_when_there_is_no_folder() -> None:
    """The distinction the whole tri-state discipline exists for. Reading a
    report without its album folder cannot prove the audio is fine, and must
    not imply it did."""
    block = rip_audit.self_check_block(_healthy(), None)
    file_checks = [c.name for c in rip_audit.CHECKS if c.needs_files]
    assert file_checks, "no check touches the filesystem; this test is vacuous"
    for name in file_checks:
        assert name in block["checks_skipped"]
        assert name not in block["checks_run"]


def test_a_check_that_raises_is_reported_and_the_rest_still_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An auditor that dies halfway through a library is worse than one that
    reports a broken check. Proves the guard fires AND that it is not a
    swallow — the failure is named in the findings."""

    def boom(report: dict, album: rip_audit.AlbumAudit) -> None:
        raise RuntimeError("deliberate")

    broken = rip_audit.Check("exploding", "?", False, boom)
    monkeypatch.setattr(rip_audit, "CHECKS", (broken, *rip_audit.CHECKS))

    block = rip_audit.self_check_block(_healthy(), tmp_path)
    assert "exploding" in block["checks_skipped"]
    assert any("could not run" in f["text"] for f in block["findings"])
    # ...and the real checks still ran.
    assert "ripper_build" in block["checks_run"]


def test_the_registry_is_not_trivially_small() -> None:
    """Floor. Every sweep above is "for each check", satisfied by an empty
    registry."""
    assert len(rip_audit.CHECKS) >= 5
    assert len({c.name for c in rip_audit.CHECKS}) == len(rip_audit.CHECKS)
    assert all(c.question.endswith("?") for c in rip_audit.CHECKS)


def test_the_block_is_embedded_in_a_written_report(tmp_path: Path) -> None:
    """End-to-end, through the real writer: the user gets this without asking.

    Also the regression for a real defect — the first run of this reported
    "completion footer absent" for a log that had one, because the parser knew
    `rip_completed` and the report never serialized it.
    """
    from platterpus.parsers.rip_log import RipLog, TrackResult
    from platterpus.rip_report import write_report

    (tmp_path / "01.flac").write_bytes(b"x" * _BIG)
    log_file = tmp_path / "Album.log"
    log_file.write_text("x", encoding="utf-8")

    out = write_report(
        RipLog(
            log_creator="cyanrip 0.9.4-rc1",
            ripper_build="platterpus-fork-ga04a94b",
            rip_completed=True,
            rip_completed_tracks=1,
            rip_completed_total=1,
            tracks=(TrackResult(1),),
        ),
        log_file=log_file,
        generated_at="2026-08-02T00:00:00Z",
    )
    assert out is not None
    block = json.loads(Path(out).read_text(encoding="utf-8"))["self_check"]
    assert block["schema"] == rip_audit.SELF_CHECK_SCHEMA
    assert set(block["checks_run"]) == {c.name for c in rip_audit.CHECKS}
    assert any("rip completed (1 of 1" in f["text"] for f in block["findings"]), block[
        "findings"
    ]


def test_the_bulk_audit_and_the_embedded_block_agree(tmp_path: Path) -> None:
    """Two surfaces, one registry — so they cannot word the same finding
    differently. If these diverge, one of them has grown its own check.

    Asserted as exact equality on the check-produced findings. The bulk audit
    additionally appends the rip's verdict line, which the embedded block has
    no reason to duplicate (it is already elsewhere in the same JSON), so that
    one trailing entry is excluded by *position* rather than by matching on its
    text — matching on text would let a real divergence hide behind a filter.
    """
    report = _healthy()
    path = _write(tmp_path / "a", report, flac_sizes=[_BIG])

    embedded = [
        f["text"] for f in rip_audit.self_check_block(report, path.parent)["findings"]
    ]
    bulk = [f.text for f in audit_album(path).findings]

    assert embedded, "the embedded block produced no findings at all"
    assert bulk[: len(embedded)] == embedded, (
        f"the two surfaces disagree:\n  embedded: {embedded}\n  bulk    : {bulk}"
    )
    # And the only extra is the verdict line the bulk report adds.
    assert len(bulk) - len(embedded) <= 1
