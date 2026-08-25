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
