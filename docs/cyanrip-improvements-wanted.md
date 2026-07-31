# cyanrip improvements wanted — the ranked ask list (2026-07-31)

> **What this is.** The maintainer's request, verbatim: *"if we need to improve
> cyanrip, make a file for that and we can start that too."* So this is the
> actionable list of changes we want in **cyanrip itself**
> ([`cyanreg/cyanrip`](https://github.com/cyanreg/cyanrip), LGPL-2.1-or-later,
> actively developed `master`), each with the evidence that it is a real gap and
> what we would have to *write* to close it.
>
> **What it is not.** It does not restate the three documents that already exist,
> which own different questions — read this one *with* them:
>
> | Document | Owns |
> |---|---|
> | [`upstream-pr-roadmap.md`](upstream-pr-roadmap.md) | The **process** — do you need collaborator access (no), who the maintainer is, upstream style/CI/responsiveness, and the ranked *PR* list as of 2026-07-07 |
> | [`cyanrip-soft-fork.md`](cyanrip-soft-fork.md) | The **runbook** — fork/branch layout, re-merge discipline, and the two already-prepared patches |
> | [`scripts/cyanrip/`](../scripts/cyanrip/) | The **execution kit** — the canonical paste-ready issue/PR bodies, the verified patcher, the build script |
> | [`ripper-engine-strategy.md`](ripper-engine-strategy.md) | The **long-horizon options** — fork/combine feasibility, licensing, the §10 per-gap menu |
> | This file | The **ask list** — *what* we want changed in cyanrip, ranked, with first-party evidence and an honest audio-vs-record verdict per item |
>
> **Standing policy (unchanged, and it governs every item here).** PR-first and
> adaptable to cyanreg's call; the soft fork is a staging area, never a goal;
> their C conventions win; one concern per commit and per PR; never paste GPL-3
> Platterpus code into an LGPL-2.1 tree; and the signed EAC log checksum stays
> **permanently** out of scope because emitting it is forgery of another tool's
> provenance (KDD-11/13/24/28).
>
> **Evidence discipline.** Every claim below is marked **read**, **measured**, or
> **unverified**. "Read" means I fetched the actual upstream source this session;
> "measured" means it came out of a committed artifact or a run of our own code;
> "unverified" means I am reasoning and say so. No line numbers are cited,
> because I read files, not line ranges.

---

## 0. The thing to be clear about before anything else

**Not one item in this document changes a byte of ripped audio.** Every one of
them improves the *archival record* — what the log can say about a rip that is
already bit-perfect by the measures we actually trust (per-track EAC CRC32,
AccurateRip v1/v2, CTDB, `-Z N` re-read consensus).

That framing is load-bearing and it is easy to overstate in the other direction,
so it is stated first: if cyanrip merged every ask below tomorrow, the FLACs
would be byte-identical to the ones it produces today. The reference disc
already reaches **14/14 Copy-CRC parity** against the committed real EAC 1.8
baseline (`docs/session-log.md`, fifth hardware run). What is thinner than
EAC's is the *document*, and that is what this list is about.

The one place this could ever have become an audio question is pre-gap
detection (§2.2), and it does not: both EAC and cyanrip append a pre-gap to the
previous track, so the samples land in the same file either way.

---

## 1. Where the asks come from — the labelled-cell census

`src/platterpus/eac_log_export.py` renders our rip into EAC's layout and fills
every row one of three ways: **measured**, **derived**, or **labelled**
`(not reported by the ripper)`. A labelled cell is, by construction, a cyanrip
gap — the exporter refuses to guess.

So the census is not an opinion. Running the real exporter over the committed
real cyanrip 0.9.3 log (`output_reference/cyanrip_flac/cyanrip_flac_police_classics.log`,
14 tracks) produces exactly **44 labelled cells** (**measured**):

| Cells | Row | Which ask |
|---:|---|---|
| 14 | `Peak level (not reported by the ripper)` | §2.1 |
| 14 | `Extraction speed (not reported by the ripper)` | §2.3 |
| 14 | `Track quality (not reported by the ripper)` | §3.1 — **closed, no ask** |
| 1 | `Utilize accurate stream : (not reported by the ripper)` | §3.2 — **closed, no ask** |
| 1 | `Defeat audio cache      : (unknown)` | §2.6 — low |

Two further gaps do **not** appear as labelled cells and are still real, which
is why the census alone is not the whole list:

- **Pre-gaps** (§2.2) — EAC's `Pre-gap length` row is *absent* rather than
  labelled, because EAC itself omits it for a track with no pre-gap. cyanrip
  measures "none" for all 14 tracks, so our export prints the row zero times
  where EAC's prints it ten. An absent row carries no claim, so nothing is
  labelled — and the shortfall is invisible in the census.
- **`Make use of C2 pointers`** (§2.5) — filled as `No` *on this drive only*,
  because the BDR-209D reports C2 unsupported. A C2-capable drive puts this row
  back into the labelled set.

And two rows that a reader might expect here are already filled from cyanrip's
own output and need nothing: `Read mode : Secure` (from `Paranoia level: max`)
and `Fill up missing offset samples with silence : Yes` (from
`Overread mode: fill with silence in lead-in/lead-out`).

---

## 2. The asks

Each block reads: **Gap → Evidence → Affects → The upstream change → Effort →
Route → Platterpus side.**

### 2.1 ⭐ Print the sample peak — the field already exists and is dead

**Gap.** EAC's `Peak level` row is the **sample** peak (the largest absolute
sample value, as a percentage of full scale). cyanrip reports only the **true**
(4×-oversampled) peak, which is a different quantity and can legitimately exceed
100 %. So the row cannot be filled, and filling it from the true peak would put a
number in EAC's row that does not mean what EAC's row means.

**Evidence.**

*The two quantities provably differ on the reference disc* (**measured**). Real
EAC 1.8 and real cyanrip 0.9.3, same disc, same drive:

```
EAC        Track  1 →      Peak level 94.2 %
cyanrip    Track 1  →   Peak:        0.3 dBFS
                        REPLAYGAIN_TRACK_PEAK:         1.029445
```

`1.029445` is **102.9 %** of full scale. All fourteen tracks exceed 1.0 (range
`1.008499`–`1.097464`), while EAC's fourteen sample peaks are all ≤ 98.8 %. A
number over 100 % cannot be a sample peak, so this is not a rounding difference
between two estimates of one quantity — they are two quantities.

*cyanrip already carries the field, and it is dead* (**read**, upstream `master`):

- `src/cyanrip_main.h` — `struct cyanrip_track` declares **both**
  `double ebu_sample_peak;` and `double ebu_true_peak;`.
- `src/cyanrip_encode.c` — `cyanrip_finalize_ebur128()` and
  `cyanrip_finalize_encoding()` each read both:
  `av_opt_get_double(filt_ctx, "sample_peak", AV_OPT_SEARCH_CHILDREN, &t->ebu_sample_peak);`
- `src/cyanrip_encode.c` — but `init_filtering()` builds the filter as
  `"ebur128=peak=true,anullsink"`, i.e. it asks for the true peak **only**.
- FFmpeg `libavfilter/f_ebur128.c` (**read**) — `sample_peak` is assigned only
  inside `if (ebur128->peak_mode & PEAK_MODE_SAMPLES_PEAKS)`, and the `peak`
  option's `"true"` constant maps to `PEAK_MODE_TRUE_PEAKS` alone.
- `src/cyanrip_main.c` (**read**, partial view) — `crip_replaygain_meta_track()`
  sets `REPLAYGAIN_TRACK_PEAK` from `powf(10, t->ebu_true_peak / 20.0)`;
  `ebu_sample_peak` is referenced nowhere in the fetched view.

So cyanrip reads a value the filter was never asked to compute. **Unverified but
strongly implied:** the filter's private context is zero-initialised, so the read
yields `0.0` — and `0.0` *dBFS* is full scale, which would render as a
plausible-looking `100.0 %`. That is precisely why the filter edit and the print
must land together, and it is worth saying in the upstream issue.

**Affects.** **RECORD only.**

**The upstream change.** Two small edits, one concern:

1. `src/cyanrip_encode.c`, `init_filtering()`: `"ebur128=peak=true,anullsink"` →
   `"ebur128=peak=true+sample,anullsink"`. This is what makes the existing
   `sample_peak` read return a real number.
2. One log line in the per-track loudness block, beside the existing
   `True peak:` / `Peak: … dBFS` pair — e.g. `Sample peak:  -0.5 dBFS`.
   **The exact print site is UNREAD.** It is not in `src/cyanrip_log.c` (I
   inventoried that file's format strings), not in `src/utils.c`, and not in the
   fetched view of `src/cyanrip_encode.c`. The fetches of the large files are
   demonstrably truncated, so absence there is not proof. Its most likely home is
   in or immediately above `cyanrip_log_track_end()` in `src/cyanrip_log.c` —
   whose first format string is `"  Preemphasis:   "`, and the loudness block sits
   directly above that line in real output. **Before patching: grep the tree for
   `dBFS`.** That one grep converts this item from "small" to "trivial".

**Effort.** Very small — a filter-string edit and a printf, once the print site
is located. No new measurement code, no drive interaction, no new dependency.
Extra cost at runtime is a per-sample max over buffers the filter already walks.

**Route.** **Upstream PR** — clean, self-contained, benefits every cyanrip user
(a sample peak is the conventional archival peak and a strictly cheaper number
than the true peak it already computes), and it cannot regress anything, because
the field it activates is currently unused.

**Deliberately NOT bundled.** Whether `REPLAYGAIN_TRACK_PEAK` *should* be the
sample peak — ReplayGain 1.0 defined that tag as the sample peak, and cyanrip
sets it from the true peak — is a **separate** question, is **unverified** here
against the ReplayGain 2.0 spec, and would turn a two-line uncontroversial patch
into a semantics argument that could sink it. File it as its own issue later, if
at all.

**Platterpus side — ✅ DONE (v0.5.19), waiting on the fork.** The reader is
already written and shipped, so a fork that prints this line fills EAC's row with
no further Platterpus change. `parsers/cyanrip_log.py` accepts **two** shapes,
because the upstream print site is unread and cyanrip's own log uses both styles:

```
    Sample peak:  -0.5 dBFS          # inline — the shape this section proposes
    Sample peak:                     # sub-header — how `True peak:` already prints
      Peak:       -0.5 dBFS
```

`TrackResult.peak_level` is populated as a linear fraction (`10 ** (dbfs / 20)`),
which is the unit `_track_block` renders as `peak_level * 100:.1f %`.

Three constraints the fork should know about, because Platterpus enforces them
and will *refuse* a value rather than print a wrong one:

1. **The unit is required.** A bare `Sample peak: 0.942` is refused — dBFS and a
   linear fraction are indistinguishable in that range, and an archival peak read
   in the wrong unit is worse than a labelled gap. Print `dBFS` or `%`.
2. **A value above full scale is refused and logged.** EAC's row is a percentage
   of full scale and cannot exceed 100 %.
3. **The label decides the quantity.** A `True peak:` sub-header actively
   *disarms* sample-peak capture, so the existing true peak can never land in
   EAC's sample-peak row. This matters concretely: all fourteen tracks of the
   reference disc have a true peak *over* full scale (`REPLAYGAIN_TRACK_PEAK`
   1.008499–1.097464, i.e. 100.8 %–109.7 %). Do not rename the existing true peak
   to `Sample peak:` — print a genuinely new value or leave the row labelled.

The export is not missing a parser; it is correctly **refusing** a wrong number.

---

### 2.2 Exact pre-gaps and INDEX 00 — carry PR #115, do not author a rival

**Gap.** EAC runs its own sub-channel gap-detection pass and reports a per-track
`Pre-gap length`. cyanrip reports what the disc's **TOC signalled**, and on the
reference disc the TOC signalled nothing — so cyanrip finds no pre-gaps at all.
The archival record is thinner than EAC's; the audio is not.

**Evidence** (**measured**, both logs committed, same disc, same drive):

```
EAC 1.8      Gap handling  : Appended to previous track
             …and a per-track "Pre-gap length" row on 10 of 14 tracks

cyanrip 0.9.3   Gaps:
                    None signalled
                …and "Pregap LSN:  none" in all 14 per-track Properties blocks
```

Parsing the real cyanrip log through our own parser gives
`pregap_sectors == 0` for all fourteen tracks — a measured "none", not a missing
field — so our export prints the `Pre-gap length` row **zero** times where EAC's
prints it **ten**.

**⚠ Correction to our own record.** Three places in this repo say EAC lists
`Pre-gap length` for **fourteen** tracks
(`docs/eac-tracker-requirements-2026-07.md`, `docs/session-log.md`, and the
`[Unreleased] → Documentation` entry in `CHANGELOG.md`). The real count is
**ten** — tracks 1, 2, 4, 5, 7, 8, 9, 10, 13, 14; tracks **3, 6, 11 and 12 have
no pre-gap row**. The likely origin of the error: the committed baseline file
contains **two concatenated EAC logs** (extractions timestamped 20:01 and 20:02,
each with its own `==== Log checksum … ====`), so a naive count over the whole
file doubles everything — 20 pre-gap lines, 28 peak lines, 28 speed lines. Per
log it is 10 / 14 / 14. See §6.

**Affects.** **RECORD only** — and this one deserves the clearest statement of
the four, because "EAC detects gaps we don't" *sounds* like an audio claim.
cyanrip's documented default is EAC's default: track-1 pre-gap ignored, every
other pre-gap merged into the previous track (upstream README §"Pregap handling",
**read**: *"This is identical to EAC's default behaviour."*). We pass no `-p`.
So both tools put the same samples in the same file; only the *label* differs.

**The upstream change.** **None that we author.** cyanrip **PR #115**
(UltraFuzzy, *"Add pregap detection for physical CDs"*) already does exactly
this: it adds `src/pregap.c` + `pregap.h`, reads Sub-channel Q via MMC — the
thing the TOC cannot give — and wires in with a one-line call-site swap
(`cdio_get_track_pregap_lsn` → `cyanrip_get_track_pregap_lsn`).

Two facts worth having:

- **`master` has no `pregap.c`** (**read**, 2026-07-31: I listed `src/` and it
  contains `accurip.c … version.h` with no `pregap.*`). So #115 is still
  unmerged as of today — consistent with the roadmap's 2026-07-21 re-check.
- **The print site already exists.** `src/cyanrip_log.c`'s `print_offsets()`,
  called from `cyanrip_log_track_end()`, already has both branches (**read**):
  `"    Pregap LSN:  %i (duration: %s)\n"` and `"    Pregap LSN:  none\n"`.
  cyanrip is not missing the *reporting*; it is missing the *detection*. That is
  why #115's one-line swap is sufficient and why there is nothing to add to the
  logging side.

**Effort.** Low as a *contribution* (build it, hardware-test it on the BDR-209D,
post the result, offer fixes against UltraFuzzy's branch), moderate as a
*maintenance commitment* (KDD-32: the `ripping` container builds cyanrip from our
pinned integration branch instead of the 2-year-old COPR tag).

**Route.** **Soft-fork carry + upstream support.** `feat/pregap` tracking #115's
head, folded into the `platterpus` integration branch. Do **not** open a
competing PR (soft-fork §3.1, §5).

**Platterpus side.** Essentially nothing — the `.cue` is consumed verbatim and
`pregap_sectors` is already parsed. **One exception, found while assembling this
(§6.3): our `Pre-gap length` formatting is probably wrong**, and it is latent
only because cyanrip currently reports no pre-gaps. Fix that in the same change
that lands the detection, or the row will appear and disagree with EAC.

---

### 2.3 Per-track extraction speed and elapsed time

**Gap.** EAC prints a per-track `Extraction speed` (a multiple of 1× read speed).
cyanrip prints neither a per-track speed nor a per-track elapsed time, so the row
is unfillable — 14 labelled cells on a 14-track disc.

**Evidence.**

*EAC does report it* (**measured**, first log, one row per track): 1.6 X, 1.8 X,
2.1 X, 2.3 X, 2.1 X, 2.5 X, 2.6 X, 2.4 X, 2.7 X, 2.6 X, 3.1 X, 3.3 X, 3.4 X,
3.5 X — visibly ramping outward across the disc, which is exactly the kind of
detail an archival log is for.

*cyanrip does not* (**read**): I inventoried every format string in
`src/cyanrip_log.c` — the file that writes the log — across
`cyanrip_log_start_report()`, `cyanrip_log_track_end()` and
`cyanrip_log_finish_report()`. There is **no** format string printing an elapsed
time, a wall-clock duration, or a read speed. The only time-like values are the
disc's *audio* length (`"Total time:     %s\n"`), each track's *audio* duration
(`"    Duration:    %s\n"`), and the finish timestamp
(`"Ripping finished at %s\n"`). `struct cyanrip_settings` in
`src/cyanrip_main.h` (**read**) has no elapsed/timing member either.

*And we already know the consequence* (**measured**, `docs/session-log.md`,
2026-06-30): a real `-Z 2` rip of this album took **2 h 45 m** while cyanrip's
own ETA sat at "~35 m", because that ETA is computed from the current read pass
and is blind to secure re-reads. cyanrip tracks *something* time-like at runtime
— it prints a live `progress - X%, ETA - …` line our worker parses — but none of
it is recorded.

**Affects.** **RECORD only.**

**The upstream change.** Stamp a monotonic timestamp at the start and end of each
track's rip and print two things:

1. In the per-track block (`cyanrip_log_track_end()` in `src/cyanrip_log.c`):
   the elapsed wall-clock, and optionally the derived speed
   (`audio duration / elapsed`).
2. In `cyanrip_log_finish_report()`: the whole-rip elapsed, next to the existing
   `"Ripping finished at %s\n"`.

The stamping belongs in the per-track rip loop in `src/cyanrip_main.c`. **That
call site is UNREAD** — grep for the ETA/progress print and for
`cyanrip_rip_track`. **Unverified but likely:** the ETA's existence means a clock
is already read per pass, so this may be plumbing an existing value rather than
adding one. Do not assert that in the issue without reading it.

**Effort.** Small-to-moderate. The printf half is trivial; the honest work is
deciding *what* the interval means (does it include encode? the AccurateRip
lookup? a `-Z` re-read?) and picking the definition that makes the number
comparable to EAC's. Say the definition in the log or the number is noise.

**Route.** **Upstream PR**, and probably the best-received of the new ones: it
touches no drive behaviour, cannot affect correctness, and "how long did this
take" is a question every user of a slow CD ripper has.

**Platterpus side — ✅ DONE (v0.5.19), waiting on the fork.** We already measure
and record whole-rip elapsed ourselves (`rip_timing.py` → the `timing` block in
`.platterpus.json`), so only the per-track row needs cyanrip — and the reader for
it is shipped. `parsers/cyanrip_log.py` reads **both halves** of what §2.3
proposes, from any of several plausible labels:

```
    Extraction speed:  1.6 X        # also: Rip speed / Read speed / Speed
    Elapsed:           00:03:13.180 # also: Elapsed time / Rip time /
    Elapsed:           193.18 s     #       Extraction time / Time taken
```

The speed multiple fills EAC's `Extraction speed` row directly. The elapsed gets
its own field (`extraction_elapsed_seconds`, serialized in the JSON report from
schema v10) and a row of its own, rendered only when measured. Clock forms with
and without hours are both accepted, as is a plain seconds form with a unit.

**We deliberately do not derive one from the other.** If the fork prints only the
elapsed, EAC's speed row stays labelled rather than filled: what the interval
covers (read only? read plus encode? plus the AccurateRip lookup?) is unknown, and
a derived multiple would be a guess wearing EAC's label. If the fork can print
the speed cheaply, print both — the elapsed is the more useful diagnostic and the
speed is the one EAC's format actually asks for.

Indentation matters and is the only thing separating this from an existing row:
cyanrip's *disc* banner already has a column-0 `Speed:` line (the drive's
speed-changeability, which Platterpus reads for the read-speed ladder). The
per-track pattern requires leading whitespace and the disc one forbids it, so
print the per-track row **indented**, inside the track block.

*A workaround exists today, and it is worth knowing about but not shipping
blind.* cyanrip writes a per-track `creation_time` tag into the Metadata block.
On the reference log the deltas between consecutive tracks' `creation_time` come
out consistently at **0.85–0.92 ×** the preceding track's audio duration
(**measured**: e.g. `10:28:21 → 10:31:19` = 178 s against track 1's 193 s) —
i.e. plausible per-track wall-clock at ~1.1–1.2× read speed. **Unverified:**
whether `creation_time` marks the start of the track's rip, the start of its
encode, or the file's creation; resolution is one second; and the interval
includes encoding and the AccurateRip query. So it is a *possible* derivation,
not a measurement, and it would have to be labelled as such (or not printed into
EAC's row at all — the same refusal that keeps the peak row empty). Getting the
number from the ripper is the better answer.

---

### 2.4 Write the `-Z` convergence verdict into the log file — **verify before asking**

**Gap (candidate, unverified).** cyanrip's secure-re-read verdict — the line that
tells us whether a track's reads ever agreed — may be printed to stdout only and
**not** written into cyanrip's own `.log`. If so, a cyanrip log re-parsed from
disk later silently loses the strongest evidence in the whole rip.

**Evidence, and its limits.** This is the one item I could not settle from
committed artifacts, and the reason is itself the finding:

- The verdict we parse is `Done; (2 out of 2 matches for current checksum …)` /
  `Done; (no matches found, but hit repeat limit of 5)`.
- **No committed artifact contains it.** Every occurrence of `Done;` in this
  repository is in a *hand-authored* fixture or a doc
  (`tests/test_parsers_cyanrip_log.py`, `tests/test_rip_worker.py`,
  `docs/*.md`). `output_reference/` has no `-Z` rip log at all — the committed
  reference was ripped without `-Z` (its `EAC CRC32:` lines carry no
  `(after N rips)` suffix).
- `src/cyanrip_log.c` has **no `Done;` format string** (**read**) — so it is
  printed from elsewhere.
- **Circumstantial:** the `\r`-redrawn `progress - X%` lines are definitely
  stdout-only (they appear nowhere in the committed log), so cyanrip clearly has
  a status channel that bypasses the log file. `Done;` is emitted from that same
  region of the rip loop and looks like a member of that family.

That is suggestive and **not** proof. And it is a textbook instance of the trap
this project has hit four times (`docs/testing.md` §5.t): **the only evidence we
have that cyanrip emits this line in a log file is a fixture we wrote
ourselves.**

**Why it matters if true.** `TrackResult.secure_rerip_converged` is what
`eac_log_export._crc_lines` uses to decide between rendering an EAC-style
`Test CRC` / `Copy CRC` pair and rendering a bare `Copy CRC` with a
"re-reads did NOT agree" caveat. The GUI is safe either way because it reads
live worker state — but anything re-reading the saved log (`--compare`,
`parity.compare_logs`, a third-party tool, a human in five years) would see a
converged track as merely single-read, and *under*-claim. Under-claiming is the
safe direction, which is why this has never bitten; it still means the durable
artifact is weaker than the rip it describes.

**Affects.** **RECORD only.**

**The upstream change (if confirmed).** One line: emit the verdict through the
same `cyanrip_log()` path as the per-track block, adjacent to
`"\n  EAC CRC32:     %08X"` / `" (after %i rips)\n"` in `cyanrip_log_track_end()`
— where the rip-pass count already lands. Trivial, and it makes the log
self-contained for exactly the value the log's own `(after N rips)` suffix
implies you should care about.

**Effort.** Trivial to write. The *verification* is the work, and it is one line
of shell on the rig (§5).

**Route.** **Upstream PR** if confirmed; **closed with a note** if the line is
already in the log file.

**Platterpus side — ✅ DONE (v0.5.19), waiting on the fork.** The reader handles
all three states the verdict has, and **indentation is the discriminator**:

```
    Secure re-read:  2 out of 2 matches          # a purpose-written row
    Done;  (2 out of 2 matches for checksum …)   # the existing string, routed
    Done;  (no matches found, but hit repeat limit of 5)
```

An **indented** verdict belongs to the track whose block is currently open. The
existing **column-0** stdout form still buffers for the *next* track, exactly as
today — so today's behaviour is bit-identical and the cheapest possible upstream
change works: route the *existing* string through `cyanrip_log()` so the same text
arrives indented instead of on stdout. No new wording needed.

Two things to know:

- **An unrecognised wording is "no opinion", never a verdict.** It can therefore
  never erase a convergence result Platterpus already measured itself (the GUI's
  own auto-fix history wins over anything the log says).
- **The middle state is the whole point.** cyanrip's health line says
  `No errors occurred` for a track that never read the same way twice, and
  `(after N rips)` does not say whether any two of those reads *agreed*. Please
  make the non-convergent case unambiguous in whatever wording you choose.

---

### 2.5 Say whether C2 was *used*, not only whether the drive supports it

**Gap.** cyanrip's header reports the drive's C2 **capability**. EAC's row asks
whether C2 was **used**. On the reference drive those coincide by luck; on a
C2-capable drive they do not, and the row goes back to unfillable.

**Evidence** (**read**, `src/cyanrip_log.c`, `cyanrip_log_start_report()`):

```c
"C2 errors:      %s by drive\n"
```

The substituted string is the libcdio SCSI capability bit
(`CDIO_DRIVE_CAP_READ_C2_ERRS` — see `ripper-engine-strategy.md` §8). On the
BDR-209D that renders (**measured**, committed log):

```
C2 errors:      unsupported by drive
```

`unsupported` *proves* C2 was not used, so `parsers/cyanrip_log.py` maps it to
`False` and the row correctly reads `Make use of C2 pointers : No`. A
`supported` line would prove only that C2 was *available* — and since
libcdio-paranoia deliberately never consumes C2, the truthful answer on such a
drive is still "not used", but cyanrip's line does not say so and we refuse to
infer it (the test `test_does_not_fabricate_read_mode_or_c2_pointers` exists to
stop exactly that inference, and it has already correctly blocked one attempt).

**Affects.** **RECORD only** — and on the reference rig, *nothing at all*: the
drive reports C2 unsupported, so the row is already filled.

**The upstream change — deliberately the small half, not the big one.** Two
different asks live here and only one is worth making:

- ❌ **Make cyanrip actually use C2.** The capability does not exist below
  cyanrip: libcdio-paranoia ignores C2 by design, and the request to change that
  is libcdio-paranoia issue #3, **open since 2015-05-02 with zero comments**.
  The roadmap already ranks this Order 4 / *skip*. **Nothing here reopens it.**
- ✅ **Make the existing line say what it means.** One printf: distinguish
  "supported by drive, not used by the reader" from a bare "supported", so the
  line answers EAC's question instead of an adjacent one. cyanrip knows both
  halves — the capability bit it already prints, and the fact that its own read
  path never requests C2.

**Effort.** Trivial (one format string plus the words to justify it).

**Route.** **Upstream PR**, low priority. Honest odds assessment: it is a wording
change that is cosmetic to everyone except a tool trying to fill EAC's row, so it
may reasonably be declined. Cheap enough to try alongside something else, and
this is the one item where a soft-fork-only patch would be a defensible outcome
rather than a failure.

**Platterpus side — ✅ DONE (v0.5.19), waiting on the fork.** The branch is
shipped: `supported by drive, not used` (also `unused` / `never used`) maps to a
truthful **No** for EAC's `Make use of C2 pointers`, filling the row on a
C2-capable drive instead of labelling it.

The bare `supported by drive` mapping is deliberately **unchanged** — still
*unknown* — because that line states a drive *capability* while EAC's row asks
what the rip *did*. That distinction is the whole reason the row is honest, and
`tests/test_eac_layout_parity.py` pins it.

There is no affirmative branch, on purpose: libcdio-paranoia never consumes C2
pointers, so a "used" line would contradict the engine. **Do not print one.**

---

### 2.6 A cache-defeat report from the rip itself (low priority)

**Gap.** cyanrip has no cache-defeat flag and emits **no cache line at all**, so
its log alone yields `(unknown)` for EAC's `Defeat audio cache` row. Its engine,
libcdio-paranoia, *attempts* cache defeat every rip (readahead exhaustion, plus
FUA where the drive advertises it), but nothing in cyanrip's output confirms it
happened.

**Evidence** (**measured**): the committed reference log's banner has no
cache-related row, and `parsers/cyanrip_log.py` has no cache pattern to remove —
there is nothing to parse. The exporter therefore renders `(unknown)` rather than
a fabricated `Yes` (KDD-25's rule, which survived KDD-29 intact).

**Affects.** **RECORD only.**

**Status — mostly already solved on our side.** KDD-29 shipped a *measured*
verdict via the standalone `cd-paranoia -A` self-test, hardware-validated on the
BDR-209D 2026-07-26 (fixture `tests/fixtures/cdparanoia_A_bdr209d.txt`). So the
row is filled today when the probe has run.

**The residual value, stated honestly.** A cyanrip-side report would (a) remove a
host-tool dependency and (b) describe *this rip* rather than a separate probe of
the drive. Both are real but small.

**The likely blocker.** This is probably the C2 situation again: the fact lives
*below* cyanrip, in libcdio-paranoia, which exposes no runtime signal for it.
**Unverified** — nobody has read libcdio-paranoia's cache path to check whether
anything is reportable. If it isn't, this becomes a two-repo chain and drops
straight to *skip*.

**Route.** **Ask before coding.** Open an issue asking whether cyanrip would
surface a cache-defeat/FUA status *if* libcdio exposed one, and check libcdio's
side first. Do not write code against this.

---

### 2.7 The two already-prepared asks — pointers, plus one correction

Both are researched, patched and paste-ready; this file does not restate them.
Runbook: [`cyanrip-soft-fork.md`](cyanrip-soft-fork.md) §2 and §3. Paste text:
[`scripts/cyanrip/issue-colon.md`](../scripts/cyanrip/issue-colon.md),
[`scripts/cyanrip/pr-colon.md`](../scripts/cyanrip/pr-colon.md),
[`scripts/cyanrip/issue-encoder-opts.md`](../scripts/cyanrip/issue-encoder-opts.md).

- **⭐ The `-a`/`-t` metadata colon fix** — a confirmed bug; `append_missing_keys()`
  tokenises with `av_strtok(src, ":")` before `av_dict_parse_string()`, so a
  literal `:` in an explicit value is corrupted. The ~4-line guard is verified
  ASan/UBSan-clean by `scripts/cyanrip/verify-meta-colon.c`. It removes our
  largest workaround (the U+2236 substitution + the metaflac restore pass).
  **This remains the highest-readiness contribution of any in this document** —
  it is a *bug fix* with a *proof*, and everything in §2 above is an enhancement.

- **Full libavcodec encoder options.** Confirmed again this session (**read**,
  `src/cyanrip_encode.c`): `setup_out_avctx()` sets
  `avctx->compression_level = cfmt->compression_level;` and
  `cyanrip_init_track_encoding()` calls
  `avcodec_open2(s->out_avctx, out_codec, NULL);` — a `NULL` options dictionary,
  so no encoder option is reachable for any codec.

  **⚠ Correction to the prepared design.** The runbook and the kit propose the
  flag as **`-O key=value`**. **`-O` is already taken** — it is cyanrip's
  overread-lead-in/lead-out flag (**read** in the upstream README this session:
  *"`-O` — Overread lead-in/lead-out areas"*, and independently verified against
  0.9.3.1 + `master` on 2026-07-21 per `docs/dependency-contracts.md`, where it
  is the flag Platterpus itself passes for the Settings "Overread" toggle). The
  proposal as written collides with a shipped flag and would be rejected on
  sight. Pick the letter by reading `master`'s getopt string, and note that
  cyanrip's documented interface is short-flags-only, so a long-only
  `--enc-opt` may not be available either (**unverified** — check whether
  cyanrip has any long-option parsing at all before proposing one). The kit
  README already says to sanity-check the flag name with the maintainer first;
  this is the specific reason why.

- **Structured/machine-readable output (`--json`)** — already recorded as the
  runner-up in `TASKS.md`. Unchanged assessment: valuable to every GUI
  integrating cyanrip, but a *bigger* ask that needs the maintainer's appetite
  gauged first, and it must be *additional* output, never a replacement for the
  human log. Note the tension with §2.1/§2.3: those add two fields to a format
  we already parse robustly, and land regardless of whether a JSON mode ever
  exists. Do the small ones first.

---

## 3. Closed — asks we are **not** making, and why

A list that only grows is less useful than one that also closes items.

### 3.1 `Track quality` — no ask, ever

EAC's `Track quality` percentage is a proprietary metric with no published
definition. Asking cyanrip to emit "a number like EAC's" would mean inventing
EAC's formula and printing the guess into a checksum-attested archival log —
which is the fabrication this whole subsystem exists to prevent. 14 labelled
cells per disc, permanently, and that is the correct outcome.

The nearest *honest* analogue already exists and we already surface it: cyanrip's
`Paranoia status counts:` block (`READ`, `VERIFY`, `FIXUP_ATOM`, `OVERLAP` —
measured: `21920 / 1501 / 58 / 448` on the reference disc) is real error
accounting from the read engine. It is not EAC's number and must never be
rendered into EAC's row.

### 3.2 `Utilize accurate stream` — no ask

EAC's row reflects a per-drive setting about whether the drive returns
positionally-accurate data without jitter. libcdio-paranoia has no equivalent
concept — its entire premise is *coping* with non-accurate-stream drives via
overlap/jitter analysis rather than asking the drive to promise anything. There
is no cyanrip value to print, so the row stays labelled. **Unverified** reasoning
about EAC's exact semantics; the conclusion (nothing for cyanrip to report) is
robust either way.

Tempting and refused: inferring "not accurate stream" from a non-zero
`OVERLAP:` count. That is the same survey-grade inference the C2 test correctly
blocked in §2.5 — a plausible mechanism is not a measurement.

### 3.3 AccurateRip under `-l` (subset rips) — **NOT a gap; confirmed working**

Stating this explicitly, because it was an open worry and it is closed.

cyanrip **does** emit the full per-track `Accurip` block when ripping a subset
with `-l`. Confirmed from the maintainer's own hardware log, 2026-07-30
(`docs/session-log.md`, item D1): their A10 rip was a genuine subset rip
(`Tracks to rip: 3, 4, …, 16`) and the log carried `Accurip:` plus all three
local CRCs per track. **`-l` does not disable the AccurateRip machinery.** No
upstream change wanted, and the dependent Platterpus task took the cheap path.

**One narrow residual, honestly flagged (D1b):** that disc was not in the
AccurateRip database, so what we observed under `-l` was `not found` — a
*positive* confidence value under `-l` has still never been seen. The machinery
demonstrably runs; the happy path is unobserved. That is a one-disc hardware
check (§5), not an upstream ask.

### 3.4 A literal two-pass Test & Copy — no ask

`-Z N` (re-rip until N reads' checksums agree) is a stronger real-world guarantee
than EAC's two fixed passes, it already exists, and KDD-30 already renders its
convergence as an EAC-style Test/Copy pair. A whole-second-pass mode would double
rip time for less assurance. The live question the maintainer raised on 2026-07-30
— *should* `-Z` become the default when AccurateRip has nothing to say about a
disc? — is a **Platterpus defaults decision**, not a cyanrip change.

### 3.5 Tracker-log recognition — no cyanrip ask can fix it

The logcheckers gate on ripper **identity** before reading a single quality line.
No amount of cyanrip log improvement changes that, and forging identity is
refused. Full analysis: `docs/eac-tracker-requirements-2026-07.md`.

---

## 4. Start here — the ranked recommendation

| # | Ask | Affects | Effort | Route | Odds |
|---|---|---|---|---|---|
| **1** | **⭐ §2.1 sample peak** | Record | **Very small** | Upstream PR | **Good** |
| 2 | §2.7 colon fix (already prepared) | Record + our code | Small | Upstream PR | Good |
| 3 | §2.3 per-track speed / elapsed | Record | Small–moderate | Upstream PR | Good |
| 4 | §2.4 `-Z` verdict in the log | Record | Trivial | PR *after* verifying | Good |
| 5 | §2.2 pre-gaps (PR #115) | Record | Low as a contribution | Carry + support | Medium-good |
| 6 | §2.5 C2 "used" vs "supported" | Record | Trivial | Upstream PR | Medium |
| 7 | §2.7 encoder options | Neither | Moderate | Ask first (flag name) | Medium |
| — | §2.6 cache report | Record | Unknown | Ask before coding | Low |

### The single best first contribution: **the sample peak (§2.1)**

Six reasons, in the order that actually decides it:

1. **The evidence is already complete and first-party.** The field
   (`ebu_sample_peak`) exists in cyanrip's own track struct, the read is already
   there on both finalize paths, and FFmpeg's own source explains why it returns
   nothing. Nothing has to be discovered before writing the patch — one `grep
   dBFS` locates the print site and the diff is two edits.
2. **It closes 14 of the 44 labelled cells** — the largest single reduction
   available, and the only one that yields a *number* rather than a Yes/No.
3. **It cannot regress anything.** The field it activates is currently unused, so
   the worst case for an existing user is a slightly cheaper extra peak
   computation and one more log line.
4. **It benefits every cyanrip user, not just us** — which is the acceptance test
   for an upstream PR. A sample peak is the conventional archival peak; cyanrip
   currently computes the more expensive true peak and reports only that.
5. **It is honestly framed as a bug, not a feature request.** "You read a value
   you never asked the filter to compute, and it silently reads as 0 dBFS = full
   scale" is a defect report. That is a materially easier conversation than "please
   add a field", and it comes with the FFmpeg source that proves it.
6. **It is the right size for a first contact.** The roadmap's responsiveness
   gauge says cyanreg merges external work but slowly; a two-line, obviously
   correct, self-justifying patch is the best possible opening move, and it also
   buys the relationship for the larger asks (§2.3, §2.7 encoder options).

**Runner-up, and a defensible alternative first move:** the **colon fix**
(§2.7). It is further along — a verified patch with an ASan/UBSan proof harness
and paste-ready issue text — and it is a genuine bug affecting every user with a
colon in an album title. It is *second* here only because it needs the C build
plus a smoke rip to be honest about, while the sample peak needs one grep. If
the build environment is already warm, do the colon fix first and the sample
peak in the same session.

**What NOT to start with:** anything requiring libcdio-paranoia changes (C2's
read path, the cache signal). Two-repo chains against an upstream that has left
the exact request open since 2015 are not first contributions.

---

## 5. What we would need from the maintainer

Nothing here is code — these are decisions and rig time, in rough priority order.

1. **A go/no-go on opening upstream issues + PRs at all**, and under whose
   GitHub identity. Everything in §4 is a public contribution to someone else's
   project. *(Decision. Blocks all of §2.)*
2. **An environment that can reach `cyanreg/cyanrip`.** This session is scoped to
   `rmccann-hub/platterpus`; it cannot fork, build C, open issues, or run a smoke
   rip. Execution needs a local checkout or a cyanrip-seeded session, plus the
   `ripping` container for the build. *(Environment. Blocks all of §2 —
   already recorded in `cyanrip-soft-fork.md` §0.)*
3. **One `grep -rn 'dBFS' src/` in a cyanrip checkout.** That single command
   converts §2.1 from "small" to "trivial" by naming the print site. *(30
   seconds, no disc, no build.)*
4. **One `-Z 2` rip, then `grep -c 'Done;' "<album>.log"`.** Settles §2.4 either
   way: a non-zero count closes the item, a zero count makes it a one-line PR.
   Please keep that log — we have **no** committed real `-Z` rip log, which is
   why this is unanswerable from here. *(Rig time. Text artifact only —
   Critical rule #8.)*
5. **A decision on the KDD-32 maintenance commitment**, if §2.2 proceeds:
   building cyanrip from a pinned integration-branch commit in the `ripping`
   container instead of the COPR package, and rebuilding on every rebase. This
   is the only item in this document that adds ongoing work. *(Decision.)*
6. **A disc that is in the AccurateRip database, ripped as a subset (`-l`)** —
   closes D1b (§3.3) by observing a *positive* confidence under `-l` rather than
   a `not found`. Any already-verified disc with a couple of tracks deselected
   will do. *(Rig time, small.)*
7. **A C2-reporting drive, if one is ever to hand.** Without one, §2.5's payoff
   is unobservable on this rig — the BDR-209D reports C2 unsupported, so the row
   is already filled. Not worth buying hardware for. *(Opportunistic.)*
8. **A ruling on the three record corrections in §6** — specifically whether to
   fix the "fourteen tracks" count in place across the three documents that carry
   it, since one of them is a released `CHANGELOG` entry. *(Decision, small.)*

---

## 6. Corrections to our own record, found while assembling this

Recorded here rather than silently fixed, because two of the three are in
documents another session may be editing and one is in a `CHANGELOG` entry.

### 6.1 EAC lists `Pre-gap length` for **ten** tracks, not fourteen

Wrong in three places: `docs/eac-tracker-requirements-2026-07.md` (§3 pregap
table and the surrounding prose), `docs/session-log.md` (2026-07-30 entry, *"EAC
lists `Pre-gap length` for fourteen tracks"*), and `CHANGELOG.md`
`[Unreleased] → Documentation` (*"EAC detecting pregaps on fourteen tracks"*).

**Measured:** 10 of 14 — tracks 1, 2, 4, 5, 7, 8, 9, 10, 13, 14. Tracks 3, 6, 11
and 12 carry no `Pre-gap length` row. The cause is almost certainly that
`output_reference/EAC_flac/eac_baseline_police_classics.log` contains **two
concatenated EAC logs** (20:01 and 20:02, each with its own
`==== Log checksum … ====`), so a whole-file count doubles: 20 pre-gap lines, 28
peak lines, 28 speed lines. Per log: 10 / 14 / 14.

**This does not weaken the finding at all** — EAC still detects pre-gaps cyanrip
reports as `none` on every track, and our export still prints the row zero times
against EAC's ten. It changes the number, not the conclusion. But an archival
project that cites a wrong count in three places has a smaller problem than the
one it thinks it has, and the wrongness would surface the first time somebody
re-derived it.

*Worth noting for anyone else reading that baseline:* the file being two logs is
itself undocumented in `output_reference/EAC_flac/README.md` as far as this pass
saw, and it is a trap for any future script that counts rows.

### 6.2 The quoted `REPLAYGAIN_TRACK_PEAK` value does not exist in the repo

The evidence briefing cited a captured peak of **`1.058659`**. That string
appears **nowhere** in this repository. The closest committed value is
**`1.058175`** (track 3, in both the FLAC and MP3 reference logs) — presumably a
different hardware run.

**The claim it was supporting is correct and provable from committed evidence, so
use these numbers instead:** all fourteen tracks exceed 1.0, ranging
`1.008499`–`1.097464`, against EAC's fourteen sample peaks of ≤ 98.8 %. Fourteen
values over full scale is a much stronger argument than one, and every one of
them is in a committed file.

### 6.3 Our `Pre-gap length` formatting is probably wrong (latent)

Found while checking §2.2, and it matters *only* once cyanrip starts reporting
pre-gaps — i.e. it becomes live the moment PR #115 lands, which is exactly when
nobody will be looking for it.

`eac_log_export._pregap_line()` renders the fractional field as **CD frames**
(`sectors % 75`, `0–74`). The committed real EAC 1.8 log's values are **not
frames**:

- `0:00:01.96` has a fractional field of **96**, which is impossible for a
  0–74 frame counter.
- All ten values are consistent with **truncated hundredths of a second**, and
  each maps to a unique integer sector count under that reading (**measured**):
  `2.00`→150, `2.13`→160, `2.10`→158, `1.53`→115, `1.40`→105, `1.13`→85,
  `1.25`→94, `1.96`→147, `1.20`→90, `1.56`→117.
- Under our current frames formatting, those same sector counts would print
  `2.00`, `2.10`, `2.08`, `1.40`, `1.30`, `1.10`, `1.19`, `1.72`, `1.15`, `1.42`
  — **disagreeing with EAC on 9 of the 10.**

**Unverified:** this is inferred from ten values in one EAC version (1.8) on one
disc, not from EAC's documentation or a second log. But the arithmetic is forced
— one value is outside the frame range and every value has an exact hundredths
pre-image — so the current formatting cannot be right for this log at minimum.

**Action:** fix the formatting in the same change that lands pre-gap detection,
with a test pinned against the real committed baseline's ten values (not a
hand-authored fixture — `docs/testing.md` §5.t, and see §2.4 for the same trap
biting a different field). Cheap to do then; invisible and wrong if skipped.

---

## Appendix — what was read this session, and what was not

So the next reader knows which claims to trust without re-checking.

**Read (upstream `master`, fetched 2026-07-31):**

- `src/cyanrip_log.c` — full format-string inventory across
  `cyanrip_log_start_report()`, `cyanrip_log_track_end()` (incl. `print_offsets()`),
  `cyanrip_log_finish_report()`, `cyanrip_log_init()`, `cyanrip_log_end()`.
- `src/cyanrip_encode.c` — `init_filtering()`'s filter description, the
  `av_opt_get_double` peak reads, `setup_out_avctx()`'s `compression_level`,
  `cyanrip_init_track_encoding()`'s `avcodec_open2(…, NULL)`, and the full
  function list.
- `src/cyanrip_main.h` — `struct cyanrip_track` and `struct cyanrip_settings` in
  full.
- `src/cyanrip_main.c` — *partial view only*; `crip_replaygain_meta_track()` /
  `crip_replaygain_meta_album()` confirmed.
- `src/` directory listing — no `pregap.c` / `pregap.h`, so PR #115 is unmerged.
- Upstream `README.md` — the flag list and §"Pregap handling".
- FFmpeg `libavfilter/f_ebur128.c` — the `peak` option table, the `PEAK_MODE_*`
  defines, and the guards on `sample_peak` / `true_peak`.

**NOT read — do not trust a claim about these without checking:**

- The per-track loudness-summary print site (`True peak:` / `Peak: … dBFS`). Not
  in `cyanrip_log.c`, `utils.c`, or the fetched view of `cyanrip_encode.c`. The
  large-file fetches are demonstrably truncated, so this is *unlocated*, not
  absent. **Grep `dBFS`.**
- The `Done;` (`-Z` convergence) print site, and whether it reaches the log file.
- The per-track rip loop's timing/ETA code in `cyanrip_main.c`.
- `master`'s getopt string — needed to pick a free flag letter for encoder
  options, and to confirm whether cyanrip parses long options at all.
- libcdio-paranoia's cache-defeat path — whether anything is reportable at all.
- No claim here rests on a line number; none was read.

**Measured (from committed artifacts and runs of our own code):** the 44-cell
labelled census; the 10/14/14 per-log EAC row counts; the fourteen
`REPLAYGAIN_TRACK_PEAK` values; `pregap_sectors == 0` on all fourteen tracks;
the `creation_time` deltas; the pre-gap hundredths-vs-frames arithmetic; and the
absence of any real `-Z` rip log in the repository.

---

*Companion to [`upstream-pr-roadmap.md`](upstream-pr-roadmap.md) (process + the
2026-07 ranked PR list), [`cyanrip-soft-fork.md`](cyanrip-soft-fork.md)
(runbook + prepared patches), [`scripts/cyanrip/`](../scripts/cyanrip/)
(execution kit), and
[`eac-tracker-requirements-2026-07.md`](eac-tracker-requirements-2026-07.md)
(the external standard these rows are measured against). PR-first, adaptable to
the upstream maintainer's call, and we never fake provenance.*

*Last updated for Platterpus v0.5.19.*
