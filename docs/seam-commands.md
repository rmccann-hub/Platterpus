# Seam commands — THE table

**One file. This is its only purpose.** Every command, flag, argument, type,
range and meaning that crosses the Platterpus↔cyanrip seam, in one place, at the
same path in both repos.

**Exchanged every handshake round, in both directions, with any updates.** Not
"published by each side and diffed" — *one artifact both sides carry, and both
sides update*. A round that changes nothing here says so explicitly; a round that
changes something ships the new version both ways. Either way it moves, so
"nobody sent it" is never confusable with "nothing changed".

**Both sides can call and test every variable in it.** That is the acceptance
test for this file: if a row exists, each side can exercise that flag with that
argument type and check the result. A row nobody can test is a row that is
documentation rather than contract.

## What every row must carry (seam-rules S-8 / S-9)

Beyond the status columns below, each row is only complete when it states — **for
every argument, whether or not either side uses it**:

| column | established how |
|---|---|
| **type** | the declared type |
| **valid range** | the **real accepted** min and max, by running the binary. The type is not the range: `int` says nothing about whether `-1` is taken |
| **boundary** | behaviour at min, at max, and **one past each**. Off-by-one at a boundary is the commonest argument defect and is invisible in a type |
| **on a bad value** | exit code, message, and **whether the operation dies or the flag is ignored** — the difference between a bad tag and a lost rip. `-t 17=` on a 16-track disc killed a rip in two seconds and the *type* was fine |
| **interactions** | mutual exclusions, ordering, silent overrides |
| **zero / empty / absent** | `0` usually means "auto", never stated in a signature |

**Each side probes its own binary. Neither probes the other's.** A limit we
derived from reading their docs is a claim about behaviour we never measured.

Where a limit cannot be probed without specific hardware or a specific disc, the
cell reads **`not-probed: <reason>`** — a recorded finding. **A blank reads as
"tested and fine"**, which is the failure this file exists to prevent.

**Nothing is out of scope for being unused.** *We may have to use or fix it in
the future*, and at that moment an undocumented argument is something a person
rediscovers under time pressure. The tables below are therefore incomplete by
construction today: they cover the 17 flags we send, not the 41 their tool has.
**That gap is the work, not an oversight** — every remaining flag needs a row
with `NO: <reason>` or `?`.

## How to read the two status columns

Every row carries a status from **each** side, because the interesting
information is where they disagree:

| status | means |
|---|---|
| **HAVE** | I send / accept this today |
| **EXPECT** | I rely on this behaviour; if it changes I break |
| **NEED** | blocking — without it I cannot ship what depends on it |
| **WANT** | non-blocking ask |
| **NO** | deliberately not used, with a reason |
| **?** | not yet stated by that side — **an open row, not a passing one** |

`-V` is why the two columns exist. Their table said `-v`/`--version` with **no
`-V`** for a full round, while every version probe we shipped sent `-V`. A
rejected flag exits non-zero, and every probe here reads non-zero as *"the tool
is not installed"* — so the app would have reported the ripper missing
immediately after the wizard built it. One side's correct document did not stop
the other side's wrong code, because nothing put them in the same row.

> **Provenance warning, now partly discharged.** §1's *type* and *range* columns
> are still **hand-transcribed from the argv builder**, and a hand-maintained
> description of behaviour goes stale invisibly — so treat §1 as a draft for
> review. **§1a is different: it is measured and generated**, by
> `scripts/probe_argv_surface.py`, and it is a CI gate rather than a document
> (`tests/test_cyanrip_backend.py::test_the_self_probe_reports_no_silently_dropped_values`).
> Where §1 and §1a disagree, **§1a wins** — it ran.
>
> The remaining work is the same in kind: extend
> `scripts/emit_dependency_contract.py` so §1's columns come out of the builder's
> own signatures too, and widen §1a's grid past the four numeric flags to the
> string and path arguments.
>
> **The cyanrip column is `?` throughout below** — not because we assume nothing,
> but because we have not asked yet. Their half arrives in the round-8 return
> file.

---

## 1. Rip-path flags

Seventeen flags reach the argv builder (`adapters/cyanrip_backend.py`). The
generated contract's §3 lists eighteen because the **version probe** contributes
its own, which is a different call path and is tabled separately in §2.

| flag | argument | type | range / shape enforced | meaning | **PP** | **CR** |
|---|---|---|---|---|---|---|
| `-N` | — | flag | **always present, unconditionally** | disable cyanrip's own MusicBrainz lookup. Critical rule #5; its interactive prompt would hang a GUI rip with no terminal | HAVE |  HAVE |
| `-d` | device | `str`, absolute path | must exist, must be a block device | the drive | HAVE |  HAVE |
| `-o` | format | `str` enum | **always `flac`** | archival master; every other format is transcoded host-side, so the ripper is never asked for a lossy encode | HAVE |  HAVE |
| `-D` | directory | `str`, path | writable | output directory | HAVE |  HAVE |
| `-a` | tag blob | `str`, colon-delimited, **backslash-escaped** | no newline, no NUL, bounded. Every `:` `=` `\` `'` in a *value* is escaped; the blob's structure (one `key=value` per unescaped `:`, exactly one unescaped `=` per field, no dangling escape) is refused at our argv chokepoint. Measured: an **unescaped** `:` does not fail, it silently truncates the value | the whole tag set as one argument | HAVE — escape shipped lap 31 |  HAVE — **and there IS an escape: `\\:`. See §7.** |
| `-t` | track list | `str`, `n=<escaped blob>` | **range-checked against the disc's real track count**, and the leading `<number>=` is required. Your reading was right and understated: it did not only read past the string, it **published** what it read as track metadata. **Refused since `3923dee`** — `Missing "=" in track metadata "%s"`, exit 1 | which tracks to rip. A `-t 17=` on a 16-track disc killed a rip in two seconds | HAVE — same escape, same chokepoint |  HAVE — fixed `3923dee`, measured in §7, regression test in `sc_cli` |
| `-c` | disc position | `int/int` | both ints, `number <= total`, else the flag is dropped | `DISCNUMBER` / `TOTALDISCS` | HAVE |  HAVE |
| `-s` | offset | `int`, samples | drive-plausible range | read offset correction | HAVE |  HAVE — **now bounded ±1048576**, §7 |
| `-S` | speed | `int` multiplier | bounded; `0` = drive max | read speed, fixed mode only | HAVE |  HAVE |
| `-r` | retries | `int` | bounded | per-track retry count | HAVE |  HAVE |
| `-Z` | matches | `int` | `0` disables | secure re-read consensus — the Test & Copy equivalent. **Measured with `-Z 2`**: track 5 converged after 3 reads, and the per-track paranoia counters then report the *last* pass while the disc totals report *every* pass (§3) | HAVE |  HAVE |
| `-l` | track number(s) | `int` list | must name tracks that exist on the disc | rip only these tracks. **Also how the auto-fix re-rip runs** — a second invocation with `-l <n>`, which is the structural signal that a pass is a subset rather than the whole album (it is what our progress model now keys on) | HAVE |  HAVE |
| `-G` | — | flag | conditional | disable cover-art embedding; we embed host-side | HAVE |  HAVE |
| `-O` | — | flag | **opt-in only** | overread into lead-in/lead-out. Their own help says it *"may freeze if unsupported by drive"*, so it is never on by default | HAVE |  HAVE |
| `-F` | — | flag | conditional | — *(transcribed from the builder; semantics need confirming, see §5)* | HAVE |  HAVE — track naming scheme, §7 |
| `-I` | — | flag | **never with `-J`** | — *(mutual exclusion recorded in `dependency-contracts.md`; we should state why)* | HAVE |  HAVE — refuses with `-J`, §7 |
| `--consumer` | tag | `str`, `<name>/<version>` | no whitespace, contains `/` | who we tell them we are. Validated because it is written verbatim into an archival log as the identity of the producing program | HAVE |  HAVE |

## 2. Probe-path flags, which is a separate call and a separate risk

| flag | why it is separate | the lesson attached to it |
|---|---|---|
| `--version` | a probe, not a rip. Does not pass the rip chokepoint | **this is where the `-V` blocker lived.** Their table said `-v`/`--version` with no `-V` for a full round while every probe we shipped sent `-V`; a rejected flag exits non-zero, and every probe here reads non-zero as *"the tool is not installed"* |
| `--verify-log` | asks the ripper to verify **its own** log with its own checksum | the one verdict in our report that is not ours, which is the entire reason it exists |

**A probe invocation and a rip invocation are different contracts**, and the
merged table must say which each flag belongs to. Ours currently does not.

## 1a. Measured limits — our own half, black-box (S-9)

**This section is GENERATED.** Run `python scripts/probe_argv_surface.py`
and paste; never hand-edit. S-9 asks each side to establish its limits by
probing its own surface, and a hand-transcribed range is a claim about
behaviour nobody ran — which is what the type/range columns in §1 still are.

It found six unvalidated values reaching the argv on first run: `-r -1`,
`-r 2147483648`, `-S 999`, `-S 2147483648`, `-s 2147483648` and `-Z 1000`.
Every one was outside the range the Settings dialog enforces, and every one
was reachable because **the range was checked at the Settings boundary and
nowhere else** — so a hand-edited `config.toml` sent it straight to a C
program. Now refused at the argv chokepoint, with the flag, the value and
the acceptable range named in the message (S-12 `usable`, not `generic`).

<!-- GENERATED by scripts/probe_argv_surface.py — do not hand-edit. -->

### Measured outbound behaviour (black-box, our own surface)

Each row is one probe of `_build_rip_argv`: one parameter changed against a
known-good baseline, and what actually reached the argv. `dropped` means the
call succeeded and the flag is **absent** — a silently ignored argument,
which is the outcome S-9 most wants written down.

| parameter | value | outcome | what happened |
|---|---|---|---|
| `max_retries` | `-1` | **raised** | RipError: refusing -r -1 (per-track retries): outside the accepted range 0..100. This is the same range the Settings dialog enforces; a value arriving from a hand-edited config, a previous disc, or a future caller that skips Settings is checked here too |
| `max_retries` | `0` | **dropped** | -r absent from argv |
| `max_retries` | `1` | **emitted** | -r 1 · chokepoint ok |
| `max_retries` | `5` | **emitted** | -r 5 · chokepoint ok |
| `max_retries` | `100` | **emitted** | -r 100 · chokepoint ok |
| `max_retries` | `10000` | **raised** | RipError: refusing -r 10000 (per-track retries): outside the accepted range 0..100. This is the same range the Settings dialog enforces; a value arriving from a hand-edited config, a previous disc, or a future caller that skips Settings is checked here too |
| `max_retries` | `2147483648` | **raised** | RipError: refusing -r 2147483648 (per-track retries): outside the accepted range 0..100. This is the same range the Settings dialog enforces; a value arriving from a hand-edited config, a previous disc, or a future caller that skips Settings is checked here too |
| `read_speed` | `-1` | **raised** | RipError: refusing read_speed=-1: a negative is not 'auto' (0 means drive maximum). Dropping the flag silently would hide a caller bug behind a default that looks deliberate |
| `read_speed` | `0` | **dropped** | -S absent from argv |
| `read_speed` | `1` | **emitted** | -S 1 · chokepoint ok |
| `read_speed` | `4` | **emitted** | -S 4 · chokepoint ok |
| `read_speed` | `48` | **emitted** | -S 48 · chokepoint ok |
| `read_speed` | `999` | **raised** | RipError: refusing -S 999 (fixed read speed): outside the accepted range 0..72. This is the same range the Settings dialog enforces; a value arriving from a hand-edited config, a previous disc, or a future caller that skips Settings is checked here too |
| `read_speed` | `2147483648` | **raised** | RipError: refusing -S 2147483648 (fixed read speed): outside the accepted range 0..72. This is the same range the Settings dialog enforces; a value arriving from a hand-edited config, a previous disc, or a future caller that skips Settings is checked here too |
| `secure_rerip_matches` | `-1` | **raised** | RipError: refusing secure_rerip_matches=-1: a negative is not 'auto' (0 is). Dropping the flag silently would hide a caller bug behind a default that looks deliberate |
| `secure_rerip_matches` | `0` | **dropped** | -Z absent from argv |
| `secure_rerip_matches` | `1` | **emitted** | -Z 1 · chokepoint ok |
| `secure_rerip_matches` | `2` | **emitted** | -Z 2 · chokepoint ok |
| `secure_rerip_matches` | `10` | **emitted** | -Z 10 · chokepoint ok |
| `secure_rerip_matches` | `1000` | **raised** | RipError: refusing -Z 1000 (secure re-read matches): outside the accepted range 0..10. This is the same range the Settings dialog enforces; a value arriving from a hand-edited config, a previous disc, or a future caller that skips Settings is checked here too |
| `read_offset_override` | `-2000` | **emitted** | -s -2000 · chokepoint ok |
| `read_offset_override` | `-667` | **emitted** | -s -667 · chokepoint ok |
| `read_offset_override` | `0` | **emitted** | -s 0 · chokepoint ok |
| `read_offset_override` | `667` | **emitted** | -s 667 · chokepoint ok |
| `read_offset_override` | `5000` | **emitted** | -s 5000 · chokepoint ok |
| `read_offset_override` | `2147483648` | **raised** | RipError: refusing -s 2147483648 (read offset correction): outside the accepted range -5000..5000. This is the same range the Settings dialog enforces; a value arriving from a hand-edited config, a previous disc, or a future caller that skips Settings is checked here too |
| `album_title` | `'A: colon, unescaped'` | **emitted** | round-tripped through 'album=A\\: colon, unescaped' |
| `album_title` | `'trailing backslash \\'` | **emitted** | round-tripped through 'album=trailing backslash \\\\' |
| `album_title` | `'A=equals, unescaped'` | **emitted** | round-tripped through 'album=A\\=equals, unescaped' |
| `album_title` | `':'` | **emitted** | round-tripped through 'album=\\:' |
| `album_title` | `'='` | **emitted** | round-tripped through 'album=\\=' |
| `album_title` | `'::'` | **emitted** | round-tripped through 'album=\\:\\:' |
| `album_title` | `'=='` | **emitted** | round-tripped through 'album=\\=\\=' |
| `album_title` | `'a:=b'` | **emitted** | round-tripped through 'album=a\\:\\=b' |
| `album_artist` | `'B: colon, unescaped'` | **emitted** | round-tripped through 'album=Probe Album:album_artist=B\\: colon, unescaped' |
| `track_title` | `'T: colon, unescaped'` | **emitted** | round-tripped through '1=title=T\\: colon, unescaped' |
| `track_title` | `':'` | **emitted** | round-tripped through '1=title=\\:' |
| `track_isrc` | `'IS:RC'` | **emitted** | round-tripped through '1=title=T:isrc=IS\\:RC' |

**38 probes: 26 emitted, 3 dropped, 9 raised.**

**Range axis — 26 probes. Silently-dropped non-zero values (findings): 0** — none. Every value a caller set either reached the argv or was refused.

**Shape axis — 12 probes, 12 round-tripped intact, 0 mangled, 0 wrongly refused. Findings: 0** — none. Every structurally awkward value came back out of the blob byte-for-byte, and none was refused for being awkward.

*Two axes with opposite expectations: on the range axis a refusal is the desired outcome, on the shape axis it is a defect. Reported separately because one total cannot mean both.*

**Chokepoint refusals across every probe: 0** — none, so no probe value can smuggle an argv past the `-N` guard.

## 2a. Return-path artifacts — the ripper's OUTPUT is contract surface too

**Added round 7 lap 29, and the reason it was missing is the finding.** This table
had an outbound half and no inbound half, so the `.cue` the ripper writes — which
we ship to the user unread — was governed by nothing. A rip on pin `9048082` lost
**9 of its 14 ISRCs** and nothing noticed, because nothing here looked.

Every row is `verified` (a test asserts it) or `documented-untested`, per S-11.

| artifact / field | type | what it must satisfy | how it is checked | status | **PP** | **CR** |
|---|---|---|---|---|---|---|
| `.cue` → `ISRC` per track | `str`, 12 chars `[A-Z0-9]` | **every ISRC we sent must come back** on its track. We send N, the log records N, the cue must carry N | `cue_validate.validate_cue` ISRC round-trip; `tests/test_cue_validate.py` | verified | HAVE | **? — broken on `9048082`** |
| `.cue` → `INDEX 00` presence | marker | present iff the log's per-track `Pregap length` is non-zero; **track 1 exempt** (its lead-in gap cannot append to a previous track) | same validator, pregap agreement | verified | HAVE | HAVE |
| `.cue` → `INDEX 00` value | `MM:SS:FF` | an offset **within its own `FILE`**, not an absolute disc position. Resolve against that file's start LSN before comparing — a naive absolute comparison reports 8 false mismatches of 9 | lap-29 §A, checked on all 9 markers | verified | HAVE | HAVE |
| `.cue` → `TITLE` / `PERFORMER` | `str`, arbitrary Unicode | must be the **real** metadata, compared **character for character** against the text we sent — which catches substitution, truncation and any other mangling with one assertion. Should carry a real colon from beta.6 + app 0.6.4b13 on; **unconfirmed until a rig rip** | title-fidelity check, tri-state; `FILE` lines deliberately exempt | verified | HAVE | HAVE |
| `.cue` → track numbering | `int` | contiguous from 1, every track has `INDEX 01`, count matches the disc | structural sanity check | verified | HAVE | ? |
| `.log` → `album:` field | `str` | same U+2236 issue as the cue's `TITLE` | — | documented-untested | ? | ? |
| `.log` → its own FUN512 checksum | `str` | `--verify-log` exits 0 with *"checksum valid"* on an unmodified log | `rip_audit`, every rip | verified | HAVE | HAVE |

**Why `FILE` lines are exempt from the colon check, and why that exemption is
load-bearing.** `FILE` names a real path on disk, and the substitute character is
genuinely *in* that filename. "Repairing" it there would name a file that does not
exist. A validator that flagged it would be worse than none, because the false
positive teaches people to ignore the true ones.

## 3. EXPECT — behaviours we rely on that are not flags

| we expect | if it changes |
|---|---|
| the version banner carries `platterpus-fork` in its parenthetical | our fork/stock/**not-determined** classification collapses to not-determined for every rip |
| a `-dirty` marker when built from a dirty tree | a build tag names a commit, not what was built — round 6 shipped two golden references whose banners named commits three behind the pin |
| durations as `MM:SS.FF` in CD frames | we parse them as frames. This shape changed **upstream** and we misattributed it to the fork for a round |
| per-track paranoia counters sum to the disc totals **without `-Z`** | under `-Z` the per-track figure is the *last pass* and the disc total is *every* pass, so a consumer rendering the disc tally as a count of distinct events over-reports by the re-read factor |
| fatal messages match their published format strings | we build the matcher from those strings rather than a hand-kept list, precisely so this expectation is mechanical |
| exit codes are meaningful and documented | we record them tri-state; `null` for a child never reaped is a real answer and must never be written `0` |

## 4. NEED — blocking

1. **Types and argument shapes in their published table.** Their §P1 gives flags
   and spellings. It does not give argument *types*, so a flag whose argument
   changed from an int to a string would pass our agreement test silently. We
   cannot close the type half of the contract without this.
2. **A statement on the `-a` blob.** We hand the entire tag set as **one
   colon-delimited argument** carrying user-edited and MusicBrainz-sourced text.
   We sanitise it outbound; we do not know what they do with it inbound, and a
   value that survives our check and breaks theirs is the exact gap the
   double-check rule exists for.
3. **Which of their 41 flags are rip-path and which are probe-path**, so §2's
   distinction can be mechanical rather than ours to infer.
4. **An escape mechanism in the `-a` / `-t` grammar — or a written statement that
   there is none.** Both flags are `key=value` pairs joined by `:`, and there is
   no documented way to express a value that *contains* a colon. Album and track
   titles contain them constantly; the reference disc is literally *"Every Breath
   You Take: The Classics"*.

   We work around it by substituting **U+2236 RATIO** (`∶`), which is visually
   identical and does not break their parser, then repairing it afterwards — but
   only in the two artifacts we own (the FLAC tags, via `metaflac`; and our
   EAC-style log). **Their cue and their log keep the substitute**, so a user
   importing that cue sees a ratio character in their album title.

   This is the oldest live defect at this seam and neither side had written it
   down. Three things are needed and all three are cheap: the escape syntax, a
   row in their contract stating what the parser does with a literal colon
   *today* (split / error / last-wins — **we have never sent one, so we do not
   know, and S-9 says we do not probe their binary to find out**), and until
   then, the limitation recorded rather than passed around as folklore.

## 5. WANT — non-blocking

1. **A machine-readable form of their table** (JSON or TSV beside the Markdown).
   We currently parse their Markdown, which is a contract we did not agree to.
2. **Confirmation of `-F` and the `-I`/`-J` exclusion.** Both are in our builder
   and our hand-written contract; neither has a recorded *reason*. We would
   rather delete them than carry flags we cannot explain.
3. **Their view on the 41-versus-18 gap** — for each flag we do not send, whether
   we are declining it, cannot use it, or have not noticed it. Today nothing
   records which.

## 6. What we owe next

- Extend `scripts/emit_dependency_contract.py` to emit the **type**, **range** and
  **path** (rip vs probe) columns from the builder's own signatures and range
  checks, so §1 and §2 stop being hand-transcribed.
- Build the merge into `docs/seam-commands.md`, with a status from **each** side
  per row, so a `we-send` / `they-accept` disagreement is a visible row rather
  than a broken release.
- Propose it in the round-8 outbound alongside `docs/seam-rules.md`.

---

## 7. cyanrip's half — MEASURED, black-box, on our own binary (S-9)

**This section is GENERATED** by `tools/probe-argv-surface.py --markdown` and is
a CI gate in `--gate` mode (`meson test -C build 'Argv surface probe'`), so a
value that starts vanishing without a refusal fails the build rather than
waiting for a round. Never hand-edit it.

Method: `-I` on a disc image, so this probes argument handling and not the
drive, and `-N -A -U` keep it off the network. Each row is one invocation of
the real binary. **`ignored` means exit 0 and the value gone** — the outcome
S-9 most wants recorded, and there are none.

### What it found in us

- **`-s` was unbounded and reached undefined behaviour.** The option table took
  the full int32 range; UBSAN reports three distinct UB sites on `INT32_MIN` —
  a negation in `cyanrip_run()`, the `abs()` in the `Offset:` log line (which
  printed `Offset:  --2147483648 samples`, a doubled sign in a contract line),
  and `offset*4` in `setup_track_lsn()`. **Now bounded to ±1048576 samples**
  (~23.8 s, three orders of magnitude past any real drive), refused by genopt
  with the flag, the value and the range named. Regression test in `sc_cli`.
- **Two bugs in the probe itself**, found by disbelieving its own output: it
  called `-s 0` silently-ignored because the header prints a sign and the
  comparison was textual, and it called `-J` alone refused-by-`-I` because the
  interaction probes inherited `-I` from the base invocation. Same shape as the
  false alarm you hit resolving `INDEX 00` against absolute LSNs.

### What it did NOT find, and why that is the more useful half

**`-t` without its `=` published adjacent process memory, and this probe walked
straight past it for a whole round.** You found it by reading the source (lap 31
J3), not us by running the binary — so S-9's "limits are established by running
the binary" bought nothing here, and it is worth being precise about why rather
than filing it as a win for source review.

Every `-t` value in the grid above was **well-formed**: `1=title=x`,
`1=title=a:b`, `0=title=x`, `99=title=x`. The grid varied the *track number* and
the *value*, and never once varied the **shape**. The defect lived in the shape.
A probe that only feeds well-formed arguments measures how the happy path
handles bad data, which is not the same thing and reads identically in a summary
— "82 probes, 0 silently ignored" was true, and the interesting input was not
among the 82.

So we added the missing axis — separator absent, doubled, empty on either side,
trailing — to **every** argument with internal structure (`-t`, `-a`, `-p`,
`-c`, `-C`), not just to the one you reported. The grid went 82 probes → 111.

### What the new axis found on its first run: four segfaults

**`-c /`, `-c //`, `-p =` and `-p ==` killed cyanrip with SIGSEGV.** Exit 139,
and **not one line of output** — the undiagnosable non-zero exit our shared
rules call the one failure a consumer cannot explain to a user. ASAN puts it at
`cyanrip_main.c:1575`:

```
ERROR: AddressSanitizer: SEGV on unknown address 0x000000000000
    #0 __GI_____strtol_l_internal ../stdlib/strtol_l.c:304
    #3 cyanrip_run ../src/cyanrip_main.c:1575
```

An argument consisting only of its own separator tokenises to **no token at
all**, so `av_strtok()` returns `NULL` and `strtol()` dereferences it. The
second `av_strtok()` in both functions was always `NULL`-checked; the first
never was, because a non-empty string was assumed to yield at least one token.
Both fixed, each revert-proved on its own, and `'/'`, `'//'`, `'='`, `'=='` are
rows in §7 now.

Three things worth carrying across the seam, because none of them is about `-t`:

- **Our own gate graded a segfault as a clean refusal.** `probe()` mapped every
  non-zero exit to `refused`, and Python reports signal death as a *negative*
  returncode, so `-11` was filed as a successful refusal and the gate printed
  `0 silently ignored` and exited **0** while the binary was crashing. Measured,
  not inferred: with the guard removed and the pre-lap-32 gate restored, it
  still exits 0. `crashed` is now its own outcome class, checked first so it
  cannot be masked, and a non-zero exit with no message is now a gate failure
  in its own right. **If your probe classifies by exit code, check the sign.**
- **A summary that counts only the failure mode you thought of reads as
  all-clear.** `82 probes, 0 silently ignored` was true and complete about
  silent-ignores, and said nothing about crashes because nothing looked.
- **Neither sanitizer covers the `-t` class**, so a green ASAN/UBSAN run is not
  evidence there. argv and environ strings share the initial stack block, so an
  overread out of one and into the next crosses no redzone either tool
  maintains. Confirmed by running the pre-fix binary under both: it leaked the
  environment variable into the FLAC tags and exited 0, silently, with no
  sanitizer diagnostic. The crashes above *are* caught by ASAN — the two
  classes differ, and "we run sanitizers" covers one and not the other.

### Answers to §4.4 and your Q3/Q4 — **an escape exists and always has**

`-a` and `-t` are split by `av_dict_parse_string(dict, str, "=", ":", 0)`,
which is **FFmpeg's** parser, and it implements a backslash escape. Measured,
all four on the real binary:

| input | result | exit |
|---|---|---|
| `-a 'album=A: B'` | `album=A` — **splits, and the fragment with no `=` is silently discarded** | 0 |
| `-a 'album=A\: B'` | `album=A: B` | 0 |
| `-a 'album=A\=B'` | `album=A=B` | 0 |
| `-a 'album=A\\B'` | `album=A\B` | 0 |
| `-t '1=title=A\: B'` | `title=A: B` — same grammar | 0 |

**So `\:` is the escape, it works in both flags, and your U+2236 substitution is
not needed.** Verified end to end: `-a 'album=Every Breath You Take\: The
Classics'` produces `TITLE "Every Breath You Take: The Classics"` in the cue.

This was never documented — by upstream or by us — which is why it was folklore
on both sides. It is now in `PROVIDER-CONTRACT.md`. **Ask (C-1) is answered by
measurement rather than by new work; ask (C-3) is answered above: split, tail
dropped, no message, exit 0.** That last is an S-12 **`absent`** grade and we
are recording it as a defect row of ours, not as documented behaviour.

Single and double quotes do **not** work as delimiters and produce garbage
rather than an error — also an `absent` row.

### Measured argument behaviour (black-box, our own binary)

| flag | meaning | value | outcome | exit | message / observed |
|---|---|---|---|---|---|
| `-s` | read offset, samples | `-2147483648` | **refused** | 1 | Error parsing -2147483648 for argument "offset": not in [-1048576:1048576] range! |
| `-s` | read offset, samples | `-5000` | **accepted** | 0 | -5000 |
| `-s` | read offset, samples | `-667` | **accepted** | 0 | -667 |
| `-s` | read offset, samples | `0` | **accepted** | 0 | +0 |
| `-s` | read offset, samples | `667` | **accepted** | 0 | +667 |
| `-s` | read offset, samples | `5000` | **accepted** | 0 | +5000 |
| `-s` | read offset, samples | `2147483647` | **refused** | 1 | Error parsing 2147483647 for argument "offset": not in [-1048576:1048576] range! |
| `-r` | frame/rip retries | `-1` | **refused** | 1 | Error parsing -1 for argument "retries": not in [0:2147483647] range! |
| `-r` | frame/rip retries | `0` | **accepted** | 0 | 0 |
| `-r` | frame/rip retries | `1` | **accepted** | 0 | 1 |
| `-r` | frame/rip retries | `10` | **accepted** | 0 | 10 |
| `-r` | frame/rip retries | `2147483647` | **accepted** | 0 | 2147483647 |
| `-r` | frame/rip retries | `2147483648` | **refused** | 1 | Error parsing 2147483648 for argument "retries": not in [0:2147483647] range! |
| `-Z` | repeat rips until N matches | `-1` | **refused** | 1 | Error parsing -1 for argument "repeat_rips": not in [0:2147483647] range! |
| `-Z` | repeat rips until N matches | `0` | **accepted** | 0 | (no header field exposes this) |
| `-Z` | repeat rips until N matches | `1` | **accepted** | 0 | (no header field exposes this) |
| `-Z` | repeat rips until N matches | `2` | **accepted** | 0 | (no header field exposes this) |
| `-Z` | repeat rips until N matches | `10` | **accepted** | 0 | (no header field exposes this) |
| `-Z` | repeat rips until N matches | `2147483647` | **accepted** | 0 | (no header field exposes this) |
| `-S` | drive speed multiplier | `-1` | **refused** | 1 | Error parsing -1 for argument "speed": not in [0:2147483647] range! |
| `-S` | drive speed multiplier | `0` | **accepted** | 0 | (no header field exposes this) |
| `-S` | drive speed multiplier | `1` | **refused** | 1 | Device does not support changing speeds! |
| `-S` | drive speed multiplier | `48` | **refused** | 1 | Device does not support changing speeds! |
| `-S` | drive speed multiplier | `2147483647` | **refused** | 1 | Device does not support changing speeds! |
| `-k` | stall threshold, seconds | `-1` | **refused** | 1 | Error parsing -1 for argument "stall_secs": not in [0:2147483647] range! |
| `-k` | stall threshold, seconds | `0` | **accepted** | 0 | (no header field exposes this) |
| `-k` | stall threshold, seconds | `1` | **accepted** | 0 | (no header field exposes this) |
| `-k` | stall threshold, seconds | `10` | **accepted** | 0 | (no header field exposes this) |
| `-k` | stall threshold, seconds | `2147483647` | **accepted** | 0 | (no header field exposes this) |
| `-P` | paranoia level | `-1` | **refused** | 1 | Invalid paranoia level -1 must be between 0 and 3! |
| `-P` | paranoia level | `0` | **accepted** | 0 | none |
| `-P` | paranoia level | `1` | **accepted** | 0 | 1 |
| `-P` | paranoia level | `3` | **accepted** | 0 | max |
| `-P` | paranoia level | `4` | **refused** | 1 | Invalid paranoia level 4 must be between 0 and 3! |
| `-P` | paranoia level | `999` | **refused** | 1 | Invalid paranoia level 999 must be between 0 and 3! |
| `-m` | cover art max size | `-2` | **refused** | 1 | Error parsing -2 for argument "cover_size": not in [-1:1200] range! |
| `-m` | cover art max size | `-1` | **accepted** | 0 | (no header field exposes this) |
| `-m` | cover art max size | `250` | **accepted** | 0 | (no header field exposes this) |
| `-m` | cover art max size | `500` | **accepted** | 0 | (no header field exposes this) |
| `-m` | cover art max size | `1200` | **accepted** | 0 | (no header field exposes this) |
| `-m` | cover art max size | `999` | **refused** | 1 | Invalid max coverart size 999 (must be 250, 500, 1200 or -1) |
| `-b` | lossy bitrate, kbps | `-1` | **refused** | 1 | Error parsing -1.000000 for argument "bitrate": not in [0.000000:10000.000000] range! |
| `-b` | lossy bitrate, kbps | `0` | **accepted** | 0 | (no header field exposes this) |
| `-b` | lossy bitrate, kbps | `1` | **accepted** | 0 | (no header field exposes this) |
| `-b` | lossy bitrate, kbps | `256` | **accepted** | 0 | (no header field exposes this) |
| `-b` | lossy bitrate, kbps | `100000` | **refused** | 1 | Error parsing 100000.000000 for argument "bitrate": not in [0.000000:10000.000000] range! |
| `-l` | track list | `0` | **refused** | 1 | Invalid rip index 0, list has 2 tracks! |
| `-l` | track list | `1` | **accepted** | 0 | (no header field exposes this) |
| `-l` | track list | `2` | **accepted** | 0 | (no header field exposes this) |
| `-l` | track list | `3` | **refused** | 1 | Invalid rip index 3, list has 2 tracks! |
| `-l` | track list | `99` | **refused** | 1 | Invalid rip index 99, list has 2 tracks! |
| `-c` | disc/totaldiscs | `'0/0'` | **refused** | 1 | Invalid discnumber 0 |
| `-c` | disc/totaldiscs | `'1/1'` | **accepted** | 0 | (no header field exposes this) |
| `-c` | disc/totaldiscs | `'2/1'` | **refused** | 1 | discnumber 2 is larger than totaldiscs 1 |
| `-c` | disc/totaldiscs | `'1/2'` | **accepted** | 0 | (no header field exposes this) |
| `-c` | disc/totaldiscs | `'1'` | **accepted** | 0 | (no header field exposes this) |
| `-c` | disc/totaldiscs | `'1/'` | **accepted** | 0 | (no header field exposes this) |
| `-c` | disc/totaldiscs | `'/2'` | **accepted** | 0 | (no header field exposes this) |
| `-c` | disc/totaldiscs | `'1//2'` | **accepted** | 0 | (no header field exposes this) |
| `-c` | disc/totaldiscs | `'/'` | **refused** | 1 | Missing discnumber |
| `-c` | disc/totaldiscs | `'//'` | **refused** | 1 | Missing discnumber |
| `-u` | consumer tag | `''` | **accepted** | 0 | (reported |
| `-u` | consumer tag | `'x'` | **accepted** | 0 | x |
| `-u` | consumer tag | `'platterpus/0.6.4b12'` | **accepted** | 0 | platterpus/0.6.4b12 |
| `-u` | consumer tag | `'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'` | **accepted** | 0 | aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa |
| `-a` | album metadata blob | `''` | **accepted** | 0 | (no header field exposes this) |
| `-a` | album metadata blob | `'album=x'` | **accepted** | 0 | (no header field exposes this) |
| `-a` | album metadata blob | `'album=a:b'` | **accepted** | 0 | (no header field exposes this) |
| `-a` | album metadata blob | `'album=zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz'` | **accepted** | 0 | (no header field exposes this) |
| `-a` | album metadata blob | `'album'` | **accepted** | 0 | (no header field exposes this) |
| `-a` | album metadata blob | `'=x'` | **refused** | 1 | Error reading album tags: Invalid argument |
| `-a` | album metadata blob | `'album='` | **refused** | 1 | Error reading album tags: Invalid argument |
| `-a` | album metadata blob | `'a=b:'` | **accepted** | 0 | (no header field exposes this) |
| `-a` | album metadata blob | `'a=b::c=d'` | **accepted** | 0 | (no header field exposes this) |
| `-a` | album metadata blob | `'a==b'` | **accepted** | 0 | (no header field exposes this) |
| `-a` | album metadata blob | `'album=x\\'` | **accepted** | 0 | (no header field exposes this) |
| `-t` | track metadata | `'1=title=x'` | **accepted** | 0 | (no header field exposes this) |
| `-t` | track metadata | `'1=title=a:b'` | **accepted** | 0 | (no header field exposes this) |
| `-t` | track metadata | `'0=title=x'` | **refused** | 1 | Invalid track number 0, list has 2 tracks! |
| `-t` | track metadata | `'99=title=x'` | **refused** | 1 | Invalid track number 99, list has 2 tracks! |
| `-t` | track metadata | `'1'` | **refused** | 1 | Missing "=" in track metadata "1" |
| `-t` | track metadata | `'99'` | **refused** | 1 | Invalid track number 99, list has 2 tracks! |
| `-t` | track metadata | `'1='` | **accepted** | 0 | (no header field exposes this) |
| `-o` | output formats | `'flac'` | **accepted** | 0 | (no header field exposes this) |
| `-o` | output formats | `''` | **refused** | 1 | Invalid format "" |
| `-o` | output formats | `'nosuchformat'` | **refused** | 1 | Invalid format "nosuchformat" |
| `-o` | output formats | `'flac,flac'` | **refused** | 1 | Duplicated format "flac" |
| `-T` | filename sanitation | `'simple'` | **accepted** | 0 | (no header field exposes this) |
| `-T` | filename sanitation | `'os_simple'` | **accepted** | 0 | (no header field exposes this) |
| `-T` | filename sanitation | `'unicode'` | **accepted** | 0 | (no header field exposes this) |
| `-T` | filename sanitation | `'os_unicode'` | **accepted** | 0 | (no header field exposes this) |
| `-T` | filename sanitation | `'bogus'` | **refused** | 1 | Invalid sanitation method bogus |
| `-p` | pregap action | `'1=default'` | **accepted** | 0 | (no header field exposes this) |
| `-p` | pregap action | `'1=drop'` | **accepted** | 0 | (no header field exposes this) |
| `-p` | pregap action | `'1=merge'` | **accepted** | 0 | (no header field exposes this) |
| `-p` | pregap action | `'1=track'` | **accepted** | 0 | (no header field exposes this) |
| `-p` | pregap action | `'1=bogus'` | **refused** | 1 | Invalid pregap action bogus |
| `-p` | pregap action | `'99=drop'` | **accepted** | 0 | (no header field exposes this) |
| `-p` | pregap action | `'1'` | **refused** | 1 | Missing pregap action |
| `-p` | pregap action | `'=drop'` | **refused** | 1 | Invalid track idx for pregap: 0 |
| `-p` | pregap action | `'1='` | **refused** | 1 | Missing pregap action |
| `-p` | pregap action | `'1==drop'` | **accepted** | 0 | (no header field exposes this) |
| `-p` | pregap action | `'1=drop='` | **accepted** | 0 | (no header field exposes this) |
| `-p` | pregap action | `'='` | **refused** | 1 | Missing track idx for pregap |
| `-p` | pregap action | `'=='` | **refused** | 1 | Missing track idx for pregap |
| `-C` | cover art location | `'Front=/nonexistent.png'` | **refused** | 1 | Unable to open "/nonexistent.png": No such file or directory! |
| `-C` | cover art location | `'Front='` | **refused** | 1 | Unable to open "": No such file or directory! |
| `-C` | cover art location | `'=/nonexistent.png'` | **refused** | 1 | Unable to open "/nonexistent.png": No such file or directory! |
| `-C` | cover art location | `'Front'` | **refused** | 1 | Unable to open "Front": No such file or directory! |
| `-C` | cover art location | `'1='` | **refused** | 1 | Unable to open "": No such file or directory! |
| `-C` | cover art location | `'='` | **refused** | 1 | Unable to open "": No such file or directory! |

### Interactions

| flags | meaning | outcome | exit | message |
|---|---|---|---|---|
| `-I -J` | info-only with cue-only | **refused** | 1 | -J (only generate a CUE sheet) cannot be used with -I (only print info)! |
| `-J` | cue-only alone | **accepted** | 0 |  |
| `-E -W` | force deemphasis with no-deemphasis | **accepted** | 0 |  |
| `-x` | cache probe on an image | **accepted** | 0 |  |
| `-f` | find-offset on an image | **accepted** | 0 |  |

**111 probes: 65 accepted, 46 refused, 0 silently ignored.**

**Silently-ignored values: none.** Every value either took effect or was refused with a message.


### Exit codes, graded (S-12)

| grade | count | which |
|---|---|---|
| **usable** | most refusals | every range refusal names the flag, the value and the accepted range; every enum refusal names the invalid value. The message distinguishes, the code does not |
| **generic** | **the exit code itself, always `1`** | **a defect row of ours.** Every refusal above exits `1`. A caller cannot tell a bad `-s` from a bad `-o` from a missing device by code alone — only by message, which S-12 then makes contract surface |
| **absent** | `-a`/`-t` colon split; `-E -W` together; quotes in `-a` | no code and no message. The colon case silently drops data, which is the worst of the three |

**We are not proposing distinct exit codes this round**, because the numbers
would become contract surface and this round is already carrying a cue change.
Proposed for round 8 with the `generic` row left standing until then, per S-12.

---
