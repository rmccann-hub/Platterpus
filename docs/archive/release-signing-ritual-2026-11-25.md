# Release signing (offline-key minisign): the maintainer ritual, retired

**Retired 2026-11-25** on the owner's word (TASKS R239): update signing was never armed
(PLANNING.md KDD-37, D9, 2026-09-25), so this ritual and the dormant code it armed
(`update_signing.py`, and the gate in `update_install.py`) were removed. The authenticity
check an update gets is the release's build attestation, verified fail-closed in the
updater (`update_attestation.py`; `docs/architecture.md` §6.2 now says so in two lines).

Kept as the record of how signing would have worked, moved unchanged from
`docs/architecture.md` §6.2, where it had been since it absorbed the former
`release-signing.md` on 2026-08-06. Inside it, "below" and "above" mean this text, and
the paths it names were true on 2026-11-25 and may not be now. If signing is ever wanted
again, this is the procedure to start from, and the code is in git at the commit before
the removal.

---

*(Absorbed the former `release-signing.md` on 2026-08-06. It is executed
under release-time pressure, so `CLAUDE.md` → *CI / release* points here directly
rather than relying on a reader finding this section — and **the arming
transition below is the part that is dangerous to half-read**: once a public key
is baked in, a release without a `.minisig` cannot be updated to.)*

Platterpus's in-app updater verifies every download's **SHA-256** (integrity).
This is the second gate — an **Ed25519 signature** that proves *who* published a
release (authenticity), made with a key the maintainer holds **offline**. It's the
maintainer-facing companion to
`src/platterpus/update_signing.py` (the
verify side, removed 2026-11-25) and [PLANNING.md KDD-26](../../PLANNING.md).

**Threat it closes:** SHA-256 alone can't stop a compromised release channel that
swaps *both* the AppImage and its `.sha256`. A signature made with a secret key
that never touches CI (or any online system) can't be forged that way — not even
by a CI compromise. That's why the key is **offline** and signing happens
**outside** the CI release workflow; a key kept in a CI secret would only prove
"built by our CI," which the SLSA build-provenance attestation already does.

> **The app only ever *verifies*.** No secret key is in the repo, the build, or
> the app. The **public** key is safe to commit — that's the whole point.

**Status.** The verify side (parse `.minisig` → Ed25519-verify fail-closed) ships
**dormant**: `update_signing.PUBLIC_KEY_B64` is empty, so the updater is
SHA-256-only and nothing about updates changes. Arming it is the one-time setup
below.

**Decided 2026-09-25: it is never armed** (maintainer, `PLANNING.md` KDD-37, D9).
What that buys is releases that run unattended, and no key that can be lost. The
ritual below is kept so the decision can be reversed without rediscovering it.

**What protects an update instead: the build attestation, checked in the app**
(added the same day, on the maintainer's yes; `src/platterpus/update_attestation.py`).
Until then the updater checked only the download's SHA-256, fetched from the same
release, which proves the file is intact and not who published it. Now, after the
checksum, it fetches `platterpus-x86_64.AppImage.sigstore.json` from the release
and refuses the update unless Sigstore confirms three things: the certificate was
issued by GitHub Actions to `.github/workflows/release.yml` in this repository; the
run was from `main` or from the release's own tag; and the signed statement names
the downloaded file's SHA-256. A missing, unreadable or failing attestation blocks
the install and leaves the current version untouched. Measured on the real v0.6.60
release: the genuine AppImage installs; the same AppImage with one bit changed and
a matching `.sha256` beside it — the swap the checksum alone could not catch — is
refused.

- **The release side.** `release.yml` now attests **before** publishing (it used
  to attest after, deliberately, while nothing read the attestation), then runs
  `scripts/release_attestation.py`, which chooses the bundle with the updater's own
  `select_verified` and stages it as a release asset. So what a release publishes
  is by construction what the updater accepts, and a release it would refuse fails
  in the workflow instead.
- **The shipped bundle's own verifier is checked.** The updater imports `sigstore`
  lazily, so an AppImage built without a working copy would pass `--version` and
  then refuse every update it is ever offered, stranding its users with no in-app
  route off it. Both AppImage workflows therefore extract the build and run
  `scripts/check_bundled_verifier.py` with the **bundled** interpreter against the
  committed v0.6.60 attestation. Run on the real v0.6.60 AppImage, which predates
  the dependency, it fails as it should: *No module named 'sigstore'*.
- **The trust root.** Sigstore's keys are refreshed over TUF, which is how a key
  rotation reaches users without a Platterpus release. A stalled network makes the
  refresh hang for 120 s (measured), so the updater starts it on a daemon thread
  before the download, waits at most `TRUST_REFRESH_WAIT_S` once the download is
  done, and falls back to the cached root, or the one inside the `sigstore`
  package. The log names which one was used.
- **What it does not prove.** Anyone who can push to `main` can run the release
  workflow. The repository rulesets decided on 2026-10-12 (`PLANNING.md` KDD-43) route
  every change through a pull request that passes CI, but require no approval, so the
  check proves a build is traceable to a public commit here, not that anyone reviewed the
  commit. On its own it also did not stop a genuine *older* build being served under
  a newer version; since 2026-10-26 the installer does, below.
- **Never an older version** (the claude-code-skills review of 2026-10-26, item 2.3;
  `src/platterpus/update_version_guard.py`). The update check never offers one, but
  the installer took whatever version it was handed. It now refuses a version lower
  than the one running **twice**: by the version asked for, before anything is
  fetched; and, once the attestation verifies, by the version the file was **built
  as**, read from `src/platterpus/__init__.py` at the commit the signed provenance
  names (`raw.githubusercontent.com`, by full commit, read capped at 64 KiB), which
  must also equal the version asked for. That is derived from the artifact's signed
  evidence rather than the release's label; reading the AppImage's own SquashFS was
  rejected because it needs a new dependency, `unsquashfs` on the host, or running
  the download before it is installed. Fail closed: an attestation with no full
  commit, or a version file that cannot be fetched or read, blocks the install.
  Reinstalling the running version is allowed. Held by `tests/test_update_install.py`
  (a correctly attested 0.6.60 build offered as newer is refused; the same build
  declaring the asked version installs) and `tests/test_update_version_guard.py`.
- **The rollout.** An installed app checks the release it updates *to*, so the
  first release carrying this code is installed by the old updater, unchecked, and
  every update after it is checked.

**One-time setup (do this once, on a trusted machine — never in CI).**

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
   Commit that change. It **arms** the fail-closed gate — read the transition
   immediately below *before* you cut the release.

**The transition (read before arming).** Once a public key is baked in, the
updater **refuses** any release without a valid `.minisig`. So:

- The **first** release built after you bake in the key **must** carry a
  `.minisig`, and **every** release after it must be signed. A release that
  forgets the signature can't be auto-updated *to* (users would see "this release
  has no verifiable signature — refusing to install").
- Users on an **older, pre-signing** release update to the first signed release
  normally (their running app has no key baked in yet, so it's still
  SHA-256-only). It's the *new* app they land on that enforces signatures going
  forward.

**Per-release signing (every release, after CI finishes).** The `release.yml`
workflow builds and uploads the AppImage, its `.sha256`, and the `.zsync`. It
**cannot** sign (the key is offline). After it finishes:

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

> **Since 2026-10-12 this order no longer works as written.** Releases on this
> repository are immutable once published (§6.4 step 1), and `release.yml` publishes
> its draft in the same step that creates it, so there is no point after CI at which
> a `.minisig` can still be attached. Arming signing would first need `release.yml`
> to leave the release as a draft until the signature is uploaded. It is never armed
> (KDD-37, D9), so nothing waits on this.

> **Sanity check the whole chain** on a spare machine: run the *previous*
> released Platterpus, "Check for updates," and confirm it installs the new
> signed release. If you ever need to unpublish, delete the release (§6.4; an
> immutable release's assets cannot be removed one at a time); the updater fails
> closed rather than installing something unverifiable.

**If a release shipped unsigned by mistake.** The updater will refuse it
(fail-closed) once signing is armed — that's working as intended, not a bug.
Before 2026-10-12 the fix was to sign that release's AppImage and upload the
`.minisig` (steps 2–4 above). An immutable release cannot take a new asset, so the
fix is now a new, signed version (§6.4 step 5).

---

*Last updated for Platterpus v0.7.131.*
