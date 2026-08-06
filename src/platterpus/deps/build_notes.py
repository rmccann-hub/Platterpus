"""Per-dependency *build* qualifiers — "which build of this tool is installed?"

A version number answers "how new is it". It does not answer "is it the binary
this project actually wants", and for cyanrip those are different questions:
the Platterpus fork deliberately keeps upstream's version string byte for byte
(see the fork's ``meson.build``: ``version: '0.9.4-rc1'`` with a *separate*
``PROJECT_FORK_ID``), precisely so that anything parsing a version out of the
banner keeps working. The consequence is that ``cyanrip 0.9.3`` and
``cyanrip 0.9.4-rc1 (platterpus-fork-ga04a94b)`` can never be told apart by
version alone — and the launch-time dependency dialog was printing only the
version.

That was a real hole rather than a cosmetic one. Platterpus had been taught to
name the ripper build in the EAC-style log, in the JSON report and in
``--doctor``, per CLAUDE.md's *"Say which build produced an artifact"* rule —
but not in **the one surface a user actually reads at launch**. The maintainer
found it by reading the dialog and asking why their fork wasn't distinguished.
The rule was right; it had simply not been applied everywhere, which is the
recurring failure mode this codebase keeps paying for (enforce a rule across the
codebase, not at the place it was learned — ``docs/testing.md`` §5.o).

**Design.** A build note is a small pure value: text in (the probe's captured
output), a dataclass out. Classification is *delegated*, never re-implemented —
:mod:`platterpus.ripper_identity` is the single shared classifier, so the log,
the report, ``--doctor`` and this dialog cannot describe the same binary four
different ways. Adding a build note for a future dependency is one function
here plus one field on its :class:`~platterpus.deps.registry.DependencySpec`;
nothing in the UI learns a tool's name (Critical rule #6 — dependency knowledge
stays inside the subsystem).

**Tri-state, like everywhere else.** ``ok`` is ``True`` / ``False`` / ``None``:
"this is the build we want", "this is definitely not", and "we could not tell".
An uncaptured banner must never render as "unmodified upstream" — that is a
claim we do not have.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from platterpus.deps.checks import ProbeResult
from platterpus.ripper_identity import identify_from_banner

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class BuildNote:
    """Which build of a dependency is installed, and whether that's the wanted one.

    - ``ok``: ``True`` (the wanted build), ``False`` (definitely not it), or
      ``None`` (could not determine — never collapsed to ``False``).
    - ``summary``: a few words to sit next to the version in a one-line list,
      e.g. ``"unmodified upstream, not the Platterpus fork"``.
    - ``detail``: the full sentence for a tooltip, a log line, or the
      needs-attention block. Explains what the difference costs the user.
    - ``fix_hint``: what to do about it, when there is something to do.
      Empty when ``ok`` is ``True``.
    - ``version_text``: the tool's **own** version string, verbatim, with the
      tool name stripped — e.g. ``"0.9.4-rc1+platterpus.5-beta.5"``. ``""`` when
      no banner was captured.
    - ``build_tag``: the parenthetical build tag, e.g.
      ``"platterpus-fork-g9048082"``. ``""`` when the banner carried none.

    **Why the last two exist.** The dependency dialog printed
    ``cyanrip 0.9.4 (the Platterpus fork)`` for a binary whose own banner reads
    ``cyanrip 0.9.4-rc1+platterpus.5-beta.5 (platterpus-fork-g9048082)`` — every
    word accurate, the message wrong, and the maintainer found it by reading the
    dialog on the rig (2026-08-05). Two independent losses met there:
    :func:`platterpus.deps.version.parse_version` reduces a version to an int
    triple, so ``-rc1+platterpus.5-beta.5`` is *structurally* unrepresentable,
    and the old ``summary`` collapsed the build to four words. **Both facts were
    already in the object this dataclass is built from** — which makes it the
    captured-and-discarded shape ``CLAUDE.md`` calls the worse kind, and rule
    #12's *say which build* obligation unmet on the one surface a user reads.
    Carrying them here means the dialog can show a commit at no new cost.
    """

    ok: bool | None
    summary: str
    detail: str
    fix_hint: str = ""
    version_text: str = ""
    build_tag: str = ""

    def identity_line(self, display_name: str) -> str:
        """``"cyanrip 0.9.4-rc1+platterpus.5 (the fork, build …)"`` for a list row.

        Falls back gracefully: with no banner captured it degrades to
        ``"<name> (<summary>)"`` rather than inventing a version, and with no
        build tag it simply omits the ``build …`` clause. A caller that wants the
        parsed int-triple version instead (the generic path for deps with no
        build note) formats that itself — this method only ever reports what the
        tool actually said about itself.
        """
        head = f"{display_name} {self.version_text}".strip()
        qualifier = self.summary
        if self.build_tag:
            # `; build tag "…"` rather than `, build …`: the summary for an
            # unrecognised binary is itself the words "build not identified", and
            # a comma there produced "build not identified, build g1a2b3c4".
            # Quoting the tag also makes it obviously a verbatim string from the
            # binary rather than our description of it.
            qualifier = f'{qualifier}; build tag "{self.build_tag}"'
        return f"{head} ({qualifier})"

    @property
    def needs_attention(self) -> bool:
        """True when the installed build is not the one the project wants.

        ``None`` counts as needing attention: "we could not tell which cyanrip
        this is" is exactly the state a user should be told about, even though
        it is not the same claim as "this is stock".
        """
        return self.ok is not True


#: What the wizard installs and what every fork-only feature depends on. Kept
#: here as text rather than imported from the fork-source module so this module
#: stays free of build machinery; the pin itself lives in
#: :mod:`platterpus.deps.fork_source` and is asserted equal by a test.
_FORK_FIX_HINT: str = (
    "Tools → Set up Platterpus… rebuilds the container's cyanrip from the "
    "Platterpus fork and re-exports it to ~/.local/bin."
)


def cyanrip_build_note(probe: ProbeResult) -> BuildNote:
    """Fork / stock / unknown for a probed cyanrip, from its ``-V`` banner.

    ``check_cyanrip`` keeps the banner in :attr:`ProbeResult.raw_output`, which
    is the same text ``--doctor`` classifies — so both reach the same verdict by
    construction rather than by two people writing two regexes.

    Never raises: it is fed external tool output, and a dependency dialog that
    crashes because a banner was odd is strictly worse than one that says
    "could not tell".
    """
    identity = identify_from_banner(probe.raw_output or "")
    # `identity.version` is the banner head, tool name included
    # ("cyanrip 0.9.4-rc1+platterpus.5-beta.5"). Strip the name here, inside the
    # cyanrip-specific note function, so the shared dataclass never has to know
    # what any tool calls itself (Critical rule #6 — dependency knowledge stays
    # in the subsystem).
    version_text = _strip_tool_name(identity.version, "cyanrip")

    if identity.kind == "fork":
        return BuildNote(
            ok=True,
            summary="the Platterpus fork",
            detail=identity.detail,
            version_text=version_text,
            build_tag=identity.build_tag,
        )

    if identity.kind == "stock":
        return BuildNote(
            ok=False,
            summary="unmodified upstream, NOT the Platterpus fork",
            version_text=version_text,
            build_tag=identity.build_tag,
            detail=(
                "This is an unmodified upstream cyanrip. Rips made with it have "
                "no per-track pre-gap length or provenance, no sample peak and "
                "no per-track timings, so their logs cannot reach EAC parity "
                "and are not interchangeable with fork rips as evidence."
            ),
            fix_hint=_FORK_FIX_HINT,
        )

    # Unknown — including the common "the probe found the binary but we never
    # captured a banner" case. Say so; do not guess either way.
    return BuildNote(
        ok=None,
        summary="build not identified",
        detail=identity.detail,
        fix_hint=_FORK_FIX_HINT,
        # Still carried: an unrecognised tag is exactly the case where a reader
        # needs to see the raw strings, and dropping them here would leave the
        # user with "build not identified" and no way to say what it *was*.
        version_text=version_text,
        build_tag=identity.build_tag,
    )


def _strip_tool_name(banner_head: str, tool: str) -> str:
    """``"cyanrip 0.9.4-rc1"`` → ``"0.9.4-rc1"``; anything else passes through.

    Only the leading word is removed, and only when it matches ``tool``, so a
    banner that does not start with the expected name is reported verbatim rather
    than silently truncated.
    """
    head = banner_head.strip()
    first, _, rest = head.partition(" ")
    if first.casefold() == tool.casefold() and rest.strip():
        return rest.strip()
    return head


#: The type a spec's ``build_note`` field must satisfy. Named so the registry's
#: annotation reads as intent rather than as a bare ``Callable`` soup.
BuildNoteProbe = Callable[[ProbeResult], BuildNote]
