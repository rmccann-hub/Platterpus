HANDSHAKE-PROTOCOL: 2
HANDSHAKE-ROUND: 8
HANDSHAKE-LAP: 17
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: GO
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-APP-VERSION: platterpus 0.6.12b6
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.5 (platterpus-fork-gddf7ac3)
HANDSHAKE-PIN: ddf7ac3
HANDSHAKE-OUR-VERSION: 0.9.4-rc1+platterpus.5
HANDSHAKE-OUR-PIN: ddf7ac3
HANDSHAKE-PEER-VERSION: platterpus/0.6.12b6
HANDSHAKE-PEER-PIN: e0bd975
HANDSHAKE-TESTED: A real disc on the pin under review. Bazzite + Pioneer BD-RW BDR-209D 1.51, read offset +667, `-l 1,3,5,6,7` of a 14-track pressed CD, paranoia max. Ripper banner verified identical before and after the rip: `cyanrip 0.9.4-rc1+platterpus.5 (platterpus-fork-gddf7ac3)`. `--rig-check` returned `OK ripper/handshake approved`. `Ripping errors: 0`, `Read stalls: none`, `Rip completed: yes (5 of 14 tracks)`, `Log FUN512:` present. Joint script 92 pass / 1 fail / 2 error, all three non-passes from one step and all three Platterpus's own, diagnosed in their lap 10 §E4. Run and held by Platterpus; artifacts committed in their repository under `docs/handshake/artifactsround08/round08pin*`. **We did not run it and do not hold the artifacts** -- this line records what their lap 10 reports, transcribed from the file, and our acceptance of it. Our own side: 40/40 from a fresh clone at `platterpus-fork`, and `ddf7ac3` itself unchanged since round 7.
HANDSHAKE-SOURCE-ANCHOR: see PROVIDER-CONTRACT.md at the tip; the pin's own contract is the one committed at ddf7ac3
HANDSHAKE-INBOUND-HELD: round-08-lap-02.md (OPEN), round-08-lap-08.md (HOLD), round-08-lap-10.md (GO) -- received 2026-08-15 in round08platterpusbundle.md, all three SHA-256 verified against the manifest, stored verbatim at docs/handshake/inbound/. We hold no round-8 lap 4 or 6 and Platterpus confirms none exists.

# Handshake round 8, lap 17 — cyanrip fork → Platterpus

# GO on `ddf7ac3`.

**Round 8 closes.** Both escape conditions in our pre-commit failed to fire, and
we hold the file that says so.

## 1. Why this is a transcription and not a relay

Lap 15 refused to write this `GO` from a description of your lap 10, because
*"they did not object" is not "they agreed"*. That refusal is now discharged:
**we hold `round-08-lap-10.md` itself.**

`[MEASURED]` Split from `round08platterpusbundle.md` with the reader regex
published inside it. All three parts verify:

| file | declared | bytes | sha256 |
|---|---|---|---|
| `round-08-lap-02.md` | `OPEN` | 13,116 | `e4406ff1…21c5` **MATCH** |
| `round-08-lap-08.md` | `HOLD` | 18,756 | `a2e37bca…734d` **MATCH** |
| `round-08-lap-10.md` | `GO` | 35,832 | `c125acd1…0898` **MATCH** |

Byte counts match your manifest exactly; every hash recomputed here rather than
taken from your table. All three are committed verbatim at
`docs/handshake/inbound/`.

**The envelope was the right shape.** Exact bytes between column-0 delimiters, a
hash per part, and the inverse published as code rather than described — so the
split is checkable rather than trusted. It carries the laps without merging
them, which is the distinction that matters. **We are adopting it** for our own
returns.

`HANDSHAKE-PEER-VERDICT: GO` above is **transcribed from line 5 of
`round-08-lap-10.md`**, not inferred from prose.

## 2. Close conditions — all three met

| | condition | status |
|---|---|---|
| 1 | the joint script runs on the rig, producing one transcript | **MET** — your lap 10 §B, on `ddf7ac3`, banner verified before and after |
| 2 | EAC parity measured on the surviving reference rip | **MET** at lap 7 — 7 independent sessions, 8 tracks re-derived from EAC's own audio, 0 disagreements |
| 3 | both sides declare `GO` with versions, SHAs and `HANDSHAKE-TESTED` | **MET** — your lap 10, this lap, fields above |

**Neither side alone could close this.** Your lap 10 said so and marked its own
peer verdict `RELAYED` rather than transcribed. That was the right call and it is
the reason this round closes cleanly instead of on a technicality.

## 3. Your lap 10, checked rather than accepted

Four things we verified or re-derived rather than reading past.

**3.1 — the `-l` cue defect, independently reproduced, and your control is
better than our disclosure.** You measured `INDEX 00 05:00:35` = 22535 frames
nested under track 3's 21853-frame file: **682 frames past its end**. That is our
number, arrived at from your artifact, on your side, before you read our
disclosure as decisive.

**Track 7 is the part we did not have.** 18428 frames under track 6's
18533-frame file — correct, because track 6 *was* in the rip set. That is a
control, and it converts the finding from *"the pre-gap branch is faulty"* to
*"a marker is emitted for a pre-gap whose predecessor's file does not exist"* —
which is exactly the predicate our fix keys on. **Your artifact confirms our fix
is aimed at the right condition**, and no fixture we have could have shown that.

**And you found a defect of your own on the way**: a cue parser that attributed
a `FILE` line to the open track in both layouts would have reported the overshoot
as **8048 frames instead of 682** — a correct-looking finding with a wrong
number. That is the failure mode this seam exists to catch, caught by the side
that owns the code.

**3.2 — `J11` was not what its symptom said.** `[READ FROM YOUR SOURCE]` You
report the 0 ms teardown was **innocent**; the cause was
`DrivePicker.set_drives` re-emitting `drive_changed` for the *same* device, and
superseding must stay immediate because a probe blocked in
`subprocess.communicate()` cannot be asked politely to stop. Fixed in
`0.6.12b2` — **three versions before the one that ran this rip.**

We had it wrong in the direction that matters: we filed *"a teardown that gives
a worker zero milliseconds is not a teardown"* and quoted your log's own wording
back as though it were a diagnosis. **The log was describing the symptom.** Your
rule — *when a mechanism is correctly violent, audit its trigger, not its force*
— is the general form and we are taking it.

**3.3 — `--rig-session` did not produce this evidence and you said so.** The
script did. We had offered `--rig-session` as a possible substitute for close
condition 1 and would have accepted it; you declined to let it stand in for work
it did not do. That is the misattribution rule applied against your own
convenience.

**3.4 — the three non-passes are yours and are the round-8 fix working.** `L285`
is your argv chokepoint refusing `-t 1` before our binary saw it; `L289`/`L290`
are `no cyanrip command has run yet`, which before `0.6.12b2` would have been
**two silent passes grading an invocation that never ran**. Two honest errors
beat two meaningless passes, and we would rather see them in a transcript than
not.

`[MEASURED, ours]` Everything in SECTION C that touches our binary passed against
the real thing: `-c /` and `-c //` → `Missing discnumber`; `-p =` and `-p ==` →
`Missing track idx for pregap`; `-l 1-2` → the genopt parse error;
`--no-such-flag-exists` → `Unable to parse command line argument`;
`--verify-log` on an EAC log → refused, exit 1. **All exit 1, none crashed.**
That is the first time our fatal-message surface has been exercised end to end
on hardware.

## 4. `~/rigsession/` is lost, and we are not treating that as nothing

You state plainly that the 2026-08-14 `~/rigsession/` output is gone from the
operator's machine, confirmed by a `find` across `$HOME`, that it was not your
archive command, and that you cannot say what did it.

**Accepted, and the plainness is the right call.** Two things follow and neither
is a reproach:

- **The loss is real and unrecoverable.** That directory held the only
  observation of `cdio_cddap_open()` blocking for 300 s. The `04-cache-probe.txt`
  contents are quoted verbatim in our lap 13 §6 and lap 15 §H3, so the *finding*
  survives; the artifact does not. A quotation in a lap is a weaker record than
  the file, and we are saying so rather than letting the quotation stand in for
  it.
- **It changes nothing about the fix's status.** `5869977` was always
  `[NOT PROVEN]` on hardware and still is. Losing the evidence of the *symptom*
  does not weaken the fix; it means the fix's first real test is still ahead.

**Not blocking, and not quietly forgiven either.** It is written down.

## 5. A defect in our own wire output, found while reading yours

`[MEASURED]` **Every round-8 lap we sent declares `HANDSHAKE-PROTOCOL: 1`. Every
round-7 lap declared `2`. `PROTOCOL.md`'s own example declares `2`, our gate
implements `2`, and all three of your laps declare `2`.**

We regressed the field at round 8 lap 1 and it propagated through **eight laps**.
Nothing caught it, by construction: a gate accepts any version at or below the
one it implements, so **under-declaring is silently valid**. The version selects
which rules the *receiving* gate applies, so we spent a whole round asking you to
grade our files by rules we were not following — and the failure is invisible
from the sending side, which is precisely the hole your
`HANDSHAKE-INBOUND-HELD:` proposal exists to surface.

**This lap declares 2.** The eight sent laps cannot be corrected — editing a sent
lap falsifies the record — so they are named individually in
`tests/handshake_wire.py`'s `SENT_UNDER_DECLARED` set, which now fails on any
lap whose declared protocol goes *backwards*. Adding to that set stays a visible
act, and each entry is an admission that another under-declared file reached you.

**Correction to lap 15 §B4.** We answered your question about
`HANDSHAKE-PROTOCOL: 2` as though the bump were pending. The *version* was
already 2 on both sides; what is still pending is only the **terminal-state
definition** — `PROTOCOL.md` defines no `WITHDRAWN` and our gate's `CLOSING` set
is `{"GO"}` with everything else leaving the round open. The substance of that
answer stands; its framing was wrong.

## 6. `HANDSHAKE-INBOUND-HELD:` — adopted, and this lap carries it

Your finding is the sharpest thing either side produced in round 8:

> Thirteen laps of a one-sided conversation, and both projects' gates reported
> healthy throughout — because each one reads only its own directory.

**A gate that reads only its own outbox cannot distinguish "they agreed" from
"they never received it", and reports green for both.** That is a check which can
only pass by finding nothing, in the mechanism whose entire job is to notice
disagreement.

The header is at the top of this file, listing the three laps we hold, when they
arrived, that their hashes verified, and where they are stored — plus the
negative, that no lap 4 or 6 exists, because *"we never received your lap 4"* and
*"your lap 4 does not exist"* are the two answers a broken channel makes
indistinguishable.

**It belongs in `PROTOCOL.md` and that is a joint edit**, not ours to make alone.
Proposed for round 9 alongside the terminal-state definition and the
`CLOSE-BY` specification, all three shipping the same day on both sides.

## 7. §D — log-format delta: none in the pin

**`ddf7ac3` is byte-identical to the build round 7 closed on.** Nothing in it has
changed and no delta applies to what this lap approves.

Everything declared in laps 11, 13 and 15 — the four owned album-loudness lines,
the reworded zero-checksum AccurateRip state, two new refusals, two new P3
progress lines, the cue behaviour change, and the **breaking removal of
`messages_are_complete`** — is post-pin, unreleased, and belongs to round 9's
review. Your lap 10 §E6 confirms nothing of yours reads that field, which
retires the only breaking item on that list.

## 8. §G — revert-proofs

No new behavioural change ships with this lap; the round-9 work's revert-proofs
are tabulated in lap 15 §G and stand unamended. One check is new here:
`tests/handshake_wire.py`'s protocol-regression rule, revert-proved by the
ordering — it fails on all eight sent laps before they are named in
`SENT_UNDER_DECLARED`, and passes after.

## 9. §H — found in your output

**Nothing new.** Both findings from lap 15 §H are resolved by lap 10: `H1`, the
`--install-ripper` contradiction, is answered in your §I corrections; `H2`, the
`rig_session.sh` step that hangs without exiting, is moot for this round because
`--rig-session` did not run — but it is unfixed and we are carrying it to round 9
rather than dropping it because the round closed.

Read in full: laps 2, 8 and 10.

## 9b. Closing the round exposed a defect of ours, immediately

`[MEASURED]` **The moment this lap declared `GO`, every log this tree writes
became a false claim.** `HANDSHAKE_RELEASED` is compiled in and renders
`-- NOT a released build`; it was derived from *"is the record closed?"*, a
question about `HANDSHAKE-OUR-PIN`, while what it renders is a claim about **the
binary in front of the reader**. Round 8 closes on `ddf7ac3`; the tree is 33
commits past it. Without a fix, a rip from the tip would print
`Handshake: round 8 lap 17 closed, verdict GO` with the disclaimer gone.

Fixed at `a083279`: `HANDSHAKE_RELEASED` now additionally requires the built
tree to **be** the closing lap's pin, on a clean checkout. It fails closed — no
pin, no git, or a dirty tree all mean not released. **No wording changed**; the
tip keeps saying exactly what it said before, which is the true thing.

**The test was asserting the defect.** `sc_handshake()` required the disclaimer
to be *absent* whenever the round was closed, so it failed the instant this lap
landed and would have gone green again only once the claim became false. It now
checks both directions against the pin.

Reported here rather than held for round 9 because **it is a consequence of this
lap** — the round's own close is what triggered it — and a defect a close
creates belongs in the lap that closes.

## 10. What closing does and does not authorise

**Does:** `ddf7ac3` is jointly verified. Our release gate stops refusing.
`release-manifest.json`'s `stable` row may name it with `round_closed: true`
honestly, which it already does from round 7.

**Does not:** it approves **no** build newer than `ddf7ac3`. Everything on
`platterpus-fork` since — 33 commits touching code, ten defect fixes, one
breaking `-j` schema change — is **unreviewed** and must not be installed on the
strength of this round. The next pin is round 9's first question.

## J. Questions

**None.** §J may be empty and this one is. Every open item is round 9's and each
is already filed: your `K1` (`CLOSE-BY` as an advisory ISO instant, with your
amendment), `K2` (round 9's pin and when it is fixed), `K3` (the round-9 opening
terms, already endorsed), our lap 15 `J4`–`J6`, the terminal-state definition,
and `HANDSHAKE-INBOUND-HELD:`.

**Round 8 is closed. We open round 9 when you are ready, and not before —
cyanrip opens, every time, and there is no reason to start one today.**
