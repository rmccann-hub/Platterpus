"""Adapter over MusicBrainz queries.

`MusicBrainzClient` is the ABC; `MusicBrainzNgsImpl` is the v1
concrete implementation backed by the `musicbrainzngs` Python library.
A future `RequestsJsonImpl` could implement the same ABC by hitting
MB's JSON REST endpoint directly with `requests` — see PLANNING.md §6
and CLAUDE.md Critical Rule #1.

The adapter exists for two reasons:
1. `musicbrainzngs` hasn't released since 2020-01-11 — wrapping it
   isolates the GUI from its eventual retirement.
2. The brief's Critical Rule #5 — every MusicBrainz lookup goes
   through this client; the GUI does the lookup itself and feeds the
   result to the ripper, so the ripper's own interactive prompt never
   surfaces to the user.

The user-agent is mandatory at construction. MusicBrainz throttles
unidentified clients, and the rate-limit is applied per-client; an
unset agent makes us indistinguishable from other anonymous traffic.
"""

from __future__ import annotations

import contextlib
import logging
import socket
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, TypeAlias

import musicbrainzngs

from platterpus import diagnostics
from platterpus.medium_select import MediumChoice, select_medium

log = logging.getLogger(__name__)

# Bound every MusicBrainz HTTP call so a stalled server/connection can't hang the
# lookup worker forever. musicbrainzngs (0.7.1, unmaintained) builds its own
# urllib opener with NO timeout argument, so the process-wide default socket
# timeout is the only injection point the library leaves us. We set it *around*
# each call and restore it after (below), rather than globally at import, so the
# adapter has no surprising process-wide side effect.
_MB_TIMEOUT_S: float = 30.0


@contextlib.contextmanager
def _socket_timeout(seconds: float) -> Iterator[None]:
    """Temporarily bound the default socket timeout for a MusicBrainz call.

    The MB worker serializes its queries on one thread, and every other network
    caller in the app (cover art, CTDB, self-update) passes an explicit per-call
    timeout to ``urlopen`` — so save/restore here can't strand another request.
    """
    previous = socket.getdefaulttimeout()
    socket.setdefaulttimeout(seconds)
    try:
        yield
    finally:
        socket.setdefaulttimeout(previous)


class MusicBrainzQueryError(Exception):
    """Raised when a MusicBrainz query fails.

    Wraps `musicbrainzngs.WebServiceError` (and subclasses) so callers
    don't need to import the third-party exception type. The original
    exception is preserved on `.__cause__`.
    """


# --- Data types -------------------------------------------------------------


@dataclass(frozen=True)
class TocSignature:
    """A disc's table of contents, for a MusicBrainz TOC lookup.

    `track_offsets` has length == last_track. Each value is the start
    sector of the corresponding track on the disc. MusicBrainz's TOC
    query string is `first+last+leadout+offset1+offset2+...`.
    """

    first_track: int
    last_track: int
    lead_out_sector: int
    track_offsets: tuple[int, ...]

    def to_query(self) -> str:
        """Render as the space-separated form MB expects."""
        return " ".join(
            [
                str(self.first_track),
                str(self.last_track),
                str(self.lead_out_sector),
                *(str(offset) for offset in self.track_offsets),
            ]
        )


@dataclass(frozen=True)
class TrackSummary:
    """One track on a release. Used inside `ReleaseDetail.tracks`."""

    number: int
    title: str
    artist_credit: str = ""
    length_ms: int | None = None
    isrc: str = ""  # recording ISRC, when MB has one (requires the "isrcs" include)


@dataclass(frozen=True)
class ReleaseSummary:
    """Compact release info for the picker dialog when MB returns >1 match."""

    mbid: str
    title: str
    artist_credit: str
    date: str = ""  # YYYY or YYYY-MM-DD per MB
    country: str = ""  # ISO-3166-1 alpha-2
    track_count: int | None = None
    label: str = ""
    catalog_number: str = ""
    barcode: str = ""  # UPC/EAN, when MB has one ("" otherwise)
    medium_format: str = ""  # e.g. "CD"
    disambiguation: str = ""
    genre: str = ""  # top MB tag (requires the "tags" include); "" when none
    disc_number: int = 1  # this medium's position in the release
    # HOW we decided which medium of a multi-disc release is in the drive, and
    # whether we actually determined it. Carried on the summary rather than
    # logged and forgotten: a rip whose metadata may belong to another disc has
    # to be able to SAY so in the report and the UI. Capture without surfacing
    # is the same bug from the user's side (CLAUDE.md, diagnostic
    # completeness). "" on the picker-list summaries, which describe a release
    # rather than a resolved disc.
    medium_basis: str = ""
    medium_detail: str = ""
    #: False only when a multi-disc release could not be resolved — never for a
    #: single-disc release, and never merely because MB was terse.
    medium_undetermined: bool = False
    total_discs: int = 1  # number of media in the release


@dataclass(frozen=True)
class ReleaseDetail:
    """Everything the track-editor pane needs from one release."""

    summary: ReleaseSummary
    tracks: tuple[TrackSummary, ...]


# --- Abstract base ----------------------------------------------------------


class MusicBrainzClient(ABC):
    """Abstract base for any MusicBrainz query backend."""

    @abstractmethod
    def releases_by_disc_id(self, disc_id: str) -> list[ReleaseSummary]:
        """Lookup releases by MB disc ID. Empty list when no match."""

    @abstractmethod
    def releases_by_toc(self, toc: TocSignature) -> list[ReleaseSummary]:
        """Lookup releases by TOC fingerprint. Empty list when no match."""

    @abstractmethod
    def release_by_mbid(
        self,
        mbid: str,
        *,
        disc_id: str = "",
        disc_track_count: int | None = None,
    ) -> ReleaseDetail:
        """Fetch full release details for one MBID.

        ``disc_id`` and ``disc_track_count`` describe the disc actually in the
        drive, and are what lets a multi-disc release resolve to the right
        medium (``medium_select``). Both default to "unknown" so a caller with
        neither still works — it just gets an unconfident selection that says
        so, rather than a confident wrong one.
        """

    @abstractmethod
    def set_user_agent(self, app: str, version: str, contact: str) -> None:
        """Re-identify the client (e.g., after a version bump)."""


# --- v1 concrete implementation --------------------------------------------


def _record_mb_failure(what: str, exc: BaseException, detail: str = "") -> str:
    """Record an MB query failure and return the message to raise with.

    One helper for all four raise sites, so they cannot describe the same class of
    failure differently — and so the *report* carries them. Before this, a
    MusicBrainz failure existed only as an exception message the UI turned into a
    dialog: nothing enumerated it, so a report from a rip whose metadata came from a
    fallback path could not say the lookup had failed at all.

    ``exit_code`` is deliberately omitted: MB is an HTTP call, there is no child
    process, and claiming a tri-state exit status for one would be a confident wrong
    answer (the same mistake this subsystem's own first output made).
    """
    message = f"{what}: {exc}"
    diagnostics.warning(
        "musicbrainz.lookup_failed",
        f"{message} — metadata for this disc could not be fetched from "
        "MusicBrainz. The rip itself is unaffected; the tags are.",
        tool="MusicBrainz (HTTP)",
        detail=detail or f"{type(exc).__name__}: {exc}",
        where="adapters.musicbrainz_client.MusicBrainzNgsImpl",
    )
    return message


class MusicBrainzNgsImpl(MusicBrainzClient):
    """MusicBrainz client backed by the `musicbrainzngs` library."""

    def __init__(self, app: str, version: str, contact: str) -> None:
        """User-agent is mandatory; MB throttles unidentified traffic.

        Per MB's policy, `contact` should be a real email or project URL
        so a human can be reached if our client misbehaves.
        """
        self.set_user_agent(app, version, contact)

    def set_user_agent(self, app: str, version: str, contact: str) -> None:
        musicbrainzngs.set_useragent(app, version, contact)
        log.debug("MB user-agent set: %s/%s (%s)", app, version, contact)

    # --- Public ABC methods ---

    def releases_by_disc_id(self, disc_id: str) -> list[ReleaseSummary]:
        try:
            with _socket_timeout(_MB_TIMEOUT_S):
                response = musicbrainzngs.get_releases_by_discid(
                    disc_id,
                    includes=["artists", "labels"],
                    cdstubs=False,
                )
        except musicbrainzngs.ResponseError as exc:
            # MB returns 404 for "no match" — translate that to an empty list
            # rather than an exception, since the picker UI treats it as
            # "no candidates" (not an error).
            if _is_not_found(exc):
                return []
            raise MusicBrainzQueryError(
                _record_mb_failure("MB disc-id lookup failed", exc, disc_id)
            ) from exc
        except musicbrainzngs.WebServiceError as exc:
            raise MusicBrainzQueryError(
                _record_mb_failure("MB disc-id lookup failed", exc, disc_id)
            ) from exc

        return _parsed("MB disc-id answer was malformed", disc_id, response)

    def releases_by_toc(self, toc: TocSignature) -> list[ReleaseSummary]:
        try:
            with _socket_timeout(_MB_TIMEOUT_S):
                response = musicbrainzngs.get_releases_by_discid(
                    "-",  # MB requires a disc-id; "-" is the documented
                    # placeholder when only `toc=` is meaningful
                    toc=toc.to_query(),
                    includes=["artists", "labels"],
                    cdstubs=False,
                )
        except musicbrainzngs.ResponseError as exc:
            if _is_not_found(exc):
                return []
            raise MusicBrainzQueryError(
                _record_mb_failure("MB TOC lookup failed", exc, toc.to_query())
            ) from exc
        except musicbrainzngs.WebServiceError as exc:
            raise MusicBrainzQueryError(
                _record_mb_failure("MB TOC lookup failed", exc, toc.to_query())
            ) from exc

        return _parsed("MB TOC answer was malformed", toc.to_query(), response)

    def release_by_mbid(
        self,
        mbid: str,
        *,
        disc_id: str = "",
        disc_track_count: int | None = None,
    ) -> ReleaseDetail:
        try:
            with _socket_timeout(_MB_TIMEOUT_S):
                response = musicbrainzngs.get_release_by_id(
                    mbid,
                    # "tags" → a genre (top folksonomy tag; MB has no plain
                    # "genres" include in musicbrainzngs 0.7.1); "isrcs" →
                    # per-recording ISRCs.
                    includes=[
                        "artists",
                        "recordings",
                        "labels",
                        "media",
                        "tags",
                        "isrcs",
                        # Per-medium disc IDs. Without this the `disc-list` is
                        # absent and medium selection can only fall back to
                        # track count — so this include is what makes the
                        # authoritative match possible at all.
                        "discids",
                    ],
                )
        except musicbrainzngs.WebServiceError as exc:
            raise MusicBrainzQueryError(
                _record_mb_failure("MB release fetch failed", exc, mbid)
            ) from exc

        try:
            return _release_detail(response, disc_id, disc_track_count)
        except _MALFORMED as exc:
            raise MusicBrainzQueryError(
                _record_mb_failure("MB release answer was malformed", exc, mbid)
            ) from exc


#: What a payload of the wrong SHAPE raises inside the helpers below: a list where
#: an object belongs (`AttributeError`), a number where a list belongs
#: (`TypeError`), a nesting deeper than the interpreter allows. The helpers coerce
#: every value they hand on, and this is the backstop that keeps a shape they did
#: not foresee from escaping the adapter as anything but its documented error
#: (peer review 2.8, 2026-10-26: a hypothesis payload raised both).
_MALFORMED: tuple[type[Exception], ...] = (
    AttributeError,
    TypeError,
    ValueError,
    KeyError,
    IndexError,
    RecursionError,
)


def _parsed(what: str, detail: str, response: object) -> list[ReleaseSummary]:
    """The summaries in a disc-id/TOC answer, or :class:`MusicBrainzQueryError`."""
    try:
        return _summaries_from_disc_response(_as_dict(response))
    except _MALFORMED as exc:
        raise MusicBrainzQueryError(_record_mb_failure(what, exc, detail)) from exc


def _release_detail(
    response: object, disc_id: str, disc_track_count: int | None
) -> ReleaseDetail:
    """One release answer, read. May raise one of :data:`_MALFORMED`."""
    release = _as_dict(_as_dict(response).get("release"))
    choice = select_medium(
        _as_list(release.get("medium-list")),
        disc_id=disc_id,
        disc_track_count=disc_track_count,
    )
    # Log the basis every time, not just on failure: when a rip later turns
    # out to carry another disc's titles, this line is the evidence for
    # which medium was believed and why.
    if choice.confident:
        log.debug("MB medium selected (%s): %s", choice.basis, choice.detail)
    else:
        log.warning("MB medium NOT determined: %s", choice.detail)
    summary = _summary_from_release_dict(release, choice=choice)
    tracks = _tracks_from_medium(choice.medium)
    return ReleaseDetail(summary=summary, tracks=tracks)


# --- Response shape helpers (private) --------------------------------------
#
# musicbrainzngs returns nested dicts mirroring MB's XML. The helpers
# below isolate that structure so a future RequestsJsonImpl can produce
# the same dataclasses from MB's JSON response without touching the
# rest of the codebase.
#
# `Any` below is a claim about reality, the same call `config.py` makes for raw
# TOML and `medium_select.MediumChoice.medium` for this JSON: musicbrainzngs ships
# no stubs, so `object` would be stricter than the truth and force a cast at every
# `.get()`. Values are coerced where they leave this module (`_safe_int`,
# `isinstance`, `str(...)`). Naming them took the module off the
# `disallow_any_generics` opt-out list (2026-10-19).
_MbObject: TypeAlias = dict[str, Any]  # one JSON object (release, medium, track)
_MbArray: TypeAlias = list[Any]  # one JSON array; its items are unchecked


def _is_not_found(exc: musicbrainzngs.ResponseError) -> bool:
    """True when MB returned a 404 (the disc/TOC isn't in the database)."""
    cause = getattr(exc, "cause", None)
    code = getattr(cause, "code", None) if cause else None
    return code == 404


#: The longest text taken from one MusicBrainz field. MusicBrainz's own longest
#: titles run to a few hundred characters; this is far above them and far below a
#: value that would freeze a text widget. A longer one keeps its head and ends in
#: "…" so the cut is visible, and the cut is logged.
MAX_TEXT_CHARS: int = 4096


def _text(value: object, field: str = "") -> str:
    """``value`` if it is text, else ``""``; bounded to :data:`MAX_TEXT_CHARS`.

    MusicBrainz's answer is the untrusted boundary of an unmaintained adapter
    (Critical rule #1). Every field this module hands on is declared ``str``, and a
    number or a list in its place used to be handed on as it was, to a widget that
    raises on it. Never raises.
    """
    if not isinstance(value, str):
        return ""
    if len(value) > MAX_TEXT_CHARS:
        log.warning(
            "MusicBrainz %s was %d characters; kept the first %d and marked the cut",
            field or "value",
            len(value),
            MAX_TEXT_CHARS,
        )
        return value[:MAX_TEXT_CHARS] + "…"
    return value


def _as_dict(value: object) -> _MbObject:
    """``value`` if it is a JSON object, else an empty one. Never raises."""
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> _MbArray:
    """``value`` if it is a JSON array, else an empty one. Never raises."""
    return value if isinstance(value, list) else []


def _summaries_from_disc_response(
    response: _MbObject,
) -> list[ReleaseSummary]:
    """Extract release summaries from `get_releases_by_discid` payload."""
    disc = _as_dict(response.get("disc"))
    return [
        _summary_from_release_dict(r)
        for r in _as_list(disc.get("release-list"))
        if isinstance(r, dict)
    ]


def _summary_from_release_dict(
    release: _MbObject, *, choice: MediumChoice | None = None
) -> ReleaseSummary:
    """Map one MB release dict to a ReleaseSummary.

    ``choice`` names the medium believed to be in the drive. The disc-ID
    lookup that builds the *picker* list has no per-medium disc data to work
    from, so it passes ``None`` and the summary describes the first medium —
    which is fine there: the picker is choosing a *release*, and the medium is
    resolved on the full fetch that follows.
    """
    mbid = _text(release.get("id"), "release id")
    title = _text(release.get("title"), "title")
    artist_credit = _artist_credit_string(_as_list(release.get("artist-credit")))
    date = _text(release.get("date"), "date")
    country = _text(release.get("country"), "country")
    disambiguation = _text(release.get("disambiguation"), "disambiguation")

    media = _as_list(release.get("medium-list"))
    if choice is None:
        choice = select_medium(media)
    track_count = _medium_track_count_of(choice.medium)
    medium_format = _medium_format_of(choice.medium)
    disc_number = choice.position if choice.index >= 0 else 1
    total_discs = max(choice.total_media, 1)

    label, catalog_number = _first_label_info(_as_list(release.get("label-info-list")))

    return ReleaseSummary(
        mbid=mbid,
        title=title,
        artist_credit=artist_credit,
        date=date,
        country=country,
        track_count=track_count,
        label=label,
        catalog_number=catalog_number,
        barcode=_text(release.get("barcode"), "barcode"),
        medium_format=medium_format,
        disambiguation=disambiguation,
        genre=_top_tag_name(release),
        disc_number=disc_number,
        total_discs=total_discs,
        medium_basis=choice.basis,
        medium_detail=choice.detail,
        # Only a real ambiguity counts. A picker-list summary (choice built
        # with no disc context) is not "undetermined" in the sense the UI
        # warns about — it simply has not been resolved yet.
        medium_undetermined=(
            choice.basis == "undetermined-first" and choice.total_media > 1
        ),
    )


def _tracks_from_medium(medium: _MbObject) -> tuple[TrackSummary, ...]:
    """Per-track summaries for ONE medium — the disc in the drive.

    Takes the already-selected medium rather than reaching for
    ``medium-list[0]`` itself. That indexing was the multi-disc defect: on a
    four-disc set it handed back disc 1's 18 tracks for a 16-track disc, which
    made cyanrip refuse the whole rip — and, once the argv chokepoint stopped
    that, would instead have produced a complete rip tagged with the wrong
    disc's titles. See :mod:`platterpus.medium_select`.
    """
    if not isinstance(medium, dict) or not medium:
        return ()
    tracks: list[TrackSummary] = []
    for track in _as_list(medium.get("track-list")):
        if not isinstance(track, dict):
            continue
        recording = _as_dict(track.get("recording"))
        number = _safe_int(track.get("position") or track.get("number"))
        if number is None:
            continue
        length_ms = _safe_int(recording.get("length") or track.get("length"))
        tracks.append(
            TrackSummary(
                number=number,
                title=_text(recording.get("title"), "track title")
                or _text(track.get("title"), "track title"),
                artist_credit=_artist_credit_string(
                    _as_list(recording.get("artist-credit"))
                ),
                length_ms=length_ms,
                isrc=_first_isrc(recording),
            )
        )
    return tuple(tracks)


def _artist_credit_string(credit: _MbArray) -> str:
    """Render MB's artist-credit list as a display string.

    MB returns artist credits as a list alternating dicts (with
    `artist` and `name` keys) and strings (the joining text like
    " feat. " or " & "). The display string is the concatenation.
    """
    parts: list[str] = []
    for item in _as_list(credit):
        if isinstance(item, dict):
            artist = _as_dict(item.get("artist"))
            parts.append(_text(item.get("name")) or _text(artist.get("name")))
        else:
            # The joining phrase (" feat. "). Text only: a number here is no phrase.
            parts.append(_text(item))
    return _text("".join(parts).strip(), "artist credit")


def _medium_track_count_of(medium: _MbObject) -> int | None:
    """One medium's track count, declared or counted. None when unknown."""
    if not isinstance(medium, dict):
        return None
    declared = _safe_int(medium.get("track-count"))
    if declared is not None:
        return declared
    tracks = medium.get("track-list")
    return len(tracks) if isinstance(tracks, list) else None


def _medium_format_of(medium: _MbObject) -> str:
    """One medium's format ("CD", "Digital Media", …), or "".

    MusicBrainz JSON is the untrusted boundary of an unmaintained adapter
    (Critical rule #1), so the value is coerced rather than trusted: this is
    declared to return ``str`` and used as one, and MB is free to send back a
    number or a null.
    """
    if not isinstance(medium, dict):
        return ""
    value = medium.get("format")
    return value if isinstance(value, str) else ""


def _top_tag_name(release: _MbObject) -> str:
    """The highest-voted folksonomy tag as a best-effort genre, or "".

    MB has no curated genre in musicbrainzngs 0.7.1's includes, so we use the
    most-applied tag (often a genre like "rock"). Empty when the release is
    untagged or the "tags" include wasn't requested.
    """
    best_name, best_count = "", -1
    for tag in _as_list(release.get("tag-list")):
        if not isinstance(tag, dict):
            continue
        name = _text(tag.get("name"), "tag")
        count = _safe_int(tag.get("count")) or 0
        if name and count > best_count:
            best_name, best_count = name, count
    return best_name


def _first_isrc(recording: _MbObject) -> str:
    """First ISRC for a recording, or "". MB returns isrc-list as strings or
    `{"id": ...}` dicts depending on the response shape — handle both."""
    for item in _as_list(recording.get("isrc-list")):
        isrc = _text(item.get("id")) if isinstance(item, dict) else _text(item)
        if isrc:
            return isrc
    return ""


def _first_label_info(infos: _MbArray) -> tuple[str, str]:
    if not infos or not isinstance(infos[0], dict):
        return "", ""
    info = infos[0]
    label = _text(_as_dict(info.get("label")).get("name"), "label")
    catno = _text(info.get("catalog-number"), "catalog number")
    return label, catno


def _safe_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value))
    except (ValueError, TypeError):
        return None
