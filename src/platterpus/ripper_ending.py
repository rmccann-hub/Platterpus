# SPDX-License-Identifier: GPL-3.0-only
"""How cyanrip says its run ended, read from its own ``-j`` record (W6).

**Why this exists.** Every rip asks cyanrip for a machine-readable record of the
run (``-j``; ``diagnostics_record.py`` finds it). Since ``a7a631b9`` the records
travel in the report bundle, but the app never READ them, so our status line and
report said how a rip ended from our side's view alone: the exit status of the
process we reaped (the Distrobox wrapper, not cyanrip itself) and whether the user
pressed Cancel. On the 2026-10-04 runs our status line inferred a cancel that the
ripper had recorded for itself. The handshake register lists this as W6, *"ours to
close"* (``docs/cyanrip-handshake.md`` §10).

**The three fields, as the fork publishes them** (its provider contract in our
tree, ``docs/handshake/inbound/artifacts/round-30-lap-09-provider-contract-
gce2e5a6.md``, §P8b's table at lines 1064, 1088 and 1089, and §P8c at 1141-1143):

* ``exit_code`` — int, in every record. **Tri-state, and ``null`` is not 0**: a
  record written from ``atexit`` before the exit status is known says ``null``.
* ``rip.interrupted`` — bool, not in every record: ``rip`` itself can be ``null``
  (a run refused during argument validation never started a rip).
* ``rip.interrupted_by`` — string, observed ``null`` (an uninterrupted run).

The record is recognised by its ``schema`` prefix, ``cyanrip-diagnostics/``, and
never by the number after the slash: §P8a says every change so far has been an
addition, and a consumer that pins one number rejects records it could have read.

**Tri-state throughout.** A record that is absent, unreadable, too large, or not
a cyanrip record answers *not determined* for every field. A field that is
missing or of the wrong type is ``None``, never ``False`` or ``0``.

**Where the record and our own reading disagree, both are said** — never one
quietly preferred (:func:`disagreements`). The record describes the ALBUM pass:
the securing pass's record is written into a temporary folder that is deleted
with it, so it is not read here.

Pure except :func:`read_ending`, which reads one file and never raises. Qt-free.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from platterpus import inbound_text, ripper_exit

log = logging.getLogger(__name__)

#: The schema prefix that identifies a cyanrip diagnostics record (§P8a).
RECORD_SCHEMA_PREFIX: Final[str] = "cyanrip-diagnostics/"

#: A record larger than this is not parsed: JSON cannot be read from half a file.
#: The fork's golden-reference record (round 12 lap 3) is 10,840 bytes.
MAX_RECORD_BYTES: Final[int] = 8 * 1024 * 1024

#: ``interrupted_by`` is a short label (``SIGTERM``). Longer text is cut and the
#: cut is counted, because a silent truncation reads as completeness.
MAX_LABEL_CHARS: Final[int] = 120

#: What the reader found. Every state but ``read`` leaves each field ``None``.
STATE_READ: Final[str] = "read"
STATE_NOT_REQUESTED: Final[str] = "not_requested"
STATE_ABSENT: Final[str] = "absent"
STATE_UNREADABLE: Final[str] = "unreadable"
STATE_UNRECOGNISED: Final[str] = "unrecognised"
#: The report writer was given no reading at all (an in-progress snapshot).
STATE_NOT_READ: Final[str] = "not_read"

#: Which pass the record describes, said in the report rather than left implied.
DESCRIBES: Final[str] = "album pass"

_STATE_PHRASE: Final[dict[str, str]] = {
    STATE_NOT_REQUESTED: "no record was named for this rip",
    STATE_ABSENT: "none was found where cyanrip was told to write it",
    STATE_UNREADABLE: "it could not be read",
    STATE_UNRECOGNISED: "the file is not a cyanrip diagnostics record",
    STATE_NOT_READ: "it was not read",
}


@dataclass(frozen=True)
class RipperEnding:
    """How cyanrip's own record says the run ended. ``None`` is "not determined"."""

    state: str
    detail: str = ""
    exit_code: int | None = None
    interrupted: bool | None = None
    interrupted_by: str | None = None


def parse_ending(text: str) -> RipperEnding:
    """Read the three fields out of a record's text. Pure; never raises."""
    try:
        data = json.loads(text)
    except (ValueError, RecursionError) as exc:
        return RipperEnding(STATE_UNREADABLE, f"not valid JSON: {exc}")
    if not isinstance(data, Mapping):
        return RipperEnding(STATE_UNRECOGNISED, "the record is not a JSON object")
    schema = data.get("schema")
    if not isinstance(schema, str) or not schema.startswith(RECORD_SCHEMA_PREFIX):
        return RipperEnding(
            STATE_UNRECOGNISED,
            f"its schema is {_label(schema)!r}, not {RECORD_SCHEMA_PREFIX}…",
        )
    rip = data.get("rip")
    rip = rip if isinstance(rip, Mapping) else {}  # `rip` is null for a refused run
    by = rip.get("interrupted_by")
    return RipperEnding(
        STATE_READ,
        exit_code=_int(data.get("exit_code")),
        interrupted=_bool(rip.get("interrupted")),
        interrupted_by=_label(by) if isinstance(by, str) else None,
    )


def read_ending(path: Path | None) -> RipperEnding:
    """Read the record at ``path``. Never raises.

    ``None`` is a rip that named no record: its argv had no ``-j``, or the ripper
    was never spawned so there is no argv to read. Runs on the rip worker's thread:
    a file read is not GUI-thread work, however small it usually is.
    """
    if path is None:
        return RipperEnding(STATE_NOT_REQUESTED)
    try:
        size = path.stat().st_size
        if size > MAX_RECORD_BYTES:
            return RipperEnding(
                STATE_UNREADABLE,
                f"{path.name} is {size} bytes, over the {MAX_RECORD_BYTES}-byte bound",
            )
        text = path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return RipperEnding(STATE_ABSENT, str(path))
    except OSError as exc:
        log.warning("could not read cyanrip's -j record %s: %r", path, exc)
        return RipperEnding(STATE_UNREADABLE, f"{path.name}: {exc}")
    ending = parse_ending(text)
    if ending.state != STATE_READ:
        log.warning("-j record %s: %s (%s)", path, ending.state, ending.detail)
    return ending


def disagreements(
    ending: RipperEnding,
    *,
    status: str,
    our_exit_code: int | None,
    securing_pass_started: bool,
) -> list[str]:
    """Where cyanrip's record and our own reading of the rip disagree. Pure.

    ``status`` is ours (``success`` / ``failed`` / ``cancelled``), and
    ``our_exit_code`` the album pass's as we reaped it. Two questions, each said
    in a sentence naming both answers, and only when both sides determined one:

    * **Did the album pass finish?** We say finished and the record says
      interrupted; or we say cancelled and the record says not interrupted, while
      no securing pass ran (a cancel during the securing pass leaves the album
      pass's record truthfully uninterrupted).
    * **How did it exit?** Our reaped code and the record's differ, except on a
      rip we cancelled, where we signalled the Distrobox wrapper and its death by
      that signal is expected beside cyanrip's own exit.
    """
    if ending.state != STATE_READ:
        return []
    found: list[str] = []
    if status == "success" and ending.interrupted is True:
        found.append(
            "Platterpus recorded the rip as finished, but cyanrip's own record of "
            f"the album pass says it was interrupted{_by(ending)}"
        )
    ran_to_the_end = ending.interrupted is False and not securing_pass_started
    if status == "cancelled" and ran_to_the_end:
        found.append(
            "Platterpus recorded the rip as cancelled, but cyanrip's own record of "
            "the album pass says it was not interrupted"
        )
    if (
        status != "cancelled"
        and our_exit_code is not None
        and ending.exit_code is not None
        and our_exit_code != ending.exit_code
    ):
        found.append(
            f"the album pass's process exited {_exit(our_exit_code)} as Platterpus "
            f"reaped it, but cyanrip's own record says it exited {ending.exit_code}"
        )
    return found


def describe(ending: RipperEnding) -> str:
    """One sentence saying what the record says, tri-state. Pure."""
    if ending.state != STATE_READ:
        why = _STATE_PHRASE.get(ending.state, ending.state)
        return f"cyanrip's own record of how it ended: not determined ({why})."
    code = (
        f"exit {ending.exit_code}"
        if ending.exit_code is not None
        else "exit status not recorded"
    )
    if ending.interrupted is True:
        return f"cyanrip's own record: interrupted{_by(ending)} ({code})."
    if ending.interrupted is False:
        return f"cyanrip's own record: not interrupted ({code})."
    return f"cyanrip's own record: {code}; whether it was interrupted is not recorded."


def report_block(
    ending: RipperEnding | None,
    *,
    status: str,
    our_exit_code: int | None,
    securing_pass_started: bool,
) -> dict[str, object]:
    """The report's ``outcome.ripper_record`` block (schema v32). Pure."""
    reading = ending if ending is not None else RipperEnding(STATE_NOT_READ)
    return {
        "describes": DESCRIBES,
        "state": reading.state,
        "detail": reading.detail or None,
        "exit_code": reading.exit_code,
        "interrupted": reading.interrupted,
        "interrupted_by": reading.interrupted_by,
        "disagreements": disagreements(
            reading,
            status=status,
            our_exit_code=our_exit_code,
            securing_pass_started=securing_pass_started,
        ),
    }


def ending_from_block(block: object) -> RipperEnding | None:
    """A report's ``ripper_record`` block back as a reading, or ``None``. Pure."""
    if not isinstance(block, Mapping) or not isinstance(block.get("state"), str):
        return None
    by = block.get("interrupted_by")
    return RipperEnding(
        state=str(block["state"]),
        exit_code=_int(block.get("exit_code")),
        interrupted=_bool(block.get("interrupted")),
        interrupted_by=by if isinstance(by, str) else None,
    )


def status_suffix(outcome: object) -> str:
    """What the status line adds about cyanrip's own record. Pure; never raises.

    On a rip that did not succeed, what the record says (or that it is not
    determined). On any rip, each disagreement, marked ``⚠`` (status is never
    colour alone). A successful rip whose record agrees adds nothing.
    """
    if not isinstance(outcome, Mapping):
        return ""
    block = outcome.get("ripper_record")
    ending = ending_from_block(block)
    if ending is None:
        return ""
    parts: list[str] = []
    if outcome.get("status") != "success":
        parts.append(describe(ending))
    found = block.get("disagreements") if isinstance(block, Mapping) else None
    for sentence in found if isinstance(found, list) else ():
        if isinstance(sentence, str) and sentence:
            parts.append(f"⚠ {sentence}.")
    return (" " + " ".join(parts)) if parts else ""


def _int(value: object) -> int | None:
    """An exit status, or ``None``: a bool is not one, and null is not 0."""
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _bool(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _by(ending: RipperEnding) -> str:
    return f" by {ending.interrupted_by}" if ending.interrupted_by else ""


def _exit(code: int) -> str:
    number = ripper_exit.signal_of(code)
    return f"{code} ({ripper_exit.signal_label(number)})" if number else str(code)


def _label(value: object) -> str:
    """A short, screened label from the record: control characters escaped, the
    length bounded, and any cut counted."""
    text = inbound_text.screen_line(str(value)).text
    if len(text) <= MAX_LABEL_CHARS:
        return text
    cut = len(text) - MAX_LABEL_CHARS
    return f"{text[:MAX_LABEL_CHARS]}… [{cut} more characters]"
