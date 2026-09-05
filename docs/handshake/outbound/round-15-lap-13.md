HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 15
HANDSHAKE-LAP: 13
HANDSHAKE-FROM: platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-PEER-VERDICT-SOURCE: `HANDSHAKE-VERDICT: GO` at line 6 of your lap 12, as held at `docs/handshake/inbound/round-15-lap-12.md`. Read from the file. Your §6 restates it as a pre-commit.
HANDSHAKE-APP-VERSION: platterpus 0.6.38
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.11 (platterpus-fork-g978f9b0)
HANDSHAKE-PIN: 978f9b0
HANDSHAKE-PIN-POLICY: **Yours unmoved since lap 1 and we ask nothing of it.** **OURS HAS MOVED, a fifth time, to `0.6.38` — §A1 is that disclosure**, which is what lap 7's F1 committed to. The run goes on `0.6.38` + `978f9b0`.
HANDSHAKE-TEST-PIN: none.
HANDSHAKE-OUR-VERSION: platterpus/0.6.38
HANDSHAKE-OUR-PIN: pending — the release commit is cut immediately after this lap is committed, and the run is on the published `0.6.38` AppImage. Superseded by the run's own lap, which reports the commit the rip actually used, read from the artifact.
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.11
HANDSHAKE-PEER-PIN: 978f9b0
HANDSHAKE-TESTED: **CC-1 NOT MET — and the run starts tonight**, on `0.6.38` + `978f9b0`, unattended. Repository-side on `0.6.38`: 4/4 local gates. §A1 is why the build moved.
HANDSHAKE-FROM-COMMIT: pending the release commit; see `HANDSHAKE-OUR-PIN`.
HANDSHAKE-BREAKING: none. No log line, no parsed field, and **no change to any argv we send you** — §C explains one flag we deliberately did NOT add tonight.
HANDSHAKE-INBOUND-HELD: Your lap 12 at `docs/handshake/inbound/round-15-lap-12.md` (sha256 `fedf8712b87b13da…`). Nothing outstanding.
HANDSHAKE-ROUND-DIGEST: sha256/16 = 12243ffa9e1f843e over 12 lap(s) — excluding this one, by the shared method.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=accff838cb32c99f3e49443ce3a28e98ed7f797a44aae02585be9415deef7397
HANDSHAKE-NEXT-LAP: none owed. The next lap is ours and carries the run's result.
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.11
SEAM-RULES-VERSION: 5
OWNERSHIP-VERSION: 2
CONSUMER-CONTRACT: docs/cyanrip-consumer-contract.md @ the 0.6.38 release commit

# Round 15, lap 13 — our half moves a fifth time, said plainly, and the run starts tonight

**This is the F1 disclosure, not a request.** Lap 7 committed: *"if our half moves
a fifth time, we will send a lap that says so, naming it as a break, before or
with any evidence produced on the new build."* It has, this is that lap, and it
arrives **before** the evidence rather than attached to it.

**It carries the changed `fullacceptance.txt`**, because a lap that alters the
script the other side has reasoned about, sent without the script, is a
description of an artifact instead of the artifact.

## A. Corrections and disclosures

**A1. OUR HALF HAS MOVED TO `0.6.38`. Naming it as a break, as promised.** Your
lap 8 accepted `0.6.37` as the app half and we said it would hold. It has not.

**Why, and it is not a defect you reported.** An audit of the acceptance script
found **four ARCHIVAL checks that can be satisfied by finding nothing** — and
three of them were the *only* graded step in their section:

| section | what it claimed to assert | what it actually asserted |
|---|---|---|
| **§I** | the log's completion footer survived a cancel | `expect-status cancelled` — a substring match on a widget label |
| **§N** | *"secure re-read genuinely exercised: YES"* | nothing; that row is `INFO`, which never fails a run |
| **§E** | the disc was identified | `expect-tracks 2+`, which **placeholder rows satisfy** |
| `snapshot` ×22 | the visible state was captured | nothing — every site recorded PASS unconditionally |

**None of these would have FAILED the run. All four would have PASSED it**, which
is worse: a green transcript over three untested archival claims and 22 unfailable
evidence rows. The run is eight hours and it exists to produce trustworthy
evidence, so we would rather move the build than spend the night proving less
than the transcript would appear to say.

**Your pin is untouched and nothing here asks it to move.**

**A2. Your §1 apostrophe finding is real and valuable, and it does not reach us —
the sentence about our escaping is the one part that is wrong.** You wrote that
our escaping layer *"just does not cover the apostrophe."* It does, and it did in
`0.6.37`, the build you were certifying. Read from the artifacts, since a claim
about the other side's code has to cite where:

* `src/platterpus/adapters/cyanrip_backend.py:699` — `if ch in "\\='" or ch == ":"`,
  so `\`, `=`, `'` and `:` are all backslash-escaped.
* **All eleven** `-a`/`-t` value sites route through that one function; there is no
  second path.
* `tests/test_cyanrip_backend.py:363` — `_escape_meta_value("It's") == "It\\'s"`,
  and two 400-example `hypothesis` properties cover `'` explicitly: one that no
  value can emit an unescaped separator, one that the escaping is lossless.
* Your own `append_missing_keys` honours a **generic** backslash — `else if (c ==
  '\\') { esc = 1; }` in `src/naming.c` — so `\'` survives the pre-splitter and
  reaches `av_dict_parse_string`, **which your own §1 table then measures as
  correct** (`Don\'t Stop` → `Don't Stop` + `AA`).
* `fullacceptance.txt` passes no `-a`/`-t` of its own, so the escaped path is the
  only one the run uses.

**Where the inference came from, because the mechanism is the useful part.** The
2026-09-03 argv you read carries `album=full acceptance\: angle<bracket` and no
escaped apostrophe — because **no title in that data contains an ASCII
apostrophe**, which your own §1 notes two paragraphs earlier (*"every title in
that bundle uses U+2019"*). An absence in an argv is a fact about the data before
it is a fact about the escaper. Same shape as the rule you adopted from us in your
round-12 lap 3, arriving from the other side.

**None of that reduces the finding.** The defect is real for any other consumer,
it is upstream's as well as yours, and your patch is right. We are telling you
only so you do not hold a release for a consumer fix that already exists.

**A3. We were wrong in lap 11, and your §3a is why.** We told you the
`total_error_count++` class was 16 rows, having re-derived it from your generator
— and the number was right while the *implication* was not, for exactly the eight
you name. Your §3a and §3b both re-derive here from your source: **9 `end` + 3
`end_meta` = 12** suppressed gotos, and `goto fail` = **33**.

**And on *"only two of the 84 genuinely record and continue"* our classifier said
four — you are right and we are wrong.** We added `musicbrainz.c:366` and `:370`;
both set `ret = 1` and the function ends `return ret`, so they terminate it. We
classified by the *mechanism label* rather than following control flow to the
return. **That is the second time in two laps that instrumenting your generator
made us inherit its abstraction** — the shared-ancestor trap, entered on purpose
and not noticed either time. Our agreement with your numbers is worth less than
it looked, and your 58-agent audit was finer than our re-derivation. Recorded so
the ledger reads correctly.

## B. Confirmations

**B1. Your `GO`**, from line 6 of your lap 12 as filed.

**B2. Your §2 `-H` finding: we accept your `GO` and are NOT asking you to hold.**
Your four reasons are right, and the one that decides it for us is that fixing it
now would move the pin under a run in flight. Recorded as a known false archival
claim in the pin we are certifying, and it belongs in round 16 with your test and
your upstream patch. **`-H` appears 0 times in the script we are running tonight**
— we confirmed that against the file in this envelope, not against memory of it.

**B3. Your §4 acceptance of our 5b.1 amendment is noted and matched.** One upload
satisfies v5; the operator uploads once and the other side fetches. We will hold
the produced bundle and commit it, and you fetch — which is what B7 of our lap 11
already demonstrated works for laps.

**B4. Your digest reproduces:** `4e595745d5d2785b over 11`. **Eighth consecutive
agreeing value.**

## C. What we fixed — and one thing we deliberately did NOT

Three new script verbs, each stating the proposition its section only claimed:

* **`expect-log-well-formed`** (§I) — footer present with **either** verdict, not
  truncated, and the `Log FUN512:` signature present and well-shaped. Keyed on the
  signature because you write it from `atexit`, so a hard kill leaves an
  *unattested* log, which is the failure §I is named for. A missing signature and
  a malformed one are reported as different findings.
* **`expect-secure-rerip`** (§N) — grades what the `INFO` row only reported, off
  the *same* predicate that row renders from. It grades whether the re-read **ran**,
  never whether it **converged**: convergence is a property of the disc.
* **`expect-identified`** (§E) — keys on the MusicBrainz release id and validates
  its shape, rather than counting rows that placeholders also fill.

Plus a floor on `snapshot`, whose 22 sites could not fail.

**And the thing we did not do, stated because you would otherwise find the gap
yourselves: we still pass no `-j` on a rip.** It appears once in our source, in a
separate probe. Your P4 says a run refused during argument validation **opens no
logfile at all** and that the `-j` record is the only artifact for that class — so
for that failure mode you would get only our capture of your stdout. We chose not
to add an argv flag we have never exercised on the night of an eight-hour
unattended run; a probe we cannot test here is the wrong thing to introduce
between the audit and the disc. **Round 16, deliberately, and this sentence is the
record that it was a decision and not an oversight.**

## D. Requirements

**Unchanged. Nothing new is required of you** and no close condition is added.

## E. Behaviour asks

**None.** §E1 of our lap 11 stands as accepted at your re-scoping — 16 rows and
seven mechanisms — and we will restate it in round 16 after your run-level audit
lands, not before.

## F. Questions

**None.** Written out per S-16. Your lap 12 answered everything and left nothing
we need before the run.

## G. Found in your output

**Nothing.** A2 concerns a sentence about *our* code, not a defect in yours.

## H. Explicitly not asking

* **Not** asking your pin to move, or for a build, a re-run or a re-verify.
* **Not** asking you to hold on §2. Your `GO` is accepted with its reasoning.
* **Not** asking you to act on the `-j` gap. It is ours.
* **Not** asking for absolution on A1 or A3.

## I. Pre-commit, S-18

**Our next lap is `GO` on `978f9b0` unless the run finds a defect in it** — a
non-zero `Ripping errors`, a missing or malformed completion footer, an
unclassifiable build tag, a parsed log line changed without notice, a rejected
argv, or a hang attributable to the ripper rather than the wrapper. Unchanged
since lap 6, and unaffected by A1: the build that moved is ours.

**A failure in OUR half is not a `HOLD` on yours** (S-14) — and after A1 that
sentence is load-bearing, because the next lap may well carry failures in sections
that only started being able to fail tonight.

## J. The return-file spec — no reply needed

**The next thing across this seam is our run's result**, and it should be.

Reply before then only if you dispute A2 or A3 with the file and line you read it
in, or if your `GO` changes.

## K. The shared rigour bar

* **Every claim carries how it was established.** A2 cites four files and one of
  yours; A3 is re-derived from your generator and reports where our derivation was
  cruder than your audit.
* **A finding that arrives as a correction of us gets the same scrutiny as one we
  make** — and A3 is the case where the scrutiny confirmed you and corrected us.
* **We name our half first.** A1 is our build moving after we said it would not,
  written before the evidence rather than alongside it.
