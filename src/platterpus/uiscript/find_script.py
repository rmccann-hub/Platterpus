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

**The copy shipped inside the app is searched LAST, never first.** The rig
scripts live in the package (``rig_scripts/``) so an AppImage user can type
``--run-script fullacceptance`` with nothing downloaded. But an operator who
fetched a newer script must still win over the one baked into their build — a
packaged copy that quietly beat their download would be exactly the "ran a
different script without saying so" defect above, moved one directory over. So
it is the final fallback, and every answer says which copy it is: the packaged
one, or the operator's own — and, when theirs wins, that a packaged copy of the
same name exists and whether the two differ.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final

#: Directories searched when the given path does not exist, in order, after the
#: directory the operator actually named. `~/Downloads` is first because that is
#: where a browser puts an attachment and where this artifact has been every
#: time it has gone missing. The scripts packaged inside the app
#: (:func:`packaged_scripts_dir`) are searched after all of these, never before.
FALLBACK_DIRS: tuple[str, ...] = ("~/Downloads", "~/Desktop", ".")

#: Suffixes a script may carry. Used only to widen the search when the operator
#: typed a bare name with no extension; an explicit extension is never ignored.
SCRIPT_SUFFIXES: tuple[str, ...] = (".txt", ".pscript")

#: The directory, *inside the package*, holding the scripts this build ships.
#: The one home of the name: `test_session.BUILTIN_SCRIPT_DIR_NAME` (the Tools →
#: Advanced → Run acceptance test… route) is this constant, so the menu and `--run-script`
#: cannot name two different directories. `pyproject.toml`'s package-data entry
#: is what puts the files there.
PACKAGED_SCRIPT_DIR_NAME: Final[str] = "rig_scripts"


def packaged_scripts_dir() -> Path:
    """Where the scripts shipped inside this build live. PURE — no disk access.

    Answers even when the directory is missing (a build whose package-data entry
    was dropped), so a "not found" can still name the place it looked.
    """
    return Path(__file__).resolve().parent.parent / PACKAGED_SCRIPT_DIR_NAME


def is_packaged_copy(path: Path) -> bool:
    """Whether ``path`` is one of the scripts shipped inside this build.

    Compared by resolved directory, not by name: the operator's own
    ``~/Downloads/fullacceptance.txt`` has the same name as the packaged one and
    is precisely the file that must NOT be reported as packaged. Never raises —
    a path that cannot be resolved is not the packaged copy.
    """
    try:
        return path.resolve().parent == packaged_scripts_dir().resolve()
    except (OSError, RuntimeError):  # RuntimeError: a symlink loop
        return False


def normalise(name: str) -> str:
    """A filename reduced to what both conventions agree on.

    Lowercase, ASCII alphanumerics only. ``"Round-08_Joint.TXT"`` and
    ``"round08joint.txt"`` both become ``"round08jointtxt"``.

    Non-ASCII characters are dropped rather than transliterated: this is a
    comparison key, not a name, and a key that depends on a Unicode table would
    make matching depend on the Python version.
    """
    return "".join(ch for ch in name.lower() if ch.isascii() and ch.isalnum())


def _resolved(directory: Path) -> Path:
    """``directory`` made absolute, or as given if that fails (never raises)."""
    try:
        return directory.resolve()
    except (OSError, RuntimeError):  # RuntimeError: a symlink loop
        return directory


def _candidates_in(directory: Path, keys: frozenset[str]) -> list[Path]:
    """Every readable file in ``directory`` whose name normalises to one of ``keys``."""
    try:
        entries = sorted(directory.iterdir())
    except OSError:
        return []  # unreadable or absent — not an error, just no candidates
    return [p for p in entries if p.is_file() and normalise(p.name) in keys]


def _keys_for(name: str, *, bare: bool) -> frozenset[str]:
    """The comparison keys a typed name matches.

    A name typed WITH a suffix matches only itself. A **bare** name also matches
    itself plus each :data:`SCRIPT_SUFFIXES` suffix — in every directory searched,
    not only the current one. That last part is what keeps the precedence honest:
    if only the packaged directory widened a bare name, `--run-script
    fullacceptance` would skip the operator's own `~/Downloads/fullacceptance.txt`
    and run the packaged copy instead, which is the defect the ordering exists to
    prevent. Two files in one directory that both match (`x.txt` and `x.pscript`)
    are still a refusal, like any other ambiguity.
    """
    key = normalise(name)
    if not key or not bare:
        return frozenset({key}) if key else frozenset()
    return frozenset({key, *(key + normalise(suffix) for suffix in SCRIPT_SUFFIXES)})


def _what_differed(typed: str, found: str) -> str:
    """What separates the name typed from the name matched, said as it happened.

    A bare name widened with a suffix is "added .txt"; one that differed only in
    separators or case is said so; both, when both. This used to say "same name
    once separators and case are ignored" for every match that was not identical,
    so `--run-script fullacceptance` reaching `fullacceptance.txt` reported a
    normalisation that never took place (review R11, 2026-09-28): a false note
    about a true result, in the module whose job is saying which file ran and why.
    """
    added = next(
        (
            suffix
            for suffix in SCRIPT_SUFFIXES
            if not Path(typed).suffix
            and found.lower().endswith(suffix)
            and normalise(found[: -len(suffix)]) == normalise(typed)
        ),
        None,
    )
    if added is None:
        return "same name once separators and case are ignored"
    written = found[-len(added) :]  # the suffix as it is spelled on disk
    if found[: -len(added)] == typed:
        return f"added {written}"
    return f"added {written}, and the same name once separators and case are ignored"


def _which_copy(found: Path, keys: frozenset[str]) -> str:
    """One line saying which copy ``found`` is — the packaged one, or yours.

    Always part of a success answer. When the operator's copy wins and the build
    also ships a script of the same name, say so and say whether the two differ:
    a stale download beating a newer packaged script is the one outcome of this
    ordering that nobody would otherwise see.
    """
    if is_packaged_copy(found):
        return "  (this is the copy packaged inside this Platterpus build)"
    shipped = _candidates_in(packaged_scripts_dir(), keys)
    if len(shipped) != 1:
        return "  (this is your copy, not one packaged inside Platterpus)"
    try:
        same = found.read_bytes() == shipped[0].read_bytes()
    except OSError as exc:
        verdict = f"could not compare the two: {exc}"
    else:
        verdict = "identical to it" if same else "DIFFERENT from it"
    return (
        f"  (this is your copy, not the one packaged inside Platterpus at "
        f"{shipped[0]} — yours wins because it was found first; it is {verdict})"
    )


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
    keys = _keys_for(given.name, bare=not given.suffix)

    if given.is_file():
        return given, f"found: {given}\n{_which_copy(given, keys)}"

    # Bare name with no suffix: try the known suffixes before giving up on an
    # exact match, so `--run-script round08joint` works.
    if not given.suffix:
        for suffix in SCRIPT_SUFFIXES:
            candidate = given.with_name(given.name + suffix)
            if candidate.is_file():
                return candidate, (
                    f"found: {candidate} (added {suffix})\n"
                    f"{_which_copy(candidate, keys)}"
                )

    if not keys:
        return None, f"{raw!r} does not name a file"

    # The directory the operator named comes first: if they pointed at a folder,
    # a match there is what they meant, even if a same-named file sits in
    # ~/Downloads too. The packaged directory comes LAST (module docstring).
    # Resolved, like the fallbacks, so the check below sees that a bare name's
    # parent `.` and the fallback `.` are one directory. Unresolved, the current
    # directory was searched twice and listed twice in the answer (review R11).
    searched: list[Path] = []
    ordered: list[Path] = [_resolved(given.parent)]
    ordered += [_resolved(Path(d).expanduser()) for d in FALLBACK_DIRS]
    ordered.append(packaged_scripts_dir())

    for directory in ordered:
        if directory in searched:
            continue
        searched.append(directory)
        matches = _candidates_in(directory, keys)
        if len(matches) == 1:
            found = matches[0]
            copy = _which_copy(found, keys)
            if is_packaged_copy(found) and len(searched) > 1:
                # Reached by falling through every other place: say which, so
                # "it used the packaged copy" arrives with its reason attached.
                earlier = ", ".join(str(d) for d in searched[:-1])
                copy += f"\n  (nothing matching was found first in: {earlier})"
            if found == given or found.name == given.name:
                # Same name, found by searching rather than where it was typed:
                # nothing was normalised, so saying "matched" would be a false
                # note about a true result.
                return found, f"found: {found}\n{copy}"
            return found, (
                f"found: {found}\n"
                f"  (you typed {given.name!r}; matched {found.name!r} — "
                f"{_what_differed(given.name, found.name)})\n{copy}"
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
