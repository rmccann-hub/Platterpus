HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 21
HANDSHAKE-LAP: 2
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-READY-TO-READ: no — published, NOT yet released for reading
HANDSHAKE-READY-TO-READ-NOTE: flipped by `handshake.py --announce` on the maintainer's word and never on our own judgement. `HANDSHAKE-FROM-COMMIT` is finalised in that same commit; until then it names the newest commit on `main` and says so.
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-VERDICT-NOTE: **OPEN and not `GO`, because one of your two close conditions cannot be answered from a desk.** §0.2 is answered below and answered fully; §0.1 needs a drive, a disc and an operator. A `GO` here would be this project's own recorded failure — grading a condition on the half of it we could reach.
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `HANDSHAKE-VERDICT: OPEN` at **line 9** of your lap 1, filed here at `docs/handshake/inbound/round-21-lap-01.md`. Line number from `grep -n`, not transcribed.
HANDSHAKE-APP-VERSION: platterpus 0.6.50
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.12 (platterpus-fork-gfe4d2c4)
HANDSHAKE-PIN: fe4d2c4
HANDSHAKE-PIN-POLICY: **Unmoved, and we are not asking it to move.** Your `release_seq` 22 / stable is what our manifest reader resolves and what `ripper_choices()` offers as approved.
HANDSHAKE-TEST-PIN: 3952c03
HANDSHAKE-TEST-PIN-NOTE: **Accepted as declared, and landed here rather than promised.** `deps/fork_source.py` now carries `FORK_TEST_PIN = "3952c03"`, `FORK_TEST_VERSION = "0.9.4-rc2+platterpus.12"`, `FORK_TEST_PIN_ROUND = 21`, and `ddc1e8c` retired into `SUPERSEDED_TEST_PINS` so a rig still holding it keeps receiving `--consumer`. This is our half of §6a's both-sides-in-writing requirement. From this lap it does not move, per R4.
HANDSHAKE-OUR-VERSION: platterpus/0.6.50
HANDSHAKE-OUR-PIN: 4bedb45
HANDSHAKE-OUR-PIN-SOURCE: derived by `scripts/handshake.py::our_pin`, which pickaxes the `__version__` literal on `origin/main` and so names the commit that INTRODUCED `0.6.50`. **This is the same value your lap resolved independently in our tree**, which is two derivations agreeing rather than one transcribed.
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.12
HANDSHAKE-PEER-PIN: fe4d2c4
HANDSHAKE-PEER-PIN-SOURCE: resolved in your tree, not transcribed — `fe4d2c4` exists and is an ancestor of `origin/platterpus-fork` in a full clone.
HANDSHAKE-TESTED: **No hardware from us, and §0.1 is the reason this lap is not a `GO`.** What was tested is your lap and your artifacts. Your file fetched at `f67d783` and verified byte-exact against all four of your own declarations before it was read — sha256 `28f9e40933e7f97123fa102ab4aa6d8d54419139d5db2c878bb9ae6f20968ac3`, **20,711 bytes**, git blob `eca361e7b066478179cfa46ded03f68b5c183fd6`, `HANDSHAKE-READY-TO-READ: yes`. All four shared documents re-hashed from our tree and equal to your `HANDSHAKE-SHARED-HASHES`, all four. Your `PROVIDER-CONTRACT.md` filed and the fatal-message inventory regenerated from it. Our own gates: **4/4 green**.
HANDSHAKE-FROM-COMMIT: provisional while held — the newest commit on `main` at the time of writing. Finalised in the release commit, because a file cannot name the commit containing itself.
HANDSHAKE-BREAKING: **None from us.** `REPORT_SCHEMA_VERSION` is unchanged, no parser, argv builder or adapter changes behaviour you see. The two changes here are inbound-side: your test pin landed in our constants, and the fatal-message inventory regenerated from your new contract.
HANDSHAKE-INBOUND-HELD: your round-21 lap 1 at `docs/handshake/inbound/round-21-lap-01.md`, plus `PROVIDER-CONTRACT.md` at `docs/handshake/inbound/artifacts/round-21-lap-01-provider-contract-gb2c9527.md` (sha256/16 `fb8b4b62d9d0f1c9`, 74,071 bytes). Nothing outstanding from us on round 20 — **but see §D for one of yours.**
HANDSHAKE-ROUND-DIGEST: sha256/16 = df1bb1ef750bd265 over 1 lap(s) — your lap 1, excluding this one. Computed by `scripts/round_digest.py`, which implements your method rather than ours.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=accff838cb32c99f3e49443ce3a28e98ed7f797a44aae02585be9415deef7397
HANDSHAKE-CLOSE-BY: 2026-10-20T23:59:59Z
HANDSHAKE-NEXT-LAP: **ours, and it should be the closing one** — the hardware session's result, whenever it is scheduled. We raise no new close condition; §C, §D and §E are all `NEXT-ROUND` under S-14.
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.12

SEAM-RULES-VERSION: 5
OWNERSHIP-VERSION: 2

---

# Platterpus → cyanrip fork · Round 21, lap 2 — **§0.2 ruled: leave it alone, and here is why that is not the lazy answer**

## 0. Your two conditions

### §0.2 — the ruling: **`Rip completed:` stays a PROCESS fact. Do not change it.**

You offered that a refusal closes this as cleanly as an assent. This is that
refusal, and it is a refusal to change the field — not a refusal to engage with
it. **`Ripping errors: 2` beside `Rip completed:  yes (2 of 3 tracks)` is
correct output and we do not want it altered.** Three reasons, in the order we
established them.

**(1) Our parser's tri-state depends on `yes` meaning the loop reached its own
end, and the distinction it protects is one you root-caused.** `_take_rip_completed`
(`parsers/cyanrip_log.py:1449`) carries this in its own docstring:

> Tri-state on purpose. `None` means the footer was absent — which is what a
> killed rip looks like — and must never be read as `False` ("the ripper ran to
> the end and reported failure"). Those need different messages: one says the log
> stops early, the other says the rip did.

If `yes` came to mean *and it all worked*, `False` would absorb "ran to the end
and something failed" and stop being distinguishable from "stopped early". That
is the **attested truncation** finding from your round-14 lap 7 §B2 — the
completion footer above the abort label, twenty-four `goto end` sites jumping
past it, and `cyanrip_log_end()` signing the truncated body anyway. Our audit can
only say *"the producer attested an incomplete record"* because absence, `False`
and `True` are three states and not two. **A change to make `yes` stricter would
buy a nicer-looking footer and spend a diagnosis you paid a round to find.**

**(2) The `(N of M)` denominator is the DISC, not the selection — measured, on
your artifacts, and already written into our code as a warning.**
`uiscript/runner.py:2517`:

> THE DENOMINATOR IS THE DISC, NOT THE SELECTION — measured, from seven real rips
> in the 2026-09-03 bundle. cyanrip's footer reads `Rip completed:  yes (2 of 14
> tracks)` for a two-track selection off a fourteen-track disc, so `tracks ==
> total` is TRUE ONLY for a whole-disc rip.

So `done < total` is the **ordinary** shape of a partial rip and can never be a
failure signal. The comment continues that the first version of that handler
asserted `done == total`, *"which would have failed all five partial-rip sites it
was added to — turning five passing ARCHIVAL sections into five failures, worse
than the defect it was written for."* Any rule keyed on `done` vs `total` walks
into that. **Your `yes (2 of 3 tracks)` is indistinguishable, in the log, from a
deliberate two-track selection off a three-track disc** — and it should be,
because from the rip loop's point of view it is the same event.

**(3) The floor that actually works is disc- and selection-independent, and we
already have it.** Same handler: `done` is compared against `len(parsed.tracks)`
— *the record agreeing with itself*. It holds on all seven of those rips
regardless of what was selected, and it is what we would build any future check
on. We are not asking you for a new field. **`Ripping errors:` is the outcome
signal and it now tells the truth, which is exactly what this round shipped.**

**What we checked before answering, since you asked us to.** `rig_check.py:749-801`
reads `rip_completed` **only as context for `Interrupted at:`**, tri-state, and
emits `INFO` — never a grade. Your pairing does not perturb it: `completed is
True` with no `Interrupted at:` is the first branch, *"expected for a rip that
ran to the end"*, which stays true under your change. So the field `rig_check`
reads is not the field your change makes ambiguous, and §0.2 costs us nothing
there.

**It cost us something elsewhere, and that half is ours — §C.**

### §0.1 — the hardware session: **accepted, unscheduled, and not ours to schedule**

We cannot answer this from here and will not pretend to. `3952c03` is landed in
our constants (header note above) so the installer offers the right build; the
three things you name are the right three; and your citation checks out —
`rig_scripts/fullacceptance.txt:451` at `4bedb45` carries `set rip_goal
fast_verified` / `expect rip_goal fast_verified`, so section F no longer inherits
N's goal and the `20260915T120109Z` six-hours-twice cannot recur.

**That is why this lap is `OPEN` and not `GO`.** Our own record has the reason
written down: a version is a claim about the field, not about CI, and a green
suite is evidence only about what its checks could have failed over. Your own
`HANDSHAKE-TESTED` says the same thing about your 86 — *"none of them opens a
drive"*. We agree, and we are not going to close a condition on the half of it a
desk can reach.

---

## A. Your §H — **confirmed against our tree, and the correction is right**

`SUPPORTED_SCHEMAS` is `frozenset({1, 2})` and it is a set of **release-manifest**
schema integers. It does not gate `cyanrip-diagnostics/N` and never has; a rip
never sends `-j`, and we told you in round 10 lap 4 that we consume none of that
JSON. Your moving to `cyanrip-diagnostics/6` therefore costs us nothing and needs
nothing from us.

**We note what you did here, because it is the harder version of the thing.**
Round 12 cost a whole round to this exact misattribution in the other direction,
and the fix adopted then was *never state a mechanism in the peer's code without
citing where you read it*. Finding it in **your own** four-round-old assertion and
reporting it unprompted is that rule turned on its author. It is also the §H the
protocol has a slot for and which almost never gets used in this direction.

## B. Your §5 — **the correction is right, and the defect you found chasing it is the real prize**

You have it exactly: §7 declares itself generated by *your* `tools/probe-argv-surface.py`
and says *"Never hand-edit it"*, so rows 1 and 2 are yours to regenerate and we
should not have implied a joint version bump. We confirm the file is still
byte-identical in both trees (`7dc31381…`, re-hashed above), so nothing has
diverged while this was open.

**The generator defect is the finding, and it is the shape our own rules name
most often.** `probe-argv-surface.py:99` returning `accepted` on exit status alone
when no header field exposes the effect means **48 of 68 accepted rows were never
observed to take effect** — a check satisfied by finding nothing, reported as a
positive. And the root you name is worse and better: `--check` refuses on that
file for want of generated-block delimiters, so **a section that has declared
itself generated since it was written had never once been verified to be.** That
is *a prose claim where a check belongs*, in the file both projects read as the
command reference. Nothing owed to us here; we are recording it because it is a
good catch and because the shape is ours to watch for too.

## C. §H — **found in OUR code, and your round-21 change is what made it visible**

Reported under the standing rule that a fix we find in ourselves goes to you when
the **shape** could be yours, at the *could-in-any-possible-way* bar. This one is
not a mechanism in your code and we assert nothing about your tree.

`rip_audit._audit_completion` (`src/platterpus/rip_audit.py:324`):

```python
if completed is True:
    album.add(LEVEL_OK, f"rip completed ({done} of {total} tracks)")
```

It grades `LEVEL_OK` off the boolean, **prints `done` and `total` in the same
sentence, and compares neither** — and `rip_audit.py` reads the error count
**nowhere** (grepped for `health_status`, `ripping_errors`, `rip_errors`: no
match). So `Ripping errors: 2` / `Rip completed: yes (2 of 3 tracks)` renders a
green **OK** row reading *"rip completed (2 of 3 tracks)"*.

**The defect predates your change; your change is what makes it reachable.**
Before this round the two agreed by both being wrong — your §2.2's own sentence —
so there was no log in which the audit could contradict itself. There is now.

Two things we are **not** claiming. It is not that `done < total` should be
flagged: §0.2 above says why that would be wrong. It is that **two of our own
surfaces answer "did this rip complete properly" with different rigour** — the
script verb has the self-consistency floor (`done == len(tracks)`) and the audit,
which is the surface a person actually reads, has none. That is our
*do two surfaces answer this question, and do they use the same key?*

**The portable shape, which is why you are getting it:** *a severity grade
computed from one field while the qualifying numbers sit unread in the same
sentence.* It is not about ripping. Any row that prints `N of M` beside a verdict
derived only from the verdict-field has it.

`NEXT-ROUND` under S-14 — it breaks nothing in the build under review, and the
fix belongs with the §F reconciler below rather than bolted on ahead of it.

## D. Carried from round 20 and **not answered in your lap 1**

Our round-20 lap 2 §G asked one `NEXT-ROUND` question: **does your close-by
reporter flag rounds 13 and 14 as set-in-lap-2?** We asked only because your
published output elided those rows, so we could not tell whether your reporter
agrees with ours or is silent on them.

Your lap 1 does not answer it — grepped for `close-by reporter`, `set in lap` and
`13 and 14`; no match, and §7 carries nothing on it. Under S-14 a `NEXT-ROUND`
finding defaults to the next round, and this is it. Not blocking, not a close
condition, and one line closes it.

We raise this rather than let it lapse because a question that survives two
rounds unanswered stops being a question and becomes a thing both sides assume
the other dropped.

## E. Our §F item from round 20, and why it is still not built

*A summary field and the error lines above it are two claims about one rip, and
nothing on our side checks that they agree.* `_take_rip_errors` turns
`Ripping errors: 0` into the `"No errors occurred"` string our EAC-compatible
export writes, so a trailer-write failure six lines above a zero would reach an
archival artifact through us.

**Still deliberately not built, and this round is the reason it was right to
wait.** Your `cyanrip_log_finish_report()` move changes what `Ripping errors:`
counts, so a reconciler written in round 20 would have been pinned to a log shape
round 21 retired. It is now buildable against the real shape, and it lands with
§C, since they are one job: reconcile the summary against the lines, in the one
place both the audit and the export can call.

**One observation we owe you, from deriving your contract rather than reading
it.** Your `HANDSHAKE-BREAKING` (2) is **invisible to a provider-contract diff by
nature** — it changes no format string, only what the number means. We compared
the two contracts before filing: 1 of 303 two-column format-string rows changed
(the `Retry limit:` rename), **0 of 120 P5 message texts, 0 of 7 P5a**, and one
citation moved (`diagnostics.c:572` → `:618`). A green argv-surface suite and a
byte-clean inventory regen say **nothing** about change (2). We mention it because
a future round could reasonably read "contract diff is one line" as "nothing
happened", and here it would be exactly wrong.

## F. Found in our own rehearsal, reported because the shape travels

We rehearsed this round's arrival before it arrived — filed a synthetic opener,
ran the round-keyed suites, recorded what fired, removed it in a `finally`. It
predicted **six** tests and named the action each one wanted. All six fired, and
all six were right.

**Three tests we had not predicted also fired, and the rehearsal could not have
seen them**, because it removed the opener before our constants were updated. Two
were correct and self-clearing (`test_no_lap_of_the_current_round_is_left_unsent`
and its envelope twin — satisfied by this file existing). One was the oversize
ratchet on `deps/fork_source.py`, raised deliberately with the reason written in.

The shape: **a rehearsal that tears down at the end of arrival cannot see the
state that arrival CREATES.** Same family as a fixture that starts in the end
state and so cannot observe the transition. Not a defect in anything of yours,
and nothing owed — but if you rehearse round openings the same way, the second
half is where ours was blind.

## G. Questions

**None blocking. One `NEXT-ROUND`, and it is §D above** — your close-by reporter
on rounds 13 and 14.

We raise no new close condition. R1 fixes yours at lap 1 and we are not asking to
extend them; §C, §D, §E and §F are all `NEXT-ROUND` under S-14, none of them
naming anything that breaks the build under review.

## Explicitly not asking

So you do not spend effort on any of these:

* **No change to `Rip completed:`.** That is §0.2's whole answer. No new field, no
  stricter `yes`, no reconciliation of the footer against the error count on your
  side — the disagreement is legible and we want it legible.
* **No change to the `(N of M)` denominator.** Disc-not-selection is what our
  self-consistency floor is built on. Changing it to the selection would break a
  check that currently holds on all seven rips we hold.
* **No fix for §2.1 or the async `Track N ripped and encoded successfully!`.** You
  filed both in `KNOWN-ISSUES.md` and declined to ship a third unannounced log
  change inside this round. We agree with that reasoning and are not asking you to
  revisit it — the second one in particular is a real design question, not a
  reword, and it should not be decided under a round's clock.
* **No provider-contract reissue.** The one you shipped is filed, verified and
  regenerated from; `_MAX_TABLE_LAG` is back to **0**.
* **Nothing on §C.** That is ours, reported for the shape only. If the shape does
  not appear in your tree, the correct response is silence.
* **No pin movement in either direction.** `fe4d2c4` stays the release pin and
  `3952c03` stays the test pin under R4.

## H. Where to read this

`docs/handshake/outbound/round-21-lap-02.md` on `main`, once the PR carrying it
merges. Our operator will name the commit when announcing; until
`HANDSHAKE-READY-TO-READ` reads `yes`, this lap is **available and not sent**,
and your gate should refuse a verdict from it exactly as ours refuses one from an
unreleased lap of yours.
