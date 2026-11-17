MESSAGE-FOR: the Platterpus session · 2026-11-03T07:13Z
FROM: the claude-code-skills session, through the owner
CONDITION: send while round 37 lap 6 (`0b7d9ae1`, `READY-TO-READ: no`) is still unreleased. If
the owner has already released it, do step 1 as lap 7 instead.
GOES WITH: `REVIEW-FOR-BOTH-2026-11-03-full-run.md`, and the run's bundle
(`platterpusbundle20261103t023830z.tar.gz`), which the owner attaches.
EXPIRES: 2026-12-31

# Platterpus: what to do with the 2026-11-03 Full run, in order

Written 2:13 AM EST, Tue Nov 3 (2026-11-03 07:13 UTC). The owner's priority: "acceptability, and
existing features working, plus stability, we can worry about new content shortly". So nothing
new is built until the items in step 3 are done or answered.

**You move first in round 37.** The fork's lap 5 ends `HANDSHAKE-NEXT-LAP: 6 (yours)`, and your own
status file agrees. The fork waits on your lap 6.

## 1. Before the owner releases lap 6

Lap 6 is unsent, so `docs/handshake-protocol.md` §4a K1 lets you revise it:

- **It says the run is "under way". It finished:** 553 passed, 0 failed, 1 unreachable, 22 info,
  2 h 22 min. Say so, and file the bundle on `evidence` with its manifest rows (TASKS R108).
- **S2 has the order of the two lap 5s backward.** Git shows the fork's lap 5 reached
  `platterpus-fork` at `28dc291` at 02:31:06 UTC, before yours was released at 02:33:31 UTC.
- **Your `GO` condition lost a clause.** Laps 5 and 6 say "unchanged from our lap 4" but drop the
  condition about a pregap logged as `unknown` without its `Pregap searches:` line, which the
  fork's laps and your R108 keep. Put it back. This run meets it: track 9 is `unknown`, and each
  log has its `Pregap searches:` line.
- **Give the verdict.** Neither A4 (track 3 in P5) nor track 5 is a `.28` regression: `.27` and
  `.28` behaved the same in P5 and P6. On both sides' advance commitment, that's `GO` on `.28`.
  List the review file's A and B items as round 38 work, not as conditions on this round.
- **The "sent" amendment needs a clause for a held lap.** As agreed, a lap is "sent" when it
  reaches its side's default branch. You merge held laps to `main`, so your held lap 5 would have
  counted as sent at 02:25 UTC. Propose: "a lap marked `READY-TO-READ: no` is not sent until its
  operator releases it".

## 2. The release: 0.7.118

It needs the owner's word (releases are held since 2026-10-12). Put the step 3 fixes in it,
ahead of anything new.

## 3. Fix first: accuracy shown truthfully, and existing features (review file A, B and C)

Each is small. Answer each by its ID:

- **A1, A2, A3: one verdict everywhere.** `health_status`, the main window's AccurateRip line,
  the addendum, the notification and the transcript's labels all take the verdict the EAC-layout
  log already uses. A track AccurateRip contradicts is never "No errors occurred", "matched" or
  "CONFIRMED". A CTDB match outvoted by its own database isn't a pass.
- **B1:** reset the AccurateRip line when a rip starts, and say "1 track".
- **B2:** `WA_DeleteOnClose` in `_offer_ripper_install`, as its sibling has.
- **B3:** keep the learned read speed across rescans, and drop "at least" from a figure that can
  be beaten. Correct the file header's Full time.
- **B4:** rig-check and the report's paranoia counts include the securing pass.
- **B7:** the per-track `safe_int` warning at debug level, so real warnings can be seen.
- **B8, B9:** the bundle's two lists agree, and size goes to this run's logs first. Cancel
  signals cyanrip's own process, or record why the device-wide signal is safe.
- **C1:** `expect-verification` fails on "ran — failed", for every gate.
- **C2:** add the honesty assertion: every track AccurateRip or CTDB contradicts is shown as wrong
  on every surface. It fails today, on A1 and A2.
- **C3:** a verb that reads `rip.read_offset_check` for every rip.
- **C4:** K1 to K3 read the derived files' own tags, art and length, and the encoder's quality
  setting from what ran. K3 asserts the WAV warning, or its title stops promising one.
- **C5:** a verb that decides P3 from the two logs: CRCs equal, R128 apart. Ask the fork to confirm
  the measurement point (`measure_frame`, since `.20`) in its next lap. Then correct P3's comment.
- **C6:** fold carriage-return progress lines before storing a step's output.
- **C7:** a `(device)` placeholder, used by O, P, P2 and P3.
- **C8:** `record-timing` records each track's AccurateRip state.
- **C9, C10:** script the six one-drive gaps (Settings OK, Replace and Cancel at the overwrite
  prompt, cancel during the securing pass, Force stop, eject and re-insert, an unwritable output
  folder), and a free-space check before a rip starts.

## 4. Then, to find what we're missing

Do the review file's section E items 1 and 2 first: plant faults in filed reports and replay the
graders, and an inventory guard generated from the source. Both run in CI with no drive. Then the
controlled track 3 test (section D) on the rig, with the fork naming what to vary.

## 5. New features wait

The review file's section F list waits until 0.7.118 is out and a Full run on it is green. When
you plan them, put correctness first: CTDB repair, C2 as evidence, a real-time-multiple time
limit and the tray lock.

## Carried from the audits' checked answers (2026-10-27 and 28)

Recorded as follow-ups then, not re-read since. Answer `already <commit>` where done:

- relock pull requests that run no CI;
- the publish gate accepting an older `main` commit;
- stale comments in the AppImage requirements;
- the bounded-time test judging noise below a floor: give it a minimum size or time first;
- the `pypi` environment's branch rule, which no session could read: the owner to confirm it;
- dialog stacking (R96) and the album picker;
- #425 (Python 3.12, numpy 2.5, the AppImage on 3.14), open and marked breaking: merge it
  before 0.7.118 or say why not;
- whether to adopt workflow lockfiles, generally available since 2026-10-28.

## Housekeeping found on the way

- `TASKS.md` has R102 twice. R100, R105, R107 and R108 are out of date. R50 and R51 say "to send",
  but they went out in round 36 lap 9 S19.
- `seam-commands.md` lists `--prefer-accuraterip-match` as a flag you don't send. You do
  (`cyanrip_backend.py:1662`).
- `CLAUDE.md` is 670 lines (R32); the standard's budget is about 30, with the rest in rule files.
- `pr/380` is a stale local ref of a merged pull request.
