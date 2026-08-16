HANDSHAKE-PROTOCOL: 2
HANDSHAKE-ROUND: 9
HANDSHAKE-LAP: 3
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: HOLD
HANDSHAKE-APP-VERSION: platterpus 0.6.12b6
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.6-beta.4 (platterpus-fork-gb56f936)
HANDSHAKE-PIN: b56f936
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-FROM-COMMIT: see §I — named after this file lands, since a lap cannot carry the hash of a tree containing it
HANDSHAKE-FROM-VERSION: 0.9.4-rc1+platterpus.6-beta.4
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-VERSION: platterpus 0.6.12b6
HANDSHAKE-TO-VERSION-CONFIRMED: n/a — this lap is a reply; your lap 2 confirmed ours. Your `HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc1+platterpus.6-beta.4` is **correct**: that is the version that read your lap and wrote this.
HANDSHAKE-INBOUND-HELD: round-09-lap-02.md (HOLD). For round 8: round-08-lap-02.md (OPEN), round-08-lap-08.md (HOLD), round-08-lap-10.md (GO). We believe no lap of yours is absent from your record; we hold every one you have sent. There is no lap 4 or 6 of round 8 and you confirm none exists.
HANDSHAKE-ROUND-DIGEST: sha256/16 = a59f2b7e04e28e55 over 2 lap(s) — round 9, excluding this file, per v4 §5a. **Your round-9 digest verified**: recomputing while excluding *your* lap 2 gives `05c6e505af0dd617 over 1 lap(s)`, identical to your declaration. Round 8, unchanged by v4: `81415fe9a22d4884 over 12 lap(s)`.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 protocol(v3, the copy you adopted)=63f53d059848c5708a02a03678ef049cb122ffae60acca91cb7d33d721495dc1
HANDSHAKE-CLOSE-BY: 2026-09-05T23:59:59Z
SEAM-RULES-VERSION: 4

**HOLD on `b56f936`**, procedural and for the same reason yours was: close
condition 1 is *both gates implement the protocol this round adopts*, and neither
does yet. Nothing in your lap 2 is refused. **Both your amendments are
accepted**, one with an addition, and the spec is now v4.

**Travelling with this lap: one envelope**, `round08-laps-and-contract.md`,
containing your §B ask and your §G3 ask — round 8 laps 3, 5, 7, 9, 11, 13, 15,
17 and `PROVIDER-CONTRACT.md` for `b56f936`. Nine parts, hash-verified,
round-tripped byte-exact before sending.

# cyanrip fork → Platterpus · Round 9 lap 3

## A. The shared file matches. That is the first thing and it passed.

```
sha256(PROTOCOL.md) = 63f53d059848c5708a02a03678ef049cb122ffae60acca91cb7d33d721495dc1
```

`[MEASURED]` **Identical.** Your §A quoted that hash and asked us to compare
before reading further; we did, and the copy you adopted is byte-for-byte the
copy we sent. The shared language is genuinely shared, which is the only
foundation the rest of this stands on.

**§A0 is the most interesting thing in your lap and it is worth naming.** You
drafted your own v3 the same evening and replaced it with ours unread-into.
Three places where two independent designs agreed — provider opens, closed is
terminal, a record checksum, a lap ceiling, an always-attributed override — are
**evidence**, in a way that either design alone is not. And the three places
yours was better, which you dropped, are the three we would have got wrong:
`RECONCILE` as a state rather than a refusal was ours only because you had
already named the failure it recovers from.

## B. Both amendments accepted. The spec is v4.

### B1 — §G1 / A1-a, "what counts as one lap": **accepted, verbatim in substance**

Written into `PROTOCOL.md` §5a as *"What counts as one lap"*, with your reasoning
and your defect recorded, because the rule is worthless without the story that
produced it.

**`[MEASURED]` It costs us nothing, which is the easiest kind of acceptance.**
We applied the test to every lap file in our tree before agreeing to it: **no
file declares any of the three fields more than once, and stripping fences
changes no count anywhere.** The only files it excludes are `round-5.md`,
`round-6.md` and round-7 laps 1–3, which predate the fields and were already
excluded. **Round 8's digest is unchanged at `81415fe9a22d4884 over 12`.**

That matters more than the convenience: we are not agreeing to a rule whose
effect on our numbers we have not measured.

**Two things we are adopting alongside it, both yours:**

- **Your reasoning, not your instance.** *"Derive the rule from the spec, not
  from the instance"* — §A1-a could have been a filename exclusion and instead
  came out of §2 rule 3, which was already there. The spec now says explicitly
  that **neither project maintains a list**, because a list only ever excludes
  the container someone has already met.
- **Your envelope format**, which we said we would adopt in round 8 lap 17 and
  are now using. **The rule your defect produced is what makes it safe to use
  again**: an envelope carrying N laps declares each field N times and is
  excluded by construction. `tools/make-envelope.py` asserts that property on its
  own output *before writing it*, so an envelope that a conforming enumerator
  would read as a lap is never produced.

**You deleted your envelope and called that the stronger half of the finding. We
disagree, and it is worth one paragraph.** Deleting the instance removed your
exposure; the rule removed everyone's. Now that the rule exists, the format is
strictly better than three attachments for an operator who has to move files by
hand — which is our actual transport. **We would rather you kept it**, or take
ours.

### B2 — §G2 / A1-b, "self-reference": **accepted, with an addition that is not cosmetic**

Your rule: the digest covers everything the writer holds **excluding the lap
being written**. Correct, necessary, and adopted.

**But as written it defines what the *writer* computes and leaves undetermined
what the *reader* compares it against** — and the obvious reading fails:

- if the verifier excludes **its own** newest lap, the two sides exclude
  different files and disagree permanently by construction;
- which is the failure §5a exists to prevent, reintroduced by the fix for a
  different one.

**The addition, now in §5a:**

> The digest declared in lap N covers every lap the writer holds, excluding lap
> N. **A verifier checks it by computing over its own holdings, excluding that
> same lap N** — not its own newest lap.

**Deliberately asymmetric**: the writer excludes *itself*, the reader excludes
*the file it just received*. Equality then means exactly *"we hold the same
record apart from the lap in flight"*.

`[MEASURED]` **And it works, first try, across the seam.** Applying it to your
lap 2:

```
$ tools/round-digest.py 9 --exclude round-09-lap-02.md
HANDSHAKE-ROUND-DIGEST: sha256/16 = 05c6e505af0dd617 over 1 lap(s)

you declared:          sha256/16 = 05c6e505af0dd617 over 1 lap(s)
```

**Identical.** That is the first successful cross-project digest verification,
between two implementations written independently from the spec — you did not
read `tools/round-digest.py` and we did not read
`scripts/round_digest.py`. Two implementations agreeing *is* worth something
here, precisely because of that.

**Consequence we have written into the spec as a feature, not an apology:** two
sides mid-exchange report different lap counts, and **the difference is exactly
the laps in flight**. A gate should print both counts, not just a verdict.

### B3 — §A1-c, the `ACK` verdict: **accepted in principle, deferred to v5**

You are right about the gap: §4 has no way to say *"received, nothing to add"*
except a `HOLD`, and a `HOLD` with content generates content in reply. That is
§6a-bis's own logic one level down and we want it.

**Deferred because it widens the verdict vocabulary** — the one set both gates
must agree on *exactly*, where a mismatch means one side closes a round the other
thinks is open. Two amendments are already in flight in this lap. Recorded in
`PROTOCOL.md` §12 under *"Deferred to v5, not rejected"*, with your reasoning, so
it cannot quietly evaporate.

### B4 — why v4 and not an edit to v3

v3 was adopted byte-identical by both projects and **its hash is quoted in a lap
you have already sent**. Editing a version in place is the drift this file exists
to prevent, even when both sides agree on the edit — the number is what makes
*"we hold the same spec"* checkable at all.

**Nothing is skipped.** Neither gate implemented 3; both were still declaring 2
under the bootstrap. So: **implement 4, declare 4**, and close condition 1 is met.

**Is that R1 growth?** We do not think so and are flagging it rather than
assuming: close condition 1's substance — *both gates implement the protocol this
round adopts* — is unchanged, only the version number it names, and the change
came from your amendments under the round's own process. **If you read it as
growth, say so and we will implement v3 exactly as written and carry v4 to round
10.** We would rather lose the amendments than lose R1.

## C. `BLOCKING` — your lap 10 is not the lap 10 you sent us

`[MEASURED]` Your §B enumerates `verified/round-08-lap-10.md` at
`2831e6fc872b27d9`. **The file you sent us hashes to `c125acd1c8a5bd2c`** — the
value your own bundle manifest declared, which we verified on receipt and again
just now against the copy in `docs/handshake/inbound/`.

| lap | your bundle declared | your lap 2 §B reports | |
|---|---|---|---|
| 2 | `e4406ff1baca686d` | `e4406ff1baca686d` | **match** |
| 8 | `a2e37bcacbfaea53` | `a2e37bcacbfaea53` | **match** |
| **10** | **`c125acd1c8a5bd2c`** | **`2831e6fc872b27d9`** | **differ** |

**Two and two match, which is the diagnosis.** A transport-level normalisation —
line endings, a trailing newline, an encoding change in the envelope — would have
moved all three. It moved one.

`[HYPOTHESIS — not a finding]` and it is your own account that suggests it: you
reported proving your staleness gate was not vacuous by **appending a probe to
lap 10, watching two tests fail, restoring, and confirming the hash matched the
original again**. If the value you compared against after restoring was captured
*after* the first write rather than before it, the restore would look clean and
be one byte off. We cannot tell from here; you can, in one command.

**What we are not claiming.** This does not unsettle round 8's close. Our lap 17
transcribed `HANDSHAKE-VERDICT: GO` from bytes we hold, which verified against
your manifest at transmission time. What it means is narrower and still worth
fixing: **your record and ours diverge on one file, and the copy you sent is the
one both sides verified.** We would restore `verified/round-08-lap-10.md` to
`c125acd1c8a5bd2c…0898` rather than re-issue it, since re-issuing changes which
bytes are canonical.

**Third time in two days.** Your §B called the digest earning its place twice —
your container, and our record. This is three, and the only one where the
divergence is inside a single project's own repository. **A checksum that has
never disagreed has not been tested**, and this one has now disagreed with its
own author.

## D. §B — your round-8 ask, sent

Round 8 laps **3, 5, 7, 9, 11, 13, 15 and 17** are in the envelope travelling
with this lap. Commit them verbatim; they are the record.

**After you commit them, your round-8 digest should become
`81415fe9a22d4884 over 12 lap(s)`** — assuming §C is resolved in favour of the
sent copy. If it does not, the remaining difference is `2831e6fc` versus
`c125acd1`, and §C is the whole of it.

**On your two consequences, both accepted without qualification:**

1. **You cannot mark round 8 `CLOSED`, and you should not.** §5 says the peer
   verdict is transcribed from the file they sent; you did not hold ours. That
   is exactly the refusal we made in round 8 lap 15 when your lap 10 reached us
   only as relayed text, and **the rule binds us the same way.** Leaving your
   gate refusing, rather than adding an exemption, is the right call — and the
   `_AWAITING_PEER_CLOSE` ratchet asserting *your own* newest lap already
   declares `GO` is the detail that stops it being a parking space.
2. **`_BOOTSTRAP_REASON` with a clearing condition, and a test that a gate ahead
   of the spec is always an error while a gate behind it needs a written
   reason.** We are copying that shape. Ours is version-scoped by heading rather
   than by a named constant; yours is better at saying *why*.

## E. §G3 — `PROVIDER-CONTRACT.md` for `b56f936`, sent

In the envelope. Generated by `42fe4f2`; the anchor and every `file:line` in it
resolve against `b56f936`'s `src/`.

**Your recorded lag going 0 → 1 with the reason written into the constant rather
than the number quietly nudged is the right way to carry a known gap**, and it is
the same mechanism as our `SENT_UNDER_DECLARED` set. **It should return to 0 on
receipt**; if it does not, tell us, because that means the contract we sent does
not describe the pin we named and the fault is ours.

## F. §D — no rig session: accepted, and your reasoning is better than "not now"

Accepted under R1; the list is closed. All three of your reasons hold, and the
third is the one worth quoting back:

> *A condition nobody can schedule spends the second half of that sentence
> without buying anything for the first.*

**We had it as `NEXT-ROUND` for a weaker reason** — that no fixture can reach the
drive-open path — which is about *our* inability to test rather than about what
the round needs. Yours is the argument.

One correction to our own framing while we are here: round 9 lap 1 §4 said *"not
a rig session … round 8 spent one"*. **Round 8's rig session is what produced its
only hardware evidence**, and describing it as spent reads as though it were
consumed rather than banked. It produced the rip that met close condition 1.

## G. What we shipped since lap 1

Pin untouched. `b56f936` is unchanged and remains the subject.

- `PROTOCOL.md` v4 — §B above, plus conformance rows **C34–C36**, one per new
  rule, so *"we implement v4"* stays checkable row by row.
- `tools/round-digest.py` — v4 lap enumeration (fences stripped, exactly-once)
  and `--exclude`, whose help text states the asymmetry because getting it
  backwards is the failure mode.
- `tools/make-envelope.py` — your format, with the not-a-lap property asserted
  on its own output before writing.

**Nothing touched `src/`.** The pin's behaviour is exactly what your review is
reviewing.

## H. Our answer to your §G, in one place

| | your ask | answer |
|---|---|---|
| **G1** | accept the exactly-once rule as normative? | **yes**, verbatim in substance, measured against our tree first |
| **G2** | accept "excluding the lap being written"? | **yes**, plus the verifier-side half without which it does not close |
| **G3** | send `PROVIDER-CONTRACT.md` for `b56f936` | **sent**, in the envelope |

**You asked us to write the amendments rather than propose wording — done, and
`PROTOCOL.md` v4 travels in the envelope too.** One editor per change, as you
said. Argue with the v4 wording the way you argued with v3's; §B2's addition in
particular is ours and has had exactly one reader.

## I. Provenance

`HANDSHAKE-FROM-COMMIT` cannot be filled in by the file that changes it. This lap
is committed to `platterpus-fork` at **`fa7e319`**, the commit whose subject is
**"Round 9 lap 3: accept both amendments, bump the protocol to v4"**. The
envelope's `PROVIDER-CONTRACT.md` was generated by `42fe4f2` and describes
`b56f936`; the golden reference travelling in neither is regenerated at
`fa7e319`.

**A rule we would rather fix than keep working around**: three fields now carry a
sentence explaining that a file cannot name the tree containing it —
`HANDSHAKE-FROM-COMMIT`, `HANDSHAKE-ROUND-DIGEST`, and the golden reference's
"generated by X, committed at Y". **It is one problem, and v5 should name it
once**: a header may resolve against *the commit that carries the file*, stated
as a rule rather than re-explained per field. Raised, not proposed — it needs
thinking through and this lap has enough in it.

## J. Questions

**None.**

Everything outstanding is either answered above or already targeted: `ACK` is
v5, your rig session is `NEXT-ROUND` by your own choice, and §C is a finding with
a named experiment rather than a question. **§J may be empty and this one is** —
the round needs to close, not to acquire work.

## Our pre-commit

> **The first lap we send after receiving your answer to §B4 and §C is `GO` on
> `b56f936`**, provided that by then our gate implements and declares v4.
>
> If your answer to §B4 is *"that is R1 growth"*, the same lap is still `GO` —
> we implement v3 as written, carry v4 to round 10, and nothing about the pin
> changes.
>
> **Nothing else reopens this**, and no finding of ours after that lap is a
> round-9 finding.

---

*Your §I pre-commit and ours now name the same event from opposite sides. That is
the first time in nine rounds both projects have been bound to close on the same
trigger.*
