---
name: steward
description: DRAFT. Drive a Platterpus pull request to a green merge and keep main green after it. Use after opening or pushing to a pull request, after every merge to main, before any release is dispatched, at the start of a session, and whenever asked to watch, babysit or steward a PR. Judges a commit's checks with scripts/pr_steward.py (GREEN, FAILED, PENDING, BLOCKED, CANCELLED) and says what to do about each.
---

# Steward — DRAFT

**Status: DRAFT, owned by this repository** (the owner's word of 2026-11-03:
*"Be clear that you should own it, but the skill checker should give a
framework for you."*). The rules and the procedure below are Platterpus's and
change with this repo, in the same commit as whatever they describe. The
claude-code-skills checker supplies the framework: where a skill lives, its
frontmatter, how it is checked. When that framework changes, change this file's
shape to match and keep its content.

**Where it lives:** `.claude/skills/steward/`, the folder a session driving a
pull request looks for (or `babysit/`); the fork's is at the same path. It was
first written under `pr-steward/`, where no session found it (the owner,
2026-11-03). The script keeps its name, `scripts/pr_steward.py`.

## Why it exists

On 2026-11-02 `main` went red twice after a merge and nobody saw it for hours:

- the CI run on #420's merge commit, where a test had left a real window on
  screen and a later test on the same worker read it;
- `appimage.yml` on every merge from #420 to #422, where appimagetool's
  floating `continuous` build refused the AppDir. A release cut then would have
  failed.

Both were found by chance. The waits written by hand in between got three
things wrong: a run **cancelled** by a newer push was read as a **failure**; the
number of checks to wait for was a constant that went stale when a job was
added; and a check the ruleset **requires** but no workflow runs any more
(`test (py3.11)`, once the 3.11 leg left the matrix) blocked a merge with
nothing saying so. `scripts/pr_steward.py` now decides those three by rule.

## The one command

```
python3 scripts/pr_steward.py --pr <N>                # a pull request's head
python3 scripts/pr_steward.py --sha <merge sha>       # main after a merge
python3 scripts/pr_steward.py --sha <sha> --logs      # and every failure line
```

It reads the required checks from the branch's ruleset, every check run on the
commit, and every workflow run for it, all from the GitHub API. The worst state
wins, in this order:

| verdict | exit | means | do |
|---|---|---|---|
| `FAILED` | 1 | a check failed or timed out, required or not | `--logs`, reproduce, fix (below) |
| `BLOCKED` | 3 | a required check never reported, and every workflow has finished | the ruleset names a job that does not run: the owner's change |
| `CANCELLED` | 4 | the newest run of a required check was cancelled | a newer push superseded it: judge the newest head |
| `PENDING` | 2 | something is queued or running, and nothing above | wait, without a tight loop |
| `GREEN` | 0 | every required check passed, and nothing failed | merge, then judge `main` |
| (none) | 5 | the API could not be read | no verdict; try again, and never report green |

## The loop

1. **Find the commit.** For a pull request, its head (`--pr N` does this). After
   a merge, the merge commit on `main`: a merge makes a NEW commit, and CI starts
   again on it. The PR's own green run says nothing about it.
2. **Judge it** with the command above, and act on the verdict:
   - **`GREEN` on a PR:** merge it with a merge commit, never a squash
     (`merge_method: merge`), when the work is in scope and nothing below needs
     the owner. Then go to step 3.
   - **`PENDING`:** wait for it to change, without polling every few seconds:
     a background `until python3 scripts/pr_steward.py --pr N; [ $? -ne 2 ]; do
     sleep 60; done` (one notification when it ends), or `subscribe_pr_activity`
     for the PR's events. A test leg takes about five minutes; the whole CI run
     about six.
   - **`FAILED`:** run `--logs` and read **every** failure line, not the last
     one. Reproduce the named tests locally, read pytest's own exit code, and
     fix the pattern. **Never re-run hoping it is noise** (the owner's rule):
     a flaky test is fixed in the test, as TASKS R90 was. A failure that is not
     ours (a floating external tool) is still ours to fix: pin it, as
     appimagetool was (Critical rule #11).
   - **`CANCELLED`:** usually a newer push to the same branch, since CI cancels
     a pull request's superseded runs. Judge the newest head instead. Batch
     commits before pushing, because each push cancels the run before it.
   - **`BLOCKED`:** name the check. Only the owner can change the ruleset, so
     put it in the HANDOFF's `ASK:` with the exact steps: open
     `https://github.com/rmccann-hub/Platterpus/settings/rules`, the `main`
     ruleset, *Require status checks to pass*, and remove or add the named check.
     A new job can be added only after it has run once.
   - **No verdict (5):** the network or the API failed. Try again later; say so
     if it persists. An unread answer is never green.
3. **After every merge, judge `main`'s merge commit** the same way, until every
   workflow run for it has finished: `ci.yml`, **and** `appimage.yml` and any
   other workflow that runs on a push to `main`. A red `main` comes before
   everything else in the session. Then recreate the session branch from it:
   `git fetch origin main && git switch -C <branch> origin/main`, and push, since
   GitHub deletes a merged head branch.
4. **Before any release** is dispatched, `main`'s merge commit must be `GREEN`
   here, because `release.yml`'s CI gate reads that commit's runs. Releases are
   held until the owner says otherwise (`CLAUDE.md`): this skill never
   dispatches `release.yml`; it says when the commit is ready.
5. **While anything is open**, keep a check-in armed (`send_later`, about an
   hour out) so a hung run or a missed event is noticed; when it fires, judge
   again and re-arm. A check-in that finds nothing new messages nobody. Stop
   when the PR is merged and `main` is green, or the owner says stop.

## Rules this repo already holds

From `CLAUDE.md`, restated here only where the loop depends on them:

- Every PR merges with a merge commit; nothing pushes to `main`; no force-push,
  no branch delete, no tag push (the git proxy refuses them anyway).
- The required checks are whatever the ruleset says today: read them, never a
  list in prose. `release.yml` keeps its own list of checks a release needs, and
  `tests/test_ci_workflow_shape.py` holds it to `ci.yml`'s matrix.
- A local run is read by pytest's own exit code (`scripts/check.py` reports it),
  never through a pipe, and every `FAILED` line is named.
- Commit and push before ending a turn (the stop hook asks), and end each reply
  with the HANDOFF block.
- `git add` new files BEFORE the last local full run. Several sweeps read only
  tracked files (the doc-stamp footer check, for one), so a run with a new file
  untracked passes and CI fails: PR #425, 2026-11-03, on this file's own footer.

## What goes to the owner

Only what the owner keeps (`CLAUDE.md` → *Reporting to the operator*): a change
to a ruleset or a repository setting; a release, or lifting the hold; a hardware
run; a protocol override. Everything else this skill does without asking.

## Known limits of this draft

- A commit is judged against the ruleset as it is **now**. An old commit made
  before a job existed reads `BLOCKED` for it (`33573022` reads `BLOCKED` for
  `ui-conformance`, which was added a merge later). Judge the newest commit.
- It needs `api.github.com`. `GITHUB_TOKEN` or `GH_TOKEN`, when set, raises the
  rate limit; without one the unauthenticated limit applies.
- It does not merge, comment or re-run anything: it reads and reports, and the
  session acts.
- It does not read the cyanrip fork. The handshake reads at session start and
  before each turn ends (`CLAUDE.md` → *The sessions read each other directly*)
  are separate.

## What the framework should supply

Asked of the claude-code-skills checker, which owns the framework:

1. The marker a draft skill should carry, in place of the `DRAFT` word in this
   file's description and title, and what a skill needs to stop being a draft.
2. Whether a steward belongs in each repository, as this one is, or as one
   shared skill each repository configures with its own rules.
3. How a skill's script and tests are checked beside the skill: here
   `tests/test_pr_steward.py` holds the script to this file's verdict table.

---

*Last updated for Platterpus v0.7.116.*
