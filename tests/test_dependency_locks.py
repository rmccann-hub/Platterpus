"""Every hashed lock is current, exact, hashed, and is what the jobs install.

The 2026-10-27 review's follow-up to items 2.1 and 2.3: a version RANGE installs
whatever PyPI serves inside it that minute, so a compromised patch release of
`build`, `twine`, `python-appimage` or `pip-audit` would have installed in a job
holding `id-token: write`, and the AppImage bundled whatever was newest the day it
was built. `build/lock-requirements.sh` now resolves each set of ranges into a
lock that names one version of every package and the sha256 of every file, and
the jobs install with `pip install --require-hashes -r <lock>`.

A lock has two ways to go wrong quietly, and this file checks both:

* **It goes stale.** Somebody moves a range in `pyproject.toml` (or the AppImage's
  `requirements.txt`) and does not re-run the generator, so the lock keeps
  installing a version the range no longer admits. The range is the decision; the
  lock must sit inside it. So each lock's TOP-LEVEL pins are checked against the
  ranges they were resolved from, re-read here from the source files.
* **It stops being a lock.** A hand-edited line without a ``--hash`` makes pip
  refuse the whole file in hash mode, which is loud; a line with a range instead
  of ``==`` is refused too. Those are checked here so the failure is a test with a
  sentence, not a red release job.
* **It is edited by hand**, a deleted package included, which leaves a file that
  still parses and still sits inside its ranges (the follow-up review of
  2026-10-27). Reading the file cannot see that; regenerating it can. Every lock
  records the uv version and the ``--exclude-newer`` date that reproduce it, and
  ``bash build/lock-requirements.sh --check`` (ci.yml's ``lock-check`` job)
  regenerates and diffs. This file holds the header fields, holds the check to
  every lock and to the uv the headers name, and checks offline what it can: that
  no package a lock was pulled in by is missing from it.

And the half that makes a lock worth anything: **the jobs that publish, attest or
gate install from it, and only from it.** A lock nobody installs is decoration.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Final

REPO: Final[Path] = Path(__file__).resolve().parents[1]
PYPROJECT: Final[Path] = REPO / "pyproject.toml"
RECIPE_REQUIREMENTS: Final[Path] = (
    REPO / "build" / "python-appimage" / "requirements.txt"
)
GENERATOR: Final[Path] = REPO / "build" / "lock-requirements.sh"
BUILD_SCRIPT: Final[Path] = REPO / "build" / "build_appimage.sh"
WORKFLOWS: Final[Path] = REPO / ".github" / "workflows"

APPIMAGE_LOCK: Final[str] = "build/python-appimage/requirements.lock"


@dataclass(frozen=True)
class LockSpec:
    """What one lock must be resolved from, and how many packages it must hold."""

    label: str
    #: The generator's selectors, in its order; the lock's header must say these.
    inputs: tuple[str, ...]
    #: A floor on pinned packages, so an empty or truncated lock cannot pass.
    #: Measured 2026-10-27 with uv 0.11.32 (36, 36, 36, 29, 88); about 80 %.
    min_packages: int


#: Every lock the generator writes. **A new lock is added here** — the header
#: check below refuses a lock whose inputs differ from this table, and the
#: audit-floor check refuses a table the pip-audit job does not count.
LOCKS: Final[dict[str, LockSpec]] = {
    APPIMAGE_LOCK: LockSpec("appimage", ("recipe",), 28),
    "build/locks/release.lock": LockSpec(
        "release",
        (
            "extra:publish:build",
            "extra:appimage",
            "build-system",
            "dependencies:sigstore",
        ),
        28,
    ),
    "build/locks/publish.lock": LockSpec(
        "publish", ("extra:publish", "build-system"), 28
    ),
    "build/locks/audit.lock": LockSpec("audit", ("extra:dev:pip-audit",), 22),
    "build/locks/ci.lock": LockSpec(
        "ci", ("dependencies", "extra:dev", "build-system"), 70
    ),
    # The follow-up review of 2026-10-27, item 5: the required sbom job (69
    # packages that day) and the workflow linters (2: zizmor and shellcheck-py;
    # actionlint-py ships no wheel, so it is not here, and TASKS R91 says so).
    "build/locks/sbom.lock": LockSpec(
        "sbom", ("dependencies", "extra:sbom", "build-system"), 55
    ),
    "build/locks/ci-lint.lock": LockSpec(
        "ci-lint", ("extra:ci-lint:zizmor", "extra:ci-lint:shellcheck-py"), 2
    ),
}


def _normalise(name: str) -> str:
    """A distribution name the PEP 503 way."""
    return re.sub(r"[-_.]+", "-", name).lower()


# --- A requirement, read without `packaging` -----------------------------------
#
# `packaging` would do this, but it is not a declared dependency (it arrives only
# because pytest needs it), and tests/test_imports_are_declared.py refuses an
# import that resolves by luck. The shapes to read are few and all ours: the
# operators pyproject and requirements.txt use, over versions that are dotted
# integers. Every version in every lock is checked to be one, so a shape this
# reader does not understand fails loudly rather than comparing wrongly.

_NUMERIC_VERSION: Final[re.Pattern[str]] = re.compile(r"\d+(?:\.\d+)*")
_REQUIREMENT: Final[re.Pattern[str]] = re.compile(
    r"^\s*(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[[^\]]*\])?"
    r"\s*(?P<specs>[^;]*?)\s*(?:;.*)?$"
)
_CLAUSE: Final[re.Pattern[str]] = re.compile(
    r"^(?P<op>~=|==|!=|>=|<=|>|<)\s*(?P<version>\d+(?:\.\d+)*)$"
)


def _version(text: str) -> tuple[int, ...]:
    assert _NUMERIC_VERSION.fullmatch(text), f"not a dotted-integer version: {text!r}"
    return tuple(int(part) for part in text.split("."))


def _padded(a: tuple[int, ...], b: tuple[int, ...]) -> tuple[tuple[int, ...], ...]:
    width = max(len(a), len(b))
    return tuple(v + (0,) * (width - len(v)) for v in (a, b))


def _clause_holds(version: tuple[int, ...], op: str, bound: tuple[int, ...]) -> bool:
    if op == "~=":
        # PEP 440: `~=X.Y.Z` is `>=X.Y.Z, ==X.Y.*`; `~=X.Y` is `>=X.Y, ==X.*`.
        assert len(bound) >= 2, f"~= needs at least two components: {bound}"
        prefix = bound[:-1]
        return _clause_holds(version, ">=", bound) and version[: len(prefix)] == prefix
    left, right = _padded(version, bound)
    return {
        "==": left == right,
        "!=": left != right,
        ">=": left >= right,
        "<=": left <= right,
        ">": left > right,
        "<": left < right,
    }[op]


def _requirement(text: str) -> tuple[str, list[tuple[str, tuple[int, ...]]]]:
    """``(normalised name, [(operator, version), ...])`` for one requirement string."""
    match = _REQUIREMENT.match(text)
    assert match is not None, f"cannot read requirement {text!r}"
    clauses: list[tuple[str, tuple[int, ...]]] = []
    for raw in filter(None, (c.strip() for c in match.group("specs").split(","))):
        clause = _CLAUSE.match(raw)
        assert clause is not None, f"cannot read the clause {raw!r} of {text!r}"
        clauses.append((clause.group("op"), _version(clause.group("version"))))
    return _normalise(match.group("name")), clauses


def _satisfies(version: str, text: str) -> bool:
    """Whether ``version`` is inside the range requirement ``text`` states."""
    _, clauses = _requirement(text)
    return all(_clause_holds(_version(version), op, bound) for op, bound in clauses)


@dataclass(frozen=True)
class Pin:
    name: str
    version: str
    marker: str
    hashes: tuple[str, ...]


#: One requirement of a lock, after continuation lines are joined.
_PIN: Final[re.Pattern[str]] = re.compile(
    r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)==(?P<version>[^\s;\\]+)"
    r"(?:\s*;\s*(?P<marker>.*?))?"
    r"(?P<hashes>(?:\s+--hash=\S+)*)\s*$"
)
_HASH: Final[re.Pattern[str]] = re.compile(r"--hash=sha256:(?P<hex>[0-9a-f]{64})\b")


def _logical_lines(text: str) -> list[str]:
    """The lock's requirement lines, continuations joined, comments dropped."""
    out: list[str] = []
    current = ""
    for raw in text.splitlines():
        stripped = raw.strip()
        if stripped.startswith("#") or not stripped:
            if current:
                out.append(current.strip())
                current = ""
            continue
        if stripped.endswith("\\"):
            current += " " + stripped[:-1].strip()
            continue
        current += " " + stripped
        out.append(current.strip())
        current = ""
    if current:
        out.append(current.strip())
    return out


def _pins(text: str) -> list[Pin]:
    """Every requirement in a lock. A line that is not an exact, hashed pin raises."""
    pins: list[Pin] = []
    for line in _logical_lines(text):
        match = _PIN.match(line)
        assert match is not None, f"not an exact `name==version` requirement: {line!r}"
        hashes = tuple(h.group("hex") for h in _HASH.finditer(match.group("hashes")))
        declared = match.group("hashes").count("--hash=")
        assert declared == len(hashes), f"a --hash is not a sha256 of 64 hex: {line!r}"
        pins.append(
            Pin(
                name=_normalise(match.group("name")),
                version=match.group("version"),
                marker=(match.group("marker") or "").strip(),
                hashes=hashes,
            )
        )
    return pins


def _header(text: str, field: str) -> str:
    match = re.search(rf"^# {re.escape(field)}: (?P<value>.*)$", text, re.MULTILINE)
    assert match is not None, f"the lock's header has no `# {field}:` line"
    return match.group("value").strip()


def _read(rel: str) -> str:
    path = REPO / rel
    assert path.is_file(), (
        f"{rel} is missing; regenerate with bash build/lock-requirements.sh"
    )
    return path.read_text(encoding="utf-8")


def _lock_versions(rel: str) -> dict[str, str]:
    return {pin.name: pin.version for pin in _pins(_read(rel))}


# --- The ranges each lock is resolved from, re-read from their sources ---------


def _selected(selector: str) -> list[str]:
    """The requirement strings one generator selector names.

    Restated here rather than imported, so the generator and this check are two
    readings of pyproject that have to agree, not one reading trusted twice.
    """
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    kind, _, rest = selector.partition(":")
    specs: list[str]
    wanted: str | None
    if kind == "dependencies":
        specs = [str(s) for s in pyproject["project"]["dependencies"]]
        wanted = rest or None
    elif kind == "extra":
        extra, _, name = rest.partition(":")
        specs = [str(s) for s in pyproject["project"]["optional-dependencies"][extra]]
        wanted = name or None
    elif kind == "build-system":
        specs = [str(s) for s in pyproject["build-system"]["requires"]]
        wanted = None
    elif kind == "recipe":
        lines = RECIPE_REQUIREMENTS.read_text(encoding="utf-8").splitlines()
        specs = [ln.split("#", 1)[0].strip() for ln in lines]
        specs = [s for s in specs if s and _normalise(s) != "platterpus"]
        wanted = None
    else:
        raise AssertionError(f"unknown selector {selector!r}")
    if wanted is not None:
        specs = [s for s in specs if _requirement(s)[0] == _normalise(wanted)]
    assert specs, f"selector {selector!r} names nothing in the source files"
    return specs


def test_every_lock_says_what_it_was_resolved_from() -> None:
    """The header records the generator's inputs; they must be this table's."""
    for rel, spec in LOCKS.items():
        text = _read(rel)
        assert text.startswith("# GENERATED by build/lock-requirements.sh"), rel
        assert _header(text, "lock") == spec.label, rel
        assert tuple(_header(text, "inputs").split()) == spec.inputs, (
            f"{rel} was generated from {_header(text, 'inputs')!r}, not "
            f"{' '.join(spec.inputs)!r}. Change build/lock-requirements.sh and this "
            f"table together, then regenerate."
        )


#: The one spelling of `--exclude-newer` the generator accepts and writes.
_EXCLUDE_NEWER: Final[re.Pattern[str]] = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z"
)


def test_every_lock_records_the_uv_and_the_date_that_reproduce_it() -> None:
    """REPRODUCIBILITY: one uv version and one `--exclude-newer` date, in every lock.

    `bash build/lock-requirements.sh --check` regenerates each lock from these two
    header fields and diffs it against the committed file, which is the check that
    sees a hand edit, a deleted package included (the follow-up review of
    2026-10-27). It needs both fields, and one run writes every lock, so the
    fields must agree across the locks too.
    """
    uvs: set[str] = set()
    dates: set[str] = set()
    for rel in LOCKS:
        text = _read(rel)
        uv = _header(text, "uv")
        date = _header(text, "exclude-newer")
        assert re.fullmatch(r"\d+\.\d+\.\d+", uv), f"{rel}: `# uv: {uv}`"
        assert _EXCLUDE_NEWER.fullmatch(date), f"{rel}: `# exclude-newer: {date}`"
        first = text.splitlines()[0]
        assert first == (
            f"# GENERATED by build/lock-requirements.sh with uv {uv}. "
            "Do not edit by hand."
        ), f"{rel}: the first line and the `# uv:` field disagree: {first!r}"
        uvs.add(uv)
        dates.add(date)
    assert len(uvs) == 1 and len(dates) == 1, (
        f"the locks name {sorted(uvs)} and {sorted(dates)}; one run of "
        f"build/lock-requirements.sh writes them all, so they must agree"
    )


def _lock_files_in_generator() -> set[str]:
    """The paths the generator's LOCK_FILES array names: the set `--check` diffs."""
    text = GENERATOR.read_text(encoding="utf-8")
    assigned = dict(re.findall(r'^([A-Z_]+_LOCK)="([^"$]+)"$', text, re.M))
    block = re.search(r"^LOCK_FILES=\((?P<body>.*?)\)$", text, re.M | re.S)
    assert block is not None, "build/lock-requirements.sh has no LOCK_FILES array"
    names = re.findall(r'"\$([A-Z_]+)"', block.group("body"))
    assert names, "LOCK_FILES names nothing"
    return {assigned[name] for name in names}


def test_the_check_covers_every_lock_this_table_holds() -> None:
    """`--check` diffs the files LOCK_FILES names; a lock outside it is never checked."""
    assert _lock_files_in_generator() == set(LOCKS), (
        "build/lock-requirements.sh's LOCK_FILES and this file's LOCKS table name "
        "different locks; a lock missing from LOCK_FILES is never checked"
    )


def _setup_uv_versions(text: str) -> list[str]:
    """The `version:` each `astral-sh/setup-uv` step in a workflow asks for.

    Read from the step's own block (the lines indented past its `- uses:`), so a
    comment between `with:` and `version:` cannot hide the field.
    """
    lines = text.splitlines()
    found: list[str] = []
    for i, line in enumerate(lines):
        if not re.match(r"^\s*- uses: astral-sh/setup-uv@", line):
            continue
        indent = len(line) - len(line.lstrip(" "))
        for after in lines[i + 1 :]:
            if after.strip() and len(after) - len(after.lstrip(" ")) <= indent:
                break
            version = re.match(r'^\s+version: "(?P<v>[^"]+)"\s*$', after)
            if version is not None:
                found.append(version.group("v"))
                break
    return found


def test_ci_checks_the_locks_with_the_uv_they_name() -> None:
    """The `lock-check` job runs `--check` with the uv the locks were made with.

    A byte-for-byte check needs the same uv, so every workflow that runs uv pins
    the version the locks' headers record, and the generator refuses to check
    with any other.
    """
    uv = _header(_read("build/locks/release.lock"), "uv")
    ci = (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")
    body = _job(ci, "lock-check")
    runs = [
        ln.strip()
        for ln in body.splitlines()
        if not ln.strip().startswith("#") and "lock-requirements.sh" in ln
    ]
    assert any(
        re.search(r"\bbash build/lock-requirements\.sh --check$", ln) for ln in runs
    ), f"the lock-check job does not run the generator's --check: {runs}"
    pinned: list[tuple[str, str]] = []
    for path in sorted(WORKFLOWS.glob("*.yml")):
        text = path.read_text(encoding="utf-8")
        found = _setup_uv_versions(text)
        assert len(found) == text.count("uses: astral-sh/setup-uv@"), (
            f"{path.name}: a setup-uv step names no exact `version:`"
        )
        pinned += [(path.name, v) for v in found]
    # Floor: dependencies.yml's and ci.yml's lock-check, at least.
    assert {name for name, _ in pinned} >= {"ci.yml", "dependencies.yml"}, pinned
    differ = [(name, v) for name, v in pinned if v != uv]
    assert not differ, (
        f"the locks were generated with uv {uv}, and these setup-uv steps install "
        f"another: {differ}. Move both together: regenerate the locks with the new "
        f"uv (UV=/path/to/uv bash build/lock-requirements.sh --exclude-newer "
        f"<the date in their headers>) in the commit that moves the pin."
    )


def _via(text: str) -> dict[str, set[str]]:
    """Each pinned package's `# via` annotations: the packages that pulled it in."""
    via: dict[str, set[str]] = {}
    current: str | None = None
    for raw in text.splitlines():
        pin = re.match(r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)==", raw)
        if pin is not None:
            current = _normalise(pin.group("name"))
            via[current] = set()
            continue
        # `# via x` on one line, or `# via` alone followed by `#   x` lines.
        note = re.match(
            r"^\s+#\s+(?:via\s+)?(?P<who>[A-Za-z0-9][A-Za-z0-9._-]*)\s*$", raw
        )
        if note is not None and current is not None and raw.strip() != "# via":
            via[current].add(_normalise(note.group("who")))
    return via


def test_every_package_a_lock_was_pulled_in_by_is_in_the_lock() -> None:
    """An offline second line behind `--check`: the dependency graph is closed.

    A package deleted from a lock leaves its dependents' `# via <it>` lines
    behind, and pip in `--require-hashes` mode then refuses the lock for a
    dependency it does not pin. This sees the deletion of any package another
    one came in through. It cannot see the deletion of a LEAF (one nothing else
    lists, such as certifi in release.lock), which only regenerating can: that
    is ci.yml's `lock-check` job.
    """
    examined = 0
    for rel in LOCKS:
        via = _via(_read(rel))
        dangling = {
            f"{name} via {who}"
            for name, whos in via.items()
            for who in whos
            if who not in via
        }
        assert not dangling, (
            f"{rel} names packages it does not pin: {sorted(dangling)}. A line was "
            f"deleted by hand; regenerate with bash build/lock-requirements.sh"
        )
        examined += sum(len(whos) for whos in via.values())
    # Floor: 265 `via` references across the five locks on 2026-10-27.
    assert examined >= 200, f"only {examined} `# via` references read"


def test_the_closure_check_sees_a_deleted_inner_package() -> None:
    """Non-triviality: delete `requests` from the real release.lock, and it fails."""
    text = _read("build/locks/release.lock")
    via = _via(text)
    assert "requests" in via and "requests" in via["certifi"]
    cut = re.sub(r"^requests==.*?(?=^[A-Za-z])", "", text, count=1, flags=re.M | re.S)
    assert cut != text
    after = _via(cut)
    assert "requests" not in after
    assert any(
        "requests" in whos and "requests" not in after for whos in after.values()
    )


def test_every_requirement_is_an_exact_version_with_a_sha256() -> None:
    """Every line pins `==` one version and carries at least one sha256, with floors."""
    total = 0
    for rel, spec in LOCKS.items():
        pins = _pins(_read(rel))
        assert len(pins) >= spec.min_packages, (
            f"{rel} pins {len(pins)} packages, below its floor of {spec.min_packages}"
        )
        names = [pin.name for pin in pins]
        assert len(names) == len(set(names)), f"{rel} pins a package twice"
        for pin in pins:
            assert pin.hashes, f"{rel}: {pin.name}=={pin.version} has no --hash"
            _version(pin.version)  # a dotted-integer version, or the reader is blind
        total += len(pins)
    assert total >= 100, f"only {total} pinned packages across every lock"


def test_every_lock_pins_its_inputs_inside_the_ranges_they_state() -> None:
    """THE CURRENCY CHECK: move a range without regenerating, and this fails."""
    checked = 0
    for rel, spec in LOCKS.items():
        versions = _lock_versions(rel)
        for selector in spec.inputs:
            for text in _selected(selector):
                name, _ = _requirement(text)
                assert name in versions, (
                    f"{rel} does not pin {name}, which {selector!r} asks "
                    f"for. Regenerate with: bash build/lock-requirements.sh"
                )
                assert _satisfies(versions[name], text), (
                    f"{rel} pins {name}=={versions[name]}, outside "
                    f"{text!r} from {selector!r}. The range moved and the lock did not: "
                    f"regenerate with bash build/lock-requirements.sh"
                )
                checked += 1
    # Floor: 6 AppImage inputs + 5 release + 4 publish + 1 audit + 22 CI on
    # 2026-10-27.
    assert checked >= 30, f"only {checked} input ranges were checked"


def test_the_currency_check_refuses_a_lock_outside_its_range() -> None:
    """Non-triviality: the check above can fail, on the shape it exists for."""
    assert _satisfies("1.6.1", "build>=1.6.1,<1.7")
    assert not _satisfies("1.7.0", "build>=1.6.1,<1.7")
    assert not _satisfies("1.6.0", "build>=1.6.1,<1.7")
    assert _satisfies("6.11.3", "PySide6~=6.11.1")
    assert not _satisfies("6.12.0", "PySide6~=6.11.1")
    assert not _satisfies("6.11.0", "PySide6~=6.11.1")
    assert _satisfies("1.2.0", "tomli-w~=1.0") and not _satisfies("2.0", "tomli-w~=1.0")
    assert _satisfies("0.7.1", "musicbrainzngs==0.7.1")
    assert not _satisfies("0.7.2", "musicbrainzngs==0.7.1")
    assert _satisfies("0.48.0", "wheel")  # no clause: any version
    assert _satisfies("11.12.0", "cyclonedx-python-lib[json-validation]>=11.12,<12")
    assert _requirement("cyclonedx-python-lib[json-validation]>=11.12,<12")[0] == (
        "cyclonedx-python-lib"
    )
    # A shape the reader does not understand fails, rather than comparing wrongly.
    for unreadable in ("1.0rc1", "1.0.post1"):
        try:
            _version(unreadable)
        except AssertionError:
            continue
        raise AssertionError(f"{unreadable!r} was read as a dotted-integer version")


def test_the_lock_parser_refuses_what_is_not_a_hashed_pin() -> None:
    """Non-triviality for the parser every check above rests on."""
    good = "pyside6==6.11.3 \\\n    --hash=sha256:" + "a" * 64 + "\n    # via x\n"
    assert _pins(good) == [Pin("pyside6", "6.11.3", "", ("a" * 64,))]
    marked = "cffi==2.1.1 ; sys_platform == 'linux' \\\n    --hash=sha256:" + "b" * 64
    assert _pins(marked)[0].marker == "sys_platform == 'linux'"
    for bad in (
        "pyside6>=6.11 \\\n    --hash=sha256:" + "a" * 64,  # a range, not a pin
        "pyside6==6.11.3 \\\n    --hash=sha256:abc",  # not a sha256
    ):
        try:
            _pins(bad)
        except AssertionError:
            continue
        raise AssertionError(f"the parser accepted {bad!r}")
    assert not _pins("pyside6==6.11.3\n")[0].hashes  # read, then refused above


def test_locks_that_share_a_package_pin_the_same_version() -> None:
    """Two locks of one release must not disagree about what they verify with.

    The release job checks the new build's attestation with the sigstore from
    release.lock; the AppImage's users check with the one the AppImage lock
    bundles. If those differed, the release could pass a check its users fail.
    """
    appimage = _lock_versions(APPIMAGE_LOCK)
    release = _lock_versions("build/locks/release.lock")
    publish = _lock_versions("build/locks/publish.lock")
    audit = _lock_versions("build/locks/audit.lock")
    ci = _lock_versions("build/locks/ci.lock")
    assert release["sigstore"] == appimage["sigstore"]
    for name in ("build", "setuptools", "wheel"):
        assert release[name] == publish[name] == ci.get(name, publish[name]), name
    assert audit["pip-audit"] == ci["pip-audit"]


def test_ci_tests_the_versions_the_appimage_ships() -> None:
    """Every package both the CI lock and the AppImage lock pin, they pin alike.

    CI's suite is evidence about the AppImage only if it ran the same PySide6,
    numpy, sigstore and the rest of their closure. A universal resolution and a
    3.12-only one could pick differently; this says so the day they do.
    """
    appimage = _lock_versions(APPIMAGE_LOCK)
    ci = _lock_versions("build/locks/ci.lock")
    shared = sorted(set(appimage) & set(ci))
    differ = {n: (appimage[n], ci[n]) for n in shared if appimage[n] != ci[n]}
    assert not differ, (
        f"the CI lock and the AppImage lock pin these differently (AppImage, CI): "
        f"{differ}. Regenerate both with bash build/lock-requirements.sh."
    )
    # Floor: the whole AppImage closure is in the CI lock (36 of 36 on 2026-10-27).
    assert len(shared) >= 30, f"only {len(shared)} packages shared: {shared}"


def _default_python(text: str) -> str:
    match = re.search(r'PLATTERPUS_PYTHON_VERSION:-(?P<v>\d+\.\d+)\}"', text)
    assert match is not None, (
        "build_appimage.sh no longer defaults PLATTERPUS_PYTHON_VERSION"
    )
    return match.group("v")


def test_the_appimage_lock_is_for_the_python_the_appimage_bundles() -> None:
    """numpy, cffi and pydantic-core ship a wheel per CPython minor: the target matters."""
    lock = _read(APPIMAGE_LOCK)
    generator = GENERATOR.read_text(encoding="utf-8")
    bundled = _default_python(BUILD_SCRIPT.read_text(encoding="utf-8"))
    assert _header(lock, "target-python") == bundled
    assert f'APPIMAGE_PYTHON="{bundled}"' in generator
    platform = _header(lock, "target-platform")
    assert re.fullmatch(r"manylinux_2_\d+_x86_64", platform), platform
    assert f'APPIMAGE_PIP_PLATFORM="{platform}"' in generator
    # And the build script reads the target out of the lock rather than assuming it.
    script = BUILD_SCRIPT.read_text(encoding="utf-8")
    assert "s/^# target-python: //p" in script and "s/^# target-platform: //p" in script


def test_the_build_scripts_prerequisite_specs_are_pyprojects() -> None:
    """The hint `build_appimage.sh` prints names the same ranges pyproject chose."""
    script = BUILD_SCRIPT.read_text(encoding="utf-8")
    named = re.findall(r"^require_python_module\s+\S+\s+'([^']+)'", script, re.M)
    by_name = {_requirement(spec)[0]: spec for spec in named}
    expected = {
        "build": _selected("extra:publish:build")[0],
        "python-appimage": _selected("extra:appimage")[0],
    }
    assert by_name == expected


# --- The jobs install from the locks, and only from them -----------------------


def _job(text: str, job: str) -> str:
    """The text of one job in a workflow: from its key to the next job's."""
    match = re.search(
        rf"^  {re.escape(job)}:\n(?P<body>.*?)(?=^  [A-Za-z][\w-]*:\n|\Z)",
        text,
        re.S | re.M,
    )
    assert match is not None, f"no job {job!r}"
    return match.group("body")


def _install_lines(text: str) -> list[str]:
    """Executable `pip install` commands, backslash continuations joined."""
    joined = re.sub(r"\\\s*\n\s*", " ", text)
    return [
        line.strip()
        for line in joined.splitlines()
        if not line.strip().startswith("#") and re.search(r"\bpip\s+install\b", line)
    ]


#: (workflow, job or "" for the whole file) -> the lock that job must install.
HASHED_JOBS: Final[dict[tuple[str, str], str]] = {
    ("release.yml", ""): "build/locks/release.lock",
    ("appimage.yml", ""): "build/locks/release.lock",
    ("publish-pypi.yml", ""): "build/locks/publish.lock",
    ("ci.yml", "pip-audit"): "build/locks/audit.lock",
    ("ci.yml", "lint"): "build/locks/ci.lock",
    ("ci.yml", "typecheck"): "build/locks/ci.lock",
    ("ci.yml", "test"): "build/locks/ci.lock",
    # The follow-up review of 2026-10-27, item 5.
    ("ci.yml", "sbom"): "build/locks/sbom.lock",
    ("ci.yml", "shellcheck"): "build/locks/ci-lint.lock",
    ("mutation.yml", ""): "build/locks/ci.lock",
}


def _is_hashed_install(line: str) -> bool:
    return "--require-hashes" in line and " -r build/" in line


def _is_offline_project_install(line: str) -> bool:
    """The project itself, after the lock: no index, no deps, no isolated build.

    None of the three may go: `--no-index` keeps it from fetching anything,
    `--no-deps` from resolving past the lock, and `--no-build-isolation` from an
    isolated build environment that would fetch setuptools by range.
    """
    flags = ("--no-index", "--no-deps", "--no-build-isolation")
    return all(f in line.split() for f in flags) and line.rstrip().endswith("-e .")


def _is_allowed_install(line: str) -> bool:
    return _is_hashed_install(line) or _is_offline_project_install(line)


def test_jobs_that_publish_attest_or_gate_install_only_from_hashed_locks() -> None:
    """Every `pip install` in these jobs is `--require-hashes -r <lock>`."""
    examined = 0
    for (workflow, job), lock in HASHED_JOBS.items():
        text = (WORKFLOWS / workflow).read_text(encoding="utf-8")
        body = _job(text, job) if job else text
        lines = _install_lines(body)
        assert lines, f"{workflow} {job}: no pip install at all"
        unhashed = [ln for ln in lines if not _is_allowed_install(ln)]
        assert not unhashed, (
            f"{workflow} {job or '(every job)'} installs without a hashed lock: "
            f"{unhashed}. Add the package to pyproject's ranges, regenerate with "
            f"bash build/lock-requirements.sh, and install from the lock."
        )
        assert any(f"-r {lock}" in ln for ln in lines), (
            f"{workflow} never installs {lock}"
        )
        examined += len(lines)
    assert examined >= len(HASHED_JOBS)


def test_workflow_lint_installs_only_actionlint_outside_the_lock() -> None:
    """The one range left in the linter jobs is actionlint-py's, and only it.

    actionlint-py publishes no wheel, so `--only-binary :all:` cannot lock it
    (TASKS R91). The job therefore installs ci-lint.lock hashed and actionlint-py
    by pyproject's range; this holds the exception to exactly that one package,
    so a second unhashed install cannot ride in beside it.
    """
    body = _job((WORKFLOWS / "ci.yml").read_text(encoding="utf-8"), "workflow-lint")
    lines = _install_lines(body)
    assert any(
        _is_hashed_install(ln) and "-r build/locks/ci-lint.lock" in ln for ln in lines
    ), lines
    unhashed = [ln for ln in lines if not _is_allowed_install(ln)]
    assert unhashed == ['python -m pip install "$spec"'], unhashed
    assert 'if s.startswith("actionlint-py")' in body, (
        "workflow-lint's one unhashed install no longer selects actionlint-py"
    )
    assert "actionlint-py" not in _lock_versions("build/locks/ci-lint.lock")


def test_the_sbom_describes_the_versions_ci_tests() -> None:
    """The sbom job's lock pins every package it shares with the CI lock alike.

    The SBOM is published as the inventory of what CI checked; a separate
    resolution that picked a different version of a runtime package would make
    it describe an environment no test ran in.
    """
    sbom = _lock_versions("build/locks/sbom.lock")
    ci = _lock_versions("build/locks/ci.lock")
    shared = sorted(set(sbom) & set(ci))
    differ = {n: (sbom[n], ci[n]) for n in shared if sbom[n] != ci[n]}
    assert not differ, f"the sbom lock and the CI lock differ (sbom, CI): {differ}"
    # Floor: 66 shared on 2026-10-27, the whole runtime closure among them.
    assert len(shared) >= 50, shared
    assert "cyclonedx-bom" in sbom


#: Locks the lock-install job need not repeat: ci.lock is installed on every
#: pull request by the test, lint and typecheck jobs already.
_INSTALLED_ELSEWHERE_ON_EVERY_PULL_REQUEST: Final[frozenset[str]] = frozenset(
    {"build/locks/ci.lock"}
)


def test_every_lock_is_installed_and_built_from_on_pull_requests() -> None:
    """Item 4 of the follow-up review of 2026-10-27: no lock waits for a release.

    publish.lock was first installed at publish time and release.lock first on
    main, so a lock that could not install surfaced at a release. ci.yml's
    `lock-install` job (which runs on pull requests, as every ci.yml job does)
    installs each into a clean venv with `--require-hashes`, runs `pip check`, and
    runs the builds the release and the publish run, without publishing.
    """
    ci = (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")
    assert re.search(r"^  pull_request:", ci, re.M), "ci.yml no longer runs on PRs"
    body = _job(ci, "lock-install")
    lines = _install_lines(body)
    unhashed = [ln for ln in lines if not _is_hashed_install(ln)]
    assert not unhashed, f"lock-install installs without a hashed lock: {unhashed}"
    expected = set(LOCKS) - _INSTALLED_ELSEWHERE_ON_EVERY_PULL_REQUEST
    installed = {
        lock for lock in expected for ln in lines if ln.endswith(f" -r {lock}")
    }
    assert installed == expected, (
        f"lock-install does not install {sorted(expected - installed)}"
    )
    # Each into a venv of its own: every install line runs a venv's python.
    assert all(re.match(r'^"\$v/[\w-]+/bin/python" -m pip', ln) for ln in lines), lines
    executable = "\n".join(
        ln for ln in body.splitlines() if not ln.strip().startswith("#")
    )
    assert re.search(r'"\$v/\$name/bin/python" -m pip check', executable)
    # The publish job's build and check, and the AppImage build's wheel build.
    assert re.search(r'"\$py" -m build --no-isolation --outdir', executable)
    assert re.search(r'"\$py" -m twine check', executable)
    assert re.search(r'"\$py" -m build --wheel --no-isolation', executable)
    # Nothing that could publish: no token, no secrets, no OIDC, no writes.
    for forbidden in (
        "secrets.",
        "github.token",
        "id-token",
        "permissions:",
        "gh-action-pypi-publish",
        "twine upload",
        "gh release",
    ):
        assert forbidden not in executable, f"lock-install has {forbidden!r}"


def test_a_weekly_job_regenerates_the_locks_and_proposes_them() -> None:
    """Item 1 of the follow-up review of 2026-10-27: the locks must not rot.

    Dependabot reads pyproject.toml, not the locks, so without this job nothing
    ever takes a newer release into one. dependencies.yml's `relock` job
    regenerates them every week with a date seven days back, opens a pull request
    when a pin or hash changed, and fails visibly when it cannot.
    """
    text = (WORKFLOWS / "dependencies.yml").read_text(encoding="utf-8")
    assert re.search(r"^  schedule:\n    - cron: ", text, re.M), "no weekly schedule"
    assert re.search(r"^  workflow_dispatch:", text, re.M)
    body = _job(text, "relock")
    executable = "\n".join(
        ln for ln in body.splitlines() if not ln.strip().startswith("#")
    )
    # Least privilege, on the job: exactly the two writes it needs.
    grants = re.search(
        r"^    permissions:\n(?P<g>(?:      [\w-]+: \w+[^\n]*\n)+)", body, re.M
    )
    assert grants is not None, "the relock job grants nothing of its own"
    granted = dict(re.findall(r"^      ([\w-]+): (\w+)", grants.group("g"), re.M))
    assert granted == {"contents": "write", "pull-requests": "write"}, granted
    # Seven days back, Dependabot's cooldown, through the generator itself.
    assert "date -u -d '7 days ago' +%Y-%m-%dT00:00:00Z" in executable
    assert 'bash build/lock-requirements.sh --exclude-newer "$date"' in executable
    # A new date alone is no reason for a pull request.
    assert "git diff --quiet -I '^# exclude-newer: '" in executable
    # It writes, so it restores no cache, setup-uv's default included.
    assert "enable-cache: false" in body
    assert not re.search(r"^\s+cache:\s*\S", body, re.M)
    # A pull request it could not open is a red job naming the branch.
    assert re.search(r"if ! url=\"\$\(gh pr create ", executable)
    failure = executable.split('if ! url="$(gh pr create ', 1)[1].split("fi\n", 1)[0]
    assert "::error::" in failure and "exit 1" in failure, failure
    # And the pull request says CI has not run on it, and who carries it.
    assert "No CI has run on this branch" in executable
    assert "KDD-43" in executable


def test_the_install_check_catches_the_lines_that_shipped() -> None:
    """Non-triviality, against the exact lines the review named."""
    for shipped in (
        'pip install "build>=1,<2" "python-appimage>=1.4,<2"',
        "python -m pip install --upgrade pip",
        'python -m pip install "${pins[@]}"',
        'python -m pip install -e . "$spec"',
        'python -m pip install "$spec"',
        'pip install -e ".[dev]"',
        # The project install with one of its three guards missing.
        "python -m pip install --no-deps --no-build-isolation -e .",
        "python -m pip install --no-index --no-build-isolation -e .",
        "python -m pip install --no-index --no-deps -e .",
    ):
        assert _install_lines(shipped) == [shipped]
        assert not _is_allowed_install(shipped), shipped
    fixed = "python -m pip install --require-hashes --only-binary=:all: -r build/locks/release.lock"
    assert _is_allowed_install(fixed)
    project = "python -m pip install --no-index --no-deps --no-build-isolation -e ."
    assert _is_allowed_install(project) and not _is_hashed_install(project)
    # A comment about installing is not an install.
    assert _install_lines("# python -m pip install foo") == []


def test_the_audit_reads_every_lock_with_a_floor_of_all_of_them() -> None:
    """pip-audit audits the locks themselves, and refuses fewer than this table holds."""
    body = _job((WORKFLOWS / "ci.yml").read_text(encoding="utf-8"), "pip-audit")
    assert "--disable-pip --require-hashes" in body
    assert APPIMAGE_LOCK in body and "build/locks/*.lock" in body
    floor = re.search(r'"\$\{#locks\[@\]\}" -lt (?P<n>\d+)', body)
    assert floor is not None, "the audit step lost its floor"
    assert int(floor.group("n")) == len(LOCKS), (
        f"the audit's floor is {floor.group('n')} locks; there are {len(LOCKS)}"
    )
    # Every lock outside build/locks/ must be named, since the glob cannot see it.
    for rel in LOCKS:
        assert rel.startswith("build/locks/") or rel in body, rel
