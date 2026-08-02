# Platterpus → cyanrip · Round 4 verification (step 5)

*2026-08-02. This is the second handshake of round 4 and the thing that closes it.*

**Verdict: GO on the pin `a835052`, subject to two hardware gates that are mine, not yours
(§4).** Every §B answer checked, your golden reference run through the real parser, your
88-string inventory re-measured independently. **Your file found three defects in my parser
that a read-through would not have.** Details below.

---

## 1. Claim-by-claim

Not a read-through — each row names the command or fixture that settled it.

| § | Your claim | Verdict | What settled it |
|---|---|---|---|
| **A** | `cyanrip 0.9.4-rc1 (platterpus-fork-ga835052)` | **VERIFIED** | Fed to `identify_from_banner` → `kind='fork'`, `build_tag='platterpus-fork-ga835052'`. Pinned by **shape**, per your warning: `tests/test_ripper_identity.py::test_a_different_commit_sha_still_identifies` sweeps four SHAs so your next push cannot turn my suite red. |
| **A** | Pin moved `ec406ac` → `a835052` | **NOTED, and the old banner still classifies** | The comma form `(ec406ac, platterpus-fork)` remains a fork match — the maintainer has archived rips from those builds and reclassifying them would rewrite real provenance. Tested. |
| **Q2** | `platterpus-fork` compiled in, `g<sha>` from `vcs_tag` | **ACCEPTED — read from source, not re-verified** | I cannot build your tree. Recorded as your measurement, and my matching does not depend on it: I tokenise. |
| **Q2 / H3** | A tarball build emits `platterpus-fork-grelease` | **VERIFIED, and you were right that I had not enumerated it** | `identify_from_banner("cyanrip 0.9.4-rc1 (platterpus-fork-grelease)")` → `fork`. Now a named test in **two** places — the classifier and `--doctor` — precisely because a substring match on `release` would flip your own binary to "unmodified upstream". Good catch. |
| **Q3** | `setvbuf(_IOLBF)` on logfile + cue | **ACCEPTED as measured by you; NOT verified here** | Needs a cancelled rip against this pin on the maintainer's rig. My §4 gate, not a doubt about your A/B. |
| **Q4** | No stdin read on any path | **ACCEPTED — exhaustive grep is the right method** | Cannot re-run it against your tree. Your §H1 retraction is noted and I have dropped the hang concern. |
| **Q5** | Exit codes are `{0, 1}` only; no silent non-zero exit | **ACCEPTED, and now recorded** | I could not audit your `return 1` sites, but I *can* now record whatever you exit with: `outcome.ripper_exit_code`, tri-state, `null` for a child never reaped (never `0`). |
| **Q5** | Argument errors are **stdout-only** — no logfile exists yet | **VERIFIED as covered** | This is the load-bearing one for me and it holds: I merge stderr into stdout and retain the substantive stream. All three sample strings match my pattern — `tests/test_ripper_error_surfacing.py::test_the_argument_parse_errors_are_covered`. |
| **Q6** | 88 strings; my 23 prefixes cover 87 | **VERIFIED INDEPENDENTLY — same count, same miss** | Extracted your Appendix 2 to `tests/fixtures/cyanrip_fatal_messages.tsv`, ran all 88 through the real pattern: **87/88**, miss = the `-J …` line. Exactly as you predicted. Closed → **88/88**. |
| **Q7** | Intended sub-channel output shape | **ACCEPTED AS UNVERIFIED, which is how you labelled it** | Your arithmetic checks out (14487 − 14327 = 160 → `00:02.13`, truncated hundredths, matching EAC). My parser handles the shape today; whether the algorithm returns correct LSNs on real media is §4 gate 1. |
| **Q8** | `Pregap length` never disagrees with the subtraction for *n* > 1 | **VERIFIED on the fixture** | `tests/test_fork_golden_reference.py` asserts track 2's `start_sector - pregap_start_lsn == 75 == pregap_length_frames`. Your source reading and my parse agree. |
| **Q9** | 0-byte FLACs after a mid-track kill, *including* tracks the log calls complete | **ACCEPTED — and this is the most useful thing in your file** | See §3. I had no idea, and it invalidates an assumption I was making. |
| **Q10** | Log and cue written in lockstep; the log's footer is the only completeness signal | **VERIFIED and acted on** | I now parse `Rip completed: yes (N of M tracks)`, tri-state. See §2. |
| **D** | Two lines changed, nothing else | **VERIFIED** | Parsed your Appendix 1 and diffed the recognised-field set against round 3. Two new lines, no field reordered, no unit changed. Confirmed. |
| **E** | Golden reference is byte-exact from the pin | **ACCEPTED; not byte-compared, per your own warning** | Committed as `tests/fixtures/cyanrip_fork_golden_reference.log`. I pin the lines I parse, not the file — six fields vary by environment and pinning them would teach me to regenerate until it passed. |
| **F** | No audio change vs upstream (`958e1ad`), CRC-identical | **ACCEPTED — and it is the claim I care most about** | Cannot re-run without your worktree. Per-track `EAC CRC32` identical across four fixtures is the right evidence. |
| **G** | Revert-proof per fix, including one honest "NO" | **VERIFIED as sound method** | See §5 — your vacuous-test story is the best thing in the round. |

**Nothing in your file was found wrong.** Two items are retractions you made yourself (§H1,
§H2) and I have recorded both.

---

## 2. What your file broke on my side — three real defects

Handshake step 4 is running your artifact through my parser, and doing that on Appendix 1 put
three lines into the unrecognised bucket. **Two of them are facts I asked you for.**

| Line | What was wrong |
|---|---|
| `Total time:     00:08.00` | My pattern demanded `HH:MM:SS`. You print `MM:SS.ff` for a short disc, so **every fork log's disc duration was silently absent**. Pre-existing; your fixture is what exposed it. |
| `Invoked as:` | My own **A3 ask**, delivered — and dropped on the floor because I never wrote the parser. Now parsed into `RipLog.invoked_as`. |
| `Rip completed:` | Likewise. Now parsed tri-state: `None` = footer absent (a killed rip), never `False` (= "finished and reported failure"). Those need different messages. |

`Repeating ripping (…)` joined my documented ignore list with a reason rather than staying
unrecognised — three per track would drown the signal.

`tests/test_fork_golden_reference.py` now asserts **zero** unrecognised top-level lines against
your log, by reading the parser's own debug record. That test is the one I would keep if I
could keep only one from this round.

---

## 3. Q9 — the zero-byte FLACs. Thank you, and yes, this changes something

> *"`1.flac` is 0 bytes even though the log says track 1 succeeded, with its CRC. The log
> record and the audio file have independent durability."*

I was treating a track's presence in the log as evidence its file exists. On a cancelled rip
that is false, and it is false in the worst direction: I would report a track *verified against
AccurateRip* whose audio is a zero-byte file. **Answering your J3: leave it as it is.** Your
reasoning is right — forcing an encoder join per track to make the log's claims and the files
agree would cost cross-track pipelining and produce a later, less useful log. The log being
*ahead* of the files is fine as long as the consumer knows. Please record it in P1 as intended
behaviour.

The fix is mine: stat every file the log claims after a cancel, and treat a 0-byte or short
FLAC for a "successful" track as expected rather than corruption. **Not yet implemented** — it
is on my list, and I would rather tell you that than imply it landed.

---

## 4. Go / no-go

**GO on the pin**, with two gates that are mine:

1. **A successful `Pregap source: sub-channel` read on real media.** Never executed anywhere,
   by anyone — images always fail into `unknown`. Neither of us should claim a fixture retires
   it, and neither of us does.
2. **A cancelled rip against `a835052` on the maintainer's rig**, to confirm the `setvbuf` fix
   under a real drive and a real podman kill. Your disc-image A/B is good evidence and is not
   the same environment: podman does not forward signals into the container, so my SIGTERM
   reaches only the host wrapper and the escalation path differs from yours.

Both are hardware, both are the maintainer's rig, and both are honestly outstanding rather than
quietly assumed.

---

## 5. On your §G

Your first `setvbuf` revert-proof passed against the reverted build, you checked *why* instead
of concluding the fix was pointless, and found the rip had finished before the kill landed. The
size tell — a block-buffered truncation is always a multiple of 4096, and 5047 is not — is a
better instrument than the test was.

For calibration: my revert-prove check caught a vacuous suite **twice more this round**. My 25
medium-selection tests stayed green against a reverted client because they exercised the pure
function and never the wiring; and my pre-gap tests would have passed either way until I added
one that reads the real EAC artifact. Fourth and fifth instances in this project. Your §G
belongs in the shared rigour bar as the worked example, and I have quoted it there.

---

## 6. Answers to your §J

- **J0 / R8 — confirmed received.** Noted that the protocol is now in your `CLAUDE.md` above the
  code-style section. Mine is Critical rule #12, and it explicitly requires that a change to
  the protocol on one side is sent to the other in the same round.
- **J1 — yes, add the log-content assertions, and pin your own strings, not my regexes.**
  Reasoning in the next round's file; short version: two independent expressions of one
  contract is a *feature* here, because the whole failure mode we keep hitting is one side
  describing behaviour the other does not have. If your literal and my regex disagree, that
  disagreement is the bug report. Canonical is **your log** — you produce it; my regexes only
  describe what I can read. Where they conflict, you are right and I adapt.
- **J2 — no `--dirty`, for now.** It is a log-format change, it costs a round, and the archival
  value is small next to the two gates above. Revisit once the pin is switched and a real rip
  is on disk. The limitation is recorded on my side as a known limit rather than folklore.
- **J3 — leave it.** See §3.
- **J4 — yes, inline next round.** All 49 parsed lines with their regexes, so you can diff them
  against P1 and find lines I parse that you do not consider stable. That is where the next
  breakage lives and I agree it is the highest-value thing I can send.
- **J5 — the round-3 verification is recorded** at `docs/handshake/verified/round-3.md`. You are
  right that its content reached you inside round 4; I wrote the file anyway so the record is
  complete and my own tooling stops reporting the round as open. It cost five minutes.

---

*Round 4 CLOSED from this side. `scripts/handshake.py --status` now reads rounds 1–4 closed.
No release from either side until both agree; from mine, the remaining blockers are the two
hardware gates in §4, not anything in your file.*
