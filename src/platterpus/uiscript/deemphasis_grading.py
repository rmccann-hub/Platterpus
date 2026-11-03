"""Section P3's pair of rips, ``-H -E`` and ``-H -W``: the pure half of the grade.

**What it decides.** Round 16's close condition, clause 2: *"`-H` together with
de-emphasis produces correct de-emphasised audio"*. The defect it probes made
``-H``, ``-H -W`` and ``-H -E`` produce byte-identical audio, the de-emphasis
filter never reached, while the log said it had been applied. Section P3 rips one
track twice, de-emphasis forced (``-E``) and disabled (``-W``), and this module
grades the two logs.

**Why two values, and why each one alone cannot decide it.**

* **The checksums are taken on the READ**, before the filter graph: EAC CRC32 and
  both AccurateRip sums accumulate over the buffer as it came off the drive
  (``crip_process_checksums`` at ``cyanrip@239adda:src/cyanrip_main.c:1680``,
  ``:1744`` and ``:1789``, each before ``cyanrip_send_pcm_to_encoders`` at
  ``:1685``, ``:1753`` and ``:1794``; the fork's own comment at
  ``src/cyanrip_encode.c:816``: *"The checksums stay on the read buffer"*). So
  equal CRCs say the two arms READ the same samples, which is what makes any
  difference downstream attributable to the filter. They cannot see the filter.
* **The loudness is measured on the DELIVERED audio**, the frames the encoders
  receive, after de-emphasis and HDCD, from the fork's ``+platterpus.20``
  (``measure_frame``, ``cyanrip@239adda:src/cyanrip_encode.c:818``, called on the
  filter graph's output at ``:909``; absent at ``cyanrip@174a134``, the ``.19``
  release, present at ``cyanrip@5704062``, ``.20``). Before ``.20`` ebur128 was fed
  the frame before the filter, and the 2026-09-22 session's P3 found exactly that:
  four streams, one set of numbers. On a build that measures before the filter
  this grade is **not determined**, never a failure, because the loudness could
  not have moved whatever the filter did.

So the pass condition is both: **the CRCs agree, and the integrated loudness
differs by at least** :data:`LOUDNESS_DIFFERENCE_FLOOR_LU`. The fork is being asked
to confirm the measurement point (our round 37 lap 6, S12 (d)); this grades on the
CRC equality and the R128 difference only, and says so in its answer.

**The floor, 0.3 LU, and why it is defensible.** Equal CRCs mean the two arms fed
the meter the same samples unless the filter changed them, and the meter is
deterministic, so a filter that did nothing prints the SAME figure twice: the null
result is a difference of exactly 0.0. cyanrip prints the figure to 0.1 LU, so two
readings of one value can differ by at most 0.1 from rounding; 0.3 is three times
that print resolution and cannot be reached by rounding alone. The effect itself is
larger: de-emphasis is the 50/15 µs shelf, about 3 dB down at 3.2 kHz and 10 dB
down by 10.6 kHz, and the K-weighting ``R128`` uses raises exactly those
frequencies. On the reference disc's track 1 it measured 0.8 LU (-20.7 forced,
-19.9 disabled, the 2026-11-03 Full run, ``.28``).

Pure and Qt-free; every function returns, none raises. The verb is
``uiscript/deemphasis_verbs.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from platterpus.data_tracks import is_data_track
from platterpus.parsers.rip_log import RipLog

#: The smallest integrated-loudness difference that counts as the filter having
#: acted, in LU. See the module docstring for the derivation.
LOUDNESS_DIFFERENCE_FLOOR_LU: Final[float] = 0.3

#: The first numbered fork release whose loudness is measured on the delivered
#: audio: ``.20``, release 30, ``cyanrip@5704062`` (``measure_frame`` is absent
#: from ``cyanrip_encode.c`` at ``.19``'s ``174a134`` and present at ``5704062``).
FIRST_RELEASE_MEASURING_DELIVERED_AUDIO: Final[int] = 30

#: The three answers. Tri-state: ``NOT_DETERMINED`` is not a pass and not a fail.
PASS: Final[str] = "pass"
FAIL: Final[str] = "fail"
NOT_DETERMINED: Final[str] = "not_determined"

#: What a fork build tag looks like before its commit (``platterpus-fork-g3f288fb``).
_FORK_COMMIT_SEPARATOR: Final[str] = "-g"


@dataclass(frozen=True)
class Arm:
    """One rip of the pair, as its log tells it."""

    #: The ``-D`` folder the rip wrote into (``r16deemphon``).
    name: str
    #: The log the values were read from; ``""`` when none was.
    source: str = ""
    #: The banner's build tag (``platterpus-fork-g3f288fb``); ``""`` when absent.
    build: str = ""
    #: ``(track, EAC CRC32)`` for each audio track, upper-case hex.
    crcs: tuple[tuple[int, str], ...] = ()
    #: ``Album integrated loudness (R128)`` in LUFS, or ``None`` when absent. For
    #: the one-track rips P3 makes it is that track's own figure.
    integrated_lufs: float | None = None
    #: Why this arm could not be read at all; ``""`` when it was.
    problem: str = ""

    def describe(self) -> str:
        """``r16deemphon: platterpus-fork-g3f288fb, track 1 B0D122E7, -20.7 LUFS``."""
        if self.problem:
            return f"{self.name}: {self.problem}"
        crcs = ", ".join(f"track {n} {c or '(no CRC)'}" for n, c in self.crcs)
        lufs = (
            f"{self.integrated_lufs:.1f} LUFS"
            if self.integrated_lufs is not None
            else "no integrated loudness"
        )
        build = self.build or "(no build named)"
        return f"{self.name}: {build}, {crcs or 'no audio track'}, {lufs}"


@dataclass(frozen=True)
class PairVerdict:
    """The grade of one pair: :data:`PASS`, :data:`FAIL` or :data:`NOT_DETERMINED`."""

    state: str
    detail: str


def arm_from_log(name: str, source: str, log: RipLog) -> Arm:
    """An :class:`Arm` from a parsed cyanrip log. Never raises.

    The loudness is read from ``RipLog.album_loudness``, the rows cyanrip owns
    (``Album integrated loudness (R128):``) preferred over FFmpeg's block, which
    is the parser's own rule (``cyanrip_log._Disc.record_album_loudness``).
    """
    crcs = tuple(
        (track.number, (track.copy_crc or "").strip().upper())
        for track in log.tracks
        if not is_data_track(track)
    )
    raw = (log.album_loudness or {}).get("integrated_lufs", "")
    try:
        lufs: float | None = float(raw) if raw else None
    except ValueError:
        lufs = None
    return Arm(
        name=name,
        source=source,
        build=(log.ripper_build or "").strip(),
        crcs=crcs,
        integrated_lufs=lufs,
    )


def measures_delivered_audio(build_tag: str) -> bool | None:
    """Whether ``build_tag``'s loudness is measured after the filter graph.

    ``True`` for a fork release from ``.20``; ``False`` for an earlier fork
    release or stock cyanrip; ``None`` when the build cannot be placed (an
    unknown tag, a fork commit outside the release list): not determined, never
    a guess in either direction. Never raises.
    """
    from platterpus.deps.fork_source import release_seq_for_commit
    from platterpus.ripper_identity import identify_ripper

    tag = (build_tag or "").strip()
    if not tag:
        return None
    identity = identify_ripper("", tag)
    if identity.kind == "stock":
        return False
    if identity.kind != "fork" or _FORK_COMMIT_SEPARATOR not in tag:
        return None
    commit = tag.casefold().removesuffix("-dirty").rsplit(_FORK_COMMIT_SEPARATOR, 1)[-1]
    seq = release_seq_for_commit(commit)
    if seq is None:
        return None
    return seq >= FIRST_RELEASE_MEASURING_DELIVERED_AUDIO


def _not_determined(why: str, lines: list[str]) -> PairVerdict:
    return PairVerdict(NOT_DETERMINED, "\n".join([f"not determined: {why}", *lines]))


def grade_pair(
    forced: Arm, disabled: Arm, *, floor: float = LOUDNESS_DIFFERENCE_FLOOR_LU
) -> PairVerdict:
    """Grade the ``-H -E`` arm against the ``-H -W`` arm. Never raises."""
    lines = [f"  forced:   {forced.describe()}", f"  disabled: {disabled.describe()}"]
    for arm in (forced, disabled):
        if arm.problem:
            return _not_determined(f"{arm.name} could not be read", lines)
    if forced.build != disabled.build:
        return _not_determined(
            "the two logs name different builds, so a difference between them "
            "cannot be put down to the filter",
            lines,
        )
    measured_after = measures_delivered_audio(forced.build)
    if measured_after is None:
        return _not_determined(
            f"the build {forced.build or '(none named)'} cannot be placed in the "
            "fork's release list, so where it measures loudness is not known",
            lines,
        )
    if not measured_after:
        return _not_determined(
            f"{forced.build} measures loudness on the read, before the filter "
            "graph (fixed in the fork's .20), so its loudness cannot show "
            "whether de-emphasis ran",
            lines,
        )
    forced_tracks = [n for n, _ in forced.crcs]
    if not forced.crcs or forced_tracks != [n for n, _ in disabled.crcs]:
        return _not_determined("the two rips did not read the same audio tracks", lines)
    if any(not crc for _, crc in (*forced.crcs, *disabled.crcs)):
        return _not_determined("a track has no EAC CRC32 in its log", lines)
    if forced.integrated_lufs is None or disabled.integrated_lufs is None:
        return _not_determined("a log has no integrated loudness", lines)
    differing = [
        n for (n, a), (_, b) in zip(forced.crcs, disabled.crcs, strict=True) if a != b
    ]
    # Rounded to the tenth cyanrip prints: -19.9 - -20.2 is 0.2999… in binary,
    # and a floor met exactly must not fail on float arithmetic.
    delta = round(forced.integrated_lufs - disabled.integrated_lufs, 1)
    lines.append(
        f"  loudness difference: {delta:+.1f} LU (forced minus disabled); "
        f"the floor is {floor:.1f} LU"
    )
    if delta > 0:
        lines.append(
            "  NOTE: de-emphasis only attenuates, so the forced arm is expected to "
            "be the quieter one; graded on the size of the difference alone"
        )
    lines.append(
        "  graded on CRC equality and the R128 difference only; the fork is asked "
        "to confirm where it measures loudness (our round 37 lap 6, S12 (d))"
    )
    if differing:
        return PairVerdict(
            FAIL,
            "\n".join(
                [
                    f"the two arms READ different audio (track(s) "
                    f"{', '.join(map(str, differing))}), so a loudness difference "
                    "cannot be put down to de-emphasis",
                    *lines,
                ]
            ),
        )
    if abs(delta) < floor:
        return PairVerdict(
            FAIL,
            "\n".join(
                [
                    "the two arms read the same audio and delivered the same "
                    "loudness: forcing de-emphasis changed nothing measurable, "
                    "which is the cascade defect's signature",
                    *lines,
                ]
            ),
        )
    return PairVerdict(
        PASS,
        "\n".join(
            [
                "the two arms read the same audio, and forcing de-emphasis "
                "changed the delivered loudness",
                *lines,
            ]
        ),
    )
