SKILL-FEEDBACK-FOR: rmccann-hub/claude-code-skills

# Skill feedback from an audit, 2026-10-27

From an audit of a Python desktop app (a Qt GUI over a command-line tool, with shell installers,
GitHub Actions CI and a review loop with a forked dependency's repository). Each item is written
as the issue the skill's "When something here is wrong" section asks for. The request, word for
word, was: "Audit this repository: its setup, CI, dependencies and context files against the
PROJECT-BOOTSTRAP-AND-AUDIT standard, and its code, Git workflows and prose with the skills that
cover them. This is a review only."

## Skills that loaded

All four expected skills loaded: project-bootstrap-and-audit (standard v0.48.2, SHA-256
`4aa13d8963b2548b90156c8e9e3887644e61798cdc11751817ea30d5e72de40e`), coding (reviewed
2026-10-26), git-workflows (reviewed 2026-10-16) and house-style (reviewed 2026-10-16). None
failed to load.

## project-bootstrap-and-audit

### 1. One report file, against a prompt that asks for two

- **Version:** standard v0.48.2.
- **Line that misled:** `references/PROJECT-BOOTSTRAP-AND-AUDIT-v0.48.2.md:322`, "Every run
  produces exactly one file", named `RUN-REPORT-<repo>-<date>.md`.
- **What happened:** the owner's audit prompt asked for two files in a private reports repository,
  one of them safe to share. The standard has no rule for an output format the request fixes, so
  the run had to decide on its own that the owner's format wins.
- **What's right:** the person's instruction about delivery wins; the standard already says the
  person decides.
- **Suggested fix:** one sentence under the rule: "Where the request names the report's files,
  form or place, follow it, keep the schema blocks, and record the difference in `overrides`."

### 2. Phase 3 has no case for "list the questions, don't wait"

- **Line that misled:** the Phase 3 section (line 1295 onward). It covers an attended wait and an
  unattended run that was given answers in advance.
- **What happened:** the prompt said to stop where the standard waits and list what to ask, and
  gave no answers. Neither case fits. The run carried the recorded tier forward and listed every
  question, but a stricter reading stops before Phase 4 and rates nothing.
- **Suggested fix:** add the case: "Where the request says not to wait and gives no answers,
  carry the recorded answers, or apply each question's default, rate on them, and put every
  question in Phase 6's first list."

### 3. The reading load for one audit

- **Line:** the routing table under *What to read, by job* (line 48 onward).
- **What happened:** an audit must read *Before you start*, *The run*, *File governance* and,
  with a second repository, *Cross-repository contracts*: about 3,600 of the file's 6,534 lines.
  The file's own Assumptions section says adherence may decay as a session lengthens.
- **Suggested fix:** split *The run* by dimension so a run can read the dimension it is rating,
  or give each dimension a short checklist at the top that names the rule's line.

### 4. Cooldown advice disagrees with zizmor

- **Line:** line 2292, a cooldown "set to roughly three days" is `OVER`.
- **What happened:** zizmor 1.30.1's `dependabot-cooldown` audit flags a Dependabot entry with
  no cooldown. The git-workflows skill recommends zizmor and says nothing about cooldowns, so a
  run using both gets opposite advice. The run followed the standard.
- **Suggested fix:** in git-workflows' `action-pinning` or `actions-security`, say that the
  platform's 3-day default makes zizmor's `dependabot-cooldown` finding informational, citing the
  standard's fact row.

## coding

### 5. Git's quoted file names are missing from bash-coding rule 5

- **Module:** `bash-coding`. **Date:** reviewed 2026-10-26.
- **Line:** `references/bash-coding.md:20`, "Read lines with `while IFS= read -r`, and names
  with `-print0` or `find -exec … {} +`."
- **What happened:** a script listed files with `git diff --name-only` and matched an anchored
  extension pattern. With git's default `core.quotePath=true`, a non-ASCII name prints as
  `"Bj\303\266rk.flac"`, with a closing quote, so `\.flac$` never matches and the check passes.
  Reproduced in a scratch repository. The rule as written points at `find` and `ls`, so a reader
  doesn't think of git.
- **What's right:** git's `core.quotePath` documentation; `-z` turns quoting off.
- **Suggested fix:** add "and `git diff`, `git ls-files` or `git status` with `-z`", and an audit
  row: "git name list read without `-z` and matched by pattern".

### 6. Subprocess text without an encoding

- **Module:** `python-coding`.
- **Lines:** rule 5 at `references/python-coding.md:21` and the audit row at `:135` name `open(`
  and `read_text(` only.
- **What happened:** most subprocess calls used `text=True` with no `encoding=`, which decodes a
  child's output with the locale. The audit row doesn't catch it.
- **Suggested fix:** extend the row to `subprocess.run` and `Popen` with `text=True` or
  `universal_newlines=True` and no `encoding=`.

### 7. The strict-mypy audit row reads too literally

- **Line:** `references/python-coding.md:137`, "mypy without `strict = true`".
- **What happened:** the project sets every strict flag one by one, which is equivalent. Read
  literally, the row raises a `GAP` against a configuration that meets the rule.
- **Suggested fix:** "mypy without `strict = true` or the equivalent individual flags".

### 8. A shell under another name

- **Module:** `python-security`.
- **Line:** rule 1 at `references/python-security.md:16`, "never `shell=True` on input".
- **What happened:** code built `["sh", "-c", f"curl … | {x} sh"]`. That's a shell, and it
  passes both the rule's wording and a project test written to the same wording.
- **Suggested fix:** name `["sh", "-c", …]` and `["bash", "-c", …]` beside `shell=True`, in the
  rule and the audit row.

### 9. Every unguarded delete is a BLOCKER

- **Module:** `bash-security`.
- **Line:** `references/bash-security.md:125`, `rm -r` or `rm -f` on a variable without `:?` or
  `--` is `BLOCKER`.
- **What happened:** 30 hits across a dozen scripts, none real: variables set to literals under
  `set -u`, `mktemp` paths with a trap, values already checked. The same module's arithmetic
  section has a carve-out for this; the delete row doesn't.
- **Suggested fix:** grade `BLOCKER` only where the variable can come from input or be empty;
  otherwise `GAP`, with the `:?` fix.

### 10. uv as the only route

- **Line:** rule 1 at `references/python-coding.md:15`, "Set a project up with `pyproject.toml`,
  uv and the src layout".
- **What happened:** the project builds with pip and a packaging tool that bundles its own
  Python. The rule's reasons don't cover that, so a reader can't tell whether the rule applies.
- **Suggested fix:** say what the rule protects (one resolver, a lock, a pinned interpreter) and
  that an existing pip-based build meeting those is fine.

### 11. No row for suppressions of rules that aren't enabled

- **Line:** contract rule 8 in `SKILL.md`, a suppression records a hand-check.
- **What happened:** Ruff's `RUF100` found 31 `noqa` markers for rules no configuration enables.
  They record nothing, and no audit row looks for them.
- **Suggested fix:** an audit row in `python-coding`: "`RUF100` not selected; `noqa` codes for
  rules not enabled".

## git-workflows

### 12. The commit-subject example refuses Conventional Commits

- **Module:** `commits-and-pull-requests`. **Date:** reviewed 2026-10-16.
- **Lines:** `assets/workflows/commit-subjects.yml:48`, regex
  `^[A-Za-z0-9_./-]+(, ?[A-Za-z0-9_./-]+)*: [^ ]`; the module points to it at
  `references/commits-and-pull-requests.md:137` for whatever grammar the context file names.
- **What happened:** the project uses `type(scope): summary`. The example refuses every such
  subject, because `(` and `)` aren't in the class. A reader following the audit row would install
  a check that fails every commit.
- **Suggested fix:** a second pattern for Conventional Commits, selected by an input, or say the
  example covers "area: summary" only.

### 13. Two modules disagree on CI triggers

- **Lines:** `references/ci-workflows.md:29` and its audit row at `:129` (push and pull_request
  with no branch filter; `BLOCKER` where anything counts on it), against
  `references/ci-speed.md:37` ("Don't run every job twice"). `ci-speed.md:119` notes the
  disagreement; nothing says which wins.
- **What happened:** the project runs CI on pushes to its default branch and on pull requests,
  and every change lands through a pull request with required checks. One module's row rates that
  `BLOCKER`; the other module recommends it.
- **Suggested fix:** make the row "CI doesn't run on the pull requests that land work" and allow
  a branch filter on `push` where work lands only through pull requests with required checks.

### 14. Rules with no audit row

- **Lines:** `references/actions-security.md:27` (`persist-credentials: false`), and in
  `references/ci-workflows.md` the rules on `concurrency`, linting workflows in CI, and a
  test-count guard.
- **What happened:** an audit that works row by row misses all four.
- **Suggested fix:** an audit row for each.

## house-style

### 15. "Newest first" against "past entries stay as written"

- **Lines:** `SKILL.md:38-39` (decisions in one record, newest first) and `SKILL.md:51` (past
  entries in an append-only record stay as written).
- **What happened:** the decision record runs oldest first, 44 entries. Following rule 11 means
  reordering; following the leave-alone list means not.
- **Suggested fix:** "Where an existing record runs oldest first, keep its order and say so at
  its top; new records run newest first."

### 16. Quotes aren't ignored by the shipped Vale config

- **Lines:** `SKILL.md:50` leaves quoted words alone; `assets/vale/HouseStyle/.vale.ini:1-2` has
  no `TokenIgnores`.
- **What happened:** quoted instructions in the context file would be flagged for spelling and
  filler. `references/prose-check.md` gives the fix per file only.
- **Suggested fix:** a default `TokenIgnores` for text in double quotes and in `*"…"*` form.

### 17. UI labels and data values quoted in prose

- **Line:** rule 12 and `references/writing-style.md` on quotes and names.
- **What happened:** the docs quote the app's own button label, spelled the British way, and a
  literal status value. Respelling the docs would make them disagree with the app.
- **Suggested fix:** "Where prose names a label or a value the code defines, put it in code
  formatting and fix the spelling in the code first."

### 18. Files two peer repositories keep identical

- **Line:** `SKILL.md:46`, files a fork shares with its upstream keep upstream's format.
- **What happened:** two peer repositories keep a few files byte-identical, owned by neither.
  The rule covers only a fork and its upstream.
- **Suggested fix:** widen it to "files shared byte-for-byte with another repository".

### 19. A generated block that sets a README's section order

- **Line:** rule 10, the README's sections in order.
- **What happened:** the README's first section is generated from a guide in the source tree, so
  the order rule 10 asks for can't be fixed in the README.
- **Suggested fix:** one line: fix generated sections at their source, and say where the
  generator's output starts.

### 20. Em dashes in headings

- **Line:** `assets/vale/HouseStyle/styles/HouseStyle/Headings.yml`.
- **What happened:** headings like "Decision 30 — Some title" capitalize the word after the dash.
  The skill doesn't say whether a dash starts a new phrase, and the rule would flag it.
- **Suggested fix:** say which, and add an exception or indicator for `—`.

## Coverage gaps

No loaded skill covers these areas of the audited code:

- Qt and PySide6 GUI code: thread ownership, widget lifetime, desktop accessibility. `html-coding`
  covers WCAG for the web only. The project's own accessibility gate turned out to depend on the
  machine's default font, which no skill rule would have prompted anyone to check.
- Test design (a testing skill is planned).
- Supply chain: lockfiles, provenance, verifying release attestations in the product (planned).
- AppImage and desktop-Linux packaging, including update information embedded in the image.
- Shell scripts run as root through `sudo` or `pkexec` on a user's machine.
- C patches carried for a forked dependency.
- TOML, YAML and JSON configuration and schema validation.
- Containers run through Distrobox or Podman.

## Environment notes for whoever runs the next audit

- Installing Vale, ShellCheck and actionlint was refused by the session's permission check as
  code from an outside source, so those checks were done by hand or not at all. zizmor installed
  from PyPI into a scratch environment and ran offline.
- Subagents' leads were re-checked before use. Two were wrong: one reported a missing check that
  existed under another name, and one proposed a cooldown the standard rates `OVER`.
