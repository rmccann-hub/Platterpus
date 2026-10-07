#!/usr/bin/env python3
"""Pack the files an exchange needs into ONE file the operator sends.

**One file per exchange.** The operator's rule, 2026-08-15: *"there should only be
one file moving forward, unless the second is a script file to run."* The
correspondence is relayed by hand between two repositories, and every extra
attachment is another thing to lose — round 8 lost fifteen laps that way, in both
directions, while both projects' gates reported healthy.

**Not a merged file and not a lap.** Each part goes in as exact bytes between
column-0 delimiters with its own SHA-256, so the receiver splits it back into the
originals and can *prove* they are the originals. A merged round file would be a
falsified record; this is an envelope around files that stay intact.

**Why it exists again after being deleted.** We built one, it was counted as a lap
by our own round digest and read as a misfiled lap by our naming sweep, and we
deleted it — calling that the stronger fix. cyanrip disagreed in round 9 lap 3 §B1
and was right: *"deleting the instance removed your exposure; the rule removed
everyone's."* The rule is now protocol v4 §5a — a file declaring
`HANDSHAKE-ROUND`, `HANDSHAKE-LAP` or `HANDSHAKE-FROM` more than once is ambiguous
and therefore not a lap — so an envelope is excluded **by construction** on both
sides. :func:`assert_not_a_lap` checks that property on this file's own output
*before writing it*, so an envelope a conforming enumerator would misread is never
produced.

Built from cyanrip's published description rather than their `tools/make-envelope.py`,
and the two are mutually splittable: we split their round-9 envelope with the
reader they published and all ten parts verified.

**It never writes into this repository** (2026-10-06). Laps travel by git since
2026-09-13 (`CLAUDE.md` Critical rule #12), so an envelope is only a hand-carry copy
of files `main` already holds. Written into `docs/handshake/outbound/`, 44 piled up
beside the laps they carried, each reading as one lap under two names; they were
retired, with their provenance in `docs/handshake/README.md` → *Retired transport
envelopes*. Writing now needs `--out DIR` outside the working tree, and
`tests/test_handshake_file_naming.py` refuses a committed one by its content.

Usage::

    python scripts/emit_envelope.py --check                # build + verify, write nothing
    python scripts/emit_envelope.py --out DIR              # write it into DIR
    python scripts/emit_envelope.py --split FILE --into DIR  # unpack a received one
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT: Path = Path(__file__).resolve().parent.parent
HANDSHAKE_DIR: Path = REPO_ROOT / "docs" / "handshake"

#: What this exchange carries, in reading order. Listed explicitly rather than
#: globbed: sending is a deliberate act, and a glob would silently ship whatever
#: happened to land in the directory.
#:
#: **This file is the OFFERED packaging of the current lap, not a record of what
#: was sent.** The record of what was sent is `tests/test_sent_laps_are_immutable.py`,
#: because a send is an act by the operator and this generator cannot observe it.
#: Keeping the two straight is not pedantry: round 9 lap 6 went out bare while this
#: envelope sat in `outbound/` packing lap 6 *and* lap 2, and the lap's own prose
#: then said both that it travelled in an envelope (§B) and that it travelled bare
#: (§E). One artifact implying a send that did not happen was half of that
#: contradiction — see lap 8 §A2.
#: `PARTS[0]` is the OPERATIVE lap — `lead_identity()` names the envelope after it.
#: Part 2 is `src/platterpus/rig_scripts/fullacceptance.txt`, the acceptance script
#: itself (it moved into the package on 2026-08-28 so the app can open it).
#: Round 14's only close condition is a hardware pass, the maintainer asked that the
#: fork be given *the plan and the script* to amend rather than a description of
#: them, and lap 2 quotes the file's sha256 — so the file has to travel or that
#: quote is unverifiable. It is NOT a lap and carries no wire headers, so it cannot
#: be miscounted; `assert_not_a_lap` checks that property on the envelope before
#: writing it.
#:
#: **Round 15 lap 15 travels ALONE, and dropping part 2 is deliberate.** The
#: acceptance script rode along for laps 13 and earlier because round 15's close
#: condition was a hardware pass and lap 2 quoted the file's sha256 — the quote is
#: unverifiable if the file does not travel. That round is closed and this lap
#: quotes no such file, so carrying it again would ship an artifact nothing in the
#: lap references. An envelope's contents are a claim about what the lap needs.
PARTS: tuple[Path, ...] = (HANDSHAKE_DIR / "outbound" / "round-31-lap-02.md",)

# WHY IT MOVED TO ROUND-31 LAP 2 (2026-10-07).
#
# **Our first lap of round 31**: `OPEN`, answering their E1-E9 and carrying the
# §6b override for v0.7.101. It replaces round 30 lap 6 (`OPEN`, amending the v7
# texts), which led until round 31 opened. Released on the operator's word.

# WHY IT MOVED TO ROUND-30 LAP 4 (2026-09-30).
#
# **Our second lap of round 30**: `OPEN`, our reading of the Full run on `.19`,
# D1-D10 answered and our operator's O1-O4 rulings. Released on the operator's
# word, so it travels alone, as lap 2 did.

# WHY IT MOVED TO ROUND-30 LAP 2 (2026-09-30).
#
# **Our first lap of round 30**: `OPEN`, answering their lap 1, questioning it, and
# carrying the operator's §6b override for v0.6.65. Released on the operator's
# word, so it travels alone, like round 29's lap 2 before it.

# WHY IT MOVED TO ROUND-29 LAP 4 (2026-09-29).
#
# **Our closing lap of round 29**: `GO` on `51cc789` from the Full run on 0.6.63,
# against their lap 3 `GO`, released on the operator's word. It travels alone: their
# lap 3 has read lap 2, so carrying it again would ship a file nothing in lap 4 needs.

# WHY IT MOVED TO ROUND-29 LAP 2 (2026-09-28).
#
# **Our first lap of round 29**: `OPEN`, answering their lap 1 and carrying the
# operator's §6b override for v0.6.63. Released on the operator's word, so it
# travels alone, like lap 9 before it.

# WHY IT MOVED TO ROUND-28 LAP 9 (2026-09-28), AND WHY IT TRAVELS ALONE.
#
# **Our closing lap of round 28**: `GO` on `e0471f4` from the Full run on 0.6.61,
# against their lap 8 `GO`, released on the operator's word. Lap 7 does not ride
# along: it was released with lap 6 and their lap 8 has read both, so carrying it
# again would ship a file nothing in lap 9 needs.

# WHY IT MOVED TO ROUND-28 LAPS 6 AND 7 (2026-09-28).
#
# **Two laps released together on the operator's word**: lap 6 checks their lap
# 5, declares protocol 6 and carries the §6b override for v0.6.62 and the R1
# override moving the Full run to it; lap 7 answers the operator's proposal, every
# item for round 29. Lap 6 leads because it is the one round 28 turns on.

# WHY IT MOVED TO ROUND-28 LAP 4 (2026-09-27).
#
# **Our second lap of round 28**: `OPEN`, acting on their lap 3 before the
# Full run: `.17`'s provider contract filed, `Partial files:` claimed, LSL 2
# read by our checker. Moved once the lap was RELEASED.

# WHY IT MOVED TO ROUND-28 LAP 2 (2026-09-27).
#
# **Our first lap of round 28**: `OPEN`, accepting their lap 1's close
# conditions, correcting our round 27 lap 5's claim that 0.6.61 needed no §6b
# override, and carrying that override. Moved once the lap was RELEASED.

# WHY IT MOVED TO ROUND-27 LAP 5 (2026-09-26).
#
# **Our closing lap for round 27**: `GO` on `221a1df` from our reading of the quick
# run, accepting the operator's override of R1, `.17`'s `Accurip 450` rewording and
# their amendment to our EAC-compatible wording, and naming 0.6.61 as the release
# that carries both pins. Moved once the lap was RELEASED. Travels alone: the bundle
# it cites is committed in both trees, not carried.

# WHY IT MOVED TO ROUND-27 LAP 3 (2026-09-25).
#
# **Our account of the failed first attempt at round 27's real test.** 0.6.59 could
# replace `.16` with `.15` from its update check or its setup wizard, and the run
# stopped at section A on `.15`; lap 3 says so first, names 0.6.60 as the fix and the
# release the test runs on, and records the operator's §6b override for it. Moved
# once the lap was RELEASED. Travels alone.

# WHY IT MOVED TO ROUND-27 LAP 2 (2026-09-24).
#
# **Our answer to their round 27 lap 1**, which names `.16` (`221a1df`) and closes on
# the real test run on it. It moves `PIN_UNDER_REVIEW`, names 0.6.59 as the release
# that carries the move, records the operator's §6b override for that tag, and
# corrects "killed from outside both programs" (the container belonged to an
# earlier Platterpus window). Moved once the lap was RELEASED, the same ordering as
# every move since round 20. Travels alone: the lap quotes no file that would have
# to ride with it.

# WHY IT MOVED TO ROUND-26 LAP 5 (2026-09-24).
#
# **Our closing lap for round 26**: `GO` on `df91ae7` from our reading of the real
# test's bundle, the one finding about us fixed, and the release that pins it. Moved
# once the lap was RELEASED, the same ordering as every move since round 20. Travels
# alone: the bundle it cites is committed in both trees, not carried.

# WHY IT MOVED TO ROUND-26 LAP 3 (2026-09-24).
#
# **Our account of the failed first attempt at the real test.** 0.6.54's section A
# refused `.15` and accepted only round 21's retired test pin; lap 3 says so first,
# describes the fix, and records the operator's §6b override for v0.6.55. Moved once
# the lap was RELEASED, the same ordering as every move since round 20. Travels
# alone: the lap quotes no file that would have to ride with it.

# WHY IT MOVED TO ROUND-26 LAP 2 (2026-09-23).
#
# **Our answer to their round 26 lap 1**, which names `.15` (`df91ae7`) and closes on
# the real test run on it. It moves `PIN_UNDER_REVIEW`, names 0.6.54 as the release
# that carries the move, and records the operator's §6b override for that tag. It
# moved only once the lap was RELEASED, the same ordering as every move since round 20.
# Travels alone: the lap quotes no file that would have to ride with it.

# WHY IT MOVED TO ROUND-23 LAP 4 (2026-09-22).
#
# **The lap that CLOSES round 23.** Their lap 3 declared GO, accepted our §A in
# full and landed `PROTOCOL.md` v5; this lap commits v5 byte-identical, re-runs
# the four shared hashes to all-match, and declares GO. `--status` reads
# `we-verified=yes (GO) they-verified=yes (GO) -> CLOSED`.
#
# **It moved only once the lap was RELEASED**, same ordering as every move since
# round 20 — and this time the clause that makes it matter is one we wrote: v5
# §5c, a lap read for its verdict must declare `HANDSHAKE-READY-TO-READ: yes`,
# fail-closed. Packing a held lap here would have been the round that specified
# that closing on an assumption of it.
#
# Travels ALONE. Every artifact this lap cites is reachable: their lap 3 at
# `cyanrip@e5008c9`, v5 at `f748d15`, and our own at `platterpus@a0aed36`.

# WHY IT MOVED TO ROUND-23 LAP 2 (2026-09-22).
#
# Round 22 is CLOSED -- GO/GO at five laps. Round 23 opened on their lap 1, and
# this lap answers all three of its close conditions: assent to v5's two clauses
# with the drafting left to them, a MEASURED assent on the held-lap banner
# qualifier, and a disposition of the 2026-09-22 acceptance run that agrees with
# four of their five rows and corrects the fifth.
#
# **It moved only once the lap was RELEASED**, the ordering round 20 established.
# The lap sat at `HANDSHAKE-READY-TO-READ: no` through four commits while the
# gate was still red, and packing it then would have built a hand-over artifact
# for a draft.
#
# Travels ALONE. This lap quotes no file that has to travel with it -- every
# artifact it cites is either in their tree (their lap 1, their PROVIDER-CONTRACT)
# or reachable in ours at `platterpus@a0aed36`, which is the whole point of
# resolving the from-commit against `origin/main`.

# WHY IT MOVED TO ROUND-20 LAP 2 (2026-09-16).
#
# Round 19 is CLOSED -- GO/GO at three laps. This lap answers round 20's two
# close conditions: CLOSE-BY enforced (print, never block) and the
# `Frame retries:` -> `Retry limit:` rename assented to.
#
# **It moved only once the lap was RELEASED, and that ordering is now enforced.**
# An envelope names the file an operator hands over, and a lap still marked
# `HANDSHAKE-READY-TO-READ: no` is not a file anyone may read -- so packing one
# would be building a hand-over artifact for a draft. While the lap was held,
# `PARTS[0]` legitimately named round 19's, and
# `test_the_envelope_leads_with_a_lap_of_the_CURRENT_round` excuses that lag ONLY
# while every lap of ours in the open round is held. The moment the flip landed,
# that test went red until this line moved -- which is the coupling working.
#
# WHY IT MOVED TO ROUND-19 LAP 2 (2026-09-14), AND WHAT THE ENVELOPE IS NOW FOR.
#
# Round 18 is CLOSED -- GO/GO at three laps. This lap answers round 19's two
# close conditions.
#
# **LAPS TRAVEL BY GIT NOW** (maintainer, 2026-09-13), so this envelope is no
# longer the transport. It stays because it is still the artifact an operator can
# hand over when git is not to hand, and because `PARTS[0]` going stale is a real
# defect with its own test -- it sat on round-14 lap 16 through all of round 15
# while four regenerations reported success. A generator cannot know a round has
# moved on.
#
# **What CHANGED with the transport is what "sent" means**, and the envelope no
# longer decides it: committing makes a lap AVAILABLE, the operator's
# announcement makes it LIVE, and `HANDSHAKE-READY-TO-READ` in the file is where
# that state is recorded. So keeping this in step is bookkeeping, not delivery --
# which is the opposite of what it used to be, and worth saying so nobody reads a
# fresh envelope as evidence a lap has gone out.
#
# One part. Lap 2 quotes no sha of `fullacceptance.txt`.

# WHY IT MOVED TO ROUND-18 LAP 2 (2026-09-13).
#
# Round 17 is CLOSED -- GO/GO at three laps, both halves published. This lap
# answers round 18's three questions and declares GO on the specification.
#
# **THE MAINTAINER ASKED FOR THIS ONE (2026-09-13)**, and specifically asked that
# the Q1 and Q3 derivations be VERIFIED before the lap was written. That paid:
# one claim was refuted (our read-speed ladder does send `-S`) and one arithmetic
# error was caught (71 steps across 8 sections, not 69 across 7). Both are in the
# lap rather than quietly corrected. Recorded like every note before it: the
# standing rule is ASK BEFORE WRITING A LAP, because a send is an event outside
# both trees and three round-15 laps were written and never handed over.
#
# One part. Lap 2 quotes no sha of `fullacceptance.txt`.

# WHY IT MOVED TO ROUND-17 LAP 2 (2026-09-12).
#
# Round 16 is CLOSED -- GO/GO, their lap 17 acknowledged our lap 16 and both
# gates agree. Lap 16 is pinned in `SENT_LAPS` at the bytes their lap 17 declares.
#
# Lap 2 answers round 17's open conditions 2 and 3 and declares 4: it names
# 0.6.46's commit, reports each of the three HANDSHAKE-BREAKING rows as handled
# with the derivation for each, and declares GO. Their §5 pre-commit makes their
# lap 3 GO unless we report a row unhandled or name a defect in `fe4d2c4`; this
# lap does neither, so the round should close at two laps.
#
# **THE MAINTAINER ASKED FOR THIS ONE (2026-09-12), and approved the merge and
# release preparation in the same breath.** Recorded like every note before it:
# the standing rule is ASK BEFORE WRITING A LAP, because a send is an event
# outside both trees and three round-15 laps were written and never handed over.
#
# One part. Lap 2 quotes no sha of `fullacceptance.txt`.

# WHY IT MOVED TO ROUND-16 LAP 16 (2026-09-12).
#
# Lap 14 is DELIVERED -- their lap 15 line 24 declares holding it at
# `2503184660c83ad0`, 17,199 bytes, extracted with OUR published reader and
# byte-identical to the raw upload. Pinned in `SENT_LAPS` at those bytes.
#
# Lap 16 CLOSES ROUND 16. Their lap 15 declares GO on `a9aedf0` after Run A
# passed on hardware; our lap 14 pre-committed to GO unless the grader exited
# non-zero or `verify_log_surface.py` found an unaccounted line. Neither fired --
# both were run here, and both results are in the lap rather than asserted. Two
# GOs close a round, so this is the last artifact of round 16 in either direction.
#
# **THE MAINTAINER ASKED FOR THIS ONE (2026-09-12), having sent lap 15 three
# times.** Recorded for the same reason every previous note records it: the
# standing rule is to ASK BEFORE WRITING A LAP, and the audit that produced that
# rule found three round-15 laps written and never handed over.
#
# One part. Lap 16 quotes no sha of `fullacceptance.txt`.

# WHY IT MOVED TO ROUND-16 LAP 14 (2026-09-11).
#
# Lap 12 is DELIVERED — the fork's lap 13 line 24 declares holding it at
# `4a69990fac889b83`, extracted with OUR published reader and byte-identical to
# the raw upload at 24,150 bytes — so its envelope on disk is history and is not
# regenerated. It is pinned in `SENT_LAPS` at those bytes.
#
# Lap 14 leads because it carries the one thing the round cannot close without
# and which their lap 13 could not supply for us: our own S-18 pre-commit,
# re-pointed at `5bbb5ae`. Lap 12's version named a REMEDY — "a commit carrying
# both `a0830e0`'s clause-1 split and §C1's `max`->`min`" — and they improved on
# `a0830e0` rather than carrying it, so the wording does not bind on the SHA they
# named. That is the second consecutive pre-commit of ours that failed to bind,
# for a second distinct reason, and an unbound pre-commit is a round that cannot
# end on an exit code.
#
# **THE MAINTAINER ASKED FOR THIS ROUND TO CLOSE (2026-09-11): "lets close".**
# Recorded for the same reason lap 10's and lap 12's notes record it: the standing
# rule is to ASK BEFORE WRITING A LAP, and the audit that produced that rule found
# three round-15 laps written and never handed over while this generator reported
# success over a round the fork had closed weeks earlier.
#
# One part again. Lap 14 quotes no sha of `fullacceptance.txt`.

# WHY IT MOVED TO ROUND-16 LAP 12 (2026-09-11).
#
# Lap 10 is DELIVERED — the fork's lap 11 line 24 declares holding it at
# `c5ab86e5fedfc33c`, and records that they ran OUR published reader over the
# envelope and got a part byte-identical to the raw upload — so its envelope on
# disk is history and is not regenerated.
#
# Lap 12 leads because it carries a finding the round cannot close without: their
# `clause2()` audio gate is `max` where it must be `min`, so one silent arm and
# one real arm PASSES clause 2 — and passes because the hashes differ. Both
# sides' S-18 pre-commits are about to resolve against that program's exit code.
#
# **THE MAINTAINER ASKED FOR THIS ONE (2026-09-11): "lets close".** Recorded for
# the same reason lap 10's note records it: the standing rule is to ASK BEFORE
# WRITING A LAP, and the audit that produced that rule found three round-15 laps
# written and never handed over while this generator reported success over a
# round the fork had closed weeks earlier.
#
# One part again. Lap 12 quotes no sha of `fullacceptance.txt`.

# WHY IT MOVED TO ROUND-16 LAP 10 (2026-09-10).
#
# Lap 7 is DELIVERED — the fork's lap 8 line 24 declares holding it at
# `990bb6bb7d25ee4b`, split with our own reader and verified against their
# manifest — so its envelope on disk is history and is not regenerated. Lap 10 is
# the operative one: it answers their laps 8 and 9, and its §D corrects OUR OWN
# published Run A block, which was missing the third file and the third command
# their `7ace6e5` added. That correction is the reason the lap cannot wait: a Run
# A performed from our instructions measures everything and grades nothing.
#
# **THE MAINTAINER ASKED FOR THIS ONE (2026-09-10): "do lap 10 back".** Recorded
# because the standing rule is to ASK BEFORE WRITING A LAP, and the audit that
# produced that rule found three round-15 laps written and never handed over
# while this generator kept reporting success over a round the fork had closed
# weeks earlier. A note saying who asked is the cheapest thing that distinguishes
# "packed and waiting" from "packed and forgotten".
#
# One part again. Lap 10 quotes no sha of `fullacceptance.txt`, and the script
# reaches the rig inside the AppImage, so shipping a copy would hand them an
# artifact nothing in the lap references.

# WHY IT MOVED TO ROUND-16 LAP 7 (2026-09-07), same day, same reasons.
#
# Lap 5 is DELIVERED — the fork's lap 6 line 24 declares holding it at
# `ad77e1346fd47218`, split with our own reader and verified against our manifest
# — so its envelope on disk is history and is not regenerated. Lap 7 leads
# because it CORRECTS lap 5: that lap told them to run `0.6.42`, which does not
# contain the two fixes the same lap describes. A correction and the thing it
# corrects must not arrive in the wrong order, which is the round-14 lap-13
# reasoning arriving again.
#
# One part again. Lap 7 quotes no sha of `fullacceptance.txt`, and Run B reaches
# the script inside the AppImage, so shipping a copy would hand them an artifact
# nothing in the lap references and a second copy of one that ships in the
# release.

# WHY IT MOVED TO ROUND-16 LAP 5 (2026-09-07), AND WHY IT TRAVELS ALONE.
#
# Lap 5 supersedes lap 3 as the operative lap: lap 3 is DELIVERED (the fork's lap
# 4 quotes it at `47368738c317f930`) and its envelope on disk is now history, kept
# rather than regenerated, because regenerating a sent artifact is the drift
# `tests/test_sent_laps_are_immutable.py` exists to prevent. This constant moving
# is the whole point — the 2026-09-04 note below is what a STALE `PARTS` costs.
#
# **One part, and `fullacceptance.txt` is deliberately out.** The script did change
# for `0.6.42`, but lap 5 quotes no sha of it and Run B reaches it through
# **Tools → Run acceptance test…** inside the AppImage, so the file the fork would
# receive is not the file the operator will run — an artifact nothing in the lap
# references, and a second copy of one that ships in the release. The rule this
# follows is the one already written for round-15 lap 15: an envelope's contents
# are a claim about what the lap needs.
#
# A one-part envelope is the case `assert_not_a_lap` is tightest against, which is
# checked on this file's own output before it is written.

# WHY THIS CARRIES FOUR LAPS, AND WHY THAT IS A FAILURE REPORT RATHER THAN A
# FEATURE (2026-09-04).
#
# Laps 4, 5 and 6 were written on 09-02, 09-03 and 09-04 and **none of them was
# ever handed over.** This constant stayed pointed at round 14 lap 16 through all
# three, and the envelope was regenerated FOUR separate times on 09-04 — because
# it also carries `fullacceptance.txt`, which was being edited — each time
# reporting success while packing a round the peer closed weeks ago.
#
# That is exactly the failure cyanrip's round-9 lap 3 §B1 named when they argued
# against deleting this generator: *"deleting the instance removed your exposure;
# the rule removed everyone's."* The rule they got us to write is that an envelope
# cannot be miscounted as a lap. It says nothing about an envelope that is
# faithfully, repeatedly, correctly built around the WRONG lap — and the docstring
# above already warned about the neighbouring case ("one artifact implying a send
# that did not happen"), which is how this one hid in plain sight.
#
# The laps travel UNMODIFIED. Protocol v4 §4a makes a correction a new lap rather
# than an edit, and there is a concrete reason beyond the principle: laps 5 and 6
# each declare a `HANDSHAKE-ROUND-DIGEST` computed over the laps before them, so
# editing 4 or 5 now would falsify a value already written down. `round-08-lap-18`
# is the precedent — written, never sent, sent unmodified two rounds later, on the
# reasoning that sending a file late does not make it a new file.
#
# PARTS[0] is lap 7 because `lead_identity()` names the envelope after the
# OPERATIVE lap, and 7 is the one that covers the other three. Its §A tells the
# reader to take 4, 5 and 6 first; the packing order and the reading order differ
# here for the first time, deliberately.
#
# `fullacceptance.txt` travels for the same reason it did in round 14: it CHANGED
# materially in this lap's subject — nine rips that asserted nothing about
# completion now do, and both `expect-status Done` sites are gone — and it is the
# artifact the round's only close condition is produced by. A lap that alters the
# script the other side is about to have run, sent without the script, is a
# description of an artifact instead of the artifact.
#
# `securereread.txt` stays OUT even though it changed this time (it carried both
# defects: the 10800 budget and `expect-status Done`). The fork's lap 11 §K
# retired it for this run because `fullacceptance.txt` contains T1 as section N,
# so it is not part of the close condition; lap 7 §C4 cites it as evidence that
# the fix was swept rather than applied where it was found, which is a claim about
# our process rather than an artifact they must review.

# WHY IT MOVED TO ROUND-15 LAP 13 (2026-09-05), and why the round-15 lap-7
# envelope was NOT regenerated.
#
# Lap 13 changes `fullacceptance.txt` -- three new graded verbs and a floor on
# `snapshot` -- so it must travel WITH the script, for the round-12 reason
# restated below: a lap that alters the file the other side is about to have run,
# sent without it, is a description of an artifact instead of the artifact.
#
# **The lap-7 envelope was left alone on purpose.** It was sent and the fork
# confirmed receipt of all four laps it carried, so regenerating it to pick up the
# edited script would have rewritten a DELIVERED artifact -- the exact drift
# `tests/test_sent_laps_are_immutable.py` exists to prevent, arriving through the
# convenient door of "the envelope test is red, run the generator". The red test
# was right that the envelope was stale against the tree; the fix was to point it
# at the lap that owns the change, not to edit history.
#
# Laps 4-7 are not re-packed: they are delivered, byte-identical on both sides,
# and verified against the fork's own repository at 098ecde.

# WHY THIS MOVED FROM LAP 6 TO LAP 13, and why `securereread.txt` came out.
#
# Lap 13 leads because it CORRECTS lap 12's own header — `0.6.26` was unpublished
# when lap 12 declared the operator was running it — so the two must travel
# together or the peer reads the correction after the thing it corrects. The lap-12
# envelope was superseded before it was sent and is not kept: an envelope on disk
# that nobody sent is a record of nothing.
#
# Laps 8 and 10 were sent BARE and PARTS deliberately stayed on lap 6 through
# both: an envelope exists to carry a lap *plus artifacts*, and a lap that only
# answers a lap would produce a one-part envelope — pointless, and the case
# `assert_not_a_lap` is tightest against. The fork sends theirs bare for the same
# reason.
#
# Lap 12 is different: it CHANGES `fullacceptance.txt` — a new `abort-if-failed`
# guard after the identity section, and the fork's C1 detector as section P2 — and
# that file is the round's only close condition. A lap that alters the script the
# other side is about to have run, sent without the script, is a description of an
# artifact instead of the artifact. So the envelope moves with it.
#
# **`securereread.txt` is out because it did not change.** The fork's lap 11 §K
# retires it for this run (`fullacceptance.txt` contains T1 as section N) and it
# is unchanged since lap 6, so re-sending it is the noise both sides keep
# declining to send. It stays in the tree for a night when only the close matters.
#
# The consequence to keep in view: the published `round14lap06platterpus.md` on
# disk is now HISTORY, not the current envelope. That is correct — it is the record
# of what lap 6 sent, and lap 6 sent the file as it then stood. Regenerating it
# against today's script would falsify what we sent. (Retired from the tree on
# 2026-10-06 with every other committed envelope; `git show 37b07893:` + its old
# path still recovers it, as `docs/handshake/README.md` records.)

#: The envelope's name, as a template. **Two properties, and both are checked by
#: `tests/test_handshake_file_naming.py` rather than asserted in this comment.**
#:
#: 1. **It cannot match `round-*.md`**, the glob both projects' gates use. The
#:    envelope carries wire headers in its body, so a matching name could be
#:    resolved as a lap and displace the round's real latest one. `round09…` has no
#:    hyphen after `round`, so it cannot match on any filesystem, case-sensitive or
#:    not.
#: 2. **It is safe to cross machines** — CLAUDE.md → *Artifact filenames that cross
#:    machines*: lowercase ASCII letters and digits only, numbers zero-padded. This
#:    file is relayed by hand through a chat client and a file manager, which is the
#:    exact path that lost a rig run to `round08joint.txt` vs `round-08-joint.txt`.
#:
#: **Why a template and not a literal.** The literal drifted three times in one
#: session — `round08platterpusbundle.md` → `round09platterpusenvelope.md` →
#: `round09lap06platterpus.md` — because nothing stated the pattern and nothing
#: checked it, so each send re-invented the name. The operator noticed before any
#: gate did. The name is now *generated from the lap it carries*, the same rule
#: `handshake_filename` follows and for the same reason: a hand-typed name is a
#: second description of a fact the file already declares.
#: **It states BOTH ENDS, not just the sender** (2026-09-07, maintainer: *"i need
#: handshake files to tell me who they came from, and who they go to"*). The old
#: name was `round16lap02platterpus.md` — the trailing word is the sender, which
#: answers half the question and looks like it answers all of it. The operator is
#: the only party who handles these by hand, in a file manager and a chat client
#: where nothing else says which way a file is travelling, and they hold files
#: going *both* ways. `…platterpustocyanrip` cannot be misread in either
#: direction and still obeys the cross-machine rule above: lowercase ASCII and
#: digits, no separators.
#:
#: Safe to change unilaterally: the name is ours to generate, and their splitter
#: keys on the BEGIN/END delimiters rather than the filename. The matching ask —
#: that their envelopes say it too — is a request in the lap, not an edit here.
#: **Matched to the fork's spelling, deliberately, and it costs a rule.** They
#: adopted the same idea in round 16 lap 1 and spelled it
#: `round16lap01FROMcyanripTOplatterpus.md`. Ours was `…platterpustocyanrip.md`:
#: the same information, a different shape. The operator holds BOTH files in one
#: folder, and `CLAUDE.md`'s own naming rule says the hazard was never hyphens as
#: such — it was *"two conventions"*, one artifact spelled two ways.
#:
#: So the uppercase `FROM`/`TO` are a deliberate exception to the lowercase-only
#: rule, taken because matching the peer serves the reader the rule exists for.
#: Every filesystem in this project's path handles the case fine; what it could
#: not handle was the same file having two names. Recorded in `CLAUDE.md` beside
#: the rule rather than left as a silent divergence from it.
NAME_TEMPLATE: str = "round{round:02d}lap{lap:02d}FROMplatterpusTOcyanrip.md"


def envelope_filename(round_: int, lap: int) -> str:
    """The cross-machine name for the envelope carrying ``round``/``lap``.

    Zero-padded to two digits to match the lap-file convention's pad width, so the
    two names state the same numbers the same way.
    """
    return NAME_TEMPLATE.format(round=round_, lap=lap)


def lead_identity() -> tuple[int, int]:
    """``(round, lap)`` of the lap this envelope is *for* — read from its header.

    ``PARTS[0]`` is the lap being sent; anything after it is context the peer asked
    for. Reading the header rather than taking arguments is what makes the name
    unable to drift from the contents: change the parts and the name follows.
    """
    text = _FENCE_RE.sub("", PARTS[0].read_text(encoding="utf-8"))
    found: list[int] = []
    for field in ("HANDSHAKE-ROUND", "HANDSHAKE-LAP"):
        values = re.findall(rf"^{field}:[ \t]*(\d+)[ \t]*$", text, re.MULTILINE)
        if len(values) != 1:
            raise SystemExit(
                f"cannot name the envelope: {PARTS[0].name} declares {field} "
                f"{len(values)} time(s), and the name states that number. "
                "A lead part must be exactly one lap."
            )
        found.append(int(values[0]))
    return found[0], found[1]


BEGIN: str = "<<<<<<<<<< BEGIN {name} sha256={sha} >>>>>>>>>>"
END: str = "<<<<<<<<<< END {name} >>>>>>>>>>"

#: The exact inverse, published inside the envelope so the receiver has code
#: rather than a description. Byte-compatible with cyanrip's reader — verified by
#: splitting their round-9 envelope with ours and theirs with the same pattern.
PART_RE: re.Pattern[str] = re.compile(
    r"^<{10} BEGIN (?P<name>\S+) sha256=(?P<sha>[0-9a-f]{64}) >{10}$\n"
    r"(?P<body>.*?)\n^<{10} END (?P=name) >{10}$",
    re.MULTILINE | re.DOTALL,
)

#: Fences stripped before counting declarations, per v4 §2 rule 2.
_FENCE_RE: re.Pattern[str] = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)

#: The three fields whose exactly-once presence defines a lap (v4 §5a).
_LAP_FIELDS: tuple[str, ...] = (
    "HANDSHAKE-ROUND",
    "HANDSHAKE-LAP",
    "HANDSHAKE-FROM",
)

#: The envelope's FILENAME — a name, deliberately not a path. Defined here rather
#: than beside `NAME_TEMPLATE` only because it calls `lead_identity()`, which needs
#: `_FENCE_RE` to exist. It was `OUT`, a path into `docs/handshake/outbound/`, until
#: 2026-10-06: that default is how 44 envelopes came to be committed beside the laps.
OUT_NAME: str = envelope_filename(*lead_identity())


def refusal_for_destination(directory: Path) -> str | None:
    """Why ``directory`` may not receive an envelope, or ``None`` if it may.

    **Anywhere inside this working tree is refused**, not only `docs/handshake/`:
    a file written anywhere in the tree is one `git add` from a commit. Laps travel
    by git, so the repository already holds every byte an envelope would carry, and
    a committed copy is a second record of one lap, under a second name. Resolved
    first, so a `..` or a symlink cannot walk a path back in. Pure: no I/O beyond
    path resolution, so a test can drive it with any path.
    """
    target = directory.resolve()
    if target == REPO_ROOT or target.is_relative_to(REPO_ROOT):
        return (
            f"{directory} is inside this repository ({REPO_ROOT}). An envelope is a "
            "hand-carry copy of laps `main` already holds, and committed it becomes "
            "a second record of the same lap. Write it outside the working tree, "
            "e.g. a scratch directory or /tmp."
        )
    return None


@dataclass(frozen=True)
class Part:
    name: str
    size: int
    sha256: str
    text: str


def assert_not_a_lap(envelope: str) -> None:
    """Refuse to emit an envelope a conforming enumerator would read as a lap.

    **Checked on the output, before writing.** The property is structural — an
    envelope carrying N parts declares each field N times — but "structural" is
    what we assumed last time, and the one-part case is exactly where the
    assumption fails: an envelope around a single lap declares each field
    **once**, which is indistinguishable from a lap.

    So the guard is not decoration even though the rule makes it look like one,
    and the fix when it fires is a real one: the envelope's own preamble declares
    the fields too, with a value that says what the file is. That keeps the count
    at two for a one-part envelope and at N+1 for the rest.
    """
    stripped = _FENCE_RE.sub("", envelope)
    for field in _LAP_FIELDS:
        count = len(re.findall(rf"^{re.escape(field)}:", stripped, re.MULTILINE))
        if count == 1:
            raise SystemExit(
                f"refusing to write {OUT_NAME}: it declares {field} exactly once, "
                "so a conforming enumerator (v4 §5a) would read this envelope as a "
                "lap. Add the envelope's own declaration to the preamble."
            )


def read_parts() -> list[Part]:
    out: list[Part] = []
    for path in PARTS:
        data = path.read_bytes()
        out.append(
            Part(
                name=path.name,
                size=len(data),
                sha256=hashlib.sha256(data).hexdigest(),
                text=data.decode("utf-8"),
            )
        )
    return out


def split(envelope: str) -> dict[str, bytes]:
    """Envelope text → ``{filename: exact original bytes}``. Never raises.

    **Parses the hash and does not check it** — deliberately, so this stays a pure
    inverse of :func:`render`. :func:`verify_split` is the checking form, and it
    is what the CLI calls. Nothing should use this one to decide whether an
    envelope arrived intact.
    """
    return {
        m["name"]: (m["body"] + "\n").encode("utf-8")
        for m in PART_RE.finditer(envelope)
    }


def verify_split(envelope: str) -> list[tuple[str, bytes, str, str]]:
    """Split and check every part. ``[(name, body, declared, computed)]``.

    A part is intact when ``declared == computed``. Returns both rather than a
    bool per part, because the caller has to be able to *print* the mismatch — a
    corrupted transfer that reports only "failed" leaves the two projects with no
    way to tell a truncation from a re-encoding.

    **Why this exists as a checking function at all.** :func:`split` parses the
    ``sha256=`` out of the delimiter and then ignores it, and until now that was
    the only splitter — reachable from no CLI, so every actual split was done by
    hand-writing the regex again (three times on 2026-08-21 alone). A per-part
    hash that nothing compares is decoration, and the delimiter carries it
    precisely so an envelope that lost bytes in a chat client cannot be read as
    complete. Same shape as the rule about a `cancel()` with no call site: the
    capability was implemented and unreachable.
    """
    out: list[tuple[str, bytes, str, str]] = []
    for match in PART_RE.finditer(envelope):
        body = (match["body"] + "\n").encode("utf-8")
        out.append(
            (match["name"], body, match["sha"], hashlib.sha256(body).hexdigest())
        )
    return out


def _do_split(envelope_path: Path, into: Path) -> int:
    """Write every part of `envelope_path` into `into`, verifying each hash.

    Refuses to write anything if any part fails, rather than leaving a directory
    of files where some are trustworthy and some are not — a half-written split
    is worse than none, because the next step reads whatever is on disk.
    """
    try:
        text = envelope_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"cannot read {envelope_path}: {exc}", file=sys.stderr)
        return 1

    parts = verify_split(text)
    if not parts:
        print(
            f"{envelope_path}: no envelope parts found. Expected column-0 "
            f"delimiters of the form '<<<<<<<<<< BEGIN <name> sha256=<64 hex> "
            f">>>>>>>>>>'. A file with none is not an envelope — check whether a "
            f"chat client reflowed it.",
            file=sys.stderr,
        )
        return 1

    bad = [(n, d, c) for n, _b, d, c in parts if d != c]
    for name, _body, declared, computed in parts:
        mark = "OK  " if declared == computed else "BAD "
        print(
            f"{mark} {name:44} {declared[:16]} {'==' if declared == computed else '!='} {computed[:16]}"
        )
    if bad:
        print(
            f"\n{len(bad)} of {len(parts)} parts do not match their declared "
            f"hash. NOTHING was written. Ask the sender to resend — and say which "
            f"parts, because a mismatch on one part and on all of them are "
            f"different problems.",
            file=sys.stderr,
        )
        return 1

    into.mkdir(parents=True, exist_ok=True)
    for name, body, _declared, _computed in parts:
        # `Path(name).name` so a part called "../../etc/passwd" cannot escape the
        # target directory. The envelope is external input from another project;
        # nothing crosses that seam unchecked (Critical rule #12).
        target = into / Path(name).name
        target.write_bytes(body)
    print(f"\n{len(parts)} parts verified and written to {into}")
    return 0


def render(parts: list[Part]) -> str:
    table = "\n".join(
        f"| `{p.name}` | {p.size:,} | `{p.sha256[:16]}…` |" for p in parts
    )
    header = f"""# Transport envelope — {len(parts)} file(s), Platterpus → cyanrip fork

**Not a merged file and not a lap.** Each part below is byte-identical to its
original, between column-0 delimiters, with its own SHA-256. Split it before
reading; the reader is published here as code so you have an exact inverse rather
than a description of one.

**It cannot be counted as a lap.** Its own preamble declares the wire fields
below, so together with the parts it carries it declares each of them more than
once — failing v4 §5a's exactly-once test, which every conforming enumerator
uses. `scripts/emit_envelope.py` asserts that on this file before writing it,
because a **single-part** envelope would otherwise declare each field exactly
once and be indistinguishable from a lap.

HANDSHAKE-ROUND: not-a-lap (transport envelope)
HANDSHAKE-LAP: not-a-lap (transport envelope)
HANDSHAKE-FROM: not-a-lap (transport envelope)

## Manifest

| file | bytes | sha256 |
| --- | --- | --- |
{table}

## Reader

```python
import hashlib, re
PART = re.compile(
    r"^<{{10}} BEGIN (?P<name>\\S+) sha256=(?P<sha>[0-9a-f]{{64}}) >{{10}}$\\n"
    r"(?P<body>.*?)\\n^<{{10}} END (?P=name) >{{10}}$",
    re.MULTILINE | re.DOTALL,
)
for m in PART.finditer(open("{OUT_NAME}", encoding="utf-8").read()):
    data = (m["body"] + "\\n").encode("utf-8")
    assert hashlib.sha256(data).hexdigest() == m["sha"], m["name"]
    open(m["name"], "wb").write(data)
```

---
"""
    bodies = [
        BEGIN.format(name=p.name, sha=p.sha256)
        + "\n"
        + p.text.rstrip("\n")
        + "\n"
        + END.format(name=p.name)
        + "\n"
        for p in parts
    ]
    return header + "\n" + "\n".join(bodies)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="build and verify in memory, write nothing; exit 1 if it fails",
    )
    parser.add_argument(
        "--out",
        metavar="DIR",
        type=Path,
        help="where to write the envelope: required, and never inside this repo",
    )
    parser.add_argument(
        "--split",
        metavar="ENVELOPE",
        type=Path,
        help=(
            "UNPACK a received envelope instead of building ours: verify every "
            "part against its declared sha256 and write them out. Refuses to "
            "write anything if any part mismatches."
        ),
    )
    parser.add_argument(
        "--into",
        metavar="DIR",
        type=Path,
        default=Path("."),
        help="where --split writes the parts (default: the current directory)",
    )
    args = parser.parse_args(argv)

    # --split is the INBOUND direction and shares nothing with building ours, so
    # it returns before any of the outbound machinery runs. In particular it must
    # not require our own PARTS to exist: unpacking what the fork sent has to work
    # in a tree where we have no outbound lap staged.
    if args.split is not None:
        return _do_split(args.split, args.into)

    wanted = render(read_parts())
    assert_not_a_lap(wanted)

    # --check no longer compares against a committed copy, because there is none
    # to compare against (2026-10-06). It checks the property a copy exists to
    # have: every part splits back out byte-identical to the file it came from.
    if args.check:
        recovered = split(wanted)
        stale = [p.name for p in PARTS if recovered.get(p.name) != p.read_bytes()]
        if stale or len(recovered) != len(PARTS):
            print(f"{OUT_NAME} does not round-trip: {stale}", file=sys.stderr)
            return 1
        print(f"{OUT_NAME}: {len(PARTS)} part(s) round-trip; nothing written")
        return 0

    # Writing needs a destination OUTSIDE the working tree. There is no default,
    # because the old default (`docs/handshake/outbound/`) is the defect.
    if args.out is None:
        print("pass --out DIR (outside this repository) to write it", file=sys.stderr)
        return 2
    refusal = refusal_for_destination(args.out)
    if refusal is not None:
        print(f"refusing to write {OUT_NAME}: {refusal}", file=sys.stderr)
        return 2
    target = args.out / OUT_NAME
    try:
        args.out.mkdir(parents=True, exist_ok=True)
        target.write_text(wanted, encoding="utf-8")
    except OSError as exc:
        print(f"cannot write {target}: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {target} ({len(wanted.encode('utf-8')):,} bytes)")
    for part in read_parts():
        print(f"  {part.name:28} {part.size:>8,}  {part.sha256[:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
