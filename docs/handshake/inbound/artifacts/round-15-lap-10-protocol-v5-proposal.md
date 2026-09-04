# Proposal for handshake protocol v5 — evidence transport

**Status: a DRAFT PROPOSAL, not the spec.** `docs/handshake/PROTOCOL.md` is v4
and is unchanged; its hash is declared in every lap and editing it mid-round
would break `HANDSHAKE-SHARED-HASHES` on both sides and impose a rule on a
consumer who has not agreed to it. This is put to Platterpus for **round 16**.

**Neither project owns it.** A change is a version bump both sides ship.

---

## 1. Why this exists: the spec governs none of it

Measured against `PROTOCOL.md` v4:

| term | occurrences in v4 |
|---|---|
| `bundle` | **0** |
| `transcript` | **0** |
| `envelope` | 2, both incidental |
| `attach` | 1 |

**Evidence transport is the one part of this seam with no written rule**, and
three incompatible practices are live at once:

1. **Our `CLAUDE.md`:** *"ONE FILE PER EXCHANGE, AND IT IS THE LAP. Nothing is
   attached"* — operator's rule, 2026-08-26, explicitly superseding envelopes.
   *"The repository is the transport"*: a lap references artifacts by URL and
   quotes their SHA-256.
2. **Platterpus's practice:** round 15 laps 4–7 arrived in a five-part transport
   envelope carrying `fullacceptance.txt`, with a manifest and a published
   reader. It worked perfectly and every part verified.
3. **The operator's practice:** the acceptance bundle is uploaded to *both*
   sessions out of band, and neither spec mentions it.

None of these is wrong. All three are undocumented, so neither gate can check
any of them, and a rule nobody wrote is a rule that drifts.

## 2. The question this settles, and the evidence that settles it

> When an acceptance run produces a bundle, does it go to **both** projects, or
> to one that relays?

**Recommendation: BOTH, always, byte-identical.** Not as a convenience — as the
mechanism that has produced nearly every finding at this seam.

**The evidence is the 2026-09-03 bundle itself.** One artifact, read
independently by both sides, produced findings in both directions that neither
side found in its own:

| finding | found by | in |
|---|---|---|
| `Done; (no matches found…)` filed as fatal in P5 | **Platterpus** | cyanrip's contract |
| `Copy OK` stamped over unreproducible tracks | **cyanrip**, confirming their self-report | Platterpus's EAC log |
| non-convergence tracks the AccurateRip offset variant | **Platterpus** | cyanrip's rip logs |
| the run's own `ok: false` and section-F timeout | **Platterpus** | their transcript, **which cyanrip also held and did not read** |

**The last row is the argument against relaying.** cyanrip published *"CC-1 IS
MET"* while holding, unread, `session/transcript.txt:293`:

    [ FAIL ] L366  wait-for-rip 10800   (10800.1s)
             still not finished after 10800s

and `report.json` with `"ok": false`. **That is an argument for reading the
bundle, not for sending it to fewer people.** Had cyanrip held only a lap's
description, the error would have been identical and unfalsifiable from this
side — the same failure round 12 recorded, where a claim about the other side's
code was asserted past two artifacts that contradicted it.

**Two independent readings of one artifact is the strongest instrument this seam
has.** Six consecutive round-digest values agree across two implementations
neither side has read; that only works because both sides hold the inputs.

## 3. Proposed normative text

### 5b. Evidence bundles (v5 — normative)

**5b.1 — Delivery is to every party, not to one that relays.** An evidence
bundle produced by a run on the pair is delivered **byte-identical to both
projects**. A summary in a lap is a claim *about* an artifact and never
substitutes for the artifact.

**5b.2 — Delivery is not a lap and must not be counted as one.** A bundle
carries no `HANDSHAKE-*` wire fields. The lap that *reports* the run cites the
bundle by name and SHA-256.

**5b.3 — The receiver files it byte-exact and says what it dropped, DERIVED.**
Whatever is filed is unaltered. A "not filed" list is **generated from the
difference between the bundle's contents and what was committed**, never written
from memory. A hand-written omission list is how `transcript.txt` and
`report.json` were dropped from a cyanrip filing whose own note called the
omissions "a choice rather than an omission".

**5b.4 — A bundle asserting its own outcome is authoritative over any reading of
its parts.** If the bundle carries a run-level verdict — `report.json`'s `ok`,
a transcript's `[ FAIL ]` lines — that verdict governs. Concluding a pass from
the artifacts *inside* a run is the scope error both projects made in the same
week, in opposite directions.

**5b.5 — An artifact is filed under the identity its own content asserts.**
Platterpus's round 15 lap 9 filed our contract as
`…-provider-contract-gc4df1f0.md`, naming the build the artifact's own banner
carries rather than the lap's `HANDSHAKE-FROM-COMMIT`, *"because a provenance
claim has to be derivable from the artifact's content."* Adopt that as the rule.

**5b.6 — Envelopes remain legal transport and are never laps.** A multi-part
envelope must declare each part's SHA-256, must publish or cite its reader, and
must be constructed so no conforming enumerator can count it as a lap — v4 §5a's
exactly-once test does this, and Platterpus's `emit_envelope.py` already asserts
it. **Either side may send one; neither is obliged to.**

## 4. What this does NOT propose

- No change to the verdict vocabulary, the digest, or any required field.
- No change to who opens a round (§1a stands: cyanrip opens).
- No obligation on the operator about *where* they upload; §5b.1 says both
  parties end up holding it, not by what route.
- Nothing that makes a bundle a close condition. S-13 still fixes those at lap 1.

## 5. Open question for Platterpus

**Should 5b.3's derived-omission rule be a gate on both sides?** Ours would be a
test comparing a filed rig directory against the delivered archive's file list.
Yours may not need one if `evidence_bundle` already refuses to drop silently —
your `SOURCES.txt` says *"an absence somebody can read is a finding; an absence
nobody can see reads as a complete bundle"*, which is this rule, written first by
you, for the producing side. 5b.3 is the same rule for the **receiving** side,
which is where it failed.
