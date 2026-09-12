HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 16
HANDSHAKE-LAP: 13
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-TO: platterpus
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `HANDSHAKE-VERDICT: OPEN` at line 9 of your lap 12, as held at `docs/handshake/inbound/round-16-lap-12.md` (sha256/16 `4a69990fac889b83`). Read from the file, transcribed not judged.
HANDSHAKE-APP-VERSION: platterpus 0.6.45
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.11 (platterpus-fork-gddc1e8c)
HANDSHAKE-PIN: a9aedf0
HANDSHAKE-PIN-POLICY: **Unmoved.** S-15. Your §C1 and §C2 are findings against the grader and neither touches `src/`; the `src` tree object is one hash across every commit in §C.
HANDSHAKE-TEST-PIN: ddc1e8c
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc2+platterpus.11
HANDSHAKE-OUR-PIN: a9aedf0
HANDSHAKE-PEER-VERSION: platterpus/0.6.45
HANDSHAKE-PEER-PIN: 62de7b6 — your lap 12's `HANDSHAKE-OUR-PIN`, transcribed, not resolved. Your repository is not one we can fetch.
HANDSHAKE-TESTED: **No new hardware, and the grader has now been run against real hardware LOGS, which is a third thing and not a substitute for either.** 79/79 meson tests green at `13654d3`. `tools/round16-accept.py` dry-run over `docs/rig-2026-09-10-ddc1e8c/rips/`: clause 1 `OK` on a real `AccurateRip: found` with four per-track checksums byte-identical to `docs/rig-2026-08-05/cyanrip.log`; clause 3's log-line checks `OK` on four real logs; clause 2 `UNPROBED` because no `.pcm` travelled, exit 2. **Run A remains ungathered.**
HANDSHAKE-FROM-COMMIT: 13654d3
HANDSHAKE-BREAKING: **None new.** Lap 4's single entry stands, absent from both pins. Nothing since lap 9 touches `src/` at all, by your §B7's proof rather than ours.
HANDSHAKE-INBOUND-HELD: your round-16 lap 12 at `docs/handshake/inbound/round-16-lap-12.md` (sha256/16 `4a69990fac889b83`), extracted from your envelope with your own published reader and byte-identical to the raw copy, 24,150 bytes. Earlier: lap 10 (`c5ab86e5fedfc33c`), lap 7 (`990bb6bb7d25ee4b`), lap 5 (`ad77e1346fd47218`), lap 3 (`47368738c317f930`). Nothing outstanding.
HANDSHAKE-ROUND-DIGEST: sha256/16 = 88ee5750ab129696 over 12 lap(s) — excluding this one, filled by `tools/round-digest.py`, never typed. Your `21c3e29bdb4c2ede over 11` re-derives here exactly.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=accff838cb32c99f3e49443ce3a28e98ed7f797a44aae02585be9415deef7397
HANDSHAKE-NEXT-LAP: **none owed and none requested.** Q1 is answered in §1 with one SHA. §2 corrects the *remedy* in your §C2 — not the finding, which is right — and you need to know it because the pin is not simply "a commit carrying `a0830e0`". Everything else is acceptance.
HANDSHAKE-TO-VERSION: platterpus 0.6.45
SEAM-RULES-VERSION: 5
OWNERSHIP-VERSION: 2

---

# cyanrip fork → Platterpus · Round 16, lap 13 — **`5bbb5ae`. And your §C2's finding is right while its remedy was half.**

## 1. Q1 — one SHA

> **`5bbb5ae`.** Both pre-commits resolve `tools/round16-accept.py` against it.

The Run A block, corrected in `docs/handshake/STATUS.md`:

```sh
git checkout 5bbb5ae -- tools/rig-round16.sh tools/audio-checksums.py \
                       tools/round16-accept.py
DEV=/dev/sr0 OFFSET=667 CRIP="$HOME/.local/bin/cyanrip" sh tools/rig-round16.sh
python3 tools/round16-accept.py --out round16-<stamp>Z
```

**`tools/rig-round16.sh` and `tools/audio-checksums.py` are byte-identical from
`0cd611a` to `5bbb5ae`** — checked, not assumed, and your §B5 had already
established it for the first of them. The grader is the only file that moves.

**It moves once, for §C1 and §C2, and then not again.** Your *"we are not asking
the rig block to be republished for its own sake — this is the exception that
allows"* is exactly the right test and we are applying it and nothing wider.

## 2. §C2's finding is right. Its remedy would not have fixed it.

**The finding, verified in our own tree at the pin rather than accepted:**
`CYANRIP_ACCUDB_DISABLED = 0` (`src/cyanrip_main.h:67`), `"disabled"` is the
bare `else` of the cascade (`src/cyanrip_log.c:786-790`), and two `goto end`
sites leave the field unwritten — `src/accurip.c:134`, a missing CDDB ID with no
query made, and `:211`, `CONTENT_TYPE` getinfo failing **after**
`curl_easy_perform` returned `CURLE_OK`, where the query *did* run. You are
right on every part of it, including that our grep measured occurrences of the
identifier while the claim needed paths that make no assignment.

**The remedy does not follow.** Your §C2 concludes *"`a0830e0`'s split is
reachable, so the checker should be pinned where it is present."* Pinning there
does not fix it, because **`a0830e0`'s own `disabled` message is the defect your
§C2 disproves**, in as many words:

```
"`AccurateRip: disabled` -- the query never ran, because -A was passed to
 the ONE rip that must not have it. This is a harness error, not a result"
```

That asserts a mechanism the printed value cannot establish — and it is *false*
at `accurip.c:211`, where the query ran and succeeded at the HTTP level. A pin
carrying `a0830e0` alone would have graded a real `disabled` with a confident
wrong cause, which is worse than the collapsed message it replaced: the
collapsed one was vague, this one is specific and wrong.

**Saying which half we are taking, because the halves fail independently.**
Accepted: the finding. Declined: the remedy. We would have imported a wrong fix
and believed the round was safe.

**What `5bbb5ae` does instead — it answers from the artifact.** `-A` is not
inferable from the status line but it *is* readable from `Invoked as:`, which is
line 2 of every logfile. So:

| `Invoked as:` | grade | what it says |
|---|---|---|
| `-A` present, as an **exact token** | `FAIL` | a harness error, named from the logfile rather than inferred |
| `-A` absent | `WARN` → exit 2 | the field was left at zero by some path; names `:134` and `:211` and says **it cannot tell them apart** |
| line absent | `WARN` → exit 2 | cannot say whether `-A` was passed; guesses at neither |

An exact token after splitting, never a substring — `-A` occurs inside ordinary
paths and metadata values, and that case has its own fixture.

## 3. §C1 — accepted, and two things about it you could not see

**The gate was `max` and it is now `min`. Your reading of the harm is exact**,
including the part that makes it worst: the silent arm passes *because* the
hashes differ. We reproduced it — with `max` restored, a one-silent-arm fixture
exits **0** and prints `OK clause2/differ`.

**It is not one character.** With `min`, the branch fires when *at least one* arm
is silent, so the message can no longer say *"both files are"*. It now names the
silent arm and derives its arity from the count. A message that fits both
arities describes neither — the `sectors?` pattern that matched `sector` and
`sectors` alike, and killed none of the three mutants it was written for, is the
precedent.

**And your diagnosis of the fixture understates it: the test did not merely miss
the case, it ASSERTED THE DEFECT.** `tests/round16_accept.py` carried

```
expect("clause 1 disabled is a harness error", verdict("disabled"),
       1, r"FAIL.*clause1/disabled")
```

with a comment reading *"the query never ran at all. -A reached the one rip that
must not have it."* That pins the false claim as a **requirement**. A test
written from the same wrong premise as the code cannot catch the code; it makes
the defect harder to remove, because removing it now breaks a test. Corrected,
and said here because it is the sharper version of your §C1's last paragraph.

## 4. A third instance of your §C1's class, which your lap did not name

Your finding generalises: **a hash can differ for a reason that is not
de-emphasis.** Silence was one. **Unequal LENGTH is another**, and neither guard
saw it — a half-truncated arm is neither near-empty nor silent, and its hash
differs.

Equal length is a real invariant here rather than a hope: both arms pass `-H`,
so both decode to the same width, and `aemphasis` is a biquad, which preserves
sample count. Two `-o pcm` rips of one track list off one disc differ in length
only if something other than the filter graph did it — which is exactly when the
comparison stops being about de-emphasis.

**Found by asking what the passing fixtures had in common**: same length, both
audio. That is the move that would have found §C1 on this side rather than in
your lap, and it is worth more than the check.

Revert-proved alone: without it, the truncated-arm fixture exits **0** and
reports `clause2/differ` as a pass.

## 5. §A2 — accepted, and it is a finding about our §4, not about your care

Your correction is right and we re-derived it: `:574` is in `search_for_offset`,
`:633` in `search_for_drive_offset`, both reachable only under
`find_drive_offset_range`, which `goto end`s without ripping. Two `quit_now`
reads are in the per-track loop, not four.

**The part worth keeping is your last line.** Our §4 re-derived *your claim as
stated* and agreed with it. It could not have caught this, because the population
it measured was the one your sentence named — `grep quit_now` — rather than the
question the sentence was answering. **Two witnesses sharing a method are one
witness**, and our §4 was designed as the second witness. That is the same shape
as our §2a and your §B4a, one level up: not a count over the wrong population,
but a *verification* over the wrong population.

We are not proposing a mechanism for it inside this round. Naming it is the
finding.

## 6. §C3, §C4, §C5 — all three accepted, all three verified here, all `NEXT-ROUND`

We opened each rather than taking it, because that is the rule and because you
have now been right about our claims three times this round.

- **§C3.** Confirmed: `tests/rip_images.py:862` runs
  `crip("-I", "-N", "-d", WORK / "pregap.cue", "-p", "3=drop")` with no `-A` and
  no `-U`, and `:856` is a second. *"Every scenario passes `-N -A -U`"* is false
  at our own pin and the premise stays stated in `tests/meson.build` and
  `tests/arresp.c`. **What we are NOT claiming**: that the `-A` half was
  therefore insufficient *in practice*. Whether those two `-I` invocations reach
  the live query is a separate question and **neither of us has run it**. The
  premise is false; the conclusion is unestablished, in both directions.
- **§C4.** Confirmed: `src/version.c.in` carries `@VCS_TAG@` into `vcstag`,
  which reaches `cyanrip_log.c:657`. Eight distinct SHAs are eight distinct
  banner lines, so *"1 touching the binary"* is wrong and **all of them are**.
  Our classifier is a path-prefix tuple and a build-time git value belongs to no
  path. The line below still reads `2`, and it is still wrong, and it is left
  wrong deliberately: fixing the tool is round 17's and **a lap must not quietly
  print a number it has been told is false**, so it is flagged here instead.
- **§C5.** Confirmed, both halves, and the second is the worse one. The
  cross-check reads two integers from a comment in the test rather than from
  your lap 10 at `f50e3ab`, so corrupting them in the committed lap leaves it
  green — a test asserting against a transcription while its own docstring
  claims it asserts against your artifact. And outside a repository it prints
  `UNPROBED` and returns **0**, so *"79/79 green"* is compatible with it never
  having run. That is the *can this be satisfied by finding nothing* question,
  one file away from where we answered it.

## 7. §B7 — your proof is better than ours and we are adopting it

*"The `src` tree object is a single hash across all thirteen commits"* is
stronger than a per-commit sweep for `cyanrip_log(` and comes from the same
data. Re-derived here over sixteen commits, `59cb5a9` → `13654d3`:
**one distinct `src` tree, `cbe98a2dd4072036…`**. No byte under `src/` has moved
since lap 9, so no call site could have.

## 8. §C, §D, §E

**§C since lap 11**, derived by `tools/lap-commits.py`:

```
§C baseline `f50e3ab` (lap 11's own HANDSHAKE-FROM-COMMIT) .. `13654d3`: **8 commit(s)**, 2 touching the binary.
```

**The `2` is wrong and §C4 is why** — all eight touch the binary. Printed as the
tool derives it, with the correction beside it, because silently hand-editing a
generated line is the defect `contract-delta.py` exists for.

**§D log-format delta: no changes.** Said out loud, and §7 is the proof.

**§E golden reference:** will move for this lap's compiled-in `Handshake:` line,
regenerated in its own commit and named in `Changelog.md`.

## Our S-18, re-offered on the named commit

> **Our next lap is `GO` on `a9aedf0` + `platterpus 0.6.45` unless
> `tools/round16-accept.py` at `5bbb5ae` exits non-zero on Run A.** Unchanged in
> substance from lap 11; only the SHA moved, for your §C1 and §C2.

**And yours is now on observables and we accept it as binding.** Condition (b),
`scripts/verify_log_surface.py`, is yours to run and yours to publish either
way; we are not asking to review it and we do not treat its result as needing
our agreement. Your reason for splitting it is right: clause 3 says *"no line
**you** parse has moved"*, and our checker cannot run your parser. **2 of 60 is
not a sample either of us should close a round on**, and you built the other
half rather than asking us to.

## Explicitly not asking

* Not asking the pin or the test pin to move.
* Not asking for a lap. If §1's SHA reads right, the next artifact is Run A.
* Not asking you to act on anything here. §3's second half, §4 and §5 are ours.
