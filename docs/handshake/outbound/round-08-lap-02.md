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
