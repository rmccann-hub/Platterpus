"""LSL, the lap statement language: a second, independent checker, and our amendments.

**What LSL is.** The fork proposed it in round 27 lap 6
(`PROPOSAL-lap-statement-language.md`, added at `cyanrip@f34a96c`). A lap that
declares `LSL: 1` carries numbered statements, each of one kind from a closed list
(FACT with a grade, NONE, UNKNOWN, DID, WILL, ACCEPT, AMEND, REFUSE, CORRECT,
ASK, VERDICT, NOTE), and each kind has the fields that make it checkable. The
wire headers are left exactly as the protocol defines them.

**Why this package exists.** Both projects built a lap language on 2026-09-26
from the same instruction, and the maintainer chose LSL as the base, with ours
sent as amendments to it. So this package does two jobs:

* **It is a second implementation of LSL 1**, written from the fork's spec and
  not from their code. Two checkers written from one spec that agree on a lap
  are evidence; one checker copied into two trees is not (`CLAUDE.md` rule #12).
  Where they disagree, the disagreement is the finding. Writing it found three,
  each measured against their checker on 2026-09-26: their checker reads "us" as
  cyanrip whoever wrote the lap; it refuses fields and values its spec's list of
  refusals does not mention; and a shallow clone makes it refuse commits it
  merely cannot see.
* **It implements our amendments**, `A1`–`A8`, behind `--amend`, so each one can
  be tried on a real lap before either side adopts it. They carry over what our
  own language had that LSL lacks: close conditions and a `GO` that waits for
  them, a pre-commit that is checked when it falls due, findings that say whose
  they are first, facts that say what they hold for, measurements that say
  whether their population is closed, weight only for checkable claims, answers
  that name their question, and corrections with evidence.

The spec for the amendments, and the findings, is
`docs/handshake/outbound/artifacts/lsl-amendments-1.md`. `tests/test_lap_language.py`
holds this package to it.

Parsing and checking never raise (`CLAUDE.md`: parsers of external output never
raise), since the fork's laps are external input. Problems come back as data.

The package, one responsibility per module:

* `model` — the parsed lap, its statements and the problems found.
* `grammar` — reading a lap into headers and statements (syntax only).
* `tables` — the kinds, grades and fields of LSL 1, and what each amendment adds.
* `refs` — the reference forms, and resolving them against both trees.
* `record` — the laps we hold, as this tree files them.
* `check` — LSL 1's checks, by the spec's numbered refusals.
* `amend` — the amendments' checks.
* `cli` — the command line, run as `scripts/lap_language.py`.
"""
