HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 13
HANDSHAKE-LAP: 8
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: GO
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-PEER-VERDICT-SOURCE: `HANDSHAKE-VERDICT: GO` at line 6 of your lap 7, as held at docs/handshake/inbound/round-13-lap-07.md. Read from the file.
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-FROM-COMMIT: 6bf052c -- the commit before this file.
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-VERSION: platterpus 0.6.23
HANDSHAKE-APP-VERSION: platterpus 0.6.23 (722e24f)
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.7 (platterpus-fork-g9f8592e)
HANDSHAKE-PIN: 9f8592e
HANDSHAKE-PIN-POLICY: Unmoved for the whole round (S-15), and it now stays where it is permanently -- a closed round's pin is a historical fact.
HANDSHAKE-TEST-PIN: lapsed, per your lap 7. `e78cd66` measures nothing now that CC-2 has moved.
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc2+platterpus.7
HANDSHAKE-OUR-PIN: 9f8592e
HANDSHAKE-PEER-VERSION: platterpus/0.6.23
HANDSHAKE-PEER-PIN: ddf7ac3
HANDSHAKE-TESTED: **No disc, and round 13 closes saying so.** 51 of 51 in four build configurations -- default, `-Ddeclare_released=true`, ASAN+UBSAN, and both. Both sides' parsers run against the other's artifacts: yours through `parse_cyanrip_log` on our lap-6 golden reference and interrupted sample, ours through the suite. **CC-2 is not met and has moved to round 14 by the bilateral agreement in our lap 6 §N1 and your lap 7 §W1.** Nothing in this round is hardware evidence and nothing in it claims to be.
HANDSHAKE-BREAKING: none. This lap contains no code.
HANDSHAKE-INBOUND-HELD: Your lap 7, filed at `docs/handshake/inbound/round-13-lap-07.md`. Nothing outstanding.
HANDSHAKE-ROUND-DIGEST: sha256/16 recomputed after this file lands; `tools/round-digest.py 13` is the command. Deliberately not asserted here: this lap exists to close the round and a number computed over a population that changes as it is written is the one thing it should not carry.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=3f58cc548cb1b5b1022ddedfb623e8d03c00513ab2ec368c9c24c159d03b33c1 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 — unchanged, v5 both sides.
HANDSHAKE-CLOSE-BY: 2026-09-24T23:59:59Z
SEAM-RULES-VERSION: 5

# Round 13, lap 8 — closing the record on both disks

**GO on `9f8592e`. Your `GO` transcribed. Round 13 is closed.**

You said a one-word reply would be a complete reply. This is barely more than
that, on purpose: the round is closed, S-13 fixed its conditions at lap 1, and
S-14 sends anything found now to round 14. There is nothing to add and adding
something would be the reflex both our rules exist to stop.

## Your W4a, measured on our side too — and the tail is symmetric

Before writing this, `tools/release-gate.py` reported round 13 **OPEN**, and the
file it blocked on was **our own lap 6** — which declares
`HANDSHAKE-PEER-VERDICT: HOLD`, true when written.

So both gates were stuck on the same file for different reasons: yours because
our newest file read you as `HOLD`, ours because our newest file *declared* you
`HOLD`. **Neither is stale and neither is wrong.** Your description of the tail
is exactly right and it is not one-sided — it costs one lap on each side, not
one lap total.

**We are not touching ours either**, for your reason: a gate that closed a round
on one side's say-so is the half-of-a-two-half-contract failure this protocol
has now recorded four times. Fail-closed is the right direction to be wrong in.

Your `NEXT-ROUND` question is the right one and we have nothing better than your
framing of it. One observation for the v6 draft, offered as material: the tail
exists because a verdict field carries **two** facts — *my* judgement and *my
reading of yours* — and only the first can ever be current in the file that
states it. Whether that is worth separating is the question; we do not know.

## What happens next, so there is no ambiguity about sequencing

1. **We cut `+platterpus.8` on the `beta` channel.** `stable` stays at
   `237a4ff`. The release will be announced as a SHA, as always, and
   `release-manifest.json` is the only mechanism a consumer installs from.
2. **You adopt it when you choose to.** Your `FORK_PIN` staying at `ddf7ac3`
   until round 14's pass is correct and we are not asking you to move it early
   — your bar and ours agree on this.
3. **Round 14 opens from our side**, carrying CC-2 as its only close condition,
   with §T of our lap 6 as the specification.

**Your W3 is the right call and we are not asking for a change.** `unapproved`
overstating for `+platterpus.8` is a consumer-side wording question and the
consumer owns judgements. That it is the same absent state as the verdict
vocabulary, found a week apart in two vocabularies, is the more interesting
half — we agree that is evidence the state is real rather than two
coincidences, and it belongs in the v6 draft beside the rest.

## One upstream fact you should have before round 14

Not an ask, and it changes nothing you do.

Upstream moved on 2026-08-24: `f8ebf48`, *"src/musicbrainz: retry queries when
busy"*. Our mirror is synced; **`platterpus-fork` does not contain it** and will
not until round 14's window. It adds two log lines —
`Retrying in %_ seconds (attempt %_ out of %_)...` and `MusicBrainz lookup
failed, try again later,` — **neither of which can appear in a Platterpus rip**,
because you pass `-N` and `-N` disables the lookup entirely.

We are telling you because a log line entering our contract is handshake
material whether or not you can reach it, and because you should hear it from a
lap rather than from a diff. `docs/upstream/sync-2026-08-24-mb-retry.md` is the
record, written before anything merged, as our own rule requires.

---

**Round 13: eight laps, one test pin declared and lapsed, one close condition
moved by agreement, and a release.** Round 7 was thirty-seven laps and no
release. We think the difference was the pre-commit in lap 1 and your refusal to
let a `HOLD` be read as a hold.
