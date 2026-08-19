# Dependencies

All dependencies, with last upstream release date and replacement plan. Reviewed on the cadence below.

## Python packages (bundled in the AppImage)

| Name | Pinned version | Last upstream release | License | Status | Planned replacement |
|---|---|---|---|---|---|
| PySide6 | `>=6.11.1,<6.12` (current: 6.11.1; CI resolves 6.11.2) — **minor-pinned 2026-08-18**, was `>=6.7,<7`. 6.11.2 stopped resolving `QKeySequence.StandardKey.Quit` and `.Preferences`, so the Quit and Settings menu items shipped with **no keyboard shortcut** — a WCAG 2.1.1 regression from somebody else's release with no change to our code. Reproduced on one machine, same `QT_QPA_PLATFORM=offscreen`, only the wheel changed. `main_window.standard_shortcut` now checks Qt's answer instead of trusting it, and the suite is run against **both** wheels before a push touching Qt behaviour. The bound is the MINOR, not the patch: 6.11.x still flows (Qt's security fixes with it, and 6.11.2 is handled correctly and proven green), while a minor bump becomes a deliberate commit that re-runs the gate. `build/python-appimage/requirements.txt` expresses the same range as `~=6.11.1` — that file is what SHIPS — and `tests/test_gating_tools_are_pinned.py` fails if the two disagree. Same class as the `cryptography` ceiling incident below. | 2026-05-13 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | Active | — |
| musicbrainzngs | `==0.7.1` | 2020-01-11 | BSD-2-Clause (one file ISC) | Unmaintained (>12mo) | direct `requests` against `https://musicbrainz.org/ws/2/` via `MusicBrainzClient.RequestsJsonImpl` |
| tomli-w | `>=1.0,<2` (current: 1.2.0) | 2025-01-15 | MIT | Active | — (stdlib `tomllib` is read-only, `tomli-w` is the canonical writer) |
| cryptography | `>=50.0.0,<51` (pyproject); AppImage bundles `~=50.0`; exact version fixed by `requirements.lock` **once that lock exists** — it is not committed yet, so today's build is a version-pinned online install (`build_appimage.sh` branches on the file) | (per PyPI) | Apache-2.0 OR BSD-3-Clause | Active | — (Ed25519 verification of a release's minisign signature — the in-app updater's authenticity gate, `src/platterpus/update_signing.py`. Verify-only; no secret key in the app. The BLAKE2b prehash uses stdlib `hashlib`, so only the Ed25519 primitive is needed — stable since cryptography 2.6. **Floor is the CVE-2026-69247 fix (50.0.0)**, raised from the GHSA-537c-gmf6-5ccf floor (48.0.1) on 2026-08-04 — 49.0.0 carries CVE-2026-69247 and the old `<50` ceiling *excluded the only fix*, so `pip-audit` resolved the vulnerable top of the range and turned CI red with no change to our code. Keep the floor on the latest patched release, and when raising a floor check the CEILING admits it. Verified against 50.0.0 before the bump: the Ed25519 sign/verify path, raw-public-bytes round-trip, tampered-message rejection, and `tests/test_update_signing.py` + `tests/test_update_install.py` (32 tests) all pass.) |

## Python packages (dev / build only — not bundled)

| Name | Pinned version | Last upstream release | License | Status | Planned replacement |
|---|---|---|---|---|---|
| python-appimage | `>=1.4,<2` (current: 1.4.5) | 2025-07-02 | GPL-3.0 (package itself); MIT for files under `python_appimage/data` | Active | `appimage-builder` only if `python-appimage` cannot express a required build step (CLAUDE.md Critical Rule #2). The recipe must avoid `appimage-builder`-specific features so swapping back is cheap. |
| build | `>=1,<2` (pinned in `release.yml`/`appimage.yml`/`build_appimage.sh`, 2026-07-21) | (per PyPI at first install) | MIT | Active | — (PEP 517 build frontend; used by `build/build_appimage.sh`) |
| pytest | `>=8,<10` | (per PyPI at first install) | MIT | Active | — |
| ruff | `>=0.15,<1` | (per PyPI at first install) | MIT | Active | — (linter + formatter; CI runs `ruff check` + `ruff format --check`. Rules `E,F,W,I,B,UP`, `E501` off. Config in `pyproject.toml`.) |
| pytest-cov | `>=5` | (per PyPI at first install) | MIT | Active | — (dev/test only; CI runs branch coverage with `--cov-fail-under=91` (ratchets up). See [docs/testing.md](docs/testing.md).) |
| hypothesis | `>=6` | (per PyPI at first install) | MPL-2.0 | Active | — (dev/test only; property-based tests in `tests/test_parsers_property.py`. MPL-2.0 is fine — test-time tool, not linked/distributed.) |
| mutmut | not installed (unpinned by design) | — | BSD-3-Clause | Active | — (dev/test only; mutation-testing **audit**, not a CI gate — see [docs/testing.md](docs/testing.md) §7. Runs weekly in CI via `.github/workflows/mutation.yml` (non-gating) and on demand via `pipx run mutmut`.) |
| mypy | `>=1.13,<3` | (per PyPI at first install) | MIT | Active | — (dev/test only; static type-checking. CI `typecheck` job runs `mypy` on every push/PR. **Strict def-typing (`disallow_untyped_defs`/`disallow_incomplete_defs`) enforced across the entire package since 2026-07-19/20** — the Qt UI mixin layer, the last hold-out, was brought in via the `MainWindowShared` typing seam (`docs/architecture.md` §3.6); no per-module exclusions remain. Approved as a new dev dep 2026-07-08.) |

## System dependencies (user-system, surfaced via the dependency subsystem or the setup wizard)

> Most rows here are probed by the dependency subsystem (`deps/`). cyanrip is probed (`check_cyanrip`) and is always provisioned by the host-setup wizard (`deps/host_setup.py`).
>
> **whipper was removed entirely on 2026-06-30 (KDD-18 amendment) — cyanrip is the sole backend.** The old whipper row is retained below struck-through as the record; nothing installs, exports, or probes whipper anymore.

| Name | Where it comes from | Version constraint | Status | Replacement plan |
|---|---|---|---|---|
| cyanrip (**the** ripping backend, KDD-18) | Distrobox container `ripping`, host-exported to `~/.local/bin/cyanrip`. **Package source: COPR `barsnick/non-fed`** (GPG-checked; cyanrip 0.9.3.1 built for Fedora 42–44 + rawhide) — verified 2026-06-09 that neither Fedora nor RPM Fusion packages cyanrip. The wizard writes the standard COPR `.repo` stanza itself (version-generic `$releasever/$basearch`), so no `dnf copr` plugin is needed. | `>=0.9.0` | Active (v0.9.3.1, 2024-06-05; LGPL-2.1 — fine: subprocess, no linking) | If the COPR disappears: meson source build inside the container — all build deps are in Fedora proper (`ffmpeg-free-devel`, `libcdio-paranoia-devel`, `libmusicbrainz5-devel`, `libcurl-devel`). See [docs/archive/ecosystem-audit-2026-06.md](docs/archive/ecosystem-audit-2026-06.md). |
| ~~whipper~~ (**removed 2026-06-30**) | ~~Distrobox container, host-exported to `~/.local/bin/whipper`~~ | — | **Removed.** Stalled since v0.10.0 (2021), `pkg_resources` cliff, and the >587 read-offset bug that failed tracks on the BDR-209D. cyanrip replaced it with no functional loss (KDD-18 amendment). | — |
| metaflac | Distrobox container `ripping` (same export route) | (whatever ships with the container's `flac` package) | Active (FLAC project) | — |
| flac (decoder) | Host, **optional** — used by CTDB verify to decode FLAC→PCM if present; the feature degrades with a clear message if absent (decision 2026-06-03). No required dependency added. | any | Active (FLAC project) | — |
| ffmpeg | Host/container, **optional** — the single encoder for the **Output format** feature (KDD-22): transcodes the FLAC master to WavPack/MP3/WAV when the user picks a non-FLAC format. Registered in `deps/registry.py`; absent only disables non-FLAC output (FLAC rips are unaffected, and the FLAC master is always kept, so a missing ffmpeg never costs audio). Already present wherever cyanrip is (cyanrip is built on FFmpeg). Shipped 2026-06-26. | `>=4.0` | Active (FFmpeg project) | — (LGPL/GPL build; invoked as a subprocess, never linked) |
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
Set up drive → Analyse cache and recorded per drive. This is the maintainer-approved
new dependency (deviation-policy sign-off given 2026-07-24). The honesty rule from
KDD-25 still holds: an inconclusive probe keeps `(unknown)`, never a forged `Yes`.
The exact `-A` verdict wording is hardware-tuned against the first real capture
(KDD-29); until then the parser stays conservative.

## System dependencies (build/runtime requirements inside the Distrobox container) — HISTORICAL (whipper-era)

> **HISTORICAL — whipper was removed on 2026-06-30 (KDD-18 amendment); the rows below were whipper-specific and are no longer current requirements.** cyanrip (the sole backend now) is installed from the COPR by the host-setup wizard and pulls its own runtime deps; it needs neither `python3-setuptools` nor `cdrdao`. Kept as the record of what the whipper-in-container era required.

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

## Review cadence

- Before every tagged release
- After every meaningful dependency bump
- At least quarterly even when nothing changes (so retirement signals don't pile up unseen)

## Retirement trigger

Any row whose "Last upstream release" exceeds 12 months requires a review of:

1. The adapter wrapping that dependency (does it still isolate the GUI from the dep?)
2. The "Planned replacement" column (is it still the right replacement?)
3. Whether to act on the retirement now or wait

A retirement review is recorded inline below as a dated bullet so future-you can see what was decided and when.

## Retirement review log

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

*Last updated for Platterpus v0.6.18.*
