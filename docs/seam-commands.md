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
| `-a` | tag blob | `str`, colon-delimited | no newline, no NUL, bounded | the whole tag set as one argument — **this is the value we are least comfortable with**, see §4 | HAVE | ? |
| `-t` | track list | `str`, `n=` / ranges | **range-checked against the disc's real track count** | which tracks to rip. A `-t 17=` on a 16-track disc killed a rip in two seconds | HAVE | ? |
| `-c` | disc position | `int/int` | both ints, `number <= total`, else the flag is dropped | `DISCNUMBER` / `TOTALDISCS` | HAVE | ? |
| `-s` | offset | `int`, samples | drive-plausible range | read offset correction | HAVE | ? |
| `-S` | speed | `int` multiplier | bounded; `0` = drive max | read speed, fixed mode only | HAVE | ? |
| `-r` | retries | `int` | bounded | per-track retry count | HAVE | ? |
| `-Z` | matches | `int` | `0` disables | secure re-read consensus — the Test & Copy equivalent | HAVE | ? |
| `-l` | — | flag | conditional | per-track selection companion | HAVE | ? |
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

*Last updated for Platterpus v0.6.4b11.*
