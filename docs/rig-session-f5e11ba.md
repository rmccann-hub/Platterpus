# Rig session — Platterpus `v0.6.4b8` + cyanrip `f5e11ba`

```
Platterpus  v0.6.4b8        GitHub PRE-RELEASE   (app-only change; the ripper pin did NOT move)
cyanrip     f5e11ba         0.9.4-rc1+platterpus.5-beta.4   (platterpus-fork-gf5e11ba)
drive       Pioneer BDR-209D
round 7     OPEN, HOLD both sides — nothing here is a release
```

**The last session already proved the hard thing.** The fork's A2 denominator change works on
real hardware — your `b6` rip logged `Tracks ripped partially accurately: 1/14` where every
earlier rip said `1/1`, and our side rendered *"1 of 14 tracks matched only an offset-variant
pressing"* with `partially_accurate_reported: "1/14"` kept verbatim. **That is the one thing
no fixture anywhere could reach, and it is done.**

So this session is **not** about the ripper. It is about three things your last rip's own
artifacts revealed, and **almost all of it is now automated** — one command, no disc needed
for most of it.

---

## What changed since your last rip, and what to look for

| fixed | how you would notice |
|---|---|
| **The ETA reached 62 hours** during track 5's re-rip (`51 → 59 → 70 → 85 → 115 → 175 → 335 → 3715 minutes`, then snapped to 11) | the estimate should now stay plausible through a re-rip, and **hold steady** rather than climb when the bar freezes |
| **A truncated debug log dropped the rip's opening** (tail-only) | not user-visible; the sweep in step 2 checks it |
| **Log retention was ~6 MiB** (`1 MiB × 5`) and silently evicted the rip you wanted | `~/.local/share/platterpus/log.txt*` should now grow to 8 MiB each, up to 10 files |
| **Report limits were routine caps** | your next `.platterpus.json` should embed the *whole* verbose log — bigger, on purpose |

> **The ETA is the one to watch with your own eyes.** Everything else is checked by the script.

---

## Step 1 — Update (2 minutes, no disc)

**Settings → Updates → "Offer beta (pre-release) updates" is already ticked.**

> **Help → Check for updates** → accept → **restart**.

Then confirm — **`Help → About` must say 0.6.4b8**.

**Do NOT re-run `--install-ripper`.** The ripper pin is unchanged (`f5e11ba`); you already have
it. Confirm with:

```sh
~/.local/bin/cyanrip --version    # expect 0.9.4-rc1+platterpus.5-beta.4 / platterpus-fork-gf5e11ba
```

---

## Step 2 — One command (this is most of the session)

```sh
bash ~/path/to/Platterpus/scripts/rig_session.sh ~/rig-b8
```

**14 steps, unattended, one artifact each, never stops on a failure** — a failing step is data,
and every exit code is recorded including the successes. It now covers **both projects**.

| # | step | needs a disc? | artifact |
|---|---|---|---|
| P1/P3 | app version + ripper banner, **flags `-dirty`/`-grelease`/`-gunknown`** | no | `01-`, `02-` |
| P4 | `--doctor` | no | `03-` |
| 5a | **their `-x` cache probe** — never executed on any real drive, ever | **yes** | `04-` |
| 5b | **their `-j` diagnostics record** — never written from a physical drive | **yes** | `05-` |
| 1 | A25 pre-gap screening off the app log | no | `06-` |
| 0 | snapshots the app logs **before rotation eats them** | no | `07-`, `logs/` |
| 3 | `--audit-rips` over `~/Music` | no | `08-` |
| 3 | `eac_parity.py` against EAC's committed baseline | no | `09-` |
| **10** | **ETA sweep — every report on the machine checked for an absurd peak** | no | `10-` |
| **11** | **report sizes + log retention** (is the 88 MiB window holding?) | no | `11-` |
| **12** | **clones the cyanrip fork FRESH** and records its refs — their own lap-25 §C1 lesson: a suite verified in the tree that built it is not verified for a consumer | no | `12-` |
| **13** | our handshake `--status` and `preflight --no-network` | no | `13-`, `14-` |

**Step 10 is the new one that matters.** It reads every `*.platterpus.json` under `~/Music`,
extracts the ETA trace, and prints the peak estimate per rip with the count of samples. Your
`b6` rip will show a **62-hour peak**; every rip from `b8` on must not. It says so explicitly if
it finds no traces at all, because *"found nothing"* is not a pass.

> **`-x` may hang.** Bounded at 300 s; the script says so if it trips. Their audit §3.1: *"A
> hang is also a result."*

---

## Step 3 — Rip the Police CD once more, and watch the ETA (the only real human step)

Same disc, same settings, through the GUI.

**Track 5 will need a re-rip again** — that is expected and is exactly the moment to watch.

```
During track 5's re-rip, the "about … left" estimate:
  highest value you saw     : ____________
  did it ever exceed 1 hour : ☐ no   ☐ YES -> what did it say: ____________
  did it climb steadily up  : ☐ no   ☐ yes
  did it hold steady        : ☐ yes  ☐ no -> describe: ____________
  did it ever VANISH        : ☐ no   ☐ yes  (at what % ______)
overall: did the estimate feel usable?  ☐ yes  ☐ no
```

**Also worth one look:** the finished `.platterpus.json` should be *larger* than the last one
(the debug log is no longer capped). If it is much *smaller*, that is a bug — tell me.

---

## Optional — the mid-rip cancel, still never verified on this drive

Carried forward because nothing has tested it yet. Skip it if you are short on time; it does not
block the release.

Start a rip, let it reach track 3, press **Cancel**, then **quit within five seconds**.

```
cancelled at track   : ______
window responsive    : ☐ yes  ☐ NO -> what froze: ______________
drive stopped in      : ______ s   ☐ never
recorded as           : ☐ cancelled  ☐ failure (wrong)
tracks kept           : ☐ yes  ☐ NO -> how many lost: ______
"Open rip folder"     : ☐ opens the partial folder  ☐ does nothing
quit within 5s        : ☐ clean  ☐ crash -> message: ______________
```

---

## One open question only your disc can settle

Your last rip's track 5 was read **twice**, and the two reads disagree:

| | first pass (discarded) | second pass (on disk) |
|---|---|---|
| Copy CRC | `6902BCF0` | **`E0036697`** |
| AccurateRip v1 | `7CE3F6E7` | **`F5426D5F`** |
| AccurateRip v2 | `268CCD94` | **`9EEB8843`** |
| AccurateRip **+450** | `4CCBCF89` | **`4CCBCF89`** ← *identical* |

Three of four changed, so the audio changed — yet **+450 did not**, and +450 is the single
value our entire "partially accurate, confidence 200" verdict for track 5 rests on.

**Our side is now ruled out.** The fold that swaps a re-ripped track's record takes the
AccurateRip results from the **shipped** read and explicitly refuses to inherit the first
pass's verdict — it logs a drop rather than carrying one (`_verified_by_this_read`). So
`4CCBCF89` is **cyanrip's own number, computed independently on the second read**, not a
stale value of ours. That leaves two possibilities, and both are the fork's to answer: the
differing samples fall outside the +450 CRC's window (legitimate, and interesting), or its
+450 computation is not sensitive to what changed. **A third read of track 5 is what
distinguishes them**, which is why step 3 is worth doing rather than skipping.

**Do not delete the album** — it is a good library entry (13 exact + 1 offset-variant, all
converged), and the files are the only copy of that second pass.

---

## What this session proves — and what it does not

| step | proves | does **not** prove |
|---|---|---|
| 1 | `b7` is installed and identifies itself | nothing about ripping |
| 2 step 10 | no report on the machine carries an absurd ETA | nothing about whether the *displayed* number was sane — only step 3 sees that |
| 2 step 11 | retention and report sizing behave as intended | nothing about content |
| 2 step 12 | what a fresh clone of the fork actually contains | it does not run their suite — that is theirs to run |
| 3 | the ETA fix **as the user experiences it**, and a third read of track 5 | nothing about a *crash* mid-rip |
| cancel | cancel and shutdown on this drive | nothing about a crash path |

**Still unproven by anything here:** the diagnosed-abort exit code (needs a rip that genuinely
fails — eject mid-rip, or a full disk), `-f` offset autodetection, and a non-zero `Read stalls:`
count.

---

## What to send

**The whole `~/rig-b8` directory**, plus from the new rip: the cyanrip `.log`, the
`(EAC-compatible).log`, the `.platterpus.json`, the `.cue`, the addendum if one appears — and
this sheet with steps 3 and the cancel block filled in.

**Empty artifacts still matter.** A file that exists and is empty is a measurement; a missing
file is a step that did not run, and only one of those is a result.

**Never audio.** Critical rule #8 — the per-track CRCs prove bit-perfection without it.

---

*Last updated for Platterpus v0.6.4b10.*
