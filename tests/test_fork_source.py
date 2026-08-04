"""The wizard's plan for installing the pinned Platterpus fork of cyanrip.

The commands cannot be executed here — there is no Distrobox, no container, and
no compiler for a foreign source tree in CI — so what is testable is the *plan*:
its order, its shape, the safety of how values reach the shell, and the fact that
the pin the code builds is the pin the handshake record says was verified.

That last one is the point of this file. A pin that lives only in a constant
drifts from the round that approved it, and "which commit is my ripper" then has
two answers. So the constant is checked against the committed handshake
document — reading the artifact, not remembering it.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from platterpus.deps import fork_source
from platterpus.deps.host_setup import DEFAULT_CONTAINER

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTAINER = DEFAULT_CONTAINER


# --- provenance: the pin matches the record ---------------------------------


def test_the_pin_is_the_one_the_newest_closed_handshake_round_verified() -> None:
    """Read the artifact, do not trust the memory of it.

    ``docs/handshake/verified/round-N.md`` is our own GO for a specific commit.
    If the constant and the document disagree, one of them is wrong and the
    disagreement IS the bug report — exactly the reasoning the fork and we agreed
    on for two independent expressions of one contract.
    """
    verified = sorted(
        (REPO_ROOT / "docs" / "handshake" / "verified").glob("round-*.md"),
        key=lambda p: int(re.search(r"round-(\d+)", p.name).group(1)),  # type: ignore[union-attr]
    )
    assert verified, "no verification files — cannot check the pin against the record"
    newest = verified[-1]
    text = newest.read_text(encoding="utf-8")
    assert fork_source.FORK_PIN in text, (
        f"{newest.name} does not mention pin {fork_source.FORK_PIN!r}; the wizard "
        f"would build a commit no closed round approved"
    )


def test_the_expected_build_tag_is_derived_not_typed() -> None:
    """cyanrip prints ``(<PROJECT_FORK_ID>-g<short sha>)``. Deriving the expected
    tag from the branch and pin means bumping the pin cannot leave a stale
    literal behind that silently accepts the wrong binary."""
    assert fork_source.FORK_EXPECTED_BUILD_TAG == (
        f"{fork_source.FORK_BRANCH}-g{fork_source.FORK_PIN}"
    )


def test_build_and_verify_cannot_be_given_different_builds() -> None:
    """The property the ``ForkTarget`` seam exists for.

    Before it, the build step read ``FORK_PIN`` and the verify step read
    ``FORK_EXPECTED_BUILD_TAG`` — two module constants that agreed only because one
    derived from the other. With two installable builds (a production pin and a
    mid-round test pin) "build X, assert it printed Y" became two independent edits,
    and getting one wrong installs one binary while checking for another.

    Asserted over BOTH targets, not just the current default: a check that only
    exercises the value in force cannot fail when the *other* one is wrong.
    """
    for target in (fork_source.PRODUCTION_TARGET, fork_source.TEST_TARGET):
        commands = fork_source.fork_build_commands(CONTAINER, target)
        build_argv, verify_argv = commands[1], commands[-1]
        assert target.pin in build_argv, f"{target.pin} is not what gets built"
        assert target.build_tag in verify_argv, (
            f"the verify does not check for {target.build_tag} — the build and the "
            f"check are looking at different binaries"
        )
        # And the pair really is distinguishable, so this cannot pass vacuously by
        # both targets happening to be the same commit.
    assert fork_source.PRODUCTION_TARGET.pin != fork_source.TEST_TARGET.pin, (
        "the two targets are the same commit, so the test above proves nothing"
    )


def test_the_wizard_target_is_named_in_the_handshake_record() -> None:
    """Whatever the wizard installs must be a build the record actually names.

    The production pin is checked against the newest *verified* round (above). A
    **test** pin is nominated by the fork, so it is checked against the newest
    *inbound* round — and that check is the thing that catches a stale one. This
    round's test pin moved twice, each time retiring a build the previous lap told
    us to install; `f750890` in particular could hang an `-x` probe with no
    diagnostic at all, which is precisely the failure the hardware session exists
    to observe.
    """
    target = fork_source.WIZARD_TARGET
    if target == fork_source.PRODUCTION_TARGET:
        return  # covered by the verified-round check above
    inbound = sorted(
        (REPO_ROOT / "docs" / "handshake" / "inbound").glob("round-*.md"),
        key=lambda p: (int(re.search(r"round-(\d+)", p.name).group(1)), p.name),  # type: ignore[union-attr]
    )
    assert inbound, "no inbound files — cannot check a test pin against the record"
    newest = inbound[-1]
    text = newest.read_text(encoding="utf-8")
    assert target.pin in text, (
        f"{newest.name} does not name test pin {target.pin!r} — the wizard would "
        f"build a commit the newest round did not nominate (which is how a retired "
        f"pin gets installed for a hardware session)"
    )
    for retired in fork_source.SUPERSEDED_TEST_PINS:
        assert retired != target.pin, f"{retired} is both current and retired"


def test_the_pin_is_a_short_sha_not_a_branch_or_tag() -> None:
    """A branch name here would install whatever is newest, which is the thing
    the pin exists to prevent."""
    assert re.fullmatch(r"[0-9a-f]{7,40}", fork_source.FORK_PIN)


def test_the_clone_url_is_the_fork_over_https() -> None:
    """HTTPS, not SSH: the wizard runs unattended and must not need a key agent."""
    assert fork_source.FORK_REPO_URL.startswith("https://")
    assert "rmccann-hub/cyanrip" in fork_source.FORK_REPO_URL


# --- the plan ---------------------------------------------------------------


def test_the_step_runs_deps_build_install_export_verify_in_that_order() -> None:
    commands = fork_source.fork_build_commands(CONTAINER)
    joined = [" ".join(c) for c in commands]
    assert len(commands) == 5

    assert "dnf install -y" in joined[0]
    assert "ninja -C" in joined[1]
    assert "install -Dm0755" in joined[2]
    assert "distrobox-export --bin" in joined[3]
    assert "-V" in joined[4]


def test_verification_is_last_because_it_checks_what_was_just_installed() -> None:
    """A verify that ran first could only ever confirm the previous state — which
    on a re-run is the very thing being replaced."""
    commands = fork_source.fork_build_commands(CONTAINER)
    assert commands[-1] == fork_source.verify_command(CONTAINER)


def test_the_verify_fails_the_step_on_a_binary_that_is_not_the_pinned_fork() -> None:
    """The command must actually compare against the expected tag. A verify that
    only ran the binary and ignored its output would pass for stock cyanrip."""
    argv = fork_source.verify_command(CONTAINER)
    assert fork_source.WIZARD_TARGET.build_tag in argv
    assert fork_source.FORK_INSTALL_PATH in argv
    script = next(a for a in argv if "banner=" in a)
    assert "exit 1" in script, "the verify script must fail, not merely print"


def test_every_command_goes_through_distrobox_enter() -> None:
    """Critical rule #3: container work is driven only through Distrobox, and
    only in setup. Nothing here may shell out to podman directly."""
    for argv in fork_source.fork_build_commands(CONTAINER):
        assert argv[:4] == ["distrobox", "enter", CONTAINER, "--"]
        assert "podman" not in argv


def test_the_fork_is_installed_where_it_outranks_the_copr_package() -> None:
    """``/usr/local/bin`` precedes ``/usr/bin`` on Fedora's PATH, so the fork wins
    inside the container too — not only via the host export."""
    assert fork_source.FORK_INSTALL_PATH == "/usr/local/bin/cyanrip"


# --- shell safety -----------------------------------------------------------


def test_no_value_is_spliced_into_the_build_script() -> None:
    """Every value arrives as a positional argument, so nothing in a URL, a
    branch name or a path can be reinterpreted by the shell. The same discipline
    the COPR repo stanza uses.
    """
    argv = fork_source.build_command(CONTAINER)
    script = argv[argv.index("-c") + 1]
    for value in (
        fork_source.FORK_REPO_URL,
        fork_source.FORK_BRANCH,
        fork_source.WIZARD_TARGET.pin,
        fork_source.FORK_SOURCE_DIR,
    ):
        assert value not in script, f"{value!r} is spliced into the script body"
        assert value in argv, f"{value!r} must be passed as its own argument"


def test_the_build_script_has_a_label_argument_so_values_are_not_eaten_as_argv0() -> (
    None
):
    """``sh -c SCRIPT NAME ARG1 …`` binds NAME to ``$0``. Without a throwaway
    label the first real value would land in ``$0`` and every ``$1``… would be
    off by one — a silent, total misconfiguration."""
    argv = fork_source.build_command(CONTAINER)
    after_script = argv[argv.index("-c") + 2 :]
    assert after_script[0] == "build-cyanrip-fork"
    assert after_script[1:] == [
        fork_source.FORK_SOURCE_DIR,
        fork_source.FORK_REPO_URL,
        fork_source.FORK_BRANCH,
        fork_source.WIZARD_TARGET.pin,
    ]


def test_the_build_script_aborts_on_the_first_failure() -> None:
    """Without ``set -e`` a failed clone falls through to "build whatever is
    already in that directory", which installs a stale binary while reporting
    success — the silent-wrong-answer class this project keeps hunting."""
    argv = fork_source.build_command(CONTAINER)
    script = argv[argv.index("-c") + 1]
    assert script.startswith("set -eu")


def test_the_build_detaches_onto_the_pin_rather_than_trusting_the_branch() -> None:
    argv = fork_source.build_command(CONTAINER)
    script = argv[argv.index("-c") + 1]
    assert "checkout --force --detach" in script
    # And it fetches before checking out, so a pin newer than a cached clone
    # still resolves.
    assert script.index("fetch") < script.index("checkout --force --detach")


# --- build dependencies -----------------------------------------------------


def test_build_deps_are_requested_as_pkgconfig_provides_not_package_names() -> None:
    """Fedora's ``ffmpeg-free-devel`` and RPM Fusion's ``ffmpeg-devel`` conflict
    and cannot both be named, so the library deps are requested by the
    pkg-config file they provide and dnf resolves whichever package ships it —
    the same trick the cd-paranoia step uses.
    """
    libs = [p for p in fork_source.FORK_BUILD_PACKAGES if p.startswith("pkgconfig(")]
    assert len(libs) >= 9, "floor: expected the fork's full pkg-config dependency set"
    toolchain = [
        p for p in fork_source.FORK_BUILD_PACKAGES if not p.startswith("pkgconfig(")
    ]
    assert set(toolchain) == {"git", "meson", "ninja-build", "gcc"}


@pytest.mark.parametrize(
    "module",
    [
        # Read off the fork's own src/meson.build at the pin — every
        # `dependency('x')` line it declares.
        "libavcodec",
        "libavformat",
        "libswresample",
        "libavfilter",
        "libavutil",
        "libcdio",
        "libcdio_paranoia",
        "libmusicbrainz5",
        "libcurl",
    ],
)
def test_every_meson_dependency_of_the_fork_is_installed(module: str) -> None:
    """A missing devel package makes ``meson setup`` fail with a message about a
    library rather than about a wizard, so this list is the difference between a
    one-click install and a support thread."""
    assert f"pkgconfig({module})" in fork_source.FORK_BUILD_PACKAGES
