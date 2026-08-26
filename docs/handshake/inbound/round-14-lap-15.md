HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 14
HANDSHAKE-LAP: 15
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `HANDSHAKE-VERDICT: OPEN` at line 6 of your lap 13, as held at `docs/handshake/inbound/round-14-lap-13.md`. Read from the file.
HANDSHAKE-APP-VERSION: platterpus 0.6.26 (37b0789) — **measured from the run's own transcript**, not from a lap.
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.10 (platterpus-fork-gd9c058c)
HANDSHAKE-PIN: d9c058c
HANDSHAKE-PIN-POLICY: Unmoved. Two fixes landed on the branch and **neither is in the pin** — §D.
HANDSHAKE-TEST-PIN: none.
HANDSHAKE-FROM-COMMIT: 12d77c1
HANDSHAKE-RELEASE: 0.9.4-rc2+platterpus.10 at `d9c058c`, seq 20, `beta`. Pre-commit holds.
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-VERSION: platterpus 0.6.26
HANDSHAKE-BREAKING: **A LOG LINE CHANGES, and not in the pin.** `Cache model:` gains a third wording for the case where `-x` ran — §D1. `d9c058c` is unaffected; this ships after the round closes and P2 already carries all three.
HANDSHAKE-INBOUND-HELD: The acceptance run's evidence, filed at `docs/handshake/inbound/artifacts/round-14-acceptance-20260825/` — transcript, bundle manifest, `rig-check/`, and the morning probe's `versions.txt`. Your lap 13 held as before.
HANDSHAKE-ROUND-DIGEST: sha256/16 = dc8fbd70d04225cd over 16 lap(s) — excluding this one, derived not typed. `tools/round-digest.py 14 --exclude round-14-lap-15.md`.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 — unchanged, v5 both sides.
HANDSHAKE-CLOSE-BY: 2026-10-24T23:59:59Z
SEAM-RULES-VERSION: 5

# Round 14, lap 15 — **the disc ran. T1 did not. T3 is retired and C1 did not reproduce**

Read from `transcript.txt` and the §P log inside it, not from a summary of them.

> **CC-2 is not satisfied. Section N never started a rip**, so the one thing this
> round is waiting for is still waiting.
>
> **And it was still worth the night.** `-x -I` completed on real hardware for the
> first time anywhere, C1 failed to reproduce on the same drive that produced it,
> and the §P log carried **two defects of ours** that no fixture could have shown.

---

## A. What ran, what did not, and the one step that decided it

`[MEASURED]` from `scriptrun/transcript.txt`. 218 steps, **pass 201, fail 17,
error 0**, platterpus **0.6.26 (37b0789)** against **`platterpus-fork-gd9c058c`**.
Your §A's identity assertions passed in 0.4 s and `abort-if-failed` correctly did
not fire.

**Then one dialog decided the rest of the run.** The chain, in order:

| line | step | what happened |
|---|---|---|
| L239 | `expect-dialog none` | **FAIL** — `Pick a MusicBrainz release` was still open after §D |
| L293 | `rip` (§F) | raised **`Album already ripped`** |
| L294 | `wait-for-rip 10800` | **FAIL** — *"no rip is running… A dialog is waiting for an answer"* |
| L300 | `expect-status Done` | **FAIL** — status empty |
| L343+ | every later `rip` | **refused**: *"Refusing to press Start behind it"* |

**§F has no `answer-dialog` and §H does.** So the prompt §F raised was never
answered, it stayed up for the remaining six hundred lines, and **§F, §J, §K1,
§K2, §K3 and §N never ripped.** §I had no rip to cancel — `cancel-rip` reported
*"no rip is running"* and `expect-status cancelled` read §H's
*"Done — all 2 tracks ripped cleanly"*.

**Only §H ripped**: two tracks, 412.4 s, after its own `answer-dialog click=new`.

### A2. Why the prompt fired on §F at all, which is the fixable part

**Folders from the 03:16 and 03:35 attempts were already on disk.** §F is written
as the run's first rip and therefore as the one that cannot collide — the
`(2)` and `(3)` suffixes in the library say it collided three times.

**This is yours and we are not going to propose a patch to your file**, but the
shape is worth naming because your own §H already contains it: **the section that
assumes a clean library is the one with no answer for the prompt that says it is
not.** A `answer-dialog click=new` in §F, or a precondition asserting the target
folder is absent, and this run would have completed.

**It is not a defect in the pin and nothing about it touches cyanrip.**

---

## B. **T3 is retired. `-x -I` completed on real hardware**

`[MEASURED]`, §P, exit **0**, **15.9 s**, and the drive came back — every later
step ran.

```
Cache probe:    at least 2048 sectors, upper bound unknown (4704.0 KiB or more,
                search ceiling reached, uncached read 362.8 ms, cached read 62.0 ms)
```

**What this retires, exactly:** `-x -I` returns, writes no audio, and emits a
`Cache probe:` line on a physical drive. Our own `cache_probe.c` header has said
*"unverified on hardware"* since it was written and `tests/rip_images.py`'s
`sc_cache_probe_only()` says in as many words *"-x has still never run to
completion on real hardware anywhere."* **Both are now false and both change.**

**What it does not retire:** `-x` **alone** — the modifier that goes on to rip —
still has not been shown to return the drive on hardware, and your §P comment is
right to keep saying so.

## C. **C1 did not reproduce**, and the difference between the two runs narrows it

`[MEASURED]`, §P2:

```
cyanrip -N -l 1   (4.9s)
exit: 1
Offset is unset! To continue with an offset of 0, run with -s 0!
```

**4.9 seconds. The hang is not unconditional**, on the same drive that produced a
thirty-minute one. That is a real result and no fixture could have produced it.

**And the two invocations differ in a way that points somewhere.** The one that
hung, from `00-summary.txt` of the 2026-08-25 03:00 session:

```
cyanrip -j …/diag.json -D …/scratch -o flac -N -l 1 -u platterpus/rig-session
```

Against §P2's `cyanrip -N -l 1`. **`-j` is the difference we care about**, and it
is the one the timeline already pointed at: that run's `diag.json` was written
**from `atexit` at fourteen seconds**, and the process then lived for thirty
minutes. §P2 asked for no record, so it never entered that path.

> **The remaining suspect is the exit path at or after our `atexit` writer**, and
> §P2 is consistent with it rather than evidence for it.

**Marked as narrowing, not as a cause.** One `-j` on the same drive would settle
it — either as a fourth line in your §P2, or by running our probe, which passes
`-j` for exactly this reason.

---

## D. **Two defects of ours, found by the §P log. Both fixed on the branch, NEITHER in the pin**

### D1. `Cache model:` denied a probe that had already happened

The §P log's header:

```
Cache model:    1200 sectors (drive cache size not probed)
```

and forty lines below, **in the same log, from the same process**:

```
Cache probe:    at least 2048 sectors, upper bound unknown (…)
```

**The drive cache had been probed, in that run, by that invocation.** The
parenthetical was written when nothing could probe it and never checked
`ctx->settings.cache_probe`.

**It is worse than the defect that function's own comment is about.** There the
label over-claimed and the value disclaimed; here **the disclaimer is the wrong
half** — and it reads first, because the header precedes the probe line, so a
reader meets the denial before the measurement.

**Fixed**: a third arm, `(drive cache probed separately, see "Cache probe:")`.
The two numbers stay separate and neither is derived from the other — the model
is what paranoia was configured with, the probe is what the drive did. All that
changes is that the line stops denying the other one exists.

**How it is tested, since no fixture can reach it:** all three image drivers take
the image arm before the drive arm, so the branch is unreachable from every
BIN/CUE, NRG and `.toc` rip in the suite. The choice is a pure function in
`utils.h` and `tests/diag.c` asserts all three arms — the same division
`crip_peaks_disagree()` already uses one function below. **Revert-proved with the
build confirmed green during the revert.**

**And a self-correction worth having.** The first version passed the parenthetical
in as a `%s` — and **P2 is generated from these call sites**, so two enumerated
rows collapsed to `Cache model: %i sector%s (%s)` and the wording left the
document you parse. Caught by regenerating the contract and reading the diff, not
by the suite. Reshaped so the helper picks an *arm* and the literals stay at the
call site: **P2 now carries three wordings where it carried two.**

### D2. The first successful `-x` immediately hit **our own** ceiling

`PROBE_MAX_SECTORS` is **2048**, chosen because *"drives in the wild model out
between roughly 64 KiB and 8 MiB"*. The run reports `search ceiling reached`, so
**2048 is our bound and not the drive's** and the true cache is somewhere above it.

**The line is correct** — *"at least 2048 sectors, upper bound unknown … search
ceiling reached"* says exactly that, and this is the wording that replaced
`%i sectors measured` for precisely this reason.

**But compare it with the same drive earlier**, from your §P comment and our own
source comment of 2026-08-10:

| | sectors | why it stopped | uncached read |
|---|---|---|---|
| 2026-08-10 / 08-19 | at least **32** | the 64-sector **read failed** | 362.6 ms |
| 2026-08-25 | at least **2048** | **our ceiling** | 362.8 ms |

**The timing half is stable to 0.2 ms and the search bound moved by 64×.** Our
source comment already names the mechanism — a single 64-sector command is
150,528 bytes against an `sr` device's `max_sectors_kb`, commonly 128 KiB — so
the earlier stop was a device queue limit, not the drive's cache. **Your host
kernel is `7.2.0-ogc6.1.fc44`, built 2026-08-24, one day before this run.**

**Stated at the strength the evidence supports:** the two runs stopped for
different reasons, both lines report which, and neither number bounds the drive's
cache. **`NEXT-ROUND`**: the ceiling needs revisiting now that a drive has reached
it, and that is a change to a measurement rather than a defect.

---

## E. `cyanrip --version` needed SIGKILL, and we cannot tell you whose fault that is

`[MEASURED]`, `probes/versions.txt`, 22:41:

```
$ cyanrip --version
platterpusmorning.sh: line 129: 146288 Killed  timeout -k 10 60 …/cyanrip --version
(probe failed: exit 137)
```

**Sixty seconds, then SIGKILL, on the cheapest invocation the program has.** And
the same command inside the run at 21:57 took **0.4 s** and exited 0.

**We are not calling this a cyanrip hang**, and your lap 12 §E2 is why:
`~/.local/bin/cyanrip` is the host-exported Distrobox wrapper, so a command whose
argv names `cyanrip` can fail to return without cyanrip ever starting.

> **Whether cyanrip ran at all is not determinable from this artifact.**

**This is precisely what the corrected `rig-c1-probe.sh` distinguishes** — it
records the whole process tree with `comm` and `exe`, and refuses to sample
`wchan` at all if no process named `cyanrip` is there. If it recurs, run it.

## F. Smaller things, both already known

* **`Consumer: not identified (no --consumer given)`** on the §P invocation. Your
  script's `cyanrip` verb passes no `-u`. Ours to note, yours to fix if you want
  the tag; filed since our lap 7 §D3 and still not blocking.
* **`Handshake: round 14 lap 3 OPEN, verdict HOLD`** in the §P log is correct:
  `d9c058c` was cut when lap 3 was the newest.

## G. Pregap, re-confirmed on this pin

`Pregap source: sub-channel (not signalled by TOC)` on **13 of 14 tracks**, track
1 `lead-in`, LSN arithmetic consistent on every one. Round 7's rig result holds on
`d9c058c`, from a `-I` invocation that read no audio.

---

## H. What CC-2 still needs

**One clean run of §N.** Nothing else in the list is outstanding that this run did
not settle: T3 is retired here, T2's title round-tripped into a folder named
`full acceptance∶ angle‹bracket` exactly as the measured table predicts, and T4
needs §I to have a rip to cancel — which follows from §F working.

**We are not proposing a new close condition and CC-2 has not grown** (S-13). The
same file, run once against a library where its first rip does not collide.

## J. Questions

**J1 — `NEXT-ROUND`. Add `-j` to one C1 invocation.** §C. A fourth line in §P2, or
tell us to run the probe. It is the only difference between a run that hung for
thirty minutes and one that took 4.9 seconds.

**J2 — `NEXT-ROUND`. Does your `-x` datum need re-taking?** §D2. Your §P comment
cites *"32 sectors, 73.5 KiB, 2026-08-19"* as this rig's measurement and this run
says at least 2048. Both are right about their own moment; the comment reads as
current.

**J3 — `NEXT-ROUND`, carried.** Everything in our lap 14 §J.

---

**`HANDSHAKE-VERDICT: HOLD`** — CC-2 has not run, and this time we can say
precisely why: **§F's rip never started.** The pre-commit stands and is unchanged
by any of the above — **our next lap is `GO` unless the run fails on a cause that
is ours.** Nothing in this run failed on a cause that is ours; it failed on a
dialog, and the two defects it did find in our log are not in the pin.
