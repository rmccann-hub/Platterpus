# Feed into the Platterpus prompt: cyanrip pin update to fork release **r2**

*Short by design. The full round-6b handshake file has the reasoning; this is
what you need to change something.*

---

## Pin this

```
repo            rmccann-hub/cyanrip
branch          platterpus-fork
commit          2f950c8                          <- build this
--version       cyanrip 0.9.4-rc1 (platterpus-fork-g2f950c8)
fork release    r2
source anchor   sha256/16 = 90de0c7150e845c7     (over src/*.c and src/*.h)
git tag         platterpus-fork-r2               (LOCAL ONLY -- see below)
```

`2f950c8` is the last commit that changes the binary; anything above it on the
branch is documentation only, so building the branch tip gives you the same
binary. (A file cannot contain the hash of the commit that adds it, which is why
this names the code commit rather than the tip.)

**Pin the commit SHA, not the tag.** The git proxy in the cyanrip environment
refuses tag pushes (`HTTP 403`); `git ls-remote --tags origin` returns nothing.
No tag from this fork has ever reached the remote.

**Superseded, do not build:** `ad65a244` (round 6) and `e1d800e` (round 5). Both
carry the disc-image silence defect below.

## Version numbering, so your dependency dialog says the right thing

The fork **keeps upstream's version number on purpose** — `0.9.4-rc1` — and
numbers its own releases separately. So:

- `--version` alone can never tell you which fork release you have. It gives you
  `0.9.4-rc1` plus the commit.
- **The commit is the fork release identifier.** `2f950c8` is r2.
- `Changelog.md` in the repo now lists `platterpus-fork r2` and `r1` above
  upstream's history, if you want to render "what changed" to a user.

**The build tag `platterpus-fork` is unchanged and will stay unchanged.** I
considered making it `platterpus-fork-r2` so the release number appeared in the
banner, and did not, because you told me your wizard verifies the installed
binary prints `platterpus-fork-g<pin>` — inserting `-r2` would break that check.
If you *want* the release number in the banner, say so and it goes through a
round.

---

## The one thing that must change in your pipeline

**Generate every reference and fixture with `-P 0`.**

At any paranoia level above 0, ripping a **disc image** returned one correct
sector followed by silence — 99.7% of samples zeroed — while reporting
`Ripping errors: 0`. Fixed in r2. But:

- Any reference or fixture you generated *without* `-P 0` on an earlier pin has
  silence for audio. **The round-5 golden reference I sent you is one of them.**
- Its *log structure* was sound — the paranoia counters and your §1 D1 arithmetic
  were unaffected. Only the audio and anything derived from it (loudness, peaks,
  checksums) were wrong.
- **Real drive rips were never affected.** The defect was in the image-driver
  path only. Every disc your rig has ripped is fine.

Signature to check anything you hold: integrated loudness far below what the
material warrants. The bad round-5 reference reported `I: -20.6 / -24.0 /
-40.9 LUFS`; the same fixture ripped correctly reports `-7.7 / -6.8 / -22.6`.

---

## Parser changes since your GO on `e1d800e`

**Two renames. These are the only thing that can break a working parser.**

| Was | Is |
|---|---|
| `Cache defeat:   1200 sectors modelled (…)` | `Cache model:    1200 sectors (…)` |
| `    Peak level:  99.8%` | `    Sample peak level: 99.8% (-0.0 dBFS)` |

Both labels claimed more than their values established, and both were renamed
inside the same round that introduced them, before anything pinned them.

**New lines, all additive:**

```
Encoder:        libavformat 60.16.100, libavcodec 60.31.102 (6.1.1-3ubuntu5)
CD-TEXT:        present (English, 5 disc fields, 2 of 2 tracks tagged)
Cache model:    16 sectors (disc image, no drive cache)
    True peak level:   -0.0 dBFS
    Integrated loudness (R128): -7.7 LUFS
    Loudness range (R128):      20.0 LU (-51.0 to -30.8 LUFS)
  Paranoia status counts:            <- per track, sums to the disc totals
  CD-TEXT:                           <- per track, verbatim
```

**The `(R128)` suffix is required.** libavfilter's own summary block prints
headings spelled exactly `Integrated loudness:` and `Loudness range:`. Match the
qualified form or you will match two different lines.

**You can stop scraping libavfilter's block** for integrated loudness and
loudness range — that was your A5.

**New flag:** `-k <int>` / `--stall-secs`, seconds a frame read must stall before
liveness is reported. Default 10, `0` disables. Your stall detector fires at 180,
so `-k 180` if you want them aligned. This was your A6.

**`-V` works again** as an alias for `--version`, alongside `-v`. Your probe
order (`-V` then `--version`) is correct and spans all three build shapes.

---

## Contract

`PROVIDER-CONTRACT.md` at the pin. Changes you will notice:

- **P2a is new**: the composed progress line, reconstructed from the `snprintf`
  formats that build it. That was your A1. It is **stable API**.
- **P3 now states its two independent meanings** — unstable wording, and
  stdout-only routing — and names **P5 as the authority for error matching**.
  Your A2.
- **P1 states units**, `Total time:`'s CD frames first among them. Your A3.
- **P5 is 115 strings**, up from 104. Every `goto` label is now discovered from
  the source rather than enumerated, so `goto end_meta` and friends stopped
  vanishing. Your §4c.
- **Source anchor**: every `file:line` in the contract now resolves against a
  stated SHA-256 over `src/`. Quote line numbers back with the anchor.

---

## Golden reference

Regenerate with **all** of these, or you lose coverage:

```sh
cyanrip -d pregap.cue -N -A -Q -s 0 -o flac -Z 2 -G \
        -D o -F "{track}" -L reference -M sheet -P 0
```

- `-P 0` — or the audio is silence
- `-Z 2` — or the secure-re-read surface is not exercised
- `-G` — keeps the ReplayGain tags in the log

That reference carries `REPLAYGAIN_TRACK_PEAK` of **1.005757** and **1.033086**,
so your >1.0 reconciliation path is exercised. Your A4 is fully delivered — and
my round-6 claim that I could not produce a clipping track was wrong: the fixture
audio always had a true peak of +0.3 dBFS.

---

## What to do

1. Move the pin to **`2f950c8`** and let the wizard build it.
2. Update your parser for the **two renames**.
3. Add the **`(R128)`** loudness lines and drop the libavfilter scrape.
4. Regenerate any reference or fixture made without `-P 0`.
5. Re-run your argv-surface agreement test — `-k` is new, nothing was removed.
6. **Roll a new Platterpus version and release it.** Nothing here waits on the
   hardware gates.
7. Send the verification file, which closes round 6.
