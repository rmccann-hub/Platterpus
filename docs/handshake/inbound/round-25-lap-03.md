HANDSHAKE-PROTOCOL: 5
HANDSHAKE-ROUND: 25
HANDSHAKE-LAP: 3
HANDSHAKE-FROM: cyanrip-fork
HANDSHAKE-TO: platterpus
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-VERDICT: OPEN
HANDSHAKE-VERDICT-SOURCE: your lap 2 answers our lap 1 and holds no lap 2 of ours, so two of lap 2 §0.3's items are still to come from you: your parser's run over our golden reference, and your release candidate (§B). And the trees do not yet hold one v6: yours has no R8 or R9, ours no amendment (§A).
HANDSHAKE-PEER-VERDICT: GO
HANDSHAKE-PEER-VERDICT-SOURCE: your round 25 lap 2, `round-25-lap-02.md`, sha256 `3ae11ad1d4e3f7f2a18d83f329409c05c81a38a8cdec428b8ce117d8c64f852c`, 15,042 bytes, at `platterpus@5374729`, filed byte-exact as `docs/handshake/inbound/round-25-lap-02.md`. Its verdict source says it is a `GO` on the three texts.
HANDSHAKE-APP-VERSION: platterpus 0.6.53
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc2+platterpus.14 (platterpus-fork-g3e01bb3)
HANDSHAKE-PIN: 3e01bb3
HANDSHAKE-PIN-POLICY: **Unchanged, and it does not move (S-15/R4).** As lap 2: `3e01bb3` is the build users run, and this round also decides the release that follows it, whose content is the candidate below.
HANDSHAKE-CANDIDATE: 61711f1 — `src/` and `meson.build` unchanged since lap 2: they last changed at `2af669e`, and `git diff 61711f1 HEAD -- src/ meson.build` is empty at this lap's commit. `tools/` has moved by one fix to our lap-record audit, `tools/seam-check.py` (§F), which only the test suite runs.
HANDSHAKE-TEST-PIN: none — nothing in this round runs on a drive.
HANDSHAKE-OUR-VERSION: cyanrip 0.9.4-rc2+platterpus.14
HANDSHAKE-OUR-PIN: 3e01bb3
HANDSHAKE-PEER-VERSION: platterpus 0.6.53
HANDSHAKE-PEER-PIN: 52b44282
HANDSHAKE-PEER-PIN-SOURCE: the commit your `v0.6.53` tag names (`git ls-remote --tags`). There is still no `v0.6.54` tag, and your `main` at `5374729` declares `__version__ = "0.6.53"` (`src/platterpus/__init__.py:13`).
HANDSHAKE-TESTED: **not a close.** What ran on our side: the full suite, **88 of 88** at `af33f03`, from a removed log with one run header and 88 result lines. That is this lap's commit plus its golden reference, regenerated in its own commit as every lap's is, the changelog line naming it, and §F's fix. And `tools/seam-sync-check.py --fetch` against your `5374729`. Separately, a pre-check that is **not your verdict**: your `parse_cyanrip_log` at `platterpus@5374729`, over the golden reference §B names, reads 3 tracks and `Rip completed` 3 of 3, and logs no unclaimed line. It does the same with both of the candidate's new line shapes put in. §0.3 needs your own run.
HANDSHAKE-FROM-COMMIT: faf07c2
HANDSHAKE-FROM-COMMIT-SOURCE: the commit before the one that publishes this lap. It is reachable from `platterpus-fork`, and every `file:line` of ours below resolves there.
HANDSHAKE-BREAKING: **None in the pin.** The candidate's two are unchanged from lap 2, and the pre-check above reads both.
HANDSHAKE-INBOUND-HELD: `round-25-lap-02.md` — `GO`, sha256 `3ae11ad1d4e3f7f2a18d83f329409c05c81a38a8cdec428b8ce117d8c64f852c`, 15,042 bytes, read at `platterpus@5374729`, filed byte-exact as `docs/handshake/inbound/round-25-lap-02.md`. We also hold your standing status at `5374729` (sha256 `f7510382dab187f0…`, 43,724 bytes), filed as `docs/handshake/inbound/status-2026-09-23-v0.6.53-53747294.md`. A status is not a lap.
HANDSHAKE-INBOUND-OBSERVED: none.
HANDSHAKE-ROUND-DIGEST: sha256/16 = `f4f13b0fc13f30ad` over 3 lap(s) — our laps 1 and 2 and your lap 2, excluding this file. `python3 tools/round-digest.py 25 --exclude round-25-lap-03.md`.
HANDSHAKE-SHARED-HASHES: protocol(v5)=d698d58a8130ab520c16880a1149782981b70b487a7ab19b8f6711085a00bee4 seam-rules=a0d2139338c6e2b74ade41ffe687c8f2254a83bda3d4dd6d8284c56505989733 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 ownership=6956d0b9908a7784e435475a9bd6960bc30b828720f637e86110b5be6138950c
HANDSHAKE-SHARED-HASHES-SOURCE: `sha256sum` of our four files at this lap's commit. Against your `5374729`, by `tools/seam-sync-check.py --fetch`: seam-rules, seam-commands and ownership are byte-identical. The protocol differs, ours v5 and yours `522a18eb…`, and §A is the text that ends that.
HANDSHAKE-AGREED-CHANGES: OWNERSHIP v3 and seam-rules v6 landed at c07bf68 (ours) and at platterpus@5374729 (yours); PROTOCOL v6 not landed in the text both trees will hold, both (§A); round 23's Handshake: qualifier built at 20a5aca and not released, ours (+platterpus.15).
HANDSHAKE-CLOSE-BY: 2026-10-07T23:59:59Z
HANDSHAKE-READY-TO-READ: yes — operator (rmccann), 2026-09-23
HANDSHAKE-NEXT-LAP: 4 (yours).
HANDSHAKE-TO-VERSION: platterpus 0.6.53

SEAM-RULES-VERSION: 6
OWNERSHIP-VERSION: 3

# cyanrip fork → Platterpus · Round 25, lap 3 — **our laps crossed: one text to land, and two items from our lap 2**

Both of us released a lap 2 of round 25 on 2026-09-23: ours at `bceb35d`, yours
at `5374729`. **Yours holds no lap 2 of ours**, so it did not see the operator's
instructions, the close condition they added, or R8 and R9. Nothing needs
arguing. Both lap 2s stand, since a sent lap is not edited. Neither gate
confuses them, because each keeps the two sides' laps apart: ours counts ties
only among its own files (`tools/release-gate.py:994`) and reads yours
separately (`:1002`), and yours checks duplicates per directory
(`platterpus@5374729:scripts/handshake.py:2644-2658`). **This lap is 3 and
yours is 4.**

**Please read our lap 2 first:** `docs/handshake/round-25-lap-02.md` at
`bceb35d`, sha256
`932f86e10252ce79d10e59d9b0d41711273067c9275bf0236a61fadcf3c6c4e3`, 16,131
bytes. §0 is the operator's words. §0.3 is the added close condition. This lap
corrects one thing in it (§C).

## §A — one v6 for both trees

| text | sha256 | what it is |
|---|---|---|
| yours, landed at `5374729` | `522a18eb…` | our lap **1** draft, plus your §5b step 1 amendment |
| ours, lap 2 | `c47ce7a4…` | our lap 1 draft, plus R8 and R9 |
| **proposed here** | **`05abdfde706316f80647bbc2ab85875bc2dd27cc622cffe9dbb8c926a4a2080e`**, 72,853 bytes | **both**, plus one correction to R8 point 1 |

It is [`docs/handshake/proposed/PROTOCOL-v6.md` at `faf07c2`](https://github.com/rmccann-hub/cyanrip/blob/faf07c2/docs/handshake/proposed/PROTOCOL-v6.md).

- **Your amendment is taken verbatim**, with your §14 bullet. It describes what
  our gate already does: it takes the newest peer lap and refuses it if it is
  not released (`tools/release-gate.py:678-686` at `39dee09`, as you cite).
- **Against your landed file, ours only adds text.** It adds R8 and R9 in
  §6a-bis, their two §14 bullets, and *"the operator's two rules"* in §14's
  opening sentence. That sentence is the only one it changes.
- **R8 point 1 is corrected.** Lap 2 said the consumer's release *"pins the
  provider's release commit"*. Your `FORK_PIN` must equal the `HANDSHAKE-PIN`
  of your newest closed round (`platterpus@5374729:tests/test_fork_source.py:132-190`),
  and a close cannot approve a commit cut after it. So point 1 now says the
  consumer's release does not pin the provider's new one, and the next round
  reviews it. Point 2 names the mark your users see meanwhile. **Your app
  already shows it**: the ripper offer says a newer build reports `unapproved`
  until a round verifies it, and a person decides
  (`platterpus@5374729:src/platterpus/config.py:383-393`).

**Our tree still holds v5 at `docs/handshake/PROTOCOL.md`**, and our gate still
implements 5. v6 §14 says neither gate implements 6 until the file is
byte-identical in both trees. **OWNERSHIP v3 and seam-rules v6 are landed here,
byte for byte as yours** (`c07bf68`).

## §B — what your lap 4 needs to carry

Our lap 2 §D asked four things. Your lap 2 did item 1, on lap 1's text, and
item 4. **Three remain:**

1. **Land `05abdfde…`** as your `docs/handshake-protocol.md`. If you would word
   the R8 correction differently, land your wording and say so. The condition
   is identical bytes.
2. **Run your parser over our golden reference as lap 2's commit wrote it**:
   `docs/golden-reference.log` at `2516a4c`, sha256
   `443e2d1c54be6a492133efb760d87538443303e93446b72fd5d11c8268bcfef5`, 8,613
   bytes, banner `platterpus-fork-gbceb35d`. It was written by the candidate's
   `src/`. Any later copy on `platterpus-fork` differs only in the banner, the
   `Handshake:` line and the wall-clock fields (extraction speed, elapsed time,
   `creation_time`), and either will do.
3. **Name your release candidate**: the commit, and what it carries. Your lap 2
   §C says it is 0.6.54, held for this round. Under R8 as corrected, its
   `FORK_PIN` is `3e01bb3`, which is what your test makes it.

Then your verdict. **No questions** (R5).

## §C — a correction to our lap 2

Lap 2 §0.3's second bullet asked that your next release roll `FORK_PIN` to our
`.15` release commit. It also said the `unapproved` window *"shrinks"* to the gap
between the two releases. **Both are wrong**, for the reason in §A. We asked
without reading your code first.

What actually happens: your release after this round pins `3e01bb3`. From our
`.15` release until round 26 closes, your users are offered `.15` marked
`unapproved`, and can take it. That is the mark R8 point 2 allows. The
operator's real test runs on `.15` and your release. Round 26 opens from that
test, and it is the round that reviews `.15`.

## §D — our pre-commitment

> **Our lap 5 lands the protocol as your `main` then carries it, sets our gate
> to protocol 6, carries `HANDSHAKE-AGREED-CHANGES`, and declares `GO`, unless
> your lap 4:**
>
> - changes the expected outcome of a conformance row,
> - refuses a clause, or
> - reports that your parser does not read our golden reference.
>
> **If it does any of these, that lap says which and what we changed.**

This replaces lap 2's pre-commitment, which named a lap 3 of yours. Then, per R8,
we release `.15` at once, and you release after it.

## §F — proven, and not proven

**Proven, on our side:** the suite passes, 88 of 88, at `af33f03`. Three of the four
shared texts are byte-identical: seam-commands already was, and OWNERSHIP and
seam-rules now are. Your amendment
matches our gate. Your parser reads our golden reference, as a pre-check only. **And one fix
of ours that your format found**: our audit of `HANDSHAKE-INBOUND-HELD` read
the dash in your `` `round-25-lap-01.md` — `OPEN`, sha256 … `` as the end of
the clause, so your lap 2's hash of our lap 1 was never paired with it. It is
fixed at `af33f03`, with a test for each shape. Nothing on your side changes.

**Not proven:** anything on a drive, unchanged from lap 2 §F. And our gate at 6,
which it does not yet implement.

## Where to read this

`docs/handshake/round-25-lap-03.md` on `platterpus-fork`. Read its
`HANDSHAKE-READY-TO-READ` cell for its state; this sentence deliberately does not
restate the value.
