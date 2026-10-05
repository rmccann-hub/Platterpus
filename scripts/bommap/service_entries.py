"""External services, with their endpoints read from the URL constants in src/."""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from bommap.model import _P, ROOT_REF, Entry
from bommap.reading import _project, _require
from bommap.tool_entries import _data_entries


def _service_entries() -> list[Entry]:
    import musicbrainzngs.musicbrainz as mb_library

    from platterpus import help_content
    from platterpus.adapters import cover_art, ctdb_client
    from platterpus.deps import fork_source, host_setup, registry, ripper_manifest
    from platterpus.update_attestation import OIDC_ISSUER, PREDICATE_TYPE
    from platterpus.update_check import RELEASES_API_URL, RELEASES_PAGE_URL
    from platterpus.update_install import asset_url

    mb_scheme = "https" if mb_library.https else "http"
    caa_base = cover_art.COVER_URL_TEMPLATE.split("{", 1)[0]
    ctdb = (
        f"{ctdb_client.CTDB_SCHEME}://{ctdb_client.CTDB_HOST}{ctdb_client.LOOKUP_PATH}"
    )
    # The COPR stanza's baseurl carries `$releasever-$basearch`, which dnf fills
    # in; the endpoint recorded is the directory above that placeholder.
    copr_base: set[str] = set()
    for url in re.findall(
        r"^(?:baseurl|gpgkey)=(\S+)", host_setup.CYANRIP_COPR_REPO_CONTENT, re.MULTILINE
    ):
        copr_base.add(
            url.split("$", 1)[0].rsplit("/", 1)[0] + "/" if "$" in url else url
        )
    picard = next(spec for spec in registry.SPECS if spec.dep_id == "picard")
    flathub = [
        word for word in (picard.install_command or []) if word.startswith("https://")
    ]
    installer = host_setup.install_argv(
        "distrobox", Path("/nonexistent/os-release"), "pkexec"
    )
    installer_urls = (
        re.findall(r"https://\S+", installer[2]) if len(installer) > 2 else []
    )
    download_base = asset_url("0").split("/v0/", 1)[0] + "/"
    image_registry = host_setup.DEFAULT_IMAGE.split("/", 1)[0]
    pypi_name = str(_project()["name"])
    # The drive-offset page the drive setup dialog links to. Its witness is the
    # dialog's own link text; the snapshot's source URL comes from the data entry.
    offsets_page = "https://www.accuraterip.com/driveoffsets.htm"
    _require(
        "src/platterpus/ui/drive_setup_dialog.py",
        offsets_page,
        as_word=True,
        why="AccurateRip drive-offset link",
    )
    snapshot_source = _data_entries()[0].external_refs[0][1]

    def service(
        key: str,
        name: str,
        provider: str,
        endpoints: Sequence[str],
        when: str,
        used_in: Sequence[str],
        description: str,
        data: Sequence[tuple[str, str]] = (),
        required_by: Sequence[str] = (ROOT_REF,),
        props: Sequence[tuple[str, str]] = (),
        refs: Sequence[tuple[str, str, str]] = (),
    ) -> Entry:
        return Entry(
            ref=f"svc:{key}",
            kind="service",
            category="service",
            name=name,
            provider=provider,
            endpoints=tuple(endpoints),
            description=description,
            used_in=tuple(used_in),
            data=tuple(data),
            properties=((_P + "when", when), *props),
            external_refs=tuple(refs),
            required_by=tuple(required_by),
        )

    return [
        service(
            "musicbrainz",
            "MusicBrainz web service",
            "MetaBrainz Foundation",
            [f"{mb_scheme}://{mb_library.hostname}/ws/2/"],
            "runtime (every disc lookup)",
            ["src/platterpus/adapters/musicbrainz_client.py"],
            "Release metadata for the disc. The only metadata source (Critical rule #5); the endpoint is musicbrainzngs's own, which our client never overrides.",
            data=(
                ("outbound", "disc ID and table of contents"),
                ("inbound", "release metadata"),
            ),
            required_by=("pypi:musicbrainzngs",),
            props=((_P + "user-agent-contact", help_content.REPO_URL),),
        ),
        service(
            "cover-art-archive",
            "Cover Art Archive",
            "MetaBrainz Foundation / Internet Archive",
            sorted({caa_base, "https://coverartarchive.org/"}),
            "runtime (cover art after a rip; a reachability check in --doctor)",
            [
                "src/platterpus/adapters/cover_art.py",
                _require(
                    "src/platterpus/preflight.py",
                    "https://coverartarchive.org/",
                    why="CAA preflight",
                ),
            ],
            "Front cover images for the identified release.",
            data=(("outbound", "release MBID"), ("inbound", "cover image")),
            props=((_P + "url-template", cover_art.COVER_URL_TEMPLATE),),
        ),
        service(
            "ctdb",
            "CUETools Database (CTDB)",
            "CUETools",
            [ctdb],
            "runtime (optional verify after a rip)",
            ["src/platterpus/adapters/ctdb_client.py"],
            "Per-track CRCs to compare with the rip. Plain HTTP by necessity: the host serves no valid certificate, and trust comes from comparing CRCs, not from the transport.",
            data=(("outbound", "disc table of contents"), ("inbound", "CRCs")),
        ),
        service(
            "accuraterip",
            "AccurateRip",
            "Illustrate",
            sorted({snapshot_source, offsets_page}),
            "maintenance (the offset snapshot); a link in the drive setup dialog",
            [
                "scripts/update_drive_offsets.py",
                "src/platterpus/ui/drive_setup_dialog.py",
            ],
            "Source of the bundled drive-offset table. The per-track AccurateRip results in a rip come from cyanrip's log; Platterpus does not query the AccurateRip database itself.",
            required_by=("data:accuraterip-drive-offsets",),
        ),
        service(
            "github-releases-api",
            "GitHub Releases API (update check)",
            "GitHub",
            [RELEASES_API_URL],
            "runtime (update check)",
            ["src/platterpus/update_check.py"],
            "Lists Platterpus releases for the in-app update check.",
            data=(("inbound", "release list"),),
            props=((_P + "release-page", RELEASES_PAGE_URL),),
        ),
        service(
            "github-release-downloads",
            "GitHub release downloads (update install)",
            "GitHub",
            [download_base],
            "runtime (installing an update)",
            ["src/platterpus/update_install.py"],
            "The AppImage, its .sha256 and its .sigstore.json attestation for an in-app update.",
            data=(("inbound", "AppImage and attestation"),),
        ),
        service(
            "fork-release-manifest",
            "cyanrip fork release manifest",
            "rmccann-hub/cyanrip",
            [ripper_manifest.MANIFEST_URL],
            "runtime (ripper update offers)",
            ["src/platterpus/deps/ripper_manifest.py"],
            "The fork's published builds per channel, for the ripper update offer.",
            data=(("inbound", "release manifest JSON"),),
        ),
        service(
            "fork-source",
            "cyanrip fork source (git clone)",
            "GitHub",
            [fork_source.FORK_REPO_URL],
            "setup (the wizard and --install-ripper, inside the container)",
            ["src/platterpus/deps/fork_source.py"],
            "Cloned at the pinned commit to build the fork.",
            data=(("inbound", "source tree"),),
            required_by=("ripper:cyanrip-fork",),
        ),
        service(
            "sigstore",
            "Sigstore public-good instance",
            "Sigstore (OpenSSF)",
            [],
            "runtime (installing an update) and release (attesting the build)",
            ["src/platterpus/update_attestation.py", ".github/workflows/release.yml"],
            "Signs the release's build-provenance attestation and supplies the trust root the updater verifies it against.",
            data=(("inbound", "trust root"),),
            required_by=("pypi:sigstore",),
            props=(
                (
                    _P + "endpoint-basis",
                    "not named in Platterpus; the sigstore library's production trust root decides",
                ),
                (_P + "accepted-issuer", OIDC_ISSUER),
                (_P + "predicate-type", PREDICATE_TYPE),
            ),
        ),
        service(
            "fedora-registry",
            "Fedora container registry",
            "Fedora Project",
            [f"https://{image_registry}/"],
            "setup (creating the container)",
            ["src/platterpus/deps/host_setup.py"],
            "Serves the fedora-toolbox image.",
            data=(("inbound", "container image"),),
            required_by=("container:fedora-toolbox",),
        ),
        service(
            "fedora-repositories",
            "Fedora package repositories",
            "Fedora Project",
            [],
            "setup (dnf inside the container)",
            ["src/platterpus/deps/host_setup.py", "src/platterpus/deps/fork_source.py"],
            "flac, cd-paranoia and the fork's build inputs.",
            data=(("inbound", "RPM packages"),),
            required_by=("container:ripping",),
            props=(
                (
                    _P + "endpoint-basis",
                    "the container image's own configured repositories; not named in Platterpus",
                ),
            ),
        ),
        service(
            "copr-barsnick-non-fed",
            "Fedora COPR barsnick/non-fed",
            "Fedora COPR",
            sorted(copr_base),
            "setup (the stock cyanrip package)",
            ["src/platterpus/deps/host_setup.py"],
            "The GPG-signed COPR that packages stock cyanrip for Fedora.",
            data=(("inbound", "RPM packages"),),
            required_by=("ripper:cyanrip-upstream",),
        ),
        service(
            "flathub",
            "Flathub",
            "Flathub",
            flathub,
            "on request (installing Picard)",
            ["src/platterpus/deps/registry.py"],
            "MusicBrainz Picard's Flatpak.",
            data=(("inbound", "Flatpak"),),
            required_by=("tool:picard",),
        ),
        service(
            "distrobox-installer",
            "Distrobox upstream installer",
            "89luca89/distrobox",
            installer_urls,
            "setup (only on an unrecognised distro)",
            ["src/platterpus/deps/host_setup.py"],
            "Installs Distrobox where no known package manager applies.",
            data=(("inbound", "installer script"),),
            required_by=("tool-host:distrobox",),
        ),
        service(
            "pypi",
            "PyPI",
            "Python Software Foundation",
            [],
            "release (publishing) and development (installing)",
            [
                _require(
                    ".github/workflows/publish-pypi.yml",
                    "pypa/gh-action-pypi-publish",
                    why="PyPI publish",
                )
            ],
            "Where Platterpus's wheel and sdist are published, and where pip resolves every Python package above.",
            data=(("outbound", "wheel and sdist"),),
            required_by=(),
            props=(
                (
                    _P + "endpoint-basis",
                    "the pip and gh-action-pypi-publish defaults; not named in Platterpus",
                ),
            ),
            refs=(("distribution", f"https://pypi.org/project/{pypi_name}/", ""),),
        ),
    ]
