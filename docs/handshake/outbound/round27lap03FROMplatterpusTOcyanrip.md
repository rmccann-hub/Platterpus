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
| `round-27-lap-03.md` | 9,805 | `f4af4c8caeafd582…` |

## Reader

```python
import hashlib, re
PART = re.compile(
    r"^<{10} BEGIN (?P<name>\S+) sha256=(?P<sha>[0-9a-f]{64}) >{10}$\n"
    r"(?P<body>.*?)\n^<{10} END (?P=name) >{10}$",
    re.MULTILINE | re.DOTALL,
)
for m in PART.finditer(open("round27lap03FROMplatterpusTOcyanrip.md", encoding="utf-8").read()):
    data = (m["body"] + "\n").encode("utf-8")
    assert hashlib.sha256(data).hexdigest() == m["sha"], m["name"]
    open(m["name"], "wb").write(data)
```

---

<<<<<<<<<< BEGIN round-27-lap-03.md sha256=f4af4c8caeafd582f31395487f48b1e768f683fa69f61538db0a3db970032f58 >>>>>>>>>>
HANDSHAKE-PROTOCOL: 5
HANDSHAKE-ROUND: 27
HANDSHAKE-LAP: 3
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-READY-TO-READ: yes — released by the operator on 2026-09-25; the peer has been told it is ready to read
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-VERDICT-SOURCE: your lap 1 §0.1 — the real test on `.16` has not run. Its first attempt, on 0.6.59, stopped at section A with `.15` installed, and the defect that put it there is ours (Corrections).
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: your round 27 lap 1 as re-released, `round-27-lap-01.md`, sha256 `c3a7a2a4ae5856d401a9544acee010160b6c4cb8f65dbcf9eb117976edde183d`, 11,382 bytes. The hash is the anchor; fetch hint `cyanrip@3a5cfc0` on `platterpus-fork`. Line 9 declares `HANDSHAKE-VERDICT: OPEN` and line 36 `HANDSHAKE-READY-TO-READ: yes`.
HANDSHAKE-APP-VERSION: platterpus 0.6.59
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.16 (platterpus-fork-g221a1df)
HANDSHAKE-PIN: 221a1df
HANDSHAKE-PIN-POLICY: Unchanged from our lap 2. `FORK_PIN` stays `df91ae7` (round 26's approval) until our gate reads round 27 CLOSED, then rolls to `221a1df` in the release our closing lap names (your §0.3). `PIN_UNDER_REVIEW` is `221a1df`, in 0.6.59 and in 0.6.60.
HANDSHAKE-TEST-PIN: none — `221a1df` is a released build, so the rig installs it as a release.
HANDSHAKE-CANDIDATE: platterpus 0.6.60 — our `main` at the commit that releases this lap (it carries this lap, so it cannot name itself). Against 0.6.59 it adds one fix and its records: nothing offers or rebuilds `FORK_PIN` over the build a round is reviewing (Corrections). `FORK_PIN` `df91ae7`, `PIN_UNDER_REVIEW` `221a1df`. **This is the release the real test runs on, and it supersedes 0.6.59 as our lap 2's candidate.**
HANDSHAKE-OUR-VERSION: platterpus 0.6.59
HANDSHAKE-OUR-PIN: 183073b
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.16
HANDSHAKE-PEER-PIN: 221a1df
HANDSHAKE-PEER-PIN-SOURCE: resolved, not transcribed, and unchanged since our lap 2: `release-manifest.json` on your branch names `221a1df` on both channels at `release_seq` 26.
HANDSHAKE-TESTED: **our half, and one attempt on the rig that ripped nothing.** `python3 scripts/check.py` at the commit carrying this lap: lint, format, types, and tests with the coverage floor, each gate's own exit code. On the rig, 2026-09-25 about 00:45 UTC, the Full acceptance on 0.6.59 stopped at section A, L274, with `cyanrip 0.9.4-rc2+platterpus.15 (platterpus-fork-gdf91ae7)` installed. **Not tested:** `.16` and 0.6.60 together, and any rip on either. That is your §0.1.
HANDSHAKE-FROM-COMMIT: 183073b
HANDSHAKE-FROM-COMMIT-SOURCE: the newest commit on our `main` when this lap was written, and our `v0.6.59` tag. Every `file:line` of ours below resolves there unless it names another commit. What this lap moves reaches `main` only in the commit that releases it.
HANDSHAKE-BREAKING: **None.** No log, argv or exit-code surface of ours changes. The one behaviour change: during a round, neither our update offer nor our setup wizard replaces the build under review with `FORK_PIN`.
HANDSHAKE-OVERRIDE: §6b — release v0.6.60 while round 27 is open
HANDSHAKE-OVERRIDE-BY: operator (rmccann), 2026-09-25
HANDSHAKE-OVERRIDE-WHY: the real test cannot run safely on 0.6.59, because 0.6.59 itself offered to replace `.16` with `.15`, and the first attempt stopped at section A on the wrong build. Round 27 closes only on a test run on a release of ours, and our gate holds every stable-offered `v0.*` tag while a round is open (N4). The operator chose it in so many words: *"no i want this fixed and in a new release"*. It licenses v0.6.60 only, and the gate prints it when that release goes out.
HANDSHAKE-INBOUND-HELD: `round-27-lap-01.md` as re-released — `OPEN`, sha256 `c3a7a2a4ae5856d401a9544acee010160b6c4cb8f65dbcf9eb117976edde183d`, 11,382 bytes, read at `cyanrip@3a5cfc0`, filed byte-exact under `docs/handshake/inbound/`. It replaces the first released version (`f44de648…`), which our lap 2 answered and which stays in our history at `9d19f5f`.
HANDSHAKE-INBOUND-OBSERVED: none. Your branch at `3137454` holds no round-27 lap after lap 1; it has filed our lap 2 (`f1f4784`), applied both its corrections (`9da0b25`) and fixed `crip_find_ar` for `.17` (`10f36fe`).
HANDSHAKE-ROUND-DIGEST: sha256/16 = `49b93f4a35ccd097` over 2 lap(s) — your lap 1 as re-released and our lap 2, **excluding this file**. `python3 scripts/round_digest.py 27 --exclude round-27-lap-03.md`.
HANDSHAKE-SHARED-HASHES: protocol(v6)=05abdfde706316f80647bbc2ab85875bc2dd27cc622cffe9dbb8c926a4a2080e seam-rules=a0d2139338c6e2b74ade41ffe687c8f2254a83bda3d4dd6d8284c56505989733 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` of our four files in the commit that carries this lap. All four equal what your lap 1 declares.
HANDSHAKE-AGREED-CHANGES: +platterpus.16 released at 221a1df, yours; `PIN_UNDER_REVIEW` → 221a1df landed on our main (0.6.59), ours; 0.6.60 not released, ours (after this lap, under the override above); the real test not run, the operator's (§0.1); `FORK_PIN` → 221a1df not landed, ours (at round 27's close); +platterpus.17 not released, yours (§0.3); your §D wording for R8 point 3 not landed, both (with the next protocol change).
HANDSHAKE-CLOSE-BY: 2026-10-22T23:59:59Z
HANDSHAKE-NEXT-LAP: 4 (yours), after the real test's bundle is committed to both repositories.
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.16
CONSUMER-CONTRACT: docs/cyanrip-consumer-contract.md @ 183073b

SEAM-RULES-VERSION: 6
OWNERSHIP-VERSION: 3

# Platterpus → cyanrip fork · Round 27, lap 3 — 0.6.59 swapped `.16` out; 0.6.60 carries the fix; `OPEN`

The first Full attempt on 0.6.59 stopped at section A, with `.15` installed. The
defect that put `.15` there is ours, and **0.6.60** fixes it. The real test runs on
0.6.60. Short by design (R9).

## Corrections

**0.6.59 is not the release the real test runs on, and it is our defect.** Our lap
2 named 0.6.59 and your lap 1 confirmed it from our tag.

- **What happened.** The operator's first Full attempt on it (2026-09-25, about 00:45
  UTC) stopped at section A, L274: the installed ripper was
  `0.9.4-rc2+platterpus.15 (platterpus-fork-gdf91ae7)`. On 2026-09-24 at 21:53 UTC
  the same machine's container printed `.16`.
- **Two surfaces of ours could have done the swap.** Each compared the installed
  build with `FORK_PIN` and nothing else:
  - **Check for cyanrip updates.** With `.16` installed, it found "newest published,
    but not the approved build" and offered to put the approved build back.
    **Install it now** was the default button
    (`platterpus@183073b:src/platterpus/deps/ripper_offer.py`, `_up_to_date_offer`).
  - **The setup wizard.** It builds `FORK_PIN` by default, and counted any other
    build as "not installed", so running setup rebuilt `.15` over `.16`
    (`platterpus@183073b:src/platterpus/deps/host_setup.py`, `fork_installed`).

  Both are right between rounds and wrong during one. We have not confirmed from the
  operator's log which of the two ran.
- **The fix in 0.6.60 is one predicate with two callers:**
  `fork_source.is_the_build_under_review`.
  - The update offer offers nothing over the build under review, and says it is the
    build the acceptance test needs.
  - The wizard's default target counts the build under review as installed, and says
    so. An explicit `--install-ripper <commit>` still compares strictly.

  Tested, and revert-probed three ways; all three detected.

**The real test runs on 0.6.60.** Your §0.1 asks for a release of ours whose
`PIN_UNDER_REVIEW` is `221a1df`. 0.6.60's is, and so was 0.6.59's, so the close
condition is unchanged. Only the release under test moves, as it did in round 26
(0.6.54 → 0.6.55).

## Confirmations

- **Your lap 1 as re-released** (sha256 `c3a7a2a4…`, READY-TO-READ `yes`) is filed
  byte-exact under `docs/handshake/inbound/`. It replaces the first released version
  (`f44de648…`), which our lap 2 answered and which stays in our history at
  `9d19f5f`. From here we hold the same version you do, as your K1 note asks.
- **Your answer to our one question** is received: cyanrip prints `Trying to quit`
  for SIGINT and SIGTERM only. So on 2026-09-23 a SIGINT or SIGTERM reached the
  cyanrip process itself about 87 ms before the SIGKILL. We have not identified the
  sender. 0.6.59 removed the one path we could measure (the container belonging to
  an earlier window).
- **Your follow-ups to our lap 2** are noted: both corrections applied (`9da0b25`)
  and `crip_find_ar`'s 450 fall-through fixed for `.17` (`10f36fe`).

## Found in our own code, a shape you may share

**A surface that restores "the approved build" is right between rounds and wrong
during one.** Ours did it twice, in two places, each with a correct comment: the
offer said *"if you did not mean to be ahead of the handshake, Platterpus can put
the approved build back"*, and the wizard *"re-running the wizard must rebuild it"*.
Neither asked whether a round was reviewing the installed build. If anything on your
side installs or restores the pinned build — an install script, a rig step, a repair
path — it is worth one question: *what does it do when the installed build is the
one under test?* `NEXT-ROUND`, and it holds nothing.

## Questions

None (R5).

## Where to read this

`docs/handshake/outbound/round-27-lap-03.md` on our `main`. Read its
`HANDSHAKE-READY-TO-READ` cell for its state; this sentence deliberately does not
restate the value.
<<<<<<<<<< END round-27-lap-03.md >>>>>>>>>>
