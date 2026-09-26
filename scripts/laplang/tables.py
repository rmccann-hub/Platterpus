"""The statement kinds, their grades and their fields: LSL 1, and our amendments.

LSL 1 is the fork's spec, §"Kinds", transcribed. Each amendment adds to it, and
is switched on by its id (`A1`–`A8`), so the same checker answers both *"is this
a well-formed LSL 1 lap?"* and *"would it be under these amendments?"*.

Every field name is lowercase letters only, because that is LSL 1's field
grammar (see `grammar.FIELD_RE`). A name like `holds-for` cannot be an LSL field.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

#: kind -> the grades it takes. An empty set means the kind takes no grade.
LSL1_GRADES: Final[dict[str, frozenset[str]]] = {
    "FACT": frozenset({"measured", "read", "reproduced", "relayed"}),
    "NONE": frozenset(),
    "UNKNOWN": frozenset(),
    "DID": frozenset(),
    "WILL": frozenset(),
    "ACCEPT": frozenset(),
    "AMEND": frozenset(),
    "REFUSE": frozenset(),
    "CORRECT": frozenset(),
    "ASK": frozenset(),
    "VERDICT": frozenset(),
    "NOTE": frozenset(),
}

#: (kind, grade) -> the fields it requires, from the spec's table.
LSL1_REQUIRED: Final[dict[tuple[str, str | None], tuple[str, ...]]] = {
    ("FACT", "measured"): ("evidence",),
    ("FACT", "read"): ("evidence",),
    ("FACT", "reproduced"): ("re", "evidence"),
    ("FACT", "relayed"): ("source",),
    ("NONE", None): ("scope", "evidence"),
    ("UNKNOWN", None): ("reason",),
    ("DID", None): ("commit",),
    ("WILL", None): ("owner", "when"),
    ("ACCEPT", None): ("re",),
    ("AMEND", None): ("re", "to"),
    ("REFUSE", None): ("re", "because"),
    ("CORRECT", None): ("re", "was", "now"),
    ("ASK", None): ("target",),
    ("VERDICT", None): ("basis",),
    ("NOTE", None): (),
}

#: Every field LSL 1 defines. The spec's kinds table is a closed list of fields,
#: so a field outside it is refused: a misspelt `evidnce:` must not pass as a
#: field nobody reads. (The fork's checker refuses one too; its spec's list of
#: refusals does not say so. That gap is one of the things we report.)
LSL1_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "evidence",
        "re",
        "source",
        "scope",
        "reason",
        "commit",
        "owner",
        "when",
        "to",
        "because",
        "was",
        "now",
        "target",
        "breaks",
        "basis",
    }
)

#: Every amendment this checker implements, in order. The spec for each is
#: `docs/handshake/outbound/artifacts/lsl-amendments-1.md`.
AMENDMENTS: Final[tuple[str, ...]] = ("A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8")


@dataclass(frozen=True)
class Amendment:
    """What one amendment adds to the tables. Its checks live in `amend.py`."""

    grades: dict[str, frozenset[str]] = field(default_factory=dict)
    required: dict[tuple[str, str | None], tuple[str, ...]] = field(
        default_factory=dict
    )
    #: Fields added to kinds that already exist, by (kind, grade); None = any grade.
    extra_required: dict[tuple[str, str | None], tuple[str, ...]] = field(
        default_factory=dict
    )
    fields: frozenset[str] = frozenset()


#: A1 close conditions, A2 a pre-commit binds, A3 findings with origin first,
#: A4 a fact names what it holds for, A5 a measurement names its population,
#: A6 only a checkable claim can carry weight, A7 answers are threaded and GO
#: waits for blocking questions, A8 a correction carries evidence.
AMENDMENT_TABLES: Final[dict[str, Amendment]] = {
    "A1": Amendment(
        grades={"TERM": frozenset({"set", "met", "unmet", "waived", "pending"})},
        required={
            ("TERM", "set"): ("requires",),
            ("TERM", "met"): ("term", "evidence"),
            ("TERM", "unmet"): ("term", "reason"),
            ("TERM", "waived"): ("term", "override"),
            ("TERM", "pending"): ("term", "on", "remains"),
        },
        fields=frozenset(
            {"requires", "restates", "regression", "term", "override", "on", "remains"}
        ),
    ),
    "A2": Amendment(fields=frozenset({"verdict", "unless", "triggers"})),
    "A3": Amendment(
        grades={"FINDING": frozenset({"ours", "yours", "upstream", "unknown"})},
        required={
            ("FINDING", "ours"): ("in", "shape", "target", "evidence", "portable"),
            ("FINDING", "yours"): ("in", "shape", "target", "evidence"),
            ("FINDING", "upstream"): ("in", "shape", "target", "evidence"),
            ("FINDING", "unknown"): ("in", "shape", "target", "evidence"),
        },
        fields=frozenset({"in", "shape", "landed", "portable"}),
    ),
    "A4": Amendment(
        extra_required={
            ("FACT", "measured"): ("holds",),
            ("FACT", "read"): ("holds",),
            ("FACT", "reproduced"): ("holds",),
        },
        fields=frozenset({"holds"}),
    ),
    "A5": Amendment(
        extra_required={
            ("FACT", "measured"): ("examined",),
            ("NONE", None): ("examined",),
        },
        fields=frozenset({"examined", "missing"}),
    ),
    "A6": Amendment(),
    "A7": Amendment(fields=frozenset({"answers"})),
    "A8": Amendment(extra_required={("CORRECT", None): ("evidence",)}),
}


@dataclass(frozen=True)
class Tables:
    """The kinds, requirements and fields in force for one check."""

    grades: dict[str, frozenset[str]]
    required: dict[tuple[str, str | None], tuple[str, ...]]
    fields: frozenset[str]
    amendments: frozenset[str]
    #: Which rule requires each field: `LSL.2` for LSL 1's own table, or the
    #: amendment that added the requirement, so a missing `holds:` is reported
    #: as A4's and not as a defect in LSL 1.
    sources: dict[tuple[str, str | None, str], str]

    def requires(self, kind: str, grade: str | None) -> tuple[str, ...]:
        return self.required.get((kind, grade), ())

    def source(self, kind: str, grade: str | None, name: str) -> str:
        return self.sources.get((kind, grade, name), "LSL.2")


def tables_for(amendments: frozenset[str]) -> Tables:
    """LSL 1 with `amendments` applied, in their declared order."""
    grades = dict(LSL1_GRADES)
    required = dict(LSL1_REQUIRED)
    fields = set(LSL1_FIELDS)
    sources: dict[tuple[str, str | None, str], str] = {}
    for amendment_id in AMENDMENTS:
        if amendment_id not in amendments:
            continue
        table = AMENDMENT_TABLES[amendment_id]
        grades.update(table.grades)
        for key, names in table.required.items():
            required[key] = names
            sources.update({(key[0], key[1], name): amendment_id for name in names})
        for key, extra in table.extra_required.items():
            required[key] = required.get(key, ()) + extra
            sources.update({(key[0], key[1], name): amendment_id for name in extra})
        fields |= table.fields
    return Tables(grades, required, frozenset(fields), amendments, sources)
