"""No live text names the ripper Platterpus used before cyanrip.

**Why this exists.** The maintainer, 2026-09-24: *"we dont use whipper any
more, so a sweep for any whipper references, file names, etc. we either need to
replacement with our cyanrip fork designation, or make them neutral."* The sweep
that answered it found about 2,000 mentions in 150 files, three months after the
backend was removed (KDD-18, 2026-06-30). Nothing had been checking, so every
comment written from memory of the old design kept the old name alive.

This file is the check. Every git-tracked text file is scanned, and each one is
in exactly one of three groups:

* **History** (:data:`_HISTORY`) — records of what happened, which stay as
  written because rewriting them would falsify them: the changelog's released
  sections, the session log, the archive, handshake laps already sent, the
  original brief, the locked rules file. Exempt, and listed by path.
* **Necessary literals** (:data:`_LITERALS`) — files that must spell the old
  name because it is a real name on disk or in data: the leftover folder and
  wrapper the uninstaller removes, the header the legacy-log detector matches,
  a token older versions wrote into saved drive profiles, a real log kept as a
  test fixture. Each has an exact count and a reason, and the count is a
  RATCHET: it may go down, never up, and a recorded count above the real one
  fails too, so there is never slack to grow into.
* **Everything else** — zero.

A mixed file (a live document that also carries dated history, such as
`PLANNING.md` with its decision log) is a literal entry with its count, not a
history exemption, so new mentions in its live sections still fail.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Final

REPO: Final[Path] = Path(__file__).resolve().parents[1]

#: The old ripper's name, assembled so this file's own source is not a hit.
_NAME: Final[re.Pattern[str]] = re.compile("whip" + "per", re.IGNORECASE)

#: Whole paths (or path prefixes ending in "/") that are history.
_HISTORY: Final[dict[str, str]] = {
    "CHANGELOG.md": "released entries record what shipped; rewriting them falsifies the record",
    "docs/session-log.md": "the dated chronology of every session",
    "docs/archive/": "retired investigations, kept as written",
    "docs/handshake/": "laps already sent to the fork are immutable",
    "docs/platterpus-research-brief-v2.1.md": "the original project brief",
    "CLAUDE.md": "the locked rules file; its mentions are dated history",
    "tests/test_no_previous_ripper_in_live_text.py": "this file",
}

#: File -> (exact count, why the name has to be spelled there). Measured on
#: 2026-09-24 after the sweep; every count may only go down.
_LITERALS: Final[dict[str, tuple[int, str]]] = {
    # --- Real names on disk or in data --------------------------------------
    "src/platterpus/paths.py": (
        2,
        "the leftover config folder and wrapper, spelled as on disk",
    ),
    "src/platterpus/ui/uninstall_dialog.py": (
        1,
        "tooltip names the real folder it deletes",
    ),
    "uninstall.sh": (
        7,
        "the leftover folder, wrapper and pre-rename folder names it removes",
    ),
    "src/platterpus/parsers/cyanrip_log.py": (
        1,
        "the legacy-log header regex matches the literal text",
    ),
    "src/platterpus/drive_profiles.py": (
        1,
        "token older versions wrote into saved drive profiles",
    ),
    # --- Citations of the upstream source a claim was read from -------------
    "src/platterpus/parsers/cd_info.py": (
        2,
        "citation: the upstream file the legacy parser was verified against",
    ),
    "src/platterpus/parsers/drive_list.py": (
        2,
        "citation: the upstream file the legacy parser was verified against",
    ),
    "src/platterpus/verdict.py": (
        2,
        "citation: the upstream file and lines a capability audit read",
    ),
    "docs/cyanrip-fork.md": (4, "citation URLs (upstream repository, plugin issue)"),
    "docs/eac-parity.md": (
        5,
        "third-party logchecker file names, a verbatim code quote, a citation URL",
    ),
    "docs/cyanrip-upstream.md": (
        3,
        "third-party function names and header quoted verbatim",
    ),
    # --- Real artifacts, kept verbatim --------------------------------------
    "tests/fixtures/rip_log_legacy_format.log": (
        1,
        "a real legacy-format log; its header line",
    ),
    "tests/fixtures/drive_list_pioneer_unconfigured.txt": (
        2,
        "real captured drive-list output",
    ),
    "tests/fixtures/README.md": (
        2,
        "attribution of the fixture to the project it came from",
    ),
    # --- Tests feeding or checking those literals ---------------------------
    "tests/test_config.py": (
        3,
        "a retired config key and backend value, as upgrade input",
    ),
    "tests/test_documented_ripper_flags_are_real.py": (
        2,
        "exemption regex for PLANNING's decision log, and its example",
    ),
    "tests/test_drive_profiles.py": (
        3,
        "the persisted token, and the check that the label omits the name",
    ),
    "tests/test_parity.py": (2, "the legacy-log header, as parser input"),
    "tests/test_parsers_cd_info.py": (
        1,
        "a real legacy disc-info line, as parser input",
    ),
    "tests/test_parsers_cyanrip_log.py": (
        2,
        "the legacy-log header, as discriminator input",
    ),
    "tests/test_parsers_eac_log.py": (1, "the legacy-log header, as parser input"),
    "tests/test_parsers_property.py": (1, "the legacy-log header, as parser input"),
    "tests/test_parsers_rip_log.py": (
        4,
        "the legacy-log header and the fixture's own creator line",
    ),
    "tests/test_ui_main_window.py": (
        2,
        "a real user's verbatim error text the read-toc branch is for",
    ),
    # --- Live documents that also carry dated history -----------------------
    # Mixed files are counted, not exempted, so their live sections stay clean:
    # a new mention anywhere in them fails.
    "PLANNING.md": (
        125,
        "the KDD decision log, plus exact leftover paths in the module map",
    ),
    "TASKS.md": (142, "completed rows and dated history; live rows were swept"),
    "DEPENDENCIES.md": (
        31,
        "struck-through rows, the HISTORICAL section and the dated review log",
    ),
    "README.md": (
        10,
        "exact leftover paths in the uninstall section and the paths table",
    ),
    "docs/test-plan.md": (
        10,
        "exact leftover paths in the uninstall and clean-slate checks",
    ),
    "docs/ux-design-principles.md": (2, "an exact leftover path, stated as not read"),
    "docs/platterpus-session-start.md": (5, "the body of a preserved bootstrap record"),
}


def _tracked_text_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout
    return [line for line in out.splitlines() if line]


def _is_history(path: str) -> bool:
    return any(
        path == key or (key.endswith("/") and path.startswith(key)) for key in _HISTORY
    )


def _counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    for rel in _tracked_text_files():
        if _is_history(rel):
            continue
        path = REPO / rel
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binary or unreadable: not text a person reads
        found = len(_NAME.findall(text))
        if found:
            counts[rel] = found
    return counts


def test_the_scan_examines_the_tree() -> None:
    """Floor: a scan that lists no files would pass by examining nothing."""
    assert len(_tracked_text_files()) > 500


def test_no_live_text_names_the_previous_ripper() -> None:
    counts = _counts()
    new = {path: n for path, n in counts.items() if path not in _LITERALS}
    grew = {
        path: (n, _LITERALS[path][0])
        for path, n in counts.items()
        if path in _LITERALS and n > _LITERALS[path][0]
    }
    assert not new and not grew, (
        "live text names the ripper Platterpus used before cyanrip. Say cyanrip, "
        "or describe it neutrally ('the ripper older versions used', 'legacy log "
        "format'):\n"
        + "".join(f"  {p}: {n}\n" for p, n in sorted(new.items()))
        + "".join(f"  {p}: {n} (allowed {a})\n" for p, (n, a) in sorted(grew.items()))
    )


def test_the_literal_counts_have_no_slack() -> None:
    """A recorded count above the real one is room to grow unnoticed."""
    counts = _counts()
    slack = {
        path: (allowed, counts.get(path, 0))
        for path, (allowed, _why) in _LITERALS.items()
        if counts.get(path, 0) < allowed
    }
    assert not slack, "record the real count (it may only go down): " + ", ".join(
        f"{p} recorded {a}, actually {n}" for p, (a, n) in slack.items()
    )


def test_every_exemption_names_something_that_exists() -> None:
    tracked = set(_tracked_text_files())
    for key in list(_HISTORY) + list(_LITERALS):
        if key.endswith("/"):
            assert any(p.startswith(key) for p in tracked), key
        else:
            assert key in tracked or (REPO / key).exists(), key


def test_the_scan_can_fail() -> None:
    """Non-vacuous: the pattern finds the name in any case."""
    assert _NAME.findall("Whip" + "per and WHIP" + "PER and whip" + "per") == [
        "Whip" + "per",
        "WHIP" + "PER",
        "whip" + "per",
    ]
