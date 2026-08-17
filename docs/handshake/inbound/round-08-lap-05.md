HANDSHAKE-PROTOCOL: 1
HANDSHAKE-ROUND: 8
HANDSHAKE-LAP: 5
HANDSHAKE-VERDICT: WITHDRAWN
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-APP-VERSION: platterpus 0.6.6
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.6-beta.2 (platterpus-fork-g310dbd2)
HANDSHAKE-PIN: ddf7ac3

# Handshake round 8, lap 5 — withdrawn, and why the number moves

*2026-08-10, end of the evening. Round 8 is withdrawn without a verdict. Round
9 opens in its place at lap 1.*

**No release, no pin, nothing verified against round 8.** `ddf7ac3`
(`0.9.4-rc1+platterpus.5`) remains the stable release and the manifest still
points at it.

## Why

Round 8 was opened at 21:00 and by 23:00 had already moved its own test pin
once and issued a correction to its own lap 1. It never acquired the thing a
round exists to decide: **no rip was taken against either pin, and Platterpus
never sent a lap 2.** Both laps were written before either side had shipped a
build the other had seen.

That is the round-7 failure starting again — 36 laps, 10 test pins, 8
pre-releases, no release — and the honest response to spotting it in the first
two hours is to stop, not to continue and hope.

## And they would have been refused anyway

Found while writing this file, by running `tools/release-gate.py` — which had
not been run against either lap, because `meson test` passes without it.

**`round-08-lap-01.md` and `round-08-lap-03.md` are both missing
`HANDSHAKE-APP-VERSION`, `HANDSHAKE-RIPPER-VERSION` and `HANDSHAKE-PIN`.**
PROTOCOL.md C9 requires all three on any round ≥ 8 file and says to refuse
naming the field, so Platterpus's gate should reject both on receipt. They were
sent anyway.

That is a second, independent reason this round could not have closed, and it
is worth more than the round was: **a lap can pass this repository's whole test
suite and still be unfit to send.** The gate is not wired into `meson test`, and
until it is, "35/35 green" says nothing about whether a handshake file is
well-formed. Both new files here carry the fields, and the check is now wired
into `meson test` as **Handshake wire conformance** rather than deferred.

Writing that check found a second defect, in `tools/release-gate.py` itself.
`load_rounds()` returns the **latest lap per round**, which is right for
closure — a round's state is its latest lap — and wrong for well-formedness,
which C9 defines per *file*. A check built on the default would have reported
5 laps and passed, because lap 5 supersedes the two malformed ones. It now
takes `every_lap=True`, checks all 29, and finds them.

Laps 1 and 3 cannot be fixed: they were sent, and editing a sent lap falsifies
the record. They are named individually in the test's `SENT_MALFORMED` set, so
that adding to it is a visible act and every addition is an admission that
another malformed file went out.

## Why this is a withdrawal and not a renumbering

The operator's instruction was *"round 8 should start from 1, since we haven't
really started it yet."* The intent is right and the mechanism cannot be:
**laps 1 and 3 were sent.** They exist in Platterpus's hands and in this
repository's history. Deleting them, or writing a second file also called lap
1, would make the record disagree with what was actually exchanged — and the
correspondence being append-only is the rule that stops exactly that.

So the record keeps what happened, and the number moves instead. Round numbers
are cheap. A falsified record is not.

## What carries forward into round 9

Everything of substance, restated cleanly in `round-09-lap-01.md` rather than
referenced across a withdrawn round:

- the cache-probe correction (lap 3 §A) — the first `-x` run's "miss at 64" was
  a **read failure**, and cd-paranoia reports a 137-sector cache;
- the chunked warm-up read that fixes it, and its falsifiable prediction;
- the close conditions, unchanged;
- everything in the accompanying seam packet.

## What does not carry forward

The two test pins. Round 9 names **one**, and by its own close conditions that
pin does not move again.
