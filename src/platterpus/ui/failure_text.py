# SPDX-License-Identifier: GPL-3.0-only
"""The one place that writes *"and here is where to look next."*

**Why this module exists.** An audit of every modal failure report (2026-08-04)
found ~20 that say *"see the log"*, *"see the log for details"* or *"send us the
log"* — and **name no path**. Two others named one: a typed-out
``~/.local/share/…/log.txt`` literal, which is simply wrong whenever
``XDG_DATA_HOME`` is set — and a path the user does not have is worse than no path
at all, because they conclude the log does not exist.

The failure is not that twenty authors forgot. It is that there was nothing to
call. Twenty hand-written sentences are twenty chances to drift, and the two that
tried hardest — by actually naming a file — are the two that got it wrong. So the
sentence lives here, once, built from :data:`platterpus.paths.LOG_PATH`, and
``tests/test_failure_surfaces.py`` sweeps the UI tree for anyone who writes their
own instead.

Keep these short. They are appended to a message that has already said what went
wrong; their whole job is to answer *"what do I do with this?"*
"""

from __future__ import annotations

from platterpus.paths import LOG_PATH

#: Appended to a failure message so the user can find the evidence. Names the real
#: path, resolved at import through ``paths``, so it is correct under a relocated
#: ``XDG_DATA_HOME`` / a sandbox.
LOG_POINTER: str = (
    f"Full details, including what each tool reported, are in:\n{LOG_PATH}"
)

#: For a message that is already pointing the user at a bug report.
BUG_REPORT_POINTER: str = (
    f"Please attach this file to a bug report — it carries the exact commands that "
    f"ran and everything they printed:\n{LOG_PATH}"
)

#: For a *rip* failure, where a per-album report exists as well as the app log.
#: Named separately because the album folder is the more useful of the two and a
#: user who only reads one should read that one.
RIP_REPORT_POINTER: str = (
    "A `.platterpus.json` report was written in the album folder — it embeds the "
    "ripper's own output and this session's debug log. The app log has the same "
    f"detail plus everything before the rip:\n{LOG_PATH}"
)


def with_log_pointer(message: str) -> str:
    """``message`` followed by the log pointer, separated by a blank line.

    Idempotent-ish by construction rather than by checking: if a caller has already
    named the path, adding it twice would be noise — but a *check* for that would be
    a substring match on a path, which is exactly the sort of clever guess this
    project avoids. Callers append once; the sweep test is what keeps them honest.
    """
    text = message.rstrip()
    return f"{text}\n\n{LOG_POINTER}" if text else LOG_POINTER


__all__ = [
    "BUG_REPORT_POINTER",
    "LOG_POINTER",
    "RIP_REPORT_POINTER",
    "with_log_pointer",
]
