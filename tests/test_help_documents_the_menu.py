"""Every Tools action a person can click is findable in the in-app User Guide.

**Why this file exists.** v0.6.32 shipped **Tools → Run acceptance test…** — the
one-click replacement for three bash scripts, and the answer to the maintainer's
*"this was supposed to be a no cli program"* — and `help_content.py` did not
mention it. Zero occurrences of the word "acceptance". The Guide's testing
section still walked the reader to `Tools → Run test script…` and then to
`--rig-session FOLDER`, a **command line**, as the way to run an unattended
hardware session.

So the feature built to remove the terminal was undiscoverable from inside the
product, and the only route the product documented was the terminal one. Nothing
was broken; a user simply could not find it.

Found 2026-09-01 by an audit lens asking *"is the in-app path documented AT ALL
in the user-facing help?"* — a question no existing test asked, because every
help test checked that the text it already had was well-formed.

**The sweep is derived, not listed.** The menu is read out of
`main_window._build_menus`' source, so an action added tomorrow is covered the
day it lands rather than the day somebody remembers this file. That is the same
reason `test_documented_ripper_flags_are_real.py` sweeps the tree instead of
naming four paths: a hand-kept list of "the places this could go wrong" decays
invisibly, and the thing it stops covering is always the newest thing.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
MAIN_WINDOW: Final[Path] = REPO_ROOT / "src" / "platterpus" / "ui" / "main_window.py"

#: `tools_menu.addAction("Run &acceptance test…")` — the label, as written.
_TOOLS_ACTION: Final[re.Pattern[str]] = re.compile(
    r'tools_menu\.addAction\(\s*"([^"]+)"', re.MULTILINE
)

#: Actions whose absence from the Guide is deliberate, each with its reason.
#: Deliberately short: an allowlist is how a check like this rots into decoration,
#: so anything added here needs a sentence somebody can disagree with.
_NOT_IN_THE_GUIDE: Final[dict[str, str]] = {
    # The Guide is what this opens. Documenting the door inside the room is
    # circular, and a reader who is reading it has already found it.
    "&Settings…": "Settings is documented field-by-field throughout the Guide",
}


def _menu_labels() -> list[str]:
    """Every Tools-menu label, read from the source that builds the menu."""
    text = MAIN_WINDOW.read_text(encoding="utf-8")
    return [m.group(1) for m in _TOOLS_ACTION.finditer(text)]


def _searchable(label: str) -> str:
    """The label reduced to what a Guide would plausibly write.

    Qt's `&` accelerator and the trailing ellipsis are chrome — the Guide writes
    *"Tools → Run acceptance test…"* but it may equally write *"Run acceptance
    test"* mid-sentence, and failing on the ellipsis would be a false alarm.

    **`&&` IS A LITERAL AMPERSAND, NOT TWO ACCELERATORS.** Stripping every `&`
    turned ``Setup && &Updates…`` into ``Setup  Updates`` — two spaces where the
    user sees an ampersand — so the sweep looked for a string no Guide would ever
    contain and reported the item as undocumented when it was documented. The
    label was right and the normaliser was wrong, which is the more expensive
    direction: its output is an instruction to go and edit a file that was
    already correct. Unescape first, then strip the accelerators.
    """
    literal = "\x00"  # a byte no menu label contains
    text = label.replace("&&", literal).replace("&", "").replace(literal, "&")
    return text.rstrip("…").strip()


def test_the_menu_sweep_actually_finds_the_menu() -> None:
    """The floor. A regex that stopped matching would pass every case below
    while checking nothing — the shape this repo has 52 live instances of."""
    labels = _menu_labels()
    # **7, down from 8 on 2026-09-21, and lowered deliberately.** The Tools menu
    # really did shrink: *Set up Platterpus…*, *Add app shortcut* and *Set up
    # drive…* became sections of the one *Setup & Updates…* window, which is a net
    # -2. The floor exists to catch the regex silently ceasing to match, so it has
    # to track the real count; leaving it at 8 would have been a floor nothing
    # could satisfy, and raising it back later is how it stops meaning anything.
    assert len(labels) >= 7, (
        f"only {len(labels)} Tools action(s) found in {MAIN_WINDOW.name}; the "
        "pattern has stopped matching and this file is measuring nothing"
    )
    assert any("acceptance" in label.lower() for label in labels), (
        f"the acceptance action is not in the swept menu: {labels}"
    )


def test_every_tools_action_appears_in_the_user_guide() -> None:
    """The regression test for the acceptance session's absence."""
    from platterpus.help_content import user_guide

    guide = user_guide()
    assert len(guide) > 5_000, (
        f"the Guide is only {len(guide)} characters — that is not the real "
        "document, so every assertion below would be about the wrong text"
    )

    missing: list[str] = []
    for label in _menu_labels():
        if label in _NOT_IN_THE_GUIDE:
            continue
        if _searchable(label) not in guide:
            missing.append(label)

    assert not missing, (
        "these Tools actions are not mentioned anywhere in the in-app User "
        "Guide, so a person cannot find them from inside the program:\n  "
        + "\n  ".join(missing)
        + "\n(If an omission is deliberate, add it to _NOT_IN_THE_GUIDE with a "
        "reason — but read that dict's comment first.)"
    )


def test_the_guide_check_can_actually_fail() -> None:
    """Non-triviality, against constructed text, in both directions.

    The `&`/ellipsis stripping is exactly the kind of normalisation that can
    quietly match everything, so both halves are pinned.
    """
    assert _searchable("Run &acceptance test…") == "Run acceptance test"
    assert _searchable("&Uninstall Platterpus…") == "Uninstall Platterpus"
    # It must NOT reduce a label to something so generic it matches any prose.
    assert _searchable("Set up &drive…") == "Set up drive"
    assert "Run acceptance test" not in "The guide says nothing about testing."


def test_the_guide_does_not_send_a_user_to_the_terminal_for_the_session() -> None:
    """The half that motivated the feature.

    The Guide is allowed to mention `--rig-session` — it exists and some people
    want it — but the acceptance session must be described as the menu action it
    is, or the document is still teaching the route the product replaced.
    """
    from platterpus.help_content import user_guide

    guide = user_guide()
    assert "Run acceptance test" in guide, "the menu action is undocumented"
    heading = guide.find("Running the full acceptance test")
    assert heading != -1, "the acceptance session has no section of its own"
    # Its own section must reach the deliverable without a command line: the
    # operator's whole question is "what do I send?".
    section = guide[heading : heading + 2_000]
    assert "Downloads" in section, (
        "the acceptance section never says where the one file lands"
    )


# ---------------------------------------------------------------------------
# THE CONVERSE: every menu path the product NAMES must exist.
#
# Everything above checks one direction — each menu item is findable in the
# Guide. Nothing checked the other: that a path written in the Guide, a dialog,
# a hint or an operator sheet leads somewhere. On 2026-09-23 five did not. The
# Guide said **Tools → Check dependencies** (no such item since the menu was
# consolidated on 2026-09-21), a prompt said **Tools → Settings → Check
# dependencies**, preflight said **Settings → Re-detect…**, a hint named a
# "Tools → Diagnose entry", and the Guide's own heading printed
# "Setup && Updates" — a Qt accelerator escape shown literally, because
# Markdown is not a menu. A menu path is an exact string to the person following
# it; a stale one is a dead end.
# ---------------------------------------------------------------------------

SETUP_CENTER: Final[Path] = (
    REPO_ROOT / "src" / "platterpus" / "ui" / "dialogs" / "setup_center.py"
)
SCRIPT_CONSOLE: Final[Path] = (
    REPO_ROOT / "src" / "platterpus" / "ui" / "dialogs" / "script_console.py"
)
SETTINGS: Final[Path] = REPO_ROOT / "src" / "platterpus" / "ui" / "settings_dialog.py"

#: User-facing documents scanned in full. The chronological records (the session
#: log, the CHANGELOG, `docs/archive/`, the handshake laps) are deliberately NOT
#: here: they describe the menu as it was on their date, and rewriting history to
#: match today's menu would be a falsified record.
_USER_FACING_DOCS: Final[tuple[str, ...]] = (
    "README.md",
    "docs/hardware-test-checklist.md",
    "docs/test-plan.md",
    "docs/rig-session.md",
)

_MENU_ACTION: Final[re.Pattern[str]] = re.compile(
    r'(file|tools|help)_menu\.addAction\(\s*"([^"]+)"', re.MULTILINE
)
_SECTION_BUTTON: Final[re.Pattern[str]] = re.compile(r'\("([^"]+)",\s*"\w+"\)')
_CONSOLE_BUTTON: Final[re.Pattern[str]] = re.compile(r'QPushButton\("([^"]+)"')
_SETTINGS_ROW: Final[re.Pattern[str]] = re.compile(r'form\.addRow\(\s*"([^"]+?):?"')
_PATH_START: Final[re.Pattern[str]] = re.compile(r"\b(File|Tools|Help)\s*→\s*")


def _plain(text: str) -> str:
    """One spelling of the punctuation, case KEPT — the menu names are found by
    their capital letter, so "the file → the folder" in prose is not a path."""
    text = text.replace("->", "→").replace("...", "…").replace("*", "").replace("`", "")
    return re.sub(r"\s+", " ", text)


def _norm(text: str) -> str:
    """:func:`_plain`, casefolded — the form a path is compared to a label in."""
    return _plain(text).casefold()


def _menu_model() -> dict[str, dict[str, list[str]]]:
    """``{menu: {item: [sub-item, …]}}``, read from the source that builds it.

    Sub-items are resolved for the three windows a path is written *into*:
    Setup & Updates (its section buttons), the test-script console (its
    buttons) and Settings (its row labels) — the last is what refuses
    "Tools → Settings → Check dependencies".

    **The narrowing, written down rather than quietly scoped.** Under any OTHER
    item a further "→" is not checked, because what follows it there is a
    sequence of steps inside a dialog ("Uninstall Platterpus… → tick the
    host-exports item", "Rip as Unknown Album… → placeholders → Start"), not a
    menu path, and there is no source list of step names to resolve it against.
    The item itself is still checked.
    """
    model: dict[str, dict[str, list[str]]] = {"file": {}, "tools": {}, "help": {}}
    for menu, label in _MENU_ACTION.findall(MAIN_WINDOW.read_text(encoding="utf-8")):
        model[menu][_norm(_searchable(label))] = []
    center = [
        _norm(_searchable(b))
        for b in _SECTION_BUTTON.findall(SETUP_CENTER.read_text(encoding="utf-8"))
    ]
    console = [
        _norm(_searchable(b))
        for b in _CONSOLE_BUTTON.findall(SCRIPT_CONSOLE.read_text(encoding="utf-8"))
    ]
    settings = [
        _norm(_searchable(row))
        for row in _SETTINGS_ROW.findall(SETTINGS.read_text(encoding="utf-8"))
    ]
    model["tools"][_norm("Setup & Updates")] = center
    model["tools"][_norm("Run test script")] = console
    model["tools"][_norm("Settings")] = settings
    return model


def _user_facing_texts() -> dict[str, str]:
    """Every string a user can read: non-docstring literals in the package, the
    rig scripts, and the user-facing documents."""
    import ast

    texts: dict[str, str] = {}
    package = REPO_ROOT / "src" / "platterpus"
    for path in sorted(package.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        docstrings: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(
                node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
            ):
                body = node.body
                if (
                    body
                    and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                ):
                    docstrings.add(id(body[0].value))
        strings = [
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstrings
        ]
        texts[str(path.relative_to(REPO_ROOT))] = "\n".join(strings)
    for path in sorted((package / "rig_scripts").glob("*.txt")):
        texts[str(path.relative_to(REPO_ROOT))] = path.read_text(encoding="utf-8")
    for doc in _USER_FACING_DOCS:
        texts[doc] = (REPO_ROOT / doc).read_text(encoding="utf-8")
    return texts


def _longest_label_at(remainder: str, labels: list[str]) -> str | None:
    """The longest label ``remainder`` begins with, ending on a word boundary."""
    best: str | None = None
    for label in labels:
        if remainder.startswith(label):
            after = remainder[len(label) : len(label) + 1]
            if (after == "" or not after.isalnum()) and (
                best is None or len(label) > len(best)
            ):
                best = label
    return best


def _dead_paths(text: str, model: dict[str, dict[str, list[str]]]) -> list[str]:
    """Each named menu path in ``text`` that does not lead anywhere, and why."""
    dead: list[str] = []
    plain = _plain(text)
    for match in _PATH_START.finditer(plain):
        menu = match.group(1).casefold()
        rest = plain[match.end() :].casefold()
        shown = f"{match.group(1)} → {rest[:50]}"
        item = _longest_label_at(rest, list(model[menu]))
        if item is None:
            dead.append(f"{shown!r}: no such item in the {match.group(1)} menu")
            continue
        rest = rest[len(item) :].lstrip("…").lstrip()
        if not rest.startswith("→"):
            continue
        rest = rest[1:].lstrip()
        subs = model[menu][item]
        if not subs:
            continue  # steps inside a dialog — see _menu_model's narrowing
        if _longest_label_at(rest, subs) is None:
            dead.append(f"{shown!r}: no such button in {item!r}")
    return dead


def test_every_menu_path_the_product_names_exists() -> None:
    """The converse sweep. Fails listing each dead path with where it is."""
    model = _menu_model()
    offenders = {
        where: dead
        for where, text in _user_facing_texts().items()
        if (dead := _dead_paths(text, model))
    }
    assert not offenders, (
        "menu paths that lead nowhere — a person following one finds nothing:\n"
        + "\n".join(f"  {where}: {d}" for where, ds in offenders.items() for d in ds)
    )


def test_the_menu_path_sweep_resolves_real_paths_and_rejects_dead_ones() -> None:
    """Non-triviality, both directions, against constructed text and the tree.

    A resolver that accepted everything would pass the sweep above; one that
    stopped finding paths would too. So it must resolve a real count, and must
    refuse each of the five shapes that shipped.
    """
    model = _menu_model()
    assert len(model["tools"]) >= 7 and len(model["tools"]["setup & updates"]) >= 6
    assert len(model["tools"]["settings"]) >= 20, "the Settings rows were not read"
    named = sum(
        len(_PATH_START.findall(_plain(text))) for text in _user_facing_texts().values()
    )
    assert named >= 30, f"only {named} menu paths found — the scan broke"
    for good in (
        "Tools → Setup & Updates… → Check dependencies.",
        "**Tools → Run acceptance test…**",
        "Tools -> Setup & Updates... -> Check for cyanrip updates",
        "Help → About Platterpus…",
    ):
        assert _dead_paths(good, model) == [], good
    for bad in (
        "Tools → Check dependencies",
        "Tools → Settings → Check dependencies",
        "Tools → Diagnose entry",
        "Help → About",
        "Tools → Setup & Updates… → Re-detect…",
    ):
        assert _dead_paths(bad, model), f"accepted a dead path: {bad}"


def test_no_user_facing_text_shows_a_qt_ampersand_escape() -> None:
    """`&&` is how a Qt LABEL writes one ampersand; anywhere else it prints as two.

    The Guide's heading read "Setup && Updates" in the rendered help, because it
    copied the menu label's source spelling into Markdown.
    """
    offenders = [
        where
        for where, text in _user_facing_texts().items()
        if "Setup && Updates" in text and "addAction" not in text
    ]
    # The menu label itself lives in main_window.py as a Qt string, where `&&`
    # is correct; every other occurrence is a literal double ampersand.
    offenders = [w for w in offenders if not w.endswith("ui/main_window.py")]
    assert not offenders, f"'Setup && Updates' shown literally in: {offenders}"
