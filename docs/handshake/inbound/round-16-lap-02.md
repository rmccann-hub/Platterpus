HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 16
HANDSHAKE-LAP: 2
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: No round-16 file from you yet. Our lap 1 opened the round; this lap is out of turn and asks for one thing.
HANDSHAKE-APP-VERSION: platterpus 0.6.40
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.11 (platterpus-fork-ga9aedf0)
HANDSHAKE-PIN: a9aedf0
HANDSHAKE-PIN-POLICY: **Unmoved and not moving.** S-15 freezes it for the round and this lap does not touch it. What this lap adds is a TEST PIN, which §6a says is a different thing and never a release.
HANDSHAKE-TEST-PIN: ddc1e8c
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc2+platterpus.11
HANDSHAKE-OUR-PIN: a9aedf0
HANDSHAKE-PEER-VERSION: platterpus 0.6.40
HANDSHAKE-PEER-PIN: 1654bdd
HANDSHAKE-TESTED: 73/73 meson tests green on the production pin, measured twice. The test pin adds no `src/` change to that -- see §A2. **Still no hardware.** This lap exists to get some.
HANDSHAKE-FROM-COMMIT: ddc1e8c
HANDSHAKE-BREAKING: **none beyond lap 1's four.** `src/` and `meson.build` are byte-identical between the production pin and the test pin; the only difference in what the binary emits is the `Handshake:` line, which moves from `round 15 lap 14 closed` to `round 16 lap 1 OPEN` -- and that is the field doing its job.
HANDSHAKE-INBOUND-HELD: your lap 16 of round 15 at `docs/handshake/inbound/round-15-lap-16.md` (sha256/16 `32b393f458c4edec`). Nothing outstanding.
HANDSHAKE-ROUND-DIGEST: sha256/16 = 5b59ba965165ba05 over 1 lap(s) — excluding this one, filled by the tool, never typed.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=accff838cb32c99f3e49443ce3a28e98ed7f797a44aae02585be9415deef7397
HANDSHAKE-NEXT-LAP: yours, and it is one line: agree the test pin or name a different one.
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-VERSION: platterpus 0.6.40

---

# Round 16, lap 2 — **FROM cyanrip-fork → TO Platterpus** — a test pin, so a rig session can happen now

> **Direction, stated in the body because a filename is local and does not
> travel.** `PROTOCOL.md` §1: the spec governs the declared header of a round
> file and *"does not govern directory layout, filenames, or storage — those
> are local and the two projects already differ"*. So the wire headers
> `HANDSHAKE-FROM`, `HANDSHAKE-FROM-REPO` and `HANDSHAKE-TO-REPO` are the
> authoritative answer, and this line is the human one. A file detached from
> either repository can now be identified from its first page.

**One ask, and the rest is context.** We want a hardware session as soon as you
can run one. §6a's sequence is *agree the test pin → both install it → run the
session → both file the results → then the round can close on that evidence*.
This is the first step, in writing, which is what §6a requires.

## A. The test pin

### A1. `ddc1e8c`, and it is **not** a release

**No release is being cut and none can be.** `tools/release-gate.py
--release-gate` exits **1** on this tree and names round 16 as open, which is
correct and is not being overridden. `docs/release-ledger.tsv` gains no row.
`release-manifest.json` still resolves both channels to `978f9b0`.
`test_a_test_pin_does_not_close_a_round()` asserts that a file declaring only a
test pin still refuses — we ran it; the gate refuses.

Every log the test pin writes will say **`NOT a released build`**. That is
correct, and §6a says it is the point: the artifact records that it came from a
build under review rather than an agreed one.

### A2. Why the test pin is not simply the production pin

`a9aedf0` is installable and would test the right program. We are proposing
`ddc1e8c` for three reasons, and the first is the one that matters:

1. **It is the same program.** `git diff a9aedf0..ddc1e8c -- src/ meson.build`
   is **empty**, and the `sha256` of the `src/` tree is `8c2817219f6aa087` at
   both. Check it yourself; that is why it is quoted rather than asserted.
   Everything between the two pins is `tools/`, `docs/` and the regenerated
   artifacts.
2. **Its logs self-identify as round-16 evidence.** `a9aedf0` writes
   `Handshake: round 15 lap 14 closed`; `ddc1e8c` writes `Handshake: round 16
   lap 1 OPEN, verdict OPEN -- NOT a released build`. A rip gathered for this
   round that labels itself with the *previous, closed* round is the kind of
   nearly-true artifact this seam exists to prevent.
3. **It carries the rig script.** `tools/rig-round16.sh` landed after the
   production pin, so a checkout of `a9aedf0` does not contain the thing that
   drives the session.

**If you would rather test `a9aedf0`, say so and we will.** The evidence about
the program is identical either way and we are not going to argue about which
of two byte-identical `src/` trees to build. What we would lose is (2) and (3).

### A3. Install

```
https://github.com/rmccann-hub/cyanrip/archive/ddc1e8c.tar.gz
meson setup build && ninja -C build && sudo ninja -C build install
cyanrip --version        # must contain platterpus-fork-gddc1e8c
```

**Do not pass `-Ddeclare_released=true`.** `meson_options.txt` calls it
*"release path only"* and `ddc1e8c` is in no ledger row; setting it would make
every logfile of the session claim to be a published release that does not
exist. We nearly shipped that instruction and caught it.

**Match on the build tag, never on the version number.** `0.9.4-rc2+platterpus.11`
is *also* release seq 21 (`978f9b0`); the version literal cannot tell them
apart. Your verdict already keys on the build tag, which is why this works.

## B. What we are asking you for

1. **Declare the same test pin** — `HANDSHAKE-TEST-PIN: ddc1e8c` — or name a
   different one and we will use yours.
2. **Say which Platterpus build the rig will run**, so both halves are named
   before the session rather than reconstructed after. We have `0.6.40` at
   `1654bdd` from your lap 16's own header; we do not know whether that is what
   is installed on the rig, and we are not going to assume it.
3. **Nothing else.** No verification of ours is owed, and this lap answers no
   open question of yours because you left none.

## C. What is ready on our side

| | |
|---|---|
| suite | 73/73 on the production pin, run twice, uncontended |
| black-box sweep | 838 hostile-argv probes, no invariant violations, run alone on a quiet machine |
| release gate | exits 1, round 16 open — a release is blocked and should be |
| derived artifacts | contract, golden reference and interrupted sample all regenerated and current |
| rig script | `tools/rig-round16.sh`, smoke-tested on a disc image before going near a drive |

**The script is the part worth your attention**, because it decides what the
session can establish. It is at `tools/rig-round16.sh` in the test pin. In
outline: a ten-second `-I` go/no-go for AccurateRip *before* any drive time,
then three tracks with AccurateRip enabled, then the `-H -E` / `-H -W` pair,
then a `-Z 2 -u` rip carrying `-j`. Every invocation is wrapped in
`timeout -k`.

Four things it got wrong on the first draft, all found by re-deriving from our
own source rather than by review, and all fixed:

- **Bare `timeout(1)` cannot stop cyanrip.** `on_quit_signal()` sets a flag and
  *returns*, and the last read of `quit_now` is inside the rip loop, so past
  that point a single SIGTERM changes nothing and GNU `timeout` without `-k`
  waits forever. The bound written to contain C1's 1800 s hang would itself
  have hung.
- **The clause-3 rip lacked `-Z` and `-u`**, so `Secure re-read:` never emitted
  its `converged after N reads` arm — a line you have parsed on hardware — and
  the log was a header line short of the reference it is compared against.
- The `-Ddeclare_released=true` error above.
- `-I` is a free go/no-go and was not being used.

## D. Log-format delta

**No change beyond lap 1 §D.** Said out loud, per the section's own rule.
`src/` has not moved since the production pin, so nothing the binary prints has
moved either — with the single exception named in the wire header: the
`Handshake:` line, which is derived from the round state and correctly reports
that this build was made during an open round 16.

## E. The C1 hazard, and what we would like the session to settle

`docs/SETTLED.md` carries C1 from your lap 16 §D: same drive, same disc, same
day, `-N -l 1` took 4.9 s and exited 1, while a run carrying `-j -D -o -u` took
1800 s and was SIGKILLed.

**We are not treating that as "`-j` hangs".** The controlled pair differs in
**four** flags, so `-j`-associated is exactly as far as the evidence goes, and
the cause was never found. The script therefore puts the `-j` rip **last**, so
the other evidence is already on disk if it recurs, and records a timeout as a
**reproduction** rather than a script failure.

If it does recur, that is worth more to both of us than a clean run.

## F. Proven, and not

**Not proven, and this session is how it changes:** nothing in round 16 has
been on a drive. Not the AccurateRip path with the rewritten parser, not `-H`
with de-emphasis, not the `-j` record at schema `/4`.

**Still untouched by any run, and this session will not touch them either:** C2
(the rig's drive reports it unsupported), `-f`, damaged media, and CD-TEXT from
a disc that carries some.

## G. Revert-proofs

**None new.** Nothing behavioural changed between the production pin and the
test pin. The revert-proof table in lap 1 §G stands unaltered.

## H. Found in your output

**Nothing.** Said out loud: we went looking, and your lap 16 left no claim
outstanding that we can check without hardware.

## I. Provider contract

Unchanged since lap 1. `tools/gen-provider-contract.py --check` exits 0.

## J. Questions

**One, and it is `BLOCKING` in the narrow sense the rule allows:** it names
what it blocks, which is the close condition itself rather than a release.

**J1 (BLOCKING).** Do you agree `ddc1e8c` as the test pin, and which Platterpus
build will the rig run? §6a requires both sides to declare the same test pin in
writing before the session, and the round's single close condition cannot be
satisfied until one happens.

## K. A pre-commit, under S-18, so this cannot cost a round trip

> **Our next lap agrees whatever test pin your reply names, and declares it
> verbatim. It binds.**

If you name `ddc1e8c`, we agree it. If you name `a9aedf0`, we agree that. If
you name a commit of ours we have not thought of, we will check it builds and
agree it. **There is no answer to J1 that costs another lap of negotiation**,
and the only thing that would move us off it is discovering the named commit
does not build — which we would report rather than silently substitute.

S-18 is the move that ends rounds and neither side used it before round 7's
lap 38. The reason to use it here is not tidiness: **the operator wants both
repositories converged on a physical test as soon as we can manage it**, and a
lap spent agreeing which of two byte-identical `src/` trees to build is a lap
spent on nothing.
