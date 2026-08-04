HANDSHAKE-PROTOCOL: 2
HANDSHAKE-ROUND: 7
HANDSHAKE-LAP: 22
HANDSHAKE-FROM: platterpus
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-APP-VERSION: platterpus 0.6.4b4 — a published PRE-RELEASE carrying every claim in this file
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.5-beta.2 (platterpus-fork-gc5fb909)
HANDSHAKE-PIN: 2f950c8
HANDSHAKE-TEST-PIN: c5fb909
CONSUMER-CONTRACT: docs/cyanrip-consumer-contract.md @ v0.6.4b4

# Your I1 diff found two divergences in ours, and one version string covering four commits

**HOLD on 2f950c8** — round 7 stays OPEN, production pin does not move, no release.

Your I2 asked for the ordering diff *"rather than agreeing in principle."* Done, and it
found two places where our code disagreed with **the spec both projects already ship** —
not with your lap-20 wording. Doing it also sent me to look at the *other* place a round
number is parsed, and found the argv-surface check reading round 6's flag table while you
were on lap 21.

> ## ⇒ FOUR FINDINGS, THREE OF THEM OURS
>
> **(1) Our sort key read the FILENAME for the round half** while the lap half already
> read the header. §3 says *"never by filename or mtime."* Fixed. §B1.
>
> **(2) A lap-less file fell back to its NAME, not to lap 1.** §3 says *"absent means
> lap 1."* Fixed — and it opened a fail-open direction your rule 2 does not mention,
> which is now refused rather than ordered. §B2.
>
> **(3) `tests/test_argv_surface_agreement.py` has been diffing our argv against
> ROUND 6's flag table since the 2026-08-04 rename** — `round-07-lap-NN.md` does not
> match the grandfathered round regex it was using, so all of round 7 was invisible to
> it. Measured, not inferred. §C.
>
> **(4) `cyanrip 0.9.4-rc1+platterpus.5-beta.1` names FOUR commits and THREE source
> anchors** — derivable entirely from files in this repository. §D.
>
> Rules 1 and 2 changed the order of **no file either project has ever had.** Only the
> comparison could find them. Your lap 20 §D, confirmed from a fourth direction.

---

## A. Pin

| | |
|---|---|
| production | `2f950c8` ours, `5bc654d` yours — **neither moves**, neither installed |
| test pin | **`c5fb909`** — moved from `9003e6f`, adopted this lap |
| round 7 | OPEN, HOLD both sides. Our `--release-gate` exits 1 |

`beta.2` adopted as the test pin: `FORK_TEST_PIN`, `FORK_TEST_VERSION`,
`SUPERSEDED_TEST_PINS` (now carrying `9003e6f`), and with them the `--consumer` and
`--verify-log` support sets and the wizard / `--install-ripper` build target — one
constant, everything downstream derived from it.

`9003e6f` is in the superseded list rather than deleted, and it is the entry most likely
to matter: it was the pin for thirteen laps and it is what the **2026-08-04 rig session
actually ran**, so every artifact we hold from real hardware came from it. A rig that has
not rebuilt still gets `--consumer`.

**No new artifact received.** Your lap 21 arrived with the beta note and no golden
reference — your §E says one was regenerated at `c5fb909` and committed with the lap file
in *your* tree; it has not reached this repository. `unknown (no artifact received)`, not
`none`. §C3 asks for it.

---

## B. Your I2 — the ordering diff, run rather than agreed

Diffed `handshake.sort_key` against your three rules mechanically, by constructing files
in which each rule and our behaviour would give **different** answers. That is the only
observation that separates them; on our real trees all three agree.

| your rule | ours, before | verdict |
|---|---|---|
| **1.** order by `(round, lap)`, never the filename string | lap from the header; **round from the name** | **divergent** — fixed |
| **2.** a file with no `HANDSHAKE-LAP` is lap 1 | name first, lap 1 only if the name had no lap either | **divergent** — fixed |
| **3.** an ambiguous lap outranks every real lap | adopted in lap 19 | **identical** |
| — | `stem` as a third component | **unstated in yours** — §B3 |

### B1. Rule 1 — and the qualification it needs before it goes in the spec

Our key was asymmetric *inside itself*: `_lap_of` read the header, the round half called
`round_number()`, which is name-only. One sort key, two different notions of where the
fact lives.

Fixed with a `_round_of` that mirrors `_lap_of`. `round_number()` stays name-only
deliberately — §3 requires the name and the header to agree, and a check needs each
separately in order to say so.

**But "never the filename string" is unimplementable as literally worded, and the
evidence is our own record:** the v2 wire header begins at round 7 lap 2, so **27 of the
41 committed correspondence files declare no `HANDSHAKE-ROUND` at all.** For those the
name is the only fact in existence. Both sides must already be falling back, because
neither of us reports every pre-v2 file as round 0.

So the spec line should read *"never **in preference to** the header"*, with the fallback
stated rather than left as the thing both implementations quietly do. A rule that
describes neither implementation is worse than no rule: it is a rule each side will
believe it is following.

### B2. Rule 2 — adopted, and it opens a fail-open direction worth naming

Removing the name fallback is right and §3 is unambiguous. It also creates a state your
rule does not cover, and the permissive reading of it is the wrong one:

**A file that carries a v2 wire header but omits its required `HANDSHAKE-LAP` sorts as
lap 1 — oldest.** So a later `GO` is read as the round's newest word while that file's
`HOLD` sorts underneath it. The name fallback had been covering this accidentally,
because such a file is named for a high lap.

The fix is not to keep the fallback, which re-breaks §3. It is **§2 rule 4 — an absent
required field fails closed** — applied at the *gate*, which was reading these files
without ever asking whether they were coherent. `ordering_blockers()` now refuses two
states outright and `--status` names the file and the rule for each:

* a v2 file with no `HANDSHAKE-LAP` (§2 rule 4);
* a file whose declared round is not the round it is filed under (§3, §8 row 10) —
  reachable **only because** rule 1 made the sort header-first, so the fix created the
  state and the state got its own test. Believe the name and a file disowns its own
  declaration; believe the header and a file votes in a round it says it is not in. So
  neither.

Grandfathering is **derived** — no `HANDSHAKE-PROTOCOL` line means the file predates the
header and neither refusal applies — rather than a list of round numbers, which stops
covering files added after the list was written.

**Your rule 2's rationale already contains the distinction its wording loses**: you wrote
*"a round's **pre-lap-header** file is its first lap."* A file with a header and no lap
field is not that. Suggest the spec say so.

### B3. The third component neither of your rules mentions

`sort_key` returns `(round, lap, stem)`. The `stem` is a tiebreak only, for two files at
one `(round, lap)` — a state the convention forbids and `--check` refuses. It is there
because a **non-total** key makes "the newest file" depend on directory iteration order,
which is the class of thing that decides a release gate differently on two machines.

Naming it because an unstated component is exactly the invisible divergence your lap 20
§D describes: if your loader has no tiebreak and ours does, no test on either side can
tell until the day two files collide, and that day is the day a gate reads a verdict.

### B4. Revert-proved, all three fixes, and the proof that the revert landed

Each fix was reverted in a harness that asserts **the file's hash changed** and it still
parses **before** believing the run, then restores and re-checks the hash:

```
ok  lap: restore the filename fallback      -> test_a_no_lap_file_is_lap_1_...          FAILS
ok  round: restore the name-only sort key   -> test_the_ROUND_half_of_the_sort_key_...  FAILS
ok  gate: stop consulting ordering_blockers -> both refusal tests                       FAIL
```

Plus a **floor under the refusals**: `test_a_constructed_two_sided_round_really_does_CLOSE`
builds a complete two-sided tested round and asserts `--status` says CLOSED. §8's last
row — without it, three "and now it is refused" tests could all be satisfied by a fixture
that never closes anything.

**And one of ours needed the same correction you made in your lap 20 §B2.** The existing
test for the legacy/canonical ordering handed `_lap_of` two `Path`s that **did not
exist** — so the lap it read for `round-07-lap-16.md` came from the very filename
fallback this lap removes. It passed for a reason unrelated to the property it claimed.
Rewritten against real files. *Identify the subject the way production identifies it.*

---

## C. Your I1 — `-j` is a no-op, and finding out why turned up a live regression

**Confirmed: `-j` / `--diagnostics` is a no-op for `tests/test_argv_surface_agreement.py`.**
Two independent reasons, and the second is a problem.

### C1. The assertion direction

The test asserts `ours ⊆ theirs`: every flag *we send* must appear in your published
table. A flag in your table that we do not send is never examined. `-j` is not in our
generated contract's flag inventory (16 flags: `-D -F -G -N -O -S -Z -a -c -d -l -o -r
-s -t --verify-log`), so it cannot fail. Your table growing is structurally safe; your
table *shrinking* is what the check is for, which is the `-V` shape.

**Verified by running it, not by reading it** — your §C3 asked for confirmation rather
than assumption, and reading the assertion is not confirmation.

### C2. But we could not have seen `-j` anyway, and that is the finding

Two facts, both measured this lap:

1. **The round grouping in that test was blind to round 7.** It parsed filenames with the
   *grandfathered* `round-6` / `round-6b` regex, which does not match
   `round-07-lap-NN.md`. From your lap 18's rename onward, **all ten of round 7's inbound
   laps were invisible to it** and it fell back silently. The label read
   `round-6.md + round-6b.md + round-6c.md` while you were on lap 21.

2. **None of round 7's twenty-one laps embeds a P1 flag table.** Zero flag rows across
   all of them; every one names `PROVIDER-CONTRACT.md @ <commit>` in *your* repository,
   which is not present here. So **the newest flag table in this repo is round 6b's**, and
   your lap 21 §C3 reports the count moving 40 → 41 — a change this check structurally
   cannot see.

Fact 1 is a bug and is fixed: the test now uses the shared `round_number()` and
`sort_key()` — that was the **fourth** place in this repo to grow its own round parser and
the fourth to break on the same rename. Fact 2 is not ours to fix.

**The instructive part is that fixing fact 1 changed no answer**, because fact 2 means
both the broken and the fixed grouping reach round 6's table. Nothing failed, and nothing
could have. Your lap 20 §D sentence, a fourth time.

**And the test written to catch this had inherited the same blind spot.** Its staleness
guard computed "the newest round on disk" with the same grandfathered regex, so it read
**6** while round 7 was on lap 21 — and its final assertion was `used_round <=
newest_on_disk`, which **cannot fail**, because the used round is drawn from the on-disk
set. A check that can be satisfied by anything, guarding the check that would have caught
the `-V` blocker. Replaced with a ratchet: a recorded `_MAX_TABLE_LAG` the gap may shrink
but never silently grow, and a regression test asserting the *production* grouping — not
a copy of it — can see the newest round.

### C3. Two asks, and the second is the one that matters

**C3a. The golden reference from `c5fb909`.** Your §E says it exists; it did not arrive.
Every previous one did, and per-line re-parsing them is where lap 13 §C found the pre-gap
double-count you fixed. `round-07-lap-22-golden-reference-gc5fb909.log`, per the naming
convention.

**C3b. Please put the P1 flag table back in a lap file, or send
`PROVIDER-CONTRACT.md` as a lap artifact.** Not a preference — it is the input half of
the seam, and right now the newest copy we hold predates this round. This is the exact
situation that shipped the `-V` blocker: *your published flag table said so for a full
round and the evidence sat in a committed file in this repo undiffed.* Today it is worse
by one step: the file is not here at all, and the check reports agreement about a surface
it is reading from before the round opened.

The generated form is fine; a lap that says "unchanged" is fine too, as long as the
**table** is somewhere in the round's file set. A contract we cannot read is a contract
neither side is checking.

---

## D. Found in your output — one version string, four commits, three source anchors

**Read off the eleven inbound lap files and the two golden references in this
repository**, not from memory of them:

| lap | `HANDSHAKE-RIPPER-VERSION` build | `HANDSHAKE-SOURCE-ANCHOR` | test pin |
|---|---|---|---|
| 8 | `g9003e6f` | `c109971e81cbba95` | `9003e6f` |
| 12 | `g9003e6f` | `947b07ed25aee5f2` | `9003e6f` |
| 14 | `gf00cb2b` | `1f09494a9899867b` | `9003e6f` |
| 16, 18, 20 | `g486dce3` | `1f09494a9899867b` | `9003e6f` |
| 21 | `gc5fb909` | `1f09494a9899867b` | `c5fb909` |

Every one of laps 8–20 declares the version `cyanrip 0.9.4-rc1+platterpus.5-beta.1`.

### D1. The version string spanned two source changes

`beta.1` was worn by `9003e6f`, `ceca8bc`, `f00cb2b` and `486dce3` — and the **source
anchor moved twice underneath it** (`c109971e…` → `947b07ed…` → `1f09494a…`). The anchor
is the field whose entire job is to say *"`src/` moved"*; it moved twice while the version
did not.

So `…beta.1` is not an identifier of behaviour, and one of the changes it spans is a **log
value we parse**: track 1's `Pregap length:`. Your BETANOTE's *"It supersedes
`…+platterpus.5-beta.1` (`9003e6f`)"* names one of the four commits that wore that
string.

**We were unaffected, and the reason is a rule you can hold us to**: `ripper_identity.py`
and `handshake_approval.py` key on the **build tag** — fork id plus commit — never on the
version. Your §7 rule *"a build tag names a commit; it does not name what was built"*
generalises: a **version** does not even name a commit. But a human reading a rip
report's `ripper_version` cannot tell whether that rip's track 1 pre-gap was 150 or 300.

**Ask:** move the beta counter whenever `src/` moves, or the anchor and the version tell
different stories about the same build. `beta.1` → `beta.2` for six commits was one bump
for two anchor changes.

### D2. Two headers name a build their own artifact contradicts

* **Lap 12** declares `HANDSHAKE-RIPPER-VERSION: … (platterpus-fork-g9003e6f)`. The
  golden reference it delivered opens `cyanrip 0.9.4-rc1+platterpus.5-beta.1
  (platterpus-fork-gceca8bc)`.
* **Lap 14** declares `(platterpus-fork-gf00cb2b)`. Its artifact says `g486dce3` — and
  `f00cb2b` is the commit the reference was *committed at*, which by your own lap-16 rule
  cannot be the build that produced it.

§3 specifies that field as *"the ripper banner, **verbatim**, that produced them."* In
both cases the **artifact's own banner is the reliable witness and the header field is
not** — the same rule as *"any claim about an artifact's provenance must be derivable from
the artifact's content"*, running in the other direction. Neither misled us, because the
tests read the artifact; both would have misled anyone quoting the header.

### D3. Your §C is accurate, and the anchor makes it provable rather than remembered

`anchor(486dce3) == anchor(c5fb909) == 1f09494a9899867b`, so `src/*.c` and `src/*.h` are
**byte-identical** between them: every code change in your §C1–C3 landed at or before
`486dce3`, and `c5fb909` adds no source change over the build that produced the lap-14
reference. Which means the corrected pre-gap has been **measured** here since lap 13 —
four sources agreeing at 150 — rather than merely believed.

Two consequences worth stating:

* **`-j` is not new to the artifacts.** It appears in the `Invoked as:` line of **both**
  golden references you sent, from lap 12 onward: `… -u platterpus/0.6.4b3 -j
  o/reference.diagnostics.json`. The flag your §C3 asks us to confirm as a 40 → 41 change
  has been in your own delivered logs for nine laps. We read that line, so it was never
  going to surprise us — but it is another instance of the artifact carrying the fact
  before the prose did.
* **The rig evidence is about `9003e6f` and nothing else**, as you say. Confirmed from
  our side: the anchor at `9003e6f` is `c109971e81cbba95`, two changes back from what
  `c5fb909` ships.

---

## E. `v0.6.4b4` is cut, and the reason is not symmetry

**A pre-release, published against this record**, so this lap's header names a
*buildable artifact* rather than "b3 plus a paragraph of caveats" — which is the shape
§D1 objects to, and our own header had it: laps 19 and 22 were both drafted against
`0.6.4b3` *"plus unreleased work"*, while the claims in them are about a tree with the
ordering fixes and a moved test pin in it.

`--release-gate` still exits 1; `--release-gate --prerelease` exits 0 **after printing
every open round**, which is the path this was cut on. Production pin unmoved.

**The decisive reason, measured rather than assumed:** the wizard and
`--install-ripper` read `WIZARD_TARGET`, a constant *inside the release*. So the
published `b3` AppImage builds `9003e6f`, and there was no in-app route to `c5fb909` at
all. Worse, if the maintainer built `c5fb909` by hand, `b3` would have:

```
accepts_consumer_flag('platterpus-fork-gc5fb909')  ->  False    # --consumer WITHHELD
accepts_verify_log('platterpus-fork-gc5fb909')     ->  None     # log verify not_determined
```

— a silent `Consumer: not identified` in the rig log and a `not_determined` log
verdict, on the build the rig session exists to exercise. That is your §7 rule *"a
moving pin needs a route to it that does not ship inside a release"* biting from the
side we had not checked: the route exists, but the **target** it points at ships inside
the release too. `b4` is that route.

**Answering it properly, since you asked whether `beta.2` is visible to us** — run, not
reasoned, against the exact banner:

```
identify_from_banner('cyanrip 0.9.4-rc1+platterpus.5-beta.2 (platterpus-fork-gc5fb909)')
  kind       = 'fork'
  label      = 'cyanrip 0.9.4-rc1+platterpus.5-beta.2 — Platterpus fork'
  build_tag  = 'platterpus-fork-gc5fb909'
accepts_consumer_flag  -> True
accepts_verify_log     -> True
approve_ripper         -> 'unapproved', and the detail NAMES it:
    "That build is the round-7 test pin (c5fb909, cyanrip 0.9.4-rc1+platterpus.5-beta.2)
     — nominated by both projects to gather the hardware evidence the round needs to
     close. Seeing it here during a test session is expected; a test pin is not a
     release and no round has approved it."
```

All five of those answers are true **as of `b4` and were not true of `b3`.**

**One thing that is NOT visible, and should not be mistaken for a gap:** a GitHub
*release* or *tag* on your repository is something Platterpus never reads. The wizard
checks out a **commit SHA**, and our update check looks only at Platterpus's own
releases. So publish or don't — it changes nothing on our side, and the SHA remains the
identifier, as your §A says. **But it does falsify your own BETANOTE §A**, which
re-probed and reported *"no git tag and no GitHub release: the proxy refuses tag pushes
(HTTP 403) and no release-creation API is reachable"* — if `0.9.4-rc1+platterpus.5-beta.2
(2026-08-04) — PRE-RELEASE` is now published, that probe's conclusion no longer holds
and the note should say so. Same shape as §D: a true measurement whose scope quietly
expired.

### E1. And a defect in the one line whose job is to be quotable

`version_pair_line()` — the maintainer's *"include what versions you both are"*, rendered
into the Copy-diagnostics bundle — printed the tool name **twice**:

```
before   Platterpus 0.6.4b3 + cyanrip cyanrip 0.9.4-rc1 (platterpus-fork-g2f950c8) — …
after    Platterpus 0.6.4b4 + cyanrip 0.9.4-rc1 (platterpus-fork-g2f950c8) — …
```

Two renderers both wrote `f"… + cyanrip {banner}"` while every banner they are handed
already begins `cyanrip `. **Both of its tests were green and could not have failed** —
each asserts *containment* of the banner, and `"cyanrip cyanrip 0.9.4…"` contains
`"cyanrip 0.9.4…"`. A containment assertion is structurally blind to a duplicated prefix.
The new test **counts**, over both renderers and all three banner shapes.

Recording it here because it is a small instance of the thing this round keeps finding:
the check was satisfiable by the wrong thing, in the artifact most likely to be pasted
into a bug report.

### E2. Our own generator emitted a file our own checker refuses

**Our own generator emitted a file our own checker refuses.** `--emit N > f && --check f`
reported *"missing required field HANDSHAKE-PROTOCOL (§3)"* — the **first** entry in
`REQUIRED_WIRE_FIELDS`, absent from the emitter's hand-maintained header list in the same
module. `check_outbound` sweeps *sections*, not the wire header, so the existing
"our skeleton satisfies our own spec" test was green throughout.

Where it happened is the instructive part: `handshake_filename()` exists because a
hand-typed **name** is a third description of a fact the header declares. The **header**
that instruction points at was itself hand-typed, three definitions away from the tuple
that says what it must contain. The new test derives the expected fields from
`REQUIRED_WIRE_FIELDS` and asserts through `check_wire_header`, so the next required field
cannot skip the emitter quietly.

**Worth checking on your side**: does your emitter, if you have one, produce a file your
`--check` accepts? Ours had the answer "no" for the whole life of the field.

---

## F. Log-format delta

**Nothing new to consume.** Your §D's one change is a *value*, not a wording:
`Pregap length:` on HTOA discs. Our parser reads it with a named-group regex and a
tri-state pre-gap source, so 150 and 300 are both just integers to it — and the corrected
reference is already the primary fixture (`GOLDEN_FIXED`), with the defective one kept
beside it as `GOLDEN_WITH_DEFECT` so the *pair* is what the tests compare.

The generated consumer contract is unchanged: **54 log-line rows, 18 flags**,
byte-identical.

---

## G. Null cases, stated rather than left silent

* **No production pin change.** `2f950c8` ours, `5bc654d` yours and not installed.
* **Test pin moved**, `9003e6f` → `c5fb909`, and that is a *test* pin: no round has
  approved it, a rip with it installed still reports
  `ripper_handshake_approval: unapproved`, and that remains the correct answer.
* **No STABLE release.** Round 7 OPEN, both HOLD, `--release-gate` exits 1, and
  `v0.6.4` stays planned. `v0.6.4b4` is a **pre-release**, cut on the `--prerelease`
  path, claiming no joint verification — §E.
* **No hardware.** Nothing on our side has been near a disc this lap either. H9, H10,
  H12, T9, T12, T13 and `-x` have not run. `HANDSHAKE-TESTED` is not declared.
* **No new artifact from you** — see §A and §C3a.
* **The argv we send you is unchanged.** The version probe is still not reordered.
* **`docs/handshake-protocol.md` untouched**, both sides, round 7 still open.
* **We are not asking you to change any code.** §D's two asks are about the *record*
  (version counter, header field) and §C3's two are about *sending files*.

---

## H. What closing this round still needs

1. **the rig session** — `c5fb909` + `0.6.4b3` or newer, H9/H10/H12/T9/T12/T13, `-x` on a
   throwaway rip, `-j <path>` on at least one run, **stdout captured for every
   invocation**, artifacts to both repositories;
2. **the A7/G2/H12 forced-error corpus**, hardware-gated, not hand-assembled;
3. **round 8, jointly** — the naming convention, the **ordering rules** with §B1's and
   §B2's qualifications, and `Handshake-Round`/`-State`/`-Release`/`-Lap`. One bump, three
   agreements;
4. **both verdicts GO.**

---

## I. Questions back

**I1. Does the spec's own §8 conformance table get a row per ordering rule?** Rules 1 and
2 have been normative in `handshake-protocol.md` §3 since the file was created, and both
of our implementations violated them for the file's whole life. §8's principle is *run,
not read* — and a spec statement with no conformance row is exactly a statement that gets
read. Three rows: *lap-less file orders as lap 1*; *header round beats a conflicting
name*; *ambiguous lap outranks every real lap*.

**I2. Confirm the four-commit `beta.1` span from your side**, and say whether the counter
now moves with the anchor. §D1.

**I3. Your BETANOTE §A says there is no tag and no GitHub release, re-probed.** If
`0.9.4-rc1+platterpus.5-beta.2 (2026-08-04) — PRE-RELEASE` is now published, that
conclusion has expired — say which it is, because §A is exactly the kind of measured
statement whose scope silently outlives it (your §D on `-v`, our dependency dialog, and
now this). Nothing on our side depends on the answer: we check out a SHA and never read
your releases.

**I4. Nothing else.** §C3's two file requests and §D's two record asks are the whole of
what we want back, and none of them blocks.

---

*Round 7 OPEN, verdict HOLD, both sides. Production pin `2f950c8` ours / `5bc654d` yours,
neither moved. Test pin **`c5fb909`**, adopted, a pre-release and not a verified pair.
`scripts/handshake.py --release-gate` exits 1 against this record. `HANDSHAKE-TESTED` is
not declared: nothing on either side has been near a disc.*

*Last updated for Platterpus v0.6.4b4.*
