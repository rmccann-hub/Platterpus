<!-- ADOPTED VERBATIM from the cyanrip fork, round 7 lap 4. THIS FILE IS SHARED:
     it is the same document in both repositories, and neither project owns it.
     Do not edit it unilaterally — a change here is a protocol version bump, which
     both sides must ship before the next close (§10). Our gate that implements it
     is `scripts/handshake.py`; our conformance tests are
     `tests/test_handshake_conformance.py`, one per §8 row. -->

# Handshake protocol v2

**This file is the shared language. Both projects implement it; neither owns
it.** cyanrip and Platterpus each have a gate that reads round files and decides
whether a release is permitted. Those gates must agree on every field name, every
allowed value, and what a close requires — otherwise one side can believe a round
is closed while the other believes it is open, which is precisely the failure both
gates exist to prevent.

Copy this file into both repositories. When it changes, `HANDSHAKE-PROTOCOL`
increments and **both sides must ship the new version before the next close**.

---

## 1. Where it applies, and where it does not

The protocol governs **the declared header of a round file**. It does not govern
directory layout, filenames, or storage — those are local and the two projects
already differ:

| | cyanrip | Platterpus |
|---|---|---|
| stores rounds in | `docs/handshake/round-N[-lapM].md` | `outbound/`, `inbound/`, `verified/` |
| gate | `tools/release-gate.py` | `scripts/handshake.py` |

**Neither layout is wrong and neither needs to change.** A gate reads whichever
files its own project stores and parses the header below. Do not encode the other
side's layout into your gate; that is a dependency on something it is free to
change.

## 2. Declaration syntax — identical on both sides

Every field is a line of the form:

```
FIELD-NAME: value
```

**Matched line-anchored at column 0.** These properties are normative, not
implementation detail, because a gate that relaxes any of them silently accepts
files the other gate rejects:

1. **Column 0 only.** An indented copy is prose, not a declaration.
   `  HANDSHAKE-VERDICT: GO` **must not** match.
2. **Strip fenced code blocks before matching.** A declaration is a statement the
   file *makes*, not one it *quotes*. Examples, templates and conformance tables
   legitimately contain field lines at column 0 and none of them is a
   declaration. **This was found the hard way**: the lap that introduced this
   very spec documented the close requirements in a ``` block, and the gate read
   the illustrated `HANDSHAKE-PEER-VERSION` as a fact and compiled it into the
   binary. If your gate does not strip fences, it will do the same to this file.
3. **A field appearing twice is ambiguous, and ambiguity is not a close.** Do not
   take the first, do not take the last — refuse.
4. **An absent required field fails closed.** Never treat "missing" as a
   permissive default. That fallback reintroduces the entire defect: under it, a
   round closes by omitting a field.
5. **Prose containing a value is not a declaration of it.** A file whose text
   reads *"this is not a closing GO"* must not close a round.
6. **An unrecognised value is not agreement.** Treat any verdict outside the
   vocabulary below as "not closed", not as an error to skip past.

## 3. Required fields

```
HANDSHAKE-PROTOCOL: 2
HANDSHAKE-ROUND: 7
HANDSHAKE-LAP: 4
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-APP-VERSION: platterpus 0.6.3
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.4 (platterpus-fork-g<sha>)
HANDSHAKE-PIN: <sha>
```

| field | value | notes |
|---|---|---|
| `HANDSHAKE-PROTOCOL` | integer | this spec's version. A gate that reads a **higher** number than it implements must refuse the round rather than guess. |
| `HANDSHAKE-ROUND` | integer | must match the round the file belongs to. A file declaring a different round than it is filed under is a bookkeeping error and refused. |
| `HANDSHAKE-LAP` | integer ≥ 1 | absent means lap 1. **A round's state is its latest lap's verdict** — by declared number, never by filename or mtime. |
| `HANDSHAKE-FROM` | `cyanrip-fork` \| `platterpus` | who wrote it. Makes a crossed pair unambiguous without relying on filename conventions. |
| `HANDSHAKE-VERDICT` | see §4 | this side's position. |
| `HANDSHAKE-APP-VERSION` | `platterpus <semver>` | the consumer build this file's results were produced with. |
| `HANDSHAKE-RIPPER-VERSION` | `cyanrip <version> (<build tag>)` | the ripper banner, **verbatim**, that produced them. |
| `HANDSHAKE-PIN` | short SHA | the commit this file concerns. |

**The two version fields are load-bearing, not bookkeeping.** A round that
approves a pin approves it *for a named consumer version*. Two artifacts from the
same ripper under different app versions are not interchangeable evidence, and a
file reporting a result without saying which **pair** produced it is a
measurement with no provenance.

**Unknown fields are ignored by both parsers**, so either side may add one
without breaking the other. A format that breaks on an extra line is a format
people stop emitting.

**Each lap is a new file. Never edit a file already sent.** A later lap may close
a round *or reopen one* on new evidence; that is why state is the latest lap and
not a conjunction over all of them.

## 4. Verdict vocabulary — closed set

| verdict | meaning | closes? |
|---|---|---|
| `OPEN` | round opened, awaiting the other side | no |
| `HOLD` | mid-round lap; work continues, do not release | no |
| `GO` | this side affirmatively agrees to release | **only with §5** |
| anything else | unrecognised | no |

`GO` is the **only** closing value, and on its own it is still not a close.

## 5. Closing a round is affirmative and two-sided

**A round closes only when all of the following are true.** One side saying `GO`
is a statement about its own tree, not agreement — "they did not object" is never
"they agreed".

```
HANDSHAKE-VERDICT: GO
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-OUR-VERSION: 0.9.4-rc1+platterpus.4
HANDSHAKE-OUR-PIN: <commit sha>
HANDSHAKE-PEER-VERSION: platterpus/0.6.4
HANDSHAKE-PEER-PIN: <commit sha>
HANDSHAKE-TESTED: <what was run, on which pair>
```

| field | why it is required for a close |
|---|---|
| `HANDSHAKE-PEER-VERDICT` | the other half of the agreement, transcribed from the file they actually sent. Not inferred from their silence, their tone, or the absence of objections. |
| `HANDSHAKE-OUR-VERSION` / `HANDSHAKE-PEER-VERSION` | **which two programs agreed.** An agreement that does not name its parties cannot be quoted later. |
| `HANDSHAKE-OUR-PIN` / `HANDSHAKE-PEER-PIN` | commit SHAs. A version string can be reused across builds; a SHA cannot. Pin SHAs, never tags or branch tips. |
| `HANDSHAKE-TESTED` | **no release without testing.** A round that closed with nothing tested is a release nobody checked. Name what ran and on which pair of builds. |

Any one missing → **the round stays open**, and the gate must say *which* field is
absent rather than refusing without a reason.

### The peer verdict is transcribed, not judged

Write down what they declared. If they said `HOLD`, record `HOLD` — do not
translate an encouraging paragraph into a `GO`. If their file is ambiguous, that
is a lap, not a close.

## 6. Optional but recommended

```
PROVIDER-CONTRACT: PROVIDER-CONTRACT.md @ <sha>
HANDSHAKE-SOURCE-ANCHOR: sha256/16 = <hex>
```

A resolvable pointer to the generated interface contract at a specific commit,
so a consumer's machine-readable check has something to resolve rather than
parsing prose. **Do not write "unchanged" unless you have compared** — that
sentence has already been proposed once when the contract had in fact moved.

## 7. Rip-time verification

The header above governs *documents*. It cannot tell anyone, months later,
whether a **particular rip on disk** came from an agreed pair. That needs the
artifact itself to carry it.

cyanrip therefore compiles its round state into the binary and prints two lines
into every logfile:

```
Handshake:      round 7 lap 3 OPEN, verdict HOLD -- NOT a released build
Consumer:       platterpus/0.6.3
                (reported by the caller, not verified by cyanrip)
```

- **`Handshake:`** is *derived*, by `tools/gen-handshake-state.py`, from the same
  round files the gate reads, regenerated by the build whenever one changes. It
  is not a hand-maintained string. A build from a tree with an open round says so
  in every log it writes, permanently.
- **`Consumer:`** is whatever the caller passed to `--consumer` (`-u`), recorded
  verbatim. **cyanrip cannot verify it**, and the line says so rather than
  implying a check happened. Absent the flag it reads
  `not identified (no --consumer given)` — a field that answers the question
  beats a field that is missing and prompts it.

**Platterpus should pass `--consumer <name>/<version>` on every rip.** Together
the two lines let anyone holding only the log answer "which pair produced this,
and had they agreed?" without access to either repository.

Neither line is a quality verdict. They report what was configured and what the
caller claimed, with provenance — the judgement stays downstream.

## 8. Conformance

A gate implementing this spec must refuse a release in every one of these cases.
Both projects should have a test per row; cyanrip's are in
`tests/release_gate.py`.

| case | expected |
|---|---|
| our `GO`, no peer verdict | refuse, naming the missing peer verdict |
| our `GO`, peer `HOLD` | refuse, naming the peer verdict |
| both `GO`, any identity field missing | refuse, naming the field |
| both `GO`, no `HANDSHAKE-TESTED` | refuse |
| verdict field absent entirely | refuse |
| verdict declared twice | refuse as ambiguous |
| verdict indented / inside prose | refuse; the declaration did not match |
| a complete close **illustrated inside a ``` block** | refuse, and do not adopt any of the illustrated values |
| unrecognised verdict | refuse |
| declared round ≠ the round it is filed under | refuse |
| a later lap declaring `HOLD` after an earlier `GO` | refuse — a round can reopen |
| no round files at all | refuse; an empty record is not agreement |
| `HANDSHAKE-PROTOCOL` higher than implemented | refuse rather than guess |
| complete two-sided tested round | **allow** — a gate that can never say yes is a wall, not a gate |

That last row matters as much as the others. Assert it, or a gate that refuses
everything passes every other test in the table.

## 9. Grandfathering

Rounds recorded before this spec existed have no verdict field. They are
exempted **by number**, in a set the gate pins and a test asserts — never by a
rule like "a missing verdict is fine for old rounds", which is the fallback that
lets any new round close by omission.

- cyanrip grandfathers rounds `{5, 6}`.
- Platterpus grandfathers rounds `{1, 2, 3}` for the prose form and `{1..7}` for
  the header form.

**Both sets may shrink, never grow.** Round 7 is grandfathered on both sides for
the wire header, because neither side could comply with a spec being written
during it.

## 10. Changes in v2

Adopted from Platterpus's round-7 lap-3 proposal, which arrived independently and
is better than what v1 had:

- `HANDSHAKE-FROM`, `HANDSHAKE-APP-VERSION`, `HANDSHAKE-RIPPER-VERSION` and
  `HANDSHAKE-PIN` become required. v1 named the *agreeing* versions only in the
  closing fields; v2 names the *producing* pair on every file, so a mid-round lap
  reporting a measurement says which two builds produced it.
- Unknown fields are explicitly ignored rather than merely tolerated.

A v1 gate reading a v2 file refuses, which is correct and is why the number
moved. **Both sides ship v2 before the next close.**

Widening either set is a visible edit to a pinned constant, and it should be
argued for in a round rather than done quietly.
