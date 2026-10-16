"""Every relative link between the project's documents must resolve.

**Why this exists, and why it exists *before* a doc consolidation.** The docs are
heavily cross-referenced — a single guide is pointed at from a dozen places — and
until now nothing checked that any of those pointers landed. Renaming or merging a
document is therefore a silent-breakage operation: the prose still reads fine, the
link still looks like a link, and the reader finds nothing. `CLAUDE.md`'s own
companion-document list has already drifted from `docs/README.md` once (the
KDD-range mismatch, v23 vs v25), which is the same failure in the milder form
where the *text* went stale rather than the target vanishing.

So this is a gate, not a report: consolidating docs is only safe under it.

Scope, deliberately narrow so it cannot cry wolf:

* **Relative links only.** `http(s)` is not our problem — a network check in a
  unit suite is a flake generator, and an upstream URL rotting is not something a
  commit here can fix.
* **Anchors are checked as far as the file.** `foo.md#bar` must have a `foo.md`;
  whether `#bar` exists is a heading-slug question with several competing
  conventions (GitHub's differs from most renderers), and guessing wrong would
  make the gate wrong. Named as a limit rather than left implied.
* **Code fences are skipped.** A doc showing `[example](does-not-exist.md)` inside
  a fence is illustrating a link, not making one.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from conftest import repo_markdown_files

_REPO_ROOT = Path(__file__).resolve().parents[1]

#: A markdown inline link with a relative target: `[text](path)` or
#: `[text](path#anchor)`. Bounded quantifiers per the project rule. Excludes
#: absolute URLs, protocol-relative URLs, in-page anchors and `mailto:`.
_LINK = re.compile(r"\[[^\]]{0,300}\]\((?P<target>[^)\s#][^)\s]{0,300})\)")

#: Directories whose contents are not ours to police.
_SKIP_DIRS = frozenset({".git", ".pytest_cache", "node_modules", ".venv", "build"})

#: A link target we deliberately do not resolve, with the reason.
_EXTERNAL_PREFIXES = ("http://", "https://", "//", "mailto:", "tel:")


def _markdown_files() -> list[Path]:
    return [
        p
        for p in repo_markdown_files(_REPO_ROOT)
        if not _SKIP_DIRS & set(p.relative_to(_REPO_ROOT).parts)
    ]


def _strip_fences(text: str) -> str:
    """Blank out fenced code blocks, preserving line count.

    Line count is preserved so a future version of this test can report a line
    number that matches the file the reader opens.
    """
    out: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append("")
            continue
        out.append("" if in_fence else line)
    return "\n".join(out)


def _relative_links(path: Path) -> list[str]:
    text = _strip_fences(path.read_text(encoding="utf-8", errors="replace"))
    targets = []
    for match in _LINK.finditer(text):
        target = match.group("target")
        if target.startswith(_EXTERNAL_PREFIXES):
            continue
        targets.append(target)
    return targets


@pytest.mark.tree_walk  # HR-2 §2: sweeps whatever is filed
def test_every_relative_doc_link_resolves() -> None:
    """The gate. A link that points at nothing is worse than no link: it tells the
    reader the answer exists somewhere and then hides it."""
    broken: list[str] = []
    checked = 0
    for path in _markdown_files():
        for target in _relative_links(path):
            checked += 1
            # Anchors: check the file half only (see the module docstring).
            file_part = target.split("#", 1)[0]
            if not file_part:
                continue
            resolved = (path.parent / file_part).resolve()
            if not resolved.exists():
                broken.append(
                    f"{path.relative_to(_REPO_ROOT)} -> {target} "
                    f"(no such file: {file_part})"
                )
    # FLOOR. Without it this passes on a repo where the regex matched nothing —
    # a renamed capture group, a reflowed link style, an empty docs tree. The
    # count only ever grows; if it drops below this, the checker broke, not the
    # docs.
    assert checked >= 200, (
        f"only found {checked} relative links across {len(_markdown_files())} "
        "markdown files — the link regex has stopped matching, so this gate is "
        "passing by finding nothing"
    )
    assert not broken, "Broken relative links in the docs:\n  " + "\n  ".join(broken)


def test_the_checker_actually_catches_a_broken_link(tmp_path: Path) -> None:
    """A detector that cannot fail is decoration — proven against a constructed
    file rather than by reasoning about the regex."""
    doc = tmp_path / "a.md"
    doc.write_text(
        "See [the guide](guide.md) and [the missing one](nope.md).\n"
        "```\n[not a real link](also-missing.md)\n```\n",
        encoding="utf-8",
    )
    (tmp_path / "guide.md").write_text("hi", encoding="utf-8")

    targets = _relative_links(doc)
    assert "guide.md" in targets
    assert "nope.md" in targets
    # The fenced one must NOT be collected — it is an illustration.
    assert "also-missing.md" not in targets, (
        "a link inside a code fence was treated as a real link"
    )
    missing = [t for t in targets if not (doc.parent / t).exists()]
    assert missing == ["nope.md"]


def test_external_links_are_skipped_on_purpose() -> None:
    """Named as a decision, not left as an accident: a network check in a unit
    suite is a flake generator, and upstream URL rot is not fixable here."""
    doc = _REPO_ROOT / "README.md"
    text = doc.read_text(encoding="utf-8")
    assert "https://" in text, "README has no external links; this test is vacuous"
    assert not [t for t in _relative_links(doc) if t.startswith("http")]


def test_a_NESTED_CHECKOUT_is_not_part_of_this_tree(tmp_path: Path) -> None:
    """A git worktree inside the tree holds a `.git` FILE; its Markdown is another
    checkout's, and reading it as ours failed a doc gate on 2026-09-25 while agent
    worktrees sat under `.claude/worktrees/`."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "ours.md").write_text("x", encoding="utf-8")
    (tmp_path / "notes").mkdir()
    (tmp_path / "notes" / "also-ours.md").write_text("x", encoding="utf-8")
    nested = tmp_path / ".claude" / "worktrees" / "agent-x"
    (nested / "notes").mkdir(parents=True)
    (nested / ".git").write_text("gitdir: /elsewhere\n", encoding="utf-8")
    (nested / "notes" / "theirs.md").write_text("x", encoding="utf-8")
    (tmp_path / ".git" / "inside.md").write_text("x", encoding="utf-8")
    found = [p.relative_to(tmp_path).as_posix() for p in repo_markdown_files(tmp_path)]
    assert found == ["notes/also-ours.md", "ours.md"]


def test_a_directory_REMOVED_DURING_THE_WALK_is_skipped_not_fatal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """TASKS R18: a repository walk met `.hypothesis/tmp` just as a parallel xdist
    worker removed it, and `Path.rglob` raised `FileNotFoundError` (2026-10-15).

    This removes a directory for real, between the moment the walk lists the
    root and the moment it descends, by wrapping `os.scandir` (which both
    `os.walk` and `Path.rglob` call). The directory is not a tool cache, so the
    cache prune cannot be what saves the walk."""
    import os
    import shutil

    (tmp_path / "ours.md").write_text("x", encoding="utf-8")
    victim = tmp_path / "vanishing"
    victim.mkdir()
    (victim / "gone.md").write_text("x", encoding="utf-8")
    real_scandir = os.scandir
    removed: list[Path] = []
    listing: list[os.DirEntry[str]] = []

    class _Listed:
        """The root's listing, taken before the removal, as scandir returns it."""

        def __init__(self, entries: list[os.DirEntry[str]]) -> None:
            self._entries = iter(entries)

        def __iter__(self) -> _Listed:
            return self

        def __next__(self) -> os.DirEntry[str]:
            return next(self._entries)

        def __enter__(self) -> _Listed:
            return self

        def __exit__(self, *exc: object) -> None:
            return None

        def close(self) -> None:
            return None

    def scandir(path: object = ".") -> object:
        # `shutil.rmtree` lists by file descriptor; only the root is intercepted.
        if isinstance(path, int) or Path(os.fspath(path)) != tmp_path:  # type: ignore[call-overload]  # str or PathLike here
            return real_scandir(path)  # type: ignore[call-overload]  # as the caller passed
        if not removed:
            with real_scandir(path) as it:  # type: ignore[call-overload]  # as above
                listing.extend(it)
            shutil.rmtree(victim)
            removed.append(victim)
        # Every listing of the root is the one taken before the removal, as a
        # walker racing the deletion would see it: `Path.rglob` lists a directory
        # more than once, and a fresh second listing would hide the race.
        return _Listed(listing)

    monkeypatch.setattr(os, "scandir", scandir)
    found = [p.relative_to(tmp_path).as_posix() for p in repo_markdown_files(tmp_path)]

    assert removed == [victim]  # floor: the removal happened mid-walk
    assert found == ["ours.md"]


def test_tool_caches_are_not_part_of_the_walk(tmp_path: Path) -> None:
    """R18's other half: `.pytest_cache/README.md` is a tool's file, not ours."""
    (tmp_path / "ours.md").write_text("x", encoding="utf-8")
    for cache in (".hypothesis", ".pytest_cache", ".mypy_cache", ".ruff_cache"):
        (tmp_path / cache).mkdir()
        (tmp_path / cache / "README.md").write_text("x", encoding="utf-8")
    found = [p.relative_to(tmp_path).as_posix() for p in repo_markdown_files(tmp_path)]
    assert found == ["ours.md"]
