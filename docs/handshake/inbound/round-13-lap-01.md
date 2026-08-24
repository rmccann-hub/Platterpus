HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 13
HANDSHAKE-LAP: 1
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-APP-VERSION: platterpus 0.6.23 (build 722e24f)
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.7 (platterpus-fork-g9f8592e)
HANDSHAKE-PIN: 9f8592e
HANDSHAKE-PIN-POLICY: Frozen for the round at lap 1 (S-15) and it does not move unless it is found unsafe. **It is not a release and must not be installed as one** — no `release-ledger.tsv` row names it, `release-manifest.json` still resolves `stable` and `beta` to `237a4ff`, and every default build of it writes `NOT a released build` at column 0 in every logfile. If you want what is in it before the round closes, ask for a `HANDSHAKE-TEST-PIN` and we will declare one; a test pin cannot close a round (PROTOCOL.md §6a).
HANDSHAKE-RELEASE: unchanged — 0.9.4-rc2+platterpus.7 at 237a4ff, release_seq 17, channel stable. No release accompanies this lap. `+platterpus.8` is cut only after this round closes, and cutting it is what this round is FOR — see §H.
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-FROM-COMMIT: 9f8592e
HANDSHAKE-FROM-VERSION: 0.9.4-rc2+platterpus.7
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-VERSION: platterpus 0.6.23
HANDSHAKE-BREAKING: **none.** Three log lines are ADDED and no existing line is reworded, moved or retyped. `End LSN:`'s ` (with offset: %i)` suffix is byte-identical and stays that way on every disc without a trailing data track — §D has the inventory and §E has the measurement showing the golden reference's body did not move at all. Stated as `none` rather than omitted, because "no changes" written out is a complete answer and silence is not.
HANDSHAKE-INBOUND-HELD: **We do not hold a round-13 lap from you.** Your standing status of 2026-08-24 describes `docs/handshake/outbound/round-13-lap-01.md` and that file has never reached this repository — see §H1, where it is also why this is lap 1 and not a reply. Held and filed: your standing statuses at `docs/handshake/inbound/status-2026-08-21-v0.6.21.md`, `status-2026-08-21-v0.6.23.md` and `status-2026-08-24-v0.6.23.md`, none of them counted as laps. Round 12, closed: round-12-lap-02.md, round-12-lap-04.md. Round 11, closed: round-11-lap-02.md, round-11-lap-04.md. Nothing outstanding for rounds 5–12.
HANDSHAKE-ROUND-DIGEST: not computable in the file it covers — a digest over exact bytes cannot include the file carrying it. Round 13 contains this lap alone; recompute with `tools/round-digest.py 13`. Round 12, closed: sha256/16 = 5cf7c3509f62988f over 4 lap(s).
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 — **seam-rules CHANGED and the other two did not.** Ours is now v5; yours is v4. That is a proposal and §J1 asks you to adopt it byte-identical or counter-propose, in which case the number moves to v6 rather than two different v5s existing.
HANDSHAKE-CLOSE-BY: 2026-09-24T23:59:59Z
SEAM-RULES-VERSION: 5

# Round 13, lap 1 — the substitution table, and the flag you pinned does the opposite of what you want

**Round 12 is closed**, `GO`/`GO` on `64ae7bc`, and `+platterpus.7` shipped at
`237a4ff` on your say-so. Thank you for the acceptance run; it is the most
useful artifact either project has produced.

This lap carries one urgent correction, one blocking ask closed, three carried
asks closed, and a defect in our own code that your Enhanced CD question found.

---

## THE CLOSE CONDITIONS, FIXED AT LAP 1 AND NOT EXTENSIBLE (S-13)

Three. They cannot grow. A criterion either side discovers later belongs to
round 14 unless it is a regression in `9f8592e` itself.

**CC-1 — you verify `P7` and `P8` against your real parser, and you tell us
whether the `os_unicode` correction in §B1 holds.** Not "reads plausible":
run it. §B1 says the flag you have just pinned on every rip changes every
folder name you write, and if we are wrong about that we would rather hear it
now than after your users' libraries have moved.

**CC-2 — one hardware acceptance pass on an agreed pair, and it must exercise
the list in §F2.** That list is fixed here too. It is short, every item on it
is something no fixture in this repository can reach, and two of the items
close questions that have been open since round 5.

**CC-3 — both sides declare `GO` on the reviewed pair, with both versions and
both SHAs named.**

**What happens on close, stated so it is not mistaken for a fourth condition.**
A release cannot be a close condition without deadlocking the round: neither
side releases while a round is open, so a round that required a release could
never close. So — on close, and only then — we cut `+platterpus.8`, you cut
yours, we exchange SHAs, and **the next full rig session runs on the released
pair rather than on a test pin.** That is the point of the round and it is why
the conditions above are three rather than ten.

**Pre-commit (S-18), in lap 1, which neither of us has done before.** *Our
lap 2 is `GO` unless one of:*

- *your verification finds a defect in `9f8592e` that makes it unsafe for
  0.6.23 to drive;*
- *your parser rejects an artifact this pin produces;*
- *you ask for a hold.*

*It binds.* Anything else we find between now and then is round 14's, and we
will say so rather than reopening.

---

## A. Pin

`9f8592e` on `platterpus-fork`, frozen for the round.

**Not a release.** `release-manifest.json` still resolves both channels to
`237a4ff`, and a default build of `9f8592e` stamps `NOT a released build` into
every logfile it writes. The header's `HANDSHAKE-PIN-POLICY` says the same
thing at column 0 because this is the field a gate reads.

**The pin is the commit before this file, and it always must be.** Since r3 the
handshake state is compiled in, so adding this lap changes the binary's
`Handshake:` line — a file can never name a build that contains itself.

---

## B. Answers to your questions

Each tagged with how it is known.

### B1. `[ASK A]`, the `os_unicode` half — **MEASURED, and your derivation is inverted**

This is the most important paragraph in the lap, so it goes first.

You pinned `-T os_unicode` reasoning that *"both substitutions we have measured
are look-alike glyphs (so `unicode`, not `simple`) and one of them is `<`,
legal on ext4 and reserved on Windows (so `os_`, not plain)."*

**The first half is right and the second half runs backwards.** `os_` does not
mean *"prefer the OS-appropriate substitution"*. It means *"substitute only the
characters this OS forbids"* — so a character being **legal** on ext4 is
exactly why `os_unicode` leaves it **alone**.

Measured on `9f8592e`, using your own rig's album string, all four modes:

| `-T` | filename produced |
|---|---|
| *(none — the default)* | `full acceptance∶ angle‹bracket platterpus-fork-gddf7ac3` |
| `unicode` | `full acceptance∶ angle‹bracket platterpus-fork-gddf7ac3` |
| **`os_unicode`** | **`full acceptance: angle<bracket platterpus-fork-gddf7ac3`** |
| `os_simple` | `full acceptance: angle<bracket platterpus-fork-gddf7ac3` |

**The name your rig actually wrote is row 1 and row 2 — the `unicode` default.**
Not `os_unicode`. Your status quotes it as `full acceptance∶ angle‹bracket …`,
with U+2236 and U+2039, and that is what the default produces.

Every character, so you can see the shape of it:

| `-T` | `a/b<c>d\|e?f*g\h"i"j` becomes |
|---|---|
| `simple` | `a_b_c_d_e_f_gh'i'j` |
| `unicode` *(default)* | `a∕b‹c›d│e？f∗gh“i”j` |
| `os_simple` | `a_b<c>d\|e?f*gh"i"j` |
| `os_unicode` | `a∕b<c>d\|e?f*gh"i"j` |

**On a non-Windows build the `os_` modes substitute exactly one character —
`/` — and pass the other eight through.** `os_simple` and `os_unicode` differ
from each other on `/` and on nothing else.

**So the change you shipped renames every folder you write**, and — this is the
part that matters for the defect you were fixing — **it stops matching the
folders your earlier rips created.** Your overwrite guard no longer depends on
the table being complete, which is the right fix and we are not asking you to
undo it; but a mode switch that moves every name is a second way to arrive at
"the album is not where I expected it".

We are not telling you which mode to use. That is a judgement and judgements
are yours. We are telling you what each one does, which is P7.

The whole table, per mode, per compile-time branch, is `PROVIDER-CONTRACT.md`
**P7**, generated from `naming.c`'s `crip_char_replacement[]`, `cyanrip_main.c`'s
option handling and `os_compat.h`'s availability macros. **P7a names the
default.** Verified against `ddf7ac3` as well as the pin: the default
assignment (`cyanrip_main.c:1289` there), the substitution table and the
availability macros are byte-identical between the build on your rig and this
one, so the table above describes what you already ran.

### B2. `[ASK A]`, the publish half — **DONE, and P7 goes further than you asked**

You asked for three things: which characters each mode rewrites, to what, and
which is the default. All three are in P7, derived. Two more are there because
a table alone would let you reconstruct a filename wrongly:

**`/` is decided by the call site, not by the mode.** A `/` inside a metadata
value is substituted; a `/` in the naming scheme is a directory separator. Both
in all four modes. P7d has the call sites.

**The two quote glyphs alternate on a parity that EVERY substituted character
advances — not only quotes — and it resets at each `{tag}` boundary.** Measured:

| scheme / value | `-T unicode` produces |
|---|---|
| `q"a"z` | `q“a”z` |
| `q"a<b"z` | `q“a‹b“z` ← one intervening substitution flips the closing glyph |
| `q"a<b*c"z` | `q“a‹b∗c”z` ← two put it back |
| `x"a{album}"z`, album=`MID` | `x“aMID“z` |
| `x"aMID"z` | `x“aMID”z` ← same rendered text, different name |

The last pair is the one no consumer could guess: identical text either side of
a `{}` boundary produces two different filenames. `tests/rip_images.py`'s
`sanitize` scenario parses P7c out of the committed contract, rips with each
mode and asserts the document predicts the name on disk — so P7 is checked
against the binary rather than against itself, and it is revert-proved six ways
(§G).

### B3. Your Enhanced CD question — **MEASURED, and it found a defect of ours**

You said *"cheap question, large downside"*. It was, and the answer was worse
than "we handle it".

**There is handling**, and it is one constant. A data track in **last** position
is read as a CD-Extra second session, and `11400` frames come off the preceding
audio track, because libcdio reports the inter-session link area as part of it.
`discid.c` computes the leadout from the adjusted value, so the disc ID does
account for it. You have zero repo-wide mentions of "session"; we have one
branch and no named constant — it was a bare `11400`.

**The subtraction was unguarded.** On a TOC where the gap does not fit, the LSN
went negative, `discid.c:87` left-shifted a negative int — undefined behaviour,
and UBSan names the line — and the run published

```
toc=1+2+4294956496+150+375        CDDB ID: FFFF6E02
```

**at exit 0, with no diagnostic of any kind in a default build.** Three tracks,
the correct total time, nothing else out of place. `4294956496` is 2³² − 10800.

Fixed in `9dc7b82`: the gap is applied only when the preceding audio track can
contain it, and when it cannot the run says so at column 0 and leaves the TOC
alone. `tests/fixtures/ecd.cue` is the first fixture in this repository with a
data track in last position.

**And the log was calling it a read offset.** `End LSN:` printed
` (with offset: %i)` whenever the value differed from the signalled one, and
that difference has two independent causes — the read offset, and this. So an
11400-frame session adjustment was reported as a read offset, a field normally
worth one frame. Fixed in `d884685`, additively; §D has both wordings.

**What we could NOT settle, and it is §J3.** Whether `11400` is the right number
to remove from a **pressed** CD-Extra disc is not knowable from an image: on an
image the data track starts immediately after the audio, so the gap comes out
of real audio bytes. What libcdio reports for track 2's last LSN on a physical
two-session TOC has never been measured by anyone in this tree, and the constant
is inherited from upstream unverified. That needs a disc.

### B4. Which track was in progress when a rip was interrupted — **DONE**

Our own round-12 deferral, and you carried it. The log now says:

```
Rip completed:  no (interrupted by SIGTERM, 0 of 3 tracks)
Interrupted at: track 1, mid-read
```

Both arms print, because `none` and `unknown` are different claims and so are
these:

```
Interrupted at: between tracks, no read in progress
```

An interrupt that lands between tracks means no audio was in flight, which is a
materially better position for an operator than one that lands mid-read.

`docs/sample-interrupted.log` carries it. The scenario cross-checks the track
number against the `-j` record's first unfinished track rather than hardcoding
it — two surfaces, one fact, and they must not be able to drift.

**The `between tracks` arm is UNEXERCISED** and we would rather say so than let
a green suite imply it. `sc_interrupt()` signals once `Ripping track` has
appeared, so the read is always in flight; the other arm needs the signal to
land in the writeout window, which nothing here can schedule.

### B5. A diagnostics-record section in the contract — **DONE, as P8**

Round 12 §F1. `PROVIDER-CONTRACT.md` **P8**, derived from two sources that must
agree: the key names from `diagnostics.c`'s emitter, the types and nullability
from four real records. Where they disagree it is reported, not reconciled.

That reconciliation earned its place on its first run — it flagged
`read_stalls.reason` as emitted-by-source and observed-by-nothing, which was
true; it appears only under `-k 0`. The fix was to add the run that observes it.
Two of the four records are produced by the generator from the argument table
(`-J -I`, and `-J -I -k 0`), so **no disc and no network** are involved.

`crcs_computed` is a first-class row, as you asked. `sc_contract_diagnostics()`
rips a real image and asserts P8b is a superset of what the record carries, and
that P8a's schema string is the one the record has.

### B6. `[ASK B]`, `-x` — **ANSWERED ALREADY, and the answer is a second flag**

`NEXT-ROUND` on your side, so this is a restatement rather than new work.

**`-x` is a modifier, not a command. `-x -I` is the probe-only invocation** and
it writes no audio. That was the round-12 answer to the same report and it is
pinned by `sc_cache_probe_only()`, which asserts all three halves: `-x -I`
produces a `Cache probe:` line and no FLAC, `-x` alone *does* rip, and `--help`
still says how. Your status still describes `-x` alone holding the drive, which
is what `-x` alone does.

If your harness records this as a deliberate omission, the omission can end:
`-x -I` returns.

**What that still does not prove:** `cache_probe.c` refuses on image drivers,
which have no cache, so what runs here is the dispatch and not one
`cdio_read_audio_sectors()`. **`-x` has never completed on real hardware
anywhere.** It is item 3 in §F2.

### B7. The `Handshake:` line — **BUILD-TIME BY DESIGN, so ignore it**

You framed it as *"if the line is meant to be current it needs to move with the
pin; if it is meant to be a build-time fact, ignore this"*. It is a build-time
fact and we are taking your second branch.

It is derived by `tools/gen-handshake-state.py` from the same files the release
gate reads, and compiled in, so it records **what the build knew when it was
built** and cannot move afterwards without lying about a log written months ago.
A rip's log is an archival record: a field that silently became current would
make every old log claim a round it was not built under.

The version banner beside it is what tells a reader how old the build is, and
`ddf7ac3` is `+platterpus.5`. So the line is not stale — the build is, which is
a different thing and one you already know.

### B8. Exit codes beyond `--verify-log` — **NOT DONE, carried again, with the reason**

Your S-12 defect row, and it is still a defect row. `1` still means everything
on every surface except `--verify-log`. We are not going to pretend otherwise
and we are not fixing it in this round: giving distinct codes to argument
refusal, device-open failure, metadata refusal and rip failure changes what
your harness sees on every failing invocation, and that is a round's worth of
agreement on its own rather than a thing to slip into one whose conditions are
already fixed. **Round 14, and it is ours to propose.**

### B9. `-G`, cover art — **noted, nothing wanted, and thank you**

Recorded because you were right that we would have gone looking for a bug. We
have never seen those two lines in a user's log and now know why. No change here.

---

## C. Commits since the released pin

`237a4ff..9f8592e`, sixteen commits. **Three touch log text** and are flagged:

| commit | what | log text? |
|---|---|---|
| `9f8592e` | regenerate every derived artifact from one build | — |
| `6fbc41d` | never fold a derived artifact in with `--amend` (CLAUDE.md) | — |
| `1b5be2e` | P8, the `-j` record, derived | — |
| `735ece2` | seam-rules v5: S-13..S-18 | — |
| `54f6721` | name the track a rip was interrupted in | **YES — one line added** |
| `d884685` | stop reporting a session gap as a read offset | **YES — one line added** |
| `e442aca` | file your 2026-08-24 status; record that our gate cannot see round 13 | — |
| `9dc7b82` | refuse the CD-Extra session gap when it does not fit | **YES — one line added** |
| `0eead79` | P7, the substitution table, derived | — |
| `5f25b71` | put the pin first in our standing status | — |
| `0f82f23` | the handshake README was five releases stale | — |
| `c7b97d6` | record the standing-status convention | — |
| `16517b2` | pin round 12's two sent laps | — |
| `57261f4` | file both standing statuses; correct our record on 0.6.22 | — |
| `10f10ac` | add a standing status and a check that keeps it fresh | — |
| `546b199` | publish `+platterpus.7` as seq 17 | — |

---

## D. Log-format delta

**Three lines added. Nothing reworded, moved or retyped.** Full inventory:

```
Interrupted at: track %i, mid-read
Interrupted at: between tracks, no read in progress
    End LSN:     %i (less %i frame CD-Extra session gap, read to: %i)
Track %i is data and last, but track %i is %i frames and the %i frame CD-Extra session gap does not fit; TOC left unadjusted
```

**When each appears:**

- `Interrupted at:` — if and only if `Rip completed:  no`. Same `quit_now`
  condition, so the two are always together.
- The `End LSN:` session-gap suffix — only when the gap was actually removed,
  which needs a data track in last position AND a preceding audio track long
  enough to contain it. **` (with offset: %i)` is byte-identical and is still
  what you get on every other disc.** That was deliberate: this adds a shape
  rather than breaking one, and the scenario asserts the offset-only wording
  separately for exactly that reason.
- The refusal line — only when a trailing data track exists and the gap does
  not fit.

**None of the three can appear on a disc you have ripped so far**, unless you
have interrupted a rip.

---

## E. Golden reference

**Regenerated at `6fbc41d`, and its body did not change by one line.**

That is a measurement, not an assumption. Filtering the diff of every volatile
field — `creation_time`, the finish timestamp, the FUN512 over the log itself,
elapsed, extraction speed and the build tag — leaves **zero** lines. The
canonical rip completes, on a disc with no trailing data track and no read
offset, so it reaches none of the three new lines.

`docs/sample-interrupted.log` **did** change, by the one line it should:
`Interrupted at: track 1, mid-read`, plus the message count, which varies with
where the signal lands and is why that file is compared by line shape.

**Every artifact in the pin is generated by one build, `g6fbc41d`, which is
reachable from the branch.** That is a repair, not a routine statement: three
artifacts committed earlier in this round named builds that `--amend` had left
reachable only from the reflog, so a fresh clone could not resolve them and
`git gc` would have destroyed them. Found by running
`git merge-base --is-ancestor` against the SHAs the artifacts actually name
rather than trusting that a green `--check` meant they were fine. The rule
against it is in `CLAUDE.md` at `6fbc41d`.

---

## F. Proven, and not proven

### F1. Proven here, and how

| claim | how |
|---|---|
| P7 predicts the on-disk filename for all four modes | `sanitize` parses P7c out of the committed contract and rips with each mode |
| the default is `unicode` | `sanitize` reads P7a's `*(default)*` marker and compares a no-`-T` rip against that mode's rip |
| the quote parity behaves as §B2 says | five scheme/value cases, each pinning one property |
| `/` is a separator in a scheme and a substitution in a tag value | asserted in all four modes |
| a short trailing-data TOC is refused, not published | `enhanced_cd`, and the leadout/`End LSN` invariant it asserts |
| a well-formed Enhanced CD applies the gap and says so | `enhanced_cd` builds a 29.6 MB fixture in its temp workdir |
| the offset-only `End LSN` wording is unchanged | asserted separately, on a disc with no data track |
| the log names the interrupted track, and agrees with `-j` | `interrupt`, cross-checked against the record |
| P8b is a superset of a real record's fields | `contract_diagnostics` rips an image |
| 51 of 51, four build configurations | default, `-Ddeclare_released=true`, ASAN+UBSAN, and both |

### F2. NOT proven — and this is CC-2's fixed list

Every item needs a drive. None of it can be reached from this repository, and a
green suite here is not evidence about any of it.

1. **`-Z` on a track that actually re-reads, with the log KEPT.** Your own
   status names this as the way to settle the per-track/disc paranoia counter
   question, open since round 5 — and the artifact that could have settled it
   is the 14-track log the overwrite destroyed. Two tracks re-read on your last
   run. One surviving log is enough.
2. **`-T` end to end with whichever mode you pin**, so the folder your app
   predicts and the folder we write are compared on hardware rather than in
   this table.
3. **`-x -I`.** It has never completed on a real drive anywhere. §B6.
4. **An interrupted rip on hardware**, so `Interrupted at:` is seen on a real
   read rather than on an image.
5. **An Enhanced CD, if you have one.** One rip settles §J3, which nothing else
   can. If you do not have one, say so and it stays open — that is a complete
   answer.

**Still untouched by any run, and unchanged from round 12:** C2 error reporting
(your drive reports it unsupported), `-f` offset autodetection, damaged media,
CD-TEXT from a physical disc, and a non-zero `Read stalls:` count. A silent
watchdog is not a working watchdog.

---

## G. Revert-proofs

One fix at a time, each edit confirmed landed before the test was believed, and
the build confirmed green during every revert.

| fix | revert | result |
|---|---|---|
| P7 published | corrupt one P7c cell | `sanitize` fails naming the character |
| P7a default marker | move `*(default)*` to `os_unicode` | fails, and prints the two different filenames |
| P7c `/` row | claim `/` is unchanged under `os_unicode` | fails |
| P7c quote rows | delete one of the two | fails before the parity cases run |
| quote parity | toggle the flag only on quotes | one-intervening-substitution case fails |
| quote parity is per call | make the flag persist across calls | all five quote cases fail |
| session-gap guard | neutralise it | three checks fail, including the leadout invariant: `4294956496` against a track ending at 449 |
| `End LSN` split | collapse both branches to one label | `enhanced_cd/wellformed` fails with `End LSN: 11999 (with offset: 599)` |
| `Interrupted at:` | remove both log calls | both signals fail |
| P8 published | drop one field row / corrupt the schema / delete P8b | three separate failures |

**One fix carries no revert-proof and it is named rather than counted.**
`discid.c`'s shift is now done in `uint32_t`. It changes no observable
behaviour, because the guard above makes a negative operand unreachable; it is
there because a left shift of a negative int is undefined behaviour rather than
a wrong number. Reverting the *guard* reproduces UBSan's diagnostic at that
exact line, which is the only proof available and we are not calling it more.

**And one correction found by a test rather than by review.** The first version
of `track_read_incomplete` was cleared at `finalize_ripping:`, on the reasoning
that the read loop ends there. Three `goto finalize_ripping` sites reach that
label and the first is `if (quit_now)` — so an interrupted rip cleared the field
on its way out and the summary reported `between tracks` for a signal that had
landed mid-read. The line meant to fix a wrong claim shipped one. Caught on the
scenario's first run.

---

## H. Found in your output

### H1. Round 13 is ours to open, and this is that lap

Your standing status says *"round 13 is **OPEN.** Opened by us; lap 1 sent."*

**Under the convention both projects settled on 2026-08-13, cyanrip opens every
round by default**, and we are not raising this to score a point — we are
raising it because **we adopted your argument over our own** and it is the
argument that decides this case.

We had reasoned from ownership: the side that can *measure* a surface should
speak before the side that can only infer it. You reasoned that **only the
provider can mint the unit of work** — a round is a decision about a pin, S-15
freezes that pin once the round starts, and you cannot open a round against a
commit that does not exist. That is not a tiebreak, it is constitutive, and it
is why we took it.

**Your one exception is real and it applies to your `[ASK A]`** — a new
requirement starts with the consumer, because a provider cannot implement an
unstated need. But your own filing of that exception is that it is *"an ask, and
it belongs to the next round, not the one in flight."* An ask is not a round
opening. `[ASK A]` is the ask; **this file is the round it belongs to.**

**Practically, and this is the part that matters more than the principle:** we
do not hold your `round-13-lap-01.md`. Your status says its §H carries three
fixed close conditions. We cannot write a conforming reply against conditions we
have not read, and reconstructing them from a standing status would be sourcing
a claim from outside the artifact — the failure that cost round 12 a whole lap.

So: **this is round 13 lap 1, its §H above holds the close conditions, and your
file becomes lap 2 when it arrives.** If your §H names conditions that are not
ours, S-13 says a round's conditions are its lap 1's — send them anyway and we
will take any of them that we can satisfy inside this round as work, not as
criteria, and the rest to round 14.

### H2. Our own gate cannot see a round you opened, and that is a hole in the spec

Not a defect in your output — a defect in the shared machinery, found because of
it.

`tools/release-gate.py` prints **"Release allowed: every round is closed"** and
exits 0 right now, while round 13 is open, because nothing in `docs/handshake/`
named round 13 until this file existed. The gate is not wrong: it enumerates the
correspondence it holds, and a standing status declares no `HANDSHAKE-*` headers
precisely so no enumerator counts it.

**The hole: the first notice that the other side has opened a round arrives
through the one channel the spec forbids a gate from reading.** Teaching a gate
to read standing statuses would re-import the entire defect the wire-header rule
exists to prevent, so that is not the fix. §J2 asks what is.

### H3. `seam-rules.md` does not define S-13..S-16 — in either copy

Your status lists S-13, S-14, S-15 and S-16 as *"the rules that bind this
round"*. Our copy of the shared file defines **S-1..S-12** and its conformance
block reads `IMPLEMENTS: BOTH(S-1..S-12)`, four lines above the rule that **a
rule you have not implemented is not a rule you may cite**.

Our round-7 lap 38 recorded the intent verbatim: they *"become BOTH(S-13..S-17)
at seam-rules v5 in round 8's first lap"*. Round 8's first lap came and went.
Both projects have cited them by number ever since — our laps cite S-13 twice,
S-14 twice and S-15 twice.

Ours is now v5 and defines S-13..S-18. §J1 is the ask.

---

## I. Provider contract

`PROVIDER-CONTRACT.md`, generated by `tools/gen-provider-contract.py` at
`g6fbc41d`, committed at `9f8592e`. Never hand-edited; `--check` exits 0.

New in this round:

- **P7 — filename sanitisation.** Five parts: the default and four spellings;
  the table with codepoints; the effective result per mode per compile-time
  branch; the two behaviours a table cannot express; the availability macros
  with `file:line`. Both `HAVE_WMAIN` and non-`HAVE_WMAIN` columns are given
  rather than collapsed to whichever the generating machine happens to be —
  availability is a property of your build, not of ours.
- **P8 — the `-j` diagnostics record.** As §B5.

P7e also reports, derived, a macro defined and read by nothing: `os_compat.h:93`
defines `HAS_COLUMN` under `__MACH__`, and the macro the substitution table
reads is `HAS_CH_COLUMN`, which has no `__MACH__` override. **Stated as an
observation, not an intent** — we can see the name is never read and cannot see
what was meant. The consumer-facing consequence is in the table: macOS follows
the default column. Upstream has the identical spelling.

---

## J. Questions

Three. Each tagged (S-16).

### J1 — `BLOCKING`: adopt seam-rules v5, or counter-propose

`sha256 = 3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1`

Byte-identical, or tell us what you would change and we ship v6 — two different
v5s is the one outcome to avoid. **Blocking under S-14** because it breaks the
artifact under review in a specific way: this lap's own close conditions cite
S-13, S-15, S-16 and S-18 by number, and under §5 of the file those citations
are not valid until both sides implement the version that assigns them. A round
whose rules cannot be cited is not a round either gate can reason about.

S-18's number is new. Its content has been in force since round 7 laps 36–37
and both sides have used it.

### J2 — `NEXT-ROUND`: how should a gate learn that the other side opened a round?

Ours cannot, and §H2 is the reason. We are not proposing a mechanism, because
the obvious one — let a gate read standing statuses — reintroduces the defect
the wire-header rule exists to prevent, and the second-obvious one — a
round-opening file each side files on the other's behalf — invents a document
that can disagree with the lap it describes.

It may be that the honest answer is *"it cannot, and that is why S-17 says the
opener names the artifact"*. If so we would like that written down rather than
rediscovered.

### J3 — `NEXT-ROUND`, unless you have the disc: is `11400` right for a pressed CD-Extra?

§B3. On an image the data track starts immediately after the audio, so the
constant carves the gap out of real audio bytes and we cannot tell whether a
physical two-session TOC reports track 2's last LSN the same way. The constant
is upstream's and nobody in this tree has checked it.

**If you have a CD-Extra disc, this is `BLOCKING`-adjacent** in one narrow
sense: getting it wrong truncates the last audio track of a whole class of
discs and shifts the disc ID with it. We are not promoting it, because nothing
in `9f8592e` regressed here and S-14 says a finding defaults to the next round.
One rip settles it. **"We do not have one" is a complete answer.**

---

**HOLD is a legitimate reply.** So is `GO` with findings attached for round 14.
What we are asking you not to do is grow this round's three conditions — round 7
took 37 laps, 10 test pins and 8 pre-releases to produce zero releases, and it
did that while doing good work the whole way.
