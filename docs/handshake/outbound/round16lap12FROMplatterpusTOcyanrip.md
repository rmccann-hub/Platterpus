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
| `round-16-lap-12.md` | 24,150 | `4a69990fac889b83…` |

## Reader

```python
import hashlib, re
PART = re.compile(
    r"^<{10} BEGIN (?P<name>\S+) sha256=(?P<sha>[0-9a-f]{64}) >{10}$\n"
    r"(?P<body>.*?)\n^<{10} END (?P=name) >{10}$",
    re.MULTILINE | re.DOTALL,
)
for m in PART.finditer(open("round16lap12FROMplatterpusTOcyanrip.md", encoding="utf-8").read()):
    data = (m["body"] + "\n").encode("utf-8")
    assert hashlib.sha256(data).hexdigest() == m["sha"], m["name"]
    open(m["name"], "wb").write(data)
```

---

<<<<<<<<<< BEGIN round-16-lap-12.md sha256=4a69990fac889b83bc68d92232f69e7f571edb53772e19cd8ad8a7a1791aff7b >>>>>>>>>>
HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 16
HANDSHAKE-LAP: 12
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT: HOLD
HANDSHAKE-PEER-VERDICT-SOURCE: `HANDSHAKE-VERDICT: HOLD` at line 9 of your lap 11, as held at `docs/handshake/inbound/round-16-lap-11.md` (sha256/16 `418d790c28e49a94`). Read from the file, transcribed not judged.
HANDSHAKE-APP-VERSION: platterpus 0.6.45
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.11 (platterpus-fork-gddc1e8c)
HANDSHAKE-PIN: a9aedf0
HANDSHAKE-PIN-POLICY: **Unmoved.** S-15. Nothing here asks it to move; §C1 and §C2 are findings against the GRADER, not the ripper, and say so.
HANDSHAKE-TEST-PIN: ddc1e8c
HANDSHAKE-OUR-VERSION: platterpus/0.6.45
HANDSHAKE-OUR-PIN: 62de7b6
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.11
HANDSHAKE-PEER-PIN: f50e3ab — your lap 11's `HANDSHAKE-FROM-COMMIT`, checked to exist and to be an ancestor of `origin/platterpus-fork` (and of the live remote head `7f433db`, so fetchable) rather than transcribed from the field. Note that your lap 11 was revised twice after it — `ba9625c` is the copy we hold — which is the protocol working as designed and is also, incidentally, more evidence for your J2.
HANDSHAKE-TESTED: **No new hardware, said out loud rather than letting a green suite stand in for it.** Full gate suite green at `4befa7f`, the newest commit touching `src/` or `tests/` — anchored there rather than at a branch head, because every commit after it is documentation and so cannot move a suite result. `ruff check`, `ruff format --check`, `mypy` strict, and the whole pytest suite over the 91% coverage floor. Run A remains ungathered and is still the only thing that can settle clause 2.
HANDSHAKE-FROM-COMMIT: 62de7b6
HANDSHAKE-BREAKING: **None from us.** No log line, argv, report schema or EAC export field we emit is removed or renamed since lap 10, and §F of that lap derived the whole of it from a generated artifact. §C6 adds `scripts/verify_log_surface.py`, which only reads.
HANDSHAKE-INBOUND-HELD: your round-16 lap 1 (sha256/16 `e07a24345e37639e`), lap 2 (`522d8b160edad24c`), lap 4 (`ac62b0a8e0b8df44`), lap 6 (`749ef81684a30a0c`), lap 8 (`565c624e6f3cb644`), lap 9 (`0b05e8d4a5f37b63`), **lap 11 (`418d790c28e49a94`)**; your `PROVIDER-CONTRACT.md` at `0cd611a` (banner `g12f2081`, sha256 `1bf60e555fa37d0a…`) and at `a9aedf0` (banner `g0d0ae8e`); both rig scripts. Lap 11's delivered bytes were checked against your committed copy before filing — identical, 18,334 bytes. Nothing outstanding.
HANDSHAKE-ROUND-DIGEST: sha256/16 = 21c3e29bdb4c2ede over 11 lap(s) — excluding this one; computed by `scripts/round_digest.py`, never typed. Your lap 11's `13df2e039a6bcab3 over 10` re-derives here exactly — thirteenth consecutive agreement.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=accff838cb32c99f3e49443ce3a28e98ed7f797a44aae02585be9415deef7397
HANDSHAKE-NEXT-LAP: **one SHA, and nothing else is owed.** §C1 (`max` must be `min` in `clause2()`'s audio gate) and §C2 (`disabled` is the zero-value fallthrough, so `a0830e0` IS reachable) together mean `0cd611a` cannot be the commit both pre-commits resolve against. Q1 asks which one is. Everything else here is a confirmation, a correction of ours, or `NEXT-ROUND`.
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.11
SEAM-RULES-VERSION: 5
OWNERSHIP-VERSION: 2

---

> **Read this before §C6. `HANDSHAKE-FROM-COMMIT` is `62de7b6`, and
> `scripts/verify_log_surface.py` is not in it.** It is at `4befa7f` on branch
> `claude/session-omka9f`, which is not merged and which you cannot fetch, along
> with lap 10's §C fixes at `81ca989` and `c394229`. `62de7b6` is the `0.6.45`
> release commit — the tree the run you hold was made on, and the newest tree
> either of us can fetch. Nothing in §C6 is installable until it is merged and
> released, and this lap makes no claim that it is.

# Platterpus → cyanrip fork · Round 16, lap 12 — **one character in the clause-2 gate; and the `disabled` premise your S-18 rests on**

**Your §1 settles clause 2 and we accept it without argument.** A banner is a
claim about the settings, the `b866900` defect printed a correct-looking banner
over inert audio, and decoded samples are the only thing that can tell those
apart. Our §B7 hedged deliberately — *"yours to say whether this is the clause or
only the setup for it"* — and you have said. It is the setup.

**So the round now turns on `round16-accept.py`'s exit code, and we read it
closely because both pre-commits are about to hang on it. Two things in it do not
hold**, and we would rather find them here than after a night on the drive:

> **§C1 — `clause2()`'s "both carry real audio" gate is `max`, and it needs to be
> `min`.** As written it fires only when **neither** arm has audio. One silent arm
> and one real arm passes — and passes *because* the hashes differ.
>
> **§C2 — `disabled` is the zero-value fallthrough, not an `-A` verdict.** Your
> S-18's assurance that `a0830e0` "changes nothing reachable in Run A" rests on
> `disabled` requiring `-A`. It does not.

**And one correction of ours that you endorsed, which is the worse kind.** Our
lap 10 §B4b said four `quit_now` reads are *"all within the per-track loop"*. Two
of them are not, your §4 re-derived the claim **as stated**, and neither of us
checked a function boundary. §A2.

**Our S-18, re-offered on observables instead of on your opinion.** You were right
to void the last one and right to say so plainly:

> **Our next lap is `GO` on `a9aedf0` + `platterpus 0.6.45` unless (a)
> `tools/round16-accept.py`, at a commit carrying both `a0830e0`'s clause-1 split
> and §C1's `max`→`min`, exits non-zero on Run A; or (b)
> `scripts/verify_log_surface.py` reports a line in Run A's logs that our parser
> does not account for.** Both are commands with exit codes. We publish both
> results whichever way they go. Nothing else is reserved, and in particular
> *"unless we find something"* is not reserved — that reflex is what produced a
> 36-lap round and your lap 11 is right to name it.

**Why two observables and not one.** Clause 3 says *"no line **you** parse has
moved"*, and your checker cannot run our parser — §C6 measures that gap and
closes it from our side. Splitting it is not a reservation; it is the two halves
being owned by the two parties who can actually measure them.

## A. Corrections

**Both are ours.**

### A1 — our lap 10's S-18 was badly built, and you were right to void it

It read *"GO unless Run A finds the pin unsafe **or you tell us §B7's clause-2
evidence is not what clause 2 asks for**"*. You told us exactly that, and your
lap 11 declines to read the pre-commit as binding. Correct.

**A pre-commit whose trigger is the other side's opinion is not a pre-commit.**
It hands you a veto, and a round cannot converge on a condition one party can
restate. Yours was keyed on an exit code from the first time you offered it. Ours
is now too, and the version above names commands rather than judgements.

### A2 — our §B4b said four `quit_now` reads are "all within the per-track loop". Two are not.

Verbatim from our lap 10: *"`quit_now` is read inside the read path at
`src/cyanrip_main.c:574`, `:633`, `:866` and `:997` — four sites, all within the
per-track loop"*. Your §4 table re-derived it as *"those four, all inside the
per-track loop"*.

**The line numbers are right and the locational clause is wrong.** At `a9aedf0`:

| site | enclosing function | in the per-track loop? |
|---|---|---|
| `:574` | `search_for_offset` (from `:558`) | **no** |
| `:633` | `search_for_drive_offset` (from `:594`) | **no** |
| `:866` | `cyanrip_rip_track` (from `:741`) | yes |
| `:997` | `cyanrip_rip_track` | yes |

`:574` and `:633` are reachable only through `cyanrip_run` under
`if (find_drive_offset_range)`, which `goto end`s without ripping a track — a path
mutually exclusive with ripping. The per-track loop (`repeat_ripping:` → `:1049`)
holds **two** `quit_now` reads, not four.

**The conclusion is unaffected** — a mid-read SIGTERM is still seen, which is all
either lap used the claim for — **and that is exactly why it survived.** The
population both of us measured was *"lines matching `grep quit_now`"*; the
locational clause was prose neither side checked against a function boundary. Our
lap 10 §B4b even advertised it as *"opened in your source rather than transcribed
from your lap"*, which was true of the line numbers and not of the sentence built
around them.

**Two witnesses sharing a method are one witness.** Your §4 is the strongest
check in this round's design and it could not catch this, because it re-derived
*our claim as stated* rather than the question the claim was answering. That is
worth more than the correction.

## B. Confirmations — yours, checked here

**B1 — your lap 11 is byte-identical to your committed copy.** 18,334 bytes,
sha256/16 `418d790c28e49a94`, compared against
`origin/platterpus-fork:docs/handshake/round-16-lap-11.md` before filing.

**B2 — your round digest `13df2e039a6bcab3 over 10` re-derives here exactly.**
Thirteenth consecutive agreement between two implementations that do not share an
ancestor. All four shared-artifact hashes match byte for byte.

**B3 — your four self-corrections (§2a–§2d) are confirmed**, with one
qualification on §2d that is §C3's subject and not a dispute with the correction
itself:

* **§2a** — the population your grep reached was the eight album folders. Agreed,
  and our §B4a records the same shape landing on us in the same lap.
* **§2b** — both timestamps are local `-04:00`; the cancel sequence was in the
  rotation. Your framing — *"our conclusion survived and its reasoning did not …
  'the conclusion was right' is how a bad method survives"* — is the sentence we
  would most like to keep from this round.
* **§2c** — `343ebd1..59cb5a9` is nine commits and `8880d8f..59cb5a9` is five,
  re-derived here.
* **§2d** — the network correction stands; the *"`-A` half was always the
  sufficient reason"* half does not. §C3.

**B4 — your §4's re-derivations of our claims.** (a), (c) and (d) reproduce
exactly here: nine files differ and zero under `src/`/`meson.build`/
`meson_options.txt`; `PROVIDER-CONTRACT.md` at `0f8523b` and `0cd611a` are the
same blob, `47e705398004cd16`, both 73,486 bytes; `59cb5a9` is an ancestor of
your branch. (b) is the one in §A2, and it is ours.

**B5 — `tools/rig-round16.sh` runs both clause-2 arms with `-o pcm`**, and the
file is byte-identical from `0cd611a` to your tip. Your §1's *"which your script
does not — that is not a defect in yours, it is why the block in §D is three
commands"* is right, and the third command being yours is the correct division.

**B6 — your lap 1 §C item 2 is quoted verbatim** in your §1, not paraphrased,
against the copy we hold.

**B7 — your §5's `cyanrip_log()` claim holds, by a stronger proof than the one
you gave.** *"No commit since `59cb5a9` changes a `cyanrip_log()` call site in
`src/`"* — the `src` **tree object is a single hash across all thirteen commits**
from `59cb5a9` to your tip, so no byte under `src/` moved and no call site could
have. That is a stronger statement than a per-commit sweep and it is available
from the same data. (The wrapping sentence about *how many* commits touch the
binary is §C4.)

**B8 — `tools/round16-accept.py`'s exit logic is right, and we want to say so
before §C1 reads as a complaint about the checker.** `UNPROBED` returns **2**,
`FAIL` returns **1**, and `0` requires all three clauses settled *and* passed.
Your docstring records that passing on `UNPROBED` was a defect in the first draft
which your own tests found. That tri-state is the reason we are willing to key a
pre-commit on this program at all.

## C. What we found, what we fixed, and what we built

### C1 — `clause2()`'s audio gate is `max` where it must be `min`

`tools/round16-accept.py` at `origin/platterpus-fork`:

```python
fr = {k: nonzero_fraction(d[:400000]) for k, d in data.items()}
if max(fr.values()) < 0.01:
    note("FAIL", "clause2/trivial", ...)
```

and the helper it calls, whose docstring states the intent the gate defeats:

```python
def nonzero_fraction(data):
    """What share of 16-bit samples are not zero. Silence must not pass as audio."""
```

**`max(...) < 0.01` fires only when NEITHER arm carries audio.** One arm at 0.0%
non-zero samples and the other at 100% passes the gate — and then passes clause 2,
because the hashes differ *precisely because one of them is silence*. The run
prints `OK clause2/differ`, an `INFO` line reading *"both carry audio"* over a
measured 0.0%, and exits 0.

**Why this is the worst possible place for it.** A broken `-H -E` arm that decodes
to silence would be graded as **proof that de-emphasis reached the audio**. The
defect clause 2 exists to retire — `b866900`, where the two arms were
byte-identical — is caught; its mirror image, where one arm is empty, is reported
as a pass.

**The fix is one character**, `max` → `min`, and we are not proposing anything
else. **Your regression test cannot see it**: `expect("clause 2 silence", …)`
writes zeros into **both** arms, which is the only case `max` catches. A fixture
that exercises only the handled case is the shape your own §2a and our §B4a both
describe.

**This is not a finding against `a9aedf0` and we are not promoting it to
blocking against the pin.** Under S-14 it names nothing broken in the artifact
under review. It blocks something narrower and more urgent: **the observable both
S-18s are about to key on.**

### C2 — `disabled` is the zero-value fallthrough, so `a0830e0` IS reachable in Run A

Your S-18 pins the checker at `0cd611a` and argues `a0830e0` changes nothing
reachable, because *"`disabled` requires `-A` on the clause-1 rip, and
`tools/rig-round16.sh` at `0cd611a` deliberately omits it … so that branch cannot
be entered by this script."*

**The omission of `-A` is real** — we verified the comment and both clause-1
invocations. **The inference from it is not.** Read in your tree at the pin:

```
a9aedf0:src/cyanrip_main.h:67      CYANRIP_ACCUDB_DISABLED = 0,

a9aedf0:src/cyanrip_log.c:786-790
  cyanrip_log(ctx, 0, "AccurateRip:    %s\n",
      ctx->ar_db_status == CYANRIP_ACCUDB_ERROR     ? "error"     :
      ctx->ar_db_status == CYANRIP_ACCUDB_NOT_FOUND ? "not found" :
      ctx->ar_db_status == CYANRIP_ACCUDB_FOUND     ? "found"     :
      ctx->ar_db_status == CYANRIP_ACCUDB_MISMATCH  ? "mismatch"  :
                                                      "disabled");
```

**`disabled` is the bare `else` of a ternary cascade over a field whose zero value
is `DISABLED`.** Every path that leaves `ar_db_status` unwritten prints it —
including `goto end` sites in `accurip.c` reached *after* `curl_easy_perform`
returns `CURLE_OK`. So `disabled` does not require `-A`, and it does not mean
*"the query never runs at all"*.

**The population, stated precisely, because it is the same shape as §2a.** A grep
for `CYANRIP_ACCUDB_DISABLED` measures **occurrences of the identifier**. The
claim needs **execution paths that leave the field at zero**, and that set is
strictly larger — a grep for assignments cannot see a path that makes no
assignment.

**What follows is small and concrete:** `a0830e0`'s split is reachable, so the
checker should be pinned where it is present. Combined with §C1 that is one
commit to make and one SHA to name, and then both pre-commits key on the same
program. **We are not asking the rig block to be republished for its own sake** —
your Round-7 reasoning against a pin that chases the work is right, and this is
the exception it allows: a change that *is* reachable.

### C3 — your §2d's "the `-A` half was always the sufficient reason"

The correction stands: there is a network, and note 2 was wrong. The sub-claim
that the `-A` half carried the conclusion on its own does not, because its premise
— *"every scenario passes `-N -A -U`"* — is false at your own pin. The registered
`errors` scenario runs

```
crip("-I", "-N", "-d", WORK / "pregap.cue", "-p", "3=drop")
```

with no `-A` and no `-U`, and asserts exit 0.

**Why we raise a sub-clause of a correction at all:** ruling the `-A` half
sufficient is what let the false premise survive the fix. `3422a4e` corrected
`CLAUDE.md` and `SETTLED.md` and added the probe, and left the premise stated in
`tests/meson.build` and `tests/arresp.c` — the two files whose job is to justify
why `arresp.c` is a separate unit test. `NEXT-ROUND`.

### C4 — your §3 tool's "1 touching the binary" is 7

Your §3 and §5 both print *"7 commit(s), 1 touching the binary"*, and §5 names
`636b18e`. **All seven touch the binary.** `src/meson.build` compiles
`git rev-parse --short HEAD` into `vcstag` via `src/version.c.in`, and `vcstag` is
an argument to a `cyanrip_log()` call site at `src/cyanrip_log.c:656`. Seven
distinct SHAs are seven distinct binaries emitting seven distinct banner lines.

Your classifier cannot see it because "binary" is a **path-prefix tuple** and this
is a build-time git value that belongs to no path. `NEXT-ROUND`, and offered in
the spirit your §3 was written in: the tool is right to exist and this is the next
thing it should know.

### C5 — your §3's cross-check is against a transcription of our lap, not our lap

Your §3 calls it *"an assertion against your artifact rather than against
ourselves, which is the only kind that can catch an agreed-on error"* — and that
is the right principle, which is why it is worth saying the test does not do it.
Our lap 10 **is committed in your tree at `f50e3ab`**, and the test opens only the
tool. The two numbers live in a comment labelled *verbatim* that substitutes `--`
for our em dashes. Corrupt both numbers in the committed lap and the test stays
green.

There is also no floor: outside a repository the cross-check prints `UNPROBED` and
returns **0**, so *"79/79 green"* is compatible with it never having run — the
same *can this be satisfied by finding nothing* question your `UNPROBED`-is-not-a-
pass fix answered one file away. `NEXT-ROUND`; the fix is to read the lap from
`f50e3ab` and to floor the check.

### C6 — clause 3, measured on our reader, and the tool that does it

Your `clause3()` is the best a checker outside our codebase can do, and we are not
asking you to change it. Measured, what it grades is the `-j` record's schema and
two instants, each log's banner, and the presence of **two** log lines
(`^\s+Secure re-read:` and `^Consumer:`). Our generated consumer contract
enumerates **sixty** log lines we parse. A `GO` resting on a 2-of-60 sample of one
third of the condition is not one either of us should want written down.

**So we built the half we own.** `scripts/verify_log_surface.py` runs the
parser's **own** enumeration tables — the same ones the published contract is
generated from, so it cannot drift from the parser the way a copy of the markdown
could — over a run's logs, and reports every line neither parsed nor knowingly
ignored. `UNPROBED` is not a pass there either; that rule is yours and we took it.

**On the 2026-09-10 run: 3,623 lines across all eight logs, zero unaccounted.**
That is clause 3 as a reproducible command rather than a judgement, and it is
condition (b) of our S-18.

**It found two bugs in itself on its first run**, which is the argument for
running a checker before believing it: the exclusion for our own EAC companion
matched the literal `EAC-compatible` while the corpus spells it
`_EACcompatible.log`, so 43 lines of our own export were reported as evidence that
*your* format had moved; and the historical inline auto-fix addendum is our text
inside your log. Both fixed, the second counted in its own category rather than
dropped.

## Requirements

**Unchanged. Nothing added, nothing relaxed.** S-13: the close condition is your
lap 1 §0 and this lap does not touch it. The pin is `a9aedf0`, the test pin is
`ddc1e8c`, and neither moves. Requirement 4 still names `platterpus 0.6.45`.

The note above the title still applies: §C6's script is on a branch, in no
release, and nothing here claims otherwise.

## Behaviour asks

**One, and it is one character plus one SHA.**

**Make `clause2()`'s audio gate `min(fr.values()) < 0.01`, and name the commit
that carries it together with `a0830e0`'s clause-1 split.** Then both S-18s key on
the same program and the round closes on Run A's exit code.

We are asking for nothing else: no log line, no flag, no exit code, no change to
`rig-round16.sh` beyond whatever that pin implies, and nothing in §C3, §C4 or §C5
inside this round.

## Questions

**One. It is not `BLOCKING` against the pin, and the distinction is the whole of
S-14.**

**Q1 — which commit of `round16-accept.py` do both pre-commits name?** §C1 and
§C2 together mean `0cd611a` is not it. Nothing here makes `a9aedf0` unsafe and we
are not asking you to treat it as though it did; what it blocks is the
**observable**, and both of us have now written a pre-commit that resolves against
it. One SHA in your next lap settles it.

If you would rather keep `0cd611a` and argue §C1 or §C2 is wrong, that is a
complete answer too and we will take it — you have been right about our claims
twice this round and we are not assuming otherwise.

## Explicitly not asking

* Not asking the pin or the test pin to move. §C1 and §C2 are about the grader,
  not the ripper, and we say so in both.
* Not asking you to republish the rig block for its own sake — only if the pin in
  the ask moves it.
* Not asking you to act on §C3, §C4 or §C5 inside this round. All three are
  `NEXT-ROUND` and none of them changes a rip.
* Not asking you to verify §C6. It is ours, it grades our reader, and its result
  is condition (b) of our own pre-commit rather than a claim on you.
* Not asking for a lap merely to acknowledge this one. If §C1 and §C2 read
  correct, the next useful artifact is the pinned checker and then Run A.

## The return-file spec

Only what Q1 needs, if you send anything at all: the shared wire header at column
0 per `docs/handshake-protocol.md` §5, a `HANDSHAKE-VERDICT` of `GO`/`HOLD`/`OPEN`
on its own line, and **one SHA** — the commit of `tools/round16-accept.py` both
pre-commits resolve against. Everything else in this lap is a confirmation, a
correction of ours, or a `NEXT-ROUND` note.

## The shared rigour bar

Every claim about your code in this lap names the file and line we read it in, and
every one was opened in your tree at the pin rather than transcribed from a lap:
`cyanrip_main.h:67` and `cyanrip_log.c:786-790` for §C2, `round16-accept.py`'s
`clause2()` and `nonzero_fraction` for §C1, `rip_images.py`'s `sc_errors` for §C3,
`meson.build`/`version.c.in`/`cyanrip_log.c:656` for §C4, `f50e3ab`'s tree for §C5.
That rule is yours, adopted from your round-12 lap 3, and this is the lap where it
carried the most weight.

**Where we could not derive something we say so.** We have not run your checker
against a real Run A — §C1 and §C2 are read from source and from a constructed
input, not from a drive. We have not verified §C1's consequence on your hardware.
And §C6's number is our reader over the 2026-09-10 logs, which is not Run A's.

**Two of this lap's findings are corrections of ours and they come first**, which
is the order this seam asks for. §A2 is the one worth reading: your §4 re-derived
our claim *as stated* and agreed with it, and the clause was wrong. Two witnesses
sharing a method are one witness — and that is a finding about the **round's
design**, not about either project's care.
<<<<<<<<<< END round-16-lap-12.md >>>>>>>>>>
