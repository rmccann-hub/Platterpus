#!/usr/bin/env python3
"""Refuse a CI test run that collected fewer tests than the committed baseline.

**Why this exists (the 2026-10-27 external review, item 2.12).** CI already
checks that the pytest session *finished* (`.pytest-session-complete`, written by
`tests/conftest.py` as its last act). It did not check *how much* ran. A test
module that stops being collected, a `collect_ignore` added by mistake, a
`pytest.skip(allow_module_level=True)` that fires on the runner, or a fixture
change that makes a parametrisation empty, each leaves a finished, green run with
fewer tests in it, and the sentinel vouches for it all the same. A run that
checks less passes more easily, and nothing said so.

So the suite's own session-finish hook writes the number of tests the controller
collected to the file named by `PLATTERPUS_TEST_COUNT_FILE` (only when that
variable is set, so local runs write nothing), and this script compares it with
`tests/collected-tests-baseline.txt`.

**It ratchets.** Below the baseline fails. Above it passes and prints a notice
naming the number to raise the baseline to; raising it is a one-line edit in the
change that adds the tests. Lowering it is allowed only in a change that deletes
or merges tests on purpose and says so; `tests/test_check_test_count.py` refuses a
baseline below the one at the newest release tag, the same rule the coverage
floor follows.

Exit status: 0 when the count meets the baseline, 1 when it is below, missing or
malformed. A count that cannot be read is a refusal, never a pass: "not
determined" is not a pass anywhere in this project.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
#: The committed floor: one positive integer and a newline.
BASELINE_FILE: Final[Path] = REPO_ROOT / "tests" / "collected-tests-baseline.txt"
#: The variable `tests/conftest.py` reads to learn where to write the count.
COUNT_FILE_ENV: Final[str] = "PLATTERPUS_TEST_COUNT_FILE"


@dataclass(frozen=True)
class Verdict:
    """What the comparison found: whether it passes, and the sentence to print."""

    ok: bool
    message: str
    #: The number to raise the baseline to, when the run collected more.
    raise_to: int | None = None


def parse_count(text: str) -> int | None:
    """The single non-negative integer `text` holds, or None if it holds anything else.

    Strict on purpose: a file holding `9327 tests` or two numbers is not a count
    this script can vouch for. Never raises.
    """
    stripped = text.strip()
    if not stripped.isascii() or not stripped.isdigit():
        return None
    return int(stripped)


def judge(collected: int | None, baseline: int | None) -> Verdict:
    """Compare the collected count with the baseline. Pure; never raises."""
    if baseline is None or baseline <= 0:
        return Verdict(
            False,
            f"the baseline in {BASELINE_FILE.name} is missing or not a positive "
            "integer, so there is nothing to compare the run with. Refusing.",
        )
    if collected is None:
        return Verdict(
            False,
            "the run's collected-test count is missing or malformed, so this check "
            "cannot say how much ran. Refusing rather than passing.",
        )
    if collected < baseline:
        return Verdict(
            False,
            f"this run collected {collected} tests, {baseline - collected} fewer than "
            f"the baseline of {baseline}. A module that stopped being collected "
            "passes by not running. If tests were removed or merged on purpose, "
            f"lower {BASELINE_FILE.name} in the same change and say why.",
        )
    if collected > baseline:
        return Verdict(
            True,
            f"collected {collected} tests, {collected - baseline} above the baseline "
            f"of {baseline}. Raise tests/{BASELINE_FILE.name} to {collected} in this "
            "change so the floor follows the suite.",
            raise_to=collected,
        )
    return Verdict(True, f"collected {collected} tests, equal to the baseline.")


def _read(path: Path) -> int | None:
    try:
        return parse_count(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--count-file",
        type=Path,
        required=True,
        help=f"the file the suite wrote its count to (${COUNT_FILE_ENV})",
    )
    parser.add_argument("--baseline-file", type=Path, default=BASELINE_FILE)
    args = parser.parse_args(argv)
    verdict = judge(_read(args.count_file), _read(args.baseline_file))
    if not verdict.ok:
        print(f"::error::{verdict.message}")
        return 1
    # A GitHub notice when the baseline is behind, so the number to raise it to
    # shows on the run's summary page rather than only in the log.
    print(f"::notice::{verdict.message}" if verdict.raise_to else verdict.message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
