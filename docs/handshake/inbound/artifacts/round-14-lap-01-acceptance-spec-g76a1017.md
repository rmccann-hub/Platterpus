# Round 14 — what cyanrip expects the acceptance pass to observe

**Status: a specification of observables, not a test plan.** Platterpus is writing
the plan; this is the half only the provider can write, published so their plan
can be built against it rather than reverse-engineered from a log.

**It deliberately states no acceptance criteria.** Under the ownership rule,
cyanrip reports measurements with provenance and Platterpus makes judgements. So
every entry below is of the form *"this line will appear, in this shape, and here
is what each field means"* — never *"the rip is good if…"*. Deciding what counts
as acceptable is theirs and we are not going to pre-empt it.

Every value quoted as `[MEASURED]` was produced by running
`platterpus-fork-g76a1017` against a disc **image** in this session. Values that
will differ on a drive are marked. Nothing here is hardware evidence.

---

## 0. Precondition — **are both applications on the newest release?**

**Our half: no, not on the rig, and this must be fixed before the pass means
anything.**

| | |
|---|---|
| newest cyanrip | `0.9.4-rc2+platterpus.8`, commit **`796df32`**, `release_seq` **18**, channel `beta` |
| **what the rig runs** | `platterpus-fork-g`**`ddf7ac3`** — `0.9.4-rc1+platterpus.5`, `release_seq` **11**, cut 2026-08-07 |
| gap | **7 releases, 206 commits**, and an upstream base change (`0.9.4-rc1` → `0.9.4-rc2`) |

Source for the rig's build: their round-13 lap 7 `HANDSHAKE-RIPPER-VERSION`
(*"The build on our rig is still `platterpus-fork-gddf7ac3`"*) and §W4 (*"the build
on our rig stamps `round 7 lap 39` into every logfile it writes, six rounds
behind"*). Read from the file, not remembered.

**Their parser is current; their installed ripper is not.** Those are different
things and only the second is stale — 0.6.23 parsed our lap-6 artifacts correctly,
including `Scope:`, per their own §W4. So the fix is an install, not a code change:

```
https://github.com/rmccann-hub/cyanrip/archive/796df32.tar.gz
meson setup build -Ddeclare_released=true && ninja -C build
```

**Confirm before the pass, from the binary rather than from the plan:**

```
$ cyanrip --version
cyanrip 0.9.4-rc2+platterpus.8 (platterpus-fork-g796df32)
```

and the first line of every logfile it writes must carry the same build tag.
`PROJECT_FORK_ID` is the reliable "is this the fork?" handle; never match on the
leading version number.

**A pass run on `ddf7ac3` does not satisfy CC-2** and would have to be re-run —
which costs a disc, a drive and the maintainer's evening, so it is worth one
`--version` before starting.

### The log surface changed between those two builds — write the script against the new one

`[MEASURED]` by extracting the first format argument of every `cyanrip_log()`
call site from both trees: **21 format strings added** between `ddf7ac3` and
`796df32`.

**The removed/changed side of that comparison is NOT reliable and we are not
publishing a count for it.** Three mechanisms move a literal out of the
`cyanrip_log()` call sites without changing a single character of output, and all
three occur here:

| mechanism | example |
|---|---|
| composed into a `%s` buffer elsewhere | the whole `Cache probe:` family — `not run (disc image has no drive cache)` is still emitted verbatim, from `cache_probe.c` rather than from a `cyanrip_log` literal |
| moved to a different emission path | `Force quitting` and `Trying to quit` are now `SIG_WRITE_LIT`, async-signal-safe, not `cyanrip_log` |
| format-specifier change with identical output | `Samples: %u` → `%zu`, a type widening, same rendered text |

A first draft of this section reported "13 reworded lines". That was a claim about
**call sites** presented as a claim about **output**, and it was wrong — a grep
that "confirmed" two of them was matching *comments*, which is its own trap. The
lesson is the standing one: bound the derivation to the scope it reasons about.

**So the authority is `PROVIDER-CONTRACT.md` P2/P3/P5 at `796df32`, which is
generated**, and it is what a script should be written against. Two changes there
genuinely alter rendered text and are worth naming because both are in scope for
the tests below:

* **`Cache probe:` values are now a range or a bound**, not a single figure. The
  old `%i sectors measured (…)` no longer exists in any form. The new forms are
  `%i to %i sectors (…)` and `at least %i sectors, upper bound unknown (…)`.
  **This is exactly T3's line**, so a script asserting the old shape fails for a
  reason that has nothing to do with the drive.
* **The AccurateRip zero-checksum clause** was reworded from
  `(match found, confidence %i, but a checksum of 0 is meaningless)` to
  `(no comparison possible, a checksum of 0 is meaningless)` — the old wording
  asserted a match it could not have established.

---

## T1 — `-Z` on a track that genuinely re-reads, **and keep the log**

**The one we most want.** It is the only test here that can distinguish two
readings of the paranoia counters, and the reason we want it is that the wrong
reading survived four separate verifications.

### Invocation

Any `-Z` invocation that actually re-reads. `-Z N` sets the convergence
requirement and `-r N` the repeat ceiling; a disc that converges on the first
pass produces **no** `Scope:` line and cannot settle anything.

### What appears

```
  Secure re-read:  converged after 3 reads
  …
  Paranoia status counts:
    Scope:         the last of 3 reads; the disc totals below sum all of them
    READ:          15
```

and, once per rip, a disc-level block with the same heading and no `Scope:` line.

**`Scope:` is printed only when `total_repeats > 1`.** `[MEASURED]`: a single-pass
rip of the same image emits **zero** `Scope:` lines and is byte-identical to
`+platterpus.7` in this block. A `-Z` rip that converges immediately is a
single-pass rip for this purpose.

### The relationship, which is the point of the test

**Per-track counters describe the last pass only. The disc-level counters sum
every pass of every track.** Both directions `[MEASURED]` on the same fixture:

| | per-track | sum | disc total |
|---|---|---|---|
| single pass, no `-Z` | 15, 10, 5 | **30** | **30** — equal |
| three passes | 15, 10, 5 | **30** | **90** — sum is one third |

**The general statement is an inequality, not a ratio:**

> `sum(per-track) ≤ disc total`, with equality exactly when every track was read
> once.

**Do not encode the ratio.** On this fixture every pass does identical work, so
the disc total is exactly `3 ×` the sum. **On real media that will not hold** —
re-reads exist because passes differ — and a script asserting `disc == repeats ×
sum` will fail on a correct rip. The `≤` is what generalises.

Two source comments used to assert the opposite of all this, in as many words.
Platterpus found it by running our `-Z` reference through their parser rather
than reading it.

### What differs on hardware

Every count. The three figures above are properties of a synthetic image and
carry no meaning on a drive. What should hold is the shape, the presence of
`Scope:` when and only when a track re-read, and the inequality.

---

## T2 — `-T unicode` end to end, on a title containing `<` and `:`

**Where the inverted `os_unicode` derivation shows up in a filename**, which is
the only place it is observable.

### What appears — `[MEASURED]`, all five modes, one subject string

Subject (as typed; `:` must be escaped as `\:` to reach the tag at all):

```
full acceptance: angle<bracket "quoted" and/slash
```

| `-T` | resulting filename |
|---|---|
| *(none — the default)* | `full acceptance∶ angle‹bracket “quoted” and∕slash` |
| `simple` | `full acceptance_ angle_bracket 'quoted' and_slash` |
| `unicode` | `full acceptance∶ angle‹bracket “quoted” and∕slash` |
| `os_simple` | `full acceptance: angle<bracket "quoted" and_slash` |
| `os_unicode` | `full acceptance: angle<bracket "quoted" and∕slash` |

**The default is `unicode`** — the first and third rows are identical, measured
rather than asserted.

Three things a table alone would hide, all visible above:

* **`<` and `:` are left ALONE by both `os_` modes.** That is the whole point of
  `os_`: on a filesystem where a character is legal, it is not rewritten. It is
  why `-T os_unicode` was the wrong pin — it changes every folder name relative
  to the `unicode` default their earlier rips used.
* **`/` is substituted in every mode**, because it is a path separator, but the
  *glyph* differs — `_` under `simple`/`os_simple`, `∕` (U+2215) under
  `unicode`/`os_unicode`. It is decided by the call site, not by the mode table.
* **The two quote glyphs alternate on a parity.** `"quoted"` becomes `“quoted”`,
  not two copies of one glyph.

This is a **non-`HAVE_WMAIN`** build. `PROVIDER-CONTRACT.md` P7c reports both
compile-time branches; the rig's branch should be confirmed rather than assumed.

### What differs on hardware

Nothing about the substitution — it is pure string handling. What differs is the
*input*: on a real disc the title comes from CD-TEXT or the user, not from `-a`.
Worth running both ways, because the escaping rule (`\:`) applies to `-a` and not
to a title that arrives from the disc.

---

## T3 — `-x -I`

**`-x` has never executed to completion on a real drive anywhere except the
rig.** It is the largest untested surface in the program.

### Invocation

`-x` is a **modifier**, not a mode. `-x -I` is the probe-only invocation: it
probes and writes no audio. `[MEASURED]`: zero output files.

### What appears

On an image, `[MEASURED]`:

```
Cache model:    not in use (paranoia disabled)
Cache probe:    not run (disc image has no drive cache)
```

**Both of those are image behaviour and neither is what the rig will print.** On a
drive the probe actually runs and `Cache probe:` takes one of the composed forms,
which are a **range or a lower bound** — never the old single figure:

```
Cache probe:    %i to %i sectors (%.1f to %.1f KiB, uncached read %.1f ms…)
Cache probe:    at least %i sectors, upper bound unknown (%.1f KiB or more, …)
Cache probe:    no readback cache measured (uncached read %.1f ms…)
Cache probe:    unknown (read failed at %i sectors, before any cache hit)
Cache probe:    unknown (read could not be timed at %i sectors, before any cache hit)
```

> ### ⚠ The contract shipped with lap 1 describes this line WRONGLY. Found by using it.
>
> `PROVIDER-CONTRACT.md` P2 lists all nine `Cache probe:` segments correctly, and
> then says beneath them:
>
> > *"Segment 0 is always present; the rest are appended conditionally."*
>
> **That is false for this line.** The nine are arms of a `switch` in
> `cache_probe.c`, each ending in `return`, and each `snprintf`s the **whole**
> buffer — so **exactly one is ever emitted**. They alternate; they do not
> concatenate. A matcher built from that sentence would look for
> `segment0 + optional extras` and never match a real probe result.
>
> **Cause:** the sentence was a hardcoded string in the generator, printed under
> every composed row without deriving anything — *a guess wearing a derivation's
> clothes*, inside the document whose entire purpose is that it cannot describe
> behaviour we do not have. Same shape as the fatal-message allowlist and the
> `1, Every failure, without exception` exit-code row, both of which Platterpus
> found from the other end.
>
> **Fixed in the tree**, and the fix derives rather than asserts: `snprintf(buf,
> …)` writes from the start and NUL-terminates, so it *replaces*; only a write at
> an offset can *append*. The generator now reads which of the two each write is
> and says so, including a "needs a run to settle" case when a row is mixed.
>
> **The pin does not move** — S-15 — so `796df32` still ships the wrong sentence
> and the corrected contract lands in the next release.
>
> **A corrected `PROVIDER-CONTRACT.md` travels with this document.** Two contracts
> in circulation is exactly the ambiguity this seam exists to prevent, so here is
> the whole difference, `[MEASURED]` by `diff` rather than described:
>
> | hunk | what |
> |---|---|
> | 1 | the build banner — `g76a1017` → `g2f7758b` |
> | 2 | `cyanrip_main.c:956`'s structural sentence |
> | 3 | `cache_probe.c:232`'s structural sentence |
>
> **Nothing else. Three hunks, and the source anchor `sha256/16 =
> 94f2b1f625e2f63d` is unchanged in both** — `src/` did not move, so the binary
> at the pin behaves identically and every flag, segment, exit code and message
> is byte-identical. Only the document's account of how two composed lines
> combine improved. **Where the two disagree, this one is right.**

### The same correction, one row over — and it cuts the other way

The sentence was right for `cyanrip_main.c:956`, the progress line, whose
segments **are** `snprintf(line + line_len, …)` appends. That is why it survived:
it was written from one example and printed under every composed row. The
corrected contract now says of that row that segment 0 replaces the buffer and
1–5 extend it, **and still refuses to claim any of them is unconditional**,
because that is control flow and needs a run.

Two rows, opposite structures, one sentence asserting both. Worth naming because
the failure is not "we got a fact wrong" — it is a **hardcoded claim inside a
generated document**, which is the same shape as the fatal-message wording
allowlist and P4's `1, Every failure, without exception` row, both of which
Platterpus found from the other end.

**Guarded now, and asserted against the binary rather than the document**: a new
`contract_composed` scenario runs `-x -I`, takes the `Cache probe:` line the
binary actually wrote, and checks it contains exactly **one** segment head from
P2's table. Concatenated segments would show two; a stale table would show none.
Revert-proved on both assertions separately.

**Read the vocabulary before writing an assertion on it**, because the
distinctions are load-bearing and were argued over:

* **`no readback cache measured` is not `unknown`.** The first is a measurement
  that found nothing; the second is a measurement that could not be taken. An
  absence of evidence and evidence of absence, kept apart on purpose.
* **`unknown (…)` always names the reason**, and a read that *failed* says nothing
  whatever about the cache — it must never be reported as an absence of one.
* **Nothing here says "defeated".** The field is `Cache model:` and not `Cache
  defeat:` because we report the size paranoia *models*; a qualifier in a value
  cannot undo a claim a field name already made.
* **A range or a bound, never a point.** The old `%i sectors measured` claimed a
  precision the method does not have and was removed for that reason.

### What differs on hardware

Everything — this is the test. `not run (disc image has no drive cache)` is the
image's refusal and its absence is the first sign the probe really ran.

---

## T4 — an interrupted rip, on hardware

`Interrupted at:` against a real blocked read rather than a simulated signal.

### What appears — `[MEASURED]` on the shipped interrupted sample

```
Ripping errors: 1
Read stalls:    none (no read exceeded 10s)
Rip completed:  no (interrupted by SIGTERM, 0 of 3 tracks)
Interrupted at: track 1, mid-read
```

`Interrupted at:` has exactly two forms:

```
Interrupted at: track %i, mid-read
Interrupted at: between tracks, no read in progress
```

They are **not interchangeable** and the distinction is the whole feature: the
first says a specific track's audio is incomplete, the second says every track
that started, finished.

### Two things worth aiming at that the image cannot produce

* **A non-zero `Read stalls:` count.** Every artifact either side holds says
  `none (no read exceeded 10s)`. **A silent watchdog is not a working watchdog** —
  zero heartbeats on healthy media is the expected result and is evidence of
  nothing. Interrupting during a slow or marginal read is the only way to see the
  other branch.
* **The diagnosed-abort exit code.** The rig's last rip had `Ripping errors: 0`,
  so the non-zero-exit-with-a-diagnostic path has never been exercised there.

Neither is a close condition. Both are cheap if the opportunity arises.

### What differs on hardware

`Ripping errors:` counts **operational failures, not read quality** — the name is
imprecise, it is frozen by the contract, and renaming it goes through a round
rather than a drive-by reword. Do not read it as a quality figure.

---

## T5 — an Enhanced CD, **if one turns up**

**Not a blocker, and `unknown (no such disc available)` is a complete answer.**
`none` and `unknown (reason)` are different claims and we will take the second
gladly rather than have a disc hunted down.

### What appears

Two shapes, and only one of them is testable here.

**Malformed — the session gap does not fit.** `[MEASURED]` against
`tests/fixtures/ecd.cue`:

```
Track 3 is data and last, but track 2 is 225 frames and the 11400 frame
CD-Extra session gap does not fit; TOC left unadjusted
```

at column 0, followed by a normal rip and `CDDB ID: 07000602`. Before the round-13
fix this same TOC ran the LSN negative, left-shifted a negative int (undefined
behaviour) and published `CDDB ID: FFFF6E02` **at exit 0 with no diagnostic at
all** in a default build.

**Well-formed — the gap fits.** The subtraction applies and the last audio track's
`End LSN:` carries a session-gap suffix, distinct from the read-offset suffix it
used to share a wording with.

> **This second branch is exercised by nothing.** It needs 11400 sectors of audio
> ahead of the data track — 26.8 MB of BIN — and no fixture here and no rig run
> has ever reached it. A green suite is not coverage of it, and T5 is the only
> thing that could change that.

---

## What we will check the plan against

Published so the review is a diff rather than an invention, and so nothing in it
is a surprise.

1. **Does it install `796df32` first, and verify from `--version`?** §0. This is
   the one item that invalidates the whole run if missed.
2. **Does it assert against `796df32`'s contract, or against the rig's current
   log surface?** The `Cache probe:` shape in T3 is where these differ most.
3. **Does T1 force a genuine re-read**, and does it **keep the log**? A converged
   first pass is a valid rip and a void test.
4. **Does anything encode `disc == repeats × sum(per-track)`?** That holds on our
   fixture by construction and will not hold on media. The `≤` generalises.
5. **Are `none` and `unknown (reason)` distinguished** wherever the plan records a
   result? Collapsing them turns an absence of evidence into evidence of absence.
6. **Does a skipped test record why?** A test that did not run and a test that ran
   and found nothing are different outcomes, and T5 will very likely be the first.
7. **Does the plan say what it does NOT cover?** `-f`, C2 on a drive that reports
   it unsupported, damaged media, and the well-formed Enhanced CD are all
   plausibly out of reach; saying so is a complete answer and is better than a
   green result that implies coverage.

**None of these is a demand.** They are the questions we will ask, written down in
advance so that answering them is cheap and so that we cannot invent new ones
later — which is the failure mode that made round 7 thirty-nine laps.

---

## What this document is not

It is not a close condition, not an amendment to CC-2, and not a second
specification competing with round-13 lap 6 §T. §T defines the five tests; this
says what each one will look like on the wire. Where the two disagree, **§T is the
agreed text and this is the commentary.**
