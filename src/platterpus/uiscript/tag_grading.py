"""The acceptance script's graders that read the FLAC FILES a rip wrote.

Split from :mod:`platterpus.uiscript.artifact_grading` by what they read: those
graders read the rip's RECORD (its report and the ripper's log), these open the
audio files themselves, through :func:`platterpus.flac_metadata.
read_flac_metadata`, because a tag or a cover is only verified where a music
library will read it. Pure and Qt-free, like their siblings; nothing here raises.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from platterpus.flac_metadata import PICTURE_FRONT_COVER, read_flac_metadata
from platterpus.inbound_text import screen_line
from platterpus.uiscript.artifact_grading import Grade


@dataclass(frozen=True)
class ExpectedTags:
    """What the user chose, read from the window — not from what we sent.

    The argv is escaped for cyanrip (``\\:`` for a colon); reading the intent
    back out of it would need the unescaping this check exists to test. The
    window's fields are the independent source: what the user saw and meant.
    """

    album: str
    album_artist: str
    #: Track number -> (title, artist).
    tracks: Mapping[int, tuple[str, str]]


def ripped_masters(report: Mapping[str, Any], folder: Path) -> list[tuple[int, Path]]:
    """``(track number, FLAC path)`` for every track the report says was ripped.

    From the report's per-track filenames, which come from cyanrip's own log, so
    the numbering is the ripper's rather than a guess from file order.
    """
    masters: list[tuple[int, Path]] = []
    for entry in report.get("tracks") or []:
        if not isinstance(entry, dict):
            continue
        number = entry.get("number")
        name = entry.get("filename")
        if isinstance(number, int) and isinstance(name, str) and name.endswith(".flac"):
            masters.append((number, folder / Path(name).name))
    return masters


def render_tags(masters: Sequence[tuple[int, Path]], limit: int = 1) -> str:
    """The tags of the first ``limit`` ripped FLACs, as text for the bundle.

    The fork's round 30 lap 3 S24: the acceptance bundle carries no audio, so no
    tag had ever been evidence either side could read. This is what
    :func:`read_flac_metadata` read, every comment in file order and each
    picture's type, size and MIME type, so the bundle holds the tags as the
    file holds them rather than our grade of them. Never raises.

    **Screened like any other external text** (:mod:`platterpus.inbound_text`):
    a value is MusicBrainz's, or the user's, and one holding a newline would
    otherwise split into a line that reads as a second tag. Each control
    character becomes a visible ``\\xNN`` escape, and the count is stated.
    """
    lines: list[str] = []
    for number, path in list(masters)[: max(limit, 0)]:
        meta = read_flac_metadata(path)
        body = [f"vendor: {meta.vendor}"]
        body.extend(f"{name}={value}" for name, value in meta.comments)
        screened = [screen_line(line) for line in body]
        lines.append(f"# track {number}: {screen_line(path.name).text}")
        if not meta.is_flac or meta.problem:
            lines.append(f"# not read completely: {meta.problem or 'not a FLAC file'}")
        escaped = sum(one.control_chars for one in screened)
        if escaped:
            lines.append(f"# {escaped} control character(s) shown as \\xNN escapes")
        lines.append(f"# {screened[0].text}")
        lines.extend(one.text for one in screened[1:])
        lines.extend(
            f"# picture: type {pic.picture_type}, "
            f"{screen_line(pic.mime).text}, {pic.data_bytes} bytes"
            for pic in meta.pictures
        )
        lines.append("")
    return "\n".join(lines)


def _one(values: list[str]) -> str | None:
    return values[0] if len(values) == 1 else None


def grade_tags(masters: Sequence[tuple[int, Path]], expected: ExpectedTags) -> Grade:
    """Every ripped FLAC carries exactly the album, artist and titles chosen.

    Exact string equality, so a colon, an ``=``, a backslash or an apostrophe
    that the escaping mangled is a failure here even when the file NAME (which
    cyanrip's ``-T unicode`` rewrites on purpose) looks right.
    """
    if not masters:
        return Grade(
            False, "the report names no ripped FLAC, so there are no tags to read"
        )
    problems: list[str] = []
    for number, path in masters:
        meta = read_flac_metadata(path)
        if not meta.is_flac or meta.problem:
            problems.append(
                f"track {number}: {path.name} could not be read ({meta.problem})"
            )
            continue
        title, artist = expected.tracks.get(number, (None, None))
        wanted = {
            "ALBUM": expected.album,
            "ALBUMARTIST": expected.album_artist,
            "TITLE": title,
            "ARTIST": artist,
        }
        for key, value in wanted.items():
            if value is None:
                problems.append(f"track {number}: the window has no row for it")
                break
            found = meta.values(key)
            if _one(found) != value:
                problems.append(f"track {number}: {key} is {found!r}, chosen {value!r}")
        numbers = meta.values("TRACKNUMBER")
        if not numbers or numbers[0].split("/")[0].strip().lstrip("0") != str(number):
            problems.append(f"track {number}: TRACKNUMBER is {numbers!r}")
    if problems:
        return Grade(
            False,
            "; ".join(problems[:12])
            + (f" (+{len(problems) - 12} more)" if len(problems) > 12 else ""),
        )
    return Grade(
        True,
        f"{len(masters)} FLAC(s): album, album artist, title, artist and track "
        f"number are each exactly what was chosen",
    )


def grade_cover_art(
    masters: Sequence[tuple[int, Path]],
    report: Mapping[str, Any],
    mode: str,
    release_id: str,
) -> Grade:
    """The cover art on disk is what the ``cover_art`` mode asks for.

    Which actions a mode asks for is :func:`cover_art.plan_actions`'s answer,
    called here rather than restated. Embedding is graded on the FLACs
    themselves: a front-cover picture in every one when asked for, none when not
    (``-G`` keeps cyanrip from embedding its own, so any picture there is ours),
    and the report's ``embedded_count`` must equal what the files hold. A folder
    copy is graded when asked for; its ABSENCE is not graded when it was not,
    because a WavPack or WAV rip saves one regardless (those formats cannot carry
    the cover the MP3 path embeds).
    """
    from platterpus.adapters.cover_art import plan_actions

    embed, save_file = plan_actions(mode, False, release_id)
    block = report.get("cover_art")
    art = block if isinstance(block, dict) else {}
    if (embed or save_file) and art.get("found") is False:
        return Grade(
            False,
            f"cover art was asked for ({mode!r}) but none was fetched: "
            f"{art.get('reason')} {art.get('error') or ''}".strip(),
            blocked=True,
        )
    with_cover: list[int] = []
    problems: list[str] = []
    for number, path in masters:
        meta = read_flac_metadata(path)
        if not meta.is_flac or meta.problem:
            problems.append(
                f"track {number}: {path.name} could not be read ({meta.problem})"
            )
            continue
        if any(
            p.picture_type == PICTURE_FRONT_COVER and p.data_bytes > 0
            for p in meta.pictures
        ):
            with_cover.append(number)
        elif meta.pictures and not embed:
            with_cover.append(number)  # any picture at all is one nobody asked for
    missing = sorted({n for n, _ in masters} - set(with_cover))
    if embed and missing:
        problems.append(
            f"no embedded front cover in track(s) {', '.join(map(str, missing))}"
        )
    if not embed and with_cover:
        problems.append(
            f"mode {mode!r} embeds nothing, yet track(s) "
            f"{', '.join(map(str, with_cover))} carry a picture"
        )
    claimed = art.get("embedded_count") or 0
    if claimed != (len(with_cover) if embed else 0):
        problems.append(
            f"the report says {claimed} file(s) took the cover; the files hold "
            f"{len(with_cover)}"
        )
    if save_file:
        saved = art.get("saved_as")
        target = masters[0][1].parent / str(saved) if masters and saved else None
        if target is None or not target.is_file() or target.stat().st_size == 0:
            problems.append(f"no folder copy of the cover (the report names {saved!r})")
    if not masters:
        problems.append("the report names no ripped FLAC, so there is no art to check")
    if problems:
        return Grade(False, "; ".join(problems))
    return Grade(
        True,
        f"mode {mode!r}: "
        + (
            f"front cover embedded in all {len(with_cover)} FLAC(s)"
            if embed
            else "nothing embedded"
        )
        + ("; folder copy present" if save_file else ""),
    )
