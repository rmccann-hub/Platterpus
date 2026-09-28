"""``--install-ripper latest`` / ``latest-beta`` — a channel's head, resolved to a commit.

**What this is.** A resolver in front of
:func:`platterpus.deps.fork_source.target_for_commit`. It reads the fork's release
manifest (:mod:`platterpus.deps.ripper_manifest`), takes the head of the channel the
keyword names, and hands that row's commit to the same function
``--install-ripper <commit>`` uses — together with the version and ``meson setup``
options the manifest states **for that commit**, which is the case
``target_for_commit``'s ``version``/``meson_options`` parameters exist for. From
there it is an ordinary ``--install-ripper <commit>``: the same step engine builds,
installs, exports and verifies it, and the same note says when the build is not the
one a closed round approved.

**Who it is for.** A *script* that wants "whatever the channel says" without
pinning a sha. A person does not need it: the GUI already notices a newer build
and offers it (``ripper_offer``). TASKS, 2026-08-07.

**What it is not.**

* **Not a new install path.** It produces a :class:`ForkTarget`; it installs
  nothing and runs nothing.
* **Not the default, and never a fallback.** A bare ``--install-ripper`` still
  builds what a closed round approved — the pin is the handshake's subject, and an
  installer that quietly fetched "the newest" would defeat the protocol both
  projects built (the TASKS row's closing warning). So a keyword is an explicit
  opt-in, and when the manifest cannot be read the answer is a refusal naming why,
  **not** the approved build instead: a script that asked for the channel head and
  silently got something else would record the wrong build as the one it tested.

**The channel is read from the manifest's key**, exactly as
:func:`platterpus.deps.ripper_offer.evaluate_offer` reads it — ``latest-beta`` is
the ``beta`` row, not "whichever row has the higher sequence". Two surfaces asking
the manifest "what is the beta build?" must get one answer.

**The commit is safe to put on an argv** because the manifest parser refuses
anything that is not a lowercase hex sha (``ripper_manifest._clean_commit``) before
a row exists. Nothing here re-validates it — that would be a second guard with its
own idea of the rule — and nothing here constructs a commit from any other input.

Never raises: every outcome, including "could not tell", is a
:class:`LatestResolution` carrying a sentence for a person.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

from platterpus.deps import ripper_manifest
from platterpus.deps.fork_source import ForkTarget, target_for_commit
from platterpus.deps.ripper_manifest import (
    CHANNEL_BETA,
    CHANNEL_STABLE,
    RipperManifest,
    RipperRelease,
)

log = logging.getLogger(__name__)

#: The keywords ``--install-ripper`` accepts in place of a commit, and the
#: manifest channel each names. Neither can collide with a sha: git needs at least
#: four hex characters, and ``l``, ``t`` and ``s`` are not hex.
LATEST_KEYWORDS: Final[dict[str, str]] = {
    "latest": CHANNEL_STABLE,
    "latest-beta": CHANNEL_BETA,
}

#: Said on every refusal, so "nothing was installed" always arrives with the two
#: routes that DO work — the operator is running a command, not reading a manual.
_ALTERNATIVES: Final[str] = (
    "Nothing was installed. Name a commit instead (--install-ripper <commit>), or "
    "run --install-ripper with no argument for the build a closed round approved."
)


@dataclass(frozen=True)
class LatestResolution:
    """What a keyword resolved to — or why it did not.

    ``target`` is ``None`` exactly when nothing should be installed; ``detail`` is
    always a sentence for a person, printed before any build starts.
    """

    #: The keyword as typed, normalised (``latest`` / ``latest-beta``).
    keyword: str
    #: The manifest channel it names.
    channel: str
    #: The build to install, or ``None`` for a refusal.
    target: ForkTarget | None
    #: The manifest row it came from, when there was one — carried for the caller
    #: that wants the facts (sequence, round) rather than the sentence.
    release: RipperRelease | None
    #: One paragraph for the operator. Never empty.
    detail: str


def channel_for(argument: str) -> str | None:
    """The channel ``argument`` names, or ``None`` when it is not a keyword.

    ``None`` means "treat it as a commit", which is every argument that is not one
    of :data:`LATEST_KEYWORDS` — so adding a keyword never changes what an existing
    commit argument means.
    """
    return LATEST_KEYWORDS.get(argument.strip().lower())


def resolve_latest(keyword: str, manifest: RipperManifest | None) -> LatestResolution:
    """Resolve ``keyword`` against an already-fetched ``manifest``. PURE.

    ``manifest`` is ``None`` when it could not be fetched or parsed —
    :func:`ripper_manifest.fetch_manifest` has already logged which. That is a
    refusal, never "use the approved build instead" (module docstring).
    """
    name = keyword.strip().lower()
    channel = LATEST_KEYWORDS.get(name)
    if channel is None:
        # Not reachable from the CLI, which asks `channel_for` first; answered
        # anyway rather than raised, because this function's contract is a sentence.
        return LatestResolution(
            keyword=name,
            channel="",
            target=None,
            release=None,
            detail=(
                f"{keyword!r} is not one of {sorted(LATEST_KEYWORDS)}. {_ALTERNATIVES}"
            ),
        )
    if manifest is None:
        return LatestResolution(
            keyword=name,
            channel=channel,
            target=None,
            release=None,
            detail=(
                f"--install-ripper {name} could not be resolved: the fork's release "
                "manifest could not be read (no network, or a document this "
                "Platterpus cannot parse — the log says which). " + _ALTERNATIVES
            ),
        )
    row = manifest.channel(channel)
    if row is None:
        return LatestResolution(
            keyword=name,
            channel=channel,
            target=None,
            release=None,
            detail=(
                f"--install-ripper {name} could not be resolved: the fork's release "
                f"manifest carried no usable {channel} entry. " + _ALTERNATIVES
            ),
        )
    target = target_for_commit(
        row.commit, version=row.version, meson_options=row.meson_options
    )
    round_state = "closed" if row.round_closed else "OPEN"
    beta_note = (
        " Beta-channel builds are ones the fork publishes for testing."
        if channel == CHANNEL_BETA
        else ""
    )
    return LatestResolution(
        keyword=name,
        channel=channel,
        target=target,
        release=row,
        detail=(
            f"--install-ripper {name}: the head of the fork's {channel} channel is "
            f"commit {row.commit} (release {row.release_seq}, {row.version}), and "
            f"the fork reports its handshake round {row.handshake_round} as "
            f"{round_state}.{beta_note} Installing it exactly as "
            f"--install-ripper {row.commit} would."
        ),
    )


def resolve_keyword(
    argument: str, fetch: Callable[[str], str] | None = None
) -> LatestResolution | None:
    """``None`` for a commit argument; otherwise fetch the manifest and resolve.

    **Blocking** — it reads the network, bounded by the manifest fetcher's own
    timeout. The one caller is ``--install-ripper``, which runs before any window
    exists; never call this on the GUI thread. ``fetch`` is injectable so no test
    touches the network.
    """
    if channel_for(argument) is None:
        return None
    resolution = resolve_latest(argument, ripper_manifest.fetch_manifest(fetch))
    if resolution.target is None:
        log.error("ripper install refused: %s", resolution.detail)
    else:
        log.info("ripper install resolved: %s", resolution.detail)
    return resolution
