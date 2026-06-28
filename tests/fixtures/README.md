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

When T32 surfaces real-world output that differs from the fixtures,
update the fixtures here and regenerate the affected tests.

## eac_baseline_police_classics.log / .cue (added 2026-06-12)

**The hardware parity baseline.** A real EAC V1.8 secure rip (Test & Copy)
of the maintainer's *The Police — Every Breath You Take: The Classics* disc
on the same Pioneer BDR-209D the GUI is tested with, conforming to the
flemmingss.com bit-perfect guide (Secure mode, accurate stream, cache
defeat, C2 off, offset +667, null samples in CRC). Lives in
`output_reference/EAC_flac/`. Stored in EAC's **native UTF-16/CRLF** (the
authentic artifact; was briefly UTF-8 — which hid a UTF-16-decoding bug in the
parity checker, since fixed). Read it via `platterpus.parity.decode_log_bytes`,
not `read_text("utf-8")`.

Ground truth for comparing whipper/cyanrip rips of the same disc: the
per-track EAC CRC32s must match exactly (same disc, same offset). Known
disc quirk to expect everywhere: **track 5** fails AccurateRip v2 and CTDB
says "differs in 3 samples @02:24:59" even under EAC — that's the disc,
not the ripper. Track 3 (whipper's >587-offset failure) rips CLEAN in EAC.
