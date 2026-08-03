# Handshake correspondence with the cyanrip fork

Every file exchanged with the cyanrip fork, both directions, committed so the
record survives the session that produced it. The protocol itself is
[`../cyanrip-handshake.md`](../cyanrip-handshake.md); the tool that enforces it
is `scripts/handshake.py`.

```
outbound/round-N.md   what Platterpus sent    (protocol §3)
inbound/round-N.md    what the fork sent back (protocol §4)
verified/round-N.md   our verification of it  (protocol §2, step 5)
```

A round is **CLOSED** when all three files exist **and our verification declares
`GO`**. The verdict closes the round, not the file's existence — a verification
may deliberately be a mid-round `**HOLD`, and round 7 is one. `python
scripts/handshake.py --status` reports it, and **no release and no pin switch
happens while any round is OPEN.** See `../cyanrip-handshake.md` §7.5 for why the
gate reads the verdict: it used to read presence, and it reported a HOLD as
closed.

## Round-by-round

Newest first. `pin` is the fork commit the round concerns; the **live** pin is
whatever `src/platterpus/deps/fork_source.py` builds, which only ever moves to a
commit a *closed* round verified.

| Round | Pin | Verdict | What it was about |
|---|---|---|---|
| **7** | `d5d12ec` (`0.9.4-rc1+platterpus.3`) | **HOLD — OPEN** | Their §7 measured both rip sessions at 81m11s / 81m13s, refuting our "much faster" explanation — we had described the dynamic-rerip mechanism and let it stand as the cause of a delta never measured. Their §5 pre-gap `Duration:` off-by-one-frame reproduced on our rig, with a sign flip they had not reported (+1 on tracks 1–13, **−1 on track 14**). Gate 1 pre-gap emission verified exactly. Their §6a/§6b answered — one mechanism refuted, one presentation fix accepted and landed. Their file ships **no §I provider contract**. Amendments: none. |
| **6** | `2f950c8` (fork release r2) | GO | The round that took three pins in one day. Their finding: at any paranoia level above 0, ripping a **disc image** returned one correct sector then silence — 99.7% of samples zeroed, reported as `Ripping errors: 0` — inherited from upstream, never affecting a real drive. Ours: two consecutive golden references whose build tags named commits three behind their content; per-track paranoia counters are per-**pass**, not per-track; their §C7 refuted by their own appendix. Amendments `6b` (urgent pin withdrawal) and `6c`. |
| **5** | `e1d800e` | GO | Found the release blocker: every version probe we shipped sent `cyanrip -V`, which upstream deleted after 0.9.3 — and a non-zero exit from a version probe reads here as *"the tool is not installed."* Also found our strongest-looking test was measuring **their** generator's allowlist, not the ripper: their fatal inventory went 88 → 104 on re-derivation and our matcher had missed all 13 matchable strings the allowlist hid. |
| **4** | `a04a94b` | GO | First round under `scripts/handshake.py`, and the round that added §I (the provider contract) to the spec. Their §B answers checked and their golden reference run through the real parser. |
| **3** | — | GO *(retrospective)* | The fork's return file, verbatim. Our verification was **late** and went out folded into round 4's outbound §1–§3 rather than as its own step-5 file — which `--status` is what surfaced, and is a fair summary of why the tooling was written. |
| **2** | — | GO *(retrospective)* | `setvbuf` as the fix for the buffering defect a signal handler cannot reach, and the `-l` track-selection semantics. |
| **1** | — | GO *(retrospective)* | The fork's FIXPLAN: cyanrip's logfile and cue are block-buffered, so a killed process loses up to a 4096-byte stdio block. Reproduced against a real cancelled rip whose log ended mid-token at `REPLAYGAIN_TRACK_GA`. |

Rounds 1–3 carry no `**GO`/`**HOLD` marker — the convention began at round 4 —
so they are grandfathered by number in `handshake.RETROSPECTIVE_ROUNDS`, a set a
test pins to exactly `{1, 2, 3}`.

## These files are correspondence, not documentation

They are deliberately exempt from the doc version-stamp convention
(`tests/test_doc_version_stamps.py`). Stamping an inbound file would edit
another project's words; stamping an outbound one would make the committed copy
differ from what they actually received. A record that is not the record is
worthless. Their currency is the round number.

Do not edit a file here after it has been sent or received. If something in it
was wrong, that belongs in the **next** round's Corrections section — which is
the mechanism, and most of the errors found so far arrived that way.

## Amendments

`round-6b.md` is **round 6**, not round 6b. A round may be amended — round 6 was,
within hours, because the pin it asked for returned silence on disc images —
and `handshake.py` reads `round-<N><suffix>.md` as round *N*. Counting an
amendment as its own round would report two open rounds where one was corrected,
and would make sending a correction immediately score *worse* in the record than
sitting on it. `--check` accepts several files so a round validates as a set, and
`--status` takes the **newest** file's verdict, so a GO withdrawn the same evening
does not keep a round closed.

## Backfill note

Rounds 1–3 predate `scripts/handshake.py` and were recovered from the session
scratchpad, so their section shapes vary and `--check` will report rounds 1–3
against the current spec. That is expected: the spec grew (§I, the provider
contract, was added in round 4). Round 3's `inbound` is the fork's file verbatim.
