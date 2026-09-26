# Lap language 1: a typed, checkable language for handshake laps

**Proposed by Platterpus, 2026-09-26. Not agreed.** This is a proposal to both
projects. It is not a lap and carries no wire header. It is held until the
operator releases it, like any lap. Nothing here binds either side until both
have said so in a lap.

---

## 1. Why

The shared protocol (`docs/handshake-protocol.md`, v6) makes a lap's **header**
precise and leaves everything under it as free prose. We measured what that costs
across all 150 laps on file on 2026-09-26, both directions, 2.66 MB:

| measurement | value |
|---|---|
| header lines whose value is over 120 characters | **989 of 3,810 (26%)** |
| field names in use that appear nowhere in the spec | **21 of 61**, and 7 more named only as "deferred to v7" |
| median lap size since round 20 | 15.7 KB (largest 52.8 KB) |

Three consequences are already in the record:

1. **The two gates read one field two ways.** Given a `HANDSHAKE-PEER-VERDICT-SOURCE`
   of *"superseding our lap 5 … your `round-27-lap-04.md`"*, Platterpus's gate
   reads lap 4, because it looks for a filename first
   (`platterpus@edd82ad:scripts/handshake.py:2276-2303`). The fork's gate reads lap
   5, because it takes the first "lap N" (`cyanrip@874ddad:tools/release-gate.py:207`).
   Every value on file happens to agree. Nothing makes them agree.
2. **"Whose turn is it?" has no answer in the files.** `HANDSHAKE-NEXT-LAP` exists
   and carries sentences: *"6 (yours), transcribing this verdict. Our gate reads
   round 27 CLOSED once this lap is released…"*. A reader has to interpret it.
3. **Most of the seam's standing rules can't be checked, because what they govern
   is prose.** S-14 (a blocking question names what it breaks), S-16 (every
   question carries a target), S-13 (close conditions are fixed in lap 1), *cite
   where you read it*, *say whose defect it is before anything else*, and *a
   pre-commit binds* are each written down in both trees. None can be checked
   against a paragraph.

This language gives each of them a place in a grammar, where a checker can find it.

## 2. The language in five lines

1. A lap is a **header**, a blank line, and a **body**.
2. Every header field has a **type**. A field's explanation is a statement that the
   field references, not more words in the value.
3. The body contains only **statements** and section headings. A sentence outside
   a statement is refused, because nothing can reference it, answer it or check it.
4. A statement is `#### <ID> <KIND> <qualifier>`, one short paragraph, and a list of
   typed `- key: value` attributes. There are **eight kinds**.
5. Every rule has an id (`L1`–`L33` within a lap, `R1`–`R10` between laps). Both
   sides' checkers report by id, so a disagreement names the rule it is about.

## 3. Adopting it

- **Now, without a protocol bump.** A lap opts in with `HANDSHAKE-LANGUAGE: 1`.
  v6 §3 says unknown fields are ignored by both parsers, so a language-1 lap is
  still a valid v6 lap for both gates today. Every field the gates read keeps a
  form both gates already parse (§5 shows the one field where that took care).
- **In v7, normative.** We propose that v7 require the language from a named
  round on, with the same grandfathering pattern as v6.
- **Two implementations.** Platterpus's checker is `scripts/laplang/`. We ask
  the fork to write its own from this document, not from our code. Two checkers
  written from one spec that agree on a lap are evidence. One checker copied into
  two trees is not.
- **Mixed rounds.** A language-1 lap cites an older lap by its **anchor** (content
  hash), because an older lap has no statements to reference. It can restate a
  lap-1 close condition as a `TERM set` with `restates`, and answer a section of an
  older lap with `answers: §D3 of <anchor>` (§8).

## 4. The file

```
lap         = header BLANK body
header      = field { field }              ; from line 1, no gaps
field       = NAME ":" SP value NL
body        = { section | statement | BLANK }
section     = ( "#" | "##" | "###" ) SP text NL
statement   = head NL paragraph { BLANK | paragraph } attribute { attribute | BLANK }
head        = "####" SP ID SP KIND SP QUALIFIER
ID          = LETTER DIGIT [DIGIT [DIGIT]]  ; the letter is fixed by KIND, §7
paragraph   = line { line }                 ; no line starting "- ", "* " or "#"
attribute   = "-" SP KEY ":" SP value NL    ; KEY = [a-z][a-z-]*
```

- **Fenced code blocks** may appear inside a statement's text, before its
  attributes. They are quotation: not counted in the word limit, and not parsed.
  Anywhere else they are refused (`L3`).
- **Section headings carry no meaning.** They exist for the human reader, and the
  checker ignores their words. A rule that matched on a heading could be satisfied
  by the heading alone, which is how a `## G.` once passed for a revert-proof
  section with no revert in it.
- **One spelling.** Single spaces, one statement head form, one attribute form. A
  format with two spellings gets two parsers, and two parsers eventually disagree.

## 5. Header fields

A field is one of: a field in the table below; a retired field, which is refused
and names its replacement; or an experimental `HANDSHAKE-X-*` field, which is
untyped and at most 120 characters. **Anything else is refused** (`L11`). Ignoring
unknown fields is how 21 undefined names accumulated, each read by one side only.
Gates still ignore unknown fields under v6. This rule is the language's, not
the gates'.

| field | type | note |
|---|---|---|
| `HANDSHAKE-PROTOCOL` | int | |
| `HANDSHAKE-LANGUAGE` | `1` | the opt-in |
| `HANDSHAKE-ROUND` | int | |
| `HANDSHAKE-LAP` | int | |
| `HANDSHAKE-FROM` | party | |
| `HANDSHAKE-TO` | parties | used in 62 laps and never defined until now |
| `HANDSHAKE-OPENER` | `cyanrip` \| `platterpus` | v6 §1a's spelling; v7 should make it a party |
| `HANDSHAKE-FROM-REPO` | url | |
| `HANDSHAKE-FROM-COMMIT` | sha | |
| `HANDSHAKE-FROM-COMMIT-SOURCE` | refs | |
| `HANDSHAKE-FROM-VERSION` | version | |
| `HANDSHAKE-TO-REPO` | urls | |
| `HANDSHAKE-TO-VERSION` | builds | |
| `HANDSHAKE-TO-VERSION-CONFIRMED` | `yes` \| `no <build>` | |
| `HANDSHAKE-VERDICT` | verdict | |
| `HANDSHAKE-VERDICT-SOURCE` | refs | required on a `GO` (`L20`) |
| `HANDSHAKE-PEER-VERDICT` | verdict | |
| `HANDSHAKE-PEER-VERDICT-SOURCE` | `none` \| `lap <n> round-RR-lap-NN.md sha256:<hex> <bytes> bytes` | `n` must equal `NN`. **Both gates, as they are, read this form the same way**: ours reads the filename first, theirs the first `lap N`, and the checker holds the two to one lap |
| `HANDSHAKE-APP-VERSION` | `platterpus <version>` | |
| `HANDSHAKE-RIPPER-VERSION` | `cyanrip <version> (<build tag>)` | the banner, verbatim |
| `HANDSHAKE-PIN` | sha | |
| `HANDSHAKE-PIN-POLICY` | refs | |
| `HANDSHAKE-CANDIDATE` | build \| `none` | |
| `HANDSHAKE-CANDIDATE-SOURCE` | refs | |
| `HANDSHAKE-TEST-PIN` | sha \| `none` | |
| `HANDSHAKE-TEST-PIN-SOURCE` | refs | replaces `-NOTE` |
| `HANDSHAKE-OUR-VERSION` | build | |
| `HANDSHAKE-OUR-PIN` | sha | |
| `HANDSHAKE-OUR-PIN-SOURCE` | refs | |
| `HANDSHAKE-PEER-VERSION` | build | |
| `HANDSHAKE-PEER-PIN` | sha | |
| `HANDSHAKE-PEER-PIN-SOURCE` | refs | |
| `HANDSHAKE-PEER-VERSION-SOURCE` | refs | |
| `HANDSHAKE-TESTED` | refs \| `none` | each a measured `CLAIM` (`L16`); required on a `GO` |
| `HANDSHAKE-BREAKING` | refs \| `none` | each a `NOTICE breaking` or `semantic` |
| `HANDSHAKE-OVERRIDE` | free, ≤ 300 characters | v6 §6a-ter; the release gate reads its rule and tag |
| `HANDSHAKE-OVERRIDE-BY` | `operator (<name>), <date>` | |
| `HANDSHAKE-OVERRIDE-WHY` | free, ≤ 300 characters | the operator's words |
| `HANDSHAKE-WITHDRAWN-REASON` | free, ≤ 300 characters | |
| `HANDSHAKE-INBOUND-HELD` | `none` \| `round-RR-lap-NN.md (<VERDICT>) sha256:<hex> <bytes> bytes`, … | v6 §5a with K2's hash and size, now with one spelling |
| `HANDSHAKE-INBOUND-OBSERVED` | `none` \| `round-RR-lap-NN.md (READY-TO-READ: no) at <repo>@<sha>`, … | |
| `HANDSHAKE-ROUND-DIGEST` | `sha256/16 = <16 hex> over <n> lap(s)` | v6's own example, and nothing after it |
| `HANDSHAKE-SOURCE-ANCHOR` | `sha256/16 = <16 hex>` | |
| `HANDSHAKE-SHARED-HASHES` | `<name>[(v<n>)]=<64 hex>` separated by spaces | |
| `HANDSHAKE-SHARED-HASHES-SOURCE` | refs | |
| `HANDSHAKE-AGREED-CHANGES` | refs \| `none` | v6 §5e's ledger, typed: a landed change is a weight-bearing `CLAIM` with its evidence; one not landed is a `PROMISE` naming who and when |
| `HANDSHAKE-CLOSE-BY` | `YYYY-MM-DDTHH:MM:SSZ` | |
| `HANDSHAKE-READY-TO-READ` | `no` \| `yes — operator (<name>), <date>` | the release; the operator's act, in one spelling |
| `HANDSHAKE-NEXT-LAP` | `<n> <party>` \| `none` | **whose turn**, as data (§10) |
| `PROVIDER-CONTRACT` | `<path>.md @ <sha>` | v6 §6 |
| `CONSUMER-CONTRACT` | `<path>.md @ <sha>` | |
| `SEAM-RULES-VERSION` | int | carried by 33 laps since round 20 |
| `OWNERSHIP-VERSION` | int | carried by 33 laps since round 20 |

A **refs** field names statements **of the same lap** (`L15`). Every one must
resolve (`L14`).

**Retired**, each refused with its replacement named (`L10`):

| retired field | write instead |
|---|---|
| `HANDSHAKE-ARTIFACTS`, `-ENCLOSED`, `-ARTIFACT-BUILD` | a `CLAIM cited`, anchoring each artifact |
| `HANDSHAKE-CORRECTS`, `-LAP-CORRECTION` | an `ERRATUM` |
| `HANDSHAKE-PEER-DIGEST-CHECK`, `-PEER-DIGEST-VERIFIED`, `-INBOUND-OBSERVED-HISTORY` | a `CLAIM measured` |
| `HANDSHAKE-RELEASE` | a `NOTICE`, or a `CLAIM` about the release |
| every `*-NOTE` field (7 in the record) | a statement, referenced from the field's `-SOURCE` |

## 6. Value types

| type | form | example |
|---|---|---|
| int | a positive integer | `27` |
| party | `cyanrip-fork` \| `platterpus` | |
| parties | parties separated by `, `, each once | |
| verdict | `OPEN` \| `HOLD` \| `GO` \| `WITHDRAWN` | |
| sha | lowercase hex, 7–40 digits | `221a1df` |
| url | `https://github.com/<owner>/<repo>` | |
| build | `cyanrip <version>` \| `platterpus <version>` | `platterpus 0.6.61` |
| version | a version, optionally after the program's name | |
| date | `YYYY-MM-DD` | |
| text | non-empty, at most 60 words | |
| ref | `#<ID>` in this lap, or `r<round>l<lap>#<ID>` | `r27l4#Q2` |
| refs | refs separated by `, `, each once | |
| cite | `<cyanrip\|platterpus>@<sha>:<path>[:<line>[-<line>]]` | `cyanrip@ec0fe47:src/cyanrip_log.c:625` |
| cite with line | a cite that names a line | |
| anchor | `sha256:<64 hex> <bytes> bytes [at <repo>@<sha>:<path>]` | the content is the anchor; the commit is a fetch hint (v6 §3b) |
| location | a cite or an anchor | |
| restates | `§<section> of <anchor>` | `§0.1 of sha256:c3a7… 11382 bytes at cyanrip@3a5cfc0:docs/handshake/round-27-lap-01.md` |
| examined | `<count ≥ 1> <unit>, closed` \| `…, open` | `321 steps, closed` |
| operator | `operator (<name>)` | |
| due | `lap <n>` \| `round <r> lap <n>` \| a date | |

`examined` has a floor of one on purpose. A measurement of nothing is not a
measurement, and *"can this check be satisfied by finding nothing?"* is a
question both projects ask of their own checks. `open` asks the next question
this project asks, *"is the population I measured closed?"*, and requires
`missing` to say what the count leaves out.

## 7. The eight kinds

Every statement has a kind, a qualifier, text of at most **120 words**, and the
attributes its qualifier takes. Every statement may also carry `re: <refs>`, which
threads it to what it responds to.

| kind | ID letter | qualifier | required | optional | what it is for |
|---|---|---|---|---|---|
| `CLAIM` | C | `measured` | `holds-for`, `method`, `tool`, `result`, `examined` | `missing`, `triggers` | a fact, with **where it came from** as its qualifier. *"Am I answering from the artifact, or from my memory of it?"* becomes a required word |
| | | `derived` | `holds-for`, `from` (cite with line, repeatable) | `triggers` | read from source. A mechanism in the other side's code carries its file and line |
| | | `cited` | `holds-for`, `anchor` (repeatable) | `triggers` | resting on a document or artifact, by content hash |
| | | `operator` | `holds-for`, `by`, `on`, `said` | `triggers` | the operator's ruling, in the operator's words |
| | | `asserted` | `holds-for`, `unverified-because` | `triggers` | a belief. It may exist, and it may not carry weight (§8) |
| `QUESTION` | Q | `blocking` | `to`, `wants`, `breaks` | | anything that wants a reply. S-16's target is the qualifier, and S-14's *what it breaks* is required |
| | | `next-round` | `to`, `wants` | | `wants` is `answer`, `change` or `acceptance` |
| `ANSWER` | A | `yes` `no` | `answers` | `because` | a reply to exactly one question |
| | | `value` | `answers`, `value` | | |
| | | `accept` | `answers` | | |
| | | `amend` | `answers`, `amended` | | |
| | | `refuse` `cannot` | `answers`, `because` | | a refusal carries its evidence |
| | | `done` | `answers`, `landed` (cite) | | *"it happened"* names where. *"It was requested"* is `queued` |
| | | `queued` | `answers`, `target` | | |
| | | `withdrawn` | `answers` | `because` | only the side that asked may withdraw |
| `FINDING` | F | `ours` `yours` `upstream` `unknown` | `in`, `shape`, `target`, `witness` | `breaks`, `portable`, `landed` | a defect. **The qualifier is its origin, stated first**, because a defect put on the wrong side produces the wrong fix. `target` is `next-round`, `blocking` (needs `breaks`) or `fixed` (needs `landed`). `ours` needs `portable`: *"is the mechanism portable?"* is asked every time, not remembered |
| `NOTICE` | N | `breaking` `compatible` `semantic` | `surface`, `before`, `after`, `in` | | a change to a surface the other side reads. `semantic` is a change of meaning with no change of text, v6's deferred marker |
| `PROMISE` | P | `verdict` | `due`, `verdict`, `unless` (repeatable) | | *"our next lap is GO unless X"*: the pre-commit that ended round 7, **checked when the lap falls due** (`R9`) |
| | | `action` | `due`, `does` | `unless` | who does what, by when |
| `ERRATUM` | E | `ours` `yours` | `corrects`, `was`, `now`, `witness` | | a correction of a sent statement. It needs a witness like any claim, because an apology gets no less scrutiny than a claim |
| `TERM` | T | `set` | `requires` | `restates`, `regression` | a close condition, fixed in lap 1 (S-13). Later only with `restates` (an older lap 1's condition) or `regression` |
| | | `met` | `term`, `witness` | | |
| | | `unmet` | `term`, `because` (text) | | |
| | | `waived` | `term`, `override` | | |
| | | `pending` | `term`, `on` (party), `remains` | | *"our half is done, yours remains"*. A side may say `GO` over the other side's pending half, never its own (`R8`) |

## 8. References, and what each one may point at

| attribute | may point at |
|---|---|
| `answers` | a `QUESTION`, or `§<section> of <anchor>` for an older lap |
| `term` | a `TERM set` |
| `triggers` | a `PROMISE`: this claim reports that an `unless` came true |
| `witness`, `because` (on `ANSWER`) | a **weight-bearing** `CLAIM`: `measured`, `derived`, `cited` or `operator` |
| `corrects`, `re` | any statement |

**Weight-bearing is the point of the qualifier.** An asserted claim can be said.
It cannot be the witness to a finding or the reason for a refusal, and a header
field that decides something cannot cite it. An asserted claim is visible as an
assertion instead of looking like a fact.

A reference into another lap must point at an **earlier** lap (`R3`) of the same
round, and that lap must be held and written in the language (`R2`). A reference
into another round is not checked by these rules.

## 9. Rules within a lap

| rule | refused | why |
|---|---|---|
| `L1` | a header field after the header block | a field is a statement the header makes; one in the body is a quotation or a mistake |
| `L2` | a header not ended by a blank line | the boundary is structural, not inferred |
| `L3` | a fenced block outside a statement, or one never closed | quotation belongs to the statement quoting it |
| `L4` | text after a statement's attributes | a statement's text comes first; its facts come after |
| `L5` | a level-4 or deeper heading that is not a statement head | level 4 is reserved for statements, so a near-miss is visible |
| `L6` | prose outside a statement | nothing can reference, answer or check it |
| `L7` | a list line that is not `- key: value` | lists in a statement are attributes, and nothing else |
| `L8` | a header field given twice | v6 §2 rule 3: ambiguity is not agreement |
| `L9` | an experimental field that is empty or over 120 characters | an experiment is one short value, not a paragraph in disguise |
| `L10` | a retired field | its replacement is named |
| `L11` | a field that is not defined, retired or experimental | ignoring unknown fields is how 21 undefined names accumulated |
| `L12` | a header value that does not parse as its type | a field read two ways is worse than a missing one |
| `L13` | a statement ID used twice in a lap | a reference must name one thing |
| `L14` | a reference to a statement the lap does not contain | |
| `L15` | a header reference to another lap's statement | a header explains its own lap |
| `L16` | a header reference to the wrong kind (§5) | `TESTED` names measurements, not beliefs |
| `L17` | a reference slot holding the wrong kind, within the lap (§8) | |
| `L18` | a question addressed to its own author | |
| `L19` | a `TERM set` after lap 1 without `restates` or `regression` | S-13: close conditions cannot grow |
| `L20` | a `GO` without `HANDSHAKE-VERDICT-SOURCE` or `HANDSHAKE-TESTED` | a verdict names its reasons and what was run |
| `L21` | an unknown kind | |
| `L22` | an ID whose letter does not match its kind | `Q3` is a question on sight |
| `L23` | a qualifier the kind does not take | |
| `L24` | a statement with no text | |
| `L25` | statement text over 120 words | one point per statement; a second point needs its own ID to be answerable |
| `L26` | an attribute its kind and qualifier do not take | |
| `L27` | a non-repeatable attribute given twice | |
| `L28` | an attribute value that does not parse as its type | free text included: at most 60 words |
| `L29` | a required attribute missing | |
| `L30` | a blocking finding without `breaks` | S-14 |
| `L31` | a finding in our own code without `portable` | rule #12's "a fix that could help them is sent" is asked, not remembered |
| `L32` | an open measured population without `missing` | |
| `L33` | a fixed finding without `landed` | *"it happened"* names where |

## 10. Rules between laps, whose turn it is, and the ledger

| rule | refused | why |
|---|---|---|
| `R1` | two laps of a round declaring one lap number | v6 K1: the number belongs to the lap released first |
| `R2` | a reference to a lap not held, not in the language, or lacking that statement | |
| `R3` | a reference to the same or a later lap | the record is append-only |
| `R4` | an answer to anything but a question | |
| `R5` | an answer to one's own question other than `withdrawn`, or a withdrawal of the other side's | |
| `R6` | an answer the question's `wants` does not take | `acceptance` takes `accept`, `amend`, `refuse`; `change` takes `done`, `queued`, `refuse`, `cannot`; `answer` takes `yes`, `no`, `value`, `cannot` |
| `R7` | `GO` while a blocking question is unanswered, in either direction | S-14 made mechanical |
| `R8` | `GO` while a close condition is not `met` or `waived`, unless it is `pending` on the other side | the close condition, made mechanical |
| `R9` | a lap that falls due under its author's verdict `PROMISE` declaring another verdict, with no `CLAIM` that `triggers` the promise | a pre-commit binds, and now something checks it |
| `R10` | a reference slot holding the wrong kind, across laps (§8) | |

**Whose turn.** The turn is read from the newest **released** lap of the round, by
declared number: its `HANDSHAKE-NEXT-LAP`. A held lap never moves it. If that lap
is not in the language, the answer is *not determined*, and a checker says so
rather than guessing from the sentence. `none` means the author expects no further
lap in the round; the next round opens with the provider's lap 1 (v6 §1a).
`python3 scripts/lap_language.py turn <round>` prints it, with any open question
the party owes and any condition still open.

**The ledger is computed, not written.** Open questions are the questions without
an answer. The state of each close condition is its latest `TERM` status. Promises
are listed with their due laps, and next-round findings are carried. v6 §5e asked
each side to write its ledger by hand. Here it is derived from statements both
sides can check.

## 11. What it does not do

- **It does not replace the gate.** Verdicts, closes, digests and releases stay in
  each project's gate under the protocol. The language makes a lap checkable. It
  decides nothing about a release.
- **It does not judge prose.** A statement's text is for the reader. **Where the
  text and the attributes disagree, the attributes are what the statement says,
  and the text is the defect.**
- **It does not make a claim true.** A `CLAIM derived` with a real file and line
  can still misread that line. What the language guarantees is that there is a
  line to go and check.
- **It does not check citations against the trees.** That needs both
  repositories and a network, and a checker that depends on the network is not
  evidence about a lap. Platterpus checks its own worked example's citations in
  a test, and skips the fork's by name when the clone is absent.

## 12. Conformance, and a worked example

- **The rule ids are the conformance surface.** For every id, a checker must reject
  a lap that breaks that rule and nothing else. Platterpus's cases are one per id in
  `tests/test_lap_language.py`. That test also requires this document and the
  checker to define exactly the same set of ids.
- **The worked example is a real lap.**
  `tests/fixtures/lap_language_round27_lap05.md` is our round 27 lap 5 written in
  the language: 33 statements, 14.3 KB against the original's 15.1 KB. It passes
  with no problems against the real round 27 record, with the real lap 5 taken out.
  Its turn reads `cyanrip-fork, lap 6`, and its one open condition is §0.3, pending
  on the fork.
- **The language asked three questions the prose lap never did.** Lap 5 reported
  three fixes of ours and never said whether their shape could hold in the fork's
  code, because nothing asked. `L31` made the example say, and all three are
  `portable: yes`. Writing it also showed that lap 5's `GO` rested on the fork's
  half of §0.3 still to come. Nothing in lap 5 recorded that; `TERM pending`
  now does.
- **Please try to break it.** A lap that satisfies every rule while misleading
  its reader is a defect in the rules, and it is worth more to us than
  agreement.

## 13. What we ask, for round 28

These are next-round items (E1, S-14). None of them holds round 27.

1. **Review this language**: accept it, amend it or refuse it. Refusals and
   amendments by rule id, please, so each one can be answered.
2. **If accepted: adopt it as optional now** (`HANDSHAKE-LANGUAGE: 1`, legal under
   v6 §3), and write your own checker from this document.
3. **Decide with us whether v7 makes it normative**, and from which round.
4. **Settle `HANDSHAKE-OPENER`'s spelling** (`cyanrip` vs `cyanrip-fork`). The
   language keeps v6's for now.

*Last updated for Platterpus v0.6.60.*
