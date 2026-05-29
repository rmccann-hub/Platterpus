# Whipper GUI — Claude Code Session Start

I am starting a fresh Claude Code session to build a Linux GUI front-end for the `whipper` audio-CD ripping CLI. This file is your instruction document. Follow the numbered steps below in order. Do not skip ahead.

---

## Attached files

You should have four other files attached to this session:

1. **`whipper-gui-research-brief-v2.1.md`** — the project brief. Authoritative for *what* to build (requirements, features, constraints, scope).
2. **`compass_artifact_*.md`** — the Research-mode validation output. Authoritative for *which tools* to use and *why* (frameworks, distribution, dependencies). The filename will look like `compass_artifact_wf-<hash>_text_markdown.md`.
3. **`CLAUDE.md`** — the persistent project context file. You will copy this verbatim to the project root in Step 3. Do not edit the rules section.
4. *(This file)* — `whipper-gui-session-start.md` — the bootstrap instructions you are reading now.

Where the brief and the research output conflict, the brief wins — its v2.1 changelog post-dates the research.

If any of those files is missing, stop and ask me to attach it before continuing.

---

## Steps — execute in order

### Step 1 — Read all attached files end to end

Read in this order:

1. `whipper-gui-research-brief-v2.1.md` (the brief — requirements)
2. `compass_artifact_*.md` (the research — tool justifications)
3. `CLAUDE.md` (the rules you will live by for the project)

Read all three completely. Do not skim. Do not begin Step 2 until you have read all three.

### Step 2 — Confirm understanding

Give me a 5–10 bullet summary of what you understand the project to be. Cover at minimum:

- The stack (language, GUI framework, distribution method)
- The non-obvious requirements: the dependency self-management subsystem with its (a) auto-install / (b) queued-install / (c) copyable-search-string tiers; the unmaintained-dependency adapter pattern (`WhipperBackend`, `MusicBrainzClient`); the Distrobox-exported `whipper` binary at `~/.local/bin/whipper`
- Anything ambiguous or anything where the brief and the research output disagree

Stop and wait for my response before Step 3.

### Step 3 — Produce the project bootstrap files

Create a project directory (suggested name: `whipper-gui/`). Inside it, produce the five files in the table below. **This is not a single PLAN.md — it's the project's persistent file structure.** Each file has a distinct role and lifetime:

| File | Role | Mutability | How to produce |
|---|---|---|---|
| `CLAUDE.md` | Persistent context, loaded on every future session | Rules locked; ops section grows | Copy from the attached `CLAUDE.md` **verbatim** |
| `PLANNING.md` | Architecture and design decisions | Living | Write from scratch per spec below |
| `TASKS.md` | Active task checklist | Updated as work progresses | Write from scratch per spec below |
| `DEPENDENCIES.md` | Dep table with release dates and replacement plans | Updated on every dep change | Write from scratch per spec below |
| `README.md` | Outward-facing description | Updated infrequently | Write from scratch per spec below |

Write them in the order shown below. Detailed specs for each follow.

#### 3a — `CLAUDE.md` (copy verbatim)

I have provided `CLAUDE.md` as one of the attachments. Copy it to the project root **without changes** to the rules section above the horizontal rule. You may add concrete entries to the "Project operations" section at the bottom (build commands, paths, etc.) once those exist — but do this after `PLANNING.md` is written, so the additions reflect actual decisions.

If you find yourself wanting to modify the rules section, stop and tell me what's wrong; don't edit silently.

#### 3b — `PLANNING.md` (architecture and design)

The primary planning artifact. Include:

- **Directory tree** of every file you intend to create under `src/whipper_gui/`
- **Per-module responsibility** — one paragraph per module, no more. Explicitly name the modules that house: the dependency self-management subsystem, the `WhipperBackend` adapter, the `MusicBrainzClient` adapter, the rip log parser, the GUI main window, and the AppImage build harness
- **Pinned dependency list** with justifications and last upstream release date for each (this also feeds `DEPENDENCIES.md`)
- **Dependency self-management subsystem (brief P0 #11)** — dedicated section showing how the (a) auto-install / (b) queued-install / (c) copyable-search-string tiers are implemented as a single subsystem. Diagram the decision tree
- **`WhipperBackend` adapter design** — interface, expected methods, how `cyanrip` would slot in later as an alternative implementation
- **`MusicBrainzClient` adapter design** — interface, how a fallback to direct `requests` against MB's JSON API would replace `python-musicbrainzngs`
- **Distribution strategy** — `python-appimage` as the build path, build script outline, where the AppImage spec lives in the repo. Do not plan for `appimage-builder` (see CLAUDE.md deviation policy)
- **Key design decisions and rationale** — anything non-obvious you chose. One paragraph each. The reader is future-you returning to the project after months away

#### 3c — `TASKS.md` (active checklist)

The numbered task list, expressed as a checklist. Each task:

```
- [ ] T01 — Short title
      Acceptance: one or two lines describing what "done" looks like
      Phase: P0
```

Status conventions:
- `[ ]` not started
- `[~]` in progress
- `[x]` complete
- `[?]` blocked (add a one-line note about what's blocking)

Section structure:

1. **P0 (v1 release)** — execute these in order
2. **P1 (backlog)** — separate section, clearly fenced off, not interleaved with P0

Keep `TASKS.md` as the single source of truth for what's next. Update it as work progresses — when a task starts, when it completes, when something blocks.

#### 3d — `DEPENDENCIES.md` (dependency table)

Use this exact structure:

```markdown
# Dependencies

| Name | Pinned version | Last upstream release | License | Status | Planned replacement |
|---|---|---|---|---|---|
| whipper | 0.10.0 | 2021-05-17 | GPL-2.0+ | Unmaintained (>12mo) | cyanrip via WhipperBackend adapter |
| python-musicbrainzngs | (pin) | 2020-01-11 | BSD-2-Clause | Unmaintained (>12mo) | direct requests via MusicBrainzClient adapter |
| PySide6 | (pin) | (lookup) | LGPL-3.0 | Active | — |
| python-appimage | (pin) | (lookup) | MIT | Active | appimage-builder if forced (see CLAUDE.md deviation policy) |
| (others) | | | | | |

## Review cadence

- Before every tagged release
- After every meaningful dependency bump
- At least quarterly even when nothing changes (so retirement signals don't pile up unseen)

## Retirement trigger

Any row whose "Last upstream release" exceeds 12 months requires a review of:
1. The adapter wrapping that dependency (does it still isolate the GUI from the dep?)
2. The "Planned replacement" column (is it still the right replacement?)
3. Whether to act on the retirement now or wait
```

Fill in every row with actual data. Look up versions and license info as needed. Don't leave `(lookup)` placeholders in the final file — those are mine, not yours.

#### 3e — `README.md` (outward-facing description)

Standard project README. Include:

- Project name and one-paragraph description (lift from the brief's §1, condensed)
- System requirements (primary: Bazzite Linux KDE Plasma 6; secondary: Fedora / Arch / Ubuntu and other modern Linux)
- Install instructions — placeholder until the AppImage exists; mention `pipx` as the secondary channel
- How to run — placeholder until the entry point exists
- Pointers to `PLANNING.md` and `DEPENDENCIES.md` for contributors
- License (use whatever the brief implies; if unspecified, leave as TBD and flag in your summary)

### Step 4 — Stop and wait for approval

After writing all five files, show me each one in turn and stop. Do not start coding. I will review, ask questions, and either approve the set or request revisions. The set must be coherent — `CLAUDE.md` rules, `PLANNING.md` architecture, and `TASKS.md` checklist should all reference the same module names and design choices.

### Step 5 — Build per the plan

Once I approve the bootstrap files, execute `TASKS.md` in order. Update task status (`[ ]` → `[~]` → `[x]`) as you work. If you need to deviate from `PLANNING.md`, stop and ask — see the deviation policy in `CLAUDE.md` for what counts.

For the first few files you write, show me each one before committing it to disk so I can spot the pattern. Once I confirm the pattern looks right, you can batch the rest.

As decisions are made and operational details emerge, fill in `CLAUDE.md`'s "Project operations" section (build commands, run commands, test commands, paths).

---

## Start

Begin Step 1.

---

## Footnote — background for the human, not for Claude Code

*This section exists so the workflow rationale isn't lost if I revisit this project later. Claude Code can ignore it.*

**Why this file set, and not just `PLAN.md`.** A single PLAN.md works for a one-session project, but Whipper GUI will span many sessions. Without `CLAUDE.md`, every new session has to re-derive the rules from the brief, and the rules drift. Without `TASKS.md`, "what's next" lives in chat history and gets lost. Without `DEPENDENCIES.md`, the unmaintained-deps discipline collapses the first time someone forgets the cadence. The five-file structure is the minimum that survives session boundaries cleanly.

**Why `CLAUDE.md` is pre-built and locked.** If Claude Code generates `CLAUDE.md` from scratch, it will subtly vary between project re-creations and between users using the same template. Locking the rules section to a known-good copy is the only reliable way to keep behavior consistent.

**Why plan-first inside Claude Code.** The brief originally specified a separate plan-writing session between Research and Claude Code. Folding plan-writing into Claude Code is fine, but only if Claude Code is forced to produce and surface the planning artifacts as discrete files and pause for approval before building. The Steps above enforce that. If Claude Code starts coding before showing the five files, interrupt and re-anchor to Step 4.
