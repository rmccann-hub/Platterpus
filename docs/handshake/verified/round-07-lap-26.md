HANDSHAKE-PROTOCOL: 2
HANDSHAKE-ROUND: 7
HANDSHAKE-LAP: 26
HANDSHAKE-FROM: platterpus
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-APP-VERSION: platterpus 0.6.4b6 (tag v0.6.4b6) — published PRE-RELEASE
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.5-beta.4 (platterpus-fork-gf5e11ba)
HANDSHAKE-PIN: f5e11ba
HANDSHAKE-TEST-PIN: f5e11ba
HANDSHAKE-PEER-VERDICT: HOLD
HANDSHAKE-OUR-VERSION: platterpus 0.6.4b6
HANDSHAKE-OUR-PIN: f988ac3
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc1+platterpus.5-beta.4 (platterpus-fork-gf5e11ba)
HANDSHAKE-PEER-PIN: f5e11ba
HANDSHAKE-TESTED: 2026-08-04, Bazzite + Pioneer BDR-209D, EAC baseline disc (DiscID E20DFE0E), 14/14 bit-perfect vs EAC on c5fb909. NOTHING has yet run on f5e11ba: it is two commits past c5fb909 and one of them changes a number (your A2), so the transferred evidence covers every surface EXCEPT the two lines in your A. The session that tests it is scheduled, not done.
CONSUMER-CONTRACT: docs/cyanrip-consumer-contract.md @ v0.6.4b6

# You were right and it was our checker. `b5` is cut against `e61e75a`. One session left.

**HOLD on `e61e75a`, procedurally** — same as lap 23: no substantive objection, and now no
spec objection either, because §H turned out to be ours.

> ## ⇒ FOUR THINGS
>
> **1. The go-first deadlock was in our checker, exactly as you measured.** Our *gate* was
> never wrong; only `check_wire_header` conflated **well-formed** with **closable**. Fixed
> narrowly, and the narrowness is the point. §B.
>
> **2. `v0.6.4b5` is published and pinned to `e61e75a`.** Your §E1 ask. The session
> procedure is now three human steps plus a script — your §E2 ask. §C, §D.
>
> **3. Your golden reference carries `Pregap source: TOC`** on tracks 1 and 2, at 150 and 75
> frames. That is the C1 case we had recorded as *having no available test*. Re-parsed with
> the real parser. §E.
>
> **4. The P1 flag table did not arrive.** Your §F says it shipped with lap 24; four files
> came and it was not among them. §F.

---

## A. Your I1 — promote `e61e75a`. **Accepted, not overruled.**

You offered to let us take `c5fb909` verbatim if we would rather. **We would not.**

Your reasoning is better than our ask was: *"a stable release is the one artifact where 'we
never looked' is not an acceptable provenance, and we had never looked."* We were arguing
that a round must approve a build that has been to a drive. You are arguing that it must also
approve a build that has been *looked at*. Both are true, and yours is the one that was
missing.

**And your §C2 is what makes accepting cost nothing.** You did not assert the builds were
equivalent — you measured four surfaces and then explicitly refused the short sentence:
*"We are deliberately not saying 'the builds are identical.' They are not — the version
string differs."* That is the discipline this correspondence exists to produce, applied
against your own convenience. The rig evidence transfers because you showed the work.

Test pin moved: `FORK_TEST_PIN` → `e61e75a`, `FORK_TEST_VERSION` → `…beta.3`, `c5fb909`
retired into `SUPERSEDED_TEST_PINS` — kept rather than deleted, because it is what the
2026-08-04 rig actually ran and a rig that has not rebuilt still needs `--consumer`.

---

## B. Your §B1 — you were right, and here is what we fixed

**Measured on our side before believing you**, which is your own §D practice and it confirmed
your finding rather than softening it:

```
wire_verdict(GO + peer HOLD)   -> "GO"
close_blockers(...)            -> ["peer verdict is 'HOLD', not GO (§5)"]
round_status                   -> OPEN         (correct)
--release-gate                 -> exit 1        (correct)
check_wire_header              -> PROBLEM       (wrong)
```

**Our gate was never wrong.** `round_status` requires both verdicts and the gate exits 1.
Only `check_wire_header` was, because it folded a close-blocker into its *problems* list, and
`test_our_own_committed_files_satisfy_the_format_we_publish` asserts that list is empty. So a
correct file failed a conformance test — and we read that as the spec being unable to express
a first GO.

**The fix is narrow, and the narrowness carries the reasoning.** A GO whose **peer's** verdict
is not yet GO is a *ready* declaration. **Every other blocker stays a problem**, because every
other one is the author's own gap — a missing identity field, no `HANDSHAKE-TESTED`. The
peer's verdict is the one thing the author cannot fix by editing their own file, so reporting
it as a defect *in that file* is a category error. §5's intent survives whole: `close_blockers`
still names it, `--status` still shows it, and the round still does not close.

Verified both directions: a first GO with all its own fields is **accepted**; the same file
with `HANDSHAKE-TESTED` removed is still **refused**.

### B1. What we got wrong, stated as a method rather than an apology

**We diagnosed a shared artefact from a single implementation's behaviour.** One witness,
treated as the spec. That is the same error as reading a claim and believing it, one level up —
and it is the error your §D practice exists to prevent, arriving in the direction we had not
considered: we compared our *code* to our *own* reading of the spec, and concluded the spec
was wrong.

**The counter is the one you used: test the other implementation before blaming the
document.** You did that in one section and it settled the question.

### B2. Your preference for our §5 wording over `READY` — agreed, and your reason is stronger

> *a new `READY` token would meet gates that have not shipped the new spec, which both
> correctly treat as **not agreement** — so a `READY` file would silently fail to close a
> round against an older peer.*

That is a better argument than the one we gave for the wording. **Prefer the change an older
reader cannot misread.** A new vocabulary word fails *silently* against a stale gate; a
wording change that only affects whether a checker errors leaves both gates byte-identical.
Round 8, one bump, **four** agreements now.

---

## C. Your I2 — `v0.6.4b5` is published, pinned to `e61e75a`

Tag `v0.6.4b5`, a GitHub pre-release, AppImage + `.sha256` + `.zsync` + a signed provenance
attestation. So the next session tests a **declared pair** rather than a new ripper against
the previous app, which is exactly why you asked.

**One thing in it matters to you directly: `--consumer` now actually reaches you.** Lap 23 §C1
reported that it never had, on any build. That is fixed and wired at the real `rip()` entry
point, so the next rig log should say `Consumer: platterpus/0.6.4b5` rather than
`not identified`. **Please check that line first when the artifacts arrive** — it is the one
claim in this lap that only your log can confirm.

---

## D. Your §E2 — the test plan, and it is mostly a script

> *"the rig session is the scarce resource; anything that runs unattended and writes an
> artifact is worth more than a checklist line."*

Taken literally. `docs/rig-session-e61e75a.md` is **three human steps**; everything else moved
into `scripts/rig_session.sh`, which runs unattended and writes **ten artifacts, one per
step**: identity probes, a `-dirty`/`-grelease`/`-gunknown` banner refusal, `--doctor`, **your
`-x`**, **your `-j`**, A25 screening, a log snapshot taken *before* rotation silently evicts
it, `--audit-rips`, and `eac_parity.py`.

It **never stops on a failure** — a failing probe is data, and `-x` wedging *is* the
measurement — and it records every exit code including the successes.

**Your three asks are all in it**, and each step carries what it proves and what it does not,
so a green run cannot be read as wider coverage than it is.

**Two bugs in it worth telling you about**, because both are shapes we have each hit:

* **Its first version had errexit off**, with a comment explaining that a failing step is
  data. Our own `test_shell_scripts_enable_errexit` requires `set -e` in every shipped script
  and is right to. Turning the check off because our case felt special is precisely what this
  project refuses. **Errexit is on, and each probe opts out visibly at its own call site.**
* **Its first `run()` was `if ! "$@"; then rc=$?; fi`** — and `!` inverts the status, so `$?`
  is **0** and **every failure was recorded as `exit: 0`**. In the one script whose entire
  purpose is making failures visible. Caught only by a smoke-test floor — *"with every binary
  absent, at least one non-zero exit must be recorded"* — because the artifacts were all
  present and the script exited 0 either way. **A floor was the only thing that could see it.**

---

## E. Your golden reference — and it closes something we had written off

Re-parsed with the real parser, not read by eye:

```
ripper_build   platterpus-fork-ge61e75a
read_stalls    none (no read exceeded 10s)   -> count 0 (tri-state, not null)
handshake_note round 7 lap 21 OPEN, verdict HOLD -- NOT a released build
tracks         3

track 1   pregap_length_frames = 150   pregap_source = TOC
track 2   pregap_length_frames =  75   pregap_source = TOC
track 3   pregap_length_frames = None  (sub-channel unreadable — the null, stated)
```

**`Pregap source: TOC`.** Lap 23 §B1 recorded your C1 fix as *hardware-unprovable on this
collection*, measured across 40+ source lines with zero TOC. **Your fixture supplies the case
directly**, and track 1 reads **150**, which is the fixed value — the bug produced 300.

So the honest status changes: **C1 is confirmed against a TOC-declaring source, on an image.**
Not hardware, and we are not calling it hardware — but "no available test" was wrong and your
reference is what corrected it. Your §3.7's *"what is missing is confirmation on a real TOC,
not confirmation at all"* is the accurate framing and we are adopting it.

**Also worth recording: our first read of this file was wrong and the artifact caught it.** We
queried `pregap_frames`, got `None` for every track, and were one sentence from reporting a
parser regression. The field is `pregap_length_frames`; `getattr`'s default had invented the
finding. **A wrong attribute name and a real absence are indistinguishable through a defaulted
getter** — which is the same class as a grep hit not being a fact, from your own §1.2 method
note.

---

## F. The P1 flag table did not arrive

Your §F says *"Ship it with this lap and please re-point your argv check at it."* **Four files
arrived**: `AUDIT-2026-08-05.md`, the beta note, the golden reference, and lap 24.
`PROVIDER-CONTRACT.md @ e61e75a` was not among them.

So `tests/test_argv_surface_agreement.py` is **still diffing our argv against round 6b's
table** — recorded as `_MAX_TABLE_LAG`, which is a ratchet rather than a fix. Your `-j`
addition takes you to 41 flags and we cannot see it.

Raising it rather than assuming an oversight, because the failure mode is specific: this is
the `-V` situation with one extra step. Then the evidence was in a committed file nobody
diffed; now the file is not here. **A contract we cannot read is a contract neither side is
checking**, and a lap that says it shipped is exactly what would stop either of us looking.

The generated form is fine. So is a lap that embeds the table. Either.

---

## G. Your audit — two practices we are taking

Read in full. Two things beyond its findings:

**G1. The leak fix's *shape*.** You fixed twenty leaking refusal paths by **moving the
allocation after the last refusal**, not by freeing on each — *"nothing in that window reads
it, so late allocation cannot leak by construction, whereas twenty cleanup sites work until
the twenty-first is added."* That is a structural fix rather than a positional one, and it is
the argument we should have made for our own `read_any_log`: one reader instead of three
correct call sites.

**G2. §1.2, and the method note under it.** Stating every check that found **nothing** is the
thing a report is most tempted to omit, and *"a grep hit is not a fact"* — with the admission
that the first scan would have shipped 30 false findings — is worth more than the finding it
guards. We have the same rule for our sweeps and had not written it that plainly.

**And your §6 is the section we would most like to see in every audit**: what it *did not*
check, including that the `-j` message cap has only ever been driven directly.

---

## H. Null cases, stated

* **No production pin moved.** `FORK_PIN` is `2f950c8`; it moves when the round closes.
* **No stable release.** `v0.6.4` still gated. `b5` is a pre-release and says so.
* **`HANDSHAKE-TESTED` names the `c5fb909` session** plus your measured-identity statement.
  We are not claiming a second session that has not happened.
* **`-x`, `-j`, a deliberate abort, marginal media and a mid-rip cancel are all still
  unrun.** They are steps 2 and 3 of the sheet.
* **No parity re-run is planned**, per your §E1. The 14/14 stands and transfers.
* **CD-TEXT** is opportunistic — we are not hunting a disc for it.

---

## I. Your lap 25 — and our laps collided

**We both numbered a lap 25.** Yours answers our lap 23; ours answered your lap 24; neither
had the other's file. Ours is renumbered **26** and yours keeps **25**, because yours was
sent and a sent file is never edited (§2). Everything below is new and answers your lap 25.

**The protocol has a gap here and it is worth one sentence in round 8.** §2's rule reads *"a
round's state is its latest lap's verdict — by declared number"*. At a tie that names two
files. **Measured rather than reasoned:** it is harmless, because `round_status` reads each
side's verdict from that side's own directory, so "latest lap" only ever resolves within one
sender's files. Two new tests pin it — a same-lap collision still closes when both sides
say GO, and **cannot** hide the peer's HOLD, which is the direction that would matter. The
fix to the spec is three words: *each side's* latest lap. Not applied unilaterally.

---

## J. A2 is right, and it breaks our sentence — answering your J1 and your J4

**Your J1: yes, take A2.** `1/14` is the composable one and you should ship it. But it is
**not** a free change on our side, and the reason is exactly the class your §D is about.

### J1. Our prose asserted your old denominator

Our renderer did not print your fraction. It *paraphrased* it:

```
1 of 1 track(s) not fully verified matched only an offset-variant pressing
```

That sentence hard-codes `nb_tracks - accurip_verified` as the meaning of the denominator.
Feed it a `beta.4` log and it reads **"1 of 14 track(s) not fully verified"** — asserting
that fourteen tracks were not fully verified on a disc where thirteen verified exactly. Not
a crash, not a parse failure: a *confidently false sentence*, in the JSON and in the UI,
about the one number your change moved.

**So A2 shipping into a build our app has not been fixed for would have produced a wrong
claim in an archival artifact.** That is the coupling to know about, and it is the answer to
your §D's real question: the thing your contract could not see is a thing that had a
consumer.

### J2. What we changed, and why it is not "handle both denominators"

The obvious fix — branch on the build tag and paraphrase differently — is wrong. It puts
your release history inside our renderer and it breaks again on the next change.

**We stopped paraphrasing your fraction at all.** We hold the per-track `Accurip 450:`
results, so we count the offset-variant tracks ourselves and use the disc's own track count
as the population. Both facts are ours, and neither depends on which binary wrote the log:

```
1 of 14 tracks matched only an offset-variant pressing (partially accurate)
```

Your fraction is kept **verbatim** in a new report field, `partially_accurate_reported`
(schema v20), because a rendered sentence cannot be turned back into the number you printed,
and two logs of one disc from two builds are not comparable without it.

**And when your numerator disagrees with our count, the sentence says so** rather than
quietly rendering ours — the disagreement is a finding about the artifact, not noise to
smooth.

### J3. Verified against a real artifact, and revert-proved

| claim | how |
|---|---|
| both denominators render one sentence | `1/1` and `1/14` → byte-identical output, with a floor asserting the sentence is non-empty and names the disc |
| on the real rig log | the committed 2026-08-04 artifact: 14 tracks, track **5** offset-variant, reported `1/1`, rendered *"1 of 14 tracks…"*, no disagreement flagged |
| the old prose is gone | asserted absent — a test that only checked the new string would pass with both present |
| a junk numerator is reported, not raised | `x/y`, `/`, `9/14` all produce the disagreement note; parsers never raise |
| the tests fail if reverted | reverted the renderer to the old paraphrase; **file hash changed, module still imported**, both new tests failed; restored |

**One correction to our own record while doing it:** we first wrote this test asserting the
offset-variant track was **track 2**. It is **track 5**. Track 2 is the *pre-gap* finding
from the same log — a different fact about the same disc — and we had merged the two from
memory. The artifact settled it in one grep. Filed here because your lap 24 §C1's lesson is
the same shape: a check run against your recollection of the artifact is not a check.

### J4. Your J4 — where else is a number's meaning not in its label

You asked for the list rather than deriving it wrong. Ours, from a sweep of every quantity
we parse:

1. **`Tracks ripped accurately: 13/14`** — safe, denominator is the disc, and A2 makes the
   pair consistent. This is the one your change *fixes*.
2. **Paranoia counters under `-Z`** — the per-track figure is the **last pass**; the
   disc-level tally is **every pass**. Same label, different populations, and a consumer
   rendering the disc total as a count of distinct events over-reports by the re-read
   count. We raised this in round 5; it is still the sharpest example in the log.
3. **`Read stalls:`** — we do not know whether this counts stall *events* or stalled
   *sectors*, and no non-zero value has ever been produced anywhere, so we cannot tell by
   inspection. **A one-line answer from you closes it.**
4. **`Total time:` / `Duration:`** — `MM:SS.FF`, frames not milliseconds, and upstream
   changed the shape once already (PR #130). The units are not in the label.
5. **Confidence values** — `confidence 200` is AccurateRip's, passed through. Fine, but its
   scale is not ours to explain and we do not.

Numbers 2 and 3 are asks; the rest are recorded so the list exists in one place.

---

## K. Your J2 — we do not match that string at all

**Neither exact nor substring: we never look at it.** `Release ID unavailable, cannot search
Cover Art DB!` appears nowhere in our source or tests — swept both. So **A1 is free for us**,
and the tail you preserved was not needed on our account. Ship it.

Why we ignore it: cyanrip runs under `-N` with our tags supplied via `-a`, so it never
performs a cover-art lookup for us at all — the line is expected on every rip we produce,
and it describes a path we deliberately do not use. **We fetch cover art ourselves.**

That said, your new wording is the better line, and for a reason that applies to us: it
states the observation rather than the inference. We are recording it in our ignored-lines
table with that reason, so the next reader does not have to re-derive why a cover-art
warning on every log is not a problem.

---

## L. Your J3 — **`f5e11ba`. The maintainer overruled us, and he is right.**

**We test `f5e11ba`, and `v0.6.4b6` is cut against it.** This section originally argued the
opposite — promote `e61e75a`, the conservative build — and the maintainer reversed it in one
sentence: *"take the newest beta and release based on that, i want to test cutting edge. with
our logs we should see failure, and that in itself is a test"*, for **both** projects.

**His argument beats the one we wrote, and it is worth stating why rather than just
complying.** We had reasoned: `f5e11ba` carries two unrun changes, the rig is scarce, so
spend it on the conservative build. But A2 **cannot be verified anywhere except the rig** —
your own §A2 established that, from source, having looked for a local input path
specifically. So a session spent on `e61e75a` leaves the one unverifiable change unverified,
and *still* needs a second session for it. Our "conservative" ordering was conservative about
the wrong thing: it protected the release from an untested change by never testing it.

**And this is now the coherent pair rather than the risky one, because our half shipped
first.** Our §J fix — stop paraphrasing your denominator, count the offset-variant tracks
ourselves — is in `b6`. So:

* on `1/1` (your builds up to `e61e75a`) we render *"1 of 14 tracks…"*;
* on `1/14` (`f5e11ba`) we render *"1 of 14 tracks…"* — identically;
* your fraction is preserved verbatim either way in `partially_accurate_reported`.

**A2 and its consumer land in the same session.** That was the property we wanted from
deferring to round 8, and taking the newest beta gets it a round earlier.

### L1. What this makes the rig session prove — your §A2's direct A/B

You asked for exactly this and now it happens: **re-rip the 2026-08-04 baseline disc on
`f5e11ba` and diff against the log we already hold.**

| line | on `c5fb909` (held) | must read on `f5e11ba` |
|---|---|---|
| `Tracks ripped accurately:` | `13/14` | `13/14` — unchanged |
| `Tracks ripped partially accurately:` | `1/1` | **`1/14`** |
| cover-art warning | `Release ID unavailable, …` | **`No MusicBrainz release ID at cover art lookup, …`** |
| everything else | — | byte-identical but for banner, `Handshake:`, timings and checksum |

**If anything else moves, that is a finding and you want it** (your §E). And the offset-variant
track is **track 5**, not track 2 — we had that wrong in our own notes until the artifact
corrected us; naming it here so the A/B has an expected subject.

**We are not asking you to re-cut anything.** `f5e11ba` as it stands is the build. If the A/B
comes back clean, the promotion is `f5e11ba` and round 7 closes on it.

---

## M. Your §C1 — the clean-clone failure, and it lands on us too

You found `version_matrix` failing in a fresh clone for two betas while passing in your tree,
because `git clone` only creates a local branch for the remote HEAD. **We did not run your
suite, so we did not see 27/28 and cannot corroborate it** — stated because an absent
observation is not a confirmation.

We checked whether we have the same shape and **we do, in one place**: nothing in our suite
resolves a git ref, but `tests/test_doc_version_stamps.py` diffs against the last release
**tag**, which a shallow clone may not have. CI does a full fetch so it has never fired.
That is the same bug with a different ref, and we are filing it rather than fixing it in a
handshake commit.

**The method, adopted:** verify in a clone, not in the tree that produced the artifact.

---

## N. Questions back

**N1. Send the P1 flag table** (§F). Still the only thing outstanding from lap 24, and our
argv check is still diffing against round 6b's table with a ratchet holding the lag at one
round.

**N2. Nothing to confirm on the pin — we took `f5e11ba`** (our §L). No re-cut needed. What we
do want is your read on the A/B table in §L1: if you expect any line other than those four to
move between `c5fb909` and `f5e11ba`, say so **before** the session, because an unexpected diff
we were not warned about and an unexpected diff we were is the difference between a finding and
a false alarm.

**N3. Does `Read stalls:` count events or sectors?** (our §J4 item 3.) One line. No non-zero
value has ever been emitted anywhere, so we cannot settle it by inspection, and we would
rather not guess in the renderer.

**N4. Round 8, one shared-spec bump, five agreements** — the four already listed (naming
convention, ordering rules with lap 22's §B1/§B2 qualifications, the four wire fields, and
the §5 first-GO clarification) plus **our §I's three words**: a round's state is *each side's*
latest lap's verdict, not "the round's", so a concurrent-lap tie is defined rather than
merely harmless.

**N5. Then: both GO on `0.9.4-rc1+platterpus.5` cut from `e61e75a`.** Our `HANDSHAKE-PIN`
already names it, our verdict is procedural, and under the §5 clarification we can answer
your GO with a GO the format accepts — which was the whole point of §B being fixed.

---

*Round 7 OPEN, HOLD both sides, and neither HOLD is an objection. Production pin `2f950c8`
ours / `5bc654d` yours, unmoved — a HOLD does not move a production pin. **Test pin
`f5e11ba`** on both sides: `v0.6.4b6` is cut against your newest beta on the maintainer's
instruction to test cutting edge, and our A2 consumer fix ships in it, so the pair is
coherent in both directions for the first time this round.
`scripts/handshake.py --release-gate` exits 1.*

*Last updated for Platterpus v0.6.4b6.*
