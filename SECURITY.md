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
  The in-app updater verifies the release's published **SHA-256 checksum**
  (integrity) on every download. **Cryptographic signature verification**
  (Ed25519, via `minisign`) is implemented and verifies **fail-closed** — but it
  is *armed* only once a maintainer-held **offline** signing key is baked into
  the build (`update_signing.PUBLIC_KEY_B64`). Until then the updater is
  SHA-256-only; from the first signed release on, it refuses any update whose
  signature is missing or invalid. The key is held offline and signing happens
  outside CI, so a CI compromise can't forge a signature. See
  [`docs/architecture.md` §6.2 *Release signing*](docs/architecture.md) and the trust-audit notes
  in `docs/`. (The updater does not yet check the SLSA attestation itself.)
- **Workflow supply chain.** CI runs least-privilege (`contents: read`), a
  server-side guard rejects committed audio, every GitHub Action is pinned to a
  full commit SHA, a gating `pip-audit` job scans the dependency graph, and
  Dependabot watches the `pip` and `github-actions` surfaces to keep the pins
  current — **with a deliberate exception for `ruff` and `mypy`**, which are pinned
  to the minor they were measured against because they gate CI, and whose
  `version-update` PRs are therefore ignored (`.github/dependabot.yml`). Security
  advisories for them still come through.
- **Secret scanning over the FULL history** (`gitleaks`, gating). Not a diff scan:
  this repository is public and `git log` is a distribution channel, so a credential
  removed in a later commit is still published and a diff-only scan passes on it.
  Same reasoning the media guard uses for audio.
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

*Last updated for Platterpus v0.6.54.*
