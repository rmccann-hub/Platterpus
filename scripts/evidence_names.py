"""Which name each member of an acceptance bundle is filed under (TASKS R16).

HR-2's evidence names are ASCII letters and digits, the run's prefix first
(``round34fullwholedisc.log``). These rules map a Full run's export to them, as
the 2026-10-14 and 2026-10-16 filings did by hand. A member they cannot name is
refused by the caller (``evidence_file.py``), never guessed.
"""

from __future__ import annotations

import re

#: Members kept under a fixed name, by their path inside the bundle.
FIXED: dict[str, str] = {
    "COMPONENTS.json": "components.json",
    "DIAGNOSTICS.txt": "diagnostics.txt",
    "MANIFEST.txt": "manifest.txt",
    "SETTINGS.json": "settings.json",
    "SOURCES.txt": "sources.txt",
    "session/run/report.json": "scriptreport.json",
    "session/run/transcript.txt": "transcript.txt",
    "session/run/rig-check/MANIFEST.txt": "rigcheckmanifest.txt",
    "session/run/rig-check/argv-probe-output.txt": "rigcheckargvprobeoutput.txt",
    "session/run/rig-check/argv-probe.json": "rigcheckargvprobe.json",
    "session/run/rig-check/ripper-version.txt": "rigcheckripperversion.txt",
}

#: Album folders by how their names begin, longest first (the Full run's folders).
ALBUMS: tuple[tuple[str, str], ...] = (
    ("derived wavpack", "derivedwavpack"),
    ("derived mp3", "derivedmp3"),
    ("derived wav", "derivedwav"),
    ("after cancel", "aftercancel"),
    ("cancel me", "cancelme"),
    ("permutations", "permutations"),
    ("secure reread", "securereread"),
    ("r16deemphoff", "deemphoff"),
    ("r16deemphon", "deemphon"),
)

#: An album member by how its file name ends.
ALBUM_FILES: tuple[tuple[str, str], ...] = (
    (" (EAC-compatible).log", "eac.log"),
    (".platterpus-securing-pass.txt", "securingpass.txt"),
    (".platterpus-addendum.txt", "addendum.txt"),
    (".platterpus.json", "report.json"),
    (".log", ".log"),
    (".cue", ".cue"),
)


SAFE_NAME = re.compile(r"[A-Za-z0-9.]+")


def skip_reason(rel: str) -> str | None:
    """Why a member is left out on purpose, or ``None`` to file it."""
    if rel.endswith(".png"):
        return "a screenshot: not text evidence"
    if rel == "session/transcript.txt":
        return "the same file as session/run/transcript.txt"
    return None


def staged_name(rel: str) -> str | None:
    """The filed name of a bundle member (without prefix), or ``None``."""
    if rel in FIXED:
        return FIXED[rel]
    if m := re.fullmatch(r"session/artifacts/\d+platterpus/log\.txt", rel):
        return "platterpusapplog.txt"
    if m := re.fullmatch(
        r"session/zz-applog-rotations/\d+platterpus/log\.txt\.(\d)", rel
    ):
        return f"platterpusapplog{m[1]}.txt"
    if m := re.fullmatch(r"session/artifacts/\d+platterpus/config\.toml", rel):
        return "config.toml"
    if m := re.fullmatch(r"session/run/cacheprobe\d*\.txt", rel):
        return "cacheprobe.txt"
    if m := re.fullmatch(r"session/run/tags(\d{4})\.txt", rel):
        return f"tags{m[1]}.txt"
    if m := re.fullmatch(
        r"ripperdiagnostics/cyanrip-diagnostics-(\w{1,40}?)(-securingpass)?\.json", rel
    ):
        return f"jrecord{m[1].lower()}{'securingpass' if m[2] else ''}.json"
    parts = rel.split("/")
    if len(parts) == 3 and parts[0] == "album":
        key = album_key(parts[1])
        for ending, suffix in ALBUM_FILES:
            if key and parts[2].endswith(ending):
                return f"{key}{suffix}"
    return None


def album_key(folder: str) -> str | None:
    if folder.startswith("full acceptance"):
        return "overwrite" if folder.endswith("_2_") else "wholedisc"
    for start, key in ALBUMS:
        if folder.startswith(start):
            return key
    return None
