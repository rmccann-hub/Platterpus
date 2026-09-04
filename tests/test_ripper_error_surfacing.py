"""A ripper that diagnosed the failure precisely, and a user shown "Rip failed."

The rig hit this for real (2026-08-02): a 16-track disc, a MusicBrainz medium
listing 18, `-t 17=` handed to cyanrip. It answered

    Invalid track number 17, list has 16 tracks!

and exited 1 in two seconds with nothing ripped. The sentence was in our
captured output the whole time. The report's ``failure_hint`` was ``null`` and
the window said "Rip failed."

That one *was* matched by the original pattern. The cyanrip fork session then
enumerated the ripper's fatal log call sites and measured that the six prefixes
we had covered **24 of 45** — so the same silent-failure shape was live for the
other 21, waiting on whichever one a user hit first.

The judgement recorded here, because the original narrowness was a considered
choice and it was the wrong one: a **miss** costs a user staring at "Rip failed"
with the answer in a buffer we already captured; a **false positive** costs one
extra sentence of the ripper's own words, on a rip that has already failed.
Those are not comparable, so the pattern is broad on purpose.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from platterpus.workers.rip_worker import _RIPPER_ERROR_PREFIXES, _RIPPER_ERROR_RE

# Real cyanrip fatal lines. Every one of these ends a rip before or during
# audio extraction, so surfacing it verbatim is strictly better than "Rip
# failed." Sourced from the fork session's enumeration of cyanrip's fatal
# `cyanrip_log` call sites plus the strings the rig has actually produced.
_FATAL_LINES: tuple[str, ...] = (
    "Invalid track number 17, list has 16 tracks!",
    "Invalid offset value!",
    "Unable to open device /dev/sr0!",
    "Unable to read disc TOC!",
    "Unable to init cover art!",
    "Missing track number in -t!",
    "Missing argument for -o!",
    "No device specified and none found!",
    "No disc inserted?",
    "No cover art file specified!",
    "No tracks selected!",
    "Error reading sector 12345!",
    "Error initializing encoder!",
    "Errors were encountered, stopping!",
    "Failed to allocate output context!",
    "Failed to open output file!",
    "Couldn't open file for writing!",
    "Could not set drive speed!",
    "Cannot use -l with -I!",
    "Unsupported output format!",
    "Unknown option -q!",
    "Unrecognized sample format!",
    "Stopping, disc read error!",
    "Stopping after 3 errors!",
    "Aborting rip!",
    "Drive media changed, stopping!",
    "Insufficient memory for track buffer!",
    "Out of memory!",
    "Fatal error, cannot continue!",
)

# Lines that must NOT be treated as fatal. Some are near-misses on purpose: a
# pattern that swallowed these would turn a healthy rip's ordinary chatter into
# a scary hint.
_BENIGN_LINES: tuple[str, ...] = (
    "Track 1 ripped and encoded successfully!",
    "No errors were encountered.",  # begins with "No", not "No device"/"No disc"
    "Errorless read confirmed",  # "Error" without the boundary
    "Invalidated cache entry",  # "Invalid" without the boundary
    "Missingno is a great track title",  # "Missing" without the boundary
    "Disc tracks:    16",
    "Accurip: disabled",
    "  Error reading sector 5",  # indented: not a top-level fatal line
    "progress - 41.65%",
    "",
)


@pytest.mark.parametrize("line", _FATAL_LINES)
def test_every_known_fatal_line_is_recognised(line: str) -> None:
    assert _RIPPER_ERROR_RE.match(line), (
        f"would be shown as a bare 'Rip failed': {line}"
    )


@pytest.mark.parametrize("line", _BENIGN_LINES)
def test_ordinary_output_is_not_mistaken_for_a_fatal_error(line: str) -> None:
    assert not _RIPPER_ERROR_RE.match(line), f"benign line flagged as fatal: {line}"


def test_the_boundary_is_a_real_boundary() -> None:
    """`Invalid` must not match `Invalidated`. Without the `(?:\\s|$)` this is a
    bare prefix match and every near-miss above starts firing."""
    assert _RIPPER_ERROR_RE.match("Invalid offset")
    assert not _RIPPER_ERROR_RE.match("Invalidated")
    assert _RIPPER_ERROR_RE.match("Invalid")  # a bare word IS the whole line


def test_the_sample_is_large_and_varied_enough_to_conclude_from() -> None:
    """Floors. "every line in the list matches" is satisfied by an empty list,
    and "the prefixes are covered" is satisfied by one prefix used 29 times."""
    assert len(_FATAL_LINES) >= 25
    assert len(_BENIGN_LINES) >= 8
    exercised = {
        prefix
        for prefix in _RIPPER_ERROR_PREFIXES
        if any(line.startswith(prefix) for line in _FATAL_LINES)
    }
    assert len(exercised) >= 18, (
        f"only {len(exercised)} of {len(_RIPPER_ERROR_PREFIXES)} prefixes have a "
        "sample line; an unexercised prefix is an untested claim"
    )


def test_a_pathological_line_is_bounded() -> None:
    """The hint reaches a QMessageBox, and the pattern reaches a regex engine.
    Neither should be handed a megabyte because a ripper went haywire."""
    assert not _RIPPER_ERROR_RE.match("Invalid " + "x" * 100_000)
    # ...while a realistically long diagnosis still matches.
    assert _RIPPER_ERROR_RE.match("Invalid " + "x" * 150)


def test_the_widening_actually_widened() -> None:
    """Revert-proof in code: the six original prefixes covered a minority of the
    sample. If someone narrows this back, the count check fails loudly rather
    than the coverage silently regressing.
    """
    original = (
        "Invalid ",
        "Unable to ",
        "Missing ",
        "No device ",
        "Error reading ",
        "Stopping, ",
    )
    covered_before = sum(1 for line in _FATAL_LINES if line.startswith(original))
    covered_now = sum(1 for line in _FATAL_LINES if _RIPPER_ERROR_RE.match(line))
    assert covered_now == len(_FATAL_LINES)
    assert covered_before < covered_now, (
        "this sample no longer demonstrates the gap the widening closed"
    )


# --- the fork's OWN inventory: 88 -> 104 -> 115 -> 130 -> 128, and each step ---
#
# This section used to read "all 88" and it was green, and it was measuring the
# wrong thing. Then it read "all 115" and was green for FIVE ROUNDS while the
# contract went to 130, for the same reason one level out: see
# `test_the_inventory_is_not_behind_the_newest_published_contract` at the bottom
# of this file, which is the check that had no counterpart on this half of the
# seam.
#
# The 88 came from the fork's contract generator filtered through its own
# hand-maintained 21-word `FATAL_PREFIXES` allowlist. Round 5 replaced that with a
# **control-flow** derivation — a message is listed because the call is followed by
# `return 1` / a non-zero `exit()` / `return AVERROR(...)` / `total_error_count++` /
# `goto fail` / `goto end` — and the inventory became **104**. Round 6 then took it
# to **115**, because the 104 still rested on a hand-maintained list of `goto`
# LABELS: it missed `goto end_meta`, `err = 1` feeding a later `+= err`, and bare
# `return -1`. Labels are now discovered from source. Re-derived independently on
# our side at each pin as it arrived: 104, then 115, strict supersets, nothing
# lost. The word allowlist had been hiding 16; the label list another 11.
#
# Rounds 7-11 took it 117 -> 120 -> **130**, the last jump because the generator's
# source scan had never had a pattern for `GEN_OPT_LOG` — so `genopt.h`, the option
# parser, contributed **zero** rows to a document whose anchor had always claimed
# `src/*.h`. Their round 8 lap 1 §D2: *"These messages were always emitted. Only
# the document was incomplete."* Round 12 reports **128**, two fewer, because two
# rows left `cyanrip_log()` for a raw `write(2)`; they are still printed, and
# `RETAINED_BEYOND_P5` is why we still match them.
#
# We had imported the 88 into a fixture and asserted "we surface everything the
# ripper can say" against it. Our own pattern missed **all 13** matchable strings
# the allowlist had hidden, two of them ordinary hardware failures —
# `Offset is unset! ...` and `Device does not support changing speeds!` — each
# rendering to the user as a bare "Rip failed."
#
# The test was green because the FIXTURE INHERITED THEIR FILTER'S BLIND SPOT. It
# described their allowlist, not the ripper's behaviour. That is CLAUDE.md's
# verify-the-behaviour-not-the-description rule biting one level below where it
# was written, and it is why the inventory now lives in
# `platterpus.ripper_message_inventory` with the provider's evidence column
# preserved, and why the matcher is built FROM it rather than from prefixes.


_INVENTORY = Path(__file__).parent / "fixtures" / "cyanrip_fatal_messages.tsv"


def _inventory() -> list[tuple[str, str]]:
    """(source location, message) for every fatal string the fork can print.

    Read from the committed fixture, which is the fork's own mechanically
    generated list (handshake round 4, Appendix 2) — not a list we imagined.
    A description derived from their behaviour cannot describe behaviour they
    do not have, which is the whole reason the contract is exchanged.
    """
    rows: list[tuple[str, str]] = []
    for line in _INVENTORY.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or "\t" not in line:
            continue
        where, message = line.split("\t", 1)
        rows.append((where, message))
    return rows


def test_every_string_the_ripper_can_print_is_surfaced() -> None:
    """All 128, from the control-flow-derived inventory rather than the
    prefix-filtered 88 — see the section comment for why that distinction is the
    whole point of this test."""
    from platterpus.ripper_message_inventory import MESSAGES

    rows = _inventory()
    # Floor raised deliberately, and it is a RATCHET: 80 was satisfiable by the old
    # 88, which is how this test stayed green while missing 13 real strings; 100 was
    # satisfiable by round 6's 115, which is how it stayed green for five more
    # rounds while the contract reached 130. A floor that the stale value clears is
    # not a floor. It may rise, never fall.
    assert len(rows) >= 125, f"inventory collapsed to {len(rows)} strings"
    assert len(rows) == len(MESSAGES), (
        f"the committed fixture ({len(rows)}) and the in-code inventory "
        f"({len(MESSAGES)}) disagree — they are two expressions of one contract "
        f"and a difference is the bug report"
    )
    # One format is excluded, named, and justified — never silently skipped.
    # `cyanrip_main.c:2272` is a bare `%s`: a pattern built from it would match
    # EVERY line of output, so every progress redraw would be reported as a fatal
    # error. Refusing it is correct, and saying so here is the difference between
    # "we cannot pattern this" and "this does not exist".
    from platterpus.workers.rip_worker import _UNMATCHABLE_RIPPER_FORMATS

    assert _UNMATCHABLE_RIPPER_FORMATS == ["%s"], (
        f"the set of unpatternable formats changed to "
        f"{_UNMATCHABLE_RIPPER_FORMATS} — each one is a message the user can only "
        f"receive as a bare 'Rip failed', so a new entry needs a decision, not a "
        f"passing test"
    )
    # Two exclusions, both named and both asserted elsewhere in this file: the
    # unpatternable bare `%s`, and the `-Z` convergence SUCCESS message that
    # round 6's label discovery swept into P5 (see
    # `test_the_convergence_success_message_is_never_a_failure_hint`). Everything
    # else in the inventory must reach the user.
    from platterpus.ripper_message_inventory import SURFACING_EXCLUDED

    excluded = set(_UNMATCHABLE_RIPPER_FORMATS) | {t for t, _ in SURFACING_EXCLUDED}
    missed = [
        (w, m)
        for w, m in rows
        if m not in excluded and not _RIPPER_ERROR_RE.match(_sample(m))
    ]
    assert not missed, "would render as a bare 'Rip failed': " + "; ".join(
        f"{w} {m}" for w, m in missed
    )
    # Floor: the exclusions must not be doing the work. Ratchet, same reasoning as
    # the one above — 110 was clearable by round 6's stale 115.
    assert len(rows) - len(excluded) >= 124


def test_the_strings_the_prefix_allowlist_had_hidden_are_covered() -> None:
    """THE REGRESSION, named string by string.

    These are the messages the fork's `FATAL_PREFIXES` allowlist filtered out of
    the 88, which our pattern therefore never had to match. Two are failures a
    user will actually hit on real hardware. Listed explicitly rather than left
    to the bulk sweep above, so a future narrowing of the matcher names which
    one it broke.
    """
    hidden = [
        "AccuRIP DB data error, got unexpected number of bytes!",
        "CDIO returned invalid track 3 end LSN",
        "Codec not found (not compiled in lavc?)!",
        'Cover art "front.jpg" already specified!',
        "Device does not support changing speeds!",
        "Directory name scheme must contain {format} with multiple output formats!",
        'Duplicated format "flac"',
        "Duplicated rip idx 3",
        "Force quitting",
        "Got empty medium list.",
        "Offset is unset! To continue with an offset of 0, run with -s 0!",
        "Too many cover arts specified!",
        'cdio: "some libcdio message"',
    ]
    missed = [m for m in hidden if not _RIPPER_ERROR_RE.match(m)]
    assert not missed, "still a bare 'Rip failed': " + "; ".join(missed)


def test_ordinary_output_is_not_mistaken_for_a_diagnostic() -> None:
    """The other half of the control. Broadening the matcher to 129 published
    formats must not turn normal progress output into a fatal-error report —
    which is exactly what a bare `%s` pattern would have done, and why the
    builder refuses formats with too little literal text.
    """
    benign = [
        "Ripping and encoding track 3, progress - 42%, ETA - 00:01:23",
        "Track 3 ripped and encoded successfully!",
        "  EAC CRC32:     B0D122E7",
        "Disc tracks:    14",
        "Ripping errors: 0",
        "Rip completed:  yes (14 of 14 tracks)",
        "    title:                         Roxanne",
        "Total time:     00:59:42.354",
        "Done; (1 out of 1 matches for current checksum B0D122E7)",
        "AccurateRip:    found",
        "Tracks:",
    ]
    assert len(benign) >= 8  # floor: a control with no cases proves nothing
    wrong = [b for b in benign if _RIPPER_ERROR_RE.match(b)]
    assert not wrong, "ordinary output read as a ripper error: " + "; ".join(wrong)


def _sample(fmt: str) -> str:
    """Substitute a plausible value for each printf conversion.

    The inventory stores cyanrip's *format strings*; what arrives on stdout has
    the conversions filled in. Matching the raw format would test the wrong
    string — a `%i` never appears in real output.
    """
    text = fmt.replace("\\n", "")
    for pattern, replacement in (
        (r"%[-+ #0-9.*]*(?:hh|h|ll|l|j|z|t|L)?[diu]", "7"),
        (r"%[-+ #0-9.*]*(?:hh|h|ll|l|j|z|t|L)?[xX]", "1A2B"),
        (r"%[-+ #0-9.*]*(?:hh|h|ll|l|j|z|t|L)?[eEfgGaA]", "1.5"),
        (r"%[-+ #0-9.*]*[c]", "x"),
        (r"%[-+ #0-9.*]*(?:hh|h|ll|l|j|z|t|L)?[sp]", "SOMEVALUE"),
    ):
        text = re.sub(pattern, replacement, text)
    return text.strip()


def test_the_hyphen_prefixed_string_is_the_one_that_needed_a_special_case() -> None:
    """Pins WHY `-J` is in the prefix list, so a tidy-up does not remove it.

    It begins with a hyphen, so no word prefix can reach it. It is also the
    reason the entry is `-J` and not `-J ` — with the trailing space the
    boundary would have to match the `(` that follows, and does not. The
    fixture caught that; reading the list would not have.
    """
    line = "-J (only generate a CUE sheet) cannot be used with -I (only print info)!"
    assert line in [m for _, m in _inventory()]
    assert _RIPPER_ERROR_RE.match(line)


def test_the_argument_parse_errors_are_covered() -> None:
    """These reach **stdout only** — argument validation runs before the
    logfile is opened, so there is no file to write them to (fork round 4, Q5).
    Our stdout capture is load-bearing for the whole class, and the pattern has
    to recognise them or the user gets "Rip failed" for a typo in a flag."""
    for message in (
        "Unable to parse command line argument: --bogus-flag",
        'Missing value for argument "--paranoia"',
        'Missing value for argument "--offset"',
    ):
        assert _RIPPER_ERROR_RE.match(message), message


def test_the_convergence_success_message_is_never_a_failure_hint() -> None:
    """THE ROUND-6 REGRESSION, and it came from a *good* change on their side.

    The fork replaced its hand-maintained list of `goto` labels with one
    discovered from source — right, and it took the inventory 104 -> 115. But one
    discovered label, `goto finalize_ripping`, is the `-Z` convergence **success**
    route, so `Done; (2 out of 2 matches for current checksum …)` — which means
    the secure re-reads AGREED — arrived classified as reachable on a failure path.

    Surfacing it would print a success sentence as the reason a rip failed, on
    exactly the rips where our secure re-read worked. Their own P5 preamble names
    the hazard: *"calling it fatal would file success lines as failures."*

    The asymmetry is why the exclusion is per-string and not per-label.
    """
    from platterpus.ripper_message_inventory import SURFACING_EXCLUDED

    success = "Done; (2 out of 2 matches for current checksum 2C926D69)"
    failure = "Done; (no matches found, but hit repeat limit of 2)"

    assert not _RIPPER_ERROR_RE.match(success), (
        "the -Z convergence success message would be reported as the reason a rip "
        "failed"
    )
    # ...and its sibling under the SAME label is a real problem statement and must
    # still surface. One label, two opposite meanings.
    assert _RIPPER_ERROR_RE.match(failure)

    # The exclusion is named, reasoned, and cannot grow silently.
    assert len(SURFACING_EXCLUDED) == 1, (
        f"the surfacing exclusion list changed to {SURFACING_EXCLUDED} — each entry "
        f"is a message the user will never be shown, so a new one is a decision"
    )
    text, reason = SURFACING_EXCLUDED[0]
    assert text.startswith("Done; (%i out of %i")
    assert "success" in reason.lower(), "an exclusion without a stated reason"


def test_every_other_inventory_row_still_reaches_the_user() -> None:
    """Floor on the exclusion: it must remove exactly one row, not act as a
    catch-all that quietly shrinks coverage.

    Stated as arithmetic over both inputs rather than as `MESSAGES - ALL_FORMATS`,
    which is what it was: that difference silently became **-1** the moment
    `RETAINED_BEYOND_P5` started contributing, so the old form could have been made
    green again by *dropping the retained rows* — the exact regression the retention
    exists to prevent. A check whose easiest repair is the bug is not a check.
    """
    from platterpus.ripper_message_inventory import (
        ALL_FORMATS,
        MESSAGES,
        RETAINED_BEYOND_P5,
        SURFACING_EXCLUDED,
    )

    assert len(ALL_FORMATS) == len(MESSAGES) + len(RETAINED_BEYOND_P5) - len(
        SURFACING_EXCLUDED
    )
    assert len(SURFACING_EXCLUDED) == 1
    assert len(ALL_FORMATS) >= 125, (
        f"surfacing coverage collapsed to {len(ALL_FORMATS)}"
    )


# --- the OUTPUT half of the staleness check, which did not exist -----------------
#
# `tests/test_argv_surface_agreement.py` has diffed every flag we send against the
# newest inbound round's P1 table, every commit, since the `-V` blocker. Nothing
# did the same for P5, so this file's inventory sat at round 6's 115 strings while
# rounds 7, 8, 9, 10 and 11 published 117, 120 and 130 — and the round-9 table has
# been COMMITTED IN THIS REPOSITORY since 2026-08-17.
#
# The two tests below are that missing half. They read the contract the fork
# actually sent, because the question can be settled by a committed artifact and
# anything else pins a belief about it.
#
# The round resolution is IMPORTED from the argv-surface test rather than rewritten.
# That file's own comments count four places in this repo that grew their own
# handshake round parser and four that broke on the 2026-08-04 renaming; a fifth
# copy here would be the same mistake with the same outcome. One naming convention,
# one reader.


def _newest_provider_contracts() -> list[tuple[int, Path]]:
    """Every committed inbound provider-contract artifact, newest round first."""
    import test_argv_surface_agreement as argv_surface

    found: list[tuple[int, Path]] = []
    for number, paths in argv_surface._group_by_round().items():
        for path in paths:
            if "provider-contract" in path.name:
                found.append((number, path))
    return sorted(found, key=lambda pair: pair[0], reverse=True)


#: A P5 row: ``| `genopt.h:598` | `Too many values …` | genopt | yes |``. The
#: message cell is fenced, and the generator escapes `"` and `|` inside it.
_P5_ROW = re.compile(
    r"^\|\s*`(?P<site>[^`]+)`\s*\|\s*`(?P<text>.*?)`\s*\|"
    r"\s*(?P<evidence>[^|]+?)\s*\|\s*(?P<logfile>[^|]+?)\s*\|\s*$",
    re.M,
)

#: Below this many rows a document is not publishing a P5 table. Their tables have
#: carried 115-130 rows since round 6, so this only ever needs to exclude prose.
_MIN_PUBLISHED_FATALS = 100


def _their_p5(text: str) -> list[tuple[str, str, str, bool]]:
    """The P5 table of one provider contract: (site, message, evidence, logfile).

    Sliced to the P5 section first. Without that, P2's two-column table and P3's
    three-column one both leak rows in through a permissive row regex, and the
    result is a check that agrees with itself about the wrong population — the
    round-6 defect this whole file is about, arriving through the parser.
    """
    heading = "## P5 - Fatal and error message inventory"
    if heading not in text:
        return []
    section = text[text.index(heading) + len(heading) :]
    if "\n## " in section:
        section = section[: section.index("\n## ")]
    rows: list[tuple[str, str, str, bool]] = []
    for match in _P5_ROW.finditer(section):
        message = match.group("text").replace('\\"', '"').replace("\\|", "|")
        if not message:
            continue
        rows.append(
            (
                match.group("site"),
                message,
                match.group("evidence"),
                match.group("logfile") == "yes",
            )
        )
    return rows


def test_the_inventory_is_not_behind_the_newest_published_contract() -> None:
    """THE CHECK THAT DID NOT EXIST, and its absence cost five rounds.

    Our inventory must BE the newest committed inbound P5 table — same strings,
    same sites, same evidence, same order. Not "a superset of", not "close to":
    the evidence column is what tells a hard fatal from a `goto end`, and the sites
    are what makes a claim about this seam re-checkable.

    A stale inventory is not a cosmetic problem. When this test was written the
    inventory was 13 rounds' worth of strings short, two of which matched **nothing**
    in the live matcher, so a user hitting either saw a bare "Rip failed."
    """
    contracts = _newest_provider_contracts()
    assert contracts, (
        "no inbound provider-contract artifact is committed — this check would "
        "otherwise pass by finding nothing to compare against"
    )
    round_number, path = contracts[0]
    published = _their_p5(path.read_text(encoding="utf-8"))
    assert len(published) >= _MIN_PUBLISHED_FATALS, (
        f"{path.name} (round {round_number}) yielded only {len(published)} P5 rows; "
        f"a table that small means the parser missed the section, not that the "
        f"ripper got quieter"
    )

    from platterpus.ripper_message_inventory import MESSAGES

    ours = [(m.site, m.text, m.evidence, m.reaches_logfile) for m in MESSAGES]
    theirs_texts = {row[1] for row in published}
    our_texts = {row[1] for row in ours}

    assert not theirs_texts - our_texts, (
        f"round {round_number} ({path.name}) publishes strings our inventory does "
        f"not carry, so the matcher is built without them: "
        + "; ".join(sorted(theirs_texts - our_texts))
    )
    assert not our_texts - theirs_texts, (
        f"our inventory carries strings round {round_number} does not publish — if "
        f"they were REMOVED rather than invented, they belong in RETAINED_BEYOND_P5 "
        f"with the reason: " + "; ".join(sorted(our_texts - theirs_texts))
    )
    assert ours == published, (
        f"the inventory and {path.name} agree on the strings but not on the rows — "
        f"a site or evidence class moved, and the evidence class is what decides "
        f"whether a message may be treated as a hard failure"
    )


def test_a_string_removed_from_p5_is_retained_rather_than_dropped() -> None:
    """A removal from their generator's population is not proof of silence.

    Round 12 dropped `Force quitting` and `No FUN512 checksum found in "%s"!` from
    P5: the first moved to a raw `write(2)` because a signal handler may not use
    stdio (their §D5, which says outright that it *"still appears on stdout"*), the
    second was reclassified to P3, whose own preamble says *"appearing here does not
    mean a line is harmless."* Neither is reachable by any word in the prefix
    fallback, so following the generator would have taken two live diagnostics
    straight back to "Rip failed."

    Checked against the PREVIOUS committed contract, so a retained row has to be a
    string the fork really published — this list cannot become a place to smuggle in
    strings nobody sent.
    """
    from platterpus.ripper_message_inventory import ALL_FORMATS, RETAINED_BEYOND_P5

    contracts = _newest_provider_contracts()
    assert len(contracts) >= 2, (
        "need two published contracts to compare; with one there is no removal to "
        "detect and this test would pass by finding nothing"
    )
    previous_round, previous_path = contracts[1]
    previous = _their_p5(previous_path.read_text(encoding="utf-8"))
    assert len(previous) >= _MIN_PUBLISHED_FATALS, (
        f"{previous_path.name} yielded only {len(previous)} P5 rows"
    )

    surfaced = set(ALL_FORMATS)
    from platterpus.ripper_message_inventory import SURFACING_EXCLUDED

    excluded = {text for text, _ in SURFACING_EXCLUDED}
    lost = [text for _, text, _, _ in previous if text not in surfaced | excluded]
    assert not lost, (
        f"round {previous_round} published these and we no longer match them: "
        + "; ".join(sorted(lost))
    )

    # ...and the retention is load-bearing, not decorative: each entry must be a
    # string the fork HAS published at some point, must NOT be in the current
    # table, must carry a reason, and must still reach the matcher.
    #
    # "has published at some point" and not "is in the previous contract": the row
    # stays retained as later rounds arrive, and pinning it to `contracts[1]` would
    # turn this into a test that fails on the round AFTER the removal for a reason
    # that is not a defect. Scanning every committed contract keeps the real
    # guarantee — the string was sent to us — without a built-in expiry.
    ever_published: set[str] = set()
    for _, path in contracts:
        ever_published.update(text for _, text, _, _ in _their_p5(path.read_text()))
    assert len(ever_published) >= _MIN_PUBLISHED_FATALS

    from platterpus.ripper_message_inventory import MESSAGES

    current_texts = {m.text for m in MESSAGES}
    assert RETAINED_BEYOND_P5, "no retained rows — see the docstring; 12 removed two"
    for message, reason in RETAINED_BEYOND_P5:
        assert message.text in ever_published, (
            f"{message.text!r} is retained but no committed provider contract has "
            f"ever published it — a retained row must be one they sent"
        )
        assert message.text not in current_texts, (
            f"{message.text!r} is in the current P5; it belongs in MESSAGES, not in "
            f"the retention list"
        )
        assert len(reason) > 60, f"a retained row without a stated reason: {message}"
        assert _RIPPER_ERROR_RE.match(_sample(message.text)), (
            f"retained and still not surfaced, which is the worst of both: "
            f"{message.text!r}"
        )


def test_the_option_parser_diagnostics_are_surfaced() -> None:
    """THE REGRESSION, string by string.

    `genopt.h` is cyanrip's option parser. Its diagnostics were absent from every
    provider contract before round 9 lap 3 — not because they were not emitted, but
    because the generator's source scan had no pattern for `GEN_OPT_LOG`. Their round
    8 lap 1 §D2: *"These messages were always emitted. Only the document was
    incomplete."*

    Ten arrived at once. Eight were caught by the word-prefix fallback, which is
    forward tolerance and not coverage — and that partial rescue is exactly why the
    staleness went unnoticed. **Two matched nothing at all**, and each was a bare
    "Rip failed." to anyone who hit it:

        genopt.h:564  Programming error, incorrect type for: %s
        genopt.h:598  Too many values for argument "%s" (at most %i)

    The second is an ordinary user mistake — one `-t` too many on a command line —
    and every argument-parse failure reaches stdout ONLY, before the logfile exists,
    so our stdout capture is the sole route it has to a bug report.
    """
    matched_nothing_before = (
        "Programming error, incorrect type for: cyanrip_something",
        'Too many values for argument "--track" (at most 4)',
    )
    caught_only_by_a_prefix_before = (
        'Error parsing "abc" as a <type> for argument "--paranoia"',
        'Error parsing 3.5 for argument "--speed": not in [1.0:16.0] range!',
        'Error parsing 99 for argument "--paranoia": not in [0:3] range!',
        'Error parsing 99 for argument "--offset": not in [0:1000] range!',
        'Error parsing value for argument "--device"',
        'Error parsing 3.5 for argument "--speed": range [1.0:16.0]!',
        "Unable to parse command line argument: --bogus",
        'Missing value for argument "--offset"',
    )
    everything = matched_nothing_before + caught_only_by_a_prefix_before
    assert len(everything) == 10, "round 9 added exactly ten genopt rows"

    missed = [line for line in everything if not _RIPPER_ERROR_RE.match(line)]
    assert not missed, "still a bare 'Rip failed': " + "; ".join(missed)

    # The two are also in the inventory now, which is what makes them independent of
    # the prefix fallback: a future narrowing of the prefixes cannot un-cover them.
    from platterpus.ripper_message_inventory import ALL_FORMATS

    for fmt in (
        "Programming error, incorrect type for: %s",
        'Too many values for argument "%s" (at most %i)',
    ):
        assert fmt in ALL_FORMATS, f"{fmt!r} is matched only by a prefix guess"


def test_the_option_parser_regression_is_not_carried_by_the_prefixes() -> None:
    """Revert-proof in code, for the half of the fix a prefix could fake.

    Eight of the ten genopt strings begin with `Error` or `Missing` or `Unable to`,
    so they would match with the inventory reverted — which is how the gap survived
    two rounds of green suites. These two do not begin with anything in the prefix
    list, so a matcher built from the prefixes ALONE must fail on them. If this ever
    passes, the prefixes have been widened into the thing the inventory is for and
    the next stale round will hide behind them again.
    """
    from platterpus.ripper_messages import build_matcher
    from platterpus.workers.rip_worker import _RIPPER_ERROR_PREFIXES

    prefixes_only, _ = build_matcher([], extra_prefixes=_RIPPER_ERROR_PREFIXES)
    for line in (
        "Programming error, incorrect type for: cyanrip_something",
        'Too many values for argument "--track" (at most 4)',
    ):
        assert not prefixes_only.match(line), (
            f"the prefix fallback now matches {line!r} on its own, so this file can "
            f"no longer tell inventory coverage from a lucky opening word"
        )
        assert _RIPPER_ERROR_RE.match(line), line


def test_the_signal_handler_failure_surfaces() -> None:
    """`Can't init %s handler!` — the contraction the prefix list had missed.

    `Cannot`, `Could not` and `Couldn't` were all in `_RIPPER_ERROR_PREFIXES`;
    `Can't` was not, and this line has been in the fork's P2 table since round 7
    lap 25 while matching nothing here.

    It is a PREFIX addition rather than an inventory row, deliberately: the string
    is not in P5, and P5 is the provider's authority on failure-path reachability.
    Adding a row we were never sent would be the guessing this subsystem was rebuilt
    to stop. The prefixes are the forward-tolerance member of the union, and this is
    exactly what that member is for.
    """
    assert _RIPPER_ERROR_RE.match("Can't init SIGINT handler!")
    # ...and the widening's cost was measured, not assumed: across round 12's whole
    # 296-row P2 table, this is the only row with a `Can't`/`Cannot` shape, and no
    # other P2 line began matching. The near-miss control:
    assert not _RIPPER_ERROR_RE.match("Cantilever bridge")


def test_the_secure_reread_verdict_is_in_the_inventory_but_is_NOT_a_failure() -> None:
    """The relation the 2026-09-03 bundle broke: in the inventory != fatal.

    `Done; (no matches found, but hit repeat limit of %i)` is a published cyanrip
    format string, so `_RIPPER_ERROR_RE` — which is *built from* that inventory —
    matches it, correctly and by construction. What it cannot answer is whether
    the ripper FAILED, and the worker read the match as if it could.

    Measured, in the acceptance bundle's own diagnostics record: a disc that
    finished `Ripping errors: 0` with an intact completion footer and all 14 tracks
    written reported ``errors: 13  warnings: 1  info: 0`` and ``worst: error``.
    Every one of the 13 was this line — the secure re-read declining to certify a
    track it could not reproduce, which is the machinery WORKING.

    Both halves are asserted, because the fix is the relation and neither half
    alone states it: the matcher must still match (dropping it from the inventory
    would be the wrong repair, and would blind us to a genuine new fatal opening
    the same way), and the parser that owns the fact must still classify it as a
    re-read verdict.
    """
    from platterpus.parsers.cyanrip_log import is_secure_rerip_verdict

    line = "Done; (no matches found, but hit repeat limit of 3)"
    assert _RIPPER_ERROR_RE.match(line), (
        "the inventory no longer carries the secure re-read verdict — if the fork "
        "removed it, this test's premise changed; if we dropped it, we have "
        "narrowed the fatal matcher to fix a classification bug, which is the "
        "wrong end"
    )
    assert is_secure_rerip_verdict(line), (
        "the parser that owns read stability no longer recognises the line the "
        "worker defers to it about, so the worker is back to grading a "
        "non-convergent track as a fatal error"
    )

    # The convergent shape is the same event reported the other way, and is
    # likewise not a failure.
    assert is_secure_rerip_verdict(
        "  Done; (2 out of 2 matches for current checksum ABCD1234)"
    )

    # The control: a real fatal must NOT be swallowed by the new exclusion. This is
    # the failure mode the reclassification could introduce, so it is pinned here
    # rather than left to inspection.
    assert not is_secure_rerip_verdict("Invalid track number 17, list has 16 tracks!")
    assert _RIPPER_ERROR_RE.match("Invalid track number 17, list has 16 tracks!")
