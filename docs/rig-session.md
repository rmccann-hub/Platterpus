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

## What the next session is for

**No run is asked for.** No handshake round is open: round 40 closed on both sides'
`GO` on 2026-11-16, approving the fork's `.32` (`0.9.4-rc3+platterpus.32`,
`cyanrip@edb73dd`) with Platterpus 0.7.125 on the owner's Full run of 2026-11-14
(evidence `7faf1b9f`, `docs/testing.md` §5B), and round 41 has not opened. When a round
next asks for a run, its laps under [`docs/handshake/`](handshake/) say what it must
show, and *A Full run, in general* below says how to make one.

## Earlier rounds' sheets

Round 39's five-rip run (run 2026-11-11) and round 38's drive test (run 2026-11-09 and
2026-11-10) moved to [`archive/rig-session-e531a33.md`](archive/rig-session-e531a33.md)
and [`archive/rig-session-5cc1c6b.md`](archive/rig-session-5cc1c6b.md) on 2026-11-16,
after their rounds closed, as earlier sheets did.

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

*Last updated for Platterpus v0.7.125.*
