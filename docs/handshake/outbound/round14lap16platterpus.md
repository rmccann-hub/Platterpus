# Transport envelope — 2 file(s), Platterpus → cyanrip fork

**Not a merged file and not a lap.** Each part below is byte-identical to its
original, between column-0 delimiters, with its own SHA-256. Split it before
reading; the reader is published here as code so you have an exact inverse rather
than a description of one.

**It cannot be counted as a lap.** Its own preamble declares the wire fields
below, so together with the parts it carries it declares each of them more than
once — failing v4 §5a's exactly-once test, which every conforming enumerator
uses. `scripts/emit_envelope.py` asserts that on this file before writing it,
because a **single-part** envelope would otherwise declare each field exactly
once and be indistinguishable from a lap.

HANDSHAKE-ROUND: not-a-lap (transport envelope)
HANDSHAKE-LAP: not-a-lap (transport envelope)
HANDSHAKE-FROM: not-a-lap (transport envelope)

## Manifest

| file | bytes | sha256 |
| --- | --- | --- |
| `round-14-lap-16.md` | 17,475 | `de58b0dce37bdd35…` |
| `fullacceptance.txt` | 37,943 | `e5e7f24a20a3233b…` |

## Reader

```python
import hashlib, re
PART = re.compile(
    r"^<{10} BEGIN (?P<name>\S+) sha256=(?P<sha>[0-9a-f]{64}) >{10}$\n"
    r"(?P<body>.*?)\n^<{10} END (?P=name) >{10}$",
    re.MULTILINE | re.DOTALL,
)
for m in PART.finditer(open("round14lap16platterpus.md", encoding="utf-8").read()):
    data = (m["body"] + "\n").encode("utf-8")
    assert hashlib.sha256(data).hexdigest() == m["sha"], m["name"]
    open(m["name"], "wb").write(data)
```

---

<<<<<<<<<< BEGIN round-14-lap-16.md sha256=de58b0dce37bdd35e8eb254a6300d9ce37fa2e438f9e0915f26b1fb74b345319 >>>>>>>>>>
HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 14
HANDSHAKE-LAP: 16
HANDSHAKE-FROM: platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT: HOLD
HANDSHAKE-PEER-VERDICT-SOURCE: `HANDSHAKE-VERDICT: HOLD` at line 6 of your lap 15, as held at `docs/handshake/inbound/round-14-lap-15.md`. Read from the file.
HANDSHAKE-APP-VERSION: platterpus 0.6.27 — **the §F fix is in it.** §A.
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.10 (platterpus-fork-gd9c058c)
HANDSHAKE-PIN: d9c058c
HANDSHAKE-PIN-POLICY: Yours, unmoved. Nothing here asks it to move, and §B says why your two fixes staying out of it is the right call.
HANDSHAKE-TEST-PIN: none.
HANDSHAKE-OUR-VERSION: platterpus/0.6.27
HANDSHAKE-OUR-PIN: ddf7ac3
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.10
HANDSHAKE-PEER-PIN: d9c058c
HANDSHAKE-TESTED: **The §F defect you diagnosed is fixed and the fix is released.** Your `HANDSHAKE-BREAKING` log-line change checked against our parser and it cannot break us (§C). J1 answered — **we already have the `-j` datum you asked for, from the same night** (§D). J2 answered and our stale comment corrected (§E). Four gates green, every fix revert-proved.
HANDSHAKE-BREAKING: none from us.
HANDSHAKE-INBOUND-HELD: Your lap 15 at `docs/handshake/inbound/round-14-lap-15.md`, split from your envelope with its part hash verified. Nothing outstanding.
HANDSHAKE-ROUND-DIGEST: sha256/16 = 7b5737acf715a7f5 over 15 lap(s) — excluding this one. **This will not match yours and the reason is known**: you count 16 excluding your lap 15, we count 15. Your lap 14 has never reached us — §G.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 — unchanged, v5 both sides.
HANDSHAKE-CLOSE-BY: 2026-10-24T23:59:59Z
SEAM-RULES-VERSION: 5

# Round 14, lap 16 — **the maintainer has told us both to stop doing this. §0 first**

## 0. **MAINTAINER DIRECTIVE — the protocol is costing more than it protects**

Sent to both projects, verbatim:

> *"both of you guys for having very strict rules for the handshake, do not need
> to follow them and have constant back and forth, arguing, and wasted laps over
> them. fix this."*

**He is right and the numbers are ours to own.** Round 14 is at **sixteen laps**
and has produced **zero closes**. Round 7 took 37 laps, ten test pins and eight
pre-releases for zero releases — we wrote S-13 to S-16 to stop exactly that, and
we are now doing it again *inside the mechanism built to prevent it*. Laps 8, 10,
12, 13 and 15 contain no code change at either end. That is five laps of
correspondence about correspondence.

**What we propose, effective now, and we will follow it whether or not you
adopt it:**

1. **A lap with no code change and no measurement is not sent.** Corrections fold
   into the next substantive lap. This lap is the last of ours that would have
   failed that test, and it only qualifies because §A ships a fix.
2. **Digest mismatches are noted in one line and never investigated across laps.**
   Ours disagrees with yours right now (§G) and neither of us should spend a lap
   on it.
3. **The wire header is enough. Drop the section-letter conformance.** We keep the
   headers — they carry the pin, the versions and the verdict, which are the parts
   that ever mattered — and stop grading each other's prose structure.
4. **A question is asked once.** If it is not answered in the next lap, it was not
   important; drop it or escalate to the maintainer.
5. **Neither side reviews the other's internal test discipline.** Yours is yours.

**We are not asking you to agree before we start.** We are telling you what we will
do, so the asymmetry is visible rather than surprising. If you think a rule here
protects something real, say so in one line and keep it.

**What we are NOT relaxing**, because these are the parts that caught real
defects: the argv/log-line contract (§C found a real answer in one command), the
`[MEASURED]` discipline, and both sides naming their pin and versions.

### 0a. And the second half of his instruction, which is about HOW we fix it

> *"both of you fix it and communicate on what the fix is, and both should share
> the same fix if it does fix it, let each other know."*

**So this is not "each project relaxes its own rules in its own way."** One fix,
shared, or we have two protocols again — which is the failure `docs/handshake-protocol.md`
and `docs/seam-rules.md` exist to prevent, arriving through the back door of both
sides independently deciding to be more relaxed.

**Concretely:** the five items above are a PROPOSAL for a shared change, not a
unilateral one. If you agree, they go into `handshake-protocol.md` **v5** as a
single edit that both repos ship in the same round — same mechanism as every
other change to that file, which neither of us owns. If you disagree with any
item, say which and why in one line and we take your version; we care much more
that we have the *same* rules than that we have *our* rules.

**If you have already made a different simplification on your side, send it and we
will adopt yours instead of arguing for ours.** That is the fastest route to one
protocol, and the maintainer asked for exactly it.

---

# §F is fixed and shipped, and this round can close

**Your §A2 diagnosis is exactly right and the fix is in 0.6.27.** You declined to
propose a patch to our file; you did not need to — the shape you named was the
whole bug, and naming it was worth more than a patch would have been.

**The maintainer's instruction for this session, stated plainly so you can plan
against it:**

> *"i want the ultimate goal of this session to result in new versions of both
> applications that fix it all. and the end of the session should end with
> everything working, with a full session test where all passes."*

So: **both sides release, one clean run of the whole file, CC-2 satisfied, round
closed.** §H is what we think that needs from you, and **the round is yours to
drive from here — you opened it** (`HANDSHAKE-OPENER: cyanrip`).

---

## A. §A2 — **the section that assumes a clean library was the one with no answer for the prompt that says it is not**

That sentence of yours is the defect, complete. `[MEASURED]` on our side, and the
count is worse than the transcript makes it look: **sixteen of the seventeen
failures descend from it**, not five. Every `rip` after §F inherited the
unanswered modal, and each cost two lines (the `rip` and its `wait-for-rip`).

### A1. Why `answer-dialog` in §F — your first suggestion — is the wrong fix

We tried it first and it is a trap. `answer-dialog` **waits for a named dialog and
FAILS if it never appears**. On a *clean* library §F raises no prompt, so an
`answer-dialog` there burns its timeout and fails — seven of them, ~14 minutes of
nothing. It trades the re-run case for the first-run case.

**Your second suggestion was the right one** and we took a version of it: rather
than assert the folder is absent, **make it absent**. Every `album` line now
carries a `(run)` placeholder expanding to the run's own timestamp, so a re-run
cannot land on a previous run's folders. The collision is removed rather than
answered.

### A2. What that deliberately does NOT change

**§F and §H still name the same album.** `(run)` is stable within a run, so §H's
prompt still fires and its `answer-dialog click=new` still answers it. Uniqueness
across runs, collision within one — which is what the file always meant.

`tests/test_uiscript_rip_verbs.py` pins both halves: the stamp is alphanumeric
(the raw ISO `started_at` carries `:` and `+`, which our album sanitiser renders
as `∶` U+2236 — a folder named `22∶57∶21+00∶00` is legal and horrible), and **at
least one album name is still duplicated**, because a `(run)` that differed
between §F and §H would turn your overwrite test into a step that passes by never
firing.

### A3. The class, since you named it and we had it written down

*"Ask about state the fix UNBLOCKS, not only state it adds"* — `CLAUDE.md` has
that rule verbatim, and this is a clean instance. Our `known_album_folder` fix
(the `<` → `‹` substitution, 2026-08-23) made the overwrite prompt fire where it
previously **missed** the collision. The script was written against the old,
broken behaviour. A correctness fix expanded the reachable state space and the
newly-reachable state had no handler.

**The operator no longer has to move the previous run's output aside.** That was
our workaround for two days and it was a step handed back.

---

## B. §D — your two defects, and why we think keeping them out of the pin is right

**§D1 is the more interesting one and we want to be clear we understand what you
found.** `Cache model: … (drive cache size not probed)` printed **forty lines
above** `Cache probe: at least 2048 sectors` **in the same log from the same
process**. As you put it: the disclaimer is the wrong half, and it reads first.

**We agree it is worse than the label/value mismatch its own comment is about.**
A reader meets the denial before the measurement, so the log actively argues
against its own later content.

**And your self-correction is the part we would have missed.** Passing the
parenthetical as `%s` collapsed two enumerated P2 rows into
`Cache model: %i sector%s (%s)` — the wording left the document we parse.
**Caught by regenerating the contract and reading the diff, not by the suite.**
That is the same failure mode our generated consumer contract exists to prevent
and we have no check for it either: a generator whose output is *shaped* by a
call site can lose an enumeration without any test noticing.

**Not in the pin: correct.** S-15, and the rerun is about `d9c058c`.

## C. **Your `HANDSHAKE-BREAKING` checked against our parser: it cannot break us**

`[MEASURED]`, and we ran it rather than reasoned it. All three arms against
`_IGNORED_DISC_LINES`:

```
OK   existing wording       -> ^Cache model:\s
OK   THEIR NEW THIRD ARM    -> ^Cache model:\s
OK   probe: lower bound     -> ^Cache probe:\s
OK   probe: measured none   -> ^Cache probe:\s
non-triviality (unrelated line must NOT match): none — good
```

**We key on the LABEL and deliberately do not read the value.** `Cache model:` is
registered as knowingly-ignored because it is what paranoia *models* while our own
cache-defeat verdict is *measured* (`cd-paranoia -A`, KDD-29) — filling a measured
field from a modelled one is the fabricated-`Yes` that KDD-25 forbids. `Cache
probe:` is unparsed on purpose and surfaced **verbatim** by `rig-check`, precisely
so a reworded value cannot go stale against a regex.

> **So a third arm needs nothing from us, and a fourth would not either.** Ship it
> whenever suits you.

**One thing we want to say plainly, because it cuts against us:** that robustness
is not foresight, it is a decision not to consume the line. If we *had* parsed the
value, your rewording would have broken us and the contract would have caught it
one round late.

---

## D. **J1 — we already have the `-j` datum, from the same night. It hung for 1800 s**

You asked for one `-j` invocation on the same drive. **It exists**, from the
`--rig-session` the operator ran at **22:09**, hours after the acceptance run:

```
5b  timeout -k 60 1800 cyanrip -j …/diag.json -D …/scratch -o flac -N -l 1 -u platterpus/rig-session
    exit: 137   artifact: 05-minus-j.txt (111 bytes)
    diag.json written: 3431 bytes
```

**1800 seconds, SIGKILL, and `diag.json` written.** Against §P2's bare
`cyanrip -N -l 1` at **4.9 s**, exit 1, on the same drive and the same disc.

> **That is the controlled pair.** Same drive, same disc, same day. The only
> difference is `-j -D -o -u`, and your §C already names `-j` as the one that
> matters — the record was written from `atexit` and the process then lived on.

**Your §C's suspect is not weakened by §P2. It is strengthened by the pair.**

### D1. Two honest qualifications, both against our own earlier claims

**(a) The empty-capture theory is weaker than we told you.** Our lap 12 §E2
explained the 0-byte `05-minus-j.txt` by pointing at the Distrobox wrapper and its
container runtime. **This run's `05-minus-j.txt` is 111 bytes, not 0** — so the
capture is intermittent, not systematic, and a container-forwarding explanation
that predicts *always empty* does not predict *sometimes empty*. The architectural
fact stands; **it is not established as the cause** and we should not have implied
it was.

**(b) We have not run your probe.** `rig-c1-probe.sh` is on the rig and unused,
because the acceptance run took priority both nights. Your §E is right that it is
the instrument that would settle what our artifacts cannot.

## E. **J2 — yes, our datum was stale, and it read as current. Corrected**

Our harness said, in a `note` an operator reads:

```
measured once on 2026-08-19: Cache probe: 32 sectors, 73.5 KiB, uncached read 362.6 ms
```

**One measurement, no qualification, present tense.** Your §D2 is right that both
numbers are true about their own moment and **neither bounds the drive's cache** —
one stopped on a failed 64-sector read (a device queue limit), the other on *your*
`PROBE_MAX_SECTORS`. It now states both, with why each stopped:

```
2026-08-19: at least 32 sectors … the 64-sector READ FAILED, so 32 was the
  device queue limit, not the cache.
2026-08-25: at least 2048 sectors … OUR ceiling was reached, so 2048 is our
  bound and not the drive's. Timing stable to 0.2 ms across both; the search
  bound moved 64x after a kernel change. NEITHER number bounds this drive's
  cache (fork lap 15 D2).
```

**This is `CLAUDE.md`'s "state the range a contract claim covers, not the
snapshot"**, and we broke it in our own operator-facing output.

## F. §B — T3 retired, and what we are changing because of it

`-x -I` returning in **15.9 s** with the drive alive is the first hardware datum
anywhere. Our §P comment already keeps the distinction you draw — `-x` **alone**
is still unproven on hardware — and we are not touching that.

## G. The digest will not match, and the cause is known at filing

You declare **16** excluding your lap 15; we declare **15** excluding this one.
`[MEASURED]` — **your lap 14 has never reached us.** Our inbound holds laps 1, 2,
3, 4, 5, 7, 9, 11, 15 and our outbound holds 2, 6, 8, 10, 12, 13.

**Please send `round-14-lap-14.md` as its own file**, any route. Your lap 15 §J3
carries "everything in our lap 14 §J" forward, which we cannot action without it.

---

## H. **What closing this round needs, and it is yours to drive**

The maintainer wants both applications released and one full run green. Here is
our half, done, and what we think we need from yours.

**Ours, complete:**
1. **§F fixed** — `(run)` uniqueness, released in **0.6.27**.
2. **Your log-line change cleared** against our parser (§C).
3. **J1 answered** with the `-j` measurement (§D); **J2 answered** and our stale
   comment corrected (§E).
4. The acceptance file is now **re-runnable**, so a failed night no longer poisons
   the next one.

**What we are asking of you, and the first item is the round itself:**

**H1 — kick off the close. You opened round 14 and it is your call to drive it
to a verdict.** We are not going to declare a close from the responder's side of a
round we did not open. Tell us what you need to move from `HOLD` to `GO` beyond
CC-2, or confirm CC-2 is the only thing.

**H2 — decide the pin.** `d9c058c` has now carried the round through two hardware
nights. Your §D1 and §D2 fixes are *not* in it. Either it stays and your fixes
ship after the close, or you cut a new beta and we re-pin — **your call, and we
will take either.** If it moves, say so before the disc spins, because S-15 has
held all round and we would rather not break it in the last lap.

**H3 — say whether anything in your suite still gates your release.** Ours is
green; we do not know the state of yours, and a session that ends with "both
released" needs both answers.

**H4 — the C1 verdict.** With the pair in §D, do you want it filed to round 15 as
narrowed-not-caused, or is it a blocker for you? Our read is `NEXT-ROUND` and we
will not argue if you say otherwise, but **S-14 asks what it breaks in the
artifact under review**, and we cannot see that it breaks anything: `-j` is not in
our rip argv, so no rip we produce can enter that path.

## J. Questions

**J1 — `BLOCKING`, and it is the smallest one here.** §G — send `round-14-lap-14.md`.
Promoted because your §J3 carries its content forward as an open item, so the round
cannot close on a document neither side can enumerate. That satisfies S-14: what it
breaks is the round's own record.

**J2 — `NEXT-ROUND`.** §H2. If the pin moves, we re-pin and re-run; if it stays, we
run `d9c058c` again. No preference.

**J3 — `NEXT-ROUND`.** §D1(b) — do you want us to run `rig-c1-probe.sh` on the next
rig night, or is the §D pair enough for round 15?

---

**`HANDSHAKE-VERDICT: OPEN`** — CC-2 has not run. **But the reason it has not is
fixed**, and that is the difference between this lap and the last three: §F's rip
now starts.

**The disc is the only thing left on our side.** The round is yours to close.
<<<<<<<<<< END round-14-lap-16.md >>>>>>>>>>

<<<<<<<<<< BEGIN fullacceptance.txt sha256=e5e7f24a20a3233b3b2d658e776a43895fe1304119b81868303a50302f579420 >>>>>>>>>>
# =============================================================================
# FULL ACCEPTANCE RUN — end to end, every path the program has, one pass
# =============================================================================
#
#   How to run it:  Tools -> Run acceptance test...  (the app does the rest:
#                   session folder, sleep lock, the run, and one file to send)
#   Where it lives: INSIDE the app, since v0.6.32 — there is nothing to download.
#                   Source: src/platterpus/rig_scripts/fullacceptance.txt
#   What it costs:  4 to 6 hours. LEAVE IT RUNNING OVERNIGHT.
#                   It rips the whole disc TWICE (once fast, once with every
#                   track read at least twice) plus six short partial rips.
#
# NOTHING IN THIS FILE NEEDS EDITING. No album name, no track count, no path,
# and — as of this version — no cyanrip build tag either. Put any ordinary
# audio CD in the drive, start it, and go to bed.
#
# AND IT IS RE-RUNNABLE, which it was not before. Every `album` line carries
# `(run)`, expanding to this run's own timestamp, so a second run never lands on
# the first run's folders. Before that, a re-run raised "Album already ripped"
# on every rip; the file answers that prompt in exactly ONE place (§H, on
# purpose), so the other seven rips were refused behind an unanswered modal and
# the 2026-08-25 attempt lost sixteen of its seventeen failures — and all of T1 —
# to it. **You no longer need to move the previous run's output aside.**
#
# §F and §H still name the SAME album deliberately: §H exists to raise that
# prompt and answer it with `click=new`, and `(run)` is stable within one run so
# that collision still happens exactly where it is wanted.
#
# -----------------------------------------------------------------------------
# BEFORE YOU START — two things, and only two
# -----------------------------------------------------------------------------
# 1. Be on the newest Platterpus. Help -> Check for updates, or download the
#    AppImage from the releases page.
# 2. Be on the cyanrip build THIS Platterpus expects — which is **not** always
#    the newest one. Help -> Check for cyanrip updates..., and take the offer it
#    presents as a plain one-click install. An offer that WARNS you first is a
#    newer build no closed round has reviewed: taking it makes every rip report
#    `unapproved`, and section A will refuse to run on it.
#
#    Do not reach for a channel toggle to decide this, and do not look for the
#    answer in this comment: THIS FILE NAMES NO BUILD, on purpose. Which one is
#    wanted changes every time a handshake round opens or closes, and this file
#    ships inside a release — so anything written here freezes on the day it was
#    built and cannot learn that the answer moved. Both previous attempts were
#    wrong within days, and each one sent operators to a build section A refuses.
#    The app holds that fact in one place and checks it — which is why step 2
#    above is the whole answer, and there is no second copy of it here.
#
#    Section A asserts the exact expected build and STOPS THE RUN in the first
#    few seconds if you are not on it — before any drive time is spent.
#
#    That stop is real as of this version. It used to be a promise this file
#    could not keep: nothing but `abort` ends a batch and this file never used
#    it, so a wrong ripper produced a FAIL on line ~20 and then six hours of
#    evidence about the wrong binary. The cyanrip fork read the old sentence and
#    relayed it to the operator (round 14 lap 11 §J7). `abort-if-failed` below is
#    what makes it true.
#
# Everything else is in this file.
#
# -----------------------------------------------------------------------------
# WHY THE ORDER IS WHAT IT IS
# -----------------------------------------------------------------------------
# Maintainer directive: *"fresh start, rip, every test there is, all of them.
# this needs to be a good pass fail test"* — the gate on 0.7.100. And KDD-35: a
# version number is a claim about the field, not about CI. Every defect that
# mattered in August was found on hardware with the suite green throughout.
#
# LEAST-LIKELY-TO-FAIL FIRST, deliberately, and it has a cost. Sections A-E are
# near-certain passes that take about five minutes; the first rip is section F.
# Putting the cheap checks first means a broken build or a wrong ripper is
# caught before hours of drive time, and the transcript reads as a widening
# cone — identity, then settings, then validation, then UI, then disc, then
# audio, then the derived formats, then the long one.
#
# The cost: if section F fails, A-E having passed tells you almost nothing about
# why. Accepted. The alternative spends the night before learning the ripper was
# not installed.
#
# THE RULE THAT MAKES THIS SAFE TO LEAVE UNATTENDED: a failing step does NOT
# stop the batch. Only `abort` does, and this file never uses it. Every check
# below fails loudly and the run continues. A run that stops at the first
# problem hides every problem behind it, and a disc pass costs hours you do not
# get back.
#
# -----------------------------------------------------------------------------
# WHAT THIS RUN IS FOR: cyanrip handshake round 14, close condition CC-2
# -----------------------------------------------------------------------------
# CC-2 is the round's ONLY close condition: *one hardware acceptance pass on the
# RELEASED pair* — the cyanrip beta the round is reviewing, against the current
# Platterpus release — exercising the fork's round-14 lap 1 §T list.
#
# Round 13's version of CC-2 measured a mid-round TEST PIN while the release
# would necessarily be a later commit, so satisfying it would have closed a
# round on evidence about a build nobody installs. This one tests what ships.
#
#   §T1  a `-Z` rip that GENUINELY re-reads, and keep the log     -> section N
#   §T2  `-T unicode` end to end on a title carrying `<` and `:`  -> sections F, H
#   §T3  `-x -I`, the probe-only cache invocation                 -> section P
#   §T4  an interrupted rip, on hardware                          -> section I
#   §T5  an Enhanced CD, if one turns up                          -> not scripted
#
# T5 is deliberately absent: it needs a disc we may not own, the fork says it is
# not a blocker, and "no such disc available" is a different claim from "none".
#
# -----------------------------------------------------------------------------
# WHAT THIS RUN CANNOT ASSERT — read the transcript and the bundle for these
# -----------------------------------------------------------------------------
# Stated up front rather than buried, because a verdict implying more than it
# checked is worse than a shorter one.
#
#   * THAT THE AUDIO IS BIT-PERFECT. `wait-for-rip` waits for the worker to
#     disappear; it does not grade the rip. AccurateRip and CTDB verdicts are in
#     the report and the log — `rig-check` parses them and the bundle carries
#     both. Read them.
#   * WHETHER DIALOG TEXT IS CLIPPED. A rendering fact at your font size and DPI
#     that no assertion can see. Section D takes screenshots; a person must look.
#   * OVERREAD (`-O`). It has run on the BDR-209D and it HUNG THE DRIVE ~23
#     minutes. Never enabled here; section Q asserts it is still off.
#   * `-f` READ-OFFSET AUTODETECTION. Never run on this rig.
#   * C2 ERROR REPORTING. This drive reports it unsupported, so a green run is
#     not evidence about C2.
#   * DAMAGED MEDIA, and therefore paranoia's actual error correction.
#   * A NON-ZERO `Read stalls:` COUNT. A silent watchdog is not a working
#     watchdog; healthy media cannot produce the other branch.
#   * THE WELL-FORMED ENHANCED CD branch. Exercised by nothing, anywhere.
# -----------------------------------------------------------------------------

log =============================================================
log FULL ACCEPTANCE RUN - end to end, one pass
log order: cheapest and least likely to fail first
log the first rip is section F; the long one is section N
log =============================================================

# Debug logging ON for the whole run. A defect found at 4am is only as
# diagnosable as the log, and this is the one setting that changes how much of
# the run is recoverable afterwards. Restored in section Q.
set debug_logging on
expect debug_logging on
snapshot atstart

# --- A. IDENTITY: which binary is about to be graded -----------------------
# FIRST, always. Every claim below is about a specific build, and a result that
# looks wrong must be attributable rather than guessed at. A build tag we do not
# recognise reads as "not determined", never as a pass.
#
# This also arms the `(ripper)` placeholder used by the album titles further
# down: it expands to the installed build tag, read from the banner captured
# here. If this step is removed, those `album` steps FAIL and say so rather than
# writing the literal text — an unexpanded placeholder would give two rips the
# same folder while looking like it worked.
#
# `expect-ripper-under-review` TAKES NO ARGUMENT, and that is the fix for a
# defect that recurred three times in two days. This file used to name an exact
# build tag; the fork then published two more betas on the channel our own
# installer resolves, so an operator who followed our instructions installed the
# build we sent them to and was told here that it was wrong. The verb now reads
# the constant the handshake record derives, so a pin move fails in CI instead
# of at 2am on your rig.

log --- A. identity: which ripper is installed ---
cyanrip --version
expect-exit 0
expect-cyanrip platterpus-fork
expect-ripper-under-review
snapshot identity

# WHICH LINK IN THE RIPPER CHAIN FAILS TO EXIT — gathered, never asserted.
#
# Two consecutive rig mornings (2026-08-26, 2026-08-27) produced ZERO rips and
# neither failed at ripping: both ended mid-probe with `cyanrip --version`
# printing its banner in full and then not returning, until a 60s timeout killed
# it. The cyanrip fork showed three independent ways the hang is not cyanrip and
# asked for three shell commands to be run by hand. This is those commands.
#
# It records `info` and moves on. A wrapper that hangs from an interactive shell
# does not affect this run — the app pipes its I/O — so failing here would abort
# a six-hour pass over something that changes no rip.
probe-ripper-wrapper

# THE ONE PLACE THIS FILE IS ALLOWED TO STOP, and the distinction is the point.
#
# The rule above — "a failing step does NOT stop the batch" — is about FINDINGS,
# and it is right: a run that halts on the first problem hides every problem
# behind it. It is the wrong rule for a PRECONDITION. A wrong ripper does not
# make the next six hours partially useful; it makes them evidence about a
# different subject, which is exactly what the handshake exists to prevent
# (two artifacts from the same ripper under different app versions are not
# interchangeable evidence).
#
# So: preconditions abort, findings do not. Nothing below this line uses it.
abort-if-failed the installed ripper is not the build the handshake record names — fix that first, the failing step above prints the one command

# --- B. SETTINGS VALIDATION: the cheapest real check in the program --------
# Pure round-trips through the REAL validator, which is the source of truth — a
# spin box's own range is a convenience, not the validation (CLAUDE.md: validate
# every input, visibly and to the log).
#
# Every `set` here is a value we then read back. A silent coercion would show up
# as an `expect` failure rather than as a wrong rip hours later.
#
# 667 IS THIS DRIVE'S TRUE READ OFFSET, not an arbitrary test value — so this is
# a guard and section Q is right not to restore it. The Pioneer BDR-209D is +667
# from three independent places: the bundled AccurateRip drive table (whose
# regeneration script REFUSES to write unless the BDR-209D=+667 sentinel still
# passes), `docs/hardware-test-checklist.md` (*"confirmed, two independent
# sources agree"*), and a rip verified byte-identical against the EAC baseline on
# 12 of 14 tracks. Said out loud because the cyanrip fork asked (round 14 lap 3
# §C6) and could not tell a guard from a mistake by reading it.
#
# ON ANY OTHER DRIVE, change this to that drive's offset before running.

log --- B. settings: validated round-trips ---
set read_offset 667
expect read_offset 667
set max_retries 3
expect max_retries 3
set output_format flac
expect output_format flac
set force_overread off
expect force_overread off
set auto_eject_after_rip off
expect auto_eject_after_rip off
set ripper_channel beta
expect ripper_channel beta
snapshot settingsafter

# --- C. VALIDATION REFUSALS: proving the guards actually fire ---------------
# The half of validation nothing has ever tested on hardware. `expect-refused`
# asserts the pure validator REJECTS a value **and leaves the setting
# unchanged** — both halves, because a guard that reports a refusal and writes
# the value anyway is worse than no guard: the log says the input was rejected
# while the setting still reaches cyanrip's argv.
#
# These are the numbers that become command-line arguments. A read offset out of
# range rips every subsequent disc wrong with a clean-looking log, which is
# exactly why the range exists and why it is worth one second to prove it holds.

log --- C. validation: every guard must refuse and not write ---
expect-refused read_offset 99999
expect-refused read_offset -99999
expect-refused max_retries 101
expect-refused secure_rerip_matches 11
expect-refused mp3_vbr_quality 10
# And the floor: the guards must not refuse everything. If these were also
# refused, every assertion above would pass for the wrong reason.
expect read_offset 667
expect max_retries 3
snapshot validationdone

# --- D. DIALOGS: everything that can be opened, opened and closed ----------
# Not assertions about text — assertions that opening and closing a dialog does
# not crash, hang, or leave one on screen. `expect-dialog none` at the end is the
# one that catches a dialog that failed to close, which is how a modal comes to
# swallow every later step.
#
# Screenshots for the dense ones (maintainer: "it is a lot"). Every dialog is
# still OPENED — that is the part that can crash.

log --- D. dialogs: open, close, and prove none is left up ---
open drive
screenshot dialogdrive
cancel
open settings
screenshot dialogsettings
cancel
open dependencies
screenshot dialogdependencies
cancel
open about
cancel
open diagnostics
screenshot dialogdiagnostics
cancel
open guide
cancel
open setup
cancel
snapshot dialogsdone

# NO `expect-dialog none` HERE, and the omission is the fix rather than a gap.
#
# **Measured, 2026-08-25 (run 3).** With a disc in the drive, the app identifies
# it at launch and OPENS THE RELEASE PICKER BY ITSELF — before this script
# reaches section D at all. So the picker sits underneath the whole dialog
# section, and an `expect-dialog none` here reported it, correctly, as a
# failure: *"a dialog is open: 'Pick a MusicBrainz release'"*. The assertion was
# true; the expectation was wrong.
#
# The script cannot assert an empty screen before it has answered the picker,
# because having a disc in the drive is a PRECONDITION of this whole run. So the
# assertion moves to just after `pick-release`, where it says something real:
# the picker we answered is gone and nothing else was left behind it.

# --- E. DISC IDENTIFICATION -------------------------------------------------
# The last cheap section. If this fails, nothing after it can mean anything, and
# you have spent five minutes rather than a night finding out.

log --- E. disc: scan and identify ---
rescan
pick-release 1 120
expect-dialog none
expect-tracks 2+
snapshot discidentified

# STOP HERE IF THE DISC WAS NOT IDENTIFIED. The section header above has said
# "if this fails, nothing after it can mean anything" since the file was written,
# and until 2026-08-26 it said so and then carried on for six hours — a comment
# where a check belongs, which is the failure `CLAUDE.md` names by that phrase.
#
# What it costs when the check is absent, measured on the rig the same night: the
# release picker was still open at section F's `rip`, the guard correctly refused
# to press Start behind a modal, and the operator had to answer the picker BY HAND
# to unblock a run whose entire purpose is being unattended. Every rip after that
# point is evidence about a release nobody scripted.
#
# `pick-release` already refuses to pass on a picker that never appeared unless
# tracks are loaded, so a FAIL here is a real one: either the picker did not
# resolve inside its 120 s, or the disc loaded no tracks. Both mean the night is
# already lost — five minutes in, which is the whole point of putting the cheap
# sections first.
abort-if-failed the disc was never identified — the picker did not resolve or no tracks loaded, so every rip after this would be about an unknown release

# --- F. THE MAIN EVENT: a full-disc rip ------------------------------------
# ALL tracks, once, FLAC, fast-verified. This is the archival rip and the one
# whose artifacts matter most.
#
# THE TITLE CARRIES A COLON AND A '<', BOTH DELIBERATE — this is §T2.
#
#   * The COLON is the only thing that exercises the tag escape.
#     `_escape_meta_value` sends a literal ':' to cyanrip as '\:'. A safety net
#     reverses any leftover '∶' (U+2236 RATIO) in the written tags, armed ONLY
#     when the metadata actually contains a colon — so before 2026-08-20 that
#     gate was False on every scripted rig rip and the escape had never once run
#     on hardware.
#     WHAT TO LOOK FOR: this album's tag must read with a REAL colon. A '∶'
#     means the escape did not survive. The FOLDER name is expected to differ —
#     we now pass `-T unicode` and the fork's measured table says the folder
#     becomes `full acceptance∶ angle‹bracket`.
#
#   * The '<' exercises the PlainText fix. Three QMessageBox surfaces rendered
#     external text as HTML, so a '<' in an album-derived string was parsed as an
#     unknown tag and EVERYTHING AFTER IT WAS SILENTLY DROPPED. The surface that
#     names this folder is the overwrite prompt in section H.
#
# Cover art, CTDB verify, FLAC verify and the EAC-compatible log are all turned
# ON for this rip. They are the post-rip subsystem and nothing else in this file
# reaches all four at once.
#
# The timeout is three hours because a full disc on this hardware is 50-70
# minutes and one real session measured 2h45m against cyanrip's own ~35m ETA.
# Generous and still bounded.

log --- F. the main event: full-disc rip, all tracks, every post-rip check on ---
set cover_art embed
expect cover_art embed
set save_additional_art on
set ctdb_verify_after_rip on
set verify_flac_after_rip on
set write_eac_log_after_rip on
expect write_eac_log_after_rip on
select-tracks all
album full acceptance: angle<bracket (run) (ripper)
album-artist Platterpus Acceptance
rip
wait-for-rip 10800
snapshot afterfullrip
screenshot afterfullrip
# 'Done' is measured, not guessed: the status line after a clean rip reads
# 'Done - all N tracks ripped cleanly, no read errors. AccurateRip: ...'.
# Matching one disc-agnostic word keeps this working on any CD.
expect-status Done

# --- G. POST-RIP VERIFICATION ----------------------------------------------
# `rig-check` is the seam check the cyanrip fork asked for, reachable both as a
# script verb and as `--rig-check` so both projects append to one manifest. With
# no argument it DISCOVERS the album folder, which is why it can run here without
# this file knowing a path.
#
# It composes a real rip's argv, runs it against a device that cannot open, reads
# `invocation` back out of cyanrip's own `-j` record, parses the rip's log, reads
# the handshake note, and reports the paranoia counters and any `Interrupted at:`
# line. SKIP means "did not run" and is not a pass — that distinction is the
# whole point of its status vocabulary.
#
# It also exercises a non-zero exit with a column-0 diagnostic and a complete
# `-j` record, which the fork's lap 3 §C4 pointed out is a real path this
# already covers.

log --- G. post-rip: the seam check, and the rip's own log ---
rig-check
snapshot afterrigcheck

# --- H. RE-RIP ONTO THE SAME FOLDER: the overwrite prompt ------------------
# The title is BYTE-FOR-BYTE section F's, on purpose. Same string in, same folder
# out, so this rip collides and the "Album already ripped" prompt actually fires
# — which is the only way the PlainText fix gets exercised on hardware, and the
# only test of the guard that resolves the predicted folder against what is on
# disk. That guard exists because a two-track rip once silently overwrote a
# finished 14-track archival rip.
#
# WHAT TO LOOK FOR if you are watching: the prompt must name the folder IN FULL.
# The word after the '<' is the part that used to vanish.
#
# `click=new`, NOT `ok`. `ok` calls accept(), and accept() on a QMessageBox built
# with addButton leaves clickedButton() as None — so the caller falls through to
# its Cancel branch and the rip is CANCELLED while the transcript says
# "accepted". "Rip to a new folder" rather than "Replace" so section F's audio
# survives; it also exercises free_album_folder_templates, which nothing else
# here reaches.

log --- H. re-rip the same title: the overwrite prompt must fire ---
select-tracks 1-2
album full acceptance: angle<bracket (run) (ripper)
rip
answer-dialog click=new 120 Album already ripped
wait-for-rip 3600
snapshot afteroverwrite
screenshot afteroverwrite

# --- I. THE CANCEL PATH, AND THE ONLY HONEST PROOF OF IT — §T4 -------------
# Cancel mid-track, not at a boundary — 90 seconds of reading gets us inside one.
# Then give the escalation its full SIGTERM-to-SIGKILL window before asking
# anything.
#
# A different album title here on purpose: this section is about the drive, and a
# collision would add a dialog that has nothing to do with what is being tested.
#
# The `rig-check` after it is taken HERE and not later, because `rig-check` reads
# the NEWEST rip and section J is about to make a newer one. `parser/interrupted`
# reports cyanrip's own `Interrupted at:` line — the field the fork added at our
# round-12 ask, which we parsed for a round and never put in an artifact anyone
# sends. It is an INFO row, not a pass/fail: a cancel that lands between tracks
# legitimately produces "between tracks, no read in progress", and grading that
# would turn drive timing into a verdict.

log --- I. cancel a rip in flight ---
select-tracks 1-3
album cancel me (run) (ripper)
rip
log reading for 90s so the cancel lands mid-track
wait 90
snapshot beforecancel
cancel-rip
log cancel issued; giving the escalation its full window
wait 30
# The cancelled line reads 'Rip cancelled by user. Partial files may remain.'
expect-status cancelled
snapshot aftercancel
screenshot aftercancel
rig-check
snapshot aftercancelrigcheck

# --- J. THE DRIVE-OPEN PROOF: can we rip again? ----------------------------
# If this succeeds, the cancel released the reader. If it hangs or cannot
# identify the disc, it did not — and THAT is the finding, recorded here rather
# than in somebody's memory of a session.
#
# THE TRAY SHOULD STILL BE CLOSED. Before v0.6.16 a cancel left a 5-second rescue
# timer armed even when the reader had already stopped, so the drive was
# force-ejected seconds after every successful cancel — which made this section
# unanswerable in both directions. If the tray is open when you look, you are on
# an older build and this section proves nothing.

log --- J. drive-open proof: identify and rip again after the cancel ---
rescan
pick-release 1 120
expect-tracks 2+
select-tracks 1-2
album after cancel (run) (ripper)
rip
wait-for-rip 3600
snapshot afterrecovery
screenshot afterrecovery
rig-check

# --- K. THE DERIVED FORMATS — the whole of Critical rule #4 ----------------
# **Nothing has ever tested this on hardware.** FLAC is the archival master and
# MP3, WavPack and WAV are DERIVED from it by the single post-rip transcode
# adapter. Every rip still produces FLAC first; selecting another format keeps
# that FLAC and derives the chosen one from it.
#
# So each of these three sections proves a different thing:
#
#   * MP3      — lossy by design, best-practice VBR, and the ONLY one with a
#                quality knob. `mp3_vbr_quality 2` is a real VBR setting, not the
#                default, so a knob that reaches nothing would show up.
#   * WavPack  — the second lossless format. Tags and art survive.
#   * WAV      — raw PCM, NO tags and NO art. The UI warns about this and the
#                warning is the point: a format that silently dropped metadata
#                without saying so is the defect.
#
# Two tracks each. The transcode path is per-file and a third track adds a row,
# not a discriminator.
#
# A DIFFERENT ALBUM TITLE PER FORMAT, so the three land in three folders and
# none of them collides with section F's archival master.

log --- K1. MP3: the lossy derived output, with a real VBR quality ---
set output_format mp3
expect output_format mp3
set mp3_vbr_quality 2
expect mp3_vbr_quality 2
select-tracks 1-2
album derived mp3 (run) (ripper)
rip
wait-for-rip 3600
snapshot aftermp3
screenshot aftermp3
rig-check

log --- K2. WavPack: the second lossless format ---
set output_format wavpack
expect output_format wavpack
select-tracks 1-2
album derived wavpack (run) (ripper)
rip
wait-for-rip 3600
snapshot afterwavpack
rig-check

log --- K3. WAV: raw PCM, no tags, no art - the UI must say so ---
set output_format wav
expect output_format wav
select-tracks 1-2
album derived wav (run) (ripper)
rip
wait-for-rip 3600
snapshot afterwav
screenshot afterwav
rig-check

log --- K4. back to FLAC, the archival master ---
set output_format flac
expect output_format flac

# --- L. THE GOAL PRESETS: a label must mean what it says -------------------
# A goal is not a setting; it is a NAME for a set of them. Selecting one applies
# the whole preset, and this section proves the label and the settings agree —
# because a goal that wrote only its own name would leave the app ripping with
# exactly the settings the user was trying not to use, under a label promising
# otherwise. "Archival Exact" was byte-identical to "Fast Verified" until
# v0.6.24 for a related reason.
#
# No drive time: pure settings round-trips through the real preset code.

log --- L. goal presets: selecting a goal applies all of it ---
set rip_goal archival
expect rip_goal archival
expect secure_rerip_dynamic off
expect rerip_offset_variant on
set rip_goal portable
expect rip_goal portable
expect output_format mp3
set rip_goal fast_verified
expect rip_goal fast_verified
expect secure_rerip_dynamic on
expect output_format flac
snapshot goalsdone

# --- M. NAMING TEMPLATES ----------------------------------------------------
# The templates decide where every file lands, so a template that silently fails
# to round-trip is a library-wide defect. Pure validation, no drive time — the
# rip in section N runs on the restored default.

log --- M. naming templates round-trip through the validator ---
set track_template %A/%d/%t - %n
expect track_template %A/%d/%t - %n
set disc_template %A/%d/%d
expect disc_template %A/%d/%d
snapshot templatesdone

# --- N. §T1: A SECURE RE-READ THAT GENUINELY RE-READS — THE LONG ONE -------
# The fork's most-wanted test, and the one the whole round-13 paranoia argument
# turned on. **This is the section to leave running overnight.**
#
# WHY IT NEEDS ITS OWN SECTION. Under `-Z`, a track's own paranoia counter is the
# LAST pass while the disc block sums EVERY pass, so the two are equal exactly
# when each track was read once — and a clean disc in DYNAMIC mode converges on
# the first read, which is what every other rip in this file does. Every artifact
# either project has ever checked that claim against had that property, which is
# why a false invariant survived five handshake rounds: it is arithmetically
# forced in the only case anyone ever measured.
#
# `secure_rerip_dynamic off` is UNIFORM mode — EAC-style Test & Copy, every track
# read until two reads agree, not only the tracks AccurateRip could not confirm.
# So `total_repeats > 1` on every track regardless of how clean the disc is, and
# the fork's `Scope:` line is printed.
#
# WHAT THE INVARIANT IS, AND WHAT IT IS NOT. The property is an INEQUALITY:
#
#     sum(per-track counters)  <=  disc-level total
#
# with equality exactly when every track was read once. The tempting form —
# `disc == passes x sum` — holds on the fork's synthetic fixture BY CONSTRUCTION,
# because every pass there does identical work, and it will NOT hold on media,
# where re-reads exist precisely when passes differ. `rig-check` grades the `<=`
# and reports the multiple as an observation. Nothing here asserts the ratio.
#
# THE WHOLE DISC, not two tracks. The fork said two tracks is sufficient for the
# inequality and they are right — but they also said the interesting case is *a
# track that needed three or more reads*, and that is a property of the disc, not
# of the selection. Ripping every track is the only way to give the disc a
# chance to produce one. It costs about two hours and this run has all night.
#
# Six hours of timeout because uniform mode roughly doubles the read and this
# rig has measured 2h45m for a single dynamic pass.

log --- N. T1: uniform secure re-read, WHOLE DISC, so the counters actually move ---
set rip_goal archival
expect secure_rerip_dynamic off
expect rerip_offset_variant on
set secure_rerip_matches 2
expect secure_rerip_matches 2
rescan
pick-release 1 120
expect-tracks 2+
select-tracks all
album secure reread (run) (ripper)
rip
wait-for-rip 21600
snapshot aftersecurereread
screenshot aftersecurereread
expect-status Done
rig-check

# --- P. §T3: THE CACHE PROBE, PROBE-ONLY ------------------------------------
# LAST OF THE DRIVE WORK, DELIBERATELY. `-x` alone has form: measured once on
# this rig (32 sectors, 73.5 KiB, uncached read 362.6 ms, 2026-08-19) and then it
# ripped the whole disc, ETA 1h 3m, leaving the drive held. `-x` is a MODIFIER;
# `-x -I` is the probe-only invocation and writes no audio — the fork states that
# in their round-13 lap 5 and round-14 lap 1 §T3, and their lap 3 §C3 confirms
# they CANNOT promise it returns the drive, because nothing in their suite has
# ever executed a single timed read (on an image the probe refuses before doing
# anything).
#
# So it is real, it is theirs to be right about, they asked for it, and it goes
# after every rip in this file: if it does hold the drive, it costs the tail of
# the run and not the rip evidence. A hang here is the finding.
#
# `-N` is present because the script sanitiser requires it of any non-probe
# invocation and it is right to — without it cyanrip runs its own MusicBrainz
# lookup and can block on a prompt with no terminal attached, which is the
# unattended hang this whole feature exists to prevent.
#
# ASSERT THE FIELD NAME, NOT THE VALUE, AND THAT IS DELIBERATE. The build under
# review REMOVED the old `%i sectors measured (…)` wording — it claimed a
# precision the method does not have. The value is now one of five forms, and
# exactly ONE is ever emitted (they are arms of a switch, each writing the whole
# buffer):
#
#     Cache probe:    %i to %i sectors (…)                    a range
#     Cache probe:    at least %i sectors, upper bound unknown (…)
#     Cache probe:    no readback cache measured (…)          measured, found none
#     Cache probe:    unknown (read failed at %i sectors, …)  could not measure
#     Cache probe:    unknown (read could not be timed …)     could not measure
#
# `no readback cache measured` and `unknown (…)` are NOT the same claim — the
# first is a measurement that found nothing, the second a measurement that could
# not be taken. On an image the line reads `not run (disc image has no drive
# cache)`, so its ABSENCE here is the first sign the probe really ran on metal.
# A script asserting any one value would fail on a correct probe.
#
# WHERE THIS EVIDENCE LANDS: the script report and the transcript, NOT the
# rig-check manifest. `-x` is not in the rip argv builder at all, so no
# Platterpus rip ever probes and no rip log can carry the line. The `cyanrip`
# verb records the exact argv, the exit code and the complete output for this
# step, which is a stronger record than a manifest row would be.

log --- P. T3: the fork's cache probe, probe-only ---
cyanrip -N -x -I
expect-exit 0
expect-cyanrip Cache probe
snapshot aftercacheprobe

# --- P2. C1: THE THIRTY-MINUTE HANG, DETECTED (NOT DIAGNOSED) ---------------
# The fork asked for this in round 14 lap 11 §K2, and the split of labour is the
# point: THIS STEP DETECTS, their `rig-c1-probe.sh` EXPLAINS. Only run their
# probe if this step hangs; if it does not hang, that is itself worth knowing —
# it says the hang is not unconditional, which no disc-image fixture could ever
# establish.
#
# WHAT IT PROVOKES. With no `-s`, cyanrip reads the TOC and refuses for want of
# a read offset. On the 2026-08-25 rig session that refusal wrote its `-j`
# diagnostics record fourteen seconds in — so the process decided to fail and ran
# its exit path all the way to completion — and then stayed alive for roughly
# THIRTY MORE MINUTES holding the drive, needing SIGKILL. Cause not determined,
# by either project. The branch is gated on a DRIVE CAPABILITY that image drivers
# do not report, so it is unreachable from every fixture either side has: it
# needs a real drive, and this is the cheapest place to put one in that state.
#
# WHY IT IS SAFE TO HAVE IN AN UNATTENDED RUN. The `cyanrip` verb is bounded —
# 300 s, then the child is killed, then a further 20 s before the runner stops
# waiting and reports an UNREAPABLE CHILD with a null exit code rather than 0.
# A hang here therefore costs five minutes and is recorded as a finding; it
# cannot eat the night. That bound is the answer to the fork's §J6, which asked
# before agreeing this step should exist at all.
#
# LAST OF THE DRIVE WORK, on §P's reasoning exactly: if it holds the drive it
# costs the tail of the run and not the rip evidence.
#
# `-l 1` is insurance, not intent. If the refusal does NOT fire on this drive,
# cyanrip would otherwise start ripping; limiting it to one track bounds the
# damage to something the verb timeout can end. In that case `expect-exit 1`
# fails and says so, which is the correct result — "it did not refuse" is a real
# finding about the rig, not a broken step.
#
# NO `-j` HERE, and the reason is worth recording rather than leaving as an
# omission. The fork's §K2 suggested one, to get cyanrip's own record as a
# channel independent of the capture. Our script language has no path
# placeholder, so a `-j` would need a hard-coded absolute path in a file whose
# whole promise is that nothing in it needs editing. It is also less necessary
# here than in their probe: this verb captures through `run_capture` — a pipe we
# drain — and not through the shell redirect whose contents went missing in
# `rig_session.sh` step 5b. Different channel, so an empty capture here would be
# a NEW finding rather than a repeat of that one.

log --- P2. C1: does a no-offset refusal hang the drive? ---
cyanrip -N -l 1
expect-exit 1
expect-cyanrip Offset is unset
snapshot afterc1

# --- Q. LEAVE THE RIG AS WE FOUND IT ---------------------------------------
# Restoring is not tidiness. Uniform secure re-read doubles every future rip on
# this machine, MP3 would make the next rip lossy, and a setting a test left
# behind is a setting nobody chose.
#
# The overread assertion is a GUARD, not a restore: this script never enables it,
# so if `force_overread` is on here something else turned it on, and that is
# worth knowing before the next disc — it reaches cyanrip's argv and on this
# drive it hangs the read.
#
# The read offset is NOT restored, because 667 is this drive's true offset (see
# section B) and putting it back to 0 would be the mis-configuration.

log --- Q. restoring what this run changed ---
set rip_goal fast_verified
expect rip_goal fast_verified
expect secure_rerip_dynamic on
set output_format flac
expect output_format flac
set mp3_vbr_quality 0
set write_eac_log_after_rip off
set debug_logging off
expect debug_logging off
expect force_overread off
expect read_offset 667
expect-dialog none
snapshot atend

log =============================================================
log DONE. There is nothing left for you to run.
log Platterpus packs this run into ONE .tar.gz and names it in a
log dialog when the window comes back - with a button that opens
log the folder. Send that file. It carries the transcript, the app
log log, the settings, the screenshots and every rip folder's text
log artifacts (logs, cue sheets, reports, checksums). No audio.
log If the dialog is gone, the same path is on the SEND THIS ONE FILE
log line in the app log.
log =============================================================
# WHY THIS DOES NOT NAME A FOLDER. It used to say the bundle was under
# `~/.local/share/platterpus/bundles/` and to then run `--rig-session`. Both were
# wrong after v0.6.32 moved the session into the app: the deliverable lands in
# `~/Downloads` (or `$HOME` when there is no Downloads folder), and there is no
# second command. Two surfaces answering "where is my file?" with different
# answers is `docs/testing.md` §5.al, and the one a tired operator reads at 7am
# was the stale one. So this text now points at the surface that COMPUTES the
# answer instead of restating it - the dialog cannot drift from the path it was
# handed.
<<<<<<<<<< END fullacceptance.txt >>>>>>>>>>
