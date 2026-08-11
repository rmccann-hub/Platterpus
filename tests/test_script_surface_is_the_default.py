"""The script language is the default place a testing capability goes.

Maintainer directive, 2026-08-11: *"the entire point of adding the ability to run
scripts is for this. you dont need to build special arguements unless absolutely
needed (which shouldnt be beyond special situations where this is no command or
ability to do so)."*

`CLAUDE.md` carries the rule; this file is the check, because a rule with no
check is the shape this project has an explicit warning about — *a comment where
a check belongs is not a fix*. The mechanism is a **ratchet**: every command-line
flag is listed below with the reason a script verb could not serve it. The list
may shrink; it may not grow without someone writing that reason down, in a place
a reviewer reads.

The failure this prevents is not a broken build. It is drift: two ways to reach
the same capability, added one convenient flag at a time, until the language the
tests are written in reaches less of the product than the command line does.
"""

from __future__ import annotations

import contextlib
import io
import re

import pytest

#: Every flag the CLI publishes, and why it is a flag rather than a script verb.
#:
#: Three reasons are legitimate and they are named, not implied:
#:   "pre-GUI"  — it runs before QApplication exists, so there is no window for a
#:                script to drive. A verb here is not merely unnecessary, it is
#:                impossible.
#:   "external" — a caller in ANOTHER repository invokes it. A script verb is
#:                unreachable from a different project's shell script, and the
#:                cyanrip seam only composes into one upload if their script can
#:                call ours.
#:   "entry"    — it is how a script run is STARTED. A verb cannot start the
#:                runner that executes verbs.
#:
#: Anything else needs a fourth reason written here and in the commit message.
JUSTIFIED_FLAGS: dict[str, str] = {
    "--help": "pre-GUI: argparse's own",
    "--version": "pre-GUI: must answer without starting Qt",
    "--doctor": "pre-GUI: the no-GUI environment check; it runs when the GUI cannot",
    "--install-ripper": "pre-GUI: installs the ripper the GUI depends on",
    "--uninstall": "pre-GUI: removes the app, so it cannot rely on the app running",
    "--run-script": "entry: this is how a script run is started",
    "--rig-session": "entry: starts the unattended harness, which drives the rest",
    "--audit-rips": "pre-GUI: read-only audit of finished rips, no disc and no window",
    "--ctdb-calibrate": "pre-GUI: CTDB sweep over a finished folder, no disc",
    "--compare": "pre-GUI: diffs two finished rips; no window is involved",
    "--assemble-best-of": "pre-GUI: builds a folder from finished rips; no window",
    "--rig-check": (
        "external: the cyanrip fork's own script calls this so both projects "
        "append to one MANIFEST.txt. It ALSO has a `rig-check` script verb — two "
        "thin callers of one function, never two implementations."
    ),
    "--rig-check-album": "external: argument of --rig-check, same interface",
    "--rig-check-device": "external: argument of --rig-check, same interface",
}


def _published_flags() -> set[str]:
    """Every long flag in ``--help``. Read off the real parser, not a list."""
    from platterpus.app import main

    buffer = io.StringIO()
    with pytest.raises(SystemExit), contextlib.redirect_stdout(buffer):
        main(["--help"])
    text = buffer.getvalue()
    assert len(text) > 200, "the help text is empty; this check would pass vacuously"
    return set(re.findall(r"(?<![\w-])--[a-z][a-z0-9-]*", text))


def test_every_cli_flag_has_a_written_reason_for_not_being_a_verb() -> None:
    """The ratchet. A new flag fails here until its reason is written down."""
    unjustified = sorted(_published_flags() - set(JUSTIFIED_FLAGS))
    assert not unjustified, (
        "these command-line flags have no recorded reason for existing instead of "
        f"a script verb: {unjustified}. The default is a verb in "
        "`uiscript/verbs.py` plus a `_do_<verb>` handler. If a flag is genuinely "
        "required (pre-GUI, an external caller, or the entry point that starts a "
        "script run), add it to JUSTIFIED_FLAGS with that reason — and say so in "
        "the commit message. See CLAUDE.md, Code conventions."
    )


def test_the_allowlist_does_not_outlive_its_flags() -> None:
    """The converse, so the list cannot rot into a record of flags long gone.

    Without this the ratchet only ever grows stale: a removed flag would leave an
    entry that looks like a live justification, and the next reader would take it
    as precedent for a flag that no longer exists.
    """
    published = _published_flags()
    stale = sorted(flag for flag in JUSTIFIED_FLAGS if flag not in published)
    assert not stale, f"JUSTIFIED_FLAGS names flags the CLI no longer has: {stale}"


def test_every_reason_names_one_of_the_permitted_categories() -> None:
    """A reason must be one of the three, not free-form prose that reads like one.

    This is the *"can it be satisfied by the wrong thing"* question asked of this
    very check: without it, "because it was easier" would sit in the dict as a
    written reason and pass, which is worse than no check — a failure gets
    investigated and a pass gets cited.
    """
    permitted = ("pre-GUI", "external", "entry")
    for flag, reason in JUSTIFIED_FLAGS.items():
        assert reason.startswith(permitted), (
            f"{flag}'s reason does not begin with one of {permitted}: {reason!r}. "
            "A fourth category needs adding here deliberately, not by prose."
        )


def test_the_seam_check_really_is_reachable_from_the_script_language() -> None:
    """`--rig-check` is allowed to exist *because* it is not the only way in.

    If the verb ever disappeared, the flag's justification in the list above would
    quietly become false while still reading as true — the exact decay this file
    exists to stop. Pin the pair together.
    """
    from platterpus.uiscript.runner import ScriptRunner
    from platterpus.uiscript.verbs import VERBS

    assert "rig-check" in VERBS, (
        "--rig-check is justified in JUSTIFIED_FLAGS on the grounds that a script "
        "verb also reaches it. The verb is gone, so that justification is now false."
    )
    assert VERBS["rig-check"].implemented
    assert hasattr(ScriptRunner, "_do_rig_check")
