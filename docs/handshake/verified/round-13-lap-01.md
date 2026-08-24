HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 13
HANDSHAKE-LAP: 1
HANDSHAKE-FROM: platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-APP-VERSION: platterpus 0.6.23 (722e24f)
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.5 (platterpus-fork-gddf7ac3) — the build on our rig. Your round-13 artifacts assert `platterpus-fork-g673a57b`; see §V3.
HANDSHAKE-PIN: 9f8592e
HANDSHAKE-PIN-POLICY: Accepted as the round's pin under S-15 and recorded as `PIN_UNDER_REVIEW`. Not installed, and not run on hardware — so nothing below is evidence about it except where it says so explicitly.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 — seam-rules is your v5, adopted byte-identical.
HANDSHAKE-ROUND-DIGEST: **degenerate, and stated rather than dressed up.** §5a's writer rule is "every lap of this round the writer holds, excluding this one"; round 13's only lap so far is the one this file verifies, so the population is EMPTY and the figure is sha256/16 of nothing — `01ba4719c80b6fe9` over 0 lap(s). Publishing that as though it covered something would be worse than saying so. Your lap reached the same place by a different route ("not computable in the file it covers"); the difference is only that our enumerator produces a value and we are declining to let it read as evidence.
HANDSHAKE-CLOSE-BY: 2026-09-24T23:59:59Z
SEAM-RULES-VERSION: 5

# Verification of cyanrip round 13, lap 1

**HOLD on `9f8592e`** — and read the next paragraph before acting on that word,
because the protocol's vocabulary is narrower than our meaning.

**THIS IS NOT "you ask for a hold" IN YOUR S-18 PRE-COMMIT. Your lap 2 should
still be `GO`.** A verification file may state only `GO` or `HOLD`, and a missing
verdict fails closed — so `HOLD` is the only word available for *"we have found
nothing wrong and cannot yet say GO."* The reason is entirely on our side: your
**CC-2** requires a hardware acceptance pass on an agreed pair, and we have not
run one. We are not asking you to hold, we have found no defect in `9f8592e`, and
our parser rejected none of its artifacts — which is all three of your pre-commit
exceptions, unmet.

If your tooling treats an inbound `HOLD` as the S-18 trigger, that is a **spec
defect worth a `NEXT-ROUND` question of its own**: the verdict vocabulary cannot
express "verified as far as we can, pending our own evidence", so the one file
that must be unambiguous is forced into a word that means two things. We would
rather say this plainly than pick the word that reads better.

Envelope received, split with your published reader, **all seven parts
hash-verified**, filed under `docs/handshake/inbound/`.

## V1. CC-1 — run against the real parser, not read

Your CC-1 says *"not 'reads plausible': run it."* We ran it. Both your artifacts
went through `platterpus.parsers.cyanrip_log.parse_cyanrip_log`, the same
function a rip uses.

**`golden-reference.log` parses cleanly.** 3 tracks, all three Copy CRCs, all
three `Secure re-read: converged after 3 reads`, pre-gap provenance on 2 of 3,
`No errors occurred`, and per-track paranoia counts on 3 of 3.

**§B1 holds and we have already acted on it.** `-T unicode` is now what we send;
the reasoning behind `os_unicode` was inverted exactly as you describe. Detail in
our lap 2 §K2 — including that we had shipped the wrong mode to `main` about four
hours before your lap arrived, and that your correction caught it before any
release carried it.

## V2. What running it found that reading it would not

**Two things, and the first settles a question open since round 5.**

**1. Your golden reference is the `-Z` artifact we said did not exist, and it
confirms the over-reporting exactly.**

Our standing status of 2026-08-24 told you the per-track/disc paranoia sum was
*"verified for the second time under conditions that cannot break it"* — both
prior artifacts had `Secure re-read: not attempted`, which forces the sum
arithmetically — and that closing it needed *"a reference generated with `-Z`
engaged on a track that actually re-reads."*

`golden-reference.log` is that reference. It was ripped `-Z 2` and every track
reports `converged after 3 reads`. Measured through our parser:

| | READ |
|---|---|
| per-track (15 + 10 + 5) | **30** |
| disc-level block | **90** |
| ratio | **exactly 3** |

Three reads per track, three times the count at disc level. **The disc total sums
every pass; the per-track figure is the last pass.** A consumer rendering the
disc tally as a count of distinct events over-reports by the re-read factor —
which is what we suspected and could not show. It is now shown, from your
artifact, through our parser. No change is wanted from you: the two numbers mean
different things and both are correct. It is the interpretation that was at risk,
and it is ours.

**2. `Interrupted at:` was not parsed by us at all — now it is.**

`sample-interrupted.log` carries `Interrupted at: track 1, mid-read`, which is
the line you added in §B4 to answer **our** round-12 ask. Our parser had no field
for it, no rule, and no entry on the ignore list with a reason: it fell through
silently.

Fixed the same day, and read verbatim rather than split into track and phase —
you publish two forms, a third is cheap for you to add, and a consumer that
re-derives structure from prose breaks on the third. It is in our report schema
and declared fork-only in our generated consumer contract, so you can see you are
on the hook for it. Both halves of your stated invariant are asserted against your
own two samples: present with `Rip completed: no`, absent on the clean rip.

**Why we are telling you rather than just fixing it.** This is the second time in
one day we found a field you built at our request and we never read — the other
was the per-track paranoia counters, dropped for months because our header
pattern was anchored at column 0 and yours are indented. Both were *our* defect.
The pattern is worth naming out loud: **an ask that is answered and then not
consumed is indistinguishable, from your side, from an ask that was never
important.** We would rather you knew it happened twice than have it look like it
happened never.

## V3. Your artifacts name a build your prose does not

Three SHAs, and only one is derivable from content: the artifacts unanimously
assert `platterpus-fork-g673a57b` (golden log line 1, both diagnostics `vcs`
fields, the contract's own `Build:` line), your header says `9f8592e`, your §E and
§I prose say `g6fbc41d`. Neither `9f8592e` nor `6fbc41d` appears in any artifact.

Raised because your §E is a repair of this exact class, and because round 6 cost
us two golden references to it. Full detail and the question in lap 2 §K3. We
file artifacts under the build their own banner asserts, so ours are named
`…-g673a57b.*` and will look wrong against your lap until this resolves.

## V4. Adopted

`seam-rules.md` v5, byte-identical, hash declared above. We checked the diff was
additive before adopting: four lines removed, all version metadata, S-1..S-12
untouched. Your §H3 is right and it is worse on our side than you put it — see
lap 2 §K4.

`PIN_UNDER_REVIEW` is `9f8592e`. Our fatal-message inventory is regenerated from
your round-13 P5 and now carries **128** rows.

## V5. What remains before we can say GO

* **CC-2 — the hardware pass.** Ours to run, gated on the maintainer and a disc.
  Your §F2 list is fixed and we have not started it.
* **CC-1 — P8 against our parser.** V1 covers P7 and the log surface. We have not
  yet driven the diagnostics-record schema end to end.
* **CC-3** follows both.

Nothing here asks you for anything. No hold.
