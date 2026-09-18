HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 21
HANDSHAKE-LAP: 6
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-READY-TO-READ: yes — a verification file, not a lap: it is not sent and adds nothing to your inbox
HANDSHAKE-READY-TO-READ-NOTE: **Your lap 5 says *"lap 6 does not exist"* and this file does not contradict it.** It is numbered 6 because our own gate reads a round's state from the newest file on each side and the numbering is per-round, not per-inbox — the same convention as `verified/round-20-lap-04.md`, which your round-20 lap 3 also declared last. It is never transmitted, never enters your `inbound/`, and is not counted in `HANDSHAKE-ROUND-DIGEST`. **If this had been a sendable lap the number would have collided with yours, which is exactly K1.**
HANDSHAKE-VERDICT: GO
HANDSHAKE-VERDICT-NOTE: **GO on 3952c03, unchanged from our lap 4 and carried here so the gate can read a closing verdict off our own side.** Nothing was re-decided. The evidence is the 2026-09-17T23:36:51Z whole-disc `fast_verified` rip on the test pin: `Ripping errors: 0`, 14 of 14 tracks, 13/14 exact against AccurateRip and the fourteenth matching the +450 offset variant at confidence 200, your `--verify-log` returning *checksum valid*, our parser reporting 0 unrecognised lines, and 0 errors and 0 warnings in the application log.
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-PEER-VERDICT-SOURCE: `HANDSHAKE-VERDICT: GO` at **line 9** of your lap 5, filed here at `docs/handshake/inbound/round-21-lap-05.md` (sha256 `9c69fce540f8e75115baa95f3fdd6930c7e64ab484cb16e79b67384b875d8ba0`, 35,198 bytes). Line number from `grep -n`, not transcribed. Its release cell is at **line 36** and reads `yes — released by the operator (rmccann), 2026-09-18`; **all four declarations were verified before the body was opened**, which is the rule and is why they are quoted here rather than summarised.
HANDSHAKE-APP-VERSION: platterpus 0.6.50
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.12 (platterpus-fork-gfe4d2c4)
HANDSHAKE-PIN: fe4d2c4
HANDSHAKE-PIN-POLICY: **Unmoved for the whole round, and neither side asked it to move.** `release_seq` 22, stable. A close authorises a release; it does not perform one, and it does not move a pin.
HANDSHAKE-TEST-PIN: 3952c03
HANDSHAKE-TEST-PIN-NOTE: **Never moved after your lap 1 agreed it, per R4/S-15**, and it **does not become a release** — your §6a, stated in your lap 5 and recorded here so our record cannot later read it as a promotion.
HANDSHAKE-OUR-VERSION: platterpus/0.6.50
HANDSHAKE-OUR-PIN: 4bedb45
HANDSHAKE-OUR-PIN-SOURCE: derived by `scripts/handshake.py::our_pin`, re-run for this file rather than copied from lap 4 — a field carried forward is a field nobody checked.
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.12
HANDSHAKE-PEER-PIN: fe4d2c4
HANDSHAKE-PEER-PIN-SOURCE: resolved in your tree, not transcribed.
HANDSHAKE-TESTED: **Hardware, on the test pin.** One whole-disc `fast_verified` rip, 2026-09-17T23:36:51Z: The Police — *Every Breath You Take: The Classics*, 14 tracks, 59:42.57, Pioneer BDR-209D rev 1.51, read offset +667, Platterpus 0.6.50 (build `4bedb45`), banner `cyanrip 0.9.4-rc2+platterpus.12 (platterpus-fork-g3952c03)`. Ripper log 1,156 lines, 39,261 bytes, sha256 `960169b78667781e050fa09a79d419b995c87a712dea193e52efc755a9739ad1`. **And the first attempt at this session was VOID** — 247 of 247 green on the *release* pin, which is our defect and is §0.1a of our lap 4. Recorded here because a verification that names only the run that worked describes a better process than the one that happened.
HANDSHAKE-FROM-COMMIT: 5ea3d2c
HANDSHAKE-FROM-COMMIT-NOTE: The squash merge that carried our released lap 4 to `main`, and the commit this verification was written against. A file cannot name the commit containing itself.
HANDSHAKE-BREAKING: **None from us, and the two received were announced in your lap 1 and are unchanged in `3952c03`.** `REPORT_SCHEMA_VERSION` is unchanged at 24; no parser, argv builder or adapter changes behaviour you see.
HANDSHAKE-INBOUND-HELD: your round-21 laps **1**, **3** and **5**, all SENT and all filed byte-exact — lap 1 (sha256/16 `28f9e40933e7f971`, 20,711 bytes), lap 3 (`f6f9524ebf80641b`, 21,720 bytes), lap 5 (`9c69fce540f8e751`, 35,198 bytes). **Your split is in force here**: this field now carries sent laps only.
HANDSHAKE-INBOUND-OBSERVED: **none, and the field is written out rather than omitted.** Nothing of yours is held-and-observed: lap 5 was released before we read it, so it went straight to the field above. The one entry this field ever had was ours to cause, not yours — see your `-HISTORY` cell.
HANDSHAKE-ROUND-DIGEST: sha256/16 `9e1bd1da1c5bb5c6` **over 5 lap(s)** — `python3 scripts/round_digest.py 21`, covering laps 1–5 in both directions and **excluding this file, which is not a lap**. Your lap 5 declares `34ee5bd1e7a3bf8e over 4`, which is correct of the population it names; ours adds your lap 5 because it is now sent. **Both of your published values reproduce here exactly** — `4c70113a594df502 over 3` and `34ee5bd1e7a3bf8e over 4` — from an implementation built from your written spec that has never read your code.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=accff838cb32c99f3e49443ce3a28e98ed7f797a44aae02585be9415deef7397
HANDSHAKE-SHARED-HASHES-SOURCE: re-derived here with `sha256sum` over our four copies, not carried from lap 4, and equal to the values your lap 5 declares. **No shared document moved in this round**, by either side.
HANDSHAKE-CLOSE-BY: 2026-10-20T23:59:59Z
HANDSHAKE-NEXT-LAP: **none. Round 21 is CLOSED at five laps, `GO`/`GO`.** This file is a verification, not a lap. Round 22 is yours to open under §1a.
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.12

SEAM-RULES-VERSION: 5
OWNERSHIP-VERSION: 2

---

# Platterpus verification · Round 21 — **CLOSED, `GO`/`GO`, at five laps**

**GO on 3952c03** — and on `fe4d2c4`, which did not move all round. Both sides
declare `GO`; the round is closed at five laps.

**Not sent, and that is the whole shape of this file.** It exists so our own gate
can read a closing verdict from our own side rather than inferring one, and so the
round's record survives the session that produced it. Everything substantive was
said in our lap 4, which is released, immutable and on `main` at `5ea3d2c`.

## What closed the round

| | |
|---|---|
| their lap 5 | `GO` on `3952c03`, released by their operator 2026-09-18 |
| our lap 4 | `GO` on `3952c03`, released by ours the same day |
| test pin | `3952c03` — agreed at their lap 1, **never moved**, and it does not become a release |
| release pin | `fe4d2c4` — unmoved, and neither side asked it to move |
| laps | five, against three for rounds 17–20 |

**Both close conditions were answered and neither grew.** §0.2 by our refusal,
which they accepted. §0.1 by one whole-disc `fast_verified` rip on the test pin —
**after a first attempt that ran on the wrong build and established nothing.** R1
held: three conditions at lap 1, three at lap 5, no fourth.

## The two extra laps, and neither was a moving finish line

Round 21 ran five laps where 17–20 ran three. Their lap 5 and our lap 4 agree on
the accounting and we are recording it rather than leaving it to be re-derived:
lap 3 exists because our lap 2 arrived before a drive could, and lap 5 because
each gate reads a round's state from its own newest lap. **The avoidable one is
ours** — had the session been scheduled before §0.2 was answered, lap 2 would have
carried both answers and the round would have been three. That is a scheduling
fact about our operator, not a protocol cost.

## What this round cost us, recorded because a close is the wrong place to go quiet

* **A full acceptance session, void.** 247 of 247 green on the release pin while
  the round's condition was about the test pin. The guard existed, was called, and
  passed — and the note retiring the premise it rested on was written by us one
  screen away. Fixed at `0950f05`, revert-proved.
* **Three challenges resolved against us**, ledger rows 17–19: a false claim about
  rounds 13 and 14 that our own fixed tool would have withdrawn; a close condition
  whose wording our own code documents as unsatisfiable; and a diagnosis one step
  too shallow. No round-21 challenge ran the other way.
* **A stale hash we caused**, by revising a held lap after they had recorded its
  digest — which produced their `HANDSHAKE-INBOUND-OBSERVED` split, adopted on both
  sides the lap it was proposed.

## What the close does NOT authorise

`--release-gate` now exits 0. **That authorises a release; it does not perform
one, and it does not move a pin.** Their words, and we are repeating them here so
our own record cannot later read a close as a promotion. `3952c03` is a test pin
and stays one.

**And their standing caveats are carried, not filed away:** C2 is `UNREACHABLE` on
this drive; `-f`, damaged media and CD-TEXT from a physical disc are not yet done;
the encoder-failure arm has never run on hardware; and §4b's cache-probe
calibration series is unrecorded — **so their cache figure is not to be cited.**
A closed round changes none of that.

## Round 22

Theirs to open under §1a, carrying **K1** (a lap number claimed on release rather
than on writing) and the held-lap warning-channel rule. **K2 is done on both sides
already.** Ours to bring: the `defeat_audio_cache` provenance asymmetry they found,
`a_round_is_reviewing_a_build()` returning `False` for a round whose subject is the
test pin, the `rip_audit` completion grading, and the `--consumer` accept-set that
ships inside a release.
