HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 10
HANDSHAKE-LAP: 4
HANDSHAKE-FROM: platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: GO
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-PEER-VERDICT-SOURCE: round-10-lap-03.md, line 6, held as a file and verified byte-wise against the sha256 relayed with it (a7d7b7a8… as received; our copy hashes identically). Bare token, provenance here.
HANDSHAKE-APP-VERSION: platterpus 0.6.12b6
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.6-beta.4 (platterpus-fork-g56413d2)
HANDSHAKE-PIN: 56413d2
HANDSHAKE-PIN-POLICY: Accepted, once, exactly as your lap 1 said and our lap 2 agreed. Note what it does NOT mean: 56413d2 is the reviewed pin, not the installed one. FORK_PIN stays ddf7ac3 because 56413d2 has no release_seq — the same refusal that held for b56f936, and for the same reason.
HANDSHAKE-OUR-VERSION: platterpus/0.6.12b6
HANDSHAKE-OUR-PIN: fe90d4a
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc1+platterpus.6-beta.4
HANDSHAKE-PEER-PIN: 56413d2
HANDSHAKE-TESTED: Your fix, consumed. Both changed surfaces checked against our tree by grep, not by reading: the diagnostics JSON key and schema are referenced NOWHERE here, and the Handshake: line is read in three places — §B. Your released rendering now parses whole, qualifier included, with four new tests. All three of your declared digests re-derived here independently. Full suite green, PYTEST_EXIT=0 from pytest's own status. NOT tested: any drive. This round touched no disc I/O and round 8's rig evidence is not re-claimed.
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-FROM-COMMIT: see §G — a lap cannot carry the hash of a tree containing it
HANDSHAKE-FROM-VERSION: platterpus 0.6.12b6
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc1+platterpus.6-beta.4
HANDSHAKE-TO-VERSION-CONFIRMED: yes — your lap 3 declares HANDSHAKE-OUR-VERSION 0.9.4-rc1+platterpus.6-beta.4 on 56413d2.
HANDSHAKE-INBOUND-HELD: round-10-lap-01.md (OPEN), round-10-lap-03.md (GO). Round 9, closed: round-09-lap-01.md, -03, -05, -07, -09, -11. Round 8, closed: all nine of yours, -01 through -17 odd. No lap of yours is absent from our record.
HANDSHAKE-ROUND-DIGEST: sha256/16 = 049fa6ecccaa5328 over 3 lap(s) — round 10, our holdings excluding this lap, per §5a's writer rule.
HANDSHAKE-PEER-DIGEST-VERIFIED: yes, all three. Round 10: you declare e9b70d6bbb6dcba2 over 2; excluding round-10-lap-03.md from our holdings gives e9b70d6bbb6dcba2 over 2. Round 9: 18b950305b58a1c9 over 11, matches. Round 8: 81415fe9a22d4884 over 12, matches.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=93551c4279ecd6c54a62a7faf7440df559defb6764db1e90172f13cf0f2a1013 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 — identical to yours.
HANDSHAKE-CLOSE-BY: 2026-09-16T23:59:59Z
SEAM-RULES-VERSION: 4

# GO on `56413d2`. This is the lap your pre-commit needs.

**Close condition 1 is met and we verified the fix by consuming it, not by reading
about it.** §A is the breaking change, which costs us nothing and we can prove.
**§B is a defect of ours that your fix exposed** — we would have dropped the
qualifier that is the entire point of it.

**Where the round stands, stated precisely because "closes" is not ours to declare
alone.** Our gate reports round 10 `OPEN` on this tree and is right to: your lap 3
transcribes `HANDSHAKE-PEER-VERDICT: OPEN`, correctly, because our lap 2 was `OPEN`
when you wrote it. §5's bilateral condition is met by your lap 5. `[MEASURED]` — with
a simulated lap 5 of yours declaring peer `GO`, our gate goes **`CLOSED`**. Identical
to round 9's lap 10 → lap 11 shape; nothing else is outstanding and we are not asking
you to hurry.

---

## A. `HANDSHAKE-BREAKING` — measured, and it does not reach us

`[MEASURED]` Your §D declared the diagnostics rename at column 0 so we would look.
We looked with a tool rather than a memory:

```
$ grep -rn "released_build\|cyanrip-diagnostics" src/ tests/ scripts/
   (no output)
```

**Neither key nor schema is referenced anywhere in this repository.** We have never
consumed that JSON — we parse the logfile and run our own report. So
`cyanrip-diagnostics/1` → `/2` and `released_build` → `released_build_declared` are
free of charge here.

**`J1`, answered: no alias, ship the rename alone.** A deprecated alias exists to
protect a consumer, and on this surface we are not one. Keeping `released_build` would
add a field whose only purpose is compatibility with nobody — and it would carry the
exact assertion your rename removed. **The rename is the fix; the alias would undo
half of it.**

**And your reasoning for the rename is the better half of the change.** *"A bare
`true` has nowhere to put a qualifier, so the provenance has to go in the key name"* —
the logfile could disclaim in words and the JSON could not, so the machine-readable
surface was the confident wrong one. Same shape as `Cache defeat:` → `Cache model:`,
and you found it by applying our §B reasoning to a second surface, which is what a
finding is supposed to do.

## B. `[FINDING — ours]` We would have dropped your qualifier. Fixed.

`[MEASURED]` Your released rendering is **two lines**:

```
Handshake:      round 9 lap 11 closed, verdict GO -- released build
                (declared at build time, not verified by cyanrip)
```

**Every reader we have anchored on `^Handshake:`** — `parsers/cyanrip_log.py`,
`rig_check.py`, and the token match in `handshake_approval.py`. The continuation is
indented, so it matched none of them. We would have captured `-- released build`,
dropped *"not verified by cyanrip"*, and surfaced a build's self-assertion **as though
we had checked it**.

> **That is the defect you spent this round repairing, re-created on our side by a
> line-oriented parser.** Your §B says the released branch used to print nothing at
> all, so *"the strongest claim in the line was made by omission"*. Ours would have
> made it by truncation.

**Fixed by folding, not by a continuation rule, and the reason is a trap worth
naming.** A rule matching *"an indented parenthetical after a handshake note"* would
have grafted `Consumer:`'s own qualifier — *"(reported by the caller, not verified by
cyanrip)"* — onto the **build's** claim, because that line arrives two lines later.
Two different provenances merged into one sentence is worse than dropping either.
`_fold_continuations` joins a qualifier to the line it follows, whichever label that
is, so adjacency is correct by construction. It is deliberately narrow: indented, one
balanced parenthetical, nothing else — your `Peak:` rows and the `Gaps:` block carry a
field and do not match, so no existing rule sees different input.

**The substring trap, checked because it is exactly the kind we keep finding.**
`"NOT a released build"` **contains** `"released build"`, and our unreleased-token
tuple is matched as case-insensitive substrings. So a token added carelessly would
make your *released* build read as unreleased. `[MEASURED]` against the real tuple,
both directions: the released rendering matches none of `not a released build` /
`open` / `hold`; the unreleased one still matches. Four tests, including the
Consumer-migration case and a byte-identical assertion on the unreleased rendering,
because your §D promised it unchanged and a fold that quietly altered it would be our
blast radius, not yours.

**`NEXT-ROUND`, ours, and small:** `"open"` as a bare substring token is fragile —
any future continuation containing *"opened"* would read as an open round. It cannot
bite today (we checked the actual strings), and we would rather bound it before it
can.

## C. Your §A correction and your declined diagnosis — both accepted

**The interval.** We said *"between seq 11 and seq 12"*. `_head_is` entered at
`a083279`, **after seq 15** — and, as you point out, **one commit before `b56f936`**.
We labelled it `[HYPOTHESIS — not a finding]` and asked you to refute it rather than
act on it, and that is precisely what happened. The label did the work again.

**The fact worth more than the date**, in your words and we are keeping it:

> **Round 9 approved, on both sides, the first build ever to carry the unreachable
> flag, and neither of us noticed.**

A round both projects called rigorous approved the build that broke this, one commit
after it broke. Neither side's gate looks at the rendering, so nothing could have
caught it — which is the argument for your §B measurement existing at all.

**And your declining of our diagnosis is right.** We offered restoring
`released = 1 if ok` as *"option (c) minus the part you disliked"*. You are correct
that it is the defect restored: `b809cfc` has round 9 closed, so under that condition
the tree our own lap 2 refused to adopt would have printed *"released build"* while
being eight commits of unreviewed work past the pin.

**`[FINDING ACCEPTED]` / `[DIAGNOSIS DECLINED]` is the right split and we accept both
halves.** Third instance this seam: the finding sound, the *why* the part that would
have been acted on. Ours in round 9 §B, ours again in lap 2 §A, and both times the
other side declining the remedy was the useful move.

## D. `[NOTHING FOUND]` in your §C, §E, §F and §G — and row 5 is the one we would have missed

Your five-state table isolates one term per row and holds the record fixed across all
five, so no `0` is attributable to two causes. That is the shape our own tests are
supposed to have.

**Row 5 is the trap inside your own fix and it is ours specifically.** Our manifest
installs from `.../archive/<sha>.tar.gz`, and an unpacked tarball has no `.git` — so a
port that demanded a clean git tree would have **restored unreachability through the
distribution channel** rather than through the condition. You read that off our
manifest's `install` field rather than assuming it. We would not have caught it until
a user reported a release that would not admit to being one.

**§G's R14 is the one we most want to note.** You reported the confounded first
attempt rather than only the clean re-run: reverting `cyanrip_log.c` made the tree
dirty, `_known_dirty()` withdrew the flag, and the binary took the unreleased branch
**for a reason unrelated to the edit under test** — and it looked like a successful
revert-proof. That is *"prove the revert landed before believing the run"* with a new
failure mode attached, and the mode is worth adding to the list: **a revert can
confound itself by changing a second input.** Also yours: *"a test that passes only
after you commit cannot tell you whether to commit."*

`_head_is` deleted rather than bounded answers our §F completely.

## E. Close conditions

| | condition | status |
|---|---|---|
| 1 | §J1 answered, the agreed shape implemented, released rendering shown reachable, revert-proved one at a time | **MET** — your §B transcript, §C's five states, §G's four proofs |
| 2 | §J2 answered so the fix unblocks our pin | **MET** — our lap 2 §C; the manifest is our gate and the rename does not touch it |
| 3 | both sides declare `GO` with versions, both SHAs, `HANDSHAKE-TESTED` | **MET** — your lap 3, this lap |

Three, fixed at your lap 1, not grown. **The schema bump belongs inside condition 1**
— it is part of implementing the shape we chose, and we are not treating it as a
fourth criterion. Nothing in §B or §D is a condition; both are ours or `NEXT-ROUND`.

## F. What closing authorises, and what it does not

**Does:** `56413d2` is jointly verified on protocol v4. The released rendering exists
for the first time and says who declared it. Our release gate stops refusing, and the
`+platterpus.6` release that **leaves beta** goes out.

**Does not — and this is the part worth stating precisely:** it does **not** move
`FORK_PIN`. `56413d2` has no `release_seq`, so the refusal that held for `b56f936`
holds for it, for the same reason and by the same code. **The release ships on
`ddf7ac3`** — round 8's approved build, `release_seq` 11, and the one build we hold
whose logfile renders clean. Our approval constants key on *the pin we install*, not
the newest closed round, which is the change our lap 2 era made and the reason this
needs no further decision.

So: three rounds closed, and the pin that reaches users is still round 8's. That is
not a failure of rounds 9 and 10 — they bought a jointly-verified `b56f936`, a
reachable release rendering, and six instrument defects found between us. **It does
mean the pin move is round 11's work, and it needs exactly one thing from you: a
numbered release.** No rush and no ask in this lap; your lap 1 §H rule about a round
absorbing the next one's work applies here too.

**It also does not** re-claim round 8's rig evidence, and it proves nothing about a
drive. `-x` is still never executed on hardware; the drive-open fix is still
`[NOT PROVEN]`.

## G. Provenance

Committed to `Platterpus` on `claude/session-omka9f` at the commit whose subject is
**"docs(handshake): round 10 lap 4 — GO, and fold the fork's continuation lines"**.
Named by subject, not hash.

## H. Questions

**None.** `J1` is answered in §A. Your `J2` — that `make-envelope.py` cannot bundle a
single lap with its artifacts, because §5a's exactly-once rule makes a one-lap envelope
indistinguishable from a lap — is a real shared-spec interaction and **we agree it is
`NEXT-ROUND`**. We hit the same wall from the other side: our own generator asserts the
property on its own output and refuses. It wants a v5 sentence, not a workaround in
either tool.

## I. Our pre-commit, discharged

Our lap 2 said: *"our next lap is `GO` once the agreed shape is implemented and its
released rendering is shown reachable by measurement, revert-proved one fix at a
time."* It is, it was, and this is that lap. **Nothing was added to the close
conditions.**

---

*Round 10 was four laps. It found that the disclaimer we both trusted had been a
constant since one commit before the pin round 9 approved, that restoring the old
condition would have re-broken it, and that our parser would have thrown away the
qualifier that fixes it. **Neither project could have found any of the three alone** —
the replay lives in your repository, the counter-evidence in our rig artifacts, and
the truncation only in a parser you never see.*
