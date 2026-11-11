# SPDX-License-Identifier: GPL-3.0-only
"""After a CTDB repair: ask AccurateRip about the repaired audio (TASKS R138).

**Why** (round 39's gate G2, 2026-11-11: *track 5's CTDB-repaired audio must be
verified by AccurateRip v2*). The repair proves its result against CTDB, whose
parity drove it; AccurateRip is the witness independent of CTDB. The repair
computes each rewritten track's AccurateRip v1 and v2 from the new file
(``RepairedTrack.accuraterip_*_after``); this module asks the database once for
the disc and records, per rewritten track and per version, the tri-state
answer (``accuraterip_db_answer.py``) on the repair record. The record, the
report, the EAC-layout log's ``Record:`` row and the results pane then read it.

Two steps, both called by the repair worker (``workers/ctdb_repair_worker.py``)
on its own thread, only after a REPAIRED commit:

* :func:`lookup_for_repair` reads the disc's AccurateRip ID from the rip's log
  (cyanrip's ``AccurateRip ID:`` line) and makes ONE lookup. No ID, or no client,
  is a stated reason, never a guess and never a request;
* :func:`with_accuraterip` puts the answers on the record. Pure; never raises.

**The track count asked for is the album's audio file count**, which for a whole
disc is its audio track count: the repair runs only on a whole-disc CTDB match,
and the files are numbered as the repair numbers them (the i-th file is the i-th
audio track, ``repair_run.accuraterip_answers``). A reply naming another count is
refused by the adapter, so a wrong count reads "not determined", never "not in
the database" by mistake.
"""

from __future__ import annotations

import dataclasses
import logging

from platterpus.accuraterip_db_answer import answer_for, summarize
from platterpus.adapters.accuraterip_db import (
    AccurateRipDbClient,
    DbarLookup,
    LookupState,
    parse_disc_id,
)
from platterpus.ctdb.repair_types import RepairRecord, RepairStatus

log = logging.getLogger(__name__)


def lookup_for_repair(
    client: AccurateRipDbClient | None,
    rip_log: object,
    track_count: int,
    cancelled: bool = False,
) -> DbarLookup:
    """The disc's AccurateRip answer, or FAILED with why it was not asked.

    ``cancelled`` (the repair's job was cancelled: the app is closing) asks
    nothing, because a lookup is a network wait the cancel cannot interrupt.
    Never raises: the client's own contract, and a guard here for a client that
    breaks it, because the repair has already committed and a raise now would
    lose the record of what it did.
    """
    if cancelled:
        return DbarLookup(
            LookupState.FAILED,
            reason="the repair was stopped (the app was closing) before AccurateRip "
            "was asked",
        )
    if client is None:
        return DbarLookup(
            LookupState.FAILED,
            reason="no AccurateRip client was given to the repair, so none was asked",
        )
    text = getattr(rip_log, "accuraterip_disc_id", "")
    disc = parse_disc_id(text)
    if disc is None:
        return DbarLookup(
            LookupState.FAILED,
            reason=(
                "the rip's log printed no AccurateRip ID (cyanrip 0.9.4-rc3 or the "
                f"fork's .23 and later print one), so the disc could not be asked "
                f"about (read {text!r})"
            ),
        )
    try:
        return client.lookup(disc, track_count)
    except Exception as exc:  # noqa: BLE001 — the client is documented never to raise; a record must survive one that does
        log.exception("the AccurateRip client raised")
        return DbarLookup(
            LookupState.FAILED,
            reason=f"the AccurateRip lookup raised {type(exc).__name__}: {exc}",
        )


def with_accuraterip(record: RepairRecord, lookup: DbarLookup | None) -> RepairRecord:
    """``record`` with each rewritten track's v1 and v2 answered from ``lookup``.

    A record that is not REPAIRED is returned as it is: it rewrote nothing, so
    there is no repaired audio to ask about. Never raises.
    """
    if record.status is not RepairStatus.REPAIRED:
        return record
    tracks = tuple(
        dataclasses.replace(
            row,
            accuraterip_v1_database=answer_for(
                lookup, row.track, row.accuraterip_v1_after
            ),
            accuraterip_v2_database=answer_for(
                lookup, row.track, row.accuraterip_v2_after
            ),
        )
        for row in record.tracks
    )
    return dataclasses.replace(
        record, tracks=tracks, accuraterip_lookup=summarize(lookup)
    )
