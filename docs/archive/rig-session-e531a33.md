# Rig session — round 39's five-rip run, `.31` (`e531a33`)

*Moved here from `docs/rig-session.md` on 2026-11-16, byte for byte below this note, once the round it served had closed (round 39 closed 2026-11-13). The current sheet is [`docs/rig-session.md`](../rig-session.md).*

## Round 39's five-rip run (run 2026-11-11; round 39 closed 2026-11-13)

*Kept as it was run: round 39 closed on both laps' `GO` (2026-11-13), so nothing below
is the next session.*

Round 39 reviews the fork's `.31` (`0.9.4-rc3+platterpus.31`, `cyanrip@e531a33`), whose
`--reread-until-accuraterip` keeps a `-Z` re-read going past reads that agree on audio
AccurateRip does not hold (track 3's `3D8FCF0C`). Platterpus 0.7.122 reads everything it
prints and sends it as `--reread-until-accuraterip 2` on the securing pass. The round
closes on the fork's lap 1 S16: five default whole-disc rips in a row of the reference
disc, each with all 14 tracks AccurateRip-verified and every track's record saying how
(G1 to G3), the C2 probe run and the `block_crcs` comparison filed (G4), and the owner's
EAC re-rip filed (G5).

1. **Platterpus 0.7.122 and `.31`.** Tools → Setup & Updates… → Check for updates, take
   0.7.122; then Tools → Setup & Updates… → Choose a build…, and pick the one labelled as
   the build under test, `.31`. Close Platterpus.
2. **The records the fork asked for (no disc, no drive), only if the rips of 2026-11-09 and
   2026-11-10 are still on the rig (the owner removed them on 2026-11-11, so skip this step
   unless you have them back): `bash
   ~/platterpus-rig/drivetest.sh records`.** It packs every ripper `--diagnostics` record in
   the rips folder since 2026-11-09 (JSON, never audio) and names one file; upload it to
   both sessions. It gives the fork track 3's per-second comparison before the five-rip run (their
   S9, S10). Fetch the script first if it is older than 2026-11-11: `curl -L -o
   ~/platterpus-rig/drivetest.sh
   https://raw.githubusercontent.com/rmccann-hub/Platterpus/main/docs/rig-scripts/drivetest.sh`.
3. **G4, with Platterpus closed and the reference disc in: `bash
   ~/platterpus-rig/drivetest.sh probe`**, and upload the one file it names. Ran once on
   2026-11-11 (filed by the fork at `cyanrip@74b6f0a`). Fetch the script again (the
   `curl` line in step 2) before running it a second time: since 2026-11-12 its C2 probe
   reads the four whole seconds the wrong samples sit in (track 3's 244, 251 and 252,
   track 5's 144), three windows each, three reads a window, plus the control: 40
   flushes and reads where the first run made 16, a few minutes more (the summary
   prints the time it took).
4. **The five-rip run: one Full acceptance run** (Tools → Advanced → Run acceptance test…, Full).
   Section A checks the installed build is `.31` and the pair is the newest; sections P5
   and P6 time and pair `.30` (the approved build) against `.31`; section R makes the five
   default whole-disc rips. Its bundle carries every rip's record, chase reads' included.
   Upload the bundle it names to both sessions.

G5, the EAC re-rip on Windows, is the owner's, and is filed beside the 11 and 25 June logs.

---

*Last updated for Platterpus v0.7.125.*
