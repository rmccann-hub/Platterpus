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
| 1 | Bazzite | one read-only drive query; Runs A, B, C | now, on 0.7.120 | not yet measured; an estimate of 2 to 3 h |
| 2 | Bazzite | track 9's sub-channel read two ways; `cdrdao read-toc` | when I say the fork has confirmed the commands | 10 min |
| 3 | Windows 11, then Bazzite | Pioneer's utility: screenshots, PureRead to Perfect, Run D, put it back | after phase 2 | an estimate of 1 to 1 h 30 min |
| 4 | Bazzite | update to the next release; one Full acceptance run | when I say 0.7.121 is out | 2 h 31 min last time (2026-11-04) |

What to send after each phase is at the end of it. Send it here; you do not need to send
it to the fork, which reads our repository.

### Phase 1 — Bazzite, now (0.7.120, no update needed)

**1.1 Get the two test scripts and the read-only drive tools** (once). Put the reference
disc in the drive, open a terminal, and run:

```sh
BASE=https://raw.githubusercontent.com/rmccann-hub/Platterpus/main/src/platterpus/rig_scripts
curl -L -o ~/drivemode.txt "$BASE/drivemode.txt"
curl -L -o ~/drivespeed.txt "$BASE/drivespeed.txt"
wc -c ~/drivemode.txt ~/drivespeed.txt
distrobox enter ripping -- sudo dnf install -y sg3_utils
```

`wc` should print 7,753 and 8,155. The last line installs tools that only *read*
from the drive.

**1.2 Ask the drive for its settings (read-only).** The first command is Pioneer's own
settings query (READ BUFFER, buffer `0xF4`); the second lists the drive's standard
settings pages:

```sh
mkdir -p ~/drivemode/dumps
distrobox enter ripping -- sudo sg_raw -R -r 256 /dev/sr0 3c 02 f4 00 00 00 00 01 00 00 > ~/drivemode/dumps/pioneer-f4.txt 2>&1
distrobox enter ripping -- sudo sh -c 'sg_inq /dev/sr0; for c in 0 1 2 3; do echo "=== page control $c ==="; sg_modes -a -c $c /dev/sr0; done' > ~/drivemode/dumps/before.txt 2>&1
cat ~/drivemode/dumps/pioneer-f4.txt; wc -l ~/drivemode/dumps/before.txt
```

If `pioneer-f4.txt` shows an error such as *illegal request*, run the first command
again with `3c 01 f4` in place of `3c 02 f4`, into `pioneer-f4-alt.txt`.

**1.3 Find your rips folder** (keep this terminal open; later commands use `$RIPS`; in a
new terminal, run this line again):

```sh
RIPS="$(grep -E '^output_dir' ~/.config/platterpus/config.toml | sed -E 's/.*= *"(.*)"/\1/')"; RIPS="${RIPS:-$HOME/Music/rips}"; echo "$RIPS"
```

**1.4 Run A — disc left in.** Close Platterpus if it is open, then:

```sh
~/Applications/platterpus-x86_64.AppImage --run-script ~/drivemode.txt
```

When the app log says **DONE** (about 40 minutes), move the run's folders aside so the
next run cannot overwrite them, and pack their logs (no audio):

```sh
mkdir -p ~/drivemode/runA && mv "$RIPS"/dm* ~/drivemode/runA/
tar czf ~/drivemode/runA-logs.tar.gz --exclude='*.flac' -C ~/drivemode runA
```

**1.5 Run B — disc wiped and reinserted.** Eject the disc, wipe it gently from the centre
outward with a soft, dry, lint-free cloth, put it back and wait about 10 seconds. Then
the same command as Run A, and when it says **DONE**:

```sh
mkdir -p ~/drivemode/runB && mv "$RIPS"/dm* ~/drivemode/runB/
tar czf ~/drivemode/runB-logs.tar.gz --exclude='*.flac' -C ~/drivemode runB
```

**1.6 Run C — the speed test, disc left in.**

```sh
~/Applications/platterpus-x86_64.AppImage --run-script ~/drivespeed.txt
```

If the drive refuses a set speed, each fixed-speed rip fails in seconds saying *"Device
does not support changing speeds!"* and the run finishes early: that is an answer, let
it finish. When it says **DONE**:

```sh
mkdir -p ~/drivemode/runC && mv "$RIPS"/ds* ~/drivemode/runC/
tar czf ~/drivemode/runC-logs.tar.gz --exclude='*.flac' -C ~/drivemode runC
```

**Send after phase 1:** `~/drivemode/dumps/pioneer-f4.txt` (and `-alt` if made),
`~/drivemode/dumps/before.txt`; for each of Runs A, B and C, the newest bundle from
`~/.local/share/platterpus/bundles/` (`ls -t ~/.local/share/platterpus/bundles/ | head -3`
lists the three) and its `run*-logs.tar.gz`; and a line saying whether anything was
unusual (a run that stopped early, the room unusually warm or cold).

### Phase 2 — Bazzite, when I say the fork has confirmed the commands

Two short read-only reads the fork asked for: track 9's sub-channel read raw and
formatted, and `cdrdao`'s reading of the disc's table of contents. Our lap 7 (S18,
S19) proposes the exact commands and asks the fork to confirm them first, because
drive commands are their side's knowledge. **This section is rewritten in place with
the confirmed commands**; until then there is nothing to run here.

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

**3.3 Bazzite: read the settings again, then Run D.** Before any rip:

```sh
distrobox enter ripping -- sudo sg_raw -R -r 256 /dev/sr0 3c 02 f4 00 00 00 00 01 00 00 > ~/drivemode/dumps/pioneer-f4-perfect.txt 2>&1
distrobox enter ripping -- sudo sh -c 'sg_inq /dev/sr0; for c in 0 1 2 3; do echo "=== page control $c ==="; sg_modes -a -c $c /dev/sr0; done' > ~/drivemode/dumps/after-perfect.txt 2>&1
```

Then Run D, with the disc left in: the Run A command, and when it says **DONE**:

```sh
mkdir -p ~/drivemode/runD && mv "$RIPS"/dm* ~/drivemode/runD/
tar czf ~/drivemode/runD-logs.tar.gz --exclude='*.flac' -C ~/drivemode runD
```

**3.4 Windows: put it back.** Restart into Windows, set Pure Read back to what your
first screenshot showed, Apply, and restart into Bazzite.

**Send after phase 3:** every screenshot; the two dumps; Run D's newest bundle and
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
| 1.1 | nothing; downloads | both URLs serve the files on `main` (7,753 and 8,155 bytes, read 2026-11-05); `tests/test_rig_scripts.py` checks every verb and setting the scripts use | that `sudo` inside the container asks no password on your machine: the command either runs or asks |
| 1.2 | the drive's own settings | the command's shape against `sg_raw` 1.46's own help (`-R` opens the drive **read-only**, `-r 256` reads 256 bytes, the output is a hex dump); the 10-byte READ BUFFER command against the SCSI layout | what buffer `0xF4`'s bytes mean on this firmware: a published census's reading, which the Windows step checks (A4 in lap 7) |
| 1.3 | nothing; finds a folder | the setting is a top-level `output_dir` in `config.toml`, default `~/Music/rips` (`config.py:146`, `:63`) | none |
| 1.4, 1.5 | tracks 3 and 5, early and late, disc left in and reinserted | the script's verbs, labels and folder names (`dm…`) by test | how long a run takes: the first run measures it |
| 1.6 | tracks 3 and 5 at the drive's own speed, 4x and 24x | the same, and the folder names (`ds…`) | whether this drive accepts a set speed at all: that is what the run finds out |
| 2 | track 9's sub-channel, and a second program's table of contents | nothing yet: the commands wait on the fork's confirmation | the fork's lap 8 |
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
