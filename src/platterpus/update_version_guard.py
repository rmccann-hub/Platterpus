"""Refuse an app update that would install an older Platterpus than the one running.

**Why this exists** (the claude-code-skills review of 2026-10-26, item 2.3). The
update check never OFFERS an older version (``update_check.is_newer``), but the
installer took whatever version it was handed, and the build attestation it
checks (``update_attestation``) proves *who built* a file, not *which version* it
is: a genuine older build served under a newer release's name passes it. So the
installer now checks the version twice, and the second check does not take the
offer's word for it:

1. **Before anything is fetched**, the version it was asked for must not be lower
   than the running one. Cheap, offline, and it saves a 270 MB download.
2. **After the attestation verifies**, the version the file was BUILT as must
   equal the one asked for, and so must not be lower either. That version is read
   from the commit the signed provenance names (``resolvedDependencies[0]``, bound
   to the file's SHA-256 by the same signature), as that commit's own
   ``src/platterpus/__init__.py`` declares it. A commit is content-addressed, so
   the file at it cannot change after the fact, and ``release.yml`` refuses a
   release whose built binary's ``--version`` differs from its tag.

**Why the commit's source and not the AppImage's own bytes.** The version is
inside the AppImage's compressed SquashFS; reading it needs a SquashFS reader (a
new dependency, or a parser of an untrusted format written here), ``unsquashfs``
on the host (not guaranteed), or running the downloaded file before it is
installed (it needs FUSE, or extracts 270 MB to ``/tmp``). The signed provenance is
part of the artifact's evidence and is already verified at this point; the
version it leads to is derived from content, not from the release's label.

Pure functions, so the rules are testable without a network. ``update_install``
does the fetching, on the update worker's thread. Nothing here raises.
"""

from __future__ import annotations

import re
from typing import Final

from platterpus.update_check import release_sort_key

#: Where a commit's version declaration is served. A commit, not a branch or tag,
#: so the answer cannot move.
_SOURCE_URL: Final[str] = (
    "https://raw.githubusercontent.com/rmccann-hub/Platterpus/{commit}/"
    "src/platterpus/__init__.py"
)

#: Cap on that file's read. It is 752 bytes at 0.7.113; 64 KiB stops a hostile
#: or broken server streaming a large body into memory.
MAX_SOURCE_BYTES: Final[int] = 64 * 1024

_FULL_COMMIT: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{40}$")

#: ``__version__: str = "0.7.113"`` (the form since the annotation pass), or the
#: older ``__version__ = "…"``. Anchored to a line start; the value is bounded.
_DECLARATION: Final[re.Pattern[str]] = re.compile(
    r"^__version__(?:[ \t]*:[ \t]*str)?[ \t]*=[ \t]*"
    r"(?P<quote>[\"'])(?P<version>[0-9A-Za-z.+-]{1,64})(?P=quote)",
    re.MULTILINE,
)


def source_url(commit: str | None) -> str | None:
    """The URL of ``commit``'s version file, or ``None`` if it is not a full SHA.

    A short or malformed commit is refused rather than resolved: a short name could
    be read as a branch, which can move.
    """
    value = (commit or "").strip().lower()
    if not _FULL_COMMIT.match(value):
        return None
    return _SOURCE_URL.format(commit=value)


def parse_declared_version(text: str) -> str | None:
    """The ``__version__`` a source file declares, or ``None``. Never raises.

    Exactly one declaration is required: two would mean we cannot say which one
    the build used.
    """
    matches = list(_DECLARATION.finditer(text or ""))
    if len(matches) != 1:
        return None
    return matches[0].group("version")


def _bare(version: str) -> str:
    value = (version or "").strip()
    return value[1:] if value[:1] in ("v", "V") else value


def downgrade_refusal(candidate: str, running: str) -> str | None:
    """Why installing ``candidate`` over ``running`` is refused, or ``None``.

    Equal is allowed (reinstalling the running version is not a downgrade).
    **Unparseable is refused**, either side: a version we cannot order is one we
    cannot show is not older, and the protected thing is the installed app.
    """
    cand = release_sort_key(_bare(candidate))
    curr = release_sort_key(_bare(running))
    if cand is None:
        return (
            f"the update's version ({candidate!r}) is not one Platterpus can "
            "compare, so it cannot be shown not to be older — not installed"
        )
    if curr is None:
        return (
            f"this Platterpus's own version ({running!r}) is not one it can "
            "compare, so an update cannot be shown not to be older — not installed"
        )
    if cand < curr:
        return (
            f"Platterpus {_bare(candidate)} is older than the version running "
            f"({_bare(running)}), and the updater never installs an older version "
            "— not installed"
        )
    return None


def built_version_refusal(source_text: str, requested: str, running: str) -> str | None:
    """Why the version the file was BUILT as is refused, or ``None``.

    ``source_text`` is the attested commit's ``src/platterpus/__init__.py``.
    """
    built = parse_declared_version(source_text)
    if built is None:
        return (
            "the source the update was built from does not declare one version, "
            "so the update's own version could not be read — not installed"
        )
    # The downgrade first: of the two facts it is the one that protects the user,
    # and an older build offered under a newer name trips both.
    older = downgrade_refusal(built, running)
    if older is not None:
        return f"{older} (read from the source the update was built from)"
    if built != _bare(requested):
        return (
            f"the update offered as {_bare(requested)} was built as Platterpus "
            f"{built}, so it is not the release it claims to be — not installed"
        )
    return None
