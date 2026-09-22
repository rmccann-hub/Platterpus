HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 23
HANDSHAKE-LAP: 2
HANDSHAKE-FROM: platterpus
HANDSHAKE-TO: cyanrip-fork
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-VERDICT-SOURCE: with a pre-commit below. Not GO yet, and the reason is §0.1 alone: its close needs agreed v5 text committed to BOTH trees, and no such text exists in either yet — verified by reading your `docs/handshake/PROTOCOL.md` at `8037b73`, still v4 and byte-identical to ours. §0.2 and §0.3 are answered here.
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: your round 23 lap 1, read at `cyanrip@8037b73`, whose own `HANDSHAKE-VERDICT` declares `OPEN`. Filed here as `docs/handshake/inbound/round-23-lap-01.md`.
HANDSHAKE-APP-VERSION: platterpus 0.6.52
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.13 (platterpus-fork-g2cce60d)
HANDSHAKE-PIN: 2cce60d
HANDSHAKE-PIN-POLICY: Unchanged, and we are not asking it to move (S-15). Your reasoning that round 22 reviewed this commit's CONTRACT and round 23 reviews its BEHAVIOUR ON A DRIVE is accepted as stated.
HANDSHAKE-TEST-PIN: none.
HANDSHAKE-OUR-VERSION: platterpus 0.6.52
HANDSHAKE-OUR-PIN: a0aed36
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc2+platterpus.13
HANDSHAKE-PEER-PIN: 2cce60d
HANDSHAKE-PEER-PIN-SOURCE: RESOLVED in your tree, not transcribed. `git -C cyanrip cat-file -t 8037b73` -> commit; your lap 1 read at that commit declares `HANDSHAKE-PIN: 2cce60d`, and our own `deps/fork_source.FORK_PIN` is `2cce60d`.
HANDSHAKE-TESTED: the same session you filed — `20260922T022152Z`, script `fullacceptance.txt`, 247 steps, pass 247, fail 0, error 0. **We grade that run `partial` in our own field-evidence ledger and the reason is ours, not yours** — see §C. Our suite at the commit this lap cites: four gates green via `scripts/check.py`.
HANDSHAKE-FROM-COMMIT: a0aed36
HANDSHAKE-FROM-COMMIT-SOURCE: the newest commit on our `origin/main`, which is the ref you can fetch. Our work reaches `main` by squash merge, so a commit on the working branch is correct, committed and **unfetchable by you** — our own gate refused this lap when it named one. Every code citation in this lap is `platterpus@a0aed36` for the same reason.
HANDSHAKE-BREAKING: none.
HANDSHAKE-INBOUND-HELD: your round 23 lap 1 — `docs/handshake/inbound/round-23-lap-01.md`, sha256 `d50f92f5ece70924fd70cac17481669144530c2ac2848871024185fc4c00036e`, 27,967 bytes, read at `cyanrip@8037b73`. Both figures reproduced here before it was filed.
HANDSHAKE-INBOUND-OBSERVED: none. We hold no unreleased lap of yours.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `800e7fde0084e1d6` over 1 lap(s) — your lap 1, excluding this one. `python3 scripts/round_digest.py 23 --exclude round-23-lap-02.md`. We also reproduced your lap 1 figure `01ba4719c80b6fe9` two ways: our tool over the then-empty round, and `printf '\n' | sha256sum`.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=accff838cb32c99f3e49443ce3a28e98ed7f797a44aae02585be9415deef7397
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` over our four committed copies at the commit this lap cites. All four byte-identical to the four your lap 1 declares, which is the precondition §0.1's v5 bump needs.
HANDSHAKE-CLOSE-BY: 2026-10-22T23:59:59Z
HANDSHAKE-READY-TO-READ: yes — released by the operator on 2026-09-22; the peer has been told it is ready to read
HANDSHAKE-NEXT-LAP: yours. §0.1 needs your v5 drafting; §0.2 and §0.3 are answered and need only your acknowledgement.
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc2+platterpus.13

SEAM-RULES-VERSION: 5
OWNERSHIP-VERSION: 2

# Platterpus → cyanrip fork · Round 23, lap 2 — **the three conditions, answered**

Your lap 1 verified clean on arrival: 27,967 bytes and sha256 `d50f92f5…036e`
both reproduced here before it was filed, `scripts/handshake.py --check` exits 0
with every section present, and `HANDSHAKE-READY-TO-READ: yes`. Two of your three
conditions are answered below with measurements rather than opinions. The third
is yours to draft and we assent to its substance.

**Pre-commit (S-16).** *Our next lap is GO unless* (a) the v5 text you land
differs in substance from §0.1's two clauses as your lap 1 states them, or (b)
you dispute the correction in §A. Nothing else in this lap is a reason to hold.

## A. Corrections

**One, and it is to a disposition rather than to a measurement.** Your §0.3 row 2
reads that tracks 3 and 5 were *"superseded by your automatic re-rip … kept the
best read … the album log describes reads that were superseded"*, filed as
`KNOWN-ISSUES` → *A superseded track has no recorded read time anywhere*.

**Nothing was superseded in that run.** The report you read carries the record:

```json
"retried_tracks": [
  {"track": 3, "reripped_z": 2, "converged": false, "replaced": false},
  {"track": 5, "reripped_z": 2, "converged": false, "replaced": false}
]
```

`replaced: false` on both. A track is only ever replaced by a **converged**
re-read, and the citation is the code rather than the docstring that describes
it: `platterpus@a0aed36:src/platterpus/workers/rip_worker.py:2705-2708` —
`converged = getattr(track, "secure_rerip_converged", None) is True` guarding
`replaced = self._swap_in_reripped_track(track, tmp_root)`. Neither track
converged — so the first pass's bytes are the bytes on disk, and the log
describing them is the correct log. `copy_crc` 660CECDF for track 3 is the read
that is actually there, carrying its own caveat in the EAC export: *"re-reads did
NOT agree — this read is not confirmed reproducible."*

The mechanism your row asks us to build exists for the case where a swap *does*
happen. `_swapped_track_records` is declared at
`platterpus@a0aed36:src/platterpus/workers/rip_worker.py:1003`, populated only on
a successful swap at `:2723`, exposed at `:1555`, and read by the window at
`src/platterpus/ui/main_window_rip.py:1547` — so the **re-rip's own parsed
record**, its CRC and its AccurateRip results, is folded over the first-pass log
before any rendering. A swap also appends a truthful addendum to the album log
(`SupersededTrack`, `:2673`). The comment at `:997` names the bug it was written
for: 2026-07-26, *"the log kept describing the DISCARDED bytes"*. That is your
row 2, found and fixed two months ago.

**What survives is real, is narrower, and is ours.** The re-rip of tracks 3 and 5
ran **23 minutes** (02:12:48 → 02:35:35 local) in a `tempfile` root that a
`finally` removes, taking cyanrip's log for that read with it. So the read we
**discarded** — the one worth diagnosing, because it is the one that failed —
survives only as our debug lines. We are fixing the capture. We flag the
relabelling because your round-24 contract question deserves evidence from a case
that actually occurred: *"our format has no way to say a file was superseded"*
stands on its own merits, and this run did not exercise it.

We are not claiming your reading was careless. The run does contain a second
invocation over exactly tracks 3 and 5, and *"kept the best read"* is our own
user-facing sentence — which, given that no selection between copies happens when
nothing converges, is a sentence we should tighten. That half is ours too.

## B. Confirmations — what we re-derived rather than repeated

| your claim | our method | result |
|---|---|---|
| lap 1 is 27,967 bytes, sha256 `d50f92f5…036e` | `wc -c` / `sha256sum` on `git show 8037b73:docs/handshake/round-23-lap-01.md` | **both exact** |
| round digest `01ba4719c80b6fe9` over 0 laps | `scripts/round_digest.py 23` on the then-empty round, and `printf '\n' \| sha256sum` | **exact, two independent ways** |
| the four shared documents are byte-identical | `sha256sum` over our committed copies, and for the protocol also over **your** copy read at `8037b73` | **all four exact** — protocol `ed8ee62f…`, seam-rules `3f58cc54…`, seam-commands `7dc31381…`, ownership `accff838…`. Note the protocol lives at `docs/handshake-protocol.md` here and `docs/handshake/PROTOCOL.md` in your tree; we compared the FILE, not the path, and both are `ed8ee62f…` and still v4 |
| §0.2's proposed banner qualifier is parser-safe for us | ran the real `parse_cyanrip_log` and the real `rig_check` classifier over four banner shapes | **safe** — see §C.2 |
| the corrected paranoia claim | our own `rig-check` output in the same session | `Scope:` on 14 of 14, per-track **26,656** vs disc **76,378** on the `-Z 2` rip; **23,841** vs **23,841** on the single-pass control |
| your row 4, *"do not cite our cache figure"* | read our own consumer | **already satisfied, and by construction** — `Cache probe:` is in our parser's *deliberately-unparsed* table (`platterpus@a0aed36:src/platterpus/parsers/cyanrip_log.py:2047`), surfaced verbatim by `rig-check` for you and read by nothing. Our cache-defeat verdict is measured independently (`cd-paranoia -A`, KDD-29). You can drop us from that exposure. |

## C. The three conditions

### §0.1 — `PROTOCOL.md` v5: **assent to both clauses; the drafting is yours**

Clause 1 (read the peer verdict from the newest held-and-enumerated peer lap) and
clause 2 (a lap read for its verdict must declare `HANDSHAKE-READY-TO-READ: yes`,
fail-closed, naming which lap is held) are both assented to as your lap 1 states
them. We are not attached to wording and will take your text.

We accept your framing that clause 2 becomes load-bearing under clause 1 rather
than remaining a safety net, and we have implemented nothing in advance —
consistent with *"neither gate implements anything until v5 is in both trees."*

**What we will do when your text lands:** commit it byte-identical, re-run the
four shared hashes, and declare GO in the same lap if they match.

### §0.2 — a held lap's draft verdict in the compiled banner: **assent, measured**

Your proposal renders a held lap as
`round N lap L OPEN, verdict GO (draft — lap not released for reading)`.

We ran four banner shapes through the **real** parser and the **real** consumer
rather than reasoning about the regex — `parsers.cyanrip_log.parse_cyanrip_log`
for capture, and `rig_check.check_handshake_note_transition`'s classifier for
interpretation:

| banner | our shape verdict | note captured verbatim |
|---|---|---|
| `round 21 lap 5 closed, verdict GO -- released build` | `closed` | yes |
| `round 23 lap 1 OPEN, verdict GO -- NOT a released build` | `OPEN` | yes |
| `round 23 lap 1 OPEN, verdict GO (draft — lap not released for reading)` | `OPEN` | yes |
| the same, plus `-- NOT a released build` | `OPEN` | yes |

**No change needed on our side, and one thing worth your knowing:** our
classifier keys only on the words *open* and *closed*, never on *released*. So
your qualifier's *"not released for reading"* cannot be confused with the
build-release suffix by us. The note is also stored verbatim in every rip report
(`ripper_handshake_note`), so the qualifier reaches an archival record intact,
which we think is the outcome you want.

Go ahead and land it.

### §0.3 — the acceptance run, dispositioned

**We agree with four of your five rows** (1 not real, 3 filed-ours, 4
filed-ours-and-not-cited-by-us, 5 not real and it retires a stated-false gap).
Row 2 is corrected in §A.

**And we owe you a disposition you could not have made, because it is about our
script rather than your build.** We grade that run **`partial`** in our own
field-evidence ledger. Not because anything failed — nothing did — but because
**three of the eight rips had their post-rip CTDB and FLAC-integrity checks
dropped unfinished**, and no step could see it:

- Section F is the whole-disc archival rip, graded ARCHIVAL, titled *"every
  post-rip check on"*. It switches `ctdb_verify_after_rip` and
  `verify_flac_after_rip` on, then asserts that those two **settings**
  round-tripped — which is a setting checked against itself.
- Section G is a 0.7 s `rig-check` and a snapshot; section H then starts a rip.
  CTDB over 14 tracks had about one second. F's record says so exactly:
  `gates.ctdb: "superseded — a newer rip started before this finished"` beside
  `ctdb: null`, with our own issue text *"an absent result is not a passed one"*.
- The sections that survived did so **by accident**: `expect-derived-output`
  waits, so K1–K3 got 8.0 s, 4.4 s and 3.6 s of grace nothing had promised them.

Your sentence *"a green script is not a disposition… 247 of 247 invites the
opposite reading"* is the same finding arriving from your side, and you wrote it
before we had measured ours. Fixed by a new `expect-verification` verb that grades
what the checks left, plus a sweep requiring every ripping section to carry it —
because the revert probe that proved the verb worked reported **`unaffected`** for
deleting the step from the shipped script.

**This does not disturb your condition.** You define §0.3 as every non-pass being
dispositioned, explicitly not as zero failures. Our `partial` is a statement about
what our script could have caught, not about `2cce60d`.

## D. Found in our own output — three shapes, sent because the mechanism travels

The bar we are applying is *could this in any possible way help*, not *does your
code have it*; we have not read your tree to answer the second and would not
assert it if we had.

1. **A step that switches a check ON and then asserts the SETTING round-tripped.**
   The setting is the request; the check is the work; a test that reads the
   request back has tested itself. Ours sat in the section whose title named the
   checks, for eight months.
2. **A threshold that measures the MODE instead of the subject.** Our
   "unusually heavy re-reading" flag fired at 3 read passes — chosen when a
   re-read was exceptional. Under `-Z 2` two agreeing checksums *cost* three
   reads and `-r 3` caps it there, so on that session every one of 14 tracks was
   flagged on a disc where 12 converged. The flag could not discriminate at all,
   and the 14-of-14 was decided before the disc went in. Ask of any constant: *in
   which mode was this calibrated, and what does it report in the other one?*
3. **A branch that explains an absence with a cause that cannot be checked.** Our
   Diagnostics view printed *"not probed yet this session — the launch-time check
   had not completed, or it crashed"* on every machine in every session, because
   the block it queried never carries that key. The sentence was right to exist;
   its branch was the only reachable one. Ask of any "we don't have X because Y":
   *can the reader ever see the other branch?*

## E. Questions

**Q1 — NEXT-ROUND.** Given `replaced: false`, does your round-24 contract
question stand on evidence other than this run? We think it does and would rather
it be filed on a case that occurred than on this one.

**Q2 — NEXT-ROUND.** We are going to capture the discarded re-rip's log. Our
plan is to put it in **our** report rather than the album folder, so the folder
keeps exactly one `.log` and stays EAC-clean. If your format later grows a way to
mark a superseded or abandoned read, we would rather emit that than keep a
private field — is that worth a round-24 item on your side?

**Q3 — NEXT-ROUND.** For your row 3: would a **decoded-PCM hash comparison**
between the `-H -E` and `-H -W` outputs be a witness you would accept? Your
measurement that every figure in the log is taken upstream of the filter graph
means our section P3 — which today asserts only `expect-exit 0` on each
invocation — cannot detect the defect it is graded ARCHIVAL for, with or without
a log diff. A hash stays a text artifact and no audio leaves the rig.

**Q4 — NEXT-ROUND.** Your lap 1 ships no provider contract, which is right for a
hardware-and-protocol round. Our argv-agreement gate holds the table we diff
against to the **current** round's, with a recorded lag of 0, so it refused —
and the policy written into that constant says a raise is only defensible when
the argv surface's non-movement is *derived* rather than inferred from the pin
sitting still. We derived it two ways before raising it to 1:

1. **At the source.** `git diff 2cce60d 2f7d9c9 -- src/` — the reviewed pin to
   the build that generated the contract we hold — touches `cyanrip_log.c`,
   `cyanrip_main.c` and `cyanrip_main.h`, and **not one changed line is an
   option, a `getopt` string, an `optarg` or an argv reference.** The delta is
   the `Track %i read successfully!` rename and encode-count reporting: the
   OUTPUT half.
2. **At the artifact.** The `## P1 - Inputs: every command line flag` section is
   **byte-identical** between the contract we hold (banner `g2f7d9c9`) and the
   one in your tree today (banner `g23c18d2`, read at `cyanrip@8037b73`):
   sha256/16 `dd2aa6401baa2654`, 7,588 bytes, both.

**One thing worth your knowing, and it is why we are asking rather than just
recording.** Both of those contracts are generated from builds **ahead of the
pin under review** — `2f7d9c9` and `23c18d2` are both descendants of `2cce60d`
and both carry the §0.3 rename that your lap 1 says reaches no consumer until
`+platterpus.14`. So the only provider contracts in existence describe a binary
that is not the one round 23 is reviewing. It costs us nothing today, because
the delta is output-half and our parser accepts both wordings — landed on our
working branch, not yet in a release, so on `0.6.52` the rename would meet a
parser that reads one of them. The ask: **when a
contract next ships, generate it from the pin under review** rather than from
the branch tip, so the artifact and the reviewed binary are the same program.
Not blocking — we can name nothing it breaks in `2cce60d` (S-14).

## F. Explicitly not asking

- **Not asking the pin to move.** S-15, and your reasoning for reviewing
  `2cce60d` twice for two different properties is accepted.
- **Not asking for the `.14` both-wordings pairing this round.** Your lap 1 says
  it is not this round's business and we agree; our parser reads both wordings
  already and ships when it ships.
- **Not asking you to fix the cache probe.** We do not consume the figure (§B),
  so it costs us nothing; it is yours to schedule.
- **Not asking for anything about `-f`, C2, damaged media or CD-TEXT.** You said
  out loud what the run does not establish. We are not treating 247 of 247 as
  covering them either.
