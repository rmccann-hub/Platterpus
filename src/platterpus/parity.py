"""Compare a rip's per-track Copy CRCs against an EAC baseline.

EAC is the bit-perfect baseline (``output_reference/``, ``docs/test-plan.md``).
A rip from any backend is byte-identical to EAC's when every track's **Copy
CRC** matches. This module reads the per-track Copy CRCs out of a log —
whichever of the three formats it is (EAC, cyanrip, or the legacy log format)
— and diffs a candidate against a baseline.

Pure and never-raises; backs ``scripts/eac_parity.py`` and the parity tests.
It's the "proof it's working" check for ``output_reference/``: a backend's log
is only committed there once it shows parity here.

**Output format (FLAC / WAV / MP3) doesn't matter to this check.** The Copy CRC
is computed on the *extracted PCM*, before the output encoder, so one comparison
covers all three:

* **FLAC / WAV** are lossless → identical PCM → identical Copy CRC, so a WAV rip
  is bit-perfect against the same EAC *FLAC* baseline (no separate WAV baseline
  needed).
* **MP3** is lossy → the encoded audio is *not* bit-comparable, but the
  extraction CRC still proves the read was bit-perfect. "MP3 parity" therefore
  means this CRC matches **plus** correct encoder/tag behaviour — the latter is
  out of scope for this module.

**A baseline is only evidence if somebody else wrote it.** Platterpus writes an
EAC-layout export of its own rips (``eac_log_export.py``). Handed back in as the
*baseline*, it compares our rip with our own rendering of that rip, and every
track matches by construction: a "14/14 PARITY" that proves nothing about EAC.
:func:`identify_baseline` says who wrote a baseline, by asking
``parsers/eac_log.eac_log_producer`` (the one predicate; nothing here restates
its rule), and :attr:`ParityReport.ok` refuses a baseline that is ours, so no
caller of :func:`compare_logs` can be handed that pass.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from platterpus.inbound_text import screen_line
from platterpus.parsers.cyanrip_log import looks_like_cyanrip_log, parse_cyanrip_log
from platterpus.parsers.eac_log import (
    EacLogProducer,
    eac_log_producer,
    eac_log_producer_line,
    looks_like_eac_log,
    parse_eac_copy_crcs,
)
from platterpus.parsers.rip_log import parse_rip_log

#: A Copy CRC is a CRC-32: exactly eight hex digits, either case.
_CRC32_HEX: Final[re.Pattern[str]] = re.compile(r"[0-9A-Fa-f]{8}")

#: How much of a baseline's identifying line a message quotes. Every banner the
#: classifier knows is under 70 characters; a longer first line (it is external
#: text, and could be anything) is quoted head-first with the rest COUNTED, never
#: silently cut, so the reader knows the quote is partial.
_SHOWN_LINE_CHARS: Final[int] = 120


def decode_log_bytes(raw: bytes) -> str:
    """Decode rip-log bytes to text, honoring the encoding the tool wrote.

    **EAC writes its logs as UTF-16** (with a BOM) — naively reading them as
    UTF-8 turns every character into a replacement char, so the parser finds no
    CRCs and the parity check silently false-fails (every track "missing").
    cyanrip and legacy-format logs are UTF-8. We sniff the BOM (and fall back to
    a NUL-heavy heuristic for the rare BOM-less UTF-16), then default to UTF-8.
    Never raises — undecodable bytes are replaced.
    """
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16", errors="replace")  # BOM picks LE/BE
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig", errors="replace")
    # BOM-less UTF-16 is rare, but an ASCII-ish UTF-16 file is ~half NUL bytes;
    # if the head is NUL-heavy, guess UTF-16 and its endianness from where the
    # NULs fall (LE → the high byte, at odd indices, is NUL).
    head = raw[:256]
    if head and head.count(0) > len(head) // 4:
        le_nuls = sum(1 for i in range(1, len(head), 2) if head[i] == 0)
        be_nuls = sum(1 for i in range(0, len(head), 2) if head[i] == 0)
        enc = "utf-16-le" if le_nuls >= be_nuls else "utf-16-be"
        return raw.decode(enc, errors="replace")
    return raw.decode("utf-8", errors="replace")


def track_copy_crcs(text: str) -> dict[int, str]:
    """Per-track ``{number: uppercase Copy CRC}`` from a rip log of ANY backend.

    Sniffs the format (cyanrip → EAC → the legacy log format as the default) and
    dispatches to the matching parser. Never raises — unrecognised input yields
    an empty map.
    Tracks with no Copy CRC (e.g. a data track) are omitted — and so are tracks whose
    value is not eight hex digits. The EAC and cyanrip parsers only ever capture that
    shape; the legacy-format parser keeps the field verbatim, so a garbled
    ``Copy CRC: n/a`` used to come back as the "CRC" ``N/A``, and two logs carrying
    the same garbage compared as a bit-perfect match (found by the property test,
    2026-09-25). One definition for all three branches.
    """
    if looks_like_cyanrip_log(text):
        return {
            t.number: t.copy_crc.upper()
            for t in parse_cyanrip_log(text).tracks
            if _CRC32_HEX.fullmatch(t.copy_crc)
        }
    if looks_like_eac_log(text):
        return parse_eac_copy_crcs(text)  # its regex already admits only 8 hex
    return {
        t.number: t.copy_crc.upper()
        for t in parse_rip_log(text).tracks
        if _CRC32_HEX.fullmatch(t.copy_crc)
    }


@dataclass(frozen=True)
class BaselineProducer:
    """Who wrote a parity baseline, as the baseline's own first line says.

    Tri-state, and each state is reported differently by every caller:

    * ``"exact_audio_copy"`` — the first line is EAC's banner. That is what the
      log SAYS, not proof: EAC's own log checksum is not checked here.
    * ``"platterpus"`` — the first line is one of OUR export's banners (either
      wording). Not an independent baseline at all; :attr:`ParityReport.ok`
      refuses it.
    * ``None`` — not determined. A cyanrip or legacy-format log is a legitimate
      baseline for comparing two rips, but a match against it is parity with
      that log, and it must never be described as parity with EAC.
    """

    producer: EacLogProducer | None
    #: The line the classifier read the answer from, as it read it (a leading BOM
    #: removed, nothing else; ``eac_log_producer_line``), or ``None`` when the
    #: text has no non-blank line.
    line: str | None

    @property
    def is_ours(self) -> bool:
        """True when the baseline is one of Platterpus's own EAC-layout exports."""
        return self.producer == "platterpus"

    @property
    def shown_line(self) -> str:
        """The identifying line, made safe to print, and bounded with a count.

        It is external text: control characters are escaped by the shared
        inbound screen (``inbound_text.screen_line``) so a quote cannot hide what
        it contains, and anything past :data:`_SHOWN_LINE_CHARS` is counted.
        """
        if self.line is None:
            return ""
        shown = screen_line(self.line).text
        if len(shown) <= _SHOWN_LINE_CHARS:
            return shown
        hidden = len(shown) - _SHOWN_LINE_CHARS
        return f"{shown[:_SHOWN_LINE_CHARS]}… [{hidden} more characters not shown]"

    def describe(self) -> str:
        """One clause naming who wrote the baseline AND the line that says so.

        Shaped to follow "it is …", so every caller states the finding in the
        same words and none of them has to re-derive which line was read.
        """
        if self.producer == "platterpus":
            return (
                "one of Platterpus's own EAC-layout exports, not a log Exact Audio "
                f"Copy wrote: its first line reads `{self.shown_line}`"
            )
        if self.producer == "exact_audio_copy":
            return (
                "a log Exact Audio Copy wrote, as its first line states "
                f"(`{self.shown_line}`); that is what the log says, not proof, "
                "since EAC's own log checksum is not checked here"
            )
        if self.line is None:
            return (
                "not determined to be Exact Audio Copy's log: it has no non-blank "
                "line to name the program that wrote it"
            )
        return (
            "not determined to be Exact Audio Copy's log: its first line, "
            f"`{self.shown_line}`, names neither Exact Audio Copy nor Platterpus"
        )


def identify_baseline(text: str) -> BaselineProducer:
    """Who wrote this baseline log, by the one producer predicate. Never raises.

    Delegates both halves to ``parsers/eac_log``: the answer to
    ``eac_log_producer`` and the line to ``eac_log_producer_line``, the same line
    the answer was read from. A second "is this ours?" rule kept here could
    drift from the parser's banner table, which is exactly how the old wording
    of our banner was once filed as EAC's own log.
    """
    return BaselineProducer(
        producer=eac_log_producer(text), line=eac_log_producer_line(text)
    )


@dataclass(frozen=True)
class TrackParity:
    """One track's baseline vs candidate Copy CRC."""

    number: int
    baseline_crc: str
    candidate_crc: str  # "" means the candidate has no CRC for this track

    @property
    def ok(self) -> bool:
        return bool(self.candidate_crc) and self.candidate_crc == self.baseline_crc


@dataclass(frozen=True)
class ParityReport:
    """The result of comparing a candidate rip log to a baseline."""

    tracks: tuple[TrackParity, ...]
    extra: tuple[int, ...] = ()  # track numbers in the candidate but not baseline
    #: Who wrote the baseline (:func:`identify_baseline`). The default is "not
    #: determined", never "EAC": a report built without asking is not evidence
    #: that EAC wrote anything.
    baseline: BaselineProducer = BaselineProducer(producer=None, line=None)

    @property
    def ok(self) -> bool:
        """True only when every baseline track matched, nothing is extra, and the
        baseline is not one of our own exports.

        An empty baseline (nothing parsed) is never parity — we can't claim a
        match against nothing. Nor is a baseline Platterpus wrote: every track of
        a rip matches our own export of that rip by construction, so the per-track
        rows can all read PASS while the comparison proves nothing. Requiring the
        baseline's PRODUCER as well as its CRCs is what stops this verdict being
        satisfied by the wrong thing, for every caller, including one that forgets
        to refuse up front (``scripts/eac_parity.py`` refuses before comparing;
        this is the backstop that needs no cooperation from it).
        """
        return (
            bool(self.tracks)
            and all(t.ok for t in self.tracks)
            and not self.extra
            and not self.baseline.is_ours
        )

    @property
    def matched(self) -> int:
        return sum(1 for t in self.tracks if t.ok)

    @property
    def total(self) -> int:
        return len(self.tracks)


def compare_logs(baseline_text: str, candidate_text: str) -> ParityReport:
    """Compare a candidate rip log against a baseline by per-track Copy CRC.

    The report also records who wrote the baseline (:attr:`ParityReport.baseline`),
    so its verdict can refuse our own export and its caller can say whether a
    match is parity with EAC or only with whatever log it was handed.
    """
    base = track_copy_crcs(baseline_text)
    cand = track_copy_crcs(candidate_text)
    tracks = tuple(TrackParity(n, base[n], cand.get(n, "")) for n in sorted(base))
    extra = tuple(sorted(set(cand) - set(base)))
    return ParityReport(
        tracks=tracks, extra=extra, baseline=identify_baseline(baseline_text)
    )
