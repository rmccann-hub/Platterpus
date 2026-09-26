"""The lap language: a typed, checkable way to write a handshake lap.

**Why this exists.** The shared protocol (`docs/handshake-protocol.md`, v6) makes
a lap's *header* precise and leaves everything under it as free prose. The record
shows what that costs, measured over all 150 laps on file on 2026-09-26 (both
directions, 2.66 MB):

* **26% of header values are paragraphs.** 989 of 3,810 header lines carry a value
  longer than 120 characters, so even the fields a gate reads hold prose.
* **21 of the 61 field names in use appear nowhere in the spec**, and 7 more are
  named only as "deferred to v7". A field nobody defined is a field each side reads
  its own way.
* **The two gates already read one field two ways.** Given a
  `HANDSHAKE-PEER-VERDICT-SOURCE` that says *"superseding our lap 5 … your
  `round-27-lap-04.md`"*, ours reads lap 4 (it tries a filename first,
  `platterpus@edd82ad:scripts/handshake.py:2276-2303`) and the fork's reads lap 5
  (the first "lap N", `cyanrip@874ddad:tools/release-gate.py:207`). They agree today
  because of how the sentences happen to be phrased.
* **"Whose turn is it?" has no answer in the files.** `HANDSHAKE-NEXT-LAP` exists
  and carries sentences such as *"6 (yours), transcribing this verdict. Our gate
  reads round 27 CLOSED once…"*.

**The language in one paragraph.** A lap is a header and a body. Every header
field has a declared type, and its explanation lives in a statement it references
rather than in the value. The body is made only of *statements*: a level-4 heading
`#### <ID> <KIND> <qualifier>`, one short paragraph of text, and a list of typed
`- key: value` attributes. There are eight kinds (CLAIM, QUESTION, ANSWER,
FINDING, NOTICE, PROMISE, ERRATUM, TERM). Each rule corresponds to a failure in
the record. Prose outside a statement is refused, because a sentence with no
statement around it can't be referenced, answered or checked.

**Who reads what.** This package is the *language* checker: grammar, types, and
the rules between statements. It is not the release gate, and it does not
duplicate the gate. Protocol fields, verdicts and closes stay in
`scripts/handshake.py`. The fork implements the same grammar on its own side,
because a convention copied from one implementation into another is one
implementation copied twice (`CLAUDE.md` rule #12).

**Adoption without a protocol bump.** A lap opts in by declaring
`HANDSHAKE-LANGUAGE: 1`. Under v6 §3 unknown fields are ignored by both gates, so
a language-1 lap is still a valid v6 lap for both of them. Protocol v7 is where
the language would become normative. Until then, only files that declare it are
checked.

The spec is `docs/handshake/outbound/artifacts/lap-language-1.md`. This package
must agree with it, and `tests/test_lap_language.py` holds both to that.

Parsing never raises (`CLAUDE.md`: parsers of external output never raise), since
the fork's laps are external input. Problems come back as data.

The package, one responsibility per module:

* `model` — the parsed lap, its statements and the problems found.
* `values` — the typed atoms both the header and the statements use.
* `header` — the header's field table and its checks.
* `kinds` — the eight statement kinds and their attributes.
* `parse` — reading a lap, and the rules inside one lap.
* `rounds` — the rules between laps, and whose turn it is.
* `cli` — the command line, run as `scripts/lap_language.py`.
"""

from __future__ import annotations
