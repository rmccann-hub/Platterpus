# Hardware test checklist — v0.5.10

> **What's left to do**, in the order that takes the fewest rips. Everything already
> proven is recorded below and removed from the steps. Test numbers are the stable
> IDs from the original sheet, so gaps mean "already passed".
>
> Everything I could fill in from your last two runs **is** filled in — rig, tool
> versions, expected values, expected CRCs. You only need to tick boxes and note
> anything that *differs* from what's printed.
>
> **Never send audio** — logs, `.cue`, `.platterpus.json` and CRCs only.

**Date:** ____________  **App version after update:** 0.5.10

---

## Your rig (pre-filled — confirm, don't re-measure)

| | |
|---|---|
| OS / kernel | Bazzite, `7.1.3-ogc5.1.fc44.x86_64`, KDE Plasma 6 |
| Install channel | AppImage (self-integrated) |
| Python / PySide6 | 3.12.13 / 6.11.1 |
| Drive | `PIONEER  BD-RW   BDR-209D 1.51` on `/dev/sr0` |
| Read offset | **+667** — *confirmed, two independent sources agree* |
| Cache defeat | **Yes** — measured, `cd-paranoia -A`: 140-sector cache, "Backseek flushes the cache as expected", "Drive tests OK with Paranoia." |
| Container | `ripping` (Distrobox) |
| Ripper | cyanrip **0.9.3** → `~/.local/bin/cyanrip` |
| Encoders | flac 1.5.0, metaflac 1.5.0, ffmpeg 8.1.2 |
| Cache tool | cd-paranoia III 10.2 (libcdio 2.1.0) → `~/.local/bin/cd-paranoia` |
| Other | Picard 2.13.3 (Flatpak), musicbrainzngs 0.7.1 |

### Test disc used throughout (pre-filled)

*The Police — Every Breath You Take: The Classics*, 14 tracks, 59:42.354
MusicBrainz release `d14a7546-815b-43c6-8af6-35cff6cee1d0` · DiscID
`pNtImOkdBm9RMBIalzx0w9cfsYY-` · CDDB `E20DFE0E`

**Expected Copy CRCs** — 12 of these should reproduce *exactly* on any new rip.
Tracks 3 and 5 are this disc's known problem children.

| Track | Expected CRC | Notes |
|---|---|---|
| 1 | `B0D122E7` | AR v2, confidence 200 |
| 2 | `985AAE32` | AR v2, confidence 200 |
| **3** | **varies** | run 1 `52DFDF7D`, run 2 `3D8FCF0C` — **never read the same way twice**; offset-variant match only |
| 4 | `60D796AE` | AR v2, confidence 200 |
| **5** | `E0036697` | offset-variant match; converged on re-read in run 2, so it *should* now be stable |
| 6 | `B32769D6` | AR v2, confidence 200 |
| 7 | `CCBFF669` | AR v2, confidence 200 |
| 8 | `D723C1B0` | AR v2, confidence 200 |
| 9 | `6F6E4A5F` | AR v2, confidence 200 |
| 10 | `3A33519F` | AR v2, confidence 200 |
| 11 | `56BFC63D` | AR v2, confidence 200 |
| 12 | `D78CEAEF` | AR v2, confidence 200 |
| 13 | `DA6A4DAF` | AR v2, confidence 200 |
| 14 | `787BA2D6` | AR v2, confidence 200 |

Expected verdict on this disc: **amber** — *"12 of 14 tracks verified exactly against
AccurateRip; the other 2 matched an offset-variant pressing."* That's correct, not a
failure. CTDB will say **no match** for the same reason.

---

## Already passed — nothing to do (recorded for the file)

| Test | Result | Evidence |
|---|---|---|
| 0.3 · wizard installs cd-paranoia | ✅ run 1 | `dnf install -y /usr/bin/cd-paranoia` + `distrobox-export` both succeeded in-container |
| 1 · cd-paranoia present & runnable | ✅ run 1 | `~/.local/bin/cd-paranoia`, v10.2 |
| 2 · cache verdict | ✅ **run 2** | panel: *"Yes — cache defeated on re-read (measured, cd-paranoia)"*; status "Done."; EAC log `Defeat audio cache : Yes` |
| 3 · log checksum + tamper test | ✅ run 1 | recomputed independently; a one-character edit broke it |
| 5 · offset auto-confirmed | ✅ **run 2** | *"+667 — confirmed — two independent sources agree (high confidence)"* |
| 14 · full rip end-to-end | ✅ **run 2** | 14/14 tracks, 0 ripping errors, FLAC verify 14/14, art embedded, all four files written |
| 15 · force-stop + recovery | ✅ run 1 | drive killed and ejected; Open folder / View log worked after |
| ⭐ 17 · INDEX 00 | ✅ **answered run 2** | 14 × `INDEX 01`, no `PREGAP` → the gap is real on 0.9.3, so Part 8 below is required |
| 4a · Test & Copy CRCs | ❌ **failed run 2** → fixed in 0.5.10 | re-tested as step 1 below |

---

## 0 — Setup (1 minute)

### 0.1 — [ ] Update to v0.5.10

*Help → Check for updates…* → download → verify → accept the restart.
Confirm *Help → About* says **0.5.10**. (No reinstall — your config carries over.)

### 0.2 — [ ] Leave your settings exactly as they are

Confirmed from your last screenshot, and all correct for this run:

- **Overread** — unticked ✅ (this is what hung the drive at 99.76% in run 1)
- **"Also re-read offset-variant tracks"** — ticked ✅ (needed for step 2)
- **"Verify every track with a second read"** — unticked ✅ (step 5 turns it on)
- **Max reads** = 2 ✅ · **Max retries** = 5 ✅ · **Read speed** = adaptive ladder ✅
- **EAC-style log** — ticked ✅ · **Debug logging** — ticked ✅

---

## 1 — [ ] The two new fixes (one rip of the Police disc)

Rip it with the settings above; let it finish. Both fixes are about **what the log
admits** — run 2 proved the app *knew* these things and the log didn't say them.

```sh
cd "<album folder>"
grep -nE "Test CRC|not confirmed reproducible|Read stability" *"(EAC-compatible).log"
```

Expected — three new lines that didn't exist in run 2:

- **Track 5:** a `Test CRC E0036697` line matching its Copy CRC, with a
  *"reads converged"* note. It was re-read and the reads agreed, which is exactly
  EAC's Test & Copy proof; run 2 silently dropped it.
- **Track 3:** `(re-reads did NOT agree — this read is not confirmed reproducible)`
  on its Copy CRC line.
- **Near the bottom:** `Read stability      : track(s) 3 did not read identically
  across re-reads — not confirmed reproducible`
- **The other 12 tracks: unchanged** — plain `Copy CRC`, no caveat, no Test CRC. We
  only say what was measured.

Then confirm the checksum still covers the new lines:

```sh
head -n -1 *"(EAC-compatible).log" | sha256sum   # must match the last line
```

**Result:** ☐ PASS ☐ FAIL
Track 5 Test CRC present: ☐ yes ☐ no · Track 3 caveat present: ☐ yes ☐ no
`Read stability` line present: ☐ yes ☐ no · Checksum matched: ☐ yes ☐ no
Track 3's CRC this time: ____________ (expected to differ from both earlier runs)

---

## 2 — [ ] Test 7: offset-variant re-read, across two rips

Step 1 gave you rip A. Rip the **same disc again** (rip B), then:

```sh
./platterpus-x86_64.AppImage --compare "<A>.platterpus.json" "<B>.platterpus.json"
```

- Expected: **track 5 byte-identical** between A and B — it converged in run 2, so
  the setting is doing its job. This is the whole point of the toggle.
- Expected: **track 3 may still differ.** Three attempts have now failed to read it
  the same way twice, so that's the disc, not the app. If it *is* identical this
  time, that's a genuine win — say so.
- Expected: tracks 3 and 5 take noticeably longer than the rest (they get re-read).

**Result:** ☐ PASS ☐ FAIL — identical tracks: ____ / 14 · track 5 identical: ☐ y ☐ n
· track 3 identical: ☐ y ☐ n

---

## 3 — [ ] Test 18: an interrupted rip must admit it

**Why:** the worst bug of run 1 — a force-stopped rip produced a checksum-signed log
that read as a *complete* 13-track rip. The fix shipped in 0.5.9 but has never been
exercised.

1. Start a rip, let two or three tracks finish, then **Cancel**.
2. In that album's folder:

```sh
head -20 *"(EAC-compatible).log"
```

- Expected, near the top:
  `*** INCOMPLETE RIP (cancelled) — this log covers N of 14 disc tracks. The
  remaining M track(s) were never extracted and are absent below. ***`
- Expected, near the bottom: `Conclusive status report : absent`
- Expected: the checksum still verifies — the banner sits **inside** it, so it can't
  be quietly deleted:

```sh
head -n -1 *"(EAC-compatible).log" | sha256sum   # must match the last line
```

**Result:** ☐ PASS ☐ FAIL — banner said: ____________ · checksum matched: ☐ y ☐ n

---

## 4 — [ ] Test 6: per-track "Rip?" selection

1. Insert a CD, let it identify. The grid has a leading **Rip?** column, all ticked.
2. Untick two tracks → **Start rip**.
   - Expected: only the ticked tracks are ripped, and filenames keep their **original
     track numbers** (e.g. `03 - …`, not renumbered 1..N).
3. Untick **everything** → **Start rip**.
   - Expected: a clear message blocks it — no rip, no crash.
4. Highlight 2–3 rows → **right-click**.
   - Expected: *Rip only these* / include / exclude / select all / none, each working.

**Result:** ☐ PASS ☐ FAIL — notes: ____________

---

## 5 — [ ] Test 4b: whole-disc Test & Copy

*Settings* → tick **"Verify every track with a second read (EAC-style Test & Copy)"**
(**Max reads** is already 2, which is what it needs) → OK. Re-rip a disc.

```sh
grep -c "Test CRC" *"(EAC-compatible).log"
```

- Expected: **14** — a Test CRC for every track, each equal to its Copy CRC
- Expected: noticeably slower than step 1, because everything is read twice

Untick it again afterwards.

**Result:** ☐ PASS ☐ FAIL — Test CRC count: ____ / 14

---

## 6 — Risk areas (only test 12 needs a full rip)

### 8 — [ ] The app is fine without cd-paranoia

```sh
mv ~/.local/bin/cd-paranoia ~/.local/bin/cd-paranoia.bak
```

1. Relaunch. *Set up drive* → **Analyse cache**.
   - Expected: it says **cd-paranoia isn't installed** and points you at
     *Tools → Set up Platterpus…* — not a vague "could not be determined".
2. Rip a CD → works as before. **Cache defeat** keeps saying **Yes**, because your
   drive's verdict is *saved per drive* and isn't re-probed. That's correct — it was
   really measured. The thing that must never happen is a `Yes` on a drive that was
   never probed.
3. `./platterpus-x86_64.AppImage --doctor` → **WARN** (optional tool missing), not FAIL.
4. Restore: `mv ~/.local/bin/cd-paranoia.bak ~/.local/bin/cd-paranoia`

**Result:** ☐ PASS ☐ FAIL — message said: ____________

### 9 — [ ] Cache probe: no disc, and cancel mid-probe

1. **Empty drive** → **Analyse cache** → expected: a clear message, no hang, no crash.
2. Disc in, start **Analyse cache**, then **close the dialog while it runs**.
   - Expected: closes cleanly, the app stays responsive, the drive spins down within
     a few seconds, no crash. (The probe now runs for minutes, so there's a wide
     window to catch it mid-flight.)

**Result:** ☐ PASS ☐ FAIL — notes: ____________

### 10 — [ ] Settings persist across a restart

Turn **both** of these on → OK → fully quit → relaunch → reopen Settings.

```sh
grep -E "secure_rerip_dynamic|rerip_offset_variant" ~/.config/platterpus/config.toml
```

- Expected: `secure_rerip_dynamic = false` (that's verify-every-track **ON** — the
  key is stored inverted) and `rerip_offset_variant = true`

**Result:** ☐ PASS ☐ FAIL — values: ____________

### 11 — [ ] Contradictory settings degrade sensibly

**"Verify every track"** ON *and* **"Max reads"** = **Off (0)** → rip a CD.

- Expected: completes normally, and the log is coherent — one Copy CRC per track, no
  fabricated Test CRC, no crash. (There's no second read to compare, so there must be
  no Test CRC.)

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

Expected, unchanged from before the update:

- `output_dir = "/home/rmccann/Music/rips"` · working dir `~/.cache/platterpus`
- `read_offset = 667` and *"Apply this read offset to rips"* still ticked
- the drive's **"confirmed — two independent sources agree"** trust line still there
- the drive's **cache-defeat = Yes** measurement still there

**Result:** ☐ PASS ☐ FAIL — anything reset? ____________

---

## 7 — [ ] Test 16: UI spot-check

- [ ] *Help → User Guide* mentions **Analyse cache** and **Verify every track**
- [ ] Every Settings control shows a tooltip on hover
- [ ] *Help → About* shows **0.5.10** and correct Qt/Python info (Qt 6.11.1, Python
      3.12.13)
- [ ] Disc-panel values can be selected and copied with the mouse

**Result:** ☐ PASS ☐ FAIL — notes: ____________

---

## 8 — [ ] Required: build cyanrip `master` for INDEX 00

Run 2 confirmed your cyanrip 0.9.3 writes only `INDEX 01`. Upstream `master` already
synthesises the track-1 pre-gap and writes `INDEX 00`/`PREGAP`. **Do this last — it
replaces the cyanrip binary**, so every result above would otherwise be on a
different ripper.

```sh
distrobox enter ripping
git clone https://github.com/cyanreg/cyanrip ~/cyanrip-master
cd ~/cyanrip-master
meson setup build          # <- read this output; see the note below
ninja -C build
build/src/cyanrip -V
exit
```

**About the build dependencies:** I haven't verified a package list for your Fedora
container, so I'm not giving you one to paste blindly. `meson setup build` names
exactly what's missing, one dependency at a time — install each with
`sudo dnf install -y <name>-devel` (plus `meson ninja-build gcc git` if the tools
themselves are absent) and re-run it. cyanrip's own README lists its dependencies if
a name doesn't map cleanly. **If it stalls, send me the meson output** — that's more
useful than guessing, and it's a one-time cost we'll write into the setup wizard
afterwards.

Rip a disc **with a pre-gap** using that build, then:

```sh
grep -nE "INDEX|PREGAP" "<new album folder>"/*.cue
```

- If `INDEX 00` appears, keep it:
  `distrobox enter ripping -- distrobox-export --bin ~/cyanrip-master/build/src/cyanrip`
- Then do **one more normal rip** of the Police disc and confirm you still get
  **12/14 exact AccurateRip matches** against the CRC table above — we changed
  rippers, so this is the safety check.
- If the build fails, send me the error and stop there. Nothing else depends on it,
  and the dependency list above is my best guess at what Fedora needs.

Commit built: `git -C ~/cyanrip-master rev-parse --short HEAD` → ____________
cyanrip version reported: ____________

**Result:** ☐ PASS ☐ FAIL — INDEX 00 appeared: ☐ yes ☐ no · 12/14 still exact: ☐ y ☐ n

---

## Send back

1. `~/.local/share/platterpus/log.txt`
2. One album's `.log`, `(EAC-compatible).log`, `.cue`, `.platterpus.json`
3. The `--compare` output from step 2
4. This sheet, filled in

Plus anything surprising, even on a test that passed.

---

*Last updated for Platterpus v0.5.10.*
