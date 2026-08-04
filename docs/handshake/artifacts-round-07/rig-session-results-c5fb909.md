# Rig session results — Platterpus `v0.6.4b4` + cyanrip `c5fb909`

*2026-08-04, Bazzite + Pioneer BDR-209D. The EAC baseline disc (The Police,
*Every Breath You Take: The Classics*, 14 tracks, DiscID `E20DFE0E`).*

**Every value below is read out of the artifacts, not off a checkbox.** The returned sheet
had only P0's three lines ticked; where a field can be derived from a committed file, this
record derives it and says which file. Where nothing ran, it says **NOT RUN** rather than
leaving a blank — a blank reads as a pass.

---

## ⇒ Headline: 14/14 bit-perfect against EAC

```
$ python3 scripts/eac_parity.py \
      output_reference/EAC_flac/eac_baseline_police_classics.log \
      <rip>/Every_Breath_You_Take__The_Classics.log

  Track  1..14: PASS   (every candidate CRC equals EAC's)
  → 14/14 tracks match — PARITY ✓
  (an auto-fix addendum was applied: ….platterpus-addendum.txt)
```

**And the first run of that command said 13/14.** That was our tool, not the rip — §5.

---

## A. The pair, verified at the drive

| | value | source |
|---|---|---|
| Platterpus | `0.6.4b4`, build `c7aa67c` | Help → About, and the EAC-compatible log's header |
| cyanrip | `0.9.4-rc1+platterpus.5-beta.2 (platterpus-fork-gc5fb909)` | rip log line 1 |
| drive | `PIONEER  BD-RW   BDR-209D 1.51 SCSI CD-ROM` | rip log |
| read offset | `+667 samples` | rip log |
| binary path | `/usr/local/bin/cyanrip` (inside the container; host export is `~/.local/bin/cyanrip`) | `Invoked as:` |

**Banner verified: yes.** No `-dirty`, no `-grelease`, no `-gunknown` — the three shapes
that mean the tag does not describe the binary.

### The report's provenance block

| field | value | verdict |
|---|---|---|
| `ripper_build` | `platterpus-fork-gc5fb909` | ✅ |
| `ripper_handshake_approval` | **`unapproved`** | ✅ **correct** — no round has approved a test pin, and the detail names `c5fb909` and says a test-pin sighting during a test session is expected |
| `ripper_handshake_note` | `round 7 lap 20 OPEN, verdict HOLD -- NOT a released build` | ✅ `lap 20`, not 21 — a commit cannot contain the hash of a file added after it |
| `ripper_log_verification` | **`verified`** | ✅ *"the ripper verified …log against its own FUN512 checksum — the log is a faithful, unmodified record of this rip"* |
| `read_stalls` / `read_stalls_count` | `none (no read exceeded 10s)` / `0` | ✅ **first hardware sighting of this line** |
| schema | `19` | |

**The two provenance witnesses agree.** `ripper_handshake_approval` (our verdict on the
banner) and `ripper_handshake_note` (the binary's own compiled-in round state) tell the
same story. Per lap 22, a disagreement would have been the finding; there is none.

---

## B. New-in-this-beta surfaces, all exercised for the first time on hardware

**1. The replayed pre-log block works.** Six lines that previously reached stdout and
nowhere else are now inside the logfile:

```
--- output before this log was opened ---
Checking /dev/sr0 for cdrom...
        CDROM sensed: PIONEER  BD-RW   BDR-209D 1.51 SCSI CD-ROM


Opening drive...
Release ID unavailable, cannot search Cover Art DB!
--- end of pre-log output ---
```

Our parser treats the block as inert, as measured in lap 13 §B2. Confirmed against a real
artifact rather than a fixture.

**2. `Read stalls:` parsed, tri-state honoured.** `none (no read exceeded 10s)` → our
`read_stalls_count` = `0`, not `null`. The distinction matters: `null` is *unknown*.

**3. `Log FUN512:` present and verified** by cyanrip's own `--verify-log`.

**4. `C2 errors: unsupported by drive`** — the C2-unsupported state, on real hardware, for
the first time. It was on the not-proven list in lap 21 §F.

**5. `CD-TEXT: none reported by libcdio (absent, or unreadable by this driver)`** — the
null stated rather than left silent, which is the shape we asked for.

---

## C. The auto-fix path fired, and the sidecar did its job

Track 5 missed AccurateRip v1/v2 on the first pass. Platterpus re-ripped it, the read
**converged after 3 reads**, and the better read was swapped in.

| | value |
|---|---|
| first pass (recorded in the ripper's log) | CRC `6902BCF0`, AR v1 `7CE3F6E7` not found, AR v2 `268CCD94` not found |
| **the file on disk** (recorded in the addendum) | CRC **`E0036697`**, `Secure re-read: converged after 3 reads` |
| EAC's baseline for track 5 | **`E0036697`** |

So the shipped file matches EAC exactly, and **the sidecar is the only thing that says
so** — the ripper's log necessarily describes the read we threw away.

This is H1 working as designed: the ripper's log is left **byte-exact** (which is why
`--verify-log` still returns `verified`), and the supersede lives beside it.

The rendered EAC-compatible log gets it right too, including the Test/Copy pair:

```
Track  5
     Test CRC E0036697
     Copy CRC E0036697  (Test and Copy CRC identical — confirmed across 3 secure re-reads)
     Matched an offset-variant pressing — partially accurate (confidence 200)  [4CCBCF89]  (AR +450)
```

---

## D. Pre-gap: all four sources agree, and A25 has an answer

**Four independent sources, cross-checked per track:**

| track | `Gaps:` block | per-track `Pregap length` | LSN subtraction | cue `INDEX 00` |
|---|---|---|---|---|
| 2 | 160 | 160 | 14487 − 14327 = **160** | `03:11:02` → LSN 14327 ✓ |
| 4 | 158 | 158 | 49920 − 49762 = **158** | ✓ |
| 5 | 115 | 115 | 72570 − 72455 = **115** | ✓ |
| 7 | 105 | 105 | 109175 − 109070 = **105** | ✓ |
| 8 | 85 | 85 | 128757 − 128672 = **85** | ✓ |
| 9 | 94 | 94 | 145662 − 145568 = **94** | ✓ |
| 10 | 147 | 147 | 159237 − 159090 = **147** | ✓ |
| 13 | 90 | 90 | 224510 − 224420 = **90** | ✓ |
| 14 | 117 | 117 | 246527 − 246410 = **117** | ✓ |

Nine `Gaps:` rows + track 1's 150-frame lead-in + four zero-pregap tracks (3, 6, 11, 12)
= 14. **No source disagrees with any other.**

### D1. Our 89× bug (F4) is now hardware-proven — A25 can close as PASSED

A25 has said since v0.5.21 that the fix *"has no hardware proof and this disc cannot give
it one"*, on the premise that cyanrip reports `none` for every track here. **That premise
has expired**: the fork reads pre-gaps from the sub-channel now, so ten tracks report a
non-zero pre-gap with a non-zero `Pregap LSN`.

That is exactly the case F4 was about. Track 2's `Pregap LSN` is **14327** and its length
is **160**; we render 160. Had the bug been live we would have archived 14327 frames — an
89× over-claim. **Proven on hardware, at last.**

### D2. Their C1 fix is hardware-unprovable on this collection — a real result

C1 (track 1's pre-gap counting the 2-second lead-in twice) fires only where the **TOC**
declares the pre-gap. Across **every `Pregap source:` line in the whole retained log
history** — 40+ occurrences spanning three days of rips — the source is `lead-in` or
`sub-channel (not signalled by TOC)`. **Zero `TOC`.**

So: `candidate found: NO`. Not "untested" — **no disc in this collection can test it.**

**And the screening command in the session sheet was the wrong test.** It greps
`Pregap LSN:` and excludes `none`, which was discriminating when cyanrip reported `none`
everywhere and is now satisfied by almost any disc. The discriminating string is
`Pregap source: TOC`. Sheet corrected.

---

## E. What ran, what didn't

| step | result |
|---|---|
| P0 update route | ✅ beta channel, in-app update |
| P1 `--version` | ✅ `0.6.4b4` (derived: About dialog + EAC-log header, both say build `c7aa67c`) |
| P2 `--install-ripper` | ✅ completed |
| P3 `cyanrip --version` | ✅ `…beta.2 (platterpus-fork-gc5fb909)`, clean tag |
| P4 `--doctor` | **NOT RUN** |
| 1 A25 screening | ✅ answered — **no candidate exists**, §D2 |
| 2 Police re-rip | ✅ 14 of 14 tracks |
| 3 EAC parity | ✅ **14/14, exit 0** — after fixing our own checker, §5 |
| 4 H10 / `-O` overread | **NOT RUN.** The log's `Overread: +2 frames` is the *offset* fill at the disc end (`Fill up missing offset samples with silence: Yes`), **not** the `-O` toggle — the argv carries no `-O`, and the EAC-compatible log says `Overread into Lead-In and Lead-Out : No`. Still owed. |
| 5a `-x` cache probe | **NOT RUN** |
| 5b `-j` diagnostics | **NOT RUN** |
| 6 mid-rip cancel | **NOT RUN** |

---

## F. Defects the artifacts found — ours

### F1. `--consumer` has never been sent, on any build ⚠️ FIXED

Log line 4: `Consumer: not identified (no --consumer given)`. No `-u` anywhere in the
`Invoked as:` line.

`_build_rip_argv` gates the flag on `consumer_tag_for_build(ripper_build_tag)` and defaults
that parameter to `""`, and **nothing ever passed it.** So the capability, its allowlist and
its sanity check were all built and tested around a value nobody supplied. Every existing
test called the argv builder *directly* and passed a tag, measuring the gate and never the
wiring.

Fixed: `rip()` now supplies `_observed_build_tag()`, which already existed for
`verify_log`. Revert-proved, and the test asserts **both** directions — sent to `c5fb909`,
withheld from an unrecognised build, because asserting only the first would pass against a
version that sent it unconditionally.

### F2. Three of our own CLI tools read a rip log without the addendum ⚠️ FIXED

`scripts/eac_parity.py` reported **13/14 — NOT parity**, naming track 5's CRC as
`6902BCF0`: the pass Platterpus *discarded*. The rip was 14/14. **A false negative on the
one number that answers "is Platterpus bit-perfect?", from Platterpus's own checker.**

`rip_addendum.read_log_with_addendum` exists for exactly this and is documented as the only
sanctioned reader, enforced by a sweep. The sweep had **two** holes:

* **scope** — it globbed `src/platterpus/` only, so every tool in `scripts/` was outside
  every guard the rule has;
* **trigger** — it fired on `parse_cyanrip_log`/`parse_rip_log`, so a module that opened a
  log and pulled CRCs from it by any *other* route was not exempt, it was **unseen**. That
  is the hole that bit: `eac_parity.py` uses `compare_logs`.

Widening both immediately found `render_eac_log.py` and `rip_report.py` doing the same — so
the **archival** EAC-compatible log and the regenerated report were exposed too. All three
now share one `rip_addendum.read_any_log()`. The app itself was always correct.

---

## G. Observations for the fork — none blocking

**G1. `Tracks ripped partially accurately: 1/1`.** One track of fourteen was partial, so
the denominator reads oddly beside `Tracks ripped accurately: 13/14`. If `1/1` means
"1 of 1 partial tracks" it is self-referential; if it means "of the disc" it should be
`1/14`. A consumer rendering the pair as a disc-level tally will over-report.

**G2. The pre-log block contradicts the header two lines later.** It says
`Release ID unavailable, cannot search Cover Art DB!` and the header then prints
`Release ID: d14a7546-815b-43c6-8af6-35cff6cee1d0`. Both are true — the ID arrives as a
`-a` **tag**, not as something cyanrip resolved for itself, so it genuinely had none at
Cover-Art time. Accurate and confusing; worth a word naming *which* release ID is absent.

**G3. `Cache model: 1200 sectors (drive cache size not probed)`** — good: it states that
the number is a model rather than a measurement. Exactly the tri-state honesty we ask for
elsewhere, and worth saying so.

---

## H. Files this record was derived from

| file | what it settled |
|---|---|
| `…The_Classics.log` | banner, argv, pre-log block, gaps, per-track CRCs, stalls, FUN512 |
| `…The_Classics.platterpus-addendum.txt` | the shipped track-5 read — the file EAC agrees with |
| `…The_Classics.platterpus.json` | approval, note, log verification, stall count, schema 19 |
| `…The_Classics_EACcompatible.log` | the rendered archival log, Test/Copy pair, appended-silence note |
| `…The_Classics.cue` | `INDEX 00` positions — the fourth pre-gap source |
| `log.txt`, `.1`, `.2` | 40+ `Pregap source:` lines → the A25 answer |

**No audio was sent or committed** (critical rule #8); the CRCs prove bit-perfection
without it.

---

*Last updated for Platterpus v0.6.4b4.*
