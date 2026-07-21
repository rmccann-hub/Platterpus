# CLAUDE.md — Platterpus Project Context

This file is loaded by Claude Code on every session in this project. It captures the persistent rules and constraints for the codebase. The **rules** section below the line is locked — do not edit it without explicit user confirmation. The **project operations** section at the bottom grows as the project develops.

---

## Project

Linux GUI front-end for the `cyanrip` audio-CD ripping CLI. EAC-equivalent archival quality, single-file AppImage distribution. Primary target: Bazzite Linux with KDE Plasma 6. Secondary: Fedora, Arch, Ubuntu, and other modern desktop Linux.

## Stack (locked)

- Python 3.11+
- PySide6 (Qt6) for the GUI
- `subprocess` for the ripper CLI invocation (cyanrip — the sole backend, KDD-18; whipper was removed 2026-06-30)
- `python-musicbrainzngs` for MusicBrainz lookups (so the ripper never shows its own interactive prompt)
- TOML config at `~/.config/platterpus/config.toml`
- `python-appimage` for AppImage builds
- `pipx` install as the secondary distribution channel

## Architecture (locked)

The GUI runs on the host. It calls the host-exported ripper binary in `~/.local/bin/` (currently `~/.local/bin/cyanrip` — see KDD-18 / the Stack note below; the historical `~/.local/bin/whipper` worked the same way), which transparently enters the Distrobox container named `ripping` to do the actual ripping work. The GUI never tries to run the ripper in its own process, install it itself, or assume a native ripper on the host. **This routing is non-negotiable** — it's how the user's system is configured and the brief disqualifies any distribution that can't reach it.

## Code conventions

- **Comments:** heavy. The maintainer has limited programming experience — comment intent, not mechanics. A reader who can read Python but doesn't deeply know Qt or cyanrip should understand the file.
- **Type hints:** mandatory on all function signatures, class attributes, and module-level constants.
- **Modules:** small and focused. Split when a file exceeds ~300 lines. One responsibility per module. The line count is a *heuristic for cohesion*, not a hard cap — don't split a cohesive 350-line file to hit a number, and *do* split a 200-line file that's secretly doing three jobs. A heavily-tested Qt "god-object" (e.g. `MainWindow`) is split via **mixins** the concrete class inherits, so methods stay reachable as `window._x` (which tests and Qt signal wiring depend on) while each concern lives in its own focused file — see `docs/architecture.md`.
- **No clever metaprogramming.** Avoid decorators that mutate behavior unobviously, dynamic class creation, monkey-patching, or "magic" imports.
- **Never block the GUI thread.** Any operation that can take more than a few milliseconds — `subprocess.run`, network I/O, large-file hashing/copying, `thread.join()`, `kbuildsycoca6` — must NOT run on the Qt main thread; a blocked event loop shows "Not Responding" and ignores every click until it returns. Need the result → a `QObject` worker on a `QThread` (or a daemon thread that reports back via a queued signal). Don't need it → fire-and-forget `subprocess.Popen(..., start_new_session=True)`. This rule was written in blood — it has now bitten **three** times: the in-app-update freeze and several latent freezes (2026-06-13), and the dependency **install** freeze (2026-06-30, shipped in 0.4.2) where a Picard Flatpak install ran on the GUI thread *inside a modal dialog's `exec()`* and locked the whole window. **The recurring trap is a modal dialog that does the blocking work itself in a button slot** — `exec()` runs a nested event loop, but the slot still blocks the GUI thread. Any dialog that installs/downloads/probes MUST run that work on a worker thread and report back via queued signals (see `docs/architecture.md` "Dialogs that do blocking work"); the injected install/work callable must be **thread-safe** (no Qt, no opening sub-dialogs). When reviewing a change, ask: *if this ran on a stalled network or a cold container, would the window freeze?* — and specifically: *does any dialog slot call subprocess/network/`exec` synchronously?*
- **Error handling:** catch specific exceptions, never bare `except:`. Log with the `logging` module, not `print`.
- **Validate every input and every dependency output — visibly, and to the log.** (Added 2026-07-01 after a real-hardware session found this was *nowhere* a written requirement — which is exactly why Settings inputs had only ad-hoc, per-widget range limits and no systematic checking. Institutional now.) Two obligations:
  - **Inputs:** every value that enters the program from outside the code — user-entered Settings (paths, templates, tool paths, numbers), config-file values, CLI args — is validated for *type, range, character set, and format* at its boundary before it's used or persisted. Invalid input gets a **visible, specific error at the point of entry** (the user must see *what* is wrong *as they change it* — not a silent reset, not a crash later), and the failure is **logged to the log file** (`logging.warning`/`error`) so a bug report carries it. Validation logic lives in a **pure, testable function** (e.g. `settings_validation.py`), never scattered inline in widget slots — same shape as the dependency subsystem (Critical rule #6). A GUI widget's own constraint (a `QSpinBox` range) is a *convenience*, not the validation — the pure validator is the source of truth and is what tests assert against.
  - **Outputs to dependencies:** before invoking an external tool, validate that the arguments we hand it satisfy that tool's documented contract (see `docs/dependency-contracts.md` — the single reference for allowable args/syntax/output per dependency). When a dependency fails or emits an error, **capture its stderr/stdout and log it** (never swallow it) so the failure is diagnosable. Parsers of that output still **never raise** (below) — validation and best-effort parsing are complementary, not alternatives.
- **Subprocess output parsing:** robust to cyanrip minor-version output changes. Use named-group regexes, not column-index splits. Parsers of external output **never raise** — they return a best-effort dataclass and get a `hypothesis` "never raises" property test.
- **Naming:** snake_case for functions, variables, modules; PascalCase for classes; SCREAMING_SNAKE_CASE for module-level constants.

## Critical rules

1. **External tools and unmaintained dependencies require adapter layers.** Currently flagged: `python-musicbrainzngs` and `appimage-builder` (if ever reached for) are unmaintained; `cyanrip` is the external ripper (actively maintained, but still an external CLI). Every call into these MUST go through a thin adapter module so a future replacement is feasible without rewriting the GUI — the `RipBackend` ABC (`adapters/rip_backend.py`) is exactly this seam, which is what let whipper be swapped out for cyanrip cleanly (KDD-18). Adapter modules are mandatory, not optional.

2. **`python-appimage` is the AppImage builder.** Do not use `appimage-builder` without stopping and asking first. If a build requirement cannot be expressed in `python-appimage`, describe the specific limitation in detail before reaching for any alternative. If `appimage-builder` is approved as a fallback, the recipe must stay close enough to vanilla that swapping back is cheap.

3. **Distrobox routing is sacred.** The GUI calls the host-exported ripper in `~/.local/bin/` (currently `~/.local/bin/cyanrip`). It does not call into the container directly, does not assume a native ripper, does not try to install or update the ripper itself. (The ripper *binary* changed — whipper → cyanrip-only, 2026-06-30, KDD-18 — but the routing pattern is unchanged and remains non-negotiable.) The one scoped, user-approved exception (2026-05-31): force-stopping a runaway drive on rip-cancel may kill the reader process — device-scoped on the host first and, only if the host saw nothing, inside the container — see `drive_control.py` and the drive/reader-control section of `docs/dependency-contracts.md`.

4. **FLAC is the default and the archival master; MP3, WavPack, and WAV are derived outputs.** (Superseded the original "FLAC only for v1" — multi-format shipped 2026-06-26 with the maintainer's explicit sign-off; FLAC stays the lossless master.) Every rip produces FLAC first (lossless, provably bit-perfect); when the user selects another format in Settings the GUI **keeps that FLAC** and derives the chosen format from it via the *single* post-rip transcode adapter (`adapters/transcode.py`). FLAC and WavPack are lossless; MP3 is best-practice VBR (lossy by design — "not for that use"); WAV is raw PCM (no tags/art — the UI warns). Every encoder routes through the same dependency self-management subsystem — **no bespoke per-encoder install code**. A new format extends the one transcode adapter + the one dep subsystem; it never gets its own install path.

5. **No bypass of MusicBrainz query path.** Always query MusicBrainz via the `MusicBrainzClient` adapter (currently backed by `python-musicbrainzngs`) to obtain the release first. The ripper's own metadata lookup is always disabled (cyanrip runs with `-N` and is fed the GUI's already-fetched, user-edited tags via `-a`/`-t`), so its interactive prompt never surfaces and the rip needs no in-container network.

6. **Dependency self-management is one subsystem, not scattered checks.** All "is this dependency present and the right version" logic lives in a single module with the three-tier resolution strategy (auto-install → queued install → copyable search string). New dependencies route through it; no ad-hoc availability checks elsewhere in the codebase.

7. **Documentation currency is part of "Done."** A change isn't finished when the tests are green — it's finished when the *record* matches the code. This rule is the always-loaded anchor; it **daisy-chains** to the rest, so the one file guaranteed to be read every session pulls the others in. Three obligations, in order:
   - **In the same commit as the change:** add the `CHANGELOG.md` `[Unreleased]` bullet (mechanics under *Project operations → Single record of changes*; CI backstops this). Pure historical-record commits (e.g. a session-log catch-up) are exempt and mark themselves with a `[skip changelog]` line of its own in the commit message.
   - **Before ending a session:** append a `docs/session-log.md` entry (newest-first) — what was built, decided, learned.
   - **Graduate every durable lesson to its real home** — a Critical rule or Code convention *here*, a KDD in `PLANNING.md`, or `docs/architecture.md` / `docs/testing.md` — so the rule lives where it's read and the log keeps only the dated entry. A lesson left *only* in the log is not graduated.

   The full code-and-docs checklist is the **Definition of Done in `docs/testing.md §6`**. Same bite as the regression-test rule: institutional, non-negotiable.

8. **No copyrighted media in the repo — ever, not even temporarily.** This repository is public. Never `git add`/commit a music file or any other copyrighted media — **no `.flac`, `.wav`, `.mp3`, `.m4a`, `.aac`, `.ogg`, `.opus`, `.wv`, `.ape`, `.aiff`, `.dsf`, etc.** — and this includes *temporary* files dropped in for testing. Owning the disc does not grant redistribution rights, and a public commit (and git history) is redistribution. **How we test with real audio instead:** work on it **outside the repo** — the session scratchpad or a `/tmp` dir — and delete it when done; the durable proof we commit is the **text** artifact (EAC/whipper/cyanrip **logs** + per-track **CRCs**), never the audio (the CRCs prove bit-perfection without it — see `output_reference/README.md`). `.gitignore` denies audio extensions as a backstop, but the rule is the line of defense, not the backstop. If a test genuinely needs real PCM, use a **short, self-generated or CC0/public-domain** sample, never a commercial track. Same bite as the rules above: institutional, non-negotiable.

## Deviation policy

When in doubt during any session, stop and ask the user before doing the following:

**Must ask before doing:**
- Adding a dependency not listed in `DEPENDENCIES.md`
- Changing the distribution model
- Switching the GUI framework
- Skipping, reordering, or redefining a P0 feature
- Reaching for `appimage-builder`
- Bypassing the host-exported `~/.local/bin/<ripper>` routing (currently cyanrip)
- Adding scattered dependency checks outside the self-management subsystem

**Just do it (no ask needed):**
- Renaming a function, variable, or local module
- Splitting an oversized file into focused submodules
- Small refactors for readability or to match project style
- Adjusting type hints, docstrings, or comments
- Reordering imports or reformatting per the linter

The line between these is judgment. When in doubt, the safer call is to stop and ask.

## Working with the maintainer (learned)

This project is as much about building durable standards as shipping the app — so this section captures what past sessions learned about *how this maintainer works and what they value*. Treat it as guidance, not law.

- **North star: "good music, good cover image, good everything."** The goal isn't "a rip" — it's a complete, trustworthy library entry: bit-perfect audio (provable via CRCs), correct tags, embedded cover art. When weighing work, favor what moves the whole experience toward that.
- **UX responsiveness is a feature, not a polish item.** The maintainer notices and reports freezes, dead buttons, and "Not Responding" windows immediately, and values them fixed ("users value those to be as responsive as possible"). This is why the GUI-thread rule above exists. A working feature that *feels* broken (frozen, silent, ambiguous) is a bug.
- **Zero-terminal for end users.** The target user downloads one file, double-clicks, and answers prompts — no command line. Distribution and setup decisions are judged against that bar (KDD-17).
- **Limited programming experience → optimize for the next reader.** Comment intent, not mechanics. Explain *why*. Spell out reasoning rather than asserting; the maintainer asks "is this arbitrary or is there a reason?" and deserves the reason. Prefer clarity over cleverness everywhere.
- **Build for contributors who aren't them, in ways not yet conceived.** Leave extension seams and document them (`docs/architecture.md`). Modular, adapter-bounded, test-covered code is the deliverable — not just working code.
- **Real hardware is the ground truth.** Many of the best fixes came from real-disc testing on the Bazzite + Pioneer BDR-209D rig (the >587 offset bug → cyanrip; the cdrdao TOC flake → Rescan; the EAC baseline). Code-side prep is welcome, but the final proof is a hardware run; flag hardware-gated work honestly.
- **Every shipped bug gets a regression test in the same change.** Institutional, non-negotiable (see `docs/testing.md`).
- **Momentum with safety.** The maintainer pushes for autonomous forward progress ("proceed", "get it done") — so act on reversible, in-scope work without asking, commit in small test-green units, and report at milestones. Still stop for destructive or scope-changing decisions.
- **Autonomous releases are expected.** Cut releases via the `workflow_dispatch` path from the cloud session (see CI/release below); don't wait for a manual tag push.

## Companion documents

Read these alongside this file when picking up a session. **`docs/README.md` is
the canonical annotated index** — one line each here (so this list can't drift
from it again; it did once, KDD-range v23 vs v25):

- **`PLANNING.md`** — architecture, module map, and the numbered KDD decision log
- **`TASKS.md`** — the active task checklist; update status (`[ ]` → `[~]` → `[x]`) in the same commit as the work
- **`DEPENDENCIES.md`** — dep pins, review cadence, retirement log
- **`README.md`** — outward-facing description + install instructions
- **`SECURITY.md`** — security policy (supported versions, vulnerability reporting)
- **`docs/README.md`** — the complete annotated index of docs/, the single-source-of-truth map, and the rebuild checklist
- **`docs/architecture.md`** — the contributor guide: patterns with their *why*, extension recipes. **Start here to extend the program.**
- **`docs/testing.md`** — testing strategy, institutional rules, and the Definition of Done (rule #7's checklist)
- **`docs/test-plan.md`** — manual & release testing (acceptance run, EAC parity, gated hardware cases)
- **`docs/dependency-contracts.md`** — exact args/flags per external tool + parsed output shapes
- **`docs/platterpus-research-brief-v2.1.md`** — the project brief; canonical for requirements/scope *as amended by the KDDs*
- **`docs/ux-design-principles.md`** — the trust-first UX principles + the canonical gap backlog
- **`docs/session-log.md`** — per-session chronology (newest first); lessons graduate out of it (rule #7)
- **`docs/ripper-engine-strategy.md`** — living fork/engine research (+ companions: `upstream-pr-roadmap.md`, `cyanrip-soft-fork.md`, the `scripts/cyanrip/` kit)
- **`docs/archive/`** — retired dated investigations + external reference; graduation map in its README

Everything else under `docs/` (log-format comparison, mp3-wav design-of-record,
CTDB CRC spec, EAC investigations, GitHub SOP, AppImage testing, dated audits)
is indexed with one-line descriptions in `docs/README.md`.

If `PLANNING.md` and the brief conflict, the brief **as amended by the maintainer-approved KDDs** wins on requirements/scope and `PLANNING.md` wins on implementation choices. If `PLANNING.md` and the research output conflict, raise it with the user — don't silently pick.

There is no `compass_artifact_*.md` in the repo; the original v1 research validation was unavailable when the project was bootstrapped, so the project proceeded against the brief alone. To refresh tool-choice research, follow `docs/platterpus-session-start.md` Step 0.

---

## Project operations

*This section grows as the project develops. Add concrete commands, paths, and operational notes as they're established. Keep entries terse.*

### Build commands

- AppImage: `bash build/build_appimage.sh` (produces `platterpus-x86_64.AppImage` at repo root via `python-appimage`)
- App icon: `python3 build/make_icon.py` (regenerates the committed `build/python-appimage/io.github.rmccann_hub.Platterpus.png` from `assets/platterpus-logo.svg`; needs an SVG rasterizer on PATH — `rsvg-convert`, Inkscape, ImageMagick, or the `cairosvg` module — **not** Pillow)

### CI / release

- **CI:** `.github/workflows/ci.yml` runs on every push to `main` and every PR. **Gating jobs:** `test` (pytest on the 3.11–3.14 matrix + the coverage floor), `lint` (`ruff check` + `ruff format --check`), `typecheck` (`mypy`, config in `pyproject.toml` `[tool.mypy]` — strict def-typing across the whole package), `changelog` (the rule-#7 backstop), `media-guard` (the rule-#8 backstop), and `pip-audit` (dependency vulnerabilities). **Advisory:** `tests-touched` warns (never fails) when `src/` changes without a `tests/` change. Two more workflows: `mutation.yml` runs mutation testing **weekly, non-gating**, and `appimage.yml` builds + smoke-tests the AppImage on every push to `main` and on demand for any branch (see `docs/appimage-testing.md`).
- **Releasing is automated** — do *not* hand-build/upload. Cut a release by pushing a version tag (`git tag vX.Y.Z && git push origin vX.Y.Z`) **or by dispatching the Release workflow with the tag as input — it creates the tag itself (works from the cloud session via the Actions API; tag pushes don't)**. `.github/workflows/release.yml` then builds the AppImage (reusing `build/build_appimage.sh`) and attaches it + a `.sha256` + the `.zsync` self-update file to a GitHub Release, with a signed build-provenance attestation; it then dispatches `publish-pypi.yml`, which publishes the wheel+sdist. `v0.*` tags publish as pre-releases. Before tagging: **(1)** bump the version in **`src/platterpus/__init__.py` (`__version__`)** — this is the *single source*; `pyproject.toml` reads it dynamically, so do **not** add a version there — and **(2)** move the `CHANGELOG.md` `[Unreleased]` entries under a new `## [X.Y.Z] — <date>` heading with a matching compare link.
- **Single record of changes:** every notable change is recorded in **`CHANGELOG.md`** (the one authoritative update log; Keep-a-Changelog style). Add a bullet to its `[Unreleased]` section **in the same commit** as the change. `PLANNING.md` (KDDs) and `docs/session-log.md` are for *design decisions and session history*, not the user-facing change record.

### Commit & PR hygiene

The general GitHub mechanics + etiquette live in **[`docs/github-workflow-sop.md`](docs/github-workflow-sop.md)** (identity/SSH, fork+PR, atomic commits, the seven commit-message rules, PR anatomy, merge strategies, conflict resolution) — read it for *upstream* contributions especially. **This section is the authority for *this* repo and wins wherever the generic SOP differs.** What we actually do:

- **Atomic commits.** One logical change per commit — don't mix a fix with an unrelated refactor. Small, test-green units keep review, `git bisect`, and `git revert` surgical.
- **Conventional-commit subject:** `type(scope): imperative summary` — **lowercase** after the colon, no trailing period, concise (aim short, but the `type(scope):` prefix + a release subject legitimately run past 50 chars — clarity over a hard cap). Types in use: `feat`, `fix`, `docs`, `test`, `refactor`, `style`, `chore`, `release`. Blank line, then a body wrapped ~72 cols that explains **what and why, not how** (the diff shows how).
- **Required trailers** on every commit (per the harness rules): the `Co-Authored-By:` line and the `Claude-Session:` line. Never put the model identifier in a commit, PR, or any pushed artifact.
- **Changelog in the same commit** (Critical rule #7) — or a standalone `[skip changelog]` line for a pure historical-record commit. CI backstops this.
- **Branch:** commit only to the session's designated `claude/…` branch; never push to `main`. Prefer `git switch` over `git checkout` for branch ops.
- **PRs squash-merge into `main`** — one `main` node per complete, deployable change. Merge only when CI is green (the `pytest` 3.11–3.14 matrix + coverage floor, `ruff` lint/format, `mypy` typecheck, the changelog check, media-guard, and `pip-audit`). Don't open a PR unless asked.
- **Deliberate divergences from the generic SOP** (do *not* "fix" these to match it): (1) we use **lowercase conventional-commit prefixes**, not the SOP's "Capitalize the subject" / no-prefix style; (2) no hard 50-char subject cap; (3) the agent git proxy is **fast-forward-only** — **no force-push, no branch delete, no tag push**; releases go via the `release.yml` `workflow_dispatch`, not `git push origin vX.Y.Z`; (4) personal `username/…` branches don't apply — the session branch is assigned.

### Run commands

- **Quickstart from a fresh clone:** `bash dev-setup.sh` then `source .venv/bin/activate && platterpus`
- **Manual:** `python3 -m venv .venv && source .venv/bin/activate && pip install --upgrade pip && pip install -e . && platterpus`
- **From the AppImage (once published):** `./platterpus-x86_64.AppImage`
- **From a `pipx` install (once published):** `platterpus`
- **CLI flags on the AppImage:** there is **no `platterpus` on `PATH`** for AppImage users (only `pipx`/dev installs put one there). The AppImage entrypoint (`build/python-appimage/entrypoint.sh`) ends with `exec python -m platterpus "$@"`, so every flag below works by passing it to the AppImage directly, e.g. `./platterpus-x86_64.AppImage --doctor` or `./platterpus-x86_64.AppImage --ctdb-calibrate "<album folder>"`. (User-facing version in README → *Command-line usage*.)
- **Version check without launching the GUI:** `platterpus --version` (or `./platterpus-x86_64.AppImage --version`)
- **Preflight / "doctor" (first-pass environment test, no CD needed):** `platterpus --doctor` (no extra flags — it just runs the full check and exits). For the tunable form use `python scripts/preflight.py`, which adds `--no-network` (skip the MB/CAA/CTDB reachability checks). It exits non-zero on a hard blocker. Logic lives in `src/platterpus/preflight.py` (reuses the real adapters + the dependency subsystem); `--doctor` and the script are thin CLIs over it. (cyanrip is the sole backend — KDD-18 — so there is no backend-override flag.)

### Test commands

- `pytest` from repo root (no env vars needed — `pyproject.toml` sets `pythonpath = ["src"]`)
- **What CI enforces:** branch coverage + a hard floor — `pytest --cov=platterpus --cov-report=term-missing --cov-fail-under=91` on a **Python 3.11–3.14 matrix**. The gate **ratchets up, never down**.
- Property-based tests (parsers never crash on any input): `pytest tests/test_parsers_property.py` (needs `hypothesis`, in the `dev` extra).
- Mutation testing (test-quality audit) runs **weekly in CI** (`.github/workflows/mutation.yml` — non-blocking, never gates a merge) over `src/platterpus/parsers/`, `src/platterpus/verdict.py`, and `src/platterpus/ctdb/crc.py`. Run locally with `pipx run mutmut run --paths-to-mutate "src/platterpus/parsers/,src/platterpus/verdict.py,src/platterpus/ctdb/crc.py"`.
- **Testing strategy + the rules every change is held to live in [`docs/testing.md`](docs/testing.md)** (the trophy + hardware gate, the five-tier case taxonomy, and the Definition of Done). **Institutional rule: every shipped bug gets a regression test in the same PR as the fix; every new parser of external output gets a property-based "never raises" test.**

### Uninstall

- `bash uninstall.sh` (interactive; removes `.venv/`, GUI config, GUI logs; prompts for Picard / Distrobox / whipper.conf / host exports)
- `bash uninstall.sh --full --yes` (removes everything except music files and the cloned repo)
- `bash uninstall.sh --dry-run` (shows what would be removed)
- `bash uninstall.sh --help`

### Lint / format commands

- **Lint:** `ruff check src tests` (config in `pyproject.toml` `[tool.ruff]`; rules `E,F,W,I,B,UP`, `E501` off). Auto-fix: `ruff check src tests --fix`.
- **Format:** `ruff format src tests` (88-col, double quotes — matches the existing code). CI checks with `ruff format --check`.
- **Type-check:** `mypy` (bare invocation; config in `pyproject.toml` `[tool.mypy]`, strict def-typing across the whole package). CI runs it as the gating `typecheck` job.
- **CI:** the `lint` job in `.github/workflows/ci.yml` runs both ruff commands in check mode on every push/PR, in parallel with `test` and `typecheck`.
- `ruff` and `mypy` are in the `dev` extra (`pip install -e ".[dev]"`).

### Enforced safety (.claude/ + git hook)

Beyond the *guidance* in the Critical rules above, a few things are **enforced** (not just trusted):

- **`.githooks/pre-commit`** — blocks any commit that stages an audio/copyrighted-media file (Critical rule #8), even via `git add -f`. The hard guarantee behind the rule + the `.gitignore` backstop. Activate per clone with `git config core.hooksPath .githooks` (**`dev-setup.sh` does this**); bypass for a verified CC0/self-generated sample with `git commit --no-verify`.
- **`.claude/settings.json`** (committed, shared) — permission `deny` for destructive commands (`rm -rf`, `git push --force`/`-f`/`--force-with-lease`) and secret reads (`.env*`, `secrets/**`), plus a `PreToolUse` hook that blocks a Bash call while audio is staged (the Claude-session belt for the same rule; git hook is the canonical guard). Deliberately does **not** prompt on normal `git push`, to preserve the merge-and-keep-going workflow. Personal overrides go in `.claude/settings.local.json` (git-ignored). Run `/memory` or `/hooks` to confirm what loaded.

### Important paths

- Source root: `src/platterpus/`
- User config: `~/.config/platterpus/config.toml`
- User logs: `~/.local/share/platterpus/log.txt`
- Ripper binary (host-exported from Distrobox): `~/.local/bin/cyanrip`
- Legacy `whipper.conf` (read-only, offset reference only): `~/.config/whipper/whipper.conf` — cyanrip does not use it; the read offset lives in the GUI's own config
- MusicBrainz Picard (Flatpak, used for auto-launch on unknown discs): `flatpak run org.musicbrainz.Picard`

### Getting help (Claude Code / Anthropic)

For problems with the **AI tooling itself** — Claude Code, the Claude model, or the Anthropic API. (This is *not* Platterpus end-user support; app questions route to the project maintainer, not Anthropic.)

- **Fastest:** the support messenger at [support.anthropic.com](https://support.anthropic.com/en/) — message icon, bottom-right. Or, when signed in, **[Claude.ai](https://claude.ai)** / **[Console](https://console.anthropic.com)** → your initials → **"Get help."** (Signed-in routes faster — they see the account.)
- **API / developer issues:** [support.claude.com](https://support.claude.com).
- **Topic-specific email:** safety / harmful content → `usersafety@anthropic.com`; security vulnerability → `security@anthropic.com`; privacy / data request → `privacy@anthropic.com`.
- **Claude via Amazon Bedrock or Google Vertex:** contact AWS / Google support, not Anthropic directly.
- Reference: [How can I contact Support?](https://support.anthropic.com/en/articles/9015913-how-can-i-contact-support)

### Session history

Chronological session notes — what was built, decided, and learned each session — live in **[`docs/session-log.md`](docs/session-log.md)** (newest first). They're kept out of this file so the always-loaded project context stays lean and scannable.

**Graduation rule:** a durable lesson from the log belongs in its real home — *Code conventions* / *Critical rules* above, a KDD in `PLANNING.md`, or `docs/architecture.md` / `docs/testing.md` — not left only in the dated log. The log is append-only chronology; the rules are the distillation.

---

*Last updated for Platterpus v0.4.24.*
