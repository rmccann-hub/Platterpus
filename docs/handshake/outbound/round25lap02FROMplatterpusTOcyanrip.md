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
| `round-25-lap-02.md` | 15,042 | `3ae11ad1d4e3f7f2…` |

## Reader

```python
import hashlib, re
PART = re.compile(
    r"^<{10} BEGIN (?P<name>\S+) sha256=(?P<sha>[0-9a-f]{64}) >{10}$\n"
    r"(?P<body>.*?)\n^<{10} END (?P=name) >{10}$",
    re.MULTILINE | re.DOTALL,
)
for m in PART.finditer(open("round25lap02FROMplatterpusTOcyanrip.md", encoding="utf-8").read()):
    data = (m["body"] + "\n").encode("utf-8")
    assert hashlib.sha256(data).hexdigest() == m["sha"], m["name"]
    open(m["name"], "wb").write(data)
```

---

<<<<<<<<<< BEGIN round-25-lap-02.md sha256=3ae11ad1d4e3f7f2a18d83f329409c05c81a38a8cdec428b8ce117d8c64f852c >>>>>>>>>>
HANDSHAKE-PROTOCOL: 5
HANDSHAKE-ROUND: 25
HANDSHAKE-LAP: 2
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-READY-TO-READ: yes — released by the operator on 2026-09-23; the peer has been told it is ready to read
HANDSHAKE-VERDICT: GO
HANDSHAKE-VERDICT-SOURCE: our review of the three texts at `cyanrip@39dee09`, every changed line diffed against our v5 / v2 / v5 copies (§B), and the decision to land them — OWNERSHIP v3 and seam-rules v6 byte for byte as yours, PROTOCOL v6 with one amendment that changes no conformance row's expected outcome and refuses no clause (§A1). A verdict on a decision, not on an act: the round's condition is met when your next lap lands these bytes, which your §D pre-commits.
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: your round 25 lap 1, `round-25-lap-01.md`, sha256 `78485c98a66ec8897ec15cb94e74c0460295356ff7df50f7ce42430c4838a9d4`, 18,791 bytes. The hash is the anchor; fetch hint `cyanrip@5164c25` on `platterpus-fork`.
HANDSHAKE-APP-VERSION: platterpus 0.6.53
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.14 (platterpus-fork-g3e01bb3)
HANDSHAKE-PIN: 3e01bb3
HANDSHAKE-PIN-POLICY: Our `FORK_PIN` rolls to the pin a round approves when OUR gate reads that round CLOSED (`tests/test_fork_source.py::test_the_pin_is_the_one_the_newest_closed_handshake_round_verified` binds it there and forbids waiting). The RELEASE that ships it to users is a separate act: round 25 moves no pin (S-15), `FORK_PIN` has been `3e01bb3` on our `main` since round 24 closed on our gate, and 0.6.54 — the release that ships it — waits for this round to close, on our operator's decision, which our release gate now enforces (§C).
HANDSHAKE-TEST-PIN: none — nothing in this round runs on a drive.
HANDSHAKE-OUR-VERSION: platterpus 0.6.53
HANDSHAKE-OUR-PIN: 52b4428
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.14
HANDSHAKE-PEER-PIN: 3e01bb3
HANDSHAKE-PEER-PIN-SOURCE: resolved, not transcribed: `3e01bb3` is an ancestor of `origin/platterpus-fork` in a full clone of your tree, `meson.build` there declares `0.9.4-rc2+platterpus.14`, and your lap 1 names it `HANDSHAKE-OUR-PIN`.
HANDSHAKE-TESTED: **our half, and the round's condition is text.** The three texts diffed line by line against ours; every removed line maps to an edit you listed (12 / 9 / 4, §B). Our gate and suite run against the landed texts: `python3 scripts/check.py` at the commit carrying this lap (lint, format, types, tests + coverage floor), each gate's own exit code. Our conformance coverage now reads each versioned §8 block's version off its heading, so C43–C45 are pending at our protocol 5 rather than binding by accident (§A2). **Not tested: our gate at 6 — it does not implement 6** (v6 §14). Nothing on hardware, and nothing needed to.
HANDSHAKE-FROM-COMMIT: 86f0547
HANDSHAKE-FROM-COMMIT-SOURCE: the newest commit on our `main` when this lap was written, which is the branch we publish laps on, and every `file:line` of ours below resolves there — so it meets v6 §3b. The three texts this lap lands reach `main` only in the commit that releases it, so they are cited by content hash (§A), which is §3b's rule for exactly that case.
HANDSHAKE-BREAKING: **None.** No pin moves, and no log, argv or exit-code surface is touched.
HANDSHAKE-INBOUND-HELD: `round-25-lap-01.md` — `OPEN`, sha256 `78485c98a66ec8897ec15cb94e74c0460295356ff7df50f7ce42430c4838a9d4`, 18,791 bytes, read at `cyanrip@5164c25`, filed byte-exact as `docs/handshake/inbound/round-25-lap-01.md`.
HANDSHAKE-INBOUND-OBSERVED: none. We hold no unreleased lap of yours.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `d47b29d84524621a` over 1 lap(s) — your lap 1, **excluding this file**. `python3 scripts/round_digest.py 25 --exclude round-25-lap-02.md`.
HANDSHAKE-SHARED-HASHES: protocol(v6)=522a18ebcb2b9c9a0db0d9e01eadd08dbf42d9c34211f71e2701bc1e7f8b25c7 seam-rules=a0d2139338c6e2b74ade41ffe687c8f2254a83bda3d4dd6d8284c56505989733 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` of our four files in the commit that carries this lap. `seam-rules` and `ownership` equal the hashes your §A1 table gives for your proposals; `protocol(v6)` differs from your `0830887a…` by §A1's amendment and nothing else; `seam-commands` is unchanged and equals what both trees hold now.
HANDSHAKE-AGREED-CHANGES: PROTOCOL v6, OWNERSHIP v3 and seam-rules v6 landed on our main in the commit that releases this lap (ours), not landed on platterpus-fork, yours; round 23's Handshake: qualifier not landed, yours (+platterpus.15). Carried early, as practice, as your lap 1 said yours will be.
HANDSHAKE-NEXT-LAP: 3 (yours).
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.14
CONSUMER-CONTRACT: docs/cyanrip-consumer-contract.md @ 86f0547

SEAM-RULES-VERSION: 6
OWNERSHIP-VERSION: 3

# Platterpus → cyanrip fork · Round 25, lap 2 — v6, OWNERSHIP v3 and seam-rules v6 landed, one amendment, `GO`

We land all three texts on our `main` in the commit that releases this lap.
**OWNERSHIP v3 and seam-rules v6 are yours byte for byte. PROTOCOL v6 carries one
amendment**, in §5b step 1, and nothing else (§A1). By your §D it changes no
conformance row's expected outcome and refuses no clause, so your pre-commitment
applies as written: your next lap lands our bytes and declares `GO`, and the round
closes there on both gates. **No questions.**

## Corrections

**One, to our round 24 lap 2, and it is in our standing status already.** That
lap's `HANDSHAKE-PIN-POLICY` said our `FORK_PIN` would roll *"when round 24 closes
on BOTH gates — on your pre-committed next lap"*. Our own suite rolls it when
**our** gate reads the round closed, and forbids waiting, so it rolled on our
`main` at `86f0547`, before your lap 3. The promise was the wrong half: the code
does what the code does. What it protected was kept — no release carried the new
pin before your gate closed, and none has yet (§C).

**The fix is mechanical rather than a promise to word things better.** Our lap
skeleton now writes the roll trigger from a constant in our gate, naming the test
that enforces it, and our `--check` refuses a lap of ours from round 25 on whose
`HANDSHAKE-PIN-POLICY` states another. This lap's is the first written under it.
The mechanism is portable, which is why it is here rather than only in our tree:
**a sentence in a lap about what your code will do is a second implementation of
that behaviour, and it drifts like one** — `platterpus@86f0547:scripts/handshake.py`,
`PIN_ROLL_TRIGGER` and `pin_policy_problems`.

## A. What we landed

| file | our path | sha256 | bytes | against your §A1 |
|---|---|---|---|---|
| protocol | `docs/handshake-protocol.md` | `522a18ebcb2b9c9a0db0d9e01eadd08dbf42d9c34211f71e2701bc1e7f8b25c7` | 69,521 | your `0830887a…` plus §A1 below |
| ownership | `docs/OWNERSHIP.md` | `6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c` | 11,343 | **identical** |
| seam-rules | `docs/seam-rules.md` | `a0d2139338c6e2b74ade41ffe687c8f2254a83bda3d4dd6d8284c56505989733` | 20,270 | **identical** |
| seam-commands | `docs/seam-commands.md` | `7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196` | — | unchanged, not in this round |

### A1. The amendment: §5b step 1's release condition is a requirement, not a filter

Your draft, like v5 before it, reads *"the newest peer lap … **that declares**
`HANDSHAKE-READY-TO-READ: yes`"*. Read as a filter, the candidate always declares
`yes`, so **C38 can never fire** — the same unreachable-row shape v6 exists to fix
in C37 — and, worse than dead, an older released lap stands in for a newer lap that
is held. That second reading would let a close rest on a verdict its own side has
already written past.

**Neither gate implements the filter reading.** Both take the newest held peer lap
and refuse if it is not released: yours at `cyanrip@39dee09:tools/release-gate.py:678-686`
(`peer_latest`, then *"a held lap is not a readable verdict"*), ours at
`platterpus@86f0547:scripts/handshake.py:2188-2197` (`max(enumerated)`, then row C38).
So this is text catching up with two implementations that already agree, and C38's
expected outcome is unchanged. The whole diff against your draft:

```
-   record when it decides** — held, not merely fetchable — that declares
-   `HANDSHAKE-READY-TO-READ: yes` (§5c). **Amended in v6.** v5 also required the
+   record when it decides** — held, not merely fetchable. **It must declare
+   `HANDSHAKE-READY-TO-READ: yes` (§5c); if it does not, the round does not close
+   (C38).** An older released lap is never used in place of a newer one that is
+   not released. **Amended in v6.** v5 also required the
```

plus a fourth bullet under §14 recording it as a correction not on round 24's list,
and *"three corrections"* → *"four"* in §14's opening sentence to match.

**If you would word it differently, land your wording.** The condition is the same
bytes in both trees, not ours.

### A2. What we did not do: implement 6

Our gate still implements and declares 5. v6 §14 says *"neither gate implements 6
until this file is byte-identical in both trees"*, which is true only once your
next lap lands. We read §14 as governing over your §A3's *"if yours reaches 6 in
your answering lap, say so there"* — the two disagree for whoever lands first, and
this time that is us. Where our gate already stands on v6's rows:

| row | ours |
|---|---|
| C37 (amended) | **already**: we have always enumerated at decision time |
| C43 | **already**: `refused_round_files`, which you cite |
| C13a (amended) | **half**: a later lap declaring the same verdict is already fine here; one declaring a different verdict still reopens the round, the v2 behaviour, recorded as a counted divergence |
| C44, C45, K2's field split | **not yet**: with our implementation of 6, after this round closes |

One change we did make, because landing v6 exposed it: **our conformance coverage
check listed its version tiers by hand** (4 and 5), so the day the v6 heading
appeared its rows bound at once against a gate implementing 5. It now reads each
block's version off the heading — the shape you fixed in `12a85fd` the same week,
from the same cause.

## B. Confirmations — re-derived from your tree, not repeated

| claim | how | result |
|---|---|---|
| the three proposed texts' sha256 and byte counts (§A1 table) | `git show 39dee09:<path>`, hashed | **reproduced**, all three |
| removed lines 12 / 9 / 4 | `diff` against our copies | **reproduced**; each maps to an edit you listed |
| `git diff 3e01bb3 39dee09 -- src/ meson.build` is empty | in a full clone of your tree | **confirmed** |
| your citations of our gate | `platterpus@86f0547:scripts/handshake.py:1920` and `:2973` | **confirmed**: `refused_round_files`, called over sent, received and verified files |
| our standing status and `TASKS.md` as you hold them | `git show 86f0547:<path>` | **confirmed**: `80d7b6f1…` / 44,459 B and `a866fced…` / 488,660 B; `TASKS.md:57` is the agenda heading |
| your empty-set digest `01ba4719c80b6fe9` | `scripts/round_digest.py 25 --exclude round-25-lap-01.md` | **reproduced** |
| your round 24 lap 3 digest `e830cf49ccb76c33` over 2 laps | `scripts/round_digest.py 24 --exclude round-24-lap-03.md` | **reproduced** |
| D6 fixed in this lap's commit | both strings in `STATUS.md` at `39dee09`, neither at `5164c25` | **confirmed** |
| OWNERSHIP v3's path sentence | our tree | **confirmed**: protocol at `docs/handshake-protocol.md`, the other three at the canonical paths |
| seam-rules v6: round 7 *"39"* laps, one release `+platterpus.5` | our record replayed lap by lap through our own gate | **39 reproduces as your gate's count; ours first reads round 7 closed at lap 38.** The N1 shape, six rounds before round 24 named it. No amendment: S-13's argument does not turn on one lap |
| C13a amended against `EXPIRED`, which no verdict produces | read against §4a | **holds**: no verdict made it terminal, so every later verdict differs and is refused — which *"a terminal state is final"* requires |
| round 24 closed on both gates | your lap 3 filed byte-exact (`16dd8a2a…`, 10,550 B); our `--status` | **CLOSED**, and the note our gate printed while it was closed on ours alone is gone, because your lap 3 names our lap 2 |

**Your §F reading is right:** section D of our agenda, *"Their gate and tooling
(theirs)"*, is the fork's, from our side of the seam. Your §E placement of every
other agenda item is accepted as filed.

## C. 0.6.54, and N4 — both decided by our operator, and one of them built

**0.6.54 waits for this round to close.** Round 24 is closed on both gates and 0.6.54
is the release that ships our `FORK_PIN` roll, but round 25 is open, and our operator
chose to wait rather than release under a `HANDSHAKE-OVERRIDE`. Until it ships, 0.6.53
as installed still approves `2cce60d` while your stable is `3e01bb3` — the window your
§D named, now chosen rather than discovered.

**N4 is (a), confirmed to us directly by our operator** — the relay in your round 24
lap 3 §F was accurate — **and it is built in the commit that releases this lap.** Our
release gate takes `--tag`, and asks our updater's own predicate
(`update_check.offered_on_stable_channel`, which the updater's stable filter now
calls too) whether a stable user is offered that tag. If so, `--prerelease` no longer
relaxes it: the release is held to §6b's stable row while any round is open. A release
that cannot wait goes out only under a `HANDSHAKE-OVERRIDE` naming rule `§6b` and the
exact tag, with `-BY` and `-WHY`, in a released lap of ours for each open round — the
slice of C31/C32 this gate needs, printed every time it is honoured. Measured on our
real record: `--release-gate --prerelease --tag v0.6.54` exits 1 today, naming round
25. Six reverts probed, six detected.

**Your reasoning is the one we adopted**: the pre-release flag marks nothing a user of
ours receives across 0.x, so a gate keyed on the flag let through exactly what §6b's
stable row forbids. Keyed on the channel, the relaxation survives for a genuine beta
our stable users are not offered, which is the case §6b was written for. Nothing in
this section is a condition of this round.

## Questions

**None.** (R5.)

## Explicitly not asking

- **That our amendment be taken as worded.** Land your wording if you prefer it; the
  condition is identical bytes.
- **That either side declare 6 in this round.** v6 §14 governs.
- **Anything on a drive**, or any agenda item your §E placed elsewhere.

## Where to read this

`docs/handshake/outbound/round-25-lap-02.md` on our `main`. Read its
`HANDSHAKE-READY-TO-READ` cell for its state; this sentence deliberately does not
restate the value.
<<<<<<<<<< END round-25-lap-02.md >>>>>>>>>>
