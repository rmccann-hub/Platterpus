# SPDX-License-Identifier: GPL-3.0-only
"""Hostnames and the owner's name in evidence: found, replaced, counted (TASKS R16).

**Why this exists.** HR-2 point 9 says each side replaces home folders, the
hostname and the owner's real name "through its filing tool, counting each
replacement". Our export replaced home folders only (``export_redaction``) and
said "Hostnames and names are NOT replaced", so filing the 2026-10-14 run found
the hostname by a search and counted it in a README by hand.

**The fork's rules, so both projects replace the same strings**
(``cyanrip@957184d:tools/redact.py:26-38`` and ``:58-73``):

* **A hostname becomes** ``host``. It is not recognisable by its shape, so it is
  read from the material itself (the second field of a ``uname -a`` line,
  ``Linux <host> <release>``, and ``host:``/``hostname:``/``node:`` fields) and
  from this machine (``socket.gethostname()``). Never from a list in the
  repository: a list of the owner's hostnames is what the rule forbids. Each is
  replaced as a whole word with its short form before the first dot too.
* **The owner's real name becomes** ``the owner``, and only from a list kept
  OUTSIDE the repository: the file named by ``$PLATTERPUS_REDACT_NAMES``, else
  ``~/.config/platterpus/redact-names``, one name per line. Without one the name
  cannot be checked, and the record says so: *not checked* and *none found* are
  different claims.

Pure except :func:`this_machines_hostnames` and :func:`local_names`, which read
the machine and one file and never raise. Qt-free.
"""

from __future__ import annotations

import logging
import os
import re
import socket
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Final

log = logging.getLogger(__name__)

PLACEHOLDER_HOST: Final[str] = "host"
PLACEHOLDER_NAME: Final[str] = "the owner"

#: Where the owner's names are kept, outside every repository.
NAMES_ENV: Final[str] = "PLATTERPUS_REDACT_NAMES"
NAMES_FILE: Final[Path] = Path("~/.config/platterpus/redact-names")

#: ``Linux <host> <release>`` from ``uname -a``; the fork's ``UNAME``.
UNAME: Final[re.Pattern[str]] = re.compile(
    r"\b(?:Linux|Darwin|FreeBSD)\s+([A-Za-z0-9][A-Za-z0-9._-]*)\s+\d+\.\d+"
)
#: A ``host:`` / ``hostname:`` / ``node:`` field; the fork's ``HOST_FIELD``.
HOST_FIELD: Final[re.Pattern[str]] = re.compile(
    r"^\s*\"?(?:host|hostname|node)\"?\s*[:=]\s*\"?([A-Za-z0-9][A-Za-z0-9._-]*)\"?\s*$",
    re.M | re.I,
)

#: Names every machine answers to, which identify nobody.
NOT_PERSONAL: Final[frozenset[str]] = frozenset(
    {PLACEHOLDER_HOST, "localhost", "localhost.localdomain"}
)


def hostnames_in(text: str) -> set[str]:
    """The hostnames the material names about itself. Pure."""
    found = set(UNAME.findall(text)) | set(HOST_FIELD.findall(text))
    return {h for h in found if h.lower() not in NOT_PERSONAL}


def this_machines_hostnames() -> list[str]:
    """This machine's hostname, or none. Never raises."""
    try:
        name = socket.gethostname().strip()
    except OSError:
        log.warning("could not read this machine's hostname", exc_info=True)
        return []
    return [name] if name and name.lower() not in NOT_PERSONAL else []


def local_names(path: Path | None = None) -> list[str] | None:
    """The owner's names from the list outside the repository, or ``None``.

    ``None`` is "not checked" (there is no list); ``[]`` is a list with no names.
    Never raises: an unreadable list is "not checked", and the log says why.
    """
    where = path or Path(os.environ.get(NAMES_ENV) or NAMES_FILE).expanduser()
    if not where.is_file():
        return None
    try:
        text = where.read_text(encoding="utf-8", errors="replace")
    except OSError:
        log.warning("could not read the redaction name list", exc_info=True)
        return None
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _forms(host: str) -> list[str]:
    """A hostname and its short form, longest first, so the full name goes whole."""
    forms = {host}
    short = host.split(".")[0]
    if short:
        forms.add(short)
    return sorted(forms, key=len, reverse=True)


def host_patterns(hosts: Iterable[str]) -> list[re.Pattern[str]]:
    """Whole-word patterns for each hostname and its short form. Pure."""
    usable = {h for h in hosts if h and h.lower() not in NOT_PERSONAL}
    return [
        re.compile(r"(?:(?<=\\[nrt])|(?<![\w.-]))" + re.escape(form) + r"(?![\w-])")
        for host in sorted(usable, key=len, reverse=True)
        for form in _forms(host)
    ]


def name_patterns(names: Sequence[str] | None) -> list[re.Pattern[str]]:
    """Whole-word patterns for each of the owner's names, longest first. Pure."""
    return [
        re.compile(r"\b" + re.escape(name) + r"\b")
        for name in sorted({n for n in names or () if n}, key=len, reverse=True)
    ]


def replace_identity(
    line: str,
    hosts: Sequence[re.Pattern[str]],
    names: Sequence[re.Pattern[str]],
) -> tuple[str, int, int]:
    """``(line with hostnames and names replaced, hosts replaced, names replaced)``."""
    host_count = name_count = 0
    for pattern in hosts:
        line, n = pattern.subn(PLACEHOLDER_HOST, line)
        host_count += n
    for pattern in names:
        line, n = pattern.subn(PLACEHOLDER_NAME, line)
        name_count += n
    return line, host_count, name_count


def names_status(names: Sequence[str] | None, replaced: int) -> str:
    """How a record states the name check: a count, or that it was not made."""
    if names is None:
        return "names not checked (no list outside the repository)"
    return f"{replaced} name(s) replaced"
