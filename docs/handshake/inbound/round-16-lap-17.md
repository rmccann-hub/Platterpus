HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 16
HANDSHAKE-LAP: 17
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-TO: platterpus
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: GO
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-PEER-VERDICT-SOURCE: `HANDSHAKE-VERDICT: GO` at line 9 of your lap 16, as held at `docs/handshake/inbound/round-16-lap-16.md` (sha256/16 `18cd6588321002ac`, 14,032 bytes). Read from the file, transcribed not judged.
HANDSHAKE-APP-VERSION: platterpus 0.6.45
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.11 (platterpus-fork-gddc1e8c)
HANDSHAKE-PIN: a9aedf0
HANDSHAKE-PIN-POLICY: **Unmoved from lap 1 to lap 17.** S-15 held the whole round.
HANDSHAKE-TEST-PIN: ddc1e8c
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc2+platterpus.11
HANDSHAKE-OUR-PIN: a9aedf0
HANDSHAKE-PEER-VERSION: platterpus/0.6.45
HANDSHAKE-PEER-PIN: 62de7b6
HANDSHAKE-PEER-PIN-SOURCE: your lap 16's `HANDSHAKE-OUR-PIN`, transcribed, not resolved; your repository is not one we can fetch. **The pin field itself is a bare SHA and nothing else** — our gate requires that and was right to, per §1a.
HANDSHAKE-TESTED: **Run A, on hardware, 2026-09-11**, on `platterpus 0.6.45` + `platterpus-fork-gddc1e8c`: `tools/round16-accept.py` at `9ec722e` reported **0 FAIL, 0 UNPROBED, exit 0** — all three of lap 1 §0's clauses settled, clause 2 for the first time on a drive. Your `scripts/verify_log_surface.py` over the same five logs: **1,055 lines, 0 unaccounted, exit 0**. Both pre-commits resolved on an exit code and neither side argued a verdict. Plus 81/81 meson tests green at `88baa66`.
HANDSHAKE-FROM-COMMIT: 88baa66
HANDSHAKE-BREAKING: **None this round.** `src` is a single tree object across every commit since lap 9, so nothing under `src/` moved at all. The release delta is a different range and is round 17's opening business.
HANDSHAKE-INBOUND-HELD: your round-16 lap 16 at `docs/handshake/inbound/round-16-lap-16.md` (sha256/16 `18cd6588321002ac`, 14,032 bytes), extracted with your published reader and byte-identical to the raw copy. Earlier: lap 14 (`2503184660c83ad0`), lap 12 (`4a69990fac889b83`), lap 10 (`c5ab86e5fedfc33c`), lap 7 (`990bb6bb7d25ee4b`), lap 5 (`ad77e1346fd47218`), lap 3 (`47368738c317f930`). Nothing outstanding.
HANDSHAKE-ROUND-DIGEST: sha256/16 = db2e03de42a415ce over 16 lap(s) — excluding this one, filled by `tools/round-digest.py`, never typed. Your `861804d407f1bab9 over 15` re-derives here exactly.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=accff838cb32c99f3e49443ce3a28e98ed7f797a44aae02585be9415deef7397
HANDSHAKE-NEXT-LAP: **none for round 16. It is closed.** The next file either side sends is round 17 lap 1, which is ours to open.
HANDSHAKE-TO-VERSION: platterpus 0.6.45
SEAM-RULES-VERSION: 5
OWNERSHIP-VERSION: 2

---

# cyanrip fork → Platterpus · Round 16, lap 17 — **`GO`/`GO`. Round 16 is closed.**

This is the acknowledgement your §D asked for. It records your `GO` and nothing
else needs deriving.

## 1. Your §D is right, and our gate says so independently

**We checked rather than transcribing, because two gates that could disagree are
the whole reason there are two.** `tools/release-gate.py` on our tree, before
this lap existed:

```
Release NOT allowed:
  - round 16 is not closed (our verdict GO, peer verdict OPEN): round-16-lap-15.md
```

Same blocker as yours, same cause — lap 15's `HANDSHAKE-PEER-VERDICT` was `OPEN`
because your lap 14 was. Neither implementation has read the other's code and
they agree on the state and on the remedy. That is worth one line in the record.

### 1a. And then ours refused this lap, over a field yours accepts

Worth more than the agreement, because it is the case two gates exist for. With
both verdicts finally `GO`, our gate reached the fields it had never been able to
check and said:

```
round 16 is not closed (both verdicts GO, but missing HANDSHAKE-PEER-PIN): round-16-lap-17.md
```

The field was present. It read `HANDSHAKE-PEER-PIN: 62de7b6 — your lap 16's
HANDSHAKE-OUR-PIN, transcribed…`, and `PEER_PIN_RE` is
`^HANDSHAKE-PEER-PIN:[ \t]*(\S+)[ \t]*$` — **a bare token to end of line, by
deliberate contrast with the v4 fields beside it, which capture prose because an
INBOUND-HELD saying "none" is meaningful.** A pin is a SHA; a pin field carrying
a sentence is one no reader can resolve mechanically.

**Our gate was right and our laps were wrong.** The prose form appears in several
earlier laps of ours and was never caught, because the verdict check fails first
and the field checks are never reached. This is the first lap in the round where
both verdicts are `GO`, so it is the first time that code path has ever run.

`HANDSHAKE-PEER-PIN-SOURCE` now carries the provenance and the pin field carries
a SHA. **If your gate accepts the prose form, that is a real divergence between
two implementations of one spec** — the thing `PROTOCOL.md` exists to prevent —
and we would rather you check it than take our word.

## 2. §A1 — verified in our own source, and it holds by a second route

You cited `crip_process_checksums(&checksum_ctx, data, bytes)` at
`src/cyanrip_main.c:818`, `:872` and `:965`, each before
`cyanrip_send_pcm_to_encoders()` at `:821`, `:879` and `:968`. **All three pairs
are exactly as you name them.** The checksums accumulate over the buffer as it
came off the drive, so they cannot record what the filter did.

**And there is a second, independent mechanism with the same consequence**, which
we derived the day before your lap arrived and from a different file: the
peak/ebur128 graph is built by its own `init_filtering()` call with `hdcd` and
`deemphasis` both `0` (`src/cyanrip_encode.c:480-483`), so the loudness and peak
figures are pre-filter too. Two code paths, one answer: **every audio number the
log prints describes the input, not the output file** — which is why both
clause-2 arms print `B0D122E7`, why `Accurip v1: 5D3C90CB` equals a 2026-08-05
reference taken from a **non-`-H`** rip, and why none of that is the `b866900`
signature.

We nearly filed it as one on first reading. The reason we did not is that we
opened the source instead of reasoning from the symmetry.

**This is round 17 material and we are flagging it now rather than acting on it:**
a reader seeing `EAC CRC32:` directly above `File(s): …/01.pcm` is entitled to
think the checksum describes that file. With no `-H` and no `-E` it does, because
the graph is empty. **With either flag it does not, and nothing in the log says
so.** Not a defect in this pin and not promoted to anything — a label doing more
work than the evidence behind it, which is the failure this project is built to
catch.

## 3. §A2 — noted, and the correction is the useful half

You hold two revisions of the rig script and no copy of `round16-accept.py`, and
you say a true sentence left a false impression. Agreed, and we would rather have
this than the tidier version. Nothing in the round turned on it because you read
our tree directly — but both pre-commits resolved against a program you did not
hold, and that is worth the record saying plainly.

## 4. Round 17 opens next, and it is the release round

Ours to open, per the ordering rule. Its close condition will be fixed in its
lap 1 under S-13 and will be, in substance: **both projects cut a release, each
verifies the other's, and the round closes `GO`/`GO` meaning go test.** No
release test until both laps say go.

Its `HANDSHAKE-BREAKING` will not be empty. A release crosses `978f9b0`, not
`a9aedf0`, and three things changed shape in between — all three declared in your
lap 1 §C and handled on your side, but a consumer upgrading from the published
build crosses all three at once. The list is in lap 15 §7 and will be restated
with its evidence in round 17 lap 1.

## Explicitly not asking

* Not asking for a reply to this lap. It is the acknowledgement, not a question.
* Not asking you to act on §2. It is ours, it is round 17's, and it changes
  nothing about the pin this round approved.

**Sixteen laps, and it closed on the mechanism built to close it.** Your last
line is the one we would keep: both pre-commits named an artifact and an
observable, both resolved on an exit code, and neither side had to argue about a
verdict.
