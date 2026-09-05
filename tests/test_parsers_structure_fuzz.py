"""Structure-aware fuzzing: adversarial values inside PLAUSIBLE log shapes.

**Why this exists alongside `test_parsers_property.py`.** That file generates
arbitrary text and asserts the parsers never raise, which is the right property
and it is not the whole surface. Random text almost never produces a line that
*looks* like `Offset:         +6 samples`, so the deep parse paths — the ones
that split a field, convert it, and store it — are essentially never reached.
The random-text sweep exercises the guards; this one exercises the body.

That distinction is the taxonomy's point about coverage-guided vs random
generation, reached here with `hypothesis` rather than a native fuzzer. **A
deliberate choice, not a shortcut:** Atheris would be another third-party tool
with its own CI wiring and its own ability to retire silently, which is Critical
rule #11's exact concern and the reason `scripts/mutation_sweep.py` exists at
all. A grammar built from the real line shapes gets the reach without the
dependency, and — the part that matters more — the grammar is derived from a
COMMITTED golden reference, so it cannot drift from a shape the ripper actually
emits into one we imagined.

**What is asserted.** Never raises; always returns the dataclass; and every
numeric field it does populate is finite and of the declared type. That last one
is the addition: "did not raise" and "did not silently store garbage" are
different claims, and only the first was checked.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Final

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.parsers.rip_log import RipLog, parse_rip_log

REPO_ROOT: Final[Path] = Path(__file__).resolve().parent.parent

#: Line PREFIXES read from a committed golden reference rather than typed out
#: here. A hand-written grammar is a second description of the ripper's output
#: that can drift from it — the same defect `docs/cyanrip-consumer-contract.md`
#: is generated to avoid. If the reference changes shape, this fuzzer follows.
_REFERENCE: Final[Path] = (
    REPO_ROOT
    / "docs"
    / "handshake"
    / "inbound"
    / "artifacts"
    / "round-07-lap-39-golden-reference-g422d12a.log"
)


def _label_prefixes() -> list[str]:
    """Every `Label:` prefix the golden reference actually uses."""
    text = _REFERENCE.read_text(encoding="utf-8", errors="replace")
    prefixes: list[str] = []
    for line in text.splitlines():
        head, sep, _rest = line.partition(":")
        if sep and head and not head.startswith(" ") and len(head) <= 24:
            prefixes.append(head + ":")
    return sorted(set(prefixes))


_PREFIXES: Final[list[str]] = _label_prefixes()


def test_the_grammar_was_actually_derived() -> None:
    """The floor. A fuzzer whose grammar came out empty would generate nothing
    recognisable and pass every property by never reaching a parse path — which
    is this project's most-repeated failure shape, applied to a fuzzer."""
    assert len(_PREFIXES) >= 15, (
        f"only {len(_PREFIXES)} label prefixes derived from {_REFERENCE.name}; "
        "the reference moved or the derivation broke, and a grammar this small "
        "cannot reach the parser's body"
    )


#: Values chosen to be hostile in the ways a real log can be: numbers at the
#: boundaries, signs where none is expected, unicode, control characters, and
#: the empty value — which is the one a field-splitter is most likely to assume
#: away.
_HOSTILE_VALUES: Final[st.SearchStrategy[str]] = st.one_of(
    st.sampled_from(
        [
            "",
            " ",
            "+0",
            "-0",
            "0",
            "-1",
            "+2147483647",
            "-2147483648",
            "99999999999999999999",
            "1" * 400,
            "nan",
            "inf",
            "-inf",
            "+6 samples",
            "none",
            "unknown",
            "yes",
            "no",
            "N/A",
            "\x00",
            "\x1b[31m",
            "\r",
            "\t\t",
            "…",
            "𝟘",
            "Ω",
            "café",
            "0x10",
            "1e309",
            "1,5",
            "1.2.3",
            "--",
            "::",
            "|",
            "`",
        ]
    ),
    st.text(max_size=40),
)


@st.composite
def _plausible_log(draw: st.DrawFn) -> str:
    """A log with real line shapes and adversarial field values."""
    lines: list[str] = [
        draw(st.sampled_from(["cyanrip 0.9.4 (platterpus-fork-gdeadbee)", ""]))
    ]
    for _ in range(draw(st.integers(min_value=1, max_value=25))):
        prefix = draw(st.sampled_from(_PREFIXES))
        value = draw(_HOSTILE_VALUES)
        pad = " " * draw(st.integers(min_value=0, max_value=8))
        lines.append(f"{prefix}{pad}{value}")
    return "\n".join(lines)


def _assert_numerics_are_sane(parsed: RipLog) -> None:
    """Every populated numeric field is of its declared type and finite.

    *"It did not raise"* and *"it did not store garbage"* are different claims.
    A parser that swallows `1e309` into a float field and stores `inf` has not
    crashed and has silently put a meaningless number into an archival record —
    which is the class of defect this project cares about most.
    """
    for field, value in vars(parsed).items():
        if isinstance(value, bool) or value is None:
            continue
        if isinstance(value, float):
            assert math.isfinite(value), f"{field} parsed to {value!r}"
        if isinstance(value, int):
            assert abs(value) < 10**12, f"{field} parsed to an absurd {value!r}"


@settings(max_examples=350, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(_plausible_log())
def test_cyanrip_log_survives_plausible_but_hostile_logs(text: str) -> None:
    parsed = parse_cyanrip_log(text)
    assert isinstance(parsed, RipLog)
    _assert_numerics_are_sane(parsed)


@settings(max_examples=350, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(_plausible_log())
def test_rip_log_dispatcher_survives_them_too(text: str) -> None:
    """The dispatcher picks a backend parser from the text; a shape that looks
    like cyanrip but is not must not make it choose wrongly and crash."""
    parsed = parse_rip_log(text)
    assert isinstance(parsed, RipLog)
    _assert_numerics_are_sane(parsed)


@settings(max_examples=120, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(
    st.lists(st.sampled_from(_PREFIXES), min_size=1, max_size=12),
    st.binary(max_size=200),
)
def test_a_log_carrying_RAW_BYTES_decodes_rather_than_raising(
    prefixes: list[str], blob: bytes
) -> None:
    """A truncated write, a wrong locale, or a device error can leave undecodable
    bytes mid-line. The seam rules require the inbound half be sanitised rather
    than trusted; this asserts the parser is not where that falls over."""
    body = blob.decode("utf-8", errors="replace")
    text = "\n".join(f"{p} {body}" for p in prefixes)
    parsed = parse_cyanrip_log(text)
    assert isinstance(parsed, RipLog)


def test_a_zero_byte_log_is_not_a_crash_and_not_a_completed_rip() -> None:
    """The empty artifact. It must parse, and it must NOT report completion —
    tri-state, where absent is `None` and never a pass."""
    parsed = parse_cyanrip_log("")
    assert isinstance(parsed, RipLog)
    assert parsed.rip_completed is None
    assert parsed.tracks == ()


def test_a_log_that_is_ONE_ENORMOUS_LINE_does_not_hang() -> None:
    """`docs/seam-rules.md` names this: a multi-megabyte single line freezes the
    GUI thread rendering it, so the parser must at least return promptly rather
    than being the thing that wedges."""
    parsed = parse_cyanrip_log("Offset:" + ("x" * 2_000_000))
    assert isinstance(parsed, RipLog)
