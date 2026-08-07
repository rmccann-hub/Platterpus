"""Property-based tests for the six external-output parsers.

(The docstring said "the three whipper-output parsers" until 2026-07-31. It was
written when there were three and whipper was the backend; the imports below now
cover six — `cd_info`, `cyanrip_info`, `cyanrip_log`, `drive_list`, `eac_log` and
`rip_log` — and cyanrip has been the sole backend since KDD-18. **The import list
is the roster**, the way it is in `test_surface_consistency.py`: a parser absent
from it is not fuzzed here.)

These complement the example-based `test_parsers_*` files. Example tests
prove the parsers handle the *known* shapes; these prove they uphold a
hard invariant across a huge space of *unknown* inputs:

    A parser must NEVER raise on arbitrary text — it degrades to empty /
    default values instead.

That invariant is exactly what a real-hardware regression needs: an external CLI's
output can drift between releases, and the GUI calls these parsers at startup
(drive list) and after a rip (log). A parser that throws on unexpected bytes is
what makes the whole window vanish — see the startup-resilience fix. Hypothesis
generates hundreds of adversarial inputs and shrinks any failure to a minimal
reproducer.

**What Hypothesis cannot reach, and where that lives instead.** Random text never
produces a 4301-digit run, so the CPython integer-conversion ceiling is invisible
to the fuzzer — every parser here passed while six of them raised on it. The
boundary is pinned explicitly: for `cyanrip_log` in
`test_an_absurdly_long_number_never_raises` below, and across every parser (plus a
structural sweep for new unguarded conversions) in
`tests/test_never_raises_contract.py`. A green run here is not the whole contract.

Hypothesis docs: https://hypothesis.readthedocs.io/
"""

from __future__ import annotations

import json
import re

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from platterpus.deps.ripper_manifest import parse_manifest
from platterpus.parsers.cd_info import DiscInfo, parse_cd_info
from platterpus.parsers.cyanrip_info import parse_cyanrip_info
from platterpus.parsers.cyanrip_log import looks_like_cyanrip_log, parse_cyanrip_log
from platterpus.parsers.drive_list import DriveDescriptor, parse_drive_list
from platterpus.parsers.eac_log import looks_like_eac_log, parse_eac_copy_crcs
from platterpus.parsers.rip_log import RipLog, parse_rip_log

# `deadline=None`: the parsers are fast, but CI runners are noisy and we
# don't want a timing blip to fail a correctness test.
_SETTINGS = settings(max_examples=300, deadline=None)


# --- A vocabulary of plausible-but-mangled whipper lines ------------------
#
# Pure st.text() is great for "never crash", but most random strings miss
# the parser's interesting branches. This strategy mixes real whipper line
# shapes (with random fills) and garbage, so the state machines actually
# get exercised on near-miss input — the "unexpected" tier of cases.

_FRAGMENTS = st.sampled_from(
    [
        "drive: /dev/sr0, vendor: ACME, model: X, release: 1.0",
        "drive: , vendor: , model: , release: ",  # empty-ish fields
        "       Configured read offset: 667",
        "       Configured read offset: not-a-number",  # bad int
        "       Can defeat audio cache: True",
        "       Can defeat audio cache: maybe",  # unrecognized bool
        "CDDB disc id: 940A6A0B",
        "MusicBrainz disc id wzr8h2ssXg4",
        "Disc duration: 01:02:08.026, 16 audio tracks",
        "Disc duration: ?, audio tracks",  # no number
        "Tracks:",
        # --- v0.5.12 EAC-layout fields. Without these the fuzzer cannot steer
        # into the new branches at all: st.text() will never emit "Start LSN:"
        # by chance, so the never-raises property was silently not covering them
        # (review finding, 2026-07-28). Each shape includes a hostile variant.
        "Album:          Every Breath You Take: The Classics",
        "Album:          ",  # padded, value-less — must not become " "
        "Album artist:   The Police",
        "C2 errors:      unsupported by drive",
        "C2 errors:      supported by drive",  # capability, NOT use
        "C2 errors:      ",
        "Paranoia level: max",
        "Paranoia level: none",
        "Paranoia level: wibble",  # unrecognised → must not become "Secure"
        "    Start LSN:   0 (with offset: 1)",
        "    End LSN:     14486 (with offset: 14488)",
        "    Start LSN:   99999999999999999999999999",  # huge but parseable
        "    End LSN:     " + "9" * 4400,  # over CPython's int() digit ceiling
        "    Start LSN:   500",
        "    End LSN:     4",  # end < start — inverted geometry
        "    Pregap LSN:  none",
        "    Pregap LSN:  150",
        "Gaps:",
        "    None signalled",
        "Overread mode:  fill with silence in lead-in/lead-out",
        "  1:",
        "    Peak level: 0.9",
        "    Peak level: not-a-float",  # bad float
        "    Extraction speed: 8.0 X",
        "    Extraction quality: 100.00 %",
        "    AccurateRip v1:",
        "      Confidence: 5",
        "      Confidence: lots",  # bad int
        "Log created by: whipper 0.10.0",
        "SHA-256 hash: deadbeef",
        # cyanrip -I report shapes (exercise the cyanrip_info parser).
        "Disc tracks:    16",
        "Disc tracks:    many",  # bad int
        "DiscID:         xA2hjkk0Jl0gKKtIdYuTje4JTXY-",
        "CDDB ID:        c50a780f",
        "MusicBrainz URL:",
        "https://musicbrainz.org/cdtoc/attach?id=x",
        "(null)",  # printf'd NULL after the URL label
        # cyanrip log shapes (exercise the cyanrip_log parser).
        "Track 5 ripped and encoded successfully!",
        "Track 5 ripped and encoded with errors.",
        "  EAC CRC32:     A1B2C3D4 (after 2 rips)",
        "    Accurip v1:  12345678 (accurately ripped, confidence 3)",
        "    Accurip v1:  12345678 (confidence lots)",  # bad int
        "Offset:         +667 samples",
        "Tracks ripped accurately: 1/2",
        "Ripping errors: many",  # bad int
        # EAC log shapes (exercise the eac_log parser).
        "Exact Audio Copy V1.8 from 15. July 2024",
        "Track  1",
        "Track  not-a-number",  # bad track number
        "     Copy CRC B0D122E7",
        "     Copy CRC nothex!!",  # not 8 hex digits
        "     Test CRC B0D122E7",
        ":::::",  # degenerate colons
        "",  # blank line
        "\t\t\t",  # whitespace only
    ]
)

_noisy_text = st.lists(_FRAGMENTS, max_size=40).map("\n".join)

# The full input strategy: either fully-random text or noisy whipper-ish text.
_any_text = st.one_of(st.text(max_size=2000), _noisy_text)


# --- Invariant 1: never raises, always returns the right type -------------


@_SETTINGS
@given(_any_text)
def test_parse_drive_list_never_raises(text: str) -> None:
    result = parse_drive_list(text)
    assert isinstance(result, list)
    for drive in result:
        assert isinstance(drive, DriveDescriptor)
        # Declared optional-numeric fields hold their declared types.
        assert drive.read_offset is None or isinstance(drive.read_offset, int)
        assert drive.cache_defeat is None or isinstance(drive.cache_defeat, bool)
        assert isinstance(drive.device, str)


@_SETTINGS
@given(_any_text)
def test_parse_cd_info_never_raises(text: str) -> None:
    result = parse_cd_info(text)
    assert isinstance(result, DiscInfo)
    assert isinstance(result.num_tracks, int)
    assert result.num_tracks >= 0


@_SETTINGS
@given(_any_text)
def test_parse_cyanrip_info_never_raises(text: str) -> None:
    result = parse_cyanrip_info(text)
    assert isinstance(result, DiscInfo)
    assert isinstance(result.num_tracks, int)
    assert result.num_tracks >= 0


@_SETTINGS
@given(_any_text)
def test_parse_cyanrip_log_never_raises(text: str) -> None:
    result = parse_cyanrip_log(text)
    assert isinstance(result, RipLog)
    for track in result.tracks:
        assert isinstance(track.number, int)
        for ar in (track.accuraterip_v1, track.accuraterip_v2):
            if ar is not None:
                assert ar.confidence is None or isinstance(ar.confidence, int)


@_SETTINGS
@given(_any_text)
def test_parse_rip_log_never_raises(text: str) -> None:
    result = parse_rip_log(text)
    assert isinstance(result, RipLog)
    assert isinstance(result.tracks, tuple)
    for track in result.tracks:
        assert isinstance(track.number, int)
        # Optional numerics keep their declared types or stay None.
        assert track.peak_level is None or isinstance(track.peak_level, float)
        assert track.extraction_speed is None or isinstance(
            track.extraction_speed, float
        )
        for ar in (track.accuraterip_v1, track.accuraterip_v2):
            if ar is not None:
                assert ar.confidence is None or isinstance(ar.confidence, int)


@_SETTINGS
@given(_any_text)
def test_parse_eac_copy_crcs_never_raises(text: str) -> None:
    result = parse_eac_copy_crcs(text)
    assert isinstance(result, dict)
    for number, crc in result.items():
        assert isinstance(number, int)
        # Only 8-hex-digit Copy CRCs are captured, always upper-cased.
        assert isinstance(crc, str) and len(crc) == 8
        assert crc == crc.upper()


@_SETTINGS
@given(_any_text)
def test_looks_like_log_sniffers_never_raise(text: str) -> None:
    """The format sniffers (used by the finish handler to pick a log parser)
    consume arbitrary text too, so they must classify, not crash."""
    assert isinstance(looks_like_cyanrip_log(text), bool)
    assert isinstance(looks_like_eac_log(text), bool)


# --- Invariant 2: a well-formed drive block round-trips -------------------
#
# If we synthesise a *valid* drive block, the parser must recover its
# fields exactly. This guards against over-eager "degrade to empty"
# behaviour swallowing good data.

_word = st.from_regex(r"[A-Za-z0-9 ]{1,12}", fullmatch=True)
_device = st.from_regex(r"/dev/sr[0-9]", fullmatch=True)
_release = st.from_regex(r"[0-9]{1,2}\.[0-9]{1,2}", fullmatch=True)


@_SETTINGS
@given(
    device=_device,
    vendor=_word,
    model=_word,
    release=_release,
    offset=st.integers(min_value=-2000, max_value=2000),
    cache=st.booleans(),
)
def test_drive_block_round_trips(
    device: str,
    vendor: str,
    model: str,
    release: str,
    offset: int,
    cache: bool,
) -> None:
    # vendor/model are .strip()'d by the parser; only compare meaningfully
    # when they survive stripping.
    block = (
        f"drive: {device}, vendor: {vendor}, model: {model}, release: {release}\n"
        f"       Configured read offset: {offset}\n"
        f"       Can defeat audio cache: {cache}\n"
    )
    drives = parse_drive_list(block)
    assert len(drives) == 1
    d = drives[0]
    assert d.device == device
    assert d.vendor == vendor.strip()
    assert d.model == model.strip()
    assert d.release == release
    assert d.read_offset == offset
    assert d.cache_defeat is cache


# --- Invariant 3: a metamorphic property ----------------------------------
#
# Concatenating N independent single-drive blocks yields exactly N drives.
# (Whipper prints one block per call, but multi-drive output is on the
# roadmap; this pins the accumulator's flush logic.)


@_SETTINGS
@given(n=st.integers(min_value=0, max_value=8))
def test_concatenated_drive_blocks_count(n: int) -> None:
    block = "drive: /dev/sr0, vendor: ACME, model: X, release: 1.0\n"
    drives = parse_drive_list(block * n)
    assert len(drives) == n


# --- CPython's int() digit ceiling: a boundary, so tested as one -------------
#
# `int(str)` refuses more than 4300 digits (CPython >= 3.11), which made every
# unguarded numeric field in the cyanrip parser a never-raises hole — seven of
# them, all demonstrated raising (review finding, 2026-07-28). Hypothesis cannot
# find this unaided: a 4301-digit run never appears by chance in `st.text()`.
# Steering the fuzzer at it DID work, but cost 2m14s per run to rediscover one
# deterministic boundary — so it is pinned explicitly instead: cheaper, and it
# names the exact field that regressed when it fails.
_OVER_THE_DIGIT_LIMIT = "9" * 4301


@pytest.mark.parametrize(
    "line",
    [
        f"Offset:         +{_OVER_THE_DIGIT_LIMIT} samples",
        f"Track {_OVER_THE_DIGIT_LIMIT} ripped and encoded successfully!",
        f"Ripping errors: {_OVER_THE_DIGIT_LIMIT}",
        f"    READ:          {_OVER_THE_DIGIT_LIMIT}",
        f"    Start LSN:   {_OVER_THE_DIGIT_LIMIT}",
        f"    End LSN:     {_OVER_THE_DIGIT_LIMIT}",
        f"    Pregap LSN:  {_OVER_THE_DIGIT_LIMIT}",
        f"  EAC CRC32:     A1B2C3D4 (after {_OVER_THE_DIGIT_LIMIT} rips)",
        f"  Accurip v1:  1234 (accurately ripped, confidence {_OVER_THE_DIGIT_LIMIT})",
        f"  Accurip 450: BF62 (matches Accurip DB, confidence {_OVER_THE_DIGIT_LIMIT})",
    ],
)
def test_an_absurdly_long_number_never_raises(line: str) -> None:
    """Every numeric field degrades to unknown instead of raising."""
    text = "\n".join(
        [
            "cyanrip 0.9.3",
            "Paranoia status counts:",
            "Track 1 ripped and encoded successfully!",
            line,
        ]
    )
    parse_cyanrip_log(text)  # must not raise


# --- The cyanrip fork's release manifest -------------------------------------
#
# Same contract as every other parser of external output: a best-effort answer or
# None, never an exception. This one is worth the property test twice over, because
# its `commit` field becomes an argument to `git checkout` inside the container — so
# "it did not raise" is the weaker half of what is being asserted here, and "it never
# emitted a commit we would not hand to a shell" is the stronger half.


@given(st.text(max_size=4000))
@settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])
def test_manifest_parse_never_raises_on_arbitrary_text(text: str) -> None:
    parse_manifest(text)  # must not raise


@given(
    st.recursive(
        st.none()
        | st.booleans()
        | st.integers()
        | st.floats(allow_nan=False, allow_infinity=False)
        | st.text(max_size=80),
        lambda children: (
            st.lists(children, max_size=6)
            | st.dictionaries(st.text(max_size=24), children, max_size=6)
        ),
        max_leaves=25,
    )
)
@settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])
def test_manifest_parse_never_raises_on_arbitrary_json(document: object) -> None:
    """Well-formed JSON of an arbitrary *shape* — the case plain text never reaches.

    Random text is almost never valid JSON, so it exercises the `json.loads` guard
    and little else. Generating structures instead is what actually reaches the
    field-by-field validation, which is where a wrong `isinstance` would live.
    """
    parse_manifest(json.dumps(document))


@given(st.text(max_size=200))
@settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])
def test_a_parsed_commit_is_always_shell_safe(commit: str) -> None:
    """**The property that matters, stated over all inputs rather than a fixture list.**

    Whatever the manifest says, anything that survives into a `RipperRelease` must be
    a bare lowercase hex sha of 7–40 characters. A table of hand-picked nasty strings
    proves the ones someone thought of; this proves the shape.
    """
    document = {
        "schema": 1,
        "project": "cyanrip-fork",
        "default_channel": "stable",
        "channels": {
            "stable": {
                "version": "0.9.4-rc1+platterpus.5",
                "commit": commit,
                "release_seq": 11,
                "handshake_round": 7,
                "round_closed": True,
                "install": "https://github.com/rmccann-hub/cyanrip/archive/x.tar.gz",
            }
        },
    }
    parsed = parse_manifest(json.dumps(document))
    if parsed is None:
        return
    row = parsed.channel("stable")
    if row is None:
        return
    assert re.fullmatch(r"[0-9a-f]{7,40}", row.commit), (
        f"a commit that reaches the build step must be a bare hex sha, got {row.commit!r}"
    )
