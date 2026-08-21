#!/usr/bin/env python3
"""Prove a test actually fails when the fix it guards is reverted.

**Why this is a committed tool and not a habit.** `CLAUDE.md` asks, of every fix:
*"Would this test fail if I reverted the fix? Check by actually reverting it."*
That question has caught a vacuous detector in this repo **twice** — including one
whose first version passed against the very bug it was written for, because it
looked for a *mention* of a thread rather than a *call* that stops it.

But the check itself was performed by hand-writing a throwaway script each time,
which has two costs. The obvious one is rework. The subtle one is that the
throwaway script kept having to re-learn the same four ways a revert can silently
fail to land — and a revert that never landed produces a **passing test that
looks exactly like a vacuous test**. All four are on the record here:

1. a `str.replace` whose anchor the formatter had reflowed, so it matched nothing;
2. a patch script that asserted *after* it edited, so the write never happened;
3. `ruff --fix` deleting an import between two halves of a change;
4. (cyanrip fork, same week) a `sed` that produced non-compiling C while build
   output was suppressed — so the **stale binary** ran the test and passed.
5. a revert that changed the file **without changing behaviour**. Found by using
   this tool, 2026-08-20: `X = {` → `X = {} or {` alters the bytes and the hash,
   and evaluates to the *same* dict, because `{}` is falsy. The probe duly
   reported `VACUOUS` — correctly, by its own definition — and the real fault was
   in the spec. So the hash check proves *the file changed*; it cannot prove *the
   meaning changed*, and no tool can. `VACUOUS` therefore says so in its own
   message: before believing a test is dead, confirm the replacement is
   semantically different, not merely textually different.

So this tool refuses rather than guesses, and it proves each step:

* the anchor must appear **exactly once** — zero means the edit cannot land, more
  than one means we do not know which site we changed;
* the file's hash must **change** — that is the proof the write landed, replacing
  the assumption that `write_text` did something;
* a **collection or import error is not a failure** — it is an absence of
  evidence, reported as such, because a syntax error otherwise reads as *"the
  test caught the bug"*;
* a test that **passes** with the fix reverted is reported as `VACUOUS`, which is
  the finding this whole exercise exists to surface;
* the original is always restored, and the restore is **verified by hash** rather
  than assumed.

**Usage.** Describe the reverts in a JSON spec so multi-line anchors survive
without shell quoting, which is its own source of silent mismatch:

    python3 scripts/revert_probe.py path/to/spec.json

    {
      "reverts": [
        {
          "label": "call-removed",
          "file": "tests/conftest.py",
          "anchor": "    print_coverage_report(session, reporter)\\n",
          "replacement": "",
          "tests": ["tests/test_harness_fidelity.py::test_session_finish_actually_calls_the_coverage_printer"],
          "expect": "detected"
        }
      ]
    }

`expect` is `"detected"` (default — the test must fail) or `"unaffected"` (the
test must still pass). `"unaffected"` is not padding: it is how you assert that a
*different* test does **not** depend on the reverted line, which is what proves
an anchor is narrow rather than merely present.

Exit status is `0` only if every revert produced its expected outcome.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]

#: Bound on one pytest invocation. Generous: a single node id is fast, but the
#: session imports Qt and a cold container has been measured at several seconds.
#: A bound at all matters because a wedged child would otherwise hang the probe
#: with no diagnosis — the same reason every CI job here carries a timeout.
_TEST_TIMEOUT_S: Final[float] = 900.0

#: pytest's own exit codes, which are the RELIABLE discriminator between "the test
#: ran and failed" and "the test never ran".
#:
#: The first version of this matched substrings ("SyntaxError", "IndentationError",
#: …) against the whole captured output, and that was wrong in both directions —
#: found by using this tool on a test that detects skip-bearing sweeps:
#:
#:  * FALSE "no evidence": pytest echoes the failing test's SOURCE in its report,
#:    and that source contained `except SyntaxError:`. The marker matched the
#:    echoed code rather than a real collection failure, so a genuine detection
#:    was reported as unusable. A substring match where a subject was needed —
#:    precisely the class this tool exists to catch, in the tool itself.
#:  * MISSED case: exit code 5 is NO_TESTS_COLLECTED, which a mistyped node id
#:    produces. Non-zero, so the old logic read it as a successful detection —
#:    a false positive far worse than the false negative above, because it would
#:    certify a test as guarding a line it never even ran against.
#:
#: 0 passed · 1 tests ran and failed · 2 interrupted (collection error) ·
#: 3 internal error · 4 usage error · 5 no tests collected.
_RAN_AND_FAILED: Final[int] = 1
_NO_EVIDENCE_CODES: Final[frozenset[int]] = frozenset({2, 3, 4, 5})

#: Kept as a SECONDARY signal only, and anchored to pytest's own line prefixes so
#: source echoed into a traceback cannot trigger them. Consulted only when the exit
#: code is otherwise ambiguous.
_NO_EVIDENCE_LINE_PREFIXES: Final[tuple[str, ...]] = (
    "ImportError while loading conftest",
    "ERROR collecting",
    "INTERNALERROR",
    "!!!!! Interrupted",
)


class ProbeError(Exception):
    """A refusal: the probe could not be performed, so it reports nothing."""


@dataclass(frozen=True)
class Revert:
    """One reversion to apply, and what the named tests should then do."""

    label: str
    file: Path
    anchor: str
    replacement: str
    tests: tuple[str, ...]
    expect: str  # "detected" | "unaffected"


@dataclass(frozen=True)
class Outcome:
    """What happened for one revert. `ok` means it matched `Revert.expect`."""

    label: str
    ok: bool
    detail: str


def _digest(path: Path) -> str:
    """Short content hash. Used only to prove a write landed, so 16 hex is ample."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _parse_spec(spec_path: Path) -> list[Revert]:
    """Read and validate the spec. Every field is checked before anything is edited.

    Validation is up front and total on purpose: this tool *modifies source files*,
    so discovering a malformed entry halfway through would leave the tree in a
    state the operator did not ask for.
    """
    try:
        raw = json.loads(spec_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ProbeError(f"cannot read the spec {spec_path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ProbeError(f"the spec {spec_path} is not valid JSON: {exc}") from exc

    entries = raw.get("reverts")
    if not isinstance(entries, list) or not entries:
        raise ProbeError(
            "the spec needs a non-empty 'reverts' list. An empty spec would exit 0 "
            "and report success having probed nothing — the exact 'satisfied by "
            "finding nothing' shape this tool exists to refuse."
        )

    reverts: list[Revert] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ProbeError(f"reverts[{index}] is not an object")
        label = str(entry.get("label") or f"revert-{index}")
        for required in ("file", "anchor", "tests"):
            if required not in entry:
                raise ProbeError(f"reverts[{index}] ({label}) has no '{required}'")
        target = (REPO_ROOT / str(entry["file"])).resolve()
        # Refuse a path outside the repo: this tool writes to it.
        if not target.is_relative_to(REPO_ROOT):
            raise ProbeError(f"{label}: {target} is outside the repository")
        if not target.is_file():
            raise ProbeError(f"{label}: {target} does not exist")
        tests = entry["tests"]
        if not isinstance(tests, list) or not tests:
            raise ProbeError(
                f"{label}: 'tests' must be a non-empty list of pytest node ids"
            )
        anchor = str(entry["anchor"])
        if not anchor:
            raise ProbeError(f"{label}: an empty anchor matches everywhere")
        expect = str(entry.get("expect", "detected"))
        if expect not in {"detected", "unaffected"}:
            raise ProbeError(
                f"{label}: expect must be 'detected' or 'unaffected', not {expect!r}"
            )
        reverts.append(
            Revert(
                label=label,
                file=target,
                anchor=anchor,
                replacement=str(entry.get("replacement", "")),
                tests=tuple(str(t) for t in tests),
                expect=expect,
            )
        )
    return reverts


def _run_tests(tests: tuple[str, ...]) -> tuple[int, str]:
    """Run pytest on the given node ids and return `(returncode, combined output)`.

    No shell, and therefore no pipeline — which is deliberate. Reading a status
    through `cmd | tail` reports the *pipe's* last stage, so a real failure prints
    `0`; that mistake has been made four times across two sessions in this project
    and is precisely the class of thing a committed tool should make unreachable.
    """
    proc = subprocess.run(  # noqa: S603 — fixed argv, no shell
        [
            sys.executable,
            "-m",
            "pytest",
            *tests,
            "-q",
            "-p",
            "no:cacheprovider",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=_TEST_TIMEOUT_S,
        check=False,
    )
    return proc.returncode, proc.stdout + proc.stderr


#: The signature of a test runner: node ids in, `(returncode, output)` out.
TestRunner = Callable[[tuple[str, ...]], tuple[int, str]]


def apply_and_probe(revert: Revert, run_tests: TestRunner | None = None) -> Outcome:
    """Apply one revert, run its tests, restore, and judge the result.

    `run_tests` is injectable so this tool's own refusals can be tested without
    nesting a pytest session inside a pytest session. That seam is not a
    convenience: the refusal paths — a non-unique anchor, a write that did not
    land, a collection error, a vacuous test — are the entire value of the tool,
    and a tool whose failure modes are untested is the thing it exists to catch.
    """
    runner: TestRunner = run_tests if run_tests is not None else _run_tests
    path = revert.file
    original = path.read_text(encoding="utf-8")

    occurrences = original.count(revert.anchor)
    if occurrences != 1:
        return Outcome(
            revert.label,
            ok=False,
            detail=(
                f"REFUSED: the anchor appears {occurrences} times in "
                f"{path.relative_to(REPO_ROOT)}, and this probe needs exactly one. "
                "Zero means the edit cannot land (a formatter may have reflowed it); "
                "more than one means we would not know which site was changed."
            ),
        )

    before = _digest(path)
    path.write_text(
        original.replace(revert.anchor, revert.replacement), encoding="utf-8"
    )
    after = _digest(path)

    try:
        if before == after:
            return Outcome(
                revert.label,
                ok=False,
                detail=(
                    "REFUSED: the file hash did not change, so the write did not "
                    "land. Any test result now would be indistinguishable from a "
                    "vacuous test."
                ),
            )

        code, output = runner(revert.tests)

        # THE EXIT CODE IS THE DISCRIMINATOR, not a substring of the output. See
        # `_NO_EVIDENCE_CODES` for the two ways the substring version was wrong.
        no_evidence_reason = ""
        if code in _NO_EVIDENCE_CODES:
            no_evidence_reason = {
                2: "pytest was interrupted — usually a collection or import error",
                3: "pytest hit an internal error",
                4: "pytest rejected the invocation (usage error)",
                5: (
                    "pytest collected NO TESTS — check the node id in `tests`. This "
                    "is the dangerous one: it is non-zero, so a naive check reads it "
                    "as a successful detection while nothing ran at all"
                ),
            }[code]
        elif code not in (0, _RAN_AND_FAILED):
            # An exit code neither pytest nor this tool knows how to interpret is
            # not a verdict. Tri-state: no result is not a pass and not a failure.
            no_evidence_reason = f"unrecognised pytest exit code {code}"
        else:
            for line in output.splitlines():
                stripped = line.strip()
                if any(
                    stripped.startswith(prefix) for prefix in _NO_EVIDENCE_LINE_PREFIXES
                ):
                    no_evidence_reason = f"pytest reported: {stripped[:120]}"
                    break

        if no_evidence_reason:
            return Outcome(
                revert.label,
                ok=False,
                detail=(
                    f"NO EVIDENCE: {no_evidence_reason}. The test never ran, so this "
                    "is neither a detection nor a vacuous test — there is nothing to "
                    f"conclude. Exit {code}.\n" + _excerpt(output)
                ),
            )

        detected = code == _RAN_AND_FAILED
        if revert.expect == "detected":
            if detected:
                return Outcome(
                    revert.label,
                    ok=True,
                    detail=(
                        f"detected: revert landed ({before} -> {after}) and pytest "
                        f"exited {code}.\n" + _failed_lines(output)
                    ),
                )
            return Outcome(
                revert.label,
                ok=False,
                detail=(
                    "VACUOUS: the test PASSED with the fix reverted, so on the "
                    f"evidence it does not guard this line. The file did change "
                    f"({before} -> {after}).\n"
                    "    BEFORE concluding the test is dead, check the ONE thing a "
                    "hash cannot: that the replacement is semantically different, "
                    "not merely textually different. `X = {` -> `X = {} or {` "
                    "changes the bytes and evaluates to the same dict. If the "
                    "replacement is a no-op, this verdict is about the spec, not "
                    "the test.\n" + _excerpt(output)
                ),
            )
        # expect == "unaffected"
        if detected:
            return Outcome(
                revert.label,
                ok=False,
                detail=(
                    f"UNEXPECTED: the test was expected NOT to depend on this line, "
                    f"but pytest exited {code}. Either the anchor is wider than "
                    "intended or the test is coupled to it.\n" + _failed_lines(output)
                ),
            )
        return Outcome(
            revert.label,
            ok=True,
            detail=f"unaffected as expected: revert landed ({before} -> {after})",
        )
    finally:
        path.write_text(original, encoding="utf-8")
        restored = _digest(path)
        if restored != before:
            # Loud, and not swallowed by the return value: the operator's working
            # tree is now wrong, which matters more than the probe's verdict.
            print(
                f"!! RESTORE FAILED for {path}: hash {restored}, expected {before}. "
                "Check `git diff` before doing anything else.",
                file=sys.stderr,
            )


def _failed_lines(output: str, limit: int = 6) -> str:
    """The FAILED lines, so the report names *which* test detected the revert."""
    lines = [ln.strip() for ln in output.splitlines() if "FAILED" in ln]
    return (
        "\n".join(f"    {ln[:200]}" for ln in lines[:limit]) or "    (no FAILED lines)"
    )


def _excerpt(output: str, tail: int = 1200) -> str:
    """Head *and* tail of the output, because a fatal message is the last thing printed.

    A head-only cap drops precisely the line that explains the failure — the
    project's diagnostic-completeness rule — and an elision is marked rather than
    silent.
    """
    if len(output) <= tail * 2:
        return output
    dropped = len(output) - tail * 2
    return (
        f"{output[:tail]}\n    [... {dropped} characters elided ...]\n{output[-tail:]}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Prove a test fails when the fix it guards is reverted. Exits non-zero "
            "unless every revert produced its expected outcome."
        )
    )
    parser.add_argument("spec", type=Path, help="JSON spec describing the reverts")
    args = parser.parse_args(argv)

    try:
        reverts = _parse_spec(
            args.spec if args.spec.is_absolute() else Path.cwd() / args.spec
        )
    except ProbeError as exc:
        print(f"revert_probe: {exc}", file=sys.stderr)
        return 2

    outcomes: list[Outcome] = []
    for revert in reverts:
        print(f"--- {revert.label}: {revert.file.relative_to(REPO_ROOT)}")
        outcome = apply_and_probe(revert)
        outcomes.append(outcome)
        print(f"    {outcome.detail}")

    print()
    failures = [o for o in outcomes if not o.ok]
    # Report the denominator, always. "0 problems" with no count of what was
    # examined is the shape this project refuses in its own gates.
    print(
        f"probed {len(outcomes)} revert(s); {len(failures)} did not behave as expected"
    )
    for outcome in failures:
        print(f"  NOT OK: {outcome.label}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
