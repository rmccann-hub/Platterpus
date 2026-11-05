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
| 1 | Bazzite | one read-only drive query; Runs A, B, C | now, on 0.7.120 | an estimate of 2 to 3 h, of which you are needed twice, a few minutes each (see *Your time* below) |
| 2 | Bazzite | track 9's sub-channel read two ways; `cdrdao read-toc` | straight after Run C, in the same paste (the fork confirmed the commands in its lap 8) | 10 min |
| 3 | Windows 11, then Bazzite | Pioneer's utility: screenshots, PureRead to Perfect, Run D, put it back | after phase 2 | an estimate of 1 to 1 h 30 min |
| 4 | Bazzite | update to the next release; one Full acceptance run | when I say 0.7.121 is out | 2 h 31 min last time (2026-11-04) |

**Your time.** Phase 1 and 2 need you at the keyboard twice:

1. **Sitting 1, about 10 minutes:** steps 1.1 to 1.4 (download, install, the drive
   query, start Run A). Then leave it, an estimated 30 to 40 minutes.
2. **Sitting 2, about 5 minutes, when Run A says DONE:** pack Run A, wipe the disc and
   put it back, and paste **one block** (step 1.5) that runs Run B, Run C and phase 2
   one after another without you, an estimated 1 h 30 min to 2 h, overnight or during
   work is fine.
3. **Then send** the files listed at the end of phase 2.

Phase 3 (Windows) is a third sitting of about an hour, whenever suits you after that.

*How the times are estimated, since no run of these scripts has been timed yet:*
track 3 is 4:51 and track 5 is 4:01 long (`output_reference/EAC_flac/eac_baseline_police_classics.log`),
this drive reads them at 2.8x to 3.1x (the fork's lap 8 S7), and each rip adds
spin-up, a cache probe and the FLAC encode: about 2 to 3 minutes a rip. Run A and Run
B are 12 rips each; Run C is 17, one of them up to twelve reads of track 5. The runs
themselves will measure it.

What to send after each phase is at the end of it. **Send it to both sessions**, this
one and the fork's (the fork's lap 8 S11): each side files and reads every run.

### Phase 1 — Bazzite, now (0.7.120, no update needed)

**1.1 Get the two test scripts and the read-only drive tools** (once). Put the reference
disc in the drive, open a terminal, and run:

```sh
BASE=https://raw.githubusercontent.com/rmccann-hub/Platterpus/main/src/platterpus/rig_scripts
curl -L -o ~/drivemode.txt "$BASE/drivemode.txt"
curl -L -o ~/drivespeed.txt "$BASE/drivespeed.txt"
wc -c ~/drivemode.txt ~/drivespeed.txt
distrobox enter ripping -- sudo dnf install -y sg3_utils cdrdao
```

`wc` should print 7,753 and 8,647. The last line installs tools that only *read* from the drive (`cdrdao` is for
phase 2).

**Through every phase, write down each time the computer or the drive is powered
off**, with the time: a restart counts, a shutdown counts more. Pioneer documents that
a setting not stored in the drive is forgotten at power-off, so the dumps can only be
read against that list.

**1.2 Ask the drive for its settings (read-only).** The first command is Pioneer's own
settings query (READ BUFFER, buffer `0xF4`); the second lists the drive's standard
settings pages and its feature list (the CD Read feature's DAP and C2 bits are only in
the feature list). Each file starts with the time it was taken. No `sudo` is needed:
Linux lets any user who can open the drive send these read-only commands (the fork's
round 38 lap 8, S11):

```sh
mkdir -p ~/drivemode/dumps
dump() { distrobox enter ripping -- sh -c "date -u; $2" > ~/drivemode/dumps/$1.txt 2>&1; }
dump pioneer-f4 'sg_raw -R -r 256 /dev/sr0 3c 02 f4 00 00 00 00 01 00 00'
dump before 'sg_inq /dev/sr0; sg_get_config -q /dev/sr0; sg_get_config -q -H /dev/sr0; for c in 0 1 2 3; do echo "=== page control $c ==="; sg_modes -a -c $c /dev/sr0; done'
cat ~/drivemode/dumps/pioneer-f4.txt; wc -l ~/drivemode/dumps/before.txt
```

If `pioneer-f4.txt` shows an error such as *illegal request*, run
`dump pioneer-f4-alt 'sg_raw -R -r 256 /dev/sr0 3c 01 f4 00 00 00 00 01 00 00'`. If
either says *permission denied*, put `sudo ` before each command inside the quotes.
(`dump` lasts as long as the terminal; in a new one, paste its line again.)

**1.3 Find your rips folder** (keep this terminal open; later commands use `$RIPS`; in a
new terminal, run this line again):

```sh
RIPS="$(grep -E '^output_dir' ~/.config/platterpus/config.toml | sed -E 's/.*= *"(.*)"/\1/')"; RIPS="${RIPS:-$HOME/Music/rips}"; echo "$RIPS"
```

**1.4 Run A — disc left in.** Close Platterpus if it is open, then:

```sh
~/Applications/platterpus-x86_64.AppImage --run-script ~/drivemode.txt
```

Leave it until the app log says **DONE** (an estimated 30 to 40 minutes).

**1.5 Sitting 2: pack Run A, wipe the disc, then Runs B and C and phase 2 in one go.**
First pack Run A (this moves its folders aside so Run B cannot overwrite them, and packs
their logs, never audio):

```sh
mkdir -p ~/drivemode/runA && mv "$RIPS"/dm* ~/drivemode/runA/
tar czf ~/drivemode/runA-logs.tar.gz --exclude='*.flac' -C ~/drivemode runA
```

Then eject the disc, wipe it gently from the centre outward with a soft, dry,
lint-free cloth (if you use a liquid, say which when you send), put it back and wait
about 10 seconds. Then paste **this whole block**, and leave it:

```sh
APP=~/Applications/platterpus-x86_64.AppImage
"$APP" --run-script ~/drivemode.txt
mkdir -p ~/drivemode/runB && mv "$RIPS"/dm* ~/drivemode/runB/
tar czf ~/drivemode/runB-logs.tar.gz --exclude='*.flac' -C ~/drivemode runB
"$APP" --run-script ~/drivespeed.txt
mkdir -p ~/drivemode/runC && mv "$RIPS"/ds* ~/drivemode/runC/
tar czf ~/drivemode/runC-logs.tar.gz --exclude='*.flac' -C ~/drivemode runC
# phase 2: track 9 read two ways, then cdrdao (explained under Phase 2 below)
mkdir -p ~/drivemode/track9 && cd ~/drivemode/track9 && date -u > times.txt
flush() { distrobox enter ripping -- sh -c 'for l in 0 26 52 78 104 130 156 182 208 234 260 286; do sg_raw -R -r 61152 /dev/sr0 be 00 $(printf "%02x %02x %02x %02x" 0 0 $((l>>8)) $((l&255))) 00 00 1a 10 00 00 >/dev/null 2>&1; done'; }
for n in 1 2 3; do
  flush; { echo "raw$n"; distrobox enter ripping -- bash -c "time sg_raw -R -o raw$n.bin -r 39168 /dev/sr0 be 00 00 02 38 98 00 00 10 10 01 00"; } >> times.txt 2>&1
  flush; { echo "q$n"; distrobox enter ripping -- bash -c "time sg_raw -R -o q$n.bin -r 37888 /dev/sr0 be 00 00 02 38 98 00 00 10 10 02 00"; } >> times.txt 2>&1
done
ls -l *.bin >> times.txt
distrobox enter ripping -- cdrdao read-toc --device /dev/sr0 ~/drivemode/track9/cdrdao.toc > cdrdao-output.txt 2>&1
cd ~ && tar czf ~/drivemode/track9.tar.gz -C ~/drivemode track9
echo "Runs B and C and phase 2 done $(date -u)"
```

When it prints **Runs B and C and phase 2 done**, everything for phases 1 and 2 is on
disk.

That is Run B (`drivemode.txt` again, disc just reinserted) and then Run C
(`drivespeed.txt`, the speed test, disc left in). In Run C, if the drive refuses a set
speed, each fixed-speed rip fails in seconds saying *"Device does not support changing
speeds!"*: that is an answer, and the run carries on. Its last rip reads track 5 with
up to twelve reads in one rip (`-Z 4 -r 12`, the fork's lap 8 S11), because the drive
has given the verified read of track 5 in three earlier sessions.

**1.6 Phase 2 is already in that block** (its last part); the section below says what
it does and why.

**Send after phases 1 and 2:** `~/drivemode/dumps/pioneer-f4.txt` (and `-alt` if made),
`~/drivemode/dumps/before.txt`; for each of Runs A, B and C, the newest bundle from
`~/.local/share/platterpus/bundles/` (`ls -t ~/.local/share/platterpus/bundles/ | head -3`
lists the three) and its `run*-logs.tar.gz`; and a line saying whether anything was
unusual (a run that stopped early, the room unusually warm or cold); your list of
power-offs; and `~/drivemode/track9.tar.gz` from phase 2.

### Phase 2 — Bazzite, track 9 read two ways (confirmed by the fork, lap 8 S12 to S14)

Read-only, about 10 minutes, disc left in. Track 9's sub-channel at LBA 145560 to
145575 is read six times, raw and formatted alternately, and before each read the
drive's cache is flushed by reading 312 other sectors (its cache holds 128 to 255).
Each read is timed: an uncached read on this drive took about 360 ms and a cached one
about 1 ms, so a read that returns in a few milliseconds came from the cache, and we
report it rather than count it. Then `cdrdao` reads the disc's table of contents, a
second program's view of track 9's pregap. **Step 1.5's block runs it for you**; this
is the same block on its own, for running it again or separately:

```sh
mkdir -p ~/drivemode/track9 && cd ~/drivemode/track9 && date -u > times.txt
flush() { distrobox enter ripping -- sh -c 'for l in 0 26 52 78 104 130 156 182 208 234 260 286; do sg_raw -R -r 61152 /dev/sr0 be 00 $(printf "%02x %02x %02x %02x" 0 0 $((l>>8)) $((l&255))) 00 00 1a 10 00 00 >/dev/null 2>&1; done'; }
for n in 1 2 3; do
  flush; { echo "raw$n"; distrobox enter ripping -- bash -c "time sg_raw -R -o raw$n.bin -r 39168 /dev/sr0 be 00 00 02 38 98 00 00 10 10 01 00"; } >> times.txt 2>&1
  flush; { echo "q$n"; distrobox enter ripping -- bash -c "time sg_raw -R -o q$n.bin -r 37888 /dev/sr0 be 00 00 02 38 98 00 00 10 10 02 00"; } >> times.txt 2>&1
done
ls -l *.bin >> times.txt
distrobox enter ripping -- cdrdao read-toc --device /dev/sr0 ~/drivemode/track9/cdrdao.toc > cdrdao-output.txt 2>&1
cd ~ && tar czf ~/drivemode/track9.tar.gz -C ~/drivemode track9
```

Each read is timed inside the container, so the time is the read's alone and not the
container starting (the fork's lap 10 S9: a start that varies by a few hundred
milliseconds could hide a cached pass). The fork reads the files.

(Send it with phase 1's files, above.)

### Phase 3 — Windows 11, then Bazzite

**3.1 Windows: look before changing anything.**

1. Restart into **Windows 11**.
2. Download `PioneerBDR-209-211_DriveUtility_v1.2.0.3.exe` from Pioneer's page,
   https://pioneer.jp/device_e/product-e/ibs/device_e/dev00001r_e.html (its
   *Drive Utility* row for the BDR-209/211 series), and install it (*Run as
   administrator* if it asks).
3. Start it. **Whether it opens on this drive is itself an answer**: Pioneer lists it for
   the BDR-209EBK/UBK and 211, not the 209DBK. If it says no supported drive is found,
   screenshot that and go to 3.4.
4. If it opens: screenshot the **Pure Read** page and the **Advanced Quiet Drive** page,
   **before changing anything**. Do not change Quiet Drive.

**3.2 Windows: set PureRead to Perfect.** Choose **Perfect**, Apply, screenshot again.
Then **restart** (not shut down) straight into **Bazzite**, so the drive stays powered.

**3.3 Bazzite: read the settings again, then Run D.** In a new terminal, first paste
the `dump` line from 1.2 and the `RIPS` line from 1.3 (a restart forgets both). Then,
before any rip:

```sh
dump pioneer-f4-perfect 'sg_raw -R -r 256 /dev/sr0 3c 02 f4 00 00 00 00 01 00 00'
dump after-perfect 'sg_inq /dev/sr0; sg_get_config -q /dev/sr0; sg_get_config -q -H /dev/sr0; for c in 0 1 2 3; do echo "=== page control $c ==="; sg_modes -a -c $c /dev/sr0; done'
```

Then Run D, with the disc left in: the Run A command, and when it says **DONE**:

```sh
mkdir -p ~/drivemode/runD && mv "$RIPS"/dm* ~/drivemode/runD/
tar czf ~/drivemode/runD-logs.tar.gz --exclude='*.flac' -C ~/drivemode runD
```

**3.4 Windows: put it back.** Restart into Windows, set Pure Read back to what your
first screenshot showed, Apply, and restart into Bazzite. Then check it really went
back (in a new terminal, paste the `dump` line from 1.2 first):

```sh
dump pioneer-f4-restored 'sg_raw -R -r 256 /dev/sr0 3c 02 f4 00 00 00 00 01 00 00'
```

**Send after phase 3:** every screenshot; the three dumps (`pioneer-f4-perfect`, `after-perfect`, `pioneer-f4-restored`); your list of power-offs; Run D's newest bundle and
`runD-logs.tar.gz`. If the utility did not open, the screenshot of what it said is the
whole of phase 3.

### Phase 4 — when I say 0.7.121 is out: update, then one Full run

0.7.121 carries the CTDB repair running on its own after a rip, and a script run's
bundle that holds every rip's log (so the `tar` steps above become unnecessary).

1. **Update Platterpus:** open it, **Tools → Setup & Updates… → Check for updates**, and
   take the newest release (it restarts itself). **Help → About Platterpus…** should
   then name 0.7.121.
2. **The ripper needs no change** unless I say so: 0.7.121 keeps `.29`.
3. **Run the Full acceptance test:** **Tools → Advanced → Run acceptance test…**, choose
   **Full**, and leave it (2 h 31 min on 2026-11-04; it holds sleep and the screen off and puts
   your settings back at the end). **During the run, don't close any other Platterpus
   window or any terminal you have used distrobox in.**

**Send after phase 4:** the one `platterpusbundle….tar.gz` from the run's session folder
under `~/platterpus-rig/`.

### If something goes wrong

| What you see | What to do |
|---|---|
| `No such file or directory` for the AppImage | `ls ~/Applications ~/Downloads \| grep -i platterpus`, and use that path. |
| `mv: cannot stat …/dm*` (or `ds*`) | The rips went elsewhere: `find ~ -maxdepth 4 -type d -name 'dmfiveearly1'` (or `dsnospeed1`) shows where; use that folder in place of `$RIPS`. |
| A run stops before DONE | Send what it produced, with a note saying where it stopped. Do not restart it mid-run. |
| The app says fewer than five tracks | Reinsert the disc, wait, run again. |
| `sg_raw: command not found` | Step 1.1's last line did not finish; run it again. |
| `permission denied` from `sg_raw` or `sg_modes` | Check the command starts with `distrobox enter ripping -- sudo`. |

## What each step measures, and what is not verified

The owner's rule of 2026-11-05: *"measure thing you can test and verify, and if you
cannot measure and verify, ask the need for the test, or how to do better."* So each
step says which of the two it is.

| Step | What it measures | Verified before you run it | Not verified, and how we find out |
|---|---|---|---|
| 1.1 | nothing; downloads | both URLs serve the files on `main` (7,753 and 8,647 bytes once this sheet's change is merged); `tests/test_rig_scripts.py` checks every verb and setting the scripts use | that `sudo` inside the container asks no password on your machine: the command either runs or asks |
| 1.2 | the drive's own settings and feature list | the command's shape against `sg_raw` and `sg_get_config` 1.46's own help (`-R` opens the drive **read-only**, `-r 256` reads 256 bytes, the output is a hex dump); the 10-byte READ BUFFER command against the SCSI layout | what buffer `0xF4`'s bytes mean on this firmware: a published census's reading, which the Windows step checks (A4 in lap 7) |
| 1.3 | nothing; finds a folder | the setting is a top-level `output_dir` in `config.toml`, default `~/Music/rips` (`config.py:146`, `:63`) | none |
| 1.4, 1.5 | tracks 3 and 5, early and late, disc left in and reinserted | the script's verbs, labels and folder names (`dm…`) by test | how long a run takes: the first run measures it |
| 1.6 | tracks 3 and 5 at the drive's own speed, 4x and 24x | the same, and the folder names (`ds…`) | whether this drive accepts a set speed at all: that is what the run finds out |
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
- **Never send audio.** Bundles and the `tar` lines above carry logs, cue sheets,
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

*Last updated for Platterpus v0.7.120.*
