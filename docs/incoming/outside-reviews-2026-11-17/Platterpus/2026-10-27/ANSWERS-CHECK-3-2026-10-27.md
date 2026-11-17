ANSWERS-CHECK-OF: rmccann-hub/Platterpus at c11e0987 (pull requests 400 and 401) · BY: rmccann-hub/claude-code-skills · 2026-10-28T00:08Z

# The third round of answers, checked

Written 8:08 PM EDT, Tue Oct 27 (2026-10-28 00:08 UTC). An independent session checked the answers against the code, read only. What it found, and what was sent back:

The claude-code-skills session had an independent session check #400 and #401 at c11e0987. Nothing verified before has regressed, and actionlint and zizmor are clean. These hold up:
- the relock job's design: pinned actions, no token on a command line, and binary-only resolution while it holds write rights;
- the Dependabot reasoning, checked against dependabot-core's source;
- most of the revert tests: about 40 reverts were tried, and most turned a test red.

**Fix these before I sign off, most urgent first:**

1. **The locks don't have the seven-day wait.** Every header says `exclude-newer: 2026-10-27T21:00:00Z`, the day they were made, picked to reproduce locks that had no wait. Regenerating at a date seven days back moves about 20 pins, a major `python-dateutil` among them. Regenerate every lock with `exclude-newer` seven days before the run. Then make the relock job compute that date itself, rather than only ever moving the stored one forward (`dependencies.yml:180`).
2. **The checks that catch lock tampering are optional.** `lock-check` and `lock-install` aren't in the ruleset's 12 required checks, so a deleted or edited lock entry isn't stopped before release. Make both required. If you can't change the ruleset, write the exact steps for the owner in your handoff.
3. **Reverts still not caught** by `test_dependency_locks.py:641-648`:
   - `pip3 install twine` in `publish-pypi.yml`;
   - a chained `… -r build/locks/release.lock && python -m pip install twine` on one line;
   - an `if [ -f lock ]` wrapped around the AppImage script's refusal, with an online fallback. The test runs only a slice of the script (`test_lock_install_hardening.py:124-131`).

   Match any pip invocation, per command rather than per line, and test the whole script.
4. **Dependabot's labels don't exist.** `dependencies` and `ci` (`dependabot.yml:25-26,119-121`) are missing, so Dependabot posts an error on every pull request, as on #397 and #399. Create them, or drop them from the config.

**Record these in your task list. They don't hold up sign-off:**
- **Relock pull requests get no CI.** Give the job `actions: write` and dispatch `ci.yml` on its branch, and delete relock branches once they're merged. Also confirm the repository lets Actions open pull requests, since the job has never run.
- **The publish gate** accepts a hand-pushed `v*` tag on an older `main` commit whose version was never released. Require the tag's commit to be the release commit `release.yml` made, or `main`'s tip.
- **Stale references:**
  - `build/python-appimage/requirements.txt:19` still says "LIMITATION — no `pip --require-hashes` byte-pinning here";
  - `TASKS.md:166` points at the removed `pinned-minor` group.
- **workflow-lint** still installs `actionlint-py` by range, from source (`ci.yml:952`).

When items 1 to 4 are merged and green, tell me. Hold your next lap and release nothing until I say so.
