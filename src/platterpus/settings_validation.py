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
from dataclasses import dataclass
from pathlib import Path

from platterpus import goal_presets
from platterpus.config import Config

log = logging.getLogger(__name__)

SEVERITY_ERROR: str = "error"
SEVERITY_WARNING: str = "warning"

# The ``%``-tokens a naming template may use (see naming.py / cyanrip_backend).
# Anything else after a ``%`` (other than ``%%``) is an unknown token — legal to
# type, but almost always a typo, so it's a WARNING, not an error.
_KNOWN_TEMPLATE_TOKENS: frozenset[str] = frozenset("AadntyY")

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
MP3_QUALITY_MIN: int = 0
MP3_QUALITY_MAX: int = 9

# Enum-valued fields → their allowed values (must match the Settings combos and
# the consumers downstream). Kept here so the validator rejects a bad hand-edit.
_ALLOWED_OUTPUT_FORMATS: frozenset[str] = frozenset({"flac", "wavpack", "mp3", "wav"})
_ALLOWED_COVER_ART: frozenset[str] = frozenset({"", "embed", "file", "complete"})
_ALLOWED_READ_SPEED_MODES: frozenset[str] = frozenset({"auto_ladder", "fixed"})


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
    unexpected failure is logged and treated as "no issue for that check" so the
    rest still run.
    """
    issues: list[ValidationIssue] = []
    try:
        issues += _validate_dir("output_dir", config.output_dir, "Output directory")
        issues += _validate_dir("working_dir", config.working_dir, "Working directory")

        for field_name, label in (
            ("track_template", "Track template"),
            ("disc_template", "Disc template"),
            ("track_template_unknown", "Track template (unknown)"),
            ("disc_template_unknown", "Disc template (unknown)"),
        ):
            issues += _validate_template(field_name, getattr(config, field_name), label)

        issues += _validate_tool_path("metaflac_path", config.metaflac_path, "metaflac")

        issues += _validate_int(
            "read_offset", config.read_offset, OFFSET_MIN, OFFSET_MAX, "Read offset"
        )
        issues += _validate_int(
            "max_retries",
            config.max_retries,
            MAX_RETRIES_MIN,
            MAX_RETRIES_MAX,
            "Max retries",
        )
        issues += _validate_int(
            "secure_rerip_matches",
            config.secure_rerip_matches,
            SECURE_REREP_MIN,
            SECURE_REREP_MAX,
            "Max reads to confirm a shaky track",
        )
        issues += _validate_int(
            "read_speed",
            config.read_speed,
            READ_SPEED_MIN,
            READ_SPEED_MAX,
            "Fixed read speed",
        )
        issues += _validate_int(
            "mp3_vbr_quality",
            config.mp3_vbr_quality,
            MP3_QUALITY_MIN,
            MP3_QUALITY_MAX,
            "MP3 VBR quality",
        )

        issues += _validate_choice(
            "output_format",
            config.output_format,
            _ALLOWED_OUTPUT_FORMATS,
            "Output format",
        )
        issues += _validate_choice(
            "cover_art", config.cover_art, _ALLOWED_COVER_ART, "Cover art"
        )
        issues += _validate_choice(
            "read_speed_mode",
            config.read_speed_mode,
            _ALLOWED_READ_SPEED_MODES,
            "Read speed mode",
        )
        issues += _validate_choice(
            "rip_goal", config.rip_goal, _allowed_goals(), "Goal"
        )

        # Every remaining field is a boolean toggle or bookkeeping value. We
        # validate their TYPE too (a hand-edited config.toml could put a string
        # where a bool/int belongs) so "cover completely" is literal — every
        # Config field has a rule (the completeness meta-test enforces this).
        for field_name in _BOOL_FIELDS:
            issues += _validate_bool(field_name, getattr(config, field_name))
        issues += _validate_str(
            "integration_declined_path", config.integration_declined_path
        )
        issues += _validate_plain_int("schema_version", config.schema_version)
    except Exception:  # noqa: BLE001 — a validator must never crash the dialog
        log.exception("settings validation raised; returning partial results")
    return issues


# The boolean toggles — validated for type so a corrupt config.toml (a string
# where a bool belongs) is caught, not silently coerced.
_BOOL_FIELDS: tuple[str, ...] = (
    "override_read_offset",
    "auto_launch_picard",
    "auto_eject_after_rip",
    "drive_setup_prompted",
    "host_setup_prompted",
    "appimage_integration_prompted",
    "debug_logging",
    "secure_rerip_dynamic",
    "ctdb_verify_after_rip",
    "verify_flac_after_rip",
    "recompress_flac_after_rip",
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
            "working_dir",
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
            "integration_declined_path",
            "schema_version",
        }
        | set(_BOOL_FIELDS)
    )


def errors_only(issues: list[ValidationIssue]) -> list[ValidationIssue]:
    """The blocking subset — issues that must be fixed before saving."""
    return [i for i in issues if i.is_error()]


def log_issues(issues: list[ValidationIssue]) -> None:
    """Record validation issues to the log file (CLAUDE.md: log input failures).

    Errors log at WARNING (they blocked a save the user attempted); warnings log
    at INFO. Called by the dialog when the user tries to save with issues, so a
    bug report's log shows exactly what was rejected and why.
    """
    for issue in issues:
        if issue.is_error():
            log.warning(
                "settings validation error: %s — %s", issue.field, issue.message
            )
        else:
            log.info("settings validation warning: %s — %s", issue.field, issue.message)


# --- Per-field validators ----------------------------------------------------


def _validate_dir(field: str, value: str, label: str) -> list[ValidationIssue]:
    """A rip output/working directory: absolute, legal, and writable-or-creatable.

    We don't require the folder to *exist* (the rip creates it) — but we do
    require that it *could* be created: an absolute path whose nearest existing
    ancestor is a writable directory. The writability probe is best-effort; if
    we genuinely can't tell, we don't manufacture an error.
    """
    text = (value or "").strip()
    if not text:
        return [ValidationIssue(field, f"{label} cannot be empty.")]
    if _has_control_char(text):
        return [ValidationIssue(field, f"{label} contains an illegal character.")]
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
                return [ValidationIssue(field, f"{label} isn’t writable: {text}")]
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
                    f"{label} can’t be created — “{ancestor}” isn’t writable.",
                )
            ]
    except OSError:
        # A permission error or odd filesystem while probing — don't block the
        # user over something we couldn't determine; the rip will surface a real
        # error if it truly can't write.
        log.debug("dir validation probe failed for %s=%s", field, text, exc_info=True)
    return []


def _validate_template(field: str, value: str, label: str) -> list[ValidationIssue]:
    """A naming template: non-empty, relative, legal chars, known tokens, renders.

    The template nests folders with its own ``/`` separators, so a leading ``/``
    (an absolute path) is an error — it would try to write to the filesystem root
    instead of under the output directory. Unknown ``%``-tokens are a warning
    (typo-catching), not an error, matching the live preview's pass-through.
    """
    from platterpus import naming

    issues: list[ValidationIssue] = []
    text = value or ""
    if not text.strip():
        return [ValidationIssue(field, f"{label} cannot be empty.")]
    if _has_control_char(text):
        return [ValidationIssue(field, f"{label} contains an illegal character.")]
    if text.startswith("/"):
        issues.append(
            ValidationIssue(
                field,
                f"{label} must be a relative path (no leading “/”) — it nests "
                "under the output directory.",
            )
        )
    # Security: a template must never climb ABOVE the output directory. A ".."
    # segment would let a crafted/typo'd template write outside the chosen folder
    # (path traversal) — reject it outright. (We split on "/" because the template
    # separator is always "/", regardless of the host OS.)
    if ".." in text.split("/"):
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
                "%Y (a literal % is written %%).",
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


def _validate_tool_path(field: str, value: str, tool: str) -> list[ValidationIssue]:
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
    text = (value or "").strip()
    if not text:
        return [
            ValidationIssue(
                field, f"{tool} path cannot be empty (use the bare name “{tool}”)."
            )
        ]
    if "/" in text:
        p = Path(text).expanduser()
        if not p.exists():
            return [ValidationIssue(field, f"No {tool} executable at: {text}")]
        if p.is_dir() or not os.access(p, os.X_OK):
            return [ValidationIssue(field, f"{text} is not an executable file.")]
    return []


def _validate_int(
    field: str, value: object, lo: int, hi: int, label: str
) -> list[ValidationIssue]:
    """A whole-number field within [lo, hi]. A bool is NOT an int here."""
    if isinstance(value, bool) or not isinstance(value, int):
        return [ValidationIssue(field, f"{label} must be a whole number.")]
    if value < lo or value > hi:
        return [ValidationIssue(field, f"{label} must be between {lo} and {hi}.")]
    return []


def _validate_choice(
    field: str, value: object, allowed: frozenset[str], label: str
) -> list[ValidationIssue]:
    """A field that must be one of a fixed set of string values."""
    if value not in allowed:
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


def _has_control_char(text: str) -> bool:
    """True if ``text`` holds a NUL or other C0 control character.

    Security/robustness: a NUL truncates a C string (path/argv) and other control
    characters have no business in a path or template — rejecting them keeps a
    crafted or pasted value from doing something surprising downstream.
    """
    return any(ord(ch) < 0x20 or ch == "\x7f" for ch in text)


def _allowed_goals() -> frozenset[str]:
    """Valid goal keys: the presets plus the 'custom' sentinel."""
    return frozenset(set(goal_presets.PRESETS) | {goal_presets.GOAL_CUSTOM})


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
