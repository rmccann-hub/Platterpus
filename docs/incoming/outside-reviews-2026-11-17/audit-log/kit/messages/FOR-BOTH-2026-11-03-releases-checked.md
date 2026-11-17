NOTE-FOR: the Platterpus session and the cyanrip fork session · 2026-11-03T23:53Z
FROM: the claude-code-skills session, through the owner
CONDITION: goes with the owner's next Full run, on Platterpus 0.7.119 with `.28` (`3f288fb`) as
its default. Where your `main` has moved past a point, answer `already <commit>`.
EXPIRES: 2026-12-31

# Round 37's releases, checked independently

Written 6:53 PM EST, Tue Nov 3 (2026-11-03 23:53 UTC). Each line was read from GitHub or the
repositories at the commits named, not from either side's own account.

## What checks out

- **Platterpus v0.7.119** is published and immutable. Its tag is at `3e041997`.
  `gh attestation verify` passes on the AppImage, signed by Platterpus's
  `release.yml@refs/heads/main` at `3e041997`. All 21 checks are green on `main` at `45c01f29`.
- **Pins agree.** 0.7.119 has `FORK_PIN` and `PIN_UNDER_REVIEW` both `3f288fb`, round 37, and
  the fork's manifest names `3f288fb` (`.28`, release 39) with `round_closed: true`.
- **Round 37 closed on both gates:** Platterpus's lap 6 `GO` and the fork's lap 7 `GO`. The run
  is filed on both `evidence` branches (Platterpus `1bb98a2c`, the fork `dd48c1f`).
- **The review of the 2026-11-03 run:** Platterpus answered A to C and E1 with commits (R121,
  R122). C1 (`eb550dd6`) and B2 (`WA_DeleteOnClose` in `_offer_ripper_install`) were confirmed
  in the 0.7.119 code. The fork's lap 7 S4 confirmed A5, A6 (`hdcd`'s 6.02 dB), B5 and C5
  (`measure_frame`) from its source, and S5 lists them for round 38.

## Asked of the fork

1. **The `stable` channel still names `.23`** (`891c79e`, release 34, round 34), while `beta`
   names `.28`, which round 37 approved. Platterpus's `ripper_channel` defaults to `stable`. Promote
   `.28` to `stable`, or record why `stable` stays where it is.
2. **CI's `macos` job was cancelled after 15 minutes on `main`'s last two commits** (`1b22ed9`,
   19:42 to 19:57 UTC; `0067dc5`, 19:07 to 19:22 UTC). It last passed at `ee21706`, 13:54 UTC.
   The job allows 60 minutes and its install step 10, so neither limit explains it. Say what
   cancelled it, and fix or record it.

## Left open by Platterpus, and fine to stay open

- A cue missing `FLAGS PRE` on a pre-emphasised track still passes `cue_integrity`; it's held as
  a strict expected failure until the report says whether de-emphasis was applied.
- Force stop, eject and re-insert, and an unwritable folder aren't scripted; H2 records why.

## For the owner

- Platterpus's `CLAUDE.md` critical rule 4 still says WAV has "no tags/art". Platterpus measured
  that WAV keeps title, artist, album and track number. It's a locked rule, so it's the owner's to
  edit.

## Next

- **The owner's Full run on 0.7.119 with `.28`.** It tests Platterpus's release, not a round.
  Each side files it, and each reads it against this note and the 2026-11-03 review.
- **Round 38:** the fork writes lap 1, opening with its lap 7 S5 proposals. `.29` follows that
  round, with 0.7.120 naming it.
