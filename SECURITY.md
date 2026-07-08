# Security Policy

Platterpus rips audio CDs and can update itself from GitHub Releases. Two things
matter most for security: the **integrity of the released binary** and the
**safety of your music library** (Platterpus never deletes or overwrites your
existing files — see Critical Rule #8 and the overwrite guards in the code).

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

- **Update authenticity.** The in-app updater verifies the downloaded AppImage
  against the release's published **SHA-256 checksum** (integrity). Cryptographic
  **signature** verification (e.g. minisign) and build-provenance attestation are
  tracked hardening items — see the trust-audit notes in `docs/`.
- **Workflow supply chain.** CI runs least-privilege (`contents: read`), a
  server-side guard rejects committed audio, and Dependabot watches the `pip` and
  `github-actions` dependency surfaces; pinning every action to a commit SHA is a
  tracked follow-up.

## Scope

This policy covers the **Platterpus application**. Vulnerabilities in the
underlying external tools (cyanrip, flac/metaflac, ffmpeg, MusicBrainz Picard)
should be reported to those projects.
