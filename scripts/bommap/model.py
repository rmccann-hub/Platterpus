"""What one entry of the map is, the categories, and the error the generator raises."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

#: The repository root: scripts/bommap/model.py is two levels below it.
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]


#: Namespace for our own properties. CycloneDX reserves ``cdx:``; a project
#: prefix keeps ours from colliding with anybody's taxonomy.
_P: Final[str] = "platterpus:"


#: The ref of the thing being described. Everything else hangs off it.
ROOT_REF: Final[str] = "platterpus"


#: Categories, in the order a reader meets them. The key is written into each
#: entry as the ``platterpus:category`` property; the title heads its table.
CATEGORIES: Final[tuple[tuple[str, str], ...]] = (
    ("runtime", "Languages, runtimes and platforms"),
    ("python-runtime", "Python packages the application imports"),
    ("ripper", "The ripper (cyanrip) and its related projects"),
    ("container", "The ripping container"),
    ("ripper-build", "What the cyanrip fork is built from, inside the container"),
    ("host-tool", "External programs Platterpus runs or offers"),
    ("desktop", "Desktop interfaces"),
    ("data", "Bundled data"),
    ("python-dev", "Python packages for development and tests (the dev extra)"),
    ("python-build", "Python packages for building, releasing and CI"),
    ("ci-action", "GitHub Actions"),
    ("ci-tool", "CI and build programs"),
    ("ci-runner", "CI runner images"),
    ("service", "External services"),
)


_CATEGORY_ORDER: Final[dict[str, int]] = {
    key: index for index, (key, _title) in enumerate(CATEGORIES)
}


class GeneratorError(RuntimeError):
    """The code and this generator's annotations disagree.

    Raised rather than papered over: a map that quietly omits what it could not
    place is the "looks complete" artifact CLAUDE.md warns about.
    """


@dataclass(frozen=True)
class Entry:
    """One thing Platterpus has or relies on — a CycloneDX component or service.

    Kept deliberately flat so the JSON renderer and the Markdown renderer read
    the SAME fields; neither has facts the other lacks.
    """

    ref: str
    category: str
    name: str
    kind: str = "component"  # "component" or "service"
    cdx_type: str = "application"
    group: str = ""
    #: An exact version (or image tag) when the code pins one exactly.
    version: str = ""
    #: The constraint as the source writes it (">=6.11.1,<6.12"), for people.
    constraint: str = ""
    #: The same constraint in CycloneDX's ``vers`` syntax. Written only for an
    #: external component (``isExternal``), which is the only place 1.6+ allows it.
    version_range: str = ""
    is_external: bool = False
    scope: str = "required"
    purl: str = ""
    description: str = ""
    used_in: tuple[str, ...] = ()
    enforced_in: tuple[str, ...] = ()
    endpoints: tuple[str, ...] = ()
    provider: str = ""
    #: (flow, classification) pairs for a service's data.
    data: tuple[tuple[str, str], ...] = ()
    #: (type, url, comment) triples.
    external_refs: tuple[tuple[str, str, str], ...] = ()
    properties: tuple[tuple[str, str], ...] = ()
    #: Refs of the entries that need this one. Inverted into the graph.
    required_by: tuple[str, ...] = ()
    #: (name, group, purl) of an ancestor — a fork's upstream (CycloneDX pedigree).
    ancestors: tuple[tuple[str, str, str], ...] = ()
    #: Properties worth showing a person under the table, not only in the JSON.
    detailed: bool = False
