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
and the `WhipperBackend` ABC + `Config.ripper_backend` mean the engine is already
swappable as a near one-file change. So we can keep this option fully open at
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
- License: **GNU LGPL-2.1** (`LICENSE.md`). C (~99%) + Meson build.
- Releases: latest **v0.9.3.1, 2024-06-05**; actively developed (8 releases).
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
bug) — which also matches KDD-18's "migrate the adapter to cyanrip if forced." The
sane escalation ladder: **Option 0 first** (upstream a specific need); escalate to
**Option 2/3** only if upstream can't/won't *and* the maintenance cost is justified.

## 4. Why deferring is free (the architectural safety net)

The `WhipperBackend` ABC + `Config.ripper_backend` already isolate the engine
(KDD-08/18). A fork would be **a new adapter implementation + a host-setup install
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

- [ ] Gauge cyanrip upstream's PR responsiveness (issue/PR turnaround) — gates Option 0.
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

