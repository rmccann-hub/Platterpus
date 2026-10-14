"""Home-folder paths become ``~`` when evidence is exported — counted, never silent.

**Why this exists.** The cyanrip fork's round 32 lap 9 S10 (their data register's
X9): when they filed our 2026-10-13 acceptance bundle they had to replace home
paths (``/var/home/<name>/…``) in nine of its files, because the repository
owner's rule of 2026-10-12 keeps personal details out of anything newly
committed, and names *export* tools as well as filing ones. A bundle is an
artifact that leaves this machine and gets posted publicly, so the export is the
right place for the replacement: once, by the program that wrote the files,
rather than by every receiver by hand.

**What is replaced, and how it is known rather than guessed.** A home folder is
recognised by its SHAPE, with the same pattern the fork's own helper uses
(``cyanrip@aa45b975:tools/redact.py:55-58``), so the two projects replace the
same strings: ``/home/<name>``, ``/var/home/<name>`` (the real home on an
rpm-ostree system such as Bazzite, the rig's), ``/Users/<name>`` and
``C:\\Users\\<name>`` all become ``~``, with whatever follows kept. No list of
user names is needed, so none is written anywhere. On top of the shape, this
machine's own home is replaced exactly, which catches a home that is not under
``/home`` (``/root``, a custom ``$HOME``).

**What is NOT replaced, and why each exclusion is a property of the bytes.**

* **A member whose bytes are signed.** A cyanrip log ends in a ``Log FUN512:``
  line, and ``cyanrip --verify-log`` (``-Y``) checks that every byte above it is
  the byte cyanrip wrote; the fork says so in their own helper (*"A cyanrip log
  also stops verifying with -Y once a path inside it changes"*,
  ``cyanrip@aa45b975:tools/redact.py:46-47``). Our EAC-compatible log carries our
  own checksum footer, the SHA-256 of the text above it (``eac_log_export``).
  Replacing a path in either would make a genuine log fail its own check — and a
  log that fails its check is worse evidence than a log that names a folder. So
  such a member is written **byte for byte**, and the manifest names it with the
  number of home paths it still carries and the reason. The receiver can
  redact after verifying, which is exactly what the fork's ingester does
  (``cyanrip@aa45b975:tools/ingest-bundle.py:555-560``: ``-Y`` on the original,
  then replace).
* **A line beginning ``HANDSHAKE-``**: a wire value of the shared handshake
  protocol, which the owner's rule leaves alone unless both sides agree. Copied
  unchanged and counted, the fork's rule word for word
  (``cyanrip@aa45b975:tools/redact.py:40-43``).
* **Hostnames and the owner's name**, which the fork's helper also replaces.
  S10 asked for home paths; a hostname is not recognisable by its shape, and
  inventing a detector for one is a different change. The manifest says so, so
  "not replaced" cannot read as "not present".

**It never raises and never decodes lossily.** Bytes are decoded with
``surrogateescape``, which round-trips ANY byte sequence exactly, so a member that
is not valid UTF-8 (a log cut mid-character by the size cap, say) still has its
ASCII paths replaced and every other byte returned untouched. The fork's helper
returns non-UTF-8 input unchanged with a zero count, which reports *no paths* for
a file it did not look at; reading the bytes we can read is the honest version.

Pure and Qt-free: no disk access, so every case is a unit test.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Final

log = logging.getLogger(__name__)

#: A home folder by its shape — the fork's ``HOME_PATH``, byte for byte
#: (``cyanrip@aa45b975:tools/redact.py:55-58``), so a bundle we export and a bundle
#: they file replace the same strings. The lookbehind keeps an already-replaced
#: ``~/…`` and a path embedded in a longer word (``x/home/y``) from matching; the
#: name stops at the next separator or quoting character.
HOME_PATH: Final[re.Pattern[str]] = re.compile(
    r"(?<![\w.~-])(?:/var)?/home/[^/\s\"'<>|:;,)\]]+"
    r"|(?<![\w.~-])/Users/[^/\s\"'<>|:;,)\]]+"
    r"|\b[A-Za-z]:\\\\?Users\\\\?[^\\\s\"'<>|:;,)\]]+"
)

#: A wire value of the shared handshake protocol; left exactly as it is.
WIRE_LINE: Final[re.Pattern[str]] = re.compile(r"^HANDSHAKE-[A-Z0-9-]+:")

#: cyanrip's log signature line. The same pattern the fork's ingester keys its
#: ``-Y`` check on (``cyanrip@aa45b975:tools/ingest-bundle.py:367``), so a log we
#: keep as written is exactly a log they would verify.
SIGNED_CYANRIP_LOG: Final[re.Pattern[str]] = re.compile(r"^Log FUN512: \S+$", re.M)

#: The replacement, the fork's and the shell's spelling of "the home folder".
PLACEHOLDER: Final[str] = "~"

#: Why a cyanrip log is kept byte for byte. Stated in the manifest beside it.
KEPT_CYANRIP_SIGNED: Final[str] = (
    "kept as written: signed by cyanrip (its `Log FUN512:` line), and "
    "`cyanrip --verify-log` checks only the bytes cyanrip wrote, so replacing a "
    "path would make a genuine log fail its own check"
)

#: Why our EAC-compatible log is kept byte for byte.
KEPT_PLATTERPUS_CHECKSUM: Final[str] = (
    "kept as written: it ends in Platterpus's own log checksum (the SHA-256 of "
    "the text above it), so replacing a path would make it fail that check"
)


@dataclass(frozen=True)
class Redaction:
    """What :func:`redact_member` did to one member. Never an exception."""

    #: The bytes to write — the input, unchanged, when nothing was replaced.
    data: bytes
    #: Home paths replaced with ``~``.
    replaced: int = 0
    #: Non-empty when the member was deliberately kept as written; says why.
    kept_reason: str = ""
    #: Home paths still present in a member kept as written (zero otherwise).
    left_in_place: int = 0
    #: ``HANDSHAKE-`` lines copied unchanged although they named a home folder.
    wire_lines_kept: int = 0
    #: False only when the member could not be examined at all, so its zero
    #: counts mean "not looked at", never "none found".
    examined: bool = True


def this_machines_homes() -> list[str]:
    """This machine's home folder as ``$HOME`` names it AND as it resolves.

    Both, because they differ on exactly the rig this matters for: on an
    rpm-ostree system `/home` is a link to `/var/home`, so a path written through
    one spelling and a home read through the other would not match. Never
    raises: a machine with no determinable home gets the shape-based replacement
    alone, which still covers `/home/<name>` and `/var/home/<name>`.
    """
    try:
        home = Path.home()
    except (RuntimeError, KeyError, OSError):
        log.warning("could not determine the home folder; shape-based only")
        return []
    homes = [str(home)]
    try:
        homes.append(str(home.resolve()))
    except OSError:
        log.warning("could not resolve the home folder %s", home, exc_info=True)
    return homes


def _exact_home_patterns(homes: Sequence[str]) -> list[re.Pattern[str]]:
    """One pattern per home folder this machine is known to have, longest first.

    A home that is ``/`` or relative is skipped: replacing ``/`` would rewrite
    every absolute path in the bundle, which is not a home folder being hidden
    but a bundle being destroyed. The lookahead stops ``/root`` matching inside
    ``/rootfs``.
    """
    usable: set[str] = set()
    for home in homes:
        candidate = (home or "").rstrip("/")
        if not candidate.startswith("/") or len(PurePosixPath(candidate).parts) < 2:
            continue
        usable.add(candidate)
    return [
        re.compile(
            r"(?<![\w.~/-])" + re.escape(home) + r"(?=$|[/\s\"'<>|:;,)\]])",
            re.M,
        )
        for home in sorted(usable, key=len, reverse=True)
    ]


def redact_text(text: str, *, homes: Sequence[str] = ()) -> tuple[str, int, int]:
    """``(text with home folders replaced, replacements, wire lines kept)``.

    Line by line, so a ``HANDSHAKE-`` line can be copied unchanged. ``keepends``
    makes the join reproduce every original line ending, so a member whose only
    change is a path differs from its source only at that path.
    """
    exact = _exact_home_patterns(homes)
    replaced = 0
    wire_kept = 0
    out: list[str] = []
    for line in text.splitlines(keepends=True):
        if WIRE_LINE.match(line):
            if HOME_PATH.search(line) or any(p.search(line) for p in exact):
                wire_kept += 1
            out.append(line)
            continue
        for pattern in exact:
            line, count = pattern.subn(PLACEHOLDER, line)
            replaced += count
        line, count = HOME_PATH.subn(PLACEHOLDER, line)
        replaced += count
        out.append(line)
    return "".join(out), replaced, wire_kept


def count_home_paths(text: str, *, homes: Sequence[str] = ()) -> int:
    """How many home paths :func:`redact_text` WOULD replace in ``text``."""
    return redact_text(text, homes=homes)[1]


def signed_reason(text: str) -> str:
    """Why ``text`` must be kept byte for byte, or ``""`` when it need not be.

    Judged by CONTENT, never by file name: a cyanrip log is recognised by its
    signature line, and our EAC-compatible log by the checksum footer the module
    that writes it verifies — asked of that module, so the two cannot disagree
    about what the footer looks like.
    """
    if SIGNED_CYANRIP_LOG.search(text):
        return KEPT_CYANRIP_SIGNED
    from platterpus.eac_log_export import verify_eac_style_log_checksum

    if verify_eac_style_log_checksum(text) is not None:
        return KEPT_PLATTERPUS_CHECKSUM
    return ""


def redact_member(data: bytes, *, homes: Sequence[str] = ()) -> Redaction:
    """Replace home folders in one text member's bytes. Never raises.

    ``surrogateescape`` both ways, so bytes that are not UTF-8 come back exactly
    as they went in and only the ASCII paths around them change.
    """
    try:
        text = data.decode("utf-8", errors="surrogateescape")
        reason = signed_reason(text)
        if reason:
            return Redaction(
                data=data,
                kept_reason=reason,
                left_in_place=count_home_paths(text, homes=homes),
            )
        new, replaced, wire_kept = redact_text(text, homes=homes)
        if not replaced:
            return Redaction(data=data, wire_lines_kept=wire_kept)
        return Redaction(
            data=new.encode("utf-8", errors="surrogateescape"),
            replaced=replaced,
            wire_lines_kept=wire_kept,
        )
    except Exception:  # noqa: BLE001 — an export must still write the member
        # Unreachable by construction (surrogateescape round-trips every byte),
        # and here because "never raises" is a claim with a branch for being
        # false. The member is written unchanged and the log says it was not
        # examined, so a zero count cannot read as "no paths found".
        log.warning("could not examine a bundle member for home paths", exc_info=True)
        return Redaction(
            data=data,
            kept_reason="kept as written: it could not be examined for home paths",
            examined=False,
        )
