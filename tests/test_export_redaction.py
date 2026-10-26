"""S10: home-folder paths become ``~`` at export, counted, and never in signed bytes.

The cyanrip fork's round 32 lap 9 S10 (their data register's X9): their filing of
the 2026-10-13 bundle replaced home paths in nine files by hand. These tests hold
the export to three promises: every home path in a text member is replaced; the
replacement is COUNTED in the manifest, never silent; and a member whose bytes are
signed (a cyanrip log, our EAC-compatible log) is written byte for byte, because a
genuine log that fails its own check is worse evidence than one naming a folder.

The real data is the floor: our own filing of that run, under
``docs/handshake/artifactsround32/`` (read here through its fixtures in
``tests/fixtures/evidence/``), still carries the home paths, so the
redaction is run over it and must both find them and leave every signed log
verifiable.
"""

from __future__ import annotations

import hashlib
import tarfile
from pathlib import Path

from evidence_paths import evidence_dir
from hypothesis import given
from hypothesis import strategies as st

from platterpus.bundle_integrity import HOME_FOLDERS_HEADING
from platterpus.eac_log_export import verify_eac_style_log_checksum
from platterpus.evidence_bundle import build_bundle
from platterpus.export_redaction import (
    HOME_PATH,
    KEPT_CYANRIP_SIGNED,
    KEPT_PLATTERPUS_CHECKSUM,
    redact_member,
    redact_text,
)

#: Our filing of the run, through its fixtures (HR-2 moved `artifactsround32` off
#: `main`). Every one of its 76 files has one: logs, cues, the manifest and the
#: settings byte for byte, the reports as slim extracts without `debug.lines` and
#: the app logs without cyanrip's progress lines (`scripts/evidence_fixtures.py`).
#: The extracts still name home paths, just fewer of them (the reports' debug
#: lines held most), so the floors below are unchanged.
_FILED = evidence_dir("docs/handshake/artifactsround32")

# A synthetic signed cyanrip log: the banner, a path, and the signature line.
_SIGNED_LOG = (
    "cyanrip 0.9.4-rc2+platterpus.22 (platterpus-fork-g200530e)\n"
    "Invoked as:     /usr/local/bin/cyanrip -N -D /home/alice/Music/x\n"
    "Log FUN512: abcDEF012._\n"
)


def _eac_style(body: str) -> str:
    """A log ending in Platterpus's checksum footer, in the documented shape."""
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return (
        f"{body}==== Platterpus log checksum (SHA-256 of the text above; NOT an "
        f"EAC checksum): {digest} ====\n"
    )


# --- the replacement itself -----------------------------------------------------


def test_every_home_shape_becomes_a_tilde_and_is_counted() -> None:
    text = (
        "a /home/alice/Music/x.flac\n"
        "b /var/home/alice\n"
        'c "/Users/bob/Desktop"\n'
        "d C:\\Users\\carol\\Music\n"
        'e {"p": "C:\\\\Users\\\\dave\\\\x"}\n'
        "f ~/already/replaced and /tmp/elsewhere and x/home/notahome\n"
    )
    new, replaced, wire = redact_text(text)
    assert replaced == 5, new
    assert wire == 0
    assert "alice" not in new and "bob" not in new
    assert "carol" not in new and "dave" not in new
    assert "a ~/Music/x.flac\n" in new
    assert "b ~\n" in new
    # Untouched: an already-replaced path, a non-home path, an embedded word.
    assert "f ~/already/replaced and /tmp/elsewhere and x/home/notahome\n" in new


def test_a_path_after_an_escaped_newline_is_replaced() -> None:
    """The 2026-10-20 Full run's reports held the setup log as one JSON string:
    ``...distrobox\\n/home/<name>/.local/bin/flac``. The ``n`` of the escape is a
    word character, so the boundary saw a path inside a word and kept the
    owner's username, in a bundle bound for the public evidence branch."""
    text = '"host-setup: exit 0 from distrobox\\n/home/alice/.local/bin/flac\\t/home/bob/x"\n'
    new, replaced, _ = redact_text(text)
    assert replaced == 2, new
    assert "alice" not in new and "bob" not in new
    assert "distrobox\\n~/.local/bin/flac" in new
    # This machine's exact home, and the identity patterns, share the boundary.
    exact, n, _ = redact_text("a\\n/root/rips\n", homes=["/root"])
    assert (exact, n) == ("a\\n~/rips\n", 1)
    # Still untouched: a path embedded in a longer word.
    assert redact_text("x/home/notahome\n") == ("x/home/notahome\n", 0, 0)


def test_this_machines_own_home_is_replaced_exactly_and_only_at_a_boundary() -> None:
    """A home outside ``/home`` (``/root``) is caught by name, not by shape."""
    new, replaced, _ = redact_text(
        "/root/rips/x and /rootfs/y and /root\n", homes=["/root"]
    )
    assert new == "~/rips/x and /rootfs/y and ~\n"
    assert replaced == 2
    # `/` is not a home anyone can hide: it would rewrite every absolute path.
    assert redact_text("/etc/x\n", homes=["/"]) == ("/etc/x\n", 0, 0)


def test_a_handshake_wire_line_is_left_as_it_is_and_counted() -> None:
    text = "HANDSHAKE-NOTE: /home/alice/x\nbody /home/alice/x\n"
    new, replaced, wire = redact_text(text)
    assert new == "HANDSHAKE-NOTE: /home/alice/x\nbody ~/x\n"
    assert (replaced, wire) == (1, 1)


def test_bytes_that_are_not_utf8_survive_exactly() -> None:
    """A log cut mid-character by the size cap: only the path changes."""
    data = b"\xff\xfe /home/alice/x \xc3"
    done = redact_member(data)
    assert done.data == b"\xff\xfe ~/x \xc3"
    assert done.replaced == 1


def test_a_signed_cyanrip_log_is_kept_byte_for_byte_with_its_paths_counted() -> None:
    data = _SIGNED_LOG.encode()
    done = redact_member(data)
    assert done.data == data
    assert done.replaced == 0
    assert done.left_in_place == 1
    assert done.kept_reason == KEPT_CYANRIP_SIGNED


def test_a_chase_record_is_redacted_around_its_embedded_logs() -> None:
    """The 2026-10-22 11:45 UTC Full run exported the verified-read chase's record
    (TASKS R7) with the rig's home folder on every argv line: the record holds
    signed cyanrip logs, so the whole file was kept as one. Our argv lines are
    redacted now, and each embedded log is kept exactly as written, its own
    path included, since replacing it would break its signature."""
    attempt = (
        "=== Platterpus verified-read chase: track 16, attempt {n} ===\n"
        "argv: /var/home/alice/.local/bin/cyanrip -l 16\n"
        "exit status: 0\n\n"
    )
    text = attempt.format(n=1) + _SIGNED_LOG + "\n" + attempt.format(n=2) + _SIGNED_LOG
    done = redact_member(text.encode())

    out = done.data.decode()
    assert "/var/home/alice" not in out
    assert out.count(_SIGNED_LOG) == 2, "an embedded log was altered"
    assert done.replaced == 2
    assert done.kept_reason == ""


def test_our_checksummed_eac_log_is_kept_byte_for_byte() -> None:
    text = _eac_style("Used drive  : x\nFilename /home/alice/Music/01.flac\n")
    # The stand-in is real: the module that writes the footer accepts it.
    assert verify_eac_style_log_checksum(text) is True
    done = redact_member(text.encode())
    assert done.data == text.encode()
    assert done.kept_reason == KEPT_PLATTERPUS_CHECKSUM
    assert done.left_in_place == 1


@given(st.binary(max_size=400))
def test_redaction_never_raises_and_changes_nothing_but_paths(data: bytes) -> None:
    """Any bytes at all: no exception, and with no replacement, identical bytes.

    Bundle members are external input (a ripper's log, a log cut mid-character by
    the size cap), so the rule for parsers of external output applies: never
    raises, property-tested.
    """
    done = redact_member(data, homes=["/root"])
    if done.replaced == 0:
        assert done.data == data
    else:
        assert len(done.data) < len(data)


#: Text with no line break of any kind, so a generated line cannot begin
#: `HANDSHAKE-` (which is left alone by design) and the property stays about paths.
_ONE_LINE = st.text(
    alphabet=st.characters(blacklist_categories=("Cc", "Zl", "Zp")), max_size=80
)


@given(_ONE_LINE, st.text(alphabet="abcdefgh", min_size=1, max_size=8))
def test_a_home_path_is_never_left_behind_in_an_unsigned_line(
    noise: str, name: str
) -> None:
    """Whatever surrounds it on the line, a ``/home/<name>/`` path does not survive."""
    new, replaced, _ = redact_text(f"x {noise} /home/{name}/Music {noise}")
    assert f" /home/{name}/" not in new
    assert replaced >= 1


# --- the real filed run ---------------------------------------------------------

#: The suffix `scripts/evidence_fixtures.py` gives an extract's provenance record.
_SIDECAR = ".extract.json"


def test_the_filed_round_32_run_is_redacted_and_its_signed_logs_stay_verifiable() -> (
    None
):
    """Run over our own filing of the 2026-10-13 bundle, which still names home.

    Floors, so "nothing went wrong" cannot be satisfied by "nothing was looked
    at": eleven cyanrip logs recognised as signed, nine EAC-compatible logs
    recognised by their footer and STILL verifying after the export, and home
    paths actually found and replaced in the unsigned members.
    """
    # An extract's sidecar records where the fixture came from; it was never part
    # of the filed run, so it is not a member.
    members = sorted(
        p for p in _FILED.iterdir() if p.is_file() and not p.name.endswith(_SIDECAR)
    )
    assert len(members) >= 70, f"the filed run shrank: {len(members)} files"
    signed_cyanrip = 0
    eac_still_verifies = 0
    replaced_total = 0
    changed_members = 0
    for path in members:
        data = path.read_bytes()
        done = redact_member(data)
        if done.kept_reason == KEPT_CYANRIP_SIGNED:
            signed_cyanrip += 1
            assert done.data == data, path.name
        elif done.kept_reason == KEPT_PLATTERPUS_CHECKSUM:
            assert done.data == data, path.name
            if verify_eac_style_log_checksum(done.data.decode("utf-8")) is True:
                eac_still_verifies += 1
        else:
            assert not done.kept_reason, (path.name, done.kept_reason)
            remaining = HOME_PATH.findall(
                done.data.decode("utf-8", errors="surrogateescape")
            )
            assert not remaining, f"{path.name} still names {len(remaining)} home(s)"
            if done.replaced:
                changed_members += 1
                replaced_total += done.replaced
    assert signed_cyanrip >= 11, signed_cyanrip
    assert eac_still_verifies >= 9, eac_still_verifies
    assert changed_members >= 5 and replaced_total >= 20, (
        changed_members,
        replaced_total,
    )


# --- through the bundle ---------------------------------------------------------


def test_the_bundle_replaces_records_and_hashes_after_replacement(
    tmp_path: Path,
) -> None:
    """End to end: the member, the manifest's record of it, and its S8 hash.

    The machine's home is given as ``tmp_path`` so the test never depends on
    where the machine running it keeps its own, and so the album folder's path in
    the manifest is a home path the manifest must replace in itself.
    """
    album = tmp_path / "album"
    album.mkdir()
    config = "output_dir = '/home/alice/Music'\nother = '/home/alice/x'\n"
    (album / "config.toml").write_text(config)
    (album / "rip.log").write_text(_SIGNED_LOG)
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "log.txt").write_text(f"started in {tmp_path}/logs\n")

    result = build_bundle(
        dest_dir=tmp_path / "out",
        stamp="20261014T000000Z",
        app_version="0.7.104",
        outcome="success",
        album_dir=album,
        log_dir=logs,
        extra_text={"SETTINGS.json": '{"output_dir": "/home/alice/Music"}'},
        homes=[str(tmp_path)],
    )

    assert result.path is not None, result.error
    with tarfile.open(result.path, "r:gz") as tar:

        def member(name: str) -> bytes:
            handle = tar.extractfile(name)
            assert handle is not None, name
            return handle.read()

        toml = member("album/config.toml")
        signed = member("album/rip.log")
        settings = member("SETTINGS.json")
        applog = member("applog/log.txt")
        manifest = member("MANIFEST.txt").decode("utf-8")

    assert toml == b"output_dir = '~/Music'\nother = '~/x'\n"
    assert settings == b'{"output_dir": "~/Music"}'
    assert applog == b"started in ~/logs\n"
    assert signed == _SIGNED_LOG.encode(), "a signed log was changed"
    # The manifest replaced its own paths — and said how many.
    assert str(tmp_path) not in manifest
    assert HOME_FOLDERS_HEADING in manifest
    own = next(
        line for line in manifest.splitlines() if "in this manifest's own text" in line
    )
    assert "and 0 in" not in own, own
    # Each changed member is named with its count and its hash BEFORE the change,
    # which is the original file's — so the rig's copy can still be matched.
    toml_row = next(
        line
        for line in manifest.splitlines()
        if line.startswith("  album/config.toml") and "replaced" in line
    )
    assert " 2 replaced" in toml_row, toml_row
    assert hashlib.sha256(config.encode()).hexdigest() in toml_row
    # The signed log is named as kept, with the paths it still carries.
    kept = next(
        line
        for line in manifest.splitlines()
        if line.startswith("  album/rip.log") and "left" in line
    )
    assert "1 left" in kept and "signed by cyanrip" in kept, kept
    # S8's hash is of the REPLACED bytes, the ones a receiver extracts.
    assert f"{hashlib.sha256(toml).hexdigest()}  album/config.toml" in manifest
    entry = next(e for e in result.included if e.name == "album/config.toml")
    assert entry.home_paths_replaced == 2


def test_home_path_starts_each_unix_arm_with_the_shared_prefix() -> None:
    """HOME_PATH is a literal so the regex sweep can time it; this keeps its two
    Unix arms on the one escape-aware start the identity patterns use."""
    from platterpus.export_redaction import ESCAPE_AWARE_START, HOME_PATH

    assert HOME_PATH.pattern.count(ESCAPE_AWARE_START) == 2
