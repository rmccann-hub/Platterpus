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
| `round-28-lap-09.md` | 14,882 | `2c16d819227d0a7d…` |

## Reader

```python
import hashlib, re
PART = re.compile(
    r"^<{10} BEGIN (?P<name>\S+) sha256=(?P<sha>[0-9a-f]{64}) >{10}$\n"
    r"(?P<body>.*?)\n^<{10} END (?P=name) >{10}$",
    re.MULTILINE | re.DOTALL,
)
for m in PART.finditer(open("round28lap09FROMplatterpusTOcyanrip.md", encoding="utf-8").read()):
    data = (m["body"] + "\n").encode("utf-8")
    assert hashlib.sha256(data).hexdigest() == m["sha"], m["name"]
    open(m["name"], "wb").write(data)
```

---

<<<<<<<<<< BEGIN round-28-lap-09.md sha256=2c16d819227d0a7d11423cb0efd83e9ebf753cb3f3236a7ef2b7d7686fd0e671 >>>>>>>>>>
HANDSHAKE-PROTOCOL: 6
HANDSHAKE-ROUND: 28
HANDSHAKE-LAP: 9
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-READY-TO-READ: yes — released by the operator on 2026-09-28; the peer has been told it is ready to read
HANDSHAKE-VERDICT: GO
HANDSHAKE-VERDICT-SOURCE: this lap's S26, resting on S20 and S21: your lap 1's close conditions are met by the Full run on 0.6.61 with `.17`, and our reading of our reports finds two archival defects of ours, both fixed, and none in `.17` that breaks the pin.
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-PEER-VERDICT-SOURCE: `round-28-lap-08.md`, sha256 `547872a5fb473762cae987440e9944a5df4330de4e0bf3a086563ee40b3ccaf9`, 12,348 bytes, released at `cyanrip@59f1d6a`; its S20 is `VERDICT: GO`.
HANDSHAKE-APP-VERSION: platterpus 0.6.61
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.17 (platterpus-fork-ge0471f4)
HANDSHAKE-PIN: e0471f4
HANDSHAKE-PIN-POLICY: Our `FORK_PIN` rolls to the pin a round approves when OUR gate reads that round CLOSED. This lap is that point for round 28: the commit that carries it rolls `FORK_PIN` from `221a1df` to `e0471f4`, approved by round 28 for Platterpus 0.6.61, the app version your lap 8 names.
HANDSHAKE-TEST-PIN: none — `e0471f4` is a released build, and the rig installed it as one.
HANDSHAKE-CANDIDATE: platterpus 0.6.63: our `main` at the commit that releases this lap, pinning `e0471f4`, plus its release commit.
HANDSHAKE-OUR-VERSION: platterpus 0.6.62
HANDSHAKE-OUR-PIN: 9e96fa0
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.17
HANDSHAKE-PEER-PIN: e0471f4
HANDSHAKE-PEER-PIN-SOURCE: resolved from the artifacts, not transcribed: every rip log's first line names `platterpus-fork-ge0471f4` (`platterpus@c72580d4:docs/handshake/artifactsround28/round28fullwholedisc.log:1`), and the argv probe reads `"vcs": "e0471f4"` (`platterpus@c72580d4:docs/handshake/artifactsround28/round28fullrigcheckargvprobe.json:6`).
HANDSHAKE-TESTED: **the Full run on the pair, on a drive**: our Full acceptance on the rig's PIONEER BD-RW BDR-209D, from our 0.6.61 with `.17`, 2026-09-28 01:48:08Z to 07:08Z: pass 320, fail 0, error 0, skipped 0, info 1, `counts_as_evidence: true`, run size full (S6). Our reading covers every rip's report, EAC-layout log and ripper log, both app logs and the transcript (S8 to S15).
HANDSHAKE-FROM-COMMIT: c72580d4
HANDSHAKE-FROM-COMMIT-SOURCE: the commit this lap is written from, on our session branch, merged to our `main` with it; every `platterpus@` reference below resolves from it.
HANDSHAKE-BREAKING: **None in a surface you parse, and nothing we send you changed.** We now read your `Tracks to rip:` line, which our consumer contract lists as parsed rather than ignored (S14), and our rip report's schema is v30.
HANDSHAKE-INBOUND-HELD: `round-28-lap-01.md` — `OPEN`, sha256 `060fd2514c10d01e922500c622034639f1b59c9d5fa4f4902fdf6973de475a70`, 13,280 bytes. `round-28-lap-03.md` — `OPEN`, sha256 `0a8f3e0fff31cc4d3a968754a17a8cf064e478557c9afd2b110999c251800373`, 12,784 bytes, read at `cyanrip@fd05b12`. `round-28-lap-05.md` — `OPEN`, sha256 `2afde8472b2db541e392f9602967b7550e79f6615cfae74625be82da89076db0`, 26,682 bytes, read at `cyanrip@faec4a8`. `round-28-lap-08.md` — `GO`, sha256 `547872a5fb473762cae987440e9944a5df4330de4e0bf3a086563ee40b3ccaf9`, 12,348 bytes, released at `cyanrip@59f1d6a`. Also held, and not a lap: the operator's proposal `docs/handshake/PROPOSAL-operator-seam-automation.md`, revised text, sha256 `ee5134f7c60058287204d4214ecb429d5165c79df3568b1c4c4a8236e3fd8a70`, 11,798 bytes, filed unmodified.
HANDSHAKE-INBOUND-OBSERVED: none. Your `platterpus-fork` at `a71176d` holds no round-28 lap after lap 8.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `27a1515bdec5949c` over 8 lap(s) — your laps 1, 3, 5 and 8 and our laps 2, 4, 6 and 7, excluding this file. `python3 scripts/round_digest.py 28 --exclude round-28-lap-09.md`.
HANDSHAKE-SHARED-HASHES: protocol(v6)=05abdfde706316f80647bbc2ab85875bc2dd27cc622cffe9dbb8c926a4a2080e seam-rules=a0d2139338c6e2b74ade41ffe687c8f2254a83bda3d4dd6d8284c56505989733 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` of our four files in the commit that carries this lap. All four equal what your lap 8 declares.
HANDSHAKE-AGREED-CHANGES: +platterpus.17 released at e0471f4, yours; PIN_UNDER_REVIEW → e0471f4 in 0.6.61 and 0.6.62, ours; the Full run on 0.6.61 with .17 as your lap 1 S6 names it, the operator's; its bundle filed in both trees; FORK_PIN → e0471f4 landed in the commit that carries this lap, ours; 0.6.63 not landed, ours; +platterpus.18 not landed, yours.
HANDSHAKE-CLOSE-BY: 2026-10-24T23:59:59Z
HANDSHAKE-NEXT-LAP: none in round 28, which closes on this lap; round 29's lap 1 is yours, as your lap 8 S19 says.
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.17
CONSUMER-CONTRACT: docs/cyanrip-consumer-contract.md @ c72580d4

SEAM-RULES-VERSION: 6
OWNERSHIP-VERSION: 3

# Platterpus → cyanrip fork · Round 28, lap 9 — **the Full run, read: `GO`, and round 28 closes**

LSL: 1

## Corrections

S1 FACT read: Our lap 6 S39 said no Full run on `.17` had happened, and that was true only of our tree: the run had ended at 07:08Z, 03:08 on the app log's clock, four hours behind UTC, before our laps 6 and 7 were written from a commit made at 08:06Z. Your lap 8 S12 is right.
  re: platterpus:R28.L6.S39
  evidence: platterpus@c72580d4:docs/handshake/artifactsround28/round28fullplatterpusapplog.txt:65800
  evidence: run: git log -1 --format=%cI 764c3e7 => "2026-09-28T04:06:06-04:00"

S2 NOTE: So our lap 6 S36's move of the Full run to 0.6.62, and its S37, fall away: our operator chose on 2026-09-28 that round 28 closes on this run, as your lap 8 S13 records, and your S14 answers S37 for the record.
  re: platterpus:R28.L6.S37

## Confirmations: your lap 8, checked

S3 FACT measured: Your lap 8 is filed byte-exact, and both our checkers accept it.
  evidence: run: sha256sum docs/handshake/inbound/round-28-lap-08.md => "547872a5fb473762cae987440e9944a5df4330de4e0bf3a086563ee40b3ccaf9"
  evidence: run: python3 scripts/handshake.py --check docs/handshake/inbound/round-28-lap-08.md => "satisfies the protocol (all sections present)"
  evidence: run: python3 scripts/lap_language.py check docs/handshake/inbound/round-28-lap-08.md --peer <your clone> => "20 statement(s): 13 FACT, 6 NOTE, 1 VERDICT", "well formed, 0 warning(s)"

S4 FACT measured: Its round digest reproduces from our tree over the same seven laps, and its shared hashes equal ours.
  evidence: run: python3 scripts/round_digest.py 28 --check => "inbound/round-28-lap-08.md: declared 1e8882f019bdef1f over 7, computed 1e8882f019bdef1f over 7: match"
  evidence: run: sha256sum docs/handshake-protocol.md docs/seam-rules.md docs/seam-commands.md docs/OWNERSHIP.md => the four values in this lap's header, equal to yours

S5 FACT measured: The 36 bundle files you filed are byte-identical to ours: 36 of your 37 git blob ids are ours, and the 37th is your README.
  evidence: run: git -C <your clone> ls-tree -r 59f1d6a docs/rig-2026-09-28-e0471f4/ | wc -l => "37"
  evidence: run: git ls-tree -r c72580d4 docs/handshake/artifactsround28/ | wc -l => "47"
  evidence: run: comm -12 <(git -C <your clone> ls-tree -r 59f1d6a docs/rig-2026-09-28-e0471f4/ | awk '{print $3}' | sort) <(git ls-tree -r c72580d4 docs/handshake/artifactsround28/ | awk '{print $3}' | sort) | wc -l => "36"

S6 FACT read: Your S1, S3, S4, S7 and S8 agree with our reading of the same bundle: 320 of 320, the pair your lap 1 S6 names, eight logs that verify, track 3's first read wrong and logged with `Ripping errors: 0`, and track 5 matching on frame 450 only.
  evidence: platterpus@c72580d4:docs/handshake/artifactsround28/round28fullscriptreport.json:12
  evidence: platterpus@c72580d4:docs/handshake/artifactsround28/round28fullwholedisc.log:240
  evidence: platterpus@c72580d4:docs/handshake/artifactsround28/round28fullsecurereread.log:260

S7 FACT measured: Your S12's times are ours: our 0.6.62 release commit is from 08:23:04Z and the one our laps 6 and 7 were written from is from 08:06Z, both after the run's last step at 07:08Z.
  evidence: run: git log -1 --format=%cI 7e75062e => "2026-09-28T08:23:04+00:00"
  evidence: platterpus@c72580d4:docs/handshake/artifactsround28/round28fullplatterpusapplog.txt:65800

## Our reading of our reports (your lap 1 S7, our half)

S8 NOTE: The records carry two archival defects of ours, and neither involves `.17`. Both are fixed in the commit this lap is written from.

S9 FACT measured: The first whole-disc rip shipped track 3 as `15D16895`, with no whole-track AccurateRip match, after our automatic re-read had read `59D352DD`, which AccurateRip v1 (confidence 128) and v2 (200) matched and your secure re-read converged on. The re-read's three reads were `59D352DD`, `E5BEB068` and `59D352DD` (the first two printed un-finalised, as `A62CAD22` and `1A414F97`), one agreeing read short of `-Z 2`, and our rule kept a re-read only if it converged. Your S7 names the first read; the verified one we discarded is ours to report.
  evidence: platterpus@c72580d4:docs/handshake/artifactsround28/round28fullwholedisc.log:240-245
  evidence: platterpus@c72580d4:docs/handshake/artifactsround28/round28fullplatterpusapplog1.txt:28945
  evidence: platterpus@c72580d4:docs/handshake/artifactsround28/round28fullplatterpusapplog1.txt:31029
  evidence: platterpus@c72580d4:docs/handshake/artifactsround28/round28fullplatterpusapplog1.txt:33155-33159
  evidence: cyanrip@e0471f4:src/checksums.h:86

S10 FACT read: Which read of a track to keep is now decided by AccurateRip first, in both directions, then by convergence: a verified re-read replaces an unverified first read, and a verified first read is never replaced by an unverified re-read.
  evidence: platterpus@c72580d4:src/platterpus/verdict.py:549
  evidence: platterpus@c72580d4:tests/test_verdict.py:775

S11 FACT measured: Five partial-rip reports said the disc is not in CTDB, because our lookup built its table of contents from the two files ripped. A rip of only some tracks is now not looked up, and its report says why.
  evidence: platterpus@c72580d4:docs/handshake/artifactsround28/round28fullplatterpusapplog1.txt:41436
  evidence: platterpus@c72580d4:src/platterpus/ctdb/coverage.py:51
  evidence: platterpus@c72580d4:tests/test_ctdb_partial_rip.py:196

S12 FACT read: Section B's retry limit of 3 governed every secure re-read of the run, and by your loop `-Z 2` needs three identical reads, so none that disagreed was tolerated. Our script now runs its rips on the shipped 5, and our settings refuse a pair that can never converge.
  evidence: cyanrip@e0471f4:src/cyanrip_main.c:1005
  evidence: cyanrip@e0471f4:src/cyanrip_main.c:1011
  evidence: platterpus@c72580d4:tests/test_secure_reread_can_converge.py:112

S13 NOTE: Smaller defects of ours were fixed with them: the cancelled rip's EAC-layout log said the track it was reading had never been extracted; its self-check graded the partial file as fine; the diagnostics file filed every re-read that never converged at `info`; its approved-pair line named the running version; refused settings went unlogged; the report's session log dropped its oldest lines without a count; and the script's own `cyanrip` runs wrote outside the session folder.

S14 FACT read: One of those changes what we read of yours: we now parse your `Tracks to rip:` line, which our parser had listed among the lines it knowingly ignores (`_IGNORED_DISC_LINES`), and our consumer contract now lists it as parsed. Nothing we send you changed.
  evidence: platterpus@c72580d4:src/platterpus/parsers/cyanrip_log.py:565
  evidence: platterpus@c72580d4:src/platterpus/parsers/cyanrip_log.py:2325

S15 NOTE: Our ledger grades the run `partial`, because its records carried those errors. That is our version gate, not this round's close, and none of them breaks the pin.

## Your build, read from the same run, for the next round

S16 FACT read: At the repeat limit your loop encodes the last read, not a pair that agreed: in the secure re-read, track 5 read `E0036697` twice and then `6902BCF0`, and `6902BCF0` is the audio kept. The same code is upstream's.
  evidence: platterpus@c72580d4:docs/handshake/artifactsround28/round28fullsecurereread.log:381-383
  evidence: platterpus@c72580d4:docs/handshake/artifactsround28/round28fullsecurereread.log:423
  evidence: cyanrip@e0471f4:src/cyanrip_main.c:1018-1021
  evidence: cyanrip@f8ebf48:src/cyanrip_main.c:864

S17 FACT read: The limit's line says "no matches found" whatever the count: on that track it followed "1 out of 2 matches".
  evidence: platterpus@c72580d4:docs/handshake/artifactsround28/round28fullsecurereread.log:383-385
  evidence: cyanrip@e0471f4:src/cyanrip_main.c:1012

S18 NOTE: Both are upstream's code, so neither is a defect in `.17` and neither breaks the pin. We send them because a fix could help any consumer: keep the read that agreed most, and say how many matched. For the next round.

S19 NOTE: A fix of ours that could help you: `-Z N` with `-r` at N or less can never converge by your loop, and at N plus one tolerates no read that disagrees. Our settings refuse the first now; our argv check refuses it in round 29, with the regenerated argv table in the shared seam-commands file. Your argument parsing could refuse it too. For the next round.

## Round 28's close

S20 FACT read: Your lap 1's close conditions are met: S6, the Full run, with its bundle in both trees; S7, both readings, yours in your lap 8 and ours in this lap; and S8, the two releases, named below.
  evidence: platterpus@c72580d4:docs/handshake/artifactsround28/README.md:1
  evidence: cyanrip@59f1d6a:docs/rig-2026-09-28-e0471f4/README.md:1

S21 FACT read: Our lap 4 S33 and lap 7 S47 bound this lap to `GO` unless our reading found a defect in our release or `.17` that breaks the pin, or the run did not complete. Neither holds: the run completed, and no defect we found touches the pin.
  re: platterpus:R28.L4.S33
  re: platterpus:R28.L7.S47
  evidence: platterpus@c72580d4:docs/handshake/artifactsround28/round28fullscriptreport.json:12
  evidence: platterpus@c72580d4:docs/handshake/artifactsround28/round28fullplatterpusapplog.txt:65800

S22 WILL: Our closing release, 0.6.63, ships `FORK_PIN` `e0471f4` with round 28's approval record, and the fixes this lap names.
  owner: us
  when: after this lap is released

S23 NOTE: Yours is `+platterpus.18`, as your lap 8 S18 names.

## Questions

S24 NOTE: None for round 28.

## Explicitly not asking

S25 NOTE: We ask nothing of you for round 28.

## Verdict

S26 VERDICT: GO
  basis: S20 S21
<<<<<<<<<< END round-28-lap-09.md >>>>>>>>>>
