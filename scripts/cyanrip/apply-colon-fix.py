#!/usr/bin/env python3
"""Apply the metadata-colon fix to a cyanrip checkout — safely and verifiably.

This is the one error-prone step of the upstream colon-fix contribution: a hand
edit to *someone else's* C. Doing it by hand risks a stray-whitespace or
misplaced-block diff, which is exactly what the maintainer's "minimal, clean,
match surrounding style" rule forbids. This script inserts the exact guard the
soft-fork runbook designed (docs/cyanrip-soft-fork.md §2), but only after it has
*verified* the target function looks the way we expect — and it defaults to a
dry run that just shows the diff, so nothing is written until you've reviewed it.

Why a script (and not a `.patch` file): a line-anchored patch needs the exact
surrounding lines of cyanrip's current source, which this Platterpus session
can't fetch (it's scoped to this repo). Anchoring on the *function* and the
*tokenisation call* instead makes the edit robust to unrelated churn around it,
and the verification refuses to touch a function that has drifted from what the
fix assumes — in which case you apply it by hand from the runbook.

The fix itself (see the runbook for the full rationale): ``append_missing_keys``
tokenises ``-a``/``-t`` with ``av_strtok(src, ":")`` before ``av_dict_parse_string``
runs, so a literal ``:`` in an explicit value gets a spurious key injected. The
guard skips the positional-key injection when the string is already explicit
``key=value`` (an ``=`` occurs before the first ``:``); the caller then passes a
literal colon as ``\\:`` and ``av_dict_parse_string`` handles it.

Usage:
    python3 apply-colon-fix.py <path-to-cyanrip-checkout>            # dry run (default)
    python3 apply-colon-fix.py <path-to-cyanrip-checkout> --apply    # write the change

Exit codes: 0 = applied (or, in dry-run, would apply cleanly / already applied);
2 = the source didn't match what the fix assumes (apply by hand per the runbook);
3 = a usage / file error.
"""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

# The file and function the fix lives in (cyanrip master, verified 2026-07-08).
TARGET_RELPATH: str = "src/cyanrip_main.c"
FUNCTION_NAME: str = "append_missing_keys"

# The guard block, exactly as designed in the runbook. Indentation is applied at
# insertion time to match the tokenisation line it sits above.
_GUARD_BODY: tuple[str, ...] = (
    "/* If the string is already in explicit key=value form (an '=' appears",
    " * before the first ':'), skip the positional-shorthand key injection.",
    " * The scan below tokenises on ':' with av_strtok(), which — unlike the",
    " * av_dict_parse_string() this feeds — does not honour the '\\' escape, so",
    " * injecting keys here corrupts any value that legitimately contains a ':'",
    " * (e.g. album=Every Breath You Take\\: The Classics). Positional shorthand",
    " * (album:album_artist, no '=') is unaffected. */",
    "char *first_colon = strchr(src, ':');",
    "char *first_eq    = strchr(src, '=');",
    "if (first_eq && (!first_colon || first_eq < first_colon))",
    "    return copy;",
    "",
)

# A short, stable substring of the guard used to detect "already applied" so the
# script is idempotent (re-running never double-inserts).
_IDEMPOTENCY_MARKER: str = "first_eq < first_colon"


class SourceMismatch(Exception):
    """The target source doesn't match what the fix assumes — don't touch it."""


def _find_function_span(lines: list[str], name: str) -> tuple[int, int]:
    """Return the ``[start, end)`` line range of a C function body by name.

    Finds the *definition* (a line naming the function followed, on it or a
    later line, by an opening brace) and brace-matches to the closing ``}``.
    Raises :class:`SourceMismatch` if the function or its braces can't be found.
    """
    # Find a line that names the function and is not obviously a call (heuristic:
    # a definition line has no trailing ';' and the name is followed by '(').
    def_line = -1
    for i, line in enumerate(lines):
        idx = line.find(name)
        if idx == -1:
            continue
        after = line[idx + len(name) :].lstrip()
        if after.startswith("(") and not line.rstrip().endswith(";"):
            def_line = i
            break
    if def_line == -1:
        raise SourceMismatch(f"could not find a definition of {name}()")

    # Walk forward to the opening brace, then brace-match to the close.
    depth = 0
    started = False
    for j in range(def_line, len(lines)):
        for ch in lines[j]:
            if ch == "{":
                depth += 1
                started = True
            elif ch == "}":
                depth -= 1
        if started and depth == 0:
            return def_line, j + 1
    raise SourceMismatch(f"could not brace-match the body of {name}()")


def _leading_ws(line: str) -> str:
    return line[: len(line) - len(line.lstrip())]


def plan_patch(text: str) -> tuple[str, str]:
    """Return ``(new_text, note)`` with the guard inserted, or raise SourceMismatch.

    Pure (no I/O). ``note`` describes the outcome ("inserted …" or "already
    applied"). Verifies the function's shape before deciding where to insert.
    """
    lines = text.splitlines(keepends=True)
    start, end = _find_function_span(lines, FUNCTION_NAME)
    body = lines[start:end]
    body_text = "".join(body)

    # Verify the function is the one the fix assumes.
    if "av_strtok" not in body_text:
        raise SourceMismatch(
            f"{FUNCTION_NAME}() has no av_strtok() call — the source has changed; "
            "apply the guard by hand per docs/cyanrip-soft-fork.md §2"
        )
    if "copy" not in body_text or "returncopy" not in body_text.replace(" ", ""):
        raise SourceMismatch(
            f"{FUNCTION_NAME}() doesn't allocate/return `copy` as the fix assumes; "
            "apply by hand per the runbook"
        )

    if _IDEMPOTENCY_MARKER in body_text:
        return text, "already applied — no change"

    # Insert immediately before the first line that tokenises with av_strtok
    # (which is after `copy` is allocated). Match that line's indentation.
    insert_at = None
    for offset, line in enumerate(body):
        if "av_strtok" in line:
            insert_at = start + offset
            break
    if insert_at is None:  # pragma: no cover — guarded by the check above
        raise SourceMismatch("no av_strtok line found to anchor the insert")

    indent = _leading_ws(lines[insert_at])
    guard = [(indent + g).rstrip() + "\n" if g else "\n" for g in _GUARD_BODY]
    new_lines = lines[:insert_at] + guard + lines[insert_at:]
    return "".join(new_lines), f"inserted the guard before line {insert_at + 1}"


def _unified_diff(old: str, new: str, path: str) -> str:
    return "".join(
        difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "checkout", type=Path, help="path to the cyanrip source checkout"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="write the change (default is a dry run that only prints the diff)",
    )
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    target = Path(args.checkout) / TARGET_RELPATH
    if not target.is_file():
        print(f"error: {target} not found — is that a cyanrip checkout?")
        return 3

    text = target.read_text(encoding="utf-8")
    try:
        new_text, note = plan_patch(text)
    except SourceMismatch as exc:
        print(f"cannot auto-apply: {exc}")
        return 2

    if new_text == text:
        print(f"{note}")
        return 0

    print(_unified_diff(text, new_text, TARGET_RELPATH))
    print(f"\n# {note}")
    if not args.apply:
        print("# dry run — re-run with --apply to write it, then review `git diff`.")
        return 0
    target.write_text(new_text, encoding="utf-8")
    print(f"# written to {target}. Review `git diff`, build, smoke-test, then commit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
