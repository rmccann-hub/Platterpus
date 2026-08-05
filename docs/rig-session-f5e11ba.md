# Rig session — Platterpus `v0.6.4b6` + cyanrip `f5e11ba` (**cutting edge, both sides**)

**Most of this is a script.** `scripts/rig_session.sh` runs unattended, captures its own
output and writes one artifact per step. So this sheet is **three human steps and one
command** — the steps a script cannot do: insert a disc, click Cancel, watch a window.

```
Platterpus  v0.6.4b6        GitHub PRE-RELEASE
cyanrip     f5e11ba         0.9.4-rc1+platterpus.5-beta.4   (platterpus-fork-gf5e11ba)
drive       Pioneer BDR-209D
round 7     OPEN, HOLD both sides — nothing here is a release
```

**Why this pair, and why it changed.** The previous sheet paired `b5` with `e61e75a`, the
*conservative* build. That was overruled on purpose: **test cutting edge on both sides.** The
fork's `f5e11ba` carries two log-text changes, and one of them **changes a number** that
cannot be verified anywhere except a real disc with an AccurateRip entry — so a session spent
on the conservative build would leave the one unverifiable change unverified and still need a
second session. `b6` also ships *our* half of that change, so for the first time this round
both sides of the seam move together.

---

## Step 1 — Update, install the new ripper, rip the Police CD

### 1a. Update Platterpus

**Settings → Updates → "Offer beta (pre-release) updates" is already ticked** from last time.

> **Help → Check for updates** → accept → **restart** when offered.

Full ~242 MB download (not a delta), installs to
`~/Applications/platterpus-x86_64.AppImage`, SHA-256 is the integrity check.

**Confirm it took** before going on — `Help → About` should say **0.6.4b6**.

### 1b. Install the new ripper pin

```sh
~/Applications/platterpus-x86_64.AppImage --install-ripper
```

`b6` targets `f5e11ba`. **This replaces whatever you have** (`c5fb909` or `e61e75a`).

Confirm:

```sh
~/.local/bin/cyanrip --version
```

Must print `0.9.4-rc1+platterpus.5-beta.4` and `platterpus-fork-gf5e11ba`. **If it says
`-dirty`, `-grelease` or `-gunknown`, stop and report it** — that banner names a tree that is
not the pin, and nothing measured afterwards would be attributable.

### 1c. Rip the Police CD

Through the GUI, all 14 tracks, FLAC, exactly as normal.

**Two things are new and worth a glance in the finished log:**

| line | should now read |
|---|---|
| `Consumer:` | `platterpus/0.6.4b6` — **not** `not identified (no --consumer given)` |
| `Tracks ripped partially accurately:` | **`1/14`** — it read `1/1` on every previous rip |

The second one is the whole reason for taking this build. Same disc, same track (**track 5**),
same verdict — only the denominator moved, and it is the one change nobody could test without
your drive.

> **Expect no visible change in the app** from that line: our side was fixed in `b6` to count
> the offset-variant tracks itself, so the summary should read *"1 of 14 tracks matched only an
> offset-variant pressing"* on both old and new logs. **If it instead says something about
> tracks "not fully verified", or mentions a disagreement, that is a real bug — send it.**

---

## Step 2 — Run the script

```sh
bash ~/path/to/Platterpus/scripts/rig_session.sh ~/rig-2026-08-05
```

Not in a checkout? Download the script from the repo and run it the same way — it degrades
gracefully and says which step it skipped.

**Takes a few minutes and wants a disc in the drive** (any disc you can afford to lose — it
rips one track to a scratch directory).

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

> **`-x` may hang. That is a result, not a mistake.** Bounded at 300 s; the script says so if
> it trips. The fork's audit §3.1: *"A hang is also a result."*

---

## Step 3 — One deliberate mid-rip cancel *(the only thing left that needs you)*

Never verified on this drive, and it is the `QThread` + `drive_control` code — the paths
CLAUDE.md calls *"written in blood."*

Start a full rip, let it reach **track 3 or so**, press **Cancel**, then **quit the app within
five seconds**.

```
cancelled at track   : ______
window responsive    : ☐ yes  ☐ NO -> what froze: ______________
drive stopped in     : ______ s   ☐ never
recorded as          : ☐ cancelled  ☐ failure (wrong)
tracks kept          : ☐ yes  ☐ NO -> how many lost: ______
"Open rip folder"    : ☐ opens the partial folder  ☐ does nothing
quit within 5s       : ☐ clean  ☐ crash -> message: ______________
```

---

## The A/B this session exists for

The fork asked for exactly this: **re-rip the baseline disc and diff against the log we
already hold** (`c5fb909`, 2026-08-04, committed in the repo).

| line | held (`c5fb909`) | must read on `f5e11ba` |
|---|---|---|
| `Tracks ripped accurately:` | `13/14` | `13/14` — unchanged |
| `Tracks ripped partially accurately:` | `1/1` | **`1/14`** |
| cover-art warning | `Release ID unavailable, …` | **`No MusicBrainz release ID at cover art lookup, …`** |
| everything else | — | byte-identical but for the banner, `Handshake:`, timings and the checksum |

**Anything else that moves is a finding**, and the fork wants it. You do not have to do this
diff by hand — send the log and it gets done here.

---

## Optional, if a disc happens to be handy

Neither is worth hunting for; both are cheap if already in reach.

* **A disc with CD-TEXT** — a different code path (`mmc_read_cdtext`) from the `.toc` parser
  their tests use. Most commercial CDs have none; some reissues and many Japanese pressings
  do. Rip it and send the log.
* **A scratched or marginal disc** ripped with paranoia working hard — a **non-zero**
  `Read stalls:` count has never been produced anywhere.

---

## What each step proves — and what it does not

So a green run cannot be read as broader coverage than it is.

| step | proves | does **not** prove |
|---|---|---|
| 1a/1b | the pair is installed and identifies itself | nothing about ripping |
| 1c | **A2's denominator on real hardware** — the one change no fixture can reach; plus that `--consumer` reaches the ripper | nothing new about bit-perfection until `eac_parity.py` runs |
| 5a `-x` | that the cache probe returns a number at all, or that it wedges | nothing about whether the number is *correct* — no baseline exists |
| 5b `-j` | the record is written by a real drive and agrees with the log | nothing about long rips — the message cap has only been driven directly |
| A25 | whether a TOC-declared pre-gap exists in your collection | it cannot prove the fix wrong; "no candidate" is a real result |
| `--audit-rips` | which build made each rip, and that the claimed files exist | nothing about bit-perfection |
| `eac_parity.py` | per-track CRCs equal EAC's committed baseline | only for discs you have an EAC log of |
| Step 3 | cancel and shutdown behave on this drive | nothing about a *crash* mid-rip — different path |

**Still not provable by anything here:** the diagnosed-abort exit code (needs a rip that
genuinely fails — eject mid-rip, or a full disk), `-f` offset autodetection, and the track-1
pre-gap fix on real hardware (the fork's golden reference covers it on a TOC-declaring
*image*, which needs no drive).

---

## What to send

**The whole `~/rig-2026-08-05` directory**, plus from the Police rip:

- the cyanrip `.log`, the `(EAC-compatible).log`, the `.platterpus.json`, the `.cue`, and the
  `.platterpus-addendum.txt` if one appears;
- this sheet with Step 3 filled in.

**Empty artifacts still matter.** A file that exists and is empty is a measurement; a missing
file is a step that did not run, and only one of those is a result.

**Never audio.** Critical rule #8 — the per-track CRCs prove bit-perfection without it.

---

*Last updated for Platterpus v0.6.4b6.*
