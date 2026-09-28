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
  external text can never be read as a tag. The escaping test below FOLLOWS each
  value rather than trusting the function: every `{…}` field of the markup, and
  every name or call joined into it, must be an `html.escape(...)` call, a number
  printed with a numeric format (`{offset:+d}`), a literal of ours, or a name
  bound only to those. It traces a name through each of its assignments and a
  call into the method or function of ours that builds the markup, judging each
  parameter by what that call passed; anything it cannot trace is a failure,
  never a pass. (Until 2026-09-28 it asked only whether the building function
  called `html.escape` at all, so one escaped value vouched for every other value
  beside it: an unescaped device path added to the drive wizard's escaped drive
  name passed.)

AutoText is refused even when written out explicitly, because stating the guess
is not a decision.

**Literal labels, since 2026-09-28.** A label built from a string literal cannot
change under it, so it is outside the value rule. But Qt's guess can still be
wrong about a literal, and for a literal it is FIXED, so it is decided here: a
literal holding markup Qt knows below a first line that holds none is shown as
typed characters, and such a label must state its format too. The uninstall
dialog showed `<b>Never touched:</b>` that way. No allowlist: the answer is Qt's
own (`Qt.mightBeRichText`), asked of each literal.

**What this does NOT cover, said out loud.** The population is a `QLabel(...)`
call whose text argument is not a string literal, plus the literals above. A
label built EMPTY or from a literal and given a value later through `setText(...)`
is outside it; the
2026-09-28 closing note on the TASKS row counts those (13 at the time, most of
them in the rip progress pane). `tests/test_message_boxes_are_plaintext.py`
sweeps `QMessageBox`; this file sweeps `QLabel`; neither sweeps the other.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
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

#: Floor on the values the escaping test ACCEPTS across those sites, so "no
#: problems" cannot mean "found no values to judge". Four on 2026-09-28: the drive
#: wizard's escaped drive name and its `:+d` offset, and the manual-install
#: intro's escaped display name on each of its two branches.
_MIN_JUDGED_VALUES: Final[int] = 3

#: Floor on the LITERAL labels the literal clause reads. 33 on 2026-09-28. The
#: clause's population on correct code is empty by design (it holds only labels
#: Qt would misread), so it is this floor, not a site count, that shows the
#: clause read the labels it judged.
_MIN_LITERAL_LABELS: Final[int] = 25

#: The formats a site may state. `AutoText` is Qt's guess, so writing it out is
#: not a decision. A label that genuinely needs `MarkdownText` would need its own
#: escaping rule first, the way RichText has one below; add both together.
_STATED_FORMATS: Final[frozenset[str]] = frozenset({"PlainText", "RichText"})


@dataclass(frozen=True)
class MarkupFromCallers:
    """A RichText site whose markup is written by its CALLERS, not by itself.

    Such a site has nothing to escape in its own function, so the escaping test
    checks the callers instead: every construction of `carrier` that passes a
    non-literal `field` must pass markup whose every value the same judge
    accepts, in the function that builds it.
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
    """One `QLabel(...)` in the population, and what the sweep found there.

    The population is every label built from a value, and every label built from
    a literal whose markup Qt would show as typed characters (`hidden_markup`).
    """

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
    #: For a RichText site: each value in its markup that could be read as a tag,
    #: and why (see `_judge`). Empty for every other format.
    markup_problems: tuple[str, ...] = ()
    #: For a RichText site: each value in its markup the judge accepted, and why.
    markup_accepted: tuple[str, ...] = ()
    #: For a label built from a LITERAL: the markup in it that Qt's AutoText would
    #: show as typed characters (see `hidden_markup`). None for a label built from
    #: a value, which is in the population whatever its text holds.
    hidden_markup: str | None = None


def _is_qlabel_call(node: ast.AST) -> bool:
    """True for `QLabel(...)` and `QtWidgets.QLabel(...)`."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    return (isinstance(func, ast.Name) and func.id == "QLabel") or (
        isinstance(func, ast.Attribute) and func.attr == "QLabel"
    )


def _label_text(call: ast.Call) -> ast.expr | None:
    """The label's first argument (or `text=`): its text, or its parent widget."""
    first: ast.expr | None = call.args[0] if call.args else None
    if first is None:
        for keyword in call.keywords:
            if keyword.arg == "text":
                first = keyword.value
    return first


def _text_is_not_literal(call: ast.Call) -> bool:
    """True when the label's first argument (or `text=`) is anything but a string.

    `QLabel()` has no first argument and is not in the population; `QLabel(self)`
    is, because its first argument is not a literal — a label built that way gets
    its text (or picture) later, from somewhere this line cannot show.
    """
    first = _label_text(call)
    if first is None:
        return False
    return not (isinstance(first, ast.Constant) and isinstance(first.value, str))


#: An HTML entity (`&amp;`, `&#60;`, `&#x3c;`): markup that rich text decodes and
#: plain text shows as typed.
_ENTITY: Final[re.Pattern[str]] = re.compile(
    r"&(?:#[0-9]+|#[xX][0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]*);"
)


def hidden_markup(text: str) -> str | None:
    """Markup in a literal that Qt's AutoText would show as typed characters.

    Qt decides AutoText once, from the text's FIRST line (`Qt::mightBeRichText`),
    so for a literal the answer is fixed and can be read here, with no allowlist
    and no judgement. When the first line holds a tag Qt knows, the whole text is
    rendered as markup: None. Otherwise it is shown as written, and any tag Qt
    knows further down (asked of Qt itself, one `<` at a time) or any entity is
    returned, because that markup was written to render and the user sees its
    characters instead: the uninstall dialog showed `<b>Never touched:</b>`
    this way until 2026-09-28. A tag Qt does not know (`<stdin>`) is text either
    way, and is not markup.
    """
    if GuiQt.mightBeRichText(text):
        return None
    for index, char in enumerate(text):
        if char == "<" and GuiQt.mightBeRichText(text[index:]):
            return text[index : text.find(">", index) + 1]
    entity = _ENTITY.search(text)
    return entity.group(0) if entity else None


def _literal_label_texts(source: str) -> list[str]:
    """The text of every `QLabel("<literal>")` in `source`, for the literal floor."""
    texts: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if not _is_qlabel_call(node):
            continue
        assert isinstance(node, ast.Call)
        text = _label_text(node)
        if isinstance(text, ast.Constant) and isinstance(text.value, str):
            texts.append(text.value)
    return texts


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


# --- What a RichText label's markup may contain --------------------------------
#
# A RichText label's text is markup, so every value put into it must be one that
# cannot be read as a tag. The judge below walks the label's text expression and
# decides that for each value separately, the way a reviewer would: where does
# this `{…}` come from, and is it escaped? It accepts only shapes it can trace to
# the end, and reports everything else, because a sweep that passes what it
# cannot read reports the unread values as escaped.

#: A format spec whose output can only be a number: optional align, sign, `z`,
#: `#`, `0`, width, grouping and precision, then a numeric presentation type.
#: Deliberately NO fill character, since a fill is repeated into the output
#: (`{n:<>5d}` pads with `<`), and NO `c`, which prints the character with that
#: code point (`{60:c}` is `<`). Formatting a non-number with any of these raises
#: rather than printing it, so what such a field adds to the markup is digits,
#: signs, separators, `e`, `%`, `inf` or `nan`: never a tag.
_NUMERIC_SPEC: Final[re.Pattern[str]] = re.compile(
    r"[<>=^]?[+\- ]?z?#?0?[0-9]*[_,]?(?:\.[0-9]+)?[bdoxXneEfFgG%]"
)

#: How many names and calls the judge follows from one label before giving up.
#: The real sites need three at most. A cycle (`a = b` and `b = a`) or a longer
#: chain ends here as a problem, never as a pass.
_MAX_FOLLOW_DEPTH: Final[int] = 8


@dataclass(frozen=True)
class _Source:
    """One parsed module, and each node's parent, for the lookups the judge makes."""

    tree: ast.Module
    parents: Mapping[ast.AST, ast.AST]


def _parse(source: str) -> _Source:
    tree = ast.parse(source)
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    return _Source(tree, parents)


@dataclass(frozen=True)
class _Frame:
    """Where a piece of markup is being read.

    `scope` is the function (or module) whose names the expression can mean. When
    the judge follows a call into the helper that builds the markup (the
    manual-install intro is built by a method), `arguments` maps each of the
    helper's parameters to what THAT call passed for it and the frame it was
    passed from. So a parameter is judged by the value that actually reaches it,
    and a parameter that never reaches the markup (a flag read by an `if`) is
    never judged at all.
    """

    scope: ast.AST
    arguments: Mapping[str, tuple[ast.expr, _Frame]]
    depth: int


@dataclass
class MarkupVerdict:
    """What the judge found in one label's markup."""

    #: Each value that could put a tag into the markup, and why.
    problems: list[str] = field(default_factory=list)
    #: Each value it accepted, and why. The floors read this, so the escaping
    #: test cannot pass by finding no values to judge.
    accepted: list[str] = field(default_factory=list)


def _is_html_escape(node: ast.AST) -> bool:
    """`html.escape(...)`, the CALL: a mention in a comment or a string is not one."""
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "escape"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "html"
    )


def _parameters(scope: ast.AST) -> set[str]:
    """Every parameter name of a function; empty for a class or a module."""
    if not isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        return set()
    signature = scope.args
    named = [*signature.posonlyargs, *signature.args, *signature.kwonlyargs]
    for star in (signature.vararg, signature.kwarg):
        if star is not None:
            named.append(star)
    return {param.arg for param in named}


def _stores(target: ast.AST, name: str) -> bool:
    """True if `target` (an assignment target, loop variable, `as` name) binds `name`."""
    return any(
        isinstance(node, ast.Name)
        and node.id == name
        and isinstance(node.ctx, ast.Store)
        for node in ast.walk(target)
    )


def _bindings(name: str, scope: ast.AST) -> tuple[list[ast.expr], list[str]]:
    """What `scope` itself (not a nested function) assigns to `name`.

    Returns the values it is given, which the judge then judges in turn, and why
    each OTHER binding cannot be judged: a loop variable, an import, a name
    unpacked from a tuple. `x += v` counts `v` as a value, since the text `x`
    ends up holding is what it held before with `v` joined on.
    """
    values: list[ast.expr] = []
    refusals: list[str] = []
    for node in _own_nodes(scope):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    values.append(node.value)
                elif _stores(target, name):
                    refusals.append(f"is unpacked from `{ast.unparse(node.value)}`")
        elif (
            isinstance(node, (ast.AnnAssign, ast.NamedExpr))
            and isinstance(node.target, ast.Name)
            and node.target.id == name
        ):
            if node.value is not None:
                values.append(node.value)
        elif (
            isinstance(node, ast.AugAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == name
        ):
            if isinstance(node.op, ast.Add):
                values.append(node.value)
            else:
                refusals.append(f"is changed by `{ast.unparse(node)}`")
        elif isinstance(node, (ast.For, ast.AsyncFor)) and _stores(node.target, name):
            refusals.append("is a loop variable")
        elif isinstance(node, (ast.With, ast.AsyncWith)) and any(
            item.optional_vars is not None and _stores(item.optional_vars, name)
            for item in node.items
        ):
            refusals.append("is bound by `with … as`")
        elif isinstance(node, ast.ExceptHandler) and node.name == name:
            refusals.append("is bound by `except … as`")
        elif isinstance(node, (ast.Import, ast.ImportFrom)) and any(
            (alias.asname or alias.name.split(".")[0]) == name for alias in node.names
        ):
            refusals.append("is imported, so what it holds is not visible here")
        elif (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and node.name == name
        ):
            refusals.append("is a function or class, not a string")
        elif isinstance(node, (ast.Global, ast.Nonlocal)) and name in node.names:
            refusals.append("is declared global or nonlocal")
    return values, refusals


def _judge(
    expr: ast.expr, frame: _Frame, source: _Source, verdict: MarkupVerdict
) -> None:
    """Judge one expression whose text becomes part of a RichText label's markup.

    Accepted: a literal of ours; an `html.escape(...)` call; an f-string, a `+`,
    or an `x if c else y` made only of accepted parts; a `{…}` with a numeric
    format; a name every binding of which is accepted; and a call into a method
    of this class or a function of this module whose every `return` is accepted,
    with its parameters judged by what the call passed. Anything else is a
    problem, including every shape this judge cannot read.
    """
    shown = ast.unparse(expr)
    if frame.depth > _MAX_FOLLOW_DEPTH:
        verdict.problems.append(
            f"`{shown}`: still not traced to a literal or an html.escape call after "
            f"{_MAX_FOLLOW_DEPTH} steps"
        )
        return
    if isinstance(expr, ast.Constant):
        # A literal of ours IS the markup, not a value put into it. Bytes are the
        # exception: they print as `b'…'` with whatever they hold.
        if isinstance(expr.value, bytes):
            verdict.problems.append(f"`{shown}`: bytes print with what they hold")
        return
    if _is_html_escape(expr):
        verdict.accepted.append(f"`{shown}`: escaped")
        return
    if isinstance(expr, ast.JoinedStr):
        for part in expr.values:
            if isinstance(part, ast.FormattedValue):
                _judge_field(part, frame, source, verdict)
        return
    if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Add):
        _judge(expr.left, frame, source, verdict)
        _judge(expr.right, frame, source, verdict)
        return
    if isinstance(expr, ast.IfExp):
        _judge(expr.body, frame, source, verdict)
        _judge(expr.orelse, frame, source, verdict)
        return
    if isinstance(expr, ast.Name):
        _judge_name(expr.id, frame, source, verdict)
        return
    if isinstance(expr, ast.Call):
        _judge_call(expr, frame, source, verdict)
        return
    verdict.problems.append(
        f"`{shown}`: this sweep cannot trace this kind of expression "
        f"({type(expr).__name__}) to a literal of ours or an html.escape call"
    )


def _judge_field(
    part: ast.FormattedValue, frame: _Frame, source: _Source, verdict: MarkupVerdict
) -> None:
    """One `{…}` of an f-string: a number, or a value judged like any other."""
    spec = part.format_spec
    if spec is not None:
        pieces = spec.values if isinstance(spec, ast.JoinedStr) else [spec]
        if not all(isinstance(piece, ast.Constant) for piece in pieces):
            verdict.problems.append(
                f"`{ast.unparse(part.value)}`: a format spec computed at run time"
            )
            return
        spec_text = "".join(
            str(piece.value) for piece in pieces if isinstance(piece, ast.Constant)
        )
        if _NUMERIC_SPEC.fullmatch(spec_text):
            verdict.accepted.append(
                f"`{{{ast.unparse(part.value)}:{spec_text}}}`: a number"
            )
            return
    _judge(part.value, frame, source, verdict)


def _judge_name(
    name: str, frame: _Frame, source: _Source, verdict: MarkupVerdict
) -> None:
    """A name: judged by what reaches it, looked up the way Python looks it up."""
    values, refusals = _bindings(name, frame.scope)
    deeper = replace(frame, depth=frame.depth + 1)
    if name in frame.arguments:
        # A parameter of a helper we followed a call into: judge what that call
        # passed, in the frame it was passed from.
        passed, passed_from = frame.arguments[name]
        _judge(passed, replace(passed_from, depth=frame.depth + 1), source, verdict)
    elif name in _parameters(frame.scope):
        verdict.problems.append(
            f"`{name}` is a parameter, so its value comes from a caller this sweep "
            "does not follow: escape it where the markup is built"
        )
    elif not values and not refusals:
        if frame.scope is source.tree:
            verdict.problems.append(
                f"`{name}` is not assigned in this module (a builtin, or bound where "
                "this sweep cannot see)"
            )
            return
        # Bound nowhere in this function: Python looks in the module next (a
        # class body is not on a method's lookup path), and so does this.
        _judge_name(name, _Frame(source.tree, {}, frame.depth + 1), source, verdict)
        return
    verdict.problems.extend(f"`{name}` {why}" for why in refusals)
    for value in values:
        _judge(value, deeper, source, verdict)


def _callee(
    call: ast.Call, frame: _Frame, source: _Source
) -> tuple[ast.FunctionDef | ast.AsyncFunctionDef | None, bool]:
    """The helper `call` runs, if it is one this sweep can read, and if `self` is bound.

    Two shapes: `self.<method>(…)` for a method defined in the class the current
    function belongs to, and `<function>(…)` for a function defined at the top of
    this module. Anything else (an inherited method, another module's function, a
    method of a string) is not followed, and the caller reports it.
    """
    func = call.func
    if (
        isinstance(func, ast.Attribute)
        and isinstance(func.value, ast.Name)
        and func.value.id == "self"
    ):
        owner = source.parents.get(frame.scope)
        if isinstance(owner, ast.ClassDef):
            for item in owner.body:
                if (
                    isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and item.name == func.attr
                ):
                    static = any(
                        isinstance(decorator, ast.Name)
                        and decorator.id == "staticmethod"
                        for decorator in item.decorator_list
                    )
                    return item, not static
        return None, False
    if isinstance(func, ast.Name):
        for item in source.tree.body:
            if (
                isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                and item.name == func.id
            ):
                return item, False
    return None, False


def _judge_call(
    call: ast.Call, frame: _Frame, source: _Source, verdict: MarkupVerdict
) -> None:
    """A call (other than html.escape) that builds markup: judge what it returns."""
    shown = ast.unparse(call)
    callee, bound = _callee(call, frame, source)
    if callee is None:
        verdict.problems.append(
            f"`{shown}`: a call this sweep cannot follow to its markup. Escape each "
            "value where the markup is built: here, or in a method of this class or "
            "a function of this module that this calls"
        )
        return
    if any(isinstance(arg, ast.Starred) for arg in call.args) or any(
        keyword.arg is None for keyword in call.keywords
    ):
        verdict.problems.append(
            f"`{shown}`: `*`/`**` arguments hide which value reaches which parameter"
        )
        return
    signature = callee.args
    positional = [*signature.posonlyargs, *signature.args]
    # Defaults belong to the END of the positional list, and are evaluated where
    # the function is defined, not where it is called.
    defined_in = _Frame(source.parents[callee], {}, frame.depth + 1)
    arguments: dict[str, tuple[ast.expr, _Frame]] = {}
    for param, default in zip(
        positional[len(positional) - len(signature.defaults) :],
        signature.defaults,
        strict=True,
    ):
        arguments[param.arg] = (default, defined_in)
    for param, kw_default in zip(
        signature.kwonlyargs, signature.kw_defaults, strict=True
    ):
        if kw_default is not None:
            arguments[param.arg] = (kw_default, defined_in)
    passable = positional[1:] if bound else positional
    if len(call.args) > len(passable):
        verdict.problems.append(
            f"`{shown}`: more positional arguments than `{callee.name}` names"
        )
        return
    for param, arg in zip(passable, call.args, strict=False):
        arguments[param.arg] = (arg, frame)
    for keyword in call.keywords:
        if keyword.arg is not None:
            arguments[keyword.arg] = (keyword.value, frame)
    returns = [node for node in _own_nodes(callee) if isinstance(node, ast.Return)]
    if not returns:
        verdict.problems.append(f"`{callee.name}` returns nothing to read")
        return
    inside = _Frame(callee, arguments, frame.depth + 1)
    for node in returns:
        if node.value is None:
            verdict.problems.append(f"`{callee.name}` has a bare `return`")
        else:
            _judge(node.value, inside, source, verdict)


def label_sites(source: str, module: str) -> list[LabelSite]:
    """Every `QLabel` in the population in `source`, each judged against the rule.

    The population: every `QLabel(<non-literal>)`, and every `QLabel("<literal>")`
    whose literal holds markup Qt would show as typed characters (`hidden_markup`).

    Pure, and working on source text rather than on the tree under `src/`, so the
    test at the bottom can feed it snippets built to fail. Every matching call
    yields a site — a shape the matcher cannot check is a site WITH a problem,
    never a site skipped, because a sweep that quietly skips what it cannot read
    reports the unreadable ones as clean.

    A site that states RichText also carries the judge's verdict on its markup
    (`markup_problems`, `markup_accepted`), judged in the function it is built in.
    """
    parsed = _parse(source)
    tree = parsed.tree
    parents = parsed.parents

    sites: list[LabelSite] = []
    # In source order, so a report (and the snippets below) read top to bottom.
    calls = sorted(
        (node for node in ast.walk(tree) if isinstance(node, ast.Call)),
        key=_position,
    )
    for call in calls:
        if not _is_qlabel_call(call):
            continue
        hidden: str | None = None
        if not _text_is_not_literal(call):
            # `QLabel()`, or a label whose text is a literal of ours. A literal is
            # in the population only when Qt's guess about it goes wrong, which
            # for a literal is decided here, once (see `hidden_markup`).
            literal = _label_text(call)
            if not (
                isinstance(literal, ast.Constant) and isinstance(literal.value, str)
            ):
                continue
            hidden = hidden_markup(literal.value)
            if hidden is None:
                continue
        # Why a literal site is here, in front of whatever it gets wrong.
        lead = (
            f"its literal text holds `{hidden}` below a first line with no tag, so "
            "Qt's default AutoText shows that markup as typed characters; "
            if hidden
            else ""
        )
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
                    lead + "built inline, so nothing can be called on it: assign it "
                    "to a name first, then call setTextFormat on that name",
                    hidden_markup=hidden,
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
                    lead + f"`{name}` is never given setTextFormat(...) after it is "
                    "built, in the same function"
                    + (
                        ". State PlainText and drop the markup, or RichText with "
                        "<br> for each line break (markup reads `\\n` as a space)"
                        if hidden
                        else ""
                    ),
                    hidden_markup=hidden,
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
        markup = MarkupVerdict()
        text = _label_text(call)
        if stated == "RichText" and text is not None:
            _judge(text, _Frame(scope, {}, 0), parsed, markup)
        sites.append(
            LabelSite(
                where,
                function,
                stated,
                problem,
                tuple(markup.problems),
                tuple(markup.accepted),
                hidden_markup=hidden,
            )
        )
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


def _value_sites() -> list[LabelSite]:
    """The labels built from a value: the population the first rule is about."""
    return [site for site in _all_sites() if site.hidden_markup is None]


def _functions(parsed: _Source, module: str) -> dict[str, ast.AST]:
    """Every function/method/module scope in a parsed module, by `module::qualname`."""
    return {
        f"{module}::{_qualified_name(node, parsed.parents)}": node
        for node in ast.walk(parsed.tree)
        if isinstance(node, _SCOPES)
    }


# --- The population -----------------------------------------------------------


def test_the_sweep_finds_the_labels() -> None:
    """Floor first: a sweep over nothing reports no offenders for ever."""
    sites = _value_sites()
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
        f"{site.where}: {site.problem}" for site in _value_sites() if site.problem
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
    """Every value a RichText site puts into its markup is escaped, a number, or ours.

    Judged value by value (`_judge`), in the function that builds the label: one
    escaped value no longer vouches for the value beside it. A site whose markup
    its callers write is listed in `_MARKUP_FROM_CALLERS` and checked at those
    callers by the next test instead.
    """
    rich = [site for site in _value_sites() if site.stated == "RichText"]
    assert len(rich) >= _MIN_RICHTEXT_SITES, (
        f"only {len(rich)} RichText label(s) found (floor {_MIN_RICHTEXT_SITES}), "
        "so the escaping check below has nothing to hold to account"
    )
    # Floor on the VALUES, not only the sites, and of both accepted kinds: a judge
    # that found nothing to judge would report every site clean.
    accepted = [
        f"{site.where}: {why}"
        for site in rich
        if site.function not in _MARKUP_FROM_CALLERS
        for why in site.markup_accepted
    ]
    assert len(accepted) >= _MIN_JUDGED_VALUES, (
        f"the judge accepted only {len(accepted)} value(s) across the RichText "
        f"sites (floor {_MIN_JUDGED_VALUES}), so it is not reading their markup: "
        f"{accepted}"
    )
    assert any(why.endswith(": escaped") for why in accepted) and any(
        why.endswith(": a number") for why in accepted
    ), f"expected both an escaped value and a number among {accepted}"
    offenders = [
        f"{site.where} ({site.function}):\n    " + "\n    ".join(site.markup_problems)
        for site in rich
        if site.function not in _MARKUP_FROM_CALLERS and site.markup_problems
    ]
    assert not offenders, (
        "these labels render RichText, and put a value into their markup that is "
        "not escaped. A value from outside the app (a drive's name, a path, a "
        "MusicBrainz field, a tool's output) put into markup unescaped is read as "
        "markup: a `<` in it becomes a tag and what follows can vanish. Pass each "
        "such value through html.escape where the markup is built (a number may "
        "use a numeric format such as `:+d` instead), or, if the site truly shows "
        "only markup its callers wrote, list it in _MARKUP_FROM_CALLERS:\n  "
        + "\n  ".join(offenders)
    )


def test_markup_from_callers_is_escaped_by_every_caller() -> None:
    """The one exemption is checked where the escaping actually happens.

    An entry says "this site's markup is written elsewhere". That is a claim about
    other functions, so this test goes and reads them: every construction of the
    carrier that passes a non-literal markup field must pass markup whose every
    value `_judge` accepts, and the carrier's own default must be a literal. And
    the entry must still be needed: a site whose own markup the judge can trace
    to the end is not written by its callers, and an entry left on it would excuse
    whatever replaces it.
    """
    sites = {site.function: site for site in _value_sites()}
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
        assert sites[function].markup_problems, (
            f"{function} is listed in _MARKUP_FROM_CALLERS, but the judge traces its "
            "own markup to the end, so its callers do not write it: remove the entry"
        )

        builders: list[str] = []
        unescaped: list[str] = []
        default_is_literal: bool | None = None
        for module, source in modules.items():
            parsed = _parse(source)
            for scope_name, scope in _functions(parsed, module).items():
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
                        verdict = MarkupVerdict()
                        _judge(keyword.value, _Frame(scope, {}, 0), parsed, verdict)
                        if verdict.problems:
                            unescaped.append(
                                f"{module}:{node.lineno} ({scope_name}): "
                                + "; ".join(verdict.problems)
                            )
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
            f"{function} — with a value in it that is not escaped:\n  "
            + "\n  ".join(unescaped)
        )


# --- Literal labels whose markup Qt would show as typed characters -----------


def test_a_literal_label_qt_would_misread_states_its_format() -> None:
    """The literal half of the rule, and it needs no allowlist.

    A literal label is outside the value rule, because its text cannot change
    under it. But Qt's guess about a literal can still be wrong, and for a literal
    it is FIXED, so it is decided here: markup of ours below a first line that
    holds none is shown as typed characters. Such a label must state its format,
    the same as a label built from a value. Found 2026-09-28 in the uninstall
    dialog, whose intro showed `<b>Never touched:</b>`, tags and all.
    """
    texts = [
        text for source in _modules().values() for text in _literal_label_texts(source)
    ]
    assert len(texts) >= _MIN_LITERAL_LABELS, (
        f"only {len(texts)} literal QLabel text(s) read under {SRC} (floor "
        f"{_MIN_LITERAL_LABELS}), so the verdict below is about labels never read"
    )
    # The subject: the detector must see real markup in real code. The drive
    # wizard's accuraterip.com link is a literal whose first line Qt DOES read as
    # markup, so it is read, and correctly left alone.
    marked_up = [text for text in texts if "<a href=" in text]
    assert marked_up and all(hidden_markup(text) is None for text in marked_up), (
        f"the literal label holding a link was not found or was misjudged: {marked_up}"
    )
    offenders = [
        f"{site.where}: {site.problem}"
        for site in _all_sites()
        if site.hidden_markup is not None and site.problem
    ]
    assert not offenders, (
        "these QLabels are built from a literal whose markup Qt shows as typed "
        "characters: Qt's default AutoText decides from the FIRST line, and theirs "
        "holds no tag, so the user sees the tags. State the format right after "
        "building it: PlainText without the tags, or RichText with <br> for each "
        "line break:\n  " + "\n  ".join(offenders)
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


def test_the_literal_clause_finds_hidden_markup_and_nothing_else() -> None:
    """Non-triviality for the literal clause, and its converse.

    `hidden_markup` asks Qt itself, so each answer below is Qt's; the snippets
    then check that the sweep acts on that answer at the label.
    """
    # Qt's own answers, including the ones the clause must NOT act on.
    assert hidden_markup("This removes:\n\n<b>Never touched:</b> x") == "<b>"
    assert hidden_markup("First line\nTom &amp; Jerry") == "&amp;"
    assert hidden_markup("<b>Bold first line</b>\nmore") is None  # rendered
    assert hidden_markup("Plain <a href='x'>link</a> on line one") is None
    assert hidden_markup("Output:\n<stdin>: no such tag") is None  # not markup
    assert hidden_markup("Fixed words") is None

    uninstall_shape = (
        "def f(self):\n"
        "    intro = QLabel('Removes:\\n\\n<b>Never touched:</b> music', self)\n"
    )
    stated_plain = uninstall_shape + (
        "    intro.setTextFormat(Qt.TextFormat.PlainText)\n"
    )
    stated_rich = uninstall_shape + "    intro.setTextFormat(Qt.TextFormat.RichText)\n"
    inline = (
        "def f(form):\n    form.addRow(QLabel('Removes:\\n<b>Never touched:</b>'))\n"
    )
    first_line_markup = "def f():\n    label = QLabel('<b>Bold</b>\\nnext')\n"
    unknown_tag = "def f():\n    label = QLabel('Output:\\n<stdin>')\n"

    sites = label_sites(uninstall_shape, "s.py")
    assert [(s.hidden_markup, s.stated) for s in sites] == [("<b>", None)]
    assert sites[0].problem and "`<b>`" in sites[0].problem, sites[0].problem
    for name, snippet in (
        ("stated PlainText", stated_plain),
        ("stated RichText", stated_rich),
    ):
        assert _problems(snippet) == [None], f"{name}: {_problems(snippet)}"
    assert len(_problems(inline)) == 1 and _problems(inline)[0], "inline accepted"
    assert _problems(first_line_markup) == [], "Qt renders it; not in population"
    assert _problems(unknown_tag) == [], "no markup Qt knows; not in population"


def _rich_label(text: str, *setup: str, params: str = "self") -> str:
    """Source for a function that builds a RichText label from `text`, after `setup`.

    `setup` lines are indented into the function as they are given, so a line
    may open a block and the next one indent under it.
    """
    lines = [
        f"def f({params}):",
        *(f"    {line}" for line in setup),
        f"    label = QLabel({text}, self)",
        "    label.setTextFormat(Qt.TextFormat.RichText)",
    ]
    return "\n".join(lines) + "\n"


def _judged(snippet: str) -> tuple[list[str], list[str]]:
    """What the judge makes of every RichText label in `snippet`: problems, accepted."""
    rich = [s for s in label_sites(snippet, "s.py") if s.stated == "RichText"]
    assert rich, (
        f"the snippet builds no RichText label, so it tests nothing:\n{snippet}"
    )
    return (
        [why for site in rich for why in site.markup_problems],
        [why for site in rich for why in site.markup_accepted],
    )


#: `(name, snippet, what the problem must name)`: each way a value can reach a
#: RichText label's markup without being escaped. The third field is the SUBJECT:
#: a refusal that names some other value would pass a check that only counted
#: problems, for the wrong reason.
_UNESCAPED: Final[list[tuple[str, str, str]]] = [
    (
        "an unescaped value beside an escaped one (the review's drive-wizard case)",
        _rich_label(
            'f"Known read offset for {name} on {device}: <b>{offset:+d}</b>"',
            'name = html.escape(drive_label or "this drive")',
            params="self, drive_label, device, offset",
        ),
        "`device`",
    ),
    (
        "an html.escape call on something else in the same function",
        _rich_label(
            'f"<b>{title}</b>"', 'log.info(html.escape("x"))', params="self, title"
        ),
        "`title`",
    ),
    (
        "a name escaped by one assignment and raw after another",
        _rich_label(
            'f"<b>{name}</b>"',
            "name = html.escape(raw)",
            "if short:",
            "    name = raw",
            params="self, raw, short",
        ),
        "`raw`",
    ),
    (
        "escaped on one branch of a conditional only",
        _rich_label('f"<b>{html.escape(a) if c else a}</b>"', params="self, a, c"),
        "`a`",
    ),
    (
        "markup built in a variable first",
        _rich_label("text", 'text = f"<b>{title}</b>"', params="self, title"),
        "`title`",
    ),
    (
        "html.escape only inside a nested function",
        _rich_label(
            'f"<b>{title}</b>"',
            "def later():",
            "    return html.escape(title)",
            params="self, title",
        ),
        "`title`",
    ),
    (
        "html.escape only named, in a comment and in the markup's own words",
        _rich_label(
            'f"<b>{title}</b> (html.escape(title))"',
            "# html.escape(title) would go here",
            params="self, title",
        ),
        "`title`",
    ),
    (
        "%-formatting",
        _rich_label('"<b>%s</b>" % title', params="self, title"),
        "% title",
    ),
    (
        "str.format",
        _rich_label('"<b>{}</b>".format(title)', params="self, title"),
        ".format(title)",
    ),
    ("str.join", _rich_label('"".join(parts)', params="self, parts"), "join(parts)"),
    ("an attribute", _rich_label('f"<b>{self.title}</b>"'), "self.title"),
    (
        "a raw value with a padding format",
        _rich_label('f"<b>{title:>10}</b>"', params="self, title"),
        "`title`",
    ),
    (
        "`:c`, which prints the character with that code (`{60:c}` is `<`)",
        _rich_label('f"<b>{code:c}</b>"', params="self, code"),
        "`code`",
    ),
    (
        "a fill character, which is repeated into the output",
        _rich_label('f"<b>{n:<>5d}</b>"', params="self, n"),
        "`n`",
    ),
    (
        "a format spec computed at run time",
        _rich_label('f"<b>{n:{spec}}</b>"', params="self, n, spec"),
        "`n`",
    ),
    (
        "a helper method given a raw value",
        "class D:\n"
        "    def __init__(self, spec):\n"
        "        label = QLabel(self._markup(name=spec.name), self)\n"
        "        label.setTextFormat(Qt.TextFormat.RichText)\n"
        "    def _markup(self, *, name):\n"
        '        return f"<b>{name}</b> is ready"\n',
        "spec.name",
    ),
    (
        "a call this sweep cannot follow",
        _rich_label('f"<b>{render(x)}</b>"', params="self, x"),
        "render(x)",
    ),
    (
        "an imported name",
        "from elsewhere import TITLE\n" + _rich_label('f"<b>{TITLE}</b>"'),
        "`TITLE`",
    ),
    (
        "a loop variable",
        _rich_label(
            'f"<b>{item}</b>"', "for item in items:", "    pass", params="self, items"
        ),
        "`item`",
    ),
    ("a cycle", _rich_label('f"<b>{a}</b>"', "a = b", "b = a"), "steps"),
]


def test_the_escape_judge_refuses_every_unescaped_route_into_markup() -> None:
    """Non-triviality: each shape must fail, and fail naming the value at fault."""
    passed: list[str] = []
    for name, snippet, subject in _UNESCAPED:
        problems, _ = _judged(snippet)
        if not any(subject in why for why in problems):
            passed.append(f"{name}: {problems}")
    assert not passed, (
        "the escaping judge let these through, or refused them over a different "
        "value than the one at fault:\n  " + "\n  ".join(passed)
    )
    # Floor, so the table cannot be emptied into a pass.
    assert len(_UNESCAPED) >= 15


def test_the_escape_judge_accepts_the_shapes_the_real_sites_use() -> None:
    """And it must be able to say yes, or the real sites would be exempted instead.

    Each shape is one a real site uses today, or the plainest way to write one.
    """
    drive_wizard = _rich_label(
        'f"Known read offset for {name}: <b>{offset:+d}</b>." + clause',
        'name = html.escape(drive_label or "this drive")',
        'clause = " Detect is optional." if can_detect else ""',
        params="self, drive_label, offset, can_detect",
    )
    # The manual-install intro: markup built by a method, from an argument the
    # call escapes. The raw `ready` flag decides a branch and never reaches the
    # markup, so it must not be judged at all.
    helper = (
        "class D:\n"
        "    def __init__(self, spec):\n"
        "        label = QLabel(\n"
        "            self._markup(name=html.escape(spec.name), ready=spec.ready)\n"
        "        )\n"
        "        label.setTextFormat(Qt.TextFormat.RichText)\n"
        "    def _markup(self, *, name, ready, suffix='.'):\n"
        "        if ready:\n"
        '            return f"{name} is <b>ready</b>{suffix}"\n'
        '        return f"{name} needs <b>setup</b>{suffix}"\n'
    )
    joined = _rich_label(
        "text", 'text = "<b>A</b> "', "text += html.escape(x)", params="self, x"
    )
    module_constant = 'TITLE = "<b>Ours</b>"\n' + _rich_label(
        'f"{TITLE}: {html.escape(x)}"', params="self, x"
    )
    for name, snippet, expected in (
        ("the drive wizard's line", drive_wizard, 2),
        ("a helper method", helper, 2),
        ("a name extended with +=", joined, 1),
        ("a module constant of ours", module_constant, 1),
    ):
        problems, accepted = _judged(snippet)
        assert problems == [], f"{name}: {problems}"
        # And it READ the values: an empty verdict would also have no problems.
        assert len(accepted) == expected, f"{name}: {accepted}"
    assert _judged(drive_wizard)[1] == [
        "`html.escape(drive_label or 'this drive')`: escaped",
        "`{offset:+d}`: a number",
    ]


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


def test_the_uninstall_intro_shows_its_bold_words_not_their_tags(
    qapp: QApplication,
) -> None:
    """Tools → Uninstall showed `<b>Never touched:</b>`, tags and all.

    The intro is a literal of ours, but its first line held no tag, so Qt's
    AutoText showed the whole label as plain text. Measured before the fix
    (PySide6 6.11.2, offscreen): AutoText drew it pixel for pixel as PlainText.
    The list must still read as a list after the fix, because markup reads a
    line break as a space.
    """
    from platterpus.ui.uninstall_dialog import UninstallDialog

    dialog = UninstallDialog(build_teardown=lambda *a: None)
    intro = _labels_showing(dialog, "Never touched:")
    assert len(intro) == 1
    # The user's symptom first, then the cause.
    shown = _shown(intro[0])
    assert "<b>" not in shown and "</b>" not in shown, shown
    assert shown.startswith(
        "This removes what Platterpus installed on this computer:\n\n"
        "• menu and desktop shortcuts\n"
    ), shown
    assert "\n• the items ticked below\n\nNever touched: your music" in shown, shown
    assert intro[0].textFormat() != Qt.TextFormat.AutoText, (
        "the intro still leaves its format to Qt's guess"
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
