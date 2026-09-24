"""Whether a read offset reaches the ripper, and how to say what it is.

A bit-perfect rip needs the drive's read offset. cyanrip (the sole backend)
reads no config file of its own — the GUI passes the offset as `-s N` at rip
time, and only while ``Config.override_read_offset`` is on. So the GUI's own
config is the one source, set in the drive-setup wizard (from the AccurateRip
drive list, or by hand).

**No other file is consulted.** Until 2026-09-24 this module also read a
leftover per-drive offset from the config file of the ripper Platterpus used
before cyanrip (KDD-18), as a reference line in the drive wizard and
``--doctor`` and as a seed for the drive ledger. cyanrip never read that file,
nothing written since 2026-06-30 put an offset there, and a reference to a
value that cannot reach the ripper is a second number for the same fact —
which is the shape this project removes wherever it finds it. The maintainer
asked for it gone (2026-09-24). The uninstaller still removes the file if it is
there (`deps/host_teardown.py`), because cleaning up is not reading.

Pure; no I/O.
"""

from __future__ import annotations


def is_offset_configured(override_read_offset: bool) -> bool:
    """True only if an offset will ACTUALLY reach the ripper.

    cyanrip (the sole backend, KDD-18) reads no config file — it only receives
    the offset from the GUI's ``-s N``, emitted solely when
    ``Config.override_read_offset`` is set. Treating anything else as
    "configured" (a leftover offset in another program's config, as an older
    version once did) made the rip preflight skip *both* the AccurateRip-list
    auto-apply *and* the setup wizard, and the rip then ran at offset 0 — a
    silent wrong-offset rip.
    """
    return bool(override_read_offset)


def describe_applied_offset(read_offset: int, override_read_offset: bool) -> str:
    """What the next rip does with the read offset, in one line. Pure.

    Shared by Settings (which shows it read-only) and Setup & Updates (beside
    *Set up drive…*), so the two can never word the same fact differently. The
    offset has ONE home, the drive-setup wizard, and these are views of it.

    It states only what the config says. "Not applied" is not "zero": with the
    tick-box off no ``-s`` reaches cyanrip at all, which for most drives is not
    bit-perfect, so the sentence says that rather than showing a bare ``+0``.
    """
    if override_read_offset:
        return f"{read_offset:+d} samples, applied to every rip"
    return "not applied: no read offset is passed to the ripper"
