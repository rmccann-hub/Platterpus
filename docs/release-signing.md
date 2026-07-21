# Release signing (offline-key minisign)

Platterpus's in-app updater verifies every download's **SHA-256** (integrity).
This document covers the second gate — an **Ed25519 signature** that proves
*who* published a release (authenticity), made with a key the maintainer holds
**offline**. It's the maintainer-facing companion to
[`../src/platterpus/update_signing.py`](../src/platterpus/update_signing.py)
(the verify side) and [PLANNING.md KDD-26](../PLANNING.md).

**Threat it closes:** SHA-256 alone can't stop a compromised release channel
that swaps *both* the AppImage and its `.sha256`. A signature made with a secret
key that never touches CI (or any online system) can't be forged that way — not
even by a CI compromise. That's why the key is **offline** and signing happens
**outside** the CI release workflow; a key kept in a CI secret would only prove
"built by our CI," which the SLSA build-provenance attestation already does.

> **The app only ever *verifies*.** No secret key is in the repo, the build, or
> the app. The **public** key is safe to commit — that's the whole point.

---

## Status

The verify side (parse `.minisig` → Ed25519-verify fail-closed) ships **dormant**:
`update_signing.PUBLIC_KEY_B64` is empty, so the updater is SHA-256-only and
nothing about updates changes. Arming it is the one-time setup below.

---

## One-time setup (do this once, on a trusted machine — never in CI)

1. **Install minisign** (`sudo dnf install minisign` / `sudo apt install
   minisign`, or from <https://jedisct1.github.io/minisign/>).

2. **Generate the keypair** and store the **secret** key somewhere offline and
   backed up (a password manager, an encrypted USB key — *not* the repo, *not* a
   CI secret):

   ```bash
   minisign -G -p minisign.pub -s minisign.key
   ```

   You'll set a password on the secret key; you'll enter it each time you sign.

3. **Bake in the public key.** Open `minisign.pub` — it has two lines:

   ```
   untrusted comment: minisign public key ABC123…
   RWQ…the base64…=
   ```

   Copy the **second line** (the base64) into
   `src/platterpus/update_signing.py`:

   ```python
   PUBLIC_KEY_B64: str = "RWQ…the base64…="
   ```

   Commit that change. It **arms** the fail-closed gate — see the transition
   note below before you cut the release.

---

## The transition (read before arming)

Once a public key is baked in, the updater **refuses** any release without a
valid `.minisig`. So:

- The **first** release built after you bake in the key **must** carry a
  `.minisig`, and **every** release after it must be signed. A release that
  forgets the signature can't be auto-updated *to* (users would see "this
  release has no verifiable signature — refusing to install").
- Users on an **older, pre-signing** release update to the first signed release
  normally (their running app has no key baked in yet, so it's still
  SHA-256-only). It's the *new* app they land on that enforces signatures going
  forward.

---

## Per-release signing (every release, after CI finishes)

The `release.yml` workflow builds and uploads the AppImage, its `.sha256`, and
the `.zsync`. It **cannot** sign (the key is offline). After it finishes:

1. **Download** the released AppImage (the exact bytes CI published):

   ```bash
   curl -fLO https://github.com/rmccann-hub/Platterpus/releases/download/vX.Y.Z/platterpus-x86_64.AppImage
   ```

2. **Sign it** (prehashed — `-H` — is what the verifier expects for a file this
   large, and is faster):

   ```bash
   minisign -S -H -s minisign.key -m platterpus-x86_64.AppImage
   ```

   This writes `platterpus-x86_64.AppImage.minisig`.

3. **Verify your own signature** before uploading (catches a wrong key/typo):

   ```bash
   minisign -V -p minisign.pub -m platterpus-x86_64.AppImage
   ```

   It should print `Signature and comment signature verified`.

4. **Upload `platterpus-x86_64.AppImage.minisig`** to the GitHub Release as an
   asset, next to the AppImage. That's the file the updater fetches
   (`<AppImage>.minisig`) and checks.

> **Sanity check the whole chain** on a spare machine: run the *previous*
> released Platterpus, "Check for updates," and confirm it installs the new
> signed release. If you ever need to unpublish, delete the release assets; the
> updater fails closed rather than installing something unverifiable.

---

## If a release shipped unsigned by mistake

The updater will refuse it (fail-closed) once signing is armed — that's working
as intended, not a bug. Fix it by signing that release's AppImage and uploading
the `.minisig` (steps 2–4 above); no rebuild needed, since you sign the exact
published bytes.

---

*Last updated for Platterpus v0.5.5.*
