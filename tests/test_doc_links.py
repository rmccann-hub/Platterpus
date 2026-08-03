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
    return sorted(
        p
        for p in _REPO_ROOT.rglob("*.md")
        if not _SKIP_DIRS & set(p.relative_to(_REPO_ROOT).parts)
    )


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
