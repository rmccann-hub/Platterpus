# Getting started

This guide takes you through your first archival rip: one ordinary audio CD, from
downloading Platterpus to a folder of verified FLAC files. Allow about twenty minutes
for the setup, plus the rip itself, which depends on the disc and the drive.

You need an audio CD, a CD, DVD or Blu-ray drive, and an Internet connection, because
the disc is looked up on MusicBrainz and checked against AccurateRip and CTDB.

Words in bold, like **Start rip**, are labels you will see in the app, spelled as
they appear there.

## 1. Download Platterpus and open it

Download `platterpus-x86_64.AppImage` from the project's Releases page on GitHub. It
is one file: there is nothing to install.

Before it can run, your system has to be told that the file is a program. In your
file manager, right-click the file, open its properties, and on the permissions page
tick the option that lets it run as a program. Then double-click it.

## 2. Let Platterpus set itself up

The first time it opens, Platterpus may offer to add itself to your applications
menu. Accept if you want it there.

It then asks **Set up Platterpus**: the ripping tool, cyanrip, runs in a small
container so that it never touches the rest of your system, and Platterpus installs
it for you. Answer **Yes**. It takes a few minutes and may ask for your password
once. Nothing here needs a terminal.

If you said no, or want to run it again, it is in **Tools → Setup & Updates…** as
**Run setup…**.

## 3. Set up your drive

Every drive starts reading a few samples early or late. The *read offset* corrects
that, and a rip is only bit-perfect, and only matches AccurateRip, when it is right.
You set it once per drive.

After setup, Platterpus offers to do this. You can also open it any time from
**Tools → Setup & Updates…** with **Set up drive…**.

For most drives the offset is already known from AccurateRip's list of drives and is
filled in for you: press **Save offset**. No disc is needed. If your drive is not in
that list, type its offset into **Read offset (samples):** by hand.

## 4. Look at the settings

Open **Tools → Settings…**. The defaults are already the archival ones, so for your
first rip you do not need to change anything:

- **Output format:** is FLAC, lossless, and the file every other format is made from.
- The rip is checked against AccurateRip, and **Verify with CTDB after a rip** is on.
- A track AccurateRip cannot confirm is read again until two reads agree.
- **Cover art:** is embedded in every file.

One thing is off by default: **Write an EAC-compatible log beside each rip**. Tick it
if you want a log in the layout Exact Audio Copy users know. Platterpus always keeps
cyanrip's own log and its report either way.

Your music goes under **Output directory:**, one folder per album.

## 5. Insert the disc

Put the CD in the drive. Platterpus reads it and looks it up on MusicBrainz.

If more than one release matches, **Pick a MusicBrainz release** asks which one is
yours. Choose the one whose country, year and barcode match your copy.

The album appears: **Album title:**, **Album artist:**, **Year:** and the track list.
Correct anything that is wrong here. What you see is what is written into the files.

## 6. Rip

Press **Start rip**. Every track is ripped unless you untick it in the track list.

The progress bar shows how far the rip has got, with the track being read and an
estimate of the time left. You can press **Cancel** at any time.

## 7. Read the verdict

When the rip finishes, a verification banner appears above the results and stays
there:

- green, *Bit-perfect*: every track matches other people's rips of the same disc in
  AccurateRip. This is the archival standard.
- amber: some tracks matched and some did not. The table says which.
- grey: AccurateRip has no rips of this disc to compare with. That is not a failure,
  but the audio has not been checked against anyone else's.

The per-track results are in the table below the banner, and the CTDB result is on
the **Details** tab.

## 8. What you get

In the album's folder:

- one FLAC file per track, tagged, with the cover art inside it;
- a cue sheet, the map of the disc's tracks;
- cyanrip's log, the record of the rip, which cyanrip can verify was not edited;
- the report, `.platterpus.json`, with every result in a form a program can read;
- the EAC-style log, if you turned it on.

Keep the logs and the report with the music. They are the proof of what was read.

## 9. If a track is not fully verified

Two results deserve a second look:

- *One frame only*: AccurateRip matched one frame of the track, 1/75 of a second,
  and nothing else. The rest of the track is not verified.
- A track that needed heavy re-reading, or whose reads never agreed: the drive could
  not read it the same way twice.

Clean the disc and rip it again. **Help → User Guide…** explains every result in
full, and how to compare the new rip with the last one.

*Last updated for Platterpus v0.7.101.*
