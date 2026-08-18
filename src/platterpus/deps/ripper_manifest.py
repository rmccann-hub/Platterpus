"""The cyanrip fork's published release manifest — *is a newer ripper out?*

**Why this exists.** The fork's pin moves faster than a Platterpus release: five
times inside round 7, twice in a single day. Until now the only way a user learned
their ripper was superseded was a human telling them, and the only way to act on it
was a constant in :mod:`platterpus.deps.fork_source` that ships inside a release —
the exact granularity mismatch `CLAUDE.md` Critical rule #12 calls out. The fork now
publishes a machine-readable manifest of what it has released, so the app can *look*.

**Notice, and offer. Never "keep up to date".** This module answers one question —
"is there a newer fork build than the one we pin?" — and nothing here installs
anything. That is not timidity, it is the deviation policy: switching the container
to a new cyanrip pin is a handshake event, and a build no round has approved makes
every rip report ``ripper_handshake_approval: unapproved``. An auto-updater would
silently turn every archival record into one that names an unverified ripper. So the
answer is shown to a person, with the consequence stated, and they decide.

**Three rules the fork asked for, and each is a real defect avoided:**

1. **Order by ``release_seq``, never by the version string.** The fork's version is
   upstream's ``0.9.4-rc1`` copied verbatim, plus ``+platterpus.N`` — SemVer *build
   metadata*, which the spec says MUST be ignored for precedence. A version
   comparison therefore sees ``0.9.4-rc1`` versus ``0.9.4-rc1`` **forever** and would
   never offer an upgrade. ``release_seq`` is a monotonic integer, one per published
   artifact, never reused or reset — including across an upstream sync, when the
   leading version number changes for reasons unrelated to their releases.
2. **Read the channel from the manifest; never sniff the string for "beta".** We
   spell a pre-release ``v0.6.4b1``; they spell it ``-beta.1``. A substring check
   finds theirs and misses ours, so the same code that looked right would tell a
   Platterpus beta user they were on stable. The manifest states the channel as a
   fact, so nothing has to infer it.
3. **Refuse a ``schema`` we do not implement.** Declared precisely so a consumer can
   *refuse* rather than guess at fields it has never seen.

**Everything here is external input, and one field of it becomes a shell argument.**
``commit`` is handed to ``git checkout --force --detach`` inside the container by
:func:`platterpus.deps.fork_source.target_for_commit`. That makes this module an
argv chokepoint in the sense of `CLAUDE.md`'s validate-every-output rule, not merely
a parser: :func:`_clean_commit` refuses anything that is not a lowercase hex sha, so
a manifest that has been tampered with — or simply gone wrong — cannot put a
metacharacter on a command line. Everything else is bounded, typed and range-checked
at the boundary, and a value that fails validation drops its *row* rather than the
whole document: one malformed channel must not hide a good one.

**Never raises.** Same contract as every other parser of external output here: a
best-effort result or ``None``, with a ``hypothesis`` property test proving it. And
``None`` means *not determined* — never "you are up to date". Those are different
answers and conflating them is how a check gets satisfied by finding nothing.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final

log = logging.getLogger(__name__)

#: Where the manifest lives. The fork's branch tip rather than a release asset:
#: they generate it with ``tools/gen-release-manifest.py`` and their CI fails if the
#: committed copy is stale, so the branch tip *is* the published record.
MANIFEST_URL: Final[str] = (
    "https://raw.githubusercontent.com/rmccann-hub/cyanrip/"
    "platterpus-fork/release-manifest.json"
)

#: The newest ``schema`` we implement. Kept as a single number because the tests and
#: the fork's own conformance check quote it; the set of values we *accept* is
#: :data:`SUPPORTED_SCHEMAS` below.
SUPPORTED_SCHEMA: Final[int] = 2

#: Every ``schema`` value we know how to read. A manifest declaring anything else is
#: refused outright rather than parsed optimistically — that is the entire point of
#: them declaring it.
#:
#: **Schema 2 adds ``build``** (round 11): the exact build command for that channel's
#: commit, derived by the fork from the commit's own tree. It is *additive*, so a
#: schema-1 document still parses — its rows simply carry no build options, which is
#: the correct reading of a manifest written before the field existed.
#:
#: Why 1 stays accepted rather than being dropped: the fork's branch tip is the
#: published record, and a consumer that refuses the older document cannot read a
#: manifest from before the bump — which is precisely the rollback direction round 11
#: §0 is about.
SUPPORTED_SCHEMAS: Final[frozenset[int]] = frozenset({1, 2})

#: The ``project`` value that identifies this as the manifest we mean. Checked so a
#: URL that has been re-pointed at some *other* project's manifest is refused rather
#: than mined for whatever fields happen to match.
EXPECTED_PROJECT: Final[str] = "cyanrip-fork"

#: Channel names, matching :mod:`platterpus.update_check`'s so one Settings concept
#: covers both. ``stable`` is what a user gets unless they opt in.
CHANNEL_STABLE: Final[str] = "stable"
CHANNEL_BETA: Final[str] = "beta"
CHANNELS: Final[tuple[str, ...]] = (CHANNEL_STABLE, CHANNEL_BETA)

#: A git short-or-full sha, and nothing else. **This is the argv guard**, not a
#: tidiness check: the value it validates is spliced into a ``git checkout`` run
#: inside the container. Anchored, lowercase-hex only, bounded 7–40.
_COMMIT_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{7,40}$")

#: Bound on the version string we will carry into a dialog and a log line. Generous
#: next to a real one (``0.9.4-rc1+platterpus.5`` is 21 characters) and small enough
#: that a hostile or broken manifest cannot push a megabyte into the GUI thread's
#: text layout — the same reasoning as the inbound seam's line-length cap.
_MAX_VERSION_CHARS: Final[int] = 64

#: Bound on ``release_seq`` / ``handshake_round``. They are small counters; a value
#: outside this range is a broken document, not a very active project.
_MAX_SEQ: Final[int] = 1_000_000

#: The manifest is well under a kilobyte. Cap the read so a misbehaving or hostile
#: endpoint cannot stream an unbounded body into memory on the worker thread — the
#: same ceiling every other network fetcher in this codebase applies.
_MAX_BODY_BYTES: Final[int] = 256 * 1024
_TIMEOUT_S: Final[float] = 6.0

#: Hosts an ``install`` URL may point at. A URL from a network document that we would
#: show a user (and could one day fetch) is not allowed to name an arbitrary host.
_ALLOWED_INSTALL_HOSTS: Final[frozenset[str]] = frozenset(
    {"github.com", "codeload.github.com", "raw.githubusercontent.com"}
)


@dataclass(frozen=True)
class RipperRelease:
    """One channel's row: a fork build the fork says it has published.

    Every field is validated before this object exists, so a caller can use it
    without re-checking. :attr:`commit` in particular is known to be a bare hex sha.
    """

    #: ``stable`` or ``beta`` — **read from the manifest key**, never inferred from
    #: the version string. See the module docstring for why that distinction is load-
    #: bearing rather than pedantic.
    channel: str
    #: The version banner this build prints, parenthetical excluded.
    version: str
    #: Short commit sha. Validated hex — safe to hand to the build step.
    commit: str
    #: The monotonic release counter. **The only ordering key.**
    release_seq: int
    #: Which handshake round this build belongs to, per *their* record.
    handshake_round: int
    #: Whether that round is closed, per *their* record. Not a substitute for our own
    #: verification — see :meth:`RipperManifest.newer_than`'s caller obligations and
    #: :mod:`platterpus.handshake_approval`, which keys on the record in this repo.
    round_closed: bool
    #: Where to get it. Carried for display and provenance; the install path we
    #: actually drive is a git checkout of :attr:`commit`, which is what our build
    #: step already knows how to do.
    install_url: str
    #: Validated ``meson setup`` options for **this commit**, from schema 2's ``build``
    #: field. Empty for a schema-1 manifest, for a commit predating the options, and
    #: for any ``build`` string we did not fully recognise — see
    #: :func:`_clean_build_options` for why empty is the safe answer in every case.
    #:
    #: Defaulted so a schema-1 row constructs unchanged, and so a caller that forgets
    #: this field gets the under-claiming build rather than an error.
    meson_options: tuple[str, ...] = ()

    @property
    def build_tag(self) -> str:
        """The banner parenthetical a correct build of :attr:`commit` prints."""
        return f"platterpus-fork-g{self.commit}"


@dataclass(frozen=True)
class RipperManifest:
    """A validated manifest: the channels we understood, keyed by channel name.

    A channel whose row failed validation is **absent** rather than present-and-
    empty, so ``manifest.channel("beta") is None`` reads as "not determined" and
    can never be mistaken for a real offer.
    """

    schema: int
    project: str
    default_channel: str
    channels: dict[str, RipperRelease]

    def channel(self, name: str) -> RipperRelease | None:
        """The row for ``name``, or ``None`` if the manifest did not carry a usable one."""
        return self.channels.get(name)

    def newer_than(self, name: str, installed_seq: int | None) -> RipperRelease | None:
        """The row on channel ``name`` **if it is strictly newer** than ``installed_seq``.

        ``None`` covers three genuinely different situations and the caller must not
        collapse them into "up to date":

        * the channel has no usable row (a malformed manifest, or a channel they do
          not publish),
        * ``installed_seq`` is ``None`` — we do not know which release our own pin
          corresponds to, so we cannot compare and must say so,
        * the row is not newer, which is the only one that means up to date.

        Distinguishing them is :mod:`platterpus.deps.ripper_offer`'s job; this
        function answers only "is there something to offer", and a caller that needs
        the reason asks for the row and the seq separately.

        **Strictly greater**, so an equal seq is never offered — re-offering the
        build you already have is how an update prompt becomes noise people click
        through. And a *lower* seq is never offered either: the fork's own generator
        asserts that opting into beta can never move a user backwards, but that is
        their invariant to keep and this is ours to enforce.
        """
        row = self.channel(name)
        if row is None or installed_seq is None:
            return None
        return row if row.release_seq > installed_seq else None


def _clean_int(value: Any, *, field: str, maximum: int = _MAX_SEQ) -> int | None:
    """A non-negative ``int`` within range, or ``None`` with a reason logged.

    ``bool`` is rejected explicitly: it is an ``int`` subclass in Python, so a
    ``true`` in the JSON would otherwise arrive here as a perfectly valid ``1``.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        log.warning("ripper manifest: %s is not an integer (%r)", field, value)
        return None
    if not 0 <= value <= maximum:
        log.warning("ripper manifest: %s out of range (%r)", field, value)
        return None
    # `int(value)` rather than `value`: the parameter is `Any`, and returning it
    # unchanged would launder the untyped JSON value straight through a typed
    # signature. The isinstance guard above has already established it is a real
    # int, so this is free at run time and honest to the checker.
    return int(value)


def _clean_commit(value: Any) -> str | None:
    """A bare lowercase hex sha, or ``None``.

    **The argv guard.** This value reaches ``git checkout --force --detach`` inside
    the container. Anything that is not ``[0-9a-f]{7,40}`` is refused here rather
    than sanitised into something plausible, because there is no such thing as a
    *nearly* valid commit and a "repaired" one would name a different build.
    """
    if not isinstance(value, str):
        log.warning("ripper manifest: commit is not a string (%r)", value)
        return None
    commit = value.strip()
    if not _COMMIT_RE.match(commit):
        log.warning("ripper manifest: refusing implausible commit %r", commit)
        return None
    return commit


def _clean_version(value: Any) -> str | None:
    """A short, printable, single-line version string, or ``None``.

    Control characters are refused rather than stripped: this string is shown to a
    user and written to the log, and the inbound-seam rule says dependency text is
    flagged, not quietly repaired.
    """
    if not isinstance(value, str):
        log.warning("ripper manifest: version is not a string (%r)", value)
        return None
    version = value.strip()
    if not version or len(version) > _MAX_VERSION_CHARS:
        log.warning("ripper manifest: version is empty or over-long (%d)", len(version))
        return None
    if any(ch < " " or ch == "\x7f" for ch in version):
        log.warning("ripper manifest: version contains control characters")
        return None
    return version


def _clean_install_url(value: Any) -> str | None:
    """An ``https`` URL on a host we recognise, or ``None``."""
    if not isinstance(value, str):
        return None
    url = value.strip()
    if not url.startswith("https://"):
        log.warning("ripper manifest: install URL is not https (%r)", url[:120])
        return None
    host = url[len("https://") :].split("/", 1)[0].split("@")[-1].lower()
    # Strip an explicit port before matching, so `github.com:443` is still github.
    host = host.split(":", 1)[0]
    if host not in _ALLOWED_INSTALL_HOSTS:
        log.warning("ripper manifest: install URL host not recognised (%r)", host)
        return None
    return url


#: Meson options we will accept out of a manifest's ``build`` field, mapped to the
#: values each may take.
#:
#: **This allowlist is the whole security argument for schema 2**, so it is worth
#: stating plainly. The fork's ``build`` field is a *shell command string*
#: (``"meson setup build -Ddeclare_released=true && ninja -C build"``). Round 11 §J1
#: asks us to run what it says instead of a constant of our own. Taking that
#: literally — handing the string to a shell — would turn a field in a remote JSON
#: document into arbitrary command execution inside the user's container, on a path
#: whose later steps run ``sudo install``. Whoever can write that file, or anyone who
#: can interpose on the fetch, would own the machine.
#:
#: So we honour the *intent* and refuse the *mechanism*: parse the string, extract
#: only ``-D`` options that appear here with a value that appears here, and build
#: with our own command. Their requirement was "it must not be a constant on your
#: side" — the options are not; the command around them is, deliberately.
_ALLOWED_MESON_OPTIONS: Final[dict[str, frozenset[str]]] = {
    "declare_released": frozenset({"true", "false"}),
}

#: The command shape we expect, ignoring options. Anything else is refused whole.
_EXPECTED_BUILD_WORDS: Final[frozenset[str]] = frozenset(
    {"meson", "setup", "build", "&&", "ninja", "-C"}
)

#: Bound on the ``build`` string. A real one is ~60 characters.
_MAX_BUILD_CHARS: Final[int] = 512


def _clean_build_options(value: Any, *, field: str) -> tuple[str, ...]:
    """The validated ``-D`` options from a manifest ``build`` command.

    Returns a tuple of option strings we are willing to pass to ``meson setup``.
    **Returns an empty tuple for anything unrecognised** — a missing field, a
    malformed one, an option we do not know, a value we do not accept, or a stray
    word that suggests the command does something beyond configure-and-compile.

    Empty is the safe answer in both directions, which is why every failure returns
    it rather than ``None``:

    * For ``declare_released``, dropping the option makes the build render as *not a
      released build*. That **under-claims**, which is the direction round 10 fixed
      the flag to fail in and the one condition we set on accepting a declaration at
      all — a permissive lie lands in somebody's archival record forever.
    * For the build itself, no options is exactly what every commit before the option
      existed needs (round 11 §0: ``meson_options.txt`` is absent at ``ddf7ac3`` and
      meson fails the *whole configure* on an unknown ``-D``).

    Never raises, per the parser rule — this reads a document off the network.
    """
    if value is None:
        return ()
    if not isinstance(value, str):
        log.warning("ripper manifest: %s is not a string (%r)", field, type(value))
        return ()
    if len(value) > _MAX_BUILD_CHARS:
        log.warning(
            "ripper manifest: %s is %d chars, over the %d cap — refusing it",
            field,
            len(value),
            _MAX_BUILD_CHARS,
        )
        return ()

    options: list[str] = []
    for word in value.split():
        if word.startswith("-D"):
            key, sep, val = word[2:].partition("=")
            allowed = _ALLOWED_MESON_OPTIONS.get(key)
            if not sep or allowed is None or val not in allowed:
                # Logged with the offending token so a bug report carries it. We
                # refuse the WHOLE field rather than the single option: a command we
                # only partly understand is a command we do not understand, and
                # silently dropping one option from a build instruction is how a
                # build ends up meaning something nobody wrote.
                log.warning(
                    "ripper manifest: %s carries an option we do not accept (%r) — "
                    "refusing the whole field and building with no options",
                    field,
                    word[:80],
                )
                return ()
            options.append(word)
        elif word not in _EXPECTED_BUILD_WORDS:
            log.warning(
                "ripper manifest: %s carries an unexpected word (%r) — refusing the "
                "whole field and building with no options",
                field,
                word[:80],
            )
            return ()
    return tuple(options)


def _parse_channel(name: str, raw: Any) -> RipperRelease | None:
    """One channel row, fully validated, or ``None`` with the reason logged."""
    if not isinstance(raw, dict):
        log.warning("ripper manifest: channel %r is not an object", name)
        return None
    version = _clean_version(raw.get("version"))
    commit = _clean_commit(raw.get("commit"))
    release_seq = _clean_int(raw.get("release_seq"), field=f"{name}.release_seq")
    handshake_round = _clean_int(
        raw.get("handshake_round"), field=f"{name}.handshake_round"
    )
    round_closed = raw.get("round_closed")
    if version is None or commit is None or release_seq is None:
        return None
    if handshake_round is None:
        return None
    if not isinstance(round_closed, bool):
        # Tri-state discipline: a missing or non-boolean `round_closed` is NOT
        # `False`. Dropping the row makes it "not determined", which is the honest
        # answer; defaulting it to False would report a closed round as open, and
        # defaulting it to True would claim verification nobody performed.
        log.warning("ripper manifest: channel %r has no boolean round_closed", name)
        return None
    install_url = _clean_install_url(raw.get("install"))
    if install_url is None:
        return None
    return RipperRelease(
        channel=name,
        version=version,
        commit=commit,
        release_seq=release_seq,
        handshake_round=handshake_round,
        round_closed=round_closed,
        install_url=install_url,
        # Absent in schema 1, and an unreadable one degrades to no options rather
        # than dropping the row: the build command is an optimisation of honesty
        # (the release admitting it is one), not a precondition for installing.
        meson_options=_clean_build_options(raw.get("build"), field=f"{name}.build"),
    )


def parse_manifest(text: str) -> RipperManifest | None:
    """Parse the fork's ``release-manifest.json``. **Never raises.**

    Returns ``None`` — *not determined* — for anything we cannot read with
    confidence: malformed JSON, a schema we do not implement, the wrong project, or
    no usable channel at all. A manifest with one good channel and one broken one
    parses, carrying only the good one.
    """
    try:
        document = json.loads(text)
    except (ValueError, TypeError):
        log.warning("ripper manifest: body is not JSON", exc_info=True)
        return None
    if not isinstance(document, dict):
        log.warning("ripper manifest: top level is not an object")
        return None

    schema = _clean_int(document.get("schema"), field="schema", maximum=1_000)
    if schema is None:
        return None
    if schema not in SUPPORTED_SCHEMAS:
        # Refusing rather than guessing is what the field is FOR. Logged at warning
        # so a bug report carries it — a user seeing "couldn't check" deserves a log
        # line saying the manifest moved past us.
        log.warning(
            "ripper manifest: schema %d is not one this Platterpus implements (%s) "
            "— refusing it rather than guessing at its fields",
            schema,
            sorted(SUPPORTED_SCHEMAS),
        )
        return None

    project = document.get("project")
    if project != EXPECTED_PROJECT:
        log.warning(
            "ripper manifest: project is %r, expected %r", project, EXPECTED_PROJECT
        )
        return None

    default_channel = document.get("default_channel")
    if default_channel not in CHANNELS:
        # Not fatal — we never *have* to use their default, since our own Settings
        # carry the user's choice. Fall back to stable and say so.
        log.warning(
            "ripper manifest: unrecognised default_channel %r — using %r",
            default_channel,
            CHANNEL_STABLE,
        )
        default_channel = CHANNEL_STABLE

    raw_channels = document.get("channels")
    if not isinstance(raw_channels, dict):
        log.warning("ripper manifest: channels is not an object")
        return None

    channels: dict[str, RipperRelease] = {}
    for name in CHANNELS:
        # Iterate OUR channel names, not theirs. A manifest that grows a third
        # channel must not silently become offerable through a Settings control that
        # cannot express it, and a channel name we do not implement is not a channel
        # a user of this build can be on.
        row = _parse_channel(name, raw_channels.get(name))
        if row is not None:
            channels[name] = row
    if not channels:
        log.warning("ripper manifest: no usable channel rows")
        return None
    return RipperManifest(
        schema=schema,
        project=str(project),
        default_channel=str(default_channel),
        channels=channels,
    )


class CancellableFetcher:
    """A one-shot HTTPS GET that another thread can actually interrupt.

    **Why this is a class rather than a function.** `CLAUDE.md` rule 9: a
    ``cancel()`` that only sets a flag the blocked call never checks is a false
    promise, and ``QThread.quit()`` never reaches a thread sitting in a socket read.
    A worker doing this fetch therefore needs a way to *break* the read, not a way to
    ask it nicely — and unlike the subprocess-backed workers there is no child to
    kill, so the handle that must be reachable is the **response object**.

    Holding it on an instance lets :meth:`cancel` close the socket from the GUI
    thread, which makes the blocked ``read()`` raise and the worker finish promptly.
    That is a real interruption, so this worker never joins the no-cancel ratchet in
    ``tests/test_qthread_ownership.py``.

    Single-use and not reusable on purpose: a fetcher that has been cancelled stays
    cancelled, so a late :meth:`fetch` cannot quietly restart work the window has
    already torn down.
    """

    def __init__(self) -> None:
        #: The live response while a read is in flight, else ``None``. Assignment of
        #: a reference is atomic under the GIL, which is all the synchronisation this
        #: needs — the GUI thread only ever reads it and calls ``close()``.
        self._response: object | None = None
        #: Set by :meth:`cancel`. Checked *before* opening so a cancel that lands in
        #: the gap between construction and connect is not silently ignored.
        self._cancelled: bool = False

    @property
    def cancelled(self) -> bool:
        """Whether :meth:`cancel` has been called.

        Public because a **caller** has to be able to tell "the fetch failed" from
        "we abandoned it", and those need opposite responses: a failure is a verdict
        to report, an abandonment happens because the window is closing and must
        produce no user-facing anything. Reading ``_cancelled`` from outside would
        have worked and would have been a private field two modules deep.
        """
        return self._cancelled

    def cancel(self) -> None:
        """Interrupt an in-flight fetch. Safe to call from any thread, and twice."""
        self._cancelled = True
        response = self._response
        if response is None:
            return
        try:
            response.close()  # type: ignore[attr-defined]  # a urlopen handle
        except Exception:  # noqa: BLE001 — closing to interrupt; failure is moot
            log.debug("ripper manifest: closing the response raised", exc_info=True)

    def fetch(self, url: str) -> str:
        """GET ``url`` and return the body text (raises on any failure, incl. cancel).

        Reads one byte past the cap so "at the limit" and "over it" are
        distinguishable, and refuses an over-cap body — :func:`fetch_manifest` turns
        that into "couldn't check" like any other failure.
        """
        if self._cancelled:
            raise ValueError("ripper manifest fetch cancelled before it started")
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        response = urllib.request.urlopen(request, timeout=_TIMEOUT_S)  # noqa: S310
        self._response = response
        try:
            data: bytes = response.read(_MAX_BODY_BYTES + 1)
        finally:
            # Cleared before closing so a concurrent cancel() cannot reach a handle
            # we are already tearing down.
            self._response = None
            try:
                response.close()
            except Exception:  # noqa: BLE001 — best-effort cleanup
                pass
        if self._cancelled:
            raise ValueError("ripper manifest fetch cancelled")
        if len(data) > _MAX_BODY_BYTES:
            raise ValueError(
                f"ripper manifest exceeded {_MAX_BODY_BYTES} bytes — refusing it"
            )
        return data.decode("utf-8")


def _default_fetch(url: str) -> str:
    """The uncancellable convenience form, for callers with no thread to interrupt.

    Delegates to :class:`CancellableFetcher` rather than repeating the open/cap/decode
    dance — two expressions of one bounded read is two things to drift, and the cap
    is the half that matters.
    """
    return CancellableFetcher().fetch(url)


def fetch_manifest(fetch: Callable[[str], str] | None = None) -> RipperManifest | None:
    """Fetch and parse the manifest, or ``None`` if it cannot be determined.

    **Blocking — never call this on the GUI thread.**
    :class:`platterpus.workers.ripper_update_worker.RipperUpdateWorker` is the
    supported caller. ``fetch`` is injectable so every test runs without a network.
    """
    try:
        body = (fetch or _default_fetch)(MANIFEST_URL)
    except Exception:  # noqa: BLE001 — any failure means "unknown", never a crash
        log.warning("ripper manifest: fetch failed", exc_info=True)
        return None
    return parse_manifest(body)
