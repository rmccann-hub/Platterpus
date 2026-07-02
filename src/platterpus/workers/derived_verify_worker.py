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

Like the others it joins the post-rip transcode thread first (``wait_for``) so it
never reads a derived file mid-write, and it never raises.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from platterpus.adapters.derived_verify import (
    DerivedVerifyResult,
    PcmHasher,
    verify_derived_files,
)
from platterpus.adapters.transcode import extension_for

log = logging.getLogger(__name__)

# The transcode (which WROTE the derived files) shares the post-rip metaflac
# thread; bound the wait so we never read a half-written derived file, without
# hanging forever on a wedged post-rip thread. Matches the CTDB/FLAC verifiers.
_SETTLE_TIMEOUT_S: float = 60.0


def _pair_derived_with_masters(
    rip_dir: Path, ext: str
) -> tuple[list[tuple[Path, Path]], int]:
    """Return ``([(derived, master)], expected)`` for the given extension.

    ``expected`` is the number of FLAC masters (one derived file per master is
    the goal); a derived file with no matching ``.flac`` master is skipped (it
    can't be bit-compared), and a master with no derived sibling is what makes
    ``len(pairs) < expected`` — i.e. the transcode was incomplete.
    """
    # Non-recursive: pair this album's masters (direct children) with their
    # sibling derived files. A recursive glob would count nested/other-album
    # FLACs as masters and inflate `expected`, wrongly reading the transcode as
    # incomplete (#40) — matches the CTDB/FLAC-verify enumeration.
    masters = sorted(rip_dir.glob("*.flac"))
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
    hasher: PcmHasher | None = None,
) -> DerivedVerifyResult:
    """Verify the derived ``fmt`` files under ``rip_dir``. Never raises.

    Intended to run OFF the GUI thread. ``wait_for`` is the post-rip transcode
    thread (or None): joined first so we never read a derived file mid-write.
    ``hasher`` is injected in tests; production decodes via host ``ffmpeg``.
    """
    if wait_for is not None and wait_for.is_alive():
        wait_for.join(_SETTLE_TIMEOUT_S)

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
