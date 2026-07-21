"""User-facing help text (Help → User Guide) plus shared project metadata.

This lives as a module-level string rather than a packaged data file on
purpose: it is then available identically from a source checkout, a `pipx`
install, and the single-file AppImage with zero package-data/MANIFEST wiring
(this project has been bitten by AppImage packaging gaps before — see the
CA-cert and recipe-bug notes in CLAUDE.md). To edit the guide, edit the string
below; the Help dialog renders it as Markdown.
"""

from __future__ import annotations

# Project metadata, also shown in the About dialog.
REPO_URL: str = "https://github.com/rmccann-hub/Platterpus"
ISSUES_URL: str = f"{REPO_URL}/issues"
LICENSE_NAME: str = "GPL-3.0-only"
TAGLINE: str = "EAC-equivalent archival-quality audio-CD ripping for Linux."

# The user guide, rendered as Markdown by HelpDialog. Keep it task-oriented and
# in step with the actual UI — when a feature changes, update the relevant
# section here too.
USER_GUIDE: str = """\
# Platterpus — User Guide

A friendly front-end for the **cyanrip** CD-ripping tool. It rips audio CDs at
archival quality (EAC-equivalent), naming and tagging tracks from
**MusicBrainz** and verifying the result against AccurateRip and CTDB. Every rip
produces a lossless **FLAC** master; you can also have **WavPack**, **MP3**, or
**WAV** derived from it (see *Output format* in Settings).

## How it's wired

The GUI runs on your desktop and calls the host-exported ripping tool
(`~/.local/bin/cyanrip`), which transparently does the actual ripping inside
the `ripping` Distrobox container.
You don't interact with the container directly — the GUI handles it.

## Ripping a CD — the basics

1. **Insert an audio CD** and pick your drive in the drive selector.
2. The GUI looks the disc up on MusicBrainz and fills in the album, artist, and
   track list. If several releases match, choose the right one.
3. Check or edit the album/artist/track fields — your edits are written to the
   FLAC tags.
4. Click **Start rip**. Progress shows an overall bar plus the current task.
5. When it finishes, the status line reports a fidelity verdict and the results
   pane shows a verification banner (see below). Files land under your output
   folder (see Settings).

## Understanding the results — is my rip trustworthy?

After a rip, a bold **verification banner** sits above the per-track table and
tells you at a glance whether the rip can be trusted:

- 🟢 **Green — "Bit-perfect: all N tracks verified against AccurateRip"** —
  every track's audio matches the shared AccurateRip database. This is the
  archival gold standard: other people's rips of the same disc produced the
  exact same audio.
- 🟡 **Amber — "M of N tracks verified"** — some tracks matched and some didn't.
  The unmatched ones either aren't in the database or read differently this
  time; check the per-track table and consider re-ripping (the **Max reads to
  confirm a shaky track** setting helps marginal discs).
- ⚪ **Grey — "no tracks matched the database"** — normal for a disc nobody has
  submitted (a home-burned CD-R, or an obscure pressing). It does *not*
  automatically mean a bad rip — AccurateRip simply has nothing to compare
  against. But the per-track **Copy CRC** only shows the FLAC losslessly encodes
  what was read; it does *not* prove the read itself was correct or the read
  offset right, so the audio isn't independently verified here.

A track counts as "verified" only when AccurateRip reports a **confidence of 1
or more** (how many submitted rips share its checksum) — the app never calls a
track verified on a guess. If you enabled **Verify with CTDB**, its result
appears just below, marked the same way by symbol and text: a CTDB match shows
green (verified — its checksum is hardware-confirmed, the same standing as an
AccurateRip match), and no match shows amber.

Alongside the rip, two records are saved next to your music: the backend's
human-readable **`.log`**, and a **`.platterpus.json`** report with the same
results in a machine-readable form (per-track CRCs, AccurateRip/CTDB outcomes,
the verdict) — handy for scripting, re-verifying later, or attaching to a report.

## What the trickier results mean

- **"Offset-variant" / "partially accurate"** (a `~` in the table, and an amber
  verdict): the track's audio matches a *known* pressing in AccurateRip, but one
  shifted by a fixed offset from the most common pressing — so it isn't the exact
  canonical checksum. Most of the time this just means you have a slightly
  different pressing, and it's fine. **But** if you re-rip the same disc and a
  track's result *changes*, that's not a pressing difference — it's a
  read-stability problem on that track (see re-rip comparison below).
- **"Track(s) N needed heavy re-reading"** (an amber footnote): the drive had to
  re-read those tracks a lot (or a secure re-read never settled on one answer).
  Even if they matched AccurateRip, that's the earliest sign a track might not be
  reproducible — worth a re-rip to confirm. *(This only fires when the ripper
  itself re-read; a disc that quietly reads one wrong-but-consistent answer per
  pass won't trip it — that's what the re-rip comparison is for.)*
- **AccurateRip says "mostly accurate" but CTDB says "no match"** — this is *not*
  a contradiction. CTDB folds the whole disc into one checksum, so if even a
  couple of tracks differ from the common pressing the whole-disc CRC can't
  match. The app spells this out in a line under the CTDB result. AccurateRip is
  the per-track authority.

## Comparing a re-rip against the last one

Because each `.platterpus.json` records every track's checksum, you can compare
two rips of the *same disc* and see exactly what changed — the app can't do this
from memory, but the reports remember it. From a terminal (or the AppImage):

    platterpus --compare previous.platterpus.json later.platterpus.json

It prints a track-by-track table: which tracks are byte-for-byte identical, which
differ, and — for the ones that differ — **which rip is the better master** (an
exact AccurateRip match beats an offset-variant one). This is how you catch a
track that quietly regressed on a re-rip even though nothing looked wrong.

If a re-rip wins on some tracks and loses on others, assemble the best of both
into a new folder (non-destructive — your originals are untouched):

    platterpus --assemble-best-of BestOf/ rip1.platterpus.json rip2.platterpus.json

## Unknown discs

If MusicBrainz has no match (or you're offline), use **File → Rip as Unknown
Album…**. The track list is filled with placeholders you can edit; the folder is
named from the album artist/title you type.

## Stopping a rip

- **Cancel** stops the current rip. Because the reader runs inside the
  container, the drive can take a moment to spin down.
- If the drive keeps spinning, **Force stop** ejects and kills the reader. After
  Cancel the GUI also auto-escalates to a force-stop after a few seconds.
- **A disc *scan* can get stuck too** (a slow drive's table-of-contents read
  holding the drive). **Force stop** is available during a scan as well — it
  frees the drive without ejecting, so the disc stays in for a **Rescan disc**.
  A scan that times out frees the drive on its own.

## Settings (Tools → Settings)

- **Goal** — pick what you want the rip to be and the format/verification/quality
  options snap to good values for it: *Fast verified* (lossless, AccurateRip-
  checked — the recommended default), *Archival exact* (also CTDB-verify and
  smallest lossless files), or *Portable* (an MP3 copy for phones). You can still
  tweak any individual option below — that switches the Goal to *Custom*.
- **Output format** — *FLAC* (the lossless archival master, always produced),
  *WavPack* (also lossless, with tags), *MP3* (best-quality VBR for phones), or
  *WAV* (raw PCM — no tags or cover art). Non-FLAC formats are derived from the
  FLAC master, which is always kept, so you never lose the archival copy.
- **MP3 VBR quality** — only when the output format is MP3: 0 is best quality
  (~245 kbps, the recommended default) and 9 is the smallest files. It has no
  effect on the FLAC master, which is always lossless.
- **Output folder** and **file-name templates** (separate templates for known
  and unknown discs).
- **Move finished rips to** — optional library folder. When set, a successful
  rip's album folder is moved there automatically — but only once every
  post-rip check has finished (tagging, cover art, verification, checksums),
  so your library only ever receives finished, verified rips. If a folder
  with the same name already exists, the new rip lands beside it as
  "… (2)" — nothing is ever overwritten. Leave empty to keep rips in the
  output folder.
- **Cover art** — off, embedded, or saved as a file. The app fetches the front
  cover from the Cover Art Archive after the rip and embeds/saves it.
- **Max retries** — how many times the ripper retries a troublesome track
  before giving up.
- **Overread** — read the disc's very first/last samples from the
  lead-in/lead-out instead of writing them as silence (they sit there once the
  read offset is applied). **Off by default** — that matches how this app's
  EAC parity baseline was ripped, and only some drives can overread; an
  unsupported drive may freeze on it, so turn it on only if you know your
  drive supports overreading.
- **Max reads to confirm a shaky track** — Platterpus rips the disc once at full
  speed, then re-reads *only* the tracks that didn't match AccurateRip until this
  many reads agree, so a shaky track converges on a stable, repeatable read
  (which then has a better chance of matching AccurateRip) while a clean disc
  stays a single fast pass. It's **on by default** (2) — raise it for a badly
  scratched disc, or set it to *Off* to accept the first read even when a track
  can't be verified.
- **Verify with CTDB after a rip** — a second, whole-disc verification against
  the CUETools Database, alongside AccurateRip. A network check, off by default.
  Its checksum is now confirmed on real hardware, so a match reads as *verified*
  — the same bar as AccurateRip; a non-match can only ever under-claim, never
  falsely say "verified".
- **Verify FLACs after a rip** — decode each FLAC back and check it against its
  stored checksum (on by default). (**Re-compress FLACs** is shown but disabled:
  cyanrip already encodes FLAC at maximum compression, so there's nothing to
  gain.)
- **Read offset override** — set the drive read-offset by hand (the drive-setup
  wizard is the recommended way to set it).
- **Eject after a successful rip** — automatically eject the disc when a rip
  finishes (off by default). You can always eject by hand with the **Eject**
  button next to the drive picker.

## Where the app lives

When you accept the "Add to your applications menu?" offer, the app
moves itself from Downloads to `~/Applications` and the menu entry
points there — so cleaning out Downloads never removes it.

## Updates (Help → Check for updates)

Asks GitHub whether a newer release exists. If one does, the app updates
itself: the new version downloads in the background (with a progress
bar you can cancel), is verified against the release's published
checksum, and installs to `~/Applications` — then the app offers to
restart into the new version. Nothing changes if the download fails or
you cancel.

## Uninstalling (Tools → Uninstall Platterpus)

Removes everything the app installed: shortcuts, the cyanrip/metaflac/flac
commands, the ripping container, optionally a legacy `whipper.conf` and the
AppImage file, and the app's own settings and logs. **Your music is never
touched**, and Distrobox/podman stay installed (other containers keep working).
You'll confirm before anything is removed.

## Drive setup (Tools → Set up drive)

Sets your drive's **read offset** — the one calibration a bit-perfect rip
depends on (without the right offset, even a clean disc won't match AccurateRip).
For most drives the wizard already knows the right value (from
the bundled AccurateRip drive list) and pre-fills it, so it's a single
**Save offset** click — no disc needed. If your drive isn't in the list,
insert a popular commercial CD and click **Detect**, or type the offset by
hand. The value is saved to the app's own settings and applied to every rip
(cyanrip's read-offset option). Do this once per drive.

The disc panel shows a **Read offset** line for the selected drive telling you
*where* the offset came from and how confident we are — measured on your drive
(high), looked up from the AccurateRip list (medium), or entered by hand. If two
identical drives are connected, or the recorded offset disagrees with the
offset that will be applied, a warning appears there so a wrong offset can't
pass unnoticed.

## Troubleshooting

- **Disc not detected, or the first scan failed** → click **Rescan disc**
  (next to Refresh). The first read sometimes happens while the disc is
  still spinning up; a rescan almost always works.
- **No drive found** → *Tools → Diagnose drive access*. If it's a permissions
  problem it will tell you the exact `usermod` command to run (then log out and
  back in).
- **Drive keeps spinning after Cancel (or during a stuck scan)** → click
  **Force stop**.
- **Window goes black during a rip (KDE Plasma 6 / Wayland)** → the app now runs
  through XWayland automatically to avoid this. If you ever want native Wayland
  instead, launch with `QT_QPA_PLATFORM=wayland`.
- **Disc not identified** → check your network; you can still rip via *Rip as
  Unknown Album* and tag later.
- **Something else** → the log has the details; please attach it when reporting
  an issue. The quickest way to find it is **Help → Open logs folder…**, which
  opens the folder containing `log.txt` in your file manager. For a *verbose*
  log, turn on **Debug logging** in Settings, reproduce the problem, then attach
  that file — it records every step (off by default to keep the log light).

## More

- Project & issues: see **Help → About** for links.
- Dependencies (cyanrip, MusicBrainz Picard, etc.) are checked automatically at
  launch and from the Settings dialog.
"""
