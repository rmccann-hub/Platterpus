# SPDX-License-Identifier: GPL-3.0-only
"""Off-thread FLAC encode-verify for a finished rip.

Testing every FLAC means a ``flac --test`` decode per file — far too slow for
the GUI thread. MainWindow runs ``verify_rip_dir`` on a **daemon thread** and
reports the result via a queued signal — the same pattern as the post-rip
tagging / cover-art / CTDB work, and deliberately NOT a joined ``QThread``: a
multi-track decode can outlast any sane ``closeEvent`` wait, and destroying a
running ``QThread`` aborts the app (``docs/architecture.md`` §3.2).

Like the others it joins the post-rip metaflac thread first (``wait_for``) so it
never decodes a FLAC mid-rewrite, and it never raises.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from pathlib import Path

from platterpus import rip_files
from platterpus.adapters.flac_verify import FlacVerifyResult, verify_flac_files

log = logging.getLogger(__name__)

# Match the CTDB worker: bound the wait on in-flight tagging/cover-art (which
# rewrite the SAME FLACs) so we never test a file mid-rewrite, without hanging
# forever on a wedged post-rip thread.
_SETTLE_TIMEOUT_S: float = 60.0


def verify_rip_dir(
    rip_dir: Path,
    *,
    wait_for: threading.Thread | None = None,
    verifier: Callable[[list[Path]], FlacVerifyResult] | None = None,
) -> FlacVerifyResult:
    """Verify every FLAC under ``rip_dir``. Never raises.

    Intended to run OFF the GUI thread. ``wait_for`` is the post-rip metaflac
    thread (or None): joined first so we never test a FLAC mid-rewrite.
    ``verifier`` is injected in tests; production decodes via host ``flac``.
    """
    if wait_for is not None and wait_for.is_alive():
        wait_for.join(_SETTLE_TIMEOUT_S)

    # Verify exactly the masters THIS rip wrote, taken from its own `.log` rather
    # than from the folder listing (see `platterpus.rip_files`). This is the check
    # a leftover hurt most: a truncated FLAC abandoned by a cancelled rip fails
    # `flac --test`, so a clean re-rip got a ⚠ FAILED line and a downgraded
    # verdict for audio that was never in question. rip_files falls back to the
    # old non-recursive glob (logging that it did) when no log names the files.
    file_set = rip_files.rip_master_files(rip_dir)
    flac_paths = list(file_set.files)
    if not flac_paths:
        return FlacVerifyResult(error="no FLAC files found to verify")
    verify = verifier or verify_flac_files
    try:
        return verify(flac_paths)
    except Exception as exc:  # noqa: BLE001 — verify must always return a result
        log.exception("FLAC verify crashed")
        return FlacVerifyResult(error=f"unexpected error: {exc}")
