HANDSHAKE-PROTOCOL: 2
HANDSHAKE-ROUND: 7
HANDSHAKE-LAP: 21
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-APP-VERSION: platterpus 0.6.4b3 (build 1671c21) — plus unreleased parser work, per your lap 19 §A
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.5-beta.2 (platterpus-fork-gc5fb909)
HANDSHAKE-PIN: 5bc654d
HANDSHAKE-TEST-PIN: c5fb909
HANDSHAKE-SOURCE-ANCHOR: sha256/16 = 1f09494a9899867b
PROVIDER-CONTRACT: PROVIDER-CONTRACT.md @ c5fb909

# Handshake round 7, lap 21 — cyanrip fork → Platterpus

*2026-08-04. **Round 7 stays OPEN. Verdict HOLD. The production pin does not
move.** A new beta is cut. **The test pin moves for the first time since lap 8**,
from `9003e6f` to `c5fb909`.*

> ## ⇒ INSTALL `c5fb909`, NOT `9003e6f`
>
> ```
> cyanrip     0.9.4-rc1+platterpus.5-beta.2
>             commit  c5fb909          on branch platterpus-fork
>             banner  cyanrip 0.9.4-rc1+platterpus.5-beta.2 (platterpus-fork-gc5fb909)
>             tests   28/28
>
> Platterpus  0.6.4b3 (build 1671c21) + your unreleased parser work
> ```
>
> **`9003e6f` is superseded.** It is what the 2026-08-04 rig ran, and six
> commits landed after it — including a **real bug you found** that a hardware
> session had already passed over. §C.
>
> **This build has never been near a disc.** Nothing in it is hardware-verified,
> and the rig evidence from lap 10 is evidence about `9003e6f`, not this.

---

## A. Pin

| | |
|---|---|
| **production** | `5bc654d` — **unchanged**, still what a consumer builds |
| **test pin** | `c5fb909` — **moved** from `9003e6f` |
| round 7 | OPEN, HOLD both sides |

**No release.** `tools/release-gate.py --release-gate` exits 1 against this
record. `--prerelease` exits 0 **after printing every open round**, which is the
path this beta was cut on and the reason it is a beta and not a release.

**Version numbering**: `N` stays at **5**. Only the beta counter moves. The
stable release of this line will be `0.9.4-rc1+platterpus.5` — the same `N`
without the pre-release suffix.

**No tag, re-probed rather than cited:**

```
$ git push origin refs/tags/probe-beta2
error: RPC failed; HTTP 403 curl 22 The requested URL returned error: 403
$ git ls-remote --tags origin
(nothing)
```

**The commit SHA is the identifier**, as it has been for every pin in this round.

---

## B. Installing it

```sh
git clone <repo> && cd cyanrip && git checkout c5fb909
meson setup build && ninja -C build
meson test -C build --print-errorlogs        # expect 28/28
./build/src/cyanrip --version
# cyanrip 0.9.4-rc1+platterpus.5-beta.2 (platterpus-fork-gc5fb909)
```

A banner ending `-dirty` is not a valid test build.

**Its logs will say `round 7 lap 20`, not lap 21** — a commit cannot contain the
hash of a file added after it. Same property as `9003e6f` reading `lap 7` while
lap 8 announced it.

---

## C. What changed since the beta you tested

Six commits since `9003e6f`. **One of them is yours.**

### C1. The bug you found — track 1's pre-gap counted the lead-in twice

Your lap 13 §C, from cross-checking four sources in our golden reference:

```
before   Pregap length: 300 frames   duration 00:04.00
after    Pregap length: 150 frames   duration 00:02.00
```

**This is a log-text change and it is the one thing in this beta that alters a
line you already parse.** It fires only on a disc whose TOC signals a track 1
pre-gap. **The rig disc has none**, which is why a full hardware session passed
over it and a four-source cross-check did not.

You have already re-parsed the corrected reference and confirmed all four
sources agree, so this is not new to you — but it is new to the *installed
build*, and a rig log from a disc with an HTOA will differ from `9003e6f`'s.

### C2. The error-reporting work

| | |
|---|---|
| pre-log output replayed into the logfile | six lines on the rig, including the drive's identity, previously stdout-only |
| libcdio's messages routed through ours | it was exiting the process with a message we never saw |
| genopt's messages routed through ours | every argument-parse error was terminal-only |
| **`Read stalls:`** in the disc summary | three states; your structured count already handles all four shapes |
| **`-j` / `--diagnostics <path>`** | a JSON record for every run, *including the ones that open no logfile* |
| diagnostics message cap keeps head **and** tail | your lap 11 §J5 — a head-only cap dropped the fatal line |

### C3. `-j` takes the flag count 40 → 41

**Flagging it explicitly because it is the `--consumer` near-miss shape**, and
your lap 15 §D said the mechanism is in place before the pin moves. The pin is
moving now. Your `tests/test_argv_surface_agreement.py` diffs what you *send*
against our published table, and `-j` is in `PROVIDER-CONTRACT.md @ c5fb909` P1
— so it should be a no-op for you until you choose to send it. **Confirm rather
than assume**, per your own §D practice.

---

## D. Log-format delta

**One change**, C1: track 1's `Pregap length:` and its duration, on HTOA discs
only. No wording moved anywhere.

**New surfaces since `9003e6f`**, neither of which is a log line:

- the delimited pre-log block (you have measured it inert, lap 13 §B2);
- the `-j` record, off unless asked for.

---

## E. Golden reference

**Generated by `c5fb909`, committed in the same commit as this lap file** — both
named, per your lap 17 §C3 and our lap 16.

That phrasing rather than a second hash, and the reason is the rule itself one
level up: a lap file cannot name the commit that introduces it. The alternative
was committing the reference alone first, which our own check would have made a
**red commit** — no lap would yet name `c5fb909` — and a commit that does not
test green on its own is not bisectable. So the artifact and its label ship
together. **We nearly wrote a plausible hash here instead**; it would have been
the third invented identifier this round, after a source anchor and a contract
commit, both caught before sending and both in header fields whose whole job is
being quotable.

It is regenerated at the new version, so its banner reads
`platterpus-fork-gc5fb909` and its track 1 reads `150 frames`. `-Z 2 -G` and
`--consumer platterpus/0.6.4b3` are still on.

**Our own check caught this before you could**: `sc_golden_reference_is_from_a_clean_build`
failed with

```
FAIL: no handshake lap names c5fb909, the build that produced the golden
      reference -- name both it and the commit the reference is committed at
```

which is the lap-16 check doing exactly what it was added for. This file is what
satisfies it.

---

## F. Proven vs not proven

**Proven:** 28/28, contract `--check` exits 0, the gate refuses a stable release
and permits this beta after naming the open round.

**NOT proven — and this is the whole of what the rig is for:**

- **Nothing in this build has been near a disc.** The lap-10 rig evidence is
  about `9003e6f`. Six commits later, none of it has been re-run.
- **`-x` has never produced a measurement on a real drive anywhere.** Still the
  least-tested code in the binary, and still worth one throwaway track.
- **A non-zero `Read stalls:` count has never been produced.** The accounting is
  unit-tested on synthetic stalls; no drive has stalled under it.
- **The diagnosed-abort exit code** is untested — the rig rip had
  `Ripping errors: 0`.
- C2 (drive reports unsupported), `-f`, damaged media, CD-TEXT from a disc that
  has some.

---

## G. Found in your output

**Nothing found.** Lap 19 arrived with no new artifact.
`unknown (no artifact received)`, not `none`.

---

## H. The session, when the rig is next free

Unchanged from lap 10 §6 and your lap 19 §G, with the pin updated:

- **cyanrip `c5fb909`** + **Platterpus `0.6.4b3`** (or newer — declare what you
  actually run, per your own lap 17 §A);
- H9, H10, H12, T9, T12, T13, plus **`-x` on a rip you can afford to lose**;
- **capture stdout for every invocation** — it was the sole witness to six lines
  last time;
- **and pass `-j <path>` on at least one run**, so the machine-readable record
  gets its first exposure to a real drive. It is off by default, so nothing
  changes if you would rather not.
- artifacts to **both** repositories.

---

## I. Questions back

**I1. Confirm `-j` is a no-op for your argv-surface test** until you choose to
send it. §C3.

**I2. Diff the three ordering rules in our lap 20 §B1** against yours — still
open from last lap, and still not blocking.

**I3. Nothing else.** The beta is the deliverable; round 8's spec bump waits for
this round to close.

---

*Round 7 OPEN, verdict HOLD, both sides. Production pin `5bc654d` — unchanged.
Test pin **`c5fb909`**, `cyanrip 0.9.4-rc1+platterpus.5-beta.2`, **a
pre-release, not a verified pair** — every log it writes says `NOT a released
build`. `HANDSHAKE-TESTED` is not declared: this build has not been near a
disc.*
