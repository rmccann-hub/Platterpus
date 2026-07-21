# Manual & release testing

> **Who this is for.** The maintainer running a full pre-release check, and the
> external testers coming on board. These are the validations that **can't run
> in CI** — they need a real CD + drive, a desktop session, or a maintainer
> credential.
>
> Two halves, in order of how you'll use them:
> - **Parts 0–D + Reporting** — the end-to-end *release/acceptance run*: a clean
>   uninstall → fresh install → rip → verify cycle, the **EAC output-parity**
>   check, and the **distribution + problem-permutation matrices** to spread
>   across testers.
> - **Single-feature cases (Test 1–14)** — the deep, individually-gated cases
>   (CTDB verify CRC, PyPI go-live, the cyanrip parity run, and the
>   multi-format output proof). Run one at a time and record the result.
>   The whipper-era cases were **rewritten for the cyanrip-only reality on
>   2026-07-21** (maintainer-approved): Test 3 is now the wizard success-screens
>   capture (absorbing Test 4, retired), Test 8 is the cyanrip parity record,
>   Test 10 is retired (feature inert under the sole backend), A8 is retired
>   into A6, and Tests 12–14 add the newer hardware-gated features. Test
>   numbers are stable IDs — retired numbers are kept as one-line stubs so
>   cross-references stay valid.
>
> Everything here is already *implemented* (or, for upstream-blocked items,
> *decided*) — these tests confirm reality matches intent and capture the real
> output the docs still need.
>
> **Status marker** in each case heading (same convention as `TASKS.md`):
> `[ ]` = not yet run · `[x]` = passed · `[?]` = failed / needs rework (note it
> in the **Record** box).

## 0. Before you start — record your environment

Capture this once per tester/run; paste it at the top of every report:

```
Distro + version : (e.g. Bazzite 41 / Fedora Silverblue 41 / Ubuntu 24.04)
Desktop          : (KDE Plasma 6 / GNOME 46 / …)
CPU arch         : x86_64   (the only supported arch today)
Drive            : (vendor + model, e.g. PIONEER BD-RW BDR-209D)
Install method   : AppImage  (or pipx / source)
App version      : (Help → About, or `platterpus --version`)
Container backend: podman ___  / docker ___  (distrobox list)
```

A run is only meaningful with the **log** attached:
`~/.local/share/platterpus/log.txt` (and the rip's `.log` next to the FLACs).
For a hard-to-reproduce issue, turn on **Settings → Debug logging** first — it
raises the log file to verbose DEBUG.

> ⚠️ **Never put ripped audio in the repo** (`CLAUDE.md` Critical rule #8). These
> tests rip and re-encode real commercial CDs — keep all `.flac`/`.wav`/`.mp3`
> output under `~/Music/…` or a temp dir, **never** inside the working tree, and
> never `git add` one even temporarily. When a test asks you to attach evidence,
> attach the **log** (and per-track CRCs), never the audio.

### 0.1 — [ ] Preflight / "doctor" (no CD needed) — do this FIRST

Before inserting a disc, run the first-pass environment check:

```
platterpus --doctor        # or: python scripts/preflight.py
```

It verifies everything the rip pipeline needs *except* the disc read: the
Distrobox→cyanrip routing reaches the backend, the drive is detected +
accessible, the dependency tools are present, and the host can reach MusicBrainz
/ Cover Art Archive / CTDB. **Expected:** a report ending `Preflight: … ready`
(exit 0). Any `✗` blocker means a normal rip won't work yet — fix it (the report
gives a hint) before continuing. This knocks out the boring environmental
failures; it does **not** replace the bit-perfect hardware proof below.

---

## Part A — Full clean-cycle acceptance run

Do these in order. Each step has an **action**, the **expected** result, and a
box. Stop and file a report at the first hard failure.

### A1 — [ ] Uninstall to a clean slate
From a checkout (`git pull` first so you have the latest `uninstall.sh`):
```bash
cd ~/Platterpus
git pull
bash uninstall.sh --full --yes
```
*Expected:* removes the AppImage in `~/Applications`, menu/desktop entries, the
`ripping` container, host-exported `whipper`/`metaflac`/`cyanrip`, `whipper.conf`,
Picard, and the app's config + logs. **Never** your music. (No checkout? Use the
app's **Tools → Uninstall Platterpus…** and tick both boxes — container +
whipper.conf. The AppImage removes itself as part of the run when launched from one.)

### A2 — [ ] Confirm the slate is clean
```bash
ls ~/Applications/platterpus* 2>/dev/null;            echo "---"
ls ~/.local/bin/whipper ~/.local/bin/cyanrip 2>/dev/null; echo "---"
distrobox list | grep ripping;                          echo "---"
ls ~/.config/platterpus ~/.config/whipper 2>/dev/null
```
*Expected:* only the `---` separators print (everything empty). Anything left →
`rm -rf` it (e.g. a stray `~/.config/whipper/whipper.conf.bak`) and note it.

### A3 — [ ] Fresh install (AppImage — the end-user path)
```bash
cd ~/Downloads
wget https://github.com/rmccann-hub/Platterpus/releases/latest/download/platterpus-x86_64.AppImage
chmod +x platterpus-x86_64.AppImage
./platterpus-x86_64.AppImage
```
*Expected:* the window appears **immediately** and **stays responsive** — no
"Not Responding" even while the container is cold (the launch probes run off the
GUI thread). On a FUSE-less host, run with `APPIMAGE_EXTRACT_AND_RUN=1`.

### A4 — [ ] First-run offers
*Expected, in order:* (1) "Add to your applications menu?" — say **Yes**; the
file moves to `~/Applications` and a menu entry appears. (2) The **host-setup
wizard** — say Yes; it builds the `ripping` container + installs cyanrip/flac
(and metaflac) and exports them. **~20–40 min** the
first time (≈600 MB image pull); one polkit password prompt only if podman/
distrobox needs installing (none on Bazzite/Silverblue). (3) Picard offer — your
call. Record any wizard step that fails **verbatim**.

### A5 — [ ] Drive setup (read offset)
**Tools → Set up drive…** *Expected:* the offset is **pre-filled** from the
AccurateRip drive list (e.g. **+667** for a BDR-209D) — one **Save offset**
click, no disc. If your drive isn't in the list: look it up at
accuraterip.com/driveoffsets.htm and **type it** into the manual field, then
Save. (cyanrip has no on-disc offset detection, so there is no "Detect" button —
the value comes from the list or manual entry.)

### A6 — [ ] Rip a recognized CD
Insert a commercial CD → it's identified via MusicBrainz, the track list fills →
**Start rip**.
*Expected:* progress bars + current-track move; on finish the status reads a
**fidelity verdict** (*"✓ Bit-perfect: all N tracks verified against AccurateRip"*). Files
land under your output folder, tagged, with embedded cover art. Open the saved
`.log` (View log) — every track **Test CRC == Copy CRC**. (This is the default
**FLAC** output; to validate the **WavPack / MP3 / WAV** output formats, see
**Test 11**.)

### A7 — [ ] EAC output-parity check  ⭐ (the headline)
If you have an EAC log for this exact disc + drive (we have one for *The Police —
Every Breath You Take: The Classics* on a BDR-209D at
`output_reference/EAC_flac/eac_baseline_police_classics.log`), compare. See **Part B** for
the full procedure, the per-track CRC baseline, and what "exact" means.

### A8 — retired (2026-07-21)

*(Was "cyanrip backend rip" — a backend-switch step from when whipper was the
default. cyanrip is the sole backend (KDD-18), so A6 **is** the cyanrip rip and
carries this step's expectations: cover art fetched from the Cover Art Archive,
the cyanrip fidelity verdict. Number kept so A9+/Part C references stay valid;
full text in git history. Parity checklist: **Test 8**.)*

### A9 — [ ] Edge discs
- **Unknown disc / offline:** *File → Rip as Unknown Album…* → placeholders →
  Start → FLACs tagged from what you typed, cover art fetched if a release was
  picked. *Expected:* no MusicBrainz TTY prompt ever surfaces. (Picard
  auto-launch flow: **Test 6**.)
- **CD-R (home-burned):** rips with no switch — cyanrip is CD-R-native (the
  whipper-era "Continue on CD-R" toggle was removed with KDD-18).

### A9b — [ ] Cancel / crash / new-disc edge cases (0.4.12, HARDWARE-GATED)
- **New-disc auto-detect:** with the app idle (no rip running), eject and insert
  a different CD. *Expected:* within ~2–3 s the app auto-rescans (disc info →
  MusicBrainz) with **no** click on “Rescan disc”. Then: start a rip, **Cancel**
  it (the drive force-stops and *ejects*), insert a new CD → *Expected:* the new
  disc is auto-detected. (Backed by `drive_media.probe_disc_status` /
  `MediaWatcher`; the ioctl is the hardware-gated piece — validate here.)
- **Incremental report on a hard stop:** start a rip; after a few tracks finish,
  **kill the app hard** (`kill -9` the process, or pull power). *Expected:* the
  album folder still has a `<album>.platterpus.json` with `outcome.status:
  "in_progress"` and the tracks completed so far (not an empty/missing report).
- **Status timestamp:** during any rip, the status line reads `HH:MM:SS · <phase>`
  and the time advances as phases change.

### A10 — [ ] In-app update (when a newer release exists)
**Help → Check for updates.** *Expected:* if newer, it downloads (cancellable
progress), shows phase labels (Downloading → Verifying → *"Installing — almost
done, please don't close…"*), verifies the checksum, installs to `~/Applications`,
and offers to **restart**. The window must **not** go "Not Responding," and
Cancel/✕ must stay responsive throughout (the 2026-06-13 freeze fixes).

### A11 — [ ] Uninstall again (clean removal)
Repeat A1 + A2. *Expected:* fully clean, music untouched, no leftovers. (For the
deeper no-terminal uninstaller verification, see **Test 9**.)

---

## Part B — EAC output parity (making the rip *exact*)

The product goal is a rip whose **audio is bit-identical to EAC's**, provable by
matching CRCs. UI differences don't matter; the bytes do.

**What must match the EAC baseline (`output_reference/EAC_flac/eac_baseline_police_classics.log`):**

| Field | EAC baseline | Where ours shows it |
|---|---|---|
| Per-track **CRC32** | the table below | cyanrip **EAC CRC32** (same algorithm as EAC's Copy CRC) |
| Read **offset** | `667` | Settings / drive setup; printed in our `.log` |
| AccurateRip | confidence per track | our rip-log panel + `.log` |

**The per-track CRC32 baseline** (ground truth — a cyanrip rip of this disc
must reproduce these EXACTLY; EAC's "Copy CRC" and cyanrip's "EAC CRC32" are
the same algorithm, as was whipper's Test/Copy CRC historically). Disc: *The Police —
Every Breath You Take: The Classics*, EAC V1.8 on a BDR-209D at offset +667:

| Track | EAC CRC32 | | Track | EAC CRC32 |
|---|---|---|---|---|
| 1 | B0D122E7 | | 8 | D723C1B0 |
| 2 | 985AAE32 | | 9 | 6F6E4A5F |
| 3 | 59D352DD | | 10 | 3A33519F |
| 4 | 60D796AE | | 11 | 56BFC63D |
| 5 | E0036697 | | 12 | D78CEAEF |
| 6 | B32769D6 | | 13 | DA6A4DAF |
| 7 | CCBFF669 | | 14 | 787BA2D6 |

**Procedure:**
1. Rip the disc with our app (A6), or run `python3 scripts/eac_parity.py
   output_reference/EAC_flac/eac_baseline_police_classics.log <your rip's .log>`
   for the same comparison in one command.
2. For each track, compare the `.log`'s EAC CRC32 to the table above.
3. Record the comparison in the **Test 8** Record box.

**They should match exactly** when the rip is bit-perfect. If a track's CRC
differs, it's almost always one of these *parity variables* — check them before
assuming a bug:
- **Read offset** — must be the EAC value (**+667** here). A wrong offset shifts
  every sample → every CRC differs.
- **Gap/pregap handling** — EAC here used **"Appended to previous track."**
  cyanrip's **default already matches this** — verified against upstream (README
  §"Pregap handling", 0.9.3.1 and master): *"By default, track 1 pregap is
  ignored, while any other track's pregap is merged into the previous track.
  This is identical to EAC's default behaviour."* We deliberately pass **no
  `-p` flag**, so the rip uses that EAC-equivalent default (which is exactly how
  the committed 12/14 parity proof was ripped). So a clean track's CRC differing
  while the offset is right is **not** expected from gap handling on this path;
  investigate the offset or a disc defect first. (cyanrip's `-p` is a *per-track*
  override — `-p track_number=action`, actions `default`/`merge`/`drop`/`track` —
  not a global switch; `drop` deletes pregap audio and breaks cyanrip's
  no-discontinuities guarantee, so it isn't an archival option.) Tracks with no
  surrounding gap (most of a typical album) are unaffected either way.
- **Lead-in/out overread** — EAC: **No** overread here. Keep "Force overread"
  off to match.
- **Null samples in CRC** — EAC: **Yes**. (whipper/cyanrip CRC the decoded PCM,
  which includes nulls — consistent.)
- **A genuine disc defect** — e.g. our reference disc's **track 5** mismatches in
  *every* tool (CTDB: "differs in 3 samples"). A track that differs everywhere is
  the disc, not the ripper — don't chase it.

> **Known reference facts (banked from the EAC baseline):** track 3 rips *clean*
> in EAC, so whipper's historical track-3 failure was its **>587-offset bug**,
> not disc damage — cyanrip should clear it. Track 5 is a real disc quirk.

If every CRC matches → **output parity achieved** for this disc (the committed
state is 12/14 — T3 read-instability + T5 disc defect — see Test 8). Repeat on a few more discs (a clean pressing, a multi-disc set, a disc
with a known pregap) to generalize.

---

## Part C — Linux distribution matrix

Spread these across testers. The GUI needs Qt 6; ripping runs in a Fedora
container, so the host only needs Distrobox + a container backend. Minimum per
distro: **A3 (install) + A4 (wizard) + A6 (one rip)**.

| Distro family | Install path notes | Must pass | Priority |
|---|---|---|---|
| **Bazzite / Fedora Silverblue** | podman + distrobox preinstalled; zero host prompts | A1–A11 (primary target) | ⭐ highest |
| **Fedora Workstation / RHEL / CentOS** | dnf installs distrobox/podman if missing | A3–A6 | high |
| **Ubuntu / Debian 24.04+** | installer adds `podman` (distrobox only *recommends* it) | A3–A6 | high |
| **Linux Mint / Pop!_OS / elementary** | Ubuntu-based — same as Ubuntu | A3–A6 | medium |
| **Arch / Manjaro / EndeavourOS** | pacman installs distrobox + podman | A3–A6 | medium |
| **openSUSE Leap / Tumbleweed** | zypper installs distrobox + podman | A3–A6 | medium |
| **Other / older** | Distrobox's official installer; ensure podman/docker first | A3–A6, note fallbacks | low |

Record for each: did the window launch responsively (A3), did the wizard finish
(A4), did one rip complete with a bit-perfect AccurateRip verdict (A6)?

---

## Part D — Problem-permutation matrix

Force each failure mode and confirm the app behaves as below (degrades loudly +
recovers, never hangs or silently fails). One row = one test.

| # | Force this | Expected behaviour | Recovery |
|---|---|---|---|
| D1 | **No drive / no disc** | Drive picker shows "(no drives found)"; *Tools → Diagnose drive access* explains why | insert disc / fix below |
| D2 | **Drive not readable** (user not in the drive's group) | Diagnosis names the exact `sudo usermod -aG … $USER` fix | run it, log out/in |
| D3 | **No FUSE** (minimal host) | AppImage won't mount | run `APPIMAGE_EXTRACT_AND_RUN=1 ./…AppImage` |
| D4 | **podman/distrobox absent** | Wizard offers to install them (one polkit prompt) | accept |
| D5 | **Container has no network** during a known rip | GUI auto-heals: re-rips as `--unknown`, tags from the on-screen metadata | none needed |
| D6 | **Cold container** (first launch after boot) | window appears + stays responsive; probes finish in the background | wait a few seconds |
| D7 | **Disc not ready** (scanned while spinning up) | friendly "couldn't read the TOC… click Rescan disc" — *not* a traceback | **Rescan disc** |
| D8 | **Disc unknown to MusicBrainz** | numbered blank rows + offer to *Rip as Unknown Album*; no TTY prompt | rip as unknown |
| D9 | **CD-R (home-burned)** | just works — cyanrip is CD-R-native (no toggle) | — |
| D10 | **Scratched / unreadable track** | clear "Track N couldn't be read… clean it" hint; the `-Z` secure re-read ceiling + stall detection (0.4.13) bound the retry time | clean the disc, or raise "Max reads to confirm a shaky track" |
| D11 | **Drive offset unknown** (drive not in the list) | rip is blocked with a "set up your drive first" prompt → wizard | type the offset from the AccurateRip list |
| D12 | **Cancel mid-rip** | drive spins down; if not, auto-force-stop after a few seconds (or **Force stop**) | — |
| D13 | **Update downloaded over the old file's path** | integration still offered; menu entry/icon fixed | accept the offer |
| D14 | **Quit while a rip / wizard / update runs** | clean shutdown (threads joined); no crash/zombie | — |

Each D-row that misbehaves → file a report with the log.

---

# Single-feature cases (Test 1–14)

The individually-gated deep cases. Each is self-contained: do the steps, record
the result, follow **If it fails**. Several are unblocked by — or feed back
into — the acceptance run above and link to it rather than repeating it.

## Recognized-CD walkthrough (ties the cases together)

A **recognized CD** (in MusicBrainz, ideally in AccurateRip + CTDB — a popular
album works best) exercises almost everything in one sitting:

1. **Calibrate the drive** — the wizard pre-fills the offset from the bundled
   AccurateRip list (or take manual entry); capture the wizard screens ("what
   success looks like"). *(This is **Test 3**.)*
2. **Rip it** from the GUI → confirm every track's **Test CRC == Copy CRC** and
   the AccurateRip confidence. Screenshot — **Test 5**.
3. **CTDB-verify the rip** — **Test 1**, the highest-value step:
   ```bash
   source .venv/bin/activate
   python3 scripts/ctdb_verify.py "$HOME/Music/rips/<Artist>/<Album>/"
   ```
   Paste the full output (TOC, lookup URL, verdict) — this validates or corrects
   the `toc=` wire format and the CRC.
4. If you have a second recognized disc, repeat step 3: a standard studio album
   is the cleanest CTDB data point, so two discs disambiguate "wrong wire format"
   (both fail) from "this pressing isn't in CTDB" (one fails).

> CTDB's CRC needs host `flac`. If `flac --version` fails, export it from the
> container once: `distrobox enter ripping -- distrobox-export --bin /usr/bin/flac`.
> Even without it, the **lookup half** of Test 1 still validates the wire format.

## Test 1 — [~] CTDB verify: wire format + CRC (KDD-16)

**Goal:** confirm (or correct) the CTDB lookup wire format and the audio-CRC
algorithm, which were written clean-room from the spec and are unvalidated.
This unblocks wiring CTDB verify into the GUI.

> **Status (2026-07-05, real-hardware v0.4.10 rip of The Police — "Every Breath
> You Take: The Classics"):** the **`toc=` wire format is now hardware-CONFIRMED**
> — the disc was found in CTDB (confidence 1347, entries returned), so the lookup
> half of this test passes. The result was **`no_match` (disc found, CRC differs)**
> against an AccurateRip-confidence-200 rip, which is the documented signature of
> the **placeholder CRC** — so the ONE remaining piece is the bit-exact CRC trim
> (see the `no_match` branch below). The verify wording no longer misreports this
> as "your rip differs" (v0.4.11). **DONE (2026-07-07):** a `--ctdb-calibrate`
> run on the v0.4.19 re-rip reproduced a stored CTDB CRC at aligned offset 0
> (frames 157,999,716; trim front 5880 / back 9996; CRC `0x5DA89FCD`), so
> `crc.CRC_VALIDATED` is now `True` with that vector as the golden-vector
> regression fixture (`crc.CONFIRMED_VECTOR` + `test_kdd16_confirmed_vector_trim`).
>
> **Calibration vehicle (v0.4.11):** run it from the shipped AppImage — no dev
> checkout, no re-rip:
> ```bash
> ./platterpus-x86_64.AppImage --ctdb-calibrate "~/Music/rips/<Artist>/<Album>/"
> ```
> It sweeps the candidate offset-guard trims over the existing FLACs and prints
> the `(front, back)` trim that reproduces a DB CRC — paste that back to bake it
> into `ctdb/crc.py`. (`scripts/ctdb_verify.py --calibrate` is the dev-checkout
> equivalent; both share `ctdb/diagnose.py`.)

**Preconditions**
- A pressed commercial CD that is very likely in CTDB (a well-known album).
- The disc ripped to FLAC through the GUI (a folder of `NN - Title.flac`).
- Host has `flac` and `metaflac` (`flac --version`); network reachable.
- A checkout with the package importable (`pip install -e .`, or prefix the
  command with `PYTHONPATH=src`).

**Steps**
1. Run the standalone verifier against the ripped album folder:
   ```bash
   python3 scripts/ctdb_verify.py "~/Music/rips/<Artist>/<Album>/"
   ```
2. Read the printed **Disc TOC** and **Lookup URL**.
3. Open the Lookup URL in a browser (or `curl` it) and compare to the script's
   parsed verdict.

**Record**
- Disc TOC string: `__________`
- Verdict (`not_in_db` / `no_match` / `match` / `no_decoder` / `lookup_error`):
  `__________`
- Confidence: `____` · Our CRC: `________` · A DB CRC: `________`

**Interpreting the result**
- **`lookup_error`** → transport/parse problem. Capture the URL + raw response;
  the issue is in `adapters/ctdb_client.py` (transport) or `parse_lookup_response`.
- **`not_in_db` for a disc you're sure is in CTDB** → the **`toc=` wire format
  is wrong**. This is the most likely first failure. Compare our TOC string to
  what CUERipper/CUETools sends for the same disc (Wireshark, or CUETools' log).
  Likely culprits: the +150 lead-in (`toc.LEAD_IN_SECTORS`), how the lead-out is
  expressed, or per-track vs. cumulative offsets (`disc_toc_from_files`). Fix
  `ctdb/toc.py` and re-run.
- **`no_match` (disc found, CRC differs)** → the lookup format is right; the
  **CRC algorithm needs the bit-exact fix**. Read the **LGPL**
  `CUETools.AccurateRip` (`AccurateRipVerify.CTDBCRC`) + `CUETools.Parity` for
  the polynomial/init/reflection and the ±5879-frame offset sweep (CTDB's
  range, `CDRepair.FindOffset` — wider than AccurateRip's ±2939), then replace
  `ctdb/crc.py:ctdb_crc_offset0` (the single seam). **Do not read
  `python-cuetoolsdb`** (GPL-2.0; KDD-16). Re-run until it matches a DB CRC.
- **`match`** → success (achieved 2026-07-07). The ±5879 offset sweep is
  implemented, `crc.CRC_VALIDATED = True`, and the real CRC vector is pinned as a
  regression test (`crc.CONFIRMED_VECTOR`).

**If it fails:** record the URL, raw XML, and TOC; the fix lives in `ctdb/toc.py`
(format) or `ctdb/crc.py` (CRC) — both are isolated for exactly this.

### Test 1b — [x] wire CTDB verify into the GUI — BUILT 2026-06-17 (experimental seam)
The GUI wiring shipped ahead of the hardware validation, kept safe behind the
`crc.CRC_VALIDATED=False` seam (a match showed as **EXPERIMENTAL**, never
"verified"); since 2026-07-07 `CRC_VALIDATED=True`, so a match now reads
**verified**. As built: `workers/ctdb_worker.py::verify_rip_dir` (runs on a
daemon thread reporting via a queued signal; joins the post-rip metaflac thread
first so it never decodes a file mid-rewrite); a CTDB verdict line under the
AccurateRip table in `ui/rip_progress.py` (`set_ctdb_status`/`set_ctdb_result`
+ the pure `ctdb_verdict_line` renderer); a `Config.ctdb_verify_after_rip`
Settings toggle (originally default off; **on by default since 0.4.5**); tests for the worker
signal flow, the UI render (incl. experimental labelling), and the off-thread
MainWindow wiring.

**Done (2026-07-07):** Test 1 confirmed the `toc=` wire format and a trustworthy
`match`, so `crc.CRC_VALIDATED` was flipped → `True` (the single seam) and matches
now read "verified ✓". (Host `flac` export in the wizard is tracked separately.)

## Test 2 — [ ] CTDB repair direction (Phase 2, KDD-14)

**Goal:** decide and prototype parity repair. **Depends on Test 1 passing.**

**Open decision (needs your call):** `ctdb-cli` is **C#/.NET 10**, so bundling
it in the AppImage is heavy. Choose: (a) bundle a self-contained .NET publish,
(b) route it through the dependency subsystem as an *optional* user-installed
tool (like Picard), or (c) revisit a pure-Python `CUETools.Parity` port. (Record
the choice in `TASKS.md` / KDD-14.)

**Steps (exploratory, on a disc that ends with uncorrectable errors)**
1. Install `ctdb-cli` (`github.com/Masterisk-F/ctdb-cli`).
2. Run `ctdb-cli verify <cue>` then `ctdb-cli repair <cue>` on the damaged rip;
   capture the exact CLI surface + `--xml` output shape.
3. Record whether repair reconstructs + re-verifies, and the parity download size.

**Record:** chosen bundling option `____`; `ctdb-cli` CLI/output notes `____`.

## Test 3 — [ ] Drive-setup wizard: success screens + auto-vs-manual offset (rewritten 2026-07-21)

*(Successor to the whipper-era `drive analyze`/`offset find` string captures —
whipper is gone (KDD-18) and cyanrip has no probe commands; the wizard fills
the offset from the bundled AccurateRip drive list, or takes manual entry.)*

**Goal:** capture what wizard success actually looks like on real hardware —
screenshots/strings for the README and the wizard's own help text — and confirm
the auto-filled offset matches an independent manual lookup.

**Steps**
1. Run **Tools → Set up drive…** with your drive connected (no disc needed —
   the lookup is by drive model).
2. Capture the wizard's screens: the recognized-drive state (offset pre-filled,
   e.g. **+667** for the BDR-209D), and the save confirmation. Note the exact
   wording shown.
3. Independently look your drive up at
   [accuraterip.com/driveoffsets.htm](https://www.accuraterip.com/driveoffsets.htm)
   and compare to the pre-filled value.
4. Confirm the saved offset lands in the GUI config (Settings shows it
   read-only) and is passed to cyanrip as `-s` on the next rip (visible in the
   rip log banner).

**Record:** wizard wording `__________`; auto offset `____`; manual lookup
`____`; match? `____`; screenshots saved for README/help? `____`.

## Test 4 — retired (2026-07-21)

*(Was "`whipper offset find` success output" — merged into **Test 3**: the
auto-vs-manual offset comparison is its step 3. Number kept as a stable ID;
full text in git history.)*

## Test 5 — [ ] GUI screenshot

**Goal:** confirm the GUI looks right on Bazzite KDE Plasma 6 and add a
screenshot to the top of the README.

**Steps**
1. Launch the published AppImage on Bazzite/KDE.
2. Screenshot the main window (ideally mid-rip, track table populated, current
   track highlighted).
3. Save to `docs/img/platterpus.png` and embed it near the top of `README.md`.

**Record:** screenshot committed? `____`; any layout issues `__________`.

## Test 6 — [ ] Picard auto-launch UX

**Goal:** verify the unknown-disc → Picard flow end-to-end and document what the
toggle actually does.

**Steps**
1. Enable "Launch MusicBrainz Picard on unknown discs" in Settings (Picard
   installed via the GUI's dependency manager).
2. Rip a disc MusicBrainz can't identify (or use *File → Rip as Unknown Album…*).
3. Observe whether Picard launches with the ripped files on finish.

**Record:** Picard launched? `____`; files loaded? `____`; UX notes `__________`.
Update README Step 6 with the real behaviour.

## Test 7 — [x] PyPI go-live — DONE (live since v0.4.22; the wheel publishes automatically on each release)

**Status (2026-07-08):** the Trusted Publisher is configured and the wheel
publishes automatically on each release — `platterpus` is on PyPI through
**v0.4.22** and `pipx install platterpus` works. The steps below are retained as
the record of what was set up.

**Goal:** make `pipx install platterpus` work from PyPI. The `publish-pypi.yml`
workflow is already in place (Trusted Publishing) and is dispatched automatically
by `release.yml` after each release (it keeps `publish-pypi.yml` as the OIDC
entry workflow, so the publisher config in step 1 is exactly right). Note: the
publish only ever *failed* before because the publisher wasn't configured —
step 1 is the missing piece.

**Steps**
1. On PyPI: **Publishing → add a pending publisher** with — project
   `platterpus`, owner `rmccann-hub`, repository
   `Platterpus`, workflow `publish-pypi.yml`, environment
   `pypi`.
2. Cut a release the usual way (bump `__version__`, roll `CHANGELOG.md`, dispatch
   the Release workflow — see `CLAUDE.md` *CI / release*).
3. Watch the **Publish to PyPI** action; confirm the release on PyPI.
4. On a clean machine: `pipx install platterpus` and launch `platterpus`.

**Record:** published version `____`; `pipx install` works? `____`. Then drop
the "if it's not on PyPI yet" caveat from the README.

## Test 8 — [~] cyanrip EAC-parity record + remaining `-Z` convergence (rewritten 2026-07-21)

**Status:** the parity core **ran on real hardware 2026-07-05/07** — the
committed result is **12/14 byte-identical vs EAC** (T3 read-instability, T5
disc defect), proof in `output_reference/cyanrip_flac/`, pinned by
`tests/test_parity.py`; a v0.4.13 re-rip reached **13/14** (T3 converged
partial→exact). What remains open here is the deliberate `-Z` convergence
re-rip below. *(The original test's backend-switch/wizard-install steps died
with whipper — that install path is now covered by A4; text in git history.)*

**Goal:** prove on a marginal track that raising **Max reads to confirm a
shaky track** (`-Z N`) converges a near-miss to the AccurateRip consensus.

**Steps**
1. Rip the Police disc (A6). If a track reads as a near-miss/offset-variant
   (T3-class), set Settings → **Max reads to confirm a shaky track → 2** and
   re-rip.
   - [ ] The re-rip's argv includes `-Z 2` (visible in the log).
   - [ ] The track converges to the consensus CRC (matches Part B). (T5 is a
         physical disc defect; EAC fails it too — not expected to converge.)
2. Run `scripts/eac_parity.py` against the Part B baseline; record the count.
3. **Verification UX:** confirm the **verdict banner** and the disc-panel
   "AccurateRip" line **agree** on the verified count (one shared
   `confidence ≥ 1` rule), and that the status line matches.

**Record:** cyanrip version `____`; `-Z 2` converged the near-miss? `____`;
CRCs vs Part B `____`/14; banner = panel count? `____`; log file `____`.

## Test 9 — [ ] In-app uninstaller: deep no-terminal run

**Goal:** prove the no-terminal uninstall on real hardware — everything the app
installed disappears; Distrobox/podman and music survive. (This is the deep
version of A1/A2/A11; do it LAST in a session, or on a sacrificial setup.)

**Steps**
1. Note what exists first: `ls ~/.local/bin/{whipper,metaflac,cyanrip,platterpus}`,
   `distrobox list`, the app menu entries, `~/.config/whipper{,-gui}`,
   `~/.local/share/platterpus`.
2. Launch the **Uninstall Platterpus** menu entry (tests `--uninstall` mode),
   or Tools → Uninstall Platterpus… inside the app.
3. Leave both checkboxes ticked → Uninstall → confirm. Watch the per-step log;
   record any ✗ verbatim.
4. Verify gone: all of step 1's items, the menu entries (may need a
   re-login/menu refresh), and — if launched from the AppImage — the AppImage
   file itself.
5. Verify KEPT: `distrobox --version` and `podman --version` still work; any
   other containers still listed; `~/Music/rips/` untouched.
6. Reinstall from the Release AppImage and confirm the first-run offers (menu
   integration, host wizard) come back fresh — proving the uninstall really
   removed the config flags.

**Record:** all removed? `____`; distrobox/podman intact? `____`; music intact?
`____`; reinstall clean? `____`.

---

## Test 10 — retired (2026-07-21)

*(Was "FLAC re-compress: bit-perfect + metadata survives + smaller" — the
opt-in re-encode existed for whipper's `-5` FLACs. cyanrip, the sole backend,
already encodes at maximum compression, so the Settings toggle is permanently
disabled and the post-rip step always skips it; the adapter is kept only as a
seam for a future backend (unit-tested; `settings_dialog.py` tooltip explains).
Number kept as a stable ID; the full real-binary procedure is in git history —
resurrect it if a non-max-compression backend ever returns.)*

## Test 11 — [ ] Multi-format output: WavPack / MP3 / WAV (v0.3.0, KDD-22)

**Goal:** prove the **Output format** feature on real files: selecting a non-FLAC
format produces a correct file in that format, the **FLAC master is always kept**,
the **lossless** formats (WavPack, WAV) are bit-identical to the FLAC, **tags +
cover art** are present per what each container allows, and the WAV warning shows.
The adapter is unit- and real-ffmpeg integration-tested in the dev environment;
this is the on-hardware, real-rip proof. Needs host `ffmpeg` + `flac`/`metaflac`.

**Design recap (so the checks make sense):** every rip produces FLAC first (the
master); a non-FLAC choice is a post-rip ffmpeg transcode of that FLAC, kept
*alongside* it. FLAC and MP3 embed the cover; WavPack and WAV can't embed via
ffmpeg, so the front cover is force-saved to the album folder as `cover.<ext>`.

**Setup**
1. Rip a recognized CD with **Output format = FLAC** (the A6 run) so you have a
   known-good tagged + arted FLAC master. Snapshot its decoded-PCM fingerprint —
   this is the lossless ground truth every other format must reproduce:
   ```bash
   D="$HOME/Music/rips/<Artist>/<Album>"
   pcm() { ffmpeg -v error -i "$1" -map 0:a -f s16le -c:a pcm_s16le - | md5sum | cut -d' ' -f1; }
   for f in "$D"/*.flac; do echo "$(basename "$f")  $(pcm "$f")"; done | tee /tmp/flac_pcm.txt
   ```

**Run — once per format**
2. Settings → **Output format → WavPack** → Save. Re-rip the same disc. Repeat for
   **MP3** and **WAV**. (Each rip re-creates the FLAC + the chosen sibling; watch
   the rip log for `Transcode: N file(s) written.`) When you pick **WAV**, confirm
   the dialog shows the **⚠ "WAV can't store tags or cover art…"** warning, and
   that it is **hidden** for FLAC/WavPack/MP3.

**Verify**
3. **FLAC master always kept:** after every non-FLAC rip, `ls "$D"` shows the
   `.flac` files next to the `.wv`/`.mp3`/`.wav`.
4. **Lossless (WavPack + WAV) — the priority:** each decoded-PCM MD5 must match the
   FLAC ground truth track-for-track:
   ```bash
   for f in "$D"/*.wv;  do echo "$(basename "$f")  $(pcm "$f")"; done
   for f in "$D"/*.wav; do echo "$(basename "$f")  $(pcm "$f")"; done
   # compare the hashes to /tmp/flac_pcm.txt — they must be identical per track
   ```
5. **Tags + cover art, per container:**
   - **WavPack:** APEv2 tags present and a folder cover exists —
     `ffprobe -hide_banner "$D"/01*.wv 2>&1 | grep -iE "title|artist|album"`
     and `ls "$D"/cover.*` (the `.wv` can't embed art, so the folder image is its
     cover — this is the v0.3.0 cover-art fix; **a missing `cover.*` is a fail**).
   - **MP3:** ID3 tags **and** an embedded cover —
     `ffprobe -hide_banner "$D"/01*.mp3 2>&1 | grep -iE "title|artist|album|Video:"`
     (a `Video:` stream == the APIC cover).
   - **WAV:** no tags/art expected (RIFF) — confirms the warning was honest.
6. **Best-practice MP3:** the encode is VBR `-V0` (≈245 kbps). `ffprobe` should
   report a VBR-ish bitrate well above 128k; it's lossy by design (not bit-compared).

**Parity proof (banks the artifact):** for each format, open the rip's `.log` and
confirm the per-track Copy/EAC CRC matches the **Part B** baseline (lossless → same
extraction CRC; MP3 → the *extraction* CRC still matches, the encode is separate).
Commit the passing **log only** (never audio — Rule #8) under
`output_reference/<backend>_<format>/` to close the WAV/MP3 rows in `TASKS.md`.

**Record:** FLAC master kept for every format? `____`; WavPack PCM == FLAC? `____`;
WAV PCM == FLAC? `____`; WavPack tags + folder cover present? `____`; MP3 tags +
embedded cover? `____`; WAV warning shown? `____`; logs committed? `____`.

**If it fails:** a missing/empty non-FLAC file → check host `ffmpeg` is present and
on PATH (`platterpus --doctor` reports it); a PCM mismatch on WavPack/WAV → a real
transcode bug (the adapter is `adapters/transcode.py`); a missing WavPack folder
cover → the cover-art force-save gate in `main_window_rip._on_rip_finished`.


## Test 12 — [ ] Read-speed ladder, auto-fix re-rip-and-swap, and the speed-locked drive (added 2026-07-21)

**Goal:** hardware-prove the adaptive read-effort stack shipped in 0.4.7–0.4.13
on the BDR-209D — none of it can be validated headless. Three checks in one run
(a scuffed/marginal disc is ideal):

**Steps**
1. **Speed-locked `-S` safety (BDR-209D-specific):** the drive reports its
   speed as *unchangeable*, and cyanrip **aborts** on `-S` there — so after
   pass 1 the ladder must lock the speed and escalate via `-Z` only. Rip a
   marginal disc; confirm the rip **never aborts with an `-S`/EINVAL error**
   and later passes show `-Z` escalation, not `-S`, in the log.
2. **Auto-fix re-rip-and-swap:** when a single track reads unstable, the
   auto-fix re-rips just that track (`-l N` in the argv) and keeps the better
   read. Confirm the report's `retried_tracks[]` names the track and trigger,
   and the kept file's CRC matches the better read.
3. **Ladder behaviour:** on repeated read errors the disc is re-read more
   slowly (where the drive allows) — confirm the per-pass speeds in the log
   descend, and quality only ever goes up (a verified track is never
   re-ripped).

**Record:** drive `____`; disc `____`; `-S` abort seen? `____` (must be no);
auto-fix track + trigger `____`; final verified count `____`/N.

## Test 13 — [ ] CD-Extra / data-track disc: CTDB TOC + rip behaviour (added 2026-07-21)

**Goal:** a disc with a data session (CD-Extra/enhanced CD) has a TOC the CTDB
`toc=` string must encode correctly (audio tracks only + the data-track
convention) — owed from the 2026-07-02 audit; unverifiable without such a disc.

**Steps**
1. Rip a CD-Extra/enhanced disc (audio + data session) end-to-end.
2. Confirm the rip covers the audio tracks only and completes with a verdict.
3. Confirm the CTDB verify returns a real lookup result (found/not-found —
   either is fine; what must NOT happen is a malformed-TOC 404/timeout on a
   disc CTDB knows).

**Record:** disc `____`; audio/data track split `____`; CTDB verdict `____`;
any TOC error verbatim `__________`.

## Test 14 — [ ] EAC-compatible companion log + goal presets (added 2026-07-21)

**Goal:** exercise the two newer GUI-visible features that have no manual test
row: the opt-in EAC-layout companion log (v0.4.16) and the Settings goal
presets (0.4.0).

**Steps**
1. Settings → enable **EAC-style log** → rip → confirm
   `<Album> (EAC-compatible).log` appears beside the rip, renders EAC's layout,
   is **plainly attributed to Platterpus and carries no checksum signature**,
   and `scripts/eac_parity.py` reads it interchangeably with cyanrip's own log.
2. Settings → **Goal → Archival exact / Fast verified / Portable** — confirm
   each preset snaps the format/verification controls as documented, and that
   editing any snapped control flips the goal to *Custom*.

**Record:** companion log present + attributed? `____`; parity script reads it?
`____`; presets snap/flip correctly? `____`.

---

## Reporting template

```
### Test report
Environment : (paste the §0 block)
Ran         : A1–A11 ✓/✗ per step  |  Part C row: ____  |  Part D rows: ____
EAC parity  : cyanrip CRCs match Part B baseline? ✓/✗   (attach the .log + EAC log)
Cases       : Test N ✓/✗ + Record-box values
Failures    : (step/case ID + what happened, verbatim)
Logs        : ~/.local/share/platterpus/log.txt  +  the rip .log
```

File issues at the repo's Issues page (Help → About has the link). Keep one
issue per distinct failure.

## After a test passes

- Update the marker (`[ ]` → `[x]`, or `[?]` on failure) with the date and notes.
- Land the follow-up the test unblocks (Test 1 → GUI wiring; Tests 3/4/5/6 →
  README updates; Test 7 → README caveat removal).
- Update `TASKS.md` and `CHANGELOG.md`.

---

*Last updated for Platterpus v0.5.5.*
