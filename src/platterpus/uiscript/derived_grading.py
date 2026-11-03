"""The pure grader behind ``expect-derived-files``: the MP3, WavPack or WAV files.

**Why it exists** (review C4 of the owner's 2026-11-03 Full run). Sections K1 to
K3 rip in a derived format, then graded the FLAC masters (``expect-tags``,
``expect-cover-art``) and counted the derived files (``expect-derived-output``).
Nothing opened a derived file, so an MP3 without its title, a WavPack cut short
or an MP3 quality that never reached the encoder would all have passed. When a
user picks MP3, the MP3 IS their library entry (``docs/testing.md``, K1).

What it reads, per track, from the derived file itself
(:func:`platterpus.derived_metadata.read_derived_metadata`):

* **length**: lossless WavPack and WAV must hold exactly the master's samples
  (its own ``STREAMINFO``, :func:`platterpus.checksums.flac_total_samples`); an
  MP3 within a tenth of a second, since a lossy encode is not sample-exact;
* **tags**, MP3 and WavPack: :func:`~platterpus.uiscript.tag_grading.tag_problems`,
  the one rule ``expect-tags`` applies to the FLACs. WAV's tags are not graded:
  RIFF has no tag the format promises, and what ffmpeg copies is reported;
* **art**: an MP3 carries the cover exactly when the ``cover_art`` setting
  embeds it (:func:`platterpus.adapters.cover_art.plan_actions`). WavPack and WAV
  cannot carry one through our transcode, and their folder copy is
  ``expect-cover-art``'s;
* **the encoder**, from the report's ``verification.transcode.encoder_argv``,
  the argv as spawned (schema v42): the codec for the format, and for MP3 the
  ``-q:a`` the script set.

Tri-state: anything the record cannot settle is *not determined* (BLOCKED),
never a pass. Pure and Qt-free; never raises.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Final

from platterpus.uiscript.artifact_grading import Grade
from platterpus.uiscript.tag_grading import ExpectedTags, ripped_masters, tag_problems

#: The derived formats, each with its file extension and the ffmpeg codec our
#: transcode adapter names for it (`adapters/transcode._build_argv`).
FORMATS: Final[dict[str, tuple[str, str]]] = {
    "mp3": ("mp3", "libmp3lame"),
    "wavpack": ("wv", "wavpack"),
    "wav": ("wav", "pcm_s16le"),
}

#: How far an MP3's length may stray from its master's: a tenth of a second.
MP3_LENGTH_TOLERANCE_S: Final[float] = 0.1


def _arg_after(argv: Sequence[object], flag: str) -> str | None:
    parts = [str(part) for part in argv]
    for index, part in enumerate(parts[:-1]):
        if part == flag:
            return parts[index + 1]
    return None


def _encoder_findings(
    report: Mapping[str, Any], fmt: str, quality: int | None
) -> tuple[list[str], list[str], str]:
    """(problems, undetermined, said) about the encoder that ran."""
    verification = report.get("verification")
    transcode = (
        verification.get("transcode") if isinstance(verification, dict) else None
    )
    argv = transcode.get("encoder_argv") if isinstance(transcode, dict) else None
    if not isinstance(argv, list) or not argv:
        return [], ["the report records no encoder argv (written from schema v42)"], ""
    codec = _arg_after(argv, "-c:a")
    problems: list[str] = []
    if codec != FORMATS[fmt][1]:
        problems.append(f"the encoder ran with -c:a {codec!r}, not {FORMATS[fmt][1]}")
    said = f"encoded with -c:a {codec}"
    if fmt == "mp3":
        ran = _arg_after(argv, "-q:a")
        said += f" -q:a {ran}"
        if quality is not None and ran != str(quality):
            problems.append(
                f"the encoder ran with -q:a {ran!r}, the script set {quality}"
            )
    return problems, [], said


def grade_derived_files(
    report: Mapping[str, Any],
    folder: Path,
    fmt: str,
    expected: ExpectedTags,
    cover_mode: str,
    quality: int | None = None,
) -> Grade:
    """Every derived file is its master's length, tags, art and encoder."""
    from platterpus.adapters.cover_art import plan_actions
    from platterpus.checksums import flac_total_samples
    from platterpus.derived_metadata import read_derived_metadata
    from platterpus.uiscript.tag_grading import report_release_id

    if fmt not in FORMATS:
        return Grade(False, f"{fmt!r} is not a derived format: {', '.join(FORMATS)}")
    masters = ripped_masters(report, folder)
    if not masters:
        return Grade(False, "the report names no ripped FLAC, so nothing was derived")
    problems, undetermined, said = _encoder_findings(report, fmt, quality)
    release_id = report_release_id(report)
    embed = plan_actions(cover_mode, False, release_id or "")[0]
    if fmt == "mp3" and release_id is None:
        undetermined.append("the report names no release, so the cover owed is unknown")
    carried: list[str] = []
    for number, master in masters:
        path = master.with_suffix(f".{FORMATS[fmt][0]}")
        meta = read_derived_metadata(path)
        if not path.is_file() or meta.kind != fmt or meta.problem:
            why = (meta.problem or f"not a {fmt} file") if path.is_file() else "missing"
            problems.append(f"track {number}: {path.name} could not be read ({why})")
            continue
        want = flac_total_samples(master)
        if want is None or meta.samples is None or not meta.sample_rate:
            undetermined.append(f"track {number}: its length")
        elif fmt == "mp3":
            if abs(meta.samples - want) > meta.sample_rate * MP3_LENGTH_TOLERANCE_S:
                problems.append(
                    f"track {number}: {meta.samples / meta.sample_rate:.2f} s, its "
                    f"master {want / meta.sample_rate:.2f} s"
                )
        elif meta.samples != want:
            problems.append(f"track {number}: {meta.samples} samples, master {want}")
        if fmt != "wav":
            problems.extend(tag_problems(number, meta.values, expected))
        elif meta.tags:
            carried.append(f"track {number}: {', '.join(n for n, _ in meta.tags)}")
        if fmt == "wav" and meta.bits != 16:
            problems.append(f"track {number}: {meta.bits}-bit, not 16-bit PCM")
        if fmt == "mp3" and release_id is not None and embed != (meta.pictures > 0):
            owed = "a cover" if embed else "no picture"
            problems.append(f"track {number}: {meta.pictures} picture(s), {owed} owed")
    if problems:
        shown = "; ".join(problems[:12])
        more = f" (+{len(problems) - 12} more)" if len(problems) > 12 else ""
        return Grade(False, shown + more)
    if undetermined:
        return Grade(
            False, "not determined: " + "; ".join(undetermined[:6]), blocked=True
        )
    art = (
        ("cover embedded in each" if embed else "no picture, as the setting asks")
        if fmt == "mp3"
        else "no embedded cover (the format's folder copy is expect-cover-art's)"
    )
    tags = (
        "tags not graded: RIFF promises none"
        + (f"; ffmpeg copied {'; '.join(carried)}" if carried else "")
        if fmt == "wav"
        else "album, album artist, title, artist and track number as chosen"
    )
    return Grade(
        True,
        f"{len(masters)} .{FORMATS[fmt][0]} file(s), each its master's length; "
        f"{tags}; {art}; {said}",
    )
