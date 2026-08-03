# Platterpus → cyanrip fork · Round 5

*2026-08-03. Platterpus v0.6.3 (unreleased — held pending this round).*

**What I need back:** one markdown file matching *The return-file spec* at the end.
I will verify every claim in it against the real parser and the committed fixtures,
then send a short verification file. **Neither project releases until both
directions are done.**

**Why this round exists.** Two reasons, and per R9 either alone is enough:

1. **Our argv surface changed.** We now pass `-c disc/totaldiscs`. That is a flag
   we never sent before, so your provider contract's argv half needs to cover it
   and mine has been regenerated to declare it.
2. **A real disc was ripped on the rig — with *stock* cyanrip 0.9.3, not the
   fork.** The container had never been switched. That is our fault and it is now
   fixed in software rather than in a note (§3), but it means **both hardware
   gates from round 4 are still open**, and it also produced a large pile of
   real-hardware evidence about a *stock* run, which is useful to you in its own
   right (§5, §6).

Everything below is measured, and each item names the file or the source line it
came from. Where I am reasoning rather than measuring, I say so.

---

## Corrections

**Nothing of yours to correct.** Stated explicitly, per our own rule.

**One of mine, and it is the important one in this file.** In round 4 §1 I told
you your 88-string fatal inventory was *"VERIFIED INDEPENDENTLY — same count,
same miss"*, having extracted it to a fixture and run all 88 through my
surfacing pattern. That verification was sound as far as it went and its *scope*
was wrong: I verified **the strings you gave me**, and called it verification of
**your inventory**. Those are different claims. Re-deriving the inventory from
your source this round found two strings your generator never emitted — so the
right verdict for round 4 was "your list is internally consistent and I have not
independently derived it", which is weaker and true.

This is the same error shape as the §H2 pre-gap mistake we *both* made: reasoning
from a true measurement of the wrong artifact. I measured your description of
your behaviour, not your behaviour.

## Confirmations

Your claims I re-checked this round, and how. Only the ones I actually touched —
this is not a re-run of round 4.

| Your claim | Verdict | How |
|---|---|---|
| `-c disc/totaldiscs` sets `disc` and `totaldiscs` as **separate integer keys** | **VERIFIED (read from source at the pin)** | `cyanrip_main.c:1708-1712`, `av_dict_set_int` twice. This is the whole basis for §2, so I read it rather than inferred it from the help text |
| Argument-parse fatals are **stdout-only** | **RE-CONFIRMED, and it now covers 2 more strings** | The two in §1 are both argument validation, before the logfile exists — consistent with your Q5, and the reason they must be captured from stdout |
| Exit codes are `{0, 1}` | **CONSISTENT with a real run** | Tonight's rip: exit `0` with two tracks unverified. See Q4 — I want that in writing rather than inferred |
| Pin `a04a94b` is the tip of `platterpus-fork` | **VERIFIED** | Fetched the branch; `a04a94b` is HEAD, above `60563d6` / `f59a385` / `a835052` / `ec406ac` |
| The banner is `cyanrip <version> (<PROJECT_FORK_ID>-g<short sha>)` | **VERIFIED (read from source)** | `cyanrip_log.c:265` and `cyanrip_main.c:1215`, both `"cyanrip %s (%s-g%s)"`. Our wizard's post-install verification depends on this exact shape, so it is now load-bearing rather than descriptive |
| `PROJECT_FORK_ID` is `platterpus-fork`, separate from the version | **VERIFIED (read from source)** | `meson.build`: `conf.set_quoted('PROJECT_FORK_ID', 'platterpus-fork')` with `version: '0.9.4-rc1'` unchanged from upstream. Your comment there explains exactly why, and it is correct — which is precisely why our dialog needed fixing rather than your version string |
| `vcs_tag` falls back to `release` for a tarball build | **VERIFIED (read from source)** | `src/meson.build`, `fallback: 'release'`. Still classified as fork when combined with `platterpus-fork`, per round 4 §Q2/H3 |
| The fork's meson dependency set | **VERIFIED and now depended on** | Read off `src/meson.build` at the pin; all nine `dependency()` modules are in the wizard's install list, each as a `pkgconfig()` provide |

---

## 1. Your generated fatal inventory is missing two strings, and the reason is systematic

**Found by reading `src/cyanrip_main.c` at pin `a04a94b`** rather than reading
your round-4 Appendix 2 — which I only did because implementing `-c` required
knowing what it refuses.

| File:line | Literal | In your 88-string inventory? |
|---|---|---|
| `cyanrip_main.c:1439` | `discnumber %i is larger than totaldiscs %i` | **No** |
| `cyanrip_main.c:1554` | `Cover art already specified for track idx %i!` | **No** |

Both `return 1`. Both are argument validation, so by your own Q5 they are
**stdout-only** — printed before the logfile exists — which is exactly the class
you flagged as load-bearing for me.

**The cause is not two typos.** In both calls the format string sits on a
*continuation line*:

```c
                cyanrip_log(ctx, 0,
                            "discnumber %i is larger than totaldiscs %i\n",
                            discnumber, totaldiscs);
```

A generator that scans for a string literal on the same line as `cyanrip_log(` /
`fprintf(` cannot see either one. **I swept your whole `src/` tree for that
shape** — every `cyanrip_log`/`fprintf` call whose line contains no `"`, then the
first literal in the following five lines, normalised `%…` conversions, diffed
against your inventory. Result: **exactly these two, and nothing else.** So the
inventory is 88 → **90**, and the fix to your generator is bounded.

**Ask:** regenerate with continuation-line calls included, and confirm 90 is the
whole set (or tell me the number you get — if it differs from 90 the
disagreement is the bug report, per our own J1 reasoning).

**Already done on my side.** Both prefixes are in the surfacing pattern, both
strings are appended to `tests/fixtures/cyanrip_fatal_messages.tsv` clearly
marked as *derived by us at the pin, not from your file*, and the standing test
is **90/90**. The first one matters immediately: it is the fatal I would hit if
the range check on `-c` ever let a bad disc position through, and shipping the
flag without surfacing its refusal would be capture-without-surfacing again.

---

## 2. `-c disc/totaldiscs` — a flag we now pass, and why

This is the argv change that opens the round.

**The defect it fixes is ours.** We were folding the disc position into the `-a`
album-tag string as `disc=2/3`. You pass an `-a` value through verbatim; ffmpeg's
Vorbis-comment writer maps the key `disc` to `DISCNUMBER`; so the FLAC carried
the single tag `DISCNUMBER=2/3` — the **ID3** convention, not the Vorbis one —
and the disc total was lost outright.

**Your `-c` is the right seam and we should have been using it.** Read off
`cyanrip_main.c`:

```c
GEN_OPT_ONE(opts_list, char *,  disc, "c", 1, 1, NULL, 0, 0,
            "Multi-disc tag: disc/totaldiscs");
...
if (discnumber)
    av_dict_set_int(&ctx->meta, "disc", discnumber, 0);
if (totaldiscs)
    av_dict_set_int(&ctx->meta, "totaldiscs", totaldiscs, 0);
```

Two separate integer keys — the Vorbis-correct shape — and it also feeds your
`{if #totaldiscs# > #1# CD|disc|}` log and cue name schemes, so two discs of a
set ripped into one folder stop both trying to write `Album.log`. (Safe for us:
we locate your log by globbing `*.log` in the rip folder, never by
reconstructing its name. Confirmed at both of our call sites.)

**What we send:**

| Case | We pass | Reasoning |
|---|---|---|
| Multi-disc, position known | `-c 2/3` | the whole point |
| Single disc | `-c 1/1` | EAC and Picard both write `DISCNUMBER`/`TOTALDISCS` on a one-disc album; emitting them keeps a library uniform instead of the field appearing only on box sets. Your name schemes guard on `totaldiscs > 1`, so **no filenames change** — please confirm §Q1 |
| `number < 1`, `total < 1`, or `number > total` | **nothing** | see below |

**Range-checked at the argv chokepoint, before it becomes an argument.** You
refuse the *entire rip* on a bad `-c` — `Invalid discnumber`, `Invalid
totaldiscs`, `discnumber N is larger than totaldiscs M`, all `return 1` before a
sector is read. Our disc position comes from MusicBrainz, i.e. from something
other than the disc in the drive, which is precisely the category our own rules
require be range-checked. This is the same defect shape as the out-of-range `-t`
that killed a real rip in two seconds: an out-of-range value we could have
caught, handed to a tool that treats it as fatal. An unusable position is dropped
and logged. Losing a tag is survivable; losing the rip is not.

---

## 3. What we fixed on our side (drop these from your list)

- **We were not running your fork at all.** The container was still on the COPR
  `cyanrip 0.9.3`, and nothing in the app said so at the point a user would look.
  Fixed properly rather than with a note: the one-time setup wizard now installs
  the build deps, clones the fork, **detaches onto the pin**, compiles, installs
  to `/usr/local/bin/cyanrip`, re-points the `~/.local/bin` export at it, and then
  **verifies the installed binary prints `platterpus-fork-g<pin>`** — a build that
  produced something unexpected fails the step instead of leaving a mystery binary
  on the ripping path. It runs *after* the stock install, so a failed build leaves
  a working ripper rather than none.
  - Build deps are read off **your `src/meson.build` at the pin**, requested as
    `pkgconfig(<module>)` virtual provides rather than package names, so
    Fedora's `ffmpeg-free-devel` and RPM Fusion's `ffmpeg-devel` (which conflict
    and cannot both be named) both satisfy it.
  - A test reads our newest **closed** handshake round and asserts the pin the
    wizard builds is the pin the record approved. The pin cannot drift from the
    round silently.
- **The dependency dialog now names the build, not just the version.** It showed
  `cyanrip 0.9.3` and `0 missing/needs-attention` — every word true, the whole
  message misleading, and the reason the fork install went unnoticed for a
  release. Your deliberate choice to keep upstream's version string byte-for-byte
  is exactly right and it means a version number can *never* answer "is this the
  fork?", so the build tag is now surfaced next to it, tri-state, with a warning
  icon and a fix.
- **Four of our own audit checks could run and say nothing.** The first
  real-hardware run of our embedded `self_check` listed 8 checks run, 0 skipped,
  and 6 findings — `pregap` and `argv_agreement` were silent *because a stock rip
  has neither the rows nor the `Invoked as:` line they read*. Auditing for it
  found two more. Each now reports why it has nothing, and there is a structural
  floor so a future silent check is impossible rather than discouraged. Your Q10
  point — the footer is the only completeness signal — is what made this visible.

---

## 4. Requirements for the pin (unchanged from round 4, restated as binding)

1. The fork identifies itself in the version banner parenthetical, on `--version`
   **and** on line 1 of every rip logfile. We classify tri-state and never report
   "unmodified upstream" for a tag we merely do not recognise.
2. `-N` must keep working exactly as documented: no network, no interactive
   prompt, ever. It is the single reason our rip cannot hang on an ambiguous disc.
3. Exit codes stay `{0, 1}`. A third value must arrive as a handshake item, not
   as a surprise. Our standing test asserts your P4 still says exactly two.
4. Argument-parse errors stay on **stdout** and remain diagnosable in words.
5. Any change to a line in your P2 *stable* list is a handshake event.
6. No audio-path change without saying so explicitly.

---

## 5. Real-hardware evidence from a full stock run

**Disc:** The Police — *Every Breath You Take: The Classics*, 14 tracks,
59:42.354, pressed CD. **Drive:** PIONEER BD-RW BDR-209D 1.51, offset +667,
overread +2 frames, C2 unsupported, speed reported unchangeable. **Binary:**
`cyanrip 0.9.3 (release)` — stock. **Exit code: 0.**

Sent to you because a stock run is still your code for everything except the
fork-only rows, and three of these numbers are contract questions rather than
observations.

**argv exactly as spawned** (this is the *re-rip* pass, `-l 3,5`; the first pass
was identical without `-l`):

```
/home/rmccann/.local/bin/cyanrip -d /dev/sr0 -s 667 -o flac -r 5 -Z 2 -l 3,5 -N
  -a album=…:album_artist=The Police:date=1995-09-12:catalognumber=31454 0380 2:
     label=A&M Records:musicbrainz_albumid=d14a7546-…
  -t 1=title=Roxanne:artist=The Police:isrc=GBAAM0201086
  … (one -t per track) …
  -D {album_artist}/{album} -F {track} - {title}
```

**Whole-disc paranoia counters, verbatim:**

```
  READ:          22133
  VERIFY:        1749
  FIXUP_ATOM:    49
  OVERLAP:       481
Ripping errors: 0
```

**AccurateRip:** 12/14 exact at confidence 200; tracks 3 and 5 matched only the
`+450` offset-variant pressing. Track 5 was re-ripped and came back stable
(`E0036697`, identical across 3 secure re-reads). **Track 3 did not read
identically even after an automatic re-rip.**

**Two long stalls,** from our own log with wall-clock stamps:

```
19:49:47 WARNING rip stalled: no forward progress for 3m 0s at 21.7% (track 3)
20:09:55 WARNING rip stalled: no forward progress for 3m 0s at 35.5% (track 5)
```

Those are the two tracks that later failed to verify exactly. First pass
17:52:32 → 18:42:42 (50 min for 59:42 of audio); re-rip pass ran to 19:13:45.

**Findings I want your read on, in §Q.**

---

## 6. Wishlist — ordered by what tonight's evidence justifies

Each item says what it would let us stop guessing. None is a request to change
audio.

### W1. Per-track paranoia counters (highest value)

You print `READ / VERIFY / FIXUP_ATOM / OVERLAP` **once, for the whole disc**.
Tonight the disc totals were dominated by two tracks, and we know *which* two
only because our stall detector timestamped them and AccurateRip disagreed
afterwards. A per-track block — even just the four counters in the existing
per-track `Properties:` section — turns "this disc needed 1749 verifies" into
"track 3 needed 1400 of them", which is the difference between a note in a report
and a sentence telling a user to clean one specific track's region of the disc.

EAC's per-track *quality* percentage is the closest analogue, and this would be
better than it, because it is raw counts rather than a derived score.

### W2. A liveness/heartbeat line while a read is stuck

Two three-minute windows with **no output at all**. Our stall detector works by
the *absence* of progress lines, which means it cannot distinguish "grinding on a
hard sector, making progress internally" from "wedged in an ioctl and never
coming back". Those need different words to a user and, on cancel, different
escalation.

A single line every N seconds while a read is retrying — `Retrying LSN 49920,
attempt 3/5` or even just a monotonic `still reading track 3` — would settle it.
Stderr or stdout, either is fine; we merge them.

### W3. Say which encoder wrote the audio, in the log

Our FLAC files carry the vendor string `Lavf62.12.102`, because you encode
in-process via libavformat. That is correct and it is *invisible in the log*: the
archival record names the ripper and not the encoder, so two rips made against
different ffmpeg majors are indistinguishable from the log alone. A
`FLAC encoder: <libavformat version>` row beside the existing header rows would
close it. (We already print our own `flac`/`metaflac` versions in the
EAC-compatible log; yours is the one that actually produced the stream.)

### W4. Tag-key casing is mixed in the output, by construction

Not a bug, and worth documenting or normalising. In one file we get:

```
TRACKNUMBER=1          ← ffmpeg mapped your `track`
ALBUMARTIST=The Police ← ffmpeg mapped your `album_artist`
title=Roxanne          ← passed through as-is
album=…                ← passed through as-is
tracktotal=14          ← passed through as-is
DESCRIPTION=cyanrip 0.9.3  ← ffmpeg mapped your `comment`
```

Vorbis field names are case-insensitive per spec, so nothing is broken. But an
EAC baseline of the same disc is uniformly upper-case, a `diff` of the two is
noise, and a human reading `metaflac --list` sees an inconsistent file. Two
possible answers and I have no preference: normalise on write, or state in the
provider contract that casing is unspecified and consumers must fold case.

### W5. `totaldiscs` vs `DISCTOTAL`

You emit `totaldiscs`. Picard and most taggers write `DISCTOTAL` (and
`TOTALDISCS` in EAC's output). Same question as W4 and the same non-preference:
either is fine if it is *stated*, because ours has to match whatever you choose.

### W6. `--dirty` in the build tag — still not asking

Unchanged from J2. A dirty build claims its base commit and neither of us can
tell. Recorded on our side as a known limit rather than folklore. Revisit after
the hardware gates close.

---

## 7. Behaviour asks (distinct from questions)

- **B1.** Please add the two missing fatal strings to the generated inventory and
  fix the continuation-line blind spot in the generator (§1).
- **B2.** Please state, in P1, that `-c 1/1` on a single-disc release changes no
  filenames — or tell me it does, in which case we will stop sending it.
- **B3.** Please keep `Invoked as:` on **line 2**, and say whether it is written
  before or after the first `fflush`/`setvbuf` takes effect. It is the only way we
  can detect the host export or a wrapper altering an argument, and a cancelled
  rip is exactly when we need it to have survived.

---

## 8. Questions

Numbered so you can answer numbered.

**Q1.** Does `-c 1/1` change any output filename? Reading
`settings.log_name_scheme = "{album}{if #totaldiscs# > #1# CD|disc|}"` I conclude
no, because the guard is `> 1`. I am asking rather than assuming because we
override `-D`/`-F` but **not** `-L`/`-M`, so your log and cue names are yours to
decide and a change there moves a file we then have to find.

**Q2.** `Total time:` has two observed formats, and they differ in *two* ways:

| Source | Line |
|---|---|
| Your round-4 golden reference (fork, 8-second image) | `Total time:     00:08.00` |
| Tonight's real disc (stock 0.9.3, 59:42) | `Total time:     00:59:42.354` |

So: `MM:SS.ff` with two fractional digits, versus `HH:MM:SS.mmm` with three. Is
the hours component dropped when zero, and is the fraction centiseconds in one
case and milliseconds in the other? Our pattern currently accepts both without
recording *which* it saw, so `.00` is ambiguous between "0 centiseconds" and
"0 milliseconds". Harmless for a duration; I would rather have it in the contract
than in a comment.

**Q3.** `Ripping errors: 0` on a disc where track 3 **did not read identically
across re-reads**. What does that counter count — hard read failures only, or
should an unresolved `-Z` mismatch increment it? We report the two facts
separately today, and if `0` is correct-by-design I will say so explicitly in our
log rather than leaving a reader to reconcile them.

**Q4.** Confirm exit `0` is correct for "ripped completely, not everything
verified against AccurateRip". Tonight: exit 0, 12/14 exact, 2 offset-variant.
That is what I expect from your `{0,1}` inventory, and I want it in writing
because our failure path keys on the exit code and an "unverified" rip is not a
failed rip.

**Q5.** Your `-Y` log verifier and appended text. We append a
`[Platterpus auto-fix addendum]` block to your logfile **after** your
`Log FUN512:` line, recording that a track was re-ripped and which CRC ships.
Does `-Y` hash to the FUN512 line, or does trailing content break verification?
If it breaks, tell me and we will move the addendum to a sidecar file — your
checksum is more valuable than our convenience.

**Q6.** Are `FIXUP_ATOM` and `OVERLAP` counts meaningful to a *user*, or purely
internal to libcdio-paranoia? We currently print them verbatim without
interpretation. If there is a threshold above which they mean "this disc is
degrading", that is a sentence worth showing.

**Q7.** Still open from round 4, and still never observed anywhere: has a
`Pregap source: sub-channel` read **ever** succeeded on real media, on your side?
Ours has not — the container had the wrong binary, so tonight's disc could not
have exercised it. I am not claiming a fixture retires it and I am not going to
imply the suite proved it.

---

## 9. Explicitly not asking

So you do not spend effort:

- **No audio-path changes.** The claim I care most about is still that the fork
  is bit-identical to upstream `958e1ad` on the audio path.
- **No new log sections.** W1/W3 fit inside blocks that already exist.
- **No `--dirty`** (§W6).
- **No byte-exact golden reference.** I pin the lines I parse; byte-comparing
  environment-varying fields would only teach me to regenerate until it passed.
- **No changes for our tag-casing preference** unless you want to — W4 and W5 are
  answered just as well by *stating* the behaviour.

---

## 10. State of the gates

**Both round-4 hardware gates remain OPEN, and neither moved tonight**, because
the rig was on stock cyanrip:

1. **A successful `Pregap source: sub-channel` read on real media.** Never
   executed anywhere. Disc images always fail into `unknown`, so only the failure
   branch has ever run.
2. **A cancelled rip against `a04a94b` on the rig**, proving the `setvbuf` fix
   under podman — which does not forward signals into the container, so our
   SIGTERM reaches only the host wrapper and the escalation path differs from the
   one you tested.

The fork will actually be installed for the next disc (§3), so the next round
should be able to close at least the second.

---

## The return-file spec

One markdown file, these sections, in this order. `scripts/handshake.py --check`
validates it on arrival and exits non-zero listing anything absent — including
the two failures worse than a missing section: **present but empty**, and **a
null case left silent** (if a section has nothing to report, say "none" and why;
do not omit it).

| § | Contents |
|---|---|
| **A** | Pin — repo, branch, commit SHA, exact `--version` output |
| **B** | Answers to §8 Q1–Q7, numbered, each saying **measured** or **read from source** |
| **C** | Commit inventory since `a04a94b` — one line each, or "none" |
| **D** | Log-format delta — every added/changed/removed line, **explicitly "none" if none** |
| **E** | A golden-reference log at the new pin, verbatim, as an appendix |
| **F** | Audio-path statement vs upstream `958e1ad`, with your evidence |
| **G** | Per fix: how you proved it, including any honest "did not prove it" |
| **H** | Corrections to anything in *this* file — and note that §Corrections above says a round-4 verification of mine was over-scoped, so a correction to me is welcome and expected |
| **I** | The regenerated provider contract: stable vs unstable log lines, argv contract **per flag including `-c`**, exit-code inventory, and the **90-string** fatal inventory (or your number, with the discrepancy named) |
| **J** | Your asks of us, numbered, so I can answer numbered |

---

## The shared rigour bar

Both sides hold to this. It is not advice; every line was paid for by a shipped
mistake in one of the two repos, and it lives in both `CLAUDE.md`-equivalents so
neither project has a private copy of the protocol.

1. **Answer from the artifact, not from your memory of the artifact — and name
   which file.** The pre-gap convention flipped twice in one day because a true
   count of `INDEX 00` lines in EAC's **cue** was cited as evidence about EAC's
   **log**. Both of us made that mistake, in the same round, and neither of us had
   opened the log.
2. **A correction is not pre-verified.** §H2 arrived as "you got this wrong", was
   well argued, was wrong, and was applied faster than any finding made in-house
   *because* of the framing. A finding that arrives as a correction deserves more
   scrutiny than one that arrives as a claim, not less.
3. **Verify the behaviour, not the description of the behaviour.** This round's
   own correction: I verified the 88 strings you sent me and called it
   verification of your inventory. Re-deriving from your source found two more.
4. **Capture without surfacing is the same bug from the user's side.** 21 of 45
   fatal strings were once captured and never shown to anyone.
5. **Would this test fail if I reverted the fix?** Check by actually reverting.
   It has caught a vacuous suite here five times now — six as of this round: my
   first revert-proof of the dependency-dialog fix *passed*, because the `str`
   replacement I used to revert it had been silently no-op'd by the formatter
   reflowing the line. The test was fine; my revert was not. Verify the revert
   landed before believing what the run tells you.
6. **Can this check be satisfied by finding nothing?** Then give it a floor.
   Four of our audit checks could run and say nothing; a silent check reads
   exactly like a clean one.
7. **A silent truncation reads as completeness.** Bound output head *and* tail,
   and mark every elision with a count.
8. **Tri-state or don't state.** "Could not determine" is never "no".
9. **A "no changes" round is still a round.**

---

*Round 5 OPEN. Platterpus v0.6.3 is built, green and **held** — our own gate
forbids a release from either side while a round is open, and this file opens
one. No pin change either; `a04a94b` stays authorised by round 4's GO.*
