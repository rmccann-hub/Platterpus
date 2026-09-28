"""Every `QLabel` built from a value must STATE its text format, and say it at the site.

**What goes wrong without it.** A `QLabel`'s default format is
`Qt.TextFormat.AutoText`, which is a guess: Qt treats the text as HTML when
`Qt::mightBeRichText` finds a known tag on its *first line*, and then silently
drops whatever markup it cannot render. So one label renders two different ways
depending on the value inside it — which is exactly the case for text that came
from outside the app. Measured on the drive wizard before this file existed
(PySide6 6.11.2, offscreen): a drive named `<i>odd</i>` lost its name's markers
and turned italic, and a drive named `TSST <corp> & Co` made Qt decide the whole
label was plain text, so the user saw the literal `<b>+667</b>` tags around their
offset. Critical rule #12 names the cure: *every widget carrying dependency output
is `PlainText`*.

**Why no allowlist of "safe" sites.** The row this closes in `TASKS.md` said it
plainly: most of these labels hold our own constants, so a sweep that exempted
the safe ones would need a long list, and a list of excuses enforces nothing —
"this label's text is ours" is a claim about every future edit to it, not about
today's. So instead of judging sites, the rule is that every site DECIDES, where a
reader can see the decision:

* **PlainText** for text that is not markup, which is almost all of them.
* **RichText** where a label deliberately renders markup (a `<b>…</b>` of ours),
  and then every value put into that markup must go through `html.escape`, so
  external text can never be read as a tag. The second test below holds each
  RichText site to that.

AutoText is refused even when written out explicitly, because stating the guess
is not a decision.

**What this does NOT cover, said out loud.** The population is a `QLabel(...)`
call whose text argument is not a string literal. A label built EMPTY or from a
literal and given a value later through `setText(...)` is outside it; the
2026-09-28 closing note on the TASKS row counts those (13 at the time, most of
them in the rip progress pane). `tests/test_message_boxes_are_plaintext.py`
sweeps `QMessageBox`; this file sweeps `QLabel`; neither sweeps the other.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from PySide6.QtCore import Qt
from PySide6.QtGui import Qt as GuiQt  # the Qt namespace with QtGui's functions
from PySide6.QtGui import QTextDocument
from PySide6.QtWidgets import QApplication, QLabel, QWidget

SRC: Final[Path] = Path(__file__).resolve().parents[1] / "src" / "platterpus"

#: Floor on the swept population. 17 sites on 2026-09-28. A scan that found
#: none would report "no offenders" for ever, so it must find at least this many
#: before its verdict means anything.
_MIN_LABEL_SITES: Final[int] = 15

#: Floor on the RichText sites, so the escaping test cannot pass by finding none.
#: Three on 2026-09-28: the manual-install intro, the drive wizard's known-offset
#: line and the setup wizard's intro.
_MIN_RICHTEXT_SITES: Final[int] = 2

#: The formats a site may state. `AutoText` is Qt's guess, so writing it out is
#: not a decision. A label that genuinely needs `MarkdownText` would need its own
#: escaping rule first, the way RichText has one below; add both together.
_STATED_FORMATS: Final[frozenset[str]] = frozenset({"PlainText", "RichText"})


@dataclass(frozen=True)
class MarkupFromCallers:
    """A RichText site whose markup is written by its CALLERS, not by itself.

    Such a site has nothing to escape in its own function, so the escaping test
    checks the callers instead: every construction of `carrier` that passes a
    non-literal `field` must happen in a function that calls `html.escape`.
    """

    #: The class that carries the markup into the site, e.g. `SetupCopy`.
    carrier: str
    #: The field of `carrier` holding the markup, e.g. `intro`.
    field: str
    #: Why the site has no external value of its own.
    reason: str


#: RichText sites whose own function has no `html.escape` because it builds no
#: markup: it shows markup its callers wrote. Each names the carrier the markup
#: arrives in, and the test below checks every builder of that carrier instead.
#: Keep this as short as possible; one entry today.
_MARKUP_FROM_CALLERS: Final[dict[str, MarkupFromCallers]] = {
    "ui/host_setup_dialog.py::HostSetupDialog.__init__": MarkupFromCallers(
        carrier="SetupCopy",
        field="intro",
        reason=(
            "shows SetupCopy.intro, markup its builders write: the dataclass "
            "default is a literal of ours, and the ripper update's builder "
            "interpolates the build pin the user picked, which it escapes"
        ),
    ),
}


@dataclass(frozen=True)
class LabelSite:
    """One `QLabel(<non-literal>)` construction and what the sweep found there."""

    #: `module:line`, for the failure message.
    where: str
    #: `module::Qualified.function` the construction sits in (the module itself
    #: for a module-level construction).
    function: str
    #: The format stated right after it (`"PlainText"`, `"RichText"`, `"AutoText"`,
    #: or the source of whatever expression was passed), or None if none was.
    stated: str | None
    #: Why this site fails the rule, or None when it passes.
    problem: str | None


def _is_qlabel_call(node: ast.AST) -> bool:
    """True for `QLabel(...)` and `QtWidgets.QLabel(...)`."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    return (isinstance(func, ast.Name) and func.id == "QLabel") or (
        isinstance(func, ast.Attribute) and func.attr == "QLabel"
    )


def _text_is_not_literal(call: ast.Call) -> bool:
    """True when the label's first argument (or `text=`) is anything but a string.

    `QLabel()` has no first argument and is not in the population; `QLabel(self)`
    is, because its first argument is not a literal — a label built that way gets
    its text (or picture) later, from somewhere this line cannot show.
    """
    first: ast.expr | None = call.args[0] if call.args else None
    if first is None:
        for keyword in call.keywords:
            if keyword.arg == "text":
                first = keyword.value
    if first is None:
        return False
    return not (isinstance(first, ast.Constant) and isinstance(first.value, str))


#: Nodes that open a new scope. A `setTextFormat` inside a nested function runs
#: when (and if) that function is called, so it does not count for the outer one.
_SCOPES: Final[tuple[type[ast.AST], ...]] = (
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.Lambda,
    ast.ClassDef,
    ast.Module,
)


def _own_nodes(scope: ast.AST) -> list[ast.AST]:
    """Every node inside `scope` that is not inside a nested scope."""
    found: list[ast.AST] = []
    pending: list[ast.AST] = list(ast.iter_child_nodes(scope))
    while pending:
        node = pending.pop()
        found.append(node)
        if not isinstance(node, _SCOPES):
            pending.extend(ast.iter_child_nodes(node))
    return found


def _qualified_name(scope: ast.AST, parents: dict[ast.AST, ast.AST]) -> str:
    """`Class.method` for a method, `function` for a function, `` for a module."""
    names: list[str] = []
    node: ast.AST | None = scope
    while node is not None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.append(node.name)
        elif isinstance(node, ast.Lambda):
            names.append("<lambda>")
        node = parents.get(node)
    return ".".join(reversed(names))


def _stated_format(call: ast.Call) -> str:
    """What a `setTextFormat(...)` call states: the enum member name, or the source."""
    if call.args and isinstance(call.args[0], ast.Attribute):
        return call.args[0].attr
    return ast.unparse(call.args[0]) if call.args else ""


def _assigned_names(node: ast.AST) -> list[str]:
    """The names an assignment statement binds, as source text; [] for anything else."""
    if isinstance(node, ast.Assign):
        return [ast.unparse(target) for target in node.targets]
    if isinstance(node, (ast.AnnAssign, ast.AugAssign)):
        return [ast.unparse(node.target)]
    return []


def _position(node: ast.AST) -> tuple[int, int]:
    return (getattr(node, "lineno", 0), getattr(node, "col_offset", 0))


def _end_position(node: ast.AST) -> tuple[int, int]:
    return (
        getattr(node, "end_lineno", None) or getattr(node, "lineno", 0),
        getattr(node, "end_col_offset", None) or 0,
    )


def label_sites(source: str, module: str) -> list[LabelSite]:
    """Every `QLabel(<non-literal>)` in `source`, each judged against the rule.

    Pure, and working on source text rather than on the tree under `src/`, so the
    test at the bottom can feed it snippets built to fail. Every matching call
    yields a site — a shape the matcher cannot check is a site WITH a problem,
    never a site skipped, because a sweep that quietly skips what it cannot read
    reports the unreadable ones as clean.
    """
    tree = ast.parse(source)
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent

    sites: list[LabelSite] = []
    # In source order, so a report (and the snippets below) read top to bottom.
    calls = sorted(
        (node for node in ast.walk(tree) if isinstance(node, ast.Call)),
        key=_position,
    )
    for call in calls:
        if not _is_qlabel_call(call) or not _text_is_not_literal(call):
            continue
        scope: ast.AST = parents[call]
        while not isinstance(scope, _SCOPES):
            scope = parents[scope]
        function = f"{module}::{_qualified_name(scope, parents)}"
        where = f"{module}:{call.lineno}"

        # The shapes the rule can check: the label is assigned, whole, to one
        # plain name or attribute. Anything else (passed straight to addRow,
        # returned, put in a list) has no name to call setTextFormat on.
        statement = parents[call]
        target: ast.expr | None = None
        if (
            isinstance(statement, ast.Assign)
            and statement.value is call
            and len(statement.targets) == 1
        ):
            target = statement.targets[0]
        elif isinstance(statement, ast.AnnAssign) and statement.value is call:
            target = statement.target
        if not isinstance(target, (ast.Name, ast.Attribute)):
            sites.append(
                LabelSite(
                    where,
                    function,
                    None,
                    "built inline, so nothing can be called on it: assign it to a "
                    "name first, then call setTextFormat on that name",
                )
            )
            continue
        name = ast.unparse(target)

        own = _own_nodes(scope)
        built_at = _end_position(statement)
        # The pin must fall between this construction and the next time the same
        # name is given something else — a later `x = QLabel(...)` is a new label.
        rebound = [
            _position(node)
            for node in own
            if node is not statement
            and _position(node) > built_at
            and name in _assigned_names(node)
        ]
        until = min(rebound) if rebound else (10**9, 0)
        pins = sorted(
            (
                node
                for node in own
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "setTextFormat"
                and ast.unparse(node.func.value) == name
                and built_at < _position(node) < until
            ),
            key=_position,
        )
        if not pins:
            sites.append(
                LabelSite(
                    where,
                    function,
                    None,
                    f"`{name}` is never given setTextFormat(...) after it is built, "
                    "in the same function",
                )
            )
            continue
        stated = _stated_format(pins[0])
        problem = (
            None
            if stated in _STATED_FORMATS
            else f"`{name}` states {stated!r}; write Qt.TextFormat.PlainText or "
            "Qt.TextFormat.RichText at the call, so the decision can be read there"
        )
        sites.append(LabelSite(where, function, stated, problem))
    return sites


def _modules() -> dict[str, str]:
    """Every module under `src/platterpus`, package-relative, with its source."""
    return {
        str(path.relative_to(SRC)): path.read_text(encoding="utf-8")
        for path in sorted(SRC.rglob("*.py"))
        if "__pycache__" not in path.parts
    }


def _all_sites() -> list[LabelSite]:
    return [
        site
        for module, source in _modules().items()
        for site in label_sites(source, module)
    ]


def _functions(source: str, module: str) -> dict[str, ast.AST]:
    """Every function/method/module scope in `source`, by `module::qualname`."""
    tree = ast.parse(source)
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    return {
        f"{module}::{_qualified_name(node, parents)}": node
        for node in ast.walk(tree)
        if isinstance(node, _SCOPES)
    }


def calls_html_escape(scope: ast.AST) -> bool:
    """True if `scope`, not counting nested functions, calls `html.escape(...)`.

    Matches the CALL, not a mention: `import html`, or `html.escape` named in a
    comment or a string, does not escape anything.
    """
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "escape"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "html"
        for node in _own_nodes(scope)
    )


# --- The population -----------------------------------------------------------


def test_the_sweep_finds_the_labels() -> None:
    """Floor first: a sweep over nothing reports no offenders for ever."""
    sites = _all_sites()
    assert len(sites) >= _MIN_LABEL_SITES, (
        f"only {len(sites)} QLabel(<non-literal>) site(s) found under {SRC} "
        f"(floor {_MIN_LABEL_SITES}) — the scan is broken, so the verdict below "
        "means nothing"
    )
    # And the subject: the release picker is the case Critical rule #12 names
    # (MusicBrainz data), so a population without it is looking in the wrong place
    # even if the count clears.
    assert any(site.where.startswith("ui/release_picker.py:") for site in sites), (
        "the release picker is not in the swept population: "
        f"{sorted(site.where for site in sites)}"
    )


def test_every_label_built_from_a_value_states_its_format() -> None:
    """The rule itself."""
    offenders = [
        f"{site.where}: {site.problem}" for site in _all_sites() if site.problem
    ]
    assert not offenders, (
        "these QLabels are built from a value without stating their text format. "
        "Qt's default AutoText treats text as HTML when its first line happens to "
        "hold a known tag, and then drops what it cannot render — so a `<` in a "
        "release title, a drive name or a tool's message can cut the label short "
        "or turn its text into formatting, silently (CLAUDE.md Critical rule "
        "#12). Call setTextFormat(Qt.TextFormat.PlainText) right after building "
        "it — or RichText, if the label renders markup of ours, with every value "
        "inside that markup passed through html.escape:\n  " + "\n  ".join(offenders)
    )


# --- RichText sites escape what they interpolate -------------------------------


def test_every_richtext_label_escapes_what_it_puts_in_its_markup() -> None:
    """A RichText site's function must call `html.escape`, or be listed with why."""
    sites = _all_sites()
    rich = [site for site in sites if site.stated == "RichText"]
    assert len(rich) >= _MIN_RICHTEXT_SITES, (
        f"only {len(rich)} RichText label(s) found (floor {_MIN_RICHTEXT_SITES}), "
        "so the escaping check below has nothing to hold to account"
    )
    scopes: dict[str, ast.AST] = {}
    for module, source in _modules().items():
        scopes.update(_functions(source, module))
    offenders = [
        f"{site.where} ({site.function})"
        for site in rich
        if site.function not in _MARKUP_FROM_CALLERS
        and not calls_html_escape(scopes[site.function])
    ]
    assert not offenders, (
        "these labels render RichText, but the function building them never calls "
        "html.escape. A value from outside the app (a drive's name, a path, a "
        "MusicBrainz field, a tool's output) put into markup unescaped is read as "
        "markup: a `<` in it becomes a tag and what follows can vanish. Escape "
        "each such value, or — if the site truly shows only markup its callers "
        "wrote — list it in _MARKUP_FROM_CALLERS:\n  " + "\n  ".join(offenders)
    )


def test_markup_from_callers_is_escaped_by_every_caller() -> None:
    """The one exemption is checked where the escaping actually happens.

    An entry says "this site's markup is written elsewhere". That is a claim about
    other functions, so this test goes and reads them: every construction of the
    carrier that passes a non-literal markup field must be in a function that
    calls `html.escape`, and the carrier's own default must be a literal.
    """
    sites = {site.function: site for site in _all_sites()}
    modules = _modules()
    for function, entry in _MARKUP_FROM_CALLERS.items():
        assert function in sites, (
            f"{function} is listed in _MARKUP_FROM_CALLERS but builds no label any "
            "more — remove the entry so it cannot excuse whatever replaces it"
        )
        assert sites[function].stated == "RichText", (
            f"{function} is listed as a RichText site but states "
            f"{sites[function].stated!r}"
        )
        assert len(entry.reason) >= 60, (
            f"{function}: reason too short: {entry.reason!r}"
        )

        builders: list[str] = []
        unescaped: list[str] = []
        default_is_literal: bool | None = None
        for module, source in modules.items():
            for scope_name, scope in _functions(source, module).items():
                for node in _own_nodes(scope):
                    if isinstance(node, ast.ClassDef) and node.name == entry.carrier:
                        for item in node.body:
                            if (
                                isinstance(item, ast.AnnAssign)
                                and isinstance(item.target, ast.Name)
                                and item.target.id == entry.field
                            ):
                                default_is_literal = isinstance(
                                    item.value, ast.Constant
                                ) and isinstance(item.value.value, str)
                    if not (
                        isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Name)
                        and node.func.id == entry.carrier
                    ):
                        continue
                    assert not node.args, (
                        f"{module}:{node.lineno} builds {entry.carrier} positionally; "
                        "pass its fields by name so this check can find the markup"
                    )
                    for keyword in node.keywords:
                        if keyword.arg != entry.field:
                            continue
                        if isinstance(keyword.value, ast.Constant):
                            continue
                        builders.append(scope_name)
                        if not calls_html_escape(scope):
                            unescaped.append(f"{module}:{node.lineno} ({scope_name})")
        assert default_is_literal is True, (
            f"{entry.carrier}.{entry.field}'s default is not a plain string literal "
            "of ours, so the markup it carries by default is no longer known to be "
            "ours"
        )
        # Floor: the claim is that the builders escape. With no builder found, the
        # loop above proved nothing — and one is known to exist (the ripper update).
        assert builders, (
            f"no builder of {entry.carrier}({entry.field}=<value>) was found, so the "
            "escaping claim was checked against nothing"
        )
        assert not unescaped, (
            f"these build {entry.carrier}.{entry.field} — markup shown as RichText by "
            f"{function} — from a value without calling html.escape:\n  "
            + "\n  ".join(unescaped)
        )


# --- The matcher can say no -----------------------------------------------------


def _problems(snippet: str) -> list[str | None]:
    return [site.problem for site in label_sites(snippet, "snippet.py")]


def test_the_matcher_finds_a_missing_format_and_accepts_a_stated_one() -> None:
    """Non-triviality, against constructed input: it must be able to say no.

    Each shape here is one the rule has to tell apart; the interesting ones are
    those where a `setTextFormat` IS present but does not pin THIS label.
    """
    stated_plain = (
        "def f(text):\n"
        "    label = QLabel(text)\n"
        "    label.setTextFormat(Qt.TextFormat.PlainText)\n"
    )
    stated_rich_attr = (
        "class D:\n"
        "    def __init__(self, text):\n"
        "        self._label: QLabel = QLabel(text, self)\n"
        "        self._label.setTextFormat(Qt.TextFormat.RichText)\n"
    )
    missing = "def f(text):\n    label = QLabel(text)\n    label.setWordWrap(True)\n"
    other_label = (
        "def f(text):\n"
        "    label = QLabel(text)\n"
        "    other.setTextFormat(Qt.TextFormat.PlainText)\n"
    )
    before_it_is_built = (
        "def f(a, b):\n"
        "    label = QLabel(a)\n"
        "    label.setTextFormat(Qt.TextFormat.PlainText)\n"
        "    label = QLabel(b)\n"
    )
    in_another_function = (
        "def f(text):\n"
        "    label = QLabel(text)\n"
        "def g():\n"
        "    label.setTextFormat(Qt.TextFormat.PlainText)\n"
    )
    in_a_nested_function = (
        "def f(text):\n"
        "    label = QLabel(text)\n"
        "    def later():\n"
        "        label.setTextFormat(Qt.TextFormat.PlainText)\n"
    )
    inline = "def f(form, text):\n    form.addRow('A:', QLabel(text))\n"
    auto = (
        "def f(text):\n"
        "    label = QLabel(text)\n"
        "    label.setTextFormat(Qt.TextFormat.AutoText)\n"
    )
    literal_only = "def f():\n    label = QLabel('Fixed words')\n"

    assert _problems(stated_plain) == [None]
    assert [s.stated for s in label_sites(stated_plain, "s.py")] == ["PlainText"]
    assert _problems(stated_rich_attr) == [None]
    assert [s.function for s in label_sites(stated_rich_attr, "s.py")] == [
        "s.py::D.__init__"
    ]
    for name, snippet in (
        ("missing", missing),
        ("a different label pinned", other_label),
        ("a pin that belongs to the first of two labels", before_it_is_built),
        ("a pin in another function", in_another_function),
        ("a pin in a nested function", in_a_nested_function),
        ("a label built inline", inline),
        ("AutoText stated", auto),
    ):
        problems = _problems(snippet)
        assert problems and problems[-1] is not None, (
            f"the matcher accepted {name!r}: {problems}"
        )
    assert _problems(literal_only) == [], (
        "a literal-text label is not in the population"
    )
    # `QLabel(parent)` is in it: the text arrives later from who knows where.
    assert len(_problems("def f(p):\n    logo = QLabel(p)\n")) == 1


def test_the_escape_detector_needs_a_call_not_a_mention() -> None:
    """`import html` or a comment naming html.escape escapes nothing."""
    called = ast.parse("def f(n):\n    return f'<b>{html.escape(n)}</b>'\n").body[0]
    mentioned = ast.parse(
        "def f(n):\n    # html.escape would go here\n    return f'<b>{n}</b>'\n"
    ).body[0]
    nested_only = ast.parse(
        "def f(n):\n    def g():\n        return html.escape(n)\n    return n\n"
    ).body[0]
    assert calls_html_escape(called) is True
    assert calls_html_escape(mentioned) is False
    assert calls_html_escape(nested_only) is False


# --- The user-visible effect, measured on the real widgets ---------------------


def _shown(label: QLabel) -> str:
    """The text a user sees, resolved the way QLabel resolves it.

    RichText is parsed as HTML, through the same QTextDocument machinery the label
    uses; PlainText is shown as it stands; AutoText is resolved by Qt's own guess,
    `Qt.mightBeRichText`, exactly as QLabel does. AutoText has to be handled
    rather than refused: a dialog's LITERAL labels are outside this sweep, and
    this helper reads every label in the dialog to find the one a test is about.
    Each test then asserts that label's own format.
    """
    text = label.text()
    fmt = label.textFormat()
    if fmt == Qt.TextFormat.RichText or (
        fmt == Qt.TextFormat.AutoText and GuiQt.mightBeRichText(text)
    ):
        document = QTextDocument()
        document.setHtml(text)
        return document.toPlainText()
    return text


def _labels_showing(widget: QWidget, needle: str) -> list[QLabel]:
    return [label for label in widget.findChildren(QLabel) if needle in _shown(label)]


def test_a_drive_name_and_path_that_look_like_markup_are_shown_as_written(
    qapp: QApplication,
) -> None:
    """The drive wizard shows the drive's own vendor/model and device path verbatim.

    Both values come from the system. Before this change the vendor string decided
    the label's format: `TSST <corp> & Co` read as plain text and showed the
    literal `<b>` tags around the offset.
    """
    from platterpus.adapters.rip_backend import RipBackend
    from platterpus.ui.drive_setup_dialog import DriveSetupDialog

    class _Backend(RipBackend):
        """Mirrors cyanrip: no offset finder, a cache probe (KDD-29)."""

        def list_drives(self):  # type: ignore[override]
            return []

        def disc_info(self, drive):  # type: ignore[override]
            raise NotImplementedError

        def rip(self, *a, **kw):  # type: ignore[override]
            raise NotImplementedError

        def version(self) -> str:
            return "fake"

        def supports_offset_detection(self) -> bool:
            return False

        def supports_cache_analysis(self) -> bool:
            return True

    name = "TSST <corp> & Co <i>X</i>"
    dialog = DriveSetupDialog(
        _Backend(), "/dev/<sr0>", known_offset=667, drive_label=name
    )
    suggestion = _labels_showing(dialog, "Known read offset for")
    assert len(suggestion) == 1
    assert suggestion[0].textFormat() == Qt.TextFormat.RichText
    assert f"Known read offset for {name}: +667 " in _shown(suggestion[0])
    # Ours is still formatting: the offset renders bold, not as `<b>` text.
    assert "<b>" not in _shown(suggestion[0])
    assert _labels_showing(dialog, "Drive: /dev/<sr0>"), "the device path was altered"


def test_a_dependency_name_that_looks_like_markup_is_shown_as_written(
    qapp: QApplication,
) -> None:
    """The manual-install intro keeps its bold button name and escapes the rest."""
    from platterpus.deps.checks import ProbeResult
    from platterpus.deps.registry import DependencySpec, Tier
    from platterpus.ui.dialogs.manual_install import ManualInstallDialog

    name = "odd<b>tool</b> & co"
    spec = DependencySpec(
        dep_id="odd",
        display_name=name,
        probe=lambda: ProbeResult(present=False, version=None, location=None),
        min_version=(0, 0, 0),
        tier=Tier.MANUAL,
        install_command=None,
        search_string="x",
        description="<i>a</i> description",
        from_setup_wizard=True,
    )
    absent = ProbeResult(present=False, version=None, location=None)
    dialog = ManualInstallDialog(spec, absent, on_setup_wizard=lambda: None)
    intro = _labels_showing(dialog, "isn't set up yet")
    assert len(intro) == 1
    assert _shown(intro[0]).startswith(f"{name} isn't set up yet.")
    assert "click Set it up automatically…" in _shown(intro[0])
    assert _labels_showing(dialog, "<i>a</i> description"), (
        "the description was altered"
    )


def test_the_release_picker_intro_is_plain_text(qapp: QApplication) -> None:
    """The count line is PlainText; the release data itself lives in table cells."""
    from platterpus.adapters.musicbrainz_client import ReleaseSummary
    from platterpus.ui.release_picker import ReleasePickerDialog

    release = ReleaseSummary(mbid="m", title="<b>Loud</b> & Clear", artist_credit="A")
    dialog = ReleasePickerDialog([release, release])
    intro = _labels_showing(dialog, "MusicBrainz returned 2 matches.")
    assert len(intro) == 1
    assert intro[0].textFormat() == Qt.TextFormat.PlainText
    assert dialog._table.item(0, 0).text() == "<b>Loud</b> & Clear"
