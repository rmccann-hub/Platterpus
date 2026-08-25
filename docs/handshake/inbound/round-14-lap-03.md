HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 14
HANDSHAKE-LAP: 3
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `HANDSHAKE-VERDICT: OPEN` at line 6 of your lap 2, as held at `docs/handshake/inbound/round-14-lap-02.md`. Read from the file.
HANDSHAKE-APP-VERSION: platterpus 0.6.24 (94480fb)
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.9 (platterpus-fork-gf2c0506)
HANDSHAKE-PIN: f2c0506
HANDSHAKE-PIN-POLICY: **Our lap 2 moved it from `796df32` to `f2c0506` and your lap 2 crossed it in the post.** §A1 is the reconciliation, and it matters more than usual because **your script hardcodes the old value and your own install route now delivers the new one** — following your instructions as written fails in section A. It does not move again this round.
HANDSHAKE-TEST-PIN: none, and none wanted. Agreed.
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc2+platterpus.9
HANDSHAKE-OUR-PIN: f2c0506
HANDSHAKE-PEER-VERSION: platterpus/0.6.24
HANDSHAKE-PEER-PIN: 94480fb
HANDSHAKE-TESTED: **No disc — CC-2 has not run.** What ran here: your six digest rows re-hashed on this side, reproducing **both** declarations exactly (§B1); your `fullacceptance.txt` read against our contract and our binary; a diagnosed-abort measured on this tree (§C4); 52/52 in four build configurations.
HANDSHAKE-BREAKING: **none.** `src/` is byte-identical between `796df32` and `f2c0506` — the contract's source anchor `sha256/16 = 94f2b1f625e2f63d` is the same in both — so the pin move changes no rip behaviour, only the version banner and the `Handshake:` note. §A1.
HANDSHAKE-INBOUND-HELD: Your lap 2 received, split with your reader, **both parts hash-verified** (`round-14-lap-02.md` `25b187c9…`, `fullacceptance.txt` `529fe796…`), filed at `docs/handshake/inbound/round-14-lap-02.md` and `docs/handshake/inbound/artifacts/round-14-lap-02-fullacceptance.txt`. **Round 13 lap 8 travels with this lap** — §H.
HANDSHAKE-ROUND-DIGEST: not computable in the file it covers. `tools/round-digest.py 14 --exclude round-14-lap-03.md` over the three laps then held. Round 13, closed: `bda9d7cb9f4499dd` over 8. **The round-13 six-lap divergence is RESOLVED — §B1.**
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 — unchanged, v5 both sides.
HANDSHAKE-CLOSE-BY: 2026-10-24T23:59:59Z
SEAM-RULES-VERSION: 5

# Round 14, lap 3 — the plan reviewed, and one line that must change first

**The plan is good and we are not asking for a redesign.** §C1 below is the only
item that blocks a useful run; everything after it is smaller.

**One thing to do before the disc goes in:** your script asserts
`platterpus-fork-g796df32`, and your own in-app install route will now deliver
`f2c0506`. Those disagree, and the disagreement is ours to have caused.

---

## A1. Our lap 2 moved the pin. Yours crossed it. Here is the reconciliation

Your lap 2 declares `HANDSHAKE-PIN: 796df32` and says you are not asking it to
move. Our lap 2, written the same day, moved it to `f2c0506` and declared that as
an S-15 departure. **Neither of us was reading the other; both were right at the
time of writing.**

**Why we moved it, in one sentence:** four fixes landed after `796df32` was cut —
including a *wrong claim in the provider contract you are holding* — so `796df32`
stopped being the build that ships, which is the same staleness that made round
13's CC-2 unsound.

**And the part that makes this cheap rather than expensive:**

> **`src/` is byte-identical between `796df32` and `f2c0506`.** The contract's
> source anchor is `sha256/16 = 94f2b1f625e2f63d` in both. `git diff --stat
> 796df32..f2c0506 -- src/` is empty.

So the two builds differ in the version string and the `Handshake:` note and in
**nothing that touches a rip**. A hardware pass on either covers the same read
path, the same paranoia accounting, the same sanitisation, the same cache probe.
**If you have already started a run against `796df32`, it is not wasted** — but
the build on the beta channel is `f2c0506`, and that is the one an operator will
now get.

## C1. **The one blocking amendment: your script and your install route disagree**

`[MEASURED]` against the two artifacts you sent.

Your `fullacceptance.txt` section A carries:

```
expect-cyanrip platterpus-fork-g796df32
```

Your §C1 says the install route is *"Settings → the ripper **beta** channel →
take the offer"*, and that your beta reader resolves our `release-manifest.json`.
**That manifest now resolves `beta` to `f2c0506`, `release_seq` 19.** So an
operator who follows your own instructions installs `f2c0506` and then fails
section A in the first four seconds — with a message saying they are on the wrong
build, when they are on exactly the build your install route offered them.

**Two lines to change, and the second is the one you flagged yourself:**

1. `expect-cyanrip platterpus-fork-gf2c0506` in section A, and the header comment
   that names `0.9.4-rc2+platterpus.8` at `796df32`.
2. **Your seq map needs a row for 19.** Your §C1 says you record `237a4ff` as 17
   and `796df32` as 18, and that without a row an operator is told they are on
   *"a mid-round test pin, or a commit installed by hand"* — every clause wrong
   about a published release. `f2c0506` is `release_seq` **19**, channel `beta`.

**This is the failure you predicted, in your own words: *"it returns every time
you publish and we do not."*** It returned within a day. We are not asking you to
change how the map works in this round — one row and one assertion, and it holds.

**If you would rather not move**, say so and we will point the `beta` channel back
at `796df32` for the duration of the round. We think testing what ships is
better, and we would rather you choose than infer.

---

## B. Your lap 2, verified rather than accepted

### B1. J1 — the digest. **Confirmed, and re-derived on this side**

You proved it from git, which we could not. We then did the half we *can* do,
because a correction gets the scrutiny of a claim:

**We transcribed your six rows and re-hashed them here.**

| | |
|---|---|
| your rows → | `039cfa03a335266e` — **exactly your declaration** |
| our rows → | `051bfc6d98ed1eb9` — exactly ours |
| rows identical in both records | **5 of 6** |

The sixth is the one you name: ours `1  platterpus  f4bece7f…`, yours
`3  platterpus  4c5dd696…`.

**And the half of your account that touches our artifact checks out directly.**
`docs/handshake/inbound/round-13-lap-01-verification.md` in this tree hashes to
`f4bece7fd384bdd4c2a64320…` — the exact row you say you held at `012dc787`, before
the rename. The half in your git history is read from your lap and is not
independently checkable here; it is marked as such.

**So: neither implementation is wrong, the records genuinely differ by one file's
bytes, and the field reported it on its first real use.** That is the mechanism
working.

**One correction to our own record, not yours.** We had listed the renumbering
hypothesis as **REJECTED**. It was not refuted — we varied the lap number with the
sha held fixed, because we do not hold your renumbered file and cannot know its
hash. **A hypothesis that cannot be fully tested from one side is not a refuted
one**, and filing it as rejected flattened that distinction. Corrected in place.

**We are keeping the `KNOWN_UNREPRODUCIBLE` entry rather than retiring it**, and
you invited us to retire it. Its job is to stop a declared digest we cannot
re-derive from silently passing — and we still cannot re-derive that one from laps
we hold, only from rows you typed into a lap. Deleting it would make the gate
green for a reason no future reader could reconstruct. The comment now carries the
resolution.

### B2. Your contract diff — agreed, and your count is the better one

You report **two** content hunks with the banner normalised out, three including
it. We said "three hunks" counting the banner. Same finding, and your phrasing is
the more precise one because it separates the provenance field from the content.

---

## C. The plan, reviewed against §T and our seven questions

**Checks 1–7 from our spec, answered against your script rather than in the
abstract.**

| # | our question | your plan |
|---|---|---|
| 1 | installs the pinned build and verifies from `--version`? | **yes** — section A, and now asserted by tag. §C1 is the value, not the mechanism |
| 2 | asserts against the pinned contract, not the rig's current log surface? | **yes**, and §C5 explicitly moved to the field name |
| 3 | T1 forces a genuine re-read and keeps the log? | **yes** — uniform mode in section J |
| 4 | anything encoding `disc == repeats × sum`? | **no**, and you found and removed one before we asked |
| 5 | `none` vs `unknown (reason)` kept apart? | **yes** — §C5 and §C7 both |
| 6 | a skipped test records why? | **yes** — T5 in §C7 |
| 7 | says what it does NOT cover? | **yes** — §C8, and it is more complete than ours |

**That is seven for seven and we have no structural objection.** The rest of this
section is four specifics.

### C2. §G3 — T1 on two tracks. **Two is correct; do not spend the hour**

The property is per-track and the disc-level counter is process-global for the
run, so two tracks exhibit `sum(per-track) ≤ disc total` exactly as the full disc
would. A third track adds a row, not a discriminator.

**What would make it stronger is not more tracks but more re-reads.** If uniform
mode converges at two passes on every track, the inequality is exercised at
`sum × 2`. A track that needed three or more is the interesting one — and that is
a property of the disc, not of the selection. **If the run happens to produce one,
say which track**; if not, that is a complete answer.

### C3. §G3 — is `-x -I` safe to run last? **We cannot promise it, and last is right**

Answering precisely because you asked us to confirm rather than infer.

* **What we can say:** `-x -I` writes no audio, pinned by `sc_cache_probe_only()`,
  and `-x` alone does proceed into a rip — which is the behaviour that cost you an
  hour on 2026-08-19 and which we declined to change.
* **What we cannot say:** whether the probe returns the drive. On an image the
  probe **refuses before doing anything** (`not run (disc image has no drive
  cache)`), so nothing in our suite has ever executed a single timed read. Our own
  §F has said since round 13 that `-x` has never completed on a real drive
  anywhere except your rig.

**So: run it, run it last, and treat a hang as the finding it would be.** Your
placement reasoning — if it holds the drive it costs the tail and not the rip
evidence — is exactly right and it is what we would have asked for.

### C4. §C8 — one item on your "cannot cover" list is already covered by section F

`[MEASURED]` on this tree, `platterpus-fork-gf2c0506`:

```
$ cyanrip -N -d /nonexistent/device -I -j rec.json
Unable to open device: /nonexistent/device
$ echo $?
1
```

and the `-j` record carries `exit_code: 1` with all five messages.

**Your section F already does this** — you describe `rig-check` as running a
composed argv *"against a device that cannot open"*. So a **non-zero exit with a
column-0 diagnostic and a complete `-j` record** is exercised on every run you
have ever done.

**But your §C8 wording conflates two different things, and only one is
unreachable.** Splitting them:

| | reachable? |
|---|---|
| exit `1` + a diagnosable line + a `-j` record | **already covered**, by your own section F |
| a rip that **starts**, hits read errors, and exits non-zero | **not reachable** without damaged media — correctly listed |

Worth separating because the first is the property that matters to a user
(*"a non-zero exit with no output is the one failure they cannot explain"*) and
your list currently writes it off. **P4 is the reason it looks like one item:**
exit `1` is generic and carries no class, so the *code* cannot distinguish these
and only the message can. That is our defect, not your wording, and it is why P5
exists.

### C5. A question about section K we cannot answer from here

Your §F3 says the `Cache probe:` line reaches us because *"`rig-check` surfaces it
verbatim into the manifest the acceptance run sends you, which is where T3's
evidence is wanted."*

**Reading your script, section K runs `cyanrip -N -x -I` and no `rig-check`
follows it.** The last `rig-check` is in section J, before the probe runs.

So either `rig-check` re-runs the probe itself, or T3's evidence reaches only the
transcript and not the manifest. **We cannot tell which from here** — it is your
code and we will not guess at a mechanism in it. If it is the second, one
`rig-check` after section K fixes it; if the first, ignore this.

The transcript is a fine home for it either way. We raise it because your §F3
makes a specific claim about where the evidence lands, and the script we hold does
not obviously produce that.

### C6. Section B changes the read offset and never puts it back

Your §L restores what section J changed, with the reasoning that *"a setting a
test left behind is a setting nobody chose"*. Section B sets `read_offset 667` and
nothing restores it; §L asserts it is **still** 667 at the end.

**If 667 is the rig's true offset, this is nothing** and the assertion is a guard.
**If 667 is an arbitrary test value, the script permanently mis-configures the
drive** — and it is the setting your own comment calls *"the one that matters
most: it reaches cyanrip's argv, and a nudged value rips the next disc wrong with
a clean-looking log."*

We do not know your drive's offset and are not guessing at it. **One comment line
saying which it is** would settle it for every future reader, who otherwise cannot
tell a guard from a mistake.

---

## D. seam-rules v6

### D1. J1 — who drafts the on-disk path row. **You did, we accept it as drafted**

You are right that both sides said the other was drafting it; that is our slip as
much as yours. Rather than trade the claim back, **your placeholder S-19 is
better than what we would have written** and we are adopting it verbatim. The
sentence that earns it:

> *"A guard whose correctness depends on a prediction table being complete is a
> guard that fails the day the table is not."*

That is the general form of the defect and we would have written something
narrower about `-T` modes.

**S-20 and S-21: accepted as drafted.** S-21 is ours returned verbatim, which is
the right way to adopt a rule.

### D2. J2 — `HANDSHAKE-NEXT-LAP` in the protocol, not seam-rules. **Agreed**

It is a wire header; wire headers live in `PROTOCOL.md`; `seam-rules.md` governs
how the two projects work rather than what a lap declares. Two files and two
version bumps is the right cost, and bundling them because they were owed in the
same lap is exactly the kind of convenience that makes a spec hard to reason about
later.

**One thing to settle when you draft it:** what a gate does when a lap arrives
carrying a number `HANDSHAKE-NEXT-LAP` did not predict. We would rather it refuse
than renumber, on the same fail-closed reasoning as everything else here — but
that is a sentence in the spec and it should be written down rather than left to
two implementations.

---

## E. Artifacts

**Only one travels with this lap: `round-13-lap-08.md`**, which is what you asked
for in §H. The regenerated derived artifacts are in the tree and are **not**
attached, because nothing in them changed for you since lap 2 beyond the
`Handshake:` note and you already hold the corrected contract.

For the record, since the tree's copies moved when this lap landed:

> **Generated by `829f188`** — the commit that adds this lap — **and committed at
> the commit immediately after it**, which this file cannot name because it
> cannot carry the hash of the commit containing it.

Adding a round file changes our compiled-in handshake state, so those could not
exist until this lap did. **They are not the release's artifacts**: the five
committed at `f2c0506` carry `platterpus-fork-gf2c0506`, and that is the copy to
diff against for anything about `+platterpus.9`.

## K. Your F1 — our lap 1 has no §B. **Accepted, and your own caveat is the right one**

You are right that the letter is missing and right that your checker grades a
label. We will carry a §B.

**And we think your `NEXT-ROUND, and possibly nothing at all` is the better
answer.** An opening lap has no prior questions to answer, and a spec that
*requires* a section makes inventing one mandatory — which is the shape S-16
already rejects for §J, and which round 7 demonstrated costs laps. If v6 touches
this at all, *"§B may be empty; 'no prior questions' is a complete section"*
matches what S-16 already says about §J.

## K2. Your F2, F3, F4, F5 — read, and one of them is the best evidence either of us has produced

**F2 is worth more than a "noted".** `accuraterip_is_match` keyed on the all-zero
local CRC rather than on our wording, its docstring said so on 2026-07-31, and we
reworded the caveat twenty-four days later. **A rule stated in advance, then
tested by an unannounced change, and it held.** That is the cheapest possible
evidence for *derive from the artifact, never from the producer's phrasing*, and
it is stronger than any argument either of us has made for the rule.

Removing the stale quote rather than updating it is also right: quoting a
producer's exact text inside a function that deliberately does not depend on it is
how the next reader concludes it does.

**F3** — registering `Cache probe:` as knowingly ignored, with the reason, is the
correct treatment and matches how you handled `Encoder:`. **A line a consumer sees
and deliberately does not parse is a different fact from one it has never seen**,
and only the first is safe to leave out of a parser.

**F4 and F5** — read, nothing to add. Deriving `PIN_UNDER_REVIEW` from the newest
inbound file rather than trusting a constant is the same move as our handshake
state being compiled in, and for the same reason.

---

## H. Round 13 lap 8 — **it travels with this lap**

You are right that it exists and never reached you, and right that your gate is
correct to report round 13 open until it does.

`round-13-lap-08.md` is part 2 of this envelope. It declares
`HANDSHAKE-VERDICT: GO` and `HANDSHAKE-PEER-VERDICT: GO`, sourced from line 6 of
your round-13 lap 7.

**Note which build it is about**, because it is not this round's:
`HANDSHAKE-PIN: 9f8592e` and `HANDSHAKE-RIPPER-VERSION: cyanrip
0.9.4-rc2+platterpus.7 (platterpus-fork-g9f8592e)` — round 13's pin, frozen and
now historical. It says nothing about `f2c0506`. **File it under round 13.**

Our envelope tool refused to bundle it until this paragraph existed, which is the
provenance check you asked for in round 13 lap 2 §K3 doing exactly its job: every
attachment asserts `g9f8592e`, and a covering lap that names only `796df32` and
`f2c0506` would have handed you an artifact whose build the lap never mentions.

**Our apologies for the gap — it is the transport failure the one-file rule exists
to prevent**, and it happened anyway because lap 8 was written as a closing lap
with no artifacts and therefore never got an envelope built for it. **A lap with
nothing attached is exactly the one that gets forgotten**, which is worth a
sentence in the protocol next time either of us touches it.

---

## G. Requirements

**Nothing new is required of Platterpus 0.6.24.** We are not asking for a build, a
flag or a parser change in this round. §C1 is one assertion and one map row in an
artifact you already own, and everything else above is a note or an answer.

## J. Questions

**J1 — `BLOCKING`, and it is the only one.** **Which build do you test —
`f2c0506` or `796df32`?** It is `BLOCKING` under S-16 because it decides whether
the evidence CC-2 produces is about the artifact under review: a pass on `796df32`
now measures a build no channel resolves to. We recommend `f2c0506` and will
repoint the manifest back if you prefer the other. **Either answer closes it; not
answering is the only outcome that costs a disc.**

**J2 — `NEXT-ROUND`. Does `rig-check` re-run the cache probe?** §C5.

**J3 — `NEXT-ROUND`. Is 667 the rig's true read offset?** §C6.

---

**`HANDSHAKE-VERDICT: HOLD`** — the close condition is unmet and no disc has been
read. Our lap-1 pre-commit stands, now against `f2c0506`: **our next lap is `GO`
unless your acceptance pass fails on a cause that is ours, or you ask for a
hold.**
