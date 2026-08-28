# The cyanrip fork — engine strategy and fork discipline

Why Platterpus maintains a fork of cyanrip at all, what the alternatives were, and how the fork is kept sane against upstream.

§1 is long-horizon *research* — a menu of options, explicitly not a commitment, including the licensing analysis that gates all of it. §2 is the concrete, executable half: branch layout, the patches we carry, how the container builds it, and the re-merge discipline that keeps the diff small.

For the **binding release protocol** with the fork see [`cyanrip-handshake.md`](cyanrip-handshake.md); for what we want *from* cyanrip and how it reaches upstream see [`cyanrip-upstream.md`](cyanrip-upstream.md).

## Where this came from

Consolidated from two separate documents so the subject has one home — part of a four-document merge that also produced `cyanrip-upstream.md`. Content is unchanged — each part below is the original file, whole, with its headings demoted one level.

**Parts are lettered, not numbered, on purpose:** the originals number their own sections from 0, so a numbered wrapper would make a reference like *§2.1* ambiguous. `Part A §8` reads exactly one way.

| Part | Was | Written |
|---|---|---|
| A | the former `ripper-engine-strategy.md` | 2026-06-23, living |
| B | the former `cyanrip-soft-fork.md` | 2026-07-08 |

---

## Part A — Engine strategy — fork / combine / upgrade feasibility

## Ripper engine strategy — fork / combine / upgrade feasibility (research, living)

> **Status: RESEARCH / OPTIONS — not a commitment.** Long-horizon: revisited
> only *after* the v1 feature set works and hardware parity is proven. This doc
> deliberately **keeps open** the option of forking and/or combining whipper and
> cyanrip and maintaining our own engine — which **revisits [KDD-18](../PLANNING.md)
> ("never fork whipper")**. Nothing here changes current direction; adopting any
> fork/combine path requires an explicit new KDD that amends KDD-18. This file is
> *living* — append findings as the research continues (see §6).

### 0. Why this exists

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

### 1. The two engines (facts, with sources)

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

### 2. Licensing — what we may legally do (the gating question, answered)

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

### 3. The strategic options (menu, with trade-offs)

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

### 4. Why deferring is free (the architectural safety net)

The `RipBackend` ABC already isolates the engine (KDD-08/18; a `Config`-level
selector would be reintroduced alongside a second backend). A fork would be **a
new adapter implementation + a host-setup install
step** — not a GUI rewrite. So the maintainer's sequencing ("after we make the
rest work") costs nothing: maintaining adapter discipline *is* what keeps the
fork/combine option open.

### 5. Decision gates before adopting any fork/combine

1. v1 feature set complete **and** hardware parity proven (the
   `output_reference/` EAC output-parity matrix passing for whipper **and** cyanrip).
2. A concrete need upstream won't serve, **documented**.
3. Maintenance capacity assessed: who builds/releases the fork; CI for a C/Meson
   (or Python) build; ongoing security updates for FFmpeg/libcdio.
4. An explicit **KDD amending KDD-18**.

### 6. Open research tasks (append findings here as we learn)

- [x] **Gauge cyanrip upstream's activity + PR responsiveness (gates Option 0) — done 2026-07-08.** *Development:* `master` is live (last commit 2026-03-25; ~25–30 commits/yr). *Releases:* stalled — last tag v0.9.3.1 is ~2 yr old. *Responsiveness:* the maintainer **does merge external PRs, but slowly** (contact/cadence facts live in the roadmap's **Process** block — [`cyanrip-upstream.md`](cyanrip-upstream.md) — the canonical home; PR #115, pregap/HTOA, is open and actively reviewed). **Conclusion — a fork is NOT warranted for "slow releases":** because Platterpus owns the `ripping` Distrobox container, we can build cyanrip **from any git commit** (our own topic branch *before* a merge, or upstream `master` *after*), so cyanrip's release cadence never gates us — the "slow releases → must fork" reasoning dissolves. The real, smaller decision is **build-cyanrip-from-source in the container vs. a distro package** (a maintenance choice, not a fork). Escalate to a **soft fork** (upstream `master` + our small rebased patch set) only if a needed PR is *declined or stalls indefinitely*; a **hard fork / consolidated tree (§7)** stays behind the §5 gates + a KDD-18 amendment. (Upstream conventions/CI: see the roadmap's Process block.) **The soft fork now exists** (decided 2026-07-08): runbook in [`cyanrip-fork.md`](cyanrip-fork.md), execution kit in `scripts/cyanrip/` — two contributions prepared (the `-a`/`-t` colon fix ⭐ and full encoder opts). The "map cyanrip's FFmpeg flag surface" question below was answered **negatively** the same day: cyanrip hardcodes `compression_level` and opens encoders with no options dict — hence the prepared encoder-opts contribution.
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

### 7. Option 3a — vendor + branch-consolidate both upstreams into one in-house tree

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

#### 7.1 Repo shape (pick at decision time)
- **(a) Monorepo via `git subtree`** — vendor each upstream under `vendor/whipper`
  and `vendor/cyanrip` *with full history*; local edits live alongside; pull
  upstream with `git subtree pull`. Best fit for "single project here." Recommended.
- **(b) Two in-house forks** (`*-whipper`, `*-cyanrip`), each with a `consolidated`
  branch — better if we intend to send PRs back upstream (Option 0 still in play).
- Either way the GUI repo is unchanged; only the host-setup install source moves
  from distro/COPR packages to our built artifacts.

#### 7.2 The consolidation procedure (the actual work)
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

#### 7.3 Staying current
Re-run a lightweight consolidation when upstream advances: `git subtree pull` (or
re-mirror + re-triage), re-merge our local deltas, re-validate. Budget this as
recurring maintenance, not one-time.

#### 7.4 Licensing & attribution (non-negotiable)
The consolidated work is **GPL-3.0** (whipper GPL-3 + cyanrip LGPL-2.1 → GPL-3;
§2). We MUST: retain **all** upstream copyright/license headers + `AUTHORS`/`NOTICE`,
keep cyanrip's LGPL-2.1 notices intact even when combined under GPL-3, **state our
modifications**, ship **complete corresponding source**, add **no further
restrictions**, and never relicense proprietary. The clean-room bar (KDD-16) still
forbids pulling in anything **GPL-2.0-only**. If we redistribute binaries (e.g.
inside the container image or AppImage), honor the GPL source-offer.

#### 7.5 Risks (why this is the heavy option)
- **We become the maintainer** of two upstream codebases (security updates for
  FFmpeg/libcdio; the whipper `pkg_resources`/Python-3.14 cliff; build/packaging).
- **Merging unreleased branches can lower quality** vs. a curated upstream release —
  hence the per-branch verify-or-reject gate; expect to reject a lot.
- **Heavy, divergent conflicts** between long-lived branches.
- **Drift from upstream** makes future `subtree pull`s harder the more we edit.

#### 7.6 First step when we start (low-cost, read-only spike)
Do **only** steps 7.2-(1→3): mirror both, enumerate, triage, and produce the
**per-branch manifest + a feasibility report** (which branches carry real
unreleased value, rough conflict/maintenance estimate). No merging, no commitment —
it turns "should we consolidate?" into a decision backed by data, and feeds the §6
checklist. Park the manifest in §6.

### 8. C2 error pointers — drive gap or software gap? (research finding, 2026-07-01)

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

#### 8.1 The adaptive read-speed ladder (shipped 0.4.6)

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

### 9. Cache defeating vs. the 2026 landscape doc (research finding, 2026-07)

> **Where that doc lives (resolved 2026-07-21):** the maintainer's 2026
> ripper-landscape research doc was provided as **session research input** and
> was never committed to this repository (a repo-wide search, and the
> 2026-07-21 full-docs audit before it, find only references). Its
> load-bearing claims are preserved — and where wrong, corrected — in the
> project's own record: `eac-parity.md`'s extraction-vector
> scorecard, this section's notes, and PLANNING.md **KDD-24**'s two
> corrections. If the original file resurfaces, save it under `docs/archive/`
> with a banner — the same convention as the missing `compass_artifact_*.md`
> (see `docs/README.md`).

**Symptom.** The maintainer's 2026 ripper-landscape research doc treats **cache
defeating** as a required extraction vector for archival credibility (alongside
read offset, overread, C2, AccurateRip, etc.), scoring tools against it.

**The finding.** Neither engine in our current lineage gives us a *measured*
cache-defeat verdict:

- **cyanrip** has no cache-**defeat** flag, and nothing it prints answers
  "was the cache defeated". Upstream prints no cache line at all; **the fork
  prints two** — `Cache model:` in every rip's banner (added round 5 as
  `Cache defeat:`, renamed in round 6 because the old label asserted an outcome
  the value disclaims) and, under `-x`/`--cache-probe` (added round 7 lap 1, at
  our own round-5 request), a `Cache probe:` line. One is what paranoia
  *models*, the other measures readback size, so neither may fill EAC's row:
  both are registered in `parsers/cyanrip_log.py`'s knowingly-ignored table
  with that reason recorded.
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
own cache-defeat self-test) was deferred, not rejected — it would add a new
host-tool dependency, which needs a `DEPENDENCIES.md` entry, deviation-policy
sign-off, and hardware validation before it could be trusted (KDD-25).

> **Superseded 2026-07-24 — see PLANNING.md KDD-29.** Every one of those
> preconditions was met and the feature **shipped in v0.5.8**: the `cd-paranoia`
> row is in `DEPENDENCIES.md`, the maintainer signed off, and the verdict was
> hardware-validated on the BDR-209D on 2026-07-26 (fixture:
> `tests/fixtures/cdparanoia_A_bdr209d.txt`). *Set up drive → Analyse cache*
> now measures the drive's real behaviour via `adapters/cache_probe.py` and
> renders a measured `Yes`/`No`. What survives from KDD-25 is the rule it was
> protecting, not its conclusion: an **inconclusive** probe still renders
> `(unknown)`, never a fabricated `Yes`.

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
  PLANNING.md **KDD-24** and `docs/eac-parity.md`.
- **The doc's "wanted-tier" comparator is fre:ac.** It names **fre:ac** as a
  tool that has shipped AccurateRip support since 2021 while writing no
  tracker-submittable logs — i.e. the same open-trust-only shape we've landed
  in, not a tool that has actually solved tracker acceptance either.

### 10. Closing the gaps with license-compatible open source (per-gap option menu, 2026-07)

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

#### The menu, gap by gap

| Gap | Best route (PR-first) | Candidate OSS / where | License fit | Effort | How we'd *verify* it (honesty gate) | Go / no-go |
|---|---|---|---|---|---|---|
| **Cache-defeat verdict** | PR to cyanrip to surface a cache self-test; else integrate `cd-paranoia -A` as a subprocess | cyanrip; `cdparanoia`/libcdio-paranoia (GPL-3) | ✓ (subprocess: any; PR to LGPL cyanrip: fine) | Med | Run `-A` on the real BDR-209D; a self-test that reports the drive's cache size + defeat method IS the verification. Until then KDD-25 keeps the honest "attempted, not measured" note. | **Deferred, PR-first.** Not worth a new host tool until a gap-consumer needs it; the honest note already satisfies the gate. |
| **Test & Copy** (two-pass Test+Copy CRC) | PR to cyanrip for a two-pass mode; else our own second invocation + diff | cyanrip | ✓ | Med | Two independent passes producing two CRCs that we compare — self-verifying by construction. | **No-go for now.** Our `-Z N` consensus re-read is a *stronger* real-world guarantee; T&C matters only for a tracker log we don't target. Revisit only if whipper is re-added. |
| **Gap / INDEX-00 detection** | Integrate `cdrdao read-toc` as a subprocess (what whipper does); else PR cyanrip | `cdrdao` (**GPL-2.0-only** — fine as a subprocess) | ✓ (subprocess only — do **not** link/copy) | Med–hard | Compare our detected pregaps against an EAC/whipper baseline cue on a real disc. | **Deferred.** Audio is already bit-perfect; only INDEX-00 *cue metadata* differs. Worth it only alongside a single-image rip mode. |
| **HTOA** (hidden track-0 audio) | PR to cyanrip to rip the track-1 pregap; else `cdrdao`/`cdparanoia` span read | cyanrip; cdparanoia | ✓ | Med | Rip a known-HTOA disc and confirm the pregap audio extracts + verifies. **Hardware-gated** (need such a disc). | **Deferred, explicit scope note.** Rare; documented as out-of-scope until a real HTOA disc is on hand (TASKS.md). |
| **C2 error pointers** | PR to **libcdio-paranoia** to expose C2, or a different read primitive below cyanrip | libcdio-paranoia (GPL-3); or a C2-aware reader | ✓ (GPL-3) | **Hard** | Only a real drive+disc with induced errors can confirm C2 flags are read and acted on. | **No-go (documented uncertainty).** The gap is *below* cyanrip — cd-paranoia deliberately ignores C2. Honest status: we do **not** use C2; overlap re-reads + AR/CTDB are our error defense. A PR to libcdio is the only route and upstream interest is unknown. |
| **Tracker (RED/OPS) recognition** | **Re-add whipper as an optional secondary backend** (reverses KDD-18, needs maintainer sign-off); *and/or* PR to add cyanrip to the OPS/orpheus Logchecker allow-list | whipper (GPL-3, a **recognized** ripper); OPSnet/orpheusnet Logchecker (PHP) | ✓ | Med (whipper) / Low but uncertain (logchecker PR) | A recognized-ripper native log scored by the real logchecker — verifiable directly against OPS's checker. | **Documented option, maintainer's call.** A cyanrip *fork alone cannot* solve this (checkers gate on ripper *identity*, not our code). whipper is the honest OSS answer; the checksum wall still bars RED regardless. |

#### Recommendation & decision gates

- **Do nothing speculative.** Every row is *deferred with a plan*, not built — matching §5's decision gates. Adopt a route only when a specific gap becomes a **hard requirement** for a real user goal.
- **When a gap does become required:** open the **upstream PR first**; keep the change small and rebased against upstream `master`; only fall back to a fork (§7) if it's declined. Prefer **subprocess integration** over forking wherever the capability can be reached from a separate binary (it sidesteps the maintenance and most obligations).
- **The one permanent no:** never forge the EAC log checksum. If tracker acceptance is ever a hard requirement, the *only* honest routes are re-adding whipper (a recognized ripper) or getting cyanrip onto the logchecker allow-list upstream — both leave provenance truthful.
- **Honesty gate is binding:** anything we surface to the user (a report field, a log line, a Settings claim) must be something we've verified or explicitly qualified — the cache-defeat "(unknown)" + reasoned note (KDD-25) is the template.

> **Ordered, step-by-step version:** this menu is turned into a *ranked* action
> list — which upstream PR to do first, its odds, and exactly how to contribute
> each — in [`cyanrip-upstream.md`](cyanrip-upstream.md). Start there when
> actually contributing; the headline (revised 2026-07-07 in the roadmap) is
> that the honest first move on the pregap/INDEX-00 + HTOA gaps is to **help
> land cyanrip PR #115**, with a Platterpus-side `cdrdao` subprocess
> integration kept only as the fallback if #115 stalls indefinitely.

---

## Part B — Soft-fork mechanics — setup, patches, re-merge discipline

## cyanrip soft fork — setup, patches, and re-merge discipline

> **What this is.** The concrete plan + ready-to-apply changes for maintaining a
> **soft fork** of cyanrip (`rmccann-hub/cyanrip` = upstream `master` + a small,
> rebased patch set), and for sending each patch back **upstream as a PR**. The
> soft fork is a *staging area and fallback*, never a divergence: every patch is
> shaped to merge cleanly into `cyanreg/cyanrip` and to disappear from our fork
> the moment it lands upstream. Companion to
> [`cyanrip-fork.md`](cyanrip-fork.md) (§3 options, §5 gates,
> §6 activity finding) and [`cyanrip-upstream.md`](cyanrip-upstream.md).
>
> **Guiding rules (maintainer, 2026-07-08):**
> 1. **Easy to re-merge for the owner.** Minimal diffs, one focused change per
>    commit/PR, no drive-by reformatting, no churn.
> 2. **Their conventions win.** cyanrip is C, LGPL-2.1-or-later; the process
>    facts (maintainer contact, style, CI, responsiveness) live in the
>    roadmap's **Process** block ([`cyanrip-upstream.md`](cyanrip-upstream.md)
>    — the canonical home). Where cyanrip's style/rules differ from
>    Platterpus's (heavy comments, type hints, 88-col, etc.), **match
>    cyanrip** — our conventions do not apply to C we send upstream.
> 3. **Documentation is key.** Each patch carries a clear rationale and, upstream,
>    an issue that explains the bug/enhancement before the PR.
> 4. **PR-first, adaptable to the maintainer's call.** The fork is the fallback if
>    a PR is declined or stalls — not the goal.

---

### 0. Status & why the execution happens elsewhere

The patches and issue text below are **prepared and reviewed here**, but the
GitHub actions (fork, push, issue, PR) and the C build **cannot run from the
Platterpus cloud session** — it is scoped to `rmccann-hub/platterpus` only
(cross-owner `add_repo` is blocked; the GitHub token can't reach
`cyanreg/cyanrip`). Execute from **one** of:

- **A new Claude Code session seeded with the repo** — start it with
  `cyanreg/cyanrip` (or your fork `rmccann-hub/cyanrip`) as the initial source
  (the `add_repo` error message recommends exactly this). That session can fork,
  build, patch, and open the PR/issue.
- **Locally** — the commands below are copy-paste runnable on any Linux box with
  the build deps.

The build/test also needs the C toolchain + a real disc (a rip smoke-test),
which is the `ripping`-container / real-hardware environment, not the cloud
session. Treat every patch here as **reviewed-but-unbuilt** until it compiles in
that environment and passes a smoke rip.

**Execution kit.** The mechanical steps below are packaged as run-anywhere
helpers in [`scripts/cyanrip/`](../scripts/cyanrip/) so each is one command:
`setup-fork.sh` (fork clone + branch layout), `apply-colon-fix.py` (a
**verified, dry-run-first** patcher for the §2 fix — it checks the function's
shape and aborts rather than write a wrong diff; unit-tested in
`tests/test_cyanrip_colon_patcher.py`), `build.sh` (meson/ninja in the
container), and copy-paste `issue-*.md` / `pr-*.md` bodies. This doc stays the
*rationale + reference*; the kit is the *execution layer* — **the kit's
`issue-*.md` / `pr-*.md` files are the canonical (and only) paste text**; since
2026-07-21 this doc links to them instead of carrying copies (a one-word drift
between the old duplicate copies is what forced the choice).

---

### 1. Fork & branch layout

```
cyanreg/cyanrip (upstream)
        └── rmccann-hub/cyanrip (our fork)
              ├── master              # mirrors upstream, fast-forward only — never commit here
              ├── fix/meta-colon      # one topic branch per upstream PR
              └── feat/encoder-opts   #   "        "
              └── platterpus          # optional: integration branch = master + all our not-yet-merged patches,
                                      #           the exact tree we build in the ripping container
```

- **`master` tracks upstream, untouched.** `git remote add upstream
  https://github.com/cyanreg/cyanrip && git fetch upstream && git switch master
  && git merge --ff-only upstream/master`. Never land our commits on it — that is
  what keeps re-merge trivial.
- **One topic branch per contribution**, branched off `master`, holding **one
  focused commit**. That branch is what becomes the upstream PR.
- **`platterpus` integration branch** (optional) = `master` + each topic branch,
  rebased whenever `master` advances. This is the tree the `ripping` container
  builds so we get a fix *before* upstream releases (see §4). Keep it a pure
  rebase of the topic branches — no unique work — so it stays a no-op to
  reconstruct.

**Staying current:** `git fetch upstream && git switch master && git merge
--ff-only upstream/master`, then `git rebase master fix/meta-colon` (etc.), then
rebuild `platterpus`. When a topic branch's PR merges upstream, **delete the
branch and drop it from `platterpus`** — it's now in `master`.

---

### 2. Contribution 1 — metadata colon parsing (bug fix) ⭐

**Why it's first:** it's a confirmed bug that removes Platterpus's single largest
workaround, and colons in titles ("Album: Subtitle", classical works) are
everywhere, so it helps every cyanrip user.

#### The bug (confirmed in `master`, `src/cyanrip_main.c`)

`main()` runs the user's `-a`/`-t` string through `append_missing_keys()` (to
support the positional `-a "Album:Artist"` shorthand) *before*
`av_dict_parse_string(&ctx->meta, copy, "=", ":", 0)`:

```c
char *copy = append_missing_keys(album_metadata_ptr, "album=", "album_artist=");
int err = av_dict_parse_string(&ctx->meta, copy, "=", ":", 0);
```

> **⚠️ SCOPE CORRECTION (2026-07-31).** This is real at **v0.9.3.1**, the tag the
> container deploys (`src/cyanrip_main.c`), and was reproduced on hardware
> 2026-06-27. It is **fixed upstream in `master`**: the function moved to
> `src/naming.c` and is a hand-rolled scan that minds `\:` / `\=` escapes. The
> fork session could not reproduce it against their tree for exactly that reason.
> So the paste-ready issue/PR for this is **superseded** — do not file it.
>
> **Do NOT remove Platterpus's colon pass on that basis.** Our
> `_escape_meta_value` substitutes U+2236 *before* invoking cyanrip, so deleting
> `restore_substituted_colons` would ship U+2236 into every user's tags. The
> version-guarded removal plan below still applies; its trigger is now "the
> container runs `master` or the fork", not "upstream fixes it".

`append_missing_keys()` tokenises with `av_strtok(src, ":", ...)` — splitting on
**every** `:`, ignoring both `=` and backslash escapes — and injects a key in
front of any keyless token. So an explicit value that contains a colon is
corrupted:

```
-a "album=Every Breath You Take: The Classics"
        → av_strtok tokens:  "album=Every Breath You Take"  |  " The Classics"
        → " The Classics" has no '=', treated as keyless → "album_artist=" injected
        → "album=Every Breath You Take:album_artist= The Classics"   ← WRONG
```

`av_dict_parse_string()` *does* honour a `\` escape, but it never gets the
chance: the damage is done by `av_strtok` (which does not) in the pre-pass. That
is why Platterpus cannot pass a literal `:` at all today and works around it by
substituting U+2236 (`∶`) and restoring the real colon post-rip via metaflac
(`adapters/cyanrip_backend.py`: `_escape_meta_value` / `restore_substituted_colons`).

#### The fix (minimal, backward-compatible)

Only run the positional-shorthand injection when the string is actually
positional. If it is already in explicit `key=value` form — an `=` occurs before
the first `:` — leave it untouched and let `av_dict_parse_string()` (which honours
`\:`) parse it. Add this guard right after the `copy` is allocated, before the
`av_strtok` scan:

```c
    /* If the string is already in explicit key=value form (an '=' appears
     * before the first ':'), skip the positional-shorthand key injection.
     * The scan below tokenises on ':' with av_strtok(), which — unlike the
     * av_dict_parse_string() this feeds — does not honour the '\' escape, so
     * injecting keys here corrupts any value that legitimately contains a ':'
     * (e.g. album=Every Breath You Take\: The Classics). Positional shorthand
     * (album:album_artist, no '=') is unaffected. */
    char *first_colon = strchr(src, ':');
    char *first_eq    = strchr(src, '=');
    if (first_eq && (!first_colon || first_eq < first_colon))
        return copy;
```

That is the whole change — a few lines, no new behaviour for the positional path,
no reformatting. **Callers pass a literal colon as `\:`** (which
`av_dict_parse_string` unescapes); the guard ensures the pre-pass no longer
mangles it.

**Verified (2026-07-08) — the algorithm is proven before it goes upstream.**
`scripts/cyanrip/verify-meta-colon.c` (moved into the kit 2026-07-21) transcribes the current function
1:1 (FFmpeg helpers → libc: `av_mallocz`→`calloc`, `av_strtok`→`strtok_r`) and
the fixed function, and asserts all four cases. Built ASan/UBSan-clean
(`gcc -Wall -Wextra -fsanitize=address,undefined`) and run:

```
case 1  in : album=Every Breath You Take: The Classics
        cur: album=Every Breath You Take:album_artist= The Classics   ← current CORRUPTS
        fix: album=Every Breath You Take: The Classics                 ← fixed intact
case 2  in : Some Album:Some Artist            → both: album=Some Album:album_artist=Some Artist (shorthand kept)
case 3  in : album=Foo:date=2020               → both unchanged
case 4  in : album=…Take\: The Classics        → current still corrupts; fixed keeps the \: intact
ALL ASSERTIONS PASSED
```

This is a logic proof (a stand-in for `av_strtok`, no consecutive `:` in any
case), not a cyanrip build — the real build + smoke rip still gate the PR — but
it confirms the guard is correct and complete before we ask the maintainer.

Case check:
| Input | first `=` before first `:`? | Behaviour |
|---|---|---|
| `Some Album:Some Artist` (positional) | no `=` | inject keys — unchanged ✓ |
| `album=Foo:date=2020` | yes | skip injection → parses both ✓ |
| `album=Every Breath You Take\: The Classics` | yes | skip → `av_dict_parse_string` unescapes `\:` → correct ✓ |
| `Foo:artist=Bar` (mixed) | no (`=` after `:`) | inject `album=` before `Foo` — unchanged ✓ |

#### Upstream issue text

The canonical, paste-ready issue body lives in the kit:
**[`scripts/cyanrip/issue-colon.md`](../scripts/cyanrip/issue-colon.md)**
(title on its first line, body below — paste from there, not from this doc).
In brief: a literal `:` inside an explicit `-a`/`-t` value is corrupted because
`append_missing_keys()` tokenises with `av_strtok(src, ":")` before
`av_dict_parse_string()` runs; the proposed fix is the ~4-line skip-injection
guard from §2 above, after which callers pass `\:`.

#### Platterpus-side cleanup — AFTER the fix is live in the container

Do **not** change our side until the `ripping` container runs a cyanrip that has
the fix (older cyanrip would corrupt `\:`). Then, behind a cyanrip-version guard:
- `adapters/cyanrip_backend.py`: change `_escape_meta_value` to emit `\:` for a
  colon (instead of U+2236), keeping the existing `\`-escaping of `= ' \`.
- Delete `restore_substituted_colons` + its metaflac post-pass and the
  `_COLON_SUBSTITUTE` constant; drop the call site in the post-rip pipeline.
- Update `docs/dependency-contracts.md` (the colon note) and add a regression
  test that a colon round-trips into the FLAC tag.

---

### 3. Contribution 2 — full FLAC (libavcodec) encoder arguments

**The gap (maintainer request, 2026-07-08):** cyanrip only lets you get *one*
FLAC compression — its hardcoded per-format maximum — with no way to pass other
encoder options. In `src/cyanrip_encode.c`, `setup_out_avctx()` sets:

```c
avctx->compression_level = cfmt->compression_level;   /* from the format table, fixed */
```

and `cyanrip_init_track_encoding()` opens the encoder with **no options
dictionary**:

```c
avcodec_open2(s->out_avctx, out_codec, NULL);          /* NULL → no user options */
```

So there is no path to set FLAC's `compression_level` (0–12) or any other
libavcodec FLAC private option (`lpc_type`, `lpc_passes`, `ch_mode`,
`exact_rice_parameters`, `multi_dim_quant`, `min/max_prediction_order`, …) — and
the same NULL blocks encoder options for *every* codec, not just FLAC.

#### The design (generic, upstream-friendly)

Add a CLI way to supply an **AVDictionary of encoder options**, passed to
`avcodec_open2` instead of `NULL`. This is the FFmpeg-idiomatic approach: it
gives full FLAC control *and* works for any codec, which is far more likely to be
accepted than a FLAC-only knob.

Sketch (exact wiring to be finished against the full source when building — the
getopt loop, the `cyanrip_settings`/`cyanrip_out_fmt` structs, and the `--help`
text are the three touch points):

1. A repeatable option, e.g. `-O key=value` (or `--enc-opt key=value`), parsed
   into `AVDictionary *enc_opts` on the settings struct via
   `av_dict_set(&s->enc_opts, key, val, 0)`.
2. Thread `enc_opts` into `cyanrip_init_track_encoding()` and open with a
   **copy** per track (avcodec_open2 consumes/returns the dict):
   ```c
   AVDictionary *opts = NULL;
   av_dict_copy(&opts, ctx->settings.enc_opts, 0);
   int err = avcodec_open2(s->out_avctx, out_codec, &opts);
   /* leftover unrecognised opts remain in `opts` → warn, then av_dict_free */
   ```
3. Keep `avctx->compression_level = cfmt->compression_level` as the default; a
   user `-O compression_level=…` overrides it via the dict (options applied in
   `avcodec_open2` win). Document that unknown options warn but don't abort.

This preserves every current default (no `-O` → identical output) and adds the
full encoder surface.

#### Upstream issue text

The canonical, paste-ready issue body lives in the kit:
**[`scripts/cyanrip/issue-encoder-opts.md`](../scripts/cyanrip/issue-encoder-opts.md)**
(sanity-check the flag name with the maintainer first — see the kit README).
In brief: `setup_out_avctx()` hardcodes `compression_level` and
`cyanrip_init_track_encoding()` opens the encoder with `avcodec_open2(…, NULL)`,
so no libavcodec encoder option is reachable; the proposal is the repeatable
`-O key=value` → `AVDictionary` design from §3 above.

#### Platterpus-side use — AFTER it's live

Add a validated Settings field (e.g. FLAC compression level, and/or a raw
encoder-options string) that flows through `RipParameters` → the cyanrip argv
builder as `-O …`, routed like every other flag (`docs/dependency-contracts.md`).
Keep FLAC-as-max the default so archival output is unchanged unless the user opts
out.

---

### 3.1 Contribution 3 — subchannel pre-gap / INDEX 00 / HTOA (carry PR #115) ⭐ INDEX-00 driver

**Why it's here (KDD-32):** this is the fix that turns the soft-fork from
"prepared" into "we actually build it" — it's the mechanism for the EAC INDEX-00
pre-gap gap. Unlike Contributions 1–2 (patches we author), this one is a PR that
**already exists upstream** and we *carry + help land*, never re-author.

#### What's actually needed vs. already present

Source-confirmed (2026-07-07, and re-verified 2026-07-21 that #115 is still open):
- **cyanrip `master` already emits INDEX 00.** It synthesises a track-1 pregap
  from the TOC and `cue_writer.c` writes `INDEX 00`/`PREGAP`/`INDEX 01`; it also
  merged PR #127 (cdrdao TOC support). So **most INDEX-00 cue metadata comes for
  free** the moment the container builds `master` instead of the 2-year-old
  v0.9.3.1 tag. *First step is empirical: build master, rip a disc with a known
  pregap, and read what its `.cue` actually contains before assuming a gap.*
- **The accuracy layer is PR #115** (UltraFuzzy, `github.com/cyanreg/cyanrip`,
  **open**): adds `src/pregap.c` (+`pregap.h`), reading Subchannel-Q via MMC —
  the exact pregaps + true HTOA the TOC can't give — wired in by a one-line
  call-site swap (`cdio_get_track_pregap_lsn` → `cyanrip_get_track_pregap_lsn`).
  cyanreg is actively reviewing it (asked for an osx/mmc platform-file split);
  known blockers are a leftover `// remove after testing` `assert.h` block and a
  macOS private-libcdio-struct hack wanting `cdio_get_device_fd()`.

#### The plan (PR-first; carry as a topic branch until it lands)

1. **Do NOT open a rival PR.** The highest-value action is to **engage #115**:
   build it in the `ripping` container, real-hardware smoke-rip a **known-pregap**
   disc (and an HTOA disc if available) on the BDR-209D, and post the build +
   test result on the PR — genuinely wanted signal for an actively-reviewed but
   slow PR. Capture **log + per-track CRCs only, never audio** (Critical rule #8).
2. **Carry it on `feat/pregap`** = a topic branch tracking PR #115's head
   (`git fetch upstream pull/115/head:feat/pregap`), rebased onto `master` and
   folded into the `platterpus` integration branch (§1). That is how we ship
   exact pregaps/HTOA *before* #115 merges upstream.
3. If a blocker is trivial (the `assert.h` leftover), offer it as a
   suggestion/commit **against #115's branch**, coordinated with UltraFuzzy — not
   a competing PR (§5 discipline).
4. When #115 merges upstream: drop `feat/pregap`, fast-forward `master`, rebuild
   (§5). Our fork carries nothing for it thereafter.

#### Platterpus-side

**Essentially nothing to build.** Platterpus consumes cyanrip's `.cue` verbatim
(surfaced via the *View cue* button; the EAC-parity check reads Copy CRCs from
logs, not the cue), so INDEX 00 appears automatically once the built cyanrip
emits it. The only Platterpus change is upstream of this doc: `host_setup.py`
building cyanrip from the pinned integration-branch commit instead of the COPR
package (§4 below) — the one real new maintenance commitment (KDD-32). The
Platterpus-side **cdrdao fallback** (a `read-toc` adapter, `cyanrip-upstream.md`)
stays the no-upstream-dependency backup **only if #115 stalls indefinitely** —
it duplicates #115 and adds a dependency, so it is not the first move.

### 4. Building & consuming the fork in the `ripping` container

The point of the soft fork: get a fix **without waiting for a cyanrip release**
(last tag is ~2 years old; `master` is active — see
`cyanrip-fork.md` Part A §6). Build from our pinned commit inside the
`ripping` Distrobox container and export it as `~/.local/bin/cyanrip` exactly
like today (Critical Rule #3 routing is unchanged — only the *source* of the
binary moves from a package to our build):

```sh
# inside the `ripping` container
git clone https://github.com/rmccann-hub/cyanrip && cd cyanrip
git switch platterpus-fork            # our integration branch (master + patches)
meson setup build && ninja -C build
# install/export build/src/cyanrip to the host ~/.local/bin/cyanrip (host_setup step)
```

This is the one **real new maintenance commitment**: building cyanrip from source
in the container instead of a distro package, and rebuilding when we rebase.
Pin an exact commit; record it (a build-info line) so a rip report can say which
cyanrip built it.

---

### 5. Re-merge / cleanup discipline (so the owner's life is easy)

- **One concern per commit and per PR.** Never bundle the colon fix and the
  encoder-opts feature.
- **No unrelated changes** — no reflow, no renames, no style sweeps. A diff the
  maintainer can read in one screen is a diff that gets merged.
- **Match surrounding C**, not Platterpus conventions.
- **Rebase, don't merge**, onto upstream `master` to keep topic branches linear
  and cherry-pick-clean.
- **When a PR merges upstream:** delete the topic branch, drop it from
  `platterpus`, fast-forward `master`, and remove the corresponding
  Platterpus-side workaround (behind a version guard). The end state of a
  successful contribution is **our fork carrying nothing** for that change.

---

*Last updated for Platterpus v0.6.31.*
