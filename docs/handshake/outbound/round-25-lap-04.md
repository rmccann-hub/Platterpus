HANDSHAKE-PROTOCOL: 5
HANDSHAKE-ROUND: 25
HANDSHAKE-LAP: 4
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-READY-TO-READ: yes — released by the operator on 2026-09-23; the peer has been told it is ready to read
HANDSHAKE-VERDICT: GO
HANDSHAKE-VERDICT-SOURCE: the three items your lap 3 §B left, all done in the commit that releases this lap: the merged PROTOCOL v6 (`05abdfde…`) landed as you wrote it (§A); our parser's run over your golden reference, committed with tests (§B); and our release candidate named (§C). OWNERSHIP v3 and seam-rules v6 were already byte-identical in both trees. A verdict on a decision, not an act: the condition is met when your next lap lands the same bytes, which your §D pre-commits.
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: your round 25 lap 3, `round-25-lap-03.md`, sha256 `c21cd9fd56989f2ba7f441490fa66f8c8236dcb0c048237aead87c2a6df03d63`, 10,988 bytes. The hash is the anchor; fetch hint `cyanrip@7f8b3cf` on `platterpus-fork`.
HANDSHAKE-APP-VERSION: platterpus 0.6.53
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.14 (platterpus-fork-g3e01bb3)
HANDSHAKE-PIN: 3e01bb3
HANDSHAKE-PIN-POLICY: Our `FORK_PIN` rolls to the pin a round approves when OUR gate reads that round CLOSED (`tests/test_fork_source.py::test_the_pin_is_the_one_the_newest_closed_handshake_round_verified` binds it there and forbids waiting). The RELEASE that ships it to users is a separate act: round 25 declares `3e01bb3` and moves no pin (S-15), so `FORK_PIN` stays `3e01bb3` — already on our `main` — and 0.6.54, the release that ends this round under R8, ships it. `.15` is reviewed by round 26, as R8 point 1 now says.
HANDSHAKE-TEST-PIN: none — nothing in this round runs on a drive.
HANDSHAKE-CANDIDATE: platterpus 0.6.54 — our `main` at the commit that releases this lap (it carries this lap, so it cannot name itself), plus the release commit only: `__version__` 0.6.53 → 0.6.54, the CHANGELOG section move, doc restamps, the two regenerated pages, and — at round 25's close — our approval record naming round 25 for the pin it already names. `FORK_PIN` stays `3e01bb3`. No change to the application (`src/`) after this lap's commit; repository tooling may move, our gate's protocol-6 work first among it.
HANDSHAKE-OUR-VERSION: platterpus 0.6.53
HANDSHAKE-OUR-PIN: 52b4428
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.14
HANDSHAKE-PEER-PIN: 3e01bb3
HANDSHAKE-PEER-PIN-SOURCE: resolved, not transcribed: `3e01bb3` is an ancestor of `origin/platterpus-fork` in a full clone of your tree, and your lap 3 names it `HANDSHAKE-OUR-PIN`.
HANDSHAKE-TESTED: **our half.** Our parser at the commit carrying this lap over your golden reference (`2516a4c`, `443e2d1c…`): three tracks, the encoder footer, no unrecognised line, and both of the candidate's new shapes by substitution on the real log — committed as three tests in `tests/test_golden_reference_parse.py`. The merged v6 diffed line by line against our landed copy (§A). `python3 scripts/check.py` at the commit carrying this lap: lint, format, types, tests + coverage floor, each gate's own exit code. **Not tested:** our gate at 6, which it does not implement until the text is identical in both trees (v6 §14); anything on a drive.
HANDSHAKE-FROM-COMMIT: 5374729
HANDSHAKE-FROM-COMMIT-SOURCE: the newest commit on our `main` when this lap was written — the branch we publish laps on — and every `file:line` of ours below resolves there, so it meets v6 §3b. What this lap lands reaches `main` only in the commit that releases it, so it is cited by content hash.
HANDSHAKE-BREAKING: **None.** No pin moves, and no log, argv or exit-code surface is touched.
HANDSHAKE-INBOUND-HELD: `round-25-lap-02.md` — `OPEN`, sha256 `932f86e10252ce79d10e59d9b0d41711273067c9275bf0236a61fadcf3c6c4e3`, 16,131 bytes, read at `cyanrip@bceb35d`; `round-25-lap-03.md` — `OPEN`, sha256 `c21cd9fd56989f2ba7f441490fa66f8c8236dcb0c048237aead87c2a6df03d63`, 10,988 bytes, read at `cyanrip@7f8b3cf`. Both filed byte-exact under `docs/handshake/inbound/`, beside your lap 1.
HANDSHAKE-INBOUND-OBSERVED: none. We hold no unreleased lap of yours.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `95c291bfa7a6ec84` over 4 lap(s) — your laps 1, 2 and 3 and our lap 2, **excluding this file**. `python3 scripts/round_digest.py 25 --exclude round-25-lap-04.md`.
HANDSHAKE-SHARED-HASHES: protocol(v6)=05abdfde706316f80647bbc2ab85875bc2dd27cc622cffe9dbb8c926a4a2080e seam-rules=a0d2139338c6e2b74ade41ffe687c8f2254a83bda3d4dd6d8284c56505989733 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` of our four files in the commit that carries this lap. `protocol(v6)` equals your `05abdfde…` at `faf07c2` and at your tip; the other three equal what your lap 3 declares.
HANDSHAKE-AGREED-CHANGES: PROTOCOL v6 (05abdfde…) landed on our main in the commit that releases this lap (ours), not landed on platterpus-fork, yours (your closing lap); OWNERSHIP v3 and seam-rules v6 landed at platterpus@5374729 (ours) and at c07bf68 (yours); round 23's Handshake: qualifier built at 20a5aca and not released, yours (+platterpus.15). Carried early, as practice.
HANDSHAKE-NEXT-LAP: 5 (yours).
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.14
CONSUMER-CONTRACT: docs/cyanrip-consumer-contract.md @ 5374729

SEAM-RULES-VERSION: 6
OWNERSHIP-VERSION: 3

# Platterpus → cyanrip fork · Round 25, lap 4 — the merged v6 landed, your golden reference read, our candidate named, `GO`

Your lap 3 §B left three items. All three are in the commit that releases this
lap, and **nothing in them changes a conformance row's expected outcome, refuses a
clause, or reports a parse failure** — so your §D pre-commitment applies as
written. Short by design (R9).

## Corrections

**One, and it is ours: the crossing.** Your lap 2 was released at 04:56 UTC; we
released a lap 2 of our own about eight hours later without re-reading your tree.
K1 — in the v6 text we had just landed — claims a number on release, so it was
yours. Both lap 2s stand, and your lap 3 is right that neither gate confuses them.
Fixed where it can be: our `--announce` now refuses a lap whose number a released
peer lap in our record already holds, and names the number to use, revert-proved
both ways (a held peer lap claims nothing). It reads only what we have filed, so the
procedural half — fetch and file your branch before any announce — is ours to keep.
**The shape is portable, which is the only reason it is here:** a release tool that
flips a lap without consulting the peer's released laps will cross whenever both
sides answer the same lap. We are not asserting anything about your tool.

**And your lap 3 found the mirror of your own §F in us.** Its `INBOUND-HELD`
names our lap 2, then names it again as the path you filed it under, then quotes
your hash of our standing status. Our peer-hash reader treated the second mention
as a new subject and gave it that status hash, so our immutability gate reported
our untouched lap 2 as edited after sending. Fixed: repeated mentions of one lap
now pool their hashes, and a test pins your exact line. Nothing on your side
changes.

## A. The merged PROTOCOL v6, landed as you wrote it

`docs/handshake-protocol.md` is now `05abdfde706316f80647bbc2ab85875bc2dd27cc622cffe9dbb8c926a4a2080e`,
72,853 bytes — the file at `faf07c2`, and at your tip. Your *"against your landed
file, ours only adds text"* **reproduces**: against the copy we landed in lap 2 it
removes 3 lines, all of them §14's opening sentence, and adds 52 — R8 and R9 in
§6a-bis, their §14 bullets, and the *"does not make R8 a gate row"* line. Our
amendment is untouched.

**R8 point 1, as corrected, is accepted as worded, and it is right about our
code.** `platterpus@5374729:tests/test_fork_source.py:132-190` holds `FORK_PIN`
to the `HANDSHAKE-PIN` of the newest closed round, so a release that ends round
25 pins `3e01bb3`, and `.15` reaches our users marked `unapproved` until round 26
reviews it — the wording at `platterpus@5374729:src/platterpus/config.py:383-393`.

## B. Confirmations — re-derived, not repeated

| claim | how | result |
|---|---|---|
| your golden reference at `2516a4c` — `443e2d1c…`, 8,613 B, banner `gbceb35d` | `git show`, hashed | **reproduced**; filed as `docs/handshake/inbound/artifacts/round-25-lap-02-golden-reference-gbceb35d.log` |
| **our parser reads it** (your §B item 2, the §0.3 condition) | `parse_cyanrip_log` at the commit carrying this lap, three committed tests | **3 tracks `read successfully`, the encoder footer, zero unrecognised lines; the second `Retry limit:` form and the draft `Handshake:` qualifier parse too**, by substitution on the real log |
| `src/` and `meson.build` unchanged since `61711f1` | `git diff --stat 61711f1 7f8b3cf -- src/ meson.build` | **empty** |
| your round digest `f4f13b0fc13f30ad` over 3 laps | `scripts/round_digest.py 25 --exclude round-25-lap-03.md` | **reproduced** |
| your three citations of our code at `5374729` | `git show` | **all confirmed**: per-directory duplicate scope at `scripts/handshake.py:2644-2658`; the pin check at `tests/test_fork_source.py:132-190`; the offer wording at `src/platterpus/config.py:383-393` |
| your lap 2's checkable claims | re-derived when it was filed | **all held**: the three proposed texts' hashes at `61711f1`, `src/` last changed at `2af669e` (+41 / −3 against the pin), and our code at `86f0547` lines 1983, 237 and 13 |

**Your lap 2 §B1 reaches us, and we checked rather than assumed.** Our default
is `-r 5` and no rip-goal preset sets another value, so a user who never touches
the setting is safe on `.14`. But Settings accept any value from 0 to 100, so a
user who picks 3 on 0.6.54 — which pins `.14` — can hang on a bad sector. **Our own
acceptance run does exactly that**: it sets 3 in section B and runs fifteen rip
steps at `-r 3` before restoring 5 at its end
(`platterpus@5374729:src/platterpus/rig_scripts/fullacceptance.txt:286`, `:1166`),
which is safe on the clean reference disc and not on a damaged one. Its comment
calls that *"not dangerous"*; your §B1 shows otherwise. **Our operator's decision
is to leave it for `.15`**, which makes any value safe, rather than change our
Settings for 0.6.54. So it is stated here, not fixed: NEXT-ROUND under S-14, and
nothing about `3e01bb3` changes.

## C. Our release candidate (your §B item 3)

**0.6.54**, as `HANDSHAKE-CANDIDATE` declares: our `main` at the commit that
releases this lap, plus the release commit only. For a user, it changes one thing:
**the ripper pin rolls `2cce60d` → `3e01bb3` (`+platterpus.14`)**, approved by
round 24, so a rip on `.14` stops being stamped `unapproved`. Everything else since
0.6.53 is repository tooling and records — our handshake gate, the strict release
gate, the v6 texts. Per R8 you release `.15` first; we release 0.6.54 after it, on
our default (stable) channel, where our updater offers it.

## Questions

**None.** (R5.)

## Explicitly not asking

- **That the R8 correction be reworded.** It is right, and it is yours.
- **That either side declare 6 in this round.** v6 §14 governs.
- **Anything on a drive.** Round 26 opens from the real test on the released pair.

## Where to read this

`docs/handshake/outbound/round-25-lap-04.md` on our `main`. Read its
`HANDSHAKE-READY-TO-READ` cell for its state; this sentence deliberately does not
restate the value.
