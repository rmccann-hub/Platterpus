"""Which cyanrip binary produced this rip — fork, stock, or unidentifiable.

Platterpus runs a *forked* cyanrip (the `platterpus-fork` build), and the fork
emits log rows stock cyanrip does not: per-track pre-gap length and provenance,
sample peak, per-track extraction speed and elapsed time, a secure-re-rip
verdict. Those rows change what the archival log and the report can claim about
a rip. Two logs of the same disc, one from each binary, both saying
``cyanrip 0.9.4`` in their first line, are therefore **not interchangeable
evidence** — and until this module existed nothing in the UI or the rendered log
said which one you were looking at.

**Three states, not two.** The recurring bug in this codebase is collapsing "we
could not tell" into a definite answer — ``Accurip: disabled`` read as "in the
database, no match"; an all-zero CRC read as a confidence-200 match;
``Pregap LSN: unknown`` read as ``none``. So :class:`RipperIdentity` has a
``kind`` of ``fork`` / ``stock`` / ``unknown``, and ``unknown`` renders as a
sentence that says so. A rip whose banner we never captured must never be
labelled "stock cyanrip" — that is a claim, and we do not have it.

**Why the build tag and not the version number.** The fork tracks upstream
versions, so ``0.9.4-rc1`` can be either binary. The distinguishing mark is the
parenthetical build tag cyanrip prints after the version —
``cyanrip 0.9.4-rc1 (platterpus-fork)`` — which the parser already captures into
``RipLog.ripper_build``. Matching on the *version string* would break the first
time the fork rebased; matching on the tag is stable across rebases and is the
thing the fork controls deliberately.

This module is pure: text in, dataclass out, no I/O and no Qt. Its callers are
the EAC-style log renderer, the report builder, and the rip-progress panel, so
all three describe the binary the same way rather than each inventing a phrase.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final, Literal

#: The build tags the fork is allowed to identify itself with, matched
#: case-insensitively against the parenthetical in cyanrip's version banner.
#:
#: ``platterpus-fork`` is the required tag (see
#: ``docs/cyanrip-consumer-contract.md``). ``platterpus`` alone is accepted
#: because the fork's earlier builds used it and logs from those rips exist on
#: the maintainer's disk; dropping it would silently reclassify real archived
#: rips as ``unknown``.
FORK_BUILD_TAGS: Final[frozenset[str]] = frozenset({"platterpus-fork", "platterpus"})

#: Build tags that positively identify an *unmodified* upstream build. Anything
#: else — a bare ``git describe``, a distro's tag, an empty parenthetical — is
#: ``unknown``, because "not a tag we recognise" is not "not modified".
STOCK_BUILD_TAGS: Final[frozenset[str]] = frozenset({"release"})

IdentityKind = Literal["fork", "stock", "unknown"]

# cyanrip prints "cyanrip 0.9.4-rc1 (platterpus-fork)". The tag may itself carry
# a hash or a suffix, so the fork match is a word-boundary search inside the tag
# rather than equality — `platterpus-fork-g1a2b3c4` must still read as the fork.
# Bounded, per the project's quantifier rule.
_TAG_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")


@dataclass(frozen=True)
class RipperIdentity:
    """What we can honestly say about the binary that produced a rip.

    ``kind`` is the machine-readable verdict; ``is_fork`` is the same thing as a
    tri-state boolean for the JSON report (``None`` meaning "not determined",
    never ``False``). ``label`` is a short phrase for a UI chip or a log row;
    ``detail`` is the one-sentence explanation for a tooltip or a report field.
    """

    kind: IdentityKind
    label: str
    detail: str
    #: The raw banner text we classified, kept so a surprising verdict is
    #: diagnosable from the report alone without re-reading the rip log.
    version: str = ""
    build_tag: str = ""

    @property
    def is_fork(self) -> bool | None:
        """``True`` / ``False`` / ``None`` — never collapse ``None`` to ``False``."""
        if self.kind == "fork":
            return True
        if self.kind == "stock":
            return False
        return None


def _normalise_tag(build_tag: str) -> str:
    """Lower-case, whitespace-stripped tag. ``""`` when there is nothing to read."""
    return build_tag.strip().casefold()


def _tag_matches(tag: str, wanted: frozenset[str]) -> bool:
    """True when any token in ``tag`` is one of ``wanted``.

    Tokenised rather than compared whole so a build tag that appends a hash
    (``platterpus-fork-g1a2b3c4``) or a date still identifies. Splitting on the
    separators cyanrip's own tags use keeps this from matching a substring of an
    unrelated word.
    """
    if tag in wanted:
        return True
    tokens = {t for t in re.split(r"[\s,;+/]+", tag) if t}
    if tokens & wanted:
        return True
    # One more pass for hyphen/underscore-joined compounds, longest-first so
    # "platterpus-fork" wins over the bare "platterpus" prefix inside it.
    for token in tokens:
        parts = re.split(r"[-_]", token)
        for width in range(len(parts), 0, -1):
            for start in range(len(parts) - width + 1):
                if "-".join(parts[start : start + width]) in wanted:
                    return True
    return False


def identify_ripper(log_creator: str, build_tag: str) -> RipperIdentity:
    """Classify the ripper from its version banner's two halves.

    ``log_creator`` is the ``"cyanrip 0.9.4-rc1"`` part and ``build_tag`` the
    parenthetical, exactly as :func:`platterpus.parsers.cyanrip_log.
    parse_cyanrip_log` stores them on :class:`~platterpus.parsers.rip_log.RipLog`.

    Never raises — it is fed parsed external output, so an empty, garbled, or
    absurd input has to produce a verdict rather than an exception. The verdict
    for anything unrecognised is ``unknown``.
    """
    version = (log_creator or "").strip()
    raw_tag = (build_tag or "").strip()
    tag = _normalise_tag(raw_tag)

    if tag and _tag_matches(tag, FORK_BUILD_TAGS):
        return RipperIdentity(
            kind="fork",
            label=f"{version or 'cyanrip'} — Platterpus fork",
            detail=(
                f"Ripped by the Platterpus fork of cyanrip (build tag "
                f"{raw_tag!r}). The fork reports per-track pre-gap length and "
                f"provenance, sample peak, extraction speed and elapsed time, "
                f"which stock cyanrip does not."
            ),
            version=version,
            build_tag=raw_tag,
        )

    if tag and _tag_matches(tag, STOCK_BUILD_TAGS):
        return RipperIdentity(
            kind="stock",
            label=f"{version or 'cyanrip'} — upstream release",
            detail=(
                f"Ripped by an unmodified upstream cyanrip (build tag "
                f"{raw_tag!r}). The fork-only rows are absent from this rip, so "
                f"pre-gap length, sample peak and per-track timings are not "
                f"available for it."
            ),
            version=version,
            build_tag=raw_tag,
        )

    # Everything else. Deliberately NOT "stock": a local build, a distro
    # package, a `git describe` tag, or a banner we never captured are all
    # "we do not know", and saying "upstream release" here would be a claim.
    if not version and not raw_tag:
        detail = (
            "The ripper's version banner was not captured for this rip, so which "
            "cyanrip binary produced it is unknown. Fork-only fields being absent "
            "does not prove a stock binary — the banner may simply be missing."
        )
    else:
        detail = (
            f"Build tag {raw_tag!r} is not one this version of Platterpus "
            f"recognises, so whether this rip came from the Platterpus fork or "
            f"an unmodified cyanrip is unknown. Recognised fork tags: "
            f"{', '.join(sorted(FORK_BUILD_TAGS))}."
            if raw_tag
            else (
                "The version banner carried no build tag, so whether this rip "
                "came from the Platterpus fork or an unmodified cyanrip is "
                "unknown."
            )
        )
    return RipperIdentity(
        kind="unknown",
        label=f"{version or 'ripper'} — build not identified",
        detail=detail,
        version=version,
        build_tag=raw_tag,
    )


def identify_from_banner(banner: str) -> RipperIdentity:
    """Classify from a whole ``cyanrip -V`` line, e.g. before a rip starts.

    The rip-progress panel and the preflight check have the raw banner rather
    than a parsed :class:`RipLog`, and this keeps them off a second private
    regex (Critical rule #6's principle, applied to identity instead of
    versions). Unparseable text yields ``unknown``, same as everywhere else.
    """
    text = (banner or "").strip()
    if not text:
        return identify_ripper("", "")
    head, _, rest = text.partition("(")
    tag = rest.partition(")")[0] if rest else ""
    return identify_ripper(head.strip(), tag.strip())


#: The prefix a fork build tag carries before its commit, e.g.
#: ``platterpus-fork-gc4d1a00``. The ``g`` is git-describe's, not ours.
_FORK_COMMIT_PREFIX: Final[str] = "platterpus-fork-g"


def fork_commit_from_banner(banner: str) -> str | None:
    """The fork commit a banner names, or ``None`` when it names none.

    ``"cyanrip 0.9.4-rc1+platterpus.6 (platterpus-fork-gc4d1a00)"`` -> ``"c4d1a00"``.

    **Why this lives here rather than in the window that wanted it.** It used to
    be a private method on the update mixin, reading a cached
    ``self._observed_ripper_banner`` — an attribute assigned **nowhere in the
    tree**. Because the read went through ``getattr(..., "")`` it could not raise,
    so the method returned ``None`` on every call and the ripper update check
    silently compared the manifest against the build-time constant ``FORK_PIN``
    instead of against the installed binary. It reported *"you have release 11
    (ddf7ac3)"* to an operator running ``c4d1a00`` — forever, including
    immediately after a successful install (2026-08-17).

    The lesson is not "assign the attribute": it is that a **cached observation
    has a producer somebody has to remember to write**, and a probe does not. The
    caller now reads the binary at check time, on its own thread, and passes the
    banner straight in. Nothing to forget, and nothing to go stale.

    Banner parsing stays in this module for the same reason
    :func:`identify_from_banner` does — one place owns the shape of that line, so
    a second private regex cannot drift from it.

    Never raises: every failure mode is "we cannot tell", which is a ``None``.
    """
    text = (banner or "").strip()
    if "(" not in text or ")" not in text:
        return None
    tag = text[text.index("(") + 1 : text.rindex(")")].strip()
    if not tag.casefold().startswith(_FORK_COMMIT_PREFIX):
        return None
    return tag[len(_FORK_COMMIT_PREFIX) :].strip() or None
