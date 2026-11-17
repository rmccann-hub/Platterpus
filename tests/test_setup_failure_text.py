# SPDX-License-Identifier: GPL-3.0-only
"""Tests for ``deps/setup_failure_text``: a failed setup step, in plain words.

UX review of 0.7.127, finding F3: the setup window led with the step's raw
detail (``command not found: pkexec ([Errno 2] …)``). The mapping is a pure
function, so each known cause is pinned here without a window, and — because it
reads external output — it carries a hypothesis "never raises" property.

The detail strings below are the shapes the step engine really produces: its own
``command not found: X (exc)`` / ``timed out after Ns: argv`` / ``exit N``, the
manual-install hints from ``deps/host_setup.MANUAL_INSTALL_HINTS``, and the LAST
line of a failing command (``HostSetup._run_commands`` keeps only that).
"""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from platterpus.deps.host_setup import MANUAL_INSTALL_HINTS
from platterpus.deps.setup_failure_text import (
    SetupFailureCause,
    SetupFailureText,
    explain_setup_failure,
)

Cause = SetupFailureCause

_PKEXEC_NOT_FOUND = (
    "command not found: pkexec ([Errno 2] No such file or directory: 'pkexec')"
)


@pytest.mark.parametrize(
    ("step_id", "detail", "cause"),
    [
        # The review's own screenshot.
        ("distrobox", _PKEXEC_NOT_FOUND, Cause.PKEXEC_MISSING),
        ("backend", _PKEXEC_NOT_FOUND, Cause.PKEXEC_MISSING),
        # pkexec's words when the prompt does not end in a yes.
        ("distrobox", "This incident has been reported.", Cause.AUTH_REFUSED),
        (
            "backend",
            "Error executing command as another user: Request dismissed",
            Cause.AUTH_REFUSED,
        ),
        (
            "distrobox",
            "Error executing command as another user: No authentication agent found.",
            Cause.AUTH_REFUSED,
        ),
        ("distrobox", "==== AUTHENTICATION FAILED ====", Cause.AUTH_REFUSED),
        # pkexec's exit codes, when it printed nothing the engine kept…
        ("distrobox", "exit 126", Cause.AUTH_REFUSED),
        ("backend", "exit 127", Cause.AUTH_REFUSED),
        # …mean that ONLY for the steps that run through pkexec.
        ("container", "exit 126", Cause.UNKNOWN),
        # Distrobox / Podman missing, by the tool's own words or by the step.
        (
            "container",
            "command not found: distrobox ([Errno 2] No such file or directory)",
            Cause.DISTROBOX_MISSING,
        ),
        ("distrobox", MANUAL_INSTALL_HINTS["distrobox"], Cause.DISTROBOX_MISSING),
        (
            "container",
            "command not found: podman ([Errno 2] No such file or directory)",
            Cause.CONTAINER_RUNTIME_MISSING,
        ),
        (
            "container",
            "Missing dependency: we need a container manager.",
            Cause.CONTAINER_RUNTIME_MISSING,
        ),
        ("backend", MANUAL_INSTALL_HINTS["backend"], Cause.CONTAINER_RUNTIME_MISSING),
        # No network, in several tools' wording — including during a step that
        # would otherwise read as "install Distrobox".
        (
            "distrobox",
            "E: Failed to fetch http://archive.ubuntu.com/... Temporary failure "
            "resolving 'archive.ubuntu.com'",
            Cause.NO_NETWORK,
        ),
        (
            "tools",
            "Error: Failed to download metadata for repo 'fedora': Cannot download "
            "repomd.xml: Curl error (6): Couldn't resolve host name",
            Cause.NO_NETWORK,
        ),
        (
            "container",
            "Error: initializing source docker://registry.fedoraproject.org/...: "
            "pinging container registry: dial tcp: lookup "
            "registry.fedoraproject.org: no such host",
            Cause.NO_NETWORK,
        ),
        (
            "cyanrip_fork",
            "fatal: unable to access 'https://github.com/x/cyanrip.git/': Could "
            "not resolve host: github.com",
            Cause.NO_NETWORK,
        ),
        # The step engine's time limit.
        (
            "container",
            "timed out after 1800s: distrobox create --name ripping",
            Cause.TIMED_OUT,
        ),
        # A build that failed for a reason other than a download.
        (
            "cyanrip_fork",
            "ninja: build stopped: subcommand failed.",
            Cause.BUILD_FAILED,
        ),
        (
            "cyanrip_fork",
            "installed cyanrip does not identify as the pinned fork build",
            Cause.BUILD_FAILED,
        ),
        ("cyanrip", "Error: Unable to find a match: cyanrip", Cause.BUILD_FAILED),
        ("tools", "exit 1", Cause.BUILD_FAILED),
        ("distrobox", "Temporary failure resolving 'deb.debian.org'", Cause.NO_NETWORK),
        # Anything else.
        (
            "export",
            "cp: cannot create regular file: Read-only file system",
            Cause.UNKNOWN,
        ),
        ("container", "", Cause.UNKNOWN),
    ],
)
def test_each_known_cause_is_recognised(
    step_id: str, detail: str, cause: SetupFailureCause
) -> None:
    explained = explain_setup_failure(step_id, "Some step", detail)
    assert explained.cause is cause, (step_id, detail, explained)
    # The raw text is carried unchanged — never dropped, never rewritten.
    assert explained.raw == detail
    # And the words a user reads are sentences, not the raw text again.
    assert explained.headline and explained.action
    assert detail == "" or detail not in explained.headline


def test_the_pkexec_case_says_what_happened_and_what_to_do() -> None:
    """The review's example, word for word in spirit: password, pkexec, install."""
    explained = explain_setup_failure("distrobox", "Distrobox", _PKEXEC_NOT_FOUND)
    assert "password" in explained.headline
    assert "pkexec" in explained.headline  # named, so it can be searched for
    assert "Errno" not in explained.headline
    assert "Install Distrobox" in explained.action
    assert "Re-run setup" in explained.action


def test_the_pkexec_case_on_the_backend_step_names_podman() -> None:
    explained = explain_setup_failure("backend", "Podman", _PKEXEC_NOT_FOUND)
    assert "Install Podman" in explained.action


def test_the_action_names_the_retry_button_it_is_given() -> None:
    """The ripper-update window's button says "Try again"; the sentence must too."""
    explained = explain_setup_failure(
        "cyanrip_fork", "fork", "ninja: build stopped", retry_label="Try again"
    )
    assert "Try again" in explained.action
    assert "Re-run setup" not in explained.action


def test_a_build_failure_points_at_the_log() -> None:
    explained = explain_setup_failure("cyanrip_fork", "fork", "meson: error")
    assert "Open log" in explained.action


def test_an_unknown_cause_names_the_step_and_points_at_the_log() -> None:
    explained = explain_setup_failure("export", "Export tools", "something odd")
    assert explained.cause is Cause.UNKNOWN
    assert "Export tools" in explained.headline
    assert "Open log" in explained.action


def test_a_network_failure_says_finished_steps_are_skipped() -> None:
    """Re-running after a dropped connection must not sound like starting over."""
    explained = explain_setup_failure("container", "c", "Network is unreachable")
    assert explained.cause is Cause.NO_NETWORK
    assert "skipped" in explained.action


@given(st.text(), st.text(), st.text(), st.text())
def test_never_raises(step_id: str, title: str, detail: str, retry: str) -> None:
    """External output: any text at all yields a result, never an exception."""
    explained = explain_setup_failure(step_id, title, detail, retry_label=retry)
    assert isinstance(explained, SetupFailureText)
    assert explained.raw == detail
    assert explained.headline and explained.action


@given(st.sampled_from(["distrobox", "backend", "tools", "cyanrip_fork"]), st.text())
def test_never_raises_for_the_real_step_ids(step_id: str, detail: str) -> None:
    """The same, weighted toward the step ids whose branches are step-specific."""
    explained = explain_setup_failure(step_id, "t", detail)
    assert isinstance(explained.cause, SetupFailureCause)
