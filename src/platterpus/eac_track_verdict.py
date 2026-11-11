# SPDX-License-Identifier: GPL-3.0-only
"""The words at the foot of each track block in the EAC-layout log: its verdict.

Split from :mod:`platterpus.eac_log_export` on 2026-11-11 (round 39's G3, "the
record") because the per-track verdict grew two more cases, a track a CTDB repair
rewrote and a track whose reads disagreed, and the renderer was already far past
the module-size heuristic. Deciding the line and laying out the block are
separate jobs: this module holds every verdict the block's last line can be,
the precedence between them, and the guard that keeps EAC's ``Accurately
ripped`` off a repaired track's AccurateRip row. ``eac_log_export`` imports them
under their old names, so its callers and tests read unchanged.

**The rule every branch keeps:** no ``OK`` unless the track was read cleanly,
its reads did not disagree, nothing contradicts it and no repair replaced it.
EAC prints ``Copy OK`` over reads that disagree and over tracks AccurateRip
rejects (``docs/eac-parity.md`` Part F row 8); this log must not.

Pure; no Qt, no I/O; never raises.
"""

from __future__ import annotations

#: The per-track verdict for a track paranoia SKIPPED on (gave up verifying a read
#: and kept what it had) that AccurateRip did not confirm. Track 18 of the
#: 2026-10-04 rig run had 2,586 skips, no whole-track AccurateRip match, and this
#: log said "Copy OK" over it. The words are ours, proposed in our round 30 lap 8
#: S20 and accepted by the fork in their lap 9 S26
#: (cyanrip@f6d72c0:docs/handshake/round-30-lap-09.md), because this log is what
#: they diff against and neither side rewords it alone (round 7 lap 11, H4).
#: Their reason for preferring it to the track's own "ripped with errors", which
#: `.20` prints for such a track: that says a specific error happened, and on a
#: skip none was reported; what happened is that the reads could not be verified.
UNVERIFIED_SKIPS_VERDICT: str = (
    "Copy NOT confirmed — the ripper could not verify every read and AccurateRip "
    "did not confirm the audio"
)

#: The per-track verdict for a track AccurateRip contradicts
#: (`verdict.track_accuraterip_contradiction`): EAC's own line for a copy it does
#: not call OK, with no "OK" in it (plan of record, 2026-10-26, row 8). The
#: `Proof:` row above it says why, in our words.
CONTRADICTED_VERDICT: str = "Copy finished"

#: The per-track verdict for a track a CTDB repair rewrote after the read (G3,
#: 2026-11-11). EAC has no wording for a repair (CUETools does it, in its own
#: log), so this is EAC's own non-OK line with our clause after it: the rows
#: above describe a read that was not verified, and the ``Record:`` row says what
#: replaced it. Never ``OK``: the read was not, and the repair is not a read.
REPAIRED_VERDICT: str = (
    "Copy finished — this read was then repaired from CTDB (see Record above)"
)

#: The per-track verdict for a track whose reads disagreed (G3's second banned
#: wording: ``Copy OK`` over disagreeing reads, EAC's own fault, ``docs/
#: eac-parity.md`` Part F row 8). EAC prints ``Copy OK`` when its Test and Copy
#: CRCs differ; ours prints EAC's own non-OK line and says why.
DISAGREED_VERDICT: str = "Copy finished — the reads disagreed (see Record above)"

#: As :data:`DISAGREED_VERDICT`, where AccurateRip verifies the read kept (a
#: verified-read chase, or a converged re-read whose earlier reads differed).
#: Still not ``OK``: the drive gave more than one value, and the record says
#: which one was kept and why, which a scanner reading ``OK`` would not see.
DISAGREED_VERIFIED_VERDICT: str = (
    "Copy finished — the reads disagreed, and AccurateRip verifies the read kept "
    "(see Record above)"
)


#: What a repaired track's AccurateRip row starts with in place of EAC's
#: ``Accurately ripped``, in the one case it could otherwise appear (below).
REPAIRED_READ_MATCHED: str = "AccurateRip matched this read"


def accuraterip_row(line: str, *, repaired: bool) -> str:
    """The AccurateRip row ``line``, never ``Accurately ripped`` over a repaired track.

    **G3's first banned wording** (the owner-approved plan of 2026-11-11):
    ``Accurately ripped`` on a track a CTDB repair rewrote. The row describes the
    READ, and the file is no longer that read, so EAC's phrase would vouch for
    audio that is not in the file. The repair refuses a track AccurateRip
    verified (``ctdb/repair_plan.py``), so the read's row is never a match there
    and this branch should never fire; it is here so the invariant holds by
    construction rather than by that guard alone, and it keeps the read's facts
    (the confidence, the checksum, the version) in words that cannot be mistaken
    for a statement about the repaired file.
    """
    if repaired and line.startswith("Accurately ripped"):
        return (
            REPAIRED_READ_MATCHED
            + line[len("Accurately ripped") :]
            + "; a CTDB repair then rewrote this track (see Record below)"
        )
    return line


def status_line(
    status: str,
    *,
    reproducible: bool | None = None,
    unverified_skips: bool = False,
    contradicted: bool = False,
    stopped_by_time_limit: bool = False,
    repaired: bool = False,
    reads_disagree: bool | None = None,
    accuraterip_verified: bool = False,
) -> str:
    """Render the track status the way EAC does — but never `Copy OK` for a track
    whose re-reads disagreed.

    **The defect this closes, measured on hardware 2026-09-03.** The
    EAC-compatible log for the acceptance run's secure re-read printed, for
    tracks 3, 4 and 5:

        Copy CRC 418F6CF8  (re-reads did NOT agree — this read is not confirmed
                            reproducible)
        Copy OK

    Two lines apart, in the same track block: an honest parenthetical and a
    verdict that contradicts it. `Copy OK` is EAC's *clean* verdict, and it is
    the string a logchecker greps for and a human scans for. The disc-level
    `Read stability` line already named those tracks — so the app knew, said so
    twice elsewhere, and still stamped the per-track verdict clean.

    `CLAUDE.md`'s EAC-parity rule is the one that decides this: *an
    EAC-compatible log must stay as close to the EAC original as possible
    **without forging it***, with equal-or-stronger rigour labelled as ours
    (KDD-24). Printing `Copy OK` over a read we have just declared
    unreproducible is the forging half.

    So a non-reproducible track gets a verdict in our own words rather than
    EAC's. It deliberately does **not** contain the substring `Copy OK`: a
    parenthetical qualifier appended to that string would still read as clean to
    every mechanical consumer, which is the *"every word accurate, the sentence
    wrong"* shape this project keeps paying for.

    ``reproducible`` is tri-state and only ``False`` changes anything. ``None``
    means the rip recorded no convergence data — a backend that does not report
    it, or a rip with no secure re-read — and inventing a doubt there would be
    the mirror defect.

    ``unverified_skips`` is ``verdict.track_has_unverified_skips``: paranoia
    skipped on the track and AccurateRip did not confirm it. It renders
    :data:`UNVERIFIED_SKIPS_VERDICT`, whatever the track's own status says. A
    skipped track AccurateRip DID confirm keeps ``Copy OK``: an exact match proves
    the audio however it was read.

    **Precedence, when a track both was skipped on and hit the repeat limit: the
    skip verdict takes this line.** Both facts stay in the block that way. The
    re-read shortfall is already on the ``Copy CRC`` line above, in words that say
    how many reads agreed, and the ``Read stability`` line names the track; the
    skip is said nowhere else in this document. The other order would print
    "re-reads did not converge" twice and drop the skip. Both verdicts begin
    ``Copy NOT confirmed``, so a reader scanning for that phrase finds the track
    either way.

    ``contradicted`` is ``verdict.track_accuraterip_contradiction(track) is not
    None``: AccurateRip matched frame 450 only, or nothing. Such a track gets
    EAC's own ``Copy finished`` (:data:`CONTRADICTED_VERDICT`), the line EAC
    prints for a copy it does not call OK, never ``Copy OK`` (plan of record,
    2026-10-26, row 8). The ``Proof:`` row above it names the contradiction in our
    words. The two verdicts above take precedence, because each already reads
    not clean and names its own cause.

    ``stopped_by_time_limit`` (the fork's proposed ``--reread-time-limit``, round
    36 lap 10 S11) words a non-reproducible track's verdict by the limit that
    stopped it: OUR time limit, never the disc. It changes nothing unless
    ``reproducible`` is ``False``.

    ``repaired`` (G3, 2026-11-11): a CTDB repair rewrote the track after the
    read. It renders :data:`REPAIRED_VERDICT`, after the skip verdict only. The
    reason is the skip precedence's own: every fact must survive somewhere in the
    block. A re-read that did not converge is still said on the ``Copy CRC`` line
    and in ``Read stability``, and a contradiction in the ``Proof:`` row, so the
    repair may take this line; a skip is said nowhere else, so it keeps it, and the
    ``Record:`` row then carries the repair. The file a reader keeps is the
    repaired one, which is why the repair outranks what the read alone showed.

    ``reads_disagree`` is :func:`platterpus.track_record.reads_disagree`, and only
    ``True`` changes anything: :data:`DISAGREED_VERIFIED_VERDICT` when
    ``accuraterip_verified`` (the ``Proof:`` row's kind is AccurateRip or a
    verified re-read), else :data:`DISAGREED_VERDICT`. After ``contradicted``,
    whose bare ``Copy finished`` already reads not clean. **No branch but the
    last can return an ``OK``**, which ``tests/test_track_record.py`` sweeps.
    """
    if unverified_skips:
        return UNVERIFIED_SKIPS_VERDICT
    if repaired:
        return REPAIRED_VERDICT
    if reproducible is False and stopped_by_time_limit:
        return (
            "Copy NOT confirmed — re-reads stopped at our time limit before they "
            "converged, so this track is not verified reproducible (see Read "
            "stability above)"
        )
    if reproducible is False:
        # "did not converge", not "did not agree": on the round-28 Full run's
        # track 5 two reads DID agree, and the Copy CRC line above says how many.
        # Converging is the -Z verdict itself, so the sentence is true of every
        # track that reaches this branch (TASKS.md, *Found while integrating*, 1).
        return (
            "Copy NOT confirmed — re-reads did not converge, so this track is not "
            "verified reproducible (see Read stability above)"
        )
    if contradicted:
        return CONTRADICTED_VERDICT
    if reads_disagree is True:
        return DISAGREED_VERIFIED_VERDICT if accuraterip_verified else DISAGREED_VERDICT
    # EAC writes "Copy OK"; our backends use phrases like "ripped successfully".
    normalized = status.strip().lower()
    if normalized in ("copy ok", "ripped successfully"):
        return "Copy OK"
    return status.strip()
