# cyanrip fork → Platterpus · Round 4 return file · 2026-08-02

> **Self-contained.** This one file carries the round-4 return (§A–J), the regenerated golden
> reference log (**Appendix 1**), and the generated fatal-message inventory (**Appendix 2**).
> Nothing else is needed from the cyanrip side this round.
>
> **The pin moved: `ec406ac` → `a835052`.** A stale pin builds the old banner format and will
> fail your new R1 assertion.


Structured per your §9 (A–J). Every claim tagged **measured**, **read from source**, or
**unverified**.

**Headline:** R1 and A3 are implemented and pushed; the pin has moved. §1 accepted — I have
made no change to `Pregap length`. §H corrects a claim of *mine* from round 3 that was wrong.

---

## A · Pin

| | |
|---|---|
| Repo | `rmccann-hub/cyanrip` |
| Branch | `platterpus-fork` |
| **Commit SHA** | **`a835052ff99a0d1db60fa7f6d85231a8af6a2eaf`** |
| Previous pin | `ec406ac…` — **the SHA has changed, do not reuse it** |

**Exact `--version` output, byte-for-byte** (measured, `cat -A` confirms no trailing space):

```
cyanrip 0.9.4-rc1 (platterpus-fork-ga835052)
```

Verified against **your own R1 regex** rather than my reading of it:

```
regex match           : True
tag                   : 'platterpus-fork-ga835052'
tokens on [-_]        : ['platterpus', 'fork', 'ga835052']
contains platterpus+fork : True
is NOT 'release'      : True
```

⚠️ **The `ga835052` component changes on every commit.** Assert on the shape and the literal
token `platterpus-fork`, not on the whole string, or your test breaks on my next push.

---

## B · Answers to Q1–Q11

### Q1 — Exact `--version` string · **measured**
`cyanrip 0.9.4-rc1 (platterpus-fork-ga835052)` — see A. Identical on the first line of every
rip's logfile (verified by rip, below).

### Q2 — Compiled in, or derived? · **measured** (both halves)

**Split.** `platterpus-fork` is **compiled in**; the `g<sha>` suffix is **derived at build
time**.

- `platterpus-fork` comes from `conf.set_quoted('PROJECT_FORK_ID', 'platterpus-fork')` in
  `meson.build`. It is a string constant in the binary. It cannot vary, cannot be absent, and
  does not depend on git.
- The suffix comes from meson's `vcs_tag(command: ['git','rev-parse','--short','HEAD'])`.

Three cases, all measured:

| Build from | Emits |
|---|---|
| Clean tree at `a835052` | `platterpus-fork-ga835052` |
| **Dirty tree** (uncommitted edits) | `platterpus-fork-ga835052` — **identical, no dirty marker** |
| Detached HEAD | the commit's SHA; works normally |
| **No git metadata** (tarball export) | `vcs_tag` falls back to the literal `release` → **`platterpus-fork-grelease`** |

⚠️ **Two caveats you should encode.**
1. **A dirty build is indistinguishable from a clean one.** `git rev-parse` does not mark it.
   A locally-patched binary claims its base commit. I can add `--dirty` if you want it — say so
   and it is a one-word meson change plus a handshake round.
2. The tarball case produces the substring `release` **inside** the tag. Your rule 3 says the
   tag must not *be* `release`; `platterpus-fork-grelease` is not equal to `release` and
   tokenises to `['platterpus','fork','grelease']`, so it classifies as fork correctly — but if
   you match `release` as a *substring* anywhere, that build would misclassify as stock.

### Q3 — Which buffering fix, on which streams, measured? · **measured**

`setvbuf(fp, NULL, _IOLBF, 0)` immediately after `fopen`, before any write, on **two** streams:

- `src/cyanrip_log.c` — the logfile
- `src/cue_writer.c` — the CUE sheet *(the cue is the same defect in a second file; a patch
  touching only the log leaves the 0-byte cue)*

Both are arrays (`FILE *logfile[]` / `cuefile[]`), one per `-o` format, so a two-format rip has
two of each and all are line-buffered.

**Measured, and the measurement is in G** — including that my *first* revert-proof was vacuous
and said the fix did nothing.

### Q4 — Any path that prompts or blocks on stdin? · **read from source, exhaustive**

**No. There is no read of stdin anywhere in the codebase.**

Grepped `src/*.c` and `src/*.h` for `scanf`, `getchar`, `gets`, `fgets`, `readline`, `getline`,
and the token `stdin`. Exactly one `fgets` exists — `cyanrip_main.c:1806` — and it reads
`ctx->cuefile[0]`, a `FILE*` on the cue file, not stdin. Nothing else touches it, on any path,
including error paths and cover art.

**⚠️ This corrects something I told you last round.** I said `Multiple releases found...` was an
"automation hang risk". **It is not.** Reading `musicbrainz.c:258-296`, that branch does
`ret = 1; goto end_meta;` — it **prints the release list and exits 1**. It never waits. I
reasoned from the message wording instead of reading the code, which is precisely the failure
§10.2 names. R4 is satisfied unconditionally, not merely because you pass `-N`.

### Q5 — Complete exit-code inventory; any silent non-zero exit? · **measured**

**Two values only: `0` and `1`.** There is exactly one `exit()` call in the codebase
(`exit(1)`, the second-Ctrl-C force-quit); every other termination is `return 0` or `return 1`
from `main()`.

| Exit | Meaning |
|---|---|
| `0` | Success — completed rip, `-I`, `-J`, `-h`, `-v`, or a `-Y` whose checksum validated |
| `1` | Everything else: bad argument, unopenable device, `-J`+`-I`, encoder/decoder init failure, rip error, `-Y` mismatch/missing/unreadable |

There is **no distinct code per failure class.** Classification must come from the text.

**Does any non-zero exit occur without a printed diagnosis? No** — audited all 27 `return 1`
sites in `main()`; 26 have a `cyanrip_log()` within the preceding lines. The 27th
(`cyanrip_main.c:1306`, an argument-parse failure) looked silent but is not: the parser prints
first. Measured:

```
args '--bogus-flag'          exit=1  ->  Unable to parse command line argument: --bogus-flag
args '-P'                    exit=1  ->  Missing value for argument "--paranoia"
args '--paranoia=notanumber' exit=1  ->  Unable to parse command line argument: --paranoia=notanumber
args '-s'                    exit=1  ->  Missing value for argument "--offset"
```

Those two strings were **not** in the 45 I sent you last round. Both match your prefixes
(`Unable to `, `Missing `). They are in the inventory in §I.

⚠️ **One caveat that matters for R3.** Argument validation runs *before* the logfile is opened,
so those diagnoses reach **stdout only** — there is no logfile yet to write them to. Your
stdout capture is therefore load-bearing for the entire argument-error class, not optional.

### Q6 — Can I emit the fatal list mechanically? · **measured — yes, and it is attached**

Yes. **Appendix 2** at the end of this file: **88 unique strings**, extracted by
walking every `cyanrip_log()` / `fprintf(stderr,…)` literal in `src/*.c`, with file and line.

**Your 23 prefixes cover 87 of 88.** The single miss:

```
-J (only generate a CUE sheet) cannot be used with -I (only print info)!
```

It begins with a hyphen. Add a `-J ` prefix, or match `cannot be used with`. Everything else —
including `Could not alloc swr context!` and `Could not init swr context!`, which were not in
my earlier 45 — is caught by `Could not`, which you already have.

### Q7 — What a successful sub-channel read looks like · **UNVERIFIED — hand-written, never observed**

**Labelled as intended output. Neither of us has ever seen this.** Constructed by reading
`print_offsets()` and tracing what the code emits when `cyanrip_get_track_pregap_lsn()` returns
via the sub-channel path with `source = CYANRIP_PREGAP_SRC_SUBCHANNEL`:

```
    Pregap LSN:  14327 (duration: 00:02.13)
    Pregap length: 160 frames
    Pregap source: sub-channel (not signalled by TOC)
    Start LSN:   14487
```

Field order, indentation and wording are certain (read from source). **The values are
illustrative** — I used your track 2 numbers so the arithmetic is checkable: 14487 − 14327 =
160 frames = 2.1333 s → truncated `00:02.13`, matching EAC's row.

The `Gaps:` block would carry a matching line, e.g.
`    160 frame pregap in track 2, merging into track 1`.

**What is genuinely unknown:** whether the algorithm returns *correct* LSNs on real media. Only
its failure path has ever executed. §11 item 1 stands.

### Q8 — Does `Pregap length` ever disagree with `Start LSN − Pregap LSN` for n > 1? · **read from source — no**

**No, never, for any track other than 1.** The code computes exactly one value:

```c
int pregap_frames = t->start_lsn_sig - t->pregap_lsn;
if (t->number == 1)
    pregap_frames += lead_in_sectors;   /* 150 */
```

`Pregap length` and the `(duration: …)` suffix are both rendered from that single variable, so
they cannot drift from each other either. For `n > 1` the value **is** the subtraction, with no
adjustment of any kind. Track 1 is the only special case, and it adds exactly 150.

So your preference for my stated value hides nothing: for n > 1 the two are the same number by
construction.

### Q9 — What is in the output directory after a mid-track cancel? · **measured — and there is a surprise**

Measured by `kill -9` immediately after track 1's record appeared, on a 3-track fixture:

```
1.flac        0 bytes     <- track 1, which the LOG reports as fully ripped
2.flac        0 bytes     <- track 2, in progress
log.log    3683 bytes     <- complete through track 1
sheet.cue   251 bytes     <- complete through track 1
```

⚠️ **`1.flac` is 0 bytes even though the log says track 1 succeeded, with its CRC.** Encoding
runs on a per-format thread behind an unbounded FIFO; the rip loop hands off and moves on, and
the encoder's own `avio` buffer plus the muxer trailer never reach disk when the process is
killed. **The log record and the audio file have independent durability.**

**What this means for you:** do not treat a track's presence in the log as evidence its audio
file exists or is playable. After a cancel, stat every file the log claims — a 0-byte or
short FLAC for a "successful" track is expected, not corruption. For cleanup: every `.flac`
present is suspect unless the rip completed; the log and cue are trustworthy up to their last
complete record.

This is pre-existing upstream behaviour, not something the fork introduced. I am not proposing
to change it — forcing an encoder join per track would remove cross-track pipelining.

### Q10 — Cue and logfile written at the same point? · **measured — yes, in lockstep**

Both are written **per track, at the same moment**: `cyanrip_rip_track()` calls
`cyanrip_log_track_end()` then `cyanrip_cue_track()` back to back, and since the fix both
streams are line-buffered. In the Q9 kill both were complete through track 1 and neither was
mid-token.

One asymmetry: the log gets a footer (`Rip completed:`, `Ripping finished at`, `Log FUN512:`)
that the cue has no equivalent of. So a killed rip's cue looks structurally normal — just
short — while the log's missing footer is detectable. **The log is the better completeness
signal; the cue cannot tell you it was truncated.**

### Q11 — Anything wrong in your output · **see §H** (nothing withheld here)

---

## C · Changes since last round

| SHA | Description | Alters log output text? |
|---|---|---|
| `a835052` | Tag the build as `platterpus-fork`; echo the invocation into the log | **YES — see D** |

One commit. Also updated `CLAUDE.md` (R8) in the same commit; that is documentation, not output.

---

## D · Log-format delta

**CHANGED.** Two lines at the top of every logfile. Nothing else — no field reordered, no
existing wording altered, no units changed.

**1. Banner reformatted** (R1):

```
-  cyanrip 0.9.4-rc1 (ec406ac, platterpus-fork)
+  cyanrip 0.9.4-rc1 (platterpus-fork-ga835052)
```

Same information, reshaped to your documented `platterpus-fork-g<sha>` format. The old
comma-separated form also satisfied your token rule, but matching your stated format exactly
removes the ambiguity.

**2. New line, immediately below the banner** (A3):

```
+  Invoked as:     /path/to/cyanrip -d /dev/sr0 -N -A -U -s 667 -o flac -D ... -L log -M sheet
```

Column 0, label padded to the same width as `Drive used:` etc. Arguments containing whitespace,
quotes or backslashes are double-quoted so the line can be pasted back. Emitted unconditionally
whenever a logfile exists.

Suggested pattern (bounded):
```python
r"^Invoked as:\s+(?P<argv>\S.{0,4000})$"
```

**Everything else in the log is byte-identical to the round-3 golden reference.**

---

## E · Regenerated golden reference

**Appendix 1** at the end of this file (replaces the round-3 copy). Extract it verbatim to
`tests/fixtures/cyanrip-fork-golden-reference.log` or wherever your fixtures live.

Produced by, exactly:

```sh
cp tests/fixtures/pregap.cue /tmp/g3/ && cp tests/fixtures/cdda.bin /tmp/g3/pregap.bin
cd /tmp/g3
cyanrip -d pregap.cue -N -A -U -s 0 -P 0 -Z 1 -o flac \
        -D o -F "{track}" -L reference -M sheet
```

First two lines:
```
cyanrip 0.9.4-rc1 (platterpus-fork-ga835052)
Invoked as:     /home/user/cyanrip/build/src/cyanrip -d pregap.cue -N -A -U -s 0 -P 0 -Z 1 -o flac -D o -F {track} -L reference -M sheet
```

Still contains the three cases worth pinning: track 1 pregap 300 frames from TOC (lead-in +
declared), track 2 75 frames from TOC, **track 3 `unknown (sub-channel unreadable)`**.

The validator shipped last round still passes against it unmodified (exit 0, with its expected
warning about track 3's `unknown`).

---

## F · Verification status

### Proven — with how

| Claim | How |
|---|---|
| No audio change vs upstream | Built upstream `958e1ad` in a separate worktree; per-track `EAC CRC32` **identical across basic/pregap/mixed/preemph** after this round's changes. Earlier rounds additionally confirmed **decoded PCM md5 identical** for every output file |
| R1 banner satisfies your rule | Ran your R1 regex against the real `--version` output; match=True, tokens `['platterpus','fork','ga835052']`, not `release` |
| R1 appears in every logfile | Ripped a fixture; banner is line 1 of `log.log`, not only `--version` |
| A3 argv echo | Same rip; `Invoked as:` is line 2, contents match the command issued |
| `setvbuf` fix works under SIGKILL | A/B of reverted vs fixed binaries, **3/3 deterministic** — see G |
| No stdin read anywhere | Exhaustive grep of `src/*.{c,h}` for six stdin-reading APIs; the single `fgets` reads the cue file |
| Exit codes are `{0,1}` only | One `exit()` call in the tree; all other terminations are `return 0/1` from `main()` |
| No silent non-zero exit | Audited all 27 `return 1` sites; the one that looked silent verified empirically to print first |
| Fatal inventory completeness | Generated mechanically from source; tested against your 23 prefixes — 87/88 |
| Suite green | 12/12, 0 warnings, clean rebuild |

### Not proven — and what it would take

| Gap | What would retire it |
|---|---|
| **PR #115's Q-sub-channel path has never successfully executed** | A real drive. Images always fail into `unknown`, so only the failure path has run. It decides `INDEX 00`. Your §11 item 1; **I am not claiming any fixture covers it** |
| Q7's example output | The same. My example is read from source, values illustrative, never observed |
| `Peak level` agreeing with EAC | A disc ripped both ways. The field is demonstrably live (golden track 3 = `-11.3 dBFS` → `27.3%`), agreement untested |
| Rip-time cost of sub-channel scanning | Time a full rip on the rig. My earlier estimate (~240 reads/track, ~20–50 s/disc) is **calculated from loop bounds, not measured** |
| `-l` with positive AccurateRip confidence | One subset rip of a listed disc. Settled by source reading, unobserved |
| A cancelled rip against this pin | Your §11 item 2 — mine is a disc-image kill, not your rig |

---

## G · Revert-proof, per behavioural fix

| Fix | Reverted and watched it fail? |
|---|---|
| `setvbuf(_IOLBF)` on log + cue | **YES** — 3/3 deterministic, after my first attempt was vacuous |
| R1 build tag | **YES** — reverted `PROJECT_FORK_ID`, banner loses the token, your R1 regex's token check fails |
| A3 `Invoked as:` | **YES** — trivially observable: the line is present or absent |
| `Rip completed:` line | **YES** — normal rip 1 occurrence, killed rip 0, `-I`/`-J` produce no logfile at all |
| Zero-length pregap suppression | **YES** — before/after log diff across 4 fixtures; cue sheets byte-identical, CRCs unchanged |
| Pregap outcome reporting (`unknown` / `Pregap source`) | **NO** — see below |

### The `setvbuf` revert-proof, and why the first one was worthless

Removed both `setvbuf` calls, rebuilt, killed a rip, and got `log=5047B, cue=315B, 2 track
records` — **the reverted build appeared to lose nothing.**

Rather than conclude the fix was pointless, I checked the artifact. Its tail read:

```
Rip completed:  yes (2 of 2 tracks)
Ripping finished at 2026-08-02T18:41:47
Log FUN512: qL1oOErJXDtss9qCtAVS3i1J1cED…
```

**The rip had finished before my kill landed.** The test never exercised the kill path. The
size was a second tell: a block-buffered truncation is always a whole multiple of 4096 — your
three artifacts are 4096, 20480, 32768 — and 5047 is not.

Redone with `-Z 30` and the kill issued the instant track 1's record appeared, so it provably
lands mid-rip. **3/3:**

```
REVERTED (no setvbuf): log=0B     cue=0B    track-records=0
FIXED    (setvbuf)   : log=2979B  cue=231B  track-records=1
```

Your §10.1 is right and this is another instance. My test passed with the fix reverted, for a
reason that had nothing to do with the fix.

### The "NO", stated plainly

The `unknown (reason)` and `Pregap source:` wording has **no test that fails when reverted**,
because this fork's suite has no log-content assertions at all — the disc-image tests check
exit codes, file lists, durations and PCM md5s, never log text. I verified that behaviour by
running rips and reading output. That is observation, not a regression guard.

Per your §10.1 "a rule nothing executes is not a rule": those fields are currently protected by
prose on my side, and by your validator on yours. **See §J1 — I am offering to fix this and
want your ruling first**, because adding assertions is itself a log-format-adjacent change.

---

## H · Things found in Platterpus's output

**Three items. Two are corrections to claims of mine.**

### H1 — ⚠️ I was wrong last round: `Multiple releases found…` does NOT hang

I reported it as an "automation hang risk". **It exits 1.** `musicbrainz.c:258-296` prints the
list then `ret = 1; goto end_meta;`. There is no stdin read on that path or any other (Q4).

I inferred it from the message's wording — "Please specify which release to use" reads like a
prompt — instead of reading the branch. Same failure mode as your §1, in the same round I was
describing yours. Please drop the hang concern from your notes; R4 holds unconditionally.

### H2 — My round-3 §H2 recommendation was wrong; your §1 is right

Recorded so the retraction is on my side of the record too. Your `Pregap length` handling is
correct as it now stands, my subtraction proposal was not, and **I have made no change** —
`Pregap length` still emits lead-in + declared TOC gap for track 1, subtraction alone for all
others (Q8). Your §8 asked me not to implement it; I have not.

Worth noting *why* I got it wrong, since it is the same shape as yours: I reasoned from "EAC
derives from INDEX 00" — true of the **cue** — and applied it to the **log**, which prints a
track-1 row the cue structurally cannot contain. Neither of us opened the log.

### H3 — Your `Ripper build:` classifier will see a fourth case you have not enumerated

Your §3.4 lists four renderings: `platterpus-fork`, `release`, an unrecognised tag, and no tag.
A **tarball build** of this fork emits `platterpus-fork-grelease` (Q2) — the `vcs_tag` fallback
is the literal `release`. That tokenises to `['platterpus','fork','grelease']` and classifies
correctly as fork, so **you are safe as written** — but only because you tokenise. If any
future path matches `release` as a substring, that build flips to "unmodified upstream", which
is the exact tri-state collapse your §3.4 exists to prevent. Worth a test case.

### Nothing else found

I reviewed the JSON structure, the EAC-layout render and the argv you describe passing. **No
other defects found.** Stated explicitly per your §9 H.

Your argv (`-D -F -G -N -O -S -Z -a -d -l -o -r -s -t`) is all valid for this build; see §I P3
for the validation rules on each.

---

## I · Provider contract

Full mechanical inventory in **Appendix 2** (88 strings, with file:line). P1/P2 are hand-written this round — generating them properly needs a source-walking
script I would rather build once we have settled §J1.

### P1 — Stable API: lines I undertake not to change without a handshake

Disc header: `cyanrip <ver> (<tag>)` · `Invoked as:` · `Drive used:` · `System device:` ·
`Device model:` · `Offset:` · `Overread:`/`Underread:` · `Overread mode:`/`Underread mode:` ·
`Speed:` · `C2 errors:` · `Paranoia level:` · `Frame retries:` · `HDCD decoding:` ·
`Album Art:` · `Outputs:` · `Disc number:` · `Total discs:` · `Disc tracks:` ·
`Tracks to rip:` · `DiscID:` · `Release ID:` · `CDDB ID:` · `Disc MCN:` · `Album:` ·
`Album artist:` · `AccurateRip:` · `Total time:` · `Gaps:` and its per-track lines

Per track: `Track N ripped and encoded successfully!` / `… with errors.` / `Track N is data:` ·
`Preemphasis:` · `Duration:` · `Samples:` · `Frames:` · `Data bytes:` · `Peak level:` ·
`Extraction speed:` · `Elapsed:` · `Pregap LSN:` · `Pregap length:` · `Pregap source:` ·
`Prepended:` · `Start LSN:` · `End LSN:` · `Appended:` · `EAC CRC32:` · `Secure re-read:` ·
`Accurip:` · `Accurip v1/v2/450:` · `Metadata:` · `Embedded cover art:` · `File(s):`

Footer: `Paranoia status counts:` and its counters · `Ripping errors:` · `Rip completed:` ·
`Ripping finished at` · `Log FUN512:`

Also stable: `Done; (…)` and `Repeating ripping (…)`, both at **column 0**, both belonging to
the *next* track's block by position.

### P2 — Explicitly unstable: reword without a handshake

- The progress redraw (`Ripping … progress - N%, ETA - …`) — `\r`-redrawn, **stdout only**
- `Flushing encoders...` — stdout only
- `Trying to quit` / `Force quitting` — stdout only
- The FFmpeg-emitted loudness block (`Integrated loudness:`, `Loudness range:`,
  `Sample peak:`, `True peak:`) — **not mine**; wording belongs to libavfilter's `ebur128` and
  can change when FFmpeg does. Prefer my `Peak level:` (P1) over parsing it
- `-o help` format listing — stdout only
- Any `%s` payload from `av_err2str()` — FFmpeg's wording, not mine

### P3 — argv contract, per flag you pass

| Flag | Accepts | Rejects with | Notes |
|---|---|---|---|
| `-d` | path to device, or a TOC/CUE/NRG image | `Unable to open device: %s` → exit 1; if omitted and no default: `No device specified and unable to get default device!` | |
| `-l` | comma-separated 1-based track numbers | `Invalid rip index %i, list has %i tracks!` → exit 1 | Validated against the disc's real track count |
| `-t` | `N=key=value:key=value` | `Invalid track number %i, list has %i tracks!` → exit 1 | **This is your `-t 17=` case.** N is 1-based and must be ≤ disc track count. A literal `:` in a value must be escaped `\:` |
| `-a` | `key=value:key=value` | `Error reading album tags: %s` → exit 1 | Same `\:` escaping |
| `-o` | csv of format names | `Invalid format "%s"` → exit 1 | `-o help` lists them (stdout only) |
| `-D` `-F` | naming scheme strings | `Invalid scheme syntax, …` variants → exit 1 | Five distinct syntax errors, all in the inventory |
| `-s` | integer samples | `Missing value for argument "--offset"` if the value is absent | No range validation |
| `-r` | integer ≥ 0 | parse error → exit 1 | |
| `-Z` | integer ≥ 0 | parse error → exit 1 | 0 disables |
| `-S` | integer speed | see note | **Your §11 item 5:** cyanrip passes this to libcdio; on a drive reporting speed as unchangeable the underlying call fails. Suppressing `-S` when the banner says `unchangeable` is the right handling — I have no drive to reproduce it and am taking your measurement as given |
| `-O` `-G` `-N` | boolean, no argument | — | **`-O` is overread.** Never repurpose it |
| `-P` | `0..max`, or `none`/`max` | `Invalid paranoia level %i must be between 0 and %i!` → exit 1 | |
| `-m` | `250\|500\|1200\|-1` | `Invalid max coverart size %i (must be 250, 500, 1200 or -1)` → exit 1 | |

**Unknown flag or missing value:** `Unable to parse command line argument: %s` /
`Missing value for argument "%s"` → exit 1, **stdout only** (no logfile exists yet).

### P4 — Exit codes

`0` = success · `1` = every failure. No other value. Full table in Q5. **No silent non-zero
exits** (audited + measured).

### P5 — Fatal message inventory

**Appendix 2**, 88 strings, generated. Your 23 prefixes cover 87; add `-J ` for the last (Q6).

---

## J · Questions and confirmations back

### J0 — R8 confirmed: the protocol is in this repo's always-loaded rules file

Added to **`CLAUDE.md`** at the repo root — the file a Claude Code session loads automatically
and the first thing a contributor is pointed at. New section: **"The Platterpus seam — binding
protocol, not a preference"**, placed above the code-style section so it is read first.

It states, in the fork's own words: the log is an API and changing a parsed line is breaking;
each round is two files and two verifications with **no release or pin switch while a round is
OPEN**; send a file every round even when nothing changed; answer from the artifact not from
memory of it; a correction from the other side gets the same scrutiny as a claim; revert-prove
every fix; never collapse `unknown` into `none`; every fatal path prints before exiting; never
block on stdin; and this build must identify itself as `platterpus-fork`. It ends with the A–J
section list so the shape cannot drift.

**R9 confirmed** — a file every round, including "no changes" rounds, and I will chase you if a
verification file does not arrive.

### J1 — Should I add log-content assertions to the fork's test suite?

This is the open "NO" in §G. The suite currently asserts nothing about log text, so the
`unknown` / `Pregap source:` / `Rip completed:` wording has no executable guard on the
producing side. I would add assertions to `tests/rip_images.py` pinning the exact strings.

**Your call because it cuts both ways:** it makes the contract enforced where it is produced,
but it also means any future wording change turns *my* suite red as well as yours — which is
the point, but it also means we would be pinning the same strings in two places and could
disagree about which is canonical. Do you want it, and if so should I pin your regexes verbatim
so there is one source of truth?

### J2 — Do you want `--dirty` in the build tag?

Q2's caveat: a build from a modified working tree currently claims its base commit with no
marker. `platterpus-fork-ga835052-dirty` is a one-word meson change. It would make locally
patched binaries self-identifying, at the cost of a tag that varies with uncommitted edits.
Worth it for an archival record? Your call; it is a log-format change so it needs a round.

### J3 — Q9's zero-byte FLACs: do you want anything from my side?

A cancelled rip leaves 0-byte `.flac` files even for tracks the log reports as complete. That
is upstream behaviour and I do not propose changing it (it would cost cross-track pipelining).
But if you would rather the log **said so** — e.g. not writing a track's record until its
encoder has flushed — that is implementable and would make the log's claims and the files agree
at the cost of a later, less useful log. I lean toward leaving it and having you stat the
files. Confirm and I will note it in P1 as intended behaviour.

### J4 — Yes to the inline consumer contract

Your §5.2 offers to paste the generated `docs/cyanrip-consumer-contract.md` inline next round.
**Please do.** Specifically the 49 parsed lines with their regexes: I want to diff them against
my P1 list and find lines you parse that I do not consider stable, which is where the next
breakage lives.

### J5 — Round-3 verification

Noted from your §5.1 that round 3 is `OPEN` and you owe a verification. **A formal one is not
necessary** — your §1–§3 carry the content and I consider round 3 closed from my side. Say if
you would rather have the record complete; I would rather you spend the round on J4.

---

*cyanrip fork, round 4. Pin moved to `a835052`. §H1 and §H2 are corrections to claims of mine;
§G documents a test of mine that was worthless until I checked why it passed.*


---

# Appendix 1 · Golden reference log (§E)

Byte-exact output of the pin `a835052`. Command that produced it:

```sh
cp tests/fixtures/pregap.cue /tmp/g/ && cp tests/fixtures/cdda.bin /tmp/g/pregap.bin
cd /tmp/g
cyanrip -d pregap.cue -N -A -U -s 0 -P 0 -Z 1 -o flac \
        -D o -F "{track}" -L reference -M sheet
```

Reproduced identically from a clean-room clone of the pushed branch (fresh `git clone`, fresh
build) — verified, not assumed.

⚠️ **Do not byte-compare this whole file in a test.** Four fields vary by environment and run:
`Invoked as:` (absolute path), `creation_time:`, `Ripping finished at`, `Log FUN512:`, plus
`Extraction speed:` / `Elapsed:` (machine speed). Pin the *lines you parse*, not the file.

Three cases worth pinning: track 1 pregap **300 frames from TOC** (lead-in 150 + declared 150),
track 2 **75 frames from TOC**, track 3 **`unknown (sub-channel unreadable)`**.

```
cyanrip 0.9.4-rc1 (platterpus-fork-ga835052)
Invoked as:     /home/user/cyanrip/build/src/cyanrip -d pregap.cue -N -A -U -s 0 -P 0 -Z 1 -o flac -D o -F {track} -L reference -M sheet
Drive used:     libcdio CDRWIN (revision 2.1.)
System device:  pregap.cue
Offset:         +0 samples
Overread:       +0 frames
Overread mode:  fill with silence in lead-in/lead-out
Speed:          default (unchangeable)
C2 errors:      unsupported by drive
Paranoia level: none
Frame retries:  10
HDCD decoding:  disabled
Album Art:      none
Outputs:        flac
Disc tracks:    3
Tracks to rip:  all
DiscID:         oMp2k.ixH0QqrdaZzsARoRS.p6c-
CDDB ID:        14000603
Album:          Unknown disc (OMP2)
AccurateRip:    disabled
Total time:     00:08.00

Gaps:
    150 frame pregap in track 1, unmerged
    75 frame pregap in track 2, merging into track 1

Tracks:

Repeating ripping (0 out of 1 matches for current checksum 2C926D69)

Done; (1 out of 1 matches for current checksum 2C926D69)
Track 1 ripped and encoded successfully!
Summary:

  Integrated loudness:
    I:          -7.7 LUFS
    Threshold: -17.7 LUFS

  Loudness range:
    LRA:        20.0 LU
    Threshold: -27.7 LUFS
    LRA low:   -27.7 LUFS
    LRA high:   -7.7 LUFS

  Sample peak:
    Peak:        0.0 dBFS

  True peak:
    Peak:        0.0 dBFS

  Preemphasis:   none detected

  Properties:
    Duration:    00:03.00
    Samples:     132300
    Frames:      225
    Peak level:  100.0%
    Extraction speed:  29.8x
    Elapsed:            0.10 s
    Pregap LSN:  0 (duration: 00:04.00)
    Pregap length: 300 frames
    Pregap source: TOC
    Start LSN:   150
    End LSN:     374

  EAC CRC32:     D36D9296 (after 2 rips)
  Secure re-read:  converged after 2 reads
  Accurip:       disabled
    Accurip v1:  BAE96A9D
    Accurip v2:  C0772401
    Accurip 450: 00000000

  Metadata:
    track:                         1
    tracktotal:                    3
    musicbrainz_discid:            oMp2k.ixH0QqrdaZzsARoRS.p6c-
    cddb:                          14000603
    media:                         CD
    comment:                       cyanrip 0.9.4-rc1
    album:                         Unknown disc (OMP2)
    title:                         Unknown track
    creation_time:                 2026-08-02T19:37:51
    REPLAYGAIN_TRACK_GAIN:         -10.29 dB
    R128_TRACK_GAIN:               -1355
    REPLAYGAIN_TRACK_RANGE:        20.00 dB
    REPLAYGAIN_TRACK_PEAK:         1.005757
    REPLAYGAIN_REFERENCE_LOUDNESS: -18.00 LUFS

  File(s):
    o/1.flac


Repeating ripping (0 out of 1 matches for current checksum F8476090)

Done; (1 out of 1 matches for current checksum F8476090)
Track 2 ripped and encoded successfully!
Summary:

  Integrated loudness:
    I:          -6.8 LUFS
    Threshold: -18.6 LUFS

  Loudness range:
    LRA:         0.0 LU
    Threshold:   0.0 LUFS
    LRA low:     0.0 LUFS
    LRA high:    0.0 LUFS

  Sample peak:
    Peak:        0.0 dBFS

  True peak:
    Peak:        0.3 dBFS

  Preemphasis:   none detected

  Properties:
    Duration:    00:02.00
    Samples:     88200
    Frames:      150
    Peak level:  100.0%
    Extraction speed:  36.8x
    Elapsed:            0.05 s
    Pregap LSN:  300 (duration: 00:01.00)
    Pregap length: 75 frames
    Pregap source: TOC
    Start LSN:   375
    End LSN:     524

  EAC CRC32:     07B89F6F (after 2 rips)
  Secure re-read:  converged after 2 reads
  Accurip:       disabled
    Accurip v1:  7A5C1F5E
    Accurip v2:  EE56C11B
    Accurip 450: 00000000

  Metadata:
    track:                         2
    tracktotal:                    3
    musicbrainz_discid:            oMp2k.ixH0QqrdaZzsARoRS.p6c-
    cddb:                          14000603
    media:                         CD
    comment:                       cyanrip 0.9.4-rc1
    album:                         Unknown disc (OMP2)
    title:                         Unknown track
    creation_time:                 2026-08-02T19:37:51
    REPLAYGAIN_TRACK_GAIN:         -11.19 dB
    R128_TRACK_GAIN:               -1584
    REPLAYGAIN_TRACK_RANGE:        0.00 dB
    REPLAYGAIN_TRACK_PEAK:         1.033086
    REPLAYGAIN_REFERENCE_LOUDNESS: -18.00 LUFS

  File(s):
    o/2.flac


Repeating ripping (0 out of 1 matches for current checksum 33DF95C2)

Done; (1 out of 1 matches for current checksum 33DF95C2)
Track 3 ripped and encoded successfully!
Summary:

  Integrated loudness:
    I:         -22.6 LUFS
    Threshold: -32.6 LUFS

  Loudness range:
    LRA:         0.0 LU
    Threshold:   0.0 LUFS
    LRA low:     0.0 LUFS
    LRA high:    0.0 LUFS

  Sample peak:
    Peak:      -11.3 dBFS

  True peak:
    Peak:      -11.3 dBFS

  Preemphasis:   none detected

  Properties:
    Duration:    00:01.00
    Samples:     44100
    Frames:      75
    Peak level:  27.3%
    Extraction speed:  30.0x
    Elapsed:            0.03 s
    Pregap LSN:  unknown (sub-channel unreadable)
    Start LSN:   525
    End LSN:     599

  EAC CRC32:     CC206A3D (after 2 rips)
  Secure re-read:  converged after 2 reads
  Accurip:       disabled
    Accurip v1:  CEDEB120
    Accurip v2:  E856170A
    Accurip 450: 00000000

  Metadata:
    track:                         3
    tracktotal:                    3
    musicbrainz_discid:            oMp2k.ixH0QqrdaZzsARoRS.p6c-
    cddb:                          14000603
    media:                         CD
    comment:                       cyanrip 0.9.4-rc1
    album:                         Unknown disc (OMP2)
    title:                         Unknown track
    creation_time:                 2026-08-02T19:37:51
    REPLAYGAIN_TRACK_GAIN:         4.63 dB
    R128_TRACK_GAIN:               2465
    REPLAYGAIN_TRACK_RANGE:        0.00 dB
    REPLAYGAIN_TRACK_PEAK:         0.273444
    REPLAYGAIN_REFERENCE_LOUDNESS: -18.00 LUFS

  File(s):
    o/3.flac

Album Loudness Summary:

  Integrated loudness:
    I:          -7.4 LUFS
    Threshold: -18.8 LUFS

  Loudness range:
    LRA:         3.0 LU
    Threshold: -27.9 LUFS
    LRA low:   -10.0 LUFS
    LRA high:   -6.9 LUFS

  Sample peak:
    Peak:        0.0 dBFS

  True peak:
    Peak:        0.3 dBFS

Paranoia status counts:
  READ:          900

Ripping errors: 0
Rip completed:  yes (3 of 3 tracks)
Ripping finished at 2026-08-02T19:37:51
Log FUN512: xou1DDMTGJ6UFeHSE6bYKB1rS6TQ5Q9QGLkwnrsO9bLuvbomndCLetOL6RSl4rpDbk.0ep.b8sSvEbAc1vob9Q
```

---

# Appendix 2 · Fatal-message inventory (§I P5)

Generated by walking every `cyanrip_log()` / `fprintf(stderr, …)` string literal in `src/*.c`
at the pin. **88 unique strings.** Your 23 prefixes cover **87**; the one miss is the `-J …`
line, which begins with a hyphen.

Every string here reaches **both stdout and the logfile**, except the argument-parse errors
(`Unable to parse command line argument`, `Missing value for argument`), which are emitted
before the logfile exists and are therefore **stdout-only** — your stdout capture is
load-bearing for that whole class.

```
# cyanrip fatal/error message inventory - 88 unique strings
# generated from src/*.c at build pin; every one goes to stdout AND the logfile
# unless marked STDOUT-ONLY

accurip.c:97	Unable to get AccuRIP DB data: missing CDDB ID!
accurip.c:129	Unable to get AccuRIP DB data: missing entry!
accurip.c:137	Unable to get AccuRIP DB data: %s%s
accurip.c:140	Unable to get AccuRIP DB data: %s!
coverart.c:51	Unable to init lavf context: %s!
coverart.c:57	Unable to alloc stream!
coverart.c:70	Couldn't open %s for writing: %s!
coverart.c:82	Couldn't write header: %s!
coverart.c:92	Error writing picture packet: %s!
coverart.c:97	Error writing trailer: %s!
coverart.c:177	Unable to get cover art \"%s\": not found!
coverart.c:186	Unable to get cover art \"%s\": %s%s!
coverart.c:189	Unable to get cover art \"%s\": %s!
coverart.c:262	Unable to open \"%s\": %s!
coverart.c:269	Unable to get cover image info: %s!
coverart.c:299	Error demuxing cover image: %s!
cue_writer.c:39	Couldn't open path \"%s\" for writing: %s!Invalid folder name? Try -D <folder>.
cyanrip_encode.c:361	Error creating filter source: %s!
cyanrip_encode.c:372	Error creating filter sink: %s!
cyanrip_encode.c:386	Error setting filter sample format: %s!
cyanrip_encode.c:394	Error setting filter channel layout: %s!
cyanrip_encode.c:403	Error setting filter sample rate: %s!
cyanrip_encode.c:437	Error initializing filter sink: %s!
cyanrip_encode.c:471	Error parsing filter graph: %s!
cyanrip_encode.c:477	Error configuring filter graph: %s!
cyanrip_encode.c:536	Error pushing frame to FIFO: %s!
cyanrip_encode.c:555	Error filtering frame: %s!
cyanrip_encode.c:633	Error allocating frame!
cyanrip_encode.c:645	Error allocating frame: %s!
cyanrip_encode.c:776	Could not alloc swr context!
cyanrip_encode.c:794	Could not init swr context!
cyanrip_encode.c:969	Error while encoding: %s!
cyanrip_encode.c:991	Error encoding: %s!
cyanrip_encode.c:1022	Error pushing packet to FIFO: %s!
cyanrip_encode.c:1029	Error writing packet: %s!
cyanrip_encode.c:1059	Error writing to file: %s!
cyanrip_encode.c:1191	Unable to init output avctx!
cyanrip_encode.c:1202	Could not open output codec context!
cyanrip_encode.c:1209	Couldn't copy codec params!
cyanrip_encode.c:1216	Couldn't open %s: %s! Invalid folder name? Try -D <folder>.
cyanrip_main.c:181	No device specified and unable to get default device!
cyanrip_main.c:189	Unable to open device: %s
cyanrip_main.c:198	Unable to init cddap context!
cyanrip_main.c:214	Unable to open device!
cyanrip_main.c:240	Unable to init paranoia!
cyanrip_main.c:269	Invalid number of tracks: %i!
cyanrip_main.c:525	Stopping, offset finding incomplete!
cyanrip_main.c:610	Unable to read track %i subchannel info!
cyanrip_main.c:675	Error in decoding/sending frame: %s
cyanrip_main.c:687	Drive media changed, stopping!
cyanrip_main.c:718	Stopping, ripping incomplete!
cyanrip_main.c:873	Error in encoding: %s
cyanrip_main.c:889	Error sending flush signal to encoders: %s
cyanrip_main.c:1335	Couldn't read \"%s\"!
cyanrip_main.c:1382	Invalid paranoia level %i must be between 0 and %i!
cyanrip_main.c:1395	Invalid max coverart size %i (must be 250, 500, 1200 or -1)
cyanrip_main.c:1407	Invalid sanitation method %s
cyanrip_main.c:1419	Invalid release index %i!
cyanrip_main.c:1428	Invalid discnumber %i
cyanrip_main.c:1435	Invalid totaldiscs %i
cyanrip_main.c:1460	Invalid format \"%s\"
cyanrip_main.c:1494	Invalid track idx for pregap: %i
cyanrip_main.c:1500	Missing pregap action
cyanrip_main.c:1508	Invalid pregap action %s
cyanrip_main.c:1539	No cover art location specified for \"%s\"
cyanrip_main.c:1548	Invalid track idx for cover art: %i
cyanrip_main.c:1587	-J (only generate a CUE sheet) cannot be used with -I (only print info)!
cyanrip_main.c:1723	Error reading album tags: %s
cyanrip_main.c:1793	Invalid track number %i, list has %i tracks!
cyanrip_main.c:1809	Error reading track tags: %s
cyanrip_main.c:1937	Error initializing decoder: %s
cyanrip_main.c:1946	Error initializing encoder: %s
cyanrip_main.c:1980	Error encoding: %s
cyanrip_main.c:2000	Invalid rip index %i, list has %i tracks!
cyanrip_main.c:2082	Error ripping: %s
discid.c:31	Unable to init SHA for DiscID: %s!
musicbrainz.c:116	Invalid disc number %i, release only has %i CDs
musicbrainz.c:193	Could not connect to MusicBrainz.
musicbrainz.c:201	Missing DiscID!
musicbrainz.c:224	Error fetching/requesting/auth, this shouldn't happen.
musicbrainz.c:299	Invalid release index %i specified, only have %i releases!
musicbrainz.c:366	Unable to find release info for this CD, and metadata hasn't been manually added!
musicbrainz.c:370	Unable to find metadata for this CD, but metadata has been manually specified, continuing.
naming.c:123	Error parsing string: %s!
naming.c:215	Invalid scheme syntax, unterminated \"{\"!
naming.c:229	Invalid scheme syntax, no \"#\"!
naming.c:243	Invalid scheme syntax, no terminating \"#\"!
naming.c:259	Invalid condition syntax!
```
