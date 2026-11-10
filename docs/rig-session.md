# Rig session — the current sheet

> **Which builds this run is for is not written here.** The Platterpus release, the
> cyanrip build it installs by default and the build a handshake round is testing all
> move with each release, so they are read where the code states them:
> **Help → About Platterpus…** (its *Ripper* section names the default build and any
> *Build under test*), `src/platterpus/deps/fork_source.py`, and the generated map in
> [`DEPENDENCIES.md`](../DEPENDENCIES.md#the-full-map-machine-readable-bomcdxjson). What
> the open round asks a run to show is in its laps under
> [`docs/handshake/`](handshake/).
>
> **Drive:** Pioneer BDR-209D 1.51, read offset +667.

**This is the one rig sheet.** It is rewritten in place when the procedure changes,
never joined by a sibling. Superseded originals are in [`docs/archive/`](archive/) with
their audit trail intact.

---

## What the next session is for: round 38's drive test

Round 38 stays open until tracks 3 and 5 of the reference disc have proper answers
(the owner, 2026-11-05; our round 38 lap 7, S17 to S27). This session gathers them, in
four phases, in this order. **Every rip run is unattended**: it never stops to ask you
anything, and you touch the disc only **between** runs. **Nothing here changes the
drive's firmware, and nothing is burned.** What the drive can do (PureRead, the speed
it chooses, whether it accepts a set speed) is *not determined* until the drive itself
answers, which is what phases 1 to 3 ask it.

| Phase | Where | What | When | About |
|---|---|---|---|---|
| 0 | Bazzite | update Platterpus to 0.7.121 and install `.30`, the build under test | first, once 0.7.121 is out | 10 min |
| 1 | Bazzite | one read-only drive query; Runs A, B, C | after phase 0, on 0.7.121 with `.30` | an estimate of 2 to 3 h, of which you are needed twice, a few minutes each (see *Your time* below) |
| 2 | Bazzite | track 9's sub-channel read two ways; `cdrdao read-toc` | straight after Run C, in the same paste (the fork confirmed the commands in its lap 8) | 10 min |
| 3 | Windows 11, then Bazzite | Pioneer's utility: screenshots, PureRead to Perfect, Run D, put it back | after phase 2 | an estimate of 1 to 1 h 30 min |
| 4 | Bazzite | one Full acceptance run, on the same 0.7.121 with `.30` | after phase 3 | 2 h 31 min last time (2026-11-04) |

**One script does every terminal step: `docs/rig-scripts/drivetest.sh`** (the owner,
2026-11-05: *"is there not a way you can give me to make all these test automated …
instead of 15 steps where i am copy and pasting?"*). It replaced fifteen pastes. It
checks the build, installs the read-only tools, reads the drive, runs Runs A, B and C
and phase 2, packs each run's logs (never audio), writes its own times in UTC to
`~/platterpus-rig/drivetest38/drivetest.log` (the log sheet, kept for you), and ends by naming **one
file to upload**. It keeps the machine awake while it runs, and **it resumes**: running
the same command again after a stop carries on from the step that stopped
(`bash drivetest.sh status` lists them; a marker in `~/platterpus-rig/drivetest38/state/` per step).

**Everything lives in one folder: `~/platterpus-rig/`**, the folder the app already keeps
every rig session in (named to mirror the fork's `~/cyanrip-rig`). The script lives at
`~/platterpus-rig/drivetest.sh`, and the test writes only to
`~/platterpus-rig/drivetest38/`. On its first run it **moves** what the first version of
this sheet left loose in your home folder (`~/drivemode.txt`, `~/drivespeed.txt`,
`~/drivemode/`, `~/drivetest.sh`) into that folder: the drive readings already taken
are reused, and nothing is deleted. Deleting `~/platterpus-rig/drivetest38/` removes the
whole test.
It fetches the current `drivemode.txt` and `drivespeed.txt` from `main` each time, so a
fix to a rip script reaches the test without a release. Both pick the reference disc as
the **BMG club release** by its MusicBrainz ID (`d14a7546…`), the release the owner rips
it as (2026-11-05: *"make sure you are choosing the correct album, i have been manually
choosing the highlighted 3rd option"*); they picked row 1, the 2003 GB release, before.

**It retries a run that stopped before its first rip, and only that.** The first
attempt at Run A (2026-11-05, 22:24 UTC, 0.7.121 with `.30`) stopped in its first three
minutes when two of the app's own disc reads overlapped at start-up and neither
finished within 120 s (the shared probe slot, fixed for the next release). Nothing had
been read from the disc for the test, so a retry loses nothing. A run that stopped
after its rips began is packed and kept, never retried: a second run would be a
different session.

**Your time.** You are needed four times, a few minutes each:

| When | What you do | Then |
|---|---|---|
| Phases 1 and 2 | the three commands below | it runs Run A unattended (an estimated 30 to 40 min) |
| After Run A | it ejects the disc and asks: wipe it from the centre outward with a soft, dry, lint-free cloth, put it back, type what you used | Run B, Run C and phase 2 unattended (an estimated 1 h 30 min to 2 h); upload the one file it names |
| Phase 3 | Windows (below), then `bash ~/platterpus-rig/drivetest.sh perfect` | Run D unattended; upload the one file it names |
| After phase 3 | Windows again, then `bash ~/platterpus-rig/drivetest.sh restored` | upload the one file it names, with your screenshots |

*How the times are estimated, since no run of these scripts has been timed yet:*
track 3 is 4:51 and track 5 is 4:01 long (`output_reference/EAC_flac/eac_baseline_police_classics.log`),
this drive reads them at 2.8x to 3.1x (the fork's lap 8 S7), and each rip adds
spin-up, a cache probe and the FLAC encode: about 2 to 3 minutes a rip. Run A and Run
B are 12 rips each; Run C is 17, one of them up to twelve reads of track 5. The script's
log will measure them.

**Send every upload to both sessions**, this one and the fork's (the fork's lap 8 S11):
each side files and reads every run.

### Phase 0 — Bazzite, update and install `.30`

The drive test runs on the fork's `.30` (`0.9.4-rc3+platterpus.30`, `cyanrip@5cc1c6b`), so it
also tests the new release (the owner, 2026-11-05). Its scripts ask the drive for its
own PureRead answer with `--read-vendor-settings`, which only `.30` has. The script
refuses to start on any other build and says how to pick `.30`.

1. Open Platterpus. **Tools → Setup & Updates… → Check for updates**, and take the
   newest release (it restarts itself).
2. **Tools → Setup & Updates… → Choose a build…**, and pick the one labelled as the
   build under test, `.30`.
3. Close Platterpus.

### Phases 1 and 2 — Bazzite, three commands

Put the reference disc in the drive, open a terminal, and run:

```sh
mkdir -p ~/platterpus-rig && curl -L -o ~/platterpus-rig/drivetest.sh https://raw.githubusercontent.com/rmccann-hub/Platterpus/main/docs/rig-scripts/drivetest.sh
bash ~/platterpus-rig/drivetest.sh
```

It may ask for your password once (installing `sg3_utils` and `cdrdao` inside the
container; both only *read* from the drive), and asks one optional question about the
room. Then leave it until it ejects the disc and asks you to wipe it. After the wipe it
needs nothing until it prints **DONE. Upload this ONE file**, naming
`~/platterpus-rig/drivetest38/platterpusdrivetest38phase12.tar.gz`.

**Write down each time the computer or the drive is powered off**, with the time: a
restart counts, a shutdown counts more. Pioneer documents that a setting not stored in
the drive is forgotten at power-off, so the drive readings can only be read against
that list. Put the list in the message with the upload.

What it runs, in order (the commands are in the script, each with its reason):

1. **The drive's own settings, read-only**, saved to `~/platterpus-rig/drivetest38/dumps/`: Pioneer's
   settings query (READ BUFFER, buffer `0xF4`) into `pioneer-f4.txt`; the standard
   settings pages and the feature list into `before.txt` (the CD Read feature's DAP and
   C2 bits are only in the feature list); and the same Pioneer query sent by `.30`
   itself into `cyanrip-vendor.json` and `.txt` (the fork's round 38 lap 12 S7). The two
   Pioneer answers should hold the same 256 bytes, which says both programs read the
   drive. No `sudo` is needed: Linux lets any user who can open the drive send these
   read-only commands (the fork's lap 8, S11). Skipped when they are already saved, as
   they were on 2026-11-05.
2. **Run A**, disc left in: `drivemode.txt`, twelve rips of tracks 5 and 3, early and
   late. Its first rip also asks the drive for its settings (`--read-vendor-settings`;
   the owner's word of 2026-11-05, TASKS R137), so every run's record carries the
   drive's own PureRead answer.
3. **The wipe**, the one stop.
4. **Run B**, disc just reinserted: `drivemode.txt` again.
5. **Run C**, disc left in: `drivespeed.txt`, the speed test. If the drive refuses a set
   speed, each fixed-speed rip fails in seconds saying *"Device does not support
   changing speeds!"*: that is an answer, and the run carries on. Its last rip reads
   track 5 up to twelve times in one rip (`-Z 4 -r 12`, the fork's lap 8 S11), because
   the drive has given the verified read of track 5 in three earlier sessions.
6. **Phase 2**, below.

### Phase 2 — track 9 read two ways (confirmed by the fork, lap 8 S12 to S14)

Read-only, about 10 minutes, disc left in, run by the script after Run C. Track 9's
sub-channel at LBA 145560 to 145575 is read six times, raw and formatted alternately,
and before each read the drive's cache is flushed by reading 312 other sectors (its
cache holds 128 to 255). Each read is timed inside the container, so the time is the
read's alone and not the container starting (the fork's lap 10 S9). An uncached read on
this drive took about 360 ms and a cached one about 1 ms, so a read that returns in a
few milliseconds came from the cache, and we report it rather than count it. Then
`cdrdao` reads the disc's table of contents, a second program's view of track 9's
pregap. The fork reads the files.

### Phase 3 — Windows 11, then Bazzite

**3.1 Windows: look before changing anything.**

1. Restart into **Windows 11**.
2. Download `PioneerBDR-209-211_DriveUtility_v1.2.0.3.exe` from Pioneer's page,
   https://pioneer.jp/device_e/product-e/ibs/device_e/dev00001r_e.html (its
   *Drive Utility* row for the BDR-209/211 series), and install it (*Run as
   administrator* if it asks).
3. Start it. **Whether it opens on this drive is itself an answer**: Pioneer lists it for
   the BDR-209EBK/UBK and 211, not the 209DBK. If it says no supported drive is found,
   screenshot that, and that is the whole of phase 3.
4. If it opens: screenshot the **Pure Read** page and the **Advanced Quiet Drive** page,
   **before changing anything**. Do not change Quiet Drive.

**3.2 Windows: set PureRead to Perfect.** Choose **Perfect**, Apply, screenshot again.
Then **restart** (not shut down) straight into **Bazzite**, so the drive stays powered.

**3.3 Bazzite: `bash ~/platterpus-rig/drivetest.sh perfect`.** It reads the drive's settings again
before any rip (`pioneer-f4-perfect.txt`, `after-perfect.txt`), says whether the Pioneer
bytes changed, runs Run D (`drivemode.txt`, disc left in), and names
`~/platterpus-rig/drivetest38/platterpusdrivetest38phase3.tar.gz`.

**3.4 Quiet Drive off, then the speed test again (optional; agreed with the fork,
2026-11-10).** Run C read every rip at 2.9x to 3.5x whether 4x or 24x was asked, and the
drive's settings block reports Quiet mode on, which may cap the speed (the fork's
reading; a guess until the drive shows it). Restart into Windows, set Pure Read back to
what your first screenshot showed **and** turn **Advanced Quiet Drive off**, Apply,
screenshot, restart into Bazzite, and run `bash ~/platterpus-rig/drivetest.sh quiet`. It
reads the settings again, runs the speed test as Run E, and names
`~/platterpus-rig/drivetest38/platterpusdrivetest38quiet.tar.gz`. To skip it, set only
Pure Read back and go to 3.5.

**3.5 Put it back.** Restart into Windows, set Advanced Quiet Drive back as your first
screenshot showed (and Pure Read, if 3.4 was skipped), Apply, restart into Bazzite, and
run `bash ~/platterpus-rig/drivetest.sh restored`. It reads the Pioneer settings once
more and says **BACK TO ORIGINAL** or **NOT THE SAME**, then names
`~/platterpus-rig/drivetest38/platterpusdrivetest38restored.tar.gz`. Send it with every
screenshot and your list of power-offs.

### Phase 4 — Bazzite, one Full run on the same release with `.30`

The release repairs a rip from CTDB on its own when every proof passes, so this run is
the first hardware proof of that, and the Full run that tests the release.

1. **Run the Full acceptance test:** **Tools → Advanced → Run acceptance test…**, choose
   **Full**, and leave it (2 h 31 min on 2026-11-04; it holds sleep and the screen off and puts
   your settings back at the end). **During the run, don't close any other Platterpus
   window or any terminal you have used distrobox in.**

**Send after phase 4:** the one `platterpusbundle….tar.gz` from the run's session folder
under `~/platterpus-rig/`.

### If something goes wrong

**When something fails, the script decides whether going on still means something.**
It **stops** only when nothing can run: no AppImage, the wrong cyanrip build, no disc,
under 2 GB free, or a run that cannot start three times. When a reading or a run fails
**after it produced something** (a drive query, a run whose rips began, the track 9
reads, `cdrdao`), it keeps what was made, writes the **full error** (the failing step's
whole text, the command, its exit code and output) to `errors.txt` in the test folder, prints
it, and **goes on**, because every later step is a separate answer. **Either way it
builds the upload**: a stopped test names `platterpusdrivetest38…stopped.tar.gz`, holding everything
measured so far, `errors.txt`, the app's log and every script run's transcript and
report. Running the same command again resumes from the step that stopped.

| What you see | What to do |
|---|---|
| `STOPPED: no Platterpus AppImage` | Put the AppImage in `~/Applications` (where the app's own updater keeps it). |
| `STOPPED: cyanrip is not platterpus.30` | Phase 0, step 2, then run the script again. |
| `STOPPED: the drive did not report a disc ready` | Check the disc is in and the tray closed, then run it again. |
| `STOPPED: … stopped before its first rip three times` | Upload the `…stopped.tar.gz` it names: it holds every attempt's full error. |
| `… ENDED WITH A FAILED STEP after its rips began` | Not a stop: it kept the run and carried on. Its report is in the upload. |
| It asks *"Use them as runA?"* | Folders from a Run A you started by hand were found. **y** only if that run finished. **n**, the default, moves them aside, puts their logs in the upload, and runs Run A again. |
| `a cyanrip from an earlier run is still running` | It waits up to 10 minutes for it to finish. If it says so after 10 minutes, eject the disc, put it back, and run the same command again. |
| `permission denied` from `sg_raw` or `sg_modes` | Tell the Platterpus session: the script would need `sudo` inside the container on this machine. |

## What each step measures, and what is not verified

The owner's rule of 2026-11-05: *"measure thing you can test and verify, and if you
cannot measure and verify, ask the need for the test, or how to do better."* So each
step says which of the two it is.

| Step | What it measures | Verified before you run it | Not verified, and how we find out |
|---|---|---|---|
| the script itself | nothing; it runs the steps | `shellcheck` 0.11 finds nothing; a stand-in run (fake AppImage, container and drive, 2026-11-05) took it through a run that stops before its first rip and is retried, three packed runs, the wipe stop, phase 2, the upload (no audio inside, checked by listing it), resume, `perfect` and `restored`; its Pioneer-byte comparison read the owner's real `pioneer-f4.txt` and matched `.30`'s JSON byte for byte | what the stand-in does not: a real AppImage's report, real `sg_turs` on this drive, `systemd-inhibit` on Bazzite. The first real run settles them |
| tools | nothing; installs | `tests/test_rig_scripts.py` checks every verb and setting the rip scripts use | that `sudo` inside the container asks no password on your machine: the command either runs or asks |
| drive readings | the drive's own settings and feature list | the command's shape against `sg_raw` and `sg_get_config` 1.46's own help (`-R` opens the drive **read-only**, `-r 256` reads 256 bytes, the output is a hex dump); the 10-byte READ BUFFER command against the SCSI layout | what buffer `0xF4`'s bytes mean on this firmware: a published census's reading, which the Windows step checks (A4 in lap 7) |
| rips folder | nothing; finds a folder | the setting is a top-level `output_dir` in `config.toml`, default `~/Music/rips` (`config.py:146`, `:63`) | none |
| Runs A, B, D | tracks 3 and 5, early and late, disc left in and reinserted | the script's verbs, labels and folder names (`dm…`) by test | how long a run takes: the first run measures it |
| Run C | tracks 3 and 5 at the drive's own speed, 4x and 24x | the same, and the folder names (`ds…`) | whether this drive accepts a set speed at all: that is what the run finds out |
| 2 | track 9's sub-channel, and a second program's table of contents | the READ CD commands' bytes and sizes (the fork's lap 8 S2, S12, S13); `cdrdao read-toc --device` against `cdrdao` 1.2.4's own help | whether the cache flush worked: each pass's time says, and a pass that came from the cache is reported, not counted |
| 3 | PureRead's effect, if the utility opens | the utility's own help text, read from its archive | whether it opens on the BDR-209DBK, and whether a setting made in Windows survives a restart into Bazzite: the dumps before and after show it |
| 4 | the whole app, with repair running on its own | the release's own CI and suite | the repair on real hardware: this run is its first proof |

**Where a test cannot settle a question, the round says so** rather than guessing:
lap 7's S23 lets an assumption close as *named by both sides as what no run here can
settle*.

## Before any run

- **Do not enable Overread (`-O`) on this drive.** It has run on the BDR-209D and hung
  the drive for about 23 minutes (`docs/dependency-contracts.md`). No script in this
  sheet sets it.
- **Do not update the drive's firmware** for this test, and do not flash another
  model's firmware to get a feature: either can leave the drive unusable, and a
  different firmware would make every earlier result incomparable.
- **Never send audio.** Bundles and the script's uploads carry logs, cue sheets,
  reports and CRCs only (Critical rule #8).

## A Full run, in general

When a handshake round asks for a Full run (phase 4 above is one), the steps are phase
4's: update, install the build under test if the round names one (**Tools → Setup &
Updates… → Choose a build…**, then check **Help → About Platterpus…** shows the same
commit on its *Installed* line as on its *Build under test* line), then **Tools →
Advanced → Run acceptance test…**, **Full**. Only a Full run counts as evidence; Quick
and Standard check the setup. The next version gate is **0.8.1**: two `full-green` rows
on at least two machines and two distros (`docs/testing.md` §5B). `-Z` is on in dynamic
mode, and the `[plan]` block at the top of each rip's live log names every flag it uses.

---

*Last updated for Platterpus v0.7.121.*
