# Manual & release testing

> **Who this is for.** The maintainer running a full pre-release check, and the
> external testers coming on board. These are the validations that **can't run
> in CI** — they need a real CD + drive, a desktop session, or a maintainer
> credential.
>
> **Just want to test the release that's in your hand?** Follow
> [`rig-session.md`](rig-session.md), the current run sheet, and run
> **Tools → Advanced → Run acceptance test…** in the app, which keeps everything a
> run makes — rips, screenshots, transcript and one `.tar.gz` — in one session
> folder under `~/platterpus-rig/` ([`rig-scripts/README.md`](rig-scripts/README.md)).
> The **Hardware test checklist** near the end of this document holds the hardware
> cases the acceptance run does not cover; this document is the full reference
> behind both.
>
> Two halves, in order of how you'll use them:
> - **Parts 0–D + Reporting** — the end-to-end *release/acceptance run*: a clean
>   uninstall → fresh install → rip → verify cycle, the **EAC output-parity**
>   check, and the **distribution + problem-permutation matrices** to spread
>   across testers.
> - **Part E** — the *failure-derived gate*: the classes of defect that have
>   actually bitten this project, how to tell a normal failure from an anomalous
>   run, and what a **pass** has to prove before it may be counted. Read it before
>   Parts 0–D on any release run.
> - **Hardware test checklist** — the fillable run sheet for every hardware test
>   the acceptance run does not cover, on the maintainer's Bazzite + BDR-209D rig
>   (§A–§D, §F; its test IDs are its own, so its A11 is not Part A's). It was the
>   standalone `hardware-test-checklist.md` until 2026-11-16.
> - **Single-feature cases (Test 1–14)** — the deep, individually-gated cases
>   (CTDB verify CRC, PyPI go-live, the cyanrip parity run, and the
>   multi-format output proof). Run one at a time and record the result.
>   The cases written for the previous backend were **rewritten for the cyanrip-only reality on
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
App version      : (Help → About Platterpus…, or `platterpus --version`)
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
`ripping` container, host-exported `metaflac`/`cyanrip`, any leftovers from older
versions (`~/.local/bin/whipper`, `~/.config/whipper/`), Picard, and the app's
config + logs. **Never** your music. (No checkout? Use the app's **Tools →
Uninstall Platterpus…** and tick both boxes — the container, and *leftover ripper
settings from older versions*. The AppImage removes itself as part of the run when
launched from one.)

### A2 — [ ] Confirm the slate is clean
```bash
ls ~/Applications/platterpus* 2>/dev/null;            echo "---"
ls ~/.local/bin/whipper ~/.local/bin/cyanrip 2>/dev/null; echo "---"
distrobox list | grep ripping;                          echo "---"
ls ~/.config/platterpus ~/.config/whipper 2>/dev/null
```
*Expected:* only the `---` separators print (everything empty; the `whipper` paths
are leftovers from older versions and should be gone too). Anything left →
`rm -rf` it (e.g. a stray `~/.config/whipper/whipper.conf.bak`) and note it.

### A3 — [ ] Fresh install (AppImage — the end-user path)
```bash
cd ~/Downloads
wget https://github.com/rmccann-hub/Platterpus/releases/latest/download/platterpus-x86_64.AppImage
chmod +x platterpus-x86_64.AppImage
./platterpus-x86_64.AppImage
```

> **After you accept the "add to menu" offer the file MOVES** to
> `~/Applications/platterpus-x86_64.AppImage` (`appimage_integration.relocate_to_applications`;
> the app names the new path in the follow-up dialog). Every later
> `./platterpus-x86_64.AppImage …` in this document is then
> `~/Applications/platterpus-x86_64.AppImage …` — a `./` command run from
> `~/Downloads` afterwards reports *No such file or directory*, which is correct
> behaviour and has already been mistaken once for a bug (rig session, 2026-08-05).
*Expected:* the window appears **immediately** and **stays responsive** — no
"Not Responding" even while the container is cold (the launch probes run off the
GUI thread). On a FUSE-less host, run with `APPIMAGE_EXTRACT_AND_RUN=1`.

### A4 — [ ] First-run offers
*Expected, in order:* (1) "Add to your applications menu?" — say **Yes**; the
file moves to `~/Applications` and a menu entry appears. (2) The **host-setup
wizard** — say Yes; it builds the `ripping` container, installs cyanrip/flac
(and metaflac), then builds the pinned fork (`FORK_PIN`; Help → About Platterpus… names it) over the stock
cyanrip and exports it, plus cd-paranoia. **~20–40 min** the
first time (≈600 MB image pull); one polkit password prompt only if podman/
distrobox needs installing (none on Bazzite/Silverblue). (3) Picard offer — your
call. Record any wizard step that fails **verbatim**.

### A5 — [ ] Drive setup (read offset)
**Tools → Setup & Updates… → Set up drive…** *Expected:* the offset is **pre-filled** from the
AccurateRip drive list (e.g. **+667** for a BDR-209D) — one **Save offset**
click, no disc. If your drive isn't in the list: look it up at
accuraterip.com/driveoffsets.htm and **type it** into the manual field, then
Save. (The wizard does not measure the offset from a disc, so there is no "Detect"
button — the value comes from the list or manual entry. The fork's own finder,
`cyanrip -f`, runs only in the acceptance run's section O. The dialog's **Analyze
cache** button measures the drive's cache with `cd-paranoia -A`, KDD-29.)

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

*(Was "cyanrip backend rip" — a backend-switch step from when the previous
ripper was the default. cyanrip is the sole backend (KDD-18), so A6 **is** the cyanrip rip and
carries this step's expectations: cover art fetched from the Cover Art Archive,
the cyanrip fidelity verdict. Number kept so A9+/Part C references stay valid;
full text in git history. Parity checklist: **Test 8**.)*

### A9 — [ ] Edge discs
- **Unknown disc / offline:** *File → Rip as Unknown Album…* → placeholders →
  Start → FLACs tagged from what you typed, cover art fetched if a release was
  picked. *Expected:* no MusicBrainz TTY prompt ever surfaces. (Picard
  auto-launch flow: **Test 6**.)
- **CD-R (home-burned):** rips with no switch — cyanrip is CD-R-native (the
  previous backend's "Continue on CD-R" toggle was removed with KDD-18).

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
**Tools → Setup & Updates… → Check for updates.** *Expected:* if newer, it downloads (cancellable
progress), shows phase labels (Downloading → Verifying → *"Installing — almost
done, please don't close…"*), verifies the checksum and the build attestation, installs to `~/Applications`,
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

> **Status (2026-10-07):** one row of this table is not ground truth. EAC's track 5,
> `E0036697`, is not AccurateRip's value; AccurateRip verifies `C96464AB`, which our
> drive read once (2026-10-07). A rip that differs from this table on track 5 only
> is not a failure until it has been checked against AccurateRip
> (`docs/eac-parity.md` Part A, TL;DR item 1).

**The per-track CRC32 baseline** (ground truth — a cyanrip rip of this disc
must reproduce these EXACTLY; EAC's "Copy CRC" and cyanrip's "EAC CRC32" are
the same algorithm, as was the previous backend's Test/Copy CRC historically). Disc: *The Police —
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
- **Null samples in CRC** — EAC: **Yes**. (cyanrip CRCs the decoded PCM,
  which includes nulls — consistent.)
- **A genuine disc defect** — e.g. our reference disc's **track 5** mismatches in
  *every* tool (CTDB: "differs in 3 samples"). A track that differs everywhere is
  the disc, not the ripper — don't chase it. *(2026-10-07: track 5 turned out not to
  be one; a secure re-read reached AccurateRip's value. See the status note above.)*

> **Known reference facts (banked from the EAC baseline):** track 3 rips *clean*
> in EAC, so the previous backend's historical track-3 failure was its **>587-offset bug**,
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
| D1 | **No drive / no disc** | Drive picker shows "(no drives found)"; *Tools → Setup & Updates… → Diagnose drive access…* explains why | insert disc / fix below |
| D2 | **Drive not readable** (user not in the drive's group) | Diagnosis names the exact `sudo usermod -aG … $USER` fix | run it, log out/in |
| D3 | **No FUSE** (minimal host) | AppImage won't mount | run `APPIMAGE_EXTRACT_AND_RUN=1 ./…AppImage` |
| D4 | **podman/distrobox absent** | Wizard offers to install them (one polkit prompt) | accept |
| D5 | **Container has no network** during a known rip | No effect: cyanrip runs offline (`-N`) with the GUI's already-fetched tags | none needed |
| D6 | **Cold container** (first launch after boot) | window appears + stays responsive; probes finish in the background | wait a few seconds |
| D7 | **Disc not ready** (scanned while spinning up) | friendly "couldn't read the TOC… click Rescan disc" — *not* a traceback | **Rescan disc** |
| D8 | **Disc unknown to MusicBrainz** | numbered blank rows + offer to *Rip as Unknown Album*; no TTY prompt | rip as unknown |
| D9 | **CD-R (home-burned)** | just works — cyanrip is CD-R-native (no toggle) | — |
| D10 | **Scratched / unreadable track** | clear "Track N couldn't be read… clean it" hint; the secure re-read's ceiling (Max retries, `-r`) + stall detection (0.4.13) bound the retry time | clean the disc, or raise "Extra matching reads to trust a track" (keeping Max retries above it) |
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

## Test 1 — [x] CTDB verify: wire format + CRC (KDD-16)

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
  **CRC algorithm needs the bit-exact fix**. Read the **GPL-2.0-or-later**
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

*(Successor to the previous backend's `drive analyze`/`offset find` string
captures — that backend is gone (KDD-18), and the wizard runs no offset probe: it fills
the offset from the bundled AccurateRip drive list, or takes manual entry. The fork's
`cyanrip -f` finder is exercised by the acceptance run's section O, not by the wizard.)*

**Goal:** capture what wizard success actually looks like on real hardware —
screenshots/strings for the README and the wizard's own help text — and confirm
the auto-filled offset matches an independent manual lookup.

**Steps**
1. Run **Tools → Setup & Updates… → Set up drive…** with your drive connected (no disc needed —
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

*(Was the previous backend's "`offset find` success output" — merged into **Test 3**: the
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
1. In Settings, enable **Tick "launch Picard" by default on unknown discs** (Picard
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
with the previous backend — that install path is now covered by A4; text in git history.)*

**Goal:** prove on a marginal track that raising **Extra matching reads to
trust a track** (`-Z N`) converges a near-miss to the AccurateRip consensus.

**Steps**
1. Rip the Police disc (A6). If a track reads as a near-miss/offset-variant
   (T3-class), set Settings → **Extra matching reads to trust a track → 3** (2 is
   the default) and re-rip.
   - [ ] The re-rip's argv includes `-Z 3` (visible in the log).
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
   `~/.local/share/platterpus`. (The `whipper` paths are leftovers from older
   versions; the uninstaller removes them if present.)
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
opt-in re-encode existed for the previous backend's `-5` FLACs. cyanrip, the sole backend,
already encodes at maximum compression, so the Settings toggle was permanently
disabled and the post-rip step always skipped it. The toggle, its setting and the
adapter were removed on 2026-10-07 on the maintainer's ruling. Number kept as a
stable ID; the full real-binary procedure is in git history.)*

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
   the dialog shows the **⚠ "WAV keeps only basic tags: title, artist, album, track
   number, year and genre…"** warning, and
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
   - **WAV:** only title, artist, album, track number, year and genre in the RIFF
     INFO chunk, no album artist, no cover —
     `ffprobe -hide_banner "$D"/01*.wav 2>&1 | grep -iE "title|artist|album|track|date|genre"`
     — confirms the warning was honest.
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
cover → the cover-art force-save gate in `main_window_rip._finish_rip` (reached from `_on_rip_finished`).


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
row: the EAC-layout companion log (v0.4.16; on by default since 2026-11-12) and the Settings goal
presets (0.4.0).

**Steps**
1. Settings → confirm **EAC-style log** is ticked on a fresh config (the default) → rip → confirm
   `<Album> (EAC-compatible).log` appears beside the rip, renders EAC's layout,
   is **plainly attributed to Platterpus and carries no checksum signature**,
   and `scripts/eac_parity.py` reads it interchangeably with cyanrip's own log
   as a *candidate*. Handed in as the *baseline* it is refused, exit 2, naming
   its first line (`docs/eac-parity.md`, P1).
2. Settings → **Goal → Archival exact / Fast verified / Portable** — confirm
   each preset snaps the format/verification controls as documented, and that
   editing any snapped control flips the goal to *Custom*. With **EAC-style log**
   unticked, choosing *Archival exact* ticks it; unticking it again leaves the
   goal on Archival exact (the log is not a field the goal is matched on).

**Record:** companion log present + attributed? `____`; parity script reads it?
`____`; presets snap/flip correctly? `____`.

---

## Part E — The failure-derived gate: what actually breaks, and what a pass has to prove

**Maintainer directive, 2026-08-20:** *"look at all past failures, look at what
normal failures are, look at everything, and devise a procedure to test against,
and if allowed to pass then it should be scrutinized and documented."*

Parts 0–D say **what to exercise**. This part says **what to disbelieve**, and it
is derived from the record rather than from imagination: the numbered cases in
[`testing.md` §5](testing.md), the `[Fixed]` entries in `CHANGELOG.md`, and the
rig runs in the [§5B evidence ledger](testing.md) (twenty-one rows on 2026-10-19, four of them
`full-green`, all on one machine). A pass on this project has
been wrong often enough that "it passed" is the beginning of the check, not the end.

### E0. The two measurements that reframe everything here

Both are counted, not felt, and both come out of the hardware runs:

1. **On three rig runs, EVERY failure descended from ONE defect.** v0.6.17: 8 of
   8 steps, all one race. v0.6.18: `pass=55 fail=5`, all five one latch. v0.6.28,
   2026-08-26: 218 steps, 211 pass and 7 fail, all seven one duplicate-picker
   defect. So the
   **number of failures carries almost no information about how much is wrong** —
   and, more dangerously, five separately-plausible explanations were available and
   would each have "fixed" one symptom. *Root-cause to a single mechanism before
   triaging anything.*
2. **Every defect that mattered in August was found on hardware, by a person, with
   the suite green throughout** — and three of them were inside the feature built
   the day before to make reporting easier. A green suite is evidence about this
   repository on a CI runner. It is not evidence about the software.

### E1. The failure classes that have actually bitten, and what catches each

Read this as a list of things to *check for*, not a history lesson. The right-hand
column is what makes the class visible; where it says **procedure**, no code check
exists and a human has to look.

| # | Class | Times | What it looks like | What catches it |
|---|---|---|---|---|
| 1 | **A check that cannot fail** — satisfied by finding nothing | 4+ | A gate reports success having examined zero things; "entries were moved" printed by a check that only tested emptiness | A floor: *examined ≥ N*. §5.ae, §5.ad |
| 2 | **A check that passes for the WRONG reason** | 3 | A required section matched by a stray sentence starting with the same letter; the contract really was present, so the verdict was right and the reason was not | Match the *label* **and** the *subject*. §5.ad |
| 3 | **Two surfaces answering one question by different keys** | 2 | Each module's own tests green; the defect lives strictly in the relation between them | One predicate, N callers; test the *relation*. §5.al |
| 4 | **Two witnesses that share an ancestor** | 2 | Cross-checking two builds/fixtures agrees perfectly, and both carry the inherited bug | Assert against the **source artifact**, plus a non-triviality assertion. §5.ac |
| 5 | **Asking for a thing vs. having it** (async seam) | 2 | A step drives a subsystem, records PASS, and the work lands 124 ms later | Assert the *state*, not the request. §5.ap |
| 6 | **A frozen or destroyed input** | 2 | A correct detector describing the design, because the value it reads is pinned by a clamp — or overwritten by a second feature that is *supposed* to overwrite it | Ask *what pins / what else writes this?* §5.ah, §5.aq |
| 7 | **The fix unblocks states that never ran** | 2 | A correctness fix makes a path reachable whose downstream has no tests and arrives already believed-in | Ask what downstream does with answers it never used to receive. §5.ak |
| 8 | **A GUI-thread block** | 4 | "Not Responding"; a dialog that installs/probes in its own button slot | `CLAUDE.md` rule; **procedure** — click during every long step |
| 9 | **A run that vanishes or hangs** | 3 | Exit 0 with no summary; progress dots then silence; a job that eats its timeout | Session sentinel; `faulthandler_timeout`. §5.ar |
| 10 | **A promise of completeness nothing sweeps** | 3 | An index missing 19 of 122 modules, decaying invisibly because a map is only ever wrong by omission | Derive the expected set from the filesystem. §5.af |
| 11 | **A number quoted from an open population** | 1 | A bound set from the legs that had finished — i.e. the fast tail — landing inside the healthy range | Close the population, or put the qualifier *in* the number. §5.ao |
| 12 | **A correction trusted more than a claim** | 3 | "You got this wrong", well-argued, applied faster than anything made in-house, and wrong | Scrutinise a correction like a claim. §5.u, §5.ax |

### E2. What a NORMAL failure looks like — and what is an ANOMALY

This distinction is the point of the directive, because the two need opposite
responses: a normal failure is *information* and you keep going; an anomaly means
**the run itself is not trustworthy** and its passes cannot be counted either.

**Normal** — one named expectation, one observed value, and the batch continues:

```
✗ expect-tracks 3 — found 0
✗ album "… (ripper)" — no build tag captured yet
```

Diagnose, fix, re-run. A script step failing does **not** stop the batch (only
`abort` does), deliberately: a run that stops at the first problem hides every
problem behind it, and a disc pass costs an hour nobody gets back.

**Anomalous — stop and investigate the RUN, not the feature.** Every one of these
has happened here:

- **No output where output was due.** Progress and then silence; a timed-out job
  with no stack. *The diagnosis existed and was discarded.*
- **A pass count that does not add up.** `passed + failed + skipped` ≠ collected,
  or a summary line missing entirely. Check `.pytest-session-complete`: absent
  means the run never reached session finish and **its exit code means nothing**.
- **Exit 0 with a truncated run.** Historically real: an `os._exit(0)` in product
  code ended pytest at 76% and CI called it green.
- **Many failures with one timestamp cluster.** Suspect one cause (E0.1) before
  writing more than one fix.
- **A step that passes in less time than the work takes.** A rip step that
  "passes" in under a second is an async seam (class 5), not a fast disc.
- **A dialog you did not expect, or one that will not close.** A modal over a live
  progress view, or a second one on top of the first (§5.ar).
- **A verdict of `not_determined` reported as a pass.** Tri-state is not boolean;
  absent evidence is not negative evidence and is certainly not positive.

### E3. The procedure

1. **Record the environment** (§0) and the **exact build**: `--version` output
   including the fingerprint, plus the AppImage's SHA-256. Two artifacts from two
   binaries are not interchangeable evidence.
2. **`--doctor` first.** It costs seconds and it fails on the things that would
   otherwise waste the disc pass.
3. **Run Tools → Advanced → Run acceptance test… → Full** (324 steps at v0.6.65; the script has grown since, and the run states its own estimate when it starts)
   end to end. Only a Full run counts as evidence. Do not stop at the first failure.
4. **Upload the evidence bundle**, not a transcript. One file, self-describing,
   with the exit code (tri-state — `null` for a child never reaped is a real
   answer), the exact argv as spawned, and complete output with stderr merged and
   any elision counted.
5. **Classify every failure against E1**, then **collapse them to root causes**
   (E0.1). Report the count of *causes*, not the count of *symptoms*.
6. **Then, and only then, scrutinise the passes** — E4.

### E4. Scrutinising a pass (the part that is usually skipped)

A pass is a claim, and this project's record is that a wrong pass costs more than a
failure, because **a failure gets investigated and a pass gets cited**. For every
step that passed, the run report must be able to answer:

- **Could it have failed?** Name the condition that would have made it fail, and
  whether that condition was reachable in this run. A check satisfied by finding
  nothing is decoration (class 1).
- **Did it verify the thing, or the request for the thing?** (class 5)
- **Was it verified where it could fail?** An invariant confirmed under conditions
  that arithmetically force it has not been tested.
- **What was the input, and what pinned it?** (class 6)
- **If the other side relabelled this without changing the artifact, would the
  answer change?** If yes, the check is keyed on a label, not an identity (class 3).
- **Is any verdict `not_determined`?** Those are neither passes nor failures and
  must be listed separately, never folded into the pass count.

### E5. Documenting it — a run is not finished until it is a ledger row

The output of this procedure is **one row appended to the §5B evidence ledger** in
`testing.md`, plus the bundle. The row records `partial` unless **every** step
passed in that single run — that is the maintainer's ruling and the reason the
ledger holds partials at all: a ledger of successes only makes the denominator
invisible. `tests/test_no_stale_version_claims.py` parses the table, so the row is
not decoration — it is what a future version bump is allowed to claim.

## Hardware test checklist

> **Read this first.** This section was the standalone `hardware-test-checklist.md`
> until 2026-11-16, when it was folded into this document (Critical rule #7: one home,
> not two). Only its heading levels, its cross-references and the two statements this
> document already made (the CRC baseline, now Part B's table, and the no-audio rule,
> now §0's warning and *Send back* below) changed in the move. The intro block below was
> written for the **v0.6.0** sheet and is kept as its record — its "this release" means
> v0.6.0, and its list of recent releases stops at v0.5.21. Which Platterpus you have,
> which cyanrip build it installs by default, and any build a handshake round is testing
> are shown in **Help → About Platterpus…**; they are not repeated here because they move
> with every release. The primary hardware route is the in-app acceptance run named at
> the top of this document (**Tools → Advanced → Run acceptance test…**, one session
> folder under `~/platterpus-rig/`; `docs/rig-scripts/README.md`, `docs/rig-session.md`).
> The individual §A–§D cases below are still the record of what the acceptance script
> does not cover. **This sheet is due a rewrite rather than another patch** — tracked in
> `TASKS.md` — because deciding which of its cases the acceptance run has since
> absorbed is a per-case judgement against hardware results, not an edit.

> **Test IDs in this section are its own.** A11–A28, B3–B9, C2–C16, D1b–D4, §E and
> F1–F3 here are **not** Part A's A1–A11, Part D's D1–D14 or Part E: when this section
> says *A11* it means its own A11 (the cancel-then-quit re-run), and where another file
> cites the former `hardware-test-checklist.md` §A20 or §F3, it means this section's
> A20 or F3. *Step 0* below is this section's own update step, not the document's §0.

> **Everything that still needs testing, in one place.** Anything that has already passed
> is gone from this sheet — the record of what passed and when lives in
> `docs/session-log.md`. Test IDs are stable across releases, so the gaps are deliberate.
> **Six sections retired since the last sheet** (A10, A19, B2, D1, D2 and D1's original
> probe): all answered by your 2026-07-30 run.
>
> Rig details, tool versions and expected values are pre-filled from your last six runs.
> You tick boxes and note anything that **differs** from what's printed.
>
> ### ⭐ THE BIG CHANGE: you only have to send ONE file now
>
> You said *"just assume I can only upload the json file."* Done — that is what **v0.6.0**
> is. The `.platterpus.json` now contains the **full text** of cyanrip's `.log`, the
> `(EAC-compatible).log` and the `.cue`, so one upload carries everything I used to ask for
> separately. Where a test below says "send the log", **send only the `.platterpus.json`.**
>
> The one exception is `~/.local/share/platterpus/log.txt` when a test explicitly asks for a
> `grep` over it — that file spans sessions and is not part of any single album's report.
>
> **Your cancelled 2-of-14 run found two real bugs, both fixed in this release.** You did not
> waste that rip:
>
> 1. The `(EAC-compatible).log` said `*** INCOMPLETE RIP (cancelled) — this log covers 2 of 14
>    disc tracks ***` on line 10 and **`All tracks accurately ripped`** on line 68. Two
>    contradictory claims inside one SHA-256-signed document.
> 2. The `.cue` was **0 bytes**. That is still an open question — see **A27**.
>
> And your "the log link may or may not work" note found a third: three separate "open"
> buttons could silently do nothing on a desktop with no handler for a `.log`. See **A26**.
>
> **Four releases since your last completed run:** v0.5.19 (nine audit findings), v0.5.20 (a
> rip-aborting bug *introduced by* v0.5.19's own blind spot, plus a false "Bit-perfect"),
> **v0.5.21 — four bugs found by running the maintainer's cyanrip fork's real output through
> our parser, three of which were live on the cyanrip you are running now**: a pre-gap
> over-claimed by up to 89x in the archival log, an AccurateRip lookup that never happened
> reported as "in DB, no match", an all-zero checksum read as a confidence-200 match, and
> every `-Z` verdict attributed to the wrong track on the fork — and **v0.6.0** (this sheet).
>
> **Where the value is this round.** §A20–A25 are new and cover things the suite genuinely
> cannot prove: whether a *contaminated album folder* is handled correctly (A20 — the
> highest-value test on this sheet, and the one that needs the most setup), and whether the
> honest-verdict work reads honestly on real output (A22, A23). **A11 is a re-run** — the
> log now says what it didn't say last time. §D1b is still an open question, and **§A25 is new and cannot be done with the usual
> test disc** — v0.5.21's biggest fix needs a disc whose TOC declares a pre-gap, and screening
> for one costs nothing.
>
> **One thing you cannot test by hand, so it's stated rather than listed.** v0.5.20 fixed a
> bug where a single malformed line of cyanrip output would have *aborted a rip in
> progress*. Provoking it needs a corrupt ripper, so there is no §A entry — the proof is
> that eight conversion sites are now guarded and eight regexes bounded, revert-proven. If
> a rip ever dies with `rip stream error:` in the status line, that is this bug's signature
> and I want the log immediately.

**Date:** ____________  ·  **App version tested:** ____________

---

### Reference (pre-filled — don't re-measure)

| | |
|---|---|
| Rig | Bazzite `7.1.3-ogc5.1.fc44.x86_64`, KDE 6, AppImage install |
| Drive | `PIONEER  BD-RW   BDR-209D 1.51` on `/dev/sr0` |
| Read offset | **+667** — confirmed, two independent sources agree |
| Cache defeat | **Yes** — measured (`cd-paranoia -A`: 140-sector cache, backseek flushes) |
| Tools | cyanrip: the Platterpus fork — for the next run, the build a handshake round is testing when there is one (Help → About Platterpus… names it under *Build under test*, and the installed one under *Installed*). Not stock 0.9.3; the build tag (`platterpus-fork-g<commit>`) identifies the build, the version cannot (KDD-33) · flac/metaflac 1.5.0 · ffmpeg 8.1.2 · cd-paranoia 10.2 · Picard 2.13.3 |
| Settings | Overread **off** · offset-variant re-read **on** · verify-every-track **off** · max reads 2 · max retries 5 · adaptive ladder · EAC log **on** · debug log **on** |

**Test disc:** *The Police — Every Breath You Take: The Classics* — 14 tracks,
59:42.354, MB release `d14a7546-815b-43c6-8af6-35cff6cee1d0`, DiscID
`pNtImOkdBm9RMBIalzx0w9cfsYY-`.

Expected Copy CRCs — **all 14, from the run-5 baseline that matched EAC exactly** — are
the per-track baseline table in **Part B** above (the same fourteen values, `B0D122E7`
for track 1 to `787BA2D6` for track 14). Read Part B's status note on track 5 as well:
since 2026-10-07 its `E0036697` is known not to be AccurateRip's value.

**Track 3 is a problem child — and that is the disc, not the app.** Its history is
`52DFDF7D` / `3D8FCF0C` / `59D352DD` / `1AC787A1` across six runs: the signature of a
marginal surface. **Expect it to vary.** What matters is that the app *says so*, not that
the value is stable.

**Track 5 is a genuine offset-variant pressing.** AccurateRip v1 and v2 both say "not
found" while `Accurip 450` matches at confidence 200 — the audio is right, the pressing is
shifted. Its shipped CRC has been `E0036697` on every run and matches EAC.

Expected verdict: **amber**. Best case 13/14 exact + 1 offset-variant (run 5); when track 3
misbehaves, 12/14 + 2. Both are correct readings of what the drive returned.

Expected CTDB: **depends on track 3, and that is consistent rather than flaky.** CTDB is
one CRC over the whole disc, so one differing track changes it. Either outcome is expected.

#### Wording changes since your last run — so they don't read as regressions

* The results block is now three tabs (**Tracks** / **Details** / **Live log**) with a
  fixed strip on top. See B5c.
* The EAC-compatible log's gap row reads **`Gap handling : Appended to previous track`** —
  EAC's own vocabulary rather than an echo of cyanrip's phrasing. The *behaviour* never
  changed. (Your last run failed this and you were right to send it; fixed in v0.5.19.)
* A disc that can't be read reports **the actual error**, not "not in MusicBrainz". See
  A17 — worth reading before you start.
* **An AccurateRip cell can now say `in DB, no match`** where it used to say something
  closer to "not found". Those are different facts and the cell now distinguishes them. See
  A22 — and note this may well be what track 3 shows.
* **A "Done." can now be amber.** If a post-rip step fails (tagging, a FLAC decode check),
  the trust banner is downgraded and says which. Previously it could stay green. See A23.
* **An AccurateRip cell can now read `not checked`** — meaning no lookup happened, as distinct
  from `not in DB` (the lookup ran, the disc is not there). The EAC-layout log says
  `Not checked against the AccurateRip database` for the same state. Previously both of these
  rendered as "in DB, no match", which claimed a comparison that never took place.
* **A `Pre-gap length` row can appear where it never did**, and any that appears is now much
  shorter — see A24's warning. It was being computed from the wrong quantity.
* The `.platterpus.json` report was **schema v24** at v0.6.0 (raised many times since; `rip_report.REPORT_SCHEMA_VERSION` is the authority, so read it rather than a number here). Two new blocks: `artifacts`, which holds
  the full text of the three files written beside it, and `completeness`, which finally
  states the **disc's** track count instead of leaving you to infer it from the track list.
  See A24 — a two-minute file check, not a rip.
* **The EAC-layout log can no longer say `All tracks accurately ripped` about a rip that was
  cancelled.** It used to measure against its own track list, which a cancel shrinks. See A28.
* **"Open externally…" and "Open rip folder" may now pop a dialog giving you the path**
  instead of doing nothing. That dialog is the *fix*, not a fault — it appears only when the
  desktop refuses the file. See A26.

---

### 0 — [ ] Update to the release under test

*Tools → Setup & Updates… → Check for updates* → download → verify → restart. *Help → About Platterpus…* names the version —
write it into the **App version tested** blank at the top of this sheet, because every result
below is about that build.
Nothing else to set up — your settings are already right (see above).

**Result:** ☐ PASS ☐ FAIL — version shown: ____________

---

### A — ⭐ New in v0.5.19 – v0.6.0 — only your rig can prove these

*Twenty-four findings were fixed across these three releases, all found by audits rather than by
anything going visibly wrong — which is exactly why they need a rig: the suite proves each
mechanism fires, and cannot prove the drive stops, that the right bytes got the right tags,
or that a verdict reads honestly to a person.*

***A20 is the one to do if you do only one.*** It is the ugliest bug of the batch (this
album's metadata, cover art and library transcodes being written into a *previous* rip's
leftover files) and it is the only one that needs a deliberately messy folder to see.

#### A11 — [~] ⭐⭐ RE-RUN on v0.5.20: cancel, then quit within five seconds — **PARTIAL PASS 2026-07-30**

> **The critical criterion passed.** The drive stopped and the tray opened — no held device,
> no crash, and the log shows the rescue path working end to end:
>
> ```
> 20:49:58,811  rip finished: success=False
> 20:50:03,949  force-stopping drive (auto trigger), device=/dev/sr0   ← +5.1s
> 20:50:04,067  fuser -k /dev/sr0 rc=0
> 20:50:06,789  ejected /dev/sr0                                       ← +8.0s total
> 20:50:06,789  force_stop_drive: killed=True ejected=True
> ```
>
> Your "7 or 8 seconds" matches exactly: 5 s of rescue timer, then ~2.7 s for `fuser -k` plus
> the eject itself. **Note the app ejected the disc for you** — you didn't need the button.
>
> **But the specific race this test targets isn't proven, and that's my fault.** The log's
> last line is a disc-removal repaint, which means the window was *still alive* at +8 s — so
> either the quit landed after the rescue fired, or it didn't land inside the five-second
> window. The log can't tell us, because **pressing Cancel logged nothing and quitting
> logged nothing**. I asked you to check "the log's last lines mention stopping the rip" and
> the app doesn't produce that. Both lines added on the branch — so **re-run this one on
> v0.5.19**, where the log will say `rip cancel requested…` and `window close requested…`
> with timestamps, and the race will be visible either way.
>
> Two things to do differently next time: start the clock at **Cancel**, and quit **fast** —
> if you watched the status message first, that alone is more than three seconds.

**Original test, kept for the record:**

**The one with no recovery.** On Cancel, the host-side wrapper dies immediately, but podman
does not forward the signal into the container — so the only thing that kills the
in-container reader is a five-second rescue timer. `closeEvent` disarmed that timer
*before* the shutdown drive-stop ran, and the shutdown stop gave up whenever the rip
already looked finished. Quitting inside that window left the reader ripping — and **the
drive's physical eject button is ignored while a read holds the device**, so there was
neither an in-app nor a hardware way out.

1. Start a rip of the Police disc. Let two or three tracks finish.
2. Press **Cancel**, and then **quit the app within about three seconds** (window ✕ or
   *File → Quit* — deliberately inside the five-second window).
3. Watch and listen to the drive.

- Expected: the drive spins down within a few seconds and the tray **opens on the first
  press** of the eject button.
- Expected: the app exits without a crash dialog, and `log.txt`'s last lines mention
  stopping the rip / freeing the drive.
- **The bug looked like:** the drive keeps spinning after the app is gone, and the eject
  button does nothing until you `eject /dev/sr0` or reboot.

```sh
tail -40 ~/.local/share/platterpus/log.txt
ps aux | grep -E "cyanrip|cd-paranoia" | grep -v grep    # expect: nothing
```

**Result:** ☐ PASS ☐ FAIL — drive spun down: ☐ y ☐ n · eject worked first press:
☐ y ☐ n · leftover process: ____________

#### A12 — [ ] Force stop is recorded as *cancelled*, not as a failure

Only the Cancel button marked a rip cancelled. Using **Force stop** on its own (it is
enabled for the whole rip) therefore produced "Rip failed.", an `outcome.status` of
`failed` in the JSON, an `*** INCOMPLETE RIP (failed) ***` banner in the signed log, **and**
a failure notification — recording your own deliberate choice as a malfunction.

1. Start a rip. After a couple of tracks, press **Force stop** (not Cancel).
2. Then:

```sh
python3 -c "import glob,json;d=json.load(open(glob.glob('*.platterpus.json')[0]));print(d['outcome'])"
head -20 *"(EAC-compatible).log" | grep -i incomplete
```

- Expected: `outcome.status` is **`cancelled`**, the banner says
  `*** INCOMPLETE RIP (cancelled) …`, and the window says cancelled rather than failed.

**Result:** ☐ PASS ☐ FAIL — status was: ____________

#### A13 — [ ] Closing the window mid-rip must not crash the app

`closeEvent` stopped six worker threads and **not the rip thread**. Because that thread is
owned by the window, destroying the window destroyed a running thread, which Qt treats as
fatal — reproduced to exit 134. No test could catch it because the test suite's own fixture
was quietly stopping the thread that production didn't.

1. Start a rip. Let one track finish.
2. **Close the window** (✕) while it is actively ripping.

- Expected: the app closes cleanly. **No** crash dialog, no "Platterpus quit unexpectedly",
  no KDE crash reporter.
- Expected: the drive stops (same as A11).

```sh
grep -iE "abort|SIGABRT|Destroyed while thread" ~/.local/share/platterpus/log.txt | tail
journalctl --user -b --since "10 min ago" | grep -i platterpus | tail
```

**Result:** ☐ PASS ☐ FAIL — crash dialog: ☐ y ☐ n · anything in journalctl:
____________

#### A14 — [ ] Cancelling the cache probe must actually stop the disc

`Analyze cache` runs `cd-paranoia -A`, which can take **minutes** and spins the disc the
whole time. Closing the dialog called a cancel hook that was a **no-op** — a do-nothing
default on the base class that this backend never overrode — so the flag was set and the
probe carried on to its 600-second ceiling. Three separate comments in the code claimed it
killed the process.

1. Disc in. *Tools → Setup & Updates… → Set up drive…* → **Analyze cache**.
2. Wait ~15 seconds so it is genuinely reading, then **close the dialog**.

- Expected: the dialog closes immediately, the app stays responsive, and **the disc spins
  down within a few seconds**.
- Expected in the log: `cancelling` / `SIGKILL to the process group` for the probe.
- **The bug looked like:** the dialog closes but the drive keeps grinding for minutes.

```sh
ps aux | grep cd-paranoia | grep -v grep     # expect: nothing
grep -i "cache probe" ~/.local/share/platterpus/log.txt | tail
```

**Since 2026-11-12 the check starts by itself (TASKS R53).** On a drive with no saved
verdict (a fresh `~/.config/platterpus/drive_profiles.json`, or one whose
`cache_defeat` is `null`), opening *Set up drive* with an audio CD in starts it with no
button pressed; the log says `automatic cache check for /dev/sr0: start`.

3. Open *Set up drive* with a CD in, wait ~15 seconds, press **Skip check**. Expected: the
   status says *Check stopped.*, the window stays usable, and the `ps` line above prints
   nothing within a few seconds.
4. Open it again and let the check finish. Close, reopen: expected, nothing starts, and
   the button reads **Re-analyze cache**.
5. Open it with the tray empty, then insert a CD. Expected: the line says it starts when a
   CD is in, and it does start once the disc has been read.

**Result:** ☐ PASS ☐ FAIL — spin-down seconds: ______ · leftover process: ☐ y ☐ n

#### A15 — [ ] Quitting during the startup dependency check should be prompt

The launch dependency probe enters the container, which on a cold start takes tens of
seconds. Its cancel existed but **nothing called it** (the teardown omitted one argument),
so quitting in that window waited out the shutdown budget — roughly a ten-second "Not
Responding" window — and then abandoned the thread.

1. Make the container cold: `podman stop ripping` (or reboot).
2. Launch Platterpus and **quit within the first couple of seconds**, while it is still
   probing.

- Expected: it exits within about a second. No greyed-out "Not Responding" window.

**Result:** ☐ PASS ☐ FAIL — roughly how long to exit: ______ s

#### A16 — [ ] "Rescan disc" mid-scan must stop the old reader

Superseding an in-flight disc scan left the previous reader running *and* — because both
probes were tracked in one slot — made the new one unkillable, whichever finished last
clearing the other's registration.

1. Insert a disc and, while it is still scanning, press **Rescan disc**. Do it two or
   three times in quick succession.

- Expected: no pile-up of readers, the panel settles on one correct result, the app stays
  responsive.

```sh
ps aux | grep cyanrip | grep -v grep     # expect: at most one, and it goes away
```

**Result:** ☐ PASS ☐ FAIL — max concurrent cyanrip seen: ______

#### A17 — [ ] ⭐ A disc that can't be read must say *why*

**The worst diagnostic hole in the app.** The disc probe discarded cyanrip's exit code
*and* its error text. A permission problem on the drive, a dead container, a broken host
export — all produced an empty disc, which is indistinguishable from a real disc
MusicBrainz has never heard of. So the app announced **"not in MusicBrainz"** and offered
an unknown-album rip, and **nothing was written to the log**: a bug report contained no
evidence at all.

Force a real failure. Easiest is to remove your read permission on the device:

```sh
sudo chmod o-r /dev/sr0     # and confirm you are not in a group that still grants it
```

1. With a **known-good disc** in the drive (the Police disc), press **Rescan disc**.
2. Then restore: `sudo chmod o+r /dev/sr0` (or reboot).

- Expected: a message about **not being able to read the disc / a permissions problem**,
  quoting what cyanrip actually said.
- Expected: **NOT** "this disc isn't in MusicBrainz", and **no** unknown-album offer.
- Expected in the log: a `cyanrip exited <n>` line carrying the tool's own error text.

```sh
grep -nE "cyanrip exited|Permission denied" ~/.local/share/platterpus/log.txt | tail
```

> ⚠️ **The one regression risk in this release.** The probe now treats *any* non-zero exit
> as a failure. If a disc you consider perfectly readable starts reporting an error, that is
> the thing to tell me immediately — it means cyanrip exits non-zero in a case we should
> tolerate, and the fix is to narrow the check rather than go back to swallowing it.

**Result:** ☐ PASS ☐ FAIL — message said: ____________ · log line present: ☐ y ☐ n
· any *good* disc now failing: ☐ y ☐ n

#### A18 — [ ] "Set up drive" must not clip its own text when the window is small

Its minimum size was a hand-picked guess 185 px shorter than the content needs. Measured at
440×300, the intro label was **73 px short** — the last lines of the explanation of what a
read offset *is* simply weren't drawn.

1. *Tools → Setup & Updates… → Set up drive…*
2. Try to make the dialog as small as it will go. Drag every edge.

- Expected: it **refuses** to shrink past the point where text would be cut off.
- Expected: every paragraph fully readable at the smallest size it allows; the
  accuraterip.com link visible and clickable.
- Expected: at most **one** scrollbar, in the results box — never two.

**Result:** ☐ PASS ☐ FAIL — any clipped text: ☐ y ☐ n · smallest size reached:
________×________

#### A20 — [ ] ⭐⭐⭐ A contaminated album folder — the worst bug of the batch

**Do this one first if you do only one.** It is the highest-value test on this sheet and the
only one that needs a deliberately messy folder to see.

**What was wrong.** Six post-rip steps walked the album folder with a plain "every `.flac`
in here" scan instead of "the files *this* rip wrote": unknown-mode tagging, the
colon-restore pass, the FLAC re-compress (since removed), the transcode to your chosen
format, and **both** cover-art embed loops. So when a folder held files from an *earlier*
rip, this disc's metadata was written into them, they were **transcoded into your
library**, this album's cover was embedded in them, and the count reported back to you
("embedded in N tracks") was inflated by the leftovers.

**The sequence is completely ordinary, which is the point.** Cancel a rip → partial files
remain → fix a track title → re-rip and choose *Replace*. The corrected title produces a
*different filename*, so the new file lands **beside** the old one rather than over it.

1. Start a rip of the Police disc. Let **3 or 4 tracks** finish, then **Cancel**.
2. Confirm the partial files are still there, and note **exactly** what is in the folder:
   ```sh
   ls -la ~/Music/*Police*/            # or wherever it landed
   ```
3. Now change a track title in the track table — pick track 2 and add a suffix, e.g.
   `Every Breath You Take (test)`. This is what makes the new filename differ.
4. Rip **again**, to the same folder, choosing **Replace** when asked.
5. When it finishes, look at the folder and at what the app told you.

- Expected: the leftover files from step 1 are **still there, untouched** — same mtimes,
  same tags, no cover art added, and *not* transcoded into your library.
- Expected: the cover-art message counts **only this rip's tracks** (14, not 17 or 18).
- Expected: if you chose MP3/WavPack, your library gained **14** derived files, not more.
- Expected: `~/.local/share/platterpus/log.txt` shows the steps using the rip's own file
  list. If it had to fall back to scanning the folder it says so at **WARNING** — that
  fallback is deliberate (an *older* rip's folder still gets art and tags), so a warning
  here is information, not a failure.

```sh
ls -la --time-style=full-iso ~/Music/*Police*/
# "embedded in N track(s)" is the count to check; "falling back to a folder" is the
# deliberate degradation, logged at WARNING. Both strings are the real wording.
grep -iE "embedded in|falling back to a folder" ~/.local/share/platterpus/log.txt | tail -20
# Did anything from step 1 get this album's tags?
metaflac --show-tag=TITLE ~/Music/*Police*/*.flac
```

**The bug looked like:** the old partial files gained this album's tags and cover, appeared
in your library as MP3s, and the app said "embedded in 17 track(s)".

**Result:** ☐ PASS ☐ FAIL — leftovers untouched: ☐ y ☐ n · cover count reported:
________ · extra files in library: ☐ y ☐ n · fallback WARNING seen: ☐ y ☐ n

#### A21 — [ ] A tagging failure must not be reported as "Done."

Every FLAC could ship **completely untagged** under a window saying "Done." — the tagging
pass logged each per-file failure and returned the list of files that succeeded, and the
caller **threw that return value away**. Nothing else in the program ever learned: no
signal, no status line, no report field. The scenario is ordinary — the disk fills during
the tagging pass, or `metaflac` goes missing mid-album.

Easiest way to provoke it is to take `metaflac` away *after* the rip's read finishes:

1. Start a rip. Wait until the status line moves past the reading phase into
   encoding/tagging.
2. Immediately make `metaflac` unavailable:
   ```sh
   sudo mv "$(command -v metaflac)" /tmp/metaflac.hidden     # host copy
   # or, if yours is the container export:
   mv ~/.local/bin/metaflac /tmp/metaflac.hidden
   ```
3. Let the rip finish. **Put it back afterwards** (`mv /tmp/metaflac.hidden …`).

- Expected: the status line says tags could **not** be written, and how many files.
- Expected: the trust banner turns **amber** and mentions the tagging failure — not a green
  "✓ Bit-perfect" (that is A23's fix doing its job here).
- Expected: `.platterpus.json` → `issues` contains a `tagging_failed` entry.
- Expected: the app does **not** crash, and the FLAC files themselves are intact.

*If the timing is too fiddly, skip it — the mechanism has a regression test. What only your
rig can show is whether the message is legible and lands where you'd look.*

**Result:** ☐ SKIPPED ☐ PASS ☐ FAIL — status line said: ____________ · banner amber:
☐ y ☐ n · `tagging_failed` in JSON: ☐ y ☐ n

#### A22 — [ ] ⭐ "In the database, but nothing matched" must read as its own answer

Your own words last round: *"Grey — 'no tracks matched the database' … we need to be able to
confidently be the gold standard first-burn proof as well."* This is the cell that was
conflating two genuinely different facts:

* **not in the database** — nobody has submitted this disc. Says nothing about your rip.
* **in the database, and your CRC does not match any submission** — that is a real
  disagreement and deserves to look different.

**Track 3 is the likely one to show it**, given its history (`52DFDF7D` / `3D8FCF0C` /
`59D352DD` / `1AC787A1` across six runs). Track 5 should keep reading as the
offset-variant match it is, which is a *third* distinct state.

1. Rip the Police disc normally, all 14 tracks.
2. Read the **Tracks** tab's AccurateRip columns carefully, and hover each interesting cell.

**The six readings a cell can legitimately show**, so you can tell a wrong one from an
unfamiliar one:

| Cell text | Means |
|---|---|
| `OK (N)` | matched the database at confidence N |
| `offset-variant match (N)` | matched the +450 shifted pressing — audio is right |
| `in DB, no match` | the disc **is** in the database and your CRC matched nothing |
| `not in DB` | the lookup ran; nobody submitted this disc. Says nothing about your rip |
| `not checked` | **no lookup happened at all** — the database has said nothing either way |
| `—` | no data for this track |

- Expected: whichever appear are distinguishable at a glance, and **`in DB, no match` and
  `not in DB` never read as the same thing** — that conflation is what was fixed.
- Expected: the **tooltip** on each cell explains it, and says the same thing as the cell
  text. Both are generated from one shared classifier (`_ar_state`), so a disagreement
  between a cell and its tooltip is a bug — worth reporting even if both are plausible.
- A sixth possibility exists and would be interesting: an **unrecognised** result is shown
  **verbatim** rather than guessed at. If you see raw cyanrip wording in a cell, send it —
  it means a state we don't classify yet.
- Expected: track 5 does **not** read as alarming — it is a shifted pressing, not a bad rip.
- Expected: whatever the cells say, the headline verdict is consistent with them.

**This is a judgement call as much as a test.** If a cell is *technically* right but reads
as scarier or vaguer than the truth warrants, say so — that is the finding.

**Result:** ☐ PASS ☐ FAIL — track 3 cell read: ____________ · track 5 cell read:
____________ · tooltip agreed with cell: ☐ y ☐ n · anything misleading: ____________

#### A23 — [ ] A green "Bit-perfect" must never sit above a failed check

The trust banner is one sentence built from two things: the AccurateRip verdict, and any
post-rip step that failed afterwards. It was assembled in **two** places, so whichever ran
last won — and a fresh verdict could restore a green "✓ Bit-perfect" over a FLAC master that
had already failed its decode check. (Reachable only in a re-rip ordering today, but the
comment in the code claimed it was handled and it was not.)

The simplest provocation is A21's (a tagging failure). If you'd rather not fiddle with
`metaflac`, this is also observable on any rip where **track 3 misbehaves**:

1. Rip normally. If track 3 comes back unstable, watch the banner through the whole
   post-rip sequence (verify → transcode → library move), not just at the moment it appears.

- Expected: the banner **never goes back to green** once it has reported a problem.
- Expected: when it is amber it says *why*, and all reasons are listed, not just the latest.
- Expected: the banner and the status line never contradict each other.

**Result:** ☐ PASS ☐ FAIL — banner ever reverted to green: ☐ y ☐ n · reasons listed:
____________

#### A24 — [ ] ⭐ Two-minute file check: the report schema (no rip needed)

**Do this one first.** It needs no disc, and it proves the thing that makes every *other*
test on this sheet cheaper for you: that one file is now enough.

⚠️ **The path-quoting trap that bit you last time.** Your album folder has spaces in it, so
an unquoted `$HOME/Music/rips/The Police/...` splits into three arguments and Python tries to
open `/home/rmccann/Music/rips/The`. **Every path below is quoted** — paste them exactly, or
drag the file from Dolphin into the terminal, which quotes it for you.

Run this against **any** `.platterpus.json`, including the cancelled one from last time:

```sh
JSON="$(ls -t "$HOME"/Music/rips/*/*/*.platterpus.json | head -1)"; echo "$JSON"
python3 - "$JSON" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
print("schema:      ", d["schema_version"])            # expect 24
print("completeness:", d["completeness"])              # expected / in_report / complete
for name, a in d["artifacts"].items():
    if name == "note":
        continue
    print(f"{name:9} exists={a['exists']} bytes={a.get('bytes')} "
          f"chars={len(a.get('text',''))} err={a.get('error')}")
PY
```

- Expected: `schema: 24` — that is `REPORT_SCHEMA_VERSION` in `src/platterpus/rip_report.py`,
  which moves most releases. A *lower* number means the report was written by an older build
  than the one you are testing.
- Expected: `completeness` names **the disc's count, not the log's**. On the cancelled rip
  that is `tracks_expected: 14, tracks_in_report: 2, complete: False`. On a whole rip,
  `14 / 14 / True`. **If a cancelled rip ever says `complete: True`, that is a bug and I
  want the file.**
- Expected: `rip_log` and `eac_log` both `exists=True` with a non-zero `chars` — that text
  *is* the file, which is why you no longer have to attach it.
- Expected: `cue exists=True`. **`bytes=0` is the open finding — see A27.**
- Expected: `err=None` on all three. An `err` mentioning *"refusing to embed"* would mean
  something handed the report a non-text path; that should be impossible, so tell me.

**Then the per-track check** (carried over from v0.5.21, still worth two lines):

```sh
python3 - "$JSON" <<'PY'
import json, sys
for t in json.load(open(sys.argv[1]))["tracks"]:
    print(t["number"], "silence:", t["appended_silence_frames"],
          "start:", t["start_sector"], "end:", t["end_sector"],
          "pregap:", t["pregap_sectors"], "pregap_lsn:", t["pregap_start_lsn"])
PY
```

- Expected on a **complete** rip: **track 14** has a small non-null `silence:` (2 on both
  reference rips) — the frames of *fabricated silence* appended because overread is off —
  and every other track is `None`. On your cancelled 2-track rip there is nothing to see here.
- Expected: `pregap: 0` and `pregap_lsn: None` on every track — cyanrip's TOC declares no
  pre-gaps for this disc, so `0` means *measured none*, not "unknown". A25 is about finding
  a disc that can actually exercise this.

**Result:** ☐ PASS ☐ FAIL — schema: ______ · completeness: ______ / ______ / ______ ·
cue bytes: ______ · track 14 silence: ______

#### A25 — [ ] ⭐⭐ Find a disc that can prove the pre-gap fix — the reference disc cannot

**v0.5.21's biggest fix has no hardware proof, and this disc cannot give it one.** Stated
plainly rather than left looking tested.

cyanrip's `Pregap LSN:` row prints the **absolute position** where `INDEX 00` begins; we were
rendering it as a **length**, so the error scaled with the track's position on the disc — up to
an **89x over-claim** in the archival log. It is fixed and revert-proven, but it can only *fire*
on a disc whose **TOC declares** a pre-gap. cyanrip reads pre-gaps from the TOC; EAC finds them
by sub-channel scanning. On the Police disc EAC reports ten and cyanrip reports `none` for all
fourteen — which is the KDD-32 gap, and is exactly why this fix never showed up here.

**Screening costs nothing — no full rip.** Insert a disc, let Platterpus scan it, then:

```sh
grep "Pregap LSN:" ~/.local/share/platterpus/log.txt | grep -v none
```

Any line printing a **number** instead of `none` is a candidate disc.

Best candidates, roughly in order:

1. **CD-Extra / enhanced CDs** (audio tracks plus a data track) — the data track's pre-gap is
   almost always TOC-declared.
2. **Mixed-mode discs** (track 1 is data) — common on older game and software CDs.
3. **Live albums and DJ mixes** with index points.
4. Anything whose EAC log shows `Pre-gap length` on *middle* tracks.

- If you find one: rip it, and send the `.log`, `(EAC-compatible).log` and `.platterpus.json`.
  Expected: our `Pre-gap length` row equals `start_sector − pregap_start_lsn` converted to
  hundredths, and matches EAC's row if you have an EAC log of the same disc.
- **If nothing in the collection declares one, that is a real result** — say so, and the fix
  gets recorded as hardware-unprovable rather than as untested.

**Result:** ☐ candidate found ☐ none found — discs screened: ________ · disc used:
____________ · our row: ____________ · EAC's row: ____________

#### A26 — [ ] ⭐⭐ The buttons you said "may or may not work" — v0.6.0's fix for your report

**Your words, and they were right.** `QDesktopServices.openUrl` returns a success/failure
flag when it hands a file to the desktop, and it returns *failure* whenever nothing on the
system is registered to open that kind of file. Three of our four buttons **threw that flag
away**: the click produced no window, no error, and — the part that made it unreportable —
no line in the log.

The worst one is the viewer's own **Open externally…**, which exists *because* a bare `.log`
usually has no default app on KDE. That is exactly when the call fails, so the escape hatch
was dead on precisely the machines it was written for.

**What I could not do: reproduce your symptom.** I proved the mechanism and fixed it, but
whether it is *the* mechanism depends on your machine's file associations, which I cannot
see. That is why the fix also adds a log line — so this test can settle it either way.

Do all four, during a rip and after one. **A dialog appearing is a PASS, not a failure** —
that is the new behaviour.

| # | Where | Click | Expected |
|---|---|---|---|
| 1 | Rip pane, **during** a rip | **View log** | The in-app viewer opens showing `log.txt`, live |
| 2 | Rip pane, **after** a rip | **View log** | The in-app viewer opens showing **cyanrip's** `.log` |
| 3 | In that viewer | **Open externally…** | Either your editor opens **or** a dialog appears giving the full path |
| 4 | Rip pane | **Open rip folder** | Either Dolphin opens **or** a dialog appears giving the full path |

Then check whether the old failure ever happened on your machine:

```sh
grep "declined to open" ~/.local/share/platterpus/log.txt
```

- **No lines** → your desktop handles all four, and whatever you saw was something else.
  Say so — that is a useful answer and it sends me looking elsewhere.
- **Any lines** → this *was* your bug, and it is now visible instead of silent. Send them.
- **A button that still does nothing at all** — no window, no dialog, no log line — is a
  fresh finding and the most important thing on this sheet. Note exactly which one and
  whether a rip was running.

**Result:** ☐ 1 ☐ 2 ☐ 3 ☐ 4 all responded · `declined to open` lines: ______ ·
still-dead button: ____________

#### A27 — [ ] ⭐ The 0-byte `.cue` — open question, and the answer is either way useful

Your cancelled rip left `Every Breath You Take∶ The Classics.cue` at **0 bytes**. I do not
yet know whether that is cyanrip writing the cue at the *end* of a rip (so a cancel catches
it mid-creation, which is benign) or something we are truncating. **v0.6.0 makes the byte
count visible in the report** — A24 reads it — but only a rip can say which.

Two five-minute observations, no full rip needed:

1. **Complete a short rip.** Tick only tracks 1–2 in the **Rip?** column, let it *finish*
   normally (do not cancel). Then:
   ```sh
   ls -la "$HOME"/Music/rips/*/*/*.cue
   ```
   - Expected: **non-zero**, and `View cue` in the rip pane shows `FILE` / `TRACK` lines.
   - If a *completed* rip also leaves 0 bytes, that is a real bug — send the JSON.

2. **Cancel one deliberately**, as you did before, and `ls -la` the cue again.
   - 0 bytes here with a healthy cue in step 1 → **cyanrip writes it last; benign**, and I
     will make the app say so instead of leaving an empty file that looks like damage.

**Result:** completed-rip cue: ______ bytes · cancelled-rip cue: ______ bytes

#### A28 — [ ] The status report and its own banner must agree — the bug your last run found

Thirty seconds, and it re-checks the exact document that lied.

Cancel a rip after two or three tracks, then open the `(EAC-compatible).log` — or just read
`artifacts.eac_log.text` out of the JSON, which now contains it.

- Expected near the top: `*** INCOMPLETE RIP (cancelled) — this log covers N of 14 disc
  tracks. ***`
- Expected near the bottom: **`Some tracks could not be verified as accurate`**
- **`All tracks accurately ripped` must NOT appear.** That sentence, sixty lines below the
  INCOMPLETE banner, is what v0.6.0 fixes.
- Also expected, and it must *not* change: the honest per-count line above it still reads
  `N track(s) accurately ripped`. The fix must not turn a truthful count into a pessimistic
  one.

And the other direction, so the fix is not simply "never say it": a **completed** rip — full
disc *or* a deliberate 2-track subset — must still print `All tracks accurately ripped` when
every track it was asked for verified.

**Result:** ☐ cancelled log says "Some tracks…" ☐ no "All tracks…" in it ☐ completed rip
still says "All tracks…"

### B — Still unproven from earlier releases

#### B3 — [ ] Quitting during the securing pass is recorded in the log too

Run 4 found this by accident: closing the window mid-re-rip reported a clean success. The
JSON report was fixed; the *durable* log — the artifact a stranger reads years later —
still said nothing, so the archival record was the more reassuring of the two.

1. Start a rip. When the status says it is re-ripping tracks 3 & 5, **close the window**.
2. Then:

```sh
grep -nE "securing pass was INTERRUPTED" *"(EAC-compatible).log"
python3 -c "import glob,json;print(json.load(open(glob.glob('*.platterpus.json')[0]))['read_speed'])"
```

- Expected in the log: `Secure re-read      : the securing pass was INTERRUPTED before it
  finished — any track it had not yet re-read carries only its first read`
- Expected in the JSON: `secure_rerip.interrupted` is `true` and agrees.
- Expected: all 14 tracks present and playable regardless.

**Result:** ☐ PASS ☐ FAIL — notes: ____________

#### B5 — [ ] The desktop notification — the log can now answer for it

Run 6 left this **inconclusive**, and that was a gap in the app: the toast lives eight
seconds and `log.txt` recorded nothing either way, so a shipped fix had no way to be
confirmed. Every outcome is now logged.

Start a rip, go do something else, and afterwards:

```sh
grep -n "completion notification" ~/.local/share/platterpus/log.txt
```

- Expected: exactly one line per rip — either `completion notification posted: <title> —
  <body>`, or a skip that says why (`turned off in Settings`, `the rip was cancelled`, `no
  usable system tray`).
- **posted** + you saw a toast → PASS, and the text should match the window's final status.
- **posted** + no toast → a KDE/notification-daemon issue rather than ours; still tell me.
- **no usable system tray** → the interesting one: your desktop is refusing us a tray icon
  and the notification needs a different mechanism.

**Result:** ☐ PASS ☐ FAIL — log line said: ____________ · toast seen: ☐ y ☐ n

#### B5c — [ ] ⭐ One scrollbar, and the mouse wheel does the obvious thing

**Your v0.5.15 report:** *"the 2 scroll bars in the lower right are difficult to use
together."* Fair — and the fix caused it. Putting the whole pane in a scroll area made the
table and the console *nested* scroll surfaces.

The tidy repair was a trap: turning the table's own scrollbar off gives one bar, but a
nested scroll area with nothing left to scroll **doesn't pass the wheel to its parent**
(measured), so the wheel over the table would have done nothing at all.

**What ships instead:** a fixed strip on top (progress bars, status, trust verdict) that
never scrolls and never hides, then three tabs — **Tracks**, **Details**, **Live log** —
with the buttons pinned at the bottom. One tab at a time, so at most one scrollbar, never
nested.

You don't need a full rip — tick two tracks in **Rip?** and rip those.

1. While it rips: **Live log** should be showing, on its own, without you clicking.
2. When it finishes: it should switch itself to **Tracks**.
3. Resize small and large. On each tab, spin the wheel over the middle of the content.

- Expected: **never two scrollbars at once.**
- Expected: the wheel scrolls that tab's content **every time, with no dead spots** — the
  bit I could not fully prove off-hardware, so the single most useful thing you can report.
- Expected: verdict and status stay visible whichever tab you're on.
- Expected: `Alt+T` / `Alt+D` / `Alt+L` jump to Tracks / Details / Live log.
- Expected: with a CTDB caveat, the **Details** tab label shows a **⚠**. (Your disc
  produces one while track 3 misbehaves.)

**Result:** ☐ PASS ☐ FAIL — two bars anywhere: ☐ y ☐ n · dead wheel spot: ☐ y ☐ n ·
tabs switched themselves: ☐ y ☐ n · ⚠ on Details: ☐ y ☐ n

> **Say so if you don't like it.** Tabs are a bigger change than a layout fix, and it's a
> judgement call: one predictable scrollbar, at the cost of seeing the table and the CTDB
> note together. If you'd rather have one page and put up with a scrollbar, that's
> legitimate and I'll do it differently — the measurements only rule out the old way.

#### B6 — [ ] Your own `cover.jpg` survives a re-rip

The scratch file written for `metaflac` reused the name `cover.jpg` and then deleted it —
so the default setting destroyed a cover you had put there yourself.

1. Put any JPEG named `cover.jpg` into an already-ripped album folder.
2. Re-rip that disc, choose **Replace** when asked about the existing folder.

- Expected: your `cover.jpg` **still there, unchanged**, and no stray
  `.platterpus-cover-tmp*` left behind.

**Result:** ☐ PASS ☐ FAIL — cover survived: ☐ y ☐ n · stray temp file: ☐ y ☐ n

#### B7 — [ ] A bad read offset is refused, visibly

*Tools → Setup & Updates… → Set up drive…* → try an offset far outside the sane range. Then try to force one
past the widget by hand-editing `~/.config/platterpus/config.toml` to
`read_offset = 999999` and relaunching.

- Expected: a clear message naming the allowed range; **+667 still in effect afterwards**.
  It must never silently accept a bad value and reset to 0 on the *next* launch — that
  would rip the following session at the wrong offset.

**Result:** ☐ PASS ☐ FAIL — offset after the attempt: ____________

#### B8 — [ ] Uninstall removes `cd-paranoia` too

*Tools → Uninstall Platterpus…* → **tick the host-exports item, untick everything else** →
run.

```sh
ls ~/.local/bin/ | grep -E "cyanrip|metaflac|flac|cd-paranoia"
```

- Expected: **all four gone.** `cd-paranoia` was being orphaned — the exact repeat of the
  `flac` bug from earlier.
- Re-run *Tools → Setup & Updates… → Run setup…* afterwards to put them back.

**Result:** ☐ PASS ☐ FAIL — left behind: ____________

#### B9 — [ ] Launched from the desktop icon, the app still finds its tools

A GUI started from a desktop icon does not inherit a login shell's `PATH`, and
`~/.local/bin` — where the container's tools are exported — is exactly what goes missing.

1. Launch from the **application menu / desktop icon**, not a terminal.
2. *Tools → Setup & Updates… → Check dependencies*. Expected: cyanrip, metaflac, flac, ffmpeg and cd-paranoia
   all **found**.
3. Rip a disc and confirm CTDB verification runs (it decodes with the host `flac`).

**Result:** ☐ PASS ☐ FAIL — any reported missing: ____________

---

### C — Carried over (still never exercised on hardware)

#### C2 — [ ] Offset-variant re-read, across two rips

Rip the same disc twice (A then B), then:

```sh
./platterpus-x86_64.AppImage --compare "<A>.platterpus.json" "<B>.platterpus.json"
```

- Expected: **track 5 byte-identical** between A and B — the point of the offset-variant
  re-read setting.
- Expected: **track 3 may still differ.** If it *is* identical, say so — genuine win.

**Result:** ☐ PASS ☐ FAIL — identical: ____ / 14 · track 5: ☐ y ☐ n · track 3: ☐ y ☐ n

#### C4 — [ ] Per-track "Rip?" selection

1. Insert a CD, let it identify. The grid has a leading **Rip?** column, all ticked.
2. Untick two tracks → **Start rip**. Expected: only ticked tracks ripped, filenames keep
   their **original** numbers (`03 - …`, not renumbered 1..N).
3. Untick **everything** → **Start rip**. Expected: a clear message blocks it — no rip, no
   crash.
4. Highlight 2–3 rows → **right-click**. Expected: *Rip only these* / include / exclude /
   select all / none, each working.

> The unknown-disc half of this feature is where the silent tag bug lived. That was this section's **A10**,
> retired after it passed on 2026-07-30 — worth five minutes with an unknown disc if you have
> one, but it is not an open item.

**Result:** ☐ PASS ☐ FAIL — notes: ____________

#### C5 — [ ] Whole-disc Test & Copy

*Settings* → tick **"Verify every track with a second read (EAC-style Test & Copy)"** → OK.
Re-rip.

```sh
grep -c "Test CRC" *"(EAC-compatible).log"
```

- Expected: **14** on a clean disc.
- On the Police disc, expect **12**: tracks 3 and 5 may legitimately fail to converge, and
  a non-converging track correctly gets **no** Test CRC. That is a pass — note which are
  missing.
- Expected: noticeably slower (everything read twice).

Untick it afterwards.

**Result:** ☐ PASS ☐ FAIL — Test CRC count: ____ / 14 · missing: ____________

#### C8 — [ ] The app is fine without cd-paranoia

```sh
mv ~/.local/bin/cd-paranoia ~/.local/bin/cd-paranoia.bak
```

1. Relaunch. *Set up drive* → **Analyze cache**. Expected: it says **cd-paranoia isn't
   installed** and points at *Tools → Setup & Updates… → Run setup…* — not a vague "could not be
   determined".
2. Rip a CD → works. **Cache defeat** keeps saying **Yes** because your drive's verdict is
   saved *per drive* and isn't re-probed — correct, it really was measured. What must never
   happen is a `Yes` on a drive that was never probed.
3. `~/Applications/platterpus-x86_64.AppImage --doctor` → **WARN**, not FAIL.
   (`~/Applications/` because accepting the first-run menu offer **moves** the file there;
   use `./platterpus-x86_64.AppImage` only if you declined it.)
4. Restore: `mv ~/.local/bin/cd-paranoia.bak ~/.local/bin/cd-paranoia`

**Result:** ☐ PASS ☐ FAIL — message said: ____________

#### C9 — [ ] Cache probe: no disc, and cancel mid-probe

1. **Empty drive** → **Analyze cache** → expected: a clear message, no hang, no crash.
2. Disc in, start **Analyze cache**, then **close the dialog while it runs** — see A14,
   which is the same action with the fix now in place.

**Result:** ☐ PASS ☐ FAIL — notes: ____________

#### C10 — [ ] Settings persist across a restart

Turn **both** toggles on → OK → fully quit → relaunch → reopen Settings.

```sh
grep -E "secure_rerip_dynamic|rerip_offset_variant" ~/.config/platterpus/config.toml
```

- Expected: `secure_rerip_dynamic = false` (verify-every-track **ON** — stored inverted)
  and `rerip_offset_variant = true`

**Result:** ☐ PASS ☐ FAIL — values: ____________

#### C11 — [ ] Contradictory settings degrade sensibly

**"Verify every track"** ON *and* **"Max reads"** = **Off (0)** → rip a CD.

- Expected: completes normally; one Copy CRC per track, **no fabricated Test CRC**, no
  crash. (No second read exists to compare, so there must be no Test CRC.)

Put **Max reads** back to 2 afterwards.

**Result:** ☐ PASS ☐ FAIL — notes: ____________

#### C12 — [ ] Log checksum survives the library auto-move

Set **"Move finished rips to"** to a library folder, rip a CD so it auto-moves, then in the
*new* location:

```sh
head -n -1 *"(EAC-compatible).log" | sha256sum   # must match the last line
```

**Result:** ☐ PASS ☐ FAIL — matched: ☐ yes ☐ no

#### C13 — [ ] Nothing was lost in the update

```sh
grep -E "output_dir|read_offset|library_dir" ~/.config/platterpus/config.toml
```

Expected, unchanged across v0.5.12 → v0.5.18: `output_dir = "/home/rmccann/Music/rips"`,
working dir `~/.cache/platterpus`, `read_offset = 667` with "Apply this read offset to
every rip" ticked (in *Set up drive…* since 2026-09-24; it was a Settings tick-box
called "…to rips" before), the drive's *"confirmed — two independent sources agree"* trust line, and the
cache-defeat **Yes** measurement.

> One deliberate change to watch for: an output or library folder that is **not mounted**
> at launch is a *warning*, not an error. It used to be an error, and an error-level field
> gets reset to its default on load — so a rip library on a NAS or removable disk that
> happened to be unmounted was silently retargeted to `~/Music/rips`. If you use a
> removable library folder, unmount it, relaunch, and confirm your path is **still in the
> config**.

**Result:** ☐ PASS ☐ FAIL — anything reset? ____________

#### C16 — [ ] UI spot-check

- [ ] *Help → User Guide* mentions **Analyze cache** and **Verify every track**, and says
      CTDB verification is **on by default**
- [ ] Every Settings control shows a tooltip on hover; the CTDB tooltip also says "on by
      default"
- [ ] *Help → About Platterpus…* shows the version you recorded in this section's step 0, and correct Qt/Python info
- [ ] Disc-panel values can be selected and copied with the mouse. Selecting a MusicBrainz
      ID and pasting must still give the whole ID.
- [ ] Force-stop a disc scan: the message says *"click Rescan disc to try again"* and does
      not offer to "switch to the cyanrip backend in Settings" (there is no such setting)

**Result:** ☐ PASS ☐ FAIL — notes: ____________

---

### D — ⭐ One question that unblocks the worst bug still open

**Not a pass/fail test — a fact I need.** This is the highest-value thing in the whole
sheet.

#### D1b — [ ] ⭐ The small follow-up: a subset rip of a disc that IS in AccurateRip

Two minutes of clicking, no shell needed. Police disc in, **untick tracks 1 and 2**,
Start rip, let it finish, then:

```sh
grep -A3 -i "accurip" *"Every Breath"*/*.log | head -40
```

- Expected: at least one track shows a **confidence number** (e.g. `Accurip: 200`), not
  just `not found`.
- If instead every track says `not found` on a disc your full rips have always matched,
  **that is the interesting answer** — it would mean `-l` breaks the lookup, and #55 needs
  the bigger fix after all. Tell me either way.

**Result:** ☐ confidence reported ☐ all "not found" — paste one track's block: ____________

#### D3 — [ ] ⭐ Nothing to run — but the most interesting thing your run surfaced

Fixing the gap row made me diff your two logs of the **same disc in the same drive**, and
they disagree in a way neither log's wording had made visible:

| | EAC 1.8 | cyanrip 0.9.3 |
|---|---|---|
| `Gap handling` | `Appended to previous track` | `None signalled` |
| Per-track `Pre-gap length` | **present, 10 of 14** | **none** |

**EAC finds pregaps that cyanrip does not** — on ten of the fourteen tracks (3, 6, 11 and 12 have none in EAC's log either). EAC runs its own gap-detection pass; cyanrip
reports only what the disc's TOC signalled, and on the Police disc the TOC signalled
nothing. Both tools then append the gap to the previous track, so **your audio is
unaffected and your CRCs are unaffected** — this is the archival *record* being less
complete than EAC's, not the rip being wrong.

This is the same gap as this section's **§E** (build cyanrip `master` for `INDEX 00`), which is now
much better motivated: it isn't a cosmetic cue-sheet nicety, it is the one measurable
place our archival record is thinner than EAC's. I've pinned the disagreement with a test
so nobody later "fixes" it by making our log print EAC's string regardless.

Nothing for you to do here — just don't read the differing row as a bug when you compare.

**Result:** noted ☐

#### D4 — [ ] Your call, not a bug: should typed titles rename the files?

Your run put the right titles in the **tags** and the right titles in the **`.cue`** — but
the files on disk are `03 - Track 03.flac`, not `03 - three3.flac`. That's how the unknown
-disc path works today: cyanrip names files from the placeholder titles it was given, then
Platterpus writes your typed tags over the top afterwards.

Defensible either way, so it's your decision rather than something I'll just change:

- **Rename to match** — "good music, good cover image, good everything" argues for it; the
  filename is the first thing you see in a file manager.
- **Leave placeholders** — filenames stay stable if you retag later, and renaming is one
  more failure mode between a good rip and a written file.

**Result:** ☐ rename them ☐ leave them ☐ discuss

---

### E — retired: the setup wizard builds the pinned fork (KDD-33)

There is no hand-build step any more. *Tools → Setup & Updates… → Run setup…* clones the fork, detaches
onto the handshake-verified pin, compiles it and re-exports it, and `--install-ripper` is the
same step engine from a terminal — so the `INDEX 00` work arrives with the pin. Do **not**
build upstream `master` over it: that replaces the binary every other result on this sheet is
about, and moving the ripper build is a handshake event rather than a test step.

---

### F — ⭐ The three things we OWE the cyanrip fork

**Read this if you have a disc and half an hour.** Nothing in §F gates a handshake
round. Three of the items we owe them can
only be produced on your rig — they are not "nice to have", they are the artifacts no fixture
can stand in for, and the next round will ask for them. Each one below says exactly what to
run and exactly what to send, so nothing has to be re-derived at the time.

Everything here is **text only**. Never send audio (Critical rule #8) — the logs and CRCs
prove what is needed.

#### F1 — [ ] ⭐⭐ H9: a disc with a NON-ZERO pre-gap on a non-first track

**Why it is owed.** Their pre-gap emission was verified exactly on one disc: 13 sub-channel
entries, 1 lead-in, zeros on tracks 3/6/11/12, 9 `Gaps:` rows. That is an **existence proof,
not a range** — every pre-gap on that disc was zero, so the code path that reports a *real*
gap has never been exercised against their output. A25 is the same hunt from our side; this
is the same disc doing double duty.

**What to run.** A normal rip, nothing special. The candidates are, in order of odds:
a CD-Extra / enhanced CD (audio tracks plus a data track — the data track's pre-gap is
usually non-zero), a live album with indexed applause, or an early-90s pressing.

**What to send.** The album's `.platterpus.json`, the cyanrip `.log`, the `.cue`. If the
`Gaps:` block shows any value other than `0`, say so in the message — that is the whole point
and I would rather not have to find it.

**If every disc you try reports all zeros:** that is still a result. Send one, and say how
many discs you tried. "Three discs, all zero" tells the fork something a silent absence does
not.

#### F2 — [ ] ⛔ H10: the overread log line — **DO NOT RUN ON THE BDR-209D**

**Two corrections, 2026-08-19. Read both before doing anything with this item.**

**(1) The flag is `-O`, not `-x`.** This heading said `-x` for months. `-x` is the *fork's*
`--cache-probe`, a different flag doing a different thing; `-x/--force-overread` belonged
to **the ripper Platterpus used before cyanrip**, retired with it in KDD-18. The hazard table is
`docs/dependency-contracts.md`.

**(2) It is not "expected to be fine" — it is measured to hang, on this exact drive.**
The previous version of this item said upstream warns it *can* freeze an unsupporting drive
and that the BDR-209D was expected to be fine. That was written before we knew: on
**2026-07-22** overread hung the BDR-209D for roughly 23 minutes — 13 of 14 tracks ripped
perfectly, then the last track's lead-out froze the progress bar near 100%. This item was
still instructing an operator to enable it and rip.

**So this item is BLOCKED, not pending.** It needs a *different drive*, and it is not worth a
rig session on the one we have.

**Superseded on this drive, 2026-10-19, by a bounded read.** The fork's `.24` (`93afa15`)
bounds `-O`: a frame the drive refuses is written as silence and counted per track,
`Beyond disc: N of M frames refused (written as silence)`, and every later build does the
same (`fork_source.BUILD_TAGS_BOUNDING_OVERREAD`, each read from its source).
`overreadprobe.txt` reads the last track with it on the BDR-209D, under the script verb's
fixed 300-second limit, and stops before reading unless the installed ripper is one of
those builds (`expect-ripper-bounds-overread`; `TASKS.md` R24). That script is the route on this drive, and the Settings toggle stays
off; the procedure below is for a second drive. If a second optical drive ever comes into the picture, the
procedure is: Settings → Overread on → rip one track → send the cyanrip `.log` (the line is
near the top, beside `Overread mode:` / `Underread mode:`) → Overread back off.

**Why it is still owed at all.** We ship the toggle, so our parser's handling of the accept
line is written against the fork's published format string and nothing else. A drive that
*refuses* is a documented outcome and equally useful — but a drive that *hangs* costs a
session and tells us nothing we do not already know.

#### F3 — [ ] ⭐⭐⭐ H12/G2/A7: the forced-error corpus — the highest-value artifact we owe

**Why it is owed, and why I will not fabricate it.** Their fatal-message inventory is 128
strings at round 12, of which 84 are proven from control flow; the rest rest on the wording
of a message, on a `goto` label neither side can settle from source, or on `genopt`'s own
class. A run that *forces* each state and records the string, its exit code and the exact
argv settles them empirically. (The numbers move every round — 115/83 was round 6's, and
this line quoted it four rounds after it expired. The authority is
`src/platterpus/ripper_message_inventory.py`, which
`tests/test_ripper_error_surfacing.py::test_the_inventory_is_not_behind_the_newest_published_contract`
holds to the newest committed contract.)

I could hand-build this corpus from reading their control flow. I deliberately have not,
because a corpus built from my reading of their code is a fixture carrying **my assumptions
about their code** — which is the §4d failure this project has now hit from three directions
(`docs/testing.md` §5.ab, §5.ac). It has to come from a real binary refusing real conditions.

**What to run — five states, each one command, all safe and reversible.** Run each from a
terminal so you get the exit code. `cyanrip` here is the host export
(`~/.local/bin/cyanrip`).

| # | State to force | Command | Then record |
|---|---|---|---|
| 1 | No disc in the drive | eject the tray, then `cyanrip -d /dev/sr0 -N` | the message, and `echo $?` |
| 2 | No such device | `cyanrip -d /dev/sr99 -N` | the message, and `echo $?` |
| 3 | Offset unset | `cyanrip -d /dev/sr0 -N` with **no** `-s` | the message, and `echo $?` |
| 4 | Track out of range | disc in, `cyanrip -d /dev/sr0 -N -t 99=` | the message, and `echo $?` |
| 5 | Speed not supported | `cyanrip -d /dev/sr0 -N -S 99` | the message, and `echo $?` |

**What to send.** For each: the **exact command you typed**, the **complete output** (stderr
included — `cyanrip … 2>&1 | tee case1.txt` captures both), and the **exit code**. All five in
one text file is ideal. The exit code matters as much as the message: our probes read a
non-zero exit as *"the tool is not installed"*, which is how the `-V` blocker nearly shipped.

**None of these can damage anything.** Every one is cyanrip refusing to start. No disc is
written, no file is created, and case 1 does not need a disc at all.

---

### Priority, if you only have an hour

**Updated 2026-08-01 for v0.6.0.** Ordered so the cheap ones come first and each one makes
the next easier.

1. **A24** — two minutes, no disc, and it proves the single-file change works. Do it against
   the cancelled JSON you already have, *before* anything else.
2. **A26** — the buttons you reported. Four clicks and one `grep`. This is the only test that
   can tell me whether I actually fixed your problem or merely a neighbouring one.
3. **A28** — thirty seconds on a cancelled rip; re-checks the document that contradicted
   itself.
4. **A27** — the 0-byte cue. Needs one short *completed* rip, which A20 can double as.
5. **A20** — the contaminated album folder. Still the ugliest bug of the batch and the only
   one that needs a messy folder to see. You started this last time; it is worth finishing.
6. **D1b** — one subset rip of the Police disc; still the last thing gating the #55 fix.
7. **F3** — the forced-error corpus. Five one-line commands, no disc needed for the first,
   nothing written to disk. **This is the single highest-value thing on the whole list right
   now**, because it is the one artifact no fixture can fabricate and the next round will ask
   for it. Roughly ten minutes.
8. **F2** — ⛔ **blocked; do not run it on this drive.** Overread is `-O`, not `-x`, and it
   hung the BDR-209D for ~23 minutes on 2026-07-22. Read F2 before touching overread at all.
9. **F1** — a non-zero pre-gap disc. Free if you are already hunting one for A25.

*If the hour runs out: A24 + A26 cost about five minutes together and answer the two things
this release is actually about. If you have ten minutes and no disc, do **F3** — it needs no
disc and it unblocks a release on both sides.*

---

### Send back

**One file per album is now enough.**

1. **The `.platterpus.json`** for each album you rip. It contains cyanrip's `.log`, the
   `(EAC-compatible).log` and the `.cue` **as text inside it** — you no longer need to
   attach those three separately, and you no longer need to hunt for them in Dolphin.
2. **This sheet, filled in** — the ☐ boxes and the blanks are the parts no file can carry.
3. Only when a test explicitly asks for it, the terminal output it names:
   - the `grep "declined to open"` from **A26**
   - the `ls -la` and `metaflac --show-tag` from **A20**
   - the `grep "Pregap LSN:"` from **A25**
   - the `grep` from **D1b**, the `--compare` output from **C2**

`~/.local/share/platterpus/log.txt` is only needed if something goes wrong *outside* a rip
(a crash at launch, a failed update) — a rip's own session log is already embedded in that
album's JSON.

**Never send audio** — no `.flac`, no `.wav`, not even briefly (§0's warning, Critical
rule #8). The JSON, the logs, the `.cue` and the CRCs prove bit-perfection without it.

**From section F, separately, because it goes to a different place:** F1/F2/F3's output is
forwarded to the cyanrip fork as an input to the next handshake round, so keep it in its own
file(s) and say which case each one is. Exit codes included — a message without its exit code
is half the answer.

Plus anything surprising, even on a test that passed. And specifically: **any rip that dies
with `rip stream error:`** — that is the v0.5.20 fix's signature and I want the log at once.

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

File issues at the repo's Issues page (Help → About Platterpus… has the link). Keep one
issue per distinct failure.

## After a test passes

- Update the marker (`[ ]` → `[x]`, or `[?]` on failure) with the date and notes.
  In the **Hardware test checklist** a passed case is removed instead, and the record
  of what passed and when goes to `docs/session-log.md` (its own intro says so).
- Land the follow-up the test unblocks (Test 1 → GUI wiring; Tests 3/4/5/6 →
  README updates; Test 7 → README caveat removal).
- Update `TASKS.md` and `CHANGELOG.md`.

---

*Last updated for Platterpus v0.7.127.*
