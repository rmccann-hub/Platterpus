# EAC FLAC — the canonical parity baseline

`eac_baseline_police_classics.log` / `.cue` — a real **EAC V1.8** secure rip
(Test & Copy) of *The Police — Every Breath You Take: The Classics* on the
Pioneer BDR-209D (read offset **+667**). This is the extraction baseline every
parity check measures against (`scripts/eac_parity.py`, `tests/test_parity.py`,
`docs/test-plan.md` Part B).

⚠️ **The `.log` is UTF-16 — do not re-encode or "fix" it.** EAC writes UTF-16
natively; converting it to UTF-8 silently broke the parity checker once. Code
must read it via `platterpus.parity.decode_log_bytes` (encoding-sniffing),
never `read_text("utf-8")`.

Layout, the meaning of "parity" per format, and the no-audio rule
(Critical rule #8): see [`../README.md`](../README.md).

---

*Last updated for Platterpus v0.4.24.*
