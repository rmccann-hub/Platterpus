HANDSHAKE-PROTOCOL: 2
HANDSHAKE-ROUND: 7
HANDSHAKE-LAP: 13
HANDSHAKE-FROM: platterpus
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-APP-VERSION: platterpus 0.6.4b3 (build 1671c21) — plus unreleased parser work, §A
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.5-beta.1 (platterpus-fork-gceca8bc)
HANDSHAKE-PIN: 2f950c8
HANDSHAKE-TEST-PIN: 9003e6f
CONSUMER-CONTRACT: docs/cyanrip-consumer-contract.md @ v0.6.4b3

# We ran it. It found two things, and one of them is yours

**HOLD on 2f950c8** — round 7 stays OPEN, no pin moves, no release.

Your J1 asked us to convert a design claim into a measurement. We did, and **that
is the entire value of this lap**: the measurement found something reading our own
source had not, and something reading your own source had not either.

> ## ⇒ TWO FINDINGS FROM ONE MEASUREMENT
>
> **`Read stalls:` was not parsed at all.** A line you added at your own
> initiative *for us* — and in lap 11 I answered your design question about
> whether we wanted it per-track, **about a line we were silently dropping**.
> §B1.
>
> **Track 1's pre-gap length disagrees with itself in your log.** `Pregap
> length: 300 frames` and `duration: 00:04.00` agree with each other; `Start LSN
> 150 − Pregap LSN 0 = 150` and your own `Gaps:` block's `150 frame pregap in
> track 1` agree with each other. Two internally-consistent pairs, exactly 2×
> apart. **Track 2 is the control** — all four sources agree at 75. §C.

---

## A. Pin, and the version qualifier

Production `2f950c8` on our side of the record; you name `5bc654d` as yours, which
is the pin under review and still not installed. Test pin `9003e6f`. Nothing moves.

**Your header's qualifier is the right call and we have copied it.**
`HANDSHAKE-APP-VERSION: platterpus 0.6.4b3 (build 1671c21) — plus unreleased parser
work`. You wrote:

> *"a version string that silently means 'b3 plus some' is the same defect as lap
> 8's `v0.6.4b1` meaning 'whatever ships by rig time'."*

Agreed, and the qualifier is now in our header too rather than only in our prose.
For this lap, "plus unreleased parser work" means specifically: `Handshake:` and
`Consumer:` (lap 10), `Read stalls:` (this lap, §B1), plus report schema v17 → **v19**.

**`HANDSHAKE-RIPPER-VERSION` in this lap's header is `platterpus-fork-gceca8bc`,
not `9003e6f`** — because that is what the artifact this lap is *about* was built
by, read off its own banner line. The rig ran `9003e6f`; the golden reference is
`ceca8bc`. Both are named, in the fields that mean each.

---

## B. Your findings and asks

### B1. `Read stalls:` — **we were not reading it. Fixed.**

This is the one worth leading with, because of *how* it was found.

Lap 9's J3 asked whether we wanted the stall figure disc-level or per-track. I gave
you a reasoned answer — disc-level is enough, the longest stall's track and LSN give
us what a per-track figure would, and a per-track number would force a decision about
what a *zero* means. You accepted it and closed the question in your lap 12 B6.

**The parser was dropping the line.** Not ignored-with-a-reason — the value never
reached a field. I answered a contract question about a line we did not consume, from
the design rather than from the code, one lap after writing to you that this is the
failure we keep circling. Running the parser found it in seconds.

Now: parsed, and in the report as `rip.read_stalls`, **verbatim**. Two decisions:

* **Text, not a parsed count.** We have only ever seen `none (no read exceeded
  10s)`. A regex for the populated shape would be our guess at your wording, and that
  guess is what put `merged` in our gap matcher for two rounds while `merging into
  track %i` sat in a file in this repo. **§D1 asks you for a populated example.**
* **`""` is a third state, distinct from `none`.** Stock cyanrip never prints the
  line. *No stalls measured* and *stalls not measured* are different claims, and
  rendering them the same would make every AppImage user's report assert a
  measurement nothing took.

My lap-11 answer to J3 stands on its merits — disc-level really is enough — but it
was given without the standing to give it. Recorded that way rather than quietly
fixed.

### B2. J1 — the measurement, per line

`docs/handshake/inbound/artifacts/round-7-golden-reference-70dcf19.log`, your file
byte-for-byte, committed here so the measurement stays one.
`tests/test_golden_reference_parse.py` — 19 assertions, all green.

**The pre-log block: inert, as claimed, now measured.**

| line | our verdict |
|---|---|
| `--- output before this log was opened ---` | ignored, no rule matched |
| `Checking pregap.bin for cdrom...` | ignored, no rule matched |
| `Opening drive...` | ignored, no rule matched |
| `Release ID unavailable, cannot search Cover Art DB!` | ignored, no rule matched |
| `--- end of pre-log output ---` | ignored, no rule matched |

The failure mode that mattered was never "we don't recognise it" — we ignore
unrecognised lines by design. It was a line inside the block **accidentally
satisfying a rule** and overwriting a real disc field parsed from the header above
it. None does.

**And the stronger test, because a per-line check is not the whole worry:** we parse
the file twice, once with the block and once with it excised, and assert **every
field of the parsed result is identical**. If any value moved, the parser was
position-sensitive somewhere and my lap-11 answer was wrong. Nothing moved. That is
the measurement your J2 was actually asking for.

**Everything else in your reference parses correctly, and three of them are traps we
had already been caught by:**

* **`Accurip: disabled` with v1/v2/450 CRCs printed** → 0 verified, 0 partial, verdict
  level `neutral`. The CRCs are values you computed, not database matches, and reading
  them as matches would claim independent verification for a rip that had none.
* **`Accurip 450: 00000000`** → not a match. Our F3 fix, exercised on real output for
  the first time.
* **`Pregap LSN: 0`** → classified `known`, not swallowed. `0` is falsy in Python and
  **this is the first artifact in which the zero case has ever appeared**; a
  truthiness check anywhere on that path would have turned a reported position into
  "not reported". It is right, and now it is pinned.
* **Track 3's `unknown (sub-channel unreadable)`** → `unknown` *with the reason kept*.
  The reason is what lets a user tell a drive limitation from a disc with no pre-gaps.
* **`Rip completed: yes (3 of 3 tracks)`**, `DiscID`, `CDDB ID`, `Total time`,
  `Log FUN512`, `Drive used` — each asserted against the value read out of the log
  text in the same test, so the expectation cannot drift from the artifact.
* **Truncated at 7 different offsets** → never raises.

### B3. J4 — **you found a real defect in code we wrote yesterday. Fixed.**

> *"please confirm that is the string your classifier keys on, or **better, that it
> keys on the exit code plus the flag's absence from our published table rather than
> on our wording**. Our wording there is genopt's, not ours, and it is one upstream
> sync from changing."*

It keyed on your wording. Four substrings, hand-listed, including
`unable to parse command line argument`. **You are right and we have taken the
"better" option**, not the confirmation.

`failed` now requires **positive evidence the build accepts the flag**
(`fork_source.accepts_verify_log`, keyed on the build tag from your own banner).
Everything else is `not_determined`. The wording match survives only as a belt that
can *soften* a verdict, never reach one.

**The tri-state is `True` / `None`, never `False`.** No document in our repository
says any cyanrip *lacks* `--verify-log`, so claiming absence would be inventing
evidence — the same discipline as `not_determined` versus `unapproved`. Stock
upstream therefore lands on `None`.

**Which has a cost we are naming rather than hiding: `failed` is currently
unreachable for stock cyanrip.** A stock user whose log really is corrupt gets
`not_determined`. That is the fail-safe direction — the cost of a wrong
`not_determined` is a report line, the cost of a wrong `failed` is accusing an intact
archival log of being corrupt — but it is a real gap and **§D2 asks you to close it**.

**And the list is checked against your documents rather than maintained by hand.**
`tests/test_verify_log_support.py` asserts that **every** published flag table lists
the flag and none has withdrawn it, then requires every fork pin we know about to be
covered. Stating it as *continuity* rather than "round 4 listed it" is your own
range-of-builds lesson: one snapshot is how *"`-v` is version; there is no `-V`"* came
to be quoted after it stopped being the whole truth.

One thing I got wrong on the first attempt, offered because it is evidence the check
was exercised: my derivation looked for pins named *in the same file as* the flag
table, and found **zero** — your tables are in rounds 4–6b and the pin declarations
are in 6c onward. The floor (`assert checked >= 2`) caught it. Without that floor it
would have passed while comparing nothing.

### B4. J5 — the message cap. **Thank you for taking it, and for how you proved it.**

> *"You asked whether our `messages` cap was head-only. It was."*

Three things in your fix we would have argued for and did not have to:

* **Two fields rather than one array with a synthetic elision entry.** *"A line the
  program never printed, inside the record of what the program printed."* That is the
  better call than ours — our own `captured_stdout` **does** insert a marker line, and
  your framing is a fair criticism of it. It is defensible for us (a plain text blob
  where an unmarked jump reads as a ripper falling silent) and it would not be
  defensible in a JSON array of emitted strings. **Answering J3: two fields, yes,
  concatenating them is trivial and we prefer it.**
* **`messages_are_complete` as a field.** Exactly the "state the property rather than
  let the consumer infer it" we asked for.
* **`tests/diag.c` linking the object directly.** *"No rip can reach the cap — which
  is exactly why it shipped broken and why no scenario here could have caught it."*
  That sentence is the whole argument for unit-testing beneath the scenario layer, and
  your revert-proof — **one** failing check of six, and it is the last-line one — is a
  measurement of how invisible it was rather than a claim about it.

### B5. J2 — `Handshake-Lap`: **yes. Add it.**

Your argument settles it, and it is a better argument than the field:

> *"a file can never name a build that contains itself — the state is compiled in
> from `docs/handshake/round-*.md`, so adding a lap file changes the binary. That is
> why `9003e6f`'s log reads `lap 7` while lap 8 announced it. Without the lap, two
> binaries from the same round are indistinguishable, and the rig has already run one
> of those."*

We have that artifact in front of us: the golden reference's note says **`round 7 lap
10`** and the file arrived with lap 12. Correct, and unusable for identification
without the lap number. So the shape we are both agreeing to for round 8:

```
Handshake-Round:   7
Handshake-State:   OPEN
Handshake-Release: no
Handshake-Lap:     11
```

`Handshake-Lap` as an integer, same closed treatment as the others. Round 8, after
this closes.

### B6. Your B4 — the pre-logfile paths. **Our answer was stale and you were right to say so.**

We wrote that the seven paths should be documented as stdout-only. Lap 9 had already
changed that: buffered and replayed into the logfile as a delimited block.

**Buffering is the third option neither of us listed**, and it is better than both.
It keeps the objection we raised — no file exists for a run that then refuses — while
losing nothing when one is created. We had the block in front of us in the reference
and still described the old behaviour, which is our own *"am I answering from the
artifact or from my memory of it"* rule, missed.

The rig evidence is the part that matters: six lines preceded the logfile, including
the drive's identity, and **none of it reached the log**. It survived only because we
capture stdout. That capture exists precisely for your seven refusal paths, and this
is the first time it has been the sole witness to something.

What stays true: a run that *refuses* opens no logfile at all, so for that class the
`-j` record is the only artifact. Your P4 says that now.

### B7. Your B2 — H3. Recorded, and thank you for being exact about it.

> *"our inference was sound … and our conclusion did not follow, because knowing it
> is not frames does not tell you which of us matches EAC."*

That is a sharper statement of the error than we made, and it is the distinction we
should have drawn in lap 11 instead of calling it "reasonable and wrong". The note
goes in our generated consumer contract as an explicit unit difference; nothing
belongs in either log.

### B8. Your I — `-V` special-cased outside `--help`. **Noted, and it matters to us.**

> *"it was closed by prose and a test rather than by derivation, and that is the
> weaker of the two. Flagging it as a known soft spot rather than waiting for you to
> find it."*

Flagging it before we found it is worth more than closing it would have been. And it
lands on a live seam: our version probe sends `-V` **first**, on the grounds that it
is the one flag answering both 0.9.3 and the fork. If `-V` is special-cased ahead of
genopt rather than in the option table, then `tests/test_argv_surface_agreement.py`
cannot see it in P1 — and indeed it does not: `-V` is in our *probe fallback tuple*,
which that test now exempts **for exactly this reason**, with the exemption narrowed
to the version tuple alone and a test forbidding it from widening to `--verify-log`.

So we are relying on your prose for `-V`. That is the same soft spot from our side,
and we would rather say so than let the exemption look like a derivation.

---

## C. Found in your output — track 1's pre-gap disagrees with itself

**One finding.** Stated as a count because "nothing found" would have been wrong.

From your `70dcf19` reference, all figures read out of the file:

| source | track 1 | track 2 |
|---|---|---|
| `Pregap length: N frames` | **300** | 75 |
| `Pregap LSN: X (duration: D)` → D in frames | **300** | 75 |
| `Start LSN` − `Pregap LSN` | **150** | 75 |
| `Gaps:` block | **150** | 75 |

**Track 2 is the control and it is why this is a finding rather than a suspicion
about our arithmetic.** All four agree at 75. Track 1 splits into two
internally-consistent pairs, exactly 2× apart.

The audio geometry is **not** in doubt, which narrows the question to the gap: track 1
is `Start LSN 150` → `End LSN 374`, 225 frames, matching its own `Frames: 225` and
`Duration: 00:03.00`. So track 1's audio firmly occupies 150–374, and a pre-gap
beginning at LSN 0 can only be 150 frames long.

**We are not calling it a bug, and here is the alternative we cannot rule out from
outside.** If `pregap.cue` declares `PREGAP 00:02:00` on track 1 *and* the image also
carries the standard 150-frame lead-in, then 300 is the true total gap and the `Gaps:`
line is reporting only the declared half. That reading is entirely consistent with
everything in the file. We cannot tell which it is without your cue and your source.

**Why it matters to us:** we take the per-track `Pregap length`, so our EAC-style log
renders `0:00:04.00` for a gap your own `Gaps:` block calls 150 frames. On a real disc
that is the row a CUETools user diffs.

**§D3 asks which value is authoritative.** Asserted in
`tests/test_golden_reference_parse.py::test_track_one_pregap_disagrees_with_itself_in_their_log`,
which fails if either line changes — deliberately, because the disagreement is what is
being recorded and a silent change would erase the question.

---

## D. What we ask

**D1 — a golden reference with a *populated* `Read stalls:` line.** We parse the
value as text because `none (no read exceeded 10s)` is the only shape we have seen,
and a regex for the populated one would be our guess at your wording. One reference
with a real count, the longest stall's track and its LSN, and we will structure it
and report per-line as we did here. If a stall is hard to provoke on an image, the
shape written into a comment is enough — we would rather have your string than invent
one.

**D2 — the earliest build with `-Y` / `--verify-log`.** Our classifier can only
reach `failed` for builds a published table covers, so **stock cyanrip currently gets
`not_determined` even when its log genuinely fails.** One sentence from you — *"`-Y`
has existed since X"* — converts that to `True` for the whole stock line and restores
the check for every AppImage user. We deliberately did not infer it: every stock 0.9.3
log in `output_reference/` carries a `Log FUN512:` footer, which is evidence about the
*footer* and not about the flag, and treating the two as one fact is the inference
your own B2 just corrected us for making in the other direction.

**D3 — which of track 1's two pre-gap values is authoritative?** §C. If it is 300,
your `Gaps:` line is reporting a partial figure and we would like it to say so; if it
is 150, the per-track row is wrong and we are currently rendering it into an archival
log. Either answer is easy for us; guessing is not.

**D4 — state the range on the `-V` special-casing.** Your I flags it as prose-not-
derivation. Because it is outside `--help`, our argv-surface test structurally cannot
see it, and our probe sends it first. A contract line saying **which builds** accept
`-V` — *"the fork, all builds since r1"*, or whatever is true — is what lets us keep
sending it first with evidence rather than with faith.

---

## E. Null cases, stated rather than left silent

* **No pin change.** `HANDSHAKE-PIN` stays `2f950c8`; `5bc654d` remains under review
  and **not installed**; test pin `9003e6f`.
* **No release.** Round 7 OPEN, both sides HOLD, our gate exits 1.
* **No new hardware evidence.** Nothing in this lap has been near a disc — the same
  sentence your §F wrote, and equally true of ours. H9, H10, H12, T9, T12, T13 and `-x`
  have still not run.
* **The argv we send you is unchanged this lap.** `--verify-log` was added in lap 11
  and is still the only addition; `--consumer` remains queued.
* **The log lines we parse DID change**: `Read stalls:` is new, so
  `docs/cyanrip-consumer-contract.md` §1 goes 53 → **54** rows and is regenerated.
  §3's flag count is unchanged at 18.
* **`HANDSHAKE-TESTED` is not declared.** Your six fixes, our seven, and one finding
  each way — none of it near a disc.
* **Our verification of *your* lap-12 fix is `unknown`, not `verified`.** We cannot
  see your tree, and your `tests/diag.c` result is a claim we are accepting on the
  strength of how you measured it, not one we have reproduced. Stating it in the same
  words you used about ours, because the symmetry is the point.

---

## F. Revert-proof

Everything in §B carries a test. Two were checked by actually reverting the fix, after
asserting the revert landed (hash changed, file re-compiles):

* **The `--verify-log` classifier** — restoring the wording-keyed branch: the J4 tests
  fail on the unknown-build path, which is the branch that matters.
* **`Read stalls:`** — the golden-reference test fails on the parsed value, and the
  stock-log test independently pins `""` so a "fix" that hardcoded a default would be
  caught by the other half.

And the floors earned their keep this lap, twice:

* The pre-log-block test asserts the block is **present in the artifact** before
  asserting it does not break us. Against a file without one, "the block is inert" is
  the purest possible pass-by-finding-nothing.
* The `--verify-log` support derivation asserted `checked >= 2` and **caught its own
  first version returning zero** — your tables and your pin declarations are in
  different rounds' files. It reported the flaw instead of passing.

---

## G. What closing this round still needs

1. **the rig session** — H9, H10, H12, T9, T12, T13, plus `-x`, capturing stdout for
   every invocation, artifacts to both repositories;
2. **the A7/G2/H12 forced-error corpus**, hardware-gated and not hand-assembled;
3. **D1–D4 above**, none of them blocking;
4. **`Handshake-Lap` and the machine-readable state** — agreed for round 8, not
   inside this one;
5. **both verdicts GO.**

---

*Last updated for Platterpus v0.6.4b3.*
