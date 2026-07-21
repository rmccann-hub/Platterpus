# Trust & quality deep audit (2026-07-08)

> **Status addendum (2026-07-21 — body below unedited, a dated record).**
> Several deferred rows have since closed: **#3** (static type checker) — a
> gating mypy CI job shipped in v0.4.23 and strict def-typing went
> package-wide 2026-07-19/20; **#9b** (known-disc re-rip overwrite) — the
> Replace / Rip-to-new-folder / Cancel confirm dialog shipped in v0.4.23;
> **#4** is partially done (`SOURCE_DATE_EPOCH` shipped in the build script;
> the hash-pinning half remains open). The "not yet audited"
> config-file / CLI-arg validation surfaces were swept and confirmed
> 2026-07-08/09 (see TASKS.md). One citation correction: the naming-sweep
> paragraph's "Critical Rule #3 — the ripper owns naming" conflates the rule's
> *number* — #3 is Distrobox routing; the ripper-owns-its-output principle is
> the routing rule's corollary, not its title. Live tracking: the TASKS.md
> trust-hardening section.

A maintainer-requested "what did we miss, especially around breaking trust"
audit. Research spanned seven categories — the four the maintainer named
(preventative practices, general best practices, input validation, naming
schemes) plus three chosen for the trust theme (**trust/verification-claim
integrity**, **security & supply-chain**, **reliability & failure-mode
handling**) — combining external best-practice research with a codebase audit.

**Method note (honest):** the audit was run as a fan-out workflow
(7 researchers → consolidate → 5 consensus reviewers → report). The 2-core
sandbox caps agent concurrency at 2, so the 14-agent run serialized far past a
practical wall-clock. The security/reliability/preventative researchers had
already produced **12 concrete, code-grounded findings** before it was stopped;
the consensus/justification step was then done directly against the code by the
maintaining agent (each finding verified in the source before being accepted or
deferred). Categories the workflow hadn't reached (naming, input-validation,
trust-integrity depth) are flagged for a follow-up pass — see the end.

Severity: **trust-critical** = could present a wrong/faked result, corrupt/lose an
archival master, or silently break bit-perfection.

---

## Fixed in v0.4.22

| # | Sev | Finding | Fix |
|---|-----|---------|-----|
| 9 | high (data-loss) | **Two unknown discs write to one fixed path and silently overwrite an archival master.** Both default to `Unknown Artist/Unknown Album/…`; the second rip clobbers the first. | `unique_album_title()` (pure, tested): an unknown-disc rip whose target folder already holds audio lands in a fresh `… (2)`/`(3)` sibling — never overwrites. Known/identified re-rips are deliberately *not* auto-suffixed (re-ripping to the same folder is usually intended; a confirm dialog is the tracked follow-up). |
| 5 | medium | **Atomic writers claimed crash *and power-loss* safety but never `fsync`.** `temp + os.replace` is atomic against a process crash, not a power loss (rename can reach disk before the data). The docstrings overstated the guarantee — a trust-claim honesty gap. | New `atomic_write.py` (temp → `flush`+`fsync` → `os.replace` → parent-dir `fsync`); `config.save`, `rip_report`, and `drive_profile_store` all route through it. Docstrings now match reality. |
| 10 | medium | **Config forward-compat dropped newer keys on a downgrade round-trip**, silently resetting a newer version's settings. | `config.save` now re-merges unknown keys (and keeps a higher `schema_version`) from disk, so an older binary's save can't drop a newer binary's settings. Round-trip test added. |
| 7 | medium | **CI granted the broad default `GITHUB_TOKEN`** (no least-privilege). | `permissions: contents: read` at the top of `ci.yml`. |
| 12 | medium | **Critical Rule #8 (no committed audio) had only client-side enforcement** (`.githooks/pre-commit`); a `--no-verify` or un-installed hook could push media to the public repo. | New `media-guard` CI job rejects any push/PR that introduces an audio-extension file — the server is now authoritative. |
| 8 | medium | **No dependency-vulnerability watch / disclosure path.** | `.github/dependabot.yml` (`pip` + `github-actions`) and a `SECURITY.md` with private-disclosure instructions. |

Every fix ships with a regression test; the full suite stays green and coverage
holds the ≥91 % gate.

---

## Confirmed but deferred (tracked follow-ups)

These are real and verified, but each needs either an owner-only asset, an
untestable-here surface, or a larger change — so they are tracked in `TASKS.md`
rather than rushed into this release.

| # | Sev | Finding | Why deferred / next step |
|---|-----|---------|--------------------------|
| 1 | **trust-critical** | **In-app updater verifies integrity (SHA-256) but not authenticity.** It downloads, `chmod +x`, and swaps in a binary with no signature check; a compromised release channel or MITM able to swap both the AppImage and its `.sha256` would be trusted. | **✅ Interim DONE (2026-07-08 follow-up):** `release.yml` now attests the AppImage with `actions/attest-build-provenance` (SLSA, GitHub OIDC + Sigstore, no dep/key) — `gh attestation verify … --repo rmccann-hub/Platterpus`; PyPI wheels attested via Trusted Publishing. **Still open:** real signing (minisign/ed25519) needs a **new crypto dependency** (CLAUDE.md "must ask") **and a signing key the maintainer holds**, plus making the updater fail-closed on a present-but-invalid signature *and* check the attestation. `SECURITY.md` documents the current boundary honestly. |
| 2/6 | high | **GitHub Actions pinned to mutable tags, not commit SHAs** — the release pipeline that builds the auto-updated binary is supply-chain-exposed. | **✅ DONE (round 2, 2026-07-08):** every `uses:` across `ci.yml`/`release.yml`/`publish-pypi.yml`/`appimage.yml`/`mutation.yml` now pins a full commit SHA (`# vN` comment); Dependabot (`github-actions`) drives the bumps via reviewed PRs. |
| 4 | medium | **AppImage bundles an unpinned, unhashed dependency graph; build is non-reproducible.** | Touches `build_appimage.sh`/`release.yml` which can't be built+verified in this sandbox; risk of breaking releases. Next: `pip-compile --generate-hashes` + `--require-hashes` + `SOURCE_DATE_EPOCH`, validated on a real build. |
| 3 | medium | **Type hints are mandated but no static type checker runs** — the annotations are unverified. | Adding `mypy`/`basedpyright` likely surfaces many findings; do it as its own ratcheting pass (non-strict baseline → strict on `adapters`/`parsers`/`workers` first), mirroring the coverage ratchet. |
| 8b | medium | **No `pip-audit` gate.** | **✅ DONE (round 2, 2026-07-08):** gating `pip-audit` CI job in `ci.yml` (currently clean; documented `--ignore-vuln` escape hatch for a fix-less advisory). |
| 11 | medium | **Test-efficacy guardrails are manual-only** (mutation testing; "every bug gets a regression test" has no CI signal). | **✅ DONE (round 2, 2026-07-08):** weekly non-blocking `mutation.yml` (`mutmut` over `parsers/`, `verdict.py`, `ctdb/crc.py`) + advisory `tests-touched` PR check mirroring the changelog gate. |
| 9b | medium | **Known-disc re-rip overwrite.** The unknown-disc case is fixed; re-ripping an *identified* album to the same folder still overwrites without asking. | Usually intentional, so it wants a confirm dialog (GUI-thread, needs hardware/UX verification), not silent auto-suffix. |

---

## Not yet audited (next pass)

The workflow was stopped before the **naming-scheme**, **input-validation**, and
deep **trust-integrity** researchers finished. Their charters (cross-filesystem
name safety incl. NTFS/exFAT reserved names + length limits + collisions; the
"validate every input" rule's actual coverage; every place a verification claim
is rendered) should be run as a focused follow-up — ideally on a
higher-core environment where the consensus fan-out can actually complete.

**Naming-scheme cross-filesystem safety — audited directly 2026-07-08; no
shippable bug on the target.** Read `naming.py`, `settings_validation.py`, and
the cyanrip naming contract. Finding: the output-naming path is **sound for the
Linux (ext4/btrfs) target** — cyanrip maps the only path-illegal characters
(`:`→`∶`, value `/`→`∕`), the Settings/config boundary rejects all control
chars incl. NUL and blocks `..` traversal / absolute templates, and any
genuinely-unwritable name fails the rip loudly, not silently. The residual
hazards (Windows/NTFS/exFAT-reserved chars `< > " \ | ? *`, reserved device
names, trailing dots/spaces, case-insensitive collisions) are legal on Linux and
bite **only** on a non-native output volume or after copying the library to
Windows/macOS — a **documented cross-filesystem limitation**, now written up in
`docs/dependency-contracts.md`, *not* a silent-data-loss bug. Re-sanitising
cyanrip's output is deliberately rejected (Critical Rule #3 — the ripper owns
naming; overriding it duplicates cyanrip and breaks the Settings preview↔reality
round-trip). Remaining as a maintainer *feature* call (not a fix): an optional
non-blocking Settings warning on a cross-FS-unsafe template. **Input-validation**
spot-check along the way: `settings_validation.validate_config` is comprehensive
— every `Config` field has a rule, enforced by a completeness meta-test — so the
Settings boundary is solid; the un-run part is the config-file / CLI-arg surfaces.

**Trust-claim-rendering sweep — completed 2026-07-08; 11 copy defects fixed.** Ran
as a two-phase workflow: (1) adversarially re-verify an initial 6-finding audit
against the current code + `verdict.py`, and (2) diverse-lens finders hunting for
*missed* overclaims. All 6 originals CONFIRMED (one upgraded to **trust-critical**:
the User Guide's grey verdict claimed the Copy CRC "proves the disc was read
securely"), and the find-more phase surfaced **5 more** the single-agent pass had
missed — including a stale CTDB parenthetical it had wrongly cleared, two
bit-perfection overclaims ("converges on the bit-perfect result", "the one
calibration that makes rips bit-perfect"), an `_eac_cell` tooltip that told a
present-but-no-match track it "isn't in the AccurateRip database", and stale
`rip_progress` comments/docstring. **Verdict: the trust *engine* is sound** —
`verdict.py`, `track_accuraterip_verified` (confidence ≥ 1), the AR table cells,
disc-info panel, JSON report, and EAC-log renderer (never signs, invents nothing)
all gate "verified"/"bit-perfect" correctly and never count a confidence-0 /
offset-variant / CD-R track as fully verified. The dishonesty was entirely in
**static copy that drifted from the code** (an overclaim + the stale
"experimental" caveats the KDD-16 flip left behind). All 11 fixed with regression
tests (`tests/test_trust_copy_honesty.py` + updated `_eac_cell`/`fidelity_summary`
tests). This closes the trust-integrity render-sweep charter.

---

*Last updated for Platterpus v0.4.24.*
