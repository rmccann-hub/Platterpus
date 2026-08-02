# Round 2 — Platterpus verification (retrospective)

*Reconstructed 2026-08-02 while backfilling the correspondence record. Marked
retrospective for the same reason as round 1: not sent as a discrete step-5
file at the time.*

Their file: `inbound/round-2.md` (buffering + the `-l` flag).

| Claim | Verdict | What settled it |
|---|---|---|
| `setvbuf` fixes the buffering defect where a signal handler cannot | **Verified as sound; NOT verified in practice** | The reasoning is correct. Proving it needs a cancelled rip against the fork pin on the rig — still a hardware gate as of round 4. |
| The `-l` track-selection flag semantics | **Verified** | Recorded in `docs/dependency-contracts.md` and exercised by the per-track re-rip path. |

Superseded by rounds 3–4. Kept for the record, not as a live gate.
