"""Arguments we hand a dependency must satisfy that dependency's contract.

CLAUDE.md has required this for a while — *"before invoking an external tool,
validate that the arguments we hand it satisfy that tool's documented
contract"* — and nothing enforced it. The rig collected the bill on
2026-08-02: disc 1 of a 4-disc set has **16** tracks, MusicBrainz's medium
listed **18**, and Platterpus passed cyanrip

    -t 17=title=Texas Cowboy:artist=Glenn Ohrlin
    -t 18=title=Streets of Laredo:artist=Brownie Ford

cyanrip's answer was ``Invalid track number 17, list has 16 tracks!``, exit 1,
**two seconds, nothing ripped.** One out-of-range tag killed the whole rip.

The medium-selection bug that produced 18 titles is a separate defect upstream
of here. This file guards the *boundary*: whatever the metadata says, argv must
never carry a track number the disc does not have.
"""

from __future__ import annotations

from types import SimpleNamespace

from platterpus.adapters.cyanrip_backend import _metadata_args
from platterpus.adapters.rip_backend import RipMetadata


def _meta(count: int) -> RipMetadata:
    return RipMetadata(
        tracks=tuple(
            SimpleNamespace(number=n, title=f"Track {n}", artist="A", isrc="")
            for n in range(1, count + 1)
        )
    )


def _track_numbers(args: list[str]) -> list[int]:
    """The N of every ``-t N=...`` in an argv list."""
    return [
        int(value.split("=", 1)[0])
        for flag, value in zip(args, args[1:], strict=False)
        if flag == "-t" and value.split("=", 1)[0].isdigit()
    ]


def test_a_track_the_disc_does_not_have_is_never_passed() -> None:
    """The rig's exact numbers: 18 titles, a 16-track disc."""
    args = _metadata_args(_meta(18), "", 16)
    assert _track_numbers(args) == list(range(1, 17))
    assert "17=" not in " ".join(args)
    assert "18=" not in " ".join(args)


def test_every_track_survives_when_the_counts_agree() -> None:
    """The guard must cost nothing in the normal case — which is every disc
    whose MusicBrainz medium matches its TOC, i.e. almost all of them."""
    assert _track_numbers(_metadata_args(_meta(14), "", 14)) == list(range(1, 15))


def test_a_short_metadata_list_is_left_alone() -> None:
    """Fewer tags than tracks is legitimate (a partial edit, an unknown disc).
    The guard trims a ceiling; it must never pad."""
    assert _track_numbers(_metadata_args(_meta(3), "", 14)) == [1, 2, 3]


def test_an_unknown_disc_count_disables_the_guard_rather_than_guessing() -> None:
    """None means "we don't know how many tracks the disc has". Inventing a
    ceiling there would drop real tags on a disc we simply hadn't scanned —
    the guard has to stay out of the way instead."""
    assert _track_numbers(_metadata_args(_meta(18), "")) == list(range(1, 19))
    assert _track_numbers(_metadata_args(_meta(18), "", None)) == list(range(1, 19))


def test_a_zero_ceiling_is_treated_as_unknown_not_as_drop_everything() -> None:
    """0 reaches here from an unscanned disc's track count. Read literally it
    would strip every tag from every rip; it means "unknown"."""
    assert _track_numbers(_metadata_args(_meta(5), "", 0)) == [1, 2, 3, 4, 5]


# --- the other half: the tool told us, and we didn't pass it on -------------


def test_the_rippers_own_fatal_error_is_recognised_as_a_hint() -> None:
    """cyanrip diagnosed the Roots failure precisely and the user saw
    "Rip failed."

    `failure_hint` was null in the report while the exact sentence sat in
    stdout. CLAUDE.md already requires capturing a dependency's error output
    instead of swallowing it — this is that rule reaching the line the user
    actually reads.
    """
    from platterpus.workers.rip_worker import _RIPPER_ERROR_RE

    fatal = [
        "Invalid track number 17, list has 16 tracks!",
        "Unable to open device: /dev/sr0",
        "Missing pregap action",
        "No device specified and unable to get default device!",
        "Stopping, ripping incomplete!",
    ]
    for line in fatal:
        assert _RIPPER_ERROR_RE.match(line), line


def test_ordinary_rip_output_is_not_mistaken_for_a_fatal_error() -> None:
    """A hint that fires on normal output is worse than none — it would
    replace "Done." with a random log line on every successful rip."""
    from platterpus.workers.rip_worker import _RIPPER_ERROR_RE

    ordinary = [
        "Ripping and encoding track 4, progress - 11.63%",
        "  EAC CRC32:     B0D122E7",
        "    Accurip v2:  22B9924D (accurately ripped, confidence 200)",
        "Track 1 ripped and encoded successfully!",
        "Gaps:",
        "    None signalled",
        "Flushing encoders...",
    ]
    for line in ordinary:
        assert not _RIPPER_ERROR_RE.match(line), line
