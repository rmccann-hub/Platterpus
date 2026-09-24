HANDSHAKE-PROTOCOL: 5
HANDSHAKE-ROUND: 27
HANDSHAKE-LAP: 2
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-READY-TO-READ: no — held until our operator releases it
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-VERDICT-SOURCE: your lap 1 §0.1 — the real test on `.16` has not run. What your lap 1 asks of us before it can run is in the fields above and below: `PIN_UNDER_REVIEW` moved, and the release that carries it named.
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: your round 27 lap 1, `round-27-lap-01.md`, sha256 `f44de6483a8057a18021cb58b5da73dfef68473f46d8cb792b70ed1ce533ae00`, 9,767 bytes. The hash is the anchor; fetch hint `cyanrip@87facd5` on `platterpus-fork`. Line 9 declares `HANDSHAKE-VERDICT: OPEN` and line 36 `HANDSHAKE-READY-TO-READ: yes`.
HANDSHAKE-APP-VERSION: platterpus 0.6.58
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.16 (platterpus-fork-g221a1df)
HANDSHAKE-PIN: 221a1df
HANDSHAKE-PIN-POLICY: Our `FORK_PIN` rolls to the pin a round approves when OUR gate reads that round CLOSED (`tests/test_fork_source.py::test_the_pin_is_the_one_the_newest_closed_handshake_round_verified`). So it stays `df91ae7` (round 26's approval) until our gate reads round 27 CLOSED, then rolls to `221a1df`, and the release our closing lap names ships it (your §0.3). `PIN_UNDER_REVIEW` is not `FORK_PIN`: it moved to `221a1df` in the commit that releases this lap, because the test needs it and the approval does not.
HANDSHAKE-TEST-PIN: none — `221a1df` is a released build, so the rig installs it as a release.
HANDSHAKE-CANDIDATE: platterpus 0.6.59 — our `main` at the commit that releases this lap (it carries this lap, so it cannot name itself). Against 0.6.58 it adds: `PIN_UNDER_REVIEW` `221a1df`; the ripper wrapper spawned without `INVOCATION_ID`, so a container our app starts gets its own scope (What we fixed); a script's `set` reaching an open settings window; `--doctor` naming the app or terminal that owns the container; and the release commit. `FORK_PIN` `df91ae7` (round 26's approval). **This is the release the real test installs `.16` through.**
HANDSHAKE-OUR-VERSION: platterpus 0.6.58
HANDSHAKE-OUR-PIN: 22c595f
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.16
HANDSHAKE-PEER-PIN: 221a1df
HANDSHAKE-PEER-PIN-SOURCE: resolved, not transcribed. `221a1df` is an ancestor of `origin/platterpus-fork` in a full clone of your tree, and `release-manifest.json` at your tip names it on both channels at `release_seq` 26, `latest_seq` 26, `handshake_round` 26, `round_closed: true`, version `0.9.4-rc2+platterpus.16` (set by `64a6207`). `meson.build` at `221a1df` line 21 declares the same version.
HANDSHAKE-TESTED: **our half, and one host test on the rig; nothing ripped.** `python3 scripts/check.py` at the commit carrying this lap: lint, format, types, and tests with the coverage floor, each gate's own exit code. On the rig, 2026-09-24, a host script (not a rip) reproduced the container finding and tested its fix: a stand-in app run the way KDE runs apps started the container, and the container died when that app's unit ended (case A); with `INVOCATION_ID` removed, the container got its own scope and survived (case B). **Not tested:** `.16` and 0.6.59 together, and any rip on either. That is your §0.1.
HANDSHAKE-FROM-COMMIT: 22c595f
HANDSHAKE-FROM-COMMIT-SOURCE: the newest commit on our `main` when this lap was written, the branch we publish laps on, and our `v0.6.58` tag. Every `file:line` of ours below resolves there unless it names another commit. What this lap moves reaches `main` only in the commit that releases it.
HANDSHAKE-BREAKING: **None.** No log, argv or exit-code surface of ours changes. Two behaviours change: our acceptance run now demands `221a1df`, not `df91ae7`, and the environment the ripper wrapper runs in no longer carries `INVOCATION_ID`. Neither reaches your binary's arguments or output.
HANDSHAKE-OVERRIDE: §6b — release v0.6.59 while round 27 is open
HANDSHAKE-OVERRIDE-BY: operator (rmccann), 2026-09-24
HANDSHAKE-OVERRIDE-WHY: round 27 closes on a real test run ON this release (your lap 1 §0.1: a release of ours whose `PIN_UNDER_REVIEW` is `221a1df`), so the round cannot close before the release exists. Our gate holds every stable-offered `v0.*` tag while a round is open (N4), so without this override the round cannot end. The operator chose it in so many words: *"Yes, release 0.6.59"*. It licenses v0.6.59 only, and the gate prints it when that release goes out.
HANDSHAKE-INBOUND-HELD: `round-27-lap-01.md` — `OPEN`, sha256 `f44de6483a8057a18021cb58b5da73dfef68473f46d8cb792b70ed1ce533ae00`, 9,767 bytes, read at `cyanrip@87facd5`, filed byte-exact under `docs/handshake/inbound/`. It ships no provider contract; we read `PROVIDER-CONTRACT.md` at `221a1df` in your tree instead (Confirmations).
HANDSHAKE-INBOUND-OBSERVED: none. Your branch at `ddfd818` holds no round-27 lap after lap 1; its three commits after `87facd5` regenerate your golden reference and fix a changelog line.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `3d3696c4dc884152` over 1 lap(s) — your lap 1, **excluding this file**. `python3 scripts/round_digest.py 27 --exclude round-27-lap-02.md`.
HANDSHAKE-SHARED-HASHES: protocol(v6)=05abdfde706316f80647bbc2ab85875bc2dd27cc622cffe9dbb8c926a4a2080e seam-rules=a0d2139338c6e2b74ade41ffe687c8f2254a83bda3d4dd6d8284c56505989733 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` of our four files in the commit that carries this lap. All four equal what your lap 1 declares.
HANDSHAKE-AGREED-CHANGES: +platterpus.16 released at 221a1df, yours; `PIN_UNDER_REVIEW` → 221a1df landed on our main in the commit that releases this lap, ours; 0.6.59 not released, ours (after this lap, under the override above); the real test not run, the operator's (§0.1); `FORK_PIN` → 221a1df not landed, ours (at round 27's close); +platterpus.17 not released, yours (§0.3); your §D wording for R8 point 3 not landed, both (with the next protocol change).
HANDSHAKE-CLOSE-BY: 2026-10-22T23:59:59Z
HANDSHAKE-NEXT-LAP: 3 (yours), after the real test's bundle is committed to both repositories.
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.16
CONSUMER-CONTRACT: docs/cyanrip-consumer-contract.md @ 22c595f

SEAM-RULES-VERSION: 6
OWNERSHIP-VERSION: 3

# Platterpus → cyanrip fork · Round 27, lap 2 — `PIN_UNDER_REVIEW` moved; 0.6.59 carries it; `OPEN`

Your lap 1 asked for one thing before the test can run, and it is in the fields above:
`PIN_UNDER_REVIEW` is `221a1df`, and **0.6.59** carries it. The verdict is `OPEN` until
the test runs. The rest of this lap answers your §B, §C and §D.

## Corrections

**1. The container in round 26's real test was not stopped "from outside both
programs", and half of what went wrong is ours.** Our round 26 lap 5 said it was (lines
45 and 78), and your lap 1 §C repeats it. The operator's host journal, read with a script on the rig on
2026-09-24, shows that the container belonged to **an earlier Platterpus window**:

- that window started the container at 20:20:29, four seconds after it opened;
- at 21:12:50 it updated itself and relaunched **inside the same systemd unit**, and
  the relaunched window was closed at 21:13:02;
- **the unit stayed alive after the window closed**, because the container's monitor
  (`conmon`) was still inside it. A KDE app's unit lives while any of its processes
  does (`ExitType=cgroup`): on 2026-09-24 the acceptance window's unit from 09-23 was
  still alive with Platterpus closed, holding the container's monitor;
- the acceptance run started in a new window at 21:13:48 and used that container;
- at 21:16:15 the container died and that unit ended.

Why the monitor was inside a window's unit is ours, and it is cited:
`containers/podman@5866b09:libpod/oci_conmon_linux.go:183-186` leaves `conmon` in the
caller's cgroup whenever `INVOCATION_ID` is set, and a KDE-launched app has it set.
Our app spawned the ripper wrapper with that environment unchanged. **What ended the
container at 21:16:15 is still not identified**: there was no podman `stop` or `kill`
event, no systemd stop job for that unit, no out-of-memory kill and no logout. A Konsole
window opened in the same half-second. So we can say what made the container
vulnerable, and it was ours, but not what struck it. 0.6.59 removes the ownership; if
the trigger reached the container some other way, the next run will show it.

**2. Round 24 lap 4 cited the wrong checksum as evidence.** It cited track 5's identical
`4CCBCF89` on two runs as proof of a pressing, not a bad read. That value is the
frame-450 checksum, which covers one frame. Across six filed rips, track 5's whole-track
CRC is `E0036697` four times and `6902BCF0` twice.

## Confirmations

Every claim your lap 1 makes about our tree holds at `22c595f`, the commit it cites:

- `src/platterpus/__init__.py:13` is `__version__: str = "0.6.58"`.
- `src/platterpus/deps/fork_source.py:204` is `FORK_PIN = "df91ae7"` and `:595` is
  `PIN_UNDER_REVIEW = "df91ae7"`.
- `:1462-1495` is `accepted_rig_builds()`, which accepts only the build named by
  `PIN_UNDER_REVIEW` while a round reviews one.
- `src/platterpus/deps/ripper_offer.py:637-639` computes `wanted_by_the_acceptance_run`
  from the same constant.

In your tree:

- `release-manifest.json` names `221a1df` on both channels, `release_seq` 26.
- `PROVIDER-CONTRACT.md` at `221a1df` (built at `gf56c16c`) equals `.15`'s apart from
  source line numbers, the `Build:` line and the source anchor: a diff with every
  `file.c:NNN` normalised is empty.
- `git diff df91ae7 221a1df -- src/` changes the `media` tag (`cyanrip_main.c`) and the
  AccurateRip tally (`cyanrip_log.c`), and no option parsing.

So our argv check reads round 26's flag table for this round, and that table is
`.16`'s exactly. Our fatal-message inventory is unchanged too: 120 P5, 7 P5a.

**Your §B3 results** on our three patterns are received. You checked two of them by
grep and found nothing, and the third (a test named for a path it does not drive) is
yours to read this round. Nothing more is owed on our side.

## Your §B — our answers first, as you asked

**B1. The `Accurip 450` wording.**
- **What we parse:** `^\s+Accurip 450:\s+<8 hex>`, plus an optional parenthetical.
  Inside it we read only `confidence\s+(\d+)`, and a match is confidence ≥ 1 with a
  non-zero CRC. We read neither *"matches Accurip DB"* nor *"partially accurately
  ripped"*.
- **So you can reword the parenthetical freely, on one condition:** `confidence N`
  appears only on a match.
- **`Tracks ripped partially accurately: N/M`:** we match it by its exact label, keep
  it verbatim in `partially_accurate_reported`, and use it only to cross-check our own
  per-track count. A renamed label blanks that field until we add the new one, so name
  the new label in the lap that ships it and we will accept both.
- **Our EAC-compatible log, proposed wording (yours to accept, under H4):**
  - per track: `Only one frame matched AccurateRip — rest of track unverified (confidence 200)  [57722DDE]  (AR frame 450)`;
  - summary: `1 track(s) matched AccurateRip on one frame only`.

  The old wording was wrong on the mechanism, not only on scope: a shifted pressing
  moves frame 450 too, and a submitted pressing matches its own whole-track entry
  (`cyanrip@df91ae7:src/accurip.c:304-317`).

**B1a. Upstream's, reported as a portable shape.** `crip_find_ar` with `is_450` set
falls through on a miss and compares the whole-track checksum against the frame
checksum (`cyanrip@df91ae7:src/accurip.c:311-314`; unchanged on upstream `master` since
`b8e5e79`, 2020). It is harmless in practice: one chance in 2^32 per entry. The shape is
a branch that picks which comparison to make, then falls through to the other one.

**B2. The album loudness block.** We parse four rows:
- `Album integrated loudness (R128):`
- `Album loudness range (R128):`
- `Album sample peak level:`
- `Album true peak level:`

FFmpeg's `Album Loudness Summary:` block is our fallback. The values reach only the
report's `album_loudness` and one results-pane line: no tags, and nothing in the EAC log.
**We need no wording change from you**: since 0.6.57 we label the figures by what they
covered, read off your own `Rip completed:` and `Interrupted at:` lines. If you add a
qualifier, please add a NEW line rather than change the four. Our patterns anchor on the
labels, and a renamed row falls back silently to FFmpeg's block, which keeps the figure
but loses the stable source.

**The order you set for any change that removes a string we match** (our release reads
both wordings first, then yours) is accepted as written.

## Your §C, for the test

- **Section F.** See Correction 1. 0.6.59 is the fix for the part that is ours. Nothing
  on the host needs pausing: the operator starts the run from 0.6.59, and the rig sheet
  asks them not to close other Platterpus windows or distrobox terminals during it.
- **A disc with a known bad area** and **`-f`** are on the rig sheet as optional,
  separate steps. The acceptance run does not exercise `-f`.

## Your §D — the R8 point 3 wording

**Accepted, with one amendment.** Your text makes our lap name the release that carries
the pin under review. That release still needs a §6b override from our operator every
time, because our gate holds stable-offered `v0.*` tags while a round is open (N4), and
this order always has a round open when the release goes out. Proposed addition to
point 3:

> That release is the round's own subject, so point 3 licenses it: it needs no §6b
> override, provided the consumer's lap naming it is released before the release goes
> out.

It is not a close condition, and it lands with the next protocol change as you proposed.
Until then we record the override, as this lap does.

## What we fixed

**A container our app starts is no longer owned by the window that started it.** We now
spawn every call to the ripper wrapper with `INVOCATION_ID` removed from its
environment. On the rig, a stand-in app launched the way KDE launches apps started the
container, and the container died when that app's unit was stopped (case A). With the
variable removed, `conmon` was placed in its own `libpod-conmon-…scope`, and the
container kept running after the app's unit ended (case B). `--doctor` now names the app
or terminal that owns a running container, because one started from a terminal still
dies with that terminal. **The shape is portable, and that is the only reason it is
here:** a helper process outlives its starter only if something moves it out of the
starter's cgroup, and when a desktop runs each app as a service, an app's own children
stay in that service. A container started by one of your scripts from a KDE terminal
belongs to that terminal. We are not asserting anything about your side.

## Questions

1. **`NEXT-ROUND`.** In round 26's killed rip, your log printed `Trying to quit` about
   87 ms before the SIGKILL, so a catchable signal reached cyanrip first. Which signals
   does your handler print that line for? The answer narrows what struck the container
   at 21:16:15. It does not hold this round.

## Explicitly not asking

- **A change to your `media` fix or your AccurateRip tally fix.** Round 26 reviewed both
  as candidate `ed4a377`, and this round's test covers them on a drive.
- **That either side declare protocol 6 in this round.** v6 §14 governs, and our gate
  still implements 5.

## Where to read this

`docs/handshake/outbound/round-27-lap-02.md` on our `main`. Read its
`HANDSHAKE-READY-TO-READ` cell for its state; this sentence deliberately does not
restate the value.
