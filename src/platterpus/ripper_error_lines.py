# SPDX-License-Identifier: GPL-3.0-only
"""Which lines of the ripper's output are diagnostics: one matcher, two callers.

**Why this is its own module** (2026-10-21, the owner's known-fixes list, item 3).
The matcher below used to live inside the rip worker, where it read each line
cyanrip streamed and surfaced the first fatal as the failure hint. The log
parser needs the same question answered of a FINISHED log: cyanrip can print an
error line (the fork's round-20 example is ``Error writing trailer: File too
large!``) six lines above a ``Ripping errors: 0`` summary, and nothing compared
the two. A second, hand-written pattern in the parser would be two guesses at
"what does a diagnostic look like", which is the exact failure
:mod:`platterpus.ripper_messages` was built to end. So the matcher moved here,
Qt-free and pure, and both the worker and the parser import it.

The comments below moved with the code unchanged, so their history (and every
measurement behind each prefix) stays beside what it explains.

Pure; no Qt, no I/O. Importing it compiles one regex.
"""

from __future__ import annotations

import logging
import re
from typing import Final

from platterpus.ripper_message_inventory import ALL_FORMATS
from platterpus.ripper_messages import build_matcher

log = logging.getLogger(__name__)

# cyanrip's own fatal-argument / fatal-setup errors, which it prints and then
# exits on. Deliberately narrow: these are the shapes that end a rip before any
# audio is read, so surfacing one verbatim is strictly better than "Rip failed."
# Bounded quantifiers per the never-unbounded rule.
#
# WIDENED 2026-08-02. The fork session enumerated cyanrip's fatal `cyanrip_log`
# call sites and measured that the six prefixes above matched **24 of 45** of
# them. The other 21 printed a precise diagnosis that the user never saw: the
# report's `failure_hint` was null and the window said "Rip failed."
#
# "Deliberately narrow" was the wrong instinct here, and worth naming because it
# is a tempting one. The cost of a MISS is a user staring at "Rip failed" with
# the answer sitting in a buffer we captured and did not read. The cost of a
# FALSE POSITIVE is one extra sentence of the ripper's own words in a hint —
# which is, at worst, mildly confusing, and is shown only on a rip that already
# failed. Those costs are not close, so the pattern is now broad on purpose.
#
# Anchored at line start with a trailing space or end-of-line after each prefix,
# so `Error reading` matches but `No errors` does not, and a track title that
# happens to begin with one of these words cannot match (titles never appear at
# column 0 in cyanrip's output — they are indented inside a Metadata block).
RIPPER_ERROR_PREFIXES: Final[tuple[str, ...]] = (
    "Invalid",
    "Unable to",
    "Missing",
    "No device",
    "No disc",
    "No cover art",
    "No tracks",
    "Error",
    "Errors",
    "Failed",
    "Couldn't",
    "Could not",
    "Cannot",
    # The contraction, and the omission was measurable rather than theoretical.
    # `Cannot`, `Could not` and `Couldn't` were all here; `Can't` was not, and
    # the ripper's P2 table carries `Can't init %s handler!` — a signal-handler
    # setup failure, published since round 7 lap 25 and matched by NOTHING in
    # this file until now. Measured against round 12's contract before adding it:
    # of 296 P2 rows, exactly one has a `Can't`/`Cannot` shape (that one), and
    # widening to `Can't` fires on zero additional P2 lines. It is a *prefix*
    # rather than an inventory row on purpose — the prefixes are the forward
    # tolerance member of the union, and the string is not in P5, which is the
    # provider's authority on failure-path reachability. Inventing a P5 row for
    # it would be us guessing again, which is the mistake this whole subsystem
    # was rebuilt to stop.
    "Can't",
    "Unsupported",
    "Unknown option",
    "Unrecognized",
    "Stopping,",
    "Stopping",
    "Aborting",
    "Drive media",
    "Insufficient",
    "Out of memory",
    "Fatal",
    # Begins with a hyphen, so no word prefix reaches it. The fork's generated
    # inventory (handshake round 4, Appendix 2) has exactly one string our 23
    # prefixes missed, and this is it — independently re-measured on our side
    # at 87/88 before adding this, rather than taken on their word.
    #
    # No trailing space: the boundary below supplies it. With `"-J "` the
    # boundary then has to match the `(` of `-J (only generate...` and does
    # not — which the fixture caught immediately, and reading the prefix list
    # would not have.
    "-J",
    # `.19`'s two `-Z`/`-r` refusals, fatal and new (cyanrip@174a134,
    # PROVIDER-CONTRACT.md: `cyanrip_main.c:2071` and `:2077`, both "control flow").
    # They begin with a hyphen, so no word prefix reaches them. Added while our
    # inventory was still round 28's; `.19`'s contract, filed with the fork's round
    # 30 lap 1, now lists both in P5 too, and this prefix stays so that a later
    # rewording of either keeps being surfaced.
    # Measured before adding: of the 539 table rows in that contract, exactly
    # these two begin with `-Z`. Our own argv check refuses the same pairs before
    # cyanrip starts, so a rip should never reach them; if one does, the user
    # reads cyanrip's sentence rather than a bare "Rip failed." (2026-09-30).
    "-Z",
    # Two more, found on our side while implementing `-c disc/totaldiscs` by
    # reading the fork's `src/cyanrip_main.c` at the pin instead of reading its
    # generated inventory. Both are fatal (`return 1`), both are argument
    # validation and therefore stdout-only (their Q5), and both are ABSENT from
    # the fork's 88-string round-4 inventory:
    #
    #   cyanrip_main.c:1439  "discnumber %i is larger than totaldiscs %i"
    #   cyanrip_main.c:1554  "Cover art already specified for track idx %i!"
    #
    # The reason they are missing is a systematic blind spot, not two typos: in
    # both calls the format string sits on a CONTINUATION LINE, so a generator
    # scanning for a literal on the same line as `cyanrip_log(` cannot see it.
    # A sweep of the fork's whole `src/` for that shape finds exactly these two,
    # which is why the number goes 88 → 90 and not further. Reported as §1 of
    # handshake round 5, with the class rather than only the instances.
    #
    # The first matters immediately: it is the fatal we would hit if the range
    # check on `-c` ever let a bad disc position through, so shipping the flag
    # without surfacing its refusal would be capture-without-surfacing again.
    "discnumber",
    "Cover art already specified",
)

# THE MATCHER IS DERIVED FROM THE RIPPER'S PUBLISHED INVENTORY, not from the
# prefix guesses above — full reasoning in `platterpus.ripper_messages`.
#
# Short version: the prefix list was a *second* guess at "what does a diagnostic
# look like", layered on the fork's own 21-word allowlist, and both shared a blind
# spot. Their control-flow re-derivation took the inventory from 88 strings to
# 104, and our pattern missed **all 13** matchable strings the allowlist had
# hidden — including `Offset is unset! To continue with an offset of 0, run with
# -s 0!` and `Device does not support changing speeds!`, which are ordinary
# hardware failures, not exotica. Every one rendered as a bare "Rip failed."
#
# Our 90/90 standing test stayed green throughout, because the fixture it
# asserted against had inherited their filter's blind spot: it measured their
# allowlist, not the ripper's behaviour. That is CLAUDE.md's
# verify-the-behaviour-not-the-description rule biting one level below where it
# was written. See docs/testing.md §5.ab.
#
# The prefixes are KEPT, as union members and nothing more. The inventory
# describes one pin; a newer build will say things it does not list, and the
# prefixes catch the common shapes of those. Inventory for completeness, prefixes
# for forward tolerance — neither alone was enough, which is the whole lesson.
#
# AND THE INVENTORY GOING STALE IS THE SAME BUG A THIRD TIME (2026-08-21). It sat
# at round 6's 115 strings while rounds 7-11 published 117, 120 and then 130; the
# 10 `genopt.h` diagnostics round 9 added include two that matched NOTHING here —
# `Programming error, incorrect type for: %s` and
# `Too many values for argument "%s" (at most %i)` — so either one was a bare
# "Rip failed." The forward-tolerance prefixes carried the other eight, which is
# exactly why nobody noticed: a fallback that half-works hides the gap it is
# filling. Now round 12's 128, and
# `tests/test_ripper_error_surfacing.py::test_the_inventory_is_not_behind_the_newest_published_contract`
# fails when the newest inbound contract publishes a string we do not carry.
_MATCHER: Final[tuple[re.Pattern[str], list[str]]] = build_matcher(
    list(ALL_FORMATS), extra_prefixes=RIPPER_ERROR_PREFIXES
)
#: The compiled matcher: a line is a ripper diagnostic when this matches it.
RIPPER_ERROR_RE: Final[re.Pattern[str]] = _MATCHER[0]
#: The published formats too generic to pattern (see the debug line below).
UNMATCHABLE_RIPPER_FORMATS: Final[list[str]] = _MATCHER[1]

# Formats too generic to pattern — a bare `%s` would match every line of output,
# turning every progress redraw into a fatal-error report. Named and counted
# rather than dropped, because "we cannot pattern this" and "this does not exist"
# are different facts and only the second one hides bugs.
if UNMATCHABLE_RIPPER_FORMATS:
    log.debug(
        "ripper diagnostics: %d of %d published formats carry too little literal "
        "text to pattern, and are covered only by the prefix fallback: %s",
        len(UNMATCHABLE_RIPPER_FORMATS),
        len(ALL_FORMATS),
        UNMATCHABLE_RIPPER_FORMATS,
    )
