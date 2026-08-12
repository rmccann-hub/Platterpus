"""No user-facing string may hardcode how to run Platterpus.

**The bug.** Six strings across five modules told the user to run
``platterpus --something`` (and one, ``./platterpus-x86_64.AppImage --audit-rips``).
Each is correct for exactly one distribution channel and produces
``bash: platterpus: command not found`` on the other. The AppImage is this
project's **primary** channel and puts nothing on ``PATH``, so the majority of
users were being handed a command that cannot work — including the update
dialog's ``platterpus --install-ripper <sha>``, which the cyanrip fork reported
as *"the only thing that has actually blocked the operator, twice"* (round 8
lap 7 §H).

**Why a sweep and not five fixes.** The fork found *one* instance. Searching for
the shape found *six*. That is the `CLAUDE.md` rule about enforcing a rule across
the codebase rather than at the place it was learned: a per-site fix leaves the
seventh free to appear, and it would appear in a release note or an error path —
somewhere nobody exercises until a user is already stuck.

**Why the detector is trusted.** It is not argued from, it is *measured*: the
sweep is run against the strings as they actually stood before the fix and must
find every one. A detector verified only against the fixed tree cannot be told
apart from one that matches nothing (`CLAUDE.md`: *can this check be satisfied by
finding nothing?*), and a hand-written decoy would only prove it catches the
string I chose to write.

The corpus is a committed fixture rather than a `git show HEAD~1`, because CI's
`test` job checks out at depth 1 and a history-reading revert-proof would
silently `skip` there — a skip in the one job that gates every merge. It is not a
hand-made stand-in: `tests/data/hardcoded_invocations_prefix.json` was *generated*
from the pre-fix blobs, records the commit it came from, and holds the excerpts
verbatim.

Docstrings and comments are exempt on purpose. This file's own prose, and
`build_info.self_invocation`'s explanation of the bug, both have to be able to
quote the broken form.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

from platterpus import build_info, help_content

SRC = Path(__file__).resolve().parent.parent / "src" / "platterpus"

#: The shape of a hardcoded invocation: an optional ``./``, the program name in
#: either of its two spellings, whitespace, then a flag. The lookbehind keeps it
#: off ``~/.local/bin/platterpus --`` style *paths* and off ``.platterpus.json``,
#: which are not instructions to type something.
HARDCODED = re.compile(r"(?<![\w./-])(?:\./)?platterpus(?:-x86_64\.AppImage)?\s+--")

#: Verbatim excerpts of every string the fix removed, generated from the pre-fix
#: blobs. Five files, seven instances — the guide held three of them.
PREFIX_CORPUS = (
    Path(__file__).resolve().parent / "data" / "hardcoded_invocations_prefix.json"
)


def _docstring_nodes(tree: ast.Module) -> set[int]:
    """`id()` of every string node that is a module/class/function docstring."""
    found: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(
            node, ast.Module | ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
        ):
            if ast.get_docstring(node, clean=False) is not None:
                first = node.body[0]
                assert isinstance(first, ast.Expr)
                found.add(id(first.value))
    return found


def _hardcoded_invocations(source: str, label: str) -> list[str]:
    """Every non-docstring string literal in ``source`` that hardcodes a command.

    Returns one human-readable hit per match, with surrounding text, so a failure
    names the string rather than only the file.
    """
    tree = ast.parse(source, filename=label)
    docstrings = _docstring_nodes(tree)
    hits: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        if id(node) in docstrings:
            continue
        for match in HARDCODED.finditer(node.value):
            excerpt = node.value[max(0, match.start() - 30) : match.end() + 40]
            hits.append(f"{label}:{node.lineno}: ...{excerpt.strip()!r}...")
    return hits


class TestTheSweep:
    def test_no_module_hardcodes_an_invocation(self) -> None:
        """The rule itself, over the whole package."""
        modules = sorted(SRC.rglob("*.py"))
        # The floor. Without it a broken glob (a renamed src layout, a bad
        # resolve()) turns this into a test that passes by examining nothing.
        assert len(modules) >= 120, (
            f"only {len(modules)} modules found under {SRC} — the sweep is not "
            "reaching the package, so a clean result means nothing"
        )
        hits: list[str] = []
        for path in modules:
            hits += _hardcoded_invocations(
                path.read_text(encoding="utf-8"), str(path.relative_to(SRC.parent))
            )
        assert not hits, (
            "user-facing strings hardcode how to run Platterpus; there is no "
            "`platterpus` on PATH for an AppImage install. Use "
            "`build_info.self_invocation()`:\n  " + "\n  ".join(hits)
        )

    def test_the_sweep_finds_every_instance_it_was_written_for(self) -> None:
        """The revert-proof, against the real pre-fix strings rather than a decoy.

        A detector that matches nothing passes the test above perfectly. This one
        fails unless the pattern still fires on every string the fix removed —
        each excerpt checked individually, so a weakening that blinds it to one
        shape (the ``./platterpus-x86_64.AppImage`` spelling, say) is named rather
        than absorbed by the other six.
        """
        corpus = json.loads(PREFIX_CORPUS.read_text(encoding="utf-8"))
        instances = corpus["instances"]
        assert len(instances) == 7, (
            "the pre-fix corpus has been edited; it is a record of what was "
            f"there, not a knob — {len(instances)} rows, expected 7"
        )
        missed = [
            f"{row['file']}:{row['line']}: {row['excerpt']!r}"
            for row in instances
            if not HARDCODED.search(row["excerpt"])
        ]
        assert not missed, (
            "the sweep no longer detects instances it was written for — it has "
            "been weakened:\n  " + "\n  ".join(missed)
        )

    def test_a_docstring_may_still_describe_the_broken_form(self) -> None:
        """The exemption is deliberate and needs to hold: `self_invocation`'s own
        docstring quotes the bug, and a sweep that banned that would push the
        explanation out of the code."""
        source = '''\
"""Says platterpus --compare in a docstring, which is fine."""
X = "and platterpus --compare in a string, which is not"
'''
        hits = _hardcoded_invocations(source, "<synthetic>")
        assert len(hits) == 1, f"expected exactly the string literal, got {hits}"
        assert "which is not" in hits[0]


class TestTheGuideRendersForThisInstall:
    def test_the_raw_guide_carries_the_token_not_a_program_name(self) -> None:
        assert help_content.INVOCATION_TOKEN in help_content.USER_GUIDE
        assert not HARDCODED.search(help_content.USER_GUIDE)

    def test_rendering_substitutes_and_leaves_no_token_behind(self) -> None:
        rendered = help_content.user_guide()
        assert help_content.INVOCATION_TOKEN not in rendered, (
            "the guide shipped its placeholder to the user"
        )
        assert "--compare previous.platterpus.json" in rendered

    def test_an_appimage_reader_gets_the_appimage_path(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The whole point. Under $APPIMAGE the copyable line must be the file
        that is actually running, not a name with nothing behind it."""
        monkeypatch.setenv(
            "APPIMAGE", "/home/u/Applications/platterpus-x86_64.AppImage"
        )
        rendered = help_content.user_guide()
        assert "/home/u/Applications/platterpus-x86_64.AppImage --compare" in rendered
        assert "\n    platterpus --" not in rendered

    def test_the_help_dialog_renders_rather_than_dumping_the_constant(self) -> None:
        """Revert-proof for the wiring: substituting in a function nobody calls
        would leave the placeholder on screen and the bug in place."""
        import inspect

        from platterpus.ui.help_dialogs import HelpDialog

        src = inspect.getsource(HelpDialog._guide_markdown)
        assert "help_content.user_guide()" in src
        assert "help_content.USER_GUIDE" not in src


class TestSelfInvocation:
    def test_no_appimage_means_the_name_on_path(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("APPIMAGE", raising=False)
        assert build_info.self_invocation() == "platterpus"

    def test_a_path_with_spaces_is_quoted(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An unquoted path with a space is a second broken command, not a
        working one — and an AppImage very often lives under a folder the user
        named themselves."""
        monkeypatch.setenv("APPIMAGE", "/home/u/My Apps/platterpus.AppImage")
        assert build_info.self_invocation() == '"/home/u/My Apps/platterpus.AppImage"'

    def test_an_empty_appimage_var_is_not_an_appimage(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An exported-but-empty variable would otherwise render as an empty
        command — worse than the wrong name, because it looks like a typo in the
        guide rather than a wrong install."""
        monkeypatch.setenv("APPIMAGE", "")
        assert build_info.self_invocation() == "platterpus"
