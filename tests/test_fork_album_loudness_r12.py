"""The album loudness/peak facts must come from the rows cyanrip OWNS.

Three real artifacts, read **from where the round already committed them** —
`docs/handshake/inbound/artifacts/` — rather than from copies under
`tests/fixtures/`. Two copies were in fact made here first and deleted the same
hour: the same artifact at the same value in two places is the duplication
Critical rule #7 forbids, and these are *correspondence* (a byte-faithful record
of what the fork sent), so a copy that drifts is worse than no copy.

* `round-12-lap-01-golden-reference-gdef36a6.log` — a completed 3-track rip of
  their `pregap.cue` image at build `platterpus-fork-gdef36a6`.
* `round-12-lap-01-sample-interrupted-gdef36a6.log` — the same rip stopped with
  SIGTERM part way through track 1. It carries the fork's own explanatory header
  above the log; their header says to "strip everything up to and including the
  next marker line", which `_log_body` does at read time.
* `round-12-lap-01-provider-contract-gdef36a6.md` — their contract. The claims
  this module's reasoning rests on (P2 declares the four rows; P3 disclaims the
  FFmpeg block) are asserted **against that file** rather than paraphrased here.
  A remembered contract line has no provenance you can re-check.

**The defect these pin.** Both logs print the whole-disc loudness twice:
once as FFmpeg's `ebur128` summary (`Integrated loudness:` / `Sample peak:`
sub-headers with `I:` / `LRA:` / `Peak:` value lines) and once as four column-0
rows of cyanrip's own (`Album integrated loudness (R128):` and family). The
fork's provider contract puts the first in **P3 — unstable wording**, saying in
as many words that it "belongs to libavfilter and moves when FFmpeg does", and
declares the second in **P2 — stable log lines (the API)**. We were reading the
disclaimed one and **silently dropping** the guaranteed one: all four rows landed
in the parser's unclaimed-line residue with no `_IGNORED_DISC_LINES` entry, which
this project distinguishes sharply from "ignored with a recorded reason".

**Why the obvious test would have been vacuous.** On both of these artifacts the
two sources agree to the digit (-7.4 / 3.0 / 0.0 / 0.3 on the golden reference),
so asserting the *values* passes identically against the old code. Two witnesses
that agree are not either one being right — CLAUDE.md's "two implementations
agreeing" question. So the assertions here are about **provenance and
discriminating inputs**: the parser records which source filled each key, the
ebur128 block is *deleted* from a real artifact to prove the stable rows alone
suffice, and a synthetic log makes the two sources disagree in both orders.

**And the fallback is pinned too, in the same file.** The ebur128 scrape is not
legacy dead code: stock cyanrip 0.9.3/0.9.4 — what every AppImage user runs —
and every fork build before round 8 print it and none of the four rows. A test
that only proved the new path works would have licensed deleting the old one.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from platterpus.parsers import cyanrip_log
from platterpus.parsers.cyanrip_log import parse_cyanrip_log

_REPO = Path(__file__).resolve().parent.parent
_INBOUND = _REPO / "docs" / "handshake" / "inbound" / "artifacts"
_GOLDEN = _INBOUND / "round-12-lap-01-golden-reference-gdef36a6.log"
_INTERRUPTED = _INBOUND / "round-12-lap-01-sample-interrupted-gdef36a6.log"
_CONTRACT = _INBOUND / "round-12-lap-01-provider-contract-gdef36a6.md"

#: The four rows the fork declares stable, from `cyanrip_encode.c:847-853` in
#: their round-12 P2 table. Labels only — the values are per-artifact.
_STABLE_ROW_LABELS: tuple[str, ...] = (
    "Album integrated loudness (R128):",
    "Album loudness range (R128):",
    "Album sample peak level:",
    "Album true peak level:",
)

#: The `album_loudness` keys those four rows fill.
_ALL_KEYS: frozenset[str] = frozenset(
    {"integrated_lufs", "lra_lu", "sample_peak_dbfs", "true_peak_dbfs"}
)

#: Where the interrupted sample's own explanatory header ends. Their file says to
#: "strip everything up to and including the next marker line", so that is what
#: this does rather than storing a pre-trimmed copy: the artifact on disk stays
#: the bytes they sent, and the trim rule lives beside the test that needs it.
_HEADER_END = re.compile(r"^=== END OF HEADER[^\n]*$\n", re.MULTILINE)


def _log_body(path: Path) -> str:
    """The bytes cyanrip wrote, with any delivery wrapper removed."""
    text = path.read_text(encoding="utf-8")
    match = _HEADER_END.search(text)
    return text[match.end() :] if match else text


def _top_level(text: str) -> list[str]:
    return [line for line in text.splitlines() if line and not line[0].isspace()]


# --- Floors: the artifacts really are what this file claims -------------------


@pytest.mark.parametrize("path", [_GOLDEN, _INTERRUPTED], ids=["golden", "interrupted"])
def test_the_artifact_carries_both_sources_of_the_same_fact(path: Path) -> None:
    """The precondition every assertion below depends on.

    If an artifact ever stopped printing BOTH blocks, the discrimination tests
    would still pass while proving nothing — the "can this check be satisfied by
    finding nothing?" trap. So the double-reporting is asserted outright.
    """
    body = _log_body(path)
    for label in _STABLE_ROW_LABELS:
        assert any(line.startswith(label) for line in body.splitlines()), (
            f"{path.name}: the fork's own stable row {label!r} is absent — this "
            "artifact can no longer prove which source the parser read"
        )
    # The disclaimed ebur128 block, identified by its own sub-headers.
    assert "  Sample peak:\n" in body, path.name
    assert "  Integrated loudness:\n" in body, path.name
    assert re.search(r"^\s+I:\s+-?\d", body, re.MULTILINE), path.name


def test_the_contract_really_declares_what_this_module_acts_on() -> None:
    """Read the artifact, do not remember it.

    Every design choice in the parser change cites two claims from the fork's
    contract: that the four `Album …` rows are in **P2 — stable log lines**, and
    that the `ebur128` block is in **P3 — unstable wording**. Both are asserted
    here off the committed file, with the section boundaries resolved rather than
    assumed — because a label match is not a check (CLAUDE.md: "where a check
    matches on a *label*, make it also require the *subject*"). A grep for the row
    text alone would pass with the rows sitting in the disclaimed section, which is
    the exact mistake this change corrects.
    """
    text = _CONTRACT.read_text(encoding="utf-8")
    p2 = text.index("## P2 - Outputs: stable log lines")
    p3 = text.index("## P3 - Unstable wording")
    p4 = text.index("## P4 - Exit codes")
    assert p2 < p3 < p4, (p2, p3, p4)
    stable_section = text[p2:p3]
    unstable_section = text[p3:p4]

    for label in _STABLE_ROW_LABELS:
        assert label in stable_section, (
            f"{label!r} is not in the contract's P2 (stable) section — the parser "
            "is now keyed on a row the provider has not promised"
        )
        assert label not in unstable_section, label

    # And the block we demoted to a fallback really is the disclaimed one.
    assert "belongs to libavfilter and moves when FFmpeg does" in unstable_section
    assert "Prefer the" in unstable_section


def test_the_artifacts_are_fork_builds_at_the_round_12_pin() -> None:
    """Provenance, from the artifact's content — not from its filename."""
    from platterpus.ripper_identity import identify_from_banner

    for path in (_GOLDEN, _INTERRUPTED):
        banner = _log_body(path).split("\n", 1)[0]
        assert identify_from_banner(banner).is_fork, (path.name, banner)
        assert "gdef36a6" in banner, (path.name, banner)


# --- The fix: the stable rows are what we read --------------------------------


def test_the_golden_reference_album_loudness_is_the_expected_four_figures() -> None:
    """The plain read, stated for the record — and it is NOT the discriminator.

    Both sources agree to the digit on this artifact, so this exact assertion
    passes against the old code too. It is here because a regression that changed
    the *values* would be worse than the one being fixed, not because it proves
    which row was read. `test_the_stable_rows_alone_are_enough` and the two
    precedence tests are what can only pass with the fix in place.
    """
    parsed = parse_cyanrip_log(_log_body(_GOLDEN))
    assert parsed.album_loudness == {
        "integrated_lufs": "-7.4",
        "lra_lu": "3.0",
        "sample_peak_dbfs": "0.0",
        "true_peak_dbfs": "0.3",
    }


def test_the_interrupted_sample_still_yields_the_album_figures() -> None:
    """A rip killed mid-track prints the album block anyway; we must read it.

    Zero tracks completed, so this is the shape where every per-track figure is
    absent and the disc-level ones are all the record has.
    """
    parsed = parse_cyanrip_log(_log_body(_INTERRUPTED))
    assert parsed.tracks == ()
    assert parsed.album_loudness == {
        "integrated_lufs": "-70.0",
        "lra_lu": "0.0",
        "sample_peak_dbfs": "0.0",
        "true_peak_dbfs": "0.0",
    }


@pytest.mark.parametrize("path", [_GOLDEN, _INTERRUPTED], ids=["golden", "interrupted"])
def test_the_stable_rows_alone_are_enough(path: Path) -> None:
    """THE discriminator, run on real bytes.

    Delete the disclaimed ebur128 block from the artifact — exactly what one
    upstream FFmpeg rewording would effectively do to a parser keyed on it — and
    the four figures must still be there. Against the old code this yields an
    empty `album_loudness`, so it fails on a revert (see the revert probe).
    """
    body = _log_body(path)
    kept = [
        line
        for line in body.splitlines()
        # The ebur128 block is the indented sub-headers and their value lines.
        if not re.match(r"^\s+(?:I|LRA|LRA low|LRA high|Peak|Threshold):\s", line)
        and not re.match(
            r"^\s+(?:Integrated loudness|Loudness range|Sample peak|True peak):\s*$",
            line,
        )
    ]
    parsed = parse_cyanrip_log("\n".join(kept) + "\n")
    assert set(parsed.album_loudness) == _ALL_KEYS, (
        f"{path.name}: with FFmpeg's block removed the album loudness came out "
        f"{parsed.album_loudness!r} — the parser is still keyed on the wording "
        "the fork disclaims"
    )
    # Non-triviality: an empty dict of the right shape is not a pass, and neither
    # is a dict of empty strings.
    assert all(parsed.album_loudness.values()), parsed.album_loudness


# --- Precedence, made non-positional -----------------------------------------


_EBUR128_BLOCK = (
    "Album Loudness Summary:\n"
    "\n"
    "  Integrated loudness:\n"
    "    I:          -1.1 LUFS\n"
    "\n"
    "  Loudness range:\n"
    "    LRA:         2.2 LU\n"
    "\n"
    "  Sample peak:\n"
    "    Peak:       -3.3 dBFS\n"
    "\n"
    "  True peak:\n"
    "    Peak:       -4.4 dBFS\n"
)

_STABLE_ROWS = (
    "Album integrated loudness (R128): -9.9 LUFS\n"
    "Album loudness range (R128):      8.8 LU (-20.0 to -11.2 LUFS)\n"
    "Album sample peak level:          -7.7 dBFS\n"
    "Album true peak level:            -6.6 dBFS\n"
)

_STABLE_VALUES = {
    "integrated_lufs": "-9.9",
    "lra_lu": "8.8",
    "sample_peak_dbfs": "-7.7",
    "true_peak_dbfs": "-6.6",
}


@pytest.mark.parametrize(
    ("order", "text"),
    [
        ("ebur128 first", _EBUR128_BLOCK + _STABLE_ROWS),
        ("stable rows first", _STABLE_ROWS + _EBUR128_BLOCK),
    ],
)
def test_a_cyanrip_owned_row_wins_over_the_ffmpeg_block_in_either_order(
    order: str, text: str
) -> None:
    """The rule is precedence, not print order.

    Every artifact we hold prints the ebur128 block first, so a plain overwrite
    would *happen* to be correct — and would silently invert the day a build
    reordered them. Both orders are asserted so "it came second" can never be
    the reason the right value won.
    """
    parsed = parse_cyanrip_log("cyanrip 0.9.4-rc2+platterpus.7 (x)\n" + text)
    assert parsed.album_loudness == _STABLE_VALUES, order


def test_the_precedence_helper_is_asymmetric_by_itself() -> None:
    """The rule as a unit, one level below the loop that uses it.

    `_Disc.record_album_loudness` is where "stable wins" actually lives, and its
    asymmetry is the whole point: a stable value overwrites a fallback one, and a
    fallback value cannot overwrite a stable one. Tested directly because the
    provenance set it maintains is parser-internal and never reaches `RipLog` —
    the log-level tests above can only observe the *consequence*, and a helper
    that got this backwards would still pass them on any artifact where the two
    sources agree (which is every artifact we hold).
    """
    disc = cyanrip_log._Disc()
    disc.record_album_loudness("integrated_lufs", "-1.1", stable=False)
    assert disc.album_loudness["integrated_lufs"] == "-1.1"
    assert disc.album_loudness_stable == set()

    disc.record_album_loudness("integrated_lufs", "-9.9", stable=True)
    assert disc.album_loudness["integrated_lufs"] == "-9.9"
    assert disc.album_loudness_stable == {"integrated_lufs"}

    # The direction that matters: the fallback must now be refused.
    disc.record_album_loudness("integrated_lufs", "-1.1", stable=False)
    assert disc.album_loudness["integrated_lufs"] == "-9.9"

    # A key no stable row claimed is still fillable.
    disc.record_album_loudness("true_peak_dbfs", "0.3", stable=False)
    assert disc.album_loudness["true_peak_dbfs"] == "0.3"
    assert disc.album_loudness_stable == {"integrated_lufs"}


def test_the_ffmpeg_block_still_fills_a_build_that_prints_nothing_else() -> None:
    """The fallback, which stock cyanrip and every pre-round-8 fork build need.

    Deleting the fallback would pass every test above and blank the album
    loudness for the ripper the primary distribution channel actually ships
    against — so it gets its own assertion.
    """
    parsed = parse_cyanrip_log("cyanrip 0.9.3.1 (x)\n" + _EBUR128_BLOCK)
    assert parsed.album_loudness == {
        "integrated_lufs": "-1.1",
        "lra_lu": "2.2",
        "sample_peak_dbfs": "-3.3",
        "true_peak_dbfs": "-4.4",
    }


def test_the_committed_older_logs_still_parse_through_the_fallback() -> None:
    """Same claim, on real bytes rather than a synthetic block.

    The stock 0.9.3 corpus log and the round-6 fork log print the ebur128 block
    and none of the four rows, so their album loudness must come out of the
    fallback path — and the fork one must still separate its sample peak from its
    true peak, the trap the sub-header state machine exists for.
    """
    repo = Path(__file__).resolve().parent.parent
    stock = (
        repo / "output_reference" / "cyanrip_flac" / "cyanrip_flac_police_classics.log"
    )
    fork_r6 = (
        repo
        / "output_reference"
        / "cyanrip_fork_flac"
        / "cyanrip_fork_police_classics.log"
    )
    assert stock.exists() and fork_r6.exists(), (stock, fork_r6)

    stock_text = stock.read_text(encoding="utf-8", errors="replace")
    assert not any(
        line.startswith(label)
        for line in stock_text.splitlines()
        for label in _STABLE_ROW_LABELS
    ), "the stock corpus log grew the fork's rows — this test's premise is gone"
    stock_parsed = parse_cyanrip_log(stock_text)
    assert stock_parsed.album_loudness == {
        "integrated_lufs": "-13.9",
        "lra_lu": "8.9",
        "true_peak_dbfs": "0.8",
    }

    fork_parsed = parse_cyanrip_log(
        fork_r6.read_text(encoding="utf-8", errors="replace")
    )
    assert fork_parsed.album_loudness == {
        "integrated_lufs": "-13.9",
        "lra_lu": "8.9",
        "sample_peak_dbfs": "-0.1",
        "true_peak_dbfs": "0.8",
    }


# --- Nothing else is dropped silently ----------------------------------------


def _classify_top_level(line: str) -> str | None:
    """Name of whatever recognises this column-0 line, or None.

    Deliberately the same three-way lookup `tests/test_parsers_cyanrip_log.py`
    uses over `output_reference/`: rules, section headers, written-down ignores.
    Duplicated as four lines rather than imported because the other module is a
    test, not a helper library — and the assertion below is about a different
    corpus.
    """
    for rule in cyanrip_log._ALL_LINE_RULES:
        if rule.pattern.match(line):
            return rule.name
    for name, pattern in cyanrip_log._SECTION_LINE_PATTERNS:
        if pattern.match(line):
            return name
    if cyanrip_log._is_ignored_disc_line(line):
        return "ignored"
    return None


@pytest.mark.parametrize("path", [_GOLDEN, _INTERRUPTED], ids=["golden", "interrupted"])
def test_every_column_zero_line_of_the_r12_artifacts_is_accounted_for(
    path: Path,
) -> None:
    """The completeness sweep, extended to the artifacts that exposed the gap.

    The existing sweep reads `output_reference/cyanrip_*/*.log`, and none of those
    logs contains the four `Album …` rows — so it passed the whole time the rows
    were being dropped. A sweep whose corpus cannot contain the defect is not
    evidence about the defect. These two artifacts can, so they are swept here.
    """
    body = _log_body(path)
    top_level = _top_level(body)
    # Floor: a mis-globbed or truncated fixture must not pass by being empty.
    assert len(top_level) >= 40, f"{path.name}: only {len(top_level)} column-0 lines"
    unaccounted = [line for line in top_level if _classify_top_level(line) is None]
    assert not unaccounted, (
        f"{path.name}: cyanrip printed {len(unaccounted)} column-0 line(s) this "
        "parser recognises nothing for. Either parse them (a table rule) or record "
        "the decision in _IGNORED_DISC_LINES with a reason:\n  "
        + "\n  ".join(repr(line) for line in unaccounted[:20])
    )


def test_the_parser_logs_no_unclaimed_residue_for_these_artifacts(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The product's own diagnostic, not just the test's view of it.

    `parse_cyanrip_log` counts unclaimed column-0 lines and reports them to the
    debug log. Asserting on THAT closes the gap between "the test's classifier is
    happy" and "the shipped parser thinks it understood the file".
    """
    import logging

    for path in (_GOLDEN, _INTERRUPTED):
        caplog.clear()
        with caplog.at_level(logging.DEBUG, logger="platterpus.parsers.cyanrip_log"):
            parse_cyanrip_log(_log_body(path))
        residue = [
            r.getMessage() for r in caplog.records if "unclaimed" in r.getMessage()
        ]
        assert not residue, (path.name, residue)


def test_the_new_ignore_entries_are_evidenced_by_these_artifacts() -> None:
    """Each line we chose NOT to parse must actually appear in a real log.

    The ignore list is an allow-list of decisions, and an entry for a line nobody
    has ever seen is speculation. These five were all measured in the round-12
    artifacts, so they are checked against them.
    """
    corpus = [
        line
        for path in (_GOLDEN, _INTERRUPTED)
        for line in _log_body(path).splitlines()
    ]
    assert len(corpus) >= 150, len(corpus)
    expected = (
        "--- output before this log was opened ---",
        "--- end of pre-log output ---",
        "Opening drive...",
        "Checking pregap.bin for cdrom...",
        "Stopping, ripping incomplete!",
    )
    for line in expected:
        assert line in corpus, f"{line!r} is no longer in the artifacts"
        assert cyanrip_log._is_ignored_disc_line(line), (
            f"{line!r} is in a real log and is neither parsed nor recorded in "
            "_IGNORED_DISC_LINES — that is the silent drop this change fixed"
        )


# --- The bounds on the new patterns ------------------------------------------

# One past CPython's 4300-digit str->int conversion ceiling, and far past what
# `float()` can hold without becoming `inf`. Hypothesis does not generate this,
# so it is pinned — the same reasoning as the identical guard on the per-track
# peak rows in `tests/test_parsers_cyanrip_log.py`.
_OVER_THE_DIGIT_LIMIT = "9" * 4301


@pytest.mark.parametrize(
    "line",
    [
        f"Album integrated loudness (R128): -{_OVER_THE_DIGIT_LIMIT}.0 LUFS",
        f"Album loudness range (R128):      {_OVER_THE_DIGIT_LIMIT}.0 LU",
        f"Album sample peak level:          -{_OVER_THE_DIGIT_LIMIT} dBFS",
        f"Album true peak level:            {_OVER_THE_DIGIT_LIMIT}.0 dBFS",
    ],
)
def test_an_absurd_album_loudness_number_is_refused_not_absorbed(line: str) -> None:
    """Bounded digits, and the bound is what makes the refusal a refusal.

    The pattern caps the integer and fraction at six digits each, so a line like
    these matches nothing and the key stays absent. "Absent means absent" is this
    module's standing rule.

    Stated precisely, because the neighbouring per-track guard is about a
    different consequence: nothing floats these four values today — they are
    carried as strings into the report JSON and interpolated into a label — so the
    concrete failure here is a 4301-digit string being archived as a loudness
    figure, not an `inf`. The bound is the same shape as the per-track one because
    the *next* consumer to convert one of these to a number should not have to
    rediscover that `float()` has no digit ceiling and returns `inf` rather than
    raising (audit, 2026-07-31).
    """
    parsed = parse_cyanrip_log("cyanrip 0.9.4-rc2+platterpus.7 (x)\n" + line + "\n")
    assert parsed.album_loudness == {}
