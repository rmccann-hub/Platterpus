# SPDX-License-Identifier: GPL-3.0-only
"""Off-thread verification of the derived files (MP3 / WavPack / WAV).

The transcode writes a sibling ``01 - x.mp3`` / ``.wv`` / ``.wav`` next to each
``01 - x.flac`` master. This worker pairs each derived file back with its master
and hands them to ``adapters.derived_verify`` — a full-album decode per file, so
it must never run on the Qt GUI thread. MainWindow runs ``verify_rip_dir`` on a
**daemon thread** and reports the result via a queued signal, exactly like the
CTDB / FLAC-integrity verifiers (and deliberately NOT a joined ``QThread``: the
decode can outlast any ``closeEvent`` wait, and destroying a running ``QThread``
aborts the app — ``docs/architecture.md`` §3.2).

It waits for the post-rip thread (``wait_for``) to FINISH before reading, and it
never raises. That thread's last step is the transcode, so its ending is the
transcode's ending; tagging and cover art run before it, and a fetch can take
30 s. **Until 2026-10-26 the wait was a fixed 60 s**, shared with the CTDB and
FLAC verifiers, and on the 0.7.112 Full run of 2026-10-22 (run C) the MP3,
WavPack and WAV transcodes took 86 to 121 s. Each verify gave up first, found
no derived file, and recorded "no mp3 files found to verify" as if the
transcode had written none, while the files appeared a minute later. The wait
is now on the work's completion, under an overall deadline far above any real
transcode, and a deadline that does pass is recorded as exactly that
(:data:`TRANSCODE_WAIT_TIMED_OUT`), never as "no files".
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Final

from platterpus import rip_files
from platterpus.adapters.derived_verify import (
    DerivedVerifyResult,
    PcmHasher,
    verify_derived_files,
)
from platterpus.adapters.transcode import extension_for

log = logging.getLogger(__name__)

#: The longest we wait for the post-rip thread (tagging, cover art, then the
#: transcode) before giving up. A bound on the WAIT, not a guess at how long a
#: transcode takes: an hour is far above a whole disc's transcode (run C's took
#: 86 to 121 s for two tracks, most of it cover art) and still ends a wait on a
#: wedged thread. The transcode bounds each file itself (300 s, `transcode.py`).
TRANSCODE_DEADLINE_S: float = 3600.0
#: How often the wait looks up from the join to ask whether a newer rip started.
_POLL_S: float = 1.0
#: The ``error`` a verify records when the deadline passed with the transcode
#: still running. Distinct from "no files found", which is what it used to say.
TRANSCODE_WAIT_TIMED_OUT: Final[str] = "timed out waiting for the transcode to finish"


def _pair_derived_with_masters(
    rip_dir: Path, ext: str
) -> tuple[list[tuple[Path, Path]], int]:
    """Return ``([(derived, master)], expected)`` for the given extension.

    ``expected`` is the number of FLAC masters (one derived file per master is
    the goal); a derived file with no matching ``.flac`` master is skipped (it
    can't be bit-compared), and a master with no derived sibling is what makes
    ``len(pairs) < expected`` — i.e. the transcode was incomplete.
    """
    # The masters come from the rip's own record, not the folder listing (see
    # `platterpus.rip_files`): `expected` is "one derived file per master THIS rip
    # wrote". Counting the folder instead doubled it whenever an earlier attempt's
    # FLACs were still there, so a complete transcode reported as incomplete.
    # rip_files falls back to the old non-recursive glob — which also keeps
    # nested/other-album FLACs out of the count (#40) — and logs the fallback.
    masters = list(rip_files.rip_master_files(rip_dir).files)
    pairs: list[tuple[Path, Path]] = []
    for master in masters:
        derived = master.with_suffix(f".{ext}")
        if derived.exists():
            pairs.append((derived, master))
    return pairs, len(masters)


def verify_rip_dir(
    rip_dir: Path,
    fmt: str,
    *,
    wait_for: threading.Thread | None = None,
    still_current: Callable[[], bool] | None = None,
    hasher: PcmHasher | None = None,
    deadline_s: float = TRANSCODE_DEADLINE_S,
) -> DerivedVerifyResult | None:
    """Verify the derived ``fmt`` files under ``rip_dir``. Never raises.

    Intended to run OFF the GUI thread (it blocks until the transcode ends).
    ``wait_for`` is the post-rip thread (or None), waited for until it FINISHES,
    because its last step is the transcode; past ``deadline_s`` the result says
    :data:`TRANSCODE_WAIT_TIMED_OUT` and nothing is read. ``hasher`` is injected
    in tests; production decodes via host ``ffmpeg``.
    """
    transcode_ended = _wait_for_transcode(wait_for, deadline_s, still_current)

    # ABANDON rather than measure a folder that is no longer ours. See the
    # `still_current` note in the docstring: the launcher discards a stale
    # result, but the reading is what produced a false ERROR in the user's own
    # diagnostics. `None` means 'no verdict', which is the truth here.
    if still_current is not None and not still_current():
        log.info("derived verify of %s abandoned: a newer rip started", rip_dir)
        return None

    if not transcode_ended:
        # Not "no files found": the files may yet be written, and saying none
        # were is the defect this wait replaced (run C, 2026-10-22).
        log.warning(
            "derived verify of %s: %s after %.0fs",
            rip_dir,
            TRANSCODE_WAIT_TIMED_OUT,
            deadline_s,
        )
        return DerivedVerifyResult(
            fmt=fmt,
            error=f"{TRANSCODE_WAIT_TIMED_OUT} (waited {deadline_s:.0f}s)",
            timed_out_waiting_for_transcode=True,
        )

    ext = extension_for(fmt)
    if ext is None:
        # "flac" or anything not transcoded → nothing derived to verify.
        return DerivedVerifyResult(
            fmt=fmt, error=f"no derived files for format {fmt!r}"
        )

    pairs, expected = _pair_derived_with_masters(rip_dir, ext)
    try:
        return verify_derived_files(pairs, fmt=fmt, expected=expected, hasher=hasher)
    except Exception as exc:  # noqa: BLE001 — verify must always return a result
        log.exception("derived-file verify crashed")
        return DerivedVerifyResult(fmt=fmt, error=f"unexpected error: {exc}")


def _wait_for_transcode(
    wait_for: threading.Thread | None,
    deadline_s: float,
    still_current: Callable[[], bool] | None,
) -> bool:
    """Wait for the post-rip thread to end. True when it ended (or there was none).

    Joins in short slices so a newer rip ends the wait at once (the caller then
    abandons), and stops at ``deadline_s`` overall, returning False. Runs off the
    GUI thread; it is the verify's own daemon that blocks here.
    """
    if wait_for is None:
        return True
    deadline = time.monotonic() + max(deadline_s, 0.0)
    while wait_for.is_alive():
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        wait_for.join(min(remaining, _POLL_S))
        if still_current is not None and not still_current():
            return not wait_for.is_alive()
    return True
