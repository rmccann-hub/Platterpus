#!/usr/bin/env python3
"""Mutation testing without a third-party mutation tool.

**Why this exists rather than `mutmut`.** The weekly audit ran for seven runs
reporting success while measuring nothing, because an unpinned major release
removed the CLI flag it was built around. It was then pinned, given a floor, and
left deliberately red — with a recorded diagnosis blaming the import path.

**That diagnosis is wrong, and this script exists because measuring it said so.**
Reproduced 2026-09-05 on `mutmut 3.7`:

* under `pytest` run from `mutants/`, the mutated module **is** the one imported —
  `platterpus.ctdb.crc` resolves to `mutants/src/platterpus/ctdb/crc.py` with the
  trampoline present, so the "tests import the source under a different module
  path" explanation does not hold here;
* `mutmut run` generates mutants and then **executes none** — including when a
  single mutant is named on the command line, which takes 150 ms and reports
  *"0 files mutated, 156 ignored, 1 unmodified"*.

So the previous session **explained the symptom without reproducing it**, which
is the first question `CLAUDE.md` asks of any fix. The explanation was plausible,
specific, and not the mechanism.

**Why build rather than swap tools.** Critical rule #11 — *a tool that gates CI
must not float* — was written after exactly this, and swapping mutmut for another
third-party mutator keeps the failure mode: a signal that can retire under us
without saying so. This project already owns the primitive the audit needs.
`scripts/revert_probe.py` applies a change, runs named tests, and reports whether
they noticed. A mutation sweep is that primitive in a loop over generated edits.

**WHAT THE SCORE IS A SCORE OF, because the denominator decides its meaning.**
Each sweep runs ONE module against the test files that target it, not the whole
suite — running 4,700 tests per mutant is not a 90-minute job. So a survivor
means *"this module's own tests do not pin this line"*, which is the useful
question, and NOT *"nothing in the repo pins it"*. Read it as a per-module
strength measure with its selection named, never as a repo-wide grade.

**A worked example of why the population matters more than the number.** The
first version of this file reported **21 mutants at 23.8%** on `verdict.py`. It
was wrong: `ast.cmpop` and `ast.boolop` nodes carry no `lineno`, so every
comparison and boolean mutant was generated and silently dropped, and all 21
survivors were constants. Fixed, the same module offers **66**. The score barely
moved; the thing being measured tripled. A mutation score without its population
is the *"is the population I measured closed?"* failure expressed as a
percentage.

**What it does NOT claim.** A surviving mutant is a *question*, not a defect: it
may be semantically equivalent to the original (`x < 1` vs `x <= 0` on ints), or
in code the selected tests were never meant to cover. The score is a floor on
suite strength, not a grade — and it is reported with the population it was
measured over, because a score without its denominator is the "is the population
closed?" failure in one number.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import random
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Final, TypedDict

REPO_ROOT: Final[Path] = Path(__file__).resolve().parent.parent

#: Comparison operators, swapped for their most confusable neighbour. Chosen so a
#: surviving mutant is *interesting*: `<` → `<=` is an off-by-one, which is the
#: boundary bug a test suite most often misses, rather than `<` → `>`, which
#: almost anything catches.
_CMP_SWAP: Final[dict[type[ast.cmpop], type[ast.cmpop]]] = {
    ast.Lt: ast.LtE,
    ast.LtE: ast.Lt,
    ast.Gt: ast.GtE,
    ast.GtE: ast.Gt,
    ast.Eq: ast.NotEq,
    ast.NotEq: ast.Eq,
    ast.Is: ast.IsNot,
    ast.IsNot: ast.Is,
    ast.In: ast.NotIn,
    ast.NotIn: ast.In,
}

#: `and` <-> `or`. The classic short-circuit defect, and the one that produced the
#: fork's own surviving mutant in `fun512.c` (relayed 2026-08-27).
_BOOL_SWAP: Final[dict[type[ast.boolop], type[ast.boolop]]] = {
    ast.And: ast.Or,
    ast.Or: ast.And,
}


class SweepReport(TypedDict):
    """The sweep's result as a declared struct, not an untyped dict.

    `CLAUDE.md` rule #10 forbids a bare dict as a pseudo-struct, and the reason
    showed up immediately here: with `dict[str, object]` the CLI had to cast
    every field back out, and two of those casts needed `type: ignore` — which is
    the checker saying the shape was never really known. Naming it once makes the
    JSON artifact, the CLI and any future reader agree on the fields.

    `score` is `None` rather than `0.0` when nothing was checked, because "no
    mutants ran" and "every mutant survived" are different findings and only one
    of them is about the tests.
    """

    generated: int
    sampled: int
    checked: int
    killed: int
    survived: int
    unappliable: int
    score: float | None
    survivors: list[str]
    unappliable_names: list[str]


@dataclass(frozen=True)
class Mutant:
    """One candidate edit: where it is, and what it becomes."""

    path: Path
    lineno: int
    col: int
    kind: str
    before: str
    after: str

    @property
    def name(self) -> str:
        # Repo-relative when it can be — that is the form a reader can paste into
        # an editor — but never at the cost of raising: the harness is also run
        # over temporary files by its own tests, and a reporting helper that
        # explodes on an unexpected path would take the sweep down with it.
        try:
            where: Path | str = self.path.relative_to(REPO_ROOT)
        except ValueError:
            where = self.path
        return (
            f"{where}:{self.lineno}:{self.col} {self.kind} {self.before}->{self.after}"
        )


class _Collector(ast.NodeVisitor):
    """Every mutable site in one module, as (node, kind, before, after)."""

    def __init__(self) -> None:
        self.found: list[tuple[ast.AST, str, str, str]] = []

    # OPERATOR NODES CARRY NO POSITION, and the first version of this file did
    # not know that. `ast.cmpop` and `ast.boolop` have no `lineno`/`col_offset`
    # — only expressions and statements do — so every comparison and boolean
    # mutant was generated and then silently dropped by the position guard in
    # `_mutants_for`. The sweep still ran, still reported a score, and every one
    # of its 21 mutants was a CONSTANT.
    #
    # **That is this project's own failure mode inside the tool built to detect
    # it**: a measurement that quietly covers less than it claims, reporting a
    # number that looks like the whole answer. Caught by writing the test that
    # asserts which KINDS are found — the check that could be satisfied by
    # finding nothing, asked of the checker.
    #
    # The anchor is therefore the END of the operand before the operator, which
    # is an expression and does have a position.

    def visit_Compare(self, node: ast.Compare) -> None:  # noqa: N802
        preceding: ast.expr = node.left
        for index, op in enumerate(node.ops):
            replacement = _CMP_SWAP.get(type(op))
            if replacement is not None:
                self.found.append(
                    (preceding, "cmp", type(op).__name__, replacement.__name__)
                )
            if index < len(node.comparators):
                preceding = node.comparators[index]
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:  # noqa: N802
        replacement = _BOOL_SWAP.get(type(node.op))
        if replacement is not None and node.values:
            self.found.append(
                (node.values[0], "bool", type(node.op).__name__, replacement.__name__)
            )
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:  # noqa: N802
        # Booleans and small ints only. Mutating a string constant mostly finds
        # log wording, which no test should be pinning and every test would then
        # "kill" for the wrong reason — a mutant that is easy to kill inflates the
        # score without measuring anything.
        if isinstance(node.value, bool):
            self.found.append((node, "const", str(node.value), str(not node.value)))
        elif isinstance(node.value, int) and not isinstance(node.value, bool):
            if -2 <= node.value <= 2:
                self.found.append((node, "const", str(node.value), str(node.value + 1)))
        self.generic_visit(node)


def _mutants_for(path: Path) -> list[Mutant]:
    """Every mutant this module offers, ordered deterministically."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    collector = _Collector()
    collector.visit(tree)
    out: list[Mutant] = []
    for node, kind, before, after in collector.found:
        if kind in ("cmp", "bool"):
            # Anchored at the END of the operand before the operator: the token
            # we are replacing begins somewhere at or after it.
            lineno = getattr(node, "end_lineno", None)
            col = getattr(node, "end_col_offset", None)
        else:
            lineno = getattr(node, "lineno", None)
            col = getattr(node, "col_offset", None)
        if lineno is None or col is None:
            # An operator node without position info cannot be located in the
            # source, so it cannot be applied OR reported. Skipped and counted by
            # the caller rather than dropped silently.
            continue
        out.append(Mutant(path, lineno, col, kind, before, after))
    return sorted(out, key=lambda m: (str(m.path), m.lineno, m.col, m.before))


#: How each operator is spelled in source, so a mutation is a textual edit at a
#: known offset rather than an unparse of the whole module. `ast.unparse` would
#: reformat the entire file, so a failing test could be reacting to the
#: reformatting instead of to the mutation — a mutant that is not the mutation.
_SPELLING: Final[dict[str, str]] = {
    "Lt": "<",
    "LtE": "<=",
    "Gt": ">",
    "GtE": ">=",
    "Eq": "==",
    "NotEq": "!=",
    "Is": "is",
    "IsNot": "is not",
    "In": "in",
    "NotIn": "not in",
    "And": "and",
    "Or": "or",
}


def _apply(source: str, mutant: Mutant) -> str | None:
    """`source` with `mutant` applied, or None if the site cannot be located.

    Returning None rather than guessing: a mutation applied to the wrong offset
    is a *different* edit than the one reported, and a survivor from it would be
    a fact about nothing.
    """
    lines = source.splitlines(keepends=True)
    if not (1 <= mutant.lineno <= len(lines)):
        return None
    line = lines[mutant.lineno - 1]
    before = _SPELLING.get(mutant.before, mutant.before)
    after = _SPELLING.get(mutant.after, mutant.after)
    if mutant.kind == "const":
        before, after = mutant.before, mutant.after
    if mutant.kind in ("cmp", "bool"):
        # Forward from the end of the preceding operand. Bounded so a token that
        # really belongs to a LATER expression on the same line cannot be picked
        # up: an edit at the wrong offset is a different mutation than the one
        # reported, and a survivor from it is a fact about nothing.
        start = line.find(before, mutant.col)
        if start < 0 or start > mutant.col + 8:
            return None
    else:
        start = line.find(before, max(0, mutant.col - 2))
        if start < 0 or start > mutant.col + len(before) + 2:
            return None
    # Word-ish operators must not match inside an identifier: `is` in `exists`.
    if before.isalpha():
        pre = line[start - 1] if start else " "
        post_at = start + len(before)
        post = line[post_at] if post_at < len(line) else " "
        if pre.isalnum() or pre == "_" or post.isalnum() or post == "_":
            return None
    lines[mutant.lineno - 1] = line[:start] + after + line[start + len(before) :]
    return "".join(lines)


def _run_tests(tests: list[str], timeout: int) -> bool:
    """True if the selected tests all PASS. A crash or timeout counts as caught.

    A mutation that makes the suite error out has been noticed, which is the only
    thing this measures. Reading the exit code directly rather than through a
    pipe — `CLAUDE.md` has this wrong four recorded times.
    """
    # `PYTHONDONTWRITEBYTECODE` is NOT hygiene here — it is the fix for a defect
    # this harness shipped with. See `_restore`: a `.pyc` compiled from a MUTANT
    # outlives the restore, because CPython validates cached bytecode by
    # (mtime, size) and a restored file has the same size and, inside one second,
    # the same mtime. The interpreter then loads the mutant's bytecode from a
    # source file byte-identical to HEAD.
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    try:
        proc = subprocess.run(  # noqa: S603 — our own pytest, fixed argv
            [
                sys.executable,
                "-m",
                "pytest",
                *tests,
                "-x",
                "-q",
                "--no-header",
                "-p",
                "no:cacheprovider",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return False
    return proc.returncode == 0


def _restore(path: Path, original: str, before_hash: str) -> None:
    """Put the file back — content, bytecode, and an mtime that invalidates both.

    **Restoring the CONTENT is not restoring the MODULE**, and that gap shipped in
    the first version of this file. CPython caches compiled bytecode keyed on the
    source's (mtime, size); a mutation and its restore have the same size and,
    inside one second, the same mtime — so a `.pyc` compiled while the file was
    mutated stays "valid" and is loaded in preference to the correct source.

    Measured 2026-09-05: six CTDB tests failed after a sweep with
    `src/platterpus/ctdb/crc.py` byte-identical to `git show HEAD:` — a wrong
    archival CRC that `git diff` could not see and `git status` called clean.
    Deleting `__pycache__` fixed them. That is the worst shape this could take:
    the corruption was invisible to every tool a developer would reach for.

    Three defences, each closing a different hole:

    1. the child runs with ``PYTHONDONTWRITEBYTECODE`` so a mutant's `.pyc` is
       never written — the actual fix;
    2. any `.pyc` for this module is deleted anyway, because something else may
       have written one (an editor, a stray import, an older version of this
       script);
    3. the restored file's mtime is pushed FORWARD, so a cache this function did
       not find is invalidated by timestamp rather than trusted.

    Belt, braces and a second belt — proportionate for the one operation in this
    repo that deliberately writes wrong code into `src/`.
    """
    path.write_text(original, encoding="utf-8")
    restored = hashlib.sha256(path.read_text(encoding="utf-8").encode()).hexdigest()
    if restored != before_hash:  # pragma: no cover — defensive
        raise SystemExit(f"FAILED TO RESTORE {path} — stop and check `git diff`")

    cache = path.parent / "__pycache__"
    if cache.is_dir():
        for stale in cache.glob(f"{path.stem}.*.pyc"):
            stale.unlink(missing_ok=True)

    # Forward, never backward: a timestamp in the past would make the source look
    # OLDER than a cache and keep the stale entry authoritative.
    now = time.time() + 1
    os.utime(path, (now, now))


def sweep(
    targets: list[Path], tests: list[str], *, limit: int, seed: int, timeout: int
) -> SweepReport:
    """Run the sweep and return the report as data, never printing a verdict."""
    all_mutants: list[Mutant] = []
    for path in targets:
        all_mutants.extend(_mutants_for(path))

    rng = random.Random(seed)
    sampled = list(all_mutants)
    rng.shuffle(sampled)
    sampled = sorted(sampled[:limit], key=lambda m: (str(m.path), m.lineno, m.col))

    killed: list[str] = []
    survived: list[str] = []
    unappliable: list[str] = []

    for mutant in sampled:
        original = mutant.path.read_text(encoding="utf-8")
        mutated = _apply(original, mutant)
        if mutated is None or mutated == original:
            unappliable.append(mutant.name)
            continue
        before_hash = hashlib.sha256(original.encode()).hexdigest()
        try:
            mutant.path.write_text(mutated, encoding="utf-8")
            # PROVE THE EDIT LANDED before believing the result. A revert that
            # never applied is indistinguishable from a vacuous test, and this
            # project has four recorded instances of exactly that.
            now = hashlib.sha256(
                mutant.path.read_text(encoding="utf-8").encode()
            ).hexdigest()
            if now == before_hash:
                unappliable.append(mutant.name)
                continue
            if _run_tests(tests, timeout):
                survived.append(mutant.name)
            else:
                killed.append(mutant.name)
        finally:
            _restore(mutant.path, original, before_hash)

    checked = len(killed) + len(survived)
    return {
        "generated": len(all_mutants),
        "sampled": len(sampled),
        "checked": checked,
        "killed": len(killed),
        "survived": len(survived),
        "unappliable": len(unappliable),
        "score": (len(killed) / checked) if checked else None,
        "survivors": survived,
        "unappliable_names": unappliable,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target", action="append", default=[], help="module to mutate"
    )
    parser.add_argument("--tests", action="append", default=[], help="tests to run")
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument(
        "--min-checked",
        type=int,
        default=10,
        help="floor: fewer mutants actually executed than this is NO RESULT, "
        "never a pass — a sweep that checks nothing must not read as a clean one",
    )
    parser.add_argument("--min-score", type=float, default=0.0)
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args(argv)

    targets = [REPO_ROOT / t for t in args.target]
    missing = [str(p) for p in targets if not p.is_file()]
    if missing or not targets:
        print(f"no such target(s): {missing or '(none given)'}", file=sys.stderr)
        return 2

    report = sweep(
        targets,
        args.tests,
        limit=args.limit,
        seed=args.seed,
        timeout=args.timeout,
    )
    if args.json:
        args.json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    score = report["score"]
    print(
        f"generated={report['generated']} sampled={report['sampled']} "
        f"checked={report['checked']} killed={report['killed']} "
        f"survived={report['survived']} unappliable={report['unappliable']}"
    )
    print(f"score={score if score is None else f'{score:.1%}'}")
    for name in report["survivors"]:
        print(f"  SURVIVED  {name}")

    checked = report["checked"]
    if checked < args.min_checked:
        print(
            f"NO RESULT: only {checked} mutant(s) reached a verdict, floor is "
            f"{args.min_checked}. A sweep that checked nothing is not a clean "
            "sweep — this is the mutmut failure mode, refused here by design.",
            file=sys.stderr,
        )
        return 1
    if score is not None and score < args.min_score:
        print(
            f"score {score:.1%} is below the floor {args.min_score:.1%}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
