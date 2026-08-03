# Hardware test checklist — v0.6.0

> **Everything that still needs testing, in one place.** Anything that has already passed
> is gone from this sheet — the record of what passed and when lives in
> `docs/session-log.md`. Test IDs are stable across releases, so the gaps are deliberate.
> **Six sections retired since the last sheet** (A10, A19, B2, D1, D2 and D1's original
> probe): all answered by your 2026-07-30 run.
>
> Rig details, tool versions and expected values are pre-filled from your last six runs.
> You tick boxes and note anything that **differs** from what's printed.
>
> ## ⭐ THE BIG CHANGE: you only have to send ONE file now
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
>
> **Never send audio** — logs, `.cue`, `.platterpus.json` and CRCs only.

**Date:** ____________  ·  **App version tested:** ____________

---

## Reference (pre-filled — don't re-measure)

| | |
|---|---|
| Rig | Bazzite `7.1.3-ogc5.1.fc44.x86_64`, KDE 6, AppImage install |
| Drive | `PIONEER  BD-RW   BDR-209D 1.51` on `/dev/sr0` |
| Read offset | **+667** — confirmed, two independent sources agree |
| Cache defeat | **Yes** — measured (`cd-paranoia -A`: 140-sector cache, backseek flushes) |
| Tools | cyanrip 0.9.3 · flac/metaflac 1.5.0 · ffmpeg 8.1.2 · cd-paranoia 10.2 · Picard 2.13.3 |
| Settings | Overread **off** · offset-variant re-read **on** · verify-every-track **off** · max reads 2 · max retries 5 · adaptive ladder · EAC log **on** · debug log **on** |

**Test disc:** *The Police — Every Breath You Take: The Classics* — 14 tracks,
59:42.354, MB release `d14a7546-815b-43c6-8af6-35cff6cee1d0`, DiscID
`pNtImOkdBm9RMBIalzx0w9cfsYY-`.

Expected Copy CRCs — **all 14, from the run-5 baseline that matched EAC exactly**:

| 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|
| `B0D122E7` | `985AAE32` | `59D352DD` | `60D796AE` | `E0036697` | `B32769D6` | `CCBFF669` |

| 8 | 9 | 10 | 11 | 12 | 13 | 14 |
|---|---|---|---|---|---|---|
| `D723C1B0` | `6F6E4A5F` | `3A33519F` | `56BFC63D` | `D78CEAEF` | `DA6A4DAF` | `787BA2D6` |

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

### Wording changes since your last run — so they don't read as regressions

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
* The `.platterpus.json` report is **schema v12**. Two new blocks: `artifacts`, which holds
  the full text of the three files written beside it, and `completeness`, which finally
  states the **disc's** track count instead of leaving you to infer it from the track list.
  See A24 — a two-minute file check, not a rip.
* **The EAC-layout log can no longer say `All tracks accurately ripped` about a rip that was
  cancelled.** It used to measure against its own track list, which a cancel shrinks. See A28.
* **"Open externally…" and "Open rip folder" may now pop a dialog giving you the path**
  instead of doing nothing. That dialog is the *fix*, not a fault — it appears only when the
  desktop refuses the file. See A26.

---

## 0 — [ ] Update to v0.6.0

*Help → Check for updates…* → download → verify → restart. *Help → About* says **0.6.0**.
Nothing else to set up — your settings are already right (see above).

**Result:** ☐ PASS ☐ FAIL — version shown: ____________

---

## A — ⭐ New in v0.5.19 – v0.6.0 — only your rig can prove these

*Twenty-four findings were fixed across these three releases, all found by audits rather than by
anything going visibly wrong — which is exactly why they need a rig: the suite proves each
mechanism fires, and cannot prove the drive stops, that the right bytes got the right tags,
or that a verdict reads honestly to a person.*

***A20 is the one to do if you do only one.*** It is the ugliest bug of the batch (this
album's metadata, cover art and library transcodes being written into a *previous* rip's
leftover files) and it is the only one that needs a deliberately messy folder to see.

### A11 — [~] ⭐⭐ RE-RUN on v0.5.20: cancel, then quit within five seconds — **PARTIAL PASS 2026-07-30**

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

### A12 — [ ] Force stop is recorded as *cancelled*, not as a failure

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

### A13 — [ ] Closing the window mid-rip must not crash the app

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

### A14 — [ ] Cancelling the cache probe must actually stop the disc

`Analyse cache` runs `cd-paranoia -A`, which can take **minutes** and spins the disc the
whole time. Closing the dialog called a cancel hook that was a **no-op** — a do-nothing
default on the base class that this backend never overrode — so the flag was set and the
probe carried on to its 600-second ceiling. Three separate comments in the code claimed it
killed the process.

1. Disc in. *Tools → Set up drive…* → **Analyse cache**.
2. Wait ~15 seconds so it is genuinely reading, then **close the dialog**.

- Expected: the dialog closes immediately, the app stays responsive, and **the disc spins
  down within a few seconds**.
- Expected in the log: `cancelling` / `SIGKILL to the process group` for the probe.
- **The bug looked like:** the dialog closes but the drive keeps grinding for minutes.

```sh
ps aux | grep cd-paranoia | grep -v grep     # expect: nothing
grep -i "cache probe" ~/.local/share/platterpus/log.txt | tail
```

**Result:** ☐ PASS ☐ FAIL — spin-down seconds: ______ · leftover process: ☐ y ☐ n

### A15 — [ ] Quitting during the startup dependency check should be prompt

The launch dependency probe enters the container, which on a cold start takes tens of
seconds. Its cancel existed but **nothing called it** (the teardown omitted one argument),
so quitting in that window waited out the shutdown budget — roughly a ten-second "Not
Responding" window — and then abandoned the thread.

1. Make the container cold: `podman stop ripping` (or reboot).
2. Launch Platterpus and **quit within the first couple of seconds**, while it is still
   probing.

- Expected: it exits within about a second. No greyed-out "Not Responding" window.

**Result:** ☐ PASS ☐ FAIL — roughly how long to exit: ______ s

### A16 — [ ] "Rescan disc" mid-scan must stop the old reader

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

### A17 — [ ] ⭐ A disc that can't be read must say *why*

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

### A18 — [ ] "Set up drive" must not clip its own text when the window is small

Its minimum size was a hand-picked guess 185 px shorter than the content needs. Measured at
440×300, the intro label was **73 px short** — the last lines of the explanation of what a
read offset *is* simply weren't drawn.

1. *Tools → Set up drive…*
2. Try to make the dialog as small as it will go. Drag every edge.

- Expected: it **refuses** to shrink past the point where text would be cut off.
- Expected: every paragraph fully readable at the smallest size it allows; the
  accuraterip.com link visible and clickable.
- Expected: at most **one** scrollbar, in the results box — never two.

**Result:** ☐ PASS ☐ FAIL — any clipped text: ☐ y ☐ n · smallest size reached:
________×________

### A20 — [ ] ⭐⭐⭐ A contaminated album folder — the worst bug of the batch

**Do this one first if you do only one.** It is the highest-value test on this sheet and the
only one that needs a deliberately messy folder to see.

**What was wrong.** Six post-rip steps walked the album folder with a plain "every `.flac`
in here" scan instead of "the files *this* rip wrote": unknown-mode tagging, the
colon-restore pass, the FLAC re-compress, the transcode to your chosen format, and **both**
cover-art embed loops. So when a folder held files from an *earlier* rip, this disc's
metadata was written into them, they were re-compressed, they were **transcoded into your
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

### A21 — [ ] A tagging failure must not be reported as "Done."

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

### A22 — [ ] ⭐ "In the database, but nothing matched" must read as its own answer

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

### A23 — [ ] A green "Bit-perfect" must never sit above a failed check

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

### A24 — [ ] ⭐ Two-minute file check: schema v12 (no rip needed)

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
print("schema:      ", d["schema_version"])            # 12
print("completeness:", d["completeness"])              # expected / in_report / complete
for name, a in d["artifacts"].items():
    if name == "note":
        continue
    print(f"{name:9} exists={a['exists']} bytes={a.get('bytes')} "
          f"chars={len(a.get('text',''))} err={a.get('error')}")
PY
```

- Expected: `schema: 12`.
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

### A25 — [ ] ⭐⭐ Find a disc that can prove the pre-gap fix — the reference disc cannot

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

### A26 — [ ] ⭐⭐ The buttons you said "may or may not work" — v0.6.0's fix for your report

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

### A27 — [ ] ⭐ The 0-byte `.cue` — open question, and the answer is either way useful

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

### A28 — [ ] The status report and its own banner must agree — the bug your last run found

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

## B — Still unproven from earlier releases

### B3 — [ ] Quitting during the securing pass is recorded in the log too

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

### B5 — [ ] The desktop notification — the log can now answer for it

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

### B5c — [ ] ⭐ One scrollbar, and the mouse wheel does the obvious thing

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

### B6 — [ ] Your own `cover.jpg` survives a re-rip

The scratch file written for `metaflac` reused the name `cover.jpg` and then deleted it —
so the default setting destroyed a cover you had put there yourself.

1. Put any JPEG named `cover.jpg` into an already-ripped album folder.
2. Re-rip that disc, choose **Replace** when asked about the existing folder.

- Expected: your `cover.jpg` **still there, unchanged**, and no stray
  `.platterpus-cover-tmp*` left behind.

**Result:** ☐ PASS ☐ FAIL — cover survived: ☐ y ☐ n · stray temp file: ☐ y ☐ n

### B7 — [ ] A bad read offset is refused, visibly

*Tools → Set up drive…* → try an offset far outside the sane range. Then try to force one
past the widget by hand-editing `~/.config/platterpus/config.toml` to
`read_offset = 999999` and relaunching.

- Expected: a clear message naming the allowed range; **+667 still in effect afterwards**.
  It must never silently accept a bad value and reset to 0 on the *next* launch — that
  would rip the following session at the wrong offset.

**Result:** ☐ PASS ☐ FAIL — offset after the attempt: ____________

### B8 — [ ] Uninstall removes `cd-paranoia` too

*Tools → Uninstall Platterpus…* → **tick the host-exports item, untick everything else** →
run.

```sh
ls ~/.local/bin/ | grep -E "cyanrip|metaflac|flac|cd-paranoia"
```

- Expected: **all four gone.** `cd-paranoia` was being orphaned — the exact repeat of the
  `flac` bug from earlier.
- Re-run *Tools → Set up Platterpus…* afterwards to put them back.

**Result:** ☐ PASS ☐ FAIL — left behind: ____________

### B9 — [ ] Launched from the desktop icon, the app still finds its tools

A GUI started from a desktop icon does not inherit a login shell's `PATH`, and
`~/.local/bin` — where the container's tools are exported — is exactly what goes missing.

1. Launch from the **application menu / desktop icon**, not a terminal.
2. *Tools → Check dependencies*. Expected: cyanrip, metaflac, flac, ffmpeg and cd-paranoia
   all **found**.
3. Rip a disc and confirm CTDB verification runs (it decodes with the host `flac`).

**Result:** ☐ PASS ☐ FAIL — any reported missing: ____________

---

## C — Carried over (still never exercised on hardware)

### C2 — [ ] Offset-variant re-read, across two rips

Rip the same disc twice (A then B), then:

```sh
./platterpus-x86_64.AppImage --compare "<A>.platterpus.json" "<B>.platterpus.json"
```

- Expected: **track 5 byte-identical** between A and B — the point of the offset-variant
  re-read setting.
- Expected: **track 3 may still differ.** If it *is* identical, say so — genuine win.

**Result:** ☐ PASS ☐ FAIL — identical: ____ / 14 · track 5: ☐ y ☐ n · track 3: ☐ y ☐ n

### C4 — [ ] Per-track "Rip?" selection

1. Insert a CD, let it identify. The grid has a leading **Rip?** column, all ticked.
2. Untick two tracks → **Start rip**. Expected: only ticked tracks ripped, filenames keep
   their **original** numbers (`03 - …`, not renumbered 1..N).
3. Untick **everything** → **Start rip**. Expected: a clear message blocks it — no rip, no
   crash.
4. Highlight 2–3 rows → **right-click**. Expected: *Rip only these* / include / exclude /
   select all / none, each working.

> Do **A10** as well if you have an unknown disc — same selection feature, but A10 is where
> the silent tag bug lived.

**Result:** ☐ PASS ☐ FAIL — notes: ____________

### C5 — [ ] Whole-disc Test & Copy

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

### C8 — [ ] The app is fine without cd-paranoia

```sh
mv ~/.local/bin/cd-paranoia ~/.local/bin/cd-paranoia.bak
```

1. Relaunch. *Set up drive* → **Analyse cache**. Expected: it says **cd-paranoia isn't
   installed** and points at *Tools → Set up Platterpus…* — not a vague "could not be
   determined".
2. Rip a CD → works. **Cache defeat** keeps saying **Yes** because your drive's verdict is
   saved *per drive* and isn't re-probed — correct, it really was measured. What must never
   happen is a `Yes` on a drive that was never probed.
3. `./platterpus-x86_64.AppImage --doctor` → **WARN**, not FAIL.
4. Restore: `mv ~/.local/bin/cd-paranoia.bak ~/.local/bin/cd-paranoia`

**Result:** ☐ PASS ☐ FAIL — message said: ____________

### C9 — [ ] Cache probe: no disc, and cancel mid-probe

1. **Empty drive** → **Analyse cache** → expected: a clear message, no hang, no crash.
2. Disc in, start **Analyse cache**, then **close the dialog while it runs** — see A14,
   which is the same action with the fix now in place.

**Result:** ☐ PASS ☐ FAIL — notes: ____________

### C10 — [ ] Settings persist across a restart

Turn **both** toggles on → OK → fully quit → relaunch → reopen Settings.

```sh
grep -E "secure_rerip_dynamic|rerip_offset_variant" ~/.config/platterpus/config.toml
```

- Expected: `secure_rerip_dynamic = false` (verify-every-track **ON** — stored inverted)
  and `rerip_offset_variant = true`

**Result:** ☐ PASS ☐ FAIL — values: ____________

### C11 — [ ] Contradictory settings degrade sensibly

**"Verify every track"** ON *and* **"Max reads"** = **Off (0)** → rip a CD.

- Expected: completes normally; one Copy CRC per track, **no fabricated Test CRC**, no
  crash. (No second read exists to compare, so there must be no Test CRC.)

Put **Max reads** back to 2 afterwards.

**Result:** ☐ PASS ☐ FAIL — notes: ____________

### C12 — [ ] Log checksum survives the library auto-move

Set **"Move finished rips to"** to a library folder, rip a CD so it auto-moves, then in the
*new* location:

```sh
head -n -1 *"(EAC-compatible).log" | sha256sum   # must match the last line
```

**Result:** ☐ PASS ☐ FAIL — matched: ☐ yes ☐ no

### C13 — [ ] Nothing was lost in the update

```sh
grep -E "output_dir|read_offset|library_dir" ~/.config/platterpus/config.toml
```

Expected, unchanged across v0.5.12 → v0.5.18: `output_dir = "/home/rmccann/Music/rips"`,
working dir `~/.cache/platterpus`, `read_offset = 667` with "Apply this read offset to
rips" ticked, the drive's *"confirmed — two independent sources agree"* trust line, and the
cache-defeat **Yes** measurement.

> One deliberate change to watch for: an output or library folder that is **not mounted**
> at launch is a *warning*, not an error. It used to be an error, and an error-level field
> gets reset to its default on load — so a rip library on a NAS or removable disk that
> happened to be unmounted was silently retargeted to `~/Music/rips`. If you use a
> removable library folder, unmount it, relaunch, and confirm your path is **still in the
> config**.

**Result:** ☐ PASS ☐ FAIL — anything reset? ____________

### C16 — [ ] UI spot-check

- [ ] *Help → User Guide* mentions **Analyse cache** and **Verify every track**, and says
      CTDB verification is **on by default**
- [ ] Every Settings control shows a tooltip on hover; the CTDB tooltip also says "on by
      default"
- [ ] *Help → About* shows **0.5.18** and correct Qt/Python info
- [ ] Disc-panel values can be selected and copied with the mouse. Selecting a MusicBrainz
      ID and pasting must still give the whole ID.
- [ ] Force-stop a disc scan: the message says *"click Rescan disc to try again"* and does
      not offer to "switch to the cyanrip backend in Settings" (there is no such setting)

**Result:** ☐ PASS ☐ FAIL — notes: ____________

---

## D — ⭐ One question that unblocks the worst bug still open

**Not a pass/fail test — a fact I need.** This is the highest-value thing in the whole
sheet.

### D1b — [ ] ⭐ The small follow-up: a subset rip of a disc that IS in AccurateRip

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

### D3 — [ ] ⭐ Nothing to run — but the most interesting thing your run surfaced

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

This is the same gap as **part E** (build cyanrip `master` for `INDEX 00`), which is now
much better motivated: it isn't a cosmetic cue-sheet nicety, it is the one measurable
place our archival record is thinner than EAC's. I've pinned the disagreement with a test
so nobody later "fixes" it by making our log print EAC's string regardless.

Nothing for you to do here — just don't read the differing row as a bug when you compare.

**Result:** noted ☐

### D4 — [ ] Your call, not a bug: should typed titles rename the files?

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

## E — [ ] Required, and do it LAST: build cyanrip `master` for INDEX 00

Unchanged from the previous sheet. Do this after everything above, because it changes the
binary everything else was tested against.

**Result:** ☐ PASS ☐ FAIL — notes: ____________

---

## Priority, if you only have an hour

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

*If the hour runs out: A24 + A26 cost about five minutes together and answer the two things
this release is actually about.*

---

## Send back

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

**Never send audio** — no `.flac`, no `.wav`, not even briefly. The JSON, the logs and the
CRCs prove bit-perfection without it.

Plus anything surprising, even on a test that passed. And specifically: **any rip that dies
with `rip stream error:`** — that is the v0.5.20 fix's signature and I want the log at once.

---

*Last updated for Platterpus v0.6.3.*
