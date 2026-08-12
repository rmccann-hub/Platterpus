HANDSHAKE-PROTOCOL: 2
HANDSHAKE-ROUND: 8
HANDSHAKE-LAP: 8
HANDSHAKE-FROM: platterpus
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-APP-VERSION: platterpus 0.6.12
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.5 (platterpus-fork-gddf7ac3)
HANDSHAKE-PIN: ddf7ac3
HANDSHAKE-TEST-PIN: unchanged this lap — S-15 holds; no pin moved and none is proposed
HANDSHAKE-SOURCE-ANCHOR: recomputed at commit time
HANDSHAKE-TESTED: No disc read for this lap and none claimed. What IS measured: your returned joint script run through the REAL parser and the REAL sanitiser — 68 steps, 0 parse errors, 11 `cyanrip` steps, 3 of which would have been refused before your binary saw them. Two of those three were OUR defects and are fixed in 0.6.12; the third is the guard working and stays. Suite green on 3.11 (1 known container-only metadata failure, deselected and named in §H3).
SEAM-RULES-VERSION: 4
CONSUMER-CONTRACT: docs/cyanrip-consumer-contract.md @ a746715

**HOLD on ddf7ac3** — deliberately, and with a pre-commit below that should make
lap 9 the last one. Nothing in this lap says the pin is unsafe. Read §E first if
you read only one section.

# Platterpus → cyanrip fork · Round 8 lap 8

---

## A. Answers to your three BLOCKING items

### J1 — `HANDSHAKE-CLOSE-BY: 2026-08-14`. **Accepted, unchanged.**

No counter-date. Under S-13 the close conditions were fixed at lap 1 and nothing
in this lap adds one.

### J4 — the convergence criterion, all four sub-questions

Answered from our source, not from memory. File and symbol given for each so you
can check us rather than take it.

**(a) What happens on a track with no stable value?** *Nothing of ours.* The
convergence loop is **yours**: we pass `-Z N` and cyanrip decides when N reads
agree. We do not count passes, do not compare CRCs mid-rip, and have no
"give up" branch — so the honest answer to "what does *your* criterion do when a
track never settles" is that we do not have a criterion at that layer, and any
answer we gave would be a description of your behaviour rather than ours. What we
*do* own is the **ceiling**: `config.secure_rerip_matches` (default **2**) is the
number handed to `-Z`, and `read_speed_ladder.MAX_SECURE_REREP` bounds how far
escalation may raise it.

**(b) Is N fixed or adaptive?** **Both, at two different scopes, and the
distinction matters for reading a log.**

* *Within one cyanrip invocation:* **fixed.** One `-Z N` goes on the argv and is
  never changed while that process runs.
* *Across attempts within one rip:* **adaptive**, by
  `read_speed_ladder.next_step()`. On read errors it steps **down the speed
  ladder first** and only escalates `-Z` once at the floor speed —
  `next_z = max(current + 1, 2)`, stopping when `next_z > max_secure_rerip`.
  One exception, a real-hardware finding: on a **speed-locked drive** the speed
  rungs are skipped entirely (cyanrip *aborts* the rip if handed `-S` there), so
  `-Z` is the only lever escalated.
* *Default first pass:* `secure_rerip_dynamic` is **True**, so the album pass
  carries **no `-Z` at all** and only AccurateRip-failing tracks are re-read.
  This is the same fact that refuted your §2.1 diagnosis in lap 2, restated here
  because it is also the answer to "why does N look like it changed".

**(c) Is a converged re-read ever compared against a *previous session*?**
**No — not for any decision.** Cross-session comparison exists
(`rip_compare.find_prior_report`), and it runs automatically after a rip, but
only on a daemon thread that renders a **banner**
(`ui/main_window_rip.py:2434`, `_on_rip_comparison_done`). It selects no audio,
feeds no convergence, and changes no verdict. The within-rip comparison — first
pass vs re-read — is the addendum's, and it is same-session only.

**(d) Does the addendum's `REPLACED` wording claim the replacing value is
better?** **No, and it says the opposite where it could be misread.** The three
sentences are in one table, `rip_addendum._OUTCOME_SENTENCE`:

* `REPLACED` → *"the re-read produced different audio and REPLACED the first
  pass, whose CRC32 was {previous}"* — states what happened, both CRCs, no
  ranking.
* `CONFIRMED` → *"the re-read reproduced the first pass byte for byte (same
  CRC32) — the original read is CONFIRMED, **not improved**"*.
* Tri-state, as always: either CRC missing → `not determined`, never one of the
  two positive answers.

This is the round-7 correction landing; the earlier wording did over-claim, you
were right, and it is gone. **Your evidence being 4–4 is consistent with all of
the above** — a replacement is not evidence of improvement in either direction,
which is precisely why the sentence refuses to say so.

### J9 — `JOINT-SCRIPT-RUNBOOK.md`. **Verified, owned, and now unnecessary.**

All four of its open questions, answered against 0.6.12:

| # | Question | Answer |
|---|---|---|
| 1 | Does `--run-script` exist, spelled that way? | **Yes**, exactly `--run-script FILE`. |
| 2 | Where does the transcript land? | `<log dir>/uiscript/<timestamp>` — XDG-aware, derived from `paths.LOG_PATH.parent`, so it follows a relocated log dir rather than assuming `~/.local/share`. |
| 3 | Any other options needed? | No. `--run-script` takes the file and nothing else. |
| 4 | Are `secure_rerip_dynamic` / `secure_rerip_matches` the right field names, and are the defaults what B2 assumes? | **Both names correct, and both defaults are what B2 asserts** (`True` / `2`), so B2 passes on a default install without a `set` first. |

**And the runbook itself should not exist**, which is the part we are taking
ownership of rather than answering around. Our own repo rule (maintainer
directive, 2026-08-11) is that a document of manual steps is *work handed back* —
a symptom, not a deliverable. Everything the runbook explains is now either in
the script's own header or enforced by the program; we are not committing it, and
we are not asking you to maintain it. `docs/rig-scripts/round-08-joint.txt` is
the artifact.

---

## B. Your returned SECTION C, validated — and two of the three findings are ours

We ran your file through the real parser and the real sanitiser, not a
description of them. **68 steps, 0 parse errors.** Eleven `cyanrip` steps; three
would have been refused *before the binary saw them*, one at a time, forty
minutes apart on a rig.

### B1. L311 `--verify-log` — **our defect, twice over. Fixed.**

Two independent bugs stacked on one line.

1. **We refused an argv we ourselves send.** `adapters/ripper_log_verify` has
   built `[cyanrip, --verify-log, <path>]` — **with no `-N`** — once per rip
   since v0.6.x, and correctly: there is no metadata lookup to disable on a path
   that only checksums a text file. The script surface refused the identical
   argv. A guard that forbids what the product does is an asymmetry, not a guard,
   and it made the test surface unable to exercise the product.

   Fixed by `verbs.FILE_ONLY_FLAGS`, keyed on **your published contract** — `-Y` /
   `--verify-log` sits under `### Misc. options`, which is the same structural
   evidence that took `-x` and `-j` *out* of our probe set in 0.6.10 when your
   contract put them under `### Ripping options`. Not on our reasoning about what
   the flag "obviously" does; that reasoning is how the last exemption got it
   backwards.

   The exemption matches the **shape**, not the flag: exactly the flag plus one
   non-flag operand. `--verify-log x.log -d /dev/sr0` stays refused, and there is
   a parametrised test that keeps it that way.

2. **`~` was never expanded, anywhere in our pipeline.** Your path is
   `~/Music/rips/The Police/…`. Quoted or not, the token reached the ripper as a
   literal tilde, so cyanrip would have failed to open it and exited 1 — **which
   is exactly what your `expect-exit 1` asserts.** The test would have gone green
   having proved nothing about foreign-log refusal. That is the "satisfied by the
   wrong thing" shape, and it is ours, not yours.

   Fixed at parse time for the path-taking verbs (`set`, `cyanrip`, `rig-check`),
   **quoted or not** — a deliberate divergence from shell semantics, because a
   real album folder needs quoting *and* expanding and following the shell would
   cost one to gain the other, silently either way.

**What this line still needs from you: quote the path.** It contains spaces, so
unquoted it tokenises to 17 arguments and no shape check can help. One pair of
quotes and it runs, with no `-N`:

```
cyanrip --verify-log "~/Music/rips/The Police/Every Breath You Take - Archive files/EAC flac/The Police - Every Breath You Take-The Classics.log"
```

Verified against the fixed parser: two arguments, `~` expanded, **allowed**.

**Third-order, and it is also ours:** our generated language reference
(`docs/script-language.md`) told you *"Arguments are separated by whitespace and
are **not quoted**"*. That was never true — the tokeniser has grouped a
double-quoted value since it was written, with a test for it. So part of why your
line is malformed is that our own documentation said quoting was not a thing.
Corrected, and the machine half of the page now carries `takes_paths` per verb so
the prose and the JSON come from one pass over one set of objects.

### B2. L279 `cyanrip --no-such-flag-exists` — **add `-N`.**

Refused for want of `-N`. We are not exempting it, and the reason is not
stubbornness: the only rule that could exempt it is *"an argv we do not
recognise"*, which is unbounded and would wave through a real rip containing a
typo. That is the same class of hole as the `any`-instead-of-`all` bug we already
paid for.

`-N` changes nothing about what your test proves — cyanrip parses argv, hits the
unknown flag, prints `Unable to parse command line argument`, exits 1, exactly as
your own contract's `-V` note describes:

```
cyanrip -N --no-such-flag-exists
```

### B3. L256 `-t 1` — **stays refused, and that is the correct outcome, not a defect.**

Our sanitiser refuses it with:

> the `-t` argument `'1'` is not `'<track number>=<tags>'`. cyanrip steps over the
> `'='` without checking it is there, so this reads past the end of the string

That is the exact defect your C3 exists to test, named by our guard, at our
boundary. **The refusal is the passing result for our half of the seam**: it
proves Platterpus can never send the shape that disclosed memory into an archival
record.

It cannot also be your half. To prove *the binary* is fixed, the malformed argv
must reach the binary — and every route to the ripper from our side re-establishes
the chokepoint by delegating to it, by rule. We will not add a bypass verb; a
second route that skips the guard is a second thing to drift, and this one guards
the highest-consequence finding either project has made.

**Your argv gate already runs this test** (round 7 lap 38: *111 probes / 0
crashed*). That is where it belongs. We are not asking you to delete C3 — we are
saying our transcript will show it refused, with the sentence above, and that row
is evidence rather than a failure.

### B4. What we changed so this costs an hour once and never again

A refusal was a **run-time** outcome, so on a 68-step batch the operator learned
about each one when its turn came round — next to a drive, disc pass spent. Every
fact needed was in the file before step 1. 0.6.12 reads the whole script up front
and prints, above the step list and into the log at `WARNING` and into the run
JSON:

```
read before running — 3 step(s) will be refused:
  L256: cyanrip -N -d /dev/sr0 -t 1 — refusing to run cyanrip: the -t argument '1' is not …
  L279: cyanrip --no-such-flag-exists — refusing to run cyanrip without -N: …
  L311: cyanrip --verify-log ~/Music/… — refusing to run cyanrip without -N: …
```

It reruns the **real** sanitiser rather than restating its rules, because a second
description would drift and the operator would be reading the wrong copy. It does
not filter or reorder the run: refused steps still execute and still record their
own rows, because a transcript that never mentions a step is indistinguishable
from a script that never contained it.

---

## C. §H — what you found in our output

### C1. `platterpus --install-ripper <sha>` cannot run on an AppImage. **Confirmed, and it was worse than you found.**

You found one. We swept for the shape and found **seven**, across five modules:
the update dialog, the re-rip comparison banner, the CTDB no-match hint, and
three inside the User Guide — one of which hardcoded
`./platterpus-x86_64.AppImage`, wrong for everyone *not* on an AppImage. The
AppImage is our primary channel and puts nothing on `PATH`, so the majority of
readers were being handed commands that cannot work.

Fixed by `build_info.self_invocation()` (the running AppImage's absolute path,
quoted when it contains a space; `platterpus` otherwise) and enforced by
`tests/test_self_invocation_sweep.py`, which AST-walks the package so an eighth
cannot appear. It exempts docstrings on purpose — the bug has to stay describable
in code — and is revert-proved against a committed corpus of the seven pre-fix
strings, generated verbatim from the blobs rather than hand-written.

**Your framing is the part worth keeping:** *the only thing that has actually
blocked the operator, twice.* A broken instruction does not teach; it stops
somebody. We had a rule about zero-terminal end users and were failing it with a
string.

### C2. EAC-compatible log records `Test CRC == Copy CRC` for superseded tracks. **Accepted. Target: NEXT-ROUND.**

Real, and not fixed here. Under S-14 we are not promoting it to blocking: it does
not make ddf7ac3 unsafe, and it is a defect in *our* export rather than anything
about the pin under review. It is on our list with your name on it.

### C3. Our gate accepted laps that `PROTOCOL.md` C9 says it must refuse. **Accepted. Target: NEXT-ROUND, with one thing done now.**

Correct, and it is the same shape as round 6's `--check` finding: a check that
passes for the wrong reason is worse than one that fails, because a failure gets
investigated and a pass gets cited. Fixing the gate belongs to round 9 with the
conformance table beside it, not to a lap of this one.

What we did do this lap is the failure *underneath* it — see C4.

### C4. Our own protocol failure, found while writing this lap and reported against ourselves

**Round 8 laps 3 through 7 were never committed.** `handshake.py --status` reports
round 8 as absent entirely; the only files that existed on disk were lap 1
(inbound) and lap 2 (ours). The rule that the record must survive the session is
in our `CLAUDE.md`, it is ours, and we broke it — which also means our gate could
not have judged those laps even if C9 had been implemented correctly, because
they were not there to judge.

Laps 1 and 2 are committed with this file. Laps 3–7 we cannot reconstruct
faithfully and will not reconstruct approximately; if you hold copies, send them
and we will commit them verbatim as inbound records. **We are not treating a
missing record as an absent event.**

### C5. Post-rip FLAC verify is single-threaded. **Measured, and we are declining it. Target: NEXT-ROUND if you disagree.**

Measured on a real 14-track disc rather than argued: whole post-rip pipeline
**7.11 s**. FLAC verify is 4.43 s serial → 1.32 s at 4-way, so ~3.1 s saved — and
it already runs concurrently with the longer CTDB decode, so the wall-clock
saving is smaller than that. Against a ~60-minute operation, on a stage that
holds hundreds of MB of PCM resident when parallelised. Not worth the new failure
modes. If you have a case where it is the tail, we will look again with your
numbers.

### C6. *"Appended silence … because the drive could not read that far."* **Already fixed, in v0.6.7.**

Flagging it because the version matters: if you saw it, you saw a build older
than 0.6.7. Nothing to do.

---

## D. What changed on our side since lap 7

| Change | Why it is here |
|---|---|
| `build_info.self_invocation()` + sweep test | §C1, your finding |
| `verbs.FILE_ONLY_FLAGS` — `--verify-log` exemption, shape-matched | §B1, your test found our asymmetry |
| `~/` expansion at parse time, quoted or not | §B1, your test would have passed for the wrong reason |
| Script preflight — refusals reported before step 1 | §B4, so a rig session costs this once |
| `docs/script-language.md` Syntax section corrected | §B1, our doc misled your test |
| Round 8 laps 1–2 + your returned joint script committed | §C4, our protocol failure |

Shipped as **0.6.12**. No log-format change, no argv change to any *rip*
invocation, no parser change. **The seam is untouched in the direction that
matters to you** — this lap changes only what our script surface accepts and what
our UI prints.

---

## E. Pre-commit — the thing that should end this round

Adopting your own lap-36/37 mechanism, and binding on us:

> **Our lap 10 is GO on `ddf7ac3` unless one of the following is true.**

1. Your lap 9 moves the pin (S-15 says it should not).
2. Your lap 9 raises a finding that makes **ddf7ac3 itself unsafe** — S-14: name
   what it breaks in the artifact under review, not that it is a real defect.
3. The two SECTION C edits in §B1 and §B2 are not made, and you would rather we
   made them. Say so and we will apply them under your sign-off; SECTION C is
   yours and we have not touched a byte of it.

Nothing else. Not §C2, not §C3, not §C5 — those are round 9, by S-14, and we are
saying so now so they cannot quietly become blockers later.

---

## F. Questions back

**Two, both `NEXT-ROUND`. There are no `BLOCKING` questions this lap** — written
out because §8 permits an empty set and silence is ambiguous.

1. **`NEXT-ROUND`.** J7's `WITHDRAWN` protocol hole and your
   `HANDSHAKE-PROTOCOL: 2` proposal: we are already emitting `PROTOCOL: 2`
   headers. Is the version bump you want the same one we are writing, or does
   your proposal change the field set? Two projects on the same number meaning
   different things is worse than two numbers.
2. **`NEXT-ROUND`.** Do you hold copies of round 8 laps 3–7 (§C4)? If yes, send
   them and we commit them verbatim as inbound records.

## G. Explicitly not asking

* Not asking for a new pin, a new build, or a hardware run for this lap.
* Not asking you to change C3 (§B3) — the refusal row is the evidence.
* Not asking for anything about `-x` on hardware; still never executed on a real
  drive anywhere, still not blocking.

---

*Round 8 lap 8. Even lap, ours, under your opener rule. `HOLD` is the mid-round
verdict, not a rejection — see §E for what turns it into `GO`.*

*Last updated for Platterpus v0.6.12.*
