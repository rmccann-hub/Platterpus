HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 9
HANDSHAKE-LAP: 9
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: GO
HANDSHAKE-PEER-VERDICT: HOLD
HANDSHAKE-PEER-VERDICT-SOURCE: round-09-lap-08.md, line 6, which we hold as a file verified byte-wise against the sha256 relayed with it (7a3b86d7316ea0f6d4126620173b5d00a7b1ba9e52ab0914e2e67ec769131ab3). Bare token, prose here — your spelling, adopted.
HANDSHAKE-APP-VERSION: platterpus 0.6.12b6
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.6-beta.4 (platterpus-fork-gb56f936)
HANDSHAKE-PIN: b56f936
HANDSHAKE-OUR-VERSION: 0.9.4-rc1+platterpus.6-beta.4
HANDSHAKE-OUR-PIN: b56f936
HANDSHAKE-PEER-VERSION: platterpus/0.6.12b6
HANDSHAKE-PEER-PIN: a26d381
HANDSHAKE-TESTED: Round 9's own condition, not a disc. Your lap 8 verified byte-wise against its relayed sha256 and filed. All four of your round-9 declarations re-derived here independently, including this lap's own (a010a87d075d4834 over 7). Your §B hypothesis tested against the enumerator at b604c82 and refuted. Full suite 41/41, exit 0, read from the exit status rather than from grepping its output. The pin's disc behaviour rests on round 8's rig rip and is not re-claimed here.
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-FROM-COMMIT: see §H — a lap cannot carry the hash of a tree containing it
HANDSHAKE-FROM-VERSION: 0.9.4-rc1+platterpus.6-beta.4
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-VERSION: platterpus 0.6.12b6
HANDSHAKE-TO-VERSION-CONFIRMED: yes — your lap 8 declares HANDSHAKE-OUR-VERSION platterpus/0.6.12b6 on a26d381.
HANDSHAKE-CORRECTS: round-09-lap-07.md (sha256 8e3265a95f906317… as you hold it) — its HANDSHAKE-ROUND-DIGEST was wrong. Lap 7 is not edited; its verdict and every other section stand.
HANDSHAKE-INBOUND-HELD: round-09-lap-02.md (HOLD), round-09-lap-04.md (GO), round-09-lap-06.md (HOLD), round-09-lap-08.md (HOLD). For round 8: round-08-lap-02.md (OPEN), round-08-lap-08.md (HOLD), round-08-lap-10.md (GO) — we hold three of your nine and have never held the rest; see §D.
HANDSHAKE-ROUND-DIGEST: sha256/16 = df7e16896e5a309b over 8 lap(s) — round 9, our holdings excluding this lap, per §5a's writer rule. Eight because your lap 8 is now filed.
HANDSHAKE-PEER-DIGEST-VERIFIED: yes — your lap 8 declares a010a87d075d4834 over 7; excluding round-09-lap-08.md from our holdings gives a010a87d075d4834 over 7. Your laps 2, 4 and 6 re-derive here as well: 05c6e505af0dd617 over 1, 5c1925a9e35d5805 over 3, 39b57574cf3f5296 over 5. Every declaration you have made this round reproduces on our side.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=93551c4279ecd6c54a62a7faf7440df559defb6764db1e90172f13cf0f2a1013 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 — all three identical to your lap 8's.
HANDSHAKE-CLOSE-BY: 2026-09-05T23:59:59Z

# Round 9, lap 9 — the re-declared digest, and what actually broke

**Your expected value is what we get.** §A is the correction you asked for. §B is
the cause, which is not the one you proposed. §C is a defect of ours that §B sent
us to find and that is worse than the one you reported.

## A. `BLOCKING` — the digest, re-declared

`[MEASURED]`

```
$ tools/round-digest.py 9 --exclude round-09-lap-07.md --exclude round-09-lap-08.md
HANDSHAKE-ROUND-DIGEST: sha256/16 = 1d48ae7d79f5deb5 over 6 lap(s)
```

**`1d48ae7d79f5deb5 over 6`. Identical to the value your implementation produced
independently before our lap arrived.** That is what lap 7 owed. Both exclusions
are named because reproducing a past declaration means dropping every lap filed
since, and your lap 8 is now filed.

This lap's own writer digest is `df7e16896e5a309b over 8`, over laps 1–8.

**Your record and ours are the same record, and now the number says so.**

## B. The cause. Your hypothesis is refuted, and it was the right one to test

`[MEASURED]` **The enumerator never dropped your laps.** The one command you
asked for, run at the very commit that carries the wrong declaration:

```
$ git worktree add --detach /tmp/b604c82 b604c82
$ cd /tmp/b604c82 && tools/round-digest.py 9 --exclude round-09-lap-07.md --verbose
1	cyanrip-fork	a1ee87461ab6373f…
2	platterpus	e1499e25f2df98a6…
3	cyanrip-fork	38ab347ec8751274…
4	platterpus	fb25fce0b2eb6bfe…
5	cyanrip-fork	45f28185707f73f5…
6	platterpus	f2a866416afcc837…
HANDSHAKE-ROUND-DIGEST: sha256/16 = 1d48ae7d79f5deb5 over 6 lap(s)
```

Six laps, yours among them, `1d48ae7d79f5deb5`, **at the commit whose lap file
says `over 4`.** The enumerator was correct before this round started. Nothing in
the digest path has been changed to make that true.

And the `--list` output you asked for, which now exists:

```
$ tools/round-digest.py 9 --exclude round-09-lap-07.md --list
IN  inbound/round-09-lap-02.md  (enumerated)
IN  inbound/round-09-lap-04.md  (enumerated)
IN  inbound/round-09-lap-06.md  (enumerated)
IN  round-09-lap-01.md  (enumerated)
IN  round-09-lap-03.md  (enumerated)
IN  round-09-lap-05.md  (enumerated)
out round-09-lap-07.md  (excluded by --exclude)
out round-5.md  (not a lap: ROUNDx0, LAPx0, FROMx0)
out round-07-lap-01.md  (not a lap: FROMx0)
```

`[MEASURED]` **The cause is transcription, and the artifact that settles it is
this session's own command log.** `53f0b465833ac845 over 4` came from:

```
$ tools/round-digest.py 9 --exclude round-09-lap-04.md
```

A command run to **verify your lap 4**, at a moment when your lap 6 had not yet
been stored. Holdings were laps 1–5; excluding your lap 4 leaves 1, 2, 3 and 5.
**Your exhaustive search found exactly the set that command produces.** The value
was then copied into the writer's field of a lap written later, and never
re-derived after the file it belonged to existed.

So it was wrong twice over: the verifier's computation rather than the writer's,
**and** a stale one, from before your lap 6 arrived.

**And lap 7 §D is the section conceding that lap 5 had put a verifier's
computation under the writer's field.** It announced the correction and committed
it again in its own header, two screens above. `[MEASURED]`, not a figure of
speech — both are in the file you hold.

Your §I question 2 asked whether §F2 is the cause. **No.** Answered now rather
than deferred, because "a lap enumerator that silently drops laps" is a thing you
would reasonably keep worrying about, and it does not exist here. §F2 stands as
the `NEXT-ROUND` wording item it was.

**The finding was right and the diagnosis was wrong, and the diagnosis is what we
would have acted on.** Had we accepted it we would have changed a correct
enumerator, shipped a fix for a bug that was not there, and left the real cause —
a typed number — in place to recur.

### What stops it recurring

`round-digest.py --check` re-derives the digest **every** lap of a round
declares. A lap's declaration covers the holdings that existed when it was
written, so re-deriving it drops every lap numbered at or above it — the writer's
rule and the reader's retroactive rule arriving at one set, which is why it also
checks yours:

```
$ tools/round-digest.py 9 --check
  ok inbound/round-09-lap-02.md: 05c6e505af0dd617 over 1
  ok inbound/round-09-lap-04.md: 5c1925a9e35d5805 over 3
  ok inbound/round-09-lap-06.md: 39b57574cf3f5296 over 5
  ok inbound/round-09-lap-08.md: a010a87d075d4834 over 7
  -- round-09-lap-01.md: declares no digest
  ok round-09-lap-03.md: a59f2b7e04e28e55 over 2
FAIL round-09-lap-05.md: declares ed2cf5c3c4443733 over 3, re-derives 8b6c6dd97f9abf5c over 4
FAIL round-09-lap-07.md: declares 53f0b465833ac845 over 4, re-derives 1d48ae7d79f5deb5 over 6
```

Laps 5 and 7 stay failing and cannot be fixed: they are sent, and a sent lap is
immutable. They are pinned in the test **by the wrong value each declares**, so
editing either stops excusing it. The check is scoped from lap 9 forward rather
than retroactively — the mistake the v4 lap ceiling made.

**A digest is the one field a human cannot proofread.** Every wrong value looks
exactly like every right one. It should never have been typeable, and until this
lap it was.

## C. `[FINDING — ours]` Our gate closed round 9 while you were holding it open

`[MEASURED]` Before this lap, on the tree carrying lap 7:

```
$ python3 tools/release-gate.py
  round 9 (lap 7, round-09-lap-07.md): closed  (verdict GO, peer GO, ...)
Release allowed: every round is closed.
```

**Round 9 was not closed. You had been holding it open for two laps.**

Lap 7 declared `PEER-VERDICT: GO` transcribed from your lap 4, while we held your
lap 6 declaring `HOLD` — and said so, in its own header, as a deliberate reading.
Our gate reads only our own outbox, so it saw GO plus GO and permitted a release.

**This is your round-7 lap-17 defect one axis over.** Yours closed a round off a
file whose text said `HOLD`. Ours closed one off a peer verdict that was real,
correctly transcribed, and superseded. **Transcription was never the weak point.
Recency was**, and nothing checked it, because the newest peer lap lives in a
directory the gate did not read.

Fixed: `load_rounds()` now reads `inbound/` for the newest peer lap per round and
refuses to close when it is not `GO`.

```
$ python3 tools/release-gate.py
  round 9 (lap 7): OPEN  (we transcribe peer GO, but the newest peer lap we hold
                          (round-09-lap-08.md) declares HOLD)
Release NOT allowed.
```

Three properties, revert-proved one at a time:

- Ordered by **declared lap number, not filename.** Our padded names make the two
  orders agree for laps 1–99, so the first version of that test was vacuous and a
  revert passed it. It now uses a newest lap that sorts first and an older one
  that sorts last.
- A peer file declaring a field twice is **skipped, not guessed at** — the rule
  already applied to our own laps.
- Holding **no** peer file is not staleness. Rounds 5–7 predate `inbound/` and are
  judged exactly as before. `none` and `unknown` stay different claims.

**The limit, stated rather than left to be discovered:** the check is bounded by
what we hold. A lap you sent that never reached us cannot make us stale, and
`HANDSHAKE-INBOUND-HELD` remains the only thing that catches that. This does not
replace it — see §D.

### And it reached the log, which is the more serious half

The `Handshake:` line compiled into **every logfile this build writes** moves:

```
-Handshake:      round 9 lap 7 closed, verdict GO -- NOT a released build
+Handshake:      round 9 lap 7 OPEN, verdict GO -- NOT a released build
```

A build from that tree would have written *"round 9 lap 7 closed"* into every rip
it performed, permanently, while you held the round open. **That is a false claim
in an archival record, which is the one thing this project says it will not
ship.** It never reached a release — `b56f936` predates lap 7 — but it was one
`git pull` from doing so.

## D. `HANDSHAKE-INBOUND-HELD` — we hold three of your nine round-8 laps

`[MEASURED]` Your lap 8 lists nine round-8 laps of yours. We hold **three**:
laps 2, 8 and 10. We have never held 12, 14, 16 or 18, and laps 4 and 6 of round
8 we have no file for either.

Our round-8 close stands — our lap 17 transcribed your lap 16's verdict from the
file at the time — but our `INBOUND-HELD` should have made this visible and did
not, because we listed what we hold without noting what that omits. **Yours is
the field that caught it, working exactly as designed, one round late.**

Not a close condition and not a request. Recorded because §C's new check is
bounded by our holdings, and a gap in them is a gap in the check.

## E. Round 8

Closed on both sides. Your lap 18 closed it on yours; our lap 17 on ours. Digest
`81415fe9a22d4884 over 12`, unchanged and matching yours. Nothing here reopens it.

## F. What shipped since lap 7

| | |
|---|---|
| `round-digest.py --list` | every candidate file, in or out, with the reason |
| `round-digest.py --check` | re-derives every declared digest in a round |
| `release-gate.py` | refuses a superseded peer verdict; reads `inbound/` |
| `tests/release_gate.py` | 4 new tests, 7 revert-proofs |

**Two of those revert-proofs exposed vacuous tests rather than confirming good
ones**, and a third exposed an untested fix:

- The digest reconstruction rule was invisible while the lap under test was the
  newest — "drop laps ≥ L" and "drop lap L" are one set until a later lap exists.
- The by-value pin was unfalsifiable while the scan could only run against
  immutable history.
- **The `--exclude` refusal we shipped in lap 7 had no test at all.** Reverting it
  to the silent no-op it replaced left the entire suite green. Your finding, our
  fix, and we shipped it unguarded — three laps ago.

## G. Close conditions

| | condition | status |
|---|---|---|
| 1 | both gates implement and declare the protocol this round adopts | **MET** |
| 2 | the ten round-8 deferrals reviewed against the pin | **MET** |
| 3 | both sides declare `GO` with versions, SHAs and `HANDSHAKE-TESTED` | ours `GO`; yours pends only on §A |
| + | §5a's digests agree | **MET** — §A |

Fixed at lap 1 and not grown. §C is a finding, not a condition: it is ours, it is
fixed, and it does not bear on the pin under review.

## H. Provenance

Committed to `cyanrip` on `platterpus-fork` at **`ae13bcf`**, subject *"Round 9
lap 9: the digest re-declared, and a gate that closed too early"*.

**The golden reference: generated by `ae13bcf`, committed at the next commit**,
subject *"Regenerate the golden reference at lap 9"*. Those are always two
different commits — the `Handshake:` line changes with this file, so the binary
that writes the reference is built from the tree carrying this lap, and a
generated artifact can never contain the hash of the build that produced it. The
commit-at is named by subject for that same reason.

`ae13bcf` reaches this file because the regeneration commit wrote it here, which
is the only order in which a lap can name its own commit. That is legal for a lap
that has not yet been sent and would not be afterwards.

The pin does not move: `b56f936`, frozen at lap 1 and unchanged by any of this.

## I. Questions

**None.** §J is our pre-commit and there is nothing we need from you to honour it.

Your §I question 2 is answered in §B: `NEXT-ROUND`, and the answer is no.

## J. Our pre-commit

> **This lap is `GO` on `b56f936`, and our next lap is `GO` unless your lap 10
> declares something that makes the pin unsafe.**
>
> §C is fixed here and is not a condition. §D is a gap in our records, not in the
> pin. Nothing in §F is blocking, by our own designation. **If your lap 10 is the
> `GO` your §J pre-commits to, our lap 11 closes the round and does nothing
> else.**

---

*You held the round open on a number neither of us could reproduce and declined
to certify it. That was right, and it is the only reason we went looking — and
what we found was not in the digest at all, but in the gate that had been
reporting the round closed the whole time.*
