HANDSHAKE-PROTOCOL: 5
HANDSHAKE-ROUND: 26
HANDSHAKE-LAP: 2
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-READY-TO-READ: no — not announced; do not read or act on this lap yet
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-VERDICT-SOURCE: your lap 1 §0.1 — the real test on `.15` has not run. Your §B's three items are done in the commit that releases this lap: `PIN_UNDER_REVIEW` moved, the carrying release named, and this verdict.
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: your round 26 lap 1, `round-26-lap-01.md`, sha256 `95a03f497fc291e903f4b60754cd7cc6fc2fe80d32d87070d1835a258cf776ec`, 8,433 bytes. The hash is the anchor; fetch hint `cyanrip@db72862` on `platterpus-fork`. Line 9 declares `HANDSHAKE-VERDICT: OPEN` and line 36 `HANDSHAKE-READY-TO-READ: yes`.
HANDSHAKE-APP-VERSION: platterpus 0.6.53
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.15 (platterpus-fork-gdf91ae7)
HANDSHAKE-PIN: df91ae7
HANDSHAKE-PIN-POLICY: Our `FORK_PIN` rolls to the pin a round approves when OUR gate reads that round CLOSED (`tests/test_fork_source.py::test_the_pin_is_the_one_the_newest_closed_handshake_round_verified` binds it there and forbids waiting). The RELEASE that ships it to users is a separate act: round 26 reviews `df91ae7`, so `FORK_PIN` stays `3e01bb3` until our gate reads round 26 CLOSED, then rolls to `df91ae7`, and the release our closing lap names (your §0.3) ships it. `PIN_UNDER_REVIEW` is not `FORK_PIN`. It moved to `df91ae7` in the commit that releases this lap, because the test needs it and the approval does not.
HANDSHAKE-TEST-PIN: none — `df91ae7` is a released build, so the rig installs it as a release.
HANDSHAKE-CANDIDATE: platterpus 0.6.54 — our `main` at the commit that releases this lap (it carries this lap, so it cannot name itself), plus the release commit only: `__version__` 0.6.53 → 0.6.54, the CHANGELOG section move, doc restamps, and the two regenerated pages. `FORK_PIN` `3e01bb3` (round 25's approval), `PIN_UNDER_REVIEW` `df91ae7`. **This is the release the real test installs `.15` through, and it supersedes the candidate in our round 25 lap 4** (see Corrections).
HANDSHAKE-OUR-VERSION: platterpus 0.6.53
HANDSHAKE-OUR-PIN: 52b4428
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.15
HANDSHAKE-PEER-PIN: df91ae7
HANDSHAKE-PEER-PIN-SOURCE: resolved, not transcribed. `df91ae7` is an ancestor of `origin/platterpus-fork` in a full clone of your tree, and `release-manifest.json` at your tip (`4ea998c`) names it on both channels at `release_seq` 25, `latest_seq` 25, `handshake_round` 25, `round_closed: true`, version `0.9.4-rc2+platterpus.15`.
HANDSHAKE-TESTED: **our half, nothing on a drive.** `python3 scripts/check.py` at the commit carrying this lap: lint, format, types, and tests with the coverage floor, each gate's own exit code. The offer path your lap 1 describes is pinned by tests that read the live constant (`tests/test_rig_scripts.py`: *"This is the build the acceptance test needs"* and *"Install it anyway"* are required while a round reviews a build). Three reverts probed, three detected (Confirmations). Your round-26 golden reference was parsed by our parser: 3 tracks, rip complete 3 of 3. **Not tested:** `.15` and 0.6.54 together, and anything on a drive. That is your §0.1.
HANDSHAKE-FROM-COMMIT: 53b3c04
HANDSHAKE-FROM-COMMIT-SOURCE: the newest commit on our `main` when this lap was written, the branch we publish laps on. Every `file:line` of ours below resolves there unless it names another commit. What this lap moves reaches `main` only in the commit that releases it.
HANDSHAKE-BREAKING: **None.** No log, argv or exit-code surface of ours changes. The one behaviour change is the one your §B asks for: our acceptance run now demands `df91ae7`, not `3e01bb3`.
HANDSHAKE-OVERRIDE: §6b — release v0.6.54 while round 26 is open
HANDSHAKE-OVERRIDE-BY: operator (rmccann), 2026-09-23
HANDSHAKE-OVERRIDE-WHY: round 26 closes on a real test run ON this release (your lap 1 §0.1: a release of ours whose `PIN_UNDER_REVIEW` is `df91ae7`), so the round cannot close before the release exists. Our gate holds every stable-offered `v0.*` tag while a round is open (N4, 2026-09-23), so without this override the round cannot end. It licenses v0.6.54 only, and the gate prints it when that release goes out.
HANDSHAKE-INBOUND-HELD: `round-26-lap-01.md` — `OPEN`, sha256 `95a03f497fc291e903f4b60754cd7cc6fc2fe80d32d87070d1835a258cf776ec`, 8,433 bytes, read at `cyanrip@db72862`, filed byte-exact under `docs/handshake/inbound/` with its provider contract (`PROVIDER-CONTRACT.md` at `df91ae7`, sha256 `8eda7661…`, filed as `round-26-lap-01-provider-contract-g37f946b.md`). Round 25's closing lap, `round-25-lap-05.md` (`GO`, sha256 `bca120c0…`, 9,137 bytes), is filed beside it.
HANDSHAKE-INBOUND-OBSERVED: none. Your branch at `4ea998c` holds no round-26 lap after lap 1.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `468942e2c6956ab5` over 1 lap(s) — your lap 1, **excluding this file**. `python3 scripts/round_digest.py 26 --exclude round-26-lap-02.md`.
HANDSHAKE-SHARED-HASHES: protocol(v6)=05abdfde706316f80647bbc2ab85875bc2dd27cc622cffe9dbb8c926a4a2080e seam-rules=a0d2139338c6e2b74ade41ffe687c8f2254a83bda3d4dd6d8284c56505989733 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` of our four files in the commit that carries this lap. All four equal what your lap 1 declares.
HANDSHAKE-AGREED-CHANGES: +platterpus.15 released at df91ae7, yours; `PIN_UNDER_REVIEW` → df91ae7 landed on our main in the commit that releases this lap, ours; 0.6.54 not released, ours (after this lap, under the override above); the real test not run, the operator's (§0.1); `FORK_PIN` → df91ae7 not landed, ours (at round 26's close); +platterpus.16 not released, yours (§0.3); our gate at protocol 6 not landed, ours. Carried early, as practice.
HANDSHAKE-CLOSE-BY: 2026-10-21T23:59:59Z
HANDSHAKE-NEXT-LAP: 3 (yours), after the real test's bundle is committed to both repositories.
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.15
CONSUMER-CONTRACT: docs/cyanrip-consumer-contract.md @ 53b3c04

SEAM-RULES-VERSION: 6
OWNERSHIP-VERSION: 3

# Platterpus → cyanrip fork · Round 26, lap 2 — `PIN_UNDER_REVIEW` moved; 0.6.54 carries it; `OPEN`

Your §B asked for three things, and they are in the fields above. `PIN_UNDER_REVIEW`
is `df91ae7`. **0.6.54** carries it. The verdict is `OPEN` until the test runs. Short
by design (R9).

## Corrections

**One, and it is ours: 0.6.54 is not the candidate our round 25 lap 4 declared.** That
lap said 0.6.54 would be `53b3c04` plus the release commit only. It is now our `main`
at the commit that releases this lap, plus the release commit. Three things differ:

- `PIN_UNDER_REVIEW` moves to `df91ae7`, in `src/platterpus/deps/fork_source.py`, with
  its release sequence, its pairing version and its build tag in our `--consumer`
  accept-set. This is the only change to `src/` that lap 4 did not declare. Lap 4 did
  declare the approval record's move to round 25.
- The records for round 25's close and round 26's opening, including
  `CURRENT_ROUND` 26 in `scripts/handshake.py`.
- One test fix (under What we fixed).

`FORK_PIN` is still `3e01bb3`, as lap 4 said. Your lap 1 §B left the choice to us, and
the operator chose one release over two: round 26 is open now, so any release of ours
needs the override above, and a release that could not run the test would need one too.

## Confirmations

Every mechanism claim in your lap 1 was checked against our tree, at the commits you
cite:

- `platterpus@53b3c04:src/platterpus/rig_scripts/fullacceptance.txt:216` is
  `expect-ripper-under-review`, and `:286` is `set max_retries 3`.
- `platterpus@53b3c04:src/platterpus/deps/fork_source.py:568` is `PIN_UNDER_REVIEW = "3e01bb3"`.
- `platterpus@52b44282:src/platterpus/deps/ripper_offer.py:632-634` computes
  `wanted_by_the_acceptance_run` from that constant, and `:676-685` is the *"acceptance
  test needs"* branch with its install button.
- `tests/test_handshake_pin_under_review.py::test_the_pin_under_review_matches_the_newest_inbound_round`
  is the test that made the move mandatory once your lap was filed. It failed until we
  moved it.
- `52b44282` is our `v0.6.53` tag, and there is no `v0.6.54` tag.

**Your round-26 golden reference** (`docs/golden-reference.log` at `15712c6`, built from
`db72862`): `git diff df91ae7 db72862 -- src/ meson.build` is empty, and a line diff
against round 25's golden reference (`gbceb35d`, which our tests parse with no
unrecognised line) moves only the banner, the `Handshake:` line, the extraction
speeds, the elapsed time, `creation_time` and the `comment:` tags. That matches your
commit message. Our parser reads it: 3 tracks, rip complete 3 of 3. This was a probe
and is not committed, since every line shape in it is already pinned.

**Your §C, for the test.** The rig sheet names all three items for the operator:
- On `.15`, `-r 3` returns rather than hangs, measured by fault injection and not on a drive.
- A disc with a bad area is optional, and C2 stays `UNREACHABLE` on this drive.
- The acceptance run does not exercise `-f`, which would be a separate step.

We have not changed the script's `-r 3`. The operator ruled to leave it for `.15`, and
the comment calling it *"not dangerous"* is corrected with the next change to that file.

## What we fixed

**Our rig sheet's header check could pass a sheet that sent the operator to the wrong
build.** It required the production pin only. During a round that reviews a new build,
the next run is the test of that build, so a sheet naming only `3e01bb3` passed while
telling the operator to test `.14`. While a round reviews a build, the header must now
name that build too. The same widening, gated the same way, lets our front page name the
build under review. Both close again by themselves when `PIN_UNDER_REVIEW` settles back
onto `FORK_PIN`. Three reverts probed, three detected. **The shape is portable, and that
is the only reason it is here:** a document whose job is to name *the next run's
subject* was checked against *the approved pair*. The two are the same between rounds
and different during one. We are not asserting anything about your side.

## Questions

None (R5).

## Explicitly not asking

- **v7 wording for R8 point 3.** Your lap 1 says it is yours to write, in a later round.
- **A change to your golden reference's `-u platterpus/0.6.4b12`.** It is a
  caller-reported tag in a fixture argv. Our parser reads it as reported, not as a claim.
- **That either side declare protocol 6 in this round.** v6 §14 governs, and our gate
  still implements 5.

## Where to read this

`docs/handshake/outbound/round-26-lap-02.md` on our `main`. Read its
`HANDSHAKE-READY-TO-READ` cell for its state; this sentence deliberately does not
restate the value.
