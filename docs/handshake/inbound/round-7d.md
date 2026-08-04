HANDSHAKE-PROTOCOL: 2
HANDSHAKE-ROUND: 7
HANDSHAKE-LAP: 7
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-APP-VERSION: platterpus 0.6.3
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.4 (platterpus-fork-gd9c7124)
HANDSHAKE-PIN: 5bc654d
HANDSHAKE-TEST-PIN: d9c7124
HANDSHAKE-SOURCE-ANCHOR: sha256/16 = c109971e81cbba95
PROVIDER-CONTRACT: PROVIDER-CONTRACT.md @ d9c7124

# Handshake round 7, lap 7 — cyanrip fork → Platterpus

*2026-08-04. **Round 7 stays OPEN. Verdict HOLD.** Neither project releases.*

**The test pin has changed: `f750890` → `d9c7124`. Do not install `f750890`.**
Lap 6 named it on a rule that was wrong, and checking what would waste the rig
session found three defects — one of which would have made an `-x` hang silent,
which is the one thing that session exists to catch. §1, §2.

**A diagnosed abort was exiting 0.** A refusal to start, or a rip that failed
outright, printed its reason and returned success. §3 — and the fix is
**unverified by any test**, which is stated rather than glossed.

**Seven refusal paths never reach the logfile at all.** They fire before the log
is opened, so they exist on stdout only. That is a direct answer to *"do errors
get passed to Platterpus?"* — for these, **no**. §4.

---

## 0. THE STANDING TEST TARGET — supersedes lap 6

```
repo          rmccann-hub/cyanrip
branch        platterpus-fork
TEST PIN      d9c7124                  <- INSTALL THIS (not f750890)
banner        cyanrip 0.9.4-rc1+platterpus.4 (platterpus-fork-gd9c7124)
handshake     round 7 lap 6 OPEN, verdict HOLD -- NOT a released build
tests         24/24
anchor        sha256/16 = c109971e81cbba95
production    HANDSHAKE-PIN 5bc654d, unchanged -- a test pin is not a release
```

Verified by building `d9c7124` in a clean worktree: banner exactly as above with
no `-dirty`, 24/24.

**Its log will say `lap 6`, not `lap 7`, and that is correct** — see §1.

---

## 1. Lap 6's test pin was wrong, and the rule that picked it was wrong

**`docs/handshake/round-*.md` changes the binary.** Since r3 the handshake state
is *compiled in*, so adding a lap file moves the `Handshake:` line. We had been
choosing pins with `git log -- src/ meson.build`, which cannot see that.

Consequence: **lap 6 claimed `f750890` "is the last commit that changes the
binary". It is not**, and a rig running it would have produced logs reading
`round 7 lap 4` — a lap that predates the file scheduling the session.

The rule is now `git log -- src/ meson.build docs/handshake/round-*.md`, and the
claim to retire is *"later commits are documentation, so the tip builds
identically"* — true when first written, false since r3.

**The unavoidable consequence, stated instead of worked around: a file can never
name a build that contains itself.** So the pin a round file announces is always
the commit *before* it, and `d9c7124`'s log says `lap 6`. There is no way to make
it say `lap 7` without a file naming its own hash. Better to say this plainly
than to keep producing pins that are quietly one behind.

---

## 2. `-x` would have hung silently — the one thing the session must not do

**Ordering defect, found by asking what would waste the rig session.**

`-x` ran at `cyanrip_main.c:1845`; the stall watchdog started at `:1852`. The
probe issues raw `cdio_read_audio_sectors()` calls on a path that **has never
executed on hardware anywhere**, which makes it the single most likely thing in
this program to hang on a real drive — and it was the one read with no liveness
reporting at all.

So H10's run could have wedged with **no heartbeat and no diagnostic**: exactly
the "wedged process versus slow drive" ambiguity the watchdog exists to remove,
on the code path most likely to hit it.

Fixed: the watchdog starts **before** the probe, and the probe brackets its own
reads. A hang during H10 is now reported as

```
Still reading track 0 - the read for LSN N has not returned after Ts
```

Track `0` is deliberate — it is not a real track number, and it says *"not
ripping a track"* rather than blaming one.

**This is in `d9c7124` and not in `f750890`.** It is the main reason the test pin
moved.

---

## 3. A diagnosed abort was exiting 0

**Your standing requirement 4 is "full error capture both directions: exit code,
exact argv, complete output."** The exit code half was not holding.

`main()` returned `!!total_error_count`, and that counter tracks **read** errors.
An operational abort increments nothing — so a refusal to start, or a rip that
failed outright, printed its reason and then **exited 0**. A consumer checking
the exit code saw success on a run that produced no audio.

**Our own generated contract predicted this and could not settle it.** It flags
`goto end` as the one class it cannot classify from control flow and says it
needs a run to settle. This is that run. Fixed at four sites; still within
`{0, 1}`, your requirement 3.

### The part that matters more than the fix

**The new `exit_codes` scenario does not cover it.** Reverting the fix leaves the
scenario passing, and we checked rather than assumed — the revert-proof came back
green, which is how we found out.

Every case it exercises already exited 1 beforehand. The paths the fix changes
are not reachable from a disc image:

- **`Offset is unset!`** is gated on `ctx->rcap & CDIO_DRIVE_CAP_READ_ISRC` — a
  *drive capability*. No image driver reports it, so **the message cannot fire on
  an image at all.** Measured: zero occurrences on every fixture.
- the two `cyanrip_rip_track` failure paths need a rip that genuinely fails,
  which a synthetic image does not do.

**So the fix is unverified by any test and belongs in H12.** The scenario's
docstring says so, so it cannot later be read as coverage it does not have.

**Directly useful for your H12 corpus**, since it changes what you should expect:

| case | reachable on an image? | exit | note |
|---|---|---|---|
| `Offset is unset!` | **no — hardware only** | **was 0, now 1** | needs a drive reporting ISRC capability. Your instinct that this one was hardware-gated was right |
| `Device does not support changing speeds!` | **yes** | 1 | you can produce this one anywhere |
| `Invalid track number N, list has M tracks!` | yes | 1 | |
| unknown flag | yes | 1 | `Unable to parse command line argument: …` |
| no such image | yes | 1 | libcdio's own `**ERROR:` wording, not ours |

**One thing to build into the corpus capture:** for several of these the *first*
line of output is libcdio noise (`Checking <file> for cdrom...`), not the
diagnostic. The real message is further down. Your *"complete output with stderr
merged"* already handles it — flagging it so nobody writes a matcher against
line 1.

---

## 4. "Do errors get passed to Platterpus?" — for seven paths, no

Asked directly by the maintainer, and the honest answer is not a clean yes.

**Seven `goto end` refusals fire between `cyanrip_main.c:1667` and `:1794`.
`cyanrip_log_init()` is at `:1816`.** So when they fire, **there is no logfile
yet** — their message exists on stdout and nowhere else.

If your pipeline archives the logfile and not stdout, **those diagnostics are
lost entirely**, and what you archive is either nothing or a log from a previous
run. Combined with §3's exit-0, an aborted rip could have looked like a quiet
success from both directions.

**We are not fixing this in the test pin**, and the reason is that the fix is not
obvious: opening the log earlier means creating a file for runs that then refuse,
and the log path itself depends on metadata that some of these paths abort before
resolving. That is a design question, not a patch, and doing it under time
pressure before a hardware session is how a worse defect ships.

**What we are doing instead, now:** telling you it is true, and recommending
that the rig session capture stdout for **every** invocation including the H12
failures — which your §7a checklist already does. **That is the mitigation, and
it only works if it is deliberate.**

**Proposed for round 8**, and we would like your view rather than assuming: either
open the logfile earlier so refusals land in it, or state in the contract that
these seven paths are stdout-only and a consumer must capture stdout to see them.
The second is honest and cheap; the first is better and riskier.

---

## 5. Also in the test pin

- **H6** — the sample-peak cross-check, shipped in `f750890` and carried forward.
  Silent on agreement; the firing path is unreachable from a disc image, so the
  decision is a pure function with its own unit test, and the wiring was proved
  by perturbation.
- **A golden reference with a `-dirty` banner was committed and then caught.**
  By A9's own marker, four laps after A9 shipped, on the person who added it. A
  shipped reference naming a build nobody can reproduce is worse than a stale
  one. Regenerated clean, and the `reference` scenario now refuses a `-dirty`
  banner and checks the banner's shape — verified by injecting one.
- **`gen-provider-contract.py` refuses a dirty build** rather than reporting the
  committed contract "stale". It was blaming the file for the state of the build
  directory.

---

## 6. Your lap 5, and what we still owe

Everything in your lap 5 was verified and answered in lap 6; nothing has changed.
Restating only what is outstanding:

**From you, when convenient:**

1. **Nominate a test pin.** Ours is `d9c7124`. This is the one that unblocks the
   session.
2. **Add C9 and C10 to your conformance table and run them.** Your table has 14
   rows; ours has 16. C9 is the row that caught our gate claiming to require four
   fields while enforcing none — and yours makes the same claim.
3. **Your view on §4** — logfile-earlier, or contract-documented as stdout-only.
4. **Whether you disagree about not bumping the protocol** for the optional
   `HANDSHAKE-TEST-PIN` field.

**`--consumer` is understood to be landing shortly** — good, and it means the rig
logs will carry both halves of the pair rather than `not identified`.

**From us:** nothing blocking. H6 is in; the exit-code fix is in and honestly
labelled as untested; the `-x` hang is fixed.

---

## 7. The rig session — unchanged except the pin

§6 of lap 6 stands in full: H9, H10, H12, T9, T12, T13, and **send the artifacts
to both repositories**.

**Two things worth repeating because losing them costs a whole session:**

- **Capture stdout, for every invocation.** Gate 3's heartbeat lines are
  stdout-only and never reach the logfile — and §4 means seven refusal paths are
  too. If only logfiles are kept, both questions stay open.
- **Install `d9c7124`, not `f750890`.** The `-x` hang fix is only in the former,
  and H10 is the run most likely to need it.

---

*Round 7 OPEN, verdict HOLD. Production pin `5bc654d` unchanged; test pin
`d9c7124`, `cyanrip 0.9.4-rc1+platterpus.4`, 24/24, **not a release**.
`tools/release-gate.py --release-gate` exits 1 against this record.*
