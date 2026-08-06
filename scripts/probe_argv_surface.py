#!/usr/bin/env python3
"""Black-box probe of OUR OWN outbound seam surface — the argv we hand the ripper.

## Why this script exists

``docs/seam-rules.md`` S-9 says limits and error behaviour are established by
**black-box testing, each side probing its own binary** — a limit read out of
someone else's documentation is a claim about behaviour nobody ran. We asked the
cyanrip fork for that in round 7 lap 29, and lap 29 admits in writing that our own
half was hand-transcribed rather than measured. This closes our half.

**What "our binary" means here.** The outbound seam is
:meth:`CyanripBackend._build_rip_argv` plus the chokepoint
:func:`assert_metadata_lookup_disabled`. Both are pure Python, so every cell S-9
asks for — the real accepted range, behaviour at min/max/one-past-each, and what a
bad value actually *does* — is measurable right here with no drive and no disc.

**What it deliberately does NOT probe.** Whether *cyanrip* accepts ``-S 999`` is
the fork's measurement to make, not ours (S-9). This script measures what we
**emit**, which is the half we own: does the flag appear, with what value, is it
silently dropped, or does the call die?

## The distinction that carries the most weight

For each probe the outcome is one of:

``emitted``
    the flag reached the argv with a value we record.
``dropped``
    the call succeeded and the flag is **absent**. This is the dangerous one — a
    silently ignored argument looks identical to one that was never configured,
    and it is exactly the cell S-9 demands be written down ("whether the
    operation dies or the flag is silently ignored").
``raised``
    the call refused, with the exception type and its message. A refusal is a
    *good* outcome for an out-of-range value, and the message is contract
    surface once it is recorded here.

A ``dropped`` outcome for a value the user explicitly set is a **finding**, not a
documented behaviour, and gets flagged in the summary.

## Output

Markdown to stdout, shaped for ``docs/seam-commands.md``. Generated, never
hand-edited — the whole point is that a hand-maintained description of behaviour
decays invisibly while the code moves.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))

from platterpus.adapters.cyanrip_backend import (  # noqa: E402
    CyanripImpl,
    assert_metadata_lookup_disabled,
)
from platterpus.adapters.rip_backend import RipError, RipMetadata  # noqa: E402

#: A call that is known-good, so every probe changes exactly one thing. A probe
#: that also perturbed the baseline could not attribute the outcome.
_BASELINE: Final[dict[str, Any]] = {
    "unknown": False,
    "cover_art": "",
    "max_retries": 5,
    "read_offset_override": 667,
    "track_template": "%d/%t - %n",
    "metadata": RipMetadata(album_title="Probe Album"),
}


@dataclass(frozen=True)
class Probe:
    """One measurement: a parameter set to a value, and what came out."""

    parameter: str
    value: str
    outcome: str
    detail: str

    @property
    def is_finding(self) -> bool:
        """True when this row is a defect rather than a documented behaviour.

        A value the caller explicitly set that vanishes without a refusal is the
        shape S-9 exists to surface. ``0``-as-auto is excluded: that is a
        documented convention, not a silent loss.
        """
        return self.outcome == "dropped" and not self.value.startswith("0")


def _probe_one(parameter: str, value: Any, *, flag: str) -> Probe:
    """Run one probe. Never raises — a probe that dies is a recorded outcome."""
    kwargs = dict(_BASELINE)
    kwargs[parameter] = value
    backend = CyanripImpl(binary_path="cyanrip")
    try:
        argv = backend._build_rip_argv("/dev/sr0", **kwargs)
    except RipError as exc:
        return Probe(parameter, repr(value), "raised", f"RipError: {exc}")
    except (TypeError, ValueError, OverflowError) as exc:
        return Probe(parameter, repr(value), "raised", f"{type(exc).__name__}: {exc}")
    if flag not in argv:
        return Probe(parameter, repr(value), "dropped", f"{flag} absent from argv")
    index = argv.index(flag)
    emitted = argv[index + 1] if index + 1 < len(argv) else "(no value)"
    # Every argv we build must still satisfy the chokepoint, whatever the probe
    # did. A probe value that could smuggle an argv past `-N` would be a far worse
    # finding than any range defect, so it is checked on EVERY row rather than
    # once at the end.
    try:
        assert_metadata_lookup_disabled(argv)
        guard = "chokepoint ok"
    except RipError as exc:
        guard = f"CHOKEPOINT REFUSED: {exc}"
    return Probe(parameter, repr(value), "emitted", f"{flag} {emitted} · {guard}")


#: The value grid. Each row is (parameter, flag it controls, values to try).
#: The values are chosen for S-9's boundary column: below-min, min, typical,
#: max-ish, one past, and the pathological cases that have actually bitten
#: (``-t 17=`` on a 16-track disc killed a rip in two seconds).
_GRID: Final[tuple[tuple[str, str, tuple[Any, ...]], ...]] = (
    ("max_retries", "-r", (-1, 0, 1, 5, 100, 10_000, 2**31)),
    ("read_speed", "-S", (-1, 0, 1, 4, 48, 999, 2**31)),
    ("secure_rerip_matches", "-Z", (-1, 0, 1, 2, 10, 1000)),
    ("read_offset_override", "-s", (-2000, -667, 0, 667, 5000, 2**31)),
)


def probe_all() -> list[Probe]:
    """Run the whole grid. Deterministic and side-effect free."""
    results: list[Probe] = []
    for parameter, flag, values in _GRID:
        for value in values:
            results.append(_probe_one(parameter, value, flag=flag))
    return results


def render(probes: Sequence[Probe]) -> str:
    """The markdown table, plus the findings summary.

    The summary is not decoration: S-11 requires three numbers reported every
    round, and a table nobody totals is a table nobody reads.
    """
    lines: list[str] = [
        "<!-- GENERATED by scripts/probe_argv_surface.py — do not hand-edit. -->",
        "",
        "### Measured outbound behaviour (black-box, our own surface)",
        "",
        "Each row is one probe of `_build_rip_argv`: one parameter changed against a",
        "known-good baseline, and what actually reached the argv. `dropped` means the",
        "call succeeded and the flag is **absent** — a silently ignored argument,",
        "which is the outcome S-9 most wants written down.",
        "",
        "| parameter | value | outcome | what happened |",
        "|---|---|---|---|",
    ]
    for probe in probes:
        mark = " ⚠" if probe.is_finding else ""
        lines.append(
            f"| `{probe.parameter}` | `{probe.value}` | **{probe.outcome}**{mark} "
            f"| {probe.detail} |"
        )
    emitted = sum(1 for p in probes if p.outcome == "emitted")
    dropped = sum(1 for p in probes if p.outcome == "dropped")
    raised = sum(1 for p in probes if p.outcome == "raised")
    findings = [p for p in probes if p.is_finding]
    refused = [p for p in probes if "CHOKEPOINT REFUSED" in p.detail]
    lines += [
        "",
        f"**{len(probes)} probes: {emitted} emitted, {dropped} dropped, "
        f"{raised} raised.**",
        "",
        f"**Silently-dropped non-zero values (findings): {len(findings)}**"
        + (
            " — none. Every value a caller set either reached the argv or was refused."
            if not findings
            else ": " + ", ".join(f"`{p.parameter}={p.value}`" for p in findings)
        ),
        "",
        f"**Chokepoint refusals across every probe: {len(refused)}** — "
        + (
            "none, so no probe value can smuggle an argv past the `-N` guard."
            if not refused
            else "SEE ABOVE, this is a safety defect."
        ),
    ]
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fail-on-findings",
        action="store_true",
        help="exit non-zero if any non-zero value is silently dropped",
    )
    args = parser.parse_args(argv)
    probes = probe_all()
    sys.stdout.write(render(probes))
    if args.fail_on_findings and any(p.is_finding for p in probes):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
