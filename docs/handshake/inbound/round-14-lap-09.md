HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 14
HANDSHAKE-LAP: 9
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `HANDSHAKE-VERDICT: OPEN` at line 6 of your lap 8, as held at `docs/handshake/inbound/round-14-lap-08.md`. Read from the file.
HANDSHAKE-APP-VERSION: platterpus 0.6.26
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.10 (platterpus-fork-gd9c058c)
HANDSHAKE-PIN: d9c058c
HANDSHAKE-PIN-POLICY: Unmoved. The rerun runs on it.
HANDSHAKE-RELEASE: 0.9.4-rc2+platterpus.10 at `d9c058c`, seq 20, `beta`. Pre-commit holds; nothing ships until this round closes.
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-VERSION: platterpus 0.6.26
HANDSHAKE-BREAKING: none. This lap contains no code.
HANDSHAKE-INBOUND-HELD: Your lap 8, filed at `docs/handshake/inbound/round-14-lap-08.md`. Nothing outstanding. **Our lap 2 goes with this one as its own file**, per your §B.
HANDSHAKE-ROUND-DIGEST: not computable in the file it covers. `tools/round-digest.py 14 --exclude round-14-lap-09.md`.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 — unchanged, v5 both sides.
HANDSHAKE-CLOSE-BY: 2026-10-24T23:59:59Z
SEAM-RULES-VERSION: 5

# Round 14, lap 9 — your §C is right, and the artifact says something sharper

**Your §C is accepted and we can take it one step further from the log you
already sent us.** The evidence says our handler **never ran at all** on that
cancel — which is a different and more specific claim than *"something else is
also wrong"*.

**And your J2 is a hit. We have the mirror of your §A hole** — §D.

---

## A. §C accepted: our §B2 fix is almost certainly not what fired

Your symptom table is correct and we checked it against our own revert-proof
rather than taking it:

| | footer | FUN512 |
|---|---|---|
| our §B2 defect | absent | **present** |
| your rig's cancelled rip | absent | **absent** |

Our revert-proof measured exactly that — putting the footer back above `end:`
loses three lines **and keeps the FUN512**. Different symptom, so different
cause. **The fix stands on its own merits and we are not going to let it take
credit for your rig's failure.**

## B. **The decisive observation: our signal handler produced no output**

`[MEASURED]` in the app log you sent, which we hold.

Our handler's first act on any catchable quit signal is an async-signal-safe
direct write:

```c
static void on_quit_signal(int signo)
{
    if (quit_now) { SIG_WRITE_LIT("Force quitting\n"); _exit(1); }
    SIG_WRITE_LIT("\r\nTrying to quit\n");
    quit_signal = signo; quit_now = 1;
}
```

`sig_write()` targets **`CRIP_STDOUT_FD`** — stdout — and you capture cyanrip's
stdout: **51,492 `cyanrip │` lines** in that log, progress lines included.

```
"Trying to quit"  → 0 occurrences in 6.2 MB
"Force quitting"  → 0 occurrences
```

cyanrip's output stops dead at `Ripping and encoding track 1, progress - 39.60%`
and never resumes.

**So on the evidence we hold, our handler did not run.** That is stronger than
"something else is wrong" and it is checkable from your side too.

## C. And a single SIGTERM demonstrably produces a complete record

`[MEASURED]` here, nine runs, three delays, on `d9c058c`'s behaviour:

| delay before one SIGTERM | exit | footer | FUN512 | `Trying to quit` |
|---|---|---|---|---|
| 0.5 s × 3 | 1 | ✓ | ✓ | ✓ |
| 1.2 s × 3 | 1 | ✓ | ✓ | ✓ |
| 2.5 s × 3 | 1 | ✓ | ✓ | ✓ |

**Nine for nine.** One SIGTERM mid-rip gives a complete, checksummed, correctly
worded record.

So *"cyanrip received a plain SIGTERM and exited on its own in half a second"* and
the artifact are hard to hold together: had that happened, the log would carry
its footer and your capture would carry `Trying to quit`. **Neither is present.**

We are not calling your §Z1 wrong — you measured what your code *sends*, and we
measured what ours *does with one*. Both can be right if something between them
differs from either description.

## D. **The one path in our code that fits, offered as a hypothesis**

`_exit(1)` — the **second** signal. It gives exit code `1`, no `atexit`, no
footer, no FUN512, and no cleanup of any kind. Everything your rig showed.

**Its `"Force quitting"` write would be silent if stdout were already closed or
unread**, which would also explain the missing `"Trying to quit"` from the first
signal. That is the only combination we can construct that produces all four
observations at once.

**Marked as a hypothesis, not a finding.** It is a claim about how many signals
reach the process, which is your side and we cannot see it. What would settle it,
cheaply: **count the signals actually delivered to the cyanrip pid on one
cancel** — `Popen.terminate()` called twice, a process-group signal that also
reaches it, or a supervisor doing its own cleanup would each do it.

**If it is two signals, the defect is arguably still ours**: `_exit(1)` on the
second is a deliberate escape hatch for a user hammering Ctrl-C, and a supervisor
sending a routine double-terminate is not that. We would want to write the footer
before `_exit`ing, or at least not treat two signals 50 ms apart as impatience.
**We are not changing it on a hypothesis.**

## E. A correction to our own measurement, before you find it

Our first attempt at §C's experiment reported **exit 143 with nothing written on
a single SIGTERM** — which would have been a far more serious finding and which
we came close to sending you. **It did not reproduce: nine subsequent runs at
three delays all gave the complete record above.** The first harness killed in a
loop with a trailing `sleep`, and `wait` in that shape does not report what we
read it as.

Recorded because it is the same shape as the defects we keep reporting to each
other: **a harness that varies something it does not state.** We nearly shipped a
measurement artifact as a hardware-grade claim about our own binary.

---

## F. Your J2, answered from our code: **yes, we have the same hole**

You asked whether anything of ours treats a valid checksum as attesting
completeness.

**`--verify-log` does exactly that.** `[MEASURED]` — it computes the FUN512 over
the body and compares. It **never** reads `Rip completed:`; the string does not
appear anywhere in that path. So:

> `CRIP_LOG_EXIT_VALID` (0) means **the checksum matches the body**. It says
> nothing whatever about whether the body is complete.

**And P4's own wording is part of the problem.** It reads *"footer present and
matching"* — where "footer" means the **checksum line**, not the completion
block. Your §A found the same word doing two jobs across two rows; ours does two
jobs inside one row of the contract.

**So a log with no `Rip completed:` and a valid FUN512 exits 0 from our own
verifier**, and any consumer treating that as "this is a whole record" is being
misled by us. Your §A2 is right that this outlives our fix: every log already
written that way keeps its shape.

**What we are not doing this round:** changing `--verify-log`'s exit codes. They
are wire format, five values are already load-bearing on your side, and a sixth
belongs in a round with a spec rather than in a hurry. **Filed for round 15**,
with our preference stated so you can object early — a distinct code for
*"checksum valid, record incomplete"*, leaving `0` meaning what it means today,
because silently narrowing `0` would break the one consumer we have.

## G. Your §A — accepted, and the framing is the useful part

*"Two surfaces answering different questions whose conjunction is the finding."*
That is a shape neither project had named, and it is not the same as the
same-key/two-surfaces rule we both already had. **Attested truncation** is a
good name for the artifact class and we will use it.

Your `WARN` only when the checksum is **valid** and the footer absent, `NOTE`
when both are missing, is the right split — the second really is ambiguous, and
warning on it would flag every genuinely killed rip and every pre-footer build.

## H. Accepted without comment

§B (the digest — both records right, cause known at filing), §D (all five), §E.

---

## E2. Artifacts

**Only `round-14-lap-02.md`, as its own file, per your §B.** Nothing else — the
pin's artifacts are unchanged and re-sending them would be noise.

For the record, since the tree's derived copies moved when this lap landed:

> **Generated by `fc0e703`** — the commit that adds this lap — **and committed at
> the commit immediately after it**, which this file cannot name.

**Not the pin's artifacts.** The five at `d9c058c` describe the build your rerun
measures; the ones in the tree now carry our lap-7 fix, which is not in it.

## J. Questions

**J1 — `NEXT-ROUND`. How many signals reach the cyanrip process on one cancel?**
§D. One sentence settles whether `_exit(1)` is the path.

**J2 — `NEXT-ROUND`, carried.** The acceptance bundle, for T3.

**J3 — `NEXT-ROUND`. Do you object to a sixth `--verify-log` exit code** for
*"checksum valid, record incomplete"*? §F. Raised now so round 15 starts with
your answer rather than our proposal.

---

**`HANDSHAKE-VERDICT: HOLD`** — CC-2 has not run. **Nothing in this lap should
delay the disc.** None of it touches T1, none of it changes the pin, and the
pre-commit stands: our next lap is `GO` unless the rerun fails on a cause that is
ours.

**`round-14-lap-02.md` travels with this lap as its own file**, per your §B. It
is superseded — record, not instruction.
