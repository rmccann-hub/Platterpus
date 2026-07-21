# Platterpus — Claude Code Session Start

> **Historical bootstrap record (note added 2026-07-21).** This document is the
> instruction set the *original* bootstrap session followed, preserved as the
> rebuild-from-scratch anchor (`docs/README.md`). It predates the
> whipper → cyanrip switch: whipper was removed 2026-06-30 (KDD-18) and
> cyanrip is the sole backend, so a verbatim re-run today would contradict the
> current CLAUDE.md it is told to read — treat the whipper framing (and
> Step 0's whipper-centred research questions) as the historical starting
> point, with `PLANNING.md`'s KDDs as the record of everything that changed
> since.

I am starting a fresh Claude Code session to build a Linux GUI front-end for the `whipper` audio-CD ripping CLI. This file is your instruction document. Follow the numbered steps below in order. Do not skip ahead.

---

## Attached files

You should have three other files attached to this session (the fourth item below is this file itself):

1. **`platterpus-research-brief-v2.1.md`** — the project brief. Authoritative for *what* to build (requirements, features, constraints, scope).
2. **`compass_artifact_*.md`** — the Research-mode validation output. Authoritative for *which tools* to use and *why* (frameworks, distribution, dependencies). The filename will look like `compass_artifact_wf-<hash>_text_markdown.md`.
3. **`CLAUDE.md`** — the persistent project context file. You will copy this verbatim to the project root in Step 3. Do not edit the rules section.
4. *(This file)* — `platterpus-session-start.md` — the bootstrap instructions you are reading now.

Where the brief and the research output conflict, the brief wins — its v2.1 changelog post-dates the research.

If any of those files is missing, stop and ask me to attach it before continuing — except the `compass_artifact_*.md` research file, whose absence Step 0 exists to handle (proceed against the brief alone).

---

## Step 0 (optional) — refresh the tool-choice research

**Skip this if you already have a `compass_artifact_*.md`** — use it directly and
go to Step 1. Do this leg only when the original Research artifact is unavailable,
or when more than ~6 months have elapsed and you want a fresh validation pass
against brief v2.1 (which the original v1 research never saw).

How to run it:

1. Open a **fresh Claude conversation** (a new chat — NOT inside a project), set
   to a current Claude Opus model, and **enable Research mode**.
2. Attach **`platterpus-research-brief-v2.1.md`** to the first message.
3. Paste the message body below verbatim and send (Research takes 15–45 min).
4. Save the resulting artifact keeping the **`compass_artifact_`** filename prefix
   (this file looks for that pattern), then continue to Step 1 with it attached.

```
The attached file (`platterpus-research-brief-v2.1.md`) is a research brief for a Linux GUI project. It is version 2.1 of a brief that was previously validated in v1. The original v1 research output is unavailable, so I need a fresh validation pass against the current v2.1 spec.

Please read the brief in full, including:
- The revision history at the top (v1 → v2 → v2.1)
- The full body (sections 1–3)
- The Required Output Format (section 4)
- Appendix A (the proposed architecture, features, constraints, scope)
- Appendices B and C

Then produce the full A–K research output as specified in section 4 of the brief.

## Where to spend extra effort

These items were added or sharpened in v2 / v2.1 and have not previously been validated. Treat them as the highest-value parts of the research:

1. **Dependency self-management subsystem (P0 #11).** Is the three-tier (a) auto-install / (b) queued-install / (c) copyable-search-string approach sound? Are there established patterns from other Linux GUI apps (GNOME Software, KDE Discover, Flatpak-based installers, pipx wrappers) that should inform this design? Surface any prior art and any failure modes the design should anticipate.

2. **Unmaintained-dependency adapter pattern (Constraints section).** Specifically for `whipper`, `python-musicbrainzngs`, and `appimage-builder`. Confirm or refute the maintenance status of each as of the date of your research. Is the adapter wrapper the right mitigation? Are there better patterns (e.g., vendoring, forking, replacing outright)? For each, what is the strongest active alternative right now and how mature is it?

3. **`python-appimage` as the preferred AppImage builder.** Confirm or refute the v2.1 framing that `python-appimage` is actively maintained with weekly automated rebuilds, and that `appimage-builder` should be fallback-only. Has anything in the AppImage tooling ecosystem changed since early 2026 that would shift this preference? Are there newer alternatives (e.g., something that's emerged in late 2025 / 2026) worth knowing about?

4. **FLAC-first, MP3/WAV-as-P1 ordering (P1 backlog).** Validate that this priority is right for an EAC-equivalent archival workflow on Linux. Are there encoder backend choices for MP3/WAV that should be locked in now (e.g., `lame` versus alternatives) so the P0 dependency subsystem can be designed to accommodate them later?

## Where to be efficient

These items were covered in v1 research. Provide updated coverage, but you may be more concise if the landscape has not materially changed:

- Framework comparison (section 3.1)
- Distribution method comparison (section 3.2) — except for the AppImage-builder question above
- Interactive subprocess handling (section 3.3)
- Reference implementations (section 3.4)
- Drive access on Bazzite / Distrobox / Flatpak (section 3.5)
- Linux-vs-EAC quality gap (section 3.6)
- Standard risks (section 3.7) — except for the unmaintained-deps question above

For any of these, if the landscape HAS changed since mid-2025 / early-2026, flag the change explicitly and update your recommendation. If nothing material has changed, a shorter recap is fine.

## Output discipline

- Cite all sources. Where evidence is weak or contested, say so.
- Where you disagree with the proposed architecture in Appendix A, push back with cited counter-evidence.
- Keep the Executive Summary (section A of the output) to ≤ 250 words as the brief specifies.
- Restate the final framework / distribution / prompt-handling combo in section J.
- End with section K (Open Questions) — short and pointed.
```

---

## Steps — execute in order

### Step 1 — Read all attached files end to end

Read in this order:

1. `platterpus-research-brief-v2.1.md` (the brief — requirements)
2. `compass_artifact_*.md` (the research — tool justifications)
3. `CLAUDE.md` (the rules you will live by for the project)

Read all three completely. Do not skim. Do not begin Step 2 until you have read all three.

### Step 2 — Confirm understanding

Give me a 5–10 bullet summary of what you understand the project to be. Cover at minimum:

- The stack (language, GUI framework, distribution method)
- The non-obvious requirements: the dependency self-management subsystem with its (a) auto-install / (b) queued-install / (c) copyable-search-string tiers; the unmaintained-dependency adapter pattern (`RipBackend`, `MusicBrainzClient`); the Distrobox-exported `whipper` binary at `~/.local/bin/whipper`
- Anything ambiguous or anything where the brief and the research output disagree

Stop and wait for my response before Step 3.

### Step 3 — Produce the project bootstrap files

Create a project directory (suggested name: `platterpus/`). Inside it, produce the five files in the table below. **This is not a single PLAN.md — it's the project's persistent file structure.** Each file has a distinct role and lifetime:

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

- **Directory tree** of every file you intend to create under `src/platterpus/`
- **Per-module responsibility** — one paragraph per module, no more. Explicitly name the modules that house: the dependency self-management subsystem, the `RipBackend` adapter, the `MusicBrainzClient` adapter, the rip log parser, the GUI main window, and the AppImage build harness
- **Pinned dependency list** with justifications and last upstream release date for each (this also feeds `DEPENDENCIES.md`)
- **Dependency self-management subsystem (brief P0 #11)** — dedicated section showing how the (a) auto-install / (b) queued-install / (c) copyable-search-string tiers are implemented as a single subsystem. Diagram the decision tree
- **`RipBackend` adapter design** — interface, expected methods, how `cyanrip` would slot in later as an alternative implementation
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
| whipper | 0.10.0 | 2021-05-17 | GPL-2.0+ | Unmaintained (>12mo) | cyanrip via RipBackend adapter |
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

**Why this file set, and not just `PLAN.md`.** A single PLAN.md works for a one-session project, but Platterpus will span many sessions. Without `CLAUDE.md`, every new session has to re-derive the rules from the brief, and the rules drift. Without `TASKS.md`, "what's next" lives in chat history and gets lost. Without `DEPENDENCIES.md`, the unmaintained-deps discipline collapses the first time someone forgets the cadence. The five-file structure is the minimum that survives session boundaries cleanly.

**Why `CLAUDE.md` is pre-built and locked.** If Claude Code generates `CLAUDE.md` from scratch, it will subtly vary between project re-creations and between users using the same template. Locking the rules section to a known-good copy is the only reliable way to keep behavior consistent.

**Why plan-first inside Claude Code.** The brief originally specified a separate plan-writing session between Research and Claude Code. Folding plan-writing into Claude Code is fine, but only if Claude Code is forced to produce and surface the planning artifacts as discrete files and pause for approval before building. The Steps above enforce that. If Claude Code starts coding before showing the five files, interrupt and re-anchor to Step 4.

---

*Last updated for Platterpus v0.4.24.*
