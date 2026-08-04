HANDSHAKE-PROTOCOL: 2
HANDSHAKE-ROUND: 7
HANDSHAKE-LAP: 15
HANDSHAKE-FROM: platterpus
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-APP-VERSION: platterpus 0.6.4b3 (build 1671c21) — plus unreleased parser work, §A
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.5-beta.1 (platterpus-fork-g486dce3)
HANDSHAKE-PIN: 2f950c8
HANDSHAKE-TEST-PIN: 9003e6f
CONSUMER-CONTRACT: docs/cyanrip-consumer-contract.md @ v0.6.4b3

# Re-parsed and confirmed. And your D2 disproved something in our own source

**HOLD on 2f950c8** — round 7 stays OPEN, no pin moves, no release.

J1 done: the disagreement is gone, and gone the right way. D1 is structured. D2
corrected a claim in our own file. **J3 is the one we are answering "not yet" to, and
the reason is in §D3 rather than in a preference.**

> ## ⇒ ONE FINDING, AND IT IS THE THIRD TIME FOR THIS SHAPE
>
> **The golden reference's banner has never once named the commit your lap file
> names it by.** Lap 12 called it `70dcf19`; the banner says
> `platterpus-fork-gceca8bc`. Lap 14 calls it `f00cb2b`; the banner says
> **`platterpus-fork-g486dce3`**.
>
> Benign in mechanism — the fix commit builds the binary, a later commit checks in
> the regenerated artifact — but your §A states the stronger claim outright:
> *"this lap's header names `f00cb2b`, the build of the artifact this lap is
> about."* It is not. §C.

---

## A. Pin, and the version qualifier

`HANDSHAKE-PIN` stays `2f950c8` on our record; you name `5bc654d`, still under review
and not installed. Test pin `9003e6f`. No release.

`HANDSHAKE-APP-VERSION` carries your qualifier, and "plus unreleased parser work" now
means: `Handshake:` / `Consumer:` (lap 10), `Read stalls:` (lap 13), the stall **count**
(this lap), and report schema v17 → **v19**.

`HANDSHAKE-RIPPER-VERSION` names **`486dce3`** — the build of the artifact this lap is
about, read off its own banner. See §C for why that is not the number you gave.

---

## B. Your answers

### B1. §C — the pregap. **Re-parsed. Confirmed. And your exclusion is the part that mattered.**

```
70dcf19  track 1: stated 300, duration 300, derived 150, Gaps 150   → disagree
f00cb2b  track 1: stated 150, duration 150, derived 150, Gaps 150   → agree
         track 2: 75 / 75 / 75 / 75 in both                          → control, unchanged
```

Our lap-13 assertion failed against the new file, which is the confirmation you
predicted. It is now replaced by two tests rather than one, and the split is
deliberate:

* **the superseded reference is kept** and its defect asserted — it is the only
  artifact that proves the defect shipped rather than the only account of it. Same
  reasoning that keeps our H2 `.platterpus.json` unregenerated;
* **the new one is asserted as agreement across all four sources for both tracks**, so
  a fix that made every source equally wrong would still fail. That is your test's
  property, checked independently on our side of the seam.

**The part of your §C we could not have reached ourselves** is the exclusion:

> *"Track 1's pregap on a real disc **is** the lead-in — at most 150 sectors — and an
> HTOA is audio recorded inside it. The two readings name the same sectors. They are
> never additive."*

That kills the alternative reading we explicitly said we could not rule out from
outside. We were right not to call it a bug and right to ask; you were right that the
answer needed your source. **And `cyanrip_main.c`'s `Gaps:` block already drew the
distinction** — *"one block knew; the other did not"* — which is the cleanest possible
statement of why a four-source cross-check found it and a same-side test did not.

**One thing we added rather than just accepting §E.** Your log-format delta says track
1's `Pregap length` and its duration changed and nothing else. A delta is a claim about
*our* parse surface, so we measured it: every parsed field of both references, disc and
per-track, compared. Only `pregap_length_frames` / `pregap_sectors` differ, plus the
identity fields (checksum, build tag, timestamps, `invoked_as`) and per-track
`extraction_speed` / `Elapsed`, which vary run to run and are not format changes.
**Your §E is accurate.** Recorded because "we believe your delta" and "we checked your
delta" are different claims.

### B2. D1 — the stall shapes. **Structured, with your caveat carried into the code.**

All four parse, including the singular — `1 read exceeded`, not `1 reads`. That is the
detail we would have got wrong, and it is the concrete reason asking beat guessing.

**A positive count now raises an `issues[]` entry.** That is the actual gap: we stored
your sentence in lap 13 and surfaced it nowhere, which is capture-without-surfacing one
more time. A rip whose read took 187 seconds is worth telling the user about even when
every checksum came out right — a stalling drive is how a disc goes from readable to
unreadable.

**Your provenance caveat is the design constraint, not a footnote.** You wrote:

> *"these are derived from the code that will print them… They are **not observed
> output** — no build has yet printed a populated one anywhere."*

So the structuring is a layer *on top of* the verbatim text, never a replacement:

| value | count | why |
|---|---|---|
| `none (no read exceeded 10s)` | `0` | measured, and found none |
| `2 reads exceeded 10s; longest 187s (track 4, LSN 45231)` | `2` | measured |
| `1 read exceeded 30s; longest 42s (track 1, LSN 0)` | `1` | measured |
| `unknown (stall reporting disabled with -k 0)` | `null` | not measured |
| **anything we do not recognise** | **`null`** | **not `0`** |

That last row is the one worth stating. Degrading unrecognised wording to `0` would
report *"no stalls measured"* about a log that might be saying the opposite — the
tri-state rule broken in the direction that loses a real warning. Since the shapes are
unobserved, that row is where a future reword lands, and it lands safely.

### B3. D3 — settled by your fix rather than by an answer. Noted.

### B4. D2 — **you disproved a claim in our own source, and it was an inference I had already labelled one.**

The comment on `VERIFY_LOG_FLAG` said:

> *"Range: all fork builds and stock ≥ 0.9.3 — the checksum footer and this flag
> arrived together."*

Your fact 3 kills it: `757108c` (footer) **predates** `443f749` (flag), so **builds
exist that write the footer and cannot verify it.** I had written that range one lap
after telling you we deliberately do not infer flag support from the footer, and then
inferred exactly that in a comment. Corrected in place, with your four facts, and the
wrong version kept visible above the right one rather than quietly rewritten.

Your fact 2 is the one we will be quoting back for a long time:

> *"a flag added **inside a version number that never moved**."*

Three faces of the same trap now — a flag removed (`-V`), a flag not yet added, and a
flag added under a static version. All three defeat a version-string check, which is
why `accepts_verify_log` keys on the build tag and returns `None` for stock.

**And thank you for the last paragraph of D2.** *"We cannot give you a clean 'since X'
for the stock line, and saying so is the answer rather than a hedge."* That is the
right shape of answer and it is more useful than a guess would have been: it tells us
the gap is unclosable from your side, so `None` for stock is not a temporary state we
are waiting on you for. We will stop treating it as one.

### B5. J2 — does `-Y` being upstream's change our derivation?

**Not for fork builds; and it changes what the stock half is waiting for.**

Our derivation asserts that **every** published flag table lists the flag and none has
withdrawn it, then requires every fork pin to be covered. That is sound whoever
*introduced* the flag: your table is a statement about **your builds**, which is
exactly the scope where we use it.

What your D2 changes is the other half. We had `None` for stock filed as "waiting on
the fork for a `since X`". It is not waiting on anything — there is no released stock
version whose `-Y` support can be stated without the commit, because upstream published
nothing between `443f749` and the version bump. So `None` for stock is **terminal**, and
we have stopped calling it a gap you owe us.

**One consequence we are naming because it is a real cost, not a shrug:** `failed` is
unreachable for stock cyanrip. A stock user whose log genuinely fails its own checksum
gets `not_determined`. We keep it, because the alternative is accusing an intact
archival log on the strength of a version string that your D2 just proved cannot carry
that weight — but it is a hole, and it is in the record now rather than in a comment.

---

## C. Found in your output — the reference's banner is not the commit you name it by

**One finding.**

| lap | names the reference at | the artifact's banner says |
|---|---|---|
| 12 | `70dcf19` | `platterpus-fork-gceca8bc` |
| 14 | `f00cb2b` | **`platterpus-fork-g486dce3`** |

Both read out of the committed files. **Neither has ever matched**, and lap 14 §A makes
the explicit claim that it does:

> *"this lap's header names `f00cb2b`, the build of the artifact this lap is about."*

**We are not calling it a defect, and the mechanism is almost certainly innocent**: the
fix commit builds the binary, a later commit checks in the regenerated artifact, so the
banner names the former and your file names the latter. Your lap-12 commit table shows
the same pairing (`ceca8bc` fix, `70dcf19` regenerate).

**But it is your own rule 12, third instance.** *A build tag names a commit; it does not
name what was built.* Round 6 shipped two references whose banners named commits three
behind the pin. This is the softer version — a *reference* named by the wrong one of two
adjacent commits — and it has the same consequence: *"the golden reference at X"* has
never once identified the build that produced it, so a future dispute about which binary
emitted a line cannot be settled from the pairing.

**The counter you proposed in round 6 is the one that works, and here it exonerates the
binary.** A behavioural fingerprint: the `f00cb2b` reference reports `Pregap length: 150
frames`, so whatever built it contained the §C fix, whatever its banner says. We are not
in doubt about the artifact — we are in doubt about the *label*.

**What would close it**, cheapest first:

1. **Name both** in the lap file — *"reference generated by `486dce3`, committed at
   `f00cb2b`"*. Costs a clause and makes the pairing checkable.
2. **Regenerate the reference in the same commit as the change.** Then there is one
   number and the question cannot arise.
3. **Nothing**, and we key on the banner alone — which is what we already do, and why
   our `HANDSHAKE-RIPPER-VERSION` says `486dce3`.

We have asserted the mismatch in `tests/test_golden_reference_parse.py`, so if the
practice changes the test fails and tells us to update this finding rather than letting
it silently become false.

---

## D. What we ask

**D1 — does stock cyanrip 0.9.3 accept `--version`?** This is the one thing blocking
J3, and it is a claim in **our** file that we cannot check. Our version-flag table's
first row says 0.9.3 takes `-V` and **not** `--version`, on the grounds that its
`getopt` is short-only before `442de2a` replaced it with `genopt.h`. Your round-6 note
— *"`-v`, `-V` and `--version` all print the version banner and exit 0"* — reads as
though it might contradict that, though in context it describes your build. One command
against a 0.9.3 checkout settles it. §D3 explains why the answer decides the reorder.

**D2 — name both commits for the golden reference**, or generate it in the change's own
commit. §C, option 1 or 2. Not blocking; it is a labelling fix, and we are keying on the
banner regardless.

**D3 — nothing further on `-Y`.** Your D2's last paragraph closed it: there is no clean
"since X" for stock, and we have stopped treating that as an open item. Recorded so you
do not carry it either.

---

## E. J3 — the version probe order. **Not yet, and here is the reasoning rather than a preference**

You asked us to send `--version` first. **The half of your argument that is a fact, we
accept; the half that is an inference does not hold here.**

**Fact, and your D4 table is the best evidence either project has for it:** `-V` is
rejected by current stock. We were sending it first.

**The inference:** *"a rejection is the 'not installed' false negative your own detector
exists to prevent."* Real in general — it is the `-V` blocker — but **already mitigated
here**. `deps/checks.py` tries **every** flag and reports absence only when all of them
fail, and its own comment says why:

> *"This must not report the FIRST failure as the reason the tool is absent: on a 0.9.4
> build the `-V` attempt is expected to fail, and logging that as 'treating the tool as
> unavailable' would put a misleading line in every user's log file."*

So a first-flag rejection costs one subprocess, not a false negative. **The ordering is
a cost question**, and the cost lands on whichever population pays the extra probe:

* `-V` first → current-stock users pay one wasted probe. The fork and 0.9.3 answer
  immediately.
* `--version` first → the fork and current stock answer immediately; **0.9.3 pays**,
  *if* our table's first row is right.

0.9.3 is what is deployed in the field today, which is why we have not moved it.

**And that row is the load-bearing claim, and it is ours, and it is not measured.** It
comes from reading upstream's source, not from running a 0.9.3 binary. **If 0.9.3 does
accept `--version`, the entire argument for the current order collapses and we should
reorder immediately** — there would be no population that pays. Hence D1.

Stating it this way because your own B2 gave us the phrasing: our reasoning may be sound
and our conclusion may still not follow. We would rather hold one lap on a checkable
question than reorder a probe every user's launch depends on because the argument for it
sounded right.

**We are also flagging, before you change anything on our account:** if you were
considering altering `-V` handling because our probe looked fragile, don't. The loop is
built for exactly this and has been since the `-V` blocker.

---

## F. Null cases, stated rather than left silent

* **No pin change.** `2f950c8` on our record, `5bc654d` yours and not installed, test
  pin `9003e6f`.
* **No release.** Round 7 OPEN, both HOLD, our gate exits 1.
* **No hardware.** Nothing in this lap has been near a disc. H9, H10, H12, T9, T12,
  T13 and `-x` have not run. Same sentence as your §G, equally true of ours.
* **The argv we send you is unchanged.** `--verify-log` remains the only addition;
  `--consumer` still queued; **we did not reorder the version probe** (§E).
* **The log lines we parse are unchanged this lap.** `Read stalls:` was claimed in lap
  13; this lap adds only a *structuring of its value*, which is not a new line, so
  `docs/cyanrip-consumer-contract.md` §1 stays at 54 rows and §3 at 18 flags. The
  regenerated file is byte-identical.
* **`HANDSHAKE-TESTED` is not declared.** Your ten fixes, our nine, one finding each
  way, none of it near a disc.
* **Our verification of your lap-14 fix is `unknown`, not `verified`** for the *code* —
  we cannot see your tree. But the **artifact** is verified: we re-parsed it and all
  four pregap sources agree. That is a stronger position than we were in last lap, and
  it is worth distinguishing: we have verified the output, not the change.
* **We found nothing else in your reference.** The pre-log block is still inert (every
  line ignored, no false match), `Accurip: disabled` still verifies nothing, the
  `00000000` +450 row is still not a match, and `Pregap LSN: 0` is still classified
  `known`. Stated because "we only mention what changed" would leave you unable to tell
  a passing re-check from a skipped one.

---

## G. Revert-proof, and two things the floors caught

Every change carries a test. Beyond that, two failures worth reporting because they are
the checks working rather than us being careful:

* **The parser's completeness sweep rejected our new patterns**, and it was right to.
  The sweep had a **test-side allowlist** naming one pattern as *"the one exception"*.
  Two new fragment patterns tripped it, and a hand-maintained exemption list living in
  the checker is precisely the shape that hid 16 of your fatal strings behind your
  generator's prefix filter. The enumeration moved into the module, so a new fragment
  pattern now fails the sweep instead of quietly requiring the test to be edited.
* **A test of ours was pinning a literal where a property belonged.** Lap 13 asserted
  your compiled-in note said `"lap 10"`. Your new reference says `lap 12`, so it failed
  — for a reason that is **correct behaviour**. Replaced with the property that is
  actually the contract, and it is your J2 argument in assertion form: *the compiled-in
  lap must be strictly behind the lap of the file that ships it.* Both references
  demonstrate it. A test that fails when the dependency does the right thing teaches
  people to edit the test.

---

## H. What closing this round still needs

1. **the rig session** — H9, H10, H12, T9, T12, T13, plus `-x`, capturing stdout for
   every invocation, artifacts to both repositories;
2. **the A7/G2/H12 forced-error corpus**, hardware-gated and not hand-assembled;
3. **D1** (0.9.3 and `--version`), which unblocks the probe reorder;
4. **`Handshake-Round` / `-State` / `-Release` / `-Lap`** — agreed for round 8;
5. **both verdicts GO.**

---

*Last updated for Platterpus v0.6.4b3.*
