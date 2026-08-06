# SPDX-License-Identifier: GPL-3.0-only
"""The rig-session harness must be reachable from a *built* Platterpus.

**The bug this is written against is not in the script — it is in where it
lived.** `rig_session.sh` sat in `scripts/`, which ships in the git repository
and in nothing else. The person who runs it has an AppImage in
`~/Applications/`, and the rig sheet's instruction was, verbatim,
``bash ~/path/to/Platterpus/scripts/rig_session.sh ~/rig-b11`` — a placeholder
path in a copy-pasteable command block. The harness had a smoke test, correct
content and no route to the machine it was written for, which is the same shape
as the scripting subsystem that shipped with no menu item: *a documented
capability is not a capability* (`docs/testing.md` §5.p).

So these tests assert **reachability**, not behaviour (the behaviour tests are in
`test_rig_session_script.py`): the file is inside the package, the accessor finds
it, and the packaging metadata will actually carry it into a wheel. The last one
matters most — the file being on disk in a checkout proves nothing about what
`pip install` produces, and that is exactly the gap that shipped.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent


def test_the_accessor_points_at_a_real_executable_script() -> None:
    from platterpus.app import rig_session_script

    script = rig_session_script()
    assert script.is_file(), f"the harness is not where the accessor says: {script}"
    # A floor, so the assertion cannot be satisfied by an empty placeholder.
    text = script.read_text(encoding="utf-8")
    assert len(text) > 2000, "the harness is implausibly short"
    assert text.startswith("#!"), "the harness lost its shebang"


def test_the_accessor_resolves_inside_the_installed_package() -> None:
    """Not `scripts/` — that directory does not exist in a wheel or an AppImage."""
    import platterpus
    from platterpus.app import rig_session_script

    package_dir = Path(platterpus.__file__).resolve().parent
    assert rig_session_script().parent == package_dir


def test_packaging_declares_the_harness_as_package_data() -> None:
    """The check that would have caught the original placement.

    Read out of `pyproject.toml` rather than asserted about the filesystem: a
    file present in a checkout and absent from the wheel is precisely the failure
    mode, and only the packaging metadata can distinguish them.
    """
    data = tomllib.loads((_REPO / "pyproject.toml").read_text(encoding="utf-8"))
    patterns = data["tool"]["setuptools"]["package-data"]["platterpus"]
    assert "rig_session.sh" in patterns, (
        "rig_session.sh is not declared as package data, so a wheel/AppImage "
        "build will silently omit it and --rig-session will report the harness "
        "missing on the one machine that needs it"
    )


def test_the_two_unattended_flags_are_in_the_apps_own_help(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Both new routes must be discoverable from `--help`.

    Driven through `main` rather than a re-declared parser: the thing under test
    is the parser the *app* builds, and a test that constructs its own would pass
    against an app that never registered the flag.
    """
    from platterpus.app import main

    with pytest.raises(SystemExit) as exit_info:
        main(["--help"])
    assert exit_info.value.code == 0
    help_text = capsys.readouterr().out
    # A floor first: if help capture broke, every substring check below would
    # fail for the wrong reason, and an empty string would pass a `not in`.
    assert len(help_text) > 500, "argparse help was not captured"
    assert "--rig-session" in help_text
    assert "--run-script" in help_text
