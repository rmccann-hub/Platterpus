# Known issues for cyanrip — from Platterpus, outside the handshake

> ## ⚠ CLOSED, 2026-08-15 — do not read this as a live list
>
> **All ten findings are dispositioned.** The fork acted on the whole document:
> **§2 is STRUCK** (we reported a defect that had been fixed at `8499890` before
> we wrote it), and the other nine were real and are all fixed. Two of our
> proposed remedies — §4a and §5 — would not have worked, and the fork said which
> half of each it accepted.
>
> **Three of them are fixed *after* the round-8 pin, so they are still present in
> `ddf7ac3`:** §7, **§8** and §9. Their live home is
> `docs/handshake/verified/round-08-lap-10.md` §C and §O, which carries the
> disposition table and the round-9 asks. **§8 is also now detected on our side**
> (`platterpus.cue_validate`, finding `cue_index00_orphaned`).
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

**What this is.** A list of concrete, evidence-backed problems that Platterpus has hit, measured, or worked around, where the fix belongs on the cyanrip side (fork or upstream). It is offered as useful information, nothing more.

**What this is not.** This is **not a handshake lap.** It carries no wire header, declares no verdict, is not numbered as a lap, and must not be counted as one. It creates no obligation to respond, and no response from you closes or advances anything.

**Round 8 is untouched.** Round 8 is OPEN; our lap 8 is a **HOLD on pin `ddf7ac3`** with a pre-commit that our lap 10 is GO unless the named conditions fail. Nothing in this document moves, amends, adds to, or argues with any of that. Items already live in round 8 were excluded during preparation; where one is mentioned it is only to say that we are not double-counting it. Under S-14, every item below defaults to **NEXT-ROUND** and none of them is put forward as blocking anything: none makes the pin under review unsafe.

**Evidence rule we held ourselves to.** Every finding cites a path with a line number or a verbatim quote from a committed artifact in this repo. Anything we could not cite was dropped, and the drops are counted at the end. Where a change's origin was in doubt we wrote "unknown" rather than guess — this project has twice misattributed an upstream change to the fork, so origin claims below are proved from artifacts where they can be.

**One correction we volunteer up front.** Two independent verification passes over these candidates refuted 16 of the 26 they examined, and the dominant reason was *already fixed at `ddf7ac3`*. That is our defect, not yours, and §12 below says so plainly. Every item that survives has been re-checked against the newest artifact we hold, and each says which one.

---

## 1. No album-level loudness line is cyanrip's — the whole album block is libavfilter's wording, with no owned fallback

**Severity: medium (silent-emptying risk on an archival field). Origin: upstream, proven from artifacts.**

### What it is

The fork gave the *per-track* loudness rows owned, stable labels — `Sample peak level:`, `True peak level:`, `Integrated loudness (R128):`, `Loudness range (R128):`. The *album* block never got the same treatment. Only the two words `Album Loudness` are cyanrip's; the ` Summary:` tail and every value line under it (`I:`, `LRA:`, `Peak:`) are FFmpeg's `ebur128` filter output, which your own contract disclaims as wording that moves when FFmpeg does.

So the album-level integrated loudness, loudness range, sample peak and true peak in a cyanrip log are, in practice, an FFmpeg output format with no version signal attached — and there is nothing else in the log to fall back to.

### Evidence

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

### Why it is yours

Log text, which the ownership test names as yours outright. We tried three ways to fix it on our side and all three fail:

1. **Derive the album value from the owned per-track rows** — impossible for integrated loudness and LRA, which are gated whole-program EBU R128 measures and are not any function of per-track values. (Album *peak* would be derivable as the max of the per-track peaks, so that sub-part is partly ours; it does not carry I or LRA.)
2. **Read it from a cyanrip-owned ReplayGain tag line** — the log's Metadata blocks carry only `REPLAYGAIN_TRACK_GAIN`, `REPLAYGAIN_TRACK_PEAK`, `REPLAYGAIN_TRACK_RANGE`, `R128_TRACK_GAIN`, `REPLAYGAIN_REFERENCE_LOUDNESS`. Zero `REPLAYGAIN_ALBUM_*` / `R128_ALBUM_GAIN` rows.
3. **Loosen our regex** — we can be tolerant, but we cannot invent a stable label or a version signal for a third party's output format.

### Suggested fix

Print cyanrip-owned album rows with the same discipline as the per-track ones, in priority order:

- `Album integrated loudness (R128): …` and `Album loudness range (R128): …` — these are the irrecoverable ones.
- `Album true peak level: …` and `Album sample peak level: …` — second priority; if you decline these we can derive them from the per-track rows.

The `(R128)` qualifier is load-bearing for the same reason it was per-track in round 6 §C4: an unqualified `Album integrated loudness:` would collide with libavfilter's own unqualified heading in the same log.

### What it costs a consumer if unfixed

One FFmpeg release can empty the entire album-loudness block of every log, with no other symptom and no version signal to branch on. We consume these values into shipped artifacts — `src/platterpus/parsers/cyanrip_log.py:1812/1816/1829` populate `album_loudness`, `src/platterpus/rip_report.py:1122` writes it into the report JSON, `src/platterpus/ui/rip_progress.py:1287` renders it — so the failure mode is a silently blank archival field, not an error.

**Scope note so this is not mistaken for our pending work.** Migrating the *per-track* scrape onto your owned rows is ours to do (`TASKS.md:765`, task #80). The residual for you is strictly the **album** level, where there is no owned row to migrate to. `TASKS.md:765` already states the gap in your terms — "`I:` / `LRA:` have **no** stable provider source at all" — but that line has only ever lived in our task file and has never been sent to you.

Nothing here is wrong in the artifact under review today: at the current FFmpeg the values are correct.

---

## 2. `C2 errors:` prints a drive *capability*, never whether the rip *used* C2 — EAC's "Make use of C2 pointers" row stays unanswerable

**Severity: low (unobservable on our current drive). Origin: upstream. Standing round-1 §1.4 ask, still unacknowledged at `ddf7ac3`.**

### What it is

The line reports what the drive supports, not what the rip did. EAC's archival field asks whether C2 was *used*. `unsupported by drive` proves it was not used (the drive cannot), so that case is answerable; `supported by drive` says only that it was available, and no other line in the log answers the question. There is no wording that makes an affirmative honest.

### Evidence

Format string at the current pin, unchanged:

> `docs/handshake/inbound/artifacts/round-08-lap-01-provider-contract-gea2793a.md:269`
> ``| `cyanrip_log.c:592` | `C2 errors:      %s` |``

(The contract row shows `%s` alone; the `by drive` suffix is real — upstream's source is quoted at `docs/cyanrip-fork.md:263`: `cyanrip_log(..., "C2 errors:      %s by drive\n", (ctx->rcap & CDIO_DRIVE_CAP_READ_C2_ERRS) ? "supported" : "unsupported");`. That quote is also the origin proof: this is upstream's libcdio capability bit, not a fork addition.)

Real value on our rig:

> `output_reference/cyanrip_flac/cyanrip_flac_police_classics.log:8` — `C2 errors:      unsupported by drive`

Our parser, and the reason it has no affirmative branch:

> `src/platterpus/parsers/cyanrip_log.py:967-1001` — "cyanrip's format string is `C2 errors:      %s by drive`. So 'unsupported' proves C2 was not used (the drive cannot), while 'supported' says only that it was available — EAC's row asks whether C2 was *used*, which cyanrip never states. Claiming Yes from a capability line would be exactly the invented rip fact the export forbids"

Our half is done and pinned: `tests/test_eac_layout_parity.py:229-243` (`test_c2_capability_is_not_reported_as_c2_use`) asserts `supported by drive` → `None`. The mapping at `cyanrip_log.py:991-1000` already accepts a "not used" wording as a truthful `False`.

**Prior ask.** This is not new. `docs/handshake/outbound/round-1.md:117-131` is titled "1.4 `C2 errors:` — say what the rip *did* (§2.5)" and carries the identical two-line proposal and the identical "no affirmative branch, on purpose" argument. `round-1.md:266` asked which of §2.1/§2.3/§2.4/§2.5 you implemented, and no inbound file has answered §2.5. A grep for "not used" / "C2 pointer" across all of `docs/handshake/inbound/` returns zero hits.

### Why it is yours

Only the ripper knows whether its read path consumed C2 pointers. Our side is complete and test-pinned; what is left is a printf.

### Suggested fix

Append the use state: `supported by drive, not used` / `supported by drive, used`. Our parser already maps the "not used" wording to a truthful **No** and deliberately has no affirmative branch (libcdio-paranoia never consumes C2 pointers, so a "used" line would contradict the engine, and "not used" contains the substring "used" — a positive check would earn nothing but a way to fabricate EAC's "Yes"). The agreed wording is already specified on our side at `docs/dependency-contracts.md:209`.

### What it costs a consumer if unfixed

On a C2-capable drive, our EAC-layout export must print "(unknown)" in a row EAC always fills, and a logchecker deducts for it. The alternative — inferring Yes from capability — would be a fabricated rip fact.

**Honest severity note, in our own words.** `docs/cyanrip-upstream.md:736` ranks this 6 of 8 (Trivial / Upstream PR / Medium odds), and `:808` says the payoff "is unobservable on this rig — the BDR-209D reports C2 unsupported, so the row is already filled. Not worth buying hardware for. (Opportunistic.)" `:106` confirms the EAC row renders a truthful "No" today. Nothing in any artifact under review is wrong; the gap opens only on a C2-capable drive we do not have. Strictly opportunistic.

---

## 3. A zero AccurateRip checksum still prints as `match found, confidence N` — the void state has no distinct machine-readable form

**Severity: low (never observed in any artifact we hold). Origin: upstream, proven from an artifact.**

### What it is

When a track's computed AccurateRip checksum is `0`, the match line is still emitted with a real confidence number, and the fact that the comparison is void is carried as a sentence *inside* the same parenthetical. A consumer keying on the structured parts — a result field plus a confidence integer, the only format-agnostic way to read the line — sees a confidence-200 verification for audio that was never meaningfully compared.

### Evidence

The format string, present unchanged in every provider contract since round 4:

> `docs/handshake/inbound/artifacts/round-08-lap-01-provider-contract-gea2793a.md:245`
> ``| `cyanrip_log.c:446` | `(match found, confidence %i, but a checksum of 0 is meaningless)` |``

(Also `round-4.md:988` at `cyanrip_log.c:195`; `round-5.md:1311` at `:316`; `round-6.md:927` and `round-6b.md:736` at `:342`; round-07 laps 25/30/32/39 at `:446`.)

Our guard and the reason for it:

> `src/platterpus/parsers/rip_log.py:426-432` — "cyanrip itself prints the caveat — 'match found, confidence 200, but a checksum of 0 is meaningless' — and without this guard that line parsed as a confidence-200 positive. It matters most on the offset-variant row, where a silent or absent track yields `Accurip 450: 00000000` and the cell then announced a partially-accurate match for audio nothing was compared against. Keying on the zero CRC rather than on cyanrip's wording is the stronger invariant: it also covers a backend that omits the caveat"

**Origin proof (upstream).** `output_reference/cyanrip_flac/cyanrip_flac_police_classics.log:1` banner reads `cyanrip 0.9.3 (release)` — stock upstream — and `:169` of that same log emits `Accurip 450: BF62B1DA (matches Accurip DB, confidence 200, track is partially accurately ripped)`. The offset-450 block and its wording are upstream code, not a fork addition.

### Two corrections we owe you on this one

1. **The checksum-0 branch has never been observed in any artifact this repo holds.** Every real zero-CRC occurrence we have (`docs/handshake/inbound/round-5.md:922, :989, :1054`; `round-6.md:510, :582`; `round-6b.md:319, :391, :461`) is a **bare** `Accurip 450: 00000000` printed under `Accurip:       disabled`, with no parenthetical at all. The evidence here is your format string, not a captured line.
2. **cyanrip is not withholding anything.** The caveat sits inside the same field, and our own capture group takes the whole field (`docs/cyanrip-consumer-contract.md`, rules `track_accurip` / `track_accurip_offset` — `\((?P<result>[^)]*)\)`) with the `00000000` CRC on the same line. The ask is that the *machine-readable shape* agree with the prose, not that information is missing.

### Why it is yours

The checksum comparison and the verdict wording are cyanrip's, and the log is the record the user keeps. That the disclaimer exists at all proves cyanrip knows the match is void — it still emits it as a match.

### Suggested fix

When the computed checksum is 0, do not print a match: print a distinct non-match state (e.g. `no comparison possible (checksum 0)`) with no confidence figure, so the structured fields say what the prose says.

### What it costs a consumer if unfixed

We have no dependency left on you changing this — we deliberately keyed on the zero CRC rather than your wording, precisely so the guard survives a backend that omits the caveat. What remains is that the only thing separating a void comparison from a genuine one is a prose sentence in a free-text field: any consumer that substring-matches the result string (the fragile pattern the seam rules discourage), or any human skimming the log, reads a confidence-200 verification for silence. A log-shape improvement, not a correctness defect.

---

# The provider contract — three findings, one artifact

§4, §5 and §6 are three separate defects **in the same document and the same generator**, found independently by two different verification routes. We are listing them separately because they have different fixes and different failure modes, but they are one cluster and are probably one afternoon's work. Please read them together. All three are **fork-origin** in the sense that matters: `PROVIDER-CONTRACT.md` and `tools/gen-provider-contract.py` have no upstream counterpart, so whatever the origin of an individual log line, the contract's coverage of it is the fork's to fix.

---

## 4. The contract delivered with round 8 lap 1 was not generated by the build it names — and eight P2 "stable API" rows carry no matchable text

**Severity: high. Origin: fork (the artifact and its generator are fork-only).**

### What it is

Two defects in one artifact and one generator, both provable from the delivered files without access to your tree.

**(a) The file is a stale regeneration, and the lap says otherwise three times.** Round-08-lap-01 §A:43 and §I:212-213 state the contract was "generated by `ea2793a`" / "generated from a clean build of `ea2793a`", and that `tools/gen-provider-contract.py --check` exits 0. §C's commit table puts `1f00653` (the `Cache probe:` bound/reason rewrite, flagged `YES` for log text) *before* `ea2793a`, so any contract generated at `ea2793a` must contain the new wordings. The delivered file contains none of them: it still publishes the superseded `Cache probe:    %i sectors measured (...)` at line 150 and has 7 `Cache probe:` rows where §D1:124 says P2 lists 9. Its `Build:` banner says `0.9.4-rc1+platterpus.5` although §A:18 names `0.9.4-rc1+platterpus.6-beta.1` as the build to install. It is the `afa32e1` regeneration — one commit before the log change and two before the regeneration at `5967439` that §C says exists. The generator's `--check` evidently does not compare the contract's own `Build:` banner (or its content) against the binary that was built, so a stale file passes the gate that exists to catch stale files.

**(b) Eight rows of the declared API cannot be matched, diffed or regression-tested.** P2 opens (:131-135) with "Changing the text, indentation, field order or units of any of them is a breaking change and requires a handshake round." Eight of its rows are bare format specifiers with no literal: `cyanrip_log.c:61` `%s`, `:184` `%s%s`, `:188` `%lu`, `:579` `%s%c%i %s`, `:619` `%s%s%s%s%s`, `:637` `%i%s`, plus `:58` `%s%s:` and `:469` `%s:`. P2a (:413) is your own mechanism for this class — "the pieces are reconstructed here from the `snprintf` formats that build the buffer" — but it decomposes exactly two call sites, both in `cyanrip_main.c`, and none in `cyanrip_log.c`. The consequence is concrete for `cyanrip_log.c:173`, published as `Read stalls:    %s`: the four wordings that line can actually emit exist only as prose in round-07-lap-14.md:159-162, a round-7 lap file, and your own note there says they are `strcmp`-pinned in `tests/stall.c`. A consumer generating checks from the contract gets nothing; a consumer that read one round's prose has it. That is precisely the "a list either side maintains by hand" failure the generated contract was built to remove. And the generator can do better where it chooses to — the seven `cache_probe.c` rows at :144-150 are fully populated wordings from the same run.

### Evidence

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
> (next heading is `## P3` at `:445` — nothing else in P2a.)

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

### Why it is yours

`PROVIDER-CONTRACT.md` and `tools/gen-provider-contract.py` are fork-only. Platterpus cannot regenerate a contract from your build, cannot read your `snprintf` chains, and cannot make `--check` compare the banner against the binary. Origin proved by log diff rather than assumed: `grep -c -i cache output_reference/cyanrip_flac/cyanrip_flac_police_classics.log` = **0** (stock upstream `cyanrip 0.9.3 (release)`), while the fork log carries `Cache model:` at line 17 — the cache subsystem and its contract rows are fork code, not inherited upstream.

### Suggested fix

**(a) Make the artifact prove its own provenance, and make `--check` able to fail.**

1. Re-run `tools/gen-provider-contract.py` from a clean build of the commit the round-8 manifest actually names (`+platterpus.6-beta.4` / `g2ce8993` is what the rig is running), and resend it — or, if a corrected contract was already sent in laps 3–7, resend that.
2. Have `--check` compare the contract's own `Build:` banner against the version string of the binary it just built, and fail on mismatch. Today it evidently does not, which is how a file whose banner reads `+platterpus.5` shipped under a cover letter naming `+platterpus.6-beta.1`.
3. Add a content assertion so the check cannot pass for the wrong reason: every `cyanrip_log()` / `cyanrip_log_start_line()` format string reachable in the built source must appear verbatim in P2/P2a. That single rule would have caught this file.
4. Keep emitting the commit as `g<commit>` if you must elide it — that normalisation is deliberate and we are not asking you to change it (round-4.md:461-462, "A generated artifact cannot contain a value that generating it alters") — but pair it with a `Generated-from:` line naming the real SHA alongside the source anchor you added in round 6.

**(b) Extend P2a to the `cyanrip_log.c` composed rows.** For the `snprintf`-chain cases (`:58`, `:184`, `:188`, `:469`, `:579`, `:619`, `:637`) apply the reconstruction P2a already does for `cyanrip_main.c:870`. For `cyanrip_log.c:173` (`Read stalls:    %s`) the argument comes from a pure formatter whose four return shapes are already `strcmp`-pinned in `tests/stall.c` — emit those enumerated strings into P2a from the same source of truth the test reads, exactly as the seven populated `cache_probe.c` rows are emitted from `tests/cacheprobe.c`. Where a row genuinely cannot be decomposed, mark it the way `cyanrip_main.c:2056` already is ("Do not pattern-match this row") so "unmatchable" is a declared property rather than an omission a consumer has to discover.

### What it costs a consumer

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

## 5. The newest contract's P2 is missing a `Cache probe:` line the shipped binary prints — and `gen-provider-contract.py --check` exits 0 on it

**Severity: high. Origin: fork.**

### What it is

This is §4(a) approached from the other end, and it is worth stating separately because the *detection* story is the sharp end.

Round-8 lap-1 §D1 announces commit `1f00653` as replacing `Cache probe:    %i sectors measured (...)` with a bounded form, and says "The nine wordings it can now emit are pinned by `tests/cacheprobe.c` and listed in `PROVIDER-CONTRACT.md` P2." The contract attached to that same lap lists **seven** `Cache probe:` wordings, one of which is the exact pre-fix string, and none of which is the new shape. The rows are byte-identical to round-07-lap-39's, line numbers included.

Three things rule out an innocent reading. (1) The source anchor moved between the two contracts (`8290677bea1a834d` → `99769a09466b0b57`), so a different tree WAS scanned — `cache_probe.c` simply did not move in it, which it must have if `1f00653` were present. (2) The new wordings appear nowhere else in the document, so they did not migrate to another file. (3) The lap orders `1f00653` before `ea2793a`, and §A states the contract was generated by `ea2793a` — so the fix is inside the tree the contract claims to describe.

Either the generator ran against a stale checkout, or its P2 scan has a hole that silently kept a retired string and dropped a live one. From this side those are indistinguishable, which is itself the problem: `--check` exits 0, so the drift checker that exists to catch exactly this reported clean.

### Evidence

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

### Why it is yours

`tools/gen-provider-contract.py` runs in your repo against your tree and your binary. Nothing on our side can regenerate it or detect the omission except by hand-diffing two of your artifacts, which is how this surfaced.

### Suggested fix

Two parts, and the second is the one that matters.

1. Regenerate `PROVIDER-CONTRACT.md` from a tree that provably contains `1f00653` and re-ship it against the round-8 test pin, so P2 lists the nine `Cache probe:` wordings the binary actually emits. While there, take the Build line's version off the built binary's `--version` rather than a source constant.
2. Close the class, because a regeneration fixes one instance and leaves the mechanism. `--check` exited 0 on this document, which makes it a check that passes for the wrong reason — the failure mode both projects' rules name as worse than a check that fails. Two cheap floors:
   - Cross-assert the generator's P2 output against the strings `tests/cacheprobe.c` already pins. The test file is the independent witness; a contract whose P2 disagrees with it is stale by construction, and this specific defect would have been a build failure instead of a shipped artifact.
   - Give `--check` a staleness floor it cannot satisfy by finding nothing: recompute the source anchor at check time and refuse if it does not match the anchor written in the document, and refuse if the built binary's `--version` does not match the Build line.

Worth saying explicitly on the way past: **this is not an ask to fix the `Cache probe:` number.** That is already agreed as a round-10 method defect, and the current wording ("upper bound unknown, search ceiling reached") correctly names its own ignorance. This finding is only about the document not describing the binary.

### What it costs a consumer

Not blocking under S-14 — nothing here makes the reviewed pin unsafe, no audio or checksum is affected, and we do not currently parse the `Cache probe:` line for anything beyond echoing it verbatim (`src/platterpus/rig_check.py:380`, an INFO row).

What makes it worth carrying is what it says about the document rather than about the line. We treat the contract as ground truth in code: `tests/test_argv_surface_agreement.py` diffs every flag we send against the newest inbound contract; `uiscript/verbs.py` keys `FILE_ONLY_FLAGS` on the contract's section placement, which is what stopped a scripted `cyanrip -x` from becoming a full rip with MusicBrainz lookup enabled; `ripper_message_inventory.py` is ordered by it. A P2 table that can silently omit a shipped log line means the fatal-message inventory our error surfacing derives from is checked against a population we cannot trust — precisely the round-5 failure this project already paid for once, where a green test was measuring your generator's allowlist rather than the ripper, and two ordinary hardware failures rendered to the user as a bare "Rip failed."

It also lands squarely on round 6's own rule — a build tag names a commit, it does not name what was built — arriving this time in the very document that rule was written to protect.

---

## 6. P2 does not enumerate nine banner labels every rip emits — six of them lines Platterpus parses

**Severity: medium. Origin: the labels are largely upstream's; the omission is the fork's.**

### What it is

P2 declares itself the stable-line API and counts "268 distinct stable lines". But nine `Label:` rows that the banner of every real rip emits are not enumerated anywhere in the file: `Overread:`, `Overread mode:`, `Disc number:`, `Total discs:`, `DiscID:`, `Release ID:`, `CDDB ID:`, `Album:`, `Album artist:`. They are not in P2, not in P2a, and not in P3; the only rows in the whole document containing those strings are P5 fatal messages from `musicbrainz.c:317` and `discid.c:31`.

The omissions are contiguous with the enumeration's own gaps — P2 runs Offset(576)/(579) straight to Speed(588), Outputs(627) straight to Disc tracks(633), and 637 straight to AccurateRip(651) — so the generator's scan of the banner emitter is landing partway rather than deliberately excluding the block.

Six of the nine are lines our parser keys on today and declares in its own published consumer contract, so the two halves of the seam disagree about what is covered, and the side that would be broken by a reword is the side with no say in it.

### Evidence

The promise — `docs/handshake/inbound/artifacts/round-08-lap-01-provider-contract-gea2793a.md:131-135`:
> "## P2 - Outputs: stable log lines (the API)
> Every line below reaches **both stdout and the logfile**. Changing the text, indentation, field order or units of any of them is a breaking change and requires a handshake round."

`:414` "**268 distinct stable lines.**" Nothing in the file disclaims completeness for the banner block; the only stated carve-outs are P2a (two rows) and P3.

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

### Why it is yours

Only the provider can enumerate its binary's format strings. Platterpus could only stop parsing the lines, which is data loss, not a fix.

### Suggested fix

Extend `tools/gen-provider-contract.py` to reach the banner emitter (the `cyanrip_log.c` 537-657 region already contributes rows, so the sweep stops partway rather than skipping the block) and regenerate, so all nine labels get P2 rows with their literal text. Where a row's format string carries the label in a `%s` — `cyanrip_log.c:579` `%s%c%i %s`, which plausibly emits `Overread:`/`Underread:` — enumerate the label variants rather than leaving an opaque row (this is the same ask as §4b).

Then close it with a self-check rather than a promise: run a real rip, extract every `^[A-Z][^:]*: ` label from the resulting log, and fail the generator if any is absent from P2 — a floor the contract cannot silently decay past.

**Our companion obligation, not part of the ask:** `tests/test_provider_contract_agreement.py:80` checks only that we parse nothing on your P3, never the converse, and its docstring at `:15-16` claims "When a new round lands with a new provider contract, this test re-derives from it" while `:28` still hardcodes `_ROUND_4 = … "round-4.md"`. That is ours, and it is why this gap went unseen here.

### What it costs a consumer

Six log lines Platterpus parses on every rip sit outside your own breaking-change rule, so they can be reworded in any build without opening a round — and nothing on either side would notice until a rip came back wrong. Our parsers never raise, so the failure is silent field loss, not a crash: `overread_mode` is the sole discriminator for the EAC-parity "Overread into Lead-In and Lead-Out" Yes/No row (the frame count is identical in both modes), so that row would flip to unknown; `album`/`album_artist` feed the EAC log's Artist/Album header; `disc_id`/`cddb_id` are the TOC-derived keys the re-rip comparison uses to prove two rips are of the same physical disc; `release_id` is the only witness that our colon-delimited `-a` tag blob parsed into the right fields.

This is the `-V` blocker's exact shape — a surface we depend on that the contract did not cover — arriving from the log side instead of the argv side, and it has been present in all five published provider contracts.

---

## 7. The `-j` diagnostics record declares `messages_are_complete: true` while dropping every ebur128 loudness block

**Severity: medium. Origin: fork (`-j` is fork-only).**

### What it is

The fork-only `-j` / `--diagnostics` JSON asserts that its `messages[]` capture is complete when it is not. In both full-rip `-j` artifacts either side holds, exactly **55** non-blank lines present in the logfile of the same rip are absent from `messages[]`, while the record states `messages_dropped: 0`, `messages_are_complete: true`, `messages_tail: []`.

Of the 55, **52 are content**: four complete ebur128 blocks (three per-track plus the album one), each being the `Summary:` header and its `Integrated loudness` / `Loudness range` / `Sample peak` / `True peak` sub-blocks. The remaining 3 are structural log-only lines (the two `--- output before this log was opened ---` / `--- end of pre-log output ---` markers and the trailing `Log FUN512:` self-hash, which is inherently uncapturable since it hashes the finished log). We state 52/55 rather than repeating a raw 55, because overstating it by three would be exactly the unqualified remembered measurement this hand-off is trying not to produce.

The mechanism is provable from your own generated contract rather than guessed. The capture hook wraps `cyanrip_log()` only — the record says so itself in `messages_note`. The contract lists `cyanrip_encode.c:820` as emitting the format string `Album Loudness` with no `Summary:`; libav's ebur128 filter appends `Summary:` and the block via `av_log`. So the JSON captures the truncated stub `"Album Loudness "` while the logfile carries `Album Loudness Summary:` followed by 12 more lines. The capture sees cyanrip's half of the line and not libav's, and then declares itself complete.

This is not a transient: it reproduces identically (55 missing, same three assertions) across two independent fork builds, g400155b (lap 32) and g422d12a (lap 39).

### Evidence

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

### Why it is yours

The record is written by cyanrip; `-j` is a fork-only flag (first appearing in the round-7 provider contracts at `:42`, with no round-4/5/6 antecedent). Platterpus cannot make a producer's capture hook see output it never saw, and cannot correct an assertion inside a file it does not write. Our only `-j` call site is a consumer (`src/platterpus/rig_check.py:187`).

Note the layer separation, because misattributing upstream to fork is a repeat failure here: the ebur128 block *itself* is upstream-inherited (present in `output_reference/cyanrip_flac`). The defect is not the block — it is the `-j` record's false completeness assertion, and that record does not exist upstream.

**Not already asked.** `messages_are_complete` appears in prose in exactly two places, both round 7: `inbound/round-07-lap-12.md:70` where you announce the field ("You asked us to state the property"), and `verified/round-07-lap-13.md:188` where we praise it. In neither did anyone check the field against the log. Asking for a field is not reporting that the field lies.

### Suggested fix

Either half of the seam's own honesty rule satisfies this; you pick.

**(a) Widen the capture.** Hook `av_log` in addition to `cyanrip_log()` so `messages[]` matches the logfile's non-blank lines. Commit `1fe78f4` shows a libav-message path already exists, so the plumbing may be closer than it looks — but note the ebur128 wording is libavfilter's and moves when FFmpeg does, which your contract flags at `:482-484`.

**(b) Keep the current scope and stop asserting a property the record does not have.** Set `messages_are_complete: false` (or make it scope-qualified), count the uncaptured lines into `messages_dropped`, and add an explicit scope field naming what is captured — e.g. `messages_scope: "cyanrip_log() only; libav/ebur128 filter output is not captured"`. The existing `messages_note` is the natural home for the prose half.

Whichever is chosen, document the scope in the provider contract. Today the contract's `-j` coverage is a single row in the P1 flag table (`:42`) plus the P4 note (`:502-506`); it never describes the record's schema or its capture scope, so a consumer has nothing to check the assertion against.

### What it costs a consumer

This is the diagnostic-completeness rule inverted: a silent truncation that reads as completeness. The `-j` record is your machine-readable capture artifact, and it is the *only* artifact for the one class of run that opens no logfile at all. A consumer that trusts `messages_are_complete: true` as the authority on what cyanrip said will silently lose 52 lines and never learn they were dropped. The fields were added at your round-7 lap 12 explicitly at our request, so the field asserts a property the record does not have — which is worse than never having stated it.

Blast radius today is limited and we should say so honestly: Platterpus passes `-j` at exactly one call site, a refused run with no loudness block, so the gap does not currently bite us. This is a correctness-of-the-record defect, not an audio or checksum defect.

---

## 8. Partial rip (`-l`): a track's `INDEX 00` is computed against a FILE that was never written, and lands 682 frames past the end of the one it is printed under

**Severity: medium. Origin: upstream, proven from source.**

### What it is

`cyanrip_cue_track()` decides to write an appended-pre-gap `INDEX 00` from `crip_track_has_appended_pregap(...)`, whose only structural input is `has_prev_track` = `!!t->pt` — the previous track *on the disc*, with no notion of whether that track is in the `-l` rip set. It then computes the marker as `t->pregap_lsn - t->pt->start_lsn_sig`, i.e. an offset into the predecessor's FILE, and prints it into whatever FILE block is currently open — which, on a partial rip, is the last track that was actually written.

Measured on `-l 1,3,5,6,7`: track 5's marker is emitted inside `FILE "03 - Message in a Bottle.flac"` with the value `05:00:35` (22535 frames), while that file is only 21853 frames long. 22535 = 72455 (track 5 pregap LSN) − 49920 (track 4 start LSN) — arithmetically an offset into track 4's file, which was never written.

The proof that this is the mechanism and not a coincidence: the full-rip reference cue of the same disc carries the byte-identical value `INDEX 00 05:00:35` nested under `FILE "04 - Walking on the Moon.flac"`, where it is correct (track 4's file is 22650 frames because the 115-frame pre-gap is appended to it). Same number, different containing FILE.

Only track 5 is affected in this rip, and that is the mechanism working as described: track 7's `INDEX 00 04:05:53` (18428 frames) sits under `FILE "06 - …"`, whose length is 18533 frames, because track 6 *was* in the rip set. The condition is precisely "the immediate predecessor is excluded by `-l`".

### Evidence

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

### Why it is yours

cyanrip writes the cue; Platterpus only reads it. Nothing under `src/platterpus/` writes or edits a cue — a grep for cue writes returns only readers (`cue_validate.py`, `ctdb/toc.py`, `rip_progress.py`).

### Suggested fix

In `cyanrip_cue_track()`, an appended pre-gap can only be written when the previous track's FILE was actually written. Extend `crip_track_has_appended_pregap()` (`src/cue_writer.h`) with a "previous track is in the rip set" input — the `-l` selection is already known at cue-write time — and drop the `TRACK`/`TITLE`/`PERFORMER`/`ISRC`/`INDEX 00` block when it is false, emitting the track normally under its own FILE instead. That is the semantically right answer: the rig log shows track 5 is 18072 frames in both the full and the partial rip, so the 115 pre-gap frames are in no file at all and there is nothing for a marker to point at.

Independently of that, add the cheap invariant at the print site: an `INDEX 00` is an offset into the currently open FILE, so `pregap_lsn - pt->start_lsn_sig` must be < the frame count of the FILE the marker is nested under. Refuse (and log) rather than emit a marker past EOF — this catches the whole class, including the already-fixed one-frame variant.

Ask back: a regression test over a `-l` selection that skips a track with a signalled pre-gap on the following track (`tests/cuegap.c` already exists for this predicate and is the natural home).

**Companion item that is OURS, filed here only so you know it is covered:** `src/platterpus/cue_validate.py:655-666` deliberately `continue`s on exactly this case — "On a selection of tracks 3 and 5, track 5's gap has nowhere to go (track 4 was not ripped), and its absent marker is correct rather than a defect" — i.e. our validator assumed cyanrip would *omit* the marker, so the one check that reads the cue skips precisely where the defect occurs. It should assert the marker is absent or in range, not skip. That is ours to fix.

### What it costs a consumer

A shipped, routinely-reachable user path corrupts an archival artifact. `-l` is driven by the per-track "Rip?" checkboxes in the GUI, so any partial rip where the user deselects a track whose successor has a signalled pre-gap emits a cue with a marker pointing past the end of the file it names. Audio is unaffected; the cue is the artifact a burner, tagger or tracker uses to reconstruct the disc, and a strict consumer reading `INDEX 00` beyond EOF either errors or mis-seeks. It also silently asserts that pre-gap audio is present in a file when the rip contains it nowhere.

Blast radius is bounded — it needs a partial rip *and* an excluded track immediately preceding one with a sub-channel/TOC pre-gap — which is why this is medium and why under S-14 it is NEXT-ROUND: it does not affect the full-disc rip that round 8's acceptance criteria are measured on.

Two things make it worth sending anyway. First, it is upstream-origin, so it also affects stock cyanrip users and is a genuine upstream PR candidate — and "roll back to upstream" is not a mitigation for it. Second, it is currently undetectable on our side, per the companion item above: no Platterpus check, log line or report field would ever surface it to a user.

---

## 9. `-t` and `-p` disagree on out-of-range policy: `-t 99=` kills the whole rip, `-p 99=drop` is accepted and silently never applied

**Severity: medium. Origin: upstream, proven from source in both trees.**

### What it is

Both flags take a track index and resolve it against the same disc, and they treat an out-of-range one in opposite ways — one fatally, one silently.

`-t`: an index not present on the disc is fatal to the entire invocation. `cyanrip_main.c:2000-2009` scans `ctx->tracks[]` for a matching `number` and, on no match, logs `Invalid track number %i, list has %i tracks!`, increments `total_error_count` and `goto end`. Nothing is ripped. A *tag* for a track that does not exist destroys the rip.

`-p`: the index IS validated, but never against the disc. `cyanrip_main.c:1648-1675` bounds it `idx < 1 || idx > 197` — a fixed cap, not a disc-relative one — then writes `settings.pregap_action[idx - 1] = act`. So `-p 99=drop` on a 2-track disc is accepted, exits 0, and the directive is stored into a slot no track will ever read. No message, no exit code, no effect.

The asymmetry has a structural cause worth stating, because it constrains the fix: `-p` is parsed in the pre-disc option block, before the TOC is read, so `ctx->nb_tracks` is not yet known at line 1656. `-t` is validated at line 2004, after `ctx->tracks[]` exists. Bounding `-p` correctly therefore means deferring or repeating its index check after the TOC read, not tightening the existing one.

**Third element, from the same rows.** `-p 99=drop` is a literal counterexample to the generated argv table's own headline. It was accepted, took no effect, and was graded `accepted` purely because the probe has no observation channel — its result cell reads `(no header field exposes this)`, as do 48 other rows. `**Silently-ignored values: none.**` is therefore a claim the probe as built cannot make; it is a check that can only pass by finding nothing. Our own round-8 lap 8 cites that headline back at you as reassurance, so the claim is already load-bearing across the seam.

### Evidence

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

### Why it is yours

Platterpus already does everything a consumer can. We pre-filter `-t` at the argv chokepoint:
> `src/platterpus/adapters/cyanrip_backend.py:830-844` — "# Dropping the surplus costs a few tags on tracks that do not exist; passing it costs the entire rip." … `if (disc_track_total and isinstance(track.number, int) and track.number > disc_track_total): log.warning("dropping metadata for track %s: the disc has only %d track(s), and cyanrip rejects the whole rip on an out-of-range -t", …); continue`

And we do not emit `-p` at all, so no Platterpus change can make an out-of-range `-p` take effect.

### Suggested fix

Pick one policy for a track index the disc does not have, apply it to both flags, and say which in the contract.

1. **`-p` — bound it against the disc, not against 197.** The check at `cyanrip_main.c:1656` runs before the TOC is read, so the fix is a second pass after the TOC read (beside the `-t` validation at 2004) that rejects — or, under policy 2, warns-and-drops — any `pregap_action` slot beyond the disc's real track count. Reuse the `-t` message shape so one consumer matcher covers both.
2. **`-t` — decide whether an out-of-range index should keep aborting.** If it should not: at `:2004-2008`, drop that one `-t` pair with a warning and continue, keeping the fatal path for structurally malformed input (the `-t 1` missing-`=` case, which our lap 8 §B3 agrees should stay refused). If it must stay fatal, say so as deliberate policy in the provider contract so consumers know the bound is theirs to enforce — and note the same fatal path is duplicated at `:2070` and at `:2227` (`Invalid rip index %i, list has %i tracks!`); whatever is decided should be decided for all three.
3. **The probe's grading vocabulary.** Split the outcome into four states — `refused` / `took effect (observed)` / `accepted, effect not observable` / `ignored` — and stop printing `Silently-ignored values: none` while any row is in the third. The `-j` machine-readable diagnostics record already exists and is the obvious observation channel: echo the effective `pregap_action[]`, `-t` tag set and other applied settings into it, and the probe can compare intent against effect instead of against exit status.

**Order matters: fix 3 first.** Without an observation channel the probe cannot prove either of the first two fixes landed, and a revert of fix 1 would still read as `accepted`, exit 0, `0 silently ignored`.

### What it costs a consumer

The `-t` half has measured, real-world cost: a 16-track disc plus an 18-track MusicBrainz medium ended a rig rip in two seconds with nothing written (rig, 2026-08-02). Platterpus is protected today, but by a bound reimplemented in one consumer — every other cyanrip caller has to discover the same lesson the same way, and the guard is one refactor away from being the thing that regresses.

The `-p` half is the more dangerous shape even though it is currently unreachable from us: a pregap directive that is accepted, exits 0, and takes no effect puts wrong track boundaries and a wrong `.cue` into an archival record with a clean-looking log — the failure class the seam rules call worse than a refusal, because a refusal gets investigated and a success gets filed. It becomes live for us the moment gap-mode handling is driven through `-p`.

Both are inherited from upstream, which means the usual mitigation does not exist: rolling back to stock cyanrip restores the identical code. This is the third instance of that pattern after the `-V` removal and the `MM:SS.FF` duration-shape change.

The third element is the one that generalises: `Silently-ignored values: none` is a headline the probe as built cannot support, 49 rows are blind, and our own lap 8 already quotes it back across the seam as evidence.

---

## 10. `Extraction speed:` / `Elapsed:` are the only fork-only per-track measurements the contract's "units that are not obvious" block does not define

**Severity: low. Origin: fork, proven by diffing the two reference logs.**

### What it is

The provider contract has a block that exists precisely to define quantities a consumer cannot infer from the line itself — "**Units that are not obvious from the line itself:**" (`:102`). It defines `Total time:`/`duration:` (MM:SS.FF frames), `Pregap length:` (frames), `Sample peak level:`/`True peak level:` (% FS and dBFS), the paranoia counters as raw callback counts, the A8 per-track-vs-disc scope rule, and the Q10 `-l` denominator. `Extraction speed:` and `Elapsed:` appear nowhere in it — they exist in the contract only as bare format strings in the stable-line table at `:231-232`.

Both are fork-only lines (stock 0.9.3 emits neither), so there is no upstream documentation to fall back on, and the interval is not derivable from the number: track 1 of the round-8 rig rip shows `Duration: 03:13.12` (193.16 s) against `Elapsed: 214.29 s`, giving exactly the printed `0.9x`, which is self-consistent whether the elapsed brackets read only, read plus encode, plus the AccurateRip query, or plus `-Z` re-reads.

**This is not an accuracy complaint.** The number is internally consistent and the rig's `Paranoia level: max` / `Frame retries: 5` / `Speed: default (unchangeable)` fully accounts for a near-1x read. It is a comparability problem: Platterpus renders your speed value verbatim into the `     Extraction speed N.N X` row of its EAC-compatible archival log, directly opposite EAC's own row for the same disc and drive, which on this Pioneer BDR-209D reads 1.6 X to 3.5 X. A reader placing the two logs side by side is comparing two rows with the same label and two intervals, only one of which is defined.

### Evidence

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

### Why it is yours

Only the ripper knows which clock stamps bracket which stage. Our own code states the refusal to infer (`eac_log_export.py:1254-1260`, `rip_report.py:1355-1358`), but that refusal does not reach the speed row, because that value is yours.

### Suggested fix

Add one bullet to the existing "**Units that are not obvious from the line itself:**" block (after `:124`, beside the `Pregap length:` and peak-level entries), naming the interval explicitly:

- `Elapsed:` is wall-clock seconds between \<the two stamps\>, and covers \<read | read + encode | + the AccurateRip query | + every `-Z` pass or only the final one\>. `Extraction speed:` is `audio duration / Elapsed` over that same interval — state it, so a consumer knows it is not a drive-speed multiple.

The four sub-questions worth answering by name, because each changes whether the number is comparable to EAC's row: (1) does the interval start before or after the drive seek/spin-up? (2) does it include the FLAC/encoder time? (3) does it include the AccurateRip lookup? (4) under `-Z N`, is it the final pass only (matching the A8 per-track paranoia scope) or every pass?

If — and only if — the interval turns out to include anything beyond the read, a second, read-only figure would let the EAC row be filled with a genuinely comparable multiple; that is a NEXT-ROUND nice-to-have, not part of this ask. The contract sentence is the whole fix.

### What it costs a consumer

Record-only; no audio, checksum, pregap or verdict consequence. The number reaches the EAC-compatible archival log filling the row EAC labels `Extraction speed`, where a reader comparing our log to a real EAC log for the same disc and drive sees 0.9–1.1 X against 1.6–3.5 X. Whether that difference is a real read-rate difference or an artefact of a wider interval is currently unanswerable from either side's published documents, which makes the comparison unsound in both directions — it could equally hide a genuine performance fact as invent one. Cost to fix is one sentence in a block you already maintain; cost of leaving it is a permanently ambiguous cell in an archival record whose entire purpose is to be trusted decades later without the ripper present.

---

# 10b. An ask, not a finding: make your builds listable

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

# 11. What we checked and dropped

Saying what we discarded is part of an honest hand-off. Several of these are things you have already fixed, and we would rather show you we checked than hand you work you have done — and knowing which of your fixes we *wrongly believed were still open* tells you which ones never reached your consumer's documentation.

**The numbers.** 87 raw candidates were gathered from 7 evidence sources. Two verification passes examined **26** of them individually. **10 survived** (the ten above). **16 were refuted or excluded.** The remaining **61 were never individually verified and are not in this document** — see §13.

## Pass 1 — 14 examined, 3 survived, 11 dropped

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

## Pass 2 — 12 examined, 7 survived, 5 dropped

Two were refuted on evidence:

12. **`Cache model:` has no branch consuming an `-x` result** — refuted on two independent grounds. The evidence does not show the claimed contradiction: both cited rip logs ran *without* `-x` (verified by tokenising the argv line of each). And the probe method is already a known-untrustworthy one you deferred to round 10.
13. **Exit code 1 for every failure class (S-12 `generic`)** — refuted. It is already your own standing defect row, one cited line range was wrong, and the cited release-blocker mechanism does not exist in our probe; Platterpus fixed the entire cited harm on its own side.

Three were real but are **already live in the correspondence**, so we excluded them rather than double-count. They are listed because "we dropped it" should not read as "we decided it was wrong":

14. **`Accurip 450:` returns an identical checksum across three reads of one track that produced three different EAC CRC32s** — survives every check and is arguably stronger than filed, but it is already round-07-lap-27 §E with its own verdict-table row and question L1. Yours, still open there.
15. **The disc-image silence defect is live in upstream master and was never reported upstream** — survives every check, decisively evidenced from outside our own docs. You agreed twice in round 7 to file it; no upstream issue exists. Left with round 7 rather than re-raised here.
16. **P1 still lacks the promised note that a cancelled rip leaves 0-byte FLACs for tracks the log calls successful** — survives every gate; our half (stat every file the log claims, refuse to call a 0-byte FLAC verified) is already implemented. Already asked; not re-raised.

---

# 12. The staleness is our defect, and we are fixing it

The single largest finding of this exercise is not in the list above. It is that **our own documentation describes a cyanrip that no longer exists.**

Of the 16 candidates we examined and dropped, the dominant cause was *already fixed at `ddf7ac3`* — the cache probe, the `Done;` verdict line, the pregap LSN row, ISRC in the appended-pregap cue branch, log/cue line buffering, the `\:` escape, the `Total time:` unit, the `Peak level:` rename, the partially-accurate denominator. Nine of your shipped fixes were still being described as open problems in our source comments, our ask list (`docs/cyanrip-upstream.md`), and our parity documents. In two cases (`docs/eac-parity.md:141`, `docs/dependency-contracts.md:327-331`) our documents promise users a preservation behaviour that we had not re-checked against your current defaults.

That is a real cost to you: a consumer whose documentation lags by four rounds sends you work you have already done, and reasons about your behaviour from a snapshot. It is also a cost to us, because it is exactly the failure our own rules name — a map that is only ever wrong by omission, and nobody reviews a file for what is not in it.

Three things we are doing about it, none of which needs anything from you:

1. **Re-derive rather than re-read.** `docs/cyanrip-consumer-contract.md` is generated from our parser; the *complementary* check — every rule we declare must appear in your current P2 — does not exist, and `tests/test_provider_contract_agreement.py` still hardcodes `round-4.md` while its docstring claims it re-derives from the newest contract. Fixing that converse assertion is what would have caught §6 in-house, and it would have caught most of the nine stale beliefs above automatically.
2. **Sweep the ask list against the current contract.** `docs/cyanrip-upstream.md` is a ranked list of things we want from cyanrip; several entries are already delivered. It gets re-derived, not re-read.
3. **Treat a present-tense comment about a dependency defect as a claim with an expiry date.** Where our source comments and this document disagree, **this document is the current position.**

The one thing worth asking of you, and it is §4 and §5 rather than a new item: the reason we could not fully trust our own staleness check is that the contract we checked against did not describe the build it named. That is the cheapest single fix on this whole list, and it makes every future check of this kind sound.

---

# 13. Coverage limits, plainly

- **87** raw candidates were gathered from 7 evidence sources (source comments, our task file, the ask list, the parity documents, the consumer contract, the committed handshake correspondence, and the 2026-08-13 rig artifacts).
- **26** were examined individually and adversarially. **10 survived** and are above. **16** were refuted or excluded, and all 16 are named in §11 — none was dropped silently.
- **61 were never individually verified and are NOT in this document.** They are not a queue of known issues; they are unexamined candidates, and on the measured base rate roughly two-thirds of them would be refuted. We are not sending you a list whose hit rate we know to be poor.
- **An earlier draft carried five additional "unverified candidates"** — `-S` fatal on a speed-locked drive, `REPLAYGAIN_TRACK_PEAK` written from the true peak, the `-j` record's missing schema, de-emphasis defaults and checksum ordering, and the `.cue`'s unpublished contract half including the `REM MEDIA_TYPE` → `REM MEDIA` rename. They are **not included here**, because they had not been through refutation and this exercise has just demonstrated what that is worth. Several look strong. If you want them as questions rather than findings, say so and we will verify them properly first.
- **Freshness bound.** The newest provider contract we hold is `gea2793a` (round 8 lap 1). The newest binary we have observed is `platterpus-fork-g2ce8993` (`+platterpus.6-beta.4`, rig, 2026-08-13). We do not hold round 8 laps 3–7 (our lap 8 §F2 asks for them). Any finding above could have been fixed in a lap we do not have; each says which artifact it was last checked against so you can dismiss it in one line if so.
- **One finding carries an explicit last-mile inference** rather than direct proof at the current pin: §7's claim that the ebur128 lines are *still* uncaptured rests on the schema, note and field set being byte-identical at the newer build plus no commit touching capture scope, because the only `-j` record we hold from that build is a refused argv probe with no loudness block. You can settle it in one command.
- **Nothing here is offered as blocking.** Under S-14 every item defaults to NEXT-ROUND, and none of them makes `ddf7ac3` unsafe. Round 8 stands exactly where our lap 8 left it.

---

*Last updated for Platterpus v0.6.23.*
