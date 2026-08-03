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
    """A report that a **fully clean fork rip** would actually produce.

    Deliberately complete rather than minimal. Every check in the registry must
    be able to reach a positive verdict from this fixture, because
    ``test_a_complete_rip_with_real_files_is_clean`` asserts the audit comes back
    with nothing to say — and a fixture missing the fields a check reads would
    make that test pass for the wrong reason (the check would go quiet, not
    clean). It was exactly that: the first real-hardware run of the embedded
    self-check found two checks running silently, and the reason this fixture had
    never noticed is that it never gave them anything to read.

    So: medium selection recorded, both halves of the command line present, and
    a pre-gap provenance row. Take any of them away and the audit says "not
    determined" — which is the behaviour the sibling tests below pin.
    """
    base: dict = {
        "album": "Healthy",
        "rip": {
            "ripper_identity": "fork",
            "ripper_build": "platterpus-fork-ga04a94b",
            "rip_completed": True,
            "rip_completed_tracks": 2,
            "rip_completed_total": 2,
            # The fork echoes the command line it received; the argv check
            # compares it against what we recorded sending.
            "invoked_as": "/usr/local/bin/cyanrip -d /dev/sr0 -N",
        },
        "outcome": {
            "status": "success",
            "ripper_argv": ["/home/u/.local/bin/cyanrip", "-d", "/dev/sr0", "-N"],
        },
        "disc": {"medium_basis": "disc-id"},
        # The TOC-derived pressing identity, so the disc-identity check has
        # something to confirm rather than something to miss.
        "tracks": [{"pregap_source": "TOC"}],
        "artifacts": {"eac_log": {"text": _stamped_eac_log()}},
    }
    base.setdefault("rip", {})
    base["rip"].setdefault("musicbrainz_disc_id", "pNtImOkdBm9RMBIalzx0w9cfsYY-")
    base["rip"].setdefault("cddb_id", "E20DFE0E")
    base.update(over)  # type: ignore[arg-type]
    return base


def _stamped_eac_log(body: str = "Track  1\n     Copy OK\n") -> str:
    """An EAC-style log carrying a VALID checksum footer.

    Built with the renderer's own footer function rather than a hand-typed hash,
    so the fixture cannot drift from the verifier: if the checksum format ever
    changes, this fixture changes with it instead of quietly starting to fail
    verification and turning the positive control into a false alarm.
    """
    from platterpus.eac_log_export import _checksum_footer

    return body + _checksum_footer(body)


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


# --- the three checks added after "the logs must include everything" ---------


def test_a_command_line_that_changed_in_transit_is_caught(tmp_path: Path) -> None:
    """Both halves of this comparison existed and nothing compared them.

    We record the argv we spawned; the fork prints the argv it received (our
    handshake ask A3). The pair exists *specifically* so a wrapper, a shell or
    the Distrobox host-export altering an argument becomes visible — and a
    difference nothing looks at is not visible. This is the look.
    """
    report = _healthy()
    report["outcome"]["ripper_argv"] = ["cyanrip", "-d", "/dev/sr0", "-N", "-o", "flac"]
    report["rip"]["invoked_as"] = "/usr/bin/cyanrip -d /dev/sr0 -o flac"  # -N vanished

    album = audit_album(_write(tmp_path / "a", report, flac_sizes=[_BIG]))
    hit = [f for f in album.findings if "changed in transit" in f.text]
    assert len(hit) == 1, [f.text for f in album.findings]
    assert "-N" in hit[0].text
    assert album.worst == LEVEL_WARN


def test_matching_command_lines_do_not_warn(tmp_path: Path) -> None:
    """The positive control, and it must tolerate legitimate differences: the
    ripper's argv[0] is the resolved absolute path behind the host export while
    ours is the wrapper we invoked, and its line is shell-formatted. Comparing
    strings would cry wolf on every single rip."""
    report = _healthy()
    report["outcome"]["ripper_argv"] = ["cyanrip", "-d", "/dev/sr0", "-N", "-o", "flac"]
    report["rip"]["invoked_as"] = (
        "/home/u/src/cyanrip/build/src/cyanrip -d /dev/sr0 -N -o flac"
    )
    album = audit_album(_write(tmp_path / "a", report, flac_sizes=[_BIG]))
    assert not any("changed in transit" in f.text for f in album.findings)
    assert any("received the" in f.text for f in album.findings)


def test_a_missing_argv_half_reports_not_determined_rather_than_nothing(
    tmp_path: Path,
) -> None:
    """A half-missing comparison must say so — it must NOT go quiet.

    This test previously asserted the opposite (silence when a half is absent),
    on the reasoning that an older rip or a stock cyanrip that does not print
    ``Invoked as:`` should not be reported as a mismatch. That reasoning is
    sound and the conclusion was wrong: a check that says nothing is
    indistinguishable in the report from a check that found everything in
    order, and the first real-hardware run of the embedded ``self_check``
    demonstrated it — ``argv_agreement`` appeared in ``checks_run`` while no
    finding mentioned it.

    "Not a mismatch" and "nothing to say" are different claims. The fix is to
    report the *reason* rather than to fall silent.
    """
    report = _healthy()
    report["rip"].pop("invoked_as")  # stock cyanrip does not print it
    album = audit_album(_write(tmp_path / "a", report, flac_sizes=[_BIG]))

    # Still not accused of a mismatch...
    assert not any("transit" in f.text for f in album.findings)
    assert not any("received the" in f.text for f in album.findings)
    # ...but it is on the record as undetermined, with the reason.
    undetermined = [
        f for f in album.findings if "command-line agreement not determined" in f.text
    ]
    assert len(undetermined) == 1
    assert "Invoked as" in undetermined[0].text
    assert undetermined[0].level != LEVEL_OK


def test_an_altered_eac_log_is_detected(tmp_path: Path) -> None:
    """We publish the log's SHA-256 as an openly-verifiable integrity claim.
    Publishing a claim and never checking it ourselves is the weaker half of a
    promise."""
    from platterpus.eac_log_export import render_eac_style_log
    from platterpus.parsers.cyanrip_log import parse_cyanrip_log

    good = render_eac_style_log(
        parse_cyanrip_log(
            "cyanrip 0.9.4-rc1 (platterpus-fork-g1)\n"
            "Track 1 ripped and encoded successfully!\n"
        ),
        platterpus_version="0.6.1",
        build_fingerprint="test",
        encoder_versions={},
    )
    tampered = good.replace("Track  1", "Track  9", 1)
    assert tampered != good, "the tamper did not change anything; test is vacuous"

    cases = (
        ("intact", good, "matches its own"),
        ("tampered", tampered, "does NOT match"),
    )
    for folder_name, text, expect in cases:
        report = _healthy()
        report["artifacts"] = {"eac_log": {"text": text, "exists": True}}
        album = audit_album(_write(tmp_path / folder_name, report, flac_sizes=[_BIG]))
        assert any(expect in f.text for f in album.findings), (
            f"{folder_name}: expected {expect!r} in {[f.text for f in album.findings]}"
        )


def test_a_truncated_embedded_log_is_not_accused_of_tampering(tmp_path: Path) -> None:
    """A truncated *copy* cannot verify, and calling that a mismatch would be a
    false accusation against an intact file on disk."""
    report = _healthy()
    report["artifacts"] = {
        "eac_log": {"text": "partial...", "exists": True, "truncated": True}
    }
    album = audit_album(_write(tmp_path / "a", report, flac_sizes=[_BIG]))
    assert any("cannot be re-checked" in f.text for f in album.findings)
    assert not any("does NOT match" in f.text for f in album.findings)


def test_the_disc_identity_is_reported_for_cross_rip_comparison(tmp_path: Path) -> None:
    """TOC-derived, so it identifies the same pressing across re-rips no matter
    what the metadata says. Without it in the audit, "is this the same disc as
    last time?" needs the JSON opened by hand."""
    report = _healthy()
    report["rip"]["musicbrainz_disc_id"] = "oMp2k.ixH0QqrdaZzsARoRS.p6c-"
    report["rip"]["cddb_id"] = "14000603"
    album = audit_album(_write(tmp_path / "a", report, flac_sizes=[_BIG]))
    text = " ".join(f.text for f in album.findings)
    assert "oMp2k" in text and "14000603" in text


# --- THE FLOOR: a check that runs must say something -------------------------
#
# The third state `run_checks` originally missed. It distinguished "ran" from
# "skipped" carefully — and a check that ran and emitted nothing landed in
# `checks_run` with no finding anywhere, which in the report is indistinguishable
# from a check that found everything in order.
#
# It was not hypothetical. The first real-hardware run of the embedded
# `self_check` (The Police, 2026-08-02, stock cyanrip 0.9.3) listed eight checks
# run, zero skipped, and carried six findings. `pregap` and `argv_agreement` were
# the silent two, because stock cyanrip emits neither the rows nor the
# `Invoked as:` line they read. Auditing for that found two more — `medium` and
# `log_integrity` — plus `disc_identity`, which spoke but graded a SUCCESS as a
# note and so made `worst` read "note" for a flawless rip.
#
# CLAUDE.md: "Can this check be satisfied by finding nothing? Then give it a
# floor." This is that floor, applied to every registered check at once so the
# next one added cannot be silent either.


@pytest.mark.parametrize("check", rip_audit.CHECKS, ids=lambda c: c.name)
def test_every_check_speaks_for_a_healthy_rip(check, tmp_path: Path) -> None:
    """Each check, run alone against a complete report, must produce a finding."""
    album = rip_audit.AlbumAudit(folder=tmp_path)
    (tmp_path / "01.flac").write_bytes(b"x" * _BIG)
    check.run(_healthy(), album)
    assert album.findings, (
        f"check {check.name!r} ran and said nothing for a healthy rip — "
        f"silence is indistinguishable from 'all in order'"
    )


@pytest.mark.parametrize("check", rip_audit.CHECKS, ids=lambda c: c.name)
def test_every_check_speaks_for_an_empty_report(check, tmp_path: Path) -> None:
    """And for a report with none of the fields it reads — the case that actually
    produced the silence, since a stock-cyanrip rip is a report missing exactly
    the fork-only fields."""
    album = rip_audit.AlbumAudit(folder=tmp_path)
    check.run({}, album)
    assert album.findings, (
        f"check {check.name!r} went silent on a report with nothing in it; it must "
        f"report 'not determined' and why"
    )
    assert all(f.level != LEVEL_OK for f in album.findings), (
        f"check {check.name!r} reported OK for a report containing none of the "
        f"fields it reads"
    )


def test_a_silent_check_is_caught_by_run_checks_itself(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The structural backstop, proven with a deliberately silent check.

    The per-check fixes above are the *good* behaviour; this is what happens when
    a future check forgets. Without it, the guarantee would rest entirely on
    every author remembering — which is the thing that already failed twice.
    """
    silent = rip_audit.Check(
        "deliberately_silent", "Does nothing?", False, lambda report, album: None
    )
    monkeypatch.setattr(rip_audit, "CHECKS", (silent,))
    album = rip_audit.AlbumAudit(folder=tmp_path)
    ran, skipped = rip_audit.run_checks(_healthy(), tmp_path, album)

    assert ran == ["deliberately_silent"]
    assert skipped == []
    assert len(album.findings) == 1
    text = album.findings[0].text
    assert "deliberately_silent" in text
    assert "nothing to report" in text
    assert "not determined" in text  # and it says which way to read that
    assert album.findings[0].level != LEVEL_OK


def test_a_clean_fork_rip_reaches_an_all_ok_verdict(tmp_path: Path) -> None:
    """`worst` has to be able to reach `ok`, or it is not a verdict.

    The first real self_check block read `"worst": "note"` for a rip with nothing
    wrong with it, because one informational check was hard-coded to note level.
    A grade that can never be clean tells the user nothing.
    """
    album = audit_album(_write(tmp_path / "a", _healthy(), flac_sizes=[_BIG, _BIG]))
    assert album.worst == LEVEL_OK, [(f.level, f.text) for f in album.findings]
    # Floor: it reached OK by every check speaking positively, not by an empty
    # findings list.
    assert len(album.findings) >= len(rip_audit.CHECKS)


# --- the multi-pass false alarm (real hardware, 2026-08-03) -------------------


def _report_two_passes(*, first: list[str], last: list[str], invoked: str) -> dict:
    """A report from a rip that spawned the ripper twice.

    The shape a dynamic secure-rerip produces: a whole-disc pass, then a
    targeted `-Z N -l <tracks>` pass over the tracks AccurateRip did not verify.
    """
    return {
        "outcome": {
            "status": "success",
            "ripper_argv": last,
            "ripper_argv_first_pass": first,
        },
        "rip": {"invoked_as": invoked},
    }


def test_argv_agreement_compares_the_first_pass_not_the_last() -> None:
    """THE REGRESSION. A clean 14-track rip whose self-heal re-ripped 2 tracks was
    told *"the command line changed in transit … Something between us altered it"*,
    naming `-Z` and `-l` as injected. Nothing had altered anything: `invoked_as`
    comes from the whole-disc log (the FIRST pass) and `ripper_argv` held the
    auto-fix pass. Comparing them is comparing two different commands.

    A cross-check that accuses the user's system of tampering whenever the
    product's own auto-fix fires is worse than no cross-check — the false alarm
    lands on exactly the rips someone looks at closely.
    """
    first = ["/bin/cyanrip", "-d", "/dev/sr0", "-s", "667", "-o", "flac", "-N"]
    last = [*first, "-Z", "2", "-l", "3,5"]
    report = _report_two_passes(
        first=first,
        last=last,
        invoked="/usr/local/bin/cyanrip -d /dev/sr0 -s 667 -o flac -N",
    )
    album = rip_audit.AlbumAudit(folder=Path("/tmp/x"))
    rip_audit._audit_argv_agreement(report, album)

    texts = [f.text for f in album.findings]
    assert not any(f.level == rip_audit.LEVEL_WARN for f in album.findings), texts
    # And it says which pass it checked, so "the N flags we sent" is not read as
    # covering the auto-fix invocation too.
    assert any("whole-disc pass" in t for t in texts), texts


def test_argv_agreement_still_catches_a_real_mismatch_on_a_multi_pass_rip() -> None:
    """The floor. Fixing the false alarm must not disarm the check: a first pass
    whose flags genuinely differ from what the ripper reports receiving is still a
    warning, even when a second pass exists."""
    first = ["/bin/cyanrip", "-d", "/dev/sr0", "-s", "667", "-N"]
    report = _report_two_passes(
        first=first,
        last=[*first, "-Z", "2"],
        # `-N` vanished in transit — the case the check exists for.
        invoked="/usr/local/bin/cyanrip -d /dev/sr0 -s 667",
    )
    album = rip_audit.AlbumAudit(folder=Path("/tmp/x"))
    rip_audit._audit_argv_agreement(report, album)
    warns = [f.text for f in album.findings if f.level == rip_audit.LEVEL_WARN]
    assert warns, [f.text for f in album.findings]
    assert "-N" in warns[0]


def test_argv_agreement_on_a_single_pass_rip_does_not_mention_a_pass() -> None:
    """No `ripper_argv_first_pass` means one invocation; the message must not
    imply there were several."""
    argv = ["/bin/cyanrip", "-d", "/dev/sr0", "-N"]
    report = {
        "outcome": {"status": "success", "ripper_argv": argv},
        "rip": {"invoked_as": "/usr/local/bin/cyanrip -d /dev/sr0 -N"},
    }
    album = rip_audit.AlbumAudit(folder=Path("/tmp/x"))
    rip_audit._audit_argv_agreement(report, album)
    texts = [f.text for f in album.findings]
    assert not any(f.level == rip_audit.LEVEL_WARN for f in album.findings), texts
    assert not any("pass" in t for t in texts), texts
