"""The dependency verdict a person reads, in one line.

**Why this exists.** The maintainer, 2026-09-28: Setup & Updates → *Check
dependencies* "seems to freeze, not respond, or give no error". One of the four
ways it looked dead was a result that could not be trusted: a check that stopped
early returned a partial report with no marker, and the Setup & Updates line then
called it complete — "✓ All required tools present" after probing two tools of
seven. The line lives here, beside the marker vocabulary, so every surface that
shows it (Setup & Updates today) reads one function.

**Pure text, no widgets**, so every verdict is testable without a display.
`deps.manager.describe_unchecked` is the one wording of an incomplete check.

**Tri-state, and never "all present" about a check that did not finish.** A check
that stopped early is marked ⚠ and names what it did not reach; it is not
allowed to borrow the ✓ of the tools it did.
"""

from __future__ import annotations

from typing import Final

from platterpus.deps.manager import describe_unchecked

#: The status marker vocabulary. **Never colour alone** — around 8% of men have
#: red/green colour-vision deficiency, and a greyscale screenshot or a
#: forced-colors theme drops hue entirely, so every level carries a glyph.
OK_MARK: Final[str] = "✓"
WARN_MARK: Final[str] = "⚠"
INFO_MARK: Final[str] = "ⓘ"

#: Where a user re-runs the check, as the menu path they would follow.
RERUN_PATH: Final[str] = "Tools → Setup & Updates… → Check dependencies"


def _item_name(item: object) -> str:
    """The name to show for a missing item.

    A real ``MissingItem`` carries only ``spec`` and ``probe``, so the spec's
    ``display_name`` is the name. The Setup & Updates line used to read a
    ``name`` attribute that no real item has, so every missing tool it listed
    rendered as ``?``; ``name`` stays as the fallback for callers that pass one.
    """
    spec = getattr(item, "spec", None)
    return str(
        getattr(spec, "display_name", None)
        or getattr(item, "name", None)
        or getattr(spec, "dep_id", None)
        or "?"
    )


def dependency_summary_line(report: object | None) -> str:
    """One line describing the last dependency probe, for a person.

    **Tri-state, like every other verdict here.** "We have not looked yet" is a
    real answer and must not render as "nothing is wrong": a window that says
    `✓ All present` before any probe has run would be asserting something it
    cannot know, which is the failure mode this project keeps a marker
    vocabulary for. The same holds for a check that stopped part-way: it reads
    ⚠ and says what it did not check, whatever the checked tools said.
    """
    if report is None:
        return f"{INFO_MARK} Not checked yet in this session."
    missing = list(getattr(report, "missing", []) or [])
    required = [
        m for m in missing if not getattr(getattr(m, "spec", None), "optional", False)
    ]
    optional = [
        m for m in missing if getattr(getattr(m, "spec", None), "optional", False)
    ]
    incomplete = describe_unchecked(report)
    parts: list[str] = []
    if required:
        names = ", ".join(_item_name(m) for m in required)
        parts.append(f"{WARN_MARK} {len(required)} required missing: {names}.")
    if incomplete:
        # Leads with its own marker when nothing required is missing, so an
        # incomplete check is never a ✓ line.
        parts.append(incomplete if required else f"{WARN_MARK} {incomplete}")
    elif not required:
        parts.append(f"{OK_MARK} All required tools present.")
    if optional:
        names = ", ".join(_item_name(m) for m in optional)
        parts.append(f"Optional not installed: {names}.")
    return " ".join(parts)
