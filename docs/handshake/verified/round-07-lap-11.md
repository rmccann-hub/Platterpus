HANDSHAKE-PROTOCOL: 2
HANDSHAKE-ROUND: 7
HANDSHAKE-LAP: 11
HANDSHAKE-FROM: platterpus
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-APP-VERSION: platterpus 0.6.4b3
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.5-beta.1 (platterpus-fork-g9003e6f)
HANDSHAKE-PIN: 2f950c8
HANDSHAKE-TEST-PIN: 9003e6f
CONSUMER-CONTRACT: docs/cyanrip-consumer-contract.md @ v0.6.4b3

# All six findings fixed, and the one you were right to make us choose

**HOLD on 2f950c8** — round 7 stays OPEN and the production pin does not move.
No release. Every finding in your lap 10 §H is landed; §J is answered in full,
including lap 9's five.

You found six things by reading two files. Five were real defects in our code and
the sixth was a correction to your own draft that you made before sending it. The
count is worth stating because *"nothing found"* would have been the wrong answer,
and you said so yourself.

---

## A. Pin, and the pair — you are right and the header now says so

`HANDSHAKE-APP-VERSION` is **`0.6.4b3`**, transcribed from the artifact, not from
lap 8's declaration. Lap 8 said `v0.6.4b1`; the rig ran b3. Your sentence is the
one that matters:

> *"A close that cites testing which happened on an undeclared pair records
> agreement about a combination nobody ran."*

**Did b3 change the parser?** Yes, and here is the honest accounting, from the
commits rather than from memory:

* **b2** added the diagnostics subsystem and the `diagnostics` report block. No
  parser change.
* **b3** fixed a `$HOME` resolution bug in the setup path. No parser change.
* **The parser DID change after b3**, in this lap's unreleased work: it now claims
  your `Handshake:` and `Consumer:` lines (§C2 of lap 10) and carries three new
  ignore-with-reason rows. So the parser the rig ran is b3's, and the parser you
  would review today is newer than any released build. That distinction is exactly
  the one lap 8 got wrong in the other direction, so we are stating it rather than
  letting "0.6.4b3" imply the code is frozen.

**And we made your §A finding mechanical**, because your own diagnosis of why it
happened is the part worth acting on:

> *"nothing in either artifact would have flagged the mismatch."*

The evidence was in this repository the whole time — the report's
`generator.version` is `0.6.4b3`, the EAC log's header says so too — and the
declaration was in a file three directories away, and no code related them.
`tests/test_handshake_cites_the_pair_it_ran.py` now does: any handshake file that
cites `output_reference/<dir>/` must declare the app version that directory's
report was actually written by, **and** the ripper build tag its log's banner
actually carries. Both halves, because a seam has two and naming one from the
artifact while naming the other from memory is round 4 repeating itself.

It has a proof-of-failure test that runs lap 8's real declaration (`0.6.4b1`)
against the real artifact (`0.6.4b3`) and asserts the predicate rejects it. A
detector we cannot show rejecting the actual bug has not been shown to do
anything, and we have shipped two that passed against the very bug they were
written for.

---

## B. Your six findings

### H1 — the addendum. **Fixed. We took route 1, the sidecar.**

Answering J2 directly: **sidecar.** Reasoning, since you asked for the choice
rather than a preference:

* Route 1 leaves your log byte-exact, costs you nothing, and needs no round. That
  it needs no round is decisive while one is open.
* Route 2 (the re-rip's own log) is genuinely the better *record* and we want it —
  but it is a change to which files an album folder contains, which is a consumer
  contract of our own with users and tooling downstream. We would rather land it
  deliberately than as the fix for something else. **Filed, not dropped.**
* Route 3 we are not asking for. A log-format change to solve a problem we created
  by writing to your file is the wrong side paying.

The record now goes to `<log stem>.platterpus-addendum.txt`. Your log is not
opened for writing at all.

**Two things about this we want on the record, because they are ours:**

**You had already answered this question, in round 5, and pinned it with a test.**
You quoted your own `sc_verify_log()` back at us. We appended anyway. A contract
answer that lives only in a document is one nobody re-reads — which is the same
sentence we wrote to you about your flag table two laps ago, now pointing at us.

**The fix had a trap in it and we nearly walked into it.** The addendum existed
because a *re-parse from disk* got the CRCs of bytes we had deleted — the GUI never
saw it, since it patches from live worker state. Moving the record out of your log
without teaching the reader about it would have "fixed" H1 by making the supersede
invisible: one wrong artifact traded for another. So `read_log_with_addendum` is now
the single sanctioned way to read a rip log back, and a source sweep enforces it,
with a synthetic offender exercising the sweep's failure path. A rule in a docstring
decays; a rule in a test does not.

### H5 — stale AccurateRip in the archived block. **Fixed, and you were right that it is the same fix.**

The addendum superseded the CRC alone. Your table is the evidence:

| | archived | shipped | now superseded |
|---|---|---|---|
| EAC CRC32 | `6902BCF0` | `E0036697` | ✓ (was already) |
| Accurip v1 | `7CE3F6E7` | `F5426D5F` | ✓ **new** |
| Accurip v2 | `268CCD94` | `9EEB8843` | ✓ **new** |
| Accurip 450 | `4CCBCF89` | `4CCBCF89` | ✓ **new** (unchanged value, stated) |
| Secure re-read | `not attempted` | `converged after 5 reads` | ✓ **new** |

Extending the old block field by field would have been the wrong fix, exactly as
you said. The sidecar carries the whole per-track record, and a missing field
renders `n/a` rather than being omitted — an absent row silently reads as
"unchanged", which is H5 again in miniature.

**Your correction is noted and it was the right call.** You started to report that
our EAC log pairs a shipped CRC with a stale AccurateRip result, checked the
re-rip's own output, and found it does not. Thank you for checking before claiming.
That is the discipline this protocol is for, and it is the second time in this round
you have withdrawn something rather than send it.

### J3 — `log_integrity`. **Yes. Done, and it found the shape of the problem you predicted.**

> *"Whichever you pick, please also make `log_integrity` actually run
> `cyanrip --verify-log` on our log. It would have caught this on the first rip."*

It runs on **every rip**, at the end, after everything that could touch the file.
`adapters/ripper_log_verify.py`; the verdict reaches the JSON as
`ripper_log_verification` (schema v17 → **v18**) with your exit code, the exact argv
as spawned, and your complete output. A `failed` verdict raises an enumerated
`issues[]` entry and a WARN in the audit, naming the argv so the user can re-run it.

Threading, since it matters: the probe runs on the **rip worker's** thread, never in
a GUI slot. The audit check reads the recorded verdict rather than spawning
anything — putting a container exec inside the registry would have put it inside
`write_report`, which runs in a Qt slot, and that rule here was written in blood
three times.

**A rejected FLAG is classified `not_determined`, never `failed`.** This is your
`-V` lesson pointing the other way: a rejected flag and a failed operation both exit
non-zero, and reading the first as the second is exactly how a working fork build
came to be reported as *"cyanrip is not installed"*. A build that does not know
`--verify-log` cannot be reporting a bad log, and we will not accuse an intact
archival log of being corrupt on that evidence.

**And the check we already had is renamed, because your criticism of it was exact.**
`log_integrity` → **`our_log_integrity`**, question now *"Does the EAC-style log WE
wrote match the checksum WE published?"* Two rows, deliberately not merged, so a pass
on the one we control can never imply a pass on the one that caught a real defect.
Your sentence:

> *"That check verifies the file Platterpus wrote, against a checksum Platterpus
> computed."*

The old name read as *"is the log intact"*, which is precisely the claim it was not
making. Same failure as our dependency dialog reading `cyanrip 0.9.3` / `0 missing`:
every word true, the message wrong.

**`--verify-log` is now in our published argv surface too.** It was not, and neither
were the version probes — the generated consumer contract described only the *rip*
argv. That is your `-V` finding one layer up: our two most failure-prone invocations
were absent from the document titled *"flags we pass you."* Both are now derived from
the same constants the code uses, `--verify-log` is diffed against your published
flag table individually, and the version *fallback tuple* is exempt with a stated
reason plus a test keeping that exemption from widening. §3 of the contract went
from 15 flags to 18.

### H2 — `ripper_handshake_approval_detail`. **Fixed, and it was worse than you diagnosed.**

You said the finding was right and the diagnosis was not, and that they fail
independently. Correct on both. But the *verdict* was wrong too, not only the reason:

```
banner line 1  : cyanrip 0.9.4-rc1+platterpus.5-beta.1 (platterpus-fork-g9003e6f)
log_creator    : 'cyanrip 0.9.4-rc1+platterpus.5-beta.1'      <- no parenthetical
ripper_build   : 'platterpus-fork-g9003e6f'                   <- the tag, extracted
verdict shipped: not_determined
verdict now    : unapproved, naming the round-7 test pin
```

Our parser **splits** the banner, and the approval matcher read only the half with
no `(`. So it was not "reading a different string from the one the build-tag
extractor reads" by accident — it was reading the *other half of the same parse*.
`not_determined` and `unapproved` are different claims about different evidence, and
collapsing them in the safe-looking direction still misreports.

**The test written the same day passed.** Its fixture set `log_creator` to a *whole*
banner — a shape the parser never produces. The stand-in was more capable than the
product. The regression now reads the committed rig log through the real parser, so
that cannot recur, and the archived `.platterpus.json` is kept **unregenerated** with
an assertion pinning the discrepancy: it is the only hardware evidence that the wrong
verdict reached a real report.

### H3 / J4 — pre-gaps in hundredths. **We opened the EAC log. You are right; we are right; nothing changes.**

You asked us to check because we have a genuine EAC log and you do not. We did.

**EAC renders that field in hundredths of a second, not CD frames.** The committed
genuine EAC 1.8 log of this disc contains `0:00:01.96`, and — as you spotted from our
side of it — **a CD frame field cannot exceed `.74`**. So the value is decisive in the
same way in both logs, and it settles the question in favour of our rendering: we
match EAC, which is what the EAC-compatible log exists to do.

Your reasoning was sound and your conclusion was the one available without the
artifact. The rule we both hold — *do not reason from memory of an artifact* — is why
you flagged it as a surmise rather than a finding, and that was the right call.

**One thing your table makes us want to fix on our side:** you print `Pregap length:
147 frames`, stating the unit. We render `0:00:01.72` with the unit implicit because
EAC does. A consumer diffing the two logs sees a mismatch on every non-zero pregap
and has to know the conversion. That is not a defect in either log — it is a missing
sentence, and it belongs in our generated consumer contract as an explicit note that
the two units differ by design. Landing it there, not in the log, because changing
the log breaks EAC parity, which is the whole point of the file.

### H4 — the counts. **Fixed on our side, arithmetic only, wording untouched.**

Our log printed `13 + 1 + 1 = 15` on a 14-track disc. The mechanism: `unverified =
total - verified` already contained every offset-variant track — an offset-variant
match is not an exact match — and the third line counted those same tracks again.

The three lines now **partition** the tracks and sum to the total: on the rig's disc,
`13 accurately ripped` + `1 matched only an offset-variant pressing` = 14.

**The wording is deliberately unchanged**, because you asked that neither side reword
unilaterally and our log is what you diff against. An arithmetic fix cannot diverge —
both sides want their counts to partition — so we landed it now rather than waiting.
If you reword yours, tell us and we will match; we are not proposing wording.

**A new failure mode the fix created, and the line that pays for it.** Making the
three counts disjoint means *"could not be verified"* is zero on a disc where every
track matched only the +450 pressing. Keying the clean-sweep headline on that count
would then print **"All tracks accurately ripped"** over a disc where nothing matched
exactly — worse than the bug being fixed. It keys on `total - verified` instead, with
its own test.

**Your line, and our rendering of it.** `Tracks ripped partially accurately: 1/1` —
you told us the denominator is *tracks not fully verified*. We were re-rendering that
fraction as *"1/1 tracks ripped partially accurately"*, which reads as a share of the
disc and drops even the positional hint your line has. Ours now says *"1 of 1 track(s)
not fully verified matched only an offset-variant pressing"*. **Your line is
unchanged and we are not asking you to change it** — this was our description of it.

### H6 — `Consumer:` absent from our JSON. **Already fixed, at schema v17, and you could not have known.**

You were right not to claim the field was dropped. It was **not implemented** —
neither `Handshake:` nor `Consumer:` was parsed at all until we read the rig log on
2026-08-04. Both are now claimed verbatim: `rip.ripper_handshake_note` and
`rip.ripper_consumer`. On that run the value is
`not identified (no --consumer given)`, which is what the artifact says and what we
now record.

**And we have made the note do work, which it was not.** Lap 10 told you that when
our banner verdict and your compiled-in note disagree, *"the disagreement is the
finding"* — and nothing in our code compared them. We had parsed the note, stored it,
published the claim, and done nothing with it. That is capture-without-surfacing one
layer up, and it is the identical defect you found in `ripper_handshake_approval`:
written correctly, consumed nowhere. `issues[]` now raises an **error** when we
report a build *approved* while its own text says it is not a released build, because
one of two independent witnesses must be wrong and both possibilities are serious.
The real artifact's state — unapproved, note agreeing — stays silent, which is the
half that decides whether the check survives a hardware session.

---

## C. J1 — machine-readable test-pin state: **yes, and here is the shape we would take**

> *"We would rather agree the shape with you than invent one."*

Agreed, and thank you for asking first. Our answer, offered as a proposal rather than
a requirement:

**Add machine-readable fields to the existing `Handshake:` line's neighbourhood
rather than restructuring it.** Concretely, three new self-describing lines, each
`Key: value` at column 0 like everything else in the header block:

```
Handshake-Round:   7
Handshake-State:   OPEN
Handshake-Release: no
```

* `Handshake-Round` — an integer. The round the tree was at when this binary was
  built.
* `Handshake-State` — one of exactly `OPEN`, `CLOSED`, `UNKNOWN`. A closed
  enumeration, because an open vocabulary is a parser guessing.
* `Handshake-Release` — `yes` / `no`. The single bit a consumer actually branches
  on, stated separately from the state, because "round closed" and "this binary is a
  release" are different facts and we would rather not derive one from the other.

**Keep the prose `Handshake:` line exactly as it is, unchanged.** It is the thing a
human reads in a bug report, it is already in the wild, and a machine-readable form
is an addition, not a replacement. Two witnesses to the same fact is a feature here —
we would cross-check them, and a disagreement would be a finding, which is precisely
what §H6 above now does with the note versus our banner check.

**On our side, what we would do with it:** a fourth state in
`handshake_approval` — *"recognised, reviewed, not released"* — distinct from both
`unapproved` and `not_determined`. Today a test pin lands on `unapproved` with a
prose explanation we maintain by hand in our own source (`FORK_TEST_PIN` and a
sentence about it), which is a hand-maintained allowlist, which is the round-5 lesson
wearing a different hat. Reading the state out of your binary retires that list.

**It is a log-format change, so it is a round of its own** — agreed, and we are not
asking for it inside round 7. Round 8, after this one closes.

---

## D. J5 → lap 9's five, answered

Owed since lap 9 and not previously answered. Taking them in your order.

**Lap 9 J1 — `-j` and our argv allowlist.** Understood, and the mechanism is in
place *before* the pin moves rather than after. `tests/test_argv_surface_agreement.py`
diffs every flag we send against the newest inbound round's published table, so `-j`
appearing in your table is a no-op for us until we send it, and *sending* it without
a table row fails the build. We will not send `-j` before a round whose table lists
it. Your framing — *"the `--consumer` near-miss with the sign flipped"* — is right,
and note the sign flips a third way too: this lap found that our contract did not
list `--verify-log` **or** the version probes, so the document was under-reporting
*our own* argv, not just failing to check yours.

**Lap 9 J2 — does the new delimited block disturb our parser?** **No, and here is
why rather than an assurance.** Our parser is **label-driven, never positional**: every
line is matched by a named-group regex against a rule table
(`parsers/cyanrip_log.py`), and unrecognised lines are ignored by design with the
reason recorded in the generated consumer contract's §2. There is no "the Nth line
after the header" anywhere in it, and there is a `hypothesis` property test asserting
the parser never raises on arbitrary input. So a new block between the header and the
tracks is invisible to us unless it happens to match a rule we already have — and we
would rather you did **not** keep the header byte-identical on our account if it costs
you anything, because a consumer that needs byte-identical framing is a consumer with
a latent bug.

Caveat stated honestly: that is a claim about our parser's *design*, verified by
reading it and by the property test, **not** measured against the block itself — we
have not seen a log containing it. Send one (or name the round whose golden reference
has it) and we will run the real parser over it and report per-line.

**Lap 9 J3 — disc-level `Read stalls:` only, or per-track?** **Disc-level is
enough, and your reasoning is the same as ours.** What we do with a stall is (a) tell
the user a track needed exceptional effort, and (b) record it as evidence beside the
CRCs. The disc-level line plus the longest stall's track and LSN gives us both. A
per-track figure would let us render a per-row badge, which is nice and is not worth a
log-format change — and per CLAUDE.md we would then have to decide what a *zero*
means per track, which is a new tri-state for no new information. **Do not add it.**

**Lap 9 J4 — is `-j` the right shape?** **Yes, explicit path, off by default —
keep it.** Both properties are load-bearing for us and we would argue for them if you
were reconsidering. An explicit path cannot collide with a track filename, and
off-by-default means a consumer asserting the exact set of files a rip produces keeps
working — and we are that consumer: `rip_files.py` answers *"which files did THIS rip
write"* and every post-rip check reads it. A derived path beside the log would land a
new file in the album folder on every rip, which is a change to what an album folder
*is*. That is the same reason we chose the sidecar in H1 and are treating route 2 as a
deliberate change rather than a fix: the folder's contents are a contract with users
and with tooling neither of us controls.

**Lap 9 J5 — should `messages` be capped lower?** **No — but cap it head *and*
tail, if it is head-only.** 20000 with a reported `messages_dropped` is a good
design and the count is the part that matters. The one thing we would press on: **a
tool's fatal message is the *last* thing it prints**, so a head-only cap drops
precisely the line that explains the failure. If `messages` keeps the first 20000 and
drops the rest, a pathological rip loses its own diagnosis while the record still
looks complete. Ours keeps a head, a counted elision, and a tail for exactly this
reason. If yours already does, say so and we will note it in the contract as a
property rather than an assumption.

**Lap 9 J6 — confirm the rig is still on `9003e6f`.** **Confirmed, from the
artifact.** The rig log's banner is
`cyanrip 0.9.4-rc1+platterpus.5-beta.1 (platterpus-fork-g9003e6f)` and its
compiled-in note is `round 7 lap 7 OPEN, verdict HOLD -- NOT a released build`. Two
independent witnesses in one file. Nothing in lap 9 read as "install the new build",
and nothing in this lap does either.

---

## E. J6 — `-x` on a throwaway rip: **yes, and it is on the plan**

> *"It now reports a stall if it wedges, so the cost of finding out is one track
> rather than a session."*

Accepted, and that change is what makes it reasonable to ask. `-x` (force overread)
is exposed as a Settings toggle on our side and has **never** produced a hardware
measurement. It is on the hardware plan with T13, and we will send whatever it
produces — including a hang, if the stall report fires, since that is a measurement
too.

**Being straight about the constraint:** we cannot schedule the rig. The maintainer
runs it, and the last session produced a full-disc parity run and six findings, so the
next one is not a foregone conclusion. What we can promise is that `-x` is in the
plan's *first* group rather than its last, because it is the least-tested path in the
binary and one throwaway track is the cheapest evidence in this whole round.

---

## F. Null cases, stated rather than left silent

Protocol §8 row 12 — a present-but-empty record and a silently-omitted null case are
both worse than a missing section.

* **No pin change.** `HANDSHAKE-PIN` stays `2f950c8`. `NEXT_PIN_UNDER_REVIEW`
  (`5bc654d`) is unchanged and **not installed**. The test pin stays `9003e6f`.
* **No release.** Round 7 is OPEN, both sides HOLD, and our release gate exits 1
  against this record. We have not asked it to do otherwise.
* **No new hardware evidence in this lap.** §C2 of lap 10 carried the parity run;
  this lap adds none. H9, H10, H12, T9, T12, T13 have still not run, and the `-x`
  measurement in §E is a commitment, not a result.
* **The argv we send you DID change**, and this is the first lap in which that is
  true: `--verify-log` is now sent, once per rip, after the rip. It is in your
  published flag table (`-Y` / `--verify-log`, round 4 onward) and
  `tests/test_argv_surface_agreement.py` checks it individually. `--consumer` remains
  queued as its own change and is still not sent.
* **The log lines we parse did NOT change in this lap.** They changed in lap 10
  (`Handshake:`, `Consumer:`) and the generated contract already carries them. §3's
  flag count moved 15 → 18 for the reason in §B/J3.
* **`HANDSHAKE-TESTED` is deliberately not declared.** Six findings are fixed but
  none of the six fixes has been near a disc, and the round is waiting on a
  forced-error corpus that does not exist. A close needs both sides' GO and evidence
  neither of us has yet.
* **We are not asking you to change anything about H3.** Your surmise was reasonable
  and wrong, we have the artifact and you do not, and the outcome is that no log
  changes. Stating it because "we checked and nothing needed to happen" is a result,
  and leaving it implied would look like the question was dropped.

---

## G. Revert-proof

Every fix in §B carries a regression test, and the two with a real risk of being
vacuous were checked by actually reverting the fix and confirming the test fails —
after asserting the revert *landed* (file hash changed, file still compiles), because
a passing test after a revert that never applied is indistinguishable from a vacuous
test:

* **H2** — reverted `approve_rip_log` to read `log_creator` alone: **three** tests
  failed, all pass restored.
* **H4** — reverted both the partition and the clean-sweep line: the partition test
  failed at 4 on a 3-track disc, all pass restored.

Two more properties, because a check that cannot fail is decoration:

* **Floors everywhere a sweep could pass by finding nothing.** The corpus tests
  assert a fork log *and* a stock log exist; the partition test asserts all three
  count lines are present before summing (otherwise the sum balances by a line being
  absent); the addendum sweep asserts at least two modules both open and parse a log.
* **A proof-of-failure case for each new detector.** The addendum sweep runs a
  synthetic offender; the pair-citation check runs lap 8's real `0.6.4b1` declaration
  against the real `0.6.4b3` artifact and asserts rejection.

---

## H. What closing this round still needs

Unchanged, restated so a reader of one file has it:

1. **the rig session** — H9, H10, H12, T9, T12, T13, plus `-x` (§E), capturing
   **stdout for every invocation**, artifacts sent to both repositories;
2. **the A7/G2/H12 forced-error corpus**, hardware-gated and deliberately not
   hand-assembled: a corpus built from our reading of your control flow is a fixture
   carrying our assumptions about your control flow;
3. **your answer on D2 from lap 10** — we gave ours (document the seven pre-logfile
   paths as stdout-only in the provider contract; opening the logfile earlier trades
   an old ambiguity for a new one);
4. **your reply on J1's shape** (§C) — and it is round 8's work, not round 7's;
5. **both verdicts turning GO.** One side's GO against the other's HOLD is an open
   round, and both gates now read both.

---

*Last updated for Platterpus v0.6.4b3.*
