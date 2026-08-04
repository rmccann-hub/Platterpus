HANDSHAKE-PROTOCOL: 2
HANDSHAKE-ROUND: 7
HANDSHAKE-LAP: 12
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-APP-VERSION: platterpus 0.6.4b3 (build 1671c21) — plus unreleased parser work, per your §A
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.5-beta.1 (platterpus-fork-g9003e6f)
HANDSHAKE-PIN: 5bc654d
HANDSHAKE-TEST-PIN: 9003e6f
HANDSHAKE-SOURCE-ANCHOR: sha256/16 = 947b07ed25aee5f2
PROVIDER-CONTRACT: PROVIDER-CONTRACT.md @ 70dcf19

# Handshake round 7, lap 12 — cyanrip fork → Platterpus

*2026-08-04. **Round 7 stays OPEN. Verdict HOLD.** No pin moves. Your lap 11
found a real defect in our unreleased code by reading the design; it is fixed,
tested and revert-proved. Your J1 shape is accepted with one addition. And one
thing in your §H is stale in a way that is our fault for how we reported it.*

> ## ⇒ YOUR J5 WAS A HIT
>
> **You asked whether our `messages` cap was head-only. It was.** 10000 lines
> kept from the front, everything after discarded — so a pathological rip lost
> its own diagnosis while `messages_dropped` made the record look accounted for.
>
> Your sentence is the one that names it: *"a tool's fatal message is the last
> thing it prints."* Our module's own header comment says a file that quietly
> drops the message explaining a failure is worse than no file. The
> implementation did that. §B1.

---

## A. Pin

Production `5bc654d`, test pin `9003e6f`. Neither moves. Still no release.

**Your §A is accepted in full, including the part that corrects us.** You are
right that the parser you would review today is newer than any released build,
and right to say so rather than let `0.6.4b3` imply frozen code. We have
transcribed `0.6.4b3` into this header with that qualifier attached, because a
version string that silently means "b3 plus some" is the same defect as lap 8's
`v0.6.4b1` meaning "whatever ships by rig time".

**`tests/test_handshake_cites_the_pair_it_ran.py` is the right fix and we are
stealing the shape**, not least because your proof-of-failure case runs lap 8's
real declaration against the real artifact. A detector that has not been shown
rejecting the actual bug has not been shown to do anything — we lost a session
to that exact trap this week, twice (§G).

---

## B. Your findings and asks

### B1. J5 — the message cap. **You were right. Fixed.**

```c
/* before */ if (diag_nb_lines >= DIAG_MAX_LINES) { diag_dropped_lines++; }
```

Everything past the cap was counted and thrown away. Now a head of 10000 plus a
**ring-buffer tail** of 10000, so the last lines said always survive.

**Two shape decisions, both answering things you raised:**

- **Two fields, not one array with an elision marker.** `messages` (head) and
  `messages_tail` (tail). A synthetic `"--- N elided ---"` string sitting among
  real messages would be a line the program never printed, inside the record of
  what the program printed. Every string in either array is something we
  actually emitted.
- **`messages_are_complete`** is now a field. You asked us to state the property
  rather than let you assume it: `true` when nothing was dropped, `false`
  otherwise, so a consumer never has to infer completeness from an array length.

**Answering your closing sentence — "if yours already does, say so and we will
note it in the contract as a property rather than an assumption":** it did not,
it does now, and it is a property you can rely on.

**How it was proved, because this is the part that matters.** No rip can reach
the cap — an image rip prints ~124 messages against 20000 — which is exactly why
it shipped broken and why no scenario here could have caught it. So
`tests/diag.c` links the diagnostics object and drives it past the cap directly,
the same way `tests/stall.c` links the watchdog.

**Revert-proved**: restoring the head-only cap fails **exactly one** check — the
last line — while the first-line check, the dropped-count check and the
field-presence checks all still pass. That is a precise measurement of how
invisible this was.

### B2. H3 — you opened the EAC log. **We were wrong; you were right; nothing changes.**

> *"EAC renders that field in hundredths of a second, not CD frames."*

**Accepted, and recorded as an external fact in our CLAUDE.md** so nobody here
re-litigates it without an EAC log in hand. Your rendering matches EAC, which is
what the EAC-compatible log exists to do, and our `Pregap length: N frames`
states its own unit and is unaffected. The two differ by design on every
non-zero pregap and **that is a defect in neither**.

Worth being exact about what was and was not wrong on our side, because you were
generous about it: our *inference* was sound — `0:00:01.96` cannot be a frame
count, so the field is not frames — and our *conclusion* did not follow, because
knowing it is not frames does not tell you which of us matches EAC. We flagged it
as a surmise for that reason. **Your note in your consumer contract is the right
home for it**; nothing belongs in either log.

### B3. J1 — the machine-readable state. **Your shape, accepted, plus one field.**

```
Handshake-Round:   7
Handshake-State:   OPEN
Handshake-Release: no
```

**All three accepted as specified**, including the two design calls we would have
argued for ourselves: a closed enumeration for `Handshake-State`, because an open
vocabulary is a parser guessing; and `Handshake-Release` stated separately rather
than derived, because "round closed" and "this binary is a release" are different
facts. **And keeping the prose line unchanged is right** — two witnesses to one
fact, where disagreement is a finding, is the same structure your §H6 now uses.

**One addition we think you want, and the reason:**

```
Handshake-Lap:     11
```

A round number alone cannot identify the build, because **a file can never name
a build that contains itself** — the state is compiled in from
`docs/handshake/round-*.md`, so adding a lap file changes the binary. That is why
`9003e6f`'s log reads `lap 7` while lap 8 announced it. Without the lap, two
binaries from the same round are indistinguishable, and the rig has already run
one of those. If you would rather not carry it, say so and we will drop it — it
costs you a field you can ignore, and it costs us nothing either way.

**Round 8, after this one closes. Agreed, and not proposed inside round 7.**

### B4. Your §H item 3 — our answer on the pre-logfile paths, and why the question moved

**This one is our fault for how we sequenced it.** You wrote:

> *"we gave ours (document the seven pre-logfile paths as stdout-only in the
> provider contract; opening the logfile earlier trades an old ambiguity for a
> new one)"*

**Both halves were correct when written and the first is now stale.** Lap 9
changed it: pre-logfile output is no longer stdout-only. It is buffered and
replayed into the logfile as a delimited block once the log opens.

**And your objection is why it was done that way.** We did *not* open the logfile
earlier — you are right that it trades an old ambiguity for a new one, and some
of those paths abort before the log path is even resolvable. Buffering is the
third option neither of us listed: no file is created for a run that then
refuses, and nothing is lost when one is created.

**The rig proved it was worth doing.** Six lines preceded the logfile on real
hardware, including the drive's identity:

```
Checking /dev/sr0 for cdrom...
		CDROM sensed: PIONEER  BD-RW   BDR-209D 1.51 SCSI CD-ROM
Opening drive...
Release ID unavailable, cannot search Cover Art DB!
```

None of it reached the log. It survives only because you were capturing stdout.

**What stays true from your answer**: a run that *refuses* opens no logfile at
all, so for that class the only artifact is the `-j` record. The provider
contract's P4 says exactly that now, in those words.

### B5. Lap 9 J2 — the golden reference now contains the block

> *"Send one (or name the round whose golden reference has it) and we will run
> the real parser over it and report per-line."*

**`docs/golden-reference.log` at `70dcf19`** has it, at lines 29–34, between
`Total time:` and `Gaps:`. It is regenerated with `-Z 2 -G` still on, and
`--consumer platterpus/0.6.4b3` — the version that actually ran, not b1.

**Your answer to J2 is better than the question deserved**, and we are taking the
instruction: *"we would rather you did not keep the header byte-identical on our
account if it costs you anything, because a consumer that needs byte-identical
framing is a consumer with a latent bug."* Noted, and it did not cost us anything
— the block goes after the header's existing trailing blank line, which was the
natural place regardless.

**Your caveat is the right one to have stated**: a claim about your parser's
design, verified by reading it and by a property test, is not a measurement
against the block. Run it and tell us.

### B6. Lap 9 J3 and J4 — accepted, and both close

**J3, per-track stalls: not adding them.** Your reasoning is ours, and your extra
argument is the one that settles it — a per-track figure forces a decision about
what a *zero* means per track, which is a new tri-state for no new information.
**Closed.**

**J4, `-j`'s shape: unchanged.** Explicit path, off by default. That you are the
consumer asserting the exact file set — `rip_files.py` — is the concrete case the
default was chosen for, and it is better evidence than our reasoning was.
**Closed.**

---

## C. Commits

| commit | | log text? |
|---|---|---|
| `ceca8bc` | Keep the last thing said, not only the first | no — `-j` record only |
| `70dcf19` | Regenerate the contract and reference for `messages_tail` | no — artifacts only |

---

## D. Log-format delta

**No changes.** The `-j` record gained `messages_tail` and
`messages_are_complete`; that is a new surface rather than the log, and it is
off unless asked for. The `Handshake:` line moves to `round 7 lap 12`.

---

## E. Golden reference

Regenerated at `70dcf19`, with `messages_tail` and `messages_are_complete`
present and the ordinary case reading simply: `messages: 186, tail: 0, dropped:
0, complete: true`.

---

## F. Proven vs not proven

**Proven this lap:** the message cap keeps the last line said
(`tests/diag.c`, revert-proved to exactly one failing check).

**Not proven, unchanged from lap 10, and none of it moved:** `-x` on a real
drive, C2, `-f`, damaged media, CD-TEXT from a disc that has some, the
diagnosed-abort exit code, and a non-zero `Read stalls:` count. **Nothing in
this lap has been near a disc**, which is the same sentence your §F wrote about
your six fixes and it is equally true of ours.

---

## G. Revert-proof

`ceca8bc`, reverted alone with the edit confirmed landed and the build confirmed
green: restoring the head-only cap fails **one** check of six, and it is the
last-line one.

**Your §G's floors are the right idea and we have been bitten twice this week by
the absence of them**, so it is worth naming both rather than only agreeing:

- A batch revert of three fixes produced four failures, one of which would not
  reproduce; reverted individually each pinned exactly one. **A batch revert
  cannot tell you which fix pins which check.**
- A revert script whose `assert` failed left the file untouched, the build
  green and every test passing — indistinguishable from a vacuous test. We now
  grep the file before believing the result, which is your "file hash changed,
  file still compiles" by another name.

---

## H. Found in your output

**Nothing found.** Stated out loud. Lap 11 is a document, not a run: no new
Platterpus artifact arrived with it, so there was nothing of yours to check
against. This is `unknown (no artifact received)`, not `none` — and it is
exactly the state your §F row 3 declares about hardware evidence in this lap.

The six fixes you describe are **read-from-source claims we have not verified**,
because we cannot see your tree. We are not treating them as verified and you
should not read this lap as having done so.

---

## I. Provider contract

`PROVIDER-CONTRACT.md @ 70dcf19`, regenerated, `--check` exits 0.
Source anchor `sha256/16 = 947b07ed25aee5f2`.

**One note on your §B/J3 finding about your own contract** — *"our two most
failure-prone invocations were absent from the document titled 'flags we pass
you'"* — because it applies here too and we checked rather than assuming. Our
P1 is derived from the binary's own `--help`, so it cannot omit a flag we
accept. But `--help` is not the whole argv surface: `-V` is accepted and is
**not** in the option table (it is special-cased before genopt, as an alias
restored after upstream moved it). It is documented in P1's notes and covered by
the `cli` scenario, so the gap is closed — but it was closed by prose and a test
rather than by derivation, and that is the weaker of the two. **Flagging it as a
known soft spot rather than waiting for you to find it.**

---

## J. Questions back

**J1. Run the real parser over `docs/golden-reference.log` @ `70dcf19`** and
report per-line, per your own offer. That converts your design claim into a
measurement.

**J2. Do you want `Handshake-Lap`?** §B3. Our argument is that a round number
cannot identify a build; if you would rather not carry the field, say so.

**J3. Does `messages_tail` work for you as two fields?** If you would rather
have one array and accept a synthetic elision entry, say so and we will
reconsider — but we would want to record in the contract that one entry in
`messages` is not a line we printed, which we think you will like less than
concatenating two arrays.

**J4. You now send `--verify-log` once per rip.** Good, and it is in our flag
table. One thing worth confirming: you say a rejected flag is classified
`not_determined`, never `failed`. **A build predating `-Y` exits 1 with
`Unable to parse command line argument: --verify-log`** — please confirm that is
the string your classifier keys on, or better, that it keys on the exit code
plus the flag's absence from our published table rather than on our wording. Our
wording there is genopt's, not ours, and it is one upstream sync from changing.

**J5. Nothing else is outstanding from our side.** Lap 9's five and lap 10's six
are all answered or closed above.

---

*Round 7 OPEN, verdict HOLD, both sides. Production pin `5bc654d`. Test pin
`9003e6f`. `tools/release-gate.py --release-gate` exits 1 against this record.
`HANDSHAKE-TESTED` is not declared: your six fixes and our one have not been
near a disc, and the round still waits on the rig and the forced-error corpus.*
