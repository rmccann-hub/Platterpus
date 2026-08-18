"""Regression tests for the whole-application audit of 2026-07-28.

Eight parallel reviewers went over typing, security/input validation,
architecture, UX honesty, latent bugs and documentation. Every defect they
confirmed is pinned here, one test per defect, in the order the fixes shipped.
The institutional rule is "every shipped bug gets a regression test in the same
change" (docs/testing.md) — this file is that obligation for the batch.

They are grouped by the *kind* of failure rather than by module, because the
audit's central finding was that the same mistake kept recurring in different
files: **a fact that is true in one place is not true in another** — the
renderer knew, the plumbing didn't; the exporter had the guard, the banner
didn't; the preview sanitised, the argv builder didn't.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

# The one canonical window teardown (see its docstring — a second copy of it
# is how CI segfaulted on 2026-07-28).
from conftest import stop_window_threads
from PySide6.QtWidgets import QApplication

from platterpus.adapters.metaflac import MetaflacAdapter
from platterpus.config import Config
from platterpus.eac_log_export import render_eac_style_log
from platterpus.parsers.rip_log import AccurateRipResult, RipLog, TrackResult
from platterpus.settings_validation import (
    OFFSET_MAX,
    OFFSET_MIN,
    errors_only,
    validate_config,
)
from platterpus.verdict import (
    accuraterip_verdict,
    expected_track_total,
    track_accuraterip_partial,
)


class _NullRunner:
    """The `CommandRunner` protocol, answering "nothing is here" to everything.

    `HostTeardown` only needs it to decide which steps are already done; the
    export-list assertion below is a pure question about its own configuration.
    """

    def which(self, name: str) -> bool:
        return False

    def exists(self, path: Path) -> bool:
        return False

    def run(self, argv: list[str]) -> tuple[int, str]:
        return 0, ""


@pytest.fixture()
def window(qapp: QApplication):
    """A real MainWindow with fake collaborators, torn down after the test.

    Several of these defects live in the *wiring* between the window and a
    renderer or a widget, which is exactly the seam the audit found untested —
    so they have to be driven through the real object, not a stand-in.

    Teardown goes through the shared `stop_window_threads`. The first draft of
    this fixture called `deleteLater()` and joined nothing, so every window it
    made was destroyed with `_mb_thread` still running — which segfaulted CI
    inside an unrelated test file during garbage collection. The lesson is the
    audit's own, applied to itself: a second copy of a teardown is a second
    chance to forget a thread.
    """
    from platterpus.adapters.rip_backend import RipBackend
    from platterpus.deps.manager import DependencyManager
    from platterpus.ui.main_window import MainWindow

    class _Backend(RipBackend):
        name = "fake"

        def list_drives(self, timeout_s: float | None = None) -> list:
            return []

        def disc_info(self, drive: str, timeout_s: float | None = None):
            raise NotImplementedError

        def rip(self, *args: object, **kwargs: object):
            raise NotImplementedError

        def version(self) -> str:
            return "fake 0"

    created = MainWindow(
        config=Config(),
        backend=_Backend(),
        mb_client=SimpleNamespace(),  # type: ignore[arg-type]
        metaflac=MetaflacAdapter(),
        dependency_manager=DependencyManager(specs=[]),
        save_config=lambda _cfg: None,
    )
    yield created
    stop_window_threads(created)
    created.deleteLater()


# --- A claim the measurement does not support --------------------------------


def test_a_track_whose_rereads_disagreed_never_gets_a_test_copy_pair() -> None:
    """The worst finding in the audit: a forged EAC verification pair.

    ``rip_count`` is cyanrip's "(after N rips)" — how many passes it *took*, not
    how many *agreed*. A ``-Z`` run that exhausts its repeat limit without
    converging prints BOTH "no matches found, but hit repeat limit" (→
    ``secure_rerip_converged=False``) and "(after 5 rips)". The old
    ``converged is True or reads >= 2`` short-circuited the measured negative, so
    one SHA-256-attested document asserted the reads were identical *and*, in its
    own status report, that they were not.
    """
    rip_log = RipLog(
        log_creator="cyanrip 0.9.3",
        tracks=(
            TrackResult(
                number=2,
                copy_crc="329DC760",
                rip_count=5,
                secure_rerip_converged=False,
            ),
        ),
    )
    text = render_eac_style_log(rip_log)
    assert "Test CRC" not in text
    assert "Copy CRC 329DC760" in text
    assert "re-reads did NOT agree" in text
    # …and the status report still carries the caveat, so the two agree.
    assert "not confirmed reproducible" in text


def test_an_unmeasured_multi_read_track_still_earns_its_pair() -> None:
    """The other direction — the fix must not lose a proof we did earn.

    ``None`` means "never re-read by the auto-fix"; a rip_count of 2+ there is
    cyanrip's own repeated read agreeing, which is exactly the Test & Copy claim.
    """
    rip_log = RipLog(
        log_creator="cyanrip 0.9.3",
        tracks=(TrackResult(number=1, copy_crc="B0D122E7", rip_count=2),),
    )
    text = render_eac_style_log(rip_log)
    assert "Test CRC B0D122E7" in text
    assert "Copy CRC B0D122E7" in text


# --- A guard that existed in one place and not the other ---------------------


def test_the_verdict_banner_counts_the_disc_not_just_what_reported() -> None:
    """A track that failed outright produced no CRC and no AccurateRip line, so
    it never reached the denominator — and ``verified == total`` went GREEN with
    "all tracks verified" while the status line and the disc panel both said a
    track was missing. The EAC exporter got this guard first; the banner, which
    is the headline the whole trust design rests on, did not."""
    ok = AccurateRipResult(version=2, result="accurately ripped", confidence=200)
    rip_log = RipLog(
        tracks=(
            TrackResult(number=1, copy_crc="AAAA1111", accuraterip_v2=ok),
            TrackResult(number=2, copy_crc="BBBB2222", accuraterip_v2=ok),
            TrackResult(number=3),  # produced nothing at all
        )
    )
    message, level = accuraterip_verdict(rip_log)
    assert level == "warn"
    assert "2 of 3" in message
    assert "1 track produced no result at all" in message
    assert "Bit-perfect" not in message


def test_a_cancelled_rip_never_calls_itself_bit_perfect() -> None:
    """The half of that guard it didn't close, reproduced from the real rig log.

    The 2026-07-28 fix compared against the *log's* track count, which catches a
    track that was ripped and failed (present in the log, no CRC) but not a track
    that was **never ripped** — that one is absent from the log entirely, so both
    sides of the comparison shrink together and `missing` stays 0.

    A cancelled rip is exactly that case. These are the real numbers from the rig
    (2026-07-30): cancel after two tracks of fourteen, both genuinely verified at
    confidence 129/131 and 200 — and the headline read "✓ Bit-perfect: all 2
    tracks verified against AccurateRip (confidence 129+)". Green, over 14% of the
    disc, while the EAC log beside it correctly said "covers 2 of 14 disc tracks".
    """
    v1a = AccurateRipResult(version=1, result="accurately ripped", confidence=129)
    v1b = AccurateRipResult(version=1, result="accurately ripped", confidence=131)
    v2 = AccurateRipResult(version=2, result="accurately ripped", confidence=200)
    rip_log = RipLog(
        log_creator="cyanrip 0.9.3",
        tracks=(
            TrackResult(
                number=1, copy_crc="B0D122E7", accuraterip_v1=v1a, accuraterip_v2=v2
            ),
            TrackResult(
                number=2, copy_crc="985AAE32", accuraterip_v1=v1b, accuraterip_v2=v2
            ),
        ),
    )
    message, level = accuraterip_verdict(
        rip_log, disc_track_total=14, outcome_status="cancelled"
    )
    assert level == "warn", "a 2-of-14 rip must not be green"
    assert "Bit-perfect" not in message
    # The disc's number, not the log's — the whole point of the fix.
    assert "2 of 14" in message
    # And it must say WHY, or the number is a puzzle rather than an explanation.
    assert "cancelled" in message
    assert "12 tracks were never ripped" in message


def test_the_verdict_still_says_bit_perfect_when_every_disc_track_verified() -> None:
    """The guard must not fire just because a disc total was supplied.

    Otherwise "pass a disc total" would silently downgrade every honest rip, and
    the fix would be worse than the bug.
    """
    ok = AccurateRipResult(version=2, result="accurately ripped", confidence=200)
    rip_log = RipLog(
        tracks=tuple(
            TrackResult(number=n, copy_crc=f"{n:08X}", accuraterip_v2=ok)
            for n in range(1, 15)
        )
    )
    message, level = accuraterip_verdict(
        rip_log, disc_track_total=14, outcome_status="success"
    )
    assert level == "ok"
    assert "Bit-perfect: all 14 tracks" in message


def test_the_verdict_falls_back_to_the_logs_count_without_a_disc_total() -> None:
    """No disc total available → the old behaviour, not a crash and not a lie.

    Both new arguments are optional, so any caller that cannot supply them (an
    older caller, `--compare` reading a log off disk) keeps working. The 2026-07-28
    failed-track guard must still fire in that mode.
    """
    ok = AccurateRipResult(version=2, result="accurately ripped", confidence=200)
    rip_log = RipLog(
        tracks=(
            TrackResult(number=1, copy_crc="AAAA1111", accuraterip_v2=ok),
            TrackResult(number=2),  # ripped, produced nothing
        )
    )
    message, level = accuraterip_verdict(rip_log)
    assert level == "warn"
    assert "1 of 2" in message
    assert "1 track produced no result at all" in message


def test_a_genuinely_complete_rip_is_still_allowed_to_say_bit_perfect() -> None:
    ok = AccurateRipResult(version=2, result="accurately ripped", confidence=200)
    rip_log = RipLog(
        tracks=(
            TrackResult(number=1, copy_crc="AAAA1111", accuraterip_v2=ok),
            TrackResult(number=2, copy_crc="BBBB2222", accuraterip_v2=ok),
        )
    )
    message, level = accuraterip_verdict(rip_log)
    assert level == "ok"
    assert message.startswith("✓ Bit-perfect: all 2 tracks")


def test_offset_variant_requires_a_match_not_merely_a_line() -> None:
    """``accuraterip_offset`` is set whenever cyanrip printed an "Accurip 450:"
    line at all — **including** "(not found, either a new pressing, or bad
    rip)". Counting the line's presence made the banner say "matched an
    offset-variant pressing" while the table beside it showed "—"."""
    no_match = AccurateRipResult(version=450, result="not found", confidence=None)
    a_match = AccurateRipResult(version=450, result="accurately ripped", confidence=7)
    assert (
        track_accuraterip_partial(TrackResult(number=1, accuraterip_offset=no_match))
        is False
    )
    assert (
        track_accuraterip_partial(TrackResult(number=2, accuraterip_offset=a_match))
        is True
    )
    # An exactly-verified track is never *also* counted as partial.
    exact = AccurateRipResult(version=2, result="accurately ripped", confidence=99)
    assert (
        track_accuraterip_partial(
            TrackResult(number=3, accuraterip_v2=exact, accuraterip_offset=a_match)
        )
        is False
    )


# --- Validation that failed open ---------------------------------------------


def test_one_bad_field_type_cannot_disarm_every_other_rule() -> None:
    """`validate_config` was one big ``try`` around every check. A hand-edited
    ``config.toml`` with a non-string path made the FIRST rule raise; the single
    ``except`` swallowed it and returned the (empty) issues gathered so far, so
    `Config._sanitized()` read "all good" and persisted a `..`-traversal
    template, an absolute template and an out-of-range offset."""
    config = Config()
    object.__setattr__(config, "library_dir", 5)  # the rule that used to raise
    config.track_template = "../../../../tmp/pwned/%t - %n"
    config.disc_template = "/etc/cron.d/%d"
    config.read_offset = 999_999_999_999

    fields = {issue.field for issue in errors_only(validate_config(config))}
    assert "library_dir" in fields  # the bad type is itself reported…
    assert "track_template" in fields  # …and every later rule still ran
    assert "disc_template" in fields
    assert "read_offset" in fields


@pytest.mark.parametrize(
    "field",
    ["output_dir", "working_dir", "track_template", "disc_template", "metaflac_path"],
)
def test_a_non_string_path_field_is_reported_not_skipped(field: str) -> None:
    """Isolating the rules is only half the fix: a rule that raises and is
    skipped leaves the user with NO error for the one field that is broken."""
    config = Config()
    object.__setattr__(config, field, 12345)
    assert any(issue.field == field for issue in errors_only(validate_config(config)))


def test_an_unmounted_volume_is_a_warning_not_a_config_rewrite(tmp_path) -> None:
    """`_sanitized()` resets every ERROR-level field to its default on load, so
    grading "this folder isn't writable right now" as an error silently
    retargeted a NAS/removable rip library to ~/Music/rips and cleared
    `library_dir` — the user's real paths gone, with only a log line. Not
    mounted is an environmental condition, not an invalid value."""
    if os.geteuid() == 0:
        pytest.skip("root ignores the write bit, so the probe can't be provoked")
    locked = tmp_path / "mnt"
    locked.mkdir()
    locked.chmod(0o500)  # readable, not writable
    try:
        config = Config()
        config.output_dir = str(locked / "rips")
        issues = [i for i in validate_config(config) if i.field == "output_dir"]
        assert issues, "the condition must still be surfaced"
        assert all(not i.is_error() for i in issues)
    finally:
        locked.chmod(0o700)


# --- Values that escaped their boundary --------------------------------------


def test_the_year_token_cannot_escape_the_output_directory() -> None:
    """``%Y`` is the one naming token *Platterpus* substitutes; every other one
    is rendered by cyanrip, which sanitises path separators inside a tag value.
    It took the Year box's text verbatim, so a year of "../." reached
    ``cyanrip -D`` as a real path component and the album was written OUTSIDE the
    output directory — while the Settings preview, which does sanitise, showed
    the safe string."""
    from platterpus.adapters.cyanrip_backend import _year_token

    assert _year_token("1971") == "1971"
    assert _year_token("1971-11-08") == "1971"
    assert _year_token("../.") == ""
    assert _year_token("/etc") == ""
    assert _year_token("..") == ""
    assert _year_token("") == ""
    assert "/" not in _year_token("19/1")


def test_an_absurd_read_offset_is_refused_at_the_single_write_path() -> None:
    """Three sources reach `_set_read_offset_override` — the hand-entered wizard
    value, the auto-detected one, and the AccurateRip lookup overlaid from the
    user-editable drive_offsets.csv (whose parser accepts any unbounded
    ``-?\\d+``). None went through the validator, so a bad offset persisted,
    reached ``cyanrip -s``, and was then silently reset to 0 by the next
    startup — leaving the FOLLOWING session ripping at the wrong offset."""
    from platterpus.ui.main_window_drive import DriveMixin

    saved: list[Config] = []
    window = SimpleNamespace(
        _config=Config(),
        _rip_controls=SimpleNamespace(set_config=lambda _cfg: None),
        _save_config=saved.append,
        _show_offset_rejected=lambda _v: None,
    )
    assert DriveMixin._set_read_offset_override(window, 667) is True
    assert window._config.read_offset == 667
    assert DriveMixin._set_read_offset_override(window, OFFSET_MAX + 1) is False
    assert DriveMixin._set_read_offset_override(window, OFFSET_MIN - 1) is False
    assert DriveMixin._set_read_offset_override(window, "6") is False  # type: ignore[arg-type]
    assert window._config.read_offset == 667  # the good value survived
    assert len(saved) == 1  # only the accepted write persisted


def test_the_drive_wizard_spin_box_uses_the_validator_bounds() -> None:
    """A widget range that disagrees with the pure validator is a second,
    silently-different rule for the same field (it was hardcoded to ±2000)."""
    import inspect

    from platterpus.ui import drive_setup_dialog

    source = inspect.getsource(drive_setup_dialog)
    assert "setRange(OFFSET_MIN, OFFSET_MAX)" in source
    assert "setRange(-2000, 2000)" not in source


# --- Contracts that raised despite promising not to --------------------------


def test_a_corrupt_drive_profile_cache_cannot_lock_the_user_out(tmp_path) -> None:
    """``UnicodeDecodeError`` subclasses ``ValueError``, not ``OSError``, so one
    non-UTF-8 byte escaped five documented "never raises" contracts. This one is
    called from ``MainWindow.__init__`` — a corrupt cache meant the app refused
    to start at all."""
    from platterpus.drive_profile_store import DriveProfileStore

    path = tmp_path / "drive_profiles.json"
    path.write_bytes(b'{"profiles": [], "note": "\xff\xfe not utf-8"}')
    store = DriveProfileStore.load(path)  # must not raise
    assert store._path == path


@pytest.mark.parametrize(
    "module_name,func_name",
    [
        ("platterpus.offset_config", "_read_conf_text"),
        ("platterpus.adapters.accuraterip_offsets", "_load_user_csv"),
        ("platterpus.deps.host_setup", "_os_release_ids"),
    ],
)
def test_the_other_external_file_readers_survive_bad_bytes(
    tmp_path, module_name: str, func_name: str
) -> None:
    import importlib

    path = tmp_path / "external.txt"
    path.write_bytes(b"key=value\n\xff\xfe\n")
    func = getattr(importlib.import_module(module_name), func_name)
    func(path)  # must not raise


def test_appimage_integration_survives_a_mangled_desktop_file(tmp_path) -> None:
    from platterpus import appimage_integration

    desktop_dir = tmp_path / "applications"
    desktop_dir.mkdir()
    target = appimage_integration._desktop_file(desktop_dir)
    target.write_bytes(b"[Desktop Entry]\nExec=\xff\xfe\n")
    assert (
        appimage_integration.is_integrated(tmp_path / "x.AppImage", desktop_dir)
        is False
    )


# --- Records that described the wrong album ----------------------------------


def test_embed_only_cover_art_never_touches_an_existing_cover_file(tmp_path) -> None:
    """metaflac imports a picture from a FILE, so the image always lands on disk
    — but the scratch write reused the canonical library name ``cover.jpg`` and
    then deleted it. Embed-without-save is the DEFAULT, so the default setting
    destroyed a cover the user had placed in the album folder."""
    from platterpus.adapters import cover_art

    keep = b"\xff\xd8\xffORIGINAL-USER-COVER"
    (tmp_path / "cover.jpg").write_bytes(keep)
    chosen = tmp_path / "chosen.jpg"
    chosen.write_bytes(b"\xff\xd8\xffNEW-ART-FROM-DISK")

    cover_art.apply_local_cover_art(
        tmp_path, chosen, embed=True, save_file=False, metaflac=MetaflacAdapter()
    )

    assert (tmp_path / "cover.jpg").read_bytes() == keep
    # …and the scratch file it used instead is cleaned up.
    assert not list(tmp_path.glob(".platterpus-cover-tmp*"))


def test_saving_the_cover_still_writes_the_canonical_name(tmp_path) -> None:
    from platterpus.adapters import cover_art

    chosen = tmp_path / "chosen.jpg"
    chosen.write_bytes(b"\xff\xd8\xffART")
    result = cover_art.apply_local_cover_art(
        tmp_path, chosen, embed=False, save_file=True, metaflac=MetaflacAdapter()
    )
    assert (tmp_path / "cover.jpg").exists()
    assert result.saved_as == "cover.jpg"


# --- Facts the report or the log never carried -------------------------------


def test_a_rip_nothing_could_verify_says_so_in_the_report() -> None:
    """`issues: []` beside a docstring reading "empty on a clean rip" told a
    triager "clean" for a rip with no independent verification whatsoever."""
    from platterpus.rip_report import _issues

    issues = _issues(
        # `ripper_exit_code: 0` is what a real success carries. Omit it and the
        # report now (correctly) raises `ripper_exit_unknown` — a success resting
        # on the log alone — which would mask the ONE signal this test isolates.
        outcome={"status": "success", "ripper_exit_code": 0},
        verdict_level="neutral",
        ctdb=None,
        flac_integrity=None,
        derived=None,
        transcode=None,
        cover_art=None,
        read_speed=None,
    )
    assert [i["code"] for i in issues] == ["unverified"]
    assert issues[0]["severity"] == "info"


def test_a_validated_ctdb_no_match_reaches_the_issues_list() -> None:
    """`ctdb` was a parameter of `_issues` that the body never read, so the one
    whole-disc cross-check contributed nothing while every other verification
    sub-block did."""
    from platterpus.rip_report import _issues

    issues = _issues(
        outcome={"status": "success", "ripper_exit_code": 0},
        verdict_level="ok",
        ctdb={"verdict": "no_match", "crc_validated": True},
        flac_integrity=None,
        derived=None,
        transcode=None,
        cover_art=None,
        read_speed=None,
    )
    assert [i["code"] for i in issues] == ["ctdb_no_match"]


def test_an_unvalidated_ctdb_no_match_stays_quiet() -> None:
    from platterpus.rip_report import _issues

    assert (
        _issues(
            outcome={"status": "success", "ripper_exit_code": 0},
            verdict_level="ok",
            ctdb={"verdict": "no_match", "crc_validated": False},
            flac_integrity=None,
            derived=None,
            transcode=None,
            cover_art=None,
            read_speed=None,
        )
        == []
    )


# --- Wiring that never carried the value it was written for ------------------


def test_the_incomplete_rip_banner_survives_the_trip_through_the_window(
    window, tmp_path
) -> None:
    """`_last_outcome` is the DICT `rip_report.build_outcome()` returns, and a
    dict does not expose its keys as attributes — so ``getattr(outcome,
    "status", "")`` was always "" and the INCOMPLETE RIP banner could never
    render on a real rip. The renderer half was correct and directly tested; the
    plumbing half shipped broken in v0.5.11. This test goes through
    `_write_eac_log`, which is where the seam actually is."""
    window._config.write_eac_log_after_rip = True
    window._current_num_tracks = 14
    window._last_outcome = {"status": "cancelled"}

    log_file = tmp_path / "The Police - Album.log"
    log_file.write_text("cyanrip log", encoding="utf-8")
    window._write_eac_log(
        RipLog(log_creator="cyanrip 0.9.3", tracks=(TrackResult(number=1),)), log_file
    )

    text = (tmp_path / "The Police - Album (EAC-compatible).log").read_text(
        encoding="utf-8"
    )
    assert "INCOMPLETE RIP (cancelled)" in text
    assert "1 of 14" in text


def test_the_desktop_notification_sends_what_the_window_shows(window) -> None:
    """The notification took a local `status` captured BEFORE the read-stability
    summary overwrote the on-screen line, so the unattended user — its entire
    audience — was told "all tracks ripped cleanly" while the window warned that
    a track never read reproducibly."""
    window._rip_progress.set_status("⚠ Read stability: track 3 did not reproduce")
    assert (
        window._rip_progress.current_status()
        == "⚠ Read stability: track 3 did not reproduce"
    )


def test_a_post_rip_failure_downgrades_the_green_trust_banner(window) -> None:
    """The banner is written once, from the AccurateRip parse, and never heard
    about anything that failed afterwards — so `flac --test` could fail on two
    masters under a green "✓ Bit-perfect" headline."""
    ok = AccurateRipResult(version=2, result="accurately ripped", confidence=200)
    window._rip_progress.set_rip_log(
        RipLog(tracks=(TrackResult(number=1, copy_crc="AAAA1111", accuraterip_v2=ok),))
    )
    banner = window._rip_progress._verdict_banner
    assert banner.text().startswith("✓ Bit-perfect")

    window._rip_progress.downgrade_verdict("1 FLAC master(s) failed the decode check")
    assert not banner.text().startswith("✓")
    assert banner.text().startswith("⚠")
    assert "failed the decode check" in banner.text()

    # Idempotent: the same reason never stacks.
    before = banner.text()
    window._rip_progress.downgrade_verdict("1 FLAC master(s) failed the decode check")
    assert banner.text() == before


def test_a_recorded_downgrade_survives_a_later_log_parse(window) -> None:
    """A second `set_rip_log` must not wipe a downgrade the user was already shown.

    Same failure as the test above, one layer down: the banner is one sentence
    assembled from the log's verdict *and* the accumulated downgrade reasons, and
    it was assembled in two places — so whichever ran last won. `set_rip_log`
    carried a comment promising it re-applied recorded downgrades; nothing did.

    The old code passed the test above only because `set_rip_log` happens to run
    exactly once per `clear()` today. That is an accident of ordering, not a
    guarantee — and the consequence of losing it is the exact thing this screen
    exists to prevent: a green "✓ Bit-perfect" over a master that will not decode.

    Worse, the dedup guard turned the loss permanent. Re-reporting the *same*
    reason after the second parse returned early ("already recorded"), so the
    banner stayed green for good. Both halves are asserted below.
    """
    progress = window._rip_progress
    banner = progress._verdict_banner
    ok = AccurateRipResult(version=2, result="accurately ripped", confidence=200)
    parsed = RipLog(
        tracks=(TrackResult(number=1, copy_crc="AAAA1111", accuraterip_v2=ok),)
    )

    progress.set_rip_log(parsed)
    progress.downgrade_verdict("1 FLAC master(s) failed the decode check")
    assert "failed the decode check" in banner.text()

    # The log gets re-parsed (a re-rip, a report re-write) with no new downgrade.
    progress.set_rip_log(parsed)
    assert not banner.text().startswith("✓"), (
        "a fresh log parse restored the green tick over a FLAC master that failed "
        "its decode check — the downgrade was dropped, not superseded"
    )
    assert "failed the decode check" in banner.text()

    # And the second half: re-reporting the same failure is still reflected,
    # rather than swallowed as a duplicate of a reason no longer on screen.
    progress.downgrade_verdict("1 FLAC master(s) failed the decode check")
    assert "failed the decode check" in banner.text()


# --- Environment assumptions that only hold on the developer's machine -------


def test_container_exported_tools_resolve_off_a_desktop_launcher_path(
    tmp_path, monkeypatch
) -> None:
    """A GUI started from a desktop icon does not inherit a login shell's PATH,
    and ``~/.local/bin`` — where `distrobox-export` puts the container's tools —
    is exactly the entry that goes missing. The wizard checked the file directly
    and reported success while the dependency probe resolved a bare name through
    PATH and reported it missing."""
    from platterpus import tool_paths

    fake_home_bin = tmp_path / ".local" / "bin"
    fake_home_bin.mkdir(parents=True)
    (fake_home_bin / "flac").write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setattr(
        tool_paths, "_FALLBACK_DIRS", (str(fake_home_bin),), raising=True
    )
    monkeypatch.setattr(tool_paths.shutil, "which", lambda _n: None)

    assert tool_paths.resolve_tool("flac") == str(fake_home_bin / "flac")
    # Unresolvable → the bare name, so no error path changes.
    assert tool_paths.resolve_tool("definitely-not-installed") == (
        "definitely-not-installed"
    )


def test_uninstall_removes_every_binary_setup_exported() -> None:
    """`flac` was omitted once and `~/.local/bin/flac` was orphaned (#34); the
    docstring memorialising that bug was then falsified by adding `cd-paranoia`
    to setup and not to teardown."""
    import inspect

    from platterpus.deps import host_setup, host_teardown

    exported = {"cyanrip", "metaflac", "flac", "cd-paranoia"}
    setup_source = inspect.getsource(host_setup)
    for name in exported:
        assert f"/usr/bin/{name}" in setup_source, name

    engine = host_teardown.HostTeardown(runner=_NullRunner())
    removed = {p.name for p in engine._export_files()}
    assert exported <= removed


def test_uninstall_script_removes_the_same_set() -> None:
    line = next(
        ln
        for ln in Path("uninstall.sh").read_text(encoding="utf-8").splitlines()
        if ln.strip().startswith("for bin in ")
    )
    for name in ("cyanrip", "metaflac", "flac", "cd-paranoia"):
        assert name in line, name


# --- The type gate itself ----------------------------------------------------


def test_mypy_cannot_silently_lose_its_view_of_pyside6() -> None:
    """A global ``ignore_missing_imports`` meant an unresolvable PySide6 turned
    every Qt class into ``Any`` — the whole UI layer went unchecked and mypy
    still printed "Success". Only the one genuinely stub-less dependency (and
    the build-generated ``_build`` module) may be ignored, per module."""
    import tomllib

    with Path("pyproject.toml").open("rb") as handle:
        config = tomllib.load(handle)
    mypy = config["tool"]["mypy"]
    assert "ignore_missing_imports" not in mypy
    assert mypy["disallow_subclassing_any"] is True  # the tripwire
    ignored = {
        override["module"]
        for override in mypy["overrides"]
        if override.get("ignore_missing_imports")
    }
    assert ignored == {"musicbrainzngs.*", "platterpus._build"}


# --- Progress that never finished --------------------------------------------


def test_a_successful_rip_leaves_the_overall_bar_at_100(window) -> None:
    """`_overall_from_track` caps at 95% by design — the last 5% was reserved
    for a whipper-only "length" phase cyanrip never emits. On the only supported
    backend the bar therefore froze at 95% under a status line reading "Done"."""
    window._rip_progress.set_progress(95.0, 100.0)
    window._rip_progress.set_progress(100.0, 100.0)
    assert window._rip_progress._overall_bar.value() == 100


# --- Strings that pointed at something that does not exist -------------------


def test_no_user_facing_string_still_offers_the_removed_whipper_backend() -> None:
    """cyanrip is the only backend (KDD-18); "switch to the cyanrip backend in
    Settings" offered a remedy that has no control behind it."""
    from platterpus.ui import main_window

    source = Path(main_window.__file__).read_text(encoding="utf-8")
    assert "switch to the cyanrip backend" not in source


def test_the_guide_and_the_tooltip_agree_that_ctdb_is_on_by_default() -> None:
    """Both places a user would check said CTDB verification was off. It is on —
    so every rip sends the disc's TOC to an external service by default, and the
    documentation said it didn't."""
    from platterpus.help_content import USER_GUIDE

    assert Config().ctdb_verify_after_rip is True
    # The bullet wraps over several lines, so take everything up to the next one.
    start = USER_GUIDE.index("- **Verify with CTDB after a rip**")
    end = USER_GUIDE.index("\n- ", start)
    bullet = USER_GUIDE[start:end]
    assert "On by default" in bullet
    assert "off by default" not in bullet.lower()


def test_the_ctdb_no_match_line_claims_only_the_alignment_it_tested() -> None:
    """We compute one checksum at the standard alignment; CTDB sweeps ±5879
    because offset-shifted pressings are routine. "This rip differs from the
    database" was a positive inaccuracy claim from 1 of ~11,759 alignments."""
    from platterpus.ctdb.verify import CtdbVerifyResult, Verdict
    from platterpus.ui.rip_progress import ctdb_verdict_line

    line = ctdb_verdict_line(CtdbVerifyResult(Verdict.NO_MATCH, crc_validated=True))
    assert "standard alignment" in line
    assert "differs" not in line


def test_the_goal_preset_moves_every_checkbox_its_summary_describes(qapp) -> None:
    """Switching the goal preset moved every dependent control except "Verify
    FLAC after the rip", so the summary line described a setting the preset had
    not applied."""
    from platterpus import goal_presets
    from platterpus.ui.settings_dialog import SettingsDialog

    dialog = SettingsDialog(Config(), None)
    try:
        for name, preset in goal_presets.PRESETS.items():
            index = dialog._goal_combo.findData(name)
            assert index >= 0, name
            dialog._goal_combo.setCurrentIndex(index)
            assert (
                dialog._verify_flac_check.isChecked() == preset.verify_flac_after_rip
            ), name
            # …and the combo must still read as that preset, not bounce to
            # Custom — the round-trip `detect_goal` does on the next open.
            assert dialog._goal_combo.currentData() == name
    finally:
        dialog.deleteLater()


def test_the_json_report_round_trips_the_new_issue_codes(tmp_path) -> None:
    """A cheap end-to-end: the codes added above must survive serialization."""
    from platterpus.rip_report import write_report

    log_file = tmp_path / "album.log"
    log_file.write_text("cyanrip log", encoding="utf-8")
    write_report(
        RipLog(tracks=(TrackResult(number=1, copy_crc="AAAA1111"),)),
        log_file,
    )
    report = json.loads(
        (tmp_path / "album.platterpus.json").read_text(encoding="utf-8")
    )
    assert "unverified" in {issue["code"] for issue in report["issues"]}


def test_an_interrupted_securing_pass_is_declared_in_the_durable_log() -> None:
    """The `interrupted` flag reached the JSON report and stopped there.

    The durable, checksum-attested log — the artifact a stranger reads years
    later — said nothing, so of the two records for one rip the archival one was
    the more reassuring. `tests/test_surface_consistency.py` states the rule in
    its own docstring: when you add a fact a surface can report, add the
    agreement it owes the others.
    """
    rip_log = RipLog(
        log_creator="cyanrip 0.9.3",
        tracks=(TrackResult(number=1, copy_crc="AAAA1111"),),
    )
    text = render_eac_style_log(
        rip_log, secure_rerip={"engaged": True, "interrupted": True}
    )
    assert "the securing pass was INTERRUPTED" in text
    # It sits inside the status report, above the checksum, so it can't be
    # stripped without invalidating the log.
    assert text.index("INTERRUPTED") < text.index("Platterpus log checksum")


def test_a_completed_securing_pass_adds_no_interruption_line() -> None:
    rip_log = RipLog(
        log_creator="cyanrip 0.9.3",
        tracks=(TrackResult(number=1, copy_crc="AAAA1111"),),
    )
    for report in ({"engaged": True, "interrupted": False}, {}, None, "nonsense"):
        text = render_eac_style_log(rip_log, secure_rerip=report)  # type: ignore[arg-type]
        assert "INTERRUPTED" not in text


def test_a_failed_test_run_still_reports_which_test_failed() -> None:
    """`conftest`'s `os._exit` workaround for a PySide teardown race discarded
    pytest's entire terminal summary — a red CI run produced progress dots and
    nothing else: no failing test names, no tracebacks, no `--durations`. The
    hook now prints the summary itself before exiting."""
    source = Path("tests/conftest.py").read_text(encoding="utf-8")
    hook = source[source.index("def pytest_sessionfinish") :]
    for call in ("summary_failures()", "short_test_summary()", "summary_stats()"):
        assert call in hook, call
    assert hook.index("short_test_summary()") < hook.index("os._exit(status)")


def test_the_window_fixture_leaves_no_running_qthread(window) -> None:
    """The fixture's own contract, asserted rather than assumed.

    CI segfaulted on 2026-07-28 because this file's first window fixture called
    `deleteLater()` and joined nothing: every window it made was destroyed with
    `_mb_thread` still running, and Qt aborted the process during a *later*
    test's garbage collection — inside `test_ui_auto_center.py`, which had
    nothing to do with it. Nothing in the suite asserted the invariant, so the
    only symptom was a crash in an unrelated file.

    This runs the shared teardown against a live window and checks the result
    directly, so a future fixture that forgets a newly-added thread fails here
    instead of segfaulting somewhere else.
    """
    from conftest import stop_window_threads

    names = (
        "_mb_thread",
        "_dep_check_thread",
        "_disc_info_thread",
        "_drive_list_thread",
    )
    # Sanity: the window really does own a running thread, or this proves nothing.
    assert any(
        getattr(window, n, None) is not None and getattr(window, n).isRunning()
        for n in names
    ), "no thread was running — this test can no longer detect a missed join"

    stop_window_threads(window)

    still_running = [
        n
        for n in names
        if getattr(window, n, None) is not None and getattr(window, n).isRunning()
    ]
    assert not still_running, f"destroying the window would abort: {still_running}"


def test_the_window_teardown_has_exactly_one_implementation() -> None:
    """A second copy of the joins is a second chance to forget a thread.

    Both window fixtures (this file's and `test_ui_main_window`'s) must call the
    shared helper rather than inline their own loop — the duplicate is what
    allowed the divergence in the first place.
    """
    for rel in ("tests/test_ui_main_window.py", "tests/test_audit_regressions.py"):
        source = Path(rel).read_text(encoding="utf-8")
        assert "stop_window_threads" in source, rel
        # The tell-tale of a re-inlined copy. Built from pieces so this test's
        # own source doesn't match the pattern it is looking for.
        inlined = "_mb_thread" + ".quit()"
        assert inlined not in source, (
            f"{rel} re-inlined the teardown instead of calling the shared helper"
        )


def test_the_rip_complete_notification_path_does_not_raise(window) -> None:
    """A type-only declaration is not an initialisation.

    v0.5.12 changed `_ensure_tray_icon` from `getattr(self, "_tray_icon", None)`
    to a plain attribute read, to satisfy mypy's `warn_return_any`, and declared
    `_tray_icon` on `MainWindowShared`. But that seam's declarations live under
    `if TYPE_CHECKING:` — they inform the type checker and create nothing at
    runtime. The read came before the only assignment, so **every** completed rip
    raised `AttributeError` and the desktop notification silently never fired.
    Found on real hardware, in the log of an otherwise perfect 14/14 rip
    (2026-07-28).

    The existing notification test passed throughout, because it stubbed
    `_ensure_tray_icon` instead of calling it — the same "test one layer below the
    layer that broke" shape this file was created for.
    """
    # The attribute must EXIST before anything reads it.
    assert hasattr(window, "_tray_icon")
    assert window._tray_icon is None

    # And the real path must be callable without raising. Headless CI has no
    # system tray, so None is the expected answer — the point is that asking is
    # safe.
    assert window._ensure_tray_icon() is None

    # Drive the notification exactly as `_on_rip_finished` does. It is
    # best-effort and swallows its own errors, so assert on the *log* instead:
    # nothing may be recorded as a failure.
    import logging

    records: list[logging.LogRecord] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    logger = logging.getLogger("platterpus.ui.main_window_rip")
    handler = _Capture()
    logger.addHandler(handler)
    try:
        window._rip_cancelled = False
        window._config.notify_on_completion = True
        window._notify_rip_complete(True, "Done — all 14 tracks ripped cleanly.")
    finally:
        logger.removeHandler(handler)

    assert not [r for r in records if r.exc_info], (
        "the notification path logged an exception: "
        f"{[r.getMessage() for r in records if r.exc_info]}"
    )


def test_every_notification_outcome_is_recorded_in_the_log(window) -> None:
    """ "Did the notification fire?" must be answerable from log.txt alone.

    A desktop toast lives for eight seconds and leaves no trace. The first
    hardware test of the v0.5.13 notification fix was inconclusive for exactly
    that reason — the maintainer was away from the screen when the rip finished,
    and the log recorded nothing either way, so a shipped fix could not be
    confirmed or refuted. Every branch of `_notify_rip_complete` therefore states
    its outcome at INFO: posted, or skipped and why.
    """
    import logging

    records: list[logging.LogRecord] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    logger = logging.getLogger("platterpus.ui.main_window_rip")
    handler = _Capture()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    def messages_for(cancelled: bool, enabled: bool) -> list[str]:
        records.clear()
        window._rip_cancelled = cancelled
        window._config.notify_on_completion = enabled
        window._notify_rip_complete(True, "Done — all 14 tracks ripped cleanly.")
        return [r.getMessage() for r in records]

    try:
        # Turned off in Settings, and cancelled, are both legitimate reasons to
        # stay silent on screen — but not reasons to stay silent in the log.
        assert any("turned off in Settings" in m for m in messages_for(False, False))
        assert any("cancelled" in m for m in messages_for(True, True))

        # The real path. Headless CI has no system tray, so the honest outcome
        # there is the "nowhere to post it" branch; on a desktop it is "posted".
        # Either is fine — what must never happen is nothing at all.
        said = messages_for(False, True)
        assert any(("posted" in m) or ("no usable system tray" in m) for m in said), (
            f"the notification path recorded no outcome at all: {said}"
        )
    finally:
        logger.removeHandler(handler)


def test_every_shared_seam_attribute_the_code_reads_is_initialised() -> None:
    """The general form of the bug above, as a fitness test.

    `MainWindowShared` declares the window's shared surface for mypy under
    `if TYPE_CHECKING:`. Those declarations are free — and therefore create
    nothing. Any attribute the code *reads* before assigning must also be
    initialised in `MainWindow.__init__`.

    Rather than try to prove that for all ~60 declared attributes (many are
    legitimately assigned on first use by the code path that owns them), this
    pins the specific shape that bit us: an attribute read with plain dot access
    inside a `_ensure_*`/`_maybe_*` lazy-initialiser must be initialised in
    `__init__`.
    """
    init = Path("src/platterpus/ui/main_window.py").read_text(encoding="utf-8")
    rip = Path("src/platterpus/ui/main_window_rip.py").read_text(encoding="utf-8")

    # The lazy tray-icon initialiser reads it plainly…
    assert "existing = self._tray_icon" in rip
    # …so __init__ must create it.
    assert "self._tray_icon: QSystemTrayIcon | None = None" in init


# --- the concept whose absence caused four repeats of one bug ---------------


def test_a_deliberate_partial_rip_is_complete_not_a_warning() -> None:
    """The false alarm the *previous* fix introduced, hours after shipping.

    Fixing the cancelled-rip verdict meant handing it the disc's track count. But
    the Rip? column exists so a user can deliberately rip a subset — and against
    the disc's count, a successful, intentional 2-of-14 rip then read
    "⚠ 2 of 14 tracks verified — 12 tracks were never ripped". The user's own
    choice, reported as a fault.

    `expected_track_total` is the missing concept: the number the rip was ASKED
    for. A complete rip of a selection is COMPLETE.
    """
    ok = AccurateRipResult(version=2, result="accurately ripped", confidence=200)
    rip_log = RipLog(
        tracks=(
            TrackResult(number=1, copy_crc="B0D122E7", accuraterip_v2=ok),
            TrackResult(number=2, copy_crc="985AAE32", accuraterip_v2=ok),
        )
    )
    # The user ticked only tracks 1 and 2 of a 14-track disc.
    expected = expected_track_total(14, (1, 2))
    assert expected == 2, "a deliberate selection is what the rip was asked for"

    message, level = accuraterip_verdict(
        rip_log, disc_track_total=expected, outcome_status="success"
    )
    assert level == "ok", "a complete rip of a selection is not a warning"
    assert "never ripped" not in message
    assert "Bit-perfect: all 2 tracks" in message


def test_a_cancelled_subset_rip_still_warns_about_what_it_missed() -> None:
    """The other side, so the fix is not simply 'never warn about a subset'.

    Ask for four tracks, get two because you cancelled: that IS incomplete, and it
    must still say so — measured against the four requested, not the fourteen on
    the disc.
    """
    ok = AccurateRipResult(version=2, result="accurately ripped", confidence=200)
    rip_log = RipLog(
        tracks=(
            TrackResult(number=1, copy_crc="B0D122E7", accuraterip_v2=ok),
            TrackResult(number=2, copy_crc="985AAE32", accuraterip_v2=ok),
        )
    )
    expected = expected_track_total(14, (1, 2, 3, 4))
    assert expected == 4

    message, level = accuraterip_verdict(
        rip_log, disc_track_total=expected, outcome_status="cancelled"
    )
    assert level == "warn"
    assert "2 of 4" in message, "measured against what was REQUESTED, not the disc"
    assert "cancelled" in message


def test_expected_track_total_falls_back_to_the_disc_then_to_unknown() -> None:
    """No selection → the disc. No disc count either → unknown, which callers
    already handle by falling back to the log's own count."""
    assert expected_track_total(14, ()) == 14
    assert expected_track_total(14, None) == 14
    assert expected_track_total(None, ()) is None
    assert expected_track_total(0, ()) is None


# --- the same denominator, a fourth time, in the attested document ----------


_RIG_CANCELLED_2_OF_14 = """cyanrip 0.9.3 (release)
System device:  /dev/sr0
Device model:   PIONEER  BD-RW   BDR-209D 1.51 SCSI CD-ROM
Offset:         +667 samples
Disc tracks:    14
Album:          Every Breath You Take: The Classics
Album artist:   The Police
AccurateRip:    found

Tracks:
Track 1 ripped and encoded successfully!
Summary:

  Properties:
    Start LSN:   0 (with offset: 1)
    End LSN:     14486 (with offset: 14488)

  EAC CRC32:     B0D122E7
  Accurip:       disc found in database (max confidence: 200)
    Accurip v1:  5D3C90CB (accurately ripped, confidence 129)
    Accurip v2:  22B9924D (accurately ripped, confidence 200)

Track 2 ripped and encoded successfully!
Summary:

  Properties:
    Start LSN:   14487 (with offset: 14488)
    End LSN:     28066 (with offset: 28068)

  EAC CRC32:     985AAE32
  Accurip:       disc found in database (max confidence: 200)
    Accurip v1:  A3019EB3 (accurately ripped, confidence 131)
    Accurip v2:  31C28378 (accurately ripped, confidence 200)
"""


def test_the_attested_log_cannot_say_incomplete_at_the_top_and_all_at_the_bottom() -> (
    None
):
    """Two contradictory claims in one SHA-256-signed document, off the rig.

    Real artifact, 2026-08-01: a rip cancelled after two tracks of fourteen. Line
    10 said ``*** INCOMPLETE RIP (cancelled) — this log covers 2 of 14 disc
    tracks. ***``; line 68, in the status report, said ``All tracks accurately
    ripped``. Both signed by the same checksum. The banner and the verdict had
    already been fixed for exactly this case — the status report had not, because
    it computed its own denominator instead of being handed one.

    `clean_sweep` compared the AccurateRip total against ``len(rip_log.tracks)``:
    the LOG's track list, which a cancel shrinks. A cancel cannot shrink the disc.
    This is the fourth appearance of that denominator (see the three tests above);
    the concept that fixes it — `expected_track_total`, the number the rip was
    ASKED for — already existed and simply wasn't threaded this far.
    """
    from platterpus.parsers.cyanrip_log import parse_cyanrip_log

    rip_log = parse_cyanrip_log(_RIG_CANCELLED_2_OF_14)
    assert len(rip_log.tracks) == 2, "the log itself only carries the two ripped"

    text = render_eac_style_log(
        rip_log, outcome_status="cancelled", disc_track_total=14
    )

    # The banner is the claim we trust; the summary must not contradict it.
    assert "INCOMPLETE RIP (cancelled)" in text
    assert "2 of 14" in text
    assert "All tracks accurately ripped" not in text
    assert "Some tracks could not be verified as accurate" in text
    # The per-count line is still honest about what DID verify — the fix must not
    # turn a truthful count into a pessimistic one.
    assert "2 track(s) accurately ripped" in text


def test_a_complete_rip_still_gets_its_clean_sweep_sentence() -> None:
    """The other side: supplying a disc total must not condemn an honest rip.

    Same failure mode as the verdict fix's companion test — if the guard fired
    merely because a denominator was passed, every complete rip would lose its
    "All tracks accurately ripped" line and the fix would be worse than the bug.
    """
    ok = AccurateRipResult(version=2, result="accurately ripped", confidence=200)
    rip_log = RipLog(
        log_creator="cyanrip 0.9.3",
        tracks=tuple(
            TrackResult(number=n, copy_crc=f"{n:08X}", accuraterip_v2=ok)
            for n in range(1, 15)
        ),
    )
    text = render_eac_style_log(rip_log, outcome_status="success", disc_track_total=14)
    assert "All tracks accurately ripped" in text
    assert "INCOMPLETE RIP" not in text


def test_a_deliberate_subset_rip_is_a_clean_sweep_of_what_was_asked() -> None:
    """A user who ticks two of fourteen and gets both has a complete rip.

    `expected_track_total` is what the caller threads in, so the status report
    measures against the REQUEST, not the disc — the same false-alarm the verdict
    fix had to walk back hours after shipping. Pinned here so the log surface
    can't repeat it.
    """
    ok = AccurateRipResult(version=2, result="accurately ripped", confidence=200)
    rip_log = RipLog(
        log_creator="cyanrip 0.9.3",
        tracks=(
            TrackResult(number=1, copy_crc="B0D122E7", accuraterip_v2=ok),
            TrackResult(number=2, copy_crc="985AAE32", accuraterip_v2=ok),
        ),
    )
    text = render_eac_style_log(
        rip_log,
        outcome_status="success",
        disc_track_total=expected_track_total(14, (1, 2)),
    )
    assert "All tracks accurately ripped" in text
    assert "INCOMPLETE RIP" not in text


def test_open_logs_folder_still_reports_a_refusal_through_the_shared_helper(
    window, monkeypatch
) -> None:
    """The one openUrl call site that was already right must survive the move.

    Help → Open logs folder had always checked the bool and shown the path when
    the desktop declined. That behaviour lived inline, which is why the rip
    pane's two buttons and the viewer's "Open externally…" never got it — the
    §5.o shape again: a rule enforced where it was learned and nowhere else. It
    is now `ui/external_open.open_path_externally`, shared by all four. This
    pins the original site's behaviour across that move; the other three are in
    `tests/test_ui_external_open.py`.
    """
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import QMessageBox

    bodies: list[str] = []
    monkeypatch.setattr(QDesktopServices, "openUrl", staticmethod(lambda _url: False))
    monkeypatch.setattr(
        QMessageBox,
        "information",
        lambda _parent, _title, text, *a: bodies.append(text),
    )

    window._on_open_logs_folder()

    assert len(bodies) == 1, "a refused open must not be silent"
    assert "platterpus" in bodies[0].lower(), "the user must be given the path"


def test_the_mypy_opt_out_list_is_a_ratchet_that_only_shrinks() -> None:
    """CLAUDE.md rule #10: *"retire one opt-out per commit, never add one."*

    **The rule was written and nothing enforced it.** Found by the 2026-08-18
    enforcement audit, which asked of every "enforced by" claim in ``CLAUDE.md`` what
    actually enforces it. This one was prose: the list could grow, and growing it is
    exactly what a module under deadline pressure invites — the opt-out is one line and
    the type work is not.

    A ratchet rather than an exact match, so retiring an entry needs no test edit while
    adding one is a deliberate, visible act. When the list shrinks, lower ``CEILING``
    in the same commit; the assertion below refuses to let it drift upward silently.

    Deliberately keyed on the **module names**, not just the count: swapping one module
    for another keeps the count and changes what is unchecked.
    """
    import tomllib

    #: The opt-out set as of 2026-08-18. **May shrink. May never grow.**
    CEILING: frozenset[str] = frozenset(
        {
            "platterpus.rip_report",
            "platterpus.rip_compare",
            "platterpus.adapters.musicbrainz_client",
            "platterpus.ui.main_window_shared",
            "platterpus.ui.main_window",
            "platterpus.workers.rip_worker",
            "platterpus.read_speed_ladder",
            "platterpus.config",
            "platterpus.ui.main_window_rip",
        }
    )

    # Resolved from this file, not from the cwd: the sibling check at
    # `test_mypy_cannot_silently_lose_its_view_of_pyside6` uses a bare relative path,
    # which works only because pytest happens to run from the repo root.
    from pathlib import Path as _Path

    repo_root = _Path(__file__).resolve().parents[1]
    with (repo_root / "pyproject.toml").open("rb") as handle:
        config = tomllib.load(handle)

    relaxed: set[str] = set()
    for override in config["tool"]["mypy"]["overrides"]:
        modules = override.get("module")
        names = [modules] if isinstance(modules, str) else list(modules or [])
        # Only the strictness opt-outs count. `ignore_missing_imports` on a THIRD-PARTY
        # module is a different thing — it says "this dependency ships no stubs", which
        # is a fact about them, not a relaxation of our own checking. Rule #10's ratchet
        # is about ours.
        if any(key != "module" and key != "ignore_missing_imports" for key in override):
            relaxed.update(n for n in names if n.startswith("platterpus"))
        elif override.get("ignore_missing_imports") and any(
            n.startswith("platterpus.") and not n.endswith("_build") for n in names
        ):
            relaxed.update(n for n in names if n.startswith("platterpus"))

    # Floor: if nothing was collected the comparison below is vacuous — it would pass
    # for a pyproject.toml with the whole `[tool.mypy]` table deleted.
    assert relaxed, (
        "no per-module mypy opt-out was found at all. Either every one has been "
        "retired — in which case delete this test and celebrate — or the parse has "
        "gone stale and the ratchet is passing by finding nothing."
    )

    added = sorted(relaxed - CEILING)
    assert not added, (
        f"new mypy opt-out(s) {added}. CLAUDE.md rule #10: the per-module opt-out list "
        f"shrinks, it does not grow — 'do not weaken a type to make a checker pass'. "
        f"Fix the types instead. If an opt-out is genuinely unavoidable, say why in "
        f"pyproject.toml AND raise the ceiling in this test, so the decision is visible."
    )
