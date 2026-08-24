# The Platterpus test-script language

**Generated — do not hand-edit.** Regenerate with
`python scripts/emit_script_language.py`. Every fact below is read out of
the code that runs it: the verb table, the runner's live limit constants,
and `Config`'s own fields. A hand-written version of this page would be a
second description of the grammar, and would drift the week after it was
written.

Two audiences, one file: prose for a person, and the same facts as JSON at
the bottom for a machine. They are emitted from one pass over one set of
objects, so they cannot disagree with each other either.

## Syntax

One statement per line. `#` starts a comment; blank lines are ignored.
Arguments are separated by whitespace. Verb names are matched
case-insensitively.

Most values need no quoting: the verbs that take free text swallow the
rest of the line, which is why `album Synchronicity (rig pass 1)` works
as typed. **Double quotes group one value** when a verb takes a fixed
number of arguments and one of them contains spaces — a `--verify-log`
path under `~/Music/The Police/…` being the case that keeps arising. A
`#` inside quotes is part of the value, not a comment; an unterminated
quote is reported against its own line.

**A leading `~/` is expanded to your home directory** in the arguments
of the path-taking verbs (`set`, `cyanrip`, `rig-check`) — quoted or not.

That last part is a deliberate difference from a shell, where `"~/x"`
stays literal. The path that needs quoting is usually the same path that
needs expanding, so following the shell here would mean losing one to
gain the other, and both losses are silent. Free-text verbs such as
`log` and `expect-cyanrip` are left alone — those carry messages and
match patterns, and rewriting a pattern changes what an assertion
asserts. `~user/` is not supported.

A step that fails is recorded and the batch **continues**; only `abort`
stops it. That is deliberate for an unattended run: stopping at the first
failure throws away every later measurement, and the later ones are often
the ones that explain the first.

Every step ends in one of: `PASS`, `FAIL`, `ERROR`, `BLOCKED`, `SKIPPED`.

## Verbs

`args` is the accepted argument count; `rest of line` means the remaining
text is taken verbatim as one value.

| verb | args | status | what it does |
|---|---|---|---|
| `log` | 1+ (rest of line) | ready | log <text> — write a line into the transcript |
| `wait` | 1 | ready | wait <seconds> — pause (fractions allowed, max 600) |
| `abort` | 0+ (rest of line) | ready | abort [reason] — stop the batch here (the only verb that does) |
| `screenshot` | 1 | ready | screenshot <name> — save a PNG of the whole app, dialogs included |
| `snapshot` | 1 | ready | snapshot <name> — record the visible state as text in the transcript |
| `open` | 1 | ready | open <settings|dependencies|about|diagnostics|guide|setup|drive> — open a dialog |
| `ok` | 0 | ready | ok — accept the dialog on top |
| `cancel` | 0 | ready | cancel — dismiss the dialog on top |
| `answer-dialog` | 3+ (rest of line) | ready | answer-dialog <ok|cancel|click=<label-substring>> <seconds> <title-substring> — wait up to <seconds> for a dialog whose title contains <title-substring>, then accept it, dismiss it, or click the one button whose label contains <label-substring>; fails if a different dialog is up at the deadline, or if the named button is absent, ambiguous or disabled |
| `expect-dialog` | 1 | ready | expect-dialog <title-or-none> — assert which dialog is on screen |
| `set` | 2+ (rest of line) | ready | set <config-field> <value> — change a setting (validated, then saved); booleans take on/off |
| `expect` | 2+ (rest of line) | ready | expect <config-field> <value> — assert a setting equals a value |
| `expect-contains` | 2+ (rest of line) | ready | expect-contains <config-field> <text> — assert a setting contains text |
| `rescan` | 0 | ready | rescan — re-read the disc in the drive |
| `pick-release` | 1–2 | ready | pick-release <mbid|prefix|N> [seconds] — answer the MusicBrainz release picker when a disc has more than one candidate, so an unattended run does not stop at a modal. Passes without choosing only if no picker appears AND tracks are loaded (the disc was unambiguous) |
| `album` | 1+ (rest of line) | ready | album <title> — set the album title, so repeat rips land in separate folders |
| `album-artist` | 1+ (rest of line) | ready | album-artist <name> — set the album artist for this rip |
| `select-tracks` | 1 | ready | select-tracks <all|none|1,3,5-7> — choose which tracks the rip covers (this is cyanrip's -l) |
| `rip` | 0 | ready | rip — start the rip (needs an identified disc) |
| `wait-for-rip` | 1 | ready | wait-for-rip <seconds> — wait for the rip to finish, up to a timeout |
| `cancel-rip` | 0 | ready | cancel-rip — cancel a rip in progress |
| `expect-status` | 1+ (rest of line) | ready | expect-status <text> — assert the rip status line (the one under the Overall progress bar) contains text, case-insensitively |
| `expect-tracks` | 1 | ready | expect-tracks <count|count+> — assert how many track rows are loaded; a trailing '+' means 'at least this many', which is what a script that must work on any disc actually wants |
| `cyanrip` | 1+ (rest of line) | ready | cyanrip <args…> — run the host-exported ripper for real and capture its exit code, exact argv and complete output |
| `expect-cyanrip` | 1+ (rest of line) | ready | expect-cyanrip <text> — assert the last cyanrip output contains text |
| `expect-exit` | 1 | ready | expect-exit <code> — assert the last cyanrip exit code |
| `rig-check` | 0+ (rest of line) | ready | rig-check [album-folder] — run the seam check the cyanrip fork asked for: compose a real rip's argv, read it back out of the ripper's own -j record, classify the build, and parse the album's log. Read-only |
| `eval` | 1+ (rest of line) | **NOT IMPLEMENTED**; needs the unsafe opt-in | eval <python> — evaluate an expression against the window (UNSAFE) |
| `call` | 1+ (rest of line) | **NOT IMPLEMENTED**; needs the unsafe opt-in | call <method> [args] — call a window method by name (UNSAFE) |

A verb marked **NOT IMPLEMENTED** is listed on purpose rather than
omitted: a documented capability that is not a capability fails at *run*
time, in front of an unattended batch, which is the worst moment to
discover it. Listing it with the mark is how the gap stays visible.

## Dialogs `open` accepts

`about`, `dependencies`, `diagnostics`, `drive`, `guide`, `settings`, `setup`

## Limits

Read off the live constants. Every one of these exists so a typo or a
paste accident cannot strand an unattended run.

| limit | value |
|---|---|
| `max_script_lines` | 2000 |
| `max_line_characters` | 4000 |
| `max_wait_seconds` | 600.0 |
| `max_wait_for_rip_seconds` | 10800 |
| `cyanrip_timeout_seconds` | 300.0 |
| `cyanrip_unreapable_grace_seconds` | 20.0 |
| `max_captured_output_characters` | 8000 |
| `step_interval_ms` | 120 |
| `max_track_range_span` | 200 |
| `max_cyanrip_arguments` | 64 |
| `max_cyanrip_argument_characters` | 4000 |

## The cyanrip passthrough

`cyanrip <args…>` runs the **host-exported binary for real**, through the
same seam the application's own probes use. It is guarded: a rip
invocation missing `-N` is refused, by delegating to the same chokepoint
every application-built rip argv passes — not by restating its rule.
Without `-N` cyanrip runs its own metadata lookup and can block on an
interactive prompt with no terminal attached, so an unattended batch would
hang forever.

These flags are exempt, because they print something and exit without
touching metadata or the drive's audio:

`--help`, `--version`, `-V`, `-h`, `-v`

Arguments containing a newline or NUL are refused. That is not injection —
no shell is involved — it is **log forgery**: cyanrip writes its argv into
an archival log, and a newline could fabricate a line in a document whose
whole purpose is being trustworthy evidence.

## Settings `set` and `expect` accept

Keyed on the **`config.toml` field name**, not the dialog's row label — a
row label is display text and a script keyed on it breaks for reasons
unrelated to the setting. Every `set` is checked by the same validator the
Settings dialog uses, so a script can never persist a value the dialog
would have refused; a *warning*-severity issue does not block, because the
dialog lets a person proceed past one and a script must not be stricter
than the UI it stands in for.

| field | value type |
|---|---|
| `output_dir` | text |
| `working_dir` | text |
| `track_template` | text |
| `disc_template` | text |
| `track_template_unknown` | text |
| `disc_template_unknown` | text |
| `metaflac_path` | text |
| `read_offset` | integer |
| `override_read_offset` | boolean (on/off) |
| `auto_launch_picard` | boolean (on/off) |
| `auto_eject_after_rip` | boolean (on/off) |
| `notify_on_completion` | boolean (on/off) |
| `drive_setup_prompted` | boolean (on/off) |
| `host_setup_prompted` | boolean (on/off) |
| `appimage_integration_prompted` | boolean (on/off) |
| `integration_declined_path` | text |
| `library_dir` | text |
| `debug_logging` | boolean (on/off) |
| `cover_art` | text |
| `save_additional_art` | boolean (on/off) |
| `max_retries` | integer |
| `force_overread` | boolean (on/off) |
| `secure_rerip_matches` | integer |
| `secure_rerip_dynamic` | boolean (on/off) |
| `rerip_offset_variant` | boolean (on/off) |
| `read_speed_mode` | text |
| `read_speed` | integer |
| `ctdb_verify_after_rip` | boolean (on/off) |
| `verify_flac_after_rip` | boolean (on/off) |
| `recompress_flac_after_rip` | boolean (on/off) |
| `write_eac_log_after_rip` | boolean (on/off) |
| `output_format` | text |
| `mp3_vbr_quality` | integer |
| `rip_goal` | text |
| `update_channel` | text |
| `ripper_channel` | text |
| `test_script_path` | text |
| `test_script_autorun` | boolean (on/off) |
| `test_script_allow_unsafe` | boolean (on/off) |
| `schema_version` | integer |

## Rules for writing a test that is worth running

These are not style preferences. Every one was paid for by a green test
that was measuring nothing, here or in the cyanrip fork. The general
versions live in `docs/testing.md`; what follows is how each one lands in
a *script*, which is where they are easiest to get wrong because a script
runs unattended and nobody watches it pass.

**1. Every script needs a floor — an assertion that fails when nothing
happened.** `rip` on a disc that was never identified rips zero tracks and
reports success exactly like a real rip. `expect-tracks <n>` before the
rip is the floor, and it is why the shipped example carries one with a
comment telling you not to delete it. *A check that can be satisfied by
finding nothing is decoration.*

**2. Assert the subject, not just the shape.** `expect-cyanrip 0.9.4` is
satisfied by stock upstream. `expect-cyanrip platterpus-fork-g<sha>` is
satisfied only by the build you meant. Where a check matches on a label,
make it also require the content — the label answers *did they name it*,
the content answers *did they do it*, and only the pair is a check.

**3. Pin your input, not only your logic.** A script that sets nothing
inherits whatever the config happened to hold from the last run, so a
passing result describes a configuration you cannot reconstruct. `expect`
the settings the outcome depends on *before* the step that depends on
them, even the ones you did not change.

**4. A failure is data. Do not abort on it.** The batch continues past a
failed step on purpose: the later measurements are often what explain the
earlier failure, and a rig session is the scarce resource. Reach for
`abort` only when continuing would be unsafe or meaningless — for example
when the wrong ripper is installed, because every artifact after that
point describes the wrong binary.

**5. Give every pass its own name.** `album <title>` decides the output
folder. Two passes with one title means the second overwrites the first,
and a session that destroys its own evidence has destroyed the thing it
was run to produce.

**6. Bound everything that waits.** `wait-for-rip` takes a timeout because
an unattended run that hangs is indistinguishable from one still working.
The caps in the table above are backstops for typos, not a substitute for
choosing a real number.

**7. Say which build produced the artifact.** Start with `cyanrip
--version` and assert the build tag. A version number cannot separate the
fork from upstream — the fork deliberately carries upstream's — and two
logs of one disc from two binaries are not interchangeable evidence.

**8. Record what you could not test.** A transcript that omits a step
reads like a transcript that passed it. If something needs a person, put
a `log` line saying so, in the script, at the point it would have run.

## Worked example, annotated

The smallest script that is actually worth running. Every line is one of
the rules above.

```
log ===== identity first =====
cyanrip --version                       # rule 7: which binary is this?
expect-exit 0
expect-cyanrip platterpus-fork-gddf7ac3 # rule 2: the tag, not the version

log ===== pin the inputs =====
expect output_format flac               # rule 3: state what you rely on
set force_overread off                  # -O hangs the BDR-209D
expect force_overread off               # and prove the set took

log ===== the disc =====
rescan
wait 20
expect-tracks 14                        # rule 1: THE FLOOR
select-tracks all
album Synchronicity (pass 1)            # rule 5: its own folder

log ===== rip =====
rip
wait-for-rip 5400                       # rule 6: bounded
screenshot after-rip
```

A fuller one, kept current and runnable, is
`docs/rig-scripts/police-rerip.txt`.

## Recipes

| you want to… | write |
|---|---|
| re-rip only the tracks that failed | `select-tracks 3,7,11-13` |
| prove a probe refuses on a disc image | `cyanrip -x -N` then `expect-cyanrip not run` |
| check a setting without changing it | `expect <field> <value>` |
| test the cancel path | `rip`, `wait 30`, `cancel-rip`, `wait-for-rip 120` |
| capture the whole window, dialogs included | `screenshot <name>` |
| record visible state as text | `snapshot <name>` |
| run any ripper invocation for real | `cyanrip <args…>` |

## Adding a verb

Two edits, and the order matters because the second is what makes the
first real:

1. Add a `Verb(...)` row to `src/platterpus/uiscript/verbs.py`. That table
   **is the security boundary** — the parser refuses anything not listed,
   so a new capability is a deliberate edit rather than a side effect of
   implementing something else.
2. Add a `_do_<name>` method to `src/platterpus/uiscript/runner.py`
   (hyphens become underscores).

`tests/test_uiscript.py` sweeps the table against the runner's real
handlers in both directions, so an advertised verb with no implementation
— or an implementation nobody can reach — fails CI rather than failing at
run time in front of an unattended batch. Regenerate this page afterwards:
`python scripts/emit_script_language.py`.

**Drive the real widget.** A handler should reach the same slot a click
reaches, not build its own version of the action. A harness that is safer
or simpler than the product makes the product's gap invisible, which is
the same reason the `cyanrip` verb is a real passthrough rather than a
simulation.

**What must never become a verb:** ejecting, deleting, uninstalling,
installing a dependency, launching an external application. The failure
mode of an unattended destructive action is unbounded, and every one of
those is reachable from a GUI a person is driving. A script that needs one
of them is a script that needs a person.

## Outcomes, and what each one means

| outcome | meaning |
|---|---|
| `PASS` | the step did what it said |
| `FAIL` | the step ran and the assertion did not hold — **the batch continues** |
| `ERROR` | the step could not run at all: a bad argument, a missing widget, a runner fault |
| `BLOCKED` | the verb needs the unsafe opt-in, which is off |
| `SKIPPED` | never reached, because `abort` stopped the batch earlier |

`ERROR` and `FAIL` are different on purpose. `FAIL` is a measurement —
the product did something you did not expect. `ERROR` is the script or the
harness being wrong, and it means the measurement never happened. Reading
them as the same thing turns *a test that could not run* into *a test that
found nothing wrong*.

## The same thing, as data

```json
{
  "language": "platterpus-uiscript",
  "grammar_version": 1,
  "platterpus_version": "0.6.23",
  "syntax": {
    "one_statement_per_line": true,
    "comment_prefix": "#",
    "blank_lines_ignored": true,
    "argument_separator": "whitespace",
    "quoting": false,
    "case_sensitive_verbs": false,
    "trailing_free_text_verbs": [
      "log",
      "abort",
      "answer-dialog",
      "set",
      "expect",
      "expect-contains",
      "album",
      "album-artist",
      "expect-status",
      "cyanrip",
      "expect-cyanrip",
      "rig-check",
      "eval",
      "call"
    ]
  },
  "verbs": [
    {
      "name": "log",
      "min_args": 1,
      "max_args": null,
      "unsafe": false,
      "takes_paths": false,
      "implemented": true,
      "help": "log <text> \u2014 write a line into the transcript"
    },
    {
      "name": "wait",
      "min_args": 1,
      "max_args": 1,
      "unsafe": false,
      "takes_paths": false,
      "implemented": true,
      "help": "wait <seconds> \u2014 pause (fractions allowed, max 600)"
    },
    {
      "name": "abort",
      "min_args": 0,
      "max_args": null,
      "unsafe": false,
      "takes_paths": false,
      "implemented": true,
      "help": "abort [reason] \u2014 stop the batch here (the only verb that does)"
    },
    {
      "name": "screenshot",
      "min_args": 1,
      "max_args": 1,
      "unsafe": false,
      "takes_paths": false,
      "implemented": true,
      "help": "screenshot <name> \u2014 save a PNG of the whole app, dialogs included"
    },
    {
      "name": "snapshot",
      "min_args": 1,
      "max_args": 1,
      "unsafe": false,
      "takes_paths": false,
      "implemented": true,
      "help": "snapshot <name> \u2014 record the visible state as text in the transcript"
    },
    {
      "name": "open",
      "min_args": 1,
      "max_args": 1,
      "unsafe": false,
      "takes_paths": false,
      "implemented": true,
      "help": "open <settings|dependencies|about|diagnostics|guide|setup|drive> \u2014 open a dialog"
    },
    {
      "name": "ok",
      "min_args": 0,
      "max_args": 0,
      "unsafe": false,
      "takes_paths": false,
      "implemented": true,
      "help": "ok \u2014 accept the dialog on top"
    },
    {
      "name": "cancel",
      "min_args": 0,
      "max_args": 0,
      "unsafe": false,
      "takes_paths": false,
      "implemented": true,
      "help": "cancel \u2014 dismiss the dialog on top"
    },
    {
      "name": "answer-dialog",
      "min_args": 3,
      "max_args": null,
      "unsafe": false,
      "takes_paths": false,
      "implemented": true,
      "help": "answer-dialog <ok|cancel|click=<label-substring>> <seconds> <title-substring> \u2014 wait up to <seconds> for a dialog whose title contains <title-substring>, then accept it, dismiss it, or click the one button whose label contains <label-substring>; fails if a different dialog is up at the deadline, or if the named button is absent, ambiguous or disabled"
    },
    {
      "name": "expect-dialog",
      "min_args": 1,
      "max_args": 1,
      "unsafe": false,
      "takes_paths": false,
      "implemented": true,
      "help": "expect-dialog <title-or-none> \u2014 assert which dialog is on screen"
    },
    {
      "name": "set",
      "min_args": 2,
      "max_args": null,
      "unsafe": false,
      "takes_paths": true,
      "implemented": true,
      "help": "set <config-field> <value> \u2014 change a setting (validated, then saved); booleans take on/off"
    },
    {
      "name": "expect",
      "min_args": 2,
      "max_args": null,
      "unsafe": false,
      "takes_paths": false,
      "implemented": true,
      "help": "expect <config-field> <value> \u2014 assert a setting equals a value"
    },
    {
      "name": "expect-contains",
      "min_args": 2,
      "max_args": null,
      "unsafe": false,
      "takes_paths": false,
      "implemented": true,
      "help": "expect-contains <config-field> <text> \u2014 assert a setting contains text"
    },
    {
      "name": "rescan",
      "min_args": 0,
      "max_args": 0,
      "unsafe": false,
      "takes_paths": false,
      "implemented": true,
      "help": "rescan \u2014 re-read the disc in the drive"
    },
    {
      "name": "pick-release",
      "min_args": 1,
      "max_args": 2,
      "unsafe": false,
      "takes_paths": false,
      "implemented": true,
      "help": "pick-release <mbid|prefix|N> [seconds] \u2014 answer the MusicBrainz release picker when a disc has more than one candidate, so an unattended run does not stop at a modal. Passes without choosing only if no picker appears AND tracks are loaded (the disc was unambiguous)"
    },
    {
      "name": "album",
      "min_args": 1,
      "max_args": null,
      "unsafe": false,
      "takes_paths": false,
      "implemented": true,
      "help": "album <title> \u2014 set the album title, so repeat rips land in separate folders"
    },
    {
      "name": "album-artist",
      "min_args": 1,
      "max_args": null,
      "unsafe": false,
      "takes_paths": false,
      "implemented": true,
      "help": "album-artist <name> \u2014 set the album artist for this rip"
    },
    {
      "name": "select-tracks",
      "min_args": 1,
      "max_args": 1,
      "unsafe": false,
      "takes_paths": false,
      "implemented": true,
      "help": "select-tracks <all|none|1,3,5-7> \u2014 choose which tracks the rip covers (this is cyanrip's -l)"
    },
    {
      "name": "rip",
      "min_args": 0,
      "max_args": 0,
      "unsafe": false,
      "takes_paths": false,
      "implemented": true,
      "help": "rip \u2014 start the rip (needs an identified disc)"
    },
    {
      "name": "wait-for-rip",
      "min_args": 1,
      "max_args": 1,
      "unsafe": false,
      "takes_paths": false,
      "implemented": true,
      "help": "wait-for-rip <seconds> \u2014 wait for the rip to finish, up to a timeout"
    },
    {
      "name": "cancel-rip",
      "min_args": 0,
      "max_args": 0,
      "unsafe": false,
      "takes_paths": false,
      "implemented": true,
      "help": "cancel-rip \u2014 cancel a rip in progress"
    },
    {
      "name": "expect-status",
      "min_args": 1,
      "max_args": null,
      "unsafe": false,
      "takes_paths": false,
      "implemented": true,
      "help": "expect-status <text> \u2014 assert the rip status line (the one under the Overall progress bar) contains text, case-insensitively"
    },
    {
      "name": "expect-tracks",
      "min_args": 1,
      "max_args": 1,
      "unsafe": false,
      "takes_paths": false,
      "implemented": true,
      "help": "expect-tracks <count|count+> \u2014 assert how many track rows are loaded; a trailing '+' means 'at least this many', which is what a script that must work on any disc actually wants"
    },
    {
      "name": "cyanrip",
      "min_args": 1,
      "max_args": null,
      "unsafe": false,
      "takes_paths": true,
      "implemented": true,
      "help": "cyanrip <args\u2026> \u2014 run the host-exported ripper for real and capture its exit code, exact argv and complete output"
    },
    {
      "name": "expect-cyanrip",
      "min_args": 1,
      "max_args": null,
      "unsafe": false,
      "takes_paths": false,
      "implemented": true,
      "help": "expect-cyanrip <text> \u2014 assert the last cyanrip output contains text"
    },
    {
      "name": "expect-exit",
      "min_args": 1,
      "max_args": 1,
      "unsafe": false,
      "takes_paths": false,
      "implemented": true,
      "help": "expect-exit <code> \u2014 assert the last cyanrip exit code"
    },
    {
      "name": "rig-check",
      "min_args": 0,
      "max_args": null,
      "unsafe": false,
      "takes_paths": true,
      "implemented": true,
      "help": "rig-check [album-folder] \u2014 run the seam check the cyanrip fork asked for: compose a real rip's argv, read it back out of the ripper's own -j record, classify the build, and parse the album's log. Read-only"
    },
    {
      "name": "eval",
      "min_args": 1,
      "max_args": null,
      "unsafe": true,
      "takes_paths": false,
      "implemented": false,
      "help": "eval <python> \u2014 evaluate an expression against the window (UNSAFE)"
    },
    {
      "name": "call",
      "min_args": 1,
      "max_args": null,
      "unsafe": true,
      "takes_paths": false,
      "implemented": false,
      "help": "call <method> [args] \u2014 call a window method by name (UNSAFE)"
    }
  ],
  "openable_dialogs": [
    "about",
    "dependencies",
    "diagnostics",
    "drive",
    "guide",
    "settings",
    "setup"
  ],
  "cyanrip_probe_flags": [
    "--help",
    "--version",
    "-V",
    "-h",
    "-v"
  ],
  "limits": {
    "max_script_lines": 2000,
    "max_line_characters": 4000,
    "max_wait_seconds": 600.0,
    "max_wait_for_rip_seconds": 10800,
    "cyanrip_timeout_seconds": 300.0,
    "cyanrip_unreapable_grace_seconds": 20.0,
    "max_captured_output_characters": 8000,
    "step_interval_ms": 120,
    "max_track_range_span": 200,
    "max_cyanrip_arguments": 64,
    "max_cyanrip_argument_characters": 4000
  },
  "settable_fields": [
    {
      "field": "output_dir",
      "type": "text"
    },
    {
      "field": "working_dir",
      "type": "text"
    },
    {
      "field": "track_template",
      "type": "text"
    },
    {
      "field": "disc_template",
      "type": "text"
    },
    {
      "field": "track_template_unknown",
      "type": "text"
    },
    {
      "field": "disc_template_unknown",
      "type": "text"
    },
    {
      "field": "metaflac_path",
      "type": "text"
    },
    {
      "field": "read_offset",
      "type": "integer"
    },
    {
      "field": "override_read_offset",
      "type": "boolean (on/off)"
    },
    {
      "field": "auto_launch_picard",
      "type": "boolean (on/off)"
    },
    {
      "field": "auto_eject_after_rip",
      "type": "boolean (on/off)"
    },
    {
      "field": "notify_on_completion",
      "type": "boolean (on/off)"
    },
    {
      "field": "drive_setup_prompted",
      "type": "boolean (on/off)"
    },
    {
      "field": "host_setup_prompted",
      "type": "boolean (on/off)"
    },
    {
      "field": "appimage_integration_prompted",
      "type": "boolean (on/off)"
    },
    {
      "field": "integration_declined_path",
      "type": "text"
    },
    {
      "field": "library_dir",
      "type": "text"
    },
    {
      "field": "debug_logging",
      "type": "boolean (on/off)"
    },
    {
      "field": "cover_art",
      "type": "text"
    },
    {
      "field": "save_additional_art",
      "type": "boolean (on/off)"
    },
    {
      "field": "max_retries",
      "type": "integer"
    },
    {
      "field": "force_overread",
      "type": "boolean (on/off)"
    },
    {
      "field": "secure_rerip_matches",
      "type": "integer"
    },
    {
      "field": "secure_rerip_dynamic",
      "type": "boolean (on/off)"
    },
    {
      "field": "rerip_offset_variant",
      "type": "boolean (on/off)"
    },
    {
      "field": "read_speed_mode",
      "type": "text"
    },
    {
      "field": "read_speed",
      "type": "integer"
    },
    {
      "field": "ctdb_verify_after_rip",
      "type": "boolean (on/off)"
    },
    {
      "field": "verify_flac_after_rip",
      "type": "boolean (on/off)"
    },
    {
      "field": "recompress_flac_after_rip",
      "type": "boolean (on/off)"
    },
    {
      "field": "write_eac_log_after_rip",
      "type": "boolean (on/off)"
    },
    {
      "field": "output_format",
      "type": "text"
    },
    {
      "field": "mp3_vbr_quality",
      "type": "integer"
    },
    {
      "field": "rip_goal",
      "type": "text"
    },
    {
      "field": "update_channel",
      "type": "text"
    },
    {
      "field": "ripper_channel",
      "type": "text"
    },
    {
      "field": "test_script_path",
      "type": "text"
    },
    {
      "field": "test_script_autorun",
      "type": "boolean (on/off)"
    },
    {
      "field": "test_script_allow_unsafe",
      "type": "boolean (on/off)"
    },
    {
      "field": "schema_version",
      "type": "integer"
    }
  ],
  "outcomes": [
    "PASS",
    "FAIL",
    "ERROR",
    "BLOCKED",
    "SKIPPED"
  ]
}
```

*Last updated for Platterpus v0.6.23.*
