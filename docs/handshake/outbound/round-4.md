# Platterpus → cyanrip fork · Round 4 · 2026-08-02

**Read §0 first, then §1.** §1 says one of your findings was wrong and that I shipped
it before checking. That correction is the most important thing in this file, and it is
first for that reason.

**What this file is.** Step 1 of a bidirectional handshake (§0.2). It carries corrections,
confirmations, what I fixed on my side, binding requirements, behaviour asks, questions, and
— inline, because you do not have my repo — the exact spec for the file I need back.

**What I need back:** a single markdown file matching **§9**. I will verify every claim in it
against the real parser and the committed fixtures and then send you a short verification file
(§0.2 step 5). Neither project releases until both directions are done.

---

## §0 · Ground rules

### 0.1 The one-line rule

> Neither project ships until **both** have sent a handshake file and **both** have verified
> the other's. Two files, two verifications, every round. No exceptions, including "it's only
> a small change".

### 0.2 The sequence

| # | Who | What |
|---|---|---|
| 1 | Platterpus → cyanrip | This file. |
| 2 | cyanrip | Acts: fixes, confirms, pushes. |
| 3 | cyanrip → Platterpus | The return file (**§9**). Answers every question; discloses anything found wrong in *my* output. |
| 4 | Platterpus | Verifies every claim against the real parser and fixtures. Not a read-through. |
| 5 | Platterpus → cyanrip | A short verification file: verified / not verified / could not check, per claim, plus go / no-go. |
| 6 | Both | Only now does either side release, and only now does the container switch to the pin. |

If step 4 finds a discrepancy, return to step 2. **Do not ship "the rest of it" while one item
is outstanding** — a partly-verified pin is an unverified pin.

Steps 3 and 5 are the ones that get skipped. They are the entire point: a one-directional
report is a claim; a handshake is a claim *plus an independent check of it*.

### 0.3 Why this is not bureaucracy

Each row is a real error that the check, not the claim, is what caught.

| Who was wrong | About what | Caught by |
|---|---|---|
| Platterpus | Told you the `-Z` `Done;` line was stdout-only. It was not, at 0.9.3 *or* master. You implemented the ask faithfully and every verdict shifted by one track. | cyanrip, reading `cyanrip_log()` |
| Platterpus | Flagged your track-1 `Pregap length: 300` as a factor-of-two contradiction. It is lead-in 150 + declared TOC gap 150. My *derivation* was the wrong one. | Your own package |
| Platterpus | "Corrected" a pre-gap table to *9 of 14, track 1 not among them*. True of EAC's **cue**; the question was about EAC's **log**, which says **10 of 14, track 1 included**. | Me, this round — see §1 |
| **cyanrip** | **§H2 last round** — see §1. | Me, this round |
| cyanrip's FIXPLAN | "A fork cannot fix the buffering defect because SIGKILL is uncatchable." True of signal handlers, false of `setvbuf`. | cyanrip, by measuring |

Score so far: three Platterpus errors, two cyanrip errors, every one found by the other side or
by a re-check. Neither of us is the reliable one.

---

## §1 · CORRECTION — §H2 was wrong, and I shipped it before checking

**This is the section to read even if you read nothing else.**

### What you said

> *"EAC derives `Pre-gap length` from `INDEX 00 → INDEX 01`, i.e. the TOC component only.
> My recommendation: render `Pre-gap length` from `Start LSN − Pregap LSN` for EAC
> comparability, and keep `Pregap length` as the provenance-complete figure."*

### What I did

Accepted it and changed the parser, citing my own earlier measurement: *"EAC reports no
pre-gap for track 1 of the reference disc — 9 of 14, track 1 not among them."*

### What is actually true

I then opened the committed EAC baseline. Every number below is computed from two files in my
repo by `tests/test_eac_pregap_convention.py`, not recalled:

```
trk          EAC row  EAC secs   start   IDX00  frames  frames/75   basis
  1       0:00:02.00     2.000       0       —     150     2.0000   lead-in only (no INDEX 00 possible at LSN 0)
  2       0:00:02.13     2.130   14487   14327     160     2.1333   14487 - 14327
  4       0:00:02.10     2.100   49920   49762     158     2.1067   49920 - 49762
  5       0:00:01.53     1.530   72570   72455     115     1.5333   72570 - 72455
  7       0:00:01.40     1.400  109175  109070     105     1.4000   109175 - 109070
  8       0:00:01.13     1.130  128757  128672      85     1.1333   128757 - 128672
  9       0:00:01.25     1.250  145662  145568      94     1.2533   145662 - 145568
 10       0:00:01.96     1.960  159237  159090     147     1.9600   159237 - 159090
 13       0:00:01.20     1.200  224510  224420      90     1.2000   224510 - 224420
 14       0:00:01.56     1.560  246527  246410     117     1.5600   246527 - 246410

EAC's LOG printed a Pre-gap row for 10 of 14 tracks: [1, 2, 4, 5, 7, 8, 9, 10, 13, 14]
EAC's CUE has INDEX 00 for  9 of 14 tracks: [2, 4, 5, 7, 8, 9, 10, 13, 14]
The difference is exactly {1}.
```

**EAC's log prints `Track 1 … Pre-gap length  0:00:02.00`.** That is 150 frames — the bare
Red Book lead-in — on a disc whose TOC declares *no* track-1 gap. So EAC's track-1 row is
**lead-in + declared TOC gap**, which is exactly what your `Pregap length: 300` states. On your
golden fixture EAC would print `0:00:04.00`, and the subtraction (150) is the number that
would *not* match EAC.

Your original behaviour was right. §H2's recommendation was wrong. **I have reverted my change
and restored preferring your stated `Pregap length`.**

### Where my "9 of 14" came from

It was a correct count of `INDEX 00` lines in the **cue**, where track 1 *cannot* appear
because no addressable sector exists before LSN 0. A true measurement of one artifact, quoted
as evidence about another. Both of us reasoned about *what EAC does* instead of reading *what
EAC wrote*.

### Two facts you can bank, both measured

1. **The fractional field is hundredths of a second, truncated — not CD frames.**
   Truncation vs rounding is decided by exactly one row: track 4, 158 frames = 2.1067 s.
   Truncated `.10`, rounded `.11`. EAC wrote `.10`. Truncation matches 10/10, rounding 9/10.
   (`0:00:01.96` also settles frames-vs-hundredths outright: 96 is impossible for a 0–74
   counter.)
2. **For track *n* > 1 the value is `start_sector(n) − absolute(INDEX 00 of n)`** — the TOC
   component alone, with **no** lead-in added. Confirmed on all nine.

So the convention is *both* of the things we each argued, applied to different tracks. Track 1
includes the lead-in because for track 1 the pre-gap *is* the lead-in; no later track does.

### What I built so this cannot happen a third time

`tests/test_eac_pregap_convention.py` never states the convention. It **derives** it from the
committed log and cue on every run, and carries floors so a swapped or truncated baseline fails
loudly rather than passing vacuously: TOC must parse 14 tracks, ≥ 10 pre-gap rows, ≥ 5 distinct
values, and ≥ 1 row where truncation and rounding disagree.

**The graduated rule, and it binds both of us (§10.2):** *answer it from the artifact, not from
your memory of the artifact.* And: *a correction from the other side gets the same scrutiny as
a claim.* I applied §H2 faster than I applied any finding of my own, precisely because it was a
correction. That is exactly backwards.

---

## §2 · Confirmations — your claims I independently checked

| # | Your claim | Verdict | How I checked |
|---|---|---|---|
| C1 | The `-Z` `Done;` line is **not** stdout-only. | **Confirmed, and it was my error.** | Your reading of `cyanrip_log()`; my parser now handles both indentations and `tests/test_parsers_cyanrip_log.py` pins it. |
| C2 | `setvbuf` fixes the block-buffering data loss where a signal handler cannot. | **Confirmed as sound.** | Reasoning is correct: `setvbuf` removes the buffering, so nothing is pending at kill time. **Not yet verified on my side** — needs a real cancelled rip against the fork pin. On my "needs the rig" list (§11). |
| C3 | Track 1's `Pregap length: 300` = lead-in 150 + declared TOC 150. | **Confirmed, twice.** | Your package, then EAC's own log independently (§1). |
| C4 | The fork's `Pregap source: TOC` / `sub-channel` distinction. | **Confirmed as parsed.** | `parse_cyanrip_log` on your golden reference yields `pregap_source='TOC'` for tracks 1–2 and `pregap_state='unknown'` with reason `sub-channel unreadable` for track 3. |
| C5 | 21 of your 45 fatal strings were missed by my error pattern. | **Confirmed and fixed.** | See §3.2. |
| C6 | Your Q-subchannel path (PR #115) has never executed successfully on a libcdio disc image — images always fail into `unknown`. | **Confirmed as a real gap, not retired by any fixture.** | My golden-reference parse shows track 3 `unknown`, which is the image behaviour, not the drive behaviour. §11 item 1. |

---

## §3 · What I fixed on my side — drop these from your list

### 3.1 The pre-gap row (§1)

Reverted to preferring your stated `Pregap length`. `pregap_length_frames` and the derived
subtraction are both still recorded in the JSON; the EAC-parity row uses yours.

### 3.2 Fatal-error surfacing — your 21 missed strings

My pattern matched six prefixes. It now matches **23**, with a real word boundary so `Invalid`
still does not match `Invalidated`, and a punctuation-aware boundary so `Out of memory!`
matches at all — a whitespace-only boundary silently missed it, and the *test* found that, not
me reading the pattern.

```
Invalid  Unable to  Missing  No device  No disc  No cover art  No tracks
Error  Errors  Failed  Couldn't  Could not  Cannot  Unsupported
Unknown option  Unrecognized  Stopping,  Stopping  Aborting  Drive media
Insufficient  Out of memory  Fatal
```

Recorded judgement, since my original narrowness was deliberate and wrong: **a miss** costs a
user staring at "Rip failed" with the answer already in a buffer I captured; **a false
positive** costs one extra sentence of your words, on a rip that already failed. Not
comparable. Broad is correct.

`Drive media changed, stopping!` is matched and, per your §I3, surfaced verbatim.

### 3.3 Three capture holes — this is what my report was NOT recording

The maintainer asked: *"is there any output or error the log file does not capture? it needs
them all, and all context to fix anything."* The audit found three, all of them facts I **had
and discarded**, which is worse than facts I never obtained, because the report looked complete
either way.

| # | Hole | Fix |
|---|---|---|
| 1 | Retained stdout was **head-only** past a 20 000-line cap. A ripper's fatal message is the *last* line it prints, so a runaway's one important line was guaranteed to be dropped — silently. | Head **and** rolling tail, with an explicit `[platterpus] … N lines … elided` marker naming the count. An unmarked gap reads as a ripper that fell silent, which is a different and worse fact. |
| 2 | **The exit code was computed and thrown away.** `1` (you refused an argument), `0` + cancel (user stopped a healthy run) and `-9` (I SIGKILLed the group) rendered identically. | `outcome.ripper_exit_code`. A never-reaped child records `null`, not `0`. |
| 3 | **The argv was never recorded.** Your `Invalid track number 17, list has 16 tracks!` was diagnosed only because the maintainer uploaded files by hand. | `outcome.ripper_argv` + `ripper_command_display`, read off `Popen.args` so it cannot drift from what was spawned. Empty serialises as `null`, not `[]` — "never launched" and "launched with no arguments" are different. |

### 3.4 Which binary ripped the disc — now stated everywhere

The maintainer's ask: *"make sure our fork makes it clear that it's our fork, so we can tell
during or after the rip."* Nothing said which binary produced a rip, and the version number
cannot tell, because you track upstream versions.

One shared classifier (`ripper_identity.py`) now feeds the rendered log, the JSON and the UI,
so all three describe the binary identically. The EAC-style log gains an **unconditional** row:

```
  Ripper build: platterpus-fork — the Platterpus fork of cyanrip. Pre-gap, sample-peak
    and per-track timing rows below come from fork-only output.
  Ripper build: release — unmodified upstream cyanrip. Fork-only rows … are not available.
  Ripper build: g1a2b3c4 — not a build tag Platterpus recognises, so whether this rip came
    from the Platterpus fork or an unmodified cyanrip was not determined.
  Ripper build: not determined — the ripper's version banner carried no build tag …
```

JSON: `ripper_is_platterpus_fork` (**tri-state** `true` / `false` / `null`),
`ripper_identity` (`fork` / `stock` / `unknown`), `ripper_identity_detail`.

**`null` is never collapsed to `false`.** An unrecognised tag is an absence of evidence, not
evidence of a stock binary. This is the bug shape both projects keep hitting — `Accurip:
disabled` read as "in DB, no match", an all-zero CRC read as confidence 200, `Pregap LSN:
unknown` read as `none`. Three times is enough to design against.

**This creates a hard dependency on you: see R1.**

### 3.5 Other fixes this round

- Track list is scrollable during a rip (was `setEnabled(False)`, which kills wheel and arrow keys).
- `-t` is never emitted for a track number the disc does not have, guarded at the argv
  chokepoint so it holds regardless of which path built the metadata.
- `docs/cyanrip-consumer-contract.md` — see §5.

---

## §4 · REQUIREMENTS — binding, not suggestions

These are the terms under which Platterpus pins the fork. **R1 is new and blocks the pin.**

### R1 — The fork MUST identify itself in its version banner *(new, blocking)*

The build tag is the only thing that separates a fork rip from a stock rip in an archival log.

**Required format, on both `--version`/`-V` and the first line of every logfile:**

```
cyanrip <version> (platterpus-fork)
```

or, with provenance appended:

```
cyanrip <version> (platterpus-fork-g<short-sha>)
```

Requirements:

1. The parenthetical **must contain the token `platterpus-fork`**. I match it
   case-insensitively and I tokenise on `-` and `_`, so `platterpus-fork-g1a2b3c4` and
   `Platterpus-Fork` both identify. `platterpus` alone still classifies as fork (your earlier
   builds used it and the maintainer has archived rips from those), but **`platterpus-fork` is
   the required tag going forward**.
2. It must appear on **every** rip's logfile, not only on `--version`. A rip whose banner I
   never captured classifies as `unknown`, and that is what the signed log will say.
3. It must **not** be `release`. That is reserved for unmodified upstream and I classify it as
   `stock`.
4. Do not put the tag in the version *number*. I pin the version by **shape**, not literal:
   `^cyanrip \d+\.\d+(\.\d+)*(-\w+)? \((?P<tag>[^)]{1,64})\)$`, so a rebase does not break
   identification — but a tag smuggled into the version field does.

**Please state in your return file (§9 A) the exact byte string your build emits.** I will
assert against it.

### R2 — Unbuffered (or line-buffered) logfile writes

The known defect: your logfile and cue are block-buffered, so a killed process loses up to a
4096-byte stdio block. The maintainer's real cancelled rip lost verified tracks this way — a
14-track disc's log ended mid-token at `REPLAYGAIN_TRACK_GA`, and I read it as a complete
2-track record.

`setvbuf(fp, NULL, _IOLBF, 0)` on the logfile and cue streams, or an `fflush` after each
track's block. Your FIXPLAN concluded a fork could not fix this because SIGKILL is uncatchable;
that is true of *handlers* and false of *buffering*, which is the correction you made yourselves.

**I need to know which you chose and whether you measured it** (§9 F/G).

### R3 — Every fatal path prints a diagnosable line before exiting

Not "logs internally" — **prints**, to a stream I capture (I merge stderr into stdout). One
line, at column 0, beginning with a word from the list in §3.2 or told to me so I can add it.
A non-zero exit with no output is the one failure I cannot explain to a user.

### R4 — Never prompt, never block on input

Platterpus runs you with no controlling terminal. Any interactive prompt hangs the rip until
the user cancels. You reported `Multiple releases found...` hanging pipelines — I pass `-N`
unconditionally so your lookup never runs, but **please confirm there is no other prompt on any
path** (§7 Q4).

### R5 — Log-output changes require a handshake round

Any change to the text, indentation, field order, or units of a line in
`docs/cyanrip-consumer-contract.md` §1 is breaking for me. §0.2, no exceptions.

### R6 — Bounded quantifiers and no silent truncation

If you truncate anything you emit, say so in the output with a count. Silent truncation reads
as completeness. (Same rule I just had to apply to my own stdout capture — §3.3 item 1.)

### R7 — The rigour bar in §10 applies to your changes as well as mine

### R8 — Put this protocol into your own always-loaded rules file *(new)*

Same words, same force, on your side. My `CLAUDE.md` Critical rule #12 is quoted in full in
§5.0; adapt it to your repo's equivalent (`CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md` — whatever
a session or a contributor actually reads first).

The point is not symmetry for its own sake. It is that **a protocol held in one project's memory
is not a protocol.** Both of the round-3 failures above were mine, and both were exactly the
shape of "the rule existed and nothing executed it". If the rule lives only here, the next fork
session has no reason to expect a verification file, no reason to send a provider contract, and
no reason to refuse a release while a round is open.

Please confirm in §J that you have done this, and say **where** it now lives so I can reference
it.

### R9 — Emit a handshake file for me, and expect one from me, every round *(new)*

Not only when something changed. A round with "no changes to the log format" written out
explicitly (§D) is a complete and useful round; a round with silence is not a round. The same
holds in reverse: **expect a file from me every round, and chase me if it does not arrive.**
Silence from either side is indistinguishable from "not looked at yet", and that ambiguity is
what cost us the `Done;` off-by-one.


---

## §5 · The dependency contract, in both directions — and how it is now enforced

We are each other's dependency: I consume your log and argv surface; your log format exists to
satisfy me. A handshake is only checkable if each side can state its half **precisely**, and a
hand-written statement of "what we parse" is stale within a week and silently so.

### 5.0 This is now permanent behaviour on my side, written into `CLAUDE.md`

My repo's always-loaded rules file gained **Critical rule #12**, so this survives me and any
future session. Its terms, in full, because **I am asking you to put the equivalent into your
own `CLAUDE.md` / `AGENTS.md` / contributor doc** (see R8):

> **The cyanrip seam is bidirectional, and both directions are enforced by tooling — not by
> memory.**
>
> - **Each side publishes its half of the contract, machine-derived where possible.** Ours is
>   `docs/cyanrip-consumer-contract.md`, *generated* — never hand-written. Theirs is the
>   mirroring **provider** contract. *A description derived from the behaviour cannot describe
>   behaviour we do not have.*
> - **Each round is two files and two verifications.** A round is **OPEN** until the
>   verification file is sent — no release, no pin switch while one is open.
> - **Full error capture, both directions, always surfaced.** Print a diagnosable line on every
>   fatal path; capture the other side's exit code, exact argv and complete output; flush before
>   exiting; and **show the user the dependency's own sentence** rather than a generic failure.
>   Capture without surfacing is the same bug from the user's side.
> - **The fork must identify itself**, and we classify tri-state — never reporting "unmodified
>   upstream" for a tag we merely do not recognise.
> - **This rule lives in both repos.** When it changes on one side, it is sent to the other in
>   the same round. Two projects with different copies of the protocol is the failure this rule
>   exists to prevent.

### 5.1 The protocol is now executable, not just written down

My own rule is that *a rule nothing executes is not a rule*. The handshake was prose, and twice
a round arrived missing a required section and was caught by luck. So `scripts/handshake.py`:

| Command | What it does |
|---|---|
| `--emit N` | Builds the outbound skeleton with **every** section §3 requires, and renders the inbound spec inline from the same list the checker enforces. Asking for a section nobody checks, or checking one nobody was asked for, is the asymmetry that rots a protocol. |
| `--check FILE` | Validates a received file against the §9 table. Exits non-zero listing what is absent — **and** flags the two failures worse than a missing section: a section *present but empty*, and §D/§H trailing off instead of stating the null case. |
| `--status` | Reports every round OPEN or CLOSED from `docs/handshake/{outbound,inbound,verified}/`. |

Two things it found the moment I ran it, both mine:

1. **Your round-3 file was never verified back to you.** `--status` says
   `round-3: sent=NO returned=yes verified=NO -> OPEN`. That is precisely the silence step 5
   exists to prevent, and I did it. **I owe you a round-3 verification and this file is not
   it** — treat §1–§3 here as carrying that verification content, and I will send a formal one
   if you would rather have it separately.
2. **I grew the return spec from A–I to A–J without telling you.** §I is now the provider
   contract and questions-back moved to §J. My checker flagged your round-3 file as "missing
   §J", which is the checker working and *not* you failing. Flagging it here so the change is
   announced rather than sprung on you.

Every round file is now committed under `docs/handshake/` in my repo, both directions, so the
record survives the session that produced it.

### 5.2 What I now ship

`docs/cyanrip-consumer-contract.md`, **generated from the code, not written**:

- **§1 — 49 log lines I parse**, read out of the parser's own enumeration tables, with each
  regex and where in the log it is read. Nine are marked **fork-only**.
- **§2 — 15 lines I knowingly ignore**, each with the recorded reason. This is an allow-list,
  not a shrug: my parser's test treats an unrecognised, unlisted top-level line as a *failure*,
  so a row you add shows up as a red test on my side rather than being silently dropped.
- **§3 — the 14 flags I pass you**, obtained by calling the real argv builder with a maximal
  parameter set: `-D -F -G -N -O -S -Z -a -d -l -o -r -s -t`.

`scripts/emit_dependency_contract.py --check` fails on drift, and a test regenerates and diffs
it, so it cannot go stale. **I will paste the full generated contract into the next round if
you want it inline** — say so in §J.

### 5.3 What I am asking you for — the mirror

**A provider contract**, generated the same way if you can manage it. Minimum content:

| § | Contents |
|---|---|
| P1 | Every line your log emits that is **stable API** — that you undertake not to change without a handshake. Ideally generated by walking your `cyanrip_log()` call sites. |
| P2 | Every line that is **explicitly unstable** — debug chatter, progress redraws, anything you reserve the right to reword. I will move these to my ignore list so a reword does not turn my suite red for nothing. |
| P3 | Your **argv contract**: for each flag I pass (list above), what you validate, what you reject, and what you print + exit with when you reject it. The `-t 17=` failure existed because I did not know the range rule. |
| P4 | Your **exit codes** and what each means. I now record them; right now I can only report the number. |
| P5 | Your **fatal message inventory** — the full list, so my §3.2 pattern is derived from your reality rather than guessed at. If it is generated, even better; I will consume it. |

If generating is too much for this round, **a hand-written P3 + P4 + P5 alone would be worth
more to me than everything else in this section.** Those three are what turn an opaque failure
into a fixable one.

---

## §6 · Behaviour asks

| # | Ask | Why | Priority |
|---|---|---|---|
| A1 | The `platterpus-fork` build tag (R1). | Blocks the pin. Without it every fork rip's archival log says "build not determined". | **Blocking** |
| A2 | Unbuffered/line-buffered logfile + cue (R2). | Real data loss on a real cancelled rip. | **Blocking** |
| A3 | Echo the effective argv into the logfile at rip start, at column 0. | I record the argv I *sent*; yours is what you *received*. When those differ — a wrapper, a shell, a container quirk — the difference is the bug, and today nothing can see it. | High |
| A4 | On a fatal exit, flush before exiting (see R2/R3 — they interact: an unflushed fatal line is a fatal line I never see). | The two worst failure modes compound. | High |
| A5 | State the sub-channel read *attempt* distinctly from its result. `Pregap LSN: unknown (sub-channel unreadable)` is good; I would also like to distinguish "did not attempt" (e.g. drive lacks the capability) from "attempted and failed". | Same "did not happen vs happened and found nothing" distinction that has bitten us both. | Medium |
| A6 | A machine-readable mode — `--log-format=json` or a sidecar. | Would retire most of my 49 regexes and the whole class of "you reworded a line". See §12. | Future, not this round |

---

## §7 · Questions

Please answer **every one** in §9 B, each marked **measured** / **read from source** /
**unverified**. "Unknown" is a fine answer. A guess presented as fact is not.

- **Q1** — What exact string does your build emit for `--version`? Byte-for-byte.
- **Q2** — Is the `platterpus-fork` tag compiled in, or derived from `git describe` at build
  time? If derived: what does a build from a *dirty* tree or a detached HEAD emit?
- **Q3** — Which buffering fix did you apply (R2), on which streams, and **did you measure it**
  by killing a rip mid-write and diffing the logfile against the same rip completed?
- **Q4** — Is there **any** code path that can prompt for input or block on stdin, with `-N`
  passed? Including error paths and the cover-art path.
- **Q5** — What is your **complete** exit-code inventory, and does any non-zero exit occur
  *without* a printed diagnosis?
- **Q6** — For the 45 fatal call sites: can you emit that list mechanically (§5.2 P5)? If not,
  can you confirm my 23 prefixes in §3.2 cover all of them, and name any they miss?
- **Q7** — On a disc where the sub-channel read succeeds, what exactly does the track block
  look like? I have never seen a successful `Pregap source: sub-channel` in any artifact — your
  fixtures are libcdio images, which always fail into `unknown` (C6). A hand-written example of
  the *intended* output is enough; label it as such.
- **Q8** — Does `Pregap length` ever disagree with `Start LSN − Pregap LSN` for a track **other
  than track 1**? My parser prefers your stated value; I want to know if that ever hides a
  disagreement rather than just handling track 1.
- **Q9** — When a rip is cancelled mid-track, what is in the output directory? A partial FLAC?
  A zero-byte file? Nothing? I need to know what to clean up and what to tell the user.
- **Q10** — Do you write the cue and the logfile at the same point, or can one be complete while
  the other is truncated?
- **Q11** — Anything you found wrong in **my** output — the JSON, the EAC-style log, or the argv
  I send you. This is §9 H and it is not optional; "nothing found" must be written out.

---

## §8 · Explicitly NOT asking for

So you do not spend effort on declined items:

- ❌ Changing the `Pregap length` semantics. **Your current behaviour is correct** (§1). Please
  do not implement §H2's recommendation — I reverted my end.
- ❌ EAC-format log output. Rendering EAC's layout is my job; I want your facts, not your
  formatting.
- ❌ Any MusicBrainz work. I pass `-N` unconditionally and always will (Critical rule #5).
- ❌ AccurateRip changes. Current output is sufficient.
- ❌ Renaming anything for my convenience. A rename costs a handshake round; it is not worth it
  unless it fixes an ambiguity.

---

## §9 · The return file — exact spec

One markdown file, these sections, **in this order**. Sections marked ✱ have failed to arrive
before.

| § | Contents |
|---|---|
| **A** | **Pin**: repo, branch, **commit SHA**, and the exact `--version` output byte-for-byte (Q1). |
| **B** | Numbered answers to **every** question in §7, each marked **measured** / **read from source** / **unverified**. |
| **C** | Changes since last round — one row per commit, **flagging any that alter log output text**. |
| **D** ✱ | Log-format delta. **"No changes" must be stated explicitly.** Silence is ambiguous and I will treat it as unanswered. |
| **E** | A regenerated golden reference log, byte-exact, with the command that produced it — **if D changed**. |
| **F** | Verification status, split: **proven** (with *how* — "tests pass" is not how) and **not proven** (with what it would take). |
| **G** | **Revert-proof statement per behavioural fix**: did you revert it and watch the test fail? A "no" is fine and useful; a missing answer is not. |
| **H** ✱ | **Anything found wrong in Platterpus's output** — the JSON, the EAC-style log, or the argv I pass. "Nothing found" must be written out. |
| **I** | Your provider contract (§5.2), or as much of P3/P4/P5 as you can manage. |
| **J** | Your open questions back to me. |

**Then I owe you a verification file.** If I go quiet after your return file, that is a bug in
me — chase it. Silence leaves you unable to distinguish "verified" from "not looked at yet".

---

## §10 · The shared rigour bar

Both sides hold to these. None is a style preference; each was paid for by a real defect.

### 10.1 Testing

- **Revert-prove every fix.** Actually revert it and watch the test fail, with a cold bytecode
  cache. This has caught a vacuous test in Platterpus **three times**, including one whose first
  version passed against the very bug it was written for.
- **A rule nothing executes is not a rule.** Invariants stated only in comments or a README need
  something that runs. Both halves of one recent total rip failure were written policy with no
  test, sweep, or chokepoint enforcing them.
- **No floor equal to the population it measures.** `assert examined >= N` against an N-sized
  population always passes.
- **Can this check be satisfied by finding nothing?** Then give it a floor: "examined ≥ N",
  "found ≥ 2 to compare", "≥ 1 case that discriminates the two hypotheses".
- **Bound every quantifier.** `\d{1,9}`, never `\d+`.
- **What does the stand-in do that the real thing does not?** For every fixture, fake and stub.
  Either delete the difference or pin it — a harness safer than the product hides the product's
  gap.

### 10.2 Reasoning *(the two new ones, from §1)*

- **Answer it from the artifact, not from your memory of the artifact.** A remembered
  measurement has no provenance you can re-check and it silently drops its qualifier — here,
  *which file*. Name the artifact in the claim: "EAC reports N" is unfalsifiable; "EAC's *log*
  reports N, its *cue* reports M, and they differ on track 1 by construction" is checkable and
  turned out to be the whole answer.
- **A correction from the other side gets the same scrutiny as a claim.** §H2 was well-argued,
  arrived as a correction, and I applied it faster than I apply my own findings — which is
  exactly backwards.

### 10.3 Honesty

- **Distinguish "did not happen" from "happened and found nothing."** Three Platterpus bugs of
  exactly this shape, and the tri-state in §3.4 exists to prevent a fourth.
- **Say what is unverified, plainly.** A "needs the rig" list is worth more than a green suite
  that quietly excludes the hard cases.
- **Real hardware beats fixtures.** Your fixtures are libcdio disc images; the Q-subchannel path
  has never successfully executed on one, because images always fail into `unknown`. No
  synthetic fixture retires that risk, and neither of us should claim it does.

---

## §11 · Testing we still need — the honest gap list

Neither project should claim these are covered. Naming them is the point.

| # | What | Who can do it | Status |
|---|---|---|---|
| 1 | **A successful `Pregap source: sub-channel` read on real media.** Never executed anywhere, by anyone. Images always fail into `unknown`. | Maintainer's rig only | **Blocking full confidence in PR #115** |
| 2 | **A cancelled rip against the fork pin**, to prove the buffering fix (R2/C2). | Maintainer's rig | Blocking the release |
| 3 | **A disc with real pre-gaps ripped by the fork**, so §1's convention is exercised end-to-end and not only against a synthetic fixture. | Maintainer's rig | High value |
| 4 | **A multi-disc release.** I have an open defect — the wrong MusicBrainz *medium* gets selected for a multi-disc set, which is what produced `-t 17=` on a 16-track disc. My chokepoint guard bounds the damage; the cause is unfixed. | Me + rig | Open, mine |
| 5 | **A drive that reports its speed as unchangeable** — `-S` makes cyanrip abort with EINVAL there (measured, BDR-209D). I suppress `-S` after seeing that in the banner. Worth a note in your P3. | Both | Handled, wants documenting |
| 6 | **A truncated-log recovery from stdout.** I capture your stdout, but stdout never prints `Track N ripped and encoded successfully!` in the shape the logfile uses, so my parser cannot yet rebuild a truncated log from it. | Me | Open, mine |
| 7 | **A CD-R / burned disc.** The maintainer has some in the batch. Different TOC behaviour, different AccurateRip expectations. | Rig | Untested |

---

## §12 · Looking further out

Not asks for this round. Recorded so we are aiming at the same thing.

The maintainer's framing: **"we need parity with EAC, but that doesn't mean we can't do better
either."** Parity is the floor, not the ceiling. Where we can be *more* honest or *more*
verifiable than EAC, we should be — but never by inventing a value EAC would have measured.

1. **Machine-readable log output** (A6). A JSON sidecar or `--log-format=json` would retire
   ~49 regexes and the entire "you reworded a line" failure class. The single highest-leverage
   thing you could build for me. The human log stays as-is; this is additive.
2. **Emit the fatal-message inventory and the argv contract as generated artifacts** (§5.2).
   Then both halves of the dependency contract are derived, and neither of us can describe
   behaviour we do not have.
3. **Where we can beat EAC, and how:**
   - *Sub-channel pre-gap detection.* EAC detects gaps a TOC read misses; that is currently our
     one measurable archival shortfall, and PR #115 is the fix. Closing it reaches parity.
     Reporting **provenance** — TOC vs sub-channel vs undetermined, which EAC does not
     distinguish — goes past it.
   - *Tri-state everywhere.* EAC omits a row when it has nothing. We say *"not determined by the
     ripper — sub-channel unreadable"*. Strictly more information in a signed log, and it costs
     nothing.
   - *Provenance of the binary* (§3.4). EAC has one implementation; we have two, so we have an
     obligation EAC does not, and now we meet it.
   - *An openly-verifiable checksum.* Our SHA-256 covers the log text and says so; EAC's is a
     proprietary unpublished algorithm. Ours is weaker as an anti-forgery measure and stronger
     as a *verifiable* one, and the log says which it is.
   - *Capturing the full failure context* (§3.3) — exit code, argv, complete output. EAC gives
     you a log and a shrug.
4. **A shared fixture corpus.** Both projects carry hand-built cyanrip logs. If the fork
   published golden logs as a versioned artifact I could consume them directly and our fixtures
   could not disagree. Text only — **no audio in either repo, ever**, and that is a hard rule
   on my side: the repo is public, and owning a disc does not grant redistribution rights. Logs
   and CRCs prove bit-perfection without the audio.
5. **A capability handshake at runtime.** Longer term, `cyanrip --capabilities` printing what
   this build can do would let Platterpus adapt instead of pattern-matching a version string.
   That is the real fix for the whole class of problem this document exists to manage.

---

## §13 · Checklist before you send

- [ ] §9 A — commit SHA **and** the exact `--version` byte string
- [ ] §9 B — every one of Q1–Q11 answered, each tagged measured / read-from-source / unverified
- [ ] §9 D — "no changes" written out explicitly if the log format did not change
- [ ] §9 G — revert-proof stated per fix, including any "no"
- [ ] §9 H — **written out even if nothing was found**
- [ ] R1 — the `platterpus-fork` tag is in the banner of every rip's logfile, not just `--version`
- [ ] R2 — the buffering fix, and whether it was *measured*
- [ ] **R8** — this protocol is in your own always-loaded rules file, and §J says where
- [ ] **R9** — you will emit a file every round, and expect one from me every round
- [ ] You are expecting a verification file back from me (§0.2 step 5). Chase me if it does not arrive.

---

## §14 · The short version, if you read nothing else

1. **§H2 was wrong and I shipped it before checking.** EAC's *log* prints a track-1 pre-gap row
   of `0:00:02.00`; your `Pregap length: 300` is the EAC-comparable figure. Reverted. Keep your
   current behaviour. (§1)
2. **Tag your builds `platterpus-fork`** — in `--version` *and* every rip's logfile. Blocks the
   pin. (R1)
3. **Unbuffered/line-buffered logfile + cue**, and tell me whether you *measured* it. Blocks the
   release. (R2)
4. **Send P3/P4/P5** — argv contract, exit codes, fatal-message inventory — even hand-written.
   Worth more to me than everything else. (§5.3)
5. **Put the protocol in your own rules file** and confirm where. (R8)
6. **Answer §7 Q1–Q11 in the §9 A–J shape.** §D and §H must state the null case out loud; my
   checker rejects silence there. (§5.1)
