"""What our report says about a cyanrip log that stops before its first track.

The fork asked this in round 27 lap 6 (S16): their `.17` (`ee0221c`) writes the
version banner and the identity lines as soon as the log opens, so a rip that
fails on its arguments or on the drive now leaves a log that starts like any
other and then stops. There is no track block and no completion footer.

Measured 2026-09-26, through the same dispatch the app uses
(`looks_like_cyanrip_log` then `parse_cyanrip_log`), the report got three things
right and one wrong:

* **Right:** the banner is read, so the build is named and the approval is judged
  from it; the rip is `rip_failed`; and the fatal line reaches the user from the
  ripper's own output, because the matcher knows it.
* **Wrong:** its `unverified` issue said *"no track matched AccurateRip … (an
  unsubmitted pressing, an unreachable database, or a wrong read offset all look
  like this)"*. That blames the disc, the database or the offset for a read that
  never happened, in the record a user keeps. Now it says the log records no
  ripped track. The wording changes only when the log parsed and was not cut
  off, because only then can it vouch for having no track.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from platterpus import rip_report
from platterpus.parsers.cyanrip_log import looks_like_cyanrip_log, parse_cyanrip_log
from platterpus.workers.rip_worker import _RIPPER_ERROR_RE

#: The shape `.17` writes when a rip fails before its first track: the banner and
#: identity lines first (fork's `tests/rip_images.py`, `sc_early_log`, at
#: `ee0221c`), the replay of what was printed before the log opened, then the
#: fatal line. The header lines are copied from the Full run's real log.
EARLY_LOG = """cyanrip 0.9.4-rc2+platterpus.17 (platterpus-fork-gee0221c)
Invoked as:     /usr/local/bin/cyanrip -d /dev/sr0 -s 667 -o flac -N --consumer platterpus/0.6.61 -D /music -L log
Handshake:      round 28 lap 1 open, verdict OPEN -- released build
                (declared at build time, not verified by cyanrip)
Consumer:       platterpus/0.6.61
                (reported by the caller, not verified by cyanrip)
--- output before this log was opened ---
Checking
Opening drive...
--- end of pre-log output ---
Invalid scheme syntax, unterminated "{"!
"""
FATAL = 'Invalid scheme syntax, unterminated "{"!'
OLD_WORDING = "an unsubmitted pressing"


def _report(rip_log: object) -> dict:
    outcome = rip_report.build_outcome(
        status="failed", ripper_exit_code=1, ripper_argv=["cyanrip", "-d", "/dev/sr0"]
    )
    return rip_report.build_report(
        rip_log, generated_at="2026-09-26T00:00:00Z", outcome=outcome
    )


def _issue(report: dict, code: str) -> dict:
    return next(i for i in report["issues"] if i["code"] == code)


def test_the_early_log_is_read_as_cyanrips_with_its_banner() -> None:
    assert looks_like_cyanrip_log(EARLY_LOG)
    rip_log = parse_cyanrip_log(EARLY_LOG)
    assert rip_log.ripper_build == "platterpus-fork-gee0221c"
    assert rip_log.tracks == [] or len(rip_log.tracks) == 0
    report = _report(rip_log)
    assert report["rip"]["ripper_build"] == "platterpus-fork-gee0221c"
    codes = {i["code"] for i in report["issues"]}
    assert "rip_failed" in codes
    assert "ripper_log_unparsed" not in codes


def test_a_rip_that_read_nothing_is_not_blamed_on_the_disc() -> None:
    report = _report(parse_cyanrip_log(EARLY_LOG))
    message = _issue(report, "unverified")["message"]
    assert "records no ripped track" in message
    assert OLD_WORDING not in message


def test_a_log_we_could_not_vouch_for_keeps_the_old_wording() -> None:
    """No log, or a truncated one, says nothing about what was ripped."""
    missing = _report(None)
    assert OLD_WORDING in _issue(missing, "unverified")["message"]

    truncated = parse_cyanrip_log(EARLY_LOG)
    truncated = SimpleNamespace(**{**vars(truncated), "log_truncated": True})
    assert OLD_WORDING in _issue(_report(truncated), "unverified")["message"]


def test_the_fatal_line_reaches_the_user_from_the_rippers_own_output() -> None:
    """The report reads the log; the user's message comes from what the ripper
    printed, through the matcher built from the fork's fatal inventory."""
    assert _RIPPER_ERROR_RE.match(FATAL)


def test_the_full_runs_real_log_opens_with_the_lines_this_fixture_copies() -> None:
    """The fixture's header is not invented: the real log has the same four lines."""
    real = (
        Path(__file__).resolve().parents[1]
        / "docs/handshake/artifactsround27/round27fullwholedisc.log"
    ).read_text(encoding="utf-8")
    heads = [line.split(":", 1)[0] for line in real.splitlines()[1:6]]
    assert heads[:1] == ["Invoked as"] and "Handshake" in heads and "Consumer" in heads
