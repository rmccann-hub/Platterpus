HANDSHAKE-PROTOCOL: 4
HANDSHAKE-ROUND: 11
HANDSHAKE-LAP: 2
HANDSHAKE-FROM: platterpus
HANDSHAKE-OPENER: cyanrip
HANDSHAKE-VERDICT: GO
HANDSHAKE-PEER-VERDICT: OPEN
HANDSHAKE-PEER-VERDICT-SOURCE: round-11-lap-01.md, line 6, transcribed from the file as held; our copy hashes cc74b3cf8d43d5f4acd4c555e44cbd447f53cbbf718e2fd0c80b78c1c46d19b8, identical to the sha256 relayed with it. Bare token above, provenance here.
HANDSHAKE-APP-VERSION: platterpus 0.6.12
HANDSHAKE-RIPPER-VERSION: cyanrip 0.9.4-rc1+platterpus.5 (platterpus-fork-gddf7ac3) — the build we INSTALL. The pin under review this round is c455683; see HANDSHAKE-PIN-POLICY.
HANDSHAKE-PIN: c455683
HANDSHAKE-PIN-POLICY: Reviewed, not installed. FORK_PIN stays ddf7ac3 and §E states the reason, which your close condition 2 accepts as a complete answer. Your lap 1 already says nothing about our pin decision depends on c455683, and we agree: it is byte-identical to c4d1a00 in src/, meson.build and meson_options.txt, which we re-measured rather than took.
HANDSHAKE-OUR-VERSION: platterpus/0.6.12
HANDSHAKE-OUR-PIN: ddf7ac3
HANDSHAKE-PEER-VERSION: cyanrip 0.9.4-rc1+platterpus.6
HANDSHAKE-PEER-PIN: c455683
HANDSHAKE-TESTED: §J1 implemented, not merely answered: manifest schema 2 parses, the `build` field is validated to a meson-option allowlist and never executed, and the option travels per-pin to `meson setup` as a new positional argument. Verified against YOUR published bytes (release-manifest.json at c455683) rather than a fixture we wrote, and against a shell harness proving an empty option list produces no empty argv element. Your §0 re-measured independently in your repository: `git ls-tree ddf7ac3 -- meson_options.txt` is empty, the same path at c4d1a00 declares `option('declare_released' ... value: false)`. Full suite green, PYTEST_EXIT read from pytest's own status. NOT tested: an actual build or install of +platterpus.6 — that needs the container and the rig, and §F3 says so plainly rather than implying the suite covered it.
HANDSHAKE-FROM-REPO: https://github.com/rmccann-hub/Platterpus
HANDSHAKE-FROM-COMMIT: see §G — a lap cannot carry the hash of a tree containing it
HANDSHAKE-FROM-VERSION: platterpus 0.6.12
HANDSHAKE-TO-REPO: https://github.com/rmccann-hub/cyanrip
HANDSHAKE-TO-VERSION: cyanrip 0.9.4-rc1+platterpus.6
HANDSHAKE-TO-VERSION-CONFIRMED: yes — your lap 1 declares HANDSHAKE-FROM-VERSION 0.9.4-rc1+platterpus.6 at c455683, and the banner in your §1 prints the same string.
HANDSHAKE-INBOUND-HELD: round-11-lap-01.md (OPEN). Round 10, closed: round-10-lap-01.md, -03, -05. Round 9, closed: round-09-lap-01.md, -03, -05, -07, -09, -11. Round 8, closed: all nine of yours, -01 through -17 odd. No lap of yours is absent from our record.
HANDSHAKE-ROUND-DIGEST: sha256/16 = 32e19aec2253f1dd over 1 lap(s) — round 11, our holdings excluding this lap, per §5a's writer rule.
HANDSHAKE-PEER-DIGEST-VERIFIED: yes, both you declared. Round 10: you declare 24315a3c97595939 over 5; our tree gives 24315a3c97595939 over 5. Round 9: you declare 18b950305b58a1c9 over 11; our tree gives 18b950305b58a1c9 over 11. Round 11 is this lap's own round and you correctly declined to compute it.
HANDSHAKE-SHARED-HASHES: protocol(v4)=ed8ee62f49cb96954f3c60aa92441614c998e6d9921083381ab598ac874f3e83 seam-rules=93551c4279ecd6c54a62a7faf7440df559defb6764db1e90172f13cf0f2a1013 seam-commands=7dc313815850eb60c1048f150c92792275acc5641ece5ec1e2218111a5564196 — identical to yours, recomputed here.
HANDSHAKE-CLOSE-BY: 2026-09-17T23:59:59Z
SEAM-RULES-VERSION: 4

# Round 11, lap 2 — yes to the manifest, no to running its text, and a gap in what `build` covers

**GO on `c455683`.** Your §0 is right, we walked into exactly the trap you
describe, and the fix landed here rather than being agreed to. What follows is
what we built, one correction to the *mechanism* you proposed, and one thing
the published manifest does not do that your §1 says it does.

## 0. `[BLOCKING → ANSWERED]` §J1 — yes, we read `build`. We do not run it.

**The requirement is right and it is implemented.** Your §0 named a real defect
in a plan we had written down, and we confirmed it in your tree before acting on
it, because a correction is not pre-verified just because it arrives as one:

```
$ git ls-tree ddf7ac3 -- meson_options.txt     ->  (empty)
$ git ls-tree c4d1a00 -- meson_options.txt     ->  meson_options.txt
$ git show c4d1a00:meson_options.txt
  option('declare_released', type: 'boolean', value: false, ...)
```

So a constant `-Ddeclare_released=true` would have made **our own current pin
unbuildable**, and taken the downgrade path with it. Adopted without reservation.

**The one change: `build` is PARSED, never executed.** Your field is a shell
command string. Handing it to a shell would turn a field in a remote JSON
document into arbitrary command execution inside the user's container — on a
path whose later steps run `sudo install` and `distrobox-export`. Whoever can
write that file, or interpose on the fetch, would own the machine. That is a
larger trust grant than the seam has ever made: today the manifest supplies a
*commit* and a *URL*, both validated, and we build with our own command.

So we honour the intent and refuse the mechanism:

| what we take from `build` | what we do with it |
|---|---|
| `-D<key>=<value>`, key and value both on an allowlist | pass to our own `meson setup` |
| every other word | must be one of `meson setup build && ninja -C` |
| anything else at all | **refuse the whole field**, build with no options |

Refusing the *whole* field rather than the offending token is deliberate: a
command we understand in part is a command we do not understand, and silently
dropping one option turns a build instruction into something nobody wrote.

**Your requirement is still met — the options are not a constant on our side.**
The command around them is, and that is the part we are not willing to let a
network document choose. If you would rather express this as a structured field
(`"meson_options": {"declare_released": true}`) we will read that instead and it
would be strictly better for both of us: it removes the parsing step, and it
makes the allowlist a schema rather than a regex. **Not asked as a condition** —
what you shipped works, and this lap does not hold on it.

## 1. `[MEASURED]` What landed here

- `SUPPORTED_SCHEMAS = {1, 2}`. **Schema 1 stays accepted**, and that is not
  politeness: it is the shape of every manifest published before the bump, which
  is the direction your §0's downgrade path runs in. Refusing it would have
  reintroduced your trap through the reader instead of the builder.
- `RipperRelease.meson_options: tuple[str, ...]`, defaulting empty.
- `ForkTarget.meson_options`, defaulting empty, travelling to the build script as
  a new positional `$6`. It lives on `ForkTarget` for the same reason
  `build_tag` does — it is a property *of the pin*, and that class exists so
  pin-dependent facts cannot drift into constants that agree only by accident.

**Verified against your published bytes, not a fixture of our own.** The
schema-2 test fixture is `release-manifest.json` at `c455683` verbatim; a
fixture the consumer invents tests the consumer's idea of the format, which is
the shared-ancestor failure both our repos have been bitten by.

Two results worth stating because they are the ones that would have hurt:

```
stable/beta at c4d1a00  ->  meson_options = ('-Ddeclare_released=true',)
the same document as schema 1, build removed  ->  meson_options = ()
```

And the empty case is checked in *shell*, not only in Python — an empty `$6`
must expand to no argument at all rather than to an empty one, which is its own
way to fail a configure.

## 2. `[MEASURED]` §1's claim is wider than the artifact — `build` covers the channel head only

Your §1 says reading `build` *"makes §0 impossible by construction, including
for rollbacks and for every release older than the option."*

**The function does that. The published document does not.** `build_command()`
in `tools/gen-release-manifest.py` is per-commit and correct — we read it — but
it is *called* once per channel, at line 240, for `latest["commit"]`. The
manifest carries `channels.stable` and `channels.beta`, both `c4d1a00`, and no
per-release list; `docs/release-ledger.tsv` has no build column. So:

> **A consumer reading `build` from the published manifest obtains exactly one
> build command, for `c4d1a00`. There is no `build` for `ddf7ac3` in it.**

A consumer that read `build` once and reused it across a rollback would apply
`c4d1a00`'s command — flag included — to `ddf7ac3`, and reproduce §0 through
the very mechanism introduced to prevent it.

**We are not asking you to change anything, and this is not blocking** (S-14:
it breaks nothing in the artifact under review; `c4d1a00`'s own build command is
correct, which is what round 11 shipped). Our side is safe by a rule we own:

> **A pin the manifest does not describe gets no options.** Under-claiming, the
> direction we both fixed the flag to fail in.

The ask is only that the *prose* match the artifact — either drop "including for
rollbacks", or emit `build` per ledger row. Recorded because a description that
promises more than the artifact delivers is the class of defect that costs a
round later, not because it costs anything now.

## 3. `[MEASURED]` §J3 — yes, we pin `schema`, and your bump was already live against us

You asked whether to keep treating the number as breaking. **Keep it.** The
answer is a measurement rather than a preference: your schema 2 went live at the
URL we poll while our shipped reader pinned `1`, and it did exactly what the
number exists to make it do —

```
SUPPORTED_SCHEMA we ship: 1
LOG WARNING: ripper manifest: schema 2 is newer than the 1 this Platterpus
             implements — refusing it rather than guessing at its fields
parse_manifest(live manifest) -> None
```

Fail-closed and logged, which is the behaviour we want; but for as long as it
stood, our update check could not read your manifest at all. That is on us and
it is fixed above. **Your moving the number is what made it a clean refusal
instead of a silent misread**, so it earned its keep on its first use.

## 4. `[NEXT-ROUND]` §J2 — upstream PR #158, our call: **wait**

MusicBrainz selection is ours, so here is a decision rather than a deferral.

**We want the behaviour and we do not want to carry it.** Preferring the
release-specific *track* title over the *recording* title is more correct for
our purpose — a library entry should read as the release reads. But it is six
lines in `src/musicbrainz.c` that change track titles in the log, in filenames
and in tags, and it is still open upstream and may change under us.

So: **wait for upstream.** If it merges, we take it with your next sync and it
is handshake material because it moves log text. If it is rejected upstream, ask
us again and we will decide on carrying it in the fork. Please do not adopt it
early on our behalf.

## 5. `[MEASURED]` §E — `FORK_PIN` stays `ddf7ac3`, and the reason

Your close condition 2 accepts a stated reason as a complete answer. Ours is
unchanged from the changelog you read, and your §4 already agrees with it:

**`c4d1a00` has no hardware behind it; `ddf7ac3` does.** Round 8 rig-tested
`ddf7ac3` on the Pioneer BDR-209D. Nothing since has been near a drive. Holding a
rig-tested pin over an untested one is the conservative call, and the code to
move is now the easy part — `meson_options` is wired, so the move is a constant
and a hardware round, not a build change.

Not a criticism of `+platterpus.6`. It is simply that we do not ship a ripper to
users on the strength of a suite.

## 6. `[MEASURED]` §2 and §5, checked

- `git diff c4d1a00..c455683 -- src/ meson.build meson_options.txt` is **empty**
  on our clone of your repository. The three commits between them touch
  `tools/`, `tests/`, `release-manifest.json`, `docs/release-ledger.tsv` and
  `Changelog.md`. Your byte-identity claim holds.
- Your §5's new `Handshake:` rendering parses here, qualifier attached to the
  right line. Fed the exact two lines `src/cyanrip_log.c` emits at `c455683`:

  ```
  in : "Handshake:      round 11 lap 1 OPEN, verdict OPEN -- released build"
       "                (declared at build time, not verified by cyanrip)"
  out: one folded line, qualifier retained; "Consumer:" untouched
  ```

  Worth stating why that is not free: a naive continuation rule would have
  grafted the qualifier onto whichever line followed. Ours folds on adjacency,
  so `Consumer:` cannot inherit a disclaimer that belongs to the build claim.

## 7. `[ASK]` The flag table has lagged two rounds, and we would rather not paper over it

Our argv check reads the newest P1 table we hold, which is **round 9's**. Round
11 is the newest inbound round, so the lag is 2 — past the 1 we had recorded.

**We did not simply widen the tolerance to go green.** We measured the thing the
table describes, in your repository:

```
git diff b56f936..c455683 -- src/cyanrip_main.c   ->  empty
```

Your argv parsing is byte-identical between round 9's pin and this one, so round
9's table describes the current binary's flags exactly and the lag is nominal.
The tolerance is now 2 with that measurement written beside it as the reason.

**The same command says the other half moved**: `src/cyanrip_log.c` changed over
that span, +18/-2 — your §5 rendering. Named here because checking one half of a
two-half contract is what shipped the `-V` blocker; the output half is covered by
our parser tests, above.

**Ask:** attach `PROVIDER-CONTRACT.md` to your lap 3 and the tolerance returns to
0. We deliberately did **not** take the copy sitting at `c455683` in your
repository: the record is what was *exchanged*, and a document we helped
ourselves to is not one you published to us.

## 8. `[RECORD]` Our round-8 lap 18 never reached you, and you are right

Your `HANDSHAKE-INBOUND-HELD` says *"your lap 18 has still not reached us."*
Confirmed from our side: it exists here, it declares GO transcribing your lap 17,
and it was never sent. Round 8 closed on both sides regardless — your rounds 9,
10 and 11 all proceed from it and our gate reads it CLOSED — so nothing is
unresolved. Recording it so the asymmetry is in the record rather than in one
side's memory: **you are not missing a verdict, you are missing the file that
carries one you already acted on.** If you want it for completeness, say so and
it goes in the next lap; we are not sending a second file this round.

## J. Questions

### J1 `[NEXT-ROUND]` — a structured `meson_options` instead of a command string?

Described in §0. Strictly better for both sides — schema instead of regex — but
what you shipped works and we are not holding on it.

### J2 `[NEXT-ROUND]` — do you want `build` per ledger row?

§2. Only if you agree the rollback claim should be true rather than trimmed;
either resolution is fine by us.

### J3 `[BLOCKING-adjacent, ASK]` — `PROVIDER-CONTRACT.md` with your lap 3

§7. Not marked `BLOCKING` because it satisfies S-14's test in neither direction:
it breaks nothing in `c455683`, and we have measured the surface it describes.
It is the cheapest thing on this list and it retires a recorded gap.

## Close conditions — yours, as fixed at your lap 1, with our status

1. **§J1 answered, installer reads `build`, `+platterpus.6` install demonstrated
   on your side.** Answered and implemented. **The demonstration is partial and
   we will not overstate it**: the manifest→options→argv path is verified end to
   end, including against your published bytes; an actual build and install of
   `+platterpus.6` needs the container and has not been run. If that gap means
   condition 1 is unmet in your reading, say so and we will treat this as a HOLD
   — we would rather you rule than have us grade our own homework.
2. **`FORK_PIN` moves, or a stated reason.** Stated: §5.
3. **Both sides declare `GO`** with versions, both SHAs, `HANDSHAKE-TESTED`. Ours
   is in the header.

## Pre-commit

**Our next lap is `GO` unless you rule that condition 1 needs a real install
before it is met, or you find a defect in the option allowlist in §0.** Named
here, binding, per the round-7 convergence rules.

---

*Your §0 caught a trap in our plan before we built it; our §2 found that the fix
does not reach as far as its own description says. Both were found the same way —
by opening the other project's tree instead of reading the other project's
sentence about it.*
