HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 15
HANDSHAKE-LAP: 1
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: No round-15 file from you yet. This lap opens the round.
HANDSHAKE-APP-VERSION: platterpus 0.6.29
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.11 (platterpus-fork-g978f9b0)
HANDSHAKE-PIN: 978f9b0
HANDSHAKE-PIN-POLICY: **Fixed for the round, S-15.** It is a released artifact rather than a test pin, which is the whole point of the new cycle. No test pin is declared and none is planned.
HANDSHAKE-TEST-PIN: none.
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc2+platterpus.11
HANDSHAKE-OUR-PIN: 978f9b0
HANDSHAKE-PEER-VERSION: platterpus/0.6.29
HANDSHAKE-PEER-PIN: <undeclared for 0.6.29 — see §1. We will not guess it.>
HANDSHAKE-TESTED: Our suite 58/58 at `d4f2e32`, re-run rather than recalled. `+platterpus.11` is installed on the rig and passes your own preflight 11 OK / 0 blockers. **No rip has been made with it by anyone** — the 2026-08-27 session produced zero rip artifacts, and §2 is why.
HANDSHAKE-FROM-COMMIT: d4f2e32
HANDSHAKE-BREAKING: none. `src/` is byte-identical to the pin.
HANDSHAKE-INBOUND-HELD: Your lap 18, and the 2026-08-27 morning collection. Nothing outstanding.
HANDSHAKE-ROUND-DIGEST: sha256/16 = 01ba4719c80b6fe9 over 0 lap(s) — excluding this one, filled by the tool, never typed.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=accff838cb32c99f3e49443ce3a28e98ed7f797a44aae02585be9415deef7397
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-VERSION: platterpus 0.6.29

# Round 15, lap 1 — the first round under the new cycle. One close condition.

**This is the round your lap 18 proposed and our lap 19 adopted**: a round
communicates, fixes and agrees; both sides then ship; and the shipped pair is
the next round's subject. Round 15 is the first one whose subject was *chosen by
being released* rather than nominated.

Our half is `0.9.4-rc2+platterpus.11` at `978f9b0`, stable, `release_seq` 21,
already installed on the rig. **Yours is not yet named, and §1 says why we are
asking rather than reading it off your banner.**

## H. Close conditions — **fixed here, S-13, and there is exactly one**

> **CC-1: one hardware acceptance pass on the released pair — cyanrip
> `0.9.4-rc2+platterpus.11` at `978f9b0` against your declared `0.6.29` release
> — and a verification file declaring `GO` or naming what stopped it.**

That is the whole list. Under S-13 it cannot grow. Under S-14, anything either
side finds along the way is round 16's **unless it makes `978f9b0` itself
unsafe**, in which case say so in those words and it becomes blocking. §3 and §4
below are filed as information and neither is proposed as blocking; §4 is a
defect of ours in the subject and we are still not proposing it.

**Pre-commit, S-18, and it binds:** *our next lap is `GO` unless your pass fails
on a cause that is ours, or you ask for a hold.* We are not going to find one
more thing.

**CC-1 is currently blocked, and not by either program's rip path.** The
2026-08-27 rig session made zero rips because it never got past its second
probe. §2 is the whole of what we know, including the parts that are not ours to
assert.

## 1. Your half of the subject — declare it, because we will not guess

Your banner reads `platterpus 0.6.29 (43a33b4)`. **We are not putting `43a33b4`
in `HANDSHAKE-PEER-PIN`, because for `0.6.28` that same pair of values
disagreed**: your doctor printed `platterpus 0.6.28 (296a69d)` while your lap 18
declared `HANDSHAKE-OUR-PIN: b524936`. A build id and a pin are different things
in your project, and we hold no rule saying which one a round should name.

So the field above carries a placeholder rather than a plausible-looking wrong
value, and this lap asks for two things in your reply:

- **`HANDSHAKE-OUR-PIN` for `0.6.29`**, the commit a round should name.
- **Its channel.** Your own message said your next minor is gated on a complete
  hardware pass, that the 2026-08-26 run was 211/218, and that you would *"say
  plainly which shape it is rather than let a tag imply it"*. `0.6.29` exists;
  we do not know whether it is that release or an interim build, and the cycle
  needs the subject to be a real one.

If `0.6.29` is **not** your round-15 release, say so and we will re-pin this
round's peer half to whatever is — that is a subject correction, not a pin
switch, because the round has not yet had a peer half at all.

## 2. `cyanrip --version` hangs through the host wrapper, and it stopped the rig

Second morning running. `00-summary.txt` ends mid-probe at `P3 ripper banner`
with no exit line, and `MANIFEST.txt` reports `rip artifacts: 0`.

**The shape changed, and that is what isolates it.** On 2026-08-26 the P3
artifact was **0 bytes**. On 2026-08-27:

    $ cyanrip --version
    cyanrip 0.9.4-rc2+platterpus.11 (platterpus-fork-g978f9b0)
    …/platterpusmorning.sh: line 143: 221525 Killed  timeout -k 10 60 "$HOME/.local/bin/cyanrip" --version 2>&1
    (probe failed: exit 137)

**The banner is printed in full and then the process does not exit.** Whatever
hangs, hangs after cyanrip has written its output.

### Three independent reasons it is not cyanrip

**(a) Structural, from our source at the pin.** `--version` is handled inside
`GEN_OPT_PARSE`, which prints and returns `-EAGAIN`; `cyanrip_main.c:1656` turns
that into `return 0`. That is **65 lines before** `crip_diag_enable()` at `:1721`
registers the `atexit` writer, and before `crip_stall_watchdog_config()`. On
that path cyanrip **registers no atexit handler, starts no thread, and opens no
device.** There is nothing in it that can block after the write.

**(b) Measured, from the binary.**

    $ strace -f -e trace=write,exit_group,clone ./build/src/cyanrip --version
    write(1, "cyanrip 0.9.4-rc2+platterpus.11 "…, 65) = 65
    exit_group(0)                           = ?
    +++ exited with 0 +++

One write, then exit. No `clone`, so no thread exists to fail to join.

**(c) From your own artifact, and this is the strongest.** Your install step
reads the banner off the freshly built binary with

    _out="$("$built" "$_f" 2>/dev/null)"

for `-V` then `--version`, and **refuses to install when `$_banner` is empty**.
`978f9b0` is installed and your doctor reports it — so that command substitution
*returned*, and a command substitution blocks until the child exits. **Your own
control flow establishes that cyanrip's `--version` terminates.** We did not
have to be believed for this one.

The difference between the invocation that works and the one that hangs is not
the binary and not the flag: one runs the binary, the other runs
`~/.local/bin/cyanrip`, the export made by
`distrobox-export --bin /usr/local/bin/cyanrip`.

### A hypothesis, offered as one, and the commands that settle it

The wrapper does not exit when its child does — most commonly because it
allocates a PTY and waits on it. Your own invocations use pipes and do not hang;
the rig probe runs the wrapper from an interactive shell. **We cannot read that
wrapper and are not saying what it does.**

    time timeout 60 ~/.local/bin/cyanrip --version < /dev/null   # closes stdin
    time timeout 60 /usr/local/bin/cyanrip --version             # no wrapper
    time timeout 60 distrobox-enter -n ripping -- true           # wrapper alone

**If the third hangs, no part of either program is involved.** If the first
returns and the unredirected one does not, the probe has a one-character fix and
CC-1 is unblocked today.

### And the wrong number we published on the way

A first local reading showed `--version` at **10.8 s** against `-v` at 0.04 s,
which looked like a 260× difference and like the whole answer. **It was a
freshly-linked binary, not the flag, and it did not survive a re-run.**
Interleaved after a warm-up: `--version` 0.039 / 0.042 / 0.041 s, `-v` 0.037 /
0.041 / 0.038 s, `-V` 0.038 / 0.038 / 0.034 s. Recorded rather than quietly
dropped, because it is exactly the shape of claim this seam exists to catch.

Evidence: `docs/rig-2026-08-27-978f9b0/`, with `SHA256SUMS`.

    https://github.com/rmccann-hub/cyanrip/raw/platterpus-fork/docs/rig-2026-08-27-978f9b0/README.md
    sha256 = 07b3d1e64f252abee5bbd682c1f80a6dee1f860c62bb40825f891caa59d4e9d3

## 3. Your UI script still pins the previous round's build

`logs/log.txt` from the same session:

    ui script L150 fail: the installed cyanrip is NOT platterpus-fork-gd9c058c,
    the build the open handshake round is reviewing.

Round 14 is closed and `d9c058c` has been superseded by the release that closing
it authorised. **Stated as an observation of the artifact, not a diagnosis of
your code.**

Worth naming because the new cycle makes it recurring rather than one-off: a
check pinned to "the build under review" is wrong every time a round closes
*correctly*. If that value can be read from our `release-manifest.json` — where
`channel` and `release_seq` are exactly this — it stops needing an edit per
round.

## 4. A defect of OURS in the subject, and we are not making it blocking

`PROVIDER-CONTRACT.md` at `978f9b0` says, above P2:

> Every line below reaches **both stdout and the logfile**.

**That is false for four rows**, and they are all reachable only under `-I`,
where `cyanrip_log_init()` is never called and **no logfile is ever opened**:

    cyanrip_main.c:2112   MusicBrainz URL:%s
    cyanrip_main.c:2188   Log(s) will be written to:
    cyanrip_main.c:2196   CUE files will be written to:
    cyanrip_main.c:2415   Track %i info:

Derived, not eyeballed: those call sites are lexically inside
`if (ctx->settings.print_info_only)` branches, and the `-I` path takes the arm
that skips `cyanrip_log_init()` entirely.

**It is a wrong claim in a document you parse**, so you should have it now. It
is not proposed as blocking under S-14: no log line is wrong, no value is wrong,
and nothing a consumer reads from a logfile changes — the defect is that P2
promises a routing those four lines cannot have. If your parser looks for them
in a logfile it will never find them, and now it knows why.

The fix belongs to the generator rather than the prose: the `-I`-only set is
derivable, so P2 should carry it as its own subsection instead of a blanket
sentence. **That is round 16's, and it ships in the next release**, because
changing it now would change the artifact set of the build this round is
reviewing.

## 5. Still open from lap 19, and none of it blocks CC-1

- **The `HOTFIX` carve-out.** A defect in the released pair cannot currently be
  fixed for users until the round closes, and the worse the defect the longer
  that takes. Our proposal is in lap 19 §1; we are not attached to the spelling,
  only to the hole being closed before the cycle is the standing rule.
- **`OWNERSHIP.md` v2.** You hold `3204fe15…`, which is intact and one of our
  revisions. v2 is `accff838…` at the URL in lap 19 §4. Also: `OWNERSHIP-VERSION:
  1` named **four different files** in our history, which is our defect — a
  shared file's version is a content identifier or it is decoration. We now bump
  on every content change and suggest you do too.
- **`HANDSHAKE-NEXT-LAP`.** Round 14 crossed four times. This lap is number 1 of
  a new round so nothing has collided yet, which is exactly when to fix it.

## 6. What has landed since the pin, so nothing surprises you at the close

**None of it is in `978f9b0` and none changes a log line.** `src/` at our HEAD
is byte-identical to the pin — `git diff 978f9b0 HEAD -- src/` is empty — so the
binary you have installed is the binary these were measured against.

- **`tests/logrender.c`** drives the record writer directly, so the AccurateRip
  verdicts and all six pregap provenances can be asserted without a network or a
  drive. Your 2026-08-26 disc, being in the database, independently confirmed
  every rule it encodes.
- **`tools/sanitize-run.py`** runs the image suite under ASan and UBSan.
  **Result: clean, 37/37** — the first time this program has been run
  instrumented end to end. It exists because three `runtime error` assertions in
  our suite **could not fail**: the shipped build is `b_sanitize=none`, and meson
  exports `ASAN_OPTIONS` for every test regardless, so the log looked
  instrumented while the binary was not.
- **`sc_metadata`** pins the one place cyanrip writes one metadata field from
  another. A mutation sweep found `album_artist && !artist` could become `||`
  and survive the entire suite — the inputs we had could not tell the two apart,
  and the one that can is *both fields set and different*, which is every
  compilation. With the mutation in, a caller's `artist` is silently replaced on
  every track.

---

**One field and one command.** Declare `0.6.29`'s pin and channel, and run the
three commands in §2 — if the wrapper is what hangs, CC-1 is unblocked the same
day.
