# Rig scripts — how to run a hardware session without babysitting it

Scripts here drive the **real** GUI: the same slots a click reaches, the same
argv the app builds, the same ripper binary. There is no simulation layer, which
is deliberate — a harness that is safer or simpler than the product makes the
product's gap invisible.

## The three-step shape of a session

| step | what runs it | what it produces |
|---|---|---|
| **1. before** the disc goes in | `platterpus --rig-session <dir>` | versions, `--doctor`, `-x`, `-j`, pre-gap screening, handshake status, preflight — one artifact per step |
| **2. with** the disc in | `Tools → Run test script…` with a script from this folder | the rip itself, plus a transcript, screenshots and state snapshots |
| **3. after** | `platterpus --audit-rips <music folder>` | the artifact checks, per album, graded |

Step 1 and step 3 are already automated and ship inside the AppImage. This
folder is step 2 — the part that needs the disc in the drive **and** a rip.

## Running `police-rerip.txt`

```sh
# Put the disc in. Wait for the drive to settle. Confirm Platterpus identified
# the album — that part is still yours.
./platterpus-x86_64.AppImage --run-script docs/rig-scripts/police-rerip.txt
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
evidence (`screenshot`, `snapshot`), dialogs (`open`, `ok`, `cancel`), and
**cyanrip itself as a real passthrough** (`cyanrip <args…>`, `expect-cyanrip`,
`expect-exit`).

**Does not reach, on purpose:** ejecting, deleting, uninstalling, installing a
dependency, launching an external app. The failure mode of an unattended
destructive action is unbounded, and all of those are reachable from a GUI a
person is driving. A script that needs one of them is a script that needs a
person.

**Does not reach, as a known gap:** `expect-status`. There is no single status
widget to assert against — progress lives in the rip-progress pane and
identification in the disc panel — so it would have to pick one surface and
silently mean only that. `expect-dialog` and `expect-tracks` cover what it was
drafted for. The row is left in the reference marked *NOT YET IMPLEMENTED* so
the gap is visible rather than forgotten.

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
| `-x` / `--cache-probe` | measures the drive's readback cache, costs seconds | fork-only, from round 7 lap 1 |
| `-O` | overread into lead-in/lead-out | **confirmed to hang the BDR-209D for ~23 minutes** |
| `-x` / `--force-overread` | overread | **whipper only** — never cyanrip |

Older revisions of `docs/dependency-contracts.md` said `-x` did not exist in
cyanrip. That was true when measured (2026-07-21, against 0.9.3.1 and upstream
master) and went stale two weeks later when the fork added it. The doc now
carries the correction; this table is here because the confusion is a hardware
hazard rather than a documentation nit.

**As of 2026-08-07 `-x` has never executed on a real drive, by anyone.** Whatever
it prints is the first data point in existence — including an absurd number,
which is a finding and a good outcome.
