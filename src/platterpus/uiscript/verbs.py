"""The closed vocabulary: one entry per verb, and nothing outside it runs.

**This table is the security boundary**, not a convenience index. The parser
rejects anything not listed here, so adding a capability to the scripting surface
is a deliberate edit to this file rather than a side effect of implementing
something else. That is the whole reason the vocabulary is data rather than a
scatter of ``if verb == ...`` branches in the runner.

**What is deliberately absent, and why.** No verb ejects the disc, deletes a
file, runs the uninstaller, installs a dependency, or launches an external
application. Those are all reachable from the GUI a human is driving; none of
them belongs in a batch that runs while nobody is watching, because the failure
mode of an unattended destructive action is unbounded. A script that needs one of
those is a script that needs a person.

**cyanrip is passed through for real, not simulated.** The maintainer's
instruction: *"it needs to be an independent test, but have full access to every
surface exposed by the application and also cyanrip. the passthrough should be
real, or at least have logic."* So ``cyanrip <args…>`` invokes the
**host-exported binary** through :func:`platterpus.adapters.rip_backend.
run_capture` — the same seam the application's own probes use, so the test
exercises the real path rather than a parallel one that could drift from it. It
inherits that seam's killable child, its bounded timeout and its
diagnostics-on-failure for free, which is also why it is not reimplemented here.

**The escape hatch.** The maintainer asked for one explicitly, so ``eval`` and
``call`` exist — and they are marked :attr:`Verb.unsafe`, which means they are
refused unless the user has separately opted in (a second Settings toggle, off by
default, distinct from the one that shows the console at all). A run that used an
unsafe verb says so at the top of its own transcript, because a report that reads
like an ordinary pass but was produced by arbitrary code is a claim we cannot
support.
"""

from __future__ import annotations

from dataclasses import dataclass

from platterpus.cyanrip_cli import VERIFY_LOG_FLAG, VERSION_FLAGS


@dataclass(frozen=True)
class Verb:
    """One command in the vocabulary.

    - ``name``: the word as typed, always lower-case.
    - ``min_args`` / ``max_args``: arity, checked by the parser so an arity
      mistake is reported against its own line rather than blowing up mid-run.
      ``max_args`` of ``None`` means "the rest of the line", used by the verbs
      whose tail is free text (``log``, ``eval``).
    - ``unsafe``: needs the separate escape-hatch opt-in.
    - ``help``: one line, shown in the console's built-in reference. Kept here so
      the reference cannot drift from the implementation — the console renders
      this table rather than a second hand-written list.
    """

    name: str
    min_args: int
    max_args: int | None
    help: str
    unsafe: bool = False
    #: True when this verb's arguments can be filesystem paths, so a leading
    #: ``~/`` is expanded at parse time. Declared per verb rather than applied to
    #: every token because the free-text verbs (``log``, ``expect-cyanrip``) carry
    #: *messages and match patterns*, and silently rewriting one of those would
    #: turn an assertion into a different assertion. See
    #: :func:`platterpus.uiscript.script.expand_home` for why the expansion has to
    #: happen at all.
    takes_paths: bool = False
    #: False while the runner has no handler for this verb yet. The table is what
    #: the console's reference renders, so an advertised verb with no
    #: implementation would offer a user a command that fails at RUN time —
    #: `docs/testing.md` §5.p, *a documented capability is not a capability*, and
    #: for an unattended batch it means dying mid-run. `tests/test_uiscript.py`
    #: sweeps this against the runner's real handlers, so it cannot go stale in
    #: either direction.
    implemented: bool = True

    def arity_problem(self, count: int) -> str | None:
        """Human-readable arity complaint, or ``None`` when the count is fine."""
        if count < self.min_args:
            return (
                f"'{self.name}' needs at least {self.min_args} argument(s), got {count}"
            )
        if self.max_args is not None and count > self.max_args:
            return (
                f"'{self.name}' takes at most {self.max_args} argument(s), got {count}"
            )
        return None


#: The vocabulary, grouped by what it is for. Order is the order the console's
#: reference lists them, so it reads as a tutorial rather than an alphabet.
_VERB_LIST: tuple[Verb, ...] = (
    # --- Narration and pacing ------------------------------------------------
    Verb("log", 1, None, "log <text> — write a line into the transcript"),
    Verb("wait", 1, 1, "wait <seconds> — pause (fractions allowed, max 600)"),
    Verb(
        "abort",
        0,
        None,
        "abort [reason] — stop the batch here (the only verb that does)",
    ),
    # --- Evidence ------------------------------------------------------------
    Verb(
        "screenshot",
        1,
        1,
        "screenshot <name> — save a PNG of the whole app, dialogs included",
    ),
    Verb(
        "snapshot",
        1,
        1,
        "snapshot <name> — record the visible state as text in the transcript",
    ),
    # --- Dialogs -------------------------------------------------------------
    Verb(
        "open",
        1,
        1,
        "open <settings|dependencies|about|diagnostics|guide|setup|drive> "
        "— open a dialog",
    ),
    Verb("ok", 0, 0, "ok — accept the dialog on top"),
    Verb("cancel", 0, 0, "cancel — dismiss the dialog on top"),
    Verb(
        "expect-dialog",
        1,
        1,
        "expect-dialog <title-or-none> — assert which dialog is on screen",
    ),
    # --- Settings ------------------------------------------------------------
    # Keyed on the **config.toml field name**, not the dialog's row label. A row
    # label is display text — translated, re-worded, re-ordered — so a script keyed
    # on it breaks for reasons unrelated to the setting. The field name is the same
    # identifier the TOML file, the validator's error messages and a bug report all
    # use. Every `set` is checked by the real validator before it is applied, so a
    # script can never persist a value the Settings dialog would have refused.
    Verb(
        "set",
        2,
        None,
        "set <config-field> <value> — change a setting (validated, then saved); "
        "booleans take on/off",
        takes_paths=True,
    ),
    Verb(
        "expect",
        2,
        None,
        "expect <config-field> <value> — assert a setting equals a value",
    ),
    Verb(
        "expect-contains",
        2,
        None,
        "expect-contains <config-field> <text> — assert a setting contains text",
    ),
    # --- Disc and rip --------------------------------------------------------
    Verb("rescan", 0, 0, "rescan — re-read the disc in the drive"),
    Verb(
        "album",
        1,
        None,
        "album <title> — set the album title, so repeat rips land in separate folders",
    ),
    Verb(
        "album-artist",
        1,
        None,
        "album-artist <name> — set the album artist for this rip",
    ),
    Verb(
        "select-tracks",
        1,
        1,
        "select-tracks <all|none|1,3,5-7> — choose which tracks the rip covers "
        "(this is cyanrip's -l)",
    ),
    Verb("rip", 0, 0, "rip — start the rip (needs an identified disc)"),
    Verb(
        "wait-for-rip",
        1,
        1,
        "wait-for-rip <seconds> — wait for the rip to finish, up to a timeout",
    ),
    Verb("cancel-rip", 0, 0, "cancel-rip — cancel a rip in progress"),
    Verb(
        # Deliberately still unimplemented, and the reference says so rather than
        # quietly omitting it. There is no single "status line" widget to assert
        # against — progress lives in the rip-progress pane and identification in
        # the disc panel — so a `expect-status` would have to pick one surface and
        # silently mean only that. `expect-dialog` and `expect-tracks` cover the
        # cases it was drafted for; this row stays as a marker that the gap is
        # known, not forgotten.
        "expect-status",
        1,
        None,
        "expect-status <text> — assert the status line contains text",
        implemented=False,
    ),
    Verb(
        "expect-tracks",
        1,
        1,
        "expect-tracks <count> — assert how many track rows are loaded",
    ),
    # --- cyanrip, passed through for real ------------------------------------
    Verb(
        "cyanrip",
        1,
        None,
        "cyanrip <args…> — run the host-exported ripper for real and capture "
        "its exit code, exact argv and complete output",
        takes_paths=True,
    ),
    Verb(
        "expect-cyanrip",
        1,
        None,
        "expect-cyanrip <text> — assert the last cyanrip output contains text",
    ),
    Verb(
        "expect-exit",
        1,
        1,
        "expect-exit <code> — assert the last cyanrip exit code",
    ),
    Verb(
        "rig-check",
        0,
        # Rest of the line, NOT one token — the argument is an album FOLDER, and
        # every real one has spaces in it ("The Police/Every Breath You Take").
        # Declared as 1 argument it rejected every genuine path with an arity
        # complaint while the handler was already calling `step.joined()`, so the
        # verb's advertised arity contradicted its own implementation. Same
        # reasoning as `album`: a verb whose tail is human text takes the tail.
        None,
        "rig-check [album-folder] — run the seam check the cyanrip fork asked "
        "for: compose a real rip's argv, read it back out of the ripper's own -j "
        "record, classify the build, and parse the album's log. Read-only",
        takes_paths=True,
    ),
    # --- The escape hatch ----------------------------------------------------
    Verb(
        "eval",
        1,
        None,
        "eval <python> — evaluate an expression against the window (UNSAFE)",
        unsafe=True,
        implemented=False,
    ),
    Verb(
        "call",
        1,
        None,
        "call <method> [args] — call a window method by name (UNSAFE)",
        unsafe=True,
        implemented=False,
    ),
)

#: Name → Verb. Built once; the parser and the console both read this.
VERBS: dict[str, Verb] = {v.name: v for v in _VERB_LIST}

#: The dialogs `open` knows about, mapped to the window method that opens each.
#: Data rather than branches for the same reason as the verb table: a reader can
#: see the entire reachable set without following call chains. Resolved lazily by
#: the runner so this module stays free of Qt.
#:
#: Every name here is asserted to EXIST on the window by
#: ``tests/test_uiscript.py::test_every_openable_dialog_names_a_real_method``.
#: Five of these seven were guessed wrong on the first attempt
#: (``open_settings_dialog``, ``open_about_dialog``, ``open_diagnostics_dialog``,
#: ``open_user_guide``, ``open_drive_setup_dialog`` — not one of which exists),
#: and a wrong name here fails at *run* time, in front of an unattended batch,
#: which is the worst possible moment to discover a typo.
OPENABLE: dict[str, str] = {
    "settings": "_on_open_settings",
    "dependencies": "run_dependency_check",
    "about": "_on_show_about",
    "diagnostics": "_on_show_diagnostics",
    "guide": "_on_show_help",
    "setup": "open_host_setup_dialog",
    "drive": "_on_drive_setup",
}


def verb_reference() -> str:
    """The vocabulary as help text, rendered from the table itself.

    The console shows this instead of a hand-maintained list — the project has
    been bitten enough times by a second description that drifts from the first
    (`docs/testing.md` §5.af).
    """
    lines = ["Commands (one per line; # starts a comment):", ""]
    for verb in _VERB_LIST:
        marks = []
        if not verb.implemented:
            # First, and in capitals. A user scanning this reference is choosing
            # what to put in a batch that will run while they are not watching.
            marks.append("NOT YET IMPLEMENTED")
        if verb.unsafe:
            marks.append("needs the unsafe opt-in")
        mark = f"  [{'; '.join(marks)}]" if marks else ""
        lines.append(f"  {verb.help}{mark}")
    lines.append("")
    lines.append(f"Dialogs `open` accepts: {', '.join(sorted(OPENABLE))}")
    return "\n".join(lines)


#: Flags that make a cyanrip invocation a *probe* rather than a rip — it prints
#: something and exits without touching metadata, the drive, or any audio.
#:
#: This distinction is the whole reason scripted invocations need their own
#: sanitiser rather than the rip path's. `assert_metadata_lookup_disabled`
#: requires `-N` on every argv, and it is right to: without it cyanrip runs its
#: own MusicBrainz lookup, which **can block on an interactive prompt with no
#: terminal attached** — an unattended batch would hang forever, which is the
#: exact failure this whole feature exists to prevent.
#:
#: **`-x` and `-j` were in this set and had to come out (2026-08-11).** Both are
#: **rip modifiers**, and the fork's own published provider contract says so: in
#: `docs/handshake/inbound/artifacts/round-07-lap-39-provider-contract-g422d12a.md`
#: they are rows 40 and 42, inside `### Ripping options` — not `### Metadata
#: options`, where the genuinely non-ripping `-I`/`-J` live. `-x` measures the
#: drive's cache *before ripping*; `-j` writes a diagnostics record *of a rip*.
#: Exempting them inverted the contract: a scripted `cyanrip -x` was a full rip
#: with MusicBrainz lookup ENABLED, which is precisely the unattended hang the
#: sanitiser exists to prevent. Every other `-x` call site in this repo already
#: passed `-N` (`rig_session.sh`, `police-rerip.txt`, the archived rig sheets) —
#: the convention was right everywhere and only the exemption was wrong.
#:
#: What remains is only what the contract's line 92 says prints and exits:
#: *"-v, -V and --version all print the version banner and exit 0"*, plus help.
#: `-I` and `-J` are deliberately NOT here: they do not rip, but they DO reach
#: the drive and DO run the metadata lookup unless `-N` is passed — the fork's
#: own probe invocation is `cyanrip -d <dev> -I -N -A -U -P 0 -x`, carrying it.
#: The version flags come from `cyanrip_cli.VERSION_FLAGS` rather than being
#: spelled again here. That module is the single home for them precisely because
#: this seam has already broken once: upstream removed `-V` after 0.9.3 and every
#: probe that hardcoded it started reporting the ripper as *missing*.
#: `tests/test_cyanrip_version_flag.py` refuses a second copy, and it caught this
#: line the moment it was written — the gate working exactly as intended.
PROBE_FLAGS: frozenset[str] = frozenset({*VERSION_FLAGS, "-v", "--help", "-h"})

#: Flags that read a **file we name** and report on it, then exit — no disc, no
#: metadata, no audio. Unlike :data:`PROBE_FLAGS` these take exactly one operand,
#: so they cannot be recognised by "every argument is a probe flag".
#:
#: **Why this set exists at all.** The application's own adapter has invoked
#: ``[cyanrip, --verify-log, <path>]`` — with no ``-N`` — once per rip since
#: v0.6.x (:mod:`platterpus.adapters.ripper_log_verify`), and correctly: there is
#: no lookup to disable on a path that only checksums a text file. The script
#: surface refused the identical argv, so the same invocation was legitimate from
#: our code and forbidden from a test of our code. That asymmetry is what the
#: cyanrip fork's round-8 C6 test walked into.
#:
#: **The evidence, not the reasoning.** Their published provider contract lists
#: ``-Y`` / ``--verify-log`` under ``### Misc. options`` — the same structural
#: test that took ``-x`` and ``-j`` *out* of :data:`PROBE_FLAGS`, where the
#: contract had them under ``### Ripping options``. The contract is the authority
#: on which side of that line a flag sits; a plausible argument about what a flag
#: "obviously" does is how the last exemption got it backwards.
#:
#: Narrow on purpose: the exemption applies only to an argv that is *exactly*
#: one of these plus one non-flag operand. ``--verify-log x.log -d /dev/sr0`` is
#: not covered and never will be.
FILE_ONLY_FLAGS: frozenset[str] = frozenset({VERIFY_LOG_FLAG, "-Y"})
