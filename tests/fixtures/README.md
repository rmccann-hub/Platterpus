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
as a reference for the format comparison in `docs/log-format-comparison.md`
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

---

*Last updated for Platterpus v0.5.0.*
