# Security Policy

Platterpus rips audio CDs and can update itself from GitHub Releases. Two things
matter most for security: the **integrity of the released binary** and the
**safety of your music library** (Platterpus does not delete or overwrite your
existing files without asking — see the overwrite guards shipped in
v0.4.22/v0.4.23: the unknown-disc auto-suffix and the known-disc re-rip
Replace / Rip-to-new-folder / Cancel confirmation, hardened in v0.6.24 after
the known-disc guard predicted the destination folder from an incomplete
character table, missed a real collision, and let a finished rip be
overwritten — it now resolves that prediction against what is on disk. All
recorded in `CHANGELOG.md`, with the earlier review in the 2026-07-08 trust
audit).

## Reporting a vulnerability

Please report security issues **privately**, not in a public issue:

- **Preferred:** GitHub private vulnerability reporting — the repository's
  **Security** tab → **Report a vulnerability**
  (<https://github.com/rmccann-hub/Platterpus/security/advisories/new>).

We'll acknowledge the report, work with you on a fix, and coordinate disclosure.
Please allow a reasonable window before any public disclosure.

## Supported versions

Platterpus is pre-1.0. Only the latest released `v0.6.x` is supported — please
reproduce on the newest release before reporting.

## Known hardening items (tracked, not secret)

- **Update authenticity.** Every released AppImage carries a **build-provenance
  attestation** (SLSA, via GitHub OIDC + Sigstore — no maintainer-held key), so
  you can prove a download really came from this repo's release pipeline:
  `gh attestation verify platterpus-x86_64.AppImage --repo rmccann-hub/Platterpus`.
  That form asks GitHub for the attestation, so it needs `gh auth login` first,
  and without a login it fails with an authentication error rather than a
  verification result. To check with no login, download the release's
  `platterpus-x86_64.AppImage.sigstore.json` beside the AppImage and run the form
  `install.sh` uses (`gh` 2.51.0 or later):
  `gh attestation verify platterpus-x86_64.AppImage --repo rmccann-hub/Platterpus --bundle platterpus-x86_64.AppImage.sigstore.json --signer-workflow rmccann-hub/Platterpus/.github/workflows/release.yml`.
  The in-app updater verifies the release's published **SHA-256 checksum**
  (integrity), and **from the release after v0.6.60 it also verifies that
  attestation, fail-closed** (`src/platterpus/update_attestation.py`): an update
  installs only if Sigstore confirms it was built by `.github/workflows/release.yml`
  in this repository, from `main` or from the release's own tag, and the signed
  statement names the exact file downloaded. A missing or failing attestation
  blocks the install and leaves the current version untouched. The one-line
  installer (`install.sh`, since 2026-09-28) makes the same two checks on the
  AppImage it downloads, the attestation only when an installed GitHub CLI can
  check it (`gh` 2.51.0 or later), and refuses a file that fails either. **What that does
  not cover:** anyone who can push to `main` can run the release workflow, and
  `main` is not branch-protected, so the attestation proves a build is traceable to
  a public commit here, not that the commit was reviewed. **Offline-key signing**
  (Ed25519, via `minisign`) is implemented but will not be armed (maintainer
  decision, 2026-09-25, `PLANNING.md` KDD-37); see
  [`docs/architecture.md` §6.2 *Release signing*](docs/architecture.md).
- **Workflow supply chain.** CI runs least-privilege (`contents: read`), a
  server-side guard rejects committed audio, every GitHub Action is pinned to a
  full commit SHA, a gating `pip-audit` job scans the dependency graph, and
  Dependabot watches the `pip` and `github-actions` surfaces to keep the pins
  current — **with a deliberate exception for `ruff` and `mypy`**, which are pinned
  to the minor they were measured against because they gate CI, and whose
  `version-update` PRs are therefore ignored (`.github/dependabot.yml`). Security
  advisories for them still come through.
- **Secret scanning** (`gitleaks`, gating), over the full history on every run since
  2026-10-05. The job installs the gitleaks CLI at a pinned version, checks the release
  tarball against its published sha256, and scans every commit reachable from the
  checked-out head with merge commits diffed against each parent (`--log-opts="-m
  HEAD"`). A scan that read too little would also print "no leaks found", so the job
  refuses three ways: a shallow clone, fewer than an absolute minimum of commits, and
  fewer than 90 % of the commits reachable from the head. The full history is what
  matters: this repository is public and `git log` is a distribution channel, so a
  credential removed in a later commit is still published. Same reasoning the media
  guard uses for audio. *History:* until 2026-10-05 the job ran
  `gitleaks/gitleaks-action`, which scans a range it builds itself, `--no-merges
  --first-parent`, so a push to `main` arriving as a merge commit scanned nothing (the
  push run for `a930411b` logged *"0 commits scanned"*). That fix was amendment A12,
  approved 2026-09-28 and held under C3 of the operator's seam-automation proposal
  until the maintainer lifted C3 for it on 2026-10-05 (`PLANNING.md` KDD-39, KDD-41).
  Until then the scan was done by hand: on 2026-09-28, gitleaks 8.24.3 over every
  commit reachable from `main`, merge commits included (1,454 commits), found nothing;
  on 2026-10-05 the new job's own step, run locally, scanned 1,636 of 1,692 and found
  nothing.
- **A CycloneDX SBOM of what actually ships** (`sbom`, gating), generated on every
  push rather than only at release, with a floor that refuses an SBOM listing fewer
  than ten components — a generated artifact describing an empty room is the shape
  this repo refuses everywhere.

  *The two entries above were added to this section on 2026-09-13. Both gates had
  been running and gating for weeks; the security policy simply did not name them —
  the two most security-relevant additions since the section was written, missing
  from the document whose job is to describe them.*

## Scope

This policy covers the **Platterpus application**. Vulnerabilities in the
underlying external tools (cyanrip, flac/metaflac, ffmpeg, MusicBrainz Picard)
should be reported to those projects.

---

*Last updated for Platterpus v0.6.65.*
