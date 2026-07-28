# Hardware test checklist — v0.5.12

> **Only what still needs testing.** Anything that passed is gone from this sheet —
> the record of what passed and when lives in `docs/session-log.md`. Test numbers are
> the stable IDs from the original sheet, so the gaps are deliberate.
>
> Rig details, tool versions and expected values are pre-filled from your last three
> runs. You tick boxes and note anything that **differs** from what's printed.
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

Expected Copy CRCs — the 12 stable tracks should reproduce exactly:

| 1 | 2 | 4 | 6 | 7 | 8 |
|---|---|---|---|---|---|
| `B0D122E7` | `985AAE32` | `60D796AE` | `B32769D6` | `CCBFF669` | `D723C1B0` |

| 9 | 10 | 11 | 12 | 13 | 14 |
|---|---|---|---|---|---|
| `6F6E4A5F` | `3A33519F` | `56BFC63D` | `D78CEAEF` | `DA6A4DAF` | `787BA2D6` |

**Tracks 3 and 5** are the disc's problem children and get re-read automatically.
Track 5's *shipped* CRC has been `E0036697` on all three runs; track 3's has varied
(`52DFDF7D`, `3D8FCF0C`). Expected verdict: **amber**, 12/14 exact + 2
offset-variant — correct, not a failure. CTDB says **no match** for the same reason.

---

## 0 — [ ] Update to v0.5.11

*Help → Check for updates…* → download → verify → restart. *Help → About* says
**0.5.11**. Nothing else to set up — your settings are already right (see above).

---

## 1 — [ ] The EAC log itself (one rip of the Police disc)

**Your run-4 result (v0.5.11):** the checksum verified (`02a7c5a8…`, I reproduced it),
all 14 tracks present, 12/14 exact + tracks 3 & 5 offset-variant as always, and the
CRCs were the shipped ones. **But the CRC fix was never exercised** — no track was
re-ripped, because you closed the window ~26 minutes into the securing pass. So step 1
is still owed, and v0.5.12 changes what you're checking.

v0.5.12 rebuilds this log to match a real EAC log row for row. Rip the disc, let it
finish (the securing pass on tracks 3 & 5 can take ~25 min — leave it), then:

```sh
cd "<album folder>"
diff <(sed -n '/TOC of the extracted CD/,/^Track  1$/p' *"(EAC-compatible).log") /dev/null | head -25
grep -nE "^Track |Pre-gap|Read mode|C2 pointers|Command line compressor|track\(s\)" *"(EAC-compatible).log"
tail -8 *.log          # cyanrip's swap addendum, if any track was re-read
```

- Expected: a **`TOC of the extracted CD`** table — 14 rows, start/length/sectors.
  This is new, and it is byte-identical to what EAC prints for this disc.
- Expected: `Track  1` … `Track  9`, then **`Track 10`**–`Track 14` (EAC's alignment).
- Expected: `Read mode : Secure`, `Make use of C2 pointers : No`,
  `Command line compressor : (none — cyanrip encodes in-process via libavcodec)`.
- Expected: rows we can't fill say **`(not reported by the ripper)`** — that's the
  honest label, not a bug.
- Expected: if a track *was* re-read and swapped in, its `Test CRC`/`Copy CRC` pair
  **equals the CRC in cyanrip's addendum**. If nothing was re-read, there is no
  Test CRC at all — also correct.

```sh
head -n -1 *"(EAC-compatible).log" | sha256sum   # must match the last line
```

**Result:** ☐ PASS ☐ FAIL — TOC present: ☐ y ☐ n · `Track 10` aligned: ☐ y ☐ n ·
addendum CRCs match: ☐ y ☐ n ☐ n/a · checksum matched: ☐ y ☐ n

---

## 1b — [ ] NEW: quit during the securing pass (what run 4 accidentally found)

Closing the window mid-re-rip reported the rip as a **clean success** with no hint
that the securing pass was cut short. Your audio was fine — the re-rip works in a
temp folder and only swaps on success — but the record didn't say what happened.

1. Start a rip of the Police disc. When the status says it is re-ripping tracks 3 & 5,
   **close the window**.
2. Then:

```sh
grep -nE "INCOMPLETE|securing|interrupted" *"(EAC-compatible).log"
python3 -c "import json;d=json.load(open([f for f in __import__('glob').glob('*.platterpus.json')][0]));print(d['read_speed'])"
```

- Expected: the report does **not** claim a securing pass that didn't finish —
  `secure_rerip.engaged` and `retried_tracks` must agree with each other.
- Expected: all 14 tracks are present and playable regardless.

**Result:** ☐ PASS ☐ FAIL — notes: ____________

---

## 2 — [ ] Test 7: offset-variant re-read, across two rips

Step 1 gave you rip A. Rip the same disc again (rip B), then:

```sh
./platterpus-x86_64.AppImage --compare "<A>.platterpus.json" "<B>.platterpus.json"
```

- Expected: **track 5 byte-identical** between A and B — that's the point of the
  offset-variant re-read setting.
- Expected: **track 3 may still differ.** Three runs have failed to read it the same
  way twice; that's the disc. If it *is* identical, say so — genuine win.
- Expected: tracks 3 and 5 take noticeably longer than the rest.

**Result:** ☐ PASS ☐ FAIL — identical: ____ / 14 · track 5: ☐ y ☐ n · track 3: ☐ y ☐ n

---

## 3 — [ ] Test 18: an interrupted rip must admit it

Shipped in v0.5.9, never exercised. This was run 1's worst bug — a force-stopped rip
produced a checksum-signed log that read as a *complete* rip.

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

---

## 4 — [ ] Test 6: per-track "Rip?" selection

1. Insert a CD, let it identify. The grid has a leading **Rip?** column, all ticked.
2. Untick two tracks → **Start rip**. Expected: only ticked tracks ripped, filenames
   keep their **original** numbers (`03 - …`, not renumbered 1..N).
3. Untick **everything** → **Start rip**. Expected: a clear message blocks it — no
   rip, no crash.
4. Highlight 2–3 rows → **right-click**. Expected: *Rip only these* / include /
   exclude / select all / none, each working.

**Result:** ☐ PASS ☐ FAIL — notes: ____________

---

## 5 — [ ] Test 4b: whole-disc Test & Copy

*Settings* → tick **"Verify every track with a second read (EAC-style Test & Copy)"**
→ OK (max reads is already 2, which is what it needs). Re-rip a disc.

```sh
grep -c "Test CRC" *"(EAC-compatible).log"
```

- Expected: **14** — a Test CRC for every track, each equal to its Copy CRC
- Expected: noticeably slower than step 1 (everything read twice)

Untick it again afterwards.

**Result:** ☐ PASS ☐ FAIL — Test CRC count: ____ / 14

---

## 6 — Risk areas (only test 12 needs a full rip)

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

Turn **both** new toggles on → OK → fully quit → relaunch → reopen Settings.

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

Expected, unchanged across v0.5.11 → v0.5.12: `output_dir =
"/home/rmccann/Music/rips"`, working dir `~/.cache/platterpus`, `read_offset = 667`
with "Apply this read offset to rips" ticked, the drive's *"confirmed — two
independent sources agree"* trust line, and the cache-defeat **Yes** measurement.

**Result:** ☐ PASS ☐ FAIL — anything reset? ____________

---

## 7 — [ ] Test 16: UI spot-check

- [ ] *Help → User Guide* mentions **Analyse cache** and **Verify every track**
- [ ] Every Settings control shows a tooltip on hover
- [ ] *Help → About* shows **0.5.12** and correct Qt/Python info (Qt 6.11.1, Python
      3.12.13)
- [ ] Disc-panel values can be selected and copied with the mouse

**Result:** ☐ PASS ☐ FAIL — notes: ____________

---

## 8 — [ ] Required: build cyanrip `master` for INDEX 00

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
3. The `--compare` output from step 2
4. This sheet, filled in

Plus anything surprising, even on a test that passed.

---

*Last updated for Platterpus v0.5.12.*
