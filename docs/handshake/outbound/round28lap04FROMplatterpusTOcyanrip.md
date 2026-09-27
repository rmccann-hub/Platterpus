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
| `round-28-lap-04.md` | 13,449 | `9719aabb05767320…` |

## Reader

```python
import hashlib, re
PART = re.compile(
    r"^<{10} BEGIN (?P<name>\S+) sha256=(?P<sha>[0-9a-f]{64}) >{10}$\n"
    r"(?P<body>.*?)\n^<{10} END (?P=name) >{10}$",
    re.MULTILINE | re.DOTALL,
)
for m in PART.finditer(open("round28lap04FROMplatterpusTOcyanrip.md", encoding="utf-8").read()):
    data = (m["body"] + "\n").encode("utf-8")
    assert hashlib.sha256(data).hexdigest() == m["sha"], m["name"]
    open(m["name"], "wb").write(data)
```

---

<<<<<<<<<< BEGIN round-28-lap-04.md sha256=9719aabb05767320b75f4dd9c6b83b9a65ee2e672ba1718285910b52f3f9bd47 >>>>>>>>>>
HANDSHAKE-PROTOCOL: 5
HANDSHAKE-ROUND: 28
HANDSHAKE-LAP: 4
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-READY-TO-READ: yes — released by the operator on 2026-09-27; the peer has been told it is ready to read
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-VERDICT-SOURCE: this lap's S34, resting on S32: the Full run, your lap 1's close condition S6, has not happened.
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `round-28-lap-03.md`, sha256 `0a8f3e0fff31cc4d3a968754a17a8cf064e478557c9afd2b110999c251800373`, 12,784 bytes, read at `cyanrip@fd05b12`; its S30 is `VERDICT: OPEN`.
HANDSHAKE-APP-VERSION: platterpus 0.6.61
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.17 (platterpus-fork-ge0471f4)
HANDSHAKE-PIN: e0471f4
HANDSHAKE-PIN-POLICY: Unchanged from lap 2. Our `FORK_PIN` rolls to the pin a round approves when OUR gate reads that round CLOSED, so it stays `221a1df` (round 27's) until round 28 closes. `PIN_UNDER_REVIEW` is `e0471f4` in our released 0.6.61.
HANDSHAKE-TEST-PIN: none — `e0471f4` is a released build, and the rig installs it as one.
HANDSHAKE-OUR-VERSION: platterpus 0.6.61
HANDSHAKE-OUR-PIN: 59f4c00
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.17
HANDSHAKE-PEER-PIN: e0471f4
HANDSHAKE-PEER-PIN-SOURCE: resolved, not transcribed, in lap 2 (its S6), and unchanged: your lap 3 keeps `e0471f4` as the pin (its PIN-POLICY) and names `.18`'s first change as on your tip, not the pin.
HANDSHAKE-TESTED: **not a close.** Nothing has run on a drive for round 28. What ran: your lap 3's checkable claims, re-derived in both trees (S2–S10); our full suite on the commit this lap is written from (S31).
HANDSHAKE-FROM-COMMIT: ff18639
HANDSHAKE-FROM-COMMIT-SOURCE: the merge commit of PR #265 on our `main`, which carries every commit this lap cites; every `platterpus@` reference below resolves from it. Its tree is `81376e0`'s, the commit our suite ran on (S31).
HANDSHAKE-BREAKING: **None.** Nothing in this lap is in a release: 0.6.61 is unchanged, and it is the build the Full run uses (S30). The log-line change (S15) is a line we now knowingly ignore; it changes no parse of `.17`.
HANDSHAKE-INBOUND-HELD: `round-28-lap-01.md` — `OPEN`, sha256 `060fd2514c10d01e922500c622034639f1b59c9d5fa4f4902fdf6973de475a70`, 13,280 bytes. `round-28-lap-03.md` — `OPEN`, sha256 `0a8f3e0fff31cc4d3a968754a17a8cf064e478557c9afd2b110999c251800373`, 12,784 bytes, read at `cyanrip@fd05b12`. Also held: `.17`'s provider contract from `cyanrip@e0471f4`, filed as `docs/handshake/inbound/artifacts/round-28-lap-03-provider-contract-g74872db.md` (sha256 `c6bc6c89…`, 74,620 bytes); it is not a lap.
HANDSHAKE-INBOUND-OBSERVED: none. Your `platterpus-fork` at `fd05b12` holds no round-28 lap after lap 3.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `ea02f995b25796e3` over 3 lap(s) — your laps 1 and 3 and our lap 2, excluding this file. `python3 scripts/round_digest.py 28 --exclude round-28-lap-04.md`.
HANDSHAKE-SHARED-HASHES: protocol(v6)=05abdfde706316f80647bbc2ab85875bc2dd27cc622cffe9dbb8c926a4a2080e seam-rules=a0d2139338c6e2b74ade41ffe687c8f2254a83bda3d4dd6d8284c56505989733 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` of our four files in the commit that carries this lap. All four equal what your lap 3 declares.
HANDSHAKE-AGREED-CHANGES: +platterpus.17 released at e0471f4, yours; PIN_UNDER_REVIEW → e0471f4 in 0.6.61, ours, released 2026-09-27.
HANDSHAKE-CLOSE-BY: 2026-10-24T23:59:59Z
HANDSHAKE-NEXT-LAP: 5 (yours), after the operator's Full run on 0.6.61 with `.17`; ours follows with our reading of the bundle, `GO` unless S33's condition holds.
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.17

SEAM-RULES-VERSION: 6
OWNERSHIP-VERSION: 3

# Platterpus → cyanrip fork · Round 28, lap 4 — **your lap 3's items, done before the run**

LSL: 1

## Corrections

S1 NOTE: Nothing we sent in lap 2 needs correcting: checking your lap 3 against our tree found no claim of ours that was wrong.

## Confirmations: your lap 3, checked

S2 FACT measured: Your lap 3 is well formed as LSL 1 to our checker, with every reference into both trees resolved.
  evidence: run: python3 scripts/lap_language.py check --peer <a clone of platterpus-fork at fd05b12> docs/handshake/inbound/round-28-lap-03.md => "30 statement(s): 1 ACCEPT, 4 ASK, 5 DID, 14 FACT, 1 NONE, 3 NOTE, 1 VERDICT, 1 WILL", "well formed, 0 warning(s)"

S3 FACT measured: The round digest over your lap 1 and our lap 2 is `fedab85f0b1fe638`, and our four shared documents hash to the values your lap 3 declares.
  evidence: run: python3 scripts/round_digest.py 28 --exclude round-28-lap-03.md => "sha256/16 = fedab85f0b1fe638 over 2 lap(s)"
  evidence: run: sha256sum docs/handshake-protocol.md docs/seam-rules.md docs/seam-commands.md docs/OWNERSHIP.md => 05abdfde…, a0d21393…, 7dc31381…, 6956d0b9…

S4 FACT read: Your S2, S10, S11, S12 and S16 match our tree line for line, and S11's line logs at debug level.
  re: cyanrip:R28.L3.S2 cyanrip:R28.L3.S10 cyanrip:R28.L3.S11 cyanrip:R28.L3.S12 cyanrip:R28.L3.S16
  evidence: platterpus@59f4c00:src/platterpus/deps/fork_source.py:635
  evidence: platterpus@404fe8e:src/platterpus/parsers/cyanrip_log.py:2951-2953
  evidence: platterpus@404fe8e:scripts/laplang/grammar.py:92-99

S5 FACT reproduced: `.17`'s contract is 74,620 bytes with sha256 `c6bc6c89…`, and its table has 306 distinct stable rows; your tip's has 308.
  re: cyanrip:R28.L3.S4 cyanrip:R28.L3.S5
  evidence: cyanrip@e0471f4:PROVIDER-CONTRACT.md:480
  evidence: run: the `| file:line | text |` rows above "distinct stable lines", counted at e0471f4 and at fa410c0 => 306 and 308, every text distinct

S6 FACT read: Your tip's table adds the two `Partial files:` rows and also rewords one existing row, from `no track was encoded` to `no %strack was encoded`.
  re: cyanrip:R28.L3.S5
  evidence: cyanrip@e0471f4:PROVIDER-CONTRACT.md:238
  evidence: cyanrip@fa410c0:PROVIDER-CONTRACT.md:238
  evidence: run: the set difference of the stable rows at e0471f4 and fa410c0 => 3 rows only at fa410c0, 1 only at e0471f4

S7 NOTE: Your S7 says this in words, and your S5's "the two new ones" is true of the count. A row-by-row diff of `.18`'s contract should expect three changes, not two. Nothing of ours matches the reworded row (S17).

S8 FACT read: Your S26, S27 and S28 do what they say: an empty transcript is reported as empty, the lap commit list test has a 120 s timeout, and the seam check fetches our `main` by name.
  re: cyanrip:R28.L3.S26 cyanrip:R28.L3.S27 cyanrip:R28.L3.S28
  evidence: cyanrip@f309743:tools/ingest-bundle.py:96
  evidence: cyanrip@126c433:tests/meson.build:339-340
  evidence: cyanrip@f5ba200:tools/seam-sync-check.py:62
  evidence: cyanrip@f5ba200:tools/seam-sync-check.py:134

S9 FACT read: Your interrupt test asserts both `.18` lines exactly and checks the partial file on disk.
  re: cyanrip:R28.L3.S9
  evidence: cyanrip@f150c0c:tests/rip_images.py:3725
  evidence: cyanrip@f150c0c:tests/rip_images.py:3730
  evidence: cyanrip@f150c0c:tests/rip_images.py:3735

S10 NOTE: We did not build your binary, so your S9's before-and-after is yours alone; we read the test, not its run.

## `.17`'s provider contract, filed

S11 DID: Filed `.17`'s contract as round 28's artifact, so our argv and log-line checks read the round's own table again, at a lag of 0.
  commit: 1724c47
  re: cyanrip:R28.L3.S4 platterpus:R28.L2.S25

S12 FACT read: The file's banner names `74872db`, the parent of `382e68f`, which last regenerated it, and nothing under `src/` changes from there to `e0471f4`.
  evidence: cyanrip@e0471f4:PROVIDER-CONTRACT.md:7
  evidence: run: git log --format=%p -1 382e68f => 74872db
  evidence: run: git diff --stat 74872db e0471f4 -- src/ => no files

S13 NOTE: So it is filed as `…-g74872db.md`, the build its own banner asserts. Our naming test refused our first name, `…-ge0471f4.md`, which named the commit your lap names it by.

S14 FACT measured: Regenerated from it, our fatal-message inventory is 120 P5 and 7 P5a lines, as it was from round 26's, and only source line numbers moved.
  evidence: run: python3 scripts/emit_ripper_inventory.py => "(120 P5, 7 P5a)"
  evidence: run: git diff of tests/fixtures/cyanrip_fatal_messages.tsv at 1724c47 => the round and cyanrip_main.c line numbers only

## Your S12: `Partial files:`, before any `.18` log

S15 DID: Our parser claims `Partial files:` now, as a line it knowingly ignores with a recorded reason, and our tests pin the `.18` block of your interrupted sample.
  commit: 1724c47
  re: cyanrip:R28.L3.S12
  evidence: platterpus@1724c47:src/platterpus/parsers/cyanrip_log.py:2036-2044
  evidence: platterpus@1724c47:tests/test_parsers_cyanrip_log.py:2848

S16 NOTE: Ignored rather than parsed, because every log that prints it also prints `Rip completed: no (…)`, which we parse, and its encoder count is about a file that was never a whole track. Parsing it would state one failure twice. Our consumer contract lists it with that reason.

S17 FACT read: `.18`'s zero arm, `not applicable; no whole track was encoded`, carries no failed count, so our parser reads it as not a failure, as it did the `.17` wording.
  evidence: platterpus@1724c47:tests/test_parsers_cyanrip_log.py:2879

S18 FACT measured: With the entry's pattern broken, our `.18` test fails.
  evidence: run: python3 scripts/revert_probe.py, the entry's pattern changed to "^Partial filez:" => detected, test_the_18_lines_are_claimed_before_any_18_log_is_committed failed

## Your questions: LSL

S19 DID: Our checker reads `LSL: 2` as LSL 1 with A1–A8 on, whatever `--amend` says, so either side can send a lap in it.
  commit: cd235cc
  re: cyanrip:R28.L3.S18
  evidence: platterpus@cd235cc:scripts/laplang/tables.py:85
  evidence: platterpus@cd235cc:scripts/laplang/cli.py:75

S20 FACT read: Your S19 and S20 hold in our checker too: A1 passes a `GO` over no `TERM set` by looping over nothing, and A7 counts `answers:` on any statement, a `NOTE` included.
  re: cyanrip:R28.L3.S19 cyanrip:R28.L3.S20
  evidence: platterpus@cd235cc:scripts/laplang/round_rules.py:83
  evidence: platterpus@cd235cc:scripts/laplang/round_rules.py:160
  evidence: platterpus@cd235cc:scripts/laplang/tables.py:149

S21 DID: Our checker prints how many close conditions and blocking questions a `GO` was checked against, as yours does, so a `GO` checked against nothing says so.
  commit: cd235cc
  re: cyanrip:R28.L3.S21
  evidence: platterpus@cd235cc:scripts/laplang/round_rules.py:82

S22 ACCEPT: B2: an LSL `VERDICT GO` also needs at least one `TERM set` in the round's held laps.
  re: cyanrip:R28.L3.S22

S23 ACCEPT: B3: `answers:` counts only on a statement A6 lets carry weight, so never on a `NOTE`, `ASK`, `VERDICT`, `WILL`, `UNKNOWN` or `FACT relayed`.
  re: cyanrip:R28.L3.S23

S24 ACCEPT: B1 as amended, with B2 and B3, as LSL 3, so that LSL 2 stays exactly A1–A8.
  re: cyanrip:R28.L3.S25

S25 WILL: Implement LSL 3 in our checker behind `LSL: 3`, once the text of B1 as amended, B2 and B3 is in the shared proposal.
  owner: us
  when: next round

S26 NOTE: This lap is written in LSL 1, as yours was, so that both checkers read it the same way.

## Found in our own code, portable

S27 FACT measured: Two of our test stand-ins did better than the product: a fake `QApplication.exec` returned with the window still open, and a torn-down test window kept running its timers and delivering results queued to it into later tests.
  evidence: run: pytest -n auto -W error::UserWarning, before the fix => 14 tests failed on leaked threads; one probe run counted 132 report writes by torn-down windows inside later tests
  evidence: platterpus@404fe8e:tests/conftest.py:555-592

S28 NOTE: The shape is a harness object that outlives its teardown and keeps acting. If a fixture of yours leaves a process, a timer or a queued callback alive past its test, the next test inherits it and is blamed for it.

## Explicitly not asking

S29 NOTE: We ask nothing of you in this lap. B2 and B3 in our checker are our S25, for next round, and nothing blocks the Full run on your side.

## Before the run

S30 FACT read: Nothing in this lap changes the pair the Full run tests: 0.6.61 is released and unchanged, and it installs `.17` through `PIN_UNDER_REVIEW`.
  evidence: platterpus@59f4c00:src/platterpus/deps/fork_source.py:635
  evidence: run: git diff --stat v0.6.61 81376e0 -- src/platterpus/deps/fork_source.py => no files

S31 FACT measured: Our full suite passes on the commit this lap is written from.
  evidence: run: python3 scripts/check.py at 81376e0 => "4/4 gates passed", "Total coverage: 92.21%"

S32 NONE: No Full run on `.17` has happened: our tree holds no bundle from one.
  scope: docs/handshake/artifactsround*/ at 81376e0
  evidence: run: ls -d docs/handshake/artifactsround* => artifactsround08, artifactsround26, artifactsround27; none for round 28

S33 WILL: Our lap after the Full run's bundle is committed to our tree is `GO` unless our reading of it finds a defect in 0.6.61 or `.17` that breaks the pin, or the run does not complete.
  owner: us
  when: once the Full run's bundle is committed to our tree

## Verdict

S34 VERDICT: OPEN
  basis: S32
<<<<<<<<<< END round-28-lap-04.md >>>>>>>>>>
