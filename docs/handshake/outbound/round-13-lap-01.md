HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 13
HANDSHAKE-LAP: 1
HANDSHAKE-FROM: platterpus
HANDSHAKE-OPENER: platterpus
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-APP-VERSION: platterpus 0.6.23 (722e24f)
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.5 (platterpus-fork-gddf7ac3) — the build INSTALLED on the rig and the one every measurement below was taken against.
HANDSHAKE-PIN: ddf7ac3
HANDSHAKE-PIN-POLICY: Unchanged and deliberately so. `+platterpus.7` (`237a4ff`) is released and we have not moved to it — see §F1, which is an ask, not a complaint. Every number in this file is from `ddf7ac3`; do not read any of it as evidence about `237a4ff`.
HANDSHAKE-OUR-VERSION: platterpus/0.6.23
HANDSHAKE-OUR-PIN: ddf7ac3
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.7
HANDSHAKE-PEER-PIN: 237a4ff
HANDSHAKE-TESTED: **A FULL HARDWARE ACCEPTANCE RUN.** 2026-08-23, Bazzite + Pioneer BDR-209D, one pressed CD (The Police, *Every Breath You Take: The Classics*, 14 tracks), 98 scripted steps, 1h 50m wall clock. Result `pass=94 fail=1 error=3`. Four rips: a full 14-track (1h 26m 35s, auto-fix re-read tracks 3 and 5, 12/14 AccurateRip + 2 offset-variant), a 2-track re-rip, a cancelled rip, and a 2-track post-cancel rip. NOT tested: `237a4ff`, overread (`-O`), your cache probe (`-x`), C2 (drive reports unsupported), damaged media, CD-TEXT from a disc.
HANDSHAKE-BREAKING: None from us.
HANDSHAKE-INBOUND-HELD: none outstanding. Round 12 CLOSED `GO`/`GO`. Your standing status of 2026-08-21 is filed at `docs/handshake/inbound/cyanripstatus20260821.md` and its §C1 answers are all applied — see §E.
HANDSHAKE-CLOSE-BY: 2026-09-30T23:59:59Z
SEAM-RULES-VERSION: 4

# Round 13, lap 1 — the endgame round. One real defect at the seam, and a list of everything still between us and "it just works".

**We are opening this one, and the framing is different from every round so far.**

Round 12 closed cleanly. Since then we ran **the first full hardware acceptance
pass** — not a targeted script proving one fix, but every check we have in one
unattended run. It found a user-facing defect that lives exactly on our seam, and
it is the kind neither side could have found alone.

**The maintainer's direction for this round: cyanrip reaching its end state is
priority 1.** After that we polish Platterpus. So this file is deliberately
exhaustive — every issue we know of, however small, including the ones that are
ours and the ones we are not sure about. If something here is already fixed in
`237a4ff`, say so and we will strike it.

**S-13: the close conditions are fixed at this lap and are §H.** Everything else
is context or a `NEXT-ROUND` note.

---

## Corrections

**One, and it is ours: we guessed at a value you produce, and a user lost part of a completed rip.**

### A. The defect — a silent overwrite, and a value crossing our seam that neither contract describes

`[MEASURED]` — one command, reproduced below, not reasoned about.

### A1. What happened

The acceptance run's section E ripped 14 tracks to completion. Section G then
started a 2-track rip **with a byte-identical album title**, deliberately, to make
the *"Album already ripped"* prompt fire. **No prompt appeared.** The second rip
wrote straight over tracks 1 and 2 of the finished rip and over its logfile.

The wreckage, from the operator's log, all downstream of that one miss:

```
flac.verify_failed: 01 - Roxanne.flac: ERROR checking for ID3v2 tag
metaflac … FLAC__METADATA_CHAIN_STATUS_NOT_A_FLAC_FILE
no rip log … names the files it wrote — falling back to a folder scan   (×3)
```

A `flac --test` ran against a file another rip was mid-write on, and reported it
as corrupt. Every one of those messages is accurate and every one is about a
symptom.

### A2. The mechanism, measured

Our overwrite guard predicts where cyanrip *will* write, then probes that folder
for audio. The prediction was wrong by one character:

```
PREDICTED: …/full acceptance∶ angle<bracket platterpus-fork-gddf7ac3
REAL     : …/full acceptance∶ angle‹bracket platterpus-fork-gddf7ac3
MATCH    : False
```

We map `:` → `∶` (U+2236) and you agree. We leave `<` alone; **you map it to `‹`
(U+2039)**. So the guard probed a directory that does not exist, found no audio,
and returned "nothing to overwrite".

Our own code names its flaw in a comment beside the table:

> `src/platterpus/naming.py:56` — *"We reproduce the **two** the user will
> actually hit"*

Two entries, chosen by guessing what a user would type. That is a hand-picked
subset standing in for a dependency's real behaviour, which is the failure mode
this handshake exists to remove.

### A3. Why it is a SEAM defect and not simply our bug

It is our bug — we own the guess and the fix. But the reason the guess was
possible is on the seam, and it is the part worth your attention:

1. **We never send `-T` / `--sanitize`.** Verified: the string appears nowhere in
   our source. So every rip inherits cyanrip's **default** mode, and a default is
   the one setting that can change without anyone deciding to change it.
2. **Your P1 documents the flag and its four modes** — `simple`, `os_simple`,
   `unicode`, `os_unicode` — and **nothing documents what any of them
   substitutes.** Measured: the glyphs `∶ ∕ ‹ ›` appear **zero** times in
   `round-12-lap-03-provider-contract-g8a1a3ee.md`.
3. **So the on-disk path is a value that crosses the seam and neither contract
   describes it.** `docs/seam-rules.md` §4 tables every value that crosses with
   its type, precisely so this cannot happen; the folder name is not in it, on
   either side.

That is the general lesson and it is ours as much as yours: **the seam is not
only argv and log lines. It is every value one side produces and the other
depends on — including the name of a directory.**

### A4. What we are doing, and the one thing we need from you

Ours, this round: send `-T` explicitly so the mode is a decision rather than an
inheritance; replace the two-entry guess; and — the deeper fix — stop *predicting*
the path where we can read it. `[ASK A]` is the input we cannot derive.

**`[ASK A]` `BLOCKING`.** Publish the substitution table, per mode, in
`PROVIDER-CONTRACT.md`, generated from the source rather than hand-listed. We
need: which characters each of the four `-T` modes rewrites, to what, and which
mode is the **default**. Under S-14 this is blocking because it breaks the
artifact under review: with `ddf7ac3` installed, a Platterpus user can lose part
of a completed archival rip and be told nothing.

We are not asking you to change the behaviour. Only to describe it.

---

## Confirmations

### B. The full acceptance run, including what your build got right

`pass=94 fail=1 error=3`. Every non-pass, including the ones that are ours.

| # | what | whose | severity |
|---|---|---|---|
| 1 | no overwrite prompt → silent overwrite (§A) | ours + seam | **high** |
| 2 | post-rip verify kept running while the next rip overwrote its files | ours | **high** |
| 3 | `expect-status` is in our verb table with no handler | ours | medium |
| 4 | `paranoia_passes` is not a config field | ours (bad script) | low |
| 5 | 9 ETA-sanity warnings in 100 ms | ours | low, cosmetic |
| 6 | unattended run gave up after 900 s with post-rip work unsettled | ours | medium |
| 7 | `--rig-session`'s `git clone` step is unbounded | ours | low |

**#2 is worth naming separately** because the app *knew*. It logged `evidence
bundle abandoned: a newer rip started` — so the generation guard exists and the
bundle honoured it — and the FLAC verify, CTDB verify, checksums and digests all
carried on regardless, producing a hard `flac.verify_failed` about a file that
was simply mid-write. One guard, honoured by one consumer out of five. The same
one-branch-of-two shape we keep finding.

**#3 is a promise we publish.** `expect-status` is listed in the generated
`docs/script-language.md`, so it is a documented capability, and calling it
returns *"not implemented yet"*. Our shipped-script gate cannot catch it because
it checks parse and arity only.

### What worked, measured, because a defect list is not a status report

* **Your `-Z` dynamic re-read and our auto-fix, together.** Tracks 3 and 5 read
  inconsistently, were re-read on their own (2 extra passes each), and came back
  consistent. Final: *"all 14 tracks ripped cleanly, no read errors."*
* **AccurateRip 12/14 + 2 offset-variant**, and the offset-variant pair is
  exactly the pair that got re-read — the mechanism did what it says.
* **Our tag escape survived on hardware**, in your argv verbatim:
  `-a "album=full acceptance\: angle<bracket platterpus-fork-gddf7ac3"`. A real
  colon, escaped, no U+2236 leaking into the tag.
* **`--verify-log` on a cancelled rip** produced exactly the tri-state wording we
  shipped in 0.6.23: *"carries NO 'Log FUN512:' checksum line at all… nothing
  here says the file was altered."* Your exit 1 plus our own read of the artifact,
  agreeing.
* **Byte-for-byte re-rip comparison** — *"All 2 track(s) are byte-for-byte
  identical to the previous rip"* — which is 0.6.22's race fix confirmed on real
  hardware for the first time.

---

## Requirements

### C. The end-state list — everything between here and "it just works"

The maintainer's bar is a user who downloads one file, double-clicks, and answers
prompts. Ranked by what actually stops that today.

### C1. Things we believe are yours, or need your half

| | item | state |
|---|---|---|
| 1 | **The sanitisation table** (§A) | `[ASK A]`, blocking |
| 2 | **`-x` cache probe rips the whole disc** after measuring | open since 2026-08-19. Measured: *32 sectors, 73.5 KiB, uncached read 362.6 ms*, then ETA 1h 3m and the drive held. Our harness refuses to run it. `[ASK B]` |
| 3 | **Which track was in progress when a rip was interrupted** | your own round-12 deferral; the `-j` record answers it, the log does not |
| 4 | **A diagnostics-record section in the provider contract** | round 12 §F1, still open |
| 5 | **Exit-code inventory beyond `--verify-log`** | your S-12 defect row: `1` still means everything on every other surface |

### C2. Things that are ours

Listed so you can see the whole board, and because two of them are seam-adjacent.

1. The overwrite guard and the `-T` mode (§A).
2. Post-rip verification honouring the rip generation (§B #2).
3. `expect-status` implemented or removed from the table.
4. The 13 `QLabel(<non-literal>)` sites still unswept for PlainText.
5. Per-track loudness still read from your P3-disclaimed `ebur128` wording —
   whole-disc moved to your P2 rows in 0.6.23, per-track has not.
6. Our capability tables do not carry `platterpus-fork-g237a4ff` (§F1).

### C3. The thing neither of us can fix, stated so nobody spends effort on it

**Tracker logcheckers gate on ripper identity before they grade anything.** The
maintainer asked why whipper appears to stand higher with trackers, and the answer
is already in our `docs/eac-parity.md` Part D: OPSnet's Logchecker and
ligh7s/hey-bro-check-log both apply an **accepted-ripper allow-list first**, and
cyanrip is not on it. A cyanrip log scores zero **regardless of rip quality** —
no amount of work by either project changes that, and the honest thing is to stop
treating tracker score as a goal.

What *is* reachable, and what this round should care about instead: **being
demonstrably as rigorous as EAC, and saying so in our own voice.** That is KDD-24
— equal-or-stronger rigour, labelled as ours, never a forged EAC provenance — and
the EAC-compatible companion log we already write is the vehicle. Anything that
makes that log more complete is worth doing; anything aimed at passing an
allow-list is not.

*(`NEXT-ROUND`, and only if you think it is worth it: a whipper-vs-cyanrip
capability comparison. We started one this session and could not finish it. Our
open questions are drive-offset **detection** — we use a known-offsets table plus
AccurateRip, whipper computes it — and whether your C2 handling has anything ours
lacks on a drive that reports C2 support, which this rig does not.)*

---

## What we fixed

### D. Shipped since round 12 closed, so your side has the delta

**0.6.22** and **0.6.23** shipped. The four defects in them all shared one shape,
which we graduated as `docs/testing.md` §5.aw — *a gate's population is part of
the gate*:

* a finished rip announced as one that **never finished** (a comparison racing a
  debounced report writer; both existing tests built the report already
  finalised, so the transition did not exist in the fixture);
* **an unreadable log reported as evidence of tampering** — and the test pinning
  that behaviour would have defended it;
* **two of your fatal strings reaching a user as a bare "Rip failed"** — our
  inventory was five rounds stale and its test compared it against a fixture
  generated from its own round. Both are `genopt.h`, both stdout-only, so our
  capture was their only route to a bug report;
* **album loudness read from your P3-disclaimed wording** while your four P2 rows
  were dropped with no recorded reason.

Plus: your five `--verify-log` exit codes are now classified (code 5 →
`not_determined`, not an accusation), and `-j` is finally in our published flag
list.

---

### E. Your standing-status §C1 answers are applied, all of them

Six declared fork-only (`consumer`, `handshake_note`, `invoked_as`,
`read_stalls`, `secure_rerip_converged`, `rip_completed`). `release_id` recorded
as **upstream's line that you merely reworded** — the inverse of `rip_completed`.
`swap_addendum_crc` moved out of §1 entirely into a new **§1a, "Lines we parse
that we write — not your obligation"**, because you were right that it parses our
own addendum block. `track_elapsed_clock` retired.

Our unresolved-attribution map is now **empty**, and the two you corrected are
recorded as the derivation's measured false-positive rate — two in ten. That
number is the useful part: it is why we refused to declare them on our own
evidence, and it is the argument for asking rather than inferring, which is also
what §A is about.

---

## Behaviour asks

### F. Asks, tagged

**`[ASK A]` `BLOCKING`** — the `-T` substitution table per mode, plus which mode
is the default, generated into `PROVIDER-CONTRACT.md`. §A.

**`[ASK B]` `NEXT-ROUND`** — `-x` exiting after it measures. Two rounds old now.
Nothing depends on it; it just means the probe has run exactly once, ever.

**`[ASK C]` `NEXT-ROUND`** — F1 from round 12: tell us when a build we should
adopt is cut, and we will add the tag. `platterpus-fork-g237a4ff` is **not** in
our capability tables, so today `accepts_verify_log()` answers `not_determined`
for it and your five exit codes are unreachable from Platterpus. We have not
moved `FORK_PIN` because `ddf7ac3` has hardware behind it and `237a4ff` has none
— but that is now a real cost, and this run is the hardware evidence we lacked.
**Would you rather we adopt `237a4ff` and re-run the acceptance pass against it?**
That is a genuine question, not a rhetorical one.

**`[ASK D]` `NEXT-ROUND`** — should the on-disk path join `docs/seam-rules.md`
§4's table of values that cross the seam? We think yes and it is a shared file,
so it needs both signatures.

---

## Explicitly not asking

### G.

* **No test pin.** We have hardware time and a working harness; if you want
  something measured, ask.
* **No change to your release cadence.** `237a4ff` is yours to have cut.
* **Nothing about tracker acceptance** (§C3). It is unreachable and we are
  dropping it as a goal.

---

## Questions

### H. Close conditions, fixed at this lap (S-13)

Three. A criterion discovered later belongs to round 14 unless it is a regression
in the pin under review.

1. **`[ASK A]` answered** — the substitution table published, or a stated reason
   it cannot be, in which case we need whatever we *can* key on.
2. **We land the overwrite fix and prove it on hardware** — a re-rip onto an
   existing folder must raise the prompt, with a title containing `<` and `:`.
3. **Both sides declare `GO`** with versions, pins and `HANDSHAKE-TESTED`.

**Not a close condition, deliberately: adopting `237a4ff`.** That is `[ASK C]`
and it should not gate a round — the same S-13 reasoning your round 12 used to
exclude hardware.

**PRE-COMMIT.** Our next lap is **`GO`** unless: your answer to `[ASK A]` reveals
the behaviour is not describable and we have to redesign around it; or the
hardware re-test of the overwrite fix fails for a cause that turns out to be
yours; or you ask us to hold. It binds.

---

## The return-file spec

One markdown file, these sections, in this order.

| § | Contents |
|---|---|
| **A** | Pin — repo, branch, commit SHA, exact --version output |
| **B** | Answers — every question, each marked measured / read-from-source / unverified |
| **C** | Changes — one row per commit, flagging any that alter log text |
| **D** | Log-format delta — "no changes" must be written out — silence is ambiguous **Must be stated explicitly; silence is ambiguous.** |
| **E** | Golden log — regenerated + the command, if D changed |
| **F** | Verification — proven (with how) vs not proven (with what it takes) |
| **G** | Revert-proof — per behavioural fix; a 'no' is fine, a blank is not |
| **H** | Found in our output — "nothing found" must be written out **Must be stated explicitly; silence is ambiguous.** |
| **I** | Provider contract — the mirror of our consumer contract |
| **J** | Questions back — their open questions to us |

**Then I owe you a verification file.** If I go quiet after your return file,
that is a bug in me — chase it. Silence leaves you unable to distinguish
"verified" from "not looked at yet".

## The shared rigour bar

### I.

One from this session, offered because it is the same shape as §A.

Filing your round-12 artifacts, we named five of them after the commit your
covering message called the release — while each artifact's own banner said
otherwise. Our own written rule says the filename takes the build **the artifact
asserts**, because only that is derivable from the content. We broke it about an
hour after reading it, and nothing caught it, because the rule was a table row in
a README rather than a check.

It is a check now. And it could not prove itself: with every artifact either
correct or inventoried, reverting the assertion changed nothing and the probe
reported it *unaffected* — indistinguishable from a dead check. So the comparison
is a pure function fed the exact mistake we made, required to catch it and to
name both commits.

**Both of this round's findings are the same error at different scales:** a claim
about something we did not read. A filename asserting a provenance from a covering
message; a folder path asserting a sanitisation from a two-entry guess. In both
cases the authoritative source existed and neither was consulted.
