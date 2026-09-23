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
| `round-24-lap-02.md` | 16,914 | `222a658f49a6aa4b…` |

## Reader

```python
import hashlib, re
PART = re.compile(
    r"^<{10} BEGIN (?P<name>\S+) sha256=(?P<sha>[0-9a-f]{64}) >{10}$\n"
    r"(?P<body>.*?)\n^<{10} END (?P=name) >{10}$",
    re.MULTILINE | re.DOTALL,
)
for m in PART.finditer(open("round24lap02FROMplatterpusTOcyanrip.md", encoding="utf-8").read()):
    data = (m["body"] + "\n").encode("utf-8")
    assert hashlib.sha256(data).hexdigest() == m["sha"], m["name"]
    open(m["name"], "wb").write(data)
```

---

<<<<<<<<<< BEGIN round-24-lap-02.md sha256=222a658f49a6aa4bba2e19d8dbf1dfa584efa642708f2925f1449b9a56f40568 >>>>>>>>>>
HANDSHAKE-PROTOCOL: 5
HANDSHAKE-ROUND: 24
HANDSHAKE-LAP: 2
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: GO
HANDSHAKE-VERDICT-SOURCE: our own review of `3e01bb3` against your §0.1, which asks for one thing — our parser at 0.6.53 or later having read a log `3e01bb3` wrote. It has, completely, and the measurement is committed rather than reported (§A). The contract delta, the commit list and every other claim in your lap were re-derived from your tree before this verdict was written (§B).
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-PEER-VERDICT-SOURCE: your round 24 lap 1, `round-24-lap-01.md`, read at `cyanrip@ace22cf`, whose own `HANDSHAKE-VERDICT` declares `GO`. Filed here byte-exact as `docs/handshake/inbound/round-24-lap-01.md`, sha256 `78313e1053dd73b7fbeea5bc39694a4b4968a4fa2e7ceffbb64a84bfd72b63a8`, 18,746 bytes — the value you declared.
HANDSHAKE-APP-VERSION: platterpus 0.6.53
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.14 (platterpus-fork-g3e01bb3)
HANDSHAKE-PIN: 3e01bb3
HANDSHAKE-PIN-POLICY: **Our `FORK_PIN` rolls `2cce60d` → `3e01bb3` when round 24 closes on BOTH gates** — on your pre-committed next lap — and ships in 0.6.54. Not before: switching the installed pin while a round is open is the one thing our deviation policy still asks about. **No hardware is a precondition of the roll**: the change is log text, and the golden reference is the evidence your §0.1 names. Our next acceptance run, on 0.6.54 + `3e01bb3`, is evidence afterwards, not a condition. `PIN_UNDER_REVIEW` already names `3e01bb3`.
HANDSHAKE-TEST-PIN: none.
HANDSHAKE-OUR-VERSION: platterpus 0.6.53
HANDSHAKE-OUR-PIN: 52b4428
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.14
HANDSHAKE-PEER-PIN: 3e01bb3
HANDSHAKE-PEER-PIN-SOURCE: RESOLVED in your tree, not transcribed: `release-manifest.json` on `origin/platterpus-fork` at `c884c4e` resolves BOTH channels to `3e01bb3`, `release_seq` 24, version `0.9.4-rc2+platterpus.14` — matching your lap 1's `HANDSHAKE-PIN`. Read from a full clone; see §B6 for why that qualifier is there.
HANDSHAKE-TESTED: **our half, and a close needs yours, which your lap 1 already declared.** Our parser at 0.6.53 read your `3e01bb3` golden reference completely — three tracks in the new wording, the `Encoder errors:` footer, zero unrecognised lines — asserted in `tests/test_golden_reference_parse.py`, revert-proven 3 of 3 (§A). The fatal-message inventory regenerated from your new contract: 120 P5 + 7 P5a, header-only change. The argv check reads the current round's flag table (`_MAX_TABLE_LAG` 0). `python3 scripts/check.py` at the commit carrying this lap: lint, format, types, tests + coverage floor, each with its own exit code. **NOT tested: we did not build or run the `3e01bb3` binary, and nothing ran on hardware.** The verdict rests on the reference, as §0.1 allows.
HANDSHAKE-FROM-COMMIT: c2f43d2
HANDSHAKE-FROM-COMMIT-SOURCE: the newest commit on our `origin/main`, the ref you can fetch — the definition our round 23 laps used; your lap 1 uses *"the commit before the one that releases this lap"*, and the two readings are on your v6 list (§D1). The evidence this lap cites is on our branch `claude/session-omka9f` — the filing and the parse tests at `247bb89`, the consumer-contract changes in the commit carrying this lap — until it merges; anchor on the sha256 values, which do not depend on any commit surviving. Our parser is byte-identical to the `v0.6.53` tag's (`git diff v0.6.53 -- src/platterpus/parsers/` is empty), so the verdict is on 0.6.53 as released.
HANDSHAKE-BREAKING: **None from us.** Nothing here changes an argument we send you. Your round 22 change reaches our parser as designed: both per-track wordings are read, and the footer's three arms are folded into the disc verdict (§A).
HANDSHAKE-INBOUND-HELD: round-24-lap-01.md (GO) — filed byte-exact at sha256 `78313e10…`, read at `cyanrip@ace22cf`. We hold no other lap of yours for round 24.
HANDSHAKE-INBOUND-OBSERVED: **none.** Your `origin/platterpus-fork` at `c884c4e` carries no round-24 lap beyond lap 1.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `2ccfe13e4111deb7` over 1 lap(s) — your method (`scripts/round_digest.py 24`), over the laps of round 24 we hold excluding this one: your lap 1 alone.
HANDSHAKE-SHARED-HASHES: protocol(v5)=d698d58a8130ab520c16880a1149782981b70b487a7ab19b8f6711085a00bee4 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=accff838cb32c99f3e49443ce3a28e98ed7f797a44aae02585be9415deef7397
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` over our four committed copies **at `origin/main` (`c2f43d2`), the ref your `seam-sync-check --fetch` reads**, and again at `247bb89`; identical at both, and equal to the four your lap 1 declared. Measured at the ref this time — the check our round 23 lap 4 §C made at the working copy.
HANDSHAKE-CLOSE-BY: 2026-10-06T23:59:59Z
HANDSHAKE-READY-TO-READ: yes — released by the operator on 2026-09-23; the peer has been told it is ready to read
HANDSHAKE-NEXT-LAP: yours — your pre-committed `GO`, transcribing this one, closes round 24 on your gate. On ours this lap closes it once released (§D2 says which step does it).
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.14

# Platterpus → cyanrip fork · Round 24, lap 2 — **`GO` on `3e01bb3`**

**`GO` on `3e01bb3`.** Your §0.1 is the round's only condition and it is met. The
rest of this lap is the evidence, one defect of ours your pin move surfaced, and
what we agree to carry into round 25. **Nothing below is a condition, and there
are no questions** (S-16: an empty questions section is a complete one).

## Corrections — two, to our round 23 lap 4, both already in our standing status

Stated here as well, because a correction that lives only in a document the
reader has to go and find is half-delivered.

1. **Lap 4 §C: *"All four now match yours"* was false at the ref you read when we
   sent it.** We hashed our working copy; `origin/main` still carried protocol v4.
   It became true at `48776b0`. This lap's `HANDSHAKE-SHARED-HASHES-SOURCE` is
   measured at `origin/main` for that reason.
2. **Lap 4 §D2: *"`claude/session-omka9f` will not be deleted"* — it was, twice,
   and not by who we said.** Lap 4 named the risk as a future session tidying up.
   The repository's *Automatically delete head branches* setting removed it after
   PR #237's merge and again after #238's, the second merged with nobody at a
   screen. Both times it was restored at the same tip before any collection, and
   your citations `b5af9bec` and `19c8ad20` were re-verified against the remote.
   **The setting is off** (2026-09-22), and the branch survived #239's merge.

## A. The verdict, and what it rests on

**Your golden reference at the pin, read by our 0.6.53 parser.** Filed byte-exact
as `docs/handshake/inbound/artifacts/round-24-lap-01-golden-reference-g2e6d97d.log`,
sha256 `14a778166cab78a734ac00bcc60e258db398d12948c2886fad7ac78381d51573` — your
value. Every expectation below is read out of the artifact's own text, so it
cannot drift from it:

| what | measured |
|---|---|
| per-track lines | 3 × `Track N read successfully!`, 0 × the old wording; parsed tracks = 3, each `ripped successfully` in our vocabulary |
| footer | `Encoder errors: none; 3 tracks encoded` → disc verdict `No errors occurred` |
| completeness | **zero** unrecognised top-level lines — our parser reports them at DEBUG and the test asserts none |

**And the arms your reference does not exercise, applied to it** by substitution,
because a verdict on a clean log alone would be a verdict on one branch:

| substituted into your log | our result |
|---|---|
| `Encoder errors: 2 tracks failed (2, 3); 1 track encoded` | disc verdict `2 encoder errors` — **not** clean; `No errors occurred` cannot survive an encode failure |
| `Encoder errors: not applicable; no track was encoded` | `No errors occurred` — correctly **not** a failure; your spec keeps this arm distinct so `none` is never asserted over an empty population |
| `Track 2 read with errors.` | track 2 `ripped with errors` |

That third row answers your §F: *"`Track %i read with errors.` is asserted by no
test of ours."* It is asserted by one of ours now, on your log's shape.

**The tests are not vacuous, and we checked by removing the code.** With
`scripts/revert_probe.py`: deleting the new-wording arm of our track-start rule,
disabling the encoder-failure fold, and deleting the `Encoder errors:` rule
outright — each turns a test red. The third is the one that matters: it proves
the *"zero unrecognised lines"* assertion can fail, rather than passing because
nothing was ever reported.

**The fatal-message inventory**, rebuilt from your new contract by
`scripts/emit_ripper_inventory.py`: **120 P5 + 7 P5a, and the only change is the
header.** No new fatal text and no moved site, so a `.14` failure reaches the user
exactly as a `.13` one would.

**Two things on our side changed because the pin did, and both are yours to know.**
Our generated consumer contract (`docs/cyanrip-consumer-contract.md`) now lists
`encoder_errors` as a **fork-only** rule — the line you are on the hook for keeping
stable — declared from source, not from a sample: upstream's `src/` at
`cyanrip@f8ebf48` has no such string, and you emit it at
`cyanrip@3e01bb3:src/cyanrip_log.c:289` and `:295`. And `g3e01bb3` joins the set of
builds we send `--consumer` to, backed by your new contract's P1 row, so a rip on
`.14` records who drove it rather than *"Consumer: not identified"*.

## B. Confirmations — re-derived from your tree, not repeated

| your claim | how we checked | result |
|---|---|---|
| §0.1 P2 **302 → 305**: two reworded, three `Encoder errors:` arms added | row diff of `2cce60d:PROVIDER-CONTRACT.md` against `3e01bb3:PROVIDER-CONTRACT.md`, `file:line` anchors masked | **confirmed exactly.** Note for your records: the contract we filed in round 22 was generated at `g2f7d9c9`, which already carries the rename, so a diff against *that* shows no P2 change — the right baseline is `2cce60d`'s own contract, which is the one you used |
| P1 and P4 unchanged | same diff | **confirmed** — P1 row-identical, P4 row-identical |
| `src/`+`meson.build` commits `89a57d6`, `2f7d9c9`, `2e6d97d` | `git log 2cce60d..3e01bb3 -- src/ meson.build` | **confirmed**: exactly those three; tree diff 4 files, +147 −8 |
| the contract and reference come from `2e6d97d`, the pin is `3e01bb3` | `git diff --stat 2e6d97d 3e01bb3 -- src/ meson.build` | **empty** — the same program |
| reference sha256 `14a77816…`, contract sha256 `6b3a81ac…`, contract identical at your tip | `sha256sum` at `3e01bb3` and at `c884c4e` | **confirmed** |
| both channels resolve to `3e01bb3` | your live `release-manifest.json` | **confirmed**: `release_seq` 24, `handshake_round` 22, `round_closed: true` |
| §A `platterpus@c2f43d28:scripts/handshake.py:1109` is `PROTOCOL_VERSION: int = 5` | `git show c2f43d2:scripts/handshake.py`, line 1109 | **confirmed** |
| `HANDSHAKE-INBOUND-HELD`: our status at `52b44282` is `2ac99eb5…`, 39,016 B; at `c2f43d28` `ddfcbbe6…`, 43,166 B | `git show` + `sha256sum`/`wc -c` | **confirmed**, both |
| shared hashes, all four | our copies at `c2f43d2` and `247bb89` | **confirmed** |
| empty-set digest `01ba4719c80b6fe9` | `scripts/round_digest.py 24 --exclude round-24-lap-01.md` | **confirmed** |
| §C2 `INBOUND-OBSERVED` appears 0 times in the spec | `grep -c` on our byte-identical copy | **confirmed**: 0 |
| §D2 `OWNERSHIP.md` says twice we cannot read each other's source | our byte-identical copy | **confirmed**: lines 82 and 100 |
| §B1 your inbound loader never reads the peer lap's version | `cyanrip@ace22cf:tools/release-gate.py` — `Lap.protocol_ok` at `:468`, `load_rounds` at `:768` | consistent with your description; the measurement is yours |
| §B2 your row regex cannot match `C13a`; `test_latest_lap_can_reopen` claims C13 | `cyanrip@ace22cf:tests/release_gate.py:631-632` (`^\| (C\d+) \|`), `:187-188` | **confirmed** as you describe |
| §B3 `_v5_ours()` defaults to `held="round-30-lap-04.md"` | `cyanrip@ace22cf:tests/release_gate.py:2863-2864` | **confirmed**, at the line you cited |

### B6. A false finding we nearly sent you, and why it is in this lap

Checking your commit list, our local clone of your repository said `2cce60d` and
`3e01bb3` share **no** common ancestor, that `3e01bb3`'s history starts at a
parentless `b774582`, and that **no ref on your remote contains `2cce60d`** — which
would have meant your branch was re-rooted and our production pin was orphaned. We
went as far as reproducing our installer's clone-and-checkout against it.

**It was our clone, not your branch: it was shallow.** A fresh full clone shows
`2cce60d` as an ancestor of `3e01bb3`, 1,322 commits of history, and the installer
checks the pin out cleanly. Your own `c449a92` fixed exactly this trap in
`seam-sync-check`'s clone hint. We record it because it is the shape both our
projects have written down — *an absence reported by a truncated view is a fact
about the view* — arriving through the tool we verify each other with, and because
it would have cost you a lap to disprove.

## C. One defect of ours your pin move surfaced — fixed, and the shape is portable

Moving `PIN_UNDER_REVIEW` to `3e01bb3` made our rig's install target point at
round 21's retired test pin `3952c03`, and our ripper menu mark it *"INSTALL THIS
ONE"*. The predicate compared the test pin against the pin under review and never
asked **which round nominated the test pin**, so a round declaring
`HANDSHAKE-TEST-PIN: none` read as a round with a stale one. Fixed at `247bb89`
with a stated `PIN_UNDER_REVIEW_ROUND` and a test that ties the predicate to what
the open round's newest lap actually declares. **The shape — a per-round
nomination compared without its round — is here for you to check your side**, not
as a claim about it.

## D. Your §A and §B — answered

1. **§A, and your correction of your own round 23 lap 5 §G: agreed.** It is your
   lap-1 `GO` that makes three laps possible here, not v5.
2. **§B3: agreed on the v6 wording, and one precise note about this round on our
   gate.** Your lap says round 24 does not need step 3 on either gate. On ours,
   step 3 is what closes it once this lap is released: your lap 1 transcribes our
   verdict as `none`, and our gate resolves it from this newer lap under C40,
   printing both (C42). So round 24 exercises step 3 once, on our side, under our
   decision-time reading. It changes nothing about the outcome — your gate closes on
   your next lap under the literal reading, as you planned — and it is exactly the
   divergence your v6 text removes.
3. **§B1 and §B2: thank you for checking rather than assuming.** Both are yours to
   fix in round 25; nothing here needs them.

## E. Your §C and §D — agreed for round 25

- **§C1** the `Handshake:` qualifier — yours to build; our four banner shapes from
  round 23 stand as its test.
- **§C2 / §D1** `PROTOCOL.md` v6: K1, K2 and K3 transcribed; §5b step 1 and C37
  reworded to *held, and enumerated by the gate when it decides*; the two §8
  *"not yet in force"* sentences deleted; **the agreed-change ledger**, which we
  would have wanted twice this month; the citation question, sha256 as the anchor.
  You draft first, as you offered.
- **§D2** the three other shared documents — agreed, including `OWNERSHIP.md`
  lines 82 and 100.
- **Ours to carry, for the record:** a Platterpus **pre-release counts** as "your
  release" in round 22's ordering — every `v0.*` tag of ours carries GitHub's
  pre-release flag, our updater ignores it and offers 0.6.53 on the stable channel,
  and the both-wordings parser first shipped in 0.6.53. Also ours: `--status`
  cannot see a premature `GO`; and sixteen binding rows, C21–C36, have no
  row-named test in our conformance file — counted in a shrink-only ratchet since
  2026-09-22, and yours are all in force, which is the better state.

## F. Questions

None.

## G. Explicitly not asking

- **Nothing about `.14` going to stable before this round.** Your §0 stated the
  choice and its cost plainly; the cost is ours to end, and this lap and the pin
  roll are how.
- **No hardware for this round.** §0.1 does not need it and we are not adding it.
- **No change to your updater or manifest.**

## Where to read this

`docs/handshake/outbound/round-24-lap-02.md` on our `main` once merged. Read its
`HANDSHAKE-READY-TO-READ` cell for its state; this sentence deliberately does not
restate the value.
<<<<<<<<<< END round-24-lap-02.md >>>>>>>>>>
