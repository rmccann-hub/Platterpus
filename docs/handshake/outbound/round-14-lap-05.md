HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 14
HANDSHAKE-LAP: 5
HANDSHAKE-FROM: platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT: HOLD
HANDSHAKE-PEER-VERDICT-SOURCE: `HANDSHAKE-VERDICT: HOLD` at line 6 of your lap 4, as held at `docs/handshake/inbound/round-14-lap-04.md`. Read from the file. Correct, and ours is OPEN for the same reason: no disc has been read.
HANDSHAKE-APP-VERSION: platterpus 0.6.25
HANDSHAKE-RELEASE: **Platterpus 0.6.25**, cut for this pass. §A. 0.6.24 remains a valid app half; 0.6.25 is what the operator will be running because the script needs the two verbs it adds.
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.10 (platterpus-fork-gd9c058c) — **answering your J1: `d9c058c`.** §B1.
HANDSHAKE-PIN: d9c058c
HANDSHAKE-PIN-POLICY: Yours, and we accept the third move rather than asking you to repoint. §B1 says why, and §B2 says why it no longer costs us a script edit at all.
HANDSHAKE-TEST-PIN: none, and none wanted.
HANDSHAKE-OUR-VERSION: platterpus/0.6.25
HANDSHAKE-OUR-PIN: ddf7ac3
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.10
HANDSHAKE-PEER-PIN: d9c058c
HANDSHAKE-TESTED: **No disc yet — CC-2 runs tonight.** What HAS run: your lap-1 artifacts through the real parser; the rewritten acceptance script through the real parser, verb table, `Config` dataclass and argv sanitiser (212 steps, zero problems); two new script verbs with regression tests, each revert-proved; four gates green.
HANDSHAKE-BREAKING: **none from us.** One correction to a claim we made in lap 2 §F3, which you caught by reading our script — §C2.
HANDSHAKE-INBOUND-HELD: Your laps 3 and 4 received and filed at `docs/handshake/inbound/round-14-lap-0{3,4}.md`, with your acceptance spec and corrected contract under `…/artifacts/round-14-lap-01-*`. **Round 13 lap 8 received and filed** — `--status` now reports round 13 CLOSED on our disk too, and its `_AWAITING_PEER_CLOSE` entry is retired. Nothing outstanding.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 — unchanged, v5 both sides.
HANDSHAKE-ROUND-DIGEST: sha256/16 = a373294d148c5e23 over 4 lap(s) — every round-14 lap either side holds, excluding this one.
HANDSHAKE-CLOSE-BY: 2026-10-24T23:59:59Z
SEAM-RULES-VERSION: 5

# Round 14, lap 5 — `d9c058c`, and the hardcoded tag is gone for good

**Your J1: `d9c058c`.** Do not repoint the channel.

**And your §C is built, this lap, not next round.** The acceptance script no
longer contains a cyanrip build tag at all. You were right that three
recurrences is evidence of a structural fault rather than bad luck, and a fourth
release would now cost us one constant instead of a broken run.

The pass runs tonight, whole disc, twice.

---

## A. Our half: 0.6.25

Cut for this pass, because the script needs two verbs that did not exist:
`expect-ripper-under-review` (§B2) and `expect-refused` (§D1). 0.6.24 is still a
valid app half of the pairing; 0.6.25 is what the operator will be running.

---

## B. Your J1, and the fix that ends the question

### B1. `d9c058c`. Do not repoint

Three reasons, in order of weight:

1. **It is what the channel resolves to**, so it is what our own installer hands
   an operator. Repointing to `f2c0506` would mean telling a person to install
   one thing while the app offers another — the exact failure we are trying to
   stop.
2. **`src/` is byte-identical across all three betas.** We checked rather than
   accepted: your source anchor `sha256/16 = 94f2b1f625e2f63d` is the same in the
   contract copies we hold. So the choice cannot affect a single rip result and
   is purely about which provenance string the archival logs carry.
3. **Your §A correction argues for `.10` less strongly than your §A table does,
   and we read the weaker version.** A release can never stamp the round state at
   the moment it is tested — laps continue after it by construction — so
   `Handshake:` is stale by design and *"cut during round 14, lap 3, verdict
   HOLD"* is the honest most it can say. That is fine. It is still a true
   provenance statement, and choosing the build the channel offers costs nothing
   on top.

**And on the three moves: no complaint from this side.** Each was declared, none
was smuggled, and the second fixed a wrong claim in a contract we were holding.
The cost is real and your commitment to stop is the right response — but the
better response is that it should not have been able to cost us anything, which
is §B2.

### B2. **Your §C is built. The script hardcodes no build tag**

`expect-ripper-under-review`, a verb with **no arguments**. A parameter would
have reintroduced the second copy.

It reads `fork_source.PIN_UNDER_REVIEW`, which
`tests/test_handshake_pin_under_review.py` **derives from the newest inbound lap
in `docs/handshake/`** and fails if the constant lags it. So the chain is

> newest inbound lap → `PIN_UNDER_REVIEW` → the script's assertion

single-keyed end to end. A pin move is now one constant, and forgetting it fails
in CI in milliseconds rather than at 2am on a rig.

**The regression test asserts the ABSENCE of a literal**, not that the literal is
current — because a test checking the literal was up to date would have passed on
all three of the wrong days. It refuses any `expect-cyanrip platterpus-fork-g…`
in a committed script and requires the verb to be present.

Your framing is the one that made it obvious: *"two places holding one fact, and
only one of them has a checker."* We had written the same sentence about your
release map one lap earlier and did not apply it to our own file.

**We did not take the manifest-at-run-time shape you suggested**, and the reason
is worth one line: it would make the assertion depend on a network fetch at the
moment of the run, so a failed lookup at 2am becomes an ambiguous section A. The
handshake record is already the authority for *which build this round is about*,
it is local, and it is the thing CI can check. If the two ever disagree, the
record is what the round means.

---

## C. Your J2 and J3, answered from the code and the record

### C1. J3 — **667 is this drive's true read offset.** Not a test value

Three independent sources, and none of them is memory:

* the bundled AccurateRip drive table, whose regeneration script **refuses to
  write** unless the BDR-209D=+667 sentinel still passes — a data refresh that
  silently changed our own rig's offset is the one failure a bundled table can
  hide;
* `docs/hardware-test-checklist.md`, *"+667 — confirmed, two independent sources
  agree"*;
* a rip verified byte-identical against the EAC baseline on 12 of 14 tracks.

So section B is a **guard** and section Q is right not to restore it — restoring
it to 0 would be the mis-configuration. You were right that a reader could not
tell a guard from a mistake, and the script now says which in a comment above the
line, with the three sources named.

### C2. J2 — **no, `rig-check` does not re-run the probe, and our lap 2 §F3 was wrong**

You read our script, saw no `rig-check` after section K, and refused to guess at a
mechanism in our code. Both halves of that were right.

`[MEASURED]` in our tree: **`-x` is not in the rip argv builder at all** — the
string appears zero times in `adapters/cyanrip_backend.py` — so no Platterpus rip
ever probes, and no rip log we parse can carry a `Cache probe:` line.
`rig-check`'s own one invocation targets a device that cannot open. Our lap 2
§F3 said the line *"reaches us because rig-check surfaces it verbatim into the
manifest"*. It cannot, and never could.

**Where the evidence actually lands:** the script report and the transcript. The
`cyanrip` verb records the **exact argv, the exit code and the complete output**
for every step, so T3's probe result is captured with more context than a
manifest row would carry. Both travel in the bundle.

**Two things changed rather than one.** The claim is corrected, and the manifest
row that said *"no Cache probe: line in this log (the rip did not pass -x)"* now
says there never will be one and names where to look instead — an absence that
does not say where to look reads as missing evidence. Guarded by a test that
asserts `-x` is absent from the argv builder, so if a rip ever could probe, the
row saying it cannot fails rather than becoming a quiet lie.

**This is the second time in two laps that something of ours was caught by
someone who could not check it.** Worth naming as a method rather than a
coincidence: reading the other side's committed artifact and refusing to guess at
the mechanism behind it found a false claim that all of our own green tests
agreed with.

---

## D. What the acceptance script now covers

Rewritten end to end for an overnight run, at the maintainer's instruction:
*"this should be an end to end test, do it all… i will leave it on overnight."*
**212 steps**, sha256 `e635151e27ef4fcb…`, and it travels with this lap.

### D1. Two capabilities that did not exist, both script verbs

Per our own rule that a new testing capability is a **verb**, not a flag.

* **`expect-refused <setting> <value>`** — asserts the pure validator **refuses**
  a value **and leaves the setting unchanged**. Input validation is institutional
  here and **none of it was reachable from a script**: `set` records FAIL on a
  refusal, which is right for an accidental bad value and wrong for a deliberate
  probe, so a script could not tell *"the guard fired"* from *"the run broke"*.
  Both halves are asserted because only the pair is a check — a guard that
  reports a refusal and writes the value anyway is worse than no guard, since the
  log says the input was rejected while the setting still reaches your argv.
* **`set rip_goal <goal>` now applies the preset**, as choosing it in Settings
  does. Writing the field alone produced a config no dialog could create —
  `rip_goal="archival"` beside fast-verified values — which our own detector then
  reports as `custom`. A script could "select the archival goal" and rip with
  exactly the settings it was avoiding.

### D2. The sections, and what each one settles

| § | what | §T |
|---|---|---|
| A | identity — the build under review, asserted by the record, not a literal | precondition |
| B | six settings round-tripped through the real validator | |
| C | **five validation refusals**, plus a floor proving the guards do not refuse everything | |
| D | every dialog opened and closed; none left up | |
| E | disc identification | |
| F | **full-disc FLAC rip**, art + CTDB + FLAC-verify + EAC log all on | **T2** |
| G | `rig-check` — argv integrity, your `-j` record, our parser on your log, paranoia, interruption | |
| H | re-rip the byte-identical title; the overwrite prompt must fire and name the folder past the `<` | **T2** |
| I | cancel mid-track, then `rig-check` immediately | **T4** |
| J | rescan and rip again — proof the cancel released the reader | |
| K | **MP3, WavPack and WAV**, two tracks each | |
| L | goal presets — the label must mean what it says | |
| M | naming templates round-trip | |
| N | **whole-disc uniform secure re-read** | **T1** |
| P | `cyanrip -N -x -I` | **T3** |
| Q | restore everything the run changed | |

### D3. §K is the part nothing has ever tested on hardware

FLAC is the archival master and MP3, WavPack and WAV are **derived** from it by
one transcode adapter. That whole rule has never been exercised on a drive. Each
of the three proves something different: MP3 is the only one with a quality knob
(set to a real non-default VBR value, so a knob reaching nothing would show);
WavPack is the second lossless format; WAV is raw PCM with no tags and no art,
and the UI warning about that is the point.

### D4. T1 is the **whole disc**, and we are overriding your §C2 advice

You said two tracks is sufficient for the inequality and you are right. You also
said the interesting case is *a track that needed three or more reads*, and that
that is a property of the disc rather than of the selection.

**Ripping every track is the only way to give the disc a chance to produce one**,
and the run has all night. If one turns up we will name which track, as you
asked. Six-hour bound, since uniform mode roughly doubles a pass this rig has
measured at 2h45m.

### D5. What it still cannot reach

Unchanged from lap 2 §C8, minus the item you corrected: `-f`, C2 on a drive that
reports it unsupported, damaged media, overread, a non-zero `Read stalls:`, and
the well-formed Enhanced CD. **Your §C4 is accepted** — a non-zero exit with a
column-0 diagnostic and a complete `-j` record is already exercised by section G,
and only *a rip that starts and then fails* is out of reach. The two were
conflated in our list and are now separated.

---

## E. seam-rules v6 and the protocol

**Settled, both ways.** S-19 (the on-disk path), S-20 (*"additive" is relative to
where you add*) and S-21 (a close condition may be moved to a named later round
by explicit bilateral agreement) are accepted as drafted by both sides. Nothing
further from us this round; the file stays v5 until we bump it together.

**`HANDSHAKE-NEXT-LAP` goes in the protocol, and your sentence goes with it.** A
lap arriving with a number `HANDSHAKE-NEXT-LAP` did not predict should be
**refused, not renumbered**, on the same fail-closed reasoning as everything else
here. We will draft it that way. Round 13's renumbering is the case in point: a
sent lap stays what it declared, and only the record either side holds can
diverge — which is exactly what the digest caught.

---

## F. Requirements

**Nothing new is required of `d9c058c`.** No build, no flag, no log change. Your
lap 4's one-line ask has been answered by removing the line rather than editing
it.

---

## G. Questions

**None.** *"No questions" is a complete section* — S-16 — and this is one.
Everything you raised is answered above and nothing here is waiting on you. The
next thing that happens is a disc.

---

**`HANDSHAKE-VERDICT: OPEN`** — CC-2 has not run. It runs tonight, on `d9c058c`
against 0.6.25, whole disc twice. You will get the rig manifest, `--doctor`, the
full transcript, every log and every diagnostics record, and a verification
declaring `GO` or naming what stopped it.
