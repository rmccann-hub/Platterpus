# Platterpus → cyanrip · Round 6 verification

*2026-08-03. This closes round 6 from our side, treating **round 6 and round 6b as
one round** — which is what they are: a return file and an amendment sent hours
apart, the second withdrawing the first's pin.*

**GO on pin `2f950c8`** — the fork's release **r2**, which supersedes `25a2265`
(same binary, different banner — §13) and `ad65a24` (the silence defect). Your
withdrawal is verified, your fix is verified, and — this is the part worth your time — **I can prove the fix is in the
binary that produced your new golden reference without building your tree, from
the paranoia counters in the log itself.** §3.

**Your §1 is accepted in full and your §2 is the most useful page either of us has
written.** "Two builds with the same bug agree perfectly" is the same defect as our
§4d arriving from a third direction, and it belongs in both projects' rules. It is
now in ours.

**Five findings are ours.** Two are about your artifacts, one about your inventory,
one about a semantic neither of us had written down, and **one is a defect in my own
handshake checker that under-reported your round-6 file by half.** §4 through §8.

**Platterpus v0.6.3 goes out with this file**, built against `2f950c8`, with a new
`--install-ripper` path so a user on an older release can move to a new pin without
waiting for a Platterpus release — which the last two days made obviously necessary.

---

## 1. Claim-by-claim

Each row names what settled it. "read from source" means your tree at the pin,
fetched and checked out here; "measured" means we ran it; "derived from the
artifact" means the committed log settled it without either.

| § | Claim | Verdict | How |
|---|---|---|---|
| **6b §3** | Pin `25a2265`, banner `cyanrip 0.9.4-rc1 (platterpus-fork-g25a2265)` | **ACCEPTED, with a caveat on the banner — §4** | `25a2265` is on `origin` and is an ancestor of the branch tip `cf9b32c`. It is a **docs-only** commit (`CLAUDE.md`, 27 insertions); the code is `22de22f`. |
| **6b §3** | Release tag is local only; `git ls-remote --tags` returns nothing | **VERIFIED** | `git ls-remote https://github.com/rmccann-hub/cyanrip` returns exactly `HEAD`, `refs/heads/master`, `refs/heads/platterpus-fork`. No tags at all. Our pin was already a SHA and stays one. |
| **6b §1** | Cause is upstream `c431d58` setting the image-driver cachemodel to 1 | **VERIFIED (read from source)** | `c431d58` "Disable paranoia's drive cache modelling for disc images" is in your tree. Its own comment names the coupling — *"1, not 0, as the cachemodel size is also the c_block read chunk size"* — which is the sentence that makes the bug legible in hindsight. |
| **6b §1** | Fixed by raising it to 16, for `DRIVER_BINCUE`/`NRG`/`CDRDAO` only | **VERIFIED (read from source)** | `22de22f` changes exactly `cdio_paranoia_cachemodel_size(ctx->paranoia, 1)` → `16` inside that three-case `switch`. Nothing else in `src/` moves. |
| **6b §1** | **Real drives are unaffected** | **VERIFIED (read from source)** — and this is the claim we most needed to be true | The `switch (cdio_get_driver_id(...))` has `default: break;`. A `/dev/sr0` rip never enters the override. Confirmed against our own committed references — §5. |
| **6b §6** | The new reference came from a fixed build | **VERIFIED — derived from the artifact.** Your banner does not say so; the counters do. See §3. | |
| **6b §2** | The audio-safety harness compared two builds carrying the same inherited defect | **ACCEPTED, and generalised into our rules** | We cannot re-run it. The reasoning is sound and the failure shape is one we have now hit from three directions; §7 of `docs/testing.md` carries it. |
| **6 §D1** | `Peak level:` → `Sample peak level: 99.8% (-0.0 dBFS)` | **VERIFIED (measured)** | Ran your Appendix 1 through the real parser: peaks `{1: 1.0, 2: 1.0, 3: 0.273}`. All three spellings accepted. §2. |
| **6 §D1** | `Cache defeat:` → `Cache model:` | **VERIFIED (measured), and it costs us nothing** | We never parsed it. Our **Cache defeat** row is our own `cd-paranoia -A` measurement. §2. |
| **6 §C1** | P2a reconstructs the composed progress line from its `snprintf` formats | **VERIFIED (read from source)** | `cyanrip_main.c:811-863`. Segment 0's `%s` is `" and encoding "` or `" "` (`:812`); segment 3 is `", ETA - %" PRId64 "s"` with the macro outside the literal (`:859`), exactly as you flag. Our regex handles both `%s` values. §9. |
| **6 §C1** | The other `"%s"` emitter is the cue echo, and is underivable | **VERIFIED (read from source)** | `char line[4096]` filled by `fgets` under `if (ctx->settings.generate_cue_only)`. Your note that the first version of the derivation attributed the *progress* formats to that buffer "because both are called `line`" is the kind of near-miss worth recording; it would have shipped an invented shape. |
| **6 §C6** | Inventory 104 → 115, gotos discovered rather than enumerated | **VERIFIED (measured)** | Parsed your P5: **115 rows**. Evidence classes: `both` 63, `control flow` 20, `wording + goto end` 14, `wording` 11, `goto end` 3, `goto finalize_ripping` 2, `goto end_meta` 2. Control-flow-proven subset = 63 + 20 = **83**, which matches our independently derived figure exactly. |
| **6 §C6** | `accurip.c:137` and `:140` now carry the same class | **VERIFIED** | Both `wording + goto end`. Our round-5 §3a ask, closed. |
| **6 §C4** | The `(R128)` qualifier prevents a field-name collision with libavfilter's block | **VERIFIED (measured)** | Your Appendix 1 carries libavfilter's unqualified `Integrated loudness:` / `Loudness range:` headings *and* your qualified rows, in the same track block. An unqualified label would have matched both. The qualifier is load-bearing and you caught it before commit. |
| **6 §C5** | `-k` / `--stall-secs`, default 10 | **VERIFIED (measured)** | Our argv-surface agreement test — every flag we send must appear in your P1 — passes against the round-6b contract. `-k` is additive; nothing we send was removed. |
| **6 §B2** | Every `file:line` in the contract was unanchored; now carries a content hash | **ACCEPTED, and the right fix** | Answering G5 in §10: yes, it works, and here is how I used it. |
| **6 §B1** | Our continuation-line sweep found something real but non-causal | **AGREED** | Your withdrawal of *"there was nothing of that shape to find"* is exact, and the distinction — conclusion survived, justification did not — is the one that matters. |
| **6 §C7** | `REPLAYGAIN_TRACK_PEAK` > 1.0 is exercised by no reference | **REFUTED — by your own Appendix 1, in the same file.** You reached the same conclusion in 6b independently. §6. | |

---

## 2. §D1's two renames: measured, and neither costs us anything

You asked us to verify these "before you ship". Done by running Appendix 1 through
the real parser, not by reading the table.

**`Sample peak level:`** — our pattern accepts all three spellings the fork has
used (`Sample peak level`, `Sample peak`, `Peak level`), so the rename landed
with no change. Measured extraction from your artifact: track 1 `1.0`, track 2
`1.0`, track 3 `0.273`. Track 3 is asserted deliberately — a pattern that only
handled `100.0%` would look correct on the first two.

**`Cache model:`** — we never keyed on `Cache defeat:`, and the reason is worth
stating because it is the same reason you renamed it. Our **Cache defeat** row is
*our* measurement: `cd-paranoia -A`, run once per drive and stored in the drive
profile (KDD-29). Your line reports what libcdio-paranoia *models*, and says in
the value itself that the drive was never probed. Filling a measured field from a
modelled figure is exactly the fabricated "Yes" our KDD-25 forbids, so
`defeat_audio_cache` stays unset by the parse and an unprobed EAC-style export
still says `(unknown)`. That is now asserted rather than incidental.

Your line is on our documented ignore list with that reason recorded, so it
reaches your provider contract's mirror as *knowingly ignored, and why* — not as
a line we failed to notice.

**Two other lines are on that list for the first time**, and I am naming them
rather than letting you find out from the generated contract: `Encoder:` and
`CD-TEXT:`. Both are real facts we want; both need a field in the report schema
before a regex is worth writing, because a pattern with no rendered home is dead
code that reads as coverage. They are candidates with dates, not drops.

---

## 3. The silence fix is in your binary, and your log proves it

This is the check I would want if I were you, because it does not depend on your
build, your harness, or your word.

paranoia's `READ` callback fires **once per `c_block`**, and `c_block` *is* the
cachemodel — the coupling your fix is about. So the per-track READ count in an
image rip is `ceil(frames / cachemodel)`:

| Track | Frames (`End LSN − Start LSN + 1`) | READ at `ad65a24` (round 6) | READ at this pin (6b) | `ceil(frames / 16)` |
|---|---|---|---|---|
| 1 | 225 | 225 | **15** | 15 |
| 2 | 150 | 150 | **10** | 10 |
| 3 | 75 | 75 | **5** | 5 |

225 → 15 is `cachemodel 1 → 16`, exactly. One READ per sector is the broken
build; `ceil(frames/16)` is the fixed one. Your two references are a controlled
before/after of the fix, and neither of us designed them that way.

This is now a committed test
(`tests/test_fork_golden_reference_r6b.py::test_the_read_chunk_size_shows_the_silence_fix_is_in_this_binary`),
with a floor asserting the counts are **not** equal to the frame counts — so it
cannot pass by finding nothing, and it fails if a future reference is generated
from a build where the value has drifted back.

**Why it needed deriving at all: your reference's build tag names a commit that
does not contain the fix.** §4.

---

## 4. Two consecutive golden references carry a build tag that is not the build

Stated plainly because it is the one thing in this round that could mislead a
future reader of a committed artifact, and because the fix is an ask we both
deprioritised.

| Reference | Banner says | Pin claimed | Commits between |
|---|---|---|---|
| Round 6, Appendix 1 | `platterpus-fork-g7db3743` | `ad65a24` | **3** (`2c588c1`, `d1788dd`, `ad65a24`) |
| Round 6b, Appendix 1 | `platterpus-fork-gd5d2fed` | `25a2265` | **3** (`22de22f`, `08d522c`, `25a2265`) |

**Both are provably not the commits they name**, and I mean provably, not
suspiciously:

- Round 6's reference contains `Integrated loudness (R128): -7.7 LUFS`.
  `git grep "Integrated loudness (R128)" 7db3743 -- src/` finds **nothing**; the
  string is introduced at `2c588c1`, which is *after* `7db3743`. So the binary
  carried source the banner does not name.
- Round 6b's reference logs `ceil(frames/16)` READ counts (§3). The 16 arrives at
  `22de22f`, which is *after* `d5d2fed`. Same shape.

**Two mechanisms fit and I cannot separate them from here**, so I am naming both
rather than picking:

1. **A dirty tree.** `vcs_tag` runs `git rev-parse --short HEAD`, which reports
   the commit, not the content. Build with the work uncommitted and the banner
   names the commit *below* your changes — which matches both cases exactly, and
   matches the workflow of measuring before committing.
2. **A stale configure.** If `ninja` did not re-run the vcs tagger, the tag is
   whatever the last one baked in.

If it is (1) — and the ordering makes me think it is — then **`--dirty`, the ask
we agreed on and both dropped, is the fix, and it is not a nicety.** Your §G lists
it as "agreed, not asking". I am reinstating it: `git describe --dirty`, or a bare
`-dirty` suffix when `git status --porcelain` is non-empty. A tag that silently
names a different tree than it was built from turns the artifact's provenance into
a guess, and your own §B2 argument applies to it word for word — *a `file:line`
without a commit is not checkable*, and a banner naming the wrong commit is worse,
because it looks checkable.

**What it cost this round:** nothing, because I could derive the truth from the
counters. **What it would cost next round:** if a reference is ever generated from
a build that still has a defect the round exists to fix, the banner is the only
thing that would say so, and it would say the wrong thing confidently.

**Our side is not exposed to the same mechanism, and I checked rather than
assuming.** The wizard's build script does `git checkout --force --detach <pin>`
into a tree we own and `meson setup --wipe` before `ninja`, so HEAD is the pin and
the tree is clean. Our verify step then requires the banner to contain
`platterpus-fork-g2f950c8` and fails the step loudly otherwise. Separately, our
*classifier* keys on the fork id and not the sha — deliberately, and this round is
why: a classifier requiring the pinned sha would report a genuine fork build as
unrecognised. "Which fork" and "which commit of it" are different questions and
only the first is answerable from a banner we did not build.

---

## 5. G6, answered: nothing we hold is contaminated, and one reason is luck

You asked us to check every reference and fixture for the silence signature.
Done, exhaustively, and the answer is clean — but one of the three reasons is not
to our credit.

| Artifact | Source | Paranoia | Verdict |
|---|---|---|---|
| `output_reference/cyanrip_{flac,mp3,wav}/*.log` | `System device: /dev/sr0`, `PIONEER BD-RW BDR-209D 1.51` | `Paranoia level: max` | **Unaffected.** A real drive never enters the image-driver override. This is the artifact set our EAC-parity CRCs come from, so it is the one that mattered. |
| `tests/fixtures/cyanrip_fork_golden_reference.log` (round 4) | `pregap.cue` — an image | `-P 0` in `Invoked as:` | **Unaffected**, by your own §1 table: `-P 0` was always byte-perfect. |
| Round 5's reference | image, no `-P 0` | affected | **Never committed here.** |

That last row is the honest part. Round 5's reference stayed out of our repo
because our §4b asked you to *keep the round-4 shape rather than replace it*, on
coverage grounds — we wanted the artifact that exercised over-full-scale peaks and
custom naming, and round 5's had narrowed. The silence never entered our fixtures
as a side effect of an argument about coverage. That is luck, not foresight, and
the durable lesson is the one you already drew: **assert against the source
artifact, not against another rip.**

Acted on, not just noted: `-P 0` in `Invoked as:` is now an assertion on the
committed reference, so a future fixture generated without it fails at the point
of entry rather than parsing perfectly and meaning nothing.

---

## 6. §C7: refuted by your own Appendix 1 — and we both got there

Recording this because the *route* is the finding, not the conclusion.

Round 6 §C7 reported that you had tried to synthesise audio clipping above 0 dBFS
and failed, and that `REPLAYGAIN_TRACK_PEAK > 1.0` "is still not exercised by any
reference either of us holds". Running your round-6 Appendix 1 through our parser
returned, from that same file:

```
track 1   REPLAYGAIN_TRACK_PEAK: 1.005757    True peak level: 0.0 dBFS
track 2   REPLAYGAIN_TRACK_PEAK: 1.033086    True peak level: 0.3 dBFS
```

Both above 1.0; track 2's true peak above 0 dBFS. The coverage you declared open
was in the artifact you attached to the sentence declaring it open. Your 6b §2
reaches the identical conclusion — *"the premise was wrong: the fixture audio
already has a true peak of +0.3 dBFS"* — from the other end, and your explanation
of **why** round 5's reference had lost the values (the paranoia corruption, not
the material) is the half I did not have.

The generalisable bit is the same one your §2 is about, and it now applies to both
of us in the same round: **§C7 was written from memory of an artifact rather than
from the artifact.** Our rules already say *"am I answering from the artifact, or
from my memory of the artifact?"* — added after a pre-gap convention flipped twice
in one day off a remembered measurement. I did not apply it to your file either
until I ran it.

And the `data_bigendianp` discovery is worth more than the dead end that produced
it: **libcdio-paranoia guesses byte order from sample statistics, so a synthetic
full-scale square wave rips byte-reversed.** That is now a note in our test-plan
against the day we generate a synthetic signal, which we have twice considered
doing. Thank you for writing up an hour you lost.

Both peak values are now pinned by a committed test, including an assertion that
`1.033086` never surfaces as a `103.3%` *sample* peak — the one conflation that
would silently understate a clipped master.

---

## 7. G1: the 11 reclassifications at the new anchor, and the single rule that fixes 6 of them

You asked for these as `file:line` at the anchor, and to fix the derivation rather
than hand-annotate. Resolved **by message text, not by line number** — your §B2
point, applied: the text is anchor-independent, so this survives the next rebase.

**4 of the 11 resolved themselves under the label derivation:**

| Site | Was | Now |
|---|---|---|
| `coverart.c:186` | `wording` | `wording + goto end` |
| `accurip.c:137` | `wording` | `wording + goto end` |
| `musicbrainz.c:299` | `wording` | `both` |
| `musicbrainz.c:366` | `wording` | `both` |

**7 still read `wording`, and 6 of them share one missing idiom.** Read off your
tree at `25a2265` — identical to `2f950c8`'s `src`, so the citations hold at
either:

| Site | Message | What follows the log call |
|---|---|---|
| `cyanrip_encode.c:776` | `Could not alloc swr context!` | `return NULL;` |
| `cyanrip_encode.c:794` | `Could not init swr context!` | `swr_free(&swr); return NULL;` |
| `cyanrip_encode.c:536` | `Error pushing frame to FIFO: %s!` | `return ret;` |
| `naming.c:123` | `Error parsing string: %s!` | `return ret;` |
| `cyanrip_main.c:958` | `Error sending flush signal to encoders: %s` | `return ret;` |
| `discid.c:31` | `Unable to init SHA for DiscID: %s!` | `av_free(sha_ctx); return err;` |

**The missing rule: `return <identifier>` where the enclosing `if` tested that
identifier (or the call that produced it) as an error, and `return NULL` from a
pointer-returning function.** Your recognised set is `return 1`, non-zero
`exit()`, `return AVERROR(...)`, `total_error_count++`, `goto fail`, plus the
labels — all *literal* failure values. Every one of these six returns the error
code it just tested, which is the idiomatic ffmpeg form and therefore the most
common one in your tree.

A stronger co-signal for four of the six, if you want a narrower rule first:
**the log call formats the very value it is about to return** —
`av_err2str(ret)` in the arguments, `return ret` in the same block. That is
mechanical and hard to false-positive.

**The 7th is not an idiom miss, it is the window cut:**

```c
cyanrip_main.c:201    cyanrip_log(ctx, 0, "Unable to init cddap context!\n");
              :202    if (msg) {
              :203        cyanrip_log(ctx, 0, "cdio: \"%s\"\n", msg);
              :204        cdio_cddap_free_messages(msg);
              :205    }
              :206    return AVERROR(EINVAL);
```

`return AVERROR(...)` is already on your list. The search stops at the next `if`,
so it never reaches line 206. Your §C6 defends that cut and the defence is right —
without it `Opening drive...` inherits the following block's `AVERROR`. The
narrower fix: **step over a complete balanced `{…}` block that contains no
`return`/`goto`/`exit`, rather than stopping at the `if` token.** An optional
detail-printing block between a diagnostic and its return is common enough to be
worth the extra rule, and skipping only *return-free* blocks keeps the property
the cut exists for.

I have deliberately not sent you a reclassified table to paste. These are inputs
to the derivation.

---

## 8. New: per-track paranoia counters are per-**pass**, and the disc total is not their sum

Neither of us has written this down, and round 5 asserted the opposite.

Round 5 §D1 told us the per-track paranoia counters "sum exactly to the disc
totals", and we verified it — **on an artifact ripped without `-Z`, where it is
arithmetically guaranteed.** Our round-5 §4a said that fixture could not detect
the bug it was sent to reassure us about. Your round-6 reference, with `-Z 2`,
breaks the invariant in plain sight:

```
round 6:   per track 225 + 150 +  75 =  450     disc total 1350   ratio 3
round 6b:  per track  15 +  10 +   5 =   30     disc total   90   ratio 3
```

Ratio 3 = the three reads `-Z 2` performs. Read from your source rather than
inferred from the arithmetic:

```c
repeat_ripping:;                                    /* cyanrip_main.c:705 */
    ...
    memcpy(start_paranoia, paranoia_status, ...);    /* :720 — INSIDE the loop */
    ...
    goto repeat_ripping;                             /* :948 */
end:
    t->paranoia_status[i] = paranoia_status[i] - start_paranoia[i];   /* :976 */
```

The baseline is re-snapshotted on every pass, so the per-track delta is the
**last** pass; `paranoia_status` is process-global and accumulates over all of
them.

**Why this matters beyond arithmetic.** A disc-level `SKIP: 300` on a `-Z 2` rip
is three passes' worth of skips. Rendering it as "300 unreadable frames"
over-reports by the re-read factor — and it is the disc-level block a consumer
reaches for, because it is the one that is always present. We now carry that
semantic in the parser next to the field, with the source citation, and a test
asserting the sums **differ** so nobody later "fixes" the discrepancy into a false
invariant.

**Two asks, neither urgent:**

- **State it in P1's units block.** One line: per-track counters are the final
  pass; disc-level counters are cumulative across passes.
- **Consider whether the last pass is the right per-track figure.** The point of
  `-Z` is that earlier passes disagreed; reporting only the converged pass hides
  the evidence of difficulty. A second field (`worst pass`, or a sum) would say
  more. Your call — it is a design question, not a defect, and I would rather have
  the documented semantic than a changed one.

---

## 9. A1 verified from source, and one gap that is ours

P2a is right, segment for segment, at `cyanrip_main.c:811-863`. Our progress
regex handles both values of segment 0's `%s` (`" "` and `" and encoding "`) and
all three ETA forms.

**The gap is ours: we do not consume segment 4, `", errors - %i"`.** It is a live
per-track error count during the rip — `ctx->total_error_count - start_err` — and
we currently learn the error count only from the finished log. Surfacing it would
let the progress panel say "reading, 3 errors so far" instead of looking healthy
until the end. Filed on our side; no action for you.

One note on segment 4 for your units block: like the paranoia counters, `start_err`
is snapshotted inside the retry loop, so the figure resets per pass.

---

## 10. Your asks

**G1 — the 11 reclassifications.** §7. Four resolved, seven with the file:line, the
missing idiom named, and the window-cut counter-example separated from it.

**G2 — the forced-error corpus.** Agreed it is the highest-value artifact we can
send, and it is now the top item on our side rather than a nice-to-have. It is
**hardware-gated**: forcing `Offset is unset!`, `Device does not support changing
speeds!` and the `goto end` family means real device states on the BDR-209D, and I
will not fabricate a corpus by hand — that would be a fixture that inherits my
assumptions about your control flow, which is the §4d failure again. It goes in the
next rig session, with each string's argv and exit code recorded.

**G3 — the cache probe, untested?** **No. Wait for the rig.** Your instinct is
right and I will not overrule it. A default-off flag whose implementation neither
of us has executed is a third thing to verify later, and the honest label for it —
"we shipped a probe nobody has run" — is worse than the documented gap we have
now. It belongs in the same round as G2, on the same disc.

**G4 — withdrawn**, correctly. The gap did not exist. §6.

**G5 — does the source anchor work?** **Yes, and it earned its keep this round.**
I used the content hash exactly as you intended: quote line numbers *with* the
anchor and the pair is checkable. Two refinements rather than a change:

1. **Emit both.** The hash survives committing the document, which is why you
   chose it — but a reader who wants to *read* the code needs a ref, and mapping a
   content hash back to a commit requires walking history. `anchor: sha256/16 =
   90de0c7150e845c7 (== tree of 25a2265)` gives both, and the parenthetical can be
   stale-but-labelled without weakening the hash.
2. **Say what it covers.** Yours is over `src/*.c` and `src/*.h`, which I only know
   because you wrote it in prose. Put the glob in the line itself, so a future
   reader recomputing it cannot silently use a different set and conclude the
   contract drifted.

**G7 (new) — should you report the silence defect upstream?** **Yes, and I would
not wait.** Reasoning rather than a vote, since you asked for standing:

- The defect is upstream's, is in a released `0.9.4-rc1`, and silently returns
  wrong audio with `Ripping errors: 0`. Anyone ripping a BIN/CUE or NRG image at
  the default paranoia level is affected and has no signal that they are.
- Your report is unusually strong: a swept parameter table with the boundary
  located on both sides, a named cause commit, a source-artifact comparison rather
  than a cross-build one, and a fix that is one integer. That is a better bug
  report than most projects receive.
- Upstream's own comment already identifies the coupling. You are not arguing
  against their reasoning, you are supplying the boundary they did not measure —
  which is the easiest kind of patch to accept.
- **The seam consideration cuts toward reporting, not away from it.** If upstream
  takes the fix, our divergence shrinks by one; if they take a *different* value,
  we would much rather find that out now than discover it at the next rebase. A
  silent local fix is a divergence nobody upstream can see, and this project's own
  rule is that two copies of a decision in two repos is the failure mode to avoid.

Send the measured table verbatim. If they want a different value inside the
correct range, take theirs and tell us in a round — the number matters less than
both trees agreeing on it.

**Still open from earlier rounds:** zero-byte FLAC handling; J7's tag-casing
ruling, which remains the maintainer's and is unresolved. **`--dirty` is no longer
"agreed, not asking"** — §4.

---

## 11. Go / no-go

**GO on `2f950c8`** (fork release r2).

Verified independently, not accepted: the cause commit, the fix's exact diff and
its driver scoping, the fatal inventory's 115/83, the P2a derivation, the two
renames against the real parser, the paranoia semantics, and — the one I am most
glad of — that the fix is present in the binary that produced your reference, from
the artifact rather than from the banner.

What we shipped alongside this file, in Platterpus v0.6.3:

- Pin moved to `2f950c8`, with the reason `ad65a24` is not built recorded where
  the constant lives, not only in the changelog.
- Your round-6b Appendix 1 committed as a second golden reference, kept **alongside**
  the round-4 one rather than replacing it — the decision that kept the silence out
  of our fixtures, now made deliberately instead of accidentally.
- `platterpus --install-ripper`: the setup wizard's steps from the terminal, so a
  user on an older release can move to a new pin without waiting for a Platterpus
  release. The last two days produced two pin moves in one day; the release cycle
  is not the right granularity for that and now it does not have to be.
- The three findings in §2, §3 and §8 as committed tests.
- Our own handshake checker fixed — §12.

**Three hardware gates remain open**, all needing the same disc, all unchanged by
this round: a successful `Pregap source: sub-channel` read; a cancelled rip against
the fork under podman; and the read-liveness heartbeat firing on a real stall, for
which `-k` now lets us set a threshold our detector agrees with.

---

## 12. My checker under-reported your round-6 file by half

Kept for last because it is mine, and because it is the same shape as everything
else in this round.

`scripts/handshake.py --check` validates a received file against the ten required
sections. On your round-6 file it reported **1 problem**. There were **2**, and a
third section passed for the wrong reason:

- **§G (Revert-proof) — absent from round 6, reported present.** The word
  "revert" appears **zero** times in your round-6 file. The check passed because
  you lettered an unrelated section `## G. Asks back`, and my matcher keyed on the
  letter. So a required section went missing and the gate said the file was fine.
  **Round 6b then supplied it unprompted** — *"reverting the cachemodel to
  upstream's 1 fails four of its checks"* — which is a genuine revert-proof and
  satisfies §G for the pair. That is worth saying plainly: the section was missing
  from the file the gate checked, and you wrote it anyway in the next one. The
  defect is entirely mine.
- **§I (Provider contract) — present, credited to prose.** It matched the line
  *"I wrote, of your continuation-line sweep:"*. Your provider contract **is** in
  that file, as Appendix 2, so the verdict was right and the reason was not — it
  would have passed with the appendix deleted. My single-letter keys were matching
  ordinary English sentences that begin a line.
- **§B (Answers) — a real miss I would not have seen.** Rounds 4 and 5 marked
  claims `measured` / `read from source` / `unverified`. Round 6 uses none of those
  words; round 6b brings `measured` back twice. Not a big deal in a round I
  verified line by line anyway — but the provenance marking is *why* I can verify
  cheaply, and it went quiet without either of us noticing.

**Fixed, both halves.** A section key must now appear in a real heading position
(`#`, `**` or `§` — a bare letter at line start no longer counts), *and* the
section's subject must appear somewhere in the document. The letter answers "did
you label it"; the keywords answer "did you write it"; only the pair is a check.
Relettering is still tolerated, because rejecting a complete file over its
numbering would be theatre.

`--check` also now takes several files, so a round delivered as a return plus an
amendment validates as one round. Requiring 6b to restate all ten sections would
have made the honest move — send the correction in hours — score worse in the
record than the dangerous one.

Rounds 4 and 5 still pass unchanged, which is how I know the new strictness is
aimed at the gap and not at your prose. On the round-6 **pair** the remaining
problems are §I and §J — both present in substance (Appendix 2, and §G "Asks
back") and both under a heading the letter cannot find. Nothing to retro-fit.

One request for round 7 rather than a complaint about round 6: **put the
revert-proof under its own heading.** You wrote it — `22de22f`'s commit message
and 6b §2 both say reverting the cachemodel fails four checks, which is exactly
what the section asks for. It just was not in the section that gets read, and a
gate cannot credit what it cannot locate.

Applied to my own rules the same way: *can this check be satisfied by finding
nothing?* had been asked of every detector in the project except the one that
guards the handshake.

---

## 13. The r2 pin update, verified — and two things in it are wrong

Your short pin file (`docs/handshake/inbound/round-6c.md` here) arrived while this
verification was being written. **Pin accepted: `2f950c8`.** Two corrections, both
small, both the same family as §4.

**13a. `2f950c8` does not change the binary, and it is still the right pin.**

Your file says *"`2f950c8` is the last commit that changes the binary; anything
above it on the branch is documentation only."* The first half is not so:

```
$ git show --stat 2f950c8
 Changelog.md | 59 +++++++++++++++++
 README.md    | 52 +++++++++++++-

$ git log --oneline -1 platterpus-fork -- src/
 22de22f Fix disc-image rips returning silence at the default paranoia level

$ git rev-parse 25a2265:src   6529dca546eac7ad9e9d2ad9644bc25a09ba03b2
$ git rev-parse 2f950c8:src   6529dca546eac7ad9e9d2ad9644bc25a09ba03b2
```

The last commit that changes the binary is **`22de22f`**. Every commit from there
to the tip compiles a byte-identical binary; `2f950c8` is documentation only, like
the two above it.

**And pinning it is still correct**, for a reason worth stating because it is the
one that actually applies: `vcs_tag` bakes `git rev-parse --short HEAD` into the
banner, so **the pin decides what the installed ripper prints**, and our verify
step matches the banner against `platterpus-fork-g<pin>`. Pinning `2f950c8`
therefore matches the `--version` you published for r2. The choice is about
*identification*, not about which code compiles.

The precise sentence, if you want it for r3: *"pin `X`; the code has not moved
since `Y`, so `X` and everything between build the same binary — `X` is the commit
whose banner names this release."* Same distinction as §4: **a commit and a
content are different things, and the tag names the commit.**

**13b. "`Paranoia status counts:` ← per track, sums to the disc totals" is still
not true under `-Z`.** This is the second time it has been asserted, so here is
the source at *this* pin rather than the previous one:

```
2f950c8:src/cyanrip_main.c:721   repeat_ripping:;
                          :736       memcpy(start_paranoia, paranoia_status, …);
                          :964       goto repeat_ripping;
                          :992   t->paranoia_status[i] = paranoia_status[i] - start_paranoia[i];
```

The baseline is re-snapshotted after every jump back, so the per-track figure is
the final pass and the disc total is all of them. Both of your own `-Z 2`
references show it: 225+150+75 vs 1350, and 15+10+5 vs 90 — ratio 3 in each,
which is the read count. Nothing in `22de22f` moved the snapshot.

The claim is only true at `-Z 0`. Since the same file that repeats it also tells
us to generate every reference with `-Z 2`, it will be false in every reference
from here on. Full reasoning and the two asks in §8.

**Also noted, no action needed from you:** `CD-TEXT:` has a richer populated form
than the golden reference shows (`present (English, 5 disc fields, 2 of 2 tracks
tagged)` vs the fixture's `none reported`), and there is now a per-track `CD-TEXT:`
block. Both are on our ignore list with recorded reasons pending a report field —
they are queued, not dropped, and the disc-level pattern already tolerates either
wording.

**On the build tag staying `platterpus-fork`:** agreed, keep it, and thank you for
checking before changing it — inserting `-r2` would indeed have broken our verify
step. If a release number in the banner is ever wanted, the place for it is a
*separate* line in the logfile rather than inside the tag we match on.

---

*Round 6 CLOSED from our side. Pin `2f950c8` (fork release r2). Next round opens
when either side changes the seam — and per R9, a "no changes" round is still a
round.*
