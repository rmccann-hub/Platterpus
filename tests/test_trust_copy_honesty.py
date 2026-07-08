"""Regression tests for the trust-claim honesty audit (2026-07-08).

The project's north star is that Platterpus never *overclaims* a rip's
trustworthiness (docs/ux-design-principles.md, verdict.py). An adversarial sweep
of every user-facing "verified / bit-perfect / secure / trustworthy" claim found
a cluster of copy defects — an overclaim in the User Guide's grey-verdict
explanation and a set of stale "experimental" CTDB caveats left behind when the
CTDB CRC gate was hardware-validated (KDD-16, ``crc.CRC_VALIDATED`` → True).

These tests pin the *honest* wording so a future edit can't silently
re-introduce an overclaim. They assert on stable keywords, not whole sentences,
so they lock the invariant without being brittle about phrasing.
"""

from __future__ import annotations

from platterpus.help_content import USER_GUIDE


def test_grey_verdict_does_not_claim_a_secure_read() -> None:
    """The grey / "no tracks matched" explanation must NOT say the Copy CRC
    proves a secure read — a lone Copy CRC only proves lossless encoding, not
    that the read (or the offset) was correct. This is the canonical honesty
    line from verdict.py; a wrong-offset rip has a self-consistent Copy CRC."""
    assert "read securely" not in USER_GUIDE
    # It must keep the honest framing: the Copy CRC proves only lossless encoding,
    # not a correct read. (Assert single-line tokens so prose re-wrapping in the
    # triple-quoted guide can't make a multi-word phrase span a newline.)
    assert "losslessly encodes" in USER_GUIDE
    assert "the read itself was correct" in USER_GUIDE
    assert "isn't independently verified" in USER_GUIDE


def test_user_guide_has_no_stale_experimental_ctdb_caveat() -> None:
    """After the KDD-16 hardware validation, a CTDB match reads as *verified*.
    The User Guide must not still describe CTDB as "experimental" or imply a
    match can only show amber."""
    assert "experimental" not in USER_GUIDE.lower()
    # The CTDB result section should say a match is verified / hardware-confirmed.
    assert "hardware-confirmed" in USER_GUIDE


def test_user_guide_does_not_overclaim_reread_convergence() -> None:
    """Repeated agreeing re-reads prove a *stable/repeatable* read, not a
    bit-perfect one — only AccurateRip/CTDB establishes bit-perfection."""
    assert "converges on the bit-perfect result" not in USER_GUIDE
    assert "converges on a stable, repeatable read" in USER_GUIDE


def test_user_guide_offset_is_necessary_not_sufficient() -> None:
    """A correct read offset is necessary for a bit-perfect rip but not
    sufficient (a scratched disc with the right offset still isn't bit-perfect),
    so the guide must not say the offset is "the one calibration that makes rips
    bit-perfect"."""
    assert "the one calibration that makes rips" not in USER_GUIDE
    assert "won't match AccurateRip" in USER_GUIDE
