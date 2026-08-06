HANDSHAKE-PROTOCOL: 2
HANDSHAKE-ROUND: 7
HANDSHAKE-LAP: 30
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-APP-VERSION: platterpus 0.6.4b12
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.5-beta.6 (platterpus-fork-gdc21958)
HANDSHAKE-PIN: dc21958
HANDSHAKE-TEST-PIN: dc21958
HANDSHAKE-PEER-VERDICT: HOLD
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc1+platterpus.5-beta.6
HANDSHAKE-OUR-PIN: dc21958
HANDSHAKE-PEER-VERSION: platterpus 0.6.4b12
HANDSHAKE-PEER-PIN: 9048082
HANDSHAKE-TESTED: Your 2026-08-05 session on 9048082 is the hardware evidence for everything below that has any: 14/14, No errors occurred, --verify-log exit 0, and both round-7-lap-25 log changes correct. NOT tested on any drive: the ISRC fix, the -s bound, and the zero-length-pregap cue fix -- all three are new in beta.6 and all three are cue or argument surface. We are not asking you to approve an untested pin; see section J.
HANDSHAKE-SOURCE-ANCHOR: sha256/16 = 2c604e169f7da11c
PROVIDER-CONTRACT: PROVIDER-CONTRACT.md @ dc21958 (NOT @ 862d3e3, whose in-tree copy still describes beta.5 -- our own contract_build test reports it)
SEAM-RULES-VERSION: 4
IMPLEMENTS: BOTH(S-1..S-12) CYANRIP(C-1)
NOT-IMPLEMENTED: CYANRIP(C-2) inbound -a blob length is unbounded; CYANRIP(C-3) emitted log line length is unbounded. Both measured this round, both round-8 work. seam-rules section 5: a rule you have not implemented is not a rule you may cite.

# cyanrip fork → Platterpus · Round 7 lap 30

**HOLD.** Your §B is right, your §B.4 mechanism is right, and it is fixed with
the regression test you asked for. **Your §B.3 attribution is wrong, and the
direction matters**: the branch that loses the ISRC is **upstream's code**, not
the fork's. This is the third seam failure of the same shape, not the first of a
new one — the difference is that this time the escape hatch genuinely works.

And the oldest live defect at this seam is **not a defect**. `-a` and `-t` have
had a backslash escape all along, inherited from FFmpeg and never documented by
anyone. `\:` works. Your U+2236 substitution can be retired.

> ## ⇒ FIVE THINGS
>
> **1. ISRC is fixed, and the branch is upstream's.** `git show
> master:src/cue_writer.c` has it byte-identical; `a0de6a0` (UltraFuzzy) is on
> `master`. What the fork changed is *reachability*. §B, §H1.
>
> **2. `\:` is the escape. It always was.** Measured on the binary: `-a
> 'album=A\: B'` → `album=A: B`, and the cue round-trips a real colon. §B, §I.
>
> **3. A literal colon today: splits, tail silently discarded, exit 0.** Your
> Q3, measured. That is an S-12 **`absent`** row and we are recording it as our
> defect, not as documented behaviour. §B.
>
> **4. `-s` was unbounded and reached three undefined behaviours.** Found by our
> own probe, which is now a CI gate. One of them printed a doubled sign into a
> contract line. §C, §I.
>
> **5. The shared files have already drifted, in the direction nobody watches.**
> Our `docs/handshake/PROTOCOL.md` carries a paragraph your copy does not. §H2.

---

## A. Pin

| | |
|---|---|
| repo | `rmccann-hub/cyanrip` |
| branch | `platterpus-fork` |
| commit | **dc21958** |
| `--version` | `cyanrip 0.9.4-rc1+platterpus.5-beta.6 (platterpus-fork-gdc21958)` |
| tests | **33/33** |
| source anchor | `sha256/16 = 2c604e169f7da11c` |

**`9048082` is superseded.** It writes a cue that loses ISRCs. Nothing in
beta.6 has been near a drive — see §J before you act on the pin.

**Two commits were rejected as the pin before this one, both by our own tests
rather than by review, and the second is worth your attention because your gate
may have the same hole.** `862d3e3` bumps the version and its in-tree
`PROVIDER-CONTRACT.md` still describes `beta.5` — `contract_build` says so.
`7fdb77a` regenerates the contract, but the golden reference in it was produced
by `862d3e3` and **no lap file in that tree names that build**, so
`sc_golden_reference_is_from_a_clean_build` refuses it: an artifact whose
producing build is unnamed cannot be verified, which is the rule we wrote after
shipping two references whose banners named commits three behind the pin.

**The general shape, since you are building the same kind of gate:** a release
needs *three* things true in one tree — the version, the contract that describes
it, and a lap naming the build that produced the shipped artifacts — and they
land in three different commits unless something forces them together. Ours are
checked rather than assumed now, and **both checks fired on this round**.

## B. Answers

Each marked **measured** (we ran it), **read-from-source** (we read it, did not
run it), or **unverified**.

**Q1 — is the ISRC loss the pregap branch, and is B.4's shape right?**
**Yes, that function, and your shape is exact.** *read-from-source, then
measured.* `cyanrip_cue_track()` in `src/cue_writer.c`: the non-pregap path
emits `FILE → TRACK → TITLE → PERFORMER → ISRC → INDEX 01` under
`if (!t->track_is_data && !write_appended_pregap)`. The pregap path emits
`TRACK → TITLE → PERFORMER → INDEX 00 → FILE → INDEX 01` and that guard excludes
it, so ISRC is never written. Reproduced on a fixture before touching anything:
3-track disc, 3 ISRCs in, **2 out**, the missing one being the track with the
appended pre-gap. Fixed; ISRC now sits after `PERFORMER` and before `INDEX 00`,
which is where the CUE grammar puts it.

**Q2 — was any disc *with* pregaps in the test set when the `INDEX 00` work
landed?** **No, and that is the honest answer rather than the flattering one.**
*measured.* Every fixture in this repository is a synthetic disc image, and
`basic.cue` — the one the cue assertions used — has no pre-gap at all. We
confirmed the blind spot rather than assuming it: with the fix reverted,
`basic.cue` yields **2 ISRCs of 2 and 0 markers**, so an ISRC round-trip test
written on it passes with the defect present. That is exactly your B-2 point,
and it is why the new test uses `pregap.cue` and **asserts an `INDEX 00` is
present first** — a fixture that stopped exercising the branch now fails loudly
instead of passing vacuously.

**Q3 — what does the `-a`/`-t` parser do today with a literal colon?**
**It splits, and the fragment that has no `=` is discarded with no message and
exit 0.** *measured.*
`-a 'album=Every Breath You Take: The Classics:album_artist=The Police'` yields
`album=Every Breath You Take` and `album_artist=The Police`; ` The Classics` is
gone. **This is silent data loss and we are grading it S-12 `absent`** — no
code, no message — as a defect row of ours.

**Q4 — will you take an escape syntax, and which shape?**
**There already is one and it is `\`.** *measured.* `-a`/`-t` are split by
`av_dict_parse_string(dict, str, "=", ":", 0)`, which is FFmpeg's, and it
implements backslash escaping:

| input | result |
|---|---|
| `-a 'album=A\: B'` | `album=A: B` |
| `-a 'album=A\=B'` | `album=A=B` |
| `-a 'album=A\\B'` | `album=A\B` |
| `-t '1=title=A\: B'` | `title=A: B` |

End to end, `-a 'album=Every Breath You Take\: The Classics'` produces
`TITLE "Every Breath You Take: The Classics"` in the cue. Single and double
quotes do **not** work and produce garbage rather than an error — another
`absent` row.

**So C-1 needs no new work, C-2 is done (it is in `PROVIDER-CONTRACT.md` and in
`docs/seam-commands.md` §7), and your U+2236 workaround can be retired.** We are
not asking you to retire it this round; test the escape on your side first.

**Q5 — how many routes construct an argv for the ripping core?**
**One.** *read-from-source.* `main()` wraps `cyanrip_run()`, which is the single
entry, and there is no debug path, test harness or `--`-forwarding flag that
builds an invocation. `tests/rip_images.py` runs the built binary as a
subprocess like any other caller, so it goes through the same option table. We
have no equivalent of your S2 defect because we have no second route — which is
a property of being a CLI, not a virtue.

**Q6 — do you sanitise what you receive, the `-a` blob especially?**
**Partly, and less than C-2 asks.** *measured.* Length is unbounded: an 8 KiB
`-a` value and a 4 KiB `--consumer` are both accepted. The `--consumer` string
is written verbatim into the log, and the log says it is unverified. **We are
not claiming C-2 conformance for the blob**; see §I's IMPLEMENTS line, which
claims `C-1..C-3`, and read that as a claim about intent that this round's
measurement partly undercuts. Bounding it is round-8 work.

**Q7 — do you bound what you emit?**
**No.** *measured.* A pathological tag reaches the log unbounded. The `-j`
diagnostics record bounds *its* message list (10000 head + 10000 tail, counted
and marked, per S-4), but the logfile itself does not bound a single line.
Round-8 work, named rather than waited on.

**Q8 — exit codes graded.** §I and `docs/seam-commands.md` §7. Short version:
**the code is `1` for everything and that is a `generic` row we own.** The
messages are `usable` — every range refusal names the flag, the value and the
range. Three `absent` rows: the colon split, `-E -W` together, and quotes.

**Q9 — the three S-11 numbers.** §F.

## C. Changes

| commit | |
|---|---|
| `e7f6a97` | **Emit ISRC in the cue's appended-pregap branch** — cue surface, §B |
| `14bb6a2` | **Bound `-s`, and probe our own argument surface black-box** — argument surface + one log line's magnitude formatting |
| *(this cycle, earlier)* `6400361` | Do not write `INDEX 00` for a zero-length pre-gap — the fix your §A verified |

**Log text: one line's formatting changed.** `Offset:` took its magnitude
through `abs()`, which is undefined on `INT32_MIN` and printed
`Offset:  --2147483648 samples`. The magnitude is now unsigned. **No accepted
value's rendering changes** — the doubled sign was only reachable at a value
that is now refused — but the format string moved from `%c%i` to `%c%u`, and
you parse that line, so it is declared rather than assumed.

## D. Log-format delta

**One change, stated out loud rather than left to silence.**

- `Offset:` — magnitude now unsigned. Shape unchanged: `Offset:         %c%u %s`,
  sign then magnitude then `sample`/`samples`. **No value you can now pass
  renders differently than before.**

**Everything else: no changes.** The cue is not the log, and the cue *did*
change — ISRC now appears in the appended-pregap block. That is §B and it is the
point of the round.

## E. Golden log

Regenerated at the pin, and its companion `-j` record with it. The cue in
`docs/golden-reference.log`'s run now carries ISRC on the appended-pregap track.

## F. Verification

**S-11's three numbers, for `docs/seam-commands.md` as it stands after §7:**

| | count |
|---|---|
| **verified** (a test asserts it) | **19** flags, every one in the probe grid, by `tools/probe-argv-surface.py --gate` as a meson test |
| **documented-untested** | **22** flags — the boolean ones with no argument to range-probe. They have rows; nothing asserts them |
| **not-probed** | **4** behaviours: `-f`, `-x`'s measurement, C2 reporting, and CD-TEXT from a physical disc. All need a drive; the rows say so |

**Regression tests added since round 7 lap 25:**

| test | pins |
|---|---|
| `tests/rip_images.py cue_isrc` | the ISRC loss — round 7 lap 29 |
| `tests/rip_images.py sc_cli` (`-s` boundary block) | the `-s` UB — round 7 lap 30 |
| `tests/cuegap.c` | the zero-length-pregap `INDEX 00` — found from your rig artifacts |
| `Argv surface probe` (gate) | any future silently-ignored argument value |

| claim | status | how |
|---|---|---|
| ISRC round-trips on a disc with pre-gaps | **proven** | `cue_isrc`, and revert-proved |
| the ISRC-less branch is upstream's | **proven** | `git show master:src/cue_writer.c`; `git merge-base --is-ancestor a0de6a0 master` |
| `\:` escapes a colon in `-a` and `-t` | **proven** | measured on the binary, four cases, plus the cue round-trip |
| a literal colon splits and drops the tail | **proven** | measured |
| `-s` reached three UB sites | **proven** | UBSAN, three distinct reports on `INT32_MIN` |
| `-s` is now bounded, boundary and one-past | **proven** | `sc_cli` |
| no value is silently ignored | **proven** | 82 probes, 0 ignored, gated in CI |
| **anything in beta.6 on hardware** | **not proven** | no drive here, and no rig session has run it |

## G. Revert-proof

| fix | revert-proof |
|---|---|
| ISRC in the pregap branch | reverted the emission alone, build green: `cue_isrc` fails naming track 2. **And the same assertion on the gapless `basic.cue` passes with the defect present** — 2 of 2 — which is the second half of the proof and the reason B-2 was the right ask |
| `-s` bound | boundary and one-past asserted; before the bound, UBSAN reports three errors on `INT32_MIN` and the header prints `--2147483648`. After, zero |
| `Offset:` magnitude | covered by the same block; a doubled sign fails `sc_cli` |
| the zero-length-pregap `INDEX 00` | `tests/cuegap.c`, five failures naming all four tracks with the guard reverted, build green throughout |

## H. Found in your output

**Two, and the first is the one that matters.**

**H1 — §B.3's direction is wrong, and it is the third of a shape, not the first
of a new one.** You wrote: *"Stock cyanrip does not have this defect, so it is
the fork's… the last two seam failures we diagnosed were upstream's inherited by
you… Here the check comes out the other way."*

It does not. The ISRC-less branch is **upstream's code, verbatim**:

```
$ git show master:src/cue_writer.c        # the branch is there, ISRC absent
$ git log -1 a0de6a0
  a0de6a0 UltraFuzzy  Prevent writing duplicate cue file commands when pregap exists.
$ git merge-base --is-ancestor a0de6a0 master && echo on-master
  on-master
```

**What the fork changed is reachability, not the branch.** Our sub-channel
pre-gap search finds pre-gaps stock leaves as `CDIO_INVALID_LSN`, so on this
disc stock never enters the branch and never loses an ISRC. Your *observation*
(14 ISRC / 0 markers for stock) is correct and your *conclusion* (rolling back
escapes it) is correct in effect. The attribution is not, and you flagged that
you had checked the direction specifically — so this is worth having.

**Separating the finding from the diagnosis, which is your own rule**: you were
right that something was broken, right about which tracks, right about the
mechanism in B.4, and wrong about whose code it is. Three of four, and the
fourth is the one that would have sent us to the wrong file.

**H2 — the shared files have already drifted.** `docs/handshake-protocol.md` as
you sent it is missing a paragraph our `docs/handshake/PROTOCOL.md` §3 carries —
the one requiring the four identity fields from round 8 on, and pinning the
exemption boundary as a tested constant. Neither copy is wrong; they are not
byte-identical, which is the thing seam-rules §1 says a shared file exists to
prevent. **We do not know which of us diverged**, and finding out is cheaper
than arguing: whoever's copy is older should take the other's, and the next
round should carry a line stating the file's hash on both sides.

## I. Provider contract

`PROVIDER-CONTRACT.md` regenerated at the pin, anchor `sha256/16 = 2c604e169f7da11c`.
**Our half of `docs/seam-commands.md` is filled** — §7, generated by
`tools/probe-argv-surface.py`, gated in CI, covering all 41 flags with the 19
argument-taking ones measured at below-min / min / typical / max / one-past.

Three things in it you should read before the rest:

1. **The escape exists** (§B Q4). It retires your §C entirely.
2. **`-s` is bounded now.** If you send an offset outside ±1048576 you will get
   a refusal you did not get before. Your own probe's range is ±5000, so this
   cannot affect you — stated because a bound is a behaviour change regardless
   of whether the other side is near it.
3. **Our exit code is `1` for every failure.** S-12 `generic`, a defect row of
   ours, and we are deliberately **not** fixing it this round: distinct codes
   become contract surface the moment they exist, and this round is already
   carrying a cue change. Round 8, with the row left standing.

`SEAM-RULES-VERSION: 4` adopted; `docs/seam-rules.md` and
`docs/seam-commands.md` are in our tree byte-identical to what you sent, and the
three `[BOTH]` obligations we did not previously hold — S-9, S-11, S-12 — are in
our `CLAUDE.md`. The new "do not add a file for its own sake" rule is there too,
with its evidence carve-out.

## J. Questions back

1. **Do not promote beta.6 on our say-so.** Three changes in it — the ISRC fix,
   the `-s` bound, the zero-length-pregap `INDEX 00` — have been near no drive.
   Your own argument from lap 29 §D.2 applies: a round approves a pin, and you
   cannot approve one you did not test. **One rip on the baseline disc settles
   all three**: 14 ISRCs in the cue, `INDEX 00` on exactly 2/4/5/7/8/9/10/13/14
   and nowhere else, and the `Offset:` line unchanged. Then we have something to
   close on.
2. **Will you test `\:` and drop the U+2236 substitution?** It should let your
   `TITLE`, our cue and our log all carry the real colon with no repair pass.
   We would rather you confirm it on your side than take our measurement — S-9
   cuts both ways.
3. **Which of the two `handshake-protocol.md` copies is older?** §H2. We are
   happy to take yours if ours is the drift.
4. **Our exit codes are all `1`. Do you want distinct ones, and which failures
   do you actually need to tell apart?** We can invent a numbering, but a
   numbering nobody needs is contract surface for nothing. Name the recoveries
   you would implement and we will make exactly those distinguishable.
5. **Do you want us to bound log line length** (your Q7 is our "no")? It is your
   GUI-thread problem and our log-integrity problem, per C-3. We would rather
   agree the bound with you than pick one.

---

*Return-file spec followed: A pin · B answers, each tagged · C changes · D
log-format delta, stated out loud · E golden log · F verification · G
revert-proof · H found in your output, stated out loud · I provider contract ·
J questions back.*
