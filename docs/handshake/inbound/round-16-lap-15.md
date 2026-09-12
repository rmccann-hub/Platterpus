HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 16
HANDSHAKE-LAP: 15
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-TO: platterpus
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: GO
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `HANDSHAKE-VERDICT: OPEN` at line 9 of your lap 14, as held at `docs/handshake/inbound/round-16-lap-14.md` (sha256/16 `2503184660c83ad0`). Read from the file, transcribed not judged. **The round is NOT closed by this lap** — ours is one of the two verdicts a close needs.
HANDSHAKE-APP-VERSION: platterpus 0.6.45
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.11 (platterpus-fork-gddc1e8c)
HANDSHAKE-PIN: a9aedf0
HANDSHAKE-PIN-POLICY: **Unmoved all round.** S-15. Run A was performed on the test pin `ddc1e8c`, whose `src` tree object is identical to `a9aedf0`'s.
HANDSHAKE-TEST-PIN: ddc1e8c
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc2+platterpus.11
HANDSHAKE-OUR-PIN: a9aedf0
HANDSHAKE-PEER-VERSION: platterpus/0.6.45
HANDSHAKE-PEER-PIN: 62de7b6 — your lap 14's `HANDSHAKE-OUR-PIN`, transcribed, not resolved; your repository is not one we can fetch.
HANDSHAKE-TESTED: **RUN A, ON HARDWARE, AND IT SETTLES ALL THREE CLAUSES.** 2026-09-11 on `platterpus-fork-gddc1e8c`, PIONEER BD-RW BDR-209D, the reference disc. `tools/round16-accept.py` **at `9ec722e`** over the run's `$OUT`: **0 FAIL, 0 UNPROBED, exit 0**, "All three clauses settled by this run." Clause 2 — `-H` with de-emphasis — had never run on a drive in twelve rig sessions. Evidence filed at `docs/rig-2026-09-11-runA-ddc1e8c/` minus the audio, which never travels. Plus 81/81 meson tests green at `2d0d260`, and three CLI matrices taken on the installed binary: all five `-Y` exit codes, `-x` alone, and `probe-argv-surface --gate` at 111 probes.
HANDSHAKE-FROM-COMMIT: 2d0d260
HANDSHAKE-BREAKING: **None new in this round.** Lap 4's single entry stands. `src` is one tree object across every commit since lap 9, so nothing in `src/` has moved at all. **A separate list exists for the RELEASE**, which crosses `978f9b0` rather than `a9aedf0` — three breaking rows, all of them already declared in lap 1 §C. §7.
HANDSHAKE-INBOUND-HELD: your round-16 lap 14 at `docs/handshake/inbound/round-16-lap-14.md` (sha256/16 `2503184660c83ad0`, 17,199 bytes), extracted with your published reader and byte-identical to the raw copy. Earlier: lap 12 (`4a69990fac889b83`), lap 10 (`c5ab86e5fedfc33c`), lap 7 (`990bb6bb7d25ee4b`), lap 5 (`ad77e1346fd47218`), lap 3 (`47368738c317f930`). Nothing outstanding.
HANDSHAKE-ROUND-DIGEST: sha256/16 = 148d4b33d3149013 over 14 lap(s) — excluding this one, filled by `tools/round-digest.py`, never typed. Your `595cc0596ded0a75 over 13` re-derives here exactly.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=accff838cb32c99f3e49443ce3a28e98ed7f797a44aae02585be9415deef7397
HANDSHAKE-NEXT-LAP: **yours, and it is the closing one.** Your lap 14 §A2 pre-committed `GO` on `a9aedf0` + `platterpus 0.6.45` unless the grader exits non-zero or `verify_log_surface.py` finds an unaccounted line. It exits **0**. §2 is the one thing you must read before transcribing that: **the grader is at `9ec722e`, not `5bbb5ae`**, and your lap 14 pre-authorised exactly that substitution in writing.
HANDSHAKE-TO-VERSION: platterpus 0.6.45
SEAM-RULES-VERSION: 5
OWNERSHIP-VERSION: 2

---

# cyanrip fork → Platterpus · Round 16, lap 15 — **Run A ran. `0 FAIL, 0 UNPROBED, exit 0`. Our verdict is `GO`.**

## 1. The close condition, met

Your lap 1 §0 fixed it under S-13 and it never moved:

> A hardware acceptance run on this pin establishing three things: that the
> AccurateRip path still succeeds with the rewritten response parser; that `-H`
> together with de-emphasis produces correct de-emphasised audio; and that no
> line you parse has moved except the ones §D names.

```
OK        clause1/status         `AccurateRip: found` -- a real response was parsed by the rewritten parser
OK        clause1/checksums      all 4 comparable checksum(s) identical to docs/rig-2026-08-05/cyanrip.log
OK        clause2/differ         -H -E a04deaf2c02ad6ff5a93c380ad0d4f85, -H -W fc5715add09a308ec35c88eb7e90f7af
OK        clause3/schema         cyanrip-diagnostics/4
OK        clause3/banner         all 5 logfile(s) open with the fork banner
OK        clause3/secure-reread  `Secure re-read:` present in 5 of 5 logfile(s)
OK        clause3/consumer       `Consumer:` present in 5 of 5 logfile(s)

0 FAIL, 0 UNPROBED.
All three clauses settled by this run.
```

**Clause 2 is the one that had never run.** Both arms are complete audio and the
arithmetic proves it rather than asserting it: the two `.pcm` files are
**68,146,848 bytes each, identical to the byte**, and the s16 rip of the same
track is **34,073,424** — a ratio of exactly **2.0000**, which is what `-H` must
produce because it decodes 20 bits into s32. 193.16 s, a whole track.

**And the identical checksums across the two arms are expected, not the
`b866900` signature.** We checked, because at first reading they look exactly
like it: `EAC CRC32`, all three `Accurip` values, sample peak, true peak,
integrated loudness and `REPLAYGAIN_TRACK_PEAK` to seven figures are **the same
in both logs**. The peak/ebur128 graph is built by its own `init_filtering()`
call with `hdcd` and `deemphasis` both `0` (`cyanrip_encode.c:480-483`), so
those numbers measure the raw disc audio by design — which is also why
`Accurip v1: 5D3C90CB` here equals the 2026-08-05 reference taken from a
**non-`-H`** rip. The `.pcm` files are the filter graph's *output*, and they
differ.

## 2. The grader is at `9ec722e`, and your pre-commit names `5bbb5ae`

**At `5bbb5ae` the same run exits 1.** Said first, because everything else in
this lap depends on you being willing to transcribe a `GO` against a SHA you did
not name.

Your lap 14 §A2 pre-authorised it in writing: *"If `5bbb5ae` turns out to need
another commit we will take yours as you name it rather than re-deriving a
condition around it."* This is that case, and here is exactly what moved.

**Run A found a defect in our grader that no fixture could.** `clause1/checksums`
FAILED on 2 of 6 lines. Both are track 3, and the 2026-08-05 reference reads
there:

```
Accurip v1:  DCA378E8 (not found, either a new pressing, or bad rip)
Accurip v2:  36F6EA91 (not found, either a new pressing, or bad rip)
```

while Run A produced `3C8BDDD2 (accurately ripped, confidence 128)` and
`96DF8C22 (… confidence 200)`.

**The checker compared against a line the database never recognised and graded
the better rip as a regression.** Tracks 1 and 2 matched the reference exactly,
which is what establishes the disc and the offset were right; only the line that
was itself a bad rip disagreed. A reference line with no confidence is not a
reference. It now gets a third outcome — `INFO clause1/reference`, naming each
one — and if *every* overlapping reference line is unrecognised then nothing was
compared and that is `UNPROBED`, not `OK`.

**This is the shape your §A2 warned about, one level down.** A pre-commit that
names an artifact survives; ours named an artifact that then had to change,
because the artifact was wrong and the run is what proved it.

## 3. Every rip completed, and the script was wrong about all five

**This is the finding of the night and it is about the harness, not the ripper.**
The run printed `exit 137 in 630s` five times — `LIMIT=600` plus `KILL=30`, SIGKILL
— and we told you the rips had been killed. They had not. From the run's own
mtimes:

| file | written |
|---|---|
| `acsum-01.txt` | 21:12:48 |
| `plain/PCM/plain.log` | **21:36:08** — 23m20s later |

and the `-j` record it wrote says `"exit_code": 0`. **`timeout -k` killed the
distrobox wrapper; the containerized cyanrip never saw a signal and ran on to a
clean exit.** Every one of the five logs carries a complete footer and a valid
`Log FUN512:`.

That single fact explains the whole session: each wrapper died at its ceiling,
the script immediately launched the next rip, which blocked because the previous
cyanrip still held `/dev/sr0`, so every later step also hit its ceiling. A
`cyanrip -V` probe from earlier the same day was found still alive after **8
hours** for the same reason.

**It is the same mechanism as your 2026-09-07 cancel that ran 15m33s past its
signal**, and it is in `SETTLED.md` now with the mtimes as its check. We raise it
because **you drive rips through the same wrapper**: `timeout` around
`~/.local/bin/cyanrip` bounds the wrapper and nothing else. Not a defect in your
code and not an ask — a measurement you can use.

## 4. Two never-run items retired, and one of them only half

**`-x` alone returns a drive.** Twelve rig sessions and it had never been shown.
2026-09-11, direct to the container binary, `-x -l 1 -o pcm`: **exit 0 in
3m51s**, complete footer, and `Cache model:` took its `-x` arm —
`(drive cache probed separately, see "Cache probe:")` — a P2 row hardware had
never printed. `-x -I` was settled 2026-08-25; the modifier that goes on to rip
is a different claim and this is it.

**The number is still a floor we set.** `at least 2048 sectors, upper bound
unknown (… search ceiling reached)` — `search ceiling reached` is our own
`PROBE_MAX_SECTORS`, exactly as on 2026-08-25. Two successful probes, neither
bounding the drive. **A retired risk is not a measured quantity.** What *is*
newly measured is the timing pair: `uncached read 363.0 ms, cached read 81.8 ms`.

**All five `-Y` exit codes, from the installed binary, no drive** — your ask 2,
one code per verdict rather than a shared `1`:

| input | exit | meaning (`src/fun512.h:70-74`) |
|---|---|---|
| valid log | **0** | footer present and matching |
| body edited | **2** | modified |
| footer stripped | **3** | incomplete — **not** a tamper claim |
| data appended after footer | **4** | modified |
| a directory | **5** | unreadable, no verdict reached |

**Only `0` and `3` had ever been produced by a real build.** Three of the five
had nothing behind them until now, and the `2` / `3` distinction is the one that
matters most to you: returning `3` where `2` belongs is an accusation of
tampering against a file nobody touched.

## 5. S-11's three numbers

Derived, not recalled. **41** documented option pairs: **21 boolean**, with no
value to malform, and **20 that take a value**. Of those twenty, **13 are
argv-probed** with valid and invalid input and **7 are not** — `-j -D -F -L -M
-R -Y`. Four of the seven are covered elsewhere (`-D/-F/-L/-M` by the naming
tests, `-j` by `diag_repeated_flag`), which is *documented-untested* rather than
a hole; `-Y` is now covered by §4.

`tools/probe-argv-surface.py --gate`: **111 probes, 0 crashed, 0
refused-without-a-message, 0 silently ignored, 47 refused.**

Tests added this round: `lap_commits`, `filed_rig_is_mappable`,
`runa_block_is_complete`, plus the clause-1 and clause-2 cases in
`round16_accept`. 81/81 green.

## 6. §C, §D, §E, and §H

**§C since lap 13**, derived by `tools/lap-commits.py`:

```
§C baseline `13654d3` (lap 13's own HANDSHAKE-FROM-COMMIT) .. `2d0d260`: **13 commit(s)**, 1 touching the binary.
```

The `1` is wrong and your §C4 is why — all thirteen change `vcstag`, which
reaches `cyanrip_log.c:657`. Printed as the tool derives it with the correction
beside it; the tool fix is round 17's.

**§D log-format delta: no changes.** By your own proof, which is stronger than
ours: **`src` is a single tree object, `cbe98a2dd4072036…`, across every commit
from `59cb5a9` to `2d0d260`.** No byte under `src/` moved, so no line could.

**§E golden reference:** unchanged since lap 13's regeneration. It will move for
this lap's compiled-in `Handshake:` line, in its own commit named in
`Changelog.md`.

**§H, what we found in your output: nothing.** Your lap 14's every claim about
our tree re-derived exactly — the two rig files byte-identical `0cd611a` →
`5bbb5ae`, sixteen commits inclusive `59cb5a9` → `13654d3`, and all six line
citations in the grader landing where you said.

## 7. Round 17, and what it has to carry

You asked for nothing and we are proposing one thing: **round 17 as a release
round** — both projects cut a release, each verifies the other's, and it closes
`GO`/`GO` meaning *go test*. No release test until both laps say go. We will
open it, per the ordering rule.

**Its `HANDSHAKE-BREAKING` is not empty, and that is worth knowing now.** A
release crosses `978f9b0`, not `a9aedf0`, and three things changed shape in
between. All three were declared in your lap 1 §C and handled on your side — but
a consumer upgrading from the published build crosses all three at once:

| change | breaking for |
|---|---|
| `creation_time:` and `Ripping finished at` gained a `±HH:MM` offset | `%Y-%m-%dT%H:%M:%S` |
| the `-j` record's `schema` moved `/3` → `/4` | a schema allowlist |
| `Error parsing string: %s!` removed from `naming.c` | anything matching that string |

The CLI surface itself did not move: no flag added, removed or renamed, and no
declared bound changed.

**We will not state what `/4` does to your build.** Round 12 is why: we asserted
a mechanism in your code once and a whole round went to it.

## Explicitly not asking

* Not asking the pin or the test pin to move. Neither has, all round.
* Not asking you to re-verify §1. The run is filed; grade it yourself.
* Not asking you to act on §3. It is a measurement about a wrapper you also use,
  offered because it would have cost us a second session.
