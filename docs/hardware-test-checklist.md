# Hardware test checklist — v0.5.10

> **What's left to do**, in the order that takes the fewest rips. Test numbers are
> the stable IDs from the original sheet, so gaps mean "already passed" — 0.3, 1, 3,
> 15 on the 2026-07-26 run 1; **2, 5, 14, ⭐17** on run 2. Copy-paste the commands,
> tick the box, jot what you saw.
>
> **Run 2 answered ⭐17:** your `.cue` had 14 × `INDEX 01` and no `PREGAP`, so the
> pre-gap gap is real on cyanrip 0.9.3 — **Part 9 at the end is now required**, not
> optional. Do it last; it replaces the cyanrip binary.
>
> **Never send audio** — logs, `.cue`, `.platterpus.json` and CRCs only.

**Date:** ____________  **App version:** ____________

---

## 0 — Setup (1 minute)

### 0.1 — [ ] Update to v0.5.10

*Help → Check for updates…* → download → verify → accept the restart.
Confirm *Help → About* says **0.5.10**.

### 0.2 — [ ] Leave these as they are

- **Overread** stays **unticked** (it hung your drive at 99.76% last time).
- **"Also re-read offset-variant tracks"** stays **ticked** — you turned it on and
  run 2 shows it working; test 7 below finishes the job.

---

## 1 — [ ] One rip of the Police disc (covers the two new fixes + 4a)

Rip *Every Breath You Take: The Classics* with your current settings, let it finish.

Both fixes below are about **what the log admits**. Run 2 proved the app *knew*
these things and the log didn't say them.

```sh
cd "<album folder>"
grep -nE "Test CRC|not confirmed reproducible|Read stability" *"(EAC-compatible).log"
```

- Expected: **track 5** now shows a `Test CRC E0036697` line matching its Copy CRC,
  with a "reads converged" note — it was re-read and the reads agreed, which is
  exactly EAC's Test & Copy proof. Run 2 dropped it.
- Expected: **track 3** now carries **`(re-reads did NOT agree — this read is not
  confirmed reproducible)`** on its Copy CRC line…
- …and near the bottom: **`Read stability      : track(s) 3 did not read identically
  across re-reads — not confirmed reproducible`**
- Expected: the other 12 tracks are unchanged — a plain `Copy CRC`, no caveat. We
  only say what was measured.

Sanity check the checksum still verifies with the new lines inside it:

```sh
head -n -1 *"(EAC-compatible).log" | sha256sum   # must match the last line
```

**Result:** ☐ PASS ☐ FAIL — track 5 Test CRC: ☐ yes ☐ no · track 3 caveat: ☐ yes ☐ no

---

## 2 — [ ] Test 7: offset-variant re-read, across two rips

You now have one rip from step 1. Rip the **same disc again**, then compare:

```sh
./platterpus-x86_64.AppImage --compare "<first>.platterpus.json" "<second>.platterpus.json"
```

- Expected: **track 5 byte-identical** between the two rips — it converged in run 2,
  so the setting is doing its job
- Expected: **track 3 may still differ.** That's the disc, not the app: three
  attempts now have failed to read it the same way twice. If it *is* identical,
  even better — say so.
- Expected: those two tracks took noticeably longer than the rest

**Result:** ☐ PASS ☐ FAIL — identical tracks: ____ / ____ · track 3 identical: ☐ y ☐ n

---

## 3 — [ ] Test 18: an interrupted rip must admit it

**Why:** the worst bug of run 1 — a force-stopped rip produced a checksum-signed
log that read as a *complete* one. Still untested.

1. Start a rip, let a couple of tracks finish, then **Cancel**.
2. In that album's folder:

```sh
head -20 *"(EAC-compatible).log"
```

- Expected: a banner near the top —
  **`*** INCOMPLETE RIP (cancelled) — this log covers N of 14 disc tracks. … ***`**
- Expected: near the bottom, **"Conclusive status report : absent"**
- Expected: the checksum still verifies (the banner sits *inside* it, so it can't be
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

## 5 — [ ] Test 4b: whole-disc Test & Copy

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

## 6 — Risk areas (only test 12 needs a full rip)

### 8 — [ ] The app is fine without cd-paranoia

```sh
mv ~/.local/bin/cd-paranoia ~/.local/bin/cd-paranoia.bak
```

1. Relaunch. *Set up drive* → **Analyse cache**.
   - Expected: it says **cd-paranoia isn't installed** and points you at
     *Tools → Set up Platterpus…* — not a vague "could not be determined".
2. Rip a CD → works as before. **Cache defeat** keeps the **saved** measurement from
   run 2 (it's stored per drive, not re-probed), and the EAC log keeps saying `Yes`
   — that's correct, it was really measured. What must *never* happen is a `Yes` on a
   drive that was never probed.
3. `./platterpus-x86_64.AppImage --doctor` → WARN (optional missing), not FAIL.
4. Restore: `mv ~/.local/bin/cd-paranoia.bak ~/.local/bin/cd-paranoia`

**Result:** ☐ PASS ☐ FAIL — message said: ____________

### 9 — [ ] Cache probe: no disc, and cancel mid-probe

1. **Empty drive** → **Analyse cache** → expected: a clear message, no hang, no crash.
2. Disc in, start **Analyse cache**, then **close the dialog while it runs**.
   - Expected: closes cleanly, app stays responsive, drive spins down within a few
     seconds, no crash. (The probe now runs for minutes, so there's plenty of window.)

**Result:** ☐ PASS ☐ FAIL — notes: ____________

### 10 — [ ] Settings persist across a restart

Turn **both** new toggles on → OK → fully quit → relaunch → reopen Settings.

```sh
grep -E "secure_rerip_dynamic|rerip_offset_variant" ~/.config/platterpus/config.toml
```

- Expected: `secure_rerip_dynamic = false` (that's verify-every-track **ON**) and
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

- Expected: folders, templates and offset intact after v0.5.9 → v0.5.10; the drive's
  offset **and** its "confirmed — two independent sources agree" trust line survive;
  the cache-defeat measurement survives.

**Result:** ☐ PASS ☐ FAIL — anything reset? ____________

---

## 7 — [ ] Test 16: UI spot-check

- [ ] *Help → User Guide* mentions **Analyse cache** and **Verify every track**
- [ ] Every Settings control shows a tooltip on hover
- [ ] *Help → About* shows **0.5.10** and correct Qt/Python info
- [ ] Disc-panel values can be selected and copied with the mouse

**Result:** ☐ PASS ☐ FAIL — notes: ____________

---

## 8 — [ ] Part 9 (required): build cyanrip `master` for INDEX 00

Run 2 confirmed your installed cyanrip writes only `INDEX 01`. Upstream `master`
already writes pre-gap markers. **Do this last — it replaces the cyanrip binary**,
so every result above would otherwise be on a different ripper.

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
- Then do **one more normal rip** to confirm AccurateRip still verifies — we changed
  rippers, so this is the safety check.
- If the build fails, send the error and stop there; nothing else depends on it.

Commit built: `git -C ~/cyanrip-master rev-parse --short HEAD` → ____________

**Result:** ☐ PASS ☐ FAIL — INDEX 00 appeared: ☐ yes ☐ no · AccurateRip still OK: ☐ y ☐ n

---

## Send back

1. `~/.local/share/platterpus/log.txt`
2. One album's `.log`, `(EAC-compatible).log`, `.cue`, `.platterpus.json`
3. The `--compare` output from step 2
4. This sheet, filled in

Plus anything surprising, even on a test that passed.

---

*Last updated for Platterpus v0.5.10.*
