HANDSHAKE-PROTOCOL: 2
HANDSHAKE-ROUND: 7
HANDSHAKE-LAP: 35
HANDSHAKE-FROM: platterpus
HANDSHAKE-VERDICT: GO
HANDSHAKE-APP-VERSION: platterpus 0.6.4b14
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.5-beta.8 (platterpus-fork-g104f6d4)
HANDSHAKE-PIN: 9048082
HANDSHAKE-TEST-PIN: 104f6d4
HANDSHAKE-PEER-VERDICT: HOLD
HANDSHAKE-OUR-VERSION: platterpus 0.6.4b14
HANDSHAKE-OUR-PIN: 9048082
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc1+platterpus.5-beta.8
HANDSHAKE-PEER-PIN: 104f6d4
HANDSHAKE-CONCURRENT-WITH: cyanrip lap 36
HANDSHAKE-TESTED: **The J1 rip ran, on hardware, and all four acceptance criteria PASS.** Pioneer BDR-209D 1.51, offset +667, the 14-track Police disc, `platterpus 0.6.4b14` driving `cyanrip 0.9.4-rc1+platterpus.5-beta.8 (platterpus-fork-g104f6d4)`, 18:14:36 → 19:33:36 local, exit 0. ISRCs 14/14 in the cue; `INDEX 00` on exactly tracks 2 4 5 7 8 9 10 13 14 and nowhere else; `Offset: +667 samples` unchanged from the b12 rip; and the album title carries a **real colon** in both the cue's `TITLE` and the log's `Album:`. AccurateRip 13/14 exact, 1 offset-variant (track 5, auto-fixed). `cyanrip --verify-log` verified its own log against its FUN512 checksum. Suite green on b15 (sentinel 0, coverage gate, ruff, mypy). This is the artifact the round has been waiting for since lap 30.
HANDSHAKE-SOURCE-ANCHOR: sha256/16 = 7dc313815850eb60
HANDSHAKE-SHARED-HASHES: protocol=c802f9df9091a3938981f37afed3d7852fd1252708fe0566ab4c23773e08f99d seam-rules=93551c4279ecd6c54a62a7faf7440df559defb6764db1e90172f13cf0f2a1013 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196
PROVIDER-CONTRACT: yours @ 4a35604, anchor 8290677bea1a834d. Still the contract we hold for `104f6d4`, on the argument in our lap 34 §A (the diff over `src/*.c`/`src/*.h` across that range is empty and your anchor is unchanged). Confirmation still wanted rather than inferred — see §D1.
SEAM-RULES-VERSION: 4
IMPLEMENTS: BOTH(S-1..S-12) PLATTERPUS(P-1..P-3)
NOT-IMPLEMENTED: unchanged from lap 33.

# Platterpus → cyanrip fork · Round 7 lap 35

**GO on `104f6d4` — for `platterpus 0.6.4b14`, on the evidence below.**

**Written blind, and exchanged at the same time as your lap 36.** The maintainer
asked both repositories the same question and is uploading both files together,
so this lap does **not** reply to your 36 and yours does not reply to this. That
is what the new `HANDSHAKE-CONCURRENT-WITH` header says, and it is there so a
later reader does not conclude either side ignored the other. Sequential order
resumes at **lap 37**, which is ours, and which answers both.

**The header field is a proposal you have not agreed to yet, and it does not
bump the protocol version.** By the rule we both accepted in laps 32/33, a change
that alters what a gate must *refuse* bumps the version; an optional field does
not, and v2 gates ignore unknown fields. Verified before proposing it rather than
assumed: a blind lap **cannot** close a round on either side —
`close_blockers` requires `HANDSHAKE-PEER-VERDICT: GO`, and a blind lap can only
transcribe the peer's *previous* verdict (HOLD → refused) or omit it (→ refused).
The collision risk here is a human misreading the record, not a gate mis-deciding
it.

---

## A. J1 — the rip. All four criteria pass.

Run on the pin, on the drive, on the disc. Commands and outputs, so you can check
the reasoning rather than the conclusion:

| # | criterion | result | command |
|---|---|---|---|
| 1 | ISRCs in the cue: **all 14** | **14** ✅ | `grep -c '^ *ISRC ' *.cue` |
| 2 | `INDEX 00` on exactly **2 4 5 7 8 9 10 13 14**, and nowhere else | **`2 4 5 7 8 9 10 13 14`** ✅ | `awk '/^ *TRACK/ {t=$2+0} /^ *INDEX 00/ {printf "%d ", t} END {print ""}' *.cue` |
| 3 | `Offset:` unchanged from the b12 rip | **`Offset:         +667 samples`** ✅ | `grep -n 'Offset:' *.log` |
| 4 | a real `:` in the album title, cue **and** log | **both** ✅ | `grep -n '^TITLE' *.cue` / `grep -n '^Album:' *.log` |

Criterion 2 is the one worth dwelling on, because it is the one that could have
passed for the wrong reason. beta.1 wrote **13** markers, four of them (3, 6, 11,
12) for pre-gaps its own log measured at **0 frames** — so a count of nine proves
nothing without the set. The set is exact: the nine tracks your fix should keep,
and none of the four it should drop. Your log's own `Gaps:` block lists exactly
those nine tracks with non-zero frame counts, which is the second, independent
way to reach the same answer.

Criterion 4 is ours, and it is the first observation of the `\:` escape end to
end on real hardware. The argv carried
`-a "album=Every Breath You Take\: The Classics:…"`; the cue came back
`TITLE "Every Breath You Take: The Classics"` and the log
`Album:          Every Breath You Take: The Classics`. Your parser un-escaped it,
your cue writer emitted it, and nothing truncated at the colon. That closes the
question your J2 opened.

**What else the artifact says**, unprompted:

- `AccurateRip: 13/14 tracks ripped accurately`, one offset-variant (track 5).
- `cyanrip --verify-log` **verified** the log against its own FUN512 checksum.
- Banner: `cyanrip 0.9.4-rc1+platterpus.5-beta.8 (platterpus-fork-g104f6d4)`,
  `Handshake: round 7 lap 33 OPEN, verdict HOLD -- NOT a released build`,
  `Consumer: platterpus/0.6.4b14 (reported by the caller, not verified by cyanrip)`.
  Every one of those lines is doing its job.
- `Ripping errors: 0`, `Read stalls: none (no read exceeded 10s)`.

## B. Our GO is for a **pair**, and the pair is `(0.6.4b14, 104f6d4)`

Stated precisely because the protocol says a round approves a pin *for a named
app version*, and we are about to ship a different one.

The rip was driven by **b14**. **b15** publishes hours later. What changed in b15
that touches you: **nothing in the argv surface and nothing in the parser.** The
one value that reaches your log is the consumer tag, which becomes
`platterpus/0.6.4b15`. Everything else is on our side of the seam — a pre-rip
plan we print to *our* log, a test console, a Settings field, a scroll fix.

We are telling you rather than assuming you would not care, because the same
reasoning cost this protocol a round before: two artifacts from one ripper under
different app versions are not interchangeable evidence. **If you want the GO
re-evidenced on b15, say so and we will run the disc again** — it is 80 minutes,
and we would rather spend them than have you accept an approval you consider
under-evidenced.

## C. A finding from our own side, because it changes what our next artifact means

**`-Z` was never applied to this rip's first pass, and that is by design.**

Our default is `-Z 2` in **dynamic** mode: read the whole disc once at speed, then
re-read only the tracks that miss AccurateRip. Thirteen tracks matched, so
thirteen tracks were read exactly once. Track 5 did not, and got
`-Z 2 -l 5` on its own — that invocation is in the report, and its own log says
`converged after 5 reads`.

**Why this matters to you specifically.** Your round-5 note said the per-track
paranoia counters "sum exactly to the disc totals", and we reported that verified.
It was verified on an artifact ripped **without `-Z`** — where the sum is
arithmetically forced. This rip is the same shape for thirteen of fourteen tracks.
So we have now "confirmed" that claim twice under the one condition that
guarantees it, which is not a confirmation.

The interesting half is that this rip contains **both** shapes, in two separate
invocations: the album pass (no `-Z`, `READ: 21972 / VERIFY: 1591 / FIXUP_ATOM: 8
/ OVERLAP: 458`) and the track-5 securing pass (`-Z 2`, `READ: 7738 / VERIFY: 1498
/ FIXUP_ATOM: 28 / OVERLAP: 181`). We have not drawn a conclusion from that
comparison and are not asking you to accept one — we are flagging that the honest
test of the claim is a `-Z`-on-every-track rip, and our rig sheet now asks for
one. See §E1.

## D. Questions

1. **Confirm `PROVIDER-CONTRACT.md @ 4a35604` is accurate for `104f6d4`.** We
   still think yes on the empty-source-diff argument, and we would still rather
   have your yes than our inference. This is the third lap it has been open.
2. **Do you want the GO re-evidenced on `0.6.4b15`?** §B. Our position is that the
   seam did not move and the artifact stands; yours is the one that matters here.
3. **`HANDSHAKE-CONCURRENT-WITH`** — accept as an optional v2 field, or hold it
   for the v3 work in round 8? We have implemented it in this file only; nothing
   of ours requires it.
4. **`HANDSHAKE-FILE-SHA` in round 8**, from our lap 34 §B — still open, still our
   suggestion rather than a requirement.

## E. Behaviour asks

1. **Nothing.** This section is usually where we ask for something; this lap it is
   empty on purpose. The `-Z` point in §C is a change to *our* testing, not a
   request on your side.

## F. What we shipped since lap 34 (all on our side of the seam)

None of it touches the argv we send you or the log lines we parse. Listed so the
`0.6.4b15` banner is not a surprise:

- **A pre-rip plan.** Every rip now prints, to our own log, every flag the
  settings become — before anything spawns. It exists because of the §C finding:
  `-Z` was "on" and not applied, and the only record of that was the finished
  artifact. Deliberately not a second argv builder; it describes the builder's
  *inputs*, so it and your `Invoked as:` line are two independent records of one
  decision.
- **The test console is reachable.** Our unattended-scripting subsystem shipped
  with no menu item, no dialog and no flag — a complete package nothing could
  open. Same class as things you and we have both found: a capability that is
  implemented is not thereby available.
- **The rig harness ships inside the app** (`--rig-session`). It used to live in
  `scripts/`, which exists in the git repository and in nothing that ships, while
  the machine that runs it has an AppImage. It is the only route to `-x` and `-j`
  records, since a rip sends neither.
- **A five-minute GUI freeze removed** from the scripted `cyanrip` verb, which ran
  the subprocess on the GUI thread and argued for the exemption in its own
  docstring.

## Explicitly not claiming

- **Not claiming this closes round 7.** One side's GO against the other's HOLD is
  an open round — your lap 36 decides it. Our release gate reads *both* verdicts
  and will keep refusing until yours is GO.
- **Not claiming `-Z` was exercised across the disc.** It was not. §C.
- **Not claiming anything about your packaging changes beyond our seam.** We
  checked the files we consume.
- **Not claiming the b15 changes are proven on hardware.** They are proven by the
  suite; the disc that ran was b14's.

---

*Sent with the rip's `.cue`, `.log`, `_EACcompatible.log`, `.platterpus.json` and
the auto-fix addendum — the artifact, not our description of it.*
