# Hardware test checklist — v0.5.18

> **Everything that still needs testing, in one place.** Anything that has already passed
> is gone from this sheet — the record of what passed and when lives in
> `docs/session-log.md`. Test IDs are stable across releases, so the gaps are deliberate.
>
> Rig details, tool versions and expected values are pre-filled from your last six runs.
> You tick boxes and note anything that **differs** from what's printed.
>
> **Three releases have landed since your last run (v0.5.14):** v0.5.16 (results-pane
> tabs), v0.5.17 (the QThread crash + four cancels that didn't work), and v0.5.18
> (silent failures, and tags being written to the wrong files). **Sections A and D are
> new and are where the value is** — they cover fixes that *cannot* be proven off
> hardware, plus one question whose answer unblocks the worst bug still open.
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
* The EAC-compatible log's gap row now reads **`Gap handling : Appended to previous
  track`** instead of echoing cyanrip's own phrasing. The *behaviour* never changed — the
  log just now says it in EAC's vocabulary. See A19.
* A disc that can't be read now reports **the actual error**, not "not in MusicBrainz". See
  A17 — this one is worth reading before you start.

---

## 0 — [ ] Update to v0.5.18

*Help → Check for updates…* → download → verify → restart. *Help → About* says **0.5.18**.
Nothing else to set up — your settings are already right (see above).

**Result:** ☐ PASS ☐ FAIL — version shown: ____________

---

## A — ⭐ New in v0.5.17 / v0.5.18 — only your rig can prove these

*Twelve findings were fixed across these two releases, most of them found by audits rather
than by anything going visibly wrong. The suite proves the mechanisms fire; it cannot prove
the drive stops or that the right bytes got the right tags. **A10 and A11 are the two that
matter most.***

### A10 — [x] ⭐⭐ Tags must land on the right files when you deselect tracks — **PASSED 2026-07-30**

> **Answered from your run.** 16-track CD-R, tracks 1–2 unticked, 3–16 ripped. The `.cue`
> pairs every typed title with its own track number — `TRACK 03` → `"three3"`, `TRACK 04`
> → `"four4"`, `TRACK 05` → `"five5"` / `PERFORMER "if madrid - ft. nelly"` — and Picard
> reads the same titles back out of the FLAC tags themselves. Under the old bug `TRACK 03`
> would have carried track 1's row ("Track 01"), and it doesn't. **The off-by-one is gone.**
>
> Your `metaflac` loop printed an error rather than tags because the `cd` failed first:
> the path has a space in it, so it needs quoting. **One self-contained command, no `cd`:**
>
> ```sh
> find ~/Music/rips -name '*.flac' -newermt '-1 day' -print0 | sort -z | while IFS= read -r -d '' f; do
>   printf '%s -> ' "$(basename "$f")"
>   metaflac --show-tag=TRACKNUMBER --show-tag=TITLE "$f" | tr '\n' ' '
>   echo
> done
> ```
>
> Worth running once to confirm `TRACKNUMBER` too — the `.cue` proves the *title* pairing
> and Picard proves the tags exist, but only `metaflac` shows the number stored in the
> file. Not urgent; the failure mode is already ruled out by the cue.

**Original test, kept for the record:**

**This is the most serious bug fixed in v0.5.18, and it was silent.** For unknown discs
(no MusicBrainz match) the tagger keyed each track on the file's *position in the folder*
rather than on its track number. Those are the same thing only when every track is ripped
— and the **Rip?** column exists so they aren't. Untick track 1 and the file `02 - …` was
written track 1's title and `TRACKNUMBER=01`, `03 - …` got track 2's, and so on down the
disc. **Every tag on the archival master off by one**, with the window reporting success
and nothing in the log.

You need a disc MusicBrainz does *not* know for this — a CD-R, a promo, an obscure
pressing. If you don't have one, say so and I'll suggest another way to force unknown mode.

1. Insert the unknown disc. When it offers **Rip as unknown album**, accept.
2. In the track table, **untick tracks 1 and 2**. Type distinctive titles into the rows
   you *are* ripping — e.g. track 3 → `THREE`, track 4 → `FOUR`.
3. Rip. Then in the album folder:

```sh
for f in *.flac; do
  printf '%s -> ' "$f"
  metaflac --show-tag=TRACKNUMBER --show-tag=TITLE "$f" | tr '\n' ' '
  echo
done
```

- Expected: `03 - ….flac` has **`TRACKNUMBER=03`** and **`TITLE=THREE`**. `04 - ….flac`
  has `TRACKNUMBER=04` / `TITLE=FOUR`.
- **The bug looked like:** `03 - ….flac` carrying `TRACKNUMBER=01` and the title you typed
  for track 1's row.
- Also expected: no file is left untagged, and `log.txt` has no "does not start with a
  track number" warnings.

**Result:** ☐ PASS ☐ FAIL — first file's number/title: ____________ · any off-by-one:
☐ y ☐ n

### A11 — [~] ⭐⭐ Cancel, then quit within five seconds — **PARTIAL PASS 2026-07-30**

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

### A19 — [x] The EAC log's gap row — **your run FAILED it, and you were right to send it**

**Both expectations I wrote here were wrong.** Your log settled both, and one of them was
a real bug.

**The gap row.** I told you to expect `Appended to previous track`. Your log said
`Gap handling : None signalled` — cyanrip's own phrasing, not EAC's. The v0.5.18 change
only took effect when cyanrip printed *nothing*, and cyanrip always prints the block, so
the fix was unreachable on real output. Its test couldn't see that because the fixture
handed the renderer EAC's phrase as *input* — a string cyanrip never emits. Fixed
properly on the branch; the row now reads EAC's own wording for the not-detected case:

```
Gap handling                                : Not detected, thus appended to previous track
```

That is EAC's verbatim string (confirmed against a real EAC 1.1 log), and it will
**deliberately differ** from your EAC baseline for the Police disc, which says
`Appended to previous track`. That difference is true and worth seeing — see D3 below.

**The C2 row.** I told you it would stay `(not reported by the ripper)`. It doesn't — your
log says **`Make use of C2 pointers : No`**, because cyanrip's header prints `C2 errors:
unsupported by drive` and we parse it. So the row I described as an open unknown is
already filled, on first-party evidence from the tool doing the read. That is exactly the
standard the test was defending, and the drive supplied it. Nothing to do.

**Nothing to re-run** — this section is answered. When you next generate an EAC log on
v0.5.19, a one-line confirmation is enough:

```sh
grep -n "Gap handling" *"(EAC-compatible).log"
```

**Result:** x FAIL as shipped (gap row) — fixed on branch · C2 row already correct

---

## B — Still unproven from earlier releases

### B2 — [x] ⭐ An interrupted rip must admit it — **PASSED 2026-07-30**

> **Broken for four releases, working now.** Your cancelled Police rip's EAC log carries it,
> at the top, inside the checksum:
>
> ```
> *** INCOMPLETE RIP (cancelled) — this log covers 2 of 14 disc tracks. The remaining
> 12 track(s) were never extracted and are absent below. ***
> ```
>
> Correct count, correct reason, correct wording. The `.platterpus.json` agrees —
> `outcome.status: "cancelled"`. Nothing to re-run.
>
> One thing still worth a single command next time you have a cancelled rip, because it's the
> half your run didn't cover — that the banner is *inside* the signed region and so can't be
> quietly deleted:
>
> ```sh
> head -n -1 *"(EAC-compatible).log" | sha256sum   # must match the log's last line
> ```

**Original test, kept for the record:**

On this sheet since v0.5.9 and it has **never worked**: the banner's renderer was correct,
but the code handing it the rip's outcome read a dictionary the wrong way and always passed
an empty status. Four releases shipped it broken.

1. Start a rip, let two or three tracks finish, then **Cancel**.
2. In that album's folder:

```sh
head -20 *"(EAC-compatible).log"
head -n -1 *"(EAC-compatible).log" | sha256sum   # must match the last line
```

- Expected near the top: `*** INCOMPLETE RIP (cancelled) — this log covers N of 14 disc
  tracks. The remaining M track(s) were never extracted and are absent below. ***`
- Expected near the bottom: `Conclusive status report : absent`
- Expected: the checksum still verifies — the banner sits **inside** it, so it can't be
  quietly deleted.

**Result:** ☐ PASS ☐ FAIL — banner said: ____________ · checksum: ☐ y ☐ n

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

### D1 — [x] Does cyanrip print AccurateRip lines when ripping a SUBSET of tracks? — **YES, answered 2026-07-30**

> **You answered this without running the probe.** Your A10 rip *was* a subset rip
> (`Tracks to rip: 3, 4, …, 16`), and its log carries the AccurateRip block for every
> track:
>
> ```
> AccurateRip:    not found          ← disc-level lookup ran
>   Accurip:      not found          ← and per track, under -l
>     Accurip v1:  9321BBF1
>     Accurip v2:  42F2D73C
>     Accurip 450: 69535AA2
> ```
>
> So the machinery is not disabled by `-l`: cyanrip performs the lookup and prints the
> per-track result and all three local CRCs. **Task #55 takes the straightforward path** —
> the re-rip's own AccurateRip lines exist and can replace the first pass's, instead of the
> bigger "drop the verdict and mark the track unverified" UX change. No sign-off needed.
>
> **One narrow thing left, and it's small.** Your disc isn't in AccurateRip, so what we saw
> printed was `not found`. What that can't show is a *positive match with a confidence*
> under `-l`. It's the same code path and I'd be surprised if it differed, but "I'd be
> surprised" is not evidence, so before I ship the #55 fix: **one subset rip of the Police
> disc** (which IS in the database) — see **D1b**.

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

### D1 — original probe (no longer needed, kept for the record)

**Why it matters.** When the auto-fix re-rips a single bad track, it swaps the new read's
CRC into the report — but keeps the **first pass's** AccurateRip result if the re-rip's log
didn't print one. If that happens, a track can be reported **"AccurateRip verified"** while
the bytes actually shipped were never checked against AccurateRip at all. The banner, the
JSON report, the track table and the EAC log would all assert a verification that never
happened.

That is precisely the class of bug the project has a standing rule against, and I will not
guess at the fix: the correct behaviour depends entirely on whether cyanrip emits those
lines under `-l`, and guessing wrong makes a correctness bug worse rather than better.

Run this by hand — **no GUI involved**, one track only, into a scratch folder:

```sh
mkdir -p /tmp/ar-probe && cd /tmp/ar-probe
~/.local/bin/cyanrip -d /dev/sr0 -l 3 -o flac -s 667 2>&1 | tee subset.txt
grep -inE "accurip|accuraterip" subset.txt
```

Then the same for the whole disc, for comparison:

```sh
mkdir -p /tmp/ar-probe-full && cd /tmp/ar-probe-full
~/.local/bin/cyanrip -d /dev/sr0 -o flac -s 667 2>&1 | tee full.txt
grep -inE "accurip|accuraterip" full.txt
```

**What I need back:** the `grep` output from both, or "no matches" if that's the answer.
Just those few lines — **not** the FLACs. Delete both scratch folders afterwards.

- If the subset rip **does** print Accurip lines → the fix is straightforward and I'll
  make the merge use them.
- If it **doesn't** → the fix has to drop the stale verdict and mark the track
  "not verified", which is a bigger UX change and needs your sign-off.

**Result:** subset printed Accurip lines: ☐ y ☐ n — paste the lines: ____________

### D2 — [x] Anything that would settle the C2-pointers row — **settled, nothing to run**

Your rip log's header answers it: `C2 errors: unsupported by drive`. cyanrip states the
drive's C2 capability itself, we parse it, and the EAC log now says `No`. First-party
evidence from the tool doing the read — better than the survey I was refused for. Done.

### D3 — [ ] ⭐ Nothing to run — but the most interesting thing your run surfaced

Fixing the gap row made me diff your two logs of the **same disc in the same drive**, and
they disagree in a way neither log's wording had made visible:

| | EAC 1.8 | cyanrip 0.9.3 |
|---|---|---|
| `Gap handling` | `Appended to previous track` | `None signalled` |
| Per-track `Pre-gap length` | **present, 14 tracks** | **none** |

**EAC finds pregaps that cyanrip does not.** EAC runs its own gap-detection pass; cyanrip
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

**Updated 2026-07-30 after your first batch.** A10, A19, D1 and D2 are answered — A10
passed, A19 found a real bug, D1 and D2 came free with your log.

1. **A11** — cancel-then-quit, drive must stop (no recovery when it fails)
2. **D1b** — one subset rip of the Police disc; the last thing gating the #55 fix
3. **A17** — a failed disc read says why (and the one regression risk this release)
4. **A13** — closing mid-rip doesn't crash
5. **B5c** — the wheel behaviour I couldn't prove off-hardware
6. **B2** — the incomplete-rip banner, broken for four releases

---

## Send back

1. `~/.local/share/platterpus/log.txt`
2. One album's `.log`, `(EAC-compatible).log`, `.cue`, `.platterpus.json`
3. The `--compare` output from C2
4. The `grep` output from **D1** — the single most useful item
5. This sheet, filled in

Plus anything surprising, even on a test that passed.

---

*Last updated for Platterpus v0.5.18.*
