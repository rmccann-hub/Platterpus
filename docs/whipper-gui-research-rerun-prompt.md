# Whipper GUI — Research Mode Re-Run Prompt

> **Use this file when:** you can't recover the original `compass_artifact_*.md` from the v1 Research session, OR you want a fresh validation pass against v2.1 of the brief (which v1 research never saw).
>
> **You don't need this file if:** you already have the original compass_artifact. Use that directly with `whipper-gui-session-start.md`.

---

## How to use this prompt

1. Open a **fresh Claude conversation** (incognito or new chat — NOT inside a project).
2. Confirm the model is set to **Claude Opus 4.7 Adaptive**.
3. **Enable Research mode** (toggle in the conversation interface).
4. Attach **`whipper-gui-research-brief-v2.1.md`** to your first message.
5. Paste the message body below as the message content.
6. Send. Research mode will take 15–45 minutes.
7. When it finishes, the output will be delivered as a `compass_artifact_*.md` artifact. Download/save it.
8. That file becomes the input for the next step — feed it (together with the brief and `whipper-gui-session-start.md`) into a fresh Claude Code session.

---

## Message body — paste this verbatim

```
The attached file (`whipper-gui-research-brief-v2.1.md`) is a research brief for a Linux GUI project. It is version 2.1 of a brief that was previously validated in v1. The original v1 research output is unavailable, so I need a fresh validation pass against the current v2.1 spec.

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

## After Research finishes

1. Save the artifact to disk. Rename it if you like, but keep `compass_artifact_` as the filename prefix — `whipper-gui-session-start.md` looks for that pattern.
2. Open a fresh Claude Code session in the desktop app.
3. Attach three files to the first message: `whipper-gui-session-start.md`, `whipper-gui-research-brief-v2.1.md`, and your new `compass_artifact_*.md`.
4. Send: *"Read whipper-gui-session-start.md and follow it."*

Claude Code will then walk Steps 1 → 5 as documented in the session-start file.
