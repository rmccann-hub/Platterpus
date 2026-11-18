# GitHub Workflows & Version-Control SOP (reference)

> **How this applies to Platterpus.** This is a general, contributor-facing SOP
> for the GitHub ecosystem — most useful here as the **playbook for contributing
> *upstream*** (forking + opening PRs to `cyanrip`, `libcdio-paranoia`,
> etc. — see `docs/cyanrip-fork.md` Part A §10 and the upstream-PR roadmap).
>
> For work **on the Platterpus repo itself**, the authoritative rules live in
> **`CLAUDE.md`** and win wherever they differ from this SOP:
> - The cloud sessions use the **git CLI + GitHub MCP**, not GitHub Desktop.
> - The agent git proxy is **fast-forward-only**: **no force-push**, no branch
>   delete, no tag push (releases go via the `release.yml` `workflow_dispatch`).
> - Feature work goes on the **designated branch** the session is given
>   (e.g. `claude/…`), never a personal `username/…` branch.
> - We merge every PR to `main` with a **merge commit**, not a squash
>   (session branches since 2026-09-26, every PR since 2026-10-12, when squash
>   and rebase merging were turned off; §7.1 below says why).
> - `main` and the `v*` tags are protected by **repository rulesets** (since
>   2026-10-12; §7.2 below).
> - GitHub **deletes a merged head branch automatically** (since 2026-09-30), so
>   start the next change with `git switch -C <branch> origin/main`; the push
>   recreates the branch.
> - Commit subjects use **lowercase conventional-commit `type(scope):`
>   prefixes**, not §5.2's "Capitalize the subject" style, and there is **no
>   hard 50-char subject cap** (see CLAUDE.md → Commit & PR hygiene).
> - Never commit copyrighted media (Critical rule #8); commit trailers and the
>   model-identity rule are per CLAUDE.md.
>
> Read this for the *mechanics and etiquette* (identity, SSH, forking, branch
> naming, atomic commits, the 7 commit-message rules, PR anatomy, merge
> strategies, conflict resolution); defer to `CLAUDE.md` for *this* repo's policy.

---

## 0. This repository's commit and PR practice — `CLAUDE.md` *Commit & PR hygiene* in full (moved 2026-11-16)

`CLAUDE.md` keeps the rules that bite and wins wherever this file differs; the full text of its *Commit & PR hygiene* section, as it stood before the R32 trim, is here.

*Verbatim from `CLAUDE.md` at `3e2f194a` (Project operations → Commit & PR hygiene), moved here on 2026-11-16 when that file was trimmed to what a session needs on every task (`TASKS.md` R32). Inside it, “here” and “this file” mean `CLAUDE.md`, and “above” / “below” mean the neighbouring entries of that section; relative link targets are rebased to this file's folder.*

The general GitHub mechanics + etiquette live in
**[`docs/github-workflow-sop.md`](github-workflow-sop.md)** (identity/SSH, fork+PR, atomic
commits, the seven commit-message rules, PR anatomy, merge strategies, conflict resolution) — read
it for *upstream* contributions especially. **This section is the authority for *this* repo and wins
wherever the generic SOP differs.** What we actually do:

- **Atomic commits.** One logical change per commit — don't mix a fix with an unrelated refactor.
  Small, test-green units keep review, `git bisect`, and `git revert` surgical.
- **Conventional-commit subject:** `type(scope): imperative summary` — **lowercase** after the
  colon, no trailing period, concise (aim short, but the `type(scope):` prefix + a release subject
  legitimately run past 50 chars — clarity over a hard cap). Types in use: `feat`, `fix`, `docs`,
  `test`, `refactor`, `style`, `chore`, `release`, and `ci` and `build`, which the `commit-subjects`
  job also accepts. Blank line, then a body wrapped ~72 cols that explains **what and why, not how**
  (the diff shows how).
- **Required trailers** on every commit (per the harness rules): the `Co-Authored-By:` line and the
  `Claude-Session:` line. Never put the model identifier in a commit, PR, or any pushed artifact.
- **Changelog in the same commit** (Critical rule #7) — or a standalone `[skip changelog]` line for
  a pure historical-record commit. **The exemption is strictly that** (maintainer ruling,
  2026-07-21): contributor/CI-facing changes — type annotations, CI config, dev tooling, refactors —
  are **not** exempt and get a bullet like any other change; "pure historical record" means the
  commit changes nothing but the record itself (e.g. a session-log catch-up). CI backstops this.
- **Branch:** commit only to the session's designated `claude/…` branch; never push to `main`.
  Prefer `git switch` over `git checkout` for branch ops. **GitHub deletes a merged head branch
  automatically** (the repository setting, on since 2026-09-30), so after a merge the session branch
  is gone from the remote: start the next change with `git switch -C <branch> origin/main`, and the
  push recreates it.
- **Every PR merges into `main` with a merge commit, never a squash** (session branches since
  2026-09-26, on the maintainer's instruction that every branch be deletable without consequence;
  every PR since 2026-10-12, when the owner turned squash and rebase merging off).
  `git log --first-parent main` still shows one node per complete, deployable change. The reason is
  the citations: our laps, TASKS and session log cite session-branch SHAs, and the fork's laps cite
  them too. A squash puts one new commit on `main` and none of the branch's, so each citation lasted
  only as long as its branch. **47 had already been stranded**, held only by GitHub's
  `refs/pull/N/head`, which a plain clone does not fetch. They were brought back with
  `git merge -s ours` (history in, tree unchanged). `tests/test_cited_commits_are_reachable.py`
  turns `main` red if a squash strands one again, and its message names the repair. **Every pull
  request merges with a merge commit, Dependabot's included: squash and rebase merging are off in
  the repository settings** (the owner's decision, 2026-10-12). The `changelog` job's Dependabot
  exemption therefore keys on the pull request's author or its `dependabot/*` branch, and on a push
  to `main` on the commits the push brings in (every non-merge commit Dependabot's), never on the
  head commit's author, which a merge commit makes whoever merged
  (`tests/test_changelog_dependabot_exemption.py`). Merge only when CI is green — **all twelve gating
  jobs**: the `pytest` 3.12–3.14 matrix (coverage floor on 3.14), **`ui-conformance`** (since
  2026-11-02), `ruff` lint/format, `mypy`
  typecheck, the changelog check, media-guard, `pip-audit`, **`gitleaks`**, **`sbom`**,
  **`lock-check`** and **`lock-install`** (both required since 2026-10-28), and
  **`tests-touched`** (gating since 2026-08-20, and omitted from this list until 2026-08-27 — the
  same file said so under *CI / release* two sections above, so this was one document disagreeing
  with itself). Don't open a PR unless asked.
- **Deliberate divergences from the generic SOP** (do *not* "fix" these to match it): (1) we use
  **lowercase conventional-commit prefixes**, not the SOP's "Capitalize the subject" / no-prefix
  style; (2) no hard 50-char subject cap; (3) the agent git proxy is **fast-forward-only** — **no
  force-push, no branch delete, no tag push**; releases go via the `release.yml`
  `workflow_dispatch`, not `git push origin vX.Y.Z`; (4) personal `username/…` branches don't apply
  — the session branch is assigned; **(5) `main` and the `v*` tags are protected by repository
  rulesets** (the owner's decision, **2026-10-12**, replacing the decline of 2026-09-11, whose
  premise no longer holds: this repository is public, and on GitHub Free a public repository gets
  rulesets at no cost). A **default-branch ruleset** blocks deletion and force pushes and requires a
  pull request with **no approvals**, with these required status checks: `lint`, `typecheck`,
  `changelog`, `media-guard`, `pip-audit`, `gitleaks`, `sbom`, `tests-touched`, `test (py3.11)` to
  `test (py3.14)` (`test (py3.11)` left with the 3.11 leg, KDD-46), and, since 2026-10-28, `lock-check` and `lock-install` (14 in all, read from
  `GET /repos/rmccann-hub/Platterpus/rules/branches/main` that day), and since 2026-11-02
  `ui-conformance` (15 in all, read from the same endpoint at 22:48 UTC that day); read the live
  list rather than this one. A **release-tag ruleset** protects `v*`. A third, on the **`evidence` branch**
  (2026-10-14, HR-2 point 3), blocks its deletion and force pushes. What every session must keep
  true under them: every change lands through a pull request (it already does); nothing pushes to
  `main`, moves or deletes a `v*` tag, or force-pushes; **merge commits are the only merge method**
  (squash and rebase are off, 2026-10-12), so the ruleset must not require linear history, which
  would forbid the one method left; and the tag ruleset may block updates and deletions but **not
  creation**, because `release.yml` creates each tag as `github-actions[bot]`: since 2026-10-27 it
  pushes an annotated tag right before it publishes the draft (`--verify-tag`), where before it let
  GitHub create a lightweight one on publish. A Dependabot pull request that changes a dependency
  fails `test` **by design** (the generated `bom.cdx.json` goes stale, and `ruff`/`mypy` are pinned
  by rule #11): carry the bump on a session branch with the regenerated files and a CHANGELOG
  bullet, then close Dependabot's. The full check of what the rulesets touch: `PLANNING.md` KDD-43.
  Read their live state from `gh api repos/rmccann-hub/Platterpus/rulesets`, not from this sentence.
  (6) **merge commits, not the SOP's favoured squash** (see the bullet above): a squash strands
  every commit a lap cites once its branch is deleted.

## 1. Local system configuration & identity

### 1.1 Global identity + editor
Git bakes author metadata into every commit's hash; misconfiguration breaks
attribution and contribution graphs.

| Setting | Command | Intent |
|---|---|---|
| Name | `git config --global user.name "Firstname Lastname"` | Human-readable author on each commit. |
| Email | `git config --global user.email "you@org.com"` | Must match a verified email on your GitHub account to link contributions. |
| Editor | `git config --global core.editor emacs` (or `nano`, VS Code, etc.) | Editor for commit messages / interactive rebase (overrides the `vi` default). |
| Editor (Windows) | `git config --global core.editor "'C:/Program Files/Notepad++/notepad++.exe' -multiInst -notabbar -nosession -noPlugin"` | Full path needed on Windows; avoids hanging processes. |
| Default branch | `git config --global init.defaultBranch main` | New repos start on `main`, not `master`. |

Verify with `git config --list`. To force per-repo identity setup (avoid
committing with a personal email on a work machine): `git config --global
user.useConfigOnly true`.

### 1.2 Line-ending normalization
Windows uses CRLF, UNIX/macOS uses LF. Unmanaged, this produces "whole file
changed" diffs. Normalize with `core.autocrlf`:

- **Windows:** `git config --global core.autocrlf true` (CRLF on checkout, LF on commit).
- **macOS/Linux:** `git config --global core.autocrlf input` (LF untouched on checkout; stray CRLF → LF on commit).
- **Repo-enforced:** `git config --global core.autocrlf false` when a `.gitattributes` (`* text=auto`) governs it — best practice for shared repos.

### 1.3 SSH authentication (industry best practice)
DSA and pre-SHA-2 RSA keys are no longer accepted. Generate **Ed25519**:

```
ssh-keygen -t ed25519 -C "you@org.com"
# hardware key (YubiKey, etc.):
ssh-keygen -t ed25519-sk -C "you@org.com"
```
Accept the default path (`~/.ssh/id_ed25519`) unless juggling multiple
identities; set a passphrase (encrypts the private key at rest). Copy the
**public** key: `pbcopy < ~/.ssh/id_ed25519.pub` (macOS) / `clip <
~/.ssh/id_ed25519.pub` (Windows). Then in the web UI: **profile → Settings →
Access → SSH and GPG keys → New SSH key**; give it a device-specific Title; Key
type = **Authentication** (repeat with **Signing** if you'll sign commits with
it); paste; **Add SSH key**. GitHub then enforces **Sudo Mode** (re-auth via
passkey / hardware key / mobile / TOTP) for a ~2-hour elevated session.

### 1.4 `gh` CLI / GitHub Desktop
- `gh auth login` — interactive; pick `github.com`, protocol (ssh/https), authorize in browser; with SSH it can auto-generate + upload a key.
- GitHub Desktop — OAuth "Sign in to GitHub.com" → "Authorize desktop" → auto-configures `.gitconfig`. (Not used by the Platterpus cloud sessions.)

## 2. Cloning & forking

- **Clone** = full history + all branches + `.git` internals (not a snapshot).
  Desktop: repo → green **Code** → *Open with GitHub Desktop* → choose local path → **Clone**. CLI: `git clone git@github.com:owner/repo.git`.
- **Fork** = your own parallel copy under your namespace — the mechanism for
  contributing without write access (**this is the upstream-PR path**). You fork,
  clone your fork, branch, change, and open a PR *across* the repo boundary back
  to the parent. You do **not** need collaborator/write access on the parent —
  forking is exactly what removes that requirement.

## 3. Branching strategy

### 3.1 GitHub Flow
`main` is always deployable; **direct commits to `main` are forbidden**; branch
off `main` for each unit of work; keep branches **short-lived** (fewer
conflicts); open a PR for review; merge after review + green CI; **delete the
branch** after merge.

### 3.2 Branch naming
Semantic prefixes, `/`- or `-`-separated:

| Prefix | Use | Example |
|---|---|---|
| `feature/` | New functionality | `feature/user-authentication-oauth` |
| `bugfix/` | Non-critical defect fix | `bugfix/login-timeout-error` |
| `hotfix/` | Emergency production patch | `hotfix/security-patch-cve-2026` |
| `release/` | Version isolation for QA | `release/v3.2.0` |
| `username/` | Personal experiment | `jsmith/experiment-new-ui` |

Inject issue IDs when an issue tracker is used (`feature/JIRA-1234-add-…`) for a
traceable audit trail. *(Platterpus overrides this: session work uses the given
`claude/…` branch.)*

## 4. Branch execution

- **Prefer `git switch`** (Git ≥ 2.23) over `git checkout` for branches — it's
  scoped to branch ops and won't drop you into a detached HEAD or clobber files:
  - Create + switch: `git switch -c feature/new-branch`
  - Switch existing: `git switch main`
  - `git checkout -b …` still works but is the overloaded legacy form.
- Desktop: **Fetch origin** → **Current Branch** dropdown → base on `main` →
  **New Branch** → name → **Create Branch** → **Publish branch** (pushes it so
  it's tracked remotely). "Bring my changes to" migrates uncommitted work if you
  branched late.

## 5. Commits: philosophy & etiquette

### 5.1 Atomic commits
One logical change per commit (don't mix a CSS tweak with a schema migration).
Atomic commits ease review, make `git bisect` precise, and let `git revert` be
surgical. If you can't summarize it in ~50 chars, it isn't atomic — split it.

### 5.2 The seven rules of a great commit message
1. **Separate subject from body with a blank line** (tools parse the subject up to the first blank line).
2. **Limit the subject to ~50 chars** (GitHub warns >50, truncates >72).
3. **Capitalize the subject.**
4. **No trailing period** in the subject.
5. **Imperative mood** — "Add X", not "Added/Adding X". Heuristic: *"If applied, this commit will [subject]."* (matches Git's own merge/revert messages).
6. **Wrap the body at 72 chars** (Git doesn't auto-wrap terminals).
7. **Body explains *what* and *why*, not *how*** (the diff shows how).

### 5.3 Committing in Desktop
Stage per-file (checkboxes) or per-line (click line numbers in the diff) for
atomicity; **Discard Changes** to drop experiments; type an imperative Summary +
a Description; add co-authors if pairing; **Commit to [branch]** → **Push
origin** (triggers CI).

## 6. Pull requests

- A PR proposes merging the **head** (compare) branch into the **base** (target,
  usually `main`). GitHub computes the diff vs the merge-base and creates
  `refs/pull/ID/head` and `refs/pull/ID/merge` refs.
- Open it: Desktop **Preview Pull Request** → verify `base:` → **Create Pull
  Request** (opens the web UI); or web UI **Compare & pull request**.
- **Description anatomy** (use a `.github/pull_request_template.md` to
  standardize): **Context/intent** (why + linked issue), **Description of
  changes** (technical overview), **Testing plan** (concrete steps to verify),
  **Architectural notes / ADRs** for deep changes.
- **Draft PRs** for early feedback on incomplete work: web UI → *Create Draft
  Pull Request* — can't be merged accidentally and suppresses Code Owner
  notifications until you click **Ready for review**.

## 7. Merging & branch protection

### 7.1 Merge strategies

| Strategy | What it does | Pro | Con |
|---|---|---|---|
| **Merge commit** | Keeps all feature commits + a merge node | Full granular audit trail | Clutters `main` with "train tracks" |
| **Squash and merge** | Combines the branch into one commit on `main` | Pristine, linear, readable `main` | Loses granular per-commit history |
| **Rebase and merge** | Replays commits atop `main` (new hashes) | Linear, no merge nodes | Painful with conflicts; rewrites hashes |

**Squash and merge is favored** for feature branches (each `main` node = one
complete, deployable change). *(Platterpus did this for all PRs into `main` until 2026-09-26 and now uses a **merge commit** instead: its handshake laps cite branch commits by SHA, and a squash leaves those commits on no branch once the branch is deleted. `git log --first-parent main` keeps the one-node-per-change view. `CLAUDE.md` → *Commit & PR hygiene* lists this as deliberate divergence (6).)* Merge in the web UI → pick the strategy → **Confirm merge** → **Delete
branch** (in Platterpus GitHub does this automatically since 2026-09-30; start the next
change with `git switch -C <branch> origin/main`). "Merge when ready" / auto-merge merges
the instant CI passes.

### 7.2 Branch protection (admin, server-enforced on `main`/`release/*`)

> **IN THIS REPO: RULESETS, NOT CLASSIC BRANCH RULES (2026-10-12).** The owner decided on 2026-10-12 to turn on repository rulesets, replacing the 2026-09-11 decline, whose premise (that protection costs money) does not hold for a public repository on GitHub Free. `main` has a default-branch ruleset: no deletion, no force push, a pull request required with **no approvals** (one maintainer), and the CI gating jobs as required status checks. `v*` tags have a release-tag ruleset that blocks updates and deletion but not creation, because `release.yml` creates each tag. Two settings below do NOT apply here: *Require approvals* (there is one maintainer) and *Require linear history* (every pull request merges with a merge commit, `CLAUDE.md` divergence (6); squash and rebase merging are off in the repository settings since 2026-10-12). `CLAUDE.md` → *Commit & PR hygiene* divergence (5) is the authority, and `PLANNING.md` KDD-43 records what the rulesets touch. The rest of this section is the **upstream** playbook, for contributing to other people's repositories.
Settings → **Branches** → **Add rule** → branch pattern → enable: **Require a
pull request before merging** (blocks direct `git push` to `main`), **Require
approvals** (≥1–2; blocks self-merge), **Require review from Code Owners** (via
`.github/CODEOWNERS`), **Require status checks to pass**, **Block force pushes**.

## 8. Merge conflicts

A conflict = Git can't auto-reconcile divergent edits to the same lines (or an
edit-vs-delete). Git halts and flags the files.

- **Desktop:** conflicted files show a red icon; open in your editor, or use
  *Accept Incoming* / *Accept Current*, or hand-merge both; save →
  **Commit Merge**.
- **CLI:** `git status` lists "Unmerged paths"; open each file and resolve the
  markers —
  - `<<<<<<< HEAD` … your current branch's version
  - `=======` … divider
  - `>>>>>>> branch-name` … the incoming version —
  delete the markers, rewrite to correct logic, `git add <file>`, then
  `git commit`. Panic-abort with `git merge --abort`.
- **Prevention:** merge `main` into your feature branch **frequently** so
  divergences stay small.
- **A clean merge is not a correct merge when one side MOVED text** (this repo,
  2026-11-16). One branch moved a thousand lines of `TASKS.md` to an archive file;
  two others had edited some of those lines in place. Git merged all three with no
  conflict and put the edited lines back, so the move half-undid itself. After
  merging any branch that moves text, compare the moved file's length (and, for a
  byte-for-byte move, its content) with the mover's own version, and when they
  differ, take the mover's file whole and re-apply the other branches' edits to it.

---

*Filed 2026-07-07 at the maintainer's request as the contributor/upstream-PR
reference. See `docs/cyanrip-fork.md` Part A §10 for the per-gap options
and its Part D for which upstream repos we'd PR to and in
what order.*

---

*Last updated for Platterpus v0.7.127.*
