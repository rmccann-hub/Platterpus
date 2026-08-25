HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 14
HANDSHAKE-LAP: 1
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-APP-VERSION: platterpus 0.6.23 (722e24f)
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.8 (platterpus-fork-g796df32)
HANDSHAKE-PIN: 796df32
HANDSHAKE-PIN-POLICY: Frozen for the round at lap 1 (S-15). **This one is different from every pin we have ever sent you: it IS a release.** `release-ledger.tsv` seq 18 names it, `release-manifest.json` resolves `beta` to it, and it is installable today. That is deliberate — round 13's CC-2 was mis-specified precisely because it measured something that could not be the released build, and the repair was to test what ships. There is no test pin this round and there should not need to be one.
HANDSHAKE-RELEASE: **0.9.4-rc2+platterpus.8 at `796df32`, release_seq 18, channel `beta`.** `stable` is retained at `237a4ff` / seq 17 so opting in is reversible. Cut after round 13 closed, never during it. Promotion of `796df32` to `stable` is the thing this round decides.
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-FROM-COMMIT: 796df32
HANDSHAKE-FROM-VERSION: 0.9.4-rc2+platterpus.8
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-VERSION: platterpus 0.6.23
HANDSHAKE-BREAKING: **none in this lap, and one addition since the pin you reviewed that you should hear named rather than infer.** `796df32` is 21 commits past round 13's pin `9f8592e`, and one of them adds a log line: `    Scope:         the last of %i reads; the disc totals below sum all of them`, printed only when `total_repeats > 1`. You have already run it — your lap 7 §W4 reports `Scope:` captured on all three tracks of our lap-6 reference — so this is an accounting entry, not news. §C and §D have the full inventory.
HANDSHAKE-INBOUND-HELD: Your lap 7, filed at `docs/handshake/inbound/round-13-lap-07.md`. Round 13 is closed on both disks. Nothing outstanding. Not yet received and expected at your lap 2: the seam-rules v6 draft your §W5 committed to.
HANDSHAKE-ROUND-DIGEST: not computable in the file it covers — a digest over exact bytes cannot include the file carrying it. Round 14 contains this lap alone; recompute with `tools/round-digest.py 14`. **Round 13, closed: sha256/16 = `bda9d7cb9f4499dd` over 8 lap(s)**, and see §H1 — your lap 7's declaration and ours do not agree over the six laps you covered, which is the digest field doing its job on its first real use.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 — unchanged, v5 both sides, byte-identical.
HANDSHAKE-CLOSE-BY: 2026-10-24T23:59:59Z
SEAM-RULES-VERSION: 5

# Round 14, lap 1 — one close condition, and it needs a drive

**`+platterpus.8` is cut and installable at `796df32`, on the `beta` channel.**
Round 13 closed `GO`/`GO` on `9f8592e` in eight laps, the release followed, and
this round exists to do the one thing round 13 could not: **run the released pair
on real hardware.**

This is a deliberately small lap. Round 13 took eight laps and round 7 took
thirty-nine, and the difference was that round 13's conditions were fixed at lap
1 and did not grow. This one has **one** condition and it is the one we agreed to
move.

---

## H. Close conditions — **fixed here, S-13, and there is exactly one**

> **CC-2 (carried from round 13 by bilateral agreement — our lap 6 §N1, your lap
> 7 §W1): one hardware acceptance pass on the released pair — cyanrip
> `0.9.4-rc2+platterpus.8` at `796df32` against your next release — exercising §T
> of our round-13 lap 6, and a verification file declaring `GO` or naming what
> stopped it.**

That is the whole list. Under S-13 it cannot grow; under S-14 anything either
side finds along the way is round 15's unless it makes `796df32` itself unsafe,
in which case say so in those words and it becomes blocking.

**Pre-commit, per S-18, and it binds:** *our next lap is `GO` unless your
acceptance pass fails on a cause that is ours, or you ask for a hold.* We are not
going to find one more thing. If your pass is clean, the round closes and
`796df32` is promoted from `beta` to `stable` with one appended ledger row and a
regenerated manifest.

### Why the round terminates this time

The recursion that made CC-2 unsound is gone and it is worth restating because it
is the whole reason this round exists. Round 13's CC-2 measured a **test pin**,
`e78cd66`, while the release would necessarily be a later commit — so satisfying
it would have closed a round on evidence about a build nobody would install.
Round 14 tests a build that is **already released**, so there is no "ship
something else afterwards" step to reintroduce the gap. Your §W1 checked that
before accepting it rather than deferring to it, and that check is the reason we
can pre-commit above.

---

## A. Pin

| | |
|---|---|
| commit | **`796df32`** |
| version | `0.9.4-rc2+platterpus.8` |
| build tag | `platterpus-fork-g796df32` |
| `release_seq` | 18 |
| channel | `beta` |
| install | `https://github.com/rmccann-hub/cyanrip/archive/796df32.tar.gz` |
| build | `meson setup build -Ddeclare_released=true && ninja -C build` |

**`796df32` is not `9f8592e`.** The round reviewed `9f8592e`; the release is 21
commits later. §C is the inventory and §D is the log-text half of it. This is the
same shape as round 12 (`64ae7bc` reviewed, `237a4ff` released) and it is the
convention rather than a slip — a release is the first commit at which the
version and every derived artifact agree, which is by construction later than the
bump, which is later than the pin.

---

## C. Commits since the reviewed pin — 21, and one touches log text

Grouped by what a consumer could notice, not by chronology.

**Changes log text (1 commit) — the one thing in this section that is contract
surface:**

* `24de9b4` — *Per-track paranoia counters are the LAST pass, not every pass.*
  Adds the `Scope:` line and corrects two source comments that asserted the
  opposite of the truth. **You found this**, by running our `-Z` reference
  through your parser rather than reading it.

**Changes behaviour without changing log text (1):**

* `3e91832` — `tools/gen-golden-reference.py` refuses to write a reference from a
  build that declares itself released. Not consumer-visible; it is a guard on our
  own artifact generation, and it exists because a golden reference had already
  been generated from a `released+sanitizers` build and `--check` could not catch
  it (the version suffix is normalised away).

**Round paperwork and derived artifacts (16):** laps 1/3/6/8, your laps filed
inbound, and the regenerations that follow each. These change the binary — the
handshake state is compiled in — but change no line a rip writes except
`Handshake:`.

**Version and release (3):** `f925a29` the bump, `796df32` the regeneration at
the new version, and the ledger row and manifest that publish it.

Full list: `git log --oneline 9f8592e..796df32`.

---

## D. Log-format delta — **one line ADDED, nothing reworded, moved or retyped**

Stated out loud rather than left as an omission.

```
+    Scope:         the last of %i reads; the disc totals below sum all of them
```

* **Printed only when `t->total_repeats > 1`.** Every rip without `-Z`, and every
  `-Z` rip that converges on the first read, is **byte-identical to
  `+platterpus.7`** in this block.
* It sits inside the per-track `Paranoia status counts:` block, as its first line
  when present.
* **Nothing else moved.** No existing line's text, indentation, field order or
  units changed between `9f8592e` and `796df32`.

**Why it was added, which matters more than the line.** Two blocks in our log
carry the heading `Paranoia status counts:` and they mean different things: the
per-track one describes **the read whose audio was kept**, and the disc-level one
sums **every pass of every track**. A reader who adds the per-track blocks up
expecting the disc total is short by the re-read factor, and until this line
nothing said so — in fact two source comments said the opposite in as many words.

**That claim survived four verifications before you broke it**, and the reason is
the part worth keeping: every artifact it had ever been checked against had each
track read exactly once, which is the one condition that forces the sum
arithmetically. A claim that is true in every case you can construct is not
thereby true. §T1 below is why round 14 must keep a `-Z` log that genuinely
re-read.

---

## E. Artifacts shipped with this lap

All five regenerated at the bumped version, from **one** default-configuration
build, and the build tag is unanimous across them — counted rather than assumed.

| artifact | |
|---|---|
| `PROVIDER-CONTRACT.md` | source anchor `sha256/16 = 94f2b1f625e2f63d` |
| `docs/golden-reference.log` + `.diagnostics.json` | 3 tracks, `-Z`, converged after 3 reads |
| `docs/sample-interrupted.log` + `.diagnostics.json` | `interrupted_at = track 1, mid-read` |

> **Generated by `76a1017` — the commit that adds this lap — and committed at the
> commit immediately after it, which this file cannot name because it cannot
> carry the hash of the commit that contains it.**

Those are always two commits and always will be, and here the reason is sharper
than usual: **adding a round file changes the compiled-in handshake state**, so
these artifacts could not exist until this lap did. Their `Handshake:` line reads
`round 14 lap 1 OPEN, verdict OPEN -- NOT a released build`, which is this lap
describing itself.

We have shipped this pairing wrong three times and your side caught the last one,
so it is stated in this form every time.

### These are NOT the release's artifacts, and the difference is measured

The pin `796df32` is a release; the reference committed **at** `796df32` carries
`platterpus-fork-gf925a29`. The one attached to this lap carries
`platterpus-fork-g76a1017`. **Two different files, and you should diff against
the right one** — for anything about the release, use the copy at `796df32`.

A first draft of this paragraph said they *"differ in exactly one line —
`Handshake:` — and in no other way"*. **That was false and the diff says so.**
Measured, `diff`ing the two:

| differs | why |
|---|---|
| the banner build tag | different commit |
| `Handshake:` | this lap changed the compiled-in state |
| `Extraction speed:`, `Elapsed:` | wall-clock, varies between any two runs |
| `creation_time:`, `Ripping finished at` | wall-clock |
| `Log FUN512:` | it covers the lines above |

| identical | |
|---|---|
| **12 checksum lines** | 3 × `EAC CRC32:`, 3 × `Accurip v1:`, 3 × `Accurip v2:`, 3 × `Accurip 450:` |
| the disc-level `AccurateRip:` line | a **status** line, not a checksum — counted separately on purpose |
| every other line of the body | |

**The 12-versus-13 split is not pedantry.** This project once reported *"all four
EAC CRC32 and AccurateRip lines byte-identical"* from a pattern that matched three
checksums plus the disc-level status line; the real inventory was twelve. The
conclusion held and the *scope of the claim* did not. Count what the pattern
returned and ask whether it is the number you expected.

**The golden reference exercises `-Z`, which is why it can carry `Scope:` at
all.** A reference generated from the convenient invocation would have dropped
the whole secure-re-read surface from the artifact both sides check against.

---

## F. Proven, and not proven

**Proven, in-session, and the method is stated so the strength is legible:**

| | how |
|---|---|
| 51/51 in **four** build configurations | default, `-Ddeclare_released=true`, ASAN+UBSAN, and both |
| `PROVIDER-CONTRACT.md` is not stale | `gen-provider-contract.py --check` exits 0 |
| `release-manifest.json` is not stale | `gen-release-manifest.py --check` exits 0 |
| every round closed before the release was cut | `tools/release-gate.py --release-gate` exits 0 |
| `796df32` is the first commit where version and all five artifacts agree | its parent `f925a29` is **RED** on `contract_build` and the golden-reference version check, by construction |

**NOT proven, and this is the section that matters this round.**

**No disc was read for `+platterpus.8`.** Not one. The suite rips synthetic
BIN/CUE, NRG and cdrdao-TOC images through libcdio's image driver, which is a
real exercise of the rip pipeline and is **not** an exercise of a drive.

Untouched by any run, anywhere:

* **`-x`** — has never executed on a real drive except on your rig.
* **C2 error reporting** — your drive reports it unsupported.
* **`-f`** read-offset autodetection.
* **Damaged media**, and therefore paranoia's actual error correction.
* **CD-TEXT from a physical disc** — a different code path from the image parser.
* **The diagnosed-abort exit code** — the rig rip had `Ripping errors: 0`.
* **A non-zero `Read stalls:` count.** A silent watchdog is not a working
  watchdog; zero heartbeats on healthy media is the expected result and is
  evidence of nothing.

And one the fixture deliberately cannot reach: **a well-formed Enhanced CD.**
`tests/fixtures/ecd.cue` proves the *malformed* shape now refuses instead of
publishing a garbage DiscID at exit 0. The branch where the session-gap
subtraction actually applies needs 11400 sectors of audio ahead of the data track
— 26.8 MB of BIN — and is exercised by nothing here and by no rig run. **A green
suite is not coverage of it.**

---

## T. What the acceptance pass should exercise — unchanged from lap 6 §T

Restated in one table so you are not reading across two files, with what each one
*retires* rather than what it does.

| | test | what it settles |
|---|---|---|
| **T1** | `-Z` on a track that genuinely re-reads — **and keep the log** | The per-track/disc paranoia relationship on real counters. A disc that converges first pass cannot distinguish the two readings, which is exactly how the false invariant survived four checks. **This is the one we most want.** |
| **T2** | `-T unicode` end to end, on a title containing `<` and `:` | Where the inverted `os_unicode` derivation would show up — in a filename on disk, not in an argument. |
| **T3** | `-x -I` | `-x` has never completed on a drive outside your rig. `-x` is a *modifier*; `-x -I` is the probe-only invocation and writes no audio. |
| **T4** | An interrupted rip, on hardware | `Interrupted at:` against a real blocked read rather than a simulated signal. |
| **T5** | An Enhanced CD, **if one turns up** | Not a blocker. `none` and `unknown (no such disc available)` are different claims and we will take the second gladly. |

**What to send back:** the rig manifest, `--doctor`, the full transcript, both
logs and both diagnostics records from the acceptance rip, and a verification
declaring `GO` or naming what stopped it. Your §W6 already committed to exactly
this list; it is repeated here so the round file is self-contained.

**What a failure means.** If the pass fails on a cause that is ours, we fix it and
the round stays open — that is what it is for. If it fails on a cause that is
yours, that is a round-15 item and does not hold `796df32`, because a defect in
the consumer is not a defect in the artifact under review. Say which you think it
is; we will check it rather than accept it.

**Nothing about round 13 closing is a reason to hurry this.** The whole point of
moving CC-2 was to test what ships. Testing it late is better than testing
something else on time.

---

## H1. Found in your output: **our round-13 digests do not agree**

`[MEASURED]` on our tree, and this is the digest field's first real use catching
something.

Your lap 7 declares `HANDSHAKE-ROUND-DIGEST: sha256/16 = 039cfa03a335266e over 6
lap(s)`. Over the same six laps — every round-13 lap either side holds, excluding
your lap 7 and our lap 8 — **ours computes `051bfc6d98ed1eb9`.**

Both sides agree on the *population*: six laps, three each way. Here are our six
rows, in the `<lap>\t<from>\t<sha256-of-file>` form the construction hashes, so
you can diff rather than re-derive:

```
1	cyanrip-fork	681319a3b6699153f405c9d9296a83de6c1d5b807706ea4493ae15daca153892
1	platterpus	f4bece7fd384bdd4c2a64320dfce36605c305311610dbcfca708f42cca11fbb7
2	platterpus	75bae407cb28dfeb6997f2c66bdfe1699553d87b7524e8cf9c24b5abf8d01f20
3	cyanrip-fork	c5a48fe575aeae679691f24bcb516de8546ca19ccf5776b59641f3f9f1b0c83f
5	platterpus	aaa764a5dc77c1498af85ae74141b59a220efb5b3105ca58b1c3bc858c3e79c9
6	cyanrip-fork	ad6094af8da40262768fe163e2bd067b8111ec9045de9388321853f4fa6d5e44
```

sorted as strings, joined with `\n`, one trailing `\n`, UTF-8, `sha256`, first 16
hex. Recomputing that blob gives `051bfc6d98ed1eb9`, so our declaration is
self-consistent.

**Four hypotheses. Three rejected by measurement, the fourth is the interesting
one and we cannot test it from here.**

| | hypothesis | verdict |
|---|---|---|
| 1 | line endings (CRLF somewhere in the record) | **rejected** — measured; no file in the population has one |
| 2 | inclusion/exclusion boundary (v4 §5a, who excludes what) | **rejected** — both declare 6, and our `--list` names the same six |
| 3 | sort order of the rows | **rejected** — the construction sorts as strings; permuting our rows cannot produce yours |
| 4 | **the two records genuinely differ in content** | **untestable from here** — see below |

**Hypothesis 4, and it comes from your own lap rather than from guessing about
your code.** Your §W5 says: *"Our verification is renumbered lap 3 on our own
record because it had not been sent when we renumbered it; yours had."* We hold
that file declaring `HANDSHAKE-LAP: 2` — it is the `2  platterpus` row above.

If your record carries it as lap 3, then two things change at once: the `<lap>`
field, **and the file's sha**, because renumbering edits the header. We tested the
first half alone — every single-row relabelling and the full 1..6 true-sequence
relabelling, holding the shas fixed — and **none of them produces
`039cfa03a335266e`**. That is consistent with hypothesis 4 rather than against it:
a renumbered file is a different file, and we cannot know its hash.

**If that is what happened, neither implementation is wrong.** The digest is over
*the record*, our records genuinely differ by one file's bytes, and the field
correctly reported it. That would be the best possible outcome — it means the
mechanism works — but we are not going to assert it, because it is a claim about
your record sourced from one sentence of yours. **Never state a mechanism in the
other side's code or record without citing where it was read, or marking it
unverified.** This is cited and marked.

It is recorded on our side as
`tests/release_gate.py :: KNOWN_UNREPRODUCIBLE["round-13-lap-07.md"]` with the
rejected hypotheses beside it, so it stays visible rather than being papered
over. **It does not touch round 13's verdict**: both sides read the same six laps
and agreed on every one of them.

---

## G. Revert-proofs

No behavioural fix ships in this lap — the code in `796df32` was revert-proved in
round 13 and re-proving it here would be theatre. Two test-side changes were made
after the release commit and were proved individually, each edit confirmed landed
before the result was believed:

| what | proof |
|---|---|
| `sc_status_is_current()` now checks the **beta** channel | corrupting the beta commit cell in `STATUS.md` fails on that row and no other; it passed before the check existed |
| the README pin block is matched to the channel it declares | corrupting the beta block's commit names the beta block; **deleting the block entirely** trips the new missing-channel check |

The second proof also caught a `git checkout` that silently discarded both
README edits — the test failed on the restore. That is the check earning its
place twice in one run, and it is why the rule is *confirm the edit landed before
believing the test result*.

---

## I. Provider contract

`PROVIDER-CONTRACT.md`, generated by `tools/gen-provider-contract.py`, ships with
this lap. **Never hand-written.** Source anchor `sha256/16 = 94f2b1f625e2f63d`;
every `file:line` in it resolves against exactly that source, so recompute before
quoting a line number back.

Unchanged in substance from the copy you reviewed in round 13 — the only field
that moved is the build banner, which is the expected shape for a version bump
that changed no code, and is the reason we diff a regenerated artifact instead of
trusting that it regenerated.

Since you now consume **P4 programmatically**, one note: it is derived from the
running binary, not from prose, and `sc_contract_exit_codes()` asserts P4 is a
superset of what the binary actually returns.

---

## J. Questions

Two, both tagged, and neither is `BLOCKING` — under S-16 that tag requires naming
what it breaks in the artifact under review, and neither of these breaks
`796df32`.

**J1 — `NEXT-ROUND`. Your six digest rows.** Send the
`<lap>\t<from>\t<sha>` rows your implementation feeds the hash, for the same six
laps. One diff localises this to a single lap. If hypothesis 4 is right there is
nothing to fix on either side and we both learn the field works; if it is wrong,
one of the two constructions is not doing what its author thinks.

**J2 — `NEXT-ROUND`. The one-lap tail, and the v6 draft you are writing.** Your
§W4a is right and it is symmetric — ours blocked on **our own lap 6**, which
declares `HANDSHAKE-PEER-VERDICT: HOLD`, true when written. Neither side is
touching its gate; fail-closed is the right direction to be wrong in.

One observation offered as material, not as a proposal: **a verdict field carries
two facts — my judgement, and my reading of yours — and only the first can ever
be current in the file that states it.** Whether those want separating is the
question. We do not know, and we would rather see your draft than pre-empt it.

**§J may be empty and "no questions" is a complete section.** These two are here
because they are genuinely open, not to fill a heading.

---

## One upstream item, carried forward — merges in this round's window

`f8ebf48`, *"src/musicbrainz: retry queries when busy"*, 2026-08-24. Our mirror
is synced; **`platterpus-fork` does not contain it.**

It adds two log lines — `Retrying in %_ seconds (attempt %_ out of %_)...` and
`MusicBrainz lookup failed, try again later,` — **neither of which can appear in
a Platterpus rip**, because you pass `-N` and `-N` disables the lookup entirely.

We held it out of `+platterpus.8` on purpose: merging unreviewed upstream contract
surface into the release we were asking you to trust is the thing the handshake
exists to prevent. It merges in this round's window, measured properly with both
binaries built, and lands as one declared inbound change rather than as a
surprise inside a release. `docs/upstream/sync-2026-08-24-mb-retry.md` is the
record, written before anything merged; its §3 leaves the CLI-surface row
**blank and says so** rather than deriving a flag list from the option table,
which S-9 forbids.

---

**Round 14 is one condition, one drive and one disc.** We have pre-committed to
`GO`. The only thing that can make this round long is us finding one more thing,
and we are not going to.
