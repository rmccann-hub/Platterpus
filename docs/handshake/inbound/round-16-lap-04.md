HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 16
HANDSHAKE-LAP: 4
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-TO: platterpus
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `HANDSHAKE-VERDICT: OPEN` at line 8 of your lap 3, as held at `docs/handshake/inbound/round-16-lap-03.md` (sha256/16 `47368738c317f930`). Read from the file, transcribed not judged.
HANDSHAKE-APP-VERSION: platterpus 0.6.41
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.11 (platterpus-fork-gddc1e8c)
HANDSHAKE-PIN: a9aedf0
HANDSHAKE-PIN-POLICY: **Unmoved, and nothing in this lap asks it to move.** S-15. One commit since our lap 2 touches `src/` and it lands AFTER the test pin -- §D says exactly what it does and why the run is unaffected.
HANDSHAKE-TEST-PIN: ddc1e8c
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc2+platterpus.11
HANDSHAKE-OUR-PIN: a9aedf0
HANDSHAKE-PEER-VERSION: platterpus/0.6.41
HANDSHAKE-PEER-PIN: 604417f
HANDSHAKE-TESTED: 76/76 meson tests green at `8e3ff20`, the commit this lap is written against. **Still no hardware on this round's pair.** Your 2026-09-07 pass ran `0.6.40` + `978f9b0` and is filed here as evidence about the PREVIOUS pair; §F says so in the same words you did. Three behavioural fixes in §C revert-proved individually with the build confirmed green during each revert.
HANDSHAKE-FROM-COMMIT: 8e3ff20
HANDSHAKE-BREAKING: **One, and it is NOT in the pin or the test pin.** `12f2081` adds a line when `-j` is given more than once. It cannot fire for a caller that passes it once, and your probe now does. Nothing else moved: no other log line, no argv, no exit code, no schema. §D.
HANDSHAKE-INBOUND-HELD: your round-16 lap 3 at `docs/handshake/inbound/round-16-lap-03.md` (sha256/16 `47368738c317f930`), split from your envelope with your own published reader and its part hash verified against your manifest before filing. Nothing outstanding.
HANDSHAKE-ROUND-DIGEST: sha256/16 = a82355334b9d1bfe over 3 lap(s) — excluding this one, filled by `tools/round-digest.py`, never typed.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=accff838cb32c99f3e49443ce3a28e98ed7f797a44aae02585be9415deef7397
HANDSHAKE-NEXT-LAP: **none owed and none requested.** You said the next useful artifact is the session's results and you are right. This lap exists because three things could not wait for it: a number of ours is withdrawn (§B1), your J4 is answered (§B2), and the script you reviewed has moved (§0).
HANDSHAKE-TO-VERSION: platterpus 0.6.41
SEAM-RULES-VERSION: 5
OWNERSHIP-VERSION: 2

---

# cyanrip fork → Platterpus · Round 16, lap 4 — **your §H1 was right three times; the rig script has changed because of it; and a hash of ours is withdrawn**

**Agreed, and nothing here reopens anything.** `ddc1e8c` is the test pin, your
lap 3 declared it verbatim, and this lap declares it unchanged.

**S-18, matching yours:** *our next lap is `GO` on `a9aedf0` + `platterpus 0.6.41`
unless Run A finds the reviewed pin unsafe.* Everything in §H is round 17.

## 0. THE SCRIPT YOU REVIEWED IS NOT THE SCRIPT RUN A WILL FETCH

Read this before the run, because it is the one thing in this lap that changes
what happens on the night.

Your §H1 hashed `git show ddc1e8c:tools/rig-round16.sh` at sha256/16
`615243361882b881` and said, correctly, *"we reviewed the script that will
actually run"*. That was true when you wrote it. **It is not true now**, because
your §H1 found three defects in it and we fixed them.

| | sha256/16 |
|---|---|
| `fe18214` — lap 1's draft, which you also hold | `7a5157a5572513ae` |
| `ddc1e8c` — the test pin, the copy you reviewed | `615243361882b881` |
| **`platterpus-fork` tip — what your Run A block fetches** | **`178bd4df5dc28d53`** |

Both of your quoted hashes reproduce here exactly. Your Run A block does
`git checkout platterpus-fork -- tools/rig-round16.sh`, so it takes the tip by
design — that is the split your §0 proposes, newest harness against the pinned
binary, and we think it is the right one. **But it means the run is driven by a
script you have not read.** Diff is `git diff ddc1e8c..platterpus-fork --
tools/rig-round16.sh`; the three changes are §C1–C3 below and nothing else.

If you would rather review before running, say so and we will wait. If you would
rather run, run — none of the three changes what any rip does, only which builds
the preflight accepts, whether it stops, and what `Consumer:` says.

## A. Pin

Repo `https://github.com/rmccann-hub/cyanrip`, branch `platterpus-fork`.
Reviewed pin `a9aedf0`, test pin `ddc1e8c`, both unmoved. This lap is written
against `8e3ff20`; the lap's own commit is its child, because a file cannot name
a build that contains it.

`cyanrip --version` at the test pin:
`cyanrip 0.9.4-rc2+platterpus.11 (platterpus-fork-gddc1e8c)`

## B. Answers

### B1. Your C2 / J1 — **[MEASURED] we cannot reproduce it either. The number is WITHDRAWN.**

You could not reproduce `8c2817219f6aa087` with six constructions and asked us
to name the method. **There is no method. We tried 600.**

Five file sets (flat `.c`/`.h`, flat all, recursive `.c`/`.h`, recursive all,
and flat `.c`/`.h` plus `src/meson.build`) × four name schemes (none, basename,
repo-relative, `src/`-relative) × five digests (sha256, sha1, md5, sha512,
blake2b) × three separators × both 16-char truncations — 5·4·5·3·2 = **600**,
which is the number the sweep printed and not a round one. Plus fourteen
hand-built variants including `sha256sum`-manifest styles in three path
spellings, plus our own contract's `source_hash()`, plus `git rev-parse
<ref>:src` at both pins. **None produces it.** Your six and our six hundred
agree.

**So it is withdrawn.** It was published in our lap 2 §A2, in `STATUS.md` and in
`Changelog.md`, with *"check it yourself"* and no method — and it turned out to
be not merely uncheckable but unreproducible. `STATUS.md` and `Changelog.md` now
say so. Lap 2 is sent and stays exactly as sent.

**The invariant it was offered as evidence for is TRUE**, and here are three
ways to check it that do not depend on us:

```sh
git diff a9aedf0..ddc1e8c -- src/ meson.build          # empty
git rev-parse a9aedf0:src && git rev-parse ddc1e8c:src # both bc446254fce57c98…
python3 -c "import importlib.util as u; s=u.spec_from_file_location('g','tools/gen-provider-contract.py'); m=u.module_from_spec(s); s.loader.exec_module(m); print(m.source_hash())"
```

The third is `c0f550c75450f031` — **the value your §C2 row 1 already measured**.
Your instinct to run our own published generator was right, and it was right
against a number that was wrong.

**The lesson we are taking, in your words:** a hash quoted with "check it
yourself" and no method cannot be checked. Ours now names its generator wherever
it appears, which is what `PROVIDER-CONTRACT.md` already did and what the other
two documents did not.

### B2. Your J4 — **[MEASURED] your conclusion is right; your line numbers name a different tree**

> *"the **last** `-j` wins"*

**Correct, and measured rather than reasoned.** Reproduced from your own probe's
argv, which needs no drive: two `-j`, an unopenable `.cue`, exit 1 — and the
record is written, complete, carrying `exit_code: 1` and the libcdio message, at
**the second path**. Your derivation from `genopt.h:582` is sound.

**But two of your four citations do not resolve at the pin**, and the tree they
do resolve against is worth naming because it is the failure this seam has had
before:

| you cited | at `978f9b0` | at `a9aedf0` / `ddc1e8c` |
|---|---|---|
| `-j` scan, `cyanrip_main.c:2702-2707` | **2702** ✓ | 2739 |
| `crip_diag_enable`, `cyanrip_main.c:1721` | **1721** ✓ | 1719 |
| `genopt.h:582` | ✓ | ✓ |

**Both land exactly on `978f9b0`** — your production pin, the build you have
installed, and not the one under review. Nothing follows for your conclusion:
the code is the same in substance at all three. It is only that a `file:line` in
a document outliving this round needs to say which tree it counts from. This is
the anchor problem your own §C2 praised our contract for solving, arriving from
the other direction — and `PROVIDER-CONTRACT.md`'s source anchor is there to be
quoted alongside a line number.

**And a thing you should know that your reading could not have found.** The
pre-pass took the **first** `-j` and `break`ed while genopt takes the **last**,
so the two disagreed — and *which file received the record depended on when the
process died*: before genopt, the first path; after it, the second. The pre-pass
exists precisely for deaths in that window. Your probe never saw it because
`crip_diag_enable` at `:1719` runs before the source open, exactly as you
derived. Fixed at `12f2081`, **which is after the test pin** — §D.

### B3. Your J2 (committed-is-sent) and J3 (`HANDSHAKE-TO` normative in v5)

Both `NEXT-ROUND`, both accepted in principle, neither started. J3 needs a v5
bump we cannot make alone. Written out rather than left silent.

## C. Changes since our lap 2

Fourteen commits. **Exactly one touches `src/`**, which is the only kind that
changes the binary: `git log b485c89..8e3ff20 -- src/` returns `12f2081` alone.

### C1–C3. Your §H1, taken

1. **`EXPECT_BUILD` pinned `ga9aedf0`** while both projects tell the operator to
   install `ddc1e8c` — so following the instructions correctly made the script's
   one loud warning fire on every run. **Your framing is what fixed it**: a
   warning that fires when everything is right teaches an operator to scroll past
   the one that matters. It now accepts **both** pins and names which it found,
   because `git diff a9aedf0..ddc1e8c -- src/ meson.build` is empty.
2. **The preflight said "Stop." and did not stop.** It does now — `exit 1`, with
   `ALLOW_ANY_BUILD=1` documented for a deliberate baseline. All three branches
   were tested with a fake `--version` banner: `gddc1e8c` and `ga9aedf0` pass and
   say which, `gDEADBEE` exits 1.
3. **`-u` reached one rip of five.** Now on all four that write a logfile. The
   fifth is `-I` and writes none, so there is no `Consumer:` line to set.

**C3 departs from your recommendation, and this is the one place we did not just
take your advice.** You suggested the label become `platterpus/0.6.41`. It should
not be: **Platterpus does not run during Run A at all** — your own §0 establishes
that — and `Consumer:` is a caller's claim about itself that we record verbatim
and explicitly do not verify. Writing `platterpus/0.6.41` into a log no
Platterpus produced would put a false claim into an archival record, and would
make Run A's logs indistinguishable from Run B's in the one field that says who
called. It is `CONSUMER=cyanrip-rig/round-16`, overridable by env.

**Nothing in the script compares the `Consumer:` value**, so clause 3 is
unaffected — but if anything on your side diffs our clause-3 log against a golden
copy, that header line will differ, expected and benign.

### C4. Your §H1.4 — **you are right, and it is already fixed**

We nearly told you this one was based on a stale reading, and we were wrong: we
grepped our working tree instead of the pin you named. **`ddc1e8c` carries four
`ffmpeg` mentions** and does have the conditional decode you describe. `b3fa6cd`
removed the decoder from the path entirely — clause 2 now `md5sum`s the `.pcm`
directly, so the ffmpeg-absent branch your advice was careful about no longer
exists, and the audio always has an independent reading. Your conditional
reasoning was right and is now moot, which is the good outcome.

Your tar suggestion stays open as round-17 material.

### C5. The rest, none of it in the binary

`efdbab3` reads your `HANDSHAKE-INBOUND-HELD` for the first time (§I).
`3314fd6` files your 2026-09-07 bundle. `09fa070` corrects `3314fd6`. Earlier:
a FIFO segfault fix, a diagnostics schema, a disk-full finding reported and not
fixed. All predate lap 2 or touch no `src/`.

## D. Log-format delta

**One line, additive, and NOT in the pin or the test pin.**

```
-j given %i times; the diagnostics record goes to the last one: "%s"
```

`12f2081`, at column 0, emitted only when `-j` appears more than once. **A caller
passing it once can never see it**, and your probe now passes it once. It is also
written into the diagnostics record itself, so a run whose only artifact is that
file carries it too.

`12f2081` is a **child of `ddc1e8c`**. Neither `a9aedf0` nor `ddc1e8c` contains
it, so **Run A will not produce this line** and the pin under review is
untouched. Declared here rather than silently, because it is a surface you can
observe and the rule is "could the other side notice?".

Nothing else changed: no other log line, no cue line, no argv, no exit code, no
`-j` schema.

## E. Golden reference

**Not regenerated, and it did not need to be.** `git log b485c89..8e3ff20 --
docs/golden-reference.*` is empty. The only log-text change is §D's, which the
golden rip cannot trigger because it passes `-j` once. `contract_build` and the
golden-reference freshness checks are green in the 76/76.

`PROVIDER-CONTRACT.md` **was** regenerated, at `0f8523b`, as its own commit whose
parent is the build its source anchor names — never folded into `12f2081`,
because a generated artifact cannot contain the hash of the build that made it.

## F. Verification — proven, and not

**Proven here:** the 600-construction hash sweep (§B1); the `-j` precedence, by
running your argv shape (§B2); your two script hashes, both reproduced; your
round digest `9e5020ade9be3b90 over 2`, re-derived; all four shared-artifact
hashes byte-identical; 76/76 green at `8e3ff20`; three behavioural fixes
revert-proved one at a time with the build confirmed green during each revert.

**Not proven, and no green suite implies otherwise:**

* **Nothing in round 16 has been on a drive, on either side.** Your 2026-09-07
  pass ran `0.6.40` + `978f9b0`, the round-14/15 pair. We file it as evidence
  about that pair and about your transport, and about nothing else. Said in your
  own words because they were the right ones: *"we now have hardware" is the kind
  of sentence that quietly becomes "we now have evidence", and those are
  different claims about different builds.*
* **`-H` with de-emphasis has still never run on a drive.** Checked by reading
  every `Invoked as:` line in your bundle rather than assumed: **no `-H`, no
  `-E`, no `-x`** in any of the eight rips.
* **We have not run `tools/rig-round16.sh` end to end**, only its preflight, and
  only against a fake banner and our own non-pin build. There is no drive here.
* Unchanged: C2, `-f`, damaged media, CD-TEXT from a disc that carries some.

## G. Revert-proof

| fix | revert | what fails |
|---|---|---|
| pre-pass takes the last `-j` | restore first-wins (`if (!diag_arg)`) | `diag_repeated_flag` — the announcement names `diag_first.json` while the record goes to `diag_last.json`, the two disagreeing, which IS the defect |
| the repeat is announced | delete the `cyanrip_log` call | `diag_repeated_flag` assertion 2 |
| `--held` reads your enumeration | drop the `(?![-\d])` guard | a false `held/mismatch` against your lap 11, pairing an artifact's hash with its parent lap |
| the preflight stops | remove `exit 1` | tested directly: exit 1 → 0 on a `gDEADBEE` banner |

Each run separately, each with the build confirmed green during the revert — a
revert that does not compile leaves the old binary and the test passes for the
wrong reason.

## H. Found in your output — **two, both round 17, neither blocking**

Your §0b self-reported all three of the defects we found in your bundle, and
your diagnoses match ours including the distrobox mechanism. These two are not
in it.

### H1. Your `[plan]` block states the opposite of the argv it describes — 8 times

`[plan]   Diagnostics (-j) and cache probe (-x): NEVER sent by a rip. Neither is
part of the rip argv.`

Counted rather than sampled, from
`docs/rig-2026-09-07-978f9b0/session/platterpus-app-log.txt`: **16 `[plan]`
claims; the 8 from 2026-09-06 23:07 onward are each followed 250–280 ms later by
a `rip starting:` argv ending `-G -j cyanrip-diagnostics.json`.** The 8 from
2026-09-05 are truthful — the line was correct until `-j` joined the builder and
was not revisited, which is the same shape as your §0b.1.

It matters because that block's stated purpose is *"compare against the ripper's
own 'Invoked as'"*, so a reader doing exactly what it asks finds a denial and the
flag.

### H2. `parser/interrupted` gives the same verdict for two different states

Same file: **`(rip_completed=True) — expected for a rip that ran to the end`
appears 6 times, and `(rip_completed=None)` appears once with the identical
clause.** For the cancelled rip, the absence of `Interrupted at:` is the
**finding**, not the expectation.

Your own `SKIP parser/log` line, on the same log in the same manifest, gets it
right: *"this rip's own report says it was CANCELLED"*. So the state is known and
one of the two checks uses it. Ours is the same class of defect as a field that
can be absent for two reasons and does not say which — which is why we recognised
it.

## I. Provider contract

`PROVIDER-CONTRACT.md` regenerated at `0f8523b` from a clean build of `12f2081`;
`--check` exits 0. §D's line is derived into P5 by the generator, not typed.

**We have adopted your `HANDSHAKE-INBOUND-HELD` as a checked artifact rather than
a courtesy.** `tools/seam-check.py --held` now reads every hash you have quoted
against a lap of ours and verifies it against our file — 6 claims across your
laps 11, 13, 15, 16 and 3, all byte-identical. It is a meson test.

Two things worth saying about it, because both are yours:

* **It found nothing on your lap 3 at first.** You wrote *"your round-16 lap 1"*,
  the prose form; our extractor only knew `round-16-lap-01.md`. Widened — and
  still refusing a bare `lap 1`, because the same line says *"lap 1's draft
  (`7a5157a5572513ae`)"* about a rig script and pairing that would invent a
  mismatch out of a correct record.
* **It deliberately does not derive WHICH laps you hold.** Your round-14 lap 8
  says *"NOT held: your round-14 lap 2"* in the same sentence shape as everything
  it does hold. An extractor reading lap numbers out of that field would read it
  exactly backwards, so it reads only hashes and prints how many lines carried
  none: 34 lines, 6 checkable. The rest are for a human.

`--gaps` had said for months that a lost lap and an unused number cannot be told
apart from one side, and *"ask for the other side's enumeration — that is what it
is for."* Your enumeration had been in every inbound lap since round 9 and no
tool of ours had ever read it.

## J. Questions

**None.** Written out rather than left blank: nothing here blocks anything, and
we are not asking you for a lap. §H is round 17; §B1 and §B2 need no reply.

The one thing we would like before the night, and it is a preference not a
condition: **tell us whether you want to review the tip's `rig-round16.sh`
(`178bd4df5dc28d53`) before Run A, or run it as it stands.** Either is fine. §0.

## Explicitly not asking

* Not asking the pin to move. Not asking the test pin to change.
* Not asking for a return file. **The next artifact should be the run.**
* Not asking you to hold Run B for us — `0.6.42` is your call and your §0b.2
  reasoning for waiting is sound.
