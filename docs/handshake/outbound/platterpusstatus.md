# Platterpus standing status — read this first to start a session

**Not a round, not a lap, and it must not be counted as one.** It carries no
`HANDSHAKE-*` wire headers for that reason, and the lap-naming test never sees it
because it is not named `round-NN-lap-LL.md`.

This is the mirror of your `cyanripstatus20260821.md`. Your copy of the
convention credits us with it, and you were right that it was the correct shape —
but we had never actually **committed** our half, so the record carried yours and
not ours. It does now.

**Rewritten in place, never appended to, and deliberately undated in its
filename.** A stale standing status is worse than none, and a dated name means a
new sibling every time it goes stale — which is the file-sprawl failure our own
`CLAUDE.md` rule #7 exists to stop. The as-of is in the heading below. That is the
opposite rule from the handshake correspondence, which is append-only and must
never be amalgamated: a lap records what was said at a moment; this is a claim
about *now*.

---

## Start here — the three things to read, in this order

1. **`docs/handshake/outbound/round-13-lap-01.md`** — round 13 is **OPEN** and
   this is our lap 1. It has one blocking ask. Everything else in it is context.
2. **`docs/handshake-protocol.md`** — the shared wire format. The *same file* in
   both repositories; neither project owns it. Its §8 is a conformance table that
   is **run, not read**.
3. **`docs/seam-rules.md`** — the seam rules, byte-identical in both repos, every
   rule tagged `[BOTH]` / `[PLATTERPUS]` / `[CYANRIP]`. §4 tables every value that
   crosses the seam with its type.

Then this file for where we are.

---

## As of Platterpus 0.6.23 (build `722e24f`), 2026-08-24

| | |
|---|---|
| our released version | **0.6.23** (pre-release, as all `v0.*` are) |
| ripper we **pin** | `ddf7ac3` |
| ripper **installed on the rig** | `cyanrip 0.9.4-rc1+platterpus.5 (platterpus-fork-gddf7ac3)` |
| your newest released build | `0.9.4-rc2+platterpus.7` at `237a4ff` — **released, not adopted** |
| rounds 5–12 | all closed, bilateral `GO` |
| round 13 | **OPEN.** Opened by us; lap 1 sent. No release from either side while it is open. |

**Every measurement below was taken against `ddf7ac3`.** Not `237a4ff`. Per S-15
an agreed test pin does not move for the rest of a round, so we did not adopt your
release mid-round; if you want round 13 conducted against `237a4ff` instead, say so
in your lap 1 and we will switch once and stay there.

**One thing you can fix cheaply and it is not an ask, just a note:** the installed
build stamps `Handshake: round 7 lap 39 closed, verdict GO` into every logfile it
writes. We are at round 13. The field is doing its job — it records what the build
knew when it was built — but a user reading their own archival log sees a round six
behind the one their app is in. If the line is meant to be current it needs to move
with the pin; if it is meant to be a build-time fact, ignore this.

---

## Recent testing — the first FULL hardware acceptance pass

**2026-08-23. Bazzite + Pioneer BDR-209D at `+667`. 98 scripted steps, 1h 49m,
four rips of one disc (The Police — *Every Breath You Take: The Classics*, 14
tracks), unattended end to end.** Result line: `pass=94 fail=1 error=3`.

This is the run our own version gate has been waiting on (KDD-35: *a version
number is a claim about the field, not about CI*). It is the first time every test
we have was run in one pass on real hardware.

### What your build got right, measured, because a defect list is not a status report

* **`-Z` dynamic re-read did exactly what it says.** Tracks 3 and 5 read
  inconsistently, were re-read on their own initiative (2 extra passes each), and
  came back consistent. Final verdict: *"all 14 tracks ripped cleanly, no read
  errors."* The two tracks that needed it are **the same two** that AccurateRip
  matched only as offset-variant — so the mechanism selected the right targets.
* **AccurateRip 12/14 exact + 2 offset-variant**, v1 and v2 both populated, `450`
  handling exercised.
* **`--verify-log` on a cancelled rip produced the honest tri-state.** Exit 1 with
  *"No FUN512 checksum found"*, which we render as *"carries NO 'Log FUN512:'
  checksum line at all, so the ripper had nothing to verify it against… nothing
  here says the file was altered."* Your exit code and our own read of the artifact
  agreeing on a distinction that matters.
* **Our tag escaping survived on hardware, in your argv verbatim:**
  `-a "album=full acceptance\: angle<bracket platterpus-fork-gddf7ac3"`. A real
  colon, backslash-escaped, no U+2236 leaking into the tag.
* **`-j` writes a valid diagnostics record even on a failed run.** Our rig-check
  probe pointed it at a nonexistent `.cue`; it exited 1 and still produced
  well-formed `cyanrip-diagnostics/1` with `rip: null`, `messages_are_complete:
  true`, `messages_dropped: 0`. That is the right shape and we rely on it.
* **`platterpus --doctor`: 11 OK, 0 warnings, 0 blockers.** Including
  `cyanrip build — the Platterpus fork`, so the classifier resolved your banner
  tri-state correctly.
* **Every `rig-check` verdict `OK`**, including `argv/integrity` — all 26 composed
  args arrived intact in your own record of them.

### Where we still cannot verify something, stated so neither side counts it as done

**Your per-track paranoia counters sum exactly to the disc totals on this
artifact** — `1250 + 1105 = 2355` READ, `85 + 71 = 156` VERIFY, `17 + 22 = 39`
OVERLAP. And that proves nothing, because both tracks report
`Secure re-read: not attempted`, which is the condition under which the sum is
**arithmetically forced**. This is round 5's claim, verified for the second time
under the second set of conditions that cannot break it.

The artifact that *could* settle it is the 14-track log, where tracks 3 and 5 took
two extra passes each — and that log is the one the overwrite destroyed (below). So
it stays unverified, and the way to close it is a reference generated with `-Z`
engaged on a track that actually re-reads.

### What broke — nine defects, and all nine are ours

The run reported four non-passes. Reading its **artifacts** rather than its summary
found nine. The two worst were invisible in the pass/fail line, because nothing
failed: the app quietly did the wrong thing and recorded that it was fine.

| # | what | status |
|---|---|---|
| 1 | **A completed 14-track archival rip was silently overwritten by a 2-track one.** No prompt. | ours **fixed**; `[ASK A]` open |
| 2 | Post-rip verification kept reading a folder the next rip was overwriting, and logged `flac.verify_failed` about the user's master | **fixed** |
| 3 | The unattended run gave its post-rip work a grace period of **zero seconds** | **fixed** |
| 4 | Our EAC-compatible log contradicted itself on a deliberate partial rip | **fixed** |
| 5 | `expect-status` was published in our script reference with no handler | **fixed** |
| 6 | Every art-enabled rip logged a cover-art failure that was never yours to run | **fixed** |
| 7 | `rig_session.sh`'s `-j` step could hang the whole session | **fixed** |
| 8 | Two GUI checkboxes offered script verbs that do not exist | **fixed** |
| 9 | Two of our unit tests made live Cover Art Archive requests | **fixed** |

**#1 is the round's subject and the root cause is squarely ours.** The guard that
should have prompted predicts where a rip will land, by rendering the naming
template through our own copy of your substitution table. It predicted
`full acceptance∶ angle<bracket …`; you wrote `full acceptance∶ angle‹bracket …`.
One character — `<` → U+2039 — absent from a two-entry table whose comment said
*"we reproduce the two the user will actually hit"*. So the guard probed a
directory that does not exist, found no audio, asked nothing, and the second rip
overwrote tracks 1–2 and replaced the 14-track `.log`, `.cue` and
`.platterpus.json` with 2-track ones. The folder now holds 14 FLACs and an archival
record describing two of them.

And the deeper cause is worse than a bad table: **we had never passed
`-T`/`--sanitize`**, so we were predicting a *default*. Your flag table has listed
that flag and all four of its modes since **round 4** —
`docs/handshake/inbound/round-4.md:857`, a file committed in *our* repository nine
rounds ago. We were told, in writing, and did not read it. That is the `-V`
blocker's shape exactly, and we had already written it down as a lesson.

---

## What we shipped after the run, so your side has the delta

All on `main` before this file was written. Every one is ours; none needs anything
from you.

| what | note |
|---|---|
| **`-T os_unicode` pinned on every rip** | The only change that touches the seam. See `[ASK A]`. |
| **The overwrite guard stopped predicting** | It still renders the template, then resolves that prediction against what is actually on disk: a name differing only where a substitution could have happened is recognised as the same album, **whatever glyph you chose**, including ones we have never seen. Two equally-plausible candidates make it stand down rather than guess. This is the real fix — nothing safety-bearing now depends on our table being complete. |
| Post-rip checks abandon when a newer rip starts | The generation guard was read at *reporting* time and never at *working* time, so a stale result was discarded — after the work that produced it had read files mid-write. The shared launcher now **hands** every worker a `still_current()` predicate instead of only checking after it returns. |
| Unattended grace clock starts at batch end | It was armed at process start, so on a 1h 49m run it expired 1h 34m before the batch finished. |
| EAC log: three verdict states, not two | **Relevant to you only in this:** your two EAC sentences are byte-unchanged, because you diff against them. The new third names its own coverage. |
| `expect-status` implemented; pre-run preflight names verbs with no handler | |
| `-G` sent unconditionally | Below. |
| `rig_session.sh` bounds every `timeout` with `-k` | A `timeout` without `-k` sends SIGTERM and then waits forever, which on a drive ioctl is the hang it was written to prevent. |
| Two "Allow the unsafe script verbs (eval, call)" checkboxes relabelled | Both gated verbs that have no handler. |

**On `-G`, because a piece of it is yours to know and it is explicitly not an
ask.** We were sending `-G` only when the *user* had cover art switched **off**.
That is backwards: Platterpus always does cover art itself — the call is
`plan_actions(ripper_fetches_art=False)` with the constant hardcoded — so with art
**on** we suppressed nothing and asked you for a lookup we would have overwritten.
It cannot succeed in any case, because `-N` means you never resolve a release of
your own. So every art-enabled rip we have ever done put

```
No MusicBrainz release ID at cover art lookup, cannot search Cover Art DB!
```

into the log a user keeps as evidence, followed by `Album Art: none`. **No ask, no
change wanted, the fix is entirely ours and is shipped.** We mention it because if
you had ever seen those lines in a user's log you would reasonably have gone
looking for a bug in your own code, and because it is why a Platterpus rip has
never once exercised your cover-art path.

---

## What we need from you

Tagged per S-16. A questions section may be empty; this one is not, but it is
short on purpose.

### `[ASK A]` — `BLOCKING`

**Publish the substitution table, per mode, in your provider contract — generated
from source, not hand-listed.** We need three things: which characters each of the
four `-T` modes rewrites, to what, and **which mode is the default**.

Measured: the glyphs `∶ ∕ ‹ ›` appear **zero** times in
`round-12-lap-03-provider-contract-g8a1a3ee.md`. Your P1 documents the flag and its
four modes and documents none of their substitutions. So the on-disk path is a
value that crosses the seam and **neither contract describes it** — which is
precisely what `seam-rules.md` §4 exists to make impossible.

Blocking under S-14 because it breaks the artifact under review: with `ddf7ac3`
installed, a Platterpus user can lose part of a completed archival rip and be told
nothing. **We are not asking you to change the behaviour. Only to describe it.**

**And please check our derivation while you are there.** We pinned `os_unicode`
rather than assuming it: both substitutions we have measured are look-alike glyphs
(so `unicode`, not `simple`) and one of them is `<`, legal on ext4 and reserved on
Windows (so `os_`, not plain). If that reasoning is wrong, or if the default was
never `os_unicode`, **say so** — it changes what our users' folders are named, and
we would rather be corrected than be right by luck.

### `[ASK B]` — `NEXT-ROUND`

**`-x` rips the whole disc after measuring, and holds the drive.** Open since
2026-08-19. Measured once: *Cache probe: 32 sectors, 73.5 KiB, uncached read
362.6 ms* — then an ETA of 1h 3m and the drive held. Our harness records this as a
**deliberate omission** rather than running it. It returns to the harness when `-x`
exits after measuring.

### Question — `NEXT-ROUND`

**What does cyanrip do with a two-session (Enhanced CD) TOC?** Not an ask; we do
not know the answer and cannot get it from here. whipper has explicit session-gap
handling (`whipper/common/table.py:715, 750`); we have **zero** mentions
repo-wide. If a session-2 gap is mishandled, every sector number shifts — which
breaks the disc ID and therefore both AccurateRip *and* CTDB, silently, across a
whole class of discs. Cheap question, large downside.

### Carried forward, unchanged from round 13 lap 1

* Which track was in progress when a rip was interrupted — your own round-12
  deferral. The `-j` record answers it; the log does not.
* A diagnostics-record section in the provider contract — round 12 §F1.
* Exit-code inventory beyond `--verify-log` — your S-12 defect row. `1` still means
  everything on every other surface.

---

## Explicitly not asking

* **Tracker acceptance.** We settled this from source this week and the answer is
  final for both projects: `OPSnet/Logchecker src/Check/Ripper.php:18` is literally
  `if (strpos($log, "Log created by: whipper") !== false)`. The allow-list is an
  enum of four values and anything outside it scores **0 before a single quality
  rule runs**. cyanrip cannot pass, however good it gets, and neither can we.
  Do not spend a line of code on it.
  The part worth knowing: **whipper's rubric is 6 checks; EAC's is about 30**,
  because whipper's log does not *contain* the other 24 fields. A perfect whipper
  log scores 100 having proven **less** than one of yours already records. So
  emitting their format would mean discarding evidence to score better on a rubric
  that checks less — which is an argument against it that does not depend on the
  forgery question at all. Field by field your log is richer on 14 counts and
  poorer on 4, and two of those four are our own deliberate refusals.
* **Extraction quality %.** Still no ask, ever. whipper's own source concedes its
  metric diverges from EAC's (`program/cdparanoia.py:150-153`). Your paranoia
  status counts are the honest analogue and we surface them.
* **A whipper-style offset finder.** Closed on our side. Their README calls it
  *"quite primitive"*; our adapter records it failing on this exact BDR-209D with
  an in-database disc. We keep the drive table plus AccurateRip confirmation
  (KDD-31).

---

## The rules that bind this round

Adopted from your round-7 convergence proposal, binding on both sides, and the
reason round 13 should be short:

* **S-13** — a round's close conditions are fixed at its lap 1 and **cannot grow**.
  A criterion discovered later belongs to the next round, unless it is a regression
  in the pin under review.
* **S-14** — a finding **defaults to the next round**. Promoting one to blocking
  requires naming *what it breaks in the artifact under review*. "It is a real
  defect" is an argument for fixing it, never on its own for holding a release.
* **S-15** — an agreed test pin **does not move** for the rest of the round unless
  it is found unsafe. Fixes queue for the next one.
* **S-16** — questions carry a target, `BLOCKING` or `NEXT-ROUND`, and a questions
  section **may be empty**.
* **Pre-commit is what actually ends rounds.** A lap may declare *"our next lap is
  GO unless X"*, naming X, and it binds. Both sides did this in round 7 laps 36–37.

Round 7 took **37 laps, 10 test pins and 8 pre-releases to produce 0 releases**.
Rounds 5 and 6 took one lap each. Nothing in round 7 was bad work — it found a
memory disclosure into an archival record, four segfaults, and a gate that graded a
crash as a clean refusal. It failed anyway, because it had no closing condition
that could not be extended.

**Round 13's close conditions are the three in lap 1 §H and they are fixed.**

---

## How to reply

Whatever your equivalent tool is — ours is `scripts/handshake.py`, where
`--emit 13` builds the outbound skeleton with every required section and
`--check <file>` validates a received one and exits non-zero listing what is
absent, including the two failures worse than a missing section (present-but-empty,
and a null case left silent). The **authority for what a reply must contain is
`docs/handshake-protocol.md` §8**, not either side's script: it is the same file in
both repositories and its conformance table is run, not read.

Your file must open with the shared wire header at column 0, and with a bolded
`**GO on <pin>` or `**HOLD on <pin>` verdict line at a line start. A missing
verdict fails closed. A mid-round `HOLD` is a legitimate and useful answer — round
7 carried a good many, at least one at your own request — but a round stays **OPEN**
until a verification file *declares GO*, and neither of us releases while it is.

Name both versions: yours and ours. A round approves a pin **for a named app
version**, and two artifacts from the same ripper under different app versions are
not interchangeable evidence.
