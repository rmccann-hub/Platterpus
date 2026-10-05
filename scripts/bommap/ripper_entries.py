"""The cyanrip fork, upstream cyanrip, the ripping container, and the fork's build inputs."""

from __future__ import annotations

import re
from typing import Final

from bommap.model import _P, _REPO_ROOT, ROOT_REF, Entry, GeneratorError
from bommap.plan import (
    _container_name,
    _dnf_installs,
    _exports,
    _fork_refs,
    _manifest_url,
    setup_plan,
)
from bommap.reading import (
    _home_relative,
    _join,
    _project_repository,
    _require,
    _text,
    _vers,
)


def _ripper_entries() -> list[Entry]:
    from platterpus import handshake_approval
    from platterpus.deps import fork_source as fs
    from platterpus.deps.registry import SPECS
    from platterpus.paths import CYANRIP_BINARY_DEFAULT

    cyanrip = next(spec for spec in SPECS if spec.dep_id == "cyanrip")
    minimum = ".".join(str(n) for n in cyanrip.min_version)
    repo = fs.FORK_REPO_URL.removesuffix(".git")
    slug = repo.removeprefix("https://github.com/")
    owner, project = slug.split("/", 1)
    upstream_match = re.search(
        r'^UPSTREAM_URL="(?P<url>[^"]+)"',
        _text("scripts/cyanrip/setup-fork.sh"),
        re.MULTILINE,
    )
    if upstream_match is None:
        raise GeneratorError(
            "scripts/cyanrip/setup-fork.sh no longer names UPSTREAM_URL"
        )
    upstream = upstream_match.group("url")
    up_owner, up_project = upstream.removeprefix("https://github.com/").split("/", 1)
    host_export = _home_relative(CYANRIP_BINARY_DEFAULT)
    exports = _exports().get("cyanrip", ())
    production = fs.PRODUCTION_TARGET
    review = fs.UNDER_REVIEW_TARGET
    test = fs.TEST_TARGET
    blob = f"{_project_repository()}/blob/main"
    shared: list[tuple[str, str, str]] = []
    for doc, note in _SHARED_TEXTS:
        if not (_REPO_ROOT / doc).is_file():
            raise GeneratorError(f"shared seam text {doc} is missing")
        # OWNERSHIP.md is the record of which texts are shared; a shared text it
        # no longer names is not shared any more.
        if doc != "docs/OWNERSHIP.md" and doc not in _text("docs/OWNERSHIP.md"):
            raise GeneratorError(f"docs/OWNERSHIP.md no longer names {doc}")
        shared.append(("documentation", f"{blob}/{doc}", note))
    used = (
        _require(
            "src/platterpus/adapters/cyanrip_backend.py",
            "cyanrip",
            why="cyanrip adapter",
        ),
        "src/platterpus/deps/fork_source.py",
        "src/platterpus/deps/host_setup.py",
        "src/platterpus/deps/registry.py",
    )
    fork_props: list[tuple[str, str]] = [
        (_P + "pin", production.pin),
        (_P + "build-tag", fs.FORK_EXPECTED_BUILD_TAG),
        (_P + "banner", fs.FORK_EXPECTED_BANNER),
        (_P + "branch", fs.FORK_BRANCH),
        (_P + "release-seq", str(fs.FORK_PIN_RELEASE_SEQ)),
        (_P + "approved-by-round", str(handshake_approval.APPROVED_BY_ROUND)),
        (
            _P + "approved-for-platterpus",
            handshake_approval.APPROVED_FOR_PLATTERPUS_VERSION,
        ),
        (_P + "checked-minimum", minimum),
        (
            _P + "installed-at",
            f"{fs.FORK_INSTALL_PATH} inside the {_container_name()} container",
        ),
        (_P + "host-export", host_export),
        (_P + "exported-from", f"{_join(exports)} (the last export wins)"),
        (
            _P + "pin-under-review",
            f"{review.pin} ({review.version}, round {fs.PIN_UNDER_REVIEW_ROUND}, published: {'yes' if fs.PIN_UNDER_REVIEW_IS_PUBLISHED else 'no'})",
        ),
        (
            _P + "test-pin",
            f"{test.pin} ({test.version}, nominated by round {fs.FORK_TEST_PIN_ROUND})",
        ),
        (
            _P + "handshake",
            "bidirectional release handshake: docs/cyanrip-handshake.md",
        ),
    ]
    entries = [
        Entry(
            ref="ripper:cyanrip-fork",
            category="ripper",
            name="cyanrip",
            group=f"{owner}/{fs.FORK_BRANCH}",
            version=production.version,
            is_external=True,
            purl=f"pkg:github/{owner}/{project}@{production.pin}",
            description=(
                "The ripping backend (KDD-18): the Platterpus fork of cyanrip, "
                "built from source at the handshake-approved pin by the setup "
                "wizard and by --install-ripper, then exported to the host."
            ),
            used_in=used,
            enforced_in=(
                "src/platterpus/deps/fork_source.py (FORK_PIN, FORK_EXPECTED_VERSION)",
                "src/platterpus/handshake_approval.py (APPROVED_BY_ROUND)",
                "src/platterpus/deps/registry.py (min_version)",
            ),
            external_refs=(
                (
                    "vcs",
                    f"{repo}#{fs.FORK_BRANCH}",
                    "the fork; the bidirectional handshake partner",
                ),
                (
                    "other",
                    _manifest_url(),
                    "the fork's release-manifest.json (update offers)",
                ),
                (
                    "documentation",
                    f"{blob}/docs/cyanrip-handshake.md",
                    "the release handshake",
                ),
                *shared,
            ),
            properties=tuple(fork_props),
            required_by=(ROOT_REF,),
            ancestors=((up_project, up_owner, f"pkg:github/{up_owner}/{up_project}"),),
            detailed=True,
        )
    ]
    if review.pin != production.pin:
        entries.append(
            Entry(
                ref="ripper:cyanrip-fork-under-review",
                category="ripper",
                name="cyanrip (build under review)",
                group=f"{owner}/{fs.FORK_BRANCH}",
                version=review.version,
                is_external=True,
                scope="optional",
                purl=f"pkg:github/{owner}/{project}@{review.pin}",
                description=(
                    f"The build handshake round {fs.PIN_UNDER_REVIEW_ROUND} is "
                    "reviewing; installable on request, never the default."
                ),
                used_in=("src/platterpus/deps/fork_source.py (UNDER_REVIEW_TARGET)",),
                enforced_in=("src/platterpus/deps/fork_source.py (PIN_UNDER_REVIEW)",),
                external_refs=(("vcs", f"{repo}#{fs.FORK_BRANCH}", ""),),
                properties=(
                    (_P + "pin", review.pin),
                    (_P + "round", str(fs.PIN_UNDER_REVIEW_ROUND)),
                    (
                        _P + "published",
                        "yes" if fs.PIN_UNDER_REVIEW_IS_PUBLISHED else "no",
                    ),
                ),
                required_by=(ROOT_REF,),
                ancestors=(
                    (up_project, up_owner, f"pkg:github/{up_owner}/{up_project}"),
                ),
                detailed=True,
            )
        )
    stock_pkgs = _dnf_installs().get("cyanrip", ())
    entries.append(
        Entry(
            ref="ripper:cyanrip-upstream",
            category="ripper",
            name="cyanrip (upstream)",
            group=up_owner,
            version_range=_vers("generic", f">={minimum}"),
            is_external=True,
            scope="optional",
            purl=f"pkg:github/{up_owner}/{up_project}",
            description=(
                "Stock cyanrip. The wizard installs it first from the COPR so a "
                "failed fork build still leaves a working ripper; the fork is then "
                "exported over it. Also the project the fork tracks."
            ),
            used_in=("src/platterpus/deps/host_setup.py (the cyanrip step)",),
            enforced_in=("src/platterpus/deps/registry.py (min_version)",),
            external_refs=(("vcs", upstream, "upstream; the fork's ancestor"),),
            properties=(
                (
                    _P + "installed-by",
                    f"dnf install {_join(stock_pkgs)} from the COPR repo in the container",
                ),
                (
                    _P + "version-basis",
                    "whatever the COPR serves; not pinned by Platterpus",
                ),
                (_P + "checked-minimum", minimum),
            ),
            required_by=(ROOT_REF,),
        )
    )
    return entries


#: The texts shared with the fork, paired by document (docs/OWNERSHIP.md).
_SHARED_TEXTS: Final[tuple[tuple[str, str], ...]] = (
    ("docs/handshake-protocol.md", "shared with the fork (its PROTOCOL.md)"),
    ("docs/seam-rules.md", "shared with the fork, byte-identical"),
    ("docs/seam-commands.md", "shared with the fork, byte-identical"),
    ("docs/OWNERSHIP.md", "shared with the fork: who owns which shared file"),
)


def _container_entries() -> list[Entry]:
    from platterpus.deps.host_setup import DEFAULT_IMAGE

    registry_host, _, image_path = DEFAULT_IMAGE.partition("/")
    image_name, _, tag = image_path.partition(":")
    create = next(argv for step, argv in setup_plan() if step == "container")
    name = _container_name()
    return [
        Entry(
            ref="container:ripping",
            category="container",
            name=name,
            cdx_type="container",
            is_external=True,
            description=(
                "The Distrobox container the ripper runs in. The GUI never enters "
                "it to rip; it calls the host-exported wrapper (Critical rule #3)."
            ),
            used_in=(
                "src/platterpus/deps/host_setup.py (creates it)",
                "src/platterpus/drive_control.py (the scoped force-stop exception)",
                "src/platterpus/deps/host_teardown.py (removes it)",
            ),
            enforced_in=("src/platterpus/deps/host_setup.py (DEFAULT_CONTAINER)",),
            properties=((_P + "created-by", " ".join(create)),),
            required_by=(*_fork_refs(), "ripper:cyanrip-upstream"),
        ),
        Entry(
            ref="container:fedora-toolbox",
            category="container",
            name=image_name,
            cdx_type="container",
            version=tag,
            purl=f"pkg:docker/{image_name}@{tag}?repository_url={registry_host}",
            description="The image the ripping container is created from.",
            used_in=("src/platterpus/deps/host_setup.py",),
            enforced_in=("src/platterpus/deps/host_setup.py (DEFAULT_IMAGE)",),
            properties=(
                (_P + "image", DEFAULT_IMAGE),
                (
                    _P + "version-basis",
                    f"the moving '{tag}' tag; the pull decides the Fedora release",
                ),
            ),
            required_by=("container:ripping",),
        ),
    ]


def _ripper_build_entries() -> list[Entry]:
    """The fork's build inputs, read off the wizard's real ``cyanrip_fork`` step.

    Libraries are what the built binary links against, so they are needed at run
    time too (scope required, needed by the fork). The toolchain is build-only.
    """
    from platterpus.deps.fork_source import FORK_BUILD_PACKAGES

    planned = _dnf_installs().get("cyanrip_fork", ())
    if tuple(planned) != tuple(FORK_BUILD_PACKAGES):
        raise GeneratorError(
            "the wizard's cyanrip_fork dnf install no longer matches "
            "fork_source.FORK_BUILD_PACKAGES; read both before trusting either"
        )
    entries: list[Entry] = []
    for package in planned:
        lib = re.fullmatch(r"pkgconfig\((?P<name>[^)]+)\)", package)
        if lib:
            entries.append(
                Entry(
                    ref=f"lib:{lib.group('name')}",
                    category="ripper-build",
                    name=lib.group("name"),
                    cdx_type="library",
                    is_external=True,
                    description="Linked by the cyanrip fork (its src/meson.build).",
                    used_in=(
                        "building and running the cyanrip fork, inside the container",
                    ),
                    enforced_in=(
                        "src/platterpus/deps/fork_source.py (FORK_BUILD_PACKAGES)",
                    ),
                    properties=(
                        (_P + "requested-as", package),
                        (
                            _P + "version-basis",
                            "whichever package the container's dnf resolves for the pkg-config name",
                        ),
                    ),
                    required_by=_fork_refs(),
                )
            )
        else:
            entries.append(
                Entry(
                    ref=f"build:{package}",
                    category="ripper-build",
                    name=package,
                    cdx_type="application",
                    is_external=True,
                    scope="excluded",
                    description="Toolchain for building the cyanrip fork; not needed to run it.",
                    used_in=("building the cyanrip fork, inside the container",),
                    enforced_in=(
                        "src/platterpus/deps/fork_source.py (FORK_BUILD_PACKAGES)",
                    ),
                    properties=(
                        (
                            _P + "installed-by",
                            f"dnf install {package} in the container",
                        ),
                    ),
                )
            )
    return entries
