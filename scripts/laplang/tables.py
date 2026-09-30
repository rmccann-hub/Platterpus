"""The statement kinds, their grades and their fields: LSL 1, and what LSL 2 and 3 add.

LSL 1 is the fork's spec, §"Kinds", transcribed. Each amendment adds to it, and
is switched on by its id (`A1`–`A8` for LSL 2, `B1`–`B3` for LSL 3), so the same
checker answers both *"is this a well-formed LSL 1 lap?"* and *"would it be under
these amendments?"*.

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

#: The rules LSL 3 adds to LSL 2, from the shared proposal's §"LSL 3"
#: (`cyanrip@889a375:docs/handshake/PROPOSAL-lap-statement-language.md:204-252`):
#: B1 a `run:` names the commit it ran at, and `--rerun` checks what it printed;
#: B2 a `GO` needs a close condition to have been checked against; B3 an
#: `answers:` counts only on a statement that can carry weight. They are kept
#: apart from `AMENDMENTS` on purpose: `--amend all` means A1-A8, as it always
#: has, so no LSL 1 or LSL 2 check changes. Only `LSL: 3` switches these on.
LSL3_RULES: Final[tuple[str, ...]] = ("B1", "B2", "B3")

#: The rule LSL 4 adds to LSL 3, from round 30: C1, a `WILL` carrying `verdict:`
#: says exactly `when: our next lap`, the lap A2 binds (the fork's round 30 lap 3
#: S10, as our lap 4 S36 and their lap 5 S12 amend it). Carried by the version a
#: lap declares, since no checker can read when a lap was written: a side
#: declares `LSL: 4` once both checkers implement it, and an LSL 3 pre-commit
#: keeps the rule it was written under. Theirs: `cyanrip@049886f`.
LSL4_RULES: Final[tuple[str, ...]] = ("C1",)

#: The one `when:` a pre-commit may carry under C1.
PRE_COMMIT_WHEN: Final[str] = "our next lap"

#: What each `LSL: N` line switches on. LSL 2 is LSL 1 with A1-A8 and nothing else:
#: the fork defined it so and implemented it behind `LSL: 2` (their round 28 lap 3
#: S14), and asked whether ours would read it the same way (S18). LSL 3 is LSL 2
#: plus B1-B3 and nothing else (round 28: their lap 3 S22-S25, our lap 4
#: S22-S24), "so that LSL 2 stays exactly A1-A8". A lap that declares a version
#: missing here is "cannot check", never "refused".
LSL_VERSIONS: Final[dict[int, frozenset[str]]] = {
    1: frozenset(),
    2: frozenset(AMENDMENTS),
    3: frozenset(AMENDMENTS) | frozenset(LSL3_RULES),
    4: frozenset(AMENDMENTS) | frozenset(LSL3_RULES) | frozenset(LSL4_RULES),
}


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
    # LSL 3. B1 adds one field, `at:`, on any statement; B2 and B3 add nothing
    # to the tables and are checks only (`lsl3.py`, `round_rules.py`).
    "B1": Amendment(fields=frozenset({"at"})),
    "B2": Amendment(),
    "B3": Amendment(),
    # LSL 4. C1 adds nothing to the tables; its check is in `amend.py`.
    "C1": Amendment(),
}

#: The kinds that cannot carry weight: they make no claim, or none either side
#: can check. A6 refuses them in `basis:` and `because:`, B3 refuses an
#: `answers:` on them, and both ask `carries_no_weight`, so the two rules cannot
#: drift into two lists (the proposal's B3 row: "the statements A6 lets carry no
#: weight"). A `FACT relayed` is the one graded case.
NO_WEIGHT_KINDS: Final[frozenset[str]] = frozenset(
    {"NOTE", "ASK", "VERDICT", "WILL", "UNKNOWN"}
)


def carries_no_weight(kind: str, grade: str | None) -> bool:
    """True for a statement A6 and B3 give no weight: see `NO_WEIGHT_KINDS`."""
    return kind in NO_WEIGHT_KINDS or (kind == "FACT" and grade == "relayed")


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
    """LSL 1 with `amendments` applied, in their declared order: A1-A8, B1-B3, C1."""
    grades = dict(LSL1_GRADES)
    required = dict(LSL1_REQUIRED)
    fields = set(LSL1_FIELDS)
    sources: dict[tuple[str, str | None, str], str] = {}
    for amendment_id in AMENDMENTS + LSL3_RULES + LSL4_RULES:
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
