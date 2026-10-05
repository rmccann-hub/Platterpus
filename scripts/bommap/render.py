"""Assembly and the two renderings: the CycloneDX JSON and the Markdown block.
Both are written from the same `collect()` result, so they cannot disagree.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from functools import cache
from typing import Final

from bommap.ci_entries import _ci_entries
from bommap.model import (
    _CATEGORY_ORDER,
    _P,
    CATEGORIES,
    ROOT_REF,
    Entry,
    GeneratorError,
)
from bommap.python_entries import (
    _python_build_entries,
    _python_dev_entries,
    _python_runtime_entries,
)
from bommap.reading import _join, _project, _project_repository
from bommap.ripper_entries import (
    _container_entries,
    _ripper_build_entries,
    _ripper_entries,
)
from bommap.runtime_entries import _runtime_entries
from bommap.service_entries import _service_entries
from bommap.tool_entries import _data_entries, _desktop_entries, _host_tool_entries

#: The two lines that fence the generated block. The text between them is
#: replaced wholesale on every run; everything outside them is hand-written and
#: never touched.
BEGIN_MARKER: Final[str] = (
    "<!-- BEGIN GENERATED: emit_bom.py — do not hand-edit; "
    "regenerate with python3 scripts/emit_bom.py -->"
)


END_MARKER: Final[str] = "<!-- END GENERATED: emit_bom.py -->"


#: CycloneDX 1.7 (the maintainer's choice, 2026-10-05). Every field this script
#: writes also exists in 1.6; nothing 1.7-only is used, so a 1.6 reader that
#: ignores the version number reads it correctly too.
SPEC_VERSION: Final[str] = "1.7"


SCHEMA_URL: Final[str] = "http://cyclonedx.org/schema/bom-1.7.schema.json"


@cache
def collect() -> tuple[Entry, ...]:
    """Every entry, checked for unique refs and a closed graph, in a fixed order."""
    entries: list[Entry] = []
    entries += _runtime_entries()
    entries += _python_runtime_entries()
    entries += _python_dev_entries()
    taken = {e.ref.split(":", 1)[1] for e in entries if e.ref.startswith("pypi:")}
    entries += _python_build_entries(taken)
    entries += _ripper_entries()
    entries += _container_entries()
    entries += _ripper_build_entries()
    entries += _host_tool_entries()
    entries += _desktop_entries()
    entries += _data_entries()
    entries += _ci_entries()
    entries += _service_entries()

    refs = [e.ref for e in entries]
    duplicates = sorted({r for r in refs if refs.count(r) > 1})
    if duplicates:
        raise GeneratorError(f"duplicate bom-refs: {duplicates}")
    known = set(refs) | {ROOT_REF}
    dangling = sorted({r for e in entries for r in e.required_by if r not in known})
    if dangling:
        raise GeneratorError(f"required_by names unknown refs: {dangling}")
    unknown_category = sorted({e.category for e in entries} - set(_CATEGORY_ORDER))
    if unknown_category:
        raise GeneratorError(f"unknown categories: {unknown_category}")
    return tuple(
        sorted(
            entries, key=lambda e: (_CATEGORY_ORDER[e.category], e.name.lower(), e.ref)
        )
    )


def _properties(entry: Entry) -> list[dict[str, str]]:
    props: list[tuple[str, str]] = [(_P + "category", entry.category)]
    if entry.used_in:
        props.append((_P + "used-in", _join(entry.used_in)))
    if entry.enforced_in:
        props.append((_P + "pin-enforced-in", _join(entry.enforced_in)))
    if entry.constraint and not any(
        k == _P + "constraint" for k, _ in entry.properties
    ):
        props.append((_P + "constraint", entry.constraint))
    props += list(entry.properties)
    return [{"name": k, "value": v} for k, v in props]


def _external_refs(entry: Entry) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for kind, url, comment in entry.external_refs:
        item = {"type": kind, "url": url}
        if comment:
            item["comment"] = comment
        out.append(item)
    return out


def _component(entry: Entry) -> dict[str, object]:
    item: dict[str, object] = {"type": entry.cdx_type, "bom-ref": entry.ref}
    if entry.group:
        item["group"] = entry.group
    item["name"] = entry.name
    # `version` and `versionRange` are mutually exclusive, and `versionRange`
    # may only appear on an external component (CycloneDX 1.6+, kept in 1.7).
    if entry.version:
        item["version"] = entry.version
    elif entry.version_range and entry.is_external:
        item["versionRange"] = entry.version_range
    if entry.is_external:
        item["isExternal"] = True
    if entry.description:
        item["description"] = entry.description
    item["scope"] = entry.scope
    if entry.purl:
        item["purl"] = entry.purl
    if entry.ancestors:
        item["pedigree"] = {
            "ancestors": [
                {"type": "application", "group": group, "name": name, "purl": purl}
                for name, group, purl in entry.ancestors
            ],
            "notes": "A fork that tracks this upstream and keeps its version string.",
        }
    refs = _external_refs(entry)
    if refs:
        item["externalReferences"] = refs
    item["properties"] = _properties(entry)
    return item


def _service(entry: Entry) -> dict[str, object]:
    item: dict[str, object] = {"bom-ref": entry.ref}
    if entry.provider:
        item["provider"] = {"name": entry.provider}
    item["name"] = entry.name
    if entry.description:
        item["description"] = entry.description
    if entry.endpoints:
        item["endpoints"] = list(entry.endpoints)
    item["authenticated"] = False
    item["x-trust-boundary"] = True
    if entry.data:
        item["data"] = [
            {"flow": flow, "classification": what} for flow, what in entry.data
        ]
    refs = _external_refs(entry)
    if refs:
        item["externalReferences"] = refs
    item["properties"] = _properties(entry)
    return item


def dependency_graph() -> dict[str, list[str]]:
    """ref → the refs it depends on, inverted from each entry's ``required_by``.

    Only refs we KNOW the dependencies of appear as keys. CycloneDX reads a
    component absent from the graph as "dependencies unknown", which is the
    honest answer for, say, ffmpeg's own libraries; an empty list would claim
    it has none.
    """
    graph: dict[str, set[str]] = {ROOT_REF: set()}
    for entry in collect():
        for parent in entry.required_by:
            graph.setdefault(parent, set()).add(entry.ref)
    return {ref: sorted(children) for ref, children in sorted(graph.items())}


def bom() -> dict[str, object]:
    """The whole CycloneDX document."""
    from platterpus import __version__

    project = _project()
    entries = collect()
    repository = _project_repository()
    counts = _counts(entries)
    return {
        "$schema": SCHEMA_URL,
        "bomFormat": "CycloneDX",
        "specVersion": SPEC_VERSION,
        "version": 1,
        "metadata": {
            "lifecycles": [{"phase": "pre-build"}],
            "tools": {
                "components": [
                    {
                        "type": "application",
                        "group": "platterpus",
                        "name": "scripts/emit_bom.py",
                        "version": __version__,
                    }
                ]
            },
            "component": {
                "type": "application",
                "bom-ref": ROOT_REF,
                "name": str(project["name"]),
                "version": __version__,
                "description": str(project.get("description", "")),
                "licenses": [{"expression": str(project["license"])}],
                "purl": f"pkg:pypi/{project['name']}@{__version__}",
                "externalReferences": [{"type": "vcs", "url": repository}],
            },
            "properties": [
                {"name": _P + "generated-by", "value": "python3 scripts/emit_bom.py"},
                {"name": _P + "check", "value": "python3 scripts/emit_bom.py --check"},
                {
                    "name": _P + "human-readable-copy",
                    "value": "DEPENDENCIES.md (the generated block)",
                },
                *(
                    {"name": _P + f"count:{key}", "value": str(n)}
                    for key, n in counts.items()
                ),
            ],
        },
        "components": [_component(e) for e in entries if e.kind == "component"],
        "services": [_service(e) for e in entries if e.kind == "service"],
        "dependencies": [
            {"ref": ref, "dependsOn": children}
            for ref, children in dependency_graph().items()
        ],
    }


def _counts(entries: Sequence[Entry]) -> dict[str, int]:
    counts = {key: 0 for key, _title in CATEGORIES}
    for entry in entries:
        counts[entry.category] += 1
    return counts


def render_json() -> str:
    """The committed ``bom.cdx.json``, byte for byte."""
    return json.dumps(bom(), indent=2, ensure_ascii=False) + "\n"


def _cell(text: str) -> str:
    """A table cell: pipes escaped, newlines flattened."""
    return text.replace("|", "\\|").replace("\n", " ") or "—"


def _version_cell(entry: Entry) -> str:
    if entry.version:
        return f"`{entry.version}`"
    if entry.constraint:
        return f"`{entry.constraint}`"
    if entry.version_range:
        return f"`{entry.version_range.split('/', 1)[1]}`"
    return "unconstrained"


def render_markdown() -> str:
    """The block between the markers in ``DEPENDENCIES.md``, markers included."""
    entries = collect()
    components = [e for e in entries if e.kind == "component"]
    services = [e for e in entries if e.kind == "service"]
    counts = _counts(entries)
    lines: list[str] = [BEGIN_MARKER, ""]
    add = lines.append
    add(
        f"**{len(components)} components and {len(services)} services**, the same "
        "entries as `bom.cdx.json` (CycloneDX "
        f"{SPEC_VERSION}), from the same run of `scripts/emit_bom.py`."
    )
    add("")
    add("| Category | Entries |")
    add("|---|---|")
    for key, title in CATEGORIES:
        add(f"| {title} | {counts[key]} |")
    add("")
    for key, title in CATEGORIES:
        rows = [e for e in entries if e.category == key]
        if not rows:
            continue
        add(f"### {title} ({len(rows)})")
        add("")
        if key == "service":
            add("| Service | Endpoints | When | Used in |")
            add("|---|---|---|---|")
            for e in rows:
                when = next((v for k, v in e.properties if k == _P + "when"), "")
                endpoints = (
                    _join(f"`{u}`" for u in e.endpoints) or "not named in Platterpus"
                )
                add(
                    f"| `{_cell(e.name)}` | {_cell(endpoints)} | {_cell(when)} | {_cell(_join(e.used_in))} |"
                )
            add("")
            continue
        add(
            "| Name | Version / constraint | Scope | What it is for | Used in | Pin enforced in |"
        )
        add("|---|---|---|---|---|---|")
        for e in rows:
            label = f"{e.group}/{e.name}" if key == "ci-action" else e.name
            add(
                f"| `{_cell(label)}` | {_cell(_version_cell(e))} | {e.scope} | "
                f"{_cell(e.description)} | {_cell(_join(e.used_in))} | "
                f"{_cell(_join(e.enforced_in))} |"
            )
        add("")
        for e in rows:
            if not e.detailed:
                continue
            add(f"Details for `{e.name}`:")
            add("")
            for k, v in e.properties:
                add(f"- `{k.removeprefix(_P)}`: {v}")
            add("")
    add("### Dependency graph")
    add("")
    add("Who needs what, as the BOM's `dependencies` section records it. An entry")
    add("absent from the left column has dependencies Platterpus does not record.")
    add("")
    for ref, children in dependency_graph().items():
        add(f"- `{ref}` → " + _join(f"`{c}`" for c in children))
    add("")
    add(END_MARKER)
    return "\n".join(lines)


def splice(document: str, block: str) -> str:
    """``document`` with the text between the markers replaced by ``block``."""
    start = document.find(BEGIN_MARKER)
    end = document.find(END_MARKER)
    if start == -1 or end == -1 or end < start:
        raise GeneratorError(
            f"no {BEGIN_MARKER!r} … {END_MARKER!r} pair; "
            "add the two marker lines where the generated map belongs"
        )
    return document[:start] + block + document[end + len(END_MARKER) :]


def committed_block(document: str) -> str:
    """The generated block as committed, markers included, or ``""``."""
    start = document.find(BEGIN_MARKER)
    end = document.find(END_MARKER)
    if start == -1 or end == -1 or end < start:
        return ""
    return document[start : end + len(END_MARKER)]
