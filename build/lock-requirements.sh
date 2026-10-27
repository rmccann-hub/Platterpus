#!/usr/bin/env bash
# Generate every hash-pinned lock Platterpus installs from, in one run.
#
# WHY LOCKS AT ALL
# ----------------
# A version range names a SET of releases. Whatever PyPI serves inside that set
# on the day a job runs is what gets installed, so a compromised patch release
# would install in a job that publishes to PyPI or signs a build attestation,
# and a CI run could test different bytes from the ones that ship. A lock names
# one version of every package in the closure and the sha256 of every file pip
# may fetch for it; `pip install --require-hashes -r <lock>` refuses anything
# else (the 2026-10-27 review, items 2.1 and 2.3; PLANNING.md KDD-45, A4).
#
# THE RANGES STAY IN ONE PLACE
# ----------------------------
# Every lock is resolved FROM the ranges pyproject.toml (or, for the AppImage,
# build/python-appimage/requirements.txt) already states. This script chooses no
# version itself. tests/test_dependency_locks.py fails when a lock's pins fall
# outside those ranges, so moving a range without re-running this is caught.
#
# THE LOCKS
# ---------
#   build/python-appimage/requirements.lock
#       What the AppImage bundles: requirements.txt minus the local `platterpus`
#       wheel, resolved for the CPython python-appimage bundles (APPIMAGE_PYTHON)
#       on the glibc floor PySide6 sets (APPIMAGE_PLATFORM). build_appimage.sh
#       downloads it into a hash-verified wheelhouse and installs offline from it.
#   build/locks/release.lock   release.yml and appimage.yml: `build`,
#       `python-appimage`, the build backend, and `sigstore` for the release's
#       attestation check (the test holds its sigstore equal to the AppImage's).
#   build/locks/publish.lock   publish-pypi.yml: `build`, `twine`, the backend.
#   build/locks/audit.lock     ci.yml's pip-audit job: pip-audit alone.
#   build/locks/ci.lock        ci.yml's test, lint and typecheck jobs: the
#       runtime dependencies, the dev extra and the backend, one universal
#       resolution for every Python the matrix runs.
#
# The build backend (pyproject's [build-system].requires) is in every lock that
# builds or installs the project, because those jobs build with
# `--no-isolation`: an isolated build would fetch setuptools and wheel from PyPI
# by range, unhashed, which is the hole the locks exist to close.
#
# THE GENERATOR IS uv
# -------------------
# `uv pip compile` resolves for a Python and platform other than the one it runs
# on (`--python-version`, `--python-platform`), which pip cannot do for a full
# closure, and `--generate-hashes` records the sha256 of EVERY file PyPI
# publishes for each pinned version, so the lock also verifies a wheel chosen on
# a different glibc or Python than the generator's. uv is already a CI tool here
# (dependencies.yml) and is listed in DEPENDENCIES.md. Nothing in CI runs uv to
# INSTALL: every job installs with pip, from these files.
#
# `--only-binary :all:` throughout: every pinned package must ship a wheel, so no
# package's own build code runs when a lock is installed.
#
# Usage (from anywhere; resolves its own paths):
#     bash build/lock-requirements.sh
# then review the diff and commit every changed lock. Re-run whenever a range in
# pyproject.toml or requirements.txt changes, or to take newer releases inside
# the same ranges (a deliberate commit, like any pin bump).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYPROJECT="$REPO_ROOT/pyproject.toml"
REQUIREMENTS="$SCRIPT_DIR/python-appimage/requirements.txt"
APPIMAGE_LOCK="$SCRIPT_DIR/python-appimage/requirements.lock"
LOCK_DIR="$SCRIPT_DIR/locks"

# The CPython python-appimage bundles. MUST equal PLATTERPUS_PYTHON_VERSION's
# default in build_appimage.sh: numpy, cffi and pydantic-core ship one wheel per
# CPython minor, so a lock for another minor names wheels the bundled pip cannot
# install. build_appimage.sh refuses a lock whose target differs from the build's,
# and tests/test_dependency_locks.py holds the two defaults equal.
APPIMAGE_PYTHON="3.12"
# uv's spelling of the AppImage's platform. manylinux_2_34 is the glibc PySide6
# 6.11's x86_64 wheels require, and the lowest that resolves (measured
# 2026-10-27 with uv 0.11.32: manylinux_2_28 has no PySide6 6.11 wheel, and 2_35
# and 2_39 resolve the same versions as 2_34). Resolving at the floor means the
# lock can never pull in a wheel that raises the AppImage's glibc requirement.
APPIMAGE_PLATFORM="x86_64-manylinux_2_34"
# The same platform in pip's spelling, written into the lock's header for
# build_appimage.sh's `pip download --platform`.
APPIMAGE_PIP_PLATFORM="manylinux_2_34_x86_64"
# The oldest Python the tool and CI locks must install on: pyproject's
# requires-python floor. The resolution is universal above it.
TOOLS_PYTHON="3.11"

UV="${UV:-uv}"
if ! command -v "$UV" >/dev/null 2>&1; then
    echo "error: uv is required (https://docs.astral.sh/uv/); set UV=/path/to/uv if it is not on PATH" >&2
    exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
    echo "error: python3 (3.11 or newer, for tomllib) is required but not on PATH" >&2
    exit 1
fi
UV_VERSION="$("$UV" --version | awk '{print $2}')"
echo "Generating locks with uv $UV_VERSION"

WORK="$(mktemp -d)"
trap 'rm -r -f -- "$WORK"' EXIT

# Print the requirement strings a list of SELECTORS names, one per line.
#   dependencies          [project].dependencies
#   dependencies:NAME     one entry of it
#   extra:X               [project.optional-dependencies].X
#   extra:X:NAME          one entry of it
#   build-system          [build-system].requires
#   recipe                requirements.txt, minus comments and the local
#                         `platterpus` wheel (built here, every commit, and
#                         pinned by SOURCE_DATE_EPOCH, so it is never locked)
# A selector that names nothing is an error: a lock built from fewer inputs than
# its header claims would still look complete.
select_requirements() {
    python3 - "$PYPROJECT" "$REQUIREMENTS" "$@" <<'PY'
import re
import sys
import tomllib

pyproject_path, recipe_path, *selectors = sys.argv[1:]
with open(pyproject_path, "rb") as fh:
    pyproject = tomllib.load(fh)


def name_of(spec: str) -> str:
    match = re.match(r"\s*([A-Za-z0-9._-]+)", spec)
    if match is None:
        sys.exit(f"error: cannot read a package name from {spec!r}")
    return re.sub(r"[-_.]+", "-", match.group(1)).lower()


def pick(specs: list[str], wanted: str | None, where: str) -> list[str]:
    if wanted is None:
        return specs
    chosen = [s for s in specs if name_of(s) == name_of(wanted)]
    if len(chosen) != 1:
        sys.exit(f"error: {where} names {wanted!r} {len(chosen)} times, not once")
    return chosen


out: list[str] = []
for selector in selectors:
    before = len(out)
    kind, _, rest = selector.partition(":")
    if kind == "dependencies":
        specs = [str(s) for s in pyproject["project"]["dependencies"]]
        out += pick(specs, rest or None, "[project].dependencies")
    elif kind == "extra":
        extra, _, wanted = rest.partition(":")
        extras = pyproject["project"].get("optional-dependencies", {})
        if extra not in extras:
            sys.exit(f"error: pyproject.toml has no {extra!r} extra")
        specs = [str(s) for s in extras[extra]]
        out += pick(specs, wanted or None, f"the {extra} extra")
    elif kind == "build-system":
        out += [str(s) for s in pyproject["build-system"]["requires"]]
    elif kind == "recipe":
        with open(recipe_path, encoding="utf-8") as fh:
            for raw in fh:
                line = raw.split("#", 1)[0].strip()
                if line and name_of(line) != "platterpus":
                    out.append(line)
    else:
        sys.exit(f"error: unknown selector {selector!r}")
    if len(out) == before:
        sys.exit(f"error: selector {selector!r} selected nothing")
print("\n".join(out))
PY
}

# lock_universal OUT LABEL SELECTOR... — a lock for every Python from
# TOOLS_PYTHON up, on every platform (markers keep each line to where it applies).
lock_universal() {
    local out="$1" label="$2"
    shift 2
    write_lock "$out" "$label" "universal, Python >= $TOOLS_PYTHON" "" "" "$@" -- \
        --universal --python-version "$TOOLS_PYTHON"
}

# write_lock OUT LABEL TARGET TARGET_PYTHON TARGET_PLATFORM SELECTOR... -- UV_ARGS...
write_lock() {
    local out="$1" label="$2" target="$3" target_python="$4" target_platform="$5"
    shift 5
    local selectors=()
    while [ "$#" -gt 0 ] && [ "$1" != "--" ]; do
        selectors+=("$1")
        shift
    done
    shift # the `--`
    local input="$WORK/$label.in" body="$WORK/$label.body"
    select_requirements "${selectors[@]}" >"$input"
    echo "== $label: $(wc -l <"$input") input requirement(s) -> ${out#"$REPO_ROOT"/}"
    sed 's/^/     /' "$input"
    # Inputs come from stdin so the top-level lines carry no temp-file path in
    # their `# via` annotation, which would change on every run.
    "$UV" pip compile - "$@" \
        --only-binary :all: \
        --generate-hashes \
        --no-header \
        --quiet \
        --output-file "$body" <"$input"
    {
        echo "# GENERATED by build/lock-requirements.sh with uv $UV_VERSION. Do not edit by hand."
        echo "# Regenerate with: bash build/lock-requirements.sh"
        if [ -n "$target_python" ]; then
            echo "# Consumed by build/build_appimage.sh, which downloads it with pip --require-hashes"
            echo "# for the target below and installs the AppImage's dependencies offline from that."
        else
            echo "# Install with: python -m pip install --require-hashes --only-binary=:all: -r <this file>"
        fi
        echo "# lock: $label"
        echo "# inputs: ${selectors[*]}"
        echo "# target: $target"
        if [ -n "$target_python" ]; then
            echo "# target-python: $target_python"
            echo "# target-platform: $target_platform"
        fi
        echo "#"
        cat "$body"
    } >"$out"
    echo "   wrote $(grep -c '^[A-Za-z0-9]' "$out") pinned packages, $(grep -c -- '--hash=sha256:' "$out") hashes"
}

mkdir -p "$LOCK_DIR"

# The AppImage: requirements.txt is the AppImage's own statement of its ranges
# (tests/test_gating_tools_are_pinned.py holds it equal to pyproject's).
write_lock "$APPIMAGE_LOCK" appimage \
    "CPython $APPIMAGE_PYTHON on $APPIMAGE_PIP_PLATFORM (the interpreter python-appimage bundles)" \
    "$APPIMAGE_PYTHON" "$APPIMAGE_PIP_PLATFORM" \
    recipe -- \
    --python-version "$APPIMAGE_PYTHON" --python-platform "$APPIMAGE_PLATFORM"

lock_universal "$LOCK_DIR/release.lock" release \
    extra:publish:build extra:appimage build-system dependencies:sigstore
lock_universal "$LOCK_DIR/publish.lock" publish \
    extra:publish build-system
lock_universal "$LOCK_DIR/audit.lock" audit \
    extra:dev:pip-audit
# CI's test, lint and typecheck jobs, on every Python of the matrix (3.11 to
# 3.14) from one resolution: the runtime dependencies, the dev extra, and the
# backend the editable install builds with (`--no-build-isolation`).
lock_universal "$LOCK_DIR/ci.lock" ci \
    dependencies extra:dev build-system

echo "Done. Review the diff and commit every changed lock."
