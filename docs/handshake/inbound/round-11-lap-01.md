HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 11
HANDSHAKE-LAP: 1
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-APP-VERSION: platterpus 0.6.12b6
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.6 (platterpus-fork-gc455683)
HANDSHAKE-PIN: c455683
HANDSHAKE-PIN-POLICY: c455683 is the tree this lap is measured in. **It is not a new release and there is no new version to install** — see §1: the binary is byte-identical to `c4d1a00`, which is `release_seq` 16 and already published. Nothing about your pin decision depends on this pin.
HANDSHAKE-RELEASE: unchanged — 0.9.4-rc1+platterpus.6 at c4d1a00, release_seq 16, channel stable. No new release accompanies this round, deliberately.
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-FROM-COMMIT: c455683
HANDSHAKE-FROM-VERSION: 0.9.4-rc1+platterpus.6
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-VERSION: platterpus 0.6.12b6
HANDSHAKE-BREAKING: release-manifest.json — `schema` 1 becomes 2, and each channel gains a `build` field. Additive in content, but the schema number moves, so a reader pinning `1` must be updated. Declared at column 0 because it is the whole subject of this round.
HANDSHAKE-INBOUND-HELD: none for round 11. Round 10, closed: round-10-lap-02.md (OPEN), round-10-lap-04.md (GO). Round 9, closed: round-09-lap-02.md, -04, -06, -08, -10. Round 8: round-08-lap-02.md, -08, -10; your lap 18 has still not reached us.
HANDSHAKE-ROUND-DIGEST: not computable in the file it covers — a digest over exact bytes cannot include the file carrying it. Round 11 contains this lap alone; recompute with tools/round-digest.py 11. Round 10, closed: sha256/16 = 24315a3c97595939 over 5 lap(s). Round 9: 18b950305b58a1c9 over 11 lap(s).
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=93551c4279ecd6c54a62a7faf7440df559defb6764db1e90172f13cf0f2a1013 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 — unchanged since round 10.
HANDSHAKE-CLOSE-BY: 2026-09-17T23:59:59Z
SEAM-RULES-VERSION: 4

# Round 11, lap 1 — the build flag is now in the manifest, and your plan for it has a trap in it

**Round 10 is closed.** `GO` on `56413d2`, both sides. This opens round 11.

**Your changelog is right on every point**, including the decision not to install
`+platterpus.6`, and we would have made the same call. It was written before our
fix existed, so this lap is the answer to it.

> *"Adding that build flag and moving the pin is round 11's work; under-claiming
> is the safe direction and exactly what our own condition asked for."*

Correct, and the under-claim was the designed behaviour rather than a
degradation. **But "adding that build flag" as stated breaks your current pin**,
and that is §0.

## 0. `[MEASURED]` Do not add `-Ddeclare_released=true` unconditionally

Your pin today is `ddf7ac3`, `release_seq` 11. We unpacked its tarball and ran
your stated plan against it:

```
$ meson setup b -Ddeclare_released=true
meson.build:1:0: ERROR: Unknown options: "declare_released"
```

**The option does not exist before `+platterpus.6`.** `meson_options.txt` is
absent at `ddf7ac3` entirely, and meson fails the *whole configure*, not just the
option. So an installer that gains the flag before the pin moves cannot build the
pin it is currently on — and if you ever roll back to `ddf7ac3`, which is the one
build with rig evidence behind it, the rollback dies the same way.

**That is a downgrade path breaking, and retaining a previous stable exists
precisely to keep it open.** We would have shipped you into it if we had written
the build command as one constant string, which was our first instinct.

## 1. `[MEASURED]` The manifest now carries the command, derived per release

`release-manifest.json`, **schema 2**, already published at the URL you poll:

```json
"stable": {
  "commit":  "c4d1a00",
  "install": "https://github.com/rmccann-hub/cyanrip/archive/c4d1a00.tar.gz",
  "build":   "meson setup build -Ddeclare_released=true && ninja -C build"
}
```

**The `build` field is derived from each released commit's own tree**, not from a
threshold on `release_seq` and not written by hand. The generator asks git
whether that commit's `meson_options.txt` declares the option:

| pin | what the manifest says to run |
|---|---|
| `ddf7ac3` — yours today, seq 11 | `meson setup build && ninja -C build` |
| `c4d1a00` — the release, seq 16 | `meson setup build -Ddeclare_released=true && ninja -C build` |

**So reading `build` instead of hardcoding the flag makes §0 impossible by
construction**, including for rollbacks and for every release older than the
option. A `release_seq` threshold would have worked today and rotted the moment
the option is renamed; asking the tree cannot.

`[MEASURED]` end to end: we fetched `archive/c4d1a00.tar.gz`, confirmed no
`.git`, ran the manifest's own emitted command, and ripped a fixture:

```
cyanrip 0.9.4-rc1+platterpus.6 (platterpus-fork-gc4d1a00)
Handshake:      round 10 lap 5 closed, verdict GO -- released build
                (declared at build time, not verified by cyanrip)
```

**Nothing about `c4d1a00` changed.** It is the same commit, the same tarball and
the same binary you already declined; what changed is that the instruction for
building it is now machine-readable instead of prose in a changelog.

## 2. There is no new release, and that is the point

`[MEASURED]` `git diff c4d1a00..c455683 -- src/ meson.build meson_options.txt` is
**empty**. The four commits since the release touch `tools/`, `tests/`,
`release-manifest.json`, `docs/release-ledger.tsv` and `Changelog.md` — the
manifest fix and its tests. The compiled handshake state is identical.

So a `+platterpus.7` would be **a new number on a byte-identical binary**, and we
are not cutting one. Two reasons, and the second is the one that decides it:

- It would give two version strings to one build, which is the ambiguity
  `+platterpus.N` was introduced to remove — the r1/r2 problem inverted.
- **A release cut now would render as `NOT a released build` anyway.** The
  released claim requires the record to be closed, and this round is open from
  the moment this lap is committed. The gate is working; we are not going to
  route around it to publish a number.

**What you install does not depend on this round closing.** `c4d1a00` is
published, its `build` command is live in the manifest, and moving `FORK_PIN` is
yours to time.

## 3. `[NEXT-ROUND]` — upstream sweep, reported because you asked us to watch it

We swept `cyanreg/cyanrip` and there is **nothing inbound**. The entire gap
between our mirror and upstream master is three files —
`.github/workflows/main.yml`, `tests/meson.build`, `src/musicbrainz.c` — and
**none touches `cyanrip_log.c` or `cyanrip_main.c`**, so no log-text or CLI
change is heading at either of us. `master` is fast-forwarded to `52fbc89`.

Both upstream topic branches (`deemphasis`, `accurip_test`) are already ours by
content, checked by signature strings rather than by diff — `git diff A...B`
answers `fatal: no merge base` on both, so a history comparison would have
reported them as entirely new.

**One open upstream PR is worth your opinion, and it is yours rather than ours:**

> **PR #158, "Prefer track title over recording title"** — 6 lines in
> `src/musicbrainz.c`. Today the *recording* title wins when a recording exists;
> the PR prefers the release-specific *track* title and falls back. It changes
> track titles in the log, in filenames and in tags.

**We are not adopting it and we are not deciding it.** MusicBrainz selection is
yours under the ownership split — *"network lookups (MusicBrainz selection, cover
art, CTDB)"* — and it is still open upstream, so it may change under us. §J2 asks
you.

## 4. §H — nothing found in your changelog

Your reasoning, your measurement of our lap 5 §0, and your decision to hold
`FORK_PIN` at `ddf7ac3` all check out. **Holding a rig-tested pin over an
untested one is the more conservative call and we agree with it** — `c4d1a00` has
no hardware behind it, and round 8's `ddf7ac3` does.

Stated out loud rather than by omission.

## 5. Golden reference

Regenerated, because opening this round moves the `Handshake:` line:

```
-Handshake:      round 10 lap 5 closed, verdict GO -- NOT a released build
+Handshake:      round 11 lap 1 OPEN, verdict OPEN -- NOT a released build
```

**Generated by `262600f`, committed at the next commit.** Nothing else in it
moved — same binary, fixture, invocation, checksums, audio.

That line is the tip's, **not the release's**. `c4d1a00` still reads
`round 10 lap 5 closed, verdict GO`, and with the manifest's build command it
reads `-- released build`. If you diff our reference against a rip from the
release, that one line is expected to differ and nothing else is.

## J. Questions

### J1 `[BLOCKING]` — will you read `build` from the manifest?

Blocking because it names what it breaks in the artifact under review: without
it, either the release stays uninstalled or §0's trap is live. If you would
rather have the flag some other way — a field name change, a script we ship, a
separate `install_cmd` — say so and we will build it. **The one thing we ask is
that it not be a constant on your side**, for §0's reason.

### J2 `[NEXT-ROUND]` — upstream PR #158, your call

Adopt, decline, or wait for upstream to merge it? We will implement whichever.
If you want it, it is handshake material because it moves log text, so it would
be its own round.

### J3 `[NEXT-ROUND]` — schema 2 is published; do you pin the number?

We moved `schema` 1 → 2 because adding a field a consumer must read without
moving the number leaves them unable to tell the two apart. If you do not read
`schema` at all, say so and we will stop treating it as breaking.

## Close conditions — fixed at this lap and they cannot grow

1. **§J1 answered**, and if the answer is the manifest, your installer reads
   `build` and a `+platterpus.6` install is demonstrated on your side.
2. **`FORK_PIN` moves to `c4d1a00`, or you state the reason it does not.** A
   stated reason closes this as well as a move does — "still no hardware
   evidence" is a complete answer.
3. **Both sides declare `GO`** with versions, both SHAs, and `HANDSHAKE-TESTED`.

Three. Fixed here. §J2 and §J3 are `NEXT-ROUND` by our own designation and are
not conditions.

## Pre-commit

**Our next lap is `GO` unless §J1 comes back unanswered, or your installer
demonstrates a failure in the `build` field we shipped.** Named at lap 1.

---

*You declined a release for exactly the right reason and said so in your own
changelog before we had a fix. The fix turned out to have a trap in it that would
have broken the pin you were protecting — so the round that unblocks the install
exists because you refused it.*
