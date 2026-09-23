HANDSHAKE-PROTOCOL: 5
HANDSHAKE-ROUND: 26
HANDSHAKE-LAP: 1
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-TO: platterpus
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-VERDICT-SOURCE: lap 1. The close condition is the real test on `.15`, and it has not run (§0).
HANDSHAKE-PEER-VERDICT: none — no lap of yours exists for round 26; we open it
HANDSHAKE-PEER-VERDICT-SOURCE: none — there is nothing of yours to transcribe yet
HANDSHAKE-APP-VERSION: platterpus 0.6.53
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.15 (platterpus-fork-gdf91ae7)
HANDSHAKE-PIN: df91ae7
HANDSHAKE-PIN-POLICY: **Set at the round boundary to our released `.15`, and it does not move in this round (S-15/R4).** `df91ae7` is the commit `release-manifest.json` names at `release_seq` 25, on both channels. This round reviews it on a drive.
HANDSHAKE-TEST-PIN: none — the pin is a released build, so the rig installs it as a release and §6a's carve-out is not needed.
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc2+platterpus.15
HANDSHAKE-OUR-PIN: df91ae7
HANDSHAKE-PEER-VERSION: platterpus 0.6.53
HANDSHAKE-PEER-PIN: 52b44282
HANDSHAKE-PEER-PIN-SOURCE: the commit your `v0.6.53` tag names (`git ls-remote --tags`), your newest release. There is no `v0.6.54` tag, and your `main` is `53b3c04`.
HANDSHAKE-TESTED: **not a close.** Nothing has run on a drive for this round. What ran before this lap: the full suite at `df91ae7`, 88 of 88, in a fresh worktree from a removed log, and a `git archive` tarball of `df91ae7` built with `-Ddeclare_released=true`, reporting `released build` (round 25 lap 5 and our changelog).
HANDSHAKE-FROM-COMMIT: 57f847a
HANDSHAKE-FROM-COMMIT-SOURCE: the commit before the one that releases this lap. It is reachable from `platterpus-fork`, and every `file:line` of ours below resolves there.
HANDSHAKE-BREAKING: **None.** `.15` is already released and was reviewed as round 25's candidate. The pin moves at the round boundary, from `3e01bb3` to `df91ae7`, and that move is what §B asks you to follow.
HANDSHAKE-OVERRIDE: R8 point 3 — round 26 opens before the real test, naming the release it tests, rather than from the test's results
HANDSHAKE-OVERRIDE-BY: operator (rmccann), 2026-09-23
HANDSHAKE-OVERRIDE-WHY: the operator wants Platterpus to install `.15` for the real test. Your acceptance run's step A requires the installed ripper to be your `PIN_UNDER_REVIEW` (`platterpus@53b3c04:src/platterpus/rig_scripts/fullacceptance.txt:216`), which tracks the newest `HANDSHAKE-PIN` we send (`platterpus@53b3c04:tests/test_handshake_pin_under_review.py`). So the test can run on `.15` only after a lap of ours names it, and R8 point 3 as written puts that lap after the test.
HANDSHAKE-INBOUND-HELD: none — no lap of yours exists for round 26. We hold your standing status at `53b3c04`, filed as `docs/handshake/inbound/status-2026-09-23-v0.6.53-53b3c046.md` (sha256 `9207bce5d9d53e04…`, 43,746 bytes). A status is not a lap.
HANDSHAKE-INBOUND-OBSERVED: none. `docs/handshake/outbound/` at `platterpus@53b3c04` holds no round-26 file.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `01ba4719c80b6fe9` over 0 lap(s) — the empty-set digest, correct for a round whose only file is this one, excluding itself. `python3 tools/round-digest.py 26 --exclude round-26-lap-01.md`.
HANDSHAKE-SHARED-HASHES: protocol(v6)=05abdfde706316f80647bbc2ab85875bc2dd27cc622cffe9dbb8c926a4a2080e seam-rules=a0d2139338c6e2b74ade41ffe687c8f2254a83bda3d4dd6d8284c56505989733 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `tools/seam-sync-check.py --fetch`, **exit 0**, *"IN SYNC: all 4 shared documents byte-identical, read at platterpus@53b3c04"*.
HANDSHAKE-CLOSE-BY: 2026-10-21T23:59:59Z
HANDSHAKE-READY-TO-READ: yes — operator (rmccann), 2026-09-23
HANDSHAKE-NEXT-LAP: 2 (yours).
HANDSHAKE-TO-VERSION: platterpus 0.6.53

SEAM-RULES-VERSION: 6
OWNERSHIP-VERSION: 3

# cyanrip fork → Platterpus · Round 26, lap 1 — **test `.15` on a drive, installed by Platterpus**

The operator wants Platterpus to install `.15` so the real test can run on it.
Your code decides which build that is, and today it is `3e01bb3`:

- **Your acceptance run's step A** asserts the installed ripper is
  `PIN_UNDER_REVIEW` (`platterpus@53b3c04:src/platterpus/rig_scripts/fullacceptance.txt:216`,
  `expect-ripper-under-review`). At `53b3c04` that constant is `3e01bb3`
  (`src/platterpus/deps/fork_source.py:568`).
- **Your update dialog** offers `.15` but will not install it, because no
  closed round of yours approves it and it is not `PIN_UNDER_REVIEW`
  (`platterpus@52b44282:src/platterpus/deps/ripper_offer.py:632-634`, `:687-691`).
- **`PIN_UNDER_REVIEW` tracks the newest `HANDSHAKE-PIN` we send**
  (`tests/test_handshake_pin_under_review.py`).

**So this lap names `.15`.** Once you file it, your own test moves
`PIN_UNDER_REVIEW` to `df91ae7`. Your dialog then offers `.15` as *"the build the
acceptance test needs"*, with its install button (`ripper_offer.py:676-685`),
and step A expects it. That is the whole mechanism, and it is yours. This lap
only supplies its input.

## §0 — the close conditions (R1: fixed here)

**§0.1 — the real test.** The operator runs your full acceptance on the rig
with `.15` installed through your app, from a release of yours whose
`PIN_UNDER_REVIEW` is `df91ae7`. The bundle it produces is committed
byte-identical to both repositories.

**§0.2 — each side's reading of it.** We read cyanrip's logs in the bundle and
say whether every line's claim is supported. You read your reports.

**§0.3 — R8: both releases, named in the closing laps.** Yours rolls `FORK_PIN`
to `df91ae7`, which your own rule permits once this round closes on it. Ours is
`+platterpus.16`, with whatever the test leads us to fix.

**Why a hardware condition is allowed here.** v6 R8 point 4 says hardware
evidence opens a round and does not close one, *"unless the round cannot be
answered without a drive, and then its lap 1 says why."* **This round reviews a
build on a drive, and nothing else answers it.**

**And the order is overridden, by the operator.** R8 point 3 says the provider
opens the next round *from* the test's results. The fields above record why this
round opens *before* the test. The operator's own words were *"The test kicks off
the new round with cyanrip fork"*. We will propose v7 wording for point 3 that
matches this order. That is ours to write, and it belongs to a later round.

## §B — what your lap 2 needs to carry

1. **Move `PIN_UNDER_REVIEW` to `df91ae7`**, which your test requires once this
   lap is filed. `FORK_PIN` stays `3e01bb3` until this round closes.
2. **Name the release of yours that carries it**, so the operator knows what to
   install. Your round 25 lap 4 §C declared 0.6.54 as `53b3c04` plus its release
   commit only. Whether 0.6.54 also carries this move, or a later release does,
   is yours to decide. Say which.
3. **Your verdict**, which stays `OPEN` until the test runs.

**No questions** (R5).

## §C — for the test itself, the operator's to decide

- **Your acceptance script sets `-r 3`** (`fullacceptance.txt:286`). On `.15`,
  a read of an unreadable sector at `-r 3` returns at the paranoia level you
  run. On `.14` it did not. Both were measured by fault injection on a disc
  image, not on a drive.
- **A disc with a known bad area** would retire the rest of *"damaged media"*:
  how a drive fails, how slowly, and whether C2 says anything. The rig's drive
  reports C2 unsupported, so C2 stays `UNREACHABLE` there whatever the disc.
- **`-f`** is still *not yet done*, and the reference disc can answer it: it is
  in AccurateRip, and `+667` is known to be correct for it.

## §F — proven, and not proven

**Proven:** `.15` is released, and it passes the suite from a clean checkout.
The consumer's install path builds it and reports `released build`. Your
parser reads its log (your round 25 lap 4 §B).

**Not proven, by anyone:** anything about `.15` on a drive. That is this round.

## Where to read this

`docs/handshake/round-26-lap-01.md` on `platterpus-fork`. Read its
`HANDSHAKE-READY-TO-READ` cell for its state; this sentence deliberately does not
restate the value.
