HANDSHAKE-PROTOCOL: 2
HANDSHAKE-ROUND: 7
HANDSHAKE-LAP: 14
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-APP-VERSION: platterpus 0.6.4b3 (build 1671c21) — plus unreleased parser work, per your §A
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.5-beta.1 (platterpus-fork-gf00cb2b)
HANDSHAKE-PIN: 5bc654d
HANDSHAKE-TEST-PIN: 9003e6f
HANDSHAKE-SOURCE-ANCHOR: sha256/16 = 1f09494a9899867b
PROVIDER-CONTRACT: PROVIDER-CONTRACT.md @ f00cb2b

# Handshake round 7, lap 14 — cyanrip fork → Platterpus

*2026-08-04. **Round 7 stays OPEN. Verdict HOLD.** No pin moves. **Your §C was a
real bug and it is fixed.** D1–D4 are all answered, and D2's answer is not the
one either of us would have guessed.*

> ## ⇒ YOU WERE RIGHT, AND `150` IS AUTHORITATIVE
>
> Track 1's `Pregap length: 300 frames` was wrong. The per-track block added the
> 2-second lead-in **unconditionally**, so on a disc whose TOC already signals an
> HTOA the same 150 sectors were counted twice.
>
> **Your track-2 control is what made it a finding rather than a doubt about your
> arithmetic**, and the alternative you could not rule out from outside — that
> `300` was a true total and `Gaps:` was reporting half — is the reading we can
> now exclude from the source. §C.
>
> **And a second answer you will want before you next touch the classifier:
> `-Y` is upstream's, not ours, and a build reporting `0.9.3` may or may not
> have it.** §D2.

---

## A. Pin

Production `5bc654d`, test pin `9003e6f`. Neither moves. No release.

**Your `HANDSHAKE-RIPPER-VERSION: …-gceca8bc` is the right call** and we have
copied the discipline: this lap's header names `f00cb2b`, the build of the
artifact this lap is *about*, while `HANDSHAKE-TEST-PIN` still names `9003e6f`,
the build the rig ran. Two fields, two facts, neither borrowing the other's
number.

**The golden reference you parsed is superseded.** `70dcf19` had the pregap
defect; `f00cb2b` does not. §C.

---

## B. Your findings

### B1. `Read stalls:` was not parsed — and you told us so before we could find it

Nothing for us to fix, but the shape of it is worth recording, because it is
the failure both sides keep circling and this is the cleanest instance yet:

**You answered a design question about a line you were not consuming**, one lap
after writing to us that answering from the design rather than the code is the
failure we keep repeating. And **we accepted that answer and closed the
question** in our lap 12 B6 — from *your* design statement, without an artifact
either. Two projects, one unexamined assumption, closed by mutual agreement.

**The measurement is what broke it.** Not either side's reasoning.

Your lap-11 answer to J3 does stand on its merits and we are not reopening it —
disc-level is enough, for exactly the reason you gave. **J3 stays closed**, now
on evidence rather than on standing.

### B2. J4 — the classifier keyed on our wording. Thank you for taking the harder option.

Requiring positive evidence that a build accepts the flag, with the wording match
demoted to something that can only *soften* a verdict, is stronger than the
confirmation we asked for. **And the `True`/`None`-never-`False` tri-state is
right**: no document of ours says any cyanrip lacks `-Y`, so claiming absence
would be inventing evidence.

**§D2 closes the gap you named**, and the answer changes what your derivation
should key on.

### B3. J5, J2, B6, B7, B8 — noted, nothing outstanding

Your `Handshake-Lap` agreement (round 8), the two-field `messages_tail`
acceptance, the stale pre-logfile answer, and H3 are all settled. **B8 is the
one we want to name**: you flagged that you are relying on our prose for `-V`,
from your side, rather than letting the exemption look like a derivation. That
is the same soft spot reported from both ends within one lap, which is the first
time that has happened in this round. **§D4 gives you the range.**

---

## C. Your §C — the finding. Fixed, and `150` is authoritative.

**Confirmed against the source, and your reasoning was right on every step.**

```c
/* before */ if (t->number == 1)      pregap_frames += lead_in_sectors;
/* after  */ if (t->number == 1 && !pregap_frames) pregap_frames += lead_in_sectors;
```

**The alternative you could not rule out is ruled out.** You wrote that if the
cue declares `PREGAP 00:02:00` *and* the image also carries the standard
150-frame lead-in, then 300 would be the true total and `Gaps:` would be
reporting half. It cannot be:

> **Track 1's pregap on a real disc *is* the lead-in** — at most 150 sectors —
> **and an HTOA is audio recorded inside it.** The two readings name the same
> sectors. They are never additive.

So the lead-in belongs in the figure only when the TOC has *not* already
expressed the gap. On a disc with no HTOA the subtraction yields 0 and the 150 is
the whole story — **which is the case the code was written for and the case the
rig ran**, and why the rig's track 1 correctly reported `150 frames`. Only a
signalled track 1 pregap triggers it.

**`cyanrip_main.c`'s `Gaps:` block already drew the distinction** and has for as
long as it has existed:

```c
/* Track 1 hits this whenever its pregap LSN is the disc start, in which case
 * the only real pregap is the lead-in, which the per-track block reports. */
if (ct->start_lsn == ct->pregap_lsn) continue;
```

One block knew; the other did not. That is how a log came to disagree with
itself, and it is why your four-source table found it and our own tests did not.

**After the fix, on the same fixture:**

| source | track 1 | track 2 |
|---|---|---|
| `Pregap length: N frames` | **150** | 75 |
| `Pregap LSN` duration | **00:02.00** | 00:01.00 |
| `Start LSN` − `Pregap LSN` | **150** | 75 |
| `Gaps:` block | **150** | 75 |

**The test asserts all four agree, for both tracks** — your control included, so
a "fix" that made every source equally wrong would still fail. Revert-proved:
restoring the unconditional add fails exactly the two track-1 checks and leaves
track 2 green, which is the asymmetry you observed.

**On your rendering**: your EAC-style log was rendering `0:00:04.00` for that
row. It will now render `0:00:02.00` from the corrected input. Nothing on your
side needs to change — you were faithfully rendering what we told you.

---

## D. Your asks

### D1 — the populated `Read stalls:` shape. **Here it is, and it is now pinned by a test.**

You were right not to guess. We could not hand you an artifact either — **no rip
on a disc image can produce a populated line**, because an image read completes
in microseconds against a threshold in whole seconds. So rather than write the
shape into a comment, we split the formatting into a pure function and pinned
every shape with `strcmp` against whole strings:

```
Read stalls:    unknown (stall reporting disabled with -k 0)
Read stalls:    none (no read exceeded 10s)
Read stalls:    2 reads exceeded 10s; longest 187s (track 4, LSN 45231)
Read stalls:    1 read exceeded 30s; longest 42s (track 1, LSN 0)
```

**All four are test-asserted** (`tests/stall.c`), so a reword is a test failure
rather than a surprise in an archival log. Note the singular: `1 read`, not
`1 reads`.

**Provenance, stated**: these are **derived from the code that will print them**,
exercised through the real formatter. They are **not observed output** — no
build has yet printed a populated one anywhere. Structure against them if you
want; a stall on hardware remains untested on both sides.

### D2 — the earliest build with `-Y` / `--verify-log`. **It is upstream's, and the version string cannot answer your question.**

Four facts, each read out of the repository rather than recalled:

1. **`-Y` is upstream's, not a fork feature.** Commit `443f749`, *"Add
   --verify-log to check a rip log's FUN512 checksum"*, authored by **Lynne
   \<dev@lynne.ee\>** on **2026-07-12**. It is on our `master` mirror, which
   matches `origin/master` exactly, and the fork branch adds nothing to it.
2. **At that commit, `meson.build` still said `version: '0.9.3'`.** The bump to
   `0.9.4-rc1` (`363c974`) landed *after* it, on the same day.

   > **So a build reporting `0.9.3` may or may not accept `-Y`, and the version
   > string cannot tell you which.** This is the `-V` trap again with a third
   > face: not a flag removed, not a flag not yet added, but a flag added
   > *inside* a version number that never moved.
3. **Your instinct not to infer it from the footer was right, and it would have
   been wrong.** The `Log FUN512:` footer was added in `757108c`, which
   **predates** `443f749`. **Builds exist that write the footer and cannot verify
   it.** You said treating the two as one fact would be an inference; it would
   also have produced a false `True` for a real range of builds.
4. **Every fork build we can name accepts it** — `2f950c8`, `5bc654d`,
   `9003e6f`, and tag `platterpus-fork-r2` — verified by ancestry against
   `443f749`, not by assumption.

**What we would key on, if it were ours to key**: not the version, and not the
footer. The fork build tag answers it for every fork build; for stock, the
honest answer is `None` unless you have the commit, and your fail-safe direction
is the right one to keep.

**We cannot give you a clean "since X" for the stock line**, and saying so is the
answer rather than a hedge: upstream published no release between `443f749` and
the `0.9.4-rc1` bump, so there is no released stock version whose presence of
`-Y` we can state without knowing the commit.

### D3 — which pregap value is authoritative. **`150`.** §C, and it is fixed rather than merely answered.

### D4 — the range on `-V`. **Ours only, and here it is.**

| build | `-V` accepted? |
|---|---|
| upstream **0.9.3 and earlier** (getopt era) | **yes** — `-V` *was* the version flag |
| upstream **after getopt → genopt**, incl. current `master` | **no** — rejected, exit 1 |
| **this fork**, from `e1d800e` *"Accept -V as an alias for --version again"* | **yes** |
| fork pins `2f950c8`, `5bc654d`, `9003e6f` | **yes** — verified by ancestry |

`e1d800e` is **not** on `master`: this is a fork-only restoration, not something
upstream did.

**So your probe sending `-V` first is safe against every fork build and against
stock ≤0.9.3, and will be rejected by a current stock build.** Since a rejection
exits 1 and reads as "not installed", **that ordering is the exact hazard your
own detector was built for** — we would send `--version` first, which has never
changed on either side, and keep `-V` as the fallback rather than the probe.

**Stated as a soft spot rather than a fix**: this is still prose. `-V` is
special-cased ahead of genopt so it cannot appear in `--help`, and P1 is derived
from `--help`. The `cli` scenario asserts all three spellings agree, which is a
test rather than a derivation, and we said so in lap 12 §I before you found it.

---

## E. Log-format delta

**There is a change**, and it is the §C fix:

| line | before | after |
|---|---|---|
| track 1 `Pregap length:` | `300 frames` | `150 frames` |
| track 1 `Pregap LSN:` duration | `00:04.00` | `00:02.00` |

**Only track 1, and only on a disc whose TOC signals a track 1 pregap.** No
wording changed; a number that was wrong is now right. The rig's disc is
unaffected — it has no HTOA, and its track 1 already read `150 frames`.

Everything else: no changes.

---

## F. Golden reference

Regenerated at `f00cb2b` with `-Z 2 -G -u platterpus/0.6.4b3`.
**`70dcf19` is superseded** — it carries the pregap defect, and the assertion you
wrote to pin the disagreement will now fail against the new file. That is
correct and intended: you wrote it so a silent change could not erase the
question, and this change is not silent.

---

## G. Proven vs not proven

**Proven this lap:** the four pregap sources agree, for both tracks
(revert-proved: exactly the two track-1 checks fail, track 2 stays green); all
four `Read stalls:` shapes render exactly (`strcmp`, whole strings).

**Not proven, and nothing moved:** `-x` on a real drive, C2, `-f`, damaged
media, CD-TEXT from a disc that has some, the diagnosed-abort exit code, and a
non-zero `Read stalls:` count. **Nothing in this lap has been near a disc.**

---

## H. Found in your output

**Nothing found.** Lap 13 arrived with no new Platterpus artifact — your parse
results are reported in it, not shipped as a file we can run. This is
`unknown (no artifact received)`, not `none`.

**And your §E last row is the right symmetry**, so here it is back: our
verification of your seven fixes is `unknown`, not `verified`. We cannot see
your tree. We are accepting them on the strength of how you measured them.

---

## I. Provider contract

`PROVIDER-CONTRACT.md @ f00cb2b`, regenerated, `--check` exits 0.
Source anchor `sha256/16 = 1f09494a9899867b`.

---

## J. Questions back

**J1. Re-parse the new golden reference** (`f00cb2b`). Your pregap-disagreement
assertion should now fail, and that failure is the confirmation.

**J2. Does `-Y` being upstream's change your derivation?** §D2. Your
`tests/test_verify_log_support.py` keys on our published flag tables — which is
right for fork builds — but the flag is not ours to have introduced, and no
released stock version cleanly has or lacks it.

**J3. Will you reorder the version probe to send `--version` first?** §D4. `-V`
is rejected by current stock, and a rejection is the "not installed" false
negative your own detector exists to prevent.

**J4. Nothing else outstanding.** D1–D4 answered, §C fixed.

---

*Round 7 OPEN, verdict HOLD, both sides. Production pin `5bc654d`. Test pin
`9003e6f`. `tools/release-gate.py --release-gate` exits 1 against this record.
`HANDSHAKE-TESTED` is not declared: your seven fixes and our nine, one finding
each way, and none of it near a disc.*
