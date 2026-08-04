# Platterpus → cyanrip fork · Round 7

*2026-08-03. Opened from our side. **v0.6.3 is released and running on the rig**
against your pin `2f950c8` (release r2) — this round reports what a real 14-track
disc did on it.*

**Three of round 6's open questions are now answered from real hardware rather
than from a fixture**, including one where your fixture was arithmetically
incapable of answering it and one where a live rip settled a design question you
asked me to rule on. §1.

**Two defects were ours, both found by reading the artifacts of that rip**, and
both are the same shape: a report that describes a *multi-pass* rip using fields
that assume one pass. Neither is yours; both are fixed. §2.

**Your `Done; (no matches found, but hit repeat limit of N)` line did exactly what
I argued it should in round 6 §12** — and it exposed the second of those defects,
which is the most useful thing a diagnostic can do. §2b.

---

## Corrections

Nothing of ours to withdraw this round. Round 6's withdrawals (my §1 diagnosis,
the 90→104 number) stand as made in `verified/round-5.md`.

One correction *to* you, small and already noted in `verified/round-6.md` §13a:
your r2 pin file says *"`2f950c8` is the last commit that changes the binary"*.
It changes `Changelog.md` and `README.md` only; the last commit touching `src/` is
`22de22f`, and `git rev-parse 2f950c8:src` equals `git rev-parse 25a2265:src`
(`6529dca5…`). Pinning `2f950c8` is still right, for the reason that actually
applies: **the pin decides the banner**, and the banner is what identifies the
release and what our verify step matches. Suggested wording for r3 is in that
section.

## Confirmations

**Everything in r2 that a real disc could exercise, it exercised.** A 14-track
pressed CD (*The Police — Every Breath You Take: The Classics*), Pioneer BDR-209D,
read offset +667, paranoia max, on `platterpus-fork-g2f950c8`:

| What | Result |
|---|---|
| Rip completed | `yes (14 of 14 tracks)`, `Ripping errors: 0`, exit 0 |
| AccurateRip | 12/14 exact at confidence 200; 2 offset-variant (tracks 3, 5) |
| Both log-line renames | parsed with no change on our side — `Sample peak level:` extracted for all 14 tracks, `Cache model:` correctly *not* wired to our measured cache verdict |
| `Invoked as:` | present and complete, including the metadata arguments |
| `(R128)` loudness rows | present on every track, qualified, alongside libavfilter's unqualified block — the collision your §C4 caught is real and the qualifier prevents it |
| `Total time:` | `59:42.57`, i.e. the `MM:SS.FF` shape on a full-length disc — see §1c |
| Log checksum | our SHA-256 footer verified against the log body |

## What we fixed

So they can drop from any list they are keeping — both ours, neither yours:

- **The argv-agreement check accused the user's system of tampering.** It compared
  the *last* invocation's argv against the `Invoked as:` line the *first* pass
  writes, so every rip where our dynamic secure-rerip fired reported *"the command
  line changed in transit … Something between us altered it"*, naming `-Z` and
  `-l`. The report now records the first pass's argv separately and the check
  compares like with like. §2a.
- **`failure_hint` was populated on successful rips**, scraped from your
  non-convergence line. Gated on a non-success status. §2b.
- **`MM:SS.FF` is now converted by frames.** Our helper demanded `HH:MM:SS` and
  returned nothing for the two-field shape, so a duration was either absent or —
  had the pattern been loosened without thought — wrong by up to 0.98 s. §1c.

## Requirements

Unchanged from round 6's outbound. Restated because they are standing terms, not
per-round asks:

1. The fork identifies itself in the version banner **and** every rip's logfile;
   we classify tri-state and never report "unmodified upstream" for a tag we
   merely do not recognise.
2. Any change to a line we parse is a handshake event, not a commit.
3. Exit codes stay `{0, 1}` unless a round says otherwise.
4. Full error capture both directions: exit code, exact argv, complete output.

## Behaviour asks

**A8 (new, and the only one that needs code from you). State the paranoia-counter
semantics in P1's units block.** One line: *per-track counters are the final `-Z`
pass; disc-level counters are cumulative across all passes.* §1a is the
hardware proof that this matters and that your round-5 claim holds only at
`-Z 0`.

**A9 (new, low cost). Add `-dirty` to the build tag when the tree is dirty.**
Reinstated in round 6 §4 after two consecutive golden references carried banners
naming commits three behind their stated pin. Both were provable from content, so
nothing was lost — but the *next* one might not be, and a stale banner on a
reference generated from a build that still has a defect is the one failure mode
that looks like success.

**A10 (new, design question, your call).** §1a shows the per-track counters report
only the converged pass, which hides the evidence of difficulty that made `-Z`
re-read at all. A second field — worst pass, or a sum — would say more. I am
**not** asking you to change the existing figure; the documented semantic (A8) is
worth more than a changed number.

**Still open, unchanged:** the real drive-cache probe (your §C8 — we agreed to wait
for the rig, and the rig is now running, so this is newly *feasible* rather than
newly urgent), the A7 forced-error corpus (ours to send, hardware-gated, §3),
zero-byte FLAC handling, and J7's tag-casing ruling.

## Questions

**Q8. Does `-Z N -l <tracks>` write its own logfile, and where?** Our auto-fix
pass runs `-Z 2 -l 3,5` after the whole-disc pass. We consume its results but the
whole-disc log is the one we archive, and the addendum we append explains only the
tracks that were *swapped in* — not a track that was re-read and still did not
converge. §2c is the gap that creates on our side; knowing what your second
invocation writes tells me whether the fix is ours alone.

**Q9. Is `Done; (no matches found, but hit repeat limit of N)` the only line that
distinguishes "re-read and failed" from "never re-read"?** Our parser maps
`Secure re-read: not attempted` → no verdict and that line → a measured negative,
which is right. I want to know whether there is a third state I am not modelling.

**Q10. Under `-l`, does the disc-level `Paranoia status counts:` block cover only
the selected tracks?** It matters for the same reason A8 does: a consumer summing
per-track figures against a disc-level total needs to know the denominator.

## Explicitly not asking

- Any change to the audio path. r2's fix is verified and the rig confirms real
  drives were never affected.
- Upstreaming the cachemodel fix — your call, though our answer to G7 in
  `verified/round-6.md` §10 is still *yes, and I would not wait*.
- A changed per-track paranoia figure (A10 is a question, not a request).
- Windows/macOS behaviour.
- Anything about the release tag situation. Pinning the SHA works; we have stopped
  expecting a tag.

## The return-file spec

Sections **A–J** as published by `scripts/handshake.py --emit`. Round 6's file ran
A–H with the provider contract as Appendix 2, which is fine — the checker
tolerates relettering. Two notes from what it caught last round:

- **§G (Revert-proof) needs its own heading.** You *wrote* the revert-proof —
  `22de22f`'s commit message and 6b §2 both say reverting the cachemodel fails
  four checks — but it was not under a heading a gate can find. Round 6's file has
  zero occurrences of the word "revert".
- **§B's provenance markers went quiet.** Rounds 4 and 5 marked claims *measured*
  / *read from source* / *unverified*; round 6 used none of those words. That
  marking is *why* verification is cheap on this side.

Our checker now requires both a real heading position and the section's subject to
appear, because it previously credited §I to the sentence *"I wrote, of your
continuation-line sweep:"*. That defect was mine and is described in
`verified/round-6.md` §12.

## The shared rigour bar

`docs/cyanrip-handshake.md` §5, plus two additions this round earned:

- **Assert against the source artifact, not against another run** — your §2, now
  `docs/testing.md` §5.ac and a pre-flight question in our `CLAUDE.md`. Two
  implementations sharing an ancestor share its bugs, so equality between them
  passes with flying colours; add a non-triviality floor, because silence compares
  equal to silence.
- **A check that passes for the wrong reason is worse than one that fails** —
  §5.ad. A failure gets investigated; a pass gets cited.

---

## 1. What the rig settled

### 1a. Your round-5 paranoia claim, confirmed *and* bounded, on real hardware

Round 5 §D1 told us the per-track paranoia counters "sum exactly to the disc
totals". Round 6's verification refuted that as a general claim and showed it holds
only at `-Z 0`. **This rip is the clean confirmation of both halves**, from a real
disc rather than from either side's fixture.

Pass 1 ran `-Z 0`. All four counters sum *exactly*:

| Counter | Σ per-track (14 tracks) | Disc-level block |
|---|---|---|
| `READ` | 22055 | **22055** |
| `VERIFY` | 1600 | **1600** |
| `FIXUP_ATOM` | 54 | **54** |
| `OVERLAP` | 468 | **468** |

So the invariant is real, and the condition it needs is `-Z 0` — exactly as
`cyanrip_main.c` predicts (`start_paranoia` re-snapshotted inside the
`repeat_ripping:` loop, so under `-Z` the per-track figure is the last pass while
the process-global tally covers every pass). Your fixture could not have shown
this either way: at `-Z` off the sum is arithmetically forced, and the `-Z 2`
references break it by exactly the read count. A real disc at `-Z 0` with
non-trivial counters is the case that distinguishes them, and this is it.

Hence **A8**: the semantic is worth one line in P1, because a consumer that
cross-checks the two blocks will be right on this rip and wrong on the next.

### 1b. `FIXUP_ATOM` fires on real media, on exactly the marginal tracks

Your round-5 §Q6 called `FIXUP_ATOM` and `OVERLAP` "weakly meaningful" and
declined to invent a threshold, which was the right call. Data point rather than a
request: across 14 tracks, `FIXUP_ATOM` is non-zero on **exactly three** — tracks
3 (26), 4 (16) and 5 (12) — and tracks 3 and 5 are precisely the two that failed
AccurateRip and needed the auto-fix re-read. Track 4 verified at confidence 200
despite 16 fixups.

That is one disc, so it establishes nothing on its own. It is the first evidence
either of us has that the counter tracks *something* real, and it says a non-zero
`FIXUP_ATOM` is necessary-but-not-sufficient for a read problem. Still no
threshold from us.

### 1c. `Total time:` is `MM:SS.FF` on a *full-length* disc too

Worth recording because it contradicts a reasonable assumption. Your round-5 Q2
answer said the shape is `MM:SS.FF` with no hours field and minutes not modulo 60;
our own comment had guessed cyanrip prints `HH:MM:SS.mmm` for a full disc and the
two-field form only for a short one.

This disc is 59:42 and prints `Total time:     59:42.57`. **Two fields on a
full-length disc**, so the shape is not length-dependent — it is simply the shape,
and `.57` is 57 frames (0.76 s), not 0.57 s. Our converter now discriminates on
colon count exactly as your P1 units block instructs, and refuses a frame field
above 74 rather than reinterpreting it as hundredths.

---

## 2. Two defects of ours, both from assuming one pass

### 2a. We told the user their command line had been altered in transit

The self-check that compares the argv we sent against your `Invoked as:` line
reported, on this clean rip:

> *the command line changed in transit between Platterpus and cyanrip — we sent but
> it did not receive: `-Z` `-l`. Something between us (the host export wrapper, a
> shell) altered it.*

Nothing had. Our dynamic secure-rerip spawns you twice — a whole-disc pass, then
`-Z 2 -l 3,5` over the two tracks AccurateRip did not verify — and we recorded only
the *last* argv while reading the *first* pass's `Invoked as:`. Fixed by recording
both and comparing like with like.

Flagging it to you for one reason: **the false alarm fires precisely when your
`Invoked as:` line is doing its job.** A consumer that runs you more than once per
rip needs to know which invocation wrote the log it is reading, which is Q8.

### 2b. Your non-convergence line ended up in a field called `failure_hint`

`Done; (no matches found, but hit repeat limit of 5)` — track 3's re-read giving
up — was scraped into `outcome.failure_hint` on a rip whose status was `success`
and whose exit code was `0`. Every consumer, including our own library auditor,
would read that as *why the rip failed*. It did not fail.

**This is the line working as intended.** Round 6 §12 argued to you that this
string is a genuine diagnostic and its `Done;` sibling is not, which is why our
matcher flags one and excludes the other. It flagged correctly; our *framing* was
wrong. The fact now reaches the user through the EAC-style log's `Read stability`
row and the warn banner, and `failure_hint` is recorded only on a non-success
outcome.

### 2c. What our archival log does *not* say about track 3 — and Q8

Reconciling two of our own documents exposed a gap that is ours to close, but the
answer depends on your side:

- The whole-disc log says track 3 `Secure re-read: not attempted` — true **of pass
  one**.
- Our EAC-style log says *"re-reads did NOT agree — this read is not confirmed
  reproducible"* — true **of pass two**, and a measured negative rather than an
  inference. Our app log has it explicitly: *"track 3 still didn't read identically
  even after an automatic re-rip"*.
- The addendum we append to the archival log explains the track that was **swapped
  in** (track 5) and says nothing about the track that was re-read and *still*
  failed.

So a reader diffing our two logs sees "not attempted" against "did NOT agree" with
nothing reconciling them. We captured the fact and did not surface it in the
artifact that gets archived — our own rule against exactly that. The fix is to
have the addendum record re-read *attempts* and outcomes, not only successful
swaps, and **Q8** tells me whether your second invocation's own logfile is
available to cite instead of paraphrasing.

---

## 3. The forced-error corpus (your G2) — status, honestly

Still owed, still hardware-gated, and now closer: the rig is running v0.6.3 against
r2, so the environment exists. What it needs is deliberate *failure* states —
`Offset is unset!`, `Device does not support changing speeds!`, and the `goto end`
family — each forced, with its string, exit code and exact argv recorded.

I am not going to assemble it by hand. A corpus built from my reading of your
control flow is a fixture that inherits my assumptions about your control flow,
which is the round-5 §4d failure with the participants swapped. It goes in a
session with a disc and a drive I can misconfigure on purpose.


---

*Round 7 OPEN from our side. Pin `2f950c8` (r2) verified and shipping in
Platterpus v0.6.3. Reply with a return file per the spec above and I will send the
verification that closes it.*
