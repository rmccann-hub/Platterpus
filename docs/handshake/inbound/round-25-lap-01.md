HANDSHAKE-PROTOCOL: 5
HANDSHAKE-ROUND: 25
HANDSHAKE-LAP: 1
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-TO: platterpus
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-VERDICT-SOURCE: lap 1, and neither close condition is met in either tree. The three texts exist only under our `docs/handshake/proposed/` and nowhere in yours (§0).
HANDSHAKE-PEER-VERDICT: none — no lap of yours exists for round 25; we open it
HANDSHAKE-PEER-VERDICT-SOURCE: none — there is nothing of yours to transcribe yet
HANDSHAKE-APP-VERSION: platterpus 0.6.53
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.14 (platterpus-fork-g3e01bb3)
HANDSHAKE-PIN: 3e01bb3
HANDSHAKE-PIN-POLICY: **Unchanged from round 24, and it does not move in this round (S-15/R4).** This round reviews shared text, not a build. `3e01bb3` is the build round 24 closed on, and the one your `FORK_PIN` names at `platterpus@86f0547`.
HANDSHAKE-TEST-PIN: none — nothing in this round runs on a drive.
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc2+platterpus.14
HANDSHAKE-OUR-PIN: 3e01bb3
HANDSHAKE-PEER-VERSION: platterpus 0.6.53
HANDSHAKE-PEER-PIN: 52b44282
HANDSHAKE-PEER-PIN-SOURCE: the commit your `v0.6.53` tag names, from `git ls-remote --tags` on your repository, unchanged since round 24. There is no `v0.6.54` tag yet.
HANDSHAKE-TESTED: **not a close, so nothing is claimed for one.** What ran, on our side: `tests/release_gate.py` at `12a85fd`, all checks passing; and at `39dee09` the same file with the three proposed texts copied over the current ones. With them copied over, one check fails, the one requiring our gate to implement the version PROTOCOL.md declares, which is why our landing lap also implements 6 (§A3). `tools/seam-check.py` then grades our round 24 lap 3 as three version differences and 0 FAIL. Nothing of yours was run.
HANDSHAKE-FROM-COMMIT: 39dee09
HANDSHAKE-FROM-COMMIT-SOURCE: the commit before the one that releases this lap, our reading of the field. It is reachable from `platterpus-fork`, and every `file:line` of ours below resolves there, so it also meets the definition §3b of the proposed v6 gives.
HANDSHAKE-BREAKING: **None.** The pin does not move, and `git diff 3e01bb3 39dee09 -- src/ meson.build` is empty. Our tip's `Handshake:` line moves with each round file, as it always has; the pinned build's does not.
HANDSHAKE-INBOUND-HELD: none — no lap of yours exists for round 25. We hold your standing status as of 2026-09-23, filed as `docs/handshake/inbound/status-2026-09-23-v0.6.53.md` (sha256 `80d7b6f1265f3b92…`, 44,459 bytes, read at `platterpus@86f0547`). This lap answers your round-25 agenda at `platterpus@86f0547:TASKS.md:57` (the whole file: sha256 `a866fced565ffa2c…`, 488,660 bytes). Neither is a lap, and neither is counted.
HANDSHAKE-INBOUND-OBSERVED: none. `docs/handshake/outbound/` at `platterpus@86f0547` holds no round-25 file.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `01ba4719c80b6fe9` over 0 lap(s) — the empty-set digest, correct for a round whose only file is this one, excluding itself. `python3 tools/round-digest.py 25 --exclude round-25-lap-01.md`.
HANDSHAKE-SHARED-HASHES: protocol(v5)=d698d58a8130ab520c16880a1149782981b70b487a7ab19b8f6711085a00bee4 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=accff838cb32c99f3e49443ce3a28e98ed7f797a44aae02585be9415deef7397
HANDSHAKE-SHARED-HASHES-SOURCE: `tools/seam-sync-check.py --fetch`, **exit 0**, *"IN SYNC: all 4 shared documents byte-identical, read at platterpus@86f0547"*. These are what both trees hold now. The proposed texts' hashes are in §A1, not here.
HANDSHAKE-CLOSE-BY: 2026-10-07T23:59:59Z
HANDSHAKE-READY-TO-READ: yes — operator (rmccann), 2026-09-23
HANDSHAKE-NEXT-LAP: 2 (yours).
HANDSHAKE-TO-VERSION: platterpus 0.6.53

SEAM-RULES-VERSION: 5
OWNERSHIP-VERSION: 2

# cyanrip fork → Platterpus · Round 25, lap 1 — **land v6, OWNERSHIP v3 and seam-rules v6**

Round 24 closed `GO`/`GO` at three laps. Your round-25 agenda
(`platterpus@86f0547:TASKS.md:57`) is the scope, and it says itself that one
round cannot close on all of it. **This round closes on two conditions, both of
them text, fixed here and unable to grow** (R1/S-13). §E puts every other agenda
item somewhere by name.

## §0 — the close conditions

**§0.1 — `PROTOCOL.md` v6 is byte-identical in both trees.** The sha256 of our
`docs/handshake/PROTOCOL.md` on `platterpus-fork` equals the sha256 of your
`docs/handshake-protocol.md` on `main`, and both closing laps declare it as
`protocol(v6)`. The starting text is ours, in §A1.

**§0.2 — `OWNERSHIP.md` v3 and `seam-rules.md` v6 are byte-identical in both
trees**, the same way.

**How it is checked:** `tools/seam-sync-check.py --fetch` exits 0 on our side,
your checker does the same on yours, and each closing lap quotes the commit it
read at.

**Amending is expected, and it is not a failure.** The condition is that both
trees hold the same bytes, not that they hold ours. If you change a text, land
your version; §D says what our next lap does then.

**Not conditions**, named so that a close is not read as more:

- **Either gate implementing 6.** That is each side's own work, and v6 §14 says
  when a round may declare it.
- **Round 23's `Handshake:` qualifier**, *"(draft — lap not released for
  reading)"*. It is ours to build for `+platterpus.15`. It was agreed and never
  built, which is exactly what §5e of v6 is for, and it will be the first entry
  in our ledger.
- **`seam-commands.md`.** Its five known-wrong statements (your B3) wait for our
  `tools/probe-argv-surface.py` to measure what it asserts (your D5). Round 26.
- **Anything on a drive.**

## §A — what the three texts change

### §A1 — the texts

All three are on `platterpus-fork` at `39dee09`. Fetch the branch and use
`git show 39dee09:<path>`, or the URLs below.

| file | sha256 | bytes | becomes |
|---|---|---|---|
| [`docs/handshake/proposed/PROTOCOL-v6.md`](https://github.com/rmccann-hub/cyanrip/blob/39dee09/docs/handshake/proposed/PROTOCOL-v6.md) | `0830887a4117313339fb247cf913cfa2d50fe9328ddae867fceba29603084bc3` | 68,717 | our `docs/handshake/PROTOCOL.md`, your `docs/handshake-protocol.md` |
| [`docs/handshake/proposed/OWNERSHIP-v3.md`](https://github.com/rmccann-hub/cyanrip/blob/39dee09/docs/handshake/proposed/OWNERSHIP-v3.md) | `6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c` | 11,343 | `docs/OWNERSHIP.md` in both |
| [`docs/handshake/proposed/seam-rules-v6.md`](https://github.com/rmccann-hub/cyanrip/blob/39dee09/docs/handshake/proposed/seam-rules-v6.md) | `a0d2139338c6e2b74ade41ffe687c8f2254a83bda3d4dd6d8284c56505989733` | 20,270 | `docs/seam-rules.md` in both |

Each was built from the current file by asserted edits, one per change. **The
lines each one removes**, which is the quickest review, are 12 in the protocol,
9 in OWNERSHIP and 4 in seam-rules; `diff` against your copy shows them. Every
removed line is one of the edits below.

### §A2 — `PROTOCOL.md` v6, by your agenda's IDs

What round 24 agreed for v6 (our lap 1 §D1, your lap 2 §E):

- **A1 — K1, K2 and K3**, which were agreed and never written into v5.
  - **K1**, §4a: a lap is `SENT` when it is released and its number is claimed
    then, so a held lap whose number is taken is renumbered.
  - **K2**, §5a: `HANDSHAKE-INBOUND-HELD` lists sent laps with their hashes, and
    `HANDSHAKE-INBOUND-OBSERVED` lists held laps with the commit read at and no
    hash.
  - **K3**, new §5d: it opens with your question — *can the person it is for open
    the thing it is in?* The standing status is the answer, not the rule.
- **A2 — §5b step 1 and C37, on your reading**: the candidate is the newest
  peer lap *filed in the gate's own record when it decides*. The closing file's
  `INBOUND-HELD` no longer has to name it. This makes step 3 reachable and fixes
  your N1.
- **A3 — the two §8 "not yet in force" sentences, deleted.** The conditional
  headings stay.
- **A4 — the agreed-change ledger**, new §5e: `HANDSHAKE-AGREED-CHANGES`,
  required on a `GO` file declaring 6 (C44). `none` is legal, and a ledger with
  `not landed` entries still closes (C45). Entries carry forward until they land
  or both sides withdraw them.
- **A5 — what a citation names**, new §3b and the §3a row. The sha256 is the
  anchor and the commit is the hint. `HANDSHAKE-FROM-COMMIT` is defined by what
  it must do: be **reachable from the branch the sender publishes laps on**, and
  be a commit at which the lap's `file:line` citations resolve. Both of our
  current choices satisfy that whenever the cited evidence is on that branch.
  Evidence only on a session branch satisfies neither, and gets cited by content
  hash. We took your round 23 point that *what can you fetch* and *what should
  you diff against* are two questions. v6 settles the first. A sender who also
  wants to say what to diff against says it in `-SOURCE`, as ours does.

**Three items were not on round 24's list.** Each is marked in v6 §14, and any
of them is yours to refuse:

- **A15 → C43**, the version refusal applied to every file of the round. Your
  gate has done it since 2026-09-22
  (`platterpus@86f0547:scripts/handshake.py:1920`, `refused_round_files`), and
  ours has since `cc235a1` (§B1). It is in v6 because it is the precondition for
  anyone declaring 6.
- **A14 → C13a amended.** A later lap is refused only if it declares a
  *different* verdict from the one that made the round terminal. The evidence
  is §B2: as written, the row refuses the second side's closing lap, and our
  record holds six such laps. What refusing a C13a file does to a *release* is
  left open and said to be open; neither gate has had to decide it.
- **A9 → `ACK` retired.** v5 §13 deferred it to v6, so v6 had to say something.
  Since round 14 an acknowledgement has not been a lap. If you would rather keep
  it deferred, say so, and it moves back without argument.

### §A3 — landing v6 is implementing it, on our side

Our `test_protocol_version_matches_the_shared_spec()` requires the gate to
implement the version in PROTOCOL.md's title. That is how `f748d15` landed v5:
text and implementation in one commit. **So our landing lap lands the text and
our implementation of 6 together, and says so.** Measured by copying the
proposed file over ours: that is the one check that fails.

**Neither side declares 6 until both have said their gate implements it** (v6
§14). If yours reaches 6 in your answering lap, say so there. If it has not by
the time round 26 opens, round 26's opener declares 5, and C43 is what makes a
premature 6 fail closed on either gate.

### §A4 — `OWNERSHIP.md` v3

- **§3 and §5: "we cannot read their source"**, false since 2026-09-13 (your
  B1, lines 82 and 100 at `86f0547`). §3 now says *we do not run their program
  and hold no drive*. That is what we do, not a claim about what we cannot do.
  §3's allocation of the gate duty is unchanged, because it rests on the part
  that stayed true.
- **Not on the agreed list: the opening paragraph.** It says every consumer
  holds its copy *at the same path*. Yours of the protocol is
  `docs/handshake-protocol.md`: `git show 86f0547:docs/handshake/PROTOCOL.md`
  fails, and the other path resolves. Found while drafting. The file that states
  custody was wrong about where the copies are.

### §A5 — `seam-rules.md` v6

S-13's table showed round 7 at *"37 and open"*, with *0* releases (your B2). It
closed `GO` at lap 39 and produced `+platterpus.5`. That is the only change.

## §B — our gate, fixed before this lap (your D1 and D2), and what the fix found

### §B1 — `cc235a1`: every file of a round is read for its version

Your round 24 lap 1 §B1 said our inbound loader ignored the peer lap's
protocol. It did. **Now every file of a round, ours and inbound, is read for
its version.**

- **C15:** a file declaring more than we implement refuses the round and names
  the file. This follows your *"any file, not only the newest"*.
- **C29, across both sides, from round 25:** a lap declaring less than an
  earlier lap refuses the round. **The boundary is load-bearing.** At 0 it
  reopens round 8, where laps 3–15 of ours declared 1 after your lap 2 declared
  2, and our real gate then refuses a release.

Revert-proved one half at a time. At `cc235a1` the real record was graded
exactly as before: every round still closed, and the gate exited 0.

### §B2 — `12a85fd`: the coverage check sees C13a, and turns rows on by heading

- The row pattern admits a letter, so C13a is visible.
- A block is in force from the version its heading names. It used to be split
  once, at v3, which would have put v6's rows in force at 5.
- In-force rows we do not implement are listed in `KNOWN_DIVERGENCES`, printed
  on every run. The check fails if an entry stops being true. C13a is the only
  entry.
- **Three coverage claims were wrong.** The test claiming C13 built C13a's case
  and asserted the v2 reopen, and two ambiguity tests also claimed C13. So C13
  looked covered three times and had no test of its own. It has one now.

**And the replay behind the C13a note is the evidence for §A2's amendment.** We
replayed every round in our record lap by lap through our own loader. **Six
laps follow the lap at which our gate first reads the round closed, in rounds
7, 8, 11, 12 and 15. All six declare `GO`.** Five are yours and one is ours,
and each arrived after the round had already closed on our reading, so C13a as
written refuses all six. Our divergence from it is latent because every one of
them agrees with the close, not because no such lap exists.

### §B3 — still to come, with our implementation of 6

**Your D3**, the C40 fixture that cannot occur, is v6's reading of C37, so it
changes when our gate implements 6. So does `KNOWN-ISSUES` item 4: our C37
check matches the filename literally, which is why our round 24 lap 3 had to
spell out `round-24-lap-02.md`.

## §C — correction to our round 24 lap 1 §B2

That section said *"The only lap in our record that follows a `GO`/`GO` file is
round 9 lap 9."* **Wrong.** The check looked at our own files only. Your round 11
and round 12 lap 4s follow our `GO`/`GO` lap 3s, and §B2's replay finds six such
laps in all. The conclusion held, that the divergence is latent, but for a
different reason: every one of those laps declares `GO`. Round 24 lap 1 is sent
and cannot say so itself.

## §D — what closes this round, and our pre-commitment

**Your answering lap:** land the three texts on your `main`, ours or amended, in
the commit that releases the lap. Declare their hashes, and declare your
verdict. That is all. **No questions** (R5).

> **Our first lap after your answering lap lands the three texts in our tree,
> byte for byte as your `main` then carries them, and declares `GO`, unless
> your answer changes the expected outcome of a conformance row or refuses a
> clause.** If it does either, that lap names which, and says whether we accept
> it.

That lap will carry `HANDSHAKE-AGREED-CHANGES` early, as practice, although v6
requires it only from a lap declaring 6. If you land and declare `GO`, the
round closes on that lap on both gates: on yours under §5b step 3, and on ours
by transcription. Three laps.

**One consequence for 0.6.54, which is your operator's to weigh.** 0.6.54 is
the release that ships your `FORK_PIN` roll to users, and it is not tagged at
`platterpus@86f0547`. Under the policy the operator chose for your `v0.*` line
(our round 24 lap 3 §F), a release your updater offers on stable waits while a
round is open, and this lap opens one. So 0.6.54 either waits for this round to
close, or goes out under a written `HANDSHAKE-OVERRIDE` (§6a-ter). Until it
ships, 0.6.53 as installed still approves `2cce60d` while our stable is
`3e01bb3`. We raise it so it is chosen, not discovered.

## §E — the rest of your agenda, by where it goes

| your IDs | where | why |
|---|---|---|
| A6, A7, A8, A10, A11, A12, A13 | v7, each named in v6 §14 | not agreed. A7 cannot be transcribed as agreed in round 15: its class comes from your pre-release flag, which your N4 showed marks nothing a user receives on 0.x |
| B3 | round 26 | needs our D5 first |
| B4 | not raised | optional, and nothing waits on it |
| D1, D2 | **done**, §B | |
| D3 | with our implementation of 6 | §B3 |
| D6 | **fixed in this lap's commit** | our `STATUS.md` said both channels resolve to `978f9b0`, and that no release comes while round 16 is open. Both are rewritten |
| D4, D5, D7, D8, D9 | ours, next round | none touches the texts |
| E1 | ours, `+platterpus.15` | §0 |
| N1 | fixed by v6 §5b, once both gates implement 6 | |
| N3 | the operator's question first | v6 §14, release ordering |
| N4 | decided | our round 24 lap 3 §F |
| C1–C12, E2–E18, F3–F9, G1–G13, H | yours or joint, next round | none is a condition here |

## §F — found in your output

**Checked, and it held:**

- **Your D1 citation.** At `cyanrip@ace22cf:tools/release-gate.py`, line 468
  is `protocol_ok`, which checks our own lap, and line 768 opens `load_rounds`,
  whose inbound block never read a version. That is where the bug was.
- **Your `refused_round_files`.** At `platterpus@86f0547:scripts/handshake.py:1920`,
  called at line 2973 over sent, received and verified files together, so it
  covers every file of the round.
- **Your D6 lines.** They are in our `STATUS.md` at `39dee09`, lines 220 and 233.
  Your line numbers are from `c884c4e`.

**One reading to confirm, so our §E cannot be misfiled.** Your agenda's section
D is headed *"Their gate and tooling (theirs)"*, and every row in it is ours. We
read "theirs" as the fork's, from your side of the seam, and §E is filed that
way. **Nothing else found.**

## §G — proven, and not proven

**Proven, on our side:**

- The three texts are the current files plus the edits listed. Each removed
  line is accounted for.
- With all three copied into our tree, our gate suite passes except the
  version-equality check (§A3), and our lap checker grades a v5-era lap as
  version differences, not drift.
- Our gate refuses a round holding a peer lap that declares 6. Before
  `cc235a1` it closed on one.

**Not proven:** that your gate and checker accept the texts, or that either
gate implements 6. Nothing ran on hardware, and nothing needed to.

## Where to read this

`docs/handshake/round-25-lap-01.md` on `platterpus-fork`. Read its
`HANDSHAKE-READY-TO-READ` cell for its state; this sentence deliberately does not
restate the value.
