"""Critical rule #11, mechanically: **a tool that gates CI must not float.**

The rule is a paragraph in ``CLAUDE.md``:

    ``ruff format`` and ``mypy --strict`` change what they accept between minor
    releases, so a wide version range means a routine upstream release turns CI red
    with zero change to our code — and it reads as a code problem. ``ruff`` and
    ``mypy`` are pinned to the minor they were measured against.

**It was written in the file that does not gate, and absent from the one that
does.** ``pyproject.toml``'s ``dev`` extra pinned ``ruff>=0.15.22,<0.16``; the
``lint`` job in ``.github/workflows/ci.yml`` — the job that actually decides whether
a PR merges — installed ``ruff>=0.15,<1``, the entire 0.x line. Only ``typecheck``
used the pin, because it installs the dev extra. So the gate this rule exists to
protect was the one place the rule did not reach, and the first ruff 0.16 release
would have reddened CI on somebody's unrelated pull request. Found 2026-08-18 by an
enforcement audit that asked, of every "enforced by" claim in ``CLAUDE.md``, *what
actually enforces this?*

The general lesson, which is why this file exists rather than a one-line workflow
fix: **a rule about a gate has to be checked at the gate.** Writing the constraint
where it is convenient to read is how it ends up describing a file nobody runs.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Final

REPO_ROOT: Path = Path(__file__).resolve().parents[1]
PYPROJECT: Path = REPO_ROOT / "pyproject.toml"
CI_WORKFLOW: Path = REPO_ROOT / ".github" / "workflows" / "ci.yml"

#: The tools CLAUDE.md rule #11 names as gating. Not derived from the workflow: the
#: rule is about *these two specifically*, because their output changes between minor
#: releases in ways that fail a check rather than merely warn.
GATING_TOOLS: Final[tuple[str, ...]] = ("ruff", "mypy")

#: A pin whose upper bound is a MINOR, e.g. ``<0.16`` or ``<2.4``. ``<1`` is not one:
#: it admits every minor release in a major series, which is what floating means.
#:
#: **``<1.0`` is not one either, and this pattern used to accept it.** A trailing
#: ``.0`` makes a *major* bound look minor-shaped: ``<1.0`` and ``<1`` admit exactly
#: the same releases, so one character of decoration flipped the verdict and the check
#: could be satisfied by the precise value it exists to reject. Found by adversarial
#: review, 2026-08-18 — the same "can it be satisfied by the wrong thing?" shape this
#: file's own docstring is about, one level in.
#:
#: The bound is therefore compared against the FLOOR rather than pattern-matched
#: alone: see :func:`_bounds_are_a_minor_pin`.
_MINOR_UPPER_BOUND: Final[re.Pattern[str]] = re.compile(r"<\s*(\d+)\.(\d+)")

#: The ``>=`` floor of a requirement, so an upper bound can be judged relative to it.
_FLOOR: Final[re.Pattern[str]] = re.compile(r">=\s*(\d+)\.(\d+)")


def _bounds_are_a_minor_pin(spec: str) -> str:
    """``""`` if ``spec`` pins to a minor, else why not.

    A minor pin means the upper bound is the floor's **next minor** — ``>=0.15.22``
    with ``<0.16``. Anything else admits releases the pin was never measured against:

    * ``<1`` — the whole major series, the shape that shipped in ci.yml.
    * ``<1.0`` — identical to ``<1``, and what a bare pattern match let through.
    * ``<2.4`` against a ``>=0.15`` floor — a range spanning majors.

    Stated as the exact arithmetic relation rather than as a shape, because a shape
    is what was gameable.
    """
    floor = _FLOOR.search(spec)
    if floor is None:
        return f"{spec!r} has no `>=major.minor` floor to judge an upper bound against"
    upper = _MINOR_UPPER_BOUND.search(spec)
    if upper is None:
        return (
            f"{spec!r} has no minor-level upper bound at all (a bare `<N` admits every "
            f"minor release in major N)"
        )
    f_major, f_minor = int(floor.group(1)), int(floor.group(2))
    u_major, u_minor = int(upper.group(1)), int(upper.group(2))
    if (u_major, u_minor) != (f_major, f_minor + 1):
        return (
            f"{spec!r} is bounded at <{u_major}.{u_minor} but its floor is "
            f">={f_major}.{f_minor}; a minor pin bounds at the floor's NEXT minor "
            f"(<{f_major}.{f_minor + 1}). As written it admits releases the pin was "
            f"never measured against — and `<{f_major}.0`-style bounds are exactly the "
            f"`<{f_major}` this rule rejects, wearing a decimal point."
        )
    return ""


#: A pip install of one of the gating tools carrying a literal version constraint.
#: Matches the shape the defect had — ``pip install "ruff>=0.15,<1"`` — including a
#: bare ``pip install ruff==0.15.0``. Deliberately does NOT match the fixed form,
#: which installs ``"$spec"`` read out of ``pyproject.toml`` at run time.
_LITERAL_PIN: Final[re.Pattern[str]] = re.compile(
    r"pip\s+install[^\n]*[\"']?\b(?P<tool>ruff|mypy)\s*[<>=!~]"
)


def _joined(text: str) -> str:
    """``text`` with shell line continuations folded away.

    The detector's ``[^\n]*`` cannot cross a newline, so a pin written across a
    backslash continuation — the most natural formatting for a longer ``pip install``,
    and one a future edit would reach for precisely because the line got long — was
    invisible to it. Folding first means the detector sees what the *shell* sees.

    Also folds YAML block-scalar continuation (a bare newline inside a ``run: |``
    block still reaches the shell as a separate command, so that one is left alone;
    only the explicit backslash form is joined).
    """
    return re.sub(r"\\\s*\n\s*", " ", text)


def _dev_extra() -> list[str]:
    document = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    dev = document["project"]["optional-dependencies"]["dev"]
    assert isinstance(dev, list)
    return [str(entry) for entry in dev]


def _spec_for(tool: str) -> str:
    """The ``dev`` extra's requirement string for ``tool``."""
    for entry in _dev_extra():
        # Normalise the PEP 503 way, so `ruff` matches however it is spelled.
        if entry.replace("-", "_").lower().startswith(tool):
            return entry
    raise AssertionError(
        f"{tool!r} is not in pyproject's `dev` extra at all — CLAUDE.md rule #11 "
        f"names it as a gating tool, so its pin has to live somewhere"
    )


def test_every_gating_tool_is_pinned_to_a_minor() -> None:
    """The pin itself: an upper bound of ``<1`` is not a pin, it is a major range."""
    for tool in GATING_TOOLS:
        spec = _spec_for(tool)
        problem = _bounds_are_a_minor_pin(spec)
        assert not problem, (
            f"{problem} CLAUDE.md rule #11: a gating tool is pinned to the minor it "
            f"was measured against, because a routine upstream release otherwise "
            f"turns CI red with no change to our code."
        )


def test_the_minor_pin_check_rejects_the_shapes_that_look_like_pins() -> None:
    """Non-triviality for the check above, including the one it used to accept.

    ``<1.0`` is the interesting row: it admits exactly what ``<1`` admits, and the
    original pattern-match passed it. A check that accepts the value it names as the
    defect is worse than no check, because a pass gets cited.
    """
    assert _bounds_are_a_minor_pin("ruff>=0.15.22,<0.16") == ""
    assert _bounds_are_a_minor_pin("mypy>=2.3.0,<2.4") == ""
    for bad in (
        "ruff>=0.15.22,<1",  # the shape that shipped in ci.yml
        "ruff>=0.15.22,<1.0",  # identical to the above, one decimal point later
        "ruff>=0.15.22,<0.17",  # skips a minor it was never measured against
        "ruff>=0.15.22",  # no ceiling at all
        "ruff",  # no floor either
    ):
        assert _bounds_are_a_minor_pin(bad), f"{bad!r} was accepted as a minor pin"


def test_the_ci_gate_installs_the_pin_rather_than_repeating_it() -> None:
    """**The half that was missing**, and the reason the pin did not bind.

    A literal version in the workflow is a *second* copy of the pin, free to disagree
    with the first — and it did, for the whole life of the ``lint`` job. So the
    workflow must derive the spec instead of restating it.
    """
    workflow = _joined(CI_WORKFLOW.read_text(encoding="utf-8"))
    offenders = sorted({m.group("tool") for m in _LITERAL_PIN.finditer(workflow)})
    assert not offenders, (
        f"{CI_WORKFLOW.name} installs {offenders} with a literal version constraint. "
        f"That is a second copy of the pin in the file that actually gates, and the "
        f"two drifted: pyproject said `<0.16` while the lint job said `<1`. Read the "
        f"spec out of pyproject.toml at run time so there is one source of truth."
    )


def _executable_lines(text: str) -> list[str]:
    """The workflow's lines with comments stripped — what actually runs.

    **The floors below matched PROSE.** ``ci.yml`` carries a twelve-line explanatory
    comment block about this very rule, and it contains the words ``ruff``, ``mypy``
    and ``pyproject.toml`` — so ``"ruff" in workflow`` was satisfied by the comment
    that explains why ruff is pinned, with every ``run:`` step deleted. Label without
    subject, which is the `CLAUDE.md` rule the docstring was citing while breaking it.
    Found by adversarial review, 2026-08-18.

    A YAML comment is ``#`` to end of line, but ``#`` inside a quoted string is not,
    and a shell fragment can legitimately contain one. Only a ``#`` that starts a line
    (after whitespace) or follows whitespace outside quotes is treated as a comment —
    conservative in the direction that keeps *more* text, so this cannot hide a real
    install line from the detector above.
    """
    kept: list[str] = []
    for raw in _joined(text).splitlines():
        stripped = raw.strip()
        if stripped.startswith("#"):
            continue
        in_single = in_double = False
        cut = len(raw)
        for i, ch in enumerate(raw):
            if ch == "'" and not in_double:
                in_single = not in_single
            elif ch == '"' and not in_single:
                in_double = not in_double
            elif (
                ch == "#"
                and not in_single
                and not in_double
                and i
                and raw[i - 1] in " \t"
            ):
                cut = i
                break
        line = raw[:cut].rstrip()
        if line.strip():
            kept.append(line)
    return kept


def test_the_ci_gate_still_INVOKES_the_gating_tools_at_all() -> None:
    """The floor. Without it, deleting the install steps makes the test above pass.

    "Can this check be satisfied by finding nothing?" — it can, and this is the
    answer. Two strengthenings over the first version, both from review:

    * it reads **executable lines only**, because ci.yml's own comment block about
      rule #11 contains every word the old floor searched for, so the floor passed on
      a workflow with all its ``run:`` steps removed;
    * it requires the tool to be **invoked**, not mentioned — a step that installs
      ruff and never runs it is not a gate.
    """
    lines = _executable_lines(CI_WORKFLOW.read_text(encoding="utf-8"))
    body = "\n".join(lines)
    assert lines, f"{CI_WORKFLOW.name} has no executable lines at all"
    for tool in GATING_TOOLS:
        invoked = [ln for ln in lines if re.search(rf"\b{tool}\b\s", ln)]
        assert invoked, (
            f"{CI_WORKFLOW.name} never invokes {tool!r} outside comments — the gate it "
            f"is supposed to run has gone missing, and the pin check above would pass "
            f"quietly for exactly that reason"
        )
    # And a job must actually DERIVE the spec, which means reading pyproject in a
    # command — not naming it in a comment about why we read pyproject.
    derives = [ln for ln in lines if "pyproject.toml" in ln]
    assert derives, (
        "no executable line reads pyproject.toml, so nothing derives a pin — the "
        "literal-pin check above is satisfied by a workflow that installs nothing"
    )
    assert "pip install" in body, (
        "no executable line installs anything; the derived spec is never used"
    )


def test_the_floors_are_not_satisfied_by_the_explanatory_comments() -> None:
    """Non-triviality for the floor: prove the comment block alone does not pass it.

    Constructed from ci.yml's real comment text plus a bare ``jobs:`` skeleton — the
    state the old floor accepted. If this ever passes, the floor has gone back to
    matching prose.
    """
    comment_only = (
        "name: CI\n"
        "jobs:\n"
        "  lint:\n"
        "    steps:\n"
        "      # Derive the ruff spec from pyproject.toml rather than repeating it\n"
        "      # here: a literal version in this file is a second copy of the pin\n"
        "      # (CLAUDE.md rule #11), and mypy is pinned the same way.\n"
    )
    lines = _executable_lines(comment_only)
    for tool in GATING_TOOLS:
        assert not [ln for ln in lines if re.search(rf"\b{tool}\b\s", ln)], (
            f"the floor still sees {tool!r} in a comment-only workflow"
        )
    assert not [ln for ln in lines if "pyproject.toml" in ln]


def test_the_literal_pin_detector_actually_matches_the_shipped_defect() -> None:
    """Non-triviality, measured against the real line rather than argued.

    The exact text that shipped is asserted to match, and the exact text that
    replaced it is asserted not to. A detector verified only against the current
    (clean) file cannot be told apart from one that matches nothing.
    """
    shipped = '        run: python -m pip install "ruff>=0.15,<1"'
    assert _LITERAL_PIN.search(shipped), (
        "the detector does not match the line that actually shipped — it would have "
        "reported the tree clean while the defect was in it"
    )

    fixed = '          python -m pip install "$spec"'
    assert not _LITERAL_PIN.search(fixed), (
        "the detector matches the derived form too, so it can never be satisfied"
    )

    # And the other spelling a future edit is most likely to reach for.
    assert _LITERAL_PIN.search("run: pip install mypy==2.3.0")

    # **Across a shell line continuation**, which the raw detector cannot see: its
    # `[^\n]*` stops at the newline, so the pin was invisible in exactly the
    # formatting a longer install command invites. Folding first is the fix, and this
    # is the case that proves it — `_joined` is what the real check now applies.
    continued = (
        "        run: |\n"
        "          python -m pip install \\\n"
        '              "ruff>=0.15,<1" \\\n'
        "              pytest\n"
    )
    assert not _LITERAL_PIN.search(continued), (
        "the raw detector already crossed the continuation, so `_joined` is not the "
        "thing being tested here — re-derive this case"
    )
    assert _LITERAL_PIN.search(_joined(continued)), (
        "a literal pin written across a backslash continuation is still invisible to "
        "the check; `_joined` did not fold it"
    )


# --- Runtime dependencies whose BEHAVIOUR we depend on -----------------------
#
# Rule #11 was written about the tools that *gate* CI, on the reasoning that a
# floating version turns CI red with no change to our code. The same reasoning
# reaches a floating **runtime** dependency, and the consequence is worse: not a red
# build, a shipped regression.
#
# Two measured instances in this repository, which is what makes this a class rather
# than an anecdote:
#
#   * **PySide6 6.11.2** stopped resolving `QKeySequence.StandardKey.Quit` and
#     `.Preferences`, so the Quit and Settings menu items shipped with no keyboard
#     shortcut at all — WCAG 2.1.1, from somebody else's release (2026-08-18).
#   * **cryptography**: a `<50` ceiling excluded the only fix for CVE-2026-69247, so
#     `pip-audit` resolved the vulnerable top of the range and reddened CI with no
#     code change (DEPENDENCIES.md, 2026-08-04).
#
# A version range is a claim that every version in it behaves the same for us.
# Nothing verifies that claim, so the range has to be narrow enough that a change in
# behaviour arrives as a deliberate commit.

APPIMAGE_REQUIREMENTS: Final[Path] = (
    REPO_ROOT / "build" / "python-appimage" / "requirements.txt"
)

#: Runtime dependencies held to a minor-level bound, each with the reason.
#: **A ratchet in the same direction as the tools above: it may grow, never shrink.**
#: An entry leaving this set means someone decided a dependency may float again, and
#: that is a decision worth a commit message.
MINOR_PINNED_RUNTIME: Final[dict[str, str]] = {
    "PySide6": (
        "6.11.2 dropped the StandardKey bindings for Quit and Preferences, shipping "
        "menu items with no keyboard shortcut"
    ),
}


def _runtime_spec(dist: str) -> str:
    """The `[project].dependencies` requirement string for ``dist``."""
    document = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    for entry in document["project"]["dependencies"]:
        if str(entry).replace("-", "_").lower().startswith(dist.lower()):
            return str(entry)
    raise AssertionError(f"{dist!r} is not in [project].dependencies at all")


def _bounds(spec: str) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """``(floor, ceiling)`` as version tuples, for either spelling.

    Understands the two forms this repo uses — an explicit ``>=a.b.c,<x.y`` range and
    the compatible-release ``~=a.b.c`` (which is ``>=a.b.c,<a.(b+1)``). They have to
    be compared as *ranges* rather than as strings, because the AppImage
    requirements file cannot use ``<`` at all: python-appimage installs each line
    through a shell, so a ``<`` is read as a redirection and crashes the build (its
    own header documents this). Two spellings of one range is exactly the kind of
    pair that drifts, so this normalises before comparing.
    """
    tilde = re.search(r"~=\s*(\d+)\.(\d+)\.(\d+)", spec)
    if tilde:
        major, minor, patch = (int(g) for g in tilde.groups())
        return (major, minor, patch), (major, minor + 1)
    floor = re.search(r">=\s*(\d+)\.(\d+)\.(\d+)", spec)
    ceil = re.search(r"<\s*(\d+)\.(\d+)", spec)
    assert floor and ceil, f"cannot read bounds from {spec!r}"
    return tuple(int(g) for g in floor.groups()), tuple(int(g) for g in ceil.groups())


def test_behaviour_critical_runtime_deps_are_minor_pinned() -> None:
    """A `<7`-style bound admits every minor release in a major series."""
    for dist, why in MINOR_PINNED_RUNTIME.items():
        spec = _runtime_spec(dist)
        floor, ceiling = _bounds(spec)
        assert ceiling[:2] == (floor[0], floor[1] + 1), (
            f"{spec!r} is not bounded to the minor it was tested against "
            f"(floor {floor}, ceiling {ceiling}). {dist}: {why}. A wider range is a "
            f"claim that every version in it behaves the same, and nothing checks it."
        )


def test_the_shipped_pin_matches_the_declared_pin() -> None:
    """**The AppImage requirements file is what a user actually runs.**

    `pyproject.toml` governs a dev or pipx install; `build/python-appimage/
    requirements.txt` governs the bundle that gets downloaded and double-clicked —
    the project's primary distribution channel. Pinning one and not the other pins
    nothing that ships.

    The two use different spellings by necessity (see :func:`_bounds`), so this
    compares the resolved ranges rather than the text.
    """
    shipped = APPIMAGE_REQUIREMENTS.read_text(encoding="utf-8")
    for dist in MINOR_PINNED_RUNTIME:
        line = next(
            (
                ln.strip()
                for ln in shipped.splitlines()
                if ln.strip().startswith(dist) and not ln.strip().startswith("#")
            ),
            None,
        )
        assert line, f"{dist} is not in {APPIMAGE_REQUIREMENTS.name} — nothing ships it"
        assert _bounds(line) == _bounds(_runtime_spec(dist)), (
            f"{dist} is pinned differently in the two files:\n"
            f"  pyproject : {_runtime_spec(dist)!r} -> {_bounds(_runtime_spec(dist))}\n"
            f"  shipped   : {line!r} -> {_bounds(line)}\n"
            "The shipped one decides what a user runs. Bump both together."
        )


def test_the_pin_admits_both_wheels_we_actually_tested() -> None:
    """Non-triviality with a floor, and a guard against over-tightening.

    A pin narrow enough to exclude a version we verified would be a different
    mistake: 6.11.1 is what runs locally and 6.11.2 is what CI installs, and the
    whole point of the exercise was that BOTH are known-good. An `==6.11.1` would
    satisfy the minor-bound test above and quietly forfeit Qt's patch releases.
    """
    floor, ceiling = _bounds(_runtime_spec("PySide6"))
    for tested in ((6, 11, 1), (6, 11, 2)):
        assert floor <= tested, (
            f"the pin's floor {floor} excludes {tested}, a wheel we verified green"
        )
        assert tested[:2] < ceiling, (
            f"the pin's ceiling {ceiling} excludes {tested}, a wheel we verified green"
        )
