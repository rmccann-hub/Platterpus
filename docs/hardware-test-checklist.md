# Hardware test checklist — v0.5.13

> **Only what still needs testing.** Anything that has passed is gone from this sheet —
> the record of what passed and when lives in `docs/session-log.md`. Test numbers are
> the stable IDs from the original sheet, so the gaps are deliberate.
>
> Rig details, tool versions and expected values are pre-filled from your last five
> runs. You tick boxes and note anything that **differs** from what's printed.
>
> **Run 5 (v0.5.12, 2026-07-28) hit full EAC parity: 14/14 tracks byte-identical to the
> genuine EAC rip of this disc, and CTDB matched for the first time.** The reference
> table below is updated to that run — it is now the best-known-good baseline.
>
> **Never send audio** — logs, `.cue`, `.platterpus.json` and CRCs only.

**Date:** ____________

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

**Track 3 is no longer a problem child.** It had produced a different CRC on every
earlier run (`52DFDF7D`, `3D8FCF0C`); on run 5 it read cleanly on the *first pass* as
`59D352DD` with an exact AccurateRip match at confidence 200 — and that value agrees
with the genuine EAC rip. If it differs again, that is the disc/drive, not the app.

**Track 5 is a genuine offset-variant pressing.** Its AccurateRip v1 and v2 both say
"not found", while `Accurip 450` matches at confidence 200 — i.e. the audio is right,
the pressing is shifted. Its shipped CRC has been `E0036697` on all five runs, and it
matches EAC. It gets re-read automatically (3 passes on run 5) and converges.

Expected verdict: **amber**, 13/14 exact + 1 offset-variant. That is the correct and
best-possible result for this disc — not a failure.

Expected CTDB: **match, confidence 1** (`our_crc` = `matched_crc` = `5DA89FCD`).

**Two expected changes in wording this release, so they don't read as regressions:**

* CTDB's no-match line now says *"no match at the standard alignment"* and explains
  that CTDB also holds offset-shifted pressings. It no longer says your rip differs
  from the database — we only ever tested one of ~11,759 valid alignments, so that
  claim was more than the check could support.
* Settings and the User Guide now say CTDB verification is **on by default**. It
  always was; both places said it was off.

---

## 0 — [ ] Update to v0.5.13

*Help → Check for updates…* → download → verify → restart. *Help → About* says
**0.5.13**. Nothing else to set up — your settings are already right (see above).

---

## A — Still-unproven fixes

*Eight reviewers went over the whole app. These are the fixes that can only be proven
on your rig. Test A1 is the important one.*

### A1 — [ ] ⭐ A track that never reads the same way twice must not show a Test CRC

**This is the headline fix and your disc is the perfect case for it.** Track 3 has
failed to reproduce on three of four runs. Until now, a track whose re-reads
*disagreed* still printed a `Test CRC == Copy CRC` pair — the EAC symbol for
"two independent reads agreed" — because the code counted *how many passes cyanrip
took* rather than *how many agreed*. The same checksum-signed document then said, a
few lines further down, that the reads had not agreed.

Rip the Police disc once, then in the album folder:

```sh
grep -nE "Test CRC|Copy CRC|Read stability|not confirmed reproducible" *"(EAC-compatible).log"
```

- If a track is listed under `Read stability … not confirmed reproducible`, it must
  have **only a Copy CRC**, tagged `(re-reads did NOT agree …)`. **No `Test CRC` line
  for that track** — that is the whole fix.
- Tracks that converged keep their `Test CRC` + `Copy CRC` pair.
- If *no* track appears under `Read stability` this run, the fix wasn't exercised —
  say so and it stays on the sheet.

**Run 5 (v0.5.12): NOT EXERCISED.** Every re-read converged — track 5 was re-read three
times and agreed, so its `Test CRC`/`Copy CRC` pair is legitimately earned, and track 3
read cleanly on the first pass. The fix's *negative* case never came up, so it is still
unproven on hardware and stays here.

Because the disc has stopped misbehaving, the cheapest way to reach the negative case is
to make a read genuinely marginal: try the rip with a **fingerprint or a smudge** on the
disc surface over tracks 3–5 (wipe it afterwards), or with the drive under load. If it
still converges every time, that is a good problem and we can retire this test as
un-provable on this disc.

**Result:** ☐ PASS ☐ FAIL ☐ not exercised — track(s) flagged: ______ · any Test CRC on
a flagged track: ☐ y ☐ n

### A2 — [ ] ⭐ An interrupted rip must admit it — *now actually wired*

Was test 18. It has been on this sheet since v0.5.9 and it has **never worked**: the
banner's renderer was correct, but the code that hands it the rip's outcome read a
dictionary the wrong way and always passed an empty status. Four releases shipped it
broken. It is fixed and pinned by a test that goes through the real write path.

1. Start a rip, let two or three tracks finish, then **Cancel**.
2. In that album's folder:

```sh
head -20 *"(EAC-compatible).log"
head -n -1 *"(EAC-compatible).log" | sha256sum   # must match the last line
```

- Expected near the top: `*** INCOMPLETE RIP (cancelled) — this log covers N of 14
  disc tracks. The remaining M track(s) were never extracted and are absent
  below. ***`
- Expected near the bottom: `Conclusive status report : absent`
- Expected: the checksum still verifies — the banner sits **inside** it, so it can't
  be quietly deleted.

**Result:** ☐ PASS ☐ FAIL — banner said: ____________ · checksum: ☐ y ☐ n

### A3 — [ ] Quitting during the securing pass is now recorded in the log too

Run 4 found this by accident: closing the window mid-re-rip reported a clean success.
The JSON report was fixed to record it; the *durable* log — the artifact a stranger
reads years later — still said nothing, so the archival record was the more
reassuring of the two. Both now carry it.

1. Start a rip of the Police disc. When the status says it is re-ripping tracks 3 & 5,
   **close the window**.
2. Then:

```sh
grep -nE "securing pass was INTERRUPTED" *"(EAC-compatible).log"
python3 -c "import glob,json;print(json.load(open(glob.glob('*.platterpus.json')[0]))['read_speed'])"
```

- Expected in the log: `Secure re-read      : the securing pass was INTERRUPTED
  before it finished — any track it had not yet re-read carries only its first read`
- Expected in the JSON: `secure_rerip.interrupted` is `true` and agrees with it.
- Expected: all 14 tracks present and playable regardless.

**Result:** ☐ PASS ☐ FAIL — notes: ____________

### A5 — [ ] The desktop notification says what the window says

Start a rip of the Police disc, switch to another window, and let it finish.

- Expected: a notification **appears at all**. On v0.5.12 it never did: your run-5 log
  carries `AttributeError: 'MainWindow' object has no attribute '_tray_icon'` at the
  moment the rip finished, swallowed because notifications are best-effort. That was a
  v0.5.12 regression — a type-checker-only declaration that nothing created at runtime
  — and it is fixed in v0.5.13. **This is the main reason to install this release.**
- Expected: the text **matches the final status line** in Platterpus. If the window
  warns that a track didn't read reproducibly, the notification must say so too.

**Result:** ☐ PASS ☐ FAIL — appeared at all: ☐ y ☐ n · notification said: ____________

### A5b — [ ] Do the CTDB and loudness lines overlap the results table?

In the run-5 screenshot the green *"CTDB: Verified (confidence 1)"* line and the album
loudness line appear to be drawn **on top of** the AccurateRip table's first row rather
than above and below it. I could not tell from a static capture whether that is real or
a compositing artifact.

- Resize the window taller after a rip finishes. Does the overlap persist, or was it
  just the pane being squeezed?
- If it persists, a screenshot of the results pane at a larger window size is enough
  for me to fix it.

**Result:** ☐ no overlap ☐ overlaps, fixed by resizing ☐ overlaps at any size

### A6 — [ ] Your own `cover.jpg` survives a re-rip

Cover art is embedded but not saved by default, and the scratch file it wrote for
`metaflac` reused the name `cover.jpg` and then deleted it — so the default setting
destroyed a cover you had put in the folder yourself.

1. Put any JPEG named `cover.jpg` into an already-ripped album folder.
2. Re-rip that disc and choose **Replace** when asked about the existing folder.
3. Expected: your `cover.jpg` is **still there, unchanged**, and no stray
   `.platterpus-cover-tmp*` file is left behind.

**Result:** ☐ PASS ☐ FAIL — cover survived: ☐ y ☐ n · stray temp file: ☐ y ☐ n

### A7 — [ ] A bad read offset is refused, visibly

*Tools → Set up drive…* → type an offset far outside the sane range (the box now
allows ±5000, matching the validator — it used to allow ±2000 while the validator
allowed ±5000). Try to save something absurd if the box lets you, e.g. by
hand-editing `~/.config/platterpus/config.toml` to `read_offset = 999999` and
relaunching.

- Expected: a clear message naming the allowed range; **+667 is still in effect
  afterwards**. It must never silently accept a bad value and reset it to 0 on the
  *next* launch — that would rip the following session at the wrong offset.

**Result:** ☐ PASS ☐ FAIL — offset after the attempt: ____________

### A8 — [ ] Uninstall removes `cd-paranoia` too

*Tools → Uninstall Platterpus…* → **tick the host-exports item, untick everything
else** (you don't want a real uninstall) → run it. Then:

```sh
ls ~/.local/bin/ | grep -E "cyanrip|metaflac|flac|cd-paranoia"
```

- Expected: **all four gone**. `cd-paranoia` was being orphaned — the exact repeat of
  the `flac` bug from earlier.
- Re-run *Tools → Set up Platterpus…* afterwards to put them back.

**Result:** ☐ PASS ☐ FAIL — left behind: ____________

### A9 — [ ] Launched from the desktop icon, the app still finds its tools

A GUI started from a **desktop icon** does not inherit a login shell's `PATH`, and
`~/.local/bin` — where the container's tools are exported — is exactly what goes
missing. The wizard would report a tool installed while the dependency probe reported
it missing.

1. Launch Platterpus from the **application menu / desktop icon**, not a terminal.
2. *Tools → Check dependencies*. Expected: cyanrip, metaflac, flac, ffmpeg and
   cd-paranoia all **found**.
3. Rip a disc and confirm CTDB verification runs (it decodes with the host `flac`).

**Result:** ☐ PASS ☐ FAIL — any reported missing: ____________

---

## B — Carried over (still never exercised on hardware)

### 2 — [ ] Test 7: offset-variant re-read, across two rips

Test A1 gave you rip A. Rip the same disc again (rip B), then:

```sh
./platterpus-x86_64.AppImage --compare "<A>.platterpus.json" "<B>.platterpus.json"
```

- Expected: **track 5 byte-identical** between A and B — that's the point of the
  offset-variant re-read setting.
- Expected: **track 3 may still differ.** Four runs have failed to read it the same
  way twice; that's the disc. If it *is* identical, say so — genuine win.

**Result:** ☐ PASS ☐ FAIL — identical: ____ / 14 · track 5: ☐ y ☐ n · track 3: ☐ y ☐ n

### 4 — [ ] Test 6: per-track "Rip?" selection

1. Insert a CD, let it identify. The grid has a leading **Rip?** column, all ticked.
2. Untick two tracks → **Start rip**. Expected: only ticked tracks ripped, filenames
   keep their **original** numbers (`03 - …`, not renumbered 1..N).
3. Untick **everything** → **Start rip**. Expected: a clear message blocks it — no
   rip, no crash.
4. Highlight 2–3 rows → **right-click**. Expected: *Rip only these* / include /
   exclude / select all / none, each working.

**Result:** ☐ PASS ☐ FAIL — notes: ____________

### 5 — [ ] Test 4b: whole-disc Test & Copy

*Settings* → tick **"Verify every track with a second read (EAC-style Test & Copy)"**
→ OK (max reads is already 2, which is what it needs). Re-rip a disc.

```sh
grep -c "Test CRC" *"(EAC-compatible).log"
```

- Expected: **14** on a disc that reads cleanly — a Test CRC for every track, each
  equal to its Copy CRC.
- On the Police disc, expect **12**: tracks 3 and 5 may legitimately fail to converge,
  and after the A1 fix a non-converging track correctly gets **no** Test CRC. That is
  a pass, not a failure — note which tracks are missing.
- Expected: noticeably slower than A1 (everything read twice).

Untick it again afterwards.

**Result:** ☐ PASS ☐ FAIL — Test CRC count: ____ / 14 · missing: ____________

### 8 — [ ] The app is fine without cd-paranoia

```sh
mv ~/.local/bin/cd-paranoia ~/.local/bin/cd-paranoia.bak
```

1. Relaunch. *Set up drive* → **Analyse cache**. Expected: it says **cd-paranoia
   isn't installed** and points you at *Tools → Set up Platterpus…* — not a vague
   "could not be determined".
2. Rip a CD → works as before. **Cache defeat** keeps saying **Yes** because your
   drive's verdict is saved *per drive* and isn't re-probed — correct, it really was
   measured. What must never happen is a `Yes` on a drive that was never probed.
3. `./platterpus-x86_64.AppImage --doctor` → **WARN** (optional tool missing), not FAIL.
4. Restore: `mv ~/.local/bin/cd-paranoia.bak ~/.local/bin/cd-paranoia`

**Result:** ☐ PASS ☐ FAIL — message said: ____________

### 9 — [ ] Cache probe: no disc, and cancel mid-probe

1. **Empty drive** → **Analyse cache** → expected: a clear message, no hang, no crash.
2. Disc in, start **Analyse cache**, then **close the dialog while it runs**. Expected:
   closes cleanly, app stays responsive, drive spins down within a few seconds, no
   crash. (The probe runs for minutes, so there's a wide window.)

**Result:** ☐ PASS ☐ FAIL — notes: ____________

### 10 — [ ] Settings persist across a restart

Turn **both** toggles on → OK → fully quit → relaunch → reopen Settings.

```sh
grep -E "secure_rerip_dynamic|rerip_offset_variant" ~/.config/platterpus/config.toml
```

- Expected: `secure_rerip_dynamic = false` (verify-every-track **ON** — stored
  inverted) and `rerip_offset_variant = true`

**Result:** ☐ PASS ☐ FAIL — values: ____________

### 11 — [ ] Contradictory settings degrade sensibly

**"Verify every track"** ON *and* **"Max reads"** = **Off (0)** → rip a CD.

- Expected: completes normally; one Copy CRC per track, no fabricated Test CRC, no
  crash. (No second read exists to compare, so there must be no Test CRC.)

Put **Max reads** back to 2 afterwards.

**Result:** ☐ PASS ☐ FAIL — notes: ____________

### 12 — [ ] Log checksum survives the library auto-move

Set **"Move finished rips to"** (currently empty) to a library folder, rip a CD so it
auto-moves, then in the *new* location:

```sh
head -n -1 *"(EAC-compatible).log" | sha256sum   # must match the last line
```

**Result:** ☐ PASS ☐ FAIL — matched: ☐ yes ☐ no

### 13 — [ ] Nothing was lost in the update

```sh
grep -E "output_dir|read_offset|library_dir" ~/.config/platterpus/config.toml
```

Expected, unchanged across v0.5.12 → v0.5.13: `output_dir =
"/home/rmccann/Music/rips"`, working dir `~/.cache/platterpus`, `read_offset = 667`
with "Apply this read offset to rips" ticked, the drive's *"confirmed — two
independent sources agree"* trust line, and the cache-defeat **Yes** measurement.

> One deliberate change to watch for: an output or library folder that is **not
> mounted** at launch is now a *warning*, not an error. It used to be an error, and
> an error-level field gets reset to its default on load — so a rip library on a NAS
> or a removable disk that happened to be unmounted was silently retargeted to
> `~/Music/rips` and the library folder cleared. If you use a removable library
> folder, unmount it, relaunch, and confirm your path is **still in the config**.

**Result:** ☐ PASS ☐ FAIL — anything reset? ____________

### 16 — [ ] UI spot-check

- [ ] *Help → User Guide* mentions **Analyse cache** and **Verify every track**, and
      says CTDB verification is **on by default**
- [ ] Every Settings control shows a tooltip on hover; the CTDB tooltip also says
      "on by default"
- [ ] *Help → About* shows **0.5.13** and correct Qt/Python info (Qt 6.11.1, Python
      3.12.13)
- [ ] Disc-panel values can be selected and copied with the mouse
- [ ] Force-stop a disc scan: the message says *"click Rescan disc to try again"* and
      no longer offers to "switch to the cyanrip backend in Settings" (there is no
      such setting — cyanrip is the only backend)

**Result:** ☐ PASS ☐ FAIL — notes: ____________

---

## C — [ ] Required, and do it LAST: build cyanrip `master` for INDEX 00

Your cyanrip 0.9.3 writes only `INDEX 01` (confirmed run 2). Upstream `master`
already synthesises the track-1 pre-gap and writes `INDEX 00`/`PREGAP`. **Do this
last — it replaces the cyanrip binary**, so every result above would otherwise be on
a different ripper.

```sh
distrobox enter ripping
git clone https://github.com/cyanreg/cyanrip ~/cyanrip-master
cd ~/cyanrip-master
meson setup build          # read this output — see the note below
ninja -C build
build/src/cyanrip -V
exit
```

**Build dependencies:** I haven't verified a Fedora package list, so I'm not giving
you one to paste blindly. `meson setup build` names exactly what's missing, one at a
time — `sudo dnf install -y <name>-devel` and re-run (plus `meson ninja-build gcc
git` if the tools themselves are absent). cyanrip's README lists its dependencies if
a name doesn't map cleanly.

Then rip a disc **with a pre-gap** and check:

```sh
grep -nE "INDEX|PREGAP" "<new album folder>"/*.cue
```

- If `INDEX 00` appears, keep the build:
  `distrobox enter ripping -- distrobox-export --bin ~/cyanrip-master/build/src/cyanrip`
- Then one more normal rip of the Police disc — confirm you still get **12/14 exact
  AccurateRip matches** against the CRC table above. We changed rippers, so this is
  the safety check.
- If the build fails, send the error and stop there. Nothing else depends on it.

Commit built: `git -C ~/cyanrip-master rev-parse --short HEAD` → ____________
cyanrip version reported: ____________

**Result:** ☐ PASS ☐ FAIL — INDEX 00: ☐ yes ☐ no · 12/14 still exact: ☐ y ☐ n

---

## Send back

1. `~/.local/share/platterpus/log.txt`
2. One album's `.log`, `(EAC-compatible).log`, `.cue`, `.platterpus.json`
3. The `--compare` output from test 2
4. This sheet, filled in

Plus anything surprising, even on a test that passed.

---

*Last updated for Platterpus v0.5.13.*
