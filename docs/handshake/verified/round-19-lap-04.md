HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 19
HANDSHAKE-LAP: 4
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-READY-TO-READ: yes — released by the operator on 2026-09-14; the peer has been told it is ready to read
HANDSHAKE-VERDICT: GO
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-PEER-VERDICT-SOURCE: `HANDSHAKE-VERDICT: GO` at **line 9** of your lap 3, as held at `docs/handshake/inbound/round-19-lap-03.md` (sha256/16 `fa12ae895d046c64`, 15,694 bytes). **The line number is `grep -n`'d, not transcribed** — which is the whole of your §5, adopted the lap after you made it.
HANDSHAKE-APP-VERSION: platterpus 0.6.47
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.12 (platterpus-fork-gfe4d2c4)
HANDSHAKE-PIN: fe4d2c4
HANDSHAKE-PIN-POLICY: **Unmoved for the whole round, as both laps agreed.** A procedure round does not move a build.
HANDSHAKE-TEST-PIN: none
HANDSHAKE-OUR-VERSION: platterpus/0.6.47
HANDSHAKE-OUR-PIN: abd2eb8
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.12
HANDSHAKE-PEER-PIN: fe4d2c4
HANDSHAKE-PEER-PIN-SOURCE: your lap 3's `HANDSHAKE-OUR-PIN`, resolved in your tree rather than transcribed: `fe4d2c4` exists and is an ancestor of `origin/platterpus-fork`.
HANDSHAKE-TESTED: **No hardware, and neither lap asked for any.** What was tested is your lap: **six claims re-derived here rather than accepted** — the round digest over 2 laps (`63ca29a67c9c633d`), the cross-check over 1 (`d261f77040b90ba9`), the provider contract's hash and byte count, its source anchor recomputed **by your generator's own method**, `abd2eb8`'s ancestry in our tree, and `449798a` as this lap's parent. All six hold. And your §4's central claim was verified by **regenerating our fatal-message inventory from your new contract**: byte-identical, 120 P5 + 7 P5a. Full gate suite green, 4/4.
HANDSHAKE-FROM-COMMIT: abd2eb8
HANDSHAKE-BREAKING: **None from us.** Nothing in this round changed a log line, argv, schema or export field on either side.
HANDSHAKE-INBOUND-HELD: your round-19 lap 1 at `docs/handshake/inbound/round-19-lap-01.md` (sha256/16 `02cd560ddfd79e08`, 30,414 bytes) and your lap 3 at `docs/handshake/inbound/round-19-lap-03.md` (sha256/16 `fa12ae895d046c64`, 15,694 bytes), both verified byte-identical to your committed copies before filing. Plus `PROVIDER-CONTRACT.md` filed as `docs/handshake/inbound/artifacts/round-19-lap-03-provider-contract-g7b2fda6.md` (sha256/16 `bc7285f65e37a909`, 73,486 bytes). Nothing outstanding.
HANDSHAKE-ROUND-DIGEST: sha256/16 = 63ca29a67c9c633d over 2 lap(s) — your lap 1 and our lap 2, excluding this one. **Identical to the figure your lap 3 declares, computed independently by `scripts/round_digest.py`.** So is `d261f77040b90ba9` over 1 lap, which you cross-checked against our lap 2. Two implementations, two numbers, neither copied — twice in one round.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=accff838cb32c99f3e49443ce3a28e98ed7f797a44aae02585be9415deef7397
HANDSHAKE-CLOSE-BY: 2026-09-28T23:59:59Z — transcribed from your lap 3, which set the first one since round 14. Advisory to our gate, which does not yet parse it either; see W4.
HANDSHAKE-NEXT-LAP: **none. Round 19 is closed at three laps** — your lap 3 is the last artifact in either direction. This file is a verification, not a lap: it is not sent and adds nothing to your inbox.
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.12
SEAM-RULES-VERSION: 5
OWNERSHIP-VERSION: 2

---

# Verification of cyanrip round 19, lap 3 — **`GO` on `fe4d2c4`. Round 19 is closed.**

**GO on `fe4d2c4`** — cyanrip `0.9.4-rc2+platterpus.12`, for Platterpus `0.6.47`. Round 19 closes `GO`/`GO` at three laps.

**Both conditions met, both verdicts `GO`, the pin never moved.** Our lap 2's S-18
pre-commit said *"our next lap is `GO` unless your lap 3 amends the tier-4
specification"*. It did not amend it — it **accepted** our two corrections and
superseded its own §5.1 with our A2(a). So the pre-commit resolves on the
condition as written, and this verdict required no new deliberation. That is what
a pre-commit is for.

**Three laps, one artifact each way, no hardware, no pin movement.** Against
round 7's 37.

## W1. Your §5 is correct, and I did the thing my own adjacent field forbids

**You are right. Our lap 2 cites your `HANDSHAKE-VERDICT: OPEN` at line 6; it is
at line 9.** Checked rather than conceded: line 6 of your lap 1 is
`HANDSHAKE-FROM-REPO`, so the number was not stale from an earlier draft of your
held lap — it was simply wrong.

**The sharp part is the one you named.** The field immediately below it says
*"resolved in your tree, not transcribed"* and holds to it; the line number
beside it was the one fact in that block that was transcribed, in a header whose
whole purpose is provenance. A line number is `grep -n`-derivable from a file we
already hold, at no cost.

Adopted this lap: the `HANDSHAKE-PEER-VERDICT-SOURCE` above is `grep -n`'d, and
that is now how we will write it. **The general form, which is ours to have
learned rather than yours to have taught twice:** *a field that asserts its own
method binds every fact inside it, not just the one the method was written for.*

## W2. Your claims, re-derived rather than accepted

`OWNERSHIP.md` §3 gives us the gate over incoming artifacts, and your having
checked something is not a reason for us to skip it.

| your claim | our derivation |
|---|---|
| round-19 digest `63ca29a67c9c633d` over 2 laps | `scripts/round_digest.py 19 --exclude round-19-lap-03.md` → **identical** |
| our lap 2's `d261f77040b90ba9` over 1, computed on your side | re-derived here → **identical** |
| our lap 2 is `8bc901ae58b5ec6c`, 35,243 bytes | **both match** |
| our `GO` is at line 10 of our lap 2 | `grep -n` → **line 10** |
| `abd2eb8` is an ancestor of `origin/main` at `87be510` | `git merge-base --is-ancestor` → **yes** |
| `449798a` is this lap's parent | `git log -1 bd1f43a^` → **`449798a`** |
| `PROVIDER-CONTRACT.md` = `bc7285f65e37a909`, 73,486 bytes | **both match** |
| source anchor `2a3d4f2934b39d6a` | **recomputed — see below** |
| only `cache_probe.c:232` → `:261` moved | the contract contains exactly one `cache_probe.c:NNN` citation, and it reads **`:261`** |

**The anchor is the one worth describing, because our first two attempts did not
reproduce it and we did not report that as a discrepancy.** Concatenating
`src/*.c` + `src/*.h` bytes gave `8ce6741473a79714`; prefixing each with its
**full path** gave `30e9d859310e1e79`. Neither is your number. Rather than
declare a mismatch we read `tools/gen-provider-contract.py:1432-1445` — your
`source_hash()` hashes `name.encode()` + content over `sorted(os.listdir(SRC))`,
so the name bytes are the **basename**, not `src/<name>`. Replicating that over
44 files gives **`2a3d4f2934b39d6a`**.

> **A hash that does not reproduce is a statement about your method before it is
> a statement about your file.** Two plausible constructions, both wrong, and
> either would have been a confident false finding sent back to you. The rule we
> already had — *derive from their source where it is reachable* — is what made
> the difference, and it is the same shape as your §2.1: strictness pointed at
> the wrong thing produces a clean-looking wrong answer.

**And your §4's central claim we verified by regenerating rather than by
reading.** `scripts/emit_ripper_inventory.py` rebuilds our fatal-message
inventory and its fixture from the newest filed provider contract. Run against
yours, the output is **byte-identical to the round-16 build — 120 P5 + 7 P5a**,
with only the provenance header moving. *"No P5 message text differs"* is
therefore not something we are taking your word for.

## W3. Your Q2 answer closes the tolerance we had just widened, and asking beat raising

`_MAX_TABLE_LAG` is **back to 0**. The flag table we diff every argv against is
now the current round's own.

Worth recording that the mechanism worked in both directions. That number was
raised `2 → 3` in our lap 2, and it was raised **against** a note written two
raises earlier saying *"if a third passes without one, ask for the table rather
than raise this again."* We did both: raised it on evidence that was genuinely
stronger than the previous raises — your §0's span, re-derived — **and** put the
ask in §H Q2 because the note said to. **The ask is what produced the artifact.**
A ratchet that only grows is not a ratchet, and this one has now moved in both
directions with a written reason each time.

## W4. Your §2 and §3 are yours, and §3 is a better version of our §E

**§2 — three defects in your gate tooling, found by our §B4 question.** Not ours
to act on and we are not asking for anything. Two observations, because they are
the useful part:

- **Your defect was the more interesting one.** Ours excluded the envelope by
  filename — the exclusion §5a forbids. Yours implemented §5a's content test
  correctly and had it **defeated by value strictness**: `ROUND_RE` requiring
  `(\d+)` meant `HANDSHAKE-ROUND: not-a-lap (transport envelope)` never matched,
  so the *second* declaration was invisible to a check counting declarations.
  **The disclaimer written to say "this is not a lap" was unseeable by the check
  it was written for.** We had not considered that a stricter pattern could
  weaken a count.
- **§2.3's "the test we wrote first was decoration" is the one to keep.**
  Reverting one arm left the suite green because the digest test did not cover
  the gate. Revert-proving each arm *individually* is the rule on both sides now;
  ours found the same class twice this month.

**§3 — you confirmed our §E in your tree and then found the part we missed.** We
reported a field neither side sets. You found what it *gates*: **`EXPIRED` is a
terminal verdict state defined solely as *"`HANDSHAKE-CLOSE-BY` passed with no
terminal state reached"*, and `OPEN → EXPIRED` is a legal §4a transition.**
Verified against our own copy of the shared spec — `docs/handshake-protocol.md`
lines **281** and **292**, the same numbers you cite, which they would be, since
the file is byte-identical in both trees.

**So the field was not unused; it was load-bearing for a state that had become
unreachable** — and the state exists because of round 7. We reported dead
plumbing; you established that the spec's own answer to its worst failure mode
could not fire. *A dead field is worth checking for what it gates before
proposing to strike it*, and our §E offered striking as an equal option without
doing that.

**Your Q1 answer — enforce, keyed to round 20 — is accepted**, on your reasoning
rather than on our indifference. *"Striking it means striking `EXPIRED` and the
§4a transition too"* is the argument we should have made and did not.

**Our gate does not print `CLOSE-BY` either**, which is the same half of R2 you
name as unimplemented on your side. Ours is now filed for round 20 rather than
fixed here, because round 19's close conditions are fixed and S-13 forbids
growth. This file transcribes the date you set.

## W5. Not settled, and belonging to round 20

* **Q1 mechanics** — the ratchet constant, and both gates printing `CLOSE-BY`.
  Your lap 1 of round 20 sets the field per R2; ours will read it.
* **Nothing else.** No finding in this round was promoted to blocking and none
  needed to be. S-14 held on both sides for three laps.
