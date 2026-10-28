# Dependencies

All dependencies, with last upstream release date and replacement plan. Reviewed on the cadence below.

The tables below are hand-kept and carry what code cannot know: licences, upstream release dates, status and replacement plans. **The complete map of everything Platterpus has or relies on** — languages, packages, external programs, the ripper and its container, services, CI — is generated from the code: see [*The full map*](#the-full-map-machine-readable-bomcdxjson) below and its machine-readable copy, `bom.cdx.json`.

## Python packages (bundled in the AppImage)

The ranges below are the decision; **the exact versions the AppImage bundles are fixed by `build/python-appimage/requirements.lock`** (committed 2026-10-27), which `build/lock-requirements.sh` resolves from `build/python-appimage/requirements.txt` for the CPython the AppImage bundles (3.12) on PySide6's glibc floor (manylinux_2_34), with the sha256 of every file. The build downloads that closure with `pip --require-hashes` and installs offline from it, and refuses to run without the lock. On 2026-10-27 it pinned PySide6 6.11.3, cryptography 50.0.2, sigstore 4.5.1, numpy 2.4.6, musicbrainzngs 0.7.1 and tomli-w 1.2.0, plus 30 transitive packages. `tests/test_dependency_locks.py` fails when a lock falls outside its ranges. **Every lock is reproducible:** its header records the uv version and the `--exclude-newer` date it was resolved with (uv only considers files PyPI received before that date), and `bash build/lock-requirements.sh --check` regenerates every lock from those two fields and diffs it against the committed file, so a hand edit, a deleted package included, fails ci.yml's `lock-check` job. The generator's default date is 00:00 UTC seven days back, Dependabot's cooldown. **The locks are kept current by a job, not by Dependabot**, which reads `pyproject.toml` and never the locks: `dependencies.yml`'s `relock` job regenerates them every Monday with that seven-day date and opens a pull request when a pin or a hash changed, which a session then carries through CI.

| Name | Pinned version | Last upstream release | License | Status | Planned replacement |
|---|---|---|---|---|---|
| PySide6 | `>=6.11.1,<6.12` (current: 6.11.1; CI resolves 6.11.2) — **minor-pinned 2026-08-18**, was `>=6.7,<7`. 6.11.2 stopped resolving `QKeySequence.StandardKey.Quit` and `.Preferences`, so the Quit and Settings menu items shipped with **no keyboard shortcut** — a WCAG 2.1.1 regression from somebody else's release with no change to our code. Reproduced on one machine, same `QT_QPA_PLATFORM=offscreen`, only the wheel changed. `main_window.standard_shortcut` now checks Qt's answer instead of trusting it, and the suite is run against **both** wheels before a push touching Qt behaviour. The bound is the MINOR, not the patch: 6.11.x still flows (Qt's security fixes with it, and 6.11.2 is handled correctly and proven green), while a minor bump becomes a deliberate commit that re-runs the gate. `build/python-appimage/requirements.txt` expresses the same range as `~=6.11.1` — that file is what SHIPS — and `tests/test_gating_tools_are_pinned.py` fails if the two disagree. Same class as the `cryptography` ceiling incident below. | 2026-10-08 (6.12.0, outside the pin; 6.11.2 was 2026-08-18, 6.11.1 2026-05-13 — PyPI, read 2026-10-19) | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | Active | — |
| musicbrainzngs | `==0.7.1` | 2020-01-11 | BSD-2-Clause (one file ISC) | Unmaintained (>12mo) | direct `requests` against `https://musicbrainz.org/ws/2/` via `MusicBrainzClient.RequestsJsonImpl` |
| tomli-w | `>=1.0,<2` (current: 1.2.0) | 2025-01-15 | MIT | Active | — (stdlib `tomllib` is read-only, `tomli-w` is the canonical writer) |
| cryptography | `>=50.0.0,<51` (pyproject); AppImage bundles `~=50.0`; exact version fixed by `build/python-appimage/requirements.lock` (50.0.2 on 2026-10-27), hash-verified at build time; the lock is committed and the build refuses to run without it (it was an uncommitted opt-in until then, so every build installed online by range) | (per PyPI) | Apache-2.0 OR BSD-3-Clause | Active | — (Ed25519 verification of a release's minisign signature — the in-app updater's authenticity gate, `src/platterpus/update_signing.py`. Verify-only; no secret key in the app. The BLAKE2b prehash uses stdlib `hashlib`, so only the Ed25519 primitive is needed — stable since cryptography 2.6. **Floor is the CVE-2026-69247 fix (50.0.0)**, raised from the GHSA-537c-gmf6-5ccf floor (48.0.1) on 2026-08-04 — 49.0.0 carries CVE-2026-69247 and the old `<50` ceiling *excluded the only fix*, so `pip-audit` resolved the vulnerable top of the range and turned CI red with no change to our code. Keep the floor on the latest patched release, and when raising a floor check the CEILING admits it. Verified against 50.0.0 before the bump: the Ed25519 sign/verify path, raw-public-bytes round-trip, tampered-message rejection, and `tests/test_update_signing.py` + `tests/test_update_install.py` (32 tests) all pass.) |
| sigstore | `>=4.5.0,<4.6` (pyproject) and `~=4.5.0` (AppImage) — **minor-pinned**, like PySide6 (current: 4.5.0) | 2026-07-28 (4.5.0) | Apache-2.0 | Active (Sigstore project) | — (Verifies each release's build-provenance attestation before an in-app update installs: `src/platterpus/update_attestation.py`, the only module that imports it. **Added 2026-09-25 with the maintainer's explicit yes**, after D9 (never arm signing) left the updater checking only a SHA-256 fetched from the same release. The reference Python implementation of Sigstore verification; writing our own would mean certificate-chain, transparency-log and DSSE verification by hand. **Weight, measured:** 31 wheels, about 14 MB, for Python 3.11 and 3.14 alike; the transitive set is `cryptography` (already here), `pydantic`/`pydantic-core`, `tuf`, `securesystemslib`, `rfc3161-client`, `rfc8785`, `pyOpenSSL`, `pyasn1`, `pyjwt`, `id`, `requests`/`urllib3`, `rich`, `platformdirs`, `sigstore-models`, `sigstore-rekor-types` and their small helpers. `pip-audit` clean over the tree (2026-09-25). Imports in about 0.7 s, so it is imported only while an update installs. **Why minor-pinned:** the updater refuses any update this check cannot pass, so a verifier API change would not redden a build, it would silently stop every user's updates. **Network:** refreshes Sigstore's trust root over TUF (`tuf-repo-cdn.sigstore.dev`), which is how a key rotation reaches users without a release; on failure it uses the cached root, or the one inside the package. Bump with `tests/test_update_attestation.py`, which verifies the real v0.6.60 bundle offline.) |
| numpy | `>=2.4.6,<2.5` (pyproject) and `~=2.4.6` (AppImage) — **minor-pinned**, like PySide6 (current: 2.4.6) | 2026-05-18 (2.4.6; PyPI, read 2026-10-26). 2.5.4 (2026-10-10) is newer and **cannot be used**: 2.5 requires Python >=3.12 and `requires-python` is `>=3.11` | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 (its PyPI licence expression; the wheel bundles OpenBLAS) | Active | — (Locates the samples a rip differs from a CTDB entry in, "differs in 16 samples @04:04:68,..." (TASKS R43): Reed-Solomon syndromes over GF(2^16), vectorised over the 11,760 interleaved columns. `src/platterpus/ctdb/syndromes.py` and `ctdb/verify_parity.py` are the only importers, reached only after `deps/registry.py` says numpy is installed; without it the localisation reads "not determined: numpy is not installed". **Added on the owner's word of 2026-10-26, 02:19 UTC: *"numpy; record what it adds to the download."*** **What it adds, measured 2026-10-26** (pip 26.2.2 `download --only-binary=:all: --platform manylinux_2_28_x86_64`; Python's `zipfile` to unpack; `du -sb`): the wheel for the AppImage's CPython 3.12 is **16,645,538 bytes (16.6 MB)** (`numpy-2.4.6-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl`, sha256 `90f98496…6d853`; cp311 16.9 MB, cp314 16.6 MB) and **56,537,090 bytes (56.5 MB) installed**: `numpy/` 27.9 MB, `numpy.libs/` (OpenBLAS) 28.5 MB, 6.6 MB of that its own test suite. **In the AppImage, an estimated +13.8 MB (about +5.4 %)** on the 256,027,128-byte (244.2 MiB) 0.7.112 AppImage. The estimate, and why it is one: `bash build/build_appimage.sh` cannot run in the cloud session (python-appimage fetches its base image from `api.github.com/repos/niess/python-appimage`, which the session's proxy refuses with 403), so no before/after build exists. Instead the shipped 0.7.112 AppImage was read: its squashfs superblock says zstd, 128 KiB blocks; compressing every file of its extracted tree the same way (`zstandard` 0.25, each 128 KiB block on its own, tails packed as fragments) gave 270.7 MB at level 15 and 267.6 MB at level 19 against the real 255.1 MB, and the same method on the unpacked numpy gave 14.67 MB and 14.50 MB, which scaled by the same ratios is 13.8 MB both ways. **Measured on the first release built with it, 0.7.113 (2026-10-26):** its AppImage is **274,356,728 bytes**, **+18,329,600 bytes (+18.3 MB, +7.2 %)** on 0.7.112's 256,027,128 (both read from the GitHub releases' asset sizes). That difference is the whole release's, not numpy's alone; numpy accounts for most of it, and the estimate above (+13.8 MB) was low by about 4.5 MB. **glibc:** numpy 2.4's Linux wheels are manylinux_2_28 (glibc 2.28), below PySide6 6.11's manylinux_2_34, so the AppImage's floor does not move. **No transitive dependencies.** **Why minor-pinned:** not a gate tool, but its answer is a claim about the user's audio, and numpy has changed integer rules across minors before (NEP 50, 2.0); a drift would name the wrong samples rather than fail. `tests/test_gating_tools_are_pinned.py` holds the two pins equal. Bump with `tests/test_ctdb_syndromes.py` and `tests/test_ctdb_localise.py`, which hold the arithmetic to an independent reference.) |

## Python packages (dev / build only — not bundled)

| Name | Pinned version | Last upstream release | License | Status | Planned replacement |
|---|---|---|---|---|---|
| python-appimage | **`>=1.4.6,<1.5`** — pyproject's new `appimage` extra (2026-10-27; it was `>=1.4,<2` written in `release.yml`, `appimage.yml` and `build_appimage.sh`). Both workflows install it at an exact version with hashes from `build/locks/release.lock` (1.4.6 on 2026-10-27) | 2026-07-23 (1.4.6; PyPI, read 2026-10-19) | GPL-3.0 (package itself); MIT for files under `python_appimage/data` | Active | `appimage-builder` only if `python-appimage` cannot express a required build step (CLAUDE.md Critical Rule #2). The recipe must avoid `appimage-builder`-specific features so swapping back is cheap. |
| build | **`>=1.6.1,<1.7`** (pyproject's `publish` extra, 2026-10-27; `release.yml`, `appimage.yml` and `build_appimage.sh` said `>=1,<2` until the review's follow-up). Installed at an exact version with hashes: `build/locks/release.lock` for the AppImage build, `build/locks/publish.lock` for the PyPI publish (1.6.1 in both on 2026-10-27) | 2026-09-10 (1.6.1; PyPI, read 2026-10-27) | MIT | Active | — (PEP 517 build frontend; used by `build/build_appimage.sh`, and by `publish-pypi.yml` to build the wheel and sdist it uploads. That job holds `id-token: write`, so its copy is minor-pinned like ruff and mypy (Critical rule #11) and read from `pyproject.toml` rather than restated: the 2026-10-27 review, item 2.1, which released the configuration audit's amendment A2.) |
| pytest | `>=8,<10` | (per PyPI at first install) | MIT | Active | — |
| twine | `>=7.0.0,<7.1` (pyproject's `publish` extra; **pinned 2026-10-27**, unpinned before). `publish-pypi.yml` installs it at an exact version with hashes from `build/locks/publish.lock` (7.0.0 on 2026-10-27), since the review's follow-up of the same day | 2026-07-27 (7.0.0; PyPI, read 2026-10-27) | Apache-2.0 | Active | — (Runs `twine check` on every wheel and sdist before the PyPI upload, so a release depends on it. The upload itself goes through `pypa/gh-action-pypi-publish`. Pinned with `build` by the 2026-10-27 review, item 2.1, which is the configuration audit's amendment A2 (2026-09-28), until then approved and held under the seam-automation proposal's C3. Minor-pinned in `pyproject.toml`, never restated in the workflow; `tests/test_gating_tools_are_pinned.py` refuses a literal version in `publish-pypi.yml`. A minor range still installs whatever patch release PyPI serves, so since the review's follow-up the job installs the hashed lock resolved from that range instead, and `tests/test_dependency_locks.py` holds the lock inside it. Row added 2026-09-28: until then this file did not name it.) |
| pip-audit | **`>=2.10.1,<2.11`** — pinned to the minor, deliberately, in `pyproject.toml`'s `dev` extra. The `ci.yml` job installs it at an exact version with hashes from `build/locks/audit.lock` (2.10.1 on 2026-10-27), resolved from that line, and audits every committed lock with `--disable-pip` rather than an environment installed by range (both since the review's follow-up, 2026-10-27). `release.yml` requires the job to have passed on the commit it releases | 2.10.1 (2026-06-10; the version `main`'s CI ran in run 40425541839, 2026-10-27) | Apache-2.0 | Active (PyPA) | — (The gating `pip-audit` job: it audits the resolved runtime graph and fails on a known vulnerability. A tool that gates CI, so Critical rule #11 applies to it: until 2026-10-27 the job installed it unversioned, and every run took the newest release. Pinned on the 2026-10-27 external review's item 2.2, which is the pip-audit half of amendment A5 (2026-09-28); `tests/test_gating_tools_are_pinned.py` now names it a gating tool and refuses an unversioned install in `ci.yml`. The other half of A5, `cyclonedx-bom` in the `sbom` job, is installed from a hashed lock since the follow-up review of 2026-10-27 (its row), and still not pinned to the minor in `ci.yml`. Row added 2026-09-28.) |
| cyclonedx-bom | `>=7,<8` — pyproject's `sbom` extra since 2026-10-27 (it was written in `ci.yml`). The `sbom` job installs it at an exact version with hashes from `build/locks/sbom.lock` (7.5.0 on 2026-10-27), with the runtime dependencies and the build backend, then the project offline; it ran `pip install --upgrade pip` and the range unhashed until the follow-up review of 2026-10-27, item 5. Still a major range: pinning it to the minor also needs it in `.github/dependabot.yml`'s `pinned-minor` group (`tests/test_dependabot_holds_the_pins.py`) | 7.5.0 (2026-09-29; PyPI, read 2026-10-19) | Apache-2.0 | Active (CycloneDX) | — (Generates the `sbom` job's CycloneDX file with `cyclonedx-py environment`. It inventories the environment it runs in, so the SBOM lists the generator's own packages too; building it from only what ships is amendment A14 (2026-09-28), approved and held under C3. Row added 2026-09-28.) |
| cyclonedx-python-lib (`[json-validation]` extra) | `>=11.12,<12` (dev extra in `pyproject.toml`) | 11.12.0 (2026-08-13) | Apache-2.0 | Active (CycloneDX) | — (dev/test only. Validates `bom.cdx.json` against the CycloneDX 1.7 JSON schema in strict mode, offline: the library bundles the schema and the SPDX and JSF schemas it references. Its `json-validation` extra brings `jsonschema` and `referencing`. Approved by the maintainer 2026-10-05, `PLANNING.md` KDD-41, C7. Row added 2026-10-05.) |
| gitleaks | **8.24.3**, pinned in `ci.yml` (`GITLEAKS_VERSION`) with the release tarball's sha256 (`GITLEAKS_SHA256`), checked before it runs; the same binary the action ran, read from `main`'s CI log on 2026-09-28 | (not checked from here) | MIT (the binary; the licence ships in its release tarball) | Active | — (Not a Python package: a Go binary the `gitleaks` CI job installs and runs. Since 2026-10-05 the job pins it itself instead of using `gitleaks/gitleaks-action`, so a bump is a deliberate change to the two env values, and a substituted download fails the checksum. What the job scans is recorded in `SECURITY.md`: the full history, merges included, with floors; that was amendment A12, released from C3 on 2026-10-05, `PLANNING.md` KDD-41. Row added 2026-09-28.) |
| uv | **`0.13.5`**, exact: not installed by any job that installs from a lock. The maintainer runs it to regenerate the locks (`bash build/lock-requirements.sh`, which records the uv version and the `--exclude-newer` date in each lock's header), and CI runs it through `astral-sh/setup-uv` in `dependencies.yml` and in `ci.yml`'s `lock-check` job, which regenerates every lock with the recorded version and date and diffs it. A byte-for-byte check needs the same uv, so every `setup-uv` step pins the version the headers record, and `tests/test_dependency_locks.py` holds them equal: move the pin and regenerate in one commit. The locks moved from 0.11.32 to 0.13.5 on 2026-10-27 with identical bodies | (per PyPI; 0.13.5 used 2026-10-27, resolved by git ls-remote 2026-10-26) | Apache-2.0 OR MIT | Active (Astral) | — (Resolves the hashed locks: `uv pip compile --generate-hashes` resolves for a Python and platform other than the one it runs on, which the AppImage lock needs (CPython 3.12 on manylinux_2_34, from a 3.11 host), and records the sha256 of every file PyPI publishes for each pinned version. pip's own resolver cannot target another interpreter for a full closure. Every job installs the locks with pip. Row added 2026-10-27.) |
| ruff | **`>=0.15.22,<0.16`** — pinned to the minor, deliberately | (per PyPI at first install) | MIT | Active | **A tool that gates CI must not float** (CLAUDE.md Critical rule #11): `ruff format` changes what it accepts between minors, so a routine upstream release turns CI red with no change to our code and reads as a code problem. Bumping is a deliberate commit that re-runs the gate. CI never restates this spec: since 2026-10-27 the `lint`, `typecheck` and `test` jobs install `build/locks/ci.lock`, pyproject's ranges resolved to exact versions with hashes (ruff 0.15.22, mypy 2.3.1 that day), and `tests/test_dependency_locks.py` holds the lock inside the ranges (before, the lint job read this line out of pyproject at run time), and `.github/dependabot.yml` ignores version-updates for it — a pin has to bind against whatever is allowed to change it. |
| pytest-cov | `>=5` | (per PyPI at first install) | MIT | Active | — (dev/test only; CI runs branch coverage with `--cov-fail-under=93` (ratchets up; 91 until 2026-10-27, raised to the measured 93.28% rounded down). See [docs/testing.md](docs/testing.md).) |
| pytest-xdist | `>=3.6,<4` | 3.8.0 (2025-07-01) | MIT | Active | — (dev/test only; approved by the maintainer 2026-09-26 to run the suite in parallel. CI and `scripts/check.py` pass `-n auto`; a bare local `pytest` stays serial. Measured on 4 CPUs: 2m08s against 7m22s serial, before the Phase 1 fixes. The session-finish hooks are controller-only under it; see `tests/conftest.py::is_xdist_worker`.) |
| hypothesis | `>=6` | (per PyPI at first install) | MPL-2.0 | Active | — (dev/test only; property-based tests in `tests/test_parsers_property.py`. MPL-2.0 is fine — test-time tool, not linked/distributed.) |
| ~~mutmut~~ | **not used since 2026-09-05** | — | BSD-3-Clause | **Retired** | Replaced by **`scripts/mutation_sweep.py`, ours**, which `.github/workflows/mutation.yml` runs weekly (non-gating). The reason is Critical rule #11 applied to a *signal* rather than a gate: swapping one external mutator for another keeps the failure mode that lost seven consecutive green-but-empty runs. The sweep has no dependency beyond pytest and carries a floor on mutants actually **checked**, so a sweep that measured nothing cannot read as a clean one. |
| mypy | **`>=2.3,<2.4`** — pinned to the minor, deliberately | (per PyPI at first install) | MIT | Active | — (dev/test only; static type-checking. CI `typecheck` job runs `mypy` on every push/PR. **Strict def-typing (`disallow_untyped_defs`/`disallow_incomplete_defs`) enforced across the entire package since 2026-07-19/20** — the Qt UI mixin layer, the last hold-out, was brought in via the `MainWindowShared` typing seam (`docs/architecture.md` §3.6). **Correction 2026-09-13: "no per-module exclusions remain" was true of *def-typing* and false as written** — `[[tool.mypy.overrides]]` carries six live modules with `disallow_any_generics = false` (`rip_report`, `rip_compare`, `adapters.musicbrainz_client`, `ui.main_window_shared`, `ui.main_window`, `workers.rip_worker`). Critical rule #10 calls that "a shrinking per-module opt-out list"; retire one per commit, never add one. Pin rationale as for ruff. Approved as a new dev dep 2026-07-08.) |
| actionlint-py | **`>=1.7.12,<1.8`** — pyproject's `ci-lint` extra, read by `ci.yml`'s `workflow-lint` job, which installs it by that range: it is **not** in `build/locks/ci-lint.lock`, because it publishes only an sdist (1.7.12.25, read 2026-10-27) whose build downloads the actionlint binary from GitHub and checks it against checksums the sdist carries, and the locks take wheels only (TASKS R91) | 2026-09-22 (1.7.12.25; PyPI, read 2026-10-27) | MIT | Active | — (Wraps the actionlint binary. Lints every workflow file's syntax and expressions. **Added 2026-10-27 on the owner's word** (the review of that day, item 2.5). Not a required check yet.) |
| zizmor | **`>=1.31.1,<1.32`** — pyproject's `ci-lint` extra; `ci.yml`'s `workflow-lint` job installs it at an exact version with hashes from `build/locks/ci-lint.lock` (1.31.1 on 2026-10-27) | 2026-10-15 (1.31.1; PyPI, read 2026-10-27) | MIT | Active | — (Audits the workflows for security problems: cache poisoning, persisted credentials, template injection, unpinned actions. Runs `--offline`, so it never calls GitHub's API. **Added 2026-10-27 on the owner's word** (item 2.5); its 17 findings of that morning were fixed before the job was added, and it reports none. Not a required check yet.) |
| shellcheck-py | **`>=0.11.0.1,<0.12`** — pyproject's `ci-lint` extra; `ci.yml`'s `shellcheck` and `workflow-lint` jobs install it at an exact version with hashes from `build/locks/ci-lint.lock` (0.11.0.1 on 2026-10-27) | 2025-08-09 (0.11.0.1; PyPI, read 2026-10-27) | MIT (the wrapper); ShellCheck itself is GPL-3.0, run as a separate program and never distributed | Active | — (ShellCheck 0.11 for every tracked shell script outside `docs/handshake/`. **Added 2026-10-27 on the owner's word** (item 3.6); its findings were fixed or carry a `# shellcheck disable` with a reason. Not a required check yet.) |

## System dependencies (user-system, surfaced via the dependency subsystem or the setup wizard)

> Most rows here are probed by the dependency subsystem (`deps/`). cyanrip is probed (`check_cyanrip`) and is always provisioned by the host-setup wizard (`deps/host_setup.py`).
>
> **The ripper Platterpus used before cyanrip was removed entirely on 2026-06-30 (KDD-18 amendment) — cyanrip (the Platterpus fork of cyanrip) is the sole backend.** Its old row is retained below struck-through as the record; nothing installs, exports, reads, or probes it anymore. The uninstaller only removes leftovers from older versions (`~/.local/bin/whipper`, `~/.config/whipper/`) if they are present.

| Name | Where it comes from | Version constraint | Status | Replacement plan |
|---|---|---|---|---|
| cyanrip (**the** ripping backend, KDD-18) | Distrobox container `ripping`, host-exported to `~/.local/bin/cyanrip`. **The shipped backend is the PINNED FORK, built from source by the wizard and by `--install-ripper` (KDD-33/34).** Which commit and version that is, the round that approved it, and any build under review are not repeated here: they are `deps/fork_source.py` (`FORK_PIN`, `PIN_UNDER_REVIEW`) and `handshake_approval.py` (`APPROVED_BY_ROUND`), and the generated [*full map*](#the-full-map-machine-readable-bomcdxjson) below lists them; Help → About Platterpus… shows them on a user's machine. A rip made with any other build is recorded as `unapproved` in its rip report; the EAC export names the build. **Fallback package source only: COPR `barsnick/non-fed`** (GPG-checked; cyanrip 0.9.3.1, chroots Fedora 43–45 + rawhide as of 2026-10-07) — verified 2026-06-09 that neither Fedora nor RPM Fusion packages cyanrip. The wizard writes the standard COPR `.repo` stanza itself (version-generic `$releasever/$basearch`), so no `dnf copr` plugin is needed. | `>=0.9.0` for a stock build; the approved build is a **pin, not a range** (`deps/fork_source.FORK_PIN`) | Active — the fork, at `FORK_PIN`; the COPR carries stock 0.9.3.1 (2024-06-05). LGPL-2.1 — fine: subprocess, no linking. | If the COPR disappears: meson source build inside the container — all build deps are in Fedora proper (`ffmpeg-free-devel`, `libcdio-paranoia-devel`, `libmusicbrainz5-devel`, `libcurl-devel`). See [docs/archive/ecosystem-audit-2026-06.md](docs/archive/ecosystem-audit-2026-06.md). |
| ~~whipper~~ (**removed 2026-06-30**) | ~~Distrobox container, host-exported to `~/.local/bin/whipper`~~ | — | **Removed.** Stalled since v0.10.0 (2021), `pkg_resources` cliff, and the >587 read-offset bug that failed tracks on the BDR-209D. cyanrip replaced it with no functional loss (KDD-18 amendment). | — |
| metaflac | Distrobox container `ripping` (same export route) | (whatever ships with the container's `flac` package) | Active (FLAC project) | — |
| flac (decoder) | Host, **optional** — used by CTDB verify to decode FLAC→PCM if present; the feature degrades with a clear message if absent (decision 2026-06-03). No required dependency added. | any | Active (FLAC project) | — |
| ffmpeg | Host/container, **optional** — the single encoder for the **Output format** feature (KDD-22): transcodes the FLAC master to WavPack/MP3/WAV when the user picks a non-FLAC format. Registered in `deps/registry.py`; absent only disables non-FLAC output (FLAC rips are unaffected, and the FLAC master is always kept, so a missing ffmpeg never costs audio). Must be on the host's `PATH`: the setup wizard neither installs nor exports it, and cyanrip links FFmpeg's libraries inside its container, which gives the host no `ffmpeg` command (Bazzite ships one). Shipped 2026-06-26. | `>=4.0` | Active (FFmpeg project) | — (LGPL/GPL build; invoked as a subprocess, never linked) |
| wavpack (standalone) | **Not a dependency yet — future enhancement.** ffmpeg already produces lossless `.wv` with text tags; the standalone `wavpack` tool would only be needed to embed cover art *inside* the `.wv` (APEv2 binary tag), which ffmpeg's WavPack muxer can't do. If/when that lands it routes through the dependency subsystem like the others. The album-folder `cover.<ext>` is the cover image for WavPack today. | n/a | Active (WavPack project) | — |
| libdiscid | (not installed) | n/a | **Not needed on host** — cyanrip computes the disc ID; the GUI never calls libdiscid (KDD-06, confirmed T32 2026-05-29) | — |
| MusicBrainz Picard | Flathub via `.flatpakref` URL (see install_command in `deps/registry.py`) | latest | Active | — |
| cd-paranoia (drive cache probe, KDD-29) | Distrobox container `ripping`, host-exported to `~/.local/bin/cd-paranoia` (installed by the setup wizard's final, **non-blocking** step via `dnf install /usr/bin/cd-paranoia`, which resolves whichever package provides it — libcdio on Fedora). **Optional.** Probed by `check_cdparanoia`. | any (`-A` self-test exists in every release) | Active (libcdio project; GPL — subprocess, no linking) | — (libcdio's own cdparanoia; it shares the read engine cyanrip links, so its `-A` cache self-test speaks for cyanrip's reads) |

**Cache-defeat note on the cyanrip row above (updated 2026-07-24, KDD-29):**
cyanrip's engine, **libcdio-paranoia**, *attempts* cache defeat on every rip
(readahead cache-exhaustion reads plus FUA where the drive advertises support) —
this comes bundled inside cyanrip itself. It is **best-effort and
drive-dependent**; nothing in cyanrip's own output confirms defeat happened, so
that field alone would read `(unknown)` (PLANNING.md KDD-25). We now **measure**
the verdict with the standalone **`cd-paranoia -A`** self-test — libcdio's own
copy of that same engine (the `cd-paranoia` dependency row above) — invoked via
Set up drive → Analyze cache and recorded per drive. This is the maintainer-approved
new dependency (deviation-policy sign-off given 2026-07-24). The honesty rule from
KDD-25 still holds: an inconclusive probe keeps `(unknown)`, never a forged `Yes`.
The exact `-A` verdict wording is hardware-tuned against the first real capture
(KDD-29); until then the parser stays conservative.

## System dependencies (build/runtime requirements inside the Distrobox container) — HISTORICAL (whipper-era)

> **HISTORICAL — whipper was removed on 2026-06-30 (KDD-18 amendment); the rows below were whipper-specific and are no longer current requirements.** cyanrip (the sole backend now) is installed by the host-setup wizard — stock cyanrip from the COPR, which pulls its runtime deps, then the pinned fork built over it; it needs neither `python3-setuptools` nor `cdrdao`. Kept as the record of what the whipper-in-container era required.

These weren't installed by our GUI but WERE required for whipper to work, inside the `ripping` Distrobox container alongside whipper itself. Documented here because real-user testing on Bazzite (2026-05-28) surfaced missing-dep issues that weren't obvious from the README.

| Name | Why it's needed | How to install (inside the container) |
|---|---|---|
| `python3-setuptools` | *(whipper-era — not needed by cyanrip.)* Whipper 0.10.0 imports `pkg_resources` from setuptools. Python 3.14 (shipped in Fedora 44) doesn't include setuptools by default, and Fedora's whipper RPM doesn't declare it as a dep. Without it, `whipper --version` raises `ModuleNotFoundError: No module named 'pkg_resources'`. | `sudo dnf install python3-setuptools` |
| `cdrdao` | *(whipper-era — not needed by cyanrip.)* Required by whipper for gap detection. Usually pulled in by `dnf install whipper` as a transitive dep, but worth noting in case of minimal container bases. | `sudo dnf install cdrdao` |

### Notes on the unmaintained items

**whipper (0.10.0, 2021-05-17)** — Last release on PyPI/GitHub. **Removed as a backend on 2026-06-30 (KDD-18 amendment); cyanrip is now the sole ripper.** While it was in use it ran on Fedora 44 + Python 3.14 only if `python3-setuptools` was installed alongside it (the `pkg_resources` import was otherwise broken). Our `RipBackend` adapter (PLANNING.md §5) is what let the swap to cyanrip happen without touching the GUI layer. CLAUDE.md Critical Rule #1 codifies this.

Whipper-on-newer-Python surfaced a `pkg_resources is deprecated` UserWarning on every invocation, and setuptools 81 was slated to remove `pkg_resources` entirely — the compatibility cliff that, together with the >587 read-offset bug, drove the migration to `cyanrip` (completed 2026-06-30).

**musicbrainzngs (0.7.1, 2020-01-11)** — Last PyPI release. The underlying MusicBrainz `ws/2` REST API is stable. Risk is library bitrot (e.g., dropped Python compatibility on a future interpreter, not a server-side break). Our `MusicBrainzClient` adapter (PLANNING.md §6) lets us replace with raw `requests` against the JSON endpoint. CLAUDE.md Critical Rule #1.

**appimage-builder (Snyk-flagged inactive)** — Not used. Listed here so it's tracked: CLAUDE.md Critical Rule #2 forbids reaching for it without explicit user approval. `python-appimage` (above) is the active builder.

## The full map (machine-readable: `bom.cdx.json`)

`bom.cdx.json`, at the repository root, is a **CycloneDX 1.7** bill of materials: the standard JSON format that dependency-track, OSV-Scanner, grype and other supply-chain tools read. It lists **everything Platterpus has or relies on**: the Python it runs on (the supported range, the CI matrix, and the interpreter the AppImage bundles), Qt through PySide6, every Python package with its pin, the cyanrip fork (the approved pin, the build under review) and upstream cyanrip, the `ripping` container and its image, the libraries the fork is built against, every external program the app runs or offers, the desktop interface it uses, the bundled AccurateRip data, the external services it talks to, and the CI actions, tools and runners. Each entry says where it is used and where its pin is enforced, and a dependency graph records who needs what.

**It is generated, not written.** `scripts/emit_bom.py` reads it out of the code that enforces each fact (`pyproject.toml`, the AppImage requirements, the dependency registry, the setup wizard's real plan, `deps/fork_source.py`, the URL constants in `src/`, and the workflow files), and writes both `bom.cdx.json` and the block below in the same run, so the two cannot disagree. Do not edit either by hand:

- regenerate: `python3 scripts/emit_bom.py`
- check: `python3 scripts/emit_bom.py --check` (exits 1 when either is stale; `tests/test_bom_emitted.py` runs the same comparison in CI)
- re-run it **after a version bump**, because the BOM names the app version it describes.

It is a *pre-build* BOM: the constraints the project declares, not what one install resolved. The CI `sbom` job's artifact is the resolved Python environment that ships, and Help → *About* (`build_info.component_inventory`) is what a user's machine actually has. Licences are not in it; they are in the tables above. `tests/test_bom_emitted.py` checks its structure and validates it against the CycloneDX 1.7 JSON schema, strict and offline, with `cyclonedx-python-lib` (the dev-extra row above, approved 2026-10-05).

<!-- BEGIN GENERATED: emit_bom.py — do not hand-edit; regenerate with python3 scripts/emit_bom.py -->

**94 components and 14 services**, the same entries as `bom.cdx.json` (CycloneDX 1.7), from the same run of `scripts/emit_bom.py`.

| Category | Entries |
|---|---|
| Languages, runtimes and platforms | 4 |
| Python packages the application imports | 6 |
| The ripper (cyanrip) and its related projects | 3 |
| The ripping container | 2 |
| What the cyanrip fork is built from, inside the container | 13 |
| External programs Platterpus runs or offers | 28 |
| Desktop interfaces | 1 |
| Bundled data | 1 |
| Python packages for development and tests (the dev extra) | 8 |
| Python packages for building, releasing and CI | 9 |
| GitHub Actions | 6 |
| CI and build programs | 12 |
| CI runner images | 1 |
| External services | 14 |

### Languages, runtimes and platforms (4)

| Name | Version / constraint | Scope | What it is for | Used in | Pin enforced in |
|---|---|---|---|---|---|
| `Linux` | unconstrained | required | The only operating system Platterpus targets. | platterpus-x86_64.AppImage, pip / pipx installs | pyproject.toml [project].classifiers |
| `python` | `>=3.11` | required | The interpreter a pipx or development install runs on. The AppImage brings its own (next row). | pip / pipx installs, development checkouts, CI | pyproject.toml [project].requires-python, .github/workflows/ci.yml (test matrix) |
| `python (bundled in the AppImage)` | `3.12` | required | The interpreter python-appimage bundles into the AppImage; pinned so a new upstream beta cannot become the release's runtime. | platterpus-x86_64.AppImage | build/build_appimage.sh (PLATTERPUS_PYTHON_VERSION, overridable) |
| `Qt` | `>=6.11.1,<6.12` | required | The GUI toolkit. It ships inside the PySide6 wheels, and PySide6 releases carry Qt's version number, so the PySide6 constraint is the Qt constraint. | every window and dialog (through PySide6) | pyproject.toml [project].dependencies (PySide6), build/python-appimage/requirements.txt (PySide6) |

### Python packages the application imports (6)

| Name | Version / constraint | Scope | What it is for | Used in | Pin enforced in |
|---|---|---|---|---|---|
| `cryptography` | `>=50.0.0,<51` | required | Ed25519 verification for the minisign path of the updater. | src/platterpus/update_signing.py | pyproject.toml [project].dependencies, build/python-appimage/requirements.txt |
| `musicbrainzngs` | `0.7.1` | required | MusicBrainz client, behind the MusicBrainzClient adapter (Critical rule #1; unmaintained upstream). | src/platterpus/adapters/musicbrainz_client.py | pyproject.toml [project].dependencies, build/python-appimage/requirements.txt, src/platterpus/deps/registry.py (checked at launch) |
| `numpy` | `>=2.4.6,<2.5` | required | Reed-Solomon syndromes over GF(2^16) that locate where a rip differs from a CTDB entry (TASKS R43). | src/platterpus/ctdb/syndromes.py, src/platterpus/ctdb/verify_parity.py | pyproject.toml [project].dependencies, build/python-appimage/requirements.txt, src/platterpus/deps/registry.py (checked at launch) |
| `PySide6` | `>=6.11.1,<6.12` | required | Qt for Python: the whole GUI. | src/platterpus/, src/platterpus/ui/, src/platterpus/ui/dialogs/, src/platterpus/uiscript/, src/platterpus/workers/ (every importer is in these directories) | pyproject.toml [project].dependencies, build/python-appimage/requirements.txt |
| `sigstore` | `>=4.5.0,<4.6` | required | Verifies each release's build-provenance attestation before an update installs. | src/platterpus/update_attestation.py | pyproject.toml [project].dependencies, build/python-appimage/requirements.txt |
| `tomli-w` | `>=1.0,<2` | required | Writes config.toml (the standard library reads TOML but cannot write it). | src/platterpus/config.py | pyproject.toml [project].dependencies, build/python-appimage/requirements.txt |

### The ripper (cyanrip) and its related projects (3)

| Name | Version / constraint | Scope | What it is for | Used in | Pin enforced in |
|---|---|---|---|---|---|
| `cyanrip` | `0.9.4-rc3+platterpus.25` | required | The ripping backend (KDD-18): the Platterpus fork of cyanrip, built from source at the handshake-approved pin by the setup wizard and by --install-ripper, then exported to the host. | src/platterpus/adapters/cyanrip_backend.py, src/platterpus/deps/fork_source.py, src/platterpus/deps/host_setup.py, src/platterpus/deps/registry.py | src/platterpus/deps/fork_source.py (FORK_PIN, FORK_EXPECTED_VERSION), src/platterpus/handshake_approval.py (APPROVED_BY_ROUND), src/platterpus/deps/registry.py (min_version) |
| `cyanrip (build under review)` | `0.9.4-rc3+platterpus.27` | optional | The build handshake round 36 is reviewing; installable on request, never the default. | src/platterpus/deps/fork_source.py (UNDER_REVIEW_TARGET) | src/platterpus/deps/fork_source.py (PIN_UNDER_REVIEW) |
| `cyanrip (upstream)` | `>=0.9.0` | optional | Stock cyanrip. The wizard installs it first from the COPR so a failed fork build still leaves a working ripper; the fork is then exported over it. Also the project the fork tracks. | src/platterpus/deps/host_setup.py (the cyanrip step) | src/platterpus/deps/registry.py (min_version) |

Details for `cyanrip`:

- `pin`: 5f1d036
- `build-tag`: platterpus-fork-g5f1d036
- `banner`: cyanrip 0.9.4-rc3+platterpus.25 (platterpus-fork-g5f1d036)
- `branch`: platterpus-fork
- `release-seq`: 36
- `approved-by-round`: 35
- `approved-for-platterpus`: 0.7.110
- `checked-minimum`: 0.9.0
- `installed-at`: /usr/local/bin/cyanrip inside the ripping container
- `host-export`: ~/.local/bin/cyanrip
- `exported-from`: /usr/bin/cyanrip, /usr/local/bin/cyanrip (the last export wins)
- `pin-under-review`: 5aeefc4 (0.9.4-rc3+platterpus.27, round 36, published: yes)
- `test-pin`: 3952c03 (0.9.4-rc2+platterpus.12, nominated by round 21)
- `handshake`: bidirectional release handshake: docs/cyanrip-handshake.md

Details for `cyanrip (build under review)`:

- `pin`: 5aeefc4
- `round`: 36
- `published`: yes

### The ripping container (2)

| Name | Version / constraint | Scope | What it is for | Used in | Pin enforced in |
|---|---|---|---|---|---|
| `fedora-toolbox` | `latest` | required | The image the ripping container is created from. | src/platterpus/deps/host_setup.py | src/platterpus/deps/host_setup.py (DEFAULT_IMAGE) |
| `ripping` | unconstrained | required | The Distrobox container the ripper runs in. The GUI never enters it to rip; it calls the host-exported wrapper (Critical rule #3). | src/platterpus/deps/host_setup.py (creates it), src/platterpus/drive_control.py (the scoped force-stop exception), src/platterpus/deps/host_teardown.py (removes it) | src/platterpus/deps/host_setup.py (DEFAULT_CONTAINER) |

### What the cyanrip fork is built from, inside the container (13)

| Name | Version / constraint | Scope | What it is for | Used in | Pin enforced in |
|---|---|---|---|---|---|
| `gcc` | unconstrained | excluded | Toolchain for building the cyanrip fork; not needed to run it. | building the cyanrip fork, inside the container | src/platterpus/deps/fork_source.py (FORK_BUILD_PACKAGES) |
| `git` | unconstrained | excluded | Toolchain for building the cyanrip fork; not needed to run it. | building the cyanrip fork, inside the container | src/platterpus/deps/fork_source.py (FORK_BUILD_PACKAGES) |
| `libavcodec` | unconstrained | required | Linked by the cyanrip fork (its src/meson.build). | building and running the cyanrip fork, inside the container | src/platterpus/deps/fork_source.py (FORK_BUILD_PACKAGES) |
| `libavfilter` | unconstrained | required | Linked by the cyanrip fork (its src/meson.build). | building and running the cyanrip fork, inside the container | src/platterpus/deps/fork_source.py (FORK_BUILD_PACKAGES) |
| `libavformat` | unconstrained | required | Linked by the cyanrip fork (its src/meson.build). | building and running the cyanrip fork, inside the container | src/platterpus/deps/fork_source.py (FORK_BUILD_PACKAGES) |
| `libavutil` | unconstrained | required | Linked by the cyanrip fork (its src/meson.build). | building and running the cyanrip fork, inside the container | src/platterpus/deps/fork_source.py (FORK_BUILD_PACKAGES) |
| `libcdio` | unconstrained | required | Linked by the cyanrip fork (its src/meson.build). | building and running the cyanrip fork, inside the container | src/platterpus/deps/fork_source.py (FORK_BUILD_PACKAGES) |
| `libcdio_paranoia` | unconstrained | required | Linked by the cyanrip fork (its src/meson.build). | building and running the cyanrip fork, inside the container | src/platterpus/deps/fork_source.py (FORK_BUILD_PACKAGES) |
| `libcurl` | unconstrained | required | Linked by the cyanrip fork (its src/meson.build). | building and running the cyanrip fork, inside the container | src/platterpus/deps/fork_source.py (FORK_BUILD_PACKAGES) |
| `libmusicbrainz5` | unconstrained | required | Linked by the cyanrip fork (its src/meson.build). | building and running the cyanrip fork, inside the container | src/platterpus/deps/fork_source.py (FORK_BUILD_PACKAGES) |
| `libswresample` | unconstrained | required | Linked by the cyanrip fork (its src/meson.build). | building and running the cyanrip fork, inside the container | src/platterpus/deps/fork_source.py (FORK_BUILD_PACKAGES) |
| `meson` | unconstrained | excluded | Toolchain for building the cyanrip fork; not needed to run it. | building the cyanrip fork, inside the container | src/platterpus/deps/fork_source.py (FORK_BUILD_PACKAGES) |
| `ninja-build` | unconstrained | excluded | Toolchain for building the cyanrip fork; not needed to run it. | building the cyanrip fork, inside the container | src/platterpus/deps/fork_source.py (FORK_BUILD_PACKAGES) |

### External programs Platterpus runs or offers (28)

| Name | Version / constraint | Scope | What it is for | Used in | Pin enforced in |
|---|---|---|---|---|---|
| `apt-get` | unconstrained | optional | Host installer for Distrobox / podman on Debian and Ubuntu. | src/platterpus/deps/host_setup.py | — |
| `bash` | unconstrained | optional | Runs the packaged rig_session.sh for --rig-session. That script uses ordinary shell utilities, which are not listed one by one. | src/platterpus/app.py | — |
| `cd-paranoia` | unconstrained | optional | Optional. libcdio's cd-paranoia — the same read engine cyanrip uses. Its `-A` self-test measures whether this drive defeats its audio cache, so the EAC-compatible log's 'Defeat audio cache' line can carry a measured Yes/No instead of '(unknown)' (KDD-29). Absent only means that verdict stays unmeasured; ripping is unaffected. Installed into the container + exported by the one-time setup wizard. | src/platterpus/adapters/cache_probe.py, src/platterpus/deps/host_setup.py, src/platterpus/deps/host_teardown.py, src/platterpus/deps/registry.py | src/platterpus/deps/registry.py (min_version, probed at launch) |
| `distrobox` | unconstrained | required | Creates and enters the ripping container: setup, the fork build, the scoped force-stop exception, and teardown. | src/platterpus/deps/fork_source.py, src/platterpus/deps/host_setup.py, src/platterpus/deps/host_teardown.py, src/platterpus/drive_control.py | — |
| `distrobox-enter` | unconstrained | required | What the exported ~/.local/bin wrappers run; the wrapper probe times it to diagnose a wrapper that hangs. | src/platterpus/deps/ripper_wrapper_probe.py | — |
| `distrobox-export` | unconstrained | required | Exports cyanrip, flac, metaflac and cd-paranoia from the container to ~/.local/bin. | src/platterpus/deps/fork_source.py, src/platterpus/deps/host_setup.py | — |
| `dnf` | unconstrained | required | Installs flac, cyanrip, cd-paranoia and the fork's build inputs inside the container; also the host installer on Fedora-family systems. | src/platterpus/deps/host_setup.py | — |
| `docker` | unconstrained | optional | Accepted in place of podman as Distrobox's engine when present. | src/platterpus/deps/host_setup.py | — |
| `eject` | unconstrained | optional | Opens the drive tray after a force-stop. | src/platterpus/drive_control.py | — |
| `ffmpeg` | `>=4.0` | optional | Optional. The encoder for the Output-format feature (KDD-22): transcodes the FLAC master to WavPack, MP3, or WAV when a non-FLAC output is selected, AND verifies those derived files afterward (decode-to-PCM bit-compare for lossless, decode-clean for MP3). Absent only disables non-FLAC output (FLAC ripping is unaffected, and the FLAC master is always kept). It must be on the host's PATH: the setup wizard neither installs nor exports it, and the FFmpeg libraries inside the ripping container are not a command the app can run. Install it with your distribution's package manager. | src/platterpus/adapters/derived_verify.py, src/platterpus/adapters/transcode.py, src/platterpus/deps/checks.py, src/platterpus/deps/registry.py | src/platterpus/deps/registry.py (min_version, probed at launch) |
| `flac` | `>=1.3.0` | optional | Optional. Only needed for the 'Verify with CTDB after a rip' setting: the CTDB audio check decodes the FLACs back to PCM on the host. The setup wizard installs it into the container alongside cyanrip and metaflac; re-run the wizard if it's missing. | src/platterpus/adapters/flac_verify.py, src/platterpus/ctdb/decode.py, src/platterpus/deps/checks.py, src/platterpus/deps/host_setup.py, src/platterpus/deps/host_teardown.py, src/platterpus/deps/registry.py | src/platterpus/deps/registry.py (min_version, probed at launch) |
| `flatpak` | unconstrained | optional | Installs MusicBrainz Picard from Flathub and launches it for an unknown disc. | src/platterpus/deps/registry.py, src/platterpus/ui/unknown_album.py | — |
| `fuser` | unconstrained | optional | Device-scoped force-stop of whatever holds the drive on cancel (host copy only). | src/platterpus/drive_control.py | — |
| `gio` | unconstrained | optional | Marks the desktop shortcut trusted after AppImage integration. | src/platterpus/appimage_integration.py | — |
| `kbuildsycoca5` | unconstrained | optional | The same refresh for KDE Plasma 5 (fire-and-forget). | src/platterpus/appimage_integration.py | — |
| `kbuildsycoca6` | unconstrained | optional | Refreshes KDE Plasma 6's menu cache after AppImage integration (fire-and-forget). | src/platterpus/appimage_integration.py | — |
| `metaflac` | `>=1.3.0` | required | Part of the FLAC reference encoder package. Used to apply tags after a rip and to add placeholders for unknown discs. Installed + exported by the one-time setup wizard. | src/platterpus/adapters/metaflac.py, src/platterpus/ctdb/decode.py, src/platterpus/deps/checks.py, src/platterpus/deps/registry.py | src/platterpus/deps/registry.py (min_version, probed at launch) |
| `MusicBrainz Picard` | unconstrained | optional | Optional. Auto-launched on unknown discs when the 'Auto-launch Picard' setting is enabled. | src/platterpus/deps/checks.py, src/platterpus/deps/registry.py, src/platterpus/ui/unknown_album.py | src/platterpus/deps/registry.py (min_version, probed at launch) |
| `pacman` | unconstrained | optional | Host installer for Distrobox / podman on Arch. | src/platterpus/deps/host_setup.py | — |
| `pgrep` | unconstrained | optional | Lists the reader processes the host sees: the exit check, and the acceptance bundle's record of whether a ripper was still running as it was packed (host copy only; never signals anything). | src/platterpus/drive_control.py | — |
| `pkexec` | unconstrained | optional | Graphical privilege prompt for installing Distrobox or podman on the host (a GUI has no terminal for sudo). | src/platterpus/deps/host_setup.py | — |
| `pkill` | unconstrained | optional | Name-matched force-stop of the reader on cancel (host first, then the container — Critical rule #3's scoped exception). | src/platterpus/drive_control.py | — |
| `podman` | unconstrained | required | Distrobox's container engine; the wizard installs it when no engine is present. Docker is accepted instead when it is already there. | src/platterpus/deps/host_setup.py | — |
| `sh` | unconstrained | required | Runs the fork's build, install and verify scripts in the container. | src/platterpus/deps/fork_source.py | — |
| `sudo` | unconstrained | required | Root inside the container for dnf and the fork install. | src/platterpus/deps/fork_source.py, src/platterpus/deps/host_setup.py | — |
| `systemd-inhibit` | unconstrained | optional | Holds idle sleep, suspend and the lid switch off during a long unattended run. | src/platterpus/sleep_inhibit.py | — |
| `update-desktop-database` | unconstrained | optional | Refreshes the menu after AppImage integration (fire-and-forget). | src/platterpus/appimage_integration.py | — |
| `zypper` | unconstrained | optional | Host installer for Distrobox / podman on openSUSE. | src/platterpus/deps/host_setup.py | — |

### Desktop interfaces (1)

| Name | Version / constraint | Scope | What it is for | Used in | Pin enforced in |
|---|---|---|---|---|---|
| `org.freedesktop.ScreenSaver` | unconstrained | optional | The freedesktop screensaver D-Bus interface, used to keep the screen from blanking during a run that takes screenshots. | src/platterpus/screen_inhibit.py | — |

### Bundled data (1)

| Name | Version / constraint | Scope | What it is for | Used in | Pin enforced in |
|---|---|---|---|---|---|
| `AccurateRip drive offsets` | `2026-06-05` | required | A snapshot of AccurateRip's drive read-offset table, shipped in the package so offset lookup works offline. | src/platterpus/adapters/accuraterip_offsets.py | scripts/update_drive_offsets.py (regenerates it) |

### Python packages for development and tests (the dev extra) (8)

| Name | Version / constraint | Scope | What it is for | Used in | Pin enforced in |
|---|---|---|---|---|---|
| `cyclonedx-python-lib` | `>=11.12,<12` | excluded | — | loaded by pytest as a plugin | pyproject.toml [project.optional-dependencies].dev |
| `hypothesis` | `>=6` | excluded | Property-based tests, including the parsers' never-raises properties. | tests/ (every importer is in these directories) | pyproject.toml [project.optional-dependencies].dev |
| `mypy` | `>=2.3,<2.4` | excluded | Strict type checking; gates CI. | .github/workflows/ci.yml, scripts/check.py | pyproject.toml [project.optional-dependencies].dev |
| `pip-audit` | `>=2.10.1,<2.11` | excluded | — | .github/workflows/ci.yml, .github/workflows/release.yml | pyproject.toml [project.optional-dependencies].dev |
| `pytest` | `>=8,<10` | excluded | The test runner. | tests/ (every importer is in these directories), .github/workflows/ci.yml, scripts/check.py | pyproject.toml [project.optional-dependencies].dev |
| `pytest-cov` | `>=5` | excluded | Branch coverage and the CI coverage floor. | loaded by pytest as a plugin | pyproject.toml [project.optional-dependencies].dev |
| `pytest-xdist` | `>=3.6,<4` | excluded | Parallel test runs (CI and scripts/check.py pass -n auto). | loaded by pytest as a plugin | pyproject.toml [project.optional-dependencies].dev |
| `ruff` | `>=0.15.22,<0.16` | excluded | Lint and format; gates CI. | .github/workflows/ci.yml, scripts/check.py | pyproject.toml [project.optional-dependencies].dev |

### Python packages for building, releasing and CI (9)

| Name | Version / constraint | Scope | What it is for | Used in | Pin enforced in |
|---|---|---|---|---|---|
| `actionlint-py` | `>=1.7.12,<1.8` | excluded | Lints the workflow files (syntax and expressions). | pyproject.toml [project.optional-dependencies].ci-lint (installed by .github/workflows/ci.yml) | pyproject.toml [project.optional-dependencies].ci-lint (installed by .github/workflows/ci.yml) |
| `build` | `>=1.6.1,<1.7` | excluded | PEP 517 frontend: builds the wheel and sdist. | build/build_appimage.sh, pyproject.toml [project.optional-dependencies].publish (installed by .github/workflows/publish-pypi.yml) | build/build_appimage.sh, pyproject.toml [project.optional-dependencies].publish (installed by .github/workflows/publish-pypi.yml) |
| `cyclonedx-bom` | `>=7,<8` | excluded | Writes the CI sbom job's resolved-environment SBOM. | pyproject.toml [project.optional-dependencies].sbom (installed by .github/workflows/ci.yml) | pyproject.toml [project.optional-dependencies].sbom (installed by .github/workflows/ci.yml) |
| `python-appimage` | `>=1.4.6,<1.5` | excluded | Builds the AppImage (Critical rule #2). | build/build_appimage.sh | build/build_appimage.sh |
| `setuptools` | `>=77` | excluded | The build backend. | pyproject.toml [build-system].requires | pyproject.toml [build-system].requires |
| `shellcheck-py` | `>=0.11.0.1,<0.12` | excluded | Checks the shell scripts. | pyproject.toml [project.optional-dependencies].ci-lint (installed by .github/workflows/ci.yml) | pyproject.toml [project.optional-dependencies].ci-lint (installed by .github/workflows/ci.yml) |
| `twine` | `>=7.0.0,<7.1` | excluded | Checks the wheel and sdist before the PyPI upload. | pyproject.toml [project.optional-dependencies].publish (installed by .github/workflows/publish-pypi.yml) | pyproject.toml [project.optional-dependencies].publish (installed by .github/workflows/publish-pypi.yml) |
| `wheel` | `unpinned` | excluded | Wheel support for the build backend. | pyproject.toml [build-system].requires | pyproject.toml [build-system].requires |
| `zizmor` | `>=1.31.1,<1.32` | excluded | Audits the workflow files for security problems, offline. | pyproject.toml [project.optional-dependencies].ci-lint (installed by .github/workflows/ci.yml) | pyproject.toml [project.optional-dependencies].ci-lint (installed by .github/workflows/ci.yml) |

### GitHub Actions (6)

| Name | Version / constraint | Scope | What it is for | Used in | Pin enforced in |
|---|---|---|---|---|---|
| `actions/attest-build-provenance` | `v4.1.1` | excluded | Signs the release AppImage's build-provenance attestation. | .github/workflows/release.yml (build-and-release) | .github/workflows/release.yml |
| `actions/checkout` | `v7.0.1` | excluded | Checks out the repository. | .github/workflows/appimage.yml (build), .github/workflows/ci.yml (changelog), .github/workflows/ci.yml (commit-subjects), .github/workflows/ci.yml (gitleaks), .github/workflows/ci.yml (lint), .github/workflows/ci.yml (lock-check), .github/workflows/ci.yml (lock-install), .github/workflows/ci.yml (media-guard), .github/workflows/ci.yml (pip-audit), .github/workflows/ci.yml (sbom), .github/workflows/ci.yml (shellcheck), .github/workflows/ci.yml (test), .github/workflows/ci.yml (tests-touched), .github/workflows/ci.yml (typecheck), .github/workflows/ci.yml (workflow-lint), .github/workflows/dependencies.yml (outdated), .github/workflows/dependencies.yml (relock), .github/workflows/mutation.yml (sweep), .github/workflows/publish-pypi.yml (publish), .github/workflows/release.yml (build-and-release) | .github/workflows/appimage.yml, .github/workflows/ci.yml, .github/workflows/dependencies.yml, .github/workflows/mutation.yml, .github/workflows/publish-pypi.yml, .github/workflows/release.yml |
| `pypa/gh-action-pypi-publish` | `v1.14.1` | excluded | Publishes the wheel and sdist to PyPI. | .github/workflows/publish-pypi.yml (publish) | .github/workflows/publish-pypi.yml |
| `actions/setup-python` | `v7.0.0` | excluded | Installs the job's Python. | .github/workflows/appimage.yml (build), .github/workflows/ci.yml (commit-subjects), .github/workflows/ci.yml (gitleaks), .github/workflows/ci.yml (lint), .github/workflows/ci.yml (lock-check), .github/workflows/ci.yml (lock-install), .github/workflows/ci.yml (pip-audit), .github/workflows/ci.yml (sbom), .github/workflows/ci.yml (shellcheck), .github/workflows/ci.yml (test), .github/workflows/ci.yml (typecheck), .github/workflows/ci.yml (workflow-lint), .github/workflows/dependencies.yml (relock), .github/workflows/mutation.yml (sweep), .github/workflows/publish-pypi.yml (publish), .github/workflows/release.yml (build-and-release) | .github/workflows/appimage.yml, .github/workflows/ci.yml, .github/workflows/dependencies.yml, .github/workflows/mutation.yml, .github/workflows/publish-pypi.yml, .github/workflows/release.yml |
| `astral-sh/setup-uv` | `v10.3.0` | excluded | — | .github/workflows/ci.yml (lock-check), .github/workflows/dependencies.yml (outdated), .github/workflows/dependencies.yml (relock) | .github/workflows/ci.yml, .github/workflows/dependencies.yml |
| `actions/upload-artifact` | `v7.0.2` | excluded | Keeps a job's output (the SBOM, the AppImage, mutation reports). | .github/workflows/appimage.yml (build), .github/workflows/ci.yml (sbom), .github/workflows/mutation.yml (sweep) | .github/workflows/appimage.yml, .github/workflows/ci.yml, .github/workflows/mutation.yml |

### CI and build programs (12)

| Name | Version / constraint | Scope | What it is for | Used in | Pin enforced in |
|---|---|---|---|---|---|
| `appimagetool` | unconstrained | excluded | Re-packs the AppImage to embed the zsync update information (the copy python-appimage caches, or the system's). | build/build_appimage.sh | — |
| `fonts-dejavu-core` | unconstrained | excluded | Installed with apt-get on the runner. | .github/workflows/ci.yml (test) | — |
| `gh` | unconstrained | excluded | GitHub CLI on the runner: creates the release and uploads its assets. | .github/workflows/release.yml | — |
| `gitleaks` | `8.24.3` | excluded | The secret scanner the gitleaks job runs. | .github/workflows/ci.yml (gitleaks) | .github/workflows/ci.yml |
| `libdbus-1-3` | unconstrained | excluded | A system library PySide6 needs to run headless in CI. | .github/workflows/ci.yml (test), .github/workflows/mutation.yml (sweep) | — |
| `libegl1` | unconstrained | excluded | A system library PySide6 needs to run headless in CI. | .github/workflows/ci.yml (test), .github/workflows/mutation.yml (sweep) | — |
| `libfontconfig1` | unconstrained | excluded | A system library PySide6 needs to run headless in CI. | .github/workflows/ci.yml (test), .github/workflows/mutation.yml (sweep) | — |
| `libfreetype6` | unconstrained | excluded | A system library PySide6 needs to run headless in CI. | .github/workflows/ci.yml (test), .github/workflows/mutation.yml (sweep) | — |
| `libgl1` | unconstrained | excluded | A system library PySide6 needs to run headless in CI. | .github/workflows/ci.yml (test), .github/workflows/mutation.yml (sweep) | — |
| `libglib2.0-0` | unconstrained | excluded | A system library PySide6 needs to run headless in CI. | .github/workflows/ci.yml (test), .github/workflows/mutation.yml (sweep) | — |
| `libxkbcommon0` | unconstrained | excluded | A system library PySide6 needs to run headless in CI. | .github/workflows/ci.yml (test), .github/workflows/mutation.yml (sweep) | — |
| `zsync` | unconstrained | excluded | zsyncmake, which writes the AppImage's .zsync delta-update file. | .github/workflows/release.yml (build-and-release) | — |

### CI runner images (1)

| Name | Version / constraint | Scope | What it is for | Used in | Pin enforced in |
|---|---|---|---|---|---|
| `ubuntu-22.04` | unconstrained | excluded | GitHub-hosted runner image. | .github/workflows/appimage.yml (build), .github/workflows/ci.yml (changelog), .github/workflows/ci.yml (commit-subjects), .github/workflows/ci.yml (gitleaks), .github/workflows/ci.yml (lint), .github/workflows/ci.yml (lock-check), .github/workflows/ci.yml (lock-install), .github/workflows/ci.yml (media-guard), .github/workflows/ci.yml (pip-audit), .github/workflows/ci.yml (sbom), .github/workflows/ci.yml (shellcheck), .github/workflows/ci.yml (test), .github/workflows/ci.yml (tests-touched), .github/workflows/ci.yml (typecheck), .github/workflows/ci.yml (workflow-lint), .github/workflows/dependencies.yml (outdated), .github/workflows/dependencies.yml (relock), .github/workflows/mutation.yml (sweep), .github/workflows/publish-pypi.yml (publish), .github/workflows/release.yml (build-and-release) | — |

### External services (14)

| Service | Endpoints | When | Used in |
|---|---|---|---|
| `AccurateRip` | `http://www.accuraterip.com/accuraterip/DriveOffsets.bin`, `https://www.accuraterip.com/driveoffsets.htm` | maintenance (the offset snapshot); a link in the drive setup dialog | scripts/update_drive_offsets.py, src/platterpus/ui/drive_setup_dialog.py |
| `Cover Art Archive` | `https://coverartarchive.org/`, `https://coverartarchive.org/release/` | runtime (cover art after a rip; a reachability check in --doctor) | src/platterpus/adapters/cover_art.py, src/platterpus/preflight.py |
| `CUETools Database (CTDB)` | `http://db.cuetools.net/lookup2.php` | runtime (optional verify after a rip) | src/platterpus/adapters/ctdb_client.py |
| `cyanrip fork release manifest` | `https://raw.githubusercontent.com/rmccann-hub/cyanrip/platterpus-fork/release-manifest.json` | runtime (ripper update offers) | src/platterpus/deps/ripper_manifest.py |
| `cyanrip fork source (git clone)` | `https://github.com/rmccann-hub/cyanrip.git` | setup (the wizard and --install-ripper, inside the container) | src/platterpus/deps/fork_source.py |
| `Fedora container registry` | `https://registry.fedoraproject.org/` | setup (creating the container) | src/platterpus/deps/host_setup.py |
| `Fedora COPR barsnick/non-fed` | `https://download.copr.fedorainfracloud.org/results/barsnick/non-fed/`, `https://download.copr.fedorainfracloud.org/results/barsnick/non-fed/pubkey.gpg` | setup (the stock cyanrip package) | src/platterpus/deps/host_setup.py |
| `Fedora package repositories` | not named in Platterpus | setup (dnf inside the container) | src/platterpus/deps/host_setup.py, src/platterpus/deps/fork_source.py |
| `Flathub` | `https://dl.flathub.org/repo/appstream/org.musicbrainz.Picard.flatpakref` | on request (installing Picard) | src/platterpus/deps/registry.py |
| `GitHub release downloads (update install)` | `https://github.com/rmccann-hub/Platterpus/releases/download/` | runtime (installing an update) | src/platterpus/update_install.py |
| `GitHub Releases API (update check)` | `https://api.github.com/repos/rmccann-hub/Platterpus/releases?per_page=5` | runtime (update check) | src/platterpus/update_check.py |
| `MusicBrainz web service` | `https://musicbrainz.org/ws/2/` | runtime (every disc lookup) | src/platterpus/adapters/musicbrainz_client.py |
| `PyPI` | not named in Platterpus | release (publishing) and development (installing) | .github/workflows/publish-pypi.yml |
| `Sigstore public-good instance` | not named in Platterpus | runtime (installing an update) and release (attesting the build) | src/platterpus/update_attestation.py, .github/workflows/release.yml |

### Dependency graph

Who needs what, as the BOM's `dependencies` section records it. An entry
absent from the left column has dependencies Platterpus does not record.

- `container:fedora-toolbox` → `svc:fedora-registry`
- `container:ripping` → `container:fedora-toolbox`, `svc:fedora-repositories`, `tool-host:distrobox-export`, `tool-host:sudo`
- `data:accuraterip-drive-offsets` → `svc:accuraterip`
- `platterpus` → `data:accuraterip-drive-offsets`, `desktop:org.freedesktop.ScreenSaver`, `pypi:cryptography`, `pypi:musicbrainzngs`, `pypi:numpy`, `pypi:pyside6`, `pypi:sigstore`, `pypi:tomli-w`, `ripper:cyanrip-fork`, `ripper:cyanrip-fork-under-review`, `ripper:cyanrip-upstream`, `runtime:linux`, `runtime:python`, `runtime:python-appimage-bundled`, `svc:cover-art-archive`, `svc:ctdb`, `svc:fork-release-manifest`, `svc:github-release-downloads`, `svc:github-releases-api`, `tool-host:apt-get`, `tool-host:bash`, `tool-host:distrobox`, `tool-host:distrobox-enter`, `tool-host:dnf`, `tool-host:eject`, `tool-host:flatpak`, `tool-host:fuser`, `tool-host:gio`, `tool-host:kbuildsycoca5`, `tool-host:kbuildsycoca6`, `tool-host:pacman`, `tool-host:pgrep`, `tool-host:pkexec`, `tool-host:pkill`, `tool-host:sh`, `tool-host:systemd-inhibit`, `tool-host:update-desktop-database`, `tool-host:zypper`, `tool:cdparanoia`, `tool:ffmpeg`, `tool:flac`, `tool:metaflac`, `tool:picard`
- `pypi:musicbrainzngs` → `svc:musicbrainz`
- `pypi:pyside6` → `runtime:qt`
- `pypi:sigstore` → `svc:sigstore`
- `ripper:cyanrip-fork` → `container:ripping`, `lib:libavcodec`, `lib:libavfilter`, `lib:libavformat`, `lib:libavutil`, `lib:libcdio`, `lib:libcdio_paranoia`, `lib:libcurl`, `lib:libmusicbrainz5`, `lib:libswresample`, `svc:fork-source`
- `ripper:cyanrip-fork-under-review` → `container:ripping`, `lib:libavcodec`, `lib:libavfilter`, `lib:libavformat`, `lib:libavutil`, `lib:libcdio`, `lib:libcdio_paranoia`, `lib:libcurl`, `lib:libmusicbrainz5`, `lib:libswresample`
- `ripper:cyanrip-upstream` → `container:ripping`, `svc:copr-barsnick-non-fed`
- `tool-host:distrobox` → `tool-host:docker`, `tool-host:podman`
- `tool:picard` → `svc:flathub`, `tool-host:flatpak`

<!-- END GENERATED: emit_bom.py -->

## Review cadence

- Before every tagged release
- After every meaningful dependency bump
- At least quarterly even when nothing changes (so retirement signals don't pile up unseen)

> **2026-09-30: this cadence has lapsed again.** No release review has been logged since the v0.6.53 catch-up (2026-09-22); v0.6.54 – v0.6.65 are unreviewed. The 2026-09-25 `sigstore` entry is a dependency addition, not a release review.
>
> **Still lapsed at the 2026-10-19 documentation audit:** no review entry covers v0.6.54 – v0.7.108. The dependencies added in that window each have a row with its sign-off (`sigstore` 2026-09-25, `pytest-xdist` 2026-09-26, `cyclonedx-python-lib` 2026-10-05), but no release in it has had the table walked against PyPI.

## Retirement trigger

Any row whose "Last upstream release" exceeds 12 months requires a review of:

1. The adapter wrapping that dependency (does it still isolate the GUI from the dep?)
2. The "Planned replacement" column (is it still the right replacement?)
3. Whether to act on the retirement now or wait

A retirement review is recorded inline below as a dated bullet so future-you can see what was decided and when.

## Retirement review log

- **2026-10-28 — Every lock regenerated with `--exclude-newer 2026-10-21T00:00:00Z`, seven days before the run (the third follow-up review of 2026-10-27, item 1).** The locks of 2026-10-27 carried their own creation date, so they took releases hours old, which the seven-day wait exists to keep out. Going back a week moved 20 pins, all to releases already in use before: PySide6 6.11.3 to 6.11.2 (inside the `>=6.11.1,<6.12` pin), python-dateutil 3.0.0 to 2.9.0.post0 (a major version back), and patch releases of certifi, coverage, hypothesis, platformdirs, pycparser, msgpack, jsonpointer, zipp and importlib-metadata. Verified: `--check` reproduces all seven locks byte for byte with uv 0.13.5; `ci.lock` installs with `--require-hashes` and `pip check` is clean; the full suite passes on that install (pytest exit 0). `tests/test_dependency_locks.py` now refuses a lock dated less than seven days before the run, and the `relock` job regenerates whenever the stored date differs from its own. **No retirements triggered.**
- **2026-10-27 — The `sbom` job, the workflow linters and the mutation sweep install from hashed locks (the follow-up review of 2026-10-27, item 5).** No dependency added or retired. `cyclonedx-bom >=7,<8` moved from `ci.yml` into pyproject's new `sbom` extra, unchanged. Two new locks with uv 0.13.5 and the same `--exclude-newer` as the rest: `build/locks/sbom.lock` (69 packages, 1,035 hashes: the runtime dependencies, the extra and the backend; every one of the 66 it shares with `ci.lock` at the same version) and `build/locks/ci-lint.lock` (zizmor 1.31.1 and shellcheck-py 0.11.0.1). actionlint-py could not join it: it has no wheel, and uv refused the resolution under `--only-binary :all:` ("has no usable wheels"). `mutation.yml` installs `ci.lock`. Verified the same day in clean CPython 3.11.17 venvs with pip 24.0: `sbom.lock` installed and `pip check` was clean, the project installed offline on top, and `cyclonedx-py environment` wrote 71 components; `ci-lint.lock` installed, `pip check` clean, `zizmor --version` 1.31.1, `shellcheck --version` 0.11.0. **No retirements triggered.**
- **2026-10-27 — The locks are reproducible, and a pull-request job checks they are what their headers say (the follow-up review of 2026-10-27).** No dependency added or retired. `build/lock-requirements.sh` resolves with `--exclude-newer` and writes the date and the uv version into every lock's header; `--check` regenerates every lock from them and diffs. Regenerated with uv 0.13.5 (the version `dependencies.yml` already pinned) and `--exclude-newer 2026-10-27T21:00:00Z`: every lock's body is byte-identical to uv 0.11.32's, only the header changed. A date of 00:00 that day would have taken platformdirs back from 4.13.6 to 4.13.5, since 4.13.6 was uploaded at 08:19 UTC, so the date is the latest whole hour before the run. Proved by deleting `certifi` from `release.lock`: `--check` printed the four missing lines and exited 1, a clean venv refused the lock with `--require-hashes` (pip 24.0: *"all requirements must have their versions pinned with =="*, for requests' certifi), and `tests/test_dependency_locks.py` passed it, which is the gap. **No retirements triggered.**
- **2026-10-27 — CI's test, lint and typecheck jobs install from a hashed universal lock (the review's follow-up to item 2.3).** No dependency added or retired. `build/locks/ci.lock` (88 packages, 1,461 hashes, uv 0.11.32) resolves the runtime dependencies, the dev extra and the build backend once for Python 3.11 and up; the three jobs install it with `--require-hashes` and then the project with `--no-index --no-deps --no-build-isolation`. Measured before adopting it: it installed with `--require-hashes` in clean venvs on CPython 3.11.17, 3.12.3, 3.13.16 and 3.14.6 (pip 24.0 to 26.1.2, upgraded by the lock to 26.2.2), 44 to 96 s each, `pip check` clean; mypy (2.3.1) is clean from it, and the full suite passed from it on 3.11 and on 3.14 with the coverage gate. Every package it shares with the AppImage lock (all 36) is pinned at the same version, which `tests/test_dependency_locks.py` now holds, so CI tests what ships. **No retirements triggered.**
- **2026-10-27 — Hashed locks for the AppImage and the CI tools (the review's follow-up to items 2.1 and 2.3; `PLANNING.md` KDD-45, A4).** No dependency added or retired. `python-appimage` moved from a literal `>=1.4,<2` in two workflows and the build script to pyproject's new `appimage` extra as `>=1.4.6,<1.5`, and `build` everywhere to the `publish` extra's `>=1.6.1,<1.7`. `build/lock-requirements.sh` now resolves four hashed locks with uv 0.11.32: `build/python-appimage/requirements.lock` (36 packages, for CPython 3.12 on manylinux_2_34_x86_64), `build/locks/release.lock` (36), `build/locks/publish.lock` (36) and `build/locks/audit.lock` (29). `release.yml`, `appimage.yml`, `publish-pypi.yml` and `ci.yml`'s `pip-audit` job install only with `--require-hashes` from them, and the builds run `--no-isolation` so the build backend comes from the lock too. Verified the same day: each tool lock installed in a clean Python 3.11 venv with pip 24.0 and `pip check` clean; `python -m build --no-isolation` and `twine check` passed on the result; `build_appimage.sh` downloaded the AppImage lock's 36 wheels with `--require-hashes` for cp312; and python-appimage 1.4.6's per-line install, replayed offline from that wheelhouse on CPython 3.12.3, installed exactly the 36 locked versions. The full AppImage build could not run in that session (GitHub's API refused the base-image lookup), so `appimage.yml` on the branch is the proof of the whole build. `pip-audit` over all four locks: no known vulnerabilities. **No retirements triggered.**
- **2026-10-27 — `actionlint-py` 1.7.12.25, `zizmor` 1.31.1 and `shellcheck-py` 0.11.0.1 added (CI linters for the workflows and shell scripts).** Asked of the owner under the deviation policy after the review of 2026-10-27 named them (items 2.5 and 3.6), and approved the same day; Vale, asked at the same time, was not. All three are MIT wheels carrying a prebuilt binary, installed only by CI from pyproject's new `ci-lint` extra, never bundled and never in the dev extra. Vetted by running each over the tree first: actionlint and zizmor report nothing on the fixed workflows, and ShellCheck's findings were fixed or annotated in the same change. **No retirements triggered.**
- **2026-10-26 — `numpy` 2.4.6 added (CTDB localisation, TASKS R43).** Asked of the owner under the deviation policy and approved at 02:19 UTC: *"numpy; record what it adds to the download."* Vetted before adding: wheels for CPython 3.11 to 3.14 on manylinux_2_28 x86-64, no transitive dependencies, and 2.4.x is the newest line that installs on our Python 3.11 floor (2.5 needs 3.12). What it adds, with the method, is on its row above: 16.6 MB wheel, 56.5 MB installed, an estimated +13.8 MB on the AppImage; 0.7.113's AppImage measured +18.3 MB over 0.7.112's, the whole release's difference. Optional at runtime: it is registered in `deps/registry.py` as optional, and its absence leaves only the localisation not determined. **No retirements triggered.**
- **2026-09-25 — `sigstore` 4.5.0 added (build-attestation check in the updater).** Asked of the maintainer as a new dependency and approved. Vetted before adding: wheels for Python 3.11 and 3.14 on manylinux x86-64 (31 wheels, about 14 MB), `pip-audit` clean over its tree, its only overlap with an existing pin is `cryptography>=42`, which our `>=50.0.0,<51` satisfies. Verified against a real release before any code depended on it: the v0.6.60 AppImage's attestation passes online and offline, and a stalled network makes its trust-root refresh hang for 120 s before failing, which is why the updater starts the refresh before the download and bounds the wait. **No retirements triggered.**
- **2026-09-22 — Catch-up review covering v0.6.48 – v0.6.53, and the cadence lapsed
  again, nine days after the entry below said why.** Six tagged releases with no
  entry, found by the pre-round-24 document audit rather than by the cadence. **No
  Python dependency moved**: `git log v0.6.47..v0.6.53 -- pyproject.toml
  build/python-appimage/requirements.txt` is empty, every row above was re-read
  against both files, and `pip-audit` was green on `main`'s CI for the v0.6.53
  merge commit. **One row was wrong, and it was the same row as last time**:
  cyanrip still named `fe4d2c4` / `+platterpus.12` / round 18, two pin-bearing
  rounds after it stopped being true — the fork's pin moved to `2cce60d`
  (`+platterpus.13`) in round 22 and round 23 re-reviewed that commit on a drive.
  Corrected here. **No retirements triggered**; `python-musicbrainzngs` stays at
  0.7.1, unmaintained, behind its adapter. **The lesson is the one the entry below
  already drew, arriving a second time**: the cyanrip row restates a fact whose
  authority lives in code (`deps/fork_source.FORK_PIN`), so it decays on every pin
  move no matter how carefully the review is done — the row now names the constant
  that is authoritative, so a reader can check it rather than trust it.

- **2026-09-13 — Catch-up review covering v0.6.21 – v0.6.47, and the cadence failed
  worse than the entry that diagnosed why.** The "before every tagged release" rule
  had lapsed across **27 tagged releases** — 3.4× the eight-release lapse the
  2026-07-28 entry was written about, and that entry had already named the cause:
  *it is prose, not a gate.* Nothing changed after it said so, which is the finding.
  **Five rows were falsified by the code they describe**, found by an audit reading
  this file against `pyproject.toml` rather than against memory: `ruff` recorded as
  `>=0.15,<1` and `mypy` as `>=1.13,<3` (both are minor-pinned, and recording the
  floating range here contradicted Critical rule #11 in the file the rule is about);
  *"no per-module exclusions remain"* for mypy, true of def-typing and false as
  written — six modules carry `disallow_any_generics = false`; `mutmut` described as
  the weekly mutation runner eight days after it was replaced by
  `scripts/mutation_sweep.py`; and **cyanrip's package source given as the COPR**,
  three KDDs after the pinned fork became the shipped backend — the most consequential
  of the five, because a reader following it installs a build that stamps every rip
  `unapproved`. All five corrected in this commit. **No retirements triggered.**
  `python-musicbrainzngs` stays frozen at 0.7.1 and unmaintained, adapter unchanged.
  **The structural lesson, since restating the rule is what did not work:** a stamp
  records when a doc was *edited*, so a document nobody edits keeps a perfect stamp
  while its prose expires — this file was gate-clean at v0.6.20 with five wrong facts
  in it. The gate that would catch this reads the *claims* against the code, not the
  footer against the tag.

- **2026-08-18 — PySide6 minor-pinned after a shipped accessibility regression.** Not a
  retirement: a *bound* correction, logged here because the review log is where "why is this
  pin what it is" has to be answerable. `>=6.7,<7` was a claim that every Qt 6.x behaves the
  same for us; 6.11.2 disproved it by dropping two `StandardKey` bindings, shipping Quit and
  Settings with no keyboard shortcut. Now `>=6.11.1,<6.12`, matched in the AppImage
  requirements and **enforced by a test** rather than stated — this log already notes that the
  review cadence "keeps failing: it is prose, not a gate", and a pin recorded only in prose has
  the same weakness. **This is the second instance of the class in this table** (see the
  `cryptography` note: a `<50` ceiling excluded the only CVE fix, so `pip-audit` resolved the
  vulnerable top and reddened CI with no code change). Both share one shape: *a version range
  is an unverified claim about behaviour.* No other dependency was changed; nothing retired.

- **2026-08-04 — `cryptography` 48.0.1 → 50.0.0 (CVE-2026-69247), and the lesson is about the *ceiling*.** `pip-audit` turned `main` red with no change to our code: `49.0.0` carries CVE-2026-69247, the fix is `50.0.0`, and our range was `>=48.0.1,<50` — **the ceiling excluded the only fix.** pip-audit resolves the *highest* version a range admits, so it picked the vulnerable top. **A ceiling that can exclude the only fix is not a safety margin**, and this is Critical rule #11 (a tool that gates CI must not float) arriving through a dependency rather than a linter: the range floated, upstream published, CI failed, and it read as a code problem. Now `>=50.0.0,<51` in `pyproject.toml` and `~=50.0` in the AppImage requirements, bumped together as the comment there instructs. **Verified before the bump rather than assumed:** installed 50.0.0 in a clean venv and exercised the exact surface `update_signing.py` uses — Ed25519 sign/verify, `from_public_bytes` raw round-trip (32 bytes), and rejection of a tampered BLAKE2b digest — then ran `tests/test_update_signing.py` + `tests/test_update_install.py` (32 tests) against it. All pass. **No retirements triggered**, and no other pin moved.

- **2026-07-28 — Catch-up review covering v0.5.5 – v0.5.12** (the whole-application audit found the "before every tagged release" cadence had lapsed for eight releases — the same gap the 2026-07-21 catch-up was created to close, so this entry is deliberately paired with a note on *why* the convention keeps failing: it is prose, not a gate). **Two dependencies were added in this window and both are already in the table with sign-off recorded:** `cryptography>=48.0.1,<50` (KDD-26, the update-signature verifier — a hard runtime dep) and the host tool `cd-paranoia` (KDD-29, the cache-defeat probe; optional — its absence leaves the verdict honestly "(unknown)"). **No retirements triggered.** python-musicbrainzngs stays frozen at 0.7.1 and unmaintained; its adapter still isolates it and the `requests`-based replacement plan is unchanged — and it is now the *only* dependency granted a mypy `ignore_missing_imports` exemption, which makes its stub-lessness visible in `pyproject.toml` rather than hidden behind a global flag. cyanrip: COPR 0.9.3.1 unchanged, upstream `master` still ahead of the last release (soft-fork runbook unchanged). No action needed.

- **2026-07-21 — Pre-release review for v0.5.0** (the "before every tagged release" cadence; v0.5.0 merged and released the same day as the catch-up below). **No new dependencies:** the whole v0.5.0 feature batch (overread toggle, library auto-move, per-track progress bars, cross-FS naming warning, accessibility completion) and the follow-on v0.5.x work (MP3 VBR-quality knob, cue-sheet button) are built entirely on the standard library (`shutil`, `pathlib`, `threading`, `subprocess`) plus the already-pinned PySide6 — `pyproject.toml`'s dependency set is byte-unchanged from v0.4.24, and the only new import across the cycle is stdlib `threading` (the library-move daemon). The table walked the same day (catch-up entry below) still holds: every pin healthy and current, mypy's `<3` bound load-bearing, python-musicbrainzngs still frozen at 0.7.1 (adapter isolates it; `requests` replacement plan unchanged), cyanrip COPR 0.9.3.1 unchanged. No retirements triggered; no action needed.
- **2026-07-21 — Catch-up review covering v0.4.19–v0.4.24** (the 2026-07-21 docs audit found no review had been logged for these six releases; maintainer chose a catch-up over relaxing the cadence). Walked the table against live PyPI: **every pin is healthy and current** — PySide6 6.11.1, tomli-w ≤1.2.0, python-appimage 1.4.5, build 1.5.0 (bound `>=1,<2` newly applied at the install sites this day), pytest 9.1.1 (pin `>=8,<10`), ruff 0.15.x, pytest-cov 7.1.0, hypothesis 6.x, **mypy 2.3.0 — the Dependabot-widened `>=1.13,<3` bound is now load-bearing** (1.x → 2.x happened upstream). python-musicbrainzngs remains frozen at 0.7.1 (unmaintained; adapter still isolates it; `requests` replacement plan unchanged). **Dependency changes across v0.4.19–v0.4.24:** mypy added as an approved dev dep (2026-07-08) and later widened to `<3` by Dependabot; `pip-audit` runs in CI as a tool, not a project dep; mutmut now runs weekly in CI (still deliberately unpinned); every GitHub Action was SHA-pinned and Dependabot keeps the pins bumped (checkout 7.0.0, setup-python 6.3.0, upload-artifact 7.0.1, attest-build-provenance v4). cyanrip: COPR 0.9.3.1 unchanged; upstream `master` live but releases stalled (see `docs/cyanrip-fork.md` Part A §6 / the soft-fork runbook). No retirements triggered; no action needed beyond the `build` pin.
- **2026-07-07 — Review for the v0.4.17 / v0.4.18 releases.** whipper is **removed**, not merely flagged (KDD-18, 2026-06-30): cyanrip is the sole ripping backend, invoked via the host-exported `~/.local/bin/cyanrip`. Table is current — cyanrip 0.9.3.1 (COPR `barsnick/non-fed`, Fedora 42–44), flac/metaflac 1.5.0, ffmpeg 8.1.x, PySide6 6.11.1, python-musicbrainzngs 0.7.x (still unmaintained; adapter still isolates it; `requests`-based replacement plan unchanged). No new dependencies added by v0.4.17 (CTDB CRC math is stdlib `zlib`) or v0.4.18 (version provenance reads the existing dependency probe). No action taken.
- **2026-06-02 — Pre-release review for v0.1.0 (first public release).** Walked the table per the "before every tagged release" cadence. No dependency changes since the last review. PySide6 (6.11.1), tomli-w, python-appimage all current. whipper + musicbrainzngs remain unmaintained but functional; adapters still isolate them; replacement plans (`cyanrip`, `requests`-based MB client) unchanged. Separately confirmed during the EAC-parity investigation (see `docs/archive/upstream-modification-investigation.md`) that the path off whipper, if forced, is the `cyanrip` adapter — **not** a maintained whipper fork. No action taken.
- **2026-05-28 — Real-user testing on Bazzite surfaced whipper deprecation canaries.** Whipper 0.10.0 is now 5 years old and showing real friction on current distros:
  - **`pkg_resources` removal countdown.** Whipper imports `pkg_resources` from setuptools, which prints a deprecation warning under setuptools 80.x. Setuptools 81 (already released as of the warning's "2025-11-30" cutoff) will remove `pkg_resources` entirely. When Fedora ships setuptools 81+, whipper will stop running. Worth a `cyanrip` migration plan but not an emergency yet — Fedora 44 still has setuptools 80.x.
  - **`whipper cd info` is broken for discs not in MB/FreeDB.** The `_CD.do()` method requires `--unknown` to be set when no metadata is found, but the `Info` subcommand doesn't accept `--unknown` (only `Rip` does). Adapter caught this with a fallback that returns an empty DiscInfo, but it's an upstream bug. Real fix would require patching whipper.
  - **Decision:** continue with whipper for v1; flag both issues in code comments on `WhipperHostExportedImpl`. The adapter pattern (Critical Rule #1) makes the `cyanrip` migration tractable when it becomes necessary.

---

*Last updated for Platterpus v0.7.114.*
