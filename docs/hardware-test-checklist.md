# Hardware test checklist — v0.5.8

> **What this is.** The fillable run sheet for *this release's* hardware test on the
> Bazzite + Pioneer BDR-209D rig. Every step is written out — copy-paste the
> commands, tick the box, jot what you saw. This is the "what do I do now" sheet;
> [`test-plan.md`](test-plan.md) stays the full reference (the clean-cycle
> acceptance run, the distro matrices, and the deep single-feature cases).
>
> **Order matters.** Do Parts 0→4 with the **released** app first. Part 5
> (INDEX 00) *replaces the cyanrip binary*, so it goes last — otherwise every
> earlier result is on a different ripper than the one shipped.
>
> **Two starred tests need something sent back to me:** ⭐ **1** (the raw
> `cd-paranoia -A` output) and ⭐ **14** (what your `.cue` contains). Those two
> unblock code that's deliberately written conservatively until it sees real output.
>
> **Never commit audio** — logs, `.cue`, `.platterpus.json`, and CRCs only
> (Critical rule #8).

**Tester:** ____________  **Date:** ____________  **App version:** ____________

| Environment | Value |
|---|---|
| Distro / kernel | |
| Drive (make · model · firmware) | |
| cyanrip version | |
| Test disc(s) used | |

---

## Part 0 — Setup (about 5 minutes)

### 0.1 — [ ] Update your existing install (do **not** uninstall)

**Update in place — that's the right path for this sheet.** Do *not* uninstall
first: test 13 checks that your existing settings and drive profile survive the
upgrade, and a clean install would destroy the very state it validates. (A full
uninstall → reinstall belongs to the separate clean-cycle acceptance run in
[`test-plan.md`](test-plan.md) Part A, which tests the *first-run* experience.)

**Preferred — the in-app updater** (this also tests the updater itself):
*Help → Check for updates…* → let it download, verify, and install → accept the
restart it offers.

**Or by hand**, if you'd rather drop the file in yourself:

```sh
chmod +x platterpus-x86_64.AppImage
./platterpus-x86_64.AppImage --version
```

- Expected either way: `platterpus 0.5.8 (<build>)`.
- Expected: your output folder, templates, and read offset are all still set —
  nothing reset by the update.

**Result:** ☐ PASS ☐ FAIL — updated via: ☐ in-app ☐ by hand — version: ____________

### 0.2 — [ ] Doctor (no CD needed)

```sh
./platterpus-x86_64.AppImage --doctor
```

- Expected: no hard failures. `cd-paranoia` may appear as **optional, missing** at
  this point — that's a WARN, not a failure, and step 0.3 fixes it.

**Result:** ☐ PASS ☐ FAIL — notes: ____________

### 0.3 — [ ] Run the setup wizard (installs the new `cd-paranoia` tool)

*Tools → Set up Platterpus…* → **Run setup**.

- Expected: every existing row says "already present"; a **new last row**,
  *"cd-paranoia cache probe (optional)"*, installs and exports.
- Expected: the wizard still reports overall **success** even if that last row
  fails — it's optional and must never block ripping.

Then confirm it landed on the host:

```sh
ls -l ~/.local/bin/cd-paranoia && ~/.local/bin/cd-paranoia --version
```

**If that last row failed** (this install path is unverified on real hardware —
please note exactly what it said), install it by hand and re-run the wizard:

```sh
distrobox enter ripping
command -v cd-paranoia            # may already be there via libcdio
sudo dnf install -y libcdio       # if not
distrobox-export --bin /usr/bin/cd-paranoia
exit
```

**Result:** ☐ PASS ☐ FAIL — wizard row said: ____________

### 0.4 — [ ] Turn on the EAC-compatible log (required for tests 3 and 4)

*Tools → Settings* → tick **"Write an EAC-compatible log"** → OK.

It's off by default, and tests 3–4 read that file, so this must be on.

**Result:** ☐ done

---

## Part 1 — New in v0.5.8: the four EAC-parity features

### ⭐ 1 — [ ] Cache-defeat measurement — capture the raw output

**Why:** the EAC log's *"Defeat audio cache"* line has always read `(unknown)`.
This measures it. **I need the raw text to finish tuning the parser.**

1. Put any audio CD in the drive.
2. Run the tool directly and **save the whole output**:

```sh
~/.local/bin/cd-paranoia -A -d /dev/sr0 > ~/cdparanoia-A-output.txt 2>&1
cat ~/cdparanoia-A-output.txt
```

3. Send me `~/cdparanoia-A-output.txt`.

**Result:** ☐ captured — file attached ☐ command failed: ____________

### 2 — [ ] Cache-defeat verdict in the app

1. *Tools → Set up drive* → click **Analyse cache** (with a disc in the drive).
2. Wait for it to finish.

- Expected: the results box says *"✓ Audio cache: …(saved)"* **or**
  *"could not be determined"* — but **never** a blank or a crash.
- Expected: the window stays responsive the whole time (no "Not Responding").
- Expected: the disc panel's new **Cache defeat** row now shows
  `Yes — …(measured, cd-paranoia)`, `No — …`, or `not measured yet`.
- Close and reopen the app → the row still shows the same thing (it's saved per drive).

**Result:** ☐ PASS ☐ FAIL — panel row read: ____________

### 3 — [ ] Log integrity checksum — verify it yourself

**Why:** our log now carries a SHA-256 anyone can check with standard tools —
at least as strong as EAC's, and openly verifiable.

1. Rip any CD (a short one is fine).
2. In the album folder, find the file ending `(EAC-compatible).log`.
3. Look at its last line, then re-compute the hash over everything above it:

```sh
cd "<album folder>"
tail -1 *"(EAC-compatible).log"                      # shows the stored checksum
head -n -1 *"(EAC-compatible).log" | sha256sum       # re-computes it
```

- Expected: the 64-character hex from `sha256sum` **matches** the hex in the last line.
- Expected: the last line names *Platterpus* and says *NOT an EAC checksum*.
- Expected: the top of the file says it is **not** a genuine EAC log.

4. Tamper test — prove it detects a change:

```sh
cp *"(EAC-compatible).log" /tmp/t.log
sed -i '5s/./X/' /tmp/t.log                          # change one character
head -n -1 /tmp/t.log | sha256sum                    # must now DIFFER
```

**Result:** ☐ PASS ☐ FAIL — matched: ☐ yes ☐ no · tamper detected: ☐ yes ☐ no

### 4 — [ ] Test & Copy CRC pair

**Why:** EAC prints a Test CRC and a Copy CRC; when two reads agree, that's the
proof. Ours shows the same pair when a track was confirmed by ≥2 agreeing reads.

**4a — default (fast) mode.** Using the log from test 3:

```sh
grep -E "Test CRC|Copy CRC" *"(EAC-compatible).log"
```

- Expected on a clean disc: mostly **Copy CRC** lines only (nothing was re-read,
  so no second read is claimed — that's correct, not a bug).
- Any track that *did* get re-read shows a matching **Test CRC** + **Copy CRC**
  plus *"confirmed across N secure re-reads"*.

**4b — whole-disc mode.** *Settings* → tick **"Verify every track with a second
read (EAC-style Test & Copy)"**, confirm **"Max reads to confirm a shaky track"**
is 2 or more → OK. Re-rip the same disc, then:

```sh
grep -c "Test CRC" *"(EAC-compatible).log"
```

- Expected: a **Test CRC for every track** now, each equal to its Copy CRC.
- Expected: the rip takes noticeably longer (it reads everything twice).

**Result:** 4a ☐ PASS ☐ FAIL · 4b ☐ PASS ☐ FAIL — Test CRC count: ____ / ____ tracks

### 5 — [ ] Read offset auto-confirmed by AccurateRip

**Why:** when a rip matches AccurateRip, the offset it used is proven right on
*your* drive — so the app should promote it to "confirmed".

1. Note the disc panel's **Read offset** line *before* ripping: ____________
2. Rip a mainstream CD that AccurateRip knows (at least one track must verify).
3. Look at the **Read offset** line again.

- Expected: it now reads **"confirmed — two independent sources agree"** (or
  names an AccurateRip-matching rip as the source).
- Expected: the offset **value** is unchanged (+667) — only its trust label improved.

**Result:** ☐ PASS ☐ FAIL — line after: ____________

---

## Part 2 — Shipped in v0.5.7, never hardware-tested

### 6 — [ ] Per-track "Rip?" selection

1. Insert a CD and let it identify.
2. The track grid has a leading **Rip?** column — all ticked.
3. Untick two tracks → **Start rip**.
   - Expected: only the ticked tracks are ripped; file numbering matches the
     original track numbers (not renumbered 1..N).
4. Untick **everything** → **Start rip**.
   - Expected: a clear message blocks the start (no rip attempted, no crash).
5. Highlight 2–3 rows → **right-click**.
   - Expected: a menu with *Rip only these* / include / exclude / select all / none,
     and each does what it says.

**Result:** ☐ PASS ☐ FAIL — notes: ____________

### 7 — [ ] Offset-variant re-read toggle

**Why:** last session's finding — tracks 3 & 5 of *The Police — The Classics* read
differently each rip while still "partially accurate". This setting fixes that.

1. *Settings* → tick **"Also re-read offset-variant (partially accurate) tracks"**.
2. Rip the disc that showed the problem (tracks 3 & 5) **twice**.
3. Compare the two rips:

```sh
./platterpus-x86_64.AppImage --compare "<first>.platterpus.json" "<second>.platterpus.json"
```

- Expected: tracks 3 & 5 are now **byte-identical** between the two rips (that was
  the whole point) — 13/13 identical rather than 11/13.
- Expected: those tracks took longer (they were re-read until reads agreed).

**Result:** ☐ PASS ☐ FAIL — identical tracks: ____ / ____

---

## Part 3 — Things we have never tested before

These are the risk areas this release introduced (or that we simply never checked).

### 8 — [ ] The app is fine **without** cd-paranoia

**Why:** it's a brand-new optional dependency. Missing it must cost nothing but
the cache verdict.

```sh
mv ~/.local/bin/cd-paranoia ~/.local/bin/cd-paranoia.bak
```

1. Relaunch the app. Rip a CD.
   - Expected: the rip works **exactly** as before.
   - Expected: the **Cache defeat** row says *not measured yet*.
   - Expected: the EAC log's *Defeat audio cache* says `(unknown)` — **never** a
     made-up `Yes`.
2. *Set up drive* → **Analyse cache**.
   - Expected: an honest "could not be determined" message, no crash, no freeze.
3. `./platterpus-x86_64.AppImage --doctor` → expected: WARN (optional missing), not FAIL.
4. Restore it: `mv ~/.local/bin/cd-paranoia.bak ~/.local/bin/cd-paranoia`

**Result:** ☐ PASS ☐ FAIL — notes: ____________

### 9 — [ ] Cache probe: no disc, and cancel mid-probe

1. **Empty drive** → *Set up drive* → **Analyse cache**.
   - Expected: a clear "could not be determined" (or a no-disc message); no hang,
     no crash.
2. Insert a disc, start **Analyse cache**, then **close the dialog while it runs**.
   - Expected: the dialog closes cleanly, the app stays alive and responsive, and
     the drive spins down within a few seconds.
   - Expected: no "QThread destroyed" style crash.

**Result:** ☐ PASS ☐ FAIL — notes: ____________

### 10 — [ ] Settings persist across a restart

1. Turn **on** both new toggles (verify-every-track, offset-variant re-read). OK.
2. Fully quit the app, relaunch, reopen Settings.
   - Expected: both still on.
3. Confirm on disk:

```sh
grep -E "secure_rerip_dynamic|rerip_offset_variant" ~/.config/platterpus/config.toml
```

- Expected: `secure_rerip_dynamic = false` (that's "verify every track" ON) and
  `rerip_offset_variant = true`.

**Result:** ☐ PASS ☐ FAIL — values: ____________

### 11 — [ ] Contradictory settings degrade sensibly

Set **"Verify every track"** ON *and* **"Max reads"** to **Off (0)** → OK → rip a CD.

- Expected: the rip still completes normally and the log is coherent (with no
  second read available, tracks show a single Copy CRC — not a fake Test CRC, and
  not a crash).

**Result:** ☐ PASS ☐ FAIL — notes: ____________

### 12 — [ ] Log checksum survives the library auto-move

**Why:** we move finished rips into the library folder. Moving must not invalidate
the log's checksum.

1. Make sure a **library folder** is set in Settings, then rip a CD so it auto-moves.
2. In the album's **new** location, re-verify as in test 3:

```sh
cd "<library album folder>"
tail -1 *"(EAC-compatible).log"
head -n -1 *"(EAC-compatible).log" | sha256sum
```

- Expected: still matches (a move copies bytes unchanged).

**Result:** ☐ PASS ☐ FAIL — matched: ☐ yes ☐ no

### 13 — [ ] Upgrading over an existing setup

**Why:** you already had a v0.5.7 config and a drive profile on disk, and you
updated in place at step 0.1 — this confirms nothing was lost. (This is the test
that a clean reinstall would have made impossible, which is why step 0.1 says
don't uninstall.)

- Expected: your existing settings (output folder, working folder, templates,
  library folder, read offset) are all intact — nothing reset to defaults.
- Expected: your drive's recorded offset **and** its provenance/trust line survived.
- Expected: the new settings appear at their defaults (verify-every-track **off**,
  offset-variant re-read **off**) rather than switched on behind your back.

```sh
ls -l ~/.config/platterpus/config.toml ~/.config/platterpus/drive_profiles.json
grep -E "output_dir|read_offset|library_dir" ~/.config/platterpus/config.toml
```

**Result:** ☐ PASS ☐ FAIL — anything reset? ____________

---

## Part 4 — Quick regression sweep (30 minutes)

A lot changed this cycle; these all worked before and must still work. One clean
rip covers most of it.

### 14 — [ ] One clean rip, end to end

Rip a mainstream CD with defaults (after undoing the test-11 settings).

- [ ] Disc identified; MusicBrainz match correct
- [ ] Progress: **one** progress bar (no duplicate in the track grid)
- [ ] Drive row shows **make · model · firmware · /dev/srN**
- [ ] cyanrip's live output appears while ripping (View log during the rip)
- [ ] Green verdict: all tracks verified against AccurateRip
- [ ] Folder holds: audio, `.log`, `.cue`, `.platterpus.json`, `(EAC-compatible).log`
- [ ] FLACs play, tags correct, cover art embedded

**Result:** ☐ PASS ☐ FAIL — notes: ____________

### 15 — [ ] Cancel / freeze recovery still works

1. Start a rip, then **Cancel** partway.
   - [ ] Drive spins down (use **Force stop** if not)
   - [ ] **Open rip folder** works *after* the cancel
   - [ ] **View log** works *after* the cancel
2. Optional (this is what hung the drive before): tick **Overread**, rip, and if it
   stalls confirm the **stall banner** appears within ~45 s and names overread.
   Then untick Overread again.

**Result:** ☐ PASS ☐ FAIL — notes: ____________

### 16 — [ ] UI accuracy spot-check

- [ ] *Help → User Guide* mentions the new **Analyse cache** and
      **Verify every track** settings
- [ ] Hovering **every** Settings control shows a tooltip
- [ ] *Help → About* shows version 0.5.8 and correct Qt/Python info
- [ ] Disc-panel values can be selected and copied with the mouse

**Result:** ☐ PASS ☐ FAIL — notes: ____________

---

## Part 5 — INDEX 00 pre-gap (do this LAST — it swaps the cyanrip binary)

### ⭐ 17 — [ ] What does your `.cue` contain today? (baseline — send this)

```sh
grep -nE "INDEX|PREGAP" "<album folder>/<album>.cue"
```

- If you see only `INDEX 01` lines → the gap is real on your installed cyanrip.
- If you already see `INDEX 00` or `PREGAP` → **the gap is already closed** and
  step 18 is unnecessary. Either way, **send me this output.**

**Result:** ☐ only INDEX 01 ☐ INDEX 00 present — pasted output sent: ☐

### 18 — [ ] Build cyanrip `master` and re-check

Only if step 17 showed no `INDEX 00`. Upstream `master` already writes pre-gap
markers; your installed copy is the 2-year-old release.

```sh
distrobox enter ripping
git clone https://github.com/cyanreg/cyanrip ~/cyanrip-master
cd ~/cyanrip-master
meson setup build && ninja -C build
build/src/cyanrip -V                       # confirm it built
exit
```

Then rip a disc **that has a pre-gap** using that build and check its cue again:

```sh
grep -nE "INDEX|PREGAP" "<new album folder>/<album>.cue"
```

- Expected: `INDEX 00` / `PREGAP` lines now present.
- If yes, keep it: `distrobox enter ripping -- distrobox-export --bin ~/cyanrip-master/build/src/cyanrip`
- Sanity-check afterwards: one more normal rip still verifies against AccurateRip
  (we changed rippers — make sure nothing regressed).

**Result:** ☐ PASS ☐ FAIL ☐ skipped — INDEX 00 appeared: ☐ yes ☐ no

**Note the commit you built** (so a rip report can say which cyanrip made it):
`git -C ~/cyanrip-master rev-parse --short HEAD` → ____________

---

## What to send back

1. ⭐ `~/cdparanoia-A-output.txt` (test 1) — unblocks the cache-verdict parser.
2. ⭐ The `grep INDEX` output (test 17) — tells us if INDEX 00 needs the fork at all.
3. `~/.local/share/platterpus/log.txt` (the app log).
4. One album's `.log`, `(EAC-compatible).log`, `.cue`, and `.platterpus.json`.
5. This sheet, filled in.

**No audio files** — the text artifacts prove everything (Critical rule #8).

## Report template

```
Test:            <number + name>
Result:          PASS / FAIL / SKIPPED
What I saw:      <one or two lines>
Unexpected:      <anything surprising, even if it passed>
```

---

*Last updated for Platterpus v0.5.8.*
