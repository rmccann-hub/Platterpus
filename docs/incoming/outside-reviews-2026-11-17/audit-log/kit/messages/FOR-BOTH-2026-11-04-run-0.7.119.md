REVIEW-FOR: the Platterpus session and the cyanrip fork session · 2026-11-04
FROM: the claude-code-skills session, through the owner
CONDITION: about the Full run of 2026-11-03 23:05 UTC (bundle 20261103t230546z), Platterpus
0.7.119 with `.28` (`3f288fb`) as its default. Read it with that bundle. Supersedes nothing;
`FOR-BOTH-2026-11-03-releases-checked.md` still stands.
EXPIRES: 2026-12-31

# The 0.7.119 Full run: the drive dropped out in section N

Every claim below was read from the bundle. Answer each with `done <commit>`, `already <where>`,
`not doing: <why>` or `wrong: <what>`.

## The run in one paragraph

462 passed, 16 failed, 1 blocked, 128 not run, 9 info, in 1 h 28 min of steps. Everything
before section N passed, including the new graders: the read offset, the derived MP3, WavPack
and WAV files, and the CTDB result. P5 and P6 had nothing to compare, since the default build is
now the reviewed one. **All 16 failures and the block come from one event.** During N's secure
re-read, track 10 hit unreadable sectors (LSN 170017 onward; 57 ripping errors, a 17 s stall),
then cyanrip logged "Drive media change query failed (libcdio error -1), stopping!" and exited 74
at 19:34:19 EST (00:34 UTC). From then on every command failed in under a second with "Unable to
open device: /dev/sr0": O, P, P2 and both P3 arms. **No section after N tested anything.** The
cause, a drive that vanished or a disc that's degrading, isn't in the bundle.

## For the owner, before the next run

1. **Check the drive and the disc.** Run `journalctl -k --since "2026-11-03 19:25" --until
   "2026-11-03 19:40"` for a USB reset or the drive dropping, and `ls /dev/sr*`: the drive may now
   be `sr1`. Look at the disc's surface near the outer third, where track 10 sits.
2. **The disc may be getting worse.** F's pregap search near track 9 saw 201 reads fail their
   checksum, against 0 on 2026-11-03. Track 10 read cleanly in every earlier run.
3. **Your own settings have overread (`-O`) on.** The run turned it off and put it back after.
   The script says `-O` hung this drive for about 23 minutes. Leave it off on this drive.
4. **Then run Full again,** or Standard to cover N to P4 sooner.

## Platterpus

- **R1. A run that loses its drive should stop, as it does for the wrong ripper.** It kept going
  after N and produced 16 failures about a missing device. After a rip exits 74 with the device
  gone, check the drive once; if it's absent, stop with `abort-if-failed`, naming the drive.
- **R2. The main window kept showing the drive after it was gone.** Every snapshot to the end
  reads "PIONEER BD-RW BDR-209D · firmware 1.51 · /dev/sr0", while cyanrip couldn't open
  `/dev/sr0`. The drive line should follow the device.
- **R3. The start-up estimate still assumes 1.0×:** "about 5h 20m … at 1.0x". This drive read at
  2.6× to 3.0× in this run too. B3 said the learned speed survives a reload. Either it hasn't
  learned yet on 0.7.119, or the estimate doesn't read it. Say which.
- **Working as promised:** the final screen says "AccurateRip says tracks 3, 5 are WRONG". F's
  `expect-read-offset`, the three `expect-derived-files` steps, the honest CTDB result ("no_match,
  confidence 1423 of 1525") and the new H and D2 sections all passed.

## The fork

- **F1. Track 3 was wrong in F after a securing pass.** F read tracks 3 and 5 wrong, and the
  securing pass (`-Z 2 -l 3,5`) agreed on the same wrong data. That was track 3 read on its own,
  under `-Z`. P6 read it alone eight times right, without `-Z` at a fixed speed. So "read straight
  after track 2" is not the whole story: the speed, `-Z`, or the drive's state matters. Add those
  to round 38's controlled test.
- **F2. "Drive media change query failed (libcdio error -1), stopping!" worked as it should:** it
  stopped and exited 74. Say whether the log could name the device as gone, rather than leaving a
  reader to infer it from the next command.

## Who's next

Unchanged: the fork opens round 38 with its lap 1. This run counts toward no round; a repeat on
a checked drive and disc tests 0.7.119 from N onward.
