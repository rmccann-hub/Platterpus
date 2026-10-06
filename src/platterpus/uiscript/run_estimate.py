"""How long an acceptance run should take, said when it starts (TASKS D6).

The operator's first wording of the 2026-10-05 request: an overall estimate for
the acceptance run. The per-rip half exists (``rip_estimate``); this sums it over
the script's rips and adds the other steps. The parts, each with its source:

* each ``rip`` the chosen size runs: ``rip_estimate.estimate_rip`` for the tracks
  selected, at the settings the script has set by then (read with the runner's
  value parsers and the real ``apply_preset``), from this drive's reading speed.
  Low is the main pass; high is every read at the retry ceiling and, in dynamic
  mode, every track re-read too: a bound, not a forecast;
* each ``wait N``: N seconds, capped as the runner caps it;
* every other step, per section: what it took on the filed 2026-10-05 Full run
  (:data:`MEASURED_OTHER_S`, re-derived from the committed report by a test);
* the runner's pause between steps (``TICK_MS``).

**Tri-state: unknown is not zero.** A rip with no estimate (no track length yet,
or no measured speed) and a section no filed run had are counted and NAMED, and
the figure becomes "at least". Pure; the window reader is
``estimate_verbs.estimate_for_window``, which never raises.
"""

from __future__ import annotations

import dataclasses
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from platterpus import rip_estimate
from platterpus.config import Config
from platterpus.goal_presets import GOAL_CUSTOM, apply_preset
from platterpus.rip_estimate import ReadRate, rough
from platterpus.uiscript import run_sizes
from platterpus.uiscript.script import Step
from platterpus.uiscript.script_values import coerce_setting, parse_track_spec
from platterpus.user_settings import with_values

#: The filed run the non-rip figures come from, and its date.
MEASURED_FROM: Final[str] = (
    "docs/handshake/artifactsround30/round30oct05fullscriptreport.json"
)
MEASURED_ON: Final[str] = "2026-10-05"

#: Seconds each section's steps took on that run, leaving out ``rip``,
#: ``wait-for-rip`` (the rips, estimated instead) and ``wait`` (read from the
#: script instead). Whole seconds. ``""`` is the preamble before section A.
#: ``tests/test_uiscript_run_estimate.py`` re-derives this from the report.
MEASURED_OTHER_S: Final[dict[str, float]] = {
    "": 0.0,
    "A": 2.0,
    "B": 0.0,
    "C": 0.0,
    "D": 1.0,
    "E": 8.0,
    "F": 27.0,
    "G": 1.0,
    "H": 5.0,
    "I": 1.0,
    "J": 13.0,
    "K1": 9.0,
    "K2": 6.0,
    "K3": 6.0,
    "K4": 0.0,
    "L": 0.0,
    "M": 0.0,
    "N": 29.0,
    "P": 9.0,
    "P2": 6.0,
    "P3": 363.0,
    "Q": 0.0,
}

#: Every Config field a ``set`` line may name.
_CONFIG_FIELDS: Final[frozenset[str]] = frozenset(
    f.name for f in dataclasses.fields(Config)
)

#: The verbs that state a run's shape (the runner's ``_STRUCTURAL_VERBS``): a run
#: size never declines them. Tied to the runner's set by a test.
STRUCTURAL_VERBS: Final[frozenset[str]] = frozenset({"tier", "needs", "run-size"})


@dataclass(frozen=True)
class RunEstimate:
    """The parts of an acceptance run's estimate, known and unknown."""

    run_size: str
    #: Rip steps the size runs, and how many of them have an estimate.
    rips: int
    rips_estimated: int
    rips_low_s: float
    rips_high_s: float
    #: Why the rest have none ("" when every rip has one).
    rip_unknown_reason: str
    waits_s: float
    measured_s: float
    ticks_s: float
    #: Sections the run includes that the filed run never had.
    unmeasured: tuple[str, ...]
    rate: ReadRate | None

    @property
    def complete(self) -> bool:
        """True when nothing that will run was left out of the figure."""
        return self.rips_estimated == self.rips and not self.unmeasured

    @property
    def low_s(self) -> float:
        return self.rips_low_s + self.waits_s + self.measured_s + self.ticks_s

    @property
    def high_s(self) -> float:
        return self.rips_high_s + self.waits_s + self.measured_s + self.ticks_s


def _rip_cost(
    config: Config,
    selection: list[int] | None,
    lengths: Mapping[int, float],
    rate: ReadRate | None,
) -> tuple[float, float] | str:
    """``(low, high)`` seconds for one rip, or why it has no estimate."""
    if not lengths:
        return "no track length is known yet (the disc is not identified)"
    wanted = sorted(lengths) if selection is None else selection
    missing = [n for n in wanted if n not in lengths]
    if missing or not wanted:
        return f"no length is known for track(s) {missing or wanted}"
    audio = sum(lengths[n] for n in wanted)
    est = rip_estimate.estimate_rip(
        audio,
        rate,
        secure_rerip_matches=config.secure_rerip_matches,
        dynamic=config.secure_rerip_dynamic,
        max_retries=config.max_retries,
    )
    if est is None:
        return "this drive's reading speed is not known (it has finished no rip here)"
    high = est.seconds_high if est.seconds_high is not None else est.seconds
    if est.reread_high is not None:
        high += est.reread_high * audio
    return est.seconds, high


def estimate_run(
    steps: Sequence[Step],
    *,
    run_size: str,
    config: Config,
    track_lengths: Mapping[int, float],
    rate: ReadRate | None,
    tick_s: float,
    wait_cap_s: float,
    start_index: int = 0,
) -> RunEstimate:
    """The estimate for ``steps[start_index:]``, as the runner would run them.

    Every step from the first is walked, because a ``run-size`` or a ``set``
    before ``start_index`` decides what the later steps do; only steps from
    ``start_index`` on are counted. A step the size declines does nothing, as in
    the runner, so its ``set`` lines do not apply either.
    """
    declared: str | None = None
    section = ""
    selection: list[int] | None = None
    counted: set[str] = set()
    unmeasured: list[str] = []
    rips = estimated = 0
    low = high = waits = measured = ticks = 0.0
    reason = ""
    for index, step in enumerate(steps):
        if not step.ok:
            continue
        verb, args = step.verb, step.args
        header = verb == "log" and step.joined().startswith("--- ")
        if header:
            section = step.joined().strip("- ").split(".", 1)[0].strip()
        if verb == "run-size" and args:
            declared = run_sizes.parse_size(args[0])
        if not (
            verb in STRUCTURAL_VERBS or header or run_sizes.includes(run_size, declared)
        ):
            continue
        counting = index >= start_index
        if counting:
            ticks += tick_s
        if verb == "set" and len(args) >= 2 and args[0] in _CONFIG_FIELDS:
            value, problem = coerce_setting(
                getattr(config, args[0]), " ".join(args[1:])
            )
            if not problem:
                config = with_values(config, {args[0]: value})
                if args[0] == "rip_goal" and value != GOAL_CUSTOM:
                    config = apply_preset(config, str(value))
        elif verb == "select-tracks" and args:
            spec = args[0].strip().lower()
            if spec == "all":
                selection = None
            elif spec == "none":
                selection = []
            else:
                numbers, problem = parse_track_spec(spec)
                selection = numbers if not problem else selection
        if not counting or verb in STRUCTURAL_VERBS or header:
            continue
        if verb == "rip":
            rips += 1
            cost = _rip_cost(config, selection, track_lengths, rate)
            if isinstance(cost, str):
                reason = reason or cost
            else:
                estimated += 1
                low, high = low + cost[0], high + cost[1]
            continue
        if verb == "wait" and args:
            try:
                seconds = float(args[0])
            except ValueError:
                seconds = 0.0
            waits += min(max(seconds, 0.0), wait_cap_s) if math.isfinite(seconds) else 0
            continue
        if section not in counted:
            counted.add(section)
            if section in MEASURED_OTHER_S:
                measured += MEASURED_OTHER_S[section]
            else:
                unmeasured.append(section)
    return RunEstimate(
        run_size,
        rips,
        estimated,
        low,
        high,
        reason,
        waits,
        measured,
        ticks,
        tuple(unmeasured),
        rate,
    )


def describe(est: RunEstimate) -> str:
    """One sentence for the transcript, the console and the log.

    "about" only when nothing that will run was left out; otherwise "at least",
    with what was left out named after it, because a floor read as a forecast is
    the figure a tired operator plans the night around.
    """
    other = est.measured_s + est.waits_s + est.ticks_s
    measured = f"measured on the {MEASURED_ON} Full run, plus this script's waits"
    missing: list[str] = []
    if est.rips and not est.rips_estimated:
        sentence = (
            f"Run estimate ({est.run_size}): no total yet, because its {est.rips} "
            f"rip(s) have no figure: {est.rip_unknown_reason}. The other steps take "
            f"at least {rough(other)} ({measured})"
        )
    else:
        word = "about" if est.complete else "at least"
        sentence = f"Run estimate ({est.run_size}): {word} {rough(est.low_s)}"
        if est.high_s > est.low_s:
            sentence += (
                f", up to {rough(est.high_s)} if reads disagree and tracks need "
                "re-reading at the retry ceiling"
            )
        multiple = est.rate.multiple if est.rate is not None else None
        if est.rips and est.rate is not None and multiple:
            basis = (
                f"this drive's own speed over {est.rate.rips} rip(s)"
                if est.rate.rips > 0
                else "the speed the project's rig measured for this drive model"
            )
            sentence += (
                f": {est.rips_estimated} rip(s) about {rough(est.rips_low_s)} at "
                f"{1 / multiple:.1f}x ({basis}), and the other steps "
                f"{rough(other)} ({measured})"
            )
        else:
            sentence += f": no rips, and the steps {rough(other)} ({measured})"
        if est.rips_estimated < est.rips:
            missing.append(
                f"{est.rips - est.rips_estimated} rip(s), because "
                f"{est.rip_unknown_reason}"
            )
    if est.unmeasured:
        missing.append(
            f"section(s) {', '.join(s or 'preamble' for s in est.unmeasured)}, "
            "never measured on a filed run"
        )
    if missing:
        sentence += "; NOT counted, so the figure is a floor: " + "; ".join(missing)
    return sentence + "."
