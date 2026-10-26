#!/usr/bin/env python3
"""File an acceptance run's bundle as evidence: stage, verify, redact, count (R16).

**Why this exists.** HR-2 point 9 says each side replaces home folders, the
hostname and the owner's real name "through its filing tool, counting each
replacement", and verifies self-verifying logs first, recording the result and
both hashes. Filing the 2026-10-14 and 2026-10-16 runs did that with scripts
written in the session scratchpad, a search for the hostname, and counts typed
into a README. This is the committed tool. It never pushes.

    python3 scripts/evidence_file.py stage <unpacked bundle> <out dir> --prefix round35full
    python3 scripts/evidence_file.py commit <out dir> --clone <clone> \\
        --folder docs/handshake/artifactsround35 --parent <evidence tip> --date <ISO>

``stage`` copies every member it has a name for into ``<out dir>`` as
``<prefix><name>``: HR-2's ASCII-only names, a member it cannot name refused
rather than guessed. Then, per member:

* a **signed log** (cyanrip's ``Log FUN512:``, our EAC-compatible log's SHA-256
  footer) is verified **before** anything, and kept byte for byte: replacing a
  path in it would make a genuine log fail its own check. Its result and hash
  are recorded, with what it still names;
* any other text member has home folders, hostnames and the owner's names
  replaced (``export_redaction.redact_all``), each counted, with the hash before
  and after.

``FILING.tsv`` in ``<out dir>`` is the record: one row per member. ``commit``
builds the evidence commit in an existing clone with git's plumbing (identity
``evidence <evidence@invalid>``, the given date in all six variables), prints
its ID, and writes ``manifest-rows.tsv`` for ``docs/evidence-manifest.tsv``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import re
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evidence_names import SAFE_NAME, skip_reason, staged_name  # noqa: E402

from platterpus import fun512  # noqa: E402
from platterpus.eac_log_export import verify_eac_style_log_checksum  # noqa: E402
from platterpus.export_identity import (  # noqa: E402
    local_names,
    names_status,
    this_machines_hostnames,
)
from platterpus.export_redaction import (  # noqa: E402
    KEPT_CYANRIP_SIGNED,
    KEPT_PLATTERPUS_CHECKSUM,
    redact_all,
    signed_reason,
    this_machines_homes,
)


@dataclass(frozen=True)
class Filed:
    """One staged member and what was done to it."""

    name: str
    source: str
    sha256_before: str
    sha256_after: str
    verification: str
    homes: int = 0
    hosts: int = 0
    names: int = 0


def verification(data: bytes) -> str:
    """A signed log's verdict, or ``""`` for a member that is not one.

    Whether a member IS a signed log is the export's own question, asked of it
    (``export_redaction.signed_reason``, by content: a ``Log FUN512:`` LINE, not
    the mark quoted inside a report's JSON), so filing and export cannot disagree.
    """
    text = data.decode("utf-8", "surrogateescape")
    reason = signed_reason(text)
    if reason == KEPT_CYANRIP_SIGNED:
        return f"cyanrip FUN512 {fun512.verify(data)}"
    if reason == KEPT_PLATTERPUS_CHECKSUM:
        footer = verify_eac_style_log_checksum(text)
        return f"platterpus SHA-256 footer {'valid' if footer else 'mismatch'}"
    return ""


def stage(
    raw: Path,
    out: Path,
    prefix: str,
    *,
    homes: Sequence[str],
    hosts: Sequence[str],
    names: Sequence[str] | None,
) -> tuple[list[Filed], list[tuple[str, str]]]:
    """Copy, verify and redact every member. Refuses an unnamed member."""
    out.mkdir(parents=True, exist_ok=False)
    filed: list[Filed] = []
    skipped: list[tuple[str, str]] = []
    for path in sorted(p for p in raw.rglob("*") if p.is_file()):
        rel = path.relative_to(raw).as_posix()
        reason = skip_reason(rel)
        if reason:
            skipped.append((rel, reason))
            continue
        name = staged_name(rel)
        if name is None:
            raise SystemExit(
                f"no filed name for {rel!r}: add it, or skip it on purpose"
            )
        dest = out / f"{prefix}{name}"
        if not SAFE_NAME.fullmatch(dest.name) or dest.exists():
            raise SystemExit(f"{rel!r} maps to {dest.name!r}, unsafe or already taken")
        data = path.read_bytes()
        filed.append(
            file_member(data, dest, rel, homes=homes, hosts=hosts, names=names)
        )
    return filed, skipped


#: The verified-read chase's record (TASKS R7, ``verified_read_chase.py``): per
#: attempt, a header and our argv line, then that attempt's whole cyanrip log.
#: Several signed logs in one file verify as none of them, so it is filed as
#: what it is, a wrapper: each embedded log is verified and kept byte for byte,
#: and only the lines between them are redacted and counted. Found filing the
#: 2026-10-22 11:45 UTC run, whose argv lines named the rig's home folder.
_CHASE_WRAPPER: Final[re.Pattern[str]] = re.compile(
    r"\A=== Platterpus verified-read chase: track \d{1,2}, attempt \d{1,2} ===\n"
)
#: One embedded cyanrip log: its banner line through its `Log FUN512:` line.
_EMBEDDED_LOG: Final[re.Pattern[str]] = re.compile(
    r"^cyanrip \S{1,80} \([^)\n]{1,120}\)\n(?:(?!Log FUN512: )[^\n]*\n){0,20000}"
    r"Log FUN512: \S{1,200}\n",
    re.M,
)


def _file_chase_wrapper(
    data: bytes,
    text: str,
    dest: Path,
    rel: str,
    *,
    homes: Sequence[str],
    hosts: Sequence[str],
    names: Sequence[str] | None,
) -> Filed:
    """Verify each embedded log, keep it as written, and redact what is around it."""
    before = hashlib.sha256(data).hexdigest()
    pieces: list[str] = []
    verdicts: list[str] = []
    counts = [0, 0, 0]
    at = 0

    def redact(chunk: str) -> str:
        done = redact_all(chunk, homes=homes, hosts=hosts, names=names)
        counts[0] += done.homes
        counts[1] += done.hosts
        counts[2] += done.names
        return done.text

    for match in _EMBEDDED_LOG.finditer(text):
        pieces.append(redact(text[at : match.start()]))
        segment = match.group(0)
        verdicts.append(fun512.verify(segment.encode("utf-8", "surrogateescape")))
        pieces.append(segment)
        at = match.end()
    pieces.append(redact(text[at:]))
    new = "".join(pieces).encode("utf-8", "surrogateescape")
    dest.write_bytes(new)
    valid = sum(1 for v in verdicts if v == "valid")
    verdict = (
        f"verified-read wrapper: {len(verdicts)} embedded cyanrip log(s), "
        f"{valid} FUN512 valid"
    )
    if valid != len(verdicts) or not verdicts:
        verdict += f", mismatch in {len(verdicts) - valid}"
    return Filed(
        dest.name,
        rel,
        before,
        hashlib.sha256(new).hexdigest(),
        verdict,
        counts[0],
        counts[1],
        counts[2],
    )


def file_member(
    data: bytes,
    dest: Path,
    rel: str,
    *,
    homes: Sequence[str],
    hosts: Sequence[str],
    names: Sequence[str] | None,
) -> Filed:
    """Verify first; then keep a signed log as written, or redact and count."""
    text = data.decode("utf-8", "surrogateescape")
    if _CHASE_WRAPPER.match(text):
        return _file_chase_wrapper(
            data, text, dest, rel, homes=homes, hosts=hosts, names=names
        )
    before = hashlib.sha256(data).hexdigest()
    verdict = verification(data)
    done = redact_all(text, homes=homes, hosts=hosts, names=names)
    if verdict:
        dest.write_bytes(data)
        left = f"; still names {done.homes} home, {done.hosts} host, {done.names} name"
        return Filed(dest.name, rel, before, before, verdict + left)
    new = done.text.encode("utf-8", "surrogateescape")
    dest.write_bytes(new)
    return Filed(
        dest.name,
        rel,
        before,
        hashlib.sha256(new).hexdigest(),
        "unsigned",
        done.homes,
        done.hosts,
        done.names,
    )


def write_record(
    out: Path,
    filed: Sequence[Filed],
    skipped: Sequence[tuple[str, str]],
    names_checked: bool,
) -> str:
    """``FILING.tsv`` beside the staged files, and a one-line summary."""
    with (out.parent / f"{out.name}-FILING.tsv").open(
        "w", newline="", encoding="utf-8"
    ) as fh:
        rows = csv.writer(fh, delimiter="\t", lineterminator="\n")
        rows.writerow(
            [
                "file",
                "source",
                "sha256 before",
                "sha256 after",
                "verification",
                "homes",
                "hosts",
                "names",
            ]
        )
        for f in filed:
            rows.writerow(
                [
                    f.name,
                    f.source,
                    f.sha256_before,
                    f.sha256_after,
                    f.verification,
                    f.homes,
                    f.hosts,
                    f.names,
                ]
            )
        for rel, why in skipped:
            rows.writerow(["", rel, "", "", f"skipped: {why}", "", "", ""])
    names = sum(f.names for f in filed)
    return (
        f"filed {len(filed)}, skipped {len(skipped)}; replaced "
        f"{sum(f.homes for f in filed)} home path(s), {sum(f.hosts for f in filed)} "
        f"hostname(s), {names_status(None if not names_checked else [], names)}"
    )


def commit(clone: Path, out: Path, folder: str, parent: str, date: str) -> str:
    """Build the evidence commit with plumbing in a temporary index; never pushes."""
    env = dict(os.environ, GIT_INDEX_FILE=str(clone / ".git" / "evidence-file-index"))
    for role in ("AUTHOR", "COMMITTER"):
        env[f"GIT_{role}_NAME"] = "evidence"
        env[f"GIT_{role}_EMAIL"] = "evidence@invalid"
        env[f"GIT_{role}_DATE"] = date

    def git(*args: str, data: bytes | None = None) -> str:
        done = subprocess.run(
            ["git", "-C", str(clone), *args],
            env=env,
            input=data,
            capture_output=True,
            check=True,
        )
        return done.stdout.decode().strip()

    git("read-tree", parent)
    for path in sorted(out.iterdir()):
        blob = git("hash-object", "-w", "--stdin", data=path.read_bytes())
        git(
            "update-index",
            "--add",
            "--cacheinfo",
            f"100644,{blob},{folder}/{path.name}",
        )
    tree = git("write-tree")
    message = f"Evidence: {folder}, {len(list(out.iterdir()))} files\n".encode()
    sha = git("commit-tree", tree, "-p", parent, "-F", "-", data=message)
    rows = [
        f"{folder}/{p.name}\t{p.stat().st_size}\t{hashlib.sha256(p.read_bytes()).hexdigest()}\t{sha}\t"
        for p in sorted(out.iterdir())
    ]
    (out.parent / f"{out.name}-manifest-rows.tsv").write_text(
        "\n".join(rows) + "\n", encoding="utf-8"
    )
    return sha


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    sub = parser.add_subparsers(dest="mode", required=True)
    s = sub.add_parser("stage")
    s.add_argument("raw", type=Path)
    s.add_argument("out", type=Path)
    s.add_argument("--prefix", required=True)
    s.add_argument(
        "--host", action="append", default=[], help="a hostname to replace too"
    )
    s.add_argument(
        "--names", type=Path, help="the owner's names, kept outside the repository"
    )
    c = sub.add_parser("commit")
    c.add_argument("out", type=Path)
    c.add_argument("--clone", type=Path, required=True)
    c.add_argument("--folder", required=True)
    c.add_argument("--parent", required=True)
    c.add_argument("--date", required=True)
    args = parser.parse_args(argv)
    if args.mode == "stage":
        if not SAFE_NAME.fullmatch(args.prefix):
            parser.error("--prefix must be ASCII letters and digits")
        names = local_names(args.names)
        filed, skipped = stage(
            args.raw,
            args.out,
            args.prefix,
            homes=this_machines_homes(),
            hosts=[*this_machines_hostnames(), *args.host],
            names=names,
        )
        print(write_record(args.out, filed, skipped, names is not None))
        bad = [
            f
            for f in filed
            if "mismatch" in f.verification or "trailing" in f.verification
        ]
        for f in bad:
            print(f"SIGNATURE FAILS: {f.name}: {f.verification}", file=sys.stderr)
        return 1 if bad else 0
    print(commit(args.clone, args.out, args.folder.rstrip("/"), args.parent, args.date))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
