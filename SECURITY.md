# Security Policy

Platterpus rips audio CDs and can update itself from GitHub Releases. Two things
matter most for security: the **integrity of the released binary** and the
**safety of your music library** (Platterpus never deletes or overwrites your
existing files — see the overwrite guards shipped in v0.4.22/v0.4.23: the
unknown-disc auto-suffix and the known-disc re-rip Replace / Rip-to-new-folder /
Cancel confirmation, both recorded in `CHANGELOG.md` and the 2026-07-08 trust
audit).

## Reporting a vulnerability

Please report security issues **privately**, not in a public issue:

- **Preferred:** GitHub private vulnerability reporting — the repository's
  **Security** tab → **Report a vulnerability**
  (<https://github.com/rmccann-hub/Platterpus/security/advisories/new>).

We'll acknowledge the report, work with you on a fix, and coordinate disclosure.
Please allow a reasonable window before any public disclosure.

## Supported versions

Platterpus is pre-1.0. Only the latest released `v0.4.x` is supported — please
reproduce on the newest release before reporting.

## Known hardening items (tracked, not secret)

- **Update authenticity.** Every released AppImage carries a **build-provenance
  attestation** (SLSA, via GitHub OIDC + Sigstore — no maintainer-held key), so
  you can prove a download really came from this repo's release pipeline:
  `gh attestation verify platterpus-x86_64.AppImage --repo rmccann-hub/Platterpus`.
  The in-app updater itself still verifies only the release's published
  **SHA-256 checksum** (integrity) — it does not yet check the attestation, and
  cryptographic **signature** verification (e.g. minisign) is still a tracked
  hardening item (it needs a maintainer-held signing key). See the trust-audit
  notes in `docs/`.
- **Workflow supply chain.** CI runs least-privilege (`contents: read`), a
  server-side guard rejects committed audio, every GitHub Action is pinned to a
  full commit SHA, a gating `pip-audit` job scans the dependency graph, and
  Dependabot watches the `pip` and `github-actions` surfaces to keep the pins
  current.

## Scope

This policy covers the **Platterpus application**. Vulnerabilities in the
underlying external tools (cyanrip, flac/metaflac, ffmpeg, MusicBrainz Picard)
should be reported to those projects.

---

*Last updated for Platterpus v0.4.24.*
