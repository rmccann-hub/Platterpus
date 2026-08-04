"""Adapter for the AccurateRip drive read-offset list.

Why this exists
---------------
whipper's own ``offset find`` is documented upstream as "primitive": it
rips trial offsets and compares them against AccurateRip *for the inserted
disc*, inside the Distrobox container. In practice it fails often — it
failed on a Pioneer BDR-209D even with a disc that IS in AccurateRip.

EAC and dBpoweramp don't probe a disc to learn the read offset at all.
They look it up by **drive model** in AccurateRip's published drive-offset
list. We already have the drive's vendor + model from ``whipper drive
list`` (``DriveDescriptor``), so we can resolve the correct offset with no
disc, no network round-trip, and no dependence on whipper's flaky probe.

Critical Rule #1 (adapters): AccurateRip's list is an external data source,
so access goes through this module. The bundled ``_CURATED_OFFSETS`` table
is a small, high-confidence subset kept **in code** (not as packaged data)
to dodge the AppImage package-data pitfalls that bit ``help_content``. A
user can extend/override it by dropping a CSV at
``~/.config/platterpus/drive_offsets.csv`` (``name,offset`` rows) — that's
the path to the full official list without a code change. See
docs/archive/offset-investigation-2026-06.md.

Safety: a wrong offset silently corrupts a rip, so this adapter only ever
*suggests* a value — the wizard prefills it and the user confirms (and can
cross-check against accuraterip.com). Nothing here writes config or rips.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from platterpus.paths import CONFIG_DIR

log = logging.getLogger(__name__)

# A user-supplied list (the full AccurateRip export, or hand additions),
# overlaid on top of the curated table. Same simple ``name,offset`` CSV
# shape the curated table uses once normalized.
USER_OFFSETS_PATH: Path = CONFIG_DIR / "drive_offsets.csv"


def canonical_token(s: str) -> str:
    """Uppercase, collapse internal whitespace, strip — the shared core.

    This is the *one* canonicalization primitive used everywhere a drive
    identity string becomes a stable key: the AccurateRip lookup key here AND
    the drive-profile fingerprint in ``drive_profiles.py``. Keeping it in one
    place means those keys can never silently disagree. Changing it is
    load-bearing — it would invalidate every stored fingerprint (which the
    profile store treats fail-safe: an unknown fingerprint just prompts a fresh
    confirm, never a wrong offset).
    """
    return re.sub(r"\s+", " ", s).strip().upper()


def normalize_combined(combined: str) -> str:
    """Canonicalize an already-joined ``"<vendor> <model>"`` string.

    Drops a leading ``ATAPI`` tag some drives prepend, collapses AccurateRip's
    ``" - "`` vendor/model separator (whipper reports the two as separate
    fields with no dash) and a leading ``"- "`` (vendorless entries), then
    applies :func:`canonical_token`. Split out from :func:`normalize_drive_name`
    so a *combined* string from another source — e.g. whipper.conf's decoded
    ``[drive:VENDOR%20MODEL]`` section id — can be canonicalized the same way.
    """
    # Some drives report "ATAPI   iHAS124   B" etc.; the ATAPI tag isn't
    # part of AccurateRip's name.
    combined = re.sub(r"^\s*ATAPI\b", " ", combined, flags=re.IGNORECASE)
    # AccurateRip's "<vendor>  - <model>" separator (spaces around a hyphen).
    # In-token hyphens like BD-RW / BDR-209D have no surrounding spaces, so
    # they're untouched.
    combined = re.sub(r"\s+-\s+", " ", combined)
    combined = re.sub(r"^\s*-\s+", "", combined)  # vendorless: leading "- "
    return canonical_token(combined)


def normalize_drive_name(vendor: str, model: str) -> str:
    """Canonicalize a drive's vendor+model into a single lookup key.

    Both AccurateRip's list and whipper derive the name from the drive's
    ATA/SCSI IDENTIFY strings, so they agree once whitespace and case are
    normalized. whipper notably emits double-spaced models (Pioneer's real
    output is ``BD-RW  BDR-209D``), so collapsing whitespace is essential.
    AccurateRip stores e.g. ``"PIONEER  - BD-RW   BDR-209D"`` while whipper
    reports vendor ``"PIONEER"`` + model ``"BD-RW  BDR-209D"`` — after this
    both become ``"PIONEER BD-RW BDR-209D"``.
    """
    return normalize_combined(f"{vendor} {model}")


# --- Curated, high-confidence offsets ---------------------------------------
#
# Keys are already normalized (see normalize_drive_name). Deliberately small:
# shipping a WRONG offset corrupts rips, so we include only widely-published,
# stable values — led by the Pioneer BD/DVD family this project is tested on
# (BDR-209D = +667 is user-confirmed real hardware). The full ~80k-row
# AccurateRip list is imported via the user CSV, not hard-coded here.
_CURATED_OFFSETS: dict[str, int] = {
    # Pioneer BD writers share the +667 read offset (tested: BDR-209D).
    "PIONEER BD-RW BDR-209D": 667,
    "PIONEER BD-RW BDR-209M": 667,
    "PIONEER BD-RW BDR-209U": 667,
    "PIONEER BD-RW BDR-S09": 667,
    "PIONEER BD-RW BDR-2090": 667,
    # Pioneer DVD writers (the classic DVR family) read at +48.
    "PIONEER DVD-RW DVR-220L": 48,
    # A couple of long-stable, very widely-cited values.
    "PLEXTOR CD-R PREMIUM": 30,
    "PLEXTOR DVDR PX-716A": 30,
}


class OffsetDatabase:
    """Maps a drive's vendor+model to its AccurateRip read offset.

    Construct via :meth:`load_default` for the bundled table overlaid with
    the user's CSV, or pass an explicit ``entries`` dict in tests.
    """

    def __init__(self, entries: dict[str, int]) -> None:
        # Keys are assumed already normalized.
        self._entries: dict[str, int] = dict(entries)

    @property
    def size(self) -> int:
        return len(self._entries)

    @classmethod
    def load_default(cls, user_path: Path = USER_OFFSETS_PATH) -> OffsetDatabase:
        """The full bundled AccurateRip list, overlaid with curated fixes and
        the user CSV (in that precedence: user > curated > bundled).

        The bundled list (`accuraterip_offsets_data`, ~4.8k drives) covers
        essentially every drive offline. `_CURATED_OFFSETS` is a tiny set of
        hand-verified values that can override a bundled entry; the user CSV
        overrides everything.
        """
        entries = _load_bundled()
        entries.update(_CURATED_OFFSETS)
        entries.update(_load_user_csv(user_path))
        return cls(entries)

    def lookup(self, vendor: str, model: str) -> int | None:
        """Return the known read offset for this drive, or None if unknown.

        Never raises — an unknown drive is a normal outcome the caller
        handles by falling back to disc-based detection or manual entry.
        """
        if not vendor and not model:
            return None
        key = normalize_drive_name(vendor, model)
        if key in self._entries:
            return self._entries[key]
        # Fallback: AccurateRip sometimes omits/duplicates the vendor token.
        # Try matching on the model tail (everything after the first token)
        # against keys' tails, but only when it's an unambiguous single hit,
        # so we never guess between two different drives.
        model_key = normalize_drive_name("", model)
        if model_key:
            matches = {v for k, v in self._entries.items() if k.endswith(model_key)}
            if len(matches) == 1:
                return next(iter(matches))
        return None


# --- Bundled full list ------------------------------------------------------


def _load_bundled() -> dict[str, int]:
    """Decode the bundled AccurateRip list (gzip+base64 in-code blob).

    Keys are already normalized at generation time (same `normalize_drive_name`
    the lookup uses), so loading is just decompress + split. Returns an empty
    dict if the data module is somehow unavailable — the curated table then
    still covers the tested hardware.
    """
    try:
        import base64
        import gzip

        from platterpus.adapters import accuraterip_offsets_data as _data

        csv = gzip.decompress(base64.b64decode(_data._BLOB)).decode("utf-8")
    except Exception:  # noqa: BLE001 — never let a bad blob break drive setup
        log.exception("could not load bundled drive-offset list")
        return {}

    entries: dict[str, int] = {}
    for line in csv.splitlines():
        key, _, value = line.partition(",")
        if key and value:
            try:
                entries[key] = int(value)
            except ValueError:
                continue
    return entries


# --- CSV loading ------------------------------------------------------------


# Deliberately NOT a regex. The obvious pattern for this row —
# `^\s*(?P<name>.+?)\s*,\s*(?P<offset>-?\d+)\s*$` — is **quadratic** in the line
# length: the lazy `.+?` and the `\s*` runs give the engine an enormous number of
# split points to backtrack through. Measured on a single long row:
#
#     500 chars → 0.38 ms · 1000 → 1.49 ms · 2000 → 5.95 ms · 3000 → 13.09 ms
#
# and before the `.strip()` above defused the all-whitespace case it was worse
# than quadratic (3000 chars → 13.8 SECONDS).
#
# That matters here specifically, and not because a CSV is big. This file is the
# documented way to install the **full official AccurateRip drive-offset export**,
# and `OffsetDatabase.load_default()` is called from `MainWindow.__init__` — i.e.
# **on the GUI thread, before the window is shown**. One pathological row in a
# user-edited file is a frozen startup with no window to look at, which is the
# project's never-block-the-GUI-thread rule broken by a regex rather than by a
# subprocess.
#
# `rpartition` does the same job in linear time (1.5 µs on the input that took
# 13 ms), splits on the LAST comma so a drive name containing one still parses,
# and is easier to read than the pattern it replaces.
def _parse_csv_row(line: str) -> tuple[str, int] | None:
    """Split a ``name,offset`` row. ``None`` for anything unparseable.

    Linear in the line length by construction — see the note above; this is a
    bounded-time replacement for a regex that was not.
    """
    name, separator, offset_text = line.rpartition(",")
    if not separator:
        return None
    name = name.strip()
    if not name:
        return None
    try:
        return name, int(offset_text.strip())
    except ValueError:
        return None


def _load_user_csv(path: Path) -> dict[str, int]:
    """Parse a user ``name,offset`` CSV into normalized entries.

    Tolerant by design (it's user-edited): blank lines, ``#`` comments, a
    header row, and malformed lines are skipped with a log note rather than
    raising — a broken row must never break drive setup.
    """
    try:
        # errors="replace" — the CSV is user-edited, so a file saved in Latin-1
        # is entirely plausible; a bad byte must skip a row, not break drive setup
        # (UnicodeDecodeError is a ValueError and slips past the OSError guard).
        text = path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return {}
    except OSError as exc:
        log.warning("could not read drive-offset CSV %s: %s", path, exc)
        return {}

    entries: dict[str, int] = {}
    skipped: list[str] = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        row = _parse_csv_row(line)
        if row is None:
            # LOG IT. The docstring above promised malformed rows "are skipped with
            # a log note"; the row-level skip logged nothing, so a user whose CSV
            # silently contributed nothing had no way to find out which line was
            # wrong. A doc claim a reader can rely on has to be true in the code.
            skipped.append(f"line {lineno}: {line[:120]!r}")
            continue
        name, offset = row
        if name.lower() in ("name", "drive"):  # header row
            continue
        # The name column is a full drive name; normalize with empty vendor
        # so it collapses whitespace/case the same way lookups do.
        entries[normalize_drive_name("", name)] = offset
    if skipped:
        # Bounded, and the bound is STATED — a list of 4,000 malformed rows must not
        # bury the log, and a silent truncation would read as "only 5 were wrong".
        shown = skipped[:5]
        more = (
            f" (+{len(skipped) - len(shown)} more)" if len(skipped) > len(shown) else ""
        )
        log.warning(
            "drive-offset CSV %s: skipped %d malformed row(s)%s: %s",
            path,
            len(skipped),
            more,
            "; ".join(shown),
        )
    if entries:
        log.info("loaded %d drive offsets from %s", len(entries), path)
    elif skipped:
        # Every row was bad. Say so plainly: "no offsets loaded" reads as "the file
        # was empty", which is a different problem with a different fix.
        log.warning(
            "drive-offset CSV %s contributed NO usable entries — all %d "
            "non-comment row(s) were malformed",
            path,
            len(skipped),
        )
    return entries
