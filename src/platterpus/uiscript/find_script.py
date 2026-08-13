"""Resolve a script path the operator typed, tolerating separator style.

**The failure this exists for.** On 2026-08-13 a rig run was lost because the
file on disk was ``round08joint.txt`` and the command said
``round-08-joint.txt``. Both names refer to the same artifact; one is what the
cyanrip fork writes, the other is what this repository writes. A path is an
exact-match string, so the load failed — and (separately fixed) the app ran a
different script without saying so.

**Why normalise instead of legislating a convention.** A rule saying "always use
this spelling" binds only whoever last read it, and this artifact crosses two
repositories, a chat client and a file manager, each of which has renamed it at
least once. A rule cannot reach any of those. Comparing names with the
separators removed does, and it is symmetric: it works whichever convention
either side picks, today or later.

**What is deliberately NOT done here.** No fuzzy matching, no edit distance, no
"did you mean". Two names match only if they are identical once ASCII
non-alphanumerics are dropped and case is folded — so ``round08joint`` matches
``round-08-joint`` and ``Round_08_Joint``, and matches nothing else. And an
ambiguous result is a refusal, never a guess: silently picking one of two
candidates is how you get a confident transcript of the wrong file, which is the
defect this module was written to end rather than to relocate.
"""

from __future__ import annotations

import os
from pathlib import Path

#: Directories searched when the given path does not exist, in order, after the
#: directory the operator actually named. `~/Downloads` is first because that is
#: where a browser puts an attachment and where this artifact has been every
#: time it has gone missing.
FALLBACK_DIRS: tuple[str, ...] = ("~/Downloads", "~/Desktop", ".")

#: Suffixes a script may carry. Used only to widen the search when the operator
#: typed a bare name with no extension; an explicit extension is never ignored.
SCRIPT_SUFFIXES: tuple[str, ...] = (".txt", ".pscript")


def normalise(name: str) -> str:
    """A filename reduced to what both conventions agree on.

    Lowercase, ASCII alphanumerics only. ``"Round-08_Joint.TXT"`` and
    ``"round08joint.txt"`` both become ``"round08jointtxt"``.

    Non-ASCII characters are dropped rather than transliterated: this is a
    comparison key, not a name, and a key that depends on a Unicode table would
    make matching depend on the Python version.
    """
    return "".join(ch for ch in name.lower() if ch.isascii() and ch.isalnum())


def _candidates_in(directory: Path, key: str) -> list[Path]:
    """Every readable file in ``directory`` whose name normalises to ``key``."""
    try:
        entries = sorted(directory.iterdir())
    except OSError:
        return []  # unreadable or absent — not an error, just no candidates
    return [p for p in entries if p.is_file() and normalise(p.name) == key]


def resolve_script_path(raw: str) -> tuple[Path | None, str]:
    """Find the script the operator meant. Returns ``(path, explanation)``.

    ``path`` is ``None`` when nothing matched or when the match was ambiguous.
    ``explanation`` is always populated and always written for a person: on
    success it says whether the name was matched exactly or by normalisation and
    where; on failure it names every directory searched, so "not found" is a
    fact about a search rather than an assertion.

    Never raises. An unreadable directory contributes no candidates and is not
    an error — the operator asked about a file, not about a directory.
    """
    given = Path(os.path.expandvars(raw)).expanduser()

    if given.is_file():
        return given, f"found: {given}"

    # Bare name with no suffix: try the known suffixes before giving up on an
    # exact match, so `--run-script round08joint` works.
    if not given.suffix:
        for suffix in SCRIPT_SUFFIXES:
            candidate = given.with_name(given.name + suffix)
            if candidate.is_file():
                return candidate, f"found: {candidate} (added {suffix})"

    key = normalise(given.name)
    if not key:
        return None, f"{raw!r} does not name a file"

    # The directory the operator named comes first: if they pointed at a folder,
    # a match there is what they meant, even if a same-named file sits in
    # ~/Downloads too.
    searched: list[Path] = []
    ordered: list[Path] = [given.parent]
    ordered += [Path(d).expanduser().resolve() for d in FALLBACK_DIRS]

    for directory in ordered:
        if directory in searched:
            continue
        searched.append(directory)
        matches = _candidates_in(directory, key)
        if len(matches) == 1:
            found = matches[0]
            if found == given:
                return found, f"found: {found}"
            return found, (
                f"found: {found}\n"
                f"  (you typed {given.name!r}; matched {found.name!r} — same name "
                f"once separators and case are ignored)"
            )
        if len(matches) > 1:
            names = ", ".join(sorted(p.name for p in matches))
            return None, (
                f"{given.name!r} matches more than one file in {directory}: "
                f"{names}. Refusing to guess — name the one you mean exactly."
            )

    places = "\n".join(f"  {d}" for d in searched)
    return None, (
        f"no script matching {given.name!r} was found. Searched:\n{places}\n"
        f"  (matching ignores case and separators, so 'round-08-joint.txt' and "
        f"'round08joint.txt' are the same name here)"
    )
