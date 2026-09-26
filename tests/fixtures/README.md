# Test fixtures

Test data files consumed by `tests/test_*.py`. These are NOT pytest
fixtures — pytest fixtures (the `@pytest.fixture` kind) live in
`tests/conftest.py` and `tests/test_*.py` files themselves.

Each file here is a stable input that exercises one parser or one
adapter. Files are named `<subject>_<scenario>.{txt,log}`:

- `drive_list_*.txt` — parsed by `parsers/drive_list.py`
- `cd_info_*.txt` — parsed by `parsers/cd_info.py`
- `rip_log_*.log` — parsed by `parsers/rip_log.py`

The primary `rip_log_legacy_format.log` is a real log in the **legacy log
format** — the one written by the ripper Platterpus drove before cyanrip
(KDD-18), which Platterpus still reads so rips made before 2026-06-30 stay
readable. **Attribution, kept because it is owed:** the file was pulled verbatim
from the test suite of whipper-team/whipper (master), the project that wrote the
format; the commit is referenced inside the file's "Log created by" line. Its
content is left exactly as published — a real artifact edited to read neutrally
would no longer be real. Renamed from its original fixture name on 2026-09-24. The `rip_log_eac_reference.log`
is hand-authored from public EAC log documentation and exists only
as a reference for the format comparison in `docs/eac-parity.md`
— it is NOT consumed by any parser.

When real-world output differs from a fixture, update the fixture here and
regenerate the affected tests (as the T32 smoke test did in 2026-05).

## eac_baseline_police_classics.log / .cue (added 2026-06-12)

**The hardware parity baseline** (a real EAC V1.8 rip of the maintainer's
Police disc) lives in `output_reference/EAC_flac/`; `output_reference/README.md`
+ that directory's own README are the canonical account (provenance, rip
settings, and the disc's known track-3/track-5 quirks). One warning repeated
here because it bites tests directly: the log is stored in EAC's **native
UTF-16/CRLF** — read it via `platterpus.parity.decode_log_bytes`, never
`read_text("utf-8")` (a UTF-8 copy once hid a real decoding bug in the parity
checker).

## cyanrip_cancelled_at_track_one.log (added 2026-09-11)

**A real cyanrip log from a rip cancelled during track 1**, lifted verbatim from
the 2026-09-11 acceptance run's §I (`cancel me …`, ripper
`platterpus-fork-gddc1e8c`). It is here because §I's shape cannot be reconstructed
from any other fixture we hold: the cancel lands before the first track block is
written, so the log carries a completion footer (`Rip completed:  no (interrupted
by SIGTERM, 0 of 14 tracks)`), an `Interrupted at:` line, a valid `Log FUN512:`
signature — and **zero track blocks**.

That combination is the whole point. `expect-log-well-formed`'s floor was *"at
least one track block"*, and every stand-in the verb had been tested against was a
completed 14-track rip, so the floor never met the case the section exists for and
failed a correct archival record on hardware. *What does my stand-in do that the
real thing does not.*

It is text (rule #8: logs and CRCs travel, audio never does) and carries no home
paths — its `Invoked as:` line names the in-container `/usr/local/bin/cyanrip`.
Do not "tidy" it: it is evidence, and a hand-edited log proves nothing.

## Handshake artifacts are NOT copied in here (note added 2026-08-21)

A test that needs a real cyanrip log from a handshake round reads it **from
`docs/handshake/inbound/artifacts/`**, not from a copy placed here.

Written down because the copy was made and then deleted the same hour:
`tests/test_fork_album_loudness_r12.py` needed the round-12 golden reference and
interrupted sample, and both were *already* committed under that directory,
byte-identical. A second copy under `tests/fixtures/` would have been the same
artifact at the same value in two places — two records of one fact, with nothing
saying which is current (Critical rule #7). Those files are also **correspondence**:
a byte-faithful record of what the fork sent, deliberately exempt from our doc
stamps, so duplicating one risks the copy drifting from the record.

Read them at the path, and strip any delivery header the artifact itself
documents (the interrupted sample carries one) at read time.

---

*Last updated for Platterpus v0.6.60.*

## attestation_v0660.sigstore.json + sigstore_trusted_root_20260925.json (added 2026-09-25)

**A real release's build attestation, and the trust root that verifies it.** The
bundle is the Sigstore attestation GitHub holds for the v0.6.60 AppImage (SHA-256
`dbd7aacd5ab705449a2d99d217d1e6a3bc57bc8725702d6777efd1315bcdd526`), fetched from
`api.github.com/repos/rmccann-hub/Platterpus/attestations/sha256:<digest>` and
stored compact. The trust root is Sigstore's production `trusted_root.json` as
refreshed over TUF the same day, identical to the copy inside `sigstore` 4.5.0.
Together they let `tests/test_update_attestation.py` verify a genuine release
**offline**, against the source artifact rather than against another run of our
code. Neither contains audio or anything private: both are published records of
public keys and a public build. Verification checks key validity at the time of
signing, not today, so these stay verifiable; replace them only to test a newer
bundle format.
