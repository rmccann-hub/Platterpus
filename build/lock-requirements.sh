#!/usr/bin/env bash
# Generate every hash-pinned lock Platterpus installs from, in one run, or check
# that the committed locks are exactly what that run produces.
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
#   build/locks/ci.lock        ci.yml's test, lint and typecheck jobs, and
#       mutation.yml's sweep: the runtime dependencies, the dev extra and the
#       backend, one universal resolution for every Python the matrix runs.
#   build/locks/sbom.lock      ci.yml's sbom job: the runtime dependencies (the
#       environment the SBOM describes), the `sbom` extra and the backend.
#   build/locks/ci-lint.lock   ci.yml's workflow-lint and shellcheck jobs: zizmor
#       and ShellCheck from the `ci-lint` extra (not actionlint-py; see below).
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
# a different glibc or Python than the generator's. uv is listed in
# DEPENDENCIES.md, and CI runs it at the version dependencies.yml pins. Nothing
# in CI runs uv to INSTALL: every job installs with pip, from these files.
#
# `--only-binary :all:` throughout: every pinned package must ship a wheel, so no
# package's own build code runs when a lock is installed.
#
# REPRODUCIBLE, AND THEREFORE CHECKABLE
# -------------------------------------
# Every run resolves with `uv pip compile --exclude-newer DATE`: uv considers only
# files PyPI received before DATE, so the same uv, the same ranges and the same
# DATE give the same lock, byte for byte, next week or next year. DATE and the uv
# version are written into every lock's header (`# exclude-newer:`, `# uv:`), and
# `--check` regenerates every lock from those two fields into a temporary
# directory and diffs it against the committed file. That is what catches a hand
# edit, a package deleted from a lock, a range moved without regenerating, or a
# release yanked after the lock was made: tests/test_dependency_locks.py reads
# the files and cannot see the first or the last (the follow-up review of
# 2026-10-27). ci.yml's `lock-check` job runs it on every pull request.
#
# DATE defaults to 00:00 UTC seven days ago, Dependabot's cooldown: a release
# that was compromised is usually found and yanked within days, so a lock takes
# nothing younger than a week unless someone asks for it by date. A DATE later
# than now is refused, because a lock resolved against the future is not
# reproducible: releases can still arrive before it.
#
# Usage (from anywhere; resolves its own paths):
#     bash build/lock-requirements.sh [--exclude-newer YYYY-MM-DDTHH:MM:SSZ]
#         Regenerate every lock, then review the diff and commit every changed
#         lock. Re-run whenever a range in pyproject.toml or requirements.txt
#         changes, or to take newer releases inside the same ranges (a
#         deliberate commit, like any pin bump). dependencies.yml's `relock` job
#         does the second every week and proposes the result as a pull request.
#     bash build/lock-requirements.sh --check
#         Regenerate with the uv version and DATE the headers record, and fail
#         on any difference. Needs that uv (set UV=/path/to/uv if it is not the
#         one on PATH) and network access to PyPI.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYPROJECT="$REPO_ROOT/pyproject.toml"
REQUIREMENTS="$SCRIPT_DIR/python-appimage/requirements.txt"

# Every lock this script writes, relative to the repository root, in the order
# it writes them. --check reads the date and uv version back out of each, and
# diffs each against a fresh copy.
APPIMAGE_LOCK="build/python-appimage/requirements.lock"
RELEASE_LOCK="build/locks/release.lock"
PUBLISH_LOCK="build/locks/publish.lock"
AUDIT_LOCK="build/locks/audit.lock"
CI_LOCK="build/locks/ci.lock"
SBOM_LOCK="build/locks/sbom.lock"
CI_LINT_LOCK="build/locks/ci-lint.lock"
LOCK_FILES=(
    "$APPIMAGE_LOCK" "$RELEASE_LOCK" "$PUBLISH_LOCK" "$AUDIT_LOCK" "$CI_LOCK"
    "$SBOM_LOCK" "$CI_LINT_LOCK"
)

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

usage() {
    echo "usage: bash build/lock-requirements.sh [--exclude-newer YYYY-MM-DDTHH:MM:SSZ | --check]"
}

MODE="generate"
EXCLUDE_NEWER=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --check)
            MODE="check"
            shift
            ;;
        --exclude-newer)
            if [ "$#" -lt 2 ]; then
                echo "error: --exclude-newer needs a date" >&2
                usage >&2
                exit 2
            fi
            EXCLUDE_NEWER="$2"
            shift 2
            ;;
        --exclude-newer=*)
            EXCLUDE_NEWER="${1#*=}"
            shift
            ;;
        -h | --help)
            usage
            exit 0
            ;;
        *)
            echo "error: unknown argument: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done
if [ "$MODE" = "check" ] && [ -n "$EXCLUDE_NEWER" ]; then
    echo "error: --check reads the date from each lock's header; do not pass --exclude-newer" >&2
    exit 2
fi

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

# One header field of one committed lock, or nothing.
header_field() {
    sed -n "s/^# $2: //p" "$REPO_ROOT/$1" | head -n 1
}

if [ "$MODE" = "check" ]; then
    # Every lock must name one date and one uv, and they must agree: the
    # generator writes them all in one run, so a disagreement is itself an edit.
    HEADER_UV=""
    for rel in "${LOCK_FILES[@]}"; do
        if [ ! -f "$REPO_ROOT/$rel" ]; then
            echo "error: $rel is missing; regenerate with: bash build/lock-requirements.sh" >&2
            exit 1
        fi
        date_here="$(header_field "$rel" exclude-newer)"
        uv_here="$(header_field "$rel" uv)"
        if [ -z "$date_here" ] || [ -z "$uv_here" ]; then
            echo "error: $rel has no '# exclude-newer:' or '# uv:' header line, so it cannot" >&2
            echo "be reproduced. Regenerate every lock with: bash build/lock-requirements.sh" >&2
            exit 1
        fi
        if [ -z "$EXCLUDE_NEWER" ]; then
            EXCLUDE_NEWER="$date_here"
            HEADER_UV="$uv_here"
        elif [ "$date_here" != "$EXCLUDE_NEWER" ] || [ "$uv_here" != "$HEADER_UV" ]; then
            echo "error: the locks disagree: ${LOCK_FILES[0]} says uv $HEADER_UV and $EXCLUDE_NEWER," >&2
            echo "$rel says uv $uv_here and $date_here. One run writes them all; regenerate." >&2
            exit 1
        fi
    done
    if [ "$HEADER_UV" != "$UV_VERSION" ]; then
        echo "error: the locks were generated with uv $HEADER_UV, and $UV is uv $UV_VERSION." >&2
        echo "A byte-for-byte check needs the same uv: install uv $HEADER_UV and set UV=/path/to/it." >&2
        exit 2
    fi
elif [ -z "$EXCLUDE_NEWER" ]; then
    EXCLUDE_NEWER="$(python3 -c 'import datetime as d; print((d.datetime.now(d.timezone.utc) - d.timedelta(days=7)).strftime("%Y-%m-%dT00:00:00Z"))')"
fi

# The date must be one exact UTC instant in one spelling (uv reads other shapes
# too, but only one keeps the header byte-stable), and must not be in the future.
if ! python3 - "$EXCLUDE_NEWER" <<'PY'
import datetime as dt
import re
import sys

value = sys.argv[1]
if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value):
    sys.exit(f"error: --exclude-newer {value!r} is not YYYY-MM-DDTHH:MM:SSZ (UTC)")
try:
    when = dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
except ValueError as exc:
    sys.exit(f"error: --exclude-newer {value!r} is not a real date: {exc}")
if when.replace(tzinfo=dt.timezone.utc) > dt.datetime.now(dt.timezone.utc):
    sys.exit(
        f"error: --exclude-newer {value} is in the future, so the lock would not be "
        "reproducible: releases can still arrive before it"
    )
PY
then
    exit 2
fi

WORK="$(mktemp -d)"
trap 'rm -r -f -- "$WORK"' EXIT

# Where the locks are written: the repository itself, or for --check a scratch
# tree with the same layout, diffed against the repository afterwards.
if [ "$MODE" = "check" ]; then
    OUT_ROOT="$WORK/out"
    echo "Checking the committed locks: regenerating with uv $UV_VERSION, exclude-newer $EXCLUDE_NEWER"
else
    OUT_ROOT="$REPO_ROOT"
    echo "Generating locks with uv $UV_VERSION, exclude-newer $EXCLUDE_NEWER"
fi

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
# OUT is relative to the repository root, and is written under OUT_ROOT.
write_lock() {
    local out="$1" label="$2" target="$3" target_python="$4" target_platform="$5"
    shift 5
    local selectors=()
    while [ "$#" -gt 0 ] && [ "$1" != "--" ]; do
        selectors+=("$1")
        shift
    done
    shift # the `--`
    local input="$WORK/$label.in" body="$WORK/$label.body" dest="$OUT_ROOT/$out"
    mkdir -p "$(dirname "$dest")"
    select_requirements "${selectors[@]}" >"$input"
    echo "== $label: $(wc -l <"$input") input requirement(s) -> $out"
    sed 's/^/     /' "$input"
    # Inputs come from stdin so the top-level lines carry no temp-file path in
    # their `# via` annotation, which would change on every run.
    "$UV" pip compile - "$@" \
        --only-binary :all: \
        --generate-hashes \
        --exclude-newer "$EXCLUDE_NEWER" \
        --no-header \
        --quiet \
        --output-file "$body" <"$input"
    {
        echo "# GENERATED by build/lock-requirements.sh with uv $UV_VERSION. Do not edit by hand."
        echo "# Regenerate with: bash build/lock-requirements.sh [--exclude-newer <date>]"
        echo "# Check with: bash build/lock-requirements.sh --check (it reuses the uv and date below)"
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
        echo "# uv: $UV_VERSION"
        echo "# exclude-newer: $EXCLUDE_NEWER"
        echo "#"
        cat "$body"
    } >"$dest"
    echo "   wrote $(grep -c '^[A-Za-z0-9]' "$dest") pinned packages, $(grep -c -- '--hash=sha256:' "$dest") hashes"
}

# The AppImage: requirements.txt is the AppImage's own statement of its ranges
# (tests/test_gating_tools_are_pinned.py holds it equal to pyproject's).
write_lock "$APPIMAGE_LOCK" appimage \
    "CPython $APPIMAGE_PYTHON on $APPIMAGE_PIP_PLATFORM (the interpreter python-appimage bundles)" \
    "$APPIMAGE_PYTHON" "$APPIMAGE_PIP_PLATFORM" \
    recipe -- \
    --python-version "$APPIMAGE_PYTHON" --python-platform "$APPIMAGE_PLATFORM"

lock_universal "$RELEASE_LOCK" release \
    extra:publish:build extra:appimage build-system dependencies:sigstore
lock_universal "$PUBLISH_LOCK" publish \
    extra:publish build-system
lock_universal "$AUDIT_LOCK" audit \
    extra:dev:pip-audit
# CI's test, lint and typecheck jobs, on every Python of the matrix (3.11 to
# 3.14) from one resolution: the runtime dependencies, the dev extra, and the
# backend the editable install builds with (`--no-build-isolation`).
lock_universal "$CI_LOCK" ci \
    dependencies extra:dev build-system
# CI's required sbom job: `cyclonedx-py environment` inventories the
# environment it runs in, so that environment is the runtime dependencies (the
# project is then installed into it offline) plus the generator.
lock_universal "$SBOM_LOCK" sbom \
    dependencies extra:sbom build-system
# CI's workflow-lint and shellcheck jobs: zizmor and ShellCheck, two wheels that
# each carry a binary. NOT actionlint-py, the extra's third tool: it publishes
# only an sdist (1.7.12.25, read 2026-10-27), whose build downloads the actionlint
# binary from GitHub, so `--only-binary :all:` cannot lock it. workflow-lint
# installs it by pyproject's range, and TASKS R91 records the gap.
lock_universal "$CI_LINT_LOCK" ci-lint \
    extra:ci-lint:zizmor extra:ci-lint:shellcheck-py

if [ "$MODE" = "check" ]; then
    failed=0
    for rel in "${LOCK_FILES[@]}"; do
        if [ ! -f "$OUT_ROOT/$rel" ]; then
            echo "error: the generator wrote no $rel, so LOCK_FILES and the calls above disagree" >&2
            failed=1
            continue
        fi
        if diff -u --label "$rel (committed)" --label "$rel (regenerated)" \
            "$REPO_ROOT/$rel" "$OUT_ROOT/$rel"; then
            echo "ok: $rel is what the generator produces"
        else
            failed=1
            echo "error: $rel differs from what uv $UV_VERSION produces with exclude-newer" >&2
            echo "$EXCLUDE_NEWER (the diff is above: - committed, + regenerated)." >&2
        fi
    done
    if [ "$failed" -ne 0 ]; then
        echo "The committed locks are not what their headers say produced them. The causes:" >&2
        echo "a hand edit (a deleted or changed line), a range in pyproject.toml or" >&2
        echo "requirements.txt moved without regenerating, or PyPI changed a release since" >&2
        echo "(a yank or a removed file). Regenerate with bash build/lock-requirements.sh," >&2
        echo "review the diff, and commit." >&2
        exit 1
    fi
    echo "Every lock (${#LOCK_FILES[@]}) reproduces byte for byte."
    exit 0
fi

echo "Done. Review the diff and commit every changed lock."
