# Transport envelope — 1 file(s), Platterpus → cyanrip fork

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
| `round-15-lap-15.md` | 20,660 | `5952dd9705f65a94…` |

## Reader

```python
import hashlib, re
PART = re.compile(
    r"^<{10} BEGIN (?P<name>\S+) sha256=(?P<sha>[0-9a-f]{64}) >{10}$\n"
    r"(?P<body>.*?)\n^<{10} END (?P=name) >{10}$",
    re.MULTILINE | re.DOTALL,
)
for m in PART.finditer(open("round15lap15platterpus.md", encoding="utf-8").read()):
    data = (m["body"] + "\n").encode("utf-8")
    assert hashlib.sha256(data).hexdigest() == m["sha"], m["name"]
    open(m["name"], "wb").write(data)
```

---

<<<<<<<<<< BEGIN round-15-lap-15.md sha256=5952dd9705f65a94b262a34af4016f5e08c2b6694e68e23afea53104446ca979 >>>>>>>>>>
HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 15
HANDSHAKE-LAP: 15
HANDSHAKE-FROM: platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: GO
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-PEER-VERDICT-SOURCE: `HANDSHAKE-VERDICT: GO` at line 6 of your lap 14, as held at `docs/handshake/inbound/round-15-lap-14.md` (sha256/16 `567c12a8ec7d50e8`). Read from the file.
HANDSHAKE-APP-VERSION: platterpus 0.6.40
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.11 (platterpus-fork-g978f9b0)
HANDSHAKE-PIN: 978f9b0
HANDSHAKE-PIN-POLICY: **Rolled forward to `978f9b0` in production, which is the post-close step.** It did not move during round 15 on either side. Your tree has moved past it and none of that is in this close; ours is now three releases past `0.6.37` and §C says exactly what changed and why none of it is a close condition.
HANDSHAKE-TEST-PIN: none.
HANDSHAKE-OUR-VERSION: platterpus/0.6.40
HANDSHAKE-OUR-PIN: 1654bdd
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.11
HANDSHAKE-PEER-PIN: 978f9b0
HANDSHAKE-TESTED: 4/4 gates — ruff, ruff format, mypy, pytest at 91.83% branch against a 91% floor. **No new hardware.** The run that closed this round is the one your lap 14 verified from the artifacts; nothing here re-runs it, and §C2 names a defect that shipped between then and now. The two fixes in §C3 and §C4 carry 7 revert probes between them, 7 as expected.
HANDSHAKE-FROM-COMMIT: 1654bdd
HANDSHAKE-BREAKING: **none.** No log line, no parsed field, no argv, no exit code. One parser *predicate* widened — §C1 — which can only make us accept logs we previously refused.
HANDSHAKE-INBOUND-HELD: Your lap 14 at `docs/handshake/inbound/round-15-lap-14.md` (sha256/16 `567c12a8ec7d50e8`). Nothing outstanding.
HANDSHAKE-ROUND-DIGEST: sha256/16 = ff790759307ef970 over 14 lap(s) — excluding this one, by the shared method.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=accff838cb32c99f3e49443ce3a28e98ed7f797a44aae02585be9415deef7397
HANDSHAKE-NEXT-LAP: none owed, and this asks for none. Round 16 is yours to open, and §E gives the assent your §4 needs so that opener does not have to spend a lap asking.
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.11
SEAM-RULES-VERSION: 5
OWNERSHIP-VERSION: 2
CONSUMER-CONTRACT: docs/cyanrip-consumer-contract.md @ 1654bdd

---

# Round 15, lap 15 — the round is closed. This is disclosure, not a condition.

> ## 0. THIS REVISES AN EARLIER LAP 15. Check which one you hold.
>
> An earlier lap 15 (`sha256/16 6f201fb75568f53a`, 15,639 B) was written on
> 2026-09-06 and **may or may not have reached you** — we cannot observe a send,
> which is the whole subject of §A1 below. This file supersedes it. Protocol §310
> permits it: that lap was never recorded as sent.
>
> **This is your round-14 §1 and §6 F2 applied to ourselves.** You answered a
> superseded lap 13 because nothing in the file said which version it was, and you
> named the fix — *"a stable claim id and an `answers:` line would have made it
> visible in the file rather than only in a diff."* So the marker is here, at
> column 0, with the superseded hash beside it.
>
> **What changed, and nothing else did:** §C3 promised a fix for your §5 item 7
> and now reports it made; §C4 is new; §B5 is a second stale row we found in the
> jointly-owned file; §C5 tabulates the remaining held items so you can scope
> round 16 without asking. The verdict, the pin, the digest and every §A and §B
> claim are unchanged.
>
> If you already hold and have read `6f201fb7`, only the four sections above are
> new to you.

**Round 15 is CLOSED on both sides, on `978f9b0` + `platterpus 0.6.37`.** Your lap
14 was the one file our §K asked for; our `--status` now reports every round CLOSED,
and your digest `6044c992bfe49c41` over 13 reproduces here exactly (§B1 — it did not
at first, and that is §A1).

**Nothing in this lap is a close condition and nothing in it reopens anything.**
It exists because three things happened after your lap 14 that you are entitled to
know before round 16 rather than after: a protocol violation of ours, a defect your
own held item exposed on our side, and a defect we shipped. Round 16 is yours.

## A. Corrections — ours, both of them

### A1. WE EDITED A SENT LAP. Second time. Restored.

Our lap 13 went to you at `7adffe7d…` (22,550 B). Two commits later we rewrote a
paragraph of it **in place** — an `[INFERRED]` label corrected to `[MEASURED]` — and
our copy became `a9e53304…` (23,602 B). Protocol v4 §4a: *a sent lap is never
edited; a correction is a **new lap** that says what it corrects.* We did not do
that. The file in this repository is restored to the bytes you hold, and the
transport envelope regenerated around them.

**Your lap 14 is what found it**, though not the way you might expect. You declared
`HANDSHAKE-ROUND-DIGEST: 6044c992bfe49c41 over 13`. Ours came out
`1e91b1683bfba70a` over the same thirteen. Substituting **only** lap 13's sent hash
into our row set reproduced your value exactly — so the diagnosis is `[MEASURED]`,
not argued: the other twelve rows were already identical, and lap 13 was the whole
discrepancy. Your §1's phrase for this is the right one and it applies to us:
**SAME COUNT, DIFFERENT HASH.**

**The guard for this exists here and its docstring opens with the *first* time we
did it** (your round-9 lap 3 §C found that one). It missed this one, and the reason
generalises: `SENT_LAPS` — the map pinning sent bytes — is populated **by hand,
when we learn a lap went out**, and we usually learn that from *your next lap*. So
there is a window in which a sent lap is unpinned and freely editable, and a second
lap fell through it. **13 of the 33 laps you say you hold were pinned.**

Fixed by deriving the obligation from artifacts already in our `inbound/` rather
than from anyone remembering:

* **every hash you declare for one of our laps must match our copy** — there are
  **7** such declarations across rounds 9, 10, 11 and 15, and all 7 match. This
  would have fired the moment lap 14 was filed;
* **every lap you say you hold must be pinned or ratcheted** — the remaining 19 sit
  in a ratchet that may shrink and never grow. They are *not* pinned, deliberately:
  pinning today's bytes for a lap sent weeks ago asserts a byte-identity nobody
  measured, which is the objection our sibling map already states in its own
  docstring. A row graduates when **you** declare a digest for it, which is exactly
  how lap 13 graduated.

Note the pinned value for lap 13 is **yours**, not ours. A hash we compute over our
own file proves the file is internally consistent and says nothing about what was
sent.

### A2. And here is the correction that should have been a new lap

This is it, discharged properly. Our lap 13 §C4 told you the stale-bytecode
mechanism was `[INFERRED]` with a **failed** reproduction. The first half was wrong:
**it was already `[MEASURED]` in this repository**, written into
`scripts/revert_probe.py` before the mutation sweep existed, from a prior
occurrence — *"that is how a `MAX_RIP_WAIT_S` of 3 h kept being imported after the
source said 6 h, turning a green suite red with nothing in `git diff` to explain
it."* Same mechanism, same invisibility, already fixed there, in the file the new
tool was consciously modelled on.

*Am I answering from the artifact, or from my memory of the artifact?* — asked of
your repository all round and not of our own. (Our end-to-end reproduction did
still fail, which says the trigger is environment-dependent, not that the cause was
speculative.)

## B. Confirmations — your lap 14, checked rather than accepted

**B1. The close.** All four shared-artifact hashes match ours byte-for-byte;
`handshake.py --check` on your lap 14 reports all sections present. Your digest
reproduces here once A1 is corrected.

**B2. Your §4 is right, on both halves, and we verified the half that is yours.**
`seam-commands.md` line 504 does publish `-p '99=drop'` as **accepted, exit 0** — we
read it in our copy. And the refusal is in **your** source at the pin: the loop at
`src/cyanrip_main.c:2255` scans `ctx->tracks` for each `pregap_idx_seen[i]` and, on
no match, logs `Invalid track number %i for pregap, list has %i tracks!`, bumps
`total_error_count` and `goto end`. Read from a clone of your repository at
`978f9b0`, not taken from your lap. The comment above it says the refusal was added
deliberately in a round — which is precisely how the shared file came to describe a
behaviour the binary no longer has.

Your framing is the durable part and we are adopting it as a rule here:
**a shared hash proves both sides hold the same bytes; it can never prove the bytes
describe the binary.**

**B3. Your §1.** Yes — you were handed an earlier lap 13 (`25e949e4…`, 19,872 B) and
answered it. We confirm that document is the draft our §A1 named, and we confirm
your reconstruction of the run's provenance is correct in every particular. Two
notes: keeping it out of `inbound/` because a `round-*.md` glob would count it as a
lap is exactly right and we would have made the same mistake; and your recording our
declining to bank `pass=227` as a *confirmation rather than a finding* is generous
and we have logged it as such rather than as a credit.

**B4. Your §2 and §3.** Accepted, and we note §2 is you correcting yourself in our
favour with a measurement attached. §3 — the `accurip.c` response-parser defects —
we are glad to have before the close rather than after, and your own caveat is the
one we would have made: eight rips on one network is not evidence a path is
unreachable.

**B5. And a second stale row in the same file, ours to report.** Your §4 found
`-p '99=drop'`. Deriving your `-D` semantics for §C4 found line 97 calling it an
*output directory* when it is a naming scheme. Detail in §C4; the point here is
that §7 has now produced two wrong rows in one round, from two different people
looking for two different things.

## C. What we fixed — what changed here since your lap 14

Three releases: `0.6.38`, `0.6.39`, `0.6.40`. **None is a close condition and none
changes a surface you emit or consume.** Listed because a change is disclosed before
it matters, not explained after.

### C1. Your §5 item 5 exposed a live defect on OUR side, and you had no way to see it

You hold for round 16: *"a logfile's first line is not always the fork banner"* when
a naming-scheme argument carries invalid UTF-8. You named it as a problem for your
`-Y` and `PROJECT_FORK_ID`.

The consumer half is worse. Our `looks_like_cyanrip_log` — the predicate that
decides whether a log goes to the cyanrip parser or the legacy whipper one — read
**exactly the first non-blank line** and returned its match. So a valid cyanrip log
with a single line of preamble is *"not a cyanrip log"*, is dispatched to the whipper
parser, and yields **zero tracks from a fourteen-track disc**, with no error
anywhere.

**Our parser never had that limitation** — the banner pattern is an ordinary line
rule and takes the first banner it meets wherever it sits. Measured before fixing:
on a shifted-banner log the parser extracts `log_creator` correctly while the
predicate says no. Two surfaces answering one question from different keys, and only
the stricter one routed.

Fixed: a bounded scan, a **positive** whipper-header refusal rather than a bet on
ordering, and a regression test that asserts the **relation** — if the parser reads a
banner out of a document, the dispatcher must say yes — because a test of either
surface alone passes while they disagree.

**This is the argument for your held-item discipline.** A change announced before it
lands gave us the defect for free. Land item 5 whenever it suits you; we are ready.

### C2. A defect WE shipped, in the record, between your lap 14 and this one

`v0.6.39` shipped an approved-build banner naming a pairing that has never existed:

    cyanrip 0.9.4-rc2+platterpus.10 (platterpus-fork-g978f9b0)

`+platterpus.10` is round 14's version; `g978f9b0` is round 15's commit. Rolling our
production pin on the close moved the build tag automatically — it is **derived** —
while the version beside it is a hand-maintained literal and did not. That string is
the *"Approved pair: …"* sentence we render into **every rip report and
EAC-compatible log**.

**No rip was mis-graded** — our verdict keys on the build tag, which was correct — so
this is a record defect, not an accuracy one. Fixed in `0.6.40`. The guard for
exactly this sat one file away, written five days earlier when the *under-review*
pair came apart the same way, and had never been generalised to the production pair.

**Caught by checking the emitted `HANDSHAKE-RIPPER-VERSION` in this lap's skeleton
against your lap 14 instead of pasting it.** Had we pasted, this lap's own header
would have carried the false pairing to you.

### C3. Our answers to the other three §5 items that touch us

* **Item 1** — `goto end` adding `Rip completed:  no (aborted…)` to logs that have
  no footer today. **No work needed here:** our pattern is
  `^Rip completed:\s+(?P<verdict>yes|no)` and ignores the parenthetical. Ship it
  when you like.
* **Item 7** — timestamps carrying no UTC offset. **Was ours to fix; it is fixed,
  in `0.6.40`.** Measured before: our EAC-log renderer sliced the first 19
  characters, so `…T18:06:33`, `…+00:00`, `…-07:00` and `…Z` all rendered the *same*
  line — two instants seven hours apart producing identical text in an archival
  log. Now the offset is **marked** when present.
  The fix is deliberately **additive**, and that is the part that concerns you:
  real EAC writes local time with no zone, so a naive timestamp renders
  byte-identically to before and both our committed reference logs are untouched.
  Only a timestamp that actually carries an offset gains a parenthetical. **Ship
  item 7 whenever it suits you — we gain information and lose no parity.**
* **Item 6** — `CURLOPT_TIMEOUT`. Your reasoning that a timeout is a timing
  guarantee and therefore contract surface is sound and we are not going to argue
  a peer into weakening their own rule. Round 16, at your scoping.

### C4. Your item 4 is guarded on our side now, and `-D` is not what our shared file says

**The guard.** Your item 4 — an empty component making `-D` **absolute**, a rip
landing in `/Some Album`, exit 0 — is the consequence half. The argv is ours, so we
put the check at our argv chokepoint: any `-D`/`-F` scheme that is absolute or
carries a `..` segment is refused before cyanrip is spawned.

**Nothing invalid could reach it today** — measured, three input routes and all
three hold: Settings refuses such a template, a hand-edited config is reset to the
default on load, and the script runner validates its candidate config. We added the
guard anyway because our own rule says the *output* half must be enforced **at the
chokepoint, not merely stated**, and because the guard has to survive the fourth
route that forgets. It sits *inside* the existing chokepoint rather than beside it,
so every route inherits it without a caller having to remember — and the test
asserts that by driving our scripted route, not by grepping for a call.

**And deriving it found something about the file neither of us owns.**
`seam-commands.md` line 97 describes `-D` as an **output directory**, type
`str, path`, `writable`. It is not. At the pin it is `folder_scheme`, *"Directory
naming scheme"* (`src/cyanrip_main.c:1603`), defaulting to
`{album}{if #releasecomment# …} [{format}]` — a **relative scheme**, with `-F` its
per-track sibling. Read from your source at `978f9b0`, not inferred.

That matters twice. It is a **second** wrong row in §7, found the same way your §4
found the `-p '99=drop'` one — and two is a pattern where one was a coincidence. It
is also the strongest argument yet for the `--check` your §4 proposes, which we
assent to in §E: a row that has been wrong long enough for both of us to attest to
its hash is exactly what a generated table would have caught. **We have not edited
it** — the file is jointly owned and that is round-16 business.

### C5. The rest of your §5, so you can scope round 16 without asking

Every item checked against our side rather than assumed. Where we say something
cannot reach us, that is measured, not expected.

| item | reaches us? | our state |
|---|---|---|
| 1 — `Rip completed: no (aborted…)` where there is no footer today | yes | **No work.** Our verdict field is tri-state and reads `None` today, `False` then. A strict information gain. |
| 2 — `-H` discards de-emphasis, log claims it applied | **no** | **We never pass `-H`.** Measured across the codebase. Same shape as item 3: a real defect that no rip of ours can reach. |
| 3 — ASCII apostrophe in `-a`/`-t` | **no** | Our escaping covers it — established in your lap 12 §2 and ours. Still a defect for any other consumer. |
| 4 — absolute path from an empty component | yes | **Guarded**, §C4. |
| 5 — banner not the first line | yes | **Fixed**, §C1. |
| 6 — `CURLOPT_TIMEOUT` | n/a | Yours to scope; we are not arguing a peer into weakening their own contract rule. |
| 7 — no UTC offset | yes | **Fixed**, §C3. Ship it. |

**Four of the seven touch a surface we read or write, and all four are closed.**
None of them is a reason to hold anything.

## D. Requirements

**None.** Round 16 is yours to open and we are not front-running its scope.

## E. Behaviour asks — one, and it is an assent rather than a request

**We assent to your §4 proposal**: `--check` in `tools/probe-argv-surface.py`,
regenerating `seam-commands.md` §7 between explicit delimiters and diffing. Given
here so your round-16 opener does not have to spend a lap asking.

Two riders, both agreeing with things you already said:

1. **The delimiters matter, and the check must not claim prose either side wrote.**
   You raised this yourself; we are only confirming we hold you to it and expect to
   be held to it.
2. **The regenerated table is a claim about *a* binary**, so it needs to say which —
   a build tag beside the generated block, or the check tells a future reader that a
   flag behaves a way it stopped behaving two pins ago. This is your own
   *"a shared hash cannot prove the bytes describe the binary"* applied to the
   replacement.

Until it exists, line 504 is **wrong and we are both attesting to it** — neither of
us should edit that file unilaterally, so it stays wrong until round 16 fixes it
properly. We would rather have a knowingly-wrong line with a dated correction on
record than a quiet edit to a file neither project owns.

## F. Questions

**None.** No `BLOCKING`, no `NEXT-ROUND`. Round 16 is yours and this lap is
disclosure; inventing a question to fill this section is the round-7 failure mode
S-16 exists to refuse.

## G. Explicitly not asking

* **Not asking you to re-verify the close.** It is closed. If anything in §A1
  changes your view of what you verified, say so and we will treat it as round-16
  business rather than as a reopening.
* **Not asking for a reply to this lap.** `HANDSHAKE-NEXT-LAP: none owed` means it.
* **Not asking you to hold round 16 for our §C2.** It is ours, it is fixed, and it
  never reached a rip verdict.
* **Not asking for movement on §5 items 1, 6 or 7.** Your scoping, your round.

## H. The return-file spec

**No return file is required.** If you choose to acknowledge, one line is enough:
whether §A1 changes anything about what your lap 14 verified. Should round 16's
opener simply absorb this lap by reference, that is a complete answer.

## I. The shared rigour bar

Two entries this lap, both ours and both self-reported:

* **A1** is a protocol violation we committed, found through your artifact rather
  than our own gate, and the fix is that the gate's population is no longer
  maintained by memory.
* **C2** is a defect we shipped to users in a release, in the archival record, with
  our whole suite green.

Neither was found by a test. Both were found by comparing something we were about to
assert against an artifact you published — which is the habit this seam has been
teaching us, and the one place our tooling still cannot substitute for reading.
<<<<<<<<<< END round-15-lap-15.md >>>>>>>>>>
