# Round 3 — Platterpus verification of cyanrip's return file

*Step 5 of `docs/cyanrip-handshake.md` §2. Recorded 2026-08-02.*

**Delivery note, stated plainly because the protocol's whole point is that
silence is not an answer:** this verification was **late**, and it went out
folded into the round-4 outbound file (§1–§3 there) rather than as its own
step-5 file. `scripts/handshake.py --status` is what surfaced the omission —
`round-3: sent=NO returned=yes verified=NO -> OPEN` — after the tooling was
written, which is a fair summary of why the tooling was written. This file is
the record; the fork has the content.

## Claim-by-claim

| # | Their claim | Verdict | What settled it |
|---|---|---|---|
| C1 | The `-Z` `Done;` line is **not** stdout-only | **Verified** | Their reading of `cyanrip_log()`, and our parser now handles both indentations — pinned in `tests/test_parsers_cyanrip_log.py`. **This was our error, not theirs.** |
| C2 | `setvbuf` fixes the block-buffering loss where a signal handler cannot | **Verified as sound, NOT verified in practice** | The reasoning is correct — `setvbuf` removes the buffering, so nothing is pending at kill time. Proving it needs a real cancelled rip against the fork pin on the rig. Listed as a hardware gate, not claimed. |
| C3 | Track 1's `Pregap length: 300` = lead-in 150 + declared TOC 150 | **Verified twice** | Their package, then independently from `output_reference/EAC_flac/eac_baseline_police_classics.log`. |
| C4 | The `Pregap source: TOC` / `sub-channel` distinction | **Verified** | `parse_cyanrip_log` over their golden reference yields `pregap_source='TOC'` for tracks 1–2 and `pregap_state='unknown'` with reason `sub-channel unreadable` for track 3. |
| C5 | 21 of their 45 fatal strings were missed by our error pattern | **Verified and fixed** | `tests/test_ripper_error_surfacing.py`; the pattern went from 6 prefixes to 23. |
| C6 | The Q-subchannel path has never executed successfully on a libcdio image | **Verified as a real, open gap** | Our parse of their golden reference shows the image behaviour (`unknown`), not drive behaviour. No synthetic fixture retires it. |

## Not verified

- **C2 in practice.** Needs the rig.
- **§H2** — their finding that EAC's `Pre-gap length` is the TOC component alone.
  **Refuted.** EAC's log prints `Track 1 … Pre-gap length  0:00:02.00`; the full
  measurement is round 4 §1 and the derivation now lives in
  `tests/test_eac_pregap_convention.py`. We had accepted and shipped it before
  checking, which is its own lesson (`docs/testing.md` §5.u).

## Go / no-go

**No-go on the release**, and the reason is not their file — it is that round 4
is now open in the other direction. Two hardware gates also remain: the
buffering fix and a successful sub-channel pre-gap read.
