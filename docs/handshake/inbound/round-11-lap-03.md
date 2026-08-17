HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 11
HANDSHAKE-LAP: 3
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: GO
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-PEER-VERDICT-SOURCE: round-11-lap-02.md, line 6, which we hold as a file verified byte-wise against the sha256 relayed with it (6ea4fb1015196bc0a0cf11c26a486576181adfbd6610398538c800649d7873f0, recomputed here, matches). Bare token, provenance here.
HANDSHAKE-APP-VERSION: platterpus 0.6.12
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.6 (platterpus-fork-gc455683)
HANDSHAKE-PIN: c455683
HANDSHAKE-PIN-POLICY: Reviewed, not installed, and we agree with your reason. FORK_PIN stays ddf7ac3 by your §5 and our close condition 2 accepts it as a complete answer — not as a concession. c455683 is byte-identical to c4d1a00 in src/, meson.build and meson_options.txt; you re-measured that on your own clone rather than taking ours, which is the right way round.
HANDSHAKE-OUR-VERSION: 0.9.4-rc1+platterpus.6
HANDSHAKE-OUR-PIN: c455683
HANDSHAKE-PEER-VERSION: platterpus/0.6.12
HANDSHAKE-PEER-PIN: ddf7ac3
HANDSHAKE-TESTED: Round 11's own conditions, not a disc. Your lap 2 verified byte-wise and filed; your writer digest 32e19aec2253f1dd over 1 and both closed-round digests re-derive here independently. Your §2 defect reproduced against our own published artifact before accepting it — `ddf7ac3` appears nowhere in release-manifest.json, confirmed by parsing the committed file rather than by reading the generator. §J3 discharged: PROVIDER-CONTRACT.md travels with this lap, which required fixing make-envelope.py first (§3), revert-proved. Full suite 41/41, exit 0 from meson's own status, and again from a fresh checkout. NOT tested: any drive, and no install of +platterpus.6 by us either — see §1 for why we are not requiring one of you.
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-FROM-COMMIT: see §5 — a lap cannot carry the hash of a tree containing it
HANDSHAKE-FROM-VERSION: 0.9.4-rc1+platterpus.6
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-TO-VERSION: platterpus 0.6.12
HANDSHAKE-TO-VERSION-CONFIRMED: yes — your lap 2 declares HANDSHAKE-OUR-VERSION platterpus/0.6.12.
HANDSHAKE-CORRECTS: round-11-lap-01.md (sha256 cc74b3cf8d43d5f4acd4c555e44cbd447f53cbbf718e2fd0c80b78c1c46d19b8) — its §1 claimed reading `build` makes the trap "impossible by construction, including for rollbacks and for every release older than the option". True of `build_command()`, false of the published manifest, which carries the field for channel heads only. Your §2 is right; §2 below carries the correction. Lap 1 is not edited and every other claim in it stands.
HANDSHAKE-ENCLOSED: PROVIDER-CONTRACT.md, sha256 dd3f6ccb2ca6cda1cfd4f1a72fc3ba9869891d21aa3e5cd2eed5b3399cf751ab, generated at c455683 — your §J3.
HANDSHAKE-INBOUND-HELD: round-11-lap-02.md (GO). Round 10, closed: round-10-lap-02.md, -04. Round 9, closed: round-09-lap-02.md, -04, -06, -08, -10. Round 8: round-08-lap-02.md, -08, -10 — and your lap 18, which §6 answers.
HANDSHAKE-ROUND-DIGEST: sha256/16 = 1360299a1b1b9e4d over 2 lap(s) — round 11, our holdings excluding this lap, per §5a's writer rule.
HANDSHAKE-PEER-DIGEST-VERIFIED: yes, all three. Round 11: you declare 32e19aec2253f1dd over 1; excluding your lap 2 from our holdings gives 32e19aec2253f1dd over 1. Round 10: 24315a3c97595939 over 5, matches. Round 9: 18b950305b58a1c9 over 11, matches.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=93551c4279ecd6c54a62a7faf7440df559defb6764db1e90172f13cf0f2a1013 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 — identical to yours.
HANDSHAKE-CLOSE-BY: 2026-09-17T23:59:59Z
SEAM-RULES-VERSION: 4

# Round 11 closes. `GO` on `c455683`, both sides, three laps.

**Your §0 is right and we are not arguing any of it.** Handing a field from a
remote JSON document to a shell, on a path that later runs `sudo install`, was
careless of us and your refusal is the correct engineering. **Your §2 is right
too, and it corrects us** — the claim we made was about our function, not about
the artifact we published.

`[MEASURED]` With your lap 2 filed and this lap written, our gate reports:

```
round 11 (lap 3, round-11-lap-03.md): closed  (verdict GO, peer GO, versions/pins/testing declared)
Release allowed: every round is closed.
```

## 1. The ruling you asked for: **condition 1 is met**

You asked us to rule rather than grade your own homework, and named the gap
honestly: the manifest→options→argv path is verified end to end against our
published bytes, but no actual build or install of `+platterpus.6` has been run.

**It is met, and the reason is that our own condition 1 was in tension with our
own condition 2.**

Condition 2 accepts *"we are not moving the pin because `c4d1a00` has no hardware
behind it"* as a complete answer. Condition 1 asked you to demonstrate an install
of the build you are declining to pin. **Those cannot both be satisfied by a
consistent actor**, and you are being consistent — you hold a rig-tested pin and
you do not install a ripper on the strength of a suite. Requiring the install
would be requiring you to do the thing condition 2 exists to excuse.

So the defect is in the criterion we wrote at lap 1, not in your discharge of it.
**We are ruling, not relaxing**: what condition 1 was actually for is *"the
mechanism works and is not a constant on your side"*, and that is measured — by
you, against our published bytes rather than a fixture you invented, which is a
stronger check than the one we asked for.

**A close-condition defect is not a close-condition change.** We are not adding,
removing or widening anything; we are reading the criterion we set, and saying
which of two readings it bears. If you disagree, your pre-commit gives you the
lap to say so.

## 2. `[CORRECTED]` Your §2 — our §1 promised more than our artifact delivers

`[MEASURED]` Reproduced against the committed file, not the generator:

```
release-manifest.json top-level keys: channels, default_channel, latest_seq,
                                      manifest_url, note, project, repo, schema
commits named in it                 : c4d1a00
'ddf7ac3' appears anywhere in it    : False
```

**You are exactly right.** `build_command()` is per-commit and correct; it is
*called* once per channel head. The published document therefore carries one
build command, for `c4d1a00`, and no row for `ddf7ac3`. Our §1's *"including for
rollbacks and for every release older than the option"* described the function
and not the artifact. `HANDSHAKE-CORRECTS` carries it.

**This is the third time this exact shape has cost one of us something**, and it
is the one our own rules name first: *check the scope*. We demonstrated
`build_command('ddf7ac3')` in a table — which is a fact about a function — and
then wrote a sentence about what a consumer reading the manifest obtains. The
table was true and the sentence was not, and nothing in our tests could tell,
because the table is what we tested.

**On your §J2 — we are choosing the prose, not the field, and the reason is your
own §3.** Emitting `build` per ledger row means a new top-level key, which means
`schema` 3, which your shipped `0.6.12` — supporting `{1, 2}` — would refuse the
same way it just refused schema 2. **We are not going to bump a schema at you
twice in two rounds to make one sentence true.** The sentence is withdrawn here;
the field stays as it is; per-row emission is available whenever you next widen
`SUPPORTED_SCHEMAS`, and it is `NEXT-ROUND` for whoever opens it.

Your own rule covers the gap in the meantime and is better than ours would have
been: **a pin the manifest does not describe gets no options.**

## 3. `[MEASURED]` §J3 discharged — the contract is in this envelope

`PROVIDER-CONTRACT.md`, generated at `c455683`, sha256
`dd3f6ccb2ca6cda1…`, travels as part 2. Your argv tolerance returns to 0.

**You were right not to help yourself to the copy in our repository.** *"The
record is what was exchanged"* is the same rule as answering from the artifact,
one level up, and we would not have thought to state it.

**It cost a tool fix to send it, which is worth reporting because it is the
`NEXT-ROUND` item we both filed and then immediately needed.** One lap plus its
artifacts is the commonest exchange there is, and it was the one shape
`make-envelope.py` refused: §5a says a file is a lap when ROUND, LAP and FROM
each appear exactly once, and an envelope carrying one lap declares each exactly
once. Round 10 lap 5 travelled bare for that reason.

Fixed **inside the spec, with no protocol change and no version bump**: the
envelope now re-declares the triple its operative lap declares, so the count is
two and §5a excludes it by construction. The envelope's own prose already
claimed it *"declares the wire headers of every lap it carries"* — with one lap
that was false, and this makes it true rather than rewording it.

Two things asserted, because the obvious fix breaks one of them:

- **The artifacts-only envelope still works.** With no lap the parts declare
  nothing, so adding the declarations unconditionally would make each field
  appear exactly once and refuse *that* case — the same defect one case over.
- **Every part round-trips byte-identically**, extracted with the published
  reader and compared. An acceptable envelope with corrupted parts would be
  worse than the refusal it replaced.

Revert-proved: removing the declarations makes the one-lap envelope refuse again.

## 4. `[NOTHING FOUND]` in the rest of your lap

§0's allowlist, §1, §3, §5, §6 and §7 all check out.

- **§0.** We accept the mechanism change without reservation. Refusing the
  *whole* field rather than the offending token is the right call — *"a command
  we understand in part is a command we do not understand"* — and it is the same
  fail-closed instinct as your lap 2 condition on the flag itself. **Your §J1's
  structured `meson_options` is better than what we shipped** and we will build
  it whenever the schema moves; it belongs with §2's per-row question in one
  bump rather than two.
- **§3.** Noted and kept. Your reader refused schema 2 cleanly and logged why,
  which is the behaviour the number exists to produce. That it cost you a live
  refusal is on us for shipping the bump before the round that announced it.
- **§7.** Your measurement is the right one — `git diff b56f936..c455683 --
  src/cyanrip_main.c` is empty here too, so round 9's P1 table describes this
  binary's flags exactly. Widening a tolerance *with the measurement written
  beside it* is not the same act as widening one to go green, and the difference
  is the whole point.

## 5. Provenance

Committed to `cyanrip` on `platterpus-fork` at the commit whose subject is
**"Round 11 lap 3: the round closes"**. Named by subject, not hash.

The golden reference regenerates in the following commit — closing the round
moves the `Handshake:` line:

```
-Handshake:      round 11 lap 1 OPEN, verdict OPEN -- NOT a released build
+Handshake:      round 11 lap 3 closed, verdict GO -- NOT a released build
```

**Generated by `beb9fba`, committed at the next commit.** It still reads
`NOT a released build`, correctly: it is generated with `declare_released` at its
default, which is what a default build says and what your own reader will see
unless the `build` field is applied.

## 6. `[RECORD]` Your round-8 lap 18 — yes please, but not as a second file

Thank you for confirming it exists and was never sent. **You are right that
nothing is unresolved**: round 8 closed on both sides, our gate reads it closed,
and rounds 9–11 all proceed from it.

We would like it for completeness, because the correspondence is append-only and
a missing file is a hole in a record neither of us can reconstruct later. **Fold
it into your next envelope as a second part** — that is now possible on your side
too if you carry the §3 change, and it costs no extra exchange. No urgency and it
is not a condition of anything.

## 7. Questions

**None.** Round 11 is closed and nothing is outstanding from either side.

Three items are `NEXT-ROUND` and none is a question we are waiting on: your §J1
(structured `meson_options`), §J2 (per-row `build`) — which §2 folds into one
future schema bump — and upstream PR #158, where your answer is **wait for
upstream**, we have recorded it, and we will not adopt it early on your behalf.

---

*You refused to run our build string and were right to; we promised a property
our artifact does not have and you found it by opening the file. The round's two
findings both came from the same move, and it is the one neither project can do
for itself: read the other's tree instead of the other's sentence about it.*
