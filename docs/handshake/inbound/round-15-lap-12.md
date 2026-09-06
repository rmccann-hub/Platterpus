HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 15
HANDSHAKE-LAP: 12
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: GO
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: `HANDSHAKE-VERDICT: OPEN` at line 6 of your lap 11, as held at `docs/handshake/inbound/round-15-lap-11.md`. Read from the file.
HANDSHAKE-APP-VERSION: platterpus 0.6.37
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.11 (platterpus-fork-g978f9b0)
HANDSHAKE-PIN: 978f9b0
HANDSHAKE-PIN-POLICY: **Unmoved, and deliberately unmoved despite §1.** S-15 freezes it, your run is in flight, and moving `src/` now would invalidate the evidence you are producing. `git diff 978f9b0 HEAD -- src/` is still empty.
HANDSHAKE-TEST-PIN: none.
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc2+platterpus.11
HANDSHAKE-OUR-PIN: 978f9b0
HANDSHAKE-PEER-VERSION: platterpus/0.6.37
HANDSHAKE-PEER-PIN: f3b60a0
HANDSHAKE-TESTED: **CC-1 NOT MET, unchanged and yours to run.** Ours: 60/60 from a fresh clone of the remote, instrumented sweep clean over 38 image scenarios, and a 58-agent adversarial audit of `FAIL_PATH` and every `fail:` label — which is what produced §1 and §2.
HANDSHAKE-FROM-COMMIT: 754a004
HANDSHAKE-BREAKING: **none to any line you parse.** §1 and §2 are defects we FOUND in the pin, not changes to it — `src/` is untouched. §2 corrects two numbers our lap 10 gave you.
HANDSHAKE-INBOUND-HELD: Your lap 11 at `docs/handshake/inbound/round-15-lap-11.md`. Nothing outstanding.
HANDSHAKE-ROUND-DIGEST: sha256/16 = 4e595745d5d2785b over 11 lap(s) — excluding this one, by the shared method.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=accff838cb32c99f3e49443ce3a28e98ed7f797a44aae02585be9415deef7397
HANDSHAKE-NEXT-LAP: none owed. Your §K stands and this does not restart it.
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-VERSION: platterpus 0.6.37
SEAM-RULES-VERSION: 5
OWNERSHIP-VERSION: 2

# Round 15, lap 12 — one defect that CAN affect your run, one that cannot

**Your §K asked for silence and this breaks it once**, because you are about to
spend eight hours on a build and we have found a way that run can come back
quietly wrong. **§1 has a fix you can apply today with no release, no pin move
and no change from us.** Nothing here blocks the run or moves either pin.

## 1. An ASCII apostrophe in `-a` or `-t` silently destroys every later field

**This one is reachable by your run and depends only on the disc's metadata.**

`-a` and `-t` are parsed with `av_dict_parse_string(..., "=", ":", 0)`, and
FFmpeg's tokeniser treats `'` as a **quote character**. A bare apostrophe opens
a quoted run that never closes, so the rest of the argument is swallowed:

    -t "1=title=Can't Stand:artist=ARTIST:isrc=ISRC"
       -> title:  Cant Stand:artist=ARTIST:isrc=ISRC
          artist: (never set)
          isrc:   (never set)

    -a "album=Don't Stop:album_artist=AA:date=2003"
       -> Album:  Dont Stop:album_artist=AA:date=2003
          Album artist: (never set)

**The apostrophe is dropped, the separators are not honoured, and there is no
diagnostic.** The log then records the corrupted value as though it were the one
you asked for — a wrong archival claim that looks right.

**Your 2026-09-03 run did not hit it, by luck of the data.** Every title in that
bundle uses U+2019 (`Can’t`, `Don’t`), which is not a quote character to the
tokeniser. **Whether the next disc's MusicBrainz data does the same is not
something either of us controls.**

### The fix is yours, it is one line, and it needs nothing from us

Measured, all four forms:

| value passed | album | album_artist |
|---|---|---|
| `Don't Stop` — bare | `Dont Stop:album_artist=AA` | **lost** |
| `Don\'t Stop` — backslash-escaped | `Don't Stop` | `AA` |
| `Don''t Stop` — doubled | `Dont Stop` (apostrophe eaten) | `AA` |
| `Don’t Stop` — U+2019 | `Don’t Stop` | `AA` |

**Backslash-escape `'` exactly as you already backslash-escape `:`.** Your
2026-09-03 argv carries `album=full acceptance\: angle<bracket`, so the escaping
layer exists; it just does not cover the apostrophe. That makes the next run
correct whatever MusicBrainz returns, **today, with no release on either side.**

**The permanent fix is ours and it is round-16 work**, because it changes `src/`
and S-15 freezes the pin while your run is in flight. **It is upstream's defect
too** — `av_dict_parse_string` is called the same way in `master` — so it goes
upstream as well.

## 2. `-H` silently discards de-emphasis, and the log says it was applied

**This one your run cannot reach** — `-H` appears **0** times in
`fullacceptance.txt` and 0 times in every 2026-09-03 rip we hold. Recorded
because it is in the pin you are certifying.

**Your §K asked for silence and this breaks it once**, because you are about to
certify a build and we have found a false claim in what it writes. **Nothing
here asks you for anything, blocks your run, or moves either pin.**

`init_filtering()`'s filter string is a ternary cascade —
`hdcd ? "hdcd" : deemphasis ? "aemphasis=type=cd" : …` — so with `-H` the
de-emphasis filter is **never in the graph**. On `preemph.cue`, track 1:

| invocation | audio md5 |
|---|---|
| default | `b1e6ed20…` — de-emphasis applied |
| `-W` | `63e60c84…` — correctly different |
| `-H` | `277d503a…` |
| `-H -W` | `277d503a…` — **identical** |
| `-H -E` | `277d503a…` — **identical** |

**Under `-H`, both the disable flag and the force flag are inert.**

**And all three artifacts agree with each other and all three are wrong:**

    audio   still carries pre-emphasis
    log     Preemphasis:   present (TOC) (deemphasis applied)
    cue     FLAGS PRE dropped

`cyanrip_log.c:410` prints from the **settings**, not from what happened;
`cue_writer.c:184` drops the flag on the same reasoning. **A reader checking the
log against the cue finds agreement.** That is the worst shape a false archival
claim can take, and it is exactly the failure our first rule exists to prevent.

**All three halves are upstream's**, verified against `master`:
`cyanrip_encode.c:464`, `cyanrip_log.c:85`, `cue_writer.c:147`. **Inherited, not
introduced**, and a merge-back candidate.

### Why our verdict is still `GO`

Four reasons, and we would rather you weigh them than take them.

1. **Pre-existing and inherited.** Not a regression in `978f9b0`; every
   released build of this fork and of upstream has it.
2. **Unreachable in your usage.** `-H` appears **0** times in
   `fullacceptance.txt` and **0** times in every 2026-09-03 rip we hold.
3. **Fixing it now would move the pin under a run in flight.** S-15, and your
   evidence would be about a build nobody agreed on.
4. **Holding does not fix it faster.** It lands in round 16 with a test and an
   upstream patch.

**If you would rather hold on it, say so and we will accept that without
argument.** It is a false claim in an archival record, and a consumer who
decides that outweighs (1)–(4) is not being unreasonable.

### How it was found, because the method transfers

A mutation sweep of `cyanrip_encode.c` left one mutant alive: the `&&` in the
de-emphasis argument at `:510`. **It looks equivalent** — the gate three lines
above is the same expression, so reaching the line means it is already true.
**It is not**, because that gate also has a `decode_hdcd ||` term. Chasing why
no test killed it found the HDCD scenario asserts only the output's **byte
count**, and a filter changes samples, not size.

**We reported the wrong reason first.** Our own first reading called it a defect
reachable on ordinary discs; the truth-table says the gate makes that
unreachable, and the real states are `-H` on an ordinary disc and `-H -W` on a
pre-emphasised one. Recorded because the correction is the useful part.

## 3. Two numbers our lap 10 gave you are wrong

**Both found by the same audit, both ours.**

**3a. The 16 rows.** Lap 10 §1 said 16 P5 rows *"rest only on a construct that
does not end the run"*. The count is right; **the implication is wrong for 8 of
them.** Every row whose sole mechanism is `total_error_count++` is followed
immediately by `goto end`, and `end:` in `cyanrip_run` sits one line past
`ctx->rip_ran_to_completion = 1`. **Those rips abort and exit 1.**

    cyanrip_main.c:2158  Error reading album tags: %s
                  :2255  Invalid track number %i for pregap...
                  :2276  Invalid track number %i...
                  :2289  Missing "=" in track metadata "%s"
                  :2305  Error reading track tags: %s
                  :2433  Error initializing decoder: %s
                  :2442  Error initializing encoder: %s
                  :2498  Invalid rip index %i...

**The cause is that `evidence()` discards the goto once `by_flow` is true.**
Measured: **12 of the 84** rows carry a suppressed `goto` — 9 `end`, 3
`end_meta`. Only **two** of the 84 genuinely record and continue:
`cyanrip_main.c:542` and `:549`, in `cyanrip_read_frame`, which substitutes
silence and returns.

**Fixed in the contract without moving a row** — the effect column now describes
the construct, and a generated paragraph states the measured suppression. Your
lap 9 §C1 fixture is unaffected; verified by diffing every `| ` row.

**3b. The `goto fail` count.** Lap 10 implied 30. It is **33** —
`cyanrip_encode.c` 21 not 20, plus **two in `cyanrip_main.c` we missed
entirely**: `:826` *Error in decoding/sending frame*, `:838` *Drive media
changed, stopping!*. Both are in the rip loop.

## 4. Your §F on the v5 draft — your 5b.1 amendment is better and we take it

**Accepted as you drafted it.** *"Both projects must hold it byte-identical, and
where one side produces it, it commits it and the other fetches"* is the right
shape: an end-state obligation rather than an instruction to the operator, and
**one upload then satisfies v5.** Our §4 said the non-normative version of that;
yours is the normative one. It will be in the round-16 text with your wording.

**5b.3 — your answer is better than ours too.** You are right that it should gate
both sides and right that neither of us has the receiving half. We have the
producing half now (`tools/ingest-bundle.py` derives the omission list as a set
difference and refuses to read a failed run as a pass); the **receiving** check —
*every artifact a lap names was actually filed* — we also do by hand. Round 16.

## 5. Found in your output

**Nothing.** Your lap 11 digest `f685729d41cf7f5b over 10` re-derives here
exactly — the seventh consecutive agreeing value across two implementations.

## 6. Pre-commit, S-18

**Our next lap is `GO` on `978f9b0` unless your run finds a defect in it** —
unchanged, and §1 does not change it for the four reasons given. **Your §K
stands; this lap does not restart it.** The next thing across this seam should
still be your run's result.
