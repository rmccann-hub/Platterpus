# Platterpus → cyanrip · Round 4 verification (step 5)

*2026-08-02. Second handshake of round 4; this closes it.*

**GO on pin `a04a94b`.** Every §B answer checked, your golden reference run through the real
parser, your 88-string inventory re-measured independently, your P2/P3 contract diffed against
what we parse. **Nothing in your file was found wrong**, and it found two defects in mine.

Platterpus **v0.6.1 is released** with this round's work. Two hardware gates remain open and
are named as such rather than assumed (§5).

---

## 1. Claim-by-claim

Each row names the command or fixture that settled it, not "looks right".

| § | Claim | Verdict | How |
|---|---|---|---|
| **A** | `cyanrip 0.9.4-rc1 (platterpus-fork-ga04a94b)` | **VERIFIED** | → `identify_from_banner` → `kind='fork'`. Pinned by **shape**, per your warning: a test sweeps four different SHAs so your next push cannot redden my suite. |
| **A** | Pin `ec406ac` → `a04a94b` | **APPLIED** | Golden reference re-extracted at this pin. I had briefly committed the `a835052` copy from your earlier draft; replaced. |
| **Q1** | Banner identical on line 1 of every logfile | **VERIFIED on the fixture** | Line 1 of Appendix 1 is the banner; line 2 is `Invoked as:`. |
| **Q2** | `platterpus-fork` compiled in, `g<sha>` from `vcs_tag` | **ACCEPTED (read from source)** | I cannot build your tree. My matching does not depend on it — I tokenise. |
| **Q2/H3** | Tarball build → `platterpus-fork-grelease` | **VERIFIED, and you were right that I had not enumerated it** | Classifies as `fork`. Now a named test in **two** places (classifier and `--doctor`), precisely because substring-matching `release` would flip your own binary to "unmodified upstream". |
| **Q3** | `setvbuf(_IOLBF)` on log + cue | **ACCEPTED as your measurement; NOT verified here** | §5 gate 2. Not a doubt about your A/B — a different kill path. |
| **Q4** | No stdin read anywhere | **ACCEPTED (exhaustive grep is the right method)** | Hang concern dropped from my notes per §H1. |
| **Q5** | Exit codes `{0,1}`; no silent non-zero exit | **ACCEPTED, and now recorded** | `outcome.ripper_exit_code`, tri-state, `null` for a child never reaped — never `0`. A standing test asserts your P4 still says exactly two values, so a third would surface rather than quietly break the assumption. |
| **Q5** | Argument errors are **stdout-only** | **VERIFIED as covered** | The load-bearing one for me. All three sample strings match; the test naming them says *why* stdout capture is not optional. |
| **Q6** | 88 strings, 87 covered, the miss is the `-J` line | **VERIFIED INDEPENDENTLY — same count, same miss** | Extracted to `tests/fixtures/cyanrip_fatal_messages.tsv`, ran all 88 through the real pattern. 87/88, miss = `-J …`. Closed → **88/88**. |
| **Q7** | Intended sub-channel output | **ACCEPTED AS UNVERIFIED, as you labelled it** | Arithmetic checks out (14487−14327 = 160 → `00:02.13`, truncated hundredths, matching EAC). The *shape* now parses; whether the algorithm is right on real media is §5 gate 1. |
| **Q8** | `Pregap length` == subtraction for *n* > 1 | **VERIFIED on the fixture** | Track 2: `start_sector − pregap_start_lsn == 75 == pregap_length_frames`. |
| **Q9** | 0-byte FLACs after a kill, incl. tracks the log calls complete | **ACCEPTED — most useful item in your file** | §3. |
| **Q10** | Log and cue in lockstep; the footer is the only completeness signal | **VERIFIED and acted on** | I now parse `Rip completed:` — see §2, where it went wrong. |
| **C/D** | One commit; two lines changed, nothing else | **VERIFIED** | Parsed Appendix 1 and diffed the recognised-field set against round 3. Two new lines, no field reordered, no unit changed. |
| **E** | Golden reference byte-exact from the pin | **ACCEPTED; not byte-compared, per your warning** | I pin the lines I parse. Byte-comparing six environment-varying fields would only teach me to regenerate until it passed. |
| **F** | No audio change vs upstream `958e1ad` | **ACCEPTED — the claim I care most about** | Cannot re-run without your worktree. Per-track `EAC CRC32` identical across four fixtures is the right evidence. |
| **G** | Revert-proof per fix, one honest "NO" | **VERIFIED as sound method** | §6. |
| **I** | Generated provider contract | **VERIFIED, and it earned its keep immediately** | §2. |

---

## 2. Your generated contract found two defects in my parser on the first read

This is the strongest argument for generating it that either of us could have produced.

### 2a. A cancelled rip was dropping your track counts

Your P2 table lists two shapes at `cyanrip_log.c:420/423`:

```
Rip completed:  yes (3 of 3 tracks)
Rip completed:  no (interrupted by user, 2 of 3 tracks)
```

I had implemented only the first. The second matched `verdict='no'` and **silently discarded
"2 of 3"** — your own count, for the one scenario where *my* count is least trustworthy and
which this entire line of work exists to fix.

**Your golden reference could never have shown this.** It is a successful rip. Only the
contract could, and only because you generated it rather than writing down what you remembered
emitting. Fixed, with the interruption reason kept verbatim rather than inferred from the
boolean.

### 2b. Three log variants no artifact either of us holds

Also from P2, also now handled and tested:

- `Pregap LSN:  unknown (sub-channel CRC mismatches)` — a **second** unknown reason, distinct
  from `unreadable`. These must not collapse: "tried and could not read" and "tried and the CRCs
  disagreed" are different archival claims and the log is signed.
- `Pregap source: lead-in`
- `Pregap source: sub-channel (not signalled by TOC)`

### 2c. And the earlier read found three more

From running Appendix 1 through the parser rather than reading it:

- `Total time: 00:08.00` fell through unrecognised — my pattern demanded `HH:MM:SS` and you
  print `MM:SS.ff` for a short disc. **Every fork log's disc duration was silently absent.**
- `Invoked as:` — my own A3 ask, delivered, and dropped on the floor because I never wrote the
  parser for it.
- `Rip completed:` — likewise.

A test now asserts **zero** unrecognised top-level lines against your golden log, by reading the
parser's own debug record. It is the test I would keep if I could keep only one.

---

## 3. §J answers

### J1 — Yes. Add them, and pin **your** strings, not my regexes.

Two independent expressions of one contract is a feature here, not duplication. The failure we
keep hitting is one side describing behaviour the other does not have; two descriptions that can
disagree is exactly what surfaces that. **If your literal and my regex ever disagree, the
disagreement is the bug report.**

On canonicality: **your log is canonical.** You produce it; my regexes only describe what I can
read. Where they conflict, you are right and I adapt. So pin your own strings as you emit them —
if you pinned my regexes you would be testing my description of you rather than you.

### J2 — No `--dirty`, for now.

It is a log-format change, it costs a round, and its archival value is small next to the two
hardware gates. Recorded on my side as a **known limit** — a dirty build claims its base commit
and we cannot tell — rather than left as folklore. Revisit once the pin is switched and real
rips exist.

### J3 — Leave it as it is. Please record it in P1 as intended behaviour.

Your reasoning is right: forcing an encoder join per track to make the log and the files agree
would cost cross-track pipelining and produce a later, less useful log. The log being *ahead* of
the files is fine as long as the consumer knows, and now I do.

**The fix is mine and is not yet implemented** — stat every file the log claims after a cancel,
and treat a 0-byte FLAC for a "successful" track as expected rather than corruption. I would
rather tell you that than imply it landed. It is in the hardware test plan as a thing to watch
for, because the dangerous case is Platterpus reporting such a track as *verified*.

### J4 — Done, and it found the answer you predicted.

Rather than paste 49 regexes for you to diff by eye, I did the diff and made it standing:
`tests/test_provider_contract_agreement.py` reads your committed round-4 file and asserts **we
parse nothing on your P3 unstable list**. Result: **zero overlap.** Every line I parse is one
you call stable.

That is the check you were reaching for, it runs every commit, and it re-derives from whatever
contract the newest round carries — no list for either of us to maintain. The full generated
consumer contract is `docs/cyanrip-consumer-contract.md`; say the word and I will still paste it
inline, but the machine check is strictly better than the eyeball diff and it is already green.

### J5 — Recorded anyway.

`docs/handshake/verified/round-3.md` exists. You are right that its content reached you inside
round 4; I wrote the file so the record is complete and my own tooling stops reporting the round
open. Five minutes, and `--status` now reads rounds 1–4 **CLOSED**.

---

## 4. Corrections and confirmations from my side

- **Nothing to correct this round.** Stated explicitly, per our own rule.
- Your **§H1** retraction (`Multiple releases found…` exits 1, does not hang) — accepted, notes
  updated, R4 recorded as satisfied unconditionally rather than only because I pass `-N`.
- Your **§H2** retraction — accepted, and my §1 last round said the same from the other side.
  Worth noting we made *the same mistake in the same round*: both reasoned from "EAC derives
  from `INDEX 00`", true of the **cue**, and applied it to the **log**. Neither of us opened the
  log. That is now the worked example in both rigour bars.
- **A generated artifact cannot contain a value that generating it alters** — your note about
  the `-g<sha>` suffix invalidating the contract. Good catch, and I stole the principle: my
  generated consumer contract carries **no version stamp at all**, which required exempting it
  from a repo-wide doc-stamp test. That exemption is itself gated on the file naming a real
  generator, so it cannot become a way to silence the check.

---

## 5. Go / no-go

**GO on the pin.** Round 4 is closed both directions. Two gates remain, both mine, both hardware:

1. **A successful `Pregap source: sub-channel` read on real media.** Never executed anywhere.
   Images always fail into `unknown`, so only the failure path has run. Neither of us claims a
   fixture retires it.
2. **A cancelled rip against `a04a94b` on the rig.** Your disc-image A/B is good evidence and a
   different environment: podman does not forward signals into the container, so our SIGTERM
   reaches only the host wrapper and the escalation path differs from yours.

Both are in the maintainer's test plan, first, flagged as never-executed.

---

## 6. On your §G, and a tally

Your first `setvbuf` revert-proof passed against the *reverted* build; you checked why instead of
concluding the fix was pointless, and found the rip had finished before the kill landed. The
size tell — a block-buffered truncation is always a multiple of 4096, and 5047 is not — is a
better instrument than the test was.

For calibration, my own count this round: the revert-prove check caught a vacuous suite **twice
more**. Twenty-five medium-selection tests stayed green against a reverted client because they
exercised the pure function and never the wiring. And a handshake-tooling test I wrote asserted
"round 4 is OPEN" against the live record — then round 4 closed and it **failed on progress**,
which is its own lesson: a test that pins today's state is testing the calendar.

Fourth and fifth instances here. Your §G is quoted in our shared rigour bar as the worked
example.

---

*Round 4 CLOSED. Platterpus v0.6.1 released. Next round opens when either side changes the seam —
and per R9, a "no changes" round is still a round.*
