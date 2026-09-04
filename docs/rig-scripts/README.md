# Rig scripts — how to run a hardware session without babysitting it

Scripts here drive the **real** GUI: the same slots a click reaches, the same
argv the app builds, the same ripper binary. There is no simulation layer, which
is deliberate — a harness that is safer or simpler than the product makes the
product's gap invisible.

> **Read this first (v0.6.32).** The full acceptance run is now **Tools → Run
> acceptance test…** inside the app, and that is the route to use. It makes the
> session folder, holds off sleep, runs the batch, releases the lock and packs
> one `.tar.gz` into `~/Downloads` — then names it, with a button that opens the
> folder. **There is nothing to download and no second command in the morning.**
>
> Check the ripper first: **Help → Check for cyanrip updates…** — and *which*
> offer to take depends on whether a handshake round is open, which is the thing
> this note got backwards until v0.6.35.
>
> * **No round open.** Take the offer only if it is a plain one-click install.
> * **A round IS open** (today: round 15, on `978f9b0`). Section A asserts the
>   installed build is the **pin under review**, and a build under review is by
>   definition one no closed round has approved — so its offer is the *warned*
>   one, **"Install it anyway"**, with the consequence stated and *Not now* as
>   the default button. Take it. Declining it is what makes section A abort at
>   L165 four seconds into a six-hour run.
>
> The old wording said to refuse exactly the offer the run requires. It was true
> when written — between rounds the approved build and the pin under review are
> the same commit — and it stopped being true the moment a round opened, which is
> the only time anybody reads it. `platterpus --doctor` names the installed build
> if you want to check without opening the menu.
>
> **The `.txt` scripts moved into the package** (`src/platterpus/rig_scripts/`)
> so the app ships them; an AppImage user used to have no copy of the acceptance
> test at all. The `.sh` wrappers below stay for now as the **legacy route** —
> they still work, and they are what has actually run on the rig before — but
> they are no longer the answer to *"how do I run the acceptance test?"*.

## The T1-only path: `securereread.txt`

**T1 alone, about 2–2.5 hours.** Use this rather than the full file when the only
thing outstanding is the whole-disc uniform secure re-read.

```sh
~/Applications/platterpus-x86_64.AppImage --run-script securereread.txt
```

The 2026-08-24 acceptance run passed 209 of 212 steps and lost only its last
section — a complete 14-of-14 rip, `-T unicode` confirmed on disk, all three
derived formats, cancel and recovery all passed. Re-running the whole file would
spend six hours re-confirming those. This file rips every track in uniform mode
and runs the one `rig-check` that reads the counters.

**What a pass looks like:** `rig-check`'s `parser/paranoia` row reporting
`secure re-read genuinely exercised: YES`. A run reporting `no` is a valid result
about the disc, not a pass — it means the disc converged on the first read and
the test did not get to measure anything.

## The overnight path — LEGACY, superseded by Tools → Run acceptance test…

**Prefer the menu action** (see the note at the top). This wrapper predates it
and does the same job from a terminal; it is kept because it is the path with
real rig hours behind it, and because a build older than v0.6.32 has no menu
action to offer.

Put an ordinary audio CD in the drive and run this. Nothing else.

```sh
bash platterpusovernight.sh
```

It holds sleep, idle and lid-suspend off for the whole run (`systemd-inhibit`,
so the lock dies with the process — nothing to undo), drives the acceptance
script, and then runs the collector for you. **In the morning there is one file
in `~/Downloads` to upload**, named on the `SEND THIS ONE FILE` line.

It is a caller, not a third implementation: the run is still `--run-script
fullacceptance.txt` and the collection is still `platterpusmorning.sh`. Run
either by hand if you want to:

```sh
# The night before — any ordinary audio CD in the drive, then walk away.
~/Applications/platterpus-x86_64.AppImage --run-script fullacceptance.txt

# The morning after — no disc needed, never touches the drive.
bash platterpusmorning.sh
```

**The sleep lock covers the collection as well as the rip.** That is not
belt-and-braces: the collector tars up to a few hundred megabytes, and an
archive interrupted mid-write still opens and still lists — the night's most
important artifact simply is not in it.

`platterpusmorning.sh` exists for one reason, and it is worth stating because
three other collectors look like they already do it: **none of them gathers the
rips.**

| collector | app log | script transcript + screenshots | the run's SEVEN rip folders |
|---|---|---|---|
| the script run's own bundle (*"SEND THIS ONE FILE"*) | ✅ | ✅ | ❌ — `build_bundle()` is called without `album_dir` |
| `--rig-session` | ✅ | ❌ | ❌ — audits the **newest** `.platterpus.json` only |
| `platterpuscollect.sh` | ✅ | partial | **newest rip only** |
| **`platterpusmorning.sh`** | ✅ | ✅ (folds the bundles in) | ✅ **all of them** |

The overnight script performs seven rips. "The newest" is the one beside the
cache probe — **not** the whole-disc uniform secure re-read from its section N,
which is the artifact round 14 closed on, and the one the next round will ask
for again. Collecting the newest loses the night, and loses it *silently*: the
bundle arrives looking complete.

It never copies audio (Critical rule #8) — only the eight text suffixes the
app's own bundler admits — and it then sweeps the staged tree and prints **how
many files it examined**, because a sweep that reports "clean" without a
denominator is satisfied by an empty directory. Every external command is
bounded with `timeout -k`; a bare `timeout` waits forever for a SIGTERM a wedged
drive ioctl will never take.

It prints a count per category and refuses to look healthy on a short bundle:
zero rip artifacts, or fewer than fourteen, is called out in the summary rather
than left for you to notice.

## The normal path: rip by hand, then run one command

**This is what almost everyone should do**, and it needs no script and no
editing:

```sh
# 1. Rip the disc normally, in the GUI. Nothing special.
# 2. Leave the disc in the drive.
# 3. Run this. No arguments.
./platterpus-x86_64.AppImage --rig-session
```

That one command does everything mechanical: app and ripper versions, `--doctor`,
the ripper's own `-j` diagnostics record (which a rip never sends), pre-gap
screening, a clean clone of the fork, handshake status, preflight — **then it finds
the rip you just made**, audits it, runs the cyanrip seam check, collects its text
artifacts, and packs the lot into a single `.tar.gz` to send.

It used to run their `-x` cache probe too. **It no longer does** (2026-08-19): `-x`
measures the cache and then rips the whole disc, so in a command you run *after* a
rig pass it spent five minutes re-reading the disc and left the drive held for
everything after it. The step announces itself as a recorded omission rather than
going quiet — a silent skip and a passed check look identical in a summary. See the
corrections further down.

Nothing is named and nothing is typed. The output directory defaults to a
timestamped one under `$HOME`, so re-running never overwrites the previous
session; the rip is **discovered** rather than named, because a folder you have to
type is a folder you can mistype — and auditing the *wrong* album still produces a
clean-looking report.

**No audio is ever copied.** The bundle carries logs, cue sheets and JSON reports
only. The CRCs inside them prove bit-perfection without the audio, and Critical
rule #8 forbids the rest.

If no rip is found, it says so and marks the step as not-a-pass rather than going
quiet — a silent skip and a clean audit look identical in a summary.

## The scripted path, for when the rip itself should be automated

Scripts in this folder drive the **real** GUI: the same slots a click reaches, the
same argv the app builds, the same ripper binary. There is no simulation layer,
which is deliberate — a harness that is safer or simpler than the product makes
the product's gap invisible.

Reach for this when you want a rip run **the same way twice** — a permutation
sweep, a cancel-path test, a re-rip of specific tracks — not for an ordinary
session. It needs a display (the window is real and on screen) and it needs the
two lines below edited for your disc.

## Running `police-rerip.txt`

```sh
# Put the disc in. Wait for the drive to settle. Confirm Platterpus identified
# the album — that part is still yours.
./platterpus-x86_64.AppImage --run-script police-rerip.txt
```

or, in a running window: **Tools → Run test script…** → **Load** → **Run**.

The window is real and on screen while it runs — the script drives it. This is
"no person needed", not "no display needed".

**Change these two lines for a different disc**, and do not delete either:

```
expect-tracks 14                                   # the disc's real track count
album Synchronicity (rig ddf7ac3 pass 1)           # a distinct folder per pass
```

`expect-tracks` is the floor. Without it a rip that identified nothing reports
success exactly like a real one. The `album` line is what stops pass 2 landing
on top of pass 1 — a session that overwrites its own evidence has destroyed the
thing it was run to produce.

## Running `rigcancelandoverread.txt` — the `[NOT PROVEN]` drive-open item

**This one needs no editing at all**, which is the difference from
`police-rerip.txt` above. Any ordinary audio CD; everything disc-specific is
discovered or expressed as "the first few tracks".

```sh
./platterpus-x86_64.AppImage --run-script rigcancelandoverread.txt
```

It exists because the v0.6.x line ships a claim it cannot make, and no amount of suite
can settle it:

1. **The drive-open fix** — cancelling must release the reader.

There used to be a second item: the fork's `-x` cache probe, which had never run on any
drive. It has now, so it is no longer an open claim — and what it turned out to *do*
makes it an obstacle to item 1 rather than a companion to it. See the two corrections
below.

> **⚠ Corrected 2026-08-18. This list said "`-x` (force overread) has never run
> on a real drive", which conflated two different flags — and did so *one screen
> above the table in this same file that separates them*.** Overread is **`-O`**,
> it **has** run on the BDR-209D (2026-07-22), and it **hung the drive for ~23
> minutes**: 13 of 14 tracks ripped perfectly, then the last track's lead-out
> froze the progress bar near 100 %. So the script must **not** turn overread on
> for this drive — doing so re-triggers a known hang under a claim that is false.
>
> The thing that was genuinely unproven is `-x`, the fork's cache probe, which the
> old script did not test at all. This is exactly the hazard the table below
> warns about, reached by reading this file's own opening.

> **⚠ Corrected again 2026-08-19, and this one corrects the correction above.** The
> 2026-08-18 note closed by saying the cache probe "costs seconds". **Measured
> false.** On the BDR-209D `cyanrip -x -N -s 0` printed
> `Cache probe: 32 sectors, 73.5 KiB, uncached read 362.6 ms` — the first data point
> in existence, and a good one — **and then went on to rip the entire disc**, ETA
> 1h 3m. The script verb killed it at 300 s and the child could not be reaped
> (`exit: null`), so the drive stayed held for the two rips that follow. That is the
> most likely reason that pass's evidence came back unusable.
>
> The `-x` step is therefore **removed from the script** until the fork ships a build
> whose `-x` exits after measuring; the measurement itself is recorded in the
> script's section C so it travels in every transcript. Note what happened here: the
> 2026-08-18 correction was right about `-O` vs `-x` and *guessed* about the cost,
> and the guess is the half that cost a session. `CLAUDE.md`: **did a correction get
> less scrutiny than a claim?** This is its second instance in two weeks
> (`docs/testing.md` §5.aq).

**The cancel test's proof is the rip *after* it, not the cancel.** A cancel is
easy to appear to fix: the button greys out, the status says cancelled, and the
drive is still held by a reader nobody can see. A snapshot taken straight after
cannot tell those apart, so section E starts a second rip; only a released
device allows one.

**That proof only works from v0.6.16 on.** Before it, a cancel left the 5-second
force-stop rescue armed even when the reader had already stopped, so the drive
was ejected moments after every *successful* cancel — which made section E
unanswerable in both directions: an empty tray reads as a failure that is not
real, and a reader freed by the rescue reads as a success the cancel did not
earn. On an older build, section E proves nothing.

Section F no longer restores `force_overread`, because the script never turns it
on; the assertion is kept as a **guard** — if overread is on when the script
ends, something else set it, and that matters before the next disc.

Dialog sizing is **screenshots, not assertions** — clipping is a fact about the
operator's real font size and DPI, and nothing in the script can see it.

Roughly 20–30 minutes. It rips a handful of tracks twice, never the whole disc.
(It was 25–40 while section C ran the cache probe; dropping that step is where
the difference went.)

**Three things it cannot assert**, named in the script itself rather than left
as silence: that a rip *succeeded* (`wait-for-rip` only waits for the worker to
vanish), *what argv* the rip sent (no verb can read it — the witness is the
`Invoked as:` line in the album's own cyanrip log), and *which album*
`rig-check` examined (bare `rig-check` auto-discovers and exits 0 when its log
checks skip). All three need new verbs, filed in `TASKS.md`.

## Reading the result

The transcript is the evidence, not the screen. Every step records `PASS`,
`FAIL`, `ERROR`, `BLOCKED` or `SKIPPED`, with the exit code, the exact argv and
the complete output for anything that ran the ripper. A failing step does **not**
stop the batch — only `abort` does — so read to the end rather than watching.

Artifacts land under `~/.local/share/platterpus/uiscript/<timestamp>/`.

## What the script surface can and cannot reach

Run `Tools → Run test script…` and read the built-in reference — it is rendered
from the vocabulary table itself, so it cannot drift from what actually works.

**Reaches:** the disc pipeline (`rescan`), album metadata (`album`,
`album-artist`), per-track selection (`select-tracks`, which is cyanrip's `-l`),
every Settings field by its `config.toml` name (`set`, `expect`,
`expect-contains` — validated by the same validator the dialog uses, so a script
cannot persist a value the dialog would refuse), the rip itself (`rip`,
`wait-for-rip`, `cancel-rip`), assertions (`expect-tracks`, `expect-dialog`),
evidence (`screenshot`, `snapshot`), dialogs (`open`, `ok`, `cancel`),
**cyanrip itself as a real passthrough** (`cyanrip <args…>`, `expect-cyanrip`,
`expect-exit`), and the **cyanrip seam check** (`rig-check [album-folder]`).

A new testing capability is a **verb here**, not a new command-line flag — that
is a written rule now (`CLAUDE.md`, Code conventions) with a ratchet test behind
it (`tests/test_script_surface_is_the_default.py`). A flag is justified only when
a verb cannot serve: the app has no window yet (`--doctor`), a caller in another
repository must invoke it (`--rig-check`, which the cyanrip fork's own script
calls), or it is how a script run is *started* (`--run-script`). When both are
warranted they are two thin callers of one function, never two implementations.

**Does not reach, on purpose:** ejecting, deleting, uninstalling, installing a
dependency, launching an external app. The failure mode of an unattended
destructive action is unbounded, and all of those are reachable from a GUI a
person is driving. A script that needs one of them is a script that needs a
person.

**`expect-status` now reaches, and the gap it used to be is worth recording.**
It was unimplemented on the argument that there is no single status widget — the
rip-progress pane has one, the disc panel another — so any implementation would
pick one surface and *silently* mean only that. The objection was about the
silence, not the ambiguity: it now reads `RipProgress.current_status()` (the
label under the Overall bar, and the same accessor the desktop notification
reads) and names that surface in its help text and in every failure message.

What forced it: the full-acceptance script *used* the verb, because the generated
reference lists it, and got an ERROR back at **step 179 of 288, 1h 49m in**. Two
things came out of that. The verb is implemented; and the pre-run `_preflight`
now names any step whose verb has no handler, alongside the `cyanrip` steps it
already checked — so a batch says what cannot run before it spends a disc pass
finding out. `expect-status Finished` was also simply *wrong*: the line reads
`Done — all N tracks ripped cleanly, …`, so the assertion would have failed even
implemented. Assert against the artifact, not against a remembered wording.

### The cyanrip passthrough is real, and it is still guarded

`cyanrip <args…>` runs the host-exported binary through
`adapters.rip_backend.run_capture` — the same seam the application's own probes
use, so a script exercises the real path rather than a parallel one that could
drift from it. It inherits that seam's killable child, bounded timeout and
diagnostics-on-failure.

It is **not** unguarded. A scripted argv bypasses the chokepoint every
application-built rip argv passes, so `sanitise_cyanrip_args` re-establishes it
by *delegating* to that same chokepoint: a rip invocation missing `-N` is
refused. Probe flags (`--version`, `-x`, `-j`, `-h`) are exempt because they
never reach the metadata path. Without `-N`, cyanrip runs its own MusicBrainz
lookup and can block on an interactive prompt with no terminal attached — an
unattended batch would hang forever, which is the exact failure the whole
feature exists to prevent.

Arguments carrying a newline or NUL are refused too. That is not injection — we
never use a shell — it is **log forgery**: cyanrip writes its argv into an
archival log, and a newline could fabricate a line in a document whose whole
purpose is being trustworthy evidence.

## ⚠ `-x` is the cache probe. `-O` is overread. Do not confuse them.

| flag | what it does | note |
|---|---|---|
| `-x` / `--cache-probe` | measures the drive's readback cache **and then rips the whole disc** — measured 2026-08-19, ETA 1h 3m, unreapable when killed | fork-only, from round 7 lap 1 |
| `-O` | overread into lead-in/lead-out | **confirmed to hang the BDR-209D for ~23 minutes** |
| `-x` / `--force-overread` | overread | **whipper only** — never cyanrip |

Older revisions of `docs/dependency-contracts.md` said `-x` did not exist in
cyanrip. That was true when measured (2026-07-21, against 0.9.3.1 and upstream
master) and went stale two weeks later when the fork added it. The doc now
carries the correction; this table is here because the confusion is a hardware
hazard rather than a documentation nit.

**`-x` executed on a real drive for the first time on 2026-08-19** (BDR-209D, fork
`platterpus-fork-gddf7ac3`), having never run on any drive by anyone before that. The
measurement: `Cache probe: 32 sectors, 73.5 KiB, uncached read 362.6 ms`. It required
`-s 0` — without an offset cyanrip refuses to open the drive and exits 1 in two
seconds, which wasted the probe's first two attempts.

**And then it ripped the disc**, which is the finding that matters and the reason the
step is no longer in any script here. The absurd-number case the old wording braced
for turned out to be an absurd *behaviour* instead; that it was a finding rather than a
disappointment is still true. What we still do not know, said out loud so nobody reads
the silence as a pass: whether 32 sectors is this drive's real cache, and which of the
`Cache probe:` states a different drive would report.

*Last updated for Platterpus v0.6.35.*
