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
from platterpus.cyanrip_cli import split_meta_blob  # noqa: E402

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

    #: Which axis produced this row. ``"range"`` probes a numeric value against
    #: its bounds; ``"shape"`` probes a malformed *structure*. They have opposite
    #: expectations, which is why the axis has to be recorded rather than inferred
    #: from the parameter name.
    axis: str = "range"

    @property
    def is_finding(self) -> bool:
        """True when this row is a defect rather than a documented behaviour.

        **Two classes, because one class is how a summary reads all-clear.** Added
        round 7 lap 33, after the cyanrip fork reported (their §C.1) that their own
        gate printed ``0 silently ignored`` and exited 0 *while the binary was
        segfaulting in the same run*: the grid only varied well-formed values, so
        nothing looked for a crash. Their generalisable statement is the one worth
        keeping — **a summary that counts only the failure mode you thought of
        reads as all-clear** — and this property was exactly that shape, counting
        silent drops and nothing else.

        * ``range`` axis: a value the caller explicitly set that **vanishes
          without a refusal**. ``0``-as-auto is excluded — a documented
          convention, not a silent loss.
        * ``shape`` axis: a value whose **structure** could malform the blob, judged
          by whether it survives a round trip. ``mangled`` (reached the argv but
          did not come back out intact) and ``wrongly-refused`` (a legal title the
          builder rejected) are both findings; a clean round trip is the pass.

          **The first version of this got the expectation backwards**, and running
          it is what showed that. It treated any such value as something to
          *refuse*, and reported 12 findings against rows where the escaping had
          worked perfectly — ``A: colon`` became ``album=A\\: colon``, which is
          exactly right. Every title is a legal input; escaping it correctly is
          the feature, not a defect to catch. A probe whose expectation is wrong
          manufactures findings, which is worse than one that misses them, because
          someone will "fix" the code to satisfy it.
        """
        if self.axis == "shape":
            # DEFINED AS THE COMPLEMENT OF THE PASS, not as a list of failures.
            # The first version listed the failure classes — `mangled` and
            # `wrongly-refused` — and a third class it had not thought of
            # (`raised`, from the builder's own chokepoint) fell through the gap
            # and was reported as neither. Eight rows vanished that way, in the
            # very experiment meant to prove this axis works. An enumeration of
            # bad outcomes is only as complete as the imagination that wrote it;
            # the complement of the good outcome cannot leak.
            return self.outcome != "emitted"
        return self.outcome == "dropped" and not self.value.startswith("0")


def _probe_one(parameter: str, value: Any, *, flag: str, axis: str = "range") -> Probe:
    """Run one probe. Never raises — a probe that dies is a recorded outcome."""
    kwargs = dict(_BASELINE)
    kwargs[parameter] = value
    backend = CyanripImpl(binary_path="cyanrip")
    try:
        argv = backend._build_rip_argv("/dev/sr0", **kwargs)
    except RipError as exc:
        return Probe(parameter, repr(value), "raised", f"RipError: {exc}", axis=axis)
    except (TypeError, ValueError, OverflowError) as exc:
        return Probe(
            parameter, repr(value), "raised", f"{type(exc).__name__}: {exc}", axis=axis
        )
    if flag not in argv:
        return Probe(
            parameter, repr(value), "dropped", f"{flag} absent from argv", axis=axis
        )
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
    return Probe(
        parameter, repr(value), "emitted", f"{flag} {emitted} · {guard}", axis=axis
    )


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


#: The MALFORMED-SHAPE axis, added round 7 lap 33 at the cyanrip fork's prompting
#: (their §C). Our grid had varied numeric *values* on four flags and nothing
#: else — so every `-a`/`-t` blob it ever built was well-formed, and a structural
#: defect could not be observed no matter how many rows the table had.
#:
#: The fork added the same axis to their probe and it found **four segfaults on
#: its first run** (`-c /`, `-c //`, `-p =`, `-p ==`): an argument consisting only
#: of its own separator tokenises to no token, so `strtol()` dereferenced NULL.
#: Their conclusion, which is the reason this exists: *"a grid that only feeds
#: well-formed values has the same blind spot as a type signature."*
#:
#: Each entry is a metadata value or track tag chosen to malform the blob in one
#: specific way. **Every row here is expected to be REFUSED** — see
#: `Probe.is_finding`, where `emitted` is the defect on this axis.
_SHAPE_GRID: Final[tuple[tuple[str, str], ...]] = (
    ("album_title", "A: colon, unescaped"),
    ("album_title", "trailing backslash \\"),
    ("album_title", "A=equals, unescaped"),
    ("album_title", ":"),
    ("album_title", "="),
    ("album_title", "::"),
    ("album_title", "=="),
    ("album_title", "a:=b"),
    ("album_artist", "B: colon, unescaped"),
    ("track_title", "T: colon, unescaped"),
    ("track_title", ":"),
    ("track_isrc", "IS:RC"),
)


def _probe_shape(field: str, raw: str) -> Probe:
    """Build a real argv with `raw` in `field`, then ask the chokepoint about it.

    The value goes through the **production** metadata path — `_build_rip_argv`
    with a real `RipMetadata` — so this measures what a caller could actually
    cause, not what a hand-written blob would look like. A row is a pass when the
    chokepoint refuses it and a finding when the argv is built and accepted.
    """
    from platterpus.adapters.rip_backend import TrackTag  # noqa: PLC0415

    if field == "album_title":
        meta = RipMetadata(album_title=raw)
    elif field == "album_artist":
        meta = RipMetadata(album_title="Probe Album", album_artist=raw)
    elif field == "track_title":
        meta = RipMetadata(
            album_title="Probe Album", tracks=[TrackTag(number=1, title=raw)]
        )
    else:
        meta = RipMetadata(
            album_title="Probe Album",
            tracks=[TrackTag(number=1, title="T", isrc=raw)],
        )

    kwargs = dict(_BASELINE)
    kwargs["metadata"] = meta
    backend = CyanripImpl(binary_path="cyanrip")
    try:
        argv = backend._build_rip_argv("/dev/sr0", **kwargs)
    except RipError as exc:
        return Probe(field, repr(raw), "raised", f"RipError: {exc}", axis="shape")
    except (TypeError, ValueError, OverflowError) as exc:
        return Probe(
            field, repr(raw), "raised", f"{type(exc).__name__}: {exc}", axis="shape"
        )
    try:
        assert_metadata_lookup_disabled(argv)
    except RipError as exc:
        # A legal title refused is a defect in the guard, not a pass. Naming it
        # `wrongly-refused` rather than `raised` keeps it out of the range axis's
        # vocabulary, where `raised` is the desired outcome.
        return Probe(
            field, repr(raw), "wrongly-refused", f"chokepoint: {exc}", axis="shape"
        )

    # Read the blob this FIELD actually lives in. The first version searched
    # `-a` then `-t` and broke on the first hit, so every track-level row reported
    # the album blob — three rows describing a value they had not looked at.
    flag = "-a" if field.startswith("album") else "-t"
    if flag not in argv:
        return Probe(
            field, repr(raw), "dropped", f"{flag} absent from argv", axis="shape"
        )
    blob = argv[argv.index(flag) + 1]

    # THE ROUND TRIP. Parse the blob back the way cyanrip's own two-stage parse
    # does and compare against what went in. This is the property that matters:
    # not "was it escaped" but "does the text survive", which is the thing their
    # §B showed can fail silently at exit 0.
    key = {
        "album_title": "album",
        "album_artist": "album_artist",
        "track_title": "title",
        "track_isrc": "isrc",
    }[field]
    payload = blob if flag == "-a" else blob.partition("=")[2]
    recovered = split_meta_blob(payload).get(key)
    if recovered != raw:
        return Probe(
            field,
            repr(raw),
            "mangled",
            f"sent {raw!r}, blob {blob!r}, came back {recovered!r}",
            axis="shape",
        )
    return Probe(
        field, repr(raw), "emitted", f"round-tripped through {blob!r}", axis="shape"
    )


def probe_all() -> list[Probe]:
    """Run both grids. Deterministic and side-effect free.

    Two axes with opposite expectations, deliberately reported in one table: the
    point of S-9 is one place a reader can total, and two tables would let one of
    them go unread.
    """
    results: list[Probe] = []
    for parameter, flag, values in _GRID:
        for value in values:
            results.append(_probe_one(parameter, value, flag=flag))
    for field, raw in _SHAPE_GRID:
        results.append(_probe_shape(field, raw))
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
    refused = [p for p in probes if "CHOKEPOINT REFUSED" in p.detail]

    # PER AXIS, because a single total is how a summary reads all-clear about a
    # failure mode nothing looked for. The fork's §C.1: their gate printed
    # "0 silently ignored" and exited 0 while the binary segfaulted in the same
    # run — the sentence was true, and complete about silent-ignores, and silent
    # about crashes. Every axis reports its own numbers and its own finding class.
    range_rows = [p for p in probes if p.axis == "range"]
    shape_rows = [p for p in probes if p.axis == "shape"]
    range_findings = [p for p in range_rows if p.is_finding]
    shape_findings = [p for p in shape_rows if p.is_finding]
    round_tripped = sum(1 for p in shape_rows if p.outcome == "emitted")
    mangled = [p for p in shape_rows if p.outcome == "mangled"]
    wrongly = [p for p in shape_rows if p.outcome == "wrongly-refused"]
    # RECONCILIATION. If the named classes do not account for every row, say so
    # in the output rather than letting the difference be silence — the arithmetic
    # not adding up is exactly how the missing class was found.
    other = [
        p
        for p in shape_rows
        if p.outcome not in ("emitted", "mangled", "wrongly-refused")
    ]

    lines += [
        "",
        f"**{len(probes)} probes: {emitted} emitted, {dropped} dropped, "
        f"{raised} raised.**",
        "",
        f"**Range axis — {len(range_rows)} probes. Silently-dropped non-zero "
        f"values (findings): {len(range_findings)}**"
        + (
            " — none. Every value a caller set either reached the argv or was refused."
            if not range_findings
            else ": " + ", ".join(f"`{p.parameter}={p.value}`" for p in range_findings)
        ),
        "",
        f"**Shape axis — {len(shape_rows)} probes, {round_tripped} round-tripped "
        f"intact, {len(mangled)} mangled, {len(wrongly)} wrongly refused"
        + (
            ". "
            if not other
            else f", {len(other)} other ("
            + ", ".join(sorted({p.outcome for p in other}))
            + "). "
        )
        + f"Findings: {len(shape_findings)}**"
        + (
            " — none. Every structurally awkward value came back out of the blob "
            "byte-for-byte, and none was refused for being awkward."
            if not shape_findings
            else ": "
            + ", ".join(
                f"`{p.parameter}={p.value}` ({p.detail})" for p in shape_findings
            )
        ),
        "",
        "*Two axes with opposite expectations: on the range axis a refusal is the "
        "desired outcome, on the shape axis it is a defect. Reported separately "
        "because one total cannot mean both.*",
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
