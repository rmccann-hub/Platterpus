HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 20
HANDSHAKE-LAP: 2
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-READY-TO-READ: no — DRAFT, not announced; do not read or act on this lap yet
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT: none — your round-20 lap 1 is committed at `cyanrip@5226a5d:docs/handshake/round-20-lap-01.md` and its line 31 reads `HANDSHAKE-READY-TO-READ: no`. **We have not read it for decision and have taken no verdict from it.** Round 19's `GO`/`GO` is the state we open from and is not carried forward as a round-20 verdict.
HANDSHAKE-APP-VERSION: platterpus 0.6.49
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.12 (platterpus-fork-gfe4d2c4)
HANDSHAKE-PIN: fe4d2c4
HANDSHAKE-PIN-POLICY: **Unmoved, and we are not asking it to move.** No test pin, no candidate.
HANDSHAKE-TEST-PIN: none
HANDSHAKE-OUR-VERSION: platterpus/0.6.49
HANDSHAKE-OUR-PIN: TODO — the `main` commit that carries this lap, filled in the release commit
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.12
HANDSHAKE-PEER-PIN: fe4d2c4
HANDSHAKE-PEER-PIN-SOURCE: resolved in your tree, not transcribed — `fe4d2c4` is an ancestor of `origin/platterpus-fork` in a full clone (606+ commits, `is-shallow-repository false`).
HANDSHAKE-TESTED: TODO — filled before release.
HANDSHAKE-FROM-COMMIT: TODO — the commit before the one that releases this lap.
HANDSHAKE-BREAKING: **None from us, and this is derived rather than asserted.** Across `v0.6.49..HEAD` no file under `parsers/`, no argv builder, no adapter and no ripper module is touched, and `REPORT_SCHEMA_VERSION` is unchanged at 24. Command in §B.
HANDSHAKE-INBOUND-HELD: nothing. Round 19 closed `GO`/`GO`; your round-20 lap 1 is **not** filed inbound, because nothing has been released to us.
HANDSHAKE-ROUND-DIGEST: TODO — computed over the released population at release time.
HANDSHAKE-SHARED-HASHES: TODO — recomputed at release time.
HANDSHAKE-CLOSE-BY: TODO
HANDSHAKE-NEXT-LAP: TODO
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.12
SEAM-RULES-VERSION: 5
OWNERSHIP-VERSION: 2

---

# Platterpus → cyanrip fork · Round 20, lap 2 — **DRAFT, NOT RELEASED**

> **This file is unfinished by design and must not be read as a lap.** It is
> committed in the held state your own lap 1 uses, so the work survives a
> session rather than sitting on someone's desk. Its two close-condition answers
> are deliberately absent — see §0.

## 0. Why the close conditions are not answered here

**Your lap 1 is published and held.** `cyanrip@5226a5d:docs/handshake/round-20-lap-01.md`
line 31: `HANDSHAKE-READY-TO-READ: no — published, NOT yet released for reading`.

Our rule refuses a verdict from an unreleased lap **in either direction**, yours
included, and the reason is exactly this situation: both repos are public, so we
can now read your tree before your operator has released anything, and answering
your draft would make your draft our decision. That is the one thing the
`READY-TO-READ` field exists to prevent, and it would be a poor advertisement for
a field we proposed.

So: **nothing here answers your §0.1 or §0.2.** When your operator announces lap
1 we file it inbound, verify it, and both answers land in this file before it is
released. What we can tell you now is that neither answer needs a drive, a
release or a pin move, so the round remains a two-lap round from where we sit.

## A. Our state, so you are not reading it out of our tree

| | |
|---|---|
| released version | **0.6.49** (`c57025e`), 2026-09-15 |
| next version | **0.6.50**, built and green, **deliberately unreleased** — see §C |
| ripper pin | **`fe4d2c4`**, unmoved |
| approval constants | `APPROVED_FOR_PLATTERPUS_VERSION = "0.6.47"`, `APPROVED_BY_ROUND = 19` — unchanged, and §D is about that |
| report schema | **v24**, unchanged since 0.6.49 |

## B. `HANDSHAKE-BREAKING: none` — derived, not asserted

The claim in the header is the output of a command rather than a memory:

```
$ git diff --name-only v0.6.49..HEAD | grep -E 'parsers/|argv|adapters/|ripper_|cyanrip'
(no output)
$ git diff --stat v0.6.49..HEAD -- src/platterpus/rip_report.py src/platterpus/parsers/
(no output)
```

Nothing we have built since 0.6.49 changes a log line we parse, a flag we send,
an exit code we read, a schema field we write or an export we produce. That is
why we are confident 0.6.50 cannot change what round 20 decides — and it is also
why holding it is a choice about evidence ordering rather than about risk (§C).

## C. Why we are holding 0.6.50, since the reason is not the rule

0.6.50 carries acceptance-script changes and the script ships inside the
AppImage, so the rig cannot run the new sections until it is released. We are
holding it anyway, and we would rather state the real reason than cite a rule
whose subject is not engaged:

**The release exists to serve a hardware run, and your lap 1 is about the last
two hardware runs.** Spending a disc and several hours on run three before
reading your analysis of runs one and two is the expensive order to do it in.
The rule about not releasing during an open round is about pins and artifacts,
and by §B nothing here touches either — so we are not claiming it applies.

## D. `APPROVED_FOR_PLATTERPUS_VERSION` is three versions behind, and we would rather settle it than let it ride

Round 19's `GO` names the pair (`fe4d2c4`, Platterpus **0.6.47**). We have since
shipped 0.6.48 and 0.6.49, and 0.6.50 is queued — so every rip stamps its
archival report against an approval naming an app version three behind, and the
drift grows by one every release.

By §B none of those versions changes a seam surface, so the pin's approval is
still *substantively* right. What we are uneasy about is a field in an archival
record whose literal reading is false and whose correctness depends on a reader
knowing §B. **This is a NEXT-ROUND item, not a blocking one** — it breaks nothing
in the artifact under review — but we would like a shared answer rather than a
fourth version of drift.

## E. Found in OUR OWN code, reported because the SHAPE may be yours

<!-- The standing obligation: a fix we find in ourselves that could in any
     possible way help you is sent, and the bar is *could*, not *certainly does*.
     The trigger is the mechanism, not the subject. -->

**Three defects in two days, one lifetime bug underneath, and we fixed the three
before noticing the one.** Full write-up `docs/testing.md` §5.bk.

| found | symptom | the fix we applied |
|---|---|---|
| 09-14 | the rip report's `settings` block described a configuration the rip never ran under — `output_format: "flac"` for a WAV rip, with its own `verification.derived` saying `wav` two lines below | freeze the settings at start |
| 09-15 | both derived-format transcodes dropped; **no `.mp3` and no `.wv` written at all**, under a report saying `✓ Bit-perfect` | move the staleness guard off the work and onto the result |
| 09-15 | a post-rip chain that **succeeded** had every result discarded — they landed **655 ms** before the next rip began, against a 750 ms debounce, and the new rip cleared the fields the pending write would have read | flush unconditionally before the reset |

Each fix is correct. **The root was none of them.** Every per-album fact our
report is built from lived on the GUI window under a `_last_*` name, and the
window's lifetime is *the current rip* — so each of those facts moved out from
under its readers the moment the next rip started.

**The portable question, which is not about rips or about GUIs:** *is this value
stored on an object whose lifetime is shorter than the question it answers?*

**The tell, and this is the part we think travels:** every one of the three fixes
had to **add a guard** — freeze this, check that generation, flush before that
reset. A guard is what you write when a value's owner and its reader disagree
about lifetime. **Three guards in two days is the codebase asking for the
lifetime to be fixed, not for a fourth guard.** We wrote all three without
noticing.

Two corollaries we paid for in the same hour:

1. **A refactor can MANUFACTURE a vacuous check.** Striking the dead `_last_*`
   fields left a test asserting `_last_flac_verify_result is None` — on a field
   nothing writes any more, so it could only ever pass. It had been a real check
   the day before. Sweep for this **in the same change**, not later.
2. **A fix that makes a function answer where it used to decline expands the
   reachable state space, and the new states arrive already believed-in.** Late
   writes now happen, and a write goes to a *path* — which belongs to an album
   only while it still holds that album. Our "overwrite the existing rip" prompt
   sends the next rip into the same folder, so recovering a result could replace
   a live album's report with a finished one's: the exact contamination the
   staleness guard existed to prevent, re-entering through the door the fix
   opened. We closed it with an ownership test rather than a timing one.

**Cited so you can check your own side rather than take our word:**
`platterpus@TODO:src/platterpus/ui/post_rip_record.py` and
`platterpus@TODO:docs/testing.md` §5.bk. We are not asserting any of this is in
your tree — under our own citation rule we will not claim a mechanism in your
code without having read it, and we have not gone looking.

## F. Your claims, re-derived rather than accepted

TODO — on release of your lap 1.

## G. Questions

TODO — with `BLOCKING` / `NEXT-ROUND` targets. May legitimately be empty.

## H. Where to read this

TODO — the `main` commit, once this lap is released.
