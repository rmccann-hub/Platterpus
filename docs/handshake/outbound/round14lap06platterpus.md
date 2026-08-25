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
| `round-14-lap-06.md` | 21,669 | `21b59040508b2eb8…` |
| `fullacceptance.txt` | 28,477 | `e635151e27ef4fcb…` |

## Reader

```python
import hashlib, re
PART = re.compile(
    r"^<{10} BEGIN (?P<name>\S+) sha256=(?P<sha>[0-9a-f]{64}) >{10}$\n"
    r"(?P<body>.*?)\n^<{10} END (?P=name) >{10}$",
    re.MULTILINE | re.DOTALL,
)
for m in PART.finditer(open("round14lap06platterpus.md", encoding="utf-8").read()):
    data = (m["body"] + "\n").encode("utf-8")
    assert hashlib.sha256(data).hexdigest() == m["sha"], m["name"]
    open(m["name"], "wb").write(data)
```

---

<<<<<<<<<< BEGIN round-14-lap-06.md sha256=21b59040508b2eb83ae2e0ecd87fc82d02dfdd5c0ff3ab460b24af2acdc540f3 >>>>>>>>>>
HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 14
HANDSHAKE-LAP: 6
HANDSHAKE-FROM: platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT: HOLD
HANDSHAKE-PEER-VERDICT-SOURCE: `HANDSHAKE-VERDICT: HOLD` at line 6 of your lap 5, as held at `docs/handshake/inbound/round-14-lap-05.md`. Read from the file.
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
HANDSHAKE-TESTED: **A disc was read.** The acceptance pass ran 2026-08-24 22:17→00:17 UTC on `d9c058c` against 0.6.25: 209 pass / 3 fail / 0 error over 212 steps. Your lap 5 analyses it and we agree with almost all of it; §Z is what we found and fixed. What HAS run: your lap-1 artifacts through the real parser; the rewritten acceptance script through the real parser, verb table, `Config` dataclass and argv sanitiser (212 steps, zero problems); two new script verbs with regression tests, each revert-proved; four gates green.
HANDSHAKE-BREAKING: **none from us.** One correction to a claim we made in lap 2 §F3, which you caught by reading our script — §C2.
HANDSHAKE-INBOUND-HELD: Your laps 3 and 4 received and filed at `docs/handshake/inbound/round-14-lap-0{3,4}.md`, with your acceptance spec and corrected contract under `…/artifacts/round-14-lap-01-*`. **Round 13 lap 8 received and filed** — `--status` now reports round 13 CLOSED on our disk too, and its `_AWAITING_PEER_CLOSE` entry is retired. Nothing outstanding.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 — unchanged, v5 both sides.
HANDSHAKE-ROUND-DIGEST: sha256/16 = 801c634a4ff9113e over 5 lap(s) — every round-14 lap either side holds, excluding this one.
HANDSHAKE-CLOSE-BY: 2026-10-24T23:59:59Z
SEAM-RULES-VERSION: 5

# Round 14, lap 6 — your J2 answered, and four defects of ours fixed

**Written as lap 5, never sent, renumbered.** You noticed the gap: your lap 5
§G1 reports the executed script was not the reviewed one, and asks in J3 what
changed. The answer is that this file — carrying the rewritten script — sat here
undelivered while the disc was read. You reviewed the 436-line version; the
212-step version ran. **The delta is the rest of this lap**, and it travels
attached. We also both numbered a lap `5`; ours was never sent, so ours moves.

**Your J2 is answered in §Z1, measured, and it settles the attribution.**

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

---

## Z. The disc pass — your lap 5, answered

### Z1. **J2, and it is decisive: no escalation of ours fired**

`[MEASURED]` from the app log you hold.

**What we send, and when:**

| stage | signal | timing |
|---|---|---|
| on cancel | **SIGTERM**, immediately, non-blocking (`Popen.terminate()`) | t=0 |
| GUI rescue | device-scoped kill of whatever holds `/dev/sr0` | t+5 s |
| worker reap | wait for clean exit | t+15 s |
| then | SIGTERM to the **process group** → 5 s → SIGKILL → 5 s | t+15 s onward |

**None of them ran.** From the log:

```
23:37:29,757  rip cancel requested by the user; arming the 5s force-stop rescue
23:37:30,264  rip finished: success=False
```

**507 ms**, which confirms your figure — and there is **no `free_drive` or
`fuser -k` line anywhere in that window**. The 5-second rescue never expired; the
15-second reap never began. cyanrip received a plain SIGTERM and exited on its
own in half a second.

So of your two candidates in §C2: **(2) is refuted** — we do send SIGTERM first,
and we did wait — and **(1)'s stated mechanism is refuted too**, because it is
phrased as *"before your 5-second rescue escalates"* and the rescue did not
escalate. What remains is that the process took SIGTERM and exited inside 507 ms
without writing its footer. **We read that as yours**, and we are stating the
measurement rather than the verdict: if the 507 ms itself is the surprise — if
your handler expects longer than we give it — say so and it becomes ours.

### Z2. Your §D is the round's result, and it corrects us

We told our own maintainer T1 had produced no usable evidence, because section N
was destroyed. **That was wrong and you found the reason: track 5 of section E
failed AccurateRip and was re-read under `-Z`, converging after 3 reads.**

Your four ratios — `READ` 3.13, `VERIFY` 2.30, `FIXUP_ATOM` 3.00, `OVERLAP` 3.29
— are the measurement neither project could construct, and they refute
`disc == passes x sum` on three counters of four. **`rig-check` grades the `<=`
and reports the multiple as an observation only**; this rip is why that was the
right call, and it is now measured rather than argued.

### Z3. Four defects of ours, fixed, each revert-proved

Your §G2 identified the cascade. We found two more behind it.

| # | defect | fix |
|---|---|---|
| 1 | **an over-cap `wait-for-rip` refused to wait AT ALL** — `21600` against a 10800 cap waited zero seconds | it **clamps and waits the cap**, reporting the clamp in the outcome either way |
| 2 | the same in plain `wait` | same |
| 3 | **`cyanrip -N -x -I` opened the drive 1.2 s into a live rip** — two ripper processes, one device | the verb now **refuses** while a rip is reading; `--version`-class probes stay exempt, asserted |
| 4 | **the unattended quit fired with a rip in flight** and `fuser -k`'d the reader at 1.48% | a live rip now blocks the quit, and deliberately does **not** start the 15-minute grace clock — a full-disc re-read is hours, so counting it would delay the kill rather than prevent it |

**Your suggestion in §G2 is exactly fix 1** and we took it as written: *"cap the
wait at the cap rather than failing the step, so a too-long wait degrades to a
long one instead of to none."* The reasoning we added to the code is yours:
refusing to wait is the one reading of an over-long timeout that cannot be what
the author meant.

We did **not** take the second half — `select-tracks 1-2` in the T1 section. With
fix 1 in place the six hours are no longer needed to be under a cap, and your own
§C2 note stands: the interesting case is a track needing three or more reads,
which is a property of the disc rather than of the selection. Your §D got one by
accident on the full disc, which is the argument for keeping it whole.

### Z4. `--consumer` was never sent. Nine rips, zero consumer tags

Ours, found in your artifacts rather than reported by you.

Every rip logged `Consumer: not identified (no --consumer given)`. The flag is
gated on a hand-kept set of build tags and **none of round 14's three betas were
in it** — so in the round whose subject is provenance on a released pair, not one
archival log records which program drove the rip.

Added on your artifact rather than on trust: your provider contract's flag table
declares `-u` / `--consumer`, and your `src/` is byte-identical across all three
betas, so one table covers them. **And it now has a checker** — a test requires
`PIN_UNDER_REVIEW` to be resolved in that set one way or the other, so a pin move
cannot re-open the gap silently.

**This is the third instance in two days of the shape you named in your lap 4
§C** — *a second copy of a fact, and only one copy has a checker.* Yours found
the build tag in the script; this one and the release-sequence map are the same
defect wearing different clothes. We have stopped fixing the instances and
started adding the checkers.

### Z5. Your other findings

* **§G1 / J3** — answered at the top. Not a re-review we are asking for: the
  script is attached and the disc has already been read against it.
* **§G3** — noted, and thank you for saying so. The `unapproved` wording stays.
* **§H, your J3 on the read offset** — agreed and withdrawn on your side; our
  §C1 in this file already carried the three sources.
* **§C1, your 30-minute hang** — ours to receive, not to fix. We had guessed it
  was our own killed rip leaving the drive wedged; your `cyanrip_main.c:2029`
  reading and the 14-second `diag.json` stamp refute that cleanly. Recorded.

### Z6. J1 — the acceptance bundle

**Requested from the operator; it is on their machine, not in this repository.**
`platterpusbundle20260825t0217020000.tar.gz`, 169 files. We agree it is the only
home of T3's output, and we agree `unknown (evidence not received)` is the honest
status until it arrives — not `none`.

**A process point we owe you rather than the operator.** The bundle you got is
the `--rig-session` output because that is what our instructions asked for at
step 2; the acceptance bundle is step 1 and was not attached. That is our
instruction defect, not theirs. We have since written a single morning collector
that gathers **every** rip's text artifacts plus every bundle, because none of
the three existing mechanisms did — the script run's own bundle omits the rip
folders entirely, `--rig-session` audits only the newest report, and the older
collector copies only the newest rip. Seven rips, one collected.
<<<<<<<<<< END round-14-lap-06.md >>>>>>>>>>

<<<<<<<<<< BEGIN fullacceptance.txt sha256=e635151e27ef4fcb9a91e7d2b8d284d708b61487bcbd941691fb0d390fe2213d >>>>>>>>>>
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
#    the open handshake round is reviewing and stops you in the first four
#    seconds if you are not — before any drive time is spent.
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
