"""One finished album's post-rip phase, as an object that owns it.

**Why this module exists, in one sentence:** every per-album fact the rip report
needs used to live on the *window* as a `_last_*` attribute, and the window's
lifetime is "the current rip" — so each of those facts moved under its readers
the moment the next rip started.

That is not a theory. It is three measured defects in two days, all the same
shape and all found on hardware:

* **2026-09-14** — the report's ``settings`` block was rebuilt from the live
  config on every write, so the one rip whose post-rip chain finished got its
  settings read six seconds late and its report described a configuration that
  rip never ran under: ``output_format: "flac"`` for a WAV rip, with its own
  ``verification.derived`` saying ``wav`` two lines below.
* **2026-09-15 (morning)** — the post-rip chain's steps each returned out of the
  daemon when a newer rip started, so both derived-format transcodes were
  dropped and **no `.mp3` or `.wv` file was written at all**, under a report
  that said ``✓ Bit-perfect``.
* **2026-09-15 (afternoon)** — the MP3 rip's whole chain *succeeded*, and every
  result was discarded: they landed **655 ms** before the next Start, against a
  750 ms debounce on the report write, and the Start path cleared the very
  fields the pending write would have read.

Each was fixed where it was found. The shape underneath all three is the same
and was never fixed: **an album's facts were stored on an object that is about
to describe a different album.** `main_window_rip.py`'s own comments describe it
without naming it — *"a `_last_*` snapshot, like every other fact the report
needs after the worker is gone"* — snapshotting a disappearing owner's facts onto
an owner that is itself about to move.

So: the album owns its facts. A :class:`PostRipRecord` is opened when a rip
*starts*, filled in when it finishes, holds everything that rip's report is built
from, and stays addressable after the next rip begins — which is what lets a late result be
recorded against the album it actually belongs to instead of being dropped for
fear of contaminating the next one.

**What this module deliberately does NOT own.** Session-level facts —
``environment``, the dependency report, the log buffer — are not per-album and
stay on the window. Copying them here would be the same mistake mirrored: a
value duplicated into a shorter-lived container goes stale the other way.

No Qt imports. This is a plain data object so it can be built, inspected and
asserted against without a window, which is also why its rules are testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:  # pragma: no cover — annotations only
    from platterpus.read_speed_ladder import SpeedAttempt
    from platterpus.report_types import RetriedTrackBlock, TimingBlock

#: Which ``verification.gates`` key each post-rip result feeds, and the record
#: attribute holding that result.
#:
#: **One table, because the two halves of the question — "was this check meant to
#: produce something?" and "did it?" — were previously answered in different
#: modules by different keys**, which is how a gate and its own result came to
#: disagree inside one document. A reader that wants either answer comes here.
GATE_RESULTS: Final[dict[str, str]] = {
    "ctdb": "ctdb",
    "flac_integrity": "flac_verify",
    "derived": "derived_verify",
}


@dataclass
class PostRipRecord:
    """Everything one finished album's report is built from.

    Created at rip finish, mutated as post-rip checks land, and kept addressable
    after the next rip starts so a late result can still be written into the
    album it describes.

    ``generation`` is the rip-generation counter the album was ripped under. It
    is the record's identity: a result carries the generation it was launched
    with, so it can always find its own record even once the window has moved on.
    """

    # --- identity: what album is this, and which rip produced it ------------
    generation: int
    #: ``None`` until the rip finishes and its log is parsed. A record exists from
    #: the moment a rip starts — that is when its settings are frozen — so there is
    #: never a window in which a post-rip result has no record to land on, and
    #: "which album is this?" has one answer rather than a guard at each caller.
    #: Nothing is written to disk while this is ``None``.
    log_file: Path | None = None
    rip_log: object = None

    # --- frozen at Start: what the rip was ASKED to do ----------------------
    #
    # Frozen rather than read back, because reading them later is defect #1
    # above. `settings` already has the effective read offset folded in — that
    # is a fact about this rip rather than a setting that can drift.
    settings: dict[str, object] = field(default_factory=dict)
    gate_inputs: dict[str, bool] = field(default_factory=dict)

    # --- captured at finish: what the rip DID -------------------------------
    outcome: dict[str, object] | None = None
    disc: dict[str, object] | None = None
    timing: TimingBlock | None = None
    secure_rerip: dict[str, object] | None = None
    eta_trace: list[object] | None = None
    ripper_stdout: str = ""
    ripper_log_verification: object | None = None
    disc_track_total: int | None = None
    speed_attempts: list[SpeedAttempt] = field(default_factory=list)
    unstable_tracks: list[int] = field(default_factory=list)
    retried_tracks: list[RetriedTrackBlock] = field(default_factory=list)
    #: This rip's slice of the session log, as an ``(epoch_start, epoch_end)``
    #: pair. Held here because a later album's finish replaces the window's copy,
    #: and a rewrite of *this* report must still exclude other albums' lines and
    #: keep its own.
    rip_window: tuple[float, float] | None = None

    # --- accumulated as post-rip checks land --------------------------------
    ctdb: object | None = None
    flac_verify: object | None = None
    transcode: object | None = None
    derived_verify: object | None = None
    recompress: object | None = None
    cover_art: object | None = None
    tagging: object | None = None
    checksums: dict[str, str] | None = None
    audio_md5: dict[str, str] | None = None

    # --- the post-rip ledger ------------------------------------------------
    #: Checks launched for this album and not yet back, by gate key. Registered
    #: at the single launcher chokepoint so the ledger cannot drift from what
    #: actually ran.
    pending: set[str] = field(default_factory=set)
    #: Checks a newer rip cut short. A gate is only moved here when the check was
    #: genuinely launched AND produced no result — both halves matter, in both
    #: directions (see :meth:`seal_superseded`).
    superseded: set[str] = field(default_factory=set)

    def seal_superseded(self) -> set[str]:
        """Mark the checks that were begun for this album and never came back.

        Returns the newly-sealed gate keys, so the caller can log them.

        A check counts as superseded only when it was actually launched *and* no
        result arrived. Requiring both matters in each direction: the first stops
        a rip that never reached its post-rip phase from reporting checks as
        "interrupted", and the second stops a check that landed microseconds
        before the next Start from being labelled dropped when its result is
        sitting right here.
        """
        dropped = {
            gate
            for gate, attr in GATE_RESULTS.items()
            if gate in self.pending and getattr(self, attr, None) is None
        }
        self.superseded |= dropped
        return dropped

    def missing_results(self) -> set[str]:
        """Gate keys whose check was meant to run and holds no result.

        The record's own answer to the question the report's backstop asks. Kept
        here so *"did this album get the checks it was promised?"* has one
        implementation rather than one per reader.
        """
        return {
            gate
            for gate, attr in GATE_RESULTS.items()
            if self.gate_inputs.get(_GATE_INPUT_FOR[gate], False)
            and getattr(self, attr, None) is None
        }


#: Which ``gate_inputs`` flag decides whether each gate's check was requested.
#: Separate from :data:`GATE_RESULTS` because the *request* and the *result* are
#: different facts — conflating them is the defect `verification.gates` exists to
#: prevent, and the one it re-created by deriving every state from config alone.
_GATE_INPUT_FOR: Final[dict[str, str]] = {
    "ctdb": "ctdb_enabled",
    "flac_integrity": "flac_verify_enabled",
    "derived": "transcode_requested",
}
