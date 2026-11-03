# SPDX-License-Identifier: GPL-3.0-only
"""The securing pass's two exit statuses, each named for the process it describes.

**Why this exists (TASKS R64; the plan of record, Appendix H §3).** Disc 1 of the
2026-10-21 Full run was stopped during its securing pass. Its report said
``securing_pass_exit_code: 1``; the pass's own ``--diagnostics`` record, kept in
the same bundle, said ``exit_code: 143``. Both were true, and nothing said so:

* **the wrapper's** — the exit status Platterpus reaped from the process it
  spawned, the host-exported ``~/.local/bin/cyanrip``, which enters the
  Distrobox container (Critical rule #3). That is ``securing_pass_exit_code``.
* **the reader's** — cyanrip's own, inside the container, as its record wrote it
  (``exit_code`` in the record, :mod:`platterpus.ripper_ending`). 143 is 128 +
  15: cyanrip ended by SIGTERM.

The two can differ for ordinary reasons (a wrapper reports its own status, not
always its child's), so a difference is recorded and named, never resolved by
quietly preferring one. The album pass's pair already sits apart
(``outcome.ripper_exit_code`` beside ``outcome.ripper_record.exit_code``); this
gives the securing pass the same, as ``outcome.securing_pass_exit_codes``
(schema v42).

Tri-state throughout: a code that was never reaped, a record that was missing or
unreadable, each is ``None`` and never 0, and ``agree`` is ``None`` unless both
codes are known. Pure, Qt-free, never raises.
"""

from __future__ import annotations

from typing import Final, TypedDict

from platterpus import ripper_exit
from platterpus.ripper_ending import STATE_READ, RipperEnding

#: What ``wrapper`` names, written into the block so a reader of the JSON alone
#: knows which process each number came from.
WRAPPER_IS: Final[str] = (
    "the process Platterpus spawned and reaped: the host-exported wrapper "
    "~/.local/bin/cyanrip, which runs cyanrip inside the container"
)
#: What ``reader`` names.
READER_IS: Final[str] = (
    "cyanrip itself, inside the container, as its own --diagnostics record wrote it"
)


class SecuringExitsBlock(TypedDict):
    """``outcome.securing_pass_exit_codes`` (schema v42)."""

    wrapper: int | None
    wrapper_is: str
    reader: int | None
    reader_is: str
    #: Whether the reader's record was read (`ripper_ending` states: `read`,
    #: `absent`, `unreadable`, `unrecognised`, `not_requested`, `not_read`).
    reader_record_state: str
    agree: bool | None
    sentence: str


def _code(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _said(code: int | None) -> str:
    """``143 (SIGTERM)``, ``1``, or "not known"."""
    if code is None:
        return "not known"
    number = ripper_exit.signal_of(code)
    return f"{code} ({ripper_exit.signal_label(number)})" if number else str(code)


def exits_block(
    *, started: bool, wrapper_code: object, ending: object
) -> SecuringExitsBlock | None:
    """The named pair, or ``None`` when no securing pass ripper was spawned.

    ``wrapper_code`` is the status we reaped (``securing_pass_exit_code``) and
    ``ending`` the reader's record as :func:`~platterpus.ripper_ending.read_ending`
    read it, or ``None`` when nothing read it. Never raises.
    """
    if not started:
        return None
    wrapper = _code(wrapper_code)
    reading = ending if isinstance(ending, RipperEnding) else None
    state = reading.state if reading is not None else "not_read"
    reader = reading.exit_code if reading is not None and state == STATE_READ else None
    agree = None if wrapper is None or reader is None else wrapper == reader
    sentence = (
        f"the wrapper Platterpus reaped exited {_said(wrapper)}; cyanrip's own "
        f"record says it exited {_said(reader)}"
    )
    if agree is False:
        sentence += ": they differ, and each is the named process's own account"
    return {
        "wrapper": wrapper,
        "wrapper_is": WRAPPER_IS,
        "reader": reader,
        "reader_is": READER_IS,
        "reader_record_state": state,
        "agree": agree,
        "sentence": sentence,
    }
