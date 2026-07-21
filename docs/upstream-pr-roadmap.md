# Upstream-PR roadmap (contributor instructions)

> **Update (2026-07-08, soft-fork decision):** two prepared, higher-readiness
> cyanrip contributions now exist *alongside* this ranked list — the `-a`/`-t`
> **meta-colon parsing fix** (⭐ do first; verified patch + ASan/UBSan proof)
> and **full libavcodec encoder options**. Runbook:
> [`cyanrip-soft-fork.md`](cyanrip-soft-fork.md); one-command execution kit:
> `scripts/cyanrip/` (paste-ready issue/PR bodies live there).

> **What this is.** The concrete, *ordered* answer to "which upstream pull
> requests would close our remaining ripper-engine gaps, in what order, and how
> do I do each one." It turns the per-gap option menu in
> [`ripper-engine-strategy.md` §10](ripper-engine-strategy.md) into a ranked
> action list with step-by-step instructions. **PR-first policy** (the
> maintainer's standing rule): we open a pull request from our own fork and are
> *adaptable* to the upstream maintainer's merge decision — a fork we maintain is
> the fallback, never the goal. The **signed EAC log checksum is permanently out
> of scope** — it is forgery of another tool's provenance and we do not fake
> anything (Critical rule spirit; `docs/eac-log-and-repair-feasibility.md`).
>
> Sourced from a 4-agent research sweep (2026-07-07) of cyanrip, whipper,
> OPSnet/Logchecker, libcdio-paranoia and cdrdao. Findings are point-in-time
> (read off public GitHub pages — the GitHub API here is scoped to this repo);
> **re-check live state before investing build/test time.** Uncertainties are
> flagged inline.

---

## The one question you asked first: "do I need to be a collaborator?"

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

## The ranked list at a glance

| # | Gap | Where | Verdict | Effort | Odds |
|---|-----|-------|---------|--------|------|
| — | **gap / INDEX-00 pregap + HTOA** | **Platterpus-side `cdrdao` integration** | **Fallback if #115 stalls** (see the 2026-07-07 update box) | Moderate | N/A — lands in our repo |
| 1 | gap / INDEX-00 pregap + HTOA | cyanrip **PR #115** (exists) | **Support the existing PR** | Low (test + review) | Medium-good |
| 2 | stable machine-parseable cyanrip log | cyanrip (new PR) | Do only if committing to #3 | Moderate-hard | Low value |
| 3 | tracker recognizes cyanrip | OPSnet/Logchecker (new PR) | **Skip for now** | Hard (2-repo) | Low |
| 4 | C2 error pointers (+ cache-defeat line) | libcdio-paranoia → cyanrip | **Skip** (keep deferred) | Hard (2-repo) | Very low |
| — | tracker recognition via a recognized ripper | **Re-add whipper (Platterpus-side)** | Fallback, hardware-gated | Moderate | N/A — no PR |

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

## DO-LATER / FALLBACK (no upstream PR) — cdrdao integration for pregap/INDEX-00 + HTOA

**Reconsidered (see the update box above): prefer landing cyanrip PR #115 over
this.** Keep this only as the fallback if #115 stalls. It is not a contribution —
it lands entirely in Platterpus. cdrdao is GPL-2-only, but we invoke every tool
as a **subprocess** (never link it — KDD-10's aggregation model, routed like every backend subprocess per Critical rule #3), so GPL-2-only is fully
compatible with our GPL-3.0 GUI. This is *exactly how whipper obtained gaps.*

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

## Order 1 — support cyanrip PR #115 (don't open a competing PR)

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

## Order 2 — a stable, machine-parseable cyanrip log (only if you commit to #3)

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

## Order 3 — add cyanrip to the OPSnet/Logchecker allow-list

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
  expect a stall, and treat **re-adding whipper** (below) as the honest fallback.
- **Steps (if pursued):** *first* comment on issue #13 (or open a fresh issue)
  proposing cyanrip support and gauge the response — the responsiveness signal is
  the whole risk. Only if the maintainer engages: fork, branch, edit
  `Ripper.php` + `Logchecker.php`, run `composer test` / `composer lint` /
  `composer static-analysis` (phpunit/phpcs/phpstan, PHP 8.1+), verify with the
  `analyze` command on a real cyanrip log, open the PR from your fork, be patient
  (or walk away to the whipper fallback).

---

## Order 4 — C2 error pointers (and the cache-defeat verdict line)

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

## The honest tracker fallback — re-add whipper (Platterpus-side, no PR)

**If tracker acceptance ever becomes a real goal, this — not Orders 2+3 — is the
honest path,** and it needs **no upstream PR at all**:

- whipper's **native YAML rip log is already a first-class recognized + scored
  format** in `orpheusnet/logchecker`: `Ripper.php` matches `"Log created by:
  whipper"` and `Logchecker.php` has a full `whipperParse()`. So tracker
  recognition via whipper is **purely a Platterpus-side second `RipBackend`
  adapter** that runs whipper and keeps its native `.log`. The
  `RipBackend` ABC seam (`adapters/rip_backend.py`) anticipates this — a
  `Config.ripper_backend` selector existed while both backends shipped, was
  removed with whipper (2026-06-30), and would return with a second engine
  (strategy-doc §0).
- **Hard blocker for your own hardware:** whipper orchestrates cd-paranoia, which
  carries the **>587-sample read-offset bug** that *failed* tracks on the
  BDR-209D (+667 offset) — the exact bug that drove the whipper→cyanrip switch
  (KDD-18). So re-adding whipper is gated on a cd-paranoia offset fix or a
  different drive, independent of tracker recognition.
- **Verify before relying on it:** run `orpheusnet/logchecker`'s `analyze` on an
  actual whipper ≥0.7.3 native `.log` to confirm the recognition claim (it's from
  reading their source, not an empirical run this session).

**Do NOT** pursue `whipper-plugin-eaclogger` issue #7 — it asks to implement
EAC's real proprietary log signing so the log passes EAC's checksum validator.
That *is* the signed-EAC-checksum forgery we permanently rule out, and it's
unnecessary because the whipper native-YAML path already yields a recognized log.
Neither consume nor contribute to it.

---

## Verify-before-you-invest checklist (uncertainties, honestly flagged)

Everything above is point-in-time. Before spending build/test hours:

- [ ] **cyanrip PR #115** — confirm it's still open and read the latest review
      round (it may have merged, closed, or moved).
- [ ] **libcdio-paranoia #3** zero-comment status was read off the HTML issue
      page twice (the GitHub API for non-Platterpus repos was unreachable here) —
      high confidence, not API-confirmed.
- [ ] **C2 "where in code"** (`p_block.c` vs `paranoia.c`) is inferred from the
      directory listing — a starting map, not a confirmed patch site.
- [ ] **Order 2 appetite** — whether cyanreg would freeze a stable log schema is
      unknown; gauge on IRC/an issue before building.
- [ ] **whipper native-YAML → Logchecker recognition** — re-verify empirically
      with the `analyze` command before relying on it as the fallback.
- [ ] **cyanrip release cadence** — master moves but the last tag is ~2 years
      old; a merged cyanrip PR would be consumed from master in the container, an
      explicit maintenance decision.

---

*Filed 2026-07-07. Companion to [`ripper-engine-strategy.md` §10](ripper-engine-strategy.md)
(the per-gap option menu) and [`github-workflow-sop.md`](github-workflow-sop.md)
(the fork + PR mechanics). PR-first, adaptable to the maintainer's call, and we
never fake provenance — the signed EAC checksum stays permanently out of scope.*

---

*Last updated for Platterpus v0.5.0.*
