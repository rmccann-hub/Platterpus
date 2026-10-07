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

## What the next run is for

**The run a handshake round asks for, when it asks for one:** the newest Platterpus
release with the build that round is testing installed. The round's lap 1 is the one
that says what closes it; the steps below are what such a run takes. When no round is
testing a build, a run on the default build is still useful evidence about the pin.

**Only a Full run counts as evidence**; Quick and Standard are for checking the setup.
`0.7.100` is gated on a Full run with **zero failures in the ARCHIVAL sections**
(`docs/testing.md` §5B), and the field-evidence ledger has no `full-green` row yet.

## Three steps

1. **Put the reference disc in the drive** and open Platterpus. **Tools → Setup &
   Updates… → Check for updates** and take the newest release (it restarts).
2. **Install the build under test:** **Tools → Setup & Updates… → Choose a build…** and
   pick the one labelled as the build the handshake round is testing. **Help → About
   Platterpus…** should then show the same commit on its *Installed* line as on its
   *Build under test* line. Then **Tools → Advanced → Run acceptance test…**, choose
   **Full**, and leave it. It states its estimate when it starts, holds sleep and the
   screen off, stops in its first seconds if the ripper is not the build under review
   (saying what to install), and puts your settings back when it ends. **During the
   run, don't close any other Platterpus window or any terminal you have used
   distrobox in.**
3. **Upload the one `platterpusbundle….tar.gz`** from the run's session folder under
   `~/platterpus-rig/` here, and point the cyanrip session at it too.

## Before you start

- **Do not enable Overread (`-O`) on this drive.** It has run on the BDR-209D and hung
  the drive for about 23 minutes (`docs/dependency-contracts.md`). The acceptance
  script never sets it.
- **`-Z` is on, in dynamic mode.** A default rip reads the whole disc once at speed and
  re-reads with `-Z 2` only the tracks that miss AccurateRip; sections F and N pin the
  rip goal so the run covers both the default path and the whole-disc secure re-read.
  The `[plan]` block at the top of each rip's live log names every flag it is about to
  use.
- **Never send audio.** The bundle carries logs, cue sheets, reports and CRCs only
  (Critical rule #8).

---

*Last updated for Platterpus v0.7.100.*
