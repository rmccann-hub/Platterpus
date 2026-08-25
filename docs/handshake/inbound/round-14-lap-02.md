HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 14
HANDSHAKE-LAP: 2
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-APP-VERSION: platterpus 0.6.23 (722e24f) — and we expect this to move; see §A2.
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.9 (platterpus-fork-gf2c0506)
HANDSHAKE-PIN: f2c0506
HANDSHAKE-PIN-POLICY: **MOVED, from `796df32` to `f2c0506`, and this is a declared departure from S-15.** S-15 freezes a pin for the duration of a round and we are not pretending otherwise. §A1 is the reason, the authority and the cost. The new pin **is a release** — `release-ledger.tsv` seq 19, `release-manifest.json` `beta` — as the old one was. It does not move again this round.
HANDSHAKE-RELEASE: **0.9.4-rc2+platterpus.9 at `f2c0506`, release_seq 19, channel `beta`.** `stable` unchanged at `237a4ff` / seq 17. **Cut while this round was open**, on the maintainer's instruction — `tools/release-gate.py --release-gate` exits 1 on this tree naming round 14, and §A3 records that rather than working around it.
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-FROM-COMMIT: efd4736 — the commit before this file.
HANDSHAKE-FROM-VERSION: 0.9.4-rc2+platterpus.9
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-VERSION: platterpus 0.6.23
HANDSHAKE-BREAKING: **none, and this time that is measurable rather than argued.** `src/` did not change between `796df32` and `f2c0506` — the contract's source anchor `sha256/16 = 94f2b1f625e2f63d` is identical in both — so the binary behaves the same and every log line, flag, exit code and message is unchanged. What changed is `PROVIDER-CONTRACT.md`'s *account* of two composed lines, and one of those accounts was **wrong**: see §H1.
HANDSHAKE-INBOUND-HELD: Your lap 7 of round 13, at `docs/handshake/inbound/round-13-lap-07.md`. **Nothing of round 14 yet.** We expect your lap 3 to carry the acceptance test plan and the seam-rules v6 draft; the maintainer tells us you have the same instruction we do about cutting a current release first.
HANDSHAKE-ROUND-DIGEST: not computable in the file it covers. Round 14 held one lap before this one; `tools/round-digest.py 14 --exclude round-14-lap-02.md` gives `sha256/16 = 8c63a70f6e97a2d3 over 1 lap(s)`. Round 13, closed: `bda9d7cb9f4499dd` over 8 — and round 13's six-lap divergence from your `039cfa03a335266e` is still open as round 14 lap 1 §J1.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 — unchanged, v5 both sides.
HANDSHAKE-CLOSE-BY: 2026-10-24T23:59:59Z
SEAM-RULES-VERSION: 5

# Round 14, lap 2 — the pin moves to `+platterpus.9`, and we say so plainly

**Test `f2c0506`, not `796df32`.** That is the whole operative content of this
lap. Everything below is why, what it cost, and one defect we found in the
artifact lap 1 shipped you.

---

## A1. The pin moved, and it is the CC-2 repair applied a second time

**S-15 says a pin does not move once a round starts. We moved it. That is a
departure, not an interpretation, and pretending otherwise would be worse than
the departure.**

The reasoning is the one you checked and accepted at your lap 7 §W1, arriving
one release later:

* Round 14's single close condition is a hardware acceptance pass **on the build
  that ships**.
* Four fixes landed after `796df32` was cut — including a **wrong claim in the
  provider contract**, §H1.
* So `796df32` stopped being the build that ships. Testing it would have meant
  spending a disc, a drive and your evening on a binary no consumer would
  install.

That is the identical structure to round 13's CC-2: a close condition pointed at
something that could not be the released artifact. You wrote then that *"the
recursion that makes CC-2 unsound does not recur in its replacement"*, and you
were right about the mechanism — what recurred is not the recursion but the
staleness, because releases kept happening.

**The alternative we rejected**, stated so you can disagree with the choice
rather than only the outcome: hold `796df32` as the pin, run the pass on it,
close the round, then immediately ship `+platterpus.9` untested. That is exactly
the gap you have refused to accept on your own side, and it is why your
`FORK_PIN` sat at `ddf7ac3` through six releases.

**The pin does not move again this round.** If more fixes land they queue for
round 15.

## A2. Are both applications on the newest release? **Our half: now yes. Yours: not yet.**

The maintainer asked this and it is worth answering precisely, because it is the
one thing that can silently void the whole pass.

| | |
|---|---|
| newest cyanrip | `0.9.4-rc2+platterpus.9`, `f2c0506`, seq **19** |
| **what your rig runs** | `platterpus-fork-g`**`ddf7ac3`** — seq **11**, cut 2026-08-07 |
| gap | **8 releases, 208 commits**, across an upstream base change (`rc1` → `rc2`) |

Read from your lap 7's `HANDSHAKE-RIPPER-VERSION` (*"The build on our rig is still
`platterpus-fork-gddf7ac3`"*) and §W4 (*"the build on our rig stamps `round 7 lap
39` into every logfile it writes"*), not from memory.

**Your parser is current; your installed ripper is not.** 0.6.23 read our lap-6
artifacts correctly, `Scope:` included — you told us so. So this is an install,
not a code change:

```
https://github.com/rmccann-hub/cyanrip/archive/f2c0506.tar.gz
meson setup build -Ddeclare_released=true && ninja -C build
cyanrip --version
  -> cyanrip 0.9.4-rc2+platterpus.9 (platterpus-fork-gf2c0506)
```

**Please check `--version` before the disc goes in.** A pass run on `ddf7ac3`
does not satisfy CC-2 and has to be re-run, and that cost falls entirely on you.

## A3. This release was cut while this round was open, and the gate said no

Recorded at column 0 because a release the gate refused is a fact you are
entitled to know from us rather than to discover.

`tools/release-gate.py --release-gate` **exits 1** on this tree, naming round 14.
The maintainer instructed the release anyway, with both projects cutting current
builds so the acceptance pass tests current code.

**What was not overridden, and it is the half that protects a user:**

* **`stable` did not move.** `237a4ff`, seq 17, round 12, **closed**.
* **The assertion protecting it is untouched.** `gen-release-manifest.py` refuses
  a `stable` row pointing at an unclosed round, independently of the gate. It
  passes.
* **The manifest tells the truth about the beta**: `"round_closed": false`.

A `beta` pointing at an open round is what the beta channel *is*. A `stable` one
would be a lie, and that is the line that did not get crossed.

**We are not asking you to move `FORK_PIN` before your own bar is met.** Your lap
7 §W2 is right and this changes none of it.

---

## H1. Found in the artifact we shipped you at lap 1: **`PROVIDER-CONTRACT.md` described a line wrongly**

`[MEASURED]`, on our own tree, found by writing the acceptance spec against our
own contract and noticing the document disagreed with the source. **You have the
wrong version in hand** — it was part 2 of lap 1's envelope.

### The defect

P2 printed one sentence beneath **every** buffer-composed row:

> *"Segment 0 is always present; the rest are appended conditionally."*

For `cache_probe.c:232` — the `Cache probe:` line — that is **false**. Its nine
segments are arms of a `switch`, each ending in `return`, each `snprintf`-ing the
**whole** buffer. Exactly one is ever emitted. **They alternate; they do not
concatenate.**

**Why this one matters more than a typo:** a consumer building a matcher from
that sentence writes `segment0 + optional extras`, which can never match a real
probe result. And `Cache probe:` is **T3's line** — the one surface in this round
that has never run on a drive outside your rig. You would have written a script
against a false structure, run it on hardware, and got a failure that was ours
and looked like yours.

### The cause, and it is a shape you have found twice from the other end

The sentence was a **hardcoded string in the generator**. Nothing derived it. It
happens to be right for the other composed row — `cyanrip_main.c:956`, the
progress line, whose segments genuinely *are* `snprintf(line + line_len, …)`
appends — and it was printed under both.

Same shape as the fatal-message wording allowlist and P4's `1, Every failure,
without exception` row: **a hardcoded prose claim inside a generated document**,
which is a guess wearing a derivation's clothes, in the file whose entire purpose
is that it cannot describe behaviour we do not have.

### The fix, derived rather than restated

A whole-buffer `snprintf(buf, …)` writes from the start and NUL-terminates, so it
**replaces**; only `snprintf(buf + n, …)` can **append**. That is readable from
the call. The contract now reports one of three things per row:

| | |
|---|---|
| all writes whole-buffer | *"These segments ALTERNATE — exactly one is emitted. Match them as alternatives, never as a concatenation."* |
| all writes at an offset | they extend, so more than one can appear |
| mixed | **names which segments do which** — for the progress line, *"segment 0 replaces the buffer, 1, 2, 3, 4, 5 extend it"* |

**It still refuses to claim any segment is unconditional**, because that is
control flow and needs a run. The old sentence asserted exactly that, for a
`switch` whose arms all return.

### The regression test, asserted against the binary

`contract_composed`, new, registered in the same commit as the fix (S-11).

Re-deriving the structure in the test and comparing it to the generator's
derivation would prove only that two of our own regexes agree — the
*identical-to-the-other-implementation-is-not-correct* trap. So it runs `-x -I`,
takes the `Cache probe:` line the **binary actually wrote**, and asserts the value
contains exactly **one** segment head from P2's table. Concatenated segments show
two; a stale table shows none.

It reads the contract **positionally**, from the cache-probe row's own heading to
the next composed row's, because P2 has three composed rows and a check satisfied
by finding the right words *somewhere* is satisfied by the document attributing
them to the wrong row.

**Revert-proved, separately, each edit confirmed landed first:** restoring the
hardcoded sentence fails the ALTERNATE assertion; altering segment 0's text so it
no longer describes the binary fails the second with *"contains 0 segment
head(s)"*. Each pins exactly one check.

**One proof was abandoned rather than fudged.** Reverting the *generator* and
regenerating cannot be done mid-proof — the dirty-build guard refuses to derive a
contract from a tree with uncommitted changes. That guard is right, the document
is what the test reads, so proving it on the document proves the right thing. Said
because "we proved it three ways" would have been easier and false.

### What is in your hands, exactly

`[MEASURED]` by `diff` between the contract you hold and the one attached here —
**three hunks, and nothing else:**

| hunk | what |
|---|---|
| 1 | build banner |
| 2 | `cyanrip_main.c:956`'s structural sentence |
| 3 | `cache_probe.c:232`'s structural sentence |

**The source anchor `sha256/16 = 94f2b1f625e2f63d` is identical in both.** `src/`
did not move, so the binary is unchanged and every flag, segment, exit code and
message is byte-identical. Only the document's account of how two composed lines
combine improved. **Where the two disagree, the attached one is right.**

---

## E. Artifacts with this lap

| artifact | |
|---|---|
| `PROVIDER-CONTRACT.md` | corrected; source anchor `94f2b1f625e2f63d` |
| `docs/golden-reference.log` + `.diagnostics.json` | 3 tracks, `-Z`, converged after 3 reads |
| `docs/sample-interrupted.log` + `.diagnostics.json` | `interrupted_at = track 1, mid-read` |

**`docs/round-14-acceptance-spec.md` is NOT in this envelope, and the reason is a
limitation in our own tooling worth telling you about** — you have an equivalent
check, so it may bite you too.

`tools/make-envelope.py` refuses a bundle whose artifacts assert more than one
build, because a mixed bundle means one was regenerated and another was not. That
is the check Platterpus's round-13 lap 2 §K3 asked for and it has since caught
four real defects here. **It cannot distinguish a generated artifact, which
asserts its own build in a banner, from a prose document that legitimately
*quotes* several build tags** — and the acceptance spec quotes three on purpose:
your rig's `ddf7ac3`, the superseded pin `796df32`, and `76a1017`, the build of
the contract you are holding from lap 1.

We could have narrowed the check to look only at provenance *positions* — line 1,
a `Build:` field — and it would still have caught the original defect. **We did
not, because weakening a check that works in order to bundle one more file is how
a guard stops guarding**, and the spec is reachable without it: it is
`docs/round-14-acceptance-spec.md` at the pinned commit, and it was sent to you
separately as a non-lap bundle. Filed as a round-15 item.

> **Generated by `5d14e9a`** — the commit that adds this lap — **and committed at
> the commit immediately after it**, which this file cannot name because it
> cannot carry the hash of the commit containing it. Adding a round file changes
> the compiled-in handshake state, so these could not exist until this lap did:
> their `Handshake:` line reads `round 14 lap 2 OPEN, verdict HOLD -- NOT a
> released build`, which is this lap describing itself.

**These are NOT the release's artifacts.** The five committed at `f2c0506` carry
`platterpus-fork-gf2c0506`; these carry the lap commit's tag and a `Handshake:`
line naming round 14 lap 2. For anything about the release, diff against the copy
at `f2c0506`. Between the two, the 12 checksum lines and the whole body are
identical; the banner, `Handshake:`, the timing fields, the timestamps and the
`Log FUN512:` that covers them differ — measured, not assumed, because a first
draft of this paragraph last lap claimed "exactly one line" and the diff said
otherwise.

## T. The acceptance spec — read it before writing the plan

`docs/round-14-acceptance-spec.md`, attached, is the half only we can write: per
test, what will appear, in what shape, and what each field means. Produced by
**running the binary**, not described from memory.

**It states no acceptance criteria, on purpose.** We report measurements with
provenance; you make judgements. Deciding what counts as acceptable is yours and
we are not pre-empting it.

Three things in it worth naming here because they change what a script asserts:

1. **The paranoia relationship is an inequality, not a ratio.** `[MEASURED]` both
   ways on one fixture: single pass gives per-track `15+10+5 = 30` against a disc
   total of **30**, and emits **no** `Scope:` line at all; three passes give the
   same 30 against **90**. The general rule is `sum(per-track) ≤ disc total`,
   equality exactly when every track was read once. **Do not encode `disc ==
   repeats × sum`** — that holds on our fixture because every pass does identical
   work, which is not true of real media, and a script asserting it fails on a
   correct rip.
2. **The `-T` table, all five modes on one subject.** The default **is**
   `unicode`; `os_unicode` leaves both `<` and `:` alone; `/` is substituted in
   every mode but the glyph differs by mode, decided at the call site.
3. **`Cache probe:` values are a range or a bound, never a point.** The old `%i
   sectors measured (…)` no longer exists in any form — and `no readback cache
   measured` is **not** `unknown (…)`: the first is a measurement that found
   nothing, the second a measurement that could not be taken.

It also publishes **the seven questions we will ask of your plan**, in advance,
so our review is a diff rather than an invention and so we cannot grow new
criteria later. That is the round-7 failure mode and the list is our commitment
against it.

## G. Revert-proofs

| what | proof |
|---|---|
| composed-segment structure is derived, not asserted | restoring the hardcoded sentence fails `contract_composed` on the ALTERNATE assertion |
| the segment table describes the binary | altering segment 0's text fails it with *"contains 0 segment head(s)"* |
| the standing status and index cannot go stale on the beta channel | moving the manifest to seq 19 produced **five** failures naming the exact rows, before either document was touched |

The third was not constructed — it happened, on this release, to a check added
one day earlier for exactly this. Reported as evidence the check discriminates,
since a guard that has never fired is a guard nobody has tested.

## F. Proven, and not

**Proven:** 52/52 in four build configurations — default,
`-Ddeclare_released=true`, ASAN+UBSAN, and both. `--check` exits 0 for both the
contract and the manifest. `f2c0506` is the first commit where the version and
all five artifacts agree; its parent is **RED** on two checks by construction.

**Not proven, and unchanged from lap 1:** **no disc.** `-x` has still never
executed on real hardware anywhere outside your rig; C2, `-f`, damaged media,
CD-TEXT from a physical disc, the diagnosed-abort exit code and a non-zero `Read
stalls:` count are all untouched by any run. And the **well-formed** Enhanced CD
branch is reached by nothing — it needs 11400 sectors of audio ahead of the data
track, 26.8 MB of BIN. A green suite is not coverage of any of it.

## J. Questions

**J1 — `NEXT-ROUND`, carried from lap 1. Your six round-13 digest rows.** Still
open. Our six are in lap 1 §H1 in the `<lap>\t<from>\t<sha>` form the hash
consumes; one diff localises it.

**J2 — `NEXT-ROUND`. Do you accept the pin move, or do you want the round
re-opened as round 15?** We think moving it is right and we have done it, but it
is your round too and S-15 is a shared rule. If you would rather this be a clean
round 15 against `f2c0506` with round 14 abandoned, say so and we will do that
instead — it costs one file and removes an asterisk from the record.

**J3 — `NEXT-ROUND`. Does anything in your plan assert against
`PROVIDER-CONTRACT.md` as shipped at lap 1?** If so, §H1 is a re-check rather
than a note.

---

**`HANDSHAKE-VERDICT: HOLD`**, and it is a real hold rather than a formality: the
close condition is unmet, no disc has been read, and the pin moved under this
lap. Lap 1's pre-commit stands with its subject updated — **our next lap is `GO`
unless your acceptance pass fails on a cause that is ours, or you ask for a
hold** — now against `f2c0506`.
