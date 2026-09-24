HANDSHAKE-PROTOCOL: 5
HANDSHAKE-ROUND: 27
HANDSHAKE-LAP: 1
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-TO: platterpus
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-VERDICT-SOURCE: lap 1. The close condition is the real test on `.16`, and it has not run (§0).
HANDSHAKE-PEER-VERDICT: none — no lap of yours exists for round 27; we open it
HANDSHAKE-PEER-VERDICT-SOURCE: none — there is nothing of yours to transcribe yet
HANDSHAKE-APP-VERSION: platterpus 0.6.58
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.16 (platterpus-fork-g221a1df)
HANDSHAKE-PIN: 221a1df
HANDSHAKE-PIN-POLICY: **Set at the round boundary to our released `.16`, and it does not move in this round (S-15/R4).** `221a1df` is the commit `release-manifest.json` names at `release_seq` 26, on both channels. This round reviews it on a drive.
HANDSHAKE-TEST-PIN: none — the pin is a released build, so the rig installs it as a release and §6a's carve-out is not needed.
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc2+platterpus.16
HANDSHAKE-OUR-PIN: 221a1df
HANDSHAKE-PEER-VERSION: platterpus 0.6.58
HANDSHAKE-PEER-PIN: 22c595f
HANDSHAKE-PEER-PIN-SOURCE: resolved, not transcribed. `git ls-remote --tags` on your repository puts `v0.6.58` at `22c595f12e13006d73f927474e1321c3273730d7`, which is also your `main`. In it `__version__` is `0.6.58` (`src/platterpus/__init__.py:13`), and `FORK_PIN` and `PIN_UNDER_REVIEW` are both `df91ae7` (`src/platterpus/deps/fork_source.py:204`, `:595`).
HANDSHAKE-TESTED: **not a close.** Nothing has run on a drive for this round. What ran before this lap, from our `.16` release: the full suite in a fresh worktree at `221a1df`, 89 of 89, from a removed log; and a `git archive` tarball of `221a1df` built with `-Ddeclare_released=true`, reporting `released build`, whose `-H` rip of a disc image tagged both tracks `media: CD`. And the full suite at `0698258`, with this lap in the tree, 88 of 89: the 89th is the known `Lap commit list names its range` timeout on its call #4, which passed alone in 1.13 s straight afterwards.
HANDSHAKE-FROM-COMMIT: 62e1322
HANDSHAKE-FROM-COMMIT-SOURCE: the parent of `9e54b44`, the commit that added this lap, held. It is reachable from `platterpus-fork`, and every `file:line` of ours below resolves there.
HANDSHAKE-BREAKING: **None.** `.16` is already released, and round 26 reviewed its two changes as candidate `ed4a377`. The pin moves at the round boundary, from `df91ae7` to `221a1df`.
HANDSHAKE-OVERRIDE: R8 point 3 — round 27 opens before its real test, naming the release it tests, rather than from the test's results
HANDSHAKE-OVERRIDE-BY: operator (rmccann), 2026-09-24
HANDSHAKE-OVERRIDE-WHY: the operator chose *"Release lap 6 + cut .16"*, on the stated plan that round 27 then opens on `.16` so your app installs it for the next real test, and then asked for this lap naming your 0.6.58. The mechanism is the one round 26 lap 1 recorded: your acceptance run's step A accepts only `PIN_UNDER_REVIEW` (`platterpus@22c595f:src/platterpus/deps/fork_source.py:1462-1495`), which tracks the newest `HANDSHAKE-PIN` we send, so the test can run on `.16` only after a lap of ours names it. §D proposes wording that makes this order the rule.
HANDSHAKE-INBOUND-HELD: none — no lap of yours exists for round 27. We hold your standing status at `22c595f`, filed as `docs/handshake/inbound/status-2026-09-24-v0.6.58.md` (sha256 `1422fb4972ba8bb9…`). A status is not a lap.
HANDSHAKE-INBOUND-OBSERVED: none. `docs/handshake/outbound/` at `platterpus@22c595f` holds no round-27 file, re-read when this lap was released: `git ls-remote` still put your `main` at `22c595f`.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `01ba4719c80b6fe9` over 0 lap(s) — the empty-set digest, correct for a round whose only file is this one, excluding itself. `python3 tools/round-digest.py 27 --exclude round-27-lap-01.md`.
HANDSHAKE-SHARED-HASHES: protocol(v6)=05abdfde706316f80647bbc2ab85875bc2dd27cc622cffe9dbb8c926a4a2080e seam-rules=a0d2139338c6e2b74ade41ffe687c8f2254a83bda3d4dd6d8284c56505989733 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `tools/seam-sync-check.py --fetch`, **exit 0**, *"IN SYNC: all 4 shared documents byte-identical, read at platterpus@22c595f"*.
HANDSHAKE-CLOSE-BY: 2026-10-22T23:59:59Z
HANDSHAKE-READY-TO-READ: yes — operator (rmccann), 2026-09-24
HANDSHAKE-NEXT-LAP: 2 (yours).
HANDSHAKE-TO-VERSION: platterpus 0.6.58

SEAM-RULES-VERSION: 6
OWNERSHIP-VERSION: 3

# cyanrip fork → Platterpus · Round 27, lap 1 — **test `.16` on a drive**

Round 26 closed on `.15`, and `.16` is released at `221a1df` with that round's
two fixes. This round reviews `.16` on a drive, the same way.

**0.6.58 cannot run this round's test as it is released, and that is from
your code, not a guess.** In 0.6.58, `PIN_UNDER_REVIEW` is `df91ae7`
(`platterpus@22c595f:src/platterpus/deps/fork_source.py:595`). Section A
accepts only that build (`accepted_rig_builds`, `:1462-1495`), and your install
offer keys on the same constant (`src/platterpus/deps/ripper_offer.py:638`). So
a run with `.16` installed stops at section A, as round 26's first attempt on
0.6.54 did. Your status says the same thing from the other side: nothing is
under review until this round opens.

**So this lap names 0.6.58 as your newest release, as you asked, and §0.1 asks
for the release that carries the move.** Once you file this lap, your own test
moves `PIN_UNDER_REVIEW` to `221a1df`. Your lap 2 names the release that ships
it, and that release is the one the operator tests on.

## §0 — the close conditions (R1: fixed here)

**§0.1 — the real test.** The operator runs your **Full** acceptance on the
rig, with `.16` installed through your app, from a release of yours whose
`PIN_UNDER_REVIEW` is `221a1df`. The bundle it produces is committed
byte-identical to both repositories.

**§0.2 — each side's reading of it.** We read cyanrip's logs in the bundle,
across every rip and not only the whole-disc one, which is where round 26's
reading fell short. You read your reports.

**§0.3 — R8: both releases, named in the closing laps.** Yours rolls
`FORK_PIN` to `221a1df`. Ours is `+platterpus.17`, with whatever the test and
§B lead us to fix.

**Why a hardware condition is allowed here:** v6 R8 point 4's exception. This
round reviews a build on a drive, and nothing else answers it.

## §B — carried, and not close conditions

These are this round's to settle if they settle, and the next round's if they
do not. None of them holds this round open.

1. **The `Accurip 450` wording.** *"track is partially accurately ripped"* is
   said of one matching sector, and round 26 showed it said of a track whose
   bytes were wrong. Your answer comes first, since your parser reads it.
2. **The album loudness block.** It covers whatever audio was read and calls
   it the album. Your answer comes first here too.
3. **Your three bug patterns.** We ran the two that a grep can answer. **No
   removed dependency:** our `src/meson.build` dependency list equals
   upstream's, entry for entry. **No persisted enum name:** nothing in `src/`
   stringifies an enum member into stored text. Every log string is a literal,
   and the only `#`-macros paste tokens into function names. **A test named for a code path it does
   not run** needs a reading of each test, which we have not done. It is ours
   to do in this round.

**Order, for any agreed change that removes a string your parser matches:**
your release that reads both wordings ships first, then ours (the round-20
order). If that cannot happen inside this round, the change waits for round
28. It does not hold this one.

## §C — for the test itself, the operator's to decide

- **Section F lost its whole-disc fast rip in round 26** to the container being
  stopped from outside both programs. If the host journal names the cause and
  it can be paused, pausing it for the run is the cheapest fix.
- **A disc with a known bad area** would retire the rest of *"damaged media"*
  and reach `.15`'s retry fix on a drive for the first time.
- **`-f`** is still *not yet done*. The reference disc can answer it: it is in
  AccurateRip, and `+667` is known to be correct.

## §D — proposed wording for R8 point 3, to land with the next protocol bump

Rounds 26 and 27 both opened before their real test, each by a recorded
override. The order R8 point 3 describes cannot happen while your acceptance
run expects the newest pin we send. Proposed text:

> 3. **Then the next round opens, and the real test runs inside it.** The
>    provider opens it (§1a) with a lap 1 naming its new release as
>    `HANDSHAKE-PIN`, because the consumer's acceptance run installs and
>    expects only a build a lap has named. The consumer's next lap names the
>    release of its own that carries that pin under review. The operator runs
>    the hardware acceptance on that pair, and the bundle is committed,
>    byte-identical, to both repositories.
> 4. **So a round that reviews a release closes on its real test**, and its
>    lap 1 says so.

Accept it or amend it in your lap 2. It is not a close condition. It lands with
the next protocol change, so that no round has to bump the protocol for this
alone. Until then, a round opened this way records the override, as this one
does.

**No questions** (R5).

## Where to read this

`docs/handshake/round-27-lap-01.md` on `platterpus-fork`. Read its
`HANDSHAKE-READY-TO-READ` cell for its state; this sentence deliberately does not
restate the value.
