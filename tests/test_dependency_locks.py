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
