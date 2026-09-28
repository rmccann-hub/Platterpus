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

**The versions.** Both sides adopted A1–A8 as **LSL 2** in round 28, and a lap
that declares `LSL: 2` is held to them without `--amend`. **LSL 3** is LSL 2 plus
`B1`–`B3` (the fork's proposal, §"LSL 3", `cyanrip@889a375`): B1 a `run:` names
the one commit it ran at, and with `--rerun` a command that can depend on nothing
but that commit is re-run and its quoted result, and any exit code it states,
compared; B2 a `GO` needs a close condition to have waited on; B3 an `answers:`
counts only on a statement that can carry weight. B1 is read as both projects
agreed in round 29 (the fork's lap 1 S28 and S29; `lsl3`'s docstring). An LSL 1
or LSL 2 lap is checked exactly as before.

The spec for the amendments, and the findings, is
`docs/handshake/outbound/artifacts/lsl-amendments-1.md`; the spec for LSL 3 is the
fork's proposal. `tests/test_lap_language.py` holds this package to both.

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
* `round_rules` — the checks that read the whole round: A1, A2, A7, B2, B3.
* `lsl3` — LSL 3's checks of one lap: B1 and B3.
* `rerun` — which `run:` commands B1 may repeat, and matching their results (pure).
* `scratch` — repeating them: a detached scratch worktree, bounded, no shell.
* `cli` — the command line, run as `scripts/lap_language.py`.
"""
