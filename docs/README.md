# Documentation

This directory contains the canonical source material the project was built from, plus reference documents the rest of the codebase points to.

## Single source of truth — where each kind of content lives

To keep the docs efficient and stop the same rule from sprawling across files (and going stale in some), every kind of content has **one canonical home**. State it there; everywhere else, *link* — don't re-explain.

| Content | Canonical home |
|---|---|
| Locked coding conventions & critical rules | `CLAUDE.md` → *Code conventions* / *Critical rules* |
| How the maintainer works / project values | `CLAUDE.md` → *Working with the maintainer* |
| CI / release & build operations | `CLAUDE.md` → *Project operations* |
| Commit & PR conventions (this repo) | `CLAUDE.md` → *Project operations → Commit & PR hygiene* (general mechanics: `docs/github-workflow-sop.md`) |
| Architectural decisions + rationale (KDD-NN) | `PLANNING.md` |
| Module map & per-module responsibility | `PLANNING.md` |
| Layered design, patterns, engineering lessons, extension recipes, packaging/release/security | `docs/architecture.md` |
| Testing strategy, taxonomy, institutional rules | `docs/testing.md` |
| Manual & release testing (acceptance run + gated cases + tester matrices) | `docs/test-plan.md` |
| Dependency pins, dates, licenses, retirement log | `DEPENDENCIES.md` |
| User-facing changes | `CHANGELOG.md` |
| Active task queue | `TASKS.md` |
| What happened each session (chronology) | `docs/session-log.md` |
| Install / usage docs | `README.md` |

A lesson legitimately appears in **two** places: a one-line *rule* in its canonical home, and a dated *entry* in `docs/session-log.md` recording how it arose (the **graduation rule** — distillation up, chronology down). Anything beyond that is duplication to delete.

### Doc version stamps

Every Markdown doc ends with a **`*Last updated for Platterpus vX.Y.Z.*`** footer — the release the doc's content was last revised for — so a reader can gauge its currency at a glance. This is part of *documentation currency* (CLAUDE.md Critical rule #7): **when you meaningfully change a doc, bump its stamp to the current `__version__`.** The stamps were seeded (2026-07-07) from git history — the `__version__` in effect at each file's last content commit — so an old stamp means the doc simply hasn't needed a change since, not that it's unmaintained.

## Source documents (anchor for "rebuild from scratch")

These two files, together with the top-level `CLAUDE.md`, `PLANNING.md`, `TASKS.md`, `DEPENDENCIES.md`, and `README.md`, are the full context needed to reproduce the project from a clean slate.

| File | What it is | Authority on |
|---|---|---|
| [`platterpus-research-brief-v2.1.md`](platterpus-research-brief-v2.1.md) | The original requirements brief — every P0/P1 feature, every constraint, every scope decision started here. | **Requirements and scope.** When PLANNING.md and the brief conflict, the brief wins on requirements; PLANNING wins on implementation. |
| [`platterpus-session-start.md`](platterpus-session-start.md) | The bootstrap instructions a fresh Claude Code session followed to produce the initial five top-level files — and (Step 0, optional) the paste-verbatim Research-mode prompt for refreshing the tool-choice validation against the brief. | **Initial repo state + the bootstrap procedure, and how to refresh the tool-choice research.** Re-run it against a clean repo to re-derive the planning artifacts. |

> **About the `compass_artifact_*.md` Research validation file:** the original v1 brief produced a compass-artifact research validation in a Claude Research session; the user could not locate it when this project was bootstrapped, so the project proceeded against the brief alone (see CLAUDE.md "Companion documents"). If the session-start Step 0 rerun prompt is ever invoked, save the resulting `compass_artifact_*.md` into this directory.

## Reference documents

| File | What it is |
|---|---|
| [`architecture.md`](architecture.md) | **Architecture & contributor guide** — the layered design and dependency direction; the core patterns *with the why and the hard-won lessons* (adapter layer, the never-block-the-GUI-thread discipline + worker mechanics, subprocess rules, never-raise parsers, the dependency subsystem, the MainWindow mixin decomposition, error/logging); step-by-step **extension recipes**; the testing contract; packaging/building/releasing; security & licensing hygiene; and the architectural future-directions horizon. **Start here to extend the program.** (Absorbed the former `best-practices.md`.) |
| [`testing.md`](testing.md) | **Testing strategy & standards** — the trophy + a real-hardware gate, the five-tier case taxonomy (easy/medium/hard/edge/unexpected), when to use property-based / golden / fault-injection / mutation testing, the institutional rules (every bug gets a regression test; parsers never raise; coverage gate ratchets up), and a Definition of Done. Portable to sibling projects. |
| [`test-plan.md`](test-plan.md) | **Manual & release testing** — the end-to-end clean-cycle acceptance run (uninstall → fresh install → drive setup → rip → verify), the **EAC output-parity** check (with the per-track CRC baseline), the **Linux-distro** + **problem-permutation** matrices for onboarding testers, *and* the deep single-feature gated cases (CTDB verify CRC, `drive analyze`/`offset find` strings, GUI screenshot, Picard UX, PyPI go-live, the cyanrip parity run). Run one at a time and record results. (Absorbed the former `release-testing.md`.) |
| [`appimage-testing.md`](appimage-testing.md) | How the AppImage is built (on every push to `main`, on demand for any branch, and at release) and how to test it in each case — including branches with no published release yet. |
| [`log-format-comparison.md`](log-format-comparison.md) | Side-by-side comparison of cyanrip's rip log against EAC's, anchoring [PLANNING.md KDD-11](../PLANNING.md). The hand-authored EAC log at `tests/fixtures/rip_log_eac_reference.log` is the comparison's data. |
| [`dependency-contracts.md`](dependency-contracts.md) | **Dependency contracts** — the single reference for the exact arguments/flags/syntax Platterpus passes each external tool (cyanrip, flac, metaflac, ffmpeg, musicbrainzngs, CAA, CTDB, drive/reader control) and the output shape it parses back. The code-side counterpart to the "validate every input and every dependency output" rule; keep it in step with the adapters. |
| [`session-log.md`](session-log.md) | **Chronological session history** — what each Claude Code session built, decided, and learned (newest first). The project's institutional memory; durable lessons graduate from here into the docs above. |
| [`ripper-engine-strategy.md`](ripper-engine-strategy.md) | **Research / options (living, long-horizon):** the feasibility of forking and/or combining whipper + cyanrip and maintaining our own engine — licensing analysis, the option menu, and decision gates. Revisits KDD-18's "never fork" stance; a commitment requires a new KDD. §10 is the per-gap, license-compatible open-source option menu. |
| [`upstream-pr-roadmap.md`](upstream-pr-roadmap.md) | **Contributor instructions (2026-07-07):** the *ordered* upstream pull requests that would close our remaining ripper-engine gaps, with per-PR feasibility, effort, acceptance odds, and step-by-step how-to — turning `ripper-engine-strategy.md` §10 into a ranked action list. Answers "do I need to be a collaborator?" (no — fork + PR) and marks the honest DO-NOW (cdrdao integration, no upstream PR) vs the skip-for-now items. PR-first; signed EAC checksum permanently out of scope. |
| [`ctdb-crc-algorithm.md`](ctdb-crc-algorithm.md) | **Reference (2026-07-07):** the bit-exact CueTools DB per-disc CRC algorithm reconstructed from the CueTools LGPL source — it *is* a plain `zlib.crc32` over a fixed-front/length-dependent-back trim, with the **±5879**-frame offset sweep (CTDB's range, wider than AccurateRip's ±2939) and the `crc32_combine` fast path. The spec behind `src/platterpus/ctdb/crc.py` + `calibrate.py`; anchors KDD-16. |
| [`github-workflow-sop.md`](github-workflow-sop.md) | **Contributor/upstream-PR reference (filed 2026-07-07):** general GitHub ecosystem SOP — identity/SSH, cloning vs forking, GitHub Flow + branch naming, atomic commits + the 7 commit-message rules, PR anatomy, merge strategies + branch protection, conflict resolution. A preface reconciles it with *this* repo's policy (CLI + GitHub MCP not Desktop, fast-forward-only proxy, `claude/…` branch, squash-merge); `CLAUDE.md` wins where they differ. Most useful as the playbook for contributing *upstream* (see `upstream-pr-roadmap.md`). |
| [`eac-parity-investigation.md`](eac-parity-investigation.md) | **Research + plan (2026-06-27):** can our output be bit-identical to EAC? Marks every deviation axis EAC↔our cyanrip rip, with feasibility. Key finding: bit-identical *audio* (AccurateRip-CRC) is the achievable, meaningful goal (12/14 already met); bit-identical *files* are impossible across FLAC encoders and unnecessary. Plan for the Track-3 near-miss and the `INDEX 00` pre-gap question. |
| [`ux-design-principles.md`](ux-design-principles.md) | **Living UX guidance (2026-06-28):** the trust-first design principles distilled from deep-research on why EAC made bit-perfect ripping usable — verification as a first-class UI object, safe-by-default, progressive disclosure, localized failure, two-logs/tamper-evident, per-drive profiles, accessibility — plus a gap analysis vs Platterpus and the ranked UX backlog. The *why* behind the UX; the bar new rip features are held to. |
| [`eac-log-and-repair-feasibility.md`](eac-log-and-repair-feasibility.md) | **Research / decision-gated (2026-06-28):** the two questions the EAC-parity investigation deferred — (A) can we make rips *tracker-accepted* by emitting an EAC log? (technically yes via the reverse-engineered checksum, but it's **forgery** of EAC provenance → hard no; trust the open AccurateRip/CTDB path instead), and (B) in-app CUETools/CTDB **repair** (feasible on Linux via `ctdb-cli`/.NET or CUETools/Mono, but a heavy dependency that rewrites the master — **blocked on CRC hardware-validation**; ship `-Z N` now, gate repair behind sign-off). Maintainer decision pending. |
| [`mp3-wav-support.md`](mp3-wav-support.md) | **Design-of-record for multi-format output (SHIPPED 2026-06-26, KDD-22):** the FLAC-master + WavPack/MP3/WAV-derived model, per-format parity semantics, the verified encoder args (FLAC `-8 -e -p`, MP3 VBR `-V0`, WavPack lossless), the transcode-always decision, and the one open item (embedding cover art inside `.wv`). Flipped Critical Rule #4 (FLAC is now the default/master, not the only format). |
| [`archive/`](archive/README.md) | Retired point-in-time investigations (ecosystem audit, read-offset, upstream-modification/CTDB spec) **plus external reference material** (the EAC archival master guide). Their durable conclusions have graduated into KDDs / DEPENDENCIES / adapter comments — see `archive/README.md` for the map. |

## Where the rest of the project context lives

Outside this directory:

| File | What it covers |
|---|---|
| [`../CLAUDE.md`](../CLAUDE.md) | Persistent rules and conventions; locked rules section; project operations |
| [`../PLANNING.md`](../PLANNING.md) | Architecture, directory tree, per-module responsibilities, adapter designs, dependency-manager design, keyed design decisions (KDD-01 … KDD-25) |
| [`../TASKS.md`](../TASKS.md) | Active task checklist — P0 (T01-T32), P1.1 (install/uninstall ease), P1 (broader backlog), P2 (future), Out of scope |
| [`../DEPENDENCIES.md`](../DEPENDENCIES.md) | Pinned versions, last upstream release dates, retirement-review log |
| [`../README.md`](../README.md) | User-facing install instructions, troubleshooting, EAC comparison |
| [`../build/python-appimage/README.md`](../build/python-appimage/README.md) | AppImage build recipe details |

## Rebuild-from-scratch checklist

If you needed to start over with a fresh git repository:

1. **Place these files at repo root:**
   - `CLAUDE.md` (copy verbatim from the user's CLAUDE.md template — the rules section is locked)
   - `PLANNING.md`, `TASKS.md`, `DEPENDENCIES.md`, `README.md` (produced by Claude Code Step 3 per `platterpus-session-start.md`)
2. **Place these files in `docs/`:**
   - `platterpus-research-brief-v2.1.md`
   - `platterpus-session-start.md`
3. **(Optional but recommended after 6+ months) Re-run Research validation:** follow `platterpus-session-start.md` **Step 0**, save the result as `docs/compass_artifact_<hash>_text_markdown.md`.
4. **Boot a fresh Claude Code session,** attach the brief + session-start + (if present) compass artifact + CLAUDE.md, and ask it to execute `platterpus-session-start.md`. The session reproduces PLANNING.md, TASKS.md, DEPENDENCIES.md, README.md from scratch and then begins executing the task list.
5. **Subsequent sessions** follow CLAUDE.md as the primary instruction document, using TASKS.md to track what's next.

---

*Last updated for Platterpus v0.4.19.*
