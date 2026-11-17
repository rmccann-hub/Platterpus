STANDARD-PROPOSAL-FOR: the owner of rmccann-hub/claude-code-skills · 2026-11-03T02:10Z

# Three additions to the standard, for your yes or no

Written 9:10 PM EST, Mon Nov 2 (2026-11-03 02:10 UTC). Nothing changes until you answer. If you
say yes, they land together as standard 0.49.0, in a pull request of their own, before the next
skills release. The standard is the PROJECT-BOOTSTRAP-AND-AUDIT file; it sets up and audits every
repository, so these reach Platterpus and the fork at their next audit.

## A. What a repository keeps, and where (dimension 10)

Built from your words of 2026-10-29, in `docs/decisions.md`.

- **The rule:** every repository decides, on purpose and in writing, where it keeps what's
  finished but worth keeping. The decision is consistent across repositories, and identical where
  that serves. Any difference is deliberate, recorded with its reason, and obvious to a reader.
- **Four questions each repository answers:**
  1. What does its own record need?
  2. What would an outside reviewer want?
  3. What do partner repositories need from it?
  4. What is worth keeping but doesn't belong on the main branch?
- **Main** carries what a new release is expected to carry: what users, end users, developers,
  agents and partner repositories read. It's never pared to nothing.
- **An auxiliary branch** holds records, archives, communications and old builds' logs. It's
  add-only and protected, and indexed by a manifest on the main branch. Each item is named or
  tagged by version, release or date. When in doubt, keep it there; it can be pruned later.
- **The model:** the evidence agreement two audited repositories already share. That's an orphan
  `evidence` branch, add-only and protected, with a manifest on the main branch.
- **Audit rows:**
  - no recorded answer to the four questions: `GAP`;
  - archives on the main branch with no recorded reason: `DRIFT`;
  - an auxiliary branch that isn't protected, or has no index on the main branch: `GAP`;
  - finished records deleted rather than kept: `GAP`.
- **Three defaults, unless you say otherwise:**
  - folders named by date and build count as "tagged", since tagging an evidence branch would
    break its hash citations;
  - each auxiliary branch gets a README at its root saying what it holds;
  - laps and documents a checker reads stay on the main branch.
- **For this repository:** `AGENTS.md`'s "deleting what moved" becomes "moving it to the archive
  branch", and the audit kit moves there from `audit-reports`' `audit-log` branch.

## B. How long CI and a release's tests take (dimension 6)

From your word of 2026-11-03: "This should also be something under your purview when asked to
set up a new repo, or audit and existing."

- **At setup:** the starter CI follows `git-workflows`' `ci-speed` module. That means cancelling
  superseded pull request runs, caching, timeouts on every job, and fast checks before merge.
- **At audit:** record how long a pull request's CI and a release's tests take, and apply
  `ci-speed`'s audit rows.
  - Slow CI with no recorded reason: `GAP`.
  - A suite weakened to save time: `DRIFT`.
  - The module's guide is about ten minutes before merge, with slower suites after.
- **The case behind it:** one audited repository's CI took 18 to 43 minutes, and fell to 6 to 8
  once it was looked at.

## C. A steward skill where agents drive pull requests (dimension 6)

- **At setup and audit:** a repository whose pull requests agent sessions open or merge keeps
  `.claude/skills/steward/SKILL.md`, written against `git-workflows`' `pr-stewardship` module,
  and the audit applies that module's rows.
- **The case behind it:** a hold sent as a message arrived after a merge. One repository put its
  steward under a name sessions don't look for.

## Your answer

A yes or no for each, such as "A yes, B yes, C yes", with any change you want. For A, also say
whether the three defaults stand.
