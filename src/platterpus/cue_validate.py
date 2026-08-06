"""Check the ``.cue`` sheet the ripper wrote — it is external input, and we ship it.

Every other artifact a rip produces is either ours (the EAC-layout log, the JSON
report) or is checked (the ripper's log, against its own checksum). The ``.cue``
was neither: cyanrip writes it, we copy it into the album folder and hand it to
the user, and **nothing in Platterpus had ever read a single line of it**. A cue
sheet is what a burner, a tagger and a tracker read to reconstruct the disc, so
an error in it is an error in the archival record.

**The rip that made this necessary** (Bazzite + Pioneer BDR-209D, 2026-08-05 —
The Police, *Every Breath You Take: The Classics*, 14 tracks, app v0.6.4b11,
ripper ``0.9.4-rc1+platterpus.5-beta.5``). Two things were wrong in the cue and
nothing noticed either:

1. **9 of 14 ``ISRC`` lines were missing — exactly the 9 tracks that carry an
   ``INDEX 00`` pre-gap marker** (set equality, verified). We sent all 14 via
   ``-t "N=…:isrc=…"``; the ripper's own log records all 14; the FLAC tags carry
   all 14. Only the cue drops them, in the branch of its writer that emits
   ``INDEX 00``. That is a fork bug — but *we had every fact needed to detect it*
   and threw the chance away, which is the part that is ours to fix.

   The **committed artifact proves the same defect independently**: in
   ``output_reference/cyanrip_fork_flac/cyanrip_fork_police_classics.cue`` (an
   older ``beta.1`` rip) 13 of 14 ISRCs are missing, and the 13 missing are
   exactly the 13 tracks carrying ``INDEX 00``. Two rips, two different counts,
   one signature. ``tests/test_cue_validate.py`` reads that file rather than
   restating its numbers.

2. **The album ``TITLE`` reads "Every Breath You Take∶ The Classics"** — U+2236
   RATIO, not a colon. That one is *ours*: cyanrip's ``-a``/``-t`` are
   colon-delimited with no escape syntax, so
   :func:`~platterpus.adapters.cyanrip_backend._escape_meta_value` substitutes
   the visually-identical U+2236 to get the value past the parser. We already
   restore the real colon in **two** places — the FLAC tags (via metaflac) and
   the EAC-layout log (via ``eac_log_export._real_colons``) — and never in the
   cue. So the one artifact that describes the whole disc shows a character the
   album title does not contain.

**This module is pure**: text in, findings out. No filesystem, no subprocess, no
Qt — so it is fully testable, and so it can be called from a GUI slot without the
"never block the GUI thread" question arising at all. Like every parser of
external output here it **never raises** (CLAUDE.md → *Subprocess output
parsing*); a malformed cue is *reported* as malformed, because an auditor that
dies on a bad artifact is useless exactly when it is needed.

Not a duplicate of :func:`platterpus.ctdb.toc.parse_cue_index01_sectors`: that
one extracts ``INDEX 01`` start sectors to build a TOC for CTDB and deliberately
ignores everything else. This one reads the whole sheet in order to *judge* it.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from platterpus.safe_int import int_or_none

log = logging.getLogger(__name__)

# --- Finding levels ---------------------------------------------------------
#
# Deliberately the same three strings `rip_audit` uses, declared here rather than
# imported from it. This module sits *below* the auditor — the auditor calls us —
# and importing upward would make a pure text validator depend on the module that
# walks a library of files. The cost of a second copy is drift, so the drift is
# checked mechanically instead of trusted: `test_cue_validate.py` asserts all
# three constants are identical to `rip_audit`'s, and that it compared all three.
LEVEL_OK: str = "ok"
LEVEL_NOTE: str = "note"
LEVEL_WARN: str = "warn"

#: The RATIO character cyanrip's tag parser forces us to substitute for ``:``.
#: Kept as a named constant so the reason travels with the character — a bare
#: ``"∶"`` in a comparison is indistinguishable from a typo. Pinned equal to
#: ``cyanrip_backend._COLON_SUBSTITUTE`` by test, same reasoning as the levels.
COLON_SUBSTITUTE: str = "∶"

#: How many free-text items (a mismatch description, a line reference) a single
#: finding names before it elides the rest. The elision is always *counted* in
#: the text — a silent truncation reads as completeness (CLAUDE.md →
#: *Diagnostic completeness*).
MAX_NAMED_ITEMS: int = 8

#: How many TRACK NUMBERS a finding names, which is deliberately far higher.
#: A Red Book CD holds at most 99 tracks, so this never elides for any real
#: disc — and it must not: "9 of 14 ISRCs are missing" is only actionable if the
#: reader learns *which* 9, and that set being exactly the pre-gap tracks is the
#: whole diagnosis. The bound exists only so a corrupt cue claiming thousands of
#: tracks cannot produce a finding nobody can read.
MAX_NAMED_TRACKS: int = 99


# --- The parsed shape -------------------------------------------------------


@dataclass
class CueMetaValue:
    """One metadata value read out of the cue, with where it came from.

    **``FILE`` values are deliberately NOT collected here**, and that is a
    correctness requirement rather than tidiness. A ``FILE`` line names a real
    path on disk, and cyanrip sanitises ``:`` out of filenames the same way it
    sanitises tag values — so a U+2236 in a ``FILE`` line is *correct* and
    "fixing" it would name a file that does not exist. Keeping paths structurally
    out of the metadata list means the colon check cannot flag one by accident;
    a filter applied at check time could be forgotten, a separate list cannot be.
    """

    field_name: str
    value: str
    line_number: int
    #: Track this value belongs to, or ``None`` for a disc-level value.
    track_number: int | None = None


@dataclass
class CueTrack:
    """One ``TRACK`` block. Every field is best-effort; absence is empty/None."""

    number: int | None = None
    title: str = ""
    performer: str = ""
    isrc: str = ""
    #: Raw ``MM:SS:FF`` text of the pre-gap marker, empty when there is none.
    index00: str = ""
    index01: str = ""
    #: The ``FILE`` this track's audio lives in, as written in the cue.
    file: str = ""
    line_number: int = 0


@dataclass
class CueSheet:
    """A whole cue sheet, parsed tolerantly. Unknown lines are ignored."""

    album_title: str = ""
    album_performer: str = ""
    tracks: list[CueTrack] = field(default_factory=list)
    #: Every ``FILE`` value, in order. Paths — never colon-checked.
    files: list[str] = field(default_factory=list)
    #: Every metadata value, for the colon check and its floor.
    metadata: list[CueMetaValue] = field(default_factory=list)
    lines_seen: int = 0
    #: How many lines this parser actually recognised. Zero recognised lines in
    #: a non-empty file means "this is not a cue sheet", which is a different
    #: answer from "this cue sheet is wrong".
    lines_understood: int = 0


@dataclass(frozen=True)
class CueFinding:
    """One thing worth saying about one cue sheet.

    ``code`` is the stable machine handle (tests and future UI match on it);
    ``text`` is the sentence a human reads. Both, because a finding that only has
    prose cannot be asserted on without pinning wording, and one that only has a
    code cannot be shown to anybody.
    """

    level: str
    code: str
    text: str


@dataclass(frozen=True)
class ExpectedCue:
    """What we know about this disc *independently of the cue*.

    Everything here comes from a different source than the file being judged —
    the argv we sent, the ripper's log, the metadata we resolved — because a
    check of an artifact against itself is consistent, not verified (CLAUDE.md →
    *assert against the source artifact, not against another run*).

    Every field is optional, and an absent field makes its check report
    **not determined** rather than pass. A check that can be satisfied by having
    nothing to compare is decoration.
    """

    #: Track number → the ISRC we handed the ripper on the command line.
    isrcs: Mapping[int, str] = field(default_factory=dict)
    #: Track number → pre-gap length in CD frames, from the ripper's own log.
    #: Only include tracks whose pre-gap was actually *measured*: an "unknown"
    #: pre-gap must not become an accusation in either direction.
    pregap_frames: Mapping[int, int] = field(default_factory=dict)
    #: Track number → the true title (real colon), for the repair message.
    track_titles: Mapping[int, str] = field(default_factory=dict)
    #: The true album title, with its real colon.
    album_title: str | None = None
    #: How many tracks this cue should describe. ``None`` when the caller cannot
    #: say — e.g. a cancelled rip, where a short cue is expected, not wrong.
    track_count: int | None = None
    #: The tracks the ripper was actually told to rip (cyanrip ``-l``), or
    #: ``None`` for a whole-disc rip.
    #:
    #: **Why this exists.** Platterpus lets the user tick individual tracks, and
    #: that selection becomes ``-l 3,5`` — but ``-t`` tag arguments are built
    #: from the *metadata*, so we still send an ISRC for all fourteen tracks of a
    #: two-track rip. Without this field the ISRC check compared a 14-entry
    #: expectation against a 2-track cue and produced twelve warnings about a
    #: rip that did exactly what the user asked. A checker that cries wolf on a
    #: shipped feature is one the reader learns to skip, which costs more than
    #: not having it (measured against the committed reference report,
    #: 2026-08-06 review).
    ripped_tracks: frozenset[int] | None = None


# --- The parser -------------------------------------------------------------
#
# Named groups throughout, never column indices (CLAUDE.md → *Subprocess output
# parsing*): a cue writer that adds a field or changes its spacing must not
# silently shift what we read.

_RE_REM = re.compile(r"^\s*REM\s+(?P<key>[A-Za-z0-9_]{1,64})\s+(?P<value>.*\S)\s*$")
_RE_TITLE = re.compile(r"^\s*TITLE\s+(?P<value>.*\S)\s*$")
_RE_PERFORMER = re.compile(r"^\s*PERFORMER\s+(?P<value>.*\S)\s*$")
# A FILE value is quoted when it contains spaces, which for a track-per-file rip
# is almost always. The optional trailing word is the format (WAVE/MP3/BINARY).
_RE_FILE = re.compile(
    r"^\s*FILE\s+(?P<value>\"[^\"]*\"|\S+)(?:\s+(?P<format>\S+))?\s*$"
)
_RE_TRACK = re.compile(r"^\s*TRACK\s+(?P<number>\d{1,6})\s+(?P<mode>\S+)\s*$")
_RE_ISRC = re.compile(r"^\s*ISRC\s+(?P<isrc>\S{1,32})\s*$")
_RE_INDEX = re.compile(
    r"^\s*INDEX\s+(?P<index>\d{1,2})\s+(?P<time>\d{1,6}:\d{2}:\d{2})\s*$"
)


def _unquote(value: str) -> str:
    """Strip the surrounding double quotes a cue uses around any value."""
    if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    return value


def parse_cue(cue_text: str) -> CueSheet:
    """Parse a cue sheet tolerantly. **Never raises**, on any input.

    Unknown lines are ignored rather than treated as errors — cue sheets carry
    writer-specific ``REM`` lines, and a validator that rejected anything it did
    not recognise would fail on every cue but ours.

    The one shape worth explaining is the **gap-appended layout** cyanrip writes,
    where a track's pre-gap belongs to the *previous* file::

        TRACK 02 AUDIO
          TITLE "…"
          INDEX 00 03:11:02        <- still inside track 1's FILE
        FILE "02 - ….flac" WAVE    <- the file changes mid-track
          INDEX 01 00:00:00

    So a ``FILE`` line can appear *inside* a ``TRACK`` block, and when it does it
    names the file that track's audio actually lives in. That is why a ``FILE``
    seen while a track is open re-points the open track, rather than only seeding
    the next one.
    """
    sheet = CueSheet()
    try:
        lines = cue_text.splitlines()
    except (AttributeError, TypeError):  # not a string at all
        log.warning("cue text is not a string; nothing parsed")
        return sheet

    current: CueTrack | None = None
    current_file = ""
    for number, raw in enumerate(lines, start=1):
        sheet.lines_seen += 1

        match_track = _RE_TRACK.match(raw)
        if match_track:
            sheet.lines_understood += 1
            current = CueTrack(
                number=int_or_none(match_track["number"], field="cue TRACK number"),
                file=current_file,
                line_number=number,
            )
            sheet.tracks.append(current)
            continue

        match_file = _RE_FILE.match(raw)
        if match_file:
            sheet.lines_understood += 1
            current_file = _unquote(match_file["value"])
            sheet.files.append(current_file)
            if current is not None:
                # Gap-appended layout: this FILE is the open track's own audio.
                current.file = current_file
            continue

        match_index = _RE_INDEX.match(raw)
        if match_index and current is not None:
            sheet.lines_understood += 1
            if match_index["index"].lstrip("0") == "":  # "00" / "0"
                current.index00 = match_index["time"]
            elif match_index["index"].lstrip("0") == "1":
                current.index01 = match_index["time"]
            continue

        match_isrc = _RE_ISRC.match(raw)
        if match_isrc and current is not None:
            sheet.lines_understood += 1
            current.isrc = match_isrc["isrc"]
            continue

        match_title = _RE_TITLE.match(raw)
        if match_title:
            sheet.lines_understood += 1
            value = _unquote(match_title["value"])
            if current is None:
                sheet.album_title = value
            else:
                current.title = value
            sheet.metadata.append(
                CueMetaValue(
                    "TITLE", value, number, current.number if current else None
                )
            )
            continue

        match_performer = _RE_PERFORMER.match(raw)
        if match_performer:
            sheet.lines_understood += 1
            value = _unquote(match_performer["value"])
            if current is None:
                sheet.album_performer = value
            else:
                current.performer = value
            sheet.metadata.append(
                CueMetaValue(
                    "PERFORMER", value, number, current.number if current else None
                )
            )
            continue

        match_rem = _RE_REM.match(raw)
        if match_rem:
            sheet.lines_understood += 1
            sheet.metadata.append(
                CueMetaValue(
                    f"REM {match_rem['key']}",
                    _unquote(match_rem["value"]),
                    number,
                    current.number if current else None,
                )
            )
            continue

    return sheet


# --- Reading back what we SENT ---------------------------------------------


def _split_meta_blob(blob: str) -> dict[str, str]:
    """Split one ``-a``/``-t`` blob into its ``key=value`` pairs.

    Splitting on ``:`` is safe *because of* the escaping this module exists to
    complain about: a real colon can never appear in one of these blobs — it was
    turned into U+2236 before the argv was built — so every ``:`` here is a
    genuine separator. Backslash escapes (``\\``, ``=``, ``'``) are undone, the
    inverse of ``cyanrip_backend._escape_meta_value``.

    Never raises: a malformed blob yields whatever pairs did parse.
    """
    pairs: dict[str, str] = {}
    for chunk in blob.split(":"):
        if "=" not in chunk:
            continue
        key, _, value = chunk.partition("=")
        key = key.strip().lower()
        if not key:
            continue
        pairs[key] = re.sub(r"\\(.)", r"\1", value)
    return pairs


def sent_track_metadata(argv: Sequence[str]) -> dict[int, dict[str, str]]:
    """Track number → the tag pairs we handed the ripper in its ``-t`` args.

    This is the *outbound* half of the seam read back out of the report, which is
    what makes the ISRC check an independent comparison rather than the cue being
    checked against itself.
    """
    out: dict[int, dict[str, str]] = {}
    tokens = [str(part) for part in argv]
    for position, token in enumerate(tokens):
        if token != "-t" or position + 1 >= len(tokens):
            continue
        blob = tokens[position + 1]
        number_text, _, rest = blob.partition("=")
        number = int_or_none(number_text.strip(), field="cyanrip -t track number")
        if number is None:
            continue
        out[number] = _split_meta_blob(rest)
    return out


def sent_track_selection(argv: Sequence[str]) -> frozenset[int] | None:
    """The tracks cyanrip was told to rip (``-l 3,5``), or ``None`` for all.

    ``None`` means "whole disc" **and also** "we could not read the selection",
    and those collapse deliberately: both leave every check at its whole-disc
    behaviour, which is the conservative direction. Narrowing on a selection we
    misread would silently stop checking tracks that *were* ripped — a checker
    quietly doing less is the failure mode this codebase keeps finding, so an
    unparseable list refuses to narrow rather than guessing.

    Only plain comma-separated integers are accepted for that reason. Our own
    argv builder emits exactly that (``",".join(str(n))`` in
    :mod:`~platterpus.adapters.cyanrip_backend`); if cyanrip ever grows a range
    syntax we have not measured, a token like ``3-7`` falls through to ``None``
    instead of being read as the number 3.

    Never raises.
    """
    tokens = [str(part) for part in argv]
    for position, token in enumerate(tokens):
        if token != "-l" or position + 1 >= len(tokens):
            continue
        parts = [chunk.strip() for chunk in tokens[position + 1].split(",")]
        numbers = [
            int_or_none(chunk, field="cyanrip -l track number") for chunk in parts
        ]
        if not numbers or any(n is None for n in numbers):
            log.warning(
                "could not read cyanrip's -l track selection %r; treating this "
                "rip as a whole-disc rip for the cue check",
                tokens[position + 1],
            )
            return None
        return frozenset(n for n in numbers if n is not None)
    return None


def sent_album_metadata(argv: Sequence[str]) -> dict[str, str]:
    """The tag pairs we handed the ripper in its ``-a`` argument."""
    tokens = [str(part) for part in argv]
    for position, token in enumerate(tokens):
        if token == "-a" and position + 1 < len(tokens):
            return _split_meta_blob(tokens[position + 1])
    return {}


# --- The consumer-side repair ----------------------------------------------


def restore_metadata_colons(cue_text: str) -> tuple[str, int]:
    """Put the real ``:`` back into cue *metadata*, never into ``FILE`` paths.

    Returns ``(new_text, substitutions)`` so the caller can log how many
    characters it changed — a repair that reports "done" without saying what it
    did is not diagnosable.

    **Where the real fix belongs.** This is a consumer-side repair of a problem
    created at the seam: cyanrip's ``-a``/``-t`` are colon-delimited with no
    escape syntax, so we cannot pass a title containing a colon at all and
    substitute U+2236 instead (see
    :func:`~platterpus.adapters.cyanrip_backend._escape_meta_value`). The
    durable fix is an escape syntax in the ripper — asked for through the
    handshake — after which every artifact carries the true colon with no
    post-processing anywhere. Until then we un-substitute in each artifact we
    render, and this is the cue's turn; the FLAC tags and the EAC-layout log
    already do it.

    **NOT YET WIRED — this function has no production call site** (verified by
    grep, 2026-08-06 review). The shipped cue still carries the artefact; today
    only the *audit* reports it, via
    :func:`platterpus.rip_audit._audit_cue_integrity`. Wiring it is not a
    one-liner and that is why it is called out here rather than assumed: the
    repair rewrites the file, and :func:`platterpus.report_artifacts.build_artifact`
    records the ``sha256`` of the cue's **bytes on disk**. Run the repair after
    the report is built and the report's hash describes a file that no longer
    exists — so the call has to land in the post-rip sequence *before* the
    artifacts block is assembled, not wherever is convenient.

    **``FILE`` lines are never touched.** They name real paths, and cyanrip
    applies the same substitution when sanitising a filename — so the U+2236 in
    a ``FILE`` line is what the file on disk is actually called. Rewriting it
    would produce a cue that points at a file that does not exist, turning a
    cosmetic blemish into a broken sheet.

    Never raises; non-string input comes back unchanged with zero changes.
    """
    try:
        lines = cue_text.splitlines(keepends=True)
    except (AttributeError, TypeError):
        log.warning("cue text is not a string; no colons restored")
        return cue_text, 0

    changed = 0
    out: list[str] = []
    for raw in lines:
        if _RE_FILE.match(raw):
            # Redundant *today* — none of the three metadata patterns below can
            # match a FILE line — and kept deliberately anyway, as an explicit
            # statement of the rule. If the metadata match is ever broadened (a
            # SONGWRITER line, a catch-all), this is what stops the broadening
            # from silently starting to rewrite paths. Cheap belt, expensive
            # failure: a rewritten FILE line points the cue at a file that does
            # not exist.
            out.append(raw)
            continue
        if _RE_TITLE.match(raw) or _RE_PERFORMER.match(raw) or _RE_REM.match(raw):
            hits = raw.count(COLON_SUBSTITUTE)
            if hits:
                changed += hits
                raw = raw.replace(COLON_SUBSTITUTE, ":")
        out.append(raw)
    return "".join(out), changed


# --- The checks -------------------------------------------------------------


def _named(items: Sequence[str], limit: int = MAX_NAMED_ITEMS) -> str:
    """Join up to ``limit`` items, always counting any elision."""
    shown = ", ".join(items[:limit])
    if len(items) > limit:
        shown += f" (and {len(items) - limit} more)"
    return shown


def _named_tracks(numbers: Sequence[int]) -> str:
    """Name track numbers — all of them, for any disc that can physically exist."""
    return _named([str(n) for n in numbers], MAX_NAMED_TRACKS)


def _check_isrcs(sheet: CueSheet, expected: ExpectedCue) -> list[CueFinding]:
    """Did every ISRC we sent come back on its track in the cue?

    ISRCs are the disc's per-track identifiers; a tracker or tagger reading the
    cue is entitled to them, and we know exactly which ones we supplied.
    """
    # Narrow to the tracks that were actually ripped BEFORE testing for
    # emptiness. `-t` arguments come from the metadata, not from the selection,
    # so a two-track rip still sends fourteen ISRCs — and the cue is only ever
    # going to carry the two. Expecting the other twelve is expecting the ripper
    # to have ignored the `-l` we gave it.
    wanted: Mapping[int, str] = expected.isrcs
    if expected.ripped_tracks is not None:
        wanted = {
            n: v for n, v in expected.isrcs.items() if n in expected.ripped_tracks
        }

    if not wanted:
        # Not determined, never "ok". A rip of an unknown disc sends no ISRCs,
        # and so does an older report that did not record its argv — in both
        # cases there is nothing to round-trip, which is a different answer from
        # "the round-trip succeeded". A selection that shares no track with the
        # ISRCs we sent lands here too, for the same reason: nothing comparable.
        return [
            CueFinding(
                LEVEL_NOTE,
                "cue_isrc_not_determined",
                "cue sheet — ISRC round-trip not determined: this rip recorded no "
                "ISRCs sent to the ripper for any track it ripped, so there is "
                "nothing to check the cue against (an unknown-disc rip, or a "
                "report from before the argv was recorded)",
            )
        ]

    by_number = {t.number: t for t in sheet.tracks if t.number is not None}
    missing: list[int] = []
    mismatched: list[str] = []
    absent_track: list[int] = []
    for number, isrc in sorted(wanted.items()):
        track = by_number.get(number)
        if track is None:
            absent_track.append(number)
        elif not track.isrc:
            missing.append(number)
        elif track.isrc.strip().upper() != isrc.strip().upper():
            mismatched.append(f"track {number}: cue {track.isrc} vs sent {isrc}")

    findings: list[CueFinding] = []
    if missing:
        # The signature sentence. On both measured rips the dropped ISRCs were
        # *exactly* the tracks carrying an INDEX 00 marker, which points a bug
        # report straight at the cue writer's pre-gap branch instead of leaving
        # the maintainer to notice the correlation by eye.
        marked = {t.number for t in sheet.tracks if t.index00 and t.number is not None}
        correlation = ""
        if marked and set(missing) == marked:
            correlation = (
                " — exactly the tracks carrying an INDEX 00 pre-gap marker, which "
                "is the signature of the ripper's cue writer dropping ISRC in its "
                "pre-gap branch (the ripper's own log and the FLAC tags keep them)"
            )
        findings.append(
            CueFinding(
                LEVEL_WARN,
                "cue_isrc_missing",
                f"cue sheet — {len(missing)} of {len(wanted)} ISRC(s) we "
                f"sent are missing from the cue: track(s) "
                f"{_named_tracks(missing)}{correlation}",
            )
        )
    if absent_track:
        findings.append(
            CueFinding(
                LEVEL_WARN,
                "cue_isrc_track_absent",
                f"cue sheet — {len(absent_track)} track(s) we sent an ISRC for do "
                f"not appear in the cue at all: "
                f"{_named_tracks(absent_track)}",
            )
        )
    if mismatched:
        findings.append(
            CueFinding(
                LEVEL_WARN,
                "cue_isrc_mismatch",
                f"cue sheet — {len(mismatched)} ISRC(s) differ from what we sent: "
                f"{_named(mismatched)}",
            )
        )
    if not findings:
        findings.append(
            CueFinding(
                LEVEL_OK,
                "cue_isrc_ok",
                f"cue sheet — all {len(wanted)} ISRC(s) we sent round-tripped "
                "into the cue",
            )
        )
    return findings


def _check_pregaps(sheet: CueSheet, expected: ExpectedCue) -> list[CueFinding]:
    """Does each ``INDEX 00`` marker agree with the measured pre-gap length?

    **Track 1 is exempt, and the reason is physical.** A track's ``INDEX 00``
    says "the pre-gap starts here, appended to the *previous* track's file".
    Track 1 has no previous track — its pre-gap is the disc's lead-in (150
    frames on every CD ever pressed), which lives before the first sector of
    audio and is not part of any file. So a cue that is entirely correct still
    never writes ``INDEX 00`` for track 1, and a checker that did not know that
    would report every disc in the world as broken.
    """
    if not expected.pregap_frames:
        return [
            CueFinding(
                LEVEL_NOTE,
                "cue_pregap_not_determined",
                "cue sheet — pre-gap markers not determined: no measured pre-gap "
                "length was recorded for any track (pre-gap rows are fork-only, so "
                "a rip made with unmodified upstream cyanrip cannot report them)",
            )
        ]

    by_number = {t.number: t for t in sheet.tracks if t.number is not None}
    missing_marker: list[int] = []
    spurious_marker: list[int] = []
    examined = 0
    for number, frames in sorted(expected.pregap_frames.items()):
        if number == 1:
            continue  # the lead-in — see the docstring
        if expected.ripped_tracks is not None and (
            number not in expected.ripped_tracks
            or number - 1 not in expected.ripped_tracks
        ):
            # A partial rip. An `INDEX 00` says "the pre-gap is appended to the
            # PREVIOUS track's file" — so it can only be written when that file
            # exists. On a selection of tracks 3 and 5, track 5's gap has
            # nowhere to go (track 4 was not ripped), and its absent marker is
            # correct rather than a defect. Judging it would accuse the ripper
            # of obeying the `-l` we sent it.
            continue
        track = by_number.get(number)
        if track is None:
            continue  # the structure check reports a track the cue omits
        examined += 1
        if frames > 0 and not track.index00:
            missing_marker.append(number)
        elif frames == 0 and track.index00:
            spurious_marker.append(number)

    if examined == 0:
        # The floor. Everything we had was track 1, or named tracks the cue does
        # not contain — either way nothing was actually compared, and a silent
        # "ok" here would be the check passing by having nothing to do.
        return [
            CueFinding(
                LEVEL_NOTE,
                "cue_pregap_not_determined",
                "cue sheet — pre-gap markers not determined: no track in the cue "
                "could be matched against a measured pre-gap length",
            )
        ]

    findings: list[CueFinding] = []
    if missing_marker:
        findings.append(
            CueFinding(
                LEVEL_WARN,
                "cue_pregap_marker_missing",
                f"cue sheet — {len(missing_marker)} track(s) have a measured pre-gap "
                "but no INDEX 00 marker in the cue, so the gap audio is not "
                f"attributed to the previous track: {_named_tracks(missing_marker)}",
            )
        )
    if spurious_marker:
        findings.append(
            CueFinding(
                LEVEL_WARN,
                "cue_pregap_marker_spurious",
                f"cue sheet — {len(spurious_marker)} track(s) carry an INDEX 00 "
                "marker although their measured pre-gap is 0 frames: "
                f"{_named_tracks(spurious_marker)}",
            )
        )
    if not findings:
        findings.append(
            CueFinding(
                LEVEL_OK,
                "cue_pregap_ok",
                f"cue sheet — INDEX 00 markers agree with the measured pre-gap "
                f"lengths on all {examined} track(s) checked (track 1's lead-in "
                "pre-gap is never marked, by design)",
            )
        )
    return findings


def _check_colon_fidelity(sheet: CueSheet, expected: ExpectedCue) -> list[CueFinding]:
    """Is any metadata value still carrying our U+2236 escaping artefact?

    ``FILE`` lines cannot reach this check: :func:`parse_cue` keeps paths in a
    separate list precisely so that the correct U+2236 in a filename can never be
    mistaken for the incorrect one in a title.
    """
    if not sheet.metadata:
        return [
            CueFinding(
                LEVEL_NOTE,
                "cue_colon_not_determined",
                "cue sheet — colon fidelity not determined: the cue carries no "
                "metadata lines (TITLE/PERFORMER/REM) to check",
            )
        ]

    offenders = [m for m in sheet.metadata if COLON_SUBSTITUTE in m.value]
    if not offenders:
        return [
            CueFinding(
                LEVEL_OK,
                "cue_colon_ok",
                f"cue sheet — all {len(sheet.metadata)} metadata value(s) carry real "
                "text, with no U+2236 colon substitute left in them",
            )
        ]

    truth = ""
    if expected.album_title and any(
        m.field_name == "TITLE" and m.track_number is None for m in offenders
    ):
        truth = f' The album title is actually "{expected.album_title}".'
    elif expected.track_titles:
        named = [
            f'track {m.track_number} is actually "{expected.track_titles[m.track_number]}"'
            for m in offenders
            if m.track_number is not None and m.track_number in expected.track_titles
        ]
        if named:
            truth = f" {_named(named)}."

    where = _named(
        [f"line {m.line_number} ({m.field_name})" for m in offenders],
    )
    return [
        CueFinding(
            LEVEL_WARN,
            "cue_colon_artefact",
            f"cue sheet — {len(offenders)} metadata value(s) still contain U+2236 "
            f"(the RATIO lookalike) where the real text has a colon: {where}. That "
            "character is Platterpus's own workaround for cyanrip's colon-delimited "
            "-a/-t arguments leaking into the shipped cue; the FLAC tags and the "
            f"EAC-style log already show the true colon, and this file does not.{truth}",
        )
    ]


def _check_structure(sheet: CueSheet, expected: ExpectedCue) -> list[CueFinding]:
    """Is this a well-formed sheet: numbered from 1, contiguous, all indexed?"""
    findings: list[CueFinding] = []

    if not sheet.tracks:
        if sheet.lines_understood == 0:
            return [
                CueFinding(
                    LEVEL_NOTE,
                    "cue_unrecognised",
                    f"cue sheet — not determined: none of the {sheet.lines_seen} "
                    "line(s) in this file look like cue-sheet syntax, so it was not "
                    "judged (it may not be a cue sheet at all)",
                )
            ]
        return [
            CueFinding(
                LEVEL_WARN,
                "cue_no_tracks",
                f"cue sheet — the file parses as a cue ({sheet.lines_understood} "
                "recognised line(s)) but declares no TRACK at all, so nothing can "
                "reconstruct the disc from it",
            )
        ]

    numbers = [t.number for t in sheet.tracks]
    unnumbered = sum(1 for n in numbers if n is None)
    if unnumbered:
        findings.append(
            CueFinding(
                LEVEL_WARN,
                "cue_track_unnumbered",
                f"cue sheet — {unnumbered} TRACK line(s) carry no readable number",
            )
        )
    real = [n for n in numbers if n is not None]
    if real and real != list(range(1, len(real) + 1)):
        if expected.ripped_tracks is not None:
            # A partial rip legitimately has non-contiguous numbers, and which
            # convention cyanrip uses — original numbers, or renumbered from 1 —
            # is something Platterpus has never measured off a real `-l` rip.
            # So this is reported as NOT DETERMINED rather than guessed at in
            # either direction: an accusation we cannot support is worse than an
            # honest gap, and a pass we cannot support is worse still.
            findings.append(
                CueFinding(
                    LEVEL_NOTE,
                    "cue_track_numbering_not_determined",
                    "cue sheet — track numbering not checked: this rip was "
                    "restricted to selected tracks, so the cue describes a "
                    f"subset ({_named_tracks(real)}) and non-contiguous numbers "
                    "are expected rather than wrong",
                )
            )
        else:
            findings.append(
                CueFinding(
                    LEVEL_WARN,
                    "cue_track_numbering",
                    "cue sheet — track numbers are not 1..N in order: "
                    f"{_named_tracks(real)}",
                )
            )

    no_index01 = [str(t.number) for t in sheet.tracks if not t.index01]
    if no_index01:
        findings.append(
            CueFinding(
                LEVEL_WARN,
                "cue_missing_index01",
                f"cue sheet — {len(no_index01)} track(s) have no INDEX 01, so their "
                f"start point is undefined: track(s) {_named(no_index01, MAX_NAMED_TRACKS)}",
            )
        )

    if expected.track_count is None:
        findings.append(
            CueFinding(
                LEVEL_NOTE,
                "cue_track_count_not_determined",
                f"cue sheet — the cue describes {len(sheet.tracks)} track(s); how "
                "many it should describe was not determined for this rip, so the "
                "count was not checked",
            )
        )
    elif len(sheet.tracks) != expected.track_count:
        findings.append(
            CueFinding(
                LEVEL_WARN,
                "cue_track_count",
                f"cue sheet — the cue describes {len(sheet.tracks)} track(s) but this "
                f"rip produced {expected.track_count}",
            )
        )

    if not findings:
        findings.append(
            CueFinding(
                LEVEL_OK,
                "cue_structure_ok",
                f"cue sheet — well formed: {len(sheet.tracks)} track(s), numbered "
                "1..N in order, each with an INDEX 01",
            )
        )
    return findings


def validate_cue(cue_text: str, *, expected: ExpectedCue) -> list[CueFinding]:
    """Judge one cue sheet against what we independently know. **Never raises.**

    Always returns at least one finding: "the cue was checked and had nothing
    wrong" and "the cue was never checked" must not look the same to a reader.
    """
    try:
        if not cue_text or not cue_text.strip():
            return [
                CueFinding(
                    LEVEL_NOTE,
                    "cue_empty",
                    "cue sheet — not determined: the cue is empty, so none of its "
                    "contents could be checked",
                )
            ]
        sheet = parse_cue(cue_text)
        findings: list[CueFinding] = []
        findings += _check_structure(sheet, expected)
        findings += _check_isrcs(sheet, expected)
        findings += _check_pregaps(sheet, expected)
        findings += _check_colon_fidelity(sheet, expected)
        return findings
    except Exception as exc:  # noqa: BLE001 — a validator must not kill its caller
        # Same contract as every parser here: external input can be anything, and
        # a crash in the checker would take down the rip report it is embedded in.
        log.exception("cue validation raised")
        return [
            CueFinding(
                LEVEL_NOTE,
                "cue_check_failed",
                f"cue sheet — not determined: the cue check itself failed ({exc})",
            )
        ]
