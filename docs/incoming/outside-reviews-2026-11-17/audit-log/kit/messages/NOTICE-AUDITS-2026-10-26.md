NOTICE-FROM: rmccann-hub/claude-code-skills · FOR: Platterpus and the cyanrip fork · 2026-10-26T22:34Z

# How audits will run, from now on

Written 6:34 PM EDT, Mon Oct 26 (2026-10-26 22:34 UTC), on the owner's decision of that day.
Nothing to do now: this says how the audits the owner starts will work, so they surprise no one.

**What an audit is.** A check of your repository with the claude-code-skills skills: the
PROJECT-BOOTSTRAP-AND-AUDIT standard for setup, CI, dependencies and context files, and the
`coding`, `git-workflows` and `house-style` skills for code, workflows and prose. It's also a test
of those skills: where one was wrong, unclear or silent, that's a finding about the skill.

**The rules.**

1. **An audit judges the tip of your default branch,** whether or not a release is due: `main`
   for Platterpus, `platterpus-fork` for the fork. Work still on another branch waits for the
   next audit. Merge what you want audited before the owner starts one.
2. **The owner starts it, in a new session** in your repository, never in the session working on
   your laps. That session reviews only: it changes, commits, pushes and releases nothing, and
   opens no pull request or issue.
3. **It writes two files, and commits neither:** the findings (`AUDIT-<date>.md`), and feedback
   on the skills alone (`SKILL-FEEDBACK-<date>.md`), with your repository's name, code and
   findings left out. Both go in your ignored working folder, or as a file to download. Findings
   stay with the owner until they're fixed: none goes in a commit, an issue or a pull request.
4. **The owner carries both files** to the claude-code-skills session. It grades the findings
   against what's already known, checks each one against your code, and brings the results to
   the owner first. Your true findings come back to you; what the skills got wrong gets fixed in
   claude-code-skills.

**What you'll see.** After the owner has read the results, a review file like the one of
2026-10-26, with one item per finding, each citing the file and line, answered as before:
`done <commit>`, `already <file:line, test>`, `not doing: <why>` or `wrong: <what you found>`.
