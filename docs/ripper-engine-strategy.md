# Ripper engine strategy — fork / combine / upgrade feasibility (research, living)

> **Status: RESEARCH / OPTIONS — not a commitment.** Long-horizon: revisited
> only *after* the v1 feature set works and hardware parity is proven. This doc
> deliberately **keeps open** the option of forking and/or combining whipper and
> cyanrip and maintaining our own engine — which **revisits [KDD-18](../PLANNING.md)
> ("never fork whipper")**. Nothing here changes current direction; adopting any
> fork/combine path requires an explicit new KDD that amends KDD-18. This file is
> *living* — append findings as the research continues (see §6).

## 0. Why this exists

The maintainer asked (2026-06-23) to not rule out, long-term, forking and/or
combining whipper and cyanrip — fixing, updating, and upgrading them ourselves
to get exactly the behaviour we need — **within what their licenses allow**.

Today we invoke the rippers as **subprocess adapters** (Critical Rule #3, KDD-18),
and the `RipBackend` ABC means the engine is already swappable as a near one-file
change — that's how whipper was replaced by cyanrip. (A `Config.ripper_backend`
selector existed while both shipped; it was removed when cyanrip became the sole
backend, and would return if a second engine did.) So we can keep this option
fully open at
**zero cost** while we finish the GUI: the decision is deferred, not foreclosed.

## 1. The two engines (facts, with sources)

**whipper** — [`whipper-team/whipper`](https://github.com/whipper-team/whipper)
- License: **GNU GPL-3.0** (copyright 2009–2021). Python 3 (3.6+), derived from `morituri`.
- Releases: last tagged release **v0.10.0, 2021-05-17** (KDD-18); the `develop`
  branch still receives commits (~1,600+), but no new *release* in years.
- Architecture: orchestrates `cdparanoia`/`cd-paranoia` (secure read), `cdrdao`
  (gap detection), `flac`, and `libdiscid` as subprocesses; writes an EAC-grade
  YAML rip log (KDD-11).
- Known liabilities we'd inherit on a fork: the **`pkg_resources`/Python-3.14
  setuptools≥81 cliff** (DEPENDENCIES.md), and the **cd-paranoia >587-sample
  read-offset bug** that failed tracks on the Pioneer BDR-209D (+667) (KDD-18).

**cyanrip** — [`cyanreg/cyanrip`](https://github.com/cyanreg/cyanrip)
- License: **LGPL-2.1-or-later** (`LICENSE.md`; confirmed from the 2026-07-07 repo clone — the roadmap doc records the same). C (~99%) + Meson build.
- Releases: latest **tag** v0.9.3.1 (2024-06-05) — but **`master` is actively
  developed**: commits through **2026-03-25** (~25–30 in the trailing year —
  pregap/cue fixes, cdrdao TOC/bin support, metadata-tag fixes, Windows fixes).
  So the accurate picture is **stalled *releases*, live *development*** — the
  distinction that actually decides the fork question (see §6 finding).
- Architecture: read + offset compensation + error recovery via
  **libcdio-paranoia**; encode/mux via **FFmpeg ≥4.0** → 11 formats
  (flac, mp3, opus, aac, wavpack, alac, vorbis, tta, wav, alac/aac/opus-in-mp4,
  pcm). Built-in **AccurateRip v1/v2 + EAC CRC32 + MusicBrainz + ReplayGain**.
  Applies the read offset with its own paranoia (no >587 bug).
- Build deps: FFmpeg (libav*), libcdio-paranoia, libmusicbrainz5, libcurl.

## 2. Licensing — what we may legally do (the gating question, answered)

**Our project is GPL-3.0-only** (KDD-10). Verdict: **licensing is not a blocker
for forking or combining either tool.** The real costs are maintenance and
engineering, not legal.

| Tool | Its license | If we fork/embed into our GPL-3.0 code |
|---|---|---|
| whipper | GPL-3.0-only | Directly compatible — same license; the combined work stays GPL-3.0. ✓ |
| cyanrip | LGPL-2.1 | LGPL-2.1 **explicitly permits relicensing to GPL-2-or-later**, hence GPL-3.0; combining LGPL-2.1 with GPL-3 yields a GPL-3 work. ✓ (LGPL is also the *more permissive* base — more downstream freedom.) |

- **cyanrip's transitive deps:** FFmpeg is LGPL-2.1+ by default (GPL only with
  `--enable-gpl`); **libcdio-paranoia is GPL-3.0-only**; libcdio is mixed
  (GPL-2+/GPL-3+/LGPL-2.1). Because cyanrip already links GPL-3.0
  libcdio-paranoia, a *distributed cyanrip binary is already effectively GPL-3.0*
  — consistent with us.
- **Obligations a fork/embed adds** (today's subprocess model keeps their licenses
  out of our code per KDD-10): ship complete corresponding **source** (we already
  do — public repo), keep it **GPL-3.0**, retain all copyright + license headers,
  **state our modifications**, add **no further restrictions**, never relicense
  proprietary. The clean-room rule (KDD-16) still bars copying anything
  **GPL-2.0-*only*** (one-way-incompatible) into our GPL-3.0 work.

Sources: [GNU license compatibility](https://www.gnu.org/licenses/license-compatibility.en.html),
[GPL FAQ](https://www.gnu.org/licenses/gpl-faq.html),
[LGPL 2.1 §3 relicensing](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html),
[FFmpeg license](https://github.com/FFmpeg/FFmpeg/blob/master/LICENSE.md),
[GNU libcdio](https://www.gnu.org/software/libcdio/).

## 3. The strategic options (menu, with trade-offs)

- **Option 0 — Status quo + upstream contribution (KDD-18 default).** Keep the
  subprocess adapters; when a ripper-level change is needed, contribute it to
  **cyanrip** (active). *Lowest burden; depends on upstream accepting + releasing.*
- **Option 1 — Fork whipper.** *Pros:* Python (our language); EAC-grade log +
  cdrdao gap detection. *Cons:* stalled releases, the `pkg_resources`/Python-3.14
  cliff we'd own, the >587 bug, morituri legacy. **High maintenance.**
- **Option 2 — Fork cyanrip.** *Pros:* active, C/FFmpeg (no Python cliff),
  already does AccurateRip+EAC-CRC+MB+ReplayGain+11 formats, LGPL→GPL3 trivial,
  applies offset without the >587 bug. *Cons:* C (not our primary language);
  Meson/FFmpeg/libcdio build + packaging to own; dep/ABI churn.
- **Option 3 — Combine.** Use **cyanrip as the engine** and port whipper's
  EAC-parity log (and any gap-detection edge) onto it → one GPL-3.0 engine we
  control. *Highest power, highest effort.*
- **Option 4 — Build our own ripper.** Rejected historically (KDD-08/18): the
  forensic read/offset/AccurateRip math is exactly what we delegate to a trusted
  tool. **Keep rejected.**

**Preliminary lean (NOT a decision):** if we ever fork, **cyanrip is the stronger
base** (active, no Python cliff, broad format support, permissive license, no >587
bug) — which also matches KDD-18's contribute-to-cyanrip stance (the "migrate the
adapter to cyanrip if forced" phrasing comes from the 2026-06-02
upstream-modification investigation guardrail that KDD-18 later codified). The
sane escalation ladder: **Option 0 first** (upstream a specific need); escalate to
**Option 2/3** only if upstream can't/won't *and* the maintenance cost is justified.

## 4. Why deferring is free (the architectural safety net)

The `RipBackend` ABC already isolates the engine (KDD-08/18; a `Config`-level
selector would be reintroduced alongside a second backend). A fork would be **a
new adapter implementation + a host-setup install
step** — not a GUI rewrite. So the maintainer's sequencing ("after we make the
rest work") costs nothing: maintaining adapter discipline *is* what keeps the
fork/combine option open.

## 5. Decision gates before adopting any fork/combine

1. v1 feature set complete **and** hardware parity proven (the
   `output_reference/` EAC output-parity matrix passing for whipper **and** cyanrip).
2. A concrete need upstream won't serve, **documented**.
3. Maintenance capacity assessed: who builds/releases the fork; CI for a C/Meson
   (or Python) build; ongoing security updates for FFmpeg/libcdio.
4. An explicit **KDD amending KDD-18**.

## 6. Open research tasks (append findings here as we learn)

- [x] **Gauge cyanrip upstream's activity + PR responsiveness (gates Option 0) — done 2026-07-08.** *Development:* `master` is live (last commit 2026-03-25; ~25–30 commits/yr). *Releases:* stalled — last tag v0.9.3.1 is ~2 yr old. *Responsiveness:* the maintainer **does merge external PRs, but slowly** (contact/cadence facts live in the roadmap's **Process** block — [`upstream-pr-roadmap.md`](upstream-pr-roadmap.md) — the canonical home; PR #115, pregap/HTOA, is open and actively reviewed). **Conclusion — a fork is NOT warranted for "slow releases":** because Platterpus owns the `ripping` Distrobox container, we can build cyanrip **from any git commit** (our own topic branch *before* a merge, or upstream `master` *after*), so cyanrip's release cadence never gates us — the "slow releases → must fork" reasoning dissolves. The real, smaller decision is **build-cyanrip-from-source in the container vs. a distro package** (a maintenance choice, not a fork). Escalate to a **soft fork** (upstream `master` + our small rebased patch set) only if a needed PR is *declined or stalls indefinitely*; a **hard fork / consolidated tree (§7)** stays behind the §5 gates + a KDD-18 amendment. (Upstream conventions/CI: see the roadmap's Process block.) **The soft fork now exists** (decided 2026-07-08): runbook in [`cyanrip-soft-fork.md`](cyanrip-soft-fork.md), execution kit in `scripts/cyanrip/` — two contributions prepared (the `-a`/`-t` colon fix ⭐ and full encoder opts). The "map cyanrip's FFmpeg flag surface" question below was answered **negatively** the same day: cyanrip hardcodes `compression_level` and opens encoders with no options dict — hence the prepared encoder-opts contribution.
- [ ] Inventory exactly what whipper does that cyanrip doesn't (gap-detection
      method, log fields, `.cue`/`.toc` output) — gates Option 3.
- [ ] Map cyanrip's FFmpeg flag surface for what we want (FLAC compression level,
      encode verify, richer tags) — a rich-enough flag surface could make a fork
      unnecessary.
- [ ] Prototype: build cyanrip from source inside our `ripping` container; measure
      the build/packaging burden.
- [ ] Re-verify transitive-dep licenses at the exact versions we'd ship
      (FFmpeg build flags; libcdio components).
- [ ] Re-confirm whipper's Python-3.14 / `pkg_resources` status at decision time.
- [ ] **Run the §7 "mirror + enumerate + triage" spike** (read-only) and attach
      the per-branch manifest below.

## 7. Option 3a — vendor + branch-consolidate both upstreams into one in-house tree

> Maintainer request (2026-06-23): *"branch off and make our own repo of both
> projects; test/verify/merge all the testing branches from those projects into a
> single merged and working branch in ours — I want the most up-to-date single
> project here for these."* This section is the **plan**; it is **not executed**.
> It is the heaviest variant of Options 1–3 (we become the maintainer of a merged
> engine), so it sits behind all the §5 decision gates **plus** a maintenance
> commitment, and adopting it amends KDD-18 via a new KDD.

**Goal.** A single in-house source tree that reflects each tool's *most current
working state* — upstream's released code **plus** the useful work stranded on
their unreleased `develop`/feature/PR branches — merged, building, and test-green.
"Single project here" = we host it; the GUI keeps consuming the built binaries
through the host-setup wizard (the adapter boundary is unchanged).

### 7.1 Repo shape (pick at decision time)
- **(a) Monorepo via `git subtree`** — vendor each upstream under `vendor/whipper`
  and `vendor/cyanrip` *with full history*; local edits live alongside; pull
  upstream with `git subtree pull`. Best fit for "single project here." Recommended.
- **(b) Two in-house forks** (`*-whipper`, `*-cyanrip`), each with a `consolidated`
  branch — better if we intend to send PRs back upstream (Option 0 still in play).
- Either way the GUI repo is unchanged; only the host-setup install source moves
  from distro/COPR packages to our built artifacts.

### 7.2 The consolidation procedure (the actual work)
1. **Mirror** each upstream: `git clone --mirror` → all branches, tags, refs (and
   PR refs via `refs/pull/*` where the host exposes them).
2. **Enumerate + classify** every branch: release/stable, `develop`, feature/test,
   PR, stale. Capture last-commit date, ahead/behind the base, and what it touches.
3. **Triage → keep/reject.** *This is the crux:* "merge everything" can **regress**
   quality — unreleased branches are often experimental, abandoned-for-cause, or
   superseded. Each candidate must earn inclusion (see step 5). Record decisions.
4. **Per-project test harness** so any branch can be verified in isolation:
   whipper → `pytest` + a smoke rip; cyanrip → `meson build && meson test` + a smoke
   rip. "Verify a branch" = builds **and** its tests pass **and** a smoke rip works.
5. **Integration branch `consolidated`,** built like our own refactor (small,
   bisectable, green-at-every-step): start from the most-advanced stable base
   (whipper `develop`, cyanrip `master`), then **merge kept branches one at a time**,
   running the harness after each; reject any branch that can't be made green
   without disproportionate surgery. (Avoid octopus merges — conflicts need
   per-branch resolution.) Document every non-trivial conflict resolution.
6. **Validate the result:** full build + tests + a **real-hardware rip** (the
   standing gate) + the `output_reference/` **EAC parity** matrix. A consolidated
   tree that fails parity is not done.
7. **Provenance manifest:** record exactly which upstream branches/commits landed,
   why, and what was rejected — committed alongside the tree.

### 7.3 Staying current
Re-run a lightweight consolidation when upstream advances: `git subtree pull` (or
re-mirror + re-triage), re-merge our local deltas, re-validate. Budget this as
recurring maintenance, not one-time.

### 7.4 Licensing & attribution (non-negotiable)
The consolidated work is **GPL-3.0** (whipper GPL-3 + cyanrip LGPL-2.1 → GPL-3;
§2). We MUST: retain **all** upstream copyright/license headers + `AUTHORS`/`NOTICE`,
keep cyanrip's LGPL-2.1 notices intact even when combined under GPL-3, **state our
modifications**, ship **complete corresponding source**, add **no further
restrictions**, and never relicense proprietary. The clean-room bar (KDD-16) still
forbids pulling in anything **GPL-2.0-only**. If we redistribute binaries (e.g.
inside the container image or AppImage), honor the GPL source-offer.

### 7.5 Risks (why this is the heavy option)
- **We become the maintainer** of two upstream codebases (security updates for
  FFmpeg/libcdio; the whipper `pkg_resources`/Python-3.14 cliff; build/packaging).
- **Merging unreleased branches can lower quality** vs. a curated upstream release —
  hence the per-branch verify-or-reject gate; expect to reject a lot.
- **Heavy, divergent conflicts** between long-lived branches.
- **Drift from upstream** makes future `subtree pull`s harder the more we edit.

### 7.6 First step when we start (low-cost, read-only spike)
Do **only** steps 7.2-(1→3): mirror both, enumerate, triage, and produce the
**per-branch manifest + a feasibility report** (which branches carry real
unreleased value, rough conflict/maintenance estimate). No merging, no commitment —
it turns "should we consolidate?" into a decision backed by data, and feeds the §6
checklist. Park the manifest in §6.

## 8. C2 error pointers — drive gap or software gap? (research finding, 2026-07-01)

**Symptom.** On the Pioneer BDR-209D, a cyanrip rip log header reads
`C2 errors:      unsupported by drive`.

**What C2 buys.** C2 error pointers are per-sample flags the drive derives from
the CD's CIRC layer, telling the ripper exactly which returned samples it could
not fully correct. A secure ripper can then do one fast pass and re-read *only*
the flagged sectors, instead of reading everything 2–3× and comparing for
consensus. This is why EAC's C2 path runs at "nearly burst mode speed"
([EAC extraction technology][eac]). C2 is a **speed** optimisation at equal
accuracy — not an accuracy feature.

**The finding: it is primarily a software gap, with a hardware caveat.**
- Our whole extraction stack ignores C2. Hydrogenaudio's ripper comparison lists
  the C2 column as **"No"** for cdparanoia, whipper **and** cyanrip; only EAC,
  dBpoweramp and XLD use C2 ([comparison][cmp]). cdparanoia has never used C2 —
  it relies on multi-pass re-reads + jitter/overlap analysis ([cdparanoia][cdp]);
  the cd-paranoia manpage never mentions C2 ([manpage][man]).
- cyanrip's line is a *capability report*, not a failed attempt. It prints the
  libcdio SCSI cap bit verbatim (`src/cyanrip_log.c`):
  `cyanrip_log(..., "C2 errors:      %s by drive\n", (ctx->rcap & CDIO_DRIVE_CAP_READ_C2_ERRS) ? "supported" : "unsupported");`
  ([source][src]). Even if the bit were set, libcdio-paranoia would not consume it.
- Hardware caveat: Pioneer BDR-208/209-class drives appear **not** to advertise
  C2 even under Windows/EAC (reported "C2 Error Pointers: No") ([dBpoweramp][dbp],
  [CdrInfo][cdr]). So for *this* drive the "unsupported" report is plausibly
  accurate — a C2-capable engine likely still couldn't get pointers from it.
  **Hardware-gated:** confirm with a real BDR-209D probe before acting.

**No mature Linux C2 path exists.** libcdio-paranoia (whipper + cyanrip) doesn't;
`cdda2wav`/`icedax` can request C2 but isn't a secure/consensus ripper; dBpoweramp
ships no Linux ripper.

**Options (decision gates).**
- **(a) Do nothing — recommended.** libcdio-paranoia consensus re-reads +
  AccurateRip/CTDB external verification already reach provable bit-perfection.
  C2 would only make it *faster*, not *more correct*. Defensible: our north star
  is correctness, and AccurateRip verifies independently of any drive flag.
- **(d) Expose read speed `-S` — cheap partial mitigation. ✅ SHIPPED (0.4.6).**
  Not C2, but the real speed lever we didn't surface. See §8.1 — this grew from
  "a Settings knob" into the adaptive read-speed **ladder** (the 0.4.6 headline):
  start fast, and only slow down / re-read harder when a disc actually reads with
  errors. Low effort, high payoff — exactly as ranked.
- **(b) Patch/fork libcdio-paranoia (or cyanrip's read loop) to use C2.** Very high
  effort — C2 logic belongs in the conservative GPL-3.0 paranoia core; low upstream
  appetite. **Pointless on the BDR-209D if it exposes no C2.** Hardware-gated.
- **(c) Swap extraction engine for a C2-using one.** No mature Linux candidate
  exists. Not viable.

**Recommendation.** Keep **(a)**; **(d) shipped** (§8.1). Treat **(b)/(c)** as
parked behind a real-hardware confirmation that the drive even exposes C2 —
current evidence says it does not, which by itself defeats them for this rig.
Effort-vs-payoff rank: **(a) > (d) > (b) > (c)**.

### 8.1 The adaptive read-speed ladder (shipped 0.4.6)

Option (d) landed as more than a fixed knob: a **ladder** that behaves like a
careful EAC user with zero terminal. **Quality can only go up.**

- **Default (`read_speed_mode = "auto_ladder"`):** rip at the drive's max speed.
  If a pass completes with unrecoverable read errors (cyanrip's log
  `Ripping errors: N > 0` / a track "with errors"), re-rip the disc a rung slower
  — `max → 8× → 4× → 2×` (`-S`) — and, at the 2× floor, re-read harder with
  `-Z 2` then `-Z 3`. Stop when a pass reads clean or the ladder is exhausted
  (then the disc is **FLAGGED** as unresolved in the report — never silently
  interpolated or papered over). Bounded by a hard `MAX_ATTEMPTS`.
- **Per-track auto-fix (0.4.8):** if a pass reads clean overall but a track's
  secure re-read never *converged* (read instability — distinct from a hard read
  error), re-rip **just that track** (cyanrip's `-l`) with a harder `-Z`, into a
  temp dir. If the re-read now converges, the improved FLAC replaces the original;
  if not, the original is kept and the track is FLAGGED. Cheap (one track, no
  speed change), so it works on a speed-locked drive, and it can never make a
  track worse. This **superseded 0.4.7's "flag, don't re-rip"** for instability
  once `-l` was confirmed (gate 3 below) — the whole-disc-cost objection was gone.
- **Dynamic secure re-rip (shipped 0.4.9 as the default behaviour — no
  checkbox).** When `-Z` is applied to *every* track, every track is read at
  least twice (the dominant cost on a clean disc; a real-user "20 min on
  track 1, an hour on track 2" ETA came straight from this). Dynamic mode instead
  rips pass 1 **fast** (`-Z 0`) and then secure-re-rips (same `-l` per-track path)
  **only the tracks that didn't match AccurateRip** — a DB match on the first read
  is already proof of bit-perfection, so re-reading it is wasted time. A clean disc
  becomes a single fast pass; marginal / not-in-DB tracks still get the full secure
  treatment. **On by default** (a power user forces `-Z` on every track via
  `secure_rerip_dynamic = false` in config.toml); the trigger is recorded per
  track (`retried_tracks[].trigger` = `accuraterip` vs `instability`).
- **Manual override:** Settings → "Fixed speed (advanced)" disables the ladder
  and rips at one chosen `-S` value (0 = drive max).
- **Honest reporting:** each pass's speed + `-Z` + clean/not lands in
  `.platterpus.json` under `read_speed` (the single per-album debug artifact),
  along with `retried_tracks` (the per-track auto-fix history) and
  `unstable_tracks` (tracks the auto-fix could not rescue — still flagged).
- **Where:** the pure decision logic is `src/platterpus/read_speed_ladder.py`
  (never raises, fully unit-tested); the loop + per-track auto-fix live in
  `workers/rip_worker.py`; `-S`/`-l` plumbing is in `adapters/cyanrip_backend.py`.

**Two signals, deliberately separate (real-hardware finding, 2026-07-01):**
The escalation *trigger* is an **unrecoverable read error** (cyanrip's
`Ripping errors: N > 0` / a track "with errors"). Distinct from that is **read
instability** — cyanrip's `-Z` secure re-read hit its repeat limit with no two
reads agreeing (`Done; (no matches found, but hit repeat limit of N)`). The first
real disc proved these come apart: it reported `Ripping errors: 0` (whole-disc)
while one track never converged. So instability is now read per-track and
**flagged, not auto-re-ripped** — a whole-disc re-rip to retry one track costs
hours with no guarantee (see check 3). A *converged* read that only matches an
offset-variant pressing is a pressing difference, not instability, and is never
flagged.

**The three HARDWARE-GATED checks — status after the source review of 2026-07-01
(none can cause a regression — a clean disc is always a single fast pass):**
1. **Does the BDR-209D honour `-S`? — the assumption was WRONG; corrected.** We
   assumed a drive that can't change speed would *silently ignore* `-S` (degrade
   to plain re-reads). Source review of cyanrip disproved that: if the drive lacks
   the `CDIO_DRIVE_CAP_MISC_SELECT_SPEED` capability, cyanrip prints "Device does
   not support changing speeds!" and **aborts the rip** (`cyanrip_main.c`); it also
   aborts if the underlying `cdio_cddap_speed_set` call errors. The BDR-209D's log
   banner says `Speed: default (unchangeable)` — i.e. it lacks that capability — so
   an `-S` escalation would have crashed the re-rip. **Fix:** the log parser reads
   the `Speed:` banner (`RippingInfo.speed_changeable`); a speed-locked drive makes
   the ladder skip the speed rungs and escalate via `-Z` only, so `-S` is never
   sent (pass 1 always runs at max, so the lock is known before any `-S` could go
   out). **Still genuinely open:** whether a drive that *does* advertise the
   capability actually reads slower — untestable on the BDR-209D, which can't.
   To exercise it, use Settings → Fixed speed on a drive that reports `changeable`.
2. **Is cyanrip's per-track read-quality signal reliable? — ANSWERED (0.4.7).**
   The whole-disc `Ripping errors:` count is NOT sufficient: a real disc reported
   `0` while a track's `-Z` re-read never converged. We now also read the
   per-track convergence verdict and flag it (`unstable_tracks`).
3. **Can cyanrip re-rip a SUBSET of tracks? — ANSWERED + WIRED IN (0.4.8): YES,
   via `-l <comma-list>`** (e.g. `-l 3,5` rips only tracks 3 and 5; confirmed in
   `cyanrip_main.c` — `rip_indices[]` gates which tracks call `cyanrip_rip_track()`,
   distinct from `-t` tag metadata). This made per-track re-rip cheap (seconds, not
   a whole-disc pass) and needs no speed change, so it's the natural escalation
   lever on a speed-locked drive — now the per-track **auto-fix** above. **The one
   remaining hardware gate:** the re-rip-and-swap path (temp-dir re-rip → copy the
   improved FLAC into the album) is safe by construction but not yet exercised on a
   real drive; validate on the BDR-209D rig.

[eac]: https://www.exactaudiocopy.de/extraction-technology/
[cmp]: https://wiki.hydrogenaudio.org/index.php?title=Comparison_of_CD_rippers
[cdp]: https://wiki.hydrogenaudio.org/index.php?title=Cdparanoia
[man]: https://manpages.debian.org/unstable/libcdio-utils/cd-paranoia.1.en.html
[src]: https://github.com/cyanreg/cyanrip/blob/master/src/cyanrip_log.c
[dbp]: https://forum.dbpoweramp.com/forum/dbpoweramp/cd-ripper/31777-pioneer-bdr-208dbk-ripping-questions
[cdr]: https://www.cdrinfo.com/d7/content/pioneer-bdr-2207-bdr-207m-bdxl-burner-review?page=1

## 9. Cache defeating vs. the 2026 landscape doc (research finding, 2026-07)

**Symptom.** The maintainer's 2026 ripper-landscape research doc treats **cache
defeating** as a required extraction vector for archival credibility (alongside
read offset, overread, C2, AccurateRip, etc.), scoring tools against it.

**The finding.** Neither engine in our current lineage gives us a *measured*
cache-defeat verdict:

- **cyanrip** has no cache-defeat flag and prints no cache line in its log at
  all (confirmed against `adapters/cyanrip_backend.py`'s argv builder and the
  `parsers/cyanrip_log.py` finish-log parser — no cache-related field exists on
  the banner to parse; it reads the offset, speed capability, and disc IDs).
- Its engine, **libcdio-paranoia**, *attempts* cache defeat every rip —
  readahead cache-exhaustion reads, plus FUA (Force Unit Access) where the
  drive advertises support — but this is **best-effort and drive-dependent**,
  with no runtime signal confirming it actually happened on a given drive.
  whipper's `defeats_cache` setting in `whipper.conf` was the same shape: a
  configured *intent*, not a measured *result*.

**Decision (see PLANNING.md KDD-25 for the full record):** report this
honestly as **"attempted, not measured."** Our EAC-style log export
(`eac_log_export.py`) already renders `Defeat audio cache: (unknown)` rather
than fabricating a `Yes` we can't verify. Correctness doesn't depend on having
a cache-defeat bit anyway — `-Z N` secure re-read consensus plus
AccurateRip/CTDB external verification catches a cache-served stale read the
same way it catches any other read discrepancy, by disagreeing with a trusted
external checksum rather than by asserting an unverifiable drive-behavior
fact. A *measured* verdict (`cd-paranoia -A`, the standalone cdparanoia tool's
own cache-defeat self-test) is deferred, not rejected — it would add a new
host-tool dependency, which needs a `DEPENDENCIES.md` entry, deviation-policy
sign-off, and hardware validation before it could be trusted (KDD-25).

**Two more notes from cross-checking that doc against our own decisions:**

- **The doc's favored tracker path is the one we deliberately left behind.**
  It endorses whipper + `whipper-plugin-eaclogger` as the way to satisfy
  OPS/Orpheus-style tracker log acceptance. That's the exact backend we
  removed as the ripper (KDD-18) and the exact path our own research
  concluded does **not** cleanly work even for whipper (the plugin's
  EAC-*style* log still can't emit a real EAC checksum — RED's wall — per
  [whipper-plugin-eaclogger#7](https://github.com/whipper-team/whipper-plugin-eaclogger/issues/7)).
  Our no-forged-provenance / open-trust position (AccurateRip + CTDB + an
  honest unsigned log) is **unchanged** by the doc's framing — see
  PLANNING.md **KDD-24** and `docs/eac-log-and-repair-feasibility.md`.
- **The doc's "wanted-tier" comparator is fre:ac.** It names **fre:ac** as a
  tool that has shipped AccurateRip support since 2021 while writing no
  tracker-submittable logs — i.e. the same open-trust-only shape we've landed
  in, not a tool that has actually solved tracker acceptance either.

## 10. Closing the gaps with license-compatible open source (per-gap option menu, 2026-07)

The maintainer's directive, recorded here as the standing policy for every gap
below:

1. **PR-first, not merge-assumed.** Where a gap is best closed *inside* an
   upstream tool, the plan is to **open a pull request upstream** (cyanrip,
   whipper, libcdio-paranoia, cdrdao, or the tracker logcheckers) and *be
   adaptable to their decision* — merging is their call. A **fork is the
   fallback**, taken only if upstream declines or stalls (§7 is the heavy
   in-house-tree procedure if it ever comes to that).
2. **Plan every gap — except the signed EAC log checksum.** That one is
   permanently off the table: emitting an EAC Rijndael-256 checksum over a
   non-EAC rip forges provenance (KDD-11/13, brief, CLAUDE.md). Not "hard" —
   *refused*. Everything else gets a real route below.
3. **The honesty gate.** For any capability we can't currently *prove*, we
   either ship a **verification path** or **state explicitly why we can't verify
   it yet** — never a bare "(unknown)" without a reason, never a fabricated
   claim. "Verify, or say why we're unsure" is the acceptance test for each row.

**Licensing latitude (recap of §2, why the menu is wide).** Platterpus is
GPL-3.0 and — critically — **invokes every external tool as a subprocess, never
links it** (KDD-10). Subprocess use is mere aggregation, not a derivative work,
so we can *invoke* essentially any OSI-licensed tool regardless of its license,
**including GPL-2.0-only** tools like `cdrdao`. Linking or copying source is the
only place license compatibility bites (and there GPL-2-only stays barred,
KDD-16). So "integrate as a subprocess" is almost always the cheapest,
lowest-obligation route, and it's how we already use cyanrip/ffmpeg/flac/metaflac.

### The menu, gap by gap

| Gap | Best route (PR-first) | Candidate OSS / where | License fit | Effort | How we'd *verify* it (honesty gate) | Go / no-go |
|---|---|---|---|---|---|---|
| **Cache-defeat verdict** | PR to cyanrip to surface a cache self-test; else integrate `cd-paranoia -A` as a subprocess | cyanrip; `cdparanoia`/libcdio-paranoia (GPL-3) | ✓ (subprocess: any; PR to LGPL cyanrip: fine) | Med | Run `-A` on the real BDR-209D; a self-test that reports the drive's cache size + defeat method IS the verification. Until then KDD-25 keeps the honest "attempted, not measured" note. | **Deferred, PR-first.** Not worth a new host tool until a gap-consumer needs it; the honest note already satisfies the gate. |
| **Test & Copy** (two-pass Test+Copy CRC) | PR to cyanrip for a two-pass mode; else our own second invocation + diff | cyanrip | ✓ | Med | Two independent passes producing two CRCs that we compare — self-verifying by construction. | **No-go for now.** Our `-Z N` consensus re-read is a *stronger* real-world guarantee; T&C matters only for a tracker log we don't target. Revisit only if whipper is re-added. |
| **Gap / INDEX-00 detection** | Integrate `cdrdao read-toc` as a subprocess (what whipper does); else PR cyanrip | `cdrdao` (**GPL-2.0-only** — fine as a subprocess) | ✓ (subprocess only — do **not** link/copy) | Med–hard | Compare our detected pregaps against an EAC/whipper baseline cue on a real disc. | **Deferred.** Audio is already bit-perfect; only INDEX-00 *cue metadata* differs. Worth it only alongside a single-image rip mode. |
| **HTOA** (hidden track-0 audio) | PR to cyanrip to rip the track-1 pregap; else `cdrdao`/`cdparanoia` span read | cyanrip; cdparanoia | ✓ | Med | Rip a known-HTOA disc and confirm the pregap audio extracts + verifies. **Hardware-gated** (need such a disc). | **Deferred, explicit scope note.** Rare; documented as out-of-scope until a real HTOA disc is on hand (TASKS.md). |
| **C2 error pointers** | PR to **libcdio-paranoia** to expose C2, or a different read primitive below cyanrip | libcdio-paranoia (GPL-3); or a C2-aware reader | ✓ (GPL-3) | **Hard** | Only a real drive+disc with induced errors can confirm C2 flags are read and acted on. | **No-go (documented uncertainty).** The gap is *below* cyanrip — cd-paranoia deliberately ignores C2. Honest status: we do **not** use C2; overlap re-reads + AR/CTDB are our error defense. A PR to libcdio is the only route and upstream interest is unknown. |
| **Tracker (RED/OPS) recognition** | **Re-add whipper as an optional secondary backend** (reverses KDD-18, needs maintainer sign-off); *and/or* PR to add cyanrip to the OPS/orpheus Logchecker allow-list | whipper (GPL-3, a **recognized** ripper); OPSnet/orpheusnet Logchecker (PHP) | ✓ | Med (whipper) / Low but uncertain (logchecker PR) | A recognized-ripper native log scored by the real logchecker — verifiable directly against OPS's checker. | **Documented option, maintainer's call.** A cyanrip *fork alone cannot* solve this (checkers gate on ripper *identity*, not our code). whipper is the honest OSS answer; the checksum wall still bars RED regardless. |

### Recommendation & decision gates

- **Do nothing speculative.** Every row is *deferred with a plan*, not built — matching §5's decision gates. Adopt a route only when a specific gap becomes a **hard requirement** for a real user goal.
- **When a gap does become required:** open the **upstream PR first**; keep the change small and rebased against upstream `master`; only fall back to a fork (§7) if it's declined. Prefer **subprocess integration** over forking wherever the capability can be reached from a separate binary (it sidesteps the maintenance and most obligations).
- **The one permanent no:** never forge the EAC log checksum. If tracker acceptance is ever a hard requirement, the *only* honest routes are re-adding whipper (a recognized ripper) or getting cyanrip onto the logchecker allow-list upstream — both leave provenance truthful.
- **Honesty gate is binding:** anything we surface to the user (a report field, a log line, a Settings claim) must be something we've verified or explicitly qualified — the cache-defeat "(unknown)" + reasoned note (KDD-25) is the template.

> **Ordered, step-by-step version:** this menu is turned into a *ranked* action
> list — which upstream PR to do first, its odds, and exactly how to contribute
> each — in [`upstream-pr-roadmap.md`](upstream-pr-roadmap.md). Start there when
> actually contributing; the headline (revised 2026-07-07 in the roadmap) is
> that the honest first move on the pregap/INDEX-00 + HTOA gaps is to **help
> land cyanrip PR #115**, with a Platterpus-side `cdrdao` subprocess
> integration kept only as the fallback if #115 stalls indefinitely.

---

*Last updated for Platterpus v0.4.24.*
