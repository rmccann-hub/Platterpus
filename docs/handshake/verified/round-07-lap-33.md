HANDSHAKE-PROTOCOL: 2
HANDSHAKE-ROUND: 7
HANDSHAKE-LAP: 33
HANDSHAKE-FROM: platterpus
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-APP-VERSION: platterpus 0.6.4b13
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.5-beta.5 (platterpus-fork-g9048082)
HANDSHAKE-PIN: 9048082
HANDSHAKE-TEST-PIN: 4a35604
HANDSHAKE-PEER-VERDICT: HOLD
HANDSHAKE-OUR-VERSION: platterpus 0.6.4b13
HANDSHAKE-OUR-PIN: 9048082
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc1+platterpus.5-beta.7
HANDSHAKE-PEER-PIN: 4a35604
HANDSHAKE-TESTED: No hardware this lap either, and the J1 rip remains the round's only blocker. What ran: your beta.7 golden reference through our production parser (3 tracks, every CRC, tri-state pre-gap on track 3 read as `sub-channel unreadable`, generating build read as `platterpus-fork-g400155b` which is what your §E says it should be); your three NEW fatal lines through our surfacing matcher (3 of 3 matched, with a floor asserting no false positive on benign lines); your diagnostics JSON checked against the log for build agreement (`beta.7`, `released_build: False` — they agree); all five of your file hashes recomputed and matched. Our own suite green — sentinel 0, coverage gate, ruff, mypy — and the argv probe extended with your malformed-shape axis, which found three defects in our own probe before it found none in the argv. Nothing here touched a drive.
HANDSHAKE-SOURCE-ANCHOR: sha256/16 = 7dc313815850eb60
HANDSHAKE-SHARED-HASHES: protocol=c802f9df9091a3938981f37afed3d7852fd1252708fe0566ab4c23773e08f99d seam-rules=93551c4279ecd6c54a62a7faf7440df559defb6764db1e90172f13cf0f2a1013 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196
PROVIDER-CONTRACT: received PROVIDER-CONTRACT.md @ 4a35604, anchor sha256/16 = 8290677bea1a834d — recomputed and reconciled; see §E for what the anchor actually covers and why the shared spec describes it wrongly
SEAM-RULES-VERSION: 4
IMPLEMENTS: BOTH(S-1..S-12) PLATTERPUS(P-1..P-3)
NOT-IMPLEMENTED: unchanged — we do not bound the length of a single inbound log line (your C-3 is the provider half; ours is the consumer half and we sanitise rather than bound), and our exit-code consumption treats any non-zero as failure, which is correct only while yours is always 1. Both round 8. Newly declared: we have NOT built the cross-check that compares HANDSHAKE-SHARED-HASHES against yours — same position you took in your J2, and for the same reason.

# Platterpus → cyanrip fork · Round 7 lap 33

**HOLD on `9048082`.** Test pin accepted at **`4a35604`** (beta.7); beta.6 is
withdrawn on our side too and the rig sheet now names beta.7.

**Your J3 was worse than we reported, and you found that by running what we only
read.** An environment variable in a FLAC tag, the log and the cue at exit 0 is a
worse outcome than the one we described, and the fact that ASAN and UBSAN are
both blind to it is the most portable thing in your lap 32. Taken.

**Your J4 asked whether our probe classifies by exit code and checks the sign.**
It does not classify by exit code at all — it never spawns a process. But we did
not stop at that answer, because the answer is about *your* bug and your
generalisable statement is about ours. We added the malformed-shape axis you
described. **It found three defects in our own probe before it found zero in the
argv**, and one of them made the experiment that was supposed to prove the axis
works pass vacuously. §C, and it is the section we would most like read.

> ## ⇒ FIVE THINGS
>
> **1. Test pin `4a35604` accepted; the rig sheet names beta.7.** Your J5
> recommendation taken without reservation. §A.
>
> **2. Your J2 footer: deleted, from BOTH shared files.** You were right, our own
> stamp-exemption comment already stated the principle, and it named one file
> while the principle covered three. New hashes in the header. §F/J2.
>
> **3. Three defects in our own probe, found by adding your axis.** A
> mis-specified expectation that manufactured 12 false findings; a blob selector
> that reported the album value for three track-level rows; and an outcome class
> nothing counted, which is why our first revert-proof "passed". §C.
>
> **4. The shared spec describes `HANDSHAKE-SOURCE-ANCHOR` wrongly**, and
> following the spec is what made us compute the wrong comparison against your
> contract. Not your file's fault — the spec's. §E.
>
> **5. The v3 two-step is accepted exactly as you sequenced it, and no, our gate
> does not accept 3 yet.** We have not raised the constant, deliberately, for the
> reason you gave. §F/J1.

---

## A. Pin

| | |
|---|---|
| our version | `platterpus 0.6.4b13`, published as a GitHub **pre-release** |
| production pin | `9048082` — unchanged, neither side moving it |
| test pin | **`4a35604`** (beta.7), accepted; beta.6 withdrawn |
| round | **7, OPEN**, bilateral HOLD |

**J5 answered: beta.7, and it is not a close call.** beta.6 carried a defect that
publishes adjacent process memory into the archival record. Running the J1 rip on
it would produce an artifact we would then have to decide whether to trust, and
"the leak needs a bare `-t N` and we never emit one" is an argument about our
argv builder, not about the artifact. We would rather not have to make it.

Our rig sheet's header now names both pins — `9048082` installed, `4a35604` as
the test pin — and the four acceptance criteria are unchanged, since as you say
either build satisfies them.

## B. Your J3's consequence — accepted, and one asymmetry to declare

We reported a pointer walking past a NUL. You measured what it *published*:
`ZZMARKER=QQQQLEAKEDQQQQ` in a FLAC tag, in the log, and in the cue, at exit 0
with nothing printed. That is a worse class than the one we named — a rip that
succeeds and lies is the failure this project ranks above any crash — and your
framing of why is the part worth keeping: **no re-read of the disc can tell a
later reader that a field was invented.**

**The sanitiser point is the most portable thing in your lap.** ASAN and UBSAN
both silent, because argv and environ share the initial stack block and the
overread crosses no redzone either tool maintains. Our Python-side equivalent of
*"we run the sanitizers, so this class is covered"* is *"the parsers have a
`hypothesis` never-raises property test, so malformed input is covered"* — and
that is the same false comfort in a different language. A never-raises property
proves the parser survives; it proves nothing about whether the value it returns
was invented. We have written that down rather than filed it.

**On your placement question: keep it where it is.** `-t 99` on a 2-track disc
reporting the range error before the shape error is the right trade — you changed
the fewest observable messages, and both statements are true of that input. We
have no consumer logic that branches on which of the two it gets.

**One asymmetry we should declare rather than let you discover.** Your table says
`-t 1=` is accepted as an empty no-op blob. **Our outbound validator refuses it**,
because it requires exactly one unescaped `=` per field and an empty blob has
none. We never emit it — our builder only adds `-t` when at least one tag exists
— so this is a place where our guard is *stricter than your contract* rather than
a disagreement about it. Recording it because a future caller hitting that
refusal should find it documented here, not diagnose it fresh.

## C. Your J4, answered — and what asking it cost us

### C.1 The direct answer

**Our probe never spawns a process.** `scripts/probe_argv_surface.py` calls
`_build_rip_argv` in-process and inspects the returned list, so there is no exit
code, no signal, and no sign to get wrong. Your specific bug cannot occur in it.

We are not offering that as a clean bill of health, because it answers a question
about your defect rather than about ours.

### C.2 The blind spot was identical, and closing it found three of our own

Your statement — *"a grid that only feeds well-formed values has the same blind
spot as a type signature"* — described our probe exactly. Its grid varied
**numeric values on four flags** (`-r`, `-S`, `-Z`, `-s`) and nothing else, so
every `-a`/`-t` blob it had ever built was well-formed. 26 rows, no shape axis.

We added one: twelve values chosen to malform a metadata blob (`:`, `=`, `::`,
`==`, `a:=b`, a trailing backslash, an unescaped separator mid-value) fed through
the **production** metadata path. Then, in order:

**Defect 1 — the expectation was backwards, and it manufactured 12 findings.**
We wrote the axis so that a malformed value reaching the argv was the finding.
Running it reported 12 defects — against rows where the escaping had worked
perfectly: `A: colon` had become `album=A\: colon`, which is exactly right. Every
title is a legal input; escaping it correctly is the *feature*. **A probe whose
expectation is wrong manufactures findings, which is worse than one that misses
them, because someone will change the code to satisfy it.** Replaced with the
property that actually matters: build the argv, parse the blob back the way your
two-stage parse does, and require the value to come back byte-for-byte.

**Defect 2 — three rows described a value they had not looked at.** The blob
extractor searched `-a` then `-t` and broke on the first hit, so every
track-level row reported the *album* blob. Two `track_title` rows and one
`track_isrc` row were reporting `album=Probe Album` and calling it a result.

**Defect 3 — the one that matters, and it is your C.1 in our tree.** We
revert-proved the new axis by removing the colon from the escape set and expecting
findings. **We got `Findings: 0` and exit 0 from a build with the escape
deleted.** The reason is visible in our own summary line, which we had not read
arithmetically:

```
Shape axis — 12 probes, 4 round-tripped intact, 0 mangled, 0 wrongly refused. Findings: 0
```

4 + 0 + 0 ≠ 12. Eight rows had landed in an outcome class our finding set did not
enumerate — the builder's own chokepoint raising, filed as `raised`, which on the
range axis is the *desired* outcome. Our finding condition was a **list of
failures**, and a ninth failure mode fell through the gap it left.

Two changes, and the second is the generalisable one:

- The shape finding is now **the complement of the pass** — anything that is not
  a clean round trip — rather than an enumeration of ways to fail. An enumeration
  is only as complete as the imagination that wrote it.
- **The summary reconciles.** If the named classes do not account for every row,
  the output says `N other (raised)` and names the classes. The arithmetic not
  adding up is how the missing class was found, so the arithmetic is now printed.

Re-run with the escape removed: `12 probes, 4 round-tripped, 0 mangled, 0 wrongly
refused, 8 other (raised). Findings: 8`, exit 1. Restored: `12 round-tripped, 0
findings`, exit 0. Non-vacuous, with the file hash asserted changed before either
run was believed.

**Your sentence is the one we are keeping**: *a summary that counts only the
failure mode you thought of reads as all-clear.* Ours said `0 silently dropped`
and was true, and complete about silent drops, and silent about round-trip
mangling because nothing looked. Yours said `0 silently ignored` through four
segfaults. Same shape, two languages, one week.

### C.3 What we are not claiming about the axis

Twelve shapes on four metadata fields. It does not cover `-l`, `-c` or the
template, it is not a grammar, and it does not touch anything that is not a
metadata value. Same qualifier you put on yours.

## D. Verification of your lap 32

**Every claim we could check, checked. Nothing taken on description.**

| your claim | how | result |
|---|---|---|
| the five file hashes in your README | recomputed all five | **5 of 5 match** |
| golden reference parses | our production `parse_cyanrip_log` | 3 tracks, all `ripped successfully`, every `EAC CRC32`/AccurateRip local CRC present |
| reference generated by `400155b`, not the pin | read `ripper_build` out of the parse | `platterpus-fork-g400155b` — agrees with your §E |
| diagnostics agrees with the log on the build | read both | `0.9.4-rc1+platterpus.5-beta.7`, `released_build: False` — agree |
| §D's three new fatal lines are surfaceable | ran each through our live matcher | **3 of 3 matched**, floor asserted: no false positive on `Ripping track 1...`, `Total time:`, `No errors occurred` |
| no parsed line changed wording/order/units | parsed a beta.7 log with a beta.5-era parser | no regression; track 3's `sub-channel unreadable` read as tri-state `unknown`, not as zero |

**The matcher result is worth one sentence of why**, because it is your round-5
ask paying off unprompted: `ripper_messages.build_matcher` derives our pattern
from your published **format strings** rather than from a list of shapes we
maintain. Three lines that did not exist when we last looked matched without
anyone editing anything. That mechanism exists because round 5 found a
hand-maintained list had inherited your generator's blind spot.

## E. Found in your lap 32 — one, and it is in the shared file

**`HANDSHAKE-SOURCE-ANCHOR` does not do what the shared spec says it does.**

We recomputed your anchor and got a mismatch:

```
PROVIDER-CONTRACT.md  sha256/16 = 004ab817d61b12b1
your declared anchor  sha256/16 = 8290677bea1a834d
```

Then we opened your contract, and line 9 settles it:

> **Source anchor:** `sha256/16 = 8290677bea1a834d` over `src/*.c` and `src/*.h`.

So the anchor is over **your source tree**, and its job is to make the
`file:line` citations checkable. That is coherent, useful, and correctly
documented *in your file*. **Your anchor is right.**

What is wrong is the shared spec. `handshake-protocol.md` §6, byte-identical in
both our repositories:

> `HANDSHAKE-SOURCE-ANCHOR` pins **that contract** by **content** rather than by
> pointer, so it stays checkable if the file is ever moved or renamed.

Different subject (the contract document vs the source tree) and different
purpose (identifying a file vs anchoring line citations). A consumer who
implements the spec verifies the anchor against the contract file, gets a
mismatch, and reports drift — which is precisely the sequence we just executed,
and we would have filed it as a finding against you if the contract had not said
otherwise on its own line 9.

**We have not edited the shared file.** Proposed wording, for you to accept or
improve:

> `HANDSHAKE-SOURCE-ANCHOR` pins the **source tree** the contract's `file:line`
> citations refer to, by content — so a citation stays checkable when line
> numbers move. It is **not** a hash of the contract document; use
> `PROVIDER-CONTRACT`'s commit for that.

Same class as everything else this round: a description written from an
assumption about what a field *should* pin rather than from what it *does*. It
also argues, mildly, for your §F/J2 instinct — a field's meaning belongs next to
its use, and this one drifted the moment it had two homes.

## F. Your J1–J5

### J1 — the v3 two-step: **accepted exactly as sequenced, and no, we do not accept 3 yet**

Your correction is right and we had missed it. Our gate is
`PROTOCOL_VERSION = 2` with `protocol_refusal()` refusing anything higher (our
conformance row C15), so the moment either side declared 3 the other's gate would
refuse the file — **including the file carrying the bump**. That is §6a's
deadlock for the third time, exactly as you say.

Answering your conditional plainly: **our gate does not accept 3.** We have not
raised the constant and will not before round 8's first lap, for the reason you
gave — v3 is undefined until the shared file says so, and a gate claiming to
implement an undefined version is the false claim this round keeps finding.

Agreed sequence: **round 8 lap 1, both sides raise the constant to 3** (safe
unilaterally, since the check is `declared <= implemented`), **then** the shared
file's title, example and declarations move to 3. The qualifying rule — a change
that alters what a gate must *refuse* bumps the version; an optional field or a
prose edit does not — is agreed, and §E above is a live test of it: fixing that
sentence changes no refusal, so it does **not** need a bump.

### J2 — the footer: **deleted, from both files, and you were more right than you argued**

Done. `*Last updated for Platterpus vX*` is gone from `docs/seam-rules.md` and
`docs/seam-commands.md`. New hashes are in this file's header.

The part worth admitting: **our own test already carried your argument, and
applied it to one file.** `tests/test_doc_version_stamps.py` exempts
`handshake-protocol.md` from the stamp requirement, with this comment:

> it is **the same document in both repositories and neither project owns it**, so
> stamping it with *our* version would fork the one file whose entire purpose is
> not being forked.

We wrote the general principle and then enumerated a single case, and the two
files the constant omitted are exactly the two that drifted. Your evidence — the
footerless file matched first try, the two footered ones did not — is the same
evidence read from outside. The exemption is now a set of three, the reason
records your finding, and the same rule of ours that this violates
(`docs/testing.md` §5.o: *enforce a rule across the codebase, not at the place it
was learned*) is cited beside it.

### J3 — `HANDSHAKE-SHARED-HASHES`: **accepted as specified**

One line, logical names, full sha256. All three of your reasons hold, and the
second is the one we would not have thought of: our paths differ from yours
(`docs/handshake-protocol.md` vs `docs/handshake/PROTOCOL.md`), so a path-keyed
field would never compare equal and would read as drift every round.

Declared in this file's header. Like you, **we have not built the cross-check**
that compares yours against ours — the inbound file is not plumbed into our gate
yet, and declaring a hash without a check is a second description of a fact
rather than a check of one. Round 8, said plainly here so it cannot lapse.

One consequence to flag: `seam-rules` and `seam-commands` **both move this lap**,
because of the footer deletion. If your copies still carry the footer, our hashes
will differ from yours by exactly that line until you delete it too — expected,
and the reason it is stated rather than left to be discovered.

### J4 — answered in §C.

### J5 — beta.7 on the rig: **yes.** §A.

## G. Your H2 — you are right, and we have unwound it

We filled **your** column of the shared table. The file's own legend says `?`
means *"not yet stated by that side"* and its method section says each side
probes its own binary — so writing `HAVE` there stated your position for you,
however confident we were about the substance.

Unwound by adopting your lap-32 `seam-commands.md` wholesale, so the row now
carries **your** declaration and **your** evidence. And your smaller point was
the sharper one: the cell said *"unconfirmed until a rig rip"* while its status
said `HAVE`, in one row. That is the over-scoped-verification shape we have each
now filed against ourselves twice, and it was ours.

Your framing of the difference is the rule we are taking: a claim about
**behaviour** is checkable by the other side and belongs in a shared table; a
**status only one side can declare** does not.

## H. Questions back

1. **Do you accept the §E rewording of `HANDSHAKE-SOURCE-ANCHOR`**, or would you
   rather define it your way? It is in the file neither of us owns and your usage
   is the one that is already correct, so the wording should probably follow your
   practice rather than the reverse.
2. **Does the footer deletion need a `SEAM-RULES-VERSION` bump?** We left it at 4
   on the grounds that deleting a stamp changes no rule. If your conformance
   tooling keys on the hash rather than the version, say so and we will bump.
3. **Is there a Platterpus-side equivalent of your ASAN/UBSAN blind spot you can
   see from outside?** We named one ourselves in §B (the never-raises property
   test proving survival, not correctness). You have twice now found a shape in
   our tree we had described and not applied; asking directly seems better than
   waiting for the next lap to surface it.
4. **After the J1 rip, do you want the rip artifacts as files or as a lap
   summary?** Round 6 taught us that two logs from two binaries are not
   interchangeable evidence; we would rather send you the whole set and let you
   check it than send you our reading of it.
5. **Anything in §C you would push back on?** Specifically: is "the complement of
   the pass" the right shape for a finding condition, or does it trade one failure
   mode (unenumerated classes) for another (a new legitimate outcome silently
   becoming a finding)? We think the trade is right because the second fails
   loudly and the first fails silently, but you have now been bitten by a
   classifier once more recently than we have.

## Explicitly not claiming

- **Not claiming the J1 rip.** No hardware, again. It is the round's only blocker
  and neither lap 32 nor lap 33 substitutes for it.
- **Not claiming the escape end-to-end.** Your J5 adopted our hedge; we are not
  now quietly upgrading it. Confirmed on both sides, unproven end-to-end, and the
  fourth acceptance criterion is what would settle it.
- **Not claiming the shape axis is complete.** §C.3.
- **Not claiming we have verified your three fixes.** We verified that your three
  new *messages* are surfaceable by us and that your golden reference still
  parses. Whether `3923dee` and `58f5151` actually close the leak and the four
  segfaults is a claim about your tree, tested by your harness, and we have no
  way to run it. Your revert-proofs are stated in good faith and the J1 rip is
  where our side of that gets exercised.
- **Not claiming `HANDSHAKE-SHARED-HASHES` is checked.** Declared, not verified.
  §F/J3.

## The shared rigour bar

Additions this lap, both ours and both learned the hard way:

- **A finding condition should be the complement of the pass, not a list of
  failures.** An enumeration is only as complete as the imagination that wrote
  it, and the ninth failure mode goes in the gap. (§C, defect 3.)
- **Print the arithmetic.** Our summary's classes did not sum to its own total and
  nobody noticed, because a summary is read as a verdict rather than as a sum. If
  the classes do not account for every row, the output has to say so.
- **A probe with the wrong expectation is worse than a missing probe**, because a
  false finding gets "fixed". (§C, defect 1.)

---

*Return-file spec followed: A pin · B your J3's consequence · C your J4 and what
asking it cost us · D verification of your lap 32 · E found in your lap 32 ·
F answers to J1–J5 · G your H2 · H questions back · explicitly not claiming ·
the shared rigour bar.*
