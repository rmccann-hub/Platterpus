# cyanrip fork → Platterpus · Round 4 return file · 2026-08-02

> **Self-contained.** This one file carries the round-4 return (§A–J), the regenerated golden
> reference log (**Appendix 1**), and the generated fatal-message inventory (**Appendix 2**).
> Nothing else is needed from the cyanrip side this round.
>
> **The pin moved: `ec406ac` → `a04a94b`.** A stale pin builds the old banner format and will
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
| **Commit SHA** | **`a04a94b84b75ed93324a954e4e94b6a57d83e28a`** |
| Previous pin | `ec406ac…` — **the SHA has changed, do not reuse it** |

**Exact `--version` output, byte-for-byte** (measured, `cat -A` confirms no trailing space):

```
cyanrip 0.9.4-rc1 (platterpus-fork-ga04a94b)
```

Verified against **your own R1 regex** rather than my reading of it:

```
regex match           : True
tag                   : 'platterpus-fork-ga04a94b'
tokens on [-_]        : ['platterpus', 'fork', 'ga04a94b']
contains platterpus+fork : True
is NOT 'release'      : True
```

⚠️ **The `ga04a94b` component changes on every commit.** Assert on the shape and the literal
token `platterpus-fork`, not on the whole string, or your test breaks on my next push.

---

## B · Answers to Q1–Q11

### Q1 — Exact `--version` string · **measured**
`cyanrip 0.9.4-rc1 (platterpus-fork-ga04a94b)` — see A. Identical on the first line of every
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
| Clean tree at `a04a94b` | `platterpus-fork-ga04a94b` |
| **Dirty tree** (uncommitted edits) | `platterpus-fork-ga04a94b` — **identical, no dirty marker** |
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
| `a04a94b` | Tag the build as `platterpus-fork`; echo the invocation into the log | **YES — see D** |

One commit. Also updated `CLAUDE.md` (R8) in the same commit; that is documentation, not output.

---

## D · Log-format delta

**CHANGED.** Two lines at the top of every logfile. Nothing else — no field reordered, no
existing wording altered, no units changed.

**1. Banner reformatted** (R1):

```
-  cyanrip 0.9.4-rc1 (ec406ac, platterpus-fork)
+  cyanrip 0.9.4-rc1 (platterpus-fork-ga04a94b)
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
cyanrip 0.9.4-rc1 (platterpus-fork-ga04a94b)
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
| R1 banner satisfies your rule | Ran your R1 regex against the real `--version` output; match=True, tokens `['platterpus','fork','ga04a94b']`, not `release` |
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

**Now generated, not hand-written** — see **Appendix 2**, produced by
`tools/gen-provider-contract.py` and committed in the fork as `PROVIDER-CONTRACT.md`.

This replaces the hand-written version in my earlier draft, which was incomplete in a way
nothing would have caught: it documented **21 of 37** flags and omitted the log's field order
entirely. Generating it fixes that by construction.

| § | Contents | Derived from |
|---|---|---|
| **P1** | Every command line flag — all **37** | the binary's own `--help` |
| **P2** | Every stable log line — **241** distinct, the API | every `cyanrip_log()` call site |
| **P3** | Every unstable line, and whether it reaches the logfile at all | same, minus an explicit unstable list |
| **P4** | Exit codes, and whether any non-zero exit can be silent | every `exit()` and `return` in `main()` |
| **P5** | Full fatal/error inventory with `file:line` — **88** strings | same walk, prefix-filtered |

`tools/gen-provider-contract.py --check PROVIDER-CONTRACT.md` exits non-zero on drift. **That
checker was itself revert-proved** — I tampered with one row, confirmed it failed, restored,
confirmed it passed. A drift checker that cannot detect drift is the same class of decoration
as a test that passes with the fix reverted.

One design note you may hit in your own generated contract: the file embeds the version banner,
whose `-g<sha>` suffix changes on every commit — so committing the contract invalidated the
contract. The generator now normalises it to `-g<commit>`. **A generated artifact cannot contain
a value that generating it alters.**

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
marker. `platterpus-fork-ga04a94b-dirty` is a one-word meson change. It would make locally
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

*cyanrip fork, round 4. Pin moved to `a04a94b`. §H1 and §H2 are corrections to claims of mine;
§G documents a test of mine that was worthless until I checked why it passed.*



---

# Appendix 1 · Golden reference log (§E)

Byte-exact output of the pin `a04a94b`. Command that produced it:

```sh
cp tests/fixtures/pregap.cue /tmp/g/ && cp tests/fixtures/cdda.bin /tmp/g/pregap.bin
cd /tmp/g
cyanrip -d pregap.cue -N -A -U -s 0 -P 0 -Z 1 -o flac \
        -D o -F "{track}" -L reference -M sheet
```

⚠️ **Do not byte-compare this whole file in a test.** Six fields vary by environment and run:
`Invoked as:` (absolute path), `creation_time:`, `Ripping finished at`, `Log FUN512:`,
`Extraction speed:` and `Elapsed:`. Pin the *lines you parse*, not the file.

Three cases worth pinning: track 1 pregap **300 frames from TOC** (lead-in 150 + declared 150),
track 2 **75 frames from TOC**, track 3 **`unknown (sub-channel unreadable)`**.

```
cyanrip 0.9.4-rc1 (platterpus-fork-ga04a94b)
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
    Extraction speed:  66.6x
    Elapsed:            0.05 s
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
    creation_time:                 2026-08-02T20:21:24
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
    Extraction speed:  57.8x
    Elapsed:            0.03 s
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
    creation_time:                 2026-08-02T20:21:24
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
    Extraction speed:  58.2x
    Elapsed:            0.02 s
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
    creation_time:                 2026-08-02T20:21:24
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
Ripping finished at 2026-08-02T20:21:24
Log FUN512: UOMSlY4tDEh3xeLZ_yqs4ivSCbnnCXJ3_u78VgijJJFcF7FyEzoS_k.QnhXok.u08R16Hlq2xmo2lUjUCnYMTQ
```

---

# Appendix 2 · Provider contract (§I) — generated

Committed in the fork as `PROVIDER-CONTRACT.md`. Regenerate with
`tools/gen-provider-contract.py`; verify with `tools/gen-provider-contract.py --check`.
Includes **P5**, the full fatal-message inventory, so no separate inventory file is needed.

# cyanrip provider contract

**Generated** by `tools/gen-provider-contract.py` from the source tree and the
built binary. Do not edit by hand -- regenerate. A hand-written contract goes
stale silently, which is the failure this file exists to prevent.

Build: `cyanrip 0.9.4-rc1 (platterpus-fork-g<commit>)`

This is the provider half of the seam. Platterpus generates the consumer half
(`docs/cyanrip-consumer-contract.md`) from its parser tables. Neither side
describes behaviour it does not have.

## P1 - Inputs: every command line flag

From the binary's own `--help`, so it cannot drift from what the build accepts.


### General

| Short | Long | Meaning |
|---|---|---|
| `-h` | `--help` | Print this text |
| `-v` | `--version` | Print the version number |

### Ripping options

| Short | Long | Meaning |
|---|---|---|
| `-d` | `--device` | Set device path (can be a TOC file) |
| `-s` | `--offset` | CD drive offset in samples (default: 0) |
| `-r` | `--retries` | Maximum number of retries for frames and repeated rips (default: 10) |
| `-Z` | `--repeat-rips` | Rip tracks until checksums match N times (for damaged CDs) (default: 0) |
| `-S` | `--speed` | Set drive speed (default: 0) |
| `-p` | `--pregap` | Track pregap handling: N=default|drop|merge|track (repeatable) |
| `-P` | `--paranoia` | Paranoia level (0..max, or 'none'/'max') |
| `-O` | `--overread` | Enable overreading into lead-in and lead-out (default: false) |
| `-H` | `--hdcd` | Enable HDCD decoding (default: false) |
| `-E` | `--force-deemphasis` | Force CD deemphasis (default: false) |
| `-W` | `--no-deemphasis` | Disable automatic CD deemphasis (default: false) |
| `-K` | `--no-replaygain` | Disable ReplayGain tagging (default: false) |

### Output options

| Short | Long | Meaning |
|---|---|---|
| `-o` | `--outputs` | Comma separated list of output formats ('help' lists all) |
| `-b` | `--bitrate` | Bitrate of lossy files in kbps (default: 256.000000) |
| `-D` | `--folder-scheme` | Directory naming scheme (default: {album}{if #releasecomment# > #0# (|releasecomment|)} [{format}]) |
| `-F` | `--track-scheme` | Track naming scheme (default: {if #totaldiscs# > #1#|disc|.}{track} - {title}) |
| `-L` | `--log-scheme` | Log file name scheme (default: {album}{if #totaldiscs# > #1# CD|disc|}) |
| `-M` | `--cue-scheme` | CUE file name scheme (default: {album}{if #totaldiscs# > #1# CD|disc|}) |
| `-l` | `--tracks` | Comma separated list of tracks to rip (default: all) |
| `-T` | `--sanitize` | Filename sanitation: simple, os_simple, unicode, os_unicode |

### Metadata options

| Short | Long | Meaning |
|---|---|---|
| `-I` | `--info` | Only print CD and track info (default: false) |
| `-J` | `--cue-only` | Only generate and print a CUE sheet, don't rip (default: false) |
| `-a` | `--album-meta` | Album metadata, key=value:key=value |
| `-t` | `--track-meta` | Track metadata as N=key=value:key=value (repeatable) |
| `-R` | `--release` | MusicBrainz release: 1-based index or ID string |
| `-c` | `--disc` | Multi-disc tag: disc/totaldiscs |
| `-C` | `--cover` | Cover art: title=path (or N=path per-track, repeatable) |
| `-N` | `--no-musicbrainz` | Disable MusicBrainz lookup (default: false) |
| `-A` | `--no-accurip` | Disable AccurateRip database query and validation (default: false) |
| `-U` | `--no-coverart-db` | Disable Cover art DB query and retrieval (default: false) |
| `-m` | `--cover-size` | Cover art max size: 250, 500, 1200, or -1 for original (default: -1) |
| `-G` | `--no-coverart-embed` | Disable embedding of cover art images (default: false) |

### Misc. options

| Short | Long | Meaning |
|---|---|---|
| `-Q` | `--eject` | Eject tray once successfully done (default: false) |
| `-f` | `--find-offset` | Find drive offset (requires a disc with an AccuRip entry) (default: false) |
| `-Y` | `--verify-log` | Verify a rip log's FUN512 checksum |

**37 flags total.** Notes that are not derivable from `--help`:

- `-O` is **overread**, not an options passthrough. Never repurpose it.
- `-v` is version; there is no `-V`.
- `-J` and `-I` are mutually exclusive; combining them exits 1.
- `-d` accepts a device path **or** a TOC/CUE/NRG image file.
- `-a`/`-t` values are `:`-separated; a literal colon must be escaped `\:`.
- `-t N=` and `-l N` are 1-based and validated against the disc's real track
  count; out of range exits 1 with a message naming both numbers.
- Multiple `-o` formats produce **one logfile and one cue per format**.

## P2 - Outputs: stable log lines (the API)

Every line below reaches **both stdout and the logfile**. Changing the text,
indentation, field order or units of any of them is a breaking change and
requires a handshake round.

| File:line | Line |
|---|---|
| `accurip.c:97` | `Unable to get AccuRIP DB data: missing CDDB ID!` |
| `accurip.c:129` | `Unable to get AccuRIP DB data: missing entry!` |
| `accurip.c:137` | `Unable to get AccuRIP DB data: %s%s` |
| `accurip.c:140` | `Unable to get AccuRIP DB data: %s!` |
| `accurip.c:176` | `AccuRIP DB data error, got unexpected number of bytes!` |
| `coverart.c:34` | `Cover art has no packet!` |
| `coverart.c:51` | `Unable to init lavf context: %s!` |
| `coverart.c:57` | `Unable to alloc stream!` |
| `coverart.c:70` | `Couldn't open %s for writing: %s!` |
| `coverart.c:82` | `Couldn't write header: %s!` |
| `coverart.c:92` | `Error writing picture packet: %s!` |
| `coverart.c:97` | `Error writing trailer: %s!` |
| `coverart.c:169` | `Downloading %s cover art...` |
| `coverart.c:177` | `Unable to get cover art \"%s\": not found!` |
| `coverart.c:186` | `Unable to get cover art \"%s\": %s%s!` |
| `coverart.c:189` | `Unable to get cover art \"%s\": %s!` |
| `coverart.c:262` | `Unable to open \"%s\": %s!` |
| `coverart.c:269` | `Unable to get cover image info: %s!` |
| `coverart.c:299` | `Error demuxing cover image: %s!` |
| `coverart.c:360` | `Release ID unavailable, cannot search Cover Art DB!` |
| `cue_writer.c:39` | `Couldn't open path \"%s\" for writing: %s!Invalid folder name? Try -D <folder>.` |
| `cyanrip_encode.c:361` | `Error creating filter source: %s!` |
| `cyanrip_encode.c:372` | `Error creating filter sink: %s!` |
| `cyanrip_encode.c:386` | `Error setting filter sample format: %s!` |
| `cyanrip_encode.c:394` | `Error setting filter channel layout: %s!` |
| `cyanrip_encode.c:403` | `Error setting filter sample rate: %s!` |
| `cyanrip_encode.c:437` | `Error initializing filter sink: %s!` |
| `cyanrip_encode.c:471` | `Error parsing filter graph: %s!` |
| `cyanrip_encode.c:477` | `Error configuring filter graph: %s!` |
| `cyanrip_encode.c:536` | `Error pushing frame to FIFO: %s!` |
| `cyanrip_encode.c:555` | `Error filtering frame: %s!` |
| `cyanrip_encode.c:633` | `Error allocating frame!` |
| `cyanrip_encode.c:645` | `Error allocating frame: %s!` |
| `cyanrip_encode.c:757` | `Album Loudness` |
| `cyanrip_encode.c:776` | `Could not alloc swr context!` |
| `cyanrip_encode.c:794` | `Could not init swr context!` |
| `cyanrip_encode.c:969` | `Error while encoding: %s!` |
| `cyanrip_encode.c:991` | `Error encoding: %s!` |
| `cyanrip_encode.c:1022` | `Error pushing packet to FIFO: %s!` |
| `cyanrip_encode.c:1029` | `Error writing packet: %s!` |
| `cyanrip_encode.c:1059` | `Error writing to file: %s!` |
| `cyanrip_encode.c:1182` | `Codec not found (not compiled in lavc?)!` |
| `cyanrip_encode.c:1191` | `Unable to init output avctx!` |
| `cyanrip_encode.c:1202` | `Could not open output codec context!` |
| `cyanrip_encode.c:1209` | `Couldn't copy codec params!` |
| `cyanrip_encode.c:1216` | `Couldn't open %s: %s! Invalid folder name? Try -D <folder>.` |
| `cyanrip_log.c:50` | `Pregap LSN:  %i (duration: %s)` |
| `cyanrip_log.c:52` | `Pregap length: %i frames` |
| `cyanrip_log.c:54` | `Pregap LSN:  unknown (sub-channel unreadable)` |
| `cyanrip_log.c:56` | `Pregap LSN:  unknown (sub-channel CRC mismatches)` |
| `cyanrip_log.c:58` | `Pregap LSN:  none` |
| `cyanrip_log.c:64` | `Pregap source: sub-channel (not signalled by TOC)` |
| `cyanrip_log.c:66` | `Pregap source: lead-in` |
| `cyanrip_log.c:68` | `Pregap source: TOC` |
| `cyanrip_log.c:71` | `Prepended:   %i frames of silence` |
| `cyanrip_log.c:72` | `Start LSN:   %i` |
| `cyanrip_log.c:74` | `(with offset: %i)` |
| `cyanrip_log.c:78` | `End LSN:     %i` |
| `cyanrip_log.c:85` | `Appended:    %i frames of silence` |
| `cyanrip_log.c:93` | `Preemphasis:` |
| `cyanrip_log.c:95` | `none detected` |
| `cyanrip_log.c:98` | `(deemphasis forced)` |
| `cyanrip_log.c:103` | `present (subcode)` |
| `cyanrip_log.c:105` | `present (TOC)` |
| `cyanrip_log.c:108` | `(deemphasis applied)` |
| `cyanrip_log.c:113` | `Properties:` |
| `cyanrip_log.c:116` | `Data bytes:  %i (%.2f Mib)` |
| `cyanrip_log.c:119` | `Frames:      %u` |
| `cyanrip_log.c:125` | `Duration:    %s` |
| `cyanrip_log.c:126` | `Samples:     %u` |
| `cyanrip_log.c:129` | `Peak level:  %.1f%%` |
| `cyanrip_log.c:131` | `Extraction speed:  %.1fx` |
| `cyanrip_log.c:133` | `Elapsed:            %.2f s` |
| `cyanrip_log.c:141` | `EAC CRC32:     %08X` |
| `cyanrip_log.c:143` | `(after %i rips)` |
| `cyanrip_log.c:150` | `Secure re-read:  converged after %i reads` |
| `cyanrip_log.c:153` | `Secure re-read:  did NOT converge after %i reads (repeat limit hit)` |
| `cyanrip_log.c:158` | `Secure re-read:  not attempted` |
| `cyanrip_log.c:162` | `Accurip:       %s` |
| `cyanrip_log.c:166` | `(max confidence: %i)` |
| `cyanrip_log.c:174` | `Accurip v1:  %08X` |
| `cyanrip_log.c:176` | `(accurately ripped, confidence %i)` |
| `cyanrip_log.c:178` | `(not found, either a new pressing, or bad rip)` |
| `cyanrip_log.c:182` | `Accurip v2:  %08X` |
| `cyanrip_log.c:193` | `Accurip 450: %08X` |
| `cyanrip_log.c:195` | `(match found, confidence %i, but a checksum of 0 is meaningless)` |
| `cyanrip_log.c:198` | `(matches Accurip DB, confidence %i, track is partially accurately ripped)` |
| `cyanrip_log.c:201` | `(not found)` |
| `cyanrip_log.c:208` | `Metadata:` |
| `cyanrip_log.c:218` | `%s:` |
| `cyanrip_log.c:221` | `%s` |
| `cyanrip_log.c:244` | `Embedded cover art:    %s: %s` |
| `cyanrip_log.c:247` | `Embedded cover art:    %s: %ix%i %s` |
| `cyanrip_log.c:251` | `File(s):` |
| `cyanrip_log.c:265` | `cyanrip %s (%s-g%s)` |
| `cyanrip_log.c:268` | `Invoked as:     %s` |
| `cyanrip_log.c:272` | `Drive used:     error retrieving drive info` |
| `cyanrip_log.c:274` | `Drive used:     %s %s (revision %s)` |
| `cyanrip_log.c:275` | `System device:  %s` |
| `cyanrip_log.c:277` | `Device model:   %s` |
| `cyanrip_log.c:278` | `Offset:         %c%i %s` |
| `cyanrip_log.c:280` | `%s%c%i %s` |
| `cyanrip_log.c:285` | `%s%s` |
| `cyanrip_log.c:289` | `Speed:          %ix` |
| `cyanrip_log.c:291` | `Speed:          default (%s)` |
| `cyanrip_log.c:293` | `C2 errors:      %s` |
| `cyanrip_log.c:296` | `Paranoia level: %s` |
| `cyanrip_log.c:300` | `Paranoia level: %i` |
| `cyanrip_log.c:301` | `Frame retries:  %i` |
| `cyanrip_log.c:302` | `HDCD decoding:  %s` |
| `cyanrip_log.c:304` | `Album Art:      %s` |
| `cyanrip_log.c:308` | `%s%s%s%s%s` |
| `cyanrip_log.c:316` | `Outputs:` |
| `cyanrip_log.c:322` | `Disc tracks:    %i` |
| `cyanrip_log.c:323` | `Tracks to rip:  %s` |
| `cyanrip_log.c:326` | `%i%s` |
| `cyanrip_log.c:340` | `AccurateRip:    %s` |
| `cyanrip_log.c:346` | `Total time:     %s` |
| `cyanrip_log.c:372` | `Tracks ripped accurately: %i/%i` |
| `cyanrip_log.c:374` | `Tracks ripped partially accurately: %i/%i` |
| `cyanrip_log.c:380` | `Paranoia status counts:` |
| `cyanrip_log.c:389` | `%lu` |
| `cyanrip_log.c:413` | `Ripping errors: %i` |
| `cyanrip_log.c:420` | `Rip completed:  no (interrupted by user, %i of %i tracks)` |
| `cyanrip_log.c:423` | `Rip completed:  yes (%i of %i tracks)` |
| `cyanrip_log.c:426` | `Ripping finished at %s` |
| `cyanrip_main.c:181` | `No device specified and unable to get default device!` |
| `cyanrip_main.c:189` | `Unable to open device: %s` |
| `cyanrip_main.c:198` | `Unable to init cddap context!` |
| `cyanrip_main.c:200` | `cdio: \"%s\"` |
| `cyanrip_main.c:211` | `Opening drive...` |
| `cyanrip_main.c:214` | `Unable to open device!` |
| `cyanrip_main.c:223` | `Device does not support changing speeds!` |
| `cyanrip_main.c:231` | `cdio error: %s` |
| `cyanrip_main.c:240` | `Unable to init paranoia!` |
| `cyanrip_main.c:269` | `Invalid number of tracks: %i!` |
| `cyanrip_main.c:292` | `CDIO returned invalid track %i end LSN` |
| `cyanrip_main.c:441` | `Frame read failed!` |
| `cyanrip_main.c:518` | `Loading data for track %i...` |
| `cyanrip_main.c:525` | `Stopping, offset finding incomplete!` |
| `cyanrip_main.c:533` | `Data loaded, searching for offsets...` |
| `cyanrip_main.c:542` | `Nothing found for track %i%s` |
| `cyanrip_main.c:547` | `Offset of %c%i found in track %i%s` |
| `cyanrip_main.c:552` | `Offset of %c%i confirmed (confidence: %i) in track %i%s` |
| `cyanrip_main.c:556` | `New offset of %c%i found at track %i, scrapping old offset of %c%i%s` |
| `cyanrip_main.c:570` | `No track had AccuRip entry, cannot find offset!` |
| `cyanrip_main.c:572` | `No track was long enough, unable to find drive offset!` |
| `cyanrip_main.c:574` | `Was not able to find drive offset with a radius of %i frames, trying again with a larger radius...` |
| `cyanrip_main.c:580` | `Drive offset of %c%i found (confidence: %i)!` |
| `cyanrip_main.c:610` | `Unable to read track %i subchannel info!` |
| `cyanrip_main.c:626` | `Track %i is data:` |
| `cyanrip_main.c:675` | `Error in decoding/sending frame: %s` |
| `cyanrip_main.c:687` | `Drive media changed, stopping!` |
| `cyanrip_main.c:718` | `Stopping, ripping incomplete!` |
| `cyanrip_main.c:836` | `Done; (%i out of %i matches for current checksum %08X)` |
| `cyanrip_main.c:842` | `Done; (no matches found, but hit repeat limit of %i)` |
| `cyanrip_main.c:858` | `Repeating ripping (%i out of %i matches for current checksum %08X)` |
| `cyanrip_main.c:873` | `Error in encoding: %s` |
| `cyanrip_main.c:889` | `Error sending flush signal to encoders: %s` |
| `cyanrip_main.c:896` | `Track %i ripped and encoded with errors.` |
| `cyanrip_main.c:898` | `Track %i ripped and encoded successfully!` |
| `cyanrip_main.c:978` | `Gaps:` |
| `cyanrip_main.c:983` | `%i frame gap between lead-in and track 1 pregap, merging into pregap` |
| `cyanrip_main.c:990` | `%i frame unmarked gap between lead-in and track 1, marking as a pregap` |
| `cyanrip_main.c:1012` | `%i frame pregap in track %i,` |
| `cyanrip_main.c:1019` | `unmerged` |
| `cyanrip_main.c:1021` | `merging into track %i` |
| `cyanrip_main.c:1027` | `dropping` |
| `cyanrip_main.c:1033` | `merging` |
| `cyanrip_main.c:1040` | `splitting off into a new track, number %i` |
| `cyanrip_main.c:1081` | `%i frame discontinuity between tracks %i and %i,` |
| `cyanrip_main.c:1086` | `padding track %i` |
| `cyanrip_main.c:1089` | `ignoring` |
| `cyanrip_main.c:1097` | `%i frame gap between last track and lead-out, padding track` |
| `cyanrip_main.c:1162` | `Can't init signal handler!` |
| `cyanrip_main.c:1382` | `Invalid paranoia level %i must be between 0 and %i!` |
| `cyanrip_main.c:1395` | `Invalid max coverart size %i (must be 250, 500, 1200 or -1)` |
| `cyanrip_main.c:1407` | `Invalid sanitation method %s` |
| `cyanrip_main.c:1419` | `Invalid release index %i!` |
| `cyanrip_main.c:1428` | `Invalid discnumber %i` |
| `cyanrip_main.c:1435` | `Invalid totaldiscs %i` |
| `cyanrip_main.c:1439` | `discnumber %i is larger than totaldiscs %i` |
| `cyanrip_main.c:1452` | `Supported output codecs:` |
| `cyanrip_main.c:1460` | `Invalid format \"%s\"` |
| `cyanrip_main.c:1465` | `Duplicated format \"%s\"` |
| `cyanrip_main.c:1480` | `Duplicated rip idx %i` |
| `cyanrip_main.c:1494` | `Invalid track idx for pregap: %i` |
| `cyanrip_main.c:1500` | `Missing pregap action` |
| `cyanrip_main.c:1508` | `Invalid pregap action %s` |
| `cyanrip_main.c:1539` | `No cover art location specified for \"%s\"` |
| `cyanrip_main.c:1548` | `Invalid track idx for cover art: %i` |
| `cyanrip_main.c:1554` | `Cover art already specified for track idx %i!` |
| `cyanrip_main.c:1566` | `Cover art \"%s\" already specified!` |
| `cyanrip_main.c:1572` | `Too many cover arts specified!` |
| `cyanrip_main.c:1582` | `Directory name scheme must contain {format} with multiple output formats!` |
| `cyanrip_main.c:1587` | `-J (only generate a CUE sheet) cannot be used with -I (only print info)!` |
| `cyanrip_main.c:1603` | `Searching for drive offset, enabling AccuRip and disabling MusicBrainz and Cover art fetching...` |
| `cyanrip_main.c:1611` | `Offset is unset! To continue with an offset of 0, run with -s 0!` |
| `cyanrip_main.c:1679` | `MusicBrainz URL:%s` |
| `cyanrip_main.c:1723` | `Error reading album tags: %s` |
| `cyanrip_main.c:1753` | `Log(s) will be written to:` |
| `cyanrip_main.c:1761` | `CUE files will be written to:` |
| `cyanrip_main.c:1793` | `Invalid track number %i, list has %i tracks!` |
| `cyanrip_main.c:1809` | `Error reading track tags: %s` |
| `cyanrip_main.c:1863` | `Cover art destination(s):` |
| `cyanrip_main.c:1898` | `WARNING: tracks %i and %i resolve to the same file \"%s\", one will overwrite the other!` |
| `cyanrip_main.c:1909` | `Tracks:` |
| `cyanrip_main.c:1919` | `Track %i info:` |
| `cyanrip_main.c:1937` | `Error initializing decoder: %s` |
| `cyanrip_main.c:1946` | `Error initializing encoder: %s` |
| `cyanrip_main.c:1980` | `Error encoding: %s` |
| `cyanrip_main.c:2000` | `Invalid rip index %i, list has %i tracks!` |
| `cyanrip_main.c:2082` | `Error ripping: %s` |
| `discid.c:31` | `Unable to init SHA for DiscID: %s!` |
| `musicbrainz.c:116` | `Invalid disc number %i, release only has %i CDs` |
| `musicbrainz.c:121` | `Got empty medium list.` |
| `musicbrainz.c:127` | `No mediums match DiscID!` |
| `musicbrainz.c:155` | `Medium has no track list.` |
| `musicbrainz.c:193` | `Could not connect to MusicBrainz.` |
| `musicbrainz.c:201` | `Missing DiscID!` |
| `musicbrainz.c:212` | `MusicBrainz query failed: %s` |
| `musicbrainz.c:219` | `Connection failed, try again? Or disable via -N` |
| `musicbrainz.c:224` | `Error fetching/requesting/auth, this shouldn't happen.` |
| `musicbrainz.c:247` | `MusicBrainz lookup failed: DiscID has no associated releases.` |
| `musicbrainz.c:255` | `MusicBrainz lookup failed: no releases found for DiscID.` |
| `musicbrainz.c:259` | `Multiple releases found in database for DiscID %s:` |
| `musicbrainz.c:280` | `%i (ID: %s): %s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s` |
| `musicbrainz.c:294` | `Please specify which release to use by adding the -R argument with an index or ID.` |
| `musicbrainz.c:299` | `Invalid release index %i specified, only have %i releases!` |
| `musicbrainz.c:317` | `Release ID %s not found in release list for DiscID %s!` |
| `musicbrainz.c:348` | `Found MusicBrainz release: %s - %s` |
| `musicbrainz.c:362` | `MusicBrainz lookup failed, but DiscID has a matching stub, consider verifying the data and creating a release here:` |
| `musicbrainz.c:366` | `Unable to find release info for this CD, and metadata hasn't been manually added!` |
| `musicbrainz.c:370` | `Unable to find metadata for this CD, but metadata has been manually specified, continuing.` |
| `musicbrainz.c:376` | `Please help improve the MusicBrainz DB by submitting the disc info via the following URL:` |
| `musicbrainz.c:382` | `To continue add metadata via -a or -t, or ignore via -N!` |
| `naming.c:123` | `Error parsing string: %s!` |
| `naming.c:215` | `Invalid scheme syntax, unterminated \"{\"!` |
| `naming.c:229` | `Invalid scheme syntax, no \"#\"!` |
| `naming.c:243` | `Invalid scheme syntax, no terminating \"#\"!` |
| `naming.c:259` | `Invalid condition syntax!` |

**241 distinct stable lines.**

Field order within a block is fixed and is part of the contract. The golden
reference log in the handshake package is the authoritative example.

## P3 - Unstable lines: reworded without a handshake

Do not parse these. Most are stdout-only and never reach the logfile at all.

| File:line | Line | Reaches logfile? |
|---|---|---|
| `cyanrip_encode.c:105` | `%s folder: [%s] extension: %s%s` | **no, stdout only** |
| `cyanrip_encode.c:125` | `Encoder for %s not compiled in ffmpeg!` | **no, stdout only** |
| `cyanrip_main.c:736` | `\r` | **no, stdout only** |
| `cyanrip_main.c:802` | `%s` | **no, stdout only** |
| `cyanrip_main.c:883` | `Flushing encoders...` | **no, stdout only** |
| `cyanrip_main.c:923` | `Force quitting` | **no, stdout only** |
| `cyanrip_main.c:926` | `\rTrying to quit` | **no, stdout only** |
| `cyanrip_main.c:1320` | `Log \"%s\" checksum valid.` | **no, stdout only** |
| `cyanrip_main.c:1323` | `Log \"%s\" checksum mismatch, the file has been modified!` | **no, stdout only** |
| `cyanrip_main.c:1327` | `Log \"%s\" has data after the checksum, the file has been modified!` | **no, stdout only** |
| `cyanrip_main.c:1331` | `No FUN512 checksum found in \"%s\"!` | **no, stdout only** |
| `cyanrip_main.c:1335` | `Couldn't read \"%s\"!` | **no, stdout only** |

Also unstable, and **not ours**: the loudness block FFmpeg's `ebur128` filter
prints (`Integrated loudness`, `Loudness range`, `Sample peak:`, `True peak:`, ...). That wording
belongs to libavfilter and moves when FFmpeg does. Prefer the `Peak level:`
line in P2, which is ours and is gated on a completed rip.

## P4 - Exit codes

| Code | Meaning |
|---|---|
| `0` | Success: completed rip, `-I`, `-J`, `-h`, `-v`, or a `-Y` that validated |
| `1` | Every failure, without exception |

Distinct exit values found in the tree: `0`, `1`.

**There is no per-failure-class code.** Classification must come from the text,
which is why P5 exists. No non-zero exit is silent: argument parse failures
print before returning, and every other `return 1` in `main()` is preceded by a
`cyanrip_log()` call.

Argument validation runs **before the logfile is opened**, so that whole class of
diagnosis is **stdout only**. A consumer that reads only the logfile cannot see it.

## P5 - Fatal and error message inventory

Every string a failure can print. Use this to derive error matching rather than
guessing prefixes.

| File:line | Message |
|---|---|
| `accurip.c:97` | `Unable to get AccuRIP DB data: missing CDDB ID!` |
| `accurip.c:129` | `Unable to get AccuRIP DB data: missing entry!` |
| `accurip.c:137` | `Unable to get AccuRIP DB data: %s%s` |
| `accurip.c:140` | `Unable to get AccuRIP DB data: %s!` |
| `coverart.c:51` | `Unable to init lavf context: %s!` |
| `coverart.c:57` | `Unable to alloc stream!` |
| `coverart.c:70` | `Couldn't open %s for writing: %s!` |
| `coverart.c:82` | `Couldn't write header: %s!` |
| `coverart.c:92` | `Error writing picture packet: %s!` |
| `coverart.c:97` | `Error writing trailer: %s!` |
| `coverart.c:177` | `Unable to get cover art \"%s\": not found!` |
| `coverart.c:186` | `Unable to get cover art \"%s\": %s%s!` |
| `coverart.c:189` | `Unable to get cover art \"%s\": %s!` |
| `coverart.c:262` | `Unable to open \"%s\": %s!` |
| `coverart.c:269` | `Unable to get cover image info: %s!` |
| `coverart.c:299` | `Error demuxing cover image: %s!` |
| `cue_writer.c:39` | `Couldn't open path \"%s\" for writing: %s!Invalid folder name? Try -D <folder>.` |
| `cyanrip_encode.c:361` | `Error creating filter source: %s!` |
| `cyanrip_encode.c:372` | `Error creating filter sink: %s!` |
| `cyanrip_encode.c:386` | `Error setting filter sample format: %s!` |
| `cyanrip_encode.c:394` | `Error setting filter channel layout: %s!` |
| `cyanrip_encode.c:403` | `Error setting filter sample rate: %s!` |
| `cyanrip_encode.c:437` | `Error initializing filter sink: %s!` |
| `cyanrip_encode.c:471` | `Error parsing filter graph: %s!` |
| `cyanrip_encode.c:477` | `Error configuring filter graph: %s!` |
| `cyanrip_encode.c:536` | `Error pushing frame to FIFO: %s!` |
| `cyanrip_encode.c:555` | `Error filtering frame: %s!` |
| `cyanrip_encode.c:633` | `Error allocating frame!` |
| `cyanrip_encode.c:645` | `Error allocating frame: %s!` |
| `cyanrip_encode.c:776` | `Could not alloc swr context!` |
| `cyanrip_encode.c:794` | `Could not init swr context!` |
| `cyanrip_encode.c:969` | `Error while encoding: %s!` |
| `cyanrip_encode.c:991` | `Error encoding: %s!` |
| `cyanrip_encode.c:1022` | `Error pushing packet to FIFO: %s!` |
| `cyanrip_encode.c:1029` | `Error writing packet: %s!` |
| `cyanrip_encode.c:1059` | `Error writing to file: %s!` |
| `cyanrip_encode.c:1191` | `Unable to init output avctx!` |
| `cyanrip_encode.c:1202` | `Could not open output codec context!` |
| `cyanrip_encode.c:1209` | `Couldn't copy codec params!` |
| `cyanrip_encode.c:1216` | `Couldn't open %s: %s! Invalid folder name? Try -D <folder>.` |
| `cyanrip_main.c:181` | `No device specified and unable to get default device!` |
| `cyanrip_main.c:189` | `Unable to open device: %s` |
| `cyanrip_main.c:198` | `Unable to init cddap context!` |
| `cyanrip_main.c:214` | `Unable to open device!` |
| `cyanrip_main.c:240` | `Unable to init paranoia!` |
| `cyanrip_main.c:269` | `Invalid number of tracks: %i!` |
| `cyanrip_main.c:525` | `Stopping, offset finding incomplete!` |
| `cyanrip_main.c:610` | `Unable to read track %i subchannel info!` |
| `cyanrip_main.c:675` | `Error in decoding/sending frame: %s` |
| `cyanrip_main.c:687` | `Drive media changed, stopping!` |
| `cyanrip_main.c:718` | `Stopping, ripping incomplete!` |
| `cyanrip_main.c:873` | `Error in encoding: %s` |
| `cyanrip_main.c:889` | `Error sending flush signal to encoders: %s` |
| `cyanrip_main.c:1335` | `Couldn't read \"%s\"!` |
| `cyanrip_main.c:1382` | `Invalid paranoia level %i must be between 0 and %i!` |
| `cyanrip_main.c:1395` | `Invalid max coverart size %i (must be 250, 500, 1200 or -1)` |
| `cyanrip_main.c:1407` | `Invalid sanitation method %s` |
| `cyanrip_main.c:1419` | `Invalid release index %i!` |
| `cyanrip_main.c:1428` | `Invalid discnumber %i` |
| `cyanrip_main.c:1435` | `Invalid totaldiscs %i` |
| `cyanrip_main.c:1460` | `Invalid format \"%s\"` |
| `cyanrip_main.c:1494` | `Invalid track idx for pregap: %i` |
| `cyanrip_main.c:1500` | `Missing pregap action` |
| `cyanrip_main.c:1508` | `Invalid pregap action %s` |
| `cyanrip_main.c:1539` | `No cover art location specified for \"%s\"` |
| `cyanrip_main.c:1548` | `Invalid track idx for cover art: %i` |
| `cyanrip_main.c:1587` | `-J (only generate a CUE sheet) cannot be used with -I (only print info)!` |
| `cyanrip_main.c:1723` | `Error reading album tags: %s` |
| `cyanrip_main.c:1793` | `Invalid track number %i, list has %i tracks!` |
| `cyanrip_main.c:1809` | `Error reading track tags: %s` |
| `cyanrip_main.c:1937` | `Error initializing decoder: %s` |
| `cyanrip_main.c:1946` | `Error initializing encoder: %s` |
| `cyanrip_main.c:1980` | `Error encoding: %s` |
| `cyanrip_main.c:2000` | `Invalid rip index %i, list has %i tracks!` |
| `cyanrip_main.c:2082` | `Error ripping: %s` |
| `discid.c:31` | `Unable to init SHA for DiscID: %s!` |
| `musicbrainz.c:116` | `Invalid disc number %i, release only has %i CDs` |
| `musicbrainz.c:193` | `Could not connect to MusicBrainz.` |
| `musicbrainz.c:201` | `Missing DiscID!` |
| `musicbrainz.c:224` | `Error fetching/requesting/auth, this shouldn't happen.` |
| `musicbrainz.c:299` | `Invalid release index %i specified, only have %i releases!` |
| `musicbrainz.c:366` | `Unable to find release info for this CD, and metadata hasn't been manually added!` |
| `musicbrainz.c:370` | `Unable to find metadata for this CD, but metadata has been manually specified, continuing.` |
| `naming.c:123` | `Error parsing string: %s!` |
| `naming.c:215` | `Invalid scheme syntax, unterminated \"{\"!` |
| `naming.c:229` | `Invalid scheme syntax, no \"#\"!` |
| `naming.c:243` | `Invalid scheme syntax, no terminating \"#\"!` |
| `naming.c:259` | `Invalid condition syntax!` |

**88 distinct strings.**
