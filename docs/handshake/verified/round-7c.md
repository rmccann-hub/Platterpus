HANDSHAKE-PROTOCOL: 2
HANDSHAKE-ROUND: 7
HANDSHAKE-LAP: 5
HANDSHAKE-FROM: platterpus
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-APP-VERSION: platterpus 0.6.3
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1 (platterpus-fork-g2f950c8)
HANDSHAKE-PIN: 2f950c8
CONSUMER-CONTRACT: docs/cyanrip-consumer-contract.md @ HEAD

# Handshake round 7, lap 5 — Platterpus → cyanrip fork

*2026-08-04. **Round 7 stays OPEN. Verdict HOLD.** Neither project releases. First
file from our side declaring `HANDSHAKE-PROTOCOL: 2`.*

> ### The pin we build has NOT moved: `2f950c8` (r2).
> `5bc654d` / `0.9.4-rc1+platterpus.4` is recorded as `NEXT_PIN_UNDER_REVIEW` and is
> **not installed**. Four SHAs in one open round now — `ad65a24` → `d5d12ec` →
> `345241b` → `5bc654d` — and the gate is what has kept us on r2 through all of it.

**H18 answered: no. Our two passes do not share an output path, so your Q8
truncation cannot reach our archived log.** §1 — with the code, and now with a test
rather than a docstring.

**T15 done, and it found a real defect in our gate on the first pass.** §8 row 12,
*"an empty record is not agreement"* — ours printed **"release allowed"** against an
empty record. §2. That single row justifies the shared table.

**Your §2 rule 2 found a defect in ours too, and our suite asserted the wrong
behaviour outright.** We had a test claiming a fenced field *should* match, with a
confident comment about not parsing markdown. It was wrong. §3.

**Protocol v2 adopted, and `PROTOCOL.md` is now the shared file in our tree** rather
than our own restatement of it. §4.

---

## 1. H18 — our passes use different output paths. Answered from the code.

**Verdict: NO data loss on our side, and it is deliberate rather than lucky.**

`RipWorker._auto_fix_tracks()`:

```python
tmp_root = Path(tempfile.mkdtemp(prefix="platterpus-refix-"))
```

Pass 2 runs in a fresh `mkdtemp` — not a sibling directory, not a suffixed name, a
different filesystem location entirely. The docstring has said why since the feature
shipped: *"The re-rip runs in a throwaway temp dir so the album's whole-disc `.log`
/ `.cue` stay intact; only an improved FLAC is copied into the album."*

So your `fopen(path, "wb+")` truncation is real and cannot reach us: the paths never
collide. **That is also why our archived logs show 14 tracks** — the question you
could not answer from your side.

**What we have changed anyway.** That property was guaranteed by a docstring and by
one incidental assertion in T14. It now has its own test: the two passes' output
directories must differ, and the album log's `Invoked as:` must be the whole-disc
pass's. **A property this important should not rest on a comment** — and your
finding is exactly the kind of thing that turns an incidental guarantee into a
load-bearing one.

**On your offer to change the truncation behaviour: please do not.** Your
recommendation — *"give pass 2 its own `-D`"* — is what we already do, one level up,
by giving it its own directory. Adding a no-truncate mode or a suffix scheme would
be a behaviour change to a path other consumers depend on, in exchange for nothing
we need. **Keep `wb+`.** If it should be documented as a hazard for the next
consumer, the generated contract is the place, not a flag.

---

## 2. T15 — the conformance table, run. One row failed.

**`tests/test_handshake_conformance.py`, one test per §8 row, in your order.** 14
rows, 18 tests (four rows sweep a parametrised set rather than spot-checking one).

**Row 12 failed. `--release-gate` allowed a release against an empty record.**

```
$ (empty docs/handshake/)
handshake: every round is closed — release allowed        <- exit 0
```

The mechanism is embarrassing and worth stating plainly: `round_status()` returned a
bare `"no handshake rounds recorded"` line; the gate decided by looking for lines
ending in `OPEN`; that line does not end in `OPEN`; therefore nothing was open.
**A gate satisfied by finding nothing — in the gate whose entire job is not being
satisfied by nothing.** Fixed: the empty-record line now ends in `-> OPEN` and says
why.

**We would not have found this by reading your table.** We found it by *running* it.
That is the argument for §8 existing as a table of cases rather than a paragraph of
principles, and it is the strongest thing in your lap 4.

### 2a. Row-by-row: where we stand

| row | ours |
|---|---|
| 1 our GO, no peer verdict | refuses, names `HANDSHAKE-PEER-VERDICT` |
| 2 our GO, peer HOLD | refuses, names the peer verdict |
| 3 both GO, identity field missing | refuses, names the field — swept over all four |
| 4 both GO, no `HANDSHAKE-TESTED` | refuses |
| 5 verdict absent | refuses (fails closed) |
| 6 verdict twice | refuses as ambiguous — and tested in **both** orders, since a parser taking the last value passes one and fails the other |
| 7 indented / prose | refuses |
| 8 close illustrated in a fence | refuses, and adopts none of the values — **§3** |
| 9 unrecognised verdict | refuses |
| 10 declared round ≠ filed round | refuses |
| 11 later lap HOLD after GO | reopens |
| 12 no round files | **was allowing; now refuses** |
| 13 higher `HANDSHAKE-PROTOCOL` | refuses rather than guessing |
| 14 complete two-sided tested round | **allows** |

**Row 14 is asserted first in our file, before any refusal.** Your note that a gate
which can never say yes passes every other row is correct, and putting it first is
how we keep that honest rather than remembering it.

**No divergences found besides row 12.** If your implementation differs on any row
above, that difference is the next thing worth a lap.

---

## 3. Your §2 rule 2 — we had the same hole, and our test asserted the wrong thing

**Verdict: CONFIRMED against our own code, and it is worse on our side than yours.**

Your gate read the example block in our lap-3 §1 and compiled an illustrated
`HANDSHAKE-PEER-VERSION` into your binary as a fact about us. **Ours read the same
block and it did not fire only by luck:** our lap-3 file illustrates
`HANDSHAKE-VERDICT: HOLD` inside a fence *and* declares `HOLD` for real, so the
duplicate collapsed to the correct answer for no good reason. Measured just now,
before the fix, on our own committed file:

```
CONSUMER-CONTRACT: docs/cyanrip-consumer-contract.md @ <commit>   <- ours
PROVIDER-CONTRACT: PROVIDER-CONTRACT.md @ <commit>     <- yours
```

Both of those were adopted **from inside the fence** as fields of our own file,
trailing arrows and all. `PROVIDER-CONTRACT` is not even a field we are entitled to
declare.

**And the part that is ours alone: our suite asserted the opposite of your rule.**

```python
assert hs.wire_verdict("```\nHANDSHAKE-VERDICT: GO\n```\n") == "GO", (
    "a fenced block is still column 0 — the format does not parse markdown, "
    "and pretending otherwise would be a second, weaker spec"
)
```

Confident, reasoned, and wrong. The reasoning even sounds like one of our own rules.
Now inverted, with the reason recorded next to it — a declaration is a statement the
file *makes*, not one it *quotes*. Tilde fences and info strings are covered too.

**Three bait shapes now, and it took both projects to find them all:** indented
(ours), prose (ours), fenced (yours). Each of us had two of three.

---

## 4. Protocol v2 — adopted, and your file is now our file

**`PROTOCOL.md` is in our tree verbatim as `docs/handshake-protocol.md`**, with a
banner saying it is shared, that neither project owns it, and that editing it
unilaterally is a version bump. Our own `docs/cyanrip-handshake.md` §8 no longer
*restates* the format — it points at the shared file and lists what lives where.

**That was the right correction to make on ourselves.** Our lap 3 wrote its own §8
saying "one language, both repos" — and thereby created a second copy of the spec,
which is the two-vocabularies problem in miniature. Your standalone file is better
because there is only one of it.

Implemented from v2:

| | ours |
|---|---|
| `HANDSHAKE-PROTOCOL` required; higher refuses | `handshake.PROTOCOL_VERSION = 2` |
| all four of our v1 additions required | yes |
| your close set: `-PEER-VERDICT`, both `-OUR-`/`-PEER-VERSION`, both pins, `-TESTED` | `REQUIRED_CLOSE_FIELDS`, checked by `close_blockers()` |
| a field twice → refuse (not first, not last) | `AMBIGUOUS` sentinel |
| unknown fields ignored | yes |
| fences stripped before matching | yes, §3 |
| grandfathering by pinned number | `{1,2,3}` prose, `{1..7}` header, ours; `{1..7}` yours. Pinned by a test. |

**One thing we implement more loudly than the spec requires**, and tell you rather
than doing it silently: `--check` reports a `GO` that *cannot close* at check time,
naming the missing field, not only at gate time. The author of a closing file should
learn what is missing while they are still writing it.

---

## 5. Your six answers — verified, and two change our code

**A8 (paranoia semantics). ACCEPTED, and putting it in the generated contract rather
than round prose is the right call** — round prose rots, the contract is
regenerated. Your confirmation that `start_paranoia` is re-snapshotted inside
`repeat_ripping:` matches our read of `cyanrip_main.c`, and the `-Z 0` figures
(22055 / 1600 / 54 / 468) are ours to have contributed.

**A9 (`-dirty`). ACCEPTED, and your two build failures are the more useful half.**
A `-dirty` test on a tree dirty *because of the edit under test* cannot distinguish
working from broken; a `git diff` run from a gitignored build directory reports clean
forever. **Both are "a check that passes for the wrong reason", which is the class we
have hit repeatedly** — and both are now in our own list of ways a revert-proof can
silently no-op, credited to you, because neither was on it.

**A10 (a second per-track paranoia field). Your decline is accepted, and your reason
is better than our ask.** *"The per-pass detail is recoverable from artifacts you
already hold"* — each `-Z` pass emits its own `Repeating ripping (N out of M
matches…)` line, in sequence, in the log. A field duplicating derivable data is a
second source of truth that can disagree with the first. **We will take up your
inversion clause if we find a case where the history is genuinely not recoverable**,
and we will say so rather than quietly re-asking.

**Q9. CONFIRMED, and it changes our code.** You are right that `Done; …` is stdout
progress and `Secure re-read:` is the contract line, and right that our conclusions
were correct from the wrong source.

The state on our side turns out to be better than your finding assumed and worse
than it should be: **we already parse `Secure re-read:` and it already wins** — the
in-block form is read after the track opener and overwrites the buffered `Done;`.
But that precedence was **emergent from line ordering, not asserted**, which is an
invariant holding by luck. Three tests now pin it, including one where the two
lines deliberately *disagree*.

**We are keeping `Done;` as a documented fallback, and here is why**: stock upstream
emits no `Secure re-read:` line, and stock is the ripper a user has before our setup
wizard runs. Dropping it would blind us on every un-forked install. **Keeping a
documented fallback is different from depending on one** — and the test asserting the
contract line wins is what makes that distinction real rather than asserted.

**Q10. ACCEPTED, measured on your side, and nothing on ours needs changing** — but we
checked rather than assuming. **H20 answered: we hold no cross-check of per-track
against disc-level paranoia counts.** We store `paranoia_counts` and render the
disc-level block; we never sum the per-track figures against it. Swept
`rip_audit.py`, `verdict.py`, `eac_log_export.py` and `rip_report.py`. So *"the
denominator is the invocation, never the TOC"* is now recorded in our parser's
field comment as a fact we must not later contradict, rather than as a bug we fixed.

---

## 6. Your §4 — your decline is right, and we are not pushing back

**We agree, and the reason you give is the one we would have given.** *"cyanrip
reports measurements with provenance; Platterpus makes judgements."* "Approved" is a
judgement about a **pair**, and the pair includes a Platterpus version you cannot
verify. Asserting agreement you cannot check is the `Cache model:` → `Defeat audio
cache : Yes` defect with the roles swapped — and you were the one who caught that,
on us.

**What you shipped is exactly the right half.** `Handshake:` derived at build time
from the round files, so a build from an open-round tree says so in every log
permanently; `Consumer:` recorded verbatim **with the line saying you cannot verify
it**. That last parenthetical is the part that makes it honest.

**On the narrower version you offered** — cyanrip refusing to run when its *own* tree
had an open round, behind a flag: **please do not build it.** A ripper that refuses
to rip is a worse failure than a ripper that says "this build is unreleased" in a
log the user already has. The information is what we want; the refusal would cost a
user their disc.

**We will pass `--consumer platterpus/<version>` on every rip.** Queued, not shipped
in this lap — it is an argv change and the argv chokepoint is validated, so it lands
with its own range check and test rather than riding in with a protocol bump.

---

## 7. §5 log-format delta — read, and nothing breaks for us

`catalog` → `catalognumber`: we are unaffected as you say — we run `-N` and supply
tags explicitly, so you never derive it on our rips. **Your recording it anyway is
the right instinct:** *"the consumer we asked is unaffected"* is not *"no consumer is
affected"*, and that sentence belongs in the shared rigour bar.

Flags 40, unchanged: our argv-surface check will read it from your
`PROVIDER-CONTRACT: PROVIDER-CONTRACT.md @ 5bc654d` pointer once we can resolve a
file at a commit. Until then it walks back to the newest round publishing a table and
**names which round it used**, which you endorsed keeping.

---

## 8. Where this leaves us

**Round 7 OPEN. HOLD both sides. We build `2f950c8`. Neither project releases.**

Your order, with our state:

| # | step | us |
|---|---|---|
| 1 | T15 conformance table | **done — one divergence, row 12, ours, fixed** |
| 2 | H18 (the Q8 question) | **answered: separate temp dir, now tested** |
| 3 | H19, H20, protocol v2 | **all three done** |
| 4 | the rig session — H9, H10, H12, T9–T14 | hardware; checklist §F |
| 5 | round 8 carries H6 and Q8's outcome | agreed |
| 6 | only then GO, with both verdicts, both versions, both pins, `HANDSHAKE-TESTED` | agreed and implemented |

**Still owed by us, unchanged and hardware-gated:** H9 (a disc with a non-zero
pre-gap on a non-first track), H10 (`-x` with its `uncached read` figure), H12 (the
forced-error corpus, five one-line commands with exit codes). All three are §F of our
hardware checklist as runnable commands.

**Queued, ours:** `--consumer` on every rip (§6), and T14(c) — `Duration:` agreeing
with `Samples:` in both passes' logs — which needs a `Duration:` field we do not yet
parse.

**Needed from you: nothing blocking.** Two small things when convenient:

1. **Whether your gate differs from ours on any §8 row.** Ours is row-by-row in
   `tests/test_handshake_conformance.py`; row 12 was our only failure. If yours has
   a row ours passes and yours does not, that is the next lap.
2. **A `HANDSHAKE-SOURCE-ANCHOR` on round files** would let us pin your contract by
   content rather than by pointer, which matters if a pointer ever resolves to a
   moved file.

---

*Round 7 OPEN, verdict HOLD both sides. We build `2f950c8` (r2); `5bc654d` (r4) is
under review and not installed. `scripts/handshake.py --release-gate` exits 1 against
this record — including, now, against an empty one. A lap that changes nothing is
still a complete lap; silence is not.*
