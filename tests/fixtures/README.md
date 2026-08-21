# Test fixtures

Test data files consumed by `tests/test_*.py`. These are NOT pytest
fixtures — pytest fixtures (the `@pytest.fixture` kind) live in
`tests/conftest.py` and `tests/test_*.py` files themselves.

Each file here is a stable input that exercises one parser or one
adapter. Files are named `<subject>_<scenario>.{txt,log}`:

- `drive_list_*.txt` — parsed by `parsers/drive_list.py`
- `cd_info_*.txt` — parsed by `parsers/cd_info.py`
- `rip_log_*.log` — parsed by `parsers/rip_log.py`

The primary `rip_log_real_whipper_0_7.log` was pulled verbatim from
whipper-team/whipper master's own test suite (commit referenced inside
the file's "Log created by" line). The `rip_log_eac_reference.log`
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

*Last updated for Platterpus v0.6.23.*
