"""Script verbs that ask what the INSTALLED ripper build can do.

A mixin :class:`~platterpus.uiscript.runner.ScriptRunner` inherits, like the
other ``*_verbs`` modules, so each handler is reachable as ``runner._do_<verb>``
while the runner file does not grow.

* ``expect-ripper-bounds-overread`` — the installed cyanrip bounds ``-O``: each
  frame outside the disc is read once and counted in a ``Beyond disc:`` line.
  ``overreadprobe.txt`` stops on it before it sends ``-O`` (TASKS R24).

**Why a verb and not a typed build tag.** The probe's first step was
``expect-cyanrip platterpus-fork-g93afa15``: ``.24``'s tag, written into the
script. Every later build bounds ``-O`` the same way, and the check still
refused all of them, so the probe could not run on the build the owner's rig
had. Which builds bound it is ONE fact, kept in
:data:`platterpus.deps.fork_source.BUILD_TAGS_BOUNDING_OVERREAD` with each
build's source citation; this verb asks it, as ``expect-ripper-under-review``
asks ``PIN_UNDER_REVIEW`` (``CLAUDE.md``: a new testing capability is a script
verb).

Reads the build tag the run has latched from a ``cyanrip --version`` banner
(``ScriptRunner._latch_ripper_identity``). Nothing here blocks: it compares two
strings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from platterpus.uiscript.report import Outcome

if TYPE_CHECKING:
    from platterpus.uiscript.script import Step


class RipperBuildVerbsMixin:
    """The ``expect-ripper-bounds-overread`` handler. Type-only declarations of
    the runner surface it uses; the attributes themselves are the runner's."""

    if TYPE_CHECKING:
        _ripper_build_tag: str

        def _record(
            self,
            step: Step,
            outcome: Outcome,
            detail: str = "",
            *,
            elapsed: float = 0.0,
            artifact: str = "",
            declined_by_size: bool = False,
        ) -> None: ...

    def _do_expect_ripper_bounds_overread(self, step: Step) -> None:
        """``expect-ripper-bounds-overread`` — PASS only on a build that bounds ``-O``.

        **Tri-state, and both refusals stop the probe.** A build known not to
        bound it (``.23`` and earlier, which hung the rig's drive for about 23
        minutes) is a FAIL. A build Platterpus cannot place is an ERROR, *not
        determined*, never reported as unbounded; ``abort-if-failed`` stops on
        both, because sending ``-O`` to a build nobody has read is the risk the
        step exists to refuse. The remedy names the approved pin, which is in the
        set (``tests/test_overread_probe_gate.py`` holds that).
        """
        from platterpus import build_info
        from platterpus.deps import fork_source

        tag = self._ripper_build_tag
        if not tag:
            self._record(
                step,
                Outcome.ERROR,
                "no cyanrip build has been read yet, so whether it bounds -O is not "
                "determined — put `cyanrip --version` above this step",
            )
            return
        verdict = fork_source.bounds_overread(tag)
        if verdict is True:
            self._record(
                step,
                Outcome.PASS,
                f"installed build {tag} bounds -O: each frame outside the disc is "
                "read once, and its track says so in a `Beyond disc:` line",
            )
            return
        remedy = (
            f"Install the approved build ({fork_source.FORK_BRANCH}-g"
            f"{fork_source.FORK_PIN}), which does:\n"
            f"    {build_info.self_invocation()} --install-ripper "
            f"{fork_source.FORK_PIN}\nthen run this script again."
        )
        if verdict is False:
            self._record(
                step,
                Outcome.FAIL,
                f"installed build {tag} does NOT bound -O: it reads outside the "
                "disc through paranoia's retries, which hung the BDR-209D for "
                f"about 23 minutes on 2026-07-22. {remedy}",
            )
            return
        self._record(
            step,
            Outcome.ERROR,
            f"whether installed build {tag} bounds -O is not determined: it is "
            "not one whose source Platterpus has read, so -O is not sent to it. "
            + remedy,
        )
