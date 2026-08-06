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

> **Provenance warning.** The *type* and *range* columns are currently
> **hand-transcribed from the argv builder**, and this project's own rule is that
> a hand-maintained description of behaviour goes stale invisibly. Treat this as a
> **draft for review** until `scripts/emit_dependency_contract.py` emits these
> columns from the builder's own signatures and range checks. That extension is
> the real deliverable; this file is its specification and the fork's copy to
> answer against.
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
| `-N` | — | flag | **always present, unconditionally** | disable cyanrip's own MusicBrainz lookup. Critical rule #5; its interactive prompt would hang a GUI rip with no terminal | HAVE | ? |
| `-d` | device | `str`, absolute path | must exist, must be a block device | the drive | HAVE | ? |
| `-o` | format | `str` enum | **always `flac`** | archival master; every other format is transcoded host-side, so the ripper is never asked for a lossy encode | HAVE | ? |
| `-D` | directory | `str`, path | writable | output directory | HAVE | ? |
| `-a` | tag blob | `str`, colon-delimited | no newline, no NUL, bounded. **No escape syntax exists**, so a value containing `:` is unrepresentable — see §4.4 | the whole tag set as one argument — **this is the value we are least comfortable with** | HAVE | ? |
| `-t` | track list | `str`, `n=` / ranges | **range-checked against the disc's real track count** | which tracks to rip. A `-t 17=` on a 16-track disc killed a rip in two seconds | HAVE | ? |
| `-c` | disc position | `int/int` | both ints, `number <= total`, else the flag is dropped | `DISCNUMBER` / `TOTALDISCS` | HAVE | ? |
| `-s` | offset | `int`, samples | drive-plausible range | read offset correction | HAVE | ? |
| `-S` | speed | `int` multiplier | bounded; `0` = drive max | read speed, fixed mode only | HAVE | ? |
| `-r` | retries | `int` | bounded | per-track retry count | HAVE | ? |
| `-Z` | matches | `int` | `0` disables | secure re-read consensus — the Test & Copy equivalent. **Measured with `-Z 2`**: track 5 converged after 3 reads, and the per-track paranoia counters then report the *last* pass while the disc totals report *every* pass (§3) | HAVE | ? |
| `-l` | track number(s) | `int` list | must name tracks that exist on the disc | rip only these tracks. **Also how the auto-fix re-rip runs** — a second invocation with `-l <n>`, which is the structural signal that a pass is a subset rather than the whole album (it is what our progress model now keys on) | HAVE | ? |
| `-G` | — | flag | conditional | disable cover-art embedding; we embed host-side | HAVE | ? |
| `-O` | — | flag | **opt-in only** | overread into lead-in/lead-out. Their own help says it *"may freeze if unsupported by drive"*, so it is never on by default | HAVE | ? |
| `-F` | — | flag | conditional | — *(transcribed from the builder; semantics need confirming, see §5)* | HAVE | ? |
| `-I` | — | flag | **never with `-J`** | — *(mutual exclusion recorded in `dependency-contracts.md`; we should state why)* | HAVE | ? |
| `--consumer` | tag | `str`, `<name>/<version>` | no whitespace, contains `/` | who we tell them we are. Validated because it is written verbatim into an archival log as the identity of the producing program | HAVE | ? |

## 2. Probe-path flags, which is a separate call and a separate risk

| flag | why it is separate | the lesson attached to it |
|---|---|---|
| `--version` | a probe, not a rip. Does not pass the rip chokepoint | **this is where the `-V` blocker lived.** Their table said `-v`/`--version` with no `-V` for a full round while every probe we shipped sent `-V`; a rejected flag exits non-zero, and every probe here reads non-zero as *"the tool is not installed"* |
| `--verify-log` | asks the ripper to verify **its own** log with its own checksum | the one verdict in our report that is not ours, which is the entire reason it exists |

**A probe invocation and a rip invocation are different contracts**, and the
merged table must say which each flag belongs to. Ours currently does not.

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
| `.cue` → `TITLE` / `PERFORMER` | `str`, arbitrary Unicode | must be the **real** metadata. Currently carries our U+2236 colon substitute, because `-a` has no escape (§4.4) | colon-fidelity check; `FILE` lines deliberately exempt | verified | HAVE | ? |
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

*Last updated for Platterpus v0.6.4b12.*
