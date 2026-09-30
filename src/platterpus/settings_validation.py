"""Pure validation of Settings / Config inputs — the "validate every input" rule.

CLAUDE.md (Code conventions → *Validate every input and every dependency
output*) requires that every value entering the program from outside the code is
checked for **type, range, character set, and format** at its boundary, with a
**visible** error and a **log** entry. This module is that boundary for the
Settings dialog and for a hand-edited ``config.toml``.

It is deliberately **pure**: a function over a :class:`~platterpus.config.Config`
that returns a list of :class:`ValidationIssue`. No Qt, no persistence, and the
only I/O is a couple of cheap, best-effort path probes (does this folder exist,
is its parent writable). The dialog renders the issues (visible errors), refuses
to save while any *error* remains, and logs them — but every rule lives *here*
so it is unit-testable without a GUI and holds equally for a config file someone
edited by hand.

Three smaller boundaries live here too, for the same reason (one home for the
rules, all of them assertable without a GUI): :func:`path_segment_issue` for the
metadata values a rip turns into folder/file names, :func:`describe_resets` for
telling the user what a config load had to throw away, and
:func:`resolve_input_directory` for a folder handed to the CLI.

Two severities:
  * :data:`SEVERITY_ERROR`   — the value would break a rip or write somewhere it
    can't; the dialog blocks **OK** until it's fixed.
  * :data:`SEVERITY_WARNING` — the value is legal but probably not intended (an
    unknown ``%``-token, a tool not yet on ``PATH``); shown, never blocked.

Design note (why this exists as its own module): a widget's own constraint — a
``QSpinBox`` range, a ``QComboBox``'s fixed items — is a *convenience*, not the
validation. Successive sessions leaned on those piecemeal and never validated the
free-text inputs (paths, templates, tool paths), which is the gap this closes.
The pure validator is the single source of truth; the widgets just make the happy
path easier to hit.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from platterpus import goal_presets
from platterpus.config import Config
from platterpus.cyanrip_cli import (
    DEFAULT_MAX_RETRIES,
    retries_flag_value,
    secure_reread_problem,
    whole_track_reads_allowed,
)
from platterpus.deps.ripper_manifest import CHANNELS as RIPPER_CHANNELS
from platterpus.update_check import CHANNELS

log = logging.getLogger(__name__)

SEVERITY_ERROR: str = "error"
SEVERITY_WARNING: str = "warning"

# The ``%``-tokens a naming template may use (see naming.py / cyanrip_backend).
# Anything else after a ``%`` (other than ``%%``) is an unknown token — legal to
# type, but almost always a typo, so it's a WARNING, not an error.
_KNOWN_TEMPLATE_TOKENS: frozenset[str] = frozenset("AadntyYNM")

# Numeric field bounds — the SINGLE source of truth (the Settings spinboxes read
# these so the widget range and the validator can never drift apart). A
# hand-edited config outside these bounds is an error.
OFFSET_MIN: int = -5000
OFFSET_MAX: int = 5000
MAX_RETRIES_MIN: int = 0
MAX_RETRIES_MAX: int = 100
SECURE_REREP_MIN: int = 0
# The user's number is the ceiling; this is only the sanity cap the maintainer
# allowed ("do not hardcode a max, unless it's like 10") — a spinner bound, not
# a substitute for their choice.
SECURE_REREP_MAX: int = 10
READ_SPEED_MIN: int = 0
READ_SPEED_MAX: int = 72  # CD ×-speeds; 0 = drive max

# The Settings row labels for the two retry settings, as the validator's
# messages name them. A message that names a control must name one the user can
# find: the secure re-read row was renamed on 2026-09-21 and this module kept
# saying "Max reads to confirm a shaky track" for a week. The dialog spells the
# label as a literal (its source is swept for row labels), and
# `tests/test_secure_reread_can_converge.py` holds the two equal.
MAX_RETRIES_LABEL: str = "Max retries"
SECURE_REREP_LABEL: str = "Extra matching reads to trust a track"
MP3_QUALITY_MIN: int = 0
MP3_QUALITY_MAX: int = 9

# Windows/NTFS/exFAT portability hazards in a naming template's LITERAL text
# (maintainer-approved warning, 2026-07-21 — see docs/dependency-contracts.md
# "Not sanitised — a documented cross-filesystem limitation"). These are all
# LEGAL on the Linux target, so they are a WARNING (never an error) and only
# matter when the library is copied to Windows/macOS or a mounted NTFS/exFAT
# volume. Only the template's literal parts can be judged here — hazards in
# tag VALUES (an album title ending in a dot, say) are produced at rip time by
# cyanrip's own sanitiser and are out of this validator's reach by design
# (Critical rule #3: the ripper owns naming).
_WINDOWS_RESERVED_CHARS: frozenset[str] = frozenset('<>:"\\|?*')
_WINDOWS_RESERVED_NAMES: frozenset[str] = frozenset(
    {"con", "prn", "aux", "nul"}
    | {f"com{n}" for n in range(1, 10)}
    | {f"lpt{n}" for n in range(1, 10)}
)

# Enum-valued fields → their allowed values (must match the Settings combos and
# the consumers downstream). Kept here so the validator rejects a bad hand-edit.
_ALLOWED_OUTPUT_FORMATS: frozenset[str] = frozenset({"flac", "wavpack", "mp3", "wav"})
_ALLOWED_COVER_ART: frozenset[str] = frozenset({"", "embed", "file", "complete"})
_ALLOWED_READ_SPEED_MODES: frozenset[str] = frozenset({"auto_ladder", "fixed"})
# Derived from update_check.CHANNELS rather than restated, so adding a channel
# there cannot leave a value the validator rejects (or worse, silently allows).
_ALLOWED_UPDATE_CHANNELS: frozenset[str] = frozenset(CHANNELS)
# Likewise derived from the ripper manifest's own vocabulary rather than restated.
# `tests/test_ripper_manifest.py` asserts the two channel tuples agree, so one
# Settings vocabulary covers both and neither can grow a value the other rejects.
_ALLOWED_RIPPER_CHANNELS: frozenset[str] = frozenset(RIPPER_CHANNELS)


@dataclass(frozen=True)
class ValidationIssue:
    """One thing wrong (or suspicious) about a config value.

    ``field`` is the :class:`Config` attribute name, so the dialog can map it
    back to the offending widget (to mark it) and so a log line is greppable.
    ``message`` is user-facing and specific ("Output directory must be an
    absolute path", not "invalid path").
    """

    field: str
    message: str
    severity: str = SEVERITY_ERROR

    def is_error(self) -> bool:
        return self.severity == SEVERITY_ERROR


def validate_config(config: Config) -> list[ValidationIssue]:
    """Validate every field of ``config``; return all issues (errors + warnings).

    Never raises — a validator that crashed would be worse than the invalid
    input it was meant to catch (it would take the Settings dialog down). Any
    unexpected failure is logged with its traceback and reported as a WARNING on
    that field, so the rest still run.

    **A crash is a warning: not a pass, and not an error** (maintainer ruling
    D17, KDD-38, 2026-09-25). It used to count as "no
    issue", so a value its check could not evaluate passed silently; three such
    crashes were found by the property tests that day. An error would be worse:
    at startup an error resets the field to its default, so a bug in a validator
    would reset a correct setting (the read offset included) and the next disc
    would rip wrong with a clean-looking log. A warning keeps the value, shows
    the user that it could not be checked, and does not block Save.

    **Each rule is isolated.** This used to be one big ``try`` around every
    check, which failed *open*: a hand-edited ``config.toml`` with, say, an
    integer where ``output_dir`` belongs made the very first rule raise, and the
    single ``except`` then swallowed it and returned the issues gathered so far
    — an empty list. The dialog read that as "everything is valid" and happily
    saved the rest of a corrupt file. One bad field must never disable the other
    twenty-odd rules (audit finding, 2026-07-28).
    """
    issues: list[ValidationIssue] = []

    def run(
        rule: str, check: Callable[..., list[ValidationIssue]], *args: object
    ) -> None:
        """Run one rule; a crash in it becomes a warning on that field (D17)."""
        try:
            issues.extend(check(*args))
        except Exception:  # noqa: BLE001 — a validator must never crash the dialog
            log.exception(
                "settings validation rule %r raised; its value is kept, unchecked",
                rule,
            )
            issues.append(
                ValidationIssue(
                    rule,
                    f"Platterpus couldn't check this setting ({rule}), so its value "
                    "was kept as it is. The log has the details.",
                    SEVERITY_WARNING,
                )
            )

    run(
        "output_dir", _validate_dir, "output_dir", config.output_dir, "Output directory"
    )
    # The library folder is OPTIONAL — empty means "leave rips in the output
    # directory" (the feature is off), so only a non-empty value goes through
    # the directory rules. A control char hiding in "whitespace" must still be
    # rejected — the strip() would otherwise let it persist to config.toml.
    run("library_dir", _validate_library_dir, config.library_dir)

    for field_name, label in (
        ("track_template", "Track template"),
        ("disc_template", "Disc template"),
        ("track_template_unknown", "Track template (unknown)"),
        ("disc_template_unknown", "Disc template (unknown)"),
    ):
        run(
            field_name,
            _validate_template,
            field_name,
            getattr(config, field_name),
            label,
        )

    run(
        "metaflac_path",
        _validate_tool_path,
        "metaflac_path",
        config.metaflac_path,
        "metaflac",
    )

    for field_name, low, high, label in (
        ("read_offset", OFFSET_MIN, OFFSET_MAX, "Read offset"),
        ("max_retries", MAX_RETRIES_MIN, MAX_RETRIES_MAX, MAX_RETRIES_LABEL),
        (
            "secure_rerip_matches",
            SECURE_REREP_MIN,
            SECURE_REREP_MAX,
            SECURE_REREP_LABEL,
        ),
        ("read_speed", READ_SPEED_MIN, READ_SPEED_MAX, "Fixed read speed"),
        ("mp3_vbr_quality", MP3_QUALITY_MIN, MP3_QUALITY_MAX, "MP3 VBR quality"),
    ):
        run(
            field_name,
            _validate_int,
            field_name,
            getattr(config, field_name),
            low,
            high,
            label,
        )

    # The PAIR, after each half's own range rule. Max retries is also the ceiling
    # on a secure re-read's whole-track reads, and `-Z N` needs N+1 of them, so a
    # pair of in-range values can still describe a re-read that never succeeds.
    run(
        "max_retries",
        _validate_secure_reread_ceiling,
        config.max_retries,
        config.secure_rerip_matches,
    )

    for field_name, allowed, label in (
        ("output_format", _ALLOWED_OUTPUT_FORMATS, "Output format"),
        ("cover_art", _ALLOWED_COVER_ART, "Cover art"),
        ("read_speed_mode", _ALLOWED_READ_SPEED_MODES, "Read speed mode"),
        ("rip_goal", _allowed_goals(), "Goal"),
        ("update_channel", _ALLOWED_UPDATE_CHANNELS, "Update channel"),
        ("ripper_channel", _ALLOWED_RIPPER_CHANNELS, "cyanrip update channel"),
    ):
        run(
            field_name,
            _validate_choice,
            field_name,
            getattr(config, field_name),
            allowed,
            label,
        )

    # Every remaining field is a boolean toggle or bookkeeping value. We validate
    # their TYPE too (a hand-edited config.toml could put a string where a
    # bool/int belongs) so "cover completely" is literal — every Config field has
    # a rule (the completeness meta-test enforces this).
    for field_name in _BOOL_FIELDS:
        run(field_name, _validate_bool, field_name, getattr(config, field_name))
    run(
        "integration_declined_path",
        _validate_str,
        "integration_declined_path",
        config.integration_declined_path,
    )
    # Its other half. Validated separately rather than as one blob because they
    # are two values with two shapes — a filesystem path and a version string —
    # and a single check would have to be loose enough for both.
    run(
        "integration_declined_version",
        _validate_str,
        "integration_declined_version",
        config.integration_declined_version,
    )
    run("test_script_path", _validate_test_script_path, config.test_script_path)
    run(
        "test_script_allow_unsafe",
        _validate_unsafe_opt_in,
        config.test_script_allow_unsafe,
    )
    run(
        "schema_version",
        _validate_plain_int,
        "schema_version",
        config.schema_version,
    )
    return issues


def _validate_unsafe_opt_in(value: object) -> list[ValidationIssue]:
    """The unsafe-verbs opt-in may be ON only once an unsafe verb is built.

    Read-only until then in every place a value can come from: this box, the config
    file (a hand-edited ``true`` is reset on load) and a script's ``set``.
    """
    from platterpus.uiscript.verbs import UNSAFE_VERBS_BUILT

    if value is True and not UNSAFE_VERBS_BUILT:
        return [
            ValidationIssue(
                "test_script_allow_unsafe",
                "The unsafe script verbs (eval, call) are not built yet, so this "
                "cannot be turned on until they exist.",
            )
        ]
    return []


def _validate_test_script_path(value: object) -> list[ValidationIssue]:
    """The optional unattended-test script: valid *format*, and it must exist.

    Empty means "no saved script" and is the default — the feature is simply off,
    so an empty value is not an error. A **non-empty** value is a promise that a
    batch will run from it, and the whole point of the feature is that nobody is
    watching when it does: a path that silently resolves to nothing produces a
    launch that looks identical to one where every test passed. So a set path is
    held to existing, being a regular file, and being readable, and the failure is
    reported *in the dialog while the user is typing it* rather than discovered
    by an empty transcript the next morning.

    Deliberately NOT checked here: whether the file parses. The script parser is
    the authority on that, it never raises, and a syntax error renders as a
    reported step at the line that caused it — which is more useful than a
    Settings error that says "line 12 is wrong" and refuses to save.
    """
    if not isinstance(value, str):  # type before content, as everywhere here
        return [
            ValidationIssue("test_script_path", "The test script path must be text.")
        ]
    # RAW value, before strip(): str.strip() eats the C0 information separators,
    # so a leading control character would pass a check on the stripped text and
    # still reach `open()`. Same trap the tool-path validator closes.
    if _has_control_char(value):
        return [
            ValidationIssue(
                "test_script_path",
                "Test script path may not contain control characters.",
            )
        ]
    text = value.strip()
    if not text:
        return []
    try:
        path = Path(text).expanduser()
        if not path.exists():
            return [ValidationIssue("test_script_path", f"No file at: {text}")]
        if path.is_dir():
            return [
                ValidationIssue(
                    "test_script_path", f"{text} is a folder, not a script."
                )
            ]
        if not os.access(path, os.R_OK):
            return [ValidationIssue("test_script_path", f"{text} cannot be read.")]
    except (OSError, RuntimeError) as exc:  # see _probe_failure
        reason = _probe_failure(exc)
        return [ValidationIssue("test_script_path", f"No file at: {text} ({reason})")]
    return []


def _validate_library_dir(value: object) -> list[ValidationIssue]:
    """The optional library folder: full directory rules only when it's set."""
    text = value if isinstance(value, str) else ""
    if text.strip():
        return _validate_dir("library_dir", text, "Library folder")
    if _has_control_char(text):
        return [
            ValidationIssue(
                "library_dir", "Library folder contains an illegal character."
            )
        ]
    if not isinstance(value, str):
        return [ValidationIssue("library_dir", "Library folder must be text.")]
    return []


# The boolean toggles — validated for type so a corrupt config.toml (a string
# where a bool belongs) is caught, not silently coerced.
_BOOL_FIELDS: tuple[str, ...] = (
    "override_read_offset",
    "force_overread",
    "auto_launch_picard",
    "auto_eject_after_rip",
    "notify_on_completion",
    "drive_setup_prompted",
    "host_setup_prompted",
    "appimage_integration_prompted",
    "debug_logging",
    "secure_rerip_dynamic",
    "rerip_offset_variant",
    "ctdb_verify_after_rip",
    "verify_flac_after_rip",
    "recompress_flac_after_rip",
    "write_eac_log_after_rip",
    "save_additional_art",
    "test_script_autorun",
    "test_script_allow_unsafe",
)


def validated_field_names() -> frozenset[str]:
    """Every Config field name this module validates.

    The completeness meta-test asserts this equals the set of Config fields — so
    a new setting can't be added without a validation rule (CLAUDE.md: validate
    *every* input). Keep this in step with :func:`validate_config`.
    """
    return frozenset(
        {
            "output_dir",
            "track_template",
            "disc_template",
            "track_template_unknown",
            "disc_template_unknown",
            "metaflac_path",
            "read_offset",
            "max_retries",
            "secure_rerip_matches",
            "read_speed",
            "mp3_vbr_quality",
            "output_format",
            "cover_art",
            "read_speed_mode",
            "rip_goal",
            "update_channel",
            "ripper_channel",
            "integration_declined_path",
            "integration_declined_version",
            "library_dir",
            "schema_version",
            "test_script_path",
        }
        | set(_BOOL_FIELDS)
    )


def errors_only(issues: list[ValidationIssue]) -> list[ValidationIssue]:
    """The blocking subset — issues that must be fixed before saving."""
    return [i for i in issues if i.is_error()]


def field_error(candidate: Config, field: str) -> str:
    """The validator's own complaint about ``field`` in ``candidate``, or ``""``.

    The one question every single-setting writer asks: the script verb ``set``,
    and each control that lives outside Settings and saves as it is changed
    (the drive wizard's Apply tick-box, the update channels in Setup & Updates,
    the script console's startup options). One predicate, so a script cannot
    write a value its control would refuse, or the reverse.

    Only a hard error counts: a warning is advice the Settings dialog shows and
    still lets a person accept. ``is_error`` is a METHOD and is called — read as
    an attribute it is a bound method, always truthy, and every warning would be
    reported as a refusal (pinned by ``tests/test_uiscript_settings.py``).
    Never raises: a validator fault is reported as a refusal, never as a pass.

    **Every refusal it answers is logged, here, once** (:func:`log_refusal`).
    Because this is the one predicate every single-setting writer asks, logging
    at the answer covers all of them without any caller remembering to — which
    is what they had all been forgetting (2026-09-28, the round-28 Full run: five
    deliberate script refusals, including a read offset of 99999, wrote nothing
    to the log at all). A caller must therefore NOT log the refusal again.
    """
    try:
        issues = validate_config(candidate)
    except Exception:  # noqa: BLE001 — a validator fault must not become a silent set
        log.exception("settings validation raised while checking %s", field)
        reason = "the settings validator could not evaluate this value"
        log_refusal(field, getattr(candidate, field, _VALUE_UNAVAILABLE), reason)
        return reason
    for issue in issues:
        if issue.field == field and issue.is_error():
            log_refusal(
                field, getattr(candidate, field, _VALUE_UNAVAILABLE), issue.message
            )
            return issue.message
    return ""


#: What a refusal line says when the refused value cannot be read off the config
#: (the field name is not an attribute). Stated, so it never reads as an empty value.
_VALUE_UNAVAILABLE: str = "<value unavailable>"

#: How much of a refused value's ``repr`` a log line carries. A template or a path
#: can be long, and a hand-edited config can hold anything; the log line must stay
#: one readable line. Head and tail, with the gap counted, like every other bound.
_REFUSED_VALUE_HEAD: int = 160
_REFUSED_VALUE_TAIL: int = 60


def _loggable_value(value: object) -> str:
    """``repr(value)``, bounded, for a log line. **Never raises.**

    ``repr`` rather than ``str`` on purpose: it escapes control characters, so a
    refused value holding a newline cannot forge a second log line — and control
    characters are exactly what several rules here refuse. Bounded to a head and
    a tail with the elided count marked, because a silent truncation reads as
    completeness (CLAUDE.md).
    """
    if value is _VALUE_UNAVAILABLE:
        return _VALUE_UNAVAILABLE
    try:
        text = repr(value)
    except Exception:  # noqa: BLE001 — a log line must not fail over its own subject
        return f"<unrepresentable {type(value).__name__}>"
    limit = _REFUSED_VALUE_HEAD + _REFUSED_VALUE_TAIL
    if len(text) <= limit:
        return text
    dropped = len(text) - limit
    return (
        f"{text[:_REFUSED_VALUE_HEAD]}… [{dropped} character(s) elided] …"
        f"{text[-_REFUSED_VALUE_TAIL:]}"
    )


def log_refusal(field: str, value: object, reason: str) -> None:
    """THE log line for a settings value the input boundary refused.

    CLAUDE.md (*Validate every input*): invalid input gets a visible error at the
    point of entry **and is logged to the log file**. The visible half was in
    place on every surface; the log half was not — the uiscript ``set`` and
    ``expect-refused`` verbs and the save-as-you-change controls refused without a
    word to the log. One function, so the line has one shape — setting name, the
    refused value, the validator's own reason — wherever it was refused, and a
    bug report can grep for ``settings input refused`` and find every one.

    Called by :func:`field_error` (every single-setting writer), by
    :func:`log_issues` for the Settings dialog and a hand-edited config file, and
    by the script runner for a value it could not even coerce to the setting's
    type. WARNING, because a refused value is an input the user or a script
    actually tried. Never raises: ``_loggable_value`` cannot, and ``logging``
    routes a handler's own failure to ``handleError`` rather than to its caller.
    """
    log.warning(
        "settings input refused: %s = %s — %s", field, _loggable_value(value), reason
    )


# --- Values that become a path SEGMENT inside a dependency -------------------
#
# A tag value (album title, album artist, track title) is substituted by cyanrip
# into one folder/file name — `-D "{album_artist}/{album}"`, `-F "{track} - {title}"`.
# cyanrip sanitises the characters that are *illegal* in a Linux path segment (a
# `/` inside a value becomes `∕`, a `:` becomes `∶` — see
# docs/dependency-contracts.md), which is why the GUI deliberately does not
# re-sanitise names (Critical rule #3: the ripper owns naming).
#
# But "." and ".." are not illegal characters — they are the two segments POSIX
# reserves to mean *this directory* and *the parent directory*. Nothing maps
# them, so an album titled ".." makes cyanrip's `-D` resolve one level ABOVE the
# output directory and the rip lands outside the folder the user chose. This is
# the exact bug already fixed for `%Y` (audit, 2026-07-28: a year of "../."
# escaped the output directory) — fixed there only for the one token Platterpus
# substitutes itself, and never generalised to the values cyanrip substitutes.
# Enforcing a rule at the place it was learned instead of across the codebase is
# its own documented failure mode (docs/testing.md §5.o), so the guard lives here
# as a pure function that both the entry point (the track table) and the argv
# builder call.
_PATH_REFERENCE_SEGMENTS: frozenset[str] = frozenset({".", ".."})


def path_segment_issue(label: str, value: str) -> str:
    """``""`` if ``value`` is safe as a rip path segment, else a specific message.

    Rejects only the two values that are directory *references* rather than
    names — ``.`` and ``..`` — plus their whitespace-padded forms (we can't see
    whether cyanrip trims a tag value before using it as a folder name, and no
    real release is titled ``" .. "``, so trimming before the comparison costs
    nothing and closes the guess). Everything else is left alone: a name like
    ``"..."`` or ``"Vol. 2."`` is a perfectly ordinary directory on the Linux
    target, and this function must not become a general-purpose sanitiser — that
    would duplicate cyanrip's naming logic and break the Settings
    preview↔reality round-trip (Critical rule #3).

    Also rejects control characters: a NUL truncates the argv string handed to
    the ripper (and `subprocess` raises on it mid-rip), and the other C0
    characters have no business in a filename.
    """
    if _has_control_char(value):
        return f"{label} contains an illegal character (a control character)."
    if value.strip() in _PATH_REFERENCE_SEGMENTS:
        return (
            f"{label} can’t be “{value.strip()}” — the rip uses it as a folder "
            "name, and that would write outside your output directory."
        )
    return ""


# --- Config-file values that had to be reset on load -------------------------


@dataclass(frozen=True)
class ResetRecord:
    """One config-file field that was invalid on load and reset to its default.

    ``old_value`` is the *rendered* value that was on disk (``repr``-ed by the
    producer, so a bad type shows as ``5`` vs ``'5'``), because the whole point
    of showing the user this notice is that they can put their real value back.
    """

    field: str
    message: str
    old_value: str
    new_value: str


def describe_resets(records: Sequence[ResetRecord]) -> str:
    """User-facing text for the fields a config load had to reset. ``""`` if none.

    Why this exists (audit, 2026-07-31): ``Config._sanitized()`` resets every
    error-level field to its default so an invalid value can never reach the
    ripper — correct — but it did so with **only a log line**, which is exactly
    the "silent reset" the *validate every input* convention forbids. The
    dangerous case is concrete and was already written down as a hazard in
    ``main_window_drive._set_read_offset_override`` without ever being closed on
    the read side: a hand-edited ``read_offset`` outside its bounds becomes ``0``
    while ``override_read_offset`` stays on, so the next disc is ripped at the
    **wrong offset** and nothing on screen says so.

    Pure and formatting-only (no Qt, no I/O) so the message is asserted in tests
    rather than scraped out of a dialog.
    """
    if not records:
        return ""
    lines = [
        "Some values in your settings file weren’t usable, so Platterpus is "
        "using its defaults for them instead. Your other settings were kept.",
        "",
    ]
    for record in records:
        lines.append(f"• {record.message}")
        lines.append(f"    was: {record.old_value}    now using: {record.new_value}")
    lines.append("")
    lines.append(
        "Nothing is written back yet. To keep your value, fix it in the file or where "
        "it lives (Settings, Setup & Updates, the script console); saving replaces it."
    )
    return "\n".join(lines)


# --- CLI path arguments ------------------------------------------------------


def resolve_input_directory(
    label: str, value: Path, *, must_exist: bool = True
) -> tuple[Path | None, str]:
    """Validate a folder given on the command line; return ``(resolved, error)``.

    ``argparse``'s ``type=Path`` only *constructs* a Path — it validates nothing —
    so a CLI folder argument was reaching the code completely unchecked. Two
    concrete consequences, both observed:

    * a folder that doesn't exist (or is a file) produced a misleading
      *"No .flac files found in …"* plus an unrelated scary warning about a
      missing rip log, instead of "that folder isn't there";
    * a **relative** folder starting with ``-`` (``./-x`` normalises to ``-x``)
      made the FLACs under it come out as ``-x/track.flac``, which ``flac`` and
      ``metaflac`` parse as *options*, not filenames — an argument injection into
      a dependency, i.e. the output-validation half of the rule.

    Resolving to an absolute path fixes the second by construction (an absolute
    path always starts with ``/``), and is what the caller should use from then
    on. Returns ``(None, message)`` on failure — the CLI prints the message and
    exits non-zero; never raises.

    ``must_exist=False`` is for an **output** folder the caller is about to
    create (``--rig-session``'s artifact directory). The argument-injection half
    of the check still applies — that is the half that matters for a path handed
    to a subprocess — but "it isn't there yet" stops being an error. A path that
    exists and is a *file* is still refused either way: that is a mistake, not a
    folder waiting to be made.
    """
    try:
        resolved = value.expanduser().resolve()
    except (OSError, RuntimeError) as exc:  # RuntimeError: symlink loop
        log.error("%s %r could not be resolved: %s", label, str(value), exc)
        return None, f"{label} could not be resolved: {value} ({exc})"
    if not must_exist:
        if resolved.exists() and not resolved.is_dir():
            log.error("%s exists and is not a folder: %s", label, resolved)
            return None, f"{label} is not a folder: {resolved}"
        return resolved, ""
    if not resolved.exists():
        log.error("%s does not exist: %s", label, resolved)
        return None, f"{label} does not exist: {resolved}"
    if not resolved.is_dir():
        log.error("%s is not a folder: %s", label, resolved)
        return None, f"{label} is not a folder: {resolved}"
    return resolved, ""


def log_issues(issues: list[ValidationIssue], config: Config | None = None) -> None:
    """Record validation issues to the log file (CLAUDE.md: log input failures).

    Errors log at WARNING (they blocked a save the user attempted); warnings log
    at INFO. Called by the dialog when the user tries to save with issues, so a
    bug report's log shows exactly what was rejected and why.

    **Pass the ``config`` the issues were found in**, and each error is logged
    through :func:`log_refusal` with the refused VALUE beside the setting and the
    reason — the same line every other surface writes. Without it the value is
    not known here, and the line says only what it can.
    """
    for issue in issues:
        if issue.is_error():
            if config is not None:
                value = getattr(config, issue.field, _VALUE_UNAVAILABLE)
                log_refusal(issue.field, value, issue.message)
            else:
                log.warning(
                    "settings validation error: %s — %s", issue.field, issue.message
                )
        else:
            log.info("settings validation warning: %s — %s", issue.field, issue.message)


# --- Per-field validators ----------------------------------------------------


def _validate_dir(field: str, value: object, label: str) -> list[ValidationIssue]:
    """A rip output/working directory: absolute, legal, and writable-or-creatable.

    We don't require the folder to *exist* (the rip creates it) — but we do
    check that it *could* be created: an absolute path whose nearest existing
    ancestor is a writable directory. The writability probe is best-effort; if
    we genuinely can't tell, we don't manufacture an issue.

    **Writability is a WARNING, not an error**, while shape (a string, absolute,
    non-empty, no control chars) is an error. ``..`` is deliberately *allowed*
    here, unlike in a naming template: a template nests **under** the output
    directory, so a ``..`` in it escapes a boundary the user chose, whereas the
    output directory **is** that boundary — ``/home/u/../shared/rips`` is just a
    folder the user picked, and there is nothing for it to escape from. (This
    docstring claimed a ``..`` check that the code has never done; corrected
    2026-07-31 rather than adding a rule that would reject a legitimate path.)
    The severity distinction matters because
    :meth:`Config._sanitized` resets every *error*-level field to its default on
    load: a rip library on a NAS or a removable disk that simply wasn't mounted
    at launch was therefore silently retargeted to ``~/Music/rips``, the library
    folder was silently cleared (turning auto-move off), and the next save
    persisted that — the user's real paths gone, with only a log line. "The
    volume isn't mounted right now" is an environmental condition, not an
    invalid value; it deserves a visible warning, not a rewrite of the config
    (audit finding, 2026-07-28).
    """
    # Type first. A hand-edited config.toml can put an integer or a list where a
    # path belongs; without this guard the rule raised, the caller swallowed it,
    # and the user was shown NO error for the one field that was actually broken
    # (audit finding, 2026-07-28 — the "fails open" half of the same bug).
    if not isinstance(value, str):
        return [ValidationIssue(field, f"{label} must be text (a folder path).")]
    raw = value or ""
    # Check for control characters on the RAW value, BEFORE stripping. Python's
    # str.strip() classifies the C0 "information separators" \x1c–\x1f (and
    # \t\n\r\v\f) as whitespace, so a leading/trailing one would be silently
    # trimmed here and slip past the check — yet it stays in the persisted config
    # value and reaches the rip as a real path character. A control char in the
    # MIDDLE was already caught; checking the raw value closes the leading/trailing
    # gap so the rule ("no control chars in a path") holds at every position.
    # (NUL was always caught since it isn't whitespace; this widens the net to its
    # whitespace-classified siblings — found by a position-fuzzing property test.)
    if _has_control_char(raw):
        return [ValidationIssue(field, f"{label} contains an illegal character.")]
    text = raw.strip()
    if not text:
        return [ValidationIssue(field, f"{label} cannot be empty.")]
    path = Path(text)
    if not path.is_absolute():
        return [
            ValidationIssue(
                field, f"{label} must be an absolute path (start with “/”)."
            )
        ]
    try:
        if path.exists():
            if not path.is_dir():
                return [
                    ValidationIssue(
                        field, f"{label} exists but is not a folder: {text}"
                    )
                ]
            if not os.access(path, os.W_OK):
                return [
                    ValidationIssue(
                        field,
                        f"{label} isn’t writable right now: {text}",
                        SEVERITY_WARNING,
                    )
                ]
            return []
        # Doesn't exist yet — walk up to the nearest existing ancestor and make
        # sure the rip could create the folder there.
        ancestor = path.parent
        while not ancestor.exists() and ancestor != ancestor.parent:
            ancestor = ancestor.parent
        if ancestor.exists() and not os.access(ancestor, os.W_OK):
            return [
                ValidationIssue(
                    field,
                    f"{label} can’t be created right now — “{ancestor}” isn’t "
                    "writable. If this is a removable disk or a network share, "
                    "mount it before ripping.",
                    SEVERITY_WARNING,
                )
            ]
    except OSError:
        # A permission error or odd filesystem while probing — don't block the
        # user over something we couldn't determine; the rip will surface a real
        # error if it truly can't write.
        log.debug("dir validation probe failed for %s=%s", field, text, exc_info=True)
    return []


def _validate_template(field: str, value: object, label: str) -> list[ValidationIssue]:
    """A naming template: non-empty, relative, legal chars, known tokens, renders.

    The template nests folders with its own ``/`` separators, so a leading ``/``
    (an absolute path) is an error — it would try to write to the filesystem root
    instead of under the output directory. Unknown ``%``-tokens are a warning
    (typo-catching), not an error, matching the live preview's pass-through.
    """
    from platterpus import naming

    if not isinstance(value, str):  # see _validate_dir — type before content
        return [ValidationIssue(field, f"{label} must be text.")]
    issues: list[ValidationIssue] = []
    text = value or ""
    if not text.strip():
        return [ValidationIssue(field, f"{label} cannot be empty.")]
    if _has_control_char(text):
        return [ValidationIssue(field, f"{label} contains an illegal character.")]
    # THE DECISION IS SHARED; ONLY THE WORDING IS OURS.
    #
    # A template must never write outside the output directory — an absolute path
    # goes to the filesystem root, a ".." segment climbs above the chosen folder.
    # Both were inline here, and the same judgement is now needed at the argv
    # chokepoint (`CLAUDE.md`: the output half "must be enforced by code at the
    # argv chokepoint — not merely stated"). Two copies of a safety check are two
    # things to drift, so `naming.path_escape_reason` decides and each caller
    # phrases its own message — this one for a person editing Settings, the
    # chokepoint's for a developer who has just added a route to the ripper.
    escapes = naming.path_escape_reasons(text)
    if "absolute" in escapes:
        issues.append(
            ValidationIssue(
                field,
                f"{label} must be a relative path (no leading “/”) — it nests "
                "under the output directory.",
            )
        )
    if "traversal" in escapes:
        issues.append(
            ValidationIssue(
                field,
                f"{label} can’t contain “..” — it would write outside the output "
                "directory.",
            )
        )
    # Unknown %-tokens (a %X where X isn't a known token and isn't %%).
    unknown = _unknown_tokens(text)
    if unknown:
        tokens = ", ".join(f"%{t}" for t in unknown)
        issues.append(
            ValidationIssue(
                field,
                f"{label} has unknown code(s) {tokens}. Valid: %A %a %d %n %t %y "
                "%Y %N %M (a literal % is written %%).",
                SEVERITY_WARNING,
            )
        )
    # Cross-filesystem portability (warning only — everything here is legal on
    # the Linux target): a template whose LITERAL text bakes in a Windows-unsafe
    # character/name would make every rip's folder un-copyable to Windows/NTFS.
    hazards = cross_fs_hazards(text)
    if hazards:
        issues.append(
            ValidationIssue(
                field,
                f"{label} may not copy cleanly to Windows or an NTFS/exFAT "
                f"drive: {'; '.join(hazards)}. Fine on Linux — only worth "
                "changing if this library will be copied there.",
                SEVERITY_WARNING,
            )
        )
    # Renders to something usable? (An all-token template of only unknown tokens,
    # or one that collapses to empty/slashes, would produce a nameless file.)
    try:
        rendered = naming.render_preview(text, naming.SAMPLE_STRESS)
        stripped = rendered[:-5] if rendered.endswith(".flac") else rendered
        if not stripped.strip("/ ").strip():
            issues.append(ValidationIssue(field, f"{label} renders to an empty name."))
        elif "//" in stripped:
            issues.append(
                ValidationIssue(
                    field,
                    f"{label} has an empty path segment (“//”).",
                    SEVERITY_WARNING,
                )
            )
    except Exception:  # noqa: BLE001 — preview is best-effort; don't block on it
        log.debug("template render probe failed for %s", field, exc_info=True)
    return issues


def cross_fs_hazards(template: str) -> list[str]:
    """Windows/NTFS-portability hazards in a template's LITERAL text.

    Returns human-readable descriptions ("" -free), empty when clean. Pure and
    deliberately conservative: a path segment containing a ``%`` token can't be
    judged until tag values exist at rip time, so token-bearing segments are
    only checked for reserved *characters* (which survive any substitution),
    never for reserved names or trailing dots/spaces. Hazards checked — all
    legal on Linux, all real on Windows/NTFS/exFAT:

    * reserved characters ``< > : " \\ | ? *`` anywhere in the literal text
      (``%%`` escapes are unfolded first so a literal ``%`` never confuses it);
    * reserved device names (``CON``, ``PRN``, ``AUX``, ``NUL``, ``COM1``–``9``,
      ``LPT1``–``9``) as a whole literal segment, with or without an extension
      (Windows reserves ``CON.flac`` too), case-insensitively;
    * a literal segment ending in a dot or space (Windows strips or rejects
      them, so the copied name silently changes or fails).
    """
    hazards: list[str] = []
    # Unfold %%-escapes and blank out the known tokens so only literal text
    # remains for the character scan ("%A" is not a literal "A").
    literal = template.replace("%%", "%")
    for token in _KNOWN_TEMPLATE_TOKENS:
        literal = literal.replace(f"%{token}", "")
    bad_chars = sorted(set(literal) & _WINDOWS_RESERVED_CHARS)
    if bad_chars:
        listed = " ".join(bad_chars)
        hazards.append(f"the character(s) {listed} are reserved on Windows")
    for segment in template.split("/"):
        # Only a TAG token makes a segment value-dependent. This used to skip any
        # segment containing a "%", but "%%" is a literal percent and an unknown
        # "%q" is kept as typed — so "CON.%%" (the device name CON) went unjudged.
        text, has_tag = _segment_text(segment)
        if has_tag:
            continue  # value-dependent — judged at rip time, not here
        stem = text.split(".", 1)[0].strip().lower()
        if stem in _WINDOWS_RESERVED_NAMES:
            hazards.append(f"“{segment}” is a reserved device name on Windows")
        if text != text.rstrip(". "):
            hazards.append(
                f"“{segment}” ends in a dot/space, which Windows strips or rejects"
            )
    return hazards


def _validate_tool_path(field: str, value: object, tool: str) -> list[ValidationIssue]:
    """A dependency binary override (e.g. metaflac): valid *format*.

    We validate what the user typed, not whether the tool is installed —
    availability is the dependency subsystem's job (Critical rule #6: no scattered
    dependency checks, and PATH at rip time can differ from the dialog's). So:
      * empty → error (the field must at least hold the bare name, e.g. "metaflac");
      * an explicit path (contains "/") → must point at an existing, executable
        file — the user named a specific binary, so a wrong one is a real error;
      * a bare command name → accepted as-is (resolved on PATH at run time; the
        dependency subsystem is the authority on whether it's actually present).
    """
    if not isinstance(value, str):  # see _validate_dir — type before content
        return [ValidationIssue(field, f"The {tool} path must be text.")]
    text = (value or "").strip()
    if not text:
        return [
            ValidationIssue(
                field, f"{tool} path cannot be empty (use the bare name “{tool}”)."
            )
        ]
    # BUG-6: a tool path is a charset-validated boundary too (CLAUDE.md), but this
    # validator alone omitted the control-char check. Check the RAW value — Python's
    # str.strip() eats the C0 "information separators" (\x1c–\x1f), so a leading/
    # trailing one would slip past a check on the stripped text yet reach the
    # subprocess argv (same trap the directory validators already close).
    if _has_control_char(value or ""):
        return [
            ValidationIssue(field, f"{tool} path may not contain control characters.")
        ]
    if "/" in text:
        try:
            p = Path(text).expanduser()
            if not p.exists():
                return [ValidationIssue(field, f"No {tool} executable at: {text}")]
            if p.is_dir() or not os.access(p, os.X_OK):
                return [ValidationIssue(field, f"{text} is not an executable file.")]
        except (OSError, RuntimeError) as exc:
            reason = _probe_failure(exc)
            return [
                ValidationIssue(field, f"No {tool} executable at: {text} ({reason})")
            ]
    return []


def _probe_failure(exc: OSError | RuntimeError) -> str:
    """Why a path could not be looked up at all, in words for the user.

    Two shapes reach here: ``~nobody/…`` names a user who does not exist
    (``expanduser`` raises ``RuntimeError``), and a component past the
    filesystem's name limit makes ``exists()`` raise ``ENAMETOOLONG``. Both used
    to escape their rule — and ``validate_config`` reports a rule that raises as
    NO issue, so the value was accepted. A path we cannot look up is not a path we
    can call fine.
    """
    if isinstance(exc, OSError) and exc.strerror:
        return exc.strerror
    return str(exc)


def _validate_int(
    field: str, value: object, lo: int, hi: int, label: str
) -> list[ValidationIssue]:
    """A whole-number field within [lo, hi]. A bool is NOT an int here."""
    if isinstance(value, bool) or not isinstance(value, int):
        return [ValidationIssue(field, f"{label} must be a whole number.")]
    if value < lo or value > hi:
        return [ValidationIssue(field, f"{label} must be between {lo} and {hi}.")]
    return []


def _validate_secure_reread_ceiling(
    max_retries: object, matches: object
) -> list[ValidationIssue]:
    """Max retries must let the configured secure re-read succeed.

    cyanrip's ``-Z N`` converges when the latest read matches N EARLIER reads, so
    it needs N+1 identical reads, and it stops re-reading a track after ``-r``
    whole-track reads (``cyanrip@faec4a8:src/cyanrip_main.c:997-1012``). The rule
    is :func:`platterpus.cyanrip_cli.secure_reread_problem`, the same one the argv
    chokepoint refuses at; this is where a person editing Settings, a script's
    ``set``, or a hand-edited ``config.toml`` meets it first.

    **Which settings actually send ``-Z``.** ``secure_rerip_matches`` > 0 sends
    ``-Z <that>`` in both modes: on every pass in uniform mode (Test & Copy), and
    on the targeted re-read of the tracks AccurateRip did not confirm in dynamic
    mode. The ladder never escalates past it. With it Off (0) the only ``-Z`` a
    rip sends is the worker's own recovery bound, which
    ``read_speed_ladder.recovery_secure_rerip_ceiling`` caps below ``-r`` itself,
    so Off never makes an impossible pair and is not refused here. ``-r`` is the
    argv's: ``cyanrip_cli.retries_flag_value`` sends none for 0, and cyanrip then
    uses its own default of 10.

    **Reported on BOTH fields**, because either one can be the one to fix, and
    because each consumer asks about one field: the ``set`` verb and every
    save-as-you-change control ask ``field_error`` about the field they are
    writing, and the startup reset puts each errored field back to its default.
    Reported on one field only, a script could write the other half of an
    impossible pair, and a reset could leave one half still impossible.

    **A zero-tolerance pair is a WARNING, not an error.** ``-r`` == N+1 can
    converge, but only if every read agrees: one bad read and the track is left
    unverified. Legal, and probably not intended — the 2026-09-28 Full run spent
    every secure re-read at ``-r 3 -Z 2`` that way without anyone choosing it.

    Values out of their own range, or of the wrong type, are the range rules'
    finding and are skipped here, so each message names one cause.
    """
    if isinstance(max_retries, bool) or not isinstance(max_retries, int):
        return []
    if isinstance(matches, bool) or not isinstance(matches, int):
        return []
    if not MAX_RETRIES_MIN <= max_retries <= MAX_RETRIES_MAX:
        return []
    if not SECURE_REREP_MIN < matches <= SECURE_REREP_MAX:
        return []  # Off, or out of range: nothing for this rule to judge
    retries = retries_flag_value(max_retries)
    reads = whole_track_reads_allowed(retries)
    shown = (
        f"{max_retries}"
        if retries is not None
        else f"0, which leaves cyanrip's own default of {DEFAULT_MAX_RETRIES}"
    )
    needed = matches + 1
    if secure_reread_problem(repeat_rips=matches, retries=retries):
        message = (
            f"{MAX_RETRIES_LABEL} ({shown}) must be more than {SECURE_REREP_LABEL} "
            f"({matches}). A track is trusted once {needed} of its reads are "
            f"identical, and {MAX_RETRIES_LABEL} lets cyanrip read it only {reads} "
            f"time{'s' if reads != 1 else ''}, so no track could ever be verified. "
            f"Raise {MAX_RETRIES_LABEL} to at least {needed}, or lower "
            f"{SECURE_REREP_LABEL}."
        )
        return [
            ValidationIssue("max_retries", message),
            ValidationIssue("secure_rerip_matches", message),
        ]
    if reads == needed:
        message = (
            f"{MAX_RETRIES_LABEL} ({shown}) leaves no room for a read that "
            f"disagrees: a track needs {needed} identical reads and cyanrip may read "
            f"it only {reads} times, so a single bad read leaves it unverified. "
            f"{MAX_RETRIES_LABEL} at {needed + 2} would allow two."
        )
        return [
            ValidationIssue("max_retries", message, SEVERITY_WARNING),
            ValidationIssue("secure_rerip_matches", message, SEVERITY_WARNING),
        ]
    return []


def _validate_choice(
    field: str, value: object, allowed: frozenset[str], label: str
) -> list[ValidationIssue]:
    """A field that must be one of a fixed set of string values."""
    # Type first: `[] in frozenset(...)` RAISES (a list is unhashable), and a
    # raising rule is reported as no issue at all — so `output_format = ["flac"]`
    # in a hand-edited config.toml used to be accepted.
    if not isinstance(value, str) or value not in allowed:
        shown = ", ".join(sorted(repr(a) for a in allowed))
        return [ValidationIssue(field, f"{label} must be one of: {shown}.")]
    return []


def _validate_bool(field: str, value: object) -> list[ValidationIssue]:
    """A toggle that must be a real boolean (a corrupt TOML could hold a string)."""
    if not isinstance(value, bool):
        return [ValidationIssue(field, f"{field} must be true or false.")]
    return []


def _validate_str(field: str, value: object) -> list[ValidationIssue]:
    """A free-text bookkeeping string: must be a string with no control chars."""
    if not isinstance(value, str):
        return [ValidationIssue(field, f"{field} must be text.")]
    if _has_control_char(value):
        return [ValidationIssue(field, f"{field} contains an illegal character.")]
    return []


def _validate_plain_int(field: str, value: object) -> list[ValidationIssue]:
    """A bookkeeping integer (no range) that must be an int, not a bool/string."""
    if isinstance(value, bool) or not isinstance(value, int):
        return [ValidationIssue(field, f"{field} must be a whole number.")]
    return []


#: The two Unicode line and paragraph separators. Not control characters by
#: category (they are Zl and Zp), but every text widget and `str.splitlines`
#: breaks a line at them, which is the harm the rule below exists to stop.
_LINE_SEPARATORS: frozenset[str] = frozenset({"\u2028", "\u2029"})


def is_control_char(ch: str) -> bool:
    """True for a character that has no place in a value we store or send.

    C0 (NUL, tab, newline…), DEL, C1 (U+0080–U+009F, which holds NEL, a line
    break), and the Unicode line and paragraph separators. So every character
    `str.splitlines` treats as a line boundary is covered, and a test derives that
    set from Python rather than listing it by hand.

    **Widened 2026-09-25.** It stopped at DEL, so a C1 character or U+2028 passed
    every check that used it, while the inbound screen (`inbound_text`) already
    flagged both. The ONE definition for outbound values: the path-bearing tag
    fields refuse these (:func:`path_segment_issue`), the tag-only fields replace
    them with a space (``tag_hygiene``, decision D14), and the script console's
    passthrough refuses them (``uiscript.script.sanitise_cyanrip_args``).
    """
    code = ord(ch)
    return code < 0x20 or 0x7F <= code <= 0x9F or ch in _LINE_SEPARATORS


def _has_control_char(text: str) -> bool:
    """True if ``text`` holds a character :func:`is_control_char` names.

    Security/robustness: a NUL truncates a C string (path/argv) and other control
    characters have no business in a path or template — rejecting them keeps a
    crafted or pasted value from doing something surprising downstream.
    """
    return any(is_control_char(ch) for ch in text)


def _allowed_goals() -> frozenset[str]:
    """Valid goal keys: the presets plus the 'custom' sentinel."""
    return frozenset(set(goal_presets.PRESETS) | {goal_presets.GOAL_CUSTOM})


def _segment_text(segment: str) -> tuple[str, bool]:
    """``(the literal text this segment writes into the path, holds a tag token)``.

    Scans left to right the way the translator does, so ``%%`` is one literal
    ``%`` (never the start of a token) and an unknown ``%q`` stays as typed.
    """
    out: list[str] = []
    has_tag = False
    i = 0
    while i < len(segment):
        if segment[i] == "%" and i + 1 < len(segment):
            token = segment[i + 1]
            if token in _KNOWN_TEMPLATE_TOKENS:
                has_tag = True
            else:
                out.append("%" if token == "%" else segment[i : i + 2])
            i += 2
            continue
        out.append(segment[i])
        i += 1
    return "".join(out), has_tag


def _unknown_tokens(template: str) -> list[str]:
    """Return the unknown ``%X`` token letters in ``template`` (deduped, in order).

    ``%%`` is a literal percent (skipped); a trailing bare ``%`` isn't a token.
    """
    unknown: list[str] = []
    seen: set[str] = set()
    i = 0
    n = len(template)
    while i < n:
        if template[i] != "%":
            i += 1
            continue
        if i + 1 >= n:
            break  # trailing bare % — render_preview keeps it literally
        token = template[i + 1]
        if token != "%" and token not in _KNOWN_TEMPLATE_TOKENS and token not in seen:
            seen.add(token)
            unknown.append(token)
        i += 2
    return unknown
