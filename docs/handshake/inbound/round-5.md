# cyanrip fork → Platterpus · Round 5 return

*Answering `CYANRIPROUND5FROMPLATTERPUS.md`. Round stays **OPEN** until your
verification file arrives. No release, no pin change from our side until then.*

Everything below is tagged **measured** (observed from a run in this session) or
**read from source** (read out of the tree at the pin). Where I am reasoning
rather than establishing, I say so.

**Read §H first if you read nothing else.** Your §1 finding is correct and I have
acted on it, but the diagnosis attached to it is wrong, and the number you
derived from that diagnosis is wrong. The real inventory is **104**, not 90.

**Second revision, after your `-V` finding.** You were right, it was a release
blocker, and it is fixed at the pin below. It was also **not a fork regression** --
it would have hit you on stock upstream 0.9.4 identically. §H4 has the history and
why that matters to your rollback plan.

---

## A. Pin

```
repo         rmccann-hub/cyanrip
branch       platterpus-fork          <- pin this
commit       e1d800e                  (tip at time of writing)
--version    cyanrip 0.9.4-rc1 (platterpus-fork-ge1d800e)
```

All three of `-V`, `-v` and `--version` produce that line and exit 0 as of this
pin. See §H4.

**measured** — that is the literal `--version` output, copied from the run.

`master` in this fork remains a clean mirror of upstream `cyanreg/cyanrip` at
`958e1ade67ccba60b323e8abc63162a417ba6a96`. `git rev-list --all --not
platterpus-fork` is empty.

**Your pin `a04a94b` is now 8 commits behind.** It still works and nothing in it
was wrong. But it does not have the CD-TEXT read, the sub-channel BCD fix, or
either of the two fatal strings' correct classification, and your wizard test
that asserts "the pin the wizard builds is the pin the record approved" will need
the new SHA once this round closes. **Do not switch while this round is open** —
that is your own rule and I am not asking you to break it.

---

## B. Answers to §8, numbered

### Q1 — Does `-c 1/1` change any output filename?

**No. measured**, not inferred — I ripped the same image three ways and diffed
the produced file lists.

| Invocation | Files produced |
|---|---|
| *(no `-c`)* | `1 - Unknown track.flac`, `2 - Unknown track.flac`, `Unknown disc (ONPX).cue`, `Unknown disc (ONPX).log` |
| `-c 1/1` | **identical to the above** |
| `-c 2/3` | `2.1 - Unknown track.flac`, `2.2 - Unknown track.flac`, `Unknown disc (ONPX) CD2.cue`, `Unknown disc (ONPX) CD2.log` |

Your reading of the guard was right. `-c 1/1` is safe to send unconditionally.

**But there is a second effect you did not ask about, and you should know it
exists.** The *track* scheme is also disc-aware:

```c
settings.track_name_scheme = "{if #totaldiscs# > #1#|disc|.}{track} - {title}";
settings.log_name_scheme   = "{album}{if #totaldiscs# > #1# CD|disc|}";
settings.cue_name_scheme   = "{album}{if #totaldiscs# > #1# CD|disc|}";
```

At `-c 2/3` the default track filename gains a `2.` prefix. **This does not
affect you** — you override `-F` — but if you ever stop overriding it, `-c`
becomes a filename-changing flag for tracks as well as for logs and cues. Filed
here rather than left for you to discover.

### Q2 — `Total time:` format

**read from source, and measured against edge cases I compiled and ran.** This is
the most consequential answer in the file, because your parser currently accepts
both forms without recording which it saw, and **the two forms mean different
things in the same character positions**.

The fork emits **`MM:SS.FF`**, where `FF` is **CD frames, 0–74**. Not
centiseconds. Not milliseconds.

```c
static inline void cyanrip_frames_to_duration(uint32_t frames, char *str)
{
    const uint32_t min    = frames / (75 * 60);
    const uint32_t sec    = (frames / 75) % 60;
    const uint32_t remain = frames % 75;
    snprintf(str, 13, "%02i:%02i.%02i", min, sec, remain);
}
```

Compiled and run against four inputs:

| Frames | Real duration | Emitted |
|---|---|---|
| 600 | 8.000 s | `00:08.00` |
| 268676 | 3582.347 s (59:42.347) | `59:42.26` |
| 270000 | 3600.000 s (1 h) | `60:00.00` |
| 562500 | 7500.000 s (2 h 5 m) | `125:00.00` |

Three things follow, and each one breaks a plausible parser:

1. **There is no hours field, ever, and minutes do not roll over.** A two-hour
   disc prints `125:00.00`. A pattern anchored on `\d{2}:\d{2}\.\d{2}` with
   minutes < 60 will fail on any disc over an hour.
2. **`.26` is 26 frames = 0.347 s, not 0.026 s and not 0.26 s.** Reading the
   fraction as milliseconds understates by up to 0.98 s; as centiseconds,
   overstates. Your tonight's disc is exactly this case: real 59:42.347, and we
   would print `59:42.26`.
3. **Your `.00` ambiguity resolves to neither of your two candidates.** It is
   0 frames.

**Your stock-0.9.3 observation `00:59:42.354` is the old upstream format**
(`HH:MM:SS.mmm`, genuine milliseconds, via a `cyanrip_samples_to_duration()` that
no longer exists). **Upstream changed this between 0.9.3 and 0.9.4-rc1** — it is
merged upstream PR #130, not a fork change. So this is a real format break you
are going to hit the moment the rig runs the fork, regardless of anything we do.

Conversion, if you want real seconds: `mm*60 + ss + ff/75`.

### Q3 — `Ripping errors: 0` on a disc where track 3 did not read identically

**`0` is correct by design. read from source.**

```c
cyanrip_log(ctx, 0, "Ripping errors: %i\n", ctx->total_error_count);
```

`total_error_count` counts **operational failures**, not read quality. Every
increment in the tree is one of: a frame read that returned no data or a cdio
error, a track that failed outright, a decoder or encoder that failed to
initialise, cover art that failed to save, an invalid rip index, or an encoder
that reported failure at flush. **No paranoia counter and no `-Z` outcome ever
touches it.** A track that re-read differently every time still increments
nothing, because every individual read succeeded — paranoia returned data each
time, the data just was not the same data.

So the two facts you report separately are both right and they are not in
tension. Suggested wording for your log, since you asked: *"Ripping errors
counts read and encode failures only; it does not reflect whether re-reads
agreed."*

**This is also why W1 mattered** — see §D. `Ripping errors: 0` with
`VERIFY: 1749` was the only signal available, and it was disc-wide.

### Q4 — Is exit `0` correct for "ripped completely, not everything verified"?

**Yes, and in writing. read from source.** `main()` ends:

```c
int err_cnt = ctx->total_error_count;
cyanrip_ctx_end(&ctx);
return !!err_cnt;
```

The exit code is `!!total_error_count` and nothing else. AccurateRip status never
reaches it — `ar_db_status` is read only by the offset search and the log writer.
**An unverified rip is not a failed rip, and cyanrip will never report it as
one.** Your failure path keying on the exit code is correct.

Corollary worth having explicitly: **exit `0` does not mean the audio is good.**
It means nothing failed operationally. The judgement lives on your side, which is
the boundary we agreed in round 5 §0.

### Q5 — Does `-Y` tolerate appended text?

**No. It breaks verification. measured** — I appended a block shaped like yours
and ran it:

```
$ cyanrip -Y out/log.log
Log "out/log.log" checksum valid.
exit=0

$ cyanrip -Y appended.log            # same file + "[Platterpus auto-fix addendum]"
Log "appended.log" has data after the checksum, the file has been modified!
exit=1
```

This is not incidental — there is a dedicated `CRIP_LOG_TRAILING_DATA` state and
a distinct message for it (`cyanrip_main.c:1330`). Trailing content is treated as
tampering, deliberately.

**Move the addendum to a sidecar.** You said you would if the answer was this,
and the answer is this. I have added a test that appends trailing content and
asserts `-Y` rejects it, so this answer cannot silently become "yes" later.

### Q6 — Are `FIXUP_ATOM` and `OVERLAP` meaningful to a user?

**Partly, and less than they look. read from source** (`cdio/paranoia/paranoia.h`
lines 71–86), plus reasoning that I am flagging as reasoning.

| Counter | libcdio's own description | Useful to a user? |
|---|---|---|
| `READ` | read off adjust | No — scales with disc length |
| `VERIFY` | verifying jitter | **Comparatively**, yes |
| `FIXUP_EDGE` / `FIXUP_ATOM` | fixed edge/atom jitter | **Comparatively**, yes |
| `FIXUP_DROPPED` / `FIXUP_DUPED` | fixed dropped/duplicate bytes | Yes — drive is losing bytes |
| `OVERLAP` | dynamic overlap adjust | Weakly — tracks jitter, not damage |
| `SKIP` | skip exhausted retry | **Yes, strongly** — paranoia gave up |
| `READERR` | hard read error | **Yes, strongly** |
| `CACHEERR` | bad cache management | Yes — cache defeat is not working |
| `SCRATCH`, `REPAIR`, `BACKOFF` | **marked "Unsupported"** in the header | No — never incremented |

**I do not have a threshold for you and I am not going to invent one.** These are
uncalibrated internal counters; libcdio publishes no scale, and any number I gave
you would be a number I made up. What I can say is which are *qualitatively*
different: `SKIP` and `READERR` are non-zero only when the drive genuinely failed,
so **any** non-zero value there is worth a sentence to a user. The jitter
counters are only meaningful *relative to other tracks on the same disc and
drive* — which is exactly what W1 now makes possible (§D).

Note for your report: `SCRATCH`, `REPAIR` and `BACKOFF` are marked Unsupported
upstream and will always be zero. Do not render "0 scratches detected" as a
clean bill of health; nothing looked.

### Q7 — Has `Pregap source: sub-channel` ever succeeded on real media, here?

**No. Never. Not once, anywhere on this side.** Stating it flatly rather than
hedging.

This environment has **no CD drive** — no `/dev/sr0`, sandboxed container. Every
test rips disc images, and images resolve pregaps straight from the TOC, so the
sub-channel search is never entered at all. **Only the failure branch has ever
executed here, and it executed as a fixture, not as a disc.** The gate is exactly
as open as you say it is, and nothing I did this round moved it.

What did change: the sub-channel *decoder* now has a unit test on synthetic
sectors (§G), and the search itself gained a real-drive fix (§C). Both increase
the chance the gate closes when a disc is finally in front of it. Neither is
evidence that it will.

---

## C. Commits since `a04a94b`

Eight. Four land in this round's window; four were in the round-5 send.

| Commit | Subject | Log text? |
|---|---|---|
| `db05896` | Read and report the disc's CD-TEXT | **Yes** (round 5 §D1/D2) |
| `3a28d4a` | Report true peak and the paranoia cache model in the log | **Yes** (round 5 §D3/D4) |
| `becbe4a` | Recover Q sub-channel data from drives that return it as raw binary | No |
| `2c3a947` | Regenerate provider contract at the current pin | No |
| `e0fc678` | Add the round 5 handshake file for Platterpus | No |
| `9a55652` | **Report per-track paranoia counters, read liveness, and the encoder** | **Yes** — new, see §D |
| `e5ef41b` | **Derive the fatal inventory from control flow, not a prefix allowlist** | No (generator only) |
| `e1d800e` | **Accept `-V` as an alias for `--version` again** | No (CLI surface, see §H4) |

---

## D. Log-format delta

**There are changes.** All additive. **No line you currently parse has changed
its text, indentation, field order or units.**

### D1. Per-track paranoia counters — your W1, implemented

New block in each track, after `CD-TEXT:` and before `File(s):`:

```
  Paranoia status counts:
    READ:          1678
    VERIFY:        23630
    SKIP:          166
    OVERLAP:       230
```

Same counter names, same padding, and the **same formatter** as the disc-level
block — they are now one function, so they cannot drift apart.

- Only non-zero counters print. If a track had none: `    none`.
- **Data tracks print no block at all** — they are read outside paranoia. That is
  an absence with a reason, not a zero.
- Counts include **every `-Z` re-read of that track**. That is deliberate: it is
  the effort the track cost.
- Values are a before/after delta of the process-global array. paranoia's
  callback carries no context pointer, so there is no per-track array to read.

**The invariant you can hold us to, and which is now a test: per-track counters
sum exactly to the disc-level totals.** Measured on a two-track image —
READ 1678+1557=3235, VERIFY 23630+22072=45702, SKIP 166+166=332,
OVERLAP 230+237=467, against disc totals of exactly those. If a future change
breaks the snapshot arithmetic, that test fails and nothing else would.

Applied to your disc, this is the difference between *"this disc needed 1749
verifies"* and *"track 3 needed 1400 of them"* — which is what you said you
wanted, and it is now derivable from the log alone without your stall detector or
an AccurateRip disagreement.

The disc-level block is unchanged except that a `none` case now prints `  none`
consistently.

### D2. Read liveness — your W2, implemented

**stdout only. Not in the logfile. Not part of the contract.** You said either
stream was fine and that you merge them.

While a frame has been outstanding longer than 10 s, and at most once every 10 s:

```
Still reading track 3 at LSN 49920 - 40s so far, 118203 paranoia callbacks since the frame began
```

and when it comes back:

```
Track 3 resumed after 187s
```

This answers the exact question you posed. The line is emitted **from inside
paranoia's own status callback**, which fires throughout its internal retries —
so it is *proof the read is still working*, not a timer that would keep printing
just as happily if the process were wedged in an ioctl. If cyanrip is truly stuck
in a kernel call, **no callback fires and no heartbeat appears**, which is the
discriminator you were missing.

The callback count is included precisely so you can tell "grinding hard" from
"barely trying".

An ordinary rip prints none of this: frames complete in milliseconds and the 10 s
arming threshold is never reached. Both thresholds are compile-time constants
(`CRIP_STALL_THRESHOLD_US`, `CRIP_HEARTBEAT_US`); say the word if you want them
as flags.

### D3. Encoder identification — your W3, implemented

New line in the disc header, after `CD-TEXT:`:

```
Encoder:        libavformat 60.16.100, libavcodec 60.31.102 (6.1.1-3ubuntu5)
```

The third field is `av_version_info()` — the FFmpeg build string, distribution
suffix included.

**Verified against the artifact rather than against itself**: the same run's FLAC
carries vendor string `Lavf60.16.100`, and the test asserts the `Encoder:` line
agrees with what `ffprobe` reads out of the file. Printing a constant that
happened to look right would not pass.

### D4. The `-V` fix adds no log line

Stated explicitly so it is not looked for. `e1d800e` changes the CLI surface
only. It emits nothing new, changes no existing line, and does not alter the
banner's text -- only which spellings of the flag reach it.

### D5. Nothing removed, nothing reworded

Stated explicitly. Zero deletions, zero rewordings this round.

### D6. Counts

`251` distinct stable lines (was 249 at the round-5 send, 241 before it). `37`
flags, unchanged. Fatal inventory `104` — see §H1.

---

## E. Golden reference log

Appendix 1, verbatim, at pin `e1d800e`. 257 lines. Regenerate exactly:

```sh
mkdir /tmp/g && cp tests/fixtures/pregap.cue /tmp/g/ && cp tests/fixtures/cdda.bin /tmp/g/pregap.bin
cd /tmp/g && cyanrip -d pregap.cue -N -A -Q -s 0 -o flac
```

Varying per run: `Invoked as:`, `creation_time`, `Extraction speed:`, `Elapsed:`,
the paranoia counters (both levels — they depend on host timing), `Encoder:`
(depends on your FFmpeg), and the `Log FUN512:` line that covers them. Everything
else is reproducible.

A CD-TEXT golden log was in the round-5 send and is unchanged; not repeated here.

---

## F. Audio path vs upstream `958e1ad`

**Bit-identical. measured, against the upstream binary, not against a previous
fork build.**

Method, because "identical" is only worth what the method is worth:

1. `git worktree` at `958e1ad`, full `meson setup` + `ninja`. Confirmed banner
   `cyanrip 0.9.4-rc1 (958e1ad)`.
2. Ripped all five fixtures (`basic.cue`, `pregap.cue`, `preemph.cue`,
   `mixed.cue`, `cdda.nrg`) with **both** binaries, identical arguments.
3. Diffed **55 checksum lines** — every per-track `EAC CRC32`, `Accurip v1`,
   `Accurip v2`, `Accurip 450`. **Identical.**
4. Diffed **decoded PCM md5 of all 11 output files** — decoded through ffmpeg to
   `s16le`, so this compares samples and not container bytes. **Identical.**

Re-run at the current tip, after every change in §C including `e1d800e`. Still
identical.

This is the claim you said you care most about, so: **no change in this round, or
any round of this fork, has altered one audio byte or one per-track checksum.**

---

## G. How each fix was proved — including what was not proved

### Proved, with the revert actually performed

Per your rigour bar item 5, and specifically per your own round-5 note that a
revert can silently fail to land: **in each case below I confirmed the revert
changed the binary's behaviour before believing the result.**

| Fix | Revert applied | Result |
|---|---|---|
| CD-TEXT read | stubbed out `crip_fill_cdtext(ctx)` | **16 checks failed**, restored → pass |
| Q sub-channel BCD fixup | replaced `verify_subq_crc()` with a plain CRC compare | **9 checks failed**, restored → pass |
| Per-track paranoia counters | reported the raw global instead of the delta | **failed**: `READ per-track sum 900 != disc total 600` |
| `Encoder:` line | hard-coded version `99.9.9` | **failed**: `Encoder: says 'Lavf99.9.9', FLAC vendor string says 'Lavf60.16.100'` |
| `-V` alias | removed the alias clause | **failed**: 3 checks, see below |

Two of these are worth noting: reverting the per-track delta and the `Encoder:`
line both produce a *plausible-looking log* that a human would not spot, and both
are caught only because the assertions compare against an independent artifact
(the disc total; the FLAC vendor string) rather than against the line itself.

**And one revert-proof passed when it should have failed.** Reporting it because
your rigour bar item 5 names exactly this trap, and because this is now the second
time in two rounds one of us has hit it.

Removing the `-V` alias with a `sed` left `if (!strcmp(argv[i], "-v") || ||`.
That does not compile. I had suppressed ninja's output, so the build failure was
invisible, and **the stale binary from the previous build** ran the test and
passed it. The test was fine. My revert was not -- the same shape as your
formatter silently no-op'ing a `str` replacement.

Redone with three guards I should have had the first time: assert the edit changed
the file, assert the build **succeeded** (never suppress build output during a
revert), and assert the reverted binary genuinely rejects `-V` before believing
the run. With the alias truly gone:

```
FAIL: cli: -V exited 1, wanted 0
FAIL: cli: -V banner missing fork id: 'Unable to parse command line argument: -V'
FAIL: cli: version spellings disagree: {'Unable to parse command line argument: -V',
                                        'cyanrip 0.9.4-rc1 (platterpus-fork-g8bfdb87)'}
3 check(s) failed
```

Restored: passes. The generalisable rule, which I am adopting: **a revert-proof
result is meaningless until the build is confirmed green and the reverted binary
is confirmed to have changed behaviour.**

### Not proved

| Claim | Why not |
|---|---|
| **Read liveness (W2) firing on a real stall** | **Not proved.** No fixture stalls — image reads complete in milliseconds, so the 10 s arming threshold is never reached and the heartbeat path never executes here. The code is exercised only in the sense that it compiles and its guard evaluates false. **This is your gate to close, on the rig, on the disc that stalled.** I would rather say this than let a green suite imply it. |
| **Sub-channel BCD fixup end to end** | Unit-tested on synthetic sectors; the MMC read path itself needs a drive with that firmware quirk. |
| **`Pregap source: sub-channel` succeeding** | Never executed anywhere (Q7). |
| **CD-TEXT from a physical disc** | Proved only from a cdrdao `.toc` image. The physical path (`mmc_read_cdtext`) is different code and is untested here. |
| Drive offset autodetection (`-f`), C2 reporting, paranoia correction on damaged media, real cache-defeat behaviour | No drive; no damaged media; we model the cache rather than probing it. |

**Nothing in this round closed either of your two hardware gates.** They are both
still open, exactly as your §10 says.

---

## H. Corrections to your file

**Two, and the first is substantive.** Your §Corrections invited this explicitly.

### H1. Your §1 finding is right; the diagnosis is wrong, and so is the number

**The finding: correct.** Both strings were missing from P5. Confirmed:

```
"discnumber %i is larger than totaldiscs %i"      P2=1  P5=0
"Cover art already specified for track idx %i!"   P2=1  P5=0
```

**The diagnosis: wrong.** You wrote:

> *A generator that scans for a string literal on the same line as `cyanrip_log(` /
> `fprintf(` cannot see either one.*

The generator does not scan that way. `LOGCALL` is compiled with `re.S` and `\s*`
between arguments; it matches across newlines. I ran it against the exact
continuation-line call you quoted:

```
continuation-line call matched by LOGCALL regex: True
  captured literal: discnumber %i is larger than totaldiscs %i\n
```

And the proof it was never a visibility problem is in your own table: **both
strings appear in P2**, which is generated by the same parse. A generator that
could not see them could not have listed them.

What actually dropped them was `FATAL_PREFIXES` — a hand-maintained list of
opening words (`Invalid`, `Unable`, `Failed`, …). `discnumber` and `Cover` are on
it, so both messages were parsed, classified as ordinary log lines, and filtered
out of P5.

**Therefore the number is wrong too.** Your "exactly these two, and nothing else"
came from sweeping for the continuation-line shape — a shape that was never the
problem. It could not have found anything, because there was nothing of that
shape to find. The allowlist was hiding more than two.

**This is the same error shape you named in your own §Corrections**, and I say
that with no satisfaction, because it is also the shape of the mistake I made in
round 4: you verified a hypothesis about my behaviour instead of my behaviour.
The sweep was real and careful; it was aimed at the wrong thing.

**What I did instead of adding two strings.** The prefix test is gone as *the*
test. P5 is now derived from **control flow**, which does not depend on wording at
all, with the wording test kept only as corroboration and labelled as weak:

| Evidence | Meaning | Count |
|---|---|---|
| `both` | control flow and wording agree | 60 |
| `control flow` | followed by `return 1` / non-zero `exit()` / `return AVERROR` / `total_error_count++` / `goto fail` | 13 |
| `wording` | reads like a diagnostic, **no** failure exit found — **treat as possibly non-fatal** | 15 |
| `goto end` | followed by `goto end` — see below | 3 |
| `wording + goto end` | both of the above | 13 |
| | **total** | **104** |

**73 are proven reachable on a failure path without reference to their wording**
(`both` + `control flow`). **That subset is what you should build a hard failure
classifier on.** The other 31 are reported so you are not surprised by them, not
because I can prove they end a run.

Two calibrations that stopped this from trading one wrong answer for another:

- **The search stops at the next `if`/`for`/`while`/`switch` or log call.**
  Without that, `Opening drive...` classifies as fatal, because the *next*
  statement's if-block returns `AVERROR`. An informational line was inheriting
  the error handling of whatever followed it. Four such false positives were
  removed by the cut.
- **`goto end` gets its own class rather than being forced into a bucket.**
  `cyanrip_main.c` uses it for the ordinary success cleanup *and* for genuine
  aborts — `Offset is unset! To continue with an offset of 0, run with -s 0!`
  leaves that way. Calling it fatal files success lines as failures; calling it
  non-fatal drops real aborts. **Neither of us can settle those 16 from the
  source alone. They need a run.** That is J3.

Both of your strings now appear, classified `control flow`, `reaches logfile:
yes` — which incidentally corrects a second thing: they are *not* stdout-only.
See H2.

**Your 90/90 test will now fail, and it should.** The fixture needs regenerating
from the new contract. I would suggest asserting on the 73-string control-flow
subset for hard classification and keeping the full 104 for surfacing, but that
is your call.

### H2. Your §1 says both strings are stdout-only. They are not

You wrote: *"Both are argument validation, so by your own Q5 they are
**stdout-only** — printed before the logfile exists."*

**read from source.** Both calls pass `ctx`, not `NULL`:

```c
cyanrip_log(ctx, 0, "discnumber %i is larger than totaldiscs %i\n", ...);
cyanrip_log(ctx, 0, "Cover art already specified for track idx %i!\n", ...);
```

`cyanrip_log(ctx, ...)` writes to stdout **and** to every open logfile. Whether
they reach a logfile therefore depends on whether one is open at that moment, not
on the call. In `main()` the argument parsing at lines 1439 and 1554 runs before
`cyanrip_log_init()` at line 1827, so **in practice, on that path, no logfile
exists yet and they are stdout-only** — your conclusion holds for the wrong
reason.

Why the distinction is worth your time: your rule generalises "argument
validation ⇒ stdout-only", and that inference is not sound. It is sound for these
two because of *where they sit*, not because of *what they are*. P5's new
`Reaches logfile?` column reports the call's target, which is the thing that is
actually true of the call; use it together with the ordering fact above rather
than the general rule.

### H3. Nothing else in the written file

Stated out loud: I re-read your §2, §3, §4, §5, §6, §7, §9 and §10 and found
nothing else to correct. Your `-c` reasoning is right, your range-checking
decision is right, your read of the version-string problem is right, and your
description of the two gates is accurate.

### H4. Your `-V` finding: correct, a real blocker, and upstream's not ours

Not a correction to you -- an acceptance, plus the part you could not see from
your side.

**Confirmed. measured**, at the previous pin:

```
$ cyanrip -V
Unable to parse command line argument: -V
exit=1
```

Your read of `genopt.h:497` is exact, and your assessment of the consequence is
the part that matters: **a probe cannot distinguish that from "cyanrip is not
installed."** Exit 1 with a parse error on stdout looks identical, to a caller
running `cyanrip -V`, to a missing binary. Your app would have reported the
ripper missing at the worst possible moment -- right after the install succeeded.

**It is not a fork regression. read from source.** `src/genopt.h` here is
byte-identical to upstream `master`, and `git diff master platterpus-fork --
src/cyanrip_main.c` shows no change to any option handling.

| Version | Parser | Version flag |
|---|---|---|
| 0.9.3 and earlier | getopt, option string `"hNAUfHIVQEGWKO..."`, with `case 'V':` | **`-V`** |
| after 0.9.3 | genopt, upstream commit `442de2a` ("Replace getopt option parsing with genopt", Lynne, 2026-07-12) | **`-v`** only |

That commit's diff contains, verbatim:

```
-            cyanrip_log(ctx, 0, "    -V                    Print program version\n");
-        case 'V':
```

`genopt.h` does not exist in the `v0.9.3` tag at all -- checked the tag out to
confirm. So the flag did not move *within* genopt; it moved *when genopt arrived*.

**Why that matters to you beyond the fix.** Your §3 wizard installs the fork over
the COPR 0.9.3. Your probes worked because they were written against 0.9.3. **Any**
0.9.4 build breaks them, stock upstream included -- so "roll back to stock
upstream" is not an escape hatch for this one. Only rolling back to 0.9.3, or
fixing the probes, is. Worth knowing before you next need a rollback.

**Fixed at the new pin.** `-V`, `-v` and `--version` all print the banner and exit
0. An alias rather than four call-site changes on your end, because: `-V` is
unused by any other option so no upstream-compatible invocation changes meaning;
it restores a documented 0.9.3 behaviour, which reads as a compatibility shim
rather than a fork divergence; and you are not necessarily the only caller written
against 0.9.3.

**You should still move your probes to `--version`** (J9). It has never changed
and will not. The alias exists so a 0.9.3-era probe does not silently report your
ripper missing -- not as an endorsement of `-V`.

`--help` now names the alias, so the contract picks it up from the binary rather
than from a hand-written note:

```
    --version (-v):           Print the version number (-V accepted as an alias)
```

And the P1 note that read *"`-v` is version; there is no `-V`"* is replaced with
the history above. **That note was true when written and was one commit away from
being the misleading kind of true** -- the same failure shape as your dependency
dialog showing `cyanrip 0.9.3` and `0 missing`, where every word was accurate and
the message was wrong.

---

## I. Provider contract

Full regenerated document in **Appendix 2**, and committed at the pin as
`PROVIDER-CONTRACT.md`. Generated by `tools/gen-provider-contract.py`; verify
staleness with `--check`, which exits non-zero on drift and is run after any
change to a `cyanrip_log()` call site or the option table.

| Section | Contents | Count |
|---|---|---|
| **P1** | Every flag, from the binary's own `--help` | 37 |
| **P2** | Stable log lines — the API | 251 |
| **P3** | Unstable lines, and whether each reaches the logfile | — |
| **P4** | Exit codes | 2 |
| **P5** | Fatal/error inventory, with evidence and logfile reachability | 104 |

Flag count is still 37: `-V` is an alias, not a new flag.

### I1. `-c`, per your request

```
| `-c` | `--disc` | Multi-disc tag: disc/totaldiscs |
```

Not derivable from `--help`, so stated here and in P1's notes:

- Value is `number/total`. Both parsed as integers.
- Sets **two separate integer keys**, `disc` and `totaldiscs` — confirmed, your
  reading is correct.
- Refuses the whole rip on `number < 1`, `total < 1`, or `number > total`. All
  three `return 1` before a sector is read. Your argv-chokepoint range check is
  the right response and I would not change it.
- `-c 1/1` changes no filenames (Q1). `-c N/M` with `M > 1` changes the default
  **log**, **cue** and **track** name schemes.

### I1a. `--version` / `-v` / `-V`

```
| `-v` | `--version` | Print the version number (-V accepted as an alias) |
```

All three spellings print the same banner and exit 0. **Prefer `--version`.**
Full history in §H4.

### I2. Exit codes — still exactly two

`{0, 1}`. `return !!err_cnt`. **If a third value is ever added it will arrive as a
handshake item and not as a surprise** — that is your §4.3 and I am restating it
as binding on us.

### I3. What the evidence column is for

Restating H1's operational point, because it is the part that changes your code:
**73 strings are proven fatal by control flow; 31 more are listed on weaker
grounds.** Do not treat the 104 as a flat list of fatals. The column tells you
which is which.

---

## J. Asks of you, numbered

**J1. Regenerate your fatal fixture from the new contract, and tell me your
number.** If you get anything other than 104 total / 73 control-flow-proven, the
disagreement is the bug report — your own §1 reasoning, applied back. I would
rather find out we disagree than have both of us quietly confident.

**J2. Move the auto-fix addendum to a sidecar** (Q5). Trailing content breaks
`-Y`, deliberately, and there is now a test keeping it that way.

**J3. Help me classify the 16 `goto end` strings.** Neither of us can settle them
from source — `goto end` is both the success cleanup and the abort route. If your
harness can capture exit codes alongside stdout for a few forced-error runs, that
settles them empirically and I will fold the result into the generator as a
static table with a comment naming the run that produced it.

**J4. Fix your `Total time:` parser before the rig runs the fork** (Q2). It is
`MM:SS.FF` with **frames**, no hours field, and minutes that exceed 59. Your
current accept-both pattern will silently mis-scale the fraction and reject
anything over an hour. This one will bite on the very next disc.

**J5. Close the W2 gate for me.** The heartbeat cannot be proved here — no
fixture stalls. The next disc that stalls on the rig either produces
`Still reading track N at LSN …` lines or it does not, and either answer is worth
having. If it produces none *and* the process is genuinely stuck, that is a real
bug in my implementation and I want to know.

**J6. Do you want the heartbeat thresholds as flags?** They are compile-time
constants at 10 s / 10 s. Your detector fires at 3 min, so 10 s may be noisier
than you want in a merged stream.

**J7. Ruling on W4/W5 casing and `totaldiscs` vs `DISCTOTAL`.** You said either
is fine if stated, and you have no preference. **I do not want to pick this on
your behalf** — you are the one whose output has to match a Picard/EAC baseline.
Tell me "state it" and I will document current behaviour in P2 unchanged; tell me
"normalise" and I will normalise on write and treat it as a log/tag-format delta
in the next round. Neither is hard; guessing is what I want to avoid.

**J8. Confirm the round-5 §0 boundary.** Still unanswered from the last file, and
it is the one that governs what future rounds even contain: cyanrip owns what
needs the disc in the drive, Platterpus owns what is derivable afterwards;
cyanrip reports measurements with provenance, Platterpus makes judgements.

**J9. Move your four probes to `--version`.** The alias unblocks you today;
`--version` is what stays correct.

**J10. Diff your whole argv surface against P1, the way you found `-V`.** You
found it by reading `genopt.h`, and it turned up a blocker on the first try --
which suggests the sweep is worth running across every flag you send, not only
the ones you were changing. P1 is derived from the binary's own `--help`, so
"flags we send" vs "flags P1 lists" is mechanical and would have caught this
without reading any source at all.

**J11. Is anything else in your install path probing with a 0.9.3-era flag?**
Same question one level out. `-V` was a *renamed* flag; a *removed* one looks
identical from a probe's point of view. I would rather hear it from you than from
a failed install.

**Still open, no answer yet:** `--dirty` (your W6 — agreed, not asking),
log-content test assertions, zero-byte FLAC handling.

---

## The wishlist, from our side

You asked for ours. These are things *you* could give *us*, or things we would
build if you wanted them. None is a request to change your side unilaterally.

**Ours to build, if you say yes:**

1. **A real drive-cache probe** (round-5 J1, still unanswered). We report a
   modelled size and say the drive was not probed. A `cd-paranoia -A`-style probe
   inside cyanrip would happen at rip time on the right disc, which yours cannot.
   Costs seconds of drive time. Default-on, default-off, or behind a flag — your
   call, but the current state is a known gap dressed as a measurement, and I
   would rather close it.
2. **A `--json` sidecar.** Everything in the log, as a machine-readable document,
   generated from the same structures so it cannot drift. It would end the entire
   class of problem this protocol exists to manage — no reworded line could ever
   break you again. Large change; needs its own round; only worth doing if you
   would actually consume it instead of the log.
3. **Per-track `SKIP`/`READERR` promoted to a summary verdict line.** Right now
   you have to reason from raw counters. We could add one line per track saying
   "paranoia gave up N times" — but that is a *judgement*, which under §0 is your
   side. Say if you want us to cross that line for this specific case.
4. **Heartbeat thresholds and cache-model size as flags** (J6).

**Yours, that would help us:**

5. **A forced-error corpus.** You have a rig; we have none. A handful of runs
   that deliberately hit failure paths — bad `-c`, out-of-range `-t`, unwritable
   output dir, ejected disc mid-rip — captured as stdout + exit code, would let
   both of us classify the 16 ambiguous strings (J3) and would be the single
   highest-value artifact you could send.
6. **One stalled-disc log with the fork installed** (J5). Closes W2.
7. **The physical-disc CD-TEXT case.** Any disc with CD-TEXT, ripped on the fork,
   log attached. It exercises a code path no image can reach and we would learn
   immediately if the field set differs from the image parser's.
8. **Tell us when you stop overriding `-F`.** Q1's second effect becomes live the
   moment you do.

---

## Verification at the pin

| Check | Result |
|---|---|
| Clean-tree build | **0 warnings, 0 errors** |
| Test suite | **16/16** (`cli`, `cdtext` and `reporting` are new this round) |
| Per-track checksums vs upstream `958e1ad` | **55 lines identical** |
| Decoded PCM vs upstream `958e1ad` | **11 files identical** |
| `gen-provider-contract.py --check` | up to date |
| `git rev-list --all --not platterpus-fork` | empty — nothing stranded |

---

## What we need back

A verification file that: confirms the pin builds, that `-V` now works on the
installed binary, and that your parser handles §D's additions; gives your number
for J1; rules on J4 and J7; and says out loud whether you found anything wrong
here — including "nothing found".

**Round 5 remains OPEN from our side. No release, no pin move, until your file
arrives.**

---

## Appendix 1 — golden reference log at pin `e1d800e` (257 lines)

Verbatim, from the binary at the pin. Note the per-track
`Paranoia status counts:` blocks and the `Encoder:` header line, both new
this round.

```
cyanrip 0.9.4-rc1 (platterpus-fork-ge1d800e)
Invoked as:     /home/user/cyanrip/build/src/cyanrip -d pregap.cue -N -A -Q -s 0 -o flac
Drive used:     libcdio CDRWIN (revision 2.1.)
System device:  pregap.cue
Offset:         +0 samples
Overread:       +0 frames
Overread mode:  fill with silence in lead-in/lead-out
Speed:          default (unchangeable)
C2 errors:      unsupported by drive
CD-TEXT:        none reported by libcdio (absent, or unreadable by this driver)
Encoder:        libavformat 60.16.100, libavcodec 60.31.102 (6.1.1-3ubuntu5)
Paranoia level: max
Frame retries:  10
Cache defeat:   1 sector modelled (disc image, no drive cache)
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
Track 1 ripped and encoded successfully!
Summary:

  Integrated loudness:
    I:         -20.6 LUFS
    Threshold: -30.6 LUFS

  Loudness range:
    LRA:        20.0 LU
    Threshold: -49.4 LUFS
    LRA low:   -49.4 LUFS
    LRA high:  -29.4 LUFS

  Sample peak:
    Peak:       -0.0 dBFS

  True peak:
    Peak:       -0.0 dBFS

  Preemphasis:   none detected

  Properties:
    Duration:    00:03.00
    Samples:     132300
    Frames:      225
    Peak level:  99.7%
    True peak level: -0.0 dBFS
    Extraction speed:  17.1x
    Elapsed:            0.18 s
    Pregap LSN:  0 (duration: 00:04.00)
    Pregap length: 300 frames
    Pregap source: TOC
    Start LSN:   150
    End LSN:     374

  EAC CRC32:     D5F7BC20
  Secure re-read:  not attempted
  Accurip:       disabled
    Accurip v1:  00000000
    Accurip v2:  00000000
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
    creation_time:                 2026-08-03T02:20:23
    REPLAYGAIN_TRACK_GAIN:         2.64 dB
    R128_TRACK_GAIN:               1956
    REPLAYGAIN_TRACK_RANGE:        20.00 dB
    REPLAYGAIN_TRACK_PEAK:         0.998996
    REPLAYGAIN_REFERENCE_LOUDNESS: -18.00 LUFS

  Paranoia status counts:
    READ:          1298
    VERIFY:        18279
    SKIP:          128
    OVERLAP:       194

  File(s):
    Unknown disc (OMP2) [FLAC]/1 - Unknown track.flac

Track 2 ripped and encoded successfully!
Summary:

  Integrated loudness:
    I:         -24.0 LUFS
    Threshold: -34.0 LUFS

  Loudness range:
    LRA:         0.0 LU
    Threshold:   0.0 LUFS
    LRA low:     0.0 LUFS
    LRA high:    0.0 LUFS

  Sample peak:
    Peak:       -2.8 dBFS

  True peak:
    Peak:       -2.6 dBFS

  Preemphasis:   none detected

  Properties:
    Duration:    00:02.00
    Samples:     88200
    Frames:      150
    Peak level:  72.4%
    True peak level: -2.6 dBFS
    Extraction speed:  16.7x
    Elapsed:            0.12 s
    Pregap LSN:  300 (duration: 00:01.00)
    Pregap length: 75 frames
    Pregap source: TOC
    Start LSN:   375
    End LSN:     524

  EAC CRC32:     9869CDF5
  Secure re-read:  not attempted
  Accurip:       disabled
    Accurip v1:  956D1AF6
    Accurip v2:  956E22AE
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
    creation_time:                 2026-08-03T02:20:23
    REPLAYGAIN_TRACK_GAIN:         5.97 dB
    R128_TRACK_GAIN:               2808
    REPLAYGAIN_TRACK_RANGE:        0.00 dB
    REPLAYGAIN_TRACK_PEAK:         0.738850
    REPLAYGAIN_REFERENCE_LOUDNESS: -18.00 LUFS

  Paranoia status counts:
    READ:          928
    VERIFY:        13141
    SKIP:          91
    OVERLAP:       146

  File(s):
    Unknown disc (OMP2) [FLAC]/2 - Unknown track.flac

Track 3 ripped and encoded successfully!
Summary:

  Integrated loudness:
    I:         -40.9 LUFS
    Threshold: -50.9 LUFS

  Loudness range:
    LRA:         0.0 LU
    Threshold:   0.0 LUFS
    LRA low:     0.0 LUFS
    LRA high:    0.0 LUFS

  Sample peak:
    Peak:      -21.0 dBFS

  True peak:
    Peak:      -21.0 dBFS

  Preemphasis:   none detected

  Properties:
    Duration:    00:01.00
    Samples:     44100
    Frames:      75
    Peak level:  8.9%
    True peak level: -21.0 dBFS
    Extraction speed:  18.1x
    Elapsed:            0.06 s
    Pregap LSN:  unknown (sub-channel unreadable)
    Start LSN:   525
    End LSN:     599

  EAC CRC32:     9F27F613
  Secure re-read:  not attempted
  Accurip:       disabled
    Accurip v1:  84F0CFDC
    Accurip v2:  84F20136
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
    creation_time:                 2026-08-03T02:20:24
    REPLAYGAIN_TRACK_GAIN:         22.93 dB
    R128_TRACK_GAIN:               7150
    REPLAYGAIN_TRACK_RANGE:        0.00 dB
    REPLAYGAIN_TRACK_PEAK:         0.088933
    REPLAYGAIN_REFERENCE_LOUDNESS: -18.00 LUFS

  Paranoia status counts:
    READ:          431
    VERIFY:        6139
    SKIP:          53
    OVERLAP:       105

  File(s):
    Unknown disc (OMP2) [FLAC]/3 - Unknown track.flac

Album Loudness Summary:

  Integrated loudness:
    I:         -23.1 LUFS
    Threshold: -35.6 LUFS

  Loudness range:
    LRA:         0.1 LU
    Threshold: -52.5 LUFS
    LRA low:   -32.7 LUFS
    LRA high:  -32.6 LUFS

  Sample peak:
    Peak:       -0.0 dBFS

  True peak:
    Peak:       -0.0 dBFS

Paranoia status counts:
  READ:          2657
  VERIFY:        37559
  SKIP:          272
  OVERLAP:       445

Ripping errors: 0
Rip completed:  yes (3 of 3 tracks)
Ripping finished at 2026-08-03T02:20:24
Log FUN512: uHbEuAnDyCBcOAsS.etQ4vheCVY8y_cXumbTLttKEd74PPWZIVqx2FzhcI2Y.LaiEvthL2Ii57B.zCkmGSbBUQ
```

## Appendix 2 — regenerated provider contract

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
| `-v` | `--version` | Print the version number (-V accepted as an alias) |

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
- `-v`, `-V` and `--version` all print the version banner and exit 0.
  Upstream moved this flag from `-V` to `-v` when it replaced getopt with
  genopt after 0.9.3; a caller probing with `-V` against a stock 0.9.4 build
  gets exit 1 and `Unable to parse command line argument: -V`, which reads
  as "not installed" rather than "flag renamed". This fork accepts `-V`
  again. **Prefer `--version`** -- it has never changed and never will.
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
| `cyanrip_log.c:50` | `%s%s:` |
| `cyanrip_log.c:53` | `%s` |
| `cyanrip_log.c:63` | `CD-TEXT:        none reported by libcdio (absent, or unreadable by this driver)` |
| `cyanrip_log.c:68` | `CD-TEXT:        present (%s, %i disc %s, %i of %i tracks tagged)` |
| `cyanrip_log.c:87` | `Cache defeat:   not in use (paranoia disabled)` |
| `cyanrip_log.c:98` | `Cache defeat:   %i sector%s modelled (disc image, no drive cache)` |
| `cyanrip_log.c:103` | `Cache defeat:   %i sector%s modelled (drive cache size not probed)` |
| `cyanrip_log.c:122` | `%s%s` |
| `cyanrip_log.c:126` | `%lu` |
| `cyanrip_log.c:166` | `Pregap LSN:  %i (duration: %s)` |
| `cyanrip_log.c:168` | `Pregap length: %i frames` |
| `cyanrip_log.c:170` | `Pregap LSN:  unknown (sub-channel unreadable)` |
| `cyanrip_log.c:172` | `Pregap LSN:  unknown (sub-channel CRC mismatches)` |
| `cyanrip_log.c:174` | `Pregap LSN:  none` |
| `cyanrip_log.c:180` | `Pregap source: sub-channel (not signalled by TOC)` |
| `cyanrip_log.c:182` | `Pregap source: lead-in` |
| `cyanrip_log.c:184` | `Pregap source: TOC` |
| `cyanrip_log.c:187` | `Prepended:   %i frames of silence` |
| `cyanrip_log.c:188` | `Start LSN:   %i` |
| `cyanrip_log.c:190` | `(with offset: %i)` |
| `cyanrip_log.c:194` | `End LSN:     %i` |
| `cyanrip_log.c:201` | `Appended:    %i frames of silence` |
| `cyanrip_log.c:209` | `Preemphasis:` |
| `cyanrip_log.c:211` | `none detected` |
| `cyanrip_log.c:214` | `(deemphasis forced)` |
| `cyanrip_log.c:219` | `present (subcode)` |
| `cyanrip_log.c:221` | `present (TOC)` |
| `cyanrip_log.c:224` | `(deemphasis applied)` |
| `cyanrip_log.c:229` | `Properties:` |
| `cyanrip_log.c:232` | `Data bytes:  %i (%.2f Mib)` |
| `cyanrip_log.c:235` | `Frames:      %u` |
| `cyanrip_log.c:241` | `Duration:    %s` |
| `cyanrip_log.c:242` | `Samples:     %u` |
| `cyanrip_log.c:245` | `Peak level:  %.1f%%` |
| `cyanrip_log.c:249` | `True peak level: %.1f dBFS` |
| `cyanrip_log.c:252` | `Extraction speed:  %.1fx` |
| `cyanrip_log.c:254` | `Elapsed:            %.2f s` |
| `cyanrip_log.c:262` | `EAC CRC32:     %08X` |
| `cyanrip_log.c:264` | `(after %i rips)` |
| `cyanrip_log.c:271` | `Secure re-read:  converged after %i reads` |
| `cyanrip_log.c:274` | `Secure re-read:  did NOT converge after %i reads (repeat limit hit)` |
| `cyanrip_log.c:279` | `Secure re-read:  not attempted` |
| `cyanrip_log.c:283` | `Accurip:       %s` |
| `cyanrip_log.c:287` | `(max confidence: %i)` |
| `cyanrip_log.c:295` | `Accurip v1:  %08X` |
| `cyanrip_log.c:297` | `(accurately ripped, confidence %i)` |
| `cyanrip_log.c:299` | `(not found, either a new pressing, or bad rip)` |
| `cyanrip_log.c:303` | `Accurip v2:  %08X` |
| `cyanrip_log.c:314` | `Accurip 450: %08X` |
| `cyanrip_log.c:316` | `(match found, confidence %i, but a checksum of 0 is meaningless)` |
| `cyanrip_log.c:319` | `(matches Accurip DB, confidence %i, track is partially accurately ripped)` |
| `cyanrip_log.c:322` | `(not found)` |
| `cyanrip_log.c:329` | `Metadata:` |
| `cyanrip_log.c:339` | `%s:` |
| `cyanrip_log.c:351` | `CD-TEXT:` |
| `cyanrip_log.c:361` | `Paranoia status counts:` |
| `cyanrip_log.c:363` | `none` |
| `cyanrip_log.c:386` | `Embedded cover art:    %s: %s` |
| `cyanrip_log.c:389` | `Embedded cover art:    %s: %ix%i %s` |
| `cyanrip_log.c:393` | `File(s):` |
| `cyanrip_log.c:407` | `cyanrip %s (%s-g%s)` |
| `cyanrip_log.c:410` | `Invoked as:     %s` |
| `cyanrip_log.c:414` | `Drive used:     error retrieving drive info` |
| `cyanrip_log.c:416` | `Drive used:     %s %s (revision %s)` |
| `cyanrip_log.c:417` | `System device:  %s` |
| `cyanrip_log.c:419` | `Device model:   %s` |
| `cyanrip_log.c:420` | `Offset:         %c%i %s` |
| `cyanrip_log.c:422` | `%s%c%i %s` |
| `cyanrip_log.c:431` | `Speed:          %ix` |
| `cyanrip_log.c:433` | `Speed:          default (%s)` |
| `cyanrip_log.c:435` | `C2 errors:      %s` |
| `cyanrip_log.c:444` | `Encoder:        libavformat %i.%i.%i, libavcodec %i.%i.%i (%s)` |
| `cyanrip_log.c:449` | `Paranoia level: %s` |
| `cyanrip_log.c:453` | `Paranoia level: %i` |
| `cyanrip_log.c:454` | `Frame retries:  %i` |
| `cyanrip_log.c:456` | `HDCD decoding:  %s` |
| `cyanrip_log.c:458` | `Album Art:      %s` |
| `cyanrip_log.c:462` | `%s%s%s%s%s` |
| `cyanrip_log.c:470` | `Outputs:` |
| `cyanrip_log.c:476` | `Disc tracks:    %i` |
| `cyanrip_log.c:477` | `Tracks to rip:  %s` |
| `cyanrip_log.c:480` | `%i%s` |
| `cyanrip_log.c:494` | `AccurateRip:    %s` |
| `cyanrip_log.c:500` | `Total time:     %s` |
| `cyanrip_log.c:526` | `Tracks ripped accurately: %i/%i` |
| `cyanrip_log.c:528` | `Tracks ripped partially accurately: %i/%i` |
| `cyanrip_log.c:538` | `Ripping errors: %i` |
| `cyanrip_log.c:545` | `Rip completed:  no (interrupted by user, %i of %i tracks)` |
| `cyanrip_log.c:548` | `Rip completed:  yes (%i of %i tracks)` |
| `cyanrip_log.c:551` | `Ripping finished at %s` |
| `cyanrip_main.c:184` | `No device specified and unable to get default device!` |
| `cyanrip_main.c:192` | `Unable to open device: %s` |
| `cyanrip_main.c:201` | `Unable to init cddap context!` |
| `cyanrip_main.c:203` | `cdio: \"%s\"` |
| `cyanrip_main.c:214` | `Opening drive...` |
| `cyanrip_main.c:217` | `Unable to open device!` |
| `cyanrip_main.c:226` | `Device does not support changing speeds!` |
| `cyanrip_main.c:234` | `cdio error: %s` |
| `cyanrip_main.c:243` | `Unable to init paranoia!` |
| `cyanrip_main.c:272` | `Invalid number of tracks: %i!` |
| `cyanrip_main.c:295` | `CDIO returned invalid track %i end LSN` |
| `cyanrip_main.c:498` | `Frame read failed!` |
| `cyanrip_main.c:575` | `Loading data for track %i...` |
| `cyanrip_main.c:582` | `Stopping, offset finding incomplete!` |
| `cyanrip_main.c:590` | `Data loaded, searching for offsets...` |
| `cyanrip_main.c:599` | `Nothing found for track %i%s` |
| `cyanrip_main.c:604` | `Offset of %c%i found in track %i%s` |
| `cyanrip_main.c:609` | `Offset of %c%i confirmed (confidence: %i) in track %i%s` |
| `cyanrip_main.c:613` | `New offset of %c%i found at track %i, scrapping old offset of %c%i%s` |
| `cyanrip_main.c:627` | `No track had AccuRip entry, cannot find offset!` |
| `cyanrip_main.c:629` | `No track was long enough, unable to find drive offset!` |
| `cyanrip_main.c:631` | `Was not able to find drive offset with a radius of %i frames, trying again with a larger radius...` |
| `cyanrip_main.c:637` | `Drive offset of %c%i found (confidence: %i)!` |
| `cyanrip_main.c:667` | `Unable to read track %i subchannel info!` |
| `cyanrip_main.c:683` | `Track %i is data:` |
| `cyanrip_main.c:740` | `Error in decoding/sending frame: %s` |
| `cyanrip_main.c:752` | `Drive media changed, stopping!` |
| `cyanrip_main.c:783` | `Stopping, ripping incomplete!` |
| `cyanrip_main.c:901` | `Done; (%i out of %i matches for current checksum %08X)` |
| `cyanrip_main.c:907` | `Done; (no matches found, but hit repeat limit of %i)` |
| `cyanrip_main.c:923` | `Repeating ripping (%i out of %i matches for current checksum %08X)` |
| `cyanrip_main.c:938` | `Error in encoding: %s` |
| `cyanrip_main.c:954` | `Error sending flush signal to encoders: %s` |
| `cyanrip_main.c:961` | `Track %i ripped and encoded with errors.` |
| `cyanrip_main.c:963` | `Track %i ripped and encoded successfully!` |
| `cyanrip_main.c:1045` | `Gaps:` |
| `cyanrip_main.c:1050` | `%i frame gap between lead-in and track 1 pregap, merging into pregap` |
| `cyanrip_main.c:1057` | `%i frame unmarked gap between lead-in and track 1, marking as a pregap` |
| `cyanrip_main.c:1079` | `%i frame pregap in track %i,` |
| `cyanrip_main.c:1086` | `unmerged` |
| `cyanrip_main.c:1088` | `merging into track %i` |
| `cyanrip_main.c:1094` | `dropping` |
| `cyanrip_main.c:1100` | `merging` |
| `cyanrip_main.c:1107` | `splitting off into a new track, number %i` |
| `cyanrip_main.c:1148` | `%i frame discontinuity between tracks %i and %i,` |
| `cyanrip_main.c:1153` | `padding track %i` |
| `cyanrip_main.c:1156` | `ignoring` |
| `cyanrip_main.c:1164` | `%i frame gap between last track and lead-out, padding track` |
| `cyanrip_main.c:1229` | `Can't init signal handler!` |
| `cyanrip_main.c:1449` | `Invalid paranoia level %i must be between 0 and %i!` |
| `cyanrip_main.c:1462` | `Invalid max coverart size %i (must be 250, 500, 1200 or -1)` |
| `cyanrip_main.c:1474` | `Invalid sanitation method %s` |
| `cyanrip_main.c:1486` | `Invalid release index %i!` |
| `cyanrip_main.c:1495` | `Invalid discnumber %i` |
| `cyanrip_main.c:1502` | `Invalid totaldiscs %i` |
| `cyanrip_main.c:1506` | `discnumber %i is larger than totaldiscs %i` |
| `cyanrip_main.c:1519` | `Supported output codecs:` |
| `cyanrip_main.c:1527` | `Invalid format \"%s\"` |
| `cyanrip_main.c:1532` | `Duplicated format \"%s\"` |
| `cyanrip_main.c:1547` | `Duplicated rip idx %i` |
| `cyanrip_main.c:1561` | `Invalid track idx for pregap: %i` |
| `cyanrip_main.c:1567` | `Missing pregap action` |
| `cyanrip_main.c:1575` | `Invalid pregap action %s` |
| `cyanrip_main.c:1606` | `No cover art location specified for \"%s\"` |
| `cyanrip_main.c:1615` | `Invalid track idx for cover art: %i` |
| `cyanrip_main.c:1621` | `Cover art already specified for track idx %i!` |
| `cyanrip_main.c:1633` | `Cover art \"%s\" already specified!` |
| `cyanrip_main.c:1639` | `Too many cover arts specified!` |
| `cyanrip_main.c:1649` | `Directory name scheme must contain {format} with multiple output formats!` |
| `cyanrip_main.c:1654` | `-J (only generate a CUE sheet) cannot be used with -I (only print info)!` |
| `cyanrip_main.c:1670` | `Searching for drive offset, enabling AccuRip and disabling MusicBrainz and Cover art fetching...` |
| `cyanrip_main.c:1678` | `Offset is unset! To continue with an offset of 0, run with -s 0!` |
| `cyanrip_main.c:1758` | `MusicBrainz URL:%s` |
| `cyanrip_main.c:1802` | `Error reading album tags: %s` |
| `cyanrip_main.c:1832` | `Log(s) will be written to:` |
| `cyanrip_main.c:1840` | `CUE files will be written to:` |
| `cyanrip_main.c:1872` | `Invalid track number %i, list has %i tracks!` |
| `cyanrip_main.c:1888` | `Error reading track tags: %s` |
| `cyanrip_main.c:1942` | `Cover art destination(s):` |
| `cyanrip_main.c:1977` | `WARNING: tracks %i and %i resolve to the same file \"%s\", one will overwrite the other!` |
| `cyanrip_main.c:1988` | `Tracks:` |
| `cyanrip_main.c:1998` | `Track %i info:` |
| `cyanrip_main.c:2016` | `Error initializing decoder: %s` |
| `cyanrip_main.c:2025` | `Error initializing encoder: %s` |
| `cyanrip_main.c:2059` | `Error encoding: %s` |
| `cyanrip_main.c:2079` | `Invalid rip index %i, list has %i tracks!` |
| `cyanrip_main.c:2161` | `Error ripping: %s` |
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

**251 distinct stable lines.**

Field order within a block is fixed and is part of the contract. The golden
reference log in the handshake package is the authoritative example.

## P3 - Unstable lines: reworded without a handshake

Do not parse these. Most are stdout-only and never reach the logfile at all.

| File:line | Line | Reaches logfile? |
|---|---|---|
| `cyanrip_encode.c:105` | `%s folder: [%s] extension: %s%s` | **no, stdout only** |
| `cyanrip_encode.c:125` | `Encoder for %s not compiled in ffmpeg!` | **no, stdout only** |
| `cyanrip_main.c:459` | `Still reading track %i at LSN %li - %` | **no, stdout only** |
| `cyanrip_main.c:483` | `Track %i resumed after %` | **no, stdout only** |
| `cyanrip_main.c:801` | `\r` | **no, stdout only** |
| `cyanrip_main.c:867` | `%s` | **no, stdout only** |
| `cyanrip_main.c:948` | `Flushing encoders...` | **no, stdout only** |
| `cyanrip_main.c:990` | `Force quitting` | **no, stdout only** |
| `cyanrip_main.c:993` | `\rTrying to quit` | **no, stdout only** |
| `cyanrip_main.c:1387` | `Log \"%s\" checksum valid.` | **no, stdout only** |
| `cyanrip_main.c:1390` | `Log \"%s\" checksum mismatch, the file has been modified!` | **no, stdout only** |
| `cyanrip_main.c:1394` | `Log \"%s\" has data after the checksum, the file has been modified!` | **no, stdout only** |
| `cyanrip_main.c:1398` | `No FUN512 checksum found in \"%s\"!` | **no, stdout only** |
| `cyanrip_main.c:1402` | `Couldn't read \"%s\"!` | **no, stdout only** |

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

Every string reachable on a failure path. Use this to derive error matching
rather than guessing prefixes.

**Evidence** says why each string is here, and is reported rather than folded
into a bare verdict so you can see which entries rest on the weaker test:

- `control flow` - the call is followed by `return 1`, a non-zero `exit()`,
  `return AVERROR(...)`, `total_error_count++`, or `goto fail`. Does not
  depend on how the message is worded.
- `wording` - the message begins like a diagnostic, but no failure exit was
  found near it. Either the exit is further away than the search window, or
  the message is a warning that does not end the run. **Treat these as
  possibly non-fatal.**
- `both` - the two agree.
- `goto end` / `wording + goto end` - the call is followed by `goto end`,
  which in `cyanrip_main.c` is *both* the ordinary success cleanup and the
  route several genuine aborts take (`Offset is unset!` leaves that way).
  It is reported as its own class because calling it fatal would file
  success lines as failures, and calling it non-fatal would drop real
  aborts. **Neither of us can settle these from the source alone; they need
  a run to classify.**

The search stops at the next `if`/`for`/`while`/`switch` or the next log
call, so a message is only credited with an exit that is its own. Without
that cut, `Opening drive...` reads as fatal because the *next* statement's
if-block returns `AVERROR`.

| File:line | Message | Evidence | Reaches logfile? |
|---|---|---|---|
| `accurip.c:97` | `Unable to get AccuRIP DB data: missing CDDB ID!` | wording + goto end | yes |
| `accurip.c:129` | `Unable to get AccuRIP DB data: missing entry!` | wording + goto end | yes |
| `accurip.c:137` | `Unable to get AccuRIP DB data: %s%s` | wording | yes |
| `accurip.c:140` | `Unable to get AccuRIP DB data: %s!` | wording + goto end | yes |
| `accurip.c:176` | `AccuRIP DB data error, got unexpected number of bytes!` | goto end | yes |
| `coverart.c:51` | `Unable to init lavf context: %s!` | both | yes |
| `coverart.c:57` | `Unable to alloc stream!` | both | yes |
| `coverart.c:70` | `Couldn't open %s for writing: %s!` | both | yes |
| `coverart.c:82` | `Couldn't write header: %s!` | both | yes |
| `coverart.c:92` | `Error writing picture packet: %s!` | both | yes |
| `coverart.c:97` | `Error writing trailer: %s!` | both | yes |
| `coverart.c:177` | `Unable to get cover art \"%s\": not found!` | wording + goto end | yes |
| `coverart.c:186` | `Unable to get cover art \"%s\": %s%s!` | wording | yes |
| `coverart.c:189` | `Unable to get cover art \"%s\": %s!` | wording + goto end | yes |
| `coverart.c:262` | `Unable to open \"%s\": %s!` | wording + goto end | yes |
| `coverart.c:269` | `Unable to get cover image info: %s!` | wording + goto end | yes |
| `coverart.c:299` | `Error demuxing cover image: %s!` | wording + goto end | yes |
| `cue_writer.c:39` | `Couldn't open path \"%s\" for writing: %s!Invalid folder name? Try -D <folder>.` | both | yes |
| `cyanrip_encode.c:361` | `Error creating filter source: %s!` | both | yes |
| `cyanrip_encode.c:372` | `Error creating filter sink: %s!` | both | yes |
| `cyanrip_encode.c:386` | `Error setting filter sample format: %s!` | both | yes |
| `cyanrip_encode.c:394` | `Error setting filter channel layout: %s!` | both | yes |
| `cyanrip_encode.c:403` | `Error setting filter sample rate: %s!` | both | yes |
| `cyanrip_encode.c:437` | `Error initializing filter sink: %s!` | both | yes |
| `cyanrip_encode.c:471` | `Error parsing filter graph: %s!` | both | yes |
| `cyanrip_encode.c:477` | `Error configuring filter graph: %s!` | both | yes |
| `cyanrip_encode.c:536` | `Error pushing frame to FIFO: %s!` | wording | yes |
| `cyanrip_encode.c:555` | `Error filtering frame: %s!` | both | yes |
| `cyanrip_encode.c:633` | `Error allocating frame!` | both | yes |
| `cyanrip_encode.c:645` | `Error allocating frame: %s!` | both | yes |
| `cyanrip_encode.c:776` | `Could not alloc swr context!` | wording | yes |
| `cyanrip_encode.c:794` | `Could not init swr context!` | wording | yes |
| `cyanrip_encode.c:969` | `Error while encoding: %s!` | both | yes |
| `cyanrip_encode.c:991` | `Error encoding: %s!` | both | yes |
| `cyanrip_encode.c:1022` | `Error pushing packet to FIFO: %s!` | both | yes |
| `cyanrip_encode.c:1029` | `Error writing packet: %s!` | both | yes |
| `cyanrip_encode.c:1059` | `Error writing to file: %s!` | both | yes |
| `cyanrip_encode.c:1182` | `Codec not found (not compiled in lavc?)!` | control flow | yes |
| `cyanrip_encode.c:1191` | `Unable to init output avctx!` | both | yes |
| `cyanrip_encode.c:1202` | `Could not open output codec context!` | both | yes |
| `cyanrip_encode.c:1209` | `Couldn't copy codec params!` | both | yes |
| `cyanrip_encode.c:1216` | `Couldn't open %s: %s! Invalid folder name? Try -D <folder>.` | both | yes |
| `cyanrip_main.c:184` | `No device specified and unable to get default device!` | both | yes |
| `cyanrip_main.c:192` | `Unable to open device: %s` | both | yes |
| `cyanrip_main.c:201` | `Unable to init cddap context!` | wording | yes |
| `cyanrip_main.c:203` | `cdio: \"%s\"` | control flow | yes |
| `cyanrip_main.c:217` | `Unable to open device!` | both | yes |
| `cyanrip_main.c:226` | `Device does not support changing speeds!` | control flow | yes |
| `cyanrip_main.c:243` | `Unable to init paranoia!` | both | yes |
| `cyanrip_main.c:272` | `Invalid number of tracks: %i!` | both | yes |
| `cyanrip_main.c:295` | `CDIO returned invalid track %i end LSN` | control flow | yes |
| `cyanrip_main.c:582` | `Stopping, offset finding incomplete!` | wording + goto end | yes |
| `cyanrip_main.c:667` | `Unable to read track %i subchannel info!` | wording | yes |
| `cyanrip_main.c:740` | `Error in decoding/sending frame: %s` | both | yes |
| `cyanrip_main.c:752` | `Drive media changed, stopping!` | both | yes |
| `cyanrip_main.c:783` | `Stopping, ripping incomplete!` | wording | yes |
| `cyanrip_main.c:938` | `Error in encoding: %s` | wording + goto end | yes |
| `cyanrip_main.c:954` | `Error sending flush signal to encoders: %s` | wording | yes |
| `cyanrip_main.c:990` | `Force quitting` | control flow | **no, stdout only** |
| `cyanrip_main.c:1402` | `Couldn't read \"%s\"!` | both | **no, stdout only** |
| `cyanrip_main.c:1449` | `Invalid paranoia level %i must be between 0 and %i!` | both | yes |
| `cyanrip_main.c:1462` | `Invalid max coverart size %i (must be 250, 500, 1200 or -1)` | both | yes |
| `cyanrip_main.c:1474` | `Invalid sanitation method %s` | both | yes |
| `cyanrip_main.c:1486` | `Invalid release index %i!` | both | yes |
| `cyanrip_main.c:1495` | `Invalid discnumber %i` | both | yes |
| `cyanrip_main.c:1502` | `Invalid totaldiscs %i` | both | yes |
| `cyanrip_main.c:1506` | `discnumber %i is larger than totaldiscs %i` | control flow | yes |
| `cyanrip_main.c:1527` | `Invalid format \"%s\"` | both | yes |
| `cyanrip_main.c:1532` | `Duplicated format \"%s\"` | control flow | yes |
| `cyanrip_main.c:1547` | `Duplicated rip idx %i` | control flow | yes |
| `cyanrip_main.c:1561` | `Invalid track idx for pregap: %i` | both | yes |
| `cyanrip_main.c:1567` | `Missing pregap action` | both | yes |
| `cyanrip_main.c:1575` | `Invalid pregap action %s` | both | yes |
| `cyanrip_main.c:1606` | `No cover art location specified for \"%s\"` | both | yes |
| `cyanrip_main.c:1615` | `Invalid track idx for cover art: %i` | both | yes |
| `cyanrip_main.c:1621` | `Cover art already specified for track idx %i!` | control flow | yes |
| `cyanrip_main.c:1633` | `Cover art \"%s\" already specified!` | control flow | yes |
| `cyanrip_main.c:1639` | `Too many cover arts specified!` | control flow | yes |
| `cyanrip_main.c:1649` | `Directory name scheme must contain {format} with multiple output formats!` | control flow | yes |
| `cyanrip_main.c:1654` | `-J (only generate a CUE sheet) cannot be used with -I (only print info)!` | both | yes |
| `cyanrip_main.c:1678` | `Offset is unset! To continue with an offset of 0, run with -s 0!` | goto end | yes |
| `cyanrip_main.c:1802` | `Error reading album tags: %s` | both | yes |
| `cyanrip_main.c:1872` | `Invalid track number %i, list has %i tracks!` | both | yes |
| `cyanrip_main.c:1888` | `Error reading track tags: %s` | both | yes |
| `cyanrip_main.c:1910` | `%s` | goto end | yes |
| `cyanrip_main.c:2016` | `Error initializing decoder: %s` | both | yes |
| `cyanrip_main.c:2025` | `Error initializing encoder: %s` | both | yes |
| `cyanrip_main.c:2059` | `Error encoding: %s` | wording + goto end | yes |
| `cyanrip_main.c:2079` | `Invalid rip index %i, list has %i tracks!` | both | yes |
| `cyanrip_main.c:2161` | `Error ripping: %s` | wording + goto end | yes |
| `discid.c:31` | `Unable to init SHA for DiscID: %s!` | wording | yes |
| `musicbrainz.c:116` | `Invalid disc number %i, release only has %i CDs` | both | yes |
| `musicbrainz.c:121` | `Got empty medium list.` | control flow | yes |
| `musicbrainz.c:193` | `Could not connect to MusicBrainz.` | both | yes |
| `musicbrainz.c:201` | `Missing DiscID!` | wording | yes |
| `musicbrainz.c:224` | `Error fetching/requesting/auth, this shouldn't happen.` | wording + goto end | yes |
| `musicbrainz.c:299` | `Invalid release index %i specified, only have %i releases!` | wording | yes |
| `musicbrainz.c:366` | `Unable to find release info for this CD, and metadata hasn't been manually added!` | wording | yes |
| `musicbrainz.c:370` | `Unable to find metadata for this CD, but metadata has been manually specified, continuing.` | wording | yes |
| `naming.c:123` | `Error parsing string: %s!` | wording | yes |
| `naming.c:215` | `Invalid scheme syntax, unterminated \"{\"!` | both | yes |
| `naming.c:229` | `Invalid scheme syntax, no \"#\"!` | both | yes |
| `naming.c:243` | `Invalid scheme syntax, no terminating \"#\"!` | both | yes |
| `naming.c:259` | `Invalid condition syntax!` | both | yes |

**104 distinct strings.** By evidence: 60 both, 13 control flow, 15 wording, 3 goto end, 13 wording + goto end.

The `control flow` and `both` rows total 73 strings proven reachable on a
failure path without reference to their wording. That subset is the one to
build a hard failure classifier on.

