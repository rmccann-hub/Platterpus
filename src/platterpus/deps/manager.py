"""The DependencyManager — single presence/version probe for brief P0 #11.

Walks the registry, runs each spec's probe, and classifies each dependency as
present-and-current or missing. Returns a `DependencyReport` for UI display.

`check_all()` is idempotent: calling it twice with no system changes produces
an identical report; calling it after a successful install reflects the new
state of the world immediately.

**Resolution (installing what's missing) is NOT here.** It's inherently GUI-
coupled — each tier opens a different dialog (consent, live-progress install,
manual search string) and the install must run off the GUI thread — so it lives
in `ui/main_window_deps._resolve_missing_unified`, reusing the tier resolver
classes in `deps/resolvers.py` (`AutoInstaller` + the install dialogs). The
manager once carried a parallel `resolve_missing` tier-cascade; it was unused in
production (the GUI always routed itself) and removed so there is a single
resolution path (Critical Rule #6). The presence/version logic — the part the
rule requires be centralized — stays here.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from platterpus.deps.build_notes import BuildNote
from platterpus.deps.checks import ProbeResult, probe_deadline
from platterpus.deps.registry import SPECS, DependencySpec
from platterpus.deps.resolvers import InstallResult, MissingItem
from platterpus.deps.version import meets_minimum

log = logging.getLogger(__name__)

#: The whole check's budget, in seconds, when the GUI runs it.
#:
#: One probe is bounded at 60 s (`checks._PROBE_TIMEOUT_S`) so a cold ripping
#: container has time to start. But seven specs run in a row and cyanrip tries two
#: version flags, so a wedged container meant ~7 minutes before the user saw any
#: result at all (2026-09-28). 120 s is two cold starts' worth: enough for the
#: first probe to start the container and every later one to find it warm, and
#: short enough that "the check is stuck" is said while the user is still looking.
CHECK_DEADLINE_S: float = 120.0

#: Why a check stopped by its caller left tools unchecked. The window cancels the
#: check only while it is closing, so the sentence says that.
_CANCELLED_REASON: str = (
    "the check was cancelled before it reached them (Platterpus was closing)"
)


def _deadline_reason(deadline_s: float) -> str:
    """Why a check stopped by its deadline left tools unchecked, for a person."""
    return (
        f"the check stopped after {deadline_s:g} s because it was taking too long. "
        "The ripping container may still be starting, or it may be stuck"
    )


@dataclass
class DependencyReport:
    """Result of a check_all() pass.

    - `ok`: specs that probed present and met the minimum version.
    - `missing`: items that didn't, with the probe attached.
    - `ok_versions`: dep_id → detected version (or None) for the `ok`
      specs, so the report can tell the user *which* version they have,
      not just that the dep is present.
    - `ok_probes`: dep_id → the full ProbeResult for the `ok` specs, so a
      consumer (the rip report's `environment.dependencies`) can record
      *where* each tool was found (`probe.location`), not only its version.
    - `install_results`: outcomes from any resolution attempts during
      this run (empty after a pure check that didn't try to resolve).
    - `build_notes`: dep_id → which *build* of that tool is installed, for
      the specs that can tell (today: cyanrip fork vs stock vs unknown). A
      dep is absent from this map when its spec has no `build_note`, which
      is the normal case — "no note" means "the version is the whole story",
      never "the build is fine".
    """

    ok: list[DependencySpec] = field(default_factory=list)
    missing: list[MissingItem] = field(default_factory=list)
    ok_versions: dict[str, tuple[int, ...] | None] = field(default_factory=dict)
    ok_probes: dict[str, object] = field(default_factory=dict)
    install_results: list[InstallResult] = field(default_factory=list)
    build_notes: dict[str, BuildNote] = field(default_factory=dict)
    #: When this probe finished, ISO-8601 UTC to the second. ``""`` for a report
    #: that never ran a probe (a test double, or one built by hand). A version is
    #: a fact about the moment it was measured, and a tool can be updated under a
    #: running app, so every surface that shows a version shows this beside it.
    measured_at: str = ""
    #: Specs this pass never got an answer for, because the check stopped early —
    #: its overall deadline passed, or its caller cancelled it. **Neither present
    #: nor missing**, and never to be rendered as either: before this field a
    #: stopped check returned `ok` and `missing` as far as it had got, with no
    #: marker, so a summary could say "all present" after probing two tools of
    #: seven. Empty for a check that reached every spec.
    unchecked: list[DependencySpec] = field(default_factory=list)
    #: Why `unchecked` is non-empty, as a clause for a person ("the check stopped
    #: after 120 s because…"). ``""`` when nothing was skipped.
    unchecked_reason: str = ""

    @property
    def complete(self) -> bool:
        """True when this pass reached every spec it was asked to probe."""
        return not self.unchecked

    @property
    def build_attention(self) -> list[tuple[DependencySpec, BuildNote]]:
        """OK deps whose installed *build* is not the one Platterpus wants.

        Separate from `missing` on purpose. A stock cyanrip is present, current
        and rips discs — routing it into the missing/install flow would be a
        lie and would offer an install for something already installed. It is
        nonetheless a thing the user must be told, because it silently changes
        what their archival log can claim. So it is its own category, counted
        and shown separately.
        """
        return [
            (spec, note)
            for spec in self.ok
            if (note := self.build_notes.get(spec.dep_id)) is not None
            and note.needs_attention
        ]

    @property
    def all_resolved(self) -> bool:
        """True if everything probed OK or was successfully installed."""
        if self.unchecked:
            # A tool we never asked about is not resolved, whatever the rest say.
            return False
        if self.missing == [] and self.install_results == []:
            return True
        # When resolution happened, success requires every previously-
        # missing item to have a matching success in install_results.
        installed_ok = {r.spec.dep_id for r in self.install_results if r.success}
        return all(item.spec.dep_id in installed_ok for item in self.missing)


class DependencyManager:
    """Single entry point for "are all my dependencies good?"."""

    def __init__(self, specs: list[DependencySpec] | None = None) -> None:
        """Construct with an optional custom spec list.

        Tests pass their own spec list (so they don't depend on the real
        registry); `specs=None` picks up `registry.SPECS`, which is what
        `app.py` and the GUI's `_build_gui_dependency_manager` use.
        """
        self._specs = specs if specs is not None else SPECS

    def check_all(
        self,
        cancelled: Callable[[], bool] | None = None,
        deadline_s: float | None = None,
    ) -> DependencyReport:
        """Probe every registered dependency. Pure check — no installs.

        ``cancelled`` is polled **between** specs. That is complementary to, not a
        substitute for, killing the running probe: the flag cannot interrupt a probe
        already blocked in a container exec, and killing the child cannot stop the
        loop from starting the next one. Both are needed for a cancel to be prompt
        (see `deps.checks.cancel_version_probes`), and either alone is the false
        promise CLAUDE.md rule 9 forbids.

        ``deadline_s`` bounds the WHOLE pass (the GUI passes `CHECK_DEADLINE_S`;
        ``None``, the default, keeps the old unbounded behaviour for `--doctor` and
        the tests). It is enforced where the waiting happens, not where the check
        was scheduled: every probe's own timeout is capped to the time left, so the
        in-flight child is killed at the deadline, and no probe starts after it
        (`deps.checks.probe_deadline`); and it is re-checked before each spec.

        **A stopped check says so.** It returns what it measured, plus
        ``report.unchecked`` — every spec it did not get an answer for — and
        ``report.unchecked_reason``. A spec whose probe came back empty-handed
        *after* the stop is unchecked, not missing: the kill that stopped it is
        our doing, and reporting it as a missing tool would send the user to the
        setup wizard for something that may be installed. (The safe direction,
        and the one it errs in: a genuinely absent tool whose answer lands in the
        same instant as the deadline reads "not checked" rather than "missing" —
        which asks for a re-check instead of offering a needless install.)
        """
        report = DependencyReport()
        deadline_at = None if deadline_s is None else time.monotonic() + deadline_s
        deadline_reason = "" if deadline_s is None else _deadline_reason(deadline_s)

        def stop_reason() -> str:
            """Why the pass must stop now, or ``""`` to carry on."""
            if deadline_at is not None and time.monotonic() >= deadline_at:
                return deadline_reason
            if cancelled is not None and cancelled():
                return _CANCELLED_REASON
            return ""

        with probe_deadline(deadline_at):
            for index, spec in enumerate(self._specs):
                reason = stop_reason()
                if reason:
                    self._stop_early(report, index, reason)
                    break
                probe = spec.probe()
                log.debug(
                    "probe %s: present=%s version=%s",
                    spec.dep_id,
                    probe.present,
                    probe.version,
                )
                if probe.present and meets_minimum(probe.version, spec.min_version):
                    _record_ok(report, spec, probe)
                    continue
                # Asked AGAIN after the probe returned, because the stop may have
                # happened while it ran — and then its "absent" is the kill's doing.
                reason = stop_reason()
                if reason:
                    self._stop_early(report, index, reason)
                    break
                report.missing.append(MissingItem(spec=spec, probe=probe))
        report.measured_at = _now_iso()
        return report

    def _stop_early(self, report: DependencyReport, index: int, reason: str) -> None:
        """Mark spec ``index`` and every spec after it as not checked, and log it."""
        report.unchecked = list(self._specs[index:])
        report.unchecked_reason = reason
        log.warning(
            "dependency check stopped after %d of %d specs — %s. Not checked: %s",
            index,
            len(self._specs),
            reason,
            ", ".join(spec.dep_id for spec in report.unchecked),
        )


def _record_ok(
    report: DependencyReport, spec: DependencySpec, probe: ProbeResult
) -> None:
    """File a spec that probed present and new enough, with its version and build."""
    report.ok.append(spec)
    report.ok_versions[spec.dep_id] = probe.version
    # Keep the whole probe (adds `location`) for the rip report's
    # environment.dependencies — ok_versions alone loses where it was.
    report.ok_probes[spec.dep_id] = probe
    if spec.build_note is None:
        return
    # Pure function over text we already captured — but it is third-party-derived
    # text, so a surprise in it must not take down the whole dependency check. A
    # note we could not compute is simply absent, and the version still shows.
    try:
        note = spec.build_note(probe)
    except Exception:  # noqa: BLE001 - see below
        # Deliberately broad, and deliberately not a bare `except:`: this is a
        # display-only enrichment, and any exception here would otherwise abort a
        # check the user needs. Logged with a traceback so it is diagnosable.
        log.exception(
            "build-note probe for %s raised; continuing without it", spec.dep_id
        )
    else:
        report.build_notes[spec.dep_id] = note
        log.info("dependency %s build: %s (ok=%s)", spec.dep_id, note.summary, note.ok)


def _now_iso() -> str:
    """Now, ISO-8601 UTC to the second: when a probe's versions were measured."""
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat(timespec="seconds")


# --- The most recent probe, so every surface can answer the same question ----
#
# Two surfaces report "what tools is this running on": the rip report's
# `environment.dependencies`, and the Diagnostics dialog a user pastes into a
# bug report. Only the first one could — `build_info.environment_report()`
# returns exactly python/platform/pyside6/install_channel and has never carried
# a `dependencies` key, while the window attaches one from its own
# `_last_dependency_report`. The dialog called `environment_report()` directly
# and then asked it for `dependencies`, so it always got None and always printed
# *"not probed yet this session — the launch-time check had not completed, or it
# crashed"* — on every machine, in every session, including the 2026-09-22
# acceptance run whose own rip reports list all seven tools with versions and
# paths, and whose transcript shows a dependency check completing in section D.
#
# The message was right to exist and its branch was unreachable-from-true: it
# explained an absence with a cause that could not be checked. So the probe
# result lives HERE, in the subsystem Critical rule #6 says owns it, and both
# surfaces read it through `build_info.dependency_summary` — one summariser, two
# callers, which is the shape that stops them describing one machine two ways.
#
# Process-global on purpose and stated plainly: it is "the last probe THIS
# PROCESS ran", it is None until one runs, and it is not persisted. Tests reset
# it by remembering None.
_LATEST_REPORT: DependencyReport | None = None


def remember_report(report: DependencyReport | None) -> None:
    """Record the newest probe result for later readers. Never raises."""
    global _LATEST_REPORT
    _LATEST_REPORT = report


def latest_report() -> DependencyReport | None:
    """The newest probe this process ran, or None if none has.

    None is a real answer — "no check has completed yet" — and is never to be
    rendered as "no dependencies".
    """
    return _LATEST_REPORT


# --- "Which tools were not checked, and why" — one answer for every surface ----
#
# The summary popup, the Setup & Updates line, the status bar, Help → About and
# Diagnostics all have to say the same thing about an incomplete check, and each
# of them used to be able to say "all present" about one. Reading it through these
# two functions is what stops five surfaces wording one fact five ways. Both take
# `object` and use `getattr`, like `build_info.dependency_summary`, so a test
# double or a report from before this field existed reads as complete.


def unchecked_names(report: object) -> list[str]:
    """The display name of every spec ``report`` did not check, in probe order."""
    return [
        str(getattr(spec, "display_name", None) or getattr(spec, "dep_id", "?"))
        for spec in (getattr(report, "unchecked", None) or [])
    ]


def describe_unchecked(report: object) -> str:
    """One sentence naming what ``report`` did not check and why; ``""`` if nothing.

    ``""`` for a complete check *and* for no report at all: "not checked yet" is
    a different fact, which each surface already states in its own words.
    """
    names = unchecked_names(report)
    if not names:
        return ""
    reason = str(getattr(report, "unchecked_reason", "") or "") or (
        "the check stopped before it reached them"
    )
    return (
        f"Check incomplete — {len(names)} not checked: {', '.join(names)} ({reason})."
    )
