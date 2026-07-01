"""Tests for platterpus.adapters.derived_verify — proving the derived files.

The real ffmpeg decode is hardware/tool-gated; here we inject a fake PCM hasher
so we exercise the honest per-format logic (lossless bit-identity vs lossy
decode-clean) deterministically and prove the never-raises contract.
"""

from __future__ import annotations

from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from platterpus.adapters.derived_verify import (
    DerivedVerifyResult,
    _default_hasher,
    verify_derived_files,
)


def _hasher_from(mapping: dict[Path, str | None]):
    """Build a fake PCM hasher returning canned digests (None = decode failed)."""

    def hasher(path: Path) -> str | None:
        return mapping.get(path)

    return hasher


# --- Lossless (WAV / WavPack): bit-identity vs the master --------------------


def test_lossless_all_bit_identical_is_ok() -> None:
    d1, m1 = Path("01.wv"), Path("01.flac")
    d2, m2 = Path("02.wv"), Path("02.flac")
    # Each derived matches its own master's PCM.
    hasher = _hasher_from({d1: "aaa", m1: "aaa", d2: "bbb", m2: "bbb"})
    result = verify_derived_files([(d1, m1), (d2, m2)], fmt="wavpack", hasher=hasher)
    assert result.ok is True
    assert result.lossless is True
    assert result.checked == 2 and result.expected == 2
    assert result.complete is True
    assert result.mismatches == () and result.failures == ()


def test_lossless_mismatch_is_flagged_not_papered_over() -> None:
    d1, m1 = Path("01.wav"), Path("01.flac")
    # The derived WAV's PCM differs from the master — a real defect.
    hasher = _hasher_from({d1: "different", m1: "master"})
    result = verify_derived_files([(d1, m1)], fmt="wav", hasher=hasher)
    assert result.ok is False
    assert result.mismatches == (d1,)
    assert result.failures == ()


def test_lossless_undecodable_derived_is_a_failure() -> None:
    d1, m1 = Path("01.wv"), Path("01.flac")
    hasher = _hasher_from({d1: None, m1: "master"})  # derived won't decode
    result = verify_derived_files([(d1, m1)], fmt="wavpack", hasher=hasher)
    assert result.ok is False
    assert result.failures == (d1,)
    assert result.mismatches == ()


def test_lossless_undecodable_master_cannot_be_compared() -> None:
    d1, m1 = Path("01.wv"), Path("01.flac")
    # Derived decodes but the master won't — we can't assert a match, so it's a
    # failure-to-verify, NOT a mismatch (we don't claim the derived is wrong).
    hasher = _hasher_from({d1: "aaa", m1: None})
    result = verify_derived_files([(d1, m1)], fmt="wavpack", hasher=hasher)
    assert result.ok is False
    assert result.failures == (d1,) and result.mismatches == ()


def test_lossless_master_hasher_crash_is_a_failure_not_a_mismatch() -> None:
    # The derived decodes fine, but hashing the MASTER blows up → we can't
    # compare, so it's a failure-to-verify (never a claimed mismatch).
    d1, m1 = Path("01.wv"), Path("01.flac")

    def hasher(path: Path) -> str:
        if path == m1:
            raise RuntimeError("master decode blew up")
        return "aaa"

    result = verify_derived_files([(d1, m1)], fmt="wavpack", hasher=hasher)
    assert result.ok is False
    assert result.failures == (d1,) and result.mismatches == ()


# --- Lossy (MP3): decode-clean + complete, never bit-identity ----------------


def test_mp3_decode_clean_is_ok_without_comparing_to_master() -> None:
    d1, m1 = Path("01.mp3"), Path("01.flac")
    # MP3's PCM is (of course) different from the master; we must NOT compare.
    hasher = _hasher_from({d1: "mp3pcm", m1: "flacpcm"})
    result = verify_derived_files([(d1, m1)], fmt="mp3", hasher=hasher)
    assert result.ok is True
    assert result.lossless is False
    assert result.checked == 1
    assert result.mismatches == ()  # lossy never mismatches by design


def test_mp3_undecodable_is_a_failure() -> None:
    d1, m1 = Path("01.mp3"), Path("01.flac")
    hasher = _hasher_from({d1: None, m1: "x"})
    result = verify_derived_files([(d1, m1)], fmt="mp3", hasher=hasher)
    assert result.ok is False and result.failures == (d1,)


# --- Completeness -------------------------------------------------------------


def test_incomplete_transcode_is_not_ok() -> None:
    # 3 masters but only 2 derived files were produced → incomplete.
    d1, m1 = Path("01.mp3"), Path("01.flac")
    d2, m2 = Path("02.mp3"), Path("02.flac")
    hasher = _hasher_from({d1: "a", d2: "b"})
    result = verify_derived_files(
        [(d1, m1), (d2, m2)], fmt="mp3", expected=3, hasher=hasher
    )
    assert result.checked == 2 and result.expected == 3
    assert result.complete is False
    assert result.ok is False  # incomplete, even though each decoded cleanly


def test_no_pairs_returns_error_result() -> None:
    result = verify_derived_files([], fmt="mp3")
    assert result.ran is False
    assert "no mp3 files" in result.error
    assert result.ok is False


# --- Never-raises contract ----------------------------------------------------


def test_verify_never_raises_when_hasher_raises() -> None:
    def boom(path: Path) -> str | None:
        raise RuntimeError("ffmpeg exploded")

    # A crashing hasher must degrade to a failure, never propagate.
    result = verify_derived_files(
        [(Path("01.wav"), Path("01.flac"))], fmt="wav", hasher=boom
    )
    assert isinstance(result, DerivedVerifyResult)
    assert result.ok is False
    assert result.failures == (Path("01.wav"),)


# --- _default_hasher (the real-ffmpeg PCM digest, tested with a fake binary) --


def test_default_hasher_missing_binary_returns_none() -> None:
    # A missing decoder is "couldn't check", not a crash — returns None.
    assert (
        _default_hasher(Path("x.wav"), binary="definitely-no-such-ffmpeg-xyz") is None
    )


def test_default_hasher_hashes_the_decoded_pcm(tmp_path: Path) -> None:
    import hashlib

    # A fake "ffmpeg" that ignores its args and writes fixed bytes to stdout —
    # exercises the Popen + chunked-read + SHA256 path without a real ffmpeg.
    fake = tmp_path / "fake_ffmpeg"
    fake.write_text('#!/bin/sh\nprintf "PCMDATA"\n')
    fake.chmod(0o755)
    got = _default_hasher(tmp_path / "in.wav", binary=str(fake))
    assert got == hashlib.sha256(b"PCMDATA").hexdigest()


def test_default_hasher_nonzero_exit_returns_none(tmp_path: Path) -> None:
    fake = tmp_path / "fail_ffmpeg"
    fake.write_text("#!/bin/sh\nexit 3\n")
    fake.chmod(0o755)
    assert _default_hasher(tmp_path / "in.wav", binary=str(fake)) is None


def test_default_hasher_timeout_returns_none_and_reaps(
    tmp_path: Path, monkeypatch
) -> None:
    # A decode that never finishes must not hang the verify thread — a bounded
    # wait times out and we report "couldn't check" (None). And the killed child
    # must be REAPED (kill + a follow-up wait), not left a zombie.
    import io

    from platterpus.adapters import derived_verify as dv

    class _FakeProc:
        def __init__(self) -> None:
            self.stdout = io.BytesIO(b"")  # EOF immediately, then wait() times out
            self.killed = False
            self.wait_calls = 0

        def wait(self, timeout=None):
            self.wait_calls += 1
            # First (bounded) wait times out; the reaping wait after kill also
            # "times out" in this fake — the code must swallow that.
            raise __import__("subprocess").TimeoutExpired(cmd="ffmpeg", timeout=timeout)

        def kill(self) -> None:
            self.killed = True

    proc = _FakeProc()
    monkeypatch.setattr(dv.subprocess, "Popen", lambda *a, **k: proc)
    assert dv._default_hasher(tmp_path / "x.wav") is None
    assert proc.killed is True  # signalled
    assert proc.wait_calls >= 2  # bounded wait + the reaping wait after kill


def test_default_hasher_read_error_returns_none_and_reaps(
    tmp_path: Path, monkeypatch
) -> None:
    from platterpus.adapters import derived_verify as dv

    class _FakeStdout:
        def read(self, n):
            raise OSError("pipe broke")

        def close(self) -> None:
            pass

    class _FakeProc:
        def __init__(self) -> None:
            self.stdout = _FakeStdout()
            self.killed = False
            self.reaped = False

        def wait(self, timeout=None):
            self.reaped = True
            return 0

        def kill(self) -> None:
            self.killed = True

    proc = _FakeProc()
    monkeypatch.setattr(dv.subprocess, "Popen", lambda *a, **k: proc)
    assert dv._default_hasher(tmp_path / "x.wav") is None
    assert proc.killed is True and proc.reaped is True  # killed AND reaped


@given(
    st.lists(
        st.tuples(
            st.sampled_from(["a", "b", "c", None]),  # derived hash
            st.sampled_from(["a", "b", "c", None]),  # master hash
        ),
        max_size=8,
    ),
    st.sampled_from(["mp3", "wav", "wavpack", "flac", "weird"]),
)
def test_verify_never_raises_property(pairs_data, fmt) -> None:
    """No combination of hash results/format ever makes verify_derived_files
    raise — it always returns a DerivedVerifyResult (never-raises contract)."""
    pairs = [(Path(f"{i}.x"), Path(f"{i}.flac")) for i, _ in enumerate(pairs_data)]
    hashes: dict[Path, str | None] = {}
    for (derived, master), (dh, mh) in zip(pairs, pairs_data, strict=True):
        hashes[derived] = dh
        hashes[master] = mh
    result = verify_derived_files(pairs, fmt=fmt, hasher=_hasher_from(hashes))
    assert isinstance(result, DerivedVerifyResult)
