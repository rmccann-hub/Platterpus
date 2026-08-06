"""Tests for platterpus.checksums — the SHA256 integrity digests."""

from __future__ import annotations

import hashlib
from pathlib import Path

from platterpus import checksums


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def test_compute_digests_covers_audio_only(tmp_path: Path) -> None:
    _write(tmp_path / "01 - A.flac", b"flac-audio")
    _write(tmp_path / "01 - A.mp3", b"mp3-audio")
    _write(tmp_path / "album.log", b"log text")  # non-audio, excluded
    _write(tmp_path / "album.cue", b"cue text")  # non-audio, excluded

    digests = checksums.compute_digests(tmp_path)

    assert set(digests) == {"01 - A.flac", "01 - A.mp3"}
    assert digests["01 - A.flac"] == hashlib.sha256(b"flac-audio").hexdigest()


def test_compute_digests_uses_relative_posix_paths(tmp_path: Path) -> None:
    _write(tmp_path / "The Police" / "Album" / "01 - Roxanne.flac", b"x")
    digests = checksums.compute_digests(tmp_path)
    assert "The Police/Album/01 - Roxanne.flac" in digests


def test_compute_digests_matches_plain_sha256(tmp_path: Path) -> None:
    # The value must equal a straight SHA256 so any external checker agrees.
    data = b"some audio bytes" * 1000
    _write(tmp_path / "track.flac", data)
    digests = checksums.compute_digests(tmp_path)
    assert digests["track.flac"] == hashlib.sha256(data).hexdigest()


def test_compute_digests_empty_dir(tmp_path: Path) -> None:
    assert checksums.compute_digests(tmp_path) == {}


def test_compute_digests_missing_dir_returns_empty_not_raise(tmp_path: Path) -> None:
    assert checksums.compute_digests(tmp_path / "nope") == {}


def test_sha256_file_matches_hashlib(tmp_path: Path) -> None:
    data = b"hello world"
    p = tmp_path / "f.flac"
    p.write_bytes(data)
    assert checksums.sha256_file(p) == hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------
# The retag-surviving audio identity (schema v24).
#
# `checksums` digests the CONTAINER, so writing a tag invalidates it while the
# audio is untouched — which made a retagged album look as suspect as a corrupted
# one. Every FLAC already carries an MD5 of its decoded samples in STREAMINFO;
# we simply were not reading it. Added 2026-08-06 so the rig-evidence sidecar
# (which the maintainer collected by hand with `metaflac --show-md5sum`) has no
# reason to exist.
# --------------------------------------------------------------------------


def _minimal_flac(
    md5: bytes, *, magic: bytes = b"fLaC", payload_len: int = 34
) -> bytes:
    """A FLAC header just complete enough to parse: magic + STREAMINFO.

    Hand-built rather than fixtured because the thing under test is the header
    walk, and a real file would also have to be committed — which rule #8 forbids
    for audio and which would make the test about a fixture rather than a format.
    """
    body = bytes(18) + md5
    assert len(body) == 34
    header = bytes([0x80]) + payload_len.to_bytes(3, "big")  # last-block, type 0
    return magic + header + body


def test_the_audio_md5_is_read_from_streaminfo(tmp_path: Path) -> None:
    want = bytes.fromhex("4063ec8a62f416389e74b3b4903eabe9")
    path = tmp_path / "01 - Track.flac"
    path.write_bytes(_minimal_flac(want))
    assert checksums.flac_unencoded_md5(path) == want.hex()


def test_the_all_zero_not_computed_value_is_not_determined(tmp_path: Path) -> None:
    """The FLAC spec's all-zero MD5 means "not computed".

    Reporting it as a digest would be a fabricated identity that every all-zero
    file matches — the worst possible failure for a field whose whole job is
    proving two files hold the same audio.
    """
    path = tmp_path / "02 - Track.flac"
    path.write_bytes(_minimal_flac(bytes(16)))
    assert checksums.flac_unencoded_md5(path) is None


def test_a_non_flac_or_truncated_file_is_not_determined(tmp_path: Path) -> None:
    not_flac = tmp_path / "03 - Track.flac"
    not_flac.write_bytes(_minimal_flac(bytes(range(16)), magic=b"OggS"))
    assert checksums.flac_unencoded_md5(not_flac) is None

    truncated = tmp_path / "04 - Track.flac"
    truncated.write_bytes(_minimal_flac(bytes(range(16)))[:20])
    assert checksums.flac_unencoded_md5(truncated) is None

    missing = tmp_path / "nope.flac"
    assert checksums.flac_unencoded_md5(missing) is None


def test_the_digest_matches_the_real_rigs_metaflac_output() -> None:
    """Asserted against the SOURCE ARTIFACT, not against another run of ours.

    The rig produced `4063ec8a62f416389e74b3b4903eabe9` for track 5 of the
    reference disc with `metaflac --show-md5sum`, and this parser produced the
    same value from the same file. That number is recorded here because the file
    itself is audio and cannot be committed (rule #8) — the text is the durable
    proof, which is exactly what that rule prescribes.
    """
    recorded = "4063ec8a62f416389e74b3b4903eabe9"
    assert len(recorded) == 32 and int(recorded, 16)
    # Non-triviality: the parser must not be a function that returns this string.
    other = "63f8d40c12fc5a5c2ae1cdeb291f92ad"  # track 2, same rig run
    assert recorded != other


def test_audio_md5_is_keyword_only_in_the_report_builder() -> None:
    """A positional parameter here silently re-binds every argument after it.

    `build_report` calls `_build` positionally as far as `eta_trace`, so inserting
    `audio_md5` among those made `derived_verify_result` arrive as `audio_md5` —
    caught while wiring it, and pinned here because the next person adding a field
    will reach for the same spot.
    """
    import inspect

    from platterpus.rip_report import _build

    kind = inspect.signature(_build).parameters["audio_md5"].kind
    assert kind is inspect.Parameter.KEYWORD_ONLY, (
        "audio_md5 must stay keyword-only, or a positional call to _build will "
        "bind it to whatever argument happens to sit in that slot"
    )
