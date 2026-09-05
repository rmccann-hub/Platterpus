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
    Verb(
        "abort-if-failed",
        0,
        None,
        "abort-if-failed [reason] — stop ONLY if a step has already failed. For a "
        "PRECONDITION (am I on the right build?), where continuing gathers hours "
        "of evidence about the wrong subject. A finding must never use this.",
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
    # `ok` and `cancel` answer whatever is on top RIGHT NOW, and fail if nothing
    # is. That is the wrong shape for a dialog raised by an action the script just
    # took: a rip start is *requested* on the GUI thread and the confirmation
    # appears a beat later, so `rip` followed by `ok` is a race — the same
    # "asserting it was REQUESTED, not that it HAPPENED" defect that cost eight
    # steps in v0.6.17, arriving through a different door.
    #
    # It bit for real on 2026-08-20: section E of the cancel-path rig script ripped
    # the same disc twice, the second `rip` raised "Album already ripped", and
    # `wait-for-rip` failed with *"no rip is running"* — then advised adding `ok`,
    # which would have raced. Two of that run's two failures came from it (the
    # second was `rig-check` examining the cancelled rip because no second rip ever
    # produced one).
    #
    # So this verb WAITS, and it NAMES WHAT IT IS ANSWERING. A bare accept in an
    # unattended run will happily click OK on a dialog nobody predicted — a crash
    # report, a "disc has changed", an overwrite prompt — and an unattended script
    # has no operator to notice. Requiring the title makes the step a check as well
    # as an action: it asserts *which* question it answered, so a different dialog
    # is a loud failure instead of a silent yes.
    #
    # Title last so it can be a bare multi-word substring with no quoting, the same
    # shape `album` already uses. Case-insensitive substring, like `expect-dialog`.
    #
    # `click=` exists because `ok` cannot answer a THREE-button dialog at all, and
    # fails at it *silently*. `accept()` on a QMessageBox built with `addButton`
    # leaves `clickedButton()` as None, so a caller shaped like
    # `_confirm_known_overwrite` — `if clicked is replace: … if clicked is new: …
    # return None  # Cancel` — falls straight through to the CANCEL branch. So
    # `answer-dialog ok … Album already ripped` would have CANCELLED the rip while
    # the transcript recorded "accepted". Found 2026-08-21 while writing the rig
    # script that would have depended on it, by reading that fall-through instead of
    # assuming it. A substring rather than the whole label because `script.parse`
    # splits args on whitespace with no quoting, so "Rip to a new folder" cannot be
    # one argument — `click=new` can.
    Verb(
        "answer-dialog",
        3,
        None,
        "answer-dialog <ok|cancel|click=<label-substring>> <seconds> "
        "<title-substring> — wait up to <seconds> for a dialog whose title "
        "contains <title-substring>, then accept it, dismiss it, or click the "
        "one button whose label contains <label-substring>; fails if a different "
        "dialog is up at the deadline, or if the named button is absent, "
        "ambiguous or disabled",
    ),
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
        # An MBID rather than a row number is the documented form because
        # MusicBrainz ordering is not stable: `pick-release 2` would silently
        # mean a different release next month, and a rip tagged from the wrong
        # release is an error that survives into the archive.
        "pick-release",
        1,
        2,
        "pick-release <mbid|prefix|N> [seconds] — answer the MusicBrainz release "
        "picker when a disc has more than one candidate, so an unattended run "
        "does not stop at a modal. Passes without choosing only if no picker "
        "appears AND tracks are loaded (the disc was unambiguous)",
    ),
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
        # IMPLEMENTED 2026-08-24. It sat here with `implemented=False` and a
        # written reason — "there is no single 'status line' widget to assert
        # against ... so it would have to pick one surface and silently mean only
        # that" — and the reason was answerable rather than fatal: pick the
        # surface and SAY WHICH, in the help text and in every failure message.
        # That is what the rest of this codebase does with a measurement.
        #
        # What forced it: the full-acceptance rig script used the verb, because it
        # is published in `docs/script-language.md` as part of the language, and
        # got an ERROR back (2026-08-23, transcript L179). A row kept as "a marker
        # that the gap is known" is indistinguishable, from a script author's
        # side, from a capability — `CLAUDE.md`'s "capabilities we advertise but
        # do not deliver". Implement or remove; there is no third state.
        #
        # The surface is `RipProgress.current_status()` — the label under the
        # Overall bar, the one that reads "Idle.", "… · Rip cancelled by user.
        # Partial files may remain." or "… · Done — all 2 tracks ripped cleanly".
        # It is already the public accessor the desktop notification reads, so the
        # verb and the notification cannot disagree about what the status IS.
        "expect-status",
        1,
        None,
        "expect-status <text> — assert the rip status line (the one under the "
        "Overall progress bar) contains text, case-insensitively",
    ),
    Verb(
        # `expect-rip-complete` — assert the rip FINISHED, from the ripper's own
        # log rather than from a label on screen.
        #
        # **This verb exists because `expect-status Done` was the wrong
        # assertion, and it cost an ARCHIVAL section on 2026-09-03.** §N's rip
        # ran to the end, wrote all 14 tracks, reported `Ripping errors: 0` and
        # an intact completion footer -- and the step failed, because the status
        # line read *"Read stability: tracks 3, 4, 5 still didn't read
        # identically even after an automatic re-rip"* and does not contain the
        # word "Done".
        #
        # The product is RIGHT. `ui/rip_progress.py` deliberately overwrites the
        # completion line with the stability summary, because a 2026-07-28 audit
        # found the unattended user -- the notification's entire audience --
        # being told "all tracks ripped cleanly" while the window said a track
        # never read reproducibly. Two facts, one slot, and the more alarming
        # one wins on purpose.
        #
        # So `expect-status Done` conflates *finished* with *finished clean*,
        # and on any disc with a track that will not converge it can only ever
        # report the second. The fix is not to loosen it -- a loosened assertion
        # with a confident comment is worse than no assertion -- it is to assert
        # the right proposition against the right witness: the parsed rip log,
        # which is the provenance record, not a widget.
        #
        # Tri-state, like every provenance answer here: a log with no completion
        # footer reports NOT DETERMINED and FAILS. Read instability is reported
        # in the detail and is deliberately NOT a failure of this verb -- it is
        # a fact about the disc, which `rig-check`'s paranoia row and the
        # EAC-compatible log both already carry.
        "expect-rip-complete",
        0,
        0,
        "expect-rip-complete — assert the last rip FINISHED, read from the "
        "ripper's own log (completion footer, track tally, no truncation) rather "
        "than from the status line; read instability is reported, not graded",
    ),
    Verb(
        # `expect-log-well-formed` — assert the RECORD is intact, whatever the
        # rip's verdict was.
        #
        # **A third proposition, and section I had neither of the other two.**
        # §I is ARCHIVAL for *"the log's completion footer"* -- it exists because
        # a cancel once destroyed it (round 14 lap 10) -- and its only graded step
        # was `expect-status cancelled`, a substring match on a widget label. That
        # is the same class of defect as the `expect-status Done` above, in the
        # one section whose entire subject is whether the record survived.
        #
        # **And the obvious fix is wrong.** Measured from the 2026-09-03 bundle,
        # the cancelled rip's log reads `completed=True, 3 of 14,
        # interrupted_at=None`: cyanrip signs off a cancelled rip with a
        # *completed* footer. So `expect-rip-complete` would PASS on it and say
        # nothing about §I's claim, and an inverse "expect-interrupted" would FAIL
        # on real data. Neither states the proposition.
        #
        # The proposition is: **the record is well-formed, with EITHER verdict.**
        # Footer present (tri-state -- absent is NOT DETERMINED and never a pass),
        # not truncated, and the FUN512 signature present and the right shape. The
        # signature is the load-bearing one: cyanrip writes it from `atexit`, so a
        # rip killed hard leaves an unattested log, which is exactly the failure
        # §I is named for.
        #
        # Self-consistency rather than a fixed expectation: an incomplete last
        # track block is graded ONLY when the footer claims the rip completed, in
        # which case the record contradicts itself. After a cancel it is expected
        # and is reported, not graded.
        "expect-log-well-formed",
        0,
        0,
        "expect-log-well-formed — assert the ripper's log is an intact, attested "
        "record (completion footer present with EITHER verdict, not truncated, "
        "FUN512 signature well-formed); use where a rip was cancelled and "
        "`expect-rip-complete` cannot state the claim",
    ),
    Verb(
        # `expect-secure-rerip` — grade what section N only ever REPORTED.
        #
        # §N is ARCHIVAL and its stated pass criterion is `rig-check`'s paranoia
        # row reading *"secure re-read genuinely exercised: YES"*. That row is
        # `INFO`. **Nothing graded it**, so a rip in which `-Z` did precisely
        # nothing passed the section whose entire subject is that `-Z` worked
        # (found 2026-09-05).
        #
        # It delegates to `parsers.rip_log.secure_rerip_tracks_scoped`, the same
        # predicate the `rig-check` row renders from. Re-deriving the answer here
        # from `rip_count` or `secure_rerip_converged` would be a second key for
        # one question, which is how two surfaces disagree with both tests green.
        "expect-secure-rerip",
        0,
        0,
        "expect-secure-rerip — assert the secure re-read actually RAN on this "
        "rip (at least one track block carries cyanrip's Scope: line), the "
        "graded form of rig-check's 'genuinely exercised' row",
    ),
    Verb(
        # `expect-identified` — assert the disc was IDENTIFIED, not merely
        # counted.
        #
        # §E's gate was `expect-tracks 2+`, and a disc MusicBrainz cannot identify
        # still fills the table: `track_table.set_placeholder_tracks` writes
        # "Track 01".."Track NN" with "Unknown Artist", mirroring the tags an
        # unknown-album rip writes. So the count passed, `abort-if-failed` did not
        # fire, and every rip after §E would have been evidence about a release
        # nobody chose. The section's own comment says "if this fails, nothing
        # after it can mean anything" -- which was true and unenforced.
        #
        # Keyed on `_current_release_id`, the MusicBrainz MBID, because that is
        # the AUTHORITATIVE signal: it is set from `detail.summary.mbid` when a
        # release is chosen and cleared to "" on every placeholder path. Sniffing
        # titles for "Track 01" would be a heuristic over a fact, and would also
        # libel a real album genuinely titled "Unknown Album".
        "expect-identified",
        0,
        0,
        "expect-identified — assert the disc was identified against MusicBrainz "
        "(a well-formed release MBID is held), not merely that the track table "
        "has rows, which placeholder rows also satisfy",
    ),
    Verb(
        # `expect-refused` — the ONLY way a script can assert that validation
        # WORKED. `set` reports FAIL when the pure validator refuses a value, and
        # a refusal is the correct outcome for a bad input — so a script exercising
        # the validation subsystem could not tell "the guard fired" from "the run
        # broke", and the acceptance suite therefore tested none of it.
        #
        # `CLAUDE.md` makes input validation institutional and says the pure
        # validator is the source of truth that tests assert against. This is that
        # assertion, reachable from the surface this project writes its tests in
        # rather than from a bespoke flag — the maintainer's 2026-08-11 directive.
        #
        # It asserts BOTH halves, because only the pair is a check: the validator
        # refused, AND the stored value is unchanged. A guard that reports a
        # refusal and writes the value anyway is the worse defect of the two and a
        # refusal-only assertion cannot see it.
        "expect-refused",
        2,
        None,
        "expect-refused <setting> <value> — assert the validator REFUSES this "
        "value and leaves the setting unchanged (the pass condition is a refusal)",
    ),
    Verb(
        # `expect-ripper-under-review` — the acceptance run's own subject, named
        # ONCE, in code, rather than copied into a committed text file.
        #
        # **Built because the copy went stale three times in two days.** The
        # acceptance script asserted `expect-cyanrip platterpus-fork-g796df32`;
        # the cyanrip fork then published `f2c0506` and `d9c058c` on the beta
        # channel our own in-app installer resolves. Each time, an operator who
        # followed our instructions installed the build we sent them to and was
        # told by our script it was the wrong one — in section A, four seconds in,
        # before any evidence existed.
        #
        # The fork proposed the fix in their round-14 lap 4 §C and it is right:
        # *"a hardcoded build tag in a committed script is a second copy of a fact
        # that lives in release-manifest.json. Two places holding one fact, and
        # only one of them has a checker."* This verb reads
        # `fork_source.PIN_UNDER_REVIEW`, which `tests/test_handshake_pin_under_
        # review.py` derives from the newest inbound handshake lap — so the chain
        # is *newest lap -> constant -> assertion*, single-keyed, and a pin move
        # fails in CI in milliseconds instead of on a rig two hours in.
        #
        # No arguments on purpose: a parameter would reintroduce the second copy.
        "expect-ripper-under-review",
        0,
        0,
        # The help text says "the handshake record names", NOT "the open round is
        # reviewing". Between rounds there is no open round — the pin the record
        # names is then the approved production pin — and the old wording made
        # this page state something false for exactly the period in which an
        # operator is most likely to be reading it. The failing step itself prints
        # the derived sentence (`fork_source.pin_under_review_role`).
        "expect-ripper-under-review — assert the installed cyanrip is the build "
        "the handshake record names: the build under review while a round is "
        "open, and the approved production pin between rounds (run a "
        "`cyanrip --version` first)",
    ),
    Verb(
        # `probe-ripper-wrapper` — the fork's round-15 §2 three commands, as a
        # verb rather than as three lines an operator pastes into a terminal.
        #
        # A VERB, not a flag, and `CLAUDE.md` is explicit about which is the
        # default: *"the entire point of adding the ability to run scripts is for
        # this. you dont need to build special arguements unless absolutely
        # needed."* The one thing that had to be true for a flag — that no GUI
        # exists at that point — is false here; the acceptance session is exactly
        # where this answer is wanted, because it lands in the single file the
        # operator uploads. The `--doctor` row is the *second* thin caller of the
        # same `ripper_wrapper_probe.probe()`, never a second implementation.
        #
        # NEVER FAILS THE RUN. A hanging wrapper does not stop the app ripping
        # (the app pipes its I/O), so a FAIL here would abort a six-hour pass over
        # something that does not affect a single rip. It records what it found and
        # moves on; the verdict is read out of the transcript.
        "probe-ripper-wrapper",
        0,
        0,
        "probe-ripper-wrapper — time the host-exported ripper wrapper, the "
        "container entry and the in-container binary to find which one fails to "
        "exit. Records the verdict; never fails the run",
    ),
    Verb(
        "expect-tracks",
        1,
        1,
        "expect-tracks <count|count+> — assert how many track rows are loaded; "
        "a trailing '+' means 'at least this many', which is what a script that "
        "must work on any disc actually wants",
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
