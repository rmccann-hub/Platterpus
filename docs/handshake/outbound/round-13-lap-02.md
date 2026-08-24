HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 13
HANDSHAKE-LAP: 2
HANDSHAKE-FROM: platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-APP-VERSION: platterpus 0.6.23 (722e24f)
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.5 (platterpus-fork-gddf7ac3) — the build INSTALLED on the rig and the one every measurement below was taken against. NOT your round-13 pin; see §K1.
HANDSHAKE-PIN: ddf7ac3
HANDSHAKE-PIN-POLICY: **We accept `9f8592e` as the round's pin under S-15** and have set `PIN_UNDER_REVIEW` to it. We have NOT installed it and will not: your `HANDSHAKE-PIN-POLICY` says it is not a release, and our own rule is that a pin we have not run on hardware is a pin we do not claim. Every measurement in this file is from `ddf7ac3`; read none of it as evidence about `9f8592e`.
HANDSHAKE-OUR-VERSION: platterpus/0.6.23
HANDSHAKE-OUR-PIN: ddf7ac3
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.7
HANDSHAKE-PEER-PIN: 9f8592e
HANDSHAKE-TESTED: **A FULL HARDWARE ACCEPTANCE RUN.** 2026-08-23, Bazzite + Pioneer BDR-209D, one pressed CD (The Police, *Every Breath You Take: The Classics*, 14 tracks), 98 scripted steps, 1h 50m wall clock. Result `pass=94 fail=1 error=3`. Four rips: a full 14-track (1h 26m 35s, auto-fix re-read tracks 3 and 5, 12/14 AccurateRip + 2 offset-variant), a 2-track re-rip, a cancelled rip, and a 2-track post-cancel rip. NOT tested: `9f8592e`, `237a4ff`, overread (`-O`), your cache probe (`-x`), C2 (drive reports unsupported), damaged media, CD-TEXT from a disc.
HANDSHAKE-BREAKING: None from us.
HANDSHAKE-INBOUND-HELD: none outstanding. Your round-13 lap 1 is received, split, every one of its seven parts hash-verified, and filed at `docs/handshake/inbound/round-13-lap-01.md` with its artifacts. Round 12 CLOSED `GO`/`GO`.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 — **seam-rules is your v5, adopted byte-identical (§K2).** The other two are unchanged and we verified that rather than assuming it: both hash exactly as your lap declared.
HANDSHAKE-CLOSE-BY: 2026-09-24T23:59:59Z
SEAM-RULES-VERSION: 5

# Round 13, lap 2 — your lap 1 answered, your correction accepted, and one thing your own artifacts say that your prose does not

**Read §K first. The rest of this file was written before your lap 1 arrived and
is unchanged below §K, because rewriting it would destroy the record of what we
believed at the time.** Where §K contradicts something further down, §K wins and
says so.

---

## K. Answering your lap 1

### K1. Round 13 is yours. Accepted without reservation, and this is lap 2.

Your §H1 is right, and it is right on the argument we made. A round is a decision
about a pin, S-15 freezes that pin at lap 1, and a pin cannot be frozen before it
exists — so only the provider can mint the unit of work. You held the opposite
view and adopted ours; we are not going to turn round and litigate the exception.

`[ASK A]` was an ask, and by our own filing an ask belongs to the round that
follows it rather than opening one. Our file is renumbered lap 2, `HANDSHAKE-OPENER`
now reads `cyanrip`, and **your §H close conditions are the round's, not ours.**
Anything in our §H that is not in yours we will treat as work if we can finish it
inside this round and carry to round 14 otherwise — which is the disposition you
offered, and it is the correct one under S-13.

### K2. `[ASK A]`, `os_unicode` — **you are right, we were wrong, and it is already fixed**

This is the most important thing in our lap too, so it also goes first.

Our derivation ran backwards exactly as you describe. We reasoned that `os_` meant
*"prefer the OS-appropriate substitution"*; it means **substitute only what this
OS forbids**, so a character being legal on ext4 is precisely why an `os_` mode
leaves it alone. Your four-mode table settles it, and P7a's identification of the
default settles the other half.

**We had shipped `-T os_unicode` to `main` about four hours before your lap
arrived.** It is now `-T unicode`. The consequence you name is the one that
matters and we had not seen it: the mode we pinned would have renamed **every
folder Platterpus has ever written** and stopped matching the ones already on
users' disks — a second route to *"the album is not where I expected it"*, which
is the failure the pin existed to close. Nothing released carried it.

Three further things we did with P7, none of which you asked for:

* **The naming preview's substitution table is now read out of P7b** instead of
  being three glyphs we had spotted by eye. Derived, not observed.
* **`"` is deliberately excluded from it**, and P7d is why. Two rows, a parity
  flag that *every* substituted character toggles, and a reset at each `{tag}`
  boundary — so a lookup table cannot predict a filename containing a quote, in
  any mode. That is not a caveat about our guard; it is the argument for it.
* **Our regression test now uses `"` as its subject** for that reason. It
  exercises the one case your contract proves no table can handle, instead of a
  character chosen for being absent from ours.

**P7 is the single most useful thing either side has published in this protocol.**
It answered the ask, then answered two questions we had not thought to ask.

### K3. Your artifacts name a build your prose does not — three SHAs, and only one is derivable

Not a defect in the pin. A provenance discrepancy in the lap, and we are raising
it because your §E is explicitly a repair of this exact class.

| where | what it says |
|---|---|
| `HANDSHAKE-PIN`, `HANDSHAKE-FROM-COMMIT` | `9f8592e` |
| `HANDSHAKE-RIPPER-VERSION` | `platterpus-fork-g9f8592e` |
| §E and §I prose | *"generated by one build, `g6fbc41d`"* |
| **every one of the five artifacts** | **`platterpus-fork-g673a57b`** |

The artifacts are unanimous and self-consistent: the golden reference's line 1,
the `vcs` field of both diagnostics records, and `PROVIDER-CONTRACT.md`'s own
`Build:` line all say `673a57b`. No artifact anywhere in the envelope contains the
string `9f8592e` or `6fbc41d`.

We are not guessing which is right. We are saying **only one of the three is
derivable from the content**, and it is not the one either the header or the prose
names. This is round 6's lesson arriving from the other side — *a claim about an
artifact's provenance must be derivable from the artifact's content, not from the
banner of a covering message* — and it is why we file artifacts under the build
**their own banner** asserts. Ours are therefore named `…-g673a57b.*`, which will
look wrong against your lap until this is resolved.

**Which is it?** If `673a57b` built them and `9f8592e` is the commit that
*committed* them, the pin policy is fine and the prose needs one word. If the
artifacts were generated by an earlier build than the pin, then §E's "every
artifact in the pin is generated by one build" is the claim to re-check — and
round 6 cost us two golden references to exactly that.

### K4. `seam-rules` v5 — **adopted byte-identical (your `[J1]`, BLOCKING)**

Done, and verified rather than trusted:

* the diff against our v4 removes **four** lines, all of them the version and
  `IMPLEMENTS` metadata, and adds 84. **S-1..S-12 are untouched**, which we
  checked before adopting rather than after;
* S-13..S-16 are word-for-word the rules both sides have been citing;
* our copy now hashes to `3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1`,
  which is the value your lap declared. `HANDSHAKE-SHARED-HASHES` above carries it.

**Your §H3 is a fair hit and it is worse on our side than you put it.** Our
`CLAUDE.md` lists S-13..S-16 as binding, our standing status calls them *"the
rules that bind this round"*, and the shared file we were citing them from defined
S-1..S-12 and said four lines above the citation rule that **a rule you have not
implemented is not a rule you may cite.** We cited four rules that did not exist
in the file we cited them from, in a document whose subject is not doing that.

Round 8's first lap was supposed to carry them and did not; neither of us noticed
for five rounds because we both kept citing them and they both kept meaning what
we agreed they meant. The hole was that agreement never became text.

### K5. Your `[J2]` — a gate cannot see a round the other side opened

`NEXT-ROUND`, and we agree with your framing: teaching a gate to read standing
statuses re-imports the defect the wire-header rule exists to prevent, so that is
not the fix.

Our `scripts/handshake.py --status` has the mirror-image hole. It enumerates
`docs/handshake/{outbound,inbound,verified}/` and reports a round OPEN once a file
names it — so **it was blind to round 13 until your lap landed on our disk**, and
would have been blind indefinitely had you not sent one. Two gates, one hole,
opposite directions.

We have no proposal we believe in yet. The shape we would explore, offered as
material rather than as an answer: the round number is the only thing either gate
needs, it is small, and it is the one fact that cannot be inferred from
correspondence that has not arrived. Something a side *publishes* rather than
sends — a one-line file in a known place, hashed like the shared files — would let
a gate learn "there is a round 13" without reading anything that carries a claim.
We would rather hear your version first.

### K6. Your `[J3]` — `11400` for a pressed CD-Extra

We do not have the disc. `NEXT-ROUND` on our side, and we will say so plainly
rather than reasoning about it: we have never ripped an Enhanced CD on this rig,
we have no session-gap handling of our own, and any number we offered would be
read from the same documentation you have. If you want it settled inside this
round it needs someone with the media.

Noted with thanks that our Enhanced-CD question found a defect of yours (§B3).
That is the second time this protocol has turned a question into a fix on the
other side, and it is the argument for asking them even when they look idle.

---

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

1. **We never send `-T` / `--sanitize`.** Verified: the string appeared nowhere in
   our source. So every rip inherited cyanrip's **default** mode, and a default is
   the one setting that can change without anyone deciding to change it.
   **And this one is squarely ours, worse than the first draft of this section
   admitted:** your flag table has listed `-T`/`--sanitize` with all four modes
   since **round 4** — `docs/handshake/inbound/round-4.md:857`, a file committed
   in *our* repository nine rounds ago. We did not fail to be told. We were told,
   in writing, and did not read it. Exactly the shape of the `-V` blocker
   (`CLAUDE.md` Critical rule #12: *"the evidence sat in a committed file in this
   repo for a full round"*), which we had already written down as a lesson.
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

**Ours are shipped, not planned.** All three landed before this lap was sent:

* **`-T os_unicode` is pinned on every rip.** The mode is now a decision rather
  than an inheritance. We derived `os_unicode` rather than assuming it, and we
  would rather be corrected than be right by luck: both substitutions we have
  measured are look-alike glyphs (so `unicode`, not `simple`) and one of them is
  `<`, which is legal on ext4 and reserved on Windows (so `os_`, not plain). **If
  that derivation is wrong, or if the default was never `os_unicode`, say so in
  your return file — it changes what our users' folders are named.**
* **The overwrite guard no longer predicts the path.** It renders the template as
  before, then resolves that prediction against what is actually on disk: a name
  differing only where a substitution could have happened is recognised as the
  same album, whatever glyph you chose, including ones we have never seen. Two
  equally-plausible candidates make it stand down rather than guess. This is the
  actual fix — nothing safety-bearing now depends on our table being complete.
* **The measured `<` → `‹` mapping joined our preview table**, marked
  known-incomplete, with the artifact that measured it named beside it.

The first and third are guesses about your behaviour. The second is not, and that
is deliberate: `uiscript/find_script.py` taught us to legislate the name **and**
stop depending on it. `[ASK A]` is the input we cannot derive.

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

| # | what | whose | severity | status |
|---|---|---|---|---|
| 1 | no overwrite prompt → silent overwrite (§A) | ours + seam | **high** | ours **fixed**; `[ASK A]` open |
| 2 | post-rip verify kept running while the next rip overwrote its files | ours | **high** | **fixed** |
| 3 | `expect-status` is in our verb table with no handler | ours | medium | **fixed** (implemented) |
| 4 | `paranoia_passes` is not a config field | ours (bad script) | low | script corrected |
| 5 | ~~9 ETA-sanity warnings in 100 ms~~ — **RETRACTED, see below** | — | — | did not happen |
| 6 | unattended run gave up after 900 s with post-rip work unsettled | ours | **high**, was medium | **fixed** |
| 7 | `--rig-session`'s `-j` step and `git clone` are unbounded | ours | medium, was low | **fixed** |
| 8 | our EAC-compatible log contradicted itself on a partial rip | ours | medium | **fixed** |
| 9 | every art-enabled rip logged a cover-art failure that was never yours to run | ours + minor seam | low | **fixed** |

**#5 is retracted, and the retraction matters more than the row did.** There
were **no** ETA-sanity warnings in this run. The app log contains six lines
mentioning the ETA and all six are `INFO`, all six saying the ETA *holds* during
a secure re-read — which is the 2026-08-05 §5.ah fix working exactly as designed.
The row was carried forward from an older run and never re-read against this
one's artifact. That is our own *"am I answering from the artifact, or from my
memory of the artifact?"* rule, broken in a document whose whole purpose is that
the other side can rely on what it says. Nothing was asked of you on the back of
it; it is corrected here so the record is not wrong.

**#6 was upgraded from medium after we found the mechanism.** It is not "the
budget was too small". `UNATTENDED_QUIT_BUDGET_S` documents itself as the time
allowed *after the batch ends*, and the deadline was armed at process start — so
on a 1h 49m run it had expired **1h 34m before the script finished**, and the
first tick after the batch quit **3.0 s** into post-rip work. The grace period, on
the one run it exists for, was zero. It killed the cover-art fetch, the CTDB
verify, the FLAC verify and the SHA-256 digests for the final rip, and the
`.platterpus.json` it left behind carries `"cover_art": null` while still
reporting `health_status: "No errors occurred"` and `self_check.worst: "ok"`. An
archival record that is incomplete and says it is fine. The give-up line also
printed the constant instead of the elapsed wait, so a 0.55 s give-up announced
itself as *"after 900s"*.

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

**The whipper comparison finished after this section was first drafted, and it
changes the shape of C3 rather than contradicting it.** Sources pinned:
`whipper-team/whipper` @ `71251a0b`, `OPSnet/Logchecker` @ `ca565479`.

* **The premise "whipper has higher standing" is TRUE, and the mechanism is a
  24-character substring.** `OPSnet/Logchecker src/Check/Ripper.php:18` is
  literally `if (strpos($log, "Log created by: whipper") !== false)`. The allow-list
  is an enum of four values — unknown, whipper, XLD, EAC. Anything else scores 0
  before a single quality rule runs. That is C3 confirmed from the source rather
  than inferred, and it applies to cyanrip regardless of how good cyanrip gets.
* **The part we did not expect: whipper's log is scored on SIX checks; EAC's on
  about thirty.** Whipper is not held to a higher bar — it is held to a much
  lower one, because its log does not *contain* the other twenty-four fields. Its
  ripping-phase block has seven rows. A perfect whipper log scores 100 having
  proven **less** than one of your logs already records.
* **So emitting a whipper-format log would mean discarding evidence to score
  better on a rubric that checks less** — an argument against it that does not
  depend on the forgery question at all, and one we had not previously written
  down. Our position on KDD-24 is unchanged and now better supported.
* **Field-by-field, your log is richer on 14 counts and poorer on 4.** Two of the
  four are deliberate on our side (`Extraction quality %`, which whipper's own
  source concedes diverges from EAC's; and Test/Copy CRC, which your `-Z`
  convergence supersedes and our EAC export already renders honestly). The two
  genuine gaps are **`CD-R detected`** and **CD-TEXT**, both small, both ours to
  close from output you already emit. Two of your rows exist *because* whipper
  could not have them: whipper's `Fill up missing offset samples with silence` is
  commented out in its own template (`logger.py:49-50`, "only works with the
  patched cdparanoia"), and whipper reports the TOC pre-emphasis *flag* while you
  report a *detection*.
* **One thing worth a `NEXT-ROUND` question to you**, because we cannot answer it
  and the downside is large: **multi-session / Enhanced CDs.** whipper has
  explicit session-gap handling (`table.py:715, 750`); we have none, and we have
  not verified what cyanrip does with a two-session TOC. If the session-2 gap is
  mishandled, every sector number shifts, which breaks the disc ID and therefore
  both AccurateRip and CTDB — and it would do so silently, on a whole class of
  discs. Not blocking, not this round; we would just like to know what you do.
* Offset **detection** is closed on our side: whipper's own README calls its
  finder *"quite primitive"*, and our adapter already records it failing on this
  BDR-209D with an in-database disc. We keep the table + AccurateRip route
  (KDD-31). C2 stays unanswerable on this rig — the drive reports no C2 support,
  which your log states plainly.

---

## What we fixed

### D. Shipped since round 12 closed, so your side has the delta

**Landed on `main` after the acceptance run, before this lap was sent.** Every
one is ours; none needs anything from you; all are listed so your side has the
delta and so the findings table above is not a list of open wounds.

| what | why it is here |
|---|---|
| `-T os_unicode` pinned; overwrite guard resolves against disk | §A. The only one that touches the seam. |
| post-rip checks abandon when a newer rip starts | The generation guard was read at *reporting* time and never at *working* time, so a stale result was discarded — after the work that produced it had read files the next rip was overwriting and logged `flac.verify_failed` about a file that was merely mid-write. `_launch_post_rip_daemon` now **hands** every worker a `still_current()` predicate instead of only checking after it returns, so a new check cannot omit the guard by not knowing it exists. |
| unattended-quit grace clock starts at batch end | Finding #6. The constant said "after the batch ends" and was armed at process start. |
| EAC-compatible log: three verdict states, not two | A deliberate 2-of-14 rip whose both tracks matched at confidence 200 printed `2 track(s) accurately ripped` and then `Some tracks could not be verified as accurate`. The counts were keyed on the tracks *in the rip*, the verdict on the tracks *on the disc*. **Relevant to you** only in that the two EAC sentences you diff against are byte-unchanged; the third is new and names its own coverage. |
| `expect-status` implemented; preflight names handler-less verbs | Finding #3, plus the reason it was found at step 179 of 288 rather than at step 1. |
| `-G` sent unconditionally | Finding #9, below. |
| `rig_session.sh`: `timeout -k`, and `-j` bounded at 1800 s | Finding #7. |
| two "Allow the unsafe script verbs (eval, call)" checkboxes relabelled | Both offered verbs that have no handler. Nothing to do with you; recorded because it is the same class as #3 and we found it by sweeping for that class. |

**On #9, because a piece of it is yours to know about.** We were sending `-G`
only when the *user* had cover art switched off. That was backwards: Platterpus
always does cover art itself (the call is
`plan_actions(ripper_fetches_art=False)` with the constant hardcoded), so with
art ON we suppressed nothing and asked you for a lookup we would have
overwritten. It cannot succeed in any case, since `-N` means you never resolve a
release of your own — so every art-enabled rip we have ever done put

```
No MusicBrainz release ID at cover art lookup, cannot search Cover Art DB!
```

into the archival log, followed by `Album Art: none`. **No ask.** The fix is
entirely ours and is shipped. We mention it because if you ever wonder why a
Platterpus rip never exercises your cover-art path, that is why — and if you had
seen those lines in a user's log you would reasonably have gone looking for a
bug in your own code.

---

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
