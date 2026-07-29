# Hardware test checklist — v0.5.16

> **Only what still needs testing.** Anything that has passed is gone from this sheet —
> the record of what passed and when lives in `docs/session-log.md`. Test numbers are
> the stable IDs from the original sheet, so the gaps are deliberate.
>
> Rig details, tool versions and expected values are pre-filled from your last five
> runs. You tick boxes and note anything that **differs** from what's printed.
>
> **Run 5 (v0.5.12) hit full EAC parity: 14/14 tracks byte-identical to the genuine EAC
> rip, and CTDB matched for the first time** — still the high-water mark, and the CRC
> table below is that run. **Run 6 (v0.5.14) came in at 13/14**, the one difference being
> track 3, which had also differed on runs 1–4; see the note below the table. Run 6 also
> *proved* the headline read-stability fix (retired test A1) and left the notification
> test inconclusive, which is why A5 now reads the log instead of your memory.
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

**Track 3 is a problem child again — and that is the disc, not the app.** Run 5 was the
one run where it read cleanly (`59D352DD`, matching EAC). On run 6 it went back to
disagreeing with itself: `1AC787A1`, AccurateRip v1/v2 both "not found", `Accurip 450`
matching at confidence 200, and the re-reads did not agree. Its history is now
`52DFDF7D` / `3D8FCF0C` / `59D352DD` / `1AC787A1` — four values across six runs, which is
the signature of a marginal disc surface. **Expect this track to vary.** What matters is
that the app *says so* (run 6 proved it does — see retired test A1), not that the value
is stable.

**Track 5 is a genuine offset-variant pressing.** Its AccurateRip v1 and v2 both say
"not found", while `Accurip 450` matches at confidence 200 — i.e. the audio is right,
the pressing is shifted. Its shipped CRC has been `E0036697` on all five runs, and it
matches EAC. It gets re-read automatically (3 passes on run 5) and converges.

Expected verdict: **amber**. Best case is 13/14 exact + 1 offset-variant (run 5); when
track 3 misbehaves it is 12/14 exact + 2 offset-variant (run 6). Both are the correct
reading of what the drive returned — neither is a failure of the app.

Expected CTDB: **it depends on track 3, and that is consistent, not flaky.** CTDB checks
one CRC over the *whole disc*, so a single differing track changes it. Run 5 (track 3
clean) matched at confidence 1 (`our_crc` = `matched_crc` = `5DA89FCD`); run 6 (track 3
divergent) returned no match at the standard alignment, and the app explained the two
findings are the same one rather than a contradiction. Either outcome is expected.

**EAC parity: 13/14 on run 6**, verified with the project's own `parity.compare_logs`
against the committed baseline — the single mismatch is track 3. Run 5's 14/14 remains the
high-water mark.

**Two expected changes in wording since your last run (v0.5.12), so they don't read as
regressions:**

* CTDB's no-match line now says *"no match at the standard alignment"* and explains
  that CTDB also holds offset-shifted pressings. It no longer says your rip differs
  from the database — we only ever tested one of ~11,759 valid alignments, so that
  claim was more than the check could support.
* Settings and the User Guide now say CTDB verification is **on by default**. It
  always was; both places said it was off.

---

## 0 — [ ] Update to v0.5.16

*Help → Check for updates…* → download → verify → restart. *Help → About* says
**0.5.16**. Nothing else to set up — your settings are already right (see above).

---

## A — Still-unproven fixes

*Eight reviewers went over the whole app. These are the fixes that can only be proven
on your rig. Test A1 is the important one.*

### A1 — [x] ✅ RETIRED — proven on run 6 (v0.5.14)

**The headline fix is confirmed on your hardware.** Track 3 finally failed to converge
again on run 6, which is exactly the negative case that had never come up before, and the
log did the right thing:

```
Copy CRC 1AC787A1  (re-reads did NOT agree — this read is not confirmed reproducible)
Read stability      : track(s) 3 did not read identically across re-reads — not confirmed reproducible
```

**No `Test CRC` line for track 3** — so the log no longer forges the EAC "two reads
agreed" symbol for a read that didn't. Track 5, which *did* converge, correctly kept its
pair (`Test CRC E0036697` / `Copy CRC E0036697`, "confirmed across 3 secure re-reads"), so
the fix distinguishes the two cases rather than just suppressing the line. Nothing to
re-test.

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

### A5 — [ ] The desktop notification — and now the log can answer for it

Run 6 left this **inconclusive**, and that was a gap in the app, not in your testing: you
were gaming and then at dinner, the toast lives for eight seconds, and `log.txt` recorded
nothing either way — so a shipped fix had no way to be confirmed. v0.5.15 fixes the
diagnosability: every outcome is now written to the log.

Start a rip, go do something else, and afterwards:

```sh
grep -n "completion notification" ~/.local/share/platterpus/log.txt
```

- Expected: exactly one line per rip. Either `completion notification posted: <title> —
  <body>`, or a skip that says why (`turned off in Settings`, `the rip was cancelled`,
  `no usable system tray`).
- If it says **posted** and you *did* see a toast: PASS, and the text should match the
  final status line in the window.
- If it says **posted** and you saw nothing, that is a KDE/notification-daemon issue
  rather than ours — still worth telling me, since we could fall back to another method.
- If it says **no usable system tray**, that is the interesting one: your desktop is
  refusing us a tray icon, and the notification needs a different mechanism.

**Result:** ☐ PASS ☐ FAIL — log line said: ____________ · toast seen: ☐ y ☐ n

### A5b — [x] ✅ RETIRED — the overlap is fixed, you confirmed it on v0.5.15

*"All works"* — the text no longer paints over itself. Nothing to re-test.

### A5c — [ ] ⭐ One scrollbar, and the mouse wheel does the obvious thing

**Your v0.5.15 report:** *"the 2 scroll bars in the lower right are difficult to use
together."* Fair — and the fix caused it. Putting the whole pane in a scroll area made the
table and the console *nested* scroll surfaces: two scrollbars 15 px apart, with the wheel
acting on whichever one the pointer happened to be over.

The tidy-looking repair turned out to be a trap. Turning the table's own scrollbar off does
give one bar — but a nested scroll area that has nothing left to scroll **doesn't pass the
wheel on to its parent** (measured), so the wheel over the table would have done *nothing
at all*. That's worse than two bars, so it was thrown out.

**What v0.5.16 does instead.** The results block is now three parts: a fixed strip at the
top (progress bars, status line, and the trust verdict) that never scrolls and never
hides, then three tabs — **Tracks**, **Details**, **Live log** — and the buttons pinned at
the bottom. Only one tab shows at a time, so there is at most one scrollbar and it is
never nested inside another.

You don't need a full rip for this — tick two tracks in the **Rip?** column and rip those.

1. While it rips: the **Live log** tab should be showing, on its own, without you clicking.
2. When it finishes: it should switch itself to **Tracks**.
3. Resize the window small and large. On each tab, spin the mouse wheel over the middle of
   the content.

- Expected: **never two scrollbars at once.** At most one, on the right of whichever tab
  you're looking at.
- Expected: the wheel scrolls **that tab's content**, every time, with no dead spots — this
  is the bit I could not fully prove off-hardware, so it is the single most useful thing
  you can tell me.
- Expected: the verdict line and status stay visible whichever tab you're on.
- Expected: `Alt+T` / `Alt+D` / `Alt+L` jump to Tracks / Details / Live log.
- Expected: when there's a CTDB caveat, the **Details** tab label shows a **⚠** — so you
  can see there's something in there without opening it. (Your disc produces one: CTDB
  won't match while track 3 is misbehaving.)

**Result:** ☐ PASS ☐ FAIL — two bars at once anywhere: ☐ y ☐ n · a dead wheel spot:
☐ y ☐ n · tabs switched themselves: ☐ y ☐ n · ⚠ on Details: ☐ y ☐ n

> **Say so if you don't like it.** Tabs are a bigger change to how the app looks than a
> layout fix, and it is a judgement call: it buys one predictable scrollbar and costs you
> seeing the table and the CTDB note at the same time. If you'd rather have everything on
> one page and put up with a scrollbar, that's a legitimate preference and I'll do it
> differently — the measurements just rule out doing it the way it was.

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

Expected, unchanged across v0.5.12 → v0.5.16: `output_dir =
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
- [ ] *Help → About* shows **0.5.16** and correct Qt/Python info (Qt 6.11.1, Python
      3.12.13)
- [ ] Disc-panel values can be selected and copied with the mouse — worth a second
      look this release, since those are the labels A5b changed. Selecting a
      MusicBrainz ID and pasting it must still give you the whole ID.
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

*Last updated for Platterpus v0.5.16.*
