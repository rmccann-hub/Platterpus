"""A label given its text LATER, by `setText(...)`, must state its format where it is built.

**The gap this closes.** `tests/test_labels_state_their_text_format.py` holds every
`QLabel(<value>)` to stating its text format, but most labels that show a value
are not built from one: they are built empty (`QLabel("", self)`) or from a
placeholder (`QLabel("Idle.", self)`), and the value arrives later through
`label.setText(value)`. Those were outside the sweep. The `TASKS.md` row that
recorded the gap counted 13 such labels on 2026-09-28, 8 of them in the rip
progress pane, and said the count might be low. Measured by this file on
2026-10-05 (PySide6 6.11.2), with the population closed by a second count (the
token count below): 115 text setters, 55 of which give a label a value; those
labels are built at 20 places (one helper builds the disc panel's seven), and 14
of those places stated no format. 8 in the rip progress pane, as the row said
(its status line quotes cyanrip's fatal sentence); the setup, uninstall and drive
wizards' status lines (each quotes the failing step's or the tool's own words);
the pending-installs dialog's per-row `FAILED: <error>`; and two lines of
Settings (the validation banner quotes what was typed, the filename preview
renders the user's template). The other 6 places were already PlainText. Under
Qt's default `AutoText` such a label renders whatever its first line suggests: a
`<` in a title or a tool's message can become formatting, or take the rest of the
line with it, silently (Critical rule #12: *every widget carrying dependency
output is `PlainText`*).

**How the receiver is found, and why with `ast`.** Each setter names its receiver
(`self._status_label`, `label`, `box`), and the rule is about the widget behind
that name, which was built somewhere else: in `__init__`, in another class of a
mixin family, in a helper that returns it, or in a dict. The resolver below traces
the receiver back the way a reviewer would:

* a local name, through each of its assignments in the function (all of them,
  whatever branch they are on), and through a closure to the function around it;
* `self.<attr>`, through every assignment to that attribute in the class and in
  every class it shares an inheritance family with (the main window is a mixin
  family, so a label built in one mixin can be filled in another);
* a call to a function or method of ours, through each value it returns;
* `x.get(k)`, `x[k]` and a loop over `x` or `x.values()`, through each value
  stored into `x`;
* `if isinstance(name, T):` around the setter, which decides the type outright;
* a call into Qt (`QGuiApplication.clipboard()`, `buttons.button(...)`), by its
  return type in PySide6's OWN shipped stubs (`QtWidgets.pyi`, `QtGui.pyi`), so
  what Qt returns is read from Qt, not from a list kept here.

Whether a type renders markup is asked of PySide6 too (its class hierarchy), not
listed: a `QLabel` or anything derived from it; a `QMessageBox`, whose labels take
the box's format; a `QTextEdit`, whose `setText` guesses the way AutoText does.
Every other widget's `setText` (a button, a line edit, the clipboard, a table
item) shows its text as written, and is counted but not judged.

**What it cannot resolve, said out loud and counted.** A parameter with no
annotation, a parameter whose widget a caller builds (this sweep does not follow
callers), and an attribute looked up by a name chosen at run time (`getattr`).
Each such receiver is listed in `_UNRESOLVED` with the reason. That list is a
ratchet: it may shrink, never grow (`_MAX_UNRESOLVED`), and an entry that no
longer matches a receiver fails until it is removed. A label known only by its
annotation (`box: QMessageBox`) is in it too: its type is known, but not where it
is built, so its format cannot be seen.

**What the rule then asks.** A label given a value later must state its format
right after it is built, in the function that builds it, as the sibling file
requires of a label built from a value (the same `pins_after`). Then, judged
across every `setTextFormat` this sweep can trace to that label:

* if it is ever **RichText**, each value given to it must be escaped, a number,
  or ours (the sibling file's `_judge`, value by value);
* if it is only ever **PlainText**, no markup of ours may be handed to it, because
  it would show the tags as typed characters. That is the failure a fix to
  PlainText could introduce, which is why it is checked here.

A `setText` passed as a slot (`worker.status.connect(label.setText)`) takes values
this sweep cannot read, so it may only feed a PlainText label. A message box must
be given `setTextFormat(Qt.TextFormat.PlainText)` right after it is built
(`tests/test_message_boxes_are_plaintext.py` holds the function that builds it
to the same).

**What this does NOT cover.** `setToolTip` (a tooltip guesses its format too),
`QWizardPage` titles, and text set by any route other than `setText` /
`setInformativeText` / a `setText` passed as a slot. `setDetailedText` is not in
the population: Qt shows it in a read-only text edit as plain text whatever it
holds (measured, and pinned in the message-box file). Bindings are read without
regard to order or branch, so a receiver is judged by every widget it could hold.
"""

from __future__ import annotations

import ast
import functools
import io
import tokenize
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import PySide6
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtGui import Qt as GuiQt  # the Qt namespace with QtGui's functions
from PySide6.QtWidgets import QApplication, QLabel
from test_labels_state_their_text_format import (
    _SCOPES,
    _STATED_FORMATS,
    MarkupVerdict,
    _Frame,
    _judge,
    _modules,
    _own_nodes,
    _parse,
    _qualified_name,
    _shown,
    _Source,
    _stated_format,
    hidden_markup,
    pins_after,
)

#: The methods that give a widget its text after it is built. `setInformativeText`
#: is a QMessageBox's second label, which takes the box's format (measured both
#: orders, PySide6 6.11.2, and pinned in `tests/test_message_boxes_are_plaintext.py`).
_TEXT_SETTERS: Final[frozenset[str]] = frozenset({"setText", "setInformativeText"})

#: The Qt classes whose text can be read as markup, and what to call each in a
#: message. Anything derived from one of them is that kind too (asked of PySide6's
#: own class hierarchy, so `QTextBrowser` is a text edit without being listed).
_MARKUP_KINDS: Final[dict[str, str]] = {
    "QLabel": "label",
    "QMessageBox": "message box",
    "QTextEdit": "text edit",
}

#: Floor on the setters examined: 109 `setText` (108 calls and one passed as a
#: slot) and 6 `setInformativeText` on 2026-10-05. A scan that found none would
#: report no offenders for ever.
_MIN_SETTERS_EXAMINED: Final[int] = 100

#: Floor on the setters that give a LABEL a value, the population the rule is
#: about: 55 on 2026-10-05.
_MIN_LABEL_VALUE_USES: Final[int] = 45

#: Floor on the places those labels are built (a constructor call each; one
#: helper builds the disc panel's seven): 20 on 2026-10-05.
_MIN_LABELS_GIVEN_VALUES: Final[int] = 16

#: Floor on the setters traced to a widget that shows text as written (a button,
#: a line edit, the clipboard): 25 on 2026-10-05. Without it, a resolver that
#: called everything a label would clear every floor above.
_MIN_PLAIN_USES: Final[int] = 18

#: Floor on the setters traced to a QMessageBox built where this sweep can see
#: it: 16 on 2026-10-05.
_MIN_MESSAGE_BOX_USES: Final[int] = 12

#: How many steps the resolver takes from one receiver before giving up. The real
#: receivers need five at most; a longer chain ends as unresolved, never as a guess.
_MAX_DEPTH: Final[int] = 12

#: Receivers this sweep cannot trace to where their widget is built, by
#: `module::Qualified.function: receiver`, each with why and what it is known to
#: be. A RATCHET: it may shrink, never grow (`_MAX_UNRESOLVED`), and an entry that
#: no longer matches an unresolved receiver fails until it is removed.
_UNRESOLVED: Final[dict[str, str]] = {
    "app.py::_arm_fatal_dialog_auto_dismiss._show_seconds_left: box": (
        "a parameter of `_arm_fatal_dialog_auto_dismiss`, annotated QMessageBox; "
        "the box comes from its caller, `_show_fatal_dialog`, which builds it and "
        "pins PlainText (tests/test_message_boxes_are_plaintext.py), and this "
        "sweep does not follow callers"
    ),
    "uiscript/runner.py::ScriptRunner._set_album_field: edit": (
        "looked up with `getattr(table, widget_name, None)`, a name chosen at run "
        "time; the script's album-field verbs name the track table's QLineEdits, "
        "which show text as written"
    ),
}

#: The size `_UNRESOLVED` may not exceed: what it held on 2026-10-05. Lower it
#: when an entry is resolved; never raise it.
_MAX_UNRESOLVED: Final[int] = 2


# --- PySide6's own answers ------------------------------------------------------


def _qt_class(name: str) -> type | None:
    """The PySide6 class called `name`, if QtWidgets, QtGui or QtCore has one."""
    for module in (QtWidgets, QtGui, QtCore):
        found = getattr(module, name, None)
        if isinstance(found, type):
            return found
    return None


def _qt_kind(name: str) -> str | None:
    """Which of `_MARKUP_KINDS` the Qt class `name` is, or None for neither/none."""
    cls = _qt_class(name)
    if cls is None:
        return None
    for base, kind in _MARKUP_KINDS.items():
        if issubclass(cls, getattr(QtWidgets, base)):
            return kind
    return None


@functools.cache
def _stub(module: str) -> dict[str, ast.ClassDef]:
    """Every class in one of PySide6's shipped stubs (`QtWidgets.pyi`), by name."""
    path = Path(PySide6.__file__).parent / f"{module}.pyi"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}


def _annotation_types(annotation: ast.expr | None) -> list[str]:
    """The class names an annotation allows, `None` dropped: `QLabel | None` is
    `["QLabel"]`, `PySide6.QtWidgets.QPushButton` is `["QPushButton"]`."""
    if annotation is None:
        return []
    if isinstance(annotation, ast.Constant):
        if isinstance(annotation.value, str):
            return _annotation_types(ast.parse(annotation.value, mode="eval").body)
        return []
    if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
        return _annotation_types(annotation.left) + _annotation_types(annotation.right)
    if isinstance(annotation, ast.Subscript):
        if _terminal(annotation.value) in ("Optional", "Union"):
            inner = annotation.slice
            parts = inner.elts if isinstance(inner, ast.Tuple) else [inner]
            return [name for part in parts for name in _annotation_types(part)]
        return []  # a container: what it holds is `_held_types`' question
    if isinstance(annotation, (ast.Name, ast.Attribute)):
        return [_terminal(annotation)]
    return []


def _held_types(annotation: ast.expr | None) -> list[str]:
    """What a container annotation holds: `dict[str, QLabel]` is `["QLabel"]`."""
    if isinstance(annotation, ast.BinOp):
        return _held_types(annotation.left) + _held_types(annotation.right)
    if not isinstance(annotation, ast.Subscript):
        return []
    inner = annotation.slice
    last = inner.elts[-1] if isinstance(inner, ast.Tuple) and inner.elts else inner
    return _annotation_types(last)


def _qt_returns(type_name: str, method: str) -> list[str] | None:
    """What a Qt method returns, read from PySide6's stubs; None if not found there.

    Looked up along the class's runtime MRO, each class in the stub of the module
    it lives in, keeping every overload's return type.
    """
    cls = _qt_class(type_name)
    if cls is None:
        return None
    for klass in cls.__mro__:
        stub_module = klass.__module__.rsplit(".", 1)[-1]
        if not stub_module.startswith("Qt"):
            continue
        stub = _stub(stub_module).get(klass.__name__)
        if stub is None:
            continue
        returns = [
            name
            for item in stub.body
            if isinstance(item, ast.FunctionDef) and item.name == method
            for name in _annotation_types(item.returns)
        ]
        if returns:
            return returns
    return None


# --- Where a widget comes from --------------------------------------------------


@dataclass(frozen=True)
class Built:
    """A widget built by a constructor call this sweep can see."""

    type_name: str
    module: str
    #: The function (or module) the constructor call sits in.
    scope: ast.AST
    #: The statement holding the call.
    statement: ast.AST
    call: ast.Call
    #: The source of the name or attribute the widget is assigned to, or None
    #: when it is built inline (passed straight to something), with no name to
    #: call `setTextFormat` on.
    target: str | None

    @property
    def where(self) -> str:
        return f"{self.module}:{self.call.lineno}"


@dataclass(frozen=True)
class Typed:
    """A widget whose type is known (annotation, `isinstance`, a Qt stub), not where
    it is built."""

    type_name: str
    module: str
    how: str


@dataclass(frozen=True)
class Unresolved:
    """A receiver this sweep cannot trace, and why."""

    reason: str


Origin = Built | Typed | Unresolved


def _terminal(expr: ast.expr) -> str:
    """The last name in `a.b.c` (`c`), or `""` for anything else."""
    if isinstance(expr, ast.Name):
        return expr.id
    if isinstance(expr, ast.Attribute):
        return expr.attr
    return ""


def _is_class_name(name: str) -> bool:
    """A constructor by its spelling: `QLabel`, `RipProgress`; not `ARGV`."""
    return name[:1].isupper() and not name.isupper()


def _enclosing(node: ast.AST, parents: Mapping[ast.AST, ast.AST]) -> ast.AST:
    """The scope (function, lambda, class, module) `node` sits in."""
    scope = parents[node]
    while not isinstance(scope, _SCOPES):
        scope = parents[scope]
    return scope


def _owning_class(
    scope: ast.AST, parents: Mapping[ast.AST, ast.AST]
) -> ast.ClassDef | None:
    """The class whose method `scope` is (or is nested in), for `self.<attr>`."""
    node: ast.AST | None = scope
    while node is not None:
        if isinstance(node, ast.ClassDef):
            return node
        node = parents.get(node)
    return None


def _params(scope: ast.AST) -> dict[str, ast.arg]:
    """A function's parameters by name; empty for a class or a module."""
    if not isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        return {}
    signature = scope.args
    named = [*signature.posonlyargs, *signature.args, *signature.kwonlyargs]
    named += [star for star in (signature.vararg, signature.kwarg) if star]
    return {param.arg: param for param in named}


def _dotted(module: str) -> str:
    """`ui/rip_progress.py` → `platterpus.ui.rip_progress`; a package → its name."""
    parts = ["platterpus", *module.removesuffix(".py").split("/")]
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


@dataclass(frozen=True)
class _Store:
    """One `self.<attr> = value` (or a class-body `attr: T = value`)."""

    module: str
    scope: ast.AST
    value: ast.expr | None
    annotation: ast.expr | None


class Index:
    """Every module of a package, parsed once, with the lookups the resolver makes.

    Built from `{module: source}` rather than read off the disk, so the snippet
    tests below can hand it a package of their own.
    """

    def __init__(self, sources: Mapping[str, str]) -> None:
        self.modules: dict[str, _Source] = {
            module: _parse(source) for module, source in sources.items()
        }
        by_dotted = {_dotted(module): module for module in self.modules}
        #: For each module, each name it imports from this package, as the module
        #: it comes from and its name there. Imports inside functions count too
        #: (the main window imports a dialog where it opens it).
        self.imports: dict[str, dict[str, tuple[str, str]]] = {}
        #: The module each class lives in.
        self.module_of: dict[ast.ClassDef, str] = {}
        self._ancestors: dict[ast.ClassDef, list[ast.ClassDef]] = {}
        self._family: dict[ast.ClassDef, list[ast.ClassDef]] = {}
        self._stores: dict[ast.ClassDef, dict[str, list[_Store]]] = {}
        for module, parsed in self.modules.items():
            package = _dotted(module).split(".")
            if not module.endswith("__init__.py"):
                package.pop()
            names: dict[str, tuple[str, str]] = {}
            for node in ast.walk(parsed.tree):
                if isinstance(node, ast.ClassDef):
                    self.module_of[node] = module
                elif isinstance(node, ast.ImportFrom):
                    base = (
                        package[: len(package) - node.level + 1] if node.level else []
                    )
                    source = by_dotted.get(
                        ".".join([*base, *[node.module or ""]]).strip(".")
                    )
                    if source is not None:
                        for alias in node.names:
                            names[alias.asname or alias.name] = (source, alias.name)
            self.imports[module] = names

    def parents(self, module: str) -> Mapping[ast.AST, ast.AST]:
        return self.modules[module].parents

    def definition(
        self, name: str, module: str, want: type[ast.AST]
    ) -> tuple[str, ast.AST] | None:
        """The top-level class (`want=ast.ClassDef`) or function named `name` in
        `module`, followed through imports from this package."""
        for _ in range(5):  # a re-export chain longer than this is not followed
            for node in self.modules[module].tree.body:
                if getattr(node, "name", None) != name:
                    continue
                if want is ast.ClassDef and isinstance(node, ast.ClassDef):
                    return module, node
                if want is not ast.ClassDef and isinstance(
                    node, (ast.FunctionDef, ast.AsyncFunctionDef)
                ):
                    return module, node
            imported = self.imports[module].get(name)
            if imported is None:
                return None
            module, name = imported
        return None

    def our_class(self, name: str, module: str) -> ast.ClassDef | None:
        hit = self.definition(name, module, ast.ClassDef)
        return hit[1] if hit is not None and isinstance(hit[1], ast.ClassDef) else None

    def ancestors(self, cls: ast.ClassDef) -> list[ast.ClassDef]:
        """`cls` and every class of ours it derives from, nearest first."""
        if cls not in self._ancestors:
            seen: list[ast.ClassDef] = []
            pending = [cls]
            while pending:
                here = pending.pop(0)
                if here in seen:
                    continue
                seen.append(here)
                for base in here.bases:
                    found = self.our_class(_terminal(base), self.module_of[here])
                    if found is not None:
                        pending.append(found)
            self._ancestors[cls] = seen
        return self._ancestors[cls]

    def family(self, cls: ast.ClassDef) -> list[ast.ClassDef]:
        """Every class an attribute of `self` can be assigned in, seen from `cls`.

        `cls`'s own ancestors, and for every class that derives from `cls`, that
        class and its ancestors: a mixin's `self` is the concrete window, which
        inherits every other mixin too.
        """
        if cls not in self._family:
            found = list(self.ancestors(cls))
            for other in self.module_of:
                lineage = self.ancestors(other)
                if cls in lineage:
                    found += [item for item in lineage if item not in found]
            self._family[cls] = found
        return self._family[cls]

    def stores(self, cls: ast.ClassDef) -> dict[str, list[_Store]]:
        """Every `self.<attr> = …` in `cls`'s own body and methods, by attribute."""
        if cls not in self._stores:
            module = self.module_of[cls]
            parents = self.parents(module)
            found: dict[str, list[_Store]] = {}
            for item in cls.body:
                if isinstance(item, ast.AnnAssign) and isinstance(
                    item.target, ast.Name
                ):
                    found.setdefault(item.target.id, []).append(
                        _Store(module, cls, item.value, item.annotation)
                    )
            for node in ast.walk(cls):
                if isinstance(node, ast.Assign):
                    targets, value, annotation = node.targets, node.value, None
                elif isinstance(node, ast.AnnAssign):
                    targets, value, annotation = (
                        [node.target],
                        node.value,
                        node.annotation,
                    )
                else:
                    continue
                for target in targets:
                    if (
                        isinstance(target, ast.Attribute)
                        and isinstance(target.value, ast.Name)
                        and target.value.id == "self"
                    ):
                        found.setdefault(target.attr, []).append(
                            _Store(module, _enclosing(node, parents), value, annotation)
                        )
            self._stores[cls] = found
        return self._stores[cls]

    def kind(self, type_name: str, module: str) -> str | None:
        """`label`, `message box` or `text edit` (see `_MARKUP_KINDS`), `own setter`
        for a class of ours that defines a text setter, or None for a widget that
        shows its text as written."""
        cls = self.our_class(type_name, module)
        if cls is None:
            return _qt_kind(type_name)
        for here in self.ancestors(cls):
            if any(
                isinstance(item, ast.FunctionDef) and item.name in _TEXT_SETTERS
                for item in here.body
            ):
                return "own setter"
        for base in self.qt_bases(cls):
            if _qt_kind(base):
                return _qt_kind(base)
        return None

    def qt_bases(self, cls: ast.ClassDef) -> list[str]:
        """The Qt classes `cls` derives from, through any classes of ours."""
        return [
            name
            for here in self.ancestors(cls)
            for base in here.bases
            for name in [_terminal(base)]
            if self.our_class(name, self.module_of[here]) is None
            and _qt_class(name) is not None
        ]


class Resolver:
    """Traces a receiver back to where its widget is built. See the module docstring."""

    def __init__(self, index: Index) -> None:
        self.index = index

    def origins(self, expr: ast.expr, module: str, at: ast.AST) -> list[Origin]:
        """Where the widget `expr` names comes from, read at the node `at`."""
        parents = self.index.parents(module)
        scope = _enclosing(at, parents)
        if isinstance(expr, ast.Name):
            narrowed = _narrowed(expr.id, at, scope, parents)
            if narrowed is not None:
                return [Typed(narrowed, module, f"isinstance({expr.id}, {narrowed})")]
        found = self._resolve(expr, scope, module, 0, frozenset())
        return found or [
            Unresolved(f"`{ast.unparse(expr)}` traces to no assignment this sweep sees")
        ]

    # A cycle (`label = self._x` … `self._x = label`) adds nothing new on its
    # second lap, so it returns nothing there and the other assignments supply the
    # origins. A receiver whose EVERY path is a cycle resolves to nothing, which
    # `origins` reports as unresolved rather than as clean.
    def _resolve(
        self,
        expr: ast.expr,
        scope: ast.AST,
        module: str,
        depth: int,
        seen: frozenset[int],
    ) -> list[Origin]:
        shown = ast.unparse(expr)
        if depth > _MAX_DEPTH:
            return [Unresolved(f"`{shown}`: not traced within {_MAX_DEPTH} steps")]
        if id(expr) in seen:
            return []
        seen, depth = seen | {id(expr)}, depth + 1
        if isinstance(expr, ast.Constant):
            return [] if expr.value is None else [Unresolved(f"`{shown}` is a literal")]
        if isinstance(expr, ast.Call):
            return self._call(expr, scope, module, depth, seen)
        if isinstance(expr, ast.Name):
            return self._name(expr.id, scope, module, depth, seen)
        if isinstance(expr, ast.Attribute):
            return self._attribute(expr, scope, module, depth, seen)
        if isinstance(expr, ast.Subscript):
            return self._held(expr.value, scope, module, depth, seen)
        if isinstance(expr, ast.IfExp):
            parts: list[ast.expr] = [expr.body, expr.orelse]
        elif isinstance(expr, ast.BoolOp):
            parts = list(expr.values)
        elif isinstance(expr, ast.NamedExpr):
            parts = [expr.value]
        else:
            return [Unresolved(f"`{shown}`: a {type(expr).__name__} is not traced")]
        return [
            o for part in parts for o in self._resolve(part, scope, module, depth, seen)
        ]

    def _built(self, call: ast.Call, type_name: str, module: str) -> Built:
        """The widget a constructor call builds, and the name it is assigned to."""
        parents = self.index.parents(module)
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
        return Built(
            type_name,
            module,
            _enclosing(call, parents),
            statement,
            call,
            ast.unparse(target) if target is not None else None,
        )

    def _call(
        self,
        call: ast.Call,
        scope: ast.AST,
        module: str,
        depth: int,
        seen: frozenset[int],
    ) -> list[Origin]:
        func = call.func
        shown = ast.unparse(call)
        name = _terminal(func)
        if isinstance(func, ast.Name) and name == "getattr":
            return [Unresolved(f"`{shown}` looks the attribute up by a run-time name")]
        # A constructor: `QLabel(...)`, `QtWidgets.QLabel(...)`, a class of ours.
        if _is_class_name(name) and (
            _qt_class(name) is not None or self.index.our_class(name, module)
        ):
            return [self._built(call, name, module)]
        if isinstance(func, ast.Attribute) and name in ("get", "pop", "setdefault"):
            return self._held(func.value, scope, module, depth, seen)
        if isinstance(func, ast.Name):
            callee = self.index.definition(func.id, module, ast.FunctionDef)
            if callee is not None:
                return self._returned(callee[1], callee[0], shown, depth, seen)
            return [Unresolved(f"`{shown}`: a call this sweep cannot follow")]
        if isinstance(func, ast.Attribute):
            return self._method(func, scope, module, depth, seen)
        return [Unresolved(f"`{shown}`: a call this sweep cannot follow")]

    def _returned(
        self,
        definition: ast.AST,
        module: str,
        shown: str,
        depth: int,
        seen: frozenset[int],
    ) -> list[Origin]:
        """What a function or method of ours returns: each `return`, traced."""
        found = [
            origin
            for node in _own_nodes(definition)
            if isinstance(node, ast.Return) and node.value is not None
            for origin in self._resolve(node.value, definition, module, depth, seen)
        ]
        annotated = _annotation_types(getattr(definition, "returns", None))
        if not found and annotated:
            return [Typed(t, module, f"`{shown}`'s annotation") for t in annotated]
        return found or [Unresolved(f"`{shown}`: its returns trace to nothing")]

    def _method(
        self,
        func: ast.Attribute,
        scope: ast.AST,
        module: str,
        depth: int,
        seen: frozenset[int],
    ) -> list[Origin]:
        """A method call: of a class of ours, through every definition of it in
        the class's family (an override is as reachable as the original); of a Qt
        object, by its return type in PySide6's own stubs."""
        shown = f"{ast.unparse(func)}(…)"
        owner_name = _terminal(func.value)
        # Each owner is a class of ours (its definition) or a Qt class (its name).
        owners: list[ast.ClassDef | str] = []
        if isinstance(func.value, ast.Name) and func.value.id == "self":
            owner = _owning_class(scope, self.index.parents(module))
            if owner is None:
                return [Unresolved(f"`{shown}` outside a class")]
            owners.append(owner)
        elif _is_class_name(owner_name) and _qt_class(owner_name) is not None:
            owners.append(owner_name)  # a static method: `QGuiApplication.clipboard()`
        else:
            for origin in self._resolve(func.value, scope, module, depth, seen):
                if isinstance(origin, Unresolved):
                    return [origin]
                ours = self.index.our_class(origin.type_name, origin.module)
                owners.append(ours if ours is not None else origin.type_name)
        found: list[Origin] = []
        for owner_type in owners:
            if isinstance(owner_type, ast.ClassDef):
                family = self.index.family(owner_type)
                definitions = [
                    (self.index.module_of[member], item)
                    for member in family
                    for item in member.body
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and item.name == func.attr
                ]
                for where, item in definitions:
                    found += self._returned(item, where, shown, depth, seen)
                if definitions:
                    continue
                # Not defined by us: a method the class inherits from Qt.
                qt_bases = self.index.qt_bases(owner_type)
                if not qt_bases:
                    return [Unresolved(f"`{shown}`: no `{func.attr}` this sweep sees")]
                owner_type = qt_bases[0]
            returned = _qt_returns(owner_type, func.attr)
            if returned is None:
                return [Unresolved(f"`{shown}`: not ours, and not in PySide6's stubs")]
            found += [
                Typed(
                    name, module, f"PySide6's stub ({owner_type}.{func.attr} → {name})"
                )
                for name in returned
            ]
        return found or [Unresolved(f"`{shown}`: a call this sweep cannot follow")]

    def _name(
        self,
        name: str,
        scope: ast.AST,
        module: str,
        depth: int,
        seen: frozenset[int],
    ) -> list[Origin]:
        """A name, through each assignment in its scope, else the scope around it."""
        found: list[Origin] = []
        typed: list[Origin] = []
        bound = False
        for node in _own_nodes(scope):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == name:
                        bound = True
                        found += self._resolve(node.value, scope, module, depth, seen)
                    elif _stores(target, name):
                        bound = True
                        found.append(
                            Unresolved(
                                f"`{name}` is unpacked from `{ast.unparse(node.value)}`"
                            )
                        )
            elif (
                isinstance(node, (ast.AnnAssign, ast.NamedExpr))
                and isinstance(node.target, ast.Name)
                and node.target.id == name
            ):
                bound = True
                if node.value is not None:
                    found += self._resolve(node.value, scope, module, depth, seen)
                if isinstance(node, ast.AnnAssign):
                    typed += [
                        Typed(t, module, f"`{name}`'s annotation")
                        for t in _annotation_types(node.annotation)
                    ]
            elif (
                isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension))
                and isinstance(node.target, ast.Name)
                and node.target.id == name
            ):
                bound = True
                found += self._looped(node.iter, scope, module, depth, seen)
            elif isinstance(node, (ast.With, ast.AsyncWith)) and any(
                item.optional_vars is not None and _stores(item.optional_vars, name)
                for item in node.items
            ):
                bound = True
                found.append(Unresolved(f"`{name}` is bound by `with … as`"))
        if bound:
            # What is assigned is the evidence; the annotation speaks only when
            # nothing assigned could be traced.
            return found or typed
        param = _params(scope).get(name)
        if param is not None:
            annotated = _annotation_types(param.annotation)
            if annotated:
                return [
                    Typed(t, module, f"parameter `{name}`'s annotation")
                    for t in annotated
                ]
            return [
                Unresolved(
                    f"`{name}` is a parameter with no annotation: its widget comes "
                    "from a caller, and this sweep does not follow callers"
                )
            ]
        if isinstance(scope, ast.Module):
            return [Unresolved(f"`{name}` is not assigned in this module")]
        parents = self.index.parents(module)
        outer = _enclosing(scope, parents)
        while isinstance(outer, ast.ClassDef):  # a class body is not on the path
            outer = _enclosing(outer, parents)
        return self._name(name, outer, module, depth, seen)

    def _attribute(
        self,
        expr: ast.Attribute,
        scope: ast.AST,
        module: str,
        depth: int,
        seen: frozenset[int],
    ) -> list[Origin]:
        """`self.<attr>` through the class family; `x.<attr>` through x's class."""
        shown = ast.unparse(expr)
        owners: list[ast.ClassDef] = []
        if isinstance(expr.value, ast.Name) and expr.value.id == "self":
            owner = _owning_class(scope, self.index.parents(module))
            if owner is None:
                return [Unresolved(f"`{shown}` outside a class")]
            owners.append(owner)
        else:
            for origin in self._resolve(expr.value, scope, module, depth, seen):
                if isinstance(origin, Unresolved):
                    return [origin]
                cls = self.index.our_class(origin.type_name, origin.module)
                if cls is None:
                    return [
                        Unresolved(f"`{shown}`: an attribute of a {origin.type_name}")
                    ]
                owners.append(cls)
        found: list[Origin] = []
        typed: list[Origin] = []
        for owner in owners:
            for cls in self.index.family(owner):
                for store in self.index.stores(cls).get(expr.attr, []):
                    typed += [
                        Typed(t, store.module, f"`{expr.attr}`'s annotation")
                        for t in _annotation_types(store.annotation)
                    ]
                    if store.value is not None:
                        found += self._resolve(
                            store.value, store.scope, store.module, depth, seen
                        )
        # What is assigned is the evidence; an annotation speaks only when nothing
        # this sweep can see is assigned (`self._x: QLabel` set by a caller).
        return found if found else typed

    def _looped(
        self,
        iterable: ast.expr,
        scope: ast.AST,
        module: str,
        depth: int,
        seen: frozenset[int],
    ) -> list[Origin]:
        """What a loop over `iterable` binds its variable to."""
        if isinstance(iterable, (ast.Tuple, ast.List, ast.Set)):
            return [
                origin
                for item in iterable.elts
                for origin in self._resolve(item, scope, module, depth, seen)
            ]
        if (
            isinstance(iterable, ast.Call)
            and isinstance(iterable.func, ast.Attribute)
            and iterable.func.attr == "values"
        ):
            return self._held(iterable.func.value, scope, module, depth, seen)
        if isinstance(iterable, (ast.Name, ast.Attribute)):
            return self._held(iterable, scope, module, depth, seen)
        return [Unresolved(f"a loop over `{ast.unparse(iterable)}`")]

    def _held(
        self,
        container: ast.expr,
        scope: ast.AST,
        module: str,
        depth: int,
        seen: frozenset[int],
    ) -> list[Origin]:
        """What a dict or list holds: each value stored into it, else its annotation.

        Stores are `c[k] = v`, `c.append(v)` / `c.setdefault(k, v)`, and the
        elements of a literal or comprehension assigned to `c`; for `self.c`, in
        every class of the family, otherwise in the function.
        """
        shown = ast.unparse(container)
        places: list[tuple[str, ast.AST]] = []
        if (
            isinstance(container, ast.Attribute)
            and _terminal(container.value) == "self"
        ):
            owner = _owning_class(scope, self.index.parents(module))
            for cls in self.index.family(owner) if owner is not None else []:
                places.append((self.index.module_of[cls], cls))
        elif isinstance(container, ast.Name):
            places.append((module, scope))
        else:
            return [Unresolved(f"what `{shown}` holds")]
        stored: list[tuple[str, ast.AST, ast.expr]] = []
        annotations: list[tuple[str, ast.expr]] = []
        for place_module, place in places:
            parents = self.index.parents(place_module)
            nodes = (
                ast.walk(place)
                if isinstance(place, ast.ClassDef)
                else _own_nodes(place)
            )
            for node in nodes:
                for value in _stored_into(node, shown):
                    stored.append((place_module, _enclosing(node, parents), value))
                if isinstance(node, ast.AnnAssign) and ast.unparse(node.target) in (
                    shown,
                    shown.removeprefix("self."),
                ):
                    annotations.append((place_module, node.annotation))
        found = [
            origin
            for where, place_scope, value in stored
            for origin in self._resolve(value, place_scope, where, depth, seen)
        ]
        typed: list[Origin] = [
            Typed(t, where, f"`{shown}`'s annotation")
            for where, annotation in annotations
            for t in _held_types(annotation)
        ]
        return found or typed or [Unresolved(f"nothing seen stored into `{shown}`")]


def _stores(target: ast.AST, name: str) -> bool:
    """True if an assignment target (a tuple, an `as` name) binds `name`."""
    return any(
        isinstance(node, ast.Name)
        and node.id == name
        and isinstance(node.ctx, ast.Store)
        for node in ast.walk(target)
    )


def _stored_into(node: ast.AST, container: str) -> Iterator[ast.expr]:
    """Each value `node` stores into the container whose source is `container`."""
    if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            if (
                isinstance(target, ast.Subscript)
                and ast.unparse(target.value) == container
            ):
                yield node.value
            elif ast.unparse(target) == container:
                value = node.value
                if isinstance(value, ast.Dict):
                    yield from (v for v in value.values)
                elif isinstance(value, (ast.List, ast.Tuple, ast.Set)):
                    yield from value.elts
                elif isinstance(value, ast.DictComp):
                    yield value.value
                elif isinstance(value, (ast.ListComp, ast.SetComp)):
                    yield value.elt
    elif (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in ("append", "setdefault", "insert")
        and ast.unparse(node.func.value) == container
        and node.args
    ):
        yield node.args[-1]


def _narrowed(
    name: str, at: ast.AST, scope: ast.AST, parents: Mapping[ast.AST, ast.AST]
) -> str | None:
    """The type an `if isinstance(name, T):` around `at` decides, if one does."""
    node = at
    while node is not scope:
        parent = parents[node]
        test = parent.test if isinstance(parent, ast.If) else None
        if (
            isinstance(parent, ast.If)
            and node in parent.body
            and isinstance(test, ast.Call)
            and _terminal(test.func) == "isinstance"
            and len(test.args) == 2
            and isinstance(test.args[0], ast.Name)
            and test.args[0].id == name
            and isinstance(test.args[1], (ast.Name, ast.Attribute))
        ):
            return _terminal(test.args[1])
        node = parent
    return None


# --- The population: every text setter in the package -------------------------


@dataclass(frozen=True)
class TextUse:
    """One `setText(...)`, `setInformativeText(...)`, or `setText` passed as a slot."""

    module: str
    #: `module::Qualified.function` the setter sits in.
    function: str
    line: int
    method: str
    receiver: ast.expr
    #: The value given, or None for a `setText` passed as a slot, whose values
    #: arrive later from a signal this sweep cannot read.
    argument: ast.expr | None
    scope: ast.AST
    origins: tuple[Origin, ...]

    @property
    def where(self) -> str:
        return f"{self.module}:{self.line}"

    @property
    def key(self) -> str:
        """How `_UNRESOLVED` names this receiver: stable across line moves."""
        return f"{self.function}: {ast.unparse(self.receiver)}"

    @property
    def literal(self) -> str | None:
        """The text given, when it is a string literal of ours."""
        argument = self.argument
        if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
            return argument.value
        return None

    @property
    def builts(self) -> list[Built]:
        return [origin for origin in self.origins if isinstance(origin, Built)]


def text_uses(index: Index) -> list[TextUse]:
    """Every text setter in the indexed package, its receiver traced. Source order."""
    resolver = Resolver(index)
    uses: list[TextUse] = []
    for module, parsed in index.modules.items():
        for node in ast.walk(parsed.tree):
            if not (
                isinstance(node, ast.Attribute)
                and node.attr in _TEXT_SETTERS
                and isinstance(node.ctx, ast.Load)
            ):
                continue
            parent = parsed.parents[node]
            argument: ast.expr | None = None
            if isinstance(parent, ast.Call) and parent.func is node:
                given = [*parent.args, *(kw.value for kw in parent.keywords)]
                # `setText()` with nothing is a TypeError at run time, not a value.
                argument = given[0] if given else ast.Constant("")
            scope = _enclosing(node, parsed.parents)
            uses.append(
                TextUse(
                    module,
                    f"{module}::{_qualified_name(scope, parsed.parents)}",
                    node.lineno,
                    node.attr,
                    node.value,
                    argument,
                    scope,
                    tuple(resolver.origins(node.value, module, at=node)),
                )
            )
    return sorted(uses, key=lambda use: (use.module, use.line))


def use_kind(use: TextUse, index: Index) -> str:
    """What the receiver is: `label`, `message box`, `text edit`, `plain` (shows
    its text as written), `mixed`, or `unresolved` (see `unresolved_reason`)."""
    kinds: set[str] = set()
    for origin in use.origins:
        if isinstance(origin, Unresolved):
            return "unresolved"
        kind = index.kind(origin.type_name, origin.module) or "plain"
        if kind == "own setter" or (kind != "plain" and isinstance(origin, Typed)):
            # A markup widget known only by its type: where it is built, and so
            # whether its format is stated, cannot be seen.
            return "unresolved"
        kinds.add(kind)
    if len(kinds) > 1:
        return "mixed"
    return kinds.pop() if kinds else "unresolved"


def unresolved_reason(use: TextUse, index: Index) -> str:
    """Why `use_kind` called a receiver unresolved, for the ratchet's message."""
    reasons: list[str] = []
    for origin in use.origins:
        if isinstance(origin, Unresolved):
            reasons.append(origin.reason)
            continue
        kind = index.kind(origin.type_name, origin.module)
        if kind == "own setter":
            reasons.append(f"{origin.type_name} defines its own text setter")
        elif kind and isinstance(origin, Typed):
            reasons.append(f"a {kind} known only by {origin.how}")
    return "; ".join(reasons) or "traces to nothing"


def stated_formats(index: Index) -> dict[ast.Call, list[tuple[str, str]]]:
    """Every `setTextFormat(...)` this sweep can trace to a widget, by its constructor.

    So a label pinned PlainText where it is built and switched to RichText
    somewhere else is known to be both.
    """
    resolver = Resolver(index)
    found: dict[ast.Call, list[tuple[str, str]]] = {}
    for module, parsed in index.modules.items():
        for node in ast.walk(parsed.tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "setTextFormat"
            ):
                for origin in resolver.origins(node.func.value, module, at=node.func):
                    if isinstance(origin, Built):
                        found.setdefault(origin.call, []).append(
                            (f"{module}:{node.lineno}", _stated_format(node))
                        )
    return found


def markup_pieces(expr: ast.expr) -> list[str]:
    """Markup of ours in a value: each literal piece of it that Qt reads as a tag.

    Only the literal parts of the value itself (an f-string's own text, each side
    of a `+`, each branch of `x if c else y`); a value inside `{…}` is not ours.
    """
    pieces: list[str] = []
    pending: list[ast.expr] = [expr]
    while pending:
        node = pending.pop()
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            pieces.append(node.value)
        elif isinstance(node, ast.JoinedStr):
            pending += [part for part in node.values if isinstance(part, ast.Constant)]
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            pending += [node.left, node.right]
        elif isinstance(node, ast.IfExp):
            pending += [node.body, node.orelse]
    found: list[str] = []
    for piece in pieces:
        markup = (
            piece.strip()[:40] if GuiQt.mightBeRichText(piece) else hidden_markup(piece)
        )
        if markup:
            found.append(markup)
    return found


def problems(
    use: TextUse, index: Index, formats: Mapping[ast.Call, list[tuple[str, str]]]
) -> list[str]:
    """Why one text setter breaks the rule; empty when it keeps it."""
    kind = use_kind(use, index)
    shown = ast.unparse(use.receiver)
    found: list[str] = []
    if kind == "mixed":
        kinds = sorted(
            {index.kind(o.type_name, o.module) or "plain" for o in use.builts}
        )
        return [f"`{shown}` may hold any of {kinds}; this sweep judges one kind"]
    if kind == "text edit" and use.literal is None:
        found.append(
            f"`{shown}` is a QTextEdit, whose setText guesses the format the way "
            "AutoText does: use setPlainText, or setHtml with every value escaped"
        )
    if kind == "message box":
        for built in use.builts:
            pins = (
                pins_after(built.statement, built.scope, built.target)
                if built.target
                else []
            )
            if not pins or _stated_format(pins[0]) != "PlainText":
                found.append(
                    f"the message box built at {built.where} is not given "
                    "setTextFormat(Qt.TextFormat.PlainText) right after it is built"
                )
    if kind != "label":
        return found
    literal = use.literal
    # A literal of ours cannot change under the label, so Qt's guess about it is
    # decided once, here (the sibling file's literal clause): only a literal whose
    # markup AutoText would show as typed needs the label to decide.
    needs_a_decision = literal is None or hidden_markup(literal) is not None
    stated: set[str] = set()
    for built in use.builts:
        pins = (
            pins_after(built.statement, built.scope, built.target)
            if built.target
            else []
        )
        if needs_a_decision and not pins:
            found.append(
                f"`{shown}` is built at {built.where}"
                + (f" as `{built.target}`" if built.target else ", inline,")
                + " and is never given setTextFormat(...) right after it is built, "
                "in the function that builds it"
            )
        for where, fmt in formats.get(built.call, []):
            stated.add(fmt)
            if fmt not in _STATED_FORMATS:
                found.append(
                    f"{where} states {fmt!r} for the label built at {built.where}; "
                    "write Qt.TextFormat.PlainText or Qt.TextFormat.RichText there"
                )
    if "RichText" in stated:
        if use.argument is None:
            found.append(
                f"`{shown}.setText` is passed as a slot, so the values it gets cannot "
                "be judged, and the label is RichText: make it PlainText"
            )
        else:
            verdict = MarkupVerdict()
            source = index.modules[use.module]
            _judge(use.argument, _Frame(use.scope, {}, 0), source, verdict)
            found += [f"RichText `{shown}` is given {why}" for why in verdict.problems]
    elif stated == {"PlainText"} and use.argument is not None:
        found += [
            f"PlainText `{shown}` is given markup of ours, `{piece}`, which it shows "
            "as typed characters: drop the markup, or make the label RichText"
            for piece in markup_pieces(use.argument)
        ]
    return found


@dataclass(frozen=True)
class _Package:
    index: Index
    uses: tuple[TextUse, ...]
    formats: dict[ast.Call, list[tuple[str, str]]]

    def kind(self, use: TextUse) -> str:
        return use_kind(use, self.index)

    def problems(self, use: TextUse) -> list[str]:
        return problems(use, self.index, self.formats)


def _package_of(sources: Mapping[str, str]) -> _Package:
    index = Index(sources)
    return _Package(index, tuple(text_uses(index)), stated_formats(index))


@functools.cache
def _real_package() -> _Package:
    """`src/platterpus`, indexed once per test process: every test below reads it."""
    return _package_of(_modules())


def _label_value_uses(package: _Package) -> list[TextUse]:
    """The population the rule is about: a label given anything but a literal."""
    return [
        use
        for use in package.uses
        if package.kind(use) == "label" and use.literal is None
    ]


def _setter_tokens(source: str) -> int:
    """How many times CODE names a text setter after a dot, counted by tokens.

    A second count of the population by a different mechanism than the tree
    walk above: comments and strings are tokens of their own kinds, so a mention
    of `setText` in prose is not counted, and nothing that is code is skipped.
    """
    count = 0
    previous: tokenize.TokenInfo | None = None
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if (
            token.type == tokenize.NAME
            and token.string in _TEXT_SETTERS
            and previous is not None
            and previous.string == "."
        ):
            count += 1
        if token.type not in (tokenize.NL, tokenize.NEWLINE, tokenize.COMMENT):
            previous = token
    return count


# --- The population -------------------------------------------------------------


def test_the_sweep_reads_every_text_setter() -> None:
    """Floors first, of every kind: a sweep over nothing reports no offenders."""
    package = _real_package()
    kinds = [package.kind(use) for use in package.uses]
    assert len(package.uses) >= _MIN_SETTERS_EXAMINED, (
        f"only {len(package.uses)} text setters found under src/platterpus (floor "
        f"{_MIN_SETTERS_EXAMINED}): the scan is broken, so its verdict means nothing"
    )
    values = _label_value_uses(package)
    labels = {built.call for use in values for built in use.builts}
    assert len(values) >= _MIN_LABEL_VALUE_USES, (
        f"only {len(values)} setters traced to a label given a value (floor "
        f"{_MIN_LABEL_VALUE_USES}): the resolver has stopped finding labels"
    )
    assert len(labels) >= _MIN_LABELS_GIVEN_VALUES, (
        f"those setters trace to only {len(labels)} labels (floor "
        f"{_MIN_LABELS_GIVEN_VALUES})"
    )
    assert kinds.count("plain") >= _MIN_PLAIN_USES, (
        f"only {kinds.count('plain')} setters traced to a widget that shows text "
        f"as written (floor {_MIN_PLAIN_USES}): a resolver calling everything a "
        "label would clear the floors above"
    )
    assert kinds.count("message box") >= _MIN_MESSAGE_BOX_USES, kinds.count(
        "message box"
    )
    # The subjects. The rip progress pane is the case the TASKS row named (eight
    # labels, rip status built partly from cyanrip's output), so a population
    # without them is looking in the wrong place whatever the counts say.
    in_rip_progress = {
        built.call
        for use in values
        for built in use.builts
        if built.module == "ui/rip_progress.py"
    }
    assert len(in_rip_progress) >= 8, sorted(u.where for u in values)
    # And the three routes that need the resolver, not a same-function match: a
    # label built in a helper that returns it, a dict of labels, and a setText
    # passed as a slot, whose values come from a worker.
    assert any(
        isinstance(built.scope, ast.FunctionDef)
        and built.scope.name == "_new_dependency_status_label"
        for use in values
        if use.module == "ui/main_window_deps.py"
        for built in use.builts
    ), "the dependency status label was not traced into the helper that builds it"
    assert any(
        use.module == "ui/dialogs/pending_installs.py" and use.builts for use in values
    ), "the pending-installs labels, kept in a dict, were not traced"
    assert any(
        use.argument is None and use.module == "ui/drive_setup_dialog.py"
        for use in values
    ), "the drive wizard's `connect(self._status_label.setText)` was not read"


def test_the_tokens_and_the_tree_count_the_same_setters() -> None:
    """Is the population closed? Two mechanisms must agree on it, module by module.

    The tree walk is what the rule judges; the token count is independent of it,
    so a shape the walk stopped seeing (a setter it no longer recognises) shows
    up as a module where the two disagree.
    """
    by_tokens = {
        module: count
        for module, source in _modules().items()
        if (count := _setter_tokens(source))
    }
    by_tree: dict[str, int] = {}
    for use in _real_package().uses:
        by_tree[use.module] = by_tree.get(use.module, 0) + 1
    assert by_tree == by_tokens
    assert sum(by_tokens.values()) >= _MIN_SETTERS_EXAMINED


def test_every_widget_given_text_later_states_its_format() -> None:
    """The rule itself."""
    package = _real_package()
    offenders = [
        f"{use.where} ({use.function}): {why}"
        for use in package.uses
        for why in package.problems(use)
    ]
    assert not offenders, (
        "these widgets are given text after they are built without deciding how "
        "it is read. Qt's default AutoText treats text as HTML when its first "
        "line happens to hold a known tag, and then drops what it cannot render, "
        "so a `<` in a tool's message, a title or a path can cut a label short or "
        "turn its text into formatting, silently (CLAUDE.md Critical rule #12). "
        "Call setTextFormat(Qt.TextFormat.PlainText) right after building the "
        "label, or RichText with every value escaped:\n  " + "\n  ".join(offenders)
    )
    # And the formats the rule read are real: every label in the population had
    # a format traced to it, through the resolver, from its own setTextFormat.
    unread = sorted(
        {
            built.where
            for use in _label_value_uses(package)
            for built in use.builts
            if not package.formats.get(built.call)
        }
    )
    assert not unread, f"no setTextFormat was traced to the labels built at {unread}"


def test_unresolved_receivers_are_listed_and_the_list_only_shrinks() -> None:
    """Counted, never dropped: each receiver this sweep cannot trace is named here."""
    package = _real_package()
    unresolved = {
        use.key: unresolved_reason(use, package.index)
        for use in package.uses
        if package.kind(use) == "unresolved"
    }
    unlisted = {key: why for key, why in unresolved.items() if key not in _UNRESOLVED}
    assert not unlisted, (
        "these text setters' receivers cannot be traced to where their widget is "
        "built, so whether it states its format cannot be checked. Make the "
        "receiver traceable (build it, or annotate it, where this sweep can see "
        "it), or, if that is not possible, list it in _UNRESOLVED with the "
        f"reason. The list may not grow past {_MAX_UNRESOLVED}:\n  "
        + "\n  ".join(f"{key}: {why}" for key, why in unlisted.items())
    )
    stale = sorted(set(_UNRESOLVED) - set(unresolved))
    assert not stale, (
        f"these _UNRESOLVED entries no longer match an unresolved receiver; remove "
        f"them and lower _MAX_UNRESOLVED: {stale}"
    )
    assert len(_UNRESOLVED) <= _MAX_UNRESOLVED
    for key, reason in _UNRESOLVED.items():
        assert len(reason) >= 60, f"{key}: the reason is too short: {reason!r}"
    assert len(_UNRESOLVED) * 20 < len(package.uses), "the list swallows the sweep"


# --- What PySide6 answers, checked rather than assumed --------------------------


def test_pyside6_answers_the_questions_this_sweep_asks_it() -> None:
    """The stubs and the class hierarchy are the dependency's own words; pin them.

    If an upgrade moved a method out of the stubs or renamed a class, the resolver
    would fall back to unresolved (which fails above), but this says why.
    """
    assert _qt_returns("QGuiApplication", "clipboard") == ["QClipboard"]
    assert _qt_returns("QDialogButtonBox", "button") == ["QPushButton"]
    assert _qt_returns("QLabel", "no_such_method") is None
    assert _qt_kind("QLabel") == "label"
    assert _qt_kind("QTextBrowser") == "text edit"  # derived, not listed
    assert _qt_kind("QMessageBox") == "message box"
    assert _qt_kind("QLineEdit") is None
    assert _qt_kind("QPushButton") is None


# --- The resolver and the rule, on constructed input ----------------------------

_HEAD: Final[str] = (
    "from PySide6.QtCore import Qt\n"
    "from PySide6.QtGui import QGuiApplication\n"
    "from PySide6.QtWidgets import (\n"
    "    QDialogButtonBox, QLabel, QLineEdit, QMessageBox, QTextEdit, QWidget,\n"
    ")\n"
)


def _snippet(**modules: str) -> _Package:
    """A package of `ui/<name>.py` modules, each given the Qt imports above."""
    return _package_of(
        {f"ui/{name}.py": _HEAD + source for name, source in modules.items()}
    )


def _verdicts(package: _Package) -> list[tuple[str, list[str]]]:
    """`(kind, problems)` for each text setter in a snippet package, in order."""
    return [(package.kind(use), package.problems(use)) for use in package.uses]


#: `(name, modules, what a problem must name)`: each must be refused, and refused
#: over the subject named, not over some other line of the snippet.
_REFUSED: Final[list[tuple[str, dict[str, str], str]]] = [
    (
        "built empty in __init__, given a value in another method, never pinned",
        {
            "a": "class A:\n"
            "    def __init__(self):\n"
            "        self._status = QLabel('', self)\n"
            "    def show(self, text):\n"
            "        self._status.setText(text)\n"
        },
        "built at ui/a.py:8 as `self._status`",
    ),
    (
        "pinned beside the setText, not where it is built",
        {
            "a": "class A:\n"
            "    def __init__(self):\n"
            "        self._status = QLabel(self)\n"
            "    def show(self, text):\n"
            "        self._status.setTextFormat(Qt.TextFormat.PlainText)\n"
            "        self._status.setText(text)\n"
        },
        "never given setTextFormat",
    ),
    (
        "a mixin: built in one class, filled in another",
        {
            "a": "class Builds:\n"
            "    def __init__(self):\n"
            "        self._status = QLabel(self)\n",
            "b": "class Fills:\n    def show(self, text):\n        self._status.setText(text)\n",
            "c": "from platterpus.ui.a import Builds\n"
            "from platterpus.ui.b import Fills\n"
            "class Window(Builds, Fills):\n"
            "    pass\n",
        },
        "built at ui/a.py:8",
    ),
    (
        "returned by a helper that does not pin it",
        {
            "a": "def make(parent):\n"
            "    label = QLabel(parent)\n"
            "    return label\n"
            "class A:\n"
            "    def show(self, text):\n"
            "        label = make(self)\n"
            "        label.setText(text)\n"
        },
        "built at ui/a.py:7 as `label`",
    ),
    (
        "kept in a dict and fetched with .get",
        {
            "a": "class A:\n"
            "    def __init__(self, keys):\n"
            "        self._labels = {}\n"
            "        for key in keys:\n"
            "            status = QLabel('', self)\n"
            "            self._labels[key] = status\n"
            "    def mark(self, key, text):\n"
            "        label = self._labels.get(key)\n"
            "        label.setText(text)\n"
        },
        "as `status`",
    ),
    (
        "a setText passed as a slot, into a RichText label",
        {
            "a": "class A:\n"
            "    def __init__(self, worker):\n"
            "        self._s = QLabel('', self)\n"
            "        self._s.setTextFormat(Qt.TextFormat.RichText)\n"
            "        worker.status.connect(self._s.setText)\n"
        },
        "passed as a slot",
    ),
    (
        "a RichText label given an unescaped value",
        {
            "a": "class A:\n"
            "    def __init__(self):\n"
            "        self._s = QLabel('', self)\n"
            "        self._s.setTextFormat(Qt.TextFormat.RichText)\n"
            "    def show(self, title):\n"
            "        self._s.setText(f'<b>{title}</b>')\n"
        },
        "`title` is a parameter",
    ),
    (
        "PlainText where built, switched to RichText elsewhere, given a raw value",
        {
            "a": "class A:\n"
            "    def __init__(self):\n"
            "        self._s = QLabel('', self)\n"
            "        self._s.setTextFormat(Qt.TextFormat.PlainText)\n"
            "    def bold(self):\n"
            "        self._s.setTextFormat(Qt.TextFormat.RichText)\n"
            "    def show(self, title):\n"
            "        self._s.setText(title)\n"
        },
        "RichText `self._s` is given",
    ),
    (
        "a PlainText label handed markup of ours, which it would show as tags",
        {
            "a": "class A:\n"
            "    def __init__(self):\n"
            "        self._s = QLabel('', self)\n"
            "        self._s.setTextFormat(Qt.TextFormat.PlainText)\n"
            "    def show(self, n):\n"
            "        self._s.setText(f'<b>{n}</b> tracks')\n"
        },
        "markup of ours, `<b>",
    ),
    (
        "AutoText stated where it is built",
        {
            "a": "def f(text):\n"
            "    label = QLabel()\n"
            "    label.setTextFormat(Qt.TextFormat.AutoText)\n"
            "    label.setText(text)\n"
        },
        "states 'AutoText'",
    ),
    (
        "a literal whose markup Qt would show as typed, on an unpinned label",
        {
            "a": "def f():\n"
            "    label = QLabel()\n"
            "    label.setText('Done.\\n<b>Note</b> the log')\n"
        },
        "never given setTextFormat",
    ),
    (
        "an override in a subclass returns a label the base class's pins do not cover",
        {
            "a": "class Base(QWidget):\n"
            "    def label(self):\n"
            "        lab = QLabel(self)\n"
            "        lab.setTextFormat(Qt.TextFormat.PlainText)\n"
            "        return lab\n"
            "    def show(self, text):\n"
            "        self.label().setText(text)\n"
            "class Child(Base):\n"
            "    def label(self):\n"
            "        lab = QLabel(self)\n"
            "        return lab\n"
        },
        "built at ui/a.py:15 as `lab`",
    ),
    (
        "a message box built in a helper that never pins it",
        {
            "a": "def make():\n"
            "    box = QMessageBox()\n"
            "    return box\n"
            "def show(text):\n"
            "    box = make()\n"
            "    box.setInformativeText(text)\n"
        },
        "message box built at ui/a.py:7",
    ),
    (
        "a name that may hold a label or a line edit",
        {
            "a": "def f(text, short):\n"
            "    w = QLineEdit() if short else QLabel()\n"
            "    w.setText(text)\n"
        },
        "may hold any of ['label', 'plain']",
    ),
    (
        "a QTextEdit given a value",
        {"a": "def f(text):\n    view = QTextEdit()\n    view.setText(text)\n"},
        "setPlainText",
    ),
]


def test_the_rule_refuses_each_unpinned_route_to_a_label() -> None:
    """Non-triviality: each shape must fail, naming the subject at fault."""
    passed: list[str] = []
    for name, modules, subject in _REFUSED:
        verdicts = _verdicts(_snippet(**modules))
        refused = [why for _kind, whys in verdicts for why in whys]
        if not any(subject in why for why in refused):
            passed.append(f"{name}: {verdicts}")
    assert not passed, (
        "the rule let these through, or refused them over a different subject:\n  "
        + "\n  ".join(passed)
    )
    assert len(_REFUSED) >= 12  # so the table cannot be emptied into a pass


#: `(name, modules, kind)`: each must be traced to that kind and accepted. For a
#: label, the resolver must also have found where it is built: "no problem" with
#: no construction found would be a pass for the wrong reason.
_ACCEPTED: Final[list[tuple[str, dict[str, str], str]]] = [
    (
        "pinned where built, filled in another method",
        {
            "a": "class A:\n"
            "    def __init__(self):\n"
            "        self._status = QLabel('Idle.', self)\n"
            "        self._status.setTextFormat(Qt.TextFormat.PlainText)\n"
            "    def show(self, text):\n"
            "        self._status.setText(f'{text} · done')\n"
        },
        "label",
    ),
    (
        "a mixin, pinned in the class that builds it",
        {
            "a": "class Builds:\n"
            "    def __init__(self):\n"
            "        self._status = QLabel(self)\n"
            "        self._status.setTextFormat(Qt.TextFormat.PlainText)\n",
            "b": "class Fills:\n    def show(self, text):\n        self._status.setText(text)\n",
            "c": "from platterpus.ui.a import Builds\n"
            "from platterpus.ui.b import Fills\n"
            "class Window(Builds, Fills):\n"
            "    pass\n",
        },
        "label",
    ),
    (
        "a cached label made by a helper that pins it (the dependency status shape)",
        {
            "a": "def make(bar):\n"
            "    label = QLabel(bar)\n"
            "    label.setTextFormat(Qt.TextFormat.PlainText)\n"
            "    return label\n"
            "class A:\n"
            "    _cached: QLabel | None = None\n"
            "    def show(self, text):\n"
            "        label = self._cached\n"
            "        if label is None:\n"
            "            label = make(self)\n"
            "            self._cached = label\n"
            "        label.setText(text)\n"
        },
        "label",
    ),
    (
        "fetched through a method of another class of ours",
        {
            "a": "class Panel(QWidget):\n"
            "    def __init__(self):\n"
            "        self._s = QLabel(self)\n"
            "        self._s.setTextFormat(Qt.TextFormat.PlainText)\n"
            "    def status(self):\n"
            "        return self._s\n"
            "def f(text):\n"
            "    panel = Panel()\n"
            "    panel.status().setText(text)\n"
        },
        "label",
    ),
    (
        "a slot into a PlainText label",
        {
            "a": "class A:\n"
            "    def __init__(self, worker):\n"
            "        self._s = QLabel('', self)\n"
            "        self._s.setTextFormat(Qt.TextFormat.PlainText)\n"
            "        worker.status.connect(self._s.setText)\n"
        },
        "label",
    ),
    (
        "RichText given an escaped value",
        {
            "a": "import html\n"
            "def f(title):\n"
            "    label = QLabel()\n"
            "    label.setTextFormat(Qt.TextFormat.RichText)\n"
            "    label.setText(f'<b>{html.escape(title)}</b>')\n"
        },
        "label",
    ),
    (
        "an unpinned label given only plain literals",
        {"a": "def f(done):\n    label = QLabel()\n    label.setText('Copied.')\n"},
        "label",
    ),
    (
        "a line edit given a value",
        {"a": "def f(text):\n    edit = QLineEdit()\n    edit.setText(text)\n"},
        "plain",
    ),
    (
        "isinstance decides the type of an unannotated parameter",
        {
            "a": "def f(widget, value):\n"
            "    if isinstance(widget, QLineEdit):\n"
            "        widget.setText(str(value))\n"
        },
        "plain",
    ),
    (
        "the clipboard, by PySide6's stub",
        {"a": "def f(text):\n    QGuiApplication.clipboard().setText(text)\n"},
        "plain",
    ),
    (
        "a dialog button, by PySide6's stub",
        {
            "a": "def f(text):\n"
            "    box = QDialogButtonBox()\n"
            "    box.button(QDialogButtonBox.StandardButton.Ok).setText(text)\n"
        },
        "plain",
    ),
    (
        "a message box pinned PlainText where it is built",
        {
            "a": "def f(text):\n"
            "    box = QMessageBox()\n"
            "    box.setTextFormat(Qt.TextFormat.PlainText)\n"
            "    box.setText(text)\n"
            "    box.setInformativeText(text)\n"
        },
        "message box",
    ),
]


def test_the_rule_accepts_the_shapes_the_real_code_uses() -> None:
    """And it must be able to say yes, having found what it judged."""
    wrong: list[str] = []
    for name, modules, kind in _ACCEPTED:
        package = _snippet(**modules)
        verdicts = _verdicts(package)
        if not verdicts or any(v != (kind, []) for v in verdicts):
            wrong.append(f"{name}: {verdicts}")
        elif kind != "plain" and not all(use.builts for use in package.uses):
            wrong.append(f"{name}: accepted without finding where it is built")
    assert not wrong, "\n  ".join(["these were misjudged:", *wrong])


#: `(name, modules, what the reason must name)`: shapes this sweep cannot trace.
#: Each must come out unresolved (counted in the ratchet), never accepted.
_UNTRACEABLE: Final[list[tuple[str, dict[str, str], str]]] = [
    (
        "a parameter with no annotation",
        {"a": "def f(label, text):\n    label.setText(text)\n"},
        "a parameter with no annotation",
    ),
    (
        "a label known only by its annotation",
        {"a": "def f(label: QLabel, text: str) -> None:\n    label.setText(text)\n"},
        "a label known only by parameter `label`'s annotation",
    ),
    (
        "an attribute looked up by a run-time name",
        {
            "a": "def f(table, name, text):\n"
            "    edit = getattr(table, name, None)\n"
            "    edit.setText(text)\n"
        },
        "run-time name",
    ),
    (
        "an attribute only ever assigned to itself",
        {
            "a": "class A:\n"
            "    def __init__(self):\n"
            "        self._s = self._s\n"
            "    def show(self, text):\n"
            "        self._s.setText(text)\n"
        },
        "traces to no assignment",
    ),
    (
        "a class of ours with its own setText",
        {
            "a": "class Wrapped(QWidget):\n"
            "    def setText(self, text):\n"
            "        pass\n"
            "def f(text):\n"
            "    w = Wrapped()\n"
            "    w.setText(text)\n"
        },
        "defines its own text setter",
    ),
]


def test_what_the_resolver_cannot_trace_is_unresolved_never_clean() -> None:
    """The converse of the floors: an unreadable receiver is counted, not passed."""
    wrong: list[str] = []
    for name, modules, reason in _UNTRACEABLE:
        package = _snippet(**modules)
        found = [
            (package.kind(use), unresolved_reason(use, package.index))
            for use in package.uses
        ]
        if len(found) != 1 or found[0][0] != "unresolved" or reason not in found[0][1]:
            wrong.append(f"{name}: {found}")
    assert not wrong, "\n  ".join(["these were not reported unresolved:", *wrong])


# --- The user-visible effect, on the real widgets -------------------------------

#: A value shaped like a tool's error, whose first line Qt WOULD read as HTML
#: (asserted below), with a tag Qt does not know and an entity after it: under
#: AutoText the first is bolded away, the second vanishes and the third decodes.
_LOOKS_LIKE_MARKUP: Final[str] = "<b>x</b>: <stdin> not found &amp; gone"


def test_the_markup_lookalike_is_the_case_that_matters() -> None:
    """The premise of the widget tests below, checked rather than assumed."""
    assert GuiQt.mightBeRichText(_LOOKS_LIKE_MARKUP)
    assert GuiQt.mightBeRichText(f"12:34:56 · {_LOOKS_LIKE_MARKUP}")


def test_the_rip_progress_pane_shows_a_value_that_looks_like_markup_as_written(
    qapp: QApplication,
) -> None:
    """The pane the TASKS row named: its labels show what they are given, verbatim.

    The status line is where cyanrip's fatal sentence is shown; the stall notice
    and the CTDB line carry what the main window and the CTDB check report; the
    verdict banner appends a post-rip check's reason.
    """
    from platterpus.ui.rip_progress import RipProgress

    pane = RipProgress()
    pane.set_status(_LOOKS_LIKE_MARKUP)
    pane.set_stall_notice(_LOOKS_LIKE_MARKUP)
    pane.set_ctdb_status(_LOOKS_LIKE_MARKUP)
    pane.downgrade_verdict(_LOOKS_LIKE_MARKUP)
    labels: dict[str, QLabel] = {
        "status": pane._status_label,
        "stall notice": pane._stall_label,
        "CTDB line": pane._ctdb_label,
        "verdict banner": pane._verdict_banner,
    }
    for name, label in labels.items():
        # The user's symptom first, then the cause.
        assert _LOOKS_LIKE_MARKUP in _shown(label), (name, _shown(label))
        assert label.textFormat() == Qt.TextFormat.PlainText, name
    assert _shown(pane._status_label).endswith(f" · {_LOOKS_LIKE_MARKUP}")


def test_the_setup_wizard_status_quotes_a_step_as_written(qapp: QApplication) -> None:
    """A running step's detail is the step's own words, shown verbatim."""
    from test_ui_host_setup_dialog import _FakeHost

    from platterpus.deps.step_engine import StepResult, StepStatus
    from platterpus.ui.host_setup_dialog import HostSetupDialog

    dialog = HostSetupDialog(host_setup=_FakeHost(True))
    dialog._on_step(StepResult("tools", "flac", StepStatus.RUNNING, _LOOKS_LIKE_MARKUP))
    assert _shown(dialog._status_label) == f"⏳ flac — {_LOOKS_LIKE_MARKUP}"
    assert dialog._status_label.textFormat() == Qt.TextFormat.PlainText
