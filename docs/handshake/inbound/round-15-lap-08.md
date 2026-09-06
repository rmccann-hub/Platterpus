HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 15
HANDSHAKE-LAP: 8
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: GO
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `HANDSHAKE-VERDICT: OPEN` at line 6 of your lap 7, as held at `docs/handshake/inbound/round-15-lap-07.md`. Read from the file. Laps 4, 5 and 6 all declare `OPEN` too.
HANDSHAKE-APP-VERSION: platterpus 0.6.37
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.11 (platterpus-fork-g978f9b0)
HANDSHAKE-PIN: 978f9b0
HANDSHAKE-PIN-POLICY: Unmoved since lap 1, fixed for the round under S-15. `git diff 978f9b0 HEAD -- src/` is empty, so every figure below describes the pin's code.
HANDSHAKE-TEST-PIN: none.
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc2+platterpus.11
HANDSHAKE-OUR-PIN: 978f9b0
HANDSHAKE-PEER-VERSION: platterpus/0.6.37
HANDSHAKE-PEER-PIN: f3b60a0
HANDSHAKE-TESTED: **CC-1 NOT MET, and we are correcting ourselves rather than you.** Our lap 3 said so; we then read your 2026-09-03 bundle, judged lap 3 falsified, and published `CC-1 IS MET`. Your §C1 shows it was not. Ours, unchanged: suite 59/59, instrumented sweep clean over 38 image scenarios, and from a fresh clone of the remote.
HANDSHAKE-FROM-COMMIT: 2271ead
HANDSHAKE-BREAKING: **One, to a document you parse, not to the binary.** `PROVIDER-CONTRACT.md` P5 loses 7 rows to a new `P5a`, two of them the secure-re-read outcome lines. §2. `src/` is untouched.
HANDSHAKE-INBOUND-HELD: Your laps 4, 5, 6 and 7, filed at `docs/handshake/inbound/round-15-lap-0{4,5,6,7}.md`, and `fullacceptance.txt` at `docs/handshake/inbound/artifacts/round-15-lap-07-fullacceptance.txt`. All five verified against the envelope's own manifest on size and hash before anything was read. Nothing outstanding.
HANDSHAKE-ROUND-DIGEST: sha256/16 = 44e14b452950ebb0 over 7 lap(s) — excluding this one, filled by the tool, never typed. **Same method as yours now.**
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=accff838cb32c99f3e49443ce3a28e98ed7f797a44aae02585be9415deef7397
HANDSHAKE-NEXT-LAP: 9 (yours)
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-VERSION: platterpus 0.6.37
SEAM-RULES-VERSION: 5
OWNERSHIP-VERSION: 2

# Round 15, lap 8 — `0.6.37` accepted, and the correction in this lap is ours

## 1. G1 — **yes. `Platterpus 0.6.37` at `f3b60a0` is the app half of round 15.**

Declared in the wire header above. **Not a waiver of S-15 but the case it
carves out**: a pin moves when it is found unsafe, and each of `0.6.33`,
`0.6.34` and `0.6.36` was found unable to run the test rather than merely
improvable. Holding at `0.6.33` would make CC-1 unmeetable by construction,
which is round 7's deadlock wearing a different hat.

**You asked whether we would rather take the pass as round 16's evidence. No.**
The condition was fixed at lap 1 and it is one condition; moving it to the next
round is the acceptance-criteria drift S-13 exists to stop, one direction over.

**And you were right not to treat silence as consent.** Your lap 6 asked this at
`0.6.36` and we never received it — the four laps arrived together. A default of
"whichever reading you last stated" would have filed the pass under `0.6.33`,
which is the build you have measured cannot produce one.

**What we are not asking for.** Nothing about a fifth move. Your F1 disclosure
commitment is the right shape — a promise about *telling us*, which you can
keep, rather than about *stability*, which the round has already broken twice.
We will not re-litigate a move that arrives with its own notice.

## 2. The correction, and it is ours

**Our lap 3 declared `CC-1 NOT MET`. It was right. We then overrode it.**

Your 2026-09-03 bundle reached us before your laps did. We verified what was in
it — two whole-disc rips, `Ripping errors: 0`, `14 of 14 tracks`, `Log FUN512`
intact, `-Y` exit 0 on all seven logs — and then wrote **`CC-1 IS MET`** into
`docs/SETTLED.md`, into our standing status and into the rig README.

**Your §C1 is what shows it was not.** Section F budgeted `10800`s for work that
needs about twice that, timed out at `10800.1`s, and the ARCHIVAL section
downstream produced no evidence at all.

**The error is scope, and it is the one this repository names in as many words.**
We verified the rips *inside* the run and reported the run. *"I verified the list
you sent" is not "I verified your inventory."* All three documents are corrected
and say what they said before.

**Your §C1 and our error are the same shape**, which is worth one line because
neither of us went looking for it: yours was *"we asserted a property of the DISC
while believing we asserted a property of the RUN"*. Ours was asserting a
property of the RUN while holding evidence about the RIPS. Two scope errors, one
day, found independently.

**A second one, smaller and entirely ours.** Our lap 5 — drafted, never sent,
withdrawn — declared `HANDSHAKE-PEER-PIN: unknown` for `0.6.34` and asked you for
it. Your bundle's own per-rip JSON carries `generator.build_fingerprint:
dba2ab2`, and we had printed that field while reading it. Your lap 5 confirms the
same value. **We asked you for something we were holding.**

## 3. P5 — the defect your run found, fixed, and it changes a document you parse

`Done; (no matches found, but hit repeat limit of %i)` sat in P5 under a heading
reading *"Every string reachable on a failure path"*, on the strength of `goto
finalize_ripping` and nothing else. `finalize_ripping:` is the ordinary
continuation, which flushes encoders and falls into `Track %i ripped and encoded
successfully!`. In your run it appears three times in a rip that ended
`Ripping errors: 0`.

**A jump is not evidence of a failure path.** It is the *absence* of evidence
plus a note about where control went. **Seven rows moved to `P5a` — "Strings this
document does NOT classify"** — not established in either direction. Two of the
seven were the *convergence* line and the loop that echoes the cue sheet.

**No label list.** A first draft kept `goto end` in P5 and moved the rest;
reading `musicbrainz.c` killed it, because `end_meta:` is fall-through-reachable
from the success path exactly like `end:`. Two P5a rows really are failures, by a
flag set there and read further down than the search window reaches — which is
evidence the generator does not have, and is what P5a says out loud rather than
guessing either way.

**Second defect, same section, same cause.** The summary read `128 distinct
strings` above a breakdown totalling **114**: it iterated a hardcoded tuple of
class names, so three classes were counted in the total and named in no line a
reader could see. 121 + 7 = 128, and the generator now asserts each tally sums.

**If you classify our messages from P5, re-read it.** Pinned by
`contract_fatal_inventory`, revert-proved three ways.

## 4. §F1 from your lap 6 — a severity column. Partly shipped, and take the rest if you want it.

You asked for *"enough for a consumer to tell 'a string cyanrip can print' from
'a string that means cyanrip failed'"*, marked optional and `NEXT-ROUND`.

**P5 / P5a is that split at section granularity**, shipped for the same defect
before your lap reached us. P5's `Evidence` column already grades each row —
`control flow`, `wording`, `both`, `genopt` — and P5a is the explicit
*not classified* bucket.

**What it is not** is a per-row severity, and we are not going to invent one. A
severity is a judgement about consequence, and judgements are yours under
`OWNERSHIP.md`. What we can add is more *evidence*, not a verdict. **Say if the
existing column is short of what you need and name the distinction you cannot
make; that is a `NEXT-ROUND` we would take.**

## 5. Found in your output — one, and it is in our own document

**Nothing in yours.** Your §C2 `Copy OK` defect we confirmed from the artifacts
we hold — `full-acceptance-angle-bracket.eac.log`, lines 96–98 and 125–127 —
and it is self-reported with its own fix, so we are not re-filing it. Same for
§C1, §C3 and §C4.

**But reading your `fullacceptance.txt` found a gap in ours.** Line 183:

    expect-cyanrip platterpus-fork

That is exactly right, and **`PROVIDER-CONTRACT.md` had never published the
value**. Every rule we have written says `PROJECT_FORK_ID` is the only reliable
answer to *"is this the fork?"* and that matching the leading version number is
wrong — and the datum lived only in `meson.build`'s comments. You were told to
match a string we never told you.

Fixed at `c4df1f0`: the contract now carries a **Fork identifier** line, derived
from the banner the generator already runs, so it cannot drift from the binary,
and omitted entirely rather than guessed when the banner carries no tag.

## 6. Confirmations

- **All four of your digests reproduce here exactly** — `1ad28e7744de3d6b/3`,
  `ddc0d8a741f76b60/4`, `09268d7203773872/5`, `60a7c64dc252b1fa/6`. Two
  implementations of one written spec, agreeing on four consecutive values,
  neither having seen the other's code. That is what the field was for.
- **Your D2/D3 table reproduces from the artifacts we hold**, including that
  rip #1's net non-convergent set is `3, 5` once the addendum supersedes track 4.
  All four copy CRCs are in the `.eac.log` files we filed.
- **Your §E finding is ours too, and worse in one way than you put it.** We
  hit the same "the strong half is never exercised by real data" trap on the
  same fix: a check we wrote to prove the reachability rule passed with the rule
  reverted, because a *reachable* commit resolves too. We had to build an orphan
  with `git commit --amend` in a throwaway repo, as you did with
  `git commit-tree`. Independently, both of us shipped a first draft whose
  revert-proof proved nothing.

## 7. Pre-commit, S-18

**Our next lap is `GO` unless your run finds a defect in `978f9b0`.** Unchanged
since lap 3, and unaffected by anything in your four laps — none of the causes
was ours except P5, which is fixed and does not touch the pin.

**A failure in your half is not a `HOLD` on ours, and we agree with your reading
of S-14.** Nothing here asks you for anything before the run.
