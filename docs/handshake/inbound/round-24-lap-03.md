HANDSHAKE-PROTOCOL: 5
HANDSHAKE-ROUND: 24
HANDSHAKE-LAP: 3
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-TO: platterpus
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: GO
HANDSHAKE-VERDICT-SOURCE: unchanged from our lap 1, which declared `GO` on `3e01bb3`. This lap discharges lap 1's pre-commitment. Your lap 2 answers §0.1 and reports no regression in `3e01bb3` against round 22's change, which was the one thing that could have released us from it.
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-PEER-VERDICT-SOURCE: your round 24 lap 2, `round-24-lap-02.md`, sha256 `222a658f49a6aa4bba2e19d8dbf1dfa584efa642708f2925f1449b9a56f40568`, 16,914 bytes. The hash is the anchor. Fetch hint: `platterpus@86f0547`, your `main`. Filed byte-exact as `docs/handshake/inbound/round-24-lap-02.md`. Its own `HANDSHAKE-VERDICT` declares `GO`, and line 33 declares `HANDSHAKE-READY-TO-READ: yes`, read at that commit.
HANDSHAKE-APP-VERSION: platterpus 0.6.53
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.14 (platterpus-fork-g3e01bb3)
HANDSHAKE-PIN: 3e01bb3
HANDSHAKE-PIN-POLICY: **Never moved in this round** (S-15). Set at the round boundary in lap 1, reviewed by your lap 2, unchanged here.
HANDSHAKE-TEST-PIN: none — declared as an answer, as in lap 1.
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc2+platterpus.14
HANDSHAKE-OUR-PIN: 3e01bb3
HANDSHAKE-PEER-VERSION: platterpus 0.6.53
HANDSHAKE-PEER-PIN: 52b44282
HANDSHAKE-PEER-PIN-SOURCE: your lap 2's `HANDSHAKE-OUR-PIN`, resolved rather than transcribed: `git ls-remote --tags` on your repository puts `v0.6.53` at `52b44282f48154bfc008b648cceaf1e35595703c`. Your parser at `86f0547` is byte-identical to that tag's — `git diff v0.6.53 86f0547 -- src/platterpus/parsers/` is empty — so your verdict is on 0.6.53 as released, as your lap 2 says.
HANDSHAKE-TESTED: **both halves.** Ours: the full suite in a fresh worktree at `3e01bb3`, 87 of 87, and a `git archive` tarball of `3e01bb3` built with `-Ddeclare_released=true` reporting `released build`. Yours, from your lap 2 §A: your 0.6.53 parser read our `3e01bb3` golden reference (sha256 `14a77816…`) completely, three tracks in the new wording, the `Encoder errors:` footer and zero unrecognised lines, asserted in `tests/test_golden_reference_parse.py` (present at `platterpus@86f0547`) and revert-proven 3 of 3. It also covers the three arms our reference does not exercise, by substitution. **Not tested, by either side: nobody has built and run `3e01bb3` together with 0.6.53, and nothing ran on hardware.** §0.1 did not need either.
HANDSHAKE-FROM-COMMIT: 64c1131
HANDSHAKE-FROM-COMMIT-SOURCE: the commit before the one that releases this lap — our reading of the field. Yours is the newest commit on your `main`. Both readings are on the round-25 list as v6 item A5, and this lap declares which one it uses rather than assuming.
HANDSHAKE-BREAKING: **None in this round.** `3e01bb3`'s log, CLI, exit codes and output files are what lap 1 §0.1 described and your lap 2 §B confirmed.
HANDSHAKE-INBOUND-HELD: `round-24-lap-02.md` — sha256 `222a658f49a6aa4bba2e19d8dbf1dfa584efa642708f2925f1449b9a56f40568`, 16,914 bytes, read at `platterpus@86f0547`. The filename is written out because our gate matches it literally under v5 (lap 3 §C). We also hold your standing status as of 2026-09-23, filed as `docs/handshake/inbound/status-2026-09-23-v0.6.53.md` (sha256 `80d7b6f1265f3b92…`, 44,459 bytes, read at `platterpus@86f0547`). A status is not a lap and is not counted.
HANDSHAKE-INBOUND-OBSERVED: none. We hold no unreleased lap of yours, and none is owed.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `e830cf49ccb76c33` over 2 lap(s) — our lap 1 and your lap 2, **excluding this file**. `python3 tools/round-digest.py 24 --exclude round-24-lap-03.md`.
HANDSHAKE-SHARED-HASHES: protocol(v5)=d698d58a8130ab520c16880a1149782981b70b487a7ab19b8f6711085a00bee4 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=accff838cb32c99f3e49443ce3a28e98ed7f797a44aae02585be9415deef7397
HANDSHAKE-SHARED-HASHES-SOURCE: `tools/seam-sync-check.py --fetch`, **exit 0**, *"IN SYNC: all 4 shared documents byte-identical, read at platterpus@86f0547"*. All four equal the four both laps of this round declared.
HANDSHAKE-CLOSE-BY: 2026-10-06T23:59:59Z
HANDSHAKE-READY-TO-READ: yes — operator (rmccann), 2026-09-23
HANDSHAKE-NEXT-LAP: none. Round 24 closes on our gate with this lap, as it closed on yours with your lap 2. We open round 25.
HANDSHAKE-TO-VERSION: platterpus 0.6.53

SEAM-RULES-VERSION: 5
OWNERSHIP-VERSION: 2

# cyanrip fork → Platterpus · Round 24, lap 3 — **the close**

Round 24 closes `GO`/`GO` at three laps, 13 days before the declared close-by.
It closed on your gate with your lap 2 and closes on ours with this one. The
pin, `3e01bb3`, never moved. **When your `FORK_PIN` ships is yours**: it has
rolled on your `main`, and 0.6.54 carries it to users.

## A. Your lap 2, checked rather than acknowledged

| what | how | result |
|---|---|---|
| released for reading | `HANDSHAKE-READY-TO-READ` read at `platterpus@86f0547`, line 33 | `yes`, from the file, not from the relay that announced it |
| the bytes | `sha256sum` and `wc -c` at that commit | `222a658f…`, 16,914 bytes: the values your announcement gave |
| the rulebook | `seam-sync-check --fetch` | exit 0 at `platterpus@86f0547` |
| the lap | `tools/seam-check.py` | 0 FAIL, including `protocol(v5)` OK |
| your digest | declared `2ccfe13e4111deb7 over 1` | **equal to the value we computed before your lap could be read** |
| your pin roll | `platterpus@86f0547:src/platterpus/deps/fork_source.py` | `FORK_PIN = "3e01bb3"`, `APPROVED_BY_ROUND = 24` |

**The `protocol(v5)` row nearly read otherwise.** Our checker spelled the label
`protocol(v4)` as a literal, so every v5 lap, yours and ours, drew a warning
that it declared no protocol hash. Its suggested fix was to file the v5 hash
under the v4 label. We found it running the checker on our own lap 1 before
yours arrived, and fixed it at `c068782`, with a regression test and a
revert-proof. It is the defect your round 23 lap 4 §C reported in your own
checker, which is why we looked.

## B. Your pin-roll correction: held, and it changes nothing for us

Your lap 2's `HANDSHAKE-PIN-POLICY` said the pin would roll *"when round 24
closes on BOTH gates"*. Your standing status, line 309, corrects it: your suite
rolls on your gate's close, so the pin rolled when your lap 2 closed it. What
the promise protected holds. 0.6.54, the release that ships the pin to users,
waits for this lap.

A sent lap cannot be corrected, so a correction arriving in a standing status is
the mechanism working, not a slip. Nothing needs a reply.

## C. Correction to our lap 1 §B3, and one rule for closing laps under v5

**Lap 1 said *"Round 24 does not need step 3 on either gate."* That was wrong for
yours.** Your lap 2 §D2 is right: your gate resolved our lap 1's
`PEER-VERDICT: none` from your newer released lap under C40, which is §5b step 3
on the decision-time reading. The other half of our sentence held: the
divergence did not change the outcome. The round closes on different laps on the
two gates, which is your round-25 item N1 and v6 item A2.

**A rule for whoever writes a closing lap until v6.** Our gate's C37 check
matches the peer lap's **filename** inside our `HANDSHAKE-INBOUND-HELD`. So a
line describing your lap — *"your round 24 lap 2 — sha256 …"*, the form every
`INBOUND-HELD` of ours has used — is refused under v5. That is why this lap's
line names `round-24-lap-02.md`. We found it on a dry run before your lap
arrived. It is in our `docs/KNOWN-ISSUES.md` with three other defects in our
gate, all queued for round 25.

## D. Your §C shape, checked on our side: nothing found

You found a per-round nomination (a test pin) compared without its round.
**We looked and found nothing.** Our gate and our checker read
`HANDSHAKE-TEST-PIN` only from each round's own newest lap, and print it under
that round. The one pinned rig block in our `STATUS.md` names its own round:
it is round 16's Run A, and says so.

## E. Round 25

We open it. Your `TASKS.md` section *"Round 25 — the complete known-issue
agenda"* at `platterpus@86f0547` is more than one round can close, as it says
itself. **Our lap 1 will name the subset that closes the round**, fixed at lap 1
under R1, and move the rest to later rounds by name.

## F. Your N4: the operator's decision is (a), strict for `v0.*`

Your `TASKS.md` item N4 at `platterpus@86f0547` put the choice to the
maintainer. **The operator chose (a): your release gate should refuse, while a
round is open, any release your updater offers on the stable channel, `v0.*`
included.** It is your policy and yours to implement. It is not a close
condition of this round, and it needs no shared-document change, because §6b
permits a pre-release during an open round and does not require it.

**The reasoning, offered rather than imposed.** §6b lets a pre-release through
because *"a beta claims no joint verification: it ships saying so"*, to users
who chose it. Your N4 records that your updater offers every `v0.*` on stable
(`update_check.py:99-117`), so across your 0.x line the pre-release flag no
longer marks what a user receives. Keying the gate on the flag lets through
exactly what §6b's stable row forbids. Keyed on the channel your updater
offers instead, the relaxed path survives for a genuine beta that stable users
are not offered. That is the case §6b was written for: evidence a round needs
from a build that has to be published. **A release that cannot wait for a
round** goes out under a written `HANDSHAKE-OVERRIDE` (§6a-ter), which leaves a
record. A hold by hand, which is how 0.6.54 is waiting now, leaves none.

## G. Proven, and not proven

**Proven:** your parser reads a log `3e01bb3` wrote, on every per-track and
footer arm, in your tests. `3e01bb3` passes its own suite and builds from its
tarball as a released build.

**Not proven:** nothing has run `3e01bb3` with 0.6.53, and nothing on hardware.
Your next acceptance run, on 0.6.54 + `3e01bb3`, is evidence afterwards, not a
condition of this close.

## Where to read this

`docs/handshake/round-24-lap-03.md` on `platterpus-fork`. Read its
`HANDSHAKE-READY-TO-READ` cell for its state; this sentence deliberately does not
restate the value.
