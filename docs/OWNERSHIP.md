# OWNERSHIP — who owns what, where, when

**OWNERSHIP-VERSION: 1**

**Neither project owns this file.** It lives at the same path in `cyanrip` and in
`Platterpus`, like `docs/handshake/PROTOCOL.md`, `docs/seam-rules.md` and
`docs/seam-commands.md`. A change is a version bump both sides ship, never a
local edit.

**It is enforced, not remembered.** Its SHA-256 is declared in every lap's
`HANDSHAKE-SHARED-HASHES`, and each side's checker recomputes that hash from its
own copy. **A lap whose declared hash does not match the receiver's file FAILS,
and a round cannot close over a failing lap.** That is what "both sides agree
100% every time" means mechanically: not a promise, a comparison.

> **If the two copies differ, the lap does not pass. Reconcile the file first.**

---

## 1. The test, before the lists

Two questions decide every case, and they are the same two that have decided
every ownership argument this seam has had:

> **RECOVERABILITY — is the disc still needed?**
> If getting this fact wrong means putting the disc back in the drive, it is
> **cyanrip's**, and it must be measured and reported at rip time.
> If it can be fixed by re-reading files already on disk, it is **Platterpus's**.
>
> **EXECUTABILITY — who can run the thing being judged?**
> A gate belongs to the side that can execute what it gates. Neither side may
> gate the other's internals, because neither can run them.

The lists below are consequences of those two. **When a new case is not on a
list, decide it with the test and add the row** — do not argue it in a lap.

## 2. cyanrip owns — everything that requires the disc in the drive

| what | when |
|---|---|
| Drive I/O, TOC, pregaps, sub-channel, ISRC/MCN/CD-TEXT, pre-emphasis | rip time |
| Drive identity, read offset, cache model and `-x` cache probe | rip time |
| C2 and paranoia counters, timing, read-stall detection | rip time |
| The audio bytes and **every checksum over them** | rip time |
| The log and the cue **as a stable record of all of it** | rip time |
| Its own binary, provider contract, golden reference, and release gate | always |
| **Its own outgoing laps**, checked before they are sent | always |

**And the rule that gives those their value:** cyanrip **reports measurements
with provenance and never emits a verdict about a rip's quality.** `none` and
`unknown (reason)` are different claims. "Modelled" is not "defeated". "None
reported by libcdio" is not "the disc has none".

## 3. Platterpus owns — everything derivable after the disc is out

| what | when |
|---|---|
| Parsing our log, cue and `-j` record | after the rip |
| Network lookups: MusicBrainz selection, cover art, CTDB | after the rip |
| Cross-disc state, library layout, presentation, EAC-format rendering | after the rip |
| **Policy** — what counts as acceptable, when to retry or quarantine | after the rip |
| The rig, the acceptance script, and the evidence bundle | at test time |
| **The gate over incoming artifacts, and the systematic feedback duty** | every lap |

**§3's last row is new, decided 2026-08-26, and it is the reason this file
exists.** The systematic-gate duty is Platterpus's because **they can execute
both sides and cyanrip can execute one**: they run our binary, parse our log and
hold the drive; we cannot run their program, read their source, or reproduce
their environment. A gate over a system you cannot execute produces confident
wrong findings — round 12's `BLOCKING` claim about a constant in their source we
had never seen is the measured proof.

## 4. Neither owns — both must agree, or it does not ship

| what | how agreement is shown |
|---|---|
| **The log's text**: wording, indentation, field order, units of any parsed line | a handshake round, before it ships |
| `PROTOCOL.md`, `seam-rules.md`, `seam-commands.md`, **this file** | a version bump both sides ship |
| The pin under review | declared as a SHA in both sides' laps |
| Whether a round closes | both verdicts `GO`, transcribed from the file the other sent |

## 5. Neither may — and these are absolute

- **Neither states a mechanism in the other's code without citing the artifact it
  was read from**, or marking it unverified. We can measure our own behaviour and
  read each other's laps; we cannot read each other's source.
- **Neither gates the other's internals.** Each gates the other's *emissions* —
  files actually sent — and its own everything.
- **Neither closes a round on the other's silence.** "They did not object" is not
  "they agreed".
- **Neither reads an absence as evidence** unless the channel is known to retain
  presence — and the side producing a capture is responsible for saying what its
  capture drops.

## 6. When the two disagree

**First, separate the two kinds of disagreement, because they need opposite
responses and treating them alike is how a seam stalls.**

| kind | what it means | what to do |
|---|---|---|
| **A RECORDS DIFFERENCE** | both sides computed correctly from what each holds, and the holdings differ | **RECONCILE.** Exchange the enumerated population, compute the set difference, and each side sends what the other lacks. **Nobody is wrong and nobody re-does work.** |
| **A RULES DIFFERENCE** | the two sides are grading against different specs | **STOP.** Reconcile the shared file first; nothing else in the lap has been graded. |
| **A CLAIM DIFFERENCE** | both hold the same inputs and disagree about what they show | **§1's test decides**, and if it cannot, §6.3. |

| **A NEARLY-RIGHT PROPOSAL** | one side's answer would work with a tweak | **COUNTER-PROPOSE.** Name the smallest change that makes it work. **Refusing something you can name a working variant of is orthodoxy, not rigour.** |

**RULES, FAILURE AND TESTING ARE NOT NEGOTIABLE — RIGIDITY IS.** A gate must
fail what is *wrong*. It must not fail what is merely *different from how we
would have done it*, and the two are distinguishable by one question:

> **Can I name a small change that would make this work?**
> If yes, the response is that change, at `WARN`. If no, it is `FAIL`.

Applied to a checker: **`FAIL` is reserved for a claim that is false, a field
that is absent, or a record that cannot be reconciled.** Everything a
counter-proposal could fix is `WARN` with the counter-proposal attached. A `FAIL`
neither side can act on is a stalled round wearing a verdict's clothes.

**A gate that reports a records difference as a bare failure is a defective
gate.** It must print what each side holds, the exact set difference, and who
sends what — otherwise it turns "we have not exchanged everything yet" into an
argument. **Every side's checker owes a recommendation, not a rejection.**

> **BASELINE: every lap enumerates the record it computed its digest over.**
> A hash says *that* two records differ; the enumeration says *how*. Without it,
> a digest mismatch costs a lap to diagnose — which it did, twice, in round 14.

**Then, for the kinds that really are failures**, in this order and without
exception:

1. **A shared-file hash mismatch is settled before anything else.** The two
   copies are reconciled, both sides ship the reconciled version, and the lap is
   re-sent. Nothing else in the lap is judged until then, because a file graded
   against the wrong rules has not been graded.
2. **An ownership dispute is settled by §1's test, not by seniority.** Whoever
   can execute the thing, gates it. Whoever needs the disc back, owns it.
3. **A dispute §1 cannot settle is the operator's**, and it goes to them as one
   question with both positions stated — not as a lap of argument.

## 7. What this file does not do

It does not decide **schedule**, **priority**, or **who writes a given fix**.
Those are per-round and belong in the round. This file decides only **whose
answer is authoritative** when the two sides differ about a fact, a gate, or a
surface.

**And it is not a licence to defer.** An owner who cannot get to something says
so; ownership is about authority over the answer, never about a right to sit on
the question.
