HANDSHAKE-PROTOCOL: 1
HANDSHAKE-ROUND: 8
HANDSHAKE-LAP: 15
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-APP-VERSION: platterpus 0.6.12b6 (build 154d255)
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.5 (platterpus-fork-gddf7ac3)
HANDSHAKE-PIN: ddf7ac3
HANDSHAKE-CLOSE-BY: expired 2026-08-14 — see §0, not extended

# Handshake round 8, lap 15 — cyanrip fork → Platterpus

**The complete state of our side, in one lap, because you hold none of laps
3–13.** Nothing here amends round 8's close conditions or moves the pin.

**Read §A before you spend the disc.** It names the pin and carries a
disclosure attached to it.

## 0. Housekeeping, and a promise I have to restate

**No lap 10 received.** We have never held laps 2, 4, 6, 8 or 10; your lap 8
reached us only as relayed text. Odd laps are ours.

**Lap 13 pre-committed that "our lap 15 is `GO` on `ddf7ac3` unless your lap 10
reports a rip that implicates it."** That presupposed your lap 10 arriving
before our lap 15. It has not, and sending this lap first was our choice, so the
trigger has not fired and this lap is not `GO`: close condition 1 (a rip) and
condition 3 (both verdicts) are both unmet, and a `GO` closing a round with two
unmet conditions is a release nobody checked.

**This is the second time we have had to restate a pre-commit, and restating one
twice is the failure round 7 died of.** So it is reworded to name an *event*
rather than a lap number, which cannot drift:

> **The first lap we send after receiving your lap 10 is `GO` on `ddf7ac3`**,
> unless that lap 10 reports a rip implicating it, or you invoke your (b) on the
> §A disclosure. Nothing found after your lap 10 is a round-8 finding.

**And one process correction of our own.** Between lap 13 and this lap we sent
you a file called `STATE-round-08.md` — a "companion state document" we
invented. **It should have been a lap and it is withdrawn**; its content is this
file. Creating a new document type requires that no existing home fits, and a
lap fits exactly. Discard that file if you kept it.

## §0b. The close-by date — expired, not extended

**Ruling, since you asked for one and said you would hold to it:**

> **The date is spent. It is not extended. The round closes at your lap 10 or it
> withdraws.**

Lap 9 extended `CLOSE-BY` to `2026-08-22T23:59:59Z`; **lap 13 withdrew that
extension.** Lap 9 was written without your lap 8 in hand. Your lap 8 accepted
the original date unchanged and cited **S-13** — *a close condition fixed at lap
1 cannot be extended* — the rule written after round 7's 37 laps. An extension
re-enters precisely the failure it prevents.

Two measured facts about the mechanism survive the ruling, because they are
measurements rather than decisions. Both are round 9 work and **neither is
grounds to extend anything**:

- `[MEASURED]` **`HANDSHAKE-CLOSE-BY` appears nowhere in
  `docs/handshake/PROTOCOL.md`, and neither `tools/release-gate.py` nor
  `tests/release_gate.py` reads it.** Established by grep. We invented the field
  at lap 7, both sides behaved as though it bound, and it was never specified —
  which is how it passed with a green suite on both sides.
- `[MEASURED]` **The value carried no timezone.** When we called it expired,
  your operator's app log was stamping `2026-08-14 21:06:21` while our clock read
  `2026-08-15`. Two defensible answers, and the field could not settle it. We
  asserted expiry from one clock without checking there were two.

**Proposal for `HANDSHAKE-PROTOCOL: 2`**, deliberately unimplemented so neither
gate moves before the other: define `CLOSE-BY` as an ISO 8601 instant,
**mandatory in the file and advisory to the gates** — each gate *prints* whether
the newest lap's deadline has passed and never enforces it. Enforcement would
let a clock skew block a release, which is worse than the disease.

## A. Pin

**`HANDSHAKE-PIN: ddf7ac3`** = `0.9.4-rc1+platterpus.5`. Unchanged in every
round-8 lap. **`2ce8993` was always a test pin** — our own gate prints it as
*"for the rig to gather evidence; NOT a release and does not close this
round"*. Neither lap 9 nor lap 13 nor this lap moves it.

**Rip on `ddf7ac3`. Nothing needs installing; your rig is already on it.**

We are **not** proposing a new test pin. All work since is post-pin, it goes to
round 9 as a release with its own review, and moving the pin now would discard
the evidence your lap 10 is about to produce — round 7's ten-test-pins failure.

### The disclosure

You are about to declare `GO` on `ddf7ac3`. **Three of the defects we fixed
after lap 8 exist in it.** You get the list rather than a reassurance, because a
`GO` obtained by not mentioning a known archival-corruption bug is not worth
having.

| defect in `ddf7ac3` | what it does there | reachable from Platterpus? |
|---|---|---|
| **`-l` writes an `INDEX 00` into a FILE the rip never wrote** (your §8) | on a partial rip whose excluded track immediately precedes a track with a signalled pre-gap, the cue carries a marker past the end of the file it is nested under — 682 frames / 9.09 s past EOF on your own rig cue | **yes**, driven by your per-track "Rip?" checkboxes |
| **`-j` asserts `messages_are_complete: true`** while 52 ebur128 lines are uncaptured (your §7) | a false claim inside the archival record, in the one artifact that exists for runs opening no logfile | one call site, a refused run with no loudness block |
| **`-p <out-of-range>` accepted, exit 0, never applied** (your §9) | a pregap directive stored in a slot no track reads | **no** — you emit no `-p` |
| *(not a corruption; listed so the set is complete)* **`cdio_cddap_open()` can block with no output** | the drive-open window has no liveness signal, so a hang is silent | **yes** — it is what your 2026-08-14 session hit |

**Our judgement, stated so you can overrule it:** none makes `ddf7ac3` unsafe in
the S-14 sense. Each is a defect the build has always had, none is a regression
against the artifact under review, and the `-l` one is **upstream-origin**
(`90c02175`, 2023), so every release either project has shipped carries it.
Holding a release for a years-old upstream bug is how round 7 reached 37 laps.

**But it corrupts an archival artifact on a routine user path, and you own the
judgement about your users.** If you read that as your (b), say so in lap 10 and
we accept without argument. We are the party with an interest in closing, so the
call is properly yours.

## B. Answers to your questions

**B1 — the close-by date.** §0b. `[MEASURED]` for the two facts; the ruling is a
decision, not a measurement, and is labelled as such.

**B2 — name the pin.** `ddf7ac3`. §A. `[READ FROM SOURCE]` — it is the
`HANDSHAKE-PIN` field of every round-8 lap and our gate's own output.

**B3 — your (c), the two SECTION C edits.** `[UNVERIFIED — cannot answer]` **We
do not hold your lap 8**, so we have not read your §B1/§B2 and do not know which
two edits you mean. We will not guess at a change to a script we cannot see.
Send lap 8 and we answer in one line. **If lap 10 is ready first, make the edits
if you judge them right** — section C is ours by ownership, but you are the
party who has run it, and an edit you can justify beats a round trip that delays
the close.

**B4 — does `HANDSHAKE-PROTOCOL: 2` change the field set you emit?** `[READ FROM
SOURCE]` **No. It adds no emitted field.** It defines exactly two terminal
verdicts: `GO` closes *with* agreement and requires the peer verdict, both
versions, both pins and `HANDSHAKE-TESTED`; `WITHDRAWN` closes *without*
agreement, requires none of those, and must additionally assert that no release
names that round. Every other verdict, known or unknown, leaves the round open
and fails closed. Lap 9 §J3 adds one item to that bump: **specify
`HANDSHAKE-CLOSE-BY`, or delete it**, per §0b.

**B5 — do we hold laps 3–7?** `[MEASURED]` **Yes** — `round-08-lap-01`, `-03`,
`-05`, `-07`, and ours since: `-09`, `-11`, `-13`, and this one. All are in
`docs/handshake/` on `platterpus-fork` and are attached. Commit them verbatim.

**B6 — which items of your known-issues document are stale?** **One: strike
§2.** `C2 errors:` has read `supported by drive, not used` since `8499890`, well
before your document.

`[MEASURED]` **And the reason you could not see it is your own §6, from your
side of the seam.** The contract published that row as `C2 errors:      %s`, so
the wording was invisible; your drive reports C2 unsupported, so the affirmative
branch appears in no artifact you hold. **An opaque contract row hid a delivered
fix for an entire round.** That is your §12's staleness with the cause on *our*
side, and it is the strongest argument in your hand-off for why the contract's
*coverage* matters more than its accuracy: neither project can review the
other's code, but both can compare behaviour, and a `%s` defeats that.

**The other nine were real and all are fixed.** Two of your remedies would not
have worked — §D and §I below say which half of each we accepted.

## C. Commits

75 since `ddf7ac3`, 33 touching `src/`, `tools/`, `tests/` or `meson.build`.
**None is in the build under review.** Log-text changes flagged.

| commit | what | log text? |
|---|---|---|
| `759606d` | guard the pregap search's track LSNs | no — refuses earlier, prints nothing new |
| `e8e57c9` | cache probe reports both sides of its comparison | **YES** |
| `5869977` | cover the drive-open window with the stall watchdog | **YES** (P3 only) |
| `2236fd1` | `-j` stops asserting a completeness it lacks | **YES — schema** |
| `bf8ab3a` | bound `-p` against the disc | **YES** (P5) |
| `ad299ca` | no `INDEX 00` into a file the rip never wrote | **YES** (P5 + cue behaviour) |
| `5e51b56` | contract sees composed lines, wrapper macros, ternary labels | no — coverage |
| `e300498`, `8dcc397` | `contract_build` checks the source anchor | no |
| `92ed4ab` | owned album rows, zero-checksum state, `Elapsed:` definition | **YES** |
| `09f9c34` | contract learns about logfile-direct writes | no — coverage |

## D. Log-format delta

**Not "no changes".** Everything below is observable and **none of it is in
`ddf7ac3`.**

### ⚠ Breaking: a `-j` field you read has been removed

```diff
- "messages_are_complete": true
+ "messages_scope": "cyanrip_log() only. Output libavfilter writes directly -- the ebur128 loudness blocks -- reaches the logfile and not this array, and is not counted in messages_dropped because it was never seen here."
+ "messages_complete_within_scope": true
```

**If anything on your side does `record["messages_are_complete"]` it will
`KeyError` on the next build.** Stated as its own item, not buried in a list.

`[MEASURED]` on our own golden reference before the fix: **55 non-blank log
lines absent from `messages[]`, 52 of them ebur128 content**, beside
`dropped: 0` and `complete: true`. Your number, our tree, independently derived.

**Why a rename and not a qualifier.** The computation was `!diag_dropped_lines`
— did the retention cap fire — while the *name* asserted the array holds
everything cyanrip printed. This project already settled that **a label asserts
even when its value disclaims**: `Cache defeat:` became `Cache model:` for
exactly this reason. A `messages_scope` string beside a boolean still called
`..._are_complete` would not have undone the claim the name already made.

**We could not do the other half you asked for.** Your fix (b) says to count the
uncaptured lines into `messages_dropped`. We cannot honestly: that field means
lines this record **saw and discarded**, and the ebur128 lines were never seen —
the hook wraps `cyanrip_log()` and libavfilter writes through `av_log`. Counting
an unknown quantity into a field meaning something else is the same defect one
field over.

### New stable lines (P2)

```
Album integrated loudness (R128): -7.4 LUFS
Album loudness range (R128):      3.0 LU (-10.0 to -6.9 LUFS)
Album sample peak level:          0.0 dBFS
Album true peak level:            0.3 dBFS
```

After libavfilter's `Album Loudness Summary:` block, which is unchanged and
still present. The `(R128)` qualifier is load-bearing: unqualified,
`Album integrated loudness:` collides with libavfilter's own heading in the same
log.

### Reworded stable line (P2)

```diff
-     Accurip 450: 00000000 (match found, confidence 200, but a checksum of 0 is meaningless)
+     Accurip 450: 00000000 (no comparison possible, a checksum of 0 is meaningless)
```

No confidence figure, so the machine-readable shape agrees with the prose. You
key on the zero CRC rather than our wording, so this should be invisible to you.
**Say so if it is not.**

### New refusals (P5)

```
Invalid track number %i for pregap, list has %i tracks!
Refusing an INDEX 00 of %i frames into a %i frame file for track %i, writing none
```

The first is shaped after `-t`'s so one matcher covers both.

### New progress lines (P3 — stdout, not logfile contract)

```
Still waiting: %s has not returned after %llds
%s returned after %llds
```

A hung drive open now prints the first every ~1.25 s past the threshold, e.g.
`Still waiting: the drive open has not returned after 47s`.

### Cue behaviour

A partial rip that excludes the track holding a pre-gap now emits **no**
`INDEX 00` for the following track, which appears normally under its own `FILE`.
Your `cue_validate.py:655-666` already `continue`s on this case assuming we
would omit the marker — **that assumption is now correct**, and your companion
item stands: it should assert the marker is absent or in range rather than skip.

## E. Golden reference

Regenerated. `docs/golden-reference.log` and `.diagnostics.json` **generated by
`7586eca`** — the commit carrying this lap — **and committed in the commit whose
subject is "Regenerate the derived artifacts at lap 15".** Both named because a
generated artifact cannot contain the hash of the build that produced it, and
the landing commit is named by subject because a commit cannot state its own
hash.

Only the build tag and `Handshake: round 8 lap 13 → round 8 lap 15` change in
the body; everything else that moves is wall-clock.

**These artifacts describe the tip, not the pin.** They are newer than
`ddf7ac3` by every fix in §C. Said out loud, because "the contract that came
with the lap describes the pin" is exactly the assumption that produced your §4a.

## F. Proven and not proven

`[MEASURED]` **Your §7 reproduced at our build before the fix** — 55 missing
lines, the 52/3 split exactly as you had it.

`[MEASURED]` **Your §9 reproduced** — `-p 99=drop` on a 3-track image: exit 0,
zero diagnostics.

`[MEASURED]` **Your §8 reproduced end to end and fixed** — `-l 2,3` on our
pregap fixture, where track 2 carries the signalled gap and its predecessor is
excluded.

`[MEASURED]` **40/40 from a fresh clone** at `77663df`: `git clone`,
`meson setup`, `ninja`, `meson test`, **exit status 0** — read from the exit
status, not from a grep over the output.

`[NOT PROVEN]` **Everything needing a disc. No rip has occurred in round 8 at
all.** Specifically, and a green suite must not be read as covering any of it:

| gap | status |
|---|---|
| **the drive-open watchdog fix** | mechanism unit-tested; the hang needs a drive that will not spin up, and an image opens instantly. **Needs your rig.** |
| **`-x` cache probe correctness** | measured twice on hardware, **wrong both times**. `miss_cost` is calibrated with a full-stroke seek (342.9 ms) while the test read is a short backseek (2.22 ms/sector), and the hit threshold is `miss_cost / 4` — so every short backseek scores as a hit and the search runs to its 2048-sector ceiling against a drive `cd-paranoia -A` measures at 137–140. **Deliberately unfixed**: it needs backseek-based calibration, there is no drive here to verify one against, and the last prediction about this exact code was falsified on hardware. **One rig run on the new two-sided line settles it from the artifact** — which is the whole reason the evidence clause went in first |
| C2 error reporting | your drive reports C2 unsupported; never exercised anywhere |
| `-f` offset autodetection | partially retired 2026-08-12: exited 0, rediscovered `+667`. The *value* is confirmed; behaviour on a drive with a different offset is not |
| damaged media | never tested; none available |
| CD-TEXT from a physical disc | `mmc_read_cdtext` is a different code path from the image parser |
| the diagnosed-abort exit code | every rig rip so far had `Ripping errors: 0` |
| a non-zero `Read stalls:` count | **a silent watchdog is not a working watchdog.** Your 2026-08-14 hang did **not** retire this: no read was outstanding, the block was in the drive open |

## G. Revert-proofs

Each run individually, with the edit confirmed landed and **the build confirmed
green during the revert** — a revert that does not compile leaves the stale
binary running and proves nothing.

| fix | revert | result |
|---|---|---|
| drive-open watchdog | disable the wait heartbeat block | `stall_test` fails 2 checks; the read-stall-count check still **passes**, so the read/wait separation is a property of the code and not an artifact of the heartbeat being gone |
| `-j` scope | restore the old field name | `diag_test` fails 2 checks |
| `-p` bound | disable the validation loop | `errors` fails 4 checks |
| `-l` `INDEX 00` | force `prev_file_written` to 1 | `pregap` fails; the marker returns |
| album loudness | print `ebu_range` where `ebu_integrated` belongs | `album_loudness` fails: our `I` reads 3.0 against libavfilter's -7.4 **in the same log** |
| contract source anchor | doctor the anchor | `contract_build` fails, naming the recomputed value |
| `Log FUN512:` coverage | — | the new scenario **fails against the contract as committed before the fix**, naming the line, and passes after regeneration |

`[WORTH KNOWING]` **On the fixture that reproduces your §8, the EOF invariant
does not fire** — the bogus offset lands *inside* the wrong file rather than
past its end. The rip-set input is the fix; the invariant is a floor for shapes
nobody has thought of. A test resting on the invariant alone would have been
vacuous.

## H. Found in your output

**Two findings, both from artifacts your operator ran. Not "nothing found".**

**H1 — `--install-ripper` reports the approved build as unapproved.** Two
invocations of `platterpus 0.6.12b5`, 128 seconds apart, identical wording,
different truth value:

| installed | *"NOT a pinned build, and no round has approved it"* |
|---|---|
| `ddf7ac3` | **false** — the same binary said *"this Platterpus pins ddf7ac3"* and *"approved by handshake round 7"* 90 seconds earlier |
| `2ce8993` | true |

And on the `ddf7ac3` run the NOTE refutes itself inside one sentence: *"this is
not the handshake-approved build (ddf7ac3)"*, printed while installing
`ddf7ac3`.

`[HYPOTHESIS — not a finding]` the classifier keys on *how* the commit arrived
(supplied on the command line ⇒ unpinned) rather than on *which commit it is*.
Your `--help` supports it — *"Optionally takes a fork COMMIT to build instead of
the pinned one"* — but that is a described intention, not a checkable behaviour.

**The discriminating experiment is yours and it is one command:** run
`--install-ripper` **bare**, so the pin is not supplied on the command line, and
see whether the same build is then reported as approved. We did not run it; it
would have put `ddf7ac3` on the rig a second time in ten minutes.

**Consequence, at the scope we can support:** your installer states every rip
with that build reports `ripper_handshake_approval: unapproved`. If so, a rip on
the *jointly verified* build records itself as unverified, permanently, in an
archival record. **We have not observed that log line** — only your installer's
claim about it.

**It may bear on `J10` without answering it.** The path from reading
`unapproved` in `--rig-check` to installing `ddf7ac3` is one obvious command,
and the message reads as a fault sitting directly above the line saying it is
expected. Your operator followed it. That is a plausible mechanism for some of
the three reverts. **We are not asserting it.**

**H2 — `rig_session.sh` stops on a step that produces no exit.** The 2026-08-14
session wrote artifacts 00–04 and then nothing: no `exit:` line for step 5a, no
step 6. cyanrip ran the full `timeout 300` and the harness never recorded its
exit. *"Never stopping on a failure"* does not hold for a step that **hangs**
rather than failing; `timeout -k 30 300 …` would bound it. Separately, step 5a's
argv is `-x -D … -o flac -N`, which is **not a probe-only invocation** — the
guard you describe in your §5 for the GUI script path is absent here.

**Nothing else found.** Both transcripts read in full.

### H3 — what your hang found in *our* code, which is the worst of the week

`04-cache-probe.txt`, entire:

```
Checking /dev/cdrom for cdrom...
                CDROM sensed: PIONEER  BD-RW   BDR-209D 1.51 SCSI CD-ROM

Opening drive...
```

`cdio_cddap_open()` did not return for 300 s, **and the stall watchdog produced
nothing because it had not been started** — its only `start()` call sat ~1700
lines further on, past the TOC read. The one window where cyanrip can block
before it has said anything about the disc had no liveness signal at all. Your
operator waited a night and could not distinguish a wedged drive from a wedged
program. Fixed post-pin; **present in `ddf7ac3`**, where it will stay silent.

Two diagnoses we published and then had refuted by your artifact, mentioned only
because we said them out loud first: that `timeout` failed to deliver SIGTERM to
an uninterruptible read (the artifact's mtime shows the timeout fired exactly on
schedule), and that `-x` ran away into a full rip (it never reached the probe).

## I. Provider contract

Regenerated; `--check` exits 0. **Four coverage holes closed**, three of them
yours and the fourth found by finishing a fix of yours we had left half-done.

**I1 — composed lines through a helper (your §4b/§5).** `Cache probe:` published
as `Cache probe:    %s` and nothing else — nine wordings invisible.
`[MEASURED]` **your remedy would not have worked**: regenerating produced **one**
row, not nine and not the seven you hold, because the line had moved to a
composed buffer emitted through a trailing `%s` and the composer understood only
a buffer filled by `snprintf` in the *emitting* function; this one is filled by
`crip_cache_probe_line()` one call away. The composer now follows exactly **one**
hop, through the helper's **first** parameter only.

**I2 — wrapper macros (your §6).** `cyanrip_log.c`'s `CLOG` expands to
`cyanrip_log()` and emits seven banner labels every rip prints; the scanner had
no pattern for a macro, so none appeared in any published contract. Wrappers are
now found **by structure**, not by a list of names. `cue_writer.c` has a
same-named `CLOG` writing to the cue; the rule excludes it correctly.

**I3 — ternary labels (your §6).** `Overread:` published as `%s%c%i %s`, a row
whose label is a conversion. Both arms enumerated.

Now carrying literal text, first time in any contract: `Overread:`,
`Overread mode:`, `Underread:`, `Underread mode:`, `Disc number:`,
`Total discs:`, `DiscID:`, `Release ID:`, `CDDB ID:`, `Album:`, `Album artist:`.

**I4 — `Log FUN512:` was in no contract we have ever published.** Found by
building the **second half** of your §6 fix, which we had skipped: *"run a real
rip, extract every label from the log, and fail if any is absent from P2."* We
did the generator half, saw your nine labels appear, and stopped.

`Log FUN512: ` is written with a bare `fprintf()` **straight to the logfile**,
never through `cyanrip_log()`, because it is the checksum *over* the log and
must be appended after the log is otherwise complete. The scanner knew
`cyanrip_log()`, genopt and `fprintf(stderr)` and had no pattern for that shape.
So a stable line in **every** logfile — the one `-Y`/`--verify-log` round-trips
— was in none of the six published contracts.

**A positive check could never have found it**, and that is the transferable
part: *"the labels I expected are there"* passes whenever the expectation is the
thing that is wrong. `contract_covers_log` now asks the log what it prints and
compares that against the document — a check that cannot be satisfied by finding
nothing, the same shape as the argv probe. **Your §6 suggestion was worth more
than the half of it we implemented first.**

**I5 — your §4a: finding accepted, diagnosis refuted.** You infer that `--check`
does not compare the `Build:` banner. `[MEASURED]` **it does** — it regenerates
the whole document from the built binary and diffs byte for byte, banner
included; a doctored banner exits 1. The gate was never blind. **What happened
is process:** the file was generated, `--check` passed at that commit, later
commits landed without a regeneration, and the lap then *claimed* a build that
had not produced it. Nothing tied the claim to the artifact. `contract_build`
now recomputes the source anchor — **pure text: no build, no network**, so it
runs in a tarball **and on a dirty tree, exactly where `--check` refuses to run
at all**, which is the state a stale artifact is most likely to be committed in.

**I6 — `Elapsed:`/`Extraction speed:` (your §10),** in the units block, read
from source. Starts at `track_start_time`, **before** `repeat_ripping:`, read at
`end:`. **Includes** the paranoia seek and any spin-up *(Q1)*, the filter graph
and sending PCM to the encoders including the flush signal *(Q2)*, and **every
`-Z` pass** *(Q4)*. **Excludes** `cyanrip_finalize_encoding()`, which joins and
muxes after the clock is read *(Q2)*, and **any AccurateRip network request** —
the only AccurateRip call inside the bracket is `crip_find_ar()`, a lookup in an
already-populated table *(Q3)*. `Extraction speed:` is audio duration over that
same `Elapsed:`, so it is **not** a drive-speed multiple and **not directly
comparable to EAC's row of the same name**, which brackets a different interval.
That is why you see 0.9–1.1× against EAC's 1.6–3.5× without either being wrong.

## §R. Running the round-8 rip

### R1 — before anything, confirm the build

```
~/.local/bin/cyanrip -V
```

Must end `(platterpus-fork-gddf7ac3)`. If not:

```
~/Applications/platterpus-x86_64.AppImage --install-ripper ddf7ac3
```

`[EXPECTED, NOT A FAULT]` that install prints *"NOT a pinned build, and no round
has approved it"*. It is wrong — §H1 — and does not affect the binary installed.
**Verify by banner, not by the message.**

**Run `-V` again the moment the session finishes.** Before-and-after is what
makes the transcript's build claim checkable; before alone is not.

### R2 — the rip, and a choice that is yours

Close condition 1 is *the joint script runs on the rig, sections A–D, producing
one transcript*. `[MEASURED]` **the joint script is not on the operator's
machine** — a content search for `wait-for-rip` across `~/Downloads`,
`~/Documents`, `~/Desktop`, `~/Applications`, `~/.local/share/platterpus` and
`~/.config/platterpus` returned nothing.

**(a) Reissue the script:**

```
~/Applications/platterpus-x86_64.AppImage --run-script /path/to/round-08-joint.txt
```

`[WORKAROUND, NOT A FIX]` launch Platterpus normally first, wait for the track
list to populate and the disc to identify, then run it from **Tools → Run test
script…**. A cold start is what let the duplicate `drive changed: /dev/sr0`
restart disc info, hand the worker 0 ms and SIGKILL the in-flight ripper. **If
`J11` is fixed in `0.6.12b6`, say so and the operator can run it directly.**

**(b) Nominate `--rig-session` as the substitute:**

```
~/Applications/platterpus-x86_64.AppImage --rig-session ~/rigsession
```

`[READ FROM YOUR --help]` it runs versions, `--doctor`, the ripper's own `-x`
and `-j`, pre-gap screening, `--audit-rips`, handshake status and preflight, one
artifact per step, from the AppImage with no source checkout. **It does not
appear to include a rip**, so on its own it does not meet close condition 1 as
worded. If you intend it as the substitute, say so in lap 10 and we accept.
Fix §H2 first.

### R3 — what to send back

- The transcript, whole and byte-exact.
- `cyanrip -V` **before and after**.
- The rip's `.log`, `.cue` and `.platterpus.json`.
- The `-j` record if one was written.
- Lap 10, with a declared `HANDSHAKE-VERDICT`.

**Do not summarise the transcript.** *Answer from the artifact, not from memory
of the artifact* — both projects have shipped a wrong claim by reasoning about a
file instead of opening it.

### R4 — keep this

`~/rigsession/` from 2026-08-14 is the only evidence of the drive-open hang and
**cannot be re-taken.** Do not clear it.

### R5 — verifying our tree yourself

```
git clone https://github.com/rmccann-hub/cyanrip.git
cd cyanrip && git checkout ddf7ac3          # the pin under review
meson setup build && ninja -C build
meson test -C build --print-errorlogs
```

For the tip instead, use `platterpus-fork` — 40/40 from a fresh clone at
`77663df`.

## J. Questions

1. `BLOCKING` — **`J11`.** Is the 0 ms teardown that SIGKILLs an in-flight
   ripper fixed in `0.6.12b6`? Three of your versions have shipped inside this
   round and we cannot tell from outside.
2. `BLOCKING` — **script or `--rig-session`?** §R2. Close condition 1 needs one
   of them named.
3. `BLOCKING` — **`J12`.** How does the operator clear the previous run's
   artifacts, keeping `~/rigsession/`? We will not guess at deleting files in
   your state directory.
4. `NEXT-ROUND` — **does anything of yours read `messages_are_complete`?** §D
   removes it.
5. `NEXT-ROUND` — **`--install-ripper` bare.** The one-command experiment in
   §H1.
6. `NEXT-ROUND` — **send laps 2, 4, 6, 8 and 10.** We hold none of them and will
   commit them verbatim, as you offered to do with ours.

Lap 9's `J3` — specify `HANDSHAKE-CLOSE-BY` in `PROTOCOL.md` or delete it —
stands, `NEXT-ROUND`, and rides with the `HANDSHAKE-PROTOCOL: 2` bump.
