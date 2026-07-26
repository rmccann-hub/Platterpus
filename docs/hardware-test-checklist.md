# Hardware test checklist — v0.5.9

> **What's left to do**, in the order that takes the fewest rips. Test numbers are
> the stable IDs from the original sheet, so gaps just mean "already passed on the
> 2026-07-26 run" (0.3, 1, 3, 15). Copy-paste the commands, tick the box, jot what
> you saw.
>
> **One thing to send back:** ⭐ **17** — what your `.cue` contains. It's the last
> input to the cyanrip fork decision, and it falls out of any rip that finishes.
>
> **Never send audio** — logs, `.cue`, `.platterpus.json` and CRCs only.

**Date:** ____________  **App version:** ____________

---

## 0 — Setup (2 minutes)

### 0.1 — [ ] Update to v0.5.9

*Help → Check for updates…* → download → verify → accept the restart.

Confirm: *Help → About* says **0.5.9**.

### 0.2 — [ ] ⛔ Untick Overread

*Settings* → untick **Overread** → OK.

This is what hung your drive at 99.76% of track 14 last time. A force-stopped rip
writes **no `.cue`**, which is exactly what left test 17 unanswered.

> `cd-paranoia` is already installed and the EAC-compatible log is already on, so
> there's nothing else to set up.

---

## 1 — [ ] Test 2: cache verdict (the headline fix — no rip needed)

Any audio CD in the drive. *Tools → Set up drive* → **Analyse cache**.

It now takes a couple of minutes instead of failing at 90 seconds.

- Expected: **"✓ Audio cache: re-reads reach the disc, not a stale cache …(measured
  and saved)"**
- Expected: the status line says **"Done."** — *not* "Finished with issues."
- Expected: the disc panel's **Cache defeat** row reads
  **"Yes — cache defeated on re-read (measured, cd-paranoia)"**
- Expected: the window stays responsive throughout

Your own `cd-paranoia -A` output already proves "Yes" is the correct answer here, so
anything else is a new finding worth reporting.

**Result:** ☐ PASS ☐ FAIL — panel row read: ____________

---

## 2 — [ ] One complete rip (covers tests 14, ⭐17, 4a, 5)

Rip a mainstream CD with defaults. Let it **finish** — no cancelling.

Then check all of these from that one rip:

### 14 — the rip itself
- [ ] Disc identified, MusicBrainz match correct
- [ ] One progress bar (no duplicate in the track grid)
- [ ] Drive row shows make · model · firmware · `/dev/sr0`
- [ ] cyanrip's live output appears while ripping (**View log** during the rip)
- [ ] Green verdict at the end
- [ ] Folder holds: audio, `.log`, `.cue`, `.platterpus.json`, `(EAC-compatible).log`
- [ ] FLACs play, tags correct, cover art embedded

### ⭐ 17 — INDEX 00 (send me this)

```sh
cd "<album folder>"
grep -nE "INDEX|PREGAP" *.cue
```

- Only `INDEX 01` lines → the gap is real on cyanrip 0.9.3
- Any `INDEX 00` or `PREGAP` → **the gap is already closed**

**Send me this output either way.** ☐ only INDEX 01 ☐ INDEX 00 present

### 4a — Test & Copy CRCs (default mode)

```sh
grep -E "Test CRC|Copy CRC" *"(EAC-compatible).log"
```

- Expected on a clean disc: mostly **Copy CRC** only (nothing needed re-reading —
  that's correct, not a bug). Any re-read track shows a matching **Test CRC** too.

### 5 — offset auto-confirmed

Look at the disc panel's **Read offset** line.

- Expected: now reads **"confirmed — two independent sources agree"** (it said
  "entered by hand (medium confidence)" before)
- Expected: still **+667** — only the trust label improved

### Two log lines that were wrong before

```sh
grep -E "offset-variant|not present in AccurateRip|Overread into" *"(EAC-compatible).log"
```

- Expected: any offset-variant track (tracks 3 & 5 on the Police disc) says
  **"Matched an offset-variant pressing — partially accurate (confidence 200)"** —
  it used to falsely claim "not present in AccurateRip database"
- Expected: **`Overread into Lead-In and Lead-Out : No`** (you turned it off) — it
  used to say "(unknown)"

**Result:** 14 ☐ PASS ☐ FAIL · 17 ☐ sent · 4a ☐ PASS ☐ FAIL · 5 ☐ PASS ☐ FAIL

---

## 3 — [ ] Test 18: an interrupted rip must admit it (new)

**Why:** this was the worst of the eight bugs — a force-stopped rip produced a
checksum-signed log that read as a *complete* one.

1. Start a rip, let a couple of tracks finish, then **Cancel**.
2. In that album's folder:

```sh
head -20 *"(EAC-compatible).log"
```

- Expected: a banner near the top —
  **`*** INCOMPLETE RIP (cancelled) — this log covers N of 14 disc tracks. … ***`**
- Expected: near the bottom, **"Conclusive status report : absent"**
- Expected: the checksum still verifies (the banner sits inside it, so it can't be
  quietly deleted):

```sh
head -n -1 *"(EAC-compatible).log" | sha256sum   # must match the last line
```

**Result:** ☐ PASS ☐ FAIL — banner said: ____________

---

## 4 — [ ] Test 6: per-track "Rip?" selection

1. Insert a CD, let it identify. The grid has a leading **Rip?** column, all ticked.
2. Untick two tracks → **Start rip**.
   - Expected: only ticked tracks ripped; filenames keep their original track
     numbers (not renumbered 1..N).
3. Untick **everything** → **Start rip**.
   - Expected: a clear message blocks it — no rip, no crash.
4. Highlight 2–3 rows → **right-click**.
   - Expected: *Rip only these* / include / exclude / select all / none, each working.

**Result:** ☐ PASS ☐ FAIL — notes: ____________

---

## 5 — [ ] Test 7: offset-variant re-read (the tracks 3 & 5 fix)

1. *Settings* → tick **"Also re-read offset-variant (partially accurate) tracks"**.
2. Rip the Police disc **twice** (tracks 3 & 5 are the unstable ones).
3. Compare:

```sh
./platterpus-x86_64.AppImage --compare "<first>.platterpus.json" "<second>.platterpus.json"
```

- Expected: tracks 3 & 5 now **byte-identical** between the two rips (13/13 rather
  than 11/13) — that's the whole point of the setting
- Expected: those tracks took longer

**Result:** ☐ PASS ☐ FAIL — identical tracks: ____ / ____

---

## 6 — [ ] Test 4b: whole-disc Test & Copy

*Settings* → tick **"Verify every track with a second read (EAC-style Test & Copy)"**,
check **"Max reads"** is 2 or more → OK. Re-rip a disc.

```sh
grep -c "Test CRC" *"(EAC-compatible).log"
```

- Expected: a **Test CRC for every track**, each equal to its Copy CRC
- Expected: noticeably slower (everything is read twice)

Untick it again afterwards.

**Result:** ☐ PASS ☐ FAIL — Test CRC count: ____ / ____ tracks

---

## 7 — Risk areas (no full rips except 12)

### 8 — [ ] The app is fine without cd-paranoia

```sh
mv ~/.local/bin/cd-paranoia ~/.local/bin/cd-paranoia.bak
```

1. Relaunch. *Set up drive* → **Analyse cache**.
   - Expected: it now says **cd-paranoia isn't installed** and points you at
     *Tools → Set up Platterpus…* — not a vague "could not be determined".
2. Rip a CD → works exactly as before; **Cache defeat** says *not measured yet*; the
   EAC log says `(unknown)` — never a made-up "Yes".
3. `./platterpus-x86_64.AppImage --doctor` → WARN (optional missing), not FAIL.
4. Restore: `mv ~/.local/bin/cd-paranoia.bak ~/.local/bin/cd-paranoia`

**Result:** ☐ PASS ☐ FAIL — message said: ____________

### 9 — [ ] Cache probe: no disc, and cancel mid-probe

1. **Empty drive** → **Analyse cache** → expected: a clear message, no hang, no crash.
2. Disc in, start **Analyse cache**, then **close the dialog while it runs**.
   - Expected: closes cleanly, app stays responsive, drive spins down within a few
     seconds, no crash.

**Result:** ☐ PASS ☐ FAIL — notes: ____________

### 10 — [ ] Settings persist across a restart

Turn both new toggles on → OK → fully quit → relaunch → reopen Settings.

```sh
grep -E "secure_rerip_dynamic|rerip_offset_variant" ~/.config/platterpus/config.toml
```

- Expected: `secure_rerip_dynamic = false` (that's verify-every-track ON) and
  `rerip_offset_variant = true`

**Result:** ☐ PASS ☐ FAIL — values: ____________

### 11 — [ ] Contradictory settings degrade sensibly

**"Verify every track"** ON *and* **"Max reads"** = **Off (0)** → rip a CD.

- Expected: completes normally; the log is coherent (a single Copy CRC per track —
  no fake Test CRC, no crash).

**Result:** ☐ PASS ☐ FAIL — notes: ____________

### 12 — [ ] Log checksum survives the library auto-move

With a **library folder** set, rip a CD so it auto-moves. In the *new* location:

```sh
head -n -1 *"(EAC-compatible).log" | sha256sum   # must match the last line
```

**Result:** ☐ PASS ☐ FAIL — matched: ☐ yes ☐ no

### 13 — [ ] Nothing was lost in the update

```sh
grep -E "output_dir|read_offset|library_dir" ~/.config/platterpus/config.toml
```

- Expected: your folders, templates and offset all intact after the v0.5.8 → v0.5.9
  update; the drive's offset **and** its trust line survived; the two new toggles are
  at their defaults (both **off**) rather than switched on for you.

**Result:** ☐ PASS ☐ FAIL — anything reset? ____________

---

## 8 — [ ] Test 16: UI spot-check

- [ ] *Help → User Guide* mentions **Analyse cache** and **Verify every track**
- [ ] Every Settings control shows a tooltip on hover
- [ ] *Help → About* shows **0.5.9** and correct Qt/Python info
- [ ] Disc-panel values can be selected and copied with the mouse

**Result:** ☐ PASS ☐ FAIL — notes: ____________

---

## 9 — Only if test 17 showed **no** `INDEX 00`

Upstream cyanrip `master` already writes pre-gap markers; your installed copy is the
2-year-old release. **Do this last — it replaces the cyanrip binary.**

```sh
distrobox enter ripping
git clone https://github.com/cyanreg/cyanrip ~/cyanrip-master
cd ~/cyanrip-master
meson setup build && ninja -C build
build/src/cyanrip -V
exit
```

Rip a disc **with a pre-gap** using that build, then:

```sh
grep -nE "INDEX|PREGAP" "<new album folder>"/*.cue
```

- If `INDEX 00` appears, keep it:
  `distrobox enter ripping -- distrobox-export --bin ~/cyanrip-master/build/src/cyanrip`
- Then do one more normal rip to confirm AccurateRip still verifies (we changed
  rippers, so this is the safety check)

Commit built: `git -C ~/cyanrip-master rev-parse --short HEAD` → ____________

**Result:** ☐ PASS ☐ FAIL ☐ not needed — INDEX 00 appeared: ☐ yes ☐ no

---

## Send back

1. ⭐ The `grep INDEX` output (test 17)
2. `~/.local/share/platterpus/log.txt`
3. One album's `.log`, `(EAC-compatible).log`, `.cue`, `.platterpus.json`
4. This sheet, filled in

Plus anything surprising, even on a test that passed.

---

*Last updated for Platterpus v0.5.9.*
