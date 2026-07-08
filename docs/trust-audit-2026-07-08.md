# Trust & quality deep audit (2026-07-08)

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
| 1 | **trust-critical** | **In-app updater verifies integrity (SHA-256) but not authenticity.** It downloads, `chmod +x`, and swaps in a binary with no signature check; a compromised release channel or MITM able to swap both the AppImage and its `.sha256` would be trusted. | Real signing (minisign/ed25519) needs a **new crypto dependency** (CLAUDE.md "must ask") **and a signing key the maintainer holds** (infra decision). Safe interim, no new dep/secret: add `actions/attest-build-provenance` in `release.yml`, and make the updater fail-closed on a *present-but-invalid* signature so it's ready when a key exists. `SECURITY.md` documents the current integrity-only boundary honestly. |
| 2/6 | high | **GitHub Actions pinned to mutable tags, not commit SHAs** — the release pipeline that builds the auto-updated binary is supply-chain-exposed. | Pinning `ci.yml` is self-validating; pinning `release.yml`/`publish-pypi.yml`/`appimage.yml` is only exercised on the next dispatch (can't verify here) and a wrong SHA breaks releases — so it's a careful dedicated pass. Dependabot (`github-actions`, added now) will drive the pins via reviewed PRs in the meantime. |
| 4 | medium | **AppImage bundles an unpinned, unhashed dependency graph; build is non-reproducible.** | Touches `build_appimage.sh`/`release.yml` which can't be built+verified in this sandbox; risk of breaking releases. Next: `pip-compile --generate-hashes` + `--require-hashes` + `SOURCE_DATE_EPOCH`, validated on a real build. |
| 3 | medium | **Type hints are mandated but no static type checker runs** — the annotations are unverified. | Adding `mypy`/`basedpyright` likely surfaces many findings; do it as its own ratcheting pass (non-strict baseline → strict on `adapters`/`parsers`/`workers` first), mirroring the coverage ratchet. |
| 8b | medium | **No `pip-audit` gate.** | Pairs with the mypy/typecheck job; add as a (initially non-gating) CI job so a new CVE in an unmaintained dep like `musicbrainzngs` is surfaced without red-flaking every PR. |
| 11 | medium | **Test-efficacy guardrails are manual-only** (mutation testing; "every bug gets a regression test" has no CI signal). | Add a scheduled (weekly, non-blocking) `mutmut` workflow over `parsers/`, `verdict.py`, `ctdb/crc.py`, and a warn-only "src changed without tests" PR check mirroring the changelog gate. |
| 9b | medium | **Known-disc re-rip overwrite.** The unknown-disc case is fixed; re-ripping an *identified* album to the same folder still overwrites without asking. | Usually intentional, so it wants a confirm dialog (GUI-thread, needs hardware/UX verification), not silent auto-suffix. |

---

## Not yet audited (next pass)

The workflow was stopped before the **naming-scheme**, **input-validation**, and
deep **trust-integrity** researchers finished. Their charters (cross-filesystem
name safety incl. NTFS/exFAT reserved names + length limits + collisions; the
"validate every input" rule's actual coverage; every place a verification claim
is rendered) should be run as a focused follow-up — ideally on a
higher-core environment where the consensus fan-out can actually complete.

---

*Last updated for Platterpus v0.4.22.*
