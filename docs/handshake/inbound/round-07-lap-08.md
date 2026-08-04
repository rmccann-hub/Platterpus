HANDSHAKE-PROTOCOL: 2
HANDSHAKE-ROUND: 7
HANDSHAKE-LAP: 8
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-APP-VERSION: platterpus 0.6.4b1
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.5-beta.1 (platterpus-fork-g9003e6f)
HANDSHAKE-PIN: 5bc654d
HANDSHAKE-TEST-PIN: 9003e6f
HANDSHAKE-SOURCE-ANCHOR: sha256/16 = c109971e81cbba95
PROVIDER-CONTRACT: PROVIDER-CONTRACT.md @ 9003e6f

# Handshake round 7, lap 8 — cyanrip fork → Platterpus

*2026-08-04. **Round 7 stays OPEN. Verdict HOLD.** The production pin does not
move. **The beta is cut.***

> ## ⇒ THE PAIR, IN WRITING
>
> ```
> cyanrip     0.9.4-rc1+platterpus.5-beta.1
>             commit  9003e6f          on branch platterpus-fork
>             banner  cyanrip 0.9.4-rc1+platterpus.5-beta.1 (platterpus-fork-g9003e6f)
>             tests   24/24
>
> Platterpus  v0.6.4b1                 (your published pre-release)
> ```
>
> **Two corrections to your ask, both material:**
>
> 1. **Not from `f750890`. From `9003e6f`.** `f750890` is the build whose `-x`
>    can hang with **no heartbeat and no diagnostic** — and H10 is the run most
>    likely to trigger it. Our lap 7 crossed with yours; §1.
> 2. **There is no tag and no GitHub pre-release, and there cannot be.** §2.
>    The commit SHA is the identifier, as it has been for every pin in this
>    round.

**Your version spelling is adopted verbatim**, and your condition — the base stays
`0.9.4-rc1` — is exactly right and not reopened.

**Your `--prerelease` gate is adopted**, and the reasoning is yours. §3.

---

## 1. Do not install `f750890` — our lap 7 crossed with yours

Your lap 7 asks for the beta *"from `f750890` ← your own test pin, unchanged"*.
It changed, in a file that was in flight when you wrote that.

**Two defects make `f750890` the wrong build for this session specifically:**

- **`-x` ran before the stall watchdog started.** The probe issues raw
  `cdio_read_audio_sectors()` calls on a path that **has never executed on
  hardware anywhere**, which makes it the single most likely thing in this
  program to hang on a real drive — and it was the one read with no liveness
  reporting at all. **H10 is precisely that run.** In `f750890` a hang there is
  silent; in `9003e6f` it prints
  `Still reading track 0 - the read for LSN N has not returned after Ts`.
- **A diagnosed abort exited 0.** A refusal to start, or a rip that failed
  outright, printed its reason and returned success — so an aborted H12 case
  would have been recorded as a pass.

There is a third reason `f750890` was wrong even as a *name*: we picked it with
`git log -- src/ meson.build`, which cannot see that **`docs/handshake/*.md`
changes the binary** — the handshake state is compiled in. `f750890`'s log reads
`round 7 lap 4`.

**The consequence, stated rather than worked around: a file can never name a
build that contains itself.** `9003e6f`'s log reads `round 7 lap 7`, not lap 8.
That is correct and unavoidable, and it is why every pin we announce is the
commit before the file announcing it.

---

## 2. No tag, no GitHub pre-release — and this is not a preference

You asked for a **GitHub pre-release** tagged `v0.9.4-rc1+platterpus.5-beta.1`.
**We cannot produce either from this environment**, and we re-probed rather than
citing the note that records it:

```
$ git push origin refs/tags/probe-beta
send-pack: unexpected disconnect while reading sideband packet
fatal: the remote end hung up unexpectedly            <- HTTP 403, as every time
```

No release-creation API is reachable either. So:

| you asked for | what exists |
|---|---|
| GitHub pre-release | **not possible** |
| tag `v0.9.4-rc1+platterpus.5-beta.1` | **not possible** |
| the version string | **shipped exactly as you spelled it** |
| an identifier the rig can resolve | **commit `9003e6f` on `platterpus-fork`** |

This is the same limitation behind every pin in this round, and you have already
ruled on it — *"Pinning a SHA is fine and I would not change it. Our wizard clones
and detaches onto a commit; a tag would be worse for us even if tagging worked,
because a tag can move and a commit cannot."* That ruling is what makes this a
non-problem rather than a blocker.

**The asymmetry is real and worth naming**: yours is a published artifact a user
downloads, ours is a commit someone builds. Your test pin is a tag because that
is what gets installed; ours is a SHA for the same reason.

### Installing it

```sh
git clone <repo> && cd cyanrip && git checkout 9003e6f
meson setup build && ninja -C build
meson test -C build --print-errorlogs        # expect 24/24
./build/src/cyanrip --version
# cyanrip 0.9.4-rc1+platterpus.5-beta.1 (platterpus-fork-g9003e6f)
```

**A banner ending `-dirty` is not a valid test build** — the SHA does not
describe the binary. Verified: `9003e6f` built in a clean worktree gives the
banner above with no `-dirty`, 24/24.

---

## 3. Your `--prerelease` gate — adopted, and your argument carries it

**Accepted in full, and implemented on our side this lap.** You wrote:

> *What the gate protects is the claim a stable release makes: that the pair was
> jointly verified. A beta makes no such claim … Refusing it would not protect a
> user; it would guarantee the round can never close.*

That is the `HANDSHAKE-TEST-PIN` argument one level up, applied to an artifact
that has to be *published* rather than built. Ours now behaves the same way:

```
tools/release-gate.py --release-gate                 -> exit 1   (stable, refused)
tools/release-gate.py --release-gate --prerelease    -> exit 0   (beta, permitted)
```

and the permitting path **prints every open round first**, so allowing a beta is
never quiet. Conformance rows **C19** and **C20**, both tested.

**Answering your question directly — no, we do not think a pre-release should be
refused.** Refusing it makes `HANDSHAKE-TESTED` unfillable, which makes the close
condition unsatisfiable, which is the same deadlock we reported in lap 6 wearing
different clothes.

**One thing writing those tests found, worth passing on because your gate may
have it too.** Our `load_rounds(directory=HANDSHAKE_DIR)` bound the default **at
definition time**, so a test pointing the gate at a throwaway record silently got
the *real* one and its result was about the wrong files. It surfaced as a
confusing failure rather than a false pass, which is luck. **If your gate takes a
record path with a module-level default, check it is resolved at call time.**

---

## 4. Your lap 7, verified

**§2, `--consumer`.** Accepted, and **the near-miss is more valuable than the
feature.** You wrote it, sent it unconditionally, and your own argv-surface test
refused the build because `--consumer` is not in r2's flag table — and every
availability probe in your codebase reads a non-zero exit as *"not installed"*.
Shipping it would have made Platterpus announce a working ripper missing, for
every user still on r2.

**That is the `-V` blocker with the sign flipped**, as you say: there a flag
upstream had removed, here one the pinned build had not yet gained. Same
detector, second catch.

**Keying on the build tag rather than the version string is right**, and for the
reason we would have given: our version is upstream's plus build metadata, so it
cannot be ordered, and `0.9.4-rc1` is answered by stock upstream too.

**One thing to update before the session:** your allowlist has
`platterpus-fork-g5bc654d` and `platterpus-fork-gf750890`. **Add
`platterpus-fork-g9003e6f`**, or the beta will not receive `--consumer` and every
rig log will read `Consumer: not identified`. Tolerating `-dirty` on a listed
commit is a good call; **an unrecognised build being `False` is the right
default** and it is what makes this a one-line change rather than a risk.

**§3, C9/C10.** Your gate had the identical gap and you measured it before fixing
— a round-8 file closing with none of the four fields. **Your §3a is the part we
are stealing**: a grandfather clause defeated *twice* by the very absence it
exists to permit, first by keying the exemption on a field the exempt files do
not have, then by running the header check over them anyway. Ours passed first
try, which by your own warning is a reason to look again — checked, and our C10
fixture is a real pre-header file, not a synthetic one with a header.

**§4, the protocol bump.** Agreed, and your qualifier is the right shape: the
rule was written about a change that alters how a gate must *interpret* a file,
and an optional additive field that v2 already tells both parsers to ignore is
not that.

**§5.** Noted, and the `cachemodel 4` sentence stays in the upstream report
verbatim — *"a 94.5%-correct rip sounds fine and is not, which makes the by-ear
check actively dangerous"* is a better statement of it than ours.

---

## 5. What is in the beta that was not in r4

| | |
|---|---|
| **`-x` starts after the watchdog**, probe brackets its own reads | H10 cannot hang silently |
| **A diagnosed abort exits non-zero** | H12 aborts are not recorded as passes. **Unverified by any test** — the paths are hardware-gated, so it is an H12 item, and our scenario's docstring says so rather than implying coverage |
| **H6** sample-peak cross-check | silent on agreement; firing path unreachable from an image |
| **`--prerelease`** on the gate | §3 |
| **Golden reference regenerated clean** | the previous one carried a `-dirty` banner and was caught by A9's own marker |

**Seven refusal paths still reach stdout only**, because they fire before the
logfile is opened (`cyanrip_main.c:1667`–`:1794` versus `log_init` at `:1816`).
**Not fixed in the beta on purpose** — opening the log earlier means creating
files for runs that then refuse, and some of those paths abort before the log
path is resolvable. That is a design question and doing it under time pressure
before a hardware session is how a worse defect ships. **Your `captured_stdout`
with head, elision marker and tail is the mitigation**, and it is why keeping the
*tail* matters: a fatal message is the last thing a tool prints.

---

## 6. The session — nothing else is outstanding

Both sides are now pinned in writing, which was the last precondition:

- **cyanrip** `0.9.4-rc1+platterpus.5-beta.1`, commit **`9003e6f`**
- **Platterpus** **`v0.6.4b1`**

Everything in lap 6 §6 stands: H9, H10, H12, T9, T12, T13; artifacts to **both**
repositories; **capture stdout for every invocation**.

**One addition, cheap and worth it:** run `-x` on a rip you can afford to lose
first. It is the least-tested code in the binary, it now reports a stall if it
hangs, and finding out whether it works costs one track rather than a session.

**What we are not doing:** moving the production pin (`5bc654d`), declaring `GO`,
or filling `HANDSHAKE-TESTED` with anything other than what runs at the drive.

---

*Round 7 OPEN, verdict HOLD. Production pin `5bc654d`. Test pin `9003e6f`,
`cyanrip 0.9.4-rc1+platterpus.5-beta.1`, **a pre-release, not a verified pair** —
every log it writes says `NOT a released build`.
`tools/release-gate.py --release-gate` exits 1 against this record;
`--release-gate --prerelease` exits 0 after printing every open round.*
