"""The pure rules behind the updater's refusal of an older version.

``update_version_guard`` decides; ``update_install`` fetches and calls it
(``tests/test_update_install.py`` drives the two together). The source-file parser
reads text served from the network, so it gets a never-raises property test.
"""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from platterpus import __version__
from platterpus.update_version_guard import (
    built_version_refusal,
    downgrade_refusal,
    parse_declared_version,
    source_url,
)


@pytest.mark.parametrize(
    ("candidate", "running", "refused"),
    [
        ("0.7.112", "0.7.113", True),
        ("0.7.113", "0.7.113", False),
        ("v0.7.114", "0.7.113", False),
        ("0.7.113rc1", "0.7.113", True),  # a pre-release of the running version
        ("0.8.0b1", "0.7.113", False),
        ("garbage", "0.7.113", True),  # cannot be shown not to be older
        ("0.7.114", "not-a-version", True),
    ],
)
def test_downgrade_refusal(candidate: str, running: str, refused: bool) -> None:
    assert (downgrade_refusal(candidate, running) is not None) is refused


def test_the_running_version_itself_is_comparable() -> None:
    """Otherwise every update would be refused, by the unparseable branch."""
    assert downgrade_refusal(__version__, __version__) is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('__version__: str = "0.7.113"\n', "0.7.113"),
        ("__version__ = '0.6.60'\n", "0.6.60"),
        ('# __version__ = "1.0"\n', None),  # a comment is not a declaration
        ('__version__ = "1.0"\n__version__ = "2.0"\n', None),  # which one?
        ("", None),
        ('__version__ = "0.7.113; rm -rf /"\n', None),
    ],
)
def test_parse_declared_version(text: str, expected: str | None) -> None:
    assert parse_declared_version(text) == expected


@given(st.text(max_size=2000))
def test_parse_declared_version_never_raises(text: str) -> None:
    result = parse_declared_version(text)
    assert result is None or 1 <= len(result) <= 64


@pytest.mark.parametrize(
    ("commit", "ok"),
    [
        ("a" * 40, True),
        ("A" * 40, True),
        ("a" * 39, False),
        ("5f1d036", False),  # a short name could be read as a branch
        ("main", False),
        (None, False),
        ("../" + "a" * 37, False),
    ],
)
def test_source_url_takes_only_a_full_commit(commit: str | None, ok: bool) -> None:
    url = source_url(commit)
    assert (url is not None) is ok
    if url is not None:
        assert url.startswith(
            "https://raw.githubusercontent.com/rmccann-hub/Platterpus/"
        )
        assert url.endswith("/src/platterpus/__init__.py")


def test_built_version_refusal_names_the_downgrade_first() -> None:
    why = built_version_refusal('__version__ = "0.6.60"\n', "99.0.0", "0.7.113")
    assert why is not None and "older than the version running" in why
    ok = built_version_refusal('__version__ = "99.0.0"\n', "99.0.0", "0.7.113")
    assert ok is None
    mislabelled = built_version_refusal('__version__ = "98.0.0"\n', "99.0.0", "0.7.113")
    assert mislabelled is not None and "not the release it claims" in mislabelled
