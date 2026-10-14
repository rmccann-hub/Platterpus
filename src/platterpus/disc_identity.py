"""Was the disc that was ripped the disc whose tags were looked up?

**Why this exists** (TASKS P1 #1, the top archival risk on the list). The tags
written into a rip come from a MusicBrainz release, and that release was found by
the disc ID read off the disc on screen when the user scanned it. The rip itself
reads whatever disc is in the drive when it starts. Nothing compared the two, so a
disc swapped after the scan — one the drive poller missed — would archive one
album's audio under another album's tags. AccurateRip cannot catch it: cyanrip
checks the audio against the TOC of the disc it actually read, so the wrong album
can verify "bit-perfect" and still be filed under the wrong name. That is the
north-star failure (good music, good tags, good everything), and the cheapest
check that catches it is comparing two strings we already have.

**Like with like, from one program.** Both IDs are MusicBrainz disc IDs that
cyanrip computes from the TOC (``cyanrip@200530e:src/discid.c:28-71``: SHA-1,
base64, ``/+=`` replaced by ``_.-``), printed on a
``DiscID:`` line: the EXPECTED one by the pre-rip scan (``cyanrip -I -N``, parsed
by ``parsers/cyanrip_info.py``), which is the ID the MusicBrainz lookup was made
with; the RIPPED one by the rip's own log (``parsers/cyanrip_log.py``). The same
binary, the same algorithm, the same drive, so a difference is a different TOC,
not a different method.

**Tri-state, and the third state is not a pass.** ``match`` and ``mismatch`` are
claims; ``not_determined`` means one side is absent or is not shaped like a
MusicBrainz disc ID, and it is NEITHER. An unparseable value is never read as a
mismatch, because an alarm a malformed line can trigger is one users learn to
ignore; and it is never read as a match, because "we could not check" is not
"it checked out".

**What a mismatch does to the rip.** It is an ARCHIVAL defect by the project's
own severity rule (``docs/testing.md`` → *Acceptance severity*, the maintainer's
ruling of 2026-08-26: "cd accuracy and provenance … for archive level records"
are archival, and which album a rip IS is its provenance), so the rip must not
read as clean anywhere: the trust headline is downgraded with the reason (the
same downgrade the window applies, through ``verdict.apply_downgrades``), the
report carries an ``error`` issue, the album audit a ``warn`` finding, and the
app log an error line. It does not delete or move anything: the audio may be a
perfect rip of the disc that was really in the drive, and only the person
holding both discs can say which album it is.

Pure, Qt-free and never raises: every input is treated as external.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final, TypedDict

#: The three answers. Strings, not an enum, because they are written into the
#: JSON report and read back by the audit from reports of any age.
IDENTITY_MATCH: Final[str] = "match"
IDENTITY_MISMATCH: Final[str] = "mismatch"
IDENTITY_NOT_DETERMINED: Final[str] = "not_determined"

#: A MusicBrainz disc ID: the SHA-1 of the TOC (20 bytes) in base64, 28
#: characters, with ``+``, ``/`` and ``=`` replaced by ``.``, ``_`` and ``-``. A
#: 20-byte digest always ends in one pad, so the last character is always ``-``.
#: (``cyanrip@200530e:src/discid.c:61-71``; cyanrip's own value on the reference
#: disc is ``pNtImOkdBm9RMBIalzx0w9cfsYY-``.)
MB_DISC_ID: Final[re.Pattern[str]] = re.compile(r"\A[A-Za-z0-9._]{27}-\Z")

#: How much of a malformed value a sentence may quote. Inbound text is bounded
#: (Critical rule #12): a log line can be any length.
_QUOTE_LIMIT: Final[int] = 40


class DiscIdentityBlock(TypedDict):
    """The report's ``disc.identity_check`` (schema v34)."""

    status: str
    #: The disc ID the MusicBrainz lookup was made with (the pre-rip scan's).
    expected: str | None
    #: The disc ID the rip's own log reports.
    ripped: str | None
    detail: str


@dataclass(frozen=True)
class DiscIdentity:
    """The answer, both IDs as they were judged, and a sentence a person reads."""

    status: str
    expected: str | None
    ripped: str | None
    detail: str

    @property
    def downgrade_reason(self) -> str:
        """The clause the trust headline gains on a mismatch; ``""`` otherwise."""
        if self.status != IDENTITY_MISMATCH:
            return ""
        return (
            f"the disc ripped (disc ID {self.ripped}) is NOT the disc these tags "
            f"were looked up for ({self.expected}), so the tags may name another "
            "album"
        )

    def block(self) -> DiscIdentityBlock:
        """This answer as the report writes it."""
        return {
            "status": self.status,
            "expected": self.expected,
            "ripped": self.ripped,
            "detail": self.detail,
        }


def _judge(value: object) -> tuple[str | None, str]:
    """``(usable ID or None, why not)``. Never raises."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None, "absent"
    if not isinstance(value, str):
        return None, f"not text ({type(value).__name__})"
    text = value.strip()
    if MB_DISC_ID.match(text):
        return text, ""
    quoted = text[:_QUOTE_LIMIT] + ("…" if len(text) > _QUOTE_LIMIT else "")
    return None, f"{quoted!r} is not shaped like a MusicBrainz disc ID"


def check_disc_identity(expected: object, ripped: object) -> DiscIdentity:
    """Compare the looked-up disc ID with the ripped one. Never raises.

    ``expected`` is the disc ID the release lookup was made with, ``ripped`` the
    one the rip's log reports. Typed ``object`` because both come from outside
    the code (a parsed log, a JSON report of any age).
    """
    want, want_why = _judge(expected)
    got, got_why = _judge(ripped)
    if want is None or got is None:
        reasons = []
        if want is None:
            reasons.append(f"the disc ID the tags were looked up for is {want_why}")
        if got is None:
            reasons.append(f"the disc ID in the rip's log is {got_why}")
        return DiscIdentity(
            status=IDENTITY_NOT_DETERMINED,
            expected=want,
            ripped=got,
            detail=(
                "not determined whether the disc ripped is the disc these tags "
                f"were looked up for: {'; '.join(reasons)}. This is not a pass."
            ),
        )
    if want == got:
        return DiscIdentity(
            status=IDENTITY_MATCH,
            expected=want,
            ripped=got,
            detail=(
                f"the disc ripped is the disc these tags were looked up for "
                f"(disc ID {got})"
            ),
        )
    return DiscIdentity(
        status=IDENTITY_MISMATCH,
        expected=want,
        ripped=got,
        detail=(
            f"WRONG DISC? The disc ripped has disc ID {got}, but these tags were "
            f"looked up for disc ID {want}. A disc changed between the scan and "
            "the rip, so the audio may be a different album from the one its tags "
            "name. Check the disc, then rescan and rip again."
        ),
    )
