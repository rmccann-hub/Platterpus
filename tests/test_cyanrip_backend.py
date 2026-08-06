"""Tests for the cyanrip backend (Phase 1: argv builder + drive scan).

The actual cyanrip execution is hardware-gated; here we test the pure argv
construction and the sysfs-based drive scan with injected paths.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from platterpus.adapters.cyanrip_backend import (
    CyanripImpl,
    _escape_meta_value,
    _metadata_args,
    restore_substituted_colons,
    scheme_from_template,
)
from platterpus.adapters.rip_backend import RipError, RipMetadata, TrackTag

#: Repo root, for loading `scripts/` helpers that are part of the contract
#: surface these tests assert on.
_REPO_ROOT = Path(__file__).resolve().parents[1]


class _FakeMetaflac:
    """Records tag reads/writes for the colon-restore tests."""

    def __init__(self, tags: dict[str, str]) -> None:
        self._tags = tags
        self.writes: list[dict[str, str]] = []

    def read_tags(self, path: Path) -> dict[str, str]:
        return dict(self._tags)

    def write_tags(self, path: Path, tags: dict[str, str]) -> None:
        self.writes.append(dict(tags))


def test_restore_substituted_colons_reverses_the_lookalike() -> None:
    """The ∶ (U+2236) fed to cyanrip is turned back into a real ':' in the tags
    — and only the affected key is rewritten (others left alone)."""
    mf = _FakeMetaflac(
        {"album": "Every Breath You Take∶ The Classics", "artist": "The Police"}
    )
    changed = restore_substituted_colons(mf, [Path("/x/01.flac")])
    assert changed == 1
    assert mf.writes == [{"album": "Every Breath You Take: The Classics"}]


def test_restore_substituted_colons_noop_without_lookalike() -> None:
    """A colon-free album is left completely untouched — no writes at all."""
    mf = _FakeMetaflac({"album": "Synchronicity", "artist": "The Police"})
    changed = restore_substituted_colons(mf, [Path("/x/01.flac"), Path("/x/02.flac")])
    assert changed == 0
    assert mf.writes == []


def _patch_run(monkeypatch, *, stdout: str = "", stderr: str = "", raises=None):
    """Stub the subprocess.run that cyanrip's info/version probes use.

    cyanrip's `_run` delegates to the shared `run_capture` helper in
    `rip_backend`, which itself now runs the child through a `KillableCommand` so
    the GUI can signal it. So the seam is that command's `run`, not
    `subprocess.run` (docs/testing.md §8: move the monkeypatch target to where the
    code now lives — this is the second such move for this helper).
    """
    import platterpus.adapters.rip_backend as mod

    def fake_run(argv, **kwargs):
        if raises is not None:
            raise raises
        return SimpleNamespace(returncode=0, stdout=stdout, stderr=stderr)

    monkeypatch.setattr(mod.INFO_PROBE, "run", fake_run)


def _impl() -> CyanripImpl:
    return CyanripImpl(binary_path="cyanrip")


# --- cache analysis (KDD-29) ----------------------------------------------


def test_supports_cache_analysis_but_not_offset_detection() -> None:
    impl = _impl()
    # cyanrip CAN measure the cache (cd-paranoia -A) but has no trusted offset
    # finder — the two capabilities are independent.
    assert impl.supports_cache_analysis() is True
    assert impl.supports_offset_detection() is False


def test_analyze_drive_delegates_to_cache_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from platterpus.adapters import cache_probe

    captured: list[str] = []

    def fake_probe(device: str, **kw):  # type: ignore[no-untyped-def]
        captured.append(device)
        return cache_probe.CacheProbeResult(defeat=True, cache_sectors=1024)

    monkeypatch.setattr(cache_probe, "probe_cache_defeat", fake_probe)
    assert _impl().analyze_drive("/dev/sr0") is True
    assert captured == ["/dev/sr0"]  # device forwarded to the probe


def test_analyze_drive_returns_none_when_probe_inconclusive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from platterpus.adapters import cache_probe

    monkeypatch.setattr(
        cache_probe,
        "probe_cache_defeat",
        lambda device, **kw: cache_probe.CacheProbeResult(defeat=None),
    )
    # Honest: an inconclusive probe yields None (rendered "(unknown)"), never a
    # fabricated verdict.
    assert _impl().analyze_drive("/dev/sr0") is None


# --- rip argv builder -----------------------------------------------------


def test_rip_argv_known_disc_with_offset() -> None:
    argv = _impl()._build_rip_argv(
        "/dev/sr0",
        unknown=False,
        cover_art="embed",
        max_retries=5,
        read_offset_override=667,
    )
    assert argv[0] == "cyanrip"
    assert "-d" in argv and argv[argv.index("-d") + 1] == "/dev/sr0"
    # cyanrip applies the offset itself via -s (no whipper >587 bug).
    assert "-s" in argv and argv[argv.index("-s") + 1] == "667"
    assert "-o" in argv and argv[argv.index("-o") + 1] == "flac"
    assert "-r" in argv and argv[argv.index("-r") + 1] == "5"
    # MusicBrainz is ALWAYS off — the GUI feeds tags via -a/-t instead
    # (KDD-18 metadata model; keeps the rip offline + deterministic).
    assert "-N" in argv
    assert "-G" not in argv  # cover art wanted → keep embedding on


def test_rip_argv_unknown_disc_disables_musicbrainz() -> None:
    argv = _impl()._build_rip_argv(
        "/dev/sr0",
        unknown=True,
        cover_art="",
        max_retries=5,
        read_offset_override=667,
    )
    assert "-N" in argv  # unknown → disable MusicBrainz (no network needed)
    assert "-G" in argv  # no cover art → disable embedding


def test_rip_argv_omits_offset_when_none() -> None:
    argv = _impl()._build_rip_argv(
        "/dev/sr0",
        unknown=False,
        cover_art="embed",
        max_retries=5,
        read_offset_override=None,
    )
    assert "-s" not in argv


def test_rip_argv_omits_secure_rerip_when_zero() -> None:
    # 0 = off: a clean disc gets no -Z, so the rip doesn't waste time
    # re-reading good tracks. This is the default.
    argv = _impl()._build_rip_argv(
        "/dev/sr0",
        unknown=False,
        cover_art="embed",
        max_retries=5,
        read_offset_override=667,
        secure_rerip_matches=0,
    )
    assert "-Z" not in argv


def test_rip_argv_passes_secure_rerip_when_set() -> None:
    # > 0 → cyanrip's -Z N (re-rip until N reads' checksums agree), for
    # marginal/damaged discs (EAC-parity item 1).
    argv = _impl()._build_rip_argv(
        "/dev/sr0",
        unknown=False,
        cover_art="embed",
        max_retries=5,
        read_offset_override=667,
        secure_rerip_matches=2,
    )
    assert "-Z" in argv and argv[argv.index("-Z") + 1] == "2"


def test_rip_argv_omits_read_speed_when_zero() -> None:
    # 0 (drive max / the ladder's first rung) → no -S; the drive picks.
    argv = _impl()._build_rip_argv(
        "/dev/sr0",
        unknown=False,
        cover_art="embed",
        max_retries=5,
        read_offset_override=667,
        read_speed=0,
    )
    assert "-S" not in argv


def test_rip_argv_passes_read_speed_when_set() -> None:
    # A positive speed → cyanrip's -S N (cap the drive read speed for this pass).
    argv = _impl()._build_rip_argv(
        "/dev/sr0",
        unknown=False,
        cover_art="embed",
        max_retries=5,
        read_offset_override=667,
        read_speed=8,
    )
    assert "-S" in argv and argv[argv.index("-S") + 1] == "8"


def test_rip_argv_omits_track_selection_by_default() -> None:
    # A whole-disc rip passes no -l; cyanrip rips everything.
    argv = _impl()._build_rip_argv(
        "/dev/sr0",
        unknown=False,
        cover_art="embed",
        max_retries=5,
        read_offset_override=667,
    )
    assert "-l" not in argv


def test_rip_argv_passes_track_subset_for_auto_fix() -> None:
    # The per-track auto-fix re-rip selects only the unstable tracks via -l.
    argv = _impl()._build_rip_argv(
        "/dev/sr0",
        unknown=False,
        cover_art="embed",
        max_retries=5,
        read_offset_override=667,
        only_tracks=(3, 5),
    )
    assert "-l" in argv and argv[argv.index("-l") + 1] == "3,5"


def test_rip_argv_always_disables_mb_and_feeds_gui_metadata() -> None:
    """KDD-18 metadata model: cyanrip never does its own MB lookup — the
    GUI's tags (release pick + user edits) are fed via -a/-t, offline."""
    meta = RipMetadata(
        album_artist="The Police",
        album_title="Greatest Hits",
        year="1992",
        genre="Rock",
        disc_number=1,
        total_discs=2,  # multi-disc → cyanrip gets `-c 1/2`
        tracks=(
            TrackTag(1, "Roxanne", "The Police", isrc="GBAAA0000001"),
            TrackTag(2, "Can't Stand Losing You"),
        ),
    )
    argv = _impl()._build_rip_argv(
        "/dev/sr0",
        unknown=False,
        cover_art="embed",
        max_retries=5,
        read_offset_override=667,
        release_id="1e477f68-c407-4eae-ad01-518528cedc2c",
        track_template="%A/%d/%t - %n",
        metadata=meta,
    )
    assert "-N" in argv  # even for a known disc
    album_arg = argv[argv.index("-a") + 1]
    assert "album=Greatest Hits" in album_arg
    assert "album_artist=The Police" in album_arg
    assert "date=1992" in album_arg
    assert "genre=Rock" in album_arg
    # The disc position is NOT an -a tag: it goes through cyanrip's own
    # `-c disc/totaldiscs`, which sets `disc` and `totaldiscs` as separate
    # integer keys. Folded into -a as "disc=1/2" it wrote the single Vorbis tag
    # DISCNUMBER=1/2 — the ID3 convention, not the Vorbis one — and dropped
    # totaldiscs entirely. See _disc_args.
    assert "disc=" not in album_arg
    assert argv[argv.index("-c") + 1] == "1/2"
    assert "musicbrainz_albumid=1e477f68-c407-4eae-ad01-518528cedc2c" in album_arg
    track_args = [argv[i + 1] for i, a in enumerate(argv) if a == "-t"]
    assert track_args[0] == "1=title=Roxanne:artist=The Police:isrc=GBAAA0000001"
    # No artist/isrc → those pairs are skipped; the ' is escaped for
    # av_get_token (which treats bare ' as a quote character).
    assert track_args[1] == "2=title=Can\\'t Stand Losing You"
    # Templates: dir part → -D, file part → -F, tokens translated.
    assert argv[argv.index("-D") + 1] == "{album_artist}/{album}"
    assert argv[argv.index("-F") + 1] == "{track} - {title}"


def test_rip_argv_no_metadata_omits_tag_flags() -> None:
    argv = _impl()._build_rip_argv(
        "/dev/sr0",
        unknown=True,
        cover_art="",
        max_retries=5,
        read_offset_override=None,
        release_id="",
        track_template="",
        metadata=None,
    )
    assert "-N" in argv
    assert "-a" not in argv and "-t" not in argv
    assert "-D" not in argv and "-F" not in argv


# --- metadata escaping (cyanrip parses -a/-t with av_dict_parse_string) ----


def test_meta_value_escaping_makes_separators_safe() -> None:
    r"""A colon is backslash-escaped now, NOT substituted (round 7 lap 31).

    **This assertion was the opposite way round until 2026-08-06, and the old
    version was correct when it was written** — which is why the reason is here
    rather than in a commit message. cyanrip's `append_missing_keys()` runs before
    `av_dict_parse_string()` and used to split on ':' naively, ignoring '\', so a
    backslash-escaped colon did not survive it: a real user's album became the
    folder "Every Breath You Take∶album_artist= The Classics" (2026-06-27). We
    substituted U+2236 RATIO instead.

    **Their code changed, and we verified that rather than taking the claim.** The
    fork told us in lap 30 that `\:` works. Our own docstring said otherwise, so
    we read both trees: `append_missing_keys` is now escape-aware ("minding
    \: and \= escapes"), and it is escape-aware **on upstream `master` too** —
    so this is safe on stock as well as the fork, which is what allowed the change
    to be unconditional instead of gated on a build tag.

    What it buys: cyanrip's `.cue` TITLE and its log's `album:` field carried the
    substitute and were the two artifacts we could never repair. Now the real
    colon goes in and comes back out. The folder name is unchanged — cyanrip
    still sanitises ':' out of paths itself, which is where U+2236 came from.
    """
    assert _escape_meta_value("Live: At The Met") == "Live\\: At The Met"
    assert "∶" not in _escape_meta_value("Every Breath You Take: The Classics")
    # Every colon is escaped, and none is replaced.
    assert _escape_meta_value("a:b:c") == "a\\:b\\:c"
    # The other tokenizer-special chars are unchanged in treatment.
    assert _escape_meta_value("a=b") == "a\\=b"
    assert _escape_meta_value("back\\slash") == "back\\\\slash"
    assert _escape_meta_value("It's") == "It\\'s"
    assert _escape_meta_value("plain") == "plain"


def test_metadata_args_skip_empty_fields() -> None:
    # Single disc + no genre → only the album title; no disc=/genre= noise.
    args = _metadata_args(RipMetadata(album_title="X"), release_id="")
    assert args == ["-a", "album=X"]
    assert _metadata_args(None, release_id="") == []
    # A track with no title/artist/isrc contributes no -t at all.
    args = _metadata_args(RipMetadata(tracks=(TrackTag(3),)), release_id="")
    assert args == []


def test_metadata_args_include_catalog_barcode_and_label() -> None:
    # Release identifiers ride the -a album tag list as Picard-style Vorbis keys.
    args = _metadata_args(
        RipMetadata(
            catalog_number="SHVL 804", barcode="5099902987682", label="Harvest"
        ),
        release_id="",
    )
    album_arg = args[args.index("-a") + 1]
    assert "catalognumber=SHVL 804" in album_arg
    assert "barcode=5099902987682" in album_arg
    assert "label=Harvest" in album_arg
    # Absent identifiers add nothing.
    empty = _metadata_args(RipMetadata(album_title="X"), release_id="")
    assert "catalognumber" not in empty[1]
    assert "barcode" not in empty[1]
    assert "label" not in empty[1]


# --- whipper template → cyanrip scheme --------------------------------------


def test_scheme_translates_default_known_template() -> None:
    assert (
        scheme_from_template("%t - %n - %d - %A - %y")
        == "{track} - {title} - {album} - {album_artist} - {date}"
    )


def test_scheme_keeps_literals_and_unknown_tokens() -> None:
    # The unknown-disc template is all literals + %t; literals pass through.
    assert (
        scheme_from_template("Unknown Artist/Unknown Album/%t - Track %t")
        == "Unknown Artist/Unknown Album/{track} - Track {track}"
    )
    # An unmapped token stays visible rather than vanishing.
    assert scheme_from_template("%X - %n") == "%X - {title}"
    # A trailing lone % can't form a token; kept as-is.
    assert scheme_from_template("100%") == "100%"


def test_scheme_neutralizes_literal_braces() -> None:
    # {…} is cyanrip's substitution syntax — stray braces in a user template
    # must not be parsed as (missing) tag keys.
    assert scheme_from_template("{weird} %n") == "(weird) {title}"


def test_scheme_expands_year_only_token_to_literal() -> None:
    # %Y has no cyanrip equivalent, so it's substituted with the literal year
    # here (cyanrip only ever sees "1995", never "%Y").
    assert scheme_from_template("%d (%Y)", year="1995") == "{album} (1995)"
    # Empty year → the token drops out (dateless disc).
    assert scheme_from_template("%d (%Y)", year="") == "{album} ()"
    # A %%Y escape is a literal percent + "Y": "%%" collapses to a single "%"
    # (matching naming.render_preview and whipper semantics) and the year is NOT
    # spliced in mid-escape (why we scan rather than str.replace). Previously this
    # returned "%%Y" — two percents — so the real filename disagreed with the
    # preview, which shows "%Y".
    assert scheme_from_template("%%Y", year="1995") == "%Y"


def test_scheme_collapses_escaped_percent() -> None:
    # "%%" is whipper's escape for a literal percent; it must become a single "%"
    # (cyanrip treats "%" as an ordinary character), so the filename matches what
    # naming.render_preview shows the user. A "%%" before a token letter is a
    # literal percent + that letter, NOT the token: "%%A" is "%A", not the album
    # artist.
    assert scheme_from_template("%%") == "%"
    assert scheme_from_template("100%%") == "100%"
    assert scheme_from_template("%%A") == "%A"
    assert scheme_from_template("%%n - %n") == "%n - {title}"


def test_rip_argv_preexpands_year_only_token_from_release_date() -> None:
    # A %Y in the template is expanded to the 4-char year taken from the fetched
    # release date, BEFORE the template is handed to cyanrip (which has no
    # year-only token). Here the date is a full "YYYY-MM-DD".
    meta = RipMetadata(
        album_artist="Nirvana", album_title="Nevermind", year="1991-09-24"
    )
    argv = _impl()._build_rip_argv(
        "/dev/sr0",
        unknown=False,
        cover_art="embed",
        max_retries=5,
        read_offset_override=None,
        track_template="%A/%d (%Y)/%t - %n",
        metadata=meta,
    )
    assert argv[argv.index("-D") + 1] == "{album_artist}/{album} (1991)"
    assert "%Y" not in " ".join(argv)


def test_rip_argv_year_only_token_empty_without_metadata() -> None:
    # No metadata / no year → %Y vanishes (same as cyanrip's own {date} on a
    # dateless disc); it must never leak the literal "%Y" into the folder name.
    argv = _impl()._build_rip_argv(
        "/dev/sr0",
        unknown=True,
        cover_art="",
        max_retries=5,
        read_offset_override=None,
        track_template="%A/%d (%Y)/%t - %n",
        metadata=None,
    )
    assert argv[argv.index("-D") + 1] == "{album_artist}/{album} ()"
    assert "%Y" not in " ".join(argv)


# --- drive scan -----------------------------------------------------------


def test_list_drives_scans_dev_and_sysfs(tmp_path: Path) -> None:
    dev = tmp_path / "dev"
    dev.mkdir()
    (dev / "sr0").write_bytes(b"")
    (dev / "sda").write_bytes(b"")  # not optical — must be ignored
    sysblk = tmp_path / "sys-block"
    info = sysblk / "sr0" / "device"
    info.mkdir(parents=True)
    (info / "vendor").write_text("PIONEER\n")
    (info / "model").write_text("BD-RW   BDR-209D\n")
    (info / "rev").write_text("1.51\n")

    impl = CyanripImpl(dev_root=dev, sys_block=sysblk)
    drives = impl.list_drives()

    assert len(drives) == 1
    d = drives[0]
    assert d.device == str(dev / "sr0")
    assert d.vendor == "PIONEER"
    assert d.model == "BD-RW   BDR-209D"
    assert d.release == "1.51"


def test_list_drives_empty_when_no_optical(tmp_path: Path) -> None:
    dev = tmp_path / "dev"
    dev.mkdir()
    impl = CyanripImpl(dev_root=dev, sys_block=tmp_path / "sys")
    assert impl.list_drives() == []


def test_list_drives_tolerates_missing_sysfs(tmp_path: Path) -> None:
    dev = tmp_path / "dev"
    dev.mkdir()
    (dev / "sr0").write_bytes(b"")
    impl = CyanripImpl(dev_root=dev, sys_block=tmp_path / "nope")
    drives = impl.list_drives()
    assert len(drives) == 1
    assert drives[0].vendor == ""  # sysfs absent → blank, no crash


def test_list_drives_degrades_on_oserror(monkeypatch: pytest.MonkeyPatch) -> None:
    """Scanning /dev can raise OSError (e.g. a permission/IO error); the scan
    must degrade to an empty list, never propagate."""
    impl = CyanripImpl(dev_root=Path("/dev"))

    def boom(self: Path, pattern: str):
        raise OSError("I/O error")

    monkeypatch.setattr(type(impl._dev_root), "glob", boom)
    assert impl.list_drives() == []


# --- disc_info (runs `cyanrip -I -N` and parses the report) ---------------


def test_disc_info_runs_info_only_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """disc_info must use info-only mode (-I) with MusicBrainz disabled (-N)
    — identification is local; the GUI does its own MB lookup — and pass the
    selected device."""
    # cyanrip's `_run` delegates to the shared run_capture in whipper_backend,
    # so the subprocess.run patch targets that module (see _patch_run).
    import platterpus.adapters.rip_backend as mod

    seen: list[list[str]] = []

    def fake_run(argv, **kwargs):
        seen.append(argv)
        return SimpleNamespace(
            returncode=0,
            stdout=(
                "Disc tracks:    16\n"
                "DiscID:         xA2hjkk0Jl0gKKtIdYuTje4JTXY-\n"
                "CDDB ID:        c50a780f\n"
            ),
            stderr="",
        )

    monkeypatch.setattr(mod.INFO_PROBE, "run", fake_run)
    info = _impl().disc_info("/dev/sr0")

    argv = seen[0]
    assert "-I" in argv and "-N" in argv
    assert argv[argv.index("-d") + 1] == "/dev/sr0"
    assert info.musicbrainz_disc_id == "xA2hjkk0Jl0gKKtIdYuTje4JTXY-"
    assert info.cddb_disc_id == "c50a780f"
    assert info.num_tracks == 16


def test_disc_info_error_output_degrades_to_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from platterpus.parsers.cd_info import DiscInfo

    _patch_run(monkeypatch, stdout="Unable to read disc TOC!\n")
    assert _impl().disc_info("/dev/sr0") == DiscInfo()


def test_disc_info_raises_when_binary_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_run(monkeypatch, raises=FileNotFoundError("cyanrip"))
    with pytest.raises(RipError, match="not found"):
        _impl().disc_info("/dev/sr0")


# --- version / find_offset (subprocess stubbed) ---------------------------


def test_version_returns_output(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_run(monkeypatch, stdout="cyanrip 0.9.3.1\n")
    assert _impl().version() == "cyanrip 0.9.3.1"


def test_does_not_self_verify_encode() -> None:
    # cyanrip (FFmpeg) has no decode-verify pass, so the GUI runs a post-rip
    # check; it inherits the ABC default.
    assert _impl().self_verifies_encode() is False


def test_produces_max_compression_flac_true() -> None:
    # cyanrip drives libavcodec at the maximum FLAC compression already, so a
    # post-rip `flac -8` re-compress would gain nothing — the GUI skips it.
    assert _impl().produces_max_compression_flac() is True


def test_native_output_formats_includes_wav_and_mp3() -> None:
    # cyanrip CAN emit these natively via `-o`. This stays a reserved capability
    # seam (KDD-22) — the shipped feature transcodes from FLAC for both backends.
    fmts = _impl().native_output_formats()
    assert {"flac", "wav", "mp3", "wavpack"} <= fmts


def test_find_offset_is_not_implemented() -> None:
    """Regression: cyanrip has NO AccurateRip offset finder (its ``-f`` is
    force-overread, not a detector). The old override ran ``cyanrip -f`` and
    scraped "offset…N" from the help/default echo, returning a meaningless 0
    that overrode the correct AccurateRip-list value on real hardware. cyanrip
    must inherit the base ``NotImplementedError`` so the wizard falls back to the
    drive-model list + manual entry, never a fabricated number.
    """
    with pytest.raises(NotImplementedError):
        _impl().find_offset("/dev/sr0")


def test_run_raises_when_binary_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_run(monkeypatch, raises=FileNotFoundError("cyanrip"))
    with pytest.raises(RipError, match="not found"):
        _impl().version()


def test_rip_argv_omits_overread_by_default() -> None:
    # Off is the default — matches EAC's baseline "overread: No", which is
    # exactly how the committed 12/14 parity proof matched.
    argv = _impl()._build_rip_argv(
        "/dev/sr0",
        unknown=False,
        cover_art="embed",
        max_retries=5,
        read_offset_override=667,
    )
    assert "-O" not in argv


def test_rip_argv_passes_overread_when_enabled() -> None:
    # Regression for the flag-letter trap (2026-07-21): the docs used to say
    # cyanrip's overread flag is -x, but -x does not exist in cyanrip's getopt
    # (verified against 0.9.3.1 + master) — the real flag is -O. Pin the
    # correct letter so the mix-up can't come back.
    argv = _impl()._build_rip_argv(
        "/dev/sr0",
        unknown=False,
        cover_art="embed",
        max_retries=5,
        read_offset_override=667,
        force_overread=True,
    )
    assert "-O" in argv
    assert "-x" not in argv


def test_cancel_setup_is_overridden_not_inherited_as_a_no_op() -> None:
    """Regression: this backend inherited the ABC's no-op `cancel_setup`.

    `RipBackend.cancel_setup` is a deliberately *concrete* no-op, which is right for
    a backend with nothing to cancel — and a trap for one that spins the disc. This
    backend runs `cd-paranoia -A` with a 600 s ceiling and never overrode it, so
    `DriveSetupWorker.cancel()` reduced to setting a flag that `run()` only reads
    *between* steps. Closing the drive-setup dialog therefore left the drive
    reading, and the physical eject button is ignored while a read holds the device.

    Asserting the method is *overridden* (not merely present) is the whole point: it
    is present either way, so `hasattr` would pass against the bug.
    """
    from platterpus.adapters.rip_backend import RipBackend

    assert (
        CyanripImpl.cancel_setup is not RipBackend.cancel_setup  # type: ignore[comparison-overlap]
    ), (
        "CyanripImpl inherits RipBackend.cancel_setup, which does nothing. This "
        "backend starts a 600 s disc-spinning cd-paranoia probe, so cancellation "
        "must be implemented — override it (delegating to "
        "cache_probe.cancel_active_probe) or the dialog's cancel is a lie."
    )


def test_cancel_setup_reaches_the_cache_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    """And the override is wired to the thing that is actually running."""
    from platterpus.adapters import cache_probe

    calls: list[int] = []
    monkeypatch.setattr(cache_probe, "cancel_active_probe", lambda: calls.append(1))

    CyanripImpl(binary_path="/nonexistent/cyanrip").cancel_setup()

    assert calls == [1], (
        "cancel_setup() did not call cache_probe.cancel_active_probe(), so the "
        "running cd-paranoia is never signalled."
    )


# --- Failure diagnosability (audit, 2026-07-29) ------------------------------


def test_a_failed_disc_probe_raises_instead_of_looking_like_an_unknown_disc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression: the single worst diagnostic hole in the app.

    `_run` discarded the exit code, so a non-zero `cyanrip -I` — permission denied
    on the device, a dead `ripping` container, a broken host export — produced an
    EMPTY `DiscInfo`. That is indistinguishable from a real disc MusicBrainz has
    never seen, so the GUI announced "not in MusicBrainz" and offered an
    unknown-album rip, while the log contained nothing at all. The user is told the
    wrong thing about the wrong subsystem and their bug report has no evidence.
    """
    from types import SimpleNamespace

    import platterpus.adapters.rip_backend as mod

    monkeypatch.setattr(
        mod.INFO_PROBE,
        "run",
        lambda *a, **k: SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="cyanrip: unable to open device: Permission denied\n",
        ),
    )

    with pytest.raises(RipError) as info:
        _impl().disc_info("/dev/sr0")

    # The user-facing message carries cyanrip's OWN words, not a generic failure.
    assert "Permission denied" in str(info.value), (
        f"the error dropped the tool's explanation: {info.value!r}. A message that "
        "does not say what the tool said is barely better than swallowing it."
    )


def test_version_raises_on_a_nonzero_exit_instead_of_returning_a_string(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression: the `--doctor` false-PASS on its most important check.

    `version()` used to run `-V` non-strict, so a broken host export (dead
    container, missing podman, unexported binary) came back as an ordinary
    *string* — and `preflight.check_backend_routing` treats a returned string as
    proof the host→Distrobox→cyanrip chain works, printing that string as "the
    version". `--doctor` then exited 0 on an environment that cannot rip. The exit
    code is visible only in here, so the conversion to an error belongs in here.
    """
    from types import SimpleNamespace

    import platterpus.adapters.rip_backend as mod

    monkeypatch.setattr(
        mod.INFO_PROBE,
        "run",
        lambda *a, **k: SimpleNamespace(
            returncode=127,
            stdout="",
            stderr="Error: cannot connect to Podman socket\n",
        ),
    )

    with pytest.raises(RipError) as info:
        _impl().version()

    # The doctor surfaces this message verbatim, so it must carry cyanrip's words.
    assert "exit 127" in str(info.value)
    assert "Podman" in str(info.value)


def test_a_failed_probe_logs_the_tools_own_output(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """The other half: it must land in the LOG, which is what a bug report carries.

    Uses the version probe, which now also *raises* (see the test above) — the
    logging must happen regardless of what the caller does with the failure, since
    swallowing quietly is the behaviour being fixed.
    """
    from types import SimpleNamespace

    import platterpus.adapters.rip_backend as mod

    monkeypatch.setattr(
        mod.INFO_PROBE,
        "run",
        lambda *a, **k: SimpleNamespace(
            returncode=127, stdout="", stderr="cannot connect to Podman\n"
        ),
    )

    with caplog.at_level("WARNING"), pytest.raises(RipError):
        _impl().version()

    messages = " ".join(r.getMessage() for r in caplog.records)
    assert "cannot connect to Podman" in messages, (
        "a non-zero cyanrip exit left nothing in the log. The convention is to "
        f"capture a dependency's output and log it. Records were: {messages!r}"
    )
    assert "exited 127" in messages


# --- Metadata that becomes a path segment (audit, 2026-07-31) ----------------
#
# cyanrip substitutes the album artist / album title / track title / track artist
# into the naming schemes we hand it as `-D`/`-F`, so each becomes one folder or
# file name. It maps the path-ILLEGAL characters inside a value ("/" → "∕",
# ":" → "∶", docs/dependency-contracts.md) but nothing maps "." and "..", the two
# segments POSIX reserves for *this* and *the parent* directory — so an album
# titled ".." made `-D` resolve ABOVE the output directory and the rip landed
# outside the folder the user chose. Identical to the `%Y` escape fixed on
# 2026-07-28, which was only ever closed for the one token Platterpus substitutes
# itself. `main_window_helpers.safe_path_segment` refuses ".."/"." for the
# unknown-album path; the ordinary known-disc path had no such guard.


@pytest.mark.parametrize(
    "meta",
    [
        RipMetadata(album_artist="..", album_title="Album"),
        RipMetadata(album_artist="Artist", album_title=".."),
        RipMetadata(album_artist="Artist", album_title="."),
        RipMetadata(album_artist="Artist", album_title=" .. "),
        RipMetadata(album_title="Album", tracks=(TrackTag(1, ".."),)),
        RipMetadata(album_title="Album", tracks=(TrackTag(1, "T", ".."),)),
    ],
)
def test_path_reference_metadata_refuses_to_build_argv(meta: RipMetadata) -> None:
    """The rip fails LOUDLY rather than writing outside the output directory —
    matching the documented contract that an unusable name is never silent."""
    with pytest.raises(RipError) as excinfo:
        _metadata_args(meta, release_id="")
    assert "outside your output directory" in str(excinfo.value)


def test_path_reference_metadata_is_refused_by_the_full_argv_builder() -> None:
    """The guard has to sit on the real rip path, not just the helper — a check
    that only the helper's own test reaches is not protecting the rip."""
    with pytest.raises(RipError):
        _impl()._build_rip_argv(
            "/dev/sr0",
            unknown=False,
            cover_art="embed",
            max_retries=5,
            read_offset_override=None,
            track_template="%A/%d/%t - %n",
            metadata=RipMetadata(album_artist="A", album_title=".."),
        )


def test_a_nul_in_metadata_is_refused_before_subprocess_sees_it() -> None:
    """`subprocess` raises ValueError on an embedded NUL, which would surface as
    a crash mid-rip instead of a message. Refuse it at the boundary."""
    with pytest.raises(RipError) as excinfo:
        _metadata_args(RipMetadata(album_title="Ab\x00cd"), release_id="")
    assert "illegal character" in str(excinfo.value)


@pytest.mark.parametrize(
    "title",
    ["...", "..and Justice for All", "Vol. 2.", ".hidden", "Every Breath You Take"],
)
def test_ordinary_titles_still_build_argv(title: str) -> None:
    """The guard must not become a general-purpose sanitiser — cyanrip owns
    naming (Critical rule #3), and these are all ordinary Linux directory names."""
    args = _metadata_args(RipMetadata(album_title=title), release_id="")
    assert any(title in a for a in args)


# --- The disc position: `-c`, not an `-a disc=` tag ---------------------------
#
# Found by comparing our FLAC tags against an EAC baseline on real hardware
# (2026-08-02). We folded the disc position into the album tag string as
# `disc=2/3`; cyanrip passes an `-a` value through verbatim and ffmpeg's
# Vorbis-comment writer maps the key `disc` to `DISCNUMBER`, so the file carried
# the single tag `DISCNUMBER=2/3` — the ID3 convention, not the Vorbis one — and
# `totaldiscs` was lost outright.
#
# cyanrip already has the right seam: `-c disc/totaldiscs` parses the slash and
# sets two separate integer keys (`cyanrip_main.c`:
# `av_dict_set_int(&ctx->meta, "disc", discnumber, 0)` / `… "totaldiscs" …`).


def _argv_with(**meta_kw: object) -> list[str]:
    return _impl()._build_rip_argv(
        "/dev/sr0",
        unknown=False,
        cover_art="",
        max_retries=5,
        read_offset_override=None,
        track_template="%d/%t - %n",
        metadata=RipMetadata(album_title="X", **meta_kw),  # type: ignore[arg-type]
    )


def test_a_multi_disc_release_passes_the_disc_position_via_c() -> None:
    argv = _argv_with(disc_number=2, total_discs=3)
    assert argv[argv.index("-c") + 1] == "2/3"
    # ...and NOT as a tag, which is what produced DISCNUMBER=2/3.
    assert "disc=" not in argv[argv.index("-a") + 1]


def test_a_single_disc_release_still_gets_a_disc_number() -> None:
    """EAC and Picard both write DISCNUMBER/TOTALDISCS on a one-disc album, so a
    library tagged by Platterpus should not have the field appear only on box
    sets. cyanrip's name schemes are guarded on `totaldiscs > 1`, so this changes
    no filenames."""
    assert (
        _argv_with(disc_number=1, total_discs=1)[
            _argv_with(disc_number=1, total_discs=1).index("-c") + 1
        ]
        == "1/1"
    )


@pytest.mark.parametrize(
    ("number", "total"),
    [
        (0, 1),  # cyanrip: "Invalid discnumber 0" → return 1
        (-1, 2),
        (1, 0),  # cyanrip: "Invalid totaldiscs 0" → return 1
        (3, 2),  # cyanrip: "discnumber 3 is larger than totaldiscs 2" → return 1
        (1, -5),
    ],
)
def test_an_out_of_range_disc_position_is_dropped_not_passed(
    number: int, total: int
) -> None:
    """cyanrip REFUSES THE WHOLE RIP on a bad `-c`, before reading a sector —
    the same defect shape as the `-t 17=` on a 16-track disc that killed a real
    rip in two seconds. These numbers come from a metadata service, i.e. from
    something other than the disc in the drive, which is exactly the category
    CLAUDE.md requires be range-checked at the argv chokepoint.

    Losing a disc tag is survivable. Losing the rip is not.
    """
    argv = _argv_with(disc_number=number, total_discs=total)
    assert "-c" not in argv


def test_a_dropped_disc_position_is_logged_so_it_is_diagnosable(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Silently dropping it would leave a mysteriously untagged rip with nothing
    in the log to explain why."""
    import logging

    with caplog.at_level(logging.WARNING):
        _argv_with(disc_number=5, total_discs=2)
    assert any("-c" in r.message for r in caplog.records)


# --- --consumer reaches the ripper (round 7 lap 23) ------------------------


def test_rip_actually_sends_consumer_to_a_build_that_accepts_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """**REGRESSION. `--consumer` was never sent, on any build, ever.**

    `_build_rip_argv` gates the flag on `consumer_tag_for_build(ripper_build_tag)`, and
    that parameter defaults to `""` so an unknown build gets no capability-gated flags.
    Its own comment said defaulting to empty *"is what makes the safe behaviour the
    default rather than something a caller must remember"* — and **no caller remembered.**
    The safe default became the only behaviour, so a fully-built and fully-tested
    capability (`accepts_consumer_flag`, the build allowlist,
    `assert_consumer_tag_is_sane`) hung off a value nothing supplied.

    **Why no existing test caught it:** every one of them called `_build_rip_argv`
    *directly* and passed a tag, so they measured the gate and never the wiring. That is
    the `RipHandle.cancel` shape from CLAUDE.md rule 9 — a working mechanism reachable
    from nowhere — and the reason this test drives the real `rip()` entry point instead.
    Found in a rig artifact: every log said `Consumer: not identified (no --consumer
    given)`.

    Asserted in **both** directions below, because "the flag appears" alone would also
    pass if we sent it unconditionally, which is the failure the gate exists to prevent.
    """
    from platterpus.adapters import cyanrip_backend as mod

    captured: list[list[str]] = []

    class _FakeProc:
        args: list[str] = []
        stdout = None
        stderr = None
        returncode = 0

        def poll(self) -> int:
            return 0

        def wait(self, timeout: float | None = None) -> int:
            return 0

    def fake_popen(argv, *a, **kw):  # type: ignore[no-untyped-def]
        captured.append(list(argv))
        proc = _FakeProc()
        proc.args = list(argv)
        return proc

    monkeypatch.setattr(mod.subprocess, "Popen", fake_popen)

    def _rip_once(banner: str) -> list[str]:
        captured.clear()
        impl = _impl()
        monkeypatch.setattr(impl, "version", lambda: banner)
        impl.rip(
            drive="/dev/sr0",
            release_id="",
            output_dir=tmp_path,
            track_template="{track} - {title}",
            disc_template="",
        )
        assert captured, "rip() did not spawn anything"
        return captured[-1]

    # 1. A build whose published flag table lists --consumer: the flag is SENT.
    supported = _rip_once(
        "cyanrip 0.9.4-rc1+platterpus.5-beta.2 (platterpus-fork-gc5fb909)"
    )
    assert "--consumer" in supported, (
        "rip() did not send --consumer to a build that accepts it — the "
        "ripper_build_tag wiring is gone again, and every rip will log "
        f"'Consumer: not identified'. argv: {supported}"
    )
    assert supported[supported.index("--consumer") + 1] == mod.consumer_tag()

    # 2. An unknown build: the flag is WITHHELD. Without this the test would pass
    #    against a version that sends --consumer unconditionally, which would abort
    #    every rip on a build that does not know the flag (the -V failure, inverted).
    unknown = _rip_once("cyanrip 0.9.3")
    assert "--consumer" not in unknown, (
        f"--consumer was sent to an unrecognised build: {unknown}"
    )


# --------------------------------------------------------------------------
# RANGE at the argv chokepoint, not only at the Settings boundary.
#
# Found 2026-08-06 by `scripts/probe_argv_surface.py` — the black-box self-probe
# `docs/seam-rules.md` S-9 asks each side to run against its OWN surface. It
# measured six out-of-range values reaching the argv, every one of them outside
# the range the Settings dialog enforces, and every one reachable because the
# range was checked at the Settings boundary and NOWHERE ELSE. A hand-edited
# `config.toml` skips Settings entirely.
#
# CLAUDE.md states it directly: range "must be enforced by code at the argv
# chokepoint — not merely stated here", and "a GUI widget's own constraint (a
# QSpinBox range) is a *convenience*, not the validation".
# --------------------------------------------------------------------------


def test_the_chokepoint_refuses_an_out_of_range_numeric_argument() -> None:
    """Each refusal must NAME the flag, the value and the range (S-12).

    A message that says only "invalid argument" is the `generic` grade the seam
    rules call a defect in its own right: a caller cannot recover differently from
    failures it cannot tell apart.
    """
    from platterpus.adapters.cyanrip_backend import assert_numeric_args_in_range

    cases = [
        (["cyanrip", "-N", "-r", "10000"], "-r", "0..100"),
        (["cyanrip", "-N", "-S", "999"], "-S", "0..72"),
        (["cyanrip", "-N", "-Z", "1000"], "-Z", "0..10"),
        (["cyanrip", "-N", "-s", "99999"], "-s", "-5000..5000"),
    ]
    for argv, flag, expected_range in cases:
        with pytest.raises(RipError) as excinfo:
            assert_numeric_args_in_range(argv)
        message = str(excinfo.value)
        assert flag in message, f"the refusal does not name the flag: {message}"
        assert expected_range in message, (
            f"the refusal does not state the range, so a user cannot tell what "
            f"would be acceptable: {message}"
        )


def test_every_in_range_value_is_accepted() -> None:
    """The floor. A guard that refuses everything is not a range check.

    Without this, tightening a bound to a single value would still pass the test
    above — and the rip would be unrunnable.
    """
    from platterpus.adapters.cyanrip_backend import assert_numeric_args_in_range

    accepted = 0
    for argv in (
        ["cyanrip", "-N", "-r", "0"],
        ["cyanrip", "-N", "-r", "100"],
        ["cyanrip", "-N", "-S", "0"],
        ["cyanrip", "-N", "-S", "72"],
        ["cyanrip", "-N", "-Z", "10"],
        ["cyanrip", "-N", "-s", "-5000"],
        ["cyanrip", "-N", "-s", "5000"],
        ["cyanrip", "-N", "-s", "667"],
    ):
        assert_numeric_args_in_range(argv)  # must not raise
        accepted += 1
    assert accepted == 8, "the accept-side cases did not all run"


def test_a_non_integer_argument_is_refused_rather_than_forwarded() -> None:
    """`-r abc` must not become the C program's problem."""
    from platterpus.adapters.cyanrip_backend import assert_numeric_args_in_range

    with pytest.raises(RipError, match="not an integer"):
        assert_numeric_args_in_range(["cyanrip", "-N", "-r", "abc"])


def test_the_range_map_reuses_the_settings_bounds_rather_than_copying_them() -> None:
    """One source of truth, or the dialog and the argv can disagree.

    Asserts the *values* agree, so a future edit to either side that forgets the
    other fails here rather than shipping two different definitions of acceptable.
    """
    from platterpus import settings_validation as sv
    from platterpus.adapters.cyanrip_backend import _load_arg_ranges

    ranges = _load_arg_ranges()
    assert ranges["-r"][:2] == (sv.MAX_RETRIES_MIN, sv.MAX_RETRIES_MAX)
    assert ranges["-S"][:2] == (sv.READ_SPEED_MIN, sv.READ_SPEED_MAX)
    assert ranges["-Z"][:2] == (sv.SECURE_REREP_MIN, sv.SECURE_REREP_MAX)
    assert ranges["-s"][:2] == (sv.OFFSET_MIN, sv.OFFSET_MAX)
    assert len(ranges) >= 4, "the range map is smaller than the flags it must cover"


def test_a_negative_is_refused_rather_than_silently_treated_as_auto() -> None:
    """`0` means auto; a negative meant nothing and emitted no flag at all.

    The silent drop is the defect: a caller that computed a negative got a default
    that looked deliberate and never learned otherwise.
    """
    for kwargs in ({"read_speed": -1}, {"secure_rerip_matches": -1}):
        with pytest.raises(RipError, match="not 'auto'"):
            _impl()._build_rip_argv(
                "/dev/sr0",
                unknown=False,
                cover_art="",
                max_retries=5,
                read_offset_override=667,
                track_template="%d/%t - %n",
                metadata=RipMetadata(album_title="X"),
                **kwargs,  # type: ignore[arg-type]
            )


def test_the_self_probe_reports_no_silently_dropped_values() -> None:
    """The black-box probe is a GATE, not a report someone might read.

    S-11: every row in the seam table is backed by a test in its owner's suite.
    This runs the real probe and fails if any non-zero value a caller set vanishes
    without a refusal — which is the exact finding that produced this whole batch.
    """
    import importlib.util

    script = _REPO_ROOT / "scripts" / "probe_argv_surface.py"
    spec = importlib.util.spec_from_file_location("probe_argv_surface", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    probes = module.probe_all()
    assert len(probes) >= 20, (
        f"only {len(probes)} probes ran; the grid is not exercising the surface"
    )
    findings = [p for p in probes if p.is_finding]
    assert not findings, "values silently dropped from the argv: " + ", ".join(
        f"{p.parameter}={p.value}" for p in findings
    )
    # A probe run where NOTHING is ever refused would mean the range guard is gone.
    refused = [p for p in probes if p.outcome == "raised"]
    assert len(refused) >= 4, (
        f"only {len(refused)} probe(s) were refused — the range guard at the argv "
        "chokepoint is not firing, so out-of-range values reach the ripper again"
    )


# --- The -a / -t blob shape guard --------------------------------------------
#
# These pin the OUTBOUND half of the seam. The numbers in the docstrings below
# are measured, not reasoned: `scratchpad/escape-harness/harness.c` compiles the
# real `append_missing_keys()` out of cyanrip @ 9048082 (the pin installed on the
# rig) against the real libavutil 58.29.100 and prints what each blob parses to.
# That is why the expectations here are stated as facts about cyanrip rather than
# as our opinion of a format.


def test_the_metadata_blob_we_build_for_a_colon_title_is_accepted() -> None:
    """The real reference disc's title passes the chokepoint.

    This is the case the whole escape change exists for: "Every Breath You Take:
    The Classics". Measured through cyanrip's own parser it comes out as the real
    colon, and it must not be refused here.
    """
    from platterpus.adapters.cyanrip_backend import assert_meta_args_are_parseable

    args = _metadata_args(
        RipMetadata(
            album_title="Every Breath You Take: The Classics",
            album_artist="The Police",
            tracks=[TrackTag(number=1, title="Roxanne", artist="The Police")],
        ),
        release_id="",
    )
    assert "-a" in args and "-t" in args
    blob = args[args.index("-a") + 1]
    # The escape is present and the substitute is not.
    assert "Take\\: The" in blob
    assert "∶" not in blob
    assert_meta_args_are_parseable(["cyanrip", "-N", *args])  # must not raise


def test_an_unescaped_colon_in_a_value_is_refused_it_truncates() -> None:
    """A raw ':' does not fail in cyanrip — it drops the rest of the value.

    Measured against the pinned parser:

        album=Every Breath You Take: The Classics:album_artist=The Police
          -> [album] = [Every Breath You Take]

    " The Classics" is gone, exit code 0, nothing in the log. Silent loss is the
    failure this guard exists to make loud, so the refusal must fire even though
    the blob is, syntactically, something cyanrip will happily accept.
    """
    from platterpus.adapters.cyanrip_backend import assert_meta_args_are_parseable

    argv = [
        "cyanrip",
        "-N",
        "-a",
        "album=Every Breath You Take: The Classics:album_artist=The Police",
    ]
    with pytest.raises(RipError) as excinfo:
        assert_meta_args_are_parseable(argv)
    # The message must name the mechanism, not just say "invalid".
    assert "truncates" in str(excinfo.value)


def test_a_dangling_backslash_is_refused_it_eats_the_separator() -> None:
    """A value ending in one backslash escapes whatever follows it.

    Writing this test corrected my own model of the failure, so the distinction is
    recorded rather than smoothed over: a dangling escape **mid-blob** does not
    surface as a dangling escape at all. It eats the ``:`` and welds two tags into
    one field, which the unescaped-``=`` count catches first — so both refusals
    are asserted here, each with the message that actually fires. A guard whose
    error text you have to guess at is a guard nobody will trust in a bug report.

    The parity count matters because ``a\\\\`` (an escaped backslash) is a
    perfectly good value and ``a\\`` is not — ``endswith("\\\\")`` cannot tell
    them apart.
    """
    from platterpus.adapters.cyanrip_backend import assert_meta_args_are_parseable

    # Mid-blob: the escape consumes the ':' and the two tags merge, so this is
    # reported as a field with two unescaped '='.
    with pytest.raises(RipError, match="unescaped '='"):
        assert_meta_args_are_parseable(
            ["cyanrip", "-N", "-a", "album=Trailing\\:album_artist=X"]
        )
    # End of blob: nothing left to weld to, so the dangling escape is what is seen.
    with pytest.raises(RipError, match="lone backslash"):
        assert_meta_args_are_parseable(
            ["cyanrip", "-N", "-a", "album_artist=X:album=Trailing\\"]
        )
    # Escaped backslash: two of them, structurally fine, in both positions.
    assert_meta_args_are_parseable(
        ["cyanrip", "-N", "-a", "album=Trailing\\\\:album_artist=X"]
    )
    assert_meta_args_are_parseable(
        ["cyanrip", "-N", "-a", "album_artist=X:album=Trailing\\\\"]
    )


def test_a_track_arg_without_the_leading_number_equals_is_refused() -> None:
    """cyanrip steps over the '=' of `-t N=` without checking one is there.

    `strtol()` then `end += 1` — so `-t 12` moves its pointer one past the NUL
    and parses whatever follows in memory. We can never emit that, and that is
    exactly why it is worth a guard: the cost of being wrong is not a bad tag.
    """
    from platterpus.adapters.cyanrip_backend import assert_meta_args_are_parseable

    for bad in ("12", "title=Roxanne", ""):
        with pytest.raises(RipError, match="track number"):
            assert_meta_args_are_parseable(["cyanrip", "-N", "-t", bad])
    # The shape we do emit is accepted.
    assert_meta_args_are_parseable(["cyanrip", "-N", "-t", "12=title=Roxanne"])


def test_the_blob_guard_runs_from_the_chokepoint_not_just_directly() -> None:
    """Reachability, not presence.

    CLAUDE.md's own history has a fully-implemented guard called from nowhere
    (`RipHandle.cancel`). This asserts the new check is wired into
    `assert_metadata_lookup_disabled`, which is the one function every route to
    the ripper passes through — including the scripted verb, which delegates here
    rather than restating the rule.
    """
    from platterpus.adapters.cyanrip_backend import assert_metadata_lookup_disabled

    with pytest.raises(RipError, match="truncates"):
        assert_metadata_lookup_disabled(
            ["cyanrip", "-N", "-a", "album=A: B:album_artist=C"]
        )


def test_split_on_unescaped_matches_how_cyanrips_parser_walks_the_blob() -> None:
    """The splitter is the thing the guard's correctness rests on, so pin it.

    Cases 1 and 5 of the measured harness, plus the degenerate ones. Note the
    escaping backslash is RETAINED: this function answers "where are the
    structural separators", not "what is the final text" — conflating those is
    how a validator ends up rejecting a legitimate value.
    """
    from platterpus.adapters.cyanrip_backend import split_on_unescaped

    assert split_on_unescaped("a:b", ":") == ["a", "b"]
    assert split_on_unescaped("a\\:b", ":") == ["a\\:b"]
    assert split_on_unescaped("a\\\\:b", ":") == ["a\\\\", "b"]
    assert split_on_unescaped("", ":") == [""]
    assert split_on_unescaped("album=A\\:B\\:C:album_artist=X", ":") == [
        "album=A\\:B\\:C",
        "album_artist=X",
    ]
