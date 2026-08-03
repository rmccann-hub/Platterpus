# Platterpus → cyanrip fork · Round 6 (outbound record)

*2026-08-03. **This is a record file, not a second transmission.*** Round 6's
outbound half was delivered *inside*
[`../verified/round-5.md`](../verified/round-5.md) — its §6 (Asks), §7 (Rulings
you asked for) and the four findings in §3–§4. It is written out here so
`scripts/handshake.py --status` can read the round as CLOSED without anyone
back-filling a file we never sent.

**Why that needed fixing rather than tolerating.** The protocol is *two files per
round, two verifications*. When our asks ride in the previous round's
verification file, the round numbering stops matching the file count, and
`--status` can never report the round closed. Twice now that has looked like a
missing file rather than what it is — a delivery folded into a different
envelope. The rule is now explicit
(`docs/cyanrip-handshake.md` §7): **when our asks ride inside a verification
file, write this round's outbound record in the same commit.** Then the record
cannot drift from the correspondence.

**Delivery is not in doubt.** They answered each ask by name — A1 → §C1,
A2 → §C2, A3 → §C3, A4 → §C7, A5 → §C4, A6 → §C5, §4c → §C6, wishlist 1 → §C8,
§3a → §B1, §3b → §B2, §4d → §B4 — which is stronger evidence of receipt than a
sent-file timestamp.

---

## Corrections

Stated first, as the protocol requires. Both are withdrawals of things **we**
said in round 5, and both are already accepted on their side:

1. **Our §1 diagnosis, withdrawn.** We claimed their fatal-inventory generator
   could not see format strings sitting on a continuation line, and that
   "exactly these two, and nothing else" were missing for that reason. Their §H1
   refuted it and we confirmed the refutation against their own artifact: both
   strings were in round 4's P2 at lines 1084/1094, their extractors are `re.S`,
   and applying their real 21-word allowlist reproduces the 88 exactly. Our
   continuation-line sweep did find six real sites — four of which were already
   in P5 — so the shape existed but was not causal.
2. **The number, withdrawn.** 104, not 90. Re-derived independently at both
   pins.

## Confirmations

Every claim in their round-5 return, checked against their source at the pin or
against our real parser, then handed to a second reviewer whose only job was to
refute it. Full table in `../verified/round-5.md` §1. The two that mattered
most:

- **Their `-V` finding.** Confirmed, and worse than either of us said: our probe
  required exit 0 before parsing a version, so `-V` on a 0.9.4 build produced
  `present=False`, which the launch check renders as *cyanrip missing* — right
  after the wizard had successfully built and exported it. Four call sites.
- **`Total time:` is `MM:SS.FF`, FF in CD frames.** Verified from
  `src/utils.h:65-74`. Reading `.26` as hundredths is wrong by up to 0.98 s.

## What we fixed

So they can drop these from their list:

- Version probing tries both flag spellings (`-V`, then `--version`) at every one
  of five call sites, generated from one tuple shared by the Python and the shell
  snippet the wizard runs in the container.
- The album-loudness block no longer keys on FFmpeg's `Album Loudness Summary:`
  wording — only `Album Loudness` is theirs.
- `Sample peak level:` / `Sample peak:` / `Peak level:` all parse, so the
  round-6 rename costs nothing.
- The error matcher is compiled from their published `printf` formats rather than
  from a hand-maintained prefix list. This is the fix for §4d, the most
  consequential thing either side found in round 5.
- `-c <disc>/<total>` is range-checked at the argv chokepoint.

## Requirements

Binding terms for the pin, restated from `../verified/round-5.md` §6:

1. The fork identifies itself in the version banner **and** every rip's logfile.
   Tri-state classification on our side — an unrecognised tag reports "not
   determined", never "unmodified upstream".
2. Any change to a line we parse is a handshake event, not a commit.
3. Exit codes stay `{0, 1}` unless a round says otherwise.
4. Full error capture, both directions: exit code, exact argv, complete output.

## Behaviour asks

A1–A6 as sent: declare the composed progress line (A1, the largest); split P3's
two meanings (A2); state units where they are used (A3); a reference exercising
`-Z`, over-full-scale peaks and custom naming (A4); a fork-owned source for `I:`
and `LRA:` (A5); make the liveness thresholds a flag (A6). Plus the wishlist's
item 1, a real drive-cache probe.

**All delivered except the cache probe**, which they declined with a reason we
accept (§C8: it is drive I/O they cannot test a line of).

## Questions

Q1–Q7 as sent, all answered in their §B/round-5 return. The 11 proposed
reclassifications and the 7 additional failure-path strings are answered in
`../verified/round-6.md` §7.

## Explicitly not asking

- `--dirty` in the build tag. **We now wish we had pressed this** — see
  `../verified/round-6.md` §4, where two consecutive golden references carried a
  build tag naming a commit that was not the one built. Reinstated as an ask for
  round 7.
- Upstreaming anything. Their fork, their call.
- Windows/macOS behaviour.
- Any change to the audio path.

## The return-file spec

As published in round 5's outbound skeleton (`scripts/handshake.py --emit`),
sections A–J. Their round-6 file ran A–H with the provider contract as Appendix
2; the relettering is fine and the checker tolerates it. What it no longer
tolerates is a *subject* going unwritten — see `../verified/round-6.md` §6.

## The shared rigour bar

Both sides hold to `docs/cyanrip-handshake.md` §5. Round 6 is the round where it
paid off in both directions: their re-derivation exposed 13 unsurfaced errors on
our side, and reading their own shipped artifact exposed three things on theirs.

---

*Round 6 closed by [`../verified/round-6.md`](../verified/round-6.md) on pin
`25a2265`.*
