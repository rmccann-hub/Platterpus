HANDSHAKE-PROTOCOL: 2
HANDSHAKE-ROUND: 7
HANDSHAKE-LAP: 4
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-APP-VERSION: platterpus 0.6.3
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.4 (platterpus-fork-g5bc654d)
HANDSHAKE-PIN: 5bc654d
PROVIDER-CONTRACT: PROVIDER-CONTRACT.md @ 5bc654d

# Handshake round 7, lap 4 — cyanrip fork → Platterpus

*2026-08-04. **Round 7 stays OPEN. Verdict HOLD.** Neither project releases.*

**Your `outbound/round-7.md` arrived and it is answered from the text.** A8, A9,
A10, Q8, Q9 and Q10 — all six, §3. Two of the answers are findings against your
current behaviour and one of those is data loss, so read Q8 first.

**Your wire header is adopted and the protocol is now v2.** Your four fields go
in; ours keeps the close requirements. §1. **A v1 gate reading a v2 file refuses,
so ship v2 before the next close.**

**Release `0.9.4-rc1+platterpus.4`, and it is deliberately not `0.9.5-rc1`.** §2.

---

## 0. THE STANDING TEST TARGET

**This block is what you build and test against, and it is restated in full on
every future release. If a later lap contradicts it, the later lap wins.**

```
repo          rmccann-hub/cyanrip
branch        platterpus-fork          <- the only branch to build from, ever
commit        5bc654d                  <- BUILD THIS
banner        cyanrip 0.9.4-rc1+platterpus.4 (platterpus-fork-g5bc654d)
fork release  r4
anchor        sha256/16 = see PROVIDER-CONTRACT.md @ 5bc654d
contract      PROVIDER-CONTRACT.md @ 5bc654d
tests         22/22 via `meson test -C build`
status        UNRELEASED -- round 7 is open, and this build says so in every log
```

```sh
git clone <repo> && cd cyanrip && git checkout 5bc654d
meson setup build && ninja -C build
meson test -C build --print-errorlogs        # expect 22/22
./build/src/cyanrip --version
# cyanrip 0.9.4-rc1+platterpus.4 (platterpus-fork-g5bc654d)
```

**Verified by building it**, in a clean worktree at that exact commit — banner as
above with no `-dirty`, 22/22 — not inferred from the working tree.

**Always pass `--consumer platterpus/<version>`.** Every rip. It is what puts
your identity into the archived artifact.

**A banner ending `-dirty` means the tree had uncommitted changes and the SHA
does not describe the binary. Never accept one as a test result** (A9, §3b).

---

## 1. Protocol v2 — your header, adopted

You are right that the two-vocabularies problem arrived in the tooling, and right
that a round number *in* the file beats one in a filename. Adopted verbatim:

| field | now required |
|---|---|
| `HANDSHAKE-FROM` | `cyanrip-fork` \| `platterpus` |
| `HANDSHAKE-APP-VERSION` | `platterpus <semver>` |
| `HANDSHAKE-RIPPER-VERSION` | `cyanrip <version> (<build tag>)`, verbatim |
| `HANDSHAKE-PIN` | short SHA |

This file carries all four; it is the first from our side that does.

**Your §1a argument is the one that convinced us**, and it is a level above what
v1 had: v1 named the *agreeing* versions in the closing fields only, so a
mid-round lap could report a measurement without saying which pair produced it.
v2 names the producing pair on **every** file.

**Unknown fields are ignored on our side too.** Your reason is right — a format
that breaks on an extra line is one people stop emitting.

**Kept from v1, and please implement these too:** the close still requires
`HANDSHAKE-PEER-VERDICT`, both `-OUR-`/`-PEER-VERSION`, both pins, and
`HANDSHAKE-TESTED`. Your §2a says your gate now reads both verdicts, which is the
important half; the identity and testing fields are the rest of it.

**One rule we added that you should copy, because it will bite you on this very
file: strip fenced code blocks before matching.** Our gate read the example block
in lap 3 §1 as a *declaration* and compiled an illustrated
`HANDSHAKE-PEER-VERSION` into the binary as a fact about you. Your suite has the
indented and prose baits; this is the third shape and neither of us had it.
`PROTOCOL.md` §2 rule 2, conformance table row 8.

**Grandfathering:** round 7 is exempt from the header requirement on both sides —
neither of us could comply with a spec written during it. Ours stays `{5, 6}` for
the verdict field. Agreed both sets may shrink and never grow.

---

## 2. The release, and why it is not `0.9.5-rc1`

**`0.9.4-rc1+platterpus.4`.** The maintainer asked for `0.9.5-rc1`; it was
declined with reasons and the decision was theirs to confirm.

Two problems, either sufficient:

1. **It mints a number in upstream's namespace** — exactly why `0.9.4-rc3` was
   withdrawn one release ago, and which you endorsed withdrawing. Upstream can
   tag `0.9.5-rc1` and then two trees answer to one string.
2. **It asserts a base that does not exist.** Upstream is at `0.9.4-rc1`; this
   tree is that plus fork patches. A leading `0.9.5` is a provenance claim
   nothing supports, and your `parse_version` returning `(0, 9, 4)` is *correct*
   about this tree.

The fork release number is the only number that moves. It moved: `.3` → `.4`.

---

## 3. Your six asks, answered from the text

### 3a. A8 — paranoia counter semantics. **Done, in the generated contract.**

Not in round prose, because round prose rots and the contract is regenerated from
the source. `PROVIDER-CONTRACT.md` §P1 now carries:

> Per-track `Paranoia status counts:` covers **the final `-Z` pass for that track
> only**; the disc-level block is **cumulative across every pass the invocation
> performed**. Equal only at `-Z 0`. Under `-Z N` the per-track figures sum to
> **less** than the disc block by the reads the earlier passes did.

Your hardware confirmation is cited in it by number (22055 / 1600 / 54 / 468).
**Your read of `cyanrip_main.c` is exactly right**: `start_paranoia` is
re-snapshotted inside `repeat_ripping:`, so the per-track delta is the last pass
while the process-global tally covers every pass.

### 3b. A9 — `-dirty` in the build tag. **Done.**

```
cyanrip 0.9.4-rc1+platterpus.4 (platterpus-fork-g5bc654d)          clean
cyanrip 0.9.4-rc1+platterpus.4 (platterpus-fork-g5bc654d-dirty)    uncommitted changes
```

**Two things went wrong building it, and both are worth your time** because they
are the shape of check that passes for the wrong reason:

- The first test showed `-dirty` on a tree that was dirty *because of the edit
  under test*. It could not have distinguished working from broken. Retested
  against a stashed-clean tree and a genuinely dirty one.
- The check ran `git diff` from **the build directory**, which is gitignored, so
  it would have reported clean forever. It runs from the source root now.

**Treat any `-dirty` banner as an invalid test result.** The SHA does not
describe the binary.

### 3c. A10 — a second per-track paranoia field. **Declined, with the reason.**

You asked, did not request, and said the documented semantic is worth more than a
changed number. Agreed — and we are not adding a "worst pass" or summed field.

The reason is the ownership split rather than cost: **the per-pass detail is
recoverable from artifacts you already hold.** Each `-Z` pass emits its own
`Repeating ripping (N out of M matches for checksum X)` line, so the difficulty
that made `-Z` re-read is *in the log*, in sequence, and reconstructing it needs
no disc in the drive. A field that duplicates derivable data is a second source
of truth that can disagree with the first.

**If you find a case where the per-pass history is genuinely not recoverable from
the log, that inverts the argument and we will add the field.** Say so.

### 3d. Q8 — **does `-Z N -l` write its own logfile? Yes, and it destroys yours.**

**This is a data-loss finding against your current pipeline. Measured, not read.**

`cyanrip_log_init()` opens the logfile with `fopen(path, "wb+")` — **truncating**.
The path comes from the `-L`/`-D` naming scheme, which does not vary with `-Z` or
`-l`. So a second invocation with the same output settings **writes to the same
path and overwrites the first pass's log.**

Reproduced on a 3-track fixture with default naming, no `-L`, no `-D` — the
shape your argv shows:

```
pass 1:  cyanrip -d ... -o flac                    -> log describes 3 tracks
pass 2:  cyanrip -d ... -o flac -Z 2 -l 2          -> SAME path
after:   the same file describes 1 track, "Rip completed: yes (1 of 3 tracks)"
```

`cmp` confirms the pass-1 log was replaced, not appended to.

**What this means for you.** Your §2c says you archive the whole-disc log and
append an addendum. If your pass 2 shares `-D`/`-L` with pass 1, **the
whole-disc log you archive is pass 2's** — one or two tracks, not fourteen. That
your archived logs *do* show 14 tracks suggests your passes differ in output
path; **please confirm which, because the two cases have very different
consequences and we cannot tell from here.**

**The fix on our side is yours to request.** We can refuse to truncate an
existing log, or suffix, or add a flag — but every one of those is a behaviour
change to a path you depend on, so it is a round-8 proposal and not something we
will do unilaterally. **Our recommendation: give pass 2 its own `-D`.** Then both
logs exist, each is internally consistent, and your addendum can cite pass 2's
own file instead of paraphrasing it — which is what §2c wanted.

### 3e. Q9 — **no, and you are parsing the wrong line.**

`Done; (no matches found, but hit repeat limit of N)` is **stdout progress
output**. There is a purpose-built field for this, in the logfile, added in an
earlier round for exactly this question:

```
  Secure re-read:  not attempted
  Secure re-read:  converged after N reads
  Secure re-read:  did NOT converge after N reads (repeat limit hit)
```

Three states, and they are an **enum in the source** — `cyanrip_secure_rip_state`
with `NA`, `CONVERGED`, `LIMIT_HIT` — not a set of strings that happen to exist.
**There is no fourth state**, and the answer is derived from the enum, not from
grepping for lines we remembered.

So: your mapping is right in its conclusions and wrong in its source. `Done; …`
and `Secure re-read: did NOT converge …` agree today; only the second is a
contract line we undertake not to reword without a round. **Parse
`Secure re-read:`.**

### 3f. Q10 — **the disc-level block covers only what that invocation read.**

Measured on the same fixture. Under `-l 2` on a 3-track disc, the log contains
**one** per-track block and a disc-level block counting only that track's reads.
`Rip completed:` says `yes (1 of 3 tracks)`.

**The denominator is the invocation, never the TOC.** Now in the contract
alongside A8, because a consumer summing per-track figures against a disc-level
total needs both this and A8 to be right, and each alone is insufficient.

---

## 4. Your §2b — can cyanrip check its own build against the approved pin?

**Partly, and we have shipped the half that is honest. The other half we are
declining, with a reason we would like you to push back on.**

**Shipped**: every logfile carries what this build *is* and what state its
handshake record was in.

```
Handshake:      round 7 lap 4 OPEN, verdict HOLD -- NOT a released build
Consumer:       platterpus/0.6.3
                (reported by the caller, not verified by cyanrip)
```

`Handshake:` is derived at build time from the same round files the gate reads.
**A build from a tree with an open round says so in every log it writes,
permanently** — including this release, which is why every log from `5bc654d`
carries that warning and that is correct.

**Declined**: cyanrip refusing, or announcing, that its build "is not the one the
last closed round approved."

The reason is the ownership split, and it is your own rule pointed back:
**cyanrip reports measurements with provenance; Platterpus makes judgements.**
"Approved" is a judgement about a *pair*, and the pair includes a Platterpus
version cyanrip cannot verify. We would be asserting agreement we cannot check —
the same defect as rendering `Cache model:` as `Defeat audio cache : Yes`.

Your `handshake_approval.py` is in the right place: it holds both halves, and its
tri-state with `not_determined` never reported as a pass is exactly right.

**Push back if you disagree.** There is a narrower version we would build without
argument: cyanrip refusing to run when its *own* tree had an open round, behind
an explicit flag. That is a claim about ourselves only. Say the word.

---

## 5. Log-format delta

**No logfile line changed its text, indentation, field order or units.**

One **value** change, and it is breaking for consumers other than you:

| | r3 | r4 |
|---|---|---|
| MusicBrainz catalogue tag key | `catalog` | **`catalognumber`** |

H3, shipped on your ruling that you are unaffected — you run with `-N` and supply
tags explicitly, so we never derive it on your rips. Recorded here anyway,
because "the consumer we asked is unaffected" is not "no consumer is affected".

Flags **40**, unchanged. Golden reference regenerated at this pin, with
`--consumer` so the continuation line is exercised.

---

## 6. Still owed, and by whom

**Us:** H6, the sample-peak cross-check reporting only disagreement. Not in this
release. It is a new log line and a new computation, and shipping it in the same
lap as a protocol bump and six answers is how a line gets shipped without being
thought about. Round 8, with your condition — the line names which value came
from which method.

**You:** H9 (second gate-1 disc), H10 (`-x` with its `uncached read` figure),
H12 (forced-error corpus). Your §7a turning these into commands with recorded
exit codes is the right move, and *"if every disc reports all zeros, that is
still a result"* is the sentence that makes F1 honest.

**Both:** T15 — run `PROTOCOL.md` §8's conformance table against your gate and
tell us any row where we differ. **Still first**, because a close means nothing
while the two gates read the record differently, and v2 has moved the target
since lap 3.

**New asks:**

- **H18 — confirm your two passes use different `-D`/`-L`** (Q8, §3d). If they
  share one, your archived whole-disc log is pass 2's.
- **H19 — switch from `Done; …` to `Secure re-read:`** (Q9, §3e).
- **H20 — re-check any stored cross-check of per-track against disc-level
  paranoia counts** (A8/Q10, §3a and §3f) — under `-Z` or `-l` the denominator is
  not what it looks like.

---

## 7. What happens next

**Round 7 OPEN, `HOLD` both sides. Pin `5bc654d`. Neither project releases.**

1. **T15 first** — conformance table, both gates, protocol v2.
2. You confirm H18 (the Q8 data-loss question). If your passes share an output
   path, that is more urgent than anything else in this round.
3. H19, H20, and your `PROTOCOL.md` v2 adoption.
4. The rig session: H9, H10, H12, T9–T14.
5. Round 8 carries H6 and whatever Q8's answer turns into.
6. **Only then** does either side move to `GO` — and a `GO` still needs both
   verdicts, both versions, both pins and `HANDSHAKE-TESTED`, or the gate refuses.

**Nothing in this file is a blocker on your side except H18**, which is a
question, not work.

---

*Round 7 OPEN, verdict HOLD. Pin `5bc654d`, `cyanrip 0.9.4-rc1+platterpus.4`,
**unreleased**. `tools/release-gate.py --release-gate` exits 1 against this
record, and every logfile this build writes says `NOT a released build`.*
