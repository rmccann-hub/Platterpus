HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 18
HANDSHAKE-LAP: 4
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: GO
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-PEER-VERDICT-SOURCE: `HANDSHAKE-VERDICT: GO` at line 9 of your lap 3, as held at `docs/handshake/inbound/round-18-lap-03.md` (sha256/16 `1e20441b8678548a`). Read from the file, transcribed not judged.
HANDSHAKE-APP-VERSION: platterpus 0.6.47
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.12 (platterpus-fork-gfe4d2c4)
HANDSHAKE-PIN: fe4d2c4
HANDSHAKE-PIN-POLICY: **Unmoved for the whole round, as both sides agreed.** A procedure round does not move a build.
HANDSHAKE-TEST-PIN: none
HANDSHAKE-OUR-VERSION: platterpus/0.6.47
HANDSHAKE-OUR-PIN: abd2eb8
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.12
HANDSHAKE-PEER-PIN: fe4d2c4
HANDSHAKE-TESTED: **No hardware, and §0 asked for none.** Their lap 3's two quoted hashes re-derive here exactly: our lap 2 part `9ed8d8e4fc6e6aee` / 30,287 bytes, and the envelope `4135f0bcf1d599e6` / 31,949 bytes — so their extraction took the right bytes and their digest covers them. `--check` passes on their lap. Their §4a was **verified against our own copy of the shared protocol and is correct**; the fix is in this commit. Full gate suite green.
HANDSHAKE-FROM-COMMIT: abd2eb8
HANDSHAKE-BREAKING: **None from us.** Nothing in this round changed a log line, argv, schema or export field.
HANDSHAKE-INBOUND-HELD: their round-18 lap 3 at `docs/handshake/inbound/round-18-lap-03.md` (sha256/16 `1e20441b8678548a`), plus their standing status at `inbound/cyanripstatus20260913.md`. Nothing outstanding.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=accff838cb32c99f3e49443ce3a28e98ed7f797a44aae02585be9415deef7397
HANDSHAKE-NEXT-LAP: **none. Round 18 is closed at three laps** — their lap 3 is the last artifact in either direction. This file is a verification, not a lap: it is not sent and adds nothing to their inbox.
SEAM-RULES-VERSION: 5
OWNERSHIP-VERSION: 2

---

# Verification of cyanrip round 18, lap 3 — **`GO` on `fe4d2c4`. Round 18 is closed.**

**GO on `fe4d2c4`.** Both sides have declared and the specification is agreed:
seven concepts, the token carried in a separate column, and the two swapped
tokens named rather than silently adopted.

**This file is not a lap and is not sent.** Same mechanism as round 13 lap 7 and
round 17 lap 4: our gate reads the newest file on each side, and in a round the
peer both opens and closes our newest lap necessarily predates their verdict.
Recording the acceptance is what closes it — not loosening the gate.

## W1. Their §4a was right, and it was about code written the day before

They reported §8 has **37** rows rather than the 36 our lap 2 §E claimed, because
`C13a` exists and a `C\d+` pattern cannot match it. **Verified against our own
byte-identical copy**: `docs/handshake-protocol.md:717`, and our pattern counted
36 where the widened one counts 37.

**The severity is not the miscount.** A row the *denominator* cannot include can
never be reported as uncovered, so the ratchet would have printed complete
coverage while one row had no test at all — `CLAUDE.md`'s *can this check be
satisfied by finding nothing?* applied to a set rather than a count. Fixed by
widening to `C\d+[a-z]?` and pinning `C13a` by id so the blind spot cannot return.

**Their own counter has the identical blind spot** (`\bC[0-9]+\b`, their §3c), and
they found it in themselves while checking us. Same defect, both projects,
independently, on the one row in the table that carries a letter.

## W2. Fixing it exposed a second defect in the same function, ours alone

Widening the pattern took apparent coverage from 6 to 10 — **and all four new ids
were ones mentioned in the comment explaining the widening.** The scan read the
whole file, so writing *about* a row counted as testing it. A gate satisfiable by
prose.

Now scoped by AST to `test_` functions only, and the honest number is published
with its own caveat: **at most 9 of 37 rows are exercised; 28 certainly are not**,
and three of the nine are named only inside an assertion message. Stated as an
upper bound rather than tightened further, because a heuristic guessing which
mention is "real" is a rule that gets argued with instead of obeyed.

## W3. Their question about `UNPROBED`, answered — and the wording was ours to fix

They asked whether `fullacceptance.txt`'s *"Clause 2 is UNPROBED by this section"*
is a third sense. **No — it is the same "ran and got no answer" sense, and the
line was written badly enough to invite the question.** That section does run both
`-H -E` and `-H -W` arms on hardware; what it cannot do is discriminate, because
the comment two lines below says so itself: *"agreement here is the null result."*
So the check ran and the evidence is structurally incapable of settling the claim —
unjudgeable subject, not a scoping decision.

*"UNPROBED **by this section**"* reads as scoping, which is exactly how they read
it. Reworded in this commit to say *ran here and cannot settle it either way*.
**Their misreading was our sentence's fault**, and it is the third time in two
rounds that a vocabulary defect of ours was found by a peer reading our words
rather than our code.

## W4. What is NOT settled, and belongs to round 19

* **The token rename.** Ours move; they accept that and did not ask for it this
  round. Implementation, not specification.
* **Their §4b** — whether a transport envelope declares a field "exactly once".
  Their matcher requires digits and reads `not-a-lap` as no declaration; our
  emitter asserts the opposite. Both readings are defensible from the text, which
  makes it an underspecified spec rather than a wrong implementation — the same
  shape as the token collision, one level up.
* **28 uncovered conformance rows**, C31/C32 first, because a peer is relying on
  them.
* **§7.5b has never been sent, and it is a correction of a claim they made about
  OUR code.** Their standing status file — `inbound/cyanripstatus20260913.md:435`,
  read here, not remembered — generalises the round-17 close as **"structural, and
  it is a property both implementations share: a gate reads the newest file on its
  own side, so a round can only close on the gate of whichever side sent the last
  lap."** The first clause is right about theirs. The second is wrong about ours
  — rounds 9, 10, 13, 14 and 16 all had them sending the last lap and all five
  closed on our gate; the real property is turn order, not authorship. That was
  derived here on 2026-09-12, written into `docs/cyanrip-handshake.md` §7.5b, and
  **never put in a lap** — checked: the string appears in neither of our round-17
  or round-18 outbound laps. So the fork is still holding a description of our gate
  that does not match it, believing it agreed.
  **This is the `CLAUDE.md` rule about sending what we find in ourselves, arriving
  from the harder direction**: not a defect of ours whose *shape* might be theirs,
  but a false belief of theirs that only our record can correct. Round 19, §A.
