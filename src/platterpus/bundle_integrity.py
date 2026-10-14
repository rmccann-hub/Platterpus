"""What an evidence bundle's manifest says about each member's BYTES.

`evidence_bundle` decides what goes into a bundle and writes it. This module
renders the part of its ``MANIFEST.txt`` that lets a receiver check the bytes
they extracted against the bytes we wrote: one SHA-256 per member, in
``sha256sum``'s own format (the cyanrip fork's round 32 lap 9 S8).

**Why it is its own module.** `evidence_bundle` is far past the ~300-line
cohesion heuristic and is held there by a ratchet
(``tests/test_critical_rules_are_enforced.py::test_no_oversize_module_grows``).
These blocks are a self-contained concern — given the finished list of included
members, say what can be checked about them — and need nothing of the bundle's
walking, filtering or budget, so they live here and `evidence_bundle` calls them.

Pure and Qt-free: it renders text from values it is handed.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    # Type-only: `evidence_bundle` imports this module, so a runtime import back
    # would be a cycle. Only the attributes are read here.
    from platterpus.evidence_bundle import BundleEntry

#: The heading of the manifest's hash section. A constant because a test and a
#: receiver both look for it, and a heading reworded in one place only is a
#: section that quietly stops being found.
SHA256_HEADING: Final[str] = "SHA-256 OF EVERY INCLUDED MEMBER"


def sha256sum_line(digest: str, name: str) -> str:
    r"""One line in exactly the format ``sha256sum`` writes and ``sha256sum -c`` reads.

    ``<64 hex>`` + TWO spaces + the name. GNU coreutils has one escape rule and we
    follow it rather than invent a second: a name containing a backslash or a
    newline is written with each one escaped (``\\`` and ``\n``) and the whole
    line prefixed with a single backslash, which is how ``sha256sum -c`` knows to
    unescape it. Without that, a member name with a newline in it would split
    into two lines and the second would read as a hash row of its own.
    """
    if "\\" in name or "\n" in name:
        escaped = name.replace("\\", "\\\\").replace("\n", "\\n")
        return f"\\{digest}  {escaped}"
    return f"{digest}  {name}"


def sha256_section(included: Sequence[BundleEntry]) -> list[str]:
    r"""The manifest's hash block: one ``sha256sum`` line per included member.

    **Why this exists** (the cyanrip fork's round 32 lap 9 S8, their data
    register's X7). The manifest gave every member's SIZE and no hash, so a
    receiver could check a filing only against the archive as it reached them —
    a member changed by an exporter, or in transit before the archive was hashed,
    was invisible. A hash computed by the SENDER, from the bytes it wrote, is the
    second witness.

    **Which bytes.** The bytes written into the archive: after the per-file cap
    (a bounded file is hashed WITH its inline elision marker, because that is
    what a receiver extracts) and after any export-time rewriting. So these
    check the members *as extracted*, never the files on the rig.

    **The format is ``sha256sum``'s own, at column 0**, so a receiver needs no
    parser of ours: extract the archive, then
    ``grep -E '^\\?[0-9a-f]{64}  ' MANIFEST.txt | sha256sum -c``. The block is
    NEW and comes after every block that existed before it; nothing above it
    changed shape, so a reader of the older manifest reads this one unchanged.

    ``MANIFEST.txt`` is not in the list and cannot be: a file cannot carry its own
    hash. The archive's hash, which the reader quotes, covers it.
    """
    lines = [
        "",
        f"{SHA256_HEADING} ({len(included)}), of the bytes written into this archive",
        "-" * 40,
        "  Each line is in sha256sum's format, so after extracting the archive:",
        "    grep -E '^\\\\?[0-9a-f]{64}  ' MANIFEST.txt | sha256sum -c",
        "  Computed from the bytes written, so a file kept head+tail is hashed",
        "  with its elision marker. MANIFEST.txt cannot hash itself; the",
        "  archive's own hash covers it.",
    ]
    hashed = [entry for entry in included if entry.sha256]
    lines += [sha256sum_line(entry.sha256, entry.name) for entry in hashed]
    unhashed = len(included) - len(hashed)
    if not included:
        lines.append("  (no member was included, so there is nothing to hash)")
    elif unhashed:
        # Every path that includes a member hashes it, so this is unreachable
        # today. It is here because "every member is hashed" is a completeness
        # claim, and a claim with no branch for being false cannot be caught
        # being false.
        lines.append(
            f"  {unhashed} included member(s) carry NO hash — this list is "
            "incomplete, and that is itself a finding"
        )
    return lines
