HANDSHAKE-PROTOCOL: 2
HANDSHAKE-ROUND: 7
HANDSHAKE-LAP: 9
HANDSHAKE-FROM: platterpus
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-APP-VERSION: platterpus 0.6.4b1
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.5-beta.1 (platterpus-fork-g9003e6f)
HANDSHAKE-PIN: 2f950c8
HANDSHAKE-TEST-PIN: v0.6.4b1
CONSUMER-CONTRACT: docs/cyanrip-consumer-contract.md @ v0.6.4b1

# Platterpus beta — `v0.6.4b1`

*Information only. This file describes the beta and nothing else. Round 7 stays OPEN,
verdict **HOLD**; the production pin `2f950c8` does not move.*

---

## Identifiers

```
version   0.6.4b1
repo      rmccann-hub/Platterpus
branch    main
tag       v0.6.4b1
release   GitHub pre-release, assets attached
artifact  platterpus-x86_64.AppImage  (+ .sha256, + .zsync)
reports   --version prints: platterpus 0.6.4b1
```

**The tag is the identifier.** Unlike the fork, this side can publish: the release
workflow creates the tag itself via the Actions API, so `v0.6.4b1` is a real GitHub
pre-release with downloadable assets and a signed build-provenance attestation.

**This is a pre-release.** It claims no joint verification, and every rip report it
writes says so — see *What every rip report from this build records*.

## The pair

```
Platterpus  0.6.4b1                        tag v0.6.4b1
cyanrip     0.9.4-rc1+platterpus.5-beta.1  commit 9003e6f on platterpus-fork
```

Both spellings are as the other side published them. The version base stays
`0.9.4-rc1`.

## What the beta builds and installs

`platterpus --install-ripper` and the setup wizard build **`9003e6f`**, not the
production pin. One `ForkTarget` object carries the commit and the banner a correct
build must print, and the build step and the verify step read the same field off it,
so the two cannot be given different builds.

The install prints, before it starts, that this is not the approved build and that
every rip will therefore report `unapproved`.

`platterpus-fork-g9003e6f` is on the list of builds that accept `--consumer`, so the
beta sends it and rig logs carry both halves of the pair rather than
`Consumer: not identified`. A `-dirty` suffix on a listed commit is tolerated for the
flag decision only.

## What every rip report from this build records

Report schema **v15**. Every rip carries, alongside the existing fields:

```
ripper_handshake_approval        unapproved | approved | not_determined
ripper_handshake_detail          one sentence, written for a person
ripper_handshake_observed_banner what the binary said it was
ripper_handshake_approved_banner what a closed round approved
ripper_handshake_round           the round whose bilateral GO settled it
```

Against `9003e6f` the verdict is **`unapproved`**, and the detail names the reason:
that build is the round-7 test pin, nominated by both projects for the joint
hardware session, and no round has approved it. A retired test pin reports
`unapproved` too and says it is retired. An absent or unreadable build tag reports
`not_determined` — never the negative.

## Diagnostic capture from the ripper

Per invocation the report records the ripper's **exit code** as tri-state (`null`
for a child never reaped, never written as `0`), the **exact argv** read off
`Popen.args`, and the **complete output with stderr merged**. Where output is
bounded it keeps **head and tail** with the elision marked and counted, so a fatal
message — the last thing a tool prints — survives.

A rip with more than one pass records the first pass's argv separately from the
last, because the archival log's `Invoked as:` line is written by the first.

## Flags this build sends

40 flags, generated from the argv builder rather than listed by hand; the full
surface is in `docs/cyanrip-consumer-contract.md` at this tag. The ones specific to
this pairing:

| flag | |
|---|---|
| `-u` / `--consumer <string>` | sent only to builds known to accept it |
| `-N` | always; the GUI does its own MusicBrainz lookup and feeds tags in |
| `-k <seconds>` | stall threshold, from the read-speed settings |
| `-x` | cache probe, when the user enables it |

Every argument derived from anything other than the disc being ripped gets a range
check at the argv chokepoint before it becomes an argument.

## Also in this beta

- **Beta update channel**, off by default. A pre-release offer says in the dialog
  that it is a pre-release, and "Yes" is not the pre-selected button. Release
  versions sort PEP 440-aware, so `0.6.4b1 < 0.6.4b2 < 0.6.4rc1 < 0.6.4` — a beta
  is not a one-way door.
- **The argv self-check no longer accuses a clean rip.** It compares the first
  pass's argv with the log's `Invoked as:` line; previously it compared the last
  pass's, so any rip where the dynamic secure re-rip fired reported that something
  between the two projects had altered the command line.
- `outcome.failure_hint` is no longer populated on successful rips.
- The AppImage is built from this tree. It previously resolved `platterpus` from
  PyPI, which for a pre-release version silently produced an AppImage of the
  previous release.

## Known limits of this build

- **No hardware evidence yet.** H9, H10 and H12 are what this beta exists to run.
  Nothing in this build's test suite exercises a real drive.
- **The rip-time approval check has never seen an approved build in the field.**
  Its `approved` branch is unit-tested only; every rig run in this session will
  take the `unapproved` branch by design.
- **`--consumer` has not been exercised against a real ripper.** It is gated on the
  build tag, and the gating is tested; the flag reaching `9003e6f` on hardware is
  not.
- **Seven of the ripper's refusal paths reach stdout only**, before its logfile
  exists. This build captures stdout for every invocation, which is what makes
  those diagnosable; nothing in the archived *logfile* can show them.

---

*Round 7 OPEN, verdict **HOLD**. Production pin `2f950c8` unchanged. Platterpus
`v0.6.4b1` is a published pre-release paired with cyanrip
`0.9.4-rc1+platterpus.5-beta.1` (`9003e6f`) — **a test pair, not a verified one**.
`scripts/handshake.py --release-gate` exits non-zero against this record;
`--release-gate --prerelease` exits 0 after printing every open round.*

*Last updated for Platterpus v0.6.4b1.*
