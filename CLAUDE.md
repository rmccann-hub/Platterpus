# CLAUDE.md — Platterpus Project Context

This file is loaded by Claude Code on every session in this project. It keeps **only what a session needs on every task**: each rule's operative sentence and a pointer to where its full text and incident history live (trimmed to that on 2026-11-16, `TASKS.md` R32; `tests/test_claude_md_size.py` holds it there). The **rules** section below the line is locked — do not edit it without explicit user confirmation. The **project operations** section at the bottom grows as the project develops; keep it to commands and the rules that bite, and put the reasons in the document the pointer names.

---

## Project

Linux GUI front-end for the `cyanrip` audio-CD ripping CLI. EAC-equivalent archival quality, single-file AppImage distribution. Primary target: Bazzite Linux with KDE Plasma 6. Secondary: Fedora, Arch, Ubuntu, and other modern desktop Linux.

## Stack (locked)

- Python 3.12+ (3.11 until 2026-11-02, dropped on the owner's word that day; `PLANNING.md` KDD-46)
- PySide6 (Qt6) for the GUI
- `subprocess` for the ripper CLI invocation (cyanrip — the sole backend, KDD-18; whipper was removed 2026-06-30)
- `python-musicbrainzngs` for MusicBrainz lookups (so the ripper never shows its own interactive prompt)
- TOML config at `~/.config/platterpus/config.toml`
- `python-appimage` for AppImage builds
- `pipx` install as the secondary distribution channel

## Architecture (locked)

The GUI runs on the host. It calls the host-exported ripper binary in `~/.local/bin/` (currently `~/.local/bin/cyanrip` — see KDD-18 / the Stack note below; the historical `~/.local/bin/whipper` worked the same way), which transparently enters the Distrobox container named `ripping` to do the actual ripping work. The GUI never tries to run the ripper in its own process, install it itself, or assume a native ripper on the host. **This routing is non-negotiable** — it's how the user's system is configured and the brief disqualifies any distribution that can't reach it.

## Code conventions

Each convention's full text as it stood on 2026-11-16: `docs/architecture.md` §3.14.

- **Comments:** heavy. The maintainer has limited programming experience — comment intent, not mechanics. A reader who can read Python but doesn't deeply know Qt or cyanrip should understand the file.
- **Type hints:** mandatory on all function signatures, class attributes, and module-level constants.
- **Modules:** small and focused, one responsibility each; split when a file exceeds ~300 lines — a *heuristic for cohesion*, not a hard cap. A heavily-tested Qt "god-object" (e.g. `MainWindow`) is split via **mixins** so methods stay reachable as `window._x` (`docs/architecture.md` §3.6).
- **No clever metaprogramming.** Avoid decorators that mutate behavior unobviously, dynamic class creation, monkey-patching, or "magic" imports.
- **Never block the GUI thread.** Any operation that can take more than a few milliseconds — `subprocess.run`, network I/O, large-file hashing/copying, `thread.join()`, `kbuildsycoca6` — must NOT run on the Qt main thread. Need the result → a `QObject` worker on a `QThread` (or a daemon thread reporting back via a queued signal); don't → fire-and-forget `subprocess.Popen(..., start_new_session=True)`. **The recurring trap is a modal dialog that does the blocking work itself in a button slot**: such work runs on a worker thread, and the injected callable is thread-safe (no Qt, no sub-dialogs). Ask of every change: *if this ran on a stalled network or a cold container, would the window freeze?* (`docs/architecture.md` §3.2, "Dialogs that do blocking work".)
- **Error handling:** catch specific exceptions, never bare `except:`. Log with the `logging` module, not `print`.
- **Validate every input and every dependency output — visibly, and to the log** (full convention: beside institutional rule 11 in `docs/testing.md` §5). **Inputs** (Settings, config values, CLI args) are validated for type, range, character set and format at the boundary by a **pure, testable function** (e.g. `settings_validation.py`), with a visible, specific error and a log line; a widget's own constraint is a convenience, not the validation. **Outputs to dependencies** satisfy the tool's contract (`docs/dependency-contracts.md`) — **range as well as syntax, enforced by code at the argv chokepoint**. **Diagnostic completeness:** capture the exit code (tri-state, `null` for a child never reaped), the exact argv (read off `Popen.args`) and the complete output, stderr merged; bounded output keeps **head *and* tail** with a counted elision mark, and what we capture we **surface** (`docs/cyanrip-handshake.md` §7.1).
- **Subprocess output parsing:** robust to cyanrip minor-version output changes. Use named-group regexes, not column-index splits. Parsers of external output **never raise** — they return a best-effort dataclass and get a `hypothesis` "never raises" property test.
- **Say which build produced an artifact** — fork or upstream, in the rendered log *and* the JSON, **tri-state** ("not determined", never the negative), classified only by `ripper_identity.py` (`docs/cyanrip-handshake.md` §7.2).
- **A new testing capability is a SCRIPT VERB; a CLI flag is the exception, and it has to be argued for.** Add a verb to `uiscript/verbs.py` + a `_do_<verb>` handler and regenerate `docs/script-language.md`; a `--flag` only where no GUI exists or another repository must call it, and then both are thin callers of one function. Enforced by `tests/test_script_surface_is_the_default.py` (`docs/architecture.md` §3.10).
- **Accessibility is a code convention — target WCAG 2.2 AA** (`docs/ux-design-principles.md` → *Conformance target*; `tests/test_accessibility_standards.py`): **(1)** status is never colour alone (`✓`/`⚠`/`ⓘ`); **(2)** no single-character keyboard shortcuts; **(3)** an explicit size is one you own — 24 px floor, 44 px for anything that commits; and **a gesture must never change a value** (`ui/scroll_guards.py`).
- **Naming:** snake_case for functions, variables, modules; PascalCase for classes; SCREAMING_SNAKE_CASE for module-level constants.

## Critical rules

1. **External tools and unmaintained dependencies require adapter layers.** Currently flagged: `python-musicbrainzngs` and `appimage-builder` (if ever reached for) are unmaintained; `cyanrip` is the external ripper (actively maintained, but still an external CLI). Every call into these MUST go through a thin adapter module so a future replacement is feasible without rewriting the GUI — the `RipBackend` ABC (`adapters/rip_backend.py`) is exactly this seam, which is what let whipper be swapped out for cyanrip cleanly (KDD-18). Adapter modules are mandatory, not optional.

2. **`python-appimage` is the AppImage builder.** Do not use `appimage-builder` without stopping and asking first. If a build requirement cannot be expressed in `python-appimage`, describe the specific limitation in detail before reaching for any alternative. If `appimage-builder` is approved as a fallback, the recipe must stay close enough to vanilla that swapping back is cheap.

3. **Distrobox routing is sacred.** The GUI calls the host-exported ripper in `~/.local/bin/` (currently `~/.local/bin/cyanrip`). It does not call into the container directly, does not assume a native ripper, does not try to install or update the ripper itself. (The ripper *binary* changed — whipper → cyanrip-only, 2026-06-30, KDD-18 — but the routing pattern is unchanged and remains non-negotiable.) The one scoped, user-approved exception (2026-05-31): force-stopping a runaway drive on rip-cancel may kill the reader process — device-scoped on the host first and, only if the host saw nothing, inside the container — see `drive_control.py` and the drive/reader-control section of `docs/dependency-contracts.md`.

4. **FLAC is the default and the archival master; MP3, WavPack, and WAV are derived outputs.** Every rip produces FLAC first and **keeps it**; another format is derived from it through the *single* transcode adapter (`adapters/transcode.py`), and every encoder routes through the one dependency subsystem — **no bespoke per-encoder install code**. WAV keeps only basic tags and no cover art, and the UI warns. (Full text and its amendments: `docs/architecture.md` §3.14.)

5. **No bypass of MusicBrainz query path.** Always query MusicBrainz via the `MusicBrainzClient` adapter (currently backed by `python-musicbrainzngs`) to obtain the release first. The ripper's own metadata lookup is always disabled (cyanrip runs with `-N` and is fed the GUI's already-fetched, user-edited tags via `-a`/`-t`), so its interactive prompt never surfaces and the rip needs no in-container network.

6. **Dependency self-management is one subsystem, not scattered checks.** All "is this dependency present and the right version" logic lives in a single module with the three-tier resolution strategy (auto-install → queued install → copyable search string). New dependencies route through it; no ad-hoc availability checks elsewhere in the codebase.

7. **Documentation currency is part of "Done."** A change is finished when the *record* matches the code. Four obligations:
   - **In the same commit as the change:** the `CHANGELOG.md` `[Unreleased]` bullet (CI backstops this). Pure historical-record commits are exempt and carry a `[skip changelog]` line of their own.
   - **Before ending a session:** append a `docs/session-log.md` entry (newest-first).
   - **Graduate every durable lesson to its real home** — a rule here, a KDD in `PLANNING.md`, or `docs/architecture.md` / `docs/testing.md`. A lesson left *only* in the log is not graduated.
   - **A NEW file is the last resort, and the commit must name the homes it rejected.** Amalgamating means moving content under a named heading in the target and deleting the source, never summarising it away; retiring a file retires **every inbound link** in the same commit, and names the dead file as a **label, not a path** (write ``the former `appimage-testing.md` ``). A recurring activity's sheet is rewritten in place, never joined by a sibling; an EAC-compatible log stays as close to EAC as possible without forging it (`docs/eac-parity.md`). The rule travels to the fork. The measured case and full text: `PLANNING.md` KDD-20; the rule as it stood on 2026-11-16: `docs/architecture.md` §3.14.

   The checklist is the **Definition of Done in `docs/testing.md §6`**; the self-audit before claiming completion is **`docs/TEST-VERIFICATION-CHECKLIST.md`**, run at **Tier 2**, whose Final Report's `DID NOT RUN`, `KNOWN GAPS` and `RISKS` sections may not be empty. Institutional, non-negotiable.

8. **No copyrighted media in the repo — ever, not even temporarily.** This repository is public. Never `git add`/commit a music file or any other copyrighted media — **no `.flac`, `.wav`, `.mp3`, `.m4a`, `.aac`, `.ogg`, `.opus`, `.wv`, `.ape`, `.aiff`, `.dsf`, etc.** — and this includes *temporary* files dropped in for testing. Owning the disc does not grant redistribution rights, and a public commit (and git history) is redistribution. **How we test with real audio instead:** work on it **outside the repo** — the session scratchpad or a `/tmp` dir — and delete it when done; the durable proof we commit is the **text** artifact (EAC/whipper/cyanrip **logs** + per-track **CRCs**), never the audio (the CRCs prove bit-perfection without it — see `output_reference/README.md`). `.gitignore` denies audio extensions as a backstop, but the rule is the line of defense, not the backstop. If a test genuinely needs real PCM, use a **short, self-generated or CC0/public-domain** sample, never a commercial track. Same bite as the rules above: institutional, non-negotiable.

9. **Qt / PySide6 threading rules.** Every one was paid for with a crash or a freeze; each one's full statement and incident is in `docs/architecture.md` §3.2 (one copy, R236).
   - **NEVER drop the last Python reference to a running `QThread`** (`qFatal` → `SIGABRT`). If a thread cannot be stopped, **abandon** it: keep the reference in a module-level list.
   - **Retaining a reference does NOT make process exit safe**: an exit path that can run with a live abandoned thread bypasses teardown (`platterpus.hard_exit`) and flushes the log first.
   - **NEVER say "detach".** Qt has no detach operation. Say "abandon", and retain the reference.
   - **`quit()` only reaches a thread sitting in its event loop.** Every worker that blocks exposes a `cancel()` that kills its child (`Popen` with `start_new_session=True`). **A flag-only `cancel()` the blocked call never checks is a false promise** — grep for a reachable call site before believing one.
   - **Never `wait()` on a child whose output pipe you have stopped draining**: bound the wait, escalate to a **group** SIGKILL, bound that wait too, and report an unreapable child.
   - **`worker.finished → thread.quit` is a QUEUED connection**; after `app.exec()` returns it is never delivered, so it is never the only stop mechanism.
   - **Shutdown order is: `cancel()` every worker, THEN `quit()`, THEN wait**, and **bound the whole shutdown** with one `ShutdownDeadline`; never hand `QThread.wait()` a negative number.
   - **Only the GUI thread touches widgets.** Workers communicate via signals.
   - **Every `QThread` slot the window declares is stopped in `closeEvent`** (`tests/test_harness_fidelity.py`), and so is **every** class's thread, swept by `tests/test_qthread_ownership.py` — read the live count from `tests/test_qthread_ownership.py::_WORKERS_WITHOUT_CANCEL`, never from prose (`docs/testing.md` §5.o).

10. **Typing is strict, and the standard is stricter than the checker.** `mypy` is `--strict`-equivalent with a shrinking per-module opt-out list in `pyproject.toml`; retire one opt-out per commit, never add one. `from __future__ import annotations` in every module; every parameter and return annotated including `-> None`; every class attribute annotated; `X | None` never `Optional[X]`; no untyped dict as a pseudo-struct; `Signal(object)  # list[DriveDescriptor]` names the payload. **No bare `Any`**, no bare `# type: ignore` (always `# type: ignore[code]  # reason`). **Do not weaken a type to make a checker pass.** (Full text: `docs/architecture.md` §3.14.)

11. **A tool that gates CI must not float.** `ruff` and `mypy` are pinned to the minor they were measured against; bumping one is a deliberate commit that re-runs the gate. Non-gating tools stay loose. **The same reasoning reaches a floating *runtime* dependency:** PySide6 is pinned to the minor — `>=6.11.1,<6.12` in `pyproject.toml`, `PySide6~=6.11.1` in the AppImage recipe (which must use `~=`) — because a patch release silently removed two menu shortcuts, and **anything we ask a dependency for, we check the answer to** (`main_window.standard_shortcut`). **The pin has to bind where the gate runs**: the workflow installs a hashed lock derived from `pyproject.toml`, `tests/test_dependency_locks.py` refuses a lock outside its ranges (wording amended on the owner's word of 2026-11-16, TASKS R92), and `tests/test_gating_tools_are_pinned.py` refuses a literal version in a workflow. When you quote a number out of a tool, **record the tool version beside it**. Full statement and the incidents: `docs/testing.md` §5.r.

12. **The cyanrip seam is bidirectional, and both directions are enforced by tooling — not by memory.** Each obligation's full text, incident record and 2026-11-16 wording are in the `docs/cyanrip-handshake.md` subsection named (one home, R236; §7.7o maps them):
    - **Each side publishes its half of the contract, machine-derived where possible.** Ours is `docs/cyanrip-consumer-contract.md`, generated by `scripts/emit_dependency_contract.py`, never hand-written; theirs is the provider contract. (`docs/cyanrip-handshake.md` §7.)
    - **The handshake is AFFIRMATIVE, BILATERAL, and checked at the drive**: a round closes only when **both** sides declare `GO`; every handshake file opens with the shared wire header of **`docs/handshake-protocol.md`** (the same file in both repos, its §8 table run by `tests/test_handshake_conformance.py`); both versions are named; every rip verifies its own ripper (`handshake_approval.py`; read `rip_report.REPORT_SCHEMA_VERSION`, do not quote it); `not_determined` is not a pass. (§7.7a.)
    - **Each round is two files and two verifications** (`scripts/handshake.py --emit N` / `--check <file>` / `--status`). **A round is OPEN until both verifications declare GO. No pin switch while one is open; a release does not wait on a round** (protocol v8 §6b, E1 and E9). A missing verdict fails closed. (§7.5, §7.7b.)
    - **Full error capture, both directions, always surfaced** — and *show the user the dependency's own sentence*. (§7.1.)
    - **The fork must identify itself** (`platterpus-fork` in the version banner, on `--version` and every rip's logfile); we classify tri-state. (§7.2.)
    - **A build tag names a commit; it does not name what was built** — `-dirty` on a dirty tree, classify on the fork *id*, and derive provenance from the artifact's content. (§7.3; `PLANNING.md` KDD-34.)
    - **A moving pin needs a route that does not ship inside a release**: `platterpus --install-ripper`, driving the wizard's step engine. (`PLANNING.md` KDD-34.)
    - **Both halves of the seam are checked, mechanically, every commit**: `tests/test_argv_surface_agreement.py` and `tests/test_cyanrip_version_flag.py`. (§7.7c.)
    - **A dependency's own flags are a validated surface, not trivia**: probe invocations go through the argv-chokepoint rule too.
    - **State the range a contract claim covers, not the snapshot.** (§7.7d.)
    - **An upstream change cannot be escaped by rolling back to upstream** — ask whether a failure is ours, the fork's or upstream's. (§7.7e.)
    - **Both directions are sanitised and error-checked, at the boundary, by code** (`docs/seam-rules.md`, byte-identical in both repos). *Outbound:* every rip argv passes `assert_metadata_lookup_disabled`, and any new route to the ripper **delegates to the chokepoint**. *Inbound:* their output is external input, and every widget carrying it is `PlainText` (`tests/test_message_boxes_are_plaintext.py`, `tests/test_labels_state_their_text_format.py`). A fix we find in ourselves that **could in any possible way** help them is sent as a NEXT-ROUND item. (§7.7f.)
    - **The fork has a standing CHALLENGE MANDATE, and it is asymmetric on purpose**: answer the questions, it absolves us of nothing, and count who is right in the *Challenge ledger*. (§7.7g, §9.)
    - **A round must be able to end**: S-13 fixed close conditions, S-14 fix within the round, S-15 a fixed test pin, S-16 targeted questions, and a binding pre-commit. (`docs/seam-rules.md`; §7.7h.)
    - **THE FORK IS THE CORE, AND MAKING SURE THEY PERFORM CORRECTLY IS OUR JOB**: verify their emissions every lap (`docs/OWNERSHIP.md` §3), derive the number from their source where reachable, never put on them a defect we started. **NOT bilateral, and it does not travel.** (§7.7i.)
    - **LAPS TRAVEL BY GIT. Write the lap, commit it, push it, then tell the maintainer to point the peer at it.** **Publishing is not sending:** a lap is emitted `HANDSHAKE-READY-TO-READ: no` and `handshake.py --announce <lap>` flips it **on the maintainer's word only**. A mechanism claimed in their code carries `cyanrip@<sha>:<path>:<line>`; **`main` is the ref of record** (`tests/test_no_lap_is_left_unsent.py`). (§7.5c, §7.7j.)
    - **This rule lives in both repos**; send a change to the fork in the same round, except the two carve-outs (*the fork is the core*, the checking we owe them). (§7.7k.)

## How to stop shipping the next one (read before calling a fix done)

Three consecutive releases each fixed a real bug and introduced the next. Answer these **in the commit message**, not in your head. Each question's full statement and the incident behind it are in the section it names; the rest, in their 2026-11-16 wording, are `docs/testing.md` §5.bw.

- **Did I reproduce the symptom, or only explain it?** (`docs/testing.md` §5.t.)
- **What new state does this fix create, and what tests *that*?** And of state it *unblocks*: what does downstream code do with answers it never used to receive? (`docs/testing.md` §5.s, §5.ak.)
- **Did I check the preconditions where the thing HAPPENS, or where it was scheduled?** (`docs/architecture.md` §3.12a.)
- **Would this test fail if I reverted the fix?** Check by actually reverting it, with `scripts/revert_probe.py`; `git checkout -- <file>` on uncommitted work deletes the feature. (`docs/testing.md` §5.t.)
- **Am I asserting that a thing HAPPENED, or that it was REQUESTED?** (`docs/testing.md` §5.ap.)
- **What pins my input?** (`docs/testing.md` §5.ah.)
- **What else WRITES to the field I'm reading — and does it write for a reason I would not want to override?** (`docs/testing.md` §5.aq.)
- **"Fail-safe" is defined against the thing being protected — say WHICH failure the safe direction avoids.** (`docs/testing.md` §5.bw.)
- **"Idempotent", "free", "harmless to repeat" are properties of the CALLEE** — harmless *to whom*? (`docs/testing.md` §5.ay.)
- **An ABSENCE in a log is a fact about the logger before it is a fact about the subject.** (`docs/testing.md` §5.az.)
- **Can this check be satisfied by finding nothing?** Then give it a floor. (`docs/testing.md` §5.t.)
- **A GREEN RUN IS EVIDENCE ONLY ABOUT THE THINGS ITS CHECKS COULD HAVE FAILED OVER** — name the artifact whose absence would turn its most important step red. (`docs/testing.md` §5.bi.)
- **A COMPLETENESS FIELD DERIVED FROM CONFIG DESCRIBES WHAT WAS REQUESTED, AND WILL BE READ AS WHAT HAPPENED.** (`docs/testing.md` §5.bi.)
- **A GUARD THAT DROPS A RESULT MUST NOT ALSO DROP THE WORK** — is the thing discarded a CLAIM or a DELIVERABLE? (`docs/testing.md` §5.bi.)
- **A SECTION'S DISTINGUISHING PROPERTY IS ASSERTED AT THE SECTION, NEVER INHERITED.** (`docs/testing.md` §5.bj.)
- **OF ANY EARLY RETURN, ASK WHICH CASE IT SKIPS AND WHETHER THAT CASE IS THE EXPENSIVE ONE.** (`docs/testing.md` §5.bj.)
- **Can it be satisfied by the *wrong* thing?** (`docs/testing.md` §5.ad.)
- **Read a step by what DEPENDS on it, not only by what it asserts.** (`docs/testing.md` → *Acceptance tiers*.)
- **When a change moves who plays which ROLE, every validator built around the old roles is wrong — in BOTH directions.** (`docs/testing.md` §5.bw.)
- **Do two surfaces answer this question, and do they use the same key?** (`docs/testing.md` §5.al.)
- **Two implementations agreeing is not either one being correct.** (`docs/testing.md` §5.ac.)
- **Is the population I measured closed?** (`docs/testing.md` §5.ao.)
- **Did I verify this where it could have failed?** (`docs/testing.md` §5.bw.)
- **What does my stand-in do that the real thing does not?** (`docs/testing.md` §5.t.)
- **Is the user's symptom gone, or just the mechanism I named?** Where only hardware can settle it, say so. (`docs/testing.md` §5.s.)
- **If the contract has two halves, did I check both?** (`docs/testing.md` §5.bw.)
- **Am I verifying the behaviour, or the other side's *description* of the behaviour?** (`docs/testing.md` §5.ab.)
- **A NUMBER THAT DOES NOT REPRODUCE IS A STATEMENT ABOUT MY METHOD BEFORE IT IS A STATEMENT ABOUT THEIR FILE.** (`docs/testing.md` §5.bw.)
- **A DEAD FIELD IS WORTH CHECKING FOR WHAT IT GATES BEFORE PROPOSING TO STRIKE IT.** (`docs/testing.md` §5.bw.)
- **Am I answering from the artifact, or from my memory of the artifact?** (`docs/testing.md` §5.u.)
- **Does this document promise completeness? Then it needs a sweep, not a comment.** (`docs/testing.md` §5.af.)
- **Did a *correction* get less scrutiny than a claim?** And an *apology*? (`docs/testing.md` §5.ax.)
- **Never state a mechanism in the other side's code without citing where you read it.** (`docs/testing.md` §5.ax.)

## Deviation policy

The full text as it stood on 2026-11-16: `PLANNING.md` §9. When in doubt, stop and ask the user. **Must ask before:** adding a dependency not listed in `DEPENDENCIES.md`; changing the distribution model; switching the GUI framework; skipping, reordering, or redefining a P0 feature; reaching for `appimage-builder`; bypassing the host-exported `~/.local/bin/<ripper>` routing; adding scattered dependency checks outside the self-management subsystem; **switching the container to a new cyanrip pin while a handshake round is open**.

**Just do it (no ask needed):** renaming a function, variable, or local module; splitting an oversized file; small refactors for readability or project style; type hints, docstrings, comments; import order and linter formatting; **writing, committing and pushing a handshake lap** (then tell the maintainer which commit it is on; Critical rule #12). The line between these is judgment; when in doubt, ask.

## Working with the maintainer (learned)

Guidance, not law; the full text of each bullet as it stood on 2026-11-16 is `PLANNING.md` §9.

- **North star: "good music, good cover image, good everything"** — bit-perfect audio (provable via CRCs), correct tags, embedded cover art.
- **UX responsiveness is a feature, not a polish item.** A working feature that *feels* broken (frozen, silent, ambiguous) is a bug.
- **Zero-terminal for end users** (KDD-17): download one file, double-click, answer prompts.
- **Limited programming experience → optimize for the next reader.** Explain *why*; the maintainer asks "is this arbitrary or is there a reason?" and deserves the reason.
- **Build for contributors who aren't them**: leave extension seams and document them (`docs/architecture.md`).
- **EAC is the gold standard: match it 100% and we succeed; beat it and we win.** A gap where EAC succeeds and we do not is **parity** and comes first; label tasks parity or win (`docs/eac-parity.md` → *Standing direction*).
- **Real hardware is the ground truth**; flag hardware-gated work honestly.
- **"Burn" means writing a disc, and only that, on both sides** (the owner, 2026-11-11). Say *the five-rip run*, *repeat rips*, *used up*, *caught out*; records keep what they said, and `tests/test_burn_means_writing_a_disc.py` holds everything current.
- **Test the drive once, up front; test the disc per disc** (the owner, 2026-11-12): drive properties run at drive setup and are saved to its profile; only disc-dependent work runs per disc.
- **Every shipped bug gets a regression test in the same change.** Institutional, non-negotiable.
- **A version number is a claim about the field, not about CI** (KDD-35; `docs/testing.md` §5B). **0.8.1** needs a complete hardware pass, every test green in ONE run, twice, on two machines and two distros; `0.7.100` is the maintainer's numbering, not a typo. The classification of a failure is a property of the TEST, declared in advance (`docs/testing.md` → *Acceptance severity*).
- **Never hand back an instruction file. Hand back three steps and a file to run** (2026-08-11): short prose — *do the ordinary thing; run this; upload the result here* — and automation absorbs the rest. If a step resists automation, say which and why.
- **Times: every record in UTC; to the maintainer in New York time on a 12-hour clock, labelled, with UTC beside it** (e.g. *6:33 PM EDT (22:33 UTC)*). **Read the time from `date -u`; never estimate it.**
- **Momentum with safety.** Act on reversible, in-scope work without asking, commit in small test-green units, report at milestones; stop for destructive or scope-changing decisions.
- **Releases are HELD from 2026-10-12 until the owner says otherwise; only the owner's word releases, and each word covers the one release it names.** Until the owner lifts the hold, prepare a release (version bump, CHANGELOG, generators) only when asked, and never dispatch `release.yml` on your own judgement. Each word and the release it covered: `docs/architecture.md` §6.3 → *The release hold, and each word that released through it*.

## Reporting to the operator

Operator's instruction of 2026-10-14; the full text (the eight Diagnostics keys, the round summary's seven headings, and the rest) is `docs/cyanrip-handshake.md` §7.7n.

- **Diagnostics in every lap**: end it with "## Diagnostics", keys D1–D8 in order, one NOTE line each, "none" where nothing applies. **The last lap of each round** carries a "## Round summary" before it.
- **The first question, in every session and before every lap: who released the last lap, and who holds the next?** Answer it from both sides' published laps with `python3 scripts/lap_turn.py --peer <clone of the fork> --fetch`, never from memory.
- **The sessions read each other directly.** At session start and before ending any turn, fetch the fork's `platterpus-fork` and read its `STATUS.md` and every lap released since the newest we filed; a released lap addressed to us is the cue to answer it. `ASK:` carries only what the owner keeps.
- **A handoff prompt at the end of every reply** that releases a lap, pushes to evidence, merges a pull request the other side needs, or needs something from anyone — this block, filled in, nothing after it; the first line is copied from `lap_turn.py`'s `turn_line`, never typed:

```
MY TURN TO SEND|MY TURN TO WAIT: round <x> lap <y> goes to <repo branch>, expecting round <a> lap <b> back
HANDOFF from <platterpus|fork>, <UTC time>
DONE: <one line: what happened>
READ: <repo> <branch> <path, PR or evidence commit> at <commit>
NEXT: <one line: what the reader should do now, or "nothing, for information">
ASK: <a question for the operator, or none>
```

If a reply needs no handoff, end it with: HANDOFF: none

## Companion documents

**`docs/README.md` is the canonical annotated index**; one line each here (the longer list as it stood on 2026-11-16: `docs/README.md` → *`CLAUDE.md`'s companion list*):

- **`PLANNING.md`** — architecture, module map, and the numbered KDD decision log
- **`TASKS.md`** — the active task checklist; update status (`[ ]` → `[~]` → `[x]`) in the same commit as the work
- **`DEPENDENCIES.md`** — dep pins, review cadence, retirement log
- **`README.md`** / **`SECURITY.md`** — outward-facing description and install; security policy
- **`docs/README.md`** — the complete annotated index of docs/ and the rebuild checklist
- **`docs/architecture.md`** — the contributor guide: patterns with their *why*, extension recipes, packaging and release. **Start here to extend the program.**
- **`docs/testing.md`** — testing strategy, institutional rules, and the Definition of Done
- **`docs/TEST-VERIFICATION-CHECKLIST.md`** — the Tier 2 self-audit before claiming a task done
- **`docs/test-plan.md`** — manual & release testing (acceptance run, EAC parity, hardware cases)
- **`docs/dependency-contracts.md`** — exact args/flags per external tool + parsed output shapes
- **`docs/platterpus-research-brief-v2.1.md`** — the project brief; canonical for requirements/scope *as amended by the KDDs*
- **`docs/ux-design-principles.md`** — the trust-first UX principles + the canonical gap backlog
- **`docs/session-log.md`** — per-session chronology (newest first); lessons graduate out of it
- **`docs/cyanrip-handshake.md`** — the binding, bidirectional release handshake with the cyanrip fork
- **`docs/cyanrip-consumer-contract.md`** — **generated, do not hand-edit**: our half of the cyanrip contract
- **`docs/cyanrip-fork.md`** — the cyanrip fork: why, the soft-fork runbook, the ask list, the upstream roadmap
- **`docs/eac-parity.md`** — the single home for EAC parity
- **`docs/github-workflow-sop.md`** — git and GitHub mechanics, and this repository's commit and PR practice
- **`docs/archive/`** — retired dated investigations + external reference; graduation map in its README

If `PLANNING.md` and the brief conflict, the brief **as amended by the maintainer-approved KDDs** wins on requirements/scope and `PLANNING.md` wins on implementation choices. If `PLANNING.md` and the research output conflict, raise it with the user — don't silently pick. To refresh tool-choice research, follow `docs/platterpus-session-start.md` Step 0.

---

## Project operations

*Commands, paths, and the rules that bite. Terse; the reasons live where each pointer says.*

### Build commands

- AppImage: `bash build/build_appimage.sh` (produces `platterpus-x86_64.AppImage` via `python-appimage`; procedure `docs/architecture.md` §6.1)
- App icon: `python3 build/make_icon.py` (from `assets/platterpus-logo.svg`; needs an SVG rasterizer, **not** Pillow)

### CI / release

The full text of this section as it stood on 2026-11-16: `docs/architecture.md` §6.5; the reason for each step: §6.3.

- **CI** (`.github/workflows/ci.yml`, every push to `main` and every PR). Merge only when every **required** check is green; read the live list from the default-branch ruleset (`gh api repos/rmccann-hub/Platterpus/rules/branches/main`), never from prose. `mutation.yml` (weekly, non-gating) and `appimage.yml` run beside it.
- **Releases are IMMUTABLE once published**: a broken release is fixed by a new version, never by editing it.
- **Releasing is automated** — never hand-build or upload. Dispatch the Release workflow (`release.yml`) with the tag as input; it creates the tag itself. Before dispatching:
  - **(1)** bump `__version__` in **`src/platterpus/__init__.py`** — the *single source* (not `pyproject.toml`);
  - **(2)** move the `CHANGELOG.md` `[Unreleased]` entries under a new `## [X.Y.Z] — <date>` heading with a compare link;
  - **(3)** run **`pytest tests/test_no_stale_version_claims.py`** (the version-bump gate);
  - **(4)** restamp the docs the cycle touched: `pytest tests/test_doc_version_stamps.py` lists them;
  - **(5)** **re-run the generators AFTER the bump**: `python3 scripts/emit_script_language.py`, `python3 scripts/emit_dependency_contract.py`, `python3 scripts/emit_bom.py` (each has `--check`); `scripts/emit_ripper_inventory.py` only when a round ships a new provider contract;
  - **(6)** **re-run `pip install -e .` before believing a local suite run**, and read pytest's own exit code, not a pipeline's.
- **WAIT FOR `main`'s OWN CI BEFORE DISPATCHING THE RELEASE, and it is not the PR's run.** The release's CI gate reads the merge commit's run; do not loosen it. The gates that run at release time live in `release.yml`.
- **Update signing is never armed** (KDD-37 D9); the build attestation, checked fail-closed in the app, protects updates, so `release.yml` must attest before it publishes (`docs/architecture.md` §6.2).
- **Single record of changes:** `CHANGELOG.md` (Keep-a-Changelog); a bullet in `[Unreleased]` **in the same commit** as the change.

### Commit & PR hygiene

This section wins wherever the generic SOP differs; the full text as it stood on 2026-11-16 is `docs/github-workflow-sop.md` §0.

- **Atomic commits**: one logical change per commit, each test-green.
- **Subject:** `type(scope): imperative summary`, **lowercase** after the colon, no trailing period, no hard length cap. Types: `feat`, `fix`, `docs`, `test`, `refactor`, `style`, `chore`, `release`, `ci`, `build` (`scripts/check_commit_subjects.py`). Body wrapped ~72 cols: **what and why, not how**.
- **Required trailers** on every commit: the `Co-Authored-By:` line and the `Claude-Session:` line. Never put the model identifier in a commit, PR, or any pushed artifact.
- **Changelog in the same commit** (rule #7); the `[skip changelog]` exemption is strictly for a commit that changes nothing but the record itself — type annotations, CI config, dev tooling and refactors are **not** exempt.
- **Branch:** commit only to the session's `claude/…` branch; never push to `main`. GitHub deletes a merged head branch, so start the next change with `git switch -C <branch> origin/main`.
- **Every PR merges with a merge commit, never a squash** (squash and rebase are off): laps cite branch SHAs, and `tests/test_cited_commits_are_reachable.py` turns `main` red if one is stranded. A Dependabot bump is carried on a session branch with the regenerated files, and Dependabot's PR closed. Don't open a PR unless asked.
- **The agent git proxy is fast-forward-only**: no force-push, no branch delete, no tag push. `main`, `v*` tags and `evidence` are protected by repository rulesets (`PLANNING.md` KDD-43; read their live state from `gh api repos/rmccann-hub/Platterpus/rulesets`).

### Run commands

- **Quickstart:** `bash dev-setup.sh` then `source .venv/bin/activate && platterpus`; manual: `python3 -m venv .venv && source .venv/bin/activate && pip install --upgrade pip && pip install -e . && platterpus`
- **AppImage:** `./platterpus-x86_64.AppImage` — there is **no `platterpus` on `PATH`** for AppImage users, so pass every flag to the AppImage itself (e.g. `./platterpus-x86_64.AppImage --doctor`)
- **Version:** `platterpus --version`. **Preflight:** `platterpus --doctor`, or `python scripts/preflight.py --no-network` (logic in `src/platterpus/preflight.py`; non-zero on a hard blocker)

### Test commands

- **`python3 scripts/check.py` — run this, not an ad-hoc pipeline.** Every gate CI runs (`lint`, `format`, `types`, `tests` + coverage floor), each one's **real** exit code, full output in `.check-logs/`; `--only lint types`, `--no-coverage`. Never read a verdict through a pipe; use `${PIPESTATUS[0]}` or `set -o pipefail` (`docs/testing.md` §7).
- `pytest` from repo root (`pyproject.toml` sets `pythonpath = ["src"]`). CI runs 3.12–3.14 with `-n auto`, the coverage floor (`--cov-fail-under=93`, ratchets up, never down) on 3.14, and a collected-tests floor (`tests/collected-tests-baseline.txt`, raised in the change that adds tests).
- Property-based tests: `pytest tests/test_parsers_property.py`.
- **Prove a test isn't vacuous:** `python3 scripts/revert_probe.py <spec.json>` (`detected` / `VACUOUS` / `REFUSED` / `NO EVIDENCE`; spec format in its docstring).
- **Judge a commit's checks:** `python3 scripts/pr_steward.py --pr <N>` or `--sha <merge sha> [--logs]` (the `steward` skill); after every merge, judge `main`'s merge commit.
- **Round digest:** `python3 scripts/round_digest.py <round> [--exclude <lap.md>] [--show-rows]` (the fork's method; `tests/test_round_digest.py`).
- **Mutation testing** (weekly, non-gating, `scripts/mutation_sweep.py`, ours): e.g. `python3 scripts/mutation_sweep.py --target src/platterpus/verdict.py --tests tests/test_verdict.py --limit 40 --min-checked 30`. The workflow's matrix is the authority for the list and floors.
- **Every shipped bug gets a regression test in the same PR; every new parser of external output gets a property-based "never raises" test** (`docs/testing.md`).

### Lint / format / uninstall

- **Lint:** `ruff check src tests scripts build` (`--fix` to auto-fix). **Format:** `ruff format src tests scripts build`. **Type-check:** `mypy` (bare; config in `pyproject.toml`). All in the `dev` extra (`pip install -e ".[dev]"`).
- `bash uninstall.sh` (plan, ask, remove everything Platterpus created: the list Tools → Uninstall
  reads, `deps/install_footprint.py`; `--keep-settings`/`--keep-logs`/`--keep-picard`; rips kept)
- `bash uninstall.sh --dry-run` (shows what would be removed); `--yes` skips the question
- `bash uninstall.sh --help`

### Enforced safety (.claude/ + git hook)

The full text: `docs/architecture.md` §6.5.

- **`.githooks/pre-commit`** blocks a commit staging audio (rule #8); activate with `git config core.hooksPath .githooks` (`dev-setup.sh` and the SessionStart hook do this). `media-guard` in CI refuses the same file.
- **`.claude/settings.json`** denies destructive commands and secret reads, and **`.claude/hooks/audio_guard.py`** blocks a commit or push while audio is staged, failing closed.
- **The `evidence` branch stays out of every fetch**: where hooks do not run, `git config --add remote.origin.fetch '^refs/heads/evidence'`. A test reads evidence only through `tests/evidence_paths.py`.

### Artifact filenames that cross machines

**ASCII letters and digits only. No hyphens, no underscores, no spaces. Numbers zero-padded**, for artifacts a PERSON handles by hand (rig scripts, anything typed or pasted, anything that comes back through a chat client); case matches the fork's spelling (`round16lap01FROMcyanripTOplatterpus.md`). **NOT** the committed handshake laps (`round-14-lap-18.md`). `uiscript/find_script.py` is the guarantee; the full convention is `docs/cyanrip-handshake.md` §7.7l.

### Important paths

- Source root: `src/platterpus/`
- User config: `~/.config/platterpus/config.toml`
- User logs: `~/.local/share/platterpus/log.txt`
- Ripper binary (host-exported from Distrobox): `~/.local/bin/cyanrip`
- Legacy `whipper.conf`: `~/.config/whipper/whipper.conf` — **not read** by the app since 2026-09-24
  (`drive_profiles.py`); cyanrip does not use it, and the read offset lives in the GUI's own config.
  Only the uninstaller still removes it
- MusicBrainz Picard (Flatpak, used for auto-launch on unknown discs):
  `flatpak run org.musicbrainz.Picard`
- **The full map of everything Platterpus has or relies on** (languages, packages, external
  programs, the ripper fork and its container, services, CI): `bom.cdx.json` (CycloneDX 1.7,
  machine-readable) and its generated block in `DEPENDENCIES.md` → *The full map*. Both are
  generated by `python3 scripts/emit_bom.py` (`--check` to verify); never hand-edit either
- Help with the AI tooling itself (not Platterpus support): `docs/architecture.md` §6.5 → *Getting help (Claude Code / Anthropic)*

### Session history

The full text of every *Project operations* subsection trimmed here: `docs/architecture.md` §6.5. Chronological session notes live in **[`docs/session-log.md`](docs/session-log.md)** (newest first); a durable lesson graduates to its real home (rule #7).

---

*Last updated for Platterpus v0.7.130.*
