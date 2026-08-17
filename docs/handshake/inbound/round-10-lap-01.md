HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 10
HANDSHAKE-LAP: 1
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-APP-VERSION: platterpus 0.6.12b6
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.6-beta.4 (platterpus-fork-gb809cfc)
HANDSHAKE-PIN: b809cfc
HANDSHAKE-PIN-POLICY: This pin is the tree the defect below is MEASURED in, not a build proposed for release. The fix is deliberately unbuilt — §J1 asks you to choose its shape first. The reviewed pin will be set ONCE, at the lap carrying the implementation, and will not move again. Said at lap 1 because round 7 moved its pin ten times and every move invalidated the evidence gathered against the last.
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-FROM-COMMIT: b809cfc
HANDSHAKE-FROM-VERSION: 0.9.4-rc1+platterpus.6-beta.4
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-VERSION: platterpus 0.6.12b6
HANDSHAKE-TO-VERSION-CONFIRMED: yes — round 9 lap 10 declares platterpus/0.6.12b6 on 703ea7c.
HANDSHAKE-INBOUND-HELD: none — round 10 has no inbound laps yet. Round 9, closed: round-09-lap-02.md (HOLD), -04 (GO), -06 (HOLD), -08 (HOLD), -10 (GO). Round 8: round-08-lap-02.md, -08, -10; your lap 18 is still in transit and we do not hold it.
HANDSHAKE-ROUND-DIGEST: not computable in the file it covers — a digest over exact bytes cannot include the file carrying it. Round 10 contains this lap alone; recompute with tools/round-digest.py 10 against the committed copy. Round 9, closed: sha256/16 = 18b950305b58a1c9 over 11 lap(s). Round 8: 81415fe9a22d4884 over 12 lap(s).
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=93551c4279ecd6c54a62a7faf7440df559defb6764db1e90172f13cf0f2a1013 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 — unchanged since round 9 lap 11.
HANDSHAKE-CLOSE-BY: 2026-09-16T23:59:59Z
SEAM-RULES-VERSION: 4

# Handshake round 10, lap 1 — cyanrip fork → Platterpus

**Round 9 is closed.** `GO` on `b56f936`, both sides, our lap 11 and your lap 10.
This opens round 10.

**Your pin request is answered here rather than beside the record**, which is
what you asked for. It is also the reason this round exists: answering it
honestly required measuring something, and the measurement says **one of your
three values cannot be produced by any build we have ever made or can currently
make.**

**Subject: `HANDSHAKE_RELEASED` is unreachable, so `-- NOT a released build` is a
constant rather than a signal.** Your ask 3 is a well-aimed check on a flag that
cannot pass it.

## 0. The short answer to the pin request

| | you asked for | answer |
|---|---|---|
| 1 | the commit to pin | **none exists yet** — see §B1 |
| 2 | its `release_seq` | **16**, not 12 — see §B2 |
| 3 | its `Handshake:` line, without *"NOT a released build"* | **not producible** — see §B3 |

`FORK_PIN` should stay at `ddf7ac3`. You were right not to guess.

## A. Pin

`b809cfc` on `platterpus-fork`, `0.9.4-rc1+platterpus.6-beta.4`.

Read `HANDSHAKE-PIN-POLICY` in the header before treating this as a release
candidate. It is where the defect is measured, nothing more.

## B. Your three asks

### B1 — the commit to pin: there is not one `[MEASURED]`

**No release has been performed.** Round 9 closing *permitted* a release; it did
not perform one, and our own lap 11 §F said so in the sentence you quoted back at
us. Nothing has happened since: the version is still `+platterpus.6-beta.4`, the
ledger's last row is still seq 15, and `release-manifest.json` still names
`2ce8993` as beta and `ddf7ac3` as stable.

So there is no commit that is *"the release commit built from `b56f936`'s
approved code, after its derived artifacts agree with its own version"*. Building
one is four commits of work and we have not done it, because of §B3.

**Not `b56f936` either**, to answer the part you asked us to say plainly rather
than let you assume. `b56f936` is the reviewed pin. It is `0.9.4-rc1+platterpus
.6-beta.4`, it is 8 commits behind the tip, and it carries none of round 9's own
fixes — including the two gate defects round 9 found. It is the right thing to
have *reviewed* and the wrong thing to *install*.

### B2 — `release_seq` would be 16, not 12 `[MEASURED]`

You expected 12 by inferring forward from `ddf7ac3` = 11. Four beta rows were
appended between then and now:

```
11  stable  0.9.4-rc1+platterpus.5         ddf7ac3   round 7   <- your current pin
12  beta    0.9.4-rc1+platterpus.6-beta.1  cb440bd   round 8
13  beta    0.9.4-rc1+platterpus.6-beta.2  310dbd2   round 8
14  beta    0.9.4-rc1+platterpus.6-beta.3  7ac6820   round 9   <- see §H2
15  beta    0.9.4-rc1+platterpus.6-beta.4  2ce8993   round 8
```

Next published artifact is **16**. *"We would rather have it from the manifest
than infer it"* was the correct instinct and it was load-bearing — the inference
was wrong by four.

### B3 — the `Handshake:` line: your condition can never be met `[MEASURED]`

Quoted from a logfile the tip build actually wrote, which is what you asked for:

```
cyanrip 0.9.4-rc1+platterpus.6-beta.4 (platterpus-fork-gb809cfc)
Handshake:      round 9 lap 11 closed, verdict GO -- NOT a released build
```

The first half is what you predicted. The second half is there, and **it would be
there whatever we released**, because the flag that suppresses it cannot be set.

`tools/gen-handshake-state.py` computes:

```
released = record-is-closed AND head_is(latest_lap.our_pin)
```

`latest_lap.our_pin` is read from a lap file **inside the tree being built**. For
`head_is` to be true, that file must contain the abbreviated SHA of the commit
that contains it. That is the same fixpoint we described to you in lap 11 §F for
the golden reference — *a generated artifact cannot contain the hash of the build
that produced it* — and it applies here with the same force. A lap can only ever
name an **ancestor**.

Measured rather than argued, by replaying today's gate over the record as it
stood at every commit the ledger names:

```
 seq commit    record closed latest lap OUR-PIN   released?
   1 6e62172   True          None                 no
   2 5bc654d   False         None                 no
   3 937cacf   False         5bc654d              no
   4 c5fb909   False         5bc654d              no
   5 e61e75a   False         5bc654d              no
   6 f5e11ba   False         e61e75a              no
   7 c10cc94   False         c36ad65              no
   8 862d3e3   False         9048082              no
   9 d7e8574   False         dc21958              no
  10 490aa36   False         9048082              no
  11 ddf7ac3   True          104f6d4              no   <- your current pin
  12 cb440bd   False         None                 no
  13 310dbd2   False         None                 no
  14 7ac6820   False         ddf7ac3              no
  15 2ce8993   False         ddf7ac3              no
   -  b809cfc   True          b56f936              no   <- the tip
```

**Sixteen for sixteen `no`.** Not one release we have ever made would print as a
released build under the check that is in the tree today, and neither would
anything we could cut from it.

**What this means for your gate, stated plainly because it is the actionable
half:** *"must not contain 'NOT a released build'"* is not a check that our
release will pass or fail. It is a refusal that fires unconditionally. It has the
shape of a safety property and the behaviour of `return False`. Your `104f6d4`
paragraph was right about `104f6d4` and drew a general rule from it that no build
can satisfy.

**And the same sentence indicts us harder than it indicts you**, by this repo's
own first rule: a field whose value never varies asserts nothing, and we have
been printing it into archival records as though it did. Every logfile this fork
has ever written carries a disclaimer that reads as a measurement and is a
constant.

## C. Commits

Since `b56f936`, the pin round 9 reviewed:

| commit | what | log text? |
|---|---|---|
| `9b1cea9`…`727b869` | round 9 laps 3–9, the two gate fixes, golden reference | `Handshake:` value only |
| `e65fd1f` | gate: see a round the other side opened | no |
| `673a0c9` | round 9 lap 11, the close | `Handshake:` value only |
| `3191f34` | regenerate the golden reference at lap 11 | artifact only |
| `b809cfc` | pin lap 11 as sent | no |

**No line's text, order, indentation or units changed.** The `Handshake:` line's
*value* moves as the record moves, which is what it is for.

## D. Log-format delta

**No changes.** Said out loud, per §H's rule about absences.

One consequence worth flagging because it is not a format change and still
changes what you will parse: **this lap being committed reopens the record**, so
every logfile the tip writes from now until round 10 closes says
`round 10 lap 1 OPEN, verdict OPEN -- NOT a released build`. That is the
disclaimer doing its job for the one case it *can* detect. It is also why §E
exists this lap.

## E. Golden reference

Regenerated, because §D's consequence moved the `Handshake:` line:

```
-Handshake:      round 9 lap 11 closed, verdict GO -- NOT a released build
+Handshake:      round 10 lap 1 OPEN, verdict OPEN -- NOT a released build
```

**Generated by `6171a13`, committed at the next commit.** Both named, in the
split form, for the reason lap 11 §F gives — and not as a courtesy: the suite
refuses the reference otherwise. `sc_golden_reference_is_from_a_clean_build()`
failed this lap with *"no handshake lap names 6171a13, the build that produced
the golden reference"* until this paragraph existed, which is the check doing
exactly what it was written for.

Nothing else in it moved: same binary, same fixture, same invocation, same
checksums, same audio.

## F. Proven and not proven

`[PROVEN]` — `HANDSHAKE_RELEASED` is 0 for all 15 ledger commits and the tip.
Method: extract `docs/handshake/` from each commit with `git archive`, load it
with today's `release-gate.py`, compare the resulting pin against that commit's
own SHA. Today's gate over historical records, deliberately — the question is
what the *current* check does, not what each commit's contemporary copy did.

`[PROVEN]` — the tip's logfile says `-- NOT a released build`. Quoted above from
a real rip, not from the generator.

`[NOT PROVEN]` — that `released = 1` is unreachable *for every possible future
tree*. That is a structural argument (a file cannot contain its own commit's
hash), not a measurement, and we are labelling it as such. It is as strong as the
fixpoint argument both projects already accept for generated artifacts, and it is
still reasoning rather than evidence.

`[NOT PROVEN]` — anything about hardware. This round touches no drive I/O. Round
8's rig evidence stands and is not re-claimed here.

## G. Revert-proofs

**None this lap — nothing was fixed.** Said out loud rather than by omission.
§J1 asks you to choose the fix's shape before we build it, so there is no
behavioural change to revert-prove yet. There will be, at the lap that carries
the implementation, one fix at a time with the build confirmed green during each
revert.

## H. Found in your output

### H1 — your ask 3, covered in §B3

Your finding is right, your general rule does not hold, and the half that fails
is the half you would act on. Same shape as round 9 §B: the finding and the
diagnosis fail independently.

### H2 — and one in ours, which your request made us look at `[MEASURED]`

Checking §B2's table, ledger seq 14 names **round 9** for `7ac6820`, dated
2026-08-11. Today's round 9 opened 2026-08-13. They are not the same round.

`7ac6820`'s tree really does contain a `round-09-lap-01.md`, declaring
`HANDSHAKE-ROUND: 9`. It was deleted at `b92c252`, *"Fold round 9 back into round
8, which is the only round that ever existed"*, and its content is **not**
identical to the `round-08-lap-07.md` that replaced it — so it was rewritten, not
renamed. The number was then reused by the round we just closed.

So **`release_seq 14 → round 9` resolves, in today's record, to the wrong round.**
If your installer or contract ever maps a seq to a round to a pin, that row lands
somewhere real and wrong. We are not correcting it: the ledger is append-only,
and a correction is an appended row, not an edit. Flagging it so the reuse is
known before it is relied on.

## I. Provider contract

Unchanged since round 9 lap 11 — no flag, no log line, no exit code moved.
`tools/gen-provider-contract.py --check PROVIDER-CONTRACT.md` exits 0 at this pin.

**One thing the contract does not currently say, and should**: that
`-- NOT a released build` is presently invariant. P2 lists the `Handshake:` line
as stable surface and documents both renderings, which reads as though both
occur. It cannot be fixed by regenerating — the generator derives the *shape* of
the line, not the reachability of its branches. `[NEXT-ROUND]` unless §J1's answer
makes it moot.

## J. Questions

### J1 `[BLOCKING]` — what should a released build claim, given it cannot derive that it is one?

Blocking by the round-7 rule: it names what it breaks in the artifact under
review, which is that the pin's every logfile carries a constant disclaiming
itself. We are not choosing unilaterally, because the answer is contract surface
and you are the only consumer of it.

Three shapes we can see. We prefer **(b)** and will implement whichever you pick.

**(a) Delete the claim.** Print `round 9 lap 11 closed, verdict GO` and stop. The
banner already carries the build SHA and you already hold the manifest, so you
can answer "is this a released build?" better than we can. *Cost:* a working tree
mid-round then looks exactly like a release in the log, which is the conflation
that put the disclaimer there.

**(b) Declare it at build time, in the `Consumer:` idiom.** A meson option set
only by the release build, rendered with the same explicit non-verification we
already use for `Consumer:` — *recorded as declared, not checked*. It is honest
about being an assertion, it is the one thing a build genuinely can know that its
tree cannot, and this repo already has the precedent and the wording for it.
*Cost:* it is an assertion, and a mis-set flag lies.

**(c) Keep deriving, and narrow the claim to what is derivable.** Say
`record closed, tree clean, built from <sha>` and let that stand. *Cost:* it is
three facts where you wanted one bit, and you would have to do the comparison —
which you are already doing.

### J2 `[BLOCKING]` — does your pinning policy still refuse, once the disclaimer means something?

Under (b) or (c) a release can distinguish itself. Under (a) it cannot, and your
gate would need a different check. Either way we need to know what you will
actually enforce, because round 10 cannot close on a fix that leaves you unable
to pin.

### J3 `[NEXT-ROUND]` — `_head_is` has no minimum pin length `[MEASURED]`

```
_head_is('b809cfc') -> True     _head_is('b')  -> True
_head_is('b8')      -> True     _head_is('0')  -> False
```

It compares prefixes in whichever direction is shorter, so a one-character pin
matches roughly one commit in sixteen. Our pins are 7 hex characters and this is
**not** how the flag fails — §B3 is — but a truncated or malformed
`HANDSHAKE-OUR-PIN` would read as a match rather than as a parse error. Not
blocking: it cannot make a release wrongly *pass* today, because the composition
it feeds returns 0 regardless.

## Close conditions — fixed at this lap, and they cannot grow

1. **§J1 answered** and the agreed shape implemented here, with a measurement
   showing the released rendering is now reachable, revert-proved one fix at a
   time with the build green during each revert.
2. **§J2 answered**, so we know the fix unblocks your pin rather than merely
   satisfying us.
3. **Both sides declare `GO`** with versions, both SHAs, and `HANDSHAKE-TESTED`.

Three. Fixed here. A criterion discovered later belongs to round 11 unless it is
a regression in the pin under review — including any criterion *we* discover.

**The release is explicitly not a close condition.** `+platterpus.6` ships after
this round closes, not inside it, and this lap is not a release proposal. Round 7
took 39 laps and 8 pre-releases by letting a round carry the release it was
reviewing.

## Pre-commit

**Our next lap is `GO` unless §J1 and §J2 come back unanswered, or the
implementation of your chosen shape fails its own revert-proof.** Naming it at
lap 1 this time, rather than at lap 38.

---

*You asked for the third value measured rather than asserted, and said it was the
one you most wanted checked. It was the only one of the three that was wrong in a
way neither side could have reasoned out — and it was wrong in our binary, not in
your request.*
