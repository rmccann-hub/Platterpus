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

#: `advanced_menu.addAction("Run &acceptance test…")` — the menu it is added to
#: (the variable's stem) and the label, as written.
_MENU_ACTION: Final[re.Pattern[str]] = re.compile(
    r'(\w+)_menu\.addAction\(\s*"([^"]+)"', re.MULTILINE
)

#: `advanced_menu = tools_menu.addMenu("&Advanced")` — a SUBMENU: its own stem,
#: the menu it hangs from, and its title. A menu-bar menu (`menubar.addMenu`) does
#: not match, because `menubar` is not a `*_menu` variable.
#:
#: **Why submenus are read at all (2026-09-27).** *Run test script…* and *Run
#: acceptance test…* moved into Tools → Advanced ▸ (maintainer decision D4 A).
#: This sweep used to read `tools_menu.addAction` only, so the move took both
#: items out of what it read. The floor below noticed — four Tools items, and no
#: acceptance action — which is what the floor is for; the fix is to read the
#: submenu, not to lower the floor until the smaller count passes.
_SUBMENU: Final[re.Pattern[str]] = re.compile(
    r'(\w+)_menu\s*=\s*(\w+)_menu\.addMenu\(\s*"([^"]+)"', re.MULTILINE
)


def _menu_children() -> dict[str, list[tuple[str, str | None]]]:
    """``{menu stem: [(label, submenu stem or None), …]}``, read from the source.

    An ordinary action has ``None`` in the second slot; a submenu's title carries
    the stem its own children are filed under, so the tree can be walked to any
    depth.
    """
    text = MAIN_WINDOW.read_text(encoding="utf-8")
    children: dict[str, list[tuple[str, str | None]]] = {}
    for menu, label in _MENU_ACTION.findall(text):
        children.setdefault(menu, []).append((label, None))
    for child, parent, title in _SUBMENU.findall(text):
        children.setdefault(parent, []).append((title, child))
    return children


def _labels_under(
    menu: str, children: dict[str, list[tuple[str, str | None]]]
) -> list[str]:
    """Every label a person can click under ``menu``: its items, each submenu's
    title, and everything inside each submenu, at any depth."""
    found: list[str] = []
    for label, submenu in children.get(menu, []):
        found.append(label)
        if submenu is not None:
            found += _labels_under(submenu, children)
    return found


#: Actions whose absence from the Guide is deliberate, each with its reason.
#: Deliberately short: an allowlist is how a check like this rots into decoration,
#: so anything added here needs a sentence somebody can disagree with.
_NOT_IN_THE_GUIDE: Final[dict[str, str]] = {
    # The Guide is what this opens. Documenting the door inside the room is
    # circular, and a reader who is reading it has already found it.
    "&Settings…": "Settings is documented field-by-field throughout the Guide",
}


def _menu_labels() -> list[str]:
    """Every Tools-menu label, submenus included, read from the source that
    builds the menu."""
    return _labels_under("tools", _menu_children())


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
    # **6, down from 7 on 2026-09-24, and lowered deliberately.** *Diagnose drive
    # access…* moved into Setup & Updates → Drive beside *Set up drive…*, so the
    # drive has one place instead of an item in each of two. (7 was itself down
    # from 8 on 2026-09-21, when setup, the app shortcut and drive setup became
    # sections of Setup & Updates.) The floor exists to catch the regex silently
    # ceasing to match, so it has to track the real count; a floor nothing could
    # satisfy stops meaning anything.
    # **7 from 2026-09-27**: the six items plus the *Advanced* submenu's title,
    # which is a thing a person clicks too.
    assert len(labels) >= 7, (
        f"only {len(labels)} Tools action(s) found in {MAIN_WINDOW.name}; the "
        "pattern has stopped matching and this file is measuring nothing"
    )
    assert any("acceptance" in label.lower() for label in labels), (
        f"the acceptance action is not in the swept menu: {labels}"
    )
    # The submenu half has its own floor, asserted here rather than inherited from
    # the count above: that count could be met by Tools' direct items alone while
    # the submenu pattern matched nothing.
    children = _menu_children()
    direct = [label for label, _sub in children.get("tools", [])]
    nested = [label for label in labels if label not in direct]
    assert len(nested) >= 2, (
        f"no submenu items found under Tools ({labels}); the submenu pattern has "
        "stopped matching, so the Advanced items are not being checked"
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


def test_every_album_menu_action_appears_in_the_user_guide(qapp: object) -> None:
    """The disc panel's right-click menu is a menu a person clicks, too.

    **Why this is not left to the Tools sweep above.** *Set cover art from
    file…* is in both places for 0.6.62 only; in 0.6.63 its Tools entry goes, and
    from then on the album menu is its only home. The sweep above reads Tools, so
    it would stop covering the item the day the transitional entry is removed —
    the exact moment the Guide's description of the album menu matters most.

    Read off the BUILT menu rather than the source, because the actions arrive
    at run time (`DiscInfoPanel.set_album_actions`). The background menu is the
    one read: it holds only the album's actions, not the value labels' own
    Copy / Select All.
    """
    from conftest import stop_window_threads
    from test_ui_main_window import _make_window

    from platterpus.help_content import user_guide

    window = _make_window(qapp)
    try:
        menu = window._disc_info_panel.album_menu()
        labels = [action.text() for action in menu.actions() if action.text()]
        menu.deleteLater()
    finally:
        stop_window_threads(window)
        window.deleteLater()
    assert labels, "the album menu offers nothing: the window handed it no actions"
    guide = user_guide()
    missing = [label for label in labels if _searchable(label) not in guide]
    assert not missing, (
        f"these album-menu actions are not in the in-app User Guide: {missing}"
    )
    # …and the Guide says where the menu IS, or naming the item finds nothing.
    assert "right-click the disc details" in guide


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
    # The one folder the run keeps EVERYTHING in (2026-09-24), named from the
    # constant the code uses, so the guide cannot name a folder the app does not.
    from platterpus.test_session import RIG_PARENT_NAME

    assert f"~/{RIG_PARENT_NAME}/" in section, (
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
SCRIPT_SETTINGS_BOX: Final[Path] = (
    REPO_ROOT / "src" / "platterpus" / "ui" / "dialogs" / "script_settings_box.py"
)

#: User-facing documents scanned in full. The chronological records (the session
#: log, the CHANGELOG's released sections, `docs/archive/`, the handshake laps) are
#: deliberately NOT here: they describe the menu as it was on their date, and
#: rewriting history to match today's menu would be a falsified record. The
#: CHANGELOG's `[Unreleased]` section is scanned (`_unreleased_notes`): it is not
#: history yet.
_USER_FACING_DOCS: Final[tuple[str, ...]] = (
    "README.md",
    "docs/hardware-test-checklist.md",
    "docs/test-plan.md",
    "docs/rig-session.md",
    # The rig-scripts guide tells an operator which menu item to press, so it is
    # an operator sheet like the rig session's, and it named the old path of
    # both test tools four times when they moved under Advanced (2026-09-27).
    "docs/rig-scripts/README.md",
)

#: ``{item: its children}`` at any depth. An empty dict is a leaf: either a
#: plain menu item, or an item whose further "→" is steps inside a dialog (see
#: :func:`_menu_model`'s narrowing).
MenuTree = dict[str, "MenuTree"]
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


def _tree(menu: str, children: dict[str, list[tuple[str, str | None]]]) -> MenuTree:
    """One menu's items as a :data:`MenuTree`, each submenu expanded in place."""
    return {
        _norm(_searchable(label)): ({} if sub is None else _tree(sub, children))
        for label, sub in children.get(menu, [])
    }


def _attach(tree: MenuTree, item: str, subs: MenuTree) -> int:
    """Hang ``subs`` under ``item`` wherever it sits in ``tree``, at any depth.

    Returns how many places it was hung, so the caller can insist on exactly one:
    the console moved from Tools into Tools → Advanced on 2026-09-27, and a model
    that pinned it to Tools by name would have stopped checking its buttons the
    day it moved, without a word.
    """
    placed = 0
    for key, child in tree.items():
        if key == item:
            tree[key] = subs
            placed += 1
        elif child:
            placed += _attach(child, item, subs)
    return placed


def _menu_model() -> dict[str, MenuTree]:
    """``{menu: MenuTree}``, read from the source that builds it.

    Submenus are expanded to any depth (Tools → Advanced → Run test script…).
    Below the menus, children are resolved for the three windows a path is
    written *into*: Setup & Updates (its section buttons), the test-script
    console (its buttons) and Settings (its row labels) — the last is what
    refuses "Tools → Settings → Check dependencies".

    **The narrowing, written down rather than quietly scoped.** Under any OTHER
    item a further "→" is not checked, because what follows it there is a
    sequence of steps inside a dialog ("Uninstall Platterpus… → tick the
    host-exports item", "Rip as Unknown Album… → placeholders → Start"), not a
    menu path, and there is no source list of step names to resolve it against.
    The item itself is still checked.
    """
    children = _menu_children()
    model: dict[str, MenuTree] = {
        m: _tree(m, children) for m in ("file", "tools", "help")
    }
    center: MenuTree = {
        _norm(_searchable(b)): {}
        for b in _SECTION_BUTTON.findall(SETUP_CENTER.read_text(encoding="utf-8"))
    }
    # The console's buttons, and those of its script-settings box (the startup
    # script's Choose / Use built-in / Clear), which is part of the same window.
    console: MenuTree = {
        _norm(_searchable(b)): {}
        for source in (SCRIPT_CONSOLE, SCRIPT_SETTINGS_BOX)
        for b in _CONSOLE_BUTTON.findall(source.read_text(encoding="utf-8"))
    }
    settings: MenuTree = {
        _norm(_searchable(row)): {}
        for row in _SETTINGS_ROW.findall(SETTINGS.read_text(encoding="utf-8"))
    }
    for item, subs in (
        ("Setup & Updates", center),
        ("Run test script", console),
        ("Settings", settings),
    ):
        placed = _attach(model["tools"], _norm(item), subs)
        assert placed == 1, (
            f"{item!r} was found {placed} times under Tools, so its buttons are "
            "not being checked; the menu moved and this model did not follow it"
        )
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
    texts["CHANGELOG.md [Unreleased]"] = _unreleased_notes()
    return texts


def _unreleased_notes() -> str:
    """The CHANGELOG's ``[Unreleased]`` section, and nothing older.

    The released sections are history and stay out (see `_USER_FACING_DOCS`).
    This one is not yet: it becomes the next release's notes, which describe the
    menu that release ships. It named `Tools → Run acceptance test…` after the
    item had moved under Advanced in the same release (review R10, 2026-09-28).
    """
    text = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    start = text.index("## [Unreleased]")
    end = text.index("\n## [", start + 1)
    return text[start:end]


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


def _dead_paths(text: str, model: dict[str, MenuTree]) -> list[str]:
    """Each named menu path in ``text`` that does not lead anywhere, and why.

    Walks the path one "→" at a time, to any depth: a menu, a submenu, an item,
    a button inside the window it opens. It stops, satisfied, at the first leaf
    (see :func:`_menu_model`'s narrowing) or where the path stops naming things.
    """
    dead: list[str] = []
    plain = _plain(text)
    for match in _PATH_START.finditer(plain):
        rest = plain[match.end() :].casefold()
        shown = f"{match.group(1)} → {rest[:50]}"
        node = model[match.group(1).casefold()]
        where = f"the {match.group(1)} menu"
        while True:
            item = _longest_label_at(rest, list(node))
            if item is None:
                dead.append(f"{shown!r}: no such item or button in {where}")
                break
            rest = rest[len(item) :].lstrip("…").lstrip()
            if not rest.startswith("→"):
                break
            rest = rest[1:].lstrip()
            node = node[item]
            if not node:
                break  # steps inside a dialog — see _menu_model's narrowing
            where = repr(item)
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
    # 5 direct Tools items since the two test tools moved into the Advanced
    # submenu (2026-09-27; 6 before, when they were direct items and Advanced did
    # not exist). Setup & Updates' section-button count went from 7 to 8 when
    # Diagnose drive access… moved into it (2026-09-24).
    assert len(model["tools"]) >= 5 and len(model["tools"]["setup & updates"]) >= 8
    assert len(model["tools"]["settings"]) >= 20, "the Settings rows were not read"
    # The submenu is expanded, and the console's buttons hang under it.
    advanced = model["tools"]["advanced"]
    assert len(advanced) >= 2, f"the Advanced submenu was not read: {advanced}"
    assert len(advanced["run test script"]) >= 6, "the console's buttons were not read"
    named = sum(
        len(_PATH_START.findall(_plain(text))) for text in _user_facing_texts().values()
    )
    assert named >= 30, f"only {named} menu paths found — the scan broke"
    for good in (
        "Tools → Setup & Updates… → Check dependencies.",
        "**Tools → Advanced → Run acceptance test…**",
        "Tools -> Advanced -> Run test script... -> Load",
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
        # The two paths the Advanced move retired, and a wrong submenu: the walk
        # has to reach the second and third levels to refuse the last two.
        "Tools → Run acceptance test…",
        "Tools → Advanced → Uninstall Platterpus…",
        "Tools → Advanced → Run test script… → Reload",
    ):
        assert _dead_paths(bad, model), f"accepted a dead path: {bad}"


def test_the_sweep_reads_the_next_releases_notes_and_no_older_ones() -> None:
    """The `[Unreleased]` section is scanned, and a released one is not."""
    notes = _unreleased_notes()
    assert notes.startswith("## [Unreleased]"), notes[:80]
    assert "\n## [" not in notes, "a released section leaked into the scan"
    assert _user_facing_texts()["CHANGELOG.md [Unreleased]"] == notes


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
