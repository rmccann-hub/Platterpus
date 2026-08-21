# cyanrip standing status — what the consumer can assume between rounds

**Not a round, not a lap, and it must not be counted as one.** It carries no
`HANDSHAKE-*` wire headers for that reason, and `tests/handshake_wire.py` never
sees it because it is not named `round-NN-lap-LL.md`.

The convention is Platterpus's, adopted verbatim: they sent us one on 2026-08-21
for v0.6.21, explicitly outside the round mechanism, and it was the right shape.
Rounds are the *formal* channel and they cost something — S-13 fixes a round's
close conditions at lap 1, and an open round blocks both sides' releases. Between
rounds each side still needs somewhere to say where it is.

**Rewritten in place, never appended to.** A stale standing status is worse than
none. That is the opposite rule from the handshake correspondence, which is
append-only and must never be amalgamated — the difference is that a lap is a
record of what was said at a moment and this is a claim about *now*.

---

## As of `0.9.4-rc2+platterpus.7` (2026-08-21)

**No round is open.** Rounds 5–12 are all closed with bilateral `GO`;
`tools/release-gate.py --release-gate` exits 0. Nothing on our side waits on
Platterpus, and nothing they do is blocked by us.

**A release was cut, and this is the SHA their lap 4 §C2 asked for.**

| | |
|---|---|
| version | `0.9.4-rc2+platterpus.7` |
| **commit** | **`237a4ff`** |
| build tag | `platterpus-fork-g237a4ff` |
| `release_seq` | 17 |
| channel | `stable` (and `beta`, which resolves to the newest row of any channel) |
| authorised by | handshake round 12, closed `GO`/`GO` on `64ae7bc` |
| install | `https://github.com/rmccann-hub/cyanrip/archive/237a4ff.tar.gz` |
| build command | `meson setup build -Ddeclare_released=true && ninja -C build` |

**`237a4ff` is not `64ae7bc`.** The round reviewed `64ae7bc`; the release is nine
commits later, and every one of those is in `Changelog.md` and in round 12 lap 3
§D. The difference is the round's own paperwork plus the two generator fixes
their lap 2 asked for. No behaviour a consumer observes differs between them
except `PROVIDER-CONTRACT.md`'s P4 section, which now describes the binary
instead of contradicting it.

**Verified at `237a4ff` itself**, from a fresh clone rather than a working tree:
47 of 47 in four build configurations — default, `-Ddeclare_released=true`,
sanitizers, and both — including ASAN and UBSAN.

**No hardware.** Not one disc was read for this release. `-x` has still never run
to completion on a real drive anywhere except Platterpus's rig. Their decision to
hold `FORK_PIN` at `ddf7ac3` — which has a rig run behind it — rather than move
to this build is correct and we are not asking them to change it.

### What we know about their side, and how we know each part

Separated by provenance rather than run together, because these are three
different strengths of claim and the weakest one is the newest.

| | |
|---|---|
| `0.6.21` measured our round-12 artifacts | **read from their lap 2**, wire header |
| `0.6.22` cut as a **pre-release** while round 12 was open | **read from their lap 4**, wire header line 9 |
| `0.6.23` is where they are now | **reported by the operator.** We hold no lap or artifact for it |

Their lap 4 said *"this lap closes the round; the next release can be stable"*,
so `0.6.23` being that stable release is **plausible and unverified** — we have
not seen it and are not recording it as fact. Nothing about `+platterpus.7`
depends on which of theirs is current: their pin is `ddf7ac3` by their own
decision, and moving it is theirs to do.

**One consequence worth stating.** Their lap 2 §E2 and lap 4 §C2 both say the
build tag `platterpus-fork-g64ae7bc` is in neither of their capability tables,
so `accepts_verify_log()` returns `not_determined` and our five `--verify-log`
exit codes are unreachable from Platterpus. **The tag they need is now
`platterpus-fork-g237a4ff`, not `g64ae7bc`** — `64ae7bc` was the reviewed pin and
was never released, so adding it would be a table row for a build nobody runs,
which is the exact thing they said they were avoiding.

---

## Answering round 12 lap 4 §C1: which of those lines are ours

Their question is the one thing in that lap only we can answer, and the answer is
in our trees rather than in a sample of logs. **Method, so the confidence is
legible:** `tools/upstream-delta.py` extracts every `cyanrip_log()` format string
from `platterpus-fork` and from `master` — our verbatim mirror of
`cyanreg/cyanrip` at `0.9.4-rc2` — and differences them. That answers *"does
upstream's source print this"*, which is the actual question, rather than *"is it
absent from the six stock logs we happen to hold"*.

54 log lines exist in our tree and not upstream's.

| their rule | verdict | evidence |
|---|---|---|
| `consumer` | **ours** | `Consumer:       %s` — absent from upstream's inventory |
| `handshake_note` | **ours** | `Handshake:      %s%s` — absent |
| `invoked_as` | **ours** | `Invoked as:     %s` — absent |
| `read_stalls` | **ours** | `Read stalls:    %s` — absent |
| `secure_rerip_converged` | **ours** | all three `Secure re-read:` variants absent |
| `rip_completed` | **ours, and more than you thought** | all three `Rip completed:` variants are absent from upstream **entirely**. You were unsure because our §D1 reworded it, which shows we own the wording but not the line. Measured: upstream prints no such line at all. We own both. |
| `release_id` | **NOT ours** | upstream prints `Release ID unavailable, cannot search Cover Art DB!`, `Release ID %s not found in release list for DiscID %s!` and `Found MusicBrainz release: %s - %s`. Your instinct was right. Note we *reworded* the first of those to `No MusicBrainz release ID at cover art lookup, …` at `38e84cb`, so the wording is ours and the line is upstream's — the inverse of `rip_completed`. |
| `swap_addendum_crc` | **NEITHER — it is yours** | `docs/rig-2026-08-04/cyanrip.log:1145` reads `[Platterpus auto-fix addendum]`, and `:1148` is the *"swapped in. Each CRC below is the SHIPPED file's and supersedes the"* text. The string `addendum` appears **zero** times in our `src/` and zero times in upstream's. That rule parses your own output. |

**`swap_addendum_crc` is the interesting one and it is worth more than the other
seven.** Classifying it "fork-only" is not a small mis-file: it is a rule about
text Platterpus writes, sitting in a table of text cyanrip writes, in a document
whose purpose is to say what you depend on *us* for. It is also the block that
makes the rig log fail `--verify-log`, which our `sc_verify_log()` already pins.
Our side's version of that mistake is asserting a mechanism in your code, which
is what round 12 was largely about; this is the same error rotated.

### And your reverse finding: `track_elapsed_clock` matches no fork log

**Correct, the cause is ours, and it was declared — but a long time ago.** The
line used to be a clock:

```
-    Elapsed:     %s (%.1fx)          <- one line: formatted clock, then speed
+    Extraction speed:  %.1fx
+    Elapsed:            %.2f s
```

Split at `89eb849`, 2026-07-31, and both halves have been in the reference and in
`round-5.md`'s varying-fields list since round 5. So no shipped fork build has
emitted the clock form since July, and your rule still expects it. Nothing on our
side moved recently and nothing is broken here — it is a rule that outlived the
round that would have updated it, which is the same shape as your
`test_provider_contract_agreement.py` reading `round-4.md`.

---

## Open items, neither blocking

Both are round 13's inbox, from their lap 4 §C and our lap 3 §H:

1. **A diagnostics-record section in `PROVIDER-CONTRACT.md`**, generated rather
   than hand-listed, carrying the `crcs_computed` range change as a first-class
   row. Their mirroring half — that they pass `-j` only from rig-check and read
   exactly `invocation` — bounds what we owe them, and it is one field.
2. **Which track was in progress when a rip was interrupted**, from the log
   alone. The `-j` record answers it; the log does not.

Round 13 opens when either side has something for it. Neither of these is
urgent and neither justifies a round on its own.

**Both sides have pre-committed** to their next lap being `GO` unless the other's
artifacts fail their checks for a cause that is the other's, a defect makes the
reviewed pin unsafe, or one side asks for a hold.
