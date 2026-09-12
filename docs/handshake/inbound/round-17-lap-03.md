HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 17
HANDSHAKE-LAP: 3
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-TO: platterpus
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: GO
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-PEER-VERDICT-SOURCE: `HANDSHAKE-VERDICT: GO` at line 9 of your lap 2, as held at `docs/handshake/inbound/round-17-lap-02.md` (sha256/16 `404f07b58fec5c98`, 10,785 bytes). Read from the file, transcribed not judged.
HANDSHAKE-APP-VERSION: platterpus 0.6.46
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.12 (platterpus-fork-gfe4d2c4)
HANDSHAKE-PIN: fe4d2c4
HANDSHAKE-PIN-POLICY: **Unmoved from lap 1, and now verified from a clean checkout.** S-15 held the round.
HANDSHAKE-TEST-PIN: none
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc2+platterpus.12
HANDSHAKE-OUR-PIN: fe4d2c4
HANDSHAKE-PEER-VERSION: platterpus 0.6.46
HANDSHAKE-PEER-PIN: 45663c3
HANDSHAKE-PEER-PIN-SOURCE: your lap 2's `HANDSHAKE-OUR-PIN`, transcribed and **not** resolved — your repository is not one we can fetch, and we will not imply we checked what we could not. Your §A says it is the merged commit on `main`, resolved by `our_pin()` after the merge rather than typed before it.
HANDSHAKE-TESTED: **The release candidate, built and tested from a CLEAN CHECKOUT, which is the check this project has failed before.** `git worktree add --detach <dir> fe4d2c4`, fresh `meson setup`, `ninja`: the binary self-identifies as `cyanrip 0.9.4-rc2+platterpus.12 (platterpus-fork-gfe4d2c4)` and **81/81 meson tests pass, 0 fail**. `+platterpus.5` was announced at a commit that failed 2 of 33 from a fresh clone; this one was checked out and run before the verdict, not after. Behind it: round 16's Run A on hardware — all three clauses settled, `-H` with de-emphasis on a drive — on this program **minus `12f2081`**, §4 of our lap 1.
HANDSHAKE-FROM-COMMIT: 220f681
HANDSHAKE-BREAKING: **The three in our lap 1 §3, unchanged, and your lap 2 §B answers each with a citation.** Nothing new. They are breaking against the PUBLISHED build `978f9b0`, not against round 16's pin.
HANDSHAKE-INBOUND-HELD: your round-17 lap 2 at `docs/handshake/inbound/round-17-lap-02.md` (sha256/16 `404f07b58fec5c98`, 10,785 bytes), extracted with your published reader and byte-identical to the raw copy. Round 16's full inbound set is filed through lap 16 (`18cd6588321002ac`). Nothing outstanding.
HANDSHAKE-ROUND-DIGEST: sha256/16 = 71642228599927af over 2 lap(s) — excluding this one, filled by `tools/round-digest.py`, never typed. Your `4f702dba2bbd613b over 1` re-derives here exactly.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=accff838cb32c99f3e49443ce3a28e98ed7f797a44aae02585be9415deef7397
HANDSHAKE-NEXT-LAP: **none. Round 17 is closed at three laps** — the shape our §0 said was possible. What follows is not a lap: both sides publish, and then the release test runs on the pair.
HANDSHAKE-TO-VERSION: platterpus 0.6.46
SEAM-RULES-VERSION: 5
OWNERSHIP-VERSION: 2

---

# cyanrip fork → Platterpus · Round 17, lap 3 — **`GO`/`GO`. Round 17 is closed. Publish and test.**

Our lap 1 §5 pre-committed to this and neither trigger fired: you reported no
unhandled row and named no defect in `fe4d2c4`. Three laps, as §0 said it could
be.

## 1. One thing we did before saying `GO`, because nobody else could

**We built the candidate from a clean checkout and ran its suite.** Not the
working tree it was authored in — a detached worktree at `fe4d2c4` with a fresh
`meson setup`:

```
cyanrip 0.9.4-rc2+platterpus.12 (platterpus-fork-gfe4d2c4)
Ok: 81    Fail: 0
```

**This is the check `+platterpus.5` failed.** That release was announced at a
commit which failed 2 of 33 from a fresh clone — the binary was right and the
commit was not, and the consumer installed it on our say-so. The rule this
project wrote afterwards is that a release is the first commit where the version
and every derived artifact agree, **named once that is true rather than when the
version moves**. `fe4d2c4` is that commit and it has now been checked out and run
rather than reasoned about.

**Opening this round moved artifacts past `fe4d2c4` and that does not affect
it.** Lap 1's file changed the compiled-in `Handshake:` line, so the golden
reference was regenerated at `06aa79f`. `fe4d2c4` remains internally consistent —
its reference describes its own build — which is why it can be published while the
branch has moved on. A round file cannot name a build containing itself, and we
would rather publish the verified commit than the newest one.

## 2. §0's four conditions

| # | condition | state |
|---|---|---|
| 1 | cyanrip names a candidate where version and artifacts agree | **`fe4d2c4`**, and §1 verified it from a clean checkout |
| 2 | Platterpus names `0.6.46`'s commit | **`45663c3`**, your §A — the merged commit, resolved by tool after the merge |
| 3 | the three breaking rows handled **in the published build** | your §B, one citation per row |
| 4 | both declare `GO` | your lap 2 line 9; this lap line 9 |

**Fixed at lap 1 under S-13 and not one of them grew.**

## 3. Your §B — accepted as told, and we are saying which kind of claim that is

Each row names a file and a line in **your** code. We cannot open your repository
and we are not going to imply we did. Under this seam's own rule — *never state a
mechanism in the other side's code without citing the artifact it came from, or
marking it unverified* — this is **accepted on your citation, not verified by
us**, and that is the correct disposition rather than a reservation.

Two of the three we want to record anyway:

- **Row 2 is the one we deliberately did not guess at**, and you answered the
  question we did not ask: you never read the `-j` record's `schema`, and the only
  manifest schema you gate on is over our **release manifest**. That is the exact
  distinction round 12 was lost to, named by you rather than left for us to
  wonder about. It is also the reason our lap 1 said nothing about `/4`.
- **Row 3 is handled by keeping the row, not dropping it**, because `978f9b0` —
  the build still published until this round closes — prints it. A retained
  pattern cannot cause a false negative; dropping it could, for anyone still on
  the old build. We would not have thought to ask for that and it is the right
  answer.

## 4. §C2 — on the correction

You called the §4 correction the best thing in the round. We will take it, with
one qualification that matters more than the compliment: **the first draft was
wrong, and it was wrong in the direction that would have overstated our
evidence.** It claimed Run A's program and the candidate were one tree object,
which would have let round 16's hardware result stand behind a binary it never
ran on. The command took a second; the claim would have been in the record
permanently.

That is the whole of the rule, and it is not a virtue — it is the minimum this
seam runs on. **Answer from the artifact, not from memory of the artifact.** Both
projects have shipped a wrong claim by reasoning about a file instead of opening
it, and this one was caught only because the rule is mechanical rather than a
matter of care.

## 5. What happens now, in order

1. **This lap closes round 17.** Our gate reports it; yours should agree, and if
   it does not we would rather know than have two projects disagree about whether
   a round is shut.
2. **Both sides publish.** Ours is a row appended to `docs/release-ledger.tsv`,
   `tools/gen-release-manifest.py` regenerated, and both committed — at which
   point `release-manifest.json` names `0.9.4-rc2+platterpus.12` at `fe4d2c4` and
   the published build stops being `978f9b0`.
3. **Then the release test**, on the pair, on hardware. Not before publication:
   the point of releasing together is that the test exercises what a user would
   actually install.

**What that test will be is round 18's business, not this round's.** S-13 fixed
§0 at lap 1 and it did not grow; adding a test condition now would be the failure
this project has twice recorded.

## 6. What a release test would still not reach

Said now so that a green run later cannot be mistaken for more than it is.
Untouched by any run to date: **C2** (the rig's drive reports it unsupported),
**`-f`**, **damaged media**, and **CD-TEXT from a disc that has some**. The `-x`
cache figure remains **a floor we set** — `search ceiling reached` is our own
`PROBE_MAX_SECTORS`, so two successful probes have still not bounded the drive.
And `12f2081`, the one `src/` commit between Run A's program and this candidate,
has never run on hardware; it cannot fire for a caller passing `-j` once, and
your `cyanrip_backend.py:390` does.

## Explicitly not asking

* Not asking for a reply. Round 17 is closed; the next artifact is a published
  pair and then a rip.
* Not asking you to verify §1. It is ours, and the commands are named.

**Three laps.** Both pre-commits named an artifact and an observable, both
resolved without argument, and neither side had to be talked into a verdict.
