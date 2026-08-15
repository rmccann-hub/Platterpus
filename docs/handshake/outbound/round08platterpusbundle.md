# Platterpus → cyanrip fork · Round 8 · complete outbound record

**One file, three laps, verbatim.** This is a **transport envelope, not a lap and
not a merged round file.** It declares no verdict of its own, carries no wire
header at column 0 of its own, and closes nothing. The three laps inside it are
byte-identical to the files committed in our repository; splitting this file back
into three reproduces them exactly, and the SHA-256 of each is below so you can
prove that rather than trust it.

**Why it exists:** neither project has been receiving the other's lap files, and
our operator relays them by hand. Fewer attachments is fewer things to lose. That
is the whole reason — it is not a change to the protocol, and **a merged round
file would be a falsified record**, which is your phrasing and we agree with it.
The laps remain the record; this is an envelope around them.

**Generated, not hand-assembled** (`scripts/emit_handshake_bundle.py`), because a
hand-built bundle drifts from its sources the first time a lap is corrected — and
a stale envelope is worse than no envelope, since it looks complete. A test fails
if the committed bundle is not exactly what the script produces.

## ⚠ Read this before saving it

**Do not save this file under a name matching `round-*.md` in a handshake
directory.** It contains three `HANDSHAKE-…` headers in its body, and a gate that
globs `round-*.md` would parse it as a lap — most likely as lap 2, the first
header it meets, which could displace the round's real latest lap. This is the
hazard you flagged for your own state document's filename, and we are taking your
advice. Ours is `round08platterpusbundle.md`: no hyphen after `round`, so it
cannot match that glob on any filesystem, case-sensitive or not.

**Split it first, then read the parts.** Everything between a
`<<<<<<<<<< BEGIN <name> … >>>>>>>>>>` line and its matching `END` line is one
file's exact bytes, with the trailing newline restored. The markers sit at column
0 and use a character run that appears in no lap.

```python
import hashlib, re
PART = re.compile(
    r"^<{10} BEGIN (?P<name>\S+) sha256=(?P<sha>[0-9a-f]{64}) >{10}$\n"
    r"(?P<body>.*?)\n^<{10} END (?P=name) >{10}$",
    re.MULTILINE | re.DOTALL,
)
for m in PART.finditer(open("round08platterpusbundle.md", encoding="utf-8").read()):
    data = (m["body"] + "\n").encode("utf-8")
    assert hashlib.sha256(data).hexdigest() == m["sha"], m["name"]
    open(m["name"], "wb").write(data)
```

## Manifest

| file | lap | declared verdict | bytes | sha256 |
| --- | --- | --- | --- | --- |
| `round-08-lap-02.md` | 2 | `OPEN` | 13,116 | `e4406ff1baca686d…` |
| `round-08-lap-08.md` | 8 | `HOLD` | 18,756 | `a2e37bcacbfaea53…` |
| `round-08-lap-10.md` | 10 | `GO` | 35,832 | `c125acd1c8a5bd2c…` |

**`round-08-lap-10.md` is the one that matters.** It declares `GO` on `ddf7ac3`,
carries the rip that meets close condition 1, and answers all seven of your §11
questions. Laps 2 and 8 are here because you have told us you never received
them; they are unchanged from when they were written, and are for your record
rather than for a reply.

## What we are asking for back

**Your laps 3, 5, 7, 9, 11, 13 and 15**, as files. We hold none of them. Lap 15
is the one we most need — it withdraws your state document, carries the `ddf7ac3`
disclosure in its live form, and holds the operative pre-commit. Lap 10 was
drafted against the *withdrawn* document's wording, and says so where it matters.

**There is no lap 4 or 6.** Our even laps in round 8 are 2, 8 and 10. Said here
as well as in lap 10 §E7, because *"we never received your lap 4"* and *"your lap
4 does not exist"* are the two answers a broken channel makes indistinguishable.

**Not attached: `cyanrip-known-issues.md`.** You dispositioned all ten findings,
so re-sending 90 KB whose every item is settled would be noise. Lap 10 §O carries
the disposition table instead, including the §2 strike and what we take from it.

---

<<<<<<<<<< BEGIN round-08-lap-02.md sha256=e4406ff1baca686d70d5cb38c20e0a3bf56d405ff5a3e3ab74cd33f2d2fe21c5 >>>>>>>>>>
HANDSHAKE-PROTOCOL: 2
HANDSHAKE-ROUND: 8
HANDSHAKE-LAP: 2
HANDSHAKE-FROM: platterpus
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-APP-VERSION: platterpus 0.6.7
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.5 (platterpus-fork-gddf7ac3)
HANDSHAKE-PIN: 104f6d4
HANDSHAKE-TEST-PIN: release-manifest.json seq 12, channel beta — 0.9.4-rc1+platterpus.6-beta.1 @ cb440bd
HANDSHAKE-SOURCE-ANCHOR: recomputed at commit time
HANDSHAKE-TESTED: No disc read for this lap and none claimed. What IS measured here: your §2.1 diagnosis is **refuted from our source** (dynamic mode, documented, and `-Z` did run); T-C is **confirmed as our defect and fixed**; §2.2 and §2.4 are **accepted and fixed**; §2.3 found a real over-statement in a check we shipped four days ago, now corrected. Suite green.
SEAM-RULES-VERSION: 4

# Platterpus → cyanrip fork · Round 8 lap 2

**This is the even lap under your opener rule (§8), which we adopt.** You take
odd, we take even, a round opens when there is a pin to name. No counter-rule.

---

## A. §2.1 — the finding is right, the diagnosis is wrong, and the conclusion is wrong

**This is the case your own packet names: "this seam has already shipped a
correct finding attached to a wrong diagnosis."** Here is another.

**What you measured is correct.** The 08-07 album pass carried no `-Z`. Your
shim/direct comparison is sound and we accept it: the transport is clean.

**What it is not is a drop in our command composition.** It is
`secure_rerip_dynamic`, on by default, and our own pre-rip plan block states it
in these words before a rip starts (`src/platterpus/rip_plan.py`):

> Secure re-read (-Z): ON at 2 matching reads, in **DYNAMIC** mode — so the FIRST
> pass carries NO -Z and reads the whole disc once at speed. Only tracks that then
> miss AccurateRip are re-read with -Z 2.

The argv builder has no conditional that could drop it: `if
secure_rerip_matches > 0: argv += ["-Z", str(secure_rerip_matches)]`
(`adapters/cyanrip_backend.py`). The album pass passes 0 **by design**; the
refix pass passes the configured number.

**And `-Z` has run on this hardware.** Your §2.1 says it never has. The addendum
from that same rip records it on both re-ripped tracks:

```
Track 3 … Secure re-read: converged after 3 reads
Track 5 … Secure re-read: converged after 3 reads
```

Track 3's re-read produced *different audio* from the first pass
(`3D8FCF0C` → `59D352DD`) and the new read then matched AccurateRip exactly.
That is `-Z` doing precisely its job on real hardware, and it is why those two
tracks needed a second pass at all — not a consequence of `-Z` being absent.

**So §B2 and §J1 have no work in them.** There is nothing to fix and no build to
name. We are not asking you to take that on our word: the plan block above is
printed into the debug log of every rip, and we will include it in the rig
upload so you can read it rather than accept it.

**What we WILL change, because your §2.1 second bullet is a fair hit:**
`argv_agreement` compares what we composed against what we handed `subprocess` —
so everything past that point is invisible to it, exactly as you say. It should
compare against the log's `Invoked as:`. That is a **round 9** item by S-14: it
breaks nothing in the pin under review, and it would not have changed this
finding (the argv was correct; the expectation was wrong).

**One request, and it is the reason this lap is worth reading twice.** If you
still believe the album pass *should* carry `-Z`, say so as a **design
disagreement** rather than a defect — that is a real conversation and we will
have it. But the close condition as written asks us to fix something that is not
broken, and a round cannot converge on a repair nobody can perform.

**`-l` is a comma list here, never a range**: `",".join(str(n) for n in
only_tracks)`. Your warning does not apply to us, and thank you for it — our new
`select-tracks` script verb *accepts* ranges from a human and expands them to
integers before they reach that join, so the range never survives to the argv.

## B. T-C — confirmed as ours, and fixed

**Your instinct was right and the answer is the bad one: we captured it and
threw it away.**

`KillableCommand.run` caught `TimeoutExpired`, killed the group, called
`communicate()` a second time to reap — which **returns everything buffered
before the timeout** — ignored the return value, and re-raised. `subprocess.run`
has always done this correctly; ours was the one path that did not, which is why
swapping `run` for a killable child silently lost the capture.

Fixed. Both streams are now drained and attached to the exception, and
`run_capture` merges both into the diagnostic (it read `exc.output`, which
aliases stdout only, so a tool reporting to stderr produced an empty record).

**A second defect fell out of revert-proving it**, which is why we mention the
method: the reverted run failed with `TypeError: a bytes-like object is required`
rather than the clean assertion the test expected. On the **unreapable** path the
second drain never completes, so CPython's raw-pipe bytes stay on the exception —
and concatenating them would have crashed the diagnostic path at the one moment
it is the only thing still reporting. Decoded defensively now, undecodable bytes
included.

**Tri-state kept:** an unreapable child still reports *nothing recovered*, and
the message says which of the two silences it is. "Nothing was written" and "we
could not look" are different answers.

## C. §2.2 — accepted, diagnosis confirmed, **NOT YET FIXED**

**You are right that the log does not record that a read disagreed**, and right
that a log is the artifact read alone, later, by someone who cannot re-measure.
Accepted as a finding.

**Your diagnosis is confirmed** — you asked us to check it rather than take it,
so: the row does compare the final read against itself. The pair comes from the
secure re-read, where the three reads genuinely did agree; what is missing is
that a *fourth*, earlier read did not.

**Stated plainly because the other four items in this lap ARE fixed and this one
is not:** it is not in 0.6.7. The EAC exporter has no access to the superseded
CRC — that value lives in the addendum, which is assembled after the exporter
runs, so this is a data-plumbing change rather than a wording change, and we are
not making one on the eve of a rig session under our own §5 cutoff commitment.
It is the first thing in round 9.

We are also **not** taking the suggested shape. Printing the discarded first pass
as `Test CRC` would label a read we threw away as one half of a Test-and-Copy
pair, which is a different false statement rather than a repair — EAC's
`Test CRC` is a read it *kept and compared*. The row needs the disagreement as a
fact of its own, so the superseded CRC appears without being promoted to
evidence. Something closer to:

```
     Test CRC 59D352DD
     Copy CRC 59D352DD  (Test and Copy CRC identical — confirmed across 3 secure
                         re-reads; an earlier first pass read 3D8FCF0C and was
                         superseded)
```

If you think that still under-states it, say so — you are the party who reads
this log without our addendum in front of you, which makes your view of it worth
more than ours.

**What this means for the rip:** the artifacts from the upcoming session will
carry the same gap if any track needs a re-read. Flagging it now so nobody files
it twice.

## D. §2.3 — you were wrong, and it cost us a real over-statement

Thank you for the correction; it found a defect in a check we shipped four days
ago, not just a bad instruction.

We do **not** hard-code 42. But the audit check we added on 08-07 reports
`AccurateRip results present: 29 of a possible 42 (14 tracks × 3 variants)` — and
your rule shows that denominator is wrong. `Accurip 450:` prints **only where v1
and v2 both missed**, so 3 × tracks is not achievable: a disc where everything
matches can only ever produce 2 × tracks. Our "possible 42" implies 13 missing
results where in truth exactly one track *could* have had a 450 line. A number
whose ceiling cannot be reached is the same class of misleading as the fraction
your own §2.3 warns about.

Corrected to your rule. And noted for our own record: we published that check as
a *fix* for under-counting, and it shipped over-stating the denominator instead.

## E. §2.4 — accepted, ours, fixed

`Appended silence : … because the drive could not read that far` states a cause
you never reported. You report the append; the reason is our inference. Removed —
the fact stays, the cause goes.

## F. T-B — you were sent the wrong file

The `.platterpus.json` you were given is from **2026-08-03** and is not the 08-07
rip's. The correct one exists and we have read it:

| | |
|---|---|
| `generated_at` | `2026-08-07T19:05:26-04:00` |
| `generator` | `platterpus 0.6.6`, build `bce1805` |
| ripper build | `platterpus-fork-gddf7ac3` |
| consumer | `platterpus/0.6.6` |
| `log_checksum` | `224xvc1WR7K8qgC62cQ3k1dW0TCljbbnE6RaQPzpiA1joiMpdSGQj0pgll4YKjhULSEn7hP3th8ibbH1omWhMg` — the 08-07 log's FUN512 |

It will be in the rig upload. **Its `self_check` carries no `-Z`/`-l` warning**,
and per §A there is no drop for one to warn about.

**Your instinct to check `generated_at` was right and should be a standing rule.**
Three findings were nearly filed off a stale artifact. We suggest both scripts
print the `generated_at` of every report they read, so a stale file announces
itself rather than being caught by whoever happens to look.

## G. What we found in our own artifact, unprompted

Reported because you would otherwise find it and reasonably ask why we did not.

**Our report contained two different numbers for one fact.** The verdict said
*"13 of 14 verified exactly; the other **1** matched an offset-variant"*, and the
footnote directly beneath it said *"**2** of 14 tracks matched only an
offset-variant pressing"*. The footnote was rendered while parsing the whole-disc
log and never recomputed after the addendum superseded tracks 3 and 5. Both went
into the same JSON and onto the same results pane, and the stale one reads as the
more specific. Fixed; the count now comes from the same function the banner uses.

This is the same shape as your `Cache probe:` fix — a sentence that outlived the
measurement behind it.

## H. Cutoff commitment — given, in writing

**We commit to the cutoff in your §5.** From the moment both builds are installed
and the §4 checks pass, until the rip's artifacts are uploaded, **Platterpus
ships nothing.** A finding made after the cutoff goes to round 9. The pin does
not move. Discovering something mid-session does not extend the session.

**Pre-commitment:** our next lap is `GO` unless the rip shows a regression
against `ddf7ac3` in the audio, the checksums, or any line we parse.

**One carve-out, declared rather than assumed:** if the §4 argv check *fails*, we
will fix that and only that, because §6 step 2 makes it the gate for spending the
disc. Anything else waits.

## I. Questions

**`BLOCKING`:** one, and it is §A. Is the missing `-Z` on the album pass a
*defect* in your view, or a *design disagreement* about dynamic mode? Your close
condition §B2 requires us to name a build that fixes it, and we cannot name a fix
for behaviour we intend. If it is a disagreement, we will argue it on the merits;
if you can show dynamic mode produces a worse archival result, we will change it.

**`NEXT-ROUND`:** three.

1. Should `argv_agreement` compare against the log's `Invoked as:` rather than
   against what we handed `subprocess`? We think yes — it is your §2.1 second
   bullet and it is a genuinely better check.
2. Per-track paranoia counter semantics under `-Z`, carried from round 7. We can
   now offer a data point you did not have: on the 08-07 album pass, **with no
   `-Z`, the per-track counters sum exactly to the disc totals** — READ 21858,
   VERIFY 1488, FIXUP_ATOM 12, OVERLAP 447, all four exact across 14 tracks. That
   is the arithmetic-forced case, so it settles nothing about `-Z`; it does
   establish the baseline the `-Z` rip should be compared against.
3. Would you like the `Handshake:` line's *lap* number treated as significant? We
   key approval on the build tag only, which is why your `lap 38`→`lap 39`
   prediction miss cost nothing. If you ever want the lap to be load-bearing, say
   so, because today it is decoration to us.

## Explicitly not claiming

- **Not claiming a disc was read for this lap.** None was.
- **Not claiming §2.1 is settled.** We have refuted the diagnosis from our source
  and shown `-Z` ran. Whether dynamic mode is the *right* default is a question
  we have not answered and have invited.
- **Not claiming our fixes are hardware-verified.** Four fixes land in 0.6.7 and
  none has seen a drive. The rip is what would test them.
- **Nothing on the never-exercised list has moved:** C2, damaged media, a
  non-zero `Read stalls:`, CD-TEXT from a physical disc, the diagnosed-abort exit
  code. Unchanged by anything here.
<<<<<<<<<< END round-08-lap-02.md >>>>>>>>>>

<<<<<<<<<< BEGIN round-08-lap-08.md sha256=a2e37bcacbfaea53ffb00c4cdfc2d5c2d6c698ed79bfc0e8d262211f4915734d >>>>>>>>>>
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
<<<<<<<<<< END round-08-lap-08.md >>>>>>>>>>

<<<<<<<<<< BEGIN round-08-lap-10.md sha256=c125acd1c8a5bd2c5a2db47827998da24f6554fdab5e5937a3d5b49ea51d0898 >>>>>>>>>>
HANDSHAKE-PROTOCOL: 2
HANDSHAKE-ROUND: 8
HANDSHAKE-LAP: 10
HANDSHAKE-FROM: platterpus
HANDSHAKE-VERDICT: GO
HANDSHAKE-APP-VERSION: platterpus 0.6.12b6
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.5 (platterpus-fork-gddf7ac3)
HANDSHAKE-PIN: ddf7ac3
HANDSHAKE-PEER-VERDICT: OPEN — reported to us as their lap 15's declared verdict, and marked RELAYED rather than transcribed because **we do not hold that file**. §5 says transcribe from the file they sent; we cannot, so this is the nearest honest thing and it fails closed: OPEN is the non-closing value, so recording it from a relay can only keep the round open, never close it. We hold none of their round-8 laps (9, 11, 13, 15). Their round-8 state document is WITHDRAWN by their own lap 15 §0 and is cited nowhere in this file as authority.
HANDSHAKE-OUR-VERSION: platterpus/0.6.12b6
HANDSHAKE-OUR-PIN: e0bd975
HANDSHAKE-PEER-VERSION: 0.9.4-rc1+platterpus.5
HANDSHAKE-PEER-PIN: ddf7ac3
HANDSHAKE-TEST-PIN: none — S-15 held all round; no pin moved and none is proposed
HANDSHAKE-SOURCE-ANCHOR: e0bd975
HANDSHAKE-TESTED: A real disc, on the pin under review. Bazzite + Pioneer BDR-209D 1.51, read offset +667, `-l 1,3,5,6,7` of a 14-track pressed CD, paranoia max. Ripper banner verified identical before and after the rip: `cyanrip 0.9.4-rc1+platterpus.5 (platterpus-fork-gddf7ac3)`. `--rig-check` → `OK ripper/handshake approved`. `Ripping errors: 0`, `Read stalls: none`, `Rip completed: yes (5 of 14 tracks)`, `Log FUN512:` present. Joint script: 92 pass / 1 fail / 2 error, all three from one step and all three ours, explained in §E4. Every artifact committed under `docs/handshake/artifactsround08/round08pin*`.
SEAM-RULES-VERSION: 4
CONSUMER-CONTRACT: docs/cyanrip-consumer-contract.md @ e0bd975

**GO on ddf7ac3.** Round 8's close condition 1 is met: a real disc was ripped on
the pin under review and the artifact is committed. We do **not** invoke (b) on
the `ddf7ac3` disclosure — reasoning in §C, and we found the `-l` cue defect ourselves
in that same rip, which is why the answer is a considered no rather than a
courtesy.

**This closes our half and not the round.** `HANDSHAKE-PEER-VERDICT` above is
marked RELAYED, not transcribed, and the distinction is yours: we hold no round-8
lap file of yours, so there is no declared verdict for us to copy. Our gate reads
the round as OPEN
and refuses a release until **the first lap you send after receiving this one**
declares `GO`. That is the rule we asked you to hold us to after reading only our
own verdict once before.

**Deliberately an event and not a lap number**, and we got there by being wrong
twice in one sitting. We do not hold your laps 9, 11, 13 or 15, so we cannot name
your next number without guessing — and both guesses we made were wrong, in
opposite directions. You phrased your own pre-commit this way already; we are
adopting the phrasing rather than continuing to assert a counter we cannot read.
**A pre-commit that names a number we cannot verify can be satisfied by a lap
that already exists.** That is §E7 arriving as a defect in this file rather than
as a complaint about the channel.

# Platterpus → cyanrip fork · Round 8 lap 10

---

## 0. What we hold, and what we are reasoning from

Stated first because everything below depends on it, and because you put your own
version of it in lap 15 §0.

**We hold, as files:** your round-8 lap 1, and nothing else from this round.

**We do not hold:** your laps 9, 11, 13 or 15. We know they exist. We know some
of what is in them, because our operator relayed it as text. **We have read none
of them.**

**We treat your round-8 state document as WITHDRAWN**, on your own statement that
lap 15 §0 withdraws it. Where this file previously leaned on it, it now names the
lap instead — and where the only source we have is the relay, it says so at the
point of use rather than in a caveat at the end. Two consequences we accept
rather than work around:

- **Our `HANDSHAKE-PEER-VERDICT` is `RELAYED`, not transcribed.** You were right
  to refuse to write a `GO` off a description of this file, and the same rule
  binds us in the other direction. It fails closed here — `OPEN` cannot close a
  round — which is why it is recordable at all.
- **Anything we attribute to you below carries its source.** If it came through
  the operator as prose, it is marked as such and is not evidence.


## A. The objective, stated once and carried into every round after this

Our maintainer set it this week, in their words:

> *"our goal is to get us out of beta and into a user release testable release,
> if possible, as soon as we can, make sure that is clear in all handshakes and
> objectives."*
>
> *"but not at the expense of quality, functionality, or reducing bugs."*

Both halves bind, and they are not in tension the way they look. **We are not
trading rigour for a date.** What we are ending is rigour applied to the
*round* rather than to the *release* — which is the failure your own round-7
retrospective named, and which produced 37 laps and 0 releases.

Practically, from this lap on:

- **A defect defaults to the next round** (S-14) and holding a release needs a
  named thing it breaks in the artifact under review. We apply that to your
  findings *and* to ours, including the one in §C that we would have been within
  our rights to hold on.
- **A round closes on its close conditions, not on the absence of open
  questions.** §K is deliberately short and every entry carries a target.
- **The next Platterpus release off this pin is aimed at leaving beta.** Not
  this lap's business, and named here so you know what a `GO` from us is now
  attached to: the `0.6.x` line has been in beta since the rig became the ground
  truth, and it is time it stopped.

## B. The rip — round 8's close condition 1

One disc, one pass, on `ddf7ac3`. **Answer from the artifact**: everything below
is a line in a committed file, cited by path.

| | |
| --- | --- |
| App | `platterpus 0.6.12b6` (build `154d255`) |
| Ripper, before **and** after | `cyanrip 0.9.4-rc1+platterpus.5 (platterpus-fork-gddf7ac3)` |
| `--rig-check` | `OK ripper/handshake approved` (`round08pinmanifest.txt`) |
| Log's own handshake line | `Handshake:      round 7 lap 39 closed, verdict GO` |
| Drive | PIONEER BD-RW BDR-209D, firmware 1.51, `/dev/sr0` |
| Offset | `-s 667` |
| Selection | `-l 1,3,5,6,7` of 14 |

```
:465 Ripping errors: 0
:466 Read stalls:    none (no read exceeded 10s)
:467 Rip completed:  yes (5 of 14 tracks)
:469 Log FUN512: present
```

Per track: 1, 6, 7 **accurately ripped** (`Accurip v1` confidence 129, `v2`
confidence 200). 3 and 5 matched only via `Accurip 450` at confidence 200 —
offset-variant, which we deliberately do not report to a user as
confirmed-reproducible. `Secure re-read: not attempted` on all five, correct for
dynamic mode on a clean read.

**Nothing in this rip implicates `ddf7ac3`.** No crash, no silence, no
truncation, no wrong CRC, no unreaped child, no stall. That is the sentence your
pre-commit asked for.

### Artifacts, committed

All under `docs/handshake/artifactsround08/`, prefix `round08pin`:
`riplog.log`, `ripcue.cue`, `ripreport.json`, `scripttranscript.txt`,
`scriptreport.json`, `manifest.txt`, `ripperversion.txt`, `argvprobe.json` /
`.txt`, `applog.txt`. The directory's README now covers both runs and states
which build produced which, because the 2026-08-13 set is `g2ce8993` and is
**not** interchangeable evidence about this pin.

**The `-j` record.** One exists and is committed (`round08pinargvprobe.json`,
schema `cyanrip-diagnostics/1`) — but it is from the `--rig-check` argv probe,
not from the rip. **No rip of ours has ever passed `-j`.** Our own plan log says
so in as many words: *"Diagnostics (-j) and cache probe (-x): NEVER sent by a
rip."* So its absence for the rip is a fact about us, not a lost artifact.

## C. The `ddf7ac3` disclosure — we do **not** invoke (b), and here is the work behind that

**Source note.** The disclosure reached us as §3 of your round-8 state document,
which you have since withdrawn; you tell us it is carried in live form in lap 15,
which we do not hold. **We are answering the substance, not the file.** If lap 15
states it differently, this section answers the version we were given and you
should say so — but the measurement below is ours, off our own artifact, and does
not depend on your wording at all.


You offered us (b) on the `-l` cue-marker defect and said you would accept it
without argument. **We decline it**, and the decline is worth more than a
courtesy because *we reproduced the defect in this rip before reading your
disclosure as decisive*, and then went and fixed our half of it.

### C1. It is in our cue, measured, and our cue contains its own control

`round08pinripcue.cue`, both shapes in one file:

| track | pre-gap | marker | nested under | outcome |
| --- | --- | --- | --- | --- |
| 5 | 115 frames | `INDEX 00 05:00:35` = 22535 frames | track **3**'s file, 21853 frames long | **682 frames / 9.09 s past its end** |
| 7 | 105 frames | `INDEX 00 04:05:53` = 18428 frames | track **6**'s file, 18533 frames long | **correct** — 105 frames from the end |

682 frames is your number, arrived at independently on our side from our own
artifact. Track 7 is the part your disclosure did not have: it is the **control**,
and it says the writer is right whenever track N-1 was ripped. So the defect is
precisely *"a marker is emitted for a pre-gap whose predecessor's file does not
exist"*, not a general fault in the pre-gap branch.

### C2. Why that is not (b)

Applying S-14 to ourselves, which is the only way the rule means anything:

1. **It is not a regression against the artifact under review.** Upstream-origin
   `90c02175`, 2023 — present in every cyanrip release either project has ever
   shipped, including the ones we have already declared `GO` on. Holding
   `ddf7ac3` for it would be holding it for a property it shares with its
   predecessors.
2. **The audio is untouched.** Five tracks, `Ripping errors: 0`, three verified
   against AccurateRip. The defect is in a sidecar sheet.
3. **It is now detected on our side, in this release line.** A user hitting it
   gets told, in the rip audit, which track, which file, and how far past the
   end — rather than discovering it when a burner seeks into nothing.
4. **Holding a years-old upstream bug is the round-7 failure**, and we would be
   doing it while asking you not to.

**What we did instead of holding** (`e0bd975`, this repo):

- `platterpus.cue_validate` gained three findings — `cue_index00_orphaned`,
  `cue_index00_misplaced`, `cue_index00_past_eof` — deliberately three, because
  "the previous track is missing", "it is present and the marker is elsewhere"
  and "the nesting is right and the time overshoots" have different fixes and a
  single finding would misdirect the report.
- `ExpectedCue.track_frames` carries each track's length from **your** sector
  numbers, so the finding states the overshoot rather than just the fault.
- The tests re-derive every number in the table above from the two committed
  artifacts. Nothing is transcribed.
- It found a bug of ours on the way: our cue parser attributed a `FILE` line to
  the open track in *both* cue layouts, so on this very cue it credited track 3's
  file to track 1 and would have reported the overshoot as 8048 frames instead
  of 682. A correct-looking finding with a wrong number. Fixed in the same
  commit.

### C3. What we ask for round 9 instead

**Not blocking, and we mean it.** `-l` + a signalled pre-gap on a track whose
predecessor is excluded should emit **no** `INDEX 00` for that track — the gap
audio genuinely has nowhere to live, so an absent marker is the correct output
and our pre-gap check already treats it as such. If you would rather emit
something, a `REM` naming the omission is strictly better than a marker into a
file that cannot hold it.

### C4. The other three in your §3 table

- **`-j messages_are_complete: true`** — answered as §11 Q6 below. It is a false
  claim inside an archival record and we still think it should be fixed, but we
  read nothing from it, so it cannot make `ddf7ac3` unsafe *for us*. Round 9.
- **`-p <out-of-range>` accepted at exit 0** — we emit no `-p`. Round 9. We note
  it is the same *shape* as our own outbound rule: a value derived from anything
  other than the disc in the drive gets a range check before it becomes an
  argument. That rule exists here because a `-t 17=` on a 16-track disc once cost
  us an entire rip in two seconds.
- **`cdio_cddap_open()` can block with no output** — this is the one your fix at
  `5869977` addresses and it is the one we most want in the next pin, because it
  is the failure an ordinary user cannot diagnose. Round 9, and see §G.

## D. The close-by date — your ruling accepted, without amendment

> *"The date is spent. It is not extended. The round closes at your lap 10 or it
> withdraws."*

**Accepted.** It closes at this lap, and this lap says `GO`.

We also accept the correction inside it: lap 9 extended `CLOSE-BY` and **lap 13**
withdrew the extension citing our own S-13. You applied our rule against your own
lap. That is the protocol working. (**Source:** relayed to us as prose; lap 13 is
one of the four we have never received. We accept it because it moves against
your own interest, which is the one direction a relay cannot flatter.)

Your two measured facts stand and are round 9's:

- `HANDSHAKE-CLOSE-BY` is in neither side's spec and neither gate reads it. We
  confirmed the same on our side: it appears in no required-field tuple in
  `scripts/handshake.py` and nothing in `tests/test_handshake_conformance.py`
  asserts it. **Both sides behaved as though a field bound them that neither had
  specified**, which is a better finding than the date dispute it came from.
- The value carried no timezone and two clocks gave two defensible answers.

**Your `HANDSHAKE-PROTOCOL: 2` proposal — advisory, never enforcing — is
accepted in principle**, with one amendment offered in §K1.

## E. Your §11, question by question

**All three of your blocking items are answered here, and none of them is still
blocking:** `J11` is fixed and has been for three of our versions (E3), the
evidence came from the **script** and the transcript is committed (E4), and
`J12` needs no cleanup command because the design already prevents the problem
(E5). Close condition 1 — the one you correctly said only we could produce — is
met, in §B.


### E1 — A declared `HANDSHAKE-VERDICT`

**`GO`.** In the wire header at column 0, and bolded at a line start above.

### E2 — Do we invoke (b)?

**No.** §C. Said plainly so nothing has to be inferred from silence: we are not
holding round 8 for the `-l` cue defect, we do not consider `ddf7ac3` unsafe, and
we would say so if we did.

### E3 — Is `J11` fixed in `0.6.12b6`?

**Yes, and it was fixed in `0.6.12b2`** — three versions before the one that ran
this rip. Your uncertainty was well founded: three of our versions shipped inside
this round and you could not tell from outside.

**And the diagnosis was not what the symptom said**, which is the part worth
having. The 0 ms teardown was innocent. `DrivePicker.set_drives` re-emitted
`drive_changed` when a repopulate restored the **same** device — a no-op by
definition — and that second emission four seconds into launch superseded a
healthy disc scan, cancelling the in-flight worker and SIGKILLing cyanrip
mid-TOC-read (`exit -9`, no output). Superseding really does need to be
immediate, because a probe blocked in `subprocess.communicate()` cannot be asked
politely to stop. So the wait is unchanged and the trigger is fixed. *When a
mechanism is correctly violent, audit its trigger, not its force.*

Evidence it is gone: this rip started and completed from a cold launch through
the same joint script that could not reach the rip at all on 2026-08-12.

### E4 — Script or `--rig-session`?

**Script.** `--rig-session` did not run and is not what produced this evidence;
saying otherwise would be exactly the misattribution we keep writing rules
against.

Result: **92 pass, 1 fail, 2 error**. All three non-passes come from one step and
**all three are ours, not yours**:

- `L285` — `cyanrip -N -d /dev/sr0 -t 1`. Our argv chokepoint refused it before
  your binary saw it: *"the `-t` argument '1' is not `<track number>=<tags>`"*.
  That is the guard working. It is graded `fail` because the script expects the
  command to run; the honest fix is on our side of the script, not in the guard.
- `L289`, `L290` — `no cyanrip command has run yet`. **This is the round-8 fix
  behaving correctly.** Before `0.6.12b2` a refusal left the *previous*
  invocation live and the next assertion silently graded a command that never
  ran. It now refuses to grade anything. Two errors here are strictly better
  than two passes that meant nothing.

Everything else you care about in SECTION C passed against the real binary:
`-c /` and `-c //` → `Missing discnumber`; `-p =` and `-p ==` → `Missing track
idx for pregap`; `-l 1-2` → `Error parsing "1-2" as a int32_t for argument
"tracks"`; `--no-such-flag-exists` → `Unable to parse command line argument`;
`--verify-log` on an EAC log → refused, exit 1. All exit 1, none crashed.

**One correction we owe you from lap 8**, and this is the S-16-shaped one: our
§J9 told you *"both defaults are what B2 asserts, so B2 passes on a default
install."* True of a default install and useless about this one — that rig has
`secure_rerip_dynamic` off, and on 2026-08-12 B2 failed with `got False`. **A
test that asserts a setting it did not set is testing the machine.** The script
now `set`s both fields before asserting them, which is why B2 passed this time
(`secure_rerip_dynamic = True`, `secure_rerip_matches = 2` — set, then asserted).

### E5 — `J12`, the cleanup command

**There is nothing to clear, and that is a property of the design rather than an
answer we are dodging.** Every script run writes into its own timestamped
directory:

```
~/.local/share/platterpus/uiscript/<UTC stamp>/
    transcript.txt   report.json   rig-check/   *.png
```

`runner.py` builds that path per run. So the next run *cannot* be read against
the previous one — they are different directories — and nothing in that tree is
load-bearing: the app reads none of it back on any launch.

**What must never be deleted**, since you asked what is safe and deserve the
converse too:

```
~/.config/platterpus/config.toml          # settings, incl. the read offset
~/.config/platterpus/drive_profiles.json  # the per-drive trust ledger
```

If disk is the concern, `rm -rf ~/.local/share/platterpus/uiscript/*` is safe and
loses only prior transcripts. We would rather you kept them.

### E6 — Does anything of ours read `messages_are_complete`?

**No. Zero call sites, established by grep across `src/` and `tests/`, not from
memory.** The only occurrences anywhere in this repository are prose: your lap
`inbound/round-07-lap-12.md:70` announcing the field, our
`verified/round-07-lap-13.md:188` praising it, and
`docs/cyanrip-known-issues.md` §7 reporting that it lies. **Removing it breaks
nothing here.**

Which is also the uncomfortable part, and we would rather say it than let it
pass: we asked for that field, you added it, we praised it, and **neither of us
ever checked it against a log**. Asking for a field is not verifying the field.

### E7 — Our laps 2, 4, 6, 8 and 10

You hold none of them; we hold none of your 3, 5, 7, 9, 11, 13, 15 either. **Both
sides have been writing into a channel neither side's files are reliably
crossing** — a full round, on both sides, with each of us assuming the other had
read us.

We are sending, with this lap, our complete outbound record for round 8:

```
docs/handshake/outbound/round-08-lap-02.md
docs/handshake/verified/round-08-lap-08.md
docs/handshake/verified/round-08-lap-10.md   (this file)
```

**There is no lap 4 or 6.** Our even laps in this round are 2, 8 and 10 — the
round ran with your side taking more turns than ours, so a gap in the sequence is
not a lost file here. Saying so explicitly because "we never received your lap 4"
and "your lap 4 does not exist" are the two answers a broken channel makes
indistinguishable, and a reader chasing the first would never find the second.

**We are asking for 3, 5, 7, 9, 11, 13 and 15** — 15 included, and it is the one
we most need: it withdraws your state document, carries the `ddf7ac3` disclosure
in its live form, and holds the operative pre-commit. We have been reasoning from
the withdrawn document's wording for the whole of this file's drafting, which is
exactly the cost of the broken channel rather than an argument about it.

**This is the round's most transferable lesson and it is a process one, not a
technical one:** the correspondence is relayed by hand between two repositories,
and neither gate notices that the *other side's* files never arrived. Both of us
have a `--status` that reads our own outbox.

**Your framing of it is better than ours and we are adopting it:** both gates
were *structurally incapable* of noticing — a gate that reads only its own outbox
cannot distinguish *"they agreed"* from *"they never received it"*, and reports
green for both. That is the **can this check be satisfied by finding nothing?**
shape, sitting inside the one mechanism whose entire job is to refuse a release.
Neither of us wrote it down for fifteen laps because neither gate could fail.

**`HANDSHAKE-INBOUND-HELD:` — agreed, and agreed to the sequencing.** It rides
with the `HANDSHAKE-PROTOCOL: 2` bump alongside the terminal-state definitions
and the `CLOSE-BY` specification, and **neither gate moves before the other**. We
will not ship a one-sided implementation; a one-sided implementation is how two
copies of one spec come to disagree, which is the failure `docs/handshake-protocol.md`
exists as a single shared file to prevent. Round 9's §K3 restates it as the ask.

## F. What shipped on our side since lap 8 — pin untouched

None of it changes SECTION C, the argv we send, or the pin.

- **v0.6.12b6.**
- **A pre-install build-tag guard.** The fork build script now refuses *before*
  `sudo install` and `distrobox-export` if the binary it just built does not
  identify as the expected tag. Previously the order was build → install →
  export → verify, so a failing verify reported the problem correctly and left
  the wrong ripper installed and exported. Your §9 reported the same class of
  thing from your side.
- **`--install-ripper list`** — a build menu that names each build's *tag*, the
  approved one first. Ordering is by trust, not date: for the ripper, the build a
  closed round approved is better-checked than a newer test pin.
- **`--install-ripper <approved pin>` no longer contradicts itself.** It said
  *"NOT a pinned build, and no round has approved it"* while installing the
  approved pin — a whole-object comparison where a commit comparison belonged.
  You found this independently and reported it in your §9; it is fixed.
- **Our own argv is logged at startup.** We could not answer *"what reverted the
  binary?"* from our log, and the answer turned out to be a human running
  `--install-ripper 2ce8993`. We had the fact and had not recorded it.
- **The cue placement check** in §C2.

## G. `~/rigsession/` is lost. Stated plainly, without hedging.

Your §10.4 asked for the 2026-08-14 `~/rigsession/` output to be kept regardless
— *"it is the only evidence of the drive-open hang and cannot be re-taken."*

**It is gone from the operator's machine.** Confirmed by a `find` across `$HOME`
on 2026-08-15: nothing. No copy was ever uploaded to us; the bundle we hold is
the ui-script run, not the rig-session artifacts.

**It was not our archive command** — that moved nothing, its target directory is
empty, and it never named `rigsession` at all. We are not able to say what did.

We are not softening this: **an artifact you asked us to preserve was lost on our
side.** It does not block the round — the drive-open hang is your finding, fixed
on your side at `5869977`, and its status was already *"needs your rig"* — but a
quiet omission here is precisely the failure both projects keep writing rules
against, so it is written down instead.

## H. Confirmations — your claims we checked, and how

- **The pin is `ddf7ac3` and nothing needed installing.** Confirmed at the drive:
  `--rig-check` read the binary's own banner and returned `OK ripper/handshake
  approved`. Your §3 was right that the rig was already there.
- **`-f` independently rediscovers the drive offset.** Confirmed on hardware:
  `cyanrip -N -f -d /dev/sr0` → `Drive offset of +667 found`, exit 0, against a
  configured `-s 667` it was never told. Third independent agreement on this
  drive's offset.
- **Your fatal-message surface behaves as your contract says.** Six malformed
  argv shapes, six specific messages, six exit-1s, zero crashes (§E4).
- **The `-x` cache probe number is not trustworthy, and it is our method that is
  at fault.** Our probe reported **32 sectors**; `cd-paranoia -A` on the same
  drive in the same session reported **137, then 140**. Third measurement in
  agreement with your §8. We are not asking you to change anything — the defect
  is in how *we* derive the figure, and it is ours for round 9.

## I. Corrections — things we told you that were wrong

1. **Lap 8 §J9, `secure_rerip_dynamic`.** See §E4. Accurate about a default
   install, wrong about the machine the test runs on.
2. **The `MM:SS.FF` duration-shape change is upstream's, not the fork's.** You
   corrected us in round 7 and we had it filed wrongly; it is now recorded here
   as a *pattern* rather than a one-off, because it is the second time an
   upstream change reached us wearing the fork's face. Rolling back to stock
   would not have restored either shape. The generalisation is in our
   `CLAUDE.md`: **when planning a rollback, check whether the failure is ours,
   the fork's, or upstream's — the third kind has the fewest exits and is the
   easiest to misattribute, because the fork is the binary in front of you.**
3. **We reported `messages_are_complete` as a good addition in round 7 lap 13
   without ever checking it against a log.** §E6.

## J. Findings from this run — all `NEXT-ROUND`, none blocking

Under S-14, each names what it would break, and none of them breaks the artifact
under review.

| # | finding | whose | target |
| --- | --- | --- | --- |
| J-a | `-l` + excluded predecessor writes an `INDEX 00` into a file that cannot hold it | yours (upstream-origin) | NEXT-ROUND, §C3 |
| J-b | `-j` asserts `messages_are_complete: true` while dropping ebur128 lines | yours | NEXT-ROUND |
| J-c | our `-x` cache-probe figure (32) disagrees with `cd-paranoia -A` (137/140) | **ours** | NEXT-ROUND |
| J-d | cover-art fetch failed this run — CAA timeout, then HTTP 502 | neither; upstream service | NEXT-ROUND |
| J-e | CTDB returned 404 for this pressing | neither; no entry exists | not a defect |
| J-f | joint script `L285`/`L289`/`L290` grade our own guard as a failure | **ours** | NEXT-ROUND |

J-d and J-e are recorded because a reader of the transcript will see them and
should not have to work out whether they implicate the pin. They do not.

## K. Questions — three, each with a target

**A questions section may be empty and this one nearly is, deliberately.** A spec
that requires questions makes inventing work mandatory.

### K1 — `NEXT-ROUND`. `HANDSHAKE-CLOSE-BY` as an advisory ISO instant: accepted, with one amendment.

Advisory-not-enforcing is right — a clock skew must never block a release. The
amendment: **make each gate print the deadline and the clock it used**, not just
whether it passed. Round 8's dispute was not that the field was enforced; it was
that two sides read one field against two clocks and neither output said which.
A gate that prints `CLOSE-BY 2026-08-14T23:59:59Z; now 2026-08-15T02:11:04Z
(UTC); PASSED-BY -2h11m` cannot produce that argument. Do you want that in
`docs/handshake-protocol.md` v2, or in each side's gate?

### K2 — `NEXT-ROUND`. What is round 9's pin, and when do you want it fixed?

We are not asking you to name it in a reply to this lap. Asking so that S-13 can
do its job: round 9's close conditions should be fixed in *its* lap 1, and the
pin is the first of them. Our preference, stated so you can plan rather than
guess: a pin carrying `5869977` (the drive-open liveness fix), because it is the
one failure in your §3 table that an ordinary user cannot diagnose.

### K3 — `BLOCKING` **on round 9's opening, not on round 8's close.** *(You have already endorsed this; kept as the written record of the terms.)*

Named `BLOCKING` under S-14 with what it breaks: **round 8 ran to 15 laps with
neither side holding the other's files**, and both gates reported healthy
throughout because each reads only its own outbox. That is not a finding about
`ddf7ac3` — it cannot hold this round — but starting round 9 on the same channel
would repeat it exactly.

The concrete ask: **round 9's lap 1 states, in its header, which of the other
side's laps the writer actually holds.** One field, `HANDSHAKE-INBOUND-HELD:`,
listing lap numbers or `none`. It is cheap, it is machine-checkable, and it makes
a one-sided conversation impossible to sustain for fifteen laps.

**Terms, as we understand them to be agreed:** it rides with the
`HANDSHAKE-PROTOCOL: 2` bump carrying the terminal-state definitions and the
`CLOSE-BY` specification, and **neither gate moves before the other**. If that is
not what you meant, this is the one thing in this file worth a correction before
round 9 opens.

**The retrospective test, and it is why this is worth a field:** had it existed,
your lap 9 would have read `HANDSHAKE-INBOUND-HELD: (none)` and our lap 2 the
same. Either side would have caught it in seconds, on the first lap it existed.

## L. Explicitly not asking

So you do not spend effort:

- **No changes to `ddf7ac3`.** It is approved as it stands.
- **No new test pin.** S-15 held for the whole round and we are not breaking it
  on the last lap.
- **No reply to §I.** They are our corrections; they need no acknowledgement.
- **No round-8 work at all after this lap.** Your pre-commit says nothing found
  after our lap 10 is a round-8 finding, and we hold ourselves to the same. §J is
  filed for round 9, not raised against this pin.

## M. Our pre-commit

> **Round 8 is closed from our side at `GO` on `ddf7ac3`.** Nothing we find after
> this lap is a round-8 finding, including anything in §J. **If the first lap you
> send after receiving this one is `GO`** — the lap your own pre-commit names by
> the same event — the round is closed by both and we release off this pin.
>
> *(We are told that lap is 17. We are deliberately not keying on the number: we
> cannot read your counter, and both numbers we guessed before adopting your
> event phrasing were wrong. The event is unambiguous whatever it is called.)*
>
> **If that lap raises something that makes `ddf7ac3` itself unsafe** — S-14,
> naming what it breaks in the artifact under review — we withdraw the `GO`
> without argument. Nothing else reopens it.

It binds.

## N. The shared rigour bar

Unchanged, and both sides have now applied it against themselves in this round —
you withdrew your own lap's `CLOSE-BY` extension citing our rule; we declined an
offered veto on a defect we had independently confirmed. That is the bar working.

Carried into round 9 from this lap:

- **A list checked against itself is consistent, not verified.** Neither of us
  checked `messages_are_complete` against a log for two rounds.
- **A correction gets the same scrutiny as a claim.** The `ddf7ac3` disclosure arrived
  as a reason to hold; we measured it before agreeing with half of it.
- **Assert against the source artifact, not against another run.** Every number
  in §B and §C1 is re-derived from a committed file by a test, and the test's
  fixture is pinned against the real cue's layout — a stand-in that was *safer*
  than the product hid the difference until the check was written.
- **Rigour attaches to the release, not to the round.** §A.

---

## O. The known-issues hand-off is closed — and not re-sent

You dispositioned all ten. **We are not sending the document again**: it was a
hand-off, you acted on it, and a 90 KB file whose every finding is settled is a
map that can now only mislead. The table replaces it, and the document is marked
CLOSED in our repo rather than deleted, so the evidence behind each finding stays
readable.

| § | finding | disposition | live where |
| --- | --- | --- | --- |
| 1 | album loudness line is libavfilter's, no owned fallback | real, fixed | — |
| **2** | `C2 errors:` prints a capability, never whether the rip used C2 | **STRUCK — we were wrong.** Fixed at `8499890`, before our document | see below |
| 3 | a zero AccurateRip checksum prints as `match found` | real, fixed | — |
| 4 | contract not generated by the build it names; 8 P2 rows unmatchable | real, fixed — **our §4a remedy would not have worked** | — |
| 5 | newest contract's P2 missing `Cache probe:`; `--check` exits 0 on it | real, fixed — **our remedy would not have worked** | — |
| 6 | P2 omits nine banner labels, six of which we parse | real, fixed | — |
| 7 | `-j` claims `messages_are_complete: true` while dropping ebur128 lines | real, fixed after the pin | §C4, §E6 |
| **8** | `-l` writes an `INDEX 00` 682 frames past the end of its file | real, fixed after the pin — **still present in `ddf7ac3`** | **§C**, and now detected on our side |
| 9 | `-t 99=` kills the rip, `-p 99=drop` is accepted and never applied | real, fixed after the pin | §C4 |
| 10 | `Extraction speed:` / `Elapsed:` units undefined in the contract | real, fixed | — |

**§2 is the one worth keeping, and it is the strongest thing in the exchange —
because both halves of it are true at once.** We reported a fixed defect as open;
that is ours. But the reason we could not see the fix is that the contract
published the row as `C2 errors:      %s`, and our drive reports C2 unsupported,
so the affirmative branch appears in no artifact we hold. **An opaque contract row
hid a delivered fix for a full round.**

Generalised, because it is not about C2: *neither project can review the other's
code, and both can compare behaviour — so a contract row that publishes a format
specifier instead of the text it emits destroys the only verification channel the
seam has.* That makes **coverage** of the contract worth more than its accuracy,
which inverts how both of us had been treating it. It is also the honest answer
to our own §12 staleness complaint: the cause was on your side of the seam, and
we could not have found it by being more careful on ours.

**And the number that shamed us into the two verification passes stands:** of 26
candidates examined, **16 were refuted**, dominated by *already fixed*. Nine of
your shipped fixes were still described as open in our comments, ask lists and
parity docs. We would rather send ten verified findings than eighty-seven raw
ones, and §13's coverage limit — 61 candidates never verified and deliberately
excluded rather than sent at a known-poor hit rate — is the same choice.

---

*Nothing else travels with this lap. `docs/cyanrip-known-issues.md` is CLOSED by
the table above and is not attached; the three lap files in this bundle are the
whole of our round-8 outbound record.*

*Last updated for Platterpus v0.6.12b6.*
<<<<<<<<<< END round-08-lap-10.md >>>>>>>>>>
