# SPDX-License-Identifier: GPL-3.0-only
"""Off-thread CTDB verify for a finished rip (KDD-14 Phase 1).

A CTDB verify does two slow things that must never run on the Qt GUI thread:
an HTTP lookup against ``db.cuetools.net`` and a decode of every ripped FLAC to
PCM (a ``flac`` subprocess per file). MainWindow runs ``verify_rip_dir`` on a
**daemon thread** and reports the verdict back via a queued signal — the same
pattern as the post-rip tagging / cover-art work, and deliberately NOT a joined
``QThread``: the decode can take far longer than any sane ``closeEvent`` wait,
and destroying a still-running ``QThread`` aborts the whole app
(``docs/architecture.md`` §3.2). A daemon thread dies with the process and
guards its own emit, so closing the window mid-verify is always safe.

The verdict is always trustworthy-by-construction-or-labelled: the audio CRC is
now hardware-validated (``ctdb.crc.CRC_VALIDATED`` is True, KDD-16), so a
``MATCH`` reads as "verified"; were the gate ever re-opened, a ``MATCH`` is
flagged experimental inside the result instead. This never *fabricates* a
verdict — every failure mode is already a verdict from ``verify_rip``.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from platterpus.adapters.ctdb_client import CTDBClient
from platterpus.ctdb.toc import SamplesProbe
from platterpus.ctdb.verify import (
    CtdbVerifyResult,
    PcmDecoder,
    Verdict,
    verify_rip,
)

log = logging.getLogger(__name__)

# How long to let any in-flight post-rip work (metaflac tagging / cover-art
# embed, on a separate daemon thread) finish before we start decoding. Those
# steps rewrite the SAME FLAC files; decoding one mid-rewrite would read a torn
# file and report a spurious decode error. Bounded so a wedged post-rip thread
# can't hang the verify forever.
_SETTLE_TIMEOUT_S: float = 60.0


def verify_rip_dir(
    client: CTDBClient,
    rip_dir: Path,
    *,
    decoder: PcmDecoder | None = None,
    samples_probe: SamplesProbe | None = None,
    wait_for: threading.Thread | None = None,
) -> CtdbVerifyResult:
    """Verify the FLACs in ``rip_dir`` against CTDB. Never raises.

    Intended to run OFF the GUI thread (MainWindow calls it on a daemon
    thread). ``decoder``/``samples_probe`` are injected in tests; production
    defaults shell out to host ``flac``/``metaflac`` via ``ctdb.verify``.
    ``wait_for`` is the post-rip metaflac thread, if running — joined first so
    we never decode a FLAC mid-rewrite.
    """
    # Let post-rip tagging / cover-art embedding settle first (see above).
    if wait_for is not None and wait_for.is_alive():
        wait_for.join(_SETTLE_TIMEOUT_S)

    # Track order = filename order ("NN - Title.flac"), matching how the rest
    # of the app enumerates a ripped album. NON-recursive on purpose: the CTDB
    # TOC is exactly this disc's tracks, which sit directly in the album folder
    # (the ripper writes the log beside them). A recursive glob would pull FLACs
    # from a nested folder — a bonus disc, a leftover, or the whole music library
    # if rip_dir ever fell back to the output root — into the TOC and produce a
    # spurious "not in database" (#40).
    flac_paths = sorted(rip_dir.glob("*.flac"))
    if not flac_paths:
        return CtdbVerifyResult(
            Verdict.LOOKUP_ERROR, message="no FLAC files found to verify"
        )
    try:
        return verify_rip(
            flac_paths, client, decoder=decoder, samples_probe=samples_probe
        )
    except Exception as exc:  # noqa: BLE001 — verify must always return a verdict
        # verify_rip is built to never raise for expected failures; this
        # belt-and-braces guard keeps the "always a verdict" contract.
        log.exception("CTDB verify crashed")
        return CtdbVerifyResult(
            Verdict.LOOKUP_ERROR, message=f"unexpected error: {exc}"
        )
