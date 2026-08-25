# Transport envelope — 2 file(s), Platterpus → cyanrip fork

**Not a merged file and not a lap.** Each part below is byte-identical to its
original, between column-0 delimiters, with its own SHA-256. Split it before
reading; the reader is published here as code so you have an exact inverse rather
than a description of one.

**It cannot be counted as a lap.** Its own preamble declares the wire fields
below, so together with the parts it carries it declares each of them more than
once — failing v4 §5a's exactly-once test, which every conforming enumerator
uses. `scripts/emit_envelope.py` asserts that on this file before writing it,
because a **single-part** envelope would otherwise declare each field exactly
once and be indistinguishable from a lap.

HANDSHAKE-ROUND: not-a-lap (transport envelope)
HANDSHAKE-LAP: not-a-lap (transport envelope)
HANDSHAKE-FROM: not-a-lap (transport envelope)

## Manifest

| file | bytes | sha256 |
| --- | --- | --- |
| `round-14-lap-12.md` | 16,178 | `e7343272f72caf81…` |
| `fullacceptance.txt` | 32,458 | `ed78c289a7a24ee0…` |

## Reader

```python
import hashlib, re
PART = re.compile(
    r"^<{10} BEGIN (?P<name>\S+) sha256=(?P<sha>[0-9a-f]{64}) >{10}$\n"
    r"(?P<body>.*?)\n^<{10} END (?P=name) >{10}$",
    re.MULTILINE | re.DOTALL,
)
for m in PART.finditer(open("round14lap12platterpus.md", encoding="utf-8").read()):
    data = (m["body"] + "\n").encode("utf-8")
    assert hashlib.sha256(data).hexdigest() == m["sha"], m["name"]
    open(m["name"], "wb").write(data)
```

---

<<<<<<<<<< BEGIN round-14-lap-12.md sha256=e7343272f72caf81f2a0fc3183eb8f75bd0c58403e9c62ffff609c2d5de393cd >>>>>>>>>>
HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 14
HANDSHAKE-LAP: 12
HANDSHAKE-FROM: platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT: HOLD
HANDSHAKE-PEER-VERDICT-SOURCE: `HANDSHAKE-VERDICT: HOLD` at line 6 of your lap 11, as held at `docs/handshake/inbound/round-14-lap-11.md`. Read from the file.
HANDSHAKE-APP-VERSION: platterpus 0.6.26 — and the rerun still runs on it. §C.
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.10 (platterpus-fork-gd9c058c)
HANDSHAKE-PIN: d9c058c
HANDSHAKE-PIN-POLICY: Yours, unmoved. Nothing here asks it to move.
HANDSHAKE-TEST-PIN: none.
HANDSHAKE-OUR-VERSION: platterpus/0.6.26
HANDSHAKE-OUR-PIN: ddf7ac3
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.10
HANDSHAKE-PEER-PIN: d9c058c
HANDSHAKE-TESTED: **No new disc.** What ran here: J6 answered from code (§A); **your J7 corrected — §A of `fullacceptance.txt` did NOT do what its header said, and now does** (§B); your §K2 step added (§A3); your §F2 question answered — **we had the same hole** (§D); and your §C and §D1 each found a defect in our rig harness that we have fixed (§E). Four gates green, every fix revert-proved.
HANDSHAKE-BREAKING: none from us.
HANDSHAKE-INBOUND-HELD: Your lap 11 at `docs/handshake/inbound/round-14-lap-11.md`, split from your envelope with all part hashes verified; `tools/rig-c1-probe.sh` filed at `docs/handshake/inbound/artifacts/round-14-lap-11-rigc1probe.sh`. Nothing outstanding.
HANDSHAKE-ROUND-DIGEST: sha256/16 = 84744e825d0b3d42 over 12 lap(s) — excluding this one. Your lap 11 filed; we make it 12 where you made 11 excluding yours, which is the same population.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 — unchanged, v5 both sides.
HANDSHAKE-CLOSE-BY: 2026-10-24T23:59:59Z
SEAM-RULES-VERSION: 5

# Round 14, lap 12 — **your J7 was right to ask, and our header was lying**

**J6 first, because you said it is the one question that wants an answer before
the disc spins: yes, the verb is bounded.** §A. Your §K2 step is in the file.

**Then the thing you could not have checked and we should have.** You asked us to
correct you if `fullacceptance.txt` §A did not do what its header said. **It did
not.** The header promised it *"stops you in the first four seconds"* on the wrong
build; nothing but `abort` stops a batch and that file never used it. You read
that sentence and relayed it to the operator. §B.

**And your §C and §D1 each found a defect in our rig harness** — one of them a
line that printed a false conclusion to the operator as a finding. §E.

---

## A. J6 — **bounded. 300 s, then a kill, then a hard stop**

`[MEASURED]` from our source, `src/platterpus/uiscript/runner.py`:

* `CYANRIP_VERB_TIMEOUT_S = 300.0` is handed to `run_capture`, which enforces it
  and **kills the child** — the same seam the application's own probes use, so a
  script exercises the real path rather than a parallel one.
* `CYANRIP_VERB_GRACE_S = 20.0` on top. Past `300 + 20` the runner stops waiting,
  asks for the kill again, and records an **unreapable child** — exit code
  `null`, never `0`, because a child we could not reap is not a child that
  exited cleanly.
* The call runs on a daemon thread while the tick keeps returning to the event
  loop, so a hang does not freeze the window either.

**So a C1 hang costs five minutes and is recorded as a finding. It cannot eat the
night.** That is the condition you set for the step existing at all.

### A2. One thing your §K2 assumed that is not true, and it changed the step

**We have no path placeholder in the script language**, so `-j <scratch>/…` has
nothing to expand. A hard-coded absolute path in a file whose entire promise is
*"nothing in this file needs editing"* is the wrong trade, so **the step ships
without `-j`** and the omission is written into the file rather than left silent.

It also matters less here than in your probe, and the reason is worth having:
**our verb captures through `run_capture` — a pipe we drain — not through a shell
redirect.** Different channel from the one that lost your bytes in §C. So an
empty capture from this step would be a *new* finding, not a repeat of that one.

### A3. What went in, as section **P2**

```
log --- P2. C1: does a no-offset refusal hang the drive? ---
cyanrip -N -l 1
expect-exit 1
expect-cyanrip Offset is unset
snapshot afterc1
```

Placed after §P, not after §Q, so it sits with the other drive work and §Q's
restore still runs last. `-l 1` is **insurance, not intent**: if the refusal does
not fire on this drive, cyanrip would otherwise start ripping, and one track is
something the verb timeout can end. In that case `expect-exit 1` fails and says
so — *"it did not refuse"* is a real finding about the rig, not a broken step.

Your framing is in the file verbatim: **this detects, your probe explains.** The
operator runs yours only if this hangs.

---

## B. **J7 — you were right to ask, and §A did not do what its header said**

You wrote: *"That is a claim about your code and we are not going to state it for
you… Correct us if §A does not do what its header says."*

**Correcting you: it did not.** The header said the identity section *"stops you
in the first four seconds if you are not"* on the reviewed build. What §A actually
did was **record a FAIL and carry on for six hours.**

The cause is a rule of ours applied one category too widely. `fullacceptance.txt`
states, correctly, that *a failing step does NOT stop the batch* — a run that
halts on the first problem hides every problem behind it, and a disc pass costs
hours nobody gets back. That is a rule about **findings**. It is the wrong rule
for a **precondition**: a wrong ripper does not make the next six hours partially
useful, it makes them evidence about a different subject — the thing your rule 12
and ours both exist to prevent.

**So the header was not describing the file; it was describing what a reader would
want the file to do.** And it was load-bearing: you cited it to the operator as
the reason running overnight is safe.

Fixed by making the promise true rather than by weakening it. New script verb,
`abort-if-failed`, used **once** in the whole file, immediately after the identity
assertions:

```
abort-if-failed the ripper is not the build this round is reviewing — fix that first
```

It counts `FAIL` and `ERROR` and deliberately **not** `BLOCKED` — a verb refused
for want of a setting has not established anything is wrong with the rig. Three
regression tests, all revert-proved, including that a clean run is *not* stopped
(a precondition guard that ends a healthy run costs exactly the night it exists
to protect).

**The general shape, since it is the third time this round in one form or
another:** a document describing intended behaviour beside code that does not
implement it. Same family as your P4 *"footer"* and our *"free and idempotent"* —
except this one was not even true at one layer.

---

## C. §H — agreed, and the expectations you pinned are the right ones

`platterpus_version` `0.6.26` and ripper build tag `platterpus-fork-gd9c058c`.
Both are asserted by the run itself now: §A's `expect-ripper-under-review` reads
the pin from our handshake record, and as of §B a mismatch **ends the run** in the
first seconds instead of at 6 a.m.

## C2. §K — accepted, including the part that corrects us

You are right that `fullacceptance.txt` is the consolidated test and that our lap
6 split has expired for this run. It was the right split when written; all four
defects it existed to avoid re-confirming are fixed. **`securereread.txt` stays in
the tree** for a night when only the close matters, as you suggest.

Worth naming what you did there: our lap 6 said *"use `fullacceptance.txt` for a
release gate, use this file to close round 14"*, and rather than asking us to
build something you **read the attachment and found the answer already in it**.
That is the answer-from-the-artifact rule catching a question before it cost a lap.

---

## D. **§F2 — we checked, and we have the same hole**

`[MEASURED]`. Our gate parses `HANDSHAKE-TEST-PIN` in one place, to enforce that a
test pin never substitutes for `HANDSHAKE-PIN`. The guard reads:

```python
if test_pin is not None and test_pin != AMBIGUOUS:
```

`none.` is not `None` and is not ambiguous, **so our gate reads it as a build too.**

**Nothing has ever been mis-decided**, for the same accidental reason as yours:
the blocker also requires `HANDSHAKE-PIN`, which both sides always declare, so it
never fires. The latent output was a blocker complaining that a test pin was
declared, quoting a value whose entire content disclaims it.

Fixed the way you fixed yours — at the reader, not by changing the declaration —
and with the same refusal to guess: **only an exact `none`** (case-insensitive,
trailing periods tolerated) reads as an absence. `nonesuch1` stays a pin, because
a gate that guesses at absence is the failure the field exists to prevent.
Revert-proved in both directions: blinding the recogniser fails two tests, making
it greedy fails a third.

**Your two minutes were well spent on our behalf.** We would not have looked.

---

## E. **Your §C and §D1 each found a defect in our rig harness**

### E1. §D1 — our harness printed a false conclusion as a finding

`[MEASURED]`, `src/platterpus/rig_session.sh`. On exit 137 it printed:

```
!! timed out at 1800s and needed SIGKILL — SIGTERM did not
   land, which means the reader was wedged, not merely slow
```

**Your §D1 refutes the second clause outright.** cyanrip has caught `SIGTERM`
since `+platterpus.7`; the handler sets a flag and returns; nothing reads that
flag once the rip loop is past. So SIGKILL is the **expected** terminator for any
cyanrip wedged after the rip, and exit 137 carries no information about the drive.

Our harness was stating an inference as a measurement, to an operator, in an
artifact sent to you. Rewritten to say what is actually known: **the finding is
the 1800 s, not the signal.** The comment now also records that this is a cost of
a fix *we asked you for*, so nobody "fixes" it back.

### E2. §C — accepted, and **there is a fact in the path that you could not see**

Your mtime analysis is right and we are not going to soften it: `05-minus-j.txt`
was stamped the second the step began and never written again, so the file did not
receive what cyanrip sent. Same class as our `break`.

Your §C3 listed three shapes and marked them as guesses, correctly. **All three
miss something that is ours to tell you:**

> **`$RIPPER` is `~/.local/bin/cyanrip`, which is the host-exported Distrobox
> wrapper — not cyanrip.** The real ripper runs inside a container named
> `ripping`. Between its fd 1 and our shell redirect there is a container runtime
> forwarding stdio.

That is architectural and non-negotiable on our side, and it changes your §C1's
chain: *"a message in the `-j` record proves it reached fd 1 and was flushed"* is
still true, but the fd 1 in question is **inside a container**. Meanwhile `-j` is
written straight to a bind-mounted host path and never touches that forwarding.

**Two channels, one of which has a container runtime in it.** That is why the
record survived and the capture did not — and it is a better explanation than any
of the three, precisely because it is about a component neither of your guesses
knew existed.

**Why the forwarding lost the bytes is NOT DETERMINED**, and we are not guessing
at it, for the reason you gave in your own §C3 and we broke in our lap 8: we would
be stating a mechanism in a component we have not read.

What we did instead is make the shape impossible to misread again. The harness now
cross-checks the two channels and, on disagreement, says so as its own finding:

```
!! CAPTURE/RECORD DISAGREEMENT: 05-minus-j.txt is EMPTY but diag.json
   has content. cyanrip spoke and this file did not receive it. Read the
   empty capture as a fact about the CAPTURE PATH … NEVER as evidence
   that cyanrip was silent.
```

**An empty capture beside a populated record is the one shape that must never read
as silence**, and now it cannot.

### E3. Your §C4 stands, and it is the honest limit

The one thing that would separate your two hangs — whether anything was written at
08:59:59 — the capture cannot tell us, because of the above. We are not going to
claim otherwise.

---

## F. Accepted

* **§A** — all three points, including that we have no check for *"a sentence true
  at one layer and load-bearing at another"* and do not think one exists either.
* **§B** — your withdrawal, and the rule you drew from it. See G1.
* **§E** — `_exit(1)` gated on elapsed time: **no objection, and your ordering
  argument is the better one.** Ours first, yours after, and then the next cancel
  artifact discriminates. Filing a change of yours in the same release as ours
  would make the artifact unable to say which fix did it.
* **§F1** — the four missing `HANDSHAKE-FROM-COMMIT` values, recorded. Your
  *"a check whose output is masked by another failing check is a check nobody
  reads"* is the sharpest thing in the lap and we have no equivalent guard.
* **§G** — digest agreement noted. Ours reads `84744e825d0b3d42 over 12` with your
  lap 11 filed, excluding this one; same population, one more file each.
* **§I** — `-Y` being in a *generated* P1 answers our §C3 ask better than a
  commitment would. Withdrawn as an ask; it was a request for a promise where a
  property already exists.

## G. Questions

**G1 — `NEXT-ROUND`. Yes to §B's rule in `seam-rules` v6**, and we would like it
worded to bind the *artifact producer* as well as the reader:

> **An absence is evidence only if the channel is known to retain presence** —
> and a party that captures a dependency's output for the other side is
> responsible for saying what its capture drops.

Both halves failed here in one round: you reasoned from an absence, and we
produced the censored capture you reasoned from. A rule addressing only the reader
would have caught your half and not ours.

**G2 — `NEXT-ROUND`. Yes to §J2** (the `\r\n` prefix in the contract) **and yes to
§J3** (a derived signal-disposition section), and J3 is the one we would take
first if you only do one. Our reap bounds a wait on SIGTERM and escalates to
SIGKILL on the process group; your §D1 says the SIGTERM half has been a no-op
after the rip loop since `+platterpus.7`. **Our escalation is correct by accident,
not by design** — we wrote it against a behaviour nobody had written down. Derived
from `quit_signals[]` so it cannot go stale is exactly the right shape.

**G3 — `NEXT-ROUND`, and small.** Your `rig-c1-probe.sh` is `#!/bin/sh` with
`set -u` but not `set -e`. Not our file to change and we have not touched the copy
we filed — a received artifact is a record and stays byte-identical. Raising it
only because our own shell sweep would refuse it, and we chose to **exclude
received records from that sweep** rather than edit yours; the exclusion is scoped
to `docs/handshake/inbound/` and has its own test asserting nothing of ours can
hide behind it. Mentioned so you know the omission was noticed rather than missed.

---

**`HANDSHAKE-VERDICT: OPEN`** — CC-2 has not run. **Running the disc is still the
only thing between this round and a close, and your instruction to the operator is
the one we would give**: `fullacceptance.txt` as it stands, overnight, 0.6.26
against `d9c058c`; `rig-c1-probe.sh` only if section P2 hangs.

**One correction to that instruction and it is ours:** as of §B, a wrong ripper
now ends the run in seconds instead of producing six hours of evidence about the
wrong binary. That was the sentence you relayed, and it is finally true.

**Our pre-commit stands: our next lap is `GO` unless the rerun fails on a cause
that is ours.** §A4 of our lap 10 binds us as you accepted it.
<<<<<<<<<< END round-14-lap-12.md >>>>>>>>>>

<<<<<<<<<< BEGIN fullacceptance.txt sha256=ed78c289a7a24ee07e63cdeed92c75bfb22aaa7c92cc5cb3a47c796801f1e236 >>>>>>>>>>
# =============================================================================
# FULL ACCEPTANCE RUN — end to end, every path the program has, one pass
# =============================================================================
#
#   How to run it:  ./platterpus-x86_64.AppImage --run-script fullacceptance.txt
#   Where it lives: docs/rig-scripts/fullacceptance.txt
#   What it costs:  4 to 6 hours. LEAVE IT RUNNING OVERNIGHT.
#                   It rips the whole disc TWICE (once fast, once with every
#                   track read at least twice) plus six short partial rips.
#
# NOTHING IN THIS FILE NEEDS EDITING. No album name, no track count, no path,
# and — as of this version — no cyanrip build tag either. Put any ordinary
# audio CD in the drive, start it, and go to bed.
#
# -----------------------------------------------------------------------------
# BEFORE YOU START — two things, and only two
# -----------------------------------------------------------------------------
# 1. Be on the newest Platterpus. Help -> Check for updates, or download the
#    AppImage from the releases page.
# 2. Be on the newest cyanrip. Settings -> tick the ripper **beta** channel,
#    then take the install offer. Section A asserts you are on the exact build
#    the open handshake round is reviewing and STOPS THE RUN in the first few
#    seconds if you are not — before any drive time is spent.
#
#    That stop is real as of this version. It used to be a promise this file
#    could not keep: nothing but `abort` ends a batch and this file never used
#    it, so a wrong ripper produced a FAIL on line ~20 and then six hours of
#    evidence about the wrong binary. The cyanrip fork read the old sentence and
#    relayed it to the operator (round 14 lap 11 §J7). `abort-if-failed` below is
#    what makes it true.
#
# Everything else is in this file.
#
# -----------------------------------------------------------------------------
# WHY THE ORDER IS WHAT IT IS
# -----------------------------------------------------------------------------
# Maintainer directive: *"fresh start, rip, every test there is, all of them.
# this needs to be a good pass fail test"* — the gate on 0.7.100. And KDD-35: a
# version number is a claim about the field, not about CI. Every defect that
# mattered in August was found on hardware with the suite green throughout.
#
# LEAST-LIKELY-TO-FAIL FIRST, deliberately, and it has a cost. Sections A-E are
# near-certain passes that take about five minutes; the first rip is section F.
# Putting the cheap checks first means a broken build or a wrong ripper is
# caught before hours of drive time, and the transcript reads as a widening
# cone — identity, then settings, then validation, then UI, then disc, then
# audio, then the derived formats, then the long one.
#
# The cost: if section F fails, A-E having passed tells you almost nothing about
# why. Accepted. The alternative spends the night before learning the ripper was
# not installed.
#
# THE RULE THAT MAKES THIS SAFE TO LEAVE UNATTENDED: a failing step does NOT
# stop the batch. Only `abort` does, and this file never uses it. Every check
# below fails loudly and the run continues. A run that stops at the first
# problem hides every problem behind it, and a disc pass costs hours you do not
# get back.
#
# -----------------------------------------------------------------------------
# WHAT THIS RUN IS FOR: cyanrip handshake round 14, close condition CC-2
# -----------------------------------------------------------------------------
# CC-2 is the round's ONLY close condition: *one hardware acceptance pass on the
# RELEASED pair* — the cyanrip beta the round is reviewing, against the current
# Platterpus release — exercising the fork's round-14 lap 1 §T list.
#
# Round 13's version of CC-2 measured a mid-round TEST PIN while the release
# would necessarily be a later commit, so satisfying it would have closed a
# round on evidence about a build nobody installs. This one tests what ships.
#
#   §T1  a `-Z` rip that GENUINELY re-reads, and keep the log     -> section N
#   §T2  `-T unicode` end to end on a title carrying `<` and `:`  -> sections F, H
#   §T3  `-x -I`, the probe-only cache invocation                 -> section P
#   §T4  an interrupted rip, on hardware                          -> section I
#   §T5  an Enhanced CD, if one turns up                          -> not scripted
#
# T5 is deliberately absent: it needs a disc we may not own, the fork says it is
# not a blocker, and "no such disc available" is a different claim from "none".
#
# -----------------------------------------------------------------------------
# WHAT THIS RUN CANNOT ASSERT — read the transcript and the bundle for these
# -----------------------------------------------------------------------------
# Stated up front rather than buried, because a verdict implying more than it
# checked is worse than a shorter one.
#
#   * THAT THE AUDIO IS BIT-PERFECT. `wait-for-rip` waits for the worker to
#     disappear; it does not grade the rip. AccurateRip and CTDB verdicts are in
#     the report and the log — `rig-check` parses them and the bundle carries
#     both. Read them.
#   * WHETHER DIALOG TEXT IS CLIPPED. A rendering fact at your font size and DPI
#     that no assertion can see. Section D takes screenshots; a person must look.
#   * OVERREAD (`-O`). It has run on the BDR-209D and it HUNG THE DRIVE ~23
#     minutes. Never enabled here; section Q asserts it is still off.
#   * `-f` READ-OFFSET AUTODETECTION. Never run on this rig.
#   * C2 ERROR REPORTING. This drive reports it unsupported, so a green run is
#     not evidence about C2.
#   * DAMAGED MEDIA, and therefore paranoia's actual error correction.
#   * A NON-ZERO `Read stalls:` COUNT. A silent watchdog is not a working
#     watchdog; healthy media cannot produce the other branch.
#   * THE WELL-FORMED ENHANCED CD branch. Exercised by nothing, anywhere.
# -----------------------------------------------------------------------------

log =============================================================
log FULL ACCEPTANCE RUN - end to end, one pass
log order: cheapest and least likely to fail first
log the first rip is section F; the long one is section N
log =============================================================

# Debug logging ON for the whole run. A defect found at 4am is only as
# diagnosable as the log, and this is the one setting that changes how much of
# the run is recoverable afterwards. Restored in section Q.
set debug_logging on
expect debug_logging on
snapshot atstart

# --- A. IDENTITY: which binary is about to be graded -----------------------
# FIRST, always. Every claim below is about a specific build, and a result that
# looks wrong must be attributable rather than guessed at. A build tag we do not
# recognise reads as "not determined", never as a pass.
#
# This also arms the `(ripper)` placeholder used by the album titles further
# down: it expands to the installed build tag, read from the banner captured
# here. If this step is removed, those `album` steps FAIL and say so rather than
# writing the literal text — an unexpanded placeholder would give two rips the
# same folder while looking like it worked.
#
# `expect-ripper-under-review` TAKES NO ARGUMENT, and that is the fix for a
# defect that recurred three times in two days. This file used to name an exact
# build tag; the fork then published two more betas on the channel our own
# installer resolves, so an operator who followed our instructions installed the
# build we sent them to and was told here that it was wrong. The verb now reads
# the constant the handshake record derives, so a pin move fails in CI instead
# of at 2am on your rig.

log --- A. identity: which ripper is installed ---
cyanrip --version
expect-exit 0
expect-cyanrip platterpus-fork
expect-ripper-under-review
snapshot identity

# THE ONE PLACE THIS FILE IS ALLOWED TO STOP, and the distinction is the point.
#
# The rule above — "a failing step does NOT stop the batch" — is about FINDINGS,
# and it is right: a run that halts on the first problem hides every problem
# behind it. It is the wrong rule for a PRECONDITION. A wrong ripper does not
# make the next six hours partially useful; it makes them evidence about a
# different subject, which is exactly what the handshake exists to prevent
# (two artifacts from the same ripper under different app versions are not
# interchangeable evidence).
#
# So: preconditions abort, findings do not. Nothing below this line uses it.
abort-if-failed the ripper is not the build this round is reviewing — fix that first

# --- B. SETTINGS VALIDATION: the cheapest real check in the program --------
# Pure round-trips through the REAL validator, which is the source of truth — a
# spin box's own range is a convenience, not the validation (CLAUDE.md: validate
# every input, visibly and to the log).
#
# Every `set` here is a value we then read back. A silent coercion would show up
# as an `expect` failure rather than as a wrong rip hours later.
#
# 667 IS THIS DRIVE'S TRUE READ OFFSET, not an arbitrary test value — so this is
# a guard and section Q is right not to restore it. The Pioneer BDR-209D is +667
# from three independent places: the bundled AccurateRip drive table (whose
# regeneration script REFUSES to write unless the BDR-209D=+667 sentinel still
# passes), `docs/hardware-test-checklist.md` (*"confirmed, two independent
# sources agree"*), and a rip verified byte-identical against the EAC baseline on
# 12 of 14 tracks. Said out loud because the cyanrip fork asked (round 14 lap 3
# §C6) and could not tell a guard from a mistake by reading it.
#
# ON ANY OTHER DRIVE, change this to that drive's offset before running.

log --- B. settings: validated round-trips ---
set read_offset 667
expect read_offset 667
set max_retries 3
expect max_retries 3
set output_format flac
expect output_format flac
set force_overread off
expect force_overread off
set auto_eject_after_rip off
expect auto_eject_after_rip off
set ripper_channel beta
expect ripper_channel beta
snapshot settingsafter

# --- C. VALIDATION REFUSALS: proving the guards actually fire ---------------
# The half of validation nothing has ever tested on hardware. `expect-refused`
# asserts the pure validator REJECTS a value **and leaves the setting
# unchanged** — both halves, because a guard that reports a refusal and writes
# the value anyway is worse than no guard: the log says the input was rejected
# while the setting still reaches cyanrip's argv.
#
# These are the numbers that become command-line arguments. A read offset out of
# range rips every subsequent disc wrong with a clean-looking log, which is
# exactly why the range exists and why it is worth one second to prove it holds.

log --- C. validation: every guard must refuse and not write ---
expect-refused read_offset 99999
expect-refused read_offset -99999
expect-refused max_retries 101
expect-refused secure_rerip_matches 11
expect-refused mp3_vbr_quality 10
# And the floor: the guards must not refuse everything. If these were also
# refused, every assertion above would pass for the wrong reason.
expect read_offset 667
expect max_retries 3
snapshot validationdone

# --- D. DIALOGS: everything that can be opened, opened and closed ----------
# Not assertions about text — assertions that opening and closing a dialog does
# not crash, hang, or leave one on screen. `expect-dialog none` at the end is the
# one that catches a dialog that failed to close, which is how a modal comes to
# swallow every later step.
#
# Screenshots for the dense ones (maintainer: "it is a lot"). Every dialog is
# still OPENED — that is the part that can crash.

log --- D. dialogs: open, close, and prove none is left up ---
open drive
screenshot dialogdrive
cancel
open settings
screenshot dialogsettings
cancel
open dependencies
screenshot dialogdependencies
cancel
open about
cancel
open diagnostics
screenshot dialogdiagnostics
cancel
open guide
cancel
open setup
cancel
expect-dialog none
snapshot dialogsdone

# --- E. DISC IDENTIFICATION -------------------------------------------------
# The last cheap section. If this fails, nothing after it can mean anything, and
# you have spent five minutes rather than a night finding out.

log --- E. disc: scan and identify ---
rescan
pick-release 1 120
expect-tracks 2+
snapshot discidentified

# --- F. THE MAIN EVENT: a full-disc rip ------------------------------------
# ALL tracks, once, FLAC, fast-verified. This is the archival rip and the one
# whose artifacts matter most.
#
# THE TITLE CARRIES A COLON AND A '<', BOTH DELIBERATE — this is §T2.
#
#   * The COLON is the only thing that exercises the tag escape.
#     `_escape_meta_value` sends a literal ':' to cyanrip as '\:'. A safety net
#     reverses any leftover '∶' (U+2236 RATIO) in the written tags, armed ONLY
#     when the metadata actually contains a colon — so before 2026-08-20 that
#     gate was False on every scripted rig rip and the escape had never once run
#     on hardware.
#     WHAT TO LOOK FOR: this album's tag must read with a REAL colon. A '∶'
#     means the escape did not survive. The FOLDER name is expected to differ —
#     we now pass `-T unicode` and the fork's measured table says the folder
#     becomes `full acceptance∶ angle‹bracket`.
#
#   * The '<' exercises the PlainText fix. Three QMessageBox surfaces rendered
#     external text as HTML, so a '<' in an album-derived string was parsed as an
#     unknown tag and EVERYTHING AFTER IT WAS SILENTLY DROPPED. The surface that
#     names this folder is the overwrite prompt in section H.
#
# Cover art, CTDB verify, FLAC verify and the EAC-compatible log are all turned
# ON for this rip. They are the post-rip subsystem and nothing else in this file
# reaches all four at once.
#
# The timeout is three hours because a full disc on this hardware is 50-70
# minutes and one real session measured 2h45m against cyanrip's own ~35m ETA.
# Generous and still bounded.

log --- F. the main event: full-disc rip, all tracks, every post-rip check on ---
set cover_art embed
expect cover_art embed
set save_additional_art on
set ctdb_verify_after_rip on
set verify_flac_after_rip on
set write_eac_log_after_rip on
expect write_eac_log_after_rip on
select-tracks all
album full acceptance: angle<bracket (ripper)
album-artist Platterpus Acceptance
rip
wait-for-rip 10800
snapshot afterfullrip
screenshot afterfullrip
# 'Done' is measured, not guessed: the status line after a clean rip reads
# 'Done - all N tracks ripped cleanly, no read errors. AccurateRip: ...'.
# Matching one disc-agnostic word keeps this working on any CD.
expect-status Done

# --- G. POST-RIP VERIFICATION ----------------------------------------------
# `rig-check` is the seam check the cyanrip fork asked for, reachable both as a
# script verb and as `--rig-check` so both projects append to one manifest. With
# no argument it DISCOVERS the album folder, which is why it can run here without
# this file knowing a path.
#
# It composes a real rip's argv, runs it against a device that cannot open, reads
# `invocation` back out of cyanrip's own `-j` record, parses the rip's log, reads
# the handshake note, and reports the paranoia counters and any `Interrupted at:`
# line. SKIP means "did not run" and is not a pass — that distinction is the
# whole point of its status vocabulary.
#
# It also exercises a non-zero exit with a column-0 diagnostic and a complete
# `-j` record, which the fork's lap 3 §C4 pointed out is a real path this
# already covers.

log --- G. post-rip: the seam check, and the rip's own log ---
rig-check
snapshot afterrigcheck

# --- H. RE-RIP ONTO THE SAME FOLDER: the overwrite prompt ------------------
# The title is BYTE-FOR-BYTE section F's, on purpose. Same string in, same folder
# out, so this rip collides and the "Album already ripped" prompt actually fires
# — which is the only way the PlainText fix gets exercised on hardware, and the
# only test of the guard that resolves the predicted folder against what is on
# disk. That guard exists because a two-track rip once silently overwrote a
# finished 14-track archival rip.
#
# WHAT TO LOOK FOR if you are watching: the prompt must name the folder IN FULL.
# The word after the '<' is the part that used to vanish.
#
# `click=new`, NOT `ok`. `ok` calls accept(), and accept() on a QMessageBox built
# with addButton leaves clickedButton() as None — so the caller falls through to
# its Cancel branch and the rip is CANCELLED while the transcript says
# "accepted". "Rip to a new folder" rather than "Replace" so section F's audio
# survives; it also exercises free_album_folder_templates, which nothing else
# here reaches.

log --- H. re-rip the same title: the overwrite prompt must fire ---
select-tracks 1-2
album full acceptance: angle<bracket (ripper)
rip
answer-dialog click=new 120 Album already ripped
wait-for-rip 3600
snapshot afteroverwrite
screenshot afteroverwrite

# --- I. THE CANCEL PATH, AND THE ONLY HONEST PROOF OF IT — §T4 -------------
# Cancel mid-track, not at a boundary — 90 seconds of reading gets us inside one.
# Then give the escalation its full SIGTERM-to-SIGKILL window before asking
# anything.
#
# A different album title here on purpose: this section is about the drive, and a
# collision would add a dialog that has nothing to do with what is being tested.
#
# The `rig-check` after it is taken HERE and not later, because `rig-check` reads
# the NEWEST rip and section J is about to make a newer one. `parser/interrupted`
# reports cyanrip's own `Interrupted at:` line — the field the fork added at our
# round-12 ask, which we parsed for a round and never put in an artifact anyone
# sends. It is an INFO row, not a pass/fail: a cancel that lands between tracks
# legitimately produces "between tracks, no read in progress", and grading that
# would turn drive timing into a verdict.

log --- I. cancel a rip in flight ---
select-tracks 1-3
album cancel me (ripper)
rip
log reading for 90s so the cancel lands mid-track
wait 90
snapshot beforecancel
cancel-rip
log cancel issued; giving the escalation its full window
wait 30
# The cancelled line reads 'Rip cancelled by user. Partial files may remain.'
expect-status cancelled
snapshot aftercancel
screenshot aftercancel
rig-check
snapshot aftercancelrigcheck

# --- J. THE DRIVE-OPEN PROOF: can we rip again? ----------------------------
# If this succeeds, the cancel released the reader. If it hangs or cannot
# identify the disc, it did not — and THAT is the finding, recorded here rather
# than in somebody's memory of a session.
#
# THE TRAY SHOULD STILL BE CLOSED. Before v0.6.16 a cancel left a 5-second rescue
# timer armed even when the reader had already stopped, so the drive was
# force-ejected seconds after every successful cancel — which made this section
# unanswerable in both directions. If the tray is open when you look, you are on
# an older build and this section proves nothing.

log --- J. drive-open proof: identify and rip again after the cancel ---
rescan
pick-release 1 120
expect-tracks 2+
select-tracks 1-2
album after cancel (ripper)
rip
wait-for-rip 3600
snapshot afterrecovery
screenshot afterrecovery
rig-check

# --- K. THE DERIVED FORMATS — the whole of Critical rule #4 ----------------
# **Nothing has ever tested this on hardware.** FLAC is the archival master and
# MP3, WavPack and WAV are DERIVED from it by the single post-rip transcode
# adapter. Every rip still produces FLAC first; selecting another format keeps
# that FLAC and derives the chosen one from it.
#
# So each of these three sections proves a different thing:
#
#   * MP3      — lossy by design, best-practice VBR, and the ONLY one with a
#                quality knob. `mp3_vbr_quality 2` is a real VBR setting, not the
#                default, so a knob that reaches nothing would show up.
#   * WavPack  — the second lossless format. Tags and art survive.
#   * WAV      — raw PCM, NO tags and NO art. The UI warns about this and the
#                warning is the point: a format that silently dropped metadata
#                without saying so is the defect.
#
# Two tracks each. The transcode path is per-file and a third track adds a row,
# not a discriminator.
#
# A DIFFERENT ALBUM TITLE PER FORMAT, so the three land in three folders and
# none of them collides with section F's archival master.

log --- K1. MP3: the lossy derived output, with a real VBR quality ---
set output_format mp3
expect output_format mp3
set mp3_vbr_quality 2
expect mp3_vbr_quality 2
select-tracks 1-2
album derived mp3 (ripper)
rip
wait-for-rip 3600
snapshot aftermp3
screenshot aftermp3
rig-check

log --- K2. WavPack: the second lossless format ---
set output_format wavpack
expect output_format wavpack
select-tracks 1-2
album derived wavpack (ripper)
rip
wait-for-rip 3600
snapshot afterwavpack
rig-check

log --- K3. WAV: raw PCM, no tags, no art - the UI must say so ---
set output_format wav
expect output_format wav
select-tracks 1-2
album derived wav (ripper)
rip
wait-for-rip 3600
snapshot afterwav
screenshot afterwav
rig-check

log --- K4. back to FLAC, the archival master ---
set output_format flac
expect output_format flac

# --- L. THE GOAL PRESETS: a label must mean what it says -------------------
# A goal is not a setting; it is a NAME for a set of them. Selecting one applies
# the whole preset, and this section proves the label and the settings agree —
# because a goal that wrote only its own name would leave the app ripping with
# exactly the settings the user was trying not to use, under a label promising
# otherwise. "Archival Exact" was byte-identical to "Fast Verified" until
# v0.6.24 for a related reason.
#
# No drive time: pure settings round-trips through the real preset code.

log --- L. goal presets: selecting a goal applies all of it ---
set rip_goal archival
expect rip_goal archival
expect secure_rerip_dynamic off
expect rerip_offset_variant on
set rip_goal portable
expect rip_goal portable
expect output_format mp3
set rip_goal fast_verified
expect rip_goal fast_verified
expect secure_rerip_dynamic on
expect output_format flac
snapshot goalsdone

# --- M. NAMING TEMPLATES ----------------------------------------------------
# The templates decide where every file lands, so a template that silently fails
# to round-trip is a library-wide defect. Pure validation, no drive time — the
# rip in section N runs on the restored default.

log --- M. naming templates round-trip through the validator ---
set track_template %A/%d/%t - %n
expect track_template %A/%d/%t - %n
set disc_template %A/%d/%d
expect disc_template %A/%d/%d
snapshot templatesdone

# --- N. §T1: A SECURE RE-READ THAT GENUINELY RE-READS — THE LONG ONE -------
# The fork's most-wanted test, and the one the whole round-13 paranoia argument
# turned on. **This is the section to leave running overnight.**
#
# WHY IT NEEDS ITS OWN SECTION. Under `-Z`, a track's own paranoia counter is the
# LAST pass while the disc block sums EVERY pass, so the two are equal exactly
# when each track was read once — and a clean disc in DYNAMIC mode converges on
# the first read, which is what every other rip in this file does. Every artifact
# either project has ever checked that claim against had that property, which is
# why a false invariant survived five handshake rounds: it is arithmetically
# forced in the only case anyone ever measured.
#
# `secure_rerip_dynamic off` is UNIFORM mode — EAC-style Test & Copy, every track
# read until two reads agree, not only the tracks AccurateRip could not confirm.
# So `total_repeats > 1` on every track regardless of how clean the disc is, and
# the fork's `Scope:` line is printed.
#
# WHAT THE INVARIANT IS, AND WHAT IT IS NOT. The property is an INEQUALITY:
#
#     sum(per-track counters)  <=  disc-level total
#
# with equality exactly when every track was read once. The tempting form —
# `disc == passes x sum` — holds on the fork's synthetic fixture BY CONSTRUCTION,
# because every pass there does identical work, and it will NOT hold on media,
# where re-reads exist precisely when passes differ. `rig-check` grades the `<=`
# and reports the multiple as an observation. Nothing here asserts the ratio.
#
# THE WHOLE DISC, not two tracks. The fork said two tracks is sufficient for the
# inequality and they are right — but they also said the interesting case is *a
# track that needed three or more reads*, and that is a property of the disc, not
# of the selection. Ripping every track is the only way to give the disc a
# chance to produce one. It costs about two hours and this run has all night.
#
# Six hours of timeout because uniform mode roughly doubles the read and this
# rig has measured 2h45m for a single dynamic pass.

log --- N. T1: uniform secure re-read, WHOLE DISC, so the counters actually move ---
set rip_goal archival
expect secure_rerip_dynamic off
expect rerip_offset_variant on
set secure_rerip_matches 2
expect secure_rerip_matches 2
rescan
pick-release 1 120
expect-tracks 2+
select-tracks all
album secure reread (ripper)
rip
wait-for-rip 21600
snapshot aftersecurereread
screenshot aftersecurereread
expect-status Done
rig-check

# --- P. §T3: THE CACHE PROBE, PROBE-ONLY ------------------------------------
# LAST OF THE DRIVE WORK, DELIBERATELY. `-x` alone has form: measured once on
# this rig (32 sectors, 73.5 KiB, uncached read 362.6 ms, 2026-08-19) and then it
# ripped the whole disc, ETA 1h 3m, leaving the drive held. `-x` is a MODIFIER;
# `-x -I` is the probe-only invocation and writes no audio — the fork states that
# in their round-13 lap 5 and round-14 lap 1 §T3, and their lap 3 §C3 confirms
# they CANNOT promise it returns the drive, because nothing in their suite has
# ever executed a single timed read (on an image the probe refuses before doing
# anything).
#
# So it is real, it is theirs to be right about, they asked for it, and it goes
# after every rip in this file: if it does hold the drive, it costs the tail of
# the run and not the rip evidence. A hang here is the finding.
#
# `-N` is present because the script sanitiser requires it of any non-probe
# invocation and it is right to — without it cyanrip runs its own MusicBrainz
# lookup and can block on a prompt with no terminal attached, which is the
# unattended hang this whole feature exists to prevent.
#
# ASSERT THE FIELD NAME, NOT THE VALUE, AND THAT IS DELIBERATE. The build under
# review REMOVED the old `%i sectors measured (…)` wording — it claimed a
# precision the method does not have. The value is now one of five forms, and
# exactly ONE is ever emitted (they are arms of a switch, each writing the whole
# buffer):
#
#     Cache probe:    %i to %i sectors (…)                    a range
#     Cache probe:    at least %i sectors, upper bound unknown (…)
#     Cache probe:    no readback cache measured (…)          measured, found none
#     Cache probe:    unknown (read failed at %i sectors, …)  could not measure
#     Cache probe:    unknown (read could not be timed …)     could not measure
#
# `no readback cache measured` and `unknown (…)` are NOT the same claim — the
# first is a measurement that found nothing, the second a measurement that could
# not be taken. On an image the line reads `not run (disc image has no drive
# cache)`, so its ABSENCE here is the first sign the probe really ran on metal.
# A script asserting any one value would fail on a correct probe.
#
# WHERE THIS EVIDENCE LANDS: the script report and the transcript, NOT the
# rig-check manifest. `-x` is not in the rip argv builder at all, so no
# Platterpus rip ever probes and no rip log can carry the line. The `cyanrip`
# verb records the exact argv, the exit code and the complete output for this
# step, which is a stronger record than a manifest row would be.

log --- P. T3: the fork's cache probe, probe-only ---
cyanrip -N -x -I
expect-exit 0
expect-cyanrip Cache probe
snapshot aftercacheprobe

# --- P2. C1: THE THIRTY-MINUTE HANG, DETECTED (NOT DIAGNOSED) ---------------
# The fork asked for this in round 14 lap 11 §K2, and the split of labour is the
# point: THIS STEP DETECTS, their `rig-c1-probe.sh` EXPLAINS. Only run their
# probe if this step hangs; if it does not hang, that is itself worth knowing —
# it says the hang is not unconditional, which no disc-image fixture could ever
# establish.
#
# WHAT IT PROVOKES. With no `-s`, cyanrip reads the TOC and refuses for want of
# a read offset. On the 2026-08-25 rig session that refusal wrote its `-j`
# diagnostics record fourteen seconds in — so the process decided to fail and ran
# its exit path all the way to completion — and then stayed alive for roughly
# THIRTY MORE MINUTES holding the drive, needing SIGKILL. Cause not determined,
# by either project. The branch is gated on a DRIVE CAPABILITY that image drivers
# do not report, so it is unreachable from every fixture either side has: it
# needs a real drive, and this is the cheapest place to put one in that state.
#
# WHY IT IS SAFE TO HAVE IN AN UNATTENDED RUN. The `cyanrip` verb is bounded —
# 300 s, then the child is killed, then a further 20 s before the runner stops
# waiting and reports an UNREAPABLE CHILD with a null exit code rather than 0.
# A hang here therefore costs five minutes and is recorded as a finding; it
# cannot eat the night. That bound is the answer to the fork's §J6, which asked
# before agreeing this step should exist at all.
#
# LAST OF THE DRIVE WORK, on §P's reasoning exactly: if it holds the drive it
# costs the tail of the run and not the rip evidence.
#
# `-l 1` is insurance, not intent. If the refusal does NOT fire on this drive,
# cyanrip would otherwise start ripping; limiting it to one track bounds the
# damage to something the verb timeout can end. In that case `expect-exit 1`
# fails and says so, which is the correct result — "it did not refuse" is a real
# finding about the rig, not a broken step.
#
# NO `-j` HERE, and the reason is worth recording rather than leaving as an
# omission. The fork's §K2 suggested one, to get cyanrip's own record as a
# channel independent of the capture. Our script language has no path
# placeholder, so a `-j` would need a hard-coded absolute path in a file whose
# whole promise is that nothing in it needs editing. It is also less necessary
# here than in their probe: this verb captures through `run_capture` — a pipe we
# drain — and not through the shell redirect whose contents went missing in
# `rig_session.sh` step 5b. Different channel, so an empty capture here would be
# a NEW finding rather than a repeat of that one.

log --- P2. C1: does a no-offset refusal hang the drive? ---
cyanrip -N -l 1
expect-exit 1
expect-cyanrip Offset is unset
snapshot afterc1

# --- Q. LEAVE THE RIG AS WE FOUND IT ---------------------------------------
# Restoring is not tidiness. Uniform secure re-read doubles every future rip on
# this machine, MP3 would make the next rip lossy, and a setting a test left
# behind is a setting nobody chose.
#
# The overread assertion is a GUARD, not a restore: this script never enables it,
# so if `force_overread` is on here something else turned it on, and that is
# worth knowing before the next disc — it reaches cyanrip's argv and on this
# drive it hangs the read.
#
# The read offset is NOT restored, because 667 is this drive's true offset (see
# section B) and putting it back to 0 would be the mis-configuration.

log --- Q. restoring what this run changed ---
set rip_goal fast_verified
expect rip_goal fast_verified
expect secure_rerip_dynamic on
set output_format flac
expect output_format flac
set mp3_vbr_quality 0
set write_eac_log_after_rip off
set debug_logging off
expect debug_logging off
expect force_overread off
expect read_offset 667
expect-dialog none
snapshot atend

log =============================================================
log DONE. Everything from this run is in ONE .tar.gz under
log ~/.local/share/platterpus/bundles/ - transcript, reports,
log screenshots, app log, rig-check manifest.
log Its path is the "SEND THIS ONE FILE" line in the app log.
log Then run:  ./platterpus-x86_64.AppImage --rig-session
log =============================================================
<<<<<<<<<< END fullacceptance.txt >>>>>>>>>>
