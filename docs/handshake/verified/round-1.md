# Round 1 — Platterpus verification (retrospective)

*Reconstructed 2026-08-02 while backfilling the correspondence record. Marked
retrospective because it was **not** sent as a discrete step-5 file at the time
— the tooling that would have caught that did not exist yet.*

Their file: `inbound/round-1.md` (the fork's FIXPLAN).

| Claim | Verdict | What settled it |
|---|---|---|
| cyanrip's logfile and cue are block-buffered, so a killed process loses up to a 4096-byte stdio block | **Verified** | Reproduced against the maintainer's real cancelled rip: the log ended mid-token at `REPLAYGAIN_TRACK_GA`. |
| A fork cannot fix it, because SIGKILL is uncatchable | **Refuted — by the fork itself, in round 2** | True of signal *handlers*, false of `setvbuf`, which removes the buffering so nothing is pending at kill time. Recorded in the protocol's "who was wrong" table. |
| podman does not forward signals into the container | **Verified** | Our SIGTERM reaches only the host wrapper; this is why `RipHandle.cancel` escalates to a process-group SIGKILL. |

Superseded by rounds 2–4. Kept for the record, not as a live gate.
