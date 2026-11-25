# The cyanrip fork — strategy, fork discipline, what we want from upstream, and known issues

Why Platterpus maintains a fork of cyanrip at all, what the alternatives were, how the fork is kept sane against upstream, what we want *from* cyanrip and how it reaches upstream, and the record of the issues we handed the fork outside the handshake. One document, five parts.

## Contents

- **[Part A — Engine strategy](#part-a--engine-strategy--fork--combine--upgrade-feasibility)** — long-horizon *research*: a menu of options, explicitly not a commitment, including the licensing analysis that gates all of it and the §10 per-gap option menu.
- **[Part B — Soft-fork mechanics](#part-b--soft-fork-mechanics--setup-patches-re-merge-discipline)** — the concrete, executable half: branch layout, the patches we carry, how the container builds it, and the re-merge discipline that keeps the diff small.
- **[Part C — What we want from upstream](#part-c--what-we-want-from-upstream--the-ranked-ask-list)** — the ranked ask list: every improvement we want from cyanrip, each with the evidence that motivates it, and an explicit list of asks we decided **not** to make. **Part C §6 is worth reading on its own:** corrections to our **own** record found while assembling the list. **Part C §7** holds the asks from the 2026-11-25 audit.
- **[Part D — The upstream PR roadmap](#part-d--the-upstream-pr-roadmap-contributor-instructions)** — *how* an ask becomes a merged pull request: the contributor-facing roadmap, in priority order, with the uncertainties flagged rather than smoothed over. The `scripts/cyanrip/` kit executes it.
- **[Part E — Known issues](#part-e--known-issues-handed-to-the-fork-outside-the-handshake-closed-2026-08-15)** — **CLOSED 2026-08-15, a record, not a live list:** the ten evidence-backed issues handed to the fork on 2026-08-14 (not a handshake lap), how each was dispositioned, and what we checked and dropped.

For the **binding release protocol** with the fork see [`cyanrip-handshake.md`](cyanrip-handshake.md); for the arguments we hand cyanrip and the output we parse see [`dependency-contracts.md`](dependency-contracts.md) and the generated [`cyanrip-consumer-contract.md`](cyanrip-consumer-contract.md).

## Where this came from

Consolidated so the subject has one home. Parts A and B were merged from two separate documents on 2026-08-03, part of a four-document merge that also produced the former `cyanrip-upstream.md`, which held Parts C and D under the letters A and B. On 2026-11-16 that file and the former `cyanrip-known-issues.md` were folded in here as Parts C, D and E (the owner's documentation consolidation of that day). Content is unchanged — each part below is the original file, whole, with its headings demoted one level. Two kinds of edit only: a cross-reference between these parts names the part (*`cyanrip-fork.md` Part A §10* became *Part A §10*, and the former upstream file's *Part A §2.7* became *Part C §2.7*), and a line-number citation into a file merged here, which a merge invalidates, became a citation of the section it pointed at. Inside a part, *this file* and *this document* still mean that part's original document.

**Parts are lettered, not numbered, on purpose:** the originals number their own sections from 0, so a numbered wrapper would make a reference like *§2.1* ambiguous. `Part A §8` and `Part C §2.1` each read exactly one way.

| Part | Was | Written |
|---|---|---|
| A | the former `ripper-engine-strategy.md` | 2026-06-23, living |
| B | the former `cyanrip-soft-fork.md` | 2026-07-08 |
| C | the former `cyanrip-improvements-wanted.md`, then Part A of the former `cyanrip-upstream.md` | 2026-07-31 |
| D | the former `upstream-pr-roadmap.md`, then Part B of the former `cyanrip-upstream.md` | 2026-07-24 |
| E | the former `cyanrip-known-issues.md` | 2026-08-14; closed 2026-08-15 |

---

## Part A — Engine strategy — fork / combine / upgrade feasibility

## Ripper engine strategy — fork / combine / upgrade feasibility (research, living)

> **Status: RESEARCH / OPTIONS — not a commitment.** Long-horizon: revisited
> only *after* the v1 feature set works and hardware parity is proven. This doc
> deliberately **keeps open** the option of forking and/or combining the previous
> backend and cyanrip and maintaining our own engine — which **revisits
> [KDD-18](../PLANNING.md)'s "never fork" stance**. Nothing here changes current direction; adopting any
> fork/combine path requires an explicit new KDD that amends KDD-18. This file is
> *living* — append findings as the research continues (see §6).
>
> *Status 2026-10-19:* Option 2, as a **soft** fork, was adopted by KDD-32
> (2026-07-24) and KDD-33 (2026-08-03): the setup wizard builds the fork's
> `platterpus-fork` branch at `FORK_PIN` (`src/platterpus/deps/fork_source.py`).
> A hard fork and Option 3 remain research.

### 0. Why this exists

The maintainer asked (2026-06-23) to not rule out, long-term, forking and/or
combining the previous backend and cyanrip — fixing, updating, and upgrading them ourselves
to get exactly the behaviour we need — **within what their licenses allow**.

Today we invoke the rippers as **subprocess adapters** (Critical Rule #3, KDD-18),
and the `RipBackend` ABC means the engine is already swappable as a near one-file
change — that's how the previous backend was replaced by cyanrip. (A `Config.ripper_backend`
selector existed while both shipped; it was removed when cyanrip became the sole
backend, and would return if a second engine did.) So we can keep this option
fully open at
**zero cost** while we finish the GUI: the decision is deferred, not foreclosed.

### 1. The two engines (facts, with sources)

**The previous backend** (the ripper Platterpus used before cyanrip) — [upstream repository](https://github.com/whipper-team/whipper)
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
| the previous backend | GPL-3.0-only | Directly compatible — same license; the combined work stays GPL-3.0. ✓ |
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
- **Option 1 — Fork the previous backend.** *Pros:* Python (our language); EAC-grade log +
  cdrdao gap detection. *Cons:* stalled releases, the `pkg_resources`/Python-3.14
  cliff we'd own, the >587 bug, morituri legacy. **High maintenance.**
- **Option 2 — Fork cyanrip.** *Pros:* active, C/FFmpeg (no Python cliff),
  already does AccurateRip+EAC-CRC+MB+ReplayGain+11 formats, LGPL→GPL3 trivial,
  applies offset without the >587 bug. *Cons:* C (not our primary language);
  Meson/FFmpeg/libcdio build + packaging to own; dep/ABI churn.
- **Option 3 — Combine.** Use **cyanrip as the engine** and port the previous
  backend's EAC-parity log (and any gap-detection edge) onto it → one GPL-3.0 engine we
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
   `output_reference/` EAC output-parity matrix passing for **every** engine being
   forked or combined — cyanrip **and** the previous backend).
2. A concrete need upstream won't serve, **documented**.
3. Maintenance capacity assessed: who builds/releases the fork; CI for a C/Meson
   (or Python) build; ongoing security updates for FFmpeg/libcdio.
4. An explicit **KDD amending KDD-18**.

### 6. Open research tasks (append findings here as we learn)

- [x] **Gauge cyanrip upstream's activity + PR responsiveness (gates Option 0) — done 2026-07-08.** *Development:* `master` is live (last commit 2026-03-25; ~25–30 commits/yr). *Releases:* stalled — last tag v0.9.3.1 is ~2 yr old. *Responsiveness:* the maintainer **does merge external PRs, but slowly** (contact/cadence facts live in the roadmap's **Process** block — [Part D](#part-d--the-upstream-pr-roadmap-contributor-instructions) of this file — the canonical home; PR #115, pregap/HTOA, is open and actively reviewed). **Conclusion — a fork is NOT warranted for "slow releases":** because Platterpus owns the `ripping` Distrobox container, we can build cyanrip **from any git commit** (our own topic branch *before* a merge, or upstream `master` *after*), so cyanrip's release cadence never gates us — the "slow releases → must fork" reasoning dissolves. The real, smaller decision is **build-cyanrip-from-source in the container vs. a distro package** (a maintenance choice, not a fork). Escalate to a **soft fork** (upstream `master` + our small rebased patch set) only if a needed PR is *declined or stalls indefinitely*; a **hard fork / consolidated tree (§7)** stays behind the §5 gates + a KDD-18 amendment. (Upstream conventions/CI: see the roadmap's Process block.) **The soft fork now exists** (decided 2026-07-08): runbook in [Part B](#part-b--soft-fork-mechanics--setup-patches-re-merge-discipline) of this file, execution kit in `scripts/cyanrip/` — two contributions prepared (the `-a`/`-t` colon fix ⭐ and full encoder opts). The "map cyanrip's FFmpeg flag surface" question below was answered **negatively** the same day: cyanrip hardcodes `compression_level` and opens encoders with no options dict — hence the prepared encoder-opts contribution.
- [ ] Inventory exactly what the previous backend does that cyanrip doesn't (gap-detection
      method, log fields, `.cue`/`.toc` output) — gates Option 3.
- [x] Map cyanrip's FFmpeg flag surface for what we want (FLAC compression level,
      encode verify, richer tags) — a rich-enough flag surface could make a fork
      unnecessary. *(Answered negatively 2026-07-08, in the first item above.)*
- [x] Prototype: build cyanrip from source inside our `ripping` container; measure
      the build/packaging burden. *(Done: since KDD-33 the setup wizard builds the
      fork from source over the COPR package, `deps/fork_source.py`.)*
- [ ] Re-verify transitive-dep licenses at the exact versions we'd ship
      (FFmpeg build flags; libcdio components).
- [ ] Re-confirm the previous backend's Python-3.14 / `pkg_resources` status at decision time.
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
- **(a) Monorepo via `git subtree`** — vendor each upstream under its own
  `vendor/<name>` directory (e.g. `vendor/cyanrip`) *with full history*; local edits live alongside; pull
  upstream with `git subtree pull`. Best fit for "single project here." Recommended.
- **(b) Two in-house forks** (one per engine, e.g. `*-cyanrip`), each with a `consolidated`
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
   the previous backend (Python) → `pytest` + a smoke rip; cyanrip → `meson build && meson test` + a smoke
   rip. "Verify a branch" = builds **and** its tests pass **and** a smoke rip works.
5. **Integration branch `consolidated`,** built like our own refactor (small,
   bisectable, green-at-every-step): start from the most-advanced stable base
   (the previous backend's `develop`, cyanrip `master`), then **merge kept branches one at a time**,
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
The consolidated work is **GPL-3.0** (the previous backend's GPL-3 + cyanrip LGPL-2.1 → GPL-3;
§2). We MUST: retain **all** upstream copyright/license headers + `AUTHORS`/`NOTICE`,
keep cyanrip's LGPL-2.1 notices intact even when combined under GPL-3, **state our
modifications**, ship **complete corresponding source**, add **no further
restrictions**, and never relicense proprietary. The clean-room bar (KDD-16) still
forbids pulling in anything **GPL-2.0-only**. If we redistribute binaries (e.g.
inside the container image or AppImage), honor the GPL source-offer.

#### 7.5 Risks (why this is the heavy option)
- **We become the maintainer** of two upstream codebases (security updates for
  FFmpeg/libcdio; the previous backend's `pkg_resources`/Python-3.14 cliff; build/packaging).
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
  the C2 column as **"No"** for cdparanoia, the previous backend **and** cyanrip; only EAC,
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

**No mature Linux C2 path exists.** libcdio-paranoia (cyanrip's engine, and the previous backend's) doesn't;
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
  (2026-11-11: it does. Its capabilities page does not declare C2, but a READ CD
  asking for C2 pointers returns them, and they flag track 5's error; the fork's
  round 39 lap 3 S11, `cyanrip@74b6f0a`.)
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
  The previous backend's `defeats_cache` setting in its own config file was the
  same shape: a configured *intent*, not a measured *result*.

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
> `tests/fixtures/cdparanoia_A_bdr209d.txt`). *Set up drive → Analyze cache*
> now measures the drive's real behaviour via `adapters/cache_probe.py` and
> renders a measured `Yes`/`No`. What survives from KDD-25 is the rule it was
> protecting, not its conclusion: an **inconclusive** probe still renders
> `(unknown)`, never a fabricated `Yes`.

**Two more notes from cross-checking that doc against our own decisions:**

- **The doc's favored tracker path is the one we deliberately left behind.**
  It endorses the previous backend plus its EAC-logger plugin as the way to
  satisfy OPS/Orpheus-style tracker log acceptance. That's the exact backend we
  removed as the ripper (KDD-18) and the exact path our own research
  concluded does **not** cleanly work even for that backend (the plugin's
  EAC-*style* log still can't emit a real EAC checksum — RED's wall — per
  [the plugin's issue #7](https://github.com/whipper-team/whipper-plugin-eaclogger/issues/7)).
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
   libcdio-paranoia, cdrdao, or the tracker logcheckers) and *be
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
| **Test & Copy** (two-pass Test+Copy CRC) | PR to cyanrip for a two-pass mode; else our own second invocation + diff | cyanrip | ✓ | Med | Two independent passes producing two CRCs that we compare — self-verifying by construction. | **No-go for now.** Our `-Z N` consensus re-read is a *stronger* real-world guarantee; T&C matters only for a tracker log we don't target. Revisit only if a tracker-recognized ripper is re-added. |
| **Gap / INDEX-00 detection** | Integrate `cdrdao read-toc` as a subprocess (what the previous backend did); else PR cyanrip | `cdrdao` (**GPL-2.0-only** — fine as a subprocess) | ✓ (subprocess only — do **not** link/copy) | Med–hard | Compare our detected pregaps against an EAC (or other trusted ripper's) baseline cue on a real disc. | **Deferred.** Audio is already bit-perfect; only INDEX-00 *cue metadata* differs. Worth it only alongside a single-image rip mode. |
| **HTOA** (hidden track-0 audio) | PR to cyanrip to rip the track-1 pregap; else `cdrdao`/`cdparanoia` span read | cyanrip; cdparanoia | ✓ | Med | Rip a known-HTOA disc and confirm the pregap audio extracts + verifies. **Hardware-gated** (need such a disc). | **Deferred, explicit scope note.** Rare; documented as out-of-scope until a real HTOA disc is on hand (TASKS.md). |
| **C2 error pointers** | PR to **libcdio-paranoia** to expose C2, or a different read primitive below cyanrip | libcdio-paranoia (GPL-3); or a C2-aware reader | ✓ (GPL-3) | **Hard** | Only a real drive+disc with induced errors can confirm C2 flags are read and acted on. | **No-go (documented uncertainty).** The gap is *below* cyanrip — cd-paranoia deliberately ignores C2. Honest status: we do **not** use C2; overlap re-reads + AR/CTDB are our error defense. A PR to libcdio is the only route and upstream interest is unknown. |
| **Tracker (RED/OPS) recognition** | **Re-add the previous backend as an optional secondary backend** (reverses KDD-18, needs maintainer sign-off); *and/or* PR to add cyanrip to the OPS/orpheus Logchecker allow-list | the previous backend (GPL-3, a **recognized** ripper); OPSnet/orpheusnet Logchecker (PHP) | ✓ | Med (re-add) / Low but uncertain (logchecker PR) | A recognized-ripper native log scored by the real logchecker — verifiable directly against OPS's checker. | **Documented option, maintainer's call.** A cyanrip *fork alone cannot* solve this (checkers gate on ripper *identity*, not our code). Re-adding a recognized OSS ripper is the honest answer; the checksum wall still bars RED regardless. |

#### Recommendation & decision gates

- **Do nothing speculative.** Every row is *deferred with a plan*, not built — matching §5's decision gates. Adopt a route only when a specific gap becomes a **hard requirement** for a real user goal.
- **When a gap does become required:** open the **upstream PR first**; keep the change small and rebased against upstream `master`; only fall back to a fork (§7) if it's declined. Prefer **subprocess integration** over forking wherever the capability can be reached from a separate binary (it sidesteps the maintenance and most obligations).
- **The one permanent no:** never forge the EAC log checksum. If tracker acceptance is ever a hard requirement, the *only* honest routes are re-adding the previous backend (a recognized ripper) or getting cyanrip onto the logchecker allow-list upstream — both leave provenance truthful.
- **Honesty gate is binding:** anything we surface to the user (a report field, a log line, a Settings claim) must be something we've verified or explicitly qualified — the cache-defeat "(unknown)" + reasoned note (KDD-25) is the template.

> **Ordered, step-by-step version:** this menu is turned into a *ranked* action
> list — which upstream PR to do first, its odds, and exactly how to contribute
> each — in [Part D](#part-d--the-upstream-pr-roadmap-contributor-instructions) of this file. Start there when
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
> Part A of this file (§3 options, §5 gates,
> §6 activity finding) and Parts C and D of this file.
>
> **Guiding rules (maintainer, 2026-07-08):**
> 1. **Easy to re-merge for the owner.** Minimal diffs, one focused change per
>    commit/PR, no drive-by reformatting, no churn.
> 2. **Their conventions win.** cyanrip is C, LGPL-2.1-or-later; the process
>    facts (maintainer contact, style, CI, responsiveness) live in the
>    roadmap's **Process** block (Part D of this file
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
              ├── fix/meta-colon      # planned: one topic branch per upstream PR (none exist today)
              └── feat/encoder-opts   #   "        "
              └── platterpus-fork     # integration branch = master + all our not-yet-merged patches;
                                      #   the tree we build in the ripping container, at FORK_PIN
```

**As it actually is (checked 2026-10-19 with `git ls-remote`):** the fork has three
branches: `master` (an ancestor of the next), **`platterpus-fork`**, which the
container builds at `FORK_PIN` (`src/platterpus/deps/fork_source.py`), and an orphan
`evidence` branch for run evidence (HR-2, `cyanrip-handshake.md` §7.4b). The fork
carries its work on `platterpus-fork` directly; the per-contribution topic branches
below are the plan for an upstream PR, and none exists today. (This diagram named
the integration branch `platterpus` until 2026-09-30.)

- **`master` tracks upstream, untouched.** `git remote add upstream
  https://github.com/cyanreg/cyanrip && git fetch upstream && git switch master
  && git merge --ff-only upstream/master`. Never land our commits on it — that is
  what keeps re-merge trivial.
- **One topic branch per contribution**, branched off `master`, holding **one
  focused commit**. That branch is what becomes the upstream PR.
- **`platterpus-fork` integration branch** = `master` + each topic branch,
  rebased whenever `master` advances. This is the tree the `ripping` container
  builds so we get a fix *before* upstream releases (see §4). Keep it a pure
  rebase of the topic branches — no unique work — so it stays a no-op to
  reconstruct.

**Staying current:** `git fetch upstream && git switch master && git merge
--ff-only upstream/master`, then `git rebase master fix/meta-colon` (etc.), then
rebuild `platterpus-fork`. When a topic branch's PR merges upstream, **delete the
branch and drop it from `platterpus-fork`** — it's now in `master`.

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
> stock COPR package ships (`src/cyanrip_main.c`); the container now builds the
> fork at `FORK_PIN` over it (`deps/fork_source.py`, KDD-32). It was reproduced on hardware
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
>
> *Status (2026-08-06, round 7 lap 31): that trigger fired.* `_escape_meta_value`
> now sends a literal colon as `\:`, and nothing writes U+2236 any more;
> `restore_substituted_colons` stays only as a safety net, armed when the
> metadata holds a colon, until a hardware rip proves the real `:` reaches the
> tag (its docstring in `adapters/cyanrip_backend.py`). The two paragraphs above
> are the 2026-07-31 record.

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

> **The letter in this sketch cannot be used:** `-O` is cyanrip's overread flag, on
> 0.9.3.x and on every later build (`cyanrip@64bc315e:src/cyanrip_main.c:2430` on the
> fork). The correction, and how to pick a name, is Part C §2.7;
> since genopt replaced getopt, every option also has a long name, so a long-only
> `--enc-opt` is available on `master`.

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
   folded into the `platterpus-fork` integration branch (§1). That is how we ship
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
emits it. The only Platterpus change was upstream of this doc, and it is **done**:
`deps/fork_source.py` builds the pinned `platterpus-fork` commit (`FORK_PIN`) over
the COPR package (§4 below) — the one real new maintenance commitment (KDD-32). The
Platterpus-side **cdrdao fallback** (a `read-toc` adapter, Part D)
stays the no-upstream-dependency backup **only if #115 stalls indefinitely** —
it duplicates #115 and adds a dependency, so it is not the first move.

### 4. Building & consuming the fork in the `ripping` container

The point of the soft fork: get a fix **without waiting for a cyanrip release**
(last tag is ~2 years old; `master` is active — see
Part A §6). Build from our pinned commit inside the
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
  `platterpus-fork`, fast-forward `master`, and remove the corresponding
  Platterpus-side workaround (behind a version guard). The end state of a
  successful contribution is **our fork carrying nothing** for that change.

---

## Part C — What we want from upstream — the ranked ask list

## cyanrip improvements wanted — the ranked ask list (2026-07-31)

> **Status, 2026-11-25 (the audit).** Most of §2 has been delivered by the fork since this
> list was written: the sample peak (§2.1, rendered as our `Peak level`), pregaps from the
> fork's own sub-channel search rather than PR #115 (§2.2), per-track `Extraction speed:`
> and `Kept read began:` (§2.3), the `-Z` convergence line (§2.4), and the C2 line's
> wording (§2.5). The text below is the record of what was asked. **New asks are §7**, and
> the fork's own upstream items (24 to 33, drafted and not yet filed) are in the fork's
> upstream issues list, `cyanrip@e665c9b4:docs/upstream/issues-to-file.md`.

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
> | **Part D** (below) | The **process** — do you need collaborator access (no), who the maintainer is, upstream style/CI/responsiveness, and the ranked *PR* list as of 2026-07-07 |
> | **Part B** (above) | The **runbook** — fork/branch layout, re-merge discipline, and the two already-prepared patches |
> | [`scripts/cyanrip/`](../scripts/cyanrip/) | The **execution kit** — the canonical paste-ready issue/PR bodies, the verified patcher, the build script |
> | **Part A** (above) | The **long-horizon options** — fork/combine feasibility, licensing, the §10 per-gap menu |
> | This part (Part C) | The **ask list** — *what* we want changed in cyanrip, ranked, with first-party evidence and an honest audio-vs-record verdict per item |
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

### 0. The thing to be clear about before anything else

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

### 1. Where the asks come from — the labelled-cell census

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

### 2. The asks

Each block reads: **Gap → Evidence → Affects → The upstream change → Effort →
Route → Platterpus side.**

#### 2.1 ⭐ Print the sample peak — the field already exists and is dead

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

**⚠️ DO NOT OPEN AN UPSTREAM PR FOR THIS — two are already live** (reported by the
fork session, 2026-07-31; not independently corroborated here because the GitHub
API is not enabled for `cyanreg/cyanrip` in this session):

- **#116** (UltraFuzzy) — makes the identical one-line `ebur128=peak=true+sample`
  change, *plus* a direct `max(|sample|)` scan over the raw PCM. cyanreg pushed
  back specifically on keeping the less-accurate ebur128-derived value alongside
  the precise one.
- **#148** (nicosp, opened 2026-07-24) — explicitly "a simpler alternative to
  #116": reuses the precise-scan code and drops the ebur128 filter change
  entirely. This looks like the response to that review comment.

So the change proposed below is *the half cyanreg declined*. Keep it fork-local,
and rebase onto whatever upstream lands. **Flag early if #148's output is a
unitless linear amplitude** — our parser requires an explicit `dBFS` or `%` unit
and would refuse it (see the constraints below).

**Platterpus side — ✅ DONE (v0.5.19), waiting on the fork.** The reader is
already written and shipped, so a fork that prints this line fills EAC's row with
no further Platterpus change. *(Status 2026-10-19: delivered by the fork, not upstream. The pinned `.23` prints `    Sample peak level: %.1f%% (%.1f dBFS)` (`cyanrip@891c79e:src/cyanrip_log.c:574`), and our reader takes it.)* `parsers/cyanrip_log.py` accepts **two** shapes,
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

#### 2.2 Exact pre-gaps and INDEX 00 — carry PR #115, do not author a rival

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
(`docs/eac-parity.md`, `docs/session-log.md`, and the
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

**Route.** **Soft-fork carry + upstream support.** Carried on the fork's
`platterpus-fork` integration branch (the plan named a `feat/pregap` topic branch
and a `platterpus` branch; neither exists — `git ls-remote`, 2026-09-30). Do **not**
open a competing PR (soft-fork §3.1, §5).

**Platterpus side.** Essentially nothing — the `.cue` is consumed verbatim and
`pregap_sectors` is already parsed. **One exception, found while assembling this
(§6.3): our `Pre-gap length` formatting was wrong** (CD frames where EAC prints
hundredths of a second), and `eac_log_export._pregap_line` now renders hundredths.
It was latent only while no build reported pre-gaps; **the pinned fork now does**
(round 29's Full-run logs on `.18` carry `Pregap length:` and `Pregap source:`,
`docs/handshake/artifactsround29/`), while upstream `master` still does not (the
fork's mirror of it, at `f8ebf48f`, has no `Pregap source` line in `src/`).

---

#### 2.3 Per-track extraction speed and elapsed time

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

*(Status 2026-10-19: delivered by the fork, not upstream. The pinned `.23` prints `    Extraction speed:  %.*fx` and `    Elapsed:            %.2f s` (`cyanrip@891c79e:src/cyanrip_log.c:610-612`), and our reader takes it.)*

**Platterpus side — ✅ DONE (v0.5.19), waiting on the fork.** We already measure
and record whole-rip elapsed ourselves (`rip_timing.py` → the `timing` block in
`.platterpus.json`), so only the per-track row needs cyanrip — and the reader for
it is shipped. `parsers/cyanrip_log.py` reads **both halves** of what §2.3
proposes, from any of several plausible labels:

```
    Extraction speed:  1.6 X        # also: Rip speed / Read speed / Speed
    Elapsed:           193.18 s     # also: Elapsed time / Rip time /
                                    #       Extraction time / Time taken
```

The speed multiple fills EAC's `Extraction speed` row directly. The elapsed gets
its own field (`extraction_elapsed_seconds`, serialized in the JSON report from
schema v10) and a row of its own, rendered only when measured. **A scalar with a
unit only** — `s`/`sec`/`secs`/`seconds`. The `(HH:)MM:SS` clock rule was retired
2026-08-21: no cyanrip build has ever emitted it, and the fork's pre-split
combined form `Elapsed:  %s (%.1fx)` was refused by its end-of-line anchor. The
shipped build emits `Elapsed:  %.2f s`.

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

#### 2.4 Write the `-Z` convergence verdict into the log file — **verify before asking**

**Gap (candidate, unverified).** cyanrip's secure-re-read verdict — the line that
tells us whether a track's reads ever agreed — may be printed to stdout only and
**not** written into cyanrip's own `.log`. If so, a cyanrip log re-parsed from
disk later silently loses the strongest evidence in the whole rip.

**⚠ Correction to our own record — the question is settled, and against this
premise.** `Done;` was **never** stdout-only: `cyanrip_log()` writes the logfile
before stdout, so the line was always in the log at 0.9.3 and at `master` — it
was merely un-indented. The fork settled it from the source. The reasoning, and
the one-track-offset bug the false premise caused once the fork indented the
string in place, are recorded in `parsers/cyanrip_log.py` beside
`_TRACK_SECURE_VERDICT`.

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
"not confirmed reproducible" caveat (worded since 2026-10-05 by how many reads
agreed: `docs/eac-parity.md`, *The repeat-limit caveat*). The GUI is safe either way because it reads
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

*(Status 2026-10-19: delivered by the fork, not upstream. The pinned `.23` prints an indented `  Secure re-read:` row for every track (`converged after N reads`, `did NOT converge after N reads (repeat limit hit)`, `not attempted`) (`cyanrip@891c79e:src/cyanrip_log.c:629-637`), and our reader takes it.)*

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

#### 2.5 Say whether C2 was *used*, not only whether the drive supports it

**Gap.** cyanrip's header reports the drive's C2 **capability**. EAC's row asks
whether C2 was **used**. On the reference drive those coincide by luck; on a
C2-capable drive they do not, and the row goes back to unfillable.

**Evidence** (**read**, `src/cyanrip_log.c`, `cyanrip_log_start_report()`):

```c
"C2 errors:      %s by drive\n"
```

The substituted string is the libcdio SCSI capability bit
(`CDIO_DRIVE_CAP_READ_C2_ERRS` — see Part A §8). On the
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

*(Status 2026-10-19: delivered by the fork, not upstream. The pinned `.23` prints `C2 errors:      supported by drive, not used` on a C2-capable drive (`cyanrip@891c79e:src/cyanrip_log.c:927-928`), and our reader takes it.)*

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

#### 2.6 A cache-defeat report from the rip itself (low priority)

**Gap — partly delivered, and by the fork rather than upstream.** Upstream
cyanrip has no cache flag and emits no cache line at all. The fork has a cache
*probe* — `-x`/`--cache-probe`, from round 7 lap 1, long-only `--cache-probe` from `.23` — and emits `Cache probe:`
(its own measurement: a range, a bound, or an explicit unknown) alongside
`Cache model:` (paranoia's *modelled* size, renamed from `Cache defeat:` in round
6 because the old label asserted an outcome the value disclaims). Neither is a
cache-**defeat** verdict, so a log alone still yields `(unknown)` for EAC's
`Defeat audio cache` row. Its engine, libcdio-paranoia, *attempts* cache defeat
every rip (readahead exhaustion, plus FUA where the drive advertises it), but
nothing in cyanrip's output confirms it happened.

**Evidence** (**measured**): the committed 0.9.3 reference log's banner has no
cache-related row; the fork's two rows are registered in `parsers/cyanrip_log.py`
as *knowingly unparsed* — `Cache model:` because filling a measured field from a
modelled figure is the fabricated `Yes` KDD-25 forbids, `Cache probe:` because it
has no rendered home and is surfaced verbatim by `rig_check` instead. The
exporter therefore renders `(unknown)` rather than a fabricated `Yes` (KDD-25's
rule, which survived KDD-29 intact).

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

#### 2.7 The two already-prepared asks — pointers, plus one correction

Both are researched, patched and paste-ready; this file does not restate them.
Runbook: Part B §2 and §3. Paste text:
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
  cyanrip has any long-option parsing at all before proposing one). *(Answered
  2026-10-19: it has, on `master`. genopt, which replaced getopt after 0.9.3,
  registers every option as `--<field name>` with `_` read as `-`
  (`cyanrip@b40c1f0:src/genopt.h:160`, `:472-479`), so `--acoustid-key` exists
  beside `-k` and a long-only option is possible. 0.9.3.x, on getopt, has no
  long options.)* The kit
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

### 3. Closed — asks we are **not** making, and why

A list that only grows is less useful than one that also closes items.

#### 3.1 `Track quality` — no ask, ever

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

#### 3.2 `Utilize accurate stream` — no ask

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

#### 3.3 AccurateRip under `-l` (subset rips) — **NOT a gap; confirmed working**

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

#### 3.4 A literal two-pass Test & Copy — no ask

`-Z N` (re-read until N+1 reads are identical) is a stronger real-world guarantee
than EAC's two fixed passes, it already exists, and KDD-30 already renders its
convergence as an EAC-style Test/Copy pair. A whole-second-pass mode would double
rip time for less assurance. The live question the maintainer raised on 2026-07-30
— *should* `-Z` become the default when AccurateRip has nothing to say about a
disc? — is a **Platterpus defaults decision**, not a cyanrip change.

#### 3.5 Tracker-log recognition — no cyanrip ask can fix it

The logcheckers gate on ripper **identity** before reading a single quality line.
No amount of cyanrip log improvement changes that, and forging identity is
refused. Full analysis: `docs/eac-parity.md`.

---

### 4. Start here — the ranked recommendation

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

#### The single best first contribution: **the sample peak (§2.1)**

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

### 5. What we would need from the maintainer

Nothing here is code — these are decisions and rig time, in rough priority order.

1. **A go/no-go on opening upstream issues + PRs at all**, and under whose
   GitHub identity. Everything in §4 is a public contribution to someone else's
   project. *(Decision. Blocks all of §2.)*
2. **An environment that can reach `cyanreg/cyanrip`.** This session is scoped to
   `rmccann-hub/platterpus`; it cannot fork, build C, open issues, or run a smoke
   rip. Execution needs a local checkout or a cyanrip-seeded session, plus the
   `ripping` container for the build. *(Environment. Blocks all of §2 —
   already recorded in Part A §0.)*
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

### 6. Corrections to our own record, found while assembling this

Recorded here rather than silently fixed, because two of the three are in
documents another session may be editing and one is in a `CHANGELOG` entry.

#### 6.1 EAC lists `Pre-gap length` for **ten** tracks, not fourteen

Wrong in three places: `docs/eac-parity.md` (Part A, pregap
table and the surrounding prose), `docs/archive/session-log-to-2026-10-15.md` (2026-07-30 entry, *"EAC
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

#### 6.2 The quoted `REPLAYGAIN_TRACK_PEAK` value does not exist in the repo

The evidence briefing cited a captured peak of **`1.058659`**. That string
appears **nowhere** in this repository. The closest committed value is
**`1.058175`** (track 3, in both the FLAC and MP3 reference logs) — presumably a
different hardware run.

**The claim it was supporting is correct and provable from committed evidence, so
use these numbers instead:** all fourteen tracks exceed 1.0, ranging
`1.008499`–`1.097464`, against EAC's fourteen sample peaks of ≤ 98.8 %. Fourteen
values over full scale is a much stronger argument than one, and every one of
them is in a committed file.

#### 6.3 Our `Pre-gap length` formatting is probably wrong (latent)

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

### Appendix — what was read this session, and what was not

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

*Companion to **Part D below** (process + the
2026-07 ranked PR list), **Part B above**
(runbook + prepared patches), [`scripts/cyanrip/`](../scripts/cyanrip/)
(execution kit), and
[`eac-parity.md`](eac-parity.md)
(the external standard these rows are measured against). PR-first, adaptable to
the upstream maintainer's call, and we never fake provenance.*

---

### 7. Asks from the 2026-11-25 audit

**What this is.** The audit of 2026-11-25 (`docs/eac-parity.md` Part H) re-read EAC parity
against round 42 and surveyed seventeen other rippers. These are the items it found that
are the fork's to do or to answer, each with the reason. The fork is its own repository,
so this list is handed over as a file and the fork decides what to take; nothing here is a
handshake statement until a lap carries it. Where the fork already tracks the item, its id
from the fork's `docs/OPEN-ITEMS.md` is named, read at `cyanrip@e665c9b4`.

| # | Ask | Why | The fork's id |
|---|---|---|---|
| F1 | **When a pregap is undecided, make the cue agree with the log.** All 14 round 42 whole-disc rips print track 9 as `94 or 95 frames (undecided)`, and every cue writes `INDEX 00 03:44:10`, 95 frames. All four EAC sessions read 94, and the fork's own count puts 94 in the majority (200 of 237 filed logs). Either write the value the record can stand behind with a `REM` saying it is undecided, or leave the `INDEX 00` out and say so, and name the rule that picks it | A cue that commits to a value the log calls undecided asserts what the record refuses, and it is the one cue line that differs from EAC's on this disc. Our half, the `Gap handling` row, is R219 | HW-6, US-12 |
| F2 | **A second try, by another method, when the sub-channel search is undecided** (EAC's gap detection methods A, B and C, retried on failure) | Track 9 is undecided in nearly every rip on this drive; a second method is how EAC reaches one answer | US-12 |
| F3 | **Print both pre-emphasis sources, and say when they disagree.** The track block names one, `present (subcode)` or `present (TOC)` (`cyanrip@e665c9b4:src/cyanrip_log.c:699-715`) | Hydrogenaudio users ask for it and say CUERipper lacks it ([HA thread](https://hydrogenaudio.org/index.php/topic,127761.msg1062237.html)); a disagreement is a fact about the disc an archive should keep | new |
| F4 | **Detect HDCD without decoding it**, as a reported flag with no sample change | dBpoweramp, EZ CD, fre:ac and CUETools flag HDCD; `-H` decodes, and the fork's own record shows it delivers a file 6.02 dB quieter on a disc without HDCD. We plan to run ffmpeg's `hdcd` filter over the finished FLAC (R202); a flag from the read would be simpler and would come from the source | new |
| F5 | **Lock the tray while a rip runs** (SCSI PREVENT ALLOW MEDIUM REMOVAL), released on every exit path | EAC does it; a tray opened mid-rip cost a Full run 57 steps once (our Part F row 33). No lock was found in the fork's source; the fork holds the drive, so it is the cheaper side (our R223) | new |
| F6 | **Fix `-f`'s two defects before we wire it** (it never tries an offset of 0, and it numbers tracks by position) | We are about to make `-f` the drive-setup offset for any drive AccurateRip does not list (R150, parity with the key-disc calibration of EAC, dBpoweramp and two Linux rippers). A drive whose true offset is 0 would get a wrong one | UP-4, HW-2 |
| F7 | **A provider-contract row for the `CD-TEXT:` lines: their fields, their character set, and their stable form** | We will use CD-TEXT as fallback tags when MusicBrainz has no match (R206, parity with EAC, abcde, dBpoweramp, fre:ac, K3b). The fork has not read CD-TEXT from a disc on a drive yet | HW-4 |
| F8 | **Re-reading only the sectors in doubt, voted per sector**, kept on the long list | dBpoweramp, EAC, XLD and Rubyripper do it, and it finishes a damaged disc sooner; our side is R134 (rebuild a disputed second) | US-13 (R5) |
| F9 | **Refresh the fork's parity rows 6, 21 and 23 with round 42**, and read our corrections in Part H.2 so the two parity files agree | Round 42: track 3 read right in 13 of 14 whole-disc rips, track 9 undecided in 14 of 14, `Recordable:` printed | — |
| F10 | *For the record, not asked now:* FUA cache invalidation (dBpoweramp; speed only), C2 pointers as evidence after a trust test (speed more than accuracy; the round 42 C2 probe is the record), and flagging a manipulated TOC (EAC; low, our R222) | Recorded so they are not found again as new | — |

**From the review of both repositories' file layout (2026-11-25).** Each is a cheap move on
your side; our cost is none unless it says so. Read at `cyanrip@a06c8de`.

| # | Ask | Why |
|---|---|---|
| F11 | **Move `JOINT-SCRIPT-RUNBOOK.md`, `ROUND-22-PLAN.md` and `DEPENDENCY-PLAN.md` into `docs/history/`**, with rows in its README | Your `docs/README.md` already classes all three as history and their banners say finished or superseded; your cost is one comment in `src/cyanrip_main.c`, three tool and test references, and the living docs that name them |
| F12 | **Move `cyanrip@a06c8de:docs/upstream-cachemodel-report.md` into your upstream folder** | Every other upstream filing is there, and it was filed as upstream issue 167 |
| F13 | **Move `docs/research/` (three files) into `docs/history/`** | It fixes three broken links in `cyanrip@a06c8de:docs/history/2026-11-04-misreads-and-pregaps.md:11-14`, which point at siblings that are not there, without editing a history file |
| F14 | **Consider grouping the 61 `docs/rig-*/` folders under one parent** | 61 of about 89 entries in your `docs/`. The cost is real on both sides (your tools, `SOURCES.tsv`, the evidence manifest keyed by path, and 94 of our files with unpinned citations), so we accept "no"; half the runs moved and half not would be worse than either |
| F15 | **`PROPOSAL-operator-seam-automation.md`, byte-identical in both trees: archive it unchanged on both sides in one round, or confirm it stays** | Its open part became your `upstream/carried-patches.md`; our half is R243 |
| F16 | **At the next protocol version, move `PROTOCOL.md`'s change history (§10 to §18, about 550 of 1,815 lines) to an appendix**, the §8 conformance table unmoved | Readers of the binding text page through history; shared file, so it rides a version both sides ship |
| F17 | **EAC parity: one authority per row.** Your file keeps the facts the fork owns (what `-r` bounds, accurate stream, CD-R detection, extraction speed) and for rows 6 and 21 cites `OPEN-ITEMS.md` HW-6 and the rig READMEs; we cite your rows by `cyanrip@<sha>` instead of restating them | The two files have drifted on row 6; this goes with F9 |

**Already on round 43's list, not repeated here:** our answer to US-21 (we will read
`Pregap sample peak:`, R227), the `?` cell at `docs/seam-commands.md:261` (PP-12, our
R228), the two proposed seam rules (R229), and the addendum's time (PP-14, our R226).

---

## Part D — The upstream PR roadmap (contributor instructions)

## Upstream-PR roadmap (contributor instructions)

> **Update (2026-07-24, KDD-32 — fork is now the committed INDEX-00 mechanism):**
> the maintainer directed that the soft-fork be the path for the upstream fixes
> Platterpus needs, with the **EAC INDEX-00 pre-gap gap** as the driver. Order 1
> below (support cyanrip **PR #115**) is unchanged as the *action*, but the fork
> is no longer merely "prepared": the `ripping` container will **build cyanrip
> from the `platterpus` integration branch** (`master` + our topic branches; named `platterpus-fork` in the fork)
> instead of the 2-year-old v0.9.3.1 COPR tag — which alone yields INDEX-00 cue
> metadata (`master` already emits it) and carries PR #115 for exact pregaps +
> HTOA. See PLANNING **KDD-32** and Part B §3.1 + §4.

> **Update (2026-07-08, soft-fork decision):** two prepared, higher-readiness
> cyanrip contributions now exist *alongside* this ranked list — the `-a`/`-t`
> **meta-colon parsing fix** (⭐ do first; verified patch + ASan/UBSan proof)
> and **full libavcodec encoder options**. Runbook:
> Part B of this file; one-command execution kit:
> `scripts/cyanrip/` (paste-ready issue/PR bodies live there).

> **What this is.** The concrete, *ordered* answer to "which upstream pull
> requests would close our remaining ripper-engine gaps, in what order, and how
> do I do each one." It turns the per-gap option menu in
> Part A §10 into a ranked
> action list with step-by-step instructions. **PR-first policy** (the
> maintainer's standing rule): we open a pull request from our own fork and are
> *adaptable* to the upstream maintainer's merge decision — a fork we maintain is
> the fallback, never the goal. The **signed EAC log checksum is permanently out
> of scope** — it is forgery of another tool's provenance and we do not fake
> anything (Critical rule spirit; `docs/eac-parity.md`).
>
> Sourced from a 4-agent research sweep (2026-07-07) of cyanrip, the previous
> backend, OPSnet/Logchecker, libcdio-paranoia and cdrdao. Findings are point-in-time
> (read off public GitHub pages — the GitHub API here is scoped to this repo);
> **re-check live state before investing build/test time.** Uncertainties are
> flagged inline.

---

### Filed, and the next notes held until upstream takes the first (2026-11-03)

**Filed:** items 1 to 23 of the fork's generated list went upstream on 2026-10-16,
by the owner, as one issue, <https://github.com/cyanreg/cyanrip/issues/167>. **The
owner's rule, 2026-11-03:** *"we sent notes before. You can give details for the
next notes to send, but we will wait for the old ones to be included"*. So nothing
more is filed until upstream has taken #167's items in; what follows is the next
batch, ready, and filed by the owner when that happens.

**Ready (the fork's list, items 24 to 28,** generated in the fork's
`cyanrip@239adda:docs/upstream/issues-to-file.md` by `tools/gen-upstream-issues.py`, each with a
reproduction, read against upstream `master` at `648b1dd` and the fork's fix):

| Item | Title | Fork's fix |
|---|---|---|
| 24 | An argument that is only its separator crashes with no message (`-c /`, `-p =`, exit 139) | `58f5151` |
| 25 | A number past `INT_MAX` wraps and is used (`-c`, `-p`, `-P`, `-R`, `-C`, `-t`) | `716a99b` |
| 26 | The AccurateRip tally divides by a count that includes data tracks | `779549a` |
| 27 | A value the log echoes can start a line of its own (a newline or U+0085 in a tag) | `46cec2a` |
| 28 | A path over 1,003 bytes is cut there, extension and all (`AV_BPRINT_SIZE_AUTOMATIC`) | `cfd738e` |

**Candidates from the Full run of 2026-11-03, not yet ready.** Each goes on the
list only once the fork confirms it holds on upstream's own code, not only on the
fork's (`docs/cyanrip-handshake.md` §7.7e: an upstream defect is the easiest to
misattribute, because the fork is the binary in front of us). Asked in our round 37
lap 6 S12.

- **The footer's tally counts the whole disc on a rip of some tracks.** `-l 1`
  prints `Tracks ripped accurately: 1/14`. Upstream's line is the same one:
  `cyanrip_log.c:366` at `648b1dd` divides by `ctx->nb_tracks`. Item 26 covers data
  tracks only; this is its other half.
- **`-H` on a disc without HDCD writes quieter audio under a CRC taken before the
  filter.** Track 1 peaked at -6.3 dBFS with `-H` against -0.5 dBFS without, with
  the same CRC and `accurately ripped`. Upstream has the same filter path
  (`cyanrip_encode.c`); the fork is asked whether libavfilter's `hdcd` output level
  is the cause.
- **A cancelled rip counts the cancel as a ripping error** (`Ripping errors: 1`).
  Not yet traced in upstream's source.

Not for upstream: `Track N read with errors.` beside `Ripping errors: 0` is the
fork's own securing-pass wording (no such line at `648b1dd`), and the cue's missing
`INDEX 00` for an undecided pregap comes from the fork's pregap search; both are
asked of the fork (round 37 lap 6 S11 and S12).

### The one question you asked first: "do I need to be a collaborator?"

**No.** For *every* target here you do **not** need collaborator / write access.
The standard open-source flow is:

1. **Fork** the upstream repo (click *Fork* → it lands under your account,
   `rmccann-hub/<repo>`).
2. **Push a topic branch** to *your* fork.
3. **Open a pull request** *from* your fork's branch *into* the upstream repo.

The upstream maintainer (cyanreg, rocky, itismadness, …) reviews and merges it.
That is exactly how every external cyanrip contributor (jp-sarte, UltraFuzzy,
nicosp, abrasive, …) submits. **Collaborator/write access only matters for repos
you already own or are invited to co-maintain** — it lets you push branches
straight into the upstream repo and click *Merge*. You never need it to
*contribute*, and it is not on offer here. Being added as a collaborator would
only matter if you wanted to *co-maintain* a project, which none of this
requires.

Rare exceptions (none block the work actually recommended below):
- **Pure GNU/Savannah projects** take patches by mailing list (`git
  format-patch`), not GitHub PRs. *libcdio-paranoia is mirrored on
  github.com/libcdio with a live PR tab and accepts normal GitHub PRs*, so it is
  **not** mailing-list-only — the `libcdio-help` GNU list is optional discussion.
- **SourceForge-hosted** projects use their own merge-request flow — not
  applicable to any target here.
- **DCO sign-off / CLA:** some projects require `git commit -s` or a CLA — none
  of the four targets here documents one (cyanrip has no `CONTRIBUTING.md` at
  all; the convention is "match the surrounding C").

---

### The ranked list at a glance

| # | Gap | Where | Verdict | Effort | Odds |
|---|-----|-------|---------|--------|------|
| — | **gap / INDEX-00 pregap + HTOA** | **Platterpus-side `cdrdao` integration** | **Fallback if #115 stalls** (see the 2026-07-07 update box) | Moderate | N/A — lands in our repo |
| 1 | exact pre-gap *detection* + HTOA | cyanrip **PR #115** (UltraFuzzy, open) | **Support the existing PR** | Low (test + review) | Medium-good |
| — | `INDEX 00` / `PREGAP` **cue reporting** | **already merged upstream** via **#104 / #118 / #122** | Nothing to do — `master` has it | N/A | Done |
| 2 | stable machine-parseable cyanrip log | cyanrip (new PR) | Do only if committing to #3 | Moderate-hard | Low value |
| 3 | tracker recognizes cyanrip | OPSnet/Logchecker (new PR) | **Skip for now** | Hard (2-repo) | Low |
| 4 | C2 error pointers (+ cache-defeat line) | libcdio-paranoia → cyanrip | **Skip** (keep deferred) | Hard (2-repo) | Very low |
| — | tracker recognition via a recognized ripper | **Re-add the previous backend (Platterpus-side)** | Fallback, hardware-gated | Moderate | N/A — no PR |

The single highest-value *action* (revised 2026-07-07 — see the update box
below) is **supporting cyanrip PR #115** (Order 1). The un-numbered top row —
the **cdrdao integration, a Platterpus task, not a contribution** — closes the
same two gaps with zero upstream dependency, but it is now the
**no-upstream-dependency fallback** kept for if #115 stalls indefinitely, not
the first move.

---

> **Source-grounded update (2026-07-07 — cloned the cyanrip repo + fetched PR
> #115's head).** This reorders the pregap/HTOA priorities below:
> - **cyanrip `master` already handles pregaps from the TOC** — `enum
>   cyanrip_pregap_action {DEFAULT,DROP,MERGE,TRACK}`, `-p <track>=<action>`,
>   it *synthesises* a track-1 pregap when it sees an unmarked lead-in↔track-1
>   gap, and `cue_writer.c` already emits `INDEX 00`/`PREGAP`/`INDEX 01`. It also
>   merged **PR #127** (cdrdao TOC/bin support) already. So we likely already
>   *receive* most INDEX-00 cue metadata from cyanrip — **check what cyanrip's
>   own `.cue` contains before building anything.**
> - **The accuracy gap (exact pregaps + true HTOA) is PR #115** (UltraFuzzy,
>   **open** since 2025-09-27, rebased 2025-11-28): adds `src/pregap.c`
>   (+483) + `pregap.h`, wired in by a **one-line call-site swap**
>   (`cdio_get_track_pregap_lsn` → `cyanrip_get_track_pregap_lsn`). It reads
>   Subchannel-Q via MMC — the thing the TOC can't give. Its blockers are a
>   leftover `// remove after testing` `assert.h` block and a macOS
>   private-libcdio-struct hack (wants `cdio_get_device_fd()`).
> - **Therefore the honest priority is to help land #115, NOT to build a
>   parallel Platterpus cdrdao path.** #115 delivers HTOA/INDEX-00 natively
>   through the sanctioned `~/.local/bin/cyanrip` with no Platterpus subchannel
>   code; a cdrdao integration duplicates it and adds a dependency. Keep the
>   cdrdao option below only as the fallback if #115 stalls indefinitely.
> - **License constraint:** cyanrip is **LGPL-2.1-or-later**; Platterpus is
>   GPL-3.0. Any code contributed *into cyanrip* must be LGPL-2.1+ (never paste
>   GPL-3-only Platterpus code upstream). Calling the LGPL binary as a subprocess
>   is unaffected.
> - **CTDB is confirmed Platterpus-only** — cyanrip has *zero* CTDB code
>   (AccurateRip-only); our `crc.py` fix is the whole story, no cyanrip PR.
> - **Process (canonical home for the upstream-process facts — the strategy
>   doc §6 and the soft-fork runbook link here):** maintainer **Lynne
>   "cyanreg" `<dev@lynne.ee>`**; IRC `#cyanrip` on Libera.Chat (sanity-check
>   before coding); no `CONTRIBUTING`/tests; terse `av_`-prefixed FFmpeg-idiom
>   C — match the surrounding style; only CI is a Windows/MinGW build —
>   **don't break it**. Responsiveness: external PRs do merge, slowly
>   (jp-sarte's #130 landed ~3.5 months out; some PRs sit 1–2 years; #115 is
>   open and actively reviewed). The two non-default branches
>   (`accurip_test`, `deemphasis`) are dead/superseded — ignore them.

### DO-LATER / FALLBACK (no upstream PR) — cdrdao integration for pregap/INDEX-00 + HTOA

**Reconsidered (see the update box above): prefer landing cyanrip PR #115 over
this.** Keep this only as the fallback if #115 stalls. It is not a contribution —
it lands entirely in Platterpus. cdrdao is GPL-2-only, but we invoke every tool
as a **subprocess** (never link it — KDD-10's aggregation model, routed like every backend subprocess per Critical rule #3), so GPL-2-only is fully
compatible with our GPL-3.0 GUI. This is *exactly how the previous backend obtained gaps.*

- **What it does:** run `cdrdao read-toc` to scan the Q sub-channel for pre-gap
  lengths + index marks → a `.toc` file (`toc2cue` converts to `.cue`); parse it
  for pregap / `INDEX 00`. HTOA (hidden track-0 audio) lives in the track-1
  pregap that `read-toc` detects, so this unblocks HTOA too.
- **Where it lands (Platterpus only):**
  - Route cdrdao through the **single dependency self-management subsystem**
    (Critical rule #6 — no ad-hoc availability check).
  - Add a thin `RipBackend`-adjacent adapter that shells out to `cdrdao
    read-toc`, plus a **never-raise** `.toc` parser with a `hypothesis` property
    test (`docs/testing.md`).
  - Document the exact args/flags/output shape in
    `docs/dependency-contracts.md`.
  - Run `read-toc` on a **worker thread** — its linear Q-subchannel scan takes
    roughly a full audio pass and must never block the GUI thread.
- **Caveats to encode:** `--fast-toc` *skips* gap/index extraction (yields only
  nominal 2 s pregaps — not what we want); the Plextor binary-search fallback is
  "usually not very reliable"; behavior is drive-dependent → validate on the
  Bazzite + Pioneer BDR-209D rig. cdrdao is healthy (v1.2.6, 2025-12-05).
- **Verdict:** the only gap of the set that needs *no* upstream PR, uses a proven
  approach, is bounded to our code under existing patterns, and moves the "good
  everything" north star. **The honest framing: this is an integration task, so
  no "collaborator" question even arises.**

---

### Order 1 — support cyanrip PR #115 (don't open a competing PR)

- **Gap:** gap/INDEX-00 pregap detection **and** HTOA — two of six gaps, both
  addressed by one *existing, live* PR.
- **Target:** `github.com/cyanreg/cyanrip` **PR #115** by *UltraFuzzy* — adds
  `src/pregap.c` + `src/pregap.h`; **open**, cyanreg actively reviewing (he asked
  UltraFuzzy to split platform code into `pregap_internal_osx.c` vs
  `pregap_internal_mmc.c` instead of `#ifdef`s).
- **What you do:** you do **not** author a fresh PR. The highest-value move is to
  **engage with #115** — real-hardware test it on the BDR-209D, review it, help
  it over the finish line. That is exactly what an actively-reviewed-but-slow PR
  needs (the strategy-doc §6 responsiveness gauge concluded 2026-07-08:
  cyanreg merges external work, slowly — hardware-testing #115 would add a
  first-hand data point).
- **Odds:** medium-good — the PR is alive and maintainer-reviewed. cyanreg *does*
  merge external work, just slowly (jp-sarte's #130 merged ~3.5 months after
  opening; some PRs sit 1–2 years).
- **Steps:**
  1. You don't need a fork just to test. Inside the `ripping` Distrobox
     container: `git clone https://github.com/cyanreg/cyanrip && cd cyanrip`
     then `git fetch origin pull/115/head:pr115 && git switch pr115`.
  2. Build: `meson setup build && ninja -C build`.
  3. Smoke-rip a disc with a **known pregap** and, if you have one, an **HTOA**
     disc. Capture the **log + per-track CRCs** — text artifacts only, **never
     audio** (Critical rule #8).
  4. On the PR page, post your build result + BDR-209D hardware-test outcome.
     This is genuinely wanted signal.
  5. If you find a bug, offer a fix as a suggestion/commit against the PR branch
     (coordinate with UltraFuzzy) — *not* a rival PR.
  6. Be adaptable to cyanreg's merge decision and his osx/mmc split request.
  7. **Do not let this block you** — the cdrdao integration above gives the same
     two gaps *now*, independent of #115 landing.
- **Release caveat:** cyanrip's last *tag* is v0.9.3.1 (~2 years old) though
  master moves. If #115 merges you'd consume it from **master** in the `ripping`
  container, not a release tag — an explicit maintenance choice to make, not an
  automatic win.

---

### Order 2 — a stable, machine-parseable cyanrip log (only if you commit to #3)

- **Gap:** the prerequisite half of tracker recognition — cyanrip has no stable,
  documented, versioned log schema a logchecker could reliably key on.
- **Target:** `github.com/cyanreg/cyanrip` (a **new** PR you'd author in
  `cyanrip_log.c`).
- **Difficulty:** moderate-hard (C; must design a format cyanreg accepts *as a
  stable contract* and commit to keeping it stable). Even if it lands, cyanrip
  structurally can't emit several fields the tracker scorer rewards (no
  cache-defeat line, single-pass so no Test&Copy CRC pair, no native gaps
  pre-#115) — so recognition ≠ a competitive score.
- **Odds / value:** low value on its own — it only pays off if Order 3 also
  lands (it likely won't). Uncertain cyanreg would even want to freeze a log
  schema.
- **Recommendation:** **skip for now.** Only pursue if you genuinely commit to
  the whole tracker chain.
- **Steps (if pursued):** *first* ask cyanreg on IRC (`#cyanrip` on
  Libera.Chat) or an issue whether he'd accept a stable, versioned,
  machine-parseable log block — do **not** build it before he signals appetite
  (releases are stalled; don't waste work). If yes: fork, branch, add it in
  `cyanrip_log.c` matching surrounding C style, document it, build (meson/ninja)
  + test, open the PR from your fork, expect weeks-to-months + rebases, accept
  his format shape.

---

### Order 3 — add cyanrip to the OPSnet/Logchecker allow-list

- **Gap:** the allow-list half — the OPS/Orpheus logcheckers gate on a *known
  ripper name*; cyanrip isn't on the allow-list so it auto-scores 0.
- **Target:** `github.com/OPSnet/Logchecker` (PHP, Unlicense; = composer
  `orpheusnet/logchecker`, shared by OPS + Orpheus).
- **Scope:** (1) `src/Check/Ripper.php` — add a `CYANRIP` const + a `getRipper()`
  match on a stable cyanrip log line; (2) a whole new parse/score path in
  `Logchecker.php` analogous to `whipperParse()`/`legacyParse()` mapping
  cyanrip's fields (drive, read offset, cache-defeat, Test&Copy CRC, gaps,
  AccurateRip) to the score model.
- **Difficulty:** hard in aggregate — **depends on Order 2 existing first**, then
  a full scorer path. A two-repo coordinated effort.
- **Odds:** **low.** The analogous request *"Add CUERipper support"* (issue #13,
  opened 2021-06-16) has sat **open with zero maintainer response for ~5 years** —
  the single most relevant acceptance signal, and it's bad. Maintainer
  *itismadness* is active on version bumps but unresponsive to new-ripper asks.
  It also benefits **only** OPS+Orpheus — RED runs a separate, non-public checker
  behind the permanent signed-EAC-checksum wall (forgery — never), so this never
  helps RED.
- **Recommendation:** **skip for now.** Two-repo effort against a maintainer who
  ignored the equivalent request for 5 years, cyanrip can't score competitively
  anyway, and it serves only two trackers. If ever pursued, PR-first per policy,
  expect a stall, and treat **re-adding the previous backend** (below) as the honest fallback.
- **Steps (if pursued):** *first* comment on issue #13 (or open a fresh issue)
  proposing cyanrip support and gauge the response — the responsiveness signal is
  the whole risk. Only if the maintainer engages: fork, branch, edit
  `Ripper.php` + `Logchecker.php`, run `composer test` / `composer lint` /
  `composer static-analysis` (phpunit/phpcs/phpstan, PHP 8.1+), verify with the
  `analyze` command on a real cyanrip log, open the PR from your fork, be patient
  (or walk away to the re-add fallback below).

---

### Order 4 — C2 per-sector error counts *(the cache-defeat half shipped in v0.5.8 — KDD-29 — and needed no upstream change)*

- **Gap:** report EAC-style C2 status/counts. libcdio-paranoia deliberately
  *ignores* C2, even though libcdio's own MMC layer can already read it.
- **Target:** a **two-project chain** — `github.com/libcdio/libcdio-paranoia`
  (C2 read-path + new public API) **then** `github.com/cyanreg/cyanrip` (emit the
  log line).
- **What it does:** (1) libcdio-paranoia: switch the paranoia read path to the
  C2-enabled read (`mmc_read_cd()` already takes a `c2_error_information` param in
  libcdio), accumulate per-sector C2 counts, add a **new public API** (e.g.
  `cdio_paranoia_get_c2_errors()`) exported via `libcdio_paranoia.sym`. (2)
  cyanrip: call the new API and emit an EAC-style C2/defeat log line. Platterpus
  then parses it.
- **Difficulty:** **hard** — driver-level C interop; adds public API surface to a
  stable ~once/year library; must not regress the paranoia algorithm (whose
  entire premise is working *without* C2); drive-dependent → needs multi-drive
  hardware validation; coordinated across two upstreams before we benefit.
- **Odds:** **very low.** The exact request is libcdio-paranoia issue #3
  *"Feature request: use C2 pointers"*, **open since 2015-05-02 with zero
  comments** — an 11-year signal of a deliberate design stance. And per
  strategy-doc §8 the BDR-209D reports **"C2 errors: unsupported by drive"** — so
  even a perfect C2 path yields *nothing on your own hardware*. C2 is a *speed*
  optimization at equal correctness; bit-perfection is already proven by CRC32 /
  AccurateRip / CTDB.
- **Recommendation:** **skip — keep deferred.** Highest-effort, lowest-acceptance
  item of all six gaps; pointless on your own drive; and it's a trust *signal*,
  not proof of correctness. Revisit only if a maintainer signals interest on #3
  *or* a C2-reporting drive is in hand.
- **Steps (if ever revisited):** comment on #3 to test appetite *before* any
  code; only if positive, fork libcdio/libcdio-paranoia, work in `lib/paranoia/`
  (the exact file — `p_block.c` vs `paranoia.c` — is **inferred from the dir
  listing, not confirmed line-by-line; treat it as a starting map**), build
  (autotools/M4), validate on multiple **C2-reporting** drives (not the BDR-209D),
  open the PR; only after it merges, open the downstream cyanrip PR.

---

### The honest tracker fallback — re-add the previous backend (Platterpus-side, no PR)

**If tracker acceptance ever becomes a real goal, this — not Orders 2+3 — is the
honest path,** and it needs **no upstream PR at all**:

- The previous backend's **native YAML rip log** (the format Platterpus still
  reads as the *legacy log format*) **is already a first-class recognized +
  scored format** in `orpheusnet/logchecker`: `Ripper.php` matches `"Log created
  by: whipper"` and `Logchecker.php` has a full `whipperParse()` (their
  identifiers, quoted verbatim). So tracker recognition via that backend is
  **purely a Platterpus-side second `RipBackend` adapter** that runs it and keeps
  its native `.log`. The
  `RipBackend` ABC seam (`adapters/rip_backend.py`) anticipates this — a
  `Config.ripper_backend` selector existed while both backends shipped, was
  removed with the previous backend (2026-06-30), and would return with a second engine
  (strategy-doc §0).
- **Hard blocker for your own hardware:** the previous backend orchestrates
  cd-paranoia, which carries the **>587-sample read-offset bug** that *failed*
  tracks on the BDR-209D (+667 offset) — the exact bug that drove the switch to
  cyanrip (KDD-18). So re-adding it is gated on a cd-paranoia offset fix or a
  different drive, independent of tracker recognition.
- **Verify before relying on it:** run `orpheusnet/logchecker`'s `analyze` on an
  actual native `.log` from the previous backend at ≥0.7.3 to confirm the recognition claim (it's from
  reading their source, not an empirical run this session).

**Do NOT** pursue issue #7 on the previous backend's EAC-logger plugin (linked
in Part A §9) — it asks to implement
EAC's real proprietary log signing so the log passes EAC's checksum validator.
That *is* the signed-EAC-checksum forgery we permanently rule out, and it's
unnecessary because the previous backend's native-YAML path already yields a recognized log.
Neither consume nor contribute to it.

---

### Verify-before-you-invest checklist (uncertainties, honestly flagged)

Everything above is point-in-time. Before spending build/test hours:

- [x] **cyanrip PR #115** — **re-verified 2026-07-21: still OPEN**, titled *"Add
      pregap detection for physical CDs."* Latest activity 2025-11-28 (UltraFuzzy
      force-pushed); cyanreg's last substantive review (2025-10-02) asked for the
      code to be split into platform-specific files (`pregap_internal_osx.c` for
      the APPLE path + a separate MMC file behind a shared header) — so it's
      alive but mid-revision, not merge-ready. Consuming it still means building
      from a branch, not a release.
- [x] **libcdio-paranoia #3** — **re-verified 2026-07-21: still OPEN, zero
      comments** (titled *"Feature request: use C2 pointers"*, opened 2015-05-02).
      A second independent live read of the issue page, consistent with the
      earlier two; the GitHub API for non-Platterpus repos is still unreachable
      from this session, so this remains page-read-confirmed, not API-confirmed.
- [ ] **C2 "where in code"** (`p_block.c` vs `paranoia.c`) is inferred from the
      directory listing — a starting map, not a confirmed patch site. *(Still
      needs a source read; not re-checked 2026-07-21.)*
- [ ] **Order 2 appetite** — whether cyanreg would freeze a stable log schema is
      unknown; gauge on IRC/an issue before building. *(Human/maintainer-contact
      step — can't be verified from a session.)*
- [ ] **Previous backend's native-YAML log → Logchecker recognition** — re-verify
      empirically with the `analyze` command before relying on it as the
      fallback. *(Needs a local run of the previous backend + Logchecker —
      hardware/tooling-gated.)*
- [x] **cyanrip release cadence** — **decided and executed (KDD-32,
      2026-07-24).** Upstream's last tag is still 0.9.3.1 (Jun 2024) and it no
      longer gates us: the `ripping` container builds the fork from a **pinned
      commit** (`deps/fork_source.py` → `FORK_PIN`, `fork_build_commands`),
      installed over the COPR package, with `platterpus --install-ripper` as the
      out-of-release route because the pin moves faster than we ship. Nothing
      left to tick.

---

*Filed 2026-07-07. Companion to Part A §10
(the per-gap option menu) and [`github-workflow-sop.md`](github-workflow-sop.md)
(the fork + PR mechanics). PR-first, adaptable to the maintainer's call, and we
never fake provenance — the signed EAC checksum stays permanently out of scope.*

---

## Part E — Known issues handed to the fork, outside the handshake (CLOSED 2026-08-15)

## Known issues for cyanrip — from Platterpus, outside the handshake

> ### ⚠ CLOSED, 2026-08-15 — do not read this as a live list
>
> **All ten findings are dispositioned.** The fork acted on the whole document:
> **§2 is STRUCK** (we reported a defect that had been fixed at `8499890` before
> we wrote it), and the other nine were real and are all fixed. Two of our
> proposed remedies — §4a and §5 — would not have worked, and the fork said which
> half of each it accepted.
>
> **Three of them were fixed *after* the round-8 pin, so at `ddf7ac3` they were
> still open:** §7, **§8** and §9. The fork delivered all three in round 9 lap 1
> — "Ten defects fixed since `ddf7ac3`, eight from your known-issues hand-off"
> (`docs/handshake/inbound/round-09-lap-01.md:207-220`) — and the pin has moved
> many times since; every later pin carries those three fixes. The current pin is
> not repeated here: it is `FORK_PIN` in `src/platterpus/deps/fork_source.py`, and
> Help → About Platterpus… shows it. The
> round-8 disposition table and the round-9 asks are in
> `docs/handshake/verified/round-08-lap-10.md` §C and §O. **§8 is also now
> detected on our side** (`platterpus.cue_validate`, finding
> `cue_index00_orphaned`).
>
> **Why this file is kept rather than deleted:** each finding's evidence — the
> cited artifacts, the line numbers, the refutation record — is the reason the
> hand-off was worth acting on, and a disposition table cannot carry it. Nothing
> here has been summarised away. But it is a **record**, not a map: it describes
> defects that mostly no longer exist, and re-reading it as current is exactly the
> silent decay this project writes rules about.
>
> **The one finding worth re-reading is §2, and for the opposite reason to the
> others.** We could not see the delivered fix because the provider contract
> published the row as `C2 errors:      %s` and our drive reports C2 unsupported,
> so the affirmative branch appears in no artifact we hold. An opaque contract row
> hid a shipped fix for a full round — which makes the contract's **coverage**
> worth more than its accuracy, since neither project can read the other's code
> and both can compare behaviour.
>
> **CORRECTION, 2026-09-13: the last clause was false, and it had been false the
> whole time.** Both repositories are public and either session can clone the
> other in one command. The cyanrip fork found this in their own copy first —
> their `CLAUDE.md` asserted it in two places and a round-18 lap in a third — ran
> the check instead of repeating the claim, and told us. Ours is the same claim in
> the same shape.
>
> **This is the class the project already names: *a note asserting an absence
> needs a check that fails when the absence ends.*** Same shape as *"there is no
> `-V`"* and *"the suite has no network"*, both true when written. This one is
> worse because it shaped how we work — round 12 cost a whole round to a mechanism
> we asserted in their build and could simply have read.
>
> **What survives the correction.** The conclusion still holds, for a different
> reason: a published contract is worth more than reading the source, because it
> is a *promise* about behaviour rather than a snapshot of an implementation that
> may change tomorrow. Reading their tree is how we **verify** a contract row,
> never how we decide what a row should say — a convention re-derived from their
> source is one implementation copied twice, and the seam's whole value is two
> independent ones catching each other. So contract coverage still matters more
> than contract accuracy; *"because we cannot look"* was never the reason.

**What this is.** A list of concrete, evidence-backed problems that Platterpus has hit, measured, or worked around, where the fix belongs on the cyanrip side (fork or upstream). It is offered as useful information, nothing more.

**What this is not.** This is **not a handshake lap.** It carries no wire header, declares no verdict, is not numbered as a lap, and must not be counted as one. It creates no obligation to respond, and no response from you closes or advances anything.

**Round 8 is untouched.** Round 8 is OPEN; our lap 8 is a **HOLD on pin `ddf7ac3`** with a pre-commit that our lap 10 is GO unless the named conditions fail. Nothing in this document moves, amends, adds to, or argues with any of that. Items already live in round 8 were excluded during preparation; where one is mentioned it is only to say that we are not double-counting it. Under S-14, every item below defaults to **NEXT-ROUND** and none of them is put forward as blocking anything: none makes the pin under review unsafe.

**Evidence rule we held ourselves to.** Every finding cites a path with a line number or a verbatim quote from a committed artifact in this repo. Anything we could not cite was dropped, and the drops are counted at the end. Where a change's origin was in doubt we wrote "unknown" rather than guess — this project has twice misattributed an upstream change to the fork, so origin claims below are proved from artifacts where they can be.

**One correction we volunteer up front.** Two independent verification passes over these candidates refuted 16 of the 26 they examined, and the dominant reason was *already fixed at `ddf7ac3`*. That is our defect, not yours, and §12 below says so plainly. Every item that survives has been re-checked against the newest artifact we hold, and each says which one.

---

### 1. No album-level loudness line is cyanrip's — the whole album block is libavfilter's wording, with no owned fallback

**Severity: medium (silent-emptying risk on an archival field). Origin: upstream, proven from artifacts.**

#### What it is

The fork gave the *per-track* loudness rows owned, stable labels — `Sample peak level:`, `True peak level:`, `Integrated loudness (R128):`, `Loudness range (R128):`. The *album* block never got the same treatment. Only the two words `Album Loudness` are cyanrip's; the ` Summary:` tail and every value line under it (`I:`, `LRA:`, `Peak:`) are FFmpeg's `ebur128` filter output, which your own contract disclaims as wording that moves when FFmpeg does.

So the album-level integrated loudness, loudness range, sample peak and true peak in a cyanrip log are, in practice, an FFmpeg output format with no version signal attached — and there is nothing else in the log to fall back to.

#### Evidence

Your contract lists exactly one owned album string:

> `docs/handshake/inbound/artifacts/round-08-lap-01-provider-contract-gea2793a.md:179`
> ``| `cyanrip_encode.c:820` | `Album Loudness` |``

and disclaims everything under it:

> same file, `:482-486` —
> "Also unstable, and **not ours**: the loudness block FFmpeg's `ebur128` filter prints (`Integrated loudness`, `Loudness range`, `Sample peak:`, `True peak:`, ...). That wording belongs to libavfilter and moves when FFmpeg does. Prefer the `Sample peak level:` and `True peak level:` lines in P2, which are ours"

That recommended alternative exists **per-track only**, so at album level the contract points at nothing.

The block as emitted, in your own golden-path rig rip:

> `docs/handshake/artifacts-round-07-lap-29/round-07-lap-29-rig-rip-g9048082.log:1121` `Album Loudness Summary:`
> `:1124` `    I:         -13.9 LUFS`
> `:1134` `    Peak:       -0.1 dBFS`
> `:1137` `    Peak:        0.8 dBFS`

versus the owned per-track rows in the same file:

> `:79` `    Sample peak level: 94.3% (-0.5 dBFS)`
> `:80` `    True peak level:   0.3 dBFS`
> `:81` `    Integrated loudness (R128): -13.9 LUFS`

Our parser and why it is anchored where it is:

> `src/platterpus/parsers/cyanrip_log.py:390-401` — "The full line reads `Album Loudness Summary:`, but only `Album Loudness` is cyanrip's … the ` Summary:` tail comes from FFmpeg's `ebur128` filter, which their P3 explicitly marks as libavfilter's wording that 'moves when FFmpeg does'. Requiring the tail meant one upstream rewording would have emptied `album_loudness` entirely and silently — the whole block, not one field."

The value patterns (`_LOUDNESS_I` / `_LOUDNESS_LRA` / `_LOUDNESS_PEAK`, `:402-408`) match only libavfilter's lines; there is no cyanrip-owned alternative to key on.

**Origin, proved from artifacts rather than argued.** Stock upstream prints the identical block with no owned rows at all:

> `output_reference/cyanrip_flac/cyanrip_flac_police_classics.log:1` banner `cyanrip 0.9.3 (release)`, `:814` `Album Loudness Summary:` followed by the same ebur128 block; `grep -c "Integrated loudness (R128)"` on that file = **0**.
> `output_reference/cyanrip_fork_flac/cyanrip_fork_police_classics.log:1` banner `cyanrip 0.9.4-rc1+platterpus.5-beta.1 (platterpus-fork-g9003e6f)`; same grep = **14**; its album block is byte-identical to upstream's.

So the album block is upstream's, inherited unchanged; the fork's owned-row discipline (round 6 §C4) was applied per-track only. Rolling back to stock does not escape it — it makes it worse.

#### Why it is yours

Log text, which the ownership test names as yours outright. We tried three ways to fix it on our side and all three fail:

1. **Derive the album value from the owned per-track rows** — impossible for integrated loudness and LRA, which are gated whole-program EBU R128 measures and are not any function of per-track values. (Album *peak* would be derivable as the max of the per-track peaks, so that sub-part is partly ours; it does not carry I or LRA.)
2. **Read it from a cyanrip-owned ReplayGain tag line** — the log's Metadata blocks carry only `REPLAYGAIN_TRACK_GAIN`, `REPLAYGAIN_TRACK_PEAK`, `REPLAYGAIN_TRACK_RANGE`, `R128_TRACK_GAIN`, `REPLAYGAIN_REFERENCE_LOUDNESS`. Zero `REPLAYGAIN_ALBUM_*` / `R128_ALBUM_GAIN` rows.
3. **Loosen our regex** — we can be tolerant, but we cannot invent a stable label or a version signal for a third party's output format.

#### Suggested fix

Print cyanrip-owned album rows with the same discipline as the per-track ones, in priority order:

- `Album integrated loudness (R128): …` and `Album loudness range (R128): …` — these are the irrecoverable ones.
- `Album true peak level: …` and `Album sample peak level: …` — second priority; if you decline these we can derive them from the per-track rows.

The `(R128)` qualifier is load-bearing for the same reason it was per-track in round 6 §C4: an unqualified `Album integrated loudness:` would collide with libavfilter's own unqualified heading in the same log.

#### What it costs a consumer if unfixed

One FFmpeg release can empty the entire album-loudness block of every log, with no other symptom and no version signal to branch on. We consume these values into shipped artifacts — `src/platterpus/parsers/cyanrip_log.py:1812/1816/1829` populate `album_loudness`, `src/platterpus/rip_report.py:1122` writes it into the report JSON, `src/platterpus/ui/rip_progress.py:1287` renders it — so the failure mode is a silently blank archival field, not an error.

**Scope note so this is not mistaken for our pending work.** Migrating the *per-track* scrape onto your owned rows is ours to do (`TASKS.md:765`, task #80). The residual for you is strictly the **album** level, where there is no owned row to migrate to. `TASKS.md:765` already states the gap in your terms — "`I:` / `LRA:` have **no** stable provider source at all" — but that line has only ever lived in our task file and has never been sent to you.

Nothing here is wrong in the artifact under review today: at the current FFmpeg the values are correct.

---

### 2. `C2 errors:` prints a drive *capability*, never whether the rip *used* C2 — EAC's "Make use of C2 pointers" row stays unanswerable

**Severity: low (unobservable on our current drive). Origin: upstream. Round-1 §1.4 ask — STRUCK: the line has read `supported by drive, not used` since `8499890`, before this document was written.**

#### What it is

The line reports what the drive's capabilities page declares, not what the rip did, and not what the drive can do (corrected 2026-11-11: the BDR-209D's page does not declare C2 and the drive returns C2 pointers anyway, the fork's round 39 lap 3 S11 and S14; `c2_declaration.py`). EAC's archival field asks whether C2 was *used*. `unsupported by drive` shows it was not used (the ripper did not ask for C2 on the page's word; it never asks, `cyanrip@54d66666:src/drive_caps.c:121`), so that case is answerable; `supported by drive` says only that it was available, and no other line in the log answers the question. There is no wording that makes an affirmative honest.

#### Evidence

Format string at the current pin, unchanged:

> `docs/handshake/inbound/artifacts/round-08-lap-01-provider-contract-gea2793a.md:269`
> ``| `cyanrip_log.c:592` | `C2 errors:      %s` |``

(The contract row shows `%s` alone; the `by drive` suffix is real — upstream's source is quoted in Part A §8 of this file: `cyanrip_log(..., "C2 errors:      %s by drive\n", (ctx->rcap & CDIO_DRIVE_CAP_READ_C2_ERRS) ? "supported" : "unsupported");`. That quote is also the origin proof: this is upstream's libcdio capability bit, not a fork addition.)

Real value on our rig:

> `output_reference/cyanrip_flac/cyanrip_flac_police_classics.log:8` — `C2 errors:      unsupported by drive`

Our parser, and the reason it has no affirmative branch:

> `src/platterpus/parsers/cyanrip_log.py:967-1001` — "cyanrip's format string is `C2 errors:      %s by drive`. So 'unsupported' proves C2 was not used (the drive cannot), while 'supported' says only that it was available — EAC's row asks whether C2 was *used*, which cyanrip never states. Claiming Yes from a capability line would be exactly the invented rip fact the export forbids"

Our half is done and pinned: `tests/test_eac_layout_parity.py:229-243` (`test_c2_capability_is_not_reported_as_c2_use`) asserts `supported by drive` → `None`. The mapping at `cyanrip_log.py:991-1000` already accepts a "not used" wording as a truthful `False`.

**Prior ask.** This is not new. `docs/handshake/outbound/round-1.md:117-131` is titled "1.4 `C2 errors:` — say what the rip *did* (§2.5)" and carries the identical two-line proposal and the identical "no affirmative branch, on purpose" argument. `round-1.md:266` asked which of §2.1/§2.3/§2.4/§2.5 you implemented, and no inbound file has answered §2.5. A grep for "not used" / "C2 pointer" across all of `docs/handshake/inbound/` returns zero hits.

#### Why it is yours

Only the ripper knows whether its read path consumed C2 pointers. Our side is complete and test-pinned; what is left is a printf.

#### Suggested fix

Append the use state: `supported by drive, not used` / `supported by drive, used`. Our parser already maps the "not used" wording to a truthful **No** and deliberately has no affirmative branch (libcdio-paranoia never consumes C2 pointers, so a "used" line would contradict the engine, and "not used" contains the substring "used" — a positive check would earn nothing but a way to fabricate EAC's "Yes"). The agreed wording is already specified on our side at `docs/dependency-contracts.md:209`.

#### What it costs a consumer if unfixed

On a C2-capable drive, our EAC-layout export must print "(unknown)" in a row EAC always fills, and a logchecker deducts for it. The alternative — inferring Yes from capability — would be a fabricated rip fact.

**Honest severity note, in our own words.** Part C §4 of this file (the ranked recommendation; in the former `cyanrip-upstream.md` when this was written) ranks this 6 of 8 (Trivial / Upstream PR / Medium odds), and Part C §5 item 7 says the payoff "is unobservable on this rig — the BDR-209D reports C2 unsupported, so the row is already filled. Not worth buying hardware for. (Opportunistic.)" Part C §1 (the labelled-cell census) confirms the EAC row renders a truthful "No" today. Nothing in any artifact under review is wrong; the gap opens only on a C2-capable drive we do not have. Strictly opportunistic.

---

### 3. A zero AccurateRip checksum still prints as `match found, confidence N` — the void state has no distinct machine-readable form

**Severity: low (never observed in any artifact we hold). Origin: upstream, proven from an artifact.**

#### What it is

When a track's computed AccurateRip checksum is `0`, the match line is still emitted with a real confidence number, and the fact that the comparison is void is carried as a sentence *inside* the same parenthetical. A consumer keying on the structured parts — a result field plus a confidence integer, the only format-agnostic way to read the line — sees a confidence-200 verification for audio that was never meaningfully compared.

#### Evidence

The format string, present unchanged in every provider contract since round 4:

> `docs/handshake/inbound/artifacts/round-08-lap-01-provider-contract-gea2793a.md:245`
> ``| `cyanrip_log.c:446` | `(match found, confidence %i, but a checksum of 0 is meaningless)` |``

(Also `round-4.md:988` at `cyanrip_log.c:195`; `round-5.md:1311` at `:316`; `round-6.md:927` and `round-6b.md:736` at `:342`; round-07 laps 25/30/32/39 at `:446`.)

Our guard and the reason for it:

> `src/platterpus/parsers/rip_log.py:426-432` — "cyanrip itself prints the caveat — 'match found, confidence 200, but a checksum of 0 is meaningless' — and without this guard that line parsed as a confidence-200 positive. It matters most on the offset-variant row, where a silent or absent track yields `Accurip 450: 00000000` and the cell then announced a partially-accurate match for audio nothing was compared against. Keying on the zero CRC rather than on cyanrip's wording is the stronger invariant: it also covers a backend that omits the caveat"

**Origin proof (upstream).** `output_reference/cyanrip_flac/cyanrip_flac_police_classics.log:1` banner reads `cyanrip 0.9.3 (release)` — stock upstream — and `:169` of that same log emits `Accurip 450: BF62B1DA (matches Accurip DB, confidence 200, track is partially accurately ripped)`. The offset-450 block and its wording are upstream code, not a fork addition.

#### Two corrections we owe you on this one

1. **The checksum-0 branch has never been observed in any artifact this repo holds.** Every real zero-CRC occurrence we have (`docs/handshake/inbound/round-5.md:922, :989, :1054`; `round-6.md:510, :582`; `round-6b.md:319, :391, :461`) is a **bare** `Accurip 450: 00000000` printed under `Accurip:       disabled`, with no parenthetical at all. The evidence here is your format string, not a captured line.
2. **cyanrip is not withholding anything.** The caveat sits inside the same field, and our own capture group takes the whole field (`docs/cyanrip-consumer-contract.md`, rules `track_accurip` / `track_accurip_offset` — `\((?P<result>[^)]*)\)`) with the `00000000` CRC on the same line. The ask is that the *machine-readable shape* agree with the prose, not that information is missing.

#### Why it is yours

The checksum comparison and the verdict wording are cyanrip's, and the log is the record the user keeps. That the disclaimer exists at all proves cyanrip knows the match is void — it still emits it as a match.

#### Suggested fix

When the computed checksum is 0, do not print a match: print a distinct non-match state (e.g. `no comparison possible (checksum 0)`) with no confidence figure, so the structured fields say what the prose says.

#### What it costs a consumer if unfixed

We have no dependency left on you changing this — we deliberately keyed on the zero CRC rather than your wording, precisely so the guard survives a backend that omits the caveat. What remains is that the only thing separating a void comparison from a genuine one is a prose sentence in a free-text field: any consumer that substring-matches the result string (the fragile pattern the seam rules discourage), or any human skimming the log, reads a confidence-200 verification for silence. A log-shape improvement, not a correctness defect.

---

## The provider contract — three findings, one artifact

§4, §5 and §6 are three separate defects **in the same document and the same generator**, found independently by two different verification routes. We are listing them separately because they have different fixes and different failure modes, but they are one cluster and are probably one afternoon's work. Please read them together. All three are **fork-origin** in the sense that matters: `PROVIDER-CONTRACT.md` and `tools/gen-provider-contract.py` have no upstream counterpart, so whatever the origin of an individual log line, the contract's coverage of it is the fork's to fix.

---

### 4. The contract delivered with round 8 lap 1 was not generated by the build it names — and eight P2 "stable API" rows carry no matchable text

**Severity: high. Origin: fork (the artifact and its generator are fork-only).**

#### What it is

Two defects in one artifact and one generator, both provable from the delivered files without access to your tree.

**(a) The file is a stale regeneration, and the lap says otherwise three times.** Round-08-lap-01 §A:43 and §I:212-213 state the contract was "generated by `ea2793a`" / "generated from a clean build of `ea2793a`", and that `tools/gen-provider-contract.py --check` exits 0. §C's commit table puts `1f00653` (the `Cache probe:` bound/reason rewrite, flagged `YES` for log text) *before* `ea2793a`, so any contract generated at `ea2793a` must contain the new wordings. The delivered file contains none of them: it still publishes the superseded `Cache probe:    %i sectors measured (...)` at line 150 and has 7 `Cache probe:` rows where §D1:124 says P2 lists 9. Its `Build:` banner says `0.9.4-rc1+platterpus.5` although §A:18 names `0.9.4-rc1+platterpus.6-beta.1` as the build to install. It is the `afa32e1` regeneration — one commit before the log change and two before the regeneration at `5967439` that §C says exists. The generator's `--check` evidently does not compare the contract's own `Build:` banner (or its content) against the binary that was built, so a stale file passes the gate that exists to catch stale files.

**(b) Eight rows of the declared API cannot be matched, diffed or regression-tested.** P2 opens (:131-135) with "Changing the text, indentation, field order or units of any of them is a breaking change and requires a handshake round." Eight of its rows are bare format specifiers with no literal: `cyanrip_log.c:61` `%s`, `:184` `%s%s`, `:188` `%lu`, `:579` `%s%c%i %s`, `:619` `%s%s%s%s%s`, `:637` `%i%s`, plus `:58` `%s%s:` and `:469` `%s:`. P2a (:413) is your own mechanism for this class — "the pieces are reconstructed here from the `snprintf` formats that build the buffer" — but it decomposes exactly two call sites, both in `cyanrip_main.c`, and none in `cyanrip_log.c`. The consequence is concrete for `cyanrip_log.c:173`, published as `Read stalls:    %s`: the four wordings that line can actually emit exist only as prose in round-07-lap-14.md:159-162, a round-7 lap file, and your own note there says they are `strcmp`-pinned in `tests/stall.c`. A consumer generating checks from the contract gets nothing; a consumer that read one round's prose has it. That is precisely the "a list either side maintains by hand" failure the generated contract was built to remove. And the generator can do better where it chooses to — the seven `cache_probe.c` rows at :144-150 are fully populated wordings from the same run.

#### Evidence

> `docs/handshake/inbound/artifacts/round-08-lap-01-provider-contract-gea2793a.md:7`
> ``Build: `cyanrip 0.9.4-rc1+platterpus.5 (platterpus-fork-g<commit>)```

> `docs/handshake/inbound/round-08-lap-01.md:18` (inside the "Build this" block)
> `> version  0.9.4-rc1+platterpus.6-beta.1`

> `docs/handshake/inbound/round-08-lap-01.md:42-43`
> ``| golden reference | **generated by `ea2793a`**, committed one commit before this file |``
> ``| provider contract | generated by `ea2793a`, committed one commit before this file |``

> `docs/handshake/inbound/round-08-lap-01.md:212-213` (§I)
> ``` 
> `PROVIDER-CONTRACT.md`, generated from a clean build of `ea2793a` and
> committed one commit before this file. `tools/gen-provider-contract.py --check` exits 0.
> ```

> `docs/handshake/inbound/round-08-lap-01.md:86-92` (§C commit order — proves `1f00653` precedes `ea2793a`)
> ```
> | `afa32e1` | contract regenerated | n/a |
> | `1f00653` | **`Cache probe:` reports a bound, and says why the search stopped** | **YES** |
> | `ea2793a` | version bump | no |
> | `5967439` | contract + golden reference regenerated | n/a |
> ```

> the delivered contract, ALL `Cache probe:` rows (lines 144-150) — seven, none of them the bound shape:
> ```
> | `cache_probe.c:108` | `Cache probe:    not run (disc image has no drive cache)` |
> | `cache_probe.c:116` | `Cache probe:    unknown (out of memory)` |
> | `cache_probe.c:129` | `Cache probe:    unknown (disc too short to probe)` |
> | `cache_probe.c:141` | `Cache probe:    unknown (read failed while calibrating)` |
> | `cache_probe.c:158` | `Cache probe:    unknown (drive returned reads too fast to time)` |
> | `cache_probe.c:187` | `Cache probe:    no readback cache measured (uncached read %.1f ms)` |
> | `cache_probe.c:193` | `Cache probe:    %i sectors measured (%.1f KiB, uncached read %.1f ms)` |
> ```
> `grep -n "to %i sectors\|upper bound\|search ceiling"` over that file → **no matches**.

> contract:131-135 (P2 declared as the API)
> ```
> ## P2 - Outputs: stable log lines (the API)
>
> Every line below reaches **both stdout and the logfile**. Changing the text,
> indentation, field order or units of any of them is a breaking change and
> requires a handshake round.
> ```

> contract, the eight opaque P2 rows (exact lines):
> `:192` ``| `cyanrip_log.c:58` | `%s%s:` |``
> `:193` ``| `cyanrip_log.c:61` | `%s` |``
> `:201` ``| `cyanrip_log.c:184` | `%s%s` |``
> `:202` ``| `cyanrip_log.c:188` | `%lu` |``
> `:249` ``| `cyanrip_log.c:469` | `%s:` |``
> `:266` ``| `cyanrip_log.c:579` | `%s%c%i %s` |``
> `:276` ``| `cyanrip_log.c:619` | `%s%s%s%s%s` |``
> `:280` ``| `cyanrip_log.c:637` | `%i%s` |``
> and `:200` ``| `cyanrip_log.c:173` | `Read stalls:    %s` |``

> contract:413-440 (P2a in full — two entries, both `cyanrip_main.c`)
> ```
> ### P2a - Composed lines
>
> Lines assembled into a buffer by a run of `snprintf()` and emitted through a
> bare `"%s"`. The emitting call site shows a consumer nothing, so the pieces
> are reconstructed here from the `snprintf` formats that build the buffer, in
> source order. Segments after the first are conditional.
>
> **`cyanrip_main.c:870`** - reaches logfile: **not directly** - see legend
> …
> **`cyanrip_main.c:2056`** - reaches logfile: yes
> ```
> (next heading is `## P3` at `:442` — nothing else in P2a.)

> `docs/handshake/inbound/round-07-lap-14.md:159-162` (the four `Read stalls:` wordings, prose only)
> ```
> Read stalls:    unknown (stall reporting disabled with -k 0)
> Read stalls:    none (no read exceeded 10s)
> Read stalls:    2 reads exceeded 10s; longest 187s (track 4, LSN 45231)
> Read stalls:    1 read exceeded 30s; longest 42s (track 1, LSN 0)
> ```
> `:164` — "**All four are test-asserted** (`tests/stall.c`), so a reword is a test failure"

Freshness, so this is not a complaint about a superseded artifact: `round-08-lap-01-provider-contract-gea2793a.md` is the newest provider contract in `docs/handshake/inbound/artifacts/` (the previous four are round-07 laps 25/30/32/39), while the 2026-08-13 rig ran `cyanrip 0.9.4-rc1+platterpus.6-beta.4 (platterpus-fork-g2ce8993)` (`docs/handshake/artifactsround08/round08rigcheckripperversion.txt`). The contract we hold is behind the field build by a version bump *and* a beta series.

**One honest caveat.** Our lap 8 §F2 (`docs/handshake/verified/round-08-lap-08.md:346-347`) asks whether you hold copies of round 8 laps 3–7, which we do not. A corrected contract could have been sent in a lap we lost. So the ask is "resend or confirm", not "you never sent it".

#### Why it is yours

`PROVIDER-CONTRACT.md` and `tools/gen-provider-contract.py` are fork-only. Platterpus cannot regenerate a contract from your build, cannot read your `snprintf` chains, and cannot make `--check` compare the banner against the binary. Origin proved by log diff rather than assumed: `grep -c -i cache output_reference/cyanrip_flac/cyanrip_flac_police_classics.log` = **0** (stock upstream `cyanrip 0.9.3 (release)`), while the fork log carries `Cache model:` at line 17 — the cache subsystem and its contract rows are fork code, not inherited upstream.

#### Suggested fix

**(a) Make the artifact prove its own provenance, and make `--check` able to fail.**

1. Re-run `tools/gen-provider-contract.py` from a clean build of the commit the round-8 manifest actually names (`+platterpus.6-beta.4` / `g2ce8993` is what the rig is running), and resend it — or, if a corrected contract was already sent in laps 3–7, resend that.
2. Have `--check` compare the contract's own `Build:` banner against the version string of the binary it just built, and fail on mismatch. Today it evidently does not, which is how a file whose banner reads `+platterpus.5` shipped under a cover letter naming `+platterpus.6-beta.1`.
3. Add a content assertion so the check cannot pass for the wrong reason: every `cyanrip_log()` / `cyanrip_log_start_line()` format string reachable in the built source must appear verbatim in P2/P2a. That single rule would have caught this file.
4. Keep emitting the commit as `g<commit>` if you must elide it — that normalisation is deliberate and we are not asking you to change it (round-4.md:461-462, "A generated artifact cannot contain a value that generating it alters") — but pair it with a `Generated-from:` line naming the real SHA alongside the source anchor you added in round 6.

**(b) Extend P2a to the `cyanrip_log.c` composed rows.** For the `snprintf`-chain cases (`:58`, `:184`, `:188`, `:469`, `:579`, `:619`, `:637`) apply the reconstruction P2a already does for `cyanrip_main.c:870`. For `cyanrip_log.c:173` (`Read stalls:    %s`) the argument comes from a pure formatter whose four return shapes are already `strcmp`-pinned in `tests/stall.c` — emit those enumerated strings into P2a from the same source of truth the test reads, exactly as the seven populated `cache_probe.c` rows are emitted from `tests/cacheprobe.c`. Where a row genuinely cannot be decomposed, mark it the way `cyanrip_main.c:2056` already is ("Do not pattern-match this row") so "unmatchable" is a declared property rather than an omission a consumer has to discover.

#### What it costs a consumer

The provider contract is the machine-derived half of the seam and is the artifact both projects use to decide what has and has not changed. A stale one is worse than a missing one, because it reads as current.

Direct, measured impact on this repo: `tests/test_argv_surface_agreement.py:563,569` deliberately reads the newest inbound round's provider contract to diff every flag we send against your published table —

> ```
>     assert any("provider-contract" in p.name for p in files), (
>         "no provider contract among the files read, so the table is being taken from "
>         f"prose in the lap files: {[p.name for p in files]}"
>     )
> ```

— that gate is currently deriving from a contract generated before `1f00653` and before the version bump, against a field build two steps further on. `tests/test_provider_contract_agreement.py` has the same dependency for the log-line half. This is the exact failure shape that already cost a release blocker here: the `-V` removal sat in a committed contract for a full round while our probes shipped a flag the build had dropped. The P1 flag table is probably unaffected in this instance, but that is a guess and cannot be checked from a file whose provenance is wrong — which is the point.

Second-order, and the reason we are listing it first: the first of our two verification passes used this file as its staleness oracle and refuted 11 of 14 candidates, 8 of them on "already fixed". Those refutations may well still be right — but the evidence behind them is one regeneration behind, and at least one thing the cover letter said was in it demonstrably is not.

The eight opaque P2 rows are the durable half: a declared breaking-change API of 268 rows where 8 cannot be matched, diffed or regression-tested means a reword of `Read stalls:` — a line that lands in an archival log — would reach a user as a parse miss with no test on either side firing.

---

### 5. The newest contract's P2 is missing a `Cache probe:` line the shipped binary prints — and `gen-provider-contract.py --check` exits 0 on it

**Severity: high. Origin: fork.**

#### What it is

This is §4(a) approached from the other end, and it is worth stating separately because the *detection* story is the sharp end.

Round-8 lap-1 §D1 announces commit `1f00653` as replacing `Cache probe:    %i sectors measured (...)` with a bounded form, and says "The nine wordings it can now emit are pinned by `tests/cacheprobe.c` and listed in `PROVIDER-CONTRACT.md` P2." The contract attached to that same lap lists **seven** `Cache probe:` wordings, one of which is the exact pre-fix string, and none of which is the new shape. The rows are byte-identical to round-07-lap-39's, line numbers included.

Three things rule out an innocent reading. (1) The source anchor moved between the two contracts (`8290677bea1a834d` → `99769a09466b0b57`), so a different tree WAS scanned — `cache_probe.c` simply did not move in it, which it must have if `1f00653` were present. (2) The new wordings appear nowhere else in the document, so they did not migrate to another file. (3) The lap orders `1f00653` before `ea2793a`, and §A states the contract was generated by `ea2793a` — so the fix is inside the tree the contract claims to describe.

Either the generator ran against a stale checkout, or its P2 scan has a hole that silently kept a retired string and dropped a live one. From this side those are indistinguishable, which is itself the problem: `--check` exits 0, so the drift checker that exists to catch exactly this reported clean.

#### Evidence

**1. THE CLAIM** — `docs/handshake/inbound/round-08-lap-01.md:123-127`:
> "The nine wordings it can now emit are pinned by `tests/cacheprobe.c` and listed in `PROVIDER-CONTRACT.md` P2. The shape you will see on the rig is:
> ```
> Cache probe:    32 to 63 sectors (73.5 to 144.7 KiB, uncached read 364.3 ms)
> ```"

**2. THE DOCUMENT** — `docs/handshake/inbound/artifacts/round-08-lap-01-provider-contract-gea2793a.md:144-150`, all seven rows, the last being the string lap-01 says was removed (quoted in full in §4 above).

Ran: `diff <(grep cache_probe.c round-07-lap-39-provider-contract-g422d12a.md) <(grep cache_probe.c round-08-lap-01-provider-contract-gea2793a.md)` → **EMPTY, exit 0**.
Ran: `grep -n "ceiling|upper bound|at least|%i to %i"` over the same file → the only hit is line 432, unrelated prose ("the progress bar and ETA of at least one consumer"). The new wordings are absent from the whole document.

**3. THE P2 PROMISE** — same file `:1-5`:
> "**Generated** by `tools/gen-provider-contract.py` from the source tree and the built binary. Do not edit by hand -- regenerate. A hand-written contract goes stale silently, which is the failure this file exists to prevent."

**4. THE FIX IS REAL** — `docs/handshake/inbound/round-08-lap-01.md:191` (§G revert-proof table):
> ``| cache probe D1 | restore `"%i sectors measured"` | `cacheprobe_test` fails |``

**5. THE ANCHOR MOVED BUT `cache_probe.c` DID NOT** — line 9 of each artifact:
> round-07-lap-32: "**Source anchor:** `sha256/16 = 8290677bea1a834d`"
> round-07-lap-39: "**Source anchor:** `sha256/16 = 8290677bea1a834d`"
> round-08-lap-01: "**Source anchor:** `sha256/16 = 99769a09466b0b57`"

**6. THE BINARY DISAGREES WITH THE DOCUMENT** — `docs/handshake/artifactsround08/round08scripttranscript.txt:198`, from the 2026-08-13 rig run:
> "Cache probe:    at least 2048 sectors, upper bound unknown (4704.0 KiB or more, search ceiling reached, uncached read 363.1 ms)"

Build that emitted it — `docs/handshake/artifactsround08/round08versions.txt`:
> "cyanrip 0.9.4-rc1+platterpus.6-beta.4 (platterpus-fork-g2ce8993)"

A real shipped line, absent from the newest published contract.

#### Why it is yours

`tools/gen-provider-contract.py` runs in your repo against your tree and your binary. Nothing on our side can regenerate it or detect the omission except by hand-diffing two of your artifacts, which is how this surfaced.

#### Suggested fix

Two parts, and the second is the one that matters.

1. Regenerate `PROVIDER-CONTRACT.md` from a tree that provably contains `1f00653` and re-ship it against the round-8 test pin, so P2 lists the nine `Cache probe:` wordings the binary actually emits. While there, take the Build line's version off the built binary's `--version` rather than a source constant.
2. Close the class, because a regeneration fixes one instance and leaves the mechanism. `--check` exited 0 on this document, which makes it a check that passes for the wrong reason — the failure mode both projects' rules name as worse than a check that fails. Two cheap floors:
   - Cross-assert the generator's P2 output against the strings `tests/cacheprobe.c` already pins. The test file is the independent witness; a contract whose P2 disagrees with it is stale by construction, and this specific defect would have been a build failure instead of a shipped artifact.
   - Give `--check` a staleness floor it cannot satisfy by finding nothing: recompute the source anchor at check time and refuse if it does not match the anchor written in the document, and refuse if the built binary's `--version` does not match the Build line.

Worth saying explicitly on the way past: **this is not an ask to fix the `Cache probe:` number.** That is already agreed as a round-10 method defect, and the current wording ("upper bound unknown, search ceiling reached") correctly names its own ignorance. This finding is only about the document not describing the binary.

#### What it costs a consumer

Not blocking under S-14 — nothing here makes the reviewed pin unsafe, no audio or checksum is affected, and we do not currently parse the `Cache probe:` line for anything beyond echoing it verbatim (`src/platterpus/rig_check.py:380`, an INFO row).

What makes it worth carrying is what it says about the document rather than about the line. We treat the contract as ground truth in code: `tests/test_argv_surface_agreement.py` diffs every flag we send against the newest inbound contract; `uiscript/verbs.py` keys `FILE_ONLY_FLAGS` on the contract's section placement, which is what stopped a scripted `cyanrip -x` from becoming a full rip with MusicBrainz lookup enabled; `ripper_message_inventory.py` is ordered by it. A P2 table that can silently omit a shipped log line means the fatal-message inventory our error surfacing derives from is checked against a population we cannot trust — precisely the round-5 failure this project already paid for once, where a green test was measuring your generator's allowlist rather than the ripper, and two ordinary hardware failures rendered to the user as a bare "Rip failed."

It also lands squarely on round 6's own rule — a build tag names a commit, it does not name what was built — arriving this time in the very document that rule was written to protect.

---

### 6. P2 does not enumerate nine banner labels every rip emits — six of them lines Platterpus parses

**Severity: medium. Origin: the labels are largely upstream's; the omission is the fork's.**

#### What it is

P2 declares itself the stable-line API and counts "268 distinct stable lines". But nine `Label:` rows that the banner of every real rip emits are not enumerated anywhere in the file: `Overread:`, `Overread mode:`, `Disc number:`, `Total discs:`, `DiscID:`, `Release ID:`, `CDDB ID:`, `Album:`, `Album artist:`. They are not in P2, not in P2a, and not in P3; the only rows in the whole document containing those strings are P5 fatal messages from `musicbrainz.c:317` and `discid.c:31`.

The omissions are contiguous with the enumeration's own gaps — P2 runs Offset(576)/(579) straight to Speed(588), Outputs(627) straight to Disc tracks(633), and 637 straight to AccurateRip(651) — so the generator's scan of the banner emitter is landing partway rather than deliberately excluding the block.

Six of the nine are lines our parser keys on today and declares in its own published consumer contract, so the two halves of the seam disagree about what is covered, and the side that would be broken by a reword is the side with no say in it.

#### Evidence

The promise — `docs/handshake/inbound/artifacts/round-08-lap-01-provider-contract-gea2793a.md:131-135`:
> "## P2 - Outputs: stable log lines (the API)
> Every line below reaches **both stdout and the logfile**. Changing the text, indentation, field order or units of any of them is a breaking change and requires a handshake round."

`:408` "**268 distinct stable lines.**" Nothing in the file disclaims completeness for the banner block; the only stated carve-outs are P2a (two rows) and P3.

The gap, measured. Scripted match of every `^[A-Z][A-Za-z0-9 /-]*:` banner label in `docs/handshake/artifactsround08/round08riplog.log:2-31` (real rig rip, fork g2ce8993) against the full contract text. **ABSENT:** `Overread:` (log:9), `Overread mode:` (log:10), `Disc number:` (log:21), `Total discs:` (log:22), `DiscID:` (log:25), `Release ID:` (log:26), `CDDB ID:` (log:27), `Album:` (log:28), `Album artist:` (log:29). Every other banner label (`Invoked as:`, `Offset:`, `Speed:`, `C2 errors:`, `Cache model:`, `Album Art:`, `Outputs:`, `Disc tracks:`, `Tracks to rip:`, `AccurateRip:`, `Total time:`) IS enumerated, so the sweep really does land partway.

Guarding against a substring false positive — the only rows in the whole file containing any of these strings are `:179` ``| `cyanrip_encode.c:820` | `Album Loudness` |``, `:275` ``| `cyanrip_log.c:615` | `Album Art:      %s` |``, `:395` (P5 fatal, `musicbrainz.c:317`) and `:644` (P5 fatal, `discid.c:31`). None is a banner label row.

The holes sit exactly where those lines fall in every log — same file `:277-281`:
> ```
> | `cyanrip_log.c:627` | `Outputs:` |
> | `cyanrip_log.c:633` | `Disc tracks:    %i` |
> | `cyanrip_log.c:634` | `Tracks to rip:  %s` |
> | `cyanrip_log.c:637` | `%i%s` |
> | `cyanrip_log.c:651` | `AccurateRip:    %s` |
> ```

`Disc number:`/`Total discs:` sit between 627 and 633 in the log; `DiscID:`/`Release ID:`/`CDDB ID:`/`Album:`/`Album artist:` between 637 and 651. Likewise `:270-273` runs Offset(576)/(579 `%s%c%i %s`) straight to Speed(588) with nothing for the two Overread lines. **Note** the one row that could be read as covering `Overread:` is `:269` ``| `cyanrip_log.c:579` | `%s%c%i %s` |`` — an opaque row whose label is a `%s`, so it pins no text (see §4b); `Overread mode:` has no row of any kind.

The consumer half — `src/platterpus/parsers/cyanrip_log.py`:
> `:125` `_OVERREAD_MODE = re.compile(r"^(?:Over|Under)read mode:\s+(?P<mode>.+?)\s*$")`
> `:132` `_ALBUM = re.compile(r"^Album:\s+(?P<value>.+?)\s*$")`
> `:133` `_ALBUM_ARTIST = re.compile(r"^Album artist:\s+(?P<value>.+?)\s*$")`
> `:157` `_DISC_ID = re.compile(r"^DiscID:\s+(?P<value>\S+)")`
> `:158` `_CDDB_ID = re.compile(r"^CDDB ID:\s+(?P<value>\S+)")`
> `:180` `_RELEASE_ID = re.compile(r"^Release ID:\s+(?P<value>\S+)")`

and `:107-113` states the load-bearing one explicitly: "THIS line — not the neighbouring `Overread:  +2 frames` — is the one that says whether the drive actually read the disc's outermost samples… Keying on the count would therefore report Yes for every rip".

Our published half declares all six as parsed — `docs/cyanrip-consumer-contract.md` §1, rules `overread_mode`, `album`, `album_artist`, `disc_id`, `cddb_id`, `release_id` — under that section's own sentence "Changing the text, indentation, or field order of any of these changes what Platterpus records about a rip." So the two published halves of the seam disagree on six lines.

Not a regression: the same nine labels are absent from all four earlier contracts (round-07 laps 25/30/32/39), so this is a standing gap.

**Origin, by diffing the two reference logs.** `output_reference/cyanrip_flac/cyanrip_flac_police_classics.log` (stock 0.9.3) lines 5,6,16,17,18,19 already emit `Overread:       +2 frames`, `Overread mode:  fill with silence in lead-in/lead-out`, `DiscID:`, `CDDB ID:`, `Album:`, `Album artist:` — so six of the nine label *texts* are upstream's. `Disc number:`/`Total discs:`/`Release ID:` appear only in the fork log (`:21,22,26`), but the stock run passed neither `-c` nor `-a`, so their absence there is **not** proof of fork origin — undetermined, and we are not guessing. The *defect*, however, is fork-only: the contract and its generator exist nowhere upstream.

#### Why it is yours

Only the provider can enumerate its binary's format strings. Platterpus could only stop parsing the lines, which is data loss, not a fix.

#### Suggested fix

Extend `tools/gen-provider-contract.py` to reach the banner emitter (the `cyanrip_log.c` 537-657 region already contributes rows, so the sweep stops partway rather than skipping the block) and regenerate, so all nine labels get P2 rows with their literal text. Where a row's format string carries the label in a `%s` — `cyanrip_log.c:579` `%s%c%i %s`, which plausibly emits `Overread:`/`Underread:` — enumerate the label variants rather than leaving an opaque row (this is the same ask as §4b).

Then close it with a self-check rather than a promise: run a real rip, extract every `^[A-Z][^:]*: ` label from the resulting log, and fail the generator if any is absent from P2 — a floor the contract cannot silently decay past.

**Our companion obligation, not part of the ask:** `tests/test_provider_contract_agreement.py:80` checks only that we parse nothing on your P3, never the converse, and its docstring at `:15-16` claims "When a new round lands with a new provider contract, this test re-derives from it" while `:28` still hardcodes `_ROUND_4 = … "round-4.md"`. That is ours, and it is why this gap went unseen here.

#### What it costs a consumer

Six log lines Platterpus parses on every rip sit outside your own breaking-change rule, so they can be reworded in any build without opening a round — and nothing on either side would notice until a rip came back wrong. Our parsers never raise, so the failure is silent field loss, not a crash: `overread_mode` is the sole discriminator for the EAC-parity "Overread into Lead-In and Lead-Out" Yes/No row (the frame count is identical in both modes), so that row would flip to unknown; `album`/`album_artist` feed the EAC log's Artist/Album header; `disc_id`/`cddb_id` are the TOC-derived keys the re-rip comparison uses to prove two rips are of the same physical disc; `release_id` is the only witness that our colon-delimited `-a` tag blob parsed into the right fields.

This is the `-V` blocker's exact shape — a surface we depend on that the contract did not cover — arriving from the log side instead of the argv side, and it has been present in all five published provider contracts.

---

### 7. The `-j` diagnostics record declares `messages_are_complete: true` while dropping every ebur128 loudness block

**Severity: medium. Origin: fork (`-j` is fork-only).**

#### What it is

The fork-only `-j` / `--diagnostics` JSON asserts that its `messages[]` capture is complete when it is not. In both full-rip `-j` artifacts either side holds, exactly **55** non-blank lines present in the logfile of the same rip are absent from `messages[]`, while the record states `messages_dropped: 0`, `messages_are_complete: true`, `messages_tail: []`.

Of the 55, **52 are content**: four complete ebur128 blocks (three per-track plus the album one), each being the `Summary:` header and its `Integrated loudness` / `Loudness range` / `Sample peak` / `True peak` sub-blocks. The remaining 3 are structural log-only lines (the two `--- output before this log was opened ---` / `--- end of pre-log output ---` markers and the trailing `Log FUN512:` self-hash, which is inherently uncapturable since it hashes the finished log). We state 52/55 rather than repeating a raw 55, because overstating it by three would be exactly the unqualified remembered measurement this hand-off is trying not to produce.

The mechanism is provable from your own generated contract rather than guessed. The capture hook wraps `cyanrip_log()` only — the record says so itself in `messages_note`. The contract lists `cyanrip_encode.c:820` as emitting the format string `Album Loudness` with no `Summary:`; libav's ebur128 filter appends `Summary:` and the block via `av_log`. So the JSON captures the truncated stub `"Album Loudness "` while the logfile carries `Album Loudness Summary:` followed by 12 more lines. The capture sees cyanrip's half of the line and not libav's, and then declares itself complete.

This is not a transient: it reproduces identically (55 missing, same three assertions) across two independent fork builds, g400155b (lap 32) and g422d12a (lap 39).

#### Evidence

**The false assertion** — `docs/handshake/inbound/artifacts/round-07-lap-39-golden-reference-diagnostics-g422d12a.json:38-42`:
> ```
>   "messages_are_classified": false,
>   "messages_note": "cyanrip_log() carries no severity, so no severity is asserted here. Progress lines that were overwritten on the terminal are collapsed to the final state of each line.",
>   "messages_dropped": 0,
>   "messages_are_complete": true,
>   "messages": [
> ```
same file `:225` `    "Album Loudness ",` and `:233` `  "messages_tail": []`

**The same rip's logfile, showing what was dropped** — `round-07-lap-39-golden-reference-g422d12a.log:47-63`:
> ```
> Summary:
>
>   Integrated loudness:
>     I:          -7.7 LUFS
>     Threshold: -17.7 LUFS
>
>   Loudness range:
>     LRA:        20.0 LU
>     Threshold: -27.7 LUFS
>     LRA low:   -27.7 LUFS
>     LRA high:   -7.7 LUFS
>
>   Sample peak:
>     Peak:        0.0 dBFS
>
>   True peak:
>     Peak:        0.0 dBFS
> ```
same file `:257` `Album Loudness Summary:` (the JSON at `:225` captured only `"Album Loudness "` — the stub without libav's half)

**Our own re-derivation, not the finding's number.** A script loaded the JSON's `messages[]`, multiset-differenced it against the non-blank lines of its paired `.log`:
> ```
> json messages: 189   log nonblank: 231   MISSING: 55
> missing set = log lines 29, 34 (pre-log markers); 47,49-51,53-57,59-60,62-63 (track 1);
> 120,122-124,126-130,132-133,135-136 (track 2); 193,195-197,199-203,205-206,208-209 (track 3);
> 257,259-261,263-267,269-270,272-273 (album); 282 ("Log FUN512: ...")
> => 52 ebur128 content lines + 3 structural.
> ```
Same diff on `round-07-lap-32-golden-reference-diagnostics-g400155b.json`:
> ```
> complete= True dropped= 0 tail= []
> missing: 55
> ```

**Mechanism, from your own generated contract** — `round-08-lap-01-provider-contract-gea2793a.md:179` ``| `cyanrip_encode.c:820` | `Album Loudness` |``, and `:482-486`:
> "Also unstable, and **not ours**: the loudness block FFmpeg's `ebur128` filter prints … That wording belongs to libavfilter and moves when FFmpeg does."

**Still true at the newest build we hold** — `docs/handshake/artifactsround08/round08rigcheckargvprobe.json`, from the 2026-08-13 rig on `cyanrip 0.9.4-rc1+platterpus.6-beta.4 (platterpus-fork-g2ce8993)`:
> ```
> messages_are_classified = false
> messages_note = "cyanrip_log() carries no severity, so no severity is asserted here. ..."
> messages_dropped = 0
> messages_are_complete = true
> messages_tail = []
> ```
— identical field set, identical note, **no scope field**, at a build newer than `gea2793a`.

**Nothing in the published commit table touches capture scope** — `round-08-lap-01.md:85-92`; the only adjacent commit is `1fe78f4` "`fflush(stdout)` after a captured libav message", which changes *flushing*, not what is captured, and you mark it "log text? no".

**Why it matters most** — `round-08-lap-01-provider-contract-gea2793a.md:502-506`:
> "Argument validation runs **before the logfile is opened**. … **But a run that refuses during argument validation opens no logfile at all**, and for that class the only artifact is the `-j` diagnostics record"

**Residual we will not paper over.** We hold no *full-rip* `-j` record newer than g422d12a — the g2ce8993 record is a refused argv probe with no loudness block, so it cannot by itself prove the ebur128 lines are still uncaptured at the current pin. The staleness conclusion rests on the schema and note being byte-identical at the newer build, no commit touching capture scope, and the contract still stating no scope limit. That is strong, but it is inference on the last mile, and you can settle it in one command by regenerating a golden-reference diagnostics JSON at the current pin.

#### Why it is yours

The record is written by cyanrip; `-j` is a fork-only flag (first appearing in the round-7 provider contracts at `:42`, with no round-4/5/6 antecedent). Platterpus cannot make a producer's capture hook see output it never saw, and cannot correct an assertion inside a file it does not write. Our only `-j` call site is a consumer (`src/platterpus/rig_check.py:187`).

Note the layer separation, because misattributing upstream to fork is a repeat failure here: the ebur128 block *itself* is upstream-inherited (present in `output_reference/cyanrip_flac`). The defect is not the block — it is the `-j` record's false completeness assertion, and that record does not exist upstream.

**Not already asked.** `messages_are_complete` appears in prose in exactly two places, both round 7: `inbound/round-07-lap-12.md:70` where you announce the field ("You asked us to state the property"), and `verified/round-07-lap-13.md:188` where we praise it. In neither did anyone check the field against the log. Asking for a field is not reporting that the field lies.

#### Suggested fix

Either half of the seam's own honesty rule satisfies this; you pick.

**(a) Widen the capture.** Hook `av_log` in addition to `cyanrip_log()` so `messages[]` matches the logfile's non-blank lines. Commit `1fe78f4` shows a libav-message path already exists, so the plumbing may be closer than it looks — but note the ebur128 wording is libavfilter's and moves when FFmpeg does, which your contract flags at `:482-484`.

**(b) Keep the current scope and stop asserting a property the record does not have.** Set `messages_are_complete: false` (or make it scope-qualified), count the uncaptured lines into `messages_dropped`, and add an explicit scope field naming what is captured — e.g. `messages_scope: "cyanrip_log() only; libav/ebur128 filter output is not captured"`. The existing `messages_note` is the natural home for the prose half.

Whichever is chosen, document the scope in the provider contract. Today the contract's `-j` coverage is a single row in the P1 flag table (`:42`) plus the P4 note (`:502-506`); it never describes the record's schema or its capture scope, so a consumer has nothing to check the assertion against.

#### What it costs a consumer

This is the diagnostic-completeness rule inverted: a silent truncation that reads as completeness. The `-j` record is your machine-readable capture artifact, and it is the *only* artifact for the one class of run that opens no logfile at all. A consumer that trusts `messages_are_complete: true` as the authority on what cyanrip said will silently lose 52 lines and never learn they were dropped. The fields were added at your round-7 lap 12 explicitly at our request, so the field asserts a property the record does not have — which is worse than never having stated it.

Blast radius today is limited and we should say so honestly: Platterpus passes `-j` at exactly one call site, a refused run with no loudness block, so the gap does not currently bite us. This is a correctness-of-the-record defect, not an audio or checksum defect.

---

### 8. Partial rip (`-l`): a track's `INDEX 00` is computed against a FILE that was never written, and lands 682 frames past the end of the one it is printed under

**Severity: medium. Origin: upstream, proven from source.**

#### What it is

`cyanrip_cue_track()` decides to write an appended-pre-gap `INDEX 00` from `crip_track_has_appended_pregap(...)`, whose only structural input is `has_prev_track` = `!!t->pt` — the previous track *on the disc*, with no notion of whether that track is in the `-l` rip set. It then computes the marker as `t->pregap_lsn - t->pt->start_lsn_sig`, i.e. an offset into the predecessor's FILE, and prints it into whatever FILE block is currently open — which, on a partial rip, is the last track that was actually written.

Measured on `-l 1,3,5,6,7`: track 5's marker is emitted inside `FILE "03 - Message in a Bottle.flac"` with the value `05:00:35` (22535 frames), while that file is only 21853 frames long. 22535 = 72455 (track 5 pregap LSN) − 49920 (track 4 start LSN) — arithmetically an offset into track 4's file, which was never written.

The proof that this is the mechanism and not a coincidence: the full-rip reference cue of the same disc carries the byte-identical value `INDEX 00 05:00:35` nested under `FILE "04 - Walking on the Moon.flac"`, where it is correct (track 4's file is 22650 frames because the 115-frame pre-gap is appended to it). Same number, different containing FILE.

Only track 5 is affected in this rip, and that is the mechanism working as described: track 7's `INDEX 00 04:05:53` (18428 frames) sits under `FILE "06 - …"`, whose length is 18533 frames, because track 6 *was* in the rip set. The condition is precisely "the immediate predecessor is excluded by `-l`".

#### Evidence

**The defect** — `docs/handshake/artifactsround08/round08ripcue.cue:20-32` (fork build `platterpus-fork-g2ce8993`):
> ```
> FILE "03 - Message in a Bottle.flac" WAVE
>   TRACK 03 AUDIO
>     INDEX 01 00:00:00
>   TRACK 05 AUDIO
>     ISRC GBAAM0201148
>     INDEX 00 05:00:35
> FILE "05 - Don’t Stand So Close to Me.flac" WAVE
>     INDEX 01 00:00:00
> ```

`docs/handshake/artifactsround08/round08riplog.log:24` `Tracks to rip:  1, 3, 5, 6, 7`
`:154` `    Frames:      21853` (track 3 — the FILE the marker is nested under)
`:164-165` `    Start LSN:   28067` / `    End LSN:     49919` (so track 4 starts at 49920)
`:239` `    Pregap LSN:  72455 (duration: 00:01.40)` (track 5)
`:232` `    Frames:      18072` (track 5 — identical to the full rip, so the 115 pre-gap frames are in **no** file)

Arithmetic: `05:00:35` = 5·60·75 + 35 = 22535 frames. 22535 − 21853 = **682 frames = 9.093 s past EOF**. 72455 − 49920 = 22535 exactly.

Counter-instance (correct, predecessor ripped): `:43` `    INDEX 00 04:05:53` = 18428 frames under `FILE "06 - …"`, whose log Frames (`:309`) is 18533. 109070 − 90642 = 18428.

**Full-rip control** — `output_reference/cyanrip_fork_flac/cyanrip_fork_police_classics.cue:36-43`:
> ```
> FILE "04 - Walking on the Moon.flac" WAVE
>   TRACK 05 AUDIO
>     INDEX 00 05:00:35
> FILE "05 - Don’t Stand So Close to Me.flac" WAVE
> ```
`output_reference/cyanrip_fork_flac/cyanrip_fork_police_classics.log:297` `    Frames:      22650` (track 4 = 22535 audio + 115 appended pre-gap → marker is in range).

**Still present at fork HEAD** — `rmccann-hub/cyanrip @ 81fea099` (branch `platterpus-fork`), newer than both `ddf7ac3` and `ea2793a`:
> `src/cue_writer.h` — `return pregap_lsn != CDIO_INVALID_LSN && pregap_lsn != start_lsn_sig && has_prev_track && dropped_pregap_start == CDIO_INVALID_LSN && merged_pregap_end == CDIO_INVALID_LSN;` ← no rip-set input at all
> `src/cue_writer.c` — `const int write_appended_pregap = crip_track_has_appended_pregap(t->pregap_lsn, t->start_lsn_sig, t->dropped_pregap_start, t->merged_pregap_end, !!t->pt);`
> `src/cue_writer.c` — `cyanrip_frames_to_cue(t->pregap_lsn - t->pt->start_lsn_sig, time_00);`

**Origin = upstream**, from `90c02175` ("cue_writer: fix pregap duration with append-to-prevous mode", Lynne, 2023-05-19, pre-fork):
> `src/cue_writer.c` — `if (t->pregap_lsn != CDIO_INVALID_LSN && t->pt && …)` … `cyanrip_frames_to_cue(t->pregap_lsn - t->pt->start_lsn + 1, time_00);`

Same "previous track on disc, ripped or not" reference, three years before the fork existed. The fork changed `start_lsn` → `start_lsn_sig` and added ISRC; it did not author the defect.

**Not a duplicate of a closed item.** The two prior `INDEX 00` cue items are both closed and different: the ISRC drop (fixed — visible as `ISRC GBAAM0201148` on line 29 of the rig cue) and the zero-length-pre-gap marker "one frame past the end of the previous FILE" (`CHANGELOG.md:1355-1357`, fixed by the `start_lsn` → `start_lsn_sig` change). This one is 682 frames, not 1, and its trigger is `-l`, not a zero-length gap.

**One thing that is NOT a defect**, so you do not chase it: the bare `INDEX 01 00:00:00` under `FILE "05 - …"` with no `TRACK` line is the standard gap-appended cue layout and is documented as intended in our own parser at `src/platterpus/cue_validate.py:244-256`.

#### Why it is yours

cyanrip writes the cue; Platterpus only reads it. Nothing under `src/platterpus/` writes or edits a cue — a grep for cue writes returns only readers (`cue_validate.py`, `ctdb/toc.py`, `rip_progress.py`).

#### Suggested fix

In `cyanrip_cue_track()`, an appended pre-gap can only be written when the previous track's FILE was actually written. Extend `crip_track_has_appended_pregap()` (`src/cue_writer.h`) with a "previous track is in the rip set" input — the `-l` selection is already known at cue-write time — and drop the `TRACK`/`TITLE`/`PERFORMER`/`ISRC`/`INDEX 00` block when it is false, emitting the track normally under its own FILE instead. That is the semantically right answer: the rig log shows track 5 is 18072 frames in both the full and the partial rip, so the 115 pre-gap frames are in no file at all and there is nothing for a marker to point at.

Independently of that, add the cheap invariant at the print site: an `INDEX 00` is an offset into the currently open FILE, so `pregap_lsn - pt->start_lsn_sig` must be < the frame count of the FILE the marker is nested under. Refuse (and log) rather than emit a marker past EOF — this catches the whole class, including the already-fixed one-frame variant.

Ask back: a regression test over a `-l` selection that skips a track with a signalled pre-gap on the following track (`tests/cuegap.c` already exists for this predicate and is the natural home).

**Companion item that is OURS, filed here only so you know it is covered:** `src/platterpus/cue_validate.py:655-666` deliberately `continue`s on exactly this case — "On a selection of tracks 3 and 5, track 5's gap has nowhere to go (track 4 was not ripped), and its absent marker is correct rather than a defect" — i.e. our validator assumed cyanrip would *omit* the marker, so the one check that reads the cue skips precisely where the defect occurs. It should assert the marker is absent or in range, not skip. That is ours to fix.

#### What it costs a consumer

A shipped, routinely-reachable user path corrupts an archival artifact. `-l` is driven by the per-track "Rip?" checkboxes in the GUI, so any partial rip where the user deselects a track whose successor has a signalled pre-gap emits a cue with a marker pointing past the end of the file it names. Audio is unaffected; the cue is the artifact a burner, tagger or tracker uses to reconstruct the disc, and a strict consumer reading `INDEX 00` beyond EOF either errors or mis-seeks. It also silently asserts that pre-gap audio is present in a file when the rip contains it nowhere.

Blast radius is bounded — it needs a partial rip *and* an excluded track immediately preceding one with a sub-channel/TOC pre-gap — which is why this is medium and why under S-14 it is NEXT-ROUND: it does not affect the full-disc rip that round 8's acceptance criteria are measured on.

Two things make it worth sending anyway. First, it is upstream-origin, so it also affects stock cyanrip users and is a genuine upstream PR candidate — and "roll back to upstream" is not a mitigation for it. Second, it is currently undetectable on our side, per the companion item above: no Platterpus check, log line or report field would ever surface it to a user.

---

### 9. `-t` and `-p` disagree on out-of-range policy: `-t 99=` kills the whole rip, `-p 99=drop` is accepted and silently never applied

**Severity: medium. Origin: upstream, proven from source in both trees.**

#### What it is

Both flags take a track index and resolve it against the same disc, and they treat an out-of-range one in opposite ways — one fatally, one silently.

`-t`: an index not present on the disc is fatal to the entire invocation. `cyanrip_main.c:2000-2009` scans `ctx->tracks[]` for a matching `number` and, on no match, logs `Invalid track number %i, list has %i tracks!`, increments `total_error_count` and `goto end`. Nothing is ripped. A *tag* for a track that does not exist destroys the rip.

`-p`: the index IS validated, but never against the disc. `cyanrip_main.c:1648-1675` bounds it `idx < 1 || idx > 197` — a fixed cap, not a disc-relative one — then writes `settings.pregap_action[idx - 1] = act`. So `-p 99=drop` on a 2-track disc is accepted, exits 0, and the directive is stored into a slot no track will ever read. No message, no exit code, no effect.

The asymmetry has a structural cause worth stating, because it constrains the fix: `-p` is parsed in the pre-disc option block, before the TOC is read, so `ctx->nb_tracks` is not yet known at line 1656. `-t` is validated at line 2004, after `ctx->tracks[]` exists. Bounding `-p` correctly therefore means deferring or repeating its index check after the TOC read, not tightening the existing one.

**Third element, from the same rows.** `-p 99=drop` is a literal counterexample to the generated argv table's own headline. It was accepted, took no effect, and was graded `accepted` purely because the probe has no observation channel — its result cell reads `(no header field exposes this)`, as do 48 other rows. `**Silently-ignored values: none.**` is therefore a claim the probe as built cannot make; it is a check that can only pass by finding nothing. Our own round-8 lap 8 cites that headline back at you as reassurance, so the claim is already load-bearing across the seam.

#### Evidence

From the generated table (`docs/seam-commands.md` §7 is explicitly your half: `:291` "**This section is GENERATED** by `tools/probe-argv-surface.py --markdown`"; `:34` "Each side probes its own binary. Neither probes the other's."):

> `docs/seam-commands.md:486` — ``| `-t` | track metadata | `'99=title=x'` | **refused** | 1 | Invalid track number 99, list has 2 tracks! |``
> `:485` — ``| `-t` | track metadata | `'0=title=x'` | **refused** | 1 | Invalid track number 0, list has 2 tracks! |``
> `:504` — ``| `-p` | pregap action | `'99=drop'` | **accepted** | 0 | (no header field exposes this) |``
> `:506` — ``| `-p` | pregap action | `'=drop'` | **refused** | 1 | Invalid track idx for pregap: 0 |``
> `:295-297` — "Method: `-I` on a disc image, so this probes argument handling and not the drive… **`ignored` means exit 0 and the value gone** — the outcome S-9 most wants recorded, and there are none."
> `:529` — "**111 probes: 65 accepted, 46 refused, 0 silently ignored.**"
> `:531` — "**Silently-ignored values: none.** Every value either took effect or was refused with a message."
> `grep -c "no header field exposes this" docs/seam-commands.md` → **49**

Real-world damage, the `-t` half:
> `CHANGELOG.md:3254-3255` — "MusicBrainz medium we used listed 18; Platterpus passed cyanrip `-t 17=` and `-t 18=`. cyanrip answered `Invalid track number 17, list has 16 tracks!` and exited — **two seconds, nothing**"
> `docs/seam-rules.md:112` — "this is the difference between a bad tag and a lost rip. `-t 17=` on a 16-track disc killed a rip in **two seconds**; the type was fine"

**Still present at fork HEAD** (`rmccann-hub/cyanrip@platterpus-fork`, newer than `ddf7ac3`), `src/cyanrip_main.c`, line numbers matching the `gea2793a` contract exactly:
> ```
> 1648  for (int i = 0; i < 198 && pregap[i]; i++) {
> 1650      /* Same shape as -c above: "-p =" tokenises to nothing. */
> 1655      idx = strtol(p, NULL, 10);
> 1656      if (idx < 1 || idx > 197) {
> 1657          cyanrip_log(ctx, 0, "Invalid track idx for pregap: %i\n", idx);
> 1674      settings.pregap_action[idx - 1] = act;
> 2000  for (; track_idx < ctx->nb_tracks; track_idx++) {
> 2004      if (track_idx >= ctx->nb_tracks) {
> 2005          cyanrip_log(ctx, 0, "Invalid track number %i, list has %i tracks!\n",
> 2007          ctx->total_error_count++;
> 2008          goto end;
> ```
Note line 1650 — your own lap-32 segfault fix comment sits three lines above the unfixed bound, which is how we know the area was touched without the bound being revisited.

**Origin proven upstream** — `repo:cyanreg/cyanrip`, `src/cyanrip_main.c @52fbc89`, byte-identical:
> `idx = strtol(p, NULL, 10);\n        if (idx < 1 || idx > 197) {\n            cyanrip_log(ctx, 0, "Invalid track idx for pregap: %i\n", idx);\n            return 1;`
> `if (track_idx >= ctx->nb_tracks) {\n            cyanrip_log(ctx, 0, "Invalid track number %i, list has %i tracks!\n",\n                        u_nb, ctx->nb_tracks);`

Both are still published as current contract surface: `round-08-lap-01-provider-contract-gea2793a.md:351` and `:367`.

The reference-log diff was inapplicable here (argv-parse refusals never reach a rip log), so origin was derived from the two source trees instead.

**Not a round-8 duplicate.** A grep for `Invalid track number|Invalid track idx|silently ignored|99=drop` across inbound lap 1, outbound lap 2 and verified lap 8 yields exactly one hit, and it is the headline being *trusted*, not questioned: `verified/round-08-lap-08.md:201-202` — "**Your argv gate already runs this test** (round 7 lap 38: *111 probes / 0 crashed*). That is where it belongs." Round 8 lap 8 §B3 is about `-t 1` — the missing-`=` shape — not the out-of-range index.

#### Why it is yours

Platterpus already does everything a consumer can. We pre-filter `-t` at the argv chokepoint:
> `src/platterpus/adapters/cyanrip_backend.py:830-844` — "# Dropping the surplus costs a few tags on tracks that do not exist; passing it costs the entire rip." … `if (disc_track_total and isinstance(track.number, int) and track.number > disc_track_total): log.warning("dropping metadata for track %s: the disc has only %d track(s), and cyanrip rejects the whole rip on an out-of-range -t", …); continue`

And we do not emit `-p` at all, so no Platterpus change can make an out-of-range `-p` take effect.

#### Suggested fix

Pick one policy for a track index the disc does not have, apply it to both flags, and say which in the contract.

1. **`-p` — bound it against the disc, not against 197.** The check at `cyanrip_main.c:1656` runs before the TOC is read, so the fix is a second pass after the TOC read (beside the `-t` validation at 2004) that rejects — or, under policy 2, warns-and-drops — any `pregap_action` slot beyond the disc's real track count. Reuse the `-t` message shape so one consumer matcher covers both.
2. **`-t` — decide whether an out-of-range index should keep aborting.** If it should not: at `:2004-2008`, drop that one `-t` pair with a warning and continue, keeping the fatal path for structurally malformed input (the `-t 1` missing-`=` case, which our lap 8 §B3 agrees should stay refused). If it must stay fatal, say so as deliberate policy in the provider contract so consumers know the bound is theirs to enforce — and note the same fatal path is duplicated at `:2070` and at `:2227` (`Invalid rip index %i, list has %i tracks!`); whatever is decided should be decided for all three.
3. **The probe's grading vocabulary.** Split the outcome into four states — `refused` / `took effect (observed)` / `accepted, effect not observable` / `ignored` — and stop printing `Silently-ignored values: none` while any row is in the third. The `-j` machine-readable diagnostics record already exists and is the obvious observation channel: echo the effective `pregap_action[]`, `-t` tag set and other applied settings into it, and the probe can compare intent against effect instead of against exit status.

**Order matters: fix 3 first.** Without an observation channel the probe cannot prove either of the first two fixes landed, and a revert of fix 1 would still read as `accepted`, exit 0, `0 silently ignored`.

#### What it costs a consumer

The `-t` half has measured, real-world cost: a 16-track disc plus an 18-track MusicBrainz medium ended a rig rip in two seconds with nothing written (rig, 2026-08-02). Platterpus is protected today, but by a bound reimplemented in one consumer — every other cyanrip caller has to discover the same lesson the same way, and the guard is one refactor away from being the thing that regresses.

The `-p` half is the more dangerous shape even though it is currently unreachable from us: a pregap directive that is accepted, exits 0, and takes no effect puts wrong track boundaries and a wrong `.cue` into an archival record with a clean-looking log — the failure class the seam rules call worse than a refusal, because a refusal gets investigated and a success gets filed. It becomes live for us the moment gap-mode handling is driven through `-p`.

Both are inherited from upstream, which means the usual mitigation does not exist: rolling back to stock cyanrip restores the identical code. This is the third instance of that pattern after the `-V` removal and the `MM:SS.FF` duration-shape change.

The third element is the one that generalises: `Silently-ignored values: none` is a headline the probe as built cannot support, 49 rows are blind, and our own lap 8 already quotes it back across the seam as evidence.

---

### 10. `Extraction speed:` / `Elapsed:` are the only fork-only per-track measurements the contract's "units that are not obvious" block does not define

**Severity: low. Origin: fork, proven by diffing the two reference logs.**

#### What it is

The provider contract has a block that exists precisely to define quantities a consumer cannot infer from the line itself — "**Units that are not obvious from the line itself:**" (`:102`). It defines `Total time:`/`duration:` (MM:SS.FF frames), `Pregap length:` (frames), `Sample peak level:`/`True peak level:` (% FS and dBFS), the paranoia counters as raw callback counts, the A8 per-track-vs-disc scope rule, and the Q10 `-l` denominator. `Extraction speed:` and `Elapsed:` appear nowhere in it — they exist in the contract only as bare format strings in the stable-line table at `:231-232`.

Both are fork-only lines (stock 0.9.3 emits neither), so there is no upstream documentation to fall back on, and the interval is not derivable from the number: track 1 of the round-8 rig rip shows `Duration: 03:13.12` (193.16 s) against `Elapsed: 214.29 s`, giving exactly the printed `0.9x`, which is self-consistent whether the elapsed brackets read only, read plus encode, plus the AccurateRip query, or plus `-Z` re-reads.

**This is not an accuracy complaint.** The number is internally consistent and the rig's `Paranoia level: max` / `Frame retries: 5` / `Speed: default (unchangeable)` fully accounts for a near-1x read. It is a comparability problem: Platterpus renders your speed value verbatim into the `     Extraction speed N.N X` row of its EAC-compatible archival log, directly opposite EAC's own row for the same disc and drive, which on this Pioneer BDR-209D reads 1.6 X to 3.5 X. A reader placing the two logs side by side is comparing two rows with the same label and two intervals, only one of which is defined.

#### Evidence

> `docs/handshake/inbound/artifacts/round-08-lap-01-provider-contract-gea2793a.md:102`
> "**Units that are not obvious from the line itself:**"

and its bullets, `:104-124`, cover only:
> `:104` - `Total time:` and every `duration:` is **`MM:SS.FF`, where FF is CD frames**
> `:112` - `Pregap length:` is in **frames**, stated in the line.
> `:113` - `Sample peak level:` is a percentage of full scale **and** dBFS;
> `:115` - Paranoia counters are **raw callback counts**, not rates or scores
> `:117` - **Paranoia counter scope (A8).**
> `:125` - **Paranoia counter denominator under `-l` (Q10).**

(the very next line, `:131`, is `## P2 - Outputs: stable log lines (the API)`)

Whole-file grep of that contract for `elapsed|extraction speed`, case-insensitive, returns only:
> `:231` ``| `cyanrip_log.c:382` | `Extraction speed:  %.1fx` |``
> `:232` ``| `cyanrip_log.c:384` | `Elapsed:            %.2f s` |``

Live at the newest build — `docs/handshake/artifactsround08/round08riplog.log:1` `cyanrip 0.9.4-rc1+platterpus.6-beta.4 (platterpus-fork-g2ce8993)`; `:75,82,83`:
> ```
>     Duration:    03:13.12
>     Extraction speed:  0.9x
>     Elapsed:            214.29 s
> ```
`:11,15,16` `Speed:          default (unchangeable)` / `Paranoia level: max` / `Frame retries:  5`

EAC comparator — `output_reference/EAC_flac/eac_baseline_police_classics.log` (UTF-16LE), decoded lines 57…231: `Extraction speed 1.6 X` … `3.5 X`.

**Origin proof (diff of the two reference logs):**
> `grep -c -i "Extraction speed|Elapsed" output_reference/cyanrip_flac/*.log` → **0** (stock upstream 0.9.3)
> `output_reference/cyanrip_fork_flac/cyanrip_fork_police_classics.log:74` `    Extraction speed:  0.9x`
> `:75` `    Elapsed:            214.59 s`

Corroborated by `docs/cyanrip-consumer-contract.md` §1, where `track_extraction_speed` and `track_elapsed_seconds` are both tagged **(fork-only)**. (This read *"all three regexes"* while a third rule, `track_elapsed_clock`, existed; it was retired 2026-08-21 — it read a `(HH:)MM:SS` clock that no cyanrip build has ever emitted, including the pre-split combined form, whose trailing ` (0.9x)` its end-of-line anchor refused.)

Materiality on our side:
> `src/platterpus/eac_log_export.py:1244-1250` — renders your number into EAC's own row.
> `:1254-1260` — "Why a row of our own rather than deriving EAC's speed from it: the speed multiple is `audio duration / elapsed`, and *what the elapsed covers* is unknown (does it include the encode? the AccurateRip lookup? a `-Z` re-read?). A number computed from an interval we cannot define is a guess wearing EAC's label — the one thing this module exists to refuse."

**A correction we owe you, because we nearly sent this as an unhonoured ask.** An earlier draft claimed round 1 had asked for the definition and quoted a sentence "Say the definition in the log or the number is noise". **That sentence does not exist** — a repo-wide grep returns one hit, `docs/handshake/inbound/round-07-lap-01.md:597`, which is your own text about sample-peak disagreement and unrelated. What round 1 actually said (`docs/handshake/outbound/round-1.md:84-88`) was "**Print both halves if you can.** Platterpus deliberately does **not** derive one from the other: what your interval covers … is unknown to us". You printed both halves. The ask was answered in full. **This is a new ask, not an unhonoured one.**

#### Why it is yours

Only the ripper knows which clock stamps bracket which stage. Our own code states the refusal to infer (`eac_log_export.py:1254-1260`, `rip_report.py:1355-1358`), but that refusal does not reach the speed row, because that value is yours.

#### Suggested fix

Add one bullet to the existing "**Units that are not obvious from the line itself:**" block (after `:124`, beside the `Pregap length:` and peak-level entries), naming the interval explicitly:

- `Elapsed:` is wall-clock seconds between \<the two stamps\>, and covers \<read | read + encode | + the AccurateRip query | + every `-Z` pass or only the final one\>. `Extraction speed:` is `audio duration / Elapsed` over that same interval — state it, so a consumer knows it is not a drive-speed multiple.

The four sub-questions worth answering by name, because each changes whether the number is comparable to EAC's row: (1) does the interval start before or after the drive seek/spin-up? (2) does it include the FLAC/encoder time? (3) does it include the AccurateRip lookup? (4) under `-Z N`, is it the final pass only (matching the A8 per-track paranoia scope) or every pass?

If — and only if — the interval turns out to include anything beyond the read, a second, read-only figure would let the EAC row be filled with a genuinely comparable multiple; that is a NEXT-ROUND nice-to-have, not part of this ask. The contract sentence is the whole fix.

#### What it costs a consumer

Record-only; no audio, checksum, pregap or verdict consequence. The number reaches the EAC-compatible archival log filling the row EAC labels `Extraction speed`, where a reader comparing our log to a real EAC log for the same disc and drive sees 0.9–1.1 X against 1.6–3.5 X. Whether that difference is a real read-rate difference or an artefact of a wider interval is currently unanswerable from either side's published documents, which makes the comparison unsound in both directions — it could equally hide a genuine performance fact as invent one. Cost to fix is one sentence in a block you already maintain; cost of leaving it is a permanently ambiguous cell in an archival record whose entire purpose is to be trusted decades later without the ripper present.

---

## 10b. An ask, not a finding: make your builds listable

**This is the one thing in this document we want *from* you rather than
something we found wrong.** It is a NEXT-ROUND ask under S-14 and blocks
nothing.

**What we built on our side (v0.6.12b6).** `--install-ripper list` now prints
the cyanrip builds a given Platterpus knows how to install, each with the build
tag a correct build must print:

```
  ✓ approved: ddf7ac3 (platterpus-fork-gddf7ac3)
  ⚠ test-pin: cb440bd (platterpus-fork-gcb440bd)
```

Naming the **tag**, not just the role, is the point. A menu offering "the newest
beta" asks an operator to choose a build they cannot identify afterwards — which
is exactly how a rig session on 2026-08-13 produced a clean, complete artifact
set for `g2ce8993` while the round under review was `ddf7ac3`. Every file looked
right and answered a question nobody had asked.

**What we deliberately did NOT build, and why it needs you.** The menu lists only
what we can state from our own constants. It does not ask GitHub for your newest
builds, because doing so needs facts about your release practice that we do not
hold, and guessing would produce a menu that looks authoritative while listing
builds that may not exist. Concretely:

1. **Do you publish GitHub releases on the fork at all**, or only tags/branches?
2. **How is a beta distinguishable from a release** — a tag-name convention, the
   API's `prerelease` flag, or neither? We learned the hard way on our own
   releases that the API flag is uninformative and the *version string* is the
   reliable signal (`update_check.is_prerelease_version` exists for that reason);
   we would rather adopt your convention than infer one.
3. **Does each release name its build tag** in a place a machine can read, so a
   listing can show `platterpus-fork-g<sha>` without cloning and building first?

**If the answer to (1) is "no", say so and we will drop the idea** — a menu that
lists commits from a branch is worse than the pinned menu we have, because a
commit is not a build anyone has tested. That is a perfectly good answer and
costs you nothing.

**The maintainer's framing**, which is what prompted this: an operator updating
either project should be able to choose between the newest official release, the
betas (if they have opted into betas), and the pinned builds — in that order,
with the tag shown for each. We now have the app half and the pinned half. The
"newest official / newest beta" half of the *ripper* menu is the part that only
you can make truthful.

---

## 11. What we checked and dropped

Saying what we discarded is part of an honest hand-off. Several of these are things you have already fixed, and we would rather show you we checked than hand you work you have done — and knowing which of your fixes we *wrongly believed were still open* tells you which ones never reached your consumer's documentation.

**The numbers.** 87 raw candidates were gathered from 7 evidence sources. Two verification passes examined **26** of them individually. **10 survived** (the ten above). **16 were refuted or excluded.** The remaining **61 were never individually verified and are not in this document** — see §13.

### Pass 1 — 14 examined, 3 survived, 11 dropped

1. **Cue writer omits ISRC in the appended-pregap branch** — real, and **already fixed** by fork `e7f6a97`, hardware-confirmed 14/14 at lap 35; `ddf7ac3` carries byte-identical C source to that build. Also: our stated origin was wrong and we retracted it — the ISRC-less branch is upstream `a0de6a0`; the fork changed only its reachability.
2. **Logfile block-buffering lost verified track records on kill** — the round-1 headline; **fixed in round 2** by `setvbuf(_IOLBF)` on log and cue, revert-proofed 3/3 in round 4. The only residual is our own stale present-tense comment.
3. **`Ripping errors:` never reflects `-Z` non-convergence** — **already asked and answered from source** in round 5 Q3 ("`0` is correct by design"), and the fix we actually asked for shipped as the per-track `Secure re-read:  did NOT converge…` line. The remaining roll-up is arithmetic over lines we already parse, i.e. ours.
4. **Disc-level vs per-track paranoia counter semantics under `-Z`** — real residual, but it is **live round-8 correspondence in both directions** (your lap 1 §J item 4, our lap 2), so it is excluded here to avoid double-counting. Also our origin call was inverted: the per-track block is *fork*, not upstream — it was our own round-5 W1 ask.
5. **`:` escaping in `-a`/`-t`** — **superseded**. `\:` always was the escape; the pre-splitter became escape-aware upstream (`f7a341e`); we retired the U+2236 substitute at lap 31 and confirmed it at the drive at lap 35.
6. **Positional `Done;` verdict** — **already delivered** as the enum-backed `Secure re-read:` row (round 7 lap 4); we keep parsing `Done;` deliberately as a stock-upstream fallback. The one-track verdict shift was our own spec error, self-recorded in round 2.
7. **No measured cache-defeat verdict** — **refuted**: `-x` / `--cache-probe` already emits a measured tri-state `Cache probe:` line, and did so in the very build cited as proof it was missing. The cited log lacks it because our argv does not pass `-x`.
8. **`Total time:` fractional field is CD frames, not ms** — **already asked (round 5 Q2) and delivered (round 6c)**; the current contract states the unit, range, PR #130 attribution and the discrimination rule. Our stale comment is ours to fix.
9. **Pregap LSN labelled as a length / unspecified unit** — **fixed at `ddf7ac3`** by `Pregap length:` / `Pregap source:`, and the "unspecified unit" half is refuted twice over: the contract states frames in bold, and the cited artifact's own 14 duration/length pairs pin frames arithmetically.
10. **`Peak level:` renamed repeatedly** — **refuted**: one fork rename, announced in advance in round 6 D1 with a Was/Is table and an explicit consumer warning, and now frozen as a P2 stable line. The alleged third spelling is libavfilter's, which you already disclaim.
11. **`Tracks ripped partially accurately:` denominator** — **already agreed** by you in lap 24 as a round-8 rename, and the substantive half landed in `d1d8312`; at `ddf7ac3` the number is correct.

### Pass 2 — 12 examined, 7 survived, 5 dropped

Two were refuted on evidence:

12. **`Cache model:` has no branch consuming an `-x` result** — refuted on two independent grounds. The evidence does not show the claimed contradiction: both cited rip logs ran *without* `-x` (verified by tokenising the argv line of each). And the probe method is already a known-untrustworthy one you deferred to round 10.
13. **Exit code 1 for every failure class (S-12 `generic`)** — refuted. It is already your own standing defect row, one cited line range was wrong, and the cited release-blocker mechanism does not exist in our probe; Platterpus fixed the entire cited harm on its own side.

Three were real but are **already live in the correspondence**, so we excluded them rather than double-count. They are listed because "we dropped it" should not read as "we decided it was wrong":

14. **`Accurip 450:` returns an identical checksum across three reads of one track that produced three different EAC CRC32s** — survives every check and is arguably stronger than filed, but it is already round-07-lap-27 §E with its own verdict-table row and question L1. Yours, still open there.
15. **The disc-image silence defect is live in upstream master and was never reported upstream** — survives every check, decisively evidenced from outside our own docs. You agreed twice in round 7 to file it; no upstream issue exists. Left with round 7 rather than re-raised here.
16. **P1 still lacks the promised note that a cancelled rip leaves 0-byte FLACs for tracks the log calls successful** — survives every gate; our half (stat every file the log claims, refuse to call a 0-byte FLAC verified) is already implemented. Already asked; not re-raised.

---

## 12. The staleness is our defect, and we are fixing it

The single largest finding of this exercise is not in the list above. It is that **our own documentation describes a cyanrip that no longer exists.**

Of the 16 candidates we examined and dropped, the dominant cause was *already fixed at `ddf7ac3`* — the cache probe, the `Done;` verdict line, the pregap LSN row, ISRC in the appended-pregap cue branch, log/cue line buffering, the `\:` escape, the `Total time:` unit, the `Peak level:` rename, the partially-accurate denominator. Nine of your shipped fixes were still being described as open problems in our source comments, our ask list (now Part C of this file, then the former `cyanrip-upstream.md`), and our parity documents. In two cases (`docs/eac-parity.md:141`, `docs/dependency-contracts.md:327-331`) our documents promise users a preservation behaviour that we had not re-checked against your current defaults.

That is a real cost to you: a consumer whose documentation lags by four rounds sends you work you have already done, and reasons about your behaviour from a snapshot. It is also a cost to us, because it is exactly the failure our own rules name — a map that is only ever wrong by omission, and nobody reviews a file for what is not in it.

Three things we are doing about it, none of which needs anything from you:

1. **Re-derive rather than re-read.** `docs/cyanrip-consumer-contract.md` is generated from our parser; the *complementary* check — every rule we declare must appear in your current P2 — does not exist, and `tests/test_provider_contract_agreement.py` still hardcodes `round-4.md` while its docstring claims it re-derives from the newest contract. Fixing that converse assertion is what would have caught §6 in-house, and it would have caught most of the nine stale beliefs above automatically.
2. **Sweep the ask list against the current contract.** The ask list (now Part C of this file, then the former `cyanrip-upstream.md`) is a ranked list of things we want from cyanrip; several entries are already delivered. It gets re-derived, not re-read.
3. **Treat a present-tense comment about a dependency defect as a claim with an expiry date.** Where our source comments and this document disagree, **this document is the current position.**

The one thing worth asking of you, and it is §4 and §5 rather than a new item: the reason we could not fully trust our own staleness check is that the contract we checked against did not describe the build it named. That is the cheapest single fix on this whole list, and it makes every future check of this kind sound.

---

## 13. Coverage limits, plainly

- **87** raw candidates were gathered from 7 evidence sources (source comments, our task file, the ask list, the parity documents, the consumer contract, the committed handshake correspondence, and the 2026-08-13 rig artifacts).
- **26** were examined individually and adversarially. **10 survived** and are above. **16** were refuted or excluded, and all 16 are named in §11 — none was dropped silently.
- **61 were never individually verified and are NOT in this document.** They are not a queue of known issues; they are unexamined candidates, and on the measured base rate roughly two-thirds of them would be refuted. We are not sending you a list whose hit rate we know to be poor.
- **An earlier draft carried five additional "unverified candidates"** — `-S` fatal on a speed-locked drive, `REPLAYGAIN_TRACK_PEAK` written from the true peak, the `-j` record's missing schema, de-emphasis defaults and checksum ordering, and the `.cue`'s unpublished contract half including the `REM MEDIA_TYPE` → `REM MEDIA` rename. They are **not included here**, because they had not been through refutation and this exercise has just demonstrated what that is worth. Several look strong. If you want them as questions rather than findings, say so and we will verify them properly first.
- **Freshness bound.** The newest provider contract we hold is `gea2793a` (round 8 lap 1). The newest binary we have observed is `platterpus-fork-g2ce8993` (`+platterpus.6-beta.4`, rig, 2026-08-13). We do not hold round 8 laps 3–7 (our lap 8 §F2 asks for them). Any finding above could have been fixed in a lap we do not have; each says which artifact it was last checked against so you can dismiss it in one line if so.
- **One finding carries an explicit last-mile inference** rather than direct proof at the current pin: §7's claim that the ebur128 lines are *still* uncaptured rests on the schema, note and field set being byte-identical at the newer build plus no commit touching capture scope, because the only `-j` record we hold from that build is a refused argv probe with no loudness block. You can settle it in one command.
- **Nothing here is offered as blocking.** Under S-14 every item defaults to NEXT-ROUND, and none of them makes `ddf7ac3` unsafe. Round 8 stands exactly where our lap 8 left it.

---

*Last updated for Platterpus v0.7.130.*
