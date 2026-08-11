"""Finding the two rips of a double test rip, without anyone typing a path.

A double test rip is: rip the disc, rip it again, compare the two. The comparison
already existed (`platterpus --compare A.json B.json`); what did not was a way to
run it that does not involve pasting two long paths, which is the shape
`CLAUDE.md` bans outright — *"never hand back an instruction file"*, and a path
the operator has to type is a path they can mistype.

The failure this guards is specific and quiet: comparing the **wrong pair** still
prints a confident, well-formatted table. Two different albums diffed
track-by-track look exactly like a disc that changed between passes. So the tests
below care much more about what discovery REFUSES than about what it finds.

One of them exists because it caught a defect in its own first draft: the decoy
"different disc" report was built by changing a field (`disc.disc_id`) that
`same_disc` never reads, so it still shared every real identity field and being
paired with it was *correct*. The test was wrong, not the code — the exact
"what does my stand-in do that the real thing does not" trap. `_disc_fields` is
asserted directly now so the decoy cannot silently stop being a decoy.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from platterpus import rip_compare

#: A real report from a real disc, committed. Built by hand it would carry
#: whatever shape I believed it had, which is how the first decoy went wrong.
GOLDEN_REPORT = (
    Path(__file__).resolve().parent.parent
    / "output_reference"
    / "cyanrip_fork_flac"
    / "cyanrip_fork_police_classics.platterpus.json"
)


def _load_golden() -> dict:
    assert GOLDEN_REPORT.is_file(), f"the golden report moved: {GOLDEN_REPORT}"
    data = json.loads(GOLDEN_REPORT.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _write(path: Path, data: dict, *, mtime: float | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return path


def _different_disc(report: dict) -> dict:
    """A report for a genuinely different disc.

    Changes **every** field `_disc_fields` reads. Asserted below rather than
    trusted: the first version of this helper changed a field that does not
    participate in identity at all, which made the decoy a duplicate and the test
    vacuous while it appeared to pass.
    """
    other = json.loads(json.dumps(report))
    other.setdefault("rip", {})["musicbrainz_disc_id"] = "DIFFERENT-DISC-ID-000"
    other.setdefault("rip", {})["cddb_id"] = "FFFFFFFF"
    other.setdefault("disc", {})["musicbrainz_release_id"] = (
        "00000000-0000-0000-0000-000000000000"
    )
    return other


class TestTheDecoyIsReallyADecoy:
    """The floor under every test below. Without it they are all decoration."""

    def test_the_golden_report_carries_identity_fields(self) -> None:
        fields = rip_compare._disc_fields(_load_golden())
        assert fields, "the golden report has no disc identity; nothing can match"

    def test_the_decoy_shares_no_identity_field_with_the_original(self) -> None:
        original = _load_golden()
        decoy = _different_disc(original)
        shared = {
            key
            for key, value in rip_compare._disc_fields(original).items()
            if rip_compare._disc_fields(decoy).get(key) == value
        }
        assert not shared, (
            f"the decoy still shares {sorted(shared)} with the original, so it is "
            "not a different disc and every test using it proves nothing"
        )
        assert rip_compare.same_disc(original, decoy) is False


class TestDiscovery:
    def test_finds_pass1_and_pass2_of_the_same_disc(self, tmp_path: Path) -> None:
        report = _load_golden()
        now = time.time()
        _write(tmp_path / "pass1/Album.platterpus.json", report, mtime=now - 300)
        _write(tmp_path / "pass2/Album.platterpus.json", report, mtime=now)

        pair = rip_compare.discover_pair_to_compare([tmp_path])
        assert pair.found, pair.reason
        assert pair.previous is not None and pair.later is not None
        assert pair.previous.parent.name == "pass1"
        assert pair.later.parent.name == "pass2"

    def test_a_newer_rip_of_a_DIFFERENT_disc_is_not_paired(
        self, tmp_path: Path
    ) -> None:
        """The one that matters. A naive "two most recent reports" rule would
        diff two different albums and print a confident table doing it."""
        report = _load_golden()
        now = time.time()
        _write(tmp_path / "pass1/Album.platterpus.json", report, mtime=now - 300)
        _write(
            tmp_path / "other/Other.platterpus.json",
            _different_disc(report),
            mtime=now,
        )

        pair = rip_compare.discover_pair_to_compare([tmp_path])
        assert not pair.found, f"paired across discs: {pair.reason}"
        assert "same disc" in pair.reason

    def test_a_different_disc_between_the_two_passes_is_skipped(
        self, tmp_path: Path
    ) -> None:
        """A rip of another album in between must not break the pairing."""
        report = _load_golden()
        now = time.time()
        _write(tmp_path / "pass1/Album.platterpus.json", report, mtime=now - 300)
        _write(
            tmp_path / "other/Other.platterpus.json",
            _different_disc(report),
            mtime=now - 200,
        )
        _write(tmp_path / "pass2/Album.platterpus.json", report, mtime=now)

        pair = rip_compare.discover_pair_to_compare([tmp_path])
        assert pair.found, pair.reason
        assert pair.previous is not None and pair.later is not None
        assert pair.previous.parent.name == "pass1"
        assert pair.later.parent.name == "pass2"

    def test_the_label_names_the_FOLDER_not_just_the_filename(
        self, tmp_path: Path
    ) -> None:
        """Two passes of one disc always share a basename, so a message built
        from `.name` reads "Album.json -> Album.json" and identifies neither
        rip. Caught by reading real output, not by reasoning."""
        report = _load_golden()
        now = time.time()
        _write(tmp_path / "pass1/Album.platterpus.json", report, mtime=now - 300)
        _write(tmp_path / "pass2/Album.platterpus.json", report, mtime=now)

        reason = rip_compare.discover_pair_to_compare([tmp_path]).reason
        assert "pass1/" in reason and "pass2/" in reason, reason


class TestRefusalsAreDistinguishable:
    """Four causes of "nothing to compare", and the operator acts differently on
    each. A bare "nothing found" would collapse them into one useless message."""

    def test_no_reports_at_all(self, tmp_path: Path) -> None:
        pair = rip_compare.discover_pair_to_compare([tmp_path])
        assert not pair.found
        assert "no .platterpus.json found" in pair.reason

    def test_no_search_roots(self) -> None:
        pair = rip_compare.discover_pair_to_compare([])
        assert not pair.found
        assert "no rip folders" in pair.reason

    def test_only_one_rip(self, tmp_path: Path) -> None:
        _write(tmp_path / "pass1/Album.platterpus.json", _load_golden())
        pair = rip_compare.discover_pair_to_compare([tmp_path])
        assert not pair.found
        assert "no earlier rip of the same disc" in pair.reason

    def test_newest_rip_has_no_disc_identity(self, tmp_path: Path) -> None:
        """An unknown-disc rip cannot be matched, and guessing "the other newest
        thing" would compare two different albums. Refuse and say why."""
        report = _load_golden()
        now = time.time()
        _write(tmp_path / "pass1/Album.platterpus.json", report, mtime=now - 300)
        anonymous = json.loads(json.dumps(report))
        anonymous.get("rip", {}).pop("musicbrainz_disc_id", None)
        anonymous.get("rip", {}).pop("cddb_id", None)
        anonymous.get("disc", {}).pop("musicbrainz_release_id", None)
        assert not rip_compare._disc_fields(anonymous), "the anonymiser missed a field"
        _write(tmp_path / "pass2/Album.platterpus.json", anonymous, mtime=now)

        pair = rip_compare.discover_pair_to_compare([tmp_path])
        assert not pair.found
        assert "no disc identity" in pair.reason

    def test_an_unreadable_newest_report_is_reported_not_swallowed(
        self, tmp_path: Path
    ) -> None:
        now = time.time()
        _write(tmp_path / "pass1/Album.platterpus.json", _load_golden(), mtime=now - 60)
        torn = tmp_path / "pass2/Album.platterpus.json"
        torn.parent.mkdir(parents=True, exist_ok=True)
        torn.write_text("{ this is not json", encoding="utf-8")
        os.utime(torn, (now, now))

        pair = rip_compare.discover_pair_to_compare([tmp_path])
        assert not pair.found
        assert "could not be read" in pair.reason


class TestNeverRaises:
    """Discovery runs from a best-effort path; a fault must degrade, not crash."""

    @pytest.mark.parametrize(
        "roots",
        [
            [Path("/nonexistent-platterpus-root")],
            [Path("/proc/1/root")],  # typically unreadable without privileges
        ],
    )
    def test_unreadable_roots_degrade(self, roots: list[Path]) -> None:
        pair = rip_compare.discover_pair_to_compare(roots)
        assert isinstance(pair.reason, str) and pair.reason


class TestCliArity:
    """`--compare` takes two paths or NONE. One or three is a mistake, and must
    be refused rather than silently falling through to discovery — a caller who
    named files meant those files."""

    @pytest.mark.parametrize("count", [1, 3])
    def test_wrong_argument_count_is_refused(
        self, count: int, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from platterpus.app import main

        argv = ["--compare", *[str(tmp_path / f"{i}.json") for i in range(count)]]
        assert main(argv) == 2
        out = capsys.readouterr().out
        assert "two report paths or none" in out
        assert f"got {count}" in out, "the message must name the count it saw"

    def test_zero_arguments_discovers_and_reports_its_reason(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from platterpus.app import main

        monkeypatch.setattr(
            rip_compare, "default_report_roots", lambda *a, **k: [tmp_path]
        )
        assert main(["--compare"]) == 1
        assert "nothing to compare:" in capsys.readouterr().out
