"""Which flag prints cyanrip's version — and why we must try more than one.

**The bug this file exists for.** Every version probe in Platterpus sent ``-V``.
That is correct for cyanrip 0.9.3 and earlier, whose short-only ``getopt`` has a
``case 'V':``. It is *wrong* for every build after that: upstream commit
``442de2a`` replaced the parser with ``genopt.h``, which special-cases only
``-v`` / ``--version`` (``src/genopt.h:497``) and treats ``-V`` as an unparseable
argument — printing a diagnostic and exiting **1**.

A non-zero exit from a version probe is deliberately read as *"this tool is not
available"*, because a failing tool that prints a number is worse than a missing
one. So installing a 0.9.4 build would have made the launch dependency check
report **cyanrip missing** and routed the user to the setup wizard to install the
ripper they had just built. The wizard's own post-install verification would have
failed the same way, on a perfect build.

Caught by the fork's provider contract saying *"-v is version; there is no -V"* —
not by a user. That is the handshake earning its keep.

**Why we still probe with two flags even though the fork restored the alias.**
The fork now accepts all three spellings from pin ``e1d800e``, but that fixes only
*its* binaries. Users are on stock 0.9.3 today (``-V`` only), stock upstream 0.9.4
accepts only the long spellings, and the fork pins between 0.9.4-rc1 and
``e1d800e`` likewise. No single flag covers the set — see the table on
:data:`platterpus.cyanrip_cli.VERSION_FLAGS`. Every build shape below is
exercised, because the point is not "the fork works now".
"""

from __future__ import annotations

import logging
import re
import subprocess
import sys
from pathlib import Path

import pytest

from platterpus.cyanrip_cli import VERSION_BANNER_SNIPPET, VERSION_FLAGS
from platterpus.deps import checks
from platterpus.deps import fork_source as _FORK_SOURCE
from platterpus.deps.checks import check_cyanrip

STOCK_BANNER = "cyanrip 0.9.3 (release)"
#: Derived from the pin, never written out. The literal form of this constant
#: silently expired twice in one day — the pin moved to `ad65a24` and then, hours
#: later, to `25a2265` when round 6b withdrew `ad65a24` — and a hardcoded banner
#: makes the *verify* test fail for a reason that has nothing to do with what it
#: tests. Deriving it means the pin move is a one-line edit in `fork_source.py`.
FORK_BANNER = _FORK_SOURCE.FORK_EXPECTED_BANNER
#: What the WIZARD installs, which is not always the production pin: mid-round a
#: test pin is nominated, and the verify snippet checks for whatever was built.
#: Kept separate from FORK_BANNER because the probe tests only care that a build
#: identifies as the fork, while the verify test cares *which* build.
WIZARD_BANNER = _FORK_SOURCE.WIZARD_TARGET.banner
REJECT = "Unable to parse command line argument: {flag}"


class _FakeProc:
    def __init__(self, rc: int, out: str) -> None:
        self.returncode = rc
        self.stdout = out
        self.stderr = ""


def _binary_answering(
    monkeypatch: pytest.MonkeyPatch, good: set[str], banner: str
) -> list[list[str]]:
    """Fake a cyanrip that exits 0 only for the flags in ``good``.

    Returns the list of argvs actually attempted, so a test can assert the ORDER
    as well as the outcome — "it eventually worked" is a weaker claim than "it
    tried the known-safe flag first".
    """
    attempts: list[list[str]] = []

    def fake_run(argv: list[str], **kwargs: object) -> _FakeProc:
        attempts.append(list(argv))
        flag = argv[-1]
        if flag in good:
            return _FakeProc(0, banner + "\n")
        return _FakeProc(1, REJECT.format(flag=flag) + "\n")

    monkeypatch.setattr(checks.VERSION_PROBE, "run", fake_run)
    return attempts


@pytest.fixture
def binary(tmp_path: Path) -> Path:
    p = tmp_path / "cyanrip"
    p.write_text("#!/bin/sh\n")
    p.chmod(0o755)
    return p


# --- the probe ---------------------------------------------------------------


def test_a_fork_build_that_only_answers_the_long_flag_is_found(
    binary: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """THE REGRESSION. Before the fix this returned present=False, i.e. the app
    told the user cyanrip was missing while the fork sat on the ripping path."""
    _binary_answering(monkeypatch, {"--version"}, FORK_BANNER)
    result = check_cyanrip(binary)
    assert result.present is True
    assert result.version == (0, 9, 4)
    assert "platterpus-fork" in result.raw_output


def test_a_stock_build_that_only_answers_uppercase_V_still_works(
    binary: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The other half of the control. The fix must not trade one build for the
    other — 0.9.3.x is what is installed in the field today."""
    _binary_answering(monkeypatch, {"-V"}, STOCK_BANNER)
    result = check_cyanrip(binary)
    assert result.present is True
    assert result.version == (0, 9, 3)


def test_the_known_safe_flag_is_tried_first(
    binary: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Order is a safety property, not a style choice.

    ``-V`` is the flag whose behaviour we have *measured* on both builds. What an
    unrecognised ``-v`` did on every historical cyanrip is not something we know,
    and "probably nothing" is not a basis for handing an argument to a program
    that spins a drive. So the unknown flag is only ever reached after the known
    one has declined.
    """
    attempts = _binary_answering(monkeypatch, {"-V", "--version"}, STOCK_BANNER)
    check_cyanrip(binary)
    assert len(attempts) == 1, "a working -V must not be followed by another probe"
    assert attempts[0][-1] == "-V"
    assert VERSION_FLAGS[0] == "-V"


def test_a_binary_answering_nothing_is_reported_absent_once(
    binary: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Every flag failing IS an absence — but it must be logged once, at the
    point where it is actually known.

    The per-attempt warning ("treating the tool as unavailable") would otherwise
    fire for the *expected* ``-V`` failure on every fork install, putting a line
    in every user's log file that is both alarming and untrue.
    """
    attempts = _binary_answering(monkeypatch, set(), "")
    with caplog.at_level(logging.DEBUG):
        result = check_cyanrip(binary)

    assert result.present is False
    assert [a[-1] for a in attempts] == list(VERSION_FLAGS)
    conclusions = [
        r for r in caplog.records if "treating cyanrip as unavailable" in r.message
    ]
    assert len(conclusions) == 1, "the absence conclusion must be logged exactly once"
    assert conclusions[0].levelno == logging.WARNING
    # ...and the evidence is still kept, at debug level, for a bug report.
    assert any(r.levelno == logging.DEBUG for r in caplog.records)


def test_the_expected_first_failure_is_not_logged_as_a_conclusion(
    binary: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """A fork install must produce NO warning at all — it is a success."""
    _binary_answering(monkeypatch, {"--version"}, FORK_BANNER)
    with caplog.at_level(logging.DEBUG):
        assert check_cyanrip(binary).present is True
    warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert warnings == [], (
        f"a successful fork probe warned: {[r.message for r in warnings]}"
    )


# --- the wizard's own probe --------------------------------------------------


def test_the_wizard_fork_probe_accepts_a_long_flag_only_binary(
    tmp_path: Path,
) -> None:
    """``fork_installed()`` asks the exported binary what it is. With ``-V``
    alone it reported a correctly-installed fork as not-done, so the wizard would
    rebuild and re-export the fork on every single run, forever."""
    from platterpus.deps import fork_source
    from platterpus.deps.host_setup import HostSetup

    cyanrip = tmp_path / "cyanrip"
    calls: list[list[str]] = []

    class _Runner:
        def which(self, name: str) -> bool:
            return False

        def exists(self, path: Path) -> bool:
            return path == cyanrip

        def run(self, argv: list[str]) -> tuple[int, str]:
            calls.append(list(argv))
            if argv[-1] == "--version":
                return 0, f"{fork_source.WIZARD_TARGET.banner}\n"
            return 1, REJECT.format(flag=argv[-1])

    setup = HostSetup(runner=_Runner(), cyanrip_path=cyanrip)
    assert setup.fork_installed() is True
    assert [c[-1] for c in calls] == list(VERSION_FLAGS)


# --- the adapter -------------------------------------------------------------


def test_the_backend_version_tries_both_and_raises_the_last_error() -> None:
    """``version()`` must still RAISE when nothing answers — that raise is what
    stops ``--doctor`` reporting a broken container as "the version". But the
    error it reports has to be the last flag's, not the first: on a 0.9.4 build
    the first failure is expected and says nothing useful."""
    from platterpus.adapters.cyanrip_backend import CyanripImpl
    from platterpus.adapters.rip_backend import RipError

    impl = CyanripImpl("cyanrip")
    seen: list[str] = []

    def fake_run(args: list[str], *a: object, **kw: object) -> str:
        seen.append(args[0])
        raise RipError(f"cyanrip failed: {args[0]}")

    impl._run = fake_run  # type: ignore[method-assign]
    with pytest.raises(RipError) as excinfo:
        impl.version()
    assert seen == list(VERSION_FLAGS)
    assert VERSION_FLAGS[-1] in str(excinfo.value)


def test_the_backend_version_returns_on_the_first_flag_that_answers() -> None:
    from platterpus.adapters.cyanrip_backend import CyanripImpl
    from platterpus.adapters.rip_backend import RipError

    impl = CyanripImpl("cyanrip")
    seen: list[str] = []

    def fake_run(args: list[str], *a: object, **kw: object) -> str:
        seen.append(args[0])
        if args[0] == "--version":
            return FORK_BANNER + "\n"
        raise RipError("nope")

    impl._run = fake_run  # type: ignore[method-assign]
    assert impl.version() == FORK_BANNER
    assert seen == ["-V", "--version"]


# --- the shell snippet the wizard runs inside the container ------------------


@pytest.mark.parametrize(
    ("label", "good_flag", "banner", "expected_exit"),
    [
        ("stock: right flag, wrong build", "-V", STOCK_BANNER, 1),
        ("fork at the wizard target", "--version", WIZARD_BANNER, 0),
        # The production pin, when the wizard is building a test pin, is the
        # RIGHT fork and the WRONG build — and must fail. Before ForkTarget the
        # verify read a different constant from the build, so this case could
        # not be expressed at all: there was only ever one "correct" banner.
        (
            "fork, but not the build being installed",
            "--version",
            _FORK_SOURCE.PRODUCTION_TARGET.banner,
            0 if _FORK_SOURCE.WIZARD_TARGET == _FORK_SOURCE.PRODUCTION_TARGET else 1,
        ),
        (
            "fork at a different pin",
            "--version",
            "cyanrip 0.9.4-rc1 (platterpus-fork-gdeadbee)",
            1,
        ),
        ("answers no version flag at all", "--nope", "never printed", 1),
    ],
)
def test_the_wizard_verify_snippet_behaves_on_every_build_shape(
    tmp_path: Path, label: str, good_flag: str, banner: str, expected_exit: int
) -> None:
    """Run the REAL generated shell against fake binaries.

    The snippet cannot import Python — it runs through ``sh -c`` inside the
    container — so it is a second, independent expression of the same rule, and
    exactly the kind of duplicate that can silently disagree. Executing it is the
    only way to know it does not.
    """
    from platterpus.deps import fork_source

    argv = fork_source.verify_command("ripping")
    script = argv[argv.index("-c") + 1]

    fake = tmp_path / "cyanrip"
    fake.write_text(
        "#!/bin/sh\n"
        f'if [ "$1" = "{good_flag}" ]; then echo "{banner}"; exit 0; fi\n'
        'echo "Unable to parse command line argument: $1" >&2\n'
        "exit 1\n"
    )
    fake.chmod(0o755)

    proc = subprocess.run(
        ["sh", "-c", script, "verify", str(fake), fork_source.WIZARD_TARGET.build_tag],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == expected_exit, (
        f"{label}: exit {proc.returncode}, stdout={proc.stdout!r} stderr={proc.stderr!r}"
    )


def test_the_snippet_keys_on_exit_status_not_on_output_being_present() -> None:
    """A rejected flag still PRINTS. A snippet that accepted the first non-empty
    output would accept "Unable to parse command line argument: -V" as a version
    banner — so the discriminator has to be the exit status."""
    assert "if out=" in VERSION_BANNER_SNIPPET
    assert "-z" in VERSION_BANNER_SNIPPET  # the empty check is only the fallback
    # And it surfaces the tool's own words on total failure rather than only ours.
    assert "2>&1" in VERSION_BANNER_SNIPPET


def test_the_snippet_is_generated_from_the_same_tuple_as_the_python() -> None:
    """Two expressions of one rule are fine; two SOURCES of it are not."""
    for flag in VERSION_FLAGS:
        assert flag in VERSION_BANNER_SNIPPET


# --- the sweep: nobody hardcodes a version flag ------------------------------


def test_no_module_outside_cyanrip_cli_hardcodes_a_version_flag() -> None:
    """Enforce the rule across the codebase, not at the place it was learned.

    Four call sites each had their own ``-V`` and all four broke together. The
    lesson from ``docs/testing.md`` §5.o is that a rule fixed where it was found
    gets re-broken somewhere else, so this sweeps every module: the version flags
    live in ``cyanrip_cli`` and everyone else imports them.
    """
    src = Path(__file__).resolve().parents[1] / "src" / "platterpus"
    # `-V` specifically: it is cyanrip's historical version flag and no other
    # tool Platterpus probes uses it (flac, metaflac and cd-paranoia all take
    # `--version`, which is why that spelling is NOT swept — it would flag every
    # other probe and our own CLI, and a check that fires on correct code gets
    # deleted rather than obeyed).
    offenders: list[str] = []
    examined = 0
    for path in sorted(src.rglob("*.py")):
        if path.name == "cyanrip_cli.py":
            continue
        examined += 1
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            code = line.split("#", 1)[0]
            if '"-V"' in code or "'-V'" in code:
                offenders.append(f"{path.relative_to(src)}:{lineno}: {line.strip()}")
    assert examined > 50, f"floor: only swept {examined} modules — the glob is wrong"
    assert not offenders, (
        "cyanrip's version flag is hardcoded outside cyanrip_cli.py; import "
        "VERSION_FLAGS instead so a future rename is one edit:\n  "
        + "\n  ".join(offenders)
    )


@pytest.mark.parametrize(
    "module",
    [
        "deps/checks.py",
        "adapters/cyanrip_backend.py",
        "deps/host_setup.py",
        "deps/fork_source.py",
    ],
)
def test_every_module_that_asks_cyanrip_its_version_imports_the_flag_list(
    module: str,
) -> None:
    """The other half of the sweep, and the half that matters.

    Absence of ``-V`` could be satisfied by deleting the probe altogether — a
    check that can be satisfied by finding nothing needs a floor. These are the
    four call sites that broke together; each must be reading the shared tuple,
    not a literal and not nothing.
    """
    src = Path(__file__).resolve().parents[1] / "src" / "platterpus"
    text = (src / module).read_text(encoding="utf-8")
    assert "VERSION_FLAGS" in text or "VERSION_BANNER_SNIPPET" in text, (
        f"{module} asks cyanrip for its version but does not use the shared flag list"
    )


def test_the_flag_list_is_ordered_and_non_empty() -> None:
    """Callers index ``VERSION_FLAGS[-1]`` for the error to report, and rely on
    the first element being the field-proven one."""
    assert VERSION_FLAGS, "an empty flag list would make every probe report absent"
    assert VERSION_FLAGS[0] == "-V"
    assert "--version" in VERSION_FLAGS
    assert sys.version_info >= (3, 11)  # tuple ordering is load-bearing, not a set


# --- The -a / -t blob syntax (round 7 lap 31) ---------------------------------
#
# These live beside the version-flag tests because both pin `cyanrip_cli.py`: the
# facts about cyanrip's command line that more than one layer needs. The escape
# is written by `adapters/cyanrip_backend.py` and read back by `cue_validate.py`,
# and the whole point of one shared implementation is that those two cannot
# disagree — so the round trip is asserted here, once, rather than on each side.


def test_the_escape_and_its_inverse_round_trip_every_awkward_value() -> None:
    """escape → split → unescape must return exactly what went in.

    Not a tautology: the two functions live in different modules (the escaper in
    the backend, the splitter here) precisely so the write side and the read side
    share no code, and this is the assertion that keeps them inverses. The
    U+2236 case is deliberate — a historical argv from before the escape shipped
    must still read back correctly, because the report reader is pointed at
    committed artifacts from those rips.
    """
    from platterpus.adapters.cyanrip_backend import _escape_meta_value
    from platterpus.cyanrip_cli import split_meta_blob

    values = [
        "Every Breath You Take: The Classics",  # the reference disc
        "Every Breath You Take∶ The Classics",  # the retired workaround
        "a:b:c",
        "a=b",
        "back\\slash",
        "It's",
        "ends with a colon:",
        ":starts with one",
        "::",
        "\\",
        "plain",
        "Cause 4 Concern: Part 1=2",
    ]
    for value in values:
        blob = f"album={_escape_meta_value(value)}:album_artist=The Police"
        pairs = split_meta_blob(blob)
        assert pairs.get("album") == value, (
            f"{value!r} did not survive the round trip: got {pairs.get('album')!r} "
            f"from blob {blob!r}"
        )
        # The second pair must still be there — the failure mode is that an
        # unescaped separator swallows it, which a one-key assertion cannot see.
        assert pairs.get("album_artist") == "The Police", blob


def test_a_naive_split_loses_text_that_the_escape_aware_one_keeps() -> None:
    """The non-triviality floor for the test above.

    A round-trip test passes just as happily against a naive splitter *if* the
    escaper is also naive, so it cannot on its own show the escape-aware walk is
    doing anything. This pins the difference: on the real reference title, the
    naive split silently drops " The Classics" and leaves a stray backslash.
    That is what shipped for the length of one change, and it is what would have
    made the title-fidelity check accuse every correct rip of this disc.
    """
    from platterpus.cyanrip_cli import split_meta_blob

    blob = "album=Every Breath You Take\\: The Classics:album_artist=The Police"

    naive: dict[str, str] = {}
    for chunk in blob.split(":"):
        if "=" in chunk:
            key, _, value = chunk.partition("=")
            naive[key.strip().lower()] = re.sub(r"\\(.)", r"\1", value)

    assert naive["album"] == "Every Breath You Take\\"  # the text is gone
    assert split_meta_blob(blob)["album"] == "Every Breath You Take: The Classics"


def test_split_on_unescaped_keeps_the_backslash_it_split_around() -> None:
    """Structure, not text — the two questions must stay separate.

    A splitter that also unescaped would make it impossible to tell an escaped
    separator from a structural one on a second pass, which is exactly what the
    argv-shape guard needs to do.
    """
    from platterpus.cyanrip_cli import split_on_unescaped

    assert split_on_unescaped("a:b", ":") == ["a", "b"]
    assert split_on_unescaped("a\\:b", ":") == ["a\\:b"]
    assert split_on_unescaped("a\\\\:b", ":") == ["a\\\\", "b"]
    assert split_on_unescaped("", ":") == [""]
    assert split_on_unescaped("album=A\\:B\\:C:album_artist=X", ":") == [
        "album=A\\:B\\:C",
        "album_artist=X",
    ]
