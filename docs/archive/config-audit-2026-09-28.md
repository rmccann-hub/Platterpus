# RUN-REPORT — rmccann-hub/Platterpus — 2026-09-28

*Archived on 2026-09-28 at the owner's request ("give it all to me as a file back to the main repo"). This is the dated narrative of one configuration audit. Its durable conclusions live in `PLANNING.md` KDD-39, and the changes it applied are [rmccann-hub/Platterpus#276](https://github.com/rmccann-hub/Platterpus/pull/276). Read those first. Where this file and a living document disagree, the living document wins.*

```yaml
standard: PROJECT-BOOTSTRAP-AND-AUDIT v0.38.0
tool: Claude Code (Agent SDK), claude.ai cloud session, ephemeral remote container
repository: rmccann-hub/Platterpus @ a930411b4150b8244dbda0e3bca3c2022d35b765   # the tree audited
applied_on: claude/serene-bell-gzywdr @ 46e98bac0d0bb66c2662b18b0bf360b8cf1fd5b4  # 11 amendment commits + a merge of main at 1a752e39
pull_request: https://github.com/rmccann-hub/Platterpus/pull/276   # open, not merged
job: audit
mode: audit
tier: T3 (blast radius B3, audience A3, basis current)
tally: {BLOCKER: 1, DRIFT: 6, GAP: 3, OVER: 0, MIRROR: 0, UNVERIFIABLE-HERE: 0, OK: 0, N/A: 0}
capabilities_absent: [tag creation (dispatch only; not exercised), GitHub API for non-attached repositories (so the AppImage build is unverifiable here), repository security-settings endpoints (vulnerability-alerts, automated-security-fixes), a local working copy (owner has none), two-way messaging with another cloud session (one-way only)]
deviations: 8
decisions_open: 0
sections_read: [owner's run instructions, How to Read This File, Before You Start (all), The Run Phases 0-9, File Governance, Cross-Repository Contracts, Conformance Self-Check, Running this on a model that is not the one it was written against, Proposing a change to this standard]
sections_skipped: [The Release and Deploy Currency Gate, Choosing a Language and Runtime, Choosing the Shape, Project Shapes and Layout, Starter File Contents, The Configuration File Map, Any Agent Any Tool, Standards Distribution, Sending Results Back]
lifecycle: transient
expires: 2026-10-28
run_file: "0c0adc15-PROJECT-BOOTSTRAP-AND-AUDIT-v0.38.0-platterpus-run.md, 242239 bytes, end marker present, sha256 fc2a96f68a32963785435274adf5058ff5e2054b18f53e6a03e334a112f05aa4"
```

**Status: done up to your merge.** The eleven amendments you approved are applied on
`claude/serene-bell-gzywdr`, one commit each, and open as
[rmccann-hub/Platterpus#276](https://github.com/rmccann-hub/Platterpus/pull/276), not merged.
The eight you approved and held are listed as held. Nothing was declined, no release was cut,
and nothing under `CLAUDE.md`, `.github/`, `.claude/`, `docs/handshake/` or the four shared seam
files changed. This file lives in the session scratchpad, which is temporary; keep the copy you
were sent. It is ready to hand to the claude-code-skills session that triages the apply half.

## Outcome

- **Your answers at the gate:** H1 (a), H2 (b), H3 yes. S1–S3 were not applied here, as you
  said; claude-code-skills already carries them as F39, F32 and F40.
- **Applied (11):** A1, A3, A8, A9, A11, A13, A15, A16 (as H1 a), A17, A18 (as H2 b), A19. One
  commit each, listed in the table below and in the Phase 7 block.
- **Held under C3 (8):** A2, A4, A5, A6, A7, A10, A12, A14. `PLANNING.md` KDD-39 records them and
  the trigger that releases them: C3 lifting. A5's direction is yours to choose then.
- **Declined:** none.
- **`main` moved during the session**, five commits (#275), so #276 conflicted and GitHub ran
  no CI on it at all (`mergeable_state: dirty`, zero check runs). I merged `main` in,
  combining both sides of `CHANGELOG.md` and `docs/session-log.md`, and pushed `46e98bac`.
  CI then started.
- **CI after the push:** see the Phase 7 block's `ci_remote_conclusion_after_push`.
- **Still yours:** review and merge #276 (X4). Check X1: at 22:30 UTC the API still answered
  `{"enabled": false}` for private vulnerability reporting. X2 can't be read from a session.
  X3 is skipped, and KDD-39 records its reopen trigger.
- **Found while applying, not changed (N1–N3):** README links `/releases/latest`, which
  reaches no v0.x release. SECURITY.md's `gh attestation verify` line needs a login. The
  AppImage's zsync update information names `latest`, which excludes pre-releases.
- **Five changes to the standard from the apply half (S4–S8)**, for claude-code-skills, are in
  the block after Phase 9.

## Numbered amendments (List 2), with outcomes

| # | Dim | Severity | Change | Outcome |
|---|---|---|---|---|
| A1 | 1 | recommended | Record this audit as KDD-39 in PLANNING.md | **applied** `21d7f075` |
| A2 | 2 | recommended | Pin `build` and `twine` in publish-pypi.yml | **held** (a workflow) |
| A3 | 2 | recommended | Fix the lock comment; add four tool rows to DEPENDENCIES.md | **applied** `8e470db9` |
| A4 | 2 | optional | Commit `build/python-appimage/requirements.lock` | **held** (round 29's closing build) |
| A5 | 2 | optional | Make rule #11 and CI agree on pip-audit and cyclonedx-bom | **held** (workflows, CLAUDE.md); you choose the direction |
| A6 | 4 | recommended | Make the Claude-side audio guard fail closed | **held** (.claude/settings.json) |
| A7 | 4 | optional | Split CLAUDE.md | **held** (CLAUDE.md) |
| A8 | 5 | recommended | Delete the dead `[tool.mutmut]` block | **applied** `a162b3f6` |
| A9 | 5 | optional | Discover the `-x` doc test's files from `git ls-files` | **applied** `eddf0894`, with the no-`.git` fallback you asked for |
| A10 | 6 | recommended | Allow the changelog opt-out only when every commit is marked | **held** (a workflow) |
| A11 | 6 | recommended | docs/testing.md: tests-touched gates | **applied** `e4c30b27` |
| A12 | 7 | recommended | Scan the full history on every run | **held** (a workflow, CLAUDE.md) |
| A13 | 7 | optional | SECURITY.md and architecture.md say what CI scans | **applied** `e3cf52a3` |
| A14 | 8 | recommended | Build the SBOM from only what ships | **held** (workflows, CLAUDE.md) |
| A15 | 9 | recommended | Name you as copyright holder | **applied** `5e226623` |
| A16 | 9 | optional | install.sh checks `.sha256`, plus the attestation when gh is present | **applied** `c0254661` |
| A17 | 10 | recommended | docs/architecture.md §6.4, *When a release is bad* | **applied** `c310018c` |
| A18 | 10 | optional | Qualify "out of beta"; date the figures | **applied** `a581a0cb` |
| A19 | 3 | optional | A minimal `.editorconfig` | **applied** `6ceb318f` |

The merge of `main` is `46e98bac`. Each amendment's full change, evidence and both consequences
are in the Phase 6 block below.

## Actions only you can take, all in the browser (List 3), with states

- **X1** Private vulnerability reporting: **reported done, not observed.** At 22:13 and 22:30
  UTC, `GET /repos/rmccann-hub/Platterpus/private-vulnerability-reporting` still answered
  `{"enabled": false}`. That call was authenticated, the endpoint accepts `metadata=read`, and
  the URL was cache-busted. Check the repository's own setting under Settings → Advanced
  Security; an account-wide default for new repositories does not change an existing one.
- **X2** Push protection, Dependabot alerts and Dependabot security updates: **reported done,
  not observable here** (those endpoints answer 403 through this session's proxy).
- **X3** Release immutability: **skipped for now**, with a reopen trigger in KDD-39.
- **X4** Review and merge #276: **open.** Merging is yours. The branch `claude/session-omka9f`
  is fully merged and can be deleted in the browser (this session's git proxy cannot delete
  branches).

## Deliberately not raised

- **Branch protection on `main`.** Your 2026-09-11 ruling stands, and KDD-39 carries it
  forward as do-not-repropose.
- **Also not raised:** arming signing, squash merges, Scorecard, a Dependabot cooldown, TASKS.md
  archiving, pre-0.6.4 tags, `eol=lf`, a repository `scratch/`, per-call apt timeouts, the fork's
  .18 provider contract (round 29's work), and the proposal's now-stale F9.

The full list, with the reason for each, is in `not_proposed`.

---

---

# Appendix — every emission block, verbatim

## Phase 0 — Preflight

```yaml
phase: 0
capabilities: {shell: yes, write_outside_repo: yes,
               remote_ci_readable: yes, can_create_tags: no,
               enforced_layer: yes, third_party_repos_readable: yes}
capability_proof: |
  shell: `GIT_OPTIONAL_LOCKS=0 git status --porcelain` ran, exit 0, empty output
  write_outside_repo: "scratch write: probe -> /tmp/claude-0/-home-user-Platterpus/0c33df2c-8092-51da-9d93-3432474abbba/scratchpad/.write-probe" (probe file then removed)
  remote_ci_readable: GitHub MCP actions_list list_workflow_runs branch=main -> run 36477804072 "CI" run_number 957 event push head_sha a930411b4150b8244dbda0e3bca3c2022d35b765 status completed conclusion success
  can_create_tags: NOT ATTEMPTED - the owner forbids writes this session. Tool list read instead: the GitHub MCP tools offer list_tags/get_tag and no tag-creation call; CLAUDE.md records the agent git proxy as "no force-push, no branch delete, no tag push"; the only tag route is release.yml's workflow_dispatch, which creates the tag as part of a release (out of bounds this session)
  enforced_layer: Claude Code obeys a committed .claude/settings.json (permissions.deny + PreToolUse hook) - file present and tracked
  third_party_repos_readable: `git ls-remote --heads https://github.com/rmccann-hub/cyanrip` -> f8ebf48fc0d6926796c785fe2dbd9dec54ac15a5 refs/heads/master, b8d494a5cb7c1d1d55302b312e8fc5d0f343ae5f refs/heads/platterpus-fork (exit 0); `git ls-remote --heads https://github.com/cyanreg/cyanrip` -> f8ebf48fc0d6926796c785fe2dbd9dec54ac15a5 refs/heads/master (exit 0). GitHub API scope is this repository only; git reads of public repositories pass the proxy
asked: {local_working_copy: no, standards_repo: "none",
        copyright_holder: "the owner personally, a natural person, as rmccann-hub (sole human author); legal name not given"}
degraded:
  - "Shallow clone: 509 commits visible, 10 shallow roots in .git/shallow. Any claim about full history is limited to what is visible; CI's own full-history jobs are read from their logs instead."
  - "Tags cannot be created from this session (see can_create_tags). Recorded as a human or dispatch action, never 'tag locally'."
  - "The session branch has no remote counterpart: the fetch pruned origin/claude/serene-bell-gzywdr (removed on the remote after PR #274 merged). The local branch sits at origin/main a930411 with no upstream configured."
tool: "Claude Code (Agent SDK) in a claude.ai cloud session - ephemeral remote container"
clean_tree_proof: |
  $ GIT_OPTIONAL_LOCKS=0 git status --porcelain
  (empty)
  [exit 0]
fetch_proof: |
  $ git fetch --tags --prune
  From https://github.com/rmccann-hub/Platterpus
   - [deleted]         (none)     -> origin/claude/serene-bell-gzywdr
     88c09dd..a930411  main       -> origin/main
   * [new tag]         v0.6.10    -> v0.6.10
   * [new tag]         v0.6.11    -> v0.6.11
   ... (60 further "* [new tag]" lines elided here, v0.6.12 .. v0.6.9; 62 new tags in all,
        which is every tag the remote holds: `git ls-remote --tags origin` lists 62, v0.6.4 .. v0.6.63)
  [exit 0, taken unpiped]
  $ git fetch --tags --prune        # re-run before recording
  [exit 0, no output]
remote: https://github.com/rmccann-hub/Platterpus
default_branch: main   # read: `git ls-remote --symref origin HEAD` -> "ref: refs/heads/main	HEAD"
branch_used: claude/serene-bell-gzywdr
branch_override: "harness-pinned to claude/serene-bell-gzywdr"
shallow: yes
clock_session: "Mon Sep 28 20:22:07 UTC 2026"
clock_git: "2026-09-28 (a930411b4150b8244dbda0e3bca3c2022d35b765)"
clock_delta_days: 0
go: yes
notes: |
  - HEAD = origin/main = a930411 (merge of PR #274). Remote heads: main only.
  - core.hooksPath=.githooks was already set in .git/config at session start. The
    repository's SessionStart hook writes it; this run did not.
  - The three undetectable facts (working copy, standards repository, copyright holder)
    were answered in the owner's run instructions rather than at the Phase 3 wait, and are
    recorded here as asked directly.
  - A previous lap (docs/handshake/outbound/round-28-lap-07.md:76) records the SHA-256 of a
    different upload of the same standard commit: the audit extract,
    PROJECT-BOOTSTRAP-AND-AUDIT-v0.38.0-audit.md, 235503 bytes, 5980efd6…. This file is the
    owner's run file (242239 bytes), so the hashes are expected to differ.
```

## Phase 1 — Detect Mode

```yaml
phase: 1
decision_record_found: "PLANNING.md - the numbered '### KDD-NN — …' decision log (KDD-01 .. KDD-38)"
decision_record_alias: PLANNING.md
decision_entries: 38   # numbered KDD entries; 21 carry a date in their heading (KDD-10, KDD-19..KDD-38; KDD-24/25 month only)
adr_files: 0
recorded_tier: none
tier_grep_proof: |
  $ git ls-files | grep -iE '(^|/)(DECISIONS|ADR|decision-log|KDD)\.md$|(^|/)docs/adr/'
  [grep exit 1, no output]
  $ git grep -cE '^#+ .*(KDD|ADR)[- ]?[0-9]+' -- '*.md'
  PLANNING.md:39
  docs/archive/upstream-modification-investigation.md:2
  docs/ctdb-crc-algorithm.md:1
  docs/cyanrip-upstream.md:1
  docs/dependency-contracts.md:2
  docs/eac-parity.md:1
  docs/handshake/outbound/round14lap02platterpus.md:1
  docs/handshake/outbound/round14lap05platterpus.md:1
  docs/handshake/outbound/round14lap06platterpus.md:1
  docs/handshake/outbound/round14lap16platterpus.md:1
  docs/handshake/outbound/round15lap07platterpus.md:1
  docs/handshake/outbound/round15lap13platterpus.md:1
  docs/hardware-test-checklist.md:1
  docs/test-plan.md:3
  $ git grep -cE '^#+ *[0-9]{4}-[0-9]{2}-[0-9]{2} ' -- '*.md'
  TASKS.md:9
  docs/handshake/outbound/round14lap02platterpus.md:1
  docs/session-log.md:109
  $ git grep -icE 'tier[:*]* *T[0-3]|blast radius:? *B[0-3]|audience:? *A[0-3]' -- PLANNING.md
  [exit 1, no output]
  $ git grep -icE 'tier[:*]* *T[0-3]|blast radius:? *B[0-3]|audience:? *A[0-3]' -- '*.md'   # widened to every tracked Markdown file
  [exit 1, no output]
  # PLANNING.md:39 = 38 KDD headings + "### `CyanripImpl` — implemented (KDD-18, …)".
  # docs/archive/audit-2026-07-21.md is a documentation audit ("easy-tier/medium-tier/ask-tier"), records no T0-T3 tier.
runbook_found: "TASKS.md:3248 '## RUNBOOK — when a round opener arrives' - a handshake-round operations runbook. No deployment or production runbook heading exists; the install procedure is README.md §Installation (Steps 1-7), and the release ritual is docs/architecture.md §6.1-6.3."
runbook_proof: |
  $ git grep -inE '^#+ *(production )?(deployment|deploy|operations|runbook|maintenance)' -- '*.md'
  TASKS.md:3248:## RUNBOOK — when a round opener arrives (re-rehearsed 2026-09-22 for round 24)
  [exit 0]
mode: audit
mode_evidence: "Agent configuration exists (CLAUDE.md, .claude/settings.json, .claude/hooks/), and the tier grep over PLANNING.md and over every tracked *.md returned nothing, so there is no recorded tier."
prior_entry: n/a
prior_declines: []    # no prior run of this standard; the repository's own recorded rulings are under do_not_repropose
prior_deferrals: []
local_mitigations:
  - {dependency: "PySide6", version: ">=6.11.1,<6.12 (pyproject) / ~=6.11.1 (AppImage requirements.txt)",
     defect: "6.11.2 stopped resolving QKeySequence.StandardKey.Quit and .Preferences, so two menu items shipped with no shortcut (2026-08-18)",
     upstream_fixed: unknown,
     evidence: "pypi.org/pypi/PySide6/json read 2026-09-28: newest release is 6.11.2, uploaded 2026-08-18. No later release exists that could carry a fix. Mitigation in code: main_window.standard_shortcut checks Qt's answer.",
     removal_condition: "The minor pin is policy (CLAUDE.md Critical rule #11), not a workaround, and stays. The StandardKey check can come out once a Qt release restores the bindings and the suite, run against that wheel, proves it."}
  - {dependency: "musicbrainzngs", version: "==0.7.1 (both pyproject and AppImage requirements.txt)",
     defect: "Unmaintained since 2020, ships no type stubs",
     upstream_fixed: no,
     evidence: "pypi.org/pypi/musicbrainzngs/json read 2026-09-28: newest release is 0.7.1, uploaded 2020-01-11. Mitigations: the MusicBrainzClient adapter (Critical rule #1) and the mypy override `musicbrainzngs.*` ignore_missing_imports.",
     removal_condition: "The planned RequestsJsonImpl (DEPENDENCIES.md) replaces it, or a maintained release appears."}
  - {dependency: "cryptography", version: ">=50.0.0,<51 (pyproject) / ~=50.0 (AppImage)",
     defect: "CVE-2026-69247 in <=49.0.0; GHSA-537c-gmf6-5ccf below 48.0.1",
     upstream_fixed: yes,
     evidence: "pypi.org read 2026-09-28: 50.0.0 uploaded 2026-07-31, newest 50.0.1 uploaded 2026-08-25, which the range admits. The floor is the fix.",
     removal_condition: "None needed. A floor on a fix is a permanent constraint, not a workaround."}
  - {dependency: "sigstore", version: ">=4.5.0,<4.6 / ~=4.5.0",
     defect: "The verification API was reshaped across 2.x, 3.x and 4.x; an API change would silently stop every user's updates",
     upstream_fixed: unknown,
     evidence: "pypi.org read 2026-09-28: 4.5.0 (2026-07-28) is the newest release. A policy pin, not a defect workaround.",
     removal_condition: "n/a - bumped deliberately together with tests/test_update_attestation.py"}
  - {dependency: "python-appimage", version: ">=1.4,<2 (appimage.yml:45, release.yml:275, build_appimage.sh:71)",
     defect: "It installs each requirements line through a shell (`' '.join(args)` + shell=True), so `<` or `>` in a specifier becomes a redirection; it also runs pip once per line, so a global --find-links line cannot work",
     upstream_fixed: no,
     evidence: "raw.githubusercontent.com/niess/python-appimage/master/python_appimage/utils/system.py read 2026-09-28: line 21 `cmd = ' '.join(args)`, line 38 `subprocess.Popen(cmd, shell=True, ...`. pypi.org: newest 1.4.6, uploaded 2026-07-23. Mitigations: `~=` specifiers throughout build/python-appimage/requirements.txt, and PIP_FIND_LINKS exported by build_appimage.sh.",
     removal_condition: "python-appimage stops passing requirement lines through a shell"}
  - {dependency: "mutmut", version: "not installed (replaced)",
     defect: "mutmut 3.x removed --paths-to-mutate, and `mutmut run` executes no mutants; the weekly job exited 2 for seven runs behind `|| true`",
     upstream_fixed: unknown,
     evidence: "Routed around by scripts/mutation_sweep.py (ours), which mutation.yml now runs; the script's docstring says the failure was reproduced 2026-09-05 on mutmut 3.7. pyproject.toml still carries a [tool.mutmut] block (examined in Phase 4).",
     removal_condition: "n/a - the replacement is permanent unless the project chooses to return to mutmut"}
  # Searched: pyproject.toml, build/python-appimage/requirements.txt (no lockfile or constraints file is tracked:
  # `git ls-files | grep -iE 'requirements|constraints|\.lock$|lock\.json|pylock'` -> build/lock-requirements.sh,
  # build/python-appimage/requirements.txt), every `==` pin, `git grep -nE 'filterwarnings|simplefilter\('` over
  # *.py/*.toml/*.cfg/*.ini (no match), vendored or patch paths (`git ls-files | grep -iE '(^|/)(vendor|vendored|
  # third_party|thirdparty|_vendor|patches?)/'` and `\.(patch|diff)$`: no match), and src/platterpus/adapters/.
do_not_repropose:
  - "Branch protection or rulesets on main - CLAUDE.md 'Deliberate divergences' (5), maintainer ruling 2026-09-11, with reasons (proxy is fast-forward-only, nine gating jobs, releases via release.yml); docs/github-workflow-sop.md §7 annotated to match"
  - "Arming update signing (minisign) - KDD-37 D9 'Never', 2026-09-25; CLAUDE.md 'do not propose arming it'; the attestation check replaces it"
  - "Squash-merging session branches - CLAUDE.md divergence (6), 2026-09-26: merge commits keep cited SHAs reachable (tests/test_cited_commits_are_reachable.py)"
  - "Capitalised or unprefixed commit subjects, and a hard 50-character subject cap - CLAUDE.md divergences (1) and (2)"
  - "CHANGELOG sections for versions with no GitHub tag - KDD-37 D7: kept as history with dead links removed (done 2026-09-25)"
notes: |
  Source of do_not_repropose: this standard has no prior entry here, so these are the
  repository's own recorded rulings. Each has its reasoning written down, so under the
  precedence rule it outranks this file inside this repository. They are carried as
  settled, and none is raised again as an amendment.
```

## Phase 2 — Inventory

```yaml
phase: 2
recon_report_used: none
environment_preexisting:
  - "Ubuntu 24.04.4 container, 4 CPUs; Python 3.11.15 at /usr/local/bin/python3; system cryptography 41.0.7; no PySide6, no .venv"
  - "Qt runtime libraries present: libGL.so.1, libxkbcommon.so.0, libglib-2.0.so.0, libfreetype.so.6, libfontconfig.so.1, libdbus-1.so.3. Absent: libEGL.so.1 (as the owner predicted)"
  - "git: core.hooksPath=.githooks in .git/config (written by the repository's SessionStart hook before the run); commit signing configured in /root/.gitconfig"
setup:
  - {cmd: "git fetch --unshallow --tags", result: PASS, note: "matches CI's fetch-depth: 0; 509 -> 1510 commits visible. A fetch: remote refs and objects only, working tree and index untouched"}
  - {cmd: "apt-get update && apt-get install -y --no-install-recommends libegl1 libgl1 libglib2.0-0 libxkbcommon0 libdbus-1-3 libfontconfig1 libfreetype6", result: PASS, note: "ci.yml test job's declared apt set; libEGL.so.1 now present. Also counted in commands (a CI install step)"}
  - {cmd: "python3 -m venv $SCRATCH/venv && pip install -e '.[dev]'", result: PASS, note: "project's own declared deps: PySide6 6.11.2, ruff 0.15.22, mypy 2.3.1, pytest 9.1.1, pytest-xdist 3.8.0, pytest-cov 7.1.0, hypothesis 6.168.3, sigstore 4.5.0, cryptography 50.0.1, musicbrainzngs 0.7.1. Also counted in commands (CI's and CLAUDE.md's install)"}
  - {cmd: "fresh venvs mirroring CI jobs: `pip install -e . pip-audit` (pip-audit job); `pip install -e . 'cyclonedx-bom>=7,<8'` (sbom job); `pip install 'cyclonedx-bom>=7,<8'` alone (floor probe); `pip install 'build>=1,<2' 'python-appimage>=1.4,<2'` (appimage job)", result: PASS, note: "each job's own declared tooling: pip-audit 2.10.1, cyclonedx-bom 7.4.0, build 1.6.1, python_appimage 1.4.6"}
  - {cmd: "gitleaks 8.24.3 linux_x64 from github.com/gitleaks/gitleaks/releases, sha256 checked", result: PASS, note: "the binary ci.yml's gitleaks-action installs (its log: 'gitleaks version: 8.24.3'); tarball sha256 9991e0b2903da4c8f6122b5c3186448b927a5da4deef1fe45271c3793f4ee29c matches gitleaks_8.24.3_checksums.txt"}
  - {cmd: "git clone --no-hardlinks <repo> $SCRATCH/fresh && checkout a930411", result: PASS, note: "scratch copy for every run that writes into a tree (AppImage build, mutation sweep, handshake --status, hook probe), so the repository was never written"}
languages: {py: 488, md: 370, log: 93, json: 69, txt: 68, cue: 35, sh: 16, png: 9, yml: 6, toml: 6, svg: 2, gitkeep: 2, xml: 1, tsv: 1, gitignore: 1}   # 1172 tracked files
agent_config:
  - {path: CLAUDE.md, tracked: true, lines: 359, bytes: 77104}
  - {path: .claude/settings.json, tracked: true, lines: 51, bytes: 1484}
  - {path: .claude/hooks/session-start.sh, tracked: true, lines: 33, bytes: 1362}
total_lines_loaded_at_session_start: 359      # CLAUDE.md alone: no @-imports (`grep -n '^@' CLAUDE.md` -> none), no .claude/rules/, no AGENTS.md
total_bytes_loaded_at_session_start: 77104
reference_markdown_lines: 180785              # the other 369 tracked .md files (all tracked Markdown: 181144 lines in 370 files)
hooks_configured: yes
hooks_installed: yes
hooks_proof: |
  $ ls .git/hooks/pre-commit 2>/dev/null || echo "pre-commit NOT INSTALLED"
  pre-commit NOT INSTALLED
  $ git config --get core.hooksPath
  .githooks
  $ ls -la .githooks/
  -rwxr-xr-x 1 root root 2962 Sep 25 23:28 pre-commit
  # Installed through core.hooksPath, so the standard's `.git/hooks` probe reads it as absent. The
  # SessionStart hook (.claude/hooks/session-start.sh, run when CLAUDE_CODE_REMOTE=true) sets it.
  # Committed Claude-side layer: PreToolUse(Bash) audio check + SessionStart hook, in .claude/settings.json.
ci:
  workflows: [.github/workflows/ci.yml, .github/workflows/appimage.yml, .github/workflows/mutation.yml, .github/workflows/release.yml, .github/workflows/publish-pypi.yml, "Dependabot (dynamic; .github/dependabot.yml: pip + github-actions, weekly)"]
  jobs: ["ci: lint, typecheck, changelog, media-guard, pip-audit, gitleaks, sbom, tests-touched, test (py3.11), test (py3.12), test (py3.13), test (py3.14)", "appimage: build", "mutation: sweep x15 legs", "release: build-and-release", "publish-pypi: publish"]
ci_remote_conclusion:
  head: success
  default_branch: success
  proof: "HEAD = origin/main = a930411b. GitHub MCP actions_list: CI run 36477804072 (push, main, a930411b) completed/success, 12 of 12 jobs success; AppImage run 36477804073 completed/success. Read at job and log level: test (py3.11) '6730 passed, 19 skipped in 147.45s', 'Session completed; recorded exit status: 0'; test (py3.14) 'TOTAL 23850 1531 6492 495 93%' 'Required test coverage of 91% reached. Total coverage: 92.84%'; gitleaks 'event type: push' ... '0 commits scanned.' 'scanned ~0 bytes (0) in 144ms' '✅ No leaks detected' (see notes); appimage 'bundled verifier accepts the genuine v0.6.60 attestation (sigstore 4.5.0)'. Last weekly mutation run 36420777070: success."
gates_present: [lint, format-check, type-check, test (4 Pythons, xdist), coverage-floor (91, py3.14 leg), suite-completion sentinel, changelog, media-guard, dependency-audit (pip-audit), secret-scan (gitleaks, see notes), sbom, tests-touched, appimage build + smoke + bundled-verifier check (push to main / dispatch), release-time gates (handshake, CI, changelog, built version, bundled verifier, attestation), mutation sweep (weekly, non-gating)]
gates_absent: [shell lint (16 tracked .sh files, including install.sh, which the one-line installer runs from main; `bash -n` covers three of them), workflow lint (actionlint / zizmor), SAST (CodeQL or similar), hash-pinned AppImage dependency install (build/python-appimage/requirements.lock is not committed, so build_appimage.sh takes its online, version-pinned branch)]
lockfile: none      # `ls uv.lock package-lock.json Cargo.lock go.sum poetry.lock requirements.lock build/python-appimage/requirements.lock` -> exit 2, none exist; build/lock-requirements.sh is the generator
license_file: LICENSE   # GPL-3.0 text; GitHub detects spdx GPL-3.0; pyproject `license = "GPL-3.0-only"`; PyPI license_expression GPL-3.0-only
tags: 62            # v0.6.4 .. v0.6.63, all on the remote (`git ls-remote --tags origin` -> 62); 62 GitHub Releases, all pre-release; PyPI holds 122 versions from 0.4.0 (2026-06-29) to 0.6.63 (2026-09-28)
repo_visibility: public
plan_supports_branch_protection: yes   # GET /repos/rmccann-hub/Platterpus/rulesets -> http 200 `[]` (the endpoint answered; no rulesets configured). GET .../branches/main/protection -> 403 "Resource not accessible by integration" (this session's token, not the plan). list_branches: main protected=false. The Facts table (2026-09) agrees for a public repository. Moot: do_not_repropose.
collaborators: 1    # rmccann-hub, admin
history: {commits_visible: 1510, shallow: no}   # 509 visible and shallow at Phase 0; unshallowed at setup
present: [CLAUDE.md, .claude/settings.json, .claude/hooks/session-start.sh, .githooks/pre-commit, .github/dependabot.yml, 5 workflows, LICENSE, SECURITY.md, CHANGELOG.md (16827 lines), README.md, PLANNING.md (decision record), TASKS.md, DEPENDENCIES.md, docs/README.md (doc index), docs/TEST-VERIFICATION-CHECKLIST.md (322 lines), scripts/check.py, install.sh, install-appimage.sh, uninstall.sh, dev-setup.sh, setup-host.sh, build/build_appimage.sh, build/lock-requirements.sh, .gitignore, .gitattributes]
absent: [AGENTS.md, .editorconfig, .pre-commit-config.yaml, any lockfile, CONTRIBUTING.md, CODE_OF_CONDUCT.md, CODEOWNERS, PR template, .gitleaks.toml, .mcp.json, .claude/rules/]
commands:
  - {cmd: "apt-get install (ci.yml test job's 7 headless-Qt packages)", result: PASS, detail: "exit 0", collected: n/a}
  - {cmd: "pip install -e '.[dev]'", result: PASS, detail: "exit 0 (CI 'Install package with dev extras'; CLAUDE.md's documented install)", collected: n/a}
  - {cmd: "python3 scripts/check.py  -> lint (ruff check src tests)", result: PASS, detail: "exit 0", collected: n/a}
  - {cmd: "python3 scripts/check.py  -> format (ruff format --check src tests)", result: PASS, detail: "exit 0", collected: n/a}
  - {cmd: "python3 scripts/check.py  -> types (mypy)", result: PASS, detail: "exit 0", collected: n/a}
  - {cmd: "python3 scripts/check.py  -> tests (pytest -n auto --cov=platterpus --cov-fail-under=91)", result: PASS, detail: "exit 0; '6730 passed, 19 skipped in 164.31s'; sentinel '0'; 'TOTAL 23850 1550 6492 497 93%', 'Required test coverage of 91% reached. Total coverage: 92.75%'; check.py table '4/4 gates passed', wall clock 20:33:18-20:36:04 UTC", collected: 6749}
  - {cmd: "pytest -n auto -rs -p no:cacheprovider", result: PASS, detail: "exit 0; '6731 passed, 19 skipped in 91.71s'; skips listed in notes", collected: 6750}
  - {cmd: "pytest --co (scratch clone at a930411 vs this tree)", result: PASS, detail: "exit 0 both; '6744 tests collected' in a fresh clone vs 6750 here: the six extra ids are test_no_live_doc_calls_dash_x_overread[.pytest_cache/README.md] and [src/platterpus.egg-info/{SOURCES,dependency_links,entry_points,requires,top_level}.txt]", collected: 6744}
  - {cmd: "pip-audit --progress-spinner=off (fresh venv: pip install -e . pip-audit, as ci.yml)", result: PASS, detail: "exit 0; 'No known vulnerabilities found' (pip-audit 2.10.1)", collected: n/a}
  - {cmd: "cyclonedx-py environment --output-format JSON --output-file sbom.cdx.json + the job's >=10 floor", result: PASS, detail: "exit 0; 72 components. Probe: an env holding only cyclonedx-bom produces 35 components, so the floor passes with no project installed (Phase 4)", collected: n/a}
  - {cmd: "ci.yml changelog job script, replayed as push d226c03b..a930411b", result: PASS, detail: "exit 0; 'Opt-out via commit message; skipping.'", collected: n/a}
  - {cmd: "ci.yml media-guard job script, replayed as push d226c03b..a930411b", result: PASS, detail: "exit 0; 'No audio/media files. ✅'", collected: n/a}
  - {cmd: "ci.yml tests-touched job script, replayed as push d226c03b..a930411b", result: PASS, detail: "exit 0; 'src/tests change balance OK. ✅'", collected: n/a}
  - {cmd: "gitleaks detect --source . --redact --exit-code=2 (8.24.3, default config, full history)", result: PASS, detail: "exit 0; '1362 commits scanned.' 'scanned ~198137937 bytes (198.14 MB) in 9.28s' 'no leaks found'; 0 findings", collected: n/a}
  - {cmd: "bash build/build_appimage.sh (scratch clone, CI's tooling, APPIMAGE_EXTRACT_AND_RUN=1)", result: UNVERIFIABLE-HERE, detail: "exit 1 after the wheel stage: python-appimage's base-image lookup got 'urllib.error.HTTPError: HTTP Error 403: Forbidden'; `curl https://api.github.com/repos/niess/python-appimage/releases/tags/python3.12` -> 403 through this session's proxy (GitHub API reaches only attached repositories). Remote AppImage run 36477804073 on the same commit: success", collected: n/a}
  - {cmd: "platterpus --version", result: PASS, detail: "exit 0; 'platterpus 0.6.63 (source)'", collected: n/a}
  - {cmd: "python3 scripts/emit_dependency_contract.py --check", result: PASS, detail: "exit 0", collected: n/a}
  - {cmd: "python3 scripts/emit_script_language.py --check", result: PASS, detail: "exit 0", collected: n/a}
  - {cmd: "python3 scripts/handshake.py --status (scratch clone)", result: FAIL, detail: "exit 1, the tool's designed signal: rounds 1-28 CLOSED, 'round-29: ... -> OPEN', 'A round is OPEN: do not release, and do not switch the pin.', 'round 29 close-by: 2026-10-26T23:59:59Z, 28 day(s) remaining'. Not a malfunction. The closed vocabulary records it as FAIL", collected: n/a}
  - {cmd: "python3 scripts/mutation_sweep.py --target src/platterpus/verdict.py --tests tests/test_verdict.py --limit 40 --min-checked 30 (scratch clone; the CLAUDE.md-documented leg)", result: PASS, detail: "exit 0; 'generated=72 sampled=40 checked=39 killed=37 survived=2 unappliable=1' 'score=94.9%'; survivors verdict.py:152:16 In->NotIn, verdict.py:317:44 Gt->GtE", collected: n/a}
  - {cmd: "mutation.yml's other 14 legs", result: NOT-RUN-HERE, detail: "weekly, non-gating, up to 90 min per leg; time-boxed out. The last scheduled run (36420777070) concluded success", collected: n/a}
command_tally: {PASS: 18, FAIL: 1, UNVERIFIABLE-HERE: 1, NOT-RUN-HERE: 1}
template: {copier_answers: none}
notes: |
  - The 19 skips (identical count remote and local): 9x tests/test_eac_pregap_convention.py:315 "track N has a
    pre-gap; covered by the formula test"; 3x tests/test_transcode.py:413/432 "needs real ffmpeg + flac"; 2x
    tests/test_lap_language.py:169/745 "no clone of the fork's tree here"; tests/test_no_stale_version_claims.py:471
    and :516 (no 0.9.x / 1.0 claim yet); :1177 "a round IS open (PIN_UNDER_REVIEW=51cc789 != FORK_PIN=e0471f4)";
    tests/test_audit_regressions.py:342 "root ignores the write bit"; tests/test_scroll_guards.py:92 "no focus in
    this headless session".
  - The collected count is not fixed: 6744 in a fresh clone, 6749 after `pip install -e` (what CI sees), 6750 after
    one pytest run with the cache provider. One parametrised test walks the working tree rather than the tracked set.
  - `on:` blocks: ci.yml runs on push to main, pull_request to main, and workflow_dispatch; appimage.yml on push to
    main and workflow_dispatch; release.yml on v* tags and dispatch; publish-pypi.yml on dispatch only; mutation.yml
    weekly and on dispatch. **A push to the session branch alone produces NO workflow run. It is absent, not
    pending.** Any apply would be gated only by the local run until a PR or a dispatch exists. This is said
    again at the gate.
  - Suppression switches: no `continue-on-error` in any workflow. Every `|| true` in ci.yml absorbs only grep's
    no-match, and the producer is checked separately. mutation.yml's `if: always()` steps are summary and upload
    only. **The step that reports success while measuring nothing is gitleaks on push**, and the cause is the
    action's own range logic, not a switch: its push run uses
    `--log-opts=--no-merges --first-parent <first-commit>^..<head>`, and on this repository's merge-commit
    workflow that walks only merge commits, which `--no-merges` then drops. PR runs do scan: PR #274's run
    scanned '3 commits', '~3919 bytes'. The rating is in Phase 4.
  - The first probe command containing `rm -rf` was refused by the enforced layer (.claude/settings.json deny
    `Bash(rm -rf:*)`), which is working as designed. It was re-run without it.
  - Not run, per the allowlist: release.yml, publish-pypi.yml, `--install-ripper`, `--doctor` (host checks for
    Distrobox and cyanrip belong to the owner's machine).
```

## Phase 3 — Establish Tier — WAIT

```yaml
phase: 3
answers_source: asked directly   # the owner's run instructions, "My answers to the Phase 3 questions" (1-6)
owner: personal
copyright_holder: "the owner personally, as rmccann-hub, the only human author; legal name not given. 'Platterpus contributors' (pyproject.toml, metainfo) is not a legal entity, per the owner"
exposure: already_public
production: today
dependents: "None known to the owner. Anyone can install from PyPI, GitHub Releases or the one-line installer, so users the owner does not know of are possible. The owner's fork, rmccann-hub/cyanrip, reads this repository's handshake laps and rig results."
blast_radius: B3
audience: A3
tier: T3
tier_basis: current
tier_reasoning: |
  Inbound and output differ, so this is rated on output (the Phase 3 constraint).
  - Inbound is narrow. There is one committer (collaborators: 1, admin), and the running app listens on
    no port and is reachable by nobody over the network. Rated on access alone, that would be B1/A1.
  - Output is public today, through channels that deliver without a further human review step:
    PyPI (122 releases since 0.4.0, 2026-06-29); GitHub Releases (62, the AppImage); the in-app updater
    (Check for updates installs a new release); the ripper offer after launch (installs a newer approved
    build of the fork into the user's Distrobox container); and the one-line installer.
  - The one-line installer (README.md:121: `curl -fsSL
    https://raw.githubusercontent.com/rmccann-hub/Platterpus/main/install.sh | bash`) runs whatever
    install.sh is on main at that moment. So a defective or hostile commit on main reaches an installer's
    machine with no release and no review step. main is unprotected, by recorded ruling (do_not_repropose).
  - Result: B3 (the public), A3 (external or public), so T3 as the higher of the two. The known population
    is one person; the rating rests on reach, not on a count.
tier_previous: none
irreversible_resolved:
  - {rank: 1, decision: "Outbound licence GPL-3.0-only (KDD-10, 2026-05-30). Every PyPI release since 0.4.0 carries it: PyPI license_expression 'GPL-3.0-only', pyproject `license = \"GPL-3.0-only\"`, LICENSE holds the GPL-3.0 text", state: locked}
  - {rank: 2, decision: "Published names: `platterpus` on PyPI (122 releases), `platterpus-x86_64.AppImage` on GitHub Releases, app ID `io.github.rmccann_hub.Platterpus`", state: locked}
  - {rank: 3, decision: "Public API: the command-line flags, the UI script language, the JSON rip report, the EAC-compatible log, and the handshake header shared with the fork", state: settled}
  - {rank: 4, decision: "What it keeps: its config (~/.config/platterpus/config.toml), its logs (~/.local/share/platterpus/log.txt), a rip report and logs beside each rip, and the rips it files into the library folder", state: settled}
  - {rank: 5, decision: "Language and runtime: Python 3.11+ with PySide6 (Qt 6), shipped as an AppImage", state: settled}
irreversible_open: []
deployment:
  runs_on: "the owner's Bazzite desktop (KDE Plasma 6) with the Pioneer BDR-209D drive, the only machine it runs on"
  started_by: "the app menu, which runs the released AppImage in ~/Applications. Hardware test runs start the same AppImage from the rig scripts. The ripper runs inside the Distrobox container `ripping`"
  binds: "none: it listens on no port. Outbound only: MusicBrainz, Cover Art Archive, AccurateRip, CTDB, GitHub (app and ripper updates), Sigstore's trust root (when verifying an update), and the Fedora COPR and Flathub (during ripper setup)"
  reachable_from: "nobody, over the network"
  source: asked directly
  matches_documentation: yes
notes: |
  Documentation compared with the answer:
  - README.md:445: the first run offers menu integration and moves the AppImage. README.md:1003: the app lives
    at `~/Applications/platterpus-x86_64.AppImage`.
  - README "At a glance": Bazzite KDE Plasma 6 is the primary target, and cyanrip runs inside Distrobox.
  - CLAUDE.md *Architecture*: the host GUI calls ~/.local/bin/cyanrip, which enters the container `ripping`.
  - A search of README.md and SECURITY.md for listen, localhost, 0.0.0.0 and 127.0.0.1 found no claim of a
    listener.
  Nothing here disagrees with the owner's answer.

  Owner's premises reproduced rather than assumed:
  - libEGL.so.1 was absent from the container (`ldconfig -p`) until CI's apt set was installed.
  - check.py took 2 min 46 s here.
  - PyPI's first upload is 0.4.0 at 2026-06-29T19:50:47Z.
  - The tagged release v0.6.63 carries the AppImage.
  - The one-line installer fetches install.sh from main (README.md:121, install.sh:15).

  Overrides (recorded here because the Phase 4 block that holds them is not emitted yet):
  1. Branch: harness-pinned `claude/serene-bell-gzywdr`, not `chore/config-audit`. Nothing is committed to it.
  2. The owner answered the Phase 3 questions and the three Phase 0 questions in the run file. They are
     recorded as asked directly, and the Phase 3 wait is still observed, as instructed.
  3. The clone was unshallowed (`git fetch --unshallow --tags`) to match CI's `fetch-depth: 0`. This matters
     because two tests skip rather than fail on a shallow clone. It is a fetch, so .git only.
  4. Every run that writes into a tree ran in a scratch clone at a930411, not in the repository: the AppImage
     build, the mutation sweep, `handshake.py --status`, and the audio-hook probe. This honours "write
     nothing to the repository". check.py wrote its logs to the scratchpad (`--log-dir`), not to
     `.check-logs/`.
  5. gitleaks 8.24.3 was downloaded and its checksum verified. That is the binary ci.yml's gitleaks-action
     installs; the owner's setup licence names apt and pip installs, and this was treated as the job's
     declared tooling.
  6. The changelog, media-guard and tests-touched jobs were replayed by extracting their `run:` scripts from
     ci.yml (lines 149-233, 254-298, 433-516) and running them with the push event's variables. They did
     not run on a GitHub runner.
  7. Mutation testing: only the CLAUDE.md-documented leg ran. The other 14 legs are NOT-RUN-HERE.
  8. The standard's hook probe (`ls .git/hooks/pre-commit`) was supplemented with `git config --get
     core.hooksPath`, because this repository installs hooks that way.
```

> **Phase 3 wait answered, 2026-09-28:** the owner replied *"Confirmed."* The tier stands as rated (T3, B3/A3, basis current). The eight overrides listed in the Phase 3 notes are carried into Phase 4's `overrides`.

## Phase 4 — Audit the Ten Dimensions

```yaml
phase: 4
dimensions:
  - n: 1
    name: stakes-and-lifecycle
    status: GAP
    finding: "No tier is recorded. The decision record (PLANNING.md, 38 KDDs) records rulings but not a tier with both axes. Every later run of this standard therefore starts as a first audit and re-asks the six questions."
    evidence: "Phase 1: `git grep -icE 'tier[:*]* *T[0-3]|blast radius:? *B[0-3]|audience:? *A[0-3]'` over PLANNING.md and over every tracked *.md returns exit 1 with no output. Tier T3 (B3/A3, basis current) was confirmed by the owner at the Phase 3 wait on 2026-09-28."
    secondary: []
    strength: "The decision record is unusually complete. There are 38 numbered KDDs; KDD-37 and KDD-38 record 19 maintainer rulings, and TASKS.md keeps each ruling's options. Declines carry their reasons (unprotected main, signing never armed, merge commits over squash). KDD-35 states what a version number claims and what earns 0.9.1 and 1.0.0."

  - n: 2
    name: language-runtime-environment
    status: DRIFT
    finding: |
      One tool configured in several places diverges.
      - The PyPI wheel and sdist, the artifacts behind all 122 releases, are built by `pip install build twine`, unpinned (publish-pypi.yml).
      - release.yml, appimage.yml and build_appimage.sh pin `build>=1,<2`, and DEPENDENCIES.md says `build` is pinned. twine has no DEPENDENCIES.md row.
      - build/python-appimage/requirements.txt says cryptography's "exact bundled version is fixed by requirements.lock". No requirements.lock is committed, so every build takes the online, version-pinned branch.
    evidence: "publish-pypi.yml 'pip install build twine'. appimage.yml:45 and release.yml:275 'pip install \"build>=1,<2\" \"python-appimage>=1.4,<2\"'. DEPENDENCIES.md:20 'build | `>=1,<2` (pinned in `release.yml`/`appimage.yml`/`build_appimage.sh`, 2026-07-21)'. `grep -c -i twine DEPENDENCIES.md` -> 0. `ls build/python-appimage/requirements.lock` -> absent, and DEPENDENCIES.md:12 itself says the lock 'is not committed yet'."
    secondary:
      - {status: GAP, note: "No lockfile for a T3 application. CI resolves fresh on every run (`pip install -e '.[dev]'`). The AppImage build's hash-verified wheelhouse path is dormant: build_appimage.sh says it 'activates ONLY when the lock exists'."}
      - {status: DRIFT, note: "Critical rule #11 says 'A tool that gates CI must not float'. The gating pip-audit job installs pip-audit unpinned (2.10.1 today), and the gating sbom job takes `cyclonedx-bom>=7,<8`. tests/test_gating_tools_are_pinned.py covers ruff and mypy only."}
    strength: "Runtime pins agree between pyproject.toml and the AppImage recipe (PySide6, cryptography, sigstore, musicbrainzngs, tomli-w), a test enforces that, and every pin carries its reason. The language choice is recorded (KDD-01 and the locked Stack) and matches the manifest. The matrix covers 3.11-3.14, and the AppImage bundles a pinned CPython 3.12, which is one of the tested legs."

  - n: 3
    name: structure-and-hygiene
    status: GAP
    finding: "There is no .editorconfig. It is a baseline default, and here it covers what no formatter does: ruff formats Python only, while 370 Markdown files, 6 YAML files and 16 shell scripts have no formatter."
    evidence: "`ls .editorconfig` -> 'No such file or directory'. .gitattributes is present (`* text=auto`; UTF-16 EAC logs marked `-text`). .gitignore is present and denies audio extensions."
    secondary: []
    strength: "There is one source root (src/platterpus) and one test root (tests/). The root-level shell scripts are the public installer entry points: install.sh is fetched by URL. docs/ has an annotated index that tests/test_doc_index_completeness.py holds complete. Retired documents live in docs/archive/ with a graduation map. The generated data module is excluded from lint. CODEOWNERS is N/A with one person."

  - n: 4
    name: agent-configuration
    status: DRIFT
    finding: "The Claude-side audio guard, the PreToolUse(Bash) hook in .claude/settings.json, fails open. When `git diff --cached` fails, the pipeline's `|| exit 0` allows the command. The repository removed that idiom from .githooks/pre-commit and from ci.yml's media-guard on 2026-08-20 ('A guard that cannot enumerate what it is guarding must REFUSE'), and the third guard was never brought in line."
    evidence: |
      Scratch-clone probe, a force-staged probe-placeholder.flac:
      (a) healthy git -> "Blocked: audio/copyrighted media is staged (CLAUDE.md Critical Rule #8)..." [hook exit 2]
      (b) GIT_INDEX_FILE=/tmp (git cannot read the index), same staged file -> [hook exit 0]
      .githooks/pre-commit under the same broken producer -> "✖ COMMIT BLOCKED — could not list the staged files (git diff failed)." [exit 1]
    secondary:
      - {status: OVER, note: "CLAUDE.md, the only always-loaded file, is 359 lines and 77,104 bytes. That is past this standard's ~150-line prune point and its ~300-line outer limit. It was already cut from 549 lines / 140,822 bytes at v0.6.60, and 21 of its 185 commits landed since 2026-09-21."}
      - {status: GAP, note: "There is no AGENTS.md and no .claude/rules/, so every rule loads in every session. The owner's proposal plans path-scoped rules on both sides (FK5, T5), and C3 holds that work."}
      - {status: UNVERIFIABLE-HERE, note: "About 49 account-level skills (the anthropic-skills:* namespace) load into this repository's sessions. The repository cannot turn them off: a project settings file's syncClaudeAiSkills is ignored. Two describe themselves as '[HIGH PRIORITY - READ FIRST]'. This run read and used none, per the run file. Who wrote or reviewed them cannot be established from here."}
      - {status: UNVERIFIABLE-HERE, note: "Anthropic's under-200-lines target and Codex's 32 KiB instruction limit come from the dated Facts table (2026-09) and were not re-checked here. The owner's proposal F6 cites the first as of 2026-09-27. The OVER rating rests on this standard's own budget, not on those numbers."}
    strength: "The enforced layer carries the project's domain invariant: audio is never committed (Critical rule #8). That is recorded here as a strength, not as excess. Deny rules block `rm -rf`, `rm -fr` and every force-push spelling, and one of them fired on this run. The SessionStart hook installs the pre-commit hook in every cloud session, so the client-side guard really gates agent commits. There are no `ask` rules and no .mcp.json. The context file was observed loaded in this session, and all 92 repository paths CLAUDE.md names resolve."
    # Hooks read, command by command:
    # - PreToolUse runs a local `git diff --cached` on every Bash call. No network, milliseconds.
    # - SessionStart runs .claude/hooks/session-start.sh. It sets core.hooksPath only when
    #   CLAUDE_CODE_REMOTE=true, is idempotent, and never fails the session.
    # The ceiling on deny rules:
    # - `Bash(rm -rf:*)` does not match `rm -r -f`, `rm -Rf` or `find -delete`.
    # - `Read(./.env*)` leaves `Bash(cat .env)` open. No .env file exists
    #   (`git ls-files | grep -iE '(^|/)\.env'` -> none).
    # - Deny rules govern the agent's own tools, never a script the agent writes. They are a speed
    #   bump, not a sandbox.

  - n: 5
    name: testing-and-verification
    status: DRIFT
    finding: |
      pyproject.toml still carries a [tool.mutmut] block (source_paths, only_mutate, a 14-file test selection) for a tool nothing runs.
      - mutation.yml runs scripts/mutation_sweep.py, and its header opens "WHY THIS NO LONGER USES `mutmut`".
      - The block's comment says "the pin in the workflow is what stops the file's schema moving under us". No such pin exists.
    evidence: "`git grep -nE 'tool\\.mutmut|only_mutate|pytest_add_cli_args_test_selection' -- ':!pyproject.toml'` -> CHANGELOG.md:5303 and :5325 only (history). `git grep -n mutmut -- .github scripts` -> mutation.yml and mutation_sweep.py comments explaining the replacement, nothing that runs it."
    secondary:
      - {status: GAP, note: "tests/test_documented_ripper_flags_are_real.py::_live_docs() walks the working tree (`REPO_ROOT.rglob('*')`), so its population includes ignored build artifacts. Collected count: 6744 in a fresh clone at a930411, 6749 after `pip install -e` (what CI sees), and 6750 after one pytest run. The extra ids are .pytest_cache/README.md and src/platterpus.egg-info/{SOURCES,dependency_links,entry_points,requires,top_level}.txt. An untracked scratch note that mentions `-x` would fail the suite locally."}
    strength: |
      The suite is strong.
      - 6,749-6,750 tests on four Pythons with xdist. 19 skips, each named with its reason.
      - Branch coverage 92.75% locally and 92.84% in CI, against a 91% floor. A test reads the floor at the last tag, so it cannot be lowered in the same commit.
      - A completion sentinel refuses a truncated run, and hypothesis 'never raises' properties cover the parsers.
      - The project's own mutation sweep has per-leg floors: 15 legs weekly, all green on 2026-09-28. Locally the verdict leg scored 94.9%, with 39 checked against a floor of 30.
      - scripts/revert_probe.py tests for vacuity.
      - TEST-VERIFICATION-CHECKLIST.md is substantive: 322 lines, 69 checkbox items.

  - n: 6
    name: enforcement-and-review
    status: DRIFT
    finding: |
      The changelog gate's opt-out covers a whole range, where Critical rule #7's exemption covers one commit.
      - One `[skip changelog]` line in any commit exempts every commit in the push or PR. The job prints "Opt-out via commit message; skipping." before it looks at CHANGELOG.md.
      - Sessions end with a marked records commit, so 10 of the 14 PR merges since 2026-09-26 were never checked.
      - Five commits on main changed src/platterpus with no CHANGELOG line under such an exemption. The latest is 1b32e19e (2026-09-16), "... and fix the reporter defect the fork found".
    evidence: "ci.yml:201-204: the range-wide grep, then `exit 0`. Replaying the job script on push d226c03b..a930411b printed 'Opt-out via commit message; skipping.' [exit 0]. Scan of origin/main: 56 first-parent merges and 440 first-parent non-merge commits examined; 5 exempted with src changes and no CHANGELOG line (31b73c04, 1b32e19e, 8b103f32, 011d6389, 2d635f25). Since 2026-09-26: 14 PR merges, 10 of whose ranges carry the marker."
    secondary:
      - {status: DRIFT, note: "ci.yml:414-418 heads the tests-touched job 'Advisory (never fails)... always exits 0', and docs/testing.md:52 calls it 'the advisory `tests-touched` nudge'. It has gated since 2026-08-20, and release.yml's CI gate requires it."}
      - {status: N/A, note: "Branch protection and rulesets on main are do_not_repropose (maintainer ruling 2026-09-11, CLAUDE.md divergence (5)). See not_proposed."}
    strength: |
      - Every workflow sets `permissions:`: read at the top, writes only on the release job. A test enforces this.
      - Every action is SHA-pinned, and every job carries a time bound.
      - Untrusted event fields reach run scripts only through `env:`, never interpolated into shell.
      - The release job re-checks, on the exact commit: all 12 required CI checks, the handshake gate, both halves of the changelog, the built version by exact match, the bundled verifier, and the attestation.
      - PRs merge with merge commits, so every SHA a lap cites stays reachable.
      - The pre-commit hook is installed in cloud sessions.
      - `[no-test-needed]` was used on 34 of 737 commits since 2026-08-20, so the tests-touched gate does not have a false-trigger problem.

  - n: 7
    name: secrets-security-data
    status: BLOCKER
    finding: |
      The secret scan reports success while measuring nothing on every push to main.
      - CLAUDE.md, SECURITY.md, docs/architecture.md and ci.yml all describe it as a full-history scan, and release.yml's CI gate requires it to be green.
      - gitleaks-action builds its own range: `--log-opts=--no-merges --first-parent <first-pushed-commit>^..<head>`. On this repository's merge-commit history, that range holds only merges, which `--no-merges` drops. The head commit's push run printed "0 commits scanned." and "✅ No leaks detected".
      - Pull-request runs scan only the PR's first-parent non-merge commits. So no CI run ever scans (a) a merge commit's own changes or (b) history that arrives as a merge's second parent.
      - Example of (b): 167e0d4 came in through the ours-merge d7cea50. It is reachable from main and no CI run ever walked it. The ours-merges of 2026-09-26 that brought 38+ stranded commits back have the same shape.
      No live exposure was found: a full-history scan run here is clean.
    evidence: |
      CI run 36477804072, job gitleaks: "event type: push" / "gitleaks cmd: ... --log-opts=--no-merges --first-parent 9ff21de7d4529f9d658d38c8c343afb16a0fbd4a^..a930411b4150b8244dbda0e3bca3c2022d35b765" / "INF 0 commits scanned." / "scanned ~0 bytes (0) in 144ms" / "✅ No leaks detected".
      PR run 36477283833: "3 commits scanned." / "scanned ~3919 bytes".
      Planted-positive replay (scratch clone; a synthetic AKIA key on a feature commit, merged --no-ff):
        PR range            -> "1 commits scanned."    "leaks found: 1"  [exit 2]
        push range on merge -> "0 commits scanned."    "no leaks found"  [exit 0]
        full history        -> "1363 commits scanned." "leaks found: 1"  [exit 2]
      A key added only inside a merge commit: `--log-opts="--all"` -> 1364 commits, not found; `--log-opts="--all -m"` -> 1458 commits, found, 23.0 s.
      Real repository, gitleaks 8.24.3 full history: "1362 commits scanned." "scanned ~198137937 bytes (198.14 MB) in 9.28s" "no leaks found".
      `git merge-base --is-ancestor 167e0d4 origin/main` -> yes; `git rev-list --first-parent origin/main | grep -c '^167e0d4'` -> 0; d7cea50's parents: 8941fee, 167e0d4.
      Scanner detection: the canonical AWS key and GitHub PAT shapes were detected. Bare `DB_PASSWORD=` lines were caught in 193 of 200 Markdown files (7 missed) and in Python.
    secondary:
      - {status: DRIFT, note: "SECURITY.md's preferred reporting channel is GitHub private vulnerability reporting, and it is disabled: `GET /repos/rmccann-hub/Platterpus/private-vulnerability-reporting` -> http 200 `{\"enabled\": false}`. The only documented route for a vulnerability report does not accept one."}
      - {status: UNVERIFIABLE-HERE, note: "Not readable from this session: platform secret scanning and push protection, Dependabot alerts, and Dependabot security updates. `security_and_analysis` is null for this token, and /vulnerability-alerts and /automated-security-fixes return http 403 'not permitted through this proxy'. The Facts table (2026-09) says secret scanning and push protection are free and default-on for public repositories. Not observed. See X2."}
    strength: "No credential in the 1362 scanned commits of public history. PyPI publishing uses OIDC trusted publishing, so no token is stored anywhere. Workflows run least-privilege. Deny rules cover .env* and secrets/**. SECURITY.md exists with scope, supported versions and a hardening list. The in-app updater verifies each release's build attestation, fail-closed."

  - n: 8
    name: dependencies
    status: DRIFT
    finding: |
      The SBOM is described as "a CycloneDX inventory of what ships" (CLAUDE.md, SECURITY.md, ci.yml). Three things are wrong with it.
      - It inventories the CI job's own environment, so it includes the generator's tree (cyclonedx-bom, cyclonedx-python-lib, lxml, jsonschema...), none of which ships.
      - Its "refuse fewer than ten components" floor passes with the project absent.
      - ci.yml:371-372 says "`release.yml` attaches the release build's copy to the GitHub Release". release.yml attaches no SBOM, and v0.6.63's six assets include none.
    evidence: "Fresh venvs mirroring the job: the project plus cyclonedx-bom 7.4.0 gives 72 components. cyclonedx-bom alone, with the project not installed, gives 35 components ('floor check would pass: True'). A venv holding only `pip install .`, scanned from outside it, gives 40 components: no generator packages, and all six runtime dependencies (platterpus, PySide6, sigstore, cryptography, musicbrainzngs, tomli-w). Release v0.6.63 assets: install-appimage.sh, install.sh, platterpus-x86_64.AppImage, .sha256, .sigstore.json, .zsync."
    secondary:
      - {status: UNVERIFIABLE-HERE, note: "dependabot.yml ignores ruff and mypy updates on the basis that 'a security advisory still reaches us'. That needs Dependabot security updates switched on, which this session cannot read. See X2."}
    strength: |
      - Runtime dependencies are pinned, each with a written reason.
      - pip-audit is gating and clean ("No known vulnerabilities found", pip-audit 2.10.1).
      - Dependabot covers pip and github-actions, weekly, limit 5. No cooldown overrides the default.
      - Every shipped licence was checked, and all are GPL-3.0-compatible. That includes sigstore-models: its metadata omits the licence, but its bundled LICENSE is MIT.
      - The unmaintained musicbrainzngs sits behind an adapter, and local mitigations are recorded with removal conditions (DEPENDENCIES.md).
      - The cyanrip dependency is pinned by commit through a recorded two-sided approval: the approved pair.

  - n: 9
    name: distribution-and-packaging
    status: GAP
    finding: "No published surface names the copyright holder the owner gave (rmccann-hub, personally). pyproject `authors = [{ name = \"Platterpus contributors\" }]` and the metainfo `<developer><name>Platterpus contributors</name>` both name something the owner says is not a legal entity. No copyright notice exists: the only 'Copyright' in the tree is the FSF's, inside LICENSE."
    evidence: "`git grep -niE 'copyright' -- README.md LICENSE pyproject.toml 'build/python-appimage/*.xml' src/platterpus/__init__.py` -> LICENSE lines only (the FSF's). data/io.github.rmccann_hub.Platterpus.metainfo.xml:51-53. pyproject.toml:14."
    secondary:
      - {status: GAP, note: "Two install surfaces answer 'is this AppImage genuine?' differently. The in-app updater verifies the release's SHA-256 and its build attestation, fail-closed (update_attestation.py). install.sh, which the one-line installer runs from main, downloads the newest listed release's AppImage with `curl -fL` and checks neither (install.sh:123-133). install.sh and the two scripts it fetches (setup-host.sh, install-appimage.sh) are served from main (REPO_RAW=.../main), so a commit to main reaches installer users without passing release.yml's gates. Put to the owner as H1, not an order."}
    strength: |
      - The licence is locked and consistent everywhere: LICENSE (GPL-3.0 text), pyproject `license = "GPL-3.0-only"` (PEP 639), metainfo project_license, and PyPI's license_expression.
      - The AppImage is built with python-appimage, per Critical rule #2.
      - The wheel and sdist pass `twine check` and are published by trusted publishing.
      - Every AppImage release carries a SLSA provenance attestation, a .sha256 and a .zsync, and is built from the tagged commit.
      - The version has one source.

  - n: 10
    name: documentation-versioning-handoff
    status: DRIFT
    finding: |
      The public README asserts states that are no longer true.
      - README:15 says "5,400+ tests ... at 91.9% branch coverage". Measured today: 6,750 tests and 92.75-92.84%. The lower bound holds; the percentage is stale.
      - README:9 says "Status: v0.6.63 — out of beta", a recorded decision (52dfe0a2, 2026-08-17). The PyPI classifier still says "Development Status :: 4 - Beta" (pyproject.toml:28). The two public surfaces disagree.
    evidence: "check.py: '6730 passed, 19 skipped' (6750 collected on re-run). CI: 'Total coverage: 92.84%'. `git log -S'out of beta' -- README.md` -> 52dfe0a2 'feat: leave beta — rounds 8-11 closed, manifest-driven cyanrip build (#154)'. pyproject.toml:28."
    secondary:
      - {status: GAP, note: "There is no recovery runbook for a bad release. Production touches the public today, and nothing written says how to take a release back: yank the PyPI version; turn the GitHub release back into a draft or delete it (the updater reads `/releases?per_page=5` unauthenticated, so a draft disappears from its view); revert install.sh on main; withdraw a ripper pin through the fork. The only such line is docs/architecture.md:1822, inside the signing ritual: 'If you ever need to unpublish, delete the release assets'. Rated GAP, not the standard's no-runbook BLOCKER: the release runbook exists (CLAUDE.md CI/release steps 1-6, docs/architecture.md §6.1-6.3). What is missing is the recovery half."}
    strength: |
      - Version reconciliation is exact. The tree, tag v0.6.63, the GitHub release, PyPI's latest and the CHANGELOG head all agree, and the highest version ever on origin/main is 0.6.63 (128 distinct). Six numbers reached main without a PyPI release, each superseded.
      - The scheme is recorded: KDD-35 says what 0.x means and what earns 0.9.1 and 1.0.0; PEP 440 pre-release spelling is used; D7 covers untagged history; D15 covers betas.
      - Keep a Changelog is enforced in CI and again at release time.
      - Generated documents have --check modes, doc version stamps are tested, and the docs index is swept for completeness.

tally: {BLOCKER: 1, DRIFT: 6, GAP: 3, OVER: 0, MIRROR: 0, UNVERIFIABLE-HERE: 0, OK: 0, N/A: 0}
tally_sum: 10
secondaries:
  - {n: 2, status: GAP, note: "no lockfile; hash-verified AppImage path dormant"}
  - {n: 2, status: DRIFT, note: "gating pip-audit and cyclonedx-bom float against Critical rule #11"}
  - {n: 4, status: OVER, note: "CLAUDE.md 359 lines / 77,104 bytes"}
  - {n: 4, status: GAP, note: "no AGENTS.md or .claude/rules/"}
  - {n: 4, status: UNVERIFIABLE-HERE, note: "about 49 account-level skills load; provenance not establishable here"}
  - {n: 4, status: UNVERIFIABLE-HERE, note: "the 200-line and 32 KiB figures are dated facts, not re-checked"}
  - {n: 5, status: GAP, note: "one test discovers inputs from the working tree; collected count 6744/6749/6750"}
  - {n: 6, status: DRIFT, note: "tests-touched described as advisory in ci.yml and docs/testing.md"}
  - {n: 6, status: N/A, note: "branch protection: do_not_repropose"}
  - {n: 7, status: DRIFT, note: "private vulnerability reporting disabled while SECURITY.md names it"}
  - {n: 7, status: UNVERIFIABLE-HERE, note: "push protection, Dependabot alerts and security updates unreadable"}
  - {n: 8, status: UNVERIFIABLE-HERE, note: "Dependabot security updates unreadable"}
  - {n: 9, status: GAP, note: "install.sh does not verify the AppImage and is served from main"}
  - {n: 10, status: GAP, note: "no recovery runbook for a bad release"}
strengths:
  - {n: 1, note: "38 KDDs; 19 rulings with their options kept; declines carry reasons"}
  - {n: 2, note: "runtime pins agree across pyproject and the AppImage recipe, test-enforced"}
  - {n: 3, note: "one source root and one test root; docs index swept by a test"}
  - {n: 4, note: "enforced layer carries the audio invariant; hooks installed in cloud sessions"}
  - {n: 5, note: "6,750 tests, 92.8% branch coverage with a tag-read ratchet, own mutation sweep with floors"}
  - {n: 6, note: "least-privilege workflows, SHA pins, release job re-gates CI on the exact commit"}
  - {n: 7, note: "full public history clean; OIDC publishing; attestation verified in the app"}
  - {n: 8, note: "pip-audit clean; every shipped licence verified"}
  - {n: 9, note: "licence consistent on every surface; attested releases"}
  - {n: 10, note: "versions reconcile exactly; the scheme is recorded (KDD-35)"}
corrections: []   # no prior run of this standard exists here. docs/archive/audit-2026-07-21.md is a documentation audit by a different method: no opinion is formed from it (standard, Limitations)
validated:
  - {rule: "Read it at job and log level, not from the rollup — and read the skip list.", caught: "The gitleaks job is green at run, job and step level, and its log reads '0 commits scanned.' on the push to main."}
  - {rule: "So prove a gate by mutating what it guards, not by running it once.", caught: "A planted synthetic key merged through a PR is found in the PR's range and missed in the push range (0 commits). A key added inside a merge commit is missed even by `--all`. Reading the workflow could have shown neither."}
  - {rule: "Enabling a feature is not the same as satisfying what it needs, and the gap is silent.", caught: "SECURITY.md names private vulnerability reporting as its preferred channel, and the setting reads {\"enabled\": false}."}
  - {rule: "A collection guard compares against a recorded baseline, not against zero", caught: "The SBOM job's 'fewer than ten components' floor passes on the generator's own 35 components, with the project not installed at all."}
constrained:
  - {rule: "Stop at Phase 6. Nothing is written to the repository before explicit human approval.", stopped: "Running build_appimage.sh, the mutation sweep and handshake.py --status in the repository. The build script rewrites build/python-appimage/requirements.txt in place and the sweep mutates source files, so all three ran in a scratch clone at a930411."}
  - {rule: "An item recorded \"do not re-propose\" is never re-proposed.", stopped: "Raising the standard's own BLOCKER for an unprotected default branch that production deploys from directly, whose premise holds here because the one-line installer runs install.sh from main. Recorded in not_proposed instead."}
  - {rule: "Never route around the deny layer, and never propose weakening it to make your own work easier.", stopped: "Re-spelling the refused `rm -rf` (for example `rm -r -f`, which the prefix rule would not match) after the enforced layer denied it. The probe was restructured so it needed no deletion."}
  - {rule: "Verify a stated problem before acting on it.", stopped: "Taking the proposal's F9 ('f8ebf48 is still not on platterpus-fork') as current. A read-only clone of the fork shows f8ebf48 is now an ancestor of platterpus-fork b6c7368. It is recorded in notes as moved, fork-side, and kept out of any finding."}
overrides:
  - {phase: 0, saw: "The harness pins branch claude/serene-bell-gzywdr.", did: "Used it instead of chore/config-audit.", why: "The standard: 'use that and record it'."}
  - {phase: 0, saw: "The owner answered the three undetectable questions and the Phase 3 questions in the run file.", did: "Recorded them as asked directly, and still stopped at the Phase 3 wait.", why: "The owner's run instructions."}
  - {phase: 2, saw: "A shallow clone (509 commits), while CI checks out with fetch-depth 0, and two tests skip on a shallow clone.", did: "`git fetch --unshallow --tags`.", why: "To run the suite the way CI does. It is a fetch: .git only."}
  - {phase: 2, saw: "build_appimage.sh, mutation_sweep.py, handshake.py --status and the hook probe all write into the tree they run in.", did: "Ran them in a scratch clone at a930411, and passed check.py `--log-dir` in the scratchpad.", why: "The owner: write nothing to the repository before the gate."}
  - {phase: 2, saw: "The gitleaks job's binary is installed by a GitHub Action, not by apt or pip.", did: "Downloaded gitleaks 8.24.3 and verified it against gitleaks_8.24.3_checksums.txt before running it.", why: "Treated as that job's declared tooling. The owner's licence named apt and pip installs."}
  - {phase: 2, saw: "The changelog, media-guard and tests-touched jobs are inline shell in ci.yml.", did: "Extracted ci.yml:149-233, 254-298 and 433-516 and ran them with the push event's variables.", why: "Closest local equivalent. Not a GitHub runner."}
  - {phase: 2, saw: "mutation.yml has 15 legs of up to 90 minutes each.", did: "Ran the one leg CLAUDE.md documents and recorded the other 14 as NOT-RUN-HERE.", why: "Time-box. The weekly job is non-gating, and its last run is read at job level."}
  - {phase: 2, saw: "The standard's hook probe (`ls .git/hooks/pre-commit`) prints 'NOT INSTALLED' for a hook installed through core.hooksPath.", did: "Added `git config --get core.hooksPath`.", why: "Reading configuration by its effect. Proposed as standard amendment S2."}
notes: |
  Two repositories: rmccann-hub/cyanrip was read read-only (a blobless clone in the scratchpad).
  - The four shared seam files are byte-identical with the fork's copies at platterpus-fork b6c7368:
      docs/handshake-protocol.md (fork path docs/handshake/PROTOCOL.md)  sha256/16 05abdfde706316f8  72853 B
      docs/OWNERSHIP.md                                                   6956d0b9908a7784  11343 B
      docs/seam-rules.md                                                  a0d2139338c6e2b7  20270 B
      docs/seam-commands.md                                               7dc313815850eb60  58134 B
    Their own text says "neither owns it". The owner's run instructions call "the fork's" copies
    canonical. Both are noted; nothing here gates on the difference.
  - Both pins resolve on the fork: FORK_PIN e0471f4 and PIN_UNDER_REVIEW 51cc789 are ancestors of
    platterpus-fork. The branch head moved from b8d494a5 to b6c7368 during this run.
  - The fork carries 1087 commits over upstream master. Upstream's f8ebf48 (2026-08-21) is now an
    ancestor, so the proposal's F9 no longer holds. That is a fork-side fact, and the proposal file
    itself is off-limits.
  - The fork's PROVIDER-CONTRACT.md is now generated from .18 (`platterpus-fork-gd830ffb`). Our newest
    vendored copy is round 28's (g74872db). Vendoring .18 belongs to open round 29; consumer: this
    repository, provider: the fork.
  - None of the ten findings is owned by the fork. Every finding is this repository's.
  Dimension 4, account skills: this session's skill list carries 16 built-ins and 49 anthropic-skills:*
  entries. None comes from the repository.
```

## Phase 5 — Report

```yaml
phase: 5
table: |
  | # | Dimension | Status | Secondary | Strength | One-line finding |
  |---|---|---|---|---|---|
  | 1 | Stakes and lifecycle | GAP | — | 38 KDDs; rulings kept with reasons | No tier recorded in the decision record |
  | 2 | Language, runtime, environment | DRIFT | GAP, DRIFT | runtime pins agree, test-enforced | PyPI artifacts built with unpinned build/twine; a comment claims a lock that does not exist |
  | 3 | Structure and hygiene | GAP | — | one source root, one test root; docs index swept | No .editorconfig |
  | 4 | Agent configuration | DRIFT | OVER, GAP, UNVERIFIABLE-HERE x2 | enforced layer carries the audio invariant | The Claude-side audio guard fails open when git fails |
  | 5 | Testing and verification | DRIFT | GAP | 6,750 tests; 92.8% branch; own mutation sweep | [tool.mutmut] configures a tool nothing runs and cites a pin that does not exist |
  | 6 | Enforcement and review | DRIFT | DRIFT, N/A | least privilege; SHA pins; release re-gates CI | One [skip changelog] line exempts a whole range: 10 of the last 14 PRs unchecked |
  | 7 | Secrets, security, data | BLOCKER | DRIFT, UNVERIFIABLE-HERE | full public history clean; OIDC publishing | The "full-history" secret scan scans 0 commits on every push to main |
  | 8 | Dependencies | DRIFT | UNVERIFIABLE-HERE | pip-audit clean; every licence verified | The SBOM of "what ships" lists its generator, and its floor passes with the project absent |
  | 9 | Distribution and packaging | GAP | GAP | licence consistent; attested releases | No surface names the copyright holder |
  | 10 | Documentation, versioning, handoff | DRIFT | GAP | versions reconcile exactly; scheme recorded | README's figures are stale, and "out of beta" disagrees with the Beta classifier |
blockers:
  - n: 7
    why_now: "The repository is public, and at T3 its history is a distribution channel. The gate named for full history protects none of it on a push to main, and release.yml counts that job's green as evidence for every release."
    interaction: "It compounds with the unprotected main (a recorded ruling), because whatever reaches main unscanned is public at once. It is the same class as dimension 4's fail-open audio guard: a guard that reports clean while blind. And the ours-merges of 2026-09-26 and 2026-09-28 put commits no CI scan ever walked into main's history."
over_items:
  - n: 4
    recipe: "Split per this standard. The canonical file keeps enforced conventions, commands and the module map. Reference prose moves to docs/ and is linked from it. Per-subsystem rules (Qt threading, the seam, accessibility, releasing) move to .claude/rules/ with path scopes. CLAUDE.md becomes a shim that imports the canonical file with `@AGENTS.md`. Content is absorbed in the same commit, never stubbed, and the commit names the homes it rejected (KDD-20). Held by C3: it is amendment A7."
fired_triggers: []    # no prior entry of this standard; the repository's recorded declines carry no reopen triggers to fire
unfired_triggers:
  - {item: "Branch protection or rulesets on main (do_not_repropose)", gated_on: "No reopen trigger is recorded. Both of its reasons concern who can push (the commit axis), while the audience here is public (A3): a trigger set that mentions one axis is a blind spot on the other. Stated for the record, not proposed."}
  - {item: "Arming minisign update signing (KDD-37 D9)", gated_on: "'Never'. The ritual in docs/architecture.md §6.2 keeps it reversible; no trigger is recorded."}
category_checks: []   # the job did not ask for any
notes: "Findings are ranked for what they risk. The ranking is information, not an order of work."
```

## Phase 6 — Approval Gate — WAIT

```yaml
phase: 6
gate_artifact: "/tmp/claude-0/-home-user-Platterpus/0c33df2c-8092-51da-9d93-3432474abbba/scratchpad/RUN-REPORT-Platterpus-2026-09-28.md"
human_decisions:
  - id: H1
    question: "Should the first-install path verify what it downloads, and which ref should the one-line installer fetch? (a) install.sh checks the downloaded AppImage against its release's .sha256, and against its attestation (`gh attestation verify`) when gh is present, refusing on a mismatch; (b) as (a), and the one-liner fetches install.sh from the newest release instead of main; (c) no change."
    default_if_unanswered: "(c) no change; A16 stays unapplied."
    gates: [A16]
  - id: H2
    question: "Which stability claim is right: README's 'out of beta' (decided 2026-08-17), or PyPI's 'Development Status :: 4 - Beta'? (a) change the classifier to '5 - Production/Stable'; (b) keep the classifier and qualify the README, e.g. 'out of beta: the bN labels ended at 0.6.12; pre-1.0 per KDD-35'; (c) leave both."
    default_if_unanswered: "(c) leave both; A18 stays unapplied."
    gates: [A18]
  - id: H3
    question: "After applying, should this session open a pull request from claude/serene-bell-gzywdr to main so CI runs? CI triggers only on pull requests, pushes to main and manual dispatch, so pushing the branch alone produces no run: absent, not pending. Merging stays yours either way."
    default_if_unanswered: "No PR is opened by this session. The branch is pushed, and remote CI stays unread until you open a PR in the browser."
    gates: []
amendments:
  - {id: A1, dimension: 1, severity: recommended, held: no,
     change: "Record this audit as KDD-39 in PLANNING.md: tier T3 (B3/A3, basis current, owner-confirmed 2026-09-28), the standard version and run-file SHA-256, the do-not-repropose set carried forward with its sources, each amendment's outcome by id, and a reopen trigger for any new decline, worded in the axis it concerns.",
     evidence: "Phase 1 tier grep: none. Phase 3 confirmation.",
     if_accepted: "The next run of this standard starts in re-check mode: it shows the recorded answers instead of asking again, and carries every settled item forward.",
     if_declined: "The next run is another first audit. It re-derives the tier and has to be handed the rulings again.",
     gates_on: [none], severity_depends_on: [none], recommendation: "not pre-selected"}
  - {id: A2, dimension: 2, severity: recommended, held: "yes — a workflow (C3)",
     change: "publish-pypi.yml: install `build` and `twine` at measured, pinned ranges read from one place, the same `build>=1,<2` release.yml uses and twine at its measured minor.",
     evidence: "publish-pypi.yml 'pip install build twine' vs release.yml:275; DEPENDENCIES.md:20.",
     if_accepted: "The PyPI wheel and sdist behind every release are built with the same pinned tooling as the AppImage, and a `build` or twine release becomes a deliberate bump.",
     if_declined: "A `build` 2.x or twine release can change the published wheel and sdist with no change here, while the AppImage stays pinned. DEPENDENCIES.md keeps describing `build` as pinned.",
     gates_on: [none], severity_depends_on: [none], recommendation: "not pre-selected"}
  - {id: A3, dimension: 2, severity: recommended, held: no,
     change: "Make two records match reality. In build/python-appimage/requirements.txt, correct the cryptography comment ('fixed by requirements.lock') to say the lock is not committed yet. In DEPENDENCIES.md, add rows for the tools that build or gate a release and have none: twine, pip-audit, cyclonedx-bom, gitleaks.",
     evidence: "No requirements.lock; `grep -c -i twine DEPENDENCIES.md` -> 0.",
     if_accepted: "The recipe stops asserting a lock that does not exist, and the dependency record names every tool a release depends on.",
     if_declined: "A reader of the recipe believes the bundled cryptography is hash-locked, and DEPENDENCIES.md stays silent on the tool that validates every PyPI upload.",
     gates_on: [none], severity_depends_on: [none], recommendation: "not pre-selected"}
  - {id: A4, dimension: 2, severity: optional, held: "yes — it changes how round 29's closing release would be built (judgement)",
     change: "Generate build/python-appimage/requirements.lock with build/lock-requirements.sh in the release environment (ubuntu-22.04, bundled CPython 3.12) and commit it, so build_appimage.sh's existing hash-verified offline path activates. Regenerate it on every dependency bump.",
     evidence: "build_appimage.sh 'activates ONLY when the lock exists'; DEPENDENCIES.md:12.",
     if_accepted: "The AppImage's third-party bytes are pinned by hash, and a swapped artifact for a pinned version aborts the build.",
     if_declined: "Each AppImage build resolves online within the `~=` ranges, so two builds of one commit can bundle different patch releases. Cost of accepting: Dependabot does not update the lock, so every bump includes a manual regeneration.",
     gates_on: [none], severity_depends_on: [none], recommendation: "not pre-selected"}
  - {id: A5, dimension: 2, severity: optional, held: "yes — workflows and CLAUDE.md (C3)",
     change: "Make Critical rule #11 and CI agree. Either pin pip-audit and cyclonedx-bom to measured minors read from pyproject (a `ci` extra) and extend tests/test_gating_tools_are_pinned.py to them, or narrow the rule's text to the tools whose acceptance criteria move (ruff, mypy).",
     evidence: "ci.yml 'python -m pip install -e . pip-audit' and \"cyclonedx-bom>=7,<8\"; CLAUDE.md Critical rule #11.",
     if_accepted: "The rule and the configuration say the same thing, whichever way is chosen.",
     if_declined: "A pip-audit or cyclonedx-bom release can turn CI red with no code change, which is the failure rule #11 names, and the rule keeps claiming more than CI enforces.",
     gates_on: [none], severity_depends_on: [none], recommendation: "not pre-selected"}
  - {id: A6, dimension: 4, severity: recommended, held: "yes — .claude/settings.json (C3)",
     change: "Make the PreToolUse audio check fail closed and independent of the working directory. Run `git -C \"$CLAUDE_PROJECT_DIR\" diff --cached --name-only --diff-filter=ACMR`, check that it succeeded before trusting grep's silence, and refuse with exit 2 (the pre-commit hook's message) when git cannot list the index. Add a test that drives it with a broken producer, like tests/test_media_guard_hook.py does.",
     evidence: "Phase 4 dimension 4 probe: [hook exit 0] with a .flac staged and the index unreadable.",
     if_accepted: "All three audio guards follow the same refuse-when-blind rule, and the Claude-side guard inspects the project's index whatever directory a command starts in.",
     if_declined: "That guard allows every Bash call while git cannot read the index. The canonical pre-commit hook and CI's media-guard still refuse, so what is weakened is the extra layer, not the guard itself.",
     gates_on: [none], severity_depends_on: [none], recommendation: "not pre-selected"}
  - {id: A7, dimension: 4, severity: optional, held: "yes — CLAUDE.md (C3); it also carries the proposal's FK5/T5",
     change: "Apply the OVER split recipe (Phase 5): bring the always-loaded file to about 150-200 lines, give subsystems path-scoped rules, and make CLAUDE.md a shim importing `@AGENTS.md`. In the same work, correct CLAUDE.md's claim that check.py runs 'every gate CI runs': it runs 4 of the 9 gating jobs.",
     evidence: "CLAUDE.md 359 lines / 77,104 bytes; scripts/check.py `_build_gates`.",
     if_accepted: "Each session loads a fraction of 77 KB, and a rule loads when a file it governs is read.",
     if_declined: "Every session pays the full 77 KB before its first instruction. The proposal's FK5/T5 still carries the question to both sides.",
     gates_on: [none], severity_depends_on: [none], recommendation: "not pre-selected"}
  - {id: A8, dimension: 5, severity: recommended, held: no,
     change: "Delete the dead `[tool.mutmut]` block from pyproject.toml. Its history already lives in mutation.yml's header and in CHANGELOG.",
     evidence: "No reader outside CHANGELOG history; mutation.yml:9-45.",
     if_accepted: "The only mutation configuration is mutation.yml's matrix, and nobody edits a block that does nothing.",
     if_declined: "The block keeps describing a mutation scope and a workflow pin that do not exist, and an edit to it silently changes nothing.",
     gates_on: [none], severity_depends_on: [none], recommendation: "not pre-selected"}
  - {id: A9, dimension: 5, severity: optional, held: no,
     change: "Derive `_live_docs()` in tests/test_documented_ripper_flags_are_real.py from `git ls-files` (tracked .md/.txt) instead of `rglob`. This keeps its 'derived from disk, never hand-listed' design and closes the population.",
     evidence: "Collected 6744 / 6749 / 6750; the six extra ids are ignored build artifacts.",
     if_accepted: "One collection count in a fresh clone, in CI and after a run, and the test checks what the repository ships.",
     if_declined: "Counts differ by environment, so a collected count cannot be compared between runs, and an ignored scratch file can fail the suite locally.",
     gates_on: [none], severity_depends_on: [none], recommendation: "not pre-selected"}
  - {id: A10, dimension: 6, severity: recommended, held: "yes — a workflow (C3)",
     change: "Scope the changelog opt-out to what rule #7 exempts: a range skips the CHANGELOG check only when every commit in it carries the `[skip changelog]` line, and a mixed range must add a CHANGELOG line. The same edit corrects ci.yml's tests-touched header ('Advisory (never fails)'). Move the logic into a script under scripts/ with a test of fixture ranges: a records-only range skips; a mixed range with no CHANGELOG line fails.",
     evidence: "ci.yml:201-204; 10 of 14 recent PR ranges skipped; 5 misses on main.",
     if_accepted: "A records commit can no longer exempt the code commit beside it, and the gate checks the ranges it now skips.",
     if_declined: "The gate keeps skipping any range that contains a records commit. The CHANGELOG then stays current only because sessions follow rule #7, which they have since 2026-09-16, with nothing to catch a slip.",
     gates_on: [none], severity_depends_on: [none], recommendation: "not pre-selected"}
  - {id: A11, dimension: 6, severity: recommended, held: no,
     change: "Correct docs/testing.md:52 ('the advisory `tests-touched` nudge') to describe the gating job it has been since 2026-08-20.",
     evidence: "docs/testing.md:52; ci.yml:451-516.",
     if_accepted: "The testing strategy describes the workflow as it is.",
     if_declined: "The testing document keeps telling readers the job only warns.",
     gates_on: [none], severity_depends_on: [none], recommendation: "not pre-selected"}
  - {id: A12, dimension: 7, severity: recommended, held: "yes — a workflow and CLAUDE.md (C3)",
     change: "Replace the gitleaks-action step with a direct scan of the whole history on every run. Download gitleaks at a pinned version and verify its sha256 before running it. On the fetch-depth-0 checkout, run `gitleaks detect --source . --redact --exit-code 2 --log-opts=\"--all -m\"`, and fail when 'N commits scanned' falls below a recorded baseline (1458 today, ratcheting up). Then bring the four descriptions (CLAUDE.md:243, SECURITY.md:58, docs/architecture.md:1838, ci.yml:326-337) in line with what it does.",
     evidence: "Phase 4 dimension 7: push run '0 commits scanned.'; merge-content key missed by `--all`, found by `--all -m` (1458 commits, 23.0 s).",
     if_accepted: "Every push and pull request scans all public history, including merge commits' own changes and second-parent history (about 23 s measured), and a scan that sees nothing fails.",
     if_declined: "Push runs keep scanning 0 commits and reporting success. Merge-commit content and ours-merged history are never scanned in CI, and four documents keep promising a full-history scan.",
     gates_on: [none], severity_depends_on: [none], recommendation: "not pre-selected"}
  - {id: A13, dimension: 7, severity: optional, held: no,
     change: "Until A12 lands, correct the public SECURITY.md:58 and docs/architecture.md:1838 to say what CI scans today: each pull request's first-parent commits; push runs on merges scan nothing; a full-history scan is pending.",
     evidence: "As for A12.",
     if_accepted: "The public security policy stops promising a scan that does not happen.",
     if_declined: "The policy keeps overstating the scan until A12 is applied. Cost of accepting: SECURITY.md and CLAUDE.md:243 disagree until A12 lands, because CLAUDE.md is held.",
     gates_on: [none], severity_depends_on: [none], recommendation: "not pre-selected"}
  - {id: A14, dimension: 8, severity: recommended, held: "yes — workflows and CLAUDE.md (C3)",
     change: "Make the SBOM describe what ships. In the sbom job, run `pip install .` into a fresh venv and run cyclonedx-py from outside it against that venv's interpreter (40 components measured, no generator packages). Replace the ten-component floor with a check that the six runtime dependencies appear by name. Either attach the release build's SBOM in release.yml or delete ci.yml:371-372's claim that it is attached. Align the CLAUDE.md and SECURITY.md wording.",
     evidence: "Phase 4 dimension 8: 72 / 35 / 40 components; v0.6.63 assets.",
     if_accepted: "The SBOM lists what the wheel installs, and it cannot pass on the generator's tree alone.",
     if_declined: "The 'inventory of what ships' keeps listing about 30 tools that never ship, its floor keeps passing with the project absent, and ci.yml keeps promising a release attachment that does not exist.",
     gates_on: [none], severity_depends_on: [none], recommendation: "not pre-selected"}
  - {id: A15, dimension: 9, severity: recommended, held: no,
     change: "Name the copyright holder: pyproject `authors = [{ name = \"rmccann-hub\" }]`, metainfo `<developer><name>rmccann-hub</name>`, and 'Copyright (C) 2026 rmccann-hub' with the GPL-3.0-only notice in README's licence section. It reaches PyPI at the next release.",
     evidence: "Phase 3 answer 5; pyproject.toml:14; metainfo:51-53.",
     if_accepted: "Every published surface names who grants the GPL licence.",
     if_declined: "Published metadata keeps naming 'Platterpus contributors', which you say is not a legal entity, and no notice states who holds the copyright.",
     gates_on: [none], severity_depends_on: [none], recommendation: "not pre-selected"}
  - {id: A16, dimension: 9, severity: optional, held: no,
     change: "Implement H1's choice in install.sh: verify against the release's .sha256, plus `gh attestation verify` when gh is present, refusing on a mismatch; and, under H1(b), fetch install.sh from the newest release. Add a test through --dry-run.",
     evidence: "install.sh:31, :116, :123-133.",
     if_accepted: "First installs get the same answer to 'is this genuine?' that updates get.",
     if_declined: "The first install trusts TLS alone, while every update after it is verified fail-closed.",
     gates_on: [H1], severity_depends_on: [none], recommendation: "not pre-selected"}
  - {id: A17, dimension: 10, severity: recommended, held: no,
     change: "Add 'When a release is bad' to docs/architecture.md §6, a section in an existing home as KDD-20 requires. Steps: yank on PyPI (browser path); turn the GitHub release back into a draft or delete it (the updater reads /releases?per_page=5 unauthenticated); revert install.sh on main; withdraw a ripper pin through the fork (cite docs/cyanrip-handshake.md, restate nothing); then how to confirm the offer is gone. Every step browser-only.",
     evidence: "Phase 4 dimension 10; update_check.py:38.",
     if_accepted: "Recovery at the worst moment follows written steps a browser can carry out.",
     if_declined: "Recovery depends on memory, and KDD-35's 'a version number is a claim about the field' has no written way to withdraw a claim.",
     gates_on: [none], severity_depends_on: [none], recommendation: "not pre-selected"}
  - {id: A18, dimension: 10, severity: optional, held: no,
     change: "Apply H2's choice (classifier or README wording), and refresh README:15's test and coverage figures with a date.",
     evidence: "README:9, :15; pyproject.toml:28.",
     if_accepted: "PyPI and the README make one stability claim, and the figures carry the date they were measured.",
     if_declined: "The PyPI page says Beta while the README says out of beta, and the README's figures keep aging.",
     gates_on: [H2], severity_depends_on: [none], recommendation: "not pre-selected"}
  - {id: A19, dimension: 3, severity: optional, held: no,
     change: "Add a minimal .editorconfig: utf-8, lf, final newline; 4-space Python, 2-space YAML; trailing-whitespace trimming off for Markdown, where trailing spaces can be meaningful.",
     evidence: "No .editorconfig.",
     if_accepted: "Editors, including GitHub's web editor, apply one convention to the ~470 files ruff never formats.",
     if_declined: "Nothing breaks. Whitespace conventions stay per-editor.",
     gates_on: [none], severity_depends_on: [none], recommendation: "not pre-selected"}
standard_amendments:
  - id: S1
    class: standard
    target: "Phase 0 — Preflight"
    rule: "Fetch before you read refs."
    evidence: "After `git fetch --tags --prune` moved origin/main 88c09dd..a930411, the clone's local branch `main` stayed at 88c09dd5 (`git rev-parse main origin/main` -> 88c09dd5... / a930411b...). History scans that named `main` returned stale results: `git log --oneline -5 main -- src/platterpus/__init__.py` showed 'release: 0.6.60' as the newest bump in a 0.6.63 tree. The run caught it only because version reconciliation disagreed with the tag. One run: a data point, not yet a defect."
    proposed: "After the fetch, read the default branch through its remote-tracking ref (`origin/<default>`), never through a local branch of the same name. A fetch does not move local branches, and a clone's local default branch is exactly as old as the clone."
    if_accepted: "History scans read the branch the remote actually has."
    if_declined: "A run can report stale history as current with every command literal and every exit 0."
  - id: S2
    class: standard
    target: "Phase 2 — Inventory"
    rule: "ls .git/hooks/pre-commit 2>/dev/null || echo \"pre-commit NOT INSTALLED\""
    evidence: "It printed 'pre-commit NOT INSTALLED' while `git config --get core.hooksPath` -> '.githooks' and .githooks/pre-commit (-rwxr-xr-x) was installed and live: it refused the broken-producer probe with exit 1."
    proposed: "Read `git config --get core.hooksPath` first, and look for the hook there when it is set."
    if_accepted: "Repositories that install hooks through core.hooksPath (a common pattern, and the one a cloud SessionStart hook can set) are rated correctly."
    if_declined: "They are reported hooks_installed: no, a false negative on the client-side gate."
  - id: S3
    class: standard
    target: "Facts with an Expiry Date — Scanners and formatters"
    rule: "none — this is a gap"
    evidence: "gitleaks-action v3.0.0 (e0c47f4f), push event: 'gitleaks cmd: ... --log-opts=--no-merges --first-parent 9ff21de7...^..a930411b...' -> 'INF 0 commits scanned.' -> '✅ No leaks detected'. PR runs use the same `--no-merges --first-parent` shape over the PR's commits."
    proposed: "Add a dated fact: gitleaks-action builds its own `--no-merges --first-parent` range, so on a merge-commit workflow its push runs scan nothing and pass, and its PR runs skip merge commits and second-parent history. A secret-scan job is read by its range and its scanned count, never by its conclusion."
    if_accepted: "Future runs read a secret-scan job's range and count before crediting it."
    if_declined: "The next run on a merge-commit repository will rate the same job OK from its green tick."
human_actions:
  - {id: X1, action: "Turn on private vulnerability reporting: repository Settings → Advanced Security (Code security) → Private vulnerability reporting → Enable. SECURITY.md already names it as the preferred channel.", why_not_agent: "server-side: this session's token cannot change repository settings"}
  - {id: X2, action: "Check, and turn on anything that is off: Secret Protection with push protection, Dependabot alerts, Dependabot security updates (Settings → Advanced Security).", why_not_agent: "server-side: unreadable through this session's proxy"}
  - {id: X3, action: "Optional: consider release immutability (Settings → General → Releases). It freezes a release's tag and assets at publish, and release.yml's draft-first creation still works, but its `gh release upload --clobber` path for re-running an already-published release would then fail.", why_not_agent: "server-side, and a trade only you can weigh"}
  - {id: X4, action: "After apply: open the pull request, or tell me to (H3), and merge when CI is green. Merging is yours.", why_not_agent: "manual: merging is the owner's decision, and this session opens a PR only when asked"}
not_proposed:
  - {finding: "main is unprotected while production deploys from it directly: the one-line installer runs install.sh from main. This standard would rank that BLOCKER.", why_not: "do_not_repropose: maintainer ruling 2026-09-11, CLAUDE.md divergence (5), docs/github-workflow-sop.md §7. For the record only: GET /repos/.../rulesets answered http 200 `[]`, and the Facts table (2026-09) lists rulesets as free for public repositories, so the ruling's quoted cost reason may not apply. Its other reason (fast-forward-only proxy, nine gating jobs, releases through release.yml) stands. No reply needed.", dimension: 6}
  - {finding: "Update signing is not armed.", why_not: "KDD-37 D9 'Never'; the attestation check replaced it.", dimension: 7}
  - {finding: "Session branches merge with merge commits, not squash.", why_not: "CLAUDE.md divergence (6): a squash strands cited SHAs.", dimension: 6}
  - {finding: "No OpenSSF Scorecard workflow.", why_not: "Two of its checks, Branch-Protection and Code-Review, would score against a recorded ruling and a solo maintainer. The automatable half is already hand-rolled and test-enforced.", dimension: 8}
  - {finding: "No Dependabot grouping and no cooldown configured.", why_not: "The platform default applies and nothing is wrong. Adding a default-matching cooldown would be OVER.", dimension: 8}
  - {finding: "TASKS.md holds 513 done items out of 647.", why_not: "Reference volume costs nothing until opened, and moving it is KDD-20's call. The churn outweighs the value.", dimension: 10}
  - {finding: "No tags for 0.4.0-0.6.3, although PyPI holds those versions.", why_not: "Settled by KDD-37 D7.", dimension: 10}
  - {finding: ".gitattributes has no `eol=lf` for *.sh.", why_not: "There is no Windows checkout, `text=auto` already stores LF, and renormalising would cost a mechanical diff.", dimension: 3}
  - {finding: "No repository scratch/ directory.", why_not: "Critical rule #8 keeps scratch work, audio above all, outside the repository on purpose.", dimension: 4}
  - {finding: "apt runs without per-call timeouts in release.yml and mutation.yml.", why_not: "Both jobs have job-level bounds; a wedge fails loudly and can be re-run.", dimension: 6}
  - {finding: "The fork's .18 provider contract is not vendored yet.", why_not: "That is round 29's in-flight work (consumer: this repository; provider: the fork), held by the open round.", dimension: 8}
  - {finding: "The seam-automation proposal's F9 is stale (f8ebf48 is now on platterpus-fork).", why_not: "The proposal is off-limits, and the fact is fork-side. It is noted so it can travel with your next relay.", dimension: 10}
  - {finding: "Deny rules miss `rm -r -f`, `rm -Rf`, `find -delete` and `Bash(cat .env)`.", why_not: "No .env exists, and deny rules are a speed bump, not a sandbox, so more patterns buy little.", dimension: 4}
premise_check:
  stated: "The container lacks libEGL.so.1; check.py runs in about 2.5 min; PyPI since 0.4.0 on 2026-06-29; tagged releases publish the AppImage; the one-line installer runs install.sh from main."
  found: "All five reproduced. libEGL.so.1 was absent until CI's apt set was installed. check.py took 2 min 46 s. PyPI's 0.4.0 was first uploaded at 2026-06-29T19:50:47Z. v0.6.63 carries the AppImage. README.md:121 and install.sh:15 fetch from main."
  evidence: "Phase 2 and Phase 3 records."
counts: {human_decisions: 3, recommended: 11, optional: 8, amendments_total: 19, human_actions: 4, standard_amendments: 3}
closure_check: "recommended + optional == amendments_total -> 11 + 8 == 19"
no_writes_proof: |
  $ GIT_OPTIONAL_LOCKS=0 git status --porcelain
  (empty)
  [exit 0]
  $ git rev-parse HEAD origin/main
  a930411b4150b8244dbda0e3bca3c2022d35b765
  a930411b4150b8244dbda0e3bca3c2022d35b765
notes: |
  Held under C3, per the owner's instruction: A2, A4, A5, A6, A7, A10, A12, A14. If you approve them
  they are listed as held and not applied. Applicable once approved: A1, A3, A8, A9, A11, A13, A15,
  A17, A19, plus A16 and A18 when H1 and H2 are answered.
  Applying follows CLAUDE.md: a CHANGELOG bullet per commit (or a lone `[skip changelog]` line for a
  pure record), conventional subjects, `python3 scripts/check.py` before each push, a
  docs/session-log.md entry at the end, and the Tier-2 verification checklist's Final Report.
  No release, no merge, and nothing in the four seam files, the laps or the proposal.
```

---

## Phase 7 — Apply

```yaml
phase: 7
applied: [A1, A3, A8, A9, A11, A13, A15, A16, A17, A18, A19]
declined: []
deferred:   # approved and held under the seam-automation proposal's C3; KDD-39 records each
  - {id: A2,  trigger: "C3 lifts: both sides have answered the proposal and the owner approves (publish-pypi.yml is a workflow)"}
  - {id: A4,  trigger: "C3 lifts (it changes how round 29's closing release would be built)"}
  - {id: A5,  trigger: "C3 lifts, and the owner chooses the direction: pin pip-audit and cyclonedx-bom, or narrow rule #11"}
  - {id: A6,  trigger: "C3 lifts (.claude/settings.json)"}
  - {id: A7,  trigger: "C3 lifts (CLAUDE.md; it also carries the proposal's FK5/T5)"}
  - {id: A10, trigger: "C3 lifts (ci.yml)"}
  - {id: A12, trigger: "C3 lifts (ci.yml and CLAUDE.md)"}
  - {id: A14, trigger: "C3 lifts (ci.yml, release.yml and CLAUDE.md)"}
not_applicable:
  - {id: S1, why: "a change to the standard: the owner said S1-S3 are for claude-code-skills, not this repository (carried there as F39)"}
  - {id: S2, why: "same (carried there as F32, which this run confirmed)"}
  - {id: S3, why: "same (carried there as F40)"}
commits:
  - {sha: eddf0894, scope: "A9: the -x doc check sweeps git ls-files, falling back to the disk walk with no .git"}
  - {sha: a162b3f6, scope: "A8: delete [tool.mutmut]"}
  - {sha: 8e470db9, scope: "A3: four DEPENDENCIES.md rows; the lock comment"}
  - {sha: e4c30b27, scope: "A11: docs/testing.md on tests-touched"}
  - {sha: e3cf52a3, scope: "A13: SECURITY.md and architecture.md 6.3 on what gitleaks scans"}
  - {sha: 5e226623, scope: "A15: rmccann-hub as copyright holder"}
  - {sha: c0254661, scope: "A16 (H1 a): install.sh checks .sha256, and the attestation when gh is present"}
  - {sha: c310018c, scope: "A17: architecture.md 6.4, when a release is bad"}
  - {sha: a581a0cb, scope: "A18 (H2 b): README qualifier and dated figures"}
  - {sha: 6ceb318f, scope: "A19: .editorconfig"}
  - {sha: 21d7f075, scope: "A1: KDD-39 and the session-log entry, last, so the record describes the applied tree"}
  - {sha: 46e98bac, scope: "merge of main at 1a752e39 (five commits after the audit base); CHANGELOG and session-log conflicts resolved by keeping both sides"}
  - {sha: f3de966f, scope: "fix to A9's test: a fixture named a rig-script path that exists only where a wheel was built; CI failed on it"}
  - {sha: "(the commit adding this file)", scope: "this report, archived at the owner's request: 'give it all to me as a file back to the main repo'"}
fresh_clone_verification:
  done: yes
  result: >-
    Two attempts, and the first was not good enough. (1) A clone from the local repository at
    21d7f075: 6755 collected, the same as this tree with 11 untracked docs on disk, which is
    A9's point; but I ran only four test files there, not the gate. (2) After CI failed, a clone
    of the pushed branch from GitHub (origin/main 1a752e39, no build/) with the fix applied: the
    full suite passed (exit 0). Without the fix, that clone reproduced CI's failure exactly.
  without_fix: >-
    At a930411b (before A9): 6744 collected in a fresh clone, 6749 and 6750 in the working tree
    after `pip install -e` and a pytest run. Without f3de966f: test_rig_scripts.py's path sweep
    fails in a clean checkout on the fixture path build/lib/platterpus/rig_scripts/rigcancelandoverread.txt.
post_apply_commands:
  - {cmd: "python3 scripts/check.py --log-dir <scratch> (at 21d7f075)", result: PASS, collected: 6755}   # 4/4 gates; 6735 passed, 20 skipped; total coverage 92.75%
  - {cmd: "python3 scripts/check.py --only tests --no-coverage (second run, at 21d7f075)", result: PASS, collected: 6755}   # 6735 passed, 20 skipped: identical
  - {cmd: "python3 scripts/check.py on the merged tree before the merge commit existed", result: FAIL, collected: 6768}   # 1 failed: test_cited_commits_are_reachable, because main's commits were not yet reachable from HEAD; passes once the merge commit exists
  - {cmd: "python3 scripts/revert_probe.py probe-a9.json", result: PASS, collected: n/a}    # 4 reverts, 0 unexpected (re-run after each change to the file)
  - {cmd: "python3 scripts/revert_probe.py probe-a16.json", result: PASS, collected: n/a}   # 5 reverts, 0 unexpected
  - {cmd: "bash install.sh --no-host --yes against the real v0.6.63 release (real curl, gh 2.101.0 with no login, sandbox HOME)", result: PASS, collected: n/a}
  - {cmd: "ci-jobs/{changelog,media-guard,tests-touched}.sh as pull_request a930411b..21d7f075", result: PASS, collected: n/a}
  - {cmd: "gitleaks detect --log-opts='--no-merges --first-parent eddf0894^..21d7f075'", result: PASS, collected: n/a}   # 11 commits, no leaks
  - {cmd: "gitleaks detect --log-opts='-m origin/main'", result: PASS, collected: n/a}   # 1454 commits, 871 MB, 0 findings
  - {cmd: "pytest (full suite) in a clone of the pushed branch from GitHub, plus f3de966f's change", result: PASS, collected: n/a}
pushed: {branch: claude/serene-bell-gzywdr, head: f3de966fb6477c1bb239ee923df1e1b1d4a40fe6, on_remote: yes, proof: "git ls-remote origin refs/heads/claude/serene-bell-gzywdr -> f3de966fb6477c1bb239ee923df1e1b1d4a40fe6 (before the commit adding this file)"}
pull_request: {opened: yes, url: "https://github.com/rmccann-hub/Platterpus/pull/276", base: main, merged: no}
report_delivered: yes   # as this file on #276's branch, and sent to the owner
ci_remote_conclusion_after_push:
  status: "success"
  proof: "run 36495651678 on f3de966f: 12 of 12 check runs 'success' (lint, typecheck, changelog, media-guard, pip-audit, gitleaks, sbom, tests-touched, test py3.11-3.14). The py3.14 leg logged 'Required test coverage of 91% reached. Total coverage: 92.81%' and 'Session completed; recorded exit status: 0'. The run before it, 36494721181 on 46e98bac, failed all four test legs on A9's fixture (see corrections); f3de966f fixed it. The commit that adds this file has its own run, whose conclusion is on #276."
corrections:
  - {claim: "The first A9 commit (never pushed; rebuilt as eddf0894) passed the suite", actual: "Its fallback test's fixture string docs/archive/old.md read as a dead link to tests/test_doc_index_completeness.py's pointer sweep. Found before any push; the unpushed commits were rebuilt from a backup ref as eddf0894 and a162b3f6, and the saved work-in-progress was checked by hash.", where_corrected: "eddf0894", decision_affected: no}
  - {claim: "The first A16 commit (never pushed; rebuilt as c0254661) passed the suite", actual: "Its pytest.param(...) cases read as a computed population to tests/test_dynamic_sweeps_declare_a_floor.py. Found by check.py before the push; rebuilt as c0254661 with literal tuples and ids= (same test ids), with the four later commits cherry-picked on top.", where_corrected: "c0254661", decision_affected: no}
  - {claim: "A9's tests pass (locally, 21d7f075)", actual: "They passed here for the wrong reason. A fixture named build/lib/platterpus/rig_scripts/rigcancelandoverread.txt, and this container had a real build/lib/ from my own wheel builds, so test_rig_scripts.py's path sweep found it. CI's clean checkout does not have it, and all four test legs failed (run 36494721181). Fixed in f3de966f.", where_corrected: "f3de966f", decision_affected: no}
  - {claim: "A draft DEPENDENCIES.md row said release.yml installs pip-audit", actual: "release.yml only lists the job among those a release requires. Caught before the commit.", where_corrected: "8e470db9", decision_affected: no}
notes: >-
  main moved five commits (#275) while the amendments were applied, so #276 conflicted with its
  base, and GitHub ran no CI on it at all: mergeable_state dirty, zero check runs. That is S4
  below. Merging main in with a merge commit is this repository's convention for a session
  branch; the git proxy only allows fast-forward pushes, and a merge on top of the branch is one.
  After the gate, one question came back to the owner: N5 (below) would change A16's approved
  mechanism, so it is proposed, not applied.
```

## Phase 8 — Record

```yaml
phase: 8
recorded_at: "PLANNING.md (KDD-39), with the session entry in docs/session-log.md; this report is archived at docs/archive/config-audit-2026-09-28.md, with a row in docs/archive/README.md"
entries: [KDD-39]
standard_version_recorded: "PROJECT-BOOTSTRAP-AND-AUDIT v0.38.0 (run file sha256 fc2a96f68a32963785435274adf5058ff5e2054b18f53e6a03e334a112f05aa4)"
do_not_repropose_added: []   # four carried forward with their sources: branch protection (2026-09-11 ruling), arming signing (KDD-37 D9), squash merges (CLAUDE.md divergence 6), pre-0.6.4 tags (KDD-37 D7)
notes: >-
  Re-checked against the applied tree before KDD-39 was written, then again after main was
  merged in. No requirements.lock (A4 held). CLAUDE.md still 359 lines and 77,104 bytes (A7
  held). ci.yml's gitleaks step has no --log-opts (A12 held); one marked commit still opts a
  whole range out of the changelog gate (A10 held); the SBOM is still built with
  `cyclonedx-py environment` (A14 held). `git diff --stat origin/main HEAD` is empty for
  CLAUDE.md, .github/, .claude/, docs/handshake/ and the four shared seam files, both at
  a930411b and after the merge of 1a752e39. main's own new files under docs/handshake/ are the
  owner's round-28 work. One observation needed a correction (Conformance Self-Check): the
  Phase 4 "full history" gitleaks scan had excluded merge commits.
```

## Phase 9 — Plan Forward

```yaml
phase: 9
next_trigger: >-
  The owner's plan (2026-09-28): fix the standard first, then start a fresh run on both
  repositories' current heads. The event is therefore the next revision of the standard that
  takes in F39-F43 (already on claude-code-skills' branch claude/brave-pasteur-40a2fq) and
  S4-S10 below. KDD-39 lets that run start in re-check mode; whether it does is the owner's call.
  Independently, C3 lifting releases the eight held amendments, and each is re-checked against
  the tree of that day before it is applied.
outstanding_human_actions:
  - {id: X4, state: open, note: "review and merge #276 once its CI is green; decide N5 first (it concerns what the merge ships)"}
  - {id: X1, state: "reported done, not observed", note: "the API answered {\"enabled\": false} at 22:13 and 22:30 UTC"}
  - {id: X2, state: "reported done, not observable here", note: "those endpoints answer 403 through this session's proxy"}
  - {id: X3, state: skipped, note: "KDD-39 has its reopen trigger"}
sequence:
  - {step: 1, ids: [N5], why_here: "it decides what install.sh does for a user whose gh is too old, and the one-liner runs install.sh from main, so it takes effect at the merge"}
  - {step: 2, ids: [X4], why_here: "merging #276 makes the ten repository amendments true of main (A1 is the record)"}
  - {step: 3, ids: [X1], why_here: "SECURITY.md names private reporting as the only channel, and the API still says it is off"}
  - {step: 4, ids: [S4, S5, S6, S7, S8, S9, S10], why_here: "the standard's fixes, triaged in claude-code-skills with F39-F43, before the fresh run"}
  - {step: 5, ids: [A12], why_here: "when C3 lifts: the BLOCKER's fix, and a gate goes in before what it gates"}
  - {step: 6, ids: [A10, A2, A5, A14], why_here: "the remaining CI and release-tool gates, one concern per change"}
  - {step: 7, ids: [A4], why_here: "changes the AppImage's inputs; apply it after the round it would affect closes"}
  - {step: 8, ids: [A6], why_here: "the Claude-side guard; the other two guards already refuse"}
  - {step: 9, ids: [A7], why_here: "the largest documentation restructure, so last and alone"}
  - {step: 10, ids: [N1, N2, N3, N4], why_here: "found while applying; the fresh run raises them as amendments"}
milestones:
  - {name: "A first install is checked the way an update is", ids: [A16, N5, X4],
     verified_by: "curl -fsSL https://raw.githubusercontent.com/rmccann-hub/Platterpus/main/install.sh | grep -c 'gh attestation verify'  -> 1", done: no}
  - {name: "No credential reaches main unscanned", ids: [A12],
     verified_by: "the gitleaks job's log on a push to main shows a scanned-commit count at or above its floor, never '0 commits scanned.'", done: no}
  - {name: "Every tool that gates CI or builds a release is pinned and recorded", ids: [A2, A3, A5, A14],
     verified_by: "pytest tests/test_gating_tools_are_pinned.py, extended by A5 to pip-audit and cyclonedx-bom", done: no}
plan_home: decision record
plan_home_why: >-
  What remains is approved-and-held decisions whose release is itself a decision (C3), already in
  KDD-39 with its trigger, plus the standard's fixes, whose home is claude-code-skills' ROADMAP.md.
  Opening issues was not approved in this session; each item carries its id if the owner opens them.
notes: none
```

## Found while applying (N1–N5)

These were found after the gate, so none was approved. N1–N4 are for the next run to raise as
amendments. N5 concerns an approved change and needs the owner's answer now.

- **N1.** README's install section links `/releases/latest`, which reaches no v0.x release (the
  owner's words, 2026-09-28). Releases do carry `install.sh` (release.yml uploads it).
- **N2.** SECURITY.md's `gh attestation verify platterpus-x86_64.AppImage --repo
  rmccann-hub/Platterpus` needs `gh auth login`. Measured with gh 2.101.0: exit 4 without a
  login. With `--bundle` and the release's `.sigstore.json` it needs none (exit 0), which is how
  install.sh calls it.
- **N3.** `build/build_appimage.sh:318` embeds `gh-releases-zsync|rmccann-hub|Platterpus|latest|…`,
  and on GitHub "latest" excludes pre-releases. Whether AppImageUpdate-compatible tools therefore
  find no v0.x update at all was not verified here.
- **N4.** Other tree sweeps still walk the disk. `tests/test_rig_scripts.py::_live_text_files` and
  `tests/test_doc_index_completeness.py::_live_pointer_files` use `rglob`, and the rig-script
  sweep also resolves each path it finds against the disk. So an untracked `build/` can make them
  read files the repository does not ship, or pass on a path only a local build has. This run
  hit the second case (Phase 7 corrections). A9 fixed the same problem in one sweep; the fix
  there (the tracked set, falling back to the disk with no `.git`) would apply to these.
- **N5 (needs your answer: it would change A16's approved mechanism).** `install.sh` runs
  `gh attestation verify` whenever `gh` is on PATH. A `gh` too old to have the `attestation`
  command exits 1 (`unknown command "…" for "gh"`, measured with 2.101.0 on a missing
  subcommand), and the installer then refuses a download that is fine. Proposed: probe first
  with `gh attestation verify --help` (exit 0 where it exists) and treat a `gh` without it
  like no `gh`: install, and say the attestation was not checked, with a test for it. *If
  accepted:* no user is blocked by an old `gh`. *If declined:* a user whose distribution packages
  an older `gh` cannot use the one-line installer until they upgrade `gh` or remove it. Which
  distribution releases ship such a `gh` was not checked here.

## Standard amendments from the apply half (S4–S10), for claude-code-skills

Found after the gate, so they are not in the Phase 6 closure count. They go to the standard's
maintainers through claude-code-skills' triage, where the gate half of this report already became
F39–F43. Each is **one run's evidence**; S6 is the second time this run met F39's trap, by a
different route.

```yaml
standard_amendments:
  - id: S4
    class: standard
    target: "Phase 7 — Apply"
    rule: "Read the remote CI conclusion after pushing, before reporting done."
    evidence: >-
      #276 opened 22:42:18Z. get_check_runs -> {"total_count":0,"check_runs":[]};
      pull_request_read get -> "mergeable_state":"dirty". main had moved from a930411b to
      1a752e39 (5 commits) during the session. After merging main into the branch and pushing
      46e98bac at 22:50, 12 check runs existed; the first started 22:50:30Z.
    proposed: >-
      Before pushing, fetch the default branch. If it moved since Phase 2, bring it in by the
      repository's convention and re-run the gate. After pushing, an empty check-run list is not
      "pending": read the pull request's mergeability first. A pull request that conflicts with
      its base gets no pull_request workflow run at all.
    if_accepted: "A run cannot report CI as pending on a pull request that will never run CI."
    if_declined: "The remote-CI read returns nothing, and nothing reads as a wait, or as a pass."
  - id: S5
    class: standard
    target: "Phase 7 — Apply (Commit by concern)"
    rule: "Commit by concern, not all at once."
    evidence: >-
      Two of eleven commits failed the full suite and passed targeted runs of the tests that name
      the edited files: the first A9 commit (a fixture read as a dead link by the repository's pointer sweep)
      and the first A16 commit (pytest.param(...) read as a computed population by the dynamic-sweep gate).
      Both were found before the push and rebuilt.
    proposed: >-
      Run the repository's full gate before every push, and after any commit that adds a test. A
      targeted selection misses the repository's own sweeps over the tree, which are the tests
      most likely to fire on a new file. When the head is red before a push, find the commit and
      rebuild the unpushed commits instead of stacking a fix, so each commit passes on its own.
    if_accepted: "No commit that fails the gate reaches a shared branch."
    if_declined: "A commit-by-concern series can carry failing commits that head-only CI never sees."
  - id: S6
    class: standard
    target: "Phase 7 — Apply (Verify in a fresh clone)"
    rule: "Clone to a temporary path, follow the documented setup, run the gate, and record what fails without the new step."
    evidence: >-
      A clone from the local repository (git clone /home/user/Platterpus) mapped the container's
      stale local main to the clone's origin/main and failed three test_lap_language tests that CI
      passes. Running four test files there instead of the gate missed the failure CI then found.
      A clone of the pushed branch from GitHub, with the full suite, reproduced CI's failure and
      proved the fix.
    proposed: >-
      Clone from the remote, never from the working copy, and run the whole gate there. A local
      clone inherits the working copy's stale branches as its remote-tracking refs (F39's trap by
      another route), and a subset of the gate is not the gate.
    if_accepted: "Fresh-clone verification tests what a clone from the remote receives."
    if_declined: "A fresh-clone check can fail for reasons CI does not have, and pass while CI fails."
  - id: S7
    class: standard
    target: "Dimension 7, and F40's dated fact on a secret-scan job's range"
    rule: "F40 (pending): a secret-scan job is read by its range and its scanned count."
    evidence: >-
      gitleaks 8.24.3 with default log options on this repository: "1362 commits scanned". With
      --log-opts="-m origin/main": 1454 commits, 871 MB, 0 findings. In a replay repository, a key
      added only inside a merge commit was missed by --log-opts="--all" and found by
      --log-opts="--all -m".
    proposed: >-
      Add to F40: a by-hand full-history scan must include merge commits' own changes
      (--log-opts="-m <ref>" or "--all -m"). The default misses them, which is the job's blind
      spot again, in the check meant to verify it.
    if_accepted: "The run's own evidence for dimension 7 cannot share the defect it is checking."
    if_declined: "A clean hand scan can be cited while merge commits' content was never read."
  - id: S8
    class: standard
    target: "Phase 9 (outstanding_human_actions) and the report's List 3"
    rule: "outstanding_human_actions: [<X ids still undone>]"
    evidence: >-
      The owner, mid-run: "X1 and X2 are done". GET /repos/rmccann-hub/Platterpus/private-vulnerability-reporting
      (authenticated; X-Accepted-Github-Permissions: metadata=read; cache-busted) answered
      {"enabled": false} at 22:13 and 22:30 UTC. X2's endpoints answer 403 through the proxy.
    proposed: >-
      Give each human action a state: done-observed, reported-done-not-observed (with the reading),
      or not-observable-here. Never mark an action done on the owner's word alone when the run
      can read the setting.
    if_accepted: "The report says what was seen, beside what was said."
    if_declined: "A setting reported done and still off reads as done."
  - id: S9
    class: standard
    target: "Phase 8 — Record"
    rule: "A Phase 8 entry states the repository as it is at Phase 8, not as Phase 2 found it."
    evidence: >-
      KDD-39 was written against the branch at 21d7f075 (base a930411b). main then moved to
      1a752e39, and the merge brought 49 new files under docs/handshake/ plus edits to five files
      the branch had also changed. The held-path claim was re-checked on the merged tree
      (git diff --stat origin/main HEAD -- <held paths> -> empty).
    proposed: >-
      When the base moves between Phase 2 and the push, re-run the Phase 8 re-checks on the
      merged tree, and record both base SHAs.
    if_accepted: "The decision record holds for the tree that merges, not only for the one audited."
    if_declined: "A record re-checked before a merge can be false after it."
  - id: S10
    class: standard
    target: "Before You Start (what counts as a write), and F42"
    rule: "F42 (pending): whether ignored artifacts the gates leave in the working tree count as writes."
    evidence: >-
      Replaying CI's sbom job in the working tree built a wheel, which left build/lib/ with
      five copies of the rig scripts. In Phase 7 one of them made a test pass locally that CI
      failed (run 36494721181, all four test legs).
    proposed: >-
      Replay CI jobs that build or install in a scratch clone, not in the working tree. If a gate
      has to run in the working tree, remove its artifacts before Phase 7 and list them.
    if_accepted: "The run's own artifacts cannot mask a failure in its later phases."
    if_declined: "A run can certify its own changes against a tree its earlier phases polluted."
```

## Cross-repository survey (2026-09-28, about 22:55 UTC)

Read-only. Reading used git over the session's proxy (public repositories) and the GitHub API
for Platterpus. Nothing was changed outside Platterpus's session branch.

| Repository | Branches | Open work | What needs fixing |
|---|---|---|---|
| rmccann-hub/Platterpus | `main` (1a752e39); `claude/serene-bell-gzywdr` (#276, open); `claude/session-omka9f` (merged, #275) | #276 only | Merge #276 when green, after N5. Delete `claude/session-omka9f` in the browser; this session's proxy cannot delete branches. X1. The eight held amendments when C3 lifts. N1–N4. |
| rmccann-hub/cyanrip (the fork) | `platterpus-fork` (tip 2026-09-28, 1,090 commits ahead of `master`); `master` (mirror, 2026-08-21) | not read (no API access to the fork from this session) | Nothing stale found in its branches. Carried from the audit, fork-side: the seam-automation proposal's F9 is stale (f8ebf48 is now on `platterpus-fork`), which the owner relays; vendoring the fork's `.18` provider contract is round 29's own work. This session made no fork-side change. |
| rmccann-hub/claude-code-skills | `main` (v0.38.0, 2026-09-24); `claude/brave-pasteur-40a2fq` (6 commits ahead, 2026-09-28: F26–F43 and research R22) | that branch, unmerged | This audit's gate half is triaged there as F39–F43; its roadmap says "the apply half is triaged when it comes back", and this file is that apply half. Triage S4–S10 and N5's lesson as F44 and after, then merge the branch. |
| rmccann-hub/claude-skills-org | not opened (private, last pushed 2026-04-16) | — | Say whether this, rather than claude-code-skills, is "the organization claude skills repo". |
| rmccann-hub/leadtime-board, rmccann-hub/scheduling-engineV2 | not opened (private, unrelated to this work) | — | — |

## Working with a second session, live

Checked in this session rather than assumed. This session can be reached by other sessions as
`platterpus-d5`. `ListAgents` found no other session running. The messaging tool says it
directly: a cloud session receives messages but cannot send any back yet. So two cloud sessions
cannot hold a live two-way conversation today. These do work:

1. **One way, plus git.** A session started on claude-code-skills can be sent instructions from
   here (`SendMessage`). It works and pushes to its branch, and this session reads the branch
   with `git fetch` and answers with another message. This is the same pattern the Platterpus ↔
   fork handshake uses, where laps travel by git.
2. **You relay.** Paste between the two sessions. It works, but slowly.
3. **Helper agents inside one session** run concurrently and report back live. They share their
   session's repository access, so claude-code-skills would have to be attached to that session.

Recommended: start a session on claude-code-skills, point it at this file at the commit it is on
(`docs/archive/config-audit-2026-09-28.md` on `claude/serene-bell-gzywdr`), and have it triage
S4–S10 into its roadmap. If both sessions are live, this one can message it.

---

# Conformance Self-Check

```yaml
conformance:
  standard_version: "0.38.0"
  standard_sha256: "fc2a96f68a32963785435274adf5058ff5e2054b18f53e6a03e334a112f05aa4"   # the run file as received: 242239 bytes, end marker present
  job: audit
  sections_read: ["the owner's run instructions", "How to Read This File", "Before You Start (all sections)", "The Run: Phases 0-9", "File Governance", "Cross-Repository Contracts", "Conformance Self-Check", "Running this on a model that is not the one it was written against", "Proposing a change to this standard"]
  sections_skipped: ["The Release and Deploy Currency Gate (routing: skip for an audit)", "Choosing a Language and Runtime / Choosing the Shape / Project Shapes and Layout (no choice is itself a finding)", "Starter File Contents, The Configuration File Map, Any Agent Any Tool, Standards Distribution, Sending Results Back (not routed)", "Validating a Change to This Standard, Provenance (not in this extract)"]

  ten_statuses_emitted: yes
  tally_sums_to_ten: yes              # 1 BLOCKER + 6 DRIFT + 3 GAP
  new_vocabulary_coined: no
  fields_added_beyond_schema: "yes: the optional `corrections` block below. Amendments carry a `held` key, the owner's C3 marking (the claude-code-skills roadmap now carries this as F43). Phase 9's human actions carry a `state` (proposed as S8). Phase 4 hook-reading notes are YAML comments, not fields."

  waits_observed: 2                   # stopped at the Phase 3 wait ("Confirmed.") and at the Phase 6 gate (answered with H1-H3 and the approval list)
  wrote_before_approval: no           # nothing was committed before the Phase 6 answer; after it, only the approved amendments, a merge of main, one fix to an applied amendment, and this file (at the owner's request)

  proof_fields_hold_literal_output: yes   # elisions are marked and counted
  unverified_facts_relied_on: ["Anthropic's under-200-line target and Codex's 32 KiB limit (Facts table 2026-09): cited in dimension 4, not re-checked", "plan_supports_branch_protection: moot, do_not_repropose", "N5: which distribution releases ship a gh without the attestation command was not checked", "architecture.md 6.4: the exact place of GitHub's delete button and PyPI's yank menu in today's web UI"]
  premise_verified: yes               # all five of the owner's stated premises were reproduced (Phase 6 premise_check)

  amendments_pre_selected: no
  both_consequences_on_every_amendment: yes   # N1-N5 and S4-S10 carry theirs too
  actions_requiring_a_local_clone: 0
  declines_reproposed_without_a_fired_trigger: 0

  report_written: "docs/archive/config-audit-2026-09-28.md on claude/serene-bell-gzywdr (at the owner's request, 2026-09-28: 'give it all to me as a file back to the main repo'); the scratchpad copy it was assembled from is RUN-REPORT-Platterpus-2026-09-28.md"
  report_handed_over: yes

  deviations: 10                      # the 8 in Phase 4 `overrides`, plus two in Phase 7: EditorConfig 0.17.1 was installed in a scratch venv to check A19 (not a tool ci.yml installs), and this report was committed into the repository, which the run instructions had said to keep outside it, because the owner asked for it there
  honest_summary: >-
    Weakest where the container's state differed from CI's. Two local-only conditions each made a
    check read differently from CI: a build/lib/ my own wheel builds left made a test pass locally
    that failed in CI, and a clone from the working copy inherited a stale local main and failed
    tests CI passes. The first reached a pushed commit, and CI caught it. Also: two commits were red
    on their own before they were rebuilt, #276 conflicted with a base that moved during the session,
    the AppImage build and the repository's security settings could not be observed, and X1 is
    reported done while the API still says it is off.

corrections:
  - prior_run: "this run, Phase 4 (working notes, before emission)"
    prior_claim: "Highest version ever committed on main: 0.6.60. On PyPI but never on main: 0.6.61, 0.6.62, 0.6.63."
    actual: "The scans had read the clone's local `main`, which the fetch does not move (88c09dd5, release 0.6.60). Re-run on origin/main (a930411b): the highest version ever there is 0.6.63, and every PyPI version was on main. The emitted blocks carry only the origin/main readings."
    rule_that_caught_it: "A gap; proposed as S1, carried in claude-code-skills as F39."
    decision_affected: no
  - prior_run: "this run, Phase 4 (dimension 7's strength line)"
    prior_claim: "No credential in the 1362 scanned commits of public history (gitleaks 8.24.3, full history)."
    actual: "That scan used gitleaks' default log options, which read no merge commit's own changes: the job's blind spot again. Re-run with --log-opts=\"-m origin/main\": 1454 commits, 871 MB, 0 findings. The conclusion stands; the claim of a full-history scan did not, until the re-run."
    rule_that_caught_it: "Phase 8's re-check rule, applied while writing A13's SECURITY.md text, which cites the scan. Proposed for the dated fact as S7."
    decision_affected: no
  - prior_run: "this run, Phase 7 (fresh-clone verification, first attempt)"
    prior_claim: "A fresh clone collects 6755 tests and the new tests pass there."
    actual: "True, but the clone was taken from the working copy, and only four test files ran in it. The gate was not run there. That missed the failure CI found (run 36494721181). A clone from GitHub with the full suite reproduced it and proved the fix (f3de966f)."
    rule_that_caught_it: "The remote CI read (Phase 7), which is the backstop this standard requires. Proposed as S6."
    decision_affected: no
```

---

# Verification report (docs/TEST-VERIFICATION-CHECKLIST.md, Tier 2)

```text
VERIFICATION REPORT — Tier 2

RAN (with output recorded in the Phase 7 block):
  build ............ PASS  (pip install -e . ; the AppImage build is under DID NOT RUN)
  lint ............. PASS  (ruff 0.15.22: check and format --check)
  typecheck ........ PASS  (mypy 2.3.1: "Success: no issues found in 183 source files")
  full suite ....... PASS  (21d7f075: 6735 passed, 0 failed, 20 skipped; run twice, identical.
                            After the merge and the fix: the full suite passes in a clone from
                            GitHub; CI's conclusion is in the Phase 7 block)
  coverage ......... 92.75% total, statements and branches (CI enforces 91%)
  mutation ......... NOT RUN (see below)
  security scan .... PASS  (gitleaks over the PR's 11 commits and over all of main with -m:
                            0 findings; CI's pip-audit job: success)

DID NOT RUN (and why):
  scripts/mutation_sweep.py — no src/platterpus module changed. The targeted equivalent ran:
    revert probes, 4 of 4 for A9 and 5 of 5 for A16.
  AppImage build — python-appimage's GitHub API call is refused by this session's proxy (403,
    Phase 2). A3's change to the recipe is a comment.
  suite in random order — the dev extra has no pytest-randomly, and adding a dependency needs
    the maintainer's approval (DEPENDENCIES.md).
  appimage.yml — it runs only on a push to main or by dispatch.
  the full suite at every intermediate commit — only at the head, plus targeted tests per
    commit. That is how two intermediate failures were missed until the full run (S5).

KNOWN GAPS:
  X1 is reported done, and the API still says it is off; X2 cannot be read from here.
  install.sh's refusals are tested against a fake release only; the real release was run once,
    for the accepting path.
  N5: an installed gh without the attestation command makes install.sh refuse a good download.
    It is reported, not fixed, because the fix changes an approved mechanism.
  N3 (the zsync update information names "latest") was not tested against an
    AppImageUpdate client.
  architecture.md 6.4's descriptions of GitHub's and PyPI's web UI were not checked against the
    live pages.

RISKS I AM NOT COMFORTABLE WITH:
  This container made two checks read differently from CI (a stale build/lib/, a stale local
    main). The evidence I trust is the full suite in a clone from GitHub and CI itself.
  A16 changes the installer the one-liner runs from main, so it reaches every new install at the
    merge, with no release in between. N5 is the known way it can refuse a good download.
  Other tree sweeps still walk the disk (N4), so the class A9 fixed remains elsewhere.

CONFIDENCE: medium. The applied changes are tested, and their tests were proved able to fail,
but this run twice mistook its own container for CI, and one of those reached a pushed commit.
```

---

*Last updated for Platterpus v0.6.63.*
