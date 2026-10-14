#!/usr/bin/env python3
"""Copy or extract a run-evidence file into the test fixtures, and check them all.

**Why this exists (HR-2, 2026-10-14).** Round 33's first task moves run evidence
(the `docs/handshake/artifacts*` folders) off `main` onto an `evidence` branch, so a
checkout stops carrying ~425 MB that no build reads. HR-2 §2 says that every moving
file a test, tool or check opens is first copied byte for byte to a fixture path, or
replaced by a slim extract that names its source's path and SHA-256, and its reader
is pointed there. This script is the one way those fixtures are made, so every one
of them has the same shape and the same proof of where it came from.

**Where a fixture lives.** Under ``tests/fixtures/evidence/``, at the evidence
file's own repository path: ``docs/handshake/artifactsround32/x.log`` becomes
``tests/fixtures/evidence/docs/handshake/artifactsround32/x.log``. A test names the
original path through ``tests/evidence_fixtures.py``, so the provenance stays
readable in the test and one place knows the layout.

Two kinds, told apart by a sidecar:

* **copy** -- the file byte for byte. Same bytes, same Git blob, so it costs the
  repository nothing.
* **extract** -- a smaller file made from it, with ``<name>.extract.json`` beside
  it recording the source's path, bytes and SHA-256 and what was taken out, with a
  count (CLAUDE.md: any elision is counted and marked). Two extractors exist:

  - ``slim-report``: a report JSON with ``debug.lines`` emptied. Those lines are the
    session log the report embeds, about 93 % of its bytes, and they are almost
    entirely cyanrip's progress line (TASKS R14).
  - ``slim-applog``: an application log with cyanrip's progress lines
    (``Ripping track N, progress - X%``) removed and one marker line appended.

``check`` verifies every fixture against its source: a copy must hash to the
source, an extract's sidecar must name the source's hash. The source is read from
the working tree while it is still there; after the move it is read from
``docs/evidence-manifest.tsv`` (HR-2 §4). A fixture whose source cannot be found
either way is refused, never passed.

    python3 scripts/evidence_fixtures.py copy docs/handshake/artifactsround32/a.log
    python3 scripts/evidence_fixtures.py slim-report docs/handshake/.../b.json
    python3 scripts/evidence_fixtures.py slim-applog docs/handshake/.../c.txt
    python3 scripts/evidence_fixtures.py check
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
FIXTURE_ROOT: Final[Path] = REPO_ROOT / "tests" / "fixtures" / "evidence"
MANIFEST: Final[Path] = REPO_ROOT / "docs" / "evidence-manifest.tsv"
SIDECAR_SUFFIX: Final[str] = ".extract.json"

#: cyanrip's progress line, as the app log and the report's debug block carry it.
#: Matched anywhere in the line, because the app log prefixes a timestamp and a
#: logger name (`... rip_worker: cyanrip │ Ripping track 3, progress - 40.59%`).
PROGRESS_LINE: Final[re.Pattern[str]] = re.compile(
    r"Ripping track \d+, progress - \d+(?:\.\d+)?%"
)


@dataclass(frozen=True)
class Source:
    """What we know of the evidence file a fixture was made from."""

    path: str
    sha256: str
    size: int


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _check_relative(original: str) -> str:
    """Refuse anything that is not a plain repository-relative path."""
    if original.startswith("/") or ".." in Path(original).parts:
        raise SystemExit(f"not a repository-relative path: {original!r}")
    return original


def fixture_path(original: str) -> Path:
    return FIXTURE_ROOT / _check_relative(original)


def sidecar_path(original: str) -> Path:
    path = fixture_path(original)
    return path.with_name(path.name + SIDECAR_SUFFIX)


def read_source(original: str) -> bytes:
    path = REPO_ROOT / _check_relative(original)
    if not path.is_file():
        raise SystemExit(
            f"{original}: not in the working tree. Make fixtures before the move."
        )
    return path.read_bytes()


def make_copy(original: str) -> Path:
    data = read_source(original)
    target = fixture_path(original)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    sidecar = sidecar_path(original)
    if sidecar.exists():
        sidecar.unlink()
    return target


def _write_extract(
    original: str, data: bytes, body: bytes, removed: str, count: int
) -> Path:
    target = fixture_path(original)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)
    record = {
        "source_path": original,
        "source_bytes": len(data),
        "source_sha256": sha256_of(data),
        "removed": removed,
        "removed_count": count,
        "made_by": "scripts/evidence_fixtures.py",
    }
    sidecar_path(original).write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return target


def make_slim_report(original: str) -> Path:
    """A report JSON with `debug.lines` emptied, the count kept beside it."""
    data = read_source(original)
    report = json.loads(data.decode("utf-8"))
    debug = report.get("debug")
    count = 0
    if isinstance(debug, dict) and isinstance(debug.get("lines"), list):
        count = len(debug["lines"])
        debug["lines"] = []
        debug["lines_removed_by_extract"] = count
    body = (json.dumps(report, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    return _write_extract(original, data, body, "debug.lines", count)


def make_slim_applog(original: str) -> Path:
    """An application log without cyanrip's progress lines, with one marker line."""
    data = read_source(original)
    text = data.decode("utf-8", errors="surrogateescape")
    kept: list[str] = []
    count = 0
    for line in text.splitlines(keepends=True):
        if PROGRESS_LINE.search(line):
            count += 1
            continue
        kept.append(line)
    if kept and not kept[-1].endswith("\n"):
        kept[-1] += "\n"
    kept.append(
        f"[evidence extract: {count} cyanrip progress line(s) removed from "
        f"{original}]\n"
    )
    body = "".join(kept).encode("utf-8", errors="surrogateescape")
    return _write_extract(original, data, body, "cyanrip progress lines", count)


def manifest_rows() -> dict[str, Source]:
    """The manifest's rows by path, or an empty map before the manifest exists."""
    if not MANIFEST.is_file():
        return {}
    rows: dict[str, Source] = {}
    with MANIFEST.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            rows[row["path"]] = Source(row["path"], row["sha256"], int(row["bytes"]))
    return rows


def source_of(original: str, manifest: dict[str, Source]) -> Source | None:
    """The source's hash: from the working tree if present, else the manifest."""
    path = REPO_ROOT / original
    if path.is_file():
        data = path.read_bytes()
        return Source(original, sha256_of(data), len(data))
    return manifest.get(original)


def fixtures() -> list[str]:
    """Every fixture, as the original path it stands for."""
    found: list[str] = []
    for path in sorted(FIXTURE_ROOT.rglob("*")):
        if not path.is_file() or path.name.endswith(SIDECAR_SUFFIX):
            continue
        found.append(path.relative_to(FIXTURE_ROOT).as_posix())
    return found


def check() -> list[str]:
    """Every problem with every fixture; an empty list means all verified."""
    manifest = manifest_rows()
    problems: list[str] = []
    for original in fixtures():
        source = source_of(original, manifest)
        if source is None:
            problems.append(
                f"{original}: its source is neither in the working tree nor in "
                "docs/evidence-manifest.tsv, so nothing can say what it was made from"
            )
            continue
        sidecar = sidecar_path(original)
        if sidecar.is_file():
            record = json.loads(sidecar.read_text(encoding="utf-8"))
            if record.get("source_sha256") != source.sha256:
                problems.append(
                    f"{original}: extract names source sha256 "
                    f"{record.get('source_sha256')}, the source is {source.sha256}"
                )
            if record.get("source_path") != original:
                problems.append(
                    f"{original}: extract names {record.get('source_path')}"
                )
            continue
        actual = sha256_of(fixture_path(original).read_bytes())
        if actual != source.sha256:
            problems.append(
                f"{original}: a copy must be byte for byte, but hashes {actual}, "
                f"the source {source.sha256}"
            )
    return problems


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("mode", choices=["copy", "slim-report", "slim-applog", "check"])
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args(argv)
    if args.mode == "check":
        problems = check()
        count = len(fixtures())
        for problem in problems:
            print(f"FAIL {problem}")
        print(f"{count} fixture(s) examined, {len(problems)} problem(s)")
        return 1 if problems or count == 0 else 0
    if not args.paths:
        parser.error(f"{args.mode} needs at least one path")
    make = {
        "copy": make_copy,
        "slim-report": make_slim_report,
        "slim-applog": make_slim_applog,
    }[args.mode]
    for original in args.paths:
        print(make(original).relative_to(REPO_ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
