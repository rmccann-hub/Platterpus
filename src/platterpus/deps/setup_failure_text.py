# SPDX-License-Identifier: GPL-3.0-only
"""Turn a failed setup step into a sentence a person can act on.

**Why this module exists (UX review of 0.7.127, finding F3).** When a host-setup
step failed, the setup window showed the step's raw detail as its headline, e.g.::

    Setup stopped at "Distrobox": command not found: pkexec ([Errno 2] …)

Every word of that is true, and it tells a non-technical user nothing: not what
``pkexec`` is, not what went wrong in their terms, not what to do next. The raw
text is still the most important evidence we have — CLAUDE.md asks us to capture
everything and to *show the user the dependency's own sentence* — so it is not
dropped. It moves BELOW a plain sentence that leads, into the window's details
line, and the full output stays in the log.

**What this module is.** One pure function, :func:`explain_setup_failure`, that
reads a failed step's id and its detail (the last line a command printed, or the
step engine's own ``command not found`` / ``timed out`` / ``exit N`` text, see
``deps/step_engine.py`` and ``HostSetup._run_commands``) and returns a
:class:`SetupFailureText`: which known cause it is, a headline, an action, and
the raw text unchanged. No Qt: ``ui/host_setup_dialog.py`` renders it.

**It parses external output, so it never raises** (CLAUDE.md, *Subprocess output
parsing*). The detail is whatever ``dnf``, ``apt-get``, ``pkexec``, ``podman``,
``distrobox``, ``git`` or ``meson`` happened to print last; its wording drifts
between versions and distributions. Every pattern below is a case-insensitive
search, an unrecognised detail falls through to the ``UNKNOWN`` cause, and
``tests/test_setup_failure_text.py`` holds a hypothesis "never raises" property.

**Order matters, and it is deliberate.** The checks run from the most specific
cause to the most general one. A missing ``pkexec`` is checked before the step it
happened in, because "install Distrobox" is the wrong advice when the real
problem is that we could not even ask for a password to install it. A network
failure is checked before "the build failed", because a build that could not
download its sources is a connection problem, not a build problem.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from platterpus.deps.host_setup import MANUAL_INSTALL_HINTS


class SetupFailureCause(Enum):
    """The known reasons a setup step fails, as far as its output can tell us."""

    #: ``pkexec`` (the graphical password prompt) is not installed.
    PKEXEC_MISSING = "pkexec_missing"
    #: The password prompt was cancelled, refused, or could not be shown.
    AUTH_REFUSED = "auth_refused"
    #: Distrobox is missing, or installing it failed.
    DISTROBOX_MISSING = "distrobox_missing"
    #: No container runtime (Podman or Docker) is installed.
    CONTAINER_RUNTIME_MISSING = "container_runtime_missing"
    #: A download failed: no connection, DNS, or a server that did not answer.
    NO_NETWORK = "no_network"
    #: A step ran past the step engine's time limit and was stopped.
    TIMED_OUT = "timed_out"
    #: Building or installing the ripper inside the container failed.
    BUILD_FAILED = "build_failed"
    #: None of the above; the raw text is all we have.
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class SetupFailureText:
    """What the setup window says about one failed step.

    ``headline`` leads (what happened, in plain words), ``action`` follows (what
    to do now), and ``raw`` is the step's own detail, unchanged, for the details
    line. ``cause`` is for the log and for tests, never shown on its own.
    """

    cause: SetupFailureCause
    headline: str
    action: str
    raw: str


#: The retry button's label, used inside the action sentences. The dialog passes
#: its own (the ripper-update copy says "Try again"), so the sentence names the
#: button the user can actually see.
DEFAULT_RETRY_LABEL: str = "Re-run setup"

# --- Patterns ---------------------------------------------------------------
# Each is searched case-insensitively anywhere in the detail. They match the
# tools' own phrasing, quoted in the comment beside each, so a reader can tell
# what output a pattern was written for.

# The step engine's own text for a program that is not on PATH:
# "command not found: pkexec ([Errno 2] No such file or directory: 'pkexec')".
# Each spelled out whole, so tests/test_regex_bounded_time.py can time it.
_PKEXEC_MISSING = re.compile(r"command not found: ?pkexec\b", re.IGNORECASE)
_DISTROBOX_MISSING = re.compile(r"command not found: ?distrobox", re.IGNORECASE)
_RUNTIME_MISSING = re.compile(
    r"command not found: ?(?:podman|docker)\b"
    # distrobox-create: "Missing dependency: we need a container manager."
    r"|need a container manager"
    # distrobox: "Please install one of podman, docker or lilipod."
    r"|install one of podman",
    re.IGNORECASE,
)

# pkexec's own words when the polkit prompt does not end in a yes:
# "Error executing command as another user: Not authorized" (followed by
# "This incident has been reported." as the LAST line, which is the one the
# step engine keeps), "Request dismissed" (the user pressed Cancel),
# "No authentication agent found." (no prompt could be shown at all), and
# "==== AUTHENTICATION FAILED ====".
_AUTH_REFUSED = re.compile(
    r"not authori[sz]ed"
    r"|this incident has been reported"
    r"|request dismissed"
    r"|authentication agent"
    r"|authentication failed"
    r"|error executing command as another user",
    re.IGNORECASE,
)
# pkexec's exit codes when it printed nothing the engine kept: 126 is "the user
# dismissed the dialog", 127 is "not authorised or authentication failed". They
# only mean that for the steps that run through pkexec.
_PKEXEC_EXIT = re.compile(r"^\s*exit\s+12[67]\s*$", re.IGNORECASE)
#: The steps that install a HOST package (Distrobox, then Podman) with ``pkexec``
#: (``install_argv``): exactly the steps that have a manual-install hint. Read
#: from there rather than spelled out, so the step ids live in ``host_setup``.
_ELEVATED_STEPS: frozenset[str] = frozenset(MANUAL_INSTALL_HINTS)
#: The one of those that installs the container runtime; the other is Distrobox.
_RUNTIME_STEP: str = "backend"

# Download failures, in the wording of curl/dnf/apt/git/podman/Go's resolver.
_NO_NETWORK = re.compile(
    r"could not resolve host"
    r"|couldn't resolve host"
    # glibc's "Temporary failure in name resolution"; apt's "Temporary failure
    # resolving 'archive.ubuntu.com'".
    r"|temporary failure (?:in name resolution|resolving)"
    r"|name or service not known"
    r"|no such host"
    r"|network is unreachable"
    r"|no route to host"
    r"|connection (?:timed out|refused|reset)"
    r"|failed to connect to"
    r"|tls handshake timeout"
    r"|i/o timeout"
    r"|curl error"
    r"|cannot download"
    r"|failed to download"
    r"|errors? during downloading metadata"
    r"|cannot retrieve repository"
    r"|unable to access 'https?://"
    r"|failed to fetch",
    re.IGNORECASE,
)
# The step engine's own text when a step exceeds its time limit:
# "timed out after 1800s: <argv>".
_TIMED_OUT = re.compile(r"^\s*timed out after\b", re.IGNORECASE)

#: Steps that install or build the ripper inside the container. A failure here
#: that is not a download problem is a build problem, and the build's own output
#: (meson, ninja, git, dnf) is in the log, not in the one line we kept.
_BUILD_STEPS: frozenset[str] = frozenset({"tools", "cyanrip", "cyanrip_fork"})


def _runtime_missing(raw: str, then_retry: str) -> SetupFailureText:
    """No Podman/Docker: by its own words, or because the step installing it failed."""
    return SetupFailureText(
        SetupFailureCause.CONTAINER_RUNTIME_MISSING,
        "No container program (Podman) is installed, so the container the "
        "ripper runs in can't be created.",
        "Install Podman with your software centre (or your distribution's "
        f"package manager), {then_retry}",
        raw,
    )


def _distrobox_missing(raw: str, then_retry: str) -> SetupFailureText:
    """No Distrobox: by its own words, or because the step installing it failed.

    The step's manual-install sentence (``MANUAL_INSTALL_HINTS``) names
    Distrobox's install page; the action keeps that address rather than leaving it
    only in the details line.
    """
    return SetupFailureText(
        SetupFailureCause.DISTROBOX_MISSING,
        "Distrobox, the tool that runs the ripper's container, isn't installed, "
        "and setup couldn't install it.",
        "Install Distrobox with your software centre, or follow "
        f"https://distrobox.it/#installation, {then_retry}",
        raw,
    )


def explain_setup_failure(
    step_id: str,
    title: str,
    detail: str,
    *,
    retry_label: str = DEFAULT_RETRY_LABEL,
) -> SetupFailureText:
    """Map one failed setup step to a plain headline and an action.

    ``step_id`` is the step engine's id (``"distrobox"``, ``"backend"``,
    ``"cyanrip_fork"`` …), ``title`` its display name, ``detail`` its raw failure
    text. ``retry_label`` is the retry button's visible label, so the action
    names the button on screen. Pure, and never raises: an input it does not
    recognise gets the ``UNKNOWN`` cause and a generic sentence.
    """
    # Coerce once, defensively: these come from another module's dataclass, and a
    # None slipping through must not take the failure report down with it.
    step = step_id if isinstance(step_id, str) else ""
    name = (title if isinstance(title, str) else "") or "a setup step"
    raw = detail if isinstance(detail, str) else ""
    retry = (retry_label if isinstance(retry_label, str) else "") or DEFAULT_RETRY_LABEL
    then_retry = f"then press {retry}."

    # The thing to install by hand when we could not install it ourselves. Named
    # per step, because "install the missing program" is a riddle.
    install_what = "Podman" if step == _RUNTIME_STEP else "Distrobox"

    if _PKEXEC_MISSING.search(raw):
        return SetupFailureText(
            SetupFailureCause.PKEXEC_MISSING,
            "Setup couldn't ask for your password: the program that shows the "
            "password prompt (pkexec) isn't installed on this system, so it "
            "can't install system packages for you.",
            f"Install {install_what} yourself with your software centre (or your "
            f"distribution's package manager), {then_retry}",
            raw,
        )
    if _AUTH_REFUSED.search(raw) or (
        step in _ELEVATED_STEPS and _PKEXEC_EXIT.match(raw)
    ):
        return SetupFailureText(
            SetupFailureCause.AUTH_REFUSED,
            "Setup needs your password to install system packages, and the "
            "password prompt was cancelled, refused or could not be shown.",
            f"Press {retry} and enter your password when asked. If no password "
            f"prompt appears at all, install {install_what} with your software "
            f"centre instead, {then_retry}",
            raw,
        )
    if _RUNTIME_MISSING.search(raw):
        return _runtime_missing(raw, then_retry)
    if _DISTROBOX_MISSING.search(raw):
        return _distrobox_missing(raw, then_retry)
    if _NO_NETWORK.search(raw):
        return SetupFailureText(
            SetupFailureCause.NO_NETWORK,
            "Setup couldn't download what it needs: the internet connection "
            "failed, or a download server didn't answer.",
            f"Check that you're online, {then_retry} Steps that already "
            "finished are skipped.",
            raw,
        )
    if _TIMED_OUT.search(raw):
        return SetupFailureText(
            SetupFailureCause.TIMED_OUT,
            f"“{name}” took too long and was stopped. This is usually a slow or "
            "stalled download.",
            f"Check your connection, {then_retry} Steps that already finished "
            "are skipped.",
            raw,
        )
    # Step-based fallbacks, AFTER the download and timeout checks: a package
    # manager that could not reach its mirror while installing Distrobox is a
    # connection problem, and saying "install Distrobox" would send the user to
    # the software centre that cannot reach the same mirror either.
    if step == _RUNTIME_STEP:
        return _runtime_missing(raw, then_retry)
    if step in _ELEVATED_STEPS:
        return _distrobox_missing(raw, then_retry)
    if step in _BUILD_STEPS:
        return SetupFailureText(
            SetupFailureCause.BUILD_FAILED,
            "Installing or building the ripping tools inside their container failed.",
            "Press Open log to read what the build printed. Then press "
            f"{retry}; if it fails the same way, report it on the project's "
            "issue page with that file attached.",
            raw,
        )
    return SetupFailureText(
        SetupFailureCause.UNKNOWN,
        f"Platterpus doesn't recognise why “{name}” failed.",
        f"The tool's own words are below, and Open log has its full output. "
        f"Press {retry} to try again; if it fails the same way, report it on the "
        "project's issue page with that file attached.",
        raw,
    )


__all__ = [
    "DEFAULT_RETRY_LABEL",
    "SetupFailureCause",
    "SetupFailureText",
    "explain_setup_failure",
]
