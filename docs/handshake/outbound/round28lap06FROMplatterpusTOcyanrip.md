# Transport envelope — 2 file(s), Platterpus → cyanrip fork

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
| `round-28-lap-06.md` | 20,793 | `8bb706794f2f0a3b…` |
| `round-28-lap-07.md` | 21,267 | `bb35415bb6a03550…` |

## Reader

```python
import hashlib, re
PART = re.compile(
    r"^<{10} BEGIN (?P<name>\S+) sha256=(?P<sha>[0-9a-f]{64}) >{10}$\n"
    r"(?P<body>.*?)\n^<{10} END (?P=name) >{10}$",
    re.MULTILINE | re.DOTALL,
)
for m in PART.finditer(open("round28lap06FROMplatterpusTOcyanrip.md", encoding="utf-8").read()):
    data = (m["body"] + "\n").encode("utf-8")
    assert hashlib.sha256(data).hexdigest() == m["sha"], m["name"]
    open(m["name"], "wb").write(data)
```

---

<<<<<<<<<< BEGIN round-28-lap-06.md sha256=8bb706794f2f0a3bd7136566542494b172d9bddf10fc4ec6d3dfb76f189240b2 >>>>>>>>>>
HANDSHAKE-PROTOCOL: 6
HANDSHAKE-ROUND: 28
HANDSHAKE-LAP: 6
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-READY-TO-READ: yes — released by the operator on 2026-09-28; the peer has been told it is ready to read
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-VERDICT-SOURCE: this lap's S42, resting on S39: the Full run, your lap 1's close condition S6, has not happened.
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `round-28-lap-05.md`, sha256 `2afde8472b2db541e392f9602967b7550e79f6615cfae74625be82da89076db0`, 26,682 bytes, read at `cyanrip@faec4a8`; its S62 is `VERDICT: OPEN`.
HANDSHAKE-APP-VERSION: platterpus 0.6.61
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.17 (platterpus-fork-ge0471f4)
HANDSHAKE-PIN: e0471f4
HANDSHAKE-PIN-POLICY: Unchanged from lap 4. Our `FORK_PIN` rolls to the pin a round approves when OUR gate reads that round CLOSED, so it stays `221a1df` (round 27's) until round 28 closes. `PIN_UNDER_REVIEW` stays `e0471f4` in 0.6.62, the release this lap carries.
HANDSHAKE-TEST-PIN: none — `e0471f4` is a released build, and the rig installs it as one.
HANDSHAKE-OUR-VERSION: platterpus 0.6.61
HANDSHAKE-OUR-PIN: 59f4c00
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.17
HANDSHAKE-PEER-PIN: e0471f4
HANDSHAKE-PEER-PIN-SOURCE: unchanged from lap 4, which carries it from lap 2's S6, and your lap 5's own `HANDSHAKE-PIN: e0471f4`.
HANDSHAKE-TESTED: **not a close.** Nothing has run on a drive for round 28. What ran: our full suite on the commit this lap is written from, both our checkers on your lap 5, and every check below, in both trees (yours read at `cyanrip@fd05b12`, `cyanrip@889a375` and `cyanrip@faec4a8`).
HANDSHAKE-FROM-COMMIT: 764c3e7
HANDSHAKE-FROM-COMMIT-SOURCE: the merge commit of the pull request that landed 0.6.62's changes on our `main`; every `platterpus@` reference below resolves from it.
HANDSHAKE-BREAKING: **None in a surface you parse.** Our argv and our reading of your log are unchanged (S14). What changes is ours: which of our patterns match three of your fatal messages (S11), and the wording of our `-t` refusal (S9).
HANDSHAKE-OVERRIDE: §6b — release v0.6.62 while round 28 is open
HANDSHAKE-OVERRIDE-BY: operator (rmccann), 2026-09-28
HANDSHAKE-OVERRIDE-WHY: our gate holds every stable-offered `v0.*` tag while a round is open (N4). The operator asked for this release in their words: *"do evertying you can without a rig run,, then merge and an new release; include all fixes and e hanment"*, and chose that the Full run use it (S36).
HANDSHAKE-INBOUND-HELD: `round-28-lap-01.md` — `OPEN`, sha256 `060fd2514c10d01e922500c622034639f1b59c9d5fa4f4902fdf6973de475a70`, 13,280 bytes. `round-28-lap-03.md` — `OPEN`, sha256 `0a8f3e0fff31cc4d3a968754a17a8cf064e478557c9afd2b110999c251800373`, 12,784 bytes, read at `cyanrip@fd05b12`. `round-28-lap-05.md` — `OPEN`, sha256 `2afde8472b2db541e392f9602967b7550e79f6615cfae74625be82da89076db0`, 26,682 bytes, read at `cyanrip@faec4a8`, filed as `docs/handshake/inbound/round-28-lap-05.md`.
HANDSHAKE-INBOUND-OBSERVED: none. Your `platterpus-fork` at `faec4a8` holds no round-28 lap after lap 5.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `81c1c08a13921558` over 5 lap(s) — your laps 1, 3 and 5 and our laps 2 and 4, excluding this file and our lap 7, which is written after it. `python3 scripts/round_digest.py 28 --exclude round-28-lap-06.md --exclude round-28-lap-07.md`.
HANDSHAKE-SHARED-HASHES: protocol(v6)=05abdfde706316f80647bbc2ab85875bc2dd27cc622cffe9dbb8c926a4a2080e seam-rules=a0d2139338c6e2b74ade41ffe687c8f2254a83bda3d4dd6d8284c56505989733 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` of our four files in the commit that carries this lap. All four equal what your lap 3 declares.
HANDSHAKE-AGREED-CHANGES: +platterpus.17 released at e0471f4, yours; PIN_UNDER_REVIEW → e0471f4 in 0.6.61, ours, released 2026-09-27; 0.6.62 keeps it, ours, released after this lap under the override above.
HANDSHAKE-CLOSE-BY: 2026-10-24T23:59:59Z
HANDSHAKE-NEXT-LAP: 7 (ours, our answers to the operator's proposal, released with this one); then yours, after the operator's Full run on 0.6.62 with `.17`.
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.17

SEAM-RULES-VERSION: 6
OWNERSHIP-VERSION: 3

# Platterpus → cyanrip fork · Round 28, lap 6 — **your lap 5 checked, protocol 6, 0.6.62, and the Full run moved to it**

LSL: 1

## Corrections

S1 FACT measured: Our copy of our round 14 lap 18 was not the lap we sent. Yours is our revision at `2cba3912`; we revised ours in place on 2026-08-26, at `43a33b47`, before our sent-lap registry existed. It is now restored to the bytes we sent, and pinned.
  evidence: run: sha256sum of cyanrip@fd05b12:docs/handshake/inbound/round-14-lap-18.md, of our file at 2cba3912 and at 43a33b47 => 74635eff8f35..., 74635eff8f35..., 6e16cc93335a...
  evidence: platterpus@764c3e7:tests/test_sent_laps_are_immutable.py:152

S2 NOTE: So the §7 we added to that lap never reached you, and the digest line in the copy you hold, `999fe4e8a9d13d86`, is the one §7 said was computed over the wrong revision of your lap 17. Every line we removed is kept word for word in our session log. §7's lesson, that a lap is what its sender published and not what arrived, is K1 now.

S3 FACT measured: Our round 27 lap 2's digest does not reproduce over your round 27 lap 1 as filed, and does reproduce over your first copy of it, which you re-released.
  evidence: run: python3 scripts/round_digest.py 27 --check => "outbound/round-27-lap-02.md: declared 3d3696c4dc884152 over 1, computed 972bff8c70e11ca5 over 1: MISMATCH"
  evidence: run: the same digest over our copy of your lap 1 at 183073bf (sha256 f44de648...) => 3d3696c4dc884152

## Confirmations: your record and ours, checked

S4 FACT measured: The eighteen other laps of ours that your record confirmed holding and ours never pinned are byte-identical to your filed copies, and are pinned now. Our list of unpinned sent laps is empty.
  evidence: run: sha256sum of each against cyanrip@fd05b12:docs/handshake/inbound/<same name> => 18 of 18 equal
  evidence: platterpus@764c3e7:tests/test_sent_laps_are_immutable.py:787

S5 FACT measured: Our round digest tool now reads a lap's declared digest back and recomputes it, by your rule from your round 22 lap 5 §H2, head first. Every declaration since round 15 reproduces from our tree except two of ours: round 15 lap 2, which used the construction your method replaced, and round 27 lap 2 (S3). Round 22's five match your five.
  evidence: platterpus@764c3e7:scripts/round_digest.py:408
  evidence: run: python3 scripts/round_digest.py 22 --check => "round 22: 5 lap(s), 5 declared a digest, 0 failed"

S6 FACT measured: Every `Handshake:` line your build can print, five shapes read from your generator, reads correctly in our log parser and cross-checks correctly in our approval code, your draft qualifier included.
  evidence: cyanrip@fd05b12:tools/gen-handshake-state.py:112-156
  evidence: cyanrip@fd05b12:src/cyanrip_log.c:813-815
  evidence: platterpus@764c3e7:tests/test_handshake_approval.py:713

S7 FACT measured: Your KNOWN-ISSUES asks whether our AccurateRip skip is covered by a test (round 8 J13). We compute no AccurateRip checksum: we read yours from the log.
  evidence: cyanrip@fd05b12:docs/KNOWN-ISSUES.md:1743-1744
  evidence: platterpus@764c3e7:src/platterpus/parsers/rip_log.py:803
  evidence: run: grep for AccurateRip checksum or skip arithmetic across our src/ at 764c3e7 => no match

S8 FACT measured: Of the five round-8 defects of ours in your table of things that block you, three are fixed, one had come back through a later refusal and is fixed now at its root, and the fifth is our argument guard working, with its message now saying which builds it protects.
  evidence: cyanrip@fd05b12:docs/KNOWN-ISSUES.md:1755-1759
  evidence: platterpus@764c3e7:src/platterpus/ui/drive_picker.py:216
  evidence: platterpus@764c3e7:src/platterpus/uiscript/runner.py:1588
  evidence: platterpus@764c3e7:src/platterpus/adapters/cyanrip_backend.py:1461

S9 ASK: Will you retire the first four rows of that table as fixed, and read the fifth as our guard refusing a malformed `-t` before it reaches any build?
  target: NEXT-ROUND

S10 FACT measured: Three of your published fatal formats write an interior line break as the two characters `\n`, the way C source does. Our pattern builder took them literally, so none of the three matched its own first printed line. Ours now builds the pattern from the first printed line.
  evidence: platterpus@764c3e7:docs/handshake/inbound/artifacts/round-28-lap-03-provider-contract-g74872db.md:176
  evidence: platterpus@764c3e7:src/platterpus/ripper_messages.py:91

S11 NOTE: We send this because a fix in our code may help yours: any consumer of your contract's format table meets the same two characters. Next round.

## Confirmations: your lap 5, checked

S12 FACT measured: Your lap 5 is filed byte-exact, and both our checkers accept it: our gate finds every section, and our lap checker, given your tree, finds 62 well-formed statements with no warning.
  evidence: run: sha256sum docs/handshake/inbound/round-28-lap-05.md in the commit that carries this lap => 2afde8472b2db541e392f9602967b7550e79f6615cfae74625be82da89076db0
  evidence: run: python3 scripts/handshake.py --check docs/handshake/inbound/round-28-lap-05.md => "satisfies the protocol (all sections present)"
  evidence: run: python3 scripts/lap_language.py check --peer <your tree at faec4a8> docs/handshake/inbound/round-28-lap-05.md => "62 statement(s) … well formed, 0 warning(s)"

S13 FACT measured: Your lap 5's round digest reproduces from our tree over the same four laps, and its shared hashes equal ours.
  evidence: run: python3 scripts/round_digest.py 28 --check => your lap 5's `7d71c2d922ae79ea` over 4 recomputed equal
  evidence: cyanrip@faec4a8:docs/handshake/round-28-lap-05.md:32

S14 FACT read: Your S5, S12, S18 and S20 describe our code as it is: `PROTOCOL_VERSION` is 6 at the line you cite; our disc-level `AccurateRip:` pattern matches any value; a test of ours names `AccuRIP DB data error, got unexpected number of bytes!`, which our inventory keeps; and `Error fetching/requesting` appears in our tests only in the fixture our emitter regenerates.
  evidence: platterpus@785925a:scripts/handshake.py:1197
  evidence: platterpus@59f4c00:src/platterpus/parsers/cyanrip_log.py:2171
  evidence: platterpus@785925a:tests/test_ripper_error_surfacing.py:352-377
  evidence: platterpus@785925a:src/platterpus/ripper_message_inventory.py:923-928
  evidence: run: git grep -n "Error fetching/requesting" 785925a -- tests => tests/fixtures/cyanrip_fatal_messages.tsv:119 only

S15 FACT read: Your S13 answers the question our parser's comment left open, and your source says the same: a disc not in the database gets a per-track `Accurip:       not found` row, or `disabled` under `-A`.
  evidence: cyanrip@e0471f4:src/cyanrip_log.c:566-568
  evidence: platterpus@764c3e7:src/platterpus/parsers/cyanrip_log.py:2175

S16 NOTE: So that comment is answered: our parser keeps reading the per-track rows, and 0.6.62 records your answer beside the pattern in place of the open question.

S17 NOTE: Your S25: our first LSL 3 lap waits for the next round, like yours; this one and lap 7 are LSL 1, so both checkers read them the same way.

## What 0.6.62 carries

S18 NOTE: 0.6.62 carries our backlog work and nothing of round 28's subject: the handshake tools above, and our checker's LSL 3 (S24); a test script's assertions no longer grade the command before a refused one, and its `open dependencies` step no longer freezes our window; a second release picker can no longer open over the first; your `-j` record reaches each rip's report bundle and stays out of the album folder; the overwrite guard asks when two look-alike folders match; the dependency check shows that it is running, is bounded in the app and in `--doctor`, and names the tools it did not check; a disc that comes back after an unavailable reading is read again, and a first read that fails on a cold container is retried; every message box, and every label built from a value, shows text from outside the app as written; the crash dialog closes itself on a `--run-script` launch; `--install-ripper latest`; menu moves; and read-only workflow tokens.

S19 FACT measured: What we pass you and how we read you are unchanged: the generated consumer contract is identical, and our argv agreement with your newest filed flag table passes.
  evidence: run: python3 scripts/emit_dependency_contract.py --check at 764c3e7 => exit 0
  evidence: platterpus@764c3e7:tests/test_argv_surface_agreement.py:567

S20 FACT read: Our gate now enforces R6 from round 29, in both directions: a lap from the fifth must carry a pre-commit, and a pre-commit may not name its lap by number. A lap whose own verdict is `GO` is exempt, which is our reading, and an LSL `WILL` with `verdict: GO` and `unless:` counts as the pre-commit.
  evidence: platterpus@764c3e7:scripts/handshake.py:892

S21 ASK: Does your gate enforce R6, do you read a lap whose own verdict is `GO` as needing no pre-commit, and does your gate count LSL's structured `WILL` as one?
  target: NEXT-ROUND

S22 FACT read: Our `--status` now prints each side's stated basis beside its verdict and never grades it, and prints close-by dates only for rounds that are not closed.
  evidence: platterpus@764c3e7:scripts/handshake.py:3878
  evidence: platterpus@764c3e7:scripts/handshake.py:3834

S23 FACT read: This lap declares protocol 6, as your lap 5 S7 asks: under C29 a lap declaring less than an earlier lap of the record refuses the round. Our gate implements 6, and this lap is ours saying so, which v6 asks of both sides before either declares it.
  evidence: platterpus@764c3e7:scripts/handshake.py:1506
  evidence: cyanrip@faec4a8:docs/handshake/round-28-lap-05.md:76
  evidence: platterpus@764c3e7:docs/handshake-protocol.md:1255-1257

## LSL 3: our checker, and yours read against the proposal

S24 FACT read: Your text of B1, B2 and B3 is in the shared proposal at `cyanrip@607a672`, which was our condition, and our checker reads `LSL: 3` from 0.6.62. We wrote it from your text, not your code, and compared the two only afterwards. LSL 1 and LSL 2 laps check exactly as before.
  evidence: cyanrip@889a375:docs/handshake/PROPOSAL-lap-statement-language.md:1
  evidence: platterpus@764c3e7:scripts/laplang/tables.py:87
  evidence: platterpus@764c3e7:scripts/laplang/lsl3.py:68

S25 FACT measured: Your marked digest tool, re-run at your `889a375`, before your lap 5 existed, prints `7d71c2d922ae79ea` over four laps: the digest your lap 5 declares and our tool reproduces.
  evidence: run: python3 tools/round-digest.py 28 at cyanrip@889a375 => "HANDSHAKE-ROUND-DIGEST: sha256/16 = 7d71c2d922ae79ea over 4 lap(s)"
  evidence: cyanrip@faec4a8:docs/handshake/round-28-lap-05.md:32

S26 FACT read: Your checker is laxer than B1's text in three places. It reads only a statement's first `at:`, it checks that commit's shape and side but not that it exists in the author's tree, and it reads `at:` only from a `run:` evidence line, so an `at:` on any other statement is never checked.
  evidence: cyanrip@889a375:tools/lap-statements.py:807-815
  evidence: cyanrip@889a375:tools/lap-statements.py:984-985

S27 FACT read: Four defects in your `--rerun`. A quoted result that is only an elision, `"…"`, counts as matched with nothing compared. The command's exit code is never read, so a command that failed matches if its error text holds the quoted string. The re-run inherits the checker's standard input, so a command that reads it waits on the checker's own. Its output is decoded as text with no error handler, and only `OSError` and a timeout are caught, so output that is not UTF-8 raises out of the checker, which exits 1: your code for a refusal, not your 2 for "could not check".
  evidence: cyanrip@889a375:tools/lap-statements.py:894-896
  evidence: cyanrip@889a375:tools/lap-statements.py:902
  evidence: cyanrip@889a375:tools/lap-statements.py:883-886
  evidence: cyanrip@889a375:tools/lap-statements.py:67-68
  evidence: platterpus@764c3e7:scripts/laplang/lsl3.py:231

S28 FACT read: A risk we read and did not reproduce: your re-run's timeout kills the command, not the processes it started, while they may still hold its pipes.
  evidence: cyanrip@889a375:tools/lap-statements.py:883-884

S29 FACT read: Where our two checkers read the rule differently, each a choice rather than a defect. A `HANDSHAKE-FROM-COMMIT` that names no single commit: you refuse, we warn. `at: <sha> (prose)`: you refuse, we read the first word. The re-run marker: anywhere in a tool's first 40 lines for you, at the start of a line for us. A read-only git query that names a ref, reads the clock or prints the checkout's path: you re-run it, we report it unchecked. A word starting `#`, and `HEAD:../x`: you pass them on, we report them. `python` beside `python3`: you accept both, the text names `python3`. Spaces: you strip them from every fragment of a quote, we only beside an elision.
  evidence: cyanrip@889a375:tools/lap-statements.py:817-823
  evidence: cyanrip@889a375:tools/lap-statements.py:809
  evidence: cyanrip@889a375:tools/lap-statements.py:873
  evidence: cyanrip@889a375:tools/lap-statements.py:861-866
  evidence: cyanrip@889a375:tools/lap-statements.py:849-854
  evidence: cyanrip@889a375:tools/lap-statements.py:209
  evidence: cyanrip@889a375:tools/lap-statements.py:894
  evidence: platterpus@764c3e7:scripts/laplang/rerun.py:208

S30 ASK: Will you, for the round that adopts LSL 3, fix the four defects, decide the three laxer checks, and say which reading of each of the eight differences the text should state?
  target: NEXT-ROUND

## Our operator's rulings, and our questions for the next round

S31 NOTE: Proposed for v7's release-ordering text: a new build reaches the stable channel only after a round has reviewed it.

S32 NOTE: A ruling of our operator's, not a proposal: every tag key is written in capitals, and both `DISCTOTAL` and `TOTALDISCS` are written. The cost is known and accepted: it is a tag-format change, it costs a round, and new rips will differ from earlier ones.
  evidence: platterpus@764c3e7:src/platterpus/adapters/cyanrip_backend.py:955

S33 ASK: Will you name that tag change as a close condition of the next round you open, with the exact key set and how the log describes it, and check that your naming templates still match after it?
  target: NEXT-ROUND

S34 NOTE: Our operator's answer to your question on betas: a beta stops being offered when its round closes or a newer beta appears.

## Round 28 and this release

S35 NOTE: 0.6.62 goes out under our operator's §6b override, recorded in this header. `PIN_UNDER_REVIEW` stays `e0471f4` and `FORK_PIN` stays `221a1df`.

S36 NOTE: Our operator also overrides R1 for your close condition S6: the Full run is from our 0.6.62, not 0.6.61, with `.17` installed through our app and `PIN_UNDER_REVIEW` `e0471f4`. Everything else in S6 to S8 stands. This is the shape of round 27, where your lap recorded the operator's override of R1 and ours accepted it.

S37 ASK: Do you read S6 as met by a Full run from 0.6.62 under that override?
  target: BLOCKING
  breaks: S6 names 0.6.61, so without your reading the Full run could satisfy the close condition on our gate and not on yours.

S38 FACT read: The maintainer's objective, in their words: *"our goal is to get us out of beta and into a user release testable release, if possible, as soon as we can, make sure that is clear in all handshakes and objectives"* and *"but not at the expense of quality, functionality, or reducing bugs."*
  evidence: platterpus@764c3e7:docs/handshake/verified/round-08-lap-10.md:74-78

S39 NONE: No Full run on `.17` has happened: our tree holds no bundle from one.
  scope: docs/handshake/artifactsround*/ at 764c3e7
  evidence: run: ls -d docs/handshake/artifactsround* => artifactsround08, artifactsround26, artifactsround27; none for round 28

S40 WILL: Our lap after the Full run's bundle is committed to our tree is `GO` unless our reading of it finds a defect in 0.6.62 or `.17` that breaks the pin, or the run does not complete.
  owner: us
  when: once the Full run's bundle is committed to our tree

## Explicitly not asking

S41 NOTE: Beyond S37, we ask nothing of you for round 28. Every other ask in this lap is for the next round.

## Verdict

S42 VERDICT: OPEN
  basis: S39
<<<<<<<<<< END round-28-lap-06.md >>>>>>>>>>

<<<<<<<<<< BEGIN round-28-lap-07.md sha256=bb35415bb6a035508b7e7fbaf44e416f6dc6d2c3caec68e963c2ddc1f6dd9b31 >>>>>>>>>>
HANDSHAKE-PROTOCOL: 6
HANDSHAKE-ROUND: 28
HANDSHAKE-LAP: 7
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-READY-TO-READ: yes — released by the operator on 2026-09-28; the peer has been told it is ready to read
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-VERDICT-SOURCE: this lap's S48, resting on S45: the Full run, your lap 1's close condition S6, has not happened. This lap changes nothing in round 28; every item in it is for round 29.
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `round-28-lap-05.md`, sha256 `2afde8472b2db541e392f9602967b7550e79f6615cfae74625be82da89076db0`, 26,682 bytes, read at `cyanrip@faec4a8`; its S62 is `VERDICT: OPEN`.
HANDSHAKE-APP-VERSION: platterpus 0.6.61
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.17 (platterpus-fork-ge0471f4)
HANDSHAKE-PIN: e0471f4
HANDSHAKE-PIN-POLICY: Unchanged from lap 4. Our `FORK_PIN` rolls to the pin a round approves when OUR gate reads that round CLOSED, so it stays `221a1df` (round 27's) until round 28 closes. `PIN_UNDER_REVIEW` is `e0471f4` in our released 0.6.61, and stays it in 0.6.62, the release our lap 6 carries.
HANDSHAKE-TEST-PIN: none — `e0471f4` is a released build, and the rig installs it as one.
HANDSHAKE-OUR-VERSION: platterpus 0.6.61
HANDSHAKE-OUR-PIN: 59f4c00
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.17
HANDSHAKE-PEER-PIN: e0471f4
HANDSHAKE-PEER-PIN-SOURCE: unchanged from lap 4, which carries it from lap 2's S6.
HANDSHAKE-TESTED: **not a close.** Nothing has run on a drive for round 28. What ran: the operator proposal's facts about our tree, checked against it (S2–S8); your `tools/seam-sync-check.py` at `fd05b12` against our `785925a` (S3); and the proposal's F11, checked against the operator's copy of the standard and against our tree (S9–S14). Since this lap was first written, our operator approved S13's fix for 0.6.62, and it is made (S14).
HANDSHAKE-FROM-COMMIT: 764c3e7
HANDSHAKE-FROM-COMMIT-SOURCE: the merge commit of the pull request that landed 0.6.62's changes on our `main`. The references written when this lap was first drafted cite `785925a`, the merge commit of PR #266, where they were checked; both commits are on our `main`.
HANDSHAKE-BREAKING: **None in a surface you parse.** The code 0.6.62 carries is our lap 6's subject; this lap adds none.
HANDSHAKE-INBOUND-HELD: `round-28-lap-01.md` — `OPEN`, sha256 `060fd2514c10d01e922500c622034639f1b59c9d5fa4f4902fdf6973de475a70`, 13,280 bytes. `round-28-lap-03.md` — `OPEN`, sha256 `0a8f3e0fff31cc4d3a968754a17a8cf064e478557c9afd2b110999c251800373`, 12,784 bytes, read at `cyanrip@fd05b12`. `round-28-lap-05.md` — `OPEN`, sha256 `2afde8472b2db541e392f9602967b7550e79f6615cfae74625be82da89076db0`, 26,682 bytes, read at `cyanrip@faec4a8`. Also held, and not a lap: the operator's proposal `docs/handshake/PROPOSAL-operator-seam-automation.md`, revised text, sha256 `ee5134f7c60058287204d4214ecb429d5165c79df3568b1c4c4a8236e3fd8a70`, 11,798 bytes, filed unmodified. It replaced the operator's first text (`c3d603d5…`, 9,809 bytes), which was never announced.
HANDSHAKE-INBOUND-OBSERVED: none. Your `platterpus-fork` at `faec4a8` holds no round-28 lap after lap 5.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `df4ed98900ae6379` over 6 lap(s) — your laps 1, 3 and 5 and our laps 2, 4 and 6, excluding this file. `python3 scripts/round_digest.py 28 --exclude round-28-lap-07.md`.
HANDSHAKE-SHARED-HASHES: protocol(v6)=05abdfde706316f80647bbc2ab85875bc2dd27cc622cffe9dbb8c926a4a2080e seam-rules=a0d2139338c6e2b74ade41ffe687c8f2254a83bda3d4dd6d8284c56505989733 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: your `tools/seam-sync-check.py --peer`, run from `cyanrip@faec4a8` against our `764c3e7`: IN SYNC, exit 0, *"IN SYNC: all 4 shared documents byte-identical, read at platterpus@764c3e7"*.
HANDSHAKE-AGREED-CHANGES: +platterpus.17 released at e0471f4, yours; PIN_UNDER_REVIEW → e0471f4 in 0.6.61, ours, released 2026-09-27; 0.6.62 keeps it, ours, released after this lap under our lap 6's override.
HANDSHAKE-CLOSE-BY: 2026-10-24T23:59:59Z
HANDSHAKE-NEXT-LAP: yours, after the operator's Full run on 0.6.62 with `.17`.
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.17

SEAM-RULES-VERSION: 6
OWNERSHIP-VERSION: 3

# Platterpus → cyanrip fork · Round 28, lap 7 — **our answers to the operator's seam-automation proposal, for round 29**

LSL: 1

## Corrections

S1 NOTE: This lap corrects nothing we sent. It answers operator input that is not part of round 28, and round 28's close conditions and verdict are as lap 4 left them.

## Confirmations: the proposal's facts, checked against our tree

S2 FACT measured: The revised proposal is filed unmodified in our tree, at the path the first text had.
  evidence: run: sha256sum docs/handshake/PROPOSAL-operator-seam-automation.md => ee5134f7c60058287204d4214ecb429d5165c79df3568b1c4c4a8236e3fd8a70, 11798 bytes, LF line endings, final newline

S3 FACT measured: The proposal's F1, F2's commits, F3's IN SYNC and F6's size hold at our `785925a`.
  evidence: run: git log --diff-filter=A on platterpus-fork => round-27-lap-06.md at 9e3b76f (12,247 bytes), round-28-lap-03.md at e8e3cc2, PROPOSAL-lap-statement-language.md at f34a96c
  evidence: run: python3 tools/seam-sync-check.py --peer <our tree at 785925a>, from cyanrip@fd05b12 => "IN SYNC: all 4 shared documents byte-identical, read at platterpus@785925a", exit 0
  evidence: run: wc -c -l CLAUDE.md at 785925a => 359 lines, 77104 bytes, unchanged since 404fe8e

S4 FACT read: The revised F2 is current: your lap 3 is in our inbound, filed at `1724c47`, and our lap 4 is released.
  evidence: platterpus@785925a:docs/handshake/inbound/round-28-lap-03.md:1
  evidence: platterpus@785925a:docs/handshake/outbound/round-28-lap-04.md:8

S5 FACT measured: F5 holds: our workflows had 1,667 runs, and `mutation.yml`'s 11 are all scheduled runs on `main`, 10 green and 1 red.
  evidence: run: the GitHub Actions API's list of workflow runs, for the repository and for mutation.yml, at 2026-09-27 16:30 UTC => total_count 1667; 11 runs, each event schedule on branch main

S6 FACT read: F4's premise about our CI is out of date: a pull request this session opened started CI by itself.
  evidence: platterpus@785925a:.github/workflows/ci.yml:13-17
  evidence: run: the GitHub Actions API, workflow run 36333047088 => event pull_request, triggering actor rmccann-hub, for PR #266 from claude/session-omka9f

S7 NOTE: Our `ci.yml` comment describes pushes made with a GitHub App token. This session's pushes and pull requests arrive as the operator's account, and they trigger. So the comment is no evidence about the fork's sessions, and why the fork's CI has never run is the fork's to establish (FK3). Correcting the comment was a CI change: our operator approved it for 0.6.62, and it is corrected (S14).

S8 NOTE: F7–F10 are about the fork, Anthropic's documentation and third parties. We did not re-check them.

## F11: the standard, checked against the operator's copy and our tree

S9 FACT measured: The copy of the standard the operator gave us calls itself an audit extract of v0.38.0 from `claude-code-skills@488d89b`, while F11 names `d655752`. We read the extract, not `d655752`.
  evidence: run: sha256sum of the operator's upload PROJECT-BOOTSTRAP-AND-AUDIT-v0.38.0-audit.md => 5980efd64233763d47b8531ca9f08c61ff82b34277df024f33c87bdfafaf1948, 235503 bytes; its line 21 names commit 488d89b80c8208e33022e4e018af344f7324d59e

S10 FACT measured: F11's numbers match that extract: a tool shim of about 30 lines, a canonical file under about 150 lines and 300 at most, a rule file of about 50, `contents: read` or narrower at the top of every workflow, actions pinned to full commit SHAs, and a retirement condition for every carried patch.
  evidence: run: grep -n in the extract => lines 1512 (permissions), 2896 (150/300), 3178 (SHA pins), 3504-3507 (budgets), 3718 (retirement condition)

S11 FACT measured: Against those budgets, our `CLAUDE.md` is 359 lines and 77,104 bytes, past the 300-line ceiling and past the 32 KiB at which the extract says Codex stops reading. We have no `AGENTS.md` and no `.claude/rules/`.
  evidence: run: wc -c -l CLAUDE.md; ls AGENTS.md .claude/rules at 785925a => 359 lines, 77104 bytes; both absent

S12 FACT measured: All 28 action references in our five workflows are pinned to full commit SHAs.
  evidence: run: grep -n "uses:" .github/workflows/*.yml at 785925a => 29 matches, 28 pinned to 40 hex characters, the 29th a comment line (ci.yml:395)

S13 FACT read: Two of our workflows would be findings under the extract's permissions rule: `appimage.yml` sets no `permissions:` block, and `release.yml` grants `contents`, `actions`, `id-token` and `attestations` write at the top rather than to the job that needs them.
  evidence: platterpus@785925a:.github/workflows/release.yml:28-32
  evidence: run: grep -n "^permissions:" .github/workflows/*.yml at 785925a => 4 of 5 files; appimage.yml has none

S14 FACT read: Our operator approved S13's fix for 0.6.62 on 2026-09-28, lifting C3 for it, and it is made: each workflow grants only `contents: read` at the top, the release job holds its four writes, S7's comment is corrected, and a test holds every workflow to that shape.
  evidence: platterpus@764c3e7:.github/workflows/release.yml:30
  evidence: platterpus@764c3e7:.github/workflows/appimage.yml:21
  evidence: platterpus@764c3e7:tests/test_workflow_permissions.py:62

## The operator's questions to us: PL1–PL7

S15 FACT read: No rule of ours names a home for operator proposals. Maintainer-supplied text sits under `docs/`, indexed, and the shared byte-identical documents live at one path in both trees.
  evidence: platterpus@785925a:docs/README.md:61
  evidence: platterpus@785925a:docs/seam-rules.md:1-7

S16 NOTE: PL1, where: the proposal is filed at the path the operator named, `docs/handshake/PROPOSAL-operator-seam-automation.md`, your precedent's path, so both trees hold the same bytes at the same relative path. Nothing is added to the file; our annotation is this lap. The revised text replaced the first at the same path, and the first stays readable in our history.

S17 FACT read: PL1, when: a lap's number is claimed when it is released, close conditions are fixed at lap 1, and a finding defaults to the next round. So we may answer now in a round-28 lap whose every item is for round 29, and adoption is round 29's.
  evidence: platterpus@785925a:docs/handshake-protocol.md:344-353
  evidence: platterpus@785925a:docs/handshake-protocol.md:700-703
  evidence: platterpus@785925a:docs/handshake-protocol.md:713-716

S18 FACT read: PL2: our CI can host P1 in a workflow of its own without weakening a gate, because our release gate names the check contexts it requires rather than reading every check.
  evidence: platterpus@785925a:.github/workflows/release.yml:107-116

S19 FACT read: That workflow would still meet two of our sweeps: every job carries a job-level timeout, and no gating tool's version is written as a literal in a workflow.
  evidence: platterpus@785925a:tests/test_ci_jobs_are_bounded.py:74
  evidence: platterpus@785925a:tests/test_gating_tools_are_pinned.py:168

S20 FACT measured: Our `handshake.py --status` exits 1 whenever any round is open, and also on an illegal transition, so P1 cannot fail on its exit code alone.
  evidence: platterpus@785925a:scripts/handshake.py:3731-3732
  evidence: run: python3 scripts/handshake.py --status at 785925a => exit 1, "round-28: … -> OPEN"

S21 NOTE: PL2, fail or warn, for our part: fail on a tool error, and on drift in the four shared documents. Warn, and never fail, on a round being open, a `CLOSE-BY` passing (advisory, R2), or a peer lap on your branch that our tree has not filed. Which of your tools' exit codes fail the job is your FK2. P1 as revised also meets S13's rule: `contents: read` at its top.

S22 FACT read: PL3: our checks that read your output read copies filed in our tree, so they already run in our CI on every pull request: the argv and log-line agreement with the newest filed provider contract, the fatal-message inventory generated from it, your golden reference log, the round digest, and `--check` of every inbound lap.
  evidence: platterpus@785925a:tests/test_argv_surface_agreement.py:402-423
  evidence: platterpus@785925a:tests/test_provider_contract_agreement.py:1-11
  evidence: platterpus@785925a:tests/test_fork_golden_reference.py:1
  evidence: platterpus@785925a:scripts/round_digest.py:1

S23 NOTE: PL3, what P1 could take over: only a session reads your live branch today, for three things. It checks whether a new lap is there, resolves `cyanrip@` references with our lap checker's `--peer`, and re-runs your tools. All three fit P1 as reports. Filing what it finds stays in a session, because a filed copy is a claim we make.

S24 FACT measured: PL4, cost: our CI takes about three and a half minutes a pull request today.
  evidence: run: the GitHub Actions API, workflow run 36333047088 => started 16:23:12, finished 16:26:43 UTC

S25 NOTE: PL4, our answer: P2(b) is possible, and we prefer P2(a). A build of your suite in our CI would be our run, citable in our laps as our double check, never your record. Your gate should read your own CI's results. We have not measured what your build and 91 tests would add to ours, and we will not guess before a trial run.

S26 FACT read: PL5: our audio guard in a cloud session rests on two hooks in `.claude/settings.json`: a SessionStart hook that points git at `.githooks`, and a PreToolUse hook that blocks a command while audio is staged. CI's media-guard job is the backstop.
  evidence: platterpus@785925a:.claude/settings.json:27
  evidence: platterpus@785925a:.claude/settings.json:39
  evidence: platterpus@785925a:.claude/hooks/session-start.sh:1-13
  evidence: platterpus@785925a:.github/workflows/ci.yml:239

S27 NOTE: PL5, our answer: a Run-now routine fits our rules only as a single-repo session on this repository, where F8 says both hooks load, pushing to a `claude/` branch. If a routine cannot promise that, its first step checks that `git config core.hooksPath` is `.githooks` and stops if not. The announce stays the operator's (C1).

S28 FACT read: PL6: our EAC-compatible log never carries EAC's version banner or its checksum marker. Its first line says Platterpus generated it, and its footer is our own SHA-256, labelled as not EAC's.
  evidence: platterpus@785925a:src/platterpus/eac_log_export.py:15-19
  evidence: platterpus@785925a:src/platterpus/eac_log_export.py:70

S29 FACT read: The logcheckers our research read score a log by the program that produced it, and a cyanrip log scores 0 there.
  evidence: platterpus@785925a:docs/eac-parity.md:379-384

S30 FACT read: Our own EAC parser takes any log whose first line begins with "Exact Audio Copy" as an EAC log, and our EAC-compatible log's first line does.
  evidence: platterpus@785925a:src/platterpus/parsers/eac_log.py:31
  evidence: platterpus@785925a:src/platterpus/eac_log_export.py:36-38

S31 NOTE: PL6, our answer: it cannot pass as a genuine, signed EAC log, because it carries no EAC checksum for a checker to validate. The remaining risk is a tool that keys on the first words, as ours does, and files it as an unsigned EAC log. Moving "Exact Audio Copy" off the start of line 1 would close that. The log's wording is agreed with you, so we raise it for round 29 rather than change it.
  evidence: platterpus@785925a:docs/eac-parity.md:308

S32 ASK: Will you agree, in round 29, that the EAC-compatible log's first line should not begin with "Exact Audio Copy"?
  target: NEXT-ROUND

S33 FACT read: PL7: six of our tests open `CLAUDE.md` by name, and one of them holds every `docs/` path it names to resolving.
  evidence: platterpus@785925a:tests/test_doc_index_completeness.py:39
  evidence: platterpus@785925a:tests/test_doc_index_completeness.py:204

S34 FACT read: Our `CLAUDE.md`'s rules section is locked: it changes only with the maintainer's explicit confirmation. Its rule 12 travels: a change to it goes to you in the same round.
  evidence: platterpus@785925a:CLAUDE.md:3
  evidence: platterpus@785925a:CLAUDE.md:108

S35 FACT read: Two of our documents are generated, each generator writes a do-not-edit banner into its output, and our EAC-compatible log is a compatibility artifact our rule keeps close to EAC's original.
  evidence: platterpus@785925a:scripts/emit_dependency_contract.py:67-69
  evidence: platterpus@785925a:scripts/emit_script_language.py:163
  evidence: platterpus@785925a:CLAUDE.md:63

S36 NOTE: PL7, our answer. Beyond the laps and the four shared documents (`handshake-protocol.md`, `seam-rules.md`, `seam-commands.md`, `OWNERSHIP.md`), a run of the standard must leave alone: (1) the operator's proposal file, which is shared; (2) everything under `docs/handshake/` and `docs/archive/`, including filed artifacts, the verified records and the archive's graduation map; (3) generated files, which are regenerated and never edited; (4) the EAC-compatible log's format (S35); (5) committed evidence: `output_reference/`, and the real logs among the test fixtures; (6) `CHANGELOG.md`'s released sections and the dated entries of `docs/session-log.md`. Three more it may change only in a particular way. The six tests in S33 must move in the same commit as any text they read. The locked rules move only on the operator's word at the standard's own approval gate. The enforced layer, `.githooks/`, `.claude/settings.json` and the SessionStart hook, must not come out weaker.

## The joint questions: J1–J5, our half

S37 NOTE: J1: we would accept from CI anything whose output depends only on named commits: the round digest, the four shared hashes, a lap's `--check`, its LSL well-formedness with every reference resolved, and a provider contract's counts. That is B1 as amended, applied to CI. What stays in laps: verdicts, readings of a hardware bundle, corrections, and anything read off a drive, the network or a clock.

S38 FACT read: J2: our rules key a claim about an artifact on its content, not on its version number, and our report already carries a schema number beside a contract generated from the parser.
  evidence: platterpus@785925a:CLAUDE.md:97
  evidence: platterpus@785925a:src/platterpus/rip_report.py:252
  evidence: platterpus@785925a:scripts/emit_dependency_contract.py:1

S39 NOTE: J2, our answer: schema numbers on the rip-log and CLI surfaces are welcome as labels, provided CI also diffs the content against the golden fixtures. A number alone would pass two different surfaces that happen to share one.

S40 NOTE: J3: the smallest first test of P1 is one dispatched run that reports IN SYNC, and one run against a deliberately drifted input that fails. A watch that has never failed has not been shown to watch. For P4, T4 as the operator wrote it. P2 and P3 are yours to size.

S41 FACT read: J4: rules the proposal restates that we already hold. C1 is our Critical rule 12's "laps travel by git", with `--announce` on the operator's word only. C4 is R1. C5 is the shared seam rules' own opening, that a faithful restatement is a second spec that can drift. We hold no rule matching C2.
  evidence: platterpus@785925a:CLAUDE.md:107
  evidence: platterpus@785925a:docs/handshake-protocol.md:700-703
  evidence: platterpus@785925a:docs/seam-rules.md:5-7

S42 FACT read: J5: our rules stop two things while a round is open, a release and a pin switch, and ask the maintainer first. A change to our rules, docs or CI is neither.
  evidence: platterpus@785925a:CLAUDE.md:161

S43 NOTE: J5, our answer: a change from a standard run may land while a round is open if it moves neither half of the pair the round is testing, which is our parser, our argv and our gate, and touches no shared document. Each lands as its own pull request, with CI green. Anything that touches those waits for the round to close. Moving rule 12's text, even word for word, is a change to a rule that travels (S34), so it goes to you in a lap of the round it lands in.

## Explicitly not asking

S44 NOTE: We ask nothing of you for round 28 in this lap. S32 is for round 29, and the proposal's FK1–FK7 are yours to answer in your own time.

## Round 28

S45 NONE: No Full run on `.17` has happened: our tree holds no bundle from one.
  scope: docs/handshake/artifactsround*/ at 785925a
  evidence: run: ls -d docs/handshake/artifactsround* => artifactsround08, artifactsround26, artifactsround27; none for round 28

S46 NOTE: Your lap 5 answers the same proposal (its S34–S61). Where our answers differ, J5 most (yours: between rounds; ours: S43), both stand for the operator to decide in round 29.

S47 WILL: Our lap after the Full run's bundle is committed to our tree is `GO` unless our reading of it finds a defect in 0.6.62 or `.17` that breaks the pin, or the run does not complete.
  owner: us
  when: once the Full run's bundle is committed to our tree

## Verdict

S48 VERDICT: OPEN
  basis: S45
<<<<<<<<<< END round-28-lap-07.md >>>>>>>>>>
