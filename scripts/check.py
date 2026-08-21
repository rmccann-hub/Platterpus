#!/usr/bin/env python3
"""Run the gates CI runs, and report each one's TRUE exit status.

**Why this exists.** The gates themselves are fine. What kept going wrong was
*reading their result*. Typing

    python3 -m pytest ... | tail -15 ; echo "EXIT=$?"

reports **tail's** status, so a run with real failures prints `0`. That mistake
has been made four times across two sessions in this repository, and the standing
countermeasure was a sentence in `CLAUDE.md` — the one file every session is
guaranteed to read. It was read, and the mistake happened twice more. So the
countermeasure is wrong in kind: a rule that must be remembered at the moment of
typing cannot compete with a habit. Removing the *need* to pipe is the fix.

This script therefore:

* runs each gate with a **fixed argv and no shell**, so no pipeline exists whose
  last stage could shadow the status;
* keeps each gate's **complete** output in a file and prints a bounded excerpt —
  head *and* tail, because a tool's fatal message is the last thing it prints and
  a head-only cap drops exactly the line that explains the failure;
* prints a final table of gate → real exit code, so the verdict is legible
  without arithmetic;
* refuses to report success if the pytest run did not reach session-finish. A
  truncated run exits 0 with no summary — that exact thing marked a CI job green
  at 76% once — so the `.pytest-session-complete` sentinel is checked, and its
  **absence is a failure, not a missing nicety**.

It is not a replacement for CI, which remains the authority. It is the local
command whose answer can be trusted without a second thought.

Usage:

    python3 scripts/check.py                 # every gate
    python3 scripts/check.py --only lint     # one or more: lint format types tests
    python3 scripts/check.py --no-coverage   # faster suite run, no floor applied
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
SENTINEL: Final[Path] = REPO_ROOT / ".pytest-session-complete"

#: Branch-coverage floor. Mirrors `.github/workflows/ci.yml`; the workflow remains
#: the authority. Stated here so a local run applies the same bar rather than a
#: politer one — a local gate that is easier than CI's is a gate that teaches the
#: wrong thing.
COVERAGE_FLOOR: Final[int] = 91

#: Per-gate wall-clock bound. The suite measured 266 s clean and 320 s under
#: coverage instrumentation, so 30 minutes is far above any healthy run while
#: still bounding a wedged child. Every CI job here carries a timeout for the same
#: reason: an unbounded hang is indistinguishable from slowness.
_GATE_TIMEOUT_S: Final[float] = 1800.0

#: Excerpt budget per end when output is elided. Head *and* tail, always.
_EXCERPT_CHARS: Final[int] = 1500


@dataclass
class Gate:
    """One check to run: a name, an argv, and where its output landed."""

    name: str
    argv: list[str]
    #: Populated after the run.
    code: int | None = None
    output: str = ""
    notes: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True only for an exit code of exactly 0 with no added objection.

        `code is None` — never run, or the child was never reaped — is deliberately
        NOT a pass. Tri-state: "no result" is not agreement.
        """
        return self.code == 0 and not self.notes


def _excerpt(text: str) -> str:
    """Bounded output with head AND tail, and any elision counted, never silent."""
    if len(text) <= _EXCERPT_CHARS * 2:
        return text
    dropped = len(text) - _EXCERPT_CHARS * 2
    return (
        f"{text[:_EXCERPT_CHARS]}\n"
        f"    [... {dropped} characters elided from the middle ...]\n"
        f"{text[-_EXCERPT_CHARS:]}"
    )


def _run(gate: Gate) -> None:
    """Run one gate. Records the real exit code, or None if it could not run."""
    try:
        proc = subprocess.run(  # noqa: S603 — fixed argv, shell=False
            gate.argv,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=_GATE_TIMEOUT_S,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        gate.code = None
        gate.output = (exc.stdout or "") + (exc.stderr or "")
        gate.notes.append(
            f"TIMED OUT after {_GATE_TIMEOUT_S:.0f}s — no verdict, which is not a pass"
        )
        return
    except OSError as exc:
        gate.code = None
        gate.notes.append(f"could not start: {exc}")
        return
    gate.code = proc.returncode
    gate.output = proc.stdout + proc.stderr


def _build_gates(only: set[str], coverage: bool) -> list[Gate]:
    py = sys.executable
    pytest_argv = [py, "-m", "pytest"]
    if coverage:
        pytest_argv += [
            "--cov=platterpus",
            "--cov-report=term",
            f"--cov-fail-under={COVERAGE_FLOOR}",
        ]
    catalogue = {
        "lint": Gate("lint (ruff check)", [py, "-m", "ruff", "check", "src", "tests"]),
        "format": Gate(
            "format (ruff format --check)",
            [py, "-m", "ruff", "format", "--check", "src", "tests"],
        ),
        "types": Gate("types (mypy)", [py, "-m", "mypy"]),
        "tests": Gate("tests (pytest)", pytest_argv),
    }
    unknown = only - catalogue.keys()
    if unknown:
        raise SystemExit(
            f"check: unknown gate(s) {sorted(unknown)}; choose from {sorted(catalogue)}"
        )
    wanted = only or set(catalogue)
    # Cheap gates first: a lint failure should not cost five minutes of suite.
    return [gate for key, gate in catalogue.items() if key in wanted]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the CI gates locally and report each one's real exit status. "
            "Exits non-zero if any gate failed or produced no verdict."
        )
    )
    parser.add_argument(
        "--only",
        nargs="+",
        default=[],
        metavar="GATE",
        help="run only these gates: lint format types tests",
    )
    parser.add_argument(
        "--no-coverage",
        action="store_true",
        help="run the suite without coverage or the floor (faster; proves less)",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=None,
        help="where to write each gate's complete output (default: a temp dir)",
    )
    args = parser.parse_args(argv)

    gates = _build_gates(set(args.only), coverage=not args.no_coverage)

    log_dir = args.log_dir or (REPO_ROOT / ".check-logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    running_tests = any(gate.name.startswith("tests") for gate in gates)
    if running_tests:
        # Clear it first: a stale sentinel from an earlier run would vouch for this
        # one. Same reason `pytest_sessionstart` clears it.
        SENTINEL.unlink(missing_ok=True)

    for gate in gates:
        print(f"==> {gate.name}")
        if shutil.which(gate.argv[0]) is None and not Path(gate.argv[0]).exists():
            gate.notes.append(f"interpreter {gate.argv[0]!r} not found")
            print(f"    SKIPPED: {gate.notes[-1]}")
            continue
        _run(gate)
        log_path = log_dir / (gate.name.split()[0] + ".log")
        log_path.write_text(gate.output, encoding="utf-8")
        verdict = "ok" if gate.code == 0 else "FAILED"
        print(f"    exit={gate.code} ({verdict})   full output: {log_path}")
        if gate.code != 0:
            print(_excerpt(gate.output))

    # The sentinel check. Its absence means the pytest process vanished mid-run,
    # in which case its exit code means nothing at all — including when it is 0.
    tests_gate = next((g for g in gates if g.name.startswith("tests")), None)
    if tests_gate is not None:
        if not SENTINEL.exists():
            tests_gate.notes.append(
                "the pytest session never reached session-finish (no "
                ".pytest-session-complete), so its exit code is not a verdict"
            )
        else:
            recorded = SENTINEL.read_text(encoding="utf-8").strip()
            if recorded != str(tests_gate.code):
                tests_gate.notes.append(
                    f"the sentinel records status {recorded!r} but the process "
                    f"exited {tests_gate.code} — these must agree"
                )

    print()
    print("=" * 62)
    width = max(len(gate.name) for gate in gates)
    for gate in gates:
        state = "PASS" if gate.passed else "FAIL"
        code = "none" if gate.code is None else str(gate.code)
        print(f"  {gate.name:<{width}}  exit={code:>4}  {state}")
        for note in gate.notes:
            print(f"  {'':<{width}}    ! {note}")
    failed = [gate for gate in gates if not gate.passed]
    print("=" * 62)
    # Always print the denominator, so "no failures" carries a count with it.
    print(f"{len(gates) - len(failed)}/{len(gates)} gates passed")
    if tests_gate is not None and tests_gate.passed:
        for line in tests_gate.output.splitlines():
            if "Required test coverage" in line or line.startswith("TOTAL"):
                print(f"  {line.strip()}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
