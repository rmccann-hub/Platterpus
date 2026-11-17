# Verification of the cyanrip audit of 2026-10-27

- **Report checked:** `/home/user/audit-reports/cyanrip/2026-10-27/AUDIT-2026-10-27.md`, all 38
  findings in its YAML block, in that block's order. `P#` is the report's prose item number.
- **Code checked:** snapshot at `590e959`, branch `audited`. The snapshot is shallow, 956 commits
  with the graft at `ae9764e`, so `git blame` stops there.
- **How "Upstream too" was judged:** `master` isn't in the snapshot. I read upstream's tree at
  `b40c1f0` (Lynne, upstream's "RC3" series, merged into the fork's history).
- **Build:** not possible here. There are no FFmpeg, libcurl, libcdio or libmusicbrainz headers
  (`pkg-config` finds none) and no `meson`. Every C claim below rests on reading the code, and no
  claim from a subagent's run (ASan, `/dev/full`, the binary's CUE) was repeated.
- **Remote state:** no remote and no network, so GitHub settings and runs are
  `UNVERIFIABLE-HERE`. The repository-side half of each such finding was checked.

| # | Finding (module: check) | Verdict | Evidence you checked (path:line, command and result) | Note |
|---|---|---|---|---|
| 1 (P1) | C: double free of cover-art `extradata` (BLOCKER) | CONFIRMED | `src/coverart.c:306` takes a shallow `memcpy` of `avf->streams[0]->codecpar`. `:347`/`:355` `avformat_close_input` frees that codecpar's `extradata`. `art->params` is freed with `av_freep` (`:115`), never `avcodec_parameters_free`. `src/coverart.c:62` and `src/cyanrip_encode.c:1491` `memcpy` the same pointer into a new stream, and `avformat_free_context` (`coverart.c:107`, `cyanrip_encode.c:1239`) frees it again. HTTP: `coverart.c:27`. Upstream `b40c1f0`: same at `coverart.c:62,278`, `cyanrip_encode.c:1166` | Worse than "twice". The muxer reads the freed `extradata` in `write_header`, a use-after-free. It is then freed once per format per art (`cyanrip_main.c:3601-3609`) and per track encoder. Only demuxers that set `extradata` trigger it (MP4/H.264, HEIF, AVIF). The Archive's JPEG and PNG don't, so the network vector needs a MITM. Platterpus runs `-N -U` (`docs/handshake/inbound/round-35-lap-08.md:61`), so its rig never fetches. `sizeof(AVCodecParameters)` with `av_calloc` also breaks FFmpeg's "allocate with `avcodec_parameters_alloc`" contract. ASan not rerun |
| 2 (P2) | C: `..` and empty path components (BLOCKER) | OVERSTATED | `src/naming.c:131-146` is the table: only `<>:\|?*/\"` are replaced, so `..` passes. `:436-457` trims a spaces-only component to empty. Tag values sanitize `/` (`HAS_CH_FWDSLASH 0`, `os_compat.h:103`). The comment at `:166-186` names `-D {album_artist}/{album}`. Upstream `b40c1f0` `naming.c:111,369` has the same | True, but **already recorded and in flight**: `docs/KNOWN-ISSUES.md:290-318` ("Found by the claude-code-skills session's review of 2026-10-26, item 3.2", measured at `ed37997`), `docs/handshake/STATUS.md:31` (open), lap 12 S10 (`docs/handshake/round-36-lap-12.md:104`), `Changelog.md:66`. The hold is deliberate: Platterpus predicts folder names, so the fix waits on the handshake. "The scheme Platterpus uses" is stale: KNOWN-ISSUES:309-311 says Platterpus's folder is `{album} [FLAC]`, which can't traverse. Default `-D` is `{album}… [{format}]` (`cyanrip_main.c:2540`), so only custom multi-part schemes are affected. Severity is fine for those users |
| 3 (P9) | python-security: tar member names escape `--into` (BLOCKER) | CONFIRMED | `tools/ingest-bundle.py:552` takes `m.name` from `getmembers()`. `:653` `out = dest / name`, `:654` mkdir, `:665` `write_bytes`. The only `resolve()` is `:617`, on `dest` alone (grep reproduced). `check_sender_hashes` checks the sender's own hashes, so it doesn't help | Rated by `python-security.md:123` ("BLOCKER where reachable"). Input is the owner's Platterpus export, which the report says |
| 4 (P3) | C: `cover_arts[32]` bounds (GAP) | CONFIRMED | `cyanrip_main.c:3070-3071` lets `nb_cover_arts` reach 31 (it returns at 32, before the write). `cyanrip_main.h:523` declares `CRIPArt cover_arts[32]`. `coverart.c:400-418` fetches Front into `[31]` and then Back into `[32]`, which lands on `nb_cover_arts` and the fields after it. Upstream `b40c1f0` `cyanrip_main.c:1879` and `coverart.c:366-381` are the same | Needs 31 `-C` titles with no Front or Back, plus a release whose Archive entry has both |
| 5 (P4) | C: CUE output escaping (GAP) | CONFIRMED | `cue_writer.c:194` prints `FILE "%s"` from `crip_get_path`. The naming sanitizer leaves `\n` alone. `cue_str` (`:56-81`) maps only `"`, `\n` and `\r`. Also `:108` prints the `REM` key unescaped. `tests/rip_images.py:1816-1822` checks TITLE and PERFORMER only. Upstream `b40c1f0` `cue_writer.c:50,161` | The test can't reach `FILE` anyway: `rip()` passes `-F {track}` (`rip_images.py:268`). Lap 12 S9 (`round-36-lap-12.md:96`) records that "tags, the cue sheet and file names keep each value as it came". The fix should account for that wording. Binary run not repeated |
| 6 (P5) | C: unchecked log, CUE and diagnostics writes (GAP) | CONFIRMED | `grep -c ferror` gives 0, 0, 0. `cyanrip_log.c:1506` is the av_log capture path; the main writer is `:1582`, and the log's `fclose` is `:1401`. `cue_writer.c:256` (not 255) is the `fclose`. `diagnostics.c:907-908` too | Known since `docs/AUDIT-2026-09-05.md:226` (lead "e": "exit 0 and empty stderr"). It is recorded but not decided. The `/dev/full` run was not repeated |
| 7 (P6) | C: AcoustID key copied into logs (GAP) | CONFIRMED | `cyanrip_main.c:2390-2405` copies argv verbatim. It is printed at `cyanrip_log.c:960` and `diagnostics.c:654`. `grep -n -i acoustid tools/redact.py` finds nothing | Fork-only: upstream has no `record_invocation`. Exposure on the evidence branch is low because Platterpus never passes the key (`docs/seam-commands.md:150`: "NO: we submit nothing to AcoustID") |
| 8 (P7) | C: lost packet-write error (GAP) | CONFIRMED | `coverart.c:89-91`: the first result is overwritten, and the second call gets `pkt == NULL` after `av_packet_free`, which is a flush. Upstream `b40c1f0` `:89-91` is the same | Also `:86-87` uses the `av_packet_clone` result unchecked |
| 9 (P8) | C: `string_is_url` (DRIFT) | CONFIRMED | `coverart.c:362-369`: every `strncmp` uses length 4, so `httpd.jpg` and `ftps-art.png` match. Upstream `b40c1f0` `:334` is the same | It's a bug, not drift from a declared state, so GAP fits better. Effect: a local file goes to curl as a URL |
| 10 (P10) | python-coding: UNPROBED returns 0 (GAP) | CONFIRMED | `tests/contract_delta.py:47-50` and `tests/lap_commits.py:135-139` both `return 0`. The suite's convention is 77 (`tests/evidence_readers.py:114`, `tests/evidence_tool.py:195`) | |
| 11 (P11) | python-coding: failed `git show` read as "no option" (GAP) | CONFIRMED | `tools/gen-release-manifest.py:164-176`: `except Exception: return base`, and any non-zero exit returns `base` | The docstring (`:150-162`) defends only the "file absent" case |
| 12 (P12) | python-security: `shell=True`, no timeouts (GAP) | OVERSTATED | `tools/check-settled.py:163,168` use `shell=True` with no timeout. `tools/warn-gate.py:95-97` uses `shell=True` **with `timeout=300`**. My AST scan matched the report: 140 subprocess calls, 102 without a timeout. `seam-sync-check.py:135` and `evidence.py:366,372,543,595` have none | Only part of the "no timeout" claim holds for warn-gate. The rest stands |
| 13 (P13) | bash: `mingw-build.sh` strict mode and delete (GAP) | CONFIRMED | No `set -` anywhere (only the line 1 shebang). `:63-64` `cd "$CYANRIPBUILDDIR" && rm -rf "$vcsFolder"`. `bash -c 'cd ""'` succeeds. Empty `tomove`: `printf '%s\0' \| xargs -0ri` ran `mv '' '.dyn'` here | |
| 14 (P14) | bash: hook reports unchecked success (GAP) | CONFIRMED | `.claude/hooks/session-start.sh:19-20` | |
| 15 (P15) | python-coding: no explicit encoding (GAP) | CONFIRMED | AST rerun: `read_text` 193/311 and `write_text` 97/192 have no encoding. `text=` calls with no encoding: 64/64 by my count, 64/66 by the report's. `ingest-bundle.py:674` `sums.open("w")` | |
| 16 (P16) | dim 1: no tier (GAP) | CONFIRMED | The tier `git grep -icE …` exits 1 with no matches. `docs/AUDIT-2026-09-05.md` is an ISTQB-shaped test audit (its lines 1-10) | |
| 17 (P17) | dim 2: false meson floor (DRIFT) | CONFIRMED | `meson.build:22` declares `>=0.53.0`. `meson_options.txt:15-16` uses `+`. `project_source_root()` is at `src/meson.build:70,128` and `tests/meson.build:521`, and `dependency('dl')` at `tests/meson.build:253,262,271`. Upstream `b40c1f0` has none of these and declares the same floor | The 8 warnings weren't rerun: no meson here |
| 18 (P18) | dim 2: no Python floor (GAP) | CONFIRMED | `src/meson.build:69-70` uses `find_program('python3')`. `docs/DEPENDENCIES.md:11` quote matches. No `pyproject.toml` or `ruff.toml`. The only use of `is_relative_to` is `tools/warn-gate.py`, and no feature newer than 3.9 was found | |
| 19 (P19) | dim 3: `.gitattributes`, `.editorconfig` (GAP) | CONFIRMED | `.gitattributes:8` holds one `export-subst` rule. There is no `.editorconfig` | |
| 20 (P20) | dim 3: 16 spent plan files (OVER) | CONFIRMED | Read all 16 headers. Ten say "THIS PLAN WAS EXECUTED", the two round plans say CLOSED or EXECUTED, BETA-NOTE says SUPERSEDED, the runbook says "DO NOT FOLLOW IT", and UPGRADE-CHANNELS says "IS WRONG" | `OPTIMISATION-PLAN.md` and `UPGRADE-CHANNELS-PLAN.md` ("MOSTLY BUILT") are not strictly finished. No recorded decision to keep them was found |
| 21 (P26) | dim 4: deny rules, AGENTS.md, scratch/ (GAP) | CONFIRMED | `.claude/settings.json` holds only the SessionStart hook. `AGENTS.md` and `scratch/` don't exist | |
| 22 (P21) | dim 6: no secret-scan, lint or format gates (GAP) | CONFIRMED | The grep over `tests/meson.build`, `.github/` and `tools/` hits only `.github/fetch-history.sh:44` (`# shellcheck disable`) | Platform secret scanning: `UNVERIFIABLE-HERE` |
| 23 (P22) | git-workflows: ruleset has no PR or status check (GAP) | UNVERIFIABLE-HERE | `CLAUDE.md:241` ("Work lands by pull request…") and `:244` (rulesets block delete and force-push only) match the report | To settle it, run `gh api repos/rmccann-hub/cyanrip/rulesets/24942304`. CLAUDE.md:244 itself records only delete and force-push protection |
| 24 (P23) | dim 6: upstream `main.yml` still active (GAP) | UNVERIFIABLE-HERE | `.github/workflows/ci.yml:3-10` says the inherited workflow "can be disabled without touching master". `ls .github/workflows` shows no `main.yml` | To settle it: the Actions workflows list and run 2 on `648b1dd` |
| 25 (P24) | rebasing: no conflict-marker sweep (GAP) | CONFIRMED | The `git grep` exits 1. Nothing in `ci.yml` or `tests/meson.build` matches a conflict or marker step | |
| 26 (P25) | actions-security: `persist-credentials` (GAP) | CONFIRMED | `ci.yml:71,105,142,221` set no `persist-credentials`. Only `ci.yml:278` and `dependencies.yml:39` set `false` | That the default is `true` in `actions/checkout` v7.0.1 is unverifiable here. `tag-release.yml:41` keeps credentials too, but that job needs `contents: write` |
| 27 (P27) | dim 7: no security contact (UNVERIFIABLE-HERE) | CONFIRMED (local part) | No `SECURITY.md`. `grep -i 'security\|vulnerab' README.md` finds nothing | The private-reporting API reading needs GitHub. The prose says GAP and the YAML says UNVERIFIABLE-HERE |
| 28 (P28) | dim 8: cooldown restates the default (OVER) | WRONG | `.github/dependabot.yml:17-18`. Lines `1-3` already give the reason: "past the same three-day wait as the weekly dependency check" | The fix "record why it stays" is already met in the file. As far as I know Dependabot applies no cooldown unless configured, so "platform default" looks false too. GitHub's docs would settle that |
| 29 (P29) | dim 10: repository description (DRIFT) | UNVERIFIABLE-HERE | Not in the tree | To settle it: the repository's About field. The README's fork block (`README.md:82-90`) says the same thing the report does |
| 30 (P30) | dim 10: OPTIMISATION-PLAN "never run" (DRIFT) | WRONG | Lines 41-43 are quoted correctly, but the file's own status at `docs/OPTIMISATION-PLAN.md:15-17` reads: "D is settled: CI runs, as `ci.yml` … so the 'has never run' below is history" | Already flagged in the file. Item 20 covers deleting it |
| 31 (P31) | dim 10: README installs upstream (GAP) | CONFIRMED | `README.md:38-80` has distribution packages with no note. `:82-90` is annotated as upstream's | |
| 32 (P32) | releases: no tags (GAP) | CONFIRMED (local part) | `docs/release-ledger.tsv`: 38 non-comment rows. `CLAUDE.md:245` quote matches. `tag-release.yml` exists, with `workflow_dispatch` and `contents: write`. `git tag` here gives 0 | Remote tags, the releases list and the run count are `UNVERIFIABLE-HERE`. To settle: `git ls-remote --tags origin`, the Actions runs list |
| 33 (P33) | commits: grammar unchecked (GAP) | CONFIRMED | `CLAUDE.md:290` quote matches. `git log --no-merges -200 --format=%s \| awk 'length>72'` gives 43. A capitalized verb opens 198 of 200 | |
| 34 (P34) | dim 10: no decision record (GAP) | CONFIRMED | `docs/SETTLED.md:13` says "Rewritten in place, never appended to". `CLAUDE.md:147` says the same | CLAUDE.md does record dated operator decisions inline, such as `:141`, `:143` |
| 35 (P35) | house-style: README sections (GAP) | CONFIRMED | `grep -ciE licen README.md` gives 0. Top-level sections are Features, Installation, Metadata, Output, Deemphasis and Links | The upstream carve-out applies, as the report says |
| 36 (P36) | house-style: Keep a Changelog (GAP) | CONFIRMED | The `grep -ciE` gives 0. Entries are narrative (`Changelog.md:1-20`) | "CLAUDE.md asks the Changelog for provenance lines" is loose. `CLAUDE.md:252` is about generated artifacts in general |
| 37 (P37) | house-style: spelling and filler (GAP) | CONFIRMED | `CLAUDE.md:113,140,214,289`. `KNOWN-ISSUES.md:475` has "simply". `SETTLED.md:22,104` has "very" | At `SETTLED.md:104` it's "the very result", which is emphatic, not filler. "acknowledgement" is an accepted US variant |
| 38 (P38) | house-style: long table cells (GAP) | CONFIRMED | `awk -F'\|'` counting cells over 300 characters in `docs/SETTLED.md` gives 102 | |

Tally: 31 CONFIRMED, 2 of them on the local part only (27, 32); 2 OVERSTATED (2, 12); 2 WRONG
(28, 30); 3 UNVERIFIABLE-HERE (23, 24, 29). The GitHub halves of 22, 26, 27 and 32 are also
unverifiable here. All six "Upstream too" claims hold against upstream's `b40c1f0`: items 1, 2,
4, 5, 8 and 9 in this table.

## What the report missed, noticed in passing

- **The project already tracks item 2.** It's the 2026-10-26 review's item 3.2:
  `docs/KNOWN-ISSUES.md:290-318`, `docs/handshake/STATUS.md:31` ("us fixing at round 36"), lap 12
  S10 and `Changelog.md:66`. Items 3.1 and 3.3 of that review are tracked at
  `KNOWN-ISSUES.md:322` and `:245`. The audit should cite these and not present the defect as
  new. It should also correct "Platterpus's scheme": KNOWN-ISSUES says Platterpus's
  `{album} [FLAC]` can't traverse.
- **Item 6 (write failures) is lead "e" of the project's own 2026-09-05 audit**
  (`docs/AUDIT-2026-09-05.md:226`), still unfixed seven weeks later. Lead "j" there flagged
  plain `http://` too. The timeouts were fixed (`coverart.c:168-189`), but HTTP stayed.
- **Lap 12 S9 records a scope decision.** The new log escape leaves "the cue sheet and file
  names" as they came (`round-36-lap-12.md:96`). Item 5's fix should be weighed against that
  recorded scope.
- **The cover-art defect is a use-after-free followed by repeated frees, not one double
  free.** The `av_calloc(sizeof(AVCodecParameters))` and `memcpy` pattern also breaks
  FFmpeg's rule that `sizeof(AVCodecParameters)` is not public ABI. That's a further reason
  for `avcodec_parameters_alloc` and `avcodec_parameters_copy`.
- **Smaller C slips in `src/coverart.c`.** At `:264`, the `av_mallocz` result is unchecked
  before `memcpy`. At `:277`, `if (res < 0)` tests a `CURLcode`, which is never negative, so
  `crip_free_art` never runs on those error paths.
