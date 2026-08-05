# Rig session — Platterpus `v0.6.4b5` + cyanrip `e61e75a`

**Most of this is now a script.** `scripts/rig_session.sh` runs unattended, captures its
own output and writes one artifact per step — the fork's lap 24 §E2 ask: *"the rig session
is the scarce resource; anything that runs unattended and writes an artifact is worth more
than a checklist line."*

So this sheet is **three human steps and one command**. The human steps are the ones a
script cannot do: insert a disc, click Cancel, watch a window.

```
Platterpus  v0.6.4b5        GitHub PRE-RELEASE
cyanrip     e61e75a         0.9.4-rc1+platterpus.5-beta.3   (platterpus-fork-ge61e75a)
drive       Pioneer BDR-209D
round 7     OPEN, HOLD both sides — nothing here is a release
```

**Why this pair:** the fork's lap 24 §E1 asked us to cut a beta against `e61e75a` so the
session tests a *declared pair* rather than a new ripper against the previous app. `e61e75a`
is `c5fb909` plus one memory-leak fix and is **observably identical** to it — they measured
log body (275 lines), cue, decoded PCM and the `-j` record side by side — so the 2026-08-04
parity evidence transfers and **the disc parity does not need repeating.**

---

## Step 1 — Update (in-app), then rip the Police CD

Exactly what you planned. Two human actions.

### 1a. Update

**Settings → Updates → "Offer beta (pre-release) updates" is already ticked** from last
time. So:

> **Help → Check for updates** → accept → **restart** when it offers.

It is a full ~242 MB download (not a delta), it installs to
`~/Applications/platterpus-x86_64.AppImage`, and SHA-256 is the integrity check.

### 1b. Install the new ripper pin

```sh
~/Applications/platterpus-x86_64.AppImage --install-ripper
```

`b5` targets `e61e75a`, so this builds the new beta. **This replaces `c5fb909`.**

### 1c. Rip the Police CD

Through the GUI, all 14 tracks, FLAC, exactly as normal.

> **One thing is genuinely new and worth a glance:** the log should now say
> `Consumer: platterpus/0.6.4b5` instead of `Consumer: not identified (no --consumer given)`.
> That flag had **never** been sent by any Platterpus version; your last rip's log is what
> revealed it. If it still says *not identified*, that is the single most important thing to
> report back.

---

## Step 2 — Run the script

```sh
bash ~/path/to/Platterpus/scripts/rig_session.sh ~/rig-2026-08-05
```

Or, if you are not in a checkout, download it from the repo and run it the same way — it
degrades gracefully and says which step it skipped.

**It takes a few minutes and needs a disc in the drive** (any disc you can afford to lose —
it rips one track to a scratch directory). It does:

| step | what it does | artifact |
|---|---|---|
| P1 / P3 | app version + ripper banner, and **flags `-dirty`/`-grelease`/`-gunknown`** | `01-`, `02-` |
| P4 | `--doctor` | `03-` |
| **5a** | **their `-x` cache probe** — never executed on a real drive, anywhere, ever | `04-` |
| **5b** | **their `-j` diagnostics record** — never written by a rip from a physical drive | `05-`, `scratch/diag.json` |
| 1 | A25 pre-gap screening, off the app log | `06-` |
| 0 | snapshots your app logs **before rotation eats them** | `07-`, `logs/` |
| 3 | `--audit-rips` over `~/Music` | `08-` |
| 3 | `eac_parity.py` against EAC's committed baseline | `09-` |

**It never stops on a failure** — a failing step is data. Every step records its exit code
even on success, and writes a file even when it finds nothing.

> **`-x` may hang. That is a result, not a mistake.** It is bounded at 300s and the script
> says so if it trips. Their audit §3.1: *"A hang is also a result."*

---

## Step 3 — One deliberate mid-rip cancel *(the only thing left that needs you)*

Never verified on this drive, and it is the `QThread` + `drive_control` code — the paths
CLAUDE.md calls *"written in blood."*

Start a full rip, let it reach **track 3 or so**, press **Cancel**, then **quit the app
within five seconds**.

| watch | expected |
|---|---|
| the window | responsive throughout — no "Not Responding", no dead buttons |
| the drive | stops within a few seconds |
| the outcome | recorded as **cancelled**, not as a failure |
| tracks already done | still present, still listed with their CRCs |
| "Open rip folder" | opens the partial folder, not silently nothing |
| quitting within 5s | clean exit, no abort |

```
cancelled at track   : ______
window responsive    : ☐ yes  ☐ NO -> what froze: ______________
drive stopped in     : ______ s   ☐ never
recorded as          : ☐ cancelled  ☐ failure (wrong)
tracks kept          : ☐ yes  ☐ NO -> how many lost: ______
quit within 5s       : ☐ clean  ☐ crash -> message: ______________
```

---

## Optional, if a disc happens to be handy

Neither is worth hunting for; both are cheap if the disc is already in reach.

* **A disc with CD-TEXT** — different code path (`mmc_read_cdtext`) from the `.toc` parser
  their tests use. Most commercial CDs have none; some reissues and many Japanese pressings
  do. Just rip it and send the log.
* **A scratched or marginal disc**, ripped with paranoia working hard — a **non-zero**
  `Read stalls:` count has never been produced anywhere. If you try one, their `-k 1` lowers
  the stall threshold and provokes it fastest, but that needs a terminal rip rather than the
  GUI.

---

## What each step proves — and what it does not

Their §E2 asked for this explicitly, *"so a green run cannot be read as broader coverage
than it is."*

| step | proves | does **not** prove |
|---|---|---|
| 1a/1b | the pair is installed and identifies itself | nothing about ripping |
| 1c | `--consumer` now reaches the ripper; the pair works end to end on a known disc | nothing new about parity — that was settled on `c5fb909` and transfers |
| 5a `-x` | that the cache probe's number is a number at all, or that it wedges | nothing about the *correctness* of the number; no baseline exists |
| 5b `-j` | the record is written by a real drive, and agrees with the log | nothing about long rips — the message cap has only ever been driven directly |
| A25 | whether a TOC-declared pre-gap exists in your collection | it cannot prove the fix is *wrong*; a "no candidate" is a real result |
| `--audit-rips` | which build made each rip, and that the claimed files exist | nothing about bit-perfection — that is `eac_parity.py` |
| `eac_parity.py` | per-track CRCs equal EAC's committed baseline | only for discs you have an EAC log of |
| Step 3 | cancel and shutdown behave on this drive | nothing about a *crash* mid-rip — different path |

**Still not provable by anything in this session:** the diagnosed-abort exit code (needs a
rip that genuinely fails — eject mid-rip, or a full disk), `-f` offset autodetection, and
the track-1 pre-gap fix on real hardware. The last one their golden reference now covers on
a TOC-declaring **image**, which is the cheapest route and needs no drive.

---

## What to send

**The whole `~/rig-2026-08-05` directory**, plus from the Police rip:

- the cyanrip `.log`, the `(EAC-compatible).log`, the `.platterpus.json`, the `.cue`, and
  the `.platterpus-addendum.txt` if one appears;
- this sheet with Step 3 filled in.

**Empty artifacts still matter.** A file that exists and is empty is a measurement; a
missing file is a step that did not run, and only one of those is a result.

**Never audio.** Critical rule #8 — the per-track CRCs prove bit-perfection without it.

---

*Last updated for Platterpus v0.6.4b5.*
