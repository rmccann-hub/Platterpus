# For the cyanrip thread — round 2: a fresh hardware run, and one contract we now depend on

**From:** Platterpus (`rmccann-hub/Platterpus`), **v0.6.0**, 2026-08-01.
**Supersedes nothing.** The earlier packet (*"hardware evidence Platterpus has and you
don't"*) still stands in full — the EAC-vs-cyanrip pre-gap table, the reference logs, the
hundredths-not-frames unit finding. This adds what a **fresh run on the physical rig** turned
up since, plus **one thing I need from you in writing** rather than as an observation.

Everything here is **measured** on a Pioneer BDR-209D at read offset +667, cyanrip **0.9.3
(release)** — the stock build, not the fork. Where I am reasoning rather than measuring, it
says so.

**No audio, here or ever** (Platterpus critical rule #8). Logs, cue sheets, CRCs, JSON.

---

## 1. ⭐ THE ASK: please pin the unit of `Pregap LSN:` in writing

This is the only item in this document that needs a decision from you rather than a look.

**What we do now.** Platterpus reads your per-track

```
    Pregap LSN:  none
    Start LSN:   14487 (with offset: 14488)
```

and, when `Pregap LSN` is a number, derives the pre-gap **length** as
`Start LSN − Pregap LSN`. That is what we print in the `Pre-gap length` row of our
EAC-layout archival log, converted to hundredths of a second.

**Why this matters more than it looks.** We shipped three releases storing your
`Pregap LSN` value in a field named `pregap_sectors` and rendering it *directly* as a
length. On the reference pressing, track 2's `INDEX 00` sits at LSN 14327 against
`Start LSN 14487` — a 160-sector, **2.13 s** gap, exactly what real EAC 1.8 reports for that
track. Our SHA-256-attested log would have said **3 m 11 s**. An **89× over-claim**, and it
stayed latent for three releases only because this disc's TOC declares no pre-gaps, so the
row never had an input to fire on.

So the field is load-bearing for us, it is easy to misread, and the log does not say which it
is. **Two ways to fix that, either is fine:**

1. **Cheapest:** a one-word label change — `Pregap start LSN:` instead of `Pregap LSN:`.
   Self-documenting, and a parser written against the old label still matches on a prefix.
2. **Best:** print both, as you already do for `Start LSN`:
   ```
       Pregap LSN:  14327 (length: 160 frames)
   ```
   Then no consumer has to derive it, and the derivation cannot drift from yours.

**What I am asking you NOT to do without a heads-up:** change `Pregap LSN` to mean a
*length*. It would be a silently breaking change — same field, same name, same plausible
number, wrong by a factor that scales with position on the disc. If you do want to change it,
please rename the row at the same time so parsers fail loudly instead of quietly.

*(For the record: we now handle both the absolute value and its absence correctly, and the
fix is revert-proven. This ask is about not having to guess next time, not about the bug.)*

---

## 2. New measurement: `Pregap LSN: none` on all 14, from a fresh run

Independent confirmation of the PR #115 case, on a **new rip** rather than the committed
reference artifacts. The maintainer screened the live app log:

```
$ grep -c "Pregap LSN:  none" ~/.local/share/platterpus/log.txt
11
$ grep "Pregap LSN:" ~/.local/share/platterpus/log.txt | grep -v none
(no output)
```

Zero non-`none` lines. Combined with the EAC 1.8 log of **the same disc in the same drive**
reporting `Pre-gap length` on **10 of 14 tracks**, this is now two independent runs saying the
same thing: the TOC read does not see what the sub-channel pass sees. That is the measured
argument for **PR #115**, and it is not a synthetic-image result.

The four tracks EAC also omits (3, 6, 11, 12) are genuinely gapless, so this is not EAC
over-reporting.

---

## 3. New observation: a cancelled rip leaves a **0-byte** `.cue`

**Measured, 2026-08-01.** Rip cancelled cleanly from the GUI after 2 of 14 tracks
(SIGTERM to the cyanrip process group). Both FLAC files landed complete and verified against
AccurateRip at confidence 200/129 and 200/131. The `.log` was written and is well-formed. The
`.cue` was **0 bytes**.

I do not yet know whether that is:

- **(a)** cyanrip opening the cue early and writing its body at the end of the rip — in which
  case a cancel catching it empty is entirely reasonable, and the fix is on *our* side (say so
  in the UI rather than leave a file that looks like damage); or
- **(b)** something being truncated.

**I am not filing this as a bug**, because I have not read the relevant part of your source
and (a) is the likelier explanation. The maintainer is re-testing this round with a
*completed* short rip as the control (our test A27), which will discriminate cleanly.

**If it is (a) and you agree it is worth changing**, the friendliest behaviour for an
interrupted rip would be to write the cue for the tracks that *did* complete, or to remove the
empty file — a 0-byte cue beside two good FLACs reads as corruption to a user and to any
tool scanning the folder. Entirely your call; I will report back either way once we have the
control result.

---

## 4. Confirmed working: GUI-supplied tags round-trip into the log

Minor, but worth stating because it is an integration point that could regress silently.

Platterpus runs cyanrip with `-N` (no metadata lookup) and feeds tags via `-a`/`-t`, so your
interactive prompt never appears and the rip needs no in-container network. On this run the
maintainer deliberately edited track 2's title in our GUI to
`Can't Stand Losing You test`, and it appears verbatim in your log's per-track metadata block:

```
  Metadata:
    track:                         2
    title:                         Can’t Stand Losing You test
    isrc:                          GBAAM0201089
```

So the `-t` path, the tag write, and the log echo all agree. Note the smart apostrophe (U+2019)
survived intact, as did the U+2236 in the album name (`Every Breath You Take∶ The Classics` —
we substitute that for `:` in path segments). No mangling anywhere in the chain.

---

## 5. Fresh reference material, if you want it as fixtures

From the same run, all text, all shareable:

| Artifact | What it is good for |
|---|---|
| cyanrip `.log`, 2-track cancelled | A **partial/interrupted** log — your fixtures are all complete rips |
| `Gaps:\n    None signalled` block | The real multi-line shape of the gaps section on stock 0.9.3 |
| `Accurip: disc found in database (max confidence: 200)` + per-track v1/v2 rows | The "found, matched" state with both versions present |
| Full `Properties:` block | `Duration` / `Samples` / `Frames` / `Pregap LSN` / `Start LSN` / `End LSN` on a real disc |

Ask and the maintainer will attach them. **One convenience worth knowing:** as of Platterpus
v0.6.0 our `.platterpus.json` embeds the verbatim text of the cyanrip `.log` and the `.cue`
inside itself, so a single file carries all of it.

---

## 6. Standing items — unchanged, listed so nothing looks dropped

These are already in `docs/cyanrip-improvements-wanted.md` and the PR roadmap; nothing here
supersedes them. Restated in one line each so this file is a complete picture of the ask:

| Item | Status |
|---|---|
| **PR #115** — `INDEX 00` pre-gap markers in the cue sheet | Best-evidenced ask; §2 above adds a second measurement |
| Per-track extraction **elapsed time** in the log | Fork-only today; `None` on 0.9.3, and we serialize it the day it ships |
| `C2 errors: unsupported by drive` — a **measured** statement, not a config echo | Already correct on 0.9.3; noting it as a thing we depend on |
| The `-Z` `Done;` verdict's **position** in the log | Resolved — we attribute by position now, not indentation. See below. |

### The one thing I got wrong and you caught

Worth repeating in this file because it changed how I write specs for you.

v0.5.19's fork spec asked you to **indent** the `-Z` `Done;` verdict, and defined
"indented ⇒ belongs to the currently-open track". The premise was that the line was
stdout-only and absent from the log file. **That was false at 0.9.3 and at master**, as you
proved by reading `cyanrip_log()`. Implementing our ask faithfully shifted every verdict by
one track.

The lesson I took, and will apply to everything above: **a spec that asserts a mechanism must
say what the assertion rests on.** Had it read *"because we believe this line is stdout-only"*,
you would have caught it before writing the commit. Everything in §1 is phrased so you can see
what I am assuming and contradict it.

---

## What I would find most useful back

1. **A yes/no/counter-proposal on §1** — the `Pregap LSN` label or dual print. That is the
   only blocking item.
2. **A one-liner on §3** — whether the cue is written at end-of-rip. Even "yes, at the end"
   closes it; I do not need a change.
3. Anything from §5 you want as a fixture.

Nothing else here needs a reply.

---

*Platterpus v0.6.0 · 2026-08-01 · all measurements re-derived from artifacts while writing.*
