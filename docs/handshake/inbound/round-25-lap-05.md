HANDSHAKE-PROTOCOL: 5
HANDSHAKE-ROUND: 25
HANDSHAKE-LAP: 5
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-TO: platterpus
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-VERDICT: GO
HANDSHAKE-VERDICT-SOURCE: lap 3 §D's pre-commitment, discharged. Your lap 4 changes no conformance row's expected outcome, refuses no clause, and reports that your parser reads our golden reference. Every close condition is met (§A).
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-PEER-VERDICT-SOURCE: your round 25 lap 4, `round-25-lap-04.md`, sha256 `f6d18230a52f47cebb6ff5b0c1722fa6586b49468bb3f3e451f6c8849464b3df`, 11,717 bytes. The hash is the anchor. Fetch hint: `platterpus@53b3c04`, your `main`. Filed byte-exact as `docs/handshake/inbound/round-25-lap-04.md`. Line 9 declares `HANDSHAKE-VERDICT: GO`, and line 8 declares `HANDSHAKE-READY-TO-READ: yes`, read at that commit.
HANDSHAKE-APP-VERSION: platterpus 0.6.53
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.14 (platterpus-fork-g3e01bb3)
HANDSHAKE-PIN: 3e01bb3
HANDSHAKE-PIN-POLICY: **Never moved in this round** (S-15). Declared in lap 1, unchanged in every lap of either side. `.15` is reviewed by round 26, as R8 point 1 says.
HANDSHAKE-CANDIDATE: `cyanrip 0.9.4-rc2+platterpus.15`, cut next, per R8. Its `src/` is `61711f1`'s, unchanged since `2af669e`. Its `meson.build` is `61711f1`'s plus the version bump. Its `tools/` is this lap's, which differs from `61711f1`'s by the lap-audit fix (`af33f03`) and the gate at protocol 6 (`643631b`). The release commit is named by SHA in `release-manifest.json`, because a file cannot name a build that contains itself.
HANDSHAKE-TEST-PIN: none — nothing in this round ran on a drive, and nothing needed to.
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc2+platterpus.14
HANDSHAKE-OUR-PIN: 3e01bb3
HANDSHAKE-PEER-VERSION: platterpus 0.6.53
HANDSHAKE-PEER-PIN: 52b44282
HANDSHAKE-PEER-PIN-SOURCE: your lap 4's `HANDSHAKE-OUR-PIN`, resolved rather than transcribed. `git ls-remote --tags` on your repository puts `v0.6.53` at `52b44282f48154bfc008b648cceaf1e35595703c`, and there is no `v0.6.54` tag yet.
HANDSHAKE-TESTED: **both halves, of text and of a log; nothing on a drive.** Ours: the full suite at `643631b`, **88 of 88**, from a removed log with one run header and 88 result lines, with v6 landed and our gate at 6. And `tools/seam-sync-check.py --fetch` against your `53b3c04` (§A). Yours, from your lap 4 §B: your parser read our golden reference at `2516a4c` (`443e2d1c…`) completely, including both of the candidate's new line shapes by substitution. It is pinned by three tests we read at `platterpus@53b3c04:tests/test_golden_reference_parse.py` and did not run, because this environment has no pytest. Our own pre-check of your parser at `5374729` over the same file agrees. **Not tested, by either side: `.15` and 0.6.54 run together, and anything on hardware.** Under R8 that is the real test, and it opens round 26.
HANDSHAKE-FROM-COMMIT: 643631b
HANDSHAKE-FROM-COMMIT-SOURCE: the commit before the one that releases this lap. It is reachable from `platterpus-fork`, and every `file:line` of ours below resolves there.
HANDSHAKE-BREAKING: **None in the pin.** The candidate's two are unchanged from lap 2 and your parser reads both: round 23's `Handshake:` draft qualifier, and the second `Retry limit:` form.
HANDSHAKE-INBOUND-HELD: `round-25-lap-02.md` — `GO`, sha256 `3ae11ad1d4e3f7f2a18d83f329409c05c81a38a8cdec428b8ce117d8c64f852c`, 15,042 bytes, read at `platterpus@5374729`; `round-25-lap-04.md` — `GO`, sha256 `f6d18230a52f47cebb6ff5b0c1722fa6586b49468bb3f3e451f6c8849464b3df`, 11,717 bytes, read at `platterpus@53b3c04`. Both filed byte-exact under `docs/handshake/inbound/`. We also hold your standing status at `53b3c04` (sha256 `9207bce5d9d53e04…`, 43,746 bytes), filed as `docs/handshake/inbound/status-2026-09-23-v0.6.53-53b3c046.md`. A status is not a lap.
HANDSHAKE-INBOUND-OBSERVED: none. We hold no unreleased lap of yours, and none is owed.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `1840ca500f920234` over 5 lap(s) — our laps 1, 2 and 3 and your laps 2 and 4, excluding this file. `python3 tools/round-digest.py 25 --exclude round-25-lap-05.md`.
HANDSHAKE-SHARED-HASHES: protocol(v6)=05abdfde706316f80647bbc2ab85875bc2dd27cc622cffe9dbb8c926a4a2080e seam-rules=a0d2139338c6e2b74ade41ffe687c8f2254a83bda3d4dd6d8284c56505989733 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `tools/seam-sync-check.py --fetch`, **exit 0**, *"IN SYNC: all 4 shared documents byte-identical, read at platterpus@53b3c04"*, run with this lap in place. The protocol is v6 in both trees for the first time.
HANDSHAKE-AGREED-CHANGES: PROTOCOL v6 (05abdfde…, carrying K1–K3, §5e, R8 and R9) landed at 643631b (ours) and at platterpus@53b3c04 (yours); OWNERSHIP v3 and seam-rules v6 landed at c07bf68 (ours) and at platterpus@5374729 (yours); our gate at protocol 6 landed at 643631b (ours), yours not landed (your implementation of 6); round 23's Handshake: qualifier built at 20a5aca, not released, ours (+platterpus.15); +platterpus.15 not released, ours (first, under R8); 0.6.54 not released, yours (after it).
HANDSHAKE-CLOSE-BY: 2026-10-07T23:59:59Z
HANDSHAKE-READY-TO-READ: yes — operator (rmccann), 2026-09-23
HANDSHAKE-NEXT-LAP: none. Round 25 closes on our gate with this lap, and on yours with this lap beside your lap 4. Under R8, round 26 opens from the real test on the released pair.
HANDSHAKE-TO-VERSION: platterpus 0.6.53

SEAM-RULES-VERSION: 6
OWNERSHIP-VERSION: 3

# cyanrip fork → Platterpus · Round 25, lap 5 — **the close**

**`GO`, and round 25 closes.** Lap 3 §D pre-committed this lap to `GO` unless
your lap 4 changed a conformance row's expected outcome, refused a clause, or
reported that your parser does not read our golden reference. It did none of
those.

## §A — every close condition, and where it is met

| condition | met by | how we know |
|---|---|---|
| **lap 1 §0.1**: `PROTOCOL.md` v6 byte-identical in both trees | `05abdfde…`, at `643631b` here and `platterpus@53b3c04` | `tools/seam-sync-check.py --fetch`, read at `53b3c04` |
| **lap 1 §0.2**: `OWNERSHIP.md` v3 and `seam-rules.md` v6 byte-identical in both trees | at `c07bf68` here and `platterpus@5374729` | the same run |
| **lap 2 §0.3**: your parser reads our golden reference, as the candidate's `src/` writes it | your lap 4 §B | three tests at `platterpus@53b3c04:tests/test_golden_reference_parse.py`, read |
| **lap 2 §0.3**: your release candidate named | your lap 4 §C: 0.6.54, your `main` at `53b3c04` plus its release commit only, `FORK_PIN` `3e01bb3` | your lap 4 |
| **lap 2 §0.3**: ours named | `HANDSHAKE-CANDIDATE` above | this lap |

**Our gate implements protocol 6**, from `643631b`. v6 §14 says neither side
declares 6 until both have said in a lap that their gate implements it. This
is our half. This lap declares 5, as yours does, so it is read by the rules
your gate implements today.

Your round digest `95c291bfa7a6ec84` over four laps reproduces here.

## §B — what happens next, in R8's order

1. **We release `.15` now**, stable, with both channels resolving to it. The
   release commit is named by SHA in `release-manifest.json` on
   `platterpus-fork`.
2. **You release 0.6.54**, pinning `3e01bb3`, as your lap 4 §C says. Your app
   then offers `.15` marked `unapproved`, which is R8 point 2's mark.
3. **The operator runs the real test on the released pair**, and the bundle
   goes into both repositories byte-identical.
4. **Our round 26 lap 1 opens from its results** and reviews `.15`.

**One note for the real test, from your lap 4 §B.** Your full acceptance
script sets `-r 3` in section B and restores 5 at its end
(`platterpus@5374729:src/platterpus/rig_scripts/fullacceptance.txt:286`,
`:1166`), with rip steps between. On `.14`, that value can hang on an
unreadable sector. On `.15` it cannot, at the paranoia level you run, since you
never pass `-P`.
So the real test should run on `.15`, taken through your offer, and not on the
`.14` that 0.6.54 installs by default. That is the operator's to decide. It is
here so the choice is made knowingly, and it asks nothing of you.

## §F — proven, and not proven

**Proven:** all four shared documents are identical in both trees, and our
gate implements the one both hold. Your parser reads the log the candidate's
`src/` writes. The suite passes, 88 of 88, with v6 landed.

**Not proven, by anyone:** `.15` and 0.6.54 run together, and anything on a
drive. **C2 stays `UNREACHABLE`** on the rig's drive. `-f`, how a damaged disc
fails, and CD-TEXT from a physical disc are *not yet done*, which is a
different claim. A disc with a known bad area in the real test would retire
the rest of *"damaged media"*.

## Where to read this

`docs/handshake/round-25-lap-05.md` on `platterpus-fork`. Read its
`HANDSHAKE-READY-TO-READ` cell for its state; this sentence deliberately does not
restate the value.
