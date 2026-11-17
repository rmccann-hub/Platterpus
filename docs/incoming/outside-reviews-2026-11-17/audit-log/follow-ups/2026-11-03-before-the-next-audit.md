FOLLOW-UPS-FROM: rmccann-hub/claude-code-skills · 2026-11-03T00:30Z

# Before the next audit

Written 7:30 PM EST, Mon Nov 2 (2026-11-03 00:30 UTC), after a quick look at both repositories.
Nothing in either was changed.

## The owner's asks of the repositories, as found

- **Dependencies brought up to date:** the fork merged "Update every pin to its newest release"
  (#77). Platterpus merged mypy 2.4 and ruff 0.17 (#424); its Python 3.12 floor, numpy 2.5 and
  the AppImage on Python 3.14 are in #425, open and marked breaking, which also carries round 37
  lap 4.
- **Faster tests:** the fork's CI on `platterpus-fork` fell from 18 to 43 minutes (2026-10-26 and
  27) to 6 to 8 (#76, "Spend less time waiting on CI and the suite"). Platterpus's CI on `main`
  runs 6 to 10 minutes, and its release workflow under 3.

## For this repository, from the owner's word of 2026-11-03

- **Test and CI speed is ours to check, at setup and at audit:** "This should also be something
  under your purview when asked to set up a new repo, or audit and existing." `git-workflows`'
  `ci-speed` module covers it, with its own audit rows. Before the next skills release, confirm
  that the standard's setup and audit both send a session to it, and that it covers a release's
  test time as well as a pull request's.
- **The next audit** waits for round 37 to close (its Full run on `.28`), #425 merged and green,
  and the next skills release, so it tests the archive rule and this one too.
