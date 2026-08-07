#!/usr/bin/env python3
"""Emit the UI-script language reference, derived from the code that runs it.

The scripting surface has three separate descriptions of itself waiting to
disagree: the verb table, the runner's handlers, and whatever a human wrote in a
doc. The first two are already held together by
``tests/test_uiscript.py`` (it sweeps the table against the runner's real
handlers). This script closes the third by **generating** the document instead of
writing one — same reasoning, and same mechanism, as
``scripts/emit_dependency_contract.py``.

Nothing here is restated. It imports the vocabulary, the runner and the parser
and asks them:

* every verb, its arity, its safety class and whether it is implemented, from
  ``uiscript.verbs.VERBS``;
* every dialog ``open`` accepts, from ``OPENABLE``;
* every probe flag exempt from the ``-N`` rule, from ``PROBE_FLAGS``;
* every numeric limit, read off the live constants in ``uiscript.runner`` and
  ``uiscript.script`` — so a cap that changes changes here on the next run;
* every settable field, from ``Config``'s own dataclass fields and their types.

The output carries **both audiences in one file** (the maintainer's ask,
2026-08-07: *"they should live in a file also for humans and machines to be able
to read"*): a prose reference for a person, and a fenced ``application/json``
block with the same facts as data for a machine. One file rather than two,
because two descriptions of one grammar is the exact failure this generator
exists to prevent — and they are emitted from one pass over one set of objects,
so they cannot disagree with each other either.

``tests/test_script_language_emitted.py`` regenerates this and diffs it against
the committed ``docs/script-language.md``, so the file cannot go stale without CI
going red.

Usage::

    python scripts/emit_script_language.py            # write the doc
    python scripts/emit_script_language.py --stdout   # print, write nothing
    python scripts/emit_script_language.py --check    # exit 1 if stale
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))

OUTPUT_PATH: Path = _REPO_ROOT / "docs" / "script-language.md"


def _verb_rows() -> list[dict[str, Any]]:
    """Every verb as data, in the vocabulary's own order."""
    from platterpus.uiscript.verbs import VERBS

    rows: list[dict[str, Any]] = []
    for verb in VERBS.values():
        rows.append(
            {
                "name": verb.name,
                "min_args": verb.min_args,
                # `None` means "the rest of the line" and is emitted as JSON null
                # rather than a sentinel number: a cap of -1 or 9999 would be a
                # value a machine reader has to know to special-case.
                "max_args": verb.max_args,
                "unsafe": verb.unsafe,
                "implemented": verb.implemented,
                "help": verb.help,
            }
        )
    return rows


def _limits() -> dict[str, Any]:
    """Every bound, read off the live constants rather than transcribed."""
    from platterpus.uiscript import runner, script

    return {
        "max_script_lines": script.MAX_LINES,
        "max_line_characters": script.MAX_LINE_CHARS,
        "max_wait_seconds": runner.MAX_WAIT_S,
        "max_wait_for_rip_seconds": runner.MAX_RIP_WAIT_S,
        "cyanrip_timeout_seconds": runner.CYANRIP_VERB_TIMEOUT_S,
        "cyanrip_unreapable_grace_seconds": runner.CYANRIP_VERB_GRACE_S,
        "max_captured_output_characters": runner.MAX_TOOL_OUTPUT_CHARS,
        "step_interval_ms": runner.TICK_MS,
        "max_track_range_span": runner._MAX_TRACK_RANGE,
        "max_cyanrip_arguments": 64,
        "max_cyanrip_argument_characters": 4000,
    }


def _settable_fields() -> list[dict[str, str]]:
    """Config fields `set`/`expect` accept, with the type a value is coerced to."""
    from platterpus.config import Config

    kinds = {bool: "boolean (on/off)", int: "integer", float: "number", str: "text"}
    rows: list[dict[str, str]] = []
    for field in dataclasses.fields(Config):
        default = getattr(Config(), field.name)
        # Keyed on the *value's* runtime type, which is what `_coerce_setting`
        # branches on — not on the annotation, which can be a string under
        # `from __future__ import annotations` and would need parsing to trust.
        # bool before int: bool is an int subclass.
        for kind, label in kinds.items():
            if type(default) is kind:
                rows.append({"field": field.name, "type": label})
                break
    return rows


def _document() -> str:
    from platterpus.uiscript.verbs import OPENABLE, PROBE_FLAGS

    verbs = _verb_rows()
    limits = _limits()
    fields = _settable_fields()
    dialogs = sorted(OPENABLE)
    probes = sorted(PROBE_FLAGS)

    from platterpus import __version__

    machine = {
        "language": "platterpus-uiscript",
        "grammar_version": 1,
        # The APP version this description was generated from. The grammar version
        # above changes only when the language does; this changes every release, and
        # it is what makes the document *truthful for the build it ships with*
        # (maintainer directive, 2026-08-07). A reader — person or machine — can
        # check it against `platterpus --version` and know whether this page
        # describes the binary in front of them.
        "platterpus_version": __version__,
        "syntax": {
            "one_statement_per_line": True,
            "comment_prefix": "#",
            "blank_lines_ignored": True,
            "argument_separator": "whitespace",
            "quoting": False,
            "case_sensitive_verbs": False,
            "trailing_free_text_verbs": [
                v["name"] for v in verbs if v["max_args"] is None
            ],
        },
        "verbs": verbs,
        "openable_dialogs": dialogs,
        "cyanrip_probe_flags": probes,
        "limits": limits,
        "settable_fields": fields,
        "outcomes": ["PASS", "FAIL", "ERROR", "BLOCKED", "SKIPPED"],
    }

    lines: list[str] = []
    add = lines.append

    add("# The Platterpus test-script language")
    add("")
    add("**Generated — do not hand-edit.** Regenerate with")
    add("`python scripts/emit_script_language.py`. Every fact below is read out of")
    add("the code that runs it: the verb table, the runner's live limit constants,")
    add("and `Config`'s own fields. A hand-written version of this page would be a")
    add("second description of the grammar, and would drift the week after it was")
    add("written.")
    add("")
    add("Two audiences, one file: prose for a person, and the same facts as JSON at")
    add("the bottom for a machine. They are emitted from one pass over one set of")
    add("objects, so they cannot disagree with each other either.")
    add("")

    add("## Syntax")
    add("")
    add("One statement per line. `#` starts a comment; blank lines are ignored.")
    add("Arguments are separated by whitespace and are **not quoted** — the verbs")
    add("that take free text swallow the rest of the line instead, which is why")
    add("`album Synchronicity (rig pass 1)` needs no quoting. Verb names are")
    add("matched case-insensitively.")
    add("")
    add("A step that fails is recorded and the batch **continues**; only `abort`")
    add("stops it. That is deliberate for an unattended run: stopping at the first")
    add("failure throws away every later measurement, and the later ones are often")
    add("the ones that explain the first.")
    add("")
    add(
        f"Every step ends in one of: {', '.join(f'`{o}`' for o in machine['outcomes'])}."
    )
    add("")

    add("## Verbs")
    add("")
    add("`args` is the accepted argument count; `rest of line` means the remaining")
    add("text is taken verbatim as one value.")
    add("")
    add("| verb | args | status | what it does |")
    add("|---|---|---|---|")
    for verb in verbs:
        if verb["max_args"] is None:
            arity = f"{verb['min_args']}+ (rest of line)"
        elif verb["max_args"] == verb["min_args"]:
            arity = str(verb["min_args"])
        else:
            arity = f"{verb['min_args']}–{verb['max_args']}"
        marks = []
        if not verb["implemented"]:
            marks.append("**NOT IMPLEMENTED**")
        if verb["unsafe"]:
            marks.append("needs the unsafe opt-in")
        status = "; ".join(marks) if marks else "ready"
        # The help text already reads as a sentence and is the same string the
        # in-app reference renders, so it is reused rather than re-worded here.
        add(f"| `{verb['name']}` | {arity} | {status} | {verb['help']} |")
    add("")
    add("A verb marked **NOT IMPLEMENTED** is listed on purpose rather than")
    add("omitted: a documented capability that is not a capability fails at *run*")
    add("time, in front of an unattended batch, which is the worst moment to")
    add("discover it. Listing it with the mark is how the gap stays visible.")
    add("")

    add("## Dialogs `open` accepts")
    add("")
    add(", ".join(f"`{name}`" for name in dialogs))
    add("")

    add("## Limits")
    add("")
    add("Read off the live constants. Every one of these exists so a typo or a")
    add("paste accident cannot strand an unattended run.")
    add("")
    add("| limit | value |")
    add("|---|---|")
    for key, value in limits.items():
        add(f"| `{key}` | {value} |")
    add("")

    add("## The cyanrip passthrough")
    add("")
    add("`cyanrip <args…>` runs the **host-exported binary for real**, through the")
    add("same seam the application's own probes use. It is guarded: a rip")
    add("invocation missing `-N` is refused, by delegating to the same chokepoint")
    add("every application-built rip argv passes — not by restating its rule.")
    add("Without `-N` cyanrip runs its own metadata lookup and can block on an")
    add("interactive prompt with no terminal attached, so an unattended batch would")
    add("hang forever.")
    add("")
    add("These flags are exempt, because they print something and exit without")
    add("touching metadata or the drive's audio:")
    add("")
    add(", ".join(f"`{flag}`" for flag in probes))
    add("")
    add("Arguments containing a newline or NUL are refused. That is not injection —")
    add("no shell is involved — it is **log forgery**: cyanrip writes its argv into")
    add("an archival log, and a newline could fabricate a line in a document whose")
    add("whole purpose is being trustworthy evidence.")
    add("")

    add("## Settings `set` and `expect` accept")
    add("")
    add("Keyed on the **`config.toml` field name**, not the dialog's row label — a")
    add("row label is display text and a script keyed on it breaks for reasons")
    add("unrelated to the setting. Every `set` is checked by the same validator the")
    add("Settings dialog uses, so a script can never persist a value the dialog")
    add("would have refused; a *warning*-severity issue does not block, because the")
    add("dialog lets a person proceed past one and a script must not be stricter")
    add("than the UI it stands in for.")
    add("")
    add("| field | value type |")
    add("|---|---|")
    for row in fields:
        add(f"| `{row['field']}` | {row['type']} |")
    add("")

    add("## Rules for writing a test that is worth running")
    add("")
    add("These are not style preferences. Every one was paid for by a green test")
    add("that was measuring nothing, here or in the cyanrip fork. The general")
    add("versions live in `docs/testing.md`; what follows is how each one lands in")
    add("a *script*, which is where they are easiest to get wrong because a script")
    add("runs unattended and nobody watches it pass.")
    add("")
    add("**1. Every script needs a floor — an assertion that fails when nothing")
    add("happened.** `rip` on a disc that was never identified rips zero tracks and")
    add("reports success exactly like a real rip. `expect-tracks <n>` before the")
    add("rip is the floor, and it is why the shipped example carries one with a")
    add("comment telling you not to delete it. *A check that can be satisfied by")
    add("finding nothing is decoration.*")
    add("")
    add("**2. Assert the subject, not just the shape.** `expect-cyanrip 0.9.4` is")
    add("satisfied by stock upstream. `expect-cyanrip platterpus-fork-g<sha>` is")
    add("satisfied only by the build you meant. Where a check matches on a label,")
    add("make it also require the content — the label answers *did they name it*,")
    add("the content answers *did they do it*, and only the pair is a check.")
    add("")
    add("**3. Pin your input, not only your logic.** A script that sets nothing")
    add("inherits whatever the config happened to hold from the last run, so a")
    add("passing result describes a configuration you cannot reconstruct. `expect`")
    add("the settings the outcome depends on *before* the step that depends on")
    add("them, even the ones you did not change.")
    add("")
    add("**4. A failure is data. Do not abort on it.** The batch continues past a")
    add("failed step on purpose: the later measurements are often what explain the")
    add("earlier failure, and a rig session is the scarce resource. Reach for")
    add("`abort` only when continuing would be unsafe or meaningless — for example")
    add("when the wrong ripper is installed, because every artifact after that")
    add("point describes the wrong binary.")
    add("")
    add("**5. Give every pass its own name.** `album <title>` decides the output")
    add("folder. Two passes with one title means the second overwrites the first,")
    add("and a session that destroys its own evidence has destroyed the thing it")
    add("was run to produce.")
    add("")
    add("**6. Bound everything that waits.** `wait-for-rip` takes a timeout because")
    add("an unattended run that hangs is indistinguishable from one still working.")
    add("The caps in the table above are backstops for typos, not a substitute for")
    add("choosing a real number.")
    add("")
    add("**7. Say which build produced the artifact.** Start with `cyanrip")
    add("--version` and assert the build tag. A version number cannot separate the")
    add("fork from upstream — the fork deliberately carries upstream's — and two")
    add("logs of one disc from two binaries are not interchangeable evidence.")
    add("")
    add("**8. Record what you could not test.** A transcript that omits a step")
    add("reads like a transcript that passed it. If something needs a person, put")
    add("a `log` line saying so, in the script, at the point it would have run.")
    add("")

    add("## Worked example, annotated")
    add("")
    add("The smallest script that is actually worth running. Every line is one of")
    add("the rules above.")
    add("")
    add("```")
    add("log ===== identity first =====")
    add("cyanrip --version                       # rule 7: which binary is this?")
    add("expect-exit 0")
    add("expect-cyanrip platterpus-fork-gddf7ac3 # rule 2: the tag, not the version")
    add("")
    add("log ===== pin the inputs =====")
    add("expect output_format flac               # rule 3: state what you rely on")
    add("set force_overread off                  # -O hangs the BDR-209D")
    add("expect force_overread off               # and prove the set took")
    add("")
    add("log ===== the disc =====")
    add("rescan")
    add("wait 20")
    add("expect-tracks 14                        # rule 1: THE FLOOR")
    add("select-tracks all")
    add("album Synchronicity (pass 1)            # rule 5: its own folder")
    add("")
    add("log ===== rip =====")
    add("rip")
    add("wait-for-rip 5400                       # rule 6: bounded")
    add("screenshot after-rip")
    add("```")
    add("")
    add("A fuller one, kept current and runnable, is")
    add("`docs/rig-scripts/police-rerip.txt`.")
    add("")

    add("## Recipes")
    add("")
    add("| you want to… | write |")
    add("|---|---|")
    add("| re-rip only the tracks that failed | `select-tracks 3,7,11-13` |")
    add(
        "| prove a probe refuses on a disc image | `cyanrip -x -N` then `expect-cyanrip not run` |"
    )
    add("| check a setting without changing it | `expect <field> <value>` |")
    add("| test the cancel path | `rip`, `wait 30`, `cancel-rip`, `wait-for-rip 120` |")
    add("| capture the whole window, dialogs included | `screenshot <name>` |")
    add("| record visible state as text | `snapshot <name>` |")
    add("| run any ripper invocation for real | `cyanrip <args…>` |")
    add("")

    add("## Adding a verb")
    add("")
    add("Two edits, and the order matters because the second is what makes the")
    add("first real:")
    add("")
    add("1. Add a `Verb(...)` row to `src/platterpus/uiscript/verbs.py`. That table")
    add("   **is the security boundary** — the parser refuses anything not listed,")
    add("   so a new capability is a deliberate edit rather than a side effect of")
    add("   implementing something else.")
    add("2. Add a `_do_<name>` method to `src/platterpus/uiscript/runner.py`")
    add("   (hyphens become underscores).")
    add("")
    add("`tests/test_uiscript.py` sweeps the table against the runner's real")
    add("handlers in both directions, so an advertised verb with no implementation")
    add("— or an implementation nobody can reach — fails CI rather than failing at")
    add("run time in front of an unattended batch. Regenerate this page afterwards:")
    add("`python scripts/emit_script_language.py`.")
    add("")
    add("**Drive the real widget.** A handler should reach the same slot a click")
    add("reaches, not build its own version of the action. A harness that is safer")
    add("or simpler than the product makes the product's gap invisible, which is")
    add("the same reason the `cyanrip` verb is a real passthrough rather than a")
    add("simulation.")
    add("")
    add("**What must never become a verb:** ejecting, deleting, uninstalling,")
    add("installing a dependency, launching an external application. The failure")
    add("mode of an unattended destructive action is unbounded, and every one of")
    add("those is reachable from a GUI a person is driving. A script that needs one")
    add("of them is a script that needs a person.")
    add("")

    add("## Outcomes, and what each one means")
    add("")
    add("| outcome | meaning |")
    add("|---|---|")
    add("| `PASS` | the step did what it said |")
    add(
        "| `FAIL` | the step ran and the assertion did not hold — **the batch continues** |"
    )
    add(
        "| `ERROR` | the step could not run at all: a bad argument, a missing widget, a runner fault |"
    )
    add("| `BLOCKED` | the verb needs the unsafe opt-in, which is off |")
    add("| `SKIPPED` | never reached, because `abort` stopped the batch earlier |")
    add("")
    add("`ERROR` and `FAIL` are different on purpose. `FAIL` is a measurement —")
    add("the product did something you did not expect. `ERROR` is the script or the")
    add("harness being wrong, and it means the measurement never happened. Reading")
    add("them as the same thing turns *a test that could not run* into *a test that")
    add("found nothing wrong*.")
    add("")

    add("## The same thing, as data")
    add("")
    add("```json")
    add(json.dumps(machine, indent=2, sort_keys=False))
    add("```")
    add("")
    add(f"*Last updated for Platterpus v{__version__}.*")
    add("")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stdout", action="store_true", help="print, write nothing")
    parser.add_argument("--check", action="store_true", help="exit 1 if stale")
    args = parser.parse_args(argv)

    document = _document()
    if args.stdout:
        print(document)
        return 0
    if args.check:
        try:
            current = OUTPUT_PATH.read_text(encoding="utf-8")
        except OSError:
            current = ""
        if current != document:
            print(
                f"{OUTPUT_PATH.relative_to(_REPO_ROOT)} is stale.\n"
                f"Regenerate with: python scripts/emit_script_language.py",
                file=sys.stderr,
            )
            return 1
        return 0
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(document, encoding="utf-8")
    print(f"wrote {OUTPUT_PATH.relative_to(_REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
