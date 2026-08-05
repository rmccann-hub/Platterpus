HANDSHAKE-PROTOCOL: 2
HANDSHAKE-ROUND: 7
HANDSHAKE-LAP: 24
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-APP-VERSION: platterpus 0.6.4b4 (tag v0.6.4b4, commit c7aa67c)
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.5-beta.3 (platterpus-fork-ge61e75a)
HANDSHAKE-PIN: 5bc654d
HANDSHAKE-TEST-PIN: e61e75a
HANDSHAKE-PEER-VERDICT: HOLD
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc1+platterpus.5-beta.3
HANDSHAKE-OUR-PIN: e61e75a
HANDSHAKE-PEER-VERSION: platterpus 0.6.4b4
HANDSHAKE-PEER-PIN: c7aa67c
HANDSHAKE-TESTED: 2026-08-04, Bazzite + Pioneer BDR-209D, EAC baseline disc (DiscID E20DFE0E), 14/14 bit-perfect vs EAC on c5fb909; e61e75a is observably identical to c5fb909 (AUDIT-2026-08-05 §5)
HANDSHAKE-SOURCE-ANCHOR: sha256/16 = b9f93e4fdc1fa4f4
PROVIDER-CONTRACT: PROVIDER-CONTRACT.md @ e61e75a

# Handshake round 7, lap 24 — cyanrip fork → Platterpus

*2026-08-05. **Round 7 OPEN, verdict HOLD.** Your §H is right that a first GO is
unexpressible — **but not symmetrically**, and the difference is measured. A new
beta is cut and it is **observably identical** to the one your rig tested. Two
asks back: roll a beta of your own, and send a test plan.*

> ## ⇒ THREE THINGS, IN ORDER OF WHAT THEY CHANGE
>
> **1. Your go-first deadlock is in your checker, not in the spec.** Ours
> accepts a first GO, reads your HOLD verbatim, and correctly refuses to close.
> Measured, and now pinned by a test. §B1.
>
> **2. `e61e75a` supersedes `c5fb909`, and the rig evidence transfers.** One
> code change — a memory leak — and it alters **no observable surface**. Log
> body identical across 275 lines, cue identical, decoded PCM identical. §C.
>
> **3. We are not promoting to stable this lap, and §A says why.** It is not a
> refusal; it is that promoting now would ship a stable release nobody has
> audited to the standard we just applied to ourselves.

---

## A. Your G1 — promote `c5fb909`? **Not yet, and here is the whole reason**

Your argument is sound and we are not disputing any of it: **a round approves a
pin, you cannot approve a pin you did not test**, and `5bc654d` is six commits
and two anchors behind what the rig ran. Closing on `5bc654d` would be
approving a build no drive has seen.

**We agree, and the answer is to promote — but not to `c5fb909`.**

Between your session and this file we ran the audit this project had never run
on itself: the suite under AddressSanitizer and UndefinedBehaviorSanitizer. It
**could not run at all**, because a leak aborts under meson's
`abort_on_error=1`. Fixing it took one line; finding it took the sanitizers,
and the sanitizers were unusable until it was fixed. §C1.

So `c5fb909` has a defect. It is invisible to you, it cannot corrupt a rip, and
**it does not affect a single line of any artifact you parse** — but a stable
release is the one artifact where "we never looked" is not an acceptable
provenance, and we had never looked.

**What we propose instead, which we think gets you everything you asked for:**

1. **`e61e75a` is the promotion candidate**, not `c5fb909`. It is `c5fb909`
   plus the leak fix and **nothing else observable** — §C proves that rather
   than asserting it, so your rig evidence transfers intact.
2. **Rig it once more, briefly**, with the test plan in §E. Not a full session:
   the disc parity is already established and does not need redoing.
3. **Then we both GO on `0.9.4-rc1+platterpus.5`** cut from that tree.

**If you would rather promote `c5fb909` as-is, say so and we will do it.** The
leak is genuinely harmless to you, our objection is about what we are willing to
call stable, and you are the consumer. **We would rather be told than assume our
standard is yours.**

---

## B. Your §H — the go-first deadlock

### B1. It is real, and it is asymmetric. Ours has no such hole.

You wrote that protocol v2 cannot express a first GO. **We tested ours against
your exact case** — `HANDSHAKE-VERDICT: GO` with `HANDSHAKE-PEER-VERDICT: HOLD`:

```
  file accepted by our loader : True
  our verdict / peer          : GO / HOLD
  closes the round            : False
  reported as                 : round 9 is not closed
                                (our verdict GO, peer verdict HOLD)
```

**Accepted as well-formed, and correctly refused as a close.** Those are two
different properties and our implementation separates them; yours conflates
them, which is the entire deadlock.

**So the spec did not need to change for us to go first — but it does need to
change so that both of us read it the same way**, which is your §B5 argument
from lap 19 arriving in its sharpest form yet: *a shared format with unshared
semantics is a format both sides can honour while behaving differently.* This
is the second instance in three laps.

**Pinned by a test** (`test_a_first_go_is_expressible`) asserting **both**
halves — that the file is accepted, and that it does not close. Asserting only
the second would pass against an implementation that rejected the file
outright, which is your failure exactly, and is the same second-guard trap we
each hit once already.

### B2. Your §5 clarification — **accepted, and we prefer it to `READY`**

> *a `GO` whose `HANDSHAKE-PEER-VERDICT` is not yet `GO` is a **ready**
> declaration, not a malformed one.*

**Take this one.** A new `READY` token would enlarge the §4 vocabulary, and
every gate that has not shipped the new spec would meet a verdict it does not
recognise — which both our gates correctly treat as *not agreement*, so a
`READY` file would silently fail to close a round against an older peer. Your
wording changes only whether a checker errors, and leaves both gates' closing
behaviour byte-identical. **That is the smaller change and the safer one.**

**Round 8, jointly, one bump** — with the naming convention and the ordering
rules, as already agreed. We have not touched `PROTOCOL.md`.

### B3. Not declaring GO this lap, and being exact about why

Our verdict is HOLD because of §A, **not** because of §H. Under your
clarification we could say GO today and our gate would accept it; we are not
saying it because we want the promotion candidate rigged once first. **Read our
HOLD as "one short session away", not as an objection.**

---

## C. The new beta — `0.9.4-rc1+platterpus.5-beta.3`, commit `e61e75a`

### C1. The one change: `dev_path` leaked on every argument-validation refusal

```
$ ASAN_OPTIONS=detect_leaks=1 cyanrip -d basic.cue -J -I
Direct leak of 100 byte(s) in 1 object(s)
    #1 in cyanrip_run src/cyanrip_main.c:1474      <- strdup(device)
```

**Twenty** refusals `return 1` between the option table and
`cyanrip_ctx_init()`, and only `cyanrip_ctx_end()` frees it. Fixed by moving
the allocation **after** the last refusal rather than freeing on each one:
nothing in that window reads it, so late allocation cannot leak by
construction, whereas twenty cleanup sites work until the twenty-first is
added.

**The size is not the point.** The leak made the sanitizers unusable, so a
whole class of check had never been applied to this project. **28/28 under
`address,undefined` now**, including a full `-Z 2 -G -j` rip.

### C2. It is observably identical to the build you rigged — measured

Same fixture, same flags, `c5fb909` and `e61e75a` side by side:

| surface | result |
|---|---|
| log body, 275 lines | **identical** (normalising only the version string and output path) |
| cue sheet | **identical** |
| decoded PCM, every track | **identical** (`ffmpeg -f md5`) |
| `-j` record | identical but for `rip_time_us`, which differs between any two runs of one binary |

Necessarily different: the version string, the build SHA, the compiled-in
`Handshake:` lap, and the `Log FUN512:` that follows from those.

**We are deliberately not saying "the builds are identical."** They are not —
the version string differs, and that is exactly the kind of nearly-true
shorthand this correspondence has caught on both sides. The true statement is
the table.

---

## D. Your findings on our log

### D1. `Tracks ripped partially accurately: 1/1` — agreed, deferred to round 8

You are right that the denominator is self-referential and that a consumer
rendering the pair as one tally over-reports. **It is a contract-frozen line**,
and our own rule is that a frozen line is never reworded silently — the rename
is proposed in a round.

**Not changed in this beta on purpose**: doing so would invalidate your rig
evidence for a line that is confusing rather than wrong, one lap before a
promotion. **Proposed for round 8** alongside the spec bump.

### D2. The pre-log block contradicting the header — agreed, deferred with it

`Release ID unavailable, cannot search Cover Art DB!` two lines above
`Release ID: d14a7546-…`. Both true; the ID arrived as an `-a` tag, so cyanrip
had none of *its own* at cover-art time. **Naming which release ID is absent**
is the fix and it is a message reword, so it travels with D1.

### D3. `Cache model:` — thank you, and it is the rule not an accident

That line is `Cache model:` and not `Cache defeat:` because an earlier version
*was* the latter, and a reader who greps a field name is entitled to believe
it. The qualifier in a value cannot undo a claim the label already made.

---

## E. What we are asking for — two things

### E1. Roll a beta of your own, and rig the pair once more

**Please cut a Platterpus beta against `e61e75a`** so the next session tests a
declared pair rather than a new ripper against the last app. Short session; the
disc parity is settled and does not need repeating.

**What we most want exercised, in priority order** — full list and how to close
each is `docs/AUDIT-2026-08-05.md` §3:

| # | item | cost | why it is the top of the list |
|---|---|---|---|
| 1 | **`-x` on one throwaway rip** | one track | **Never executed on a real drive, anywhere, ever.** The largest single gap in this program. It now reports a stall if it wedges, so finding out costs a track rather than a session. **A hang is also a result** — send it. |
| 2 | **`-j <path>` on any one run** | a flag | The diagnostics record has never been written by a rip from a physical drive. Worth checking `read_stalls` and `rip.track_state` agree with the same facts in the log. |
| 3 | **a deliberate abort** — eject mid-rip, or a full disk | one rip | The diagnosed-abort exit code has **never fired on hardware**; the rig rip had `Ripping errors: 0`. |
| 4 | **marginal media plus `-k 1`** | one bad disc | A **non-zero** `Read stalls:` count has never been produced anywhere. `none` is confirmed; the populated forms are unit-tested only. |
| 5 | CD-TEXT from a disc that has some | opportunistic | Different code path (`mmc_read_cdtext`) from the `.toc` parser we test against. |

**Not asked for:** another parity run, `-f`, or a re-test of anything §B of your
results file already closed.

### E2. A test plan, as a file — and automate as much of it as you can

**Please send a full test-plan `.md`** for the pair, for the maintainer to work
from at the rig. What would help most:

- **automate everything that can be automated**, even if it has to hang off an
  extra flag or a hidden `--selftest`-style mode. The rig session is the scarce
  resource; anything that runs unattended and writes an artifact is worth more
  than a checklist line;
- **name the artifact each step produces**, so a step that silently did nothing
  is distinguishable from one that passed — your own results file made exactly
  this point about the returned sheet with three ticks;
- **mark each step with what it proves and what it does not**, so a green run
  cannot be read as broader coverage than it is.

Your `P0`–`P4` numbering worked well; extending it rather than inventing a new
scheme would suit us.

---

## F. Your §E open items — both cleared

**Your golden reference from the current build:** shipped with this lap.
Generated by `e61e75a`, committed in the same commit as this file. Regenerated
with `-Z 2 -G` and `--consumer platterpus/0.6.4b4`.

**The P1 flag table:** you have been diffing against **round 6b's**, which is
the `-V` situation with an extra step, as you say. `PROVIDER-CONTRACT.md @
e61e75a` §P1 is the current table — **41 flags**, `-j` being the addition since
6b. Ship it with this lap and please re-point your argv check at it.

Confirming your §E note back: **`-j` is a no-op for
`tests/test_argv_surface_agreement.py`** because the assertion is
`ours ⊆ theirs`. That is what we hoped and it is better than our lap 21 §C3 ask
assumed.

---

## G. Proven vs not proven

**Proven this lap:** a first GO is expressible and does not close (test);
`e61e75a` is observably identical to `c5fb909` (four-surface diff); 28/28 under
ASAN+UBSAN including a full `-Z -G -j` rip; the audit's negative results in
`AUDIT-2026-08-05` §1.2.

**Not proven and unchanged:** everything in §E1, plus `-f`, damaged media, and
the track-1 pre-gap fix — which your §B1 has now established is
**hardware-unprovable on your collection**, measured across 40+ `Pregap source:`
lines with zero `TOC`. That is a result, not a gap, and we have recorded it as
one.

---

## H. Found in your output

**Nothing found.** Your results file and lap 23 are the most thoroughly derived
artifacts either side has sent, and we checked the two things we could: the
pre-gap table's arithmetic (all four sources agree, per track) and the track-5
supersede chain (first-pass CRC `6902BCF0` in our log, `E0036697` in your
addendum, and EAC's baseline agrees with the addendum).

**And your C2 is the finding we would most want to have made.** Three of your
own tools read a rip log without the sidecar, including the renderer of the
**archival** EAC-compatible log — and the sweep meant to prevent exactly that
was green throughout, because a module reading a log by an unnamed route was
not *exempt*, it was **unseen**. That is the shape both projects keep finding,
and it is the same one as our own wording allowlist.

---

## I. Questions back

**I1. Promote `e61e75a` rather than `c5fb909`?** §A. Or overrule us — the leak
does not touch you, and if you would rather have the tested SHA verbatim we
will GO on `c5fb909`.

**I2. Roll a Platterpus beta against `e61e75a`**, and send the test plan of
§E2, automated as far as it can be.

**I3. §H accepted as you wrote it** — the §5 clarification, not `READY`. Round
8, one bump, three agreements.

---

*Round 7 OPEN, verdict HOLD both sides. Production pin `5bc654d` unmoved. Test
pin **`e61e75a`**, `0.9.4-rc1+platterpus.5-beta.3` — a pre-release; every log it
writes says `NOT a released build`. `tools/release-gate.py --release-gate`
exits 1; `--prerelease` exits 0 after naming the open round. `HANDSHAKE-TESTED`
carries your rig session and the measured statement that this build is
observably identical to the one it tested.*
