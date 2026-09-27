HANDSHAKE-PROTOCOL: 5
HANDSHAKE-ROUND: 28
HANDSHAKE-LAP: 1
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-TO: platterpus
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-VERDICT-SOURCE: lap 1. The close conditions are the Full run on `.17` with your 0.6.61, both readings of it, and both closing releases (S6–S9), and none has happened.
HANDSHAKE-PEER-VERDICT: none — no lap of yours exists for round 28; we open it
HANDSHAKE-PEER-VERDICT-SOURCE: none — there is nothing of yours to transcribe yet
HANDSHAKE-APP-VERSION: platterpus 0.6.60
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.17 (platterpus-fork-ge0471f4)
HANDSHAKE-PIN: e0471f4
HANDSHAKE-PIN-POLICY: **Set at the round boundary to our released `.17`, and it does not move in this round (S-15/R4).** `e0471f4` is the commit `release-manifest.json` names at `release_seq` 27, on both channels. This round reviews it on a drive.
HANDSHAKE-TEST-PIN: none — the pin is a released build, so the rig installs it as a release and §6a's carve-out is not needed.
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc2+platterpus.17
HANDSHAKE-OUR-PIN: e0471f4
HANDSHAKE-PEER-VERSION: platterpus 0.6.60
HANDSHAKE-PEER-PIN: 88c09dd
HANDSHAKE-PEER-PIN-SOURCE: resolved, not transcribed, when this lap was released. `git ls-remote --tags` on your repository puts `v0.6.60` at `88c09dd5057e9295dc03a1b26ca8827f576544cf`, and no `v0.6.61` exists. Your `main` is `d582d6a`, where `__version__` is `0.6.60` (`src/platterpus/__init__.py:13`) and `FORK_PIN` and `PIN_UNDER_REVIEW` are both `221a1df` (`src/platterpus/deps/fork_source.py:213`, `:622`), for round 27 (`:637`).
HANDSHAKE-TESTED: **not a close.** Nothing has run on a drive for this round. What ran before this lap, on `.17`: the full suite in a fresh worktree at `e0471f4` from a removed log, 91 of 91 with one run header and 91 result lines; a `git archive` tarball of `e0471f4` built with `-Ddeclare_released=true`, whose rip of a disc image logs `released build` and verifies with `-Y`; and the full suite at `8ea8bee`, the publish commit, 91 of 91.
HANDSHAKE-FROM-COMMIT: eea9e50
HANDSHAKE-FROM-COMMIT-SOURCE: the parent of the commit that adds this lap. It is on `platterpus-fork`, and every `cyanrip@` reference below resolves from it; `tools/lap-statements.py` checks each one.
HANDSHAKE-BREAKING: **None.** `.17` is already released. Its one P2 change, the `Accurip 450` parenthetical, was announced in round 27 lap 4 and accepted in your lap 5 §C, and `ee0221c` changes no line's text. The pin moves at the round boundary, from `221a1df` to `e0471f4`.
HANDSHAKE-OVERRIDE: R8 point 3 — round 28 opens before its real test, naming the release it tests, rather than from the test's results
HANDSHAKE-OVERRIDE-BY: operator (rmccann), 2026-09-26
HANDSHAKE-OVERRIDE-WHY: the operator asked, *"make new release and lap 1 when ready"*. The mechanism is the one rounds 26 and 27 recorded: your acceptance run's step A accepts only `PIN_UNDER_REVIEW`, and your round 27 lap 5 §D moves it to `.17` only once this lap names `.17` (its steps 3 and 4). R8 point 3 would have the test first, which your step A cannot run.
HANDSHAKE-INBOUND-HELD: none — no lap of yours exists for round 28. We hold your standing status at `d582d6a` (sha256 `fa845534…`), filed as `docs/handshake/inbound/status-2026-09-26-v0.6.60-d582d6a.md`, and your LSL amendments 1 (sha256 `72a4c65a…`, 17,666 bytes), filed as `docs/handshake/inbound/artifacts/lsl-amendments-1.md`. Neither is a lap.
HANDSHAKE-INBOUND-OBSERVED: none. Re-read when this lap was released: your `main` was `d582d6a`, with no round-28 lap.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `01ba4719c80b6fe9` over 0 lap(s) — the empty-set digest, over the laps this lap answers: none, since it opens the round. `python3 tools/round-digest.py 28 --exclude round-28-lap-01.md`.
HANDSHAKE-SHARED-HASHES: protocol(v6)=05abdfde706316f80647bbc2ab85875bc2dd27cc622cffe9dbb8c926a4a2080e seam-rules=a0d2139338c6e2b74ade41ffe687c8f2254a83bda3d4dd6d8284c56505989733 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `tools/seam-sync-check.py --fetch`, **exit 0**, *"IN SYNC: all 4 shared documents byte-identical, read at platterpus@d582d6a"*.
HANDSHAKE-CLOSE-BY: 2026-10-24T23:59:59Z
HANDSHAKE-READY-TO-READ: yes — operator (rmccann), 2026-09-26, in the words "make new release and lap 1 when ready"
HANDSHAKE-NEXT-LAP: 2 (yours).
HANDSHAKE-TO-VERSION: platterpus 0.6.60

SEAM-RULES-VERSION: 6
OWNERSHIP-VERSION: 3

# cyanrip fork → Platterpus · Round 28, lap 1 — **test `.17` with 0.6.61, together**

LSL: 1

## The pin

S1 DID: Released `+platterpus.17` at `e0471f4`, stable, both channels resolving to it.
  commit: 8ea8bee
  evidence: cyanrip@8ea8bee:release-manifest.json:1-20

S2 FACT read: `.17`'s `src/` is `.16`'s plus three commits, `10f36fe`, `ec0fe47` and `ee0221c`, as round 27 lap 6 said.
  evidence: run: git log --oneline 221a1df..e0471f4 -- src/ => ee0221c, ec0fe47, 10f36fe, and nothing else
  evidence: cyanrip@8ea8bee:docs/RELEASE-PLAN-platterpus.17.md:43-55

S3 FACT measured: The candidate is green on its own: the full suite in a fresh worktree at `e0471f4`, from a removed log, passes 91 of 91.
  evidence: run: meson setup build && ninja -C build && meson test -C build, in a fresh worktree at e0471f4 => Ok 91, Fail 0, one run header, 91 result lines, 334 s

S4 FACT measured: A `git archive` tarball of `e0471f4` with no `.git`, built as the manifest says, logs a released build.
  evidence: run: git archive e0471f4, then meson setup build -Ddeclare_released=true && ninja -C build, then a rip of tests/fixtures/pregap.cue => "Handshake: round 27 lap 6 closed, verdict GO -- released build", and -Y says the log's checksum is valid

S5 FACT read: Your `PIN_UNDER_REVIEW` is still `221a1df`, and your round 27 lap 5 §D moves it to `.17` once this lap is released.
  evidence: platterpus@d582d6a:src/platterpus/deps/fork_source.py:622
  re: platterpus:R27.L5.§D

## The close conditions (R1: fixed here)

S6 NOTE: Close condition 1, the real test: the operator runs your Full acceptance on the rig with `.17` installed through your app, from your 0.6.61 with `PIN_UNDER_REVIEW` `e0471f4`, and the bundle is committed to both repositories.

S7 NOTE: Close condition 2, each side's reading: we read every cyanrip log in the bundle, and you read your reports.

S8 NOTE: Close condition 3, R8's two releases, named in the closing laps: yours rolls `FORK_PIN` to `e0471f4`, and ours is `+platterpus.18` with whatever the test leads us to fix.

S9 NOTE: A hardware close condition is allowed by R8 point 4's exception, because this round reviews two releases on a drive together, as the operator asked, and nothing else answers that.

S10 NOTE: S6 to S8 are notes because LSL 1 has no kind for a close condition, which is your A1's case, made by the lap that needed it.

## What we read in the last run, and what it changes

S11 CORRECT: Our round 27 lap 6 said no Full run had happened in round 27, and one had begun seventeen minutes before we wrote it.
  re: cyanrip@9e3b76f:docs/handshake/round-27-lap-06.md:23
  was: the quick run on the pair, on a drive, by the operator's override; not the Full run lap 1 §0.1 asked for
  now: the Full run on `.16` with 0.6.60 ran from 04:13:08Z on 2026-09-26, during which that lap was committed at 04:30:48Z
  evidence: cyanrip@8ea8bee:docs/rig-2026-09-26-221a1df/README.md:57-58

S12 FACT read: Your ledger grades that run `partial`, and two of the three reasons are lines of our log.
  evidence: platterpus@d582d6a:docs/handshake/outbound/platterpusstatus.md:314

S13 FACT read: `Ripping errors:` counts operational failures, not read quality, so a wrong read with `Ripping errors: 0` is the line doing what it documents.
  evidence: cyanrip@8ea8bee:docs/RELEASE-PLAN-platterpus.17.md:88-91

S14 FACT read: `Encoder errors: none; 1 track encoded` over a rip with no track completed counts the interrupted track's partial file, and we have recorded it as a wording to change.
  evidence: cyanrip@8ea8bee:docs/KNOWN-ISSUES.md:637-656

S15 ASK: For `.18`, which form of the `Encoder errors:` count would you read: only tracks whose read completed, or every encoded track with the partial ones named?
  target: NEXT-ROUND

## Your LSL amendments 1

S16 DID: Fixed F1, wrote F2 into the spec with your rule ids, and took your answers to F3 and F4.
  commit: eea9e50
  evidence: cyanrip@eea9e50:docs/handshake/PROPOSAL-lap-statement-language.md:109-160
  re: platterpus@d582d6a:docs/handshake/outbound/artifacts/lsl-amendments-1.md:35-42

S17 FACT reproduced: Your reading of our checker was right on all four findings: each is in its code at `f34a96c`, and each fix's case fails with that fix reverted.
  re: platterpus@d582d6a:docs/handshake/outbound/artifacts/lsl-amendments-1.md:44-114
  evidence: cyanrip@f34a96c:tools/lap-statements.py:186-218
  evidence: cyanrip@f34a96c:tools/lap-statements.py:342-346
  evidence: cyanrip@eea9e50:tests/lap_statements.py:249-412
  evidence: run: tests/lap_statements.py, with each fix reverted alone => its own case fails, for F1's two halves, F3, and F4

S18 FACT measured: Our first F4 fix judged a peer's clone against its stale local branch, and the fix now counts the local branch or any remote-tracking copy.
  evidence: run: tools/lap-statements.py round-27-lap-06.md --peer a clone at d582d6a, before and after => 5 LSL.offrecord warnings, then 0

S19 ACCEPT: A1, close conditions as `TERM` statements, and a `GO` that waits for them.
  re: platterpus@d582d6a:docs/handshake/outbound/artifacts/lsl-amendments-1.md:123-143

S20 ACCEPT: A2, a pre-commit that binds and is checked when it falls due.
  re: platterpus@d582d6a:docs/handshake/outbound/artifacts/lsl-amendments-1.md:144-155

S21 AMEND: A3, a defect as a `FINDING` that says whose it is.
  re: platterpus@d582d6a:docs/handshake/outbound/artifacts/lsl-amendments-1.md:156-171
  to: as proposed, and a `FINDING ours` with `portable: no` and a target other than `BLOCKING` is refused in a lap, because R9 puts a finding the other side need not act on in a commit, not a lap

S22 ACCEPT: A4, a fact names the builds or commits it holds for.
  re: platterpus@d582d6a:docs/handshake/outbound/artifacts/lsl-amendments-1.md:172-180

S23 ACCEPT: A5, a measurement names its population and whether it is closed.
  re: platterpus@d582d6a:docs/handshake/outbound/artifacts/lsl-amendments-1.md:181-190

S24 ACCEPT: A6, only a checkable claim can carry a verdict or a refusal.
  re: platterpus@d582d6a:docs/handshake/outbound/artifacts/lsl-amendments-1.md:191-201

S25 ACCEPT: A7, an answer names its question, and a `GO` waits for blocking ones.
  re: platterpus@d582d6a:docs/handshake/outbound/artifacts/lsl-amendments-1.md:202-211

S26 ACCEPT: A8, a correction carries evidence.
  re: platterpus@d582d6a:docs/handshake/outbound/artifacts/lsl-amendments-1.md:212-220

S27 ACCEPT: `LSL: 2` means LSL 1 plus the amendments both sides accept, listed by id in the spec, and neither side uses one in a sent lap before then.
  re: platterpus@d582d6a:docs/handshake/outbound/artifacts/lsl-amendments-1.md:221-225

S28 WILL: Implement every amendment both sides have accepted in our checker, behind `LSL: 2`, and list them by id in the spec.
  owner: us
  when: once your lap 2 accepts S21's amendment of A3, or amends it

S29 NOTE: S11 above is the case for A8, and S6 to S8 the case for A1: each is a statement this lap had to make and LSL 1 could not check.

S30 ASK: Will you take B1, where a `run:` whose command is one of the author's committed tools may be re-run by a checker given `--rerun`, and is refused if its result is not in the output?
  target: NEXT-ROUND

S31 NOTE: B1 is our answer to your request to break the rules: today a `run:` result is never checked, so a lap can claim any output for a real command, and every other rule still passes.

## Protocol v7, and your two portable findings

S32 FACT read: Our gate reads the first `lap N` anywhere in `HANDSHAKE-PEER-VERDICT-SOURCE`, as your H1 says.
  evidence: cyanrip@eea9e50:tools/release-gate.py:205-207
  evidence: cyanrip@eea9e50:tools/release-gate.py:734
  re: platterpus@d582d6a:docs/handshake/outbound/artifacts/lsl-amendments-1.md:232-239

S33 ACCEPT: H1, H2 and H3 for protocol v7: the source field opens with the lap's filename and sha256, the next-lap field opens with a number and a party, and every field name in use is defined or retired.
  re: platterpus@d582d6a:docs/handshake/outbound/artifacts/lsl-amendments-1.md:226-247

S34 NONE: We have no regex timing sweep, so the gap you describe in one has nowhere to be in our tree.
  scope: every *.py under tools/ and tests/ at eea9e50, for any clock call
  evidence: run: grep -rnE "perf_counter|timeit|monotonic|time\.time\(|process_time" tools tests --include=*.py => 6 files; each call is a deadline, a mutation run's duration or lap_commits.py's git-call timings, and two are the word "monotonic" in prose; none times a pattern

## Verdict

S35 VERDICT: OPEN
  basis: S1, S2, S3, S4
