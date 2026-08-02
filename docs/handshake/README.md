# Handshake correspondence with the cyanrip fork

Every file exchanged with the cyanrip fork, both directions, committed so the
record survives the session that produced it. The protocol itself is
[`../cyanrip-handshake.md`](../cyanrip-handshake.md); the tool that enforces it
is `scripts/handshake.py`.

```
outbound/round-N.md   what Platterpus sent   (protocol §3)
inbound/round-N.md    what the fork sent back (protocol §4)
verified/round-N.md   our verification of it  (protocol §2, step 5)
```

A round is **CLOSED** only when all three exist. `python scripts/handshake.py
--status` reports it, and **no release and no pin switch happens while any round
is OPEN.**

## These files are correspondence, not documentation

They are deliberately exempt from the doc version-stamp convention
(`tests/test_doc_version_stamps.py`). Stamping an inbound file would edit
another project's words; stamping an outbound one would make the committed copy
differ from what they actually received. A record that is not the record is
worthless. Their currency is the round number.

Do not edit a file here after it has been sent or received. If something in it
was wrong, that belongs in the **next** round's Corrections section — which is
the mechanism, and three of the five errors found so far arrived that way.

## Backfill note

Rounds 1–3 predate `scripts/handshake.py` and were recovered from the session
scratchpad, so their section shapes vary and `--check` will report rounds 1–3
against the current spec. That is expected: the spec grew (§I, the provider
contract, was added in round 4). Round 3's `inbound` is the fork's file verbatim.
