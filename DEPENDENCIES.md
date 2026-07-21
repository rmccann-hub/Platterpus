# Dependencies

All dependencies, with last upstream release date and replacement plan. Reviewed on the cadence below.

## Python packages (bundled in the AppImage)

| Name | Pinned version | Last upstream release | License | Status | Planned replacement |
|---|---|---|---|---|---|
| PySide6 | `>=6.7,<7` (current: 6.11.1) | 2026-05-13 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | Active | — |
| musicbrainzngs | `==0.7.1` | 2020-01-11 | BSD-2-Clause (one file ISC) | Unmaintained (>12mo) | direct `requests` against `https://musicbrainz.org/ws/2/` via `MusicBrainzClient.RequestsJsonImpl` |
| tomli-w | `>=1.0,<2` (current: 1.2.0) | 2025-01-15 | MIT | Active | — (stdlib `tomllib` is read-only, `tomli-w` is the canonical writer) |
| cryptography | `>=41,<47` (pyproject); AppImage bundles `~=44.0`; exact version fixed by `requirements.lock` | (per PyPI) | Apache-2.0 OR BSD-3-Clause | Active | — (Ed25519 verification of a release's minisign signature — the in-app updater's authenticity gate, `src/platterpus/update_signing.py`. Verify-only; no secret key in the app. The BLAKE2b prehash uses stdlib `hashlib`, so only the Ed25519 primitive is needed — stable since cryptography 2.6.) |

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

**Cache-defeat note on the cyanrip row above:** cyanrip's engine,
**libcdio-paranoia**, *attempts* cache defeat on every rip (readahead
cache-exhaustion reads plus FUA where the drive advertises support) — this
comes bundled inside cyanrip itself, so it adds no dependency of its own.
It is **best-effort and drive-dependent**; nothing confirms at runtime that
defeat actually happened on a given drive, so we report the EAC-equivalent
field as `(unknown)`, never a measured `Yes` (PLANNING.md KDD-25). There is
**no standalone `cd-paranoia`/`cdparanoia` CLI tool in our dependency table**
today — libcdio-paranoia is only ever used as a library linked *inside*
cyanrip, never invoked by us directly. Adding the standalone `cd-paranoia -A`
tool (which could give a real *measured* cache-defeat verdict) would be a new
row here plus explicit deviation-policy sign-off ("adding a dependency not
listed in DEPENDENCIES.md" is must-ask territory) and hardware validation
before the result could be trusted — deferred, not rejected.

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

- **2026-07-21 — Pre-release review for v0.5.0** (the "before every tagged release" cadence; v0.5.0 merged and released the same day as the catch-up below). **No new dependencies:** the whole v0.5.0 feature batch (overread toggle, library auto-move, per-track progress bars, cross-FS naming warning, accessibility completion) and the follow-on v0.5.x work (MP3 VBR-quality knob, cue-sheet button) are built entirely on the standard library (`shutil`, `pathlib`, `threading`, `subprocess`) plus the already-pinned PySide6 — `pyproject.toml`'s dependency set is byte-unchanged from v0.4.24, and the only new import across the cycle is stdlib `threading` (the library-move daemon). The table walked the same day (catch-up entry below) still holds: every pin healthy and current, mypy's `<3` bound load-bearing, python-musicbrainzngs still frozen at 0.7.1 (adapter isolates it; `requests` replacement plan unchanged), cyanrip COPR 0.9.3.1 unchanged. No retirements triggered; no action needed.
- **2026-07-21 — Catch-up review covering v0.4.19–v0.4.24** (the 2026-07-21 docs audit found no review had been logged for these six releases; maintainer chose a catch-up over relaxing the cadence). Walked the table against live PyPI: **every pin is healthy and current** — PySide6 6.11.1, tomli-w ≤1.2.0, python-appimage 1.4.5, build 1.5.0 (bound `>=1,<2` newly applied at the install sites this day), pytest 9.1.1 (pin `>=8,<10`), ruff 0.15.x, pytest-cov 7.1.0, hypothesis 6.x, **mypy 2.3.0 — the Dependabot-widened `>=1.13,<3` bound is now load-bearing** (1.x → 2.x happened upstream). python-musicbrainzngs remains frozen at 0.7.1 (unmaintained; adapter still isolates it; `requests` replacement plan unchanged). **Dependency changes across v0.4.19–v0.4.24:** mypy added as an approved dev dep (2026-07-08) and later widened to `<3` by Dependabot; `pip-audit` runs in CI as a tool, not a project dep; mutmut now runs weekly in CI (still deliberately unpinned); every GitHub Action was SHA-pinned and Dependabot keeps the pins bumped (checkout 7.0.0, setup-python 6.3.0, upload-artifact 7.0.1, attest-build-provenance v4). cyanrip: COPR 0.9.3.1 unchanged; upstream `master` live but releases stalled (see `docs/ripper-engine-strategy.md` §6 / the soft-fork runbook). No retirements triggered; no action needed beyond the `build` pin.
- **2026-07-07 — Review for the v0.4.17 / v0.4.18 releases.** whipper is **removed**, not merely flagged (KDD-18, 2026-06-30): cyanrip is the sole ripping backend, invoked via the host-exported `~/.local/bin/cyanrip`. Table is current — cyanrip 0.9.3.1 (COPR `barsnick/non-fed`, Fedora 42–44), flac/metaflac 1.5.0, ffmpeg 8.1.x, PySide6 6.11.1, python-musicbrainzngs 0.7.x (still unmaintained; adapter still isolates it; `requests`-based replacement plan unchanged). No new dependencies added by v0.4.17 (CTDB CRC math is stdlib `zlib`) or v0.4.18 (version provenance reads the existing dependency probe). No action taken.
- **2026-06-02 — Pre-release review for v0.1.0 (first public release).** Walked the table per the "before every tagged release" cadence. No dependency changes since the last review. PySide6 (6.11.1), tomli-w, python-appimage all current. whipper + musicbrainzngs remain unmaintained but functional; adapters still isolate them; replacement plans (`cyanrip`, `requests`-based MB client) unchanged. Separately confirmed during the EAC-parity investigation (see `docs/archive/upstream-modification-investigation.md`) that the path off whipper, if forced, is the `cyanrip` adapter — **not** a maintained whipper fork. No action taken.
- **2026-05-28 — Real-user testing on Bazzite surfaced whipper deprecation canaries.** Whipper 0.10.0 is now 5 years old and showing real friction on current distros:
  - **`pkg_resources` removal countdown.** Whipper imports `pkg_resources` from setuptools, which prints a deprecation warning under setuptools 80.x. Setuptools 81 (already released as of the warning's "2025-11-30" cutoff) will remove `pkg_resources` entirely. When Fedora ships setuptools 81+, whipper will stop running. Worth a `cyanrip` migration plan but not an emergency yet — Fedora 44 still has setuptools 80.x.
  - **`whipper cd info` is broken for discs not in MB/FreeDB.** The `_CD.do()` method requires `--unknown` to be set when no metadata is found, but the `Info` subcommand doesn't accept `--unknown` (only `Rip` does). Adapter caught this with a fallback that returns an empty DiscInfo, but it's an upstream bug. Real fix would require patching whipper.
  - **Decision:** continue with whipper for v1; flag both issues in code comments on `WhipperHostExportedImpl`. The adapter pattern (Critical Rule #1) makes the `cyanrip` migration tractable when it becomes necessary.

---

*Last updated for Platterpus v0.5.0.*
