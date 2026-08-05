# Rig session sheet — `v0.6.4b4` + cyanrip `c5fb909`

**One session, six steps, ordered so the cheapest evidence comes first.** This is a front
page for a specific pair, not a replacement for
[`hardware-test-checklist.md`](hardware-test-checklist.md) — where a step has a fuller
write-up there, this sheet names the section instead of restating it.

```
Platterpus  v0.6.4b4        GitHub PRE-RELEASE, tag v0.6.4b4 -> commit c7aa67c
cyanrip     c5fb909         0.9.4-rc1+platterpus.5-beta.2   (platterpus-fork-gc5fb909)
drive       Pioneer BDR-209D
round 7     OPEN, HOLD both sides — nothing here is a release
```

> ## ⇒ READ THIS FIRST: A CORRECTION TO WHAT I TOLD YOU IN CHAT
>
> I said *"`-x` on a throwaway rip (H10)"*. **That conflated two different flags that have
> both been called `-x` in this correspondence, and only one of them is ours.**
>
> | | what it is | do we send it? |
> |---|---|---|
> | **`-O`** | force **overread** — read the disc's outermost samples. Our Settings toggle. **This is H10 / F2.** | **yes** |
> | **`-x` / `--cache-probe`** | the fork's **cache probe**, new-ish, *"never executed on real hardware"* | **no** — not in our 16-flag argv surface |
>
> `cyanrip_backend.py` says it outright: *"the `-x` that older project notes named does not
> exist in cyanrip's getopt at all, so passing it would abort every rip."* Their lap 21 §H
> asking for *"`-x` on a rip you can afford to lose"* means **their cache probe**, which
> Platterpus cannot invoke.
>
> **Consequence for this sheet:** steps 1–4 happen **in the app**. Step 5 (`-x`, `-j`)
> happens **at a terminal against the built binary**, because we send neither flag.

---

## Before you start — 5 checks, ~5 minutes, no disc

Each one is here because a session has been lost to its absence.

### P0. Get to `b4` — and the in-app updater will do it

**You must switch channel first.** `update_channel` defaults to `stable`, and **stable
never offers a pre-release**; `v0.6.4b4` is one. So:

1. **Settings → Updates → tick "Offer beta (pre-release) updates"**
2. **Help → Check for updates** → accept the offer
3. **restart** when it asks — the running session holds the old inode

Skip step 1 and "Check for updates" will say you are up to date. That is *correct for your
channel*, not a bug — and if you are already on a beta it adds *"Note: you are running a
pre-release build. Turn on the beta channel in Settings → Updates to be offered newer
betas."*

**Three things about how this update behaves**, all worth knowing before you watch it:

* **It is a full ~242 MB download, not a delta.** The `.zsync` is published and the
  update-information is embedded, but that is for external `AppImageUpdate`;
  `update_install.py` streams the whole AppImage and verifies its SHA-256 against the
  published `.sha256`. Nothing is wrong — it is just not quick.
* **It installs to `~/Applications/platterpus-x86_64.AppImage`, always**, atomically
  replacing whatever is there (safe mid-run — the old session keeps its inode). **If the
  AppImage you actually launch lives somewhere else — `~/Downloads`, a desktop copy — the
  update lands in `~/Applications` and you can carry on launching the old one.** The app
  should offer to relocate a stray AppImage (`is_settled()` exists for exactly this), but
  **P1 is what catches it if that does not happen.**
* **No signature blocker, and this was worth checking rather than assuming.** The
  fail-closed signing gate is dormant — `PUBLIC_KEY_B64` is empty, so
  `signing_configured()` is `False` and integrity is SHA-256 only. Had a key been baked in,
  this update would have been **refused outright**: `b4` publishes no `.minisig`. (Note for
  whoever arms signing: the release ritual has to start producing `.minisig` in the *same*
  change, or the first signed release breaks every in-app update.)

**Manual route, if you would rather not update in-app:** download the AppImage from
[the release](https://github.com/rmccann-hub/Platterpus/releases/tag/v0.6.4b4), verify it
against the published `.sha256`, `chmod +x`, and put it in `~/Applications/`.

### P1. You are on `b4`, not `b3` — **verify, do not assume**

```sh
~/Applications/platterpus-x86_64.AppImage --version
```

Expect `0.6.4b4`. **Run this against the path you will actually launch for the rest of the
session**, which is the point: an update that installed correctly into `~/Applications`
while you keep double-clicking a copy in `~/Downloads` looks exactly like a successful
update until a rip reports the wrong thing.

**Why it matters more than a version string usually does:** `b3` builds `9003e6f` from the
wizard, and if you hand-build `c5fb909` anyway, `b3` **withholds `--consumer`** (a silent
`Consumer: not identified` in the log) and reports log verification as `not_determined`.
Both are fixed only in `b4`.

### P2. Install the test pin, through the app

```sh
~/Applications/platterpus-x86_64.AppImage --install-ripper
```

This drives the **same step engine** as the setup wizard — not a copied shell snippet — and
targets `c5fb909` because `b4`'s `WIZARD_TARGET` says so.

### P3. Confirm the binary is the one we think

```sh
~/.local/bin/cyanrip --version
```

Expect **exactly**:

```
cyanrip 0.9.4-rc1+platterpus.5-beta.2 (platterpus-fork-gc5fb909)
```

**A banner ending `-dirty` is not a valid test build** — the tree had uncommitted changes,
so the commit does not describe the binary. **A banner reading `-grelease` or `-gunknown`
means `vcs_tag` could not resolve a revision**; that was the whole of the `b3` bug, and it
looks like success everywhere else. Stop and say so if you see either.

### P4. Environment check

```sh
~/Applications/platterpus-x86_64.AppImage --doctor
```

Exits non-zero on a hard blocker. Run it now rather than discovering a missing encoder
after a 40-minute rip.

**Record for P0–P4:**

```
channel set to beta : ☐ yes
update route        : ☐ in-app  ☐ manual download
launched path       : ______________________________________________
--version         : ______________
--install-ripper  : ☐ completed   ☐ failed at step: ______________
cyanrip --version : ______________________________________________
--doctor          : ☐ exit 0   ☐ exit non-zero — blocker: ____________
```

---

## Step 0 — Capture stdout for *everything*, from here on

**Last session this was the sole witness to six lines that reached no logfile at all.** The
beta replays pre-log output into the logfile now, which is the fix — but that fix is one of
the things this session is testing, so do not rely on it as the record.

```sh
mkdir -p ~/rig-2026-08-XX && cd ~/rig-2026-08-XX
~/Applications/platterpus-x86_64.AppImage 2>&1 | tee app-stdout.txt
```

For every terminal command below, append `2>&1 | tee <name>.txt`. Keep the files even when
nothing goes wrong — *"nothing was printed"* is only a finding if you were capturing.

---

## Step 1 — A25 pre-gap screening ⭐⭐⭐ *(no rip at all; do this first)*

**Highest value per minute in the session, and it gates two separate fixes.**

The fork's lead-in-counted-twice bug (their C1) fires **only on a disc whose TOC declares a
pre-gap**. The Police disc declares none, so it cannot test C1 — see step 2's note.

**Our own 89× bug (F4) is a different case and it is now PROVEN.** It needed a non-zero
`Pregap LSN`, not a TOC-declared one, and the fork's sub-channel read supplies ten of them:
track 2 reports `Pregap LSN 14327` with a true length of `160`, and we render 160. A25's
premise (*"cyanrip reports none for all fourteen"*) has expired — **A25 closes as passed.**

Screening costs no rip: insert a disc, let Platterpus scan it, then move on.

```sh
# after scanning each disc — the SOURCE line is the discriminating one:
grep "Pregap source:" ~/.local/share/platterpus/log.txt | grep TOC
```

**Any line saying `TOC` is a candidate. There will usually be none.**

> **CORRECTED 2026-08-04.** This step originally said `grep "Pregap LSN:" … | grep -v none`,
> inherited from A25. **That test no longer discriminates.** A25 was written when cyanrip
> reported `none` for every track on this disc; the fork now reads pre-gaps from the
> **sub-channel**, so a non-`none` `Pregap LSN` is present on almost any disc and the grep
> hits every time. Measured over the retained log history: **40+ `Pregap source:` lines,
> every one `lead-in` or `sub-channel (not signalled by TOC)`, zero `TOC`.** The pre-gap
> fixes on both sides fire only where the **TOC** declares it, so `Pregap source: TOC` is
> the only string that answers the question. Best bets, in order:

1. **CD-Extra / enhanced CDs** (audio tracks + a data track) — the data track's pre-gap is
   almost always TOC-declared;
2. **mixed-mode discs** (track 1 is data) — common on older game/software CDs;
3. **live albums and DJ mixes** with index points;
4. anything whose EAC log shows `Pre-gap length` on a *middle* track.

**If you find one:** rip it, and keep the `.log`, the `(EAC-compatible).log` and the
`.platterpus.json`. Also note whether track 1's `Pregap source:` says **`TOC`** — that is
the case their C1 fix needs, and it is the only way this beta's single log-text change gets
tested.

**If nothing in the collection declares one, that is a real result.** Say so, and both
fixes get recorded as *hardware-unprovable* rather than as *untested*. Do not leave it
silent — a blank looks like the step was skipped.

**Record:**

```
discs screened      : ______   (list them, even the misses)
candidate found     : ☐ yes -> disc: ____________________  ☐ no
track 1 Pregap source on the candidate : ☐ TOC   ☐ lead-in   ☐ none   ☐ n/a
our Pre-gap length row : ____________   EAC's row (if you have one): ____________
```

---

## Step 2 — The Police re-rip on `c5fb909`

**This is the regression leg.** Same disc, same drive, same offset as the 2026-08-04 run.
Rip it exactly as you normally would, through the GUI, all 14 tracks, FLAC.

### What it genuinely proves

1. **The pair verified at the drive** — rule 12's *"every rip verifies its own ripper"*,
   against a build no round has approved.
2. **A regression across six commits of fork changes**, anchored properly (step 3).
3. **The new `Read stalls:` line and the replayed pre-log block**, on real hardware for the
   first time.

### What it structurally cannot prove — and this is the important part

The **single log-text change** in this beta is their C1: track 1's pre-gap counting the
2-second lead-in twice, `300 frames` / `00:04.00` where everything else said 150. It fires
**only on a disc whose TOC signals an HTOA.** Your disc reports:

```
Pregap LSN:  0 (duration: 00:02.00)
Pregap length: 150 frames
Pregap source: lead-in        <- lead-in, NOT TOC
```

It reported **150 correctly both before and after** the fix. **So this re-rip is not
evidence about C1.** That is exactly A25's point (step 1), now applying to their fix as
well as to our old one. Say so in the write-up rather than letting a clean run imply the
fix was exercised.

### Expected results — including one that looks like a failure and is not

Open the `.platterpus.json` and check these fields:

| field | expected | why |
|---|---|---|
| `ripper_handshake_approval` | **`unapproved`** | ✅ **CORRECT, not a defect.** No round has approved a test pin. The `detail` should *name* `c5fb909` and say a test-pin sighting during a test session is expected. |
| `ripper_build` | `platterpus-fork-gc5fb909` | never `grelease` / `gunknown` |
| `ripper_version` | `cyanrip 0.9.4-rc1+platterpus.5-beta.2` | |
| `ripper_handshake_note` | `round 7 lap 20 OPEN, verdict HOLD -- NOT a released build` | **`lap 20`, not 21** — a commit cannot contain the hash of a file added after it. Not a bug. |
| `ripper_log_verification` | `verified` | cyanrip checking its own log with its own code. `not_determined` here means the flag was rejected — report it. |
| `read_stalls` | `none (no read exceeded 10s)` | expected on a healthy drive |
| `read_stalls_count` | `0` | |
| `ripper_handshake_approval` vs `ripper_handshake_note` | should agree | **two independent witnesses.** If they disagree, *the disagreement is the finding* — send both. |

**Record:**

```
tracks ripped        : ____ / 14
approval verdict     : ______________  (detail names c5fb909? ☐ yes ☐ no)
ripper_build         : ______________________
handshake_note       : ______________________________________________
log_verification     : ______________
read_stalls          : ______________________  count: ______
witnesses agree      : ☐ yes  ☐ NO -> send both, this is a finding
```

**Keep:** the cyanrip `.log`, the `(EAC-compatible).log`, the `.platterpus.json`, the
`.cue`, and `app-stdout.txt`.

---

## Step 3 — Anchor the rip against **EAC**, not against the previous rip

**The trap this step exists to avoid.** Comparing the new rip to the 2026-08-04 rip
compares **two runs of related builds** — they share an ancestor, so they share its bugs,
and they will agree with flying colours while both being wrong. This project has now hit
that shape from four directions. **Assert against the source artifact.**

The source artifact is EAC's committed baseline log:

```sh
# from a checkout, with the package importable
python3 scripts/eac_parity.py \
    output_reference/EAC_flac/eac_baseline_police_classics.log \
    ~/Music/rips/<the new rip>/<Album>.log
```

It auto-detects the log format, prints a per-track PASS/FAIL table, and **exits non-zero
if any track is not bit-perfect.** 14/14 PASS is the target.

*(EAC writes its log as UTF-16, so a plain `grep` for `Copy CRC` finds nothing — the script
decodes it via `platterpus.parity.decode_log_bytes`. Don't be fooled by an empty grep.)*

**Then, and only as a secondary check**, the run-to-run diff:

```sh
~/Applications/platterpus-x86_64.AppImage --compare <old 9003e6f>.platterpus.json <new c5fb909>.platterpus.json
```

This tells you which tracks are byte-identical between the two builds. Useful, but it is
the *weaker* evidence — it can only tell you the two builds agree, never that either is
right.

**Record:**

```
eac_parity.py     : ____ / 14 PASS   exit code: ____
tracks failing    : ______________________________  (if any)
--compare         : ☐ all byte-identical to the 9003e6f rip
                    ☐ differences on tracks: ______________
```

---

## Step 4 — H10 / F2: the `-O` force-overread line ⭐ *(one track)*

**Why it is owed:** we ship the toggle, and we have never captured the line cyanrip prints
when a drive **accepts** the command. Our parser's handling of it is written against their
published format string and nothing else.

**Note the flag is `-O`, not `-x`** — see the correction at the top.

1. Settings → tick **"Read the disc's outermost samples (overread lead-in/out)"**.
2. Right-click the track table → rip **only track 1**. One track is enough; the line is
   emitted per rip, not per track.

**Send:** just the cyanrip `.log`. The line sits near the top, next to `Overread mode:` /
`Underread mode:`.

**Upstream warns this can freeze a drive that does not support it.** The BDR-209D is
expected to be fine. **If the rip hangs: cancel — and *that is the answer*.** Send the log
and say it hung. A drive that refuses is a documented outcome, not a failed test.

**Afterwards: untick the toggle**, or every later rip in this session carries it.

**Record:**

```
overread line captured : ☐ yes -> paste it: ______________________________
                         ☐ drive hung -> cancelled at: ______  (still a result)
toggle turned back off : ☐ yes
```

---

## Step 5 — Their two flags, at a terminal *(we do not send either)*

Platterpus's argv surface is 16 flags and contains **neither** `-x` nor `-j`. So these are
direct invocations of the binary the wizard just built. **Use a disc you can afford to
lose** and a scratch output directory — nothing here should touch your library.

```sh
cd ~/rig-2026-08-XX
mkdir -p scratch

# 5a — their CACHE PROBE. "The least-tested code in the binary"; it has never
#      produced a measurement on any real drive, anywhere. Refuses on a disc image,
#      so a real disc is the only way to exercise it.
~/.local/bin/cyanrip -x -D scratch -o flac -N 2>&1 | tee cache-probe.txt

# 5b — their JSON DIAGNOSTICS RECORD, new in this beta, never near a drive.
#      Off unless asked for, so it changes nothing else. Combine with a short rip.
~/.local/bin/cyanrip -j scratch/diag.json -D scratch -o flac -N -l 1 2>&1 | tee minus-j.txt
```

**Why 5a is worth the minute:** test pin `f750890` was **withdrawn for cause** because its
cache probe ran *before* the stall watchdog started — so a hang on the least-exercised read
path in the program was **completely silent**. That is the failure mode you are checking
for. If it hangs, cancel and say so; that is the finding.

**Send:** `cache-probe.txt`, `minus-j.txt`, and `scratch/diag.json`.

**Record:**

```
5a  -x  : ☐ printed a measurement -> paste: ______________________
          ☐ hung -> cancelled after ______   ☐ refused -> message: ____________
5b  -j  : ☐ diag.json written, size ______ bytes   ☐ not written
```

---

## Step 6 — One deliberate mid-rip cancel ⭐⭐

**Never fully verified on this drive, and it is the `QThread` + `drive_control` code — the
paths CLAUDE.md calls "written in blood."** Checklist cases A11–A14 and A16 cover the
variants; one honest run of the main one is worth more than none.

Start a full rip, let it reach **track 3 or so**, then press **Cancel**.

| what to watch | expected |
|---|---|
| the window | stays responsive — no "Not Responding", no dead buttons |
| the drive | stops spinning within a few seconds |
| the outcome | recorded as **cancelled**, *not* as a failure |
| the tracks already done | still present and still listed with their CRCs |
| "Open rip folder" | opens the partial folder rather than silently doing nothing |

Then **quit the app within five seconds of cancelling** (A11) — that is the sequence that
found the `v0.5.8` abort, and the shutdown path is bounded by a shared deadline now.

**Record:**

```
cancelled at track   : ______
window responsive    : ☐ yes  ☐ NO -> what froze: ______________
drive stopped in     : ______ s   ☐ never -> say so
recorded as          : ☐ cancelled  ☐ failure (wrong)
completed tracks kept: ☐ yes  ☐ NO -> how many lost: ______
quit within 5s       : ☐ clean  ☐ crash/abort -> message: ______________
```

---

## What to send back, and where

**To this repository** (the durable record — text only):

- the cyanrip `.log`, the `(EAC-compatible).log`, the `.platterpus.json` and the `.cue`
  for each rip;
- `app-stdout.txt`, `cache-probe.txt`, `minus-j.txt`, `scratch/diag.json`;
- the `eac_parity.py` output;
- this sheet with the blanks filled in — **including the misses**.

**Never commit audio.** Critical rule #8: no `.flac`/`.wav`/`.mp3`/etc. in the repo, not
even temporarily. The CRCs in the logs prove bit-perfection without it. The `.githooks`
pre-commit hook blocks it, but the rule is the defence and the hook is the backstop.

**To the cyanrip fork:** the same logs plus `diag.json` — their lap 21 §H asks for
artifacts in **both** repositories.

---

## The honest summary to write at the end

Fill this in even where the answer is "not run" — a blank reads as a pass, and that is the
failure mode this whole sheet is built against.

```
Pair:            Platterpus v0.6.4b4 + cyanrip c5fb909 (banner verified? ☐)
EAC parity:      ____ / 14
A25 screening:   ____ discs, candidate ☐ found ☐ none found  <- a real result either way
C1 (their lead-in fix): ☐ exercised on a TOC-pregap disc   ☐ NOT exercised — no such disc
H10 / -O:        ☐ line captured  ☐ drive hung  ☐ not run
-x cache probe:  ☐ measured  ☐ hung  ☐ refused  ☐ not run
-j record:       ☐ written  ☐ not run
mid-rip cancel:  ☐ clean  ☐ problems: ______________
Round 7 still OPEN, both HOLD. Nothing here approves a pin.
```

---

*Last updated for Platterpus v0.6.4b8.*
