"""Which passes ask for ``--reread-until-accuraterip``: every ``-Z`` pass, and no other.

**Why (the fork's round 39 lap 3 S15).** Commit f7615bf6 sent the option on the
securing pass alone. The rig sheet's section N, "uniform secure re-read, WHOLE
DISC", is an Archival Exact rip whose ALBUM pass reads with ``-Z 2``, and the
five-rip run's first-pass argv (2026-11-11, ``secure reread``'s report,
``ripper_argv_first_pass``) carried ``-r 5 -Z 2 ... --prefer-accuraterip-match``
and not the option, so that pass kept ``3D8FCF0C`` by agreement (reads 1 and 4)
before our chase replaced it. An agreement AccurateRip rejects is the same
question on any ``-Z`` pass, so the worker now asks on each one
(``reread_until_accuraterip_args.confidence_for_pass``), and the backend's build
gate and ``-Z`` rule still decide what is sent.

**What does not follow it:** ``--reread-time-limit`` stays on the securing pass
(its value needs the album pass's read time, which an album pass has not yet
measured; the adapter module says why), and the verified-read chase's single
reads carry neither, having no ``-Z``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication
from test_rip_worker_verified_read import (
    _ALBUM_PASS,
    _FORK_GEOMETRY,
    _archival_album,
    _run,
    _run_archival,
    _securing_pass,
)

from platterpus.adapters.cyanrip_backend import CyanripImpl
from platterpus.adapters.reread_until_accuraterip_args import (
    REREAD_ACCURATERIP_CONFIDENCE,
    REREAD_UNTIL_ACCURATERIP_FLAG,
    confidence_for_pass,
)

_TAG_30 = "platterpus-fork-g5cc1c6b"
_TAG_31 = "platterpus-fork-ge531a33"


def _argv(tag: str, secure_rerip_matches: int, **options: object) -> list[str]:
    """The real builder, fed what the worker's one spawn site feeds it."""
    return CyanripImpl(binary_path="cyanrip")._build_rip_argv(
        "/dev/sr0",
        unknown=False,
        cover_art="",
        max_retries=5,
        read_offset_override=667,
        ripper_build_tag=tag,
        secure_rerip_matches=secure_rerip_matches,
        reread_until_accuraterip=confidence_for_pass(secure_rerip_matches),
        **options,  # type: ignore[arg-type]  # keyword options of the builder, typed there
    )


# --- the decision ------------------------------------------------------------------


@pytest.mark.parametrize("z", [1, 2, 5])
def test_every_z_pass_asks_for_conf_2(z: int) -> None:
    assert confidence_for_pass(z) == REREAD_ACCURATERIP_CONFIDENCE == 2


@pytest.mark.parametrize("z", [0, -1])
def test_a_pass_without_z_asks_for_nothing(z: int) -> None:
    assert confidence_for_pass(z) is None


# --- the argv each pass shape produces -----------------------------------------------


def test_section_ns_whole_disc_z_pass_now_sends_the_option_to_31() -> None:
    """The five-rip run's first-pass shape (``-r 5 -Z 2``, whole disc, no ``-l``): the
    option rides beside ``-Z``, and no time limit is sent with it."""
    argv = _argv(_TAG_31, 2)
    assert argv[argv.index("-Z") + 1] == "2"
    assert argv[argv.index(REREAD_UNTIL_ACCURATERIP_FLAG) + 1] == "2"
    assert "-l" not in argv, "a whole-disc pass"
    assert "--reread-time-limit" not in argv


def test_30_still_gets_z_and_not_the_option() -> None:
    """The gate is unchanged: ``.30``, FORK_PIN, does not list the option."""
    argv = _argv(_TAG_30, 2)
    assert "-Z" in argv and REREAD_UNTIL_ACCURATERIP_FLAG not in argv


def test_a_chase_reads_argv_is_unchanged_and_is_never_refused() -> None:
    """The chase's shape (``-r 5 -l 5``, no ``-Z``): nothing asked, so the builder's
    refusal of the option without ``-Z`` can never fire on it."""
    argv = _argv(_TAG_31, 0, only_tracks=(5,))
    assert "-Z" not in argv and REREAD_UNTIL_ACCURATERIP_FLAG not in argv


# --- the worker: which calls ask --------------------------------------------------------


def test_archival_exacts_album_pass_asks_and_its_chase_reads_do_not(
    qapp: QApplication, tmp_path: Path
) -> None:
    """Section N's shape: the uniform album pass reads every track with -Z 2, so it
    asks; it gets no time limit; the chase's single reads ask for neither."""
    album = _archival_album(
        ("59D352DD", "3D8FCF0C", "3D8FCF0C"),
        "3D8FCF0C",
        "Done; (2 out of 2 matches for current checksum 3D8FCF0C)",
    )
    _worker, backend = _run_archival(
        tmp_path, album, [("3D8FCF0C", None, 0), ("59D352DD", 200, 0)]
    )
    assert len(backend.rip_calls) == 3, "floor: album pass and two chase reads"
    album_call, *chase_calls = backend.rip_calls
    assert album_call["secure_rerip_matches"] == 2 and album_call["only_tracks"] == ()
    assert album_call["reread_until_accuraterip"] == 2
    assert album_call["reread_time_limit_s"] is None
    for call in chase_calls:
        assert call["secure_rerip_matches"] == 0
        assert call["reread_until_accuraterip"] is None
        assert call["reread_time_limit_s"] is None


def test_fast_verifieds_album_pass_has_no_z_and_does_not_ask(
    qapp: QApplication, tmp_path: Path
) -> None:
    """Dynamic mode: the album pass reads once without -Z and asks nothing; the
    securing pass asks; the chase read does not."""
    album = _ALBUM_PASS.replace(
        "Track 1 ripped and encoded successfully!\n",
        "Track 1 ripped and encoded successfully!\n" + _FORK_GEOMETRY,
    )
    _worker, backend = _run(
        tmp_path,
        _securing_pass(("C96464AB", "4065BECC"), "4065BECC"),
        [("C96464AB", 200, 0)],
        album=album,
    )
    assert len(backend.rip_calls) == 3, "floor: album, securing, one chase read"
    asked = [call["reread_until_accuraterip"] for call in backend.rip_calls]
    assert asked == [None, 2, None]


def test_every_call_asks_exactly_when_it_reads_with_z(
    qapp: QApplication, tmp_path: Path
) -> None:
    """The relation over both modes' calls, with a floor that both kinds of pass
    were seen, so a run that spawned only one kind cannot pass it vacuously."""
    album = _archival_album(
        ("59D352DD", "3D8FCF0C", "3D8FCF0C"),
        "3D8FCF0C",
        "Done; (2 out of 2 matches for current checksum 3D8FCF0C)",
    )
    _w1, archival = _run_archival(
        tmp_path / "a", album, [("3D8FCF0C", None, 0), ("59D352DD", 200, 0)]
    )
    _w2, dynamic = _run(
        tmp_path / "d",
        _securing_pass(("C96464AB", "4065BECC"), "4065BECC"),
        [("C96464AB", 200, 0)],
    )
    calls = archival.rip_calls + dynamic.rip_calls
    with_z = [c for c in calls if c["secure_rerip_matches"] > 0]
    without_z = [c for c in calls if c["secure_rerip_matches"] <= 0]
    assert len(with_z) >= 2 and len(without_z) >= 3, "floor: both kinds seen"
    for call in calls:
        assert (call["reread_until_accuraterip"] is not None) == (
            call["secure_rerip_matches"] > 0
        ), call
