"""A CTDB match outvoted by a stronger entry is not shown as verified (P1).

The claude-code-skills audit check of 2026-10-19 found 8 of the 26 shipped rips
of the reference disc reporting a green "CTDB: verified ✓ (confidence 1)". Each
matched an entry of confidence 1, very likely the owner's own EAC rip of
2026-06-11 carrying the same track-5 misread, while the strongest entry for the
disc had about 1,405 submissions behind it. And every one of those rips had a
track AccurateRip rejected.

The database CRCs and the matched CRC below are read from the real round-32
report, not typed. The report does not record each entry's confidence, so the
weights come from the audit: the matched entry at 1 (the report's own
`confidence`) and the strongest at 1,405 (the lower end of the audit's 1,405 to
1,409); every other entry is given 1.
"""

from __future__ import annotations

import json

import pytest
from evidence_paths import evidence

from platterpus.adapters.ctdb_client import CtdbEntry, CtdbLookupResult
from platterpus.ctdb import crc as crc_mod
from platterpus.ctdb.verify import CtdbVerifyResult, Verdict, _match_verdict
from platterpus.parsers.cyanrip_log import parse_cyanrip_log
from platterpus.rip_report import _ctdb
from platterpus.ui.rip_progress import ctdb_verdict_level, ctdb_verdict_line
from platterpus.verdict import accuraterip_rejected_count

REPORT = "docs/handshake/artifactsround32/round32fullwholediscreport.json"
LOG = "docs/handshake/artifactsround32/round32fullwholedisc.log"
STRONGEST = 1405


def _real_ctdb_block() -> dict[str, object]:
    block = json.loads(evidence(REPORT).read_text(encoding="utf-8"))["ctdb"]
    # Non-triviality: this is one of the eight rips the audit names.
    assert block["verdict"] == "match" and block["confidence"] == 1, block
    assert len(block["db_crcs"]) >= 100, block
    return block


def _lookup(block: dict[str, object]) -> tuple[CtdbLookupResult, int]:
    matched = int(str(block["matched_crc"]), 16)
    crcs = [int(c, 16) for c in block["db_crcs"]]  # type: ignore[union-attr]
    strongest = next(c for c in crcs if c != matched)
    entries = tuple(
        CtdbEntry(crc=c, confidence=STRONGEST if c == strongest else 1) for c in crcs
    )
    return CtdbLookupResult(entries=entries), matched


@pytest.fixture
def validated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(crc_mod, "CRC_VALIDATED", True)


def test_the_round_32_match_is_outvoted_and_not_trustworthy(validated: None) -> None:
    result = _match_verdict(*_lookup(_real_ctdb_block()))
    assert result.verdict is Verdict.MATCH
    assert result.confidence == 1
    assert result.best_confidence == STRONGEST
    assert result.outvoted is True
    assert result.trustworthy is False
    assert result.disagreeing_confidence == result.total_confidence - 1 > STRONGEST


def test_the_screen_says_the_weight_in_amber_not_verified(validated: None) -> None:
    result = _match_verdict(*_lookup(_real_ctdb_block()))
    line = ctdb_verdict_line(result)
    assert "verified" not in line.lower(), line
    assert "matched 1 of" in line and "disagree" in line, line
    assert ctdb_verdict_level(result) == "warn"


def test_the_report_carries_the_weight_and_the_narrowed_trust(validated: None) -> None:
    block = _ctdb(_match_verdict(*_lookup(_real_ctdb_block())))
    assert block is not None
    assert block["trustworthy"] is False
    assert block["outvoted"] is True
    assert block["best_confidence"] == STRONGEST


def test_a_plurality_match_stays_green_when_accuraterip_agrees(
    validated: None,
) -> None:
    entries = (
        CtdbEntry(crc=0xAAAA, confidence=50),
        CtdbEntry(crc=0xBBBB, confidence=3),
    )
    result = _match_verdict(CtdbLookupResult(entries=entries), 0xAAAA)
    assert result.outvoted is False and result.trustworthy is True
    assert ctdb_verdict_line(result).startswith("CTDB: verified ✓")
    assert ctdb_verdict_level(result) == "ok"


def test_a_plurality_match_is_amber_beside_a_track_accuraterip_rejected() -> None:
    """The second condition, on the real round-32 log: track 3 and track 5
    matched AccurateRip only at one frame, so a whole-disc match beside them is
    two checks disagreeing."""
    rip_log = parse_cyanrip_log(evidence(LOG).read_text(encoding="utf-8"))
    assert accuraterip_rejected_count(rip_log) >= 1
    plurality = CtdbVerifyResult(
        Verdict.MATCH, confidence=50, best_confidence=50, crc_validated=True
    )
    assert plurality.trustworthy is True
    assert ctdb_verdict_level(plurality) == "ok"
    assert ctdb_verdict_level(plurality, rip_log) == "warn"
