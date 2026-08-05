"""Embed a rip's companion **text** files inside the JSON report.

Why this exists: the ``.platterpus.json`` is meant to be the one file a user
uploads when something looks wrong. It very nearly was — it already carries the
settings, the environment, the per-track results and the whole session log —
but the three artifacts that sit *beside* it were not in it, so every real
diagnosis so far has started with "can you also send me the .log?". The
maintainer's instruction was blunt and correct: *"just assume I can only upload
the json file, put all [the tests] in there that you need"* (2026-08-01).

What goes in:

* ``rip_log`` — cyanrip's own per-track log. The primary artifact; it is where
  the pre-gap LSNs, the AccurateRip confidences and the loudness live.
* ``eac_log`` — our rendered EAC-layout companion. Worth embedding *separately*
  from the rip log even though it is derived from it: it is the file the user
  archives and the one whose *rendering* has now been wrong twice, and a
  derived artifact is only checkable if you can see both sides.
* ``cue`` — the cue sheet. A zero-byte cue after a cancelled rip is the kind of
  thing that is invisible in a summary and obvious in a byte count.

**Text only, and the extension allowlist is the guard, not a convention.**
Critical rule #8 forbids audio ever entering an artifact we hand around, and
"the caller passes the right path" is not a guarantee — a future caller can
pass a ``.flac`` by mistake and this must refuse rather than base64 an album
into a bug report. A rejected path is still *recorded* (with its reason), so
the refusal is visible instead of looking like an absent file.

Absence is data. A file that isn't there gets ``exists: false`` rather than
being omitted, because "cyanrip wrote no cue" and "Platterpus didn't look for
one" are different findings and a missing key cannot tell them apart.

Never raises: this runs inside the report builder, which runs in a rip's finish
path. An unreadable file degrades to a recorded error.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from platterpus.report_types import ArtifactEntry, ArtifactsBlock

log = logging.getLogger(__name__)

# Per-artifact cap. A 14-track cyanrip log is ~60 KB and our EAC render ~8 KB,
# so this is roughly 8x the largest thing we expect while still bounding a
# pathological case (a marathon re-rip log) to something a user can actually
# attach to an issue. Over the cap we keep the HEAD, not the tail: a rip log's
# header carries the drive, offset, paranoia level and disc identity, and
# losing those costs more than losing the last tracks.
MAX_ARTIFACT_BYTES: int = 512 * 1024

# The only suffixes we will read into the report. Deliberately narrow, and
# deliberately not "anything that isn't audio" — an allowlist fails closed when
# a format nobody thought about shows up.
EMBEDDABLE_SUFFIXES: frozenset[str] = frozenset(
    {".log", ".cue", ".txt", ".toc", ".m3u", ".m3u8", ".json"}
)


def build_artifact(path: Path | None) -> ArtifactEntry:
    """Describe one companion file, embedding its text. Never raises.

    Returns a dict that always answers the same questions in the same shape, so
    a reader never has to distinguish "key missing" from "file missing":

    * ``path`` — where it was looked for (``None`` if the caller had no path)
    * ``exists`` / ``bytes`` / ``sha256`` — is it there, how big, and a digest
      of the **bytes on disk** (not of the possibly-truncated text below, which
      would be a digest of something no file ever contained)
    * ``truncated`` — True when ``text`` is only the first
      :data:`MAX_ARTIFACT_BYTES`
    * ``text`` — the contents, UTF-8 with replacement so a stray byte cannot
      cost us the whole artifact
    * ``error`` — present only when something went wrong (unreadable, or a
      suffix we refuse to embed), naming the reason
    """
    if path is None:
        return {"path": None, "exists": False}
    p = Path(path)
    entry: ArtifactEntry = {"path": str(p), "exists": False}
    if p.suffix.lower() not in EMBEDDABLE_SUFFIXES:
        # Not an assertion or an exception: refusing loudly in the artifact is
        # more useful than crashing a rip's finish path, and it keeps the
        # rule-#8 guard visible in the output it protects.
        entry["error"] = (
            f"refusing to embed “{p.suffix}” — the report embeds text artifacts "
            f"only ({', '.join(sorted(EMBEDDABLE_SUFFIXES))})"
        )
        log.warning("refused to embed non-text artifact in the rip report: %s", p)
        return entry
    try:
        data = p.read_bytes()
    except OSError as exc:
        # A missing file is the common, uninteresting case; anything else is
        # worth a log line. Both land in the report either way.
        entry["error"] = str(exc)
        if not isinstance(exc, FileNotFoundError):
            log.warning("could not embed %s in the rip report: %s", p, exc)
        return entry
    entry["exists"] = True
    entry["bytes"] = len(data)
    entry["sha256"] = hashlib.sha256(data).hexdigest()
    truncated = len(data) > MAX_ARTIFACT_BYTES
    entry["truncated"] = truncated
    entry["text"] = data[:MAX_ARTIFACT_BYTES].decode("utf-8", errors="replace")
    return entry


def build_text_artifact(text: str | None, *, label: str) -> ArtifactEntry:
    """Wrap already-in-memory text as an artifact entry. Never raises.

    Some artifacts never touch the filesystem — the ripper's captured stdout is
    the important one. It is the only record that survives the ripper being
    killed (its logfile is block-buffered; its stdout is a pipe we are already
    draining), so it must reach the report even though there is no path to read.

    ``path`` is None and a ``source`` names where it came from, so a reader can
    tell an in-memory capture from a file that happened to be missing.
    """
    if not text:
        return {"path": None, "exists": False, "source": label}
    data = text.encode("utf-8", errors="replace")
    truncated = len(data) > MAX_ARTIFACT_BYTES
    return {
        "path": None,
        "exists": True,
        "source": label,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "truncated": truncated,
        "text": data[:MAX_ARTIFACT_BYTES].decode("utf-8", errors="replace"),
    }


def build_artifacts(
    *,
    rip_log: Path | None = None,
    eac_log: Path | None = None,
    cue: Path | None = None,
    addendum: Path | None = None,
    ripper_stdout: str | None = None,
) -> ArtifactsBlock:
    """Build the report's ``artifacts`` block from the three companion paths.

    Keyword-only and explicitly named rather than taking a free-form mapping:
    the report's wire format is pinned by tests and consumed by future readers,
    so the set of embedded artifacts should be a deliberate change here, not
    whatever a call site happened to pass. Never raises.
    """
    return {
        "note": (
            "Verbatim text of the files written beside this report, so this "
            "one file is enough to diagnose a rip without asking for the "
            "others. Text only — never audio (see CLAUDE.md critical rule #8)."
        ),
        "rip_log": build_artifact(rip_log),
        # The kill-proof one. When `rip_log.text` is short and this is long, the
        # difference is exactly what the ripper failed to flush.
        "ripper_stdout": build_text_artifact(
            ripper_stdout,
            label="captured from the ripper's stdout (progress "
            "redraws excluded); complete even when the ripper was killed",
        ),
        "eac_log": build_artifact(eac_log),
        "cue": build_artifact(cue),
        # THE AUTO-FIX ADDENDUM, and it was missing until 2026-08-05 — while the
        # `note` above promised "this one file is enough to diagnose a rip without
        # asking for the others". It is the one companion that **supersedes** the
        # ripper's log: when a track is re-ripped, the log keeps the DISCARDED
        # read's CRCs (it must stay byte-exact for `cyanrip --verify-log`) and this
        # file states what actually shipped. Omitting it meant the report embedded
        # the superseded values verbatim and not the correction.
        #
        # Found by the maintainer asking "why can that not be put in the json
        # file?" — a question about placement that turned out to be about absence.
        "addendum": build_artifact(addendum),
    }
