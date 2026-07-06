"""Tests for platterpus.adapters.cover_art.

The fetcher is injectable, so nothing here touches the network; metaflac
is replaced with a recording fake, so nothing shells out. Case taxonomy
per docs/testing.md: easy (happy paths), medium (mode matrix), hard
(partial failures), edge (empty/oversized), unexpected (junk bytes via
hypothesis — the institutional never-raises rule for anything that
parses external input).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from platterpus.adapters import cover_art
from platterpus.adapters.metaflac import MetaflacError

# Minimal valid-looking magic bytes for each format CAA serves.
_JPEG = b"\xff\xd8\xff\xe0" + b"x" * 32
_PNG = b"\x89PNG\r\n\x1a\n" + b"x" * 32
_GIF = b"GIF89a" + b"x" * 32

# A MusicBrainz release id (UUID). It's URL-encoded into the CAA request path;
# a UUID (only unreserved chars) encodes to itself, so the built URL is unchanged.
_MBID = "12345678-90ab-cdef-1234-567890abcdef"


class _FakeMetaflac:
    """Records embed calls; optionally fails for specific paths."""

    def __init__(self, fail_for: set[str] | None = None) -> None:
        self.embedded: list[tuple[Path, Path]] = []
        self._fail_for = fail_for or set()

    def embed_picture(self, flac_path: Path, image_path: Path) -> None:
        if flac_path.name in self._fail_for:
            raise MetaflacError("boom")
        self.embedded.append((flac_path, image_path))


# --- image_extension --------------------------------------------------------


def test_image_extension_recognizes_the_caa_formats() -> None:
    assert cover_art.image_extension(_JPEG) == ".jpg"
    assert cover_art.image_extension(_PNG) == ".png"
    assert cover_art.image_extension(_GIF) == ".gif"


def test_image_extension_rejects_non_images() -> None:
    # An HTML error page must not be saved as "cover.jpg".
    assert cover_art.image_extension(b"<html>404 Not Found</html>") == ""
    assert cover_art.image_extension(b"") == ""


@given(st.binary(max_size=64))
def test_image_extension_never_raises(data: bytes) -> None:
    result = cover_art.image_extension(data)
    assert result in ("", ".jpg", ".png", ".gif")


# --- fetch_front_cover ------------------------------------------------------


def test_fetch_returns_image_bytes_and_builds_the_caa_url() -> None:
    seen: list[str] = []

    def fetcher(url: str) -> bytes:
        seen.append(url)
        return _JPEG

    data = cover_art.fetch_front_cover(_MBID, fetcher=fetcher)

    assert data == _JPEG
    assert seen == [f"https://coverartarchive.org/release/{_MBID}/front"]


def test_fetch_url_encodes_the_release_id() -> None:
    """Regression: the release id is percent-encoded into the request path, so a
    tampered id containing "/" or "?" can't rewrite which resource is fetched
    (it can only address a non-existent release → 404)."""
    seen: list[str] = []

    def fetcher(url: str) -> bytes:
        seen.append(url)
        return b""  # 404-ish; we only care about the URL that was built

    cover_art.fetch_front_cover("abc/../release-group/x?q=1", fetcher=fetcher)

    assert seen == [
        "https://coverartarchive.org/release/abc%2F..%2Frelease-group%2Fx%3Fq%3D1/front"
    ]


def test_fetch_blank_release_id_skips_the_network() -> None:
    def fetcher(url: str) -> bytes:  # pragma: no cover — must not be called
        raise AssertionError("fetcher must not be called without an MBID")

    assert cover_art.fetch_front_cover("", fetcher=fetcher) is None
    assert cover_art.fetch_front_cover("   ", fetcher=fetcher) is None


def test_fetch_failure_returns_none() -> None:
    # 404 (not in CAA) surfaces as HTTPError, an OSError subclass — the
    # common, normal case for discs nobody uploaded art for.
    def fetcher(url: str) -> bytes:
        raise OSError("HTTP Error 404: Not Found")

    assert cover_art.fetch_front_cover(_MBID, fetcher=fetcher) is None


def test_fetch_non_image_response_returns_none() -> None:
    fetched = cover_art.fetch_front_cover(
        _MBID, fetcher=lambda url: b"<html>rate limited</html>"
    )
    assert fetched is None


def test_fetch_empty_or_oversized_returns_none() -> None:
    assert cover_art.fetch_front_cover(_MBID, fetcher=lambda url: b"") is None
    huge = _JPEG + b"\0" * (30 * 1024 * 1024)
    assert cover_art.fetch_front_cover(_MBID, fetcher=lambda url: huge) is None


# --- plan_actions -----------------------------------------------------------


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("", (False, False)),
        ("embed", (True, False)),
        ("file", (False, True)),
        ("complete", (True, True)),
    ],
)
def test_plan_actions_maps_the_cover_art_modes(
    mode: str, expected: tuple[bool, bool]
) -> None:
    assert cover_art.plan_actions(mode, False, "mbid") == expected


def test_plan_actions_noop_when_the_ripper_fetches_art_itself() -> None:
    # whipper with a release ID passes --cover-art and does this itself.
    assert cover_art.plan_actions("complete", True, "mbid") == (False, False)


def test_plan_actions_noop_without_a_release_id() -> None:
    # Unidentified disc: there is nothing to look up art for.
    assert cover_art.plan_actions("complete", False, "") == (False, False)
    assert cover_art.plan_actions("complete", False, "  ") == (False, False)


# --- apply_cover_art --------------------------------------------------------


def _album(tmp_path: Path, tracks: int = 2) -> Path:
    album = tmp_path / "Artist" / "Album"
    album.mkdir(parents=True)
    for n in range(1, tracks + 1):
        (album / f"{n:02d} - Track.flac").write_bytes(b"flac")
    return album


def test_apply_embeds_and_saves_when_both_requested(tmp_path: Path) -> None:
    album = _album(tmp_path)
    fake = _FakeMetaflac()

    result = cover_art.apply_cover_art(
        album,
        _MBID,
        embed=True,
        save_file=True,
        metaflac=fake,
        fetcher=lambda url: _JPEG,
    )

    assert (album / "cover.jpg").read_bytes() == _JPEG
    assert [f.name for f, _img in fake.embedded] == [
        "01 - Track.flac",
        "02 - Track.flac",
    ]
    assert "embedded in 2 track(s)" in result.message
    assert "cover.jpg" in result.message


def test_apply_embed_only_removes_the_temp_image(tmp_path: Path) -> None:
    album = _album(tmp_path)
    fake = _FakeMetaflac()

    result = cover_art.apply_cover_art(
        album,
        _MBID,
        embed=True,
        save_file=False,
        metaflac=fake,
        fetcher=lambda url: _PNG,
    )

    # The PNG was written for metaflac to import, then cleaned up.
    assert not (album / "cover.png").exists()
    assert len(fake.embedded) == 2
    assert "embedded in 2 track(s)" in result.message


def test_apply_file_only_never_touches_metaflac(tmp_path: Path) -> None:
    album = _album(tmp_path)
    fake = _FakeMetaflac()

    result = cover_art.apply_cover_art(
        album,
        _MBID,
        embed=False,
        save_file=True,
        metaflac=fake,
        fetcher=lambda url: _JPEG,
    )

    assert (album / "cover.jpg").exists()
    assert fake.embedded == []
    assert "saved as cover.jpg" in result.message


def test_apply_reports_when_no_art_exists(tmp_path: Path) -> None:
    album = _album(tmp_path)
    fake = _FakeMetaflac()

    def fetcher(url: str) -> bytes:
        raise OSError("404")

    result = cover_art.apply_cover_art(
        album, "mbid", embed=True, save_file=True, metaflac=fake, fetcher=fetcher
    )

    assert fake.embedded == []
    assert not (album / "cover.jpg").exists()
    assert "none found" in result.message
    assert "rip unaffected" in result.message


def test_apply_survives_per_file_embed_failures(tmp_path: Path) -> None:
    """One bad FLAC must not stop the others from getting art."""
    album = _album(tmp_path, tracks=3)
    fake = _FakeMetaflac(fail_for={"02 - Track.flac"})

    result = cover_art.apply_cover_art(
        album,
        _MBID,
        embed=True,
        save_file=False,
        metaflac=fake,
        fetcher=lambda url: _JPEG,
    )

    assert len(fake.embedded) == 2
    assert "embedded in 2 track(s)" in result.message


def test_apply_with_no_flacs_still_reports_honestly(tmp_path: Path) -> None:
    album = tmp_path / "empty"
    album.mkdir()
    fake = _FakeMetaflac()

    result = cover_art.apply_cover_art(
        album,
        _MBID,
        embed=True,
        save_file=False,
        metaflac=fake,
        fetcher=lambda url: _JPEG,
    )

    assert "embedding failed" in result.message  # 0 embedded — don't claim success


def test_apply_reports_when_image_cannot_be_saved(tmp_path: Path) -> None:
    """If the cover bytes can't be written to disk (e.g. the rip dir isn't a
    directory), report it without crashing and without embedding."""
    not_a_dir = tmp_path / "rip_dir"
    not_a_dir.write_text("i am a file, not a directory")
    fake = _FakeMetaflac()

    result = cover_art.apply_cover_art(
        not_a_dir,
        _MBID,
        embed=True,
        save_file=True,
        metaflac=fake,
        fetcher=lambda url: _JPEG,
    )

    assert fake.embedded == []
    assert "could not be saved" in result.message


def test_apply_survives_temp_image_unlink_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Embed-only cleans up the temp image; if that unlink fails it's purely
    cosmetic and must not change the (successful) outcome."""
    album = _album(tmp_path, tracks=1)
    fake = _FakeMetaflac()

    import pathlib

    def boom_unlink(self: pathlib.Path, *a: object, **k: object) -> None:
        raise OSError("cannot remove")

    monkeypatch.setattr(pathlib.Path, "unlink", boom_unlink)

    result = cover_art.apply_cover_art(
        album,
        _MBID,
        embed=True,
        save_file=False,
        metaflac=fake,
        fetcher=lambda url: _JPEG,
    )

    assert len(fake.embedded) == 1
    assert "embedded in 1 track(s)" in result.message


# --- CoverArtResult (structured outcome for the rip report, 0.4.10) ---------


def test_apply_returns_structured_result(tmp_path: Path) -> None:
    album = _album(tmp_path)
    result = cover_art.apply_cover_art(
        album,
        _MBID,
        embed=True,
        save_file=True,
        metaflac=_FakeMetaflac(),
        fetcher=lambda url: _JPEG,
        mode="complete",
    )
    assert result.mode == "complete"
    assert result.found is True and result.reason == "ok"
    assert result.embedded_count == 2
    assert result.saved_as == "cover.jpg"
    assert result.format == "jpg"
    assert result.bytes == len(_JPEG)
    assert result.release_id == _MBID


def test_apply_result_distinguishes_404_from_network(tmp_path: Path) -> None:
    import urllib.error

    def not_found(url: str) -> bytes:
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)

    r = cover_art.apply_cover_art(
        tmp_path,
        _MBID,
        embed=True,
        save_file=False,
        metaflac=_FakeMetaflac(),
        fetcher=not_found,
    )
    assert r.found is False and r.reason == "404"

    def down(url: str) -> bytes:
        raise OSError("connection refused")

    r2 = cover_art.apply_cover_art(
        tmp_path,
        _MBID,
        embed=True,
        save_file=False,
        metaflac=_FakeMetaflac(),
        fetcher=down,
    )
    assert r2.found is False and r2.reason == "network"


# --- save_additional_covers (back + booklet) --------------------------------


def test_save_additional_covers_saves_back_and_booklet(tmp_path: Path) -> None:
    manifest = json.dumps(
        {
            "images": [
                {"types": ["Front"], "image": "http://caa/front.jpg"},
                {"types": ["Back"], "image": "http://caa/back.jpg"},
                {"types": ["Booklet"], "image": "http://caa/b1.jpg"},
                {"types": ["Booklet"], "image": "http://caa/b2.jpg"},
            ]
        }
    ).encode()

    def fetcher(url: str) -> bytes:
        # The manifest URL has no /front suffix; everything else is an image.
        return manifest if url.rstrip("/").endswith(_MBID) else _JPEG

    saved = cover_art.save_additional_covers(tmp_path, _MBID, fetcher=fetcher)
    assert set(saved) == {"back.jpg", "booklet-01.jpg", "booklet-02.jpg"}
    assert (tmp_path / "back.jpg").exists()
    assert (tmp_path / "booklet-02.jpg").exists()
    # The front cover is NOT saved here — apply_cover_art owns it.
    assert not (tmp_path / "front.jpg").exists()


def test_save_additional_covers_no_release_or_error(tmp_path: Path) -> None:
    assert cover_art.save_additional_covers(tmp_path, "") == []

    def boom(_url: str) -> bytes:
        raise OSError("network down")

    assert cover_art.save_additional_covers(tmp_path, _MBID, fetcher=boom) == []


def test_save_additional_covers_ignores_non_image_bytes(tmp_path: Path) -> None:
    manifest = json.dumps(
        {"images": [{"types": ["Back"], "image": "http://caa/back"}]}
    ).encode()

    def fetcher(url: str) -> bytes:
        return manifest if url.rstrip("/").endswith(_MBID) else b"<html>nope</html>"

    assert cover_art.save_additional_covers(tmp_path, _MBID, fetcher=fetcher) == []
    assert not (tmp_path / "back.jpg").exists()


# --- apply_local_cover_art (load from a file) -------------------------------


def test_apply_local_cover_art_embeds_and_saves(tmp_path: Path) -> None:
    (tmp_path / "01.flac").write_bytes(b"")
    (tmp_path / "02.flac").write_bytes(b"")
    img = tmp_path / "mine.png"
    img.write_bytes(_PNG)
    fake = _FakeMetaflac()
    r = cover_art.apply_local_cover_art(
        tmp_path, img, embed=True, save_file=True, metaflac=fake
    )
    assert r.found is True and r.mode == "local"
    assert r.embedded_count == 2
    assert (tmp_path / "cover.png").exists()
    assert r.saved_as == "cover.png"


def test_apply_local_cover_art_embed_only_removes_the_file(tmp_path: Path) -> None:
    (tmp_path / "01.flac").write_bytes(b"")
    img = tmp_path / "mine.jpg"
    img.write_bytes(_JPEG)
    r = cover_art.apply_local_cover_art(
        tmp_path, img, embed=True, save_file=False, metaflac=_FakeMetaflac()
    )
    assert r.embedded_count == 1
    assert not (tmp_path / "cover.jpg").exists()  # temp copy cleaned up


def test_apply_local_cover_art_rejects_non_image(tmp_path: Path) -> None:
    bad = tmp_path / "notimg.txt"
    bad.write_bytes(b"hello, not an image")
    r = cover_art.apply_local_cover_art(
        tmp_path, bad, embed=True, save_file=True, metaflac=_FakeMetaflac()
    )
    assert r.found is False and r.reason == "not-image"
    assert not (tmp_path / "cover.png").exists()


def test_apply_local_cover_art_missing_file(tmp_path: Path) -> None:
    r = cover_art.apply_local_cover_art(
        tmp_path,
        tmp_path / "nope.png",
        embed=True,
        save_file=False,
        metaflac=_FakeMetaflac(),
    )
    assert r.found is False and r.reason == "read-failed"
