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

import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType

import pytest

from platterpus.deps import fork_source
from platterpus.deps.host_setup import DEFAULT_CONTAINER


def _handshake() -> ModuleType:
    """Load `scripts/handshake.py`, which owns the handshake file ordering.

    Imported rather than re-implemented: `sort_key` is the single definition of "which
    handshake file is newer", and this file used to carry the third copy of it.
    """
    script = Path(__file__).resolve().parents[1] / "scripts" / "handshake.py"
    spec = importlib.util.spec_from_file_location("handshake_ordering", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


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
    # `handshake.sort_key`, not a local sort. This test had its own `(round, name)`
    # key and it was the THIRD copy of that ordering in the repo; all three broke when
    # the naming migration mixed `round-7.md` with `round-07-lap-16.md`, because
    # lexically `"round-07-lap-16" < "round-7"`. This one then read the fork's lap-1
    # file as the newest round and reported the test pin as unnamed.
    inbound = sorted(
        (REPO_ROOT / "docs" / "handshake" / "inbound").glob("round-*.md"),
        key=_handshake().sort_key,
    )
    assert inbound, "no inbound files — cannot check a test pin against the record"
    newest = inbound[-1]
    text = newest.read_text(encoding="utf-8")

    # OUR OWN NEWEST LAP COUNTS TOO, but only if it DECLARES the pin in the wire
    # header — not if the sha merely appears somewhere in its prose.
    #
    # **Why this arm exists** (round 7 lap 34). A test pin is the fork's to nominate,
    # which is why the check reads the *inbound* record and why that is the right
    # default. But `beta.8` / `92ceeed` reached us **out of band** — reported by the
    # maintainer, who is the one holding the rig — while both sides' newest laps still
    # named `4a35604`. The record and the machine disagreed, with hardware about to
    # run on the machine.
    #
    # Refusing outright would mean shipping an app that installs a build the rig does
    # not have. Accepting silently would defeat the whole guard. So: we may declare a
    # pin first, and the declaration has to be a `HANDSHAKE-TEST-PIN` line in a lap we
    # actually wrote and sent — which lap 34 is, and which asks them to confirm it in
    # as many words. A sha mentioned in passing still fails, because "the record names
    # it" has to mean *declared*, not *discussed*.
    if target.pin not in text:
        ours = sorted(
            (REPO_ROOT / "docs" / "handshake" / "verified").glob("round-*.md"),
            key=_handshake().sort_key,
        )
        declared = ""
        if ours:
            for line in ours[-1].read_text(encoding="utf-8").splitlines():
                if line.startswith("HANDSHAKE-TEST-PIN:"):
                    declared = line.split(":", 1)[1].strip()
                    break
        assert declared == target.pin, (
            f"{newest.name} does not name test pin {target.pin!r}, and our newest lap "
            f"({ours[-1].name if ours else 'none'}) does not DECLARE it either "
            f"(HANDSHAKE-TEST-PIN reads {declared!r}) — the wizard would build a commit "
            "no side put in the record, which is how a retired pin gets installed for a "
            "hardware session"
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
        fork_source.FORK_SOURCE_SUBPATH,
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
        fork_source.FORK_SOURCE_SUBPATH,
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


# --- The `$HOME` defect: paths, expansion, and the guard --------------------


def test_the_source_subpath_carries_no_shell_variable() -> None:
    """REGRESSION (real-user log, 2026-08-04, v0.6.4b2).

    This constant was the literal ``"$HOME/.cache/platterpus/cyanrip-fork"`` with a
    comment claiming the container's shell would expand it. **Parameter expansion
    does not recurse:** the script did ``src="$1"``, so ``$HOME`` stayed 5 literal
    characters and every path became relative to a directory *named* ``$HOME``. The
    user's own log said::

        Source dir: /home/rmccann/$HOME/.cache/platterpus/cyanrip-fork

    The build still succeeded — right commit, right version, 31/31 targets — because
    clone, configure, compile and install all used the same wrong string and agreed
    with each other. The only casualty was meson's ``vcs_tag``, which fell back to
    upstream's literal ``release``, so the binary reported
    ``platterpus-fork-grelease``: a build tag naming no commit.
    """
    assert "$" not in fork_source.FORK_SOURCE_SUBPATH
    assert not fork_source.FORK_SOURCE_SUBPATH.startswith("/"), (
        "the subpath is relative to $HOME by design — the script prefixes it"
    )
    assert not hasattr(fork_source, "FORK_SOURCE_DIR"), (
        "FORK_SOURCE_DIR was the `$HOME`-bearing constant; it must not come back"
    )


def test_no_command_ships_an_unexpanded_variable_to_the_container() -> None:
    """The sweep, not the single case. ANY argv with a `$` is the same defect.

    Checked across the whole plan rather than the two commands known to have had
    it, because the failure mode is invisible when every consumer is wrong the same
    way — which is exactly how it survived.
    """
    for argv in fork_source.fork_build_commands(CONTAINER):
        # The script BODIES legitimately contain `$1`/`$HOME` — that is the fix.
        # It is the *arguments* that must be literal.
        script_idx = argv.index("-c") + 1 if "-c" in argv else -1
        for i, arg in enumerate(argv):
            if i == script_idx:
                continue
            assert "$" not in arg, (
                f"argv element {arg!r} carries an unexpanded shell variable; it will "
                f"arrive at the container literally (full argv: {argv})"
            )


def test_the_build_and_install_scripts_expand_home_at_the_point_of_use() -> None:
    """Both must prefix `$HOME` themselves, and both must agree.

    Fixing only the build would leave the install copying from a path that no
    longer exists — the two were consistent in being wrong, so they have to stay
    consistent in being right.
    """
    build = fork_source.build_command(CONTAINER)
    install = fork_source.install_command(CONTAINER)
    for argv in (build, install):
        script = argv[argv.index("-c") + 1]
        assert 'src="$HOME/$1"' in script, (
            f"script does not expand $HOME at the point of use:\n{script[:200]}"
        )
        assert fork_source.FORK_SOURCE_SUBPATH in argv, (
            "the subpath must arrive as its own argument, never spliced into the body"
        )


@pytest.mark.parametrize(
    "bad",
    [
        "$HOME/.cache/platterpus/cyanrip-fork",  # the actual defect
        "/absolute/path",
        "../escape",
        "a/../../b",
        "has space; rm -rf /",
        "back`tick`",
        "quote'd",
        'double"quote',
        "pipe|it",
        "amp&it",
        "glob*star",
        "",
        "  padded  ",
    ],
)
def test_the_chokepoint_guard_rejects_what_a_shell_would_mangle(bad: str) -> None:
    """CLAUDE.md: validate outputs to dependencies **at the argv chokepoint**, in
    code — not merely stated in a doc. The `$` case is the one that shipped."""
    with pytest.raises(ValueError):
        fork_source.assert_shell_safe_subpath(bad)


def test_the_chokepoint_guard_accepts_the_real_subpath() -> None:
    """The converse — so the guard cannot pass by rejecting everything."""
    assert (
        fork_source.assert_shell_safe_subpath(fork_source.FORK_SOURCE_SUBPATH)
        == fork_source.FORK_SOURCE_SUBPATH
    )


def test_the_build_script_reports_the_paths_it_resolved() -> None:
    """The diagnostics that would have ended this in seconds instead of two rounds.

    The failure was *entirely* visible in a path, and nothing printed the path.
    """
    argv = fork_source.build_command(CONTAINER)
    script = argv[argv.index("-c") + 1]
    for needed in (
        "HOME=$HOME",
        "cwd=$(pwd)",
        "source tree=$src",
        "rev-parse HEAD",
        "status --porcelain",
        "built banner=",
    ):
        assert needed in script, f"the build script never reports {needed!r}"


def test_the_build_script_refuses_a_relative_or_variable_bearing_source_tree() -> None:
    """Belt to the Python guard's braces — the shell checks its own `$src` too.

    Two independent expressions, deliberately: the Python guard protects the value
    we pass, and this protects against a `$HOME` that is itself unset or odd inside
    the container, which Python cannot see.
    """
    argv = fork_source.build_command(CONTAINER)
    script = argv[argv.index("-c") + 1]
    assert "is not an absolute path" in script
    assert "unexpanded variable" in script


def test_the_verify_error_names_the_banner_it_ACTUALLY_saw() -> None:
    """The single missing string that cost two sessions.

    The old message said only "does not identify as the pinned fork build ($2)" —
    what we EXPECTED. The observed banner was printed one line earlier on stdout,
    and `HostSetup._run_commands` keeps only the LAST line for the UI, so the one
    fact that mattered was discarded exactly when it mattered. The answer was
    `platterpus-fork-grelease` — not a wrong commit, a tag naming *no* commit.
    """
    argv = fork_source.verify_command(CONTAINER)
    script = argv[argv.index("-c") + 1]
    assert "reports" in script and "$banner" in script, (
        f"the verify error does not quote the observed banner:\n{script}"
    )
    assert "grelease" in script, (
        "the vcs_tag-fallback case has a specific cause and deserves its own "
        "sentence — a user should not need to know meson internals to act on it"
    )
