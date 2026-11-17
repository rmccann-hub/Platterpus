FOLLOW-UPS-FROM: rmccann-hub/claude-code-skills · 2026-11-03T02:48Z

# Priorities, for the owner's goals

Written 9:48 PM EST, Mon Nov 2 (2026-11-03 02:48 UTC). The owner's goals, given to all three
repositories: fix every bug, make testing quicker, use the correct dependencies, reduce security
issues, give the best user experience, and match or improve on EAC's bit-correct output. Each
repository applies them in its own terms; for claude-code-skills, "correct output" is facts
checked at their sources and examples that run.

## claude-code-skills: done on 2026-11-03

- **Bugs and correct output:** `action-pinning` caught up with lockfiles' general availability
  (#106); the steward framework's one-person limit and `CODEOWNERS` rule (#105, #106); Vale's
  facts in `prose-check` moved with its pin (#108).
- **Dependencies:** every update past the three-day wait, in one batch (#108); nothing behind.
- **Security:** no known vulnerabilities in the Python lock or the npm tree; a live `hold`
  check (#107).
- **Testing:** CI on `main` runs in under a minute, so nothing to speed up.

## claude-code-skills: waiting on the owner

1. Merge #107, then #108, which is stacked on it.
2. Add `subjects` and `hold` to the default-branch ruleset's required checks.
3. Answer the standard proposal of 2026-11-03 (A, B, C), and the seven items of 2026-10-27's.
4. Say whether to delete the merged branches left on GitHub (about 17), and whether draft #73
   (review-loops, supply-chain-security, idle since 2026-10-21) is finished or closed.

## claude-code-skills: next, in order

1. After round 37 closes: its review, both repositories' steward files graded against
   `pr-stewardship`.
2. Apply the approved proposal as standard 0.49.0.
3. Split three modules within 10 characters of the 16,000 limit before any addition:
   `pr-stewardship`, and `house-style`'s `prose-check` and `writing-style`.
4. Release 0.1.25.
5. The full audit of both repositories, with 0.1.25.
6. Open design question: `releases-and-versions` isn't read, because `git-workflows`' rule 7
   answers release questions itself.
7. Consistency, for the audit: lockfiles or SHA pins; merge titles; times; commit subjects;
   releases and tags; where finished work is kept.

## Platterpus and the fork: for the next audit, by goal

Taken from the three rounds of checked answers and their recorded follow-ups, not from a new
reading of either repository.

- **Bit-correct output:** the Full run on `.28` with 0.7.117 is the round's proof. Then the
  open drive findings: track 3's read-to-read variance, track 9's pregap, and `-Z` converging on
  a read AccurateRip doesn't match. Each against EAC's log and CUE for the same disc.
- **Bugs:**
  - the fork's recorded items: TSan annotations around its own frame frees, `redact.py`
    mangling prose after `--acoustid-key`, no test of `fetch_image` without a declared size, a
    silent loss of hardening flags under clang;
  - Platterpus's: relock pull requests with no CI, the publish gate accepting an older `main`
    commit, stale comments in its AppImage requirements.
- **Quicker tests:** Platterpus's bounded-time test judging noise below a floor; the fork's
  stalled-mirror job, given a step timeout and retry.
- **Dependencies:** Platterpus's Python 3.12 and numpy 2.5 move (#425); whether either moves
  to workflow lockfiles now they're generally available.
- **Security:** the fork's AcoustID key from a file; Platterpus's `pypi` environment's branch
  rule, which no session could read.
- **User experience:** Platterpus's dialog stacking (R96) and album picker; plain log wording
  for the four new `.28` lines.
- **Their steward files:** graded against `pr-stewardship` at the audit.
