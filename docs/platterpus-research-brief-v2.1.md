# Research Brief: Linux GUI Front-End for `whipper` CLI

> **Preservation note (added 2026-07-21 — the body below is unedited).** This
> brief is preserved **verbatim** as the original requirements record; it is
> canonical for scope *as amended by the maintainer-approved KDDs in
> `PLANNING.md`*. The largest amendments since it was written:
> **whipper → cyanrip as the sole backend** (KDD-18, 2026-06-30 — the
> Distrobox host-export routing constraint stands unchanged, the binary is
> `~/.local/bin/cyanrip`, and `whipper.conf` is a read-only legacy reference);
> **CTDB verification moved in-scope and shipped** (KDD-12/KDD-16,
> hardware-validated v0.4.20); **MP3/WavPack/WAV shipped** via the single
> ffmpeg transcode adapter, not lame/sox (KDD-22, 2026-06-26); and the
> AccurateRip-submission exclusion is policy-blocked, not a technical Linux
> gap (KDD-12). Where the body below disagrees with those KDDs, the KDD is
> the operative record.


> **For:** Claude Opus 4.7 Adaptive with **Research mode enabled**
> **Output goal:** A complete, evidence-backed comparison of architectural options for building a Linux GUI wrapper around the `whipper` audio-CD ripping CLI, so I can make an informed final-plan document for Claude Code.
>
> **Brief revision history**
> - **v2.1 (current):** Tightened the AppImage builder choice in Appendix A. `python-appimage` is now explicitly preferred (actively maintained, weekly automated rebuilds through 2025). `appimage-builder` is permitted only as a fallback if `python-appimage` cannot express a required build step, and any such recipe must avoid `appimage-builder`-specific features so a future swap back to `python-appimage` (or a successor) is cheap. This brings line 218 into alignment with the unmaintained-dependency constraint already stated in §Constraints.
> - **v2:** Added P0 #11 *dependency self-management* with the three-tier auto-install → queue → copyable-error fallback; moved MP3/WAV from "out of scope" to P1 with FLAC explicitly named the v1 priority; added explicit constraint that unmaintained dependencies must be treated with caution and wrapped in adapter layers.
> - **v1:** Original brief that produced the validation pass in `compass_artifact_*.md`.

---

## 0. How To Use This Document

1. Open a **new, fresh Claude conversation** (incognito or new chat — not a project chat).
2. Confirm the model is set to **Claude Opus 4.7 Adaptive**.
3. **Enable Research mode** (toggle in the conversation interface).
4. Copy this entire document into the message box (or upload it as an attachment).
5. Send. Research mode will take 15–45 minutes and search the web extensively.
6. Save the Research output — that becomes the input for the next step.
7. **Next step (separate session):** Open another fresh Claude session (Research mode OFF). Paste the Research output + my project goals + the Proposed Architecture (Appendix A below). Ask Claude to produce a final Claude Code-ready plan `.md`.
8. **Final step:** Take that plan `.md` into Claude Code (Desktop app, not IDE) and let Claude Code build the project.

---

## 1. My Goal

I want to build a **GUI front-end for the `whipper` audio-CD ripping CLI** on Linux, distributed as **one installable file** wherever practical, with **EAC-equivalent (Exact Audio Copy) archival quality**. The GUI must run natively on my system (Bazzite, KDE Plasma 6) and ideally on other modern Linux distros too.

I have **limited programming experience**. I can read code, follow instructions, and modify small things, but I cannot architect or debug deeply. Therefore the chosen stack must be:

- **Readable** by a non-expert
- **Maintainable** with minimal mystery
- **Debuggable** without exotic tooling
- **Stable** — no fragile dependencies or sandbox workarounds

My eventual workflow:
1. **You (this Research session)** validate the proposed architecture against alternatives and surface anything I'm missing.
2. **I take your Research output** to a new Claude session and produce a final plan `.md`.
3. **Claude Code** consumes that plan and builds the actual application.

I am running **Claude Code in the desktop Claude application** (not the IDE plugin), so any tooling assumptions you make for the build step should fit that environment.

---

## 2. My Current State (What Already Works)

This is **not** what you're being asked to redesign. It's the baseline the GUI wraps.

- **Hardware:** Pioneer BD-RW BDR-209D, firmware 1.51, at `/dev/sr0`
- **OS:** Bazzite Linux (Fedora Atomic / rpm-ostree base, KDE Plasma 6 default)
- **`whipper 0.10.0`** is installed inside a **Distrobox container named `ripping`** running Fedora 40
- The `whipper` and `metaflac` binaries are **exported to the host** via `distrobox-export`, so they're callable from `~/.local/bin/whipper` on the host as if native
- **Whipper config** at `~/.config/whipper/whipper.conf`:
  ```ini
  [drive:PIONEER :BD-RW   BDR-209D:1.51]
  defeats_cache = True
  read_offset = 667
  ```
- **MusicBrainz Picard** and **Kid3** installed as **Flatpaks** for manual tagging
- A working bash helper `~/.local/bin/rip-cd` automates the CLI flow (insert → rip → tag fallback → eject)

**Key constraint from this setup:** the GUI must call the host-exported `~/.local/bin/whipper`, which transparently enters the Distrobox container to do its work. Any GUI distribution method that **can't reach that binary or `/dev/sr0`** is disqualified.

---

## 3. What I'm Asking You To Research

Address each of the following sections. Be thorough, cite sources, and call out where evidence is weak.

### 3.1 GUI framework comparison

Compare these options for a small-to-medium Linux desktop app that subprocesses to a CLI tool:

- **Python + PySide6 (Qt6)**
- **Python + PyQt6** (LGPL vs GPL licensing differences vs PySide6)
- **Python + GTK4 + libadwaita** (via PyGObject)
- **Python + Tkinter** (stdlib, simplest)
- **Python + Toga** (BeeWare, cross-platform)
- **Rust + Tauri** (web view backend, small binaries)
- **Rust + Slint** (native, no web view)
- **Go + Fyne**
- **Electron** (last resort, mentioned only for completeness)
- **C++ + Qt6** (heavier dev burden but mature)
- **Avalonia (.NET / C#)** on Linux

For each: native look on KDE Plasma 6, dev ergonomics, AppImage packaging difficulty, binary size, runtime stability, debuggability for a non-expert, Claude Code's likely strength with that stack, and ecosystem maturity for the specific task (subprocess wrapping + interactive prompt handling + table-based UI).

Recommend one primary + one fallback.

### 3.2 Single-file / cross-distro distribution methods

Compare:

- **AppImage** (build tools: `appimagetool`, `python-appimage`, `appimage-builder`, `linuxdeploy`)
- **Flatpak** — *critically* address whether the Flatpak sandbox can:
  - Access `/dev/sr0` or the optical drive
  - Execute a host binary like `~/.local/bin/whipper` (which itself enters a Distrobox container)
  - Read/write `~/.config/whipper/` (shared with the container)
  - Show desktop notifications and launch other Flatpaks (Picard)
- **Snap** (similar sandbox questions)
- **Static binaries via PyInstaller / Nuitka / cx_Freeze / Briefcase / py2app**
- **Native RPM and .deb packages** (rpm-ostree layering on Bazzite vs traditional distros)
- **pipx-installed Python package**
- **Just a Python project + install script**

For each: true single-file-ness, install simplicity for a non-technical user, security/sandbox concerns, build complexity, update story, file size, success rate on Bazzite specifically.

### 3.3 Interactive subprocess handling

`whipper cd rip` is mostly non-interactive but **prompts the user when MusicBrainz returns multiple release matches**. The GUI needs to either:

- Drive that prompt via **pexpect / pty / asyncio.subprocess** programmatically
- Or **bypass it entirely** by querying MusicBrainz directly (via `python-musicbrainzngs` or REST) and passing `whipper cd rip --release-id <MBID>` so whipper never prompts

Evaluate both approaches. Identify the **canonical method** real-world Linux rippers use (look at `cyanrip`, abcde wrappers, Asunder source, fre:ac, Sound Juicer).

### 3.4 Reference implementations to learn from

Examine the design and architecture of existing Linux CD-rip GUIs. For each: framework, distribution method, MB handling, code organization, last-active date, and what's worth copying or avoiding.

- **fre:ac** (cross-platform, Flathub)
- **Sound Juicer** (GNOME, archived/inactive?)
- **Asunder** (GTK, no AccurateRip)
- **K3b** ripping UI (KDE-native)
- **whipper-gtk** (unmaintained but informative)
- **AudioGridder, Rubyripper, Morituri** — historical references
- **EAC** (Windows, the gold standard — what UI patterns does it use that a Linux GUI should mirror?)
- **dBpoweramp** (Windows, also gold standard, different UI philosophy)

### 3.5 Optical drive access in modern Linux

Confirm or refute these assumptions:

- A non-sandboxed user-space app on Bazzite KDE can read `/dev/sr0` directly via the `cdrom` group / udev ACLs without `sudo`
- A Flatpak with `--device=all` can access `/dev/sr0`
- A Distrobox container can pass `/dev/sr0` through to its userspace (already proven in my setup)
- Calling a Distrobox-exported binary from a sandboxed Flatpak is not possible without `--filesystem=host`
- AppImage has no sandbox, so it can do all of the above unconstrained

If any of these are wrong, surface real-world Bazzite/KDE forum reports or upstream issues.

### 3.6 Honest Linux-vs-EAC quality gap

Quantify what's actually impossible on Linux today vs Windows EAC:

- **AccurateRip submission** — is there *any* Linux tool that submits? (whipper, cyanrip, fre:ac, anything else?)
- **CTDB (CUETools Database)** verification — is there *any* Linux implementation?
- **C2 error pointer use** — does any Linux ripper use them well?
- Anything else worth knowing.

This determines what to label "Out of Scope" in my final plan. I want this list to be complete and current as of mid-2026.

### 3.7 Risks and dealbreakers

What would cause the proposed Python + PySide6 + AppImage architecture (see Appendix A) to fail or become unmaintainable over 2–5 years? Specifically:

- PySide6 release cadence and breaking changes
- AppImage tooling abandonment risk (appimagetool, appimage-builder)
- Qt6 in KDE Plasma 6 versioning concerns
- Bazzite rpm-ostree base image flux (will the host-exported `whipper` still work after a rebase?)
- Python 3.11 → 3.12 → 3.13 compatibility for any chosen dependency
- MusicBrainz API breaking changes / rate limits
- libdiscid / libcdio dependency chain volatility

### 3.8 Out-of-scope but worth flagging

Anything else I'm missing — patterns from similar projects, common pitfalls, must-have features I forgot, security concerns, accessibility issues for KDE Plasma, packaging gotchas.

---

## 4. Required Output Format

Please structure your response as follows. **Cite sources throughout.**

### A. Executive Summary (top of response, ≤ 250 words)
Your overall recommendation for framework + distribution + interactive-prompt approach. State confidence level.

### B. Framework Comparison Matrix
A table comparing all the §3.1 frameworks across: native KDE look, dev ergonomics, AppImage packaging, binary size, debuggability, Claude Code's likely strength, ecosystem maturity. Plus 2–3 paragraphs of prose calling out the top 2 and bottom 2.

### C. Distribution Comparison Matrix
Same format for §3.2 options.

### D. Interactive Prompt Handling
Recommendation between pexpect-style and MB-API-bypass, with reasoning grounded in §3.4 reference implementations.

### E. Reference Implementations
For each tool in §3.4: bullet summary of architecture + 1 useful takeaway.

### F. Drive Access Confirmation
Per-bullet answers to §3.5. Each answer cites a source or marks itself as "no authoritative source found."

### G. Linux Quality Gap (mid-2026 state)
Bulleted list of what's possible/impossible on Linux today vs Windows EAC.

### H. Risks Assessment
Per-risk in §3.7: severity (High/Med/Low), evidence, mitigation.

### I. Critique of My Proposed Architecture (Appendix A)
Where do you agree, where do you disagree, what would you change?

### J. Final Recommendation
Restate the framework + distribution + prompt-handling combo + any other key decisions. Include a 1-paragraph justification.

### K. Open Questions for the User
Things I should answer before the plan-writing step. Keep this short and pointed.

---

## Appendix A — My Currently Proposed Architecture (validate or refute)

This is what I'm leaning toward. Tell me if it's right or wrong.

- **Language:** Python 3.11+
- **GUI framework:** PySide6 (Qt6)
- **Subprocess approach:** `subprocess` for non-interactive whipper calls + `python-musicbrainzngs` for MB lookups (bypass the interactive prompt)
- **Config storage:** TOML at `~/.config/platterpus/config.toml`
- **Distribution:** Single AppImage built via `python-appimage` (preferred — actively maintained, weekly automated rebuilds through 2025). `appimage-builder` is permitted only as a fallback if `python-appimage` cannot express a needed build step; in that case the recipe must avoid `appimage-builder`-specific features so a future swap back to `python-appimage` is cheap. A `pipx`-installable Python wheel is the secondary distribution channel.
- **Architecture:** GUI runs on host, calls the existing host-exported `~/.local/bin/whipper` (which itself enters the Distrobox container), no Flatpak sandbox

### Features (P0 — must have)

1. Drive selection dropdown (lists drives from `whipper drive list`)
2. Disc info panel (TOC, MB match status, AccurateRip availability — from `whipper cd info`)
3. MusicBrainz release picker (when multiple matches — driven by `python-musicbrainzngs`, not whipper's TTY prompt)
4. Editable track listing pre-rip (table view, edit per-track tags and album-level fields)
5. Rip execution with cancel
6. AccurateRip results display (per-track confidence parsed from the rip log)
7. Rip log viewer (read-only display of the `.log` file)
8. Settings page (output dir, working dir, track template, disc template, read offset, whipper/metaflac paths, auto-launch-Picard toggle)
9. Unknown album helper (rip with `--unknown`, apply `Track NN` placeholder tags via `metaflac`, optionally auto-launch Picard with the folder loaded)
10. Single-file AppImage as the primary deliverable
11. **Dependency self-management.** At launch (and on demand from a "Check dependencies" settings button), the GUI verifies every required dependency and its minimum version: `whipper` (host-exported), `metaflac`, `libdiscid` (system C library), `python-musicbrainzngs` (bundled), MusicBrainz Picard (only if the user has the auto-launch toggle on), and any encoder backends used by P1 MP3/WAV support once those land. Resolution follows a strict three-tier preference order:
    - **(a) Automatic install / upgrade** — preferred whenever the dependency can be installed without requiring elevation or out-of-band tooling. This covers: bundled Python wheels inside the AppImage (always resolved at build time), pipx-installable Python packages into the user's `~/.local/pipx/venvs`, and Flathub installs of Picard via `flatpak install --user flathub org.musicbrainz.Picard` after a confirmation dialog. The GUI does the work silently after one explicit user OK; no terminal commands surfaced.
    - **(b) Queued install list with one-click resolution** — for dependencies that can't complete automatically without user confirmation, batching, or a re-launch (e.g., several Flatpaks at once, or a Python wheel that needs a network retry), present them in a dedicated "Pending installs" dialog with per-item checkboxes, an "Install selected" button, and per-item progress feedback. The user clicks once; the GUI handles the loop.
    - **(c) Manual-install message box with copyable search string** — last resort, used only for dependencies that genuinely require something outside user-scope (e.g., a system `libdiscid` provided by `rpm-ostree install` on Bazzite, which needs a reboot and is policy-discouraged). The dialog shows: the exact missing item, the minimum version required, the reason it can't be auto-installed, and a clearly-labeled copyable text field containing a Google-search-ready query (e.g., `install libdiscid Bazzite Fedora Atomic rpm-ostree`). The "Copy" button is the primary action; "Close" is secondary.
    - **Rule of thumb:** if the install path is well-known and common, automate it. Only fall to tier (c) when the install genuinely depends on user judgment or root privileges.

### Features (P1 — backlog, do not build first)

- Eject button + auto-eject toggle
- Multi-disc queue
- Live progress bars per track
- Multi-drive support
- udev-driven auto-detect on disc insert
- ReplayGain calculation
- Auto-move completed rips to a library folder
- **Additional encoding outputs: MP3 and WAV** (FLAC is the v1 default and the priority for the first release; MP3/WAV come later once the FLAC pipeline is stable. Encoder backends — likely `lame` for MP3 and `sox`/whipper-native for WAV — must be detected and offered through the same P0 #11 dependency-resolution flow.)

### Out of scope (do not build)

- Replacing whipper itself
- AccurateRip submission (Linux gap)
- CTDB verification (Linux gap)
- "Test & Copy" dual-pass
- Network features (NAS, Plex, Jellyfin, cloud)
- Library/catalog database
- DVD/Blu-ray support
- Windows or macOS support

### Constraints

- Maintainer has limited programming experience → heavily commented, type-hinted, modular code
- All Python dependencies must be bundled in the AppImage
- Whipper config remains authoritative for offset/cache settings
- Subprocess output parsing must be robust to whipper minor-version changes
- **Treat unmaintained dependencies with caution.** Any upstream that shows >12 months of release inactivity must be wrapped in a thin adapter layer so a future replacement is feasible without rewriting the GUI. As of this brief's v2 revision, the dependencies known to be in this state are: **whipper itself** (no release since 0.10.0 on 17 May 2021; community-recognized active successor is `cyanrip`), **python-musicbrainzngs** (no PyPI release since 0.7.1 on 11 Jan 2020; underlying ws/2 REST API is still stable, but be ready to drop to `requests` against the JSON endpoint if it bitrots), and **appimage-builder** (Snyk-flagged inactive; prefer niess's `python-appimage` which has weekly automated rebuilds through 2025). The adapter pattern applies even when the dependency is currently working — the goal is to make replacement cheap, not to predict failure. Maintain a `DEPENDENCIES.md` in the repo that records each direct dependency's last upstream release date, current pinned version, and the planned replacement if/when retirement is needed; review this file before every tagged release.

---

## Appendix B — Reference Material

- whipper GitHub: https://github.com/whipper-team/whipper
- cyanrip GitHub: https://github.com/cyanreg/cyanrip
- fre:ac website: https://www.freac.org
- AccurateRip drive offset list: https://www.accuraterip.com/driveoffsets.htm
- MusicBrainz API: https://musicbrainz.org/doc/MusicBrainz_API
- Bazzite docs: https://docs.bazzite.gg
- Distrobox docs: https://distrobox.it
- AppImage docs: https://docs.appimage.org

---

## Appendix C — What I'm NOT Asking You To Do

- Don't write code. This is a research and recommendation document.
- Don't propose new features beyond the P0/P1 lists unless they fix a real gap.
- Don't recommend macOS/Windows ports (Linux-only project).
- Don't recommend cloud-hosted or web-SaaS solutions.
- Don't suggest replacing whipper.

---

*End of research brief. When you finish, your output should be self-contained enough that I can paste it into a fresh Claude session along with this brief and Appendix A, and get a buildable Claude Code plan.*

---

*Last updated for Platterpus v0.5.0.*
