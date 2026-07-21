# GitHub Workflows & Version-Control SOP (reference)

> **How this applies to Platterpus.** This is a general, contributor-facing SOP
> for the GitHub ecosystem — most useful here as the **playbook for contributing
> *upstream*** (forking + opening PRs to `cyanrip`, `whipper`, `libcdio-paranoia`,
> etc. — see `docs/ripper-engine-strategy.md` §10 and the upstream-PR roadmap).
>
> For work **on the Platterpus repo itself**, the authoritative rules live in
> **`CLAUDE.md`** and win wherever they differ from this SOP:
> - The cloud sessions use the **git CLI + GitHub MCP**, not GitHub Desktop.
> - The agent git proxy is **fast-forward-only**: **no force-push**, no branch
>   delete, no tag push (releases go via the `release.yml` `workflow_dispatch`).
> - Feature work goes on the **designated branch** the session is given
>   (e.g. `claude/…`), never a personal `username/…` branch.
> - We **squash-merge** PRs to `main` (matches §7.1 below).
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
complete, deployable change). *(This is what Platterpus uses for **all** PRs into `main`.)* Merge in the web UI → pick the strategy → **Confirm merge** → **Delete
branch**. "Merge when ready" / auto-merge merges the instant CI passes.

### 7.2 Branch protection (admin, server-enforced on `main`/`release/*`)
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

---

*Filed 2026-07-07 at the maintainer's request as the contributor/upstream-PR
reference. See `docs/ripper-engine-strategy.md` §10 for the per-gap options
and `docs/upstream-pr-roadmap.md` for which upstream repos we'd PR to and in
what order.*

---

*Last updated for Platterpus v0.4.24.*
