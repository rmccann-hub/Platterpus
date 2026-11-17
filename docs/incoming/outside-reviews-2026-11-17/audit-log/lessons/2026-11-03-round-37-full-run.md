LESSONS-FROM: rmccann-hub/claude-code-skills · CYCLE: round 37's Full run, 2026-11-03 · 2026-11-03T07:13Z

# What the 2026-11-03 Full run taught us

Written 2:13 AM EST, Tue Nov 3 (2026-11-03 07:13 UTC), from the run's bundle (553 passed, 0
failed), five independent reviews of it, and both repositories at their current heads.

## The main lesson, for all three of us

**A green run isn't a correct one.** Track 5 was wrong in every rip and track 3 in four, and the
run passed: the graders could fail only on what was missing, never on what was wrong. The
fix is the same in every repository: plant the defect and check that a test fails. The fork does
this for its Python tests; Platterpus's mutation sweep covers 15 product modules and no grader;
this repository's tests do plant a defect for each check (`tests/test_checks.py:448`, a hidden
character that must fire), but nothing mutates `skillcheck`'s own code to see the tests fail.

## claude-code-skills (this session)

- **Agents' findings were checked before they went out.** The coverage audit's top claim and the
  bundle review's two accuracy claims were each confirmed in source or in the run's files. Keep
  doing it; one agent's "P4 runs before P5" was true of the tested build and already fixed on
  `main`, which only a second look at the current head showed.
- **My EAC plan of record (2026-10-26) had two wrong claims:** "no change to secure mode after
  beta 3" and "closed, obfuscated signature". The installer's own changelog and OPS's open source
  disprove both. A claim drawn from one source is marked as such, or checked against a second.
- **A module sat two characters under its size limit,** with a review due to add to it. It's now
  13,020 (#110). Leave room before a known addition, not after.
- **Skills gap:** nothing in this repository teaches "a grader that can't fail". The planned
  `testing-patterns` module (ROADMAP) should open with it: plant the defect, replay the check.
- **Review-loop gap:** the laps crossed twice in round 37 (two lap 4s, two lap 5s). Draft #73,
  the `review-loops` skeleton, should carry the rule that ends it: one side holds the turn, named
  in the last lap, and a lap written out of turn is held, not sent.

## Platterpus

- **Its own EAC-layout log said WRONG; its report, window and notification didn't.** One verdict,
  computed once, should feed every surface.
- **Its estimate threw away what it measured,** so the operator was told 6 h 40 min for a 2 h 22
  min run. A figure the app learns should survive a rescan.
- **Good:** the cancel, the drive-open proof, the paired rips (P6) and the overwrite prompt all
  held on hardware, and P6's design separated "the build" from "the read path".

## The fork

- **Footers that count against the whole disc** ("0/14" for an offset search) and "Ripping errors:
  0" under "read with errors" undercut a log people trust.
- **Good:** the cache probe now agrees with cd-paranoia (128 to 255 against 144 sectors, where it
  read "at least 2048" for sixteen runs), and the offset finder confirmed +667 on 14 tracks.

## The owner, with us

- **The run's bundle reached this session first;** neither repository has it filed yet, and both
  need it to close the round. When a run finishes, the bundle goes to all three at once.
- **Five parallel reviews cost a lot of usage.** They found what one would have missed (C1, A4),
  but a smaller set will do for a run that changes less.

## Where we can be more consistent

| | claude-code-skills | Platterpus | The fork |
|---|---|---|---|
| **A check that can't fail** | a planted defect per check; no mutation run | graders unmutated | planted defects for Python tests |
| **Held messages** | a file the owner sends, with its condition | `READY-TO-READ: no`, merged to `main` | released by its session for laps that move no pin |
| **Run records** | `audit-log` | `evidence`, not yet holding this run | `evidence`, not yet holding this run |
