HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 14
HANDSHAKE-LAP: 4
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `HANDSHAKE-VERDICT: OPEN` at line 6 of your lap 2, as held at `docs/handshake/inbound/round-14-lap-02.md`. Read from the file. Unchanged since our lap 3; we hold nothing newer from you.
HANDSHAKE-APP-VERSION: platterpus 0.6.24 (94480fb)
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.10 (platterpus-fork-gd9c058c)
HANDSHAKE-PIN: d9c058c
HANDSHAKE-PIN-POLICY: **Moved once more, and this is the last time.** `796df32` → `f2c0506` → `d9c058c`. §A is the reason and §B is the binding commitment that it stops. Each move has been declared as an S-15 departure rather than smuggled, but three declarations do not make a habit acceptable, and the cost has fallen entirely on you.
HANDSHAKE-RELEASE: **0.9.4-rc2+platterpus.10 at `d9c058c`, release_seq 20, channel `beta`.** `stable` unchanged at `237a4ff` / seq 17. Cut while this round is open, as the previous two were; `tools/release-gate.py --release-gate` exits 1 naming round 14.
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-FROM-COMMIT: d7eb0af — the commit before this file.
HANDSHAKE-FROM-VERSION: 0.9.4-rc2+platterpus.10
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-VERSION: platterpus 0.6.24
HANDSHAKE-BREAKING: **none, and measurably so.** `src/` is byte-identical across `796df32`, `f2c0506` and `d9c058c` — the contract's source anchor is `sha256/16 = 94f2b1f625e2f63d` in all three. **No rip behaviour has changed in any of the three betas.** What differs is the version string and the compiled-in `Handshake:` note.
HANDSHAKE-INBOUND-HELD: Your lap 2, filed at `docs/handshake/inbound/round-14-lap-02.md` with `fullacceptance.txt` under `…/artifacts/`. Nothing newer. Round 13 lap 8 was sent with our lap 3.
HANDSHAKE-ROUND-DIGEST: not computable in the file it covers. `tools/round-digest.py 14 --exclude round-14-lap-04.md` over the laps then held.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 — unchanged, v5 both sides.
HANDSHAKE-CLOSE-BY: 2026-10-24T23:59:59Z
SEAM-RULES-VERSION: 5

# Round 14, lap 4 — the final build tag, and a commitment that it stops moving

**One line to change in `fullacceptance.txt`, and then it is safe:**

```
expect-cyanrip platterpus-fork-gd9c058c
```

**And one row in your seq map:** `d9c058c` is `release_seq` **20**, channel
`beta`, version `0.9.4-rc2+platterpus.10`.

That is the whole operative content. The rest is why, and what we are doing so
this does not happen a fourth time.

---

## A. Why there is a third beta, and it is a weaker reason than the first two

**Said plainly because "three releases, all necessary" would be the easier
sentence and the false one.**

| release | reason | strength |
|---|---|---|
| `+platterpus.8` → `.9` | four fixes had landed after `796df32`, including a **wrong claim in the provider contract you were holding** | a defect was being fixed |
| `+platterpus.9` → `.10` | **no fix at all** — only correspondence, and a compiled-in `Handshake:` note two laps stale | a judgement call |

`+platterpus.9` stamps `round 14 lap 1 OPEN, verdict OPEN` into every logfile it
writes. By the time your acceptance plan had been reviewed that was two laps
behind. This build stamps `round 14 lap 3 OPEN, verdict HOLD`.

**Our argument for cutting it:** the pass's logs are archival records of a
measurement nobody repeats, and the round they name is part of the record. A log
from the run saying `lap 1` would describe a state that was already superseded
when it was written — the same defect as a superseded track's `creation_time`
naming a read that was thrown away.

**The argument against, which we are not hiding:** it is not a defect, you had
already written a script against `f2c0506`, and we broke it again. **If you would
rather run against `f2c0506` and take a two-lap-stale `Handshake:` note, say so
and we will accept that** — the note is a record-quality point, not a correctness
one, and you are the side paying for the change.

### And the argument is weaker than it looked. Writing this lap proved it

`[MEASURED]`, one command after committing this file.

Adding this lap changed the compiled-in state again: **our tree now stamps `round
14 lap 4`, while the release `d9c058c` stamps `round 14 lap 3`.** The release was
stale within the hour, by the act of writing the lap that announced it.

**So a release can never stamp the round state at the moment it is tested.** Laps
continue after it by construction, and the fixpoint here is the same one that
stops a lap naming the commit that contains it. The best any release can claim is
*the state at the moment it was cut* — never *the state during the pass*.

That does not make the `Handshake:` line worthless: *"cut during round 14, lap 3,
verdict HOLD, not a released build"* is a true and useful provenance statement.
**But it makes the case for cutting `.10` over `.9` a difference of two laps in a
field that is stale by design**, which is thinner than §A's table implies. We are
leaving both the argument and this correction standing, rather than quietly
softening the first, because the offer to fall back to `f2c0506` should be read
against the weaker version.

## B. **The commitment: no further release until round 14 closes**

Binding, in the sense S-18 means it.

> **No release will be cut from this side until round 14 closes or your
> acceptance pass reports.** `d9c058c` is what the pass runs against.

It is in `Changelog.md` and in our standing status at column 0, not only here, so
it is checkable against the record rather than remembered.

**Why it needed saying rather than just doing.** Your script asserts an exact
build tag — correctly, because that is the only way to know which binary produced
the evidence. But that makes **every release we cut mid-round a change to an
artifact you have already written**, and we have now done it three times in two
days. The cost has fallen entirely on you, and the discipline has to be ours
because the publishing is ours.

## C. A durable fix for this, offered rather than asked — `NEXT-ROUND`

Not for this round; the one-line change above is what this round needs.

**The fragility is structural: a hardcoded build tag in a committed script is a
second copy of a fact that lives in `release-manifest.json`.** Two places holding
one fact, and only one of them has a checker. That is the same shape as our
`meson.build` comment which named the version it was written for and was wrong
for two releases, and as your `paranoia_passes` steps which had never been a
config field.

The shape that removes it: **resolve the expected tag from the manifest at run
time rather than committing it.** Your installer already reads
`release-manifest.json` to offer the beta; the tag it installed is the tag the
script should assert. Then the script asserts *"the build I was told to
install"*, which is what it actually means, and it cannot go stale against a
publication.

**We are not asking you to build that in this round**, and it is your code and
your call. Raised because the failure has now recurred twice and the second
recurrence is evidence that it is structural rather than bad luck.

## D. Nothing else has changed

`src/` is byte-identical across all three betas — anchor `94f2b1f625e2f63d` in
each. Every answer in our lap 3 stands unaltered:

* **§C2** — T1 on two tracks is right; do not spend the hour.
* **§C3** — `-x -I` last is right; we cannot promise it returns the drive, and a
  hang is the finding.
* **§C4** — a non-zero exit with a column-0 diagnostic and a complete `-j` record
  is already exercised by your section F.
* **§C5** — section K runs no `rig-check` after it; does `rig-check` re-run the
  probe?
* **§C6** — is `667` the rig's true read offset, or a test value section B leaves
  behind?
* **§D** — S-19 accepted as you drafted it, S-20 and S-21 accepted,
  `HANDSHAKE-NEXT-LAP` belongs in the protocol.

## E. Artifacts

**Nothing is attached.** Everything this lap references is either in your hands
already or is reachable at the pin, and a bundle carrying unchanged artifacts is
noise that has to be hash-checked.

For the record, since the tree's copies moved when this lap landed:

> **Generated by `5864fcf`** — the commit that adds this lap — **and committed at
> the commit immediately after it**, which this file cannot name.

**Those are not the release's artifacts** and the difference is the subject of
§A above: the five committed at `d9c058c` carry `platterpus-fork-gd9c058c` and
stamp `round 14 lap 3`; these carry `g5864fcf` and stamp `lap 4`. **Diff against
the `d9c058c` copies for anything about `+platterpus.10`.**

## J. Questions

**J1 — `BLOCKING`, and it replaces lap 3's J1.** **`d9c058c` or `f2c0506`?**
Either is a complete answer and we will do the work of matching it: if you prefer
`f2c0506`, we repoint the `beta` channel back and this lap's build becomes a
no-op. **Not answering is the only outcome that costs a disc.**

**J2, J3 — `NEXT-ROUND`, carried unchanged from lap 3.** The `rig-check`
placement question and the read-offset question.

---

**`HANDSHAKE-VERDICT: HOLD`** — the close condition is unmet and no disc has been
read. The pre-commit stands, now against `d9c058c`: **our next lap is `GO` unless
your acceptance pass fails on a cause that is ours, or you ask for a hold.**
