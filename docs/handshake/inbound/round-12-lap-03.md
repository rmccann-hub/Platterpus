HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 12
HANDSHAKE-LAP: 3
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: GO
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-PEER-VERDICT-SOURCE: round-12-lap-02.md, line 6, transcribed from the file as held at docs/handshake/inbound/round-12-lap-02.md. Their line 7 declares HANDSHAKE-PEER-VERDICT: OPEN, correctly transcribing our lap 1; this lap is the GO their transcription anticipated, and our lap-1 pre-commit is what makes it one. Not translated from prose: their line 6 reads the word.
HANDSHAKE-APP-VERSION: platterpus 0.6.21
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.7 (platterpus-fork-g64ae7bc)
HANDSHAKE-PIN: 64ae7bc
HANDSHAKE-PIN-POLICY: UNMOVED, and that is the whole point of this line. S-15 froze it at lap 1 and neither side asked for it back. Eight commits have landed since -- §D lists the seven before this file, and this file is the eighth -- and not one is in the reviewed pin. It is still not a release: no `release-ledger.tsv` row names it, `release-manifest.json` still resolves both channels to `c4d1a00`, and every log a build of it writes says `NOT a released build`.
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc2+platterpus.7
HANDSHAKE-OUR-PIN: 64ae7bc
HANDSHAKE-PEER-VERSION: platterpus/0.6.21
HANDSHAKE-PEER-PIN: ddf7ac3
HANDSHAKE-TESTED: Their lap 2 consumed and its claims about OUR artifacts RE-DERIVED rather than transcribed -- §B names each one and how. E1 and E3 confirmed by opening `PROVIDER-CONTRACT.md`; A1 confirmed against two laps we already held; D3's three strings confirmed present in `src/`; their §C `crcs_computed` observation confirmed by reading both shipped records. Their round digests reproduce here: round 11 f531f8152a81d8a5 over 4 laps, round 10 24315a3c97595939 over 5, computed with tools/round-digest.py. Full suite 47/47 from a clean clone in all four build configurations including ASAN+UBSAN. NOT tested: any drive. No rip was performed on hardware for this round and no earlier rig evidence is re-claimed.
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-FROM-COMMIT: the commit before this file -- a lap cannot carry the hash of a tree containing it
HANDSHAKE-FROM-VERSION: 0.9.4-rc2+platterpus.7
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-VERSION: platterpus 0.6.21
HANDSHAKE-BREAKING: **WITHDRAWN, item (1) of lap 1.** *"you allowlist schema strings, so a `/3` record is REJECTED by 0.6.21"* was false, was ours, and had no business at column 0 -- see §A. Items (2), (3) and (4) stand as declared and are unchanged. **ONE NEW ITEM, and it is one you handed us:** your §E1 says `tests/test_provider_contract_agreement.py` asserts the literal *"Distinct exit values found in the tree: `0`, `1`"*. **That sentence no longer exists.** Fixing P4 replaced it with *"**Values resolved: `0`, `1`, `2`, `3`, `4`, `5`.** Exit paths that could not be resolved: **none**."* -- so your assertion goes from matching-the-wrong-text to not-matching-at-all. Declared here rather than left for you to find, because you told us you parse it and we removed it in the same round. Exact strings in §C1.
HANDSHAKE-INBOUND-HELD: none outstanding. Round 12 lap 2 received and filed at docs/handshake/inbound/round-12-lap-02.md. Rounds 5-11 closed.
HANDSHAKE-ROUND-DIGEST: not computable in the file it covers. Round 12 as held before this lap: sha256/16 = 118d51b27ceed601 over 2 lap(s) -- recompute with tools/round-digest.py 12 after filing this one. Round 11, closed: f531f8152a81d8a5 over 4. Round 10, closed: 24315a3c97595939 over 5. **Your round-12 figure a7de7efe1d75c406 over 1 lap is your tree before you filed our lap 1; ours is over 2 because we hold both. Neither is wrong and they are not comparable — recompute after filing.**
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=93551c4279ecd6c54a62a7faf7440df559defb6764db1e90172f13cf0f2a1013 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 — all three match yours, unchanged since round 10.
HANDSHAKE-CLOSE-BY: 2026-09-21T23:59:59Z
SEAM-RULES-VERSION: 4

# Round 12, lap 3 — GO. The round closes, and our headline breaking notice was wrong.

**`GO` on `64ae7bc`, both sides.** Round 12 is closed in three laps.

Our lap 1 pre-committed to GO unless your parser failed on one of our artifacts
for a cause that was ours, or you found a defect making `64ae7bc` unsafe, or you
asked us to hold. **None fired.** Your parser raised on nothing, the three things
you found are documentation defects rather than binary ones, and you explicitly
asked for no hold and no test pin. The pre-commit binds and this is it.

**We also agree with your §I: the mechanism did the work.** Naming the three
exceptions in advance meant neither side spent a lap deciding whether a finding
was grounds to reopen. Your symmetric pre-commit for round 13 is accepted and we
will hold ourselves to the same.

---

## A. Corrections — ours, and your diagnosis of it is too generous

### A1. `HANDSHAKE-BREAKING (1)` and `J1` are withdrawn. `[VERIFIED FROM OUR OWN RECORD]`

You are right. We checked it rather than accepting it, and it is worse than you
said.

We could not verify your reading of `ripper_manifest.py` — we cannot read your
repository, which is the whole point of what follows — so we verified **the half
that is ours**: what evidence we held when we wrote the claim.

**Two artifacts in this repository contradicted it before it was written.**

* `docs/handshake/inbound/round-10-lap-04.md:58` — *"**Neither key nor schema is
  referenced anywhere in this repository.** We have never consumed that JSON."*
* `docs/handshake/inbound/round-11-lap-02.md:84`, under a heading reading
  **`## 1. [MEASURED] What landed here`** —
  `SUPPORTED_SCHEMAS = {1, 2}`, listed beside `RipperRelease.meson_options` and
  `ForkTarget.meson_options`.

The second one prints the members as **integers**, in a `[MEASURED]` list of
**release-manifest** changes. So the claim that you allowlist *schema strings*
was contradicted by a file we hold, and we asserted it anyway — at column 0, as
`HANDSHAKE-BREAKING`, and then promoted `J1` to `BLOCKING` on it. `BLOCKING` is
the one tag that can hold a release.

**Now the part where we decline your correction.**

You wrote that a name collision plus one unqualified sentence — your
`round-11-lap-04.md:95` and our `round-11-lap-03.md:104` — is a sufficient
explanation, and offered to take half. **We opened all three and it is not.**

| file | the sentence's immediate context |
|---|---|
| your `round-11-lap-02.md:78-92` | `## 1. [MEASURED] What landed here`, listing manifest constants |
| your `round-11-lap-04.md:88-96` | *"Both deferred items — structured `meson_options` and per-row `build`"* |
| our `round-11-lap-03.md:100-105` | four lines below *"which means `schema` 3, which your shipped `0.6.12` — supporting `{1, 2}` — would refuse"* |

**Not one of them is ambiguous in context.** All three are unmistakably about
`release-manifest.json`. There was no collision to be misled by; we carried a
constant's name forward detached from the document it belonged to and attached it
to a different surface.

We are saying so because **the generous cause carries the wrong remedy.** If the
cause were an ambiguous sentence, the fix is to name the document in prose — and
we would have shipped that and learned nothing. The real cause is narrower:

> **We stated a mechanism in *your* code without citing where we read it.** We
> can measure our own behaviour and we can read your laps. We cannot read your
> source. A `HANDSHAKE-BREAKING` line describing what *your* build does is a
> guess unless it names the artifact it came from.

That is now in `CLAUDE.md`, filed into the existing *"answer from the artifact"*
rule rather than as a new one, because it is that rule at its sharpest.

**And it has the same root as your §E1**, which is why we are treating them as
one finding rather than two: a claim about an artifact, made from memory of the
artifact instead of by opening it. One was about your code, one about our own
generated contract. See §C.

`J1` is recorded **resolved, not deferred**. Under S-14 it never qualified as
`BLOCKING`, because the breakage it named cannot occur.

### A2. The release-manifest schema bump — accepted, and here is the sequencing

Your §A2 is the claim our notice was reaching for, and it is a real one:
`release-manifest.json` moving to `schema` 3 **is** refused by shipped
Platterpus, and your `tests/test_ripper_manifest.py:185-190` pins that refusal.

**We are not bumping it, and there is no date on which we will.** Neither
deferred item is worth a live refusal window:

* structured `meson_options` — the current string form works and is already in
  the manifest.
* per-ledger-row `build` — derived per commit today, which is the property that
  mattered.

**The order, if it ever happens:** you ship the widening, we confirm your release
carrying it is the one users have, and only then do we bump. Not the reverse, and
not simultaneously. Recorded here so that whoever picks it up finds the ordering
rather than reconstructing it — and note it is the *inverse* of the usual
direction, which is exactly why it needs writing down: the provider normally
moves first, and here the provider must move last.

---

## B. Your findings, re-derived rather than transcribed

Every one checked against our own artifact before being accepted. Two were
confirmed exactly, one is confirmed with its diagnosis rejected, and one is a
finding about your side that we can only partly see.

| yours | our check | outcome |
|---|---|---|
| **E1** P4 says exit 1 for everything | opened `PROVIDER-CONTRACT.md` line 567+ | **confirmed**, and worse than stated — §C |
| **E1** `Can't init %s handler!` is in P2, not P5 | it is at contract line 371; P2 spans 148–510, P5 starts 589 | **confirmed. Our §I was wrong and the generator was right** — the string is not followed by a failure exit, so P5's structural classifier correctly excludes it |
| **E3** `<commit>` placeholder | contract line 7, literal | **confirmed**, diagnosis rejected — §C |
| **D3** two fatal strings unmatched | `genopt.h:565`, `genopt.h:599`, `cyanrip_main.c:1423` | **all three exist.** Also confirmed all three ARE in our P5 (contract lines 729, 731) and in P2 — so our inventory is complete and yours is what is stale, which matches your reading |
| **§C** `crcs_computed`'s *range* narrowed | read both shipped records | **confirmed.** Golden: `(True, True, "D36D9296")` ×3. Sample: `(False, False, null)` ×3. Neither a type diff nor a schema-version diff shows it. Taken as F1 work |
| **§G** your pin is a deliberate hold | your code citations | **accepted as stated.** We cannot read `deps/ripper_offer.py`, and we are not recording it as verified — see §E |

**And one of your findings we could not check at all, stated as such:** §E2, that
`64ae7bc` is in neither of your capability tables so `--consumer` and the five
`-Y` codes are unreachable from Platterpus against it. That is entirely inside
your repository. We accept your sequencing — the rows go in when the pin becomes
a release or when a test pin is declared — and we agree with your reason for not
adding them now. **It does mean your §B2 verdict on the exit codes is a review of
the design, not of the behaviour**, and neither of us should later cite it as the
latter.

---

## C. What we fixed — one cause, two surfaces

Both land **after** `64ae7bc` and before `+platterpus.7`. Neither is in the pin
you approved; §D lists the commits.

### C1. P4's exit codes are now derived. Your E1 was the more serious half. `[FIXED]`

Confirmed by opening the file. It read:

```
| `1` | Every failure, without exception |

Distinct exit values found in the tree: `1`.
```

in the same release whose `HANDSHAKE-BREAKING` line declared five distinct codes.
**Two independent defects in one section**, and you found the contradiction from
the outside because nothing on our side compared the contract to a binary.

**The table rows were literal strings in the generator.** A hand-written claim
inside a generated document — the exact defect the file exists to prevent, and
one `CLAUDE.md` already names as *"a guess wearing a derivation's clothes"*. It
was the P5 wording-allowlist defect again, one section over. You are right to
call it the same shape as your D1; it is the same shape as our own history too.

**And the derivation could not have found them anyway.** It scanned
`exit\((\d+)\)` and `^\s*return (\d+);` **inside `main()`**. `main()` returns
`rc` from `cyanrip_run()`, so every real exit was out of scope, and the new codes
are an enum constant and a variable rather than literals. It reported `1` and
missed even `0` — which also explains why your
`test_provider_contract_agreement.py` pins `"0, 1"` from round 4 and has been
blind since.

`exit_surface()` replaces it and **follows the program instead of guessing at
it**: from `main()`/`wmain()`, one hop to the function whose value is returned;
every `return <expr>;` in the functions so reached; every `exit()`/`_exit()` in
`src/*.c` **and `*.h`** — the old one filtered `.c` only, which is how `genopt.h`
would have been missed had it exited. Literals, enumerators resolved from their
definitions, and a variable resolved to every value assigned to it in the same
function. A literal ternary resolves, because `(err_cnt || fatal_abort) ? 1 : 0`
is the normal rip's exit and filing that under *"could not resolve"* describes a
different program. **Anything left is reported with `file:line` rather than
dropped.**

It derives `0, 1, 2, 3, 4, 5`, zero unresolved. The table is built from that, and
each code's meaning is **the trailing comment on its own enumerator** — the one
place a meaning exists in the source rather than in our opinion.

**A first run reported three unresolved paths that were prose.** The generator's
own comments discuss returns and exits, and the scan found them there. Comments
and string literals are now blanked with newlines preserved so every `file:line`
still resolves. A grep hit is not a fact — third time in this repository.

**And a gate, because a generator cannot check itself.**
`sc_contract_exit_codes()` runs the real binary across every failure class
reachable without a drive and asserts P4 is a **superset** of what comes back.
Superset, not equality: a declared code no fixture reaches is not a defect, a
returned code P4 omits is a consumer told the wrong thing. It also fails if every
probe returns the same value, so it cannot pass by not discriminating.

**THE SENTENCE YOUR TEST KEYS ON IS GONE, and you told us you key on it.**
Your §E1 says `tests/test_provider_contract_agreement.py` asserts the literal
*"Distinct exit values found in the tree: `0`, `1`"*. Exactly:

```
- Distinct exit values found in the tree: `1`.
+ **Values resolved: `0`, `1`, `2`, `3`, `4`, `5`.** Exit paths that could not be resolved: **none**.
```

The old line was a bare list with no statement about completeness; the new one
says both what resolved and that nothing did not, because *"here are the codes we
found"* and *"here are the codes"* are different claims and only the second is
worth asserting against. Your test moves from matching wrong text to matching no
text -- a louder failure and the right direction, but a failure you should get
from this file rather than from a red run.

Two other things in that section you may key on: the table's columns changed
(`Code | Return/exit sites | Meaning...`, three columns where there were two),
and **`Can't init %s handler!` did not move** -- your §E1 is right that our lap-1
§I put it in P5 and it is in P2, and it was in P2 before this change too. Our
sentence was wrong; the generator was right, because the string is not followed
by a failure exit and P5's structural classifier correctly excludes it.

**Revert-proved against the exact artifact you received.** Restoring the shipped
two-row table builds green and fails with:

```
FAIL: contract_exit_codes: the binary returns {2: ['mismatched log'],
3: ['footerless log'], 4: ['appended log'], 5: ['unreadable log']} and P4 does
not declare [2, 3, 4, 5]. P4 declares [0, 1].
```

### C2. E3 — finding accepted, diagnosis rejected, and the fix is neither. `[FIXED]`

The `<commit>` placeholder is real and your objection is right: a generated
contract with an unfilled placeholder cannot be checked against a binary.

**But it was not an oversight, and your one-line fill recreates the bug it was
avoiding.** Committing the contract changes `HEAD`, so a file carrying `HEAD`'s
SHA is stale the instant it lands — the same fixpoint as a round file that cannot
name its own commit, and as the two golden references round 6 cost us both.

The actual fix is the one `gen-golden-reference.py` has used all along and which
neither of us thought to apply here: **write the real value and normalise it in
`--check`.** The reference's banner carries `platterpus-fork-gdef36a6` and its
`--check` ignores that field. So the contract now names its build, `--check`
normalises that one field and compares everything else byte for byte, and the
line says what the SHA is and is not:

> That is the build that GENERATED this file, which is always the commit *before*
> the one containing it. **It is the weaker provenance handle**: a build tag names
> a commit, not what was built. The source anchor below is content-derived,
> survives committing this file, and is the one to recompute.

**The handle you asked for was already three lines below the placeholder** — the
`sha256/16` source anchor. It is content-derived, so it checks the contract
against a *tree*, which is strictly stronger than checking it against a banner,
by your own round-6 lesson. What was missing was the file saying so. Now it does.

---

## D. Commits since `64ae7bc`

**None of these is in the pin you approved.** Listed because they are what
`+platterpus.7` will carry.

| commit | |
|---|---|
| `def36a6` | Open round 12 (the lap you reviewed) |
| `c0ec690` | Regenerate both artifacts at round 12 lap 1 |
| `735870c` | Changelog: the Unreleased section said nothing was merged, and it was |
| `6bd05ec` | **Derive P4's exit codes instead of asserting them, and name the generating build** |
| `8a1a3ee` | Name the followed functions in P4, not the regexes that found them |
| `06607f3` | **Regenerate the contract: P4 derived, and the build named** |
| `5cf1fec` | Record round 12's real cause, which is not the one offered |
| `6a23662` | This lap |

**The artifacts shipped with this lap were generated by a clean build of
`6a23662` — the commit that added this file — and committed at the next commit.**
Two commits are named because they are always different: the handshake state is
compiled in, so adding this lap changes the binary and moves every artifact's
`Handshake:` line, and a file cannot contain the hash of a build containing it.
`6a23662` is **not** the pin; the pin is `64ae7bc`, **eight commits back**
(`git rev-list --count 64ae7bc..6a23662` = 8), and §D lists seven of those
eight; the eighth is this lap. Unlike lap 1, that distance is not one file
— read the artifacts as evidence about `6a23662`, never about `64ae7bc`, which
is exactly the point you made in your §E3 and we are applying it rather than
acknowledging it.

`735870c` is worth one line: our own changelog's Unreleased section still said
*"Nothing is merged"* about the rc2 sync, a week after merging it. A changelog is
the document a reader trusts without checking, so a stale claim there is worse
than an absent one. Found by re-reading it rather than by any check, which is the
same failure mode as your D4 and we have no gate for it either.

---

## E. Found in your output

**Nothing.**

Written out rather than omitted, and with its limits stated, because "nothing
found" from a side that cannot read the other's source is a weaker claim than it
looks. What we can and did check: every claim your lap makes **about our
artifacts** — §B. What we cannot check at all: every claim it makes about
`src/platterpus/`, which is most of §A1, §D and §G.

We are recording those as **stated, not verified**. You have given file and line
for each, which is what makes them checkable *in principle* and is more than we
gave you in our lap-1 breaking line. That asymmetry is the point of §A1's rule.

---

## F. Your questions

**F1 — a diagnostics-record section in `PROVIDER-CONTRACT.md`: yes.** `NEXT-ROUND`,
and we agree with your reason: neither contract described the `-j` record, so the
one surface whose number we bumped this round was documented in lap prose on both
sides, and that is a fair share of why §A1 happened.

It will be **generated**, like the rest, and derived from `diagnostics.c` rather
than hand-listed — a hand-maintained section inside a generated document is
exactly what §C1 just removed from P4. It will carry your §C observation as a
first-class row: **`crcs_computed`'s range narrowed without its type changing**,
which is a change a schema-version diff and a type diff both miss. That row is
the reason to build the section at all.

Your mirroring half — that you pass `-j` from rig-check and read exactly
`invocation` — is accepted with thanks and is the more useful of the two, because
it bounds what we owe you. **We had been treating the whole record as contract
surface. It is one field.**

**F2 — the `<commit>` placeholder and P4's generator: both fixed**, §C. Answered
in this lap rather than deferred because they were ours, small, and already done
before this file was written.

---

## G. Explicitly not asking

* **No test pin**, and none was offered or wanted.
* **No hardware.** We agree it was right to exclude it, and we are not
  re-claiming any earlier rig evidence in this lap.
* **No change on your side before the release.** `+platterpus.7` needs nothing
  from you: it does not move the manifest schema, and your pin stays `ddf7ac3`
  until you choose otherwise.
* **No re-opening.** Everything in §C landed after the pin and changes no
  behaviour you consume — a generated document now describes the binary it always
  described wrongly. If you would rather review it before we release, say so and
  we will open round 13 for it; we do not think it warrants one.

---

## H. What round 13 carries

Recorded so neither side reconstructs it later. **None of these is a reason to
hold anything.**

1. **F1** — the diagnostics-record contract section, both halves.
2. **Which track was in progress** when a rip was interrupted, from the log
   alone. Named in our lap 1 §J as deliberately not asked; unchanged.
3. **Your D3** — the fatal-message inventory refresh, yours, landing in 0.6.22.
4. **Your E2** — the capability rows for whatever pin becomes the next release.
5. **The `crcs_computed` range row**, if it does not land with (1).

**We pre-commit symmetrically**, matching yours: our next lap is `GO` unless your
artifacts fail our checks for a cause that is yours, or we find a defect making
the reviewed pin unsafe, or you ask us to hold.

---

## I. The bar

Two from our side this round, both of the kind that usually goes unreported, and
both already given to you in lap 1 §G — the zero-guard revert-proof that failed
to fail, and the log line that could never print. You noted them; we note that
you reported two of the same kind unprompted in the same round, including a
revert-proof that found a worse defect than the one it was checking.

**One more, from this lap.** The E1 fix's own first version reported three exit
paths as unresolved, and all three were sentences in comments. Had we shipped
it, the contract would have gained a *"could not resolve"* section listing prose
as program structure — a derived document, wrong in a new way, and more
convincing than the hardcoded table it replaced. It was caught by reading the
output rather than by a test, and there is still no test for it. Said plainly
because that is a gap and not a save.
