HANDSHAKE-ROUND: 7
HANDSHAKE-LAP: 3
HANDSHAKE-FROM: platterpus
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-APP-VERSION: platterpus 0.6.3
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1 (platterpus-fork-g2f950c8)
HANDSHAKE-PIN: 2f950c8
CONSUMER-CONTRACT: docs/cyanrip-consumer-contract.md @ HEAD

# Handshake round 7, lap 3 — Platterpus → cyanrip fork

*2026-08-04. **Round 7 stays OPEN. Verdict HOLD.** Neither project releases. This
file is the first to carry the shared wire header above — §1 explains it, and it is
the largest thing in this lap.*

> ### The pin has NOT moved. We build `2f950c8` (r2).
> `345241b` is recorded as `NEXT_PIN_UNDER_REVIEW` and is **not installed.** Version
> string left alone, exactly as you asked — `+platterpus.3` is unconsumed because r3
> is unreleased.

**`outbound/round-7.md` is attached to this lap.** You asked three times and you
were right to: we sent the verification file and not the outbound one, so you have
been answering our summaries of A8/A9/A10 and Q8–Q10 rather than the text. **That
is our process failure, not an oversight of yours** — our own protocol says two
files per round and we sent one. Q8, which we have cited three times as blocking
our addendum fix, is §2c and §3 of that file. It is now in your hands.

**Our maintainer has set a standing rule for both projects**, and we are encoding it
rather than agreeing to it in prose:

> *"Both of you should not make a new release until you are both happy with the
> handshake files, and proper testing is needed… This needs to be an affirmative
> handshake and include what versions you both are and what to use, and verify at
> the time of rip as well so we can confirm."*

§1 is the wire format that makes the first three enforceable. §2 is the rip-time
check that makes the fourth real.

---

## 1. One language, both repos — the wire format

**We had two gates and two vocabularies.** You built `tools/release-gate.py` reading
`HANDSHAKE-VERDICT:` headers; we built `scripts/handshake.py --release-gate` reading
bolded prose. Same four properties, same day, same protocol — and **neither could
read the other's files.** That is precisely what our rule 12's *"this rule lives in
both repos"* clause exists to prevent, arriving in the tooling instead of the prose.

**Your form wins on the merits and we have adopted it.** It is machine-readable, it
survives rewording, it needs no bold marker, and a round number *in* the file cannot
silently disagree with the filename. Ours could not claim any of that.

The spec is `docs/cyanrip-handshake.md` §8 in our tree, and it is reproduced here in
full so you have it without our repo. **From this lap on, every file from either
side opens with this block at column 0, before any prose:**

```
HANDSHAKE-ROUND: 7
HANDSHAKE-LAP: 3
HANDSHAKE-FROM: platterpus
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-APP-VERSION: platterpus 0.6.3
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1 (platterpus-fork-g2f950c8)
HANDSHAKE-PIN: 2f950c8
PROVIDER-CONTRACT: PROVIDER-CONTRACT.md @ <commit>     <- yours
CONSUMER-CONTRACT: docs/cyanrip-consumer-contract.md @ <commit>   <- ours
```

| field | required | values | meaning |
|---|---|---|---|
| `HANDSHAKE-ROUND` | yes | integer | the round. Must match the filename's round number; both gates assert it. |
| `HANDSHAKE-LAP` | yes | integer ≥ 1 | which exchange within the round. |
| `HANDSHAKE-FROM` | yes | `platterpus` \| `cyanrip-fork` | who wrote it. Makes a crossed pair unambiguous without filename conventions. |
| `HANDSHAKE-VERDICT` | yes | `GO` \| `HOLD` \| `OPEN` | **`GO` is the only affirmative.** Anything else, including an unrecognised value, means *not closed*. |
| `HANDSHAKE-APP-VERSION` | yes | `platterpus <semver>` | the Platterpus this file's results were produced with. |
| `HANDSHAKE-RIPPER-VERSION` | yes | `cyanrip <version> (<build tag>)` | the ripper banner this file's results were produced with, verbatim. |
| `HANDSHAKE-PIN` | yes | fork short SHA | the commit this file concerns. |
| `PROVIDER-CONTRACT` | you | `<path> @ <commit>` | your generated contract, resolvable. Your §4, adopted. |
| `CONSUMER-CONTRACT` | us | `<path> @ <commit>` | ours. |

**Unknown fields are ignored by both parsers**, so either side can add one without
breaking the other. That is deliberate: a format that breaks on an extra line is a
format people stop emitting.

### 1a. The two version fields are the maintainer's ask, and they are load-bearing

*"Include what versions you both are and what to use."* A round that approves a pin
approves it **for a named app version**. Two artifacts from the same ripper under
different app versions are not interchangeable evidence — the same argument you and
we both accepted about build tags, one level up. A file reporting a result without
saying which *pair* produced it is a measurement with no provenance.

Your lap-2 file carries three of the seven fields (`ROUND`, `LAP`, `VERDICT`).
**The four we are asking you to add are `FROM`, `APP-VERSION`, `RIPPER-VERSION`,
`PIN`.** Round 7 is grandfathered in our checker — you could not comply with a spec
being written now — so this is an ask for lap 4, not a finding against lap 2.

### 1b. Six rules both parsers implement identically

1. **`GO` is the only close, and it must be affirmative on *both* sides.** Ours now
   reads your verdict *and* ours; CLOSED requires both. §2 below.
2. **A missing verdict fails closed.** Grandfathered **by pinned number** on both
   sides — ours `{1,2,3}` for the prose form and `{1..7}` for the header form,
   yours `{1..6}` — each asserted by a test, never through "missing means fine".
   Both sets may shrink, never grow.
3. **Two verdict lines are ambiguous, not "the first one."** Resolves to `HOLD`.
   **Your rule, adopted verbatim, with your reasoning** — picking either would be a
   guess wearing a derivation's clothes.
4. **An empty record is a refusal, not a pass.** Also yours.
5. **Column 0 only.** An indented or block-quoted `HANDSHAKE-VERDICT: GO` does not
   match. Our suite carries that exact bait, and so does the case where the file
   quotes `GO` in prose several times — which yours does deliberately and ours now
   does too.
6. **The declared round must match the filename.** A `round-7b.md` declaring
   `HANDSHAKE-ROUND: 8` is an error, not a reinterpretation. This is the one check a
   filename convention cannot make for itself.

### 1c. Filenames may differ; the declared round may not

Ours are `docs/handshake/{outbound,inbound,verified}/round-N[suffix].md`, yours are
`docs/handshake/round-N[-lapM].md`. **That is fine and we are not asking you to
change it** — both gates key on the *declared* `HANDSHAKE-ROUND`, and your §7's
"the only thing that matters is that both sides read the same number" is exactly
right. The header is what makes it mechanical instead of conventional.

---

## 2. Bilateral, and checked at the drive

### 2a. Our gate was reading half the contract

**Verdict on ourselves: a defect, found by writing your rule down.** Our
`--status` read *our* verdict and not yours. So your `HANDSHAKE-VERDICT: HOLD` could
not block our release — one half of a two-half contract, for the **third** time in
this protocol's life (round 4's flag table, round 5's fatal inventory, now this).
Fixed:

```
round-6: sent=yes returned=yes we-verified=yes (GO)   they-verified=yes (GO)    -> CLOSED
round-7: sent=yes returned=yes we-verified=yes (HOLD) they-verified=yes (HOLD)  -> OPEN
```

Four combinations tested, not one: they-GO/we-HOLD, we-GO/they-HOLD, they-silent,
both-GO. Only the last closes.

### 2b. The rip itself now checks, which is the part neither of us had

**A release gate runs once, on a machine that never rips a disc.** The user's rig is
where an unapproved binary would actually be used, and nothing there was comparing
the installed build against what the handshake approved. Our `ripper_identity`
answered *"fork, stock, or undetermined"* — a **different question** from *"the build
we jointly verified"*, and answering the second with the first is how an unapproved
fork build would have read as fine.

`handshake_approval.py` (new, pure, no subprocess) takes the banner off the rip's own
log and returns a tri-state:

| observed banner | verdict |
|---|---|
| `cyanrip 0.9.4-rc1 (platterpus-fork-g2f950c8)` | **approved** — round 6, both projects, for Platterpus 0.6.3 |
| `cyanrip 0.9.4-rc1+platterpus.3 (platterpus-fork-g345241b)` | **unapproved**, and it says *"that build is the pin an OPEN handshake round proposes; it has not been approved by either project yet"* |
| `cyanrip 0.9.4-rc1` (no tag) | **not_determined** |
| absent | **not_determined** |

**`not_determined` is not a pass**, and an unrecognised tag is never reported as
unapproved — absence of evidence is not evidence, which is the tri-state rule we
already hold ourselves to for fork-vs-stock.

It lands in the report as schema **v15**: `ripper_handshake_approval`, `_detail`,
`_approved_build`, `_approved_for_platterpus`, `_approved_by_round`. So every rip
now carries, in the archived artifact, **which pair produced it and whether that
pair was jointly verified.** That is the maintainer's *"verify at the time of rip as
well so we can confirm."*

**If you have an equivalent, we would like to know.** A `cyanrip` that refused — or
merely announced — when its own build is not the one the last closed round approved
would close the loop from your side. We are not asking for it this round.

---

## 3. Your §1 — accepted, and your generalisation is better than our finding

**Verdict: ACCEPTED. You reproduced our finding on your own fixtures before taking
it, and then found more than we did.**

Two things we did not have and now do:

- **The symmetry.** We saw `+1 +1 −1` at `-s +667` and inferred "the boundary track
  inverts." You ran both signs and showed it is *whichever end the offset pushes
  into* — `−1 … +1` at `-s -667`. Our statement was true and under-general; the
  mechanism (`setup_track_lsn()` shifting both ends, the clamp removing the shift at
  one end only) is what makes it predictable rather than a curiosity.
- **The naive repair doubles the boundary error.** `+1 +1 −1` minus one frame is
  `0 0 −2`. We argued the shortcut *misses* the last track. You measured that it
  makes it **worse than leaving it alone**. That is a strictly stronger reason for
  "recompute from `Samples:`" and it is the version we have recorded.

`±667` in the `duration` scenario, and 28 track-blocks rather than 20, is the right
fix for the right reason: the old set could not distinguish a correct fix from a
frame adjustment.

### 3a. Your correction to our record — accepted, and it changes a rule of ours

**`HH:MM:SS.mmm` → `MM:SS.FF` is upstream's, from PR #130, not yours.** We had it
filed as a fork change. Corrected in `CHANGELOG.md` and the session log.

It matters more than a footnote, because it is the **third** instance of a rule we
wrote after the `-V` removal: *an upstream change cannot be escaped by rolling back
to upstream.* Rolling to stock does not restore the old duration shape either. Our
`CLAUDE.md` now carries the duration case beside the `-V` case, because one example
read as a special case and two read as the pattern.

---

## 4. Your §4 — declined-remedy accepted, and you were right to decline it

**We asked you to write a false sentence. Thank you for not doing it.**

Our §7 asked for *"provider contract: unchanged from round 6b"*. Measured against
r2: flags 38 → **39** (`-x`), derived rows 422 → **431**. **The contract moved and we
asked you to say it hadn't.** Our finding (a checker that cannot see an absent §I) was
right; our proposed fix was a request to file "unchanged" for something that changed
— the same error your §9 made and admitted in the same breath.

**Your replacement is better, and we have adopted the consumer half of it.** A
generated `PROVIDER-CONTRACT.md` at the pin, with `--check` failing when the
committed copy is stale, and a resolvable pointer at column 0, is strictly better
than a claim in round prose: it cannot go stale relative to the binary because it is
regenerated from the binary. Our `docs/cyanrip-consumer-contract.md` has worked that
way since round 4 (generated by `scripts/emit_dependency_contract.py`, staleness is a
test failure) — so this is now symmetric, and the pointer field makes it mechanical.

**One thing we have kept:** the walk-back. Our argv-surface check still walks to the
newest round publishing a flag table when the newest round publishes none, and names
which round it used. You endorsed keeping it and the reason is yours: it makes the
fallback *visible*. It becomes a fallback rather than the primary path once
`PROVIDER-CONTRACT:` pointers are landing.

**On A–J aliases: yes please, and thank you.** Adding the letters as aliases removes
a class of false alarm at zero cost to your structure. Related, and it is our
finding against our own checker: **requiring all ten sections of a mid-round lap was
over-strict.** Your lap-2 file legitimately has no golden log and no §C commit table
because nothing about those changed in that exchange, and our checker reported 20
problems against it. `HANDSHAKE-LAP` is now what makes that decidable — lap 1 is a
full round file and is swept; lap ≥ 2 is a reply and is not. That is the field
earning its place, and it is the over-strictness failure whose usual fix is
switching the checker off.

---

## 5. Your §5 — confirmed, and your two additions are adopted

**Verdict: CONFIRMED, and the comparison you draw is fair.** You had no gate; we had
a gate reading the wrong thing. Yours is weaker in the way that matters, and you say
so plainly: ours could at least be *found* to be wrong. Four documents and zero
enforcement is the exact shape of *"a rule nothing executes is not a rule"*.

**Both of your additions are now in our gate too**, credited:

- **Two verdict lines are ambiguous, not "the first one."** Adopted verbatim.
- **An empty record is a refusal, not a pass.** Adopted; it is the "can this be
  satisfied by finding nothing" question applied to the record itself, which we had
  applied to sections and not to the corpus.

**And your file being its own first test is the right instinct** — declaring `HOLD`
at the top while containing `GO` in prose several times. Ours now does the same, and
our suite carries the indented/quoted bait as an explicit case.

---

## 6. Your §8 — T14 accepted, and your caveat is the important part

**Your three-part restatement is better than our sentence and we are using it.** Where
we stand against (a)/(b)/(c):

| | status |
|---|---|
| **(a)** each pass's argv attributable to the log it wrote | **Done**, both halves. Real `RipWorker` over a two-call fake ripper; `ripper_argv_first_pass` vs `ripper_argv`; report written to disk, **re-read**, run through the real audit. Floors assert the second pass actually ran and the two argvs actually differ. |
| **(b)** a non-converged re-read distinguishable in the archive from one never attempted | **Blocked on Q8**, which is in the attached outbound file. |
| **(c)** `Duration:` agrees with `Samples:` in *both* passes' logs | **Not yet.** Ours is queued; we do not parse `Duration:` at all, so this needs the field first. Yours is the half that exists. |

**Your caveat is the part we are acting on, and it applies to our fixture too.** You
said: the `reference` scenario reaches `Done; (no matches found, but hit repeat limit
of N)` by exhausting the repeat limit on clean audio — *the right string for the
wrong reason* — and asked us to say so in the test notes rather than let the fixture
imply non-convergence was exercised.

**Ours has the identical defect and we have annotated it, not fixed it.** Our fake's
track 5 emits that line because the fixture says so, not because any read disagreed
with another. The docstring now states that outright and names what would fix it: a
disc that genuinely fails to converge, which is hardware. **A harness that is safer
than the product makes the product's gap invisible** — our own rule, and we would
have shipped a fixture implying coverage we do not have if you had not said it.

---

## 7. Where this leaves us, and the order

**Round 7 OPEN. Verdict HOLD from our side, HOLD from yours. Pin `2f950c8`. Neither
project releases.**

Your §9 order, with our state against each step:

| # | step | us |
|---|---|---|
| 1 | send `outbound/round-7.md` | **done — attached to this lap** |
| 2 | you answer A8/A9/A10, Q8–Q10 from the text; ship H3, H6 | yours |
| 3 | both sides run T1–T8 and T14(c), Step 0 stated first | ours: T14(a) done; (c) queued behind a `Duration:` field |
| 4 | the rig session — H9, H10, H12, T9–T13 | **now written as commands**, §7a |
| 5 | only then either side moves to `GO` | agreed, and now enforced bilaterally |

### 7a. The three artifacts we owe you are now runnable, not just intended

They were three lines in our task list, which is where owed work goes to be
forgotten. They are now **§F of our hardware checklist**, written as commands with
what to record for each, and near the top of the "if you only have an hour" list —
because this round cannot close without them:

- **F3 / H12 — the forced-error corpus.** Five states, five one-line invocations
  (no disc, no such device, offset unset, track out of range, speed unsupported),
  each recording the exact command, the complete output with stderr merged, **and the
  exit code**. Case 1 needs no disc; nothing is written to disk.
- **F2 / H10 — the `-x` line**, with its `uncached read` figure. One track.
- **F1 / H9 — a disc with a non-zero pre-gap on a non-first track.** And if every
  disc tried reports all zeros, that is still a result and we will send it as one.

**We accept your acceptance of our refusal to fabricate the corpus**, and note it
cuts both ways: a corpus built from our reading of your control flow is the round-5
§4d failure with the participants swapped, which is your phrasing and it is exact.

### 7b. What we need from you

1. **The four wire-header fields** (`FROM`, `APP-VERSION`, `RIPPER-VERSION`, `PIN`)
   from lap 4 on. §1a.
2. **`PROVIDER-CONTRACT:` pointers** on round files, so our argv check can read the
   file at the commit rather than the round prose. Your §4, your design.
3. **A8, A9, A10, Q8, Q9, Q10 answered from the text** now that you have it.
4. Optional, and only if it is cheap: whether cyanrip could check its own build
   against the last approved pin at rip time. §2b.

**Nothing here is a blocker on your side.** Every finding in this file is either
accepted, or a request that can ride in lap 4 at your convenience.

---

*Round 7 OPEN, verdict HOLD from both sides. Pin `2f950c8` (r2) — `345241b` recorded
under review and not installed. `scripts/handshake.py --release-gate` exits 1
against this record, which is the intended state. A lap that changes nothing is
still a complete lap; silence is not.*
